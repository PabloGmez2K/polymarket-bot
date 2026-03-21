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
# bot.py — Bot de Polymarket v6.1 (Dashboard Telegram completo)
# Sesión 7: Todo controlable desde el móvil
# =============================================================
#
# Cambios respecto a v6:
#   - /cartera: balance real + posiciones abiertas desde Telegram
#   - /modo: activa/desactiva DRY_RUN desde Telegram (con confirmación)
#   - Órdenes mejoradas: ciudad, pregunta, shares, no solo precio
#   - Menú reorganizado: más intuitivo
#   - bot_state guarda datos del último ciclo para consultas
# =============================================================


# =============================================================
# CONFIGURACIÓN
# =============================================================

# DRY_RUN ahora es mutable — se puede cambiar desde Telegram.
# Si Railway reinicia, vuelve al valor de la variable de entorno.
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
# Open-Meteo actualiza modelos a las 00, 06, 12, 18 UTC.
# Traders de Polymarket más activos en horario EEUU (14-22 UTC).
#
#   08:00 UTC (09:00 España) → Datos del modelo 06 UTC
#   16:00 UTC (17:00 España) → Datos del modelo 12 UTC, EEUU activo
#   23:00 UTC (00:00 España) → Datos del modelo 18 UTC, última pasada
#
# Configurable con SCHEDULE_HOURS_UTC="8,16,23" en Railway.
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

bot_state = {
    "next_run": None,
    "last_run": None,
    "last_orders_placed": 0,
    "last_opportunities": 0,
    "running": False,
    "cycle_count": 0,
    "last_trades": [],
}

force_event = threading.Event()
clob_client = None


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

MENU_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📊 Estado", "callback_data": "estado"},
            {"text": "💰 Cartera", "callback_data": "cartera"},
        ],
        [
            {"text": "📋 Órdenes", "callback_data": "ordenes"},
            {"text": "⏰ Siguiente", "callback_data": "siguiente"},
        ],
        [
            {"text": "🚀 Forzar ciclo", "callback_data": "forzar"},
            {"text": "⚡ Modo", "callback_data": "modo"},
        ],
    ]
}


