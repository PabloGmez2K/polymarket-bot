import urllib.request
import urllib.parse
import json
import re
import math
import os
import time
import logging
import threading
from datetime import date, datetime, timezone, timedelta

# Dependencias externas (pip install python-dotenv py-clob-client)
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Cargar .env ANTES de leer cualquier variable de entorno
load_dotenv()

# =============================================================
# bot.py — Bot de Polymarket v6 (Timing estratégico + Telegram)
# Sesión 7: Scheduler inteligente + comandos Telegram con botones
# =============================================================
#
# Cambios respecto a v5:
#   - Scheduler estratégico: ejecuta a horas UTC fijas (no cada 6h)
#   - Telegram bidireccional: recibe comandos, no solo envía
#   - Botones inline: tocas un botón en el móvil, obtienes info
#   - Threading: un hilo escucha Telegram, otro gestiona ciclos
#   - /forzar: ejecuta un ciclo inmediato desde el móvil
#   - Cliente CLOB global: se autentica una vez, se reutiliza
# =============================================================


# =============================================================
# CONFIGURACIÓN
# =============================================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))

MIN_EDGE = 10.0
MIN_BET = 1.00
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.40
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
MIN_DAYS_AHEAD = 1

MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8

# ---- TIMING ESTRATÉGICO ----
# Horas UTC en las que el bot ejecuta un ciclo.
#
# ¿Por qué estas horas y no "cada 6h"?
#
# Open-Meteo actualiza sus modelos meteorológicos a las 00, 06, 12, 18 UTC.
# Los traders de Polymarket están más activos en horario EEUU (14-22 UTC).
# Queremos correr DESPUÉS de cada actualización de datos, Y cuando hay liquidez.
#
#   08:00 UTC (09:00 España) → Datos de la actualización 06 UTC, mercados asiáticos
#   16:00 UTC (17:00 España) → Datos de la actualización 12 UTC, EEUU activo
#   23:00 UTC (00:00 España) → Datos de la actualización 18 UTC, última pasada del día
#
# Puedes cambiar esto con la variable de entorno SCHEDULE_HOURS_UTC.
# Ejemplo: "8,14,20" para tres horas distintas.
SCHEDULE_HOURS_UTC_STR = os.getenv("SCHEDULE_HOURS_UTC", "8,16,23")
SCHEDULE_HOURS_UTC = [int(h.strip()) for h in SCHEDULE_HOURS_UTC_STR.split(",")]

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# =============================================================
# LOGGING
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("trades.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


# =============================================================
# ESTADO COMPARTIDO ENTRE HILOS
# =============================================================
#
# Este diccionario es el "tablón de anuncios" del bot.
# El hilo del scheduler escribe aquí (cuándo corrió, qué encontró).
# El hilo de Telegram lo lee (para responder a tus comandos).
#
# threading.Event es el "walkie-talkie":
# - El scheduler duerme esperando la señal.
# - Cuando mandas /forzar, el hilo Telegram llama force_event.set()
# - El scheduler se despierta inmediatamente.

bot_state = {
    "next_run": None,
    "last_run": None,
    "last_orders_placed": 0,
    "last_opportunities": 0,
    "running": False,
    "cycle_count": 0,
}

force_event = threading.Event()
clob_client = None  # Se autentica una vez al arrancar


# =============================================================
# DATOS DE REFERENCIA
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

RESOLUTION_STATIONS = {
    "Seoul":          {"lat": 37.4602, "lon": 126.4407, "name": "Incheon Intl"},
    "London":         {"lat": 51.5048, "lon": 0.0495,   "name": "London City"},
    "Tel Aviv":       {"lat": 32.0114, "lon": 34.8867,  "name": "Ben Gurion"},
    "Shanghai":       {"lat": 31.1443, "lon": 121.8083, "name": "Pudong"},
    "Tokyo":          {"lat": 35.5494, "lon": 139.7798, "name": "Haneda"},
    "New York City":  {"lat": 40.7772, "lon": -73.8726, "name": "LaGuardia"},
    "Beijing":        {"lat": 40.0799, "lon": 116.6031, "name": "Beijing Capital"},
    "Hong Kong":      {"lat": 22.3080, "lon": 113.9185, "name": "HK Intl"},
    "Singapore":      {"lat": 1.3502,  "lon": 103.9940, "name": "Changi"},
    "Toronto":        {"lat": 43.6772, "lon": -79.6306, "name": "Pearson"},
    "Chicago":        {"lat": 41.9742, "lon": -87.9073, "name": "O'Hare"},
    "Wellington":     {"lat": -41.3272, "lon": 174.8053, "name": "Wellington"},
    "Munich":         {"lat": 48.3538, "lon": 11.7861,  "name": "Munich"},
    "Warsaw":         {"lat": 52.1657, "lon": 20.9671,  "name": "Warsaw Chopin"},
    "Ankara":         {"lat": 40.1281, "lon": 32.9951,  "name": "Esenboğa"},
    "Atlanta":        {"lat": 33.6407, "lon": -84.4277, "name": "Hartsfield"},
    "Shenzhen":       {"lat": 22.6393, "lon": 113.8107, "name": "Bao'an"},
    "Paris":          {"lat": 49.0097, "lon": 2.5479,   "name": "CDG"},
    "Buenos Aires":   {"lat": -34.8222, "lon": -58.5358, "name": "Ezeiza"},
}


# =============================================================
# TELEGRAM — ENVÍO DE MENSAJES
# =============================================================

# Los botones que aparecen en Telegram.
# Cada botón tiene un texto visible y un callback_data (lo que el bot recibe
# cuando lo tocas). Es una lista de filas — cada fila es una lista de botones.
MENU_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📊 Estado", "callback_data": "estado"},
            {"text": "📋 Órdenes", "callback_data": "ordenes"},
        ],
        [
            {"text": "⏰ Siguiente", "callback_data": "siguiente"},
            {"text": "🚀 Forzar ciclo", "callback_data": "forzar"},
        ],
    ]
}


