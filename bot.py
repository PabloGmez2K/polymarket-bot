import urllib.request
import urllib.parse
import json
import base64
import re
import math
import os
import sys
import time
import logging
import threading
import subprocess
import shutil
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY, SELL
from waitress import serve

load_dotenv()

# =============================================================
# bot.py v10.5.5 — dashboard web de monitorización + scorecard de agentes
# Sesión 23: observabilidad visual separada de Telegram
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
# v10.4.6:
#   - backfill automático de postmortem.json desde performance.json
#   - alerts_state.json para alertas one-shot persistentes
#   - alertas: 30 trades limpios, signals stale/vacío, pending_exit atascadas
# v10.4.7:
#   - bloqueo operativo de London hasta resolver WU vs Open-Meteo
# v10.4.8:
#   - /traders alinea cartera por ciudad+lado+fecha exacta del mercado
#   - /postmortem mejora etiquetas para registros legacy sin question
#   - /detalle muestra el ultimo ciclo completo del log, sin corte fijo
# v10.5.4:
#   - Contador dual de ciclos: histórico total + serie lógica actual
#   - cycle_summary/cycles_history guardan logic_series y logic_cycle_number
#   - /estado y /info muestran ambos contadores para comparar estrategias
# v10.5.5:
#   - Dashboard web HTML en navegador (separado de Telegram)
#   - Checklist de promoción de bankroll con semáforos y progreso
#   - Scoreboard de agentes con rivalidad constructiva y eventos validados
# =============================================================


# =============================================================
# CONFIGURACIÓN
# =============================================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))

MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_EDGE_EXACT = float(os.getenv("MIN_EDGE_EXACT", "15.0"))  # v10.5: exact bets necesitan más edge (20% win rate histórico)
MIN_BET = float(os.getenv("MIN_BET", "1.00"))           # v10.4: default alineado con Railway
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))   # v9: subido de 0.05 a 0.10 (10%)
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))  # -1 = automático
BOT_VERSION = "v10.5.9"
LOGIC_SERIES = "10.5"
REVIEW_READY_CLEAN_TRADES = 30
PENDING_EXIT_ALERT_HOURS = 12.0

# v10.5: Smart alerts — drawdown, scaling, win rate
DRAWDOWN_WINDOW = int(os.getenv("DRAWDOWN_WINDOW", "5"))
DRAWDOWN_THRESHOLD = float(os.getenv("DRAWDOWN_THRESHOLD", "-3.0"))
SCALING_TIERS = [25, 35, 50, 75, 100]
SCALING_WINDOW = int(os.getenv("SCALING_WINDOW", "20"))
WIN_RATE_WINDOW = int(os.getenv("WIN_RATE_WINDOW", "15"))
WIN_RATE_LOW = float(os.getenv("WIN_RATE_LOW", "30.0"))
WIN_RATE_HIGH = float(os.getenv("WIN_RATE_HIGH", "50.0"))
# v10.5.2: City accuracy tracker
CITY_MIN_TRADES_FOR_BLOCK = int(os.getenv("CITY_MIN_TRADES_FOR_BLOCK", "3"))
CITY_BLOCK_WIN_RATE = float(os.getenv("CITY_BLOCK_WIN_RATE", "25.0"))

# v10.5.5: Dashboard web
DASHBOARD_ENABLED = os.getenv("DASHBOARD_ENABLED", "true").lower() == "true"
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8080")))
DASHBOARD_TITLE = os.getenv("DASHBOARD_TITLE", "Polymarket Bot Control Center")
DASHBOARD_REFRESH_SEC = int(os.getenv("DASHBOARD_REFRESH_SEC", "60"))
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
BANKROLL_LEVELS = [
    float(v.strip())
    for v in os.getenv("BANKROLL_LEVELS", "25,35,50,75,100").split(",")
    if v.strip()
]
PROMOTION_MIN_SERIES_CYCLES = int(os.getenv("PROMOTION_MIN_SERIES_CYCLES", "10"))
PROMOTION_MIN_SERIES_WIN_RATE = float(os.getenv("PROMOTION_MIN_SERIES_WIN_RATE", "40.0"))
PROMOTION_MIN_SERIES_PNL = float(os.getenv("PROMOTION_MIN_SERIES_PNL", "0.0"))
PROMOTION_CITY_COVERAGE_TARGET = int(os.getenv("PROMOTION_CITY_COVERAGE_TARGET", "3"))

BLOCKED_CITIES = {
    city.strip().lower()
    for city in os.getenv("BLOCKED_CITIES", "London").split(",")
    if city.strip()
}


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


def is_city_blocked(city):
    """Devuelve True si la ciudad está bloqueada operativamente."""
    return city.strip().lower() in BLOCKED_CITIES if city else False


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
INTRA_SL_INTERVAL = int(os.getenv("INTRA_SL_INTERVAL", "90"))  # minutos entre checks, 0=desactivar

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


def _seed_data_file(filename):
    """
    Si DATA_DIR está activo y el archivo aún no existe en el volume,
    lo inicializa copiando la versión local del repo una sola vez.
    """
    target = _data_path(filename)
    if DATA_DIR and not os.path.exists(target) and os.path.exists(filename):
        try:
            shutil.copy2(filename, target)
        except Exception:
            pass
    return target

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
    "cycle_count_series": 0,
    "last_trades": [],
    "last_decision_summary": "",
    "last_trader_scan": None,
    "last_trader_analysis": None,
    "last_edge_analysis": [],       # v9: para /logfull
    "last_trader_signals": {},      # v9: para cruce en /logfull
}

force_event = threading.Event()
sell_lock = threading.Lock()  # v10.5.1: protege ventas concurrentes (ciclo principal vs intra-SL)
clob_client = None

# Cache de token_id → info del mercado.
# Se llena cada vez que el bot escanea mercados o coloca órdenes.
# Así cuando consultas /ordenes, sabe a qué mercado pertenece cada token.
known_tokens = {}

PERFORMANCE_FILE = _data_path("performance.json")
CYCLE_SUMMARY_FILE = _data_path("cycle_summary.json")
CYCLES_HISTORY_FILE = _data_path("cycles_history.jsonl")
POSTMORTEM_FILE = _data_path("postmortem.json")
ALERTS_FILE = _data_path("alerts_state.json")
AGENT_EVENTS_FILE = _seed_data_file("agent_events.jsonl")
SIGNALS_FILE = _seed_data_file("signals.json")
TRADERS_DB_FILE = _seed_data_file("traders_db.json")


def load_performance_history():
    """Carga el historial de performance; devuelve [] si no existe o está dañado."""
    if not os.path.exists(PERFORMANCE_FILE):
        return []
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_alerts_state():
    """Carga el estado persistente de alertas y resetea si cambia la serie lógica."""
    default = {
        "logic_series": LOGIC_SERIES,
        "milestones": {},
        "signals_health": {"last_issue": None},
        "pending_exit_notified": {},
        # v10.5: smart alerts state
        "drawdown_alerted": False,
        "scaling_alerted_tier": None,
        "scaling_negative_alerted": False,
        "win_rate_low_alerted": False,
        "win_rate_high_alerted": False,
        # v10.5.2: city accuracy tracker
        "city_accuracy_flagged": {},
    }
    if not os.path.exists(ALERTS_FILE):
        return default
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        if data.get("logic_series") != LOGIC_SERIES:
            return default
        state = dict(default)
        state.update(data)
        state["milestones"] = data.get("milestones", {}) if isinstance(data.get("milestones"), dict) else {}
        state["signals_health"] = data.get("signals_health", {}) if isinstance(data.get("signals_health"), dict) else {"last_issue": None}
        state["pending_exit_notified"] = data.get("pending_exit_notified", {}) if isinstance(data.get("pending_exit_notified"), dict) else {}
        # v10.5: smart alerts — reconstruct with defaults
        state.setdefault("drawdown_alerted", False)
        state.setdefault("scaling_alerted_tier", None)
        state.setdefault("scaling_negative_alerted", False)
        state.setdefault("win_rate_low_alerted", False)
        state.setdefault("win_rate_high_alerted", False)
        state.setdefault("city_accuracy_flagged", {})
        return state
    except Exception:
        return default


def save_alerts_state(state):
    """Guarda el estado de alertas evitando crecimiento innecesario."""
    try:
        pending = state.get("pending_exit_notified", {})
        if isinstance(pending, dict) and len(pending) > 200:
            keep_keys = sorted(
                pending,
                key=lambda k: pending[k].get("sent_at", ""),
                reverse=True,
            )[:200]
            state["pending_exit_notified"] = {k: pending[k] for k in keep_keys}
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando alerts_state: {e}")


def _extract_logic_series(value):
    """Normaliza 'v10.5.4' o '10.5' a '10.5'."""
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d+\.\d+)", value)
    return match.group(1) if match else None


def _load_cycle_counts():
    """
    Lee cycles_history.jsonl y devuelve:
      - total de ciclos históricos
      - ciclos de la serie lógica actual (LOGIC_SERIES)

    El contador total nunca se reinicia con deploys; el de serie permite
    medir cambios de estrategia sin perder continuidad operativa.
    """
    if not os.path.exists(CYCLES_HISTORY_FILE):
        return 0, 0
    try:
        with open(CYCLES_HISTORY_FILE, "r", encoding="utf-8") as f:
            total = 0
            series = 0
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                total += 1
                entry_series = None
                try:
                    data = json.loads(line)
                    if isinstance(data, dict):
                        entry_series = (
                            _extract_logic_series(data.get("logic_series"))
                            or _extract_logic_series(data.get("version"))
                        )
                except Exception:
                    logic_match = re.search(r'"logic_series"\s*:\s*"([^"]+)"', line)
                    version_match = re.search(r'"version"\s*:\s*"([^"]+)"', line)
                    if logic_match:
                        entry_series = _extract_logic_series(logic_match.group(1))
                    elif version_match:
                        entry_series = _extract_logic_series(version_match.group(1))
                if entry_series == LOGIC_SERIES:
                    series += 1
            return total, series
    except Exception:
        return 0, 0


def _load_cycle_count():
    """Compatibilidad: devuelve solo el total histórico."""
    return _load_cycle_counts()[0]


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


def parse_market_date_iso(text):
    """Normaliza varias representaciones de fecha de mercado a YYYY-MM-DD."""
    if not text:
        return ""

    text = str(text).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    month_map = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    match = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})\b",
            text,
            re.IGNORECASE,
        )
    if not match:
        return ""

    month = month_map.get(match.group(1).lower())
    day = int(match.group(2))
    year = datetime.now(timezone.utc).year
    return f"{year:04d}-{month:02d}-{day:02d}"


def format_market_date_short(text):
    """Convierte YYYY-MM-DD o texto parseable a Mar29."""
    iso_date = parse_market_date_iso(text)
    if not iso_date:
        return ""

    year_str, month_str, day_str = iso_date.split("-")
    month_num = int(month_str)
    day = int(day_str)
    month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month_num - 1]
    return f"{month_abbr}{day}"


def format_postmortem_label(record):
    """Etiqueta legible para postmortem, incluso en historico legacy sin question."""
    side = str(record.get("side", "?")).upper()
    question = record.get("question", "")
    if question:
        label = _parse_position_label(question, side)
        if label and not label.startswith("?"):
            return label

    city = record.get("city", "?") or "?"
    date_short = format_market_date_short(record.get("date", ""))
    parts = [city]
    if date_short:
        parts.append(date_short)
    if side:
        parts.append(side)
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
        "bot_version": BOT_VERSION,
    }
    entry.update(kwargs)

    try:
        history = load_performance_history()

        history.append(entry)

        # Máximo 500 entradas (evitar que crezca infinito)
        if len(history) > 500:
            history = history[-500:]

        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando performance: {e}")

    try:
        update_postmortem(action, entry)
    except Exception as e:
        log.warning(f"Error actualizando postmortem: {e}")