def send_telegram(mensaje, with_menu=False, custom_keyboard=None):
    """
    Manda un mensaje al móvil via Telegram.

    with_menu=True → botones del menú principal
    custom_keyboard → botones personalizados (ej: confirmación Sí/No)
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML",
        }
        if custom_keyboard:
            payload["reply_markup"] = custom_keyboard
        elif with_menu:
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
    """Responde a un botón pulsado (quita el spinner)."""
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
    """📊 Estado general del bot."""
    global DRY_RUN
    modo = "🔴 REAL" if not DRY_RUN else "🟡 DRY RUN"
    running = "🔄 Ejecutando..." if bot_state["running"] else "💤 Esperando"

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

    schedule_display = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    msg = (
        f"📊 <b>Estado del Bot</b>\n"
        f"\n"
        f"Modo: {modo}\n"
        f"Bankroll: <b>${BANKROLL:.2f}</b>\n"
        f"Estado: {running}\n"
        f"\n"
        f"Última ejecución: {last_str}\n"
        f"Próxima: {next_str}\n"
        f"Ciclos completados: {bot_state['cycle_count']}\n"
        f"\n"
        f"Último ciclo:\n"
        f"  Oportunidades: {bot_state['last_opportunities']}\n"
        f"  Órdenes colocadas: {bot_state['last_orders_placed']}\n"
        f"\n"
        f"⏰ Schedule: {schedule_display} UTC"
    )
    send_telegram(msg, with_menu=True)


def cmd_cartera():
    """
    💰 Muestra cartera: posiciones abiertas con PnL.

    Consulta la Gamma API con tu dirección FUNDER para ver
    en qué mercados tienes shares y cómo van.
    """
    funder = os.getenv("FUNDER", "")
    if not funder:
        send_telegram("❌ No hay FUNDER configurado.", with_menu=True)
        return

    # ---- Obtener posiciones desde Gamma API ----
    try:
        url = (
            f"{GAMMA_URL}/positions"
            f"?user={funder.lower()}"
            f"&limit=20"
            f"&sortBy=value"
            f"&sortOrder=desc"
        )
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "polymarket-bot/0.6")
        resp = urllib.request.urlopen(req, timeout=15)
        positions = json.loads(resp.read())
    except Exception as e:
        send_telegram(f"❌ Error al consultar cartera: {e}", with_menu=True)
        return

    if not positions:
        send_telegram(
            "💰 <b>Cartera</b>\n\nNo tienes posiciones abiertas.",
            with_menu=True,
        )
        return

    # ---- Calcular totales ----
    total_invested = 0
    total_current_value = 0
    lines = []

    for i, pos in enumerate(positions):
        # Gamma API fields — parseamos con fallbacks robustos
        market_question = pos.get("title", pos.get("question", ""))
        if not market_question:
            # Intentar sacar del mercado anidado
            market_obj = pos.get("market", {})
            market_question = market_obj.get("question", "Mercado desconocido")

        outcome = pos.get("outcome", pos.get("side", "?"))
        size = float(pos.get("size", pos.get("shares", 0)))
        avg_price = float(pos.get("avgPrice", pos.get("avg_price", 0)))
        cur_price = float(pos.get("curPrice", pos.get("cur_price", pos.get("price", 0))))

        invested = size * avg_price
        current = size * cur_price

        total_invested += invested
        total_current_value += current

        pnl = current - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0
        pnl_icon = "🟢" if pnl >= 0 else "🔴"

        q_short = market_question[:50] + "..." if len(market_question) > 50 else market_question

        lines.append(
            f"{i+1}. {pnl_icon} <b>{outcome}</b>\n"
            f"   {q_short}\n"
            f"   {size:.1f} shares @ ${avg_price:.2f} → ${cur_price:.2f}\n"
            f"   Invertido: ${invested:.2f} | Valor: ${current:.2f}\n"
            f"   PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%)"
        )

    total_pnl = total_current_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    total_icon = "🟢" if total_pnl >= 0 else "🔴"

    header = (
        f"💰 <b>Cartera</b>\n"
        f"\n"
        f"Posiciones: {len(positions)}\n"
        f"Invertido: ${total_invested:.2f}\n"
        f"Valor actual: ${total_current_value:.2f}\n"
        f"PnL total: {total_icon} ${total_pnl:+.2f} ({total_pnl_pct:+.1f}%)\n"
        f"\n"
        f"{'─' * 30}\n"
    )

    msg = header + "\n".join(lines)

    if len(msg) > 4000:
        msg = msg[:3990] + "\n..."

    send_telegram(msg, with_menu=True)


def cmd_ordenes():
    """📋 Órdenes abiertas (pendientes de llenarse)."""
    global clob_client

    if bot_state["running"]:
        send_telegram("🔄 Ciclo en ejecución, prueba en unos segundos...", with_menu=True)
        return

    if clob_client is None:
        send_telegram("❌ Cliente no autenticado.", with_menu=True)
        return

    try:
        orders = get_open_orders(clob_client)
    except Exception as e:
        send_telegram(f"❌ Error: {e}", with_menu=True)
        return

    if not orders:
        send_telegram("📋 <b>Órdenes pendientes:</b> ninguna", with_menu=True)
        return

    # ---- Enriquecer con datos del mercado ----
    token_to_market = {}
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false&limit=30"
        )
        for event in events:
            for m in event.get("markets", []):
                clob_raw = m.get("clobTokenIds", "[]")
                try:
                    clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
                except (json.JSONDecodeError, TypeError):
                    clob_ids = []
                question = m.get("question", "?")
                for idx, tid in enumerate(clob_ids):
                    side_label = "YES" if idx == 0 else "NO"
                    token_to_market[tid] = {"question": question, "side": side_label}
    except Exception:
        pass

    lines = [f"📋 <b>Órdenes pendientes: {len(orders)}</b>\n"]

    for i, order in enumerate(orders):
        price = order.get("price", "?")
        size = order.get("original_size", order.get("size", "?"))
        side = order.get("side", "?")
        asset_id = order.get("asset_id", "")

        # Edad
        created_raw = order.get("created_at", "")
        age_str = ""
        if created_raw:
            try:
                if isinstance(created_raw, (int, float)):
                    created = datetime.fromtimestamp(created_raw, tz=timezone.utc)
                else:
                    created = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - created).total_seconds() / 3600
                age_str = f" | ⏱ {age_h:.1f}h"
            except (ValueError, TypeError, OSError):
                pass

        market_info = token_to_market.get(asset_id, {})
        question = market_info.get("question", "")
        token_side = market_info.get("side", "")

        if question:
            q_short = question[:55] + "..." if len(question) > 55 else question
            lines.append(
                f"\n{i+1}. {side} {token_side} @ ${price}\n"
                f"   {q_short}\n"
                f"   Shares: {size}{age_str}"
            )
        else:
            lines.append(
                f"\n{i+1}. {side} @ ${price}{age_str}\n"
                f"   Token: {asset_id[:20]}..."
            )

    send_telegram("\n".join(lines), with_menu=True)


def cmd_siguiente():
    """⏰ Cuánto falta para el próximo ciclo."""
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
        f"Schedule diario: {schedule_display} UTC\n"
        f"\n"
        f"💡 Toca 🚀 para ejecutar ahora"
    )
    send_telegram(msg, with_menu=True)


def cmd_forzar():
    """🚀 Ejecuta un ciclo inmediatamente."""
    if bot_state["running"]:
        send_telegram("🔄 Ya hay un ciclo en ejecución.", with_menu=True)
        return

    send_telegram("🚀 <b>Ciclo forzado</b>\nDespertando al scheduler...")
    force_event.set()


def cmd_modo():
    """
    ⚡ Cambiar entre DRY RUN y REAL.

    Primer toque: muestra estado actual + confirmación.
    Segundo toque: cambia el modo.

    ¿Por qué dos toques? Porque activar MODO REAL
    gasta dinero de verdad. No queremos toques accidentales.
    """
    global DRY_RUN

    if DRY_RUN:
        msg = (
            f"⚡ <b>Modo actual: 🟡 DRY RUN</b>\n"
            f"(Las órdenes se simulan)\n"
            f"\n"
            f"¿Activar <b>MODO REAL</b>?\n"
            f"Se usarán los ${BANKROLL:.2f} del bankroll.\n"
            f"\n"
            f"⚠️ Esto es dinero real."
        )
        kb = {
            "inline_keyboard": [[
                {"text": "✅ Sí, activar REAL", "callback_data": "confirmar_real"},
                {"text": "❌ Cancelar", "callback_data": "cancelar_modo"},
            ]]
        }
    else:
        msg = (
            f"⚡ <b>Modo actual: 🔴 REAL</b>\n"
            f"(Las órdenes son reales)\n"
            f"\n"
            f"¿Volver a <b>DRY RUN</b>?"
        )
        kb = {
            "inline_keyboard": [[
                {"text": "🟡 Sí, volver a DRY RUN", "callback_data": "confirmar_dry"},
                {"text": "❌ Cancelar", "callback_data": "cancelar_modo"},
            ]]
        }

    send_telegram(msg, custom_keyboard=kb)


def cmd_confirmar_real():
    """Confirmación: activar modo real."""
    global DRY_RUN
    DRY_RUN = False
    log.info("MODO REAL activado desde Telegram")
    send_telegram(
        f"🔴 <b>MODO REAL ACTIVADO</b>\n"
        f"\n"
        f"Las órdenes son reales a partir de ahora.\n"
        f"Bankroll: ${BANKROLL:.2f}\n"
        f"\n"
        f"⚠️ Si Railway reinicia, volverá al valor\n"
        f"de DRY_RUN en Variables de Railway.\n"
        f"Para hacerlo permanente: Railway → Variables → DRY_RUN=false",
        with_menu=True,
    )


def cmd_confirmar_dry():
    """Confirmación: volver a dry run."""
    global DRY_RUN
    DRY_RUN = True
    log.info("DRY RUN activado desde Telegram")
    send_telegram(
        f"🟡 <b>DRY RUN ACTIVADO</b>\n"
        f"\n"
        f"Las órdenes se simularán.",
        with_menu=True,
    )


def cmd_cancelar_modo():
    """No cambiar nada."""
    modo = "🟡 DRY RUN" if DRY_RUN else "🔴 REAL"
    send_telegram(f"Sin cambios. Modo: {modo}", with_menu=True)


# Mapa de comandos
COMMANDS = {
    "estado": cmd_estado,
    "cartera": cmd_cartera,
    "ordenes": cmd_ordenes,
    "siguiente": cmd_siguiente,
    "forzar": cmd_forzar,
    "modo": cmd_modo,
    "confirmar_real": cmd_confirmar_real,
    "confirmar_dry": cmd_confirmar_dry,
    "cancelar_modo": cmd_cancelar_modo,
}


# =============================================================
# TELEGRAM — RECEPCIÓN (POLLING)
# =============================================================

def is_authorized(chat_id):
    """Solo responde a tu chat_id."""
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def handle_telegram_update(update):
    """Procesa un update de Telegram (botón o texto)."""

    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        chat_id = cb.get("message", {}).get("chat", {}).get("id", 0)
        command = cb.get("data", "")

        if not is_authorized(chat_id):
            answer_callback_query(cb_id, "No autorizado")
            return

        answer_callback_query(cb_id)

        if command in COMMANDS:
            try:
                COMMANDS[command]()
            except Exception as e:
                log.warning(f"Error en comando '{command}': {e}")
                send_telegram(f"❌ Error: {e}", with_menu=True)
        return

    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id", 0)
        text = msg.get("text", "").strip().lower()

        if not is_authorized(chat_id):
            return

        if text.startswith("/"):
            text = text[1:]
        if "@" in text:
            text = text.split("@")[0]

        if text in COMMANDS:
            try:
                COMMANDS[text]()
            except Exception as e:
                log.warning(f"Error en comando '{text}': {e}")
                send_telegram(f"❌ Error: {e}", with_menu=True)
        else:
            send_telegram(
                "🤖 <b>Bot Polymarket</b>\n\n"
                "Toca un botón:",
                with_menu=True,
            )


def telegram_polling_loop():
    """
    Hilo que escucha Telegram (long polling).
    Pregunta cada 30s si hay mensajes nuevos.
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
                    log.warning(f"Error procesando update: {e}")

        except Exception as e:
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
# FUNCIONES: GESTIÓN DE ÓRDENES
# =============================================================

