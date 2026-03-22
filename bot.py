import urllib.request
import urllib.parse
import json
import re
import math
import os
import sys
import time
import logging
import threading
import subprocess
from datetime import date, datetime, timezone, timedelta

from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

load_dotenv()

# =============================================================
# bot.py v9 — Pipeline de inteligencia de traders integrado
# Sesión 9: Señales de traders + descubrimiento automático
# =============================================================
#
# Nuevo en v9:
#   - Cruza edge con señales de traders tracked (signals.json)
#   - Comando /traders en Telegram
#   - Descubrimiento semanal automático (lunes 08:00 UTC)
#   - Análisis diario de traders (primer ciclo del día)
#   - Decision log anota cuando trader confirma edge
#
# Heredado de v8:
#   - MIN_DAYS_AHEAD = 0, MAX_DAYS_AHEAD = 5
#   - Reintentos automáticos en APIs
# =============================================================


# =============================================================
# CONFIGURACIÓN
# =============================================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))

MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))   # v9: env var, bajado de 10 a 7
MIN_BET = 1.00
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.40
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = 0

MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8

SCHEDULE_HOURS_UTC_STR = os.getenv("SCHEDULE_HOURS_UTC", "8,16,23")
SCHEDULE_HOURS_UTC = [int(h.strip()) for h in SCHEDULE_HOURS_UTC_STR.split(",")]

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

# Decision log — archivo separado con toda la lógica de cada ciclo
# Esto es lo que leerás mañana para entender qué hizo el bot
decision_log = logging.getLogger("decisions")
decision_log.setLevel(logging.INFO)
decision_handler = logging.FileHandler("decisions.log", encoding="utf-8")
decision_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
decision_log.addHandler(decision_handler)
decision_log.propagate = False  # No duplicar en consola


# =============================================================
# ESTADO COMPARTIDO
# =============================================================

bot_state = {
    "next_run": None,
    "last_run": None,
    "last_orders_placed": 0,
    "last_opportunities": 0,
    "running": False,
    "cycle_count": 0,
    "last_trades": [],
    "last_decision_summary": "",
    "last_trader_scan": None,
    "last_trader_analysis": None,
    "last_edge_analysis": [],       # v9: para /logfull
    "last_trader_signals": {},      # v9: para cruce en /logfull
}

force_event = threading.Event()
clob_client = None

# Cache de token_id → info del mercado.
# Se llena cada vez que el bot escanea mercados o coloca órdenes.
# Así cuando consultas /ordenes, sabe a qué mercado pertenece cada token.
known_tokens = {}


# =============================================================
# PIPELINE DE TRADERS (v9)
# =============================================================