def load_postmortem_data():
    """Carga postmortems acumulativos de mercados/posiciones."""
    if os.path.exists(POSTMORTEM_FILE):
        try:
            with open(POSTMORTEM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def save_postmortem_data(records):
    """Guarda postmortems. Conserva histórico reciente y evita crecimiento infinito."""
    if len(records) > 500:
        records = records[-500:]
    try:
        with open(POSTMORTEM_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando postmortem: {e}")


def _find_open_postmortem(records, entry):
    """
    Busca el postmortem abierto más probable para una entrada.
    Prioridad: token_id -> question -> city+side+date.
    """
    open_statuses = {"open", "pending_exit", "exit_failed"}
    token_id = entry.get("token_id", "")
    question = entry.get("question", "")
    city = entry.get("city", "")
    side = str(entry.get("side", "")).upper()
    market_date = entry.get("date", "")

    for record in reversed(records):
        if record.get("status") not in open_statuses:
            continue
        if token_id and record.get("token_id") == token_id:
            return record
        if question and record.get("question") == question and record.get("side") == side:
            return record
        if city and market_date and record.get("city") == city and record.get("side") == side and record.get("date") == market_date:
            return record
    return None


def update_postmortem(action, entry):
    """
    Mantiene postmortem.json sincronizado con el ciclo de vida de cada posición.

    Estados:
      - open: una o más compras abiertas
      - pending_exit: se colocó una venta, pendiente de fill
      - exit_failed: la salida falló, la posición sigue abierta
      - closed: posición cerrada por SELL, LOSS_TOTAL o RESOLVED_WIN
    """
    if action not in {"BUY", "SELL_PENDING", "SELL", "SELL_FAILED", "LOSS_TOTAL", "RESOLVED_WIN"}:
        return

    records = load_postmortem_data()
    record = _find_open_postmortem(records, entry)

    timestamp = (
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    side = str(entry.get("side", "")).upper()
    token_id = entry.get("token_id", "")
    question = entry.get("question", "")
    city = entry.get("city", "?")
    market_date = entry.get("date", "")
    condition = entry.get("condition", "")

    if action == "BUY":
        if record is None:
            record = {
                "id": f"{token_id or city}|{side}|{market_date}|{timestamp}",
                "status": "open",
                "token_id": token_id,
                "question": question,
                "city": city,
                "side": side,
                "date": market_date,
                "condition": condition,
                "opened_at": timestamp,
                "closed_at": None,
                "buy_count": 0,
                "total_amount": 0.0,
                "total_shares": 0.0,
                "avg_entry_price": None,
                "trader_confirmed": [],
                "bot_version_opened": entry.get("bot_version", ""),
                "buys": [],
            }
            records.append(record)

        amount = float(entry.get("amount", 0) or 0)
        shares = float(entry.get("shares", 0) or 0)
        price = float(entry.get("price", 0) or 0)
        record["status"] = "open"
        record["token_id"] = token_id or record.get("token_id", "")
        record["question"] = question or record.get("question", "")
        record["condition"] = condition or record.get("condition", "")
        record["date"] = market_date or record.get("date", "")
        record["latest_forecast_max"] = entry.get("forecast_max")
        record["latest_edge_pct"] = entry.get("edge_pct")
        record["latest_our_prob"] = entry.get("our_prob")
        record["latest_mkt_price"] = entry.get("mkt_price")
        record["last_buy_at"] = timestamp
        record["buy_count"] = int(record.get("buy_count", 0)) + 1
        record["total_amount"] = round(float(record.get("total_amount", 0)) + amount, 2)
        record["total_shares"] = round(float(record.get("total_shares", 0)) + shares, 2)
        if record["total_shares"] > 0:
            record["avg_entry_price"] = round(record["total_amount"] / record["total_shares"], 4)
        traders = set(record.get("trader_confirmed", []))
        traders.update(entry.get("trader_confirmed", []) or [])
        record["trader_confirmed"] = sorted(traders)
        record.setdefault("buys", []).append({
            "timestamp": timestamp,
            "amount": amount,
            "shares": shares,
            "price": price,
            "edge_pct": entry.get("edge_pct"),
            "forecast_max": entry.get("forecast_max"),
            "our_prob": entry.get("our_prob"),
            "mkt_price": entry.get("mkt_price"),
            "bot_version": entry.get("bot_version", ""),
        })

    elif action == "SELL_PENDING":
        if record is None:
            record = {
                "id": f"{token_id or city}|{side}|{market_date}|{timestamp}",
                "status": "pending_exit",
                "token_id": token_id,
                "question": question,
                "city": city,
                "side": side,
                "date": market_date,
                "condition": condition,
                "opened_at": timestamp,
                "closed_at": None,
                "buy_count": 0,
                "total_amount": 0.0,
                "total_shares": 0.0,
                "avg_entry_price": entry.get("avg_buy_price"),
                "trader_confirmed": [],
                "bot_version_opened": entry.get("bot_version", ""),
                "buys": [],
                "orphan_open": True,
            }
            records.append(record)

        record["status"] = "pending_exit"
        record["pending_exit"] = {
            "timestamp": timestamp,
            "reason": entry.get("reason"),
            "price": entry.get("price"),
            "shares": entry.get("shares"),
            "return_est": entry.get("return_est"),
            "pnl_pct": entry.get("pnl_pct"),
            "pnl_cash": entry.get("pnl_cash"),
            "order_id": entry.get("order_id"),
        }

    elif action == "SELL_FAILED":
        if record is None:
            record = {
                "id": f"{token_id or city}|{side}|{market_date}|{timestamp}",
                "status": "exit_failed",
                "token_id": token_id,
                "question": question,
                "city": city,
                "side": side,
                "date": market_date,
                "condition": condition,
                "opened_at": timestamp,
                "closed_at": None,
                "buy_count": 0,
                "total_amount": 0.0,
                "total_shares": 0.0,
                "avg_entry_price": entry.get("avg_buy_price"),
                "trader_confirmed": [],
                "bot_version_opened": entry.get("bot_version", ""),
                "buys": [],
                "orphan_open": True,
            }
            records.append(record)

        record["status"] = "exit_failed"
        record.pop("pending_exit", None)
        record["last_exit_failed"] = {
            "timestamp": timestamp,
            "reason": entry.get("fail_reason", entry.get("reason")),
            "order_id": entry.get("order_id"),
        }

    else:
        if record is None:
            record = {
                "id": f"{token_id or city}|{side}|{market_date}|{timestamp}",
                "status": "closed",
                "token_id": token_id,
                "question": question,
                "city": city,
                "side": side,
                "date": market_date,
                "condition": condition,
                "opened_at": timestamp,
                "closed_at": None,
                "buy_count": 0,
                "total_amount": 0.0,
                "total_shares": 0.0,
                "avg_entry_price": entry.get("avg_buy_price"),
                "trader_confirmed": [],
                "bot_version_opened": entry.get("bot_version", ""),
                "buys": [],
                "orphan_open": True,
            }
            records.append(record)

        # Idempotencia para mercados ya cerrados por resolución
        if action == "RESOLVED_WIN" and record.get("close_action") == "RESOLVED_WIN":
            return

        payout_est = entry.get("payout_est", entry.get("return_est"))
        initial_value = float(entry.get("initial_value", record.get("total_amount", 0)) or 0)
        if action == "RESOLVED_WIN" and payout_est is None:
            payout_est = float(entry.get("shares", record.get("total_shares", 0)) or 0)

        pnl_cash = entry.get("pnl_cash")
        if pnl_cash is None and payout_est is not None:
            pnl_cash = round(float(payout_est) - initial_value, 2)
        elif pnl_cash is None:
            pnl_cash = entry.get("loss")

        pnl_pct = entry.get("pnl_pct")
        if pnl_pct is None and initial_value > 0 and payout_est is not None:
            pnl_pct = round((float(payout_est) / initial_value - 1.0) * 100, 1)

        record["status"] = "closed"
        record["closed_at"] = timestamp
        record["close_action"] = action
        record["close_reason"] = entry.get("reason", "market_resolved_yes" if action == "RESOLVED_WIN" else "")
        record["close_subtype"] = entry.get("reason")
        record["close_price"] = entry.get("price", entry.get("cur_price"))
        record["close_shares"] = entry.get("shares", record.get("total_shares"))
        record["return_est"] = payout_est if payout_est is not None else entry.get("current_value")
        record["pnl_cash"] = pnl_cash
        record["pnl_pct"] = pnl_pct
        record["order_id"] = entry.get("order_id", record.get("order_id"))
        record["bot_version_closed"] = entry.get("bot_version", "")
        record.pop("pending_exit", None)

    save_postmortem_data(records)


def backfill_postmortem_from_performance():
    """
    Reconstruye postmortem.json desde performance.json si aún no existe historial.
    Se usa al arrancar tras introducir postmortem en un bot que ya tenía trades previos.
    """
    existing = load_postmortem_data()
    if existing:
        return len(existing)

    history = load_performance_history()
    replayable = {"BUY", "SELL_PENDING", "SELL", "SELL_FAILED", "LOSS_TOTAL", "RESOLVED_WIN"}
    events = [dict(entry) for entry in history if entry.get("action") in replayable]
    if not events:
        return 0

    events.sort(
        key=lambda entry: (
            entry.get("fill_confirmed")
            or entry.get("failed_at")
            or entry.get("timestamp")
            or ""
        )
    )

    save_postmortem_data([])
    rebuilt = 0
    for entry in events:
        try:
            update_postmortem(entry.get("action", ""), entry)
            rebuilt += 1
        except Exception as e:
            log.warning(f"Error en backfill postmortem: {e}")

    total = len(load_postmortem_data())
    log.info(f"postmortem backfill OK: {total} registros reconstruidos desde {rebuilt} eventos")
    return total


def inspect_signals_file_health():
    """Devuelve el estado operativo de signals.json para alertas/observabilidad."""
    if not os.path.exists(SIGNALS_FILE):
        return {"status": "missing", "age_hours": None, "actionable": 0}

    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        generated = datetime.fromisoformat(data.get("generated", "2000-01-01T00:00:00+00:00"))
        age_hours = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
        actionable = len([s for s in data.get("signals", []) if not s.get("is_reference")])
        if age_hours > 26:
            return {"status": "stale", "age_hours": age_hours, "actionable": actionable}
        if actionable == 0:
            return {"status": "empty", "age_hours": age_hours, "actionable": 0}
        return {"status": "ok", "age_hours": age_hours, "actionable": actionable}
    except Exception as e:
        return {"status": "error", "age_hours": None, "actionable": 0, "detail": str(e)[:120]}


def get_clean_closed_trade_stats():
    """
    Cuenta trades limpios cerrados para saber cuándo hay muestra suficiente
    para revisar lógica de salida sin depender de estimaciones manuales.
    """
    records = load_postmortem_data()
    if records:
        closed = [
            r for r in records
            if r.get("status") == "closed"
            and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
            and r.get("pnl_cash") is not None
        ]
        return {
            "count": len(closed),
            "sell": sum(1 for r in closed if r.get("close_action") == "SELL"),
            "loss_total": sum(1 for r in closed if r.get("close_action") == "LOSS_TOTAL"),
            "resolved_win": sum(1 for r in closed if r.get("close_action") == "RESOLVED_WIN"),
        }

    history = load_performance_history()
    sells = [h for h in history if h.get("action") == "SELL" and h.get("pnl_cash") is not None]
    loss_total = [h for h in history if h.get("action") == "LOSS_TOTAL" and h.get("loss") is not None]
    resolved_win = [h for h in history if h.get("action") == "RESOLVED_WIN"]
    return {
        "count": len(sells) + len(loss_total) + len(resolved_win),
        "sell": len(sells),
        "loss_total": len(loss_total),
        "resolved_win": len(resolved_win),
    }


def get_logic_series_clean_closed_trade_stats(logic_series=None):
    """Cuenta trades limpios cerrados asociados solo a la serie lógica actual."""
    series_records = get_logic_series_records(logic_series)
    closed = [
        r for r in series_records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("pnl_cash") is not None
    ]
    return {
        "count": len(closed),
        "sell": sum(1 for r in closed if r.get("close_action") == "SELL"),
        "loss_total": sum(1 for r in closed if r.get("close_action") == "LOSS_TOTAL"),
        "resolved_win": sum(1 for r in closed if r.get("close_action") == "RESOLVED_WIN"),
    }


def _get_recent_closed_trades(n=None):
    """Devuelve los últimos N trades cerrados de postmortem.json, más reciente primero."""
    records = load_postmortem_data()
    closed = [
        r for r in records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("pnl_cash") is not None
    ]
    closed.sort(key=lambda r: r.get("closed_at", ""), reverse=True)
    if n is not None:
        closed = closed[:n]
    return closed


def get_city_accuracy():
    """Calcula win rate y PnL por ciudad desde postmortem.json cerrados."""
    records = load_postmortem_data()
    closed = [r for r in records if r.get("status") == "closed"
              and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
              and r.get("city")]

    cities = {}
    for r in closed:
        city = r["city"]
        if city not in cities:
            cities[city] = {"trades": 0, "wins": 0, "pnl": 0.0}
        cities[city]["trades"] += 1
        if (r.get("pnl_cash") or 0) > 0:
            cities[city]["wins"] += 1
        cities[city]["pnl"] += r.get("pnl_cash", 0) or 0

    for city, data in cities.items():
        data["win_rate"] = round(data["wins"] / data["trades"] * 100, 1) if data["trades"] > 0 else 0.0

    return cities


def run_observability_alerts():
    """
    Alertas one-shot de observabilidad y review readiness.
    No toca lógica de trading; solo avisa por Telegram cuando aparece información útil.
    """
    state = load_alerts_state()
    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()

    stats = get_clean_closed_trade_stats()
    milestone_key = f"clean_trades_{REVIEW_READY_CLEAN_TRADES}"
    if stats["count"] >= REVIEW_READY_CLEAN_TRADES and milestone_key not in state["milestones"]:
        send_telegram(
            f"🧠 <b>Review Trigger</b>\n"
            f"Ya hay <b>{stats['count']} trades limpios cerrados</b>.\n"
            f"SELL: {stats['sell']} | LOSS_TOTAL: {stats['loss_total']} | RESOLVED_WIN: {stats['resolved_win']}\n\n"
            f"Recomendado abrir sesión de análisis/coding para revisar la lógica de salida de la serie <b>v{LOGIC_SERIES}.x</b>."
        )
        state["milestones"][milestone_key] = {
            "sent_at": now_iso,
            "count": stats["count"],
            "logic_series": LOGIC_SERIES,
        }
        changed = True

    signals = inspect_signals_file_health()
    issue = None if signals["status"] == "ok" else signals["status"]
    prev_issue = state.get("signals_health", {}).get("last_issue")
    if issue != prev_issue:
        if issue == "missing":
            send_telegram(
                "⚠️ <b>Alerta traders</b>\n"
                "signals.json no existe en DATA_DIR.\n"
                "El bot seguirá funcionando, pero sin confirmación de traders."
            )
        elif issue == "stale":
            send_telegram(
                f"⚠️ <b>Alerta traders</b>\n"
                f"signals.json está expirado ({signals.get('age_hours', 0):.1f}h).\n"
                f"Señales accionables actuales: {signals.get('actionable', 0)}."
            )
        elif issue == "empty":
            send_telegram(
                f"⚠️ <b>Alerta traders</b>\n"
                f"signals.json está al día ({signals.get('age_hours', 0):.1f}h), pero sin señales accionables."
            )
        elif issue == "error":
            send_telegram(
                "⚠️ <b>Alerta traders</b>\n"
                f"No se pudo leer signals.json.\n<code>{signals.get('detail', 'error')}</code>"
            )
        elif prev_issue:
            send_telegram(
                f"✅ <b>Alerta resuelta</b>\n"
                f"signals.json vuelve a estar operativo.\n"
                f"Edad: {signals.get('age_hours', 0):.1f}h | Señales: {signals.get('actionable', 0)}"
            )

        state["signals_health"] = {
            "last_issue": issue,
            "last_checked_at": now_iso,
            "last_status": signals["status"],
            "last_actionable": signals.get("actionable", 0),
        }
        changed = True

    notified = state.get("pending_exit_notified", {})
    pending = load_audit_data().get("pending_sells", [])
    active_pending_ids = set()
    stuck_new = []
    now = datetime.now(timezone.utc)

    for sell in pending:
        order_id = sell.get("order_id") or f"{sell.get('city', '?')}|{sell.get('side', '?')}|{sell.get('timestamp', '?')}"
        active_pending_ids.add(order_id)
        try:
            placed_at = datetime.fromisoformat(sell.get("timestamp", ""))
            age_hours = (now - placed_at).total_seconds() / 3600
        except Exception:
            continue
        if age_hours >= PENDING_EXIT_ALERT_HOURS and order_id not in notified:
            stuck_new.append((order_id, sell, age_hours))

    if stuck_new:
        lines = [
            "⏳ <b>Ventas pendientes atascadas</b>",
            f"Hay {len(stuck_new)} orden(es) > {PENDING_EXIT_ALERT_HOURS:.0f}h sin fill.",
            "",
        ]
        for order_id, sell, age_hours in stuck_new[:5]:
            lines.append(
                f"• {sell.get('city', '?')} {sell.get('side', '?')} | "
                f"{age_hours:.1f}h | ${float(sell.get('price', 0) or 0):.2f}"
            )
            notified[order_id] = {
                "sent_at": now_iso,
                "age_hours": round(age_hours, 1),
                "city": sell.get("city", "?"),
                "side": sell.get("side", "?"),
            }
        if len(stuck_new) > 5:
            lines.append(f"• ... y {len(stuck_new) - 5} más")
        send_telegram("\n".join(lines))
        changed = True

    for order_id in list(notified):
        if order_id not in active_pending_ids:
            notified.pop(order_id, None)
            changed = True
    state["pending_exit_notified"] = notified

    # --- v10.5: Drawdown alert ---
    recent_dd = _get_recent_closed_trades(DRAWDOWN_WINDOW)
    if len(recent_dd) >= DRAWDOWN_WINDOW:
        window_pnl = sum(r.get("pnl_cash", 0) for r in recent_dd)
        if window_pnl <= DRAWDOWN_THRESHOLD and not state.get("drawdown_alerted"):
            send_telegram(
                f"📉 <b>Drawdown Alert</b>\n"
                f"Los últimos {DRAWDOWN_WINDOW} trades cerrados tienen PnL neto de <b>${window_pnl:+.2f}</b>.\n"
                f"Umbral: ${DRAWDOWN_THRESHOLD:.2f}\n\n"
                f"Considerar sesión de revisión en Claude Code."
            )
            state["drawdown_alerted"] = True
            changed = True
        elif window_pnl > DRAWDOWN_THRESHOLD and state.get("drawdown_alerted"):
            state["drawdown_alerted"] = False
            changed = True

    # --- v10.5: Scaling readiness ---
    recent_sc = _get_recent_closed_trades(SCALING_WINDOW)
    if len(recent_sc) >= SCALING_WINDOW:
        scaling_pnl = sum(r.get("pnl_cash", 0) for r in recent_sc)
        next_tier = None
        for tier in SCALING_TIERS:
            if tier > BANKROLL:
                next_tier = tier
                break

        if scaling_pnl > 0 and next_tier and state.get("scaling_alerted_tier") != next_tier:
            if BANKROLL + scaling_pnl >= next_tier:
                send_telegram(
                    f"📈 <b>Scaling Readiness</b>\n"
                    f"PnL acumulado de últimos {SCALING_WINDOW} trades: <b>${scaling_pnl:+.2f}</b>.\n"
                    f"Considerar subir bankroll de ${BANKROLL:.0f} a ${next_tier:.0f}."
                )
                state["scaling_alerted_tier"] = next_tier
                changed = True

        if scaling_pnl < 0 and not state.get("scaling_negative_alerted"):
            send_telegram(
                f"⚠️ <b>Scaling Warning</b>\n"
                f"PnL acumulado de últimos {SCALING_WINDOW} trades: <b>${scaling_pnl:+.2f}</b>.\n"
                f"No subir de escalón hasta recuperar."
            )
            state["scaling_negative_alerted"] = True
            changed = True
        elif scaling_pnl >= 0 and state.get("scaling_negative_alerted"):
            state["scaling_negative_alerted"] = False
            changed = True

    # --- v10.5: Win rate rolling check ---
    recent_wr = _get_recent_closed_trades(WIN_RATE_WINDOW)
    if len(recent_wr) >= WIN_RATE_WINDOW:
        wins = sum(1 for r in recent_wr if (r.get("pnl_cash") or 0) > 0)
        win_rate = (wins / len(recent_wr)) * 100

        if win_rate < WIN_RATE_LOW and not state.get("win_rate_low_alerted"):
            send_telegram(
                f"🔴 <b>Strategy Review</b>\n"
                f"Win rate últimos {WIN_RATE_WINDOW} trades: <b>{win_rate:.0f}%</b> (umbral: {WIN_RATE_LOW:.0f}%).\n"
                f"Revisar lógica de entrada y sigma."
            )
            state["win_rate_low_alerted"] = True
            state["win_rate_high_alerted"] = False
            changed = True
        elif win_rate >= WIN_RATE_LOW and state.get("win_rate_low_alerted"):
            state["win_rate_low_alerted"] = False
            changed = True

        if win_rate >= WIN_RATE_HIGH and not state.get("win_rate_high_alerted"):
            send_telegram(
                f"🟢 <b>Strategy Signal</b>\n"
                f"Win rate últimos {WIN_RATE_WINDOW} trades: <b>{win_rate:.0f}%</b>.\n"
                f"Rendimiento positivo sostenido."
            )
            state["win_rate_high_alerted"] = True
            state["win_rate_low_alerted"] = False
            changed = True
        elif win_rate < WIN_RATE_HIGH and state.get("win_rate_high_alerted"):
            state["win_rate_high_alerted"] = False
            changed = True

    # ---- v10.5.2: City Accuracy Alert ----
    city_stats = get_city_accuracy()
    flagged_key = "city_accuracy_flagged"
    if flagged_key not in state:
        state[flagged_key] = {}

    for city, data in city_stats.items():
        if data["trades"] >= CITY_MIN_TRADES_FOR_BLOCK and data["win_rate"] <= CITY_BLOCK_WIN_RATE:
            if not is_city_blocked(city) and city not in state[flagged_key]:
                now_iso = datetime.now(timezone.utc).isoformat()
                send_telegram(
                    f"⚠️ <b>Ciudad con baja accuracy</b>\n"
                    f"{city}: {data['win_rate']}% win rate ({data['wins']}/{data['trades']} trades)\n"
                    f"PnL: ${data['pnl']:+.2f}\n"
                    f"<i>Considerar añadir a BLOCKED_CITIES</i>"
                )
                state[flagged_key][city] = {"sent_at": now_iso, **data}
                changed = True

    if changed:
        save_alerts_state(state)


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
# DASHBOARD WEB (v10.5.5)
# =============================================================

def load_cycle_history(limit=None):
    """Carga el historial de ciclos desde cycles_history.jsonl."""
    records = []
    if not os.path.exists(CYCLES_HISTORY_FILE):
        return records
    try:
        with open(CYCLES_HISTORY_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict):
                    records.append(item)
    except Exception as e:
        log.warning(f"Error cargando cycles_history: {e}")
        return []

    if limit is not None:
        records = records[-limit:]
    return records


def get_logic_series_records(logic_series=None):
    """Devuelve postmortems asociados a una serie lógica concreta."""
    target = logic_series or LOGIC_SERIES
    records = load_postmortem_data()
    matched = []
    for rec in records:
        opened = _extract_logic_series(rec.get("bot_version_opened"))
        closed = _extract_logic_series(rec.get("bot_version_closed"))
        if opened == target or (opened is None and closed == target):
            matched.append(rec)
    return matched


def get_logic_series_stats(logic_series=None):
    """Resumen de performance para la serie lógica actual."""
    series_records = get_logic_series_records(logic_series)
    closed = [
        r for r in series_records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("pnl_cash") is not None
    ]
    openish = [r for r in series_records if r.get("status") in {"open", "pending_exit", "exit_failed"}]

    pnl = round(sum(float(r.get("pnl_cash", 0) or 0) for r in closed), 2)
    wins = sum(1 for r in closed if float(r.get("pnl_cash", 0) or 0) > 0)
    count = len(closed)
    win_rate = round((wins / count) * 100, 1) if count else 0.0
    last_window = closed[-DRAWDOWN_WINDOW:] if count else []
    recent_drawdown = round(sum(float(r.get("pnl_cash", 0) or 0) for r in last_window), 2) if last_window else 0.0

    return {
        "logic_series": logic_series or LOGIC_SERIES,
        "closed_count": count,
        "open_count": len(openish),
        "wins": wins,
        "losses": count - wins,
        "win_rate": win_rate,
        "pnl": pnl,
        "take_profits": sum(1 for r in closed if r.get("close_reason") == "take_profit"),
        "stop_losses": sum(1 for r in closed if r.get("close_reason") in {"stop_loss", "stop_loss_intra"}),
        "reevals": sum(1 for r in closed if r.get("close_reason") == "reeval"),
        "loss_total": sum(1 for r in closed if r.get("close_action") == "LOSS_TOTAL"),
        "resolved_win": sum(1 for r in closed if r.get("close_action") == "RESOLVED_WIN"),
        "recent_drawdown": recent_drawdown,
        "recent_window_size": len(last_window),
    }


def get_validated_closed_postmortems():
    """Postmortems cerrados y validados para observabilidad/trofeos del dashboard."""
    records = load_postmortem_data()
    closed = [
        r for r in records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("pnl_cash") is not None
    ]
    closed.sort(key=lambda r: (r.get("closed_at") or "", r.get("opened_at") or ""), reverse=True)
    return closed


def _dashboard_status_item(label, value, detail, status):
    """Normaliza items operativos reutilizables para dashboard."""
    tags = {
        "good": "OK",
        "bad": "Pendiente",
        "waiting": "Esperando muestra",
        "blocked": "Bloqueado",
    }
    return {
        "label": label,
        "value": value,
        "detail": detail,
        "status": status,
        "tag": tags.get(status, "Pendiente"),
    }


def _dashboard_record_meta(record):
    """Contexto compacto de serie/versión para trofeos del dashboard."""
    version = record.get("bot_version_closed") or record.get("bot_version_opened") or "v?"
    logic_series = _extract_logic_series(record.get("bot_version_opened")) or _extract_logic_series(record.get("bot_version_closed"))
    action = record.get("close_action", "")
    reason = record.get("close_reason", "")
    parts = [version]
    if logic_series:
        parts.append(f"serie v{logic_series}")
    if action:
        parts.append(action)
    if reason and reason not in {"", action}:
        parts.append(reason)
    return " · ".join(parts)


def build_dashboard_progress(
    promotion=None,
    clean_stats=None,
    series_clean_stats=None,
    series_stats=None,
    city_accuracy=None,
    alerts=None,
    cycle_series=None,
):
    """Bloque de progreso operativo y readiness del dashboard."""
    if promotion is None:
        promotion = build_promotion_checklist()
    if clean_stats is None:
        clean_stats = get_clean_closed_trade_stats()
    if series_clean_stats is None:
        series_clean_stats = get_logic_series_clean_closed_trade_stats()
    if series_stats is None:
        series_stats = get_logic_series_stats()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if alerts is None:
        alerts = get_dashboard_alert_summary()
    if cycle_series is None:
        _, cycle_series = _load_cycle_counts()

    critical_alerts = 0
    if alerts.get("signals", {}).get("status") != "ok":
        critical_alerts += 1
    if alerts.get("pending_stuck"):
        critical_alerts += 1

    series_trade_remaining = max(0, REVIEW_READY_CLEAN_TRADES - int(series_clean_stats.get("count", 0) or 0))
    series_cycle_remaining = max(0, PROMOTION_MIN_SERIES_CYCLES - int(cycle_series or 0))
    series_closed_count = int(series_stats.get("closed_count", 0) or 0)
    city_coverage_count = sum(
        1 for data in city_accuracy.values()
        if int(data.get("trades", 0) or 0) >= CITY_MIN_TRADES_FOR_BLOCK
    )
    max_city_sample = max((int(data.get("trades", 0) or 0) for data in city_accuracy.values()), default=0)
    gates_missing = max(0, int(promotion.get("total", 0) or 0) - int(promotion.get("passed", 0) or 0))

    readiness_status = "good" if promotion.get("decision") == "READY" else "bad"
    if critical_alerts:
        readiness_status = "blocked"
    elif promotion.get("levels", {}).get("is_max_level"):
        readiness_status = "good"

    useful_closures_status = "good" if series_closed_count >= 1 else "waiting"
    city_coverage_status = "good" if city_coverage_count >= PROMOTION_CITY_COVERAGE_TARGET else "bad"
    if not city_accuracy:
        city_coverage_status = "waiting"

    return [
        _dashboard_status_item(
            f"Muestra para revisar lógica v{LOGIC_SERIES}",
            f"{series_clean_stats['count']} / {REVIEW_READY_CLEAN_TRADES}",
            (
                "muestra suficiente alcanzada"
                if series_trade_remaining == 0
                else f"faltan {series_trade_remaining} trades limpios serie"
            ),
            "good" if series_trade_remaining == 0 else "bad",
        ),
        _dashboard_status_item(
            f"Estabilidad de serie v{LOGIC_SERIES}",
            f"{cycle_series} / {PROMOTION_MIN_SERIES_CYCLES}",
            (
                "estabilidad mínima alcanzada"
                if series_cycle_remaining == 0
                else f"faltan {series_cycle_remaining} ciclos estables"
            ),
            "good" if series_cycle_remaining == 0 else "bad",
        ),
        _dashboard_status_item(
            "Cierres útiles para win rate",
            f"{series_closed_count} cierres",
            (
                "faltan cierres validados para activar win rate y drawdown"
                if series_closed_count == 0
                else "win rate y drawdown de serie ya están activos"
            ),
            useful_closures_status,
        ),
        _dashboard_status_item(
            f"Readiness subida ${promotion['levels']['next_target']:.0f}" if promotion["levels"].get("next_target") else "Readiness nivel máximo",
            f"{promotion['passed']} / {promotion['total']} gates",
            (
                "sin siguiente nivel disponible"
                if promotion["levels"].get("is_max_level")
                else f"faltan {gates_missing} gates · críticos {promotion['blocking_failed']}"
            ),
            readiness_status,
        ),
        _dashboard_status_item(
            "Cobertura de ciudades",
            f"{city_coverage_count} / {PROMOTION_CITY_COVERAGE_TARGET} ciudades",
            (
                f"ninguna ciudad supera {CITY_MIN_TRADES_FOR_BLOCK} cierres todavía"
                if not city_accuracy
                else f"objetivo: >= {CITY_MIN_TRADES_FOR_BLOCK} cierres por ciudad · mejor muestra {max_city_sample}/{CITY_MIN_TRADES_FOR_BLOCK}"
            ),
            city_coverage_status,
        ),
    ]


def build_dashboard_trophies(closed_records=None, city_accuracy=None):
    """Trofeos e hitos del bot usando solo cierres validados."""
    if closed_records is None:
        closed_records = get_validated_closed_postmortems()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _record_pct(record):
        pct = _safe_float(record.get("pnl_pct"))
        if pct is not None:
            return pct
        pnl_cash = _safe_float(record.get("pnl_cash"))
        total_amount = _safe_float(record.get("total_amount"))
        if pnl_cash is not None and total_amount and total_amount > 0:
            return round((pnl_cash / total_amount) * 100, 1)
        return None

    def _make_trophy(label, value="n/d", detail="sin muestra validada", meta="", status="waiting"):
        return {
            "label": label,
            "value": value,
            "detail": detail,
            "meta": meta,
            "status": status,
        }

    trophies = []

    if closed_records:
        best_trade = max(closed_records, key=lambda r: _safe_float(r.get("pnl_cash")) or float("-inf"))
        trophies.append(_make_trophy(
            "Mejor operación",
            f"${(_safe_float(best_trade.get('pnl_cash')) or 0):+.2f}",
            format_postmortem_label(best_trade),
            _dashboard_record_meta(best_trade),
            "good",
        ))

        pct_candidates = [r for r in closed_records if _record_pct(r) is not None]
        if pct_candidates:
            best_return = max(pct_candidates, key=lambda r: _record_pct(r) or float("-inf"))
            trophies.append(_make_trophy(
                "Mejor retorno %",
                f"{(_record_pct(best_return) or 0):+.1f}%",
                format_postmortem_label(best_return),
                _dashboard_record_meta(best_return),
                "good",
            ))
        else:
            trophies.append(_make_trophy("Mejor retorno %"))

        edge_candidates = []
        for record in closed_records:
            for buy in record.get("buys", []) or []:
                edge = _safe_float(buy.get("edge_pct"))
                if edge is not None:
                    edge_candidates.append((edge, record, buy))
            fallback_edge = _safe_float(record.get("latest_edge_pct"))
            if fallback_edge is not None and not (record.get("buys") or []):
                edge_candidates.append((fallback_edge, record, None))
        if edge_candidates:
            edge_value, edge_record, _ = max(edge_candidates, key=lambda item: item[0])
            trophies.append(_make_trophy(
                "Mayor edge ejecutado",
                f"{edge_value:+.1f}%",
                format_postmortem_label(edge_record),
                _dashboard_record_meta(edge_record),
                "good",
            ))
        else:
            trophies.append(_make_trophy("Mayor edge ejecutado"))

        win_candidates = [
            r for r in closed_records
            if (_safe_float(r.get("pnl_cash")) or 0) > 0 or r.get("close_action") == "RESOLVED_WIN"
        ]
        if win_candidates:
            first_win = min(win_candidates, key=lambda r: (r.get("closed_at") or r.get("opened_at") or ""))
            trophies.append(_make_trophy(
                "Primera victoria validada",
                format_postmortem_label(first_win),
                f"${(_safe_float(first_win.get('pnl_cash')) or 0):+.2f}",
                _dashboard_record_meta(first_win),
                "good",
            ))
        else:
            trophies.append(_make_trophy("Primera victoria validada"))

        recovery_candidates = [
            r for r in closed_records
            if r.get("close_action") == "SELL" and (_safe_float(r.get("pnl_cash")) or 0) > 0
        ]
        if recovery_candidates:
            recovery = max(recovery_candidates, key=lambda r: _safe_float(r.get("pnl_cash")) or float("-inf"))
            trophies.append(_make_trophy(
                "Mayor recuperación en una salida",
                f"${(_safe_float(recovery.get('pnl_cash')) or 0):+.2f}",
                format_postmortem_label(recovery),
                _dashboard_record_meta(recovery),
                "good",
            ))
        else:
            trophies.append(_make_trophy("Mayor recuperación en una salida"))

        worst_trade = min(closed_records, key=lambda r: _safe_float(r.get("pnl_cash")) or float("inf"))
        trophies.append(_make_trophy(
            "Peor operación",
            f"${(_safe_float(worst_trade.get('pnl_cash')) or 0):+.2f}",
            format_postmortem_label(worst_trade),
            _dashboard_record_meta(worst_trade),
            "bad",
        ))
    else:
        trophies.extend([
            _make_trophy("Mejor operación"),
            _make_trophy("Mejor retorno %"),
            _make_trophy("Mayor edge ejecutado"),
            _make_trophy("Primera victoria validada"),
            _make_trophy("Mayor recuperación en una salida"),
            _make_trophy("Peor operación"),
        ])

    if city_accuracy:
        city_items = list(city_accuracy.items())
        best_city = max(city_items, key=lambda item: (item[1].get("pnl", 0), item[1].get("win_rate", 0), item[1].get("trades", 0)))
        worst_city = min(city_items, key=lambda item: (item[1].get("pnl", 0), item[1].get("win_rate", 0), -item[1].get("trades", 0)))
        trophies.append(_make_trophy(
            "Ciudad más rentable",
            best_city[0],
            f"${best_city[1].get('pnl', 0):+.2f} · WR {best_city[1].get('win_rate', 0):.1f}%",
            f"{best_city[1].get('trades', 0)} trades validados",
            "good",
        ))
        trophies.append(_make_trophy(
            "Ciudad más peligrosa",
            worst_city[0],
            f"${worst_city[1].get('pnl', 0):+.2f} · WR {worst_city[1].get('win_rate', 0):.1f}%",
            f"{worst_city[1].get('trades', 0)} trades validados",
            "bad",
        ))
    else:
        trophies.extend([
            _make_trophy("Ciudad más rentable"),
            _make_trophy("Ciudad más peligrosa"),
        ])

    return trophies


def build_dashboard_unlocks(
    promotion=None,
    series_stats=None,
    series_clean_stats=None,
    city_accuracy=None,
    alerts=None,
):
    """Desbloqueos y confirmaciones pendientes antes de actuar."""
    if promotion is None:
        promotion = build_promotion_checklist()
    if series_stats is None:
        series_stats = get_logic_series_stats()
    if series_clean_stats is None:
        series_clean_stats = get_logic_series_clean_closed_trade_stats()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if alerts is None:
        alerts = get_dashboard_alert_summary()
    _, cycle_series = _load_cycle_counts()

    series_trade_remaining = max(0, REVIEW_READY_CLEAN_TRADES - int(series_clean_stats.get("count", 0) or 0))
    series_cycle_remaining = max(0, PROMOTION_MIN_SERIES_CYCLES - int(cycle_series or 0))
    series_closed_count = int(series_stats.get("closed_count", 0) or 0)
    critical_operational = []
    if alerts.get("signals", {}).get("status") != "ok":
        critical_operational.append(f"signals={alerts['signals']['status']}")
    if alerts.get("pending_stuck"):
        critical_operational.append(f"pending_exit={len(alerts['pending_stuck'])}")

    best_city_name = None
    best_city_trades = 0
    if city_accuracy:
        best_city_name, best_city_data = max(city_accuracy.items(), key=lambda item: int(item[1].get("trades", 0) or 0))
        best_city_trades = int(best_city_data.get("trades", 0) or 0)

    qualified_cities = sum(
        1 for data in city_accuracy.values()
        if int(data.get("trades", 0) or 0) >= CITY_MIN_TRADES_FOR_BLOCK
    )

    next_target = promotion["levels"].get("next_target")
    next_target_text = f"${next_target:.0f}" if next_target else "siguiente nivel"

    return [
        _dashboard_status_item(
            f"Revisar lógica v{LOGIC_SERIES} con confianza",
            (
                "muestra suficiente alcanzada"
                if series_trade_remaining == 0
                else f"faltan {series_trade_remaining} trades limpios serie"
            ),
            f"objetivo: {REVIEW_READY_CLEAN_TRADES} cierres limpios de la serie actual",
            "good" if series_trade_remaining == 0 else "bad",
        ),
        _dashboard_status_item(
            f"Evaluar subida de bankroll a {next_target_text}",
            (
                "gates completos para evaluación manual"
                if promotion["decision"] == "READY"
                else f"faltan {promotion['blocking_failed']} gates críticos"
            ),
            f"gates totales: {promotion['passed']}/{promotion['total']}",
            (
                "blocked" if critical_operational else
                "good" if promotion["decision"] == "READY" else
                "bad"
            ),
        ),
        _dashboard_status_item(
            "Activar win rate y drawdown de serie",
            (
                f"{series_closed_count} cierres validados"
                if series_closed_count > 0
                else "falta al menos 1 cierre serie validado"
            ),
            "sin este cierre, las métricas de serie no son interpretables",
            "good" if series_closed_count > 0 else "waiting",
        ),
        _dashboard_status_item(
            "Accuracy con muestra suficiente por ciudad",
            (
                f"{qualified_cities} ciudades ya superan el umbral"
                if qualified_cities > 0
                else (
                    f"faltan {max(0, CITY_MIN_TRADES_FOR_BLOCK - best_city_trades)} cierres en {best_city_name}"
                    if best_city_name
                    else "sin cierres por ciudad todavía"
                )
            ),
            f"umbral: {CITY_MIN_TRADES_FOR_BLOCK} cierres validados por ciudad",
            "good" if qualified_cities > 0 else "waiting" if not city_accuracy else "bad",
        ),
        _dashboard_status_item(
            "Sin alertas críticas operativas",
            (
                "signals ok y sin pending exits atascadas"
                if not critical_operational
                else " | ".join(critical_operational)
            ),
            "las alertas de observabilidad bloquean decisiones de subida si siguen activas",
            "good" if not critical_operational else "blocked",
        ),
        _dashboard_status_item(
            "Confiar en métricas de serie",
            (
                f"{series_closed_count} cierres validados disponibles"
                if series_closed_count > 0
                else "todavía no hay cierres validados en la serie"
            ),
            "sin cierres validados, PnL/WR/drawdown de la serie son solo placeholders",
            "good" if series_closed_count > 0 else "waiting",
        ),
    ]


def get_bankroll_level_context():
    """Calcula el nivel actual y el siguiente escalón de bankroll."""
    levels = sorted({float(v) for v in BANKROLL_LEVELS})
    current_level_index = -1
    for i, level_value in enumerate(levels):
        if BANKROLL >= level_value:
            current_level_index = i

    if current_level_index < 0:
        current_level_index = 0

    current_target = levels[current_level_index]
    next_target = levels[current_level_index + 1] if current_level_index + 1 < len(levels) else None

    return {
        "levels": levels,
        "current_level": current_level_index + 1,
        "current_target": current_target,
        "next_target": next_target,
        "is_max_level": next_target is None,
    }


def load_agent_events(limit=None):
    """Carga eventos estructurados del scoreboard de agentes."""
    events = []
    if not os.path.exists(AGENT_EVENTS_FILE):
        return events
    try:
        with open(AGENT_EVENTS_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict):
                    events.append(item)
    except Exception as e:
        log.warning(f"Error cargando agent_events: {e}")
        return []

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    if limit is not None:
        events = events[:limit]
    return events


def _normalize_agent_event_stage(event):
    """Normaliza el estado de una contribución para el scoreboard."""
    if not isinstance(event, dict):
        return "proposed"

    stage = str(event.get("stage", "") or "").strip().lower()
    if stage in {"proposed", "implemented", "validated"}:
        return stage

    if event.get("validated"):
        return "validated"
    if event.get("type") in {"fix_implemented", "feature_shipped", "review_correction", "validated_improvement"}:
        return "implemented"
    return "proposed"


def compute_agent_scorecard(events):
    """Agrega eventos en un ranking útil, priorizando impacto validado."""
    scorecard = {}
    for event in events:
        agent = event.get("agent", "Unknown")
        row = scorecard.setdefault(agent, {
            "agent": agent,
            "points": 0,
            "events": 0,
            "bugs_detected": 0,
            "fixes": 0,
            "proposed": 0,
            "implemented": 0,
            "validated": 0,
            "corrections": 0,
            "major_changes": 0,
            "proposed_points": 0,
            "implemented_points": 0,
            "validated_points": 0,
            "last_event": "",
        })
        stage = _normalize_agent_event_stage(event)
        points = int(event.get("points", 0) or 0)
        row["events"] += 1
        row["points"] += points
        row["last_event"] = max(row["last_event"], event.get("timestamp", ""))
        row[stage] += 1
        row[f"{stage}_points"] += points

        event_type = event.get("type", "")
        if event_type == "bug_detected":
            row["bugs_detected"] += 1
        if event_type in {"fix_implemented", "review_correction", "feature_shipped", "validated_improvement"}:
            row["fixes"] += 1
        if event.get("target_agent") and event.get("target_agent") != agent:
            row["corrections"] += 1
        if event.get("impact") in {"high", "critical"}:
            row["major_changes"] += 1

    ranking = sorted(
        scorecard.values(),
        key=lambda row: (
            -row["validated_points"],
            -row["points"],
            -row["corrections"],
            -row["bugs_detected"],
            row["agent"],
        ),
    )
    return ranking


def build_agent_rivalry(events):
    """Construye un resumen simple de quién corrige/detecta problemas a quién."""
    rivalry = {}
    for event in events:
        source = event.get("agent")
        target = event.get("target_agent")
        if not source or not target or source == target:
            continue
        key = (source, target)
        rivalry[key] = rivalry.get(key, 0) + 1

    rows = []
    for (source, target), count in sorted(rivalry.items(), key=lambda item: -item[1]):
        rows.append({
            "source": source,
            "target": target,
            "count": count,
        })
    return rows


def get_dashboard_alert_summary():
    """Resume alertas y riesgos operativos visibles para el panel."""
    signals = inspect_signals_file_health()
    issue = signals.get("status", "unknown")
    audit = load_audit_data()
    pending = audit.get("pending_sells", [])
    now = datetime.now(timezone.utc)

    pending_stuck = []
    for sell in pending:
        try:
            placed_at = datetime.fromisoformat(sell.get("timestamp", ""))
        except Exception:
            continue
        age_hours = (now - placed_at).total_seconds() / 3600
        if age_hours >= PENDING_EXIT_ALERT_HOURS:
            pending_stuck.append({
                "city": sell.get("city", "?"),
                "side": sell.get("side", "?"),
                "age_hours": round(age_hours, 1),
                "price": float(sell.get("price", 0) or 0),
            })

    city_accuracy = get_city_accuracy()
    flagged_cities = [
        {
            "city": city,
            "win_rate": data["win_rate"],
            "trades": data["trades"],
            "pnl": round(data["pnl"], 2),
        }
        for city, data in city_accuracy.items()
        if data["trades"] >= CITY_MIN_TRADES_FOR_BLOCK and data["win_rate"] <= CITY_BLOCK_WIN_RATE
    ]
    flagged_cities.sort(key=lambda item: (item["win_rate"], -item["trades"], item["city"]))

    active_items = []
    if issue != "ok":
        active_items.append({
            "level": "critical" if issue in {"missing", "error"} else "warn",
            "title": "Señales de traders",
            "detail": f"{issue} | accionables={signals.get('actionable', 0)}",
        })
    if pending_stuck:
        active_items.append({
            "level": "warn",
            "title": "Pending exits atascadas",
            "detail": f"{len(pending_stuck)} órdenes > {PENDING_EXIT_ALERT_HOURS:.0f}h",
        })
    if flagged_cities:
        active_items.append({
            "level": "warn",
            "title": "Ciudades con accuracy baja",
            "detail": ", ".join(f"{item['city']} ({item['win_rate']}%)" for item in flagged_cities[:4]),
        })

    return {
        "signals": signals,
        "pending_stuck": pending_stuck,
        "flagged_cities": flagged_cities,
        "active_items": active_items,
    }


def build_promotion_checklist():
    """Checklist gamificado para decidir si el bankroll puede subir de nivel."""
    def _check(label, value, scope, passed, blocking, waiting=False):
        if waiting:
            status = "waiting"
            tag = "Esperando muestra"
        elif passed:
            status = "good"
            tag = "OK"
        else:
            status = "bad"
            tag = "Pendiente"
        return {
            "label": label,
            "value": value,
            "scope": scope,
            "passed": passed,
            "blocking": blocking,
            "waiting": waiting,
            "status": status,
            "tag": tag,
        }

    levels = get_bankroll_level_context()
    clean_stats = get_clean_closed_trade_stats()
    series_clean_stats = get_logic_series_clean_closed_trade_stats()
    series_stats = get_logic_series_stats()
    alerts = get_dashboard_alert_summary()
    cycle_total, cycle_series = _load_cycle_counts()
    _ = cycle_total
    has_series_closures = series_stats["closed_count"] > 0
    has_drawdown_window = series_stats["recent_window_size"] > 0

    checks = [
        _check(
            "Trades limpios históricos",
            f"{clean_stats['count']} / {REVIEW_READY_CLEAN_TRADES}",
            "Histórico",
            clean_stats["count"] >= REVIEW_READY_CLEAN_TRADES,
            False,
        ),
        _check(
            f"Trades limpios serie v{LOGIC_SERIES}",
            f"{series_clean_stats['count']} / {REVIEW_READY_CLEAN_TRADES}",
            f"Serie v{LOGIC_SERIES}",
            series_clean_stats["count"] >= REVIEW_READY_CLEAN_TRADES,
            True,
        ),
        _check(
            f"Ciclos estables serie v{LOGIC_SERIES}",
            f"{cycle_series} / {PROMOTION_MIN_SERIES_CYCLES}",
            f"Serie v{LOGIC_SERIES}",
            cycle_series >= PROMOTION_MIN_SERIES_CYCLES,
            True,
        ),
        _check(
            f"PnL serie v{LOGIC_SERIES}",
            f"${series_stats['pnl']:+.2f}" if has_series_closures else "sin cierres",
            f"Serie v{LOGIC_SERIES}",
            has_series_closures and series_stats["pnl"] >= PROMOTION_MIN_SERIES_PNL,
            True,
            waiting=not has_series_closures,
        ),
        _check(
            f"Win rate serie v{LOGIC_SERIES}",
            (
                f"{series_stats['win_rate']}% / {PROMOTION_MIN_SERIES_WIN_RATE:.1f}%"
                if has_series_closures
                else f"sin cierres / {PROMOTION_MIN_SERIES_WIN_RATE:.1f}%"
            ),
            f"Serie v{LOGIC_SERIES}",
            has_series_closures and series_stats["win_rate"] >= PROMOTION_MIN_SERIES_WIN_RATE,
            True,
            waiting=not has_series_closures,
        ),
        _check(
            f"Drawdown últimos {DRAWDOWN_WINDOW} cierres",
            (
                f"${series_stats['recent_drawdown']:+.2f} / umbral ${DRAWDOWN_THRESHOLD:.2f}"
                if has_drawdown_window
                else f"sin cierres / umbral ${DRAWDOWN_THRESHOLD:.2f}"
            ),
            f"Serie v{LOGIC_SERIES}",
            has_drawdown_window and (
                series_stats["recent_window_size"] < DRAWDOWN_WINDOW
                or series_stats["recent_drawdown"] > DRAWDOWN_THRESHOLD
            ),
            True,
            waiting=not has_drawdown_window,
        ),
        _check(
            "Signals operativas",
            alerts["signals"]["status"],
            "Operativa",
            alerts["signals"]["status"] == "ok",
            True,
        ),
        _check(
            "Pending exits atascadas",
            str(len(alerts["pending_stuck"])),
            "Operativa",
            len(alerts["pending_stuck"]) == 0,
            True,
        ),
        _check(
            "Ciudades flaggeadas críticas",
            str(len(alerts["flagged_cities"])),
            "Riesgo",
            len(alerts["flagged_cities"]) == 0,
            False,
        ),
    ]

    passed = sum(1 for item in checks if item["passed"])
    blocking_failed = sum(1 for item in checks if item["blocking"] and not item["passed"])
    total = len(checks)

    if levels["is_max_level"]:
        decision = "MAX_LEVEL"
        decision_label = "Nivel máximo alcanzado"
    elif blocking_failed == 0 and passed == total:
        decision = "READY"
        decision_label = f"Listo para evaluar subida a ${levels['next_target']:.0f}"
    elif blocking_failed <= 1 and passed >= total - 2:
        decision = "NEARLY"
        decision_label = "Casi listo, conviene observar algunos ciclos más"
    else:
        decision = "HOLD"
        decision_label = "Aún no listo para subir bankroll"

    return {
        "levels": levels,
        "checks": checks,
        "trade_target": REVIEW_READY_CLEAN_TRADES,
        "history_clean_stats": clean_stats,
        "series_clean_stats": series_clean_stats,
        "passed": passed,
        "total": total,
        "progress_pct": round((passed / total) * 100, 1) if total else 0.0,
        "blocking_failed": blocking_failed,
        "decision": decision,
        "decision_label": decision_label,
    }


def load_cycle_summary_data():
    """Carga el último resumen de ciclo."""
    if not os.path.exists(CYCLE_SUMMARY_FILE):
        return {}
    try:
        with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_dashboard_snapshot():
    """Construye el snapshot completo que renderiza el dashboard web."""
    cycle_total, cycle_series = _load_cycle_counts()
    cycle_summary = load_cycle_summary_data()
    cycle_history = load_cycle_history(limit=8)
    clean_stats = get_clean_closed_trade_stats()
    series_clean_stats = get_logic_series_clean_closed_trade_stats()
    validated_closed = get_validated_closed_postmortems()
    perf = get_performance_summary() or {}
    series_stats = get_logic_series_stats()
    alerts = get_dashboard_alert_summary()
    promotion = build_promotion_checklist()
    city_accuracy = get_city_accuracy()
    progress = build_dashboard_progress(
        promotion=promotion,
        clean_stats=clean_stats,
        series_clean_stats=series_clean_stats,
        series_stats=series_stats,
        city_accuracy=city_accuracy,
        alerts=alerts,
        cycle_series=cycle_series,
    )
    unlocks = build_dashboard_unlocks(
        promotion=promotion,
        series_stats=series_stats,
        series_clean_stats=series_clean_stats,
        city_accuracy=city_accuracy,
        alerts=alerts,
    )
    portfolio = _get_portfolio_and_positions()
    trophies = build_dashboard_trophies(closed_records=validated_closed, city_accuracy=city_accuracy)
    agent_events = []
    stage_labels = {
        "proposed": "Propuesta",
        "implemented": "Implementada",
        "validated": "Validada",
    }
    stage_badges = {
        "proposed": "muted",
        "implemented": "accent",
        "validated": "good",
    }
    for raw_event in load_agent_events(limit=30):
        event = dict(raw_event)
        stage = _normalize_agent_event_stage(event)
        event["stage"] = stage
        event["validated"] = bool(event.get("validated")) or stage == "validated"
        event["stage_label"] = stage_labels[stage]
        event["stage_badge"] = stage_badges[stage]
        agent_events.append(event)
    agent_scoreboard = compute_agent_scorecard(agent_events)
    rivalry = build_agent_rivalry(agent_events)

    open_positions = []
    if portfolio and isinstance(portfolio.get("active"), list):
        for pos in portfolio["active"][:8]:
            open_positions.append({
                "label": _parse_position_label(pos.get("title", ""), pos.get("outcome", "")),
                "current_value": round(float(pos.get("currentValue", 0) or 0), 2),
                "cash_pnl": round(float(pos.get("cashPnl", 0) or 0), 2),
                "percent_pnl": round(float(pos.get("percentPnl", 0) or 0), 1),
            })

    flagged_city_names = {item["city"] for item in alerts["flagged_cities"]}
    top_cities = sorted(
        (
            {
                "city": city,
                "trades": data["trades"],
                "win_rate": data["win_rate"],
                "pnl": round(data["pnl"], 2),
                "risk_level": (
                    "critical"
                    if city in flagged_city_names
                    else "watch" if data["pnl"] < 0 or data["win_rate"] < 50.0 else "good"
                ),
                "risk_label": (
                    "Crítica"
                    if city in flagged_city_names
                    else "Observación" if data["pnl"] < 0 or data["win_rate"] < 50.0 else "OK"
                ),
            }
            for city, data in city_accuracy.items()
        ),
        key=lambda item: (
            0 if item["risk_level"] == "critical" else 1 if item["risk_level"] == "watch" else 2,
            item["win_rate"],
            item["pnl"],
            -item["trades"],
            item["city"],
        ),
    )[:8]

    cycle_history_display = []
    for raw_cycle in reversed(cycle_history):
        cycle = dict(raw_cycle)
        cycle_logic_series = (
            _extract_logic_series(cycle.get("logic_series"))
            or _extract_logic_series(cycle.get("version"))
        )
        if cycle_logic_series and cycle.get("logic_cycle_number") is not None:
            cycle["series_display"] = f"v{cycle_logic_series} #{cycle.get('logic_cycle_number')}"
        elif cycle_logic_series:
            cycle["series_display"] = f"legacy v{cycle_logic_series}"
        else:
            cycle["series_display"] = "legacy"
        cycle_history_display.append(cycle)

    last_cycle_label = "Sin ciclos aún"
    if cycle_summary:
        cycle_label_series = (
            _extract_logic_series(cycle_summary.get("logic_series"))
            or _extract_logic_series(cycle_summary.get("version"))
        )
        if cycle_label_series and cycle_summary.get("logic_cycle_number") is not None:
            last_cycle_label = (
                f"Total #{cycle_summary.get('cycle_number', '?')} | "
                f"Serie v{cycle_label_series} #{cycle_summary.get('logic_cycle_number')}"
            )
        elif cycle_label_series:
            last_cycle_label = f"Total #{cycle_summary.get('cycle_number', '?')} | legacy v{cycle_label_series}"
        else:
            last_cycle_label = f"Total #{cycle_summary.get('cycle_number', '?')} | legacy"

    auth_enabled = bool(DASHBOARD_USER and DASHBOARD_PASSWORD)
    series_metrics = dict(series_stats)
    series_metrics["has_closed_count"] = series_stats["closed_count"] > 0
    series_metrics["has_drawdown_data"] = series_stats["recent_window_size"] > 0
    series_metrics["pnl_display"] = f"${series_stats['pnl']:+.2f}" if series_metrics["has_closed_count"] else "n/d"
    series_metrics["win_rate_display"] = f"{series_stats['win_rate']}%" if series_metrics["has_closed_count"] else "n/d"
    series_metrics["drawdown_display"] = (
        f"${series_stats['recent_drawdown']:+.2f}" if series_metrics["has_drawdown_data"] else "n/d"
    )

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "title": DASHBOARD_TITLE,
        "version": BOT_VERSION,
        "logic_series": LOGIC_SERIES,
        "mode": "REAL" if not DRY_RUN else "DRY RUN",
        "auth_enabled": auth_enabled,
        "next_run": bot_state["next_run"].strftime("%Y-%m-%d %H:%M UTC") if bot_state.get("next_run") else "No programado",
        "last_run": bot_state["last_run"].strftime("%Y-%m-%d %H:%M UTC") if bot_state.get("last_run") else "",
        "cycle_total": cycle_total,
        "cycle_series": cycle_series,
        "last_cycle_label": last_cycle_label,
        "cycle_summary": cycle_summary,
        "cycle_history": cycle_history_display,
        "promotion": promotion,
        "progress": progress,
        "trophies": trophies,
        "unlocks": unlocks,
        "clean_stats": clean_stats,
        "series_clean_stats": series_clean_stats,
        "series_stats": series_metrics,
        "performance": perf,
        "alerts": alerts,
        "portfolio": portfolio,
        "open_positions": open_positions,
        "top_cities": top_cities,
        "agent_scoreboard": agent_scoreboard,
        "agent_events": agent_events[:12],
        "rivalry": rivalry[:8],
        "refresh_sec": DASHBOARD_REFRESH_SEC,
        "intra_label": f"{INTRA_SL_INTERVAL} min" if INTRA_SL_INTERVAL > 0 else "desactivado",
    }


def _dashboard_auth_ok(req):
    """Autenticación básica opcional para el dashboard."""
    if not DASHBOARD_USER or not DASHBOARD_PASSWORD:
        return True
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
    except Exception:
        return False
    user, _, password = decoded.partition(":")
    return user == DASHBOARD_USER and password == DASHBOARD_PASSWORD


def create_dashboard_app():
    """Crea la app web del dashboard."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/healthz")
    def dashboard_healthz():
        return jsonify({
            "ok": True,
            "version": BOT_VERSION,
            "logic_series": LOGIC_SERIES,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    @app.route("/api/dashboard.json")
    def dashboard_api():
        if not _dashboard_auth_ok(request):
            return Response(
                "Dashboard auth required",
                401,
                {"WWW-Authenticate": 'Basic realm="Polymarket Dashboard"'},
            )
        return jsonify(build_dashboard_snapshot())

    @app.route("/")
    def dashboard_home():
        if not _dashboard_auth_ok(request):
            return Response(
                "Dashboard auth required",
                401,
                {"WWW-Authenticate": 'Basic realm="Polymarket Dashboard"'},
            )
        return render_template("dashboard.html", dashboard=build_dashboard_snapshot())

    return app


def start_dashboard_server():
    """Levanta el dashboard web en un thread independiente."""
    if not DASHBOARD_ENABLED:
        log.info("Dashboard web: desactivado por configuración")
        return None

    app = create_dashboard_app()

    def _serve_dashboard():
        try:
            serve(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, threads=6)
        except Exception as e:
            log.warning(f"Dashboard web error: {e}")

    thread = threading.Thread(target=_serve_dashboard, daemon=True, name="DashboardHTTP")
    thread.start()
    log.info(f"Dashboard web: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    return thread


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
    if not os.path.exists(SIGNALS_FILE):
        log.info("load_trader_signals: signals.json no existe")
        return {}
    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
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
            {"text": "📚 Postmortem", "callback_data": "postmortem"},
            {"text": "📍 Accuracy", "callback_data": "accuracy"},
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

    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    # Último ciclo desde cycle_summary.json si existe
    cycle_line = ""
    cycle_ts = None
    if os.path.exists(CYCLE_SUMMARY_FILE):
        try:
            with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
                cd = json.load(f)
            cycle_ts = cd.get("timestamp_utc")
            mgmt = cd.get("management", {})
            scan = cd.get("scan", {})
            buys = cd.get("buys", [])
            n_buys = len(buys)
            n_sold = mgmt.get("n_sold", 0)
            n_mkts = scan.get("markets_evaluated", 0)
            exp = cd.get("exposure_after")
            exp_str = f" | Exp ${exp:.2f}" if exp is not None else ""
            cycle_total_num = cd.get("cycle_number", "?")
            logic_cycle_num = cd.get("logic_cycle_number")
            if logic_cycle_num is None:
                cycle_series = (
                    _extract_logic_series(cd.get("logic_series"))
                    or _extract_logic_series(cd.get("version"))
                )
                if cycle_series == LOGIC_SERIES and cycle_total_num == bot_state.get("cycle_count"):
                    logic_cycle_num = bot_state.get("cycle_count_series")
            cycle_label = f"Ciclo total #{cycle_total_num}"
            if logic_cycle_num is not None:
                cycle_label += f" | serie v{LOGIC_SERIES} #{logic_cycle_num}"
            cycle_line = (
                f"\n📋 {cycle_label} "
                f"({cd.get('timestamp_utc','?')[:10]}):\n"
                f"  Mercados: {n_mkts} | Compras: {n_buys} | Ventas: {n_sold}{exp_str}"
            )
        except Exception:
            pass

    if bot_state["last_run"]:
        last_str = bot_state["last_run"].strftime('%d/%m %H:%M UTC')
    elif cycle_ts:
        try:
            last_str = datetime.fromisoformat(cycle_ts.replace("Z", "+00:00")).strftime('%d/%m %H:%M UTC')
        except Exception:
            last_str = f"{cycle_ts[:16]} UTC"
    else:
        last_str = "Nunca"

    if not cycle_line:
        cycle_line = (
            f"\n📋 Último ciclo:\n"
            f"  Oportunidades: {bot_state['last_opportunities']}\n"
            f"  Compras: {bot_state['last_orders_placed']} | Ventas: {bot_state.get('last_sells_placed', 0)}"
        )

    intra_label = f"cada {INTRA_SL_INTERVAL}min" if INTRA_SL_INTERVAL > 0 else "desactivado"

    send_telegram(
        f"📊 <b>Bot {BOT_VERSION} | {modo}</b>\n\n"
        f"💰 Bankroll: <b>${BANKROLL:.2f}</b> | Edge mín: {MIN_EDGE}% (exact: {MIN_EDGE_EXACT}%)\n"
        f"🔧 SL {STOP_LOSS_PCT}% / TP +{TAKE_PROFIT_PCT}%\n"
        f"🛡 Intra-SL: {intra_label}\n\n"
        f"⏱ Estado: {running}\n"
        f"📅 Último: {last_str}\n"
        f"⏰ Próximo: {next_str}\n"
        f"🔢 Ciclos: {bot_state['cycle_count']} total | {bot_state.get('cycle_count_series', 0)} serie v{LOGIC_SERIES}"
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
                        for line in lines[last_start:]:
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
    if not os.path.exists(SIGNALS_FILE):
        send_telegram(
            "🔍 <b>Traders Intel</b>\n\n"
            "Sin datos todavía.\n"
            "Se generarán automáticamente en el próximo ciclo.",
            with_menu=True,
        )
        return

    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
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

    # Cruce con posiciones activas — filtra por ciudad + lado + fecha exacta del mercado
    portfolio = _get_portfolio_and_positions()
    active_positions = {}  # (city_lower, outcome_lower) -> set(fecha_iso)
    if portfolio:
        for pos in portfolio["active"]:
            city = parse_city_from_title(pos.get("title", ""))
            outcome = pos.get("outcome", "")
            market_date_iso = parse_market_date_iso(pos.get("title", ""))
            if city != "?" and outcome:
                key = (city.lower(), outcome.lower())
                active_positions.setdefault(key, set())
                if market_date_iso:
                    active_positions[key].add(market_date_iso)

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
            key = (city.lower(), outcome.lower())
            matching_dates = active_positions.get(key)
            # Filtrar: ciudad+lado coincide con posición activa
            if matching_dates is None:
                continue
            sig_date_iso = parse_market_date_iso(sig_date)
            # Si conocemos fechas de la cartera, exigir match exacto
            if matching_dates:
                if not sig_date_iso or sig_date_iso not in matching_dates:
                    continue
            # Filtrar: fecha no pasada (si el formato es ISO)
            if sig_date_iso and sig_date_iso < today_str:
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
    timing_bits = []
    if scan_ts:
        timing_bits.append(f"Scan: {scan_ts.strftime('%d/%m %H:%M UTC')}")
    if analysis_ts:
        timing_bits.append(f"Análisis: {analysis_ts.strftime('%d/%m %H:%M UTC')}")
    if timing_bits:
        text += f"\n{' | '.join(timing_bits)}\n"

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


def cmd_postmortem():
    """
    📚 Vista simple de postmortem.json para inspección rápida desde Telegram.
    No sustituye análisis profundo, pero permite ver cierres/abiertas sin SSH.
    """
    records = load_postmortem_data()
    if not records:
        has_performance = False
        if os.path.exists(PERFORMANCE_FILE):
            try:
                with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                has_performance = bool(history)
            except Exception:
                pass

        extra = ""
        if has_performance:
            extra = (
                "\n\nHay histórico en performance.json, pero "
                "postmortem.json todavía no se ha rellenado con datos anteriores.\n"
                "Se irá llenando automáticamente con nuevos BUY, SELL y resoluciones."
            )
        send_telegram(
            "📚 <b>Postmortem</b>\n\n"
            "Sin datos todavía.\n"
            "Se irá llenando automáticamente con compras, ventas y resoluciones."
            f"{extra}",
            with_menu=True,
        )
        return

    open_count = sum(1 for r in records if r.get("status") == "open")
    pending_count = sum(1 for r in records if r.get("status") == "pending_exit")
    failed_count = sum(1 for r in records if r.get("status") == "exit_failed")
    closed = [r for r in records if r.get("status") == "closed"]
    closed_count = len(closed)
    sell_closed = sum(1 for r in closed if r.get("close_action") == "SELL")
    resolved_closed = sum(1 for r in closed if r.get("close_action") == "RESOLVED_WIN")

    text = (
        "📚 <b>Postmortem</b>\n\n"
        f"Open: {open_count} | Pending exit: {pending_count}\n"
        f"Exit failed: {failed_count} | Closed: {closed_count}\n"
        f"Cierres SELL: {sell_closed} | Resoluciones WIN: {resolved_closed}\n"
    )

    if closed:
        text += "\n<b>Últimos cierres:</b>\n"
        recent_closed = sorted(
            closed,
            key=lambda r: r.get("closed_at") or r.get("opened_at") or "",
            reverse=True,
        )[:8]
        for rec in recent_closed:
            label = format_postmortem_label(rec)
            close_action = rec.get("close_action", "?")
            reason = rec.get("close_reason", "") or "n/a"
            pnl_cash = rec.get("pnl_cash")
            pnl_str = f"${float(pnl_cash):+.2f}" if isinstance(pnl_cash, (int, float)) else "n/a"
            text += f"  • {label} | {close_action} | {reason} | {pnl_str}\n"

    openish = [r for r in records if r.get("status") in {"open", "pending_exit", "exit_failed"}]
    if openish:
        text += "\n<b>Abiertas / seguimiento:</b>\n"
        recent_open = sorted(
            openish,
            key=lambda r: r.get("last_buy_at") or r.get("opened_at") or "",
            reverse=True,
        )[:8]
        for rec in recent_open:
            label = format_postmortem_label(rec)
            status = rec.get("status", "?")
            amount = rec.get("total_amount", 0)
            edge = rec.get("latest_edge_pct")
            edge_str = f"edge {edge:+.1f}%" if isinstance(edge, (int, float)) else "edge n/a"
            text += f"  • {label} | {status} | ${float(amount):.2f} | {edge_str}\n"

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
        city_acc = get_city_accuracy()
        text += f"\n<b>Top ciudades:</b>\n"
        for city, count in stats['top_cities']:
            pnl = stats['city_pnl'].get(city, 0)
            acc = city_acc.get(city, {})
            wr = f" | WR:{acc['win_rate']}%" if acc.get('win_rate') is not None else ""
            text += f"  {city}: {count} ops, ${pnl:+.2f}{wr}\n"

    text += f"\n<i>⚠️ PnL fiable: dashboard Polymarket.</i>\n"
    send_telegram_paged(text, with_menu=True)


def cmd_info():
    """ℹ️ Bloque resumen del bot para pegar en ChatGPT/Claude."""
    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))

    # Último ciclo desde cycle_summary.json
    cycle_block = ""
    cycle_ts = None
    if os.path.exists(CYCLE_SUMMARY_FILE):
        try:
            with open(CYCLE_SUMMARY_FILE, "r", encoding="utf-8") as f:
                cd = json.load(f)
            cycle_ts = cd.get("timestamp_utc")
            mgmt = cd.get("management", {})
            scan = cd.get("scan", {})
            buys = cd.get("buys", [])
            buys_str = ", ".join(
                f"{b.get('city','?')} {b.get('side','?')} ${b.get('amount',0):.2f}"
                for b in buys
            ) if buys else "ninguna"
            exp = cd.get("exposure_after")
            bud = cd.get("budget_left")
            cycle_total_num = cd.get("cycle_number", "?")
            logic_cycle_num = cd.get("logic_cycle_number")
            if logic_cycle_num is None:
                cycle_series = (
                    _extract_logic_series(cd.get("logic_series"))
                    or _extract_logic_series(cd.get("version"))
                )
                if cycle_series == LOGIC_SERIES and cycle_total_num == bot_state.get("cycle_count"):
                    logic_cycle_num = bot_state.get("cycle_count_series")
            cycle_label = f"Ciclo total #{cycle_total_num}"
            if logic_cycle_num is not None:
                cycle_label += f" | serie v{LOGIC_SERIES} #{logic_cycle_num}"
            cycle_block = (
                f"\n{cycle_label} ({cd.get('timestamp_utc','?')[:16]} UTC)\n"
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

    if bot_state["last_run"]:
        last_str = bot_state["last_run"].strftime('%Y-%m-%d %H:%M UTC')
    elif cycle_ts:
        try:
            last_str = datetime.fromisoformat(cycle_ts.replace("Z", "+00:00")).strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            last_str = f"{cycle_ts[:16]} UTC"
    else:
        last_str = "Nunca"

    # Estadísticas
    stats = get_performance_summary()
    perf_block = ""
    if stats:
        perf_block = (
            f"\n{stats['total_buys']} compras, {stats['total_sells']} ventas\n"
            f"PnL ventas: ${stats['sell_pnl']:+.2f}\n"
            f"TP: {stats['take_profits']} | SL: {stats['stop_losses']} | Reeval: {stats['reevals']}\n"
        )

    intra_info = f"Intra-SL: cada {INTRA_SL_INTERVAL}min\n" if INTRA_SL_INTERVAL > 0 else ""
    text = (
        f"<b>BOT POLYMARKET {BOT_VERSION}</b>\n"
        f"Modo: {modo} | Bankroll: ${BANKROLL:.2f}\n"
        f"Edge mín: {MIN_EDGE}% (exact: {MIN_EDGE_EXACT}%) | SL: {STOP_LOSS_PCT}% | TP: +{TAKE_PROFIT_PCT}%\n"
        f"Exp máx: {int(MAX_EXPOSURE_PCT*100)}% | Min bet: ${MIN_BET:.2f}\n"
        f"{intra_info}"
        f"Schedule: {schedule} UTC\n"
        f"Ciclos completados: {bot_state['cycle_count']} total | {bot_state.get('cycle_count_series', 0)} serie v{LOGIC_SERIES}\n"
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


def cmd_accuracy():
    """Muestra accuracy (win rate) por ciudad desde postmortem."""
    city_stats = get_city_accuracy()
    if not city_stats:
        send_telegram("Sin datos de accuracy todavía.", with_menu=True)
        return

    sorted_cities = sorted(city_stats.items(), key=lambda x: -x[1]["trades"])

    lines = ["<b>Accuracy por ciudad</b>\n"]
    for city, data in sorted_cities:
        blocked = " 🚫" if is_city_blocked(city) else ""
        flag = " ⚠️" if data["trades"] >= CITY_MIN_TRADES_FOR_BLOCK and data["win_rate"] <= CITY_BLOCK_WIN_RATE else ""
        lines.append(
            f"<b>{city}</b>{blocked}{flag}: "
            f"{data['wins']}/{data['trades']} ({data['win_rate']}%) "
            f"${data['pnl']:+.2f}"
        )

    send_telegram_paged("\n".join(lines), with_menu=True)


COMMANDS = {
    "estado": cmd_estado, "cartera": cmd_cartera, "ordenes": cmd_ordenes,
    "log": cmd_log, "logfull": cmd_logfull, "forzar": cmd_forzar,
    "modo": cmd_modo, "traders": cmd_traders, "rendimiento": cmd_rendimiento,
    "info": cmd_info, "postmortem": cmd_postmortem, "accuracy": cmd_accuracy,
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
    title_full = position.get("title", "?")
    title = title_full[:50]
    city = parse_city_from_title(title)
    initial_value = float(position.get("initialValue", 0))
    current_value = float(position.get("currentValue", 0))
    parsed = parse_temperature_question(title_full)
    market_date = date_text_to_iso(parsed["date_str"]) if parsed and parsed.get("date_str") else ""

    dl.append(f"    💀 LOSS_TOTAL: {outcome} {city} | invertido ${initial_value:.2f} → vale ${current_value:.3f}")

    track_trade("LOSS_TOTAL",
        city=city,
        side=outcome,
        date=market_date,
        question=title_full,
        token_id=asset_id,
        condition=parsed.get("condition", "") if parsed else "",
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
            parsed = parse_temperature_question(title_full)
            market_date = date_text_to_iso(parsed["date_str"]) if parsed and parsed.get("date_str") else ""
            try:
                update_postmortem("RESOLVED_WIN", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "city": parse_city_from_title(title_full),
                    "side": outcome,
                    "date": market_date,
                    "question": title_full,
                    "token_id": asset_id,
                    "condition": parsed.get("condition", "") if parsed else "",
                    "shares": size,
                    "initial_value": initial_value,
                    "payout_est": round(size, 2),
                    "cur_price": cur_price,
                    "bot_version": BOT_VERSION,
                })
            except Exception as e:
                log.warning(f"Error actualizando postmortem resolved_win: {e}")
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
        title_full = p.get("title", "?")
        title = title_full[:50]
        city = parse_city_from_title(title)
        parsed_sell = parse_temperature_question(title_full)
        market_date = date_text_to_iso(parsed_sell["date_str"]) if parsed_sell and parsed_sell.get("date_str") else ""

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
                date=market_date,
                question=title_full,
                token_id=asset_id,
                condition=parsed_sell.get("condition", "") if parsed_sell else "",
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


# ---- v10.5.1: INTRA-CYCLE SL/TP MONITOR ----

def intra_cycle_sl_check(client):
    """Check SL/TP entre ciclos — solo protección, no compras ni re-evaluación."""
    if not sell_lock.acquire(timeout=5):
        log.info("[INTRA-SL] Ciclo principal activo, saltando")
        return

    try:
        funder = os.getenv("FUNDER", "")
        if not funder:
            return

        # Fetch posiciones (mismo endpoint que manage_positions)
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

        n_checked = 0
        n_sold = 0

        for p in positions:
            title_full = p.get("title", "")
            if not re.search(r"temperature", title_full, re.IGNORECASE):
                continue
            current_value = float(p.get("currentValue", 0))
            cur_price = float(p.get("curPrice", 0))
            if current_value < 0.10 or cur_price >= 0.98:
                continue

            asset_id = p.get("asset", "")
            if not asset_id:
                continue

            pct_pnl = float(p.get("percentPnl", 0))
            n_checked += 1

            # Determinar si hay que vender
            sell_type = None
            if pct_pnl <= STOP_LOSS_PCT:
                sell_type = "stop_loss_intra"
                icon, type_label = "🔻", "Stop-loss"
            elif pct_pnl >= TAKE_PROFIT_PCT:
                sell_type = "take_profit_intra"
                icon, type_label = "💰", "Take-profit"

            if not sell_type:
                continue

            outcome = p.get("outcome", "?")
            size = float(p.get("size", 0))
            title = title_full[:50]
            city = parse_city_from_title(title)
            parsed = parse_temperature_question(title_full)
            market_date = date_text_to_iso(parsed["date_str"]) if parsed and parsed.get("date_str") else ""

            sell_price = round(max(0.01, cur_price - SELL_AGGRESSION), 2)
            shares_to_sell = round(size, 2)
            if shares_to_sell < 0.1:
                continue
            estimated_return = round(shares_to_sell * sell_price, 2)
            if estimated_return < 0.10:
                continue

            log.info(f"[INTRA-SL] {sell_type}: {outcome} {city} {pct_pnl:+.1f}%")

            if DRY_RUN:
                log.info(f"[INTRA-SL] [DRY] SELL {outcome} {shares_to_sell}sh × ${sell_price:.2f}")
                n_sold += 1
                continue

            try:
                order_args = OrderArgs(
                    token_id=asset_id,
                    price=sell_price,
                    size=shares_to_sell,
                    side=SELL,
                )
                signed = client.create_order(order_args)
                resp_order = client.post_order(signed, OrderType.GTC)
                oid = resp_order.get("orderID", resp_order.get("id", "?"))
                n_sold += 1

                send_telegram(
                    f"{icon} <b>[INTRA-SL] {type_label}</b>\n"
                    f"{outcome} {city}\n"
                    f"Venta: {shares_to_sell}sh × ${sell_price:.2f}\n"
                    f"PnL: {pct_pnl:+.1f}% (${float(p.get('cashPnl', 0)):+.2f})\n"
                    f"<i>Entre ciclos — próximo ciclo confirmará fill</i>"
                )

                pct = float(p.get("percentPnl", 0))
                track_trade("SELL_PENDING",
                    reason=sell_type,
                    city=city,
                    side=outcome,
                    date=market_date,
                    question=title_full,
                    token_id=asset_id,
                    condition=parsed.get("condition", "") if parsed else "",
                    price=sell_price,
                    shares=shares_to_sell,
                    return_est=estimated_return,
                    avg_buy_price=float(p.get("avgPrice", 0)),
                    pnl_pct=pct,
                    pnl_cash=float(p.get("cashPnl", 0)),
                    order_id=oid,
                )

                audit_register_pending_sell(
                    order_id=oid, city=city,
                    side=outcome, price=sell_price, shares=shares_to_sell,
                    return_est=estimated_return, reason=sell_type,
                )

            except Exception as e:
                log.error(f"[INTRA-SL] Error vendiendo {outcome} {city}: {e}")

        log.info(f"[INTRA-SL] Check: {n_checked} posiciones, {n_sold} vendidas")

    except Exception as e:
        log.warning(f"[INTRA-SL] Error: {e}")
    finally:
        sell_lock.release()


def intra_sl_loop(client):
    """Thread daemon: revisa SL/TP cada INTRA_SL_INTERVAL minutos."""
    log.info(f"[INTRA-SL] Monitor iniciado (cada {INTRA_SL_INTERVAL}min)")
    while True:
        time.sleep(INTRA_SL_INTERVAL * 60)
        try:
            intra_cycle_sl_check(client)
        except Exception as e:
            log.warning(f"[INTRA-SL] Error en loop: {e}")


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
    updated_entries = []
    for entry in history:
        if entry.get("action") != "SELL_PENDING":
            continue
        oid = entry.get("order_id", "")
        if oid in filled_ids:
            entry["action"] = "SELL"
            entry["fill_confirmed"] = datetime.now(timezone.utc).isoformat()
            updated += 1
            updated_entries.append(dict(entry))
        elif oid in expired_ids:
            entry["action"] = "SELL_FAILED"
            entry["fail_reason"] = "expired_no_fill_24h"
            entry["failed_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
            updated_entries.append(dict(entry))

    if updated > 0:
        try:
            with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            dl.append(f"  📝 performance.json: {updated} entradas actualizadas")
            for entry in updated_entries:
                try:
                    update_postmortem(entry.get("action", ""), entry)
                except Exception as e:
                    log.warning(f"Error sincronizando postmortem con performance: {e}")
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
    # v10.5: sigma ampliada — v10.4 sobreconfiaba (win rate 29%, PnL -$8.57)
    # Evidencia: exact bets 20% win rate, modelo asignaba 70-85% a outcomes que perdían
    # Sigma más alta → probabilidades más moderadas → menos trades pero con edge real
    return {0: 2.0, 1: 2.5, 2: 3.0, 3: 3.5}.get(days_ahead, 4.0 if days_ahead <= 5 else 4.5)


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
    log.info(f"BOT {BOT_VERSION} | {today_str} | {mode_label} | ${effective_bankroll:.2f} (tope ${BANKROLL:.2f})")
    log.info("=" * 65)

    # Decision log: registrar inicio
    dl = []  # Lista de líneas para el log de decisiones
    dl.append(f"{'='*50}")
    dl.append(f"CICLO {bot_state['cycle_count']+1} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | {mode_label}")
    dl.append(f"BANKROLL: ${effective_bankroll:.2f} (tope ${BANKROLL:.2f}) | MIN_EDGE={MIN_EDGE}% (exact: {MIN_EDGE_EXACT}%)")
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
        with sell_lock:  # v10.5.1: evitar conflicto con intra-SL thread
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
    blocked_city_skip = 0
    blocked_seen = set()
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
        if is_city_blocked(city):
            blocked_city_skip += 1
            blocked_seen.add(city)
            continue
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

    dl.append(f"FILTROS: {len(candidates)} pasan | {parse_fail} no parseables | {date_fail} fuera de fecha | {timezone_skip} bloqueados por zona horaria | {blocked_city_skip} bloqueados por ciudad | {price_fail} fuera de precio | {liq_fail} sin liquidez")
    if blocked_seen:
        dl.append(f"  🚫 Ciudades bloqueadas operativamente: {', '.join(sorted(blocked_seen))} (WU vs Open-Meteo)")

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

        # v10.5: exact bets requieren MIN_EDGE_EXACT (15%) por win rate histórico bajo
        effective_min_edge = MIN_EDGE_EXACT if c["condition"] == "exact" else MIN_EDGE
        if edge_pct < effective_min_edge:
            edge_analysis.append(f"  ✗ {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% → BAJO (min {effective_min_edge}%)")
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
                    question=trade["question"],
                    token_id=trade["token_id"],
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
            "version": BOT_VERSION,
            "logic_series": LOGIC_SERIES,
            "cycle_number": bot_state["cycle_count"] + 1,
            "logic_cycle_number": bot_state.get("cycle_count_series", 0) + 1,
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

    try:
        run_observability_alerts()
    except Exception as e:
        log.warning(f"Error evaluando alertas de observabilidad: {e}")

    bot_state["cycle_count"] += 1
    bot_state["cycle_count_series"] = bot_state.get("cycle_count_series", 0) + 1
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
    log.info(f"POLYMARKET BOT {BOT_VERSION} | Schedule: {sorted(SCHEDULE_HOURS_UTC)} UTC")
    log.info(f"Modo: {'DRY RUN' if DRY_RUN else 'REAL'}")
    log.info("=" * 65)

    # v10.5.4: ciclos acumulativos + contador por serie lógica
    cycle_count_total, cycle_count_series = _load_cycle_counts()
    bot_state["cycle_count"] = cycle_count_total
    bot_state["cycle_count_series"] = cycle_count_series
    log.info(
        f"Ciclos históricos cargados: {bot_state['cycle_count']} total | "
        f"{bot_state['cycle_count_series']} serie v{LOGIC_SERIES}"
    )

    start_dashboard_server()

    clob_client = setup_client()
    if clob_client is None:
        send_telegram("❌ <b>Error autenticación</b>")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        threading.Thread(target=telegram_polling_loop, daemon=True, name="TelegramPoller").start()
        log.info("Telegram polling: OK")

    # v10.5.1: Intra-cycle SL monitor
    if INTRA_SL_INTERVAL > 0 and clob_client is not None:
        threading.Thread(target=intra_sl_loop, args=(clob_client,), daemon=True, name="IntraSL").start()
        log.info(f"[INTRA-SL] Monitor cada {INTRA_SL_INTERVAL}min: OK")

    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    intra_label = f"cada {INTRA_SL_INTERVAL}min" if INTRA_SL_INTERVAL > 0 else "desactivado"
    send_telegram(
        f"🤖 <b>Bot {BOT_VERSION} arrancado</b>\n"
        f"Modo: {modo} | ${BANKROLL:.2f}\n"
        f"Min edge: {MIN_EDGE}% (exact: {MIN_EDGE_EXACT}%) | Schedule: {schedule} UTC\n"
        f"🔧 Gestión activa: SL {STOP_LOSS_PCT}% / TP +{TAKE_PROFIT_PCT}%\n"
        f"⏱ Intra-SL: {intra_label}\n"
        f"🌏 Zona horaria per-city activa\n"
        f"🔍 Traders: auto-análisis diario, descubrimiento lunes",
        with_menu=True,
    )

    try:
        rebuilt = backfill_postmortem_from_performance()
        if rebuilt > 0:
            log.info(f"postmortem listo al arrancar: {rebuilt} registros")
    except Exception as e:
        log.warning(f"Error en backfill de postmortem al arrancar: {e}")

    # v9: Ejecutar análisis de traders antes del primer ciclo
    run_trader_tasks()

    try:
        run_observability_alerts()
    except Exception as e:
        log.warning(f"Error evaluando alertas al arrancar: {e}")

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