def get_open_orders(client):
    try:
        orders = client.get_orders()
        open_orders = []
        for order in orders:
            status = order.get("status", "").upper()
            if status in ("LIVE", "ACTIVE", "OPEN"):
                open_orders.append(order)
        log.info(f"Órdenes abiertas: {len(open_orders)}")
        return open_orders
    except Exception as e:
        log.warning(f"Error al obtener órdenes: {e}")
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
                f"Cancelando stale: {order_id[:16]}... ({age_hours:.1f}h)"
            )
            try:
                client.cancel(order_id)
                cancelled += 1
            except Exception as e:
                log.warning(f"  Error al cancelar: {e}")

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
        f"{trade['side']} {size}sh × ${price:.2f} "
        f"| {trade['city']} {trade['date']} "
        f"| token {token_id[:12]}..."
    )

    if dry_run:
        return {"ok": True, "order_id": "DRY_RUN", "msg": "Simulado"}

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
    """Ejecuta un ciclo completo del bot."""
    today_str = date.today().isoformat()
    mode_label = "DRY RUN" if DRY_RUN else "MODO REAL"

    bot_state["running"] = True
    bot_state["last_run"] = datetime.now(timezone.utc)

    log.info("=" * 65)
    log.info(f"POLYMARKET WEATHER BOT v6.1  |  {today_str}")
    log.info(f"Modo: {mode_label} | Bankroll: ${BANKROLL:.2f}")
    log.info("=" * 65)

    if client is None:
        log.error("Cliente no autenticado. Saltando ciclo.")
        send_telegram("❌ Cliente no autenticado. Saltando ciclo.")
        bot_state["running"] = False
        return

    # ---- PASO 0: LIMPIAR STALE ----
    log.info("[0/6] Limpiando stale...")
    open_orders = get_open_orders(client)
    cancelled = clean_stale_orders(client, open_orders, ORDER_MAX_AGE_HOURS)
    if cancelled > 0:
        log.info(f"       {cancelled} canceladas")
        open_orders = get_open_orders(client)
    open_token_ids = get_order_token_ids(open_orders)

    # ---- PASO 1: Mercados ----
    log.info("[1/6] Mercados...")
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=30&order=volume24hr&ascending=false"
        )
    except Exception as e:
        log.error(f"Error mercados: {e}")
        events = []

    all_markets = []
    for event in events:
        for m in event.get("markets", []):
            all_markets.append(m)
    log.info(f"       {len(all_markets)} mercados")

    # ---- PASO 2: Parsear + filtro ----
    log.info("[2/6] Parseando...")
    candidates = []

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
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
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

    # ---- PASO 3: Previsiones ----
    log.info("[3/6] Previsiones...")
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
                continue

        forecast_cache[city] = get_forecast(lat, lon)
        label = station["name"] if station else "fallback"
        log.info(f"       {city} ({label}): OK")

    # ---- PASO 4: Edge ----
    log.info("[4/6] Calculando edge...")
    trades = []
    skipped_dup = 0

    for c in candidates:
        city = c["city"]
        if city not in forecast_cache:
            continue
        if c["date_iso"] not in forecast_cache[city]:
            continue

        forecast_day = forecast_cache[city][c["date_iso"]]
        forecast_max = forecast_day["temp_max"]

        threshold = c["temp_threshold"]
        threshold_c = (threshold - 32) * 5 / 9 if c["unit"] == "F" else float(threshold)

        our_prob_yes = estimate_prob(forecast_max, threshold_c, c["condition"], c["days_ahead"])
        our_prob_no = 1.0 - our_prob_yes

        edge_yes = our_prob_yes - c["mkt_prob_yes"]
        edge_no = our_prob_no - c["mkt_prob_no"]

        if edge_yes > edge_no and edge_yes > 0:
            side, our_prob, mkt_price, edge, token_id = "YES", our_prob_yes, c["mkt_prob_yes"], edge_yes, c["token_id_yes"]
        elif edge_no > 0:
            side, our_prob, mkt_price, edge, token_id = "NO", our_prob_no, c["mkt_prob_no"], edge_no, c["token_id_no"]
        else:
            continue

        edge_pct = edge * 100
        if edge_pct < MIN_EDGE:
            continue

        if token_id in open_token_ids:
            skipped_dup += 1
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

    if skipped_dup > 0:
        log.info(f"       {skipped_dup} duplicados saltados")

    bot_state["last_opportunities"] = len(trades)

    # ---- PASO 5: Presupuesto ----
    max_budget = BANKROLL * MAX_EXPOSURE_PCT
    budget_remaining = max_budget
    selected_trades = []

    for t in trades:
        pos = t["position"]
        if pos["amount"] <= budget_remaining:
            budget_remaining -= pos["amount"]
            selected_trades.append(t)
        else:
            if budget_remaining >= MIN_BET:
                reduced = round(budget_remaining, 2)
                agg_p = pos.get("aggressive_price", t["mkt_price"] / 100)
                shares = reduced / agg_p
                profit = round(shares * (1.0 - agg_p), 2)
                prob_d = t["our_prob"] / 100
                ev = round(prob_d * profit - (1 - prob_d) * reduced, 2)

                t["position"] = {
                    "fraction_pct": round(reduced / BANKROLL * 100, 2),
                    "amount": reduced,
                    "shares": round(shares, 2),
                    "profit_if_win": profit,
                    "loss_if_lose": reduced,
                    "expected_value": ev,
                    "aggressive_price": agg_p,
                    "market_price": t["mkt_price"] / 100,
                }
                budget_remaining = 0
                selected_trades.append(t)

    log.info(f"[5/6] {len(trades)} oportunidades | {len(selected_trades)} seleccionadas")

    # ---- Log plan ----
    if selected_trades:
        for i, t in enumerate(selected_trades):
            pos = t["position"]
            log.info(
                f"  #{i+1} {t['city']} {t['side']} | "
                f"${pos['amount']:.2f} × {pos['shares']:.1f}sh | "
                f"edge={t['edge_pct']}% | EV=${pos['expected_value']:+.2f}"
            )

    # ---- PASO 6: EJECUCIÓN ----
    if not selected_trades:
        log.info("Sin operaciones.")
        bot_state["last_orders_placed"] = 0
        bot_state["last_trades"] = []
    else:
        results = []
        for i, trade in enumerate(selected_trades):
            result = execute_trade(client, trade, dry_run=DRY_RUN)
            results.append(result)

            log.info(
                f"Trade #{i+1}: {trade['city']} {trade['side']} | "
                f"${trade['position']['amount']:.2f} | "
                f"ok={result['ok']} | id={result['order_id']}"
            )

            if not DRY_RUN:
                icono = "✅" if result["ok"] else "❌"
                send_telegram(
                    f"{icono} <b>Orden ejecutada</b>\n"
                    f"{trade['city']} | {trade['side']}\n"
                    f"${trade['position']['amount']:.2f} "
                    f"({trade['position']['shares']:.1f}sh "
                    f"@ ${trade['position'].get('aggressive_price', 0):.2f})\n"
                    f"Edge: {trade['edge_pct']}% | "
                    f"EV: ${trade['position']['expected_value']:+.2f}\n"
                    f"Fecha: {trade['date']}"
                )

        ok_count = sum(1 for r in results if r["ok"])
        bot_state["last_orders_placed"] = ok_count
        bot_state["last_trades"] = selected_trades

        if not DRY_RUN and ok_count > 0:
            send_telegram(
                f"📊 <b>Ciclo completado</b>\n"
                f"Órdenes: {ok_count}/{len(results)} OK\n"
                f"Bankroll: ${BANKROLL:.2f}",
                with_menu=True,
            )

    bot_state["cycle_count"] += 1
    bot_state["running"] = False
    log.info("Ciclo finalizado.")