def load_trader_signals():
    """
    Lee signals.json generado por trader_analyzer.py.
    Devuelve dict de match_key → lista de señales para cruce rápido.
    Si el archivo no existe o es viejo (>12h), devuelve vacío.
    """
    signals_file = "signals.json"
    if not os.path.exists(signals_file):
        return {}
    try:
        with open(signals_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check freshness
        generated = datetime.fromisoformat(data.get("generated", "2000-01-01T00:00:00+00:00"))
        age_hours = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
        if age_hours > 12:
            return {}
        # Indexar por match_key para cruce O(1)
        index = {}
        for s in data.get("signals", []):
            key = s.get("match_key", "")
            if key:
                if key not in index:
                    index[key] = []
                index[key].append(s)
        return index
    except Exception as e:
        log.warning(f"Error cargando signals.json: {e}")
        return {}


def run_trader_analysis():
    """
    Ejecuta trader_analyzer.py como subproceso.
    Se llama una vez al día (primer ciclo) para actualizar signals.json.
    """
    import subprocess
    try:
        log.info("Ejecutando trader_analyzer.py...")
        result = subprocess.run(
            [sys.executable, "trader_analyzer.py", "--signals"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.info("trader_analyzer.py completado OK")
            bot_state["last_trader_analysis"] = datetime.now(timezone.utc)
            return True
        else:
            log.warning(f"trader_analyzer.py error: {result.stderr[:200]}")
            return False
    except Exception as e:
        log.warning(f"Error ejecutando trader_analyzer.py: {e}")
        return False


def run_trader_discovery():
    """
    Ejecuta find_traders.py como subproceso.
    Se llama semanalmente (lunes 08:00 UTC) para descubrir nuevos traders.
    """
    import subprocess
    try:
        log.info("Ejecutando find_traders.py (descubrimiento semanal)...")
        send_telegram("🔍 Descubrimiento semanal de traders iniciado...")
        result = subprocess.run(
            [sys.executable, "find_traders.py", "--quick"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            log.info("find_traders.py completado OK")
            bot_state["last_trader_scan"] = datetime.now(timezone.utc)
            # Después del descubrimiento, actualizar análisis
            run_trader_analysis()
            send_telegram("✅ Descubrimiento de traders completado")
            return True
        else:
            log.warning(f"find_traders.py error: {result.stderr[:200]}")
            send_telegram(f"⚠️ Error en descubrimiento: {result.stderr[:100]}")
            return False
    except Exception as e:
        log.warning(f"Error ejecutando find_traders.py: {e}")
        return False


# =============================================================
# DATOS DE REFERENCIA
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"
DATA_API_URL = "https://data-api.polymarket.com"
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
    # Ciudades añadidas en v8 (detectadas en análisis de ColdMath)
    "Miami":          {"lat": 25.7954,  "lon": -80.2901,  "name": "Miami Intl"},
    "Madrid":         {"lat": 40.4936,  "lon": -3.5668,   "name": "Barajas"},
    "Seattle":        {"lat": 47.4499,  "lon": -122.3118, "name": "Sea-Tac"},
    "Dallas":         {"lat": 32.8972,  "lon": -97.0377,  "name": "Dallas Fort Worth"},
    "Lucknow":        {"lat": 26.7606,  "lon": 80.8893,   "name": "Chaudhary Charan Singh"},
    "Sao Paulo":      {"lat": -23.4355, "lon": -46.4730,  "name": "Guarulhos"},
    "Taipei":         {"lat": 25.0777,  "lon": 121.2330,  "name": "Taoyuan Intl"},
    # Ciudades añadidas en v8 — análisis tercer trader
    "Milan":          {"lat": 45.6306,  "lon": 8.7281,   "name": "Malpensa"},
    "Chongqing":      {"lat": 29.7123,  "lon": 106.6519, "name": "Jiangbei"},
    "Chengdu":        {"lat": 30.5737,  "lon": 103.9415, "name": "Shuangliu"},
    "Wuhan":          {"lat": 30.7748,  "lon": 114.2137, "name": "Tianhe"},
}

# Alias → nombre canónico (mercados de rango usan abreviaturas)
CITY_ALIASES = {
    "NYC": "New York City",
    "New York": "New York City",
    "LA": "Los Angeles",
    "SF": "San Francisco",
    "HK": "Hong Kong",
    "SP": "Sao Paulo",
    "São Paulo": "Sao Paulo",
    "BA": "Buenos Aires",
}


def normalize_city(city_raw):
    """Normaliza nombre de ciudad: aplica alias y limpia."""
    city = city_raw.strip()
    return CITY_ALIASES.get(city, city)


# =============================================================
# TELEGRAM — ENVÍO
# =============================================================

MENU_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📊 Estado", "callback_data": "estado"},
            {"text": "💰 Cartera", "callback_data": "cartera"},
        ],
        [
            {"text": "📓 Log", "callback_data": "log"},
            {"text": "📋 Detalle", "callback_data": "logfull"},
        ],
        [
            {"text": "🔍 Traders", "callback_data": "traders"},
            {"text": "📋 Órdenes", "callback_data": "ordenes"},
        ],
        [
            {"text": "🚀 Forzar ciclo", "callback_data": "forzar"},
            {"text": "⚡ Modo", "callback_data": "modo"},
        ],
    ]
}


def send_telegram(mensaje, with_menu=False, custom_keyboard=None):
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
        log.warning(f"Telegram error: {e}")


def answer_callback_query(callback_id, text=""):
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
    global DRY_RUN
    modo = "🔴 REAL" if not DRY_RUN else "🟡 DRY RUN"
    running = "🔄 Ejecutando..." if bot_state["running"] else "💤 Esperando"

    next_run = bot_state["next_run"]
    if next_run:
        diff = next_run - datetime.now(timezone.utc)
        if diff.total_seconds() > 0:
            h = int(diff.total_seconds() // 3600)
            m = int((diff.total_seconds() % 3600) // 60)
            next_str = f"{next_run.strftime('%H:%M UTC')} (en {h}h {m}m)"
        else:
            next_str = "Ahora"
    else:
        next_str = "No programado"

    last_str = bot_state["last_run"].strftime('%H:%M UTC') if bot_state["last_run"] else "Nunca"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    send_telegram(
        f"📊 <b>Estado del Bot</b>\n\n"
        f"Modo: {modo}\n"
        f"Bankroll: <b>${BANKROLL:.2f}</b>\n"
        f"Min edge: {MIN_EDGE}%\n"
        f"Estado: {running}\n\n"
        f"Última ejecución: {last_str}\n"
        f"Próxima: {next_str}\n"
        f"Ciclos: {bot_state['cycle_count']}\n\n"
        f"Último ciclo:\n"
        f"  Oportunidades: {bot_state['last_opportunities']}\n"
        f"  Órdenes: {bot_state['last_orders_placed']}\n\n"
        f"⏰ Schedule: {schedule} UTC",
        with_menu=True,
    )


def cmd_cartera():
    """
    💰 Cartera completa: balance + posiciones + PnL.

    Usa data-api.polymarket.com/positions para posiciones.
    El balance disponible se calcula: bankroll - valor posiciones.
    """
    funder = os.getenv("FUNDER", "")
    if not funder:
        send_telegram("❌ No hay FUNDER.", with_menu=True)
        return

    try:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "20",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"{DATA_API_URL}/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "polymarket-bot/0.7")
        resp = urllib.request.urlopen(req, timeout=15)
        positions = json.loads(resp.read())
    except Exception as e:
        send_telegram(f"❌ Error cartera: {e}", with_menu=True)
        return

    # ---- Calcular totales ----
    total_invested = 0
    total_current = 0
    total_pnl = 0
    lines = []

    for i, pos in enumerate(positions):
        title = pos.get("title", "?")
        outcome = pos.get("outcome", "?")
        size = float(pos.get("size", 0))
        avg_price = float(pos.get("avgPrice", 0))
        cur_price = float(pos.get("curPrice", 0))
        initial_value = float(pos.get("initialValue", 0))
        current_value = float(pos.get("currentValue", 0))
        cash_pnl = float(pos.get("cashPnl", 0))
        pct_pnl = float(pos.get("percentPnl", 0))

        total_invested += initial_value
        total_current += current_value
        total_pnl += cash_pnl

        icon = "🟢" if cash_pnl >= 0 else "🔴"
        t_short = title[:50] + "..." if len(title) > 50 else title

        lines.append(
            f"{i+1}. {icon} <b>{outcome}</b>\n"
            f"   {t_short}\n"
            f"   {size:.1f}sh @ ${avg_price:.2f} → ${cur_price:.2f}\n"
            f"   Invertido: ${initial_value:.2f} | Valor: ${current_value:.2f}\n"
            f"   PnL: ${cash_pnl:+.2f} ({pct_pnl:+.1f}%)"
        )

    pnl_icon = "🟢" if total_pnl >= 0 else "🔴"

    if not positions:
        header = "💰 <b>Cartera</b>\n\nNo hay posiciones abiertas.\n"
    else:
        header = (
            f"💰 <b>Cartera</b>\n\n"
            f"Posiciones: {len(positions)}\n"
            f"Invertido: ${total_invested:.2f}\n"
            f"Valor actual: ${total_current:.2f}\n"
            f"PnL: {pnl_icon} <b>${total_pnl:+.2f}</b>\n"
            f"\n{'─' * 30}\n"
        )

    msg = header + "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:3990] + "\n..."
    send_telegram(msg, with_menu=True)


def cmd_ordenes():
    """📋 Órdenes pendientes — usa known_tokens para enriquecer."""
    global clob_client
    if bot_state["running"]:
        send_telegram("🔄 Ciclo en ejecución...", with_menu=True)
        return
    if clob_client is None:
        send_telegram("❌ No autenticado.", with_menu=True)
        return

    try:
        orders = get_open_orders(clob_client)
    except Exception as e:
        send_telegram(f"❌ Error: {e}", with_menu=True)
        return

    if not orders:
        send_telegram("📋 <b>Órdenes pendientes:</b> ninguna", with_menu=True)
        return

    lines = [f"📋 <b>Órdenes pendientes: {len(orders)}</b>\n"]

    for i, order in enumerate(orders):
        price = order.get("price", "?")
        size = order.get("original_size", order.get("size", "?"))
        side = order.get("side", "?")
        asset_id = order.get("asset_id", "")

        # Edad
        age_str = ""
        created_raw = order.get("created_at", "")
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

        # Buscar en known_tokens (cache del bot)
        info = known_tokens.get(asset_id, {})
        question = info.get("question", "")
        token_side = info.get("side", "")

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
                f"   Token: {asset_id[:24]}..."
            )

    send_telegram("\n".join(lines), with_menu=True)


def cmd_log():
    """
    📓 Muestra qué hizo el bot en el último ciclo.
    Si no hay resumen en memoria (post-redeploy), lee del archivo.
    """
    summary = bot_state.get("last_decision_summary", "")

    # Si no hay en memoria, intentar leer del archivo decisions.log
    if not summary:
        try:
            if os.path.exists("decisions.log"):
                with open("decisions.log", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                # Buscar el último ciclo (empieza con "====")
                last_cycle_start = -1
                for i in range(len(lines) - 1, -1, -1):
                    if "CICLO" in lines[i] and "=====" in lines[max(0, i-1)]:
                        last_cycle_start = max(0, i - 1)
                        break
                if last_cycle_start >= 0:
                    cycle_lines = lines[last_cycle_start:]
                    summary = "📓 <b>Último ciclo (de archivo)</b>\n\n"
                    for line in cycle_lines[:30]:  # máx 30 líneas
                        clean = line.strip()
                        if clean:
                            summary += f"{clean}\n"
        except Exception:
            pass

    if not summary:
        send_telegram("📓 <b>Log</b>\n\nAún no hay ciclos registrados.", with_menu=True)
        return

    if len(summary) > 3900:
        summary = summary[:3900] + "\n..."

    send_telegram(summary, with_menu=True)


def cmd_forzar():
    if bot_state["running"]:
        send_telegram("🔄 Ya hay un ciclo en ejecución.", with_menu=True)
        return
    send_telegram("🚀 <b>Ciclo forzado</b>\nDespertando...")
    force_event.set()


def cmd_logfull():
    """
    📋 Log detallado: muestra TODOS los mercados evaluados,
    incluyendo por qué se descartó cada uno.
    Cruza con señales de traders.
    """
    edge_analysis = bot_state.get("last_edge_analysis", [])
    trader_signals = bot_state.get("last_trader_signals", {})

    if not edge_analysis:
        send_telegram(
            "📋 <b>Log detallado</b>\n\nSin datos. Espera a que complete un ciclo.",
            with_menu=True,
        )
        return

    # Clasificar las líneas
    accepted = []      # ✓
    near_misses = []   # ✗ BAJO con edge ≥3%
    no_edge = []       # ✗ SIN EDGE
    duplicates = []    # ⏭
    kelly_low = []     # ✗ KELLY

    for line in edge_analysis:
        stripped = line.strip()
        if stripped.startswith("✓"):
            accepted.append(stripped)
        elif "BAJO" in stripped:
            # Extraer edge %
            edge_match = re.search(r"edge=(\d+\.?\d*)%", stripped)
            edge_val = float(edge_match.group(1)) if edge_match else 0
            near_misses.append((edge_val, stripped[2:]))
        elif "SIN EDGE" in stripped:
            no_edge.append(stripped[2:])
        elif stripped.startswith("⏭"):
            duplicates.append(stripped[2:])
        elif "KELLY" in stripped:
            kelly_low.append(stripped[2:])

    near_misses.sort(key=lambda x: -x[0])

    text = f"📋 <b>Log detallado del último ciclo</b>\n\n"
    text += f"Total: {len(edge_analysis)} mercados evaluados\n"
    text += f"✅ Aceptados: {len(accepted)}\n"
    text += f"🔶 Near miss (edge ≥3%): {len([n for n in near_misses if n[0] >= 3])}\n"
    text += f"⏭ Duplicados: {len(duplicates)}\n"
    text += f"❌ Sin edge: {len(no_edge)}\n"
    text += f"❌ Kelly bajo: {len(kelly_low)}\n"

    # Aceptados
    if accepted:
        text += f"\n<b>✅ ACEPTADOS:</b>\n"
        for line in accepted[:5]:
            text += f"🟢 {line[2:70]}\n"

    # Near misses con cruce de traders (lo más útil)
    interesting = [(e, t) for e, t in near_misses if e >= 3.0]
    if interesting:
        text += f"\n<b>🔶 NEAR MISSES (edge ≥3%, < {MIN_EDGE}%):</b>\n"
        for edge_val, line_text in interesting[:8]:
            # Cruzar con traders
            trader_info = ""
            if trader_signals:
                for key, sigs in trader_signals.items():
                    # Buscar coincidencia por ciudad en la línea
                    parts = key.split("|")
                    if len(parts) >= 1:
                        city = parts[0]
                        if city.lower() in line_text.lower():
                            traders = [s["trader"] for s in sigs]
                            trader_info = f"\n    👀 Traders aquí: {', '.join(traders[:4])}"
                            break

            text += f"  🔶 edge={edge_val:.1f}% | {line_text[:65]}{trader_info}\n"

        if len(interesting) > 8:
            text += f"  ... y {len(interesting) - 8} más\n"
    else:
        text += f"\n<i>Sin near misses ≥3% — el mercado está muy eficiente ahora.</i>\n"

    if len(text) > 3900:
        text = text[:3890] + "\n..."
    send_telegram(text, with_menu=True)


def cmd_modo():
    global DRY_RUN
    if DRY_RUN:
        msg = (
            f"⚡ <b>Modo: 🟡 DRY RUN</b>\n\n"
            f"¿Activar <b>MODO REAL</b>?\n"
            f"Bankroll: ${BANKROLL:.2f}\n\n"
            f"⚠️ Dinero real."
        )
        kb = {"inline_keyboard": [[
            {"text": "✅ Activar REAL", "callback_data": "confirmar_real"},
            {"text": "❌ Cancelar", "callback_data": "cancelar_modo"},
        ]]}
    else:
        msg = (
            f"⚡ <b>Modo: 🔴 REAL</b>\n\n"
            f"¿Volver a <b>DRY RUN</b>?"
        )
        kb = {"inline_keyboard": [[
            {"text": "🟡 Volver a DRY RUN", "callback_data": "confirmar_dry"},
            {"text": "❌ Cancelar", "callback_data": "cancelar_modo"},
        ]]}
    send_telegram(msg, custom_keyboard=kb)


def cmd_confirmar_real():
    global DRY_RUN
    DRY_RUN = False
    log.info("MODO REAL desde Telegram")
    send_telegram(
        f"🔴 <b>MODO REAL ACTIVADO</b>\n\n"
        f"Bankroll: ${BANKROLL:.2f}\n\n"
        f"⚠️ Si Railway reinicia → vuelve a DRY_RUN de Railway.\n"
        f"Permanente: Railway → Variables → DRY_RUN=false",
        with_menu=True,
    )


def cmd_confirmar_dry():
    global DRY_RUN
    DRY_RUN = True
    log.info("DRY RUN desde Telegram")
    send_telegram("🟡 <b>DRY RUN ACTIVADO</b>", with_menu=True)


def cmd_cancelar_modo():
    modo = "🟡 DRY RUN" if DRY_RUN else "🔴 REAL"
    send_telegram(f"Sin cambios: {modo}", with_menu=True)


def cmd_traders():
    """
    🔍 Muestra resumen de inteligencia de traders.
    Lee signals.json y muestra señales accionables.
    """
    signals_file = "signals.json"
    if not os.path.exists(signals_file):
        send_telegram(
            "🔍 <b>Traders Intel</b>\n\n"
            "Sin datos todavía.\n"
            "Se generarán automáticamente en el próximo ciclo.",
            with_menu=True,
        )
        return

    try:
        with open(signals_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        send_telegram(f"❌ Error: {e}", with_menu=True)
        return

    generated = data.get("generated", "?")[:16]
    n_signals = data.get("n_actionable_signals", 0)
    n_consensus = data.get("n_consensus_markets", 0)
    n_traders = data.get("n_traders_analyzed", 0)
    n_quality = data.get("n_quality_traders", 0)
    quality_names = data.get("quality_traders", [])
    n_skipped = data.get("n_skipped_low_quality", 0)

    text = f"🔍 <b>Traders Intel</b>\n"
    text += f"Actualización: {generated} UTC\n"
    text += f"Analizados: {n_traders} | Calidad: {n_quality} | Filtrados: {n_skipped} señales\n"
    text += f"Señales: {n_signals} | Consenso: {n_consensus}\n"

    if quality_names:
        text += f"\n⭐ <b>Traders calidad:</b> {', '.join(quality_names[:8])}\n"

    # Último scan y análisis
    scan = bot_state.get("last_trader_scan")
    analysis = bot_state.get("last_trader_analysis")
    if scan:
        text += f"\nÚltimo scan: {scan.strftime('%d/%m %H:%M')} UTC"
    if analysis:
        text += f"\nÚltimo análisis: {analysis.strftime('%d/%m %H:%M')} UTC"

    if n_signals == 0:
        text += "\n\nSin señales accionables ahora."
    else:
        text += f"\n\n<b>Señales activas:</b>\n"
        shown = 0
        for s in data.get("signals", []):
            if s.get("is_reference"):
                continue
            if shown >= 8:
                text += f"\n... y {n_signals - shown} más"
                break
            icon = "🤝" if s.get("has_consensus") else "📍"
            city = s.get("city", "?")
            date_str = s.get("date", "?")
            outcome = s.get("outcome", "?")
            price = s.get("avg_price", 0)
            text += f"{icon} {s['trader']}: {outcome} {city} {date_str} ${price:.2f}\n"
            shown += 1

    if len(text) > 4000:
        text = text[:3990] + "\n..."
    send_telegram(text, with_menu=True)


COMMANDS = {
    "estado": cmd_estado, "cartera": cmd_cartera, "ordenes": cmd_ordenes,
    "log": cmd_log, "logfull": cmd_logfull, "forzar": cmd_forzar,
    "modo": cmd_modo, "traders": cmd_traders,
    "confirmar_real": cmd_confirmar_real, "confirmar_dry": cmd_confirmar_dry,
    "cancelar_modo": cmd_cancelar_modo,
}


# =============================================================
# TELEGRAM — POLLING
# =============================================================

def is_authorized(chat_id):
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def handle_telegram_update(update):
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
                send_telegram(f"❌ Error: {e}", with_menu=True)
        else:
            send_telegram("🤖 <b>Bot Polymarket</b>\n\nToca un botón:", with_menu=True)


def telegram_polling_loop():
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
                    log.warning(f"Telegram update error: {e}")
        except Exception as e:
            log.warning(f"Telegram poll error: {e}")
            time.sleep(10)


# =============================================================
# AUTENTICACIÓN
# =============================================================

def setup_client():
    pk = os.getenv("PK")
    funder = os.getenv("FUNDER")
    if not pk or not funder:
        log.error("PK o FUNDER no encontrados")
        return None
    try:
        client = ClobClient(
            "https://clob.polymarket.com", key=pk,
            chain_id=137, signature_type=1, funder=funder,
        )
        client.set_api_creds(client.create_or_derive_api_creds())
        log.info("Autenticación OK")
        return client
    except Exception as e:
        log.error(f"Auth error: {e}")
        return None


# =============================================================
# FUNCIONES: API
# =============================================================

def api_get(endpoint, retries=3, delay=5):
    """GET a la Gamma API con reintentos automáticos.
    
    Si la conexión falla (error de red), espera `delay` segundos y reintenta.
    Esto soluciona el 'Connection reset by peer' del ciclo 23:00.
    """
    url = GAMMA_URL + endpoint
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-bot/0.8")
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                log.warning(f"API error (intento {attempt+1}/{retries}): {e} — reintentando en {delay}s")
                time.sleep(delay)
    raise last_error


def get_coordinates_fallback(city_name):
    city_clean = city_name.strip().replace(" ", "+")
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_clean}&count=1&language=en"
    resp = urllib.request.urlopen(url, timeout=15)
    data = json.loads(resp.read())
    if "results" not in data or not data["results"]:
        return None
    return data["results"][0]["latitude"], data["results"][0]["longitude"]


def get_forecast(lat, lon, retries=3, delay=5):
    """GET a Open-Meteo con reintentos automáticos."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f",precipitation_probability_max,precipitation_sum"
        f"&timezone=auto"
    )
    last_error = None
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(url, timeout=30)
            data = json.loads(resp.read())
            daily = data["daily"]
            result = {}
            for i in range(len(daily["time"])):
                result[daily["time"][i]] = {
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "rain_prob": daily["precipitation_probability_max"][i],
                    "rain_mm": daily["precipitation_sum"][i],
                }
            return result
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                log.warning(f"Forecast error (intento {attempt+1}/{retries}): {e} — reintentando en {delay}s")
                time.sleep(delay)
    raise last_error


# =============================================================
# FUNCIONES: ÓRDENES
# =============================================================

def get_open_orders(client):
    try:
        orders = client.get_orders()
        return [o for o in orders if o.get("status", "").upper() in ("LIVE", "ACTIVE", "OPEN")]
    except Exception as e:
        log.warning(f"Error órdenes: {e}")
        return []


def get_order_token_ids(open_orders):
    return set(o.get("asset_id", "") for o in open_orders if o.get("asset_id"))


def clean_stale_orders(client, open_orders, max_age_hours):
    cancelled = 0
    now = datetime.now(timezone.utc)
    for order in open_orders:
        oid = order.get("id", "")
        raw = order.get("created_at", "")
        if not raw or not oid:
            continue
        try:
            if isinstance(raw, (int, float)):
                created = datetime.fromtimestamp(raw, tz=timezone.utc)
            else:
                created = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError, OSError):
            continue
        if (now - created).total_seconds() / 3600 > max_age_hours:
            try:
                client.cancel(oid)
                cancelled += 1
                log.info(f"Stale cancelada: {oid[:16]}...")
            except Exception as e:
                log.warning(f"Cancel error: {e}")
    return cancelled


# =============================================================
# FUNCIONES: PARSEO
# =============================================================

def parse_temperature_question(question):
    """
    Parsea preguntas de temperatura de Polymarket.
    
    Formato exact/above/below:
      "Will the highest temperature in London be 18°C on March 22?"
      "Will the highest temperature in Seoul be 14°C or higher on March 22?"
    
    Formato range (NUEVO en v9):
      "Will the highest temperature in NYC be between 62-63°F on March 22?"
    
    Devuelve dict con:
      city, temp_threshold, condition, date_str, unit
      + temp_threshold_high (solo para ranges)
    """
    # ---- Intentar formato RANGO primero ----
    range_match = re.search(
        r"temperature in (.+?) be between "
        r"(\d+)\s*[-–]\s*(\d+)°([CF])"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)"
        r"\s+\d+)",
        question, re.IGNORECASE,
    )
    if range_match:
        city = normalize_city(range_match.group(1).strip())
        temp_low = int(range_match.group(2))
        temp_high = int(range_match.group(3))
        unit = range_match.group(4).upper()
        date_str = range_match.group(5)
        return {
            "city": city,
            "temp_threshold": temp_low,
            "temp_threshold_high": temp_high,
            "condition": "range",
            "date_str": date_str,
            "unit": unit,
        }

    # ---- Formato exact / above / below ----
    match = re.search(
        r"temperature in (.+?) (?:be |on )"
        r"(\d+)°([CF])"
        r"(?: or (below|higher|above))?"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)"
        r"\s+\d+)",
        question, re.IGNORECASE,
    )
    if not match:
        return None
    city = normalize_city(match.group(1).strip())
    temp = int(match.group(2))
    unit = match.group(3).upper() if match.group(3) else "C"
    condition = "exact"
    if match.lastindex >= 4 and match.group(4):
        mod = match.group(4).lower()
        if mod == "below":
            condition = "at_or_below"
        elif mod in ("higher", "above"):
            condition = "at_or_above"
    date_str = match.group(5) if match.lastindex >= 5 else None
    return {
        "city": city,
        "temp_threshold": temp,
        "temp_threshold_high": None,
        "condition": condition,
        "date_str": date_str,
        "unit": unit,
    }


def date_text_to_iso(date_text, year=2026):
    if not date_text:
        return None
    months = {"january":"01","february":"02","march":"03","april":"04","may":"05","june":"06",
              "july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"}
    parts = date_text.strip().split()
    if len(parts) != 2 or parts[0].lower() not in months:
        return None
    return f"{year}-{months[parts[0].lower()]}-{parts[1].zfill(2)}"


# =============================================================
# FUNCIONES: MODELO
# =============================================================

def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def get_uncertainty(days_ahead):
    return {0: 0.8, 1: 1.0, 2: 1.4, 3: 1.8}.get(days_ahead, 2.5 if days_ahead <= 5 else 3.0)


def estimate_prob(forecast_max, threshold_c, condition, days_ahead, threshold_high_c=None):
    """
    Calcula probabilidad de que se cumpla la condición.
    
    Para rangos: P(low ≤ T ≤ high).
    La corrección ±0.5 se aplica porque la temperatura se redondea a enteros.
    Ejemplo: "between 62-63°F" → P(61.5 ≤ T ≤ 63.5)
    """
    sigma = get_uncertainty(days_ahead)
    mu = forecast_max
    if condition == "exact":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma) - normal_cdf(threshold_c - 0.5, mu, sigma)
    elif condition == "at_or_below":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma)
    elif condition == "at_or_above":
        prob = 1.0 - normal_cdf(threshold_c - 0.5, mu, sigma)
    elif condition == "range" and threshold_high_c is not None:
        # Rango: P(low ≤ T ≤ high)
        # Corrección: low-0.5 a high+0.5 porque se redondea a enteros
        prob = normal_cdf(threshold_high_c + 0.5, mu, sigma) - normal_cdf(threshold_c - 0.5, mu, sigma)
    else:
        prob = 0.5
    return max(0.01, min(0.99, prob))


# =============================================================
# FUNCIONES: KELLY
# =============================================================

def kelly_fraction(estimated_prob, market_price):
    if market_price <= 0.01 or market_price >= 0.99:
        return 0.0
    if estimated_prob <= 0.01 or estimated_prob >= 0.99:
        return 0.0
    b = (1.0 - market_price) / market_price
    kelly = (estimated_prob * b - (1 - estimated_prob)) / b
    if kelly <= 0:
        return 0.0
    return min(kelly / 2.0, MAX_BET_PCT)


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
        amount = round(5.0 * aggressive_price, 2)
        if amount > bankroll * MAX_BET_PCT or amount < MIN_BET:
            return None
        shares = 5.0
    profit = round(shares * (1.0 - aggressive_price), 2)
    loss = round(amount, 2)
    ev = round(estimated_prob * profit - (1 - estimated_prob) * loss, 2)
    return {
        "fraction_pct": round(fraction * 100, 2), "amount": amount,
        "shares": round(shares, 2), "profit_if_win": profit,
        "loss_if_lose": loss, "expected_value": ev,
        "aggressive_price": aggressive_price, "market_price": market_price,
    }


# =============================================================
# EJECUCIÓN
# =============================================================

def execute_trade(client, trade, dry_run=True):
    token_id = trade["token_id"]
    price = round(trade["position"].get("aggressive_price", trade["mkt_price"] / 100.0), 2)
    size = round(trade["position"]["shares"], 2)

    log.info(f"{'[DRY] ' if dry_run else ''}Orden: {trade['side']} {size}sh × ${price:.2f} | {trade['city']} {trade['date']}")

    if dry_run:
        return {"ok": True, "order_id": "DRY_RUN", "msg": "Simulado"}
    try:
        order_args = OrderArgs(token_id=token_id, price=price, size=size, side=BUY)
        signed = client.create_order(order_args)
        resp = client.post_order(signed, OrderType.GTC)
        oid = resp.get("orderID", resp.get("id", "?"))
        status = resp.get("status", "?")
        return {"ok": True, "order_id": oid, "msg": f"Status: {status}"}
    except Exception as e:
        log.error(f"Orden error: {e}")
        return {"ok": False, "order_id": None, "msg": str(e)}


# =============================================================
# FUNCIÓN PRINCIPAL
# =============================================================

def main(client):
    today_str = date.today().isoformat()
    mode_label = "DRY RUN" if DRY_RUN else "MODO REAL"

    bot_state["running"] = True
    bot_state["last_run"] = datetime.now(timezone.utc)

    log.info("=" * 65)
    log.info(f"BOT v9 | {today_str} | {mode_label} | ${BANKROLL:.2f}")
    log.info("=" * 65)

    # Decision log: registrar inicio
    dl = []  # Lista de líneas para el log de decisiones
    dl.append(f"{'='*50}")
    dl.append(f"CICLO {bot_state['cycle_count']+1} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | {mode_label}")
    dl.append(f"MIN_DAYS={MIN_DAYS_AHEAD} MAX_DAYS={MAX_DAYS_AHEAD} MIN_EDGE={MIN_EDGE}%")
    dl.append(f"{'='*50}")

    if client is None:
        log.error("No autenticado.")
        dl.append("ERROR: Cliente no autenticado. Ciclo abortado.")
        _save_decision_log(dl)
        bot_state["running"] = False
        return

    # ---- v9: Cargar señales de traders ----
    trader_signals = load_trader_signals()
    n_signals = sum(len(v) for v in trader_signals.values())
    if n_signals > 0:
        dl.append(f"TRADERS: {n_signals} señales cargadas de signals.json")
    else:
        dl.append(f"TRADERS: sin señales (signals.json vacío o ausente)")

    # ---- PASO 0: STALE ----
    open_orders = get_open_orders(client)
    cancelled = clean_stale_orders(client, open_orders, ORDER_MAX_AGE_HOURS)
    if cancelled > 0:
        dl.append(f"STALE: {cancelled} órdenes canceladas (>{ORDER_MAX_AGE_HOURS}h)")
        open_orders = get_open_orders(client)
    open_token_ids = get_order_token_ids(open_orders)
    dl.append(f"Órdenes activas: {len(open_token_ids)}")

    # ---- PASO 1: Mercados ----
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false&limit=30&order=volume24hr&ascending=false"
        )
    except Exception as e:
        log.error(f"Error mercados: {e}")
        events = []

    all_markets = []
    for event in events:
        for m in event.get("markets", []):
            all_markets.append(m)

            # Poblar known_tokens con TODOS los mercados que vemos
            clob_raw = m.get("clobTokenIds", "[]")
            try:
                clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
            except (json.JSONDecodeError, TypeError):
                clob_ids = []
            q = m.get("question", "?")
            for idx, tid in enumerate(clob_ids):
                known_tokens[tid] = {"question": q, "side": "YES" if idx == 0 else "NO"}

    dl.append(f"\nMERCADOS: {len(all_markets)} encontrados")

    # ---- PASO 2: Parseo + filtro ----
    candidates = []
    parse_fail = 0
    date_fail = 0
    price_fail = 0
    liq_fail = 0

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)
        if not parsed or not parsed["date_str"]:
            parse_fail += 1
            continue

        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            parse_fail += 1
            continue

        try:
            days_ahead = (date.fromisoformat(date_iso) - date.today()).days
        except ValueError:
            continue

        if days_ahead < MIN_DAYS_AHEAD or days_ahead > MAX_DAYS_AHEAD:
            date_fail += 1
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
                price_fail += 1
                continue

        liquidity = float(market.get("liquidity", 0))
        if liquidity < MIN_LIQUIDITY:
            liq_fail += 1
            continue

        parsed.update({
            "question": question, "date_iso": date_iso, "days_ahead": days_ahead,
            "mkt_prob_yes": mkt_prob_yes, "mkt_prob_no": 1.0 - mkt_prob_yes,
            "volume_24h": float(market.get("volume24hr", 0)), "liquidity": liquidity,
            "token_id_yes": clob_ids[0], "token_id_no": clob_ids[1],
        })
        candidates.append(parsed)

    dl.append(f"FILTROS: {len(candidates)} pasan | {parse_fail} no parseables | {date_fail} fuera de fecha | {price_fail} fuera de precio | {liq_fail} sin liquidez")

    # ---- PASO 3: Previsiones ----
    cities_needed = set(c["city"] for c in candidates)
    forecast_cache = {}
    for city in sorted(cities_needed):
        station = RESOLUTION_STATIONS.get(city)
        if station:
            lat, lon = station["lat"], station["lon"]
        else:
            coords = get_coordinates_fallback(city)
            if not coords:
                continue
            lat, lon = coords
        forecast_cache[city] = get_forecast(lat, lon)

    dl.append(f"PREVISIONES: {len(forecast_cache)} ciudades consultadas")

    # ---- PASO 4: Edge ----
    trades = []
    skipped_dup = 0
    edge_analysis = []  # Para el log detallado

    for c in candidates:
        city = c["city"]
        if city not in forecast_cache or c["date_iso"] not in forecast_cache[city]:
            continue

        forecast_max = forecast_cache[city][c["date_iso"]]["temp_max"]
        threshold = c["temp_threshold"]
        threshold_c = (threshold - 32) * 5 / 9 if c["unit"] == "F" else float(threshold)

        # v9: Soporte para rangos ("between 62-63°F")
        threshold_high = c.get("temp_threshold_high")
        threshold_high_c = None
        if threshold_high is not None:
            threshold_high_c = (threshold_high - 32) * 5 / 9 if c["unit"] == "F" else float(threshold_high)

        # Label para logs (muestra rango si aplica)
        temp_label = f"{threshold}-{threshold_high}°{c['unit']}" if threshold_high else f"{threshold}°{c['unit']}"

        our_prob_yes = estimate_prob(forecast_max, threshold_c, c["condition"], c["days_ahead"], threshold_high_c)
        our_prob_no = 1.0 - our_prob_yes
        edge_yes = our_prob_yes - c["mkt_prob_yes"]
        edge_no = our_prob_no - c["mkt_prob_no"]

        # Elegir lado con más edge
        if edge_yes > edge_no and edge_yes > 0:
            side, our_prob, mkt_price, edge, token_id = "YES", our_prob_yes, c["mkt_prob_yes"], edge_yes, c["token_id_yes"]
        elif edge_no > 0:
            side, our_prob, mkt_price, edge, token_id = "NO", our_prob_no, c["mkt_prob_no"], edge_no, c["token_id_no"]
        else:
            edge_analysis.append(f"  ✗ {city} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | edge_yes={edge_yes*100:.1f}% edge_no={edge_no*100:.1f}% → SIN EDGE")
            continue

        edge_pct = edge * 100

        if edge_pct < MIN_EDGE:
            edge_analysis.append(f"  ✗ {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% → BAJO (min {MIN_EDGE}%)")
            continue

        if token_id in open_token_ids:
            skipped_dup += 1
            edge_analysis.append(f"  ⏭ {city} {side} | edge={edge_pct:.1f}% → YA HAY ORDEN")
            continue

        position = calculate_position(BANKROLL, our_prob, mkt_price)
        if not position:
            edge_analysis.append(f"  ✗ {city} {side} | edge={edge_pct:.1f}% → KELLY MUY BAJO (no alcanza $1 mín)")
            continue

        # v9: Cruzar con señales de traders
        # match_key: para rangos usa "low-high" como temp
        if threshold_high:
            match_key = f"{city}|{c['date_iso']}|{c['condition']}|{threshold}-{threshold_high}|{c['unit']}"
        else:
            match_key = f"{city}|{c['date_iso']}|{c['condition']}|{threshold}|{c['unit']}"
        matching_traders = trader_signals.get(match_key, [])
        trader_confirm = ""
        if matching_traders:
            names = [s["trader"] for s in matching_traders]
            trader_confirm = f" 🤝 CONFIRMADO por: {', '.join(names)}"

        edge_analysis.append(f"  ✓ {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% | ${position['amount']:.2f} EV=${position['expected_value']:+.2f}{trader_confirm}")

        trades.append({
            "question": c["question"], "city": city, "date": c["date_iso"],
            "days_ahead": c["days_ahead"], "forecast_max": forecast_max,
            "threshold": threshold, "threshold_high": threshold_high,
            "unit": c["unit"], "condition": c["condition"],
            "side": side, "our_prob": round(our_prob * 100, 1),
            "mkt_price": round(mkt_price * 100, 1), "edge_pct": round(edge_pct, 1),
            "position": position, "volume_24h": c["volume_24h"],
            "liquidity": c["liquidity"],
            "station": RESOLUTION_STATIONS.get(city, {}).get("name", "?"),
            "token_id": token_id,
            "trader_confirmed": [s["trader"] for s in matching_traders],  # v9
        })

    trades.sort(key=lambda x: x["position"]["expected_value"], reverse=True)
    bot_state["last_opportunities"] = len(trades)

    # v9: Guardar análisis completo para /logfull
    bot_state["last_edge_analysis"] = edge_analysis
    bot_state["last_trader_signals"] = trader_signals

    dl.append(f"\nANÁLISIS DE EDGE ({len(candidates)} mercados evaluados):")
    dl.extend(edge_analysis)
    if skipped_dup:
        dl.append(f"\n  {skipped_dup} saltados (orden ya abierta)")
    dl.append(f"\nRESULTADO: {len(trades)} oportunidades con edge")

    # ---- PASO 5: Presupuesto ----
    max_budget = BANKROLL * MAX_EXPOSURE_PCT
    budget_left = max_budget
    selected = []

    for t in trades:
        pos = t["position"]
        if pos["amount"] <= budget_left:
            budget_left -= pos["amount"]
            selected.append(t)
        elif budget_left >= MIN_BET:
            reduced = round(budget_left, 2)
            agg_p = pos.get("aggressive_price", t["mkt_price"] / 100)
            sh = reduced / agg_p
            pr = round(sh * (1.0 - agg_p), 2)
            pd = t["our_prob"] / 100
            ev = round(pd * pr - (1 - pd) * reduced, 2)
            t["position"] = {
                "fraction_pct": round(reduced / BANKROLL * 100, 2),
                "amount": reduced, "shares": round(sh, 2),
                "profit_if_win": pr, "loss_if_lose": reduced,
                "expected_value": ev, "aggressive_price": agg_p,
                "market_price": t["mkt_price"] / 100,
            }
            budget_left = 0
            selected.append(t)

    dl.append(f"\nPRESUPUESTO: ${max_budget:.2f} (40% de ${BANKROLL:.2f})")
    dl.append(f"SELECCIONADAS: {len(selected)} de {len(trades)}")

    # ---- PASO 6: Ejecución ----
    if not selected:
        dl.append(f"\nSin operaciones este ciclo.")
        bot_state["last_orders_placed"] = 0
        bot_state["last_trades"] = []
        # v9: Siempre notificar que el ciclo terminó
        if not DRY_RUN:
            send_telegram(
                f"💤 <b>Ciclo completado</b>\n"
                f"Evaluados: {len(candidates)} | Edge: {len(trades)} | Seleccionados: 0\n"
                f"Min edge: {MIN_EDGE}%\n"
                f"Toca 📓 Log para detalle",
                with_menu=True,
            )
    else:
        results = []
        for i, trade in enumerate(selected):
            # Guardar en known_tokens para que /ordenes lo encuentre
            known_tokens[trade["token_id"]] = {
                "question": trade["question"],
                "side": trade["side"],
            }

            result = execute_trade(client, trade, dry_run=DRY_RUN)
            results.append(result)

            dl.append(f"\n  {'OK' if result['ok'] else 'FAIL'} #{i+1}: {trade['city']} {trade['side']} ${trade['position']['amount']:.2f} → {result['msg']}")

            if not DRY_RUN:
                icon = "✅" if result["ok"] else "❌"
                # v9: añadir confirmación de traders si existe
                trader_line = ""
                if trade.get("trader_confirmed"):
                    trader_line = f"\n🤝 Confirmado: {', '.join(trade['trader_confirmed'])}"
                send_telegram(
                    f"{icon} <b>Orden</b>\n"
                    f"{trade['city']} {trade['side']}\n"
                    f"${trade['position']['amount']:.2f} "
                    f"({trade['position']['shares']:.1f}sh "
                    f"@ ${trade['position'].get('aggressive_price', 0):.2f})\n"
                    f"Edge: {trade['edge_pct']}% | EV: ${trade['position']['expected_value']:+.2f}"
                    f"{trader_line}"
                )

        ok = sum(1 for r in results if r["ok"])
        bot_state["last_orders_placed"] = ok
        bot_state["last_trades"] = selected

        if not DRY_RUN:
            send_telegram(f"📊 <b>Ciclo completado</b>\nÓrdenes: {ok}/{len(results)} OK", with_menu=True)

    dl.append(f"\n{'='*50}")

    # Guardar log de decisiones
    _save_decision_log(dl)

    bot_state["cycle_count"] += 1
    bot_state["running"] = False
    log.info("Ciclo finalizado.")


def _save_decision_log(lines):
    """Guarda el log y prepara el resumen para Telegram."""
    full_text = "\n".join(lines)

    # Guardar en archivo
    for line in lines:
        decision_log.info(line)

    # Preparar versión Telegram (más corta, con HTML)
    summary = f"📓 <b>Último ciclo</b>\n\n"

    # Near misses: mercados con edge pero por debajo de MIN_EDGE
    near_misses = []

    # Extraer las partes más importantes
    for line in lines:
        if line.startswith("CICLO"):
            summary += f"<b>{line}</b>\n"
        elif line.startswith("TRADERS:"):
            summary += f"{line}\n"
        elif line.startswith("MERCADOS:"):
            summary += f"{line}\n"
        elif line.startswith("FILTROS:"):
            summary += f"{line}\n"
        elif line.startswith("PREVISIONES:"):
            summary += f"{line}\n"
        elif line.startswith("RESULTADO:"):
            summary += f"\n<b>{line}</b>\n"
        elif line.startswith("PRESUPUESTO:"):
            summary += f"{line}\n"
        elif line.startswith("SELECCIONADAS:"):
            summary += f"<b>{line}</b>\n"
        elif line.strip().startswith("✓"):
            text = line.strip()[2:]
            if "🤝" in text:
                summary += f"🟢🤝 {text}\n"
            else:
                summary += f"🟢 {text}\n"
        elif line.strip().startswith("✗") and "BAJO" in line:
            # Near miss: tenía edge pero no suficiente
            # Extraer el % de edge para ordenar
            import re as _re
            edge_match = _re.search(r"edge=(\d+\.?\d*)%", line)
            if edge_match:
                edge_val = float(edge_match.group(1))
                if edge_val >= 3.0:  # solo mostrar los interesantes (≥3%)
                    near_misses.append((edge_val, line.strip()[2:]))
        elif line.strip().startswith("⏭"):
            summary += f"⏭ {line.strip()[2:]}\n"
        elif line.strip().startswith("OK") or line.strip().startswith("FAIL"):
            summary += f"{line.strip()}\n"
        elif "Sin operaciones" in line:
            summary += f"\n💤 {line.strip()}\n"

    # Añadir near misses al resumen (top 5 por edge)
    if near_misses:
        near_misses.sort(key=lambda x: -x[0])
        summary += f"\n<b>🔶 Casi entraron ({len(near_misses)} con edge ≥3%):</b>\n"
        for edge_val, text in near_misses[:5]:
            # Cruzar con traders si hay señales
            trader_info = ""
            signals = bot_state.get("last_trader_signals", {})
            if signals:
                # Intentar extraer ciudad y fecha del texto para buscar señales
                import re as _re
                city_m = _re.match(r"(\S+(?:\s\S+)?)\s+(YES|NO)\s+", text)
                if city_m:
                    city_name = city_m.group(1)
                    # Buscar en señales cualquier match parcial por ciudad
                    matching = [
                        k for k in signals.keys()
                        if city_name.lower() in k.lower()
                    ]
                    if matching:
                        all_traders = set()
                        for k in matching:
                            for s in signals[k]:
                                all_traders.add(s["trader"])
                        if all_traders:
                            trader_info = f" 👀 {', '.join(list(all_traders)[:3])}"

            summary += f"  🔶 {text[:70]}{trader_info}\n"

        if len(near_misses) > 5:
            summary += f"  ... y {len(near_misses) - 5} más\n"

    bot_state["last_decision_summary"] = summary


# =============================================================
# SCHEDULER
# =============================================================

def get_next_run_time():
    now = datetime.now(timezone.utc)
    for hour in sorted(SCHEDULE_HOURS_UTC):
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=sorted(SCHEDULE_HOURS_UTC)[0], minute=0, second=0, microsecond=0)


def should_run_daily_analysis():
    """¿Toca actualizar señales de traders? Una vez al día."""
    last = bot_state.get("last_trader_analysis")
    if last is None:
        return True
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return age_hours >= 20  # cada ~20h para que no se salte por timing


def should_run_weekly_discovery():
    """¿Toca descubrir traders nuevos? Lunes 08:00 UTC."""
    now = datetime.now(timezone.utc)
    if now.weekday() != 0:  # 0 = lunes
        return False
    if now.hour != sorted(SCHEDULE_HOURS_UTC)[0]:  # primer ciclo del día
        return False
    last = bot_state.get("last_trader_scan")
    if last is None:
        return True
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return age_hours >= 100  # mínimo ~4 días entre scans


def run_trader_tasks():
    """Ejecuta tareas del pipeline de traders según corresponda."""
    # Descubrimiento semanal (lunes)
    if should_run_weekly_discovery():
        try:
            run_trader_discovery()
        except Exception as e:
            log.warning(f"Error en descubrimiento de traders: {e}")

    # Análisis diario
    elif should_run_daily_analysis():
        try:
            run_trader_analysis()
        except Exception as e:
            log.warning(f"Error en análisis de traders: {e}")


if __name__ == "__main__":
    log.info("=" * 65)
    log.info(f"POLYMARKET BOT v9 | Schedule: {sorted(SCHEDULE_HOURS_UTC)} UTC")
    log.info(f"Modo: {'DRY RUN' if DRY_RUN else 'REAL'}")
    log.info("=" * 65)

    clob_client = setup_client()
    if clob_client is None:
        send_telegram("❌ <b>Error autenticación</b>")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        threading.Thread(target=telegram_polling_loop, daemon=True, name="TelegramPoller").start()
        log.info("Telegram polling: OK")

    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    send_telegram(
        f"🤖 <b>Bot v9 arrancado</b>\n"
        f"Modo: {modo} | ${BANKROLL:.2f}\n"
        f"Min edge: {MIN_EDGE}% | Schedule: {schedule} UTC\n"
        f"🔍 Traders: auto-análisis diario, descubrimiento lunes",
        with_menu=True,
    )

    # v9: Ejecutar análisis de traders antes del primer ciclo
    run_trader_tasks()

    log.info("Primer ciclo...")
    try:
        main(clob_client)
    except Exception as e:
        log.error(f"Error primer ciclo: {e}")
        send_telegram(f"❌ <b>Error</b>\n<code>{str(e)[:200]}</code>")

    while True:
        next_run = get_next_run_time()
        bot_state["next_run"] = next_run
        log.info(f"Próximo: {next_run.strftime('%H:%M UTC')}")

        while datetime.now(timezone.utc) < next_run:
            if force_event.wait(timeout=30):
                force_event.clear()
                log.info("⚡ Forzado")
                break

        # v9: Tareas de traders antes de cada ciclo
        run_trader_tasks()

        try:
            main(clob_client)
        except Exception as e:
            log.error(f"Error: {e}")
            send_telegram(f"❌ <b>Error</b>\n<code>{str(e)[:200]}</code>")
