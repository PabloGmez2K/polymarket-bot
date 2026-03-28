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
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY, SELL

load_dotenv()

# =============================================================
# bot.py v10.4.5 — zonas horarias reales + limpieza config local
# Sesión 19: Fase 1.5 — rediseño Telegram + fixes post-deploy
# =============================================================
#
# Nuevo en v10.4.3:
#   - Ciclos persistentes: _load_cycle_count() lee cycles_history.jsonl al arrancar
#   - Fix /detalle: escapa HTML en fallback decisions.log (Bug #13 parcial)
#   - Fix arranque: mensaje "Bug #11" eliminado
#   - Fix traders: coincidencias filtradas por ciudad+lado+fecha futura
#
# v10.4.2:
#   - Rediseño completo Telegram: 7 botones mejorados + botón /info nuevo
#   - Fix Bug #13: send_telegram_paged() — paginación automática >4096 chars
#   - Helpers: _parse_position_label(), _get_portfolio_and_positions()
#   - /log lee desde cycle_summary.json (estructurado, fiable)
#   - /info: bloque resumen para pegar en ChatGPT/Claude
#   - /cartera: precios en centavos, etiquetas legibles
#
# v10.4.1:
#   - cycles_history.jsonl: historial append-only de todos los ciclos
#   - cycle_summary.json: último ciclo para consulta rápida
#   - Cada ciclo registra: gestión, escaneo, compras, exposición, versión
#
# v10.4 (base):
#   - Fix Bug #3: check posiciones abiertas en Data API antes de comprar
#   - Fix Bug #9: sold_this_cycle — no re-comprar lo vendido en manage_positions
#   - Fix Bug #11: comprobar último ciclo al arrancar (min 3h gap)
#   - Fix Bug #10: MIN_BET default 0.50 → 1.00 (alineado con Railway)
#   - Fix Bug #12: resueltas no cuentan como "mantenidas" en Telegram
#   - Fix Bug #14: mensajes Telegram clarifican "precio límite" vs fill
#   - Mejora Telegram: /estado separa "Compras: X | Ventas: Y"
#   - Mejora Telegram: resumen ciclo dice "Exposición actual" y "Presupuesto libre"
#
# Heredado de v10.3:
#   - Fix Bug #5: get_min_days_for_city() — zona horaria per-city
#   - Fix Bug #4: get_current_exposure() excluye curPrice >= 0.98
#   - Fix Bug #7: SELL → SELL_PENDING hasta confirmar fill
#   - Fix Bug #6: signals.json freshness 12h → 26h + alerta Telegram
#   - Fix Bug #8: Posiciones micro (<$0.10) → LOSS_TOTAL
# v10.4.5:
#   - CITY_TIMEZONES con zonas IANA reales (sin parches manuales de DST)
# =============================================================


# =============================================================
# CONFIGURACIÓN
# =============================================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))

MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "1.00"))           # v10.4: default alineado con Railway
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))   # v9: subido de 0.05 a 0.10 (10%)
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))  # -1 = automático


def get_min_days_ahead():
    """
    Calcula MIN_DAYS_AHEAD base dinámicamente según la hora UTC.
    SOLO para logging y display. Para filtrar mercados, usar get_min_days_for_city().
    
    Si MIN_DAYS_AHEAD está forzado en Railway (≥0), usa ese valor.
    """
    if MIN_DAYS_AHEAD >= 0:
        return MIN_DAYS_AHEAD  # Override manual desde Railway

    hour_utc = datetime.now(timezone.utc).hour
    if hour_utc < 12:
        return 0  # Mañana: la mayoría de ciudades aún no registraron temp
    else:
        return 1  # Tarde/noche: muchas ciudades ya tienen dato real


def get_min_days_for_city(city):
    """
    Calcula MIN_DAYS_AHEAD para una ciudad específica, considerando su zona horaria.

    Problema que resuelve (Bug #5, sesión 12):
      A las 08:00 UTC, el bot compró Chongqing porque min_days=0 (mañana UTC).
      Pero en Chongqing (UTC+8) eran las 16:00 local → temperatura máxima ya registrada.
      Resultado: -$5.16 apostando contra información conocida.

    Lógica:
      La temperatura máxima diaria ocurre ~14:00-16:00 hora local.
      Si hora_local >= 14 → la temperatura de hoy ya se registró → min_days=1
      Si hora_local < 14 → aún puede subir → min_days=0

    Usamos 14 como umbral (conservador: a las 14:00 local muchas estaciones
    ya reportaron la máxima, aunque técnicamente puede subir hasta las 16:00).
    """
    if MIN_DAYS_AHEAD >= 0:
        return MIN_DAYS_AHEAD  # Override manual desde Railway

    local_tz = ZoneInfo(CITY_TIMEZONES.get(city, "UTC"))
    local_now = datetime.now(timezone.utc).astimezone(local_tz)
    local_hour = local_now.hour

    # Caso 1: local_hour >= 24 → la ciudad ya está en el DÍA SIGUIENTE.
    # "Hoy" (fecha UTC) ya terminó completamente allí.
    # Con ZoneInfo no vemos 25 directamente; lo detectamos comparando fechas.
    # La temperatura de "hoy" (fecha UTC) ya se registró entera.
    if local_now.date() > datetime.now(timezone.utc).date():
        return 1

    # Caso 2: local_hour < 0 → la ciudad está aún en el DÍA ANTERIOR.
    # "Hoy" (fecha UTC) aún no empezó allí. El mercado para "hoy" es futuro.
    # Con ZoneInfo tampoco vemos negativos; si la fecha local va retrasada, sigue siendo 0.
    if local_now.date() < datetime.now(timezone.utc).date():
        return 0

    # Caso 3: hora local normal (0-23)
    if local_hour >= 14:
        return 1  # Temperatura máxima de hoy ya registrada en esta ciudad
    else:
        return 0  # Aún puede subir

# v10.1: Gestión activa de posiciones
# Basado en investigación: Entire-Hood corta a -10%, toma a +17%
# Usamos umbrales un poco más amplios para nuestro bankroll pequeño
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))     # vender si PnL% < -25%
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))  # vender si PnL% > +40%
SELL_AGGRESSION = 0.02  # cuánto bajar el precio para asegurar venta rápida

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

# v10.4: Directorio de datos persistente (Railway Volume)
# En Railway, montar volume en /app/data y configurar DATA_DIR="/app/data"
# Los archivos sobreviven deploys. Sin DATA_DIR, usa directorio actual (compatible).
DATA_DIR = os.getenv("DATA_DIR", "")

def _data_path(filename):
    """Devuelve ruta completa para un archivo de datos."""
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, filename)
    return filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_data_path("trades.log"), encoding="utf-8"),
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
decision_handler = logging.FileHandler(_data_path("decisions.log"), encoding="utf-8")
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
    "last_sells_placed": 0,       # v10.4: ventas para /estado
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

PERFORMANCE_FILE = _data_path("performance.json")
CYCLE_SUMMARY_FILE = _data_path("cycle_summary.json")
CYCLES_HISTORY_FILE = _data_path("cycles_history.jsonl")