def send_telegram(mensaje, with_menu=False):
    """
    Manda un mensaje al móvil via Telegram (POST).

    with_menu=True añade los botones interactivos debajo del mensaje.
    Así después de cada respuesta puedes tocar otro botón sin escribir nada.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML",
        }
        if with_menu:
            payload["reply_markup"] = MENU_KEYBOARD

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Telegram: error al enviar: {e}")


def answer_callback_query(callback_id, text=""):
    """
    Responde a un callback (botón pulsado) en Telegram.

    Esto es obligatorio: si no respondes, el botón muestra un spinner
    infinito. El 'text' aparece como una notificación pequeña arriba.
    """
    if not TELEGRAM_TOKEN:
        return
    try:
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# =============================================================
# TELEGRAM — COMANDOS
# =============================================================

def cmd_estado():
    """📊 Muestra el estado general del bot."""
    modo = "🔴 REAL" if not DRY_RUN else "🟡 DRY RUN"
    running = "🔄 Sí, ahora mismo" if bot_state["running"] else "💤 No"

    next_run = bot_state["next_run"]
    if next_run:
        now = datetime.now(timezone.utc)
        diff = next_run - now
        if diff.total_seconds() > 0:
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            next_str = f"{next_run.strftime('%H:%M UTC')} (en {hours}h {minutes}m)"
        else:
            next_str = "Ahora"
    else:
        next_str = "No programado"

    last_run = bot_state["last_run"]
    last_str = last_run.strftime('%H:%M UTC') if last_run else "Nunca"

    msg = (
        f"📊 <b>Estado del Bot</b>\n"
        f"\n"
        f"Modo: {modo}\n"
        f"Bankroll: <b>${BANKROLL:.2f}</b>\n"
        f"Ejecutando: {running}\n"
        f"\n"
        f"Última ejecución: {last_str}\n"
        f"Próxima: {next_str}\n"
        f"Ciclos completados: {bot_state['cycle_count']}\n"
        f"\n"
        f"Último ciclo:\n"
        f"  Oportunidades: {bot_state['last_opportunities']}\n"
        f"  Órdenes: {bot_state['last_orders_placed']}\n"
        f"\n"
        f"Schedule: {SCHEDULE_HOURS_UTC} UTC"
    )
    send_telegram(msg, with_menu=True)


def cmd_ordenes():
    """📋 Muestra las órdenes abiertas en Polymarket."""
    global clob_client

    if bot_state["running"]:
        send_telegram("🔄 Ciclo en ejecución, prueba en unos segundos...", with_menu=True)
        return

    if clob_client is None:
        send_telegram("❌ Cliente no autenticado. No puedo consultar órdenes.", with_menu=True)
        return

    try:
        orders = get_open_orders(clob_client)
    except Exception as e:
        send_telegram(f"❌ Error al consultar órdenes: {e}", with_menu=True)
        return

    if not orders:
        send_telegram("📋 <b>Órdenes abiertas:</b> ninguna", with_menu=True)
        return

    lines = [f"📋 <b>Órdenes abiertas: {len(orders)}</b>\n"]
    for i, order in enumerate(orders):
        price = order.get("price", "?")
        size = order.get("original_size", order.get("size", "?"))
        side = order.get("side", "?")
        asset_id = order.get("asset_id", "")

        # Intentar calcular la edad de la orden
        created_raw = order.get("created_at", "")
        age_str = ""
        if created_raw:
            try:
                if isinstance(created_raw, (int, float)):
                    created = datetime.fromtimestamp(created_raw, tz=timezone.utc)
                else:
                    created = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - created).total_seconds() / 3600
                age_str = f" | {age_h:.1f}h"
            except (ValueError, TypeError, OSError):
                pass

        lines.append(
            f"{i+1}. {side} @ ${price}{age_str}\n"
            f"   Token: {asset_id[:16]}..."
        )

    send_telegram("\n".join(lines), with_menu=True)


def cmd_siguiente():
    """⏰ Muestra cuánto falta para el próximo ciclo."""
    next_run = bot_state["next_run"]
    if not next_run:
        send_telegram("⏰ No hay próxima ejecución programada.", with_menu=True)
        return

    now = datetime.now(timezone.utc)
    diff = next_run - now

    if diff.total_seconds() <= 0:
        send_telegram("⏰ Ejecutando ahora mismo...", with_menu=True)
        return

    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)

    schedule_display = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    msg = (
        f"⏰ <b>Próximo ciclo</b>\n"
        f"\n"
        f"Hora: {next_run.strftime('%H:%M UTC')} ({next_run.strftime('%d %b')})\n"
        f"Faltan: <b>{hours}h {minutes}m</b>\n"
        f"\n"
        f"Schedule diario: {schedule_display} UTC"
    )
    send_telegram(msg, with_menu=True)


def cmd_forzar():
    """🚀 Ejecuta un ciclo inmediatamente."""
    if bot_state["running"]:
        send_telegram("🔄 Ya hay un ciclo en ejecución. Espera a que termine.", with_menu=True)
        return

    send_telegram("🚀 <b>Ciclo forzado</b>\nDespertando al scheduler...")
    force_event.set()  # ← Esto despierta al scheduler inmediatamente


# Mapa de comandos: texto → función
COMMANDS = {
    "estado": cmd_estado,
    "ordenes": cmd_ordenes,
    "siguiente": cmd_siguiente,
    "forzar": cmd_forzar,
}


# =============================================================
# TELEGRAM — RECEPCIÓN (POLLING)
# =============================================================

def is_authorized(chat_id):
    """Solo responde a tu chat_id. Seguridad básica."""
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def handle_telegram_update(update):
    """
    Procesa un update de Telegram. Hay dos tipos:
    - callback_query: alguien tocó un botón
    - message: alguien escribió un texto (como /estado)
    """

    # ---- Botón pulsado ----
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        chat_id = cb.get("message", {}).get("chat", {}).get("id", 0)
        command = cb.get("data", "")

        if not is_authorized(chat_id):
            answer_callback_query(cb_id, "⛔ No autorizado")
            return

        # Responder al callback (quita el spinner del botón)
        answer_callback_query(cb_id)

        # Ejecutar el comando
        if command in COMMANDS:
            try:
                COMMANDS[command]()
            except Exception as e:
                log.warning(f"Error en comando Telegram '{command}': {e}")
                send_telegram(f"❌ Error: {e}", with_menu=True)
        return

    # ---- Mensaje de texto ----
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id", 0)
        text = msg.get("text", "").strip().lower()

        if not is_authorized(chat_id):
            return

        # Quitar la barra / si la escriben
        if text.startswith("/"):
            text = text[1:]

        # Quitar @nombre_del_bot si lo incluyen
        if "@" in text:
            text = text.split("@")[0]

        if text in COMMANDS:
            try:
                COMMANDS[text]()
            except Exception as e:
                log.warning(f"Error en comando Telegram '{text}': {e}")
                send_telegram(f"❌ Error: {e}", with_menu=True)
        else:
            # Cualquier texto desconocido → mostrar menú
            send_telegram(
                "🤖 <b>Bot Polymarket</b>\n"
                "Toca un botón para interactuar:",
                with_menu=True
            )


def telegram_polling_loop():
    """
    Hilo que escucha Telegram constantemente.

    ¿Cómo funciona el polling?
    - Le preguntamos a Telegram: "¿hay mensajes nuevos?"
    - Telegram espera hasta 30 segundos antes de responder (long polling)
    - Si llega un mensaje durante esa espera, responde inmediatamente
    - Procesamos el mensaje y volvemos a preguntar
    - El 'offset' le dice a Telegram: "ya procesé todo hasta este ID,
      dame solo los nuevos"

    Este bucle NUNCA termina — corre mientras el bot esté vivo.
    Si hay un error de red, espera 10 segundos y reintenta.
    """
    log.info("Telegram polling: iniciado")
    offset = 0

    while True:
        try:
            url = (
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
                f"?offset={offset}&timeout=30"
            )
            resp = urllib.request.urlopen(url, timeout=35)
            data = json.loads(resp.read())

            if not data.get("ok"):
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    handle_telegram_update(update)
                except Exception as e:
                    log.warning(f"Error procesando update Telegram: {e}")

        except Exception as e:
            # Error de red, Telegram caído, etc. — esperar y reintentar
            log.warning(f"Telegram polling error: {e}")
            time.sleep(10)


# =============================================================
# AUTENTICACIÓN
# =============================================================

def setup_client():
    pk = os.getenv("PK")
    funder = os.getenv("FUNDER")

    if not pk or not funder:
        log.error("No se encontraron PK o FUNDER en .env")
        return None

    try:
        client = ClobClient(
            "https://clob.polymarket.com",
            key=pk,
            chain_id=137,
            signature_type=1,
            funder=funder,
        )
        client.set_api_creds(client.create_or_derive_api_creds())
        log.info("Autenticación con Polymarket: OK")
        return client
    except Exception as e:
        log.error(f"Error en autenticación: {e}")
        return None


# =============================================================
# FUNCIONES: API
# =============================================================

def api_get(endpoint):
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.6")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_coordinates_fallback(city_name):
    city_clean = city_name.strip().replace(" ", "+")
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city_clean}&count=1&language=en"
    )
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    if "results" not in data or len(data["results"]) == 0:
        return None
    place = data["results"][0]
    return place["latitude"], place["longitude"]


def get_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f",precipitation_probability_max"
        f",precipitation_sum"
        f"&timezone=auto"
    )
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    daily = data["daily"]
    forecast_by_date = {}
    for i in range(len(daily["time"])):
        d = daily["time"][i]
        forecast_by_date[d] = {
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_prob": daily["precipitation_probability_max"][i],
            "rain_mm": daily["precipitation_sum"][i],
        }
    return forecast_by_date


# =============================================================
# FUNCIONES: GESTIÓN DE ÓRDENES ABIERTAS
# =============================================================

def get_open_orders(client):
    try:
        orders = client.get_orders()
        open_orders = []
        for order in orders:
            status = order.get("status", "").upper()
            if status in ("LIVE", "ACTIVE", "OPEN"):
                open_orders.append(order)
        log.info(f"Órdenes abiertas encontradas: {len(open_orders)}")
        return open_orders
    except Exception as e:
        log.warning(f"Error al obtener órdenes abiertas: {e}")
        return []


def get_order_token_ids(open_orders):
    token_ids = set()
    for order in open_orders:
        asset_id = order.get("asset_id", "")
        if asset_id:
            token_ids.add(asset_id)
    return token_ids


def clean_stale_orders(client, open_orders, max_age_hours):
    cancelled = 0
    now = datetime.now(timezone.utc)

    for order in open_orders:
        order_id = order.get("id", "")
        created_at_raw = order.get("created_at", "")

        if not created_at_raw or not order_id:
            continue

        try:
            if isinstance(created_at_raw, (int, float)):
                created_at = datetime.fromtimestamp(created_at_raw, tz=timezone.utc)
            else:
                created_at_clean = str(created_at_raw).replace("Z", "+00:00")
                created_at = datetime.fromisoformat(created_at_clean)
        except (ValueError, TypeError, OSError):
            log.warning(f"No se pudo parsear fecha de orden {order_id}: {created_at_raw}")
            continue

        age_hours = (now - created_at).total_seconds() / 3600

        if age_hours > max_age_hours:
            log.info(
                f"Cancelando orden stale: {order_id[:16]}... "
                f"(edad: {age_hours:.1f}h, límite: {max_age_hours}h)"
            )
            try:
                client.cancel(order_id)
                cancelled += 1
                log.info(f"  → Cancelada OK")
            except Exception as e:
                log.warning(f"  → Error al cancelar: {e}")

    return cancelled


# =============================================================
# FUNCIONES: PARSEO
# =============================================================

def parse_temperature_question(question):
    match = re.search(
        r"temperature in (.+?) (?:be |on )"
        r"(\d+)°([CF])"
        r"(?: or (below|higher|above))?"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)"
        r"\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if not match:
        return None

    city = match.group(1).strip()
    temp = int(match.group(2))
    unit = match.group(3).upper() if match.group(3) else "C"

    condition = "exact"
    if match.lastindex >= 4 and match.group(4):
        modifier = match.group(4).lower()
        if modifier == "below":
            condition = "at_or_below"
        elif modifier in ("higher", "above"):
            condition = "at_or_above"

    date_str = match.group(5) if match.lastindex >= 5 else None

    return {
        "city": city, "temp_threshold": temp,
        "condition": condition, "date_str": date_str, "unit": unit,
    }


def date_text_to_iso(date_text, year=2026):
    if not date_text:
        return None
    months = {
        "january": "01", "february": "02", "march": "03",
        "april": "04", "may": "05", "june": "06",
        "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12",
    }
    parts = date_text.strip().split()
    if len(parts) != 2:
        return None
    month_name = parts[0].lower()
    day = parts[1]
    if month_name not in months:
        return None
    return f"{year}-{months[month_name]}-{day.zfill(2)}"


# =============================================================
# FUNCIONES: MODELO DE PROBABILIDAD
# =============================================================

def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def get_uncertainty(days_ahead):
    if days_ahead <= 0:
        return 0.8
    elif days_ahead == 1:
        return 1.0
    elif days_ahead == 2:
        return 1.4
    elif days_ahead == 3:
        return 1.8
    elif days_ahead <= 5:
        return 2.5
    else:
        return 3.0


def estimate_prob(forecast_max, threshold_c, condition, days_ahead):
    sigma = get_uncertainty(days_ahead)
    mu = forecast_max

    if condition == "exact":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma) - normal_cdf(threshold_c - 0.5, mu, sigma)
    elif condition == "at_or_below":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma)
    elif condition == "at_or_above":
        prob = 1.0 - normal_cdf(threshold_c - 0.5, mu, sigma)
    else:
        prob = 0.5

    return max(0.01, min(0.99, prob))


# =============================================================
# FUNCIONES: BANKROLL / KELLY
# =============================================================

def kelly_fraction(estimated_prob, market_price):
    if market_price <= 0.01 or market_price >= 0.99:
        return 0.0
    if estimated_prob <= 0.01 or estimated_prob >= 0.99:
        return 0.0

    b = (1.0 - market_price) / market_price
    p = estimated_prob
    q = 1.0 - p

    kelly = (p * b - q) / b
    if kelly <= 0:
        return 0.0

    half_kelly = kelly / 2.0
    return min(half_kelly, MAX_BET_PCT)


def calculate_position(bankroll, estimated_prob, market_price):
    fraction = kelly_fraction(estimated_prob, market_price)

    if fraction <= 0:
        return None

    aggressive_price = min(market_price + PRICE_AGGRESSION, 0.99)
    amount = round(bankroll * fraction, 2)
    if amount < MIN_BET:
        return None

    shares = amount / aggressive_price

    if shares < 5.0:
        amount_for_5_shares = round(5.0 * aggressive_price, 2)
        if amount_for_5_shares > bankroll * MAX_BET_PCT:
            return None
        if amount_for_5_shares < MIN_BET:
            return None
        amount = amount_for_5_shares
        shares = 5.0

    profit = round(shares * (1.0 - aggressive_price), 2)
    loss = round(amount, 2)
    ev = round(estimated_prob * profit - (1 - estimated_prob) * loss, 2)

    return {
        "fraction_pct": round(fraction * 100, 2),
        "amount": amount,
        "shares": round(shares, 2),
        "profit_if_win": profit,
        "loss_if_lose": loss,
        "expected_value": ev,
        "aggressive_price": aggressive_price,
        "market_price": market_price,
    }


# =============================================================
# FUNCIONES: EJECUCIÓN DE ÓRDENES
# =============================================================

def execute_trade(client, trade, dry_run=True):
    token_id = trade["token_id"]

    position = trade["position"]
    if "aggressive_price" in position:
        price = position["aggressive_price"]
    else:
        price = trade["mkt_price"] / 100.0

    size = position["shares"]
    price = round(price, 2)
    size = round(size, 2)
    side = BUY

    log.info(
        f"{'[DRY RUN] ' if dry_run else ''}Orden: "
        f"{trade['side']} {size} shares × ${price:.2f} "
        f"(mercado: ${trade['mkt_price']/100:.2f}, agresividad: +${PRICE_AGGRESSION:.2f}) "
        f"| {trade['city']} {trade['date']} "
        f"| token {token_id[:12]}..."
    )

    if dry_run:
        return {"ok": True, "order_id": "DRY_RUN", "msg": "Simulado (DRY_RUN=True)"}

    try:
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.GTC)

        order_id = resp.get("orderID", resp.get("id", "desconocido"))
        status = resp.get("status", "?")

        log.info(f"Orden enviada: ID={order_id} | Status={status}")
        return {"ok": True, "order_id": order_id, "msg": f"Status: {status}"}

    except Exception as e:
        log.error(f"Error al ejecutar orden: {e}")
        return {"ok": False, "order_id": None, "msg": str(e)}


# =============================================================
# FUNCIÓN PRINCIPAL (UN CICLO)
# =============================================================

def main(client):
    """
    Ejecuta un ciclo completo del bot.
    Recibe el cliente ya autenticado (no lo crea cada vez).
    """
    today_str = date.today().isoformat()
    mode_label = "DRY RUN (sin órdenes reales)" if DRY_RUN else "⚠️  MODO REAL — ÓRDENES ACTIVAS"

    bot_state["running"] = True
    bot_state["last_run"] = datetime.now(timezone.utc)

    log.info("=" * 65)
    log.info(f"POLYMARKET WEATHER BOT v6  |  {today_str}")
    log.info(f"Modo: {mode_label}")
    log.info(f"Bankroll: ${BANKROLL:.2f}  |  Edge mín: {MIN_EDGE}%")
    log.info(f"Filtro precio: {MIN_PRICE:.0%} – {MAX_PRICE:.0%}")
    log.info(f"Agresividad: +${PRICE_AGGRESSION:.2f}")
    log.info(f"Limpieza stale: >{ORDER_MAX_AGE_HOURS}h")
    log.info("=" * 65)

    if client is None:
        log.error("Cliente no autenticado. Saltando ciclo.")
        send_telegram("❌ <b>Error:</b> cliente no autenticado. Saltando ciclo.")
        bot_state["running"] = False
        return

    # ---- PASO 0: LIMPIAR ÓRDENES STALE ----
    log.info("[0/6] Limpiando órdenes stale...")
    open_orders = get_open_orders(client)
    cancelled_count = clean_stale_orders(client, open_orders, ORDER_MAX_AGE_HOURS)
    log.info(f"       {cancelled_count} órdenes stale canceladas")

    if cancelled_count > 0:
        open_orders = get_open_orders(client)
    open_token_ids = get_order_token_ids(open_orders)
    log.info(f"       {len(open_token_ids)} órdenes activas restantes")

    # ---- PASO 1: Mercados ----
    log.info("[1/6] Obteniendo mercados...")
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=30&order=volume24hr&ascending=false"
        )
    except Exception as e:
        log.error(f"Error al obtener mercados: {e}")
        events = []

    all_markets = []
    for event in events:
        for m in event.get("markets", []):
            all_markets.append(m)
    log.info(f"       {len(all_markets)} mercados encontrados")

    # ---- PASO 2: Parsear + filtro de precio ----
    log.info("[2/6] Parseando preguntas + filtro de precio...")
    candidates = []
    filtered_price_count = 0

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)
        if not parsed or not parsed["date_str"]:
            continue

        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            continue

        try:
            market_date = date.fromisoformat(date_iso)
            days_ahead = (market_date - date.today()).days
        except ValueError:
            continue

        if days_ahead < MIN_DAYS_AHEAD or days_ahead > MAX_DAYS_AHEAD:
            continue

        prices_raw = market.get("outcomePrices", "[]")
        outcomes_raw = market.get("outcomes", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except (json.JSONDecodeError, TypeError):
            continue

        if not prices:
            continue

        clob_ids_raw = market.get("clobTokenIds", "[]")
        try:
            clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        except (json.JSONDecodeError, TypeError):
            clob_ids = []

        if not clob_ids or len(clob_ids) < 2:
            continue

        mkt_prob_yes = float(prices[0])

        if mkt_prob_yes < MIN_PRICE or mkt_prob_yes > MAX_PRICE:
            mkt_prob_no = 1.0 - mkt_prob_yes
            if mkt_prob_no < MIN_PRICE or mkt_prob_no > MAX_PRICE:
                filtered_price_count += 1
                continue

        liquidity = float(market.get("liquidity", 0))
        if liquidity < MIN_LIQUIDITY:
            continue

        parsed["question"] = question
        parsed["date_iso"] = date_iso
        parsed["days_ahead"] = days_ahead
        parsed["mkt_prob_yes"] = mkt_prob_yes
        parsed["mkt_prob_no"] = 1.0 - mkt_prob_yes
        parsed["volume_24h"] = float(market.get("volume24hr", 0))
        parsed["liquidity"] = liquidity
        parsed["token_id_yes"] = clob_ids[0]
        parsed["token_id_no"] = clob_ids[1]
        candidates.append(parsed)

    log.info(f"       {len(candidates)} candidatos")
    if filtered_price_count > 0:
        log.info(f"       {filtered_price_count} filtrados por precio (<{MIN_PRICE:.0%} o >{MAX_PRICE:.0%})")

    # ---- PASO 3: Previsiones ----
    log.info("[3/6] Obteniendo previsiones...")
    cities_needed = set(c["city"] for c in candidates)
    forecast_cache = {}

    for city in sorted(cities_needed):
        station = RESOLUTION_STATIONS.get(city)
        if station:
            lat, lon = station["lat"], station["lon"]
        else:
            coords = get_coordinates_fallback(city)
            if coords:
                lat, lon = coords
            else:
                log.warning(f"No se encontraron coordenadas para {city}")
                continue

        forecast_cache[city] = get_forecast(lat, lon)
        label = station["name"] if station else "fallback"
        log.info(f"       {city} ({label}): OK")

    # ---- PASO 4: Calcular edge ----
    log.info("[4/6] Calculando edge...")
    trades = []
    skipped_duplicates = 0

    for c in candidates:
        city = c["city"]
        if city not in forecast_cache:
            continue
        if c["date_iso"] not in forecast_cache[city]:
            continue

        forecast_day = forecast_cache[city][c["date_iso"]]
        forecast_max = forecast_day["temp_max"]

        threshold = c["temp_threshold"]
        if c["unit"] == "F":
            threshold_c = (threshold - 32) * 5 / 9
        else:
            threshold_c = float(threshold)

        our_prob_yes = estimate_prob(
            forecast_max, threshold_c, c["condition"], c["days_ahead"]
        )
        our_prob_no = 1.0 - our_prob_yes

        edge_yes = our_prob_yes - c["mkt_prob_yes"]
        edge_no = our_prob_no - c["mkt_prob_no"]

        if edge_yes > edge_no and edge_yes > 0:
            side = "YES"
            our_prob = our_prob_yes
            mkt_price = c["mkt_prob_yes"]
            edge = edge_yes
            token_id = c["token_id_yes"]
        elif edge_no > 0:
            side = "NO"
            our_prob = our_prob_no
            mkt_price = c["mkt_prob_no"]
            edge = edge_no
            token_id = c["token_id_no"]
        else:
            continue

        edge_pct = edge * 100
        if edge_pct < MIN_EDGE:
            continue

        if token_id in open_token_ids:
            skipped_duplicates += 1
            continue

        position = calculate_position(BANKROLL, our_prob, mkt_price)
        if not position:
            continue

        trades.append({
            "question": c["question"],
            "city": city,
            "date": c["date_iso"],
            "days_ahead": c["days_ahead"],
            "forecast_max": forecast_max,
            "threshold": threshold,
            "unit": c["unit"],
            "condition": c["condition"],
            "side": side,
            "our_prob": round(our_prob * 100, 1),
            "mkt_price": round(mkt_price * 100, 1),
            "edge_pct": round(edge_pct, 1),
            "position": position,
            "volume_24h": c["volume_24h"],
            "liquidity": c["liquidity"],
            "station": RESOLUTION_STATIONS.get(city, {}).get("name", "?"),
            "token_id": token_id,
        })

    trades.sort(key=lambda x: x["position"]["expected_value"], reverse=True)

    if skipped_duplicates > 0:
        log.info(f"       {skipped_duplicates} mercados saltados (ya hay orden abierta)")

    # Actualizar estado compartido
    bot_state["last_opportunities"] = len(trades)

    # ---- PASO 5: Presupuesto global + plan ----
    max_budget = BANKROLL * MAX_EXPOSURE_PCT
    budget_remaining = max_budget
    selected_trades = []

    for t in trades:
        pos = t["position"]
        if pos["amount"] <= budget_remaining:
            budget_remaining -= pos["amount"]
            t["selected"] = True
            selected_trades.append(t)
        else:
            if budget_remaining >= MIN_BET:
                reduced_amount = round(budget_remaining, 2)
                aggressive_price = pos.get("aggressive_price", t["mkt_price"] / 100)
                shares = reduced_amount / aggressive_price
                profit = round(shares * (1.0 - aggressive_price), 2)
                loss = round(reduced_amount, 2)
                our_prob_decimal = t["our_prob"] / 100
                ev = round(our_prob_decimal * profit - (1 - our_prob_decimal) * loss, 2)

                t["position"] = {
                    "fraction_pct": round(reduced_amount / BANKROLL * 100, 2),
                    "amount": reduced_amount,
                    "shares": round(shares, 2),
                    "profit_if_win": profit,
                    "loss_if_lose": loss,
                    "expected_value": ev,
                    "aggressive_price": aggressive_price,
                    "market_price": t["mkt_price"] / 100,
                }
                budget_remaining = 0
                selected_trades.append(t)

    log.info("[5/6] Generando plan de operaciones...")
    log.info(f"       {len(trades)} oportunidades detectadas")
    log.info(f"       {len(selected_trades)} seleccionadas (presupuesto: ${max_budget:.2f})")
    log.info(f"       {len(trades) - len(selected_trades)} descartadas (sin presupuesto)")

    # ---- IMPRIMIR PLAN ----
    print()
    print("=" * 65)
    print("  PLAN DE OPERACIONES")
    print("=" * 65)

    if not selected_trades:
        print()
        print("  No hay operaciones recomendadas ahora.")
        print()
    else:
        total_exposure = 0
        total_ev = 0

        print()
        for i, t in enumerate(selected_trades):
            pos = t["position"]
            total_exposure += pos["amount"]
            total_ev += pos["expected_value"]
            confidence = "ALTA" if t["days_ahead"] <= 1 else "MEDIA"
            unit = "°" + t["unit"]

            agg_price = pos.get("aggressive_price", t["mkt_price"] / 100)
            mkt_price_display = t["mkt_price"] / 100

            print(f"  ┌─ Operación #{i + 1} ──────────────────────────────")
            print(f"  │ {t['question']}")
            print(f"  │")
            print(f"  │ Acción:    COMPRAR {t['side']} a ${agg_price:.2f} (mercado: ${mkt_price_display:.2f})")
            print(f"  │ Cantidad:  ${pos['amount']:.2f} ({pos['fraction_pct']}% del bankroll)")
            print(f"  │ Shares:    {pos['shares']:.1f}")
            print(f"  │")
            print(f"  │ Edge:      {t['edge_pct']:.1f}% | Confianza: {confidence}")
            print(f"  │ Previsión: {t['forecast_max']:.1f}°C  |  Umbral: {t['threshold']}{unit}")
            print(f"  │ Nuestro:   {t['our_prob']}%  |  Mercado: {t['mkt_price']}%")
            print(f"  │")
            print(f"  │ Si ganas:  +${pos['profit_if_win']:.2f}")
            print(f"  │ Si pierdes: -${pos['loss_if_lose']:.2f}")
            print(f"  │ EV:        ${pos['expected_value']:+.2f}")
            print(f"  │")
            print(f"  │ Liquidez: ${t['liquidity']:,.0f} | Vol 24h: ${t['volume_24h']:,.0f}")
            print(f"  │ Estación: {t['station']} | Fecha: {t['date']}")
            print(f"  │ Token ID:  {t['token_id'][:16]}...")
            print(f"  └────────────────────────────────────────────")
            print()

        print("=" * 65)
        print("  RESUMEN DEL PLAN")
        print("=" * 65)
        print(f"  Operaciones:      {len(selected_trades)} de {len(trades)} oportunidades")
        print(f"  Bankroll:         ${BANKROLL:.2f}")
        print(f"  Presupuesto:      ${max_budget:.2f} ({MAX_EXPOSURE_PCT*100:.0f}% del bankroll)")
        print(f"  Exposición total: ${total_exposure:.2f} ({total_exposure/BANKROLL*100:.1f}%)")
        print(f"  Capital libre:    ${BANKROLL - total_exposure:.2f}")
        print(f"  EV total:         ${total_ev:+.2f}")
        print(f"  Agresividad:      +${PRICE_AGGRESSION:.2f} por orden")
        print()
        print(f"  Modo: {mode_label}")
        print("=" * 65)

    # ---- PASO 6: EJECUCIÓN ----
    if not selected_trades:
        log.info("Sin operaciones que ejecutar.")
        bot_state["last_orders_placed"] = 0
    else:
        print()
        if DRY_RUN:
            print("  [DRY RUN] Las siguientes órdenes se SIMULARÍAN:")
        else:
            print("  ⚠️  EJECUTANDO ÓRDENES REALES...")
        print()

        results = []
        for i, trade in enumerate(selected_trades):
            result = execute_trade(client, trade, dry_run=DRY_RUN)
            results.append(result)

            status_icon = "✓" if result["ok"] else "✗"
            print(
                f"  {status_icon} #{i+1} {trade['city']} {trade['side']} "
                f"${trade['position']['amount']:.2f} → {result['msg']}"
            )

            log.info(
                f"Trade #{i+1}: {trade['city']} | {trade['side']} | "
                f"${trade['position']['amount']:.2f} | edge={trade['edge_pct']}% | "
                f"price={trade['position'].get('aggressive_price', '?')} | "
                f"order_id={result['order_id']} | ok={result['ok']}"
            )

            # Alerta Telegram solo en modo real
            if not DRY_RUN:
                icono = "✅" if result["ok"] else "❌"
                send_telegram(
                    f"{icono} <b>Orden ejecutada</b>\n"
                    f"Ciudad: {trade['city']} | {trade['side']}\n"
                    f"Cantidad: ${trade['position']['amount']:.2f} "
                    f"({trade['position']['shares']:.1f} shares @ ${trade['position'].get('aggressive_price', 0):.2f})\n"
                    f"Edge: {trade['edge_pct']}% | EV: ${trade['position']['expected_value']:+.2f}\n"
                    f"Fecha mercado: {trade['date']}\n"
                    f"Estado: {result['msg']}"
                )

        ok_count = sum(1 for r in results if r["ok"])
        bot_state["last_orders_placed"] = ok_count

        print()
        print(f"  Resultado: {ok_count}/{len(results)} órdenes OK")
        print()

        # Resumen final por Telegram en modo real
        if not DRY_RUN:
            send_telegram(
                f"📊 <b>Ciclo completado</b>\n"
                f"Órdenes: {ok_count}/{len(results)} OK\n"
                f"Bankroll: ${BANKROLL:.2f} | Modo: REAL"
            )

    bot_state["cycle_count"] += 1
    bot_state["running"] = False
    log.info("Ciclo finalizado.")


# =============================================================
# SCHEDULER ESTRATÉGICO
# =============================================================

def get_next_run_time():
    """
    Calcula cuándo toca la próxima ejecución.

    Mira las horas programadas (SCHEDULE_HOURS_UTC), busca la próxima
    que aún no ha pasado hoy. Si todas las de hoy ya pasaron,
    devuelve la primera de mañana.

    Ejemplo con schedule [8, 16, 23]:
      - Son las 10:00 UTC → próxima: 16:00 UTC hoy
      - Son las 23:30 UTC → próxima: 08:00 UTC mañana
    """
    now = datetime.now(timezone.utc)
    hours_sorted = sorted(SCHEDULE_HOURS_UTC)

    for hour in hours_sorted:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate

    # Todas las horas de hoy ya pasaron → primera de mañana
    tomorrow = now + timedelta(days=1)
    first_hour = hours_sorted[0]
    return tomorrow.replace(hour=first_hour, minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    log.info("=" * 65)
    log.info("POLYMARKET BOT v6 — Scheduler estratégico + Telegram")
    log.info(f"Schedule: {sorted(SCHEDULE_HOURS_UTC)} UTC")
    log.info(f"Modo: {'DRY RUN' if DRY_RUN else 'REAL'}")
    log.info("=" * 65)

    # ---- Autenticación (una sola vez) ----
    clob_client = setup_client()
    if clob_client is None:
        log.error("No se pudo autenticar. El bot arranca pero no podrá operar.")
        send_telegram("❌ <b>Error de autenticación</b> al arrancar. Revisa las claves.")

    # ---- Arrancar hilo de Telegram ----
    # daemon=True significa que el hilo muere automáticamente cuando
    # el programa principal termina. Sin esto, el programa no cerraría nunca.
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        telegram_thread = threading.Thread(
            target=telegram_polling_loop,
            daemon=True,
            name="TelegramPoller",
        )
        telegram_thread.start()
        log.info("Hilo de Telegram polling: arrancado")
    else:
        log.warning("Telegram no configurado — comandos desactivados")

    # ---- Alerta de arranque ----
    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule_display = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    send_telegram(
        f"🤖 <b>Bot arrancado (v6)</b>\n"
        f"Modo: {modo} | Bankroll: ${BANKROLL:.2f}\n"
        f"Schedule: {schedule_display} UTC\n"
        f"\n"
        f"Usa los botones para controlar el bot:",
        with_menu=True,
    )

    # ---- Primer ciclo inmediato ----
    log.info("Ejecutando primer ciclo al arrancar...")
    try:
        main(clob_client)
    except Exception as e:
        log.error(f"Error en primer ciclo: {e}")
        send_telegram(f"❌ <b>Error en primer ciclo</b>\n<code>{str(e)[:200]}</code>")

    # ---- Bucle del scheduler ----
    while True:
        next_run = get_next_run_time()
        bot_state["next_run"] = next_run

        time_until = next_run - datetime.now(timezone.utc)
        hours_until = time_until.total_seconds() / 3600
        log.info(
            f"Próximo ciclo: {next_run.strftime('%H:%M UTC')} "
            f"(en {hours_until:.1f}h). Esperando..."
        )

        # ---- Espera inteligente ----
        # En vez de un time.sleep() largo, esperamos en bloques de 30s.
        # Cada 30 segundos comprobamos:
        #   1. ¿Ya es la hora? → ejecutar ciclo
        #   2. ¿Alguien mandó /forzar? → ejecutar ciclo inmediato
        # force_event.wait(30) duerme 30 segundos, PERO se despierta
        # inmediatamente si alguien llama force_event.set().
        while datetime.now(timezone.utc) < next_run:
            was_forced = force_event.wait(timeout=30)
            if was_forced:
                force_event.clear()
                log.info("⚡ Ciclo forzado desde Telegram")
                break

        # ---- Ejecutar ciclo ----
        try:
            main(clob_client)
        except Exception as e:
            log.error(f"Error inesperado en ciclo: {e}")
            send_telegram(f"❌ <b>Error inesperado</b>\n<code>{str(e)[:200]}</code>")