# =============================================================
# SCHEDULER ESTRATÉGICO
# =============================================================

def get_next_run_time():
    """Próxima hora UTC programada."""
    now = datetime.now(timezone.utc)
    hours_sorted = sorted(SCHEDULE_HOURS_UTC)

    for hour in hours_sorted:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate

    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hours_sorted[0], minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    log.info("=" * 65)
    log.info("POLYMARKET BOT v6.1 — Dashboard Telegram")
    log.info(f"Schedule: {sorted(SCHEDULE_HOURS_UTC)} UTC")
    log.info(f"Modo: {'DRY RUN' if DRY_RUN else 'REAL'}")
    log.info("=" * 65)

    # ---- Autenticación ----
    clob_client = setup_client()
    if clob_client is None:
        log.error("No se pudo autenticar.")
        send_telegram("❌ <b>Error de autenticación</b> al arrancar.")

    # ---- Hilo Telegram ----
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        telegram_thread = threading.Thread(
            target=telegram_polling_loop,
            daemon=True,
            name="TelegramPoller",
        )
        telegram_thread.start()
        log.info("Telegram polling: arrancado")
    else:
        log.warning("Telegram no configurado")

    # ---- Alerta arranque ----
    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule_display = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    send_telegram(
        f"🤖 <b>Bot arrancado (v6.1)</b>\n"
        f"Modo: {modo} | Bankroll: ${BANKROLL:.2f}\n"
        f"Schedule: {schedule_display} UTC",
        with_menu=True,
    )

    # ---- Primer ciclo ----
    log.info("Primer ciclo al arrancar...")
    try:
        main(clob_client)
    except Exception as e:
        log.error(f"Error primer ciclo: {e}")
        send_telegram(f"❌ <b>Error</b>\n<code>{str(e)[:200]}</code>")

    # ---- Bucle scheduler ----
    while True:
        next_run = get_next_run_time()
        bot_state["next_run"] = next_run

        time_until = next_run - datetime.now(timezone.utc)
        log.info(
            f"Próximo: {next_run.strftime('%H:%M UTC')} "
            f"(en {time_until.total_seconds()/3600:.1f}h)"
        )

        while datetime.now(timezone.utc) < next_run:
            was_forced = force_event.wait(timeout=30)
            if was_forced:
                force_event.clear()
                log.info("⚡ Ciclo forzado")
                break

        try:
            main(clob_client)
        except Exception as e:
            log.error(f"Error en ciclo: {e}")
            send_telegram(f"❌ <b>Error</b>\n<code>{str(e)[:200]}</code>")