def _load_cycle_count():
    """
    Lee cycles_history.jsonl y devuelve el número de ciclos históricos.
    Así el contador no se reinicia con cada deploy — es acumulativo
    mientras el volume de Railway persista y la versión sea 10.4.X.
    """
    if not os.path.exists(CYCLES_HISTORY_FILE):
        return 0
    try:
        with open(CYCLES_HISTORY_FILE, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def parse_city_from_title(title):
    """Extrae ciudad de un título de posición. Helper para el tracker."""
    match = re.search(r"temperature in (.+?) (?:be |between |\d)", title, re.IGNORECASE)
    return match.group(1).strip() if match else "?"


def _parse_position_label(title, outcome=""):
    """
    Convierte título de mercado + outcome en etiqueta corta y legible.
    Ejemplos:
      "Will the high temperature in Dallas, TX be between 58 and 59°F on March 28?"
      → "Dallas 58-59°F Mar28 YES"
      "Will the temperature in Paris be 11°C on March 29?" → "Paris 11°C Mar29 NO"
      "Will the high temperature in Seattle be at most 51°F on March 28?" → "Seattle ≤51°F Mar28 YES"
    """
    city = parse_city_from_title(title)

    temp = ""
    m = re.search(r'between (\d+) and (\d+)\s*(°[CF])', title, re.IGNORECASE)
    if m:
        temp = f"{m.group(1)}-{m.group(2)}{m.group(3)}"
    else:
        m = re.search(r'at most (\d+)\s*(°[CF])', title, re.IGNORECASE)
        if m:
            temp = f"≤{m.group(1)}{m.group(2)}"
        else:
            m = re.search(r'at least (\d+)\s*(°[CF])', title, re.IGNORECASE)
            if m:
                temp = f"≥{m.group(1)}{m.group(2)}"
            else:
                m = re.search(r'be (\d+)\s*(°[CF])', title, re.IGNORECASE)
                if m:
                    temp = f"{m.group(1)}{m.group(2)}"

    date_str = ""
    m = re.search(
        r'on (January|February|March|April|May|June|July|August|September|October|November|December) (\d+)',
        title, re.IGNORECASE
    )
    if m:
        date_str = f"{m.group(1)[:3]}{m.group(2)}"

    parts = [city]
    if temp:
        parts.append(temp)
    if date_str:
        parts.append(date_str)
    if outcome:
        parts.append(outcome)
    return " ".join(parts)


def _get_portfolio_and_positions():
    """
    Obtiene posiciones y cash de la Data API en una sola llamada.
    Devuelve dict con: cash, cash_ok, active, resolved_won, dead,
                       active_value, resolved_value, portfolio_total,
                       api_error (str o None).
    Devuelve None si no hay FUNDER configurado.
    """
    funder = os.getenv("FUNDER", "")
    if not funder:
        return None

    positions = []
    api_error = None
    try:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "50",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"{DATA_API_URL}/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "polymarket-bot/0.10")
        resp = urllib.request.urlopen(req, timeout=15)
        positions = json.loads(resp.read())
    except Exception as e:
        api_error = str(e)
        log.warning(f"Error _get_portfolio_and_positions: {e}")

    cash, cash_ok = get_cash_balance(clob_client)

    active = []
    resolved_won = []
    dead = []
    for pos in positions:
        cv = float(pos.get("currentValue", 0))
        cp = float(pos.get("curPrice", 0))
        if cp >= 0.98:
            resolved_won.append(pos)
        elif cv >= 0.10:
            active.append(pos)
        else:
            dead.append(pos)

    active_value = sum(float(p.get("currentValue", 0)) for p in active)
    resolved_value = sum(float(p.get("currentValue", 0)) for p in resolved_won)
    portfolio_total = cash + active_value + resolved_value

    return {
        "cash": cash,
        "cash_ok": cash_ok,
        "active": active,
        "resolved_won": resolved_won,
        "dead": dead,
        "active_value": active_value,
        "resolved_value": resolved_value,
        "portfolio_total": portfolio_total,
        "api_error": api_error,
    }


# =============================================================
# TRACKER DE RENDIMIENTO (v10.1)
# =============================================================

def track_trade(action, **kwargs):
    """
    Registra cada BUY y SELL en performance.json.

    Esto es lo que permite analizar:
      - ROI por ciudad, por tipo de mercado, por días ahead
      - Accuracy del modelo (previsión vs resultado real)
      - Qué stop-losses/take-profits fueron correctos
      - Si los traders confirmados dan mejor resultado

    Uso:
      track_trade("BUY", city="Taipei", side="YES", price=0.11, ...)
      track_trade("SELL", city="Taipei", side="YES", price=0.19, reason="take_profit", ...)
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
    }
    entry.update(kwargs)

    try:
        history = []
        if os.path.exists(PERFORMANCE_FILE):
            with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

        history.append(entry)

        # Máximo 500 entradas (evitar que crezca infinito)
        if len(history) > 500:
            history = history[-500:]

        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando performance: {e}")


def get_performance_summary():
    """
    Calcula ROI y estadísticas desde performance.json.
    Para el comando /rendimiento de Telegram.
    """
    if not os.path.exists(PERFORMANCE_FILE):
        return None

    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return None

    buys = [h for h in history if h.get("action") == "BUY"]
    sells = [h for h in history if h.get("action") == "SELL"]
    # v10.3: SELLs pendientes de confirmación (Bug #7)
    pending_sells = [h for h in history if h.get("action") == "SELL_PENDING"]

    total_invested = sum(h.get("amount", 0) for h in buys)
    total_returned = sum(h.get("return_est", 0) for h in sells)

    # Ventas por tipo
    stop_losses = [s for s in sells if s.get("reason") == "stop_loss"]
    take_profits = [s for s in sells if s.get("reason") == "take_profit"]
    reevals = [s for s in sells if s.get("reason") == "reeval"]

    # PnL de ventas
    sell_pnl = sum(s.get("pnl_cash", 0) for s in sells)

    # Ciudades con más operaciones
    city_counts = {}
    city_pnl = {}
    for s in sells:
        c = s.get("city", "?")
        city_counts[c] = city_counts.get(c, 0) + 1
        city_pnl[c] = city_pnl.get(c, 0) + s.get("pnl_cash", 0)

    # Trades con confirmación de traders vs sin
    confirmed_sells = [s for s in sells if s.get("trader_confirmed")]
    unconfirmed_sells = [s for s in sells if not s.get("trader_confirmed")]

    return {
        "total_buys": len(buys),
        "total_sells": len(sells),
        "pending_sells": len(pending_sells),  # v10.3: ventas sin confirmar fill
        "total_invested": total_invested,
        "sell_pnl": sell_pnl,
        "stop_losses": len(stop_losses),
        "take_profits": len(take_profits),
        "reevals": len(reevals),
        "top_cities": sorted(city_counts.items(), key=lambda x: -x[1])[:5],
        "city_pnl": city_pnl,
        "confirmed_count": len(confirmed_sells),
        "confirmed_pnl": sum(s.get("pnl_cash", 0) for s in confirmed_sells),
        "unconfirmed_count": len(unconfirmed_sells),
        "unconfirmed_pnl": sum(s.get("pnl_cash", 0) for s in unconfirmed_sells),
    }


# =============================================================
# PIPELINE DE TRADERS (v9)
# =============================================================

def load_trader_signals():
    """
    Lee signals.json generado por trader_analyzer.py.
    Devuelve dict de match_key → lista de señales para cruce rápido.

    v10.3 Fix Bug #6: Freshness aumentada de 12h a 26h.
    Bug real: signals.json se generó a las 08:00, expiró a las 20:00 (12h).
    El ciclo de las 16:00 del día siguiente (32h) no tenía señales.
    Con 26h cubre todos los ciclos hasta la siguiente regeneración diaria.

    También añade logging explícito cuando está vacío para debugging.
    """
    signals_file = "signals.json"
    if not os.path.exists(signals_file):
        log.info("load_trader_signals: signals.json no existe")
        return {}
    try:
        with open(signals_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check freshness — v10.3: 26h (era 12h)
        generated = datetime.fromisoformat(data.get("generated", "2000-01-01T00:00:00+00:00"))
        age_hours = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
        if age_hours > 26:
            log.warning(f"load_trader_signals: signals.json expirado ({age_hours:.1f}h > 26h)")
            return {}
        # Indexar por match_key para cruce O(1)
        index = {}
        for s in data.get("signals", []):
            key = s.get("match_key", "")
            if key:
                if key not in index:
                    index[key] = []
                index[key].append(s)
        n_signals = sum(len(v) for v in index.values())
        if n_signals == 0:
            log.warning(f"load_trader_signals: signals.json tiene 0 señales (edad: {age_hours:.1f}h)")
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

# Zonas horarias reales por ciudad — evitan tener que tocar offsets en cada DST.
# Si una ciudad no está aquí, get_min_days_for_city() cae a UTC como fallback seguro.
CITY_TIMEZONES = {
    "Tokyo":          "Asia/Tokyo",
    "Seoul":          "Asia/Seoul",
    "Chongqing":      "Asia/Shanghai",
    "Shanghai":       "Asia/Shanghai",
    "Beijing":        "Asia/Shanghai",
    "Taipei":         "Asia/Taipei",
    "Shenzhen":       "Asia/Shanghai",
    "Chengdu":        "Asia/Shanghai",
    "Wuhan":          "Asia/Shanghai",
    "Hong Kong":      "Asia/Hong_Kong",
    "Singapore":      "Asia/Singapore",
    "Bangkok":        "Asia/Bangkok",
    "Lucknow":        "Asia/Kolkata",
    "Wellington":     "Pacific/Auckland",
    "Ankara":         "Europe/Istanbul",
    "London":         "Europe/London",
    "Paris":          "Europe/Paris",
    "Madrid":         "Europe/Madrid",
    "Milan":          "Europe/Rome",
    "Munich":         "Europe/Berlin",
    "Warsaw":         "Europe/Warsaw",
    "Tel Aviv":       "Asia/Jerusalem",
    "Buenos Aires":   "America/Argentina/Buenos_Aires",
    "Sao Paulo":      "America/Sao_Paulo",
    "New York City":  "America/New_York",
    "Toronto":        "America/Toronto",
    "Atlanta":        "America/New_York",
    "Miami":          "America/New_York",
    "Chicago":        "America/Chicago",
    "Dallas":         "America/Chicago",
    "Seattle":        "America/Los_Angeles",
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
            {"text": "📈 Rendimiento", "callback_data": "rendimiento"},
        ],
        [
            {"text": "🗒 Órdenes", "callback_data": "ordenes"},
            {"text": "ℹ️ Info", "callback_data": "info"},
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


def send_telegram_paged(text, with_menu=False, page_size=3800):
    """
    Fix Bug #13: envía mensajes largos divididos en páginas.
    Telegram rechaza mensajes > 4096 chars con HTTP 400.
    Divide en el último salto de línea antes del límite.
    El menú solo se muestra en la última página.
    """
    if len(text) <= page_size:
        send_telegram(text, with_menu=with_menu)
        return

    pages = []
    remaining = text
    while remaining:
        if len(remaining) <= page_size:
            pages.append(remaining)
            break
        cut = remaining.rfind("\n", 0, page_size)
        if cut == -1:
            cut = page_size
        pages.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")

    for i, page in enumerate(pages):
        is_last = (i == len(pages) - 1)
        header = f"[{i+1}/{len(pages)}]\n" if len(pages) > 1 else ""
        send_telegram(header + page, with_menu=(with_menu and is_last))


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

    last_str = bot_state["last_run"].strftime('%d/%m %H:%M UTC') if bot_state["last_run"] else "Nunca"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    # Último ciclo desde cycle_summary.json si existe
    cycle_line = ""
    if os.path.exists(CYCLE_SUMMARY_FILE):
        try:
            with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
                cd = json.load(f)
            mgmt = cd.get("management", {})
            scan = cd.get("scan", {})
            buys = cd.get("buys", [])
            n_buys = len(buys)
            n_sold = mgmt.get("n_sold", 0)
            n_mkts = scan.get("markets_evaluated", 0)
            exp = cd.get("exposure_after")
            exp_str = f" | Exp ${exp:.2f}" if exp is not None else ""
            cycle_line = (
                f"\n📋 Ciclo #{cd.get('cycle_number','?')} "
                f"({cd.get('timestamp_utc','?')[:10]}):\n"
                f"  Mercados: {n_mkts} | Compras: {n_buys} | Ventas: {n_sold}{exp_str}"
            )
        except Exception:
            pass

    if not cycle_line:
        cycle_line = (
            f"\n📋 Último ciclo:\n"
            f"  Oportunidades: {bot_state['last_opportunities']}\n"
            f"  Compras: {bot_state['last_orders_placed']} | Ventas: {bot_state.get('last_sells_placed', 0)}"
        )

    send_telegram(
        f"📊 <b>Bot v10.4.5 | {modo}</b>\n\n"
        f"💰 Bankroll: <b>${BANKROLL:.2f}</b> | Edge mín: {MIN_EDGE}%\n"
        f"🔧 SL {STOP_LOSS_PCT}% / TP +{TAKE_PROFIT_PCT}%\n\n"
        f"⏱ Estado: {running}\n"
        f"📅 Último: {last_str}\n"
        f"⏰ Próximo: {next_str}\n"
        f"🔢 Ciclos: {bot_state['cycle_count']}"
        f"{cycle_line}\n\n"
        f"Schedule: {schedule} UTC",
        with_menu=True,
    )


def cmd_cartera():
    """💰 Cartera: cash + posiciones activas. v10.4.2: etiquetas legibles, precios en centavos."""
    portfolio = _get_portfolio_and_positions()
    if portfolio is None:
        send_telegram("❌ No hay FUNDER configurado.", with_menu=True)
        return

    cash = portfolio["cash"]
    cash_ok = portfolio["cash_ok"]
    active = portfolio["active"]
    resolved_won = portfolio["resolved_won"]
    dead = portfolio["dead"]
    active_value = portfolio["active_value"]
    resolved_value = portfolio["resolved_value"]
    portfolio_total = portfolio["portfolio_total"]
    api_error = portfolio.get("api_error")

    dead_lost = sum(float(p.get("initialValue", 0)) for p in dead)
    active_pnl = sum(float(p.get("cashPnl", 0)) for p in active)

    msg = f"💰 <b>Cartera</b>\n\n"
    if api_error:
        msg += f"⚠️ <i>Error API posiciones: {api_error[:80]}</i>\n\n"
    if cash_ok:
        msg += f"💵 Cash: <b>${cash:.2f}</b>\n"
    else:
        msg += f"💵 Cash: <i>no disponible</i>\n"

    msg += f"📊 Posiciones vivas: <b>${active_value:.2f}</b> ({len(active)} pos)\n"
    if resolved_won:
        msg += f"🏁 Pendiente pago: ${resolved_value:.2f} ({len(resolved_won)})\n"
    if cash_ok:
        msg += f"{'─'*24}\n💼 Total: <b>${portfolio_total:.2f}</b>\n"

    # ---- Posiciones activas detalladas ----
    if active:
        msg += f"\n<b>Posiciones activas:</b>\n"
        for i, pos in enumerate(active):
            title = pos.get("title", "")
            outcome = pos.get("outcome", "?")
            label = _parse_position_label(title, outcome)
            size = float(pos.get("size", 0))
            avg_price = float(pos.get("avgPrice", 0))
            cur_price = float(pos.get("curPrice", 0))
            current_value = float(pos.get("currentValue", 0))
            pct_pnl = float(pos.get("percentPnl", 0))
            cash_pnl = float(pos.get("cashPnl", 0))
            icon = "🟢" if cash_pnl >= 0 else "🔴"
            avg_c = int(round(avg_price * 100))
            cur_c = int(round(cur_price * 100))
            msg += (
                f"\n{i+1}. {icon} <b>{label}</b>\n"
                f"   {size:.1f}sh @ {avg_c}¢ → {cur_c}¢\n"
                f"   ${current_value:.2f} | {pct_pnl:+.1f}% (${cash_pnl:+.2f})\n"
            )

    # ---- Resueltas ganadas ----
    if resolved_won:
        msg += f"\n<b>🏁 Esperando pago:</b>\n"
        for pos in resolved_won:
            label = _parse_position_label(pos.get("title", ""), pos.get("outcome", "?"))
            current_value = float(pos.get("currentValue", 0))
            msg += f"  ✅ {label} → ${current_value:.2f}\n"

    # ---- Muertas (solo resumen) ----
    if dead:
        msg += f"\n<i>💀 {len(dead)} posiciones sin valor (${dead_lost:.2f} invertidos)</i>\n"

    send_telegram_paged(msg, with_menu=True)


def cmd_ordenes():
    """🗒 Órdenes pendientes — etiquetas legibles con ciudad+temp+fecha."""
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
        send_telegram("🗒 <b>Órdenes pendientes:</b> ninguna", with_menu=True)
        return

    lines = [f"🗒 <b>Órdenes pendientes: {len(orders)}</b>\n"]

    for i, order in enumerate(orders):
        price = order.get("price", "?")
        size_raw = order.get("original_size", order.get("size", "?"))
        try:
            size_str = f"{float(size_raw):.1f}sh"
        except (ValueError, TypeError):
            size_str = str(size_raw)
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
                age_str = f" ⏱{age_h:.1f}h"
            except (ValueError, TypeError, OSError):
                pass

        # Enriquecer con known_tokens (cache del bot)
        info = known_tokens.get(asset_id, {})
        question = info.get("question", "")
        token_side = info.get("side", "")

        if question:
            label = _parse_position_label(question, token_side)
            price_c = int(round(float(price) * 100)) if price != "?" else "?"
            lines.append(
                f"\n{i+1}. <b>{label}</b>\n"
                f"   BUY @ {price_c}¢ | {size_str}{age_str}"
            )
        else:
            lines.append(
                f"\n{i+1}. BUY @ ${price} | {size_str}{age_str}\n"
                f"   Token: {asset_id[:20]}..."
            )

    send_telegram_paged("\n".join(lines), with_menu=True)


def cmd_log():
    """
    📓 Resumen legible del último ciclo.
    v10.4.2: Lee desde cycle_summary.json (estructurado). Fallback a bot_state.
    """
    # Fuente primaria: cycle_summary.json
    if os.path.exists(CYCLE_SUMMARY_FILE):
        try:
            with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
                cd = json.load(f)
            ts = cd.get("timestamp_utc", "?")[:16].replace("T", " ")
            mode = cd.get("mode", "?")
            cycle_n = cd.get("cycle_number", "?")
            mgmt = cd.get("management", {})
            scan = cd.get("scan", {})
            buys = cd.get("buys", [])
            exposure = cd.get("exposure_after")
            budget = cd.get("budget_left")

            msg = f"📓 <b>Ciclo #{cycle_n}</b>\n"
            msg += f"<i>{ts} UTC | {mode}</i>\n\n"

            # Gestión
            n_kept = mgmt.get("n_kept", 0)
            n_sold = mgmt.get("n_sold", 0)
            n_res = mgmt.get("n_resolved", 0)
            n_loss = mgmt.get("n_loss_total", 0)
            msg += f"<b>Gestión:</b> {n_kept} mantenidas"
            if n_sold:
                msg += f" | {n_sold} vendidas"
            if n_res:
                msg += f" | {n_res} resueltas"
            if n_loss:
                msg += f" | 💀 {n_loss} loss total"
            msg += "\n"

            # Escaneo
            n_mkts = scan.get("markets_evaluated", 0)
            n_edge = scan.get("with_edge", 0)
            n_sel = scan.get("selected", 0)
            msg += f"<b>Escaneo:</b> {n_mkts} mercados → {n_edge} con edge → {n_sel} seleccionados\n"

            # Compras
            if buys:
                msg += f"\n<b>Compras ({len(buys)}):</b>\n"
                for b in buys:
                    trader_icon = " 🤝" if b.get("traders") else ""
                    msg += f"  🟢 {b.get('city','?')} {b.get('side','?')} ${b.get('amount',0):.2f} | edge {b.get('edge',0)}%{trader_icon}\n"
            else:
                msg += "\n<i>Sin compras este ciclo</i>\n"

            if exposure is not None:
                msg += f"\nExposición actual: <b>${exposure:.2f}</b>\n"
            if budget is not None:
                msg += f"Presupuesto libre: <b>${budget:.2f}</b>\n"

            send_telegram_paged(msg, with_menu=True)
            return
        except Exception as e:
            log.warning(f"Error leyendo cycle_summary en cmd_log: {e}")

    # Fallback: resumen en memoria
    summary = bot_state.get("last_decision_summary", "")
    if summary:
        send_telegram_paged(summary, with_menu=True)
        return

    send_telegram("📓 <b>Log</b>\n\nAún no hay ciclos registrados.", with_menu=True)


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

    v10: mejor manejo de errores + fallback a decisions.log
    """
    try:
        edge_analysis = bot_state.get("last_edge_analysis", [])
        trader_signals = bot_state.get("last_trader_signals", {})

        if not edge_analysis:
            # Fallback: intentar leer del archivo decisions.log
            if os.path.exists(_data_path("decisions.log")):
                try:
                    with open(_data_path("decisions.log"), "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    # Buscar el último ciclo
                    last_start = -1
                    for i in range(len(lines) - 1, -1, -1):
                        if "CICLO" in lines[i]:
                            last_start = i
                            break
                    if last_start >= 0:
                        cycle_text = "📋 <b>Detalle (de archivo)</b>\n\n"
                        for line in lines[last_start:last_start + 40]:
                            clean = line.strip()
                            # Quitar timestamp del log
                            if " | " in clean:
                                clean = clean.split(" | ", 1)[-1]
                            if clean:
                                # Escapar caracteres HTML para evitar HTTP 400
                                clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                cycle_text += f"{clean}\n"
                        send_telegram_paged(cycle_text, with_menu=True)
                        return
                except Exception as e:
                    log.warning(f"Error leyendo decisions.log para /detalle: {e}")

            send_telegram(
                "📋 <b>Log detallado</b>\n\nSin datos. Espera a que complete un ciclo.",
                with_menu=True,
            )
            return

        # Clasificar las líneas
        accepted = []
        near_misses = []
        no_edge = []
        duplicates = []
        kelly_low = []

        for line in edge_analysis:
            stripped = line.strip()
            if stripped.startswith("✓"):
                accepted.append(stripped)
            elif "BAJO" in stripped:
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

        # Near misses con cruce de traders
        interesting = [(e, t) for e, t in near_misses if e >= 3.0]
        if interesting:
            text += f"\n<b>🔶 NEAR MISSES (edge ≥3%, &lt; {MIN_EDGE}%):</b>\n"
            for edge_val, line_text in interesting[:8]:
                trader_info = ""
                if trader_signals:
                    for key, sigs in trader_signals.items():
                        parts = key.split("|")
                        if len(parts) >= 1:
                            city = parts[0]
                            if city.lower() in line_text.lower():
                                traders = [s["trader"] for s in sigs]
                                trader_info = f"\n    👀 {', '.join(traders[:4])}"
                                break
                text += f"  🔶 edge={edge_val:.1f}% | {line_text[:65]}{trader_info}\n"
            if len(interesting) > 8:
                text += f"  ... y {len(interesting) - 8} más\n"
        else:
            text += f"\n<i>Sin near misses ≥3%</i>\n"

        send_telegram_paged(text, with_menu=True)

    except Exception as e:
        log.error(f"Error en /detalle: {e}")
        send_telegram(f"❌ Error en detalle: {str(e)[:200]}", with_menu=True)


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
    🔍 Traders Intel: señales + coincidencias con posiciones activas.
    v10.4.2: cruza señales con cartera actual.
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
    text += f"<i>{generated} UTC</i>\n"
    text += f"Analizados: {n_traders} | Calidad: {n_quality} | Skip: {n_skipped}\n"
    text += f"Señales: {n_signals} | Consenso: {n_consensus}\n"

    if quality_names:
        text += f"\n⭐ <b>Calidad:</b> {', '.join(quality_names[:6])}\n"

    # Cruce con posiciones activas — filtra por ciudad + lado + fecha no pasada
    portfolio = _get_portfolio_and_positions()
    active_positions = set()  # set de (city_lower, outcome_lower)
    if portfolio:
        for pos in portfolio["active"]:
            city = parse_city_from_title(pos.get("title", ""))
            outcome = pos.get("outcome", "")
            if city != "?" and outcome:
                active_positions.add((city.lower(), outcome.lower()))

    today_str = date.today().isoformat()  # "2026-03-28"

    if active_positions and n_signals > 0:
        text += f"\n<b>🔗 Señales alineadas con cartera:</b>\n"
        found_any = False
        for s in data.get("signals", []):
            if s.get("is_reference"):
                continue
            city = s.get("city", "")
            outcome = s.get("outcome", "")
            sig_date = s.get("date", "")  # formato "2026-03-28" o "Mar28"
            # Filtrar: ciudad+lado coincide con posición activa
            if (city.lower(), outcome.lower()) not in active_positions:
                continue
            # Filtrar: fecha no pasada (si el formato es ISO)
            if sig_date and len(sig_date) == 10:
                if sig_date < today_str:
                    continue
            icon = "🤝" if s.get("has_consensus") else "📍"
            price = s.get("avg_price", 0)
            text += f"  {icon} {city} {outcome} {sig_date} @ {int(price*100)}¢\n"
            found_any = True
        if not found_any:
            text += "  <i>Ninguna señal de traders coincide con tus posiciones actuales</i>\n"

    # Último scan y análisis
    scan_ts = bot_state.get("last_trader_scan")
    analysis_ts = bot_state.get("last_trader_analysis")
    if scan_ts:
        text += f"\nScan: {scan_ts.strftime('%d/%m %H:%M UTC')}"
    if analysis_ts:
        text += f" | Análisis: {analysis_ts.strftime('%d/%m %H:%M UTC')}"
    if scan_ts or analysis_ts:
        text += "\n"

    if n_signals == 0:
        text += "\n<i>Sin señales accionables ahora.</i>\n"
    else:
        text += f"\n<b>Señales activas ({n_signals}):</b>\n"
        shown = 0
        for s in data.get("signals", []):
            if s.get("is_reference"):
                continue
            if shown >= 10:
                text += f"<i>... y {n_signals - shown} más</i>\n"
                break
            icon = "🤝" if s.get("has_consensus") else "📍"
            city = s.get("city", "?")
            date_str = s.get("date", "?")
            outcome = s.get("outcome", "?")
            price = s.get("avg_price", 0)
            price_c = int(round(price * 100))
            text += f"{icon} {city} {outcome} {date_str} @ {price_c}¢\n"
            shown += 1

    send_telegram_paged(text, with_menu=True)


def cmd_rendimiento():
    """📈 Rendimiento: portfolio actual + estadísticas desde performance.json."""
    # Portfolio en tiempo real
    portfolio = _get_portfolio_and_positions()
    text = f"📈 <b>Rendimiento</b>\n\n"

    if portfolio:
        cash = portfolio["cash"]
        cash_ok = portfolio["cash_ok"]
        active_value = portfolio["active_value"]
        resolved_value = portfolio["resolved_value"]
        active = portfolio["active"]
        resolved_won = portfolio["resolved_won"]
        active_pnl = sum(float(p.get("cashPnl", 0)) for p in active)

        if cash_ok:
            text += f"💵 Cash: ${cash:.2f}\n"
        text += f"📊 Posiciones vivas: ${active_value:.2f}"
        if active_pnl != 0:
            text += f" ({active_pnl:+.2f})"
        text += "\n"
        if resolved_value > 0:
            text += f"🏁 Pendiente pago: ${resolved_value:.2f} ({len(resolved_won)})\n"
        if cash_ok:
            total = portfolio["portfolio_total"]
            text += f"💼 Total: <b>${total:.2f}</b>\n"
        text += "\n"

    # Estadísticas históricas
    stats = get_performance_summary()
    if not stats:
        text += "<i>Sin trades registrados todavía.</i>\n"
        send_telegram(text, with_menu=True)
        return

    text += f"<b>Trades (v10.2+):</b>\n"
    text += f"  Compras: {stats['total_buys']} | Ventas: {stats['total_sells']}\n"
    if stats.get('pending_sells', 0) > 0:
        text += f"  ⏳ Pendientes fill: {stats['pending_sells']}\n"
    text += f"  Invertido: ${stats['total_invested']:.2f}\n"
    text += f"  PnL ventas: <b>${stats['sell_pnl']:+.2f}</b>\n"

    text += f"\n<b>Salidas:</b>\n"
    text += f"  💰 TP: {stats['take_profits']} | 🔻 SL: {stats['stop_losses']} | 🔄 Reeval: {stats['reevals']}\n"

    if stats['confirmed_count'] + stats['unconfirmed_count'] > 0:
        text += f"\n<b>Con/sin trader:</b>\n"
        if stats['confirmed_count'] > 0:
            text += f"  🤝 {stats['confirmed_count']} ops → ${stats['confirmed_pnl']:+.2f}\n"
        if stats['unconfirmed_count'] > 0:
            text += f"  🔹 {stats['unconfirmed_count']} ops → ${stats['unconfirmed_pnl']:+.2f}\n"

    if stats['top_cities']:
        text += f"\n<b>Top ciudades:</b>\n"
        for city, count in stats['top_cities']:
            pnl = stats['city_pnl'].get(city, 0)
            text += f"  {city}: {count} ops, ${pnl:+.2f}\n"

    text += f"\n<i>⚠️ PnL fiable: dashboard Polymarket.</i>\n"
    send_telegram_paged(text, with_menu=True)


def cmd_info():
    """ℹ️ Bloque resumen del bot para pegar en ChatGPT/Claude."""
    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    last_str = bot_state["last_run"].strftime('%Y-%m-%d %H:%M UTC') if bot_state["last_run"] else "Nunca"

    # Último ciclo desde cycle_summary.json
    cycle_block = ""
    if os.path.exists(CYCLE_SUMMARY_FILE):
        try:
            with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
                cd = json.load(f)
            mgmt = cd.get("management", {})
            scan = cd.get("scan", {})
            buys = cd.get("buys", [])
            buys_str = ", ".join(
                f"{b.get('city','?')} {b.get('side','?')} ${b.get('amount',0):.2f}"
                for b in buys
            ) if buys else "ninguna"
            exp = cd.get("exposure_after")
            bud = cd.get("budget_left")
            cycle_block = (
                f"\nCiclo #{cd.get('cycle_number','?')} ({cd.get('timestamp_utc','?')[:16]} UTC)\n"
                f"  Gestión: {mgmt.get('n_kept',0)} mantenidas, {mgmt.get('n_sold',0)} vendidas, "
                f"{mgmt.get('n_resolved',0)} resueltas\n"
                f"  Escaneo: {scan.get('markets_evaluated',0)} mercados → "
                f"{scan.get('selected',0)} seleccionados\n"
                f"  Compras: {buys_str}\n"
            )
            if exp is not None:
                cycle_block += f"  Exposición: ${exp:.2f}"
            if bud is not None:
                cycle_block += f" | Libre: ${bud:.2f}"
            if exp is not None or bud is not None:
                cycle_block += "\n"
        except Exception:
            pass

    # Estadísticas
    stats = get_performance_summary()
    perf_block = ""
    if stats:
        perf_block = (
            f"\n{stats['total_buys']} compras, {stats['total_sells']} ventas\n"
            f"PnL ventas: ${stats['sell_pnl']:+.2f}\n"
            f"TP: {stats['take_profits']} | SL: {stats['stop_losses']} | Reeval: {stats['reevals']}\n"
        )

    text = (
        f"<b>BOT POLYMARKET v10.4.2</b>\n"
        f"Modo: {modo} | Bankroll: ${BANKROLL:.2f}\n"
        f"Edge mín: {MIN_EDGE}% | SL: {STOP_LOSS_PCT}% | TP: +{TAKE_PROFIT_PCT}%\n"
        f"Exp máx: {int(MAX_EXPOSURE_PCT*100)}% | Min bet: ${MIN_BET:.2f}\n"
        f"Schedule: {schedule} UTC\n"
        f"Ciclos completados: {bot_state['cycle_count']}\n"
        f"Último: {last_str}\n"
    )
    if cycle_block:
        text += f"\n<b>Último ciclo:</b>{cycle_block}"
    if perf_block:
        text += f"\n<b>Rendimiento (v10.2+):</b>{perf_block}"
    text += (
        f"\n<b>Arquitectura:</b>\n"
        f"~330 mercados temp | Open-Meteo | normal(μ,σ)\n"
        f"Sigma: D0=1.2 D1=1.5 D2=2.0 D3=2.5 D4+=3.0\n"
        f"Half-Kelly | Railway EU-West (Amsterdam)\n"
        f"⚠️ Polymarket resuelve con Weather Underground, no Open-Meteo"
    )

    send_telegram_paged(text, with_menu=True)


COMMANDS = {
    "estado": cmd_estado, "cartera": cmd_cartera, "ordenes": cmd_ordenes,
    "log": cmd_log, "logfull": cmd_logfull, "forzar": cmd_forzar,
    "modo": cmd_modo, "traders": cmd_traders, "rendimiento": cmd_rendimiento,
    "info": cmd_info,
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
            req.add_header("User-Agent", "polymarket-bot/0.10")
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
# FUNCIONES: EXPOSICIÓN REAL (v10)
# =============================================================

def get_current_exposure():
    """
    Consulta la Data API para saber cuánto dinero hay invertido en posiciones.

    Esto es CRÍTICO: sin esto, cada ciclo cree que tiene presupuesto completo
    y puede sobreinvertir (bug de v9 que causó 80% de exposición).

    Devuelve total_invested (float): dinero real comprometido en posiciones vivas.
    Solo cuenta posiciones con valor actual > $0.01 (ignora las resueltas a 0).
    """
    funder = os.getenv("FUNDER", "")
    if not funder:
        return 0.0
    try:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "50",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"{DATA_API_URL}/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "polymarket-bot/0.10")
        resp = urllib.request.urlopen(req, timeout=15)
        positions = json.loads(resp.read())

        total_exposure = 0.0
        for p in positions:
            current_value = float(p.get("currentValue", 0))
            cur_price = float(p.get("curPrice", 0))
            # Exposición = lo que VALE ahora, no lo que pagamos
            # Una posición comprada a $2.50 que vale $0.11 es $0.11 de exposición,
            # no $2.50 — ese dinero ya está perdido.
            # Ignorar posiciones < $0.01 (resueltas a $0)
            if current_value <= 0.01:
                continue
            # v10.3 Fix Bug #4: posiciones resueltas (curPrice >= 0.98) son cash
            # garantizado, NO riesgo. No deben contar como exposición.
            # Bug real: Shanghai resuelta a $8.04 bloqueó $8 de presupuesto,
            # el bot encontró 15 oportunidades y no pudo entrar en ninguna.
            if cur_price >= 0.98:
                continue
            total_exposure += current_value

        return total_exposure
    except Exception as e:
        log.warning(f"Error consultando exposición: {e}")
        # Si falla la consulta, asumir que NO hay presupuesto disponible
        # Es mejor no apostar que apostar de más
        return BANKROLL  # Conservador: asume todo invertido


def get_cash_balance(client):
    """
    Obtiene el cash (USDC) disponible para operar.

    v10.2 fix: client.get_balance() no existe en py_clob_client.
    El método correcto es get_balance_allowance() con AssetType.COLLATERAL.

    Devuelve: (cash_float, success_bool)
    """
    if client is None:
        return 0.0, False
    try:
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        result = client.get_balance_allowance(params)
        # result puede ser dict con 'balance' key, o string numérico
        if isinstance(result, dict):
            raw = result.get("balance", 0)
        else:
            raw = result
        # El balance viene en unidades base (6 decimales para USDC)
        cash = float(raw) / 1e6
        return cash, True
    except Exception as e:
        log.warning(f"Error consultando cash balance: {e}")
        return 0.0, False


def get_effective_bankroll(client=None):
    """
    Calcula el bankroll REAL: cash libre + valor de posiciones.

    El BANKROLL de Railway es un tope máximo. Pero si hemos perdido dinero,
    el bankroll real es menor.

    Si cash no se puede leer, usa BANKROLL como fallback.
    """
    cash_balance, cash_ok = get_cash_balance(client)
    positions_value = 0.0

    # ---- Valor de posiciones activas ----
    funder = os.getenv("FUNDER", "")
    if funder:
        try:
            params = urllib.parse.urlencode({
                "user": funder.lower(),
                "sizeThreshold": "0",
                "limit": "50",
                "sortBy": "CURRENT",
                "sortDirection": "DESC",
            })
            url = f"{DATA_API_URL}/positions?{params}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-bot/0.10")
            resp = urllib.request.urlopen(req, timeout=15)
            positions = json.loads(resp.read())
            positions_value = sum(float(p.get("currentValue", 0)) for p in positions)
        except Exception as e:
            log.warning(f"Error consultando posiciones: {e}")

    effective = cash_balance + positions_value

    if not cash_ok or cash_balance < 0.01:
        effective = BANKROLL
        log.info(f"Bankroll: ${effective:.2f} (cash no disponible, usando BANKROLL tope=${BANKROLL:.2f}, posiciones=${positions_value:.2f})")
    else:
        # Tope: nunca asumir más del BANKROLL depositado
        effective = min(effective, BANKROLL)
        # Mínimo: $1 para que el bot no se pare totalmente
        effective = max(effective, 1.0)
        log.info(f"Bankroll: ${effective:.2f} (cash=${cash_balance:.2f} + posiciones=${positions_value:.2f}, tope=${BANKROLL:.2f})")

    return effective


# =============================================================
# GESTIÓN ACTIVA DE POSICIONES (v10.1)
# =============================================================

# v10.3: Set de asset_ids ya marcados como LOSS_TOTAL para no repetir
_loss_total_tracked = set()


def _mark_micro_as_loss_total(position, dl):
    """
    v10.3 Fix Bug #8: Marca una posición micro (<$0.10) como pérdida total.

    Bug real: Chongqing NO 18°C (17 shares × 0.1¢ = $0.017) reaparecía ciclo
    tras ciclo en gestión. Polymarket rechaza ventas tan pequeñas.

    Solo registra una vez por sesión (usa _loss_total_tracked set en memoria).
    """
    asset_id = position.get("asset", "")
    if asset_id in _loss_total_tracked:
        return  # Ya marcada esta sesión

    _loss_total_tracked.add(asset_id)

    outcome = position.get("outcome", "?")
    title = position.get("title", "?")[:50]
    city = parse_city_from_title(title)
    initial_value = float(position.get("initialValue", 0))
    current_value = float(position.get("currentValue", 0))

    dl.append(f"    💀 LOSS_TOTAL: {outcome} {city} | invertido ${initial_value:.2f} → vale ${current_value:.3f}")

    track_trade("LOSS_TOTAL",
        city=city,
        side=outcome,
        initial_value=initial_value,
        current_value=current_value,
        loss=round(-initial_value, 2),
        reason="micro_position_unsellable",
    )

def manage_positions(client, dl):
    """
    Gestión activa: stop-loss, take-profit, Y re-evaluación con datos frescos.

    Basado en investigación de traders exitosos:
      - Entire-Hood: 58% gestión activa, 0 pérdidas por resolución
      - Clave: detecta cuándo la previsión cambia y sale antes

    Lógica por posición (en orden de prioridad):
      1. Si PnL% < STOP_LOSS_PCT (-25%) → VENDER (cortar pérdida)
      2. Si PnL% > TAKE_PROFIT_PCT (+40%) → VENDER (asegurar ganancia)
      3. RE-EVALUACIÓN: consultar previsión fresca. Si edge ahora
         es negativo (< -3%) → VENDER (el mercado tiene razón)

    Devuelve: (n_sold, capital_freed)
    """
    if DRY_RUN:
        dl.append(f"GESTIÓN: modo DRY RUN — solo análisis, sin ventas")

    funder = os.getenv("FUNDER", "")
    if not funder:
        dl.append(f"GESTIÓN: sin FUNDER, saltando")
        return {"n_sold": 0, "capital_freed": 0, "kept": 0, "resolved": 0, "sells": [], "sold_token_ids": set()}

    # ---- Obtener posiciones actuales ----
    try:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "50",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"{DATA_API_URL}/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "polymarket-bot/0.10")
        resp = urllib.request.urlopen(req, timeout=15)
        positions = json.loads(resp.read())
    except Exception as e:
        dl.append(f"GESTIÓN: error obteniendo posiciones: {e}")
        return {"n_sold": 0, "capital_freed": 0, "kept": 0, "resolved": 0, "sells": [], "sold_token_ids": set()}

    # ---- Filtrar posiciones de temperatura con valor ----
    temp_positions = []
    n_micro = 0  # v10.3: posiciones demasiado pequeñas para vender
    for p in positions:
        title = p.get("title", "")
        if not re.search(r"temperature", title, re.IGNORECASE):
            continue
        current_value = float(p.get("currentValue", 0))
        if current_value < 0.01:
            continue  # Ya resuelta a $0, nada que hacer

        # v10.3 Fix Bug #8: Posiciones micro (<$0.10) no se pueden vender
        # Polymarket rechaza órdenes tan pequeñas. En vez de intentar ciclo
        # tras ciclo, las marcamos como pérdida total una sola vez.
        if current_value < 0.10:
            n_micro += 1
            _mark_micro_as_loss_total(p, dl)
            continue

        temp_positions.append(p)

    if n_micro > 0:
        dl.append(f"  💀 {n_micro} posiciones micro (<$0.10) → pérdida total")

    if not temp_positions:
        dl.append(f"GESTIÓN: sin posiciones de temperatura gestionables")
        return {"n_sold": 0, "capital_freed": 0, "kept": 0, "resolved": 0, "sells": [], "sold_token_ids": set()}

    dl.append(f"\nGESTIÓN DE POSICIONES: {len(temp_positions)} posiciones activas")
    dl.append(f"  Stop-loss: {STOP_LOSS_PCT}% | Take-profit: +{TAKE_PROFIT_PCT}% | Re-eval: edge<-3%")

    # ---- Cache de previsiones para re-evaluación ----
    forecast_cache = {}

    # ---- Evaluar cada posición ----
    to_sell = []        # lista de (posición, tipo, razón)
    keeping = []        # info de las que mantenemos
    n_resolved = 0      # mercados ya resueltos (curPrice >= 0.98)

    for p in temp_positions:
        title_full = p.get("title", "?")
        title = title_full[:55]
        outcome = p.get("outcome", "?")
        size = float(p.get("size", 0))
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", 0))
        pct_pnl = float(p.get("percentPnl", 0))
        cash_pnl = float(p.get("cashPnl", 0))
        initial_value = float(p.get("initialValue", 0))
        asset_id = p.get("asset", "")

        # Fix v10.2: Si curPrice >= 0.98, el mercado se resolvió a YES
        # El orderbook ya no existe — intentar vender da error.
        # Dejar que resuelva: si ganamos, paga $1.00 por share automáticamente.
        if cur_price >= 0.98:
            dl.append(f"  🏁 RESUELTO ({outcome} @ {cur_price:.2f}) | {title} | Esperando pago")
            # v10.4 Fix Bug #12: NO añadir a keeping — son resueltas, no mantenidas
            n_resolved += 1
            continue

        # Sin asset_id no podemos vender
        if not asset_id:
            dl.append(f"  ⚠ {outcome} {title} | sin asset_id")
            continue

        label = f"{outcome:3s} {title}"

        # ---- CHECK 1: Stop-loss (prioridad máxima) ----
        if pct_pnl <= STOP_LOSS_PCT:
            reason = f"🔻 STOP-LOSS ({pct_pnl:+.1f}% < {STOP_LOSS_PCT}%)"
            to_sell.append((p, "stop_loss", reason))
            dl.append(f"  {reason} | {label} | ${cash_pnl:+.2f}")
            continue

        # ---- CHECK 2: Take-profit ----
        if pct_pnl >= TAKE_PROFIT_PCT:
            reason = f"💰 TAKE-PROFIT ({pct_pnl:+.1f}% > +{TAKE_PROFIT_PCT}%)"
            to_sell.append((p, "take_profit", reason))
            dl.append(f"  {reason} | {label} | ${cash_pnl:+.2f}")
            continue

        # ---- CHECK 3: Re-evaluación con previsión fresca ----
        parsed = parse_temperature_question(title_full)
        if not parsed or not parsed.get("date_str"):
            dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | no parseable")
            keeping.append(p)
            continue

        city = parsed["city"]
        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | fecha inválida")
            keeping.append(p)
            continue

        try:
            days_ahead = (date.fromisoformat(date_iso) - date.today()).days
        except ValueError:
            keeping.append(p)
            continue

        # Si ya pasó la fecha, no re-evaluar (se resolverá sola)
        if days_ahead < 0:
            dl.append(f"  ⏳ RESOLUCIÓN pendiente | {label}")
            keeping.append(p)
            continue

        # Obtener previsión fresca (con cache)
        if city not in forecast_cache:
            station = RESOLUTION_STATIONS.get(city)
            if station:
                try:
                    forecast_cache[city] = get_forecast(station["lat"], station["lon"])
                except Exception:
                    forecast_cache[city] = None
            else:
                forecast_cache[city] = None

        fc = forecast_cache.get(city)
        if not fc or date_iso not in fc:
            dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | sin previsión")
            keeping.append(p)
            continue

        # Recalcular probabilidad con datos frescos
        forecast_max = fc[date_iso]["temp_max"]
        threshold = parsed["temp_threshold"]
        threshold_c = (threshold - 32) * 5 / 9 if parsed["unit"] == "F" else float(threshold)

        threshold_high = parsed.get("temp_threshold_high")
        threshold_high_c = None
        if threshold_high is not None:
            threshold_high_c = (threshold_high - 32) * 5 / 9 if parsed["unit"] == "F" else float(threshold_high)

        our_prob_yes = estimate_prob(forecast_max, threshold_c, parsed["condition"], days_ahead, threshold_high_c)

        # ¿Qué lado tenemos? Calcular edge actual
        if outcome.upper() == "YES":
            our_prob = our_prob_yes
            mkt_price = cur_price
        else:
            our_prob = 1.0 - our_prob_yes
            mkt_price = 1.0 - cur_price

        edge_pct = (our_prob - mkt_price) * 100

        # Si edge es negativo: la previsión dice que estamos equivocados
        if edge_pct < -3.0:
            reason = (f"🔄 RE-EVAL edge={edge_pct:+.1f}% "
                      f"forecast={forecast_max:.1f}°C "
                      f"nuestro={our_prob*100:.0f}% vs mercado={mkt_price*100:.0f}%")
            to_sell.append((p, "reeval", reason))
            dl.append(f"  {reason}")
            dl.append(f"    → {label} | PnL={pct_pnl:+.1f}% (${cash_pnl:+.2f})")
        else:
            dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) edge={edge_pct:+.1f}% | {label}")
            keeping.append(p)

    if not to_sell:
        dl.append(f"\n  Sin posiciones que cerrar este ciclo")
        return {"n_sold": 0, "capital_freed": 0, "kept": len(keeping), "resolved": n_resolved, "sells": [], "sold_token_ids": set()}

    # ---- Ejecutar ventas ----
    dl.append(f"\n  VENDIENDO {len(to_sell)} posiciones:")
    n_sold = 0
    capital_freed = 0.0
    sell_summaries = []  # v10.2: para resumen de Telegram

    for p, sell_type, reason in to_sell:
        asset_id = p.get("asset", "")
        outcome = p.get("outcome", "?")
        size = float(p.get("size", 0))
        cur_price = float(p.get("curPrice", 0))
        title = p.get("title", "?")[:50]
        city = parse_city_from_title(title)

        # Precio agresivo: ligeramente por debajo del mercado para asegurar fill
        sell_price = round(max(0.01, cur_price - SELL_AGGRESSION), 2)

        # Shares: vender todo
        shares_to_sell = round(size, 2)
        if shares_to_sell < 0.1:
            dl.append(f"    ⚠ {outcome} {title} | muy pocas shares ({shares_to_sell})")
            continue

        estimated_return = round(shares_to_sell * sell_price, 2)

        # No intentar vender posiciones que no valen nada
        # Polymarket rechaza ventas con "not enough balance/allowance" si es muy poco
        if estimated_return < 0.10:
            dl.append(f"    ⏭ {outcome} {title} | valor ~${estimated_return:.2f} < $0.10, no vale la pena")
            continue

        log.info(f"{'[DRY] ' if DRY_RUN else ''}VENTA: {outcome} {shares_to_sell}sh × ${sell_price:.2f} | {title}")

        if DRY_RUN:
            dl.append(f"    [DRY] SELL {outcome} {shares_to_sell}sh × ${sell_price:.2f} = ~${estimated_return:.2f} | {title}")
            n_sold += 1
            capital_freed += estimated_return
            sell_summaries.append({"type": sell_type, "city": city, "side": outcome, "pnl_pct": 0})
            continue

        try:
            order_args = OrderArgs(
                token_id=asset_id,
                price=sell_price,
                size=shares_to_sell,
                side=SELL,
            )
            signed = client.create_order(order_args)
            resp = client.post_order(signed, OrderType.GTC)
            oid = resp.get("orderID", resp.get("id", "?"))
            status = resp.get("status", "?")

            dl.append(f"    📤 SELL orden colocada: {outcome} {shares_to_sell}sh × ${sell_price:.2f} → {status} | {title}")
            n_sold += 1
            capital_freed += estimated_return

            pct = float(p.get("percentPnl", 0))
            sell_summaries.append({"type": sell_type, "city": city, "side": outcome, "pnl_pct": pct})

            # Notificar por Telegram
            if sell_type == "stop_loss":
                icon, type_label = "🔻", "Stop-loss"
            elif sell_type == "take_profit":
                icon, type_label = "💰", "Take-profit"
            else:
                icon, type_label = "🔄", "Re-evaluación"
            send_telegram(
                f"{icon} <b>{type_label} — orden colocada</b>\n"
                f"{outcome} {city}\n"
                f"Venta: {shares_to_sell}sh × ${sell_price:.2f} (precio límite)\n"
                f"PnL estimado: {pct:+.1f}% (${float(p.get('cashPnl', 0)):+.2f})\n"
                f"<i>⏳ Pendiente de fill — precio real puede diferir</i>"
            )

            # v10.3 Fix Bug #7: Registrar como SELL_PENDING, NO como SELL
            # Solo se convierte en SELL cuando audit_check_sell_fills confirma el fill.
            # Bug real: Chongqing stop-loss se registró como vendida pero la orden
            # nunca se llenó (nadie quiso comprar a 1¢). Performance.json mentía.
            track_trade("SELL_PENDING",
                reason=sell_type,
                city=city,
                side=outcome,
                price=sell_price,
                shares=shares_to_sell,
                return_est=estimated_return,
                avg_buy_price=float(p.get("avgPrice", 0)),
                pnl_pct=pct,
                pnl_cash=float(p.get("cashPnl", 0)),
                order_id=oid,
            )

            # Registrar para verificar fill en próximo ciclo
            audit_register_pending_sell(
                order_id=oid, city=city,
                side=outcome, price=sell_price, shares=shares_to_sell,
                return_est=estimated_return, reason=sell_type,
            )

        except Exception as e:
            dl.append(f"    ❌ ERROR vendiendo {outcome} {title}: {e}")
            log.error(f"Error vendiendo posición: {e}")

    dl.append(f"\n  Resultado: {n_sold} vendidas | ~${capital_freed:.2f} liberados")
    # v10.4 Fix Bug #9: devolver token_ids vendidos para evitar re-entrada mismo ciclo
    sold_token_ids = set(p.get("asset", "") for p, _, _ in to_sell if p.get("asset"))
    return {
        "n_sold": n_sold,
        "capital_freed": capital_freed,
        "kept": len(keeping),
        "resolved": n_resolved,
        "sells": sell_summaries,
        "sold_token_ids": sold_token_ids,
    }


AUDIT_FILE = _data_path("audit.json")

def load_audit_data():
    """Carga datos de auditoría acumulativos."""
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pending_sells": [], "forecast_vs_real": [], "errors": []}


def save_audit_data(data):
    """Guarda datos de auditoría."""
    # Limitar tamaño
    for key in ["pending_sells", "forecast_vs_real", "errors"]:
        if key in data and len(data[key]) > 200:
            data[key] = data[key][-200:]
    try:
        with open(AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando audit: {e}")


def audit_check_sell_fills(client, dl):
    """
    Verifica si las órdenes de VENTA pendientes se llenaron.

    v10.3 Fix Bug #7: Ahora actualiza performance.json cuando confirma fill.
    Bug real: Chongqing stop-loss se registró como vendida en performance.json,
    pero la orden nunca se llenó (nadie compra a 1¢). El tracking mentía.

    Flujo:
      1. Lee pending_sells de audit.json (orden_id, ciudad, precio)
      2. Consulta open_orders del CLOB
      3. Si una pending_sell ya NO está en open_orders → se llenó (o cancelada)
      4. Actualiza SELL_PENDING → SELL en performance.json
      5. Ventas pendientes >24h → probablemente no se llenarán, marcar como SELL_FAILED
    """
    audit = load_audit_data()
    pending = audit.get("pending_sells", [])

    if not pending:
        return

    # Obtener órdenes abiertas actuales
    try:
        open_orders = get_open_orders(client)
    except Exception:
        return

    open_ids = set(o.get("id", "") for o in open_orders)
    still_pending = []
    filled = []
    expired = []

    for sell in pending:
        order_id = sell.get("order_id", "")
        age_hours = 0
        try:
            placed = datetime.fromisoformat(sell.get("timestamp", ""))
            age_hours = (datetime.now(timezone.utc) - placed).total_seconds() / 3600
        except Exception:
            pass

        if order_id in open_ids:
            # Sigue pendiente
            if age_hours > 24:
                # Llevan más de 24h sin llenarse — probablemente no se llenarán
                expired.append(sell)
                dl.append(f"  ⚠ Venta expirada >24h: {sell.get('city', '?')} {sell.get('side', '?')} | ${sell.get('price', 0):.2f} — marcando como fallida")
            elif age_hours > 12:
                dl.append(f"  ⏳ Venta pendiente >12h: {sell.get('city', '?')} {sell.get('side', '?')} | ${sell.get('price', 0):.2f}")
                still_pending.append(sell)
            else:
                still_pending.append(sell)
        else:
            # Ya no está en open_orders → se llenó (o fue cancelada por stale cleanup)
            filled.append(sell)
            dl.append(f"  ✅ Venta llenada: {sell.get('city', '?')} {sell.get('side', '?')} | ~${sell.get('return_est', 0):.2f} recuperados")

    audit["pending_sells"] = still_pending
    save_audit_data(audit)

    # v10.3: Actualizar performance.json — convertir SELL_PENDING → SELL para fills confirmados
    if filled or expired:
        _confirm_sell_fills_in_performance(filled, expired, dl)

    if filled or expired:
        n_filled = len(filled)
        n_expired = len(expired)
        dl.append(f"  FILLS: {n_filled} confirmadas | {n_expired} expiradas | {len(still_pending)} pendientes")
        if n_filled > 0:
            send_telegram(
                f"✅ <b>{n_filled} venta(s) confirmada(s)</b>\n"
                + "\n".join(f"  {s.get('city','?')} {s.get('side','?')} ~${s.get('return_est',0):.2f}" for s in filled)
            )


def _confirm_sell_fills_in_performance(filled, expired, dl):
    """
    Actualiza performance.json: SELL_PENDING → SELL (confirmadas) o SELL_FAILED (expiradas).
    Busca por order_id para hacer match exacto.
    """
    if not os.path.exists(PERFORMANCE_FILE):
        return

    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return

    filled_ids = set(s.get("order_id", "") for s in filled)
    expired_ids = set(s.get("order_id", "") for s in expired)

    updated = 0
    for entry in history:
        if entry.get("action") != "SELL_PENDING":
            continue
        oid = entry.get("order_id", "")
        if oid in filled_ids:
            entry["action"] = "SELL"
            entry["fill_confirmed"] = datetime.now(timezone.utc).isoformat()
            updated += 1
        elif oid in expired_ids:
            entry["action"] = "SELL_FAILED"
            entry["fail_reason"] = "expired_no_fill_24h"
            entry["failed_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1

    if updated > 0:
        try:
            with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            dl.append(f"  📝 performance.json: {updated} entradas actualizadas")
        except Exception as e:
            log.warning(f"Error actualizando performance.json: {e}")


def audit_register_pending_sell(order_id, city, side, price, shares, return_est, reason):
    """Registra una orden de venta pendiente para seguimiento."""
    audit = load_audit_data()
    audit["pending_sells"].append({
        "order_id": order_id,
        "city": city,
        "side": side,
        "price": price,
        "shares": shares,
        "return_est": return_est,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_audit_data(audit)


def audit_check_forecasts(dl):
    """
    Compara previsiones pasadas con temperatura REAL observada.

    Open-Meteo devuelve datos observados para fechas pasadas.
    Si ayer predijimos 16°C para Paris y hoy Open-Meteo dice que
    fue 15°C, registramos el error (1°C) para calibrar sigma.
    """
    if not os.path.exists(PERFORMANCE_FILE):
        return

    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            perf = json.load(f)
    except Exception:
        return

    # Buscar BUYs de días pasados sin verificación
    audit = load_audit_data()
    already_checked = set(
        f"{v.get('city')}|{v.get('date')}"
        for v in audit.get("forecast_vs_real", [])
    )

    to_check = []
    for entry in perf:
        if entry.get("action") != "BUY":
            continue
        market_date = entry.get("date", "")
        city = entry.get("city", "")
        if not market_date or not city:
            continue
        key = f"{city}|{market_date}"
        if key in already_checked:
            continue
        try:
            days_ago = (date.today() - date.fromisoformat(market_date)).days
        except ValueError:
            continue
        # Solo verificar mercados de ayer o antes (ya resueltos)
        if days_ago >= 1:
            to_check.append(entry)
            already_checked.add(key)

    if not to_check:
        return

    # Consultar temperatura real para cada ciudad/fecha
    checked_cities = {}
    n_checked = 0

    for entry in to_check[:10]:  # Max 10 por ciclo para no saturar API
        city = entry["city"]
        market_date = entry["date"]

        # Obtener previsión (que para fechas pasadas es dato real)
        if city not in checked_cities:
            station = RESOLUTION_STATIONS.get(city)
            if not station:
                continue
            try:
                checked_cities[city] = get_forecast(station["lat"], station["lon"])
            except Exception:
                continue

        fc = checked_cities.get(city)
        if not fc or market_date not in fc:
            continue

        real_temp = fc[market_date]["temp_max"]
        forecast_temp = entry.get("forecast_max", 0)
        error = round(real_temp - forecast_temp, 1)

        record = {
            "city": city,
            "date": market_date,
            "forecast": forecast_temp,
            "real": real_temp,
            "error_c": error,
            "abs_error_c": abs(error),
            "side": entry.get("side", "?"),
            "edge_pct": entry.get("edge_pct", 0),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        audit["forecast_vs_real"].append(record)
        n_checked += 1

        emoji = "✅" if abs(error) <= 1.0 else "⚠️" if abs(error) <= 2.0 else "❌"
        dl.append(f"  {emoji} {city} {market_date}: previsión={forecast_temp:.1f}°C real={real_temp:.1f}°C error={error:+.1f}°C")

    if n_checked > 0:
        # Calcular error medio global
        all_errors = [v["abs_error_c"] for v in audit.get("forecast_vs_real", [])]
        if all_errors:
            avg_error = sum(all_errors) / len(all_errors)
            dl.append(f"  📊 Error medio acumulado: {avg_error:.1f}°C ({len(all_errors)} mercados)")

    save_audit_data(audit)


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
    # v10: sigma más alta = modelo más humilde
    # v9 (0.8/1.0/1.4/1.8) sobreconfiaba: 0/5 en mercados resueltos
    # Ahora: reconocemos que Open-Meteo tiene error típico de 1-2°C
    return {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5}.get(days_ahead, 3.0 if days_ahead <= 5 else 3.5)


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
    # Mínimo 1 share (Polymarket acepta fracciones)
    if shares < 1.0:
        amount = round(1.0 * aggressive_price, 2)
        if amount > bankroll * MAX_BET_PCT or amount < MIN_BET:
            return None
        shares = 1.0
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

    # v10.1: Bankroll real (no el hardcoded de $15)
    effective_bankroll = get_effective_bankroll(client)

    log.info("=" * 65)
    log.info(f"BOT v10.4.5 | {today_str} | {mode_label} | ${effective_bankroll:.2f} (tope ${BANKROLL:.2f})")
    log.info("=" * 65)

    # Decision log: registrar inicio
    dl = []  # Lista de líneas para el log de decisiones
    dl.append(f"{'='*50}")
    dl.append(f"CICLO {bot_state['cycle_count']+1} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | {mode_label}")
    dl.append(f"BANKROLL: ${effective_bankroll:.2f} (tope ${BANKROLL:.2f}) | MIN_EDGE={MIN_EDGE}%")
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
        # v10.3: Alerta Telegram si no hay señales (Bug #6)
        send_telegram("⚠️ <b>Ciclo sin señales de traders</b>\nsignals.json vacío o expirado. Compras sin confirmación de trader.")

    # ---- PASO 0: STALE ----
    open_orders = get_open_orders(client)
    cancelled = clean_stale_orders(client, open_orders, ORDER_MAX_AGE_HOURS)
    if cancelled > 0:
        dl.append(f"STALE: {cancelled} órdenes canceladas (>{ORDER_MAX_AGE_HOURS}h)")
        open_orders = get_open_orders(client)
    open_token_ids = get_order_token_ids(open_orders)
    dl.append(f"Órdenes activas: {len(open_token_ids)}")

    # v10.4 Fix Bug #3: obtener token_ids de posiciones YA LLENADAS
    # El check de open_token_ids solo mira órdenes pendientes.
    # Si una orden ya se llenó, su token_id sale de open_orders pero
    # la posición sigue abierta. Sin este check, el bot compra duplicados.
    # Bug real: Madrid se compró en ciclo 7, y en ciclo 8 se volvió a comprar.
    existing_position_tokens = set()
    funder = os.getenv("FUNDER", "")
    if funder:
        try:
            params = urllib.parse.urlencode({
                "user": funder.lower(),
                "sizeThreshold": "0",
                "limit": "50",
                "sortBy": "CURRENT",
                "sortDirection": "DESC",
            })
            url = f"{DATA_API_URL}/positions?{params}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-bot/0.10")
            resp = urllib.request.urlopen(req, timeout=15)
            positions = json.loads(resp.read())
            for p in positions:
                cv = float(p.get("currentValue", 0))
                cp = float(p.get("curPrice", 0))
                asset = p.get("asset", "")
                # Solo contar posiciones vivas (no micro ni resueltas)
                if cv >= 0.10 and cp < 0.98 and asset:
                    existing_position_tokens.add(asset)
            dl.append(f"Posiciones activas: {len(existing_position_tokens)} token_ids")
        except Exception as e:
            dl.append(f"⚠ Error consultando posiciones para duplicados: {e}")
            log.warning(f"Error consultando posiciones: {e}")

    # ---- PASO 0.5: GESTIÓN ACTIVA (v10.1) ----
    # Antes de buscar nuevas oportunidades, gestionar posiciones existentes
    # Esto libera capital y corta pérdidas (como hacen Entire-Hood y Thrifty)
    mgmt = {"n_sold": 0, "capital_freed": 0, "kept": 0, "resolved": 0, "sells": [], "sold_token_ids": set()}
    try:
        mgmt = manage_positions(client, dl)
        bot_state["last_sells_placed"] = mgmt["n_sold"]  # v10.4: para /estado
        if mgmt["n_sold"] > 0:
            dl.append(f"GESTIÓN: {mgmt['n_sold']} posiciones cerradas, ~${mgmt['capital_freed']:.2f} liberados")
    except Exception as e:
        dl.append(f"GESTIÓN: error: {e}")
        log.warning(f"Error en gestión de posiciones: {e}")

    # ---- PASO 0.6: AUDITORÍA (v10.1 final) ----
    # Verificar si ventas anteriores se llenaron
    try:
        audit_check_sell_fills(client, dl)
    except Exception as e:
        log.warning(f"Error audit fills: {e}")

    # Comparar previsiones pasadas con temperatura real
    try:
        audit_check_forecasts(dl)
    except Exception as e:
        log.warning(f"Error audit forecasts: {e}")

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
    # v10.3: min_days es ahora PER-CITY (Bug #5 fix — zona horaria asiática)
    min_days_global = get_min_days_ahead()  # Solo para logging
    dl.append(f"MIN_DAYS_AHEAD base: {min_days_global} (hora UTC: {datetime.now(timezone.utc).hour:02d})")
    dl.append(f"  ↳ Ajuste por zona horaria activo: ciudades asiáticas pueden requerir min_days=1 incluso a las 08:00 UTC")

    candidates = []
    parse_fail = 0
    date_fail = 0
    timezone_skip = 0  # v10.3: contador de filtrados por zona horaria
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

        # v10.3: min_days PER-CITY según zona horaria (Bug #5 fix)
        city = parsed["city"]
        min_days = get_min_days_for_city(city)

        if days_ahead < min_days:
            # Distinguir si fue por zona horaria o por filtro global
            if min_days > min_days_global:
                timezone_skip += 1
            else:
                date_fail += 1
            continue

        if days_ahead > MAX_DAYS_AHEAD:
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

    dl.append(f"FILTROS: {len(candidates)} pasan | {parse_fail} no parseables | {date_fail} fuera de fecha | {timezone_skip} bloqueados por zona horaria | {price_fail} fuera de precio | {liq_fail} sin liquidez")

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
    # v10.4 Fix Bug #9: token_ids vendidos en manage_positions → no re-comprar
    sold_this_cycle = mgmt.get("sold_token_ids", set())

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

        # v10.4 Fix Bug #9: no re-comprar lo que vendimos este ciclo
        if token_id in sold_this_cycle:
            skipped_dup += 1
            edge_analysis.append(f"  ⏭ {city} {side} | edge={edge_pct:.1f}% → VENDIDO ESTE CICLO (no re-entrada)")
            continue

        # v10.4 Fix Bug #3: no comprar si ya tenemos posición abierta
        if token_id in existing_position_tokens:
            skipped_dup += 1
            edge_analysis.append(f"  ⏭ {city} {side} | edge={edge_pct:.1f}% → YA HAY POSICIÓN ABIERTA")
            continue

        position = calculate_position(effective_bankroll, our_prob, mkt_price)
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

    # ---- PASO 5: Presupuesto (v10: acumulativo) ----
    # Consultar cuánto hay REALMENTE invertido en posiciones
    current_exposure = get_current_exposure()
    max_total_exposure = effective_bankroll * MAX_EXPOSURE_PCT
    budget_left = max(0, max_total_exposure - current_exposure)

    dl.append(f"\nEXPOSICIÓN: ${current_exposure:.2f} invertido | Máx: ${max_total_exposure:.2f} | Disponible: ${budget_left:.2f}")

    if budget_left < MIN_BET:
        dl.append(f"⛔ Presupuesto agotado (${budget_left:.2f} < ${MIN_BET} mín)")
        selected = []
    else:
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
                    "fraction_pct": round(reduced / effective_bankroll * 100, 2),
                    "amount": reduced, "shares": round(sh, 2),
                    "profit_if_win": pr, "loss_if_lose": reduced,
                    "expected_value": ev, "aggressive_price": agg_p,
                    "market_price": t["mkt_price"] / 100,
                }
                budget_left = 0
                selected.append(t)

    dl.append(f"SELECCIONADAS: {len(selected)} de {len(trades)}")

    # ---- PASO 6: Ejecución ----
    buy_summaries = []  # v10.2: para resumen de Telegram

    if not selected:
        dl.append(f"\nSin operaciones este ciclo.")
        bot_state["last_orders_placed"] = 0
        bot_state["last_trades"] = []
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

            if not DRY_RUN and result["ok"]:
                buy_summaries.append({
                    "city": trade["city"],
                    "side": trade["side"],
                    "amount": trade["position"]["amount"],
                    "edge": trade["edge_pct"],
                    "traders": trade.get("trader_confirmed", []),
                })

                # v10.1: Registrar en performance tracker
                track_trade("BUY",
                    city=trade["city"],
                    side=trade["side"],
                    date=trade["date"],
                    days_ahead=trade["days_ahead"],
                    price=trade["position"].get("aggressive_price", 0),
                    shares=trade["position"]["shares"],
                    amount=trade["position"]["amount"],
                    edge_pct=trade["edge_pct"],
                    our_prob=trade["our_prob"],
                    mkt_price=trade["mkt_price"],
                    forecast_max=trade["forecast_max"],
                    condition=trade["condition"],
                    trader_confirmed=trade.get("trader_confirmed", []),
                )

        ok = sum(1 for r in results if r["ok"])
        bot_state["last_orders_placed"] = ok
        bot_state["last_trades"] = selected

    # ---- v10.2: RESUMEN COMPLETO DEL CICLO ----
    if not DRY_RUN:
        summary = f"📊 <b>Ciclo #{bot_state['cycle_count']+1}</b>\n"
        summary += f"{'─' * 25}\n"

        # Gestión activa
        if mgmt["n_sold"] > 0:
            for s in mgmt["sells"]:
                icons = {"stop_loss": "🔻", "take_profit": "💰", "reeval": "🔄"}
                icon = icons.get(s["type"], "📤")
                summary += f"{icon} Vendido: {s['side']} {s['city']} ({s['pnl_pct']:+.0f}%)\n"
        if mgmt["resolved"] > 0:
            summary += f"🏁 {mgmt['resolved']} resueltas (esperando pago)\n"
        if mgmt["kept"] > 0:
            summary += f"✓ {mgmt['kept']} mantenidas\n"

        # Compras
        if buy_summaries:
            for b in buy_summaries:
                trader_tag = " 🤝" if b["traders"] else ""
                summary += f"🛒 Compra: {b['side']} {b['city']} ${b['amount']:.2f} edge={b['edge']:.0f}%{trader_tag}\n"
        elif not mgmt["n_sold"]:
            summary += f"💤 Sin operaciones\n"

        # Estado
        summary += f"{'─' * 25}\n"
        summary += f"Evaluados: {len(candidates)} | Edge: {len(trades)}\n"
        summary += f"Exposición actual: ${current_exposure:.2f} | Presupuesto libre: ${budget_left:.2f}\n"

        send_telegram(summary, with_menu=True)

    dl.append(f"\n{'='*50}")

    # Guardar log de decisiones
    _save_decision_log(dl)

    # --- v10.4.1: Guardar resumen de ciclo para historial ---
    try:
        cycle_data = {
            "version": "v10.4.5",
            "cycle_number": bot_state["cycle_count"] + 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "DRY_RUN" if DRY_RUN else "REAL",
            "management": {
                "n_kept": mgmt.get("n_kept", 0),
                "n_sold": mgmt.get("n_sold", 0),
                "n_resolved": mgmt.get("n_resolved", 0),
                "n_loss_total": mgmt.get("n_loss_total", 0),
            },
            "scan": {
                "markets_evaluated": len(candidates) if 'candidates' in locals() else 0,
                "with_edge": len(trades) if 'trades' in locals() else 0,
                "selected": len(selected) if 'selected' in locals() else 0,
            },
            "buys": [
                {
                    "city": b.get("city", "?"),
                    "side": b.get("side", "?"),
                    "amount": round(b.get("amount", 0), 2),
                    "edge": round(b.get("edge", 0), 1),
                    "traders": bool(b.get("traders")),
                }
                for b in (buy_summaries if 'buy_summaries' in locals() else [])
            ],
            "exposure_after": round(current_exposure, 2) if 'current_exposure' in locals() else None,
            "budget_left": round(budget_left, 2) if 'budget_left' in locals() else None,
        }
        # Último ciclo (se sobreescribe)
        with open(CYCLE_SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(cycle_data, f, indent=2, ensure_ascii=False)
        # Historial acumulativo (append-only, una línea JSON por ciclo)
        with open(CYCLES_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(cycle_data, ensure_ascii=False) + "\n")
        log.info("cycle_summary guardado OK")
    except Exception as e:
        log.warning(f"Error guardando cycle_summary: {e}")

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
    log.info(f"POLYMARKET BOT v10.4.5 | Schedule: {sorted(SCHEDULE_HOURS_UTC)} UTC")
    log.info(f"Modo: {'DRY RUN' if DRY_RUN else 'REAL'}")
    log.info("=" * 65)

    # v10.4.2: ciclos acumulativos — no se reinician con cada deploy
    bot_state["cycle_count"] = _load_cycle_count()
    log.info(f"Ciclos históricos cargados: {bot_state['cycle_count']}")

    clob_client = setup_client()
    if clob_client is None:
        send_telegram("❌ <b>Error autenticación</b>")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        threading.Thread(target=telegram_polling_loop, daemon=True, name="TelegramPoller").start()
        log.info("Telegram polling: OK")

    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    send_telegram(
        f"🤖 <b>Bot v10.4.5 arrancado</b>\n"
        f"Modo: {modo} | ${BANKROLL:.2f}\n"
        f"Min edge: {MIN_EDGE}% | Schedule: {schedule} UTC\n"
        f"🔧 Gestión activa: SL {STOP_LOSS_PCT}% / TP +{TAKE_PROFIT_PCT}%\n"
        f"🌏 Zona horaria per-city activa\n"
        f"🔍 Traders: auto-análisis diario, descubrimiento lunes",
        with_menu=True,
    )

    # v9: Ejecutar análisis de traders antes del primer ciclo
    run_trader_tasks()

    # v10.4 Fix Bug #11: comprobar si el último ciclo fue reciente
    # Bug real: al hacer deploy, el bot ejecutaba un ciclo inmediato
    # aunque el anterior fue hace 5 minutos. Causó doble Chicago.
    # Si el último ciclo fue hace menos de 3 horas, saltamos al scheduler.
    skip_first_cycle = False
    min_cycle_gap_hours = 3.0  # mínimo entre ciclos para no duplicar
    try:
        if os.path.exists(PERFORMANCE_FILE):
            with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            if history:
                # Buscar el timestamp más reciente
                last_ts = None
                for entry in reversed(history):
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        try:
                            last_ts = datetime.fromisoformat(ts_str)
                            break
                        except (ValueError, TypeError):
                            continue
                if last_ts:
                    age_hours = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600
                    if age_hours < min_cycle_gap_hours:
                        skip_first_cycle = True
                        log.info(f"Último ciclo hace {age_hours:.1f}h (< {min_cycle_gap_hours}h) — saltando ciclo inicial")
                        send_telegram(
                            f"⏭ <b>Bot arrancado</b>\n"
                            f"Último ciclo hace {age_hours:.1f}h — esperando al siguiente programado."
                        )
    except Exception as e:
        log.warning(f"Error comprobando último ciclo: {e}")

    if not skip_first_cycle:
        log.info("Primer ciclo...")
        # v10: Avisar que el primer ciclo está corriendo
        send_telegram("🔄 <b>Ejecutando primer ciclo...</b>\nEsto puede tardar ~30s")
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
