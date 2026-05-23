import urllib.request
import urllib.parse
import urllib.error
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
import hashlib
import uuid
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.clob_types import OrderArgs, OrderType, BalanceAllowanceParams, AssetType, TradeParams
from py_clob_client_v2.order_builder.constants import BUY, SELL
from waitress import serve

load_dotenv()

# =============================================================
# bot.py v10.6.43 — Exact/no-QT-match LOG_ONLY evaluation capture, env var OFF (sesion 2026-05-23)
# bot.py v10.6.42 — SQLite Recorder Fase 0: persistencia pasiva fail-safe (sesion 257, 2026-04-27)
# bot.py v10.6.41 — Fill-real reconciliation para SELL por order_id + anti-flapping guard legacy (sesion 255, 2026-04-27)
# bot.py v10.6.40 — Guard SL_intra para condition=exact + days<=1 (Opus, sesion 246, 2026-04-26)
# bot.py v10.6.30 — Dallas al whitelist: degradacion inflada por ghost-position bug (v10.5.12)
# bot.py v10.6.29 — Busan (RKPK) ICAO-only: WU/RKPK resolution confirmado, NOAA 2026 dead
# bot.py v10.6.28 — P5 new cities: Moscow, Amsterdam, Jeddah, Istanbul, Helsinki (ICAO-only)
# bot.py v10.6.27 — P4 whitelist expansion: Tel Aviv, Taipei, Singapore, Wuhan
# bot.py v10.6.24 — reactivar intra-cycle SL/TP monitor
# v10.6.10 — mission HUD discovery / stabilization
# Sesión 36: fallback BANKROLL sincronizado a $25 tras recarga manual
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
BANKROLL = float(os.getenv("BANKROLL", "25.00"))

MIN_EDGE = float(os.getenv("MIN_EDGE", "15.0"))
MIN_BET = float(os.getenv("MIN_BET", "1.00"))           # v10.4: default alineado con Railway
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))   # v9: subido de 0.05 a 0.10 (10%)
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))  # -1 = automático
BOT_VERSION = "v10.6.50"
LOGIC_SERIES = "10.6"
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
LOW_BANKROLL_THRESHOLD = float(os.getenv("LOW_BANKROLL_THRESHOLD", "5.0"))  # v10.6: alerta para recargar
LOW_BANKROLL_RESET_MARGIN = float(os.getenv("LOW_BANKROLL_RESET_MARGIN", "1.0"))  # v10.6: salir de zona roja con margen
FORECAST_CACHE_TTL_SECONDS = int(os.getenv("FORECAST_CACHE_TTL_SECONDS", "900"))
FORECAST_STALE_IF_ERROR_SECONDS = int(os.getenv("FORECAST_STALE_IF_ERROR_SECONDS", "21600"))
FORECAST_RATE_LIMIT_COOLDOWN_SECONDS = int(os.getenv("FORECAST_RATE_LIMIT_COOLDOWN_SECONDS", "120"))
# v10.5.2: City accuracy tracker
CITY_MIN_TRADES_FOR_BLOCK = int(os.getenv("CITY_MIN_TRADES_FOR_BLOCK", "3"))
CITY_BLOCK_WIN_RATE = float(os.getenv("CITY_BLOCK_WIN_RATE", "25.0"))
SHADOW_CANARY_MIN_EDGE_HITS = int(os.getenv("SHADOW_CANARY_MIN_EDGE_HITS", "5"))
SHADOW_CANARY_MIN_CYCLES = int(os.getenv("SHADOW_CANARY_MIN_CYCLES", "10"))
SHADOW_CANARY_MIN_BEST_EDGE = float(os.getenv("SHADOW_CANARY_MIN_BEST_EDGE", str(MIN_EDGE)))
SHADOW_CANARY_MIN_SUPPORT = int(os.getenv("SHADOW_CANARY_MIN_SUPPORT", "5"))
# v10.6.17: días mínimos en shadow antes de poder promocionar a canary
SHADOW_CANARY_MIN_DAYS = int(os.getenv("SHADOW_CANARY_MIN_DAYS", "14"))
ALLOWLIST_REMOVE_MIN_TRADES = int(os.getenv("ALLOWLIST_REMOVE_MIN_TRADES", str(CITY_MIN_TRADES_FOR_BLOCK)))
ALLOWLIST_REMOVE_MAX_WIN_RATE = float(os.getenv("ALLOWLIST_REMOVE_MAX_WIN_RATE", str(CITY_BLOCK_WIN_RATE)))
ALLOWLIST_REMOVE_MAX_PNL = float(os.getenv("ALLOWLIST_REMOVE_MAX_PNL", "0.0"))
ALERT_VERIFIED_BAD_MIN_TRADES = int(os.getenv("ALERT_VERIFIED_BAD_MIN_TRADES", "5"))
ALERT_VERIFIED_BAD_MAX_WIN_RATE = float(os.getenv("ALERT_VERIFIED_BAD_MAX_WIN_RATE", str(CITY_BLOCK_WIN_RATE)))
ALERT_ACTIVE_NOAA_MIN_CASES = int(os.getenv("ALERT_ACTIVE_NOAA_MIN_CASES", "3"))
ALERT_SHADOW_JOIN_MIN_SIGNALS = int(os.getenv("ALERT_SHADOW_JOIN_MIN_SIGNALS", "20"))
ALERT_SHADOW_JOIN_MIN_NOAA_SAMPLE = int(os.getenv("ALERT_SHADOW_JOIN_MIN_NOAA_SAMPLE", "10"))
ALERT_SHADOW_WR_MIN_RESOLVED = int(os.getenv("ALERT_SHADOW_WR_MIN_RESOLVED", "8"))
ALERT_SHADOW_WR_TARGET = float(os.getenv("ALERT_SHADOW_WR_TARGET", "45.0"))
SHADOW_DIRECTIONAL_HISTORY_LIMIT = int(os.getenv("SHADOW_DIRECTIONAL_HISTORY_LIMIT", "500"))
# v10.6.12: daily cross-check señales traders vs edge bot
# Número de corridas acumuladas antes de avisar "listo para análisis".
SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD = int(os.getenv("SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD", "7"))
# Hora UTC (0-23) a partir de la cual se envía el resumen diario.
# El daily se envía en el PRIMER ciclo del día cuya hora UTC >= este valor.
# Default 8 → ciclo 08:00 UTC = 9h España (CET/invierno) / 10h España (CEST/verano).
# Para 9h exactas en verano CEST añadir slot 7 a SCHEDULE_HOURS_UTC en Railway.
DAILY_SUMMARY_HOUR_UTC = int(os.getenv("DAILY_SUMMARY_HOUR_UTC", "8"))
SL_RETRO_ENABLED = os.getenv("SL_RETRO_ENABLED", "1").lower() in ("1", "true", "yes", "on")
DAILY_BRIEFING_ENABLED = os.getenv("DAILY_BRIEFING_ENABLED", "1").lower() in ("1", "true", "yes", "on")
DAILY_BRIEFING_HOUR_UTC = int(os.getenv("DAILY_BRIEFING_HOUR_UTC", "8"))
PNL_RECONCILIATION_ENABLED = os.getenv("PNL_RECONCILIATION_ENABLED", "1").lower() in ("1", "true", "yes", "on")
PNL_RECONCILIATION_HOUR_UTC = int(os.getenv("PNL_RECONCILIATION_HOUR_UTC", str(DAILY_BRIEFING_HOUR_UTC)))
WALLET_SNAPSHOT_ENABLED = os.getenv("WALLET_SNAPSHOT_ENABLED", "1").lower() in ("1", "true", "yes", "on")
WALLET_SNAPSHOT_HOUR_UTC = int(os.getenv("WALLET_SNAPSHOT_HOUR_UTC", str(PNL_RECONCILIATION_HOUR_UTC)))
WALLET_SNAPSHOT_TIMEOUT_SECONDS = int(os.getenv("WALLET_SNAPSHOT_TIMEOUT_SECONDS", "45"))
# v10.6.48: daily leaderboard P&L digest por Telegram. Hora UTC a partir de la cual se envía.
# Default 20 → primer ciclo >= 20:00 UTC = 22:00 España (CEST/verano). Para exactitud añadir
# 20 a SCHEDULE_HOURS_UTC en Railway. Sin ese slot el primer ciclo elegible es el de 23 UTC.
DAILY_DIGEST_ENABLED = os.getenv("DAILY_DIGEST_ENABLED", "1").lower() in ("1", "true", "yes", "on")
DAILY_DIGEST_HOUR_UTC = int(os.getenv("DAILY_DIGEST_HOUR_UTC", "20"))
DB_THROUGHPUT_DIGEST_ENABLED = os.getenv("DB_THROUGHPUT_DIGEST_ENABLED", "1").lower() in ("1", "true", "yes", "on")
UNSELLABLE_GUARD_MONITOR_ENABLED = os.getenv("UNSELLABLE_GUARD_MONITOR_ENABLED", "1").lower() in ("1", "true", "yes", "on")
UNSELLABLE_GUARD_MONITOR_HOUR_UTC = int(os.getenv("UNSELLABLE_GUARD_MONITOR_HOUR_UTC", str(PNL_RECONCILIATION_HOUR_UTC)))
UNSELLABLE_GUARD_MONITOR_TIMEOUT_SECONDS = int(os.getenv("UNSELLABLE_GUARD_MONITOR_TIMEOUT_SECONDS", "30"))
POST_INTRA_SL_COOLDOWN_REVIEW_ENABLED = os.getenv("POST_INTRA_SL_COOLDOWN_REVIEW_ENABLED", "1").lower() in ("1", "true", "yes", "on")
POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED = int(os.getenv("POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED", "10"))
# v10.6.42: SQLite Recorder (Fase 0) — default OFF hasta validación en Railway
SQLITE_RECORDER_ENABLED = os.getenv("SQLITE_RECORDER_ENABLED", "0").lower() in ("1", "true", "yes", "on")
# v10.6.43: Recorder Health Alerts (Fase 0.6) — default OFF, activar tras validación inicial
RECORDER_HEALTH_ALERTS_ENABLED = os.getenv("RECORDER_HEALTH_ALERTS_ENABLED", "0").lower() in ("1", "true", "yes", "on")
BANKROLL_SCALING_MONITOR_ENABLED = os.getenv("BANKROLL_SCALING_MONITOR_ENABLED", "1").lower() in ("1", "true", "yes", "on")
BANKROLL_SCALING_MONITOR_EVERY_CYCLES = int(os.getenv("BANKROLL_SCALING_MONITOR_EVERY_CYCLES", "6"))
BANKROLL_SCALING_MONITOR_ON_STATUS_CHANGE = os.getenv("BANKROLL_SCALING_MONITOR_ON_STATUS_CHANGE", "1").lower() in ("1", "true", "yes", "on")
BANKROLL_SCALING_MONITOR_TIMEOUT_SECONDS = int(os.getenv("BANKROLL_SCALING_MONITOR_TIMEOUT_SECONDS", "12"))
TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED = os.getenv("TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED", "true").lower() in ("1", "true", "yes", "on")
TRADERS_OPERATIONAL_INTELLIGENCE_TIMEOUT_SECONDS = int(os.getenv("TRADERS_OPERATIONAL_INTELLIGENCE_TIMEOUT_SECONDS", "180"))
SOURCE_ONBOARDING_ANDON_ENABLED = os.getenv("SOURCE_ONBOARDING_ANDON_ENABLED", "true").lower() in ("1", "true", "yes", "on")
SOURCE_ONBOARDING_ANDON_TIMEOUT_SECONDS = int(os.getenv("SOURCE_ONBOARDING_ANDON_TIMEOUT_SECONDS", "45"))
# Cutoff de stats por ciudad: "Dallas=2026-04-06,Chicago=2026-03-01"
# Trades cerrados ANTES de la fecha indicada se ignoran en get_city_accuracy().
CITY_STATS_CUTOFF: dict[str, str] = {}
for _city_stats_part in os.getenv("CITY_STATS_CUTOFF", "").split(","):
    _city_stats_part = _city_stats_part.strip()
    if "=" not in _city_stats_part:
        continue
    _city_stats_city, _city_stats_date = _city_stats_part.split("=", 1)
    _city_stats_city = _city_stats_city.strip()
    _city_stats_date = _city_stats_date.strip()
    if _city_stats_city and _city_stats_date:
        CITY_STATS_CUTOFF[_city_stats_city] = _city_stats_date

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
    for city in os.getenv(
        "BLOCKED_CITIES",
        # BLOCKED_CITIES = hard block de trading/admission.
        # Estas ciudades NO pueden abrir BUY ni como active, canary, auto_canary
        # ni por quality-trader gate. La observacion NOAA/shadow queda separada:
        # si existe proxy observado valido, pueden seguir acumulando forecast audit.
        #
        # Para "no operar pero sí observar/acumular NOAA":
        #   → No incluir en ACTIVE_TRADING_CITIES (quedan en shadow automáticamente).
        #   → Shadow = observa mercados, acumula observed_vs_forecast, no abre posiciones.
        #
        # Resumen de modos (ver AGENTS.md § Modos de ciudad):
        #   active  → opera + observa  (en ACTIVE_TRADING_CITIES)
        #   canary  → opera pequeño + observa  (en CANARY_TRADING_CITIES o auto_canary)
        #   shadow  → solo observa, no opera  (default si no está en ninguna lista)
        #   blocked → sin trading/admission  (en BLOCKED_CITIES o auto_blocked)
        "London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara"
    ).split(",")
    if city.strip()
}

ACTIVE_TRADING_CITIES = {
    city.strip()
    for city in os.getenv(
        "ACTIVE_TRADING_CITIES",
        "Chicago,Atlanta,Dallas,Buenos Aires"
    ).split(",")
    if city.strip()
}

CANARY_TRADING_CITIES = {
    city.strip()
    for city in os.getenv(
        "CANARY_TRADING_CITIES",
        ""
    ).split(",")
    if city.strip()
}
CANARY_POSITION_SCALE = float(os.getenv("CANARY_POSITION_SCALE", "0.50"))

ALLOWED_CONDITIONS = {
    condition.strip().lower()
    for condition in os.getenv(
        "ALLOWED_CONDITIONS",
        "at_or_above,at_or_below",
    ).split(",")
    if condition.strip()
}

# v10.6.15: Quality-trader-gated canary para exact/range
# Solo opera exact/range si: trader ∈ quality_traders AND ciudad ∈ whitelist AND edge ≥ MIN_EDGE+buffer
QUALITY_TRADER_CONDITIONS = {
    c.strip().lower()
    for c in os.getenv("QUALITY_TRADER_CONDITIONS", "exact,range").split(",")
    if c.strip()
}
QUALITY_TRADER_CITIES_WHITELIST = {
    c.strip()
    for c in os.getenv(
        "QUALITY_TRADER_CITIES_WHITELIST",
        "Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan,Atlanta,London,New York City,Munich,Ankara,Madrid,Miami,Paris,Wellington,Houston,Jakarta,Kuala Lumpur,Tel Aviv,Taipei,Singapore,Wuhan,Moscow,Amsterdam,Jeddah,Istanbul,Helsinki,Busan,Dallas",
    ).split(",")
    if c.strip()
}
MIN_EDGE_EXACT_RANGE_BUFFER_PP = float(os.getenv("MIN_EDGE_EXACT_RANGE_BUFFER_PP", "5.0"))
EXACT_RANGE_SIZE_SCALE = float(os.getenv("EXACT_RANGE_SIZE_SCALE", "0.50"))
EXACT_RANGE_MIN_AMOUNT = float(os.getenv("EXACT_RANGE_MIN_AMOUNT", "2.50"))

# OBSERVED_AUDIT-only cities that need explicit human review before canary.
# They can accumulate NOAA/proxy evidence, but auto_canary must not promote them.
AUTO_CANARY_REVIEW_REQUIRED_CITIES = {
    "Los Angeles": "manual_review_required_pre_canary",
}

UNSELLABLE_GUARD_ENABLED = os.getenv("UNSELLABLE_GUARD_ENABLED", "0").lower() in ("1", "true", "yes", "on")
UNSELLABLE_GUARD_LOG_ONLY = os.getenv("UNSELLABLE_GUARD_LOG_ONLY", "1").lower() in ("1", "true", "yes", "on")
UNSELLABLE_GUARD_VERSION = "unsellable_v1"
# v10.6.24: low-price buffer — posiciones especulativas (<LOW_PRICE_THRESHOLD) exigen más edge
# porque el ratio riesgo/recompensa es peor y el modelo es más sensible a errores en our_prob
MIN_EDGE_LOW_PRICE_BUFFER_PP = float(os.getenv("MIN_EDGE_LOW_PRICE_BUFFER_PP", "5.0"))
LOW_PRICE_THRESHOLD = float(os.getenv("LOW_PRICE_THRESHOLD", "0.35"))


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
    """Devuelve True si la ciudad esta bloqueada para trading/admission."""
    city = str(city or "").strip()
    if not city:
        return False
    return city.lower() in BLOCKED_CITIES


def _city_has_observed_proxy(city):
    """True si la ciudad tiene NOAA configurado y por tanto conviene seguir observándola."""
    city = str(city or "").strip()
    if not city:
        return False
    resolution_meta = RESOLUTION_ICAO.get(city, {}) if isinstance(globals().get("RESOLUTION_ICAO"), dict) else {}
    if city in OBSERVED_AUDIT_CITIES:
        return True
    return bool(
        resolution_meta.get("noaa_station_id")
        or resolution_meta.get("noaa_daily_station_id")
    )


def should_skip_observation(city):
    """True si una ciudad bloqueada no tiene proxy observado util para auditar."""
    city = str(city or "").strip()
    if not city:
        return False
    if not is_city_blocked(city):
        return False
    observed_proxy_helper = globals().get("_city_has_observed_proxy")
    has_observed_proxy = observed_proxy_helper(city) if callable(observed_proxy_helper) else False
    return not has_observed_proxy


def _city_requires_manual_proxy_canary_review(city):
    """True para ciudades observadas que no deben auto-promocionar sin revision."""
    city = str(city or "").strip()
    review_required = globals().get("AUTO_CANARY_REVIEW_REQUIRED_CITIES", {})
    if isinstance(review_required, dict) and city in review_required:
        return True
    if isinstance(review_required, (set, list, tuple)) and city in review_required:
        return True
    if not city or city not in OBSERVED_AUDIT_CITIES:
        return False
    resolution_meta = RESOLUTION_ICAO.get(city, {}) if isinstance(globals().get("RESOLUTION_ICAO"), dict) else {}
    return not bool(
        resolution_meta.get("noaa_station_id")
        or resolution_meta.get("noaa_daily_station_id")
    )


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

    # Caso 1: local_hour >= 24 → la ciudad ya está en el DA SIGUIENTE.
    # "Hoy" (fecha UTC) ya terminó completamente allí.
    # Con ZoneInfo no vemos 25 directamente; lo detectamos comparando fechas.
    # La temperatura de "hoy" (fecha UTC) ya se registró entera.
    if local_now.date() > datetime.now(timezone.utc).date():
        return 1

    # Caso 2: local_hour < 0 → la ciudad está aún en el DA ANTERIOR.
    # "Hoy" (fecha UTC) aún no empezó allí. El mercado para "hoy" es futuro.
    # Con ZoneInfo tampoco vemos negativos; si la fecha local va retrasada, sigue siendo 0.
    if local_now.date() < datetime.now(timezone.utc).date():
        return 0

    # Caso 3: hora local normal (0-23)
    if local_hour >= 14:
        return 1  # Temperatura máxima de hoy ya registrada en esta ciudad
    else:
        return 0  # Aún puede subir


def compute_city_windows():
    """
    Pre-computa el umbral min_days por ciudad para este ciclo.

    Reutiliza get_min_days_for_city() como source of truth para no divergir
    del override manual MIN_DAYS_AHEAD ni de la lógica per-city existente.
    Las ciudades fuera de CITY_TIMEZONES quedan fuera del dict a propósito:
    el prefilter es permisivo y el safety net sigue viviendo en PASO 2.
    """
    return {city: get_min_days_for_city(city) for city in CITY_TIMEZONES}

# v10.1: Gestión activa de posiciones
# Basado en investigación: Entire-Hood corta a -10%, toma a +17%
# Usamos umbrales un poco más amplios para nuestro bankroll pequeño
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))     # vender si PnL% < -25%
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))  # vender si PnL% > +40%
HIGH_CONVICTION_TP_PCT        = float(os.getenv("HIGH_CONVICTION_TP_PCT", "80.0"))         # TP elevado si our_prob >= umbral
HIGH_CONVICTION_PROB_THRESHOLD = float(os.getenv("HIGH_CONVICTION_PROB_THRESHOLD", "0.80")) # umbral de alta convicción
# v10.6.31: TP escalonado por precio + gate LOW+exact (Opus sesión 225, 2026-04-23)
HIGH_PRICE_THRESHOLD         = float(os.getenv("HIGH_PRICE_THRESHOLD", "0.65"))
TP_LOW_PRICE_PCT             = float(os.getenv("TP_LOW_PRICE_PCT", "60.0"))
TP_MID_PRICE_PCT             = float(os.getenv("TP_MID_PRICE_PCT", "40.0"))
TP_HIGH_PRICE_PCT            = float(os.getenv("TP_HIGH_PRICE_PCT", "80.0"))
BLOCK_LOW_EXACT_ENTRIES      = int(os.getenv("BLOCK_LOW_EXACT_ENTRIES", "1")) == 1
SELL_AGGRESSION = 0.02  # cuánto bajar el precio para asegurar venta rápida
INTRA_SL_INTERVAL = int(os.getenv("INTRA_SL_INTERVAL", "20"))  # v10.6.24: reactivado solo SL+TP (sin re-eval) — evita perder TPs entre ciclos
# v10.6.17: city-level SL cooldown — bloquea re-entrada en la misma ciudad tras stop-loss
SL_CITY_COOLDOWN_HOURS = int(os.getenv("SL_CITY_COOLDOWN_HOURS", "48"))
# v10.6.30: re-evaluación condicional intra-ciclo (shadow-log opt-in)
INTRA_REEVAL_ENABLED = int(os.getenv("INTRA_REEVAL_ENABLED", "0")) == 1        # master switch (default off)
INTRA_REEVAL_SHADOW_MODE = int(os.getenv("INTRA_REEVAL_SHADOW_MODE", "1")) == 1 # 1=solo loggea; 0=vende de verdad
INTRA_REEVAL_PRICE_DRIFT_PP = float(os.getenv("INTRA_REEVAL_PRICE_DRIFT_PP", "10.0"))  # pp mínimos de drift desde entry
INTRA_REEVAL_COOLDOWN_MIN = int(os.getenv("INTRA_REEVAL_COOLDOWN_MIN", "80"))   # minutos entre reevals de misma posición
INTRA_REEVAL_EDGE_THRESHOLD = float(os.getenv("INTRA_REEVAL_EDGE_THRESHOLD", "-3.0"))  # umbral de venta

# v10.6.40: guard SL_intra para condition=exact con resolución <=1 día (Opus, sesión 246, 2026-04-26).
# Evidencia 14d post-fix v10.6.28+: SL_intra n=10 WR=10% pnl=-$3.95. Patrón concentrado en exact+days<=1
# con edges enormes (>40%) y rebote intra-day; SL vende en suelo antes de la resolución.
# Si guard activo: para condition=exact y days_ahead<=SL_INTRA_GUARD_DAYS_AHEAD_MAX, NO se vende por SL_intra
# (TP_intra y SL del ciclo principal siguen activos). Cada skip se registra en sl_intra_guard_audit.json.
SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION = os.getenv("SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION", "1").lower() in ("1", "true", "yes", "on")
SL_INTRA_GUARD_DAYS_AHEAD_MAX = int(os.getenv("SL_INTRA_GUARD_DAYS_AHEAD_MAX", "1"))
SL_INTRA_GUARD_REVIEW_MIN_SKIPS = int(os.getenv("SL_INTRA_GUARD_REVIEW_MIN_SKIPS", "5"))
SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN = int(os.getenv("SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN", "60"))
SL_INTRA_GUARD_COHORT_SCHEMA_VERSION = "sl_intra_guard_cohort_v1"
SL_INTRA_GUARD_CATCHABLE_THRESHOLD_PCT = -35.0
SL_INTRA_GUARD_DEEP_DRAWDOWN_LOW_PCT = -75.0
SL_INTRA_GUARD_DEEP_DRAWDOWN_HIGH_PCT = -35.0
# SL_intra Hazard Monitor L2: observador puro bajo L1, LOG_ONLY y default OFF.
SL_INTRA_HAZARD_MONITOR_ENABLED = os.getenv("SL_INTRA_HAZARD_MONITOR_ENABLED", "0").lower() in ("1", "true", "yes", "on")
SL_INTRA_HAZARD_MONITOR_LOG_ONLY = os.getenv("SL_INTRA_HAZARD_MONITOR_LOG_ONLY", "1").lower() in ("1", "true", "yes", "on")
SL_INTRA_HAZARD_MONITOR_VERSION = "sl_intra_hazard_l2_v1"
SL_INTRA_HAZARD_DETERIORATING_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_DETERIORATING_PNL_PCT", "-50.0"))
SL_INTRA_HAZARD_DEEP_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_DEEP_PNL_PCT", "-70.0"))
SL_INTRA_HAZARD_TERMINAL_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_TERMINAL_PNL_PCT", "-85.0"))
SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE = float(os.getenv("SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE", "0.30"))
SL_INTRA_HAZARD_COLLAPSED_PRICE = float(os.getenv("SL_INTRA_HAZARD_COLLAPSED_PRICE", "0.05"))
SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES = int(os.getenv("SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES", "2"))
SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN = int(os.getenv("SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN", "60"))
SL_INTRA_HAZARD_MAX_EVENTS = int(os.getenv("SL_INTRA_HAZARD_MAX_EVENTS", "1000"))

MIN_PRICE = 0.20
MAX_PRICE = 0.80
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
ORDER_MIN_NOTIONAL = float(os.getenv("ORDER_MIN_NOTIONAL", "1.00"))


def effective_tp_pct(entry_price, our_prob=None):
    """v10.6.31: TP combinando conviccion (our_prob) y precio de entrada.

    Preserva la logica HIGH_CONVICTION existente y aniade floors por precio:
    - LOW (<LOW_PRICE_THRESHOLD): TP >= TP_LOW_PRICE_PCT (60%)
    - HIGH (>=HIGH_PRICE_THRESHOLD): TP >= TP_HIGH_PRICE_PCT (80%, unreachable, deja resolver)
    - MID: usa la logica base sin modificar
    """
    base = (
        HIGH_CONVICTION_TP_PCT
        if our_prob is not None and our_prob >= HIGH_CONVICTION_PROB_THRESHOLD
        else TAKE_PROFIT_PCT
    )
    if entry_price is not None and entry_price < LOW_PRICE_THRESHOLD:
        return max(base, TP_LOW_PRICE_PCT)
    if entry_price is not None and entry_price >= HIGH_PRICE_THRESHOLD:
        return max(base, TP_HIGH_PRICE_PCT)
    return base


def _parse_schedule_hours_utc(raw):
    hours = []
    seen = set()
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError:
            continue
        if 0 <= hour <= 23 and hour not in seen:
            seen.add(hour)
            hours.append(hour)
    return sorted(hours)

SCHEDULE_HOURS_UTC_STR = os.getenv("SCHEDULE_HOURS_UTC", "8,16,23")
SCHEDULE_DISABLED_HOURS_UTC_STR = os.getenv("SCHEDULE_DISABLED_HOURS_UTC", "").strip()
_SCHEDULE_HOURS_BASE = _parse_schedule_hours_utc(SCHEDULE_HOURS_UTC_STR) or [8, 16, 23]
_SCHEDULE_HOURS_DISABLED = set(_parse_schedule_hours_utc(SCHEDULE_DISABLED_HOURS_UTC_STR))
SCHEDULE_HOURS_UTC = [hour for hour in _SCHEDULE_HOURS_BASE if hour not in _SCHEDULE_HOURS_DISABLED] or list(_SCHEDULE_HOURS_BASE)

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


def _sync_agent_events_seed():
    """
    Combina agent_events.jsonl local (semilla del repo) con el del Volume (producción).
    - Si el Volume aún no tiene el archivo, copia la semilla completa.
    - Si ya existe, añade solo los eventos del repo local que no están en el Volume,
      identificados por (timestamp, agent, title). Nunca borra eventos ya persistidos.
    Necesario para que nuevas sesiones añadidas al repo aparezcan en el scoreboard
    sin esperar a que se elimine el archivo del Volume manualmente.
    """
    target = _data_path("agent_events.jsonl")
    source = "agent_events.jsonl"

    if not os.path.exists(source):
        return target

    if DATA_DIR and not os.path.exists(target):
        try:
            shutil.copy2(source, target)
        except Exception:
            pass
        return target

    if not DATA_DIR:
        return target

    try:
        def _load_jsonl_events(path):
            events = []
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            pass
            return events

        target_events = _load_jsonl_events(target)
        source_events = _load_jsonl_events(source)

        existing_keys = {
            (e.get("timestamp", ""), e.get("agent", ""), e.get("title", ""))
            for e in target_events
        }
        new_events = [
            e for e in source_events
            if (e.get("timestamp", ""), e.get("agent", ""), e.get("title", ""))
            not in existing_keys
        ]

        if new_events:
            with open(target, "a", encoding="utf-8") as fh:
                for e in new_events:
                    fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    except Exception as exc:
        logging.getLogger(__name__).warning(f"agent_events sync failed: {exc}")

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
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", _data_path("polymarket.db"))
PHASE1_READINESS_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "phase1_readiness_check.py",
)
BANKROLL_SCALING_CHECK_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "bankroll_scaling_check.py",
)
WALLET_SNAPSHOT_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "wallet_snapshot.py",
)
UNSELLABLE_GUARD_MONITOR_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "unsellable_guard_monitor.py",
)
CYCLES_HISTORY_FILE = _data_path("cycles_history.jsonl")
FUNNEL_OBSERVABILITY_LOG_ONLY_FILE = _data_path("funnel_observability_log_only.jsonl")
FUNNEL_OBSERVABILITY_LATEST_FILE = _data_path("funnel_observability_latest.json")
POSTMORTEM_FILE = _data_path("postmortem.json")
TRADE_LIFECYCLE_FILE = _data_path("trade_lifecycle.json")
ALERTS_FILE = _data_path("alerts_state.json")
SHADOW_TRACKING_FILE = _data_path("shadow_city_tracking.json")
CITY_POLICY_FILE = _data_path("city_policy_state.json")
SOURCE_ONBOARDING_FILE = _data_path("source_onboarding.json")
SKIP_LOG_FILE = _data_path("skip_log.jsonl")
SKIP_LOG_MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — rotación del contrato R3
SL_COOLDOWN_FILE = _data_path("sl_city_cooldown.json")
INTRA_REEVAL_STATE_FILE = _data_path("intra_reeval_state.json")
SL_INTRA_GUARD_STATE_FILE = _data_path("sl_intra_guard_audit.json")
SL_INTRA_HAZARD_MONITOR_STATE_FILE = _data_path("sl_intra_hazard_monitor_audit.json")
AGENT_EVENTS_FILE = _sync_agent_events_seed()
SIGNALS_FILE = _seed_data_file("signals.json")
SIGNALS_CROSSCHECK_FILE = _data_path("signals_crosscheck.jsonl")
SIGNALS_CROSSCHECK_DAILY_SUMMARY_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "signals_crosscheck_daily_summary.py",
)
TRADERS_INTELLIGENCE_REPORT_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "traders_intelligence_report.py",
)
TRADERS_INTELLIGENCE_DAILY_SUMMARY_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "traders_intelligence_daily_summary.py",
)
TRADERS_INTELLIGENCE_COLLECTOR_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "traders_intelligence_collector.py",
)
TRADERS_OPERATIONAL_INTELLIGENCE_MONITOR_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "traders_operational_intelligence_monitor.py",
)
SOURCE_ONBOARDING_ANDON_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "source_onboarding_andon.py",
)
SL_RETROSPECTIVE_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "sl_retrospective.py",
)
DAILY_POSITION_BRIEFING_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "daily_position_briefing.py",
)
PNL_RECONCILIATION_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "pnl_reconciliation_alert.py",
)
SL_RETROSPECTIVE_STATE_FILE = _data_path("sl_retrospective_state.json")
DAILY_BRIEFING_STATE_FILE = _data_path("daily_briefing_state.json")
PNL_RECONCILIATION_STATE_FILE = _data_path("pnl_reconciliation_state.json")
DAILY_DIGEST_STATE_FILE = _data_path("daily_digest_state.json")
DAILY_DIGEST_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "daily_bot_observability_run.py",
)
CITY_INTELLIGENCE_RUNTIME_EXPORT_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "runtime_import_local_export.py",
)
CITY_INTELLIGENCE_EFFECTIVE_VIEW_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "runtime_policy_effective_view.py",
)
CITY_INTELLIGENCE_PIPELINE_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "city_intelligence_pipeline.py",
)
CITY_INTELLIGENCE_ALIGNMENT_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "system_alignment_check.py",
)
CITY_INTELLIGENCE_DAILY_SUMMARY_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "city_intelligence_daily_summary.py",
)
TRADERS_INTELLIGENCE_ENABLED = os.getenv("TRADERS_INTELLIGENCE_ENABLED", "true").lower() in ("1", "true", "yes", "on")
TRADERS_INTELLIGENCE_HOUR_UTC = int(os.getenv("TRADERS_INTELLIGENCE_HOUR_UTC", "8"))
TRADERS_INTELLIGENCE_COLLECTOR_ENABLED = os.getenv("TRADERS_INTELLIGENCE_COLLECTOR", "OFF").lower() in ("1", "true", "yes", "on")
CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED = os.getenv("CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED", "true").lower() in ("1", "true", "yes", "on")
CITY_INTELLIGENCE_RUNTIME_BRIDGE_HOUR_UTC = int(os.getenv("CITY_INTELLIGENCE_RUNTIME_BRIDGE_HOUR_UTC", "7"))
BLOCKED_SIGNALS_FILE = _data_path("blocked_signals_resolutions.jsonl")
BOT_SIGNAL_EVALUATIONS_FILE = _data_path("bot_signal_evaluations.jsonl")
EXACT_NO_QT_MATCH_EVAL_FILE = _data_path("exact_no_qt_match_evaluations_log_only.jsonl")
TRADERS_DB_FILE = _seed_data_file("traders_db.json")
LIFECYCLE_REVIEW_JSON_FILE = _data_path("city_lifecycle_review.json")
LIFECYCLE_REVIEW_COOLDOWN_HOURS = 24
_LIFECYCLE_MONITOR_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "city_lifecycle_review_monitor.py",
)
_LIFECYCLE_REVIEW_ALERT_TRANSITIONS = {
    "manual_review_pending",
    "active_review",
    "silent_promotion_detected",
}


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


# =============================================================
# SKIP LOG (R3) — log append-only de skips por ciudad por ciclo
# Ver docs/control-center-r3-contract.md
# =============================================================

SKIP_LOG_REQUIRED_FIELDS = ("ts_utc", "cycle_id", "skip_reason", "extras")

SKIP_REASONS_VALID = frozenset({
    # Grupo A — datos ricos (edge calculado en Loop B)
    "no_edge",
    "below_min_edge",
    "kelly_too_low",
    "shadow_only_override",
    "fuera_allowlist",
    "existing_order",
    "sold_this_cycle",
    "sl_city_cooldown",
    "existing_position",
    "low_exact_gap_risk",
    "unsellable_guard_candidate",
    "unsellable_liquidity_guard",
    # Grupo B — datos parciales (Loop A, pre-edge)
    "blocked_city",
    "timezone_filter",
    "date_out_of_range_past",
    "date_out_of_range_future",
    "price_out_of_range",
    "liquidity_low",
    "forecast_missing",
    "condition_filtered",
    # Grupo C — parse fail
    "parse_fail",
})


def _unsellable_guard_match_zone_bucket(price_at_guard):
    try:
        price = float(price_at_guard)
    except (TypeError, ValueError):
        return "unknown"
    if price < 0.10:
        return "below_0_10"
    if price <= 0.35:
        return "0_10_to_0_35"
    if price <= 0.65:
        return "0_35_to_0_65"
    return "above_0_65"


def _unsellable_guard_decision(
    *,
    enabled,
    log_only,
    condition,
    days_ahead,
    price_at_guard,
    amount,
    effective_bankroll,
):
    try:
        bankroll = float(effective_bankroll)
        amount_value = float(amount)
        price_value = float(price_at_guard)
        days_value = int(days_ahead)
    except (TypeError, ValueError):
        return {"active": False, "triggered": False, "size_ratio": None}

    if not enabled or bankroll <= 0:
        return {"active": False, "triggered": False, "size_ratio": None}

    size_ratio = amount_value / bankroll
    triggered = (
        str(condition or "").lower() in {"exact", "range"}
        and days_value == 0
        and 0.10 <= price_value <= 0.65
        and size_ratio >= 0.15
    )
    return {
        "active": True,
        "triggered": triggered,
        "size_ratio": size_ratio,
        "guard_action": "would_skip" if log_only else "skipped",
        "skip_reason": "unsellable_guard_candidate" if log_only else "unsellable_liquidity_guard",
        "match_zone_bucket": _unsellable_guard_match_zone_bucket(price_value),
    }


def _make_skip_entry(
    reason,
    *,
    cycle_id,
    ts_utc=None,
    city=None,
    date_iso=None,
    side=None,
    city_mode=None,
    allowlisted=None,
    days_ahead=None,
    edge_pct=None,
    our_prob=None,
    mkt_prob=None,
    min_edge=None,
    forecast_max=None,
    threshold=None,
    threshold_high=None,
    unit=None,
    condition=None,
    sigma_used=None,
    question=None,
    extras=None,
):
    """Construye un dict de skip_log entry según el contrato R3.

    reason: valor del enum SKIP_REASONS_VALID.
    cycle_id: string determinista "YYYY-MM-DDTHH:MM" UTC (compartido por todas las filas del ciclo).
    ts_utc: ISO 8601 tz-aware UTC. Si None, usa datetime.now(timezone.utc).isoformat().
    Los demás campos son opcionales según el grupo del skip (A/B/C).
    """
    return {
        "ts_utc": ts_utc or datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "city": city,
        "date_iso": date_iso,
        "side": side,
        "skip_reason": reason,
        "city_mode": city_mode,
        "allowlisted": allowlisted,
        "days_ahead": days_ahead,
        "edge_pct": edge_pct,
        "our_prob": our_prob,
        "mkt_prob": mkt_prob,
        "min_edge": min_edge,
        "forecast_max": forecast_max,
        "threshold": threshold,
        "threshold_high": threshold_high,
        "unit": unit,
        "condition": condition,
        "sigma_used": sigma_used,
        "question": question,
        "extras": extras if extras is not None else {},
    }


def _bot_eval_capture_disabled():
    return os.getenv("DISABLE_BOT_EVAL_CAPTURE", "").strip().lower() in {"1", "true", "yes", "on"}


def _bot_eval_read_enabled():
    return os.getenv("READ_BOT_EVAL_CAPTURE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _build_bot_eval_key(city, date_iso, condition, threshold, threshold_high=None, unit=None):
    if not city or not date_iso or not condition or threshold is None or not unit:
        return None
    temp_part = f"{threshold}-{threshold_high}" if threshold_high is not None else str(threshold)
    return f"{city}|{date_iso}|{condition}|{temp_part}|{unit}"


def _funnel_market_identifier(market):
    """Stable LOG_ONLY market id; never used for trading authorization."""
    if not isinstance(market, dict):
        return None
    for key in ("condition_id", "conditionId", "market_id", "id", "marketId", "market_slug", "slug"):
        value = market.get(key)
        if value is not None and str(value).strip():
            if key in {"condition_id", "conditionId"}:
                return f"condition_id:{str(value).strip()}"
            if key in {"market_slug", "slug"}:
                return f"market_slug:{str(value).strip()}"
            return f"market_id:{str(value).strip()}"

    question = str(market.get("question") or "").strip()
    parsed = parse_temperature_question(question) if question else None
    if not parsed:
        return f"fallback:|||||||{question}" if question else None
    date_iso = date_text_to_iso(parsed.get("date_str", "")) or parsed.get("date_str", "")
    parts = [
        parsed.get("city", ""),
        date_iso,
        parsed.get("condition", ""),
        parsed.get("temp_threshold", ""),
        parsed.get("temp_threshold_high", ""),
        parsed.get("unit", ""),
        question,
    ]
    return "fallback:" + "|".join(str(part) for part in parts)


def count_discovered_markets_unique(markets):
    """
    Count unique discovered markets before filters.
    LOG_ONLY metrics only: this does not authorize trading and is not read by
    BUY/SELL/SKIP decisions.
    """
    if markets is None:
        return None
    seen = set()
    for market in markets:
        identifier = _funnel_market_identifier(market)
        if identifier:
            seen.add(identifier)
    return len(seen)


def _safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def _funnel_reason_count(reason_counts, *names):
    if not isinstance(reason_counts, dict):
        return 0
    return sum(_safe_int(reason_counts.get(name)) for name in names)


def build_funnel_observability_record(cycle_data, discovered_markets_unique=None):
    """
    Build the per-cycle funnel artifact.
    LOG_ONLY / NO_ACTION: metrics only, no trading authorization, and no impact
    on BUY/SELL/SKIP, sizing, city modes, scheduler, filters, or guards.
    """
    cycle_data = cycle_data if isinstance(cycle_data, dict) else {}
    scan = cycle_data.get("scan", {}) if isinstance(cycle_data.get("scan"), dict) else {}
    slot_metrics = scan.get("slot_metrics", {}) if isinstance(scan.get("slot_metrics"), dict) else {}
    reject_reasons = slot_metrics.get("reject_reasons", {})
    execution_rejects = slot_metrics.get("execution_reject_reasons", {})
    if not isinstance(reject_reasons, dict):
        reject_reasons = {}
    if not isinstance(execution_rejects, dict):
        execution_rejects = {}

    policy_source_blocked = {
        "fuera_allowlist": _funnel_reason_count(reject_reasons, "fuera_allowlist"),
        "blocked_city": _funnel_reason_count(reject_reasons, "blocked_city"),
        "settlement_risk": _funnel_reason_count(reject_reasons, "settlement_risk"),
        "shadow_only_mode": _funnel_reason_count(reject_reasons, "shadow_only_override", "shadow_only_mode"),
    }
    policy_source_blocked["total"] = sum(policy_source_blocked.values())

    date_past = _funnel_reason_count(reject_reasons, "date_out_of_range_past")
    date_future = _funnel_reason_count(reject_reasons, "date_out_of_range_future")
    discovered_is_known = discovered_markets_unique is not None

    return {
        "schema_version": 1,
        "ts_utc": cycle_data.get("timestamp_utc") or datetime.now(timezone.utc).isoformat(),
        "cycle_number": cycle_data.get("cycle_number"),
        "logic_cycle_number": cycle_data.get("logic_cycle_number"),
        "logic_series": cycle_data.get("logic_series"),
        "version": cycle_data.get("version"),
        "mode": cycle_data.get("mode"),
        "log_only": True,
        "trading_authorization": "NO_ACTION",
        "discovered_markets_unique": _safe_int(discovered_markets_unique) if discovered_is_known else None,
        "prefiltered": _safe_int(scan.get("markets_evaluated")),
        "markets_evaluated": _safe_int(scan.get("markets_evaluated")),
        "city_window_skipped": _safe_int(scan.get("city_window_skipped")),
        "price_out_of_range": _funnel_reason_count(reject_reasons, "price_out_of_range"),
        "date_out_of_range_past": date_past,
        "date_out_of_range_future": date_future,
        "date_out_of_range": {"past": date_past, "future": date_future},
        "condition_filtered": _safe_int(scan.get("condition_filtered")) or _funnel_reason_count(reject_reasons, "condition_filtered"),
        "policy_source_blocked": policy_source_blocked,
        "edge": _safe_int(scan.get("with_edge")),
        "with_edge": _safe_int(scan.get("with_edge")),
        "shadow_edge": _safe_int(scan.get("shadow")),
        "shadow": _safe_int(scan.get("shadow")),
        "selected": _safe_int(scan.get("selected")),
        "real_buy": len(cycle_data.get("buys", []) if isinstance(cycle_data.get("buys"), list) else []),
        "execution_rejects": dict(execution_rejects),
        "baseline_partial": not discovered_is_known,
        "reject_reasons": dict(reject_reasons),
    }


def write_exact_no_qt_match_evals(batch, jsonl_path=None, cap_per_cycle=20):
    """
    Best-effort writer for exact/no-QT-match LOG_ONLY evaluations.
    Deduplicates by eval_key, applies SHA-256 stable cap if needed. Fail-open.
    """
    if not batch:
        return
    jsonl_path = jsonl_path or EXACT_NO_QT_MATCH_EVAL_FILE
    # Dedup by eval_key within the cycle (keep first occurrence)
    seen: set = set()
    deduped = []
    for r in batch:
        k = r.get("eval_key")
        if k not in seen:
            seen.add(k)
            deduped.append(r)
    eligible_before_cap = len(deduped)
    if eligible_before_cap <= cap_per_cycle:
        selected = list(deduped)
        cap_active = False
        sampling_method = "none"
        capped_count = 0
    else:
        def _sha_rank(r):
            return hashlib.sha256(
                f"{r.get('cycle_id', '')}|{r.get('eval_key', '')}".encode("utf-8")
            ).hexdigest()
        selected = sorted(deduped, key=_sha_rank)[:cap_per_cycle]
        cap_active = True
        sampling_method = "sha256_rank"
        capped_count = eligible_before_cap - cap_per_cycle
    selected_after_cap = len(selected)
    for r in selected:
        r["capture_meta"] = {
            "sampled": cap_active,
            "cap_active": cap_active,
            "sampling_method": sampling_method,
            "stable_rank": hashlib.sha256(
                f"{r.get('cycle_id', '')}|{r.get('eval_key', '')}".encode("utf-8")
            ).hexdigest() if cap_active else None,
            "cap_per_cycle": cap_per_cycle,
            "eligible_before_cap": eligible_before_cap,
            "selected_after_cap": selected_after_cap,
            "capped_count": capped_count,
        }
    try:
        target_dir = os.path.dirname(jsonl_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(jsonl_path, "a", encoding="utf-8") as fh:
            for r in selected:
                fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        log.info(
            f"[exact_no_qt_eval] eligible_before_cap={eligible_before_cap} "
            f"selected_after_cap={selected_after_cap} capped_count={capped_count} "
            f"sampling_method={sampling_method} cap_per_cycle={cap_per_cycle}"
        )
    except Exception as _e:
        log.warning(f"exact_no_qt_match_eval write failed (LOG_ONLY, no trading impact): {_e}")


def write_funnel_observability_log_only(record, jsonl_path=None, latest_path=None):
    """
    Best-effort writer for funnel observability.
    NO_ACTION metrics only: write failures are warnings and never affect trading.
    """
    if not isinstance(record, dict):
        return False
    jsonl_path = jsonl_path or FUNNEL_OBSERVABILITY_LOG_ONLY_FILE
    latest_path = latest_path or FUNNEL_OBSERVABILITY_LATEST_FILE
    try:
        target_dir = os.path.dirname(jsonl_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        latest_dir = os.path.dirname(latest_path)
        if latest_dir:
            os.makedirs(latest_dir, exist_ok=True)
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        log.warning(f"funnel observability LOG_ONLY write failed (NO_ACTION metrics only): {e}")
        return False


def record_bot_evaluation(cycle_id, eval_key, would_buy: bool, **fields):
    """
    LOG_ONLY append-only capture of the bot's live evaluation outcome.
    Best-effort by design: failures never affect trading or cycle control flow.
    """
    if _bot_eval_capture_disabled() or not eval_key:
        return False
    try:
        record = {
            "schema_version": 1,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "cycle_id": cycle_id,
            "eval_key": eval_key,
            "city": fields.get("city"),
            "date_iso": fields.get("date_iso"),
            "condition": fields.get("condition"),
            "threshold": fields.get("threshold"),
            "threshold_high": fields.get("threshold_high"),
            "unit": fields.get("unit"),
            "would_buy": bool(would_buy),
            "bot_edge_pct_at_signal": fields.get("bot_edge_pct_at_signal", fields.get("edge_pct")),
            "evaluation_source": "live_eval",
            "skip_or_block_reason": fields.get("skip_or_block_reason"),
            "decision_gate": fields.get("decision_gate"),
            "decision_confidence": fields.get("decision_confidence"),
            "our_prob": fields.get("our_prob"),
            "mkt_prob": fields.get("mkt_prob"),
            "forecast_max": fields.get("forecast_max"),
            "sigma_used": fields.get("sigma_used"),
            "days_ahead": fields.get("days_ahead"),
        }
        target_dir = os.path.dirname(BOT_SIGNAL_EVALUATIONS_FILE)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(BOT_SIGNAL_EVALUATIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except Exception:
        return False


def _load_bot_evaluation_index():
    index = {}
    if not _bot_eval_read_enabled():
        return index
    try:
        if not os.path.exists(BOT_SIGNAL_EVALUATIONS_FILE):
            return index
        with open(BOT_SIGNAL_EVALUATIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                eval_key = rec.get("eval_key")
                if eval_key:
                    index[eval_key] = rec
    except Exception:
        return {}
    return index


def _bot_eval_join_fields(signal: dict) -> dict:
    try:
        eval_key = (
            signal.get("eval_key")
            or signal.get("match_key")
            or _build_bot_eval_key(
                signal.get("city"),
                signal.get("date") or signal.get("date_iso"),
                signal.get("condition"),
                signal.get("temp") if signal.get("temp") is not None else signal.get("threshold"),
                signal.get("temp_high") if signal.get("temp_high") is not None else signal.get("threshold_high"),
                signal.get("unit"),
            )
        )
        rec = _load_bot_evaluation_index().get(eval_key)
        if not rec:
            return {
                "bot_would_have_bought": False,
                "bot_evaluation_source": "unknown",
                "bot_evaluation_join_status": "missing",
            }
        return {
            "bot_would_have_bought": bool(rec.get("would_buy")),
            "bot_evaluation_source": "live_eval",
            "bot_edge_pct_at_signal": rec.get("bot_edge_pct_at_signal"),
            "bot_skip_or_block_reason": rec.get("skip_or_block_reason"),
            "bot_decision_gate": rec.get("decision_gate"),
            "bot_decision_confidence": rec.get("decision_confidence"),
            "bot_evaluation_join_status": "captured",
        }
    except Exception:
        return {
            "bot_would_have_bought": False,
            "bot_evaluation_source": "unknown",
            "bot_evaluation_join_status": "missing",
        }


def _record_bot_evaluation_from_skip_entry(entry):
    try:
        extras = entry.get("extras") if isinstance(entry.get("extras"), dict) else {}
        skip_reason = entry.get("skip_reason")
        decision_gate = "shadow_only" if skip_reason == "shadow_only_override" else skip_reason
        eval_key = extras.get("qt_match_key") or _build_bot_eval_key(
            entry.get("city"),
            entry.get("date_iso"),
            entry.get("condition"),
            entry.get("threshold"),
            entry.get("threshold_high"),
            entry.get("unit"),
        )
        return record_bot_evaluation(
            entry.get("cycle_id"),
            eval_key,
            False,
            city=entry.get("city"),
            date_iso=entry.get("date_iso"),
            condition=entry.get("condition"),
            threshold=entry.get("threshold"),
            threshold_high=entry.get("threshold_high"),
            unit=entry.get("unit"),
            edge_pct=entry.get("edge_pct"),
            skip_or_block_reason=skip_reason,
            decision_gate=decision_gate,
            decision_confidence=entry.get("our_prob"),
            our_prob=entry.get("our_prob"),
            mkt_prob=entry.get("mkt_prob"),
            forecast_max=entry.get("forecast_max"),
            sigma_used=entry.get("sigma_used"),
            days_ahead=entry.get("days_ahead"),
        )
    except Exception:
        return False


def _sl_cooldown_register(city: str, hours: int = None) -> None:
    """Registra city en cooldown post-SL. Bloquea re-entrada por SL_CITY_COOLDOWN_HOURS."""
    if not city:
        return
    h = hours if hours is not None else int(globals().get("SL_CITY_COOLDOWN_HOURS", 48) or 48)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=h)
    try:
        try:
            with open(SL_COOLDOWN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data[city] = {
            "triggered_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "cooldown_hours": h,
        }
        with open(SL_COOLDOWN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        log.warning(f"sl_cooldown_register error ({city}): {e}")


def _sl_cooldown_check(city: str) -> bool:
    """Devuelve True si la ciudad está en cooldown post-SL (no debe comprar)."""
    if not city:
        return False
    try:
        with open(SL_COOLDOWN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        entry = data.get(city)
        if not entry:
            return False
        expires = datetime.fromisoformat(entry["expires_at"])
        return datetime.now(timezone.utc) < expires
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    except Exception as e:
        log.warning(f"sl_cooldown_check error ({city}): {e}")
        return False


def _skip_log_rotate_if_needed(path=None, max_size=None):
    """Rota skip_log.jsonl → skip_log.YYYY-MM-DD.jsonl si supera max_size. No lanza."""
    target = path if path is not None else SKIP_LOG_FILE
    limit = max_size if max_size is not None else SKIP_LOG_MAX_SIZE_BYTES
    try:
        if not os.path.exists(target):
            return
        if os.path.getsize(target) < limit:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if target.endswith(".jsonl"):
            rotated = target[:-len(".jsonl")] + f".{stamp}.jsonl"
        else:
            rotated = target + f".{stamp}"
        if os.path.exists(rotated):
            i = 1
            candidate = rotated[:-len(".jsonl")] + f".{i}.jsonl"
            while os.path.exists(candidate):
                i += 1
                candidate = rotated[:-len(".jsonl")] + f".{i}.jsonl"
            rotated = candidate
        os.replace(target, rotated)
    except Exception as e:
        try:
            log.warning(f"skip_log rotate fallo: {e}")
        except Exception:
            pass


def append_skip_log_entries(entries, path=None, max_size=None):
    """Append batch de skip entries a data/skip_log.jsonl.

    - entries: lista de dicts ya construidos con _make_skip_entry.
    - No-op si entries vacío.
    - Fail-fast (ValueError) si un entry no tiene los campos obligatorios del contrato.
    - NUNCA propaga excepciones de I/O al caller — solo warning.
    - Rota el archivo ANTES de escribir si supera max_size.
    """
    if not entries:
        return
    for e in entries:
        for field in SKIP_LOG_REQUIRED_FIELDS:
            if field not in e:
                raise ValueError(f"skip_log entry missing required field: {field}")

    target = path if path is not None else SKIP_LOG_FILE
    try:
        _skip_log_rotate_if_needed(target, max_size)
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = "".join(
            json.dumps(e, ensure_ascii=False, default=str) + "\n" for e in entries
        )
        with open(target, "a", encoding="utf-8") as f:
            f.write(payload)
    except Exception as e:
        try:
            log.warning(f"skip_log append fallo: {e}")
        except Exception:
            pass


def _skip_log_rotated_files(base=None):
    """Lista de archivos rotados skip_log.*.jsonl (excluye el activo), ordenados desc."""
    target = base if base is not None else SKIP_LOG_FILE
    directory = os.path.dirname(target) or "."
    basename = os.path.basename(target)
    if not basename.endswith(".jsonl"):
        return []
    prefix = basename[: -len(".jsonl")] + "."  # "skip_log."
    try:
        files = []
        for name in os.listdir(directory):
            if name == basename:
                continue
            if name.startswith(prefix) and name.endswith(".jsonl"):
                files.append(os.path.join(directory, name))
        files.sort(reverse=True)
        return files
    except Exception:
        return []


def read_skip_log_last_n_cycles(n, path=None):
    """Devuelve todas las filas de los últimos N cycle_id distintos.

    Lee el archivo activo y los rotados (del más reciente al más viejo), tolera
    líneas malformadas con warning.
    """
    if n <= 0:
        return []
    target = path if path is not None else SKIP_LOG_FILE
    files = [target] + _skip_log_rotated_files(target)
    seen_cycles = []
    collected = []
    for fpath in files:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            try:
                log.warning(f"skip_log read fallo en {fpath}: {e}")
            except Exception:
                pass
            continue
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                try:
                    log.warning(f"skip_log linea malformada en {fpath}")
                except Exception:
                    pass
                continue
            cid = obj.get("cycle_id")
            if cid is None:
                continue
            if cid not in seen_cycles:
                if len(seen_cycles) >= n:
                    return collected
                seen_cycles.append(cid)
            collected.append(obj)
    return collected


def read_skip_log_since(ts_utc_iso, path=None):
    """Devuelve todas las filas con ts_utc >= ts_utc_iso (archivo activo + rotados)."""
    target = path if path is not None else SKIP_LOG_FILE
    files = [target] + _skip_log_rotated_files(target)
    out = []
    for fpath in files:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                    except Exception:
                        continue
                    ts = obj.get("ts_utc")
                    if ts and ts >= ts_utc_iso:
                        out.append(obj)
        except Exception as e:
            try:
                log.warning(f"skip_log read_since fallo en {fpath}: {e}")
            except Exception:
                pass
    return out


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
        # v10.6: alerta de bankroll bajo
        "low_bankroll_alerted": False,
        # v10.6.11 (M4): resumen diario Telegram — fecha UTC del último envío (YYYY-MM-DD)
        "daily_summary_last_sent": None,
        "slot_monetization_last_date": None,
        "slot_monetization_last_signature": None,
        # v10.6.11 (M5): ciudades ya notificadas como candidatas a canary (one-shot por ciudad)
        "canary_candidate_notified": {},
        # v10.6.30: revisión one-shot intra-reeval shadow (7 días tras primer trigger)
        "intra_reeval_review_alert_sent": False,
        "post_intra_sl_cooldown_review": {},
        # v10.6.37: auto-close de posiciones expiradas sin evidencia (daily)
        "legacy_cleanup_last_run": None,
        # v10.6.43: Recorder Health Alerts — fecha YYYY-MM-DD del último stale alert
        "recorder_stale_last_alert_date": None,
        "bankroll_scaling_last_status": None,
        "bankroll_scaling_last_target_tier": None,
        "bankroll_scaling_last_digest_date": None,
        "bankroll_scaling_last_blockers_hash": None,
        "bankroll_scaling_last_alert_cycle": 0,
        "bankroll_scaling_last_eligible_for_manual_review": False,
        "wallet_snapshot_last_run_date": None,
        "wallet_snapshot_last_phase2_ready": False,
        "wallet_snapshot_last_ready_reason": None,
        "wallet_snapshot_last_valid_snapshot_days": 0,
        "wallet_snapshot_last_valid_snapshot_at": None,
        "wallet_snapshot_last_error_date": None,
        "wallet_snapshot_phase2_ready_alert_sent": False,
        "unsellable_guard_monitor_last_run_date": None,
        "unsellable_guard_last_status": None,
        "unsellable_guard_candidate_total": 0,
        "unsellable_guard_first_candidate_at": None,
        "unsellable_guard_last_candidate_at": None,
        "unsellable_guard_last_alert_date": None,
        "unsellable_guard_action_review_sent": False,
        "unsellable_guard_safety_alert_sent": False,
        "unsellable_guard_safety_last_seen_at": None,
        "lifecycle_review_last_run_date": None,
        "lifecycle_review_alerted": {},
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
        state.setdefault("low_bankroll_alerted", False)
        state.setdefault("daily_summary_last_sent", None)
        state.setdefault("slot_monetization_last_date", None)
        state.setdefault("slot_monetization_last_signature", None)
        state.setdefault("canary_candidate_notified", {})
        state.setdefault("intra_reeval_review_alert_sent", False)
        state.setdefault("post_intra_sl_cooldown_review", {})
        state.setdefault("legacy_cleanup_last_run", None)
        state.setdefault("bankroll_scaling_last_status", None)
        state.setdefault("bankroll_scaling_last_target_tier", None)
        state.setdefault("bankroll_scaling_last_digest_date", None)
        state.setdefault("bankroll_scaling_last_blockers_hash", None)
        state.setdefault("bankroll_scaling_last_alert_cycle", 0)
        state.setdefault("bankroll_scaling_last_eligible_for_manual_review", False)
        state.setdefault("wallet_snapshot_last_run_date", None)
        state.setdefault("wallet_snapshot_last_phase2_ready", False)
        state.setdefault("wallet_snapshot_last_ready_reason", None)
        state.setdefault("wallet_snapshot_last_valid_snapshot_days", 0)
        state.setdefault("wallet_snapshot_last_valid_snapshot_at", None)
        state.setdefault("wallet_snapshot_last_error_date", None)
        state.setdefault("wallet_snapshot_phase2_ready_alert_sent", False)
        state.setdefault("unsellable_guard_monitor_last_run_date", None)
        state.setdefault("unsellable_guard_last_status", None)
        state.setdefault("unsellable_guard_candidate_total", 0)
        state.setdefault("unsellable_guard_first_candidate_at", None)
        state.setdefault("unsellable_guard_last_candidate_at", None)
        state.setdefault("unsellable_guard_last_alert_date", None)
        state.setdefault("unsellable_guard_action_review_sent", False)
        state.setdefault("unsellable_guard_safety_alert_sent", False)
        state.setdefault("unsellable_guard_safety_last_seen_at", None)
        state.setdefault("lifecycle_review_last_run_date", None)
        state.setdefault("lifecycle_review_alerted", {})
        return state
    except Exception:
        return default


def load_shadow_city_tracking():
    """Carga la capa de observacion shadow por ciudad."""
    default = {
        "logic_series": LOGIC_SERIES,
        "updated_at": "",
        "cities": {},
        "recent_opportunities": [],
        "directional_history": [],
        "summary": {
            "cycles_with_shadow": 0,
            "opportunities_seen": 0,
            "edge_hits": 0,
            "promotable_cities": 0,
        },
    }
    if not os.path.exists(SHADOW_TRACKING_FILE):
        return default
    try:
        with open(SHADOW_TRACKING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        if data.get("logic_series") != LOGIC_SERIES:
            return default
        payload = dict(default)
        payload.update(data)
        if not isinstance(payload.get("cities"), dict):
            payload["cities"] = {}
        if not isinstance(payload.get("recent_opportunities"), list):
            payload["recent_opportunities"] = []
        if not isinstance(payload.get("directional_history"), list):
            payload["directional_history"] = []
        if not isinstance(payload.get("summary"), dict):
            payload["summary"] = dict(default["summary"])
        return payload
    except Exception:
        return default


def save_shadow_city_tracking(data):
    """Guarda la capa shadow por ciudad con orden estable."""
    payload = data if isinstance(data, dict) else {}
    payload.setdefault("logic_series", LOGIC_SERIES)
    payload.setdefault("updated_at", "")
    payload.setdefault("cities", {})
    payload.setdefault("recent_opportunities", [])
    payload.setdefault("directional_history", [])
    payload.setdefault("summary", {})

    ordered_cities = {}
    for city in sorted(payload["cities"]):
        ordered_cities[city] = payload["cities"][city]
    payload["cities"] = ordered_cities
    # Keep directional (edge_hit=True) and filtered separately, prioritize directional
    all_opps = payload["recent_opportunities"]
    directional = sorted(
        [o for o in all_opps if o.get("edge_hit")],
        key=lambda item: (str(item.get("seen_at", "")), float(item.get("edge_pct", 0) or 0)),
        reverse=True,
    )[:30]
    filtered = sorted(
        [o for o in all_opps if not o.get("edge_hit")],
        key=lambda item: (str(item.get("seen_at", "")), float(item.get("edge_pct", 0) or 0)),
        reverse=True,
    )[:10]
    payload["recent_opportunities"] = directional + filtered
    payload["directional_history"] = sorted(
        [
            row for row in payload["directional_history"]
            if isinstance(row, dict) and row.get("signal_key")
        ],
        key=lambda item: (
            str(item.get("last_seen_at", "") or item.get("first_seen_at", "")),
            float(item.get("best_edge_pct", 0) or 0),
        ),
        reverse=True,
    )[:SHADOW_DIRECTIONAL_HISTORY_LIMIT]

    with open(SHADOW_TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_city_policy_state():
    """Carga el overlay operativo automatico por ciudad."""
    default = {
        "logic_series": LOGIC_SERIES,
        "updated_at": "",
        "auto_canary_cities": {},
        "auto_shadow_cities": {},
        "auto_blocked_cities": {},
        "transition_history": [],
    }
    if not os.path.exists(CITY_POLICY_FILE):
        return default
    try:
        with open(CITY_POLICY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        if data.get("logic_series") != LOGIC_SERIES:
            return default
        return _normalize_city_policy_state(data, default=default)
    except Exception:
        return default


def _is_real_block_policy(meta):
    """True only for explicit real discards; legacy auto_block overlays are migrated to shadow."""
    if not isinstance(meta, dict):
        return False
    action = str(meta.get("action") or "").strip().lower()
    block_kind = str(meta.get("block_kind") or "").strip().lower()
    return action in {"real_block", "manual_block", "structural_block", "data_block"} or block_kind in {
        "real",
        "manual",
        "structural",
        "data",
    }


def _coerce_shadow_policy_entry(meta):
    """Normaliza una degradacion automatica a shadow y migra el legado auto_block -> shadow."""
    meta = meta if isinstance(meta, dict) else {}
    metrics = meta.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    shadowed_at = str(meta.get("shadowed_at") or meta.get("triggered_at") or "").strip()
    return {
        "action": "auto_shadow",
        "reason": str(meta.get("reason") or "baja performance persistente"),
        "metrics": {
            "trades": int(metrics.get("trades", 0) or 0),
            "wins": int(metrics.get("wins", 0) or 0),
            "win_rate": round(float(metrics.get("win_rate", 0.0) or 0.0), 1),
            "pnl": round(float(metrics.get("pnl", 0.0) or 0.0), 2),
            "observed_count": int(metrics.get("observed_count", 0) or 0),
            "shadow_seen": int(metrics.get("shadow_seen", 0) or 0),
            "shadow_edges": int(metrics.get("shadow_edges", 0) or 0),
            "shadow_best_edge": round(float(metrics.get("shadow_best_edge", 0.0) or 0.0), 1),
            "support_count": int(metrics.get("support_count", 0) or 0),
        },
        "from_mode": str(meta.get("from_mode") or "active"),
        "shadowed_at": shadowed_at,
        "source_action": str(meta.get("action") or "auto_shadow"),
    }


def _normalize_city_policy_state(data, default=None):
    """Mantiene el overlay consistente con la semantica canonica blocked/shadow/canary/active."""
    base = dict(default or {
        "logic_series": LOGIC_SERIES,
        "updated_at": "",
        "auto_canary_cities": {},
        "auto_shadow_cities": {},
        "auto_blocked_cities": {},
        "transition_history": [],
    })
    payload = dict(base)
    if isinstance(data, dict):
        payload.update(data)

    raw_auto_canary = payload.get("auto_canary_cities", {})
    raw_auto_shadow = payload.get("auto_shadow_cities", {})
    raw_auto_blocked = payload.get("auto_blocked_cities", {})
    raw_history = payload.get("transition_history", [])

    auto_canary = raw_auto_canary if isinstance(raw_auto_canary, dict) else {}
    auto_shadow = raw_auto_shadow if isinstance(raw_auto_shadow, dict) else {}
    auto_blocked = raw_auto_blocked if isinstance(raw_auto_blocked, dict) else {}
    history = raw_history if isinstance(raw_history, list) else []

    normalized_shadow = {
        city: _coerce_shadow_policy_entry(meta)
        for city, meta in auto_shadow.items()
        if isinstance(city, str) and city.strip()
    }
    normalized_blocked = {}
    for city, meta in auto_blocked.items():
        if not isinstance(city, str) or not city.strip():
            continue
        if _is_real_block_policy(meta):
            normalized_blocked[city] = meta if isinstance(meta, dict) else {}
        elif city not in normalized_shadow:
            normalized_shadow[city] = _coerce_shadow_policy_entry(meta)

    normalized_history = []
    for item in history:
        if not isinstance(item, dict):
            continue
        clean = dict(item)
        if clean.get("to") == "blocked" and str(clean.get("action") or "").strip().lower() == "auto_block":
            clean["to"] = "shadow"
            clean["action"] = "auto_shadow"
        normalized_history.append(clean)

    payload["auto_canary_cities"] = auto_canary
    payload["auto_shadow_cities"] = normalized_shadow
    payload["auto_blocked_cities"] = normalized_blocked
    payload["transition_history"] = normalized_history
    if not isinstance(payload.get("auto_canary_from_active"), dict):
        payload["auto_canary_from_active"] = {}
    if not isinstance(payload.get("active_city_monitoring"), dict):
        payload["active_city_monitoring"] = {}
    if not isinstance(payload.get("updated_at"), str):
        payload["updated_at"] = ""
    return payload


def save_city_policy_state(data):
    """Guarda el overlay operativo automatico por ciudad."""
    payload = _normalize_city_policy_state(data if isinstance(data, dict) else {})
    payload.setdefault("logic_series", LOGIC_SERIES)
    payload.setdefault("updated_at", "")
    payload.setdefault("auto_canary_cities", {})
    payload.setdefault("auto_shadow_cities", {})
    payload.setdefault("auto_blocked_cities", {})
    payload.setdefault("transition_history", [])
    payload["auto_canary_cities"] = {
        city: payload["auto_canary_cities"][city]
        for city in sorted(payload["auto_canary_cities"])
    }
    payload["auto_shadow_cities"] = {
        city: payload["auto_shadow_cities"][city]
        for city in sorted(payload["auto_shadow_cities"])
    }
    payload["auto_blocked_cities"] = {
        city: payload["auto_blocked_cities"][city]
        for city in sorted(payload["auto_blocked_cities"])
    }
    payload["transition_history"] = sorted(
        payload["transition_history"],
        key=lambda item: (str(item.get("at", "")), str(item.get("city", ""))),
        reverse=True,
    )[:40]
    with open(CITY_POLICY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def get_effective_city_mode(city, policy_state=None):
    """Devuelve active/canary/shadow/blocked segun politica manual + automatica."""
    city = str(city or "").strip()
    if not city:
        return "shadow"
    observed_proxy_helper = globals().get("_city_has_observed_proxy")
    has_observed_proxy = observed_proxy_helper(city) if callable(observed_proxy_helper) else False
    if is_city_blocked(city):
        return "blocked"
    policy_state = _normalize_city_policy_state(policy_state or load_city_policy_state())
    auto_blocked = policy_state.get("auto_blocked_cities", {}) if isinstance(policy_state, dict) else {}
    auto_shadow = policy_state.get("auto_shadow_cities", {}) if isinstance(policy_state, dict) else {}
    auto_canary = policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}
    auto_canary_from_active = policy_state.get("auto_canary_from_active", {}) if isinstance(policy_state, dict) else {}
    if city in auto_blocked:
        return "blocked" if not has_observed_proxy else "shadow"
    if city in auto_shadow:
        return "shadow"
    if city in auto_canary_from_active:
        return "canary"
    if city in ACTIVE_TRADING_CITIES:
        return "active"
    manual_proxy_review_helper = globals().get("_city_requires_manual_proxy_canary_review")
    needs_manual_proxy_review = (
        manual_proxy_review_helper(city) if callable(manual_proxy_review_helper) else False
    )
    if city in auto_canary and not needs_manual_proxy_review:
        return "canary"
    if city in CANARY_TRADING_CITIES:
        return "canary"
    return "shadow"


def _build_auto_city_block_policy(row, current_mode, triggered_at):
    """Reserva metadata de bloqueo para descartes reales explicitos."""
    row = row if isinstance(row, dict) else {}
    trades = int(row.get("trades", 0) or 0)
    win_rate = round(float(row.get("win_rate", 0.0) or 0.0), 1)
    pnl = round(float(row.get("pnl", 0.0) or 0.0), 2)
    if "pnl" not in row and row.get("pnl_display"):
        try:
            pnl = round(float(str(row.get("pnl_display", "$0.00")).replace("$", "")), 2)
        except (TypeError, ValueError):
            pnl = 0.0

    return {
        "action": "real_block",
        "reason": str(row.get("reason") or row.get("main_reason") or "baja accuracy persistente"),
        "metrics": {
            "trades": trades,
            "wins": int(row.get("wins", 0) or 0),
            "win_rate": win_rate,
            "pnl": pnl,
            "observed_count": int(row.get("observed_count", 0) or 0),
            "shadow_seen": int(row.get("shadow_seen", 0) or 0),
            "shadow_edges": int(row.get("shadow_edges", 0) or 0),
            "shadow_best_edge": round(float(row.get("shadow_best_edge", 0.0) or 0.0), 1),
            "support_count": int(row.get("support_count", 0) or 0),
        },
        "from_mode": str(current_mode or "active"),
        "triggered_at": triggered_at,
    }


def _build_auto_city_shadow_policy(row, current_mode, shadowed_at):
    """Normaliza la evidencia persistida al degradar una ciudad a shadow."""
    row = row if isinstance(row, dict) else {}
    trades = int(row.get("trades", 0) or 0)
    win_rate = round(float(row.get("win_rate", 0.0) or 0.0), 1)
    pnl = round(float(row.get("pnl", 0.0) or 0.0), 2)
    if "pnl" not in row and row.get("pnl_display"):
        try:
            pnl = round(float(str(row.get("pnl_display", "$0.00")).replace("$", "")), 2)
        except (TypeError, ValueError):
            pnl = 0.0

    return {
        "action": "auto_shadow",
        "reason": str(row.get("reason") or row.get("main_reason") or "baja performance persistente"),
        "metrics": {
            "trades": trades,
            "wins": int(row.get("wins", 0) or 0),
            "win_rate": win_rate,
            "pnl": pnl,
            "policy_source": str(row.get("policy_source") or "legacy"),
            "policy_is_provisional": bool(row.get("policy_is_provisional")),
            "policy_trades": int(row.get("policy_trades", trades) or 0),
            "policy_wins": int(row.get("policy_wins", row.get("wins", 0)) or 0),
            "policy_win_rate": round(float(row.get("policy_win_rate", win_rate) or 0.0), 1),
            "policy_pnl": round(float(row.get("policy_pnl", pnl) or 0.0), 2),
            "verified_trades": int(row.get("verified_trades", 0) or 0),
            "legacy_trades": int(row.get("legacy_trades", trades) or 0),
            "observed_count": int(row.get("observed_count", 0) or 0),
            "shadow_seen": int(row.get("shadow_seen", 0) or 0),
            "shadow_edges": int(row.get("shadow_edges", 0) or 0),
            "shadow_best_edge": round(float(row.get("shadow_best_edge", 0.0) or 0.0), 1),
            "support_count": int(row.get("support_count", 0) or 0),
        },
        "from_mode": str(current_mode or "active"),
        "shadowed_at": shadowed_at,
    }


def _scaled_position(position, estimated_prob, city_mode):
    """Reduce sizing para modo canary sin tocar la logica principal."""
    if city_mode != "canary" or not isinstance(position, dict):
        return position
    aggressive_price = float(position.get("aggressive_price", position.get("market_price", 0)) or 0)
    market_price = float(position.get("market_price", aggressive_price) or aggressive_price)
    if aggressive_price <= 0:
        return position
    amount = max(MIN_BET, round(float(position.get("amount", 0) or 0) * CANARY_POSITION_SCALE, 2))
    shares = round(amount / aggressive_price, 2)
    profit = round(shares * (1.0 - aggressive_price), 2)
    loss = round(amount, 2)
    ev = round(estimated_prob * profit - (1 - estimated_prob) * loss, 2)
    scaled = dict(position)
    scaled.update({
        "fraction_pct": round(float(position.get("fraction_pct", 0) or 0) * CANARY_POSITION_SCALE, 2),
        "amount": amount,
        "shares": shares,
        "profit_if_win": profit,
        "loss_if_lose": loss,
        "expected_value": ev,
        "aggressive_price": aggressive_price,
        "market_price": market_price,
    })
    return scaled


def _resize_position_amount(position, target_amount, estimated_prob):
    """Recalcula una posicion manteniendo precio/EV cuando sube o baja amount."""
    if not isinstance(position, dict):
        return position
    aggressive_price = float(position.get("aggressive_price", position.get("market_price", 0)) or 0)
    market_price = float(position.get("market_price", aggressive_price) or aggressive_price)
    if aggressive_price <= 0:
        return position
    amount = round(float(target_amount or 0), 2)
    if amount <= 0:
        return position
    shares = round(amount / aggressive_price, 2)
    profit = round(shares * (1.0 - aggressive_price), 2)
    loss = round(amount, 2)
    ev = round(estimated_prob * profit - (1 - estimated_prob) * loss, 2)
    resized = dict(position)
    resized.update({
        "amount": amount,
        "shares": shares,
        "profit_if_win": profit,
        "loss_if_lose": loss,
        "expected_value": ev,
        "aggressive_price": aggressive_price,
        "market_price": market_price,
    })
    return resized


def record_shadow_city_opportunities(opportunities, cycle_context=None):
    """
    Registra oportunidades fuera de allowlist para aprender sin comprar.
    Cada fila representa una operacion que el bot habria considerado si la ciudad
    estuviera habilitada.
    """
    data = load_shadow_city_tracking()
    cities = data.setdefault("cities", {})
    recent = data.setdefault("recent_opportunities", [])
    directional_history = data.setdefault("directional_history", [])
    summary = data.setdefault("summary", {})

    cycle_context = cycle_context if isinstance(cycle_context, dict) else {}
    cycle_seen = False

    for item in opportunities or []:
        if not isinstance(item, dict):
            continue
        city = str(item.get("city", "") or "").strip()
        if not city:
            continue
        seen_at = str(item.get("seen_at") or datetime.now(timezone.utc).isoformat())
        city_state = cities.setdefault(city, {
            "city": city,
            "first_seen_at": seen_at,
            "last_seen_at": seen_at,
            "markets_seen": 0,
            "edge_hits": 0,
            "cycles_seen": 0,
            "best_edge_pct": 0.0,
            "best_ev": 0.0,
            "last_side": "",
            "last_question": "",
            "last_date": "",
            "last_market_price": None,
            "last_our_prob": None,
            "last_forecast_max": None,
            "recent_edges": [],
        })
        city_state["last_seen_at"] = seen_at
        city_state["markets_seen"] = int(city_state.get("markets_seen", 0) or 0) + 1
        city_state["edge_hits"] = int(city_state.get("edge_hits", 0) or 0) + (1 if item.get("edge_hit") else 0)
        city_state["cycles_seen"] = int(city_state.get("cycles_seen", 0) or 0) + (1 if item.get("first_for_cycle") else 0)
        city_state["best_edge_pct"] = round(max(float(city_state.get("best_edge_pct", 0) or 0), float(item.get("edge_pct", 0) or 0)), 1)
        city_state["best_ev"] = round(max(float(city_state.get("best_ev", 0) or 0), float(item.get("expected_value", 0) or 0)), 2)
        city_state["last_side"] = item.get("side", "")
        city_state["last_question"] = item.get("question", "")
        city_state["last_date"] = item.get("date", "")
        city_state["last_market_price"] = item.get("mkt_price")
        city_state["last_our_prob"] = item.get("our_prob")
        city_state["last_forecast_max"] = item.get("forecast_max")
        recent_edge = {
            "seen_at": seen_at,
            "date": item.get("date", ""),
            "question": item.get("question", ""),
            "side": item.get("side", ""),
            "edge_hit": bool(item.get("edge_hit")),
            "edge_pct": round(float(item.get("edge_pct", 0) or 0), 1),
            "expected_value": round(float(item.get("expected_value", 0) or 0), 2),
            "market_price": item.get("mkt_price"),
            "our_prob": item.get("our_prob"),
            "forecast_max": item.get("forecast_max"),
        }
        city_state.setdefault("recent_edges", []).append(recent_edge)
        city_state["recent_edges"] = sorted(
            city_state["recent_edges"],
            key=lambda row: (str(row.get("seen_at", "")), float(row.get("edge_pct", 0) or 0)),
            reverse=True,
        )[:8]
        recent.append({
            "city": city,
            "seen_at": seen_at,
            "date": item.get("date", ""),
            "question": item.get("question", ""),
            "side": item.get("side", ""),
            "edge_hit": bool(item.get("edge_hit")),
            "edge_pct": round(float(item.get("edge_pct", 0) or 0), 1),
            "expected_value": round(float(item.get("expected_value", 0) or 0), 2),
            "market_price": item.get("mkt_price"),
            "our_prob": item.get("our_prob"),
            "forecast_max": item.get("forecast_max"),
        })
        if item.get("first_for_cycle"):
            cycle_seen = True

    directional_history[:] = _merge_shadow_signal_history(directional_history, opportunities or [])

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    summary["cycles_with_shadow"] = int(summary.get("cycles_with_shadow", 0) or 0) + (1 if cycle_seen else 0)
    summary["opportunities_seen"] = sum(int(item.get("markets_seen", 0) or 0) for item in cities.values())
    summary["edge_hits"] = sum(int(item.get("edge_hits", 0) or 0) for item in cities.values())
    summary["promotable_cities"] = sum(
        1
        for item in cities.values()
        if float(item.get("best_edge_pct", 0) or 0) >= MIN_EDGE
    )

    if cycle_context:
        summary["last_cycle_number"] = cycle_context.get("cycle_number")
        summary["last_logic_cycle_number"] = cycle_context.get("logic_cycle_number")
        summary["last_cycle_at"] = cycle_context.get("timestamp_utc")

    save_shadow_city_tracking(data)
    return data


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


def _html_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _bankroll_scaling_runtime_args():
    data_dir = DATA_DIR or "data"
    db_path = SQLITE_DB_PATH if DATA_DIR else os.path.join(data_dir, "polymarket.db")
    return data_dir, db_path


def run_bankroll_scaling_check_json():
    """
    Ejecuta el check read-only de scaling y devuelve su contrato JSON.
    Fail-safe: no escribe estado, no manda Telegram y no interrumpe ciclos.
    """
    data_dir, db_path = _bankroll_scaling_runtime_args()
    command = [
        sys.executable,
        BANKROLL_SCALING_CHECK_SCRIPT,
        "--data-dir",
        data_dir,
        "--db",
        db_path,
        "--json",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=BANKROLL_SCALING_MONITOR_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        log.warning(f"bankroll scaling check: fallo ejecutando CLI read-only ({exc})")
        return None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:500]
        log.warning(f"bankroll scaling check: exit={result.returncode} detail={detail}")
        return None
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        log.warning(f"bankroll scaling check: JSON invalido ({exc})")
        return None
    if not isinstance(payload, dict) or not payload.get("status"):
        log.warning("bankroll scaling check: contrato JSON incompleto")
        return None
    return payload


def _bankroll_scaling_item_codes(items):
    if not isinstance(items, list):
        return []
    codes = []
    for item in items:
        if isinstance(item, dict) and item.get("code"):
            codes.append(str(item.get("code")))
    return codes


def _bankroll_scaling_blockers_hash(report):
    codes = sorted(_bankroll_scaling_item_codes(report.get("hard_blockers")))
    return "|".join(codes)


def _bankroll_scaling_criterion(report, name):
    for item in report.get("criteria", []) or []:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return {}


def _bankroll_scaling_format_value(value, kind):
    if value is None:
        return "n/d"
    try:
        number = float(value)
    except Exception:
        return _html_escape(value)
    if kind == "money":
        return f"${number:+.2f}"
    if kind == "pct":
        return f"{number:.1f}%"
    return f"{number:g}"


def format_bankroll_scaling_telegram(report):
    status = str(report.get("status", "UNKNOWN"))
    current = report.get("current_bankroll", "?")
    target = report.get("target_tier", "?")
    evidence = report.get("evidence", {}) if isinstance(report.get("evidence"), dict) else {}
    pnl = evidence.get("pnl_drawdown", {}) if isinstance(evidence.get("pnl_drawdown"), dict) else {}
    sqlite = evidence.get("sqlite_recorder", {}) if isinstance(evidence.get("sqlite_recorder"), dict) else {}
    positions = evidence.get("positions", {}) if isinstance(evidence.get("positions"), dict) else {}
    phase1 = evidence.get("phase1", {}) if isinstance(evidence.get("phase1"), dict) else {}

    decision = "eligible for manual review" if report.get("eligible_for_manual_review") else "no subir bankroll"
    lines = [
        "📊 <b>Bankroll Scaling Monitor</b>",
        "",
        f"${current} → ${target}: <b>{_html_escape(status)}</b>",
        f"Decisión: {_html_escape(decision)}.",
        "NO autoriza subida automática ni cambiar BANKROLL.",
        "",
    ]

    blockers = _bankroll_scaling_item_codes(report.get("hard_blockers"))
    if blockers:
        lines.append("<b>Bloqueantes</b>")
        for code in blockers[:6]:
            if code == "pnl_negative":
                detail = f"PnL negativo: {_bankroll_scaling_format_value(pnl.get('pnl_total'), 'money')}"
            elif code == "win_rate_below_threshold":
                detail = f"WR bajo: {_bankroll_scaling_format_value(pnl.get('win_rate_pct'), 'pct')}"
            elif code == "recent_drawdown_exceeded":
                detail = f"Drawdown reciente: {_bankroll_scaling_format_value(pnl.get('drawdown_last_5'), 'money')}"
            elif code == "sqlite_recorder_stale":
                detail = f"SQLite stale: age_hours={sqlite.get('last_write_age_hours')}"
            else:
                detail = code.replace("_", " ")
            lines.append(f"❌ {_html_escape(detail)}")
        if len(blockers) > 6:
            lines.append(f"❌ ... y {len(blockers) - 6} mas")
        lines.append("")

    watch = _bankroll_scaling_item_codes(report.get("watch_items"))
    missing = _bankroll_scaling_item_codes(report.get("missing_evidence"))
    if watch or missing:
        lines.append("<b>Vigilancia</b>")
        for code in (watch + missing)[:5]:
            lines.append(f"⏳ {_html_escape(code.replace('_', ' '))}")
        lines.append("")

    favorable = []
    if sqlite.get("readable") and sqlite.get("last_write_age_hours") is not None:
        favorable.append("SQLite fresh")
    if not sqlite.get("large_gaps"):
        favorable.append("Sin gaps")
    if int(positions.get("stale_pending_exits", 0) or 0) == 0:
        favorable.append("Sin pending exits")
    if _bankroll_scaling_criterion(report, "cycles_minimum").get("status") == "pass":
        favorable.append("Ciclos suficientes")
    if phase1.get("status") == "ready":
        favorable.append("Phase 1 proxy OK - canonical check pending/no evaluado")
    if favorable:
        lines.append("<b>A favor</b>")
        for item in favorable[:5]:
            lines.append(f"✅ {_html_escape(item)}")
        lines.append("")

    lines.extend(
        [
            "<b>Acción</b>",
            f"Mantener bankroll ${current}. No cambiar BANKROLL.",
            "Phase 1 canonica: validar con tools/phase1_readiness_check.py.",
            "No autoriza Truth Pipeline/Fase C.",
            "La politica exige revision manual:",
            "docs/bankroll_scaling_policy.md",
        ]
    )
    return "\n".join(lines)


def run_wallet_snapshot_json():
    """
    Ejecuta la captura read-only de wallet y devuelve el contrato JSON.
    Fail-safe: no manda Telegram, no toca trading y no interrumpe ciclos.
    """
    data_dir = DATA_DIR or "data"
    command = [
        sys.executable,
        WALLET_SNAPSHOT_SCRIPT,
        "--data-dir",
        data_dir,
        "--json",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=WALLET_SNAPSHOT_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        log.warning(f"wallet snapshot: fallo ejecutando CLI read-only ({exc})")
        return None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:500]
        log.warning(f"wallet snapshot: exit={result.returncode} detail={detail}")
        return None
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        log.warning(f"wallet snapshot: JSON invalido ({exc})")
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("phase2_readiness"), dict):
        log.warning("wallet snapshot: contrato JSON incompleto")
        return None
    return payload


def _wallet_snapshot_format_time(value):
    dt = None
    try:
        text = str(value or "").strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if text:
            dt = datetime.fromisoformat(text)
    except Exception:
        dt = None
    if dt is None:
        return "n/d"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def format_wallet_snapshot_phase2_ready_telegram(report):
    readiness = report.get("phase2_readiness", {}) if isinstance(report.get("phase2_readiness"), dict) else {}
    history = report.get("history", {}) if isinstance(report.get("history"), dict) else {}
    pnl = report.get("wallet_pnl", {}) if isinstance(report.get("wallet_pnl"), dict) else {}
    wallet_pnl = pnl.get("wallet_pnl_7d")
    try:
        pnl_text = f"${float(wallet_pnl):+.2f}" if wallet_pnl is not None else "n/d"
    except Exception:
        pnl_text = "n/d"
    valid_days = readiness.get("valid_snapshot_days", history.get("valid_snapshot_days", "n/d"))
    required_days = readiness.get("required_snapshot_days", 7)
    return "\n".join(
        [
            "✅ <b>Wallet Snapshot listo para Fase 2</b>",
            "",
            "phase2_ready=true",
            f"P/L wallet 7d: {pnl_text}",
            f"Confianza: {_html_escape(pnl.get('wallet_pnl_confidence', 'n/d'))}",
            f"Snapshots válidos: {valid_days} días / {required_days}",
            f"Baseline: {_wallet_snapshot_format_time(history.get('baseline_snapshot_at'))}",
            f"Último snapshot: {_wallet_snapshot_format_time(history.get('latest_snapshot_at'))}",
            "",
            "Siguiente paso: preparar integración con pnl_reconciliation_alert.py.",
            "No cambiar BANKROLL automáticamente ni sizing.",
        ]
    )


def run_unsellable_guard_monitor_json():
    """
    Ejecuta el monitor read-only del Unsellable Guard y devuelve su contrato JSON.
    Fail-safe: no manda Telegram, no toca trading y no interrumpe ciclos.
    """
    data_dir = DATA_DIR or "data"
    command = [
        sys.executable,
        UNSELLABLE_GUARD_MONITOR_SCRIPT,
        "--data-dir",
        data_dir,
        "--skip-log",
        SKIP_LOG_FILE,
        "--json",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=UNSELLABLE_GUARD_MONITOR_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        log.warning(f"unsellable guard monitor: fallo ejecutando CLI read-only ({exc})")
        return None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:500]
        log.warning(f"unsellable guard monitor: exit={result.returncode} detail={detail}")
        return None
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        log.warning(f"unsellable guard monitor: JSON invalido ({exc})")
        return None
    if not isinstance(payload, dict) or not payload.get("status"):
        log.warning("unsellable guard monitor: contrato JSON incompleto")
        return None
    return payload


def _unsellable_guard_monitor_pct(value):
    if value is None:
        return "n/d"
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "n/d"


def _unsellable_guard_monitor_money(value):
    if value is None:
        return "n/d"
    try:
        return f"${float(value):.2f}"
    except Exception:
        return "n/d"


def format_unsellable_guard_monitor_telegram(report):
    status = str(report.get("status", "UNKNOWN"))
    lines = [
        "<b>Unsellable Guard Monitor</b>",
        f"Nivel: <b>{_html_escape(status)}</b>",
        "",
        f"Ventana: ultimas {report.get('window_hours', 24)}h",
        f"Candidatos LOG_ONLY: {int(report.get('total_candidates_24h', 0) or 0)}",
        f"Acumulado 7d: {int(report.get('total_candidates_7d', 0) or 0)}",
        f"Acumulado total: {int(report.get('total_candidates_all_time', 0) or 0)}",
        f"Skipped real inesperado: {int(report.get('unexpected_real_skips_count', 0) or 0)}",
        "",
    ]

    cities = report.get("top_cities") if isinstance(report.get("top_cities"), list) else []
    if cities:
        lines.append("<b>Top ciudades</b>")
        for item in cities[:5]:
            if isinstance(item, dict):
                lines.append(f"- {_html_escape(item.get('city', '?'))}: {item.get('count', 0)}")
        lines.append("")

    conditions = report.get("conditions") if isinstance(report.get("conditions"), list) else []
    if conditions:
        lines.append("<b>Condiciones</b>")
        for item in conditions[:5]:
            if isinstance(item, dict):
                lines.append(f"- {_html_escape(item.get('condition', '?'))}: {item.get('count', 0)}")
        lines.append("")

    lines.extend([
        "<b>Promedios</b>",
        f"- size_ratio: {_unsellable_guard_monitor_pct(report.get('avg_size_ratio'))}",
        f"- price_at_guard: {_unsellable_guard_monitor_money(report.get('avg_price_at_guard'))}",
        "",
    ])

    examples = report.get("examples") if isinstance(report.get("examples"), list) else []
    if examples:
        lines.append("<b>Ejemplos</b>")
        for idx, item in enumerate(examples[:3], start=1):
            if not isinstance(item, dict):
                continue
            lines.append(
                f"{idx}. {_html_escape(item.get('city', '?'))} {_html_escape(item.get('side', '?'))} "
                f"{_html_escape(item.get('condition', '?'))} | "
                f"price={_unsellable_guard_monitor_money(item.get('price_at_guard'))} | "
                f"size={_unsellable_guard_monitor_pct(item.get('size_ratio'))} | "
                f"amount={_unsellable_guard_monitor_money(item.get('amount'))}"
            )
        lines.append("")

    if status == "ACTION_SAFETY":
        lines.extend([
            "<b>Accion</b>",
            "Aparecio SKIP real del guard mientras LOG_ONLY debe estar activo.",
            "Revisar Railway env: UNSELLABLE_GUARD_ENABLED=1 y UNSELLABLE_GUARD_LOG_ONLY=1.",
            "Revisión manual / Opus requerida antes de promoción. No activar SKIP automáticamente.",
        ])
    else:
        lines.extend([
            "<b>Accion</b>",
            "Revisión manual / Opus requerida antes de promoción. No activar SKIP automáticamente.",
        ])
    return "\n".join(lines)


def maybe_run_unsellable_guard_monitor(state, now=None):
    """
    Monitor diario read-only del Unsellable Guard v1 LOG_ONLY.
    No activa SKIP ni cambia trading; solo resume skip_log y alerta si hay senales.
    """
    logger = globals().get("log")
    if not UNSELLABLE_GUARD_MONITOR_ENABLED:
        if logger:
            logger.info("unsellable guard monitor: skip (UNSELLABLE_GUARD_MONITOR_ENABLED=0)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    target_hour = UNSELLABLE_GUARD_MONITOR_HOUR_UTC % 24
    if now.hour < target_hour:
        if logger:
            logger.info(
                "unsellable guard monitor: skip "
                f"(before target hour: now_hour={now.hour} target_hour={target_hour})"
            )
        return False

    today = now.date().isoformat()
    if state.get("unsellable_guard_monitor_last_run_date") == today:
        if logger:
            logger.info(f"unsellable guard monitor: skip (already ran today: {today})")
        return False

    previous_status = state.get("unsellable_guard_last_status")
    previous_total = int(state.get("unsellable_guard_candidate_total", 0) or 0)
    previous_safety_at = state.get("unsellable_guard_safety_last_seen_at")

    state["unsellable_guard_monitor_last_run_date"] = today
    report = run_unsellable_guard_monitor_json()
    if not report:
        return True

    status = str(report.get("status", "UNKNOWN"))
    total_all = int(report.get("total_candidates_all_time", 0) or 0)
    total_24h = int(report.get("total_candidates_24h", 0) or 0)
    last_safety_at = report.get("last_safety_at")

    state["unsellable_guard_last_status"] = status
    state["unsellable_guard_candidate_total"] = total_all
    state["unsellable_guard_first_candidate_at"] = report.get("first_candidate_at")
    state["unsellable_guard_last_candidate_at"] = report.get("last_candidate_at")

    should_alert = False
    if status == "ACTION_SAFETY":
        should_alert = bool(last_safety_at and last_safety_at != previous_safety_at)
        if should_alert:
            state["unsellable_guard_safety_alert_sent"] = True
            state["unsellable_guard_safety_last_seen_at"] = last_safety_at
    elif status == "ACTION_REVIEW":
        should_alert = (
            previous_status != "ACTION_REVIEW"
            or total_all > previous_total
            or not state.get("unsellable_guard_action_review_sent")
        )
        if should_alert:
            state["unsellable_guard_action_review_sent"] = True
    elif status == "WATCH":
        should_alert = total_24h > 0 and state.get("unsellable_guard_last_alert_date") != today

    if should_alert:
        send_telegram(format_unsellable_guard_monitor_telegram(report))
        state["unsellable_guard_last_alert_date"] = today
    elif logger:
        logger.info(
            "unsellable guard monitor: OK "
            f"(status={status}, candidates_24h={total_24h}, total={total_all})"
        )
    return True


def maybe_run_wallet_snapshot(state, now=None):
    """
    Captura wallet/portfolio una vez al dia como observabilidad read-only.
    No envia Telegram durante ACUMULANDO; solo alerta one-shot al phase2_ready.
    """
    logger = globals().get("log")
    if not WALLET_SNAPSHOT_ENABLED:
        if logger:
            logger.info("wallet snapshot: skip (WALLET_SNAPSHOT_ENABLED=0)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    target_hour = WALLET_SNAPSHOT_HOUR_UTC % 24
    if now.hour < target_hour:
        if logger:
            logger.info(
                "wallet snapshot: skip "
                f"(before target hour: now_hour={now.hour} target_hour={target_hour})"
            )
        return False

    today = now.date().isoformat()
    if state.get("wallet_snapshot_last_run_date") == today:
        if logger:
            logger.info(f"wallet snapshot: skip (already ran today: {today})")
        return False

    state["wallet_snapshot_last_run_date"] = today
    report = run_wallet_snapshot_json()
    if not report:
        state["wallet_snapshot_last_error_date"] = today
        return True

    readiness = report.get("phase2_readiness", {}) if isinstance(report.get("phase2_readiness"), dict) else {}
    history = report.get("history", {}) if isinstance(report.get("history"), dict) else {}
    phase2_ready = bool(readiness.get("phase2_ready"))
    state["wallet_snapshot_last_phase2_ready"] = phase2_ready
    state["wallet_snapshot_last_ready_reason"] = readiness.get("phase2_ready_reason")
    state["wallet_snapshot_last_valid_snapshot_days"] = readiness.get(
        "valid_snapshot_days",
        history.get("valid_snapshot_days", 0),
    )
    state["wallet_snapshot_last_valid_snapshot_at"] = history.get("latest_snapshot_at")

    if phase2_ready and not state.get("wallet_snapshot_phase2_ready_alert_sent"):
        send_telegram(format_wallet_snapshot_phase2_ready_telegram(report))
        state["wallet_snapshot_phase2_ready_alert_sent"] = True

    if logger:
        logger.info(
            "wallet snapshot: OK "
            f"(phase2_ready={phase2_ready}, reason={state.get('wallet_snapshot_last_ready_reason')})"
        )
    return True


def maybe_run_bankroll_scaling_monitor(state):
    """
    Monitor read-only de scaling: alerta solo por cambios o resumen anti-spam.
    Devuelve True si muta alerts_state. Si el check falla, no alerta ni rompe ciclo.
    """
    if not BANKROLL_SCALING_MONITOR_ENABLED:
        return False
    report = run_bankroll_scaling_check_json()
    if not report:
        return False

    status = str(report.get("status", "UNKNOWN"))
    target_tier = report.get("target_tier")
    blockers_hash = _bankroll_scaling_blockers_hash(report)
    eligible = bool(report.get("eligible_for_manual_review"))
    cycle = int(bot_state.get("cycle_count", 0) or 0)
    every_cycles = max(1, int(BANKROLL_SCALING_MONITOR_EVERY_CYCLES or 6))
    last_cycle = int(state.get("bankroll_scaling_last_alert_cycle", 0) or 0)

    status_changed = status != state.get("bankroll_scaling_last_status")
    target_changed = target_tier != state.get("bankroll_scaling_last_target_tier")
    blockers_changed = blockers_hash != state.get("bankroll_scaling_last_blockers_hash")
    eligible_transition = eligible and not state.get("bankroll_scaling_last_eligible_for_manual_review", False)
    cycle_summary_due = cycle > 0 and (cycle - last_cycle) >= every_cycles

    should_alert = (
        eligible_transition
        or (BANKROLL_SCALING_MONITOR_ON_STATUS_CHANGE and (status_changed or target_changed or blockers_changed))
        or cycle_summary_due
    )

    state["bankroll_scaling_last_status"] = status
    state["bankroll_scaling_last_target_tier"] = target_tier
    state["bankroll_scaling_last_blockers_hash"] = blockers_hash
    state["bankroll_scaling_last_eligible_for_manual_review"] = eligible
    state["bankroll_scaling_last_digest_date"] = datetime.now(timezone.utc).date().isoformat()

    if should_alert:
        send_telegram(format_bankroll_scaling_telegram(report))
        state["bankroll_scaling_last_alert_cycle"] = cycle
    return True


def load_intra_reeval_state(observed_token_ids=None):
    """Carga el estado persistente de re-evaluación intra-ciclo.

    observed_token_ids: si se pasa, purga del cooldown los token_ids que no estén ahí.
    """
    default = {
        "generated_at": "",
        "cooldown": {},
        "shadow_log": {
            "triggers": [],
            "first_trigger_at": "",
            "last_telegram_at": "",
            "review_alert_sent": False,
        },
    }
    if not os.path.exists(INTRA_REEVAL_STATE_FILE):
        return default
    try:
        with open(INTRA_REEVAL_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        state = dict(default)
        state["cooldown"] = data.get("cooldown", {}) if isinstance(data.get("cooldown"), dict) else {}
        shadow = data.get("shadow_log", {}) if isinstance(data.get("shadow_log"), dict) else {}
        state["shadow_log"] = {
            "triggers": shadow.get("triggers", []) if isinstance(shadow.get("triggers"), list) else [],
            "first_trigger_at": shadow.get("first_trigger_at", ""),
            "last_telegram_at": shadow.get("last_telegram_at", ""),
            "review_alert_sent": shadow.get("review_alert_sent", False),
        }
        # Purgar entradas cooldown cuyos token_ids no estén en posiciones observadas
        if observed_token_ids is not None:
            obs_set = set(str(t) for t in observed_token_ids)
            state["cooldown"] = {k: v for k, v in state["cooldown"].items() if k in obs_set}
        return state
    except Exception:
        return default


def save_intra_reeval_state(state):
    """Guarda el estado persistente de re-evaluación intra-ciclo."""
    try:
        state["generated_at"] = datetime.now(timezone.utc).isoformat()
        with open(INTRA_REEVAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando intra_reeval_state: {e}")


def load_sl_intra_guard_state():
    """v10.6.40: estado persistente del guard SL_intra exact+near-resolution."""
    default = {
        "version": 1,
        "guard_started_at": "",
        "skips": [],
        "last_telegram_at": "",
        "review_alert_sent": False,
        "review_started_at": "",
    }
    if not os.path.exists(SL_INTRA_GUARD_STATE_FILE):
        return default
    try:
        with open(SL_INTRA_GUARD_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        state = dict(default)
        state["guard_started_at"] = data.get("guard_started_at", "") or ""
        skips = data.get("skips", [])
        state["skips"] = skips if isinstance(skips, list) else []
        state["last_telegram_at"] = data.get("last_telegram_at", "") or ""
        state["review_alert_sent"] = bool(data.get("review_alert_sent", False))
        state["review_started_at"] = data.get("review_started_at", "") or ""
        return state
    except Exception:
        return default


def save_sl_intra_guard_state(state):
    """v10.6.40: persiste estado del guard SL_intra."""
    try:
        skips = state.get("skips", [])
        if isinstance(skips, list) and len(skips) > 500:
            state["skips"] = skips[-500:]
        with open(SL_INTRA_GUARD_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando sl_intra_guard_audit: {e}")


def _sl_intra_guard_should_skip(condition, days_ahead):
    """v10.6.40: True si la posición cumple el guard exact+near-resolution."""
    if not SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION:
        return False
    if not condition or str(condition).lower() != "exact":
        return False
    if days_ahead is None:
        return False
    try:
        return int(days_ahead) <= SL_INTRA_GUARD_DAYS_AHEAD_MAX
    except (ValueError, TypeError):
        return False


def _sl_intra_guard_cohort_fields(pct_pnl_at_skip):
    """Classify SL_intra guard skip audit events for LOG_ONLY review analytics."""
    base = {
        "sl_window_catchable_threshold": SL_INTRA_GUARD_CATCHABLE_THRESHOLD_PCT,
        "deep_drawdown_threshold_high": SL_INTRA_GUARD_DEEP_DRAWDOWN_HIGH_PCT,
        "deep_drawdown_threshold_low": SL_INTRA_GUARD_DEEP_DRAWDOWN_LOW_PCT,
        "cohort_schema_version": SL_INTRA_GUARD_COHORT_SCHEMA_VERSION,
    }
    if pct_pnl_at_skip is None or pct_pnl_at_skip == "":
        base.update({
            "sl_window_catchable": None,
            "deep_drawdown_at_skip": None,
            "cohort": "unknown",
            "cohort_reason": "pct_pnl_at_skip_missing",
        })
        return base
    try:
        pct = float(pct_pnl_at_skip)
    except (ValueError, TypeError):
        base.update({
            "sl_window_catchable": None,
            "deep_drawdown_at_skip": None,
            "cohort": "unknown",
            "cohort_reason": "pct_pnl_at_skip_invalid",
        })
        return base
    if pct > SL_INTRA_GUARD_CATCHABLE_THRESHOLD_PCT:
        base.update({
            "sl_window_catchable": True,
            "deep_drawdown_at_skip": False,
            "cohort": "zone_a",
            "cohort_reason": "pct_pnl_at_skip_gt_-35_leverage_real",
        })
    elif pct > SL_INTRA_GUARD_DEEP_DRAWDOWN_LOW_PCT:
        base.update({
            "sl_window_catchable": False,
            "deep_drawdown_at_skip": True,
            "cohort": "zone_b",
            "cohort_reason": "pct_pnl_at_skip_between_-75_and_-35_deep_drawdown",
        })
    else:
        base.update({
            "sl_window_catchable": False,
            "deep_drawdown_at_skip": False,
            "cohort": "zone_c",
            "cohort_reason": "pct_pnl_at_skip_lte_-75_inherited_loss",
        })
    return base


def _extract_logic_series(value):
    """Normaliza 'v10.5.4' o '10.5' a '10.5'."""
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d+\.\d+)", value)
    return match.group(1) if match else None


def _sl_intra_hazard_monitor_default_state():
    return {
        "version": 1,
        "monitor_version": SL_INTRA_HAZARD_MONITOR_VERSION,
        "monitor_started_at": "",
        "last_telegram_at": "",
        "seen": {},
        "collapsed_candidates": {},
        "events": [],
    }


def load_sl_intra_hazard_monitor_state():
    """L2 Hazard Monitor: auditoria independiente, separada del guard SL_intra."""
    default = _sl_intra_hazard_monitor_default_state()
    if not os.path.exists(SL_INTRA_HAZARD_MONITOR_STATE_FILE):
        return default
    try:
        with open(SL_INTRA_HAZARD_MONITOR_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        state = dict(default)
        state["monitor_started_at"] = data.get("monitor_started_at", "") or ""
        state["last_telegram_at"] = data.get("last_telegram_at", "") or ""
        seen = data.get("seen", {})
        state["seen"] = seen if isinstance(seen, dict) else {}
        collapsed_candidates = data.get("collapsed_candidates", {})
        state["collapsed_candidates"] = collapsed_candidates if isinstance(collapsed_candidates, dict) else {}
        events = data.get("events", [])
        state["events"] = events if isinstance(events, list) else []
        return state
    except Exception:
        return default


def save_sl_intra_hazard_monitor_state(state):
    """L2 Hazard Monitor: persiste solo observabilidad LOG_ONLY."""
    try:
        events = state.get("events", [])
        if isinstance(events, list) and len(events) > SL_INTRA_HAZARD_MAX_EVENTS:
            state["events"] = events[-SL_INTRA_HAZARD_MAX_EVENTS:]
        with open(SL_INTRA_HAZARD_MONITOR_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando sl_intra_hazard_monitor_audit: {e}")


def _sl_intra_hazard_monitor_tier(pct_pnl, cur_price, current_value, collapsed_cycles=0):
    """Clasifica riesgo L2 sin accion ejecutable."""
    try:
        pct_value = float(pct_pnl)
        price_value = float(cur_price)
        current_value_float = float(current_value)
        collapsed_cycles_value = int(collapsed_cycles or 0)
    except (ValueError, TypeError):
        return ""
    if (
        price_value <= SL_INTRA_HAZARD_COLLAPSED_PRICE
        and collapsed_cycles_value >= SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES
    ):
        return "collapsed"
    if (
        pct_value <= SL_INTRA_HAZARD_TERMINAL_PNL_PCT
        or current_value_float <= SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE
    ):
        return "terminal"
    if pct_value <= SL_INTRA_HAZARD_DEEP_PNL_PCT:
        return "deep"
    if pct_value <= SL_INTRA_HAZARD_DETERIORATING_PNL_PCT:
        return "deteriorating"
    return ""


def _sl_intra_hazard_telegram_allowed(state, now_utc):
    last_telegram = state.get("last_telegram_at", "")
    if not last_telegram:
        return True
    try:
        last_dt = datetime.fromisoformat(last_telegram.replace("Z", "+00:00"))
        return (now_utc - last_dt).total_seconds() >= SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN * 60
    except (ValueError, TypeError):
        return True


def maybe_record_sl_intra_hazard_event(position, *, condition, days_ahead, entry_price, now_utc=None):
    """L2 Hazard Monitor LOG_ONLY: observa solo posiciones que L1 protegeria."""
    if not SL_INTRA_HAZARD_MONITOR_ENABLED:
        return False
    if not SL_INTRA_HAZARD_MONITOR_LOG_ONLY:
        return False
    if not _sl_intra_guard_should_skip(condition, days_ahead):
        return False

    token_id = str(position.get("asset", "") or "").strip()
    if not token_id:
        return False
    now = now_utc or datetime.now(timezone.utc)
    state = load_sl_intra_hazard_monitor_state()
    state_changed = False
    if not state.get("monitor_started_at"):
        state["monitor_started_at"] = now.isoformat()
        state_changed = True

    try:
        cur_price = float(position.get("curPrice", 0))
        pct_pnl = float(position.get("percentPnl", 0))
        current_value = float(position.get("currentValue", 0))
    except (ValueError, TypeError):
        return False

    collapsed_candidates = state.setdefault("collapsed_candidates", {})
    collapsed_meta = collapsed_candidates.get(token_id, {}) if isinstance(collapsed_candidates.get(token_id), dict) else {}
    if cur_price <= SL_INTRA_HAZARD_COLLAPSED_PRICE:
        collapsed_cycles = int(collapsed_meta.get("consecutive_cycles", 0) or 0) + 1
        collapsed_candidates[token_id] = {
            "first_seen_at": collapsed_meta.get("first_seen_at") or now.isoformat(),
            "last_seen_at": now.isoformat(),
            "consecutive_cycles": collapsed_cycles,
        }
        state_changed = True
    else:
        collapsed_cycles = 0
        if token_id in collapsed_candidates:
            collapsed_candidates.pop(token_id, None)
            state_changed = True

    tier = _sl_intra_hazard_monitor_tier(
        pct_pnl,
        cur_price,
        current_value,
        collapsed_cycles=collapsed_cycles,
    )
    if not tier:
        if state_changed:
            save_sl_intra_hazard_monitor_state(state)
        return False

    seen = state.setdefault("seen", {})
    token_seen = set(seen.get(token_id, [])) if isinstance(seen.get(token_id, []), list) else set()
    if tier in token_seen:
        if state_changed:
            save_sl_intra_hazard_monitor_state(state)
        return False

    title_full = str(position.get("title", "") or "")
    city = parse_city_from_title(title_full[:50]) or ""
    outcome = position.get("outcome", "?")
    event = {
        "timestamp": now.isoformat(),
        "token_id": token_id,
        "city": city,
        "outcome": outcome,
        "title": title_full[:120],
        "tier": tier,
        "condition": condition,
        "days_ahead": days_ahead,
        "entry_price": entry_price,
        "cur_price": cur_price,
        "pct_pnl": round(pct_pnl, 2),
        "current_value": current_value,
        "shares": float(position.get("size", 0)),
        "bot_version": BOT_VERSION,
        "monitor_version": SL_INTRA_HAZARD_MONITOR_VERSION,
        "log_only": True,
    }
    state.setdefault("events", []).append(event)
    seen[token_id] = sorted(token_seen | {tier})
    log.info(
        f"[SL-INTRA-L2] hazard {tier}: {outcome} {city} "
        f"pnl={pct_pnl:+.1f}% value=${current_value:.2f}"
    )

    if _sl_intra_hazard_telegram_allowed(state, now):
        try:
            send_telegram(
                f"⚠️ <b>[SL_intra L2 Hazard Monitor]</b>\n"
                f"{tier}: {outcome} {city}\n"
                f"PnL: <b>{pct_pnl:+.1f}%</b> | value=${current_value:.2f}\n"
                f"Entry ${float(entry_price or 0):.2f} → ahora ${cur_price:.2f}\n"
                f"<i>LOG_ONLY: no venta, no lifecycle, no accion ejecutable.</i>"
            )
            state["last_telegram_at"] = now.isoformat()
        except Exception:
            pass

    save_sl_intra_hazard_monitor_state(state)
    return True


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

    try:
        _sync_trade_lifecycle_from_sources()
    except Exception as e:
        log.warning(f"Error sincronizando trade_lifecycle: {e}")


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


def load_trade_lifecycle_data():
    """
    Capa de trazabilidad completa por posición.

    Centraliza entrada, snapshots en vida, intentos de salida, fill, cierre y
    comportamiento posterior del mercado cuando existe observación.
    """
    if os.path.exists(TRADE_LIFECYCLE_FILE):
        try:
            with open(TRADE_LIFECYCLE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("records"), list):
                return data
        except Exception:
            pass
    return {
        "generated_at": "",
        "summary": {},
        "integrity": {},
        "note": (
            "trade_lifecycle es una capa de observabilidad derivada. "
            "El histórico viejo puede tener campos reconstruidos de forma parcial "
            "si nunca se guardaron snapshots o fills más detallados."
        ),
        "records": [],
    }


def save_trade_lifecycle_data(data):
    """Guarda trade_lifecycle.json ordenado por actividad reciente."""
    payload = data if isinstance(data, dict) else {}
    records = payload.get("records", [])
    if not isinstance(records, list):
        records = []
    records.sort(
        key=lambda r: str(
            r.get("last_activity_at")
            or r.get("closed_at")
            or r.get("last_buy_at")
            or r.get("opened_at")
            or ""
        ),
        reverse=True,
    )
    payload["records"] = records
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(TRADE_LIFECYCLE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Error guardando trade_lifecycle: {e}")


def _lifecycle_clone(value):
    """Copia profunda barata para estructuras JSON-friendly."""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return value


def _lifecycle_is_empty(value):
    if value is None or value == "":
        return True
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _parse_lifecycle_timestamp(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_lifecycle_float(value, digits=4):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _normalize_trade_lifecycle_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _trade_lifecycle_market_key(entry):
    token_id = str(entry.get("token_id", "") or "").strip()
    question = _normalize_trade_lifecycle_text(entry.get("question", ""))
    city = _normalize_trade_lifecycle_text(entry.get("city", ""))
    market_date = str(entry.get("date", "") or "").strip()
    if token_id:
        return f"token:{token_id}|date:{market_date}"
    if question:
        return f"question:{question}|date:{market_date}"
    if city or market_date:
        return f"market:{city}|date:{market_date}"
    return ""


def _trade_lifecycle_position_key(entry):
    side = str(entry.get("side", "") or "").upper()
    market_key = _trade_lifecycle_market_key(entry)
    if market_key:
        return f"{market_key}|side:{side}"
    return ""


def _trade_lifecycle_entry_anchor(record):
    buys = record.get("buys", []) or []
    if buys:
        ts = str((buys[0] or {}).get("timestamp", "") or "").strip()
        if ts:
            return ts

    for context_key in ["entry_context", "latest_entry_context"]:
        context = record.get(context_key) or {}
        ts = str(context.get("timestamp", "") or "").strip()
        if not ts:
            continue
        if any(
            not _lifecycle_is_empty(context.get(field))
            for field in [
                "price",
                "amount",
                "shares",
                "forecast_max",
                "edge_pct",
                "our_prob",
                "mkt_price",
                "cycle_number",
                "logic_cycle_number",
                "trader_confirmed",
            ]
        ):
            return ts
    return ""


def _trade_lifecycle_merge_priority(record):
    entry_anchor = _trade_lifecycle_entry_anchor(record)
    buys = record.get("buys", []) or []
    timeline = record.get("timeline", []) or []
    exit_attempts = record.get("exit_attempts", []) or []
    close_context = record.get("close_context") or {}
    post_exit = record.get("post_exit_analysis") or {}
    score = 0
    if entry_anchor:
        score += 100
    score += len(buys) * 20
    score += len(timeline) * 3
    score += len(exit_attempts) * 5
    if record.get("token_id"):
        score += 8
    if record.get("question"):
        score += 6
    if close_context.get("close_action"):
        score += 4
    if post_exit.get("market_seen_after_close"):
        score += 2
    if record.get("position_key"):
        score += 1
    return (
        score,
        str(record.get("last_activity_at") or record.get("closed_at") or record.get("opened_at") or ""),
    )


def _trade_lifecycle_records_can_merge(existing, candidate):
    existing_key = existing.get("position_key") or _trade_lifecycle_position_key(existing)
    candidate_key = candidate.get("position_key") or _trade_lifecycle_position_key(candidate)
    if not existing_key or not candidate_key or existing_key != candidate_key:
        return False

    existing_anchor = _trade_lifecycle_entry_anchor(existing)
    candidate_anchor = _trade_lifecycle_entry_anchor(candidate)
    if existing_anchor and candidate_anchor:
        return existing_anchor == candidate_anchor
    return True


def _trade_lifecycle_label(record):
    question = str(record.get("question", "") or "").strip()
    if question:
        label = _parse_position_label(question, str(record.get("side", "") or "").upper())
        if label and not label.startswith("?"):
            return label
        side = str(record.get("side", "") or "").upper()
        return f"{question} [{side}]".strip()
    city = str(record.get("city", "?") or "?")
    side = str(record.get("side", "?") or "?")
    market_date = str(record.get("date", "") or "").strip()
    if market_date:
        return f"{city} {market_date} {side}"
    return f"{city} {side}".strip()


def _trade_lifecycle_record_id(entry):
    timestamp = (
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("closed_at")
        or entry.get("opened_at")
        or entry.get("last_buy_at")
        or entry.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    token_id = entry.get("token_id", "")
    city = entry.get("city", "?")
    position_key = _trade_lifecycle_position_key(entry)
    return entry.get("id") or f"{position_key or token_id or city}|{timestamp}"


def _find_trade_lifecycle_record(records, entry):
    """
    Busca el record de lifecycle más probable.

    Prioridad:
      1. id reconstruido
      2. token_id
      3. question + side
      4. city + side + date
    """
    record_id = _trade_lifecycle_record_id(entry)
    position_key = _trade_lifecycle_position_key(entry)
    token_id = entry.get("token_id", "")
    question = entry.get("question", "")
    city = entry.get("city", "")
    side = str(entry.get("side", "")).upper()
    market_date = entry.get("date", "")

    fallback_candidates = []
    close_like_action = str(entry.get("action", "") or "").upper() in {
        "SELL_PENDING",
        "SELL",
        "SELL_FAILED",
        "LOSS_TOTAL",
        "RESOLVED_WIN",
    }
    event_ts = str(
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("closed_at")
        or entry.get("timestamp")
        or ""
    ).strip()

    for record in reversed(records):
        if record_id and record.get("id") == record_id:
            return record
        if position_key and (record.get("position_key") or _trade_lifecycle_position_key(record)) == position_key:
            return record
        if token_id and record.get("token_id") == token_id:
            return record
        if question and record.get("question") == question and record.get("side") == side:
            return record
        if city and market_date and record.get("city") == city and record.get("side") == side and record.get("date") == market_date:
            return record

        if not close_like_action or token_id or question or market_date:
            continue
        if record.get("city") != city or record.get("side") != side:
            continue

        opened_at = str(
            record.get("last_buy_at")
            or record.get("opened_at")
            or _trade_lifecycle_entry_anchor(record)
            or ""
        ).strip()
        if event_ts and opened_at and opened_at > event_ts:
            continue

        closed_at = str(
            record.get("closed_at")
            or (record.get("close_context") or {}).get("timestamp")
            or ""
        ).strip()
        if closed_at and event_ts and closed_at <= event_ts:
            continue

        fallback_candidates.append(record)

    if fallback_candidates:
        fallback_candidates.sort(
            key=lambda record: (
                1 if record.get("status") in {"open", "pending_exit", "exit_failed"} else 0,
                str(
                    record.get("last_buy_at")
                    or record.get("opened_at")
                    or _trade_lifecycle_entry_anchor(record)
                    or ""
                ),
            ),
            reverse=True,
        )
        return fallback_candidates[0]
    return None


def _new_trade_lifecycle_record(entry):
    timestamp = (
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("closed_at")
        or entry.get("opened_at")
        or entry.get("last_buy_at")
        or entry.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    token_id = entry.get("token_id", "")
    city = entry.get("city", "?")
    side = str(entry.get("side", "")).upper()
    market_date = entry.get("date", "")
    record_id = _trade_lifecycle_record_id(entry)
    return {
        "id": record_id,
        "position_key": _trade_lifecycle_position_key(entry),
        "label": entry.get("question") or f"{city} {market_date} {side}".strip(),
        "token_id": token_id,
        "question": entry.get("question", ""),
        "city": city,
        "side": side,
        "date": market_date,
        "condition": entry.get("condition", ""),
        "status": entry.get("status", "open"),
        "opened_at": entry.get("opened_at") or entry.get("timestamp") or timestamp,
        "last_buy_at": entry.get("last_buy_at") or entry.get("timestamp") or timestamp,
        "closed_at": entry.get("closed_at"),
        "buy_count": int(entry.get("buy_count", 0) or 0),
        "total_amount": _to_lifecycle_float(entry.get("total_amount", 0), 2) or 0.0,
        "total_shares": _to_lifecycle_float(entry.get("total_shares", 0)) or 0.0,
        "avg_entry_price": _to_lifecycle_float(entry.get("avg_entry_price")),
        "trader_confirmed": sorted(set(entry.get("trader_confirmed", []) or [])),
        "bot_version_opened": entry.get("bot_version_opened", ""),
        "bot_version_closed": entry.get("bot_version_closed", ""),
        "entry_context": {},
        "latest_entry_context": {},
        "close_context": {},
        "buys": [],
        "timeline": [],
        "exit_attempts": [],
        "position_snapshots": [],
        "market_observations": [],
        "position_stats": {
            "max_cur_price_open": None,
            "min_cur_price_open": None,
            "max_pct_pnl_open": None,
            "min_pct_pnl_open": None,
            "max_current_value_open": None,
            "last_snapshot_at": "",
        },
        "post_exit_analysis": {
            "market_seen_after_close": False,
            "observations_after_close": 0,
            "last_price_after_close": None,
            "max_price_after_close": None,
            "min_price_after_close": None,
            "reached_98_after_close": False,
            "first_reached_98_after_close_at": "",
            "upside_left_cash_peak": None,
            "upside_left_pct_peak": None,
            "drawdown_avoided_cash_peak": None,
            "drawdown_avoided_pct_peak": None,
        },
        "history_sources": {
            "performance": False,
            "postmortem": False,
            "reconstructed": True,
        },
        "last_activity_at": timestamp,
    }


def _merge_trade_lifecycle_context(target, incoming):
    target = target if isinstance(target, dict) else {}
    incoming = incoming if isinstance(incoming, dict) else {}
    for key, value in incoming.items():
        if key == "trader_confirmed":
            merged = sorted(set(target.get(key, []) or []) | set(value or []))
            if merged:
                target[key] = merged
            continue
        if _lifecycle_is_empty(target.get(key)) and not _lifecycle_is_empty(value):
            target[key] = _lifecycle_clone(value)
    return target


def _merge_trade_lifecycle_record(target, incoming):
    if not isinstance(target, dict) or not isinstance(incoming, dict):
        return target

    def _prefer(existing, candidate):
        return existing if not _lifecycle_is_empty(existing) else candidate

    def _merge_max(existing, candidate):
        if candidate is None:
            return existing
        if existing is None:
            return candidate
        return max(existing, candidate)

    def _merge_min(existing, candidate):
        if candidate is None:
            return existing
        if existing is None:
            return candidate
        return min(existing, candidate)

    status_rank = {"open": 0, "pending_exit": 1, "exit_failed": 2, "closed": 3}
    if status_rank.get(incoming.get("status", ""), -1) > status_rank.get(target.get("status", ""), -1):
        target["status"] = incoming.get("status", target.get("status", "open"))

    for key in [
        "position_key",
        "token_id",
        "question",
        "city",
        "side",
        "date",
        "condition",
        "opened_at",
        "last_buy_at",
        "closed_at",
        "avg_entry_price",
        "bot_version_opened",
        "bot_version_closed",
        "last_activity_at",
    ]:
        target[key] = _prefer(target.get(key), incoming.get(key))

    target["buy_count"] = max(int(target.get("buy_count", 0) or 0), int(incoming.get("buy_count", 0) or 0))
    target["total_amount"] = max(
        _to_lifecycle_float(target.get("total_amount"), 2) or 0.0,
        _to_lifecycle_float(incoming.get("total_amount"), 2) or 0.0,
    )
    target["total_shares"] = max(
        _to_lifecycle_float(target.get("total_shares")) or 0.0,
        _to_lifecycle_float(incoming.get("total_shares")) or 0.0,
    )
    target["trader_confirmed"] = sorted(
        set(target.get("trader_confirmed", []) or []) | set(incoming.get("trader_confirmed", []) or [])
    )

    target["entry_context"] = _merge_trade_lifecycle_context(
        target.get("entry_context"),
        incoming.get("entry_context"),
    )
    target["latest_entry_context"] = _merge_trade_lifecycle_context(
        target.get("latest_entry_context"),
        incoming.get("latest_entry_context"),
    )
    target["close_context"] = _merge_trade_lifecycle_context(
        target.get("close_context"),
        incoming.get("close_context"),
    )

    for buy in incoming.get("buys", []) or []:
        _append_trade_lifecycle_buy(target, buy)
    for event in incoming.get("timeline", []) or []:
        _append_trade_lifecycle_event(target, event)

    attempts = target.setdefault("exit_attempts", [])
    for attempt in incoming.get("exit_attempts", []) or []:
        marker = (attempt.get("order_id", ""), attempt.get("placed_at", ""), attempt.get("reason", ""))
        existing_attempt = None
        for candidate in attempts:
            candidate_marker = (
                candidate.get("order_id", ""),
                candidate.get("placed_at", ""),
                candidate.get("reason", ""),
            )
            if candidate_marker == marker:
                existing_attempt = candidate
                break
        if existing_attempt is None:
            attempts.append(_lifecycle_clone(attempt))
        else:
            for key, value in (attempt or {}).items():
                if existing_attempt.get(key) in {None, ""} and value not in {None, ""}:
                    existing_attempt[key] = _lifecycle_clone(value)
            if existing_attempt.get("status") == "pending" and attempt.get("status") in {"filled", "failed"}:
                existing_attempt["status"] = attempt.get("status")

    for list_key, marker_keys in [
        ("position_snapshots", ["timestamp", "source", "stage", "cur_price", "current_value", "pct_pnl", "cash_pnl"]),
        ("market_observations", ["timestamp", "source", "price", "liquidity", "volume_24h", "question"]),
    ]:
        target_list = target.setdefault(list_key, [])
        known = {
            tuple(item.get(key) for key in marker_keys)
            for item in target_list
            if isinstance(item, dict)
        }
        for item in incoming.get(list_key, []) or []:
            marker = tuple(item.get(key) for key in marker_keys)
            if marker in known:
                continue
            target_list.append(_lifecycle_clone(item))
            known.add(marker)

    target_stats = target.setdefault("position_stats", {})
    incoming_stats = incoming.get("position_stats") or {}
    for key in ["max_cur_price_open", "max_pct_pnl_open", "max_current_value_open"]:
        target_stats[key] = _merge_max(target_stats.get(key), incoming_stats.get(key))
    for key in ["min_cur_price_open", "min_pct_pnl_open"]:
        target_stats[key] = _merge_min(target_stats.get(key), incoming_stats.get(key))
    last_snapshot_target = target_stats.get("last_snapshot_at", "")
    last_snapshot_incoming = incoming_stats.get("last_snapshot_at", "")
    if last_snapshot_incoming and last_snapshot_incoming > last_snapshot_target:
        target_stats["last_snapshot_at"] = last_snapshot_incoming

    target_post = target.setdefault("post_exit_analysis", {})
    incoming_post = incoming.get("post_exit_analysis") or {}
    target_post["market_seen_after_close"] = bool(
        target_post.get("market_seen_after_close") or incoming_post.get("market_seen_after_close")
    )
    target_post["observations_after_close"] = max(
        int(target_post.get("observations_after_close", 0) or 0),
        int(incoming_post.get("observations_after_close", 0) or 0),
    )
    target_post["last_price_after_close"] = _prefer(
        target_post.get("last_price_after_close"),
        incoming_post.get("last_price_after_close"),
    )
    target_post["max_price_after_close"] = _merge_max(
        target_post.get("max_price_after_close"),
        incoming_post.get("max_price_after_close"),
    )
    target_post["min_price_after_close"] = _merge_min(
        target_post.get("min_price_after_close"),
        incoming_post.get("min_price_after_close"),
    )
    target_post["reached_98_after_close"] = bool(
        target_post.get("reached_98_after_close") or incoming_post.get("reached_98_after_close")
    )
    first_hit_target = target_post.get("first_reached_98_after_close_at", "")
    first_hit_incoming = incoming_post.get("first_reached_98_after_close_at", "")
    if first_hit_incoming and (not first_hit_target or first_hit_incoming < first_hit_target):
        target_post["first_reached_98_after_close_at"] = first_hit_incoming
    for key in [
        "upside_left_cash_peak",
        "upside_left_pct_peak",
        "drawdown_avoided_cash_peak",
        "drawdown_avoided_pct_peak",
    ]:
        target_post[key] = _merge_max(target_post.get(key), incoming_post.get(key))

    target_sources = target.setdefault("history_sources", {})
    incoming_sources = incoming.get("history_sources") or {}
    for key in ["performance", "postmortem", "reconstructed"]:
        target_sources[key] = bool(target_sources.get(key) or incoming_sources.get(key))

    target["label"] = _trade_lifecycle_label(target)
    return target


def _coalesce_trade_lifecycle_records(records):
    merged_by_id = []
    merged_id_index = {}
    collisions = 0

    for record in records:
        if not isinstance(record, dict):
            continue
        candidate = _lifecycle_clone(record)
        candidate["id"] = candidate.get("id") or _trade_lifecycle_record_id(candidate)
        candidate["position_key"] = candidate.get("position_key") or _trade_lifecycle_position_key(candidate)
        record_id = candidate.get("id")
        if record_id and record_id in merged_id_index:
            _merge_trade_lifecycle_record(merged_by_id[merged_id_index[record_id]], candidate)
            collisions += 1
            continue
        if record_id:
            merged_id_index[record_id] = len(merged_by_id)
        merged_by_id.append(candidate)

    grouped = {}
    for record in merged_by_id:
        position_key = record.get("position_key") or _trade_lifecycle_position_key(record) or record.get("id")
        record["position_key"] = position_key
        grouped.setdefault(position_key, []).append(record)

    merged = []
    for group in grouped.values():
        group.sort(key=_trade_lifecycle_merge_priority, reverse=True)
        merged_group = []
        for candidate in group:
            target = None
            for existing in merged_group:
                if _trade_lifecycle_records_can_merge(existing, candidate):
                    target = existing
                    break
            if target is None:
                merged_group.append(candidate)
                continue
            _merge_trade_lifecycle_record(target, candidate)
            collisions += 1
        merged.extend(merged_group)

    for record in merged:
        record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        record["label"] = _trade_lifecycle_label(record)
    return merged, collisions


def _build_trade_lifecycle_record_integrity(record):
    token_id = str(record.get("token_id", "") or "").strip()
    question = str(record.get("question", "") or "").strip()
    total_amount = _to_lifecycle_float(record.get("total_amount"), 2) or 0.0
    total_shares = _to_lifecycle_float(record.get("total_shares")) or 0.0
    buys = record.get("buys", []) or []
    entry_context = record.get("entry_context") or {}
    close_context = record.get("close_context") or {}

    partial_historical = (
        not token_id
        and not question
        and not buys
        and not entry_context.get("timestamp")
        and abs(total_amount) < 1e-9
        and abs(total_shares) < 1e-9
    )
    close_only = not buys and bool(close_context.get("close_action"))
    return {
        "missing_token_id": not bool(token_id),
        "missing_question": not bool(question),
        "missing_entry_context": not bool(entry_context.get("timestamp")),
        "missing_buy_history": not bool(buys),
        "zero_amount": abs(total_amount) < 1e-9,
        "zero_shares": abs(total_shares) < 1e-9,
        "partial_historical_record": partial_historical,
        "close_only_record": close_only,
        "analysis_ready": not partial_historical,
    }


def _build_trade_lifecycle_integrity(records, duplicate_collisions=0):
    flags = [_build_trade_lifecycle_record_integrity(record) for record in records]
    return {
        "records_total": len(records),
        "analysis_ready_records": sum(1 for item in flags if item.get("analysis_ready")),
        "partial_historical_records": sum(1 for item in flags if item.get("partial_historical_record")),
        "close_only_records": sum(1 for item in flags if item.get("close_only_record")),
        "records_missing_token_id": sum(1 for item in flags if item.get("missing_token_id")),
        "records_missing_question": sum(1 for item in flags if item.get("missing_question")),
        "records_missing_entry_context": sum(1 for item in flags if item.get("missing_entry_context")),
        "records_without_buy_history": sum(1 for item in flags if item.get("missing_buy_history")),
        "zero_amount_records": sum(1 for item in flags if item.get("zero_amount")),
        "zero_share_records": sum(1 for item in flags if item.get("zero_shares")),
        "duplicate_id_collisions_resolved": int(duplicate_collisions or 0),
    }


def _copy_trade_lifecycle_dynamic_fields(target, existing):
    """Conserva snapshots y métricas dinámicas al re-sincronizar desde fuentes base."""
    if not isinstance(existing, dict):
        return
    for key in [
        "position_snapshots",
        "market_observations",
        "position_stats",
        "post_exit_analysis",
        "last_activity_at",
    ]:
        if key in existing:
            target[key] = _lifecycle_clone(existing.get(key))


def _timeline_event_from_entry(entry):
    return {
        "timestamp": entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("timestamp")
        or datetime.now(timezone.utc).isoformat(),
        "action": entry.get("action", ""),
        "reason": entry.get("reason", ""),
        "decision_note": entry.get("decision_note", ""),
        "decision_source": entry.get("decision_source", ""),
        "price": _to_lifecycle_float(entry.get("price")),
        "limit_price": _to_lifecycle_float(entry.get("limit_price")),
        "fill_price": _to_lifecycle_float(entry.get("fill_price")),
        "fill_value": _to_lifecycle_float(entry.get("fill_value"), 2),
        "fill_source": entry.get("fill_source", ""),
        "shares": _to_lifecycle_float(entry.get("shares")),
        "amount": _to_lifecycle_float(entry.get("amount"), 2),
        "return_est": _to_lifecycle_float(entry.get("return_est"), 2),
        "pnl_pct": _to_lifecycle_float(entry.get("pnl_pct"), 2),
        "pnl_cash": _to_lifecycle_float(entry.get("pnl_cash"), 2),
        "loss": _to_lifecycle_float(entry.get("loss"), 2),
        "forecast_max": _to_lifecycle_float(entry.get("forecast_max")),
        "edge_pct": _to_lifecycle_float(entry.get("edge_pct"), 2),
        "our_prob": _to_lifecycle_float(entry.get("our_prob"), 2),
        "mkt_price": _to_lifecycle_float(entry.get("mkt_price"), 2),
        "days_ahead": entry.get("days_ahead"),
        "order_id": entry.get("order_id", ""),
        "bot_version": entry.get("bot_version", ""),
        "source_file": "performance",
    }


def _append_trade_lifecycle_event(record, event):
    timeline = record.setdefault("timeline", [])
    marker = (
        event.get("timestamp"),
        event.get("action"),
        event.get("order_id", ""),
        event.get("price"),
        event.get("shares"),
    )
    for existing in timeline:
        existing_marker = (
            existing.get("timestamp"),
            existing.get("action"),
            existing.get("order_id", ""),
            existing.get("price"),
            existing.get("shares"),
        )
        if existing_marker == marker:
            return
    timeline.append(event)


def _append_trade_lifecycle_buy(record, entry):
    buy = {
        "timestamp": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "amount": _to_lifecycle_float(entry.get("amount"), 2),
        "shares": _to_lifecycle_float(entry.get("shares")),
        "price": _to_lifecycle_float(entry.get("price")),
        "edge_pct": _to_lifecycle_float(entry.get("edge_pct"), 2),
        "forecast_max": _to_lifecycle_float(entry.get("forecast_max")),
        "our_prob": _to_lifecycle_float(entry.get("our_prob"), 2),
        "mkt_price": _to_lifecycle_float(entry.get("mkt_price"), 2),
        "days_ahead": entry.get("days_ahead"),
        "trader_confirmed": sorted(set(entry.get("trader_confirmed", []) or [])),
        "bot_version": entry.get("bot_version", ""),
        "cycle_number": entry.get("cycle_number"),
        "logic_cycle_number": entry.get("logic_cycle_number"),
    }
    buys = record.setdefault("buys", [])
    marker = (buy.get("timestamp"), buy.get("price"), buy.get("amount"), buy.get("shares"))
    target = None
    for existing in buys:
        existing_marker = (
            existing.get("timestamp"),
            existing.get("price"),
            existing.get("amount"),
            existing.get("shares"),
        )
        if existing_marker == marker:
            target = existing
            break
    if target is None:
        buys.append(buy)
        target = buys[-1]
    else:
        for key, value in buy.items():
            if key == "trader_confirmed":
                merged_traders = sorted(set(target.get("trader_confirmed", []) or []) | set(value or []))
                if merged_traders:
                    target["trader_confirmed"] = merged_traders
                continue
            if target.get(key) in {None, ""} and value not in {None, ""}:
                target[key] = value

    buys.sort(key=lambda item: str(item.get("timestamp", "")))
    record["buy_count"] = max(int(record.get("buy_count", 0) or 0), len(buys))
    record["total_amount"] = round(sum((_to_lifecycle_float(b.get("amount"), 2) or 0.0) for b in buys), 2)
    record["total_shares"] = round(sum((_to_lifecycle_float(b.get("shares")) or 0.0) for b in buys), 4)
    if record["total_shares"] > 0:
        record["avg_entry_price"] = round(record["total_amount"] / record["total_shares"], 4)
    traders = sorted(set(record.get("trader_confirmed", []) or []) | set(target.get("trader_confirmed", []) or []))
    if traders:
        record["trader_confirmed"] = traders

    first_buy = buys[0]
    last_buy = buys[-1]
    record["opened_at"] = record.get("opened_at") or first_buy.get("timestamp")
    record["last_buy_at"] = last_buy.get("timestamp") or record.get("last_buy_at")
    record["entry_context"] = {
        "timestamp": first_buy.get("timestamp"),
        "price": first_buy.get("price"),
        "amount": first_buy.get("amount"),
        "shares": first_buy.get("shares"),
        "days_ahead": first_buy.get("days_ahead"),
        "forecast_max": first_buy.get("forecast_max"),
        "edge_pct": first_buy.get("edge_pct"),
        "our_prob": first_buy.get("our_prob"),
        "mkt_price": first_buy.get("mkt_price"),
        "trader_confirmed": first_buy.get("trader_confirmed", []),
        "bot_version": first_buy.get("bot_version", ""),
        "cycle_number": first_buy.get("cycle_number"),
        "logic_cycle_number": first_buy.get("logic_cycle_number"),
    }
    record["latest_entry_context"] = {
        "timestamp": last_buy.get("timestamp"),
        "price": last_buy.get("price"),
        "amount": last_buy.get("amount"),
        "shares": last_buy.get("shares"),
        "days_ahead": last_buy.get("days_ahead"),
        "forecast_max": last_buy.get("forecast_max"),
        "edge_pct": last_buy.get("edge_pct"),
        "our_prob": last_buy.get("our_prob"),
        "mkt_price": last_buy.get("mkt_price"),
        "trader_confirmed": last_buy.get("trader_confirmed", []),
        "bot_version": last_buy.get("bot_version", ""),
        "cycle_number": last_buy.get("cycle_number"),
        "logic_cycle_number": last_buy.get("logic_cycle_number"),
    }


def _append_trade_lifecycle_exit_attempt(record, entry):
    attempts = record.setdefault("exit_attempts", [])
    attempt = {
        "order_id": entry.get("order_id", ""),
        "status": "pending",
        "placed_at": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "confirmed_at": "",
        "failed_at": "",
        "reason": entry.get("reason", ""),
        "decision_note": entry.get("decision_note", ""),
        "decision_source": entry.get("decision_source", ""),
        "limit_price": _to_lifecycle_float(entry.get("limit_price", entry.get("price"))),
        "trigger_price": _to_lifecycle_float(entry.get("trigger_price")),
        "shares": _to_lifecycle_float(entry.get("shares")),
        "fill_price": _to_lifecycle_float(entry.get("fill_price")),
        "fill_shares": _to_lifecycle_float(entry.get("fill_shares")),
        "fill_value": _to_lifecycle_float(entry.get("fill_value"), 2),
        "fill_source": entry.get("fill_source", ""),
        "fill_count": entry.get("fill_count"),
        "return_est": _to_lifecycle_float(entry.get("return_est"), 2),
        "pnl_pct": _to_lifecycle_float(entry.get("pnl_pct"), 2),
        "pnl_cash": _to_lifecycle_float(entry.get("pnl_cash"), 2),
        "current_value": _to_lifecycle_float(entry.get("current_value"), 2),
        "bot_version": entry.get("bot_version", ""),
    }
    marker = (attempt.get("order_id"), attempt.get("placed_at"), attempt.get("reason"))
    target = None
    for existing in attempts:
        existing_marker = (
            existing.get("order_id"),
            existing.get("placed_at"),
            existing.get("reason"),
        )
        if existing_marker == marker:
            target = existing
            break
    if target is None:
        attempts.append(attempt)
    else:
        for key, value in attempt.items():
            if target.get(key) in {None, ""} and value not in {None, ""}:
                target[key] = value


def _update_trade_lifecycle_exit_attempt(record, entry, status):
    order_id = entry.get("order_id", "")
    attempts = record.setdefault("exit_attempts", [])
    target = None
    for attempt in reversed(attempts):
        if order_id and attempt.get("order_id") == order_id:
            target = attempt
            break
    if target is None:
        _append_trade_lifecycle_exit_attempt(record, entry)
        target = attempts[-1]
    target["status"] = status
    if status == "filled":
        target["confirmed_at"] = entry.get("fill_confirmed") or entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
        for key in ["fill_price", "fill_shares", "fill_value", "fill_source", "fill_count"]:
            value = entry.get(key)
            if value not in {None, ""}:
                target[key] = value
    elif status == "failed":
        target["failed_at"] = entry.get("failed_at") or entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
        target["fail_reason"] = entry.get("fail_reason", "")


def _apply_trade_lifecycle_close(record, entry):
    timestamp = (
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("closed_at")
        or entry.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    action = entry.get("action", "")
    if action == "SELL_FAILED":
        record["status"] = "exit_failed"
    elif action in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}:
        record["status"] = "closed"
        record["closed_at"] = timestamp

    record["close_context"] = {
        "close_action": action or record.get("close_context", {}).get("close_action", ""),
        "close_reason": entry.get("reason", record.get("close_context", {}).get("close_reason", "")),
        "close_subtype": entry.get("reason", record.get("close_context", {}).get("close_subtype", "")),
        "close_price": _to_lifecycle_float(entry.get("fill_price", entry.get("price", entry.get("cur_price")))),
        "close_shares": _to_lifecycle_float(entry.get("fill_shares", entry.get("shares", record.get("total_shares")))),
        "return_est": _to_lifecycle_float(entry.get("fill_value", entry.get("return_est", entry.get("payout_est"))), 2),
        "pnl_cash": _to_lifecycle_float(entry.get("pnl_cash", entry.get("loss")), 2),
        "pnl_pct": _to_lifecycle_float(entry.get("pnl_pct"), 2),
        "order_id": entry.get("order_id", ""),
        "timestamp": timestamp,
        "bot_version": entry.get("bot_version", ""),
    }
    if entry.get("limit_price") is not None:
        record["close_context"]["limit_price"] = _to_lifecycle_float(entry.get("limit_price"))
    if entry.get("fill_source"):
        record["close_context"]["fill_source"] = entry.get("fill_source", "")
    if action == "SELL":
        _update_trade_lifecycle_exit_attempt(record, entry, "filled")
    elif action == "SELL_FAILED":
        _update_trade_lifecycle_exit_attempt(record, entry, "failed")


def _append_synthetic_postmortem_close_event(record, postmortem_record):
    action = postmortem_record.get("close_action", "")
    if not action:
        return
    close_ts = postmortem_record.get("closed_at") or ""
    for event in record.get("timeline", []):
        if event.get("action") == action and event.get("timestamp") == close_ts:
            return
    event = {
        "timestamp": close_ts or datetime.now(timezone.utc).isoformat(),
        "action": action,
        "reason": postmortem_record.get("close_reason", ""),
        "decision_note": "",
        "decision_source": "postmortem_sync",
        "price": _to_lifecycle_float(postmortem_record.get("close_price")),
        "shares": _to_lifecycle_float(postmortem_record.get("close_shares")),
        "amount": None,
        "return_est": _to_lifecycle_float(postmortem_record.get("return_est"), 2),
        "pnl_pct": _to_lifecycle_float(postmortem_record.get("pnl_pct"), 2),
        "pnl_cash": _to_lifecycle_float(postmortem_record.get("pnl_cash"), 2),
        "loss": None,
        "forecast_max": None,
        "edge_pct": None,
        "our_prob": None,
        "mkt_price": None,
        "days_ahead": None,
        "order_id": postmortem_record.get("order_id", ""),
        "bot_version": postmortem_record.get("bot_version_closed", ""),
        "source_file": "postmortem",
    }
    _append_trade_lifecycle_event(record, event)


def _build_trade_lifecycle_summary(records):
    closed = [r for r in records if r.get("status") == "closed"]
    pending = [r for r in records if r.get("status") == "pending_exit"]
    exit_failed = [r for r in records if r.get("status") == "exit_failed"]
    open_records = [r for r in records if r.get("status") == "open"]

    def _close_reason(record):
        return str((record.get("close_context") or {}).get("close_reason", "") or "")

    take_profit = [r for r in closed if _close_reason(r) in {"take_profit", "take_profit_intra"}]
    stop_loss = [r for r in closed if _close_reason(r) in {"stop_loss", "stop_loss_intra"}]
    reeval = [r for r in closed if _close_reason(r) == "reeval"]
    resolved = [r for r in closed if (r.get("close_context") or {}).get("close_action", "") == "RESOLVED_WIN"]
    loss_total = [r for r in closed if (r.get("close_context") or {}).get("close_action", "") == "LOSS_TOTAL"]

    top_upside_left = []
    for record in closed:
        post_exit = record.get("post_exit_analysis") or {}
        upside_cash = _to_lifecycle_float(post_exit.get("upside_left_cash_peak"), 2)
        max_after = _to_lifecycle_float(post_exit.get("max_price_after_close"))
        close_price = _to_lifecycle_float((record.get("close_context") or {}).get("close_price"))
        if upside_cash is None or upside_cash <= 0 or max_after is None or close_price is None:
            continue
        top_upside_left.append({
            "label": _trade_lifecycle_label(record),
            "closed_at": record.get("closed_at", ""),
            "close_reason": _close_reason(record),
            "close_price": close_price,
            "max_price_after_close": max_after,
            "upside_left_cash_peak": upside_cash,
            "upside_left_pct_peak": _to_lifecycle_float(post_exit.get("upside_left_pct_peak"), 2),
        })

    top_upside_left.sort(key=lambda item: float(item.get("upside_left_cash_peak", 0) or 0), reverse=True)

    return {
        "tracked_positions": len(records),
        "open_positions": len(open_records),
        "pending_exit_positions": len(pending),
        "exit_failed_positions": len(exit_failed),
        "closed_positions": len(closed),
        "take_profit_closes": len(take_profit),
        "stop_loss_closes": len(stop_loss),
        "reeval_closes": len(reeval),
        "resolved_wins": len(resolved),
        "loss_totals": len(loss_total),
        "with_market_data_after_close": sum(
            1 for r in closed if bool((r.get("post_exit_analysis") or {}).get("market_seen_after_close"))
        ),
        "with_upside_left_after_close": len(top_upside_left),
        "top_upside_left": top_upside_left[:10],
    }


def _sync_trade_lifecycle_from_sources():
    """
    Reconstruye trade_lifecycle.json desde performance + postmortem
    preservando snapshots dinámicos ya observados.
    """
    existing = load_trade_lifecycle_data()
    existing_records = existing.get("records", []) if isinstance(existing, dict) else []
    existing_records, existing_duplicate_collisions = _coalesce_trade_lifecycle_records(existing_records)
    existing_map = {
        record.get("id"): record
        for record in existing_records
        if isinstance(record, dict) and record.get("id")
    }

    postmortem_records = load_postmortem_data()
    records = []
    record_by_id = {}

    for pm in postmortem_records:
        record = _new_trade_lifecycle_record(pm)
        record["status"] = pm.get("status", record.get("status", "open"))
        record["opened_at"] = pm.get("opened_at") or record.get("opened_at")
        record["last_buy_at"] = pm.get("last_buy_at") or record.get("last_buy_at")
        record["closed_at"] = pm.get("closed_at")
        record["buy_count"] = int(pm.get("buy_count", 0) or 0)
        record["total_amount"] = _to_lifecycle_float(pm.get("total_amount"), 2) or 0.0
        record["total_shares"] = _to_lifecycle_float(pm.get("total_shares")) or 0.0
        record["avg_entry_price"] = _to_lifecycle_float(pm.get("avg_entry_price"))
        record["trader_confirmed"] = sorted(set(pm.get("trader_confirmed", []) or []))
        record["bot_version_opened"] = pm.get("bot_version_opened", "")
        record["bot_version_closed"] = pm.get("bot_version_closed", "")
        record["buys"] = _lifecycle_clone(pm.get("buys", []) or [])
        if record["buys"]:
            record["buys"].sort(key=lambda item: str(item.get("timestamp", "")))
            first_buy = record["buys"][0]
            last_buy = record["buys"][-1]
            record["entry_context"] = {
                "timestamp": first_buy.get("timestamp"),
                "price": _to_lifecycle_float(first_buy.get("price")),
                "amount": _to_lifecycle_float(first_buy.get("amount"), 2),
                "shares": _to_lifecycle_float(first_buy.get("shares")),
                "days_ahead": first_buy.get("days_ahead"),
                "forecast_max": _to_lifecycle_float(first_buy.get("forecast_max")),
                "edge_pct": _to_lifecycle_float(first_buy.get("edge_pct"), 2),
                "our_prob": _to_lifecycle_float(first_buy.get("our_prob"), 2),
                "mkt_price": _to_lifecycle_float(first_buy.get("mkt_price"), 2),
                "trader_confirmed": first_buy.get("trader_confirmed", []),
                "bot_version": first_buy.get("bot_version", ""),
                "cycle_number": first_buy.get("cycle_number"),
                "logic_cycle_number": first_buy.get("logic_cycle_number"),
            }
            record["latest_entry_context"] = {
                "timestamp": last_buy.get("timestamp"),
                "price": _to_lifecycle_float(last_buy.get("price")),
                "amount": _to_lifecycle_float(last_buy.get("amount"), 2),
                "shares": _to_lifecycle_float(last_buy.get("shares")),
                "days_ahead": last_buy.get("days_ahead"),
                "forecast_max": _to_lifecycle_float(last_buy.get("forecast_max")),
                "edge_pct": _to_lifecycle_float(last_buy.get("edge_pct"), 2),
                "our_prob": _to_lifecycle_float(last_buy.get("our_prob"), 2),
                "mkt_price": _to_lifecycle_float(last_buy.get("mkt_price"), 2),
                "trader_confirmed": last_buy.get("trader_confirmed", []),
                "bot_version": last_buy.get("bot_version", ""),
                "cycle_number": last_buy.get("cycle_number"),
                "logic_cycle_number": last_buy.get("logic_cycle_number"),
            }
        record["close_context"] = {
            "close_action": pm.get("close_action", ""),
            "close_reason": pm.get("close_reason", ""),
            "close_subtype": pm.get("close_subtype", ""),
            "close_price": _to_lifecycle_float(pm.get("close_price")),
            "close_shares": _to_lifecycle_float(pm.get("close_shares")),
            "return_est": _to_lifecycle_float(pm.get("return_est"), 2),
            "pnl_cash": _to_lifecycle_float(pm.get("pnl_cash"), 2),
            "pnl_pct": _to_lifecycle_float(pm.get("pnl_pct"), 2),
            "order_id": pm.get("order_id", ""),
            "timestamp": pm.get("closed_at", ""),
            "bot_version": pm.get("bot_version_closed", ""),
        }
        if pm.get("limit_price") is not None:
            record["close_context"]["limit_price"] = _to_lifecycle_float(pm.get("limit_price"))
        if pm.get("fill_source"):
            record["close_context"]["fill_source"] = pm.get("fill_source")
        pending_exit = pm.get("pending_exit") or {}
        if isinstance(pending_exit, dict) and pending_exit:
            record["exit_attempts"].append({
                "order_id": pending_exit.get("order_id", ""),
                "status": "pending",
                "placed_at": pending_exit.get("timestamp", ""),
                "confirmed_at": "",
                "failed_at": "",
                "reason": pending_exit.get("reason", ""),
                "decision_note": "",
                "decision_source": "postmortem",
                "limit_price": _to_lifecycle_float(pending_exit.get("price")),
                "trigger_price": None,
                "shares": _to_lifecycle_float(pending_exit.get("shares")),
                "return_est": _to_lifecycle_float(pending_exit.get("return_est"), 2),
                "pnl_pct": _to_lifecycle_float(pending_exit.get("pnl_pct"), 2),
                "pnl_cash": _to_lifecycle_float(pending_exit.get("pnl_cash"), 2),
                "current_value": None,
                "bot_version": pm.get("bot_version_opened", ""),
            })
        record["history_sources"]["postmortem"] = True
        _copy_trade_lifecycle_dynamic_fields(record, existing_map.get(record.get("id")))
        record["label"] = _trade_lifecycle_label(record)
        records.append(record)
        record_by_id[record["id"]] = record

    replayable = {"BUY", "SELL_PENDING", "SELL", "SELL_FAILED", "LOSS_TOTAL", "RESOLVED_WIN"}
    history = sorted(
        load_performance_history(),
        key=lambda item: str(
            item.get("fill_confirmed")
            or item.get("failed_at")
            or item.get("timestamp")
            or ""
        ),
    )
    for entry in history:
        if entry.get("action") not in replayable:
            continue
        record = _find_trade_lifecycle_record(records, entry)
        if record is None:
            record = _new_trade_lifecycle_record(entry)
            _copy_trade_lifecycle_dynamic_fields(record, existing_map.get(record.get("id")))
            record["label"] = _trade_lifecycle_label(record)
            records.append(record)
            record_by_id[record["id"]] = record

        record["token_id"] = entry.get("token_id") or record.get("token_id", "")
        record["question"] = entry.get("question") or record.get("question", "")
        record["city"] = entry.get("city") or record.get("city", "?")
        record["side"] = str(entry.get("side", "")).upper() or record.get("side", "")
        record["date"] = entry.get("date") or record.get("date", "")
        record["condition"] = entry.get("condition") or record.get("condition", "")
        record["label"] = _trade_lifecycle_label(record)
        record["history_sources"]["performance"] = True
        record["last_activity_at"] = (
            entry.get("fill_confirmed")
            or entry.get("failed_at")
            or entry.get("timestamp")
            or record.get("last_activity_at", "")
        )

        event = _timeline_event_from_entry(entry)
        _append_trade_lifecycle_event(record, event)

        action = entry.get("action")
        if action == "BUY":
            record["status"] = "open"
            record["bot_version_opened"] = entry.get("bot_version", record.get("bot_version_opened", ""))
            _append_trade_lifecycle_buy(record, entry)
        elif action == "SELL_PENDING":
            record["status"] = "pending_exit"
            _append_trade_lifecycle_exit_attempt(record, entry)
        else:
            if action == "SELL_FAILED":
                _update_trade_lifecycle_exit_attempt(record, entry, "failed")
            elif action == "SELL":
                _update_trade_lifecycle_exit_attempt(record, entry, "filled")
            _apply_trade_lifecycle_close(record, entry)
            if action == "SELL_FAILED":
                record["status"] = "exit_failed"
            if action in {"LOSS_TOTAL", "RESOLVED_WIN"}:
                record["status"] = "closed"
                record["closed_at"] = event.get("timestamp") or record.get("closed_at")

    for pm in postmortem_records:
        record = record_by_id.get(pm.get("id"))
        if not record:
            continue
        _append_synthetic_postmortem_close_event(record, pm)
        status_rank = {"open": 0, "pending_exit": 1, "exit_failed": 2, "closed": 3}
        pm_status = pm.get("status", record.get("status", "open"))
        if status_rank.get(pm_status, -1) > status_rank.get(record.get("status", ""), -1):
            record["status"] = pm_status
        record["opened_at"] = pm.get("opened_at") or record.get("opened_at")
        record["last_buy_at"] = pm.get("last_buy_at") or record.get("last_buy_at")
        record["closed_at"] = pm.get("closed_at") or record.get("closed_at")
        if pm.get("bot_version_closed"):
            record["bot_version_closed"] = pm.get("bot_version_closed")
        if pm.get("close_action"):
            record["close_context"] = {
                "close_action": pm.get("close_action", ""),
                "close_reason": pm.get("close_reason", ""),
                "close_subtype": pm.get("close_subtype", ""),
                "close_price": _to_lifecycle_float(pm.get("close_price")),
                "close_shares": _to_lifecycle_float(pm.get("close_shares")),
                "return_est": _to_lifecycle_float(pm.get("return_est"), 2),
                "pnl_cash": _to_lifecycle_float(pm.get("pnl_cash"), 2),
                "pnl_pct": _to_lifecycle_float(pm.get("pnl_pct"), 2),
                "order_id": pm.get("order_id", ""),
                "timestamp": pm.get("closed_at", ""),
                "bot_version": pm.get("bot_version_closed", ""),
            }
            if pm.get("limit_price") is not None:
                record["close_context"]["limit_price"] = _to_lifecycle_float(pm.get("limit_price"))
            if pm.get("fill_source"):
                record["close_context"]["fill_source"] = pm.get("fill_source")
        if not record.get("last_activity_at"):
            record["last_activity_at"] = (
                record.get("closed_at")
                or record.get("last_buy_at")
                or record.get("opened_at")
                or ""
            )

    records, built_duplicate_collisions = _coalesce_trade_lifecycle_records(records)
    for record in records:
        record["timeline"].sort(key=lambda item: str(item.get("timestamp", "")))
        record["exit_attempts"].sort(key=lambda item: str(item.get("placed_at", "")))
        if not record.get("entry_context") and record.get("buys"):
            first_buy = sorted(record["buys"], key=lambda item: str(item.get("timestamp", "")))[0]
            record["entry_context"] = {
                "timestamp": first_buy.get("timestamp"),
                "price": _to_lifecycle_float(first_buy.get("price")),
                "amount": _to_lifecycle_float(first_buy.get("amount"), 2),
                "shares": _to_lifecycle_float(first_buy.get("shares")),
                "days_ahead": first_buy.get("days_ahead"),
                "forecast_max": _to_lifecycle_float(first_buy.get("forecast_max")),
                "edge_pct": _to_lifecycle_float(first_buy.get("edge_pct"), 2),
                "our_prob": _to_lifecycle_float(first_buy.get("our_prob"), 2),
                "mkt_price": _to_lifecycle_float(first_buy.get("mkt_price"), 2),
                "trader_confirmed": first_buy.get("trader_confirmed", []),
                "bot_version": first_buy.get("bot_version", ""),
                "cycle_number": first_buy.get("cycle_number"),
                "logic_cycle_number": first_buy.get("logic_cycle_number"),
            }
        record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        record["label"] = _trade_lifecycle_label(record)

    duplicate_collisions = existing_duplicate_collisions + built_duplicate_collisions
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "trade_lifecycle centraliza entrada, snapshots, intentos de salida, fill y "
            "comportamiento posterior del mercado. Los registros viejos pueden estar "
            "reconstruidos parcialmente si faltan snapshots históricos."
        ),
        "summary": _build_trade_lifecycle_summary(records),
        "integrity": _build_trade_lifecycle_integrity(records, duplicate_collisions=duplicate_collisions),
        "records": records,
    }
    save_trade_lifecycle_data(payload)
    return payload


def record_trade_lifecycle_position_snapshots(positions, source="manage_positions", stage="cycle_check"):
    """Añade snapshots de posiciones vivas para análisis posterior de exits y hold."""
    if not positions:
        return

    data = load_trade_lifecycle_data()
    records = data.get("records", [])
    if not records:
        return

    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()
    for pos in positions:
        title_full = pos.get("title", "")
        if not re.search(r"temperature", title_full, re.IGNORECASE):
            continue

        parsed = parse_temperature_question(title_full)
        market_date = date_text_to_iso(parsed["date_str"]) if parsed and parsed.get("date_str") else ""
        entry = {
            "token_id": pos.get("asset", ""),
            "question": title_full,
            "city": parse_city_from_title(title_full),
            "side": pos.get("outcome", "?"),
            "date": market_date,
        }
        record = _find_trade_lifecycle_record(records, entry)
        if record is None:
            continue

        snapshot = {
            "timestamp": now_iso,
            "source": source,
            "stage": stage,
            "cur_price": _to_lifecycle_float(pos.get("curPrice")),
            "current_value": _to_lifecycle_float(pos.get("currentValue"), 2),
            "pct_pnl": _to_lifecycle_float(pos.get("percentPnl"), 2),
            "cash_pnl": _to_lifecycle_float(pos.get("cashPnl"), 2),
            "size": _to_lifecycle_float(pos.get("size")),
            "avg_price": _to_lifecycle_float(pos.get("avgPrice")),
            "outcome": pos.get("outcome", "?"),
        }

        last_snapshot = record.get("position_snapshots", [])[-1] if record.get("position_snapshots") else None
        if last_snapshot and all(
            last_snapshot.get(key) == snapshot.get(key)
            for key in ["source", "stage", "cur_price", "current_value", "pct_pnl", "cash_pnl", "size", "avg_price"]
        ):
            continue

        record.setdefault("position_snapshots", []).append(snapshot)
        stats = record.setdefault("position_stats", {})
        cur_price = snapshot.get("cur_price")
        pct_pnl = snapshot.get("pct_pnl")
        current_value = snapshot.get("current_value")
        if cur_price is not None:
            stats["max_cur_price_open"] = cur_price if stats.get("max_cur_price_open") is None else max(stats.get("max_cur_price_open"), cur_price)
            stats["min_cur_price_open"] = cur_price if stats.get("min_cur_price_open") is None else min(stats.get("min_cur_price_open"), cur_price)
        if pct_pnl is not None:
            stats["max_pct_pnl_open"] = pct_pnl if stats.get("max_pct_pnl_open") is None else max(stats.get("max_pct_pnl_open"), pct_pnl)
            stats["min_pct_pnl_open"] = pct_pnl if stats.get("min_pct_pnl_open") is None else min(stats.get("min_pct_pnl_open"), pct_pnl)
        if current_value is not None:
            stats["max_current_value_open"] = current_value if stats.get("max_current_value_open") is None else max(stats.get("max_current_value_open"), current_value)
        stats["last_snapshot_at"] = now_iso
        record["last_activity_at"] = now_iso
        changed = True

    if changed:
        for record in records:
            record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        data["summary"] = _build_trade_lifecycle_summary(records)
        data["integrity"] = _build_trade_lifecycle_integrity(
            records,
            duplicate_collisions=(data.get("integrity") or {}).get("duplicate_id_collisions_resolved", 0),
        )
        save_trade_lifecycle_data(data)


def record_trade_lifecycle_market_observations(markets, source="cycle_market_scan"):
    """Añade observaciones de precio de mercado para posiciones abiertas y ya cerradas."""
    if not markets:
        return

    data = load_trade_lifecycle_data()
    records = data.get("records", [])
    if not records:
        return

    token_map = {}
    for market in markets:
        prices_raw = market.get("outcomePrices", "[]")
        clob_ids_raw = market.get("clobTokenIds", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        except (json.JSONDecodeError, TypeError):
            prices = []
        try:
            clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        except (json.JSONDecodeError, TypeError):
            clob_ids = []
        if not prices or len(prices) < 2 or not clob_ids or len(clob_ids) < 2:
            continue
        question = market.get("question", "")
        meta = {
            "question": question,
            "liquidity": _to_lifecycle_float(market.get("liquidity"), 2),
            "volume_24h": _to_lifecycle_float(market.get("volume24hr"), 2),
        }
        token_map[clob_ids[0]] = dict(meta, price=_to_lifecycle_float(prices[0]))
        token_map[clob_ids[1]] = dict(meta, price=_to_lifecycle_float(prices[1]))

    if not token_map:
        return

    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = _parse_lifecycle_timestamp(now_iso)
    for record in records:
        token_id = record.get("token_id", "")
        if not token_id or token_id not in token_map:
            continue
        info = token_map[token_id]
        observation = {
            "timestamp": now_iso,
            "source": source,
            "price": info.get("price"),
            "liquidity": info.get("liquidity"),
            "volume_24h": info.get("volume_24h"),
            "question": info.get("question", ""),
        }
        last_observation = record.get("market_observations", [])[-1] if record.get("market_observations") else None
        if last_observation and all(
            last_observation.get(key) == observation.get(key)
            for key in ["source", "price", "liquidity", "volume_24h", "question"]
        ):
            continue

        record.setdefault("market_observations", []).append(observation)
        record["last_activity_at"] = now_iso
        changed = True

        close_context = record.get("close_context") or {}
        close_dt = _parse_lifecycle_timestamp(close_context.get("timestamp") or record.get("closed_at"))
        price = observation.get("price")
        if close_dt and now_dt and now_dt >= close_dt and price is not None:
            post_exit = record.setdefault("post_exit_analysis", {})
            post_exit["market_seen_after_close"] = True
            post_exit["observations_after_close"] = int(post_exit.get("observations_after_close", 0) or 0) + 1
            post_exit["last_price_after_close"] = price
            post_exit["max_price_after_close"] = price if post_exit.get("max_price_after_close") is None else max(post_exit.get("max_price_after_close"), price)
            post_exit["min_price_after_close"] = price if post_exit.get("min_price_after_close") is None else min(post_exit.get("min_price_after_close"), price)
            if price >= 0.98 and not post_exit.get("reached_98_after_close"):
                post_exit["reached_98_after_close"] = True
                post_exit["first_reached_98_after_close_at"] = now_iso

            close_price = _to_lifecycle_float(close_context.get("close_price"))
            close_shares = _to_lifecycle_float(close_context.get("close_shares"))
            if close_price is not None and close_shares and close_shares > 0:
                max_after = post_exit.get("max_price_after_close")
                min_after = post_exit.get("min_price_after_close")
                if max_after is not None and max_after > close_price:
                    post_exit["upside_left_cash_peak"] = round((max_after - close_price) * close_shares, 2)
                    if close_price > 0:
                        post_exit["upside_left_pct_peak"] = round((max_after / close_price - 1.0) * 100, 2)
                if min_after is not None and min_after < close_price:
                    post_exit["drawdown_avoided_cash_peak"] = round((close_price - min_after) * close_shares, 2)
                    if close_price > 0:
                        post_exit["drawdown_avoided_pct_peak"] = round((1.0 - (min_after / close_price)) * 100, 2)

    if changed:
        for record in records:
            record["integrity"] = _build_trade_lifecycle_record_integrity(record)
        data["summary"] = _build_trade_lifecycle_summary(records)
        data["integrity"] = _build_trade_lifecycle_integrity(
            records,
            duplicate_collisions=(data.get("integrity") or {}).get("duplicate_id_collisions_resolved", 0),
        )
        save_trade_lifecycle_data(data)


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

    fallback_candidates = []
    close_like_action = str(entry.get("action", "") or "").upper() in {
        "SELL_PENDING",
        "SELL",
        "SELL_FAILED",
        "LOSS_TOTAL",
        "RESOLVED_WIN",
    }
    event_ts = str(
        entry.get("fill_confirmed")
        or entry.get("failed_at")
        or entry.get("closed_at")
        or entry.get("timestamp")
        or ""
    ).strip()

    for record in reversed(records):
        if record.get("status") not in open_statuses:
            continue
        if token_id and record.get("token_id") == token_id:
            return record
        if question and record.get("question") == question and record.get("side") == side:
            return record
        if city and market_date and record.get("city") == city and record.get("side") == side and record.get("date") == market_date:
            return record

        if not close_like_action or token_id or question or market_date:
            continue
        if record.get("city") != city or record.get("side") != side:
            continue

        opened_at = str(record.get("last_buy_at") or record.get("opened_at") or "").strip()
        if event_ts and opened_at and opened_at > event_ts:
            continue

        fallback_candidates.append(record)

    if fallback_candidates:
        fallback_candidates.sort(
            key=lambda record: str(record.get("last_buy_at") or record.get("opened_at") or ""),
            reverse=True,
        )
        return fallback_candidates[0]
    return None


def _find_postmortem_by_position_key(records, entry, close_action=None):
    position_key = _trade_lifecycle_position_key(entry)
    if not position_key:
        return None

    for record in reversed(records):
        record_key = record.get("position_key") or _trade_lifecycle_position_key(record)
        if record_key != position_key:
            continue
        if close_action and record.get("close_action") != close_action:
            continue
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
    match_entry = dict(entry or {})
    match_entry["action"] = action
    record = _find_open_postmortem(records, match_entry)

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
                "position_key": _trade_lifecycle_position_key(entry),
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
        record["position_key"] = record.get("position_key") or _trade_lifecycle_position_key(entry)
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
                "position_key": _trade_lifecycle_position_key(entry),
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
        record["position_key"] = record.get("position_key") or _trade_lifecycle_position_key(entry)
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
                "position_key": _trade_lifecycle_position_key(entry),
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
        record["position_key"] = record.get("position_key") or _trade_lifecycle_position_key(entry)
        record.pop("pending_exit", None)
        record["last_exit_failed"] = {
            "timestamp": timestamp,
            "reason": entry.get("fail_reason", entry.get("reason")),
            "order_id": entry.get("order_id"),
        }

    else:
        if record is None and action in {"LOSS_TOTAL", "RESOLVED_WIN"}:
            duplicate_closed = _find_postmortem_by_position_key(records, entry, close_action=action)
            if duplicate_closed is not None:
                return

        if record is None:
            record = {
                "id": f"{token_id or city}|{side}|{market_date}|{timestamp}",
                "position_key": _trade_lifecycle_position_key(entry),
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
        record["position_key"] = record.get("position_key") or _trade_lifecycle_position_key(entry)
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
        if entry.get("limit_price") is not None:
            record["limit_price"] = entry.get("limit_price")
        if entry.get("fill_price") is not None:
            record["fill_price"] = entry.get("fill_price")
        if entry.get("fill_value") is not None:
            record["fill_value"] = entry.get("fill_value")
        if entry.get("fill_source"):
            record["fill_source"] = entry.get("fill_source")
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
    """Calcula win rate y PnL por ciudad desde postmortem.json cerrados.

    Respeta CITY_STATS_CUTOFF: trades cerrados antes de la fecha de corte
    por ciudad se excluyen del cálculo (el historial en postmortem.json
    no se modifica; solo cambia qué trades cuentan para métricas de auto-block).
    """
    records = load_postmortem_data()
    closed = [r for r in records if r.get("status") == "closed"
              and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
              and r.get("city")]

    cities = {}
    for r in closed:
        city = r["city"]
        cutoff = CITY_STATS_CUTOFF.get(city)
        if cutoff and (r.get("closed_at") or "")[:10] < cutoff:
            continue  # trade anterior al reset — excluido de métricas
        if city not in cities:
            cities[city] = {"trades": 0, "wins": 0, "pnl": 0.0}
        cities[city]["trades"] += 1
        if (r.get("pnl_cash") or 0) > 0:
            cities[city]["wins"] += 1
        cities[city]["pnl"] += r.get("pnl_cash", 0) or 0

    for city, data in cities.items():
        data["win_rate"] = round(data["wins"] / data["trades"] * 100, 1) if data["trades"] > 0 else 0.0

    return cities


def get_city_policy_metrics(audit=None):
    """
    Separa el historico por ciudad entre:
    - total cerrado
    - NOAA-verificado (join city+date contra observed_vs_forecast)
    - legacy/no verificado

    La policy debe evitar decisiones fuertes basadas solo en eras pre-NOAA-verificado.
    """
    if audit is None:
        audit = load_audit_data()

    verified_keys = set()
    for raw in audit.get(OBSERVED_AUDIT_KEY, []):
        if not isinstance(raw, dict) or raw.get("source") != "noaa_ncei":
            continue
        city = str(raw.get("city") or "").strip()
        market_date = str(raw.get("date") or "").strip()[:10]
        if city and market_date:
            verified_keys.add((city, market_date))

    records = load_postmortem_data()
    closed = [
        r for r in records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("city")
    ]

    cities = {}

    def _bucket_stats():
        return {"trades": 0, "wins": 0, "pnl": 0.0}

    def _append_trade(stats, record):
        stats["trades"] += 1
        if (record.get("pnl_cash") or 0) > 0:
            stats["wins"] += 1
        stats["pnl"] += record.get("pnl_cash", 0) or 0

    for r in closed:
        city = r["city"]
        cutoff = CITY_STATS_CUTOFF.get(city)
        if cutoff and (r.get("closed_at") or "")[:10] < cutoff:
            continue

        city_stats = cities.setdefault(city, {
            "total": _bucket_stats(),
            "verified": _bucket_stats(),
            "legacy": _bucket_stats(),
        })
        _append_trade(city_stats["total"], r)

        market_date = str(r.get("date") or "").strip()[:10]
        target_bucket = "verified" if (city, market_date) in verified_keys else "legacy"
        _append_trade(city_stats[target_bucket], r)

    for city, buckets in cities.items():
        total = buckets["total"]
        verified = buckets["verified"]
        legacy = buckets["legacy"]
        for stats in (total, verified, legacy):
            stats["win_rate"] = round(stats["wins"] / stats["trades"] * 100, 1) if stats["trades"] > 0 else 0.0
            stats["pnl"] = round(float(stats["pnl"] or 0.0), 2)

        policy_source = "noaa_verified" if verified["trades"] > 0 else "legacy"
        policy_stats = verified if policy_source == "noaa_verified" else legacy
        buckets.update({
            "policy_source": policy_source,
            "policy_is_provisional": policy_source != "noaa_verified",
            "policy": {
                "trades": int(policy_stats["trades"] or 0),
                "wins": int(policy_stats["wins"] or 0),
                "win_rate": round(float(policy_stats["win_rate"] or 0.0), 1),
                "pnl": round(float(policy_stats["pnl"] or 0.0), 2),
            },
            "verified_dates": sorted(
                date_key for row_city, date_key in verified_keys
                if row_city == city and date_key
            ),
        })

    return cities


def maybe_run_recorder_health_alert(state: dict) -> bool:
    """Fase 0.6: alerta Telegram para salud del SQLite Recorder.

    Tipo A — readiness (one-shot): avisa cuando phase1_readiness_check devuelve exit 0.
    Tipo B — stale (1/día): avisa si el recorder lleva >30h sin escribir.

    Retorna True si el state fue modificado. Completamente fail-safe.
    """
    if not RECORDER_HEALTH_ALERTS_ENABLED:
        return False
    if not SQLITE_RECORDER_ENABLED:
        return False
    if not os.path.exists(PHASE1_READINESS_SCRIPT):
        log.warning("recorder health: tools/phase1_readiness_check.py no encontrado")
        return False

    try:
        result = subprocess.run(
            [sys.executable, PHASE1_READINESS_SCRIPT, "--db", SQLITE_DB_PATH, "--json"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        raw = result.stdout.strip()
        if not raw:
            return False
        data = json.loads(raw)
    except Exception as e:
        log.warning(f"recorder health: error llamando readiness check ({e})")
        return False

    now_utc = datetime.now(timezone.utc)
    today = now_utc.strftime("%Y-%m-%d")
    milestones = state.setdefault("milestones", {})
    changed = False

    readiness = data.get("readiness", {})
    cycle_info = data.get("cycle_events", {})
    market_info = data.get("market_snapshots", {})
    forecast_info = data.get("forecast_snapshots", {})
    freshness = data.get("freshness", {})

    # Tipo A — readiness alcanzada (one-shot, nunca se repite)
    if readiness.get("ready"):
        milestone_key = "sqlite_recorder_phase1_ready"
        if milestone_key not in milestones:
            hours_ago = freshness.get("hours_ago")
            freshness_str = f"{hours_ago:.1f}h" if hours_ago is not None else "?"
            send_telegram(
                f"✅ <b>SQLite Recorder listo para Fase 1</b>\n"
                f"Ciclos: {cycle_info.get('total', '?')}\n"
                f"Días: {cycle_info.get('days_span', '?')}\n"
                f"Market snapshots: {market_info.get('total', '?')}\n"
                f"Forecast snapshots: {forecast_info.get('total', '?')}\n"
                f"Última escritura: hace {freshness_str}\n"
                f"ETA: completada\n\n"
                f"Puedes pedir diseño de Fase 1: Truth Pipeline."
            )
            milestones[milestone_key] = {"sent_at": now_utc.isoformat()}
            changed = True

    # Tipo B — recorder stale (máximo 1 alerta por día)
    if freshness.get("is_stale") and state.get("recorder_stale_last_alert_date") != today:
        hours_ago = freshness.get("hours_ago") or 0
        send_telegram(
            f"⚠️ <b>SQLite Recorder sin datos recientes</b>\n"
            f"Última escritura: hace {hours_ago:.1f}h\n"
            f"Threshold: {freshness.get('stale_threshold_hours', 30)}h\n\n"
            f"Verificar:\n"
            f"- SQLITE_RECORDER_ENABLED=1\n"
            f"- SQLITE_DB_PATH=/app/data/polymarket.db\n"
            f"- logs del último ciclo"
        )
        state["recorder_stale_last_alert_date"] = today
        changed = True

    return changed


def maybe_run_city_lifecycle_review_alert(state: dict) -> bool:
    """City Lifecycle Review Monitor — integración runtime (LOG_ONLY).

    Ejecuta el monitor una vez por día y avisa por Telegram si hay transiciones
    relevantes (manual_review_pending, canary_review, active_review,
    silent_promotion_detected) con cooldown de 24h por ciudad+transición.

    LOG_ONLY: no toca BUY/SELL/SKIP, whitelist, city modes, BANKROLL, Fase C.
    No escribe en /app/data salvo city_lifecycle_review.json y el cooldown en alerts_state.
    Retorna True si se modificó el state.
    """
    import importlib.util

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("lifecycle_review_last_run_date") == today:
        return False

    if not os.path.exists(_LIFECYCLE_MONITOR_SCRIPT):
        log.warning("lifecycle review: tools/city_lifecycle_review_monitor.py no encontrado")
        return False

    try:
        spec = importlib.util.spec_from_file_location(
            "city_lifecycle_review_monitor", _LIFECYCLE_MONITOR_SCRIPT
        )
        monitor_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor_mod)
    except Exception as e:
        log.warning(f"lifecycle review: error importando monitor ({e})")
        return False

    try:
        policy_state = load_city_policy_state()
        shadow_tracking = load_shadow_city_tracking()

        policy_env = {
            "variables": {
                "ACTIVE_TRADING_CITIES": ",".join(sorted(ACTIVE_TRADING_CITIES)),
                "CANARY_TRADING_CITIES": ",".join(sorted(CANARY_TRADING_CITIES)),
                "BLOCKED_CITIES": ",".join(sorted(BLOCKED_CITIES)),
            }
        }

        overrides_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "city_lifecycle_overrides.json",
        )
        overrides = {}
        if os.path.exists(overrides_path):
            try:
                with open(overrides_path, "r", encoding="utf-8") as _f:
                    overrides = json.load(_f)
            except Exception:
                pass

        promo_gate = None
        promo_gate_path = _data_path("city_promotion_gate.json")
        if os.path.exists(promo_gate_path):
            try:
                with open(promo_gate_path, "r", encoding="utf-8") as _f:
                    promo_gate = json.load(_f)
            except Exception:
                pass

        trade_lifecycle = None
        trade_lifecycle_path = _data_path("trade_lifecycle.json")
        if os.path.exists(trade_lifecycle_path):
            try:
                with open(trade_lifecycle_path, "r", encoding="utf-8") as _f:
                    trade_lifecycle = json.load(_f)
            except Exception:
                pass

        inputs = {
            "policy_env": policy_env,
            "policy_state": policy_state,
            "shadow_tracking": shadow_tracking,
            "overrides": overrides,
            "promotion_gate": promo_gate,
            "trade_lifecycle": trade_lifecycle,
        }
        records = monitor_mod.build_city_records(inputs)
    except Exception as e:
        log.warning(f"lifecycle review: error construyendo records ({e})")
        return False

    try:
        stage_counts = {}
        transition_counts = {}
        for r in records:
            stage_counts[r["lifecycle_stage"]] = stage_counts.get(r["lifecycle_stage"], 0) + 1
            transition_counts[r["transition_proposed"]] = transition_counts.get(r["transition_proposed"], 0) + 1
        payload = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "log_only": True,
            "disclaimer": monitor_mod.LOG_ONLY_DISCLAIMER,
            "summary": {
                "n_cities": len(records),
                "stage_counts": stage_counts,
                "transition_counts": transition_counts,
            },
            "cities": records,
        }
        outdir = os.path.dirname(LIFECYCLE_REVIEW_JSON_FILE)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
        with open(LIFECYCLE_REVIEW_JSON_FILE, "w", encoding="utf-8") as _f:
            json.dump(payload, _f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"lifecycle review: error guardando JSON ({e})")

    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)
    alerted = state.setdefault("lifecycle_review_alerted", {})
    changed = False

    for record in records:
        transition = record.get("transition_proposed", "")
        if transition not in _LIFECYCLE_REVIEW_ALERT_TRANSITIONS:
            continue

        city = record.get("city", "?")
        cooldown_key = f"{city}|{transition}"
        last_sent = alerted.get(cooldown_key)
        if last_sent:
            try:
                last_dt = datetime.fromisoformat(last_sent)
                if (now_dt - last_dt).total_seconds() < LIFECYCLE_REVIEW_COOLDOWN_HOURS * 3600:
                    continue
            except Exception:
                pass

        stage = record.get("lifecycle_stage", "?")
        override = record.get("override") or {}
        notes = record.get("notes") or []
        gates_failed = record.get("gates_failed") or []

        override_tag = " [OVERRIDE]" if override else ""
        notes_str = "\n".join(f"• {n}" for n in notes[:3]) if notes else "—"
        gates_str = ", ".join(gates_failed[:3]) if gates_failed else "—"

        message = "\n".join([
            "<b>City Lifecycle Review</b> (LOG_ONLY)",
            "",
            f"<b>{city}</b>{override_tag} → <code>{transition}</code>",
            f"Stage actual: <code>{stage}</code>",
            "",
            "<b>Notas:</b>",
            notes_str,
            f"<b>Gates fallidos:</b> {gates_str}",
            "",
            "<i>LOG_ONLY — No autoriza BUY/SELL/SKIP, whitelist, canary, active, BANKROLL ni Fase C.</i>",
            "<i>Requiere revisión humana explícita antes de cualquier cambio de policy.</i>",
        ])

        send_telegram(message)
        alerted[cooldown_key] = now_iso
        changed = True

    state["lifecycle_review_last_run_date"] = today
    return changed


# ---------------------------------------------------------------------------
# Source Onboarding Scanner — LOG_ONLY daily runtime integration (genera JSON para digest)
# ---------------------------------------------------------------------------

_SOURCE_ONBOARDING_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "source_onboarding_scanner.py",
)
_SOURCE_ONBOARDING_JSON_FILE = _data_path("source_onboarding.json")


def maybe_run_source_onboarding_scanner(state: dict) -> bool:
    """Source Onboarding Scanner — integración runtime (LOG_ONLY).

    Ejecuta el scanner una vez por día UTC y genera /app/data/source_onboarding.json
    que City Intelligence Digest consume en el mismo ciclo.

    LOG_ONLY: no toca BUY/SELL/SKIP, whitelist, city modes, env vars, BANKROLL, Fase C.
    No envía Telegram propio. No ejecuta source_audit_workbench.
    Si faltan inputs críticos, loguea warning y degrada limpiamente (el digest leerá
    el JSON anterior o degradará por su cuenta).
    Retorna True si se modificó el state.
    """
    import importlib.util

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("source_onboarding_last_run_date") == today:
        return False

    if not os.path.exists(_SOURCE_ONBOARDING_SCRIPT):
        log.warning("source_onboarding_scanner: tools/source_onboarding_scanner.py no encontrado")
        state["source_onboarding_last_run_date"] = today
        return True

    try:
        spec = importlib.util.spec_from_file_location(
            "source_onboarding_scanner", _SOURCE_ONBOARDING_SCRIPT
        )
        scanner_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner_mod)
    except Exception as e:
        log.warning(f"source_onboarding_scanner: error importando modulo ({e})")
        state["source_onboarding_last_run_date"] = today
        return True

    # Sintetizar policy_env_snapshot desde globals (solo city lists, sin secretos)
    policy_env_path = _data_path("policy_env_snapshot.json")
    try:
        policy_env_data = {
            "variables": {
                "ACTIVE_TRADING_CITIES": ",".join(sorted(ACTIVE_TRADING_CITIES)),
                "CANARY_TRADING_CITIES": ",".join(sorted(CANARY_TRADING_CITIES)),
                "BLOCKED_CITIES": ",".join(sorted(BLOCKED_CITIES)),
            }
        }
        with open(policy_env_path, "w", encoding="utf-8") as _f:
            json.dump(policy_env_data, _f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"source_onboarding_scanner: no se pudo escribir policy_env_snapshot ({e})")
        state["source_onboarding_last_run_date"] = today
        return True

    overrides_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "city_lifecycle_overrides.json",
    )
    md_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "docs", "source_onboarding_latest.md",
    )

    argv = [
        "--signals-crosscheck", _data_path("signals_crosscheck.jsonl"),
        "--blocked-resolutions", _data_path("blocked_signals_resolutions.jsonl"),
        "--shadow-tracking", _data_path("shadow_city_tracking.json"),
        "--policy-env", policy_env_path,
        "--policy-state", _data_path("city_policy_state.json"),
        "--overrides", overrides_path,
        "--json-output", _SOURCE_ONBOARDING_JSON_FILE,
        "--md-output", md_path,
    ]

    try:
        result = scanner_mod.main(argv)
        if result and result != 0:
            log.warning(
                f"source_onboarding_scanner: main() returned {result} "
                "(inputs criticos ausentes — digest degradara limpiamente)"
            )
    except Exception as e:
        log.warning(f"source_onboarding_scanner: error ejecutando scanner ({e})")

    state["source_onboarding_last_run_date"] = today
    return True


# ---------------------------------------------------------------------------
# City Intelligence Digest — LOG_ONLY daily unified digest (Fase 1, Telegram wired)
# ---------------------------------------------------------------------------

_DIGEST_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "city_intelligence_digest.py",
)
_DIGEST_JSON_FILE = _data_path("city_intelligence_digest.json")
_METAR_SHADOW_REPORT_FILE = _data_path("metar_shadow_report.json")
_DIGEST_COOLDOWN_HOURS = 24

# Onboarding states that surface in digest Telegram
_DIGEST_TELEGRAM_ONBOARDING_STATES = {"READY_FOR_SOURCE_AUDIT"}
# Audit statuses that surface in digest Telegram
_DIGEST_TELEGRAM_AUDIT_STATUSES = {"NEEDS_MANUAL_SOURCE_LOOKUP", "READY_FOR_OBSERVED_AUDIT_REVIEW"}


def maybe_run_city_intelligence_digest_alert(state: dict) -> bool:
    """City Intelligence Digest — integración runtime (LOG_ONLY).

    Ejecuta el digest una vez por día y envía UN único Telegram con:
      - Source Onboarding candidates (no overlap con lifecycle individual alerts)
      - Source Audit packages pendientes
      - Review Queue summary (sólo conteo, lifecycle ya envió alerts per-city)
      - Drift / policy conflicts

    LOG_ONLY: no toca BUY/SELL/SKIP, whitelist, city modes, env vars, BANKROLL, Fase C.
    No duplica lifecycle alerts: sección Review Queue es sólo resumen de conteo.
    Retorna True si se modificó el state.
    """
    import importlib.util
    import glob as _glob

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("digest_last_run_date") == today:
        return False

    if not os.path.exists(_DIGEST_SCRIPT):
        log.warning("city_intelligence_digest: tools/city_intelligence_digest.py no encontrado")
        return False

    try:
        spec = importlib.util.spec_from_file_location("city_intelligence_digest", _DIGEST_SCRIPT)
        digest_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(digest_mod)
    except Exception as e:
        log.warning(f"city_intelligence_digest: error importando modulo ({e})")
        return False

    try:
        lifecycle_path = _data_path("city_lifecycle_review.json")
        onboarding_path = _data_path("source_onboarding.json")
        audits_dir = _data_path("source_audits")

        argv = [
            "--lifecycle-review", lifecycle_path,
            "--source-onboarding", onboarding_path,
            "--source-audits-dir", audits_dir,
            "--json-output", _DIGEST_JSON_FILE,
        ]
        try:
            md_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "docs", "city_intelligence_digest_latest.md",
            )
            argv += ["--md-output", md_path]
        except Exception:
            pass

        digest_mod.main(argv)
    except Exception as e:
        log.warning(f"city_intelligence_digest: error ejecutando digest ({e})")

    # Load the generated digest JSON to build the Telegram message
    try:
        if not os.path.exists(_DIGEST_JSON_FILE):
            state["digest_last_run_date"] = today
            return True

        with open(_DIGEST_JSON_FILE, "r", encoding="utf-8") as _f:
            digest_data = json.load(_f)
    except Exception as e:
        log.warning(f"city_intelligence_digest: error leyendo JSON generado ({e})")
        state["digest_last_run_date"] = today
        return True

    try:
        summary = digest_data.get("summary", {})
        review_queue = digest_data.get("review_queue", [])
        onboarding = digest_data.get("onboarding", {})
        audit_section = digest_data.get("source_audits", {})
        drift = digest_data.get("drift", [])

        # Only send Telegram if there's something noteworthy
        has_content = (
            len(onboarding.get("ready", [])) > 0
            or len(audit_section.get("actionable", [])) > 0
            or len(drift) > 0
            or summary.get("review_queue_count", 0) > 0
        )
        if not has_content:
            state["digest_last_run_date"] = today
            return True

        lines = [
            f"<b>City Intelligence Digest — {today}</b> (LOG_ONLY)",
            "",
        ]

        # Review Queue: summary only (per-city alerts sent individually by lifecycle)
        rq_count = summary.get("review_queue_count", 0)
        if rq_count > 0:
            strongest = review_queue[0] if review_queue else None
            transitions = summary.get("review_queue_transitions", {}) or {}
            canary_watch_count = int(transitions.get("canary_watch", 0) or 0)
            drift_count = int(transitions.get("reporting_drift_blocked_effective", 0) or 0)
            strongest_str = ""
            if strongest:
                strongest_str = f" — strongest: <b>{strongest['city']}</b> → {strongest['transition_proposed']}"
            lines.append(f"<b>Review Queue:</b> {rq_count} ciudad(es) en revisión{strongest_str}")
            if canary_watch_count:
                lines.append(
                    f"<i>Canary watch grouped: {canary_watch_count} candidate(s), not active-ready.</i>"
                )
            if drift_count:
                lines.append(
                    f"<i>Blocked effective reporting drift: {drift_count} item(s), NO_ACTION / LOG_ONLY.</i>"
                )
            lines.append("<i>Alertas individuales solo para manual_review_pending, active_review real o silent promotion.</i>")
            lines.append("")

        # Source Onboarding: full detail for READY candidates
        ready_cities = onboarding.get("ready", [])
        if ready_cities:
            lines.append("<b>Source Onboarding — READY_FOR_SOURCE_AUDIT:</b>")
            for c in ready_cities[:5]:
                t = c.get("trader", {})
                b = c.get("blocked_signals", {})
                wr_str = f"WR={b['wr']:.0%} n={b['n']}" if b.get("wr") is not None and b.get("qualifies") else f"n={b.get('n', 0)}"
                lines.append(
                    f"• <b>{c['city']}</b> score={c.get('priority_score', 0):.2f}"
                    f" {c.get('source_feasibility', '?')}"
                    f" traders={t.get('n_sources', 0)}/{t.get('n_days', 0)}d {wr_str}"
                )
            if len(ready_cities) > 5:
                lines.append(f"  ... y {len(ready_cities) - 5} más")
            lines.append("")

        waiting = onboarding.get("waiting_count", 0)
        if waiting > 0:
            lines.append(f"<i>Onboarding quiet: {waiting} WAITING_EVIDENCE/RANGE_ONLY</i>")
            lines.append("")

        # Source Audit packages
        actionable = audit_section.get("actionable", [])
        if actionable:
            lines.append("<b>Source Audit Packages pendientes:</b>")
            for a in actionable[:5]:
                next_step = a.get("proposed_next_step") or a.get("recommendation") or "-"
                lines.append(f"• <b>{a['city']}</b> <code>{a['status']}</code> — {next_step}")
            lines.append("")

        # Drift / Policy conflicts
        if drift:
            lines.append("<b>⚠ Drift / Policy conflicts:</b>")
            for r in drift[:3]:
                notes_str = "; ".join(r.get("notes", [])[:1]) or "-"
                transition = r.get("transition_proposed") or "policy_drift"
                lines.append(f"• <b>{r['city']}</b> <code>{transition}</code> — {notes_str}")
            lines.append("<i>NO_ACTION / LOG_ONLY. Do not promote.</i>")
            lines.append("")

        lines += [
            "<i>LOG_ONLY — No autoriza BUY/SELL/SKIP, whitelist, canary, active, "
            "env vars, BANKROLL ni Fase C.</i>",
            "<i>Requiere revisión humana explícita antes de cualquier cambio de policy.</i>",
        ]

        message = "\n".join(lines)
        send_telegram(message)
    except Exception as e:
        log.warning(f"city_intelligence_digest: error construyendo Telegram ({e})")

    state["digest_last_run_date"] = today
    return True


def run_observability_alerts():
    """
    Alertas one-shot de observabilidad y review readiness.
    No toca lógica de trading; solo avisa por Telegram cuando aparece información útil.
    """
    state = load_alerts_state()
    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()
    milestones = state.setdefault("milestones", {})

    stats = get_clean_closed_trade_stats()
    milestone_key = f"clean_trades_{REVIEW_READY_CLEAN_TRADES}"
    if stats["count"] >= REVIEW_READY_CLEAN_TRADES and milestone_key not in milestones:
        send_telegram(
            f"🧠 <b>Review Trigger</b>\n"
            f"Ya hay <b>{stats['count']} trades limpios cerrados</b>.\n"
            f"SELL: {stats['sell']} | LOSS_TOTAL: {stats['loss_total']} | RESOLVED_WIN: {stats['resolved_win']}\n\n"
            f"Recomendado abrir sesión de análisis/coding para revisar la lógica de salida de la serie <b>v{LOGIC_SERIES}.x</b>."
        )
        milestones[milestone_key] = {
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
                "⚠ <b>Alerta traders</b>\n"
                "signals.json no existe en DATA_DIR.\n"
                "El bot seguirá funcionando, pero sin confirmación de traders."
            )
        elif issue == "stale":
            send_telegram(
                f"⚠ <b>Alerta traders</b>\n"
                f"signals.json está expirado ({signals.get('age_hours', 0):.1f}h).\n"
                f"Señales accionables actuales: {signals.get('actionable', 0)}."
            )
        elif issue == "empty":
            send_telegram(
                f"⚠ <b>Alerta traders</b>\n"
                f"signals.json está al día ({signals.get('age_hours', 0):.1f}h), pero sin señales accionables."
            )
        elif issue == "error":
            send_telegram(
                "⚠ <b>Alerta traders</b>\n"
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

    audit = load_audit_data()
    observed_rows = [
        row for row in audit.get(OBSERVED_AUDIT_KEY, [])
        if isinstance(row, dict) and row.get("source") == "noaa_ncei"
    ]
    observed_city_counts = {city: 0 for city in sorted(OBSERVED_AUDIT_CITIES)}
    for row in observed_rows:
        city = row.get("city")
        if city in observed_city_counts:
            observed_city_counts[city] += 1

    observed_sample_size = len(observed_rows)
    observed_with_sample = [city for city, count in observed_city_counts.items() if count >= 1]
    observed_interpretable = [
        city for city, count in observed_city_counts.items()
        if count >= OBSERVED_FORECAST_MIN_SAMPLE
    ]

    observed_started_key = "observed_proxy_started"
    if observed_sample_size >= 1 and observed_started_key not in milestones:
        send_telegram(
            f"🛰 <b>Observed proxy NOAA activo</b>\n"
            f"Ya hay <b>{observed_sample_size} caso(s)</b> en <code>{OBSERVED_AUDIT_KEY}</code>.\n"
            f"Ciudades con muestra: {len(observed_with_sample)}/{len(observed_city_counts)}."
        )
        milestones[observed_started_key] = {
            "sent_at": now_iso,
            "count": observed_sample_size,
            "coverage": len(observed_with_sample),
        }
        changed = True

    observed_min_key = f"observed_proxy_min_sample_{OBSERVED_FORECAST_MIN_SAMPLE}"
    if observed_sample_size >= OBSERVED_FORECAST_MIN_SAMPLE and observed_min_key not in milestones:
        send_telegram(
            f"🧪 <b>Muestra NOAA mínima alcanzada</b>\n"
            f"{OBSERVED_AUDIT_KEY} ya tiene <b>{observed_sample_size} casos</b>.\n"
            f"MAE/bias global preliminar ya es visible en el dashboard.\n"
            f"Cobertura actual: {len(observed_with_sample)}/{len(observed_city_counts)} ciudades."
        )
        milestones[observed_min_key] = {
            "sent_at": now_iso,
            "count": observed_sample_size,
            "coverage": len(observed_with_sample),
        }
        changed = True

    observed_global_key = f"observed_proxy_global_target_{OBSERVED_FORECAST_GLOBAL_TARGET}"
    if observed_sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET and observed_global_key not in milestones:
        send_telegram(
            f"📊 <b>Muestra NOAA global útil</b>\n"
            f"{OBSERVED_AUDIT_KEY} ya tiene <b>{observed_sample_size} casos</b>.\n"
            f"Ya tiene sentido leer sesgo global con más confianza.\n"
            f"Cobertura actual: {len(observed_with_sample)}/{len(observed_city_counts)} ciudades."
        )
        milestones[observed_global_key] = {
            "sent_at": now_iso,
            "count": observed_sample_size,
            "coverage": len(observed_with_sample),
        }
        changed = True

    new_observed_cities = []
    for city in observed_with_sample:
        city_key = f"observed_city_started:{city}"
        if city_key not in milestones:
            new_observed_cities.append(city)
            milestones[city_key] = {
                "sent_at": now_iso,
                "count": observed_city_counts.get(city, 0),
            }
            changed = True
    if new_observed_cities:
        send_telegram(
            f"🗺 <b>NOAA nueva ciudad con muestra</b>\n"
            f"{', '.join(new_observed_cities)}.\n"
            f"Cobertura actual: {len(observed_with_sample)}/{len(observed_city_counts)} ciudades activas."
        )

    new_interpretable_cities = []
    for city in observed_interpretable:
        city_key = f"observed_city_interpretable:{city}"
        if city_key not in milestones:
            new_interpretable_cities.append(f"{city} ({observed_city_counts.get(city, 0)})")
            milestones[city_key] = {
                "sent_at": now_iso,
                "count": observed_city_counts.get(city, 0),
            }
            changed = True
    if new_interpretable_cities:
        send_telegram(
            f" <b>NOAA ciudad interpretable</b>\n"
            f"{', '.join(new_interpretable_cities)}.\n"
            f"Ciudades con >= {OBSERVED_FORECAST_MIN_SAMPLE} casos: "
            f"{len(observed_interpretable)}/{len(observed_city_counts)}."
        )

    notified = state.get("pending_exit_notified", {})
    pending = audit.get("pending_sells", [])
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
            " <b>Ventas pendientes atascadas</b>",
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
                    f"Señal auxiliar de scaling: abrir revisión manual de bankroll ${BANKROLL:.0f} → ${next_tier:.0f}.\n"
                    f"NO autoriza subida automática ni cambiar BANKROLL solo por esta alerta.\n"
                    f"Requiere cumplir docs/bankroll_scaling_policy.md y validar health/readiness/PnL antes de decidir."
                )
                state["scaling_alerted_tier"] = next_tier
                changed = True

        if scaling_pnl < 0 and not state.get("scaling_negative_alerted"):
            send_telegram(
                f"⚠ <b>Scaling Warning</b>\n"
                f"PnL acumulado de últimos {SCALING_WINDOW} trades: <b>${scaling_pnl:+.2f}</b>.\n"
                f"Señal auxiliar: no subir bankroll; revisar PnL/drawdown antes de cualquier revisión manual."
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
    city_stats = {}
    policy_state = load_city_policy_state()
    flagged_key = "city_accuracy_flagged"
    if flagged_key not in state:
        state[flagged_key] = {}

    for city, data in city_stats.items():
        if data["trades"] >= CITY_MIN_TRADES_FOR_BLOCK and data["win_rate"] <= CITY_BLOCK_WIN_RATE:
            city_mode = get_effective_city_mode(city, policy_state=policy_state)
            if city_mode != "blocked" and city not in state[flagged_key]:
                now_iso = datetime.now(timezone.utc).isoformat()
                send_telegram(
                    f"⚠ <b>Ciudad con baja accuracy</b>\n"
                    f"{city}: {data['win_rate']}% win rate ({data['wins']}/{data['trades']} trades)\n"
                    f"PnL: ${data['pnl']:+.2f}\n"
                    f"<i>Considerar añadir a BLOCKED_CITIES</i>"
                )
                state[flagged_key][city] = {"sent_at": now_iso, **data}
                changed = True

    # ---- v10.6.11: City NOAA-verified review alert ----
    policy_state_loader = globals().get("load_city_policy_state")
    policy_state = policy_state_loader() if callable(policy_state_loader) else {}
    city_mode_helper = globals().get("get_effective_city_mode")
    if "get_city_policy_metrics" in globals():
        city_policy_metrics = get_city_policy_metrics(audit=audit)
    else:
        city_policy_metrics = {}
    flagged_key = "city_policy_review_flagged"
    if flagged_key not in state:
        state[flagged_key] = {}

    verified_bad_min_trades = int(globals().get("ALERT_VERIFIED_BAD_MIN_TRADES", 5) or 5)
    verified_bad_max_win_rate = float(
        globals().get(
            "ALERT_VERIFIED_BAD_MAX_WIN_RATE",
            globals().get("CITY_BLOCK_WIN_RATE", 25.0),
        )
        or globals().get("CITY_BLOCK_WIN_RATE", 25.0)
    )

    for city, buckets in city_policy_metrics.items():
        verified = buckets.get("verified", {}) if isinstance(buckets, dict) else {}
        trades = int(verified.get("trades", 0) or 0)
        wins = int(verified.get("wins", 0) or 0)
        win_rate = float(verified.get("win_rate", 0.0) or 0.0)
        pnl = round(float(verified.get("pnl", 0.0) or 0.0), 2)
        city_mode = get_effective_city_mode(city, policy_state=policy_state)
        if trades < verified_bad_min_trades or win_rate > verified_bad_max_win_rate:
            continue
        if city_mode not in {"active", "canary"}:
            continue
        if city in state[flagged_key]:
            continue
        now_iso = datetime.now(timezone.utc).isoformat()
        send_telegram(
            f"âš  <b>Ciudad bajo review NOAA-verificado</b>\n"
            f"{city}: {win_rate:.1f}% win rate ({wins}/{trades} trades NOAA-verificados)\n"
            f"PnL NOAA-verificado: ${pnl:+.2f}\n"
            f"<i>Revisar allowlist/canary antes de ampliar riesgo</i>"
        )
        state[flagged_key][city] = {
            "sent_at": now_iso,
            "trades": trades,
            "wins": wins,
            "win_rate": round(win_rate, 1),
            "pnl": pnl,
            "city_mode": city_mode,
        }
        changed = True

    # ---- v10.6: Low bankroll alert ----
    portfolio = _get_portfolio_and_positions()
    bankroll_signal_reliable = (
        portfolio
        and portfolio.get("cash") is not None
        and portfolio.get("cash_ok")
        and not portfolio.get("api_error")
    )
    if bankroll_signal_reliable:
        total = portfolio.get("portfolio_total", portfolio["cash"])
        reset_threshold = LOW_BANKROLL_THRESHOLD + LOW_BANKROLL_RESET_MARGIN
        if total <= LOW_BANKROLL_THRESHOLD and not state.get("low_bankroll_alerted"):
            send_telegram(
                f"🚨 <b>Bankroll bajo — recargar</b>\n"
                f"Cash: ${portfolio['cash']:.2f} | Total cartera: ${total:.2f}\n"
                f"Umbral: ${LOW_BANKROLL_THRESHOLD:.2f}\n\n"
                f"El bot necesita fondos para seguir operando y generando datos.\n"
                f"Considerar depositar $25 USDC."
            )
            state["low_bankroll_alerted"] = True
            changed = True
        elif total > reset_threshold and state.get("low_bankroll_alerted"):
            state["low_bankroll_alerted"] = False
            changed = True

    # v10.6.14 (M2): degrada ciudades Active→Canary si performance baja; antes de notify_active_candidates.
    try:
        if maybe_run_bankroll_scaling_monitor(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"bankroll scaling monitor: fallo ({e})")

    try:
        if maybe_run_active_degradation(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"Error en active degradation: {e}")

    # v10.6.11 (M5): alerta one-shot cuando una ciudad shadow se vuelve candidata a canary.
    # Se evalúa antes del sync para que la notificación humana preceda (o acompañe) al auto-promote.
    try:
        if notify_canary_candidates(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"Error evaluando canary candidates: {e}")

    # v10.6.14 (M1): notifica ciudades canary listas para Active (criterios v1).
    try:
        if notify_active_candidates(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"Error evaluando active candidates: {e}")

    try:
        sync_city_policy_state(notify=True)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"Error sincronizando city policy state: {e}")

    # v10.6.11 (M4): resumen diario Telegram 08:00 UTC, one-shot por día.
    try:
        if maybe_send_daily_summary_telegram(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"Error evaluando resumen diario: {e}")

    try:
        if maybe_run_daily_crosscheck(state):
            changed = True
            maybe_run_daily_crosscheck_temporal_summary()
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"crosscheck diario: fallo ({e})")

    # v10.6.13: seguimiento resoluciones blocked signals (exact/range), una vez por día.
    # v10.6.31: puente runtime read-only para City Intelligence desde el volumen real del bot.
    try:
        if maybe_run_city_intelligence_runtime_summary(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"city intelligence runtime summary: fallo ({e})")

    try:
        if maybe_run_blocked_signals_check(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"blocked signals check: fallo ({e})")

    try:
        if maybe_run_traders_intelligence_summary(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"traders intelligence summary: fallo ({e})")

    # Traders Operational Intelligence: LOG_ONLY snapshots + six-question digest, default ON.
    try:
        if maybe_run_traders_operational_intelligence_monitor():
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"traders operational intelligence: fallo ({e})")

    # v10.6.14 (M3): alerta one-shot cuando las precondiciones para v2 se cumplen.
    try:
        if maybe_alert_v2_trigger(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"v2 trigger alarm: fallo ({e})")

    # v10.6.16: checkpoint automático canary condition_filtered exact/range (día 7+).
    try:
        if maybe_run_condition_monitor(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"condition monitor: fallo ({e})")

    # v10.6.50: monitor rolling Phase 2 mixed-condition (exact + at_or_above + at_or_below).
    try:
        if maybe_run_phase2_monitor(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"phase2 monitor: fallo ({e})")

    # v10.6.18: alerta one-shot observacion W17 (dispara el 2026-04-20).
    try:
        if maybe_run_w17_observation_alert(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"w17 observation alert: fallo ({e})")

    # v10.6.20: alerta one-shot expansion post-checkpoint condition_filtered (dispara 2026-04-22).
    try:
        if maybe_alert_p4_p5_expansion(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"p4_p5 expansion alert: fallo ({e})")

    # v10.6.20: alerta one-shot limpieza post-V2 cutover (dispara 2026-04-25).
    try:
        if maybe_alert_p6_p7_post_v2_cleanup(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"p6_p7 post v2 alert: fallo ({e})")

    # v10.6.25: alerta one-shot Steps 2+3 TP/SL dinamico por precio (dispara 2026-05-10).
    try:
        if maybe_alert_tp_sl_price_steps(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"tp_sl_price_steps alert: fallo ({e})")

    # v10.6.26: alerta one-shot expansion Busan (dispara 2026-04-24).
    try:
        if maybe_alert_busan_expansion(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"busan expansion alert: fallo ({e})")

    try:
        if maybe_evaluate_slot_monetization(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"slot monetization review: fallo ({e})")

    # v10.6.30: alerta one-shot revision intra-reeval shadow (7 dias tras primer trigger).
    try:
        if maybe_run_intra_reeval_review_alert(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"intra reeval review alert: fallo ({e})")

    # v10.6.36: follow-up de muestra post-fix para cooldown de stop_loss_intra.
    try:
        if maybe_run_post_intra_sl_cooldown_review(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"post intra-SL cooldown review: fallo ({e})")

    # v10.6.40: review del guard SL_intra (exact + days<=N).
    try:
        if maybe_run_sl_intra_guard_review(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"sl_intra_guard review: fallo ({e})")

    try:
        if maybe_run_sl_retrospective(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"sl retrospective: fallo ({e})")

    try:
        if maybe_run_pnl_reconciliation(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"pnl reconciliation: fallo ({e})")

    try:
        if maybe_run_unsellable_guard_monitor(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"unsellable guard monitor: fallo ({e})")

    try:
        if maybe_run_wallet_snapshot(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"wallet snapshot: fallo ({e})")

    # v10.6.37: cierra posiciones expiradas sin evidencia antes del briefing.
    try:
        maybe_close_expired_legacy_positions(state)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"legacy cleanup: fallo ({e})")

    try:
        if maybe_run_daily_briefing(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"daily briefing: fallo ({e})")

    # v10.6.48: leaderboard P&L digest diario por Telegram.
    try:
        if maybe_send_daily_bot_digest():
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"daily digest: fallo ({e})")

    # Traders Intelligence V1.1 collector: LOG_ONLY, default OFF.
    try:
        if maybe_run_traders_intelligence_collector():
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"traders intelligence collector: fallo ({e})")

    # v10.6.43: Recorder Health Alerts (Fase 0.6)
    try:
        if maybe_run_recorder_health_alert(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"recorder health alert: fallo ({e})")

    # City Lifecycle Review Monitor — LOG_ONLY, daily, Telegram cooldown 24h/ciudad+transición.
    try:
        if maybe_run_city_lifecycle_review_alert(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"lifecycle review alert: fallo ({e})")

    # Source Onboarding Scanner — LOG_ONLY, daily, genera source_onboarding.json para el digest.
    try:
        if maybe_run_source_onboarding_scanner(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"source onboarding scanner: fallo ({e})")

    # Source Onboarding Andon: LOG_ONLY, idempotent Telegram for human source actions.
    try:
        if maybe_run_source_onboarding_andon():
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"source onboarding andon: fallo ({e})")

    # City Intelligence Digest: LOG_ONLY daily unified digest after Andon.
    try:
        if maybe_run_city_intelligence_digest_alert(state):
            changed = True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"city intelligence digest alert: fallo ({e})")

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
    # v10.6: ordenar por fecha antes de tomar ventana de drawdown
    closed_sorted = sorted(closed, key=lambda r: r.get("closed_at", ""), reverse=False)
    last_window = closed_sorted[-DRAWDOWN_WINDOW:] if count else []
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
    ]


def build_dashboard_exit_breakdown(closed_records=None, series_records=None, portfolio=None, logic_series=None):
    """Resume balance por tipo de salida y estado de liquidación/cobro."""
    logic_series = logic_series or LOGIC_SERIES
    if closed_records is None:
        closed_records = get_validated_closed_postmortems()
    if series_records is None:
        series_records = get_logic_series_records(logic_series)
    if portfolio is None:
        portfolio = _get_portfolio_and_positions()

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sum_pnl(records, pending=False):
        values = []
        for record in records:
            if pending:
                value = _safe_float((record.get("pending_exit") or {}).get("pnl_cash"))
            else:
                value = _safe_float(record.get("pnl_cash"))
            if value is not None:
                values.append(value)
        if not values:
            return None
        return round(sum(values), 2)

    def _fmt_money(value, signed=True):
        if value is None:
            return "n/d"
        if signed:
            return f"${value:+.2f}"
        return f"${value:.2f}"

    def _status_tag(status):
        return {
            "good": "OK",
            "bad": "Atención",
            "waiting": "Sin muestra",
            "blocked": "Pendiente",
        }.get(status, "Pendiente")

    def _make_row(label, count, note, balance=None, avg=None, status="waiting", signed=True):
        balance_display = _fmt_money(balance, signed=signed)
        avg_display = _fmt_money(avg, signed=signed)
        return {
            "label": label,
            "count": count,
            "note": note,
            "status": status,
            "tag": _status_tag(status),
            "balance_display": balance_display,
            "balance_class": "good" if isinstance(balance, (int, float)) and balance > 0 else "bad" if isinstance(balance, (int, float)) and balance < 0 else "",
            "avg_display": avg_display,
            "avg_class": "good" if isinstance(avg, (int, float)) and avg > 0 else "bad" if isinstance(avg, (int, float)) and avg < 0 else "",
        }

    def _make_closed_row(label, records, note):
        count = len(records)
        balance = _sum_pnl(records)
        avg = round(balance / count, 2) if count and balance is not None else None
        if count == 0:
            status = "waiting"
        elif balance is not None and balance >= 0:
            status = "good"
        else:
            status = "bad"
        return _make_row(label, count, note, balance=balance, avg=avg, status=status, signed=True)

    take_profit_records = [
        r for r in closed_records
        if r.get("close_reason") in {"take_profit", "take_profit_intra"}
    ]
    stop_loss_records = [
        r for r in closed_records
        if r.get("close_reason") in {"stop_loss", "stop_loss_intra"}
    ]
    reeval_records = [r for r in closed_records if r.get("close_reason") == "reeval"]
    loss_total_records = [r for r in closed_records if r.get("close_action") == "LOSS_TOTAL"]
    resolved_win_records = [r for r in closed_records if r.get("close_action") == "RESOLVED_WIN"]
    won_records = [
        r for r in closed_records
        if (_safe_float(r.get("pnl_cash")) or 0) > 0 or r.get("close_action") == "RESOLVED_WIN"
    ]
    lost_records = [
        r for r in closed_records
        if (_safe_float(r.get("pnl_cash")) or 0) < 0 or r.get("close_action") == "LOSS_TOTAL"
    ]

    validated_rows = [
        _make_closed_row("Take-profit", take_profit_records, "cierres por take_profit o take_profit_intra"),
        _make_closed_row("Stop-loss", stop_loss_records, "cierres por stop_loss o stop_loss_intra"),
        _make_closed_row("Re-evaluación", reeval_records, "cierres por pérdida de edge frente al mercado"),
        _make_closed_row("LOSS_TOTAL", loss_total_records, "posiciones no vendibles o muertas antes de cobrar"),
        _make_closed_row("Ganadas por resolución", resolved_win_records, "mercados que llegaron a resolución favorable ($1/share)"),
        _make_closed_row("Ganadas validadas", won_records, "cierres con pnl positivo o resolución ganada"),
        _make_closed_row("Perdidas validadas", lost_records, "cierres con pnl negativo o pérdida total"),
    ]

    series_closed = [
        r for r in series_records
        if r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
        and r.get("pnl_cash") is not None
    ]
    series_pending = [r for r in series_records if r.get("status") == "pending_exit"]
    series_open = [r for r in series_records if r.get("status") == "open"]
    series_failed = [r for r in series_records if r.get("status") == "exit_failed"]
    pending_balance = _sum_pnl(series_pending, pending=True)
    pending_avg = round(pending_balance / len(series_pending), 2) if series_pending and pending_balance is not None else None

    resolved_won = portfolio.get("resolved_won", []) if isinstance(portfolio, dict) else []
    resolved_value = round(float((portfolio or {}).get("resolved_value", 0) or 0), 2) if portfolio else 0.0
    resolved_avg = round(resolved_value / len(resolved_won), 2) if resolved_won else None

    series_rows = [
        _make_closed_row(
            f"Cierres validados serie v{logic_series}",
            series_closed,
            "solo cuentan SELL / LOSS_TOTAL / RESOLVED_WIN ya reconciliados",
        ),
        _make_row(
            f"Pending exit serie v{logic_series}",
            len(series_pending),
            "ventas colocadas; balance aún estimado hasta que auditoría confirme el fill",
            balance=pending_balance,
            avg=pending_avg,
            status="blocked" if series_pending else "good",
            signed=True,
        ),
        _make_row(
            f"Abiertas serie v{logic_series}",
            len(series_open),
            "posiciones todavía sin salida; no cuentan como cierre limpio",
            balance=None,
            avg=None,
            status="waiting" if series_open else "good",
            signed=True,
        ),
        _make_row(
            f"Exit failed serie v{logic_series}",
            len(series_failed),
            "salidas fallidas: conviene revisar si siguen abiertas o han sido reintentadas",
            balance=None,
            avg=None,
            status="bad" if series_failed else "good",
            signed=True,
        ),
        _make_row(
            "Pendiente pago / canjear",
            len(resolved_won),
            "valor resuelto favorable pendiente de convertirse en cash operativo",
            balance=resolved_value,
            avg=resolved_avg,
            status="blocked" if resolved_won else "good",
            signed=False,
        ),
    ]

    return {
        "validated_rows": validated_rows,
        "series_rows": series_rows,
    }


def build_dashboard_forecast_quality(audit=None):
    """Resume observed_vs_forecast (NOAA) sin mezclarlo con trading ni legacy drift."""
    if audit is None:
        audit = load_audit_data()

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fmt_temp(value, signed=False):
        number = _safe_float(value)
        if number is None:
            return "n/d"
        return f"{number:+.1f}C" if signed else f"{number:.1f}C"

    def _fmt_checked_at(value):
        text = str(value or "").strip()
        if not text:
            return "n/d"
        text = text.replace("T", " ")
        if text.endswith("+00:00"):
            return f"{text[:16]} UTC"
        return text[:16]

    def _error_badge(abs_error_c):
        if abs_error_c is None:
            return "muted"
        if abs_error_c <= 1.0:
            return "good"
        if abs_error_c <= 2.0:
            return "warn"
        return "bad"

    rows = []
    for raw in audit.get(OBSERVED_AUDIT_KEY, []):
        if not isinstance(raw, dict) or raw.get("source") != "noaa_ncei":
            continue
        row = dict(raw)
        observed_temp = _safe_float(row.get("observed_temp_c"))
        forecast_temp = _safe_float(row.get("forecast_temp_c"))
        error_c = _safe_float(row.get("error_c"))
        if error_c is None and observed_temp is not None and forecast_temp is not None:
            error_c = round(observed_temp - forecast_temp, 1)
        abs_error_c = _safe_float(row.get("abs_error_c"))
        if abs_error_c is None and error_c is not None:
            abs_error_c = abs(error_c)
        row["_error_c"] = error_c
        row["_abs_error_c"] = abs_error_c
        rows.append(row)

    rows.sort(
        key=lambda item: (
            item.get("checked_at") or "",
            item.get("date") or "",
            item.get("city") or "",
        ),
        reverse=True,
    )

    all_errors = [item["_error_c"] for item in rows if item.get("_error_c") is not None]
    all_abs_errors = [item["_abs_error_c"] for item in rows if item.get("_abs_error_c") is not None]
    sample_size = len(rows)
    kpis_ready = sample_size >= OBSERVED_FORECAST_MIN_SAMPLE and bool(all_abs_errors)
    global_ready = sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET and bool(all_abs_errors)

    mae_c = round(sum(all_abs_errors) / len(all_abs_errors), 1) if kpis_ready else None
    bias_c = round(sum(all_errors) / len(all_errors), 1) if kpis_ready and all_errors else None

    city_order = [city for city in ["Chicago", "Atlanta", "Dallas", "Buenos Aires"] if city in OBSERVED_AUDIT_CITIES]
    for city in sorted(OBSERVED_AUDIT_CITIES):
        if city not in city_order:
            city_order.append(city)

    coverage_with_sample = 0
    coverage_ready = 0
    city_rows = []
    for city in city_order:
        city_entries = [item for item in rows if item.get("city") == city]
        city_errors = [item["_error_c"] for item in city_entries if item.get("_error_c") is not None]
        city_abs_errors = [item["_abs_error_c"] for item in city_entries if item.get("_abs_error_c") is not None]
        count = len(city_entries)
        if count > 0:
            coverage_with_sample += 1
        interpretable = count >= OBSERVED_FORECAST_MIN_SAMPLE and bool(city_abs_errors)
        if interpretable:
            coverage_ready += 1
        city_mae = round(sum(city_abs_errors) / len(city_abs_errors), 1) if interpretable else None
        city_bias = round(sum(city_errors) / len(city_errors), 1) if interpretable and city_errors else None
        last_date = city_entries[0].get("date", "") if city_entries else ""
        if count == 0:
            status = "bad"
            tag = "Sin muestra"
            detail = "sin casos NOAA todavia"
        elif interpretable:
            status = "good"
            tag = "Interpretable"
            detail = f"{count} casos | MAE {city_mae:.1f}C | ultimo {last_date}"
        else:
            status = "waiting"
            tag = "Acumulando"
            detail = f"{count}/{OBSERVED_FORECAST_MIN_SAMPLE} casos para leer bias | ultimo {last_date}"
        city_rows.append({
            "city": city,
            "count": count,
            "count_display": f"{count} caso" if count == 1 else f"{count} casos",
            "status": status,
            "tag": tag,
            "detail": detail,
            "bias_display": _fmt_temp(city_bias, signed=True) if city_bias is not None else "acumulando muestra...",
        })

    latest_rows = []
    for item in rows[:20]:
        latest_rows.append({
            "city": item.get("city", "?"),
            "date": item.get("date", "?"),
            "forecast_display": _fmt_temp(item.get("forecast_temp_c")),
            "observed_display": _fmt_temp(item.get("observed_temp_c")),
            "error_display": _fmt_temp(item.get("_error_c"), signed=True),
            "error_badge": _error_badge(item.get("_abs_error_c")),
            "source": item.get("source", "?"),
        })

    kpis_gated = sample_size < OBSERVED_FORECAST_GLOBAL_TARGET
    if sample_size < OBSERVED_FORECAST_MIN_SAMPLE:
        note_level = "muted"
        note = (
            "acumulando muestra... los KPIs NOAA se activan con al menos "
            f"{OBSERVED_FORECAST_MIN_SAMPLE} casos observados."
        )
    elif sample_size < OBSERVED_FORECAST_GLOBAL_TARGET:
        note_level = "warn"
        note = (
            "lectura global preliminar: MAE y bias ya son visibles, pero conviene "
            f"llegar a {OBSERVED_FORECAST_GLOBAL_TARGET} casos antes de leer sesgo global."
        )
    else:
        note_level = "good"
        note = (
            "muestra global util: revisar tambien la distribucion por ciudad. "
            f"El bias por ciudad solo es interpretable con >= {OBSERVED_FORECAST_MIN_SAMPLE} casos."
        )

    return {
        "sample_size": sample_size,
        "sample_display": f"{sample_size} mercado" if sample_size == 1 else f"{sample_size} mercados",
        "mae_display": _fmt_temp(mae_c) if mae_c is not None else "acumulando muestra...",
        "bias_display": _fmt_temp(bias_c, signed=True) if bias_c is not None else "acumulando muestra...",
        "coverage_display": f"{coverage_with_sample} / {len(city_order)} ciudades con muestra",
        "kpis_gated": kpis_gated,
        "kpis_gate_message": (
            f"Muestra insuficiente — {sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET}. "
            "MAE/Bias se habilitan al alcanzar el umbral."
        ),
        "coverage_detail": (
            f"{coverage_ready} / {len(city_order)} con >= {OBSERVED_FORECAST_MIN_SAMPLE} casos"
            if city_order else
            "sin ciudades activas configuradas"
        ),
        "city_rows": city_rows,
        "latest_rows": latest_rows,
        "note": note,
        "note_level": note_level,
        "last_record_display": _fmt_checked_at(rows[0].get("checked_at")) if rows else "n/d",
        "kpis_ready": kpis_ready,
        "global_ready": global_ready,
    }


def build_dashboard_city_accuracy_views(city_accuracy=None, city_policy_metrics=None):
    """Separa rendimiento NOAA-verificado vs legado para no mezclar eras operativas."""
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if city_policy_metrics is None:
        city_policy_metrics = get_city_policy_metrics()

    def _risk_meta(trades, win_rate, pnl):
        if trades >= CITY_MIN_TRADES_FOR_BLOCK and win_rate <= CITY_BLOCK_WIN_RATE:
            return "critical", "Crítica"
        if pnl < 0 or win_rate < 50.0:
            return "watch", "Observación"
        return "good", "OK"

    verified_rows = []
    legacy_rows = []

    all_cities = sorted(set(city_accuracy.keys()) | set(city_policy_metrics.keys()))
    for city in all_cities:
        total_stats = city_accuracy.get(city, {}) if isinstance(city_accuracy, dict) else {}
        policy_stats = city_policy_metrics.get(city, {}) if isinstance(city_policy_metrics, dict) else {}
        verified = policy_stats.get("verified", {}) if isinstance(policy_stats, dict) else {}
        legacy = policy_stats.get("legacy", {}) if isinstance(policy_stats, dict) else {}

        verified_trades = int(verified.get("trades", 0) or 0)
        verified_win_rate = float(verified.get("win_rate", 0.0) or 0.0)
        verified_pnl = round(float(verified.get("pnl", 0.0) or 0.0), 2)
        if verified_trades > 0:
            risk_level, risk_label = _risk_meta(verified_trades, verified_win_rate, verified_pnl)
            verified_rows.append({
                "city": city,
                "trades": verified_trades,
                "win_rate": round(verified_win_rate, 1),
                "pnl": verified_pnl,
                "risk_level": risk_level,
                "risk_label": risk_label,
                "basis_label": "NOAA verificado",
            })

        legacy_trades = int(legacy.get("trades", 0) or 0)
        legacy_win_rate = float(legacy.get("win_rate", 0.0) or 0.0)
        legacy_pnl = round(float(legacy.get("pnl", 0.0) or 0.0), 2)
        if legacy_trades > 0:
            total_trades = int(total_stats.get("trades", 0) or 0)
            legacy_rows.append({
                "city": city,
                "trades": legacy_trades,
                "win_rate": round(legacy_win_rate, 1),
                "pnl": legacy_pnl,
                "risk_level": "muted",
                "risk_label": "Legacy",
                "basis_label": (
                    "Solo legado"
                    if verified_trades == 0 and total_trades == legacy_trades
                    else "Legado remanente"
                ),
            })

    verified_rows.sort(key=lambda item: (
        0 if item["risk_level"] == "critical" else 1 if item["risk_level"] == "watch" else 2,
        item["win_rate"],
        item["pnl"],
        -item["trades"],
        item["city"],
    ))
    legacy_rows.sort(key=lambda item: (
        item["win_rate"],
        item["pnl"],
        -item["trades"],
        item["city"],
    ))

    return {
        "verified_rows": verified_rows[:8],
        "legacy_rows": legacy_rows[:8],
        "verified_count": len(verified_rows),
        "legacy_count": len(legacy_rows),
        "verified_note": (
            "Mide solo cierres enlazados con NOAA por city+date. Esta es la capa util para juzgar la operativa nueva."
        ),
        "legacy_note": (
            "Mantiene el historico previo o no enlazado con NOAA. Sirve como contexto, pero no debe mandar sobre la policy nueva."
        ),
    }


def build_dashboard_city_observation(audit=None, city_accuracy=None, city_policy_metrics=None):
    """Resume el estado operativo/observacional por ciudad sin promocionar nada automaticamente."""
    if audit is None:
        audit = load_audit_data()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if city_policy_metrics is None:
        city_policy_metrics = get_city_policy_metrics(audit=audit)

    observed_counts = {}
    observed_last_date = {}
    for raw in audit.get(OBSERVED_AUDIT_KEY, []):
        if not isinstance(raw, dict) or raw.get("source") != "noaa_ncei":
            continue
        city = raw.get("city")
        if not city:
            continue
        observed_counts[city] = observed_counts.get(city, 0) + 1
        market_date = str(raw.get("date") or "").strip()
        if market_date and market_date > observed_last_date.get(city, ""):
            observed_last_date[city] = market_date

    policy_state = load_city_policy_state()
    auto_canary = set((policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}).keys())
    auto_shadow_dict = policy_state.get("auto_shadow_cities", {}) if isinstance(policy_state, dict) else {}
    auto_shadow = set(auto_shadow_dict.keys()) if isinstance(auto_shadow_dict, dict) else set()
    auto_blocked = policy_state.get("auto_blocked_cities", {}) if isinstance(policy_state, dict) else {}
    auto_blocked_names = set(auto_blocked.keys()) if isinstance(auto_blocked, dict) else set()
    tracked_cities = (
        set(ACTIVE_TRADING_CITIES)
        | set(CANARY_TRADING_CITIES)
        | auto_canary
        | auto_shadow
        | auto_blocked_names
        | set(OBSERVED_AUDIT_CITIES)
        | set(city_accuracy.keys())
    )
    tracked_cities |= {city for city in RESOLUTION_ICAO if is_city_blocked(city)}
    # Filter out sentinel values like "NONE"
    tracked_cities = {c for c in tracked_cities if c.upper() not in {"NONE", ""}}

    rows = []
    active_count = 0
    blocked_count = 0
    observed_ready_count = 0
    observed_configured_count = 0

    for city in tracked_cities:
        city_mode = get_effective_city_mode(city, policy_state=policy_state)
        active = city_mode in {"active", "canary"}
        blocked = city_mode == "blocked"
        auto_shadow_meta = auto_shadow_dict.get(city, {}) if isinstance(auto_shadow_dict, dict) else {}
        auto_block_meta = auto_blocked.get(city, {}) if isinstance(auto_blocked, dict) else {}
        resolution_meta = RESOLUTION_ICAO.get(city, {})
        observed_proxy_helper = globals().get("_city_has_observed_proxy")
        noaa_configured = observed_proxy_helper(city) if callable(observed_proxy_helper) else (
            city in OBSERVED_AUDIT_CITIES or bool(resolution_meta.get("noaa_station_id"))
        )
        observed_count = int(observed_counts.get(city, 0) or 0)
        observed_last = observed_last_date.get(city, "n/d")
        interpretable = noaa_configured and observed_count >= OBSERVED_FORECAST_MIN_SAMPLE

        stats = city_accuracy.get(city, {})
        trades = int(stats.get("trades", 0) or 0)
        wins = int(stats.get("wins", 0) or 0)
        win_rate = float(stats.get("win_rate", 0.0) or 0.0)
        pnl = round(float(stats.get("pnl", 0.0) or 0.0), 2)
        policy_stats = city_policy_metrics.get(city, {}) if isinstance(city_policy_metrics, dict) else {}
        verified_stats = policy_stats.get("verified", {}) if isinstance(policy_stats, dict) else {}
        legacy_stats = policy_stats.get("legacy", {}) if isinstance(policy_stats, dict) else {}
        policy_bucket = policy_stats.get("policy", {}) if isinstance(policy_stats, dict) else {}
        policy_source = str(policy_stats.get("policy_source") or ("legacy" if trades > 0 else "none"))
        policy_is_provisional = bool(policy_stats.get("policy_is_provisional")) if isinstance(policy_stats, dict) else False
        policy_trades = int(policy_bucket.get("trades", 0) or 0)
        policy_wins = int(policy_bucket.get("wins", 0) or 0)
        policy_win_rate = float(policy_bucket.get("win_rate", 0.0) or 0.0)
        policy_pnl = round(float(policy_bucket.get("pnl", 0.0) or 0.0), 2)
        verified_trades = int(verified_stats.get("trades", 0) or 0)
        legacy_trades = int(legacy_stats.get("trades", 0) or 0)

        if active:
            active_count += 1
        if blocked:
            blocked_count += 1
        if noaa_configured:
            observed_configured_count += 1
        if interpretable:
            observed_ready_count += 1

        if _is_shadow_only():
            if city_mode == "canary":
                trading_label = "Canary (shadow)"
                trading_badge = "warn"
                auto_canary_dict = policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}
                auto_canary_meta = auto_canary_dict.get(city, {}) if isinstance(auto_canary_dict, dict) else {}
                promoted_at_raw = auto_canary_meta.get("promoted_at", "") if isinstance(auto_canary_meta, dict) else ""
                promoted_at = promoted_at_raw[:10] if promoted_at_raw else "?"
                trading_detail = f"canary autopromovida ({promoted_at}) pero shadow-only override activo: sin BUY real"
            elif city_mode == "active":
                trading_label = "Activa (shadow)"
                trading_badge = "warn"
                trading_detail = "active allowlist pero shadow-only override activo: sin BUY real"
            elif blocked:
                trading_label = "Bloqueada"
                trading_badge = "bad"
                if auto_block_meta:
                    trading_detail = f"descarte real persistido: {auto_block_meta.get('reason', 'fuera de juego')}"
                else:
                    trading_detail = "sin NOAA configurado: fuera de observacion hasta nueva revision manual"
            elif auto_shadow_meta:
                trading_label = "Shadow degradada"
                trading_badge = "warn"
                trading_detail = auto_shadow_meta.get("reason") or "se sigue observando, pero sin BUY real"
            else:
                trading_label = "Shadow"
                trading_badge = "muted"
                trading_detail = "sin BUY real; observacion activa"
        elif city_mode == "active":
            trading_label = "Activa"
            trading_badge = "good"
            trading_detail = "BUY habilitado en el scan"
        elif city_mode == "canary":
            trading_label = "Canary"
            trading_badge = "accent"
            trading_detail = f"BUY habilitado en modo canary ({CANARY_POSITION_SCALE:.0%} sizing)"
        elif blocked:
            trading_label = "Bloqueada"
            trading_badge = "bad"
            if auto_block_meta:
                trading_detail = f"descarte real persistido: {auto_block_meta.get('reason', 'fuera de juego')}"
            else:
                trading_detail = "sin NOAA configurado: fuera de observacion hasta nueva revision manual"
        elif auto_shadow_meta:
            trading_label = "Shadow degradada"
            trading_badge = "warn"
            trading_detail = auto_shadow_meta.get("reason") or "se sigue observando, pero sin BUY real"
        else:
            trading_label = "Shadow"
            trading_badge = "muted"
            trading_detail = "sin BUY real; seguir observando para aprendizaje"

        if noaa_configured:
            if interpretable:
                noaa_label = "Interpretable"
                noaa_badge = "good"
                noaa_detail = f"{observed_count} casos | ultimo {observed_last}"
            elif observed_count > 0:
                noaa_label = "Acumulando"
                noaa_badge = "warn"
                noaa_detail = f"{observed_count}/{OBSERVED_FORECAST_MIN_SAMPLE} casos | ultimo {observed_last}"
            else:
                noaa_label = "Sin muestra"
                noaa_badge = "bad"
                noaa_detail = "NOAA configurado pero todavia sin casos"
        else:
            noaa_label = "Sin NOAA"
            noaa_badge = "muted"
            noaa_detail = "sin observed proxy para esta ciudad"

        if trades == 0:
            history_label = "Sin cierres"
            history_badge = "muted"
            history_detail = "sin muestra real validada todavia"
        elif policy_is_provisional and legacy_trades > 0:
            history_label = f"{wins}/{trades} | WR {win_rate:.1f}%"
            history_badge = "warn"
            history_detail = (
                f"${pnl:+.2f} | historico legacy; policy provisional hasta sumar casos NOAA-verificados"
            )
        elif policy_trades >= CITY_MIN_TRADES_FOR_BLOCK and policy_win_rate <= CITY_BLOCK_WIN_RATE:
            history_label = f"{wins}/{trades} | WR {win_rate:.1f}%"
            history_badge = "bad"
            history_detail = (
                f"${pnl:+.2f} | historico NOAA-verificado malo ({policy_wins}/{policy_trades})"
            )
        elif pnl > 0 or win_rate >= 50.0:
            history_label = f"{wins}/{trades} | WR {win_rate:.1f}%"
            history_badge = "good"
            history_detail = f"${pnl:+.2f} | historial por ahora favorable"
        else:
            history_label = f"{wins}/{trades} | WR {win_rate:.1f}%"
            history_badge = "warn"
            history_detail = f"${pnl:+.2f} | historial mixto o flojo"

        if active and interpretable:
            state_label = "Operando con observabilidad"
            state_badge = "good"
            state_detail = "allowlist activa + NOAA interpretable"
        elif active and noaa_configured:
            state_label = "Activa con muestra incipiente"
            state_badge = "warn"
            state_detail = f"NOAA {observed_count}/{OBSERVED_FORECAST_MIN_SAMPLE} antes de leer bias"
        elif blocked:
            state_label = "Bloqueada"
            state_badge = "bad"
            if auto_block_meta:
                state_detail = f"descarte real persistido {auto_block_meta.get('triggered_at', 'n/d')}"
            else:
                state_detail = "sin NOAA configurado; no conviene observarla todavia"
        elif noaa_configured and interpretable:
            state_label = "Lista para revisar"
            state_badge = "accent"
            state_detail = "proxy observado util, pero aun sin activar BUY"
        elif auto_shadow_meta:
            state_label = "Shadow degradada"
            state_badge = "warn"
            state_detail = auto_shadow_meta.get("reason") or "historico malo; sigue en observacion activa"
        elif noaa_configured:
            state_label = "Shadow observada"
            state_badge = "accent"
            state_detail = "proxy activo; falta muestra antes de decidir"
        elif trades > 0:
            state_label = "Referencia historica"
            state_badge = "muted"
            state_detail = "tuvo operaciones, pero hoy falta observabilidad"
        else:
            state_label = "Shadow sin NOAA"
            state_badge = "muted"
            state_detail = "no hay NOAA ni evidencia suficiente para promover"

        if active:
            sort_rank = 0
        elif noaa_configured and (observed_count > 0 or trades > 0):
            sort_rank = 1
        elif trades > 0:
            sort_rank = 2
        elif blocked:
            sort_rank = 3
        else:
            sort_rank = 4

        rows.append({
            "city": city,
            "city_mode": city_mode,
            "active": active,
            "blocked": blocked,
            "noaa_configured": noaa_configured,
            "interpretable": interpretable,
            "observed_count": observed_count,
            "observed_goal": OBSERVED_FORECAST_MIN_SAMPLE,
            "observed_progress_pct": int(min(100, round((observed_count / max(1, OBSERVED_FORECAST_MIN_SAMPLE)) * 100))),
            "trades": trades,
            "wins": wins,
            "win_rate": round(win_rate, 1),
            "pnl": pnl,
            "policy_source": policy_source,
            "policy_is_provisional": policy_is_provisional,
            "policy_trades": policy_trades,
            "policy_wins": policy_wins,
            "policy_win_rate": round(policy_win_rate, 1),
            "policy_pnl": policy_pnl,
            "verified_trades": verified_trades,
            "legacy_trades": legacy_trades,
            "trading_label": trading_label,
            "trading_badge": trading_badge,
            "trading_detail": trading_detail,
            "noaa_label": noaa_label,
            "noaa_badge": noaa_badge,
            "noaa_detail": noaa_detail,
            "history_label": history_label,
            "history_badge": history_badge,
            "history_detail": history_detail,
            "state_label": state_label,
            "state_badge": state_badge,
            "state_detail": state_detail,
            "policy_action": auto_block_meta.get("action", ""),
            "policy_reason": auto_block_meta.get("reason", ""),
            "policy_metrics": auto_block_meta.get("metrics", {}),
            "policy_changed_at": auto_block_meta.get("triggered_at", ""),
            "_sort": (
                sort_rank,
                0 if active else 1,
                0 if interpretable else 1 if observed_count > 0 else 2,
                -observed_count,
                -trades,
                city,
            ),
        })

    rows.sort(key=lambda item: item["_sort"])
    for row in rows:
        row.pop("_sort", None)

    active_rows = [row for row in rows if row.get("active")]
    watch_rows = [
        row for row in rows
        if not row.get("active") and not row.get("blocked") and (
            row.get("noaa_configured") or row.get("trades", 0) > 0
        )
    ]
    blocked_rows = [row for row in rows if row.get("blocked")]

    observed_target_display = observed_configured_count if observed_configured_count else 0
    summary = (
        f"{active_count} activas | "
        f"{observed_ready_count}/{observed_target_display} NOAA interpretables | "
        f"{blocked_count} bloqueadas"
    )
    note = (
        "Esta tabla no promociona ciudades automaticamente: resume allowlist actual, "
        "cobertura NOAA y cierres validados para saber que es operativa real, "
        "que es solo referencia y que sigue sin observabilidad."
    )

    return {
        "tracked_count": len(rows),
        "active_count": active_count,
        "blocked_count": blocked_count,
        "observed_ready_count": observed_ready_count,
        "observed_configured_count": observed_configured_count,
        "summary": summary,
        "note": note,
        "note_level": "muted" if observed_ready_count < observed_configured_count else "good",
        "rows": rows,
        "active_rows": active_rows,
        "watch_rows": watch_rows,
        "blocked_rows": blocked_rows,
    }


def _shadow_condition_code(question):
    """Extract directional condition code from question text."""
    parsed = parse_temperature_question(str(question or ""))
    if isinstance(parsed, dict):
        condition = str(parsed.get("condition", "") or "")
        if condition in {"at_or_above", "at_or_below"}:
            return condition
        if condition in {"range", "exact"}:
            return "range/exact"
    q = str(question or "").lower()
    if "above" in q or "higher" in q:
        return "at_or_above"
    if "below" in q:
        return "at_or_below"
    if "between" in q or "exactly" in q:
        return "range/exact"
    return "otro"


def _shadow_condition_label(question):
    """Translate the shadow condition into a short user-facing label."""
    condition = _shadow_condition_code(question)
    if condition == "at_or_above":
        return "≥ umbral"
    if condition == "at_or_below":
        return "≤ umbral"
    if condition == "range/exact":
        return "rango/exacta"
    return "direccional"


def _extract_threshold_display_from_question(question):
    """Build a human-readable threshold fallback from the market question."""
    q = str(question or "")
    unit_gap = r'\s*(?:[^0-9A-Za-z\s])?\s*'
    patterns = [
        rf'(?:above|below)\s+(-?\d+(?:\.\d+)?){unit_gap}([FCfc])',
        rf'(-?\d+(?:\.\d+)?){unit_gap}([FCfc])\s+or\s+(?:above|below)',
        rf'(?:at\s+most|at\s+least)\s+(-?\d+(?:\.\d+)?){unit_gap}([FCfc])',
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            break
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).upper()
    value_display = f"{int(value)}" if value.is_integer() else f"{value:.1f}"
    return f"umbral {value_display}°{unit}"


def _build_shadow_forecast_fields(row):
    """Normalize forecast fields for shadow rows across both builder branches."""
    question = row.get("question", "")
    forecast_display = row.get("forecast_display")
    forecast_max = row.get("forecast_max")

    if isinstance(forecast_display, str) and forecast_display.strip():
        return {
            "forecast_display": forecast_display.strip(),
            "forecast_badge": None,
        }

    try:
        if forecast_max is not None:
            forecast_value = float(forecast_max)
            return {
                "forecast_display": f"{forecast_value:.1f}C",
                "forecast_badge": None,
            }
    except (TypeError, ValueError):
        pass

    threshold_display = _extract_threshold_display_from_question(question)
    if threshold_display:
        return {
            "forecast_display": threshold_display,
            "forecast_badge": None,
        }

    return {
        "forecast_display": "dato faltante en origen",
        "forecast_badge": "muted",
    }


def _build_recent_shadow_rows(shadow_tracking):
    """Build shadow signal rows for the dashboard — only directional signals.

    Strategy: first try recent_opportunities with edge_hit=True.
    If empty (legacy data where recent_opportunities is overwhelmed by
    condition_filtered entries), fall back to per-city recent_edges
    filtered to directional questions (above/below) with edge > 0.
    """
    if not isinstance(shadow_tracking, dict):
        return []

    def _strip_resolution_fields(row):
        clean_row = dict(row)
        clean_row.pop("resolution_label", None)
        clean_row.pop("resolution_badge", None)
        return clean_row

    # Primary: directional signals from recent_opportunities
    recent = shadow_tracking.get("recent_opportunities", [])
    directional = [
        {
            **_strip_resolution_fields(row),
            **_build_shadow_forecast_fields(row),
            "condition_label": _shadow_condition_label(row.get("question")),
        }
        for row in recent
        if row.get("edge_hit")
    ]
    if directional:
        return directional[:15]

    # Fallback: per-city recent_edges, filtered to directional only
    cities = shadow_tracking.get("cities", {})
    all_edges = []
    for city_name, city_data in cities.items():
        if not isinstance(city_data, dict):
            continue
        for edge in city_data.get("recent_edges", []):
            if not isinstance(edge, dict):
                continue
            condition_code = _shadow_condition_code(edge.get("question"))
            if condition_code not in ("at_or_above", "at_or_below"):
                continue
            edge_pct = float(edge.get("edge_pct", 0) or 0)
            if edge_pct <= 0:
                continue
            all_edges.append({
                "city": city_name,
                "date": edge.get("date", ""),
                "question": edge.get("question", ""),
                "side": edge.get("side", ""),
                "edge_pct": edge_pct,
                "expected_value": float(edge.get("expected_value", 0) or 0),
                "market_price": edge.get("market_price"),
                "our_prob": edge.get("our_prob"),
                "forecast_max": edge.get("forecast_max"),
                **_build_shadow_forecast_fields(edge),
                "seen_at": edge.get("seen_at", ""),
                "condition_label": _shadow_condition_label(edge.get("question")),
            })
    all_edges.sort(key=lambda r: str(r.get("seen_at", "")), reverse=True)
    return all_edges[:15]


def _city_decision_gates(
    *,
    trades,
    win_rate,
    pnl,
    history_bad,
    provisional_review,
    degraded,
    blocked,
    removable_active,
    degradation_reason,
    block_reason,
    shadow_seen,
    shadow_edges,
    shadow_cycles,
    shadow_best_edge,
    promotable_shadow,
    interpretable,
    noaa_configured,
    observed_count,
    observed_goal,
):
    """
    Computa los 3 gates (A historial, B shadow, C NOAA) para una ciudad en el ranking.
    Contrato público documentado en docs/control-center-r1-contract.md.
    Retorna {"gate_a": {...}, "gate_b": {...}, "gate_c": {...}, "gates_summary": "..."}.
    """
    # --- Gate A: historial real (trades cerrados) ---
    is_bad_history = bool(history_bad or degraded or blocked or removable_active)
    if is_bad_history:
        gate_a_state = "bad"
        gate_a_label = "Malo"
        gate_a_badge = "bad"
        if blocked and block_reason:
            gate_a_detail = block_reason
        elif degraded and degradation_reason:
            gate_a_detail = degradation_reason
        elif removable_active or history_bad:
            gate_a_detail = f"regla de salida: {trades} trades, WR {win_rate:.1f}%, PnL ${pnl:+.2f}"
        else:
            gate_a_detail = f"{trades} trades, WR {win_rate:.1f}%, PnL ${pnl:+.2f}"
    elif provisional_review and trades > 0:
        gate_a_state = "provisional"
        gate_a_label = "Provisional"
        gate_a_badge = "warn"
        gate_a_detail = f"legacy bajo review: {trades} trades, WR {win_rate:.1f}%, PnL ${pnl:+.2f}"
    elif trades > 0:
        gate_a_state = "clean"
        gate_a_label = "Limpio"
        gate_a_badge = "good"
        gate_a_detail = f"{trades} trades, WR {win_rate:.1f}%, PnL ${pnl:+.2f}"
    else:
        gate_a_state = "no_data"
        gate_a_label = "Sin datos"
        gate_a_badge = "muted"
        gate_a_detail = "sin trades reales"

    # --- Gate B: shadow signal ---
    has_shadow_activity = shadow_seen > 0 or shadow_edges > 0 or shadow_cycles > 0
    if promotable_shadow:
        gate_b_state = "ready"
        gate_b_label = "Lista"
        gate_b_badge = "good"
        gate_b_detail = f"{shadow_edges} edges, {shadow_cycles} ciclos, pico {shadow_best_edge:.1f}%"
    elif has_shadow_activity:
        gate_b_state = "building"
        gate_b_label = "Construyendo"
        gate_b_badge = "accent"
        gate_b_detail = f"{shadow_edges} edges, {shadow_cycles} ciclos, pico {shadow_best_edge:.1f}%"
    else:
        gate_b_state = "empty"
        gate_b_label = "Vacío"
        gate_b_badge = "muted"
        gate_b_detail = "sin actividad shadow"

    # --- Gate C: NOAA observed proxy ---
    if interpretable:
        gate_c_state = "interpretable"
        gate_c_label = "Interpretable"
        gate_c_badge = "good"
        gate_c_detail = f"{observed_count} casos NOAA"
    elif noaa_configured and observed_count > 0:
        gate_c_state = "partial"
        gate_c_label = "Parcial"
        gate_c_badge = "warn"
        gate_c_detail = f"{observed_count}/{observed_goal} casos NOAA"
    elif noaa_configured:
        gate_c_state = "waiting"
        gate_c_label = "Sin muestra"
        gate_c_badge = "warn"
        gate_c_detail = "NOAA configurado pero todavia sin casos"
    else:
        gate_c_state = "none"
        gate_c_label = "Sin NOAA"
        gate_c_badge = "muted"
        gate_c_detail = "sin NOAA configurado"

    return {
        "gate_a": {
            "state": gate_a_state,
            "label": gate_a_label,
            "badge": gate_a_badge,
            "detail": gate_a_detail,
        },
        "gate_b": {
            "state": gate_b_state,
            "label": gate_b_label,
            "badge": gate_b_badge,
            "detail": gate_b_detail,
        },
        "gate_c": {
            "state": gate_c_state,
            "label": gate_c_label,
            "badge": gate_c_badge,
            "detail": gate_c_detail,
        },
        "gates_summary": f"A {gate_a_state} · B {gate_b_state} · C {gate_c_state}",
    }


def build_dashboard_city_decisions(city_observation=None, city_accuracy=None, shadow_tracking=None, city_policy_metrics=None):
    """
    Convierte el seguimiento de ciudades en una lectura decisional:
    mantener, promover a canary, observar, revisar salida o bloquear.
    """
    if city_observation is None:
        city_observation = build_dashboard_city_observation()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if shadow_tracking is None:
        shadow_tracking = load_shadow_city_tracking()
    if city_policy_metrics is None:
        city_policy_metrics = get_city_policy_metrics()
    policy_state = load_city_policy_state()

    shadow_cities = shadow_tracking.get("cities", {}) if isinstance(shadow_tracking, dict) else {}
    shadow_summary = shadow_tracking.get("summary", {}) if isinstance(shadow_tracking, dict) else {}
    auto_canary = policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}
    auto_shadow = policy_state.get("auto_shadow_cities", {}) if isinstance(policy_state, dict) else {}
    auto_blocked = policy_state.get("auto_blocked_cities", {}) if isinstance(policy_state, dict) else {}
    transition_history = list((policy_state.get("transition_history", []) if isinstance(policy_state, dict) else [])[:20])
    policy = {
        "promote": {
            "edge_hits": SHADOW_CANARY_MIN_EDGE_HITS,
            "cycles": SHADOW_CANARY_MIN_CYCLES,
            "best_edge_pct": round(SHADOW_CANARY_MIN_BEST_EDGE, 1),
            "support": SHADOW_CANARY_MIN_SUPPORT,
            "label": (
                f"canary si shadow >= {SHADOW_CANARY_MIN_EDGE_HITS} edges, >= {SHADOW_CANARY_MIN_CYCLES} ciclos, "
                f"mejor edge >= {SHADOW_CANARY_MIN_BEST_EDGE:.1f}%, soporte >= {SHADOW_CANARY_MIN_SUPPORT} "
                f"y >= {SHADOW_CANARY_MIN_DAYS} dias en shadow"
            ),
        },
        "remove": {
            "trades": ALLOWLIST_REMOVE_MIN_TRADES,
            "win_rate": round(ALLOWLIST_REMOVE_MAX_WIN_RATE, 1),
            "pnl": round(ALLOWLIST_REMOVE_MAX_PNL, 2),
            "label": (
                f"degradar a shadow si active/canary tiene >= {ALLOWLIST_REMOVE_MIN_TRADES} trades NOAA-verificados, "
                f"WR <= {ALLOWLIST_REMOVE_MAX_WIN_RATE:.1f}% y PnL <= ${ALLOWLIST_REMOVE_MAX_PNL:.2f}"
            ),
        },
    }
    rows = []
    buckets = {
        "keep": [],
        "promote": [],
        "observe": [],
        "remove": [],
        "blocked": [],
    }
    priority_order = {
        "ready": 0,
        "near": 1,
        "watch": 2,
        "operating": 3,
        "no_touch": 4,
        "expelled": 5,
    }

    for row in city_observation.get("rows", []):
        city = row.get("city", "?")
        observed_audit_cities = globals().get("OBSERVED_AUDIT_CITIES")
        if not isinstance(observed_audit_cities, (set, list, tuple)):
            observed_audit_cities = (
                set(globals().get("FORECAST_BIAS_C", {}).keys())
                if isinstance(globals().get("FORECAST_BIAS_C"), dict)
                else set()
            )
        forecast_bias_value = (
            float(FORECAST_BIAS_C.get(city, 0.0))
            if city in observed_audit_cities
            else None
        )
        forecast_bias_applied = forecast_bias_value is not None
        forecast_bias_display = (
            f"{forecast_bias_value:+.2f}C"
            if forecast_bias_applied
            else "n/d"
        )
        forecast_bias_badge = "accent" if forecast_bias_applied else "muted"
        forecast_bias_detail = (
            f"FORECAST_BIAS_C aplicado en estimate_prob_with_city: {forecast_bias_value:+.2f}C"
            if forecast_bias_applied
            else "esta ciudad no usa correccion declarativa en FORECAST_BIAS_C"
        )
        shadow = shadow_cities.get(city, {}) if isinstance(shadow_cities, dict) else {}
        shadow_seen = int(shadow.get("markets_seen", 0) or 0)
        shadow_edges = int(shadow.get("edge_hits", 0) or 0)
        shadow_best_edge = round(float(shadow.get("best_edge_pct", 0) or 0), 1)
        shadow_cycles = int(shadow.get("cycles_seen", 0) or 0)
        trades = int(row.get("trades", 0) or 0)
        wins = int(row.get("wins", 0) or 0)
        pnl = round(float(row.get("pnl", 0) or 0), 2)
        win_rate = round(float(row.get("win_rate", 0) or 0), 1)
        policy_meta = city_policy_metrics.get(city, {}) if isinstance(city_policy_metrics, dict) else {}
        row_policy_source = str(
            row.get("policy_source")
            or policy_meta.get("policy_source")
            or ("legacy" if trades > 0 else "none")
        )
        row_policy_bucket = policy_meta.get("policy", {}) if isinstance(policy_meta, dict) else {}
        policy_is_provisional = bool(row.get("policy_is_provisional")) or bool(policy_meta.get("policy_is_provisional"))
        policy_trades = int(row.get("policy_trades", row_policy_bucket.get("trades", trades)) or 0)
        policy_wins = int(row.get("policy_wins", row_policy_bucket.get("wins", wins)) or 0)
        policy_win_rate = round(float(row.get("policy_win_rate", row_policy_bucket.get("win_rate", win_rate)) or 0), 1)
        policy_pnl = round(float(row.get("policy_pnl", row_policy_bucket.get("pnl", pnl)) or 0), 2)
        verified_trades = int(
            row.get(
                "verified_trades",
                (policy_meta.get("verified", {}) if isinstance(policy_meta, dict) else {}).get("trades", 0),
            ) or 0
        )
        legacy_trades = int(
            row.get(
                "legacy_trades",
                (policy_meta.get("legacy", {}) if isinstance(policy_meta, dict) else {}).get("trades", 0),
            ) or 0
        )
        active = bool(row.get("active"))
        blocked = bool(row.get("blocked"))
        city_mode = row.get("city_mode", "shadow")
        interpretable = bool(row.get("interpretable"))
        noaa_configured = bool(row.get("noaa_configured"))
        observed_count = int(row.get("observed_count", 0) or 0)
        observed_goal = int(row.get("observed_goal", OBSERVED_FORECAST_MIN_SAMPLE) or OBSERVED_FORECAST_MIN_SAMPLE)
        support_count = max(observed_count, trades, shadow_cycles)
        manual_proxy_review_helper = globals().get("_city_requires_manual_proxy_canary_review")
        needs_manual_proxy_review = (
            manual_proxy_review_helper(city) if callable(manual_proxy_review_helper) else False
        )
        # v10.6.17: calcular días en shadow desde first_seen_at
        _shadow_first_seen = shadow.get("first_seen_at", "")
        _shadow_days = 0
        if _shadow_first_seen:
            try:
                _dt = datetime.fromisoformat(_shadow_first_seen)
                _shadow_days = (datetime.now(timezone.utc) - _dt).days
            except Exception:
                _shadow_days = 0
        verified_history_bad = (
            row_policy_source == "noaa_verified"
            and policy_trades >= ALLOWLIST_REMOVE_MIN_TRADES
            and policy_win_rate <= ALLOWLIST_REMOVE_MAX_WIN_RATE
            and policy_pnl <= ALLOWLIST_REMOVE_MAX_PNL
        )
        removable_active = active and verified_history_bad
        history_bad = verified_history_bad
        auto_shadow_meta = auto_shadow.get(city, {}) if isinstance(auto_shadow, dict) else {}
        auto_canary_meta = auto_canary.get(city, {}) if isinstance(auto_canary, dict) else {}
        auto_block_meta = auto_blocked.get(city, {}) if isinstance(auto_blocked, dict) else {}
        latest_transition = next(
            (
                item for item in transition_history
                if isinstance(item, dict) and item.get("city") == city
            ),
            {},
        )
        degraded = bool(auto_shadow_meta) or (
            city_mode == "shadow"
            and isinstance(latest_transition, dict)
            and latest_transition.get("to") == "shadow"
        )
        # v10.6.20: anti-flapping — bloquea promoción shadow→canary si el historial
        # NOAA-verificado es malo. Sin este guard, una ciudad degradada por regla de
        # salida se re-promociona en el siguiente ciclo por sus edges shadow acumulados.
        # v10.6.41: extiende el anti-flapping a ciudades degradadas con historial legacy malo.
        # Sin esto, ciudades con policy_source="legacy" evaden el guard y se re-promocionan
        # aunque tengan WR/PnL malos (bug observado en Dallas: 17t WR 11.8% PnL -$1.60).
        degraded_history_bad = (
            degraded
            and policy_trades >= ALLOWLIST_REMOVE_MIN_TRADES
            and policy_win_rate <= ALLOWLIST_REMOVE_MAX_WIN_RATE
            and policy_pnl <= ALLOWLIST_REMOVE_MAX_PNL
        )
        promotable_shadow = (
            shadow_edges >= SHADOW_CANARY_MIN_EDGE_HITS
            and shadow_cycles >= SHADOW_CANARY_MIN_CYCLES
            and shadow_best_edge >= SHADOW_CANARY_MIN_BEST_EDGE
            and support_count >= SHADOW_CANARY_MIN_SUPPORT
            and _shadow_days >= SHADOW_CANARY_MIN_DAYS
            and not verified_history_bad
            and not degraded_history_bad
            and not needs_manual_proxy_review
        )
        provisional_review = (
            active
            and policy_is_provisional
            and legacy_trades >= ALLOWLIST_REMOVE_MIN_TRADES
            and win_rate <= ALLOWLIST_REMOVE_MAX_WIN_RATE
            and pnl <= ALLOWLIST_REMOVE_MAX_PNL
        )
        state_label = (
            "Activa" if city_mode == "active"
            else "Canary" if city_mode == "canary"
            else "Bloqueada" if blocked
            else "Shadow degradada" if degraded
            else "Referencia" if trades > 0 and not noaa_configured and shadow_seen == 0
            else "Shadow"
        )
        state_badge = (
            "good" if city_mode == "active"
            else "accent" if city_mode == "canary"
            else "bad" if blocked
            else "warn" if degraded
            else "muted" if state_label == "Referencia"
            else "warn"
        )

        if blocked:
            decision = "blocked"
            decision_label = "Bloqueada"
            badge = "bad"
            reason = (
                auto_block_meta.get("reason")
                or row.get("policy_reason")
                or row.get("state_detail")
                or "descarte real fuera de juego"
            )
        elif removable_active:
            decision = "remove"
            decision_label = "Pasar a shadow"
            badge = "bad"
            reason = (
                f"regla de salida disparada con historico NOAA-verificado: "
                f"{policy_wins}/{policy_trades} trades, WR {policy_win_rate:.1f}% y PnL ${policy_pnl:+.2f}; "
                "queda shadow para seguir observando"
            )
        elif active:
            decision = "keep"
            decision_label = "Mantener"
            if provisional_review:
                badge = "warn"
                reason = (
                    f"histórico legacy muy flojo ({wins}/{trades}, WR {win_rate:.1f}%, PnL ${pnl:+.2f}) "
                    "pero sin base NOAA-verificada suficiente; mantener sin autodegradar y revisar manualmente"
                )
            elif policy_is_provisional and legacy_trades > 0:
                badge = "accent"
                reason = (
                    f"historico legacy {wins}/{trades} (WR {win_rate:.1f}%) pero sin base NOAA-verificada suficiente; "
                    "mantener y observar antes de degradar"
                )
            else:
                badge = "good" if interpretable or pnl >= 0 else "accent"
                reason = (
                    "ciudad ya operativa; mantener mientras siga aportando evidencia"
                    if interpretable or pnl >= 0
                    else "sigue activa, pero aun sin evidencia suficiente para ampliar riesgo"
                )
        elif promotable_shadow:
            decision = "promote"
            decision_label = "Candidata a canary"
            badge = "accent"
            reason = f"regla canary disparada: {shadow_edges} edges shadow, {shadow_cycles} ciclos y pico {shadow_best_edge:.1f}%"
        elif noaa_configured or shadow_seen > 0 or trades > 0:
            decision = "observe"
            decision_label = "Shadow observada"
            badge = "warn" if shadow_seen > 0 else "muted"
            if verified_history_bad:
                reason = (
                    f"historial NOAA-verificado malo ({policy_wins}/{policy_trades}, "
                    f"WR {policy_win_rate:.1f}%, PnL ${policy_pnl:+.2f}); "
                    "promoción a canary bloqueada hasta reunir evidencia nueva mejor"
                )
            elif needs_manual_proxy_review:
                reason = (
                    "ciudad observada con revision manual requerida antes de canary; "
                    "auto-canary bloqueado hasta decision humana explicita"
                )
            elif shadow_seen > 0:
                reason = (
                    f"shadow ya vio {shadow_seen} mercados y {shadow_edges} edges; "
                    "falta decidir si merece canary"
                )
            elif policy_is_provisional and legacy_trades > 0:
                reason = (
                    f"historico legacy {wins}/{trades} separado del NOAA-verificado; "
                    "no conviene degradar ni promocionar solo por esa era"
                )
            elif noaa_configured and observed_count > 0:
                reason = "proxy NOAA activo, pero todavia sin muestra para promocionar"
            elif trades > 0:
                reason = "hay historico, pero hoy no hay señal suficiente para volver a operar"
            else:
                reason = "todavia sin evidencia accionable"
        else:
            decision = "observe"
            decision_label = "Sin evidencia suficiente"
            badge = "muted"
            reason = "ni NOAA ni shadow ni historico suficiente para tomar una decision"

        canary_gaps = []
        if shadow_edges < SHADOW_CANARY_MIN_EDGE_HITS:
            missing_edges = SHADOW_CANARY_MIN_EDGE_HITS - shadow_edges
            canary_gaps.append(f"{missing_edges} edge{'s' if missing_edges != 1 else ''}")
        if shadow_cycles < SHADOW_CANARY_MIN_CYCLES:
            missing_cycles = SHADOW_CANARY_MIN_CYCLES - shadow_cycles
            canary_gaps.append(f"{missing_cycles} ciclo{'s' if missing_cycles != 1 else ''}")
        if shadow_best_edge < SHADOW_CANARY_MIN_BEST_EDGE:
            canary_gaps.append(f"pico +{(SHADOW_CANARY_MIN_BEST_EDGE - shadow_best_edge):.1f}%")
        if support_count < SHADOW_CANARY_MIN_SUPPORT:
            missing_support = SHADOW_CANARY_MIN_SUPPORT - support_count
            canary_gaps.append(f"{missing_support} soporte")
        if _shadow_days < SHADOW_CANARY_MIN_DAYS:
            missing_days = SHADOW_CANARY_MIN_DAYS - _shadow_days
            canary_gaps.append(f"{missing_days} día{'s' if missing_days != 1 else ''} en shadow")
        if needs_manual_proxy_review:
            canary_gaps.append("revision proxy ICAO-only")

        if active:
            distance_label = "Ya operativa"
            distance_badge = "good" if city_mode == "active" else "accent"
            distance_detail = (
                "ya esta en allowlist activa"
                if city_mode == "active"
                else "ya opera con sizing reducido en canary"
            )
        elif blocked:
            distance_label = "Fuera de carrera"
            distance_badge = "bad"
            distance_detail = "bloqueada por politica; no es candidata mientras siga asi"
        elif degraded:
            distance_label = "Observando tras degradacion"
            distance_badge = "warn"
            distance_detail = auto_shadow_meta.get("reason") or latest_transition.get("reason") or "sigue en shadow para reunir evidencia nueva"
        elif promotable_shadow:
            distance_label = "Lista ahora"
            distance_badge = "good"
            distance_detail = "cumple la regla shadow -> canary"
        else:
            distance_label = f"{len(canary_gaps)} gap{'s' if len(canary_gaps) != 1 else ''}"
            distance_badge = "warn" if shadow_seen > 0 or observed_count > 0 else "muted"
            distance_detail = (
                "falta " + " + ".join(canary_gaps[:3])
                if canary_gaps else
                "acumula evidencia, pero aun no tiene señal clara para canary"
            )

        score = 0.0
        score += min(30.0, shadow_edges * 12.0)
        score += min(18.0, shadow_cycles * 8.0)
        if SHADOW_CANARY_MIN_BEST_EDGE > 0:
            score += min(12.0, max(0.0, shadow_best_edge) / SHADOW_CANARY_MIN_BEST_EDGE * 12.0)
        if noaa_configured:
            score += 6.0
        score += min(16.0, (observed_count / max(1, observed_goal)) * 16.0)
        if interpretable:
            score += 6.0
        if trades > 0:
            if history_bad:
                score -= 28.0
            elif provisional_review:
                score -= 12.0
            elif pnl > 0 or win_rate >= 50.0:
                score += 10.0
            else:
                score += 3.0
        if city_mode == "active":
            score += 24.0
        elif city_mode == "canary":
            score += 18.0
        if promotable_shadow:
            score = max(score, 82.0)
        if blocked:
            score = min(score, 8.0)
        if degraded:
            score = min(score, 18.0)
        if removable_active:
            score = min(score, 15.0)
        if provisional_review:
            score = min(score, 42.0)
        readiness_score = int(max(0.0, min(99.0, round(score))))

        if blocked:
            priority_group = "expelled"
            priority_label = "Bloqueada"
            priority_badge = "bad"
        elif degraded:
            priority_group = "watch"
            priority_label = "Seguir observando"
            priority_badge = "warn"
        elif removable_active or (history_bad and not active):
            priority_group = "no_touch"
            priority_label = "No tocar"
            priority_badge = "bad" if history_bad or removable_active else "muted"
        elif promotable_shadow:
            priority_group = "ready"
            priority_label = "Lista para canary"
            priority_badge = "good"
        elif provisional_review:
            priority_group = "watch"
            priority_label = "Revisar legado"
            priority_badge = "warn"
        elif not active and shadow_seen > 0 and not history_bad:
            priority_group = "near"
            priority_label = "Cerca de canary"
            priority_badge = "accent"
        elif active:
            priority_group = "operating"
            priority_label = "Operando"
            priority_badge = "good" if city_mode == "active" else "accent"
        elif noaa_configured or trades > 0 or shadow_seen > 0:
            priority_group = "watch"
            priority_label = "Seguir observando"
            priority_badge = "warn"
        else:
            priority_group = "no_touch"
            priority_label = "No tocar"
            priority_badge = "muted"

        if degraded or removable_active or history_bad:
            trend_label = "Enfriándose"
            trend_badge = "bad"
        elif provisional_review:
            trend_label = "Bajo review"
            trend_badge = "warn"
        elif promotable_shadow or (shadow_seen > 0 and shadow_edges > 0) or (observed_count > 0 and not active):
            trend_label = "Subiendo"
            trend_badge = "good" if promotable_shadow else "accent"
        else:
            trend_label = "Estable"
            trend_badge = "muted" if priority_group in {"no_touch", "operating"} else "warn"

        if degraded:
            main_reason = "shadow degradada por histórico real"
        elif removable_active:
            main_reason = "histórico real malo"
        elif blocked:
            main_reason = "bloqueada por política"
        elif promotable_shadow:
            main_reason = "shadow fuerte"
        elif shadow_seen > 0 and shadow_edges > 0:
            main_reason = "shadow prometedor"
        elif noaa_configured and observed_count == 0:
            main_reason = "sin muestra NOAA"
        elif noaa_configured and observed_count < observed_goal:
            main_reason = "NOAA aún corta"
        elif trades > 0 and pnl < 0:
            main_reason = "histórico mixto o flojo"
        elif trades == 0 and shadow_seen == 0:
            main_reason = "sin muestra"
        else:
            main_reason = "solo referencia"

        if provisional_review and not degraded and not removable_active:
            main_reason = "historico legacy bajo review"
        if removable_active:
            main_reason = "historico NOAA-verificado malo"

        gates = _city_decision_gates(
            trades=trades,
            win_rate=win_rate,
            pnl=pnl,
            history_bad=history_bad,
            provisional_review=provisional_review,
            degraded=degraded,
            blocked=blocked,
            removable_active=removable_active,
            degradation_reason=auto_shadow_meta.get("reason") or latest_transition.get("reason") or "",
            block_reason=auto_block_meta.get("reason") or "",
            shadow_seen=shadow_seen,
            shadow_edges=shadow_edges,
            shadow_cycles=shadow_cycles,
            shadow_best_edge=shadow_best_edge,
            promotable_shadow=promotable_shadow,
            interpretable=interpretable,
            noaa_configured=noaa_configured,
            observed_count=observed_count,
            observed_goal=observed_goal,
        )

        candidate = {
            "city": city,
            "decision": decision,
            "decision_label": decision_label,
            "badge": badge,
            "readiness_score": readiness_score,
            "gate_a": gates["gate_a"],
            "gate_b": gates["gate_b"],
            "gate_c": gates["gate_c"],
            "gates_summary": gates["gates_summary"],
            "score_badge": (
                "good" if readiness_score >= 80
                else "accent" if readiness_score >= 60
                else "warn" if readiness_score >= 35
                else "bad" if degraded or removable_active or history_bad
                else "muted"
            ),
            "priority_group": priority_group,
            "priority_label": priority_label,
            "priority_badge": priority_badge,
            "city_mode": city_mode,
            "state_label": state_label,
            "state_badge": state_badge,
            "active": active,
            "blocked": blocked,
            "degraded": degraded,
            "provisional_review": provisional_review,
            "interpretable": interpretable,
            "trades": trades,
            "wins": wins,
            "win_rate": win_rate,
            "pnl": pnl,
            "policy_source": row_policy_source,
            "policy_is_provisional": policy_is_provisional,
            "policy_trades": policy_trades,
            "policy_wins": policy_wins,
            "policy_win_rate": policy_win_rate,
            "policy_pnl": policy_pnl,
            "verified_trades": verified_trades,
            "legacy_trades": legacy_trades,
            "pnl_display": f"${pnl:+.2f}",
            "observed_display": f"{observed_count}/{observed_goal}",
            "forecast_bias_value": forecast_bias_value,
            "forecast_bias_applied": forecast_bias_applied,
            "forecast_bias_display": forecast_bias_display,
            "forecast_bias_badge": forecast_bias_badge,
            "forecast_bias_detail": forecast_bias_detail,
            "shadow_seen": shadow_seen,
            "shadow_edges": shadow_edges,
            "shadow_cycles": shadow_cycles,
            "shadow_best_edge": shadow_best_edge,
            "shadow_best_edge_display": f"{shadow_best_edge:.1f}%" if shadow_best_edge else "n/d",
            "distance_label": distance_label,
            "distance_badge": distance_badge,
            "distance_detail": distance_detail,
            "trend_label": trend_label,
            "trend_badge": trend_badge,
            "main_reason": main_reason,
            "support_count": support_count,
            "canary_gap_count": len(canary_gaps),
            "degradation_reason": auto_shadow_meta.get("reason") or latest_transition.get("reason") or "",
            "degradation_from": auto_shadow_meta.get("from_mode") or latest_transition.get("from") or "",
            "degradation_at": auto_shadow_meta.get("shadowed_at") or latest_transition.get("at") or "",
            "policy_action": auto_block_meta.get("action", row.get("policy_action", "")),
            "policy_metrics": auto_block_meta.get("metrics", row.get("policy_metrics", {})),
            "policy_changed_at": auto_block_meta.get("triggered_at", row.get("policy_changed_at", "")),
            "overlay_reason": (
                auto_canary_meta.get("reason") if city_mode == "canary"
                else auto_block_meta.get("reason") if city_mode == "blocked"
                else auto_shadow_meta.get("reason")
            ),
            "reason": reason,
            "trading_label": row.get("trading_label", ""),
            "history_label": row.get("history_label", ""),
            "noaa_label": row.get("noaa_label", ""),
            "_sort": (
                priority_order.get(priority_group, 9),
                -readiness_score,
                len(canary_gaps),
                -shadow_edges,
                -shadow_best_edge,
                -observed_count,
                -trades,
                city,
            ),
        }
        rows.append(candidate)
        buckets[decision].append(candidate)

    rows.sort(key=lambda item: item["_sort"])
    for item in rows:
        item.pop("_sort", None)

    for bucket_name in buckets:
        buckets[bucket_name].sort(
            key=lambda item: (
                0 if item.get("active") else 1,
                priority_order.get(item.get("priority_group"), 9),
                -int(item.get("readiness_score", 0) or 0),
                -int(item.get("shadow_edges", 0) or 0),
                -float(item.get("shadow_best_edge", 0) or 0),
                -int(item.get("trades", 0) or 0),
                item.get("city", ""),
            )
        )

    audit_loader = globals().get("load_audit_data")
    audit = audit_loader() if callable(audit_loader) else {}
    shadow_resolution_builder = globals().get("_build_shadow_noaa_resolution_stats")
    if callable(shadow_resolution_builder):
        shadow_resolution = shadow_resolution_builder(shadow_tracking, audit=audit)
    else:
        shadow_resolution = {"total_signals": 0, "matched": 0, "resolved": 0, "win_rate": 0.0}
    promotable = len(buckets["promote"])
    top_candidate_rows = [
        item for item in rows
        if item.get("priority_group") in {"ready", "near", "watch"}
        and not item.get("active")
        and not item.get("blocked")
        and not item.get("degraded")
    ]
    top_candidate = top_candidate_rows[0] if top_candidate_rows else None
    next_candidate = top_candidate_rows[1] if len(top_candidate_rows) > 1 else None
    cooling_rows = [item for item in rows if item.get("trend_label") == "Enfriandose"]
    noise_rows = [item for item in rows if item.get("priority_group") == "no_touch"]
    note = (
        "Esta tabla ordena ciudades por prioridad operativa real. "
        "Combina historico validado, evidencia NOAA, actividad shadow y overlay de politica "
        "para separar candidatas reales de degradadas, ruido o referencias. "
        f"Promover: {policy['promote']['label']}. "
        f"Salida: {policy['remove']['label']}."
    )
    summary = (
        f"{top_candidate.get('city') if top_candidate else 'Nadie'} lidera | "
        f"{promotable} listas para canary | "
        f"{len(cooling_rows)} enfriándose"
    )

    grouped_sections = [
        {
            "id": "operating",
            "label": "Operativas y candidatas",
            "badge": "good",
            "note": "Ciudades activas, canary o shadow con evidencia suficiente para seguimiento prioritario.",
            "rows": [
                item for item in rows
                if item.get("priority_group") in {"ready", "near", "operating"}
            ],
        },
        {
            "id": "observed_shadow",
            "label": "Shadow observadas",
            "badge": "accent",
            "note": "Ciudades con NOAA o evidencia shadow que conviene seguir mirando, pero sin promocion inmediata.",
            "rows": [
                item for item in rows
                if item.get("priority_group") == "watch" and not item.get("blocked")
            ],
        },
        {
            "id": "no_noaa",
            "label": "Sin NOAA util",
            "badge": "muted",
            "note": "Ciudades sin NOAA interpretable o sin pipeline observado util; sirven como contexto, no como prioridad operativa.",
            "rows": [
                item for item in rows
                if item.get("priority_group") == "no_touch" and not item.get("blocked")
            ],
        },
        {
            "id": "blocked",
            "label": "Fuera de observacion",
            "badge": "bad",
            "note": "Ciudades efectivamente bloqueadas porque no tienen NOAA utilizable o quedaron fuera por descarte real.",
            "rows": [
                item for item in rows
                if item.get("blocked")
            ],
        },
    ]
    for section in grouped_sections:
        section["count"] = len(section["rows"])

    effective_blocked_rows = [
        {"city": city, **(auto_blocked.get(city) or {})}
        for city in sorted(auto_blocked)
        if get_effective_city_mode(city, policy_state=policy_state) == "blocked"
    ]

    return {
        "summary": summary,
        "note": note,
        "note_level": "accent" if promotable else "warn" if top_candidate else "muted",
        "policy": policy,
        "rows": rows,
        "ranking_rows": rows,
        "grouped_sections": grouped_sections,
        "keep_rows": buckets["keep"],
        "promote_rows": buckets["promote"],
        "observe_rows": buckets["observe"],
        "remove_rows": buckets["remove"],
        "blocked_rows": buckets["blocked"],
        "ranking_summary": {
            "ready": len([item for item in rows if item.get("priority_group") == "ready"]),
            "near": len([item for item in rows if item.get("priority_group") == "near"]),
            "watch": len([item for item in rows if item.get("priority_group") == "watch"]),
            "operating": len([item for item in rows if item.get("priority_group") == "operating"]),
            "no_touch": len(noise_rows),
            "expelled": len([item for item in rows if item.get("priority_group") == "expelled"]),
        },
        "top_candidate": top_candidate,
        "next_candidate": next_candidate,
        "cooling_city": cooling_rows[0] if cooling_rows else None,
        "noise_city": noise_rows[0] if noise_rows else None,
        "shadow_summary": {
            "cycles_with_shadow": int(shadow_summary.get("cycles_with_shadow", 0) or 0),
            "opportunities_seen": int(shadow_summary.get("opportunities_seen", 0) or 0),
            "edge_hits": int(shadow_summary.get("edge_hits", 0) or 0),
            "promotable_cities": promotable,
        },
        "auto_state": {
            "canary_count": len(auto_canary),
            "shadow_count": len(auto_shadow),
            "blocked_count": len(effective_blocked_rows),
            "canary_rows": [
                {"city": city, **(auto_canary.get(city) or {})}
                for city in sorted(auto_canary)
            ],
            "shadow_rows": [
                {"city": city, **(auto_shadow.get(city) or {})}
                for city in sorted(auto_shadow)
            ],
            "blocked_rows": effective_blocked_rows,
            "transitions": list((policy_state.get("transition_history", []) if isinstance(policy_state, dict) else [])[:10]),
        },
        "recent_shadow_rows": _build_recent_shadow_rows(shadow_tracking),
    }


def sync_city_policy_state(notify=True):
    """
    Promueve shadow -> canary y degrada active/canary -> shadow cuando hay evidencia.
    No toca las env vars; aplica un overlay persistente en volumen.
    """
    policy_state = load_city_policy_state()
    audit = load_audit_data()
    city_accuracy = get_city_accuracy()
    city_policy_metrics = get_city_policy_metrics(audit=audit)
    shadow_tracking = load_shadow_city_tracking()
    city_observation = build_dashboard_city_observation(
        audit=audit,
        city_accuracy=city_accuracy,
        city_policy_metrics=city_policy_metrics,
    )
    city_decisions = build_dashboard_city_decisions(
        city_observation=city_observation,
        city_accuracy=city_accuracy,
        shadow_tracking=shadow_tracking,
        city_policy_metrics=city_policy_metrics,
    )

    auto_canary = policy_state.setdefault("auto_canary_cities", {})
    auto_shadow = policy_state.setdefault("auto_shadow_cities", {})
    auto_blocked = policy_state.setdefault("auto_blocked_cities", {})
    history = policy_state.setdefault("transition_history", [])
    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in city_decisions.get("rows", []):
        city = row.get("city", "?")
        current_mode = get_effective_city_mode(city, policy_state=policy_state)
        decision = row.get("decision")
        manual_proxy_review_helper = globals().get("_city_requires_manual_proxy_canary_review")
        needs_manual_proxy_review = (
            manual_proxy_review_helper(city) if callable(manual_proxy_review_helper) else False
        )
        if city in auto_canary and needs_manual_proxy_review:
            auto_canary.pop(city, None)
            history.append({
                "at": now_iso,
                "city": city,
                "from": "canary",
                "to": "shadow",
                "reason": "observed city requires manual review before auto-canary",
                "action": "auto_canary_revoked",
            })
            changed = True
            if notify:
                send_telegram(
                    f"🧪 <b>Canary revertida a shadow</b>\n"
                    f"{city} vuelve a <b>shadow</b>.\n"
                    "Ciudad observada con revision manual requerida antes de canary: "
                    "auto-canary bloqueado hasta decision humana explicita.\n"
                    "Sin BUY real por esta autopromocion."
                )
            continue

        if decision == "promote" and current_mode == "shadow" and city not in auto_blocked and city not in ACTIVE_TRADING_CITIES and not is_city_blocked(city) and not needs_manual_proxy_review:
            auto_canary[city] = {
                "promoted_at": now_iso,
                "reason": row.get("reason", ""),
                "best_edge_pct": row.get("shadow_best_edge"),
                "shadow_edges": row.get("shadow_edges"),
            }
            auto_shadow.pop(city, None)
            history.append({
                "at": now_iso,
                "city": city,
                "from": "shadow",
                "to": "canary",
                "reason": row.get("reason", ""),
            })
            changed = True
            if notify:
                send_telegram(
                    f"🧪 <b>Ciudad promovida a canary</b>\n"
                    f"{city} pasa de <b>shadow</b> a <b>canary</b>.\n"
                    f"{row.get('reason', '')}\n"
                    f"El bot ya puede abrir entradas pequeñas en esta ciudad."
                )

        if decision == "remove" and current_mode in {"active", "canary"}:
            auto_shadow[city] = _build_auto_city_shadow_policy(
                row=row,
                current_mode=current_mode,
                shadowed_at=now_iso,
            )
            auto_blocked.pop(city, None)
            auto_canary.pop(city, None)
            history.append({
                "at": now_iso,
                "city": city,
                "from": current_mode,
                "to": "shadow",
                "reason": row.get("reason", ""),
                "action": "auto_shadow",
                "metrics": auto_shadow[city].get("metrics", {}),
            })
            changed = True
            if notify:
                metrics = auto_shadow[city].get("metrics", {})
                send_telegram(
                    f"📉 <b>Ciudad degradada a shadow</b>\n"
                    f"{city} pasa de <b>{current_mode}</b> a <b>shadow</b>.\n"
                    f"{row.get('reason', '')}\n"
                    f"Evidencia: {metrics.get('wins', 0)}/{metrics.get('trades', 0)} trades, "
                    f"WR {metrics.get('win_rate', 0.0):.1f}%, PnL ${metrics.get('pnl', 0.0):+.2f}.\n"
                    f"Se corta el BUY real, pero la ciudad sigue en observacion activa para reunir evidencia nueva."
                )

    if changed:
        policy_state["updated_at"] = now_iso
        save_city_policy_state(policy_state)
    return policy_state


# =============================================================
# v10.6.11 — M5: alerta ciudad candidata a canary (one-shot)
# =============================================================

def _compute_city_decisions_for_alerts():
    """
    Reconstruye city_decisions con los mismos helpers que usa sync_city_policy_state
    pero aislado para poder consumirlo desde alertas sin duplicar lógica de transición.
    """
    audit = load_audit_data()
    city_accuracy = get_city_accuracy()
    city_policy_metrics = get_city_policy_metrics(audit=audit)
    shadow_tracking = load_shadow_city_tracking()
    city_observation = build_dashboard_city_observation(
        audit=audit,
        city_accuracy=city_accuracy,
        city_policy_metrics=city_policy_metrics,
    )
    return build_dashboard_city_decisions(
        city_observation=city_observation,
        city_accuracy=city_accuracy,
        shadow_tracking=shadow_tracking,
        city_policy_metrics=city_policy_metrics,
    )


def notify_canary_candidates(state):
    """
    Fires a one-shot Telegram alert when a shadow city first reaches the canary
    promotion rule (decision == "promote"). Does NOT mutate city_policy_state:
    the auto-promote logic in sync_city_policy_state keeps its own transition flow.

    Uses alerts_state["canary_candidate_notified"] as the idempotency map:
      { city: {"notified_at": iso, "reason": str, "shadow_edges": int, "best_edge": float} }

    An entry is cleared when the city no longer meets the promote rule, so the
    alert can fire again if the evidence reappears after a regression.

    Returns True if `state` was mutated (caller should persist it).
    """
    try:
        city_decisions = _compute_city_decisions_for_alerts()
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"canary candidates: no pude computar city_decisions ({e})")
        return False

    rows = city_decisions.get("rows", []) if isinstance(city_decisions, dict) else []
    notified = state.setdefault("canary_candidate_notified", {})
    if not isinstance(notified, dict):
        notified = {}
        state["canary_candidate_notified"] = notified

    current_candidates = {
        row.get("city"): row
        for row in rows
        if isinstance(row, dict)
        and row.get("city")
        and row.get("decision") == "promote"
    }

    changed = False
    now_iso = datetime.now(timezone.utc).isoformat()

    # Nuevas candidatas → enviar alerta y registrar one-shot.
    for city, row in current_candidates.items():
        if city in notified:
            continue
        reason = row.get("reason", "")
        shadow_edges = row.get("shadow_edges", 0)
        shadow_cycles = row.get("shadow_cycles") or row.get("support_count") or 0
        shadow_best_edge = row.get("shadow_best_edge", 0.0)
        observed_count = row.get("observed_count", 0)
        try:
            send_telegram(
                f"🎯 <b>Ciudad candidata a canary</b>\n"
                f"{city} cumple la regla shadow → canary.\n\n"
                f"Evidencia:\n"
                f"• Shadow edges: <b>{shadow_edges}</b>\n"
                f"• Mejor edge shadow: <b>{float(shadow_best_edge or 0):.1f}%</b>\n"
                f"• Ciclos shadow/soporte: <b>{shadow_cycles}</b>\n"
                f"• NOAA observados: <b>{observed_count}</b>\n\n"
                f"<i>{reason}</i>\n\n"
                f"El auto-promote puede activarse en este mismo ciclo; "
                f"revisar antes de confiar en BUYs en esta ciudad."
            )
        except Exception as e:
            logger = globals().get("log")
            if logger:
                logger.warning(f"canary candidates: fallo al enviar Telegram ({e})")
            continue
        notified[city] = {
            "notified_at": now_iso,
            "reason": reason,
            "shadow_edges": int(shadow_edges or 0),
            "best_edge": float(shadow_best_edge or 0),
        }
        changed = True

    # Ciudades que ya no son candidatas → limpiar flag para permitir re-disparo futuro.
    for city in list(notified.keys()):
        if city not in current_candidates:
            notified.pop(city, None)
            changed = True

    return changed


# =============================================================
# v10.6.11 — M4: resumen diario Telegram (08:00 UTC)
# =============================================================

def _daily_summary_cycles_last_24h(now):
    """
    Agrega ciclos de cycles_history.jsonl dentro de las últimas 24h.
    Retorna dict con cycles, markets_evaluated, with_edge, selected, shadow, buys_real.
    """
    stats = {
        "cycles": 0,
        "markets_evaluated": 0,
        "with_edge": 0,
        "selected": 0,
        "shadow": 0,
        "buys_real": 0,
        "buys_active": 0,
        "buys_canary": 0,
        "buys_other": 0,
    }
    cutoff = now - timedelta(hours=24)
    policy_state_loader = globals().get("load_city_policy_state")
    policy_state = policy_state_loader() if callable(policy_state_loader) else {}
    city_mode_helper = globals().get("get_effective_city_mode")
    try:
        records = load_cycle_history()
    except Exception:
        records = []
    for rec in records:
        ts_raw = rec.get("timestamp_utc", "")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except Exception:
            continue
        if ts < cutoff:
            continue
        stats["cycles"] += 1
        scan = rec.get("scan", {}) if isinstance(rec.get("scan"), dict) else {}
        stats["markets_evaluated"] += int(scan.get("markets_evaluated", 0) or 0)
        stats["with_edge"] += int(scan.get("with_edge", 0) or 0)
        stats["selected"] += int(scan.get("selected", 0) or 0)
        stats["shadow"] += int(scan.get("shadow", 0) or 0)
        buys = rec.get("buys", []) if isinstance(rec.get("buys"), list) else []
        stats["buys_real"] += len(buys)
        for buy in buys:
            if not isinstance(buy, dict):
                continue
            city = str(buy.get("city", "") or "").strip()
            city_mode = str(buy.get("city_mode", "") or "").strip().lower()
            if not city_mode and city:
                if callable(city_mode_helper):
                    city_mode = city_mode_helper(city, policy_state=policy_state)
                elif city in (globals().get("ACTIVE_TRADING_CITIES", []) or []):
                    city_mode = "active"
                elif city in (globals().get("CANARY_TRADING_CITIES", []) or []):
                    city_mode = "canary"
            if city_mode == "active":
                stats["buys_active"] += 1
            elif city_mode == "canary":
                stats["buys_canary"] += 1
            else:
                stats["buys_other"] += 1
    return stats


def _daily_summary_closed_trades_last_24h(now):
    """Resoluciones del día: trades cerrados en las últimas 24h.

    Separa trades recientes reales de resoluciones batch (market_resolved de
    fechas antiguas que el bot detecta hoy). El PnL neto solo cuenta trades
    reales; el batch se reporta aparte para no inflar la cifra del día.
    """
    batch_reasons = {"market_resolved", "market_resolved_yes"}
    stats = {
        "closed": 0, "wins": 0, "breakeven": 0, "losses": 0, "pnl": 0.0,
        "batch_closed": 0, "batch_pnl": 0.0,
    }
    cutoff = now - timedelta(hours=24)
    try:
        closed = _get_recent_closed_trades()
    except Exception:
        closed = []
    for rec in closed:
        closed_at_raw = rec.get("closed_at", "")
        if not closed_at_raw:
            continue
        try:
            closed_at = datetime.fromisoformat(closed_at_raw)
        except Exception:
            continue
        if closed_at < cutoff:
            continue
        pnl = float(rec.get("pnl_cash", 0) or 0)
        close_reason = str(rec.get("close_reason", "") or "")
        if close_reason in batch_reasons:
            stats["batch_closed"] += 1
            stats["batch_pnl"] += pnl
        else:
            stats["closed"] += 1
            stats["pnl"] += pnl
            if pnl > 0:
                stats["wins"] += 1
            elif pnl < 0:
                stats["losses"] += 1
            else:
                stats["breakeven"] += 1
    return stats


def _daily_summary_noaa_last_24h(now):
    """NOAA: filas observadas añadidas en últimas 24h + acumulado histórico."""
    stats = {"new_total": 0, "new_by_city": {}, "cumulative": 0}
    cutoff = now - timedelta(hours=24)
    try:
        audit = load_audit_data()
    except Exception:
        audit = {}
    rows = audit.get(OBSERVED_AUDIT_KEY, []) if isinstance(audit, dict) else []
    for row in rows:
        if not isinstance(row, dict) or row.get("source") != "noaa_ncei":
            continue
        stats["cumulative"] += 1
        checked_at_raw = row.get("checked_at", "")
        if not checked_at_raw:
            continue
        try:
            checked_at = datetime.fromisoformat(checked_at_raw)
        except Exception:
            continue
        if checked_at < cutoff:
            continue
        stats["new_total"] += 1
        city = row.get("city", "?")
        stats["new_by_city"][city] = stats["new_by_city"].get(city, 0) + 1
    return stats


def _get_live_operable_city_counts(policy_state=None):
    """Cuenta ciudades operables hoy por modo efectivo (active/canary)."""
    policy_state = _normalize_city_policy_state(policy_state or load_city_policy_state())
    auto_canary = policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}
    tracked = (
        set(ACTIVE_TRADING_CITIES)
        | set(CANARY_TRADING_CITIES)
        | set(auto_canary.keys() if isinstance(auto_canary, dict) else [])
    )
    tracked = {city for city in tracked if str(city).strip().upper() not in {"", "NONE"}}

    counts = {"active": 0, "canary": 0}
    for city in tracked:
        mode = get_effective_city_mode(city, policy_state=policy_state)
        if mode in counts:
            counts[mode] += 1
    return counts


def _format_operable_mode_label(active_count=0, canary_count=0, shadow_only=False):
    """Texto corto para Telegram con el universo operable actual."""
    if shadow_only:
        return "SHADOW-ONLY"

    parts = []
    if active_count:
        parts.append(f"{active_count} activa" if active_count == 1 else f"{active_count} activas")
    if canary_count:
        parts.append(f"{canary_count} canary")
    if not parts:
        return "sin ciudades operables"
    return " + ".join(parts)


def _format_buy_mode_tag(city_mode):
    """Tag compacto para distinguir compras active vs canary en Telegram."""
    mode = str(city_mode or "").strip().lower()
    if mode == "canary":
        return "CANARY"
    if mode == "active":
        return "ACTIVE"
    return mode.upper() if mode else "OPERABLE"


def _daily_summary_has_cycle_today(now):
    """True si ya hay al menos un ciclo real registrado hoy."""
    try:
        records = load_cycle_history()
    except Exception:
        records = []

    latest_ts = None
    for rec in records:
        ts_raw = rec.get("timestamp_utc", "")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except Exception:
            continue
        if ts > now:
            continue
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
    return bool(latest_ts and latest_ts.date() == now.date())


def _safe_float_text(value, suffix=""):
    if value is None:
        return "n/d"
    try:
        return f"{float(value):.1f}{suffix}"
    except Exception:
        return "n/d"


def _load_metar_log_only_digest(path=None):
    """Read the last manual METAR parity report. No network and no runtime writes."""
    report_path = path or _METAR_SHADOW_REPORT_FILE
    if not path and not os.path.exists(report_path):
        local_report_path = os.path.join("data", "metar_shadow_report.json")
        if os.path.exists(local_report_path):
            report_path = local_report_path
    try:
        if not os.path.exists(report_path):
            return {
                "available": False,
                "status": "BLOCKED_WAITING_REPORT",
                "message": "waiting last data/metar_shadow_report.json",
                "path": str(report_path),
            }
        with open(report_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)
    except Exception as exc:
        return {
            "available": False,
            "status": "BLOCKED_REPORT_PARSE_ERROR",
            "message": f"METAR report parse error: {exc}",
            "path": str(report_path),
        }

    waves = report.get("wave_summary") or []
    alerts = report.get("alerts") or []
    waiting_rows = [
        row
        for row in report.get("rows", [])
        if row.get("waiting_local_day_close")
        or row.get("coverage_status") == "waiting_local_day_close"
    ]
    real_gap_alerts = [
        alert
        for alert in alerts
        if alert.get("code") == "A_METAR_COVERAGE_GAP"
    ]
    parity_status = str(report.get("verdict") or "UNKNOWN")
    if real_gap_alerts:
        status = "WARNING_COVERAGE_GAP_REAL"
    elif waiting_rows:
        status = "WAITING_LOCAL_DAY_CLOSE"
    elif parity_status == "METAR_PARITY_INSUFFICIENT_DATA":
        status = "BLOCKED_WAITING_EXTERNAL_PARITY_INPUTS"
    else:
        status = "OK_COVERAGE_HEALTHY"

    return {
        "available": True,
        "status": status,
        "generated_at": report.get("generated_at"),
        "verdict": parity_status,
        "metrics": report.get("metrics") or {},
        "wave_summary": waves,
        "alerts": alerts,
        "waiting_rows": waiting_rows,
        "real_gap_alerts": real_gap_alerts,
        "path": str(report_path),
    }


def _format_metar_log_only_daily_lines(metar):
    lines = ["", "<b>METAR LOG_ONLY</b>"]
    if not metar or not metar.get("available"):
        lines.append(f"• Blocked: {metar.get('message', 'waiting METAR report') if metar else 'waiting METAR report'}")
        lines.append("• Trigger: run tools/metar_shadow_fetch.py manually, then tools/metar_parity_report.py.")
        return lines

    for wave in metar.get("wave_summary", []):
        lines.append(
            f"• {wave.get('wave')}: {wave.get('stations_seen')}/{wave.get('stations_configured')} stations, "
            f"coverage {_safe_float_text(wave.get('coverage_pct'), '%')}, "
            f"real gaps {int(wave.get('insufficient_coverage_rows') or 0)}, "
            f"waiting {int(wave.get('waiting_local_day_close_rows') or 0)}"
        )

    metrics = metar.get("metrics") or {}
    lines.append(
        f"• Parity: <code>{metar.get('verdict')}</code>; "
        f"coverage {_safe_float_text(metrics.get('coverage_pct'), '%')}; "
        f"METAR-WU n={metrics.get('n_compared_metar_wu', 0)}"
    )

    real_gap_alerts = metar.get("real_gap_alerts") or []
    waiting_rows = metar.get("waiting_rows") or []
    if real_gap_alerts:
        examples = ", ".join(
            f"{alert.get('city')}/{alert.get('icao')}" for alert in real_gap_alerts[:3]
        )
        lines.append(f"• Warning: coverage gap real ({examples})")
    elif waiting_rows:
        examples = ", ".join(
            f"{row.get('city')}/{row.get('icao')} {row.get('date_local')}" for row in waiting_rows[:3]
        )
        lines.append(f"• Waiting local day close: {examples}")
    elif metar.get("status") == "BLOCKED_WAITING_EXTERNAL_PARITY_INPUTS":
        lines.append("• Blocked: waiting external parity inputs (WU/Gamma/Open-Meteo CSV).")
    else:
        lines.append("• OK: METAR Wave 1+2 coverage healthy.")

    alert_codes = [str(alert.get("code")) for alert in metar.get("alerts", []) if alert.get("code")]
    if alert_codes:
        lines.append(f"• Alerts LOG_ONLY: {', '.join(alert_codes[:5])}")
    else:
        lines.append("• Alerts LOG_ONLY: none.")
    lines.append("• Runtime: reads latest JSON only; no fetch, no scheduler.")
    return lines


def build_daily_summary_payload(now=None):
    """Construye payload del resumen diario (datos crudos sin formateo)."""
    if now is None:
        now = datetime.now(timezone.utc)
    shadow_only_helper = globals().get("_is_shadow_only")
    shadow_only = shadow_only_helper() if callable(shadow_only_helper) else (len(ACTIVE_TRADING_CITIES) == 0)
    operable_counts_helper = globals().get("_get_live_operable_city_counts")
    operable_counts = (
        operable_counts_helper()
        if callable(operable_counts_helper)
        else {
            "active": len(globals().get("ACTIVE_TRADING_CITIES", []) or []),
            "canary": len(globals().get("CANARY_TRADING_CITIES", []) or []),
        }
    )
    next_run_at = ""
    try:
        next_run_at = get_next_run_time().isoformat()
    except Exception:
        next_run_at = ""
    return {
        "generated_at": now.isoformat(),
        "next_run_at": next_run_at,
        "cycles_24h": _daily_summary_cycles_last_24h(now),
        "resolutions_24h": _daily_summary_closed_trades_last_24h(now),
        "noaa_24h": _daily_summary_noaa_last_24h(now),
        "version": BOT_VERSION,
        "logic_series": LOGIC_SERIES,
        "active_cities_count": len(ACTIVE_TRADING_CITIES),
        "shadow_only": shadow_only,
        "operable_active_count": operable_counts["active"],
        "operable_canary_count": operable_counts["canary"],
        "metar_log_only": _load_metar_log_only_digest(),
    }


def format_daily_summary_text(payload):
    """Formatea payload del resumen diario como mensaje Telegram HTML."""
    c = payload.get("cycles_24h", {})
    r = payload.get("resolutions_24h", {})
    n = payload.get("noaa_24h", {})
    generated_at_raw = str(payload.get("generated_at", "") or "").strip()
    try:
        generated_at = datetime.fromisoformat(generated_at_raw)
    except Exception:
        generated_at = datetime.now(timezone.utc)

    mode_label_helper = globals().get("_format_operable_mode_label")
    mode_label = (
        mode_label_helper(
            active_count=int(payload.get("operable_active_count", 0) or 0),
            canary_count=int(payload.get("operable_canary_count", 0) or 0),
            shadow_only=bool(payload.get("shadow_only")),
        )
        if callable(mode_label_helper)
        else ("SHADOW-ONLY" if payload.get("shadow_only") else f"{payload.get('active_cities_count', 0)} ciudades activas")
    )
    buys_breakdown = []
    if int(c.get("buys_active", 0) or 0) > 0:
        buys_breakdown.append(f"{c.get('buys_active', 0)} active")
    if int(c.get("buys_canary", 0) or 0) > 0:
        buys_breakdown.append(f"{c.get('buys_canary', 0)} canary")
    if int(c.get("buys_other", 0) or 0) > 0:
        buys_breakdown.append(f"{c.get('buys_other', 0)} otras")
    buys_line = f"• BUYs reales: {c.get('buys_real', 0)}"
    if buys_breakdown:
        buys_line += f" ({' | '.join(buys_breakdown)})"

    lines = [
        f"📊 <b>Resumen diario — {generated_at.strftime('%Y-%m-%d')}</b>",
        f"<i>Bot {payload.get('version', '?')} · {mode_label}</i>",
        "",
        "<b>🔄 Ciclos 24h</b>",
        f"• Ejecutados: <b>{c.get('cycles', 0)}</b>",
        f"• Candidatos evaluados: {c.get('markets_evaluated', 0)}",
        f"• Con edge detectado: <b>{c.get('with_edge', 0)}</b>",
        f"• Seleccionados para BUY: {c.get('selected', 0)} | Shadow con edge: {c.get('shadow', 0)}",
        buys_line,
        "",
        "<b>💰 Resoluciones 24h</b>",
    ]

    if r.get("closed", 0) > 0:
        resolution_parts = [f"✅ {r.get('wins', 0)}"]
        if int(r.get("breakeven", 0) or 0) > 0:
            resolution_parts.append(f"➖ {r.get('breakeven', 0)}")
        resolution_parts.append(f"❌ {r.get('losses', 0)}")
        lines.append(
            f"• Cerrados: <b>{r['closed']}</b> "
            f"({' / '.join(resolution_parts)})"
        )
        lines.append(f"• PnL neto: <b>${r.get('pnl', 0.0):+.2f}</b>")
    else:
        lines.append("• Sin trades recientes cerrados hoy")
    if int(r.get("batch_closed", 0) or 0) > 0:
        lines.append(
            f"• Batch market_resolved: {r['batch_closed']} trades "
            f"(${r.get('batch_pnl', 0.0):+.2f}) — resoluciones de mercados antiguos"
        )

    lines.append("")
    lines.append("<b>🛰 NOAA 24h</b>")
    if n.get("new_total", 0) > 0:
        lines.append(f"• Nuevos casos: <b>{n['new_total']}</b>")
        for city, count in sorted(n.get("new_by_city", {}).items(), key=lambda x: -x[1]):
            lines.append(f"  · {city}: {count}")
    else:
        lines.append("• Sin casos nuevos en 24h")
    lines.append(f"• Acumulado histórico: {n.get('cumulative', 0)}")
    lines.append("")
    lines.append("<i>Caso NOAA = 1 fila city+date en observed_vs_forecast (forecast vs observado NOAA).</i>")
    lines.extend(_format_metar_log_only_daily_lines(payload.get("metar_log_only")))

    next_run_raw = str(payload.get("next_run_at", "") or "").strip()
    if next_run_raw:
        try:
            next_run = datetime.fromisoformat(next_run_raw)
            lines.append("")
            lines.append(f"<b>⏭ Próximo ciclo:</b> {next_run.strftime('%H:%M UTC')}")
        except Exception:
            pass

    return "\n".join(lines)


def maybe_send_daily_summary_telegram(state, now=None):
    """
    Envía el resumen diario por Telegram en el primer ciclo del día cuya hora UTC
    sea >= DAILY_SUMMARY_HOUR_UTC. Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    # Primer ciclo del día a partir de la hora configurada.
    if now.hour < DAILY_SUMMARY_HOUR_UTC:
        return False
    today = now.date().isoformat()
    if state.get("daily_summary_last_sent") == today:
        return False
    if not _daily_summary_has_cycle_today(now):
        return False

    try:
        payload = build_daily_summary_payload(now=now)
        text = format_daily_summary_text(payload)
        send_telegram(text)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"daily summary: fallo generando/enviando ({e})")
        return False

    state["daily_summary_last_sent"] = today
    return True


def _load_crosscheck_records(path):
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if isinstance(row, dict):
                    records.append(row)
    except Exception:
        pass
    return records


def _index_crosscheck_source_onboarding(payload):
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("candidates") or payload.get("records") or payload.get("cities") or []
    if isinstance(rows, dict):
        rows = rows.values()
    index = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        city = str(row.get("city") or "").strip()
        if city:
            index[city] = row
    return index


def _crosscheck_source_status(source_row):
    source_row = source_row if isinstance(source_row, dict) else {}
    values = [
        source_row.get("primary_status"),
        source_row.get("state"),
        source_row.get("mapping_status"),
        source_row.get("internal_mapping_status"),
        source_row.get("source_audit_status"),
        source_row.get("source_feasibility"),
    ]
    blocking_reasons = source_row.get("blocking_reasons")
    if isinstance(blocking_reasons, list):
        values.extend(blocking_reasons)
    normalized = {str(value or "").strip() for value in values if str(value or "").strip()}
    joined = " ".join(normalized).upper()
    source_blocked = "MAPPING_MISSING" in joined or "NO_ICAO" in joined
    if source_blocked:
        if "MAPPING_MISSING" in joined and "NO_ICAO" in joined:
            return "MAPPING_MISSING/no_icao", True
        if "MAPPING_MISSING" in joined:
            return "MAPPING_MISSING", True
        return "no_icao", True
    if "SOURCE_BLOCKED" in joined or "SOURCE_MISMATCH" in joined:
        return next((value for value in normalized if value in {"SOURCE_BLOCKED", "SOURCE_MISMATCH"}), "SOURCE_BLOCKED"), True
    if not normalized:
        return "unknown", False
    mapping = str(
        source_row.get("mapping_status")
        or source_row.get("internal_mapping_status")
        or source_row.get("primary_status")
        or "unknown"
    )
    return mapping, False


def _crosscheck_record_has_operable_gap(record, city):
    if not isinstance(record, dict):
        return False
    details = record.get("trader_only_severity_details")
    if isinstance(details, dict):
        detail = details.get(city)
        if isinstance(detail, dict):
            return int(detail.get("operable_signal_count", 0) or 0) >= 2
    if city in (record.get("operational_trader_only_cities") or []):
        return True
    return False


def _crosscheck_distinct_gap_days(city, previous_records, now):
    days = set()
    now_date = now.date() if hasattr(now, "date") else datetime.now(timezone.utc).date()
    for record in previous_records or []:
        if not _crosscheck_record_has_operable_gap(record, city):
            continue
        day_text = str(record.get("run_at") or "")[:10]
        if not day_text:
            continue
        try:
            day = datetime.fromisoformat(day_text).date()
        except Exception:
            continue
        if (now_date - day).days <= 14:
            days.add(day.isoformat())
    days.add(now_date.isoformat())
    return len(days)


def _classify_trader_gap_city_severity(
    city,
    city_stat,
    source_row,
    shadow_row,
    previous_records,
    now=None,
    city_mode="shadow",
    is_blocked=False,
    observed_audit_cities=None,
):
    now = now or datetime.now(timezone.utc)
    city_stat = city_stat if isinstance(city_stat, dict) else {}
    shadow_row = shadow_row if isinstance(shadow_row, dict) else {}
    observed_audit_cities = observed_audit_cities or set()

    operable_signal_count = int(city_stat.get("allowed", 0) or 0)
    consensus_signal_count = int(city_stat.get("consensus", 0) or 0)
    consensus_trader_count = len(city_stat.get("consensus_operable_traders", set()) or set())
    distinct_gap_days = _crosscheck_distinct_gap_days(city, previous_records, now)
    markets_seen = int(shadow_row.get("markets_seen", 0) or 0)
    edge_hits = int(shadow_row.get("edge_hits", 0) or 0)
    source_status, source_blocked = _crosscheck_source_status(source_row)

    gate_reasons = []
    if distinct_gap_days >= 3:
        gate_reasons.append("distinct_gap_days>=3")
    if operable_signal_count >= 5 and consensus_trader_count >= 2:
        gate_reasons.append("operable_n>=5_consensus_traders>=2")
    if markets_seen >= 15 and edge_hits >= 1:
        gate_reasons.append("shadow_markets_seen>=15_edge_hits>=1")
    gate_passed = bool(gate_reasons)

    if operable_signal_count < 2 or consensus_signal_count <= 0 or is_blocked:
        severity = "INFO"
        reason = "not_operational_gap"
    elif source_blocked:
        severity = "WATCH_SOURCE"
        reason = "source_blocked"
    elif not gate_passed and distinct_gap_days <= 1:
        severity = "INFO"
        reason = "single_day_or_insufficient_magnitude"
    elif not gate_passed:
        severity = "WATCH_SOURCE"
        reason = "magnitude_gates_not_met"
    else:
        action_allowed = city_mode in {"active", "canary"} or (
            city in observed_audit_cities and int(shadow_row.get("cycles_seen", 0) or 0) >= 1
        )
        if action_allowed:
            severity = "ACTION"
            reason = "magnitude_gates_met_source_ready_action_context"
        else:
            severity = "WATCH"
            reason = "magnitude_gates_met_source_ready_observe"

    if source_blocked and severity == "ACTION":
        severity = "WATCH_SOURCE"
        reason = "source_blocked_hard_no_action"

    return {
        "city": city,
        "severity": severity,
        "reason": reason,
        "source_status": source_status,
        "operable_signal_count": operable_signal_count,
        "consensus_signal_count": consensus_signal_count,
        "consensus_trader_count": consensus_trader_count,
        "distinct_gap_days": distinct_gap_days,
        "markets_seen": markets_seen,
        "edge_hits": edge_hits,
        "gate_passed": gate_passed,
        "gate_status": "gate_passed" if gate_passed else "gate_failed",
        "gate_reasons": gate_reasons,
        "city_mode": city_mode,
    }


def _crosscheck_overall_severity(details_by_city):
    # Legacy verify anchors: action_level = "ACTION" / action_level = "WATCH" / action_level = "INFO".
    order = {"INFO": 0, "WATCH_SOURCE": 1, "WATCH": 2, "ACTION": 3}
    best = "INFO"
    for detail in (details_by_city or {}).values():
        severity = str((detail or {}).get("severity") or "INFO")
        if order.get(severity, 0) > order.get(best, 0):
            best = severity
    return best


def _crosscheck_action_task(action_level, operational_trader_only, details_by_city):
    details_by_city = details_by_city or {}
    focus_city = operational_trader_only[0] if operational_trader_only else None
    if action_level == "ACTION" and focus_city:
        return (
            f"Accion: auditar {focus_city} primero (fuente lista, gates cumplidos). "
            "Cerrar con decision operativa Opus; no mutar trading automaticamente."
        )
    if action_level == "WATCH":
        return "Accion diferida: observar serie extendida antes de abrir decision operativa."
    if action_level == "WATCH_SOURCE":
        blocked = [
            city for city, detail in details_by_city.items()
            if "MAPPING_MISSING" in str(detail.get("source_status", "")) or "no_icao" in str(detail.get("source_status", ""))
        ]
        if blocked:
            return (
                f"Fuente/mapping pendiente en {blocked[0]}: mantener WATCH_SOURCE. "
                "No source unlock, no whitelist/canary y no cambio de city modes."
            )
        return "Gap operable real, pero gates de magnitud no cumplidos: notificacion baja prioridad."
    return "Sin tarea nueva: seguir acumulando serie."


def maybe_run_daily_crosscheck(state, now=None):
    """
    v10.6.12: corre el cross-check señales traders vs edge bot una vez por día
    (primer ciclo de cada día). Appenda a SIGNALS_CROSSCHECK_FILE y manda Telegram
    con un resumen breve. Cuando acumula SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD corridas
    envía un aviso one-shot indicando que hay suficiente serie temporal para analizar.
    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if state.get("crosscheck_last_date") == today:
        return False

    try:
        if not os.path.exists(SIGNALS_FILE) or not os.path.exists(SHADOW_TRACKING_FILE):
            return False

        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            sig_data = json.load(f)
        with open(SHADOW_TRACKING_FILE, "r", encoding="utf-8") as f:
            shadow_data = json.load(f)
        try:
            with open(SOURCE_ONBOARDING_FILE, "r", encoding="utf-8") as f:
                source_onboarding_data = json.load(f)
        except Exception:
            source_onboarding_data = {}

        signals = sig_data.get("signals", []) if isinstance(sig_data, dict) else []
        shadow_cities = shadow_data.get("cities", {}) if isinstance(shadow_data, dict) else {}
        source_onboarding = _index_crosscheck_source_onboarding(source_onboarding_data)
        signals_generated_at = sig_data.get("generated", "") if isinstance(sig_data, dict) else ""
        shadow_updated_at = shadow_data.get("updated_at", "") if isinstance(shadow_data, dict) else ""

        # Aggregate signal stats per city
        city_stats = {}
        allowed_conds = {"at_or_above", "at_or_below"}
        for s in signals:
            if not isinstance(s, dict):
                continue
            city = s.get("city", "")
            if not city:
                continue
            if city not in city_stats:
                city_stats[city] = {
                    "n": 0,
                    "consensus": 0,
                    "allowed": 0,
                    "max_wr": 0.0,
                    "operable_traders": set(),
                    "consensus_operable_traders": set(),
                    "dates": set(),
                }
            st = city_stats[city]
            st["n"] += 1
            if s.get("has_consensus"):
                st["consensus"] += 1
            if s.get("condition") in allowed_conds:
                st["allowed"] += 1
                trader = str(s.get("trader") or "").strip()
                if trader:
                    st["operable_traders"].add(trader)
                    if s.get("has_consensus"):
                        st["consensus_operable_traders"].add(trader)
                date_value = str(s.get("date") or "").strip()
                if date_value:
                    st["dates"].add(date_value[:10])
            wr = float(s.get("trader_win_rate") or 0)
            if wr > st["max_wr"]:
                st["max_wr"] = wr

        # Compute buckets
        signal_city_set = set(city_stats.keys())
        bot_edge_set = {
            c for c, d in shadow_cities.items()
            if isinstance(d, dict) and int(d.get("edge_hits", 0) or 0) >= 1
        }
        match_cities = sorted(signal_city_set & bot_edge_set)
        bot_only_cities = sorted(bot_edge_set - signal_city_set)
        trader_only_cities = sorted(signal_city_set - bot_edge_set)
        actionable_trader_only = [c for c in trader_only_cities if city_stats[c]["allowed"] > 0]
        operational_trader_only = [
            c for c in actionable_trader_only
            if city_stats[c]["consensus"] > 0 and not is_city_blocked(c)
        ]
        previous_records = _load_crosscheck_records(SIGNALS_CROSSCHECK_FILE)
        severity_details = {}
        for c in trader_only_cities:
            severity_details[c] = _classify_trader_gap_city_severity(
                c,
                city_stats.get(c, {}),
                source_onboarding.get(c, {}),
                shadow_cities.get(c, {}) if isinstance(shadow_cities, dict) else {},
                previous_records,
                now=now,
                city_mode=get_effective_city_mode(c),
                is_blocked=is_city_blocked(c),
                observed_audit_cities=OBSERVED_AUDIT_CITIES,
            )
        operational_severity_details = {
            c: severity_details[c]
            for c in operational_trader_only
            if c in severity_details
        }
        action_level = _crosscheck_overall_severity(operational_severity_details)
        severity_action_level = action_level

        # Append record to JSONL
        record = {
            "run_at": now.isoformat(),
            "signals_generated_at": signals_generated_at,
            "shadow_updated_at": shadow_updated_at,
            "match_cities": match_cities,
            "bot_only_cities": bot_only_cities,
            "trader_only_cities": trader_only_cities,
            "match_count": len(match_cities),
            "bot_only_count": len(bot_only_cities),
            "trader_only_count": len(trader_only_cities),
            "consensus_match_count": sum(
                1 for c in match_cities if city_stats.get(c, {}).get("consensus", 0) > 0
            ),
            "consensus_trader_only_count": sum(
                1 for c in trader_only_cities if city_stats.get(c, {}).get("consensus", 0) > 0
            ),
            "actionable_trader_only_count": len(actionable_trader_only),
            "operational_trader_only_count": len(operational_trader_only),
            "operational_trader_only_cities": operational_trader_only,
            "trader_only_severity_details": severity_details,
        }
        crosscheck_dir = os.path.dirname(SIGNALS_CROSSCHECK_FILE)
        if crosscheck_dir:
            os.makedirs(crosscheck_dir, exist_ok=True)
        with open(SIGNALS_CROSSCHECK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        # Count records in JSONL
        try:
            with open(SIGNALS_CROSSCHECK_FILE, "r", encoding="utf-8") as f:
                n_records = sum(1 for line in f if line.strip())
        except Exception:
            n_records = 1

        # Daily Telegram message
        action_lines = ""
        if operational_trader_only:
            top_city = operational_trader_only[0]
            action_level = severity_action_level
            action_task = (
                f"Accion: auditar {top_city} primero (whitelist, RESOLUTION_ICAO/estacion, "
                f"OBSERVED_AUDIT_CITIES/cobertura NOAA y ultimas seÃ±ales trader). "
                f"Cerrar con: sin cambio / preparar whitelist-canary / bloqueo por fuente."
            )
        elif len(trader_only_cities) >= 10:
            action_level = "WATCH"
            action_task = (
                "Accion diferida: si estas ciudades se repiten varios dias, revisar whitelist "
                "y cobertura observada antes de tocar reglas core."
            )
        else:
            action_level = "INFO"
            action_task = "Sin tarea nueva: seguir acumulando serie."
        action_level = severity_action_level
        action_task = _crosscheck_action_task(
            action_level,
            operational_trader_only,
            operational_severity_details,
        )
        if action_level == "INFO" and not operational_trader_only and len(trader_only_cities) >= 10:
            action_level = "WATCH"
            action_task = (
                "Accion diferida: si estas ciudades se repiten varios dias, revisar whitelist "
                "y cobertura observada antes de tocar reglas core."
            )
        for c in operational_trader_only[:4]:
            st = city_stats[c]
            cons_tag = " (consenso)" if st["consensus"] > 0 else ""
            action_lines += f"\n  • {c}: {st['allowed']} señal(es){cons_tag}"

        if operational_trader_only:
            detailed_action_lines = ""
            for c in operational_trader_only[:4]:
                st = city_stats[c]
                cons_tag = " (consenso)" if st["consensus"] > 0 else ""
                detail = operational_severity_details.get(c, {})
                detailed_action_lines += (
                    f"\n  - {c}: {st['allowed']} senal(es){cons_tag}"
                    f" | severity={detail.get('severity', 'INFO')}"
                    f" source={detail.get('source_status', 'unknown')}"
                    f" operable={detail.get('operable_signal_count')}"
                    f" days={detail.get('distinct_gap_days')}"
                    f" markets={detail.get('markets_seen')}"
                    f" edge_hits={detail.get('edge_hits')}"
                    f" gate={detail.get('gate_status', 'gate_failed')}"
                )
            action_lines = detailed_action_lines

        daily_msg = (
            f"📊 <b>Cross-check diario traders vs bot</b>\n"
            f"MATCH {len(match_cities)} | BOT_ONLY {len(bot_only_cities)} | TRADER_ONLY {len(trader_only_cities)}\n"
        )
        if operational_trader_only:
            daily_msg += (
                f"Gap operativo real (conds operables, consenso, fuera de blocked) "
                f"<i>(muestra top {min(len(operational_trader_only), 4)} de {len(operational_trader_only)})</i>:"
                f"{action_lines}\n"
            )
        else:
            daily_msg += "Sin gap operativo real hoy <i>(TRADER_ONLY blocked o sin consenso no alertan)</i>\n"
        daily_msg += (
            f"Nivel: <b>{action_level}</b>\n"
            f"{action_task}\n"
            f"<i>Corrida {n_records}/{SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD}</i>"
        )
        send_telegram(daily_msg)

        # One-shot "ready for analysis" notification at threshold
        if (
            n_records >= SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD
            and not state.get("crosscheck_analysis_notified")
        ):
            send_telegram(
                f"🔬 <b>Cross-check listo para análisis</b>\n"
                f"{n_records} corridas acumuladas — serie temporal suficiente.\n\n"
                f"Preguntas que ya puedes responder:\n"
                f"• ¿Las mismas ciudades TRADER_ONLY aparecen cada día?\n"
                f"• ¿Austin/Toronto siguen siendo actionable de forma consistente?\n"
                f"• ¿El ratio MATCH/TRADER_ONLY cambia con el tiempo?\n\n"
                f"Iniciar sesión Sonnet: <i>\"Analizar signals_crosscheck.jsonl, "
                f"{n_records} corridas\"</i>"
            )
            state["crosscheck_analysis_notified"] = True

    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"crosscheck diario: fallo ({e})")
        return False

    state["crosscheck_last_date"] = today
    return True


def maybe_run_daily_crosscheck_temporal_summary(now=None):
    """
    Ejecuta el resumen temporal del cross-check usando el mismo JSONL live del bot.
    No toca trading ni policy; solo dispara la capa humana diaria sobre la serie acumulada.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if not os.path.exists(SIGNALS_CROSSCHECK_FILE):
        return False
    if not os.path.exists(SIGNALS_CROSSCHECK_DAILY_SUMMARY_SCRIPT):
        return False

    try:
        result = subprocess.run(
            [
                sys.executable,
                SIGNALS_CROSSCHECK_DAILY_SUMMARY_SCRIPT,
                "--crosscheck-file",
                SIGNALS_CROSSCHECK_FILE,
                "--signals",
                SIGNALS_FILE,
                "--shadow",
                SHADOW_TRACKING_FILE,
                "--policy",
                CITY_POLICY_FILE,
                "--source-onboarding",
                SOURCE_ONBOARDING_FILE,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        logger = globals().get("log")
        if result.returncode != 0:
            if logger:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "sin detalle"
                logger.warning(f"crosscheck temporal summary: fallo ({detail[:500]})")
            return False
        if logger:
            logger.info("crosscheck temporal summary: OK")
        return True
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"crosscheck temporal summary: fallo ({e})")
        return False


def maybe_run_traders_intelligence_summary(state, now=None):
    """
    Regenera traders_intelligence v0 y dispara el resumen diario con checks de
    readiness para abrir v1 cuando toque.
    No toca trading ni policy; solo produce artefactos read-only y Telegram.
    """
    logger = globals().get("log")
    if not TRADERS_INTELLIGENCE_ENABLED:
        if logger:
            logger.info("traders intelligence summary: skip (TRADERS_INTELLIGENCE_ENABLED=0)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    target_hour = TRADERS_INTELLIGENCE_HOUR_UTC % 24
    hour_delta = min((now.hour - target_hour) % 24, (target_hour - now.hour) % 24)
    if hour_delta > 1:
        if logger:
            logger.info(
                "traders intelligence summary: skip "
                f"(outside hour window: now_hour={now.hour} target_hour={target_hour} delta={hour_delta})"
            )
        return False

    today = now.date().isoformat()
    if state.get("traders_intelligence_last_date") == today:
        if logger:
            logger.info(f"traders intelligence summary: skip (already ran today: {today})")
        return False

    required_scripts = [
        TRADERS_INTELLIGENCE_REPORT_SCRIPT,
        TRADERS_INTELLIGENCE_DAILY_SUMMARY_SCRIPT,
    ]
    missing_scripts = [path for path in required_scripts if not os.path.exists(path)]
    if missing_scripts:
        if logger:
            logger.warning(f"traders intelligence summary: scripts faltantes {missing_scripts}")
        return False

    repo_root = os.path.dirname(os.path.abspath(__file__))
    commands = [
        [sys.executable, TRADERS_INTELLIGENCE_REPORT_SCRIPT],
        [sys.executable, TRADERS_INTELLIGENCE_DAILY_SUMMARY_SCRIPT],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
            )
        except Exception as exc:
            if logger:
                logger.warning(
                    f"traders intelligence summary: fallo ejecutando {os.path.basename(command[1])}: {exc}"
                )
            return False
        if result.returncode != 0:
            if logger:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "sin detalle"
                logger.warning(
                    f"traders intelligence summary: {os.path.basename(command[1])} fallo ({detail[:500]})"
                )
            return False

    state["traders_intelligence_last_date"] = today
    if logger:
        logger.info("traders intelligence summary: OK")
    return True


def maybe_run_traders_intelligence_collector(now=None):
    """
    Ejecuta el collector V1.1 LOG_ONLY detras de TRADERS_INTELLIGENCE_COLLECTOR.
    Default OFF; el propio collector aplica cooldown, idempotencia y kill switch.
    """
    logger = globals().get("log")
    if not TRADERS_INTELLIGENCE_COLLECTOR_ENABLED:
        if logger:
            logger.info("traders intelligence collector: skip (TRADERS_INTELLIGENCE_COLLECTOR=OFF)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if not os.path.exists(TRADERS_INTELLIGENCE_COLLECTOR_SCRIPT):
        if logger:
            logger.warning(f"traders intelligence collector: skip (missing script: {TRADERS_INTELLIGENCE_COLLECTOR_SCRIPT})")
        return False

    try:
        result = subprocess.run(
            [
                sys.executable,
                TRADERS_INTELLIGENCE_COLLECTOR_SCRIPT,
                "--json",
                "--signals",
                SIGNALS_FILE,
                "--agent-events",
                AGENT_EVENTS_FILE,
                "--now",
                now.replace(microsecond=0).isoformat(),
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"traders intelligence collector: fallo ejecutando script ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"traders intelligence collector: fallo ({detail[:500]})")
        return False

    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        payload = {}
    status = payload.get("status")
    reason = payload.get("reason") or "none"
    run_id = payload.get("run_id") or "none"
    if logger:
        logger.info(f"traders intelligence collector: status={status} reason={reason} run_id={run_id}")
    return status == "completed"


def maybe_run_traders_operational_intelligence_monitor(now=None):
    """
    Ejecuta Traders Operational Intelligence LOG_ONLY con estado propio.
    El monitor archiva snapshots completos, regenera el reporte de seis preguntas
    y devuelve un Telegram corto solo cuando hay transición, error/stale o digest diario.
    """
    logger = globals().get("log")
    if not TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED:
        if logger:
            logger.info("traders operational intelligence: skip (TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED=false)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if not os.path.exists(TRADERS_OPERATIONAL_INTELLIGENCE_MONITOR_SCRIPT):
        if logger:
            logger.warning(
                "traders operational intelligence: skip "
                f"(missing script: {TRADERS_OPERATIONAL_INTELLIGENCE_MONITOR_SCRIPT})"
            )
        return False

    intelligence_dir = _data_path("intelligence")
    try:
        result = subprocess.run(
            [
                sys.executable,
                TRADERS_OPERATIONAL_INTELLIGENCE_MONITOR_SCRIPT,
                "--json",
                "--signals",
                SIGNALS_FILE,
                "--snapshots",
                os.path.join(intelligence_dir, "trader_signals_snapshots.jsonl"),
                "--report-json",
                os.path.join(intelligence_dir, "traders_operational_questions_report.json"),
                "--state",
                os.path.join(intelligence_dir, "traders_operational_monitor_state.json"),
                "--agent-events",
                AGENT_EVENTS_FILE,
                "--blocked-resolutions",
                BLOCKED_SIGNALS_FILE,
                "--blocked-fallback",
                _data_path("runtime_import_derived/blocked_signals_resolutions.jsonl"),
                "--trade-lifecycle",
                TRADE_LIFECYCLE_FILE,
                "--now",
                now.replace(microsecond=0).isoformat(),
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=TRADERS_OPERATIONAL_INTELLIGENCE_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"traders operational intelligence: fallo ejecutando monitor ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"traders operational intelligence: fallo ({detail[:500]})")
        return False

    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        payload = {}

    if payload.get("should_notify") and payload.get("telegram_message"):
        send_telegram(payload["telegram_message"])

    if logger:
        reasons = ",".join(payload.get("notification_reasons") or []) or "none"
        logger.info(
            "traders operational intelligence: "
            f"status={payload.get('status')} notify={payload.get('should_notify')} reasons={reasons}"
        )
    return payload.get("status") == "completed"


def maybe_run_source_onboarding_andon(now=None):
    """
    Ejecuta Source Onboarding Andon LOG_ONLY sobre source_onboarding.json.
    El Andon mantiene estado idempotente y devuelve Telegram solo cuando una
    ciudad candidata requiere accion humana clara. No toca trading ni policy.
    """
    logger = globals().get("log")
    if not SOURCE_ONBOARDING_ANDON_ENABLED:
        if logger:
            logger.info("source onboarding andon: skip (SOURCE_ONBOARDING_ANDON_ENABLED=false)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if not os.path.exists(SOURCE_ONBOARDING_ANDON_SCRIPT):
        if logger:
            logger.warning(
                "source onboarding andon: skip "
                f"(missing script: {SOURCE_ONBOARDING_ANDON_SCRIPT})"
            )
        return False

    output_dir = _data_path("source_onboarding")
    try:
        result = subprocess.run(
            [
                sys.executable,
                SOURCE_ONBOARDING_ANDON_SCRIPT,
                "--json",
                "--source-json",
                _SOURCE_ONBOARDING_JSON_FILE,
                "--state",
                os.path.join(output_dir, "andon_state.json"),
                "--output",
                os.path.join(output_dir, "andon_latest.json"),
                "--agent-events",
                AGENT_EVENTS_FILE,
                "--now",
                now.replace(microsecond=0).isoformat(),
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=SOURCE_ONBOARDING_ANDON_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"source onboarding andon: fallo ejecutando monitor ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"source onboarding andon: fallo ({detail[:500]})")
        return False

    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        payload = {}

    if payload.get("should_notify") and payload.get("telegram_message"):
        send_telegram(payload["telegram_message"])

    if logger:
        reasons = ",".join(payload.get("notification_reasons") or []) or "none"
        logger.info(
            "source onboarding andon: "
            f"status={payload.get('status')} notify={payload.get('should_notify')} reasons={reasons}"
        )
    return payload.get("status") == "completed"


def maybe_run_city_intelligence_runtime_summary(state, now=None):
    """
    Puente read-only desde el bot principal: exporta su runtime local a
    data/runtime_import y genera el daily summary con inputs reales.
    No escribe policy ni toca trading; solo produce artefactos derivados.
    """
    if not CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if state.get("city_intelligence_runtime_summary_last_date") == today:
        return False
    if now.hour < CITY_INTELLIGENCE_RUNTIME_BRIDGE_HOUR_UTC:
        return False

    required_scripts = [
        CITY_INTELLIGENCE_RUNTIME_EXPORT_SCRIPT,
        CITY_INTELLIGENCE_EFFECTIVE_VIEW_SCRIPT,
        CITY_INTELLIGENCE_PIPELINE_SCRIPT,
        CITY_INTELLIGENCE_ALIGNMENT_SCRIPT,
        CITY_INTELLIGENCE_DAILY_SUMMARY_SCRIPT,
    ]
    missing_scripts = [path for path in required_scripts if not os.path.exists(path)]
    logger = globals().get("log")
    if missing_scripts:
        if logger:
            logger.warning(f"city-intelligence runtime bridge: scripts faltantes {missing_scripts}")
        return False

    repo_root = os.path.dirname(os.path.abspath(__file__))
    pipeline_command = [sys.executable, CITY_INTELLIGENCE_PIPELINE_SCRIPT, "--telegram-dry-run"]
    if not os.path.exists(os.path.join(repo_root, "data", "directional_trader_census.json")):
        pipeline_command.append("--refresh-census")
    if not os.path.exists(os.path.join(repo_root, "data", "settlement_fidelity_probe.json")):
        pipeline_command.append("--refresh-probe")

    commands = [
        [sys.executable, CITY_INTELLIGENCE_RUNTIME_EXPORT_SCRIPT],
        [sys.executable, CITY_INTELLIGENCE_EFFECTIVE_VIEW_SCRIPT],
        pipeline_command,
        [sys.executable, CITY_INTELLIGENCE_ALIGNMENT_SCRIPT, "--decision-mode", "operational"],
        [sys.executable, CITY_INTELLIGENCE_DAILY_SUMMARY_SCRIPT],
    ]

    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=360,
                check=False,
            )
        except Exception as exc:
            if logger:
                logger.warning(f"city-intelligence runtime bridge: fallo ejecutando {os.path.basename(command[1])}: {exc}")
            return False
        if result.returncode != 0:
            if logger:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "sin detalle"
                logger.warning(
                    f"city-intelligence runtime bridge: {os.path.basename(command[1])} fallo ({detail[:500]})"
                )
            return False

    state["city_intelligence_runtime_summary_last_date"] = today
    if logger:
        logger.info("city-intelligence runtime bridge: OK")
    return True


def maybe_run_sl_retrospective(state):
    """Analiza SLs pasados y reporta si el bot era correcto al ser stoppeado."""
    logger = globals().get("log")
    if not SL_RETRO_ENABLED:
        if logger:
            logger.info("sl retrospective: skip (SL_RETRO_ENABLED=0)")
        return False
    if not os.path.exists(TRADE_LIFECYCLE_FILE):
        if logger:
            logger.info(f"sl retrospective: skip (missing lifecycle file: {TRADE_LIFECYCLE_FILE})")
        return False
    if not os.path.exists(SL_RETROSPECTIVE_SCRIPT):
        if logger:
            logger.info(f"sl retrospective: skip (missing script: {SL_RETROSPECTIVE_SCRIPT})")
        return False

    now = datetime.now(timezone.utc)

    lifecycle_data = load_trade_lifecycle_data()
    records = lifecycle_data.get("records", []) if isinstance(lifecycle_data, dict) else []
    stop_loss_closes = []
    for record in records:
        if not isinstance(record, dict):
            continue
        close_context = record.get("close_context") or {}
        if close_context.get("close_reason") != "stop_loss":
            continue
        closed_at = record.get("closed_at")
        if closed_at:
            stop_loss_closes.append(closed_at)

    retrospective_state = {}
    if os.path.exists(SL_RETROSPECTIVE_STATE_FILE):
        try:
            with open(SL_RETROSPECTIVE_STATE_FILE, "r", encoding="utf-8-sig") as fh:
                retrospective_state = json.load(fh)
        except Exception as exc:
            if logger:
                logger.warning(f"sl retrospective: no pude leer state ({exc})")
            retrospective_state = {}

    last_run_raw = retrospective_state.get("last_run_at", "")
    try:
        last_run_at = datetime.fromisoformat(last_run_raw) if last_run_raw else None
    except Exception:
        last_run_at = None
    if last_run_at and last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=timezone.utc)
    elif last_run_at:
        last_run_at = last_run_at.astimezone(timezone.utc)

    has_new_stop_loss = False
    for closed_at_raw in stop_loss_closes:
        try:
            closed_at = datetime.fromisoformat(str(closed_at_raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if closed_at.tzinfo is None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)
        else:
            closed_at = closed_at.astimezone(timezone.utc)
        if last_run_at is None or closed_at > last_run_at:
            has_new_stop_loss = True
            break

    periodic_recheck_due = last_run_at is None or (now - last_run_at) >= timedelta(hours=24)
    if not has_new_stop_loss and not periodic_recheck_due:
        if logger:
            logger.info(
                "sl retrospective: skip "
                f"(no new stop_loss since last_run_at={last_run_raw or 'never'}; "
                f"periodic_recheck_due={periodic_recheck_due}; "
                f"tracked_stop_losses={len(stop_loss_closes)})"
            )
        return False

    command = [
        sys.executable,
        SL_RETROSPECTIVE_SCRIPT,
        "--lifecycle-file",
        TRADE_LIFECYCLE_FILE,
        "--state-file",
        SL_RETROSPECTIVE_STATE_FILE,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"sl retrospective: fallo ejecutando script ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"sl retrospective: fallo ({detail[:500]})")
        return False

    if logger:
        logger.info("sl retrospective: OK")
    return True


def close_expired_legacy_positions():
    """Cierra posiciones abiertas cuya fecha de resolución venció hace >2 días sin snapshots ni observaciones."""
    from datetime import date as _date
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=2)
    now_str = datetime.now(timezone.utc).isoformat()
    logger = globals().get("log")

    tl_data = load_trade_lifecycle_data()
    tl_closed = 0
    for r in tl_data.get("records", []):
        if r.get("status") != "open":
            continue
        raw_date = str(r.get("date") or "").strip()[:10]
        if not raw_date:
            continue
        try:
            res_date = _date.fromisoformat(raw_date)
        except ValueError:
            continue
        if res_date >= cutoff:
            continue
        if r.get("position_snapshots") or r.get("market_observations"):
            continue
        r["status"] = "closed"
        r["closed_at"] = now_str
        r.setdefault("close_context", {}).update({
            "close_action": "EXPIRED_UNVERIFIED",
            "close_reason": "expired_no_evidence",
            "close_subtype": "expired_no_evidence",
            "close_price": None,
            "close_shares": None,
            "return_est": None,
            "pnl_cash": None,
            "pnl_pct": None,
            "order_id": "",
            "timestamp": now_str,
            "bot_version": BOT_VERSION,
            "reconciliation_needed": True,
        })
        if logger:
            logger.info(
                f"legacy_cleanup: closed {r.get('city')} {raw_date} {r.get('side')} "
                f"EXPIRED_UNVERIFIED (expired {(today - res_date).days}d ago, no evidence — needs manual reconciliation)"
            )
        tl_closed += 1
    if tl_closed:
        save_trade_lifecycle_data(tl_data)

    pm_records = load_postmortem_data()
    pm_closed = 0
    for r in pm_records:
        if r.get("status") != "open":
            continue
        raw_date = str(r.get("date") or "").strip()[:10]
        if not raw_date:
            continue
        try:
            res_date = _date.fromisoformat(raw_date)
        except ValueError:
            continue
        if res_date >= cutoff:
            continue
        r["status"] = "closed"
        r["closed_at"] = now_str
        r["close_action"] = "EXPIRED_UNVERIFIED"
        r["close_reason"] = "expired_no_evidence"
        r["close_subtype"] = "expired_no_evidence"
        r["close_price"] = None
        r["close_shares"] = 0.0
        r["return_est"] = None
        r["pnl_cash"] = None
        r["pnl_pct"] = None
        r["order_id"] = None
        r["bot_version_closed"] = BOT_VERSION
        r["legacy_close"] = True
        r["reconciliation_needed"] = True
        pm_closed += 1
    if pm_closed:
        save_postmortem_data(pm_records)

    if tl_closed or pm_closed:
        event = {
            "session": "auto",
            "timestamp": now_str,
            "action": "legacy_cleanup_auto_close",
            "description": (
                f"Auto-close de posiciones expiradas sin evidencia: "
                f"trade_lifecycle={tl_closed}, postmortem={pm_closed}."
            ),
            "tl_closed": tl_closed,
            "pm_closed": pm_closed,
            "bot_version": BOT_VERSION,
        }
        try:
            with open(AGENT_EVENTS_FILE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
        except Exception as exc:
            if logger:
                logger.warning(f"legacy_cleanup: no pude escribir agent_events ({exc})")

    return tl_closed + pm_closed


def maybe_close_expired_legacy_positions(state, now=None):
    """Wrapper diario para close_expired_legacy_positions — una vez por día."""
    logger = globals().get("log")
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if state.get("legacy_cleanup_last_run") == today:
        return False
    closed = close_expired_legacy_positions()
    state["legacy_cleanup_last_run"] = today
    if logger:
        logger.info(f"legacy_cleanup: done (closed={closed})")
    return True


def maybe_run_pnl_reconciliation(state):
    """Alerta diaria: reconcilia P/L wallet Polymarket vs lectura del bot."""
    logger = globals().get("log")
    if not PNL_RECONCILIATION_ENABLED:
        if logger:
            logger.info("pnl reconciliation: skip (PNL_RECONCILIATION_ENABLED=0)")
        return False
    if not os.path.exists(TRADE_LIFECYCLE_FILE):
        if logger:
            logger.info(f"pnl reconciliation: skip (missing lifecycle file: {TRADE_LIFECYCLE_FILE})")
        return False
    if not os.path.exists(PNL_RECONCILIATION_SCRIPT):
        if logger:
            logger.info(f"pnl reconciliation: skip (missing script: {PNL_RECONCILIATION_SCRIPT})")
        return False

    now = datetime.now(timezone.utc)
    target_hour = PNL_RECONCILIATION_HOUR_UTC % 24
    hour_delta = min((now.hour - target_hour) % 24, (target_hour - now.hour) % 24)
    if hour_delta > 1:
        if logger:
            logger.info(
                "pnl reconciliation: skip "
                f"(outside hour window: now_hour={now.hour} target_hour={target_hour} delta={hour_delta})"
            )
        return False

    reconciliation_state = {}
    if os.path.exists(PNL_RECONCILIATION_STATE_FILE):
        try:
            with open(PNL_RECONCILIATION_STATE_FILE, "r", encoding="utf-8-sig") as fh:
                reconciliation_state = json.load(fh)
        except Exception as exc:
            if logger:
                logger.warning(f"pnl reconciliation: no pude leer state ({exc})")
            reconciliation_state = {}

    today = now.date().isoformat()
    if reconciliation_state.get("last_sent_date") == today:
        if logger:
            logger.info(f"pnl reconciliation: skip (already sent today: {today})")
        return False

    command = [
        sys.executable,
        PNL_RECONCILIATION_SCRIPT,
        "--lifecycle-file",
        TRADE_LIFECYCLE_FILE,
        "--state-file",
        PNL_RECONCILIATION_STATE_FILE,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"pnl reconciliation: fallo ejecutando script ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"pnl reconciliation: fallo ({detail[:500]})")
        return False

    if logger:
        logger.info("pnl reconciliation: OK")
    return True


def maybe_run_daily_briefing(state):
    """Briefing diario de posiciones abiertas y estado del sistema."""
    logger = globals().get("log")
    if not DAILY_BRIEFING_ENABLED:
        if logger:
            logger.info("daily briefing: skip (DAILY_BRIEFING_ENABLED=0)")
        return False
    if not os.path.exists(TRADE_LIFECYCLE_FILE):
        if logger:
            logger.info(f"daily briefing: skip (missing lifecycle file: {TRADE_LIFECYCLE_FILE})")
        return False
    if not os.path.exists(DAILY_POSITION_BRIEFING_SCRIPT):
        if logger:
            logger.info(f"daily briefing: skip (missing script: {DAILY_POSITION_BRIEFING_SCRIPT})")
        return False

    now = datetime.now(timezone.utc)
    target_hour = DAILY_BRIEFING_HOUR_UTC % 24
    hour_delta = min((now.hour - target_hour) % 24, (target_hour - now.hour) % 24)
    if hour_delta > 1:
        if logger:
            logger.info(
                "daily briefing: skip "
                f"(outside hour window: now_hour={now.hour} target_hour={target_hour} delta={hour_delta})"
            )
        return False

    briefing_state = {}
    if os.path.exists(DAILY_BRIEFING_STATE_FILE):
        try:
            with open(DAILY_BRIEFING_STATE_FILE, "r", encoding="utf-8-sig") as fh:
                briefing_state = json.load(fh)
        except Exception as exc:
            if logger:
                logger.warning(f"daily briefing: no pude leer state ({exc})")
            briefing_state = {}

    today = now.date().isoformat()
    if briefing_state.get("last_sent_date") == today:
        if logger:
            logger.info(f"daily briefing: skip (already sent today: {today})")
        return False

    command = [
        sys.executable,
        DAILY_POSITION_BRIEFING_SCRIPT,
        "--lifecycle-file",
        TRADE_LIFECYCLE_FILE,
        "--sl-state-file",
        SL_RETROSPECTIVE_STATE_FILE,
        "--briefing-state-file",
        DAILY_BRIEFING_STATE_FILE,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"daily briefing: fallo ejecutando script ({exc})")
        return False

    if result.returncode != 0:
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"daily briefing: fallo ({detail[:500]})")
        return False

    if logger:
        logger.info("daily briefing: OK")
    return True


def maybe_send_daily_bot_digest(now=None):
    """v10.6.48: Digest diario de P&L vía leaderboard. One-shot por día a partir de DAILY_DIGEST_HOUR_UTC UTC."""
    logger = globals().get("log")
    if not DAILY_DIGEST_ENABLED:
        if logger:
            logger.info("daily digest: skip (DAILY_DIGEST_ENABLED=0)")
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if now.hour < DAILY_DIGEST_HOUR_UTC:
        return False

    today = now.date().isoformat()
    digest_state: dict = {}
    if os.path.exists(DAILY_DIGEST_STATE_FILE):
        try:
            with open(DAILY_DIGEST_STATE_FILE, "r", encoding="utf-8-sig") as fh:
                digest_state = json.load(fh)
        except Exception as exc:
            if logger:
                logger.warning(f"daily digest: no pude leer state ({exc})")
            digest_state = {}

    if digest_state.get("last_sent_date") == today:
        if logger:
            logger.info(f"daily digest: skip (already sent today: {today})")
        return False

    if not os.path.exists(DAILY_DIGEST_SCRIPT):
        if logger:
            logger.warning(f"daily digest: skip (missing script: {DAILY_DIGEST_SCRIPT})")
        return False

    command = [sys.executable, DAILY_DIGEST_SCRIPT, "--write-snapshot", "--send-telegram-manual",
               "--traders-activity-profile"]
    if DB_THROUGHPUT_DIGEST_ENABLED:
        command.extend(["--db-throughput-report", "--db", SQLITE_DB_PATH])

    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception as exc:
        if logger:
            logger.warning(f"daily digest: fallo ejecutando script ({exc})")
        return False

    if result.returncode not in (0, 2):
        if logger:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            logger.warning(f"daily digest: fallo ({detail[:500]})")
        return False

    if logger:
        output = (result.stdout or "").strip()
        sent_line = next((ln for ln in output.splitlines() if "telegram_manual_send=" in ln), "")
        logger.info(f"daily digest: OK ({sent_line or 'sin linea de resultado'})")

    try:
        digest_state["last_sent_date"] = today
        digest_state["last_sent_utc"] = now.replace(microsecond=0).isoformat()
        with open(DAILY_DIGEST_STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(digest_state, fh, indent=2)
    except Exception as exc:
        if logger:
            logger.warning(f"daily digest: no pude guardar state ({exc})")

    return True


def _classify_city_bucket(city: str) -> str:
    try:
        if is_city_blocked(city):
            return "BLOCKED"
        if city in ACTIVE_TRADING_CITIES:
            return "ACTIVE"
        if city in CANARY_TRADING_CITIES:
            return "CANARY"
        if city in OBSERVED_AUDIT_CITIES:
            return "OBSERVED_AUDIT"
        if get_effective_city_mode(city) == "shadow":
            return "SHADOW"
        return "UNTRACKED"
    except Exception:
        return "unknown"


def _resolve_observed_coverage_status(city: str) -> str:
    try:
        icao_meta = RESOLUTION_ICAO.get(city, {}) if isinstance(RESOLUTION_ICAO, dict) else {}
        if icao_meta.get("noaa_station_id"):
            return "noaa_configured"
        if icao_meta.get("icao") or (isinstance(RESOLUTION_STATIONS, dict) and city in RESOLUTION_STATIONS):
            return "icao_only"
        if city in OBSERVED_AUDIT_CITIES:
            return "open_meteo_proxy_only"
        return "no_local_station"
    except Exception:
        return "unknown"


def _build_blocked_signal_canonical_id(signal: dict, outcome: str) -> str:
    try:
        city = signal.get("city", "")
        date_str = signal.get("date", "")
        condition = signal.get("condition", "")
        trader = signal.get("trader", "")
        unit = signal.get("unit", "")
        low = signal.get("low") if signal.get("low") is not None else signal.get("threshold_low")
        high = signal.get("high") if signal.get("high") is not None else signal.get("threshold_high")
        value = signal.get("value") if signal.get("value") is not None else signal.get("threshold")
        if condition == "range" and low is not None and high is not None:
            threshold_part = f"{low}-{high}"
        elif condition in {"exact", "at_or_above", "at_or_below"} and value is not None:
            threshold_part = str(value)
        else:
            mk = signal.get("match_key", "")
            return f"{mk}|{outcome}|{trader}"
        return f"{city}|{date_str}|{condition}|{threshold_part}|{unit}|{outcome}|{trader}"
    except Exception:
        mk = signal.get("match_key", "") if isinstance(signal, dict) else ""
        tr = signal.get("trader", "") if isinstance(signal, dict) else ""
        return f"{mk}|{outcome}|{tr}"


def _price_bucket(price) -> str:
    try:
        if price is None:
            return "unknown"
        p = float(price)
        if p < 0.2:
            return "<0.2"
        if p < 0.4:
            return "0.2-0.4"
        if p < 0.6:
            return "0.4-0.6"
        if p < 0.8:
            return "0.6-0.8"
        return ">0.8"
    except Exception:
        return "unknown"


def _extract_token_id(market: dict, index: int):
    try:
        raw = market.get("clobTokenIds")
        if raw is None:
            return None
        tokens = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(tokens, list) and index < len(tokens):
            return tokens[index]
        return None
    except Exception:
        return None


def _resolve_blocked_reason(city: str, condition=None) -> tuple:
    """Returns (reason_blocked, detail). reason_blocked enum: out_of_whitelist, blocked_city, shadow_only_mode, condition_filtered, settlement_risk, mixed, unknown."""
    try:
        reasons = []
        if is_city_blocked(city):
            reasons.append("blocked_city")
        if os.getenv("SHADOW_ONLY_MODE", "").strip().lower() in {"true", "1", "yes"}:
            reasons.append("shadow_only_mode")
        if city not in QUALITY_TRADER_CITIES_WHITELIST:
            reasons.append("out_of_whitelist")
        if condition is not None and str(condition).lower() not in ALLOWED_CONDITIONS:
            reasons.append("condition_filtered")
        if not reasons:
            return ("unknown", "")
        if len(reasons) == 1:
            r = reasons[0]
            if r == "blocked_city":
                return ("blocked_city", "city in BLOCKED_CITIES")
            if r == "shadow_only_mode":
                return ("shadow_only_mode", "SHADOW_ONLY_MODE=1 at record time")
            if r == "out_of_whitelist":
                return ("out_of_whitelist", "city not in QUALITY_TRADER_CITIES_WHITELIST")
            if r == "condition_filtered":
                return ("condition_filtered", f"condition={condition} fuera de ALLOWED_CONDITIONS")
        return ("mixed", "+".join(reasons))
    except Exception:
        return ("unknown", "")


# =============================================================
# v10.6.47 — Fase B2: blocked_signals Telegram summary helpers
# =============================================================

def _blocked_signal_bot_eval_fields(signal: dict) -> dict:
    """
    v3 schema adapter for blocked_signals records.
    Only trusts explicit bot eval metadata already captured upstream.
    """
    if _bot_eval_read_enabled():
        return _bot_eval_join_fields(signal)
    try:
        source = str(signal.get("bot_evaluation_source", "") or "").strip()
        if source not in {"live_eval", "replay", "unknown"}:
            source = "unknown"
        would_have_bought = signal.get("bot_would_have_bought")
        if isinstance(would_have_bought, bool):
            fields = {
                "bot_would_have_bought": would_have_bought,
                "bot_evaluation_source": source,
            }
            if signal.get("bot_evaluation_join_status") in {"captured", "missing"}:
                fields["bot_evaluation_join_status"] = signal.get("bot_evaluation_join_status")
            return fields
    except Exception:
        pass
    return {
        "bot_would_have_bought": False,
        "bot_evaluation_source": "unknown",
    }


def _build_blocked_signal_resolution_record(signal: dict, market: dict, prices, now) -> dict:
    outcome = signal.get("outcome", "")
    yes_p, no_p = float(prices[0]), float(prices[1])
    resolved = yes_p >= 0.95 or no_p >= 0.95
    if outcome == "Yes":
        win = yes_p >= 0.95
    elif outcome == "No":
        win = no_p >= 0.95
    else:
        win = False

    city = signal.get("city", "")
    condition = signal.get("condition", "")
    reason_blocked, block_reason_detail = _resolve_blocked_reason(city, condition)
    canonical_signal_id = _build_blocked_signal_canonical_id(signal, outcome)
    bot_eval_fields = _blocked_signal_bot_eval_fields(signal)
    return {
        "schema_version": 3,
        "canonical_signal_id": canonical_signal_id,
        "checked_at": now.isoformat(),
        "match_key": signal.get("match_key", ""),
        "city": city,
        "date": signal.get("date", ""),
        "condition": condition,
        "trader": signal.get("trader", ""),
        "trader_historical_wr": signal.get("trader_win_rate", 0),
        "outcome": outcome,
        "avg_price_entered": signal.get("avg_price", 0),
        "close_price": yes_p if outcome == "Yes" else no_p,
        "resolved": resolved,
        "win_for_trader": bool(win and resolved),
        "has_consensus": signal.get("has_consensus", False),
        "market_id": market.get("id") or None,
        "condition_id": market.get("conditionId") or None,
        "token_id_yes": _extract_token_id(market, 0),
        "token_id_no": _extract_token_id(market, 1),
        "market_slug": market.get("slug") or None,
        "city_mode_at_record_time": get_effective_city_mode(city) or "unknown",
        "whitelist_status_at_record_time": "in" if city in QUALITY_TRADER_CITIES_WHITELIST else "out",
        "city_policy_status_at_record_time": _classify_city_bucket(city),
        "reason_blocked": reason_blocked,
        "block_reason_detail": block_reason_detail,
        "resolution_source": "polymarket_market_price",
        "observed_coverage_status": _resolve_observed_coverage_status(city),
        "settlement_source": "unknown",
        "settlement_fidelity_status": "unverified",
        "bot_edge_pct_at_signal": bot_eval_fields.get("bot_edge_pct_at_signal"),
        "bot_would_have_bought": bot_eval_fields["bot_would_have_bought"],
        "bot_evaluation_source": bot_eval_fields["bot_evaluation_source"],
        **({"bot_skip_or_block_reason": bot_eval_fields.get("bot_skip_or_block_reason")} if "bot_skip_or_block_reason" in bot_eval_fields else {}),
        **({"bot_decision_gate": bot_eval_fields.get("bot_decision_gate")} if "bot_decision_gate" in bot_eval_fields else {}),
        **({"bot_decision_confidence": bot_eval_fields.get("bot_decision_confidence")} if "bot_decision_confidence" in bot_eval_fields else {}),
        **({"bot_evaluation_join_status": bot_eval_fields.get("bot_evaluation_join_status")} if "bot_evaluation_join_status" in bot_eval_fields else {}),
        "price_bucket": _price_bucket(signal.get("avg_price", 0)),
    }


def _bs_normalize(rec):
    out = dict(rec)
    out.setdefault("schema_version", 1)
    out.setdefault("reason_blocked", "unknown")
    out.setdefault("city_policy_status_at_record_time", "unknown")
    out.setdefault("whitelist_status_at_record_time", "unknown")
    out.setdefault("settlement_fidelity_status", "unknown")
    out.setdefault("observed_coverage_status", "unknown")
    if "win_for_trader" not in out:
        out["win_for_trader"] = bool(out.get("win", False))
    return out


def _bs_wr(wins, total):
    if total == 0:
        return None
    return round(wins / total * 100, 1)


def _blocked_signals_build_telegram_summary(all_records, whitelist_cities=None):
    """
    Build summary dict for the daily Telegram alert from BLOCKED_SIGNALS_FILE records.
    Works with mixed v1/v2 schema. Returns minimal dict for empty input without raising.
    """
    if whitelist_cities is None:
        whitelist_cities = set()
    records = [_bs_normalize(r) for r in all_records]
    total = len(records)
    if total == 0:
        return {"total": 0, "level": "INFO", "has_v2": False, "v1_count": 0, "v2_count": 0}

    v1_count = sum(1 for r in records if r["schema_version"] == 1)
    v2_count = total - v1_count
    has_v2 = v2_count > 0

    out_wl = [r for r in records if r.get("whitelist_status_at_record_time") == "out"]
    in_wl = [r for r in records if r.get("whitelist_status_at_record_time") == "in"]
    unknown_wl = [r for r in records if r.get("whitelist_status_at_record_time") not in ("in", "out")]
    out_resolved = [r for r in out_wl if r.get("resolved")]
    out_wins = sum(1 for r in out_resolved if r.get("win_for_trader"))

    fuera_recs = [r for r in records if r.get("city") not in whitelist_cities]
    fuera_resolved = [r for r in fuera_recs if r.get("resolved")]
    fuera_wins = sum(1 for r in fuera_resolved if r.get("win_for_trader"))
    canary_excl = [r for r in records if r.get("city") in whitelist_cities and r.get("resolved")]

    city_map = {}
    for r in (out_wl if (has_v2 and out_wl) else records):
        city = r.get("city", "")
        if city:
            city_map.setdefault(city, []).append(r)
    city_stats = []
    for city, recs in city_map.items():
        res = [r for r in recs if r.get("resolved")]
        wins_c = sum(1 for r in res if r.get("win_for_trader"))
        city_stats.append({
            "city": city, "n": len(recs), "resolved": len(res),
            "wins": wins_c, "wr": _bs_wr(wins_c, len(res)),
        })
    city_stats.sort(key=lambda x: x["n"], reverse=True)
    top3 = city_stats[:3]
    top3_total = sum(c["n"] for c in top3)
    top3_pct = round(top3_total / total * 100, 1) if total > 0 else 0.0

    n_fid = sum(1 for r in records if r.get("settlement_fidelity_status") in ("unverified", "unknown"))
    fidelity_pct = round(n_fid / total * 100, 1) if total > 0 else 0.0

    v2_recs = [r for r in records if r["schema_version"] == 2]
    top_reason = top_policy = None
    if v2_recs:
        rc = {}
        for r in v2_recs:
            k = r.get("reason_blocked", "unknown")
            rc[k] = rc.get(k, 0) + 1
        top_reason = max(rc, key=rc.get)
        pc = {}
        for r in v2_recs:
            k = r.get("city_policy_status_at_record_time", "unknown")
            pc[k] = pc.get(k, 0) + 1
        top_policy = max(pc, key=pc.get)

    audit_candidates = []
    for cs in city_stats:
        if cs["n"] >= 10 and cs["wr"] is not None and cs["wr"] >= 70:
            c_recs = city_map[cs["city"]]
            is_out = any(r.get("whitelist_status_at_record_time") == "out" for r in c_recs)
            if is_out or has_v2:
                audit_candidates.append(cs["city"])

    n_fuera_res = len(fuera_resolved)
    fuera_wr = _bs_wr(fuera_wins, n_fuera_res)
    out_wr = _bs_wr(out_wins, len(out_resolved))
    v2_low_sample_legacy_fallback = (
        has_v2
        and len(out_resolved) < 50
        and n_fuera_res >= 50
        and fuera_wr is not None
        and fuera_wr >= 70
        and fidelity_pct >= 50.0
    )
    level = "INFO"
    if has_v2:
        if len(out_resolved) >= 50 and out_wr is not None:
            if out_wr >= 70 and top3_pct < 60:
                level = "ACTION"
            elif out_wr >= 55:
                level = "WATCH"
        elif v2_low_sample_legacy_fallback:
            level = "WATCH_AUDIT"
    elif n_fuera_res >= 50 and fuera_wr is not None and fuera_wr >= 70:
        level = "ACTION"
    elif n_fuera_res >= 30 and fuera_wr is not None and fuera_wr >= 55:
        level = "WATCH"

    return {
        "total": total,
        "v1_count": v1_count,
        "v2_count": v2_count,
        "has_v2": has_v2,
        "out_wl_count": len(out_wl),
        "in_wl_count": len(in_wl),
        "unknown_wl_count": len(unknown_wl),
        "out_wl_resolved": len(out_resolved),
        "out_wl_wins": out_wins,
        "out_wl_wr": out_wr,
        "fuera_resolved": n_fuera_res,
        "fuera_wins": fuera_wins,
        "fuera_wr": fuera_wr,
        "canary_excluded_count": len(canary_excl),
        "top3": top3,
        "top3_pct": top3_pct,
        "concentration_warning": top3_pct > 60.0,
        "fidelity_unverified_pct": fidelity_pct,
        "v2_low_sample_legacy_fallback": v2_low_sample_legacy_fallback,
        "top_reason_blocked": top_reason,
        "top_city_policy": top_policy,
        "audit_candidate_cities": audit_candidates,
        "top_cities_source": "out_whitelist" if (has_v2 and out_wl) else "global",
        "level": level,
    }


def _blocked_signals_format_telegram(summary):
    """
    Format blocked signals summary dict as Telegram HTML string (~2000 chars max).
    Always includes: schema v1/v2, settlement unverified%, 'no accionable para trading'.
    """
    if summary.get("total", 0) == 0:
        return (
            "📊 <b>Blocked signals — auditoría diaria</b>\n"
            "Sin registros en el período.\n"
            "Nivel: <b>INFO</b>"
        )
    total = summary["total"]
    v1 = summary["v1_count"]
    v2 = summary["v2_count"]
    has_v2 = summary["has_v2"]
    level = summary["level"]

    lines = ["📊 <b>Blocked signals — auditoría diaria</b>"]
    lines.append(f"Total: {total} | v1/v2: {v1}/{v2}")

    if has_v2:
        out_n = summary.get("out_wl_count", 0)
        in_n = summary.get("in_wl_count", 0)
        unk_n = summary.get("unknown_wl_count", 0)
        lines.append(f"OUT whitelist: {out_n} | IN: {in_n} | Unknown: {unk_n}")
        out_res = summary.get("out_wl_resolved", 0)
        out_wins = summary.get("out_wl_wins", 0)
        out_wr = summary.get("out_wl_wr")
        if out_res > 0:
            wr_s = f"{out_wr}%" if out_wr is not None else "n/d"
            lines.append(f"WR OUT whitelist: {wr_s} ({out_wins}/{out_res})")
    else:
        lines.append(f"OUT whitelist: n/d | Unknown: {total}")
        fuera_res = summary.get("fuera_resolved", 0)
        fuera_wins = summary.get("fuera_wins", 0)
        fuera_wr = summary.get("fuera_wr")
        if fuera_res > 0:
            wr_s = f"{fuera_wr}%" if fuera_wr is not None else "n/d"
            lines.append(f"WR global: {wr_s} ({fuera_wins}/{fuera_res})")
        lines.append("<i>Mayoría registros v1: clasificación limitada.</i>")

    top3 = summary.get("top3", [])
    if top3:
        src = "(OUT wl)" if summary.get("top_cities_source") == "out_whitelist" else "(global)"
        lines.append(f"Top ciudades {src}:")
        for i, c in enumerate(top3, 1):
            wr_s = f"{c['wr']}%" if c["wr"] is not None else "n/d"
            lines.append(f"  {i}. {c['city']} {c['n']} | WR {wr_s}")

    top3_pct = summary.get("top3_pct", 0.0)
    lines.append(f"Concentración top3: {top3_pct}%")
    if summary.get("concentration_warning"):
        lines.append("<i>[alta concentración]</i>")

    fid_pct = summary.get("fidelity_unverified_pct", 0.0)
    lines.append(f"Settlement unverified/unknown: {fid_pct}%")
    if summary.get("v2_low_sample_legacy_fallback"):
        lines.append("<i>v2 OUT resolved &lt;50: fallback v1 queda solo como auditoria de datos.</i>")

    if has_v2:
        top_r = summary.get("top_reason_blocked")
        if top_r and top_r != "unknown":
            lines.append(f"Top reason_blocked: {top_r}")
        top_p = summary.get("top_city_policy")
        if top_p and top_p != "unknown":
            lines.append(f"Top city_policy: {top_p}")

    cands = summary.get("audit_candidate_cities", [])
    if cands:
        cand_s = ", ".join(cands[:5])
        if len(cands) > 5:
            cand_s += f" (+{len(cands) - 5})"
        lines.append(f"Candidatos auditoría: {cand_s}")

    excl = summary.get("canary_excluded_count", 0)
    if excl > 0:
        lines.append(f"Excluidas (ya en whitelist): {excl}")

    lines.append(f"Nivel: <b>{level}</b>")
    _lvl_note = {
        "INFO": "No accionable para trading.",
        "WATCH": "No accionable para trading. Acumular muestra.",
        "WATCH_AUDIT": "No accionable para trading. Auditoría de datos — sin cambios en whitelist ni city modes sin revisión separada.",
        "ACTION": "No accionable para trading. Auditoría de datos — sin cambios en whitelist ni city modes sin revisión separada.",
    }
    lines.append(_lvl_note.get(level, "No accionable para trading."))
    lines.append(
        "<i>Para investigar: python tools/blocked_signals_audit.py "
        "--source data/blocked_signals_resolutions.jsonl --markdown --top 10</i>"
    )

    msg = "\n".join(lines)
    if len(msg) > 2200:
        msg = msg[:2150] + "…\n<i>[truncado]</i>"
    return msg


def maybe_run_blocked_signals_check(state, now=None):
    """
    v10.6.13: mide diariamente la WR de señales exact/range bloqueadas por
    condition_filtered. Corre una vez por día (primer ciclo del día).
    Appenda a BLOCKED_SIGNALS_FILE y manda Telegram con WR actualizada.
    Avisos one-shot con instrucción copiable en n=30 (Sonnet) y n=50 (Opus).
    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if state.get("blocked_signals_last_date") == today:
        return False

    try:
        if not os.path.exists(SIGNALS_FILE):
            return False

        # --- Leer signals.json (puede tener UTF-8 BOM) ---
        try:
            with open(SIGNALS_FILE, "r", encoding="utf-8-sig") as f:
                sig_data = json.load(f)
        except Exception:
            with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
                sig_data = json.load(f)

        signals = sig_data.get("signals", []) if isinstance(sig_data, dict) else []

        cutoff = (now.date() - timedelta(days=1)).isoformat()
        candidates = [
            s for s in signals
            if isinstance(s, dict)
            and s.get("condition") in {"exact", "range"}
            and s.get("date", "") <= cutoff
        ]

        if not candidates:
            state["blocked_signals_last_date"] = today
            return True

        # --- Cargar claves ya procesadas ---
        # v10.6.44: dedupe acepta canonical_signal_id (v2) y match_key (v1 fallback).
        # Registros v1 existentes bloquean re-insercion por match_key.
        # Registros nuevos usan canonical_signal_id mas granular, permitiendo
        # capturar multiples traders por mismo match_key v1.
        existing_canonical_ids = set()
        if os.path.exists(BLOCKED_SIGNALS_FILE):
            try:
                with open(BLOCKED_SIGNALS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rec = json.loads(line)
                            canonical = rec.get("canonical_signal_id")
                            if canonical:
                                existing_canonical_ids.add(canonical)
                            else:
                                existing_canonical_ids.add(rec.get("match_key", ""))
            except Exception:
                pass

        new_candidates = [
            s for s in candidates
            if _build_blocked_signal_canonical_id(s, s.get("outcome", "")) not in existing_canonical_ids
        ]

        if new_candidates:
            # --- Fetch mercados cerrados (últimas 3 páginas = ~300 eventos = ~1 semana) ---
            market_map = {}
            for offset in range(0, 300, 100):
                try:
                    events = api_get(
                        f"/events?tag_id={DAILY_TEMP_TAG_ID}"
                        f"&closed=true&limit=100&offset={offset}"
                        f"&order=startDate&ascending=false",
                        retries=2, delay=3,
                    )
                    time.sleep(0.3)
                except Exception:
                    break
                if not events:
                    break
                for event in events:
                    for market in event.get("markets", []):
                        q = market.get("question", "").strip()
                        if q:
                            market_map[q.lower()] = market
                if len(events) < 100:
                    break

            # --- Procesar nuevas señales ---
            new_records = []
            for signal in new_candidates:
                title = signal.get("title", "").strip()
                # Normalizar bug encoding: U+252C U+2591 (┬░) → ° (U+00B0)
                normalized = title.replace("\u252c\u2591", "\u00b0").lower()
                market = market_map.get(normalized)
                if not market:
                    continue

                prices_raw = market.get("outcomePrices", "[]")
                try:
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    yes_p, no_p = float(prices[0]), float(prices[1])
                except Exception:
                    continue

                new_records.append(_build_blocked_signal_resolution_record(signal, market, prices, now))

            if new_records:
                blocked_dir = os.path.dirname(BLOCKED_SIGNALS_FILE)
                if blocked_dir:
                    os.makedirs(blocked_dir, exist_ok=True)
                with open(BLOCKED_SIGNALS_FILE, "a", encoding="utf-8") as f:
                    for rec in new_records:
                        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

        # --- Leer totales del JSONL completo ---
        all_records = []
        if os.path.exists(BLOCKED_SIGNALS_FILE):
            try:
                with open(BLOCKED_SIGNALS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_records.append(json.loads(line))
            except Exception:
                pass

        all_resolved = [r for r in all_records if r.get("resolved")]
        # v10.6.18: excluir ciudades ya abiertas por canary — esas señales ya no están bloqueadas
        # y cuentan en condition_reopen_monitor, no en este baseline
        canary_excluded_recs = [r for r in all_resolved if r.get("city") in QUALITY_TRADER_CITIES_WHITELIST]
        resolved_recs = [r for r in all_resolved if r.get("city") not in QUALITY_TRADER_CITIES_WHITELIST]
        n_resolved = len(resolved_recs)
        n_win = sum(1 for r in resolved_recs if r.get("win_for_trader"))
        wr_pct = round(n_win / n_resolved * 100, 1) if n_resolved > 0 else 0.0

        # --- Telegram diario (Fase B2) ---
        try:
            _bs_summary = _blocked_signals_build_telegram_summary(
                all_records, whitelist_cities=QUALITY_TRADER_CITIES_WHITELIST
            )
            _bs_msg = _blocked_signals_format_telegram(_bs_summary)
        except Exception as _bs_e:
            _log = globals().get("log")
            if _log:
                _log.warning(f"blocked signals telegram summary fallo ({_bs_e}), usando fallback")
            _fallback_action = "INFO"
            _fallback_task = "Sin tarea nueva: usar como baseline de inteligencia, no como permiso automatico de trading."
            _fallback_v2_recs = [r for r in all_records if r.get("schema_version") == 2]
            _fallback_v2_out_resolved = [
                r for r in _fallback_v2_recs
                if r.get("resolved") and r.get("whitelist_status_at_record_time") == "out"
            ]
            _fallback_low_fidelity_v2 = (
                bool(_fallback_v2_recs)
                and len(_fallback_v2_out_resolved) < 50
                and any(r.get("settlement_fidelity_status") in (None, "unknown", "unverified") for r in all_records)
            )
            if n_resolved >= 50 and wr_pct >= 70 and not _fallback_low_fidelity_v2:
                _fallback_action = "ACTION"
                _fallback_task = (
                    "Accion: priorizar auditoria de las ciudades fuera de whitelist con mas muestra "
                    "(whitelist, cobertura observada y fuente de resolucion) antes de tocar reglas core."
                )
            elif n_resolved >= 50 and wr_pct >= 70 and _fallback_low_fidelity_v2:
                _fallback_action = "WATCH_AUDIT"
                _fallback_task = (
                    "No accionable para trading. Auditoría de datos — sin cambios en whitelist "
                    "ni city modes sin revisión separada."
                )
            elif n_resolved >= 30 and wr_pct >= 55:
                _fallback_action = "WATCH"
                _fallback_task = "Accion diferida: acumular muestra o cruzar con gap operativo real por ciudad."
            _bs_msg = (
                f"📊 <b>Blocked signals (fuera de whitelist) - WR diaria</b>\n"
                f"Baseline fuera de whitelist: {n_resolved} resueltas | Wins: {n_win} | WR: {wr_pct}%\n"
                f"Excluidas del calculo por estar ya en whitelist: {len(canary_excluded_recs)}\n"
                f"Nivel: <b>{_fallback_action}</b>\n"
                f"{_fallback_task}\n"
                f"<i>Baseline fuera de QUALITY_TRADER_CITIES_WHITELIST; no mide ejecucion real del bot.</i>"
            )
        send_telegram(_bs_msg)

        # --- One-shot n>=30/n>=50: suprimir si canary ya abierto (decision tomada en Sesion 175) ---
        if now.date() >= date(2026, 4, 14):
            state["blocked_signals_30_notified"] = True
            state["blocked_signals_50_notified"] = True
        else:
            # --- Aviso one-shot n>=30: instruccion para Sonnet ---
            if n_resolved >= 30 and not state.get("blocked_signals_30_notified"):
                send_telegram(
                    f"\U0001f514 <b>Blocked signals — primera muestra lista (n={n_resolved})</b>\n"
                    f"WR actual: {wr_pct}% ({n_win}/{n_resolved} wins)\n\n"
                    f"<b>Instruccion para Sonnet:</b>\n"
                    f"<code>Analizar blocked_signals_resolutions.jsonl ({n_resolved} resoluciones). "
                    f"Calcular WR total, por condition (exact/range) y por ciudad (n\u22653). "
                    f"Comparar con threshold 55% para reabrir condition_filtered. "
                    f"Contexto: docs/next-session-handoff-2026-04-13-B-blocked-settlement.md "
                    f"y docs/blocked-signals-wr-baseline-2026-04-13.md</code>"
                )
                state["blocked_signals_30_notified"] = True

            # --- Aviso one-shot n>=50: instruccion para Opus ---
            if n_resolved >= 50 and not state.get("blocked_signals_50_notified"):
                verdict = "REOPEN CANDIDATE" if wr_pct >= 55 else ("GRAY ZONE" if wr_pct >= 50 else "FILTER VALIDATED")
                send_telegram(
                    f"\U0001f52c <b>Blocked signals — muestra robusta (n={n_resolved})</b>\n"
                    f"WR: {wr_pct}% ({n_win}/{n_resolved}) — {verdict}\n\n"
                    f"<b>Instruccion para Opus:</b>\n"
                    f"<code>Decision condition_filtered: WR={wr_pct}% en n={n_resolved} señales "
                    f"exact/range de quality traders. "
                    f"Si WR\u226555%: disenar experimento canary minimo "
                    f"(1 condicion, 1 ciudad, edge\u226520%, sizing minimo). "
                    f"Archivos: blocked_signals_resolutions.jsonl, "
                    f"docs/blocked-signals-wr-baseline-2026-04-13.md, "
                    f"docs/next-session-handoff-2026-04-13-B-blocked-settlement.md</code>"
                )
                state["blocked_signals_50_notified"] = True

    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"blocked signals check: fallo ({e})")
        return False

    state["blocked_signals_last_date"] = today
    return True


# =============================================================
# v10.6.18 — W17 observation alert (one-shot, 2026-04-20)
# =============================================================

def maybe_run_w17_observation_alert(state, now=None):
    """
    v10.6.18: alerta one-shot de observacion W17.

    Dispara una sola vez el 2026-04-20 o posterior (primer ciclo del dia).
    Resume los cambios de config de la semana y entrega el prompt exacto
    para la sesion Sonnet/Codex de revision.

    Cambios que mide:
    - QUALITY_TRADER_CITIES_WHITELIST ampliada (Atlanta, London, NYC, Munich)
    - Slot 23h desactivado
    - Fix v10.6.18: YES exact/range canary requiere our_prob >= 65%

    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    FIRE_DATE = "2026-04-20"
    STATE_KEY = "w17_observation_alert_sent"

    if state.get(STATE_KEY):
        return False
    if now.date().isoformat() < FIRE_DATE:
        return False

    # Anti-spam: solo primer ciclo del dia
    today_str = now.date().isoformat()
    last_daily = state.get("w17_observation_alert_last_daily", "")
    if last_daily == today_str:
        return False

    # Recoger metricas recientes de cycles_history si esta disponible
    cycles_after_deploy = 0
    buys_after_deploy = 0
    edges_after_deploy = 0
    avg_eval = 0.0
    try:
        ch_path = os.path.join(DATA_DIR, "cycles_history.jsonl")
        rows = []
        if os.path.exists(ch_path):
            with open(ch_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    ts = obj.get("timestamp_utc", "")
                    if ts >= "2026-04-17T18:00":
                        rows.append(obj)
            if rows:
                cycles_after_deploy = len(rows)
                buys_after_deploy = sum(len(r.get("buys", [])) for r in rows)
                edges_after_deploy = sum(r.get("scan", {}).get("with_edge", 0) for r in rows)
                evals = [r.get("scan", {}).get("markets_evaluated", 0) for r in rows]
                avg_eval = sum(evals) / len(evals) if evals else 0
    except Exception:
        pass

    prompt_codex = (
        "Lee AGENTS.md y el bloque reciente de CONTEXTO.md.\n\n"
        "Tarea: Sesion de observacion W17 — revisar si los cambios del 17 de abril funcionaron.\n\n"
        "Cambios aplicados el 2026-04-17:\n"
        "- QUALITY_TRADER_CITIES_WHITELIST ampliada: +Atlanta, London, New York City, Munich\n"
        "- Slot 23h desactivado (SCHEDULE_DISABLED_HOURS_UTC=23)\n"
        "- Fix v10.6.18/19: YES exact/range canary bloqueado si our_prob < 65% (exact) / 72% (range)\n\n"
        "Archivos a leer:\n"
        "- data/runtime_import/cycles_history.jsonl (ciclos desde 2026-04-17T18:00)\n"
        "- data/runtime_import/skip_log.jsonl (ultimas 1000 entradas)\n"
        "- data/runtime_import/cycle_summary.json (ultimo ciclo)\n"
        "- docs/strategic-review-opus-2026-04-17.md (contexto estrategico)\n"
        "- docs/execution-plan-w17-2026-04-17.md (plan + criterios de exito)\n"
        "- docs/c1-autopsy-exact-range-2026-04-17.md (hallazgos autopsia)\n\n"
        "Preguntas a responder:\n"
        "1. markets_evaluated promedio post-deploy vs pre-deploy (target >= 25)\n"
        "2. with_edge promedio post-deploy (target >= 0.5/ciclo)\n"
        "3. buys/ciclo post-deploy (target >= 0.3)\n"
        "4. Hay exact/range NO-side con quality trader? Cuales ciudades?\n"
        "5. El fix YES our_prob<65% esta bloqueando correctamente? (ver skip_log 'exact_range_yes_low_confidence')\n"
        "6. El slot 23h desaparecio de cycles_history?\n\n"
        "Salida esperada:\n"
        "- Veredicto por gate (cumple / no cumple / parcial)\n"
        "- Si targets no se cumplen: hipotesis de por que y siguiente accion\n"
        "- Actualizar CONTEXTO.md con estado post-deploy\n"
        "- Preparar handoff para la revision Opus del 24 de abril"
    )

    msg = (
        f"\U0001f4ca <b>Alerta W17 — Sesion de observacion lista</b>\n\n"
        f"Han pasado 3 dias desde los cambios del 17 de abril. "
        f"Es momento de revisar si el throughput mejoro.\n\n"
        f"<b>Datos disponibles (post-deploy):</b>\n"
        f"  Ciclos: {cycles_after_deploy}\n"
        f"  Buys: {buys_after_deploy}\n"
        f"  Edges: {edges_after_deploy}\n"
        f"  Eval/ciclo: {avg_eval:.1f}\n\n"
        f"<b>Targets W17:</b>\n"
        f"  markets_evaluated: &gt;= 25/ciclo\n"
        f"  with_edge: &gt;= 0.5/ciclo\n"
        f"  buys/ciclo: &gt;= 0.3\n\n"
        f"<b>Prompt para Sonnet/Codex</b> (copiar y pegar):\n"
        f"<code>{prompt_codex}</code>"
    )

    try:
        send_telegram(msg)
    except Exception:
        pass

    state[STATE_KEY] = True
    state["w17_observation_alert_last_daily"] = today_str
    return True


def maybe_alert_p4_p5_expansion(state, now=None):
    """
    v10.6.20: alerta one-shot de expansion post-checkpoint condition_filtered (P4+P5).

    Dispara el 2026-04-22 o posterior (dia posterior al checkpoint dia 7 del
    canary exact/range abierto el 2026-04-14). Entrega prompt explicito para
    que Codex evalue expansion whitelist exact/range (P4) + universo ciudades
    (P5) usando evidencia acumulada.

    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    FIRE_DATE = "2026-04-22"
    STATE_KEY = "p4_p5_expansion_alert_sent"

    if state.get(STATE_KEY):
        return False
    if now.date().isoformat() < FIRE_DATE:
        return False

    today_str = now.date().isoformat()
    last_daily = state.get("p4_p5_expansion_alert_last_daily", "")
    if last_daily == today_str:
        return False

    prompt_codex = (
        "Lee AGENTS.md, CONTEXTO.md ultimo bloque y OPERATIONS_PLAYBOOK.md.\n\n"
        "Tarea: Expansion post-checkpoint condition_filtered (P4+P5).\n\n"
        "Precondicion critica: verificar el checkpoint dia 7 del 2026-04-21. "
        "LOGICA CORRECTA: el canary se cierra SOLO si WR<50% con n>=15. "
        "Si n<15 (muestra insuficiente), verdict=OK_INSUFICIENTE — no es "
        "fallo, es falta de volumen; CONTINUAR con expansion. "
        "ABORTAR solo si n>=15 y WR<50% (verdict CLOSE/ALERT real).\n\n"
        "Contexto actual (2026-04-21): WR bot exact/range = 40.0% (2/5), n=5 < 15. "
        "Verdict = OK_INSUFICIENTE. Canary activo. Checkpoint dia 14 = 2026-04-28.\n\n"
        "Archivos a leer:\n"
        "- data/runtime_import/trade_lifecycle.json (filtrar opened_at>=2026-04-14, "
        "condition in {exact,range})\n"
        "- data/runtime_import_derived/blocked_signals_resolutions.jsonl\n"
        "- data/runtime_import_derived/signals_crosscheck.jsonl (ultimas 7 corridas)\n"
        "- data/directional_trader_census.json\n"
        "- data/reference_trader_city_market_cross.json\n"
        "- docs/blocked-signals-wr-baseline-2026-04-13.md\n"
        "- docs/handoffs/condition-filtered-canary-implement-2026-04-14.md\n\n"
        "P4 - Expandir whitelist exact/range:\n"
        "NOTA: el 2026-04-21 (Sesion 213) ya se anadieron: Tel Aviv, Taipei, "
        "Singapore, Wuhan. Verificar que esten en Railway. Si faltan, anadirlos.\n"
        "1. Correr tools/blocked_signals_settlement_tracker.py fresh.\n"
        "2. Identificar ciudades con WR>=55% n>=3 que NO esten en "
        "QUALITY_TRADER_CITIES_WHITELIST actual.\n"
        "3. Buscar candidatas nuevas con evidencia. Priorizar: Amsterdam, "
        "Moscow, Jeddah (si P5 ya las tiene en RESOLUTION_STATIONS).\n"
        "4. Proponer adicion a whitelist con evidencia cuantitativa por ciudad.\n\n"
        "P5 - Ampliar universo de ciudades:\n"
        "1. Leer signals_crosscheck.jsonl - bloque TRADER_ONLY.\n"
        "2. De las ~21 ciudades TRADER_ONLY, filtrar las que:\n"
        "   a) Tengan consensus>=2 traders quality\n"
        "   b) Tengan RESOLUTION_STATIONS disponibles en NOAA (verificar ICAO + "
        "stationid ISD historico)\n"
        "   c) NO sean blocked_cities ni legacy blocked\n"
        "3. Proponer 3-5 candidatas top con:\n"
        "   - Coords NOAA (lat/lon)\n"
        "   - ICAO + noaa_station_id + noaa_daily_station_id\n"
        "   - Timezone correcta\n"
        "   - Muestra historica que justifique (consensus, WR traders)\n"
        "4. Preparar patch bot.py con RESOLUTION_STATIONS, RESOLUTION_ICAO, "
        "CITY_TIMEZONES, OBSERVED_AUDIT_CITIES.\n\n"
        "Guardrails:\n"
        "- NO tocar filtros de precio, MIN_EDGE global, Kelly, sigma, exits.\n"
        "- NO anadir ciudad sin RESOLUTION_STATIONS verificado (evitar Seoul "
        "mismatch repetido - sesion 185).\n"
        "- verify_before_deploy.py debe cerrar verde antes de commit.\n\n"
        "Salida esperada:\n"
        "- Patch en bot.py (si P5 aplica).\n"
        "- Lista de env vars Railway a actualizar (P4).\n"
        "- docs/p4-p5-expansion-2026-04-22.md con evidencia y decision.\n"
        "- Commit + push + deploy Railway.\n"
        "- Actualizar CONTEXTO.md y engram."
    )

    msg = (
        f"\U0001f680 <b>Alerta P4+P5 \u2014 Expansion post-checkpoint</b>\n\n"
        f"Han pasado &gt;=1 dia desde el checkpoint dia 7 del canary "
        f"condition_filtered exact/range (2026-04-21).\n\n"
        f"<b>Precondicion critica:</b>\n"
        f"  Verificar que el checkpoint cerro en OK o PROMOTE.\n"
        f"  Si fue CLOSE/ALERT: abortar expansion y notificar.\n\n"
        f"<b>Tareas</b>:\n"
        f"  P4 = expandir QUALITY_TRADER_CITIES_WHITELIST.\n"
        f"  P5 = ampliar universo 3-5 ciudades del set TRADER_ONLY.\n\n"
        f"<b>Prompt para Codex</b> (copiar y pegar):\n"
        f"<code>{prompt_codex}</code>"
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"p4_p5 expansion alert: fallo al enviar Telegram ({e})")
        state["p4_p5_expansion_alert_last_daily"] = today_str
        return True

    state[STATE_KEY] = True
    state["p4_p5_expansion_alert_last_daily"] = today_str
    return True


def maybe_alert_p6_p7_post_v2_cleanup(state, now=None):
    """
    v10.6.20: alerta one-shot de limpieza post-V2 cutover (P6+P7).

    Dispara el 2026-04-25 o posterior (3 dias despues del cutover V1->V2 del
    2026-04-22). Entrega prompt explicito para Codex sobre dos tareas de
    limpieza pendientes que quedaron bloqueadas durante la ventana V2:
    P6 - Reset shadow_city_tracking Seoul legacy (post Seoul station mismatch
    fix sesion 185).
    P7 - Investigar MIN_EDGE por ciudad para WR>70% historico.

    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    FIRE_DATE = "2026-04-25"
    STATE_KEY = "p6_p7_post_v2_alert_sent"

    if state.get(STATE_KEY):
        return False
    if now.date().isoformat() < FIRE_DATE:
        return False

    today_str = now.date().isoformat()
    last_daily = state.get("p6_p7_post_v2_alert_last_daily", "")
    if last_daily == today_str:
        return False

    prompt_codex = (
        "Lee AGENTS.md, CONTEXTO.md ultimo bloque y OPERATIONS_PLAYBOOK.md.\n\n"
        "Tarea: Limpieza post-V2 cutover (P6+P7). Ambas tareas asumen que el "
        "cutover V1->V2 del 2026-04-22 cerro limpio y el bot lleva >=3 dias "
        "estable en V2 SDK (sin errores CLOB repetidos).\n\n"
        "Precondicion critica: verificar en Railway logs que no hay errores "
        "recurrentes en create_or_derive_api_key, get_open_orders ni auth "
        "endpoints. Si hay inestabilidad V2, ABORTAR P6+P7 y escalar a Opus.\n\n"
        "P6 - Reset shadow_city_tracking Seoul legacy:\n"
        "Contexto: sesion 185 (2026-04-17) arreglo Seoul station mismatch "
        "(Incheon -> KMA Seoul City). El shadow_city_tracking acumulo datos "
        "previos al fix con forecasts erroneos (~65 ciclos con fuente "
        "Incheon). La promotion logic podria mezclar muestra contaminada con "
        "post-fix.\n"
        "Pasos:\n"
        "1. Backup: cp data/runtime_import/shadow_city_tracking.json "
        "data/runtime_import/shadow_city_tracking.json.bak-pre-p6\n"
        "2. Filtrar entradas Seoul anteriores a 2026-04-17 (fecha fix "
        "RESOLUTION_STATIONS). Conservar solo Seoul post-fix.\n"
        "3. Reescribir el JSON con Seoul aislado; otras ciudades intactas.\n"
        "4. Verificar que city_promotion_gate y notify_active_candidates "
        "ahora leen solo evidencia post-fix para Seoul.\n"
        "5. Actualizar el archivo en Railway via railway_safe.ps1 ssh.\n\n"
        "P7 - Investigar MIN_EDGE por ciudad:\n"
        "Contexto: MIN_EDGE_PCT global obliga a todas las ciudades al mismo "
        "umbral. Ciudades con WR historico >70% podrian operar con MIN_EDGE "
        "mas bajo sin incrementar riesgo. Esto aumentaria throughput.\n"
        "Pasos:\n"
        "1. Leer trade_lifecycle.json, agrupar por city.\n"
        "2. Para cada ciudad con n_closed>=10 calcular: WR, PnL neto, avg "
        "edge entrada, EV realizado.\n"
        "3. Identificar ciudades con WR>=70% n>=10 y PnL>0.\n"
        "4. Calcular MIN_EDGE propuesto por ciudad: target edge minimo tal "
        "que el peor trade historico hubiera sido marginalmente rentable.\n"
        "5. ANALISIS SOLAMENTE, no aplicar. Output:\n"
        "   docs/min-edge-per-city-analysis-2026-04-25.md con:\n"
        "   - Tabla por ciudad (WR, PnL, n, edge historico, MIN_EDGE propuesto)\n"
        "   - Propuesta Railway env var MIN_EDGE_PER_CITY (JSON o CSV)\n"
        "   - Implementacion sugerida (sin tocar aun)\n"
        "6. Opus decidira en sesion siguiente si aplicar y como implementar.\n\n"
        "Guardrails:\n"
        "- P6 toca data (no codigo). P7 es analisis puro (no toca nada).\n"
        "- NO modificar trading core, filtros, Kelly, sigma en esta sesion.\n"
        "- verify_before_deploy.py debe cerrar verde si se tocase codigo "
        "(solo aplicable a P6 si modifica script de sync).\n"
        "- Si P6 y P7 resultan en cambios de codigo: commit separados.\n\n"
        "Salida esperada:\n"
        "- P6: shadow_city_tracking.json actualizado en Railway + backup local.\n"
        "- P7: docs/min-edge-per-city-analysis-2026-04-25.md con propuesta.\n"
        "- Actualizar CONTEXTO.md y engram con ambos resultados."
    )

    msg = (
        f"\U0001f9f9 <b>Alerta P6+P7 \u2014 Limpieza post-V2 cutover</b>\n\n"
        f"Han pasado &gt;=3 dias desde el V2 cutover del 2026-04-22.\n\n"
        f"<b>Precondicion critica:</b>\n"
        f"  Verificar en Railway logs que V2 SDK esta estable.\n"
        f"  Si hay errores recurrentes V2: abortar y escalar a Opus.\n\n"
        f"<b>Tareas</b>:\n"
        f"  P6 = reset shadow_city_tracking Seoul legacy (post sesion 185).\n"
        f"  P7 = investigar MIN_EDGE por ciudad (analisis, no aplicar).\n\n"
        f"<b>Prompt para Codex</b> (copiar y pegar):\n"
        f"<code>{prompt_codex}</code>"
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"p6_p7 post v2 alert: fallo al enviar Telegram ({e})")
        state["p6_p7_post_v2_alert_last_daily"] = today_str
        return True

    state[STATE_KEY] = True
    state["p6_p7_post_v2_alert_last_daily"] = today_str
    return True


def maybe_alert_tp_sl_price_steps(state, now=None):
    """
    v10.6.25: alerta one-shot para implementar Steps 2+3 del plan TP/SL dinamico por precio.

    Dispara el 2026-05-10 o posterior (3 semanas tras el deploy de v10.6.25 el 2026-04-19).
    Da tiempo para acumular datos con el nuevo MIN_EDGE low-price buffer antes de afinar exits.

    Step 2: TP escalonado por precio de entrada (requiere entry_price en lifecycle).
    Step 3: SL absoluto en centavos en vez de %, para evitar cortes por ruido en posiciones baratas.

    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    FIRE_DATE = "2026-05-10"
    STATE_KEY = "tp_sl_price_steps_alert_sent"

    if state.get(STATE_KEY):
        return False
    if now.date().isoformat() < FIRE_DATE:
        return False

    today_str = now.date().isoformat()
    last_daily = state.get("tp_sl_price_steps_alert_last_daily", "")
    if last_daily == today_str:
        return False

    prompt_codex = (
        "Lee AGENTS.md, CONTEXTO.md ultimo bloque y OPERATIONS_PLAYBOOK.md.\n\n"
        "Tarea: Implementar Steps 2+3 del plan TP/SL dinamico por precio de entrada.\n"
        "Contexto: En sesion 210 (2026-04-19) Opus analizo la asimetria TP/SL en "
        "posiciones baratas. Step 1 (MIN_EDGE low-price buffer) se implemento en v10.6.25. "
        "Han pasado ~3 semanas: ahora hay datos para evaluar si Step 2 y 3 son necesarios.\n\n"
        "PRECONDICION CRITICA antes de implementar:\n"
        "1. Leer trade_lifecycle.json, filtrar trades opened_at >= 2026-04-19.\n"
        "2. Separar por bucket de precio entrada: [0.20-0.35], [0.35-0.65], [0.65-0.80].\n"
        "3. Calcular WR y PnL neto por bucket.\n"
        "4. Si el bucket [0.20-0.35] tiene WR>=50% y PnL>=0: Step 2 y 3 probablemente "
        "NO son necesarios. Reportar a Pablo y NO implementar.\n"
        "5. Si el bucket [0.20-0.35] sigue con WR<45% o PnL<-$0.50: implementar Steps 2+3.\n\n"
        "STEP 2 — TP escalonado por precio de entrada:\n"
        "- Anadir ENV vars: TP_LOW_PRICE_PCT=60, TP_MID_PRICE_PCT=40, TP_HIGH_PRICE_PCT=80.\n"
        "- Nota: LOW_PRICE_THRESHOLD (0.35) y HIGH_PRICE_THRESHOLD (0.65) ya existen o "
        "anadir HIGH_PRICE_THRESHOLD = float(os.getenv('HIGH_PRICE_THRESHOLD', '0.65')).\n"
        "- Logica: en manage_positions y en intra_cycle_sl_check, reemplazar la lookup "
        "actual de HIGH_CONVICTION_TP_PCT por una funcion effective_tp_pct(entry_price).\n"
        "- Para saber el entry_price hay que leerlo del lifecycle: "
        "entry_context.price (ya existe en track_trade BUY). Verificar que se guarda.\n"
        "- Si entry_price no esta en lifecycle: anadir 'entry_price' al track_trade BUY "
        "call en el path de compra (buscar track_trade(\"BUY\", ...)).\n"
        "- Funcion a anadir en bot.py (cerca de HIGH_CONVICTION_TP_PCT):\n"
        "  def effective_tp_pct(entry_price):\n"
        "      if entry_price is not None and entry_price < LOW_PRICE_THRESHOLD:\n"
        "          return TP_LOW_PRICE_PCT\n"
        "      if entry_price is not None and entry_price >= HIGH_PRICE_THRESHOLD:\n"
        "          return TP_HIGH_PRICE_PCT\n"
        "      return TP_MID_PRICE_PCT\n\n"
        "STEP 3 — SL absoluto en centavos (solo si Step 2 no basta o datos lo justifican):\n"
        "- ENV vars: SL_ABS_CENTS_LOW=0.08 (entry<0.35), SL_ABS_CENTS_HIGH=0.15 (entry>=0.35).\n"
        "- Funcion should_stop_loss_abs(entry_price, cur_price) -> bool.\n"
        "- Reemplazar 'if pct_pnl <= STOP_LOSS_PCT' en manage_positions e intra_cycle_sl_check.\n"
        "- Tambien requiere entry_price en lifecycle (igual que Step 2).\n"
        "- ADVERTENCIA: cambio mas grande. Implementar solo si Step 2 muestra datos positivos.\n\n"
        "GUARDRAILS:\n"
        "- NO tocar sigma, Kelly, MIN_EDGE global, NOAA, scheduler ni arquitectura core.\n"
        "- verify_before_deploy.py debe cerrar verde.\n"
        "- Commit separado por Step (v10.6.26 para Step 2, v10.6.27 para Step 3 si aplica).\n"
        "- Actualizar CONTEXTO.md, HISTORIAL_SESIONES.md y engram con resultado.\n"
        "- Si la precondicion dice NO implementar: igualmente actualizar CONTEXTO.md con "
        "el veredicto de los datos y marcar el plan como cerrado.\n\n"
        "Archivos clave:\n"
        "- bot.py:248-255 (LOW_PRICE_THRESHOLD, MIN_EDGE_LOW_PRICE_BUFFER_PP)\n"
        "- bot.py:352-355 (STOP_LOSS_PCT, TAKE_PROFIT_PCT, HIGH_CONVICTION_TP_PCT)\n"
        "- bot.py:13613-13633 (check SL/TP ciclo principal)\n"
        "- bot.py:13939-13955 (check SL/TP intra-cycle)\n"
        "- Engram: buscar 'Plan Steps 2+3 TP/SL dinamico' para contexto completo."
    )

    msg = (
        "\U0001f551 <b>Alerta Steps 2+3 \u2014 TP/SL din\u00e1mico por precio de entrada</b>\n\n"
        "Han pasado ~3 semanas desde el deploy de v10.6.25 (2026-04-19).\n"
        "Ya hay datos suficientes para evaluar si implementar TP/SL escalados por precio.\n\n"
        "<b>Precondici\u00f3n cr\u00edtica:</b>\n"
        "  Analizar WR+PnL por bucket de precio antes de tocar nada.\n"
        "  Si bucket [0.20-0.35] WR>=50% y PnL>=0: NO implementar, cerrar plan.\n\n"
        "<b>Tareas</b>:\n"
        "  Step 2 = TP escalonado (60%/40%/80%) por precio de entrada.\n"
        "  Step 3 = SL absoluto en centavos (solo si Step 2 no basta).\n\n"
        "<b>Prompt para Codex/Sonnet</b> (copiar y pegar):\n"
        f"<code>{prompt_codex}</code>"
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"tp_sl_price_steps alert: fallo al enviar Telegram ({e})")
        state["tp_sl_price_steps_alert_last_daily"] = today_str
        return True

    state[STATE_KEY] = True
    state["tp_sl_price_steps_alert_last_daily"] = today_str
    return True


def _parse_iso_utc(value):
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _post_intra_sl_cooldown_review_stats(started_at_iso):
    started_at = _parse_iso_utc(started_at_iso)
    if started_at is None:
        return {"closed": [], "n": 0}

    records = load_postmortem_data()
    closed = []
    for record in records:
        if record.get("status") != "closed":
            continue
        if record.get("close_action") not in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}:
            continue
        if record.get("pnl_cash") is None:
            continue
        closed_at = _parse_iso_utc(record.get("closed_at"))
        if closed_at is None or closed_at < started_at:
            continue
        closed.append(record)

    closed.sort(key=lambda r: str(r.get("closed_at") or ""))
    wins = sum(1 for r in closed if float(r.get("pnl_cash") or 0) > 0)
    pnl = round(sum(float(r.get("pnl_cash") or 0) for r in closed), 2)

    low = []
    mid_high = []
    for record in closed:
        try:
            entry_price = float(record.get("avg_entry_price"))
        except (TypeError, ValueError):
            entry_price = None
        if entry_price is not None and entry_price < LOW_PRICE_THRESHOLD:
            low.append(record)
        else:
            mid_high.append(record)

    def _bucket(rows):
        n = len(rows)
        w = sum(1 for r in rows if float(r.get("pnl_cash") or 0) > 0)
        total_pnl = round(sum(float(r.get("pnl_cash") or 0) for r in rows), 2)
        wr = round((w / n) * 100, 1) if n else 0.0
        return {"n": n, "wins": w, "wr": wr, "pnl": total_pnl}

    market_groups = {}
    for record in closed:
        token = str(record.get("token_id") or "").strip()
        key = "|".join([
            token or str(record.get("question") or record.get("city") or ""),
            str(record.get("date") or ""),
            str(record.get("side") or ""),
        ])
        market_groups.setdefault(key, []).append(record)

    repeated_groups = [rows for rows in market_groups.values() if len(rows) > 1]
    repeated_extra_closes = sum(len(rows) - 1 for rows in repeated_groups)
    repeated_labels = []
    for rows in sorted(repeated_groups, key=len, reverse=True)[:3]:
        sample = rows[0]
        repeated_labels.append(
            f"{sample.get('city', '?')} {sample.get('side', '?')} {sample.get('date', '?')} x{len(rows)}"
        )

    intra_sl_rows = [r for r in closed if r.get("close_reason") == "stop_loss_intra"]
    return {
        "closed": closed,
        "n": len(closed),
        "wins": wins,
        "wr": round((wins / len(closed)) * 100, 1) if closed else 0.0,
        "pnl": pnl,
        "low": _bucket(low),
        "mid_high": _bucket(mid_high),
        "intra_sl_count": len(intra_sl_rows),
        "repeated_extra_closes": repeated_extra_closes,
        "repeated_labels": repeated_labels,
    }


def maybe_run_post_intra_sl_cooldown_review(state, now=None):
    """
    v10.6.36: follow-up Telegram tras el fix de cooldown en stop_loss_intra.

    En el primer ciclo post-deploy se auto-ancla en alerts_state. Cuando hay
    POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED cierres nuevos, envia una lectura
    unica sobre WR/PnL, LOW bucket, SL intra y reentradas repetidas.
    """
    if not POST_INTRA_SL_COOLDOWN_REVIEW_ENABLED:
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    review = state.setdefault("post_intra_sl_cooldown_review", {})
    if review.get("sent_at"):
        return False

    if not review.get("started_at"):
        review["started_at"] = now.isoformat()
        review["min_closed"] = POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED
        return True

    stats = _post_intra_sl_cooldown_review_stats(review.get("started_at"))
    min_closed = int(review.get("min_closed") or POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED)
    if stats.get("n", 0) < min_closed:
        review["last_seen_closed"] = stats.get("n", 0)
        return True

    low = stats["low"]
    mid_high = stats["mid_high"]
    repeated = stats["repeated_extra_closes"]
    repeated_text = ", ".join(stats["repeated_labels"]) if stats["repeated_labels"] else "ninguna"
    if repeated == 0:
        readout = "El cooldown parece haber cortado las cascadas de reentrada post intra-SL."
    else:
        readout = "Aun hay cierres repetidos en el mismo mercado: revisar cooldown por token/mercado."

    msg = (
        f"\U0001f9ea <b>Review post-fix: cooldown intra-SL</b>\n\n"
        f"Muestra desde <code>{review.get('started_at')}</code>: <b>{stats['n']}</b> cierres.\n"
        f"WR: <b>{stats['wr']:.1f}%</b> ({stats['wins']}/{stats['n']}) | PnL: <b>${stats['pnl']:+.2f}</b>\n"
        f"SL intra: <b>{stats['intra_sl_count']}</b> | reentradas repetidas: <b>{repeated}</b>\n"
        f"Repetidos: <code>{repeated_text}</code>\n\n"
        f"<b>Bucket LOW &lt;35c</b>: WR {low['wr']:.1f}% ({low['wins']}/{low['n']}), PnL ${low['pnl']:+.2f}\n"
        f"<b>MID/HIGH</b>: WR {mid_high['wr']:.1f}% ({mid_high['wins']}/{mid_high['n']}), PnL ${mid_high['pnl']:+.2f}\n\n"
        f"<b>Lectura</b>: {readout}\n"
        f"<b>Siguiente paso</b>: si LOW sigue negativo, abrir investigacion especifica "
        f"<code>LOW at_or_above YES</code>; no tocar sigma global sin evidencia nueva."
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"post intra-SL cooldown review: fallo al enviar Telegram ({e})")
        review["last_send_error_at"] = now.isoformat()
        review["last_seen_closed"] = stats.get("n", 0)
        return True

    review["sent_at"] = now.isoformat()
    review["summary"] = {
        "n": stats["n"],
        "wins": stats["wins"],
        "wr": stats["wr"],
        "pnl": stats["pnl"],
        "low": low,
        "mid_high": mid_high,
        "intra_sl_count": stats["intra_sl_count"],
        "repeated_extra_closes": repeated,
    }
    return True


def _sl_intra_guard_resolved_outcome(token_id, lifecycle_records):
    """v10.6.40: localiza un trade cerrado en lifecycle por token_id y devuelve outcome real.

    Devuelve (resolved: bool, pnl_cash: float, close_reason: str) o (False, 0.0, "").
    """
    if not token_id:
        return False, 0.0, ""
    for r in lifecycle_records:
        if str(r.get("token_id") or "") != str(token_id):
            continue
        cc = r.get("close_context") or {}
        status = (r.get("status") or "").lower()
        if not (cc.get("close_reason") or status in ("closed", "resolved")):
            return False, 0.0, ""
        try:
            pnl_cash = float(cc.get("pnl_cash") or 0)
        except (ValueError, TypeError):
            pnl_cash = 0.0
        return True, pnl_cash, str(cc.get("close_reason") or status or "")
    return False, 0.0, ""


def maybe_run_sl_intra_guard_review(state, now=None):
    """
    v10.6.40: alerta one-shot del guard SL_intra (exact + days<=N).

    Dispara cuando hay >=SL_INTRA_GUARD_REVIEW_MIN_SKIPS skips registrados
    y todos los token_ids skipped tienen un cierre en trade_lifecycle.
    Compara PnL real vs hipotetico (si SL hubiera vendido al momento del skip).

    Idempotencia en alerts_state["sl_intra_guard_review"].
    Retorna True si state (alerts_state) fue mutado.
    """
    if not SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION:
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    review = state.setdefault("sl_intra_guard_review", {})
    if review.get("sent_at"):
        return False

    try:
        guard_state = load_sl_intra_guard_state()
    except Exception:
        return False

    skips = guard_state.get("skips", []) or []
    if len(skips) < SL_INTRA_GUARD_REVIEW_MIN_SKIPS:
        review["last_seen_skips"] = len(skips)
        if not review.get("started_at") and skips:
            review["started_at"] = skips[0].get("skipped_at") or now.isoformat()
        return True if not review.get("started_at") and skips else False

    # Cargar lifecycle para resolver outcomes reales
    try:
        lc = load_trade_lifecycle_data() or {}
    except Exception:
        return False
    records = lc.get("records") or []

    # Deduplicar por token_id (un trade puede tener varios skips antes de resolver)
    skips_by_token = {}
    for s in skips:
        tid = str(s.get("token_id") or "")
        if not tid:
            continue
        # Conservar el skip mas reciente por token (el que tiene mejor evidencia del momento previo al cierre)
        prev = skips_by_token.get(tid)
        if prev is None or (s.get("skipped_at", "") > prev.get("skipped_at", "")):
            skips_by_token[tid] = s

    resolved_skips = []
    pending_skips = []
    for tid, s in skips_by_token.items():
        ok, real_pnl, close_reason = _sl_intra_guard_resolved_outcome(tid, records)
        if ok:
            resolved_skips.append((s, real_pnl, close_reason))
        else:
            pending_skips.append(s)

    if len(resolved_skips) < SL_INTRA_GUARD_REVIEW_MIN_SKIPS:
        review["last_seen_skips"] = len(skips)
        review["last_seen_resolved"] = len(resolved_skips)
        if not review.get("started_at"):
            review["started_at"] = skips[0].get("skipped_at") or now.isoformat()
        return True

    # Calcular hipotetico vs real. Cohorts are LOG_ONLY analytics; they do not affect guard behavior.
    real_total = 0.0
    hypo_total = 0.0
    wins = 0
    losses = 0
    cohort_stats = {
        "zone_a": {"label": "Zona A / leverage-real", "n": 0, "wins": 0, "losses": 0, "real_total": 0.0, "hypo_total": 0.0},
        "zone_b": {"label": "Zona B / deep drawdown", "n": 0, "wins": 0, "losses": 0, "real_total": 0.0, "hypo_total": 0.0},
        "zone_c": {"label": "Zona C / inherited loss", "n": 0, "wins": 0, "losses": 0, "real_total": 0.0, "hypo_total": 0.0},
        "unknown": {"label": "Unknown / pct missing", "n": 0, "wins": 0, "losses": 0, "real_total": 0.0, "hypo_total": 0.0},
    }
    rows = []
    for s, real_pnl, close_reason in resolved_skips:
        # Hipotetico: si SL hubiera disparado, perdida = pct_pnl_at_skip% * current_value_at_skip
        # current_value_at_skip ~= shares * cur_price; con SELL_AGGRESSION 0.02 la perdida real seria un poco mayor
        # pero tomamos pct_pnl_at_skip directamente como aproximacion conservadora.
        try:
            current_value = float(s.get("current_value") or 0)
            pct_raw = s.get("pct_pnl_at_skip")
            pct = float(pct_raw) if pct_raw is not None and pct_raw != "" else 0.0
        except (ValueError, TypeError):
            current_value, pct = 0.0, 0.0
        cohort_fields = _sl_intra_guard_cohort_fields(s.get("pct_pnl_at_skip"))
        cohort = str(s.get("cohort") or cohort_fields.get("cohort") or "unknown")
        if cohort not in cohort_stats:
            cohort = "unknown"
        hypo_loss = current_value * (pct / 100.0)
        real_total += real_pnl
        hypo_total += hypo_loss
        if real_pnl > 0:
            wins += 1
        else:
            losses += 1
        cs = cohort_stats[cohort]
        cs["n"] += 1
        cs["real_total"] += real_pnl
        cs["hypo_total"] += hypo_loss
        if real_pnl > 0:
            cs["wins"] += 1
        else:
            cs["losses"] += 1
        rows.append({
            "city": s.get("city", "?"),
            "outcome": s.get("outcome", "?"),
            "pct_at_skip": pct,
            "real_pnl": real_pnl,
            "hypo_loss": hypo_loss,
            "close_reason": close_reason,
            "cohort": cohort,
        })

    delta = real_total - hypo_total
    for cs in cohort_stats.values():
        cs["delta"] = cs["real_total"] - cs["hypo_total"]

    zone_a = cohort_stats["zone_a"]
    n_zone_a_resolved = int(zone_a["n"])
    mixed_cohorts = sum(1 for cs in cohort_stats.values() if cs["n"] > 0) > 1
    if n_zone_a_resolved < 6:
        verdict = (
            "REVIEW PRELIMINAR — muestra insuficiente / mezclada. "
            "No cambiar guard/env vars sin revisión Opus."
        )
    elif zone_a["delta"] > 0:
        verdict = (
            f"Zona A <b>funcionando</b>: real ${zone_a['real_total']:+.2f} vs "
            f"hipotetico SL ${zone_a['hypo_total']:+.2f} = <b>${zone_a['delta']:+.2f}</b>."
        )
    elif zone_a["delta"] < 0:
        verdict = (
            f"Zona A <b>perjudicando</b>: real ${zone_a['real_total']:+.2f} vs "
            f"hipotetico SL ${zone_a['hypo_total']:+.2f} = <b>${zone_a['delta']:+.2f}</b>. "
            "Revisar con Opus antes de cambiar guard/env vars."
        )
    else:
        verdict = (
            f"Zona A <b>neutra</b>: real ${zone_a['real_total']:+.2f} = "
            f"hipotetico SL ${zone_a['hypo_total']:+.2f}."
        )

    cohort_summary_lines = []
    for cohort_key in ("zone_a", "zone_b", "zone_c", "unknown"):
        cs = cohort_stats[cohort_key]
        if cs["n"] <= 0:
            continue
        note = ""
        if cohort_key == "zone_a":
            note = " | base del veredicto operativo"
        elif cohort_key == "zone_b":
            note = " | evidencia separada"
        elif cohort_key == "zone_c":
            note = " | excluida del veredicto principal"
        cohort_summary_lines.append(
            f"- {cs['label']}: n={cs['n']} W={cs['wins']} L={cs['losses']} "
            f"real=${cs['real_total']:+.2f} hipo=${cs['hypo_total']:+.2f} "
            f"delta=${cs['delta']:+.2f}{note}"
        )
    cohort_summary_text = "\n".join(cohort_summary_lines) or "- Sin cohortes resueltas."

    rows_text_parts = []
    for cohort_key in ("zone_a", "zone_b", "zone_c", "unknown"):
        cohort_rows = [r for r in rows if r["cohort"] == cohort_key]
        if not cohort_rows:
            continue
        rows_text_parts.append(f"<b>{cohort_stats[cohort_key]['label']}</b>:")
        for r in cohort_rows[:6]:
            rows_text_parts.append(
                f"- {r['city']} {r['outcome']} pct@skip={r['pct_at_skip']:+.1f}% "
                f"real=${r['real_pnl']:+.2f} (hipo=${r['hypo_loss']:+.2f})"
            )
        if len(cohort_rows) > 6:
            rows_text_parts.append(f"- ... y {len(cohort_rows) - 6} mas")
    rows_text = "\n".join(rows_text_parts)

    mixed_note = ""
    if mixed_cohorts:
        mixed_note = (
            "\n\nMuestra mezclada: el delta global se muestra como contexto, "
            "pero no es veredicto accionable del guard."
        )

    msg = (
        f"\U0001f6e1️ <b>Review guard SL_intra v10.6.40</b>\n\n"
        f"Skips resueltos: <b>{len(resolved_skips)}</b> "
        f"(W={wins}, L={losses}) | Pendientes: <b>{len(pending_skips)}</b>\n"
        f"Resueltos PnL real: <b>${real_total:+.2f}</b>\n"
        f"Hipotetico si SL hubiera disparado: <b>${hypo_total:+.2f}</b>\n"
        f"Delta global: <b>${delta:+.2f}</b>{mixed_note}\n\n"
        f"<b>Veredicto</b>: {verdict}\n\n"
        f"<b>Resumen por cohortes</b>:\n{cohort_summary_text}\n\n"
        f"<b>Detalle</b>:\n{rows_text}\n\n"
        f"<i>Zona B se conserva como evidencia separada. Zona C queda excluida del veredicto principal.</i>"
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"sl_intra_guard review: fallo al enviar Telegram ({e})")
        review["last_send_error_at"] = now.isoformat()
        review["last_seen_resolved"] = len(resolved_skips)
        return True

    review["sent_at"] = now.isoformat()
    review["summary"] = {
        "resolved": len(resolved_skips),
        "pending": len(pending_skips),
        "wins": wins,
        "losses": losses,
        "real_total": round(real_total, 2),
        "hypo_total": round(hypo_total, 2),
        "delta": round(delta, 2),
        "n_zone_a_resolved": n_zone_a_resolved,
        "mixed_cohorts": mixed_cohorts,
        "cohorts": {
            key: {
                "n": int(cs["n"]),
                "wins": int(cs["wins"]),
                "losses": int(cs["losses"]),
                "real_total": round(cs["real_total"], 2),
                "hypo_total": round(cs["hypo_total"], 2),
                "delta": round(cs["delta"], 2),
            }
            for key, cs in cohort_stats.items()
        },
    }
    # Marcar tambien en guard_state (idempotencia cruzada)
    try:
        guard_state["review_alert_sent"] = True
        save_sl_intra_guard_state(guard_state)
    except Exception:
        pass
    return True


def _intra_reeval_trigger_outcome(trigger, lifecycle_records):
    token_id = str(trigger.get("token_id", "") or "").strip()
    if not token_id:
        return {
            "classification": "INSUFFICIENT_DATA",
            "reason": "missing_token_id",
        }

    trigger_dt = _parse_lifecycle_timestamp(trigger.get("ts"))
    trigger_price = _to_lifecycle_float(trigger.get("cur_price"))
    if trigger_dt is None or trigger_price is None:
        return {
            "classification": "INSUFFICIENT_DATA",
            "reason": "missing_trigger_time_or_price",
        }

    record = None
    for candidate in lifecycle_records or []:
        if str(candidate.get("token_id", "") or "").strip() == token_id:
            record = candidate
            break
    if not record:
        return {
            "classification": "INSUFFICIENT_DATA",
            "reason": "no_lifecycle_match",
        }

    for attempt in record.get("exit_attempts", []) or []:
        placed_dt = _parse_lifecycle_timestamp(attempt.get("placed_at"))
        if placed_dt is None or placed_dt < trigger_dt:
            continue
        reason = str(attempt.get("reason", "") or "")
        source = str(attempt.get("decision_source", "") or "")
        if reason in {"reeval", "reeval_intra"} and source in {"manage_positions", "intra_cycle_sl_check", ""}:
            return {
                "classification": "OVERLAP_ACTIVE_REEVAL",
                "reason": "real_reeval_exit_attempt_after_trigger",
                "close_price": _to_lifecycle_float(attempt.get("fill_price", attempt.get("limit_price"))),
                "closed_at": attempt.get("confirmed_at") or attempt.get("placed_at") or "",
            }

    close_ctx = record.get("close_context") or {}
    close_dt = _parse_lifecycle_timestamp(record.get("closed_at") or close_ctx.get("timestamp"))
    close_reason = str(close_ctx.get("close_reason", "") or "")
    if close_dt and close_dt >= trigger_dt and close_reason in {"reeval", "reeval_intra"}:
        return {
            "classification": "OVERLAP_ACTIVE_REEVAL",
            "reason": "real_reeval_close_after_trigger",
            "close_price": _to_lifecycle_float(close_ctx.get("close_price")),
            "closed_at": record.get("closed_at") or close_ctx.get("timestamp") or "",
        }

    status = str(record.get("status", "") or "")
    if status in {"open", "pending_exit", "exit_failed"}:
        return {
            "classification": "STILL_OPEN",
            "reason": f"lifecycle_status_{status or 'open'}",
        }

    if not close_dt or close_dt < trigger_dt:
        return {
            "classification": "INSUFFICIENT_DATA",
            "reason": "no_close_after_trigger",
        }

    close_price = _to_lifecycle_float(close_ctx.get("close_price"))
    close_action = str(close_ctx.get("close_action", "") or "")
    if close_price is None:
        if close_action == "RESOLVED_WIN":
            close_price = 1.0
        elif close_action == "LOSS_TOTAL":
            close_price = 0.0

    if close_price is None:
        return {
            "classification": "INSUFFICIENT_DATA",
            "reason": "missing_close_price",
            "closed_at": record.get("closed_at") or close_ctx.get("timestamp") or "",
        }

    delta_vs_trigger = round(close_price - trigger_price, 4)
    if delta_vs_trigger < 0:
        classification = "GOOD_SHADOW"
        reason = "later_exit_price_below_trigger"
    elif delta_vs_trigger > 0:
        classification = "BAD_SHADOW"
        reason = "later_exit_price_above_trigger"
    else:
        classification = "INSUFFICIENT_DATA"
        reason = "later_exit_price_equal_trigger"

    return {
        "classification": classification,
        "reason": reason,
        "trigger_price": trigger_price,
        "close_price": close_price,
        "delta_vs_trigger": delta_vs_trigger,
        "closed_at": record.get("closed_at") or close_ctx.get("timestamp") or "",
        "close_reason": close_reason,
        "close_action": close_action,
    }


def _annotate_intra_reeval_shadow_outcomes(reeval_state, lifecycle_data=None):
    shadow_log = reeval_state.setdefault("shadow_log", {})
    triggers = shadow_log.setdefault("triggers", [])
    if lifecycle_data is None:
        try:
            lifecycle_data = load_trade_lifecycle_data()
        except Exception:
            lifecycle_data = {}
    lifecycle_records = lifecycle_data.get("records", []) if isinstance(lifecycle_data, dict) else []

    counts = {
        "OVERLAP_ACTIVE_REEVAL": 0,
        "GOOD_SHADOW": 0,
        "BAD_SHADOW": 0,
        "STILL_OPEN": 0,
        "INSUFFICIENT_DATA": 0,
    }
    changed = False
    for trigger in triggers:
        if not isinstance(trigger, dict):
            counts["INSUFFICIENT_DATA"] += 1
            continue
        outcome = _intra_reeval_trigger_outcome(trigger, lifecycle_records)
        classification = outcome.get("classification", "INSUFFICIENT_DATA")
        counts[classification] = counts.get(classification, 0) + 1
        previous = trigger.get("outcome_review") or {}
        if previous != outcome:
            trigger["outcome_review"] = outcome
            changed = True

    summary = {
        "n_triggers": len(triggers),
        "n_classified": sum(
            counts.get(key, 0)
            for key in ["OVERLAP_ACTIVE_REEVAL", "GOOD_SHADOW", "BAD_SHADOW", "STILL_OPEN"]
        ),
        "n_overlap_active_reeval": counts.get("OVERLAP_ACTIVE_REEVAL", 0),
        "n_good_shadow": counts.get("GOOD_SHADOW", 0),
        "n_bad_shadow": counts.get("BAD_SHADOW", 0),
        "n_still_open": counts.get("STILL_OPEN", 0),
        "n_insufficient_data": counts.get("INSUFFICIENT_DATA", 0),
        "counts": counts,
        "observability_only": True,
    }
    if shadow_log.get("outcome_review_summary") != summary:
        shadow_log["outcome_review_summary"] = summary
        changed = True
    return summary, changed


def maybe_run_intra_reeval_review_alert(state, now=None):
    """
    v10.6.30: alerta one-shot de revision intra-reeval shadow.

    Dispara 7 dias despues del primer trigger shadow, una sola vez.
    Lee data/intra_reeval_state.json y envia resumen con prompt para sesion Opus/Sonnet.

    El campo de idempotencia esta en alerts_state: 'intra_reeval_review_alert_sent'.
    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    STATE_KEY = "intra_reeval_review_alert_sent"
    if state.get(STATE_KEY):
        return False

    # Leer estado shadow
    try:
        reeval_state = load_intra_reeval_state()
    except Exception:
        return False

    first_trigger_at = reeval_state.get("shadow_log", {}).get("first_trigger_at", "")
    if not first_trigger_at:
        return False  # Nunca hubo un trigger

    try:
        first_dt = datetime.fromisoformat(first_trigger_at.replace("Z", "+00:00"))
    except Exception:
        return False

    # Disparar solo 7 días después del primer trigger
    if (now - first_dt).total_seconds() < 7 * 24 * 3600:
        return False

    # Calcular métricas del shadow_log
    triggers = reeval_state.get("shadow_log", {}).get("triggers", [])
    n_triggers = len(triggers)
    if n_triggers == 0:
        return False

    # Top 3 ciudades
    from collections import Counter
    city_counts = Counter(t.get("city", "") for t in triggers)
    top3_cities = ", ".join(f"{c}({n})" for c, n in city_counts.most_common(3))

    # PnL stats
    pnl_list = [t.get("pnl_pct", 0) for t in triggers]
    pnl_avg = sum(pnl_list) / len(pnl_list) if pnl_list else 0
    pnl_sorted = sorted(pnl_list)
    mid = len(pnl_sorted) // 2
    pnl_median = pnl_sorted[mid] if len(pnl_sorted) % 2 == 1 else (pnl_sorted[mid - 1] + pnl_sorted[mid]) / 2

    # Edge stats
    edge_list = [t.get("fresh_edge_pct", 0) for t in triggers]
    edge_avg = sum(edge_list) / len(edge_list) if edge_list else 0

    # Distribución por banda de PnL
    in_positive_band = sum(1 for pnl in pnl_list if 20 <= pnl <= 40)
    in_drawdown = sum(1 for pnl in pnl_list if pnl < 0)

    outcome_summary, outcomes_changed = _annotate_intra_reeval_shadow_outcomes(reeval_state)
    if outcomes_changed:
        try:
            save_intra_reeval_state(reeval_state)
        except Exception:
            pass

    prompt_opus = (
        "Lee AGENTS.md y el bloque reciente de CONTEXTO.md.\n\n"
        "Tarea: Sesion de revision intra-reeval shadow — decidir si promover a modo real.\n\n"
        f"Datos del shadow log (ultimos 7 dias, n={n_triggers}):\n"
        f"- Top ciudades: {top3_cities}\n"
        f"- PnL% promedio al trigger: {pnl_avg:+.1f}%\n"
        f"- PnL% mediana al trigger: {pnl_median:+.1f}%\n"
        f"- fresh_edge_pct promedio: {edge_avg:+.1f}%\n"
        f"- Triggers con PnL en +20..+40%: {in_positive_band}\n"
        f"- Triggers con PnL negativo: {in_drawdown}\n"
        f"- Outcomes: clasificados={outcome_summary['n_classified']} | "
        f"overlap_active_reeval={outcome_summary['n_overlap_active_reeval']} | "
        f"good_shadow={outcome_summary['n_good_shadow']} | "
        f"bad_shadow={outcome_summary['n_bad_shadow']} | "
        f"still_open={outcome_summary['n_still_open']} | "
        f"insufficient={outcome_summary['n_insufficient_data']}\n\n"
        "Preguntas a responder:\n"
        "1. Es la mediana de PnL en triggers positiva? Si si -> shadow predice ventas prematuras; "
        "ajustar INTRA_REEVAL_PRICE_DRIFT_PP o INTRA_REEVAL_EDGE_THRESHOLD antes de promover.\n"
        "2. Las ciudades del top3 coinciden con el perfil de errores documentados en CONTEXTO.md?\n"
        "3. Promovemos a INTRA_REEVAL_SHADOW_MODE=0? Criterio sugerido: mediana PnL < 0 "
        "Y edge_avg < -5% Y n_triggers >= 10.\n\n"
        "Archivo a revisar: data/intra_reeval_state.json (triggers completos)\n"
        "Si se promueve a modo real: actualizar Railway ENV INTRA_REEVAL_SHADOW_MODE=0 "
        "y documentar en CONTEXTO.md + HISTORIAL_SESIONES.md."
    )

    msg = (
        f"\U0001f9ea <b>Review: intra-reeval shadow (7 dias)</b>\n\n"
        f"Han pasado 7 dias desde el primer trigger shadow de re-evaluacion intra-ciclo.\n\n"
        f"<b>Resumen shadow log ({n_triggers} triggers):</b>\n"
        f"  Top ciudades: {top3_cities}\n"
        f"  PnL% promedio: {pnl_avg:+.1f}% | mediana: {pnl_median:+.1f}%\n"
        f"  Edge promedio: {edge_avg:+.1f}%\n"
        f"  Triggers en +20..+40%: {in_positive_band} | en drawdown: {in_drawdown}\n\n"
        f"<b>Outcome tracking (LOG_ONLY):</b>\n"
        f"  Clasificados: {outcome_summary['n_classified']}/{outcome_summary['n_triggers']}\n"
        f"  OVERLAP_ACTIVE_REEVAL: {outcome_summary['n_overlap_active_reeval']}\n"
        f"  GOOD_SHADOW: {outcome_summary['n_good_shadow']} | BAD_SHADOW: {outcome_summary['n_bad_shadow']}\n"
        f"  STILL_OPEN: {outcome_summary['n_still_open']} | INSUFFICIENT_DATA: {outcome_summary['n_insufficient_data']}\n"
        f"  <i>Observability only: no ventas nuevas, no BUY/SELL/SKIP, no BANKROLL, no Fase C.</i>\n\n"
        f"<b>Prompt para Opus/Sonnet</b> (copiar y pegar):\n"
        f"<code>{prompt_opus}</code>"
    )

    try:
        send_telegram(msg)
    except Exception:
        pass

    state[STATE_KEY] = True
    return True


def maybe_alert_busan_expansion(state, now=None):
    """
    v10.6.26: alerta one-shot para incorporar Busan al universo del bot.

    Dispara el 2026-04-24 o posterior. Busan aparecio como TRADER_ONLY en
    7/7 corridas del cross-check (detectado 2026-04-20, corrida 8 de la serie
    reciente). Patron identico al batch Ankara/Madrid/Miami/Wellington (Sesion 200)
    y Jakarta/KL (Sesion 201).

    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    FIRE_DATE = "2026-04-24"
    STATE_KEY = "busan_expansion_alert_sent"

    if state.get(STATE_KEY):
        return False
    if now.date().isoformat() < FIRE_DATE:
        return False

    today_str = now.date().isoformat()
    last_daily = state.get("busan_expansion_alert_last_daily", "")
    if last_daily == today_str:
        return False

    prompt_codex = (
        "Lee AGENTS.md, CONTEXTO.md ultimo bloque y OPERATIONS_PLAYBOOK.md.\n\n"
        "Tarea: Incorporar Busan al universo del bot (NOAA + whitelist).\n\n"
        "Contexto: Busan aparecio como TRADER_ONLY en 7/7 corridas del cross-check "
        "traders vs bot (detectado 2026-04-20). Mismo patron que el batch "
        "Ankara/Madrid/Miami/Wellington (Sesion 200) y Jakarta/KL (Sesion 201). "
        "El flujo validado es el mismo: verificar fuente Polymarket, verificar NOAA, "
        "patch bot.py, update Railway.\n\n"
        "PASO 1 — Verificar fuente de resolucion Polymarket:\n"
        "1. Buscar en Wunderground que estacion usa Polymarket para Busan.\n"
        "   Candidato probable: Gimhae International (ICAO=RKPK, lat=35.1795, lon=128.9380).\n"
        "   URL de referencia: https://www.wunderground.com/history/daily/kr/gimhae/RKPK\n"
        "2. Confirmar que la estacion WU coincide con la que Polymarket cita "
        "en el detalle del mercado (mismo ciudad/aeropuerto).\n\n"
        "PASO 2 — Verificar NOAA:\n"
        "1. Buscar RKPK en isd-history.csv (campo ICAO -> USAF -> ISD station id).\n"
        "2. Verificar si el feed 2026 tiene datos: "
        "https://www.ncei.noaa.gov/data/global-hourly/access/2026/<ISD_ID>.csv\n"
        "3. Si el CSV devuelve 404 o esta vacio -> ciudad entra como ICAO-only "
        "(mismo patron que Singapore, Jakarta, KL). No bloquea el patch.\n"
        "4. Buscar tambien GHCND station para Busan en ghcnd-inventory.txt si aplica.\n\n"
        "PASO 3 — Patch bot.py:\n"
        "Anadir Busan a los siguientes diccionarios (con coordenadas verificadas en paso 1):\n"
        "- RESOLUTION_STATIONS: {lat, lon, name}\n"
        "- RESOLUTION_ICAO: {icao, noaa_station_id (si hay), noaa_daily_station_id (si hay)}\n"
        "- CITY_TIMEZONES: 'Asia/Seoul'\n"
        "- OBSERVED_AUDIT_CITIES: incluir en la lista\n"
        "- default de QUALITY_TRADER_CITIES_WHITELIST: agregar ',Busan' al final\n"
        "Ampliar verify_before_deploy.py con tests de Busan en cada estructura.\n\n"
        "PASO 4 — Railway:\n"
        "Actualizar env var QUALITY_TRADER_CITIES_WHITELIST agregando ',Busan' al final.\n\n"
        "GUARDRAILS:\n"
        "- NO tocar filtros de precio, MIN_EDGE global, Kelly, sigma, exits, NOAA fetcher.\n"
        "- NO anadir ciudad sin RESOLUTION_STATIONS verificado (evitar Seoul mismatch - Sesion 185).\n"
        "- Si NOAA feed no disponible: ICAO-only esta bien, no bloquea el patch.\n"
        "- verify_before_deploy.py debe cerrar verde antes de commit.\n\n"
        "Salida esperada:\n"
        "- Patch en bot.py (v10.6.27 o siguiente disponible).\n"
        "- Railway env actualizada.\n"
        "- Actualizar CONTEXTO.md, HISTORIAL_SESIONES.md y engram."
    )

    msg = (
        "\U0001f1f0\U0001f1f7 <b>Alerta Busan \u2014 Incorporar al universo del bot</b>\n\n"
        "Busan apareci\u00f3 como TRADER_ONLY en 7/7 corridas del cross-check "
        "(detectado 2026-04-20). Han pasado 4 d\u00edas de observaci\u00f3n.\n\n"
        "<b>Patr\u00f3n</b>: id\u00e9ntico a Ankara/Madrid/Jakarta/KL (batches previos).\n\n"
        "<b>Tareas</b>:\n"
        "  1. Verificar fuente Polymarket (Wunderground RKPK).\n"
        "  2. Verificar NOAA ISD station.\n"
        "  3. Patch bot.py + Railway whitelist.\n\n"
        "<b>Prompt para Codex</b> (copiar y pegar):\n"
        f"<code>{prompt_codex}</code>"
    )

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"busan expansion alert: fallo al enviar Telegram ({e})")
        state["busan_expansion_alert_last_daily"] = today_str
        return True

    state[STATE_KEY] = True
    state["busan_expansion_alert_last_daily"] = today_str
    return True


# =============================================================
# v10.6.14 — Canary → Active automation (Módulos 1, 2, 3)
# =============================================================

def maybe_evaluate_slot_monetization(state, now=None):
    """
    Evalúa automáticamente la monetización reciente de 04h y 23h usando scan.slot_metrics.
    Envía una alerta operativa pensada para accionar en Codex, no solo para documentar.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if state.get("slot_monetization_last_date") == today:
        return False

    try:
        records = load_cycle_history()
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"slot monetization: no pude cargar cycles_history ({e})")
        return False

    slot_04 = evaluate_slot_monetization(records, 4, min_cycles=3)
    slot_23_enabled = 23 in SCHEDULE_HOURS_UTC
    slot_23 = evaluate_slot_monetization(records, 23, min_cycles=3)
    signature_payload = {
        "04": {
            "decision": slot_04.get("decision"),
            "same_day_selected": slot_04.get("same_day_selected"),
            "same_day_buys": slot_04.get("same_day_buys"),
            "top_execution": _top_reason(slot_04.get("execution_reject_reasons")),
            "top_same_day": _top_reason(slot_04.get("same_day_reject_reasons")),
        },
    }
    if slot_23_enabled and isinstance(slot_23, dict):
        signature_payload["23"] = {
            "decision": slot_23.get("decision"),
            "edges": slot_23.get("edges"),
            "buys": slot_23.get("buys"),
            "top_same_day": _top_reason(slot_23.get("same_day_reject_reasons")),
        }
    signature = json.dumps(signature_payload, sort_keys=True, ensure_ascii=False)

    benign_execution_reasons = {"buy_min_size", "buy_min_notional"}
    execution_reasons_04 = slot_04.get("execution_reject_reasons") if isinstance(slot_04, dict) else {}
    if not isinstance(execution_reasons_04, dict):
        execution_reasons_04 = {}
    relevant_execution_04 = {
        reason: count
        for reason, count in execution_reasons_04.items()
        if reason not in benign_execution_reasons and int(count or 0) > 0
    }
    benign_execution_total_04 = sum(
        int(count or 0)
        for reason, count in execution_reasons_04.items()
        if reason in benign_execution_reasons
    )
    same_day_buys_04 = int(slot_04.get("same_day_buys", 0) or 0)
    healthy_validated_04 = (
        slot_04.get("decision") == "validated"
        and slot_04.get("status") == "keep"
        and same_day_buys_04 > 0
        and float(slot_04.get("buy_rate", 0.0) or 0.0) > 0.0
        and float(slot_04.get("same_day_buy_rate", 0.0) or 0.0) > 0.0
        and not relevant_execution_04
        and benign_execution_total_04 <= max(1, same_day_buys_04)
    )
    slot_04_actionable = not healthy_validated_04
    slot_23_actionable = (
        slot_23_enabled
        and isinstance(slot_23, dict)
        and slot_23.get("decision") in {"disable_candidate", "low_value", "weak_signal", "observe_post_edge", "not_validated_yet"}
    )
    should_send = (
        signature != state.get("slot_monetization_last_signature")
        and (slot_04_actionable or slot_23_actionable)
    )

    if should_send:
        lines = [
            "🎯 <b>Slot monetization review</b>",
            f"Ventana leída: 04h {slot_04.get('cycles', 0)} ciclos | 23h {slot_23.get('cycles', 0)} ciclos",
            "",
            f"<b>04h UTC</b> -> <code>{slot_04.get('decision')}</code> / <code>{slot_04.get('status')}</code>",
            f"• same_day_candidates={slot_04.get('same_day_candidates', 0)} | same_day_edges={slot_04.get('same_day_edges', 0)} | same_day_selected={slot_04.get('same_day_selected', 0)} | same_day_buys={slot_04.get('same_day_buys', 0)}",
            f"• buy_rate={slot_04.get('buy_rate', 0.0):.2%} | same_day_buy_rate={slot_04.get('same_day_buy_rate', 0.0):.2%}",
            f"• resumen: {slot_04.get('summary', 'n/d')}",
            f"• reject_reasons: {_format_reason_summary(slot_04.get('same_day_reject_reasons'))}",
            f"• execution_reject_reasons: {_format_reason_summary(slot_04.get('execution_reject_reasons'))}",
            "",
            f"<b>23h UTC</b> -> <code>{slot_23.get('decision')}</code> / <code>{slot_23.get('status')}</code>",
            f"• edges={slot_23.get('edges', 0)} | selected={slot_23.get('selected', 0)} | buys={slot_23.get('buys', 0)} | buy_rate={slot_23.get('buy_rate', 0.0):.2%}",
            f"• resumen: {slot_23.get('summary', 'n/d')}",
            f"• reject_reasons: {_format_reason_summary(slot_23.get('same_day_reject_reasons'))}",
            "",
            "<b>Acción sugerida para Codex</b>",
        ]
        if not slot_23_enabled:
            lines = lines[:10] + lines[-1:]
            if len(lines) > 1:
                lines[1] = f"Ventana leída: 04h {slot_04.get('cycles', 0)} ciclos"
        if slot_04.get("decision") == "not_validated_yet":
            dominant = _top_reason(slot_04.get("execution_reject_reasons")) or _top_reason(slot_04.get("same_day_reject_reasons")) or "unknown"
            lines.append(f"• 04h sigue en <code>keep</code>; revisar si el cuello dominante <code>{dominant}</code> amerita patch operativo.")
        elif slot_04.get("decision") == "validated":
            lines.append("• 04h ya valida monetización; mantenerlo y vigilar estabilidad.")
        else:
            lines.append("• 04h todavía no valida monetización; revisar si falta muestra o si discovery sigue débil.")

        if slot_23_enabled:
            if slot_23.get("decision") == "disable_candidate":
                lines.append("• 23h es candidato a apagado reversible: <code>SCHEDULE_DISABLED_HOURS_UTC=23</code>.")
            else:
                lines.append("• 23h todavía no se apaga automáticamente; seguir observando con slot_metrics.")

        lines.append("• Esta alerta está diseñada para abrir sesión Codex con salida accionable, no solo documental.")
        send_telegram("\n".join(lines))
    elif signature != state.get("slot_monetization_last_signature") and healthy_validated_04:
        logger = globals().get("log")
        if logger:
            logger.info("slot monetization review: NO_ACTION 04h validated/keep healthy; Telegram suppressed")

    state["slot_monetization_last_date"] = today
    state["slot_monetization_last_signature"] = signature
    return True


def _detect_atlanta_inconsistency(record):
    """True si el record tiene el patrón inconsistente Atlanta (LOSS_TOTAL + RESOLVED_WIN positivo en
    timeline + post_exit_analysis confirmando win). Ver docs/atlanta-lifecycle-inconsistency-2026-04-12.md."""
    if not isinstance(record, dict):
        return False
    close_ctx = record.get("close_context") or {}
    if close_ctx.get("close_action") != "LOSS_TOTAL":
        return False
    timeline = record.get("timeline") or []
    has_resolved_win_positive = any(
        isinstance(e, dict)
        and e.get("action") == "RESOLVED_WIN"
        and float(e.get("pnl_cash") or 0) > 0
        for e in timeline
    )
    if not has_resolved_win_positive:
        return False
    post_exit = record.get("post_exit_analysis") or {}
    return bool(
        post_exit.get("market_seen_after_close") is True
        and float(post_exit.get("max_price_after_close") or 0) >= 0.95
    )


def notify_active_candidates(state):
    """
    v10.6.14 (Módulo 1): evalúa ciudades en auto_canary_cities y detecta cuáles cumplen
    los criterios v1 para ser promovidas manualmente a Active.

    Umbrales v1 CONGELADOS (sesión 172 Opus):
    - canary_trades >= 5, WR >= 60%, PnL >= +$1.00, days_since_promotion >= 7

    Envía Telegram cuando:
    - Nueva candidata detectada (primera vez que cumple criterios).
    - Candidata sigue cumpliendo y han pasado >= 22h desde último aviso (recordatorio).

    Revoca (envía aviso + borra entry) cuando:
    - Candidata ya no cumple criterios.

    Silencia cuando:
    - Pablo aplicó el cambio: la ciudad aparece en ACTIVE_TRADING_CITIES en runtime.

    Retorna True si mutó state (caller persiste).
    """
    MIN_CANARY_TRADES = 5
    MIN_WIN_RATE = 60.0
    MIN_PNL = 1.00
    MIN_DAYS = 7
    RATE_LIMIT_HOURS = 22

    try:
        policy_state = load_city_policy_state()
        lifecycle_data = load_trade_lifecycle_data()
        lifecycle_records = lifecycle_data.get("records", []) if isinstance(lifecycle_data, dict) else []
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"notify active candidates: no pude cargar datos ({e})")
        return False

    auto_canary = policy_state.get("auto_canary_cities", {})
    if not isinstance(auto_canary, dict):
        auto_canary = {}
    transition_history = policy_state.get("transition_history", [])
    if not isinstance(transition_history, list):
        transition_history = []
    auto_blocked = policy_state.get("auto_blocked_cities", {})
    if not isinstance(auto_blocked, dict):
        auto_blocked = {}

    active_env = {
        c.strip() for c in os.getenv("ACTIVE_TRADING_CITIES", "").split(",")
        if c.strip() and c.strip().upper() != "NONE"
    }

    notified = state.setdefault("active_candidate_notified", {})
    if not isinstance(notified, dict):
        notified = {}
        state["active_candidate_notified"] = notified

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    changed = False

    # Silencing: user already activated the city → clean state silently
    for city in list(notified.keys()):
        if city in active_env:
            notified.pop(city, None)
            changed = True

    # Evaluate each canary city against v1 criteria
    current_candidates = {}
    for city, meta in auto_canary.items():
        if not city or not isinstance(meta, dict):
            continue
        if city in active_env:
            continue
        if city in auto_blocked:
            continue

        promoted_at_raw = meta.get("promoted_at", "")
        if not promoted_at_raw:
            continue
        try:
            promoted_at = datetime.fromisoformat(promoted_at_raw)
        except Exception:
            continue

        # Trades canary post-promoción (solo cerrados)
        city_records = [
            r for r in lifecycle_records
            if isinstance(r, dict)
            and r.get("city") == city
            and r.get("closed_at")
            and str(r.get("opened_at", "")) >= promoted_at_raw
        ]

        n_trades = len(city_records)
        if n_trades < MIN_CANARY_TRADES:
            continue

        # Bloque 2: integrity — Atlanta inconsistency pattern
        if any(_detect_atlanta_inconsistency(r) for r in city_records):
            logger = globals().get("log")
            if logger:
                logger.info(f"notify active candidates: {city} omitida por inconsistencia Atlanta en lifecycle")
            continue
        # All trades must have analysis_ready
        if not all(bool(r.get("integrity", {}).get("analysis_ready", False)) for r in city_records):
            continue

        n_wins = sum(1 for r in city_records if float(r.get("pnl_cash") or 0) > 0)
        n_losses = n_trades - n_wins
        pnl = sum(float(r.get("pnl_cash") or 0) for r in city_records)
        win_rate = round(n_wins / n_trades * 100, 1)
        best_edge = float(meta.get("best_edge_pct") or 0)
        days_since_promotion = (now - promoted_at).days

        # Bloque 1
        if win_rate < MIN_WIN_RATE:
            continue
        if pnl < MIN_PNL:
            continue
        if days_since_promotion < MIN_DAYS:
            continue

        # Bloque 4: anti-flapping — no demoted to shadow in last 14 days
        cutoff_14d = (now - timedelta(days=14)).isoformat()
        recently_demoted = any(
            isinstance(h, dict)
            and h.get("city") == city
            and h.get("to") == "shadow"
            and str(h.get("at", "")) >= cutoff_14d
            for h in transition_history
        )
        if recently_demoted:
            continue

        current_candidates[city] = {
            "trades": n_trades,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": win_rate,
            "pnl": round(pnl, 2),
            "best_edge": best_edge,
            "days": days_since_promotion,
            "promoted_at_date": promoted_at.strftime("%Y-%m-%d"),
        }

    current_active_cities_str = ",".join(sorted(active_env)) if active_env else ""

    for city, stats in current_candidates.items():
        city_env_str = (current_active_cities_str + "," + city) if current_active_cities_str else city
        prev = notified.get(city)

        if prev is None:
            # Nueva candidata → alerta
            try:
                send_telegram(
                    f"\U0001f680 <b>Ciudad lista para Active</b>\n"
                    f"{city} cumple todos los criterios canary \u2192 active.\n\n"
                    f"Evidencia canary (desde {stats['promoted_at_date']}):\n"
                    f"\u2022 Trades: {stats['trades']} ({stats['wins']}W / {stats['losses']}L)"
                    f" \u2014 WR {stats['win_rate']:.1f}%\n"
                    f"\u2022 PnL acumulado: ${stats['pnl']:+.2f}\n"
                    f"\u2022 Mejor edge: {stats['best_edge']:.1f}%\n"
                    f"\u2022 D\u00edas en canary: {stats['days']}\n"
                    f"\u2022 Integridad de datos: OK \u2713\n\n"
                    f"Para activar en Railway aplicar exactamente:\n"
                    f"<code>ACTIVE_TRADING_CITIES={city_env_str}</code>\n\n"
                    f"Mientras no apliques el cambio, este aviso se repetir\u00e1 cada 24h.\n"
                    f"Si los criterios dejan de cumplirse, te llegar\u00e1 aviso de revocaci\u00f3n."
                )
            except Exception as e:
                logger = globals().get("log")
                if logger:
                    logger.warning(f"notify active candidates: fallo al enviar Telegram ({e})")
                continue
            notified[city] = {
                "first_notified_at": now_iso,
                "last_notified_at": now_iso,
                "trades": stats["trades"],
                "win_rate": stats["win_rate"],
                "pnl": stats["pnl"],
                "days_since_promotion": stats["days"],
            }
            changed = True
        else:
            # Candidata existente → recordatorio si pasaron >= 22h
            last_notified_raw = prev.get("last_notified_at", now_iso)
            try:
                last_notified = datetime.fromisoformat(last_notified_raw)
            except Exception:
                last_notified = now
            hours_since = (now - last_notified).total_seconds() / 3600
            if hours_since < RATE_LIMIT_HOURS:
                continue
            try:
                send_telegram(
                    f"\U0001f514 <b>Recordatorio \u2014 {city} sigue lista para Active</b>\n"
                    f"Han pasado 24h desde el primer aviso y los criterios siguen cumpli\u00e9ndose.\n\n"
                    f"Evidencia actualizada:\n"
                    f"\u2022 Trades: {stats['trades']} \u2014 WR {stats['win_rate']:.1f}%"
                    f" \u2014 PnL ${stats['pnl']:+.2f}\n\n"
                    f"Env var para aplicar:\n"
                    f"<code>ACTIVE_TRADING_CITIES={city_env_str}</code>"
                )
            except Exception as e:
                logger = globals().get("log")
                if logger:
                    logger.warning(f"notify active candidates: fallo al enviar recordatorio ({e})")
                continue
            notified[city]["last_notified_at"] = now_iso
            notified[city]["trades"] = stats["trades"]
            notified[city]["win_rate"] = stats["win_rate"]
            notified[city]["pnl"] = stats["pnl"]
            changed = True

    # Revocación: ciudades que ya no cumplen criterios
    for city in list(notified.keys()):
        if city not in current_candidates and city not in active_env:
            meta = auto_canary.get(city, {})
            promoted_at_raw = meta.get("promoted_at", "") if isinstance(meta, dict) else ""
            city_records = [
                r for r in lifecycle_records
                if isinstance(r, dict)
                and r.get("city") == city
                and r.get("closed_at")
                and str(r.get("opened_at", "")) >= promoted_at_raw
            ] if promoted_at_raw else []
            n_trades = len(city_records)
            n_wins = sum(1 for r in city_records if float(r.get("pnl_cash") or 0) > 0)
            pnl = round(sum(float(r.get("pnl_cash") or 0) for r in city_records), 2)
            win_rate = round(n_wins / n_trades * 100, 1) if n_trades > 0 else 0.0
            try:
                send_telegram(
                    f"\U0001f6ab <b>{city} ya no cumple criterios para Active</b>\n"
                    f"Raz\u00f3n: criterios dejaron de cumplirse\n"
                    f"(WR ca\u00edy\u00f3 a {win_rate:.1f}% / PnL ${pnl:+.2f} / n={n_trades})\n\n"
                    f"La candidatura queda revocada. Si vuelve a cumplir, recibir\u00e1s nueva alerta."
                )
            except Exception as e:
                logger = globals().get("log")
                if logger:
                    logger.warning(f"notify active candidates: fallo al enviar revocaci\u00f3n ({e})")
            notified.pop(city, None)
            changed = True

    return changed


def maybe_run_active_degradation(state):
    """
    v10.6.14 (Módulo 2): degrada ciudades Active→Canary automáticamente si la performance
    cae bajo umbral. Corre en cada ciclo de observability.

    Criterios v1 CONGELADOS (sesión 172 Opus):
    - active_trades >= 5 AND (WR <= 45% OR PnL <= -1.50)
    - Anti-flapping: no degradada en últimos 14 días.

    Usa overlay auto_canary_from_active en city_policy_state para que
    get_effective_city_mode() trate la ciudad como canary aunque esté en ACTIVE_TRADING_CITIES.

    Retorna True si state (alerts_state) fue mutado.
    """
    active_env = {
        c.strip() for c in os.getenv("ACTIVE_TRADING_CITIES", "").split(",")
        if c.strip() and c.strip().upper() != "NONE"
    }
    if not active_env:
        return False

    try:
        policy_state = load_city_policy_state()
        lifecycle_data = load_trade_lifecycle_data()
        lifecycle_records = lifecycle_data.get("records", []) if isinstance(lifecycle_data, dict) else []
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"active degradation: no pude cargar datos ({e})")
        return False

    monitoring = policy_state.get("active_city_monitoring", {})
    if not isinstance(monitoring, dict):
        monitoring = {}
    policy_state["active_city_monitoring"] = monitoring

    auto_canary_from_active = policy_state.get("auto_canary_from_active", {})
    if not isinstance(auto_canary_from_active, dict):
        auto_canary_from_active = {}
    policy_state["auto_canary_from_active"] = auto_canary_from_active

    transition_history = policy_state.get("transition_history", [])
    if not isinstance(transition_history, list):
        transition_history = []

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    changed_alerts = False
    changed_policy = False

    for city in list(active_env):
        if city in auto_canary_from_active:
            continue

        # Registrar monitoreo si primera vez que vemos esta ciudad en active
        if city not in monitoring:
            monitoring[city] = {"started_at": now_iso}
            changed_policy = True

        started_at_raw = monitoring[city].get("started_at", now_iso)

        # Trades activos cerrados desde el inicio de monitoreo
        city_records = [
            r for r in lifecycle_records
            if isinstance(r, dict)
            and r.get("city") == city
            and r.get("closed_at")
            and str(r.get("opened_at", "")) >= started_at_raw
        ]

        n_trades = len(city_records)
        if n_trades < 5:
            continue

        # Anti-flapping: no degradada a canary en últimos 14 días
        cutoff_14d = (now - timedelta(days=14)).isoformat()
        recently_degraded = any(
            isinstance(h, dict)
            and h.get("city") == city
            and h.get("to") in ("active_to_canary",)
            and str(h.get("at", "")) >= cutoff_14d
            for h in transition_history
        )
        if recently_degraded:
            continue

        n_wins = sum(1 for r in city_records if float(r.get("pnl_cash") or 0) > 0)
        pnl = sum(float(r.get("pnl_cash") or 0) for r in city_records)
        win_rate = round(n_wins / n_trades * 100, 1) if n_trades > 0 else 0.0

        if win_rate <= 45.0:
            reason_short = f"WR {win_rate:.1f}% \u2264 45%"
        elif pnl <= -1.50:
            reason_short = f"PnL ${pnl:+.2f} \u2264 -$1.50"
        else:
            continue

        # Construir nuevo env var copiable
        new_active = sorted(active_env - {city})
        new_cities_str = ",".join(new_active) if new_active else "NONE"

        # Añadir overlay
        auto_canary_from_active[city] = {
            "degraded_at": now_iso,
            "reason": reason_short,
            "metrics": {
                "trades": n_trades,
                "wins": n_wins,
                "win_rate": win_rate,
                "pnl": round(pnl, 2),
            },
        }

        # Registrar en transition_history
        transition_history.append({
            "at": now_iso,
            "city": city,
            "from": "active",
            "to": "active_to_canary",
            "action": "auto_degrade_active",
            "reason": reason_short,
        })
        policy_state["transition_history"] = transition_history
        changed_policy = True

        try:
            send_telegram(
                f"\u26a0\ufe0f <b>Ciudad degradada Active \u2192 Canary</b>\n"
                f"{city} ha sido degradada autom\u00e1ticamente por performance pobre.\n\n"
                f"Evidencia (desde activaci\u00f3n):\n"
                f"\u2022 Trades: {n_trades} \u2014 WR {win_rate:.1f}% \u2014 PnL ${pnl:+.2f}\n"
                f"\u2022 Raz\u00f3n: {reason_short}\n\n"
                f"El bot ya operaba {city} con sizing active. A partir de este ciclo vuelve a "
                f"sizing canary (posici\u00f3n peque\u00f1a).\n\n"
                f"Para limpiar el env var en Railway:\n"
                f"<code>ACTIVE_TRADING_CITIES={new_cities_str}</code>\n"
                f"(opcional \u2014 el overlay runtime ya la excluye)."
            )
        except Exception as e:
            logger = globals().get("log")
            if logger:
                logger.warning(f"active degradation: fallo al enviar Telegram ({e})")

        changed_alerts = True

    if changed_policy:
        try:
            policy_state["updated_at"] = now_iso
            save_city_policy_state(policy_state)
        except Exception as e:
            logger = globals().get("log")
            if logger:
                logger.warning(f"active degradation: fallo al guardar policy_state ({e})")

    return changed_alerts


def maybe_alert_v2_trigger(state, now=None):
    """
    v10.6.14 (Módulo 3): alarma one-shot cuando las condiciones para habilitar v2 se cumplen.
    Bloques 3+5 (corroboración externa + gate global post-recalibración) están DEFERIDOS a v2.
    Este módulo solo avisa cuándo es momento de arrancarlos.

    Precondiciones:
    1. RECALIBRATION_PHASE2_CLOSED=true (env var) o data/recalibration_phase2_status.json con status=closed
    2. Al menos 1 ciudad en ACTIVE_TRADING_CITIES (distinto de NONE)
    3. data/runtime_import/signals.json fresco (< 48h)

    One-shot: idempotencia via state["v2_trigger_notified"].
    Retorna True si state fue mutado.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    # Verificar solo una vez por día
    if state.get("v2_trigger_last_check") == today:
        return False

    # Idempotencia
    if state.get("v2_trigger_notified"):
        state["v2_trigger_last_check"] = today
        return True

    # Precondición 1: recalibración Phase 2 cerrada
    phase2_closed = str(os.getenv("RECALIBRATION_PHASE2_CLOSED", "")).strip().lower() == "true"
    if not phase2_closed:
        phase2_file = _data_path("recalibration_phase2_status.json")
        if os.path.exists(phase2_file):
            try:
                with open(phase2_file, "r", encoding="utf-8") as f:
                    phase2_data = json.load(f)
                phase2_closed = isinstance(phase2_data, dict) and phase2_data.get("status") == "closed"
            except Exception:
                pass
    if not phase2_closed:
        state["v2_trigger_last_check"] = today
        return True

    # Precondición 2: al menos una ciudad en Active
    active_env = {
        c.strip() for c in os.getenv("ACTIVE_TRADING_CITIES", "").split(",")
        if c.strip() and c.strip().upper() != "NONE"
    }
    if not active_env:
        state["v2_trigger_last_check"] = today
        return True

    # Precondición 3: signals.json fresco (< 48h)
    if not os.path.exists(SIGNALS_FILE):
        state["v2_trigger_last_check"] = today
        return True
    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8-sig") as f:
            sig_data = json.load(f)
        generated_raw = sig_data.get("generated") or sig_data.get("updated_at", "")
        generated = datetime.fromisoformat(generated_raw)
        age_hours = (now - generated).total_seconds() / 3600
        if age_hours > 48:
            state["v2_trigger_last_check"] = today
            return True
    except Exception:
        state["v2_trigger_last_check"] = today
        return True

    # Todas las precondiciones cumplidas — alerta one-shot
    n_cities_active = len(active_env)
    try:
        send_telegram(
            f"\U0001f3af <b>Condiciones para v2 cumplidas</b>\n\n"
            f"Canary\u2192Active v1 ha estado corriendo con {n_cities_active} ciudad(es) en Active "
            f"y la recalibraci\u00f3n Phase 2 est\u00e1 cerrada. Es momento de a\u00f1adir los Bloques 3+5 "
            f"(corroboraci\u00f3n externa + gate global post-recalibraci\u00f3n) al gate de promoci\u00f3n.\n\n"
            f"Para arrancar la sesi\u00f3n limpia con Opus, copiar exactamente:\n\n"
            f"<code>Leer docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md \u00a76 "
            f"(Bloques 3+5 v2). Extender notify_active_candidates con: (Bloque 3) corroboraci\u00f3n "
            f"trader_signals o shadow_edge reciente, (Bloque 5) gate global WR sistema >= 50% "
            f"\u00faltimos 30 d\u00edas. No tocar criterios v1 ya en producci\u00f3n. "
            f"Verificar con verify_before_deploy.py. Cierre: commit + push + deploy Railway.</code>\n\n"
            f"Este aviso es one-shot. No se repetir\u00e1."
        )
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"v2 trigger alarm: fallo al enviar Telegram ({e})")
        state["v2_trigger_last_check"] = today
        return True

    state["v2_trigger_notified"] = {"at": now.isoformat()}
    state["v2_trigger_last_check"] = today
    return True


def _condition_monitor_stats(today=None):
    """
    v10.6.16: Calcula WR de trades con condition exact/range desde apertura canary (2026-04-14).
    Lee trade_lifecycle.json; retorna dict con n_closed, n_wins, wr, wr_pct, by_city,
    days_since_open, verdict, kill_switch, file_found.
    """
    from datetime import date as _date
    if today is None:
        today = _date.today()

    CANARY_OPEN = _date(2026, 4, 14)
    days_since = (today - CANARY_OPEN).days

    result = {
        "n_closed": 0,
        "n_wins": 0,
        "wr": 0.0,
        "wr_pct": "0.0",
        "by_city": {},
        "days_since_open": days_since,
        "verdict": "INSUFFICIENT",
        "kill_switch": False,
        "file_found": False,
    }

    lifecycle_path = TRADE_LIFECYCLE_FILE
    if not os.path.exists(lifecycle_path):
        return result

    result["file_found"] = True
    try:
        with open(lifecycle_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return result

    records = data.get("records", []) if isinstance(data, dict) else []
    canary_start = CANARY_OPEN.isoformat()

    trades = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if r.get("condition") not in {"exact", "range"}:
            continue
        opened = str(r.get("opened_at") or "")
        if opened[:10] < canary_start:
            continue
        if r.get("status") != "closed":
            continue
        trades.append(r)

    n_closed = len(trades)
    n_wins = 0
    by_city = {}
    for r in trades:
        cc = r.get("close_context") or {}
        pnl = cc.get("pnl_cash")
        win = False
        if pnl is not None:
            try:
                win = float(pnl) > 0
            except (TypeError, ValueError):
                pass
        if not win:
            win = cc.get("close_action") == "RESOLVED_WIN"
        if win:
            n_wins += 1
        city = r.get("city", "?")
        if city not in by_city:
            by_city[city] = {"wins": 0, "total": 0}
        by_city[city]["total"] += 1
        if win:
            by_city[city]["wins"] += 1

    wr = (n_wins / n_closed) if n_closed > 0 else 0.0
    wr_pct = f"{wr * 100:.1f}"
    kill_switch = wr < 0.45 and n_closed >= 20

    if kill_switch:
        verdict = "KILL_SWITCH"
    elif days_since >= 14:
        if n_closed >= 30 and wr >= 0.55:
            verdict = "PROMOTE"
        elif n_closed >= 30 and wr >= 0.50:
            verdict = "EXTEND"
        elif n_closed >= 30:
            verdict = "CLOSE"
        else:
            verdict = "INSUFFICIENT"
    elif days_since >= 7:
        if n_closed >= 15 and wr < 0.50:
            verdict = "CLOSE"
        elif n_closed >= 15 and wr < 0.70:
            verdict = "ALERT"
        elif n_closed >= 15:
            verdict = "OK"
        else:
            verdict = "INSUFFICIENT"
    else:
        verdict = "INSUFFICIENT"

    result.update({
        "n_closed": n_closed,
        "n_wins": n_wins,
        "wr": wr,
        "wr_pct": wr_pct,
        "by_city": by_city,
        "verdict": verdict,
        "kill_switch": kill_switch,
    })
    return result


def _condition_monitor_city_breakdown(by_city):
    """Formatea desglose por ciudad para Telegram (top 5 por volumen)."""
    lines = []
    for city, cs in sorted(by_city.items(), key=lambda x: -x[1]["total"])[:5]:
        cwr = cs["wins"] / cs["total"] * 100 if cs["total"] > 0 else 0
        lines.append(f"{city} {cs['wins']}/{cs['total']} ({cwr:.0f}%)")
    return ", ".join(lines) if lines else "sin datos"


def _build_condition_checkpoint_message(stats, is_checkpoint):
    """
    v10.6.16: Construye el mensaje Telegram para checkpoint o kill-switch del canary
    condition_filtered. Siempre incluye instrucción lista para sesión Sonnet/Codex.
    """
    from datetime import date as _date
    n = stats["n_closed"]
    wins = stats["n_wins"]
    wr_pct = stats["wr_pct"]
    days = stats["days_since_open"]
    verdict = stats["verdict"]
    kill = stats["kill_switch"]
    city_str = _condition_monitor_city_breakdown(stats["by_city"])

    today = _date.today()
    CHECKPOINT_DAY14 = _date(2026, 4, 28)
    next_checkpoint = CHECKPOINT_DAY14 if today < CHECKPOINT_DAY14 else None

    handoff_main = "docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md"
    handoff_impl = "docs/handoffs/condition-filtered-canary-implement-2026-04-14.md"

    if kill:
        return (
            f"\U0001f6a8 <b>KILL-SWITCH condition_filtered</b>\n\n"
            f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
            f"Threshold: &lt;45% con n\u226520 \u2192 CUMPLIDO\n"
            f"Ciudades: {city_str}\n\n"
            f"<b>Para sesi\u00f3n Sonnet/Codex:</b>\n"
            f"<code>Leer {handoff_main} y {handoff_impl}.\n"
            f"WR={wr_pct}% n={n} \u2192 kill-switch activado.\n"
            f"Acci\u00f3n urgente: setear QUALITY_TRADER_CONDITIONS=\"\" en Railway "
            f"y actualizar CONTEXTO.md secci\u00f3n \"Condition filtered reopen\".</code>\n\n"
            f"Este aviso se repetir\u00e1 diariamente hasta que se ejecute la acci\u00f3n."
        )

    if verdict == "CLOSE":
        accion = (
            f"WR={wr_pct}% n={n} &lt; 50% threshold d\u00eda {days}.\n"
            f"Acci\u00f3n requerida: cerrar canary. Setear QUALITY_TRADER_CONDITIONS=\"\" "
            f"en Railway y actualizar CONTEXTO.md."
        )
        return (
            f"\u26a0\ufe0f <b>ALERTA condition_filtered \u2014 D\u00eda {days}</b>\n\n"
            f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
            f"Estado: \u26a0\ufe0f BAJO THRESHOLD\n"
            f"Ciudades: {city_str}\n\n"
            f"<b>Para sesi\u00f3n Sonnet:</b>\n"
            f"<code>Leer {handoff_main} y {handoff_impl}.\n"
            f"{accion}</code>"
        )

    if verdict == "ALERT":
        next_str = f"\nPr\u00f3ximo checkpoint: {next_checkpoint}" if next_checkpoint else ""
        return (
            f"\U0001f4ca Checkpoint condition_filtered \u2014 D\u00eda {days}\n\n"
            f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
            f"Estado: \u26a0\ufe0f ALERTA (50-70%) \u2014 continuar sin cambios de sizing{next_str}\n"
            f"Ciudades: {city_str}\n\n"
            f"<b>Para sesi\u00f3n Sonnet (no urgente):</b>\n"
            f"<code>Leer {handoff_main}.\n"
            f"WR={wr_pct}% n={n} d\u00eda {days}. Estado: ALERT.\n"
            f"Acci\u00f3n: actualizar CONTEXTO.md con m\u00e9tricas. Sin cambios en Railway.</code>"
        )

    if verdict == "PROMOTE":
        return (
            f"\u2705 <b>PROMOVER condition_filtered \u2014 D\u00eda {days}</b>\n\n"
            f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
            f"Estado: \u2705 WR\u226555% n\u226530 \u2192 listo para promover\n"
            f"Ciudades: {city_str}\n\n"
            f"<b>Para sesi\u00f3n Sonnet:</b>\n"
            f"<code>Leer {handoff_main} y {handoff_impl}.\n"
            f"WR={wr_pct}% n={n} d\u00eda {days}. Verdict: PROMOTE.\n"
            f"Acci\u00f3n: quitar EXACT_RANGE_SIZE_SCALE de Railway (mantener trader-gate y edge buffer). "
            f"Actualizar CONTEXTO.md.</code>"
        )

    if verdict == "EXTEND":
        return (
            f"\U0001f4ca Checkpoint condition_filtered \u2014 D\u00eda {days}\n\n"
            f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
            f"Estado: WR 50-55% \u2192 extender canary 14 d\u00edas m\u00e1s\n"
            f"Ciudades: {city_str}\n\n"
            f"<b>Para sesi\u00f3n Sonnet (no urgente):</b>\n"
            f"<code>Leer {handoff_main}.\n"
            f"WR={wr_pct}% n={n} d\u00eda {days}. Verdict: EXTEND.\n"
            f"Acci\u00f3n: mantener canary sin cambios. Actualizar CONTEXTO.md con m\u00e9tricas.</code>"
        )

    # OK (WR>=70%, n>=15)
    next_str = f"\nPr\u00f3ximo checkpoint: {next_checkpoint}" if next_checkpoint else ""
    return (
        f"\u2705 Checkpoint condition_filtered \u2014 D\u00eda {days}\n\n"
        f"WR bot exact/range: {wr_pct}% ({wins}/{n})\n"
        f"Estado: \u2705 OK{next_str}\n"
        f"Ciudades: {city_str}\n\n"
        f"<b>Para sesi\u00f3n Sonnet (no urgente):</b>\n"
        f"<code>Leer {handoff_main}.\n"
        f"WR={wr_pct}% n={n} d\u00eda {days}. Estado: OK.\n"
        f"Acci\u00f3n: actualizar CONTEXTO.md con m\u00e9tricas actuales. Sin cambios en Railway.</code>"
    )


def maybe_run_condition_monitor(state, now=None):
    """
    v10.6.16: checkpoint automático del canary condition_filtered exact/range.

    Dispara desde el día 7 (2026-04-21):
    - En fechas exactas de checkpoint (día 7 y día 14)
    - Cuando kill-switch se activa (WR<45% n>=20), diariamente hasta acción
    - Anti-spam: un envío por fecha de checkpoint; kill-switch se repite diariamente

    Retirado el 2026-05-10: el canary original cerró con kill-switch en sesión 341.
    Phase 2 abre esa fecha y su monitor (v10.6.50) toma el control.

    Retorna True si state fue mutado.
    """
    from datetime import date as _date
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.date()
    today_str = today.isoformat()

    CANARY_OPEN = _date(2026, 4, 14)
    CHECKPOINT_DAY7 = _date(2026, 4, 21)
    CHECKPOINT_DAY14 = _date(2026, 4, 28)
    CANARY_RETIRED = _date(2026, 5, 10)

    if today >= CANARY_RETIRED:
        return False  # canary legacy retirado; Phase 2 monitor (v10.6.50) gobierna desde esta fecha

    days_since = (today - CANARY_OPEN).days
    if days_since < 7:
        return False

    is_checkpoint = today in {CHECKPOINT_DAY7, CHECKPOINT_DAY14}

    # Anti-spam para checkpoints normales: un envío por fecha
    last_sent = state.get("last_condition_checkpoint") or {}
    if isinstance(last_sent, str):
        last_sent = {"date": last_sent}

    # Siempre calcular stats (necesario para kill-switch check)
    try:
        stats = _condition_monitor_stats(today=today)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"condition monitor: error calculando stats ({e})")
        return False

    kill = stats.get("kill_switch", False)

    # Kill-switch repite diariamente; checkpoints solo si no enviado hoy
    if kill:
        if last_sent.get("date") == today_str and last_sent.get("type") == "kill":
            return False  # ya enviado hoy
    elif is_checkpoint:
        if last_sent.get("date") == today_str:
            return False  # ya enviado hoy
    else:
        return False  # no es checkpoint ni kill-switch

    try:
        msg = _build_condition_checkpoint_message(stats, is_checkpoint=is_checkpoint)
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"condition monitor: fallo al enviar Telegram ({e})")
        return False

    state["last_condition_checkpoint"] = {
        "date": today_str,
        "type": "kill" if kill else "checkpoint",
        "wr_pct": stats["wr_pct"],
        "n": stats["n_closed"],
        "verdict": stats["verdict"],
    }
    return True


def _phase2_monitor_stats(today=None):
    """
    v10.6.50: Calcula WR Phase 2 mixed-condition desde apertura (2026-05-10).

    Mixed: exact + at_or_above + at_or_below (range excluido).
    Exact-slice: solo exact.

    Kill-switches (rolling, sin fechas de checkpoint):
    - mixed: WR < 40% con n >= 20 → rollback Phase 2
    - exact: WR < 40% con n >= 10 → vaciar QUALITY_TRADER_CONDITIONS

    El bot NO modifica Railway automáticamente. Solo alerta para acción manual.
    """
    from datetime import date as _date
    if today is None:
        today = _date.today()

    PHASE2_OPEN = _date(2026, 5, 10)
    days_since = (today - PHASE2_OPEN).days

    result = {
        "n_mixed": 0,
        "n_mixed_wins": 0,
        "wr_mixed": 0.0,
        "wr_mixed_pct": "0.0",
        "n_exact": 0,
        "n_exact_wins": 0,
        "wr_exact": 0.0,
        "wr_exact_pct": "0.0",
        "mixed_kill_switch": False,
        "exact_kill_switch": False,
        "days_since_open": days_since,
        "file_found": False,
    }

    lifecycle_path = TRADE_LIFECYCLE_FILE
    if not os.path.exists(lifecycle_path):
        return result

    result["file_found"] = True
    try:
        with open(lifecycle_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return result

    records = data.get("records", []) if isinstance(data, dict) else []
    phase2_start = PHASE2_OPEN.isoformat()

    MIXED_CONDITIONS = {"exact", "at_or_above", "at_or_below"}

    n_mixed_wins = 0
    n_exact = 0
    n_exact_wins = 0
    trades_mixed = []

    for r in records:
        if not isinstance(r, dict):
            continue
        cond = r.get("condition", "")
        if cond not in MIXED_CONDITIONS:
            continue
        opened = str(r.get("opened_at") or "")
        if opened[:10] < phase2_start:
            continue
        if r.get("status") != "closed":
            continue
        trades_mixed.append(r)

    for r in trades_mixed:
        cc = r.get("close_context") or {}
        pnl = cc.get("pnl_cash")
        win = False
        if pnl is not None:
            try:
                win = float(pnl) > 0
            except (TypeError, ValueError):
                pass
        if not win:
            win = cc.get("close_action") == "RESOLVED_WIN"
        if win:
            n_mixed_wins += 1
        if r.get("condition") == "exact":
            n_exact += 1
            if win:
                n_exact_wins += 1

    n_mixed = len(trades_mixed)
    wr_mixed = (n_mixed_wins / n_mixed) if n_mixed > 0 else 0.0
    wr_exact = (n_exact_wins / n_exact) if n_exact > 0 else 0.0

    mixed_kill_switch = wr_mixed < 0.40 and n_mixed >= 20
    exact_kill_switch = wr_exact < 0.40 and n_exact >= 10

    result.update({
        "n_mixed": n_mixed,
        "n_mixed_wins": n_mixed_wins,
        "wr_mixed": wr_mixed,
        "wr_mixed_pct": f"{wr_mixed * 100:.1f}",
        "n_exact": n_exact,
        "n_exact_wins": n_exact_wins,
        "wr_exact": wr_exact,
        "wr_exact_pct": f"{wr_exact * 100:.1f}",
        "mixed_kill_switch": mixed_kill_switch,
        "exact_kill_switch": exact_kill_switch,
    })
    return result


def _build_phase2_monitor_message(stats):
    """
    v10.6.50: Construye alarma Telegram Phase 2 condition monitor.
    Solo recomendación manual. No BUY/SELL/SKIP. No auto-mutación Railway.
    """
    mixed_kill = stats["mixed_kill_switch"]
    exact_kill = stats["exact_kill_switch"]
    days = stats["days_since_open"]
    parts = []

    if mixed_kill:
        wr_pct = stats["wr_mixed_pct"]
        n = stats["n_mixed"]
        wins = stats["n_mixed_wins"]
        parts.append(
            f"\U0001f6a8 <b>Phase 2 mixed-condition rollback recommended</b>\n\n"
            f"WR mixed (exact+at_or_above+at_or_below): {wr_pct}% ({wins}/{n})\n"
            f"Threshold: &lt;40% con n≥20 → CUMPLIDO\n"
            f"Días desde apertura Phase 2: {days}\n\n"
            f"<b>Acción recomendada (manual):</b>\n"
            f"<code>Revertir Railway env vars:\n"
            f"QUALITY_TRADER_CONDITIONS=\n"
            f"ACTIVE_TRADING_CITIES=NONE\n"
            f"BLOCKED_CITIES=London</code>\n\n"
            f"Este aviso se repetirá diariamente hasta acción manual."
        )

    if exact_kill:
        wr_pct = stats["wr_exact_pct"]
        n = stats["n_exact"]
        wins = stats["n_exact_wins"]
        parts.append(
            f"⚠️ <b>Exact slice degraded — set QUALITY_TRADER_CONDITIONS=''</b>\n\n"
            f"WR exact-slice: {wr_pct}% ({wins}/{n})\n"
            f"Threshold: &lt;40% con n≥10 → CUMPLIDO\n"
            f"Días desde apertura Phase 2: {days}\n\n"
            f"<b>Acción recomendada (manual):</b>\n"
            f"<code>Setear en Railway: QUALITY_TRADER_CONDITIONS=\n"
            f"(at_or_above/at_or_below siguen activos en ALLOWED_CONDITIONS)</code>\n\n"
            f"Este aviso se repetirá diariamente hasta acción manual."
        )

    return "\n\n---\n\n".join(parts) if parts else ""


def maybe_run_phase2_monitor(state, now=None):
    """
    v10.6.50: Monitor rolling Phase 2 mixed-condition (exact + at_or_above + at_or_below).

    Dispara diariamente si kill-switch activo. Anti-spam: un envío por día por tipo.
    No auto-modifica Railway. Solo alerta para acción manual.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today_str = now.date().isoformat()

    try:
        stats = _phase2_monitor_stats(today=now.date())
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"phase2 monitor: error calculando stats ({e})")
        return False

    if not stats["mixed_kill_switch"] and not stats["exact_kill_switch"]:
        return False

    last = state.get("phase2_monitor_last_sent") or {}
    if isinstance(last, str):
        last = {"date": last}

    mixed_already_sent = last.get("date") == today_str and last.get("mixed_kill")
    exact_already_sent = last.get("date") == today_str and last.get("exact_kill")

    needs_send_mixed = stats["mixed_kill_switch"] and not mixed_already_sent
    needs_send_exact = stats["exact_kill_switch"] and not exact_already_sent

    if not needs_send_mixed and not needs_send_exact:
        return False

    msg = _build_phase2_monitor_message(stats)
    if not msg:
        return False

    try:
        send_telegram(msg)
    except Exception as e:
        logger = globals().get("log")
        if logger:
            logger.warning(f"phase2 monitor: fallo al enviar Telegram ({e})")
        return False

    state["phase2_monitor_last_sent"] = {
        "date": today_str,
        "mixed_kill": stats["mixed_kill_switch"],
        "exact_kill": stats["exact_kill_switch"],
        "wr_mixed_pct": stats["wr_mixed_pct"],
        "wr_exact_pct": stats["wr_exact_pct"],
        "n_mixed": stats["n_mixed"],
        "n_exact": stats["n_exact"],
    }
    return True


def _extract_threshold_from_question(question):
    """Extract temperature threshold from Polymarket question text.

    Examples:
        'Will ... be at or above 50°F ...' → 10.0 (converted to Celsius)
        'Will ... be at or below 13°C ...' → 13.0
    """
    import re
    q = str(question or "")
    # Match patterns like "above 50°F", "below 13°C", "above 285°F"
    match = re.search(r'(?:above|below)\s+(-?\d+(?:\.\d+)?)\s*[°]?\s*([FCfc])', q)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).upper()
    if unit == "F":
        value = round((value - 32) * 5 / 9, 1)
    return value


def _normalize_shadow_market_date(value):
    """Normaliza YYYY-MM-DD o datetime ISO a una clave YYYY-MM-DD."""
    text = str(value or "").strip()
    return text[:10] if text else ""


def _shadow_signal_signature(row):
    """Construye una firma estable por señal direccional shadow."""
    if not isinstance(row, dict):
        return ""
    city = str(row.get("city", "") or "").strip()
    market_date = _normalize_shadow_market_date(row.get("date", ""))
    side = str(row.get("side", "") or "").strip().upper()
    question = str(row.get("question", "") or "").strip()
    condition = _shadow_condition_code(question)
    threshold = _extract_threshold_canonical(question)
    threshold_key = "na"
    if threshold is not None:
        threshold_key = f"{threshold:.3f}".rstrip("0").rstrip(".")
    if city and market_date and side and condition != "otro":
        return f"{city}|{market_date}|{side}|{condition}|{threshold_key}"
    return f"{city}|{market_date}|{side}|{question}".strip("|")


def _build_shadow_signal_record(row):
    """Normaliza una oportunidad direccional para persistirla y resolverla con lag NOAA."""
    if not isinstance(row, dict):
        return None
    question = str(row.get("question", "") or "")
    condition = _shadow_condition_code(question)
    edge_pct = float(row.get("edge_pct", 0) or 0)
    if condition not in {"at_or_above", "at_or_below"} or edge_pct <= 0:
        return None
    city = str(row.get("city", "") or "").strip()
    market_date = _normalize_shadow_market_date(row.get("date", ""))
    side = str(row.get("side", "") or "").strip().upper()
    signal_key = _shadow_signal_signature(row)
    if not city or not market_date or not side or not signal_key:
        return None
    seen_at = str(row.get("seen_at") or datetime.now(timezone.utc).isoformat())
    threshold = _extract_threshold_canonical(question)
    return {
        "signal_key": signal_key,
        "city": city,
        "date": market_date,
        "side": side,
        "edge_hit": True,
        "question": question,
        "condition": condition,
        "threshold": threshold,
        "edge_pct": round(edge_pct, 1),
        "best_edge_pct": round(edge_pct, 1),
        "expected_value": round(float(row.get("expected_value", 0) or 0), 2),
        "market_price": row.get("mkt_price", row.get("market_price")),
        "our_prob": row.get("our_prob"),
        "forecast_max": row.get("forecast_max"),
        "first_seen_at": seen_at,
        "last_seen_at": seen_at,
        "times_seen": 1,
    }


def _merge_shadow_signal_history(existing_rows, new_rows):
    """Fusiona señales direccionales sin contar el mismo mercado una vez por ciclo."""
    merged = {}
    for raw in existing_rows or []:
        if not isinstance(raw, dict):
            continue
        normalized = _build_shadow_signal_record(raw) or dict(raw)
        signal_key = str(normalized.get("signal_key") or _shadow_signal_signature(normalized)).strip()
        if not signal_key:
            continue
        normalized["signal_key"] = signal_key
        normalized["date"] = _normalize_shadow_market_date(normalized.get("date", ""))
        normalized["times_seen"] = int(normalized.get("times_seen", 1) or 1)
        normalized["best_edge_pct"] = round(
            float(normalized.get("best_edge_pct", normalized.get("edge_pct", 0)) or 0),
            1,
        )
        merged[signal_key] = normalized

    for raw in new_rows or []:
        normalized = _build_shadow_signal_record(raw)
        if not normalized:
            continue
        signal_key = normalized["signal_key"]
        current = merged.get(signal_key)
        if not current:
            merged[signal_key] = normalized
            continue
        current["last_seen_at"] = max(
            str(current.get("last_seen_at", "") or ""),
            str(normalized.get("last_seen_at", "") or ""),
        )
        first_seen = str(current.get("first_seen_at", "") or "")
        normalized_first = str(normalized.get("first_seen_at", "") or "")
        if not first_seen or (normalized_first and normalized_first < first_seen):
            current["first_seen_at"] = normalized_first
        current["times_seen"] = int(current.get("times_seen", 1) or 1) + 1
        current["edge_pct"] = round(max(float(current.get("edge_pct", 0) or 0), float(normalized.get("edge_pct", 0) or 0)), 1)
        current["best_edge_pct"] = round(max(float(current.get("best_edge_pct", 0) or 0), float(normalized.get("edge_pct", 0) or 0)), 1)
        current["expected_value"] = round(max(float(current.get("expected_value", 0) or 0), float(normalized.get("expected_value", 0) or 0)), 2)
        for field in ("market_price", "our_prob", "forecast_max", "threshold", "condition", "question", "city", "date", "side"):
            if current.get(field) in (None, "", []):
                current[field] = normalized.get(field)

    return list(merged.values())


def _build_shadow_noaa_resolution_stats(shadow_tracking, audit=None):
    """Resuelve señales shadow persistidas contra NOAA observed usando join normalizado."""
    shadow_tracking = shadow_tracking if isinstance(shadow_tracking, dict) else {}
    audit = audit if isinstance(audit, dict) else load_audit_data()
    history = shadow_tracking.get("directional_history", [])
    if not history:
        seed_rows = []
        for row in shadow_tracking.get("recent_opportunities", []):
            if isinstance(row, dict):
                seed_rows.append(row)
        for city_name, city_data in (shadow_tracking.get("cities", {}) or {}).items():
            if not isinstance(city_data, dict):
                continue
            for edge in city_data.get("recent_edges", []):
                if not isinstance(edge, dict):
                    continue
                seeded = dict(edge)
                seeded.setdefault("city", city_name)
                seed_rows.append(seeded)
        history = _merge_shadow_signal_history([], seed_rows)

    noaa_lookup = {}
    observed_key = globals().get("OBSERVED_AUDIT_KEY", "observed_vs_forecast")
    for entry in audit.get(observed_key, []):
        if not isinstance(entry, dict) or entry.get("source") != "noaa_ncei":
            continue
        city = str(entry.get("city", "") or "").strip()
        market_date = _normalize_shadow_market_date(entry.get("date", ""))
        obs_temp = entry.get("observed_temp_c")
        if not city or not market_date or obs_temp is None:
            continue
        noaa_lookup[(city, market_date)] = float(obs_temp)

    total_signals = 0
    matched = 0
    resolved = 0
    wins = 0
    threshold_missing = 0
    for row in history:
        signal = _build_shadow_signal_record(row) or dict(row)
        city = str(signal.get("city", "") or "").strip()
        market_date = _normalize_shadow_market_date(signal.get("date", ""))
        side = str(signal.get("side", "") or "").strip().upper()
        threshold = signal.get("threshold")
        if not city or not market_date or not side:
            continue
        total_signals += 1
        observed_temp = noaa_lookup.get((city, market_date))
        if observed_temp is None:
            continue
        matched += 1
        if threshold is None:
            threshold_missing += 1
            continue
        resolved += 1
        if side == "YES" and observed_temp >= float(threshold):
            wins += 1
        elif side == "NO" and observed_temp < float(threshold):
            wins += 1

    win_rate = round((wins / resolved * 100), 1) if resolved > 0 else 0.0
    return {
        "total_signals": total_signals,
        "matched": matched,
        "resolved": resolved,
        "wins": wins,
        "win_rate": win_rate,
        "noaa_matches": len(noaa_lookup),
        "threshold_missing": threshold_missing,
    }


def build_dashboard_road_to_real(
    shadow_tracking=None,
    forecast_quality=None,
    city_accuracy=None,
    city_decisions=None,
    alerts=None,
):
    """Build the Road to Real progress bar — checklist to reactivate live trading."""
    if shadow_tracking is None:
        shadow_tracking = load_shadow_city_tracking()
    if forecast_quality is None:
        forecast_quality = build_dashboard_forecast_quality()
    if city_accuracy is None:
        city_accuracy = get_city_accuracy()
    if alerts is None:
        alerts = get_dashboard_alert_summary()
    audit_loader = globals().get("load_audit_data")
    audit = audit_loader() if callable(audit_loader) else {}
    shadow_resolution_builder = globals().get("_build_shadow_noaa_resolution_stats")
    if callable(shadow_resolution_builder):
        shadow_resolution = shadow_resolution_builder(shadow_tracking, audit=audit)
    else:
        shadow_resolution = {"total_signals": 0, "matched": 0, "resolved": 0, "win_rate": 0.0}

    shadow_summary = shadow_tracking.get("summary", {}) if isinstance(shadow_tracking, dict) else {}
    recent_opps = shadow_tracking.get("directional_history", []) if isinstance(shadow_tracking, dict) else []

    # R1: >= 30 shadow directional signals (edge_hit=True means passed condition + edge)
    directional_signals = int(shadow_resolution.get("total_signals", 0) or 0)
    r1_target = 30
    r1_current = min(directional_signals, r1_target)
    r1_done = r1_current >= r1_target

    # R2: >= 10 NOAA observations
    noaa_sample = int(forecast_quality.get("sample_size", 0) or 0)
    r2_target = 10
    r2_current = min(noaa_sample, r2_target)
    r2_done = r2_current >= r2_target

    # R3: Simulated WR >= 45% — join shadow directional signals with NOAA observed by city+date
    audit = audit if isinstance(audit, dict) else {}
    # Build lookup: (city, date) → observed_temp_c from NOAA
    noaa_lookup = {}
    if isinstance(audit, dict):
        for entry in audit.get(OBSERVED_AUDIT_KEY, []):
            if not isinstance(entry, dict) or entry.get("source") != "noaa_ncei":
                continue
            obs_temp = entry.get("observed_temp_c")
            if obs_temp is None:
                continue
            key = (str(entry.get("city", "")).strip(), _normalize_shadow_market_date(entry.get("date", "")))
            if key[0] and key[1]:
                noaa_lookup[key] = float(obs_temp)
    # Match shadow directional signals (edge_hit=True) with NOAA observed
    directional_wins = 0
    directional_resolved = 0
    for opp in recent_opps:
        if not opp.get("edge_hit"):
            continue
        city = str(opp.get("city", "")).strip()
        date = _normalize_shadow_market_date(opp.get("date", ""))
        if not city or not date:
            continue
        observed_temp = noaa_lookup.get((city, date))
        if observed_temp is None:
            continue
        # Parse threshold from question text
        question = str(opp.get("question", "") or "")
        side = str(opp.get("side", "") or "").upper()
        threshold = _extract_threshold_from_question(question)
        if threshold is None or not side:
            continue
        directional_resolved += 1
        if side == "YES" and observed_temp >= threshold:
            directional_wins += 1
        elif side == "NO" and observed_temp < threshold:
            directional_wins += 1
    sim_wr = round((directional_wins / directional_resolved * 100), 1) if directional_resolved > 0 else 0.0
    matched_with_noaa = int(shadow_resolution.get("matched", 0) or 0)
    directional_resolved = int(shadow_resolution.get("resolved", 0) or 0)
    sim_wr = float(shadow_resolution.get("win_rate", 0.0) or 0.0)
    r3_target = 45.0
    r3_current = sim_wr
    r3_done = sim_wr >= r3_target and directional_resolved >= 5
    r3_no_join_reason = ""
    if directional_resolved == 0 and directional_signals > 0:
        r3_no_join_reason = f"0/{directional_signals} señales con NOAA enlazada por city+date"

    # R4: Sigma empirica calibrada con n >= 5 por ciudad activa
    cities_with_sigma = 0
    for city, data in (city_accuracy or {}).items():
        if isinstance(data, dict) and int(data.get("trades", 0) or 0) >= 5:
            cities_with_sigma += 1
    r4_target = 2
    r4_current = min(cities_with_sigma, r4_target)
    r4_done = r4_current >= r4_target

    # R5: >= 2 cities with readiness from city decisions ranking
    ready_cities = 0
    if isinstance(city_decisions, dict):
        for row in city_decisions.get("ranking_rows", []):
            score = int(row.get("readiness_score", 0) or 0)
            if score >= 60:
                ready_cities += 1
    r5_target = 2
    r5_current = min(ready_cities, r5_target)
    r5_done = r5_current >= r5_target

    # R6: No critical alerts active
    critical_items = [
        item for item in alerts.get("active_items", [])
        if str(item.get("level", "")) in {"critical", "bad"}
    ]
    r6_done = len(critical_items) == 0
    r6_current = 1 if r6_done else 0
    r6_target = 1

    checks = [
        {
            "id": "shadow_signals",
            "label": f">= {r1_target} señales shadow direccionales",
            "current": directional_signals,
            "target": r1_target,
            "display": f"{directional_signals} / {r1_target}",
            "done": r1_done,
            "badge": "good" if r1_done else "warn" if directional_signals >= r1_target // 2 else "bad",
        },
        {
            "id": "noaa_resolved",
            "label": f">= {r2_target} observaciones NOAA",
            "current": noaa_sample,
            "target": r2_target,
            "display": f"{noaa_sample} / {r2_target}",
            "done": r2_done,
            "badge": "good" if r2_done else "warn" if noaa_sample >= r2_target // 2 else "bad",
        },
        {
            "id": "sim_wr",
            "label": f"WR observado direccional >= {r3_target:.0f}%",
            "current": sim_wr,
            "target": r3_target,
            "display": (
                f"{sim_wr:.1f}% (n={directional_resolved})" if directional_resolved > 0
                else r3_no_join_reason if r3_no_join_reason
                else "sin señales shadow direccionales"
            ),
            "done": r3_done,
            "badge": "good" if r3_done else "warn" if directional_resolved >= 3 else "bad",
        },
        {
            "id": "sigma_calibrated",
            "label": f">= {r4_target} ciudades con sigma empírica (n>=5)",
            "current": cities_with_sigma,
            "target": r4_target,
            "display": f"{cities_with_sigma} / {r4_target}",
            "done": r4_done,
            "badge": "good" if r4_done else "warn" if cities_with_sigma >= 1 else "bad",
        },
        {
            "id": "cities_ready",
            "label": f">= {r5_target} ciudades con readiness >= 60",
            "current": ready_cities,
            "target": r5_target,
            "display": f"{ready_cities} / {r5_target}",
            "done": r5_done,
            "badge": "good" if r5_done else "warn" if ready_cities >= 1 else "bad",
        },
        {
            "id": "no_critical",
            "label": "Sin alertas críticas activas",
            "current": r6_current,
            "target": r6_target,
            "display": "OK" if r6_done else f"{len(critical_items)} alertas críticas",
            "done": r6_done,
            "badge": "good" if r6_done else "bad",
        },
    ]

    passed = sum(1 for c in checks if c["done"])
    total = len(checks)
    pct = int(round(passed / total * 100)) if total > 0 else 0

    if pct >= 100:
        status_label = "Listo para modo canary"
        status_badge = "good"
    elif pct >= 50:
        status_label = "En progreso"
        status_badge = "accent"
    else:
        status_label = "Fase temprana"
        status_badge = "warn"

    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "pct": pct,
        "status_label": status_label,
        "status_badge": status_badge,
    }


def build_dashboard_focus_center(
    alerts=None,
    forecast_quality=None,
    city_observation=None,
    series_stats=None,
    series_clean_stats=None,
    next_run_display="No programado",
    last_cycle_label="Sin ciclos aún",
):
    """Construye la capa 1 operativa para discovery / stabilization."""
    if alerts is None:
        alerts = get_dashboard_alert_summary()
    if forecast_quality is None:
        forecast_quality = build_dashboard_forecast_quality()
    if city_observation is None:
        city_observation = build_dashboard_city_observation()
    if series_stats is None:
        series_stats = get_logic_series_stats()
    if series_clean_stats is None:
        series_clean_stats = get_logic_series_clean_closed_trade_stats()

    def _pct(value, total):
        if total <= 0:
            return 0
        return max(0, min(100, int(round((value / total) * 100))))

    def _answer(question, answer, detail, badge, tag):
        return {
            "question": question,
            "answer": answer,
            "detail": detail,
            "badge": badge,
            "tag": tag,
        }

    def _item(label, value, detail, status):
        tags = {
            "good": "OK",
            "warn": "Watch",
            "bad": "Atender",
            "accent": "Focus",
            "muted": "n/d",
        }
        return {
            "label": label,
            "value": value,
            "detail": detail,
            "status": status,
            "tag": tags.get(status, "Focus"),
        }

    signal_status = str(alerts.get("signals", {}).get("status", "unknown") or "unknown")
    signal_actionable = int(alerts.get("signals", {}).get("actionable", 0) or 0)
    pending_count = len(alerts.get("pending_stuck", []))
    flagged_cities = alerts.get("flagged_cities_operational", alerts.get("flagged_cities", []))
    flagged_count = len(flagged_cities)
    low_bankroll = bool(alerts.get("low_bankroll"))
    portfolio_total = alerts.get("portfolio_total")

    sample_size = int(forecast_quality.get("sample_size", 0) or 0)
    active_count = int(city_observation.get("active_count", 0) or 0)
    blocked_count = int(city_observation.get("blocked_count", 0) or 0)
    observed_ready_count = int(city_observation.get("observed_ready_count", 0) or 0)
    observed_configured_count = int(city_observation.get("observed_configured_count", 0) or 0)
    observed_target = observed_configured_count or active_count or len(OBSERVED_AUDIT_CITIES)
    series_clean_count = int(series_clean_stats.get("count", 0) or 0)
    coverage_target = active_count or observed_target
    measurement_limited = active_count > observed_ready_count or sample_size < OBSERVED_FORECAST_GLOBAL_TARGET

    critical_ops = []
    warn_ops = []

    if low_bankroll:
        total_display = f"${portfolio_total:.2f}" if isinstance(portfolio_total, (int, float)) else "n/d"
        critical_ops.append(
            f"bankroll bajo: cartera {total_display} por debajo del umbral ${LOW_BANKROLL_THRESHOLD:.2f}"
        )
    if signal_status in {"missing", "error"}:
        critical_ops.append(
            f"signals.json en estado {signal_status} con {signal_actionable} señales accionables"
        )
    elif signal_status in {"stale", "empty"} and not measurement_limited:
        warn_ops.append(
            f"signals.json en estado {signal_status} con {signal_actionable} señales accionables"
        )
    if pending_count > 0:
        critical_ops.append(
            f"{pending_count} pending exits llevan más de {PENDING_EXIT_ALERT_HOURS:.0f}h"
        )
    if flagged_count > 0:
        flagged_names = ", ".join(item.get("city", "?") for item in flagged_cities[:3])
        warn_ops.append(
            f"{flagged_count} ciudades bajo review NOAA-verificado ({flagged_names})"
        )

    if critical_ops:
        status_label = "Intervención requerida"
        status_badge = "bad"
        headline = "Resolver el incidente operativo antes de dejar al bot seguir solo."
        summary = critical_ops[0]
    elif measurement_limited:
        status_label = "Sano con limitaciones"
        status_badge = "accent"
        headline = "La operativa parece estable; el cuello de botella ahora es learning / measurement."
        summary = (
            f"NOAA {sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET} casos | "
            f"{observed_ready_count}/{max(1, observed_target)} ciudades interpretables."
        )
    elif warn_ops:
        status_label = "Sano con alertas"
        status_badge = "warn"
        headline = "El sistema sigue operativo, pero hoy conviene revisar una alerta real."
        summary = warn_ops[0]
    else:
        status_label = "Sano"
        status_badge = "good"
        headline = "Sistema sano y con observabilidad suficiente para seguir aprendiendo."
        summary = "No hay incidentes operativos activos ni cuellos de botella dominantes visibles."

    health_score = 100
    if low_bankroll:
        health_score -= 45
    if signal_status in {"missing", "error"}:
        health_score -= 35
    elif signal_status in {"stale", "empty"} and not measurement_limited:
        health_score -= 18
    if pending_count > 0:
        health_score -= min(35, 12 + pending_count * 8)
    if flagged_count > 0:
        health_score -= min(15, flagged_count * 3)
    health_score = max(0, min(100, health_score))
    health_badge = "good" if health_score >= 85 and not critical_ops else "warn" if health_score >= 60 else "bad"
    coverage_pct = _pct(observed_ready_count, max(1, coverage_target))
    sample_pct = _pct(sample_size, OBSERVED_FORECAST_GLOBAL_TARGET)
    series_pct = _pct(series_clean_count, REVIEW_READY_CLEAN_TRADES)

    if critical_ops:
        intervention_answer = "Sí, antes del próximo ciclo"
        intervention_badge = "bad"
        intervention_detail = critical_ops[0]
    elif measurement_limited and warn_ops:
        intervention_answer = "No; seguir discovery y sanear alertas secundarias"
        intervention_badge = "accent"
        intervention_detail = (
            "La prioridad sigue siendo NOAA / coverage; "
            f"secundario: {warn_ops[0]}"
        )
    elif warn_ops:
        intervention_answer = "Revisión hoy, sin urgencia crítica"
        intervention_badge = "warn"
        intervention_detail = warn_ops[0]
    else:
        intervention_answer = "No; solo monitorizar"
        intervention_badge = "good"
        intervention_detail = "Sin incidentes operativos activos ahora mismo."

    if low_bankroll:
        limiter_answer = "Bankroll operativo"
        limiter_badge = "bad"
        limiter_detail = (
            f"la cartera cayó por debajo del umbral ${LOW_BANKROLL_THRESHOLD:.2f}; "
            "sin caja el bot deja de aprender"
        )
    elif signal_status in {"missing", "error"}:
        limiter_answer = "Señales de traders"
        limiter_badge = "bad" if signal_status in {"missing", "error"} else "warn"
        limiter_detail = f"signals.json está en {signal_status} y limita el scan accionable"
    elif pending_count > 0:
        limiter_answer = "Pending exits atascadas"
        limiter_badge = "bad"
        limiter_detail = (
            f"{pending_count} órdenes siguen pendientes tras {PENDING_EXIT_ALERT_HOURS:.0f}h"
        )
    elif active_count > 0 and observed_ready_count < active_count:
        limiter_answer = "Cobertura NOAA del universo activo"
        limiter_badge = "accent" if observed_ready_count > 0 else "warn"
        limiter_detail = (
            f"{observed_ready_count}/{active_count} activas tienen NOAA interpretable; "
            "seguimos operando mejor de lo que medimos"
        )
    elif sample_size < OBSERVED_FORECAST_GLOBAL_TARGET:
        limiter_answer = "Muestra NOAA global"
        limiter_badge = "accent" if sample_size else "warn"
        limiter_detail = (
            f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET} casos; "
            "todavía cuesta leer sesgo global con confianza"
        )
    elif signal_status != "ok":
        limiter_answer = "SeÃ±ales de traders"
        limiter_badge = "warn"
        limiter_detail = f"signals.json estÃ¡ en {signal_status} y limita el scan accionable"
    elif flagged_count > 0:
        limiter_answer = "NOAA-verificado desigual"
        limiter_badge = "warn"
        limiter_detail = f"{flagged_count} ciudades siguen bajo review NOAA-verificado"
    elif series_clean_count < REVIEW_READY_CLEAN_TRADES:
        limiter_answer = "Muestra de la serie actual"
        limiter_badge = "accent"
        limiter_detail = (
            f"{series_clean_count}/{REVIEW_READY_CLEAN_TRADES} cierres limpios; "
            "aún no toca reinterpretar trading"
        )
    else:
        limiter_answer = "Sin limitador dominante"
        limiter_badge = "good"
        limiter_detail = "no aparece un bloqueo principal claro ahora mismo"

    if sample_size == 0:
        learning_answer = "Solo operando"
        learning_badge = "bad"
        learning_detail = "0 casos NOAA: todavía no estamos aprendiendo de forma útil"
    elif observed_ready_count == 0:
        learning_answer = "Aprendizaje incipiente"
        learning_badge = "warn"
        learning_detail = (
            f"{sample_size} casos NOAA, pero 0/{max(1, observed_target)} ciudades interpretables"
        )
    elif sample_size < OBSERVED_FORECAST_GLOBAL_TARGET or observed_ready_count < max(1, active_count):
        learning_answer = "Operando y aprendiendo"
        learning_badge = "accent"
        learning_detail = (
            f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET} casos NOAA | "
            f"{observed_ready_count}/{max(1, observed_target)} ciudades interpretables"
        )
    else:
        learning_answer = "Aprendizaje útil"
        learning_badge = "good"
        learning_detail = (
            f"{sample_size} casos NOAA | "
            f"{observed_ready_count}/{max(1, observed_target)} ciudades interpretables"
        )

    if critical_ops:
        mission_label = "Mission Critical"
        mission_badge = "bad"
        mission_title = "Primera misión: estabilizar la operación antes del siguiente ciclo."
        mission_detail = "Hay un bloqueo operativo real; cualquier mejora visual o de muestra queda en segundo plano hasta cerrar esta incidencia."
    elif measurement_limited:
        mission_label = "Primary Quest"
        mission_badge = "accent"
        mission_title = "Misión actual: convertir operativa en aprendizaje medible."
        mission_detail = (
            "La prioridad no es tocar reglas de trading, sino ganar cobertura NOAA y volumen de muestra suficiente "
            "para entender mejor lo que ya estamos ejecutando."
        )
    elif flagged_count > 0:
        mission_label = "Hold Position"
        mission_badge = "warn"
        mission_title = "Misión actual: mantener la estabilidad y revisar ciudades en observación."
        mission_detail = "La operativa aguanta, pero todavía no toca expandir el universo ni relajar la vigilancia."
    else:
        mission_label = "Cruise Control"
        mission_badge = "good"
        mission_title = "Misión actual: sostener estabilidad y seguir acumulando evidencia útil."
        mission_detail = "La capa 1 pasa a modo seguimiento: no hay una intervención dominante y el sistema puede seguir aprendiendo."

    if low_bankroll:
        action_title = "Recargar bankroll antes del próximo ciclo"
        action_badge = "bad"
        total_display = f"${portfolio_total:.2f}" if isinstance(portfolio_total, (int, float)) else "n/d"
        action_detail = (
            f"Total cartera {total_display}; sin caja el bot no puede seguir operando ni generando muestra."
        )
    elif signal_status in {"missing", "error"}:
        action_title = "Reparar o regenerar señales antes del próximo ciclo"
        action_badge = "bad"
        action_detail = (
            f"signals.json está en {signal_status}; revisar pipeline de traders antes de dejar correr el bot."
        )
    elif pending_count > 0:
        action_title = "Auditar y reconciliar pending exits atascadas"
        action_badge = "bad"
        action_detail = (
            f"Hay {pending_count} órdenes por encima de {PENDING_EXIT_ALERT_HOURS:.0f}h; "
            "es la única señal que hoy justifica intervención manual."
        )
    elif signal_status in {"stale", "empty"} and not measurement_limited:
        action_title = "Revisar el estado de signals hoy"
        action_badge = "warn"
        action_detail = (
            f"signals.json está en {signal_status}; no rompe el bot, pero conviene sanearlo antes del siguiente ciclo."
        )
    elif measurement_limited:
        action_title = "No tocar trading: priorizar crecimiento de muestra NOAA"
        action_badge = "accent"
        action_detail = (
            f"Universo operable {active_count} | NOAA interpretable {observed_ready_count}/{max(1, observed_target)} | "
            f"muestra global {sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET}."
        )
        if signal_status in {"stale", "empty"}:
            action_detail += f" Secundario: signals.json {signal_status}."
    elif flagged_count > 0:
        action_title = "Mantener allowlist y revisar ciudades con NOAA-verificado flojo"
        action_badge = "warn"
        action_detail = (
            f"{flagged_count} ciudades siguen bajo review NOAA-verificado; no ampliar universo hasta tener evidencia mejor."
        )
    else:
        action_title = "Sin intervención hoy; seguir monitorizando"
        action_badge = "good"
        action_detail = f"Próximo ciclo: {next_run_display} | Último ciclo: {last_cycle_label}"

    incidents = []
    for item in alerts.get("active_items", []):
        level = str(item.get("level", "warn") or "warn")
        badge = "bad" if level in {"critical", "bad"} else "warn" if level == "warn" else "accent"
        incidents.append({
            "title": item.get("title", "?"),
            "detail": item.get("detail", ""),
            "badge": badge,
        })

    # Alarma: sin ciclo en >12h
    try:
        _cycle_ts = None
        if os.path.exists(CYCLE_SUMMARY_FILE):
            _cycle_raw = load_cycle_summary_data()
            _cycle_ts = (_cycle_raw.get("timestamp_utc") if isinstance(_cycle_raw, dict) else None)
        if _cycle_ts:
            _last_cycle = datetime.fromisoformat(str(_cycle_ts).replace("Z", "+00:00"))
            if _last_cycle.tzinfo is None:
                _last_cycle = _last_cycle.replace(tzinfo=timezone.utc)
            _hours_ago = (datetime.now(timezone.utc) - _last_cycle).total_seconds() / 3600
            if _hours_ago > 12:
                incidents.append({
                    "title": f"sin ciclo en {_hours_ago:.0f}h — verificar que el bot sigue corriendo",
                    "detail": f"Último ciclo registrado: {str(_cycle_ts)[:16]} UTC",
                    "badge": "bad",
                })
        else:
            incidents.append({
                "title": "sin ciclo registrado todavía",
                "detail": "cycle_summary.json no existe o no contiene timestamp",
                "badge": "warn",
            })
    except Exception:
        pass

    quick_stats = [
        {
            "label": "Universo operable",
            "value": f"{active_count} operables",
            "detail": f"{blocked_count} bloqueadas",
            "badge": "accent" if active_count else "muted",
        },
        {
            "label": "NOAA interpretable",
            "value": f"{observed_ready_count}/{max(1, observed_target)}",
            "detail": "ciudades con >= 3 casos",
            "badge": "good" if observed_ready_count >= active_count and active_count else "warn" if observed_ready_count else "bad",
        },
        {
            "label": "Muestra NOAA",
            "value": f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET}",
            "detail": forecast_quality.get("coverage_display", "sin muestra"),
            "badge": "good" if sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET else "accent" if sample_size >= OBSERVED_FORECAST_MIN_SAMPLE else "warn" if sample_size else "bad",
        },
        {
            "label": "Próximo ciclo",
            "value": next_run_display,
            "detail": last_cycle_label,
            "badge": "muted",
        },
    ]

    tracks = [
        {
            "id": "health",
            "label": "System health",
            "value": health_score,
            "target": 100,
            "value_text": f"{health_score}/100",
            "target_text": "0 incidentes críticos",
            "pct": health_score,
            "badge": health_badge,
            "tag": "HP",
            "detail": (
                "Operación estable y sin intervención manual urgente."
                if health_badge == "good"
                else "Hay señales que degradan la salud operativa y conviene vigilarlas."
                if health_badge == "warn"
                else "Hay una incidencia que puede romper la sesión si no se atiende."
            ),
        },
        {
            "id": "coverage",
            "label": "Allowlist vs NOAA",
            "value": observed_ready_count,
            "target": max(1, coverage_target),
            "value_text": f"{observed_ready_count}/{max(1, coverage_target)}",
            "target_text": "ciudades activas cubiertas",
            "pct": coverage_pct,
            "badge": "good" if active_count and observed_ready_count >= active_count else "accent" if observed_ready_count else "warn" if active_count else "muted",
            "tag": "MAP",
            "detail": (
                "Cada ciudad activa ya tiene NOAA interpretable."
                if active_count and observed_ready_count >= active_count
                else "Seguimos operando con parte del universo sin lectura observable suficiente."
            ),
        },
        {
            "id": "sample",
            "label": "NOAA sample growth",
            "value": sample_size,
            "target": OBSERVED_FORECAST_GLOBAL_TARGET,
            "value_text": f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET}",
            "target_text": "meta global de casos",
            "pct": sample_pct,
            "badge": "good" if sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET else "accent" if sample_size >= OBSERVED_FORECAST_MIN_SAMPLE else "warn" if sample_size else "bad",
            "tag": "EXP",
            "detail": forecast_quality.get("note", "Sin muestra NOAA suficiente todavía."),
        },
        {
            "id": "learning",
            "label": f"Serie v{LOGIC_SERIES}",
            "value": series_clean_count,
            "target": REVIEW_READY_CLEAN_TRADES,
            "value_text": f"{series_clean_count}/{REVIEW_READY_CLEAN_TRADES}",
            "target_text": "cierres limpios para revisión",
            "pct": series_pct,
            "badge": "good" if series_clean_count >= REVIEW_READY_CLEAN_TRADES else "accent" if series_clean_count else "warn",
            "tag": "XP",
            "detail": "Progreso de evidencia de la serie actual sin reinterpretar aún la lógica de trading.",
        },
    ]

    drivers = [
        _item(
            "Universo operable vs NOAA",
            f"{observed_ready_count}/{max(1, active_count)} cubiertas" if active_count else "0 operables",
            (
                "todas las ciudades activas ya tienen NOAA interpretable"
                if active_count and observed_ready_count >= active_count
                else "seguimos operando con parte del universo aún sin lectura observable útil"
            ),
            "good" if active_count and observed_ready_count >= active_count else "warn" if observed_ready_count else "bad",
        ),
        _item(
            "Muestra NOAA global",
            f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET}",
            forecast_quality.get("note", "sin muestra"),
            "good" if sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET else "accent" if sample_size >= OBSERVED_FORECAST_MIN_SAMPLE else "warn" if sample_size else "bad",
        ),
        _item(
            f"Serie v{LOGIC_SERIES}",
            f"{series_clean_count}/{REVIEW_READY_CLEAN_TRADES}",
            "cierres limpios de la serie actual para revisar lógica con confianza",
            "good" if series_clean_count >= REVIEW_READY_CLEAN_TRADES else "accent" if series_clean_count else "warn",
        ),
        _item(
            "Incidentes operativos",
            str(len(incidents)),
            incidents[0]["title"] if incidents else "sin incidentes operativos activos",
            "bad" if critical_ops else "warn" if warn_ops else "good",
        ),
    ]

    stage_path = [
        {
            "label": "Health",
            "value": status_label,
            "detail": summary,
            "status": status_badge,
            "tag": "OPS",
        },
        {
            "label": "Universe",
            "value": f"{active_count} activas | {blocked_count} bloqueadas",
            "detail": "Allowlist real que hoy determina qué estamos operando y qué solo observamos.",
            "status": "good" if active_count else "muted",
            "tag": "MAP",
        },
        {
            "label": "NOAA",
            "value": f"{sample_size}/{OBSERVED_FORECAST_GLOBAL_TARGET} casos",
            "detail": f"{observed_ready_count}/{max(1, observed_target)} ciudades interpretables.",
            "status": "good" if sample_size >= OBSERVED_FORECAST_GLOBAL_TARGET else "accent" if sample_size >= OBSERVED_FORECAST_MIN_SAMPLE else "warn" if sample_size else "bad",
            "tag": "EXP",
        },
        {
            "label": "Learning",
            "value": learning_answer,
            "detail": learning_detail,
            "status": learning_badge,
            "tag": "XP",
        },
    ]

    city_rows = list(city_observation.get("rows", []))
    city_race = []
    for row in city_rows:
        if not row.get("active") and not row.get("noaa_configured"):
            continue
        observed_count = int(row.get("observed_count", 0) or 0)
        city_race.append({
            "city": row.get("city", "?"),
            "value": observed_count,
            "target": OBSERVED_FORECAST_MIN_SAMPLE,
            "pct": _pct(min(observed_count, OBSERVED_FORECAST_MIN_SAMPLE), OBSERVED_FORECAST_MIN_SAMPLE),
            "value_text": f"{observed_count}/{OBSERVED_FORECAST_MIN_SAMPLE}",
            "detail": row.get("state_detail", ""),
            "badge": row.get("state_badge", "muted"),
            "tag": row.get("state_label", "Seguimiento"),
            "active": bool(row.get("active")),
            "trades": int(row.get("trades", 0) or 0),
        })

    city_race.sort(
        key=lambda item: (
            0 if item["active"] else 1,
            0 if item["value"] >= OBSERVED_FORECAST_MIN_SAMPLE else 1 if item["value"] > 0 else 2,
            -item["value"],
            -item["trades"],
            item["city"],
        )
    )
    city_race = city_race[:6]

    detail_routes = [
        {"label": "/estado", "detail": "salud y ciclos"},
        {"label": "/noaa", "detail": "sample NOAA"},
        {"label": "/accuracy", "detail": "histórico por ciudad"},
        {"label": "/detalle", "detail": "último ciclo raw"},
    ]

    return {
        "headline": headline,
        "summary": summary,
        "status_label": status_label,
        "status_badge": status_badge,
        "health_score": health_score,
        "mission": {
            "label": mission_label,
            "badge": mission_badge,
            "title": mission_title,
            "detail": mission_detail,
        },
        "answers": [
            _answer("¿Está sano el sistema?", status_label, summary, status_badge, "Sistema"),
            _answer("¿Hay que intervenir hoy?", intervention_answer, intervention_detail, intervention_badge, "Hoy"),
            _answer("¿Qué me limita ahora?", limiter_answer, limiter_detail, limiter_badge, "Bloqueo"),
            _answer("¿Estamos aprendiendo o solo operando?", learning_answer, learning_detail, learning_badge, "Discovery"),
        ],
        "action": {
            "title": action_title,
            "detail": action_detail,
            "badge": action_badge,
        },
        "incidents": incidents,
        "quick_stats": quick_stats,
        "tracks": tracks,
        "stage_path": stage_path,
        "city_race": city_race,
        "drivers": drivers,
        "detail_routes": detail_routes,
    }


def build_dashboard_legacy_forecast_drift(audit=None):
    """Resume el bloque legacy forecast_vs_real, dejando claro que es historico y no comparable."""
    if audit is None:
        audit = load_audit_data()

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fmt_temp(value, signed=False):
        number = _safe_float(value)
        if number is None:
            return "n/d"
        return f"{number:+.1f}C" if signed else f"{number:.1f}C"

    def _fmt_checked_at(value):
        text = str(value or "").strip()
        if not text:
            return "n/d"
        text = text.replace("T", " ")
        if text.endswith("+00:00"):
            return f"{text[:16]} UTC"
        return text[:16]

    rows = []
    for raw in audit.get(FORECAST_AUDIT_KEY, []):
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        original = _safe_float(row.get("forecast_original"))
        posterior = _safe_float(row.get("forecast_posterior"))
        error_c = _safe_float(row.get("error_c"))
        if error_c is None and original is not None and posterior is not None:
            error_c = round(posterior - original, 1)
        abs_error_c = _safe_float(row.get("abs_error_c"))
        if abs_error_c is None and error_c is not None:
            abs_error_c = abs(error_c)
        row["_error_c"] = error_c
        row["_abs_error_c"] = abs_error_c
        rows.append(row)

    rows.sort(
        key=lambda item: (
            item.get("checked_at") or "",
            item.get("date") or "",
            item.get("city") or "",
        ),
        reverse=True,
    )

    all_errors = [item["_error_c"] for item in rows if item.get("_error_c") is not None]
    all_abs_errors = [item["_abs_error_c"] for item in rows if item.get("_abs_error_c") is not None]
    mae_c = round(sum(all_abs_errors) / len(all_abs_errors), 1) if all_abs_errors else None
    bias_c = round(sum(all_errors) / len(all_errors), 1) if all_errors else None
    latest = rows[0] if rows else {}

    latest_case = ""
    if latest:
        latest_case = (
            f"{latest.get('city', '?')} {latest.get('date', '?')} | "
            f"forecast original { _fmt_temp(latest.get('forecast_original')) } | "
            f"forecast posterior { _fmt_temp(latest.get('forecast_posterior')) } | "
            f"deriva { _fmt_temp(latest.get('_error_c'), signed=True) }"
        )

    return {
        "sample_size": len(rows),
        "sample_display": f"{len(rows)} mercado" if len(rows) == 1 else f"{len(rows)} mercados",
        "mae_display": _fmt_temp(mae_c) if mae_c is not None else "n/d",
        "bias_display": _fmt_temp(bias_c, signed=True) if bias_c is not None else "n/d",
        "last_record_display": _fmt_checked_at(latest.get("checked_at")) if latest else "n/d",
        "latest_case": latest_case,
        "note": (
            "Historico legacy congelado: compara forecast original vs forecast posterior Open-Meteo. "
            "No es comparable 1:1 con NOAA ni con resolucion real."
        ),
    }


def build_dashboard_trade_analytics(trade_lifecycle=None, portfolio=None):
    """Resume la eficiencia observada de las salidas sin tocar reglas de trading."""
    if trade_lifecycle is None:
        trade_lifecycle = load_trade_lifecycle_data()
    if portfolio is None:
        portfolio = _get_portfolio_and_positions()

    payload = trade_lifecycle if isinstance(trade_lifecycle, dict) else {}
    records = payload.get("records", []) if isinstance(payload.get("records"), list) else []
    coalesce_fn = globals().get("_coalesce_trade_lifecycle_records")
    if callable(coalesce_fn):
        records, _ = coalesce_fn(records)
    summary_builder = globals().get("_build_trade_lifecycle_summary")
    integrity_builder = globals().get("_build_trade_lifecycle_integrity")
    summary = (
        summary_builder(records)
        if callable(summary_builder)
        else payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    )
    integrity_summary = (
        integrity_builder(records)
        if callable(integrity_builder)
        else payload.get("integrity", {}) if isinstance(payload.get("integrity"), dict) else {}
    )
    position_key_fn = globals().get("_trade_lifecycle_position_key")
    if not callable(position_key_fn):
        def position_key_fn(entry):
            side = str(entry.get("side", "") or "").upper()
            token_id = str(entry.get("token_id", "") or "").strip()
            question = re.sub(r"\s+", " ", str(entry.get("question", "") or "").strip()).lower()
            city = re.sub(r"\s+", " ", str(entry.get("city", "") or "").strip()).lower()
            market_date = str(entry.get("date", "") or "").strip()
            if token_id:
                return f"token:{token_id}|date:{market_date}|side:{side}"
            if question:
                return f"question:{question}|date:{market_date}|side:{side}"
            if city or market_date:
                return f"market:{city}|date:{market_date}|side:{side}"
            return ""
    market_key_fn = globals().get("_trade_lifecycle_market_key")
    if not callable(market_key_fn):
        def market_key_fn(entry):
            token_id = str(entry.get("token_id", "") or "").strip()
            question = re.sub(r"\s+", " ", str(entry.get("question", "") or "").strip()).lower()
            city = re.sub(r"\s+", " ", str(entry.get("city", "") or "").strip()).lower()
            market_date = str(entry.get("date", "") or "").strip()
            if token_id:
                return f"token:{token_id}|date:{market_date}"
            if question:
                return f"question:{question}|date:{market_date}"
            if city or market_date:
                return f"market:{city}|date:{market_date}"
            return ""
    def _position_alias_keys(entry):
        aliases = []
        token_id = str(entry.get("token_id", "") or "").strip()
        side = str(entry.get("side", "") or "").upper()
        question = re.sub(r"\s+", " ", str(entry.get("question", "") or "").strip()).lower()
        city = re.sub(r"\s+", " ", str(entry.get("city", "") or "").strip()).lower()
        market_date = str(entry.get("date", "") or "").strip()
        if token_id:
            aliases.append(f"token:{token_id}|date:{market_date}|side:{side}")
        if question:
            aliases.append(f"question:{question}|date:{market_date}|side:{side}")
        if city or market_date:
            aliases.append(f"market:{city}|date:{market_date}|side:{side}")
        deduped = []
        for alias in aliases:
            if alias and alias not in deduped:
                deduped.append(alias)
        return deduped
    parse_city_fn = globals().get("parse_city_from_title")
    if not callable(parse_city_fn):
        def parse_city_fn(title):
            match = re.search(r"temperature in (.+?) (?:be |between |\d)", str(title or ""), re.IGNORECASE)
            return match.group(1).strip() if match else "?"

    portfolio_lookup = {}
    portfolio_states = {}
    unmatched_portfolio_records = []
    if isinstance(portfolio, dict):
        for bucket in ["active", "resolved_won", "dead"]:
            for pos in portfolio.get(bucket, []) or []:
                entry = {
                    "token_id": pos.get("asset", ""),
                    "question": pos.get("title", ""),
                    "city": parse_city_fn(pos.get("title", "")),
                    "side": pos.get("outcome", ""),
                    "date": pos.get("endDate", ""),
                }
                alias_keys = _position_alias_keys(entry)
                if not alias_keys:
                    continue
                state = {
                    "alias_keys": alias_keys,
                    "primary_key": alias_keys[0],
                    "bucket": bucket,
                    "asset": pos.get("asset", ""),
                    "title": pos.get("title", ""),
                    "side": str(pos.get("outcome", "") or "").upper(),
                    "date": pos.get("endDate", ""),
                    "cur_price": _to_lifecycle_float(pos.get("curPrice")),
                    "current_value": _to_lifecycle_float(pos.get("currentValue"), 2),
                    "cash_pnl": _to_lifecycle_float(pos.get("cashPnl"), 2),
                    "pct_pnl": _to_lifecycle_float(pos.get("percentPnl"), 2),
                    "shares": _to_lifecycle_float(pos.get("size")),
                    "avg_price": _to_lifecycle_float(pos.get("avgPrice")),
                    "initial_value": _to_lifecycle_float(pos.get("initialValue"), 2),
                    "redeemable": bool(pos.get("redeemable")),
                    "realized_pnl": _to_lifecycle_float(pos.get("realizedPnl"), 2),
                }
                existing_state = portfolio_lookup.get(alias_keys[0])
                if existing_state is None or state["bucket"] == "resolved_won":
                    portfolio_states[state["primary_key"]] = state
                    for alias in alias_keys:
                        portfolio_lookup[alias] = state

    known_position_keys = {
        alias
        for record in records
        if isinstance(record, dict)
        for alias in _position_alias_keys(record)
    }

    for pos in portfolio_states.values():
        position_key = pos.get("primary_key")
        if not position_key:
            continue
        if any(alias in known_position_keys for alias in pos.get("alias_keys", [])):
            continue
        synthetic = {
            "id": f"portfolio::{position_key}",
            "position_key": position_key,
            "label": pos.get("title", ""),
            "token_id": pos.get("asset", ""),
            "question": pos.get("title", ""),
            "city": parse_city_fn(pos.get("title", "")),
            "side": pos.get("side", ""),
            "date": pos.get("date", ""),
            "condition": "",
            "status": "open" if pos.get("bucket") == "active" else "closed",
            "opened_at": "",
            "last_buy_at": "",
            "closed_at": "",
            "buy_count": 0,
            "total_amount": pos.get("initial_value") or 0.0,
            "total_shares": pos.get("shares") or 0.0,
            "avg_entry_price": pos.get("avg_price"),
            "trader_confirmed": [],
            "bot_version_opened": "",
            "bot_version_closed": "",
            "entry_context": {},
            "latest_entry_context": {},
            "close_context": {},
            "buys": [],
            "timeline": [],
            "exit_attempts": [],
            "position_snapshots": [],
            "market_observations": [],
            "position_stats": {
                "max_cur_price_open": None,
                "min_cur_price_open": None,
                "max_pct_pnl_open": None,
                "min_pct_pnl_open": None,
                "max_current_value_open": None,
                "last_snapshot_at": "",
            },
            "post_exit_analysis": {
                "market_seen_after_close": False,
                "observations_after_close": 0,
                "last_price_after_close": None,
                "max_price_after_close": None,
                "min_price_after_close": None,
                "reached_98_after_close": False,
                "first_reached_98_after_close_at": "",
                "upside_left_cash_peak": None,
                "upside_left_pct_peak": None,
                "drawdown_avoided_cash_peak": None,
                "drawdown_avoided_pct_peak": None,
            },
            "history_sources": {
                "performance": False,
                "postmortem": False,
                "reconstructed": True,
                "portfolio": True,
            },
            "last_activity_at": "",
        }
        if pos.get("avg_price") is not None or pos.get("shares") is not None:
            synthetic["entry_context"] = {
                "timestamp": "",
                "price": pos.get("avg_price"),
                "amount": pos.get("initial_value"),
                "shares": pos.get("shares"),
            }
            synthetic["latest_entry_context"] = dict(synthetic["entry_context"])
        if pos.get("bucket") == "active":
            synthetic["position_snapshots"].append({
                "timestamp": "",
                "source": "portfolio_snapshot",
                "stage": "dashboard",
                "cur_price": pos.get("cur_price"),
                "current_value": pos.get("current_value"),
                "pct_pnl": pos.get("pct_pnl"),
                "cash_pnl": pos.get("cash_pnl"),
                "size": pos.get("shares"),
                "avg_price": pos.get("avg_price"),
                "outcome": pos.get("side", ""),
            })
        else:
            close_action = "RESOLVED_WIN" if pos.get("bucket") == "resolved_won" else "LOSS_TOTAL"
            close_reason = "market_resolved_yes" if close_action == "RESOLVED_WIN" else "portfolio_dead_residual"
            synthetic["close_context"] = {
                "close_action": close_action,
                "close_reason": close_reason,
                "close_subtype": close_reason,
                "close_price": 1.0 if close_action == "RESOLVED_WIN" else pos.get("cur_price"),
                "close_shares": pos.get("shares"),
                "return_est": pos.get("current_value"),
                "pnl_cash": pos.get("cash_pnl"),
                "pnl_pct": pos.get("pct_pnl"),
                "order_id": "",
                "timestamp": "",
                "bot_version": "",
            }
        synthetic["label"] = _trade_lifecycle_label(synthetic)
        synthetic["integrity"] = _build_trade_lifecycle_record_integrity(synthetic)
        unmatched_portfolio_records.append(synthetic)

    if unmatched_portfolio_records:
        records = records + unmatched_portfolio_records
        summary = (
            summary_builder(records)
            if callable(summary_builder)
            else payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
        )
        integrity_summary = (
            integrity_builder(records)
            if callable(integrity_builder)
            else payload.get("integrity", {}) if isinstance(payload.get("integrity"), dict) else {}
        )

    resolved_side_by_market = {}
    for record in records:
        market_key = market_key_fn(record)
        side = str(record.get("side", "") or "").upper()
        action = str((record.get("close_context") or {}).get("close_action", "") or "")
        if market_key and side and action == "RESOLVED_WIN":
            resolved_side_by_market[market_key] = side
    for state in portfolio_lookup.values():
        if state.get("bucket") != "resolved_won":
            continue
        market_key = market_key_fn({
            "token_id": state.get("asset", ""),
            "question": state.get("title", ""),
            "city": parse_city_fn(state.get("title", "")),
            "date": state.get("date", ""),
        })
        side = str(state.get("side", "") or "").upper()
        if market_key and side:
            resolved_side_by_market[market_key] = side

    def _fmt_cash(value):
        number = _to_lifecycle_float(value, 2)
        if number is None:
            return "n/d"
        return f"${number:+.2f}"

    def _fmt_cash_plain(value):
        number = _to_lifecycle_float(value, 2)
        if number is None:
            return "n/d"
        return f"${number:.2f}"

    def _fmt_pct(value):
        number = _to_lifecycle_float(value, 1)
        if number is None:
            return "n/d"
        return f"{number:.1f}%"

    def _fmt_cents(value):
        number = _to_lifecycle_float(value, 1)
        if number is None:
            return "n/d"
        return f"{number:+.1f}c"

    def _fmt_ts(value):
        text = str(value or "").strip()
        if not text:
            return "n/d"
        text = text.replace("T", " ")
        if text.endswith("+00:00"):
            return f"{text[:16]} UTC"
        return text[:16]

    def _close_bucket(record):
        close_context = record.get("close_context") or {}
        reason = str(close_context.get("close_reason", "") or "")
        action = str(close_context.get("close_action", "") or "")
        if reason in {"take_profit", "take_profit_intra"}:
            return "take_profit"
        if reason in {"stop_loss", "stop_loss_intra"}:
            return "stop_loss"
        if reason == "reeval":
            return "reeval"
        if action == "LOSS_TOTAL":
            return "loss_total"
        if action == "RESOLVED_WIN":
            return "resolved_win"
        return "other"

    bucket_meta = {
        "take_profit": {"label": "Take-profit", "tag": "TP", "badge": "good"},
        "reeval": {"label": "Re-eval", "tag": "RV", "badge": "accent"},
        "stop_loss": {"label": "Stop-loss", "tag": "SL", "badge": "warn"},
        "loss_total": {"label": "LOSS_TOTAL", "tag": "LT", "badge": "bad"},
        "resolved_win": {"label": "Resolucion", "tag": "WIN", "badge": "good"},
        "other": {"label": "Otro cierre", "tag": "Otro", "badge": "muted"},
    }

    def _bucket_meta(record):
        bucket = _close_bucket(record)
        return bucket, bucket_meta.get(bucket, bucket_meta["other"])

    def _quality_meta(integrity):
        if integrity.get("partial_historical_record"):
            return {
                "label": "Historico parcial",
                "note": "faltan token, buys y entrada",
                "badge": "muted",
                "sort_key": 2,
            }
        if integrity.get("close_only_record"):
            return {
                "label": "Cierre heredado",
                "note": "solo se conserva la salida",
                "badge": "warn",
                "sort_key": 1,
            }
        if integrity.get("missing_entry_context") or integrity.get("missing_buy_history"):
            return {
                "label": "Incompleta",
                "note": "falta parte del contexto de entrada",
                "badge": "warn",
                "sort_key": 1,
            }
        return {
            "label": "Completa",
            "note": "lista para lectura operativa",
            "badge": "good",
            "sort_key": 0,
        }

    def _result_meta(status, close_context, pnl_cash, integrity):
        action = str(close_context.get("close_action", "") or "")
        if status == "open":
            return {"label": "Abierta", "badge": "accent", "kind": "open"}
        if status == "pending_exit":
            return {"label": "Pending exit", "badge": "warn", "kind": "pending"}
        if status == "exit_failed":
            return {"label": "Exit failed", "badge": "bad", "kind": "failed"}
        if action == "LOSS_TOTAL":
            return {"label": "Perdida total", "badge": "bad", "kind": "loss_total"}
        if action == "RESOLVED_WIN":
            return {"label": "Ganada por resolucion", "badge": "good", "kind": "win"}
        if pnl_cash is not None and pnl_cash > 0:
            return {"label": "Ganada", "badge": "good", "kind": "win"}
        if pnl_cash is not None and pnl_cash < 0:
            if integrity.get("partial_historical_record") or integrity.get("close_only_record"):
                return {"label": "Perdida legacy", "badge": "warn", "kind": "legacy_loss"}
            return {"label": "Perdida SELL", "badge": "bad", "kind": "sell_loss"}
        if integrity.get("partial_historical_record") or integrity.get("close_only_record"):
            return {"label": "Legacy parcial", "badge": "warn", "kind": "legacy"}
        return {"label": "Neutral", "badge": "muted", "kind": "neutral"}

    def _effective_exit_price(record):
        close_context = record.get("close_context") or {}
        close_price = _to_lifecycle_float(close_context.get("close_price"))
        if close_price is not None:
            return close_price

        action = str(close_context.get("close_action", "") or "")
        if action == "RESOLVED_WIN":
            return 1.0
        if action == "LOSS_TOTAL":
            return 0.0

        snapshots = record.get("position_snapshots", []) or []
        if snapshots:
            return _to_lifecycle_float(snapshots[-1].get("cur_price"))
        return None

    def _portfolio_state_for_record(record):
        return portfolio_lookup.get(record.get("position_key") or position_key_fn(record))

    def _portfolio_claim_note(record, portfolio_state):
        if not isinstance(portfolio_state, dict):
            return ""
        bucket = portfolio_state.get("bucket")
        redeemable = bool(portfolio_state.get("redeemable"))
        realized = _to_lifecycle_float(portfolio_state.get("realized_pnl"), 2)
        current_value = _to_lifecycle_float(portfolio_state.get("current_value"), 2)
        action = str((record.get("close_context") or {}).get("close_action", "") or "")
        if bucket == "resolved_won":
            if redeemable:
                return "claim pendiente (wallet redeemable=true)"
            if realized is not None and abs(realized) > 1e-9:
                return "claim/redeem ya impactado en wallet"
            return "mercado resuelto; claim aun no confirmado"
        if bucket == "dead" and redeemable:
            return "wallet redeemable=true; revisar claim/manual"
        if bucket == "dead" and action == "SELL" and current_value is not None and current_value < 0.10:
            return f"tras la salida quedo residuo micro {_fmt_cash_plain(current_value)}"
        return ""

    def _after_close_note(record, portfolio_state):
        post_exit = record.get("post_exit_analysis") or {}
        notes = []
        if post_exit.get("market_seen_after_close"):
            obs = int(post_exit.get("observations_after_close", 0) or 0)
            notes.append(f"{obs} obs post-salida")
        elif record.get("status") == "open":
            notes.append("sigue abierta")
        else:
            notes.append("sin obs")

        market_key = market_key_fn(record)
        winning_side = resolved_side_by_market.get(market_key)
        record_side = str(record.get("side", "") or "").upper()
        action = str((record.get("close_context") or {}).get("close_action", "") or "")
        if winning_side and record_side and winning_side != record_side and action == "LOSS_TOTAL":
            notes.append(f"mercado termino del lado {winning_side}")

        if isinstance(portfolio_state, dict):
            bucket = portfolio_state.get("bucket")
            if bucket == "active":
                notes.append("activa en cartera")
            elif bucket == "resolved_won":
                notes.append("resuelta en cartera")
            elif bucket == "dead":
                notes.append("cartera muerta")

        claim_note = _portfolio_claim_note(record, portfolio_state)
        if claim_note:
            notes.append(claim_note)
        return " | ".join(notes)

    def _entry_condition(record, integrity, portfolio_state=None):
        entry = record.get("latest_entry_context") or record.get("entry_context") or {}
        if not entry.get("timestamp") and isinstance(portfolio_state, dict) and portfolio_state.get("avg_price") is not None:
            parts = [f"entrada reconstruida {portfolio_state.get('avg_price') * 100:.1f}c"]
            initial_value = _to_lifecycle_float(portfolio_state.get("initial_value"), 2)
            shares = _to_lifecycle_float(portfolio_state.get("shares"))
            if initial_value is not None:
                parts.append(f"inversion {_fmt_cash_plain(initial_value)}")
            if shares is not None:
                parts.append(f"{shares:.4f} shares")
            parts.append("sin timestamp BUY")
            return " | ".join(parts)
        if integrity.get("partial_historical_record"):
            return "Historico parcial: faltan token, buys y datos de entrada."
        if integrity.get("close_only_record"):
            return "Cierre heredado: solo se conserva la salida, no la entrada completa."
        if not entry.get("timestamp"):
            return "Entrada reconstruida sin timestamp claro."

        parts = []
        entry_price = _to_lifecycle_float(entry.get("price"))
        if entry_price is not None:
            parts.append(f"entrada {entry_price * 100:.1f}c")
        edge_pct = _to_lifecycle_float(entry.get("edge_pct"), 1)
        if edge_pct is not None:
            parts.append(f"edge {edge_pct:.1f}%")
        forecast_max = _to_lifecycle_float(entry.get("forecast_max"), 1)
        if forecast_max is not None:
            parts.append(f"forecast {forecast_max:.1f}C")
        our_prob = _to_lifecycle_float(entry.get("our_prob"), 1)
        mkt_price = _to_lifecycle_float(entry.get("mkt_price"), 1)
        if our_prob is not None and mkt_price is not None:
            parts.append(f"nuestro {our_prob:.1f}% vs mercado {mkt_price:.1f}c")
        elif our_prob is not None:
            parts.append(f"nuestro {our_prob:.1f}%")
        elif mkt_price is not None:
            parts.append(f"mercado {mkt_price:.1f}c")

        traders = entry.get("trader_confirmed") or record.get("trader_confirmed") or []
        if traders:
            suffix = "..." if len(traders) > 2 else ""
            parts.append(f"traders {', '.join(traders[:2])}{suffix}")

        cycle_number = entry.get("cycle_number")
        logic_cycle_number = entry.get("logic_cycle_number")
        if cycle_number is not None and logic_cycle_number is not None:
            parts.append(f"ciclo {cycle_number} / serie {logic_cycle_number}")
        elif cycle_number is not None:
            parts.append(f"ciclo {cycle_number}")

        return " | ".join(parts) if parts else "Entrada registrada sin detalle adicional."

    def _exit_condition(record, integrity, portfolio_state=None):
        status = str(record.get("status", "") or "")
        close_context = record.get("close_context") or {}
        reason = str(close_context.get("close_reason", "") or "")
        action = str(close_context.get("close_action", "") or "")
        attempts = record.get("exit_attempts", []) or []
        last_attempt = attempts[-1] if attempts else {}

        if status == "open":
            snapshots = record.get("position_snapshots", []) or []
            if snapshots:
                last_snapshot = snapshots[-1]
                cur_price = _to_lifecycle_float(last_snapshot.get("cur_price"))
                pct_pnl = _to_lifecycle_float(last_snapshot.get("pct_pnl"), 1)
                parts = ["Posicion abierta"]
                if cur_price is not None:
                    parts.append(f"cur {cur_price * 100:.1f}c")
                if pct_pnl is not None:
                    parts.append(f"PnL {pct_pnl:+.1f}%")
                return " | ".join(parts)
            return "Posicion abierta; aun sin salida."

        rule_map = {
            "take_profit": "TP mecanico: PnL >= +40%",
            "take_profit_intra": "TP intra: PnL >= +40%",
            "stop_loss": "SL mecanico: PnL <= -25%",
            "stop_loss_intra": "SL intra: PnL <= -25%",
            "reeval": "Re-eval: edge recalculado < -3%",
            "micro_position_unsellable": "Micro posicion incanjeable / perdida total",
            "market_resolved_yes": "Mercado resuelto a favor",
            "market_resolved_no": "Mercado resuelto en contra",
            "portfolio_dead_residual": "Solo visible hoy en cartera muerta",
        }
        action_map = {
            "SELL": "Salida vendida",
            "SELL_FAILED": "Salida fallida",
            "LOSS_TOTAL": "Perdida total",
            "RESOLVED_WIN": "Mercado resuelto a favor",
        }

        parts = []
        if reason:
            parts.append(rule_map.get(reason, reason))
        elif action:
            parts.append(action_map.get(action, action))

        trigger_price = _to_lifecycle_float(last_attempt.get("trigger_price"))
        if trigger_price is not None:
            parts.append(f"trigger {trigger_price * 100:.1f}c")
        limit_price = _to_lifecycle_float(last_attempt.get("limit_price"))
        if limit_price is not None:
            parts.append(f"limite {limit_price * 100:.1f}c")
        decision_note = str(last_attempt.get("decision_note", "") or "").strip()
        if decision_note:
            parts.append(decision_note)

        claim_note = _portfolio_claim_note(record, portfolio_state)
        if claim_note and action == "RESOLVED_WIN":
            parts.append(claim_note)
        elif claim_note and action == "SELL":
            parts.append(claim_note)

        if integrity.get("close_only_record") and not attempts:
            parts.append("registro heredado")

        if not parts and integrity.get("partial_historical_record"):
            return "Cierre parcial heredado sin regla explicitada."
        return " | ".join(parts) if parts else "Salida cerrada sin detalle adicional."

    observed_rows = []
    for record in records:
        integrity = record.get("integrity") or _build_trade_lifecycle_record_integrity(record)
        if record.get("status") != "closed" or not integrity.get("analysis_ready"):
            continue

        close_context = record.get("close_context") or {}
        post_exit = record.get("post_exit_analysis") or {}
        close_price = _to_lifecycle_float(close_context.get("close_price"))
        close_shares = _to_lifecycle_float(close_context.get("close_shares"))
        if (
            not post_exit.get("market_seen_after_close")
            or close_price is None
            or close_shares is None
            or close_shares <= 0
        ):
            continue

        close_value = round(close_price * close_shares, 2)
        upside_left = _to_lifecycle_float(post_exit.get("upside_left_cash_peak"), 2) or 0.0
        drawdown_avoided = _to_lifecycle_float(post_exit.get("drawdown_avoided_cash_peak"), 2) or 0.0
        opportunity_total = close_value + upside_left + drawdown_avoided
        efficiency_pct = (
            round(((close_value + drawdown_avoided) / opportunity_total) * 100, 1)
            if opportunity_total > 0
            else None
        )
        harvest_pct = (
            round((close_value / (close_value + upside_left)) * 100, 1)
            if (close_value + upside_left) > 0
            else None
        )
        protection_pct = (
            round((drawdown_avoided / (close_value + drawdown_avoided)) * 100, 1)
            if (close_value + drawdown_avoided) > 0 and drawdown_avoided > 0
            else None
        )
        bucket, reason_meta = _bucket_meta(record)
        net_delta_cash = round(drawdown_avoided - upside_left, 2)
        if upside_left > 0 and drawdown_avoided <= 0:
            verdict_label = "Upside dejado"
            verdict_badge = "bad"
        elif drawdown_avoided > 0 and upside_left <= 0:
            verdict_label = "Downside evitado"
            verdict_badge = "good"
        elif upside_left > 0 and drawdown_avoided > 0:
            verdict_label = "Mixto"
            verdict_badge = "warn"
        else:
            verdict_label = "Neutral"
            verdict_badge = "muted"

        short_label = str(record.get("city", "?") or "?")
        if bucket == "take_profit":
            short_label = f"{short_label} TP"
        elif bucket == "reeval":
            short_label = f"{short_label} RV"
        elif bucket == "stop_loss":
            short_label = f"{short_label} SL"
        elif bucket == "loss_total":
            short_label = f"{short_label} LT"
        elif bucket == "resolved_win":
            short_label = f"{short_label} WIN"

        observed_rows.append({
            "id": record.get("id"),
            "label": _trade_lifecycle_label(record),
            "short_label": short_label[:18],
            "city": record.get("city", "?"),
            "close_bucket": bucket,
            "close_reason_label": reason_meta["label"],
            "close_reason_tag": reason_meta["tag"],
            "closed_at": record.get("closed_at") or close_context.get("timestamp") or "",
            "closed_at_display": _fmt_ts(record.get("closed_at") or close_context.get("timestamp")),
            "close_value": close_value,
            "close_value_display": _fmt_cash_plain(close_value),
            "close_price": close_price,
            "close_price_display": f"{close_price:.2f}",
            "close_shares": close_shares,
            "upside_left_cash_peak": upside_left,
            "upside_left_display": _fmt_cash_plain(upside_left),
            "drawdown_avoided_cash_peak": drawdown_avoided,
            "drawdown_avoided_display": _fmt_cash_plain(drawdown_avoided),
            "efficiency_pct": efficiency_pct,
            "efficiency_display": _fmt_pct(efficiency_pct),
            "harvest_pct": harvest_pct,
            "harvest_display": _fmt_pct(harvest_pct),
            "protection_pct": protection_pct,
            "protection_display": _fmt_pct(protection_pct),
            "net_delta_cash": net_delta_cash,
            "net_delta_display": _fmt_cash(net_delta_cash),
            "reached_98_after_close": bool(post_exit.get("reached_98_after_close")),
            "verdict_label": verdict_label,
            "verdict_badge": verdict_badge,
            "score_badge": (
                "good" if efficiency_pct is not None and efficiency_pct >= 85
                else "accent" if efficiency_pct is not None and efficiency_pct >= 70
                else "warn" if efficiency_pct is not None and efficiency_pct >= 55
                else "bad" if efficiency_pct is not None
                else "muted"
            ),
        })

    observed_rows.sort(key=lambda item: item.get("closed_at") or "", reverse=True)

    observed_count = len(observed_rows)
    total_closed = int(summary.get("closed_positions", 0) or 0)
    tracked_positions = int(summary.get("tracked_positions", len(records)) or len(records))
    analysis_ready_records = int(integrity_summary.get("analysis_ready_records", 0) or 0)
    partial_historical_records = int(integrity_summary.get("partial_historical_records", 0) or 0)
    close_only_records = int(integrity_summary.get("close_only_records", 0) or 0)
    close_only_only_records = max(0, close_only_records - partial_historical_records)
    legacy_review_records = partial_historical_records + close_only_only_records
    close_value_total = round(sum(item["close_value"] for item in observed_rows), 2)
    upside_left_total = round(sum(item["upside_left_cash_peak"] for item in observed_rows), 2)
    drawdown_avoided_total = round(sum(item["drawdown_avoided_cash_peak"] for item in observed_rows), 2)
    opportunity_total = close_value_total + upside_left_total + drawdown_avoided_total
    score_pct = (
        round(((close_value_total + drawdown_avoided_total) / opportunity_total) * 100, 1)
        if opportunity_total > 0
        else None
    )
    harvest_candidates = [item for item in observed_rows if item["close_bucket"] in {"take_profit", "reeval"} or item["upside_left_cash_peak"] > 0]
    harvest_value_total = round(sum(item["close_value"] for item in harvest_candidates), 2)
    harvest_upside_total = round(sum(item["upside_left_cash_peak"] for item in harvest_candidates), 2)
    harvest_efficiency_pct = (
        round((harvest_value_total / (harvest_value_total + harvest_upside_total)) * 100, 1)
        if (harvest_value_total + harvest_upside_total) > 0
        else None
    )
    protection_candidates = [item for item in observed_rows if item["close_bucket"] in {"stop_loss", "reeval"} or item["drawdown_avoided_cash_peak"] > 0]
    protection_value_total = round(sum(item["close_value"] for item in protection_candidates), 2)
    protection_drawdown_total = round(sum(item["drawdown_avoided_cash_peak"] for item in protection_candidates), 2)
    protection_efficiency_pct = (
        round((protection_drawdown_total / (protection_value_total + protection_drawdown_total)) * 100, 1)
        if (protection_value_total + protection_drawdown_total) > 0 and protection_drawdown_total > 0
        else None
    )

    maturity_goal = 12
    maturity_pct = min(100, round((observed_count / maturity_goal) * 100)) if maturity_goal > 0 else 0
    if observed_count >= 12:
        confidence_label = "Alta"
        confidence_badge = "good"
    elif observed_count >= 6:
        confidence_label = "Media"
        confidence_badge = "accent"
    elif observed_count >= 3:
        confidence_label = "Baja"
        confidence_badge = "warn"
    else:
        confidence_label = "Muy baja"
        confidence_badge = "muted"

    if observed_count == 0:
        headline = "Sin cierres observados todavia"
        summary_text = (
            "trade_lifecycle ya esta listo, pero aun no hay cierres con trayectoria post-salida "
            "y precio util para medir si el bot capturo valor o dejo upside."
        )
        score_badge = "muted"
    else:
        net_delta_total = round(drawdown_avoided_total - upside_left_total, 2)
        if upside_left_total > drawdown_avoided_total + 0.5:
            headline = "La muestra observada sugiere salidas prematuras"
        elif drawdown_avoided_total > upside_left_total + 0.5:
            headline = "La muestra observada sugiere buena proteccion"
        else:
            headline = "La muestra observada esta equilibrada"

        summary_text = (
            f"{observed_count} cierre(s) con mercado observado despues de salir. "
            f"Upside dejado { _fmt_cash_plain(upside_left_total) } | downside evitado { _fmt_cash_plain(drawdown_avoided_total) } | "
            f"neto { _fmt_cash(net_delta_total) }. "
            "Usa esto como evidencia operativa; aun no equivale a una orden de cambiar reglas."
        )
        score_badge = (
            "good" if score_pct is not None and score_pct >= 85
            else "accent" if score_pct is not None and score_pct >= 70
            else "warn" if score_pct is not None and score_pct >= 55
            else "bad"
        )

    breakdown_rows = []
    for bucket in ["take_profit", "reeval", "stop_loss"]:
        meta = bucket_meta[bucket]
        bucket_rows = [item for item in observed_rows if item["close_bucket"] == bucket]
        total_bucket = sum(1 for record in records if record.get("status") == "closed" and _close_bucket(record) == bucket)
        bucket_upside = round(sum(item["upside_left_cash_peak"] for item in bucket_rows), 2)
        bucket_drawdown = round(sum(item["drawdown_avoided_cash_peak"] for item in bucket_rows), 2)
        avg_eff = (
            round(sum(item["efficiency_pct"] for item in bucket_rows if item["efficiency_pct"] is not None) / len(bucket_rows), 1)
            if bucket_rows
            else None
        )
        if not bucket_rows:
            signal_label = "Sin muestra"
            signal_badge = "muted"
        elif bucket_upside > bucket_drawdown + 0.25:
            signal_label = "Revisar captura"
            signal_badge = "bad"
        elif bucket_drawdown > bucket_upside + 0.25:
            signal_label = "Protege bien"
            signal_badge = "good"
        else:
            signal_label = "Mixto"
            signal_badge = "warn"
        breakdown_rows.append({
            "label": meta["label"],
            "tag": meta["tag"],
            "total_count": total_bucket,
            "observed_count": len(bucket_rows),
            "coverage_display": f"{len(bucket_rows)}/{total_bucket}" if total_bucket else f"{len(bucket_rows)}/0",
            "avg_efficiency_display": _fmt_pct(avg_eff),
            "upside_left_display": _fmt_cash_plain(bucket_upside),
            "drawdown_avoided_display": _fmt_cash_plain(bucket_drawdown),
            "signal_label": signal_label,
            "signal_badge": signal_badge,
        })

    top_upside_rows = sorted(
        [item for item in observed_rows if item["upside_left_cash_peak"] > 0],
        key=lambda item: item["upside_left_cash_peak"],
        reverse=True,
    )[:5]
    top_protection_rows = sorted(
        [item for item in observed_rows if item["drawdown_avoided_cash_peak"] > 0],
        key=lambda item: item["drawdown_avoided_cash_peak"],
        reverse=True,
    )[:5]

    timeline_points = []
    for item in reversed(observed_rows[:8]):
        height_pct = 12 if item["efficiency_pct"] is None else max(12, min(100, round(item["efficiency_pct"])))
        timeline_points.append({
            "label": item["label"],
            "short_label": item["short_label"],
            "score_display": item["efficiency_display"],
            "height_pct": height_pct,
            "badge": item["score_badge"],
            "closed_at_display": item["closed_at_display"],
            "reason_tag": item["close_reason_tag"],
        })

    trade_rows = []
    won_count = 0
    lost_count = 0
    open_count = 0
    pending_count = 0
    won_cash_total = 0.0
    lost_cash_total = 0.0
    net_pnl_total = 0.0
    sell_loss_count = 0
    sell_loss_cash_total = 0.0
    loss_total_count = 0
    loss_total_cash_total = 0.0

    for record in records:
        integrity = record.get("integrity") or _build_trade_lifecycle_record_integrity(record)
        quality_meta = _quality_meta(integrity)
        portfolio_state = _portfolio_state_for_record(record)
        status = str(record.get("status", "") or "")
        close_context = record.get("close_context") or {}
        post_exit = record.get("post_exit_analysis") or {}
        bucket, bucket_display_meta = _bucket_meta(record)
        avg_entry_price = _to_lifecycle_float(record.get("avg_entry_price"))
        effective_exit_price = _effective_exit_price(record)
        cents_result = (
            round((effective_exit_price - avg_entry_price) * 100, 1)
            if effective_exit_price is not None and avg_entry_price is not None
            else None
        )

        close_price = _to_lifecycle_float(close_context.get("close_price"))
        close_shares = _to_lifecycle_float(close_context.get("close_shares"))
        close_value = (
            round(close_price * close_shares, 2)
            if close_price is not None and close_shares is not None and close_shares > 0
            else None
        )
        snapshots = record.get("position_snapshots", []) or []
        latest_snapshot = snapshots[-1] if snapshots else {}
        current_value = _to_lifecycle_float(latest_snapshot.get("current_value"), 2)
        if current_value is None and isinstance(portfolio_state, dict):
            current_value = _to_lifecycle_float(portfolio_state.get("current_value"), 2)
        trade_value = close_value if close_value is not None else current_value
        if trade_value is None:
            trade_value = _to_lifecycle_float(record.get("total_amount"), 2)
        if trade_value is None and isinstance(portfolio_state, dict):
            trade_value = _to_lifecycle_float(portfolio_state.get("initial_value"), 2)

        pnl_cash = _to_lifecycle_float(close_context.get("pnl_cash"), 2)
        pnl_pct = _to_lifecycle_float(close_context.get("pnl_pct"), 2)
        if status == "open":
            pnl_cash = _to_lifecycle_float(latest_snapshot.get("cash_pnl"), 2)
            pnl_pct = _to_lifecycle_float(latest_snapshot.get("pct_pnl"), 2)
            if pnl_cash is None and isinstance(portfolio_state, dict):
                pnl_cash = _to_lifecycle_float(portfolio_state.get("cash_pnl"), 2)
            if pnl_pct is None and isinstance(portfolio_state, dict):
                pnl_pct = _to_lifecycle_float(portfolio_state.get("pct_pnl"), 2)
        elif pnl_cash is None and isinstance(portfolio_state, dict):
            pnl_cash = _to_lifecycle_float(portfolio_state.get("cash_pnl"), 2)
            pnl_pct = _to_lifecycle_float(portfolio_state.get("pct_pnl"), 2)
        result_meta = _result_meta(status, close_context, pnl_cash, integrity)
        result_label = result_meta["label"]
        result_badge = result_meta["badge"]
        result_kind = result_meta["kind"]
        after_close_display = _after_close_note(record, portfolio_state)

        if status == "open":
            bucket_label = "Abierta"
        elif status == "pending_exit":
            bucket_label = "Pending exit"
        elif status == "exit_failed":
            bucket_label = "Exit failed"
        else:
            bucket_label = bucket_display_meta["label"]

        if result_kind == "open":
            open_count += 1
        elif result_kind == "pending":
            pending_count += 1
        elif result_kind == "win":
            won_count += 1
            if pnl_cash is not None and pnl_cash > 0:
                won_cash_total += pnl_cash
        elif result_kind == "sell_loss":
            lost_count += 1
            sell_loss_count += 1
            if pnl_cash is not None and pnl_cash < 0:
                lost_cash_total += abs(pnl_cash)
                sell_loss_cash_total += abs(pnl_cash)
        elif result_kind == "loss_total":
            lost_count += 1
            loss_total_count += 1
            if pnl_cash is not None and pnl_cash < 0:
                lost_cash_total += abs(pnl_cash)
                loss_total_cash_total += abs(pnl_cash)
        elif result_kind == "legacy_loss":
            lost_count += 1
            if pnl_cash is not None and pnl_cash < 0:
                lost_cash_total += abs(pnl_cash)

        if pnl_cash is not None:
            net_pnl_total += pnl_cash

        trade_rows.append({
            "id": record.get("id"),
            "label": _trade_lifecycle_label(record),
            "status": status,
            "status_badge": result_badge if status != "open" else "accent",
            "status_label": result_label,
            "bucket_label": bucket_label,
            "entry_condition": _entry_condition(record, integrity, portfolio_state=portfolio_state),
            "exit_condition": _exit_condition(record, integrity, portfolio_state=portfolio_state),
            "opened_at_display": _fmt_ts(record.get("opened_at")),
            "closed_at_display": _fmt_ts(record.get("closed_at") or close_context.get("timestamp")),
            "pnl_cash": pnl_cash,
            "pnl_cash_display": _fmt_cash(pnl_cash),
            "pnl_pct": pnl_pct,
            "pnl_pct_display": _fmt_pct(pnl_pct),
            "trade_value_display": _fmt_cash_plain(trade_value),
            "cents_result": cents_result,
            "cents_result_display": _fmt_cents(cents_result),
            "left_to_gain_display": _fmt_cash_plain(_to_lifecycle_float(post_exit.get("upside_left_cash_peak"), 2)),
            "downside_avoided_display": _fmt_cash_plain(_to_lifecycle_float(post_exit.get("drawdown_avoided_cash_peak"), 2)),
            "observed_after_close": bool(post_exit.get("market_seen_after_close")),
            "observed_after_close_display": after_close_display,
            "after_close_display": after_close_display,
            "analysis_ready": bool(integrity.get("analysis_ready")),
            "integrity_note": quality_meta["label"],
            "integrity_badge": quality_meta["badge"],
            "quality_sort": quality_meta["sort_key"],
            "sort_key": (
                record.get("last_activity_at")
                or record.get("closed_at")
                or close_context.get("timestamp")
                or record.get("opened_at")
                or ""
            ),
        })

    trade_rows.sort(key=lambda item: item.get("sort_key") or "", reverse=True)
    trade_rows.sort(key=lambda item: item.get("quality_sort", 0))
    total_cards = [
        {"label": "Operaciones totales", "value": str(tracked_positions), "detail": f"{total_closed} cerradas | {open_count} abiertas | {pending_count} pending"},
        {"label": "TP", "value": str(int(summary.get("take_profit_closes", 0) or 0)), "detail": "cierres por take-profit"},
        {"label": "SL", "value": str(int(summary.get("stop_loss_closes", 0) or 0)), "detail": "solo SELL por stop-loss"},
        {"label": "LOSS_TOTAL", "value": str(loss_total_count), "detail": _fmt_cash_plain(loss_total_cash_total) if loss_total_cash_total > 0 else "posiciones muertas/no vendibles"},
        {"label": "Ganadas", "value": str(won_count), "detail": _fmt_cash_plain(won_cash_total)},
        {"label": "SELL negativos", "value": str(sell_loss_count), "detail": _fmt_cash_plain(sell_loss_cash_total) if sell_loss_count else "sin SELL cerrados en negativo"},
        {"label": "Legacy/parcial", "value": str(legacy_review_records), "detail": f"{partial_historical_records} parciales | {close_only_only_records} close-only"},
        {"label": "PnL neto", "value": _fmt_cash(net_pnl_total), "detail": "cash realizado/estimado por trade"},
        {"label": "Dejado de ganar", "value": _fmt_cash_plain(upside_left_total), "detail": "solo muestra observada"},
        {"label": "Protegido", "value": _fmt_cash_plain(drawdown_avoided_total), "detail": "solo muestra observada"},
    ]

    return {
        "headline": headline,
        "summary": summary_text,
        "score_pct": score_pct or 0,
        "score_display": _fmt_pct(score_pct) if score_pct is not None else "n/d",
        "score_badge": score_badge,
        "sample_size": observed_count,
        "sample_display": f"{observed_count} cierre observado" if observed_count == 1 else f"{observed_count} cierres observados",
        "sample_detail": f"{observed_count}/{total_closed} cierres cerrados con trayectoria post-salida util",
        "confidence_label": confidence_label,
        "confidence_badge": confidence_badge,
        "maturity_pct": maturity_pct,
        "tracked_positions": tracked_positions,
        "closed_positions": total_closed,
        "analysis_ready_records": analysis_ready_records,
        "legacy_review_records": legacy_review_records,
        "loss_total_closes": loss_total_count,
        "sell_loss_closes": sell_loss_count,
        "harvest_efficiency_pct": harvest_efficiency_pct,
        "harvest_efficiency_display": _fmt_pct(harvest_efficiency_pct),
        "protection_efficiency_pct": protection_efficiency_pct,
        "protection_efficiency_display": _fmt_pct(protection_efficiency_pct),
        "upside_left_total_cash": upside_left_total,
        "upside_left_total_display": _fmt_cash_plain(upside_left_total),
        "drawdown_avoided_total_cash": drawdown_avoided_total,
        "drawdown_avoided_total_display": _fmt_cash_plain(drawdown_avoided_total),
        "close_value_total_cash": close_value_total,
        "close_value_total_display": _fmt_cash_plain(close_value_total),
        "quick_stats": [
            {"label": "Sample observado", "value": f"{observed_count}/{total_closed}", "detail": "cierres con mercado visto despues de salir"},
            {"label": "Eficiencia captura", "value": _fmt_pct(harvest_efficiency_pct), "detail": "cash realizado vs upside observado"},
            {"label": "Valor dejado", "value": _fmt_cash_plain(upside_left_total), "detail": "upside pico tras salir"},
            {"label": "Valor protegido", "value": _fmt_cash_plain(drawdown_avoided_total), "detail": "downside evitado tras salir"},
        ],
        "breakdown_rows": breakdown_rows,
        "top_upside_rows": top_upside_rows,
        "top_protection_rows": top_protection_rows,
        "total_cards": total_cards,
        "trade_rows": trade_rows[:40],
        "recent_rows": observed_rows[:12],
        "timeline_points": timeline_points,
        "note": (
            "Solo cuenta cierres con precio de salida util y observacion de mercado despues del cierre. "
            "La consola usa trade_lifecycle como base y lo contrasta con cartera live para distinguir SL, LOSS_TOTAL, resolucion y estado de claim/redeem sin mezclar semanticas."
        ),
    }


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
    import re as _re
    import unicodedata as _unicodedata

    events = []
    seen_keys = set()
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
                    raw_session = item.get("session", 0)
                    session_text = str(raw_session or "").strip().lower()
                    session_match = _re.search(r"(\d+)$", session_text)
                    session_number = int(session_match.group(1)) if session_match else 0
                    normalized_title = str(item.get("title", "") or "").strip().lower()
                    normalized_title = _unicodedata.normalize("NFKD", normalized_title)
                    normalized_title = "".join(
                        ch for ch in normalized_title if not _unicodedata.combining(ch)
                    )
                    normalized_title = _re.sub(r"[^a-z0-9]+", "", normalized_title)
                    dedupe_key = (
                        str(item.get("timestamp", "") or "").strip(),
                        session_number,
                        str(item.get("agent", "") or "").strip(),
                        str(item.get("type", "") or "").strip(),
                        normalized_title,
                    )
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    item["session"] = session_number
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


def _build_flagged_city_history_note(flagged_cities):
    """Build a static note for frozen low-accuracy history in shadow/dry contexts."""
    if not flagged_cities:
        return None

    flagged_names = {item.get("city", "") for item in flagged_cities if item.get("city")}
    frozen_since = ""
    if flagged_names:
        records = load_postmortem_data()
        latest_closed_at = ""
        for record in records:
            if record.get("status") != "closed":
                continue
            if record.get("city") not in flagged_names:
                continue
            closed_at = str(record.get("closed_at") or "").strip()
            if closed_at > latest_closed_at:
                latest_closed_at = closed_at
        if latest_closed_at:
            try:
                frozen_since = datetime.fromisoformat(
                    latest_closed_at.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
            except Exception:
                frozen_since = latest_closed_at[:10]

    city_list = ", ".join(
        f"{item['city']} ({item['win_rate']}%)" for item in flagged_cities
    )
    since_label = frozen_since or "fecha no disponible"
    return {
        "frozen_since": frozen_since,
        "detail": (
            f"Histórico congelado desde {since_label}. "
            f"No se promoverán sin evidencia nueva: {city_list}."
        ),
    }


def get_dashboard_alert_summary():
    """Resume alertas y riesgos operativos visibles para el panel."""
    verified_bad_min_trades = int(globals().get("ALERT_VERIFIED_BAD_MIN_TRADES", 5) or 5)
    verified_bad_max_win_rate = float(
        globals().get(
            "ALERT_VERIFIED_BAD_MAX_WIN_RATE",
            globals().get("CITY_BLOCK_WIN_RATE", 25.0),
        )
        or globals().get("CITY_BLOCK_WIN_RATE", 25.0)
    )
    active_noaa_min_cases = int(globals().get("ALERT_ACTIVE_NOAA_MIN_CASES", 3) or 3)
    shadow_join_min_signals = int(globals().get("ALERT_SHADOW_JOIN_MIN_SIGNALS", 20) or 20)
    shadow_join_min_noaa_sample = int(globals().get("ALERT_SHADOW_JOIN_MIN_NOAA_SAMPLE", 10) or 10)
    shadow_wr_min_resolved = int(globals().get("ALERT_SHADOW_WR_MIN_RESOLVED", 8) or 8)
    shadow_wr_target = float(globals().get("ALERT_SHADOW_WR_TARGET", 45.0) or 45.0)
    signals = inspect_signals_file_health()
    issue = signals.get("status", "unknown")
    audit = load_audit_data()
    city_accuracy = get_city_accuracy()
    if "get_city_policy_metrics" in globals():
        city_policy_metrics = get_city_policy_metrics(audit=audit)
    else:
        city_policy_metrics = {}
    if "build_dashboard_forecast_quality" in globals():
        forecast_quality = build_dashboard_forecast_quality(audit=audit)
    else:
        forecast_quality = {"sample_size": 0}
    if "build_dashboard_city_observation" in globals():
        city_observation = build_dashboard_city_observation(
            audit=audit,
            city_accuracy=city_accuracy,
            city_policy_metrics=city_policy_metrics,
        )
    else:
        city_observation = {"active_rows": []}
    shadow_tracking = load_shadow_city_tracking() if "load_shadow_city_tracking" in globals() else {}
    shadow_resolution_builder = globals().get("_build_shadow_noaa_resolution_stats")
    if callable(shadow_resolution_builder):
        shadow_resolution = shadow_resolution_builder(shadow_tracking, audit=audit)
    else:
        shadow_resolution = {"total_signals": 0, "matched": 0, "resolved": 0, "win_rate": 0.0}
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

    legacy_flagged_cities = [
        {
            "city": city,
            "win_rate": data["win_rate"],
            "trades": data["trades"],
            "pnl": round(data["pnl"], 2),
        }
        for city, data in city_accuracy.items()
        if data["trades"] >= verified_bad_min_trades and data["win_rate"] <= verified_bad_max_win_rate
    ]
    legacy_flagged_cities.sort(key=lambda item: (item["win_rate"], -item["trades"], item["city"]))

    flagged_cities = []
    for city, buckets in city_policy_metrics.items():
        verified = buckets.get("verified", {}) if isinstance(buckets, dict) else {}
        trades = int(verified.get("trades", 0) or 0)
        win_rate = float(verified.get("win_rate", 0.0) or 0.0)
        pnl = round(float(verified.get("pnl", 0.0) or 0.0), 2)
        if trades >= verified_bad_min_trades and win_rate <= verified_bad_max_win_rate:
            flagged_cities.append({
                "city": city,
                "win_rate": round(win_rate, 1),
                "trades": trades,
                "pnl": pnl,
            })
    flagged_cities.sort(key=lambda item: (item["win_rate"], -item["trades"], item["city"]))
    flagged_cities_operational = list(flagged_cities)
    flagged_history_note = _build_flagged_city_history_note(legacy_flagged_cities) if legacy_flagged_cities else None

    active_rows = city_observation.get("active_rows", []) if isinstance(city_observation, dict) else []
    active_without_interpretable = [
        {
            "city": row.get("city", "?"),
            "observed_count": int(row.get("observed_count", 0) or 0),
            "observed_goal": int(row.get("observed_goal", OBSERVED_FORECAST_MIN_SAMPLE) or OBSERVED_FORECAST_MIN_SAMPLE),
        }
        for row in active_rows
        if not bool(row.get("interpretable")) and int(row.get("observed_count", 0) or 0) < active_noaa_min_cases
    ]

    shadow_summary = shadow_tracking.get("summary", {}) if isinstance(shadow_tracking, dict) else {}
    directional_signals = int(shadow_resolution.get("total_signals", 0) or 0)
    recent_opps = shadow_tracking.get("directional_history", []) if isinstance(shadow_tracking, dict) else []
    noaa_lookup = {}
    observed_audit_key = globals().get("OBSERVED_AUDIT_KEY", "observed_vs_forecast")
    for entry in audit.get(observed_audit_key, []):
        if not isinstance(entry, dict) or entry.get("source") != "noaa_ncei":
            continue
        obs_temp = entry.get("observed_temp_c")
        if obs_temp is None:
            continue
        key = (str(entry.get("city", "")).strip(), _normalize_shadow_market_date(entry.get("date", "")))
        if key[0] and key[1]:
            noaa_lookup[key] = float(obs_temp)

    directional_resolved = 0
    directional_wins = 0
    for opp in recent_opps:
        if not opp.get("edge_hit"):
            continue
        city = str(opp.get("city", "")).strip()
        market_date = _normalize_shadow_market_date(opp.get("date", ""))
        observed_temp = noaa_lookup.get((city, market_date))
        if observed_temp is None:
            continue
        threshold_helper = globals().get("_extract_threshold_from_question")
        threshold = threshold_helper(str(opp.get("question", "") or "")) if callable(threshold_helper) else None
        side = str(opp.get("side", "") or "").upper()
        if threshold is None or not side:
            continue
        directional_resolved += 1
        if side == "YES" and observed_temp >= threshold:
            directional_wins += 1
        elif side == "NO" and observed_temp < threshold:
            directional_wins += 1
    directional_wr = round((directional_wins / directional_resolved * 100), 1) if directional_resolved > 0 else 0.0
    directional_resolved = int(shadow_resolution.get("resolved", 0) or 0)
    directional_wr = float(shadow_resolution.get("win_rate", 0.0) or 0.0)

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
    if flagged_cities_operational:
        active_items.append({
            "level": "warn",
            "title": "Ciudades con NOAA-verificado malo",
            "detail": ", ".join(
                f"{item['city']} ({item['win_rate']}%, n={item['trades']})"
                for item in flagged_cities_operational
            ),
        })
    if active_without_interpretable:
        active_items.append({
            "level": "warn",
            "title": "Ciudades activas sin NOAA interpretable",
            "detail": ", ".join(
                f"{item['city']} ({item['observed_count']}/{item['observed_goal']})"
                for item in active_without_interpretable[:5]
            ),
        })
    if (
        directional_signals >= shadow_join_min_signals
        and directional_resolved == 0
        and int(forecast_quality.get("sample_size", 0) or 0) >= shadow_join_min_noaa_sample
    ):
        active_items.append({
            "level": "warn",
            "title": "Shadow sin join NOAA util",
            "detail": f"0/{directional_signals} señales shadow enlazadas por city+date con NOAA",
        })
    elif directional_resolved >= shadow_wr_min_resolved and directional_wr < shadow_wr_target:
        active_items.append({
            "level": "warn",
            "title": "WR shadow observado por debajo de objetivo",
            "detail": f"{directional_wr:.1f}% con n={directional_resolved} señales resueltas",
        })

    portfolio = _get_portfolio_and_positions()
    low_bankroll = False
    portfolio_total = None
    if portfolio and portfolio.get("cash") is not None:
        portfolio_total = portfolio.get("portfolio_total", portfolio["cash"])
        bankroll_signal_reliable = portfolio.get("cash_ok") and not portfolio.get("api_error")
        if bankroll_signal_reliable and portfolio_total <= LOW_BANKROLL_THRESHOLD:
            low_bankroll = True
            active_items.insert(0, {
                "level": "critical",
                "title": "Bankroll bajo — recargar $25 USDC",
                "detail": f"Total cartera: ${portfolio_total:.2f} (umbral: ${LOW_BANKROLL_THRESHOLD:.2f})",
            })

    return {
        "signals": signals,
        "pending_stuck": pending_stuck,
        "flagged_cities": flagged_cities,
        "flagged_cities_operational": flagged_cities_operational,
        "legacy_flagged_cities": legacy_flagged_cities,
        "flagged_cities_suppressed": bool(legacy_flagged_cities),
        "flagged_history_note": flagged_history_note,
        "active_without_interpretable": active_without_interpretable,
        "shadow_join_resolved": directional_resolved,
        "shadow_join_win_rate": directional_wr,
        "active_items": active_items,
        "low_bankroll": low_bankroll,
        "portfolio_total": portfolio_total,
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
    has_full_drawdown_window = series_stats["recent_window_size"] >= DRAWDOWN_WINDOW

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
                if has_full_drawdown_window
                else f"{series_stats['recent_window_size']}/{DRAWDOWN_WINDOW} cierres"
                if has_drawdown_window
                else f"sin cierres / umbral ${DRAWDOWN_THRESHOLD:.2f}"
            ),
            f"Serie v{LOGIC_SERIES}",
            has_full_drawdown_window and series_stats["recent_drawdown"] > DRAWDOWN_THRESHOLD,
            True,
            waiting=not has_full_drawdown_window,
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


def _is_shadow_only():
    """True when system is in global observation-only mode (no real trades).

    Checks SHADOW_ONLY_MODE env var first (explicit control).
    Legacy fallback: shadow-only when ACTIVE_TRADING_CITIES is empty/NONE and no
    canary cities are configured, whether explicit or persisted in policy_state.
    This preserves backward compatibility but decouples the pause toggle from
    the city hierarchy level.

    Design intent: ACTIVE_TRADING_CITIES=NONE means "no city has earned active status
    yet", NOT "system is paused". Use SHADOW_ONLY_MODE=true for an explicit pause.
    """
    val = os.getenv("SHADOW_ONLY_MODE", "").strip().lower()
    if val in {"true", "1", "yes"}:
        return True
    if val in {"false", "0", "no"}:
        return False
    # Legacy fallback: no active cities AND no canary cities (env/persisted) → shadow-only
    real_active = {c for c in ACTIVE_TRADING_CITIES if c.upper() not in {"NONE", ""}}
    real_canary = {c for c in CANARY_TRADING_CITIES if c.strip()}
    policy_state = {}
    policy_loader = globals().get("load_city_policy_state")
    policy_normalizer = globals().get("_normalize_city_policy_state")
    if callable(policy_loader):
        try:
            policy_state = policy_loader() or {}
            if callable(policy_normalizer):
                policy_state = policy_normalizer(policy_state)
        except Exception:
            policy_state = {}
    auto_canary = policy_state.get("auto_canary_cities", {}) if isinstance(policy_state, dict) else {}
    auto_canary_from_active = policy_state.get("auto_canary_from_active", {}) if isinstance(policy_state, dict) else {}
    real_auto_canary = {
        str(city).strip()
        for city in (set(auto_canary.keys()) | set(auto_canary_from_active.keys()))
        if str(city).strip()
    }
    return len(real_active) == 0 and len(real_canary) == 0 and len(real_auto_canary) == 0


def _dashboard_mode_label():
    """Human-readable mode for the dashboard badge."""
    if DRY_RUN:
        return "DRY RUN"
    if _is_shadow_only():
        return "SHADOW-ONLY"
    return "REAL"


def _build_topology_line(policy_state=None):
    """Línea compacta de topología: 'N activas | N canary | N shadow | N bloqueadas'.
    Itera RESOLUTION_ICAO (universo conocido) y llama get_effective_city_mode.
    Safe at startup: uses file-based policy_state.
    """
    try:
        if policy_state is None:
            policy_state = load_city_policy_state()
        counts = {"active": 0, "canary": 0, "shadow": 0, "blocked": 0}
        for city in RESOLUTION_ICAO:
            mode = get_effective_city_mode(city, policy_state=policy_state)
            counts[mode] = counts.get(mode, 0) + 1
        parts = []
        if counts["active"]:
            parts.append(f"{counts['active']} activa{'s' if counts['active'] != 1 else ''}")
        if counts["canary"]:
            parts.append(f"{counts['canary']} canary")
        if counts["shadow"]:
            parts.append(f"{counts['shadow']} shadow")
        if counts["blocked"]:
            parts.append(f"{counts['blocked']} bloqueada{'s' if counts['blocked'] != 1 else ''}")
        return " | ".join(parts) if parts else "sin datos"
    except Exception:
        return "n/d"


def build_dashboard_snapshot():
    """Construye el snapshot completo que renderiza el dashboard web."""
    cycle_total, cycle_series = _load_cycle_counts()
    cycle_summary = load_cycle_summary_data()
    cycle_history = load_cycle_history(limit=8)
    audit = load_audit_data()
    trade_lifecycle = load_trade_lifecycle_data()
    shadow_tracking = load_shadow_city_tracking()
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
    exit_breakdown = build_dashboard_exit_breakdown(
        closed_records=validated_closed,
        portfolio=portfolio,
        logic_series=LOGIC_SERIES,
    )
    forecast_quality = build_dashboard_forecast_quality(audit=audit)
    city_policy_metrics = get_city_policy_metrics(audit=audit)
    if "build_dashboard_city_accuracy_views" in globals():
        city_accuracy_views = build_dashboard_city_accuracy_views(
            city_accuracy=city_accuracy,
            city_policy_metrics=city_policy_metrics,
        )
    else:
        city_accuracy_views = {
            "verified_rows": [],
            "legacy_rows": [],
            "verified_count": 0,
            "legacy_count": 0,
            "verified_note": (
                "Mide solo cierres enlazados con NOAA por city+date. Esta es la capa util para juzgar la operativa nueva."
            ),
            "legacy_note": (
                "Mantiene el historico previo o no enlazado con NOAA. Sirve como contexto, pero no debe mandar sobre la policy nueva."
            ),
        }
    city_observation = build_dashboard_city_observation(
        audit=audit,
        city_accuracy=city_accuracy,
        city_policy_metrics=city_policy_metrics,
    )
    city_decisions = build_dashboard_city_decisions(
        city_observation=city_observation,
        city_accuracy=city_accuracy,
        shadow_tracking=shadow_tracking,
        city_policy_metrics=city_policy_metrics,
    )
    legacy_forecast_drift = build_dashboard_legacy_forecast_drift(audit=audit)
    trade_analytics = build_dashboard_trade_analytics(trade_lifecycle=trade_lifecycle, portfolio=portfolio)
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
    next_run_display = (
        bot_state["next_run"].strftime("%Y-%m-%d %H:%M UTC")
        if bot_state.get("next_run")
        else "No programado"
    )
    focus = build_dashboard_focus_center(
        alerts=alerts,
        forecast_quality=forecast_quality,
        city_observation=city_observation,
        series_stats=series_stats,
        series_clean_stats=series_clean_stats,
        next_run_display=next_run_display,
        last_cycle_label=last_cycle_label,
    )
    road_to_real = build_dashboard_road_to_real(
        shadow_tracking=shadow_tracking,
        forecast_quality=forecast_quality,
        city_accuracy=city_accuracy,
        city_decisions=city_decisions,
        alerts=alerts,
    )

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "title": DASHBOARD_TITLE,
        "version": BOT_VERSION,
        "logic_series": LOGIC_SERIES,
        "mode": _dashboard_mode_label(),
        "auth_enabled": auth_enabled,
        "next_run": next_run_display,
        "last_run": bot_state["last_run"].strftime("%Y-%m-%d %H:%M UTC") if bot_state.get("last_run") else "",
        "cycle_total": cycle_total,
        "cycle_series": cycle_series,
        "last_cycle_label": last_cycle_label,
        "cycle_summary": cycle_summary,
        "focus": focus,
        "road_to_real": road_to_real,
        "cycle_history": cycle_history_display,
        "promotion": promotion,
        "progress": progress,
        "exit_breakdown": exit_breakdown,
        "forecast_quality": forecast_quality,
        "city_accuracy_views": city_accuracy_views,
        "city_observation": city_observation,
        "city_decisions": city_decisions,
        "legacy_forecast_drift": legacy_forecast_drift,
        "trade_analytics": trade_analytics,
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
        send_telegram(" Descubrimiento semanal de traders iniciado...")
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
            send_telegram(f"⚠ Error en descubrimiento: {result.stderr[:100]}")
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
    "Seoul":          {"lat": 37.5665, "lon": 126.9780, "name": "Seoul City (KMA)"},
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
    "Los Angeles":    {"lat": 33.93816, "lon": -118.3866, "name": "Los Angeles International Airport"},
    "Dallas":         {"lat": 32.8459,  "lon": -96.8510,  "name": "Dallas Love Field"},
    "Lucknow":        {"lat": 26.7606,  "lon": 80.8893,   "name": "Chaudhary Charan Singh"},
    "Sao Paulo":      {"lat": -23.4355, "lon": -46.4730,  "name": "Guarulhos"},
    "Taipei":         {"lat": 25.0777,  "lon": 121.2330,  "name": "Taoyuan Intl"},
    # Ciudades añadidas en v8 — análisis tercer trader
    "Milan":          {"lat": 45.6306,  "lon": 8.7281,   "name": "Malpensa"},
    "Chongqing":      {"lat": 29.7123,  "lon": 106.6519, "name": "Jiangbei"},
    "Chengdu":        {"lat": 30.5737,  "lon": 103.9415, "name": "Shuangliu"},
    "Wuhan":          {"lat": 30.7748,  "lon": 114.2137, "name": "Tianhe"},
    # Añadidas en v10.6.21 — expansion QUALITY_TRADER_CITIES_WHITELIST (sesion 200)
    "Houston":        {"lat": 29.9902,  "lon": -95.3368,  "name": "George Bush Intercontinental"},
    # Añadidas en v10.6.22 — expansion QUALITY_TRADER_CITIES_WHITELIST (sesion 201)
    # Tel Aviv ya en RESOLUTION_STATIONS + ICAO + noaa_station_id; añadida a whitelist en v10.6.27 (sesion 213)
    # Jakarta: WIHH (Halim Perdanakusuma) — Polymarket resuelve contra esa estación vía WU, NO WIII/Soekarno-Hatta
    "Jakarta":        {"lat": -6.2666, "lon": 106.8906, "name": "Halim Perdanakusuma"},
    "Kuala Lumpur":   {"lat":  2.7456, "lon": 101.7099, "name": "KLIA"},
    # Añadidas en v10.6.28 — expansion P5 RESOLUTION_STATIONS (sesion 215)
    # Todas ICAO-only: NOAA global-hourly + GHCND vacío en 2026 para estaciones non-US (patrón Jakarta/KL sesion 201)
    # Polymarket resolution verificado via WebFetch market rules (Opus, sesion 215)
    "Moscow":         {"lat": 55.592,  "lon": 37.261,   "name": "Vnukovo"},
    "Amsterdam":      {"lat": 52.309,  "lon":  4.764,   "name": "Schiphol"},
    "Jeddah":         {"lat": 21.680,  "lon": 39.157,   "name": "King Abdulaziz Intl"},
    "Helsinki":       {"lat": 60.317,  "lon": 24.963,   "name": "Helsinki Vantaa"},
    # Istanbul: LTFM (Istanbul Airport nuevo) — NO existe en NOAA ISD, por tanto riesgo Seoul-mismatch = cero
    "Istanbul":       {"lat": 41.2622, "lon": 28.7278,  "name": "Istanbul Airport"},
    # Busan: RKPK (Gimhae Intl) — NOAA global-hourly 2026 dead (404); WU/RKPK resolution confirmado v10.6.29
    "Busan":          {"lat": 35.18,   "lon": 128.95,   "name": "Gimhae Intl"},
}


def _wu_history_url(icao, market_date="{date}"):
    """Plantilla de Weather Underground para la estacion de resolucion."""
    return f"https://www.wunderground.com/history/daily/{icao}/date/{market_date}"


# Capa formal de resolucion: referencia declarativa de la estacion que Polymarket
# usa para settlement/revision manual. Incluye ciudades activas, bloqueadas y el
# resto de ciudades que hoy existen en RESOLUTION_STATIONS.
# Verify anchors (legacy):
# "London":         {"icao": "EGLC", "wu_url": _wu_history_url("EGLC")}
# "Madrid":         {"icao": "LEMD", "wu_url": _wu_history_url("LEMD")}
RESOLUTION_ICAO = {
    "Seoul":          {"icao": "RKSI", "wu_url": _wu_history_url("RKSI"), "noaa_station_id": "47113199999", "noaa_daily_station_id": "KS000047112"},
    "London":         {"icao": "EGLC", "wu_url": _wu_history_url("EGLC"), "noaa_station_id": "03768399999", "noaa_daily_station_id": "UKE00107650"},
    "Tel Aviv":       {"icao": "LLBG", "wu_url": _wu_history_url("LLBG"), "noaa_station_id": "40180099999", "noaa_daily_station_id": "ISE00105694"},
    "Shanghai":       {"icao": "ZSPD", "wu_url": _wu_history_url("ZSPD"), "noaa_station_id": "58321199999", "noaa_daily_station_id": "CHM00058362"},
    "Tokyo":          {"icao": "RJTT", "wu_url": _wu_history_url("RJTT"), "noaa_station_id": "47671099999", "noaa_daily_station_id": "JA000047670"},
    "New York City":  {"icao": "KLGA", "wu_url": _wu_history_url("KLGA"), "noaa_station_id": "72503014732", "noaa_daily_station_id": "USW00014732"},
    "Beijing":        {"icao": "ZBAA", "wu_url": _wu_history_url("ZBAA")},
    "Hong Kong":      {"icao": "VHHH", "wu_url": _wu_history_url("VHHH")},
    "Singapore":      {"icao": "WSSS", "wu_url": _wu_history_url("WSSS")},
    "Toronto":        {"icao": "CYYZ", "wu_url": _wu_history_url("CYYZ")},
    "Chicago":        {"icao": "KORD", "wu_url": _wu_history_url("KORD"), "noaa_station_id": "72530094846", "noaa_daily_station_id": "USW00094846"},
    "Wellington":     {"icao": "NZWN", "wu_url": _wu_history_url("NZWN"), "noaa_station_id": "93436000488", "noaa_daily_station_id": "NZM00093439"},
    "Munich":         {"icao": "EDDM", "wu_url": _wu_history_url("EDDM"), "noaa_station_id": "10866099999", "noaa_daily_station_id": "GMM00010870"},
    "Warsaw":         {"icao": "EPWA", "wu_url": _wu_history_url("EPWA")},
    "Ankara":         {"icao": "LTAC", "wu_url": _wu_history_url("LTAC"), "noaa_station_id": "17128099999", "noaa_daily_station_id": "TUM00017130"},
    "Atlanta":        {"icao": "KATL", "wu_url": _wu_history_url("KATL"), "noaa_station_id": "72219013874", "noaa_daily_station_id": "USW00013874"},
    "Shenzhen":       {"icao": "ZGSZ", "wu_url": _wu_history_url("ZGSZ")},
    "Paris":          {"icao": "LFPG", "wu_url": _wu_history_url("LFPG"), "noaa_station_id": "07157099999", "noaa_daily_station_id": "FRM00007149"},
    # SAEZ confirmado via NOAA HOMR + probe real en global-hourly: 87576 + 99999.
    # GHCND daily exacta para Ministro Pistarini: ARM00087576 (valida con TMAX 2025;
    # el Access Data Service sigue devolviendo vacio para marzo 2026).
    "Buenos Aires":   {"icao": "SAEZ", "wu_url": _wu_history_url("SAEZ"), "noaa_station_id": "87576099999", "noaa_daily_station_id": "ARM00087576"},
    "Miami":          {"icao": "KMIA", "wu_url": _wu_history_url("KMIA"), "noaa_station_id": "72202012839", "noaa_daily_station_id": "USW00012839"},
    "Madrid":         {"icao": "LEMD", "wu_url": _wu_history_url("LEMD"), "noaa_station_id": "08221099999", "noaa_daily_station_id": "SPE00120278"},
    "Seattle":        {"icao": "KSEA", "wu_url": _wu_history_url("KSEA"), "noaa_station_id": "72793024233", "noaa_daily_station_id": "USW00024233"},
    # Los Angeles OBSERVED_AUDIT-only: GHCND daily is primary; ISD hourly is metadata/fallback
    # because recent global-hourly returned empty in the 2026-05-01 probe.
    "Los Angeles":    {"icao": "KLAX", "wu_url": _wu_history_url("KLAX"), "noaa_station_id": "72295023174", "noaa_daily_station_id": "USW00023174"},
    "Dallas":         {"icao": "KDAL", "wu_url": _wu_history_url("KDAL"), "noaa_station_id": "72258303927", "noaa_daily_station_id": "USW00013960"},
    # ISD 72254013904 registrado hasta 2025-08-27 (feed migrado); GHCND USW00013904
    # verificado: 182 registros TMAX oct-2025/mar-2026. El bot usa daily path (prioridad 1).
    "Austin":         {"icao": "KAUS", "wu_url": _wu_history_url("KAUS"), "noaa_station_id": "72254013904", "noaa_daily_station_id": "USW00013904"},
    "Lucknow":        {"icao": "VILK", "wu_url": _wu_history_url("VILK")},
    "Sao Paulo":      {"icao": "SBGR", "wu_url": _wu_history_url("SBGR")},
    "Taipei":         {"icao": "RCTP", "wu_url": _wu_history_url("RCTP")},
    "Milan":          {"icao": "LIMC", "wu_url": _wu_history_url("LIMC"), "noaa_station_id": "16066099999", "noaa_daily_station_id": "SZ000009480"},
    "Chongqing":      {"icao": "ZUCK", "wu_url": _wu_history_url("ZUCK")},
    "Chengdu":        {"icao": "ZUUU", "wu_url": _wu_history_url("ZUUU"), "noaa_station_id": "56294099999", "noaa_daily_station_id": "CHM00056187"},
    "Wuhan":          {"icao": "ZHHH", "wu_url": _wu_history_url("ZHHH")},
    # Añadidas en v10.6.21 — ICAO pendiente verificación Polymarket resolution source
    "Houston":        {"icao": "KIAH", "wu_url": _wu_history_url("KIAH")},
    # Añadidas en v10.6.22 — Polymarket resuelve contra WU; sin NOAA diario reciente
    # Jakarta: WIHH (Halim Perdanakusuma) — ISD 96749599999 confirmado sin CSV global-hourly 2026; GHCND ID000096745/IDM00096741 sin TMAX reportado en 2026 (yearly file)
    # Kuala Lumpur: WMKK (KLIA) — ISD 48650099999 confirmado sin CSV global-hourly 2026; GHCND MYM00048650 sin TMAX reportado en 2026
    "Jakarta":        {"icao": "WIHH", "wu_url": _wu_history_url("WIHH")},
    "Kuala Lumpur":   {"icao": "WMKK", "wu_url": _wu_history_url("WMKK")},
    # Ciudades sin cobertura NOAA verificada (2026-04-06) — pendiente alternativa
    # Toronto: CYYZ — ISD 71624099999 confirmado; GHCND local sin TMAX en 2025-10-01..2026-03-31
    # Beijing: ZBAA — ISD 54511099999 confirmado; GHCND local sin TMAX en 2025-10-01..2026-03-31
    # Hong Kong: VHHH — ISD 45007099999 confirmado; GHCND cercano sin TMAX en 2025-10-01..2026-03-31
    # Singapore: WSSS — ISD 48698099999 confirmado; GHCND cercano sin TMAX en 2025-10-01..2026-03-31
    # Warsaw: EPWA — ISD 12375099999 confirmado; GHCND local sin TMAX en 2025-10-01..2026-03-31
    # Taipei: RCTP — ISD 46686099999 confirmado; sin candidato GHCND con TMAX suficiente cerca
    # Shenzhen: ZGSZ — ISD 59493099999 confirmado; GHCND regional sin TMAX en 2025-10-01..2026-03-31
    # Chongqing: ZUCK — ISD 57516099999 confirmado; GHCND local sin TMAX en 2025-10-01..2026-03-31
    # Wuhan: ZHHH — ISD 57494099999 confirmado; GHCND local sin TMAX en 2025-10-01..2026-03-31
    # Lucknow: VILK — ISD 42369099999 confirmado; GHCND cercano sin TMAX en 2025-10-01..2026-03-31
    # Sao Paulo: SBGR — ISD 83075099999 confirmado; GHCND cercano sin TMAX en 2025-10-01..2026-03-31
    # Añadidas en v10.6.28 — expansion P5 (sesion 215)
    # Polymarket: Moscow→NOAA weather.gov/wrh?site=UUWW | Amsterdam→WU EHAM | Jeddah→WU OEJN | Istanbul→NOAA weather.gov/wrh?site=LTFM | Helsinki→WU EFHK
    # NOAA global-hourly + GHCND probe 2026: vacío para UUWW/EHAM/OEJN/EFHK; LTFM ausente de isd-history.csv
    "Moscow":         {"icao": "UUWW", "wu_url": _wu_history_url("UUWW")},
    "Amsterdam":      {"icao": "EHAM", "wu_url": _wu_history_url("EHAM")},
    "Jeddah":         {"icao": "OEJN", "wu_url": _wu_history_url("OEJN")},
    "Helsinki":       {"icao": "EFHK", "wu_url": _wu_history_url("EFHK")},
    "Istanbul":       {"icao": "LTFM", "wu_url": _wu_history_url("LTFM"), "weather_gov_timeseries_site": "LTFM"},
    # Añadida en v10.6.29 — Busan TRADER_ONLY 7/7; WU/RKPK es fuente Polymarket (confirmado Apr-21-2026)
    # NOAA global-hourly 2026: 404 para 47158099999; WU historical "No data" = artefacto JS no renderizado
    "Busan":          {"icao": "RKPK", "wu_url": _wu_history_url("RKPK")},
}

# Verify anchor (legacy): OBSERVED_AUDIT_CITIES = {"Chicago", "Atlanta", "Buenos Aires", "Dallas"}
OBSERVED_AUDIT_CITIES = {
    "Ankara",
    "Atlanta",
    "Austin",
    "Beijing",
    "Buenos Aires",
    "Chengdu",
    "Chicago",
    "Dallas",
    "Jakarta",
    "Kuala Lumpur",
    "London",
    "Lucknow",
    "Los Angeles",
    "Madrid",
    "Miami",
    "Milan",
    "Munich",
    "New York City",
    "Paris",
    "Sao Paulo",
    "Seattle",
    "Seoul",
    "Shanghai",
    "Busan",
    "Tel Aviv",
    "Tokyo",
    "Warsaw",
    "Wellington",
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
    "Jakarta":        "Asia/Jakarta",
    "Kuala Lumpur":   "Asia/Kuala_Lumpur",
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
    "Austin":         "America/Chicago",
    "Chicago":        "America/Chicago",
    "Dallas":         "America/Chicago",
    "Houston":        "America/Chicago",
    "Seattle":        "America/Los_Angeles",
    "San Francisco":  "America/Los_Angeles",
    "Los Angeles":    "America/Los_Angeles",
    "Denver":         "America/Denver",
    "Mexico City":    "America/Mexico_City",
    "Moscow":         "Europe/Moscow",
    "Amsterdam":      "Europe/Amsterdam",
    "Jeddah":         "Asia/Riyadh",
    "Istanbul":       "Europe/Istanbul",
    "Helsinki":       "Europe/Helsinki",
    "Busan":          "Asia/Seoul",
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
# TELEGRAM — ENVO
# =============================================================

MENU_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🎯 Focus", "callback_data": "focus"},
            {"text": "📊 Estado", "callback_data": "estado"},
        ],
        [
            {"text": "🛰 Observabilidad", "callback_data": "noaa"},
            {"text": "💰 Cartera", "callback_data": "cartera"},
        ],
        [
            {"text": " Accuracy", "callback_data": "accuracy"},
            {"text": "📚 Postmortem", "callback_data": "postmortem"},
        ],
        [
            {"text": "📓 Log", "callback_data": "log"},
            {"text": "📋 Detalle", "callback_data": "logfull"},
        ],
        [
            {"text": " Traders", "callback_data": "traders"},
            {"text": "📈 Rendimiento", "callback_data": "rendimiento"},
        ],
        [
            {"text": "🗒 Órdenes", "callback_data": "ordenes"},
            {"text": "ℹ Info", "callback_data": "info"},
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

def cmd_focus():
    """Vista principal Telegram: capa 1 para discovery / stabilization."""
    audit = load_audit_data()
    city_accuracy = get_city_accuracy()
    cycle_summary = load_cycle_summary_data()

    next_run_display = (
        bot_state["next_run"].strftime("%Y-%m-%d %H:%M UTC")
        if bot_state.get("next_run")
        else "No programado"
    )

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

    city_policy_metrics = get_city_policy_metrics(audit=audit)
    focus = build_dashboard_focus_center(
        alerts=get_dashboard_alert_summary(),
        forecast_quality=build_dashboard_forecast_quality(audit=audit),
        city_observation=build_dashboard_city_observation(
            audit=audit,
            city_accuracy=city_accuracy,
            city_policy_metrics=city_policy_metrics,
        ),
        series_stats=get_logic_series_stats(),
        series_clean_stats=get_logic_series_clean_closed_trade_stats(),
        next_run_display=next_run_display,
        last_cycle_label=last_cycle_label,
    )
    icon_map = {"good": "🟢", "accent": "🔵", "warn": "🟡", "bad": "🔴", "muted": "⚪"}

    lines = [
        "🎯 <b>Focus / Discovery-Stabilization</b>",
        "",
        f"{icon_map.get(focus['status_badge'], '⚪')} <b>{focus['headline']}</b>",
        f"<i>{focus['summary']}</i>",
        "",
    ]

    for answer in focus["answers"]:
        icon = icon_map.get(answer.get("badge"), "⚪")
        lines.append(f"{icon} <b>{answer['question']}</b>")
        lines.append(answer["answer"])
        lines.append(f"<i>{answer['detail']}</i>")
        lines.append("")

    lines.append("👉 <b>Acción recomendada hoy</b>")
    lines.append(focus["action"]["title"])
    lines.append(f"<i>{focus['action']['detail']}</i>")

    lines.append("")
    lines.append("<b>Universo y muestra</b>")
    for item in focus["quick_stats"][:3]:
        lines.append(f"• <b>{item['label']}</b>: {item['value']} | {item['detail']}")
    lines.append(f"• <b>Próximo ciclo</b>: {next_run_display}")

    if focus["incidents"]:
        lines.append("")
        lines.append("<b>Incidentes activos</b>")
        for item in focus["incidents"][:3]:
            icon = icon_map.get(item.get("badge"), "⚪")
            lines.append(f"{icon} <b>{item['title']}</b>: {item['detail']}")
    else:
        lines.append("")
        lines.append("🟢 <b>Incidentes activos</b>: ninguno relevante ahora mismo.")

    lines.append("")
    lines.append("<b>Siguiente capa</b>")
    lines.append("/estado sistema | /noaa muestra | /accuracy ciudades | /detalle ciclo raw")
    send_telegram_paged("\n".join(lines), with_menu=True)


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

    intra_str = f" | Intra-SL cada {INTRA_SL_INTERVAL}min" if INTRA_SL_INTERVAL > 0 else ""
    topology = _build_topology_line()

    send_telegram(
        f"📊 <b>Bot {BOT_VERSION} | {modo}</b>\n\n"
        f"💰 Bankroll: <b>${BANKROLL:.2f}</b> | Edge mín: {MIN_EDGE}%\n"
        f"🔧 SL/TP en ciclo: -{STOP_LOSS_PCT}%/+{TAKE_PROFIT_PCT}%{intra_str}\n"
        f"🗺 Ciudades: {topology}\n\n"
        f" Estado: {running}\n"
        f"📅 Último: {last_str}\n"
        f" Próximo: {next_str}\n"
        f"🔢 Ciclos: {bot_state['cycle_count']} total | {bot_state.get('cycle_count_series', 0)} serie v{LOGIC_SERIES}"
        f"{cycle_line}\n\n"
        f"Schedule: {schedule} UTC",
        with_menu=True,
    )


def cmd_cartera():
    """💰 Cartera: cash + posiciones activas. v10.4.2: etiquetas legibles, precios en centavos."""
    portfolio = _get_portfolio_and_positions()
    if portfolio is None:
        send_telegram(" No hay FUNDER configurado.", with_menu=True)
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
        msg += f"⚠ <i>Error API posiciones: {api_error[:80]}</i>\n\n"
    if cash_ok:
        msg += f"💵 Cash: <b>${cash:.2f}</b>\n"
    else:
        msg += f"💵 Cash: <i>no disponible</i>\n"

    msg += f"📊 Posiciones vivas: <b>${active_value:.2f}</b> ({len(active)} pos)\n"
    if resolved_won:
        msg += f" Pendiente pago: ${resolved_value:.2f} ({len(resolved_won)})\n"
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
        msg += f"\n<b> Esperando pago:</b>\n"
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
        send_telegram(" No autenticado.", with_menu=True)
        return

    try:
        orders = get_open_orders(clob_client)
    except Exception as e:
        send_telegram(f" Error: {e}", with_menu=True)
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
                age_str = f" {age_h:.1f}h"
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
            n_shadow = scan.get("shadow", 0)
            n_condition_filtered = scan.get("condition_filtered", 0)
            msg += (
                f"<b>Escaneo:</b> {n_mkts} candidatos → {n_edge} con edge → "
                f"{n_sel} seleccionados para BUY | shadow {n_shadow}\n"
            )

            msg += f"Condición filtrada: {n_condition_filtered} mercados (range/exact)\n"

            # Compras
            if buys:
                msg += f"\n<b>Compras ({len(buys)}):</b>\n"
                for b in buys:
                    trader_icon = " " if b.get("traders") else ""
                    mode_tag_helper = globals().get("_format_buy_mode_tag")
                    mode_tag = (
                        mode_tag_helper(b.get("city_mode"))
                        if callable(mode_tag_helper)
                        else str(b.get("city_mode", "") or "OPERABLE").upper()
                    )
                    msg += (
                        f"  🟢 [{mode_tag}] {b.get('city','?')} {b.get('side','?')} "
                        f"${b.get('amount',0):.2f} | edge {b.get('edge',0)}%{trader_icon}\n"
                    )
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
        condition_filtered = []
        shadow_edges = []
        duplicates = []
        kelly_low = []

        for line in edge_analysis:
            stripped = line.strip()
            if stripped.startswith("✓"):
                accepted.append(stripped)
            elif stripped.startswith("SHADOW-FILTER"):
                condition_filtered.append(stripped)
            elif stripped.startswith("SHADOW "):
                shadow_edges.append(stripped)
            elif "BAJO" in stripped:
                edge_match = re.search(r"edge=(\d+\.?\d*)%", stripped)
                edge_val = float(edge_match.group(1)) if edge_match else 0
                near_misses.append((edge_val, stripped[2:]))
            elif "SIN EDGE" in stripped:
                no_edge.append(stripped[2:])
            elif (
                "YA HAY ORDEN" in stripped
                or "VENDIDO ESTE CICLO" in stripped
                or "YA HAY POSICIÓN ABIERTA" in stripped
            ):
                duplicates.append(stripped[2:])
            elif "KELLY" in stripped:
                kelly_low.append(stripped[2:])

        near_misses.sort(key=lambda x: -x[0])

        text = f"📋 <b>Log detallado del último ciclo</b>\n\n"
        text += f"Total: {len(edge_analysis)} candidatos evaluados\n"
        text += f"✅ Aceptados: {len(accepted)}\n"
        text += f"🔶 Near miss (edge ≥3%): {len([n for n in near_misses if n[0] >= 3])}\n"
        text += f"🟣 Shadow con edge: {len(shadow_edges)}\n"
        text += f"🟡 Condición filtrada: {len(condition_filtered)}\n"
        text += f"🔁 Duplicados/protecciones: {len(duplicates)}\n"
        text += f"⚪ Sin edge: {len(no_edge)}\n"
        text += f"💸 Kelly bajo: {len(kelly_low)}\n"

        # Aceptados
        if accepted:
            text += f"\n<b>✅ ACEPTADOS:</b>\n"
            for line in accepted[:5]:
                text += f"🟢 {line[2:70]}\n"

        if shadow_edges:
            text += f"\n<b>🟣 SHADOW CON EDGE:</b>\n"
            for line in shadow_edges[:5]:
                text += f"  {line[:80]}\n"

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
        send_telegram(f" Error en detalle: {str(e)[:200]}", with_menu=True)


def cmd_modo():
    global DRY_RUN
    if DRY_RUN:
        msg = (
            f"⚡ <b>Modo: 🟡 DRY RUN</b>\n\n"
            f"¿Activar <b>MODO REAL</b>?\n"
            f"Bankroll: ${BANKROLL:.2f}\n\n"
            f"⚠ Dinero real."
        )
        kb = {"inline_keyboard": [[
            {"text": "✅ Activar REAL", "callback_data": "confirmar_real"},
            {"text": " Cancelar", "callback_data": "cancelar_modo"},
        ]]}
    else:
        msg = (
            f"⚡ <b>Modo: 🔴 REAL</b>\n\n"
            f"¿Volver a <b>DRY RUN</b>?"
        )
        kb = {"inline_keyboard": [[
            {"text": "🟡 Volver a DRY RUN", "callback_data": "confirmar_dry"},
            {"text": " Cancelar", "callback_data": "cancelar_modo"},
        ]]}
    send_telegram(msg, custom_keyboard=kb)


def cmd_confirmar_real():
    global DRY_RUN
    DRY_RUN = False
    log.info("MODO REAL desde Telegram")
    send_telegram(
        f"🔴 <b>MODO REAL ACTIVADO</b>\n\n"
        f"Bankroll: ${BANKROLL:.2f}\n\n"
        f"⚠ Si Railway reinicia → vuelve a DRY_RUN de Railway.\n"
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
     Traders Intel: señales + coincidencias con posiciones activas.
    v10.4.2: cruza señales con cartera actual.
    """
    if not os.path.exists(SIGNALS_FILE):
        send_telegram(
            " <b>Traders Intel</b>\n\n"
            "Sin datos todavía.\n"
            "Se generarán automáticamente en el próximo ciclo.",
            with_menu=True,
        )
        return

    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        send_telegram(f" Error: {e}", with_menu=True)
        return

    generated = data.get("generated", "?")[:16]
    n_signals = data.get("n_actionable_signals", 0)
    n_consensus = data.get("n_consensus_markets", 0)
    n_traders = data.get("n_traders_analyzed", 0)
    n_quality = data.get("n_quality_traders", 0)
    quality_names = data.get("quality_traders", [])
    n_skipped = data.get("n_skipped_low_quality", 0)

    text = f" <b>Traders Intel</b>\n"
    text += f"<i>{generated} UTC</i>\n"
    text += f"Analizados: {n_traders} | Calidad: {n_quality} | Skip: {n_skipped}\n"
    text += f"Señales: {n_signals} | Consenso: {n_consensus}\n"

    if quality_names:
        text += f"\n <b>Calidad:</b> {', '.join(quality_names[:6])}\n"

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
            icon = "" if s.get("has_consensus") else ""
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
            icon = "" if s.get("has_consensus") else ""
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
            text += f" Pendiente pago: ${resolved_value:.2f} ({len(resolved_won)})\n"
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
        text += f"   Pendientes fill: {stats['pending_sells']}\n"
    text += f"  Invertido: ${stats['total_invested']:.2f}\n"
    text += f"  PnL ventas: <b>${stats['sell_pnl']:+.2f}</b>\n"

    text += f"\n<b>Salidas:</b>\n"
    text += f"  💰 TP: {stats['take_profits']} | 🔻 SL: {stats['stop_losses']} | 🔄 Reeval: {stats['reevals']}\n"

    if stats['confirmed_count'] + stats['unconfirmed_count'] > 0:
        text += f"\n<b>Con/sin trader:</b>\n"
        if stats['confirmed_count'] > 0:
            text += f"   {stats['confirmed_count']} ops → ${stats['confirmed_pnl']:+.2f}\n"
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

    text += f"\n<i>⚠ PnL fiable: dashboard Polymarket.</i>\n"
    send_telegram_paged(text, with_menu=True)


def cmd_info():
    """ℹ Bloque resumen del bot para pegar en ChatGPT/Claude."""
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
            mode_tag_helper = globals().get("_format_buy_mode_tag")
            buys_str = ", ".join(
                f"[{mode_tag_helper(b.get('city_mode')) if callable(mode_tag_helper) else str(b.get('city_mode', '') or 'OPERABLE').upper()}] "
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
                f"  Escaneo: {scan.get('markets_evaluated',0)} candidatos → "
                f"{scan.get('with_edge',0)} con edge → {scan.get('selected',0)} seleccionados para BUY\n"
                f"  Compras: {buys_str}\n"
            )
            cycle_block += (
                f"  Shadow con edge: {scan.get('shadow',0)} | "
                f"Condición filtrada: {scan.get('condition_filtered',0)} mercados (range/exact)\n"
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
        f"Edge mín: {MIN_EDGE}% | SL: {STOP_LOSS_PCT}% | TP: +{TAKE_PROFIT_PCT}%\n"
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
        f"~330 mercados temp | forecast operativo: Open-Meteo | modelo normal(μ,σ)\n"
        f"Sigma: D0=1.2 D1=1.5 D2=2.0 D3=2.5 D4-5=3.0\n"
        f"Half-Kelly | Railway EU-West (Amsterdam)\n"
        f"Observed proxy: NOAA | resolución final de Polymarket: Weather Underground"
    )

    send_telegram_paged(text, with_menu=True)


def cmd_accuracy():
    """Resumen por ciudad, priorizando policy/NOAA-verificado sobre histórico legacy."""
    city_stats = get_city_accuracy()
    audit = load_audit_data()
    city_policy_metrics = get_city_policy_metrics(audit=audit)
    policy_state = load_city_policy_state()

    if not city_stats and not city_policy_metrics:
        send_telegram("Sin datos de accuracy todavía.", with_menu=True)
        return

    operable_cities = sorted(
        {
            city
            for city in set(city_stats.keys()) | set(city_policy_metrics.keys()) | set(ACTIVE_TRADING_CITIES) | set(CANARY_TRADING_CITIES)
            if get_effective_city_mode(city, policy_state=policy_state) in {"active", "canary"}
        }
    )

    lines = [
        "<b>Accuracy por ciudad</b>",
        "",
        "<b>Operables hoy — NOAA-verificado / policy</b>",
    ]

    if operable_cities:
        for city in operable_cities:
            mode_tag = _format_buy_mode_tag(get_effective_city_mode(city, policy_state=policy_state))
            buckets = city_policy_metrics.get(city, {}) if isinstance(city_policy_metrics, dict) else {}
            verified = buckets.get("verified", {}) if isinstance(buckets, dict) else {}
            trades = int(verified.get("trades", 0) or 0)
            wins = int(verified.get("wins", 0) or 0)
            win_rate = round(float(verified.get("win_rate", 0.0) or 0.0), 1)
            pnl = round(float(verified.get("pnl", 0.0) or 0.0), 2)
            if trades > 0:
                flag = " ⚠" if trades >= CITY_MIN_TRADES_FOR_BLOCK and win_rate <= CITY_BLOCK_WIN_RATE else ""
                lines.append(
                    f"<b>{city}</b> [{mode_tag}]{flag}: "
                    f"{wins}/{trades} ({win_rate}%) ${pnl:+.2f}"
                )
            else:
                lines.append(f"<b>{city}</b> [{mode_tag}]: sin trades NOAA-verificados todavía")
    else:
        lines.append("<i>Sin ciudades operables hoy.</i>")

    if city_stats:
        sorted_cities = sorted(city_stats.items(), key=lambda x: -x[1]["trades"])
        lines.extend([
            "",
            "<b>Histórico total postmortem</b>",
            "<i>Incluye histórico legacy; úsalo como contexto, no como policy principal.</i>",
        ])
        for city, data in sorted_cities:
            blocked = " 🚫" if is_city_blocked(city) else ""
            flag = " ⚠" if data["trades"] >= CITY_MIN_TRADES_FOR_BLOCK and data["win_rate"] <= CITY_BLOCK_WIN_RATE else ""
            lines.append(
                f"<b>{city}</b>{blocked}{flag}: "
                f"{data['wins']}/{data['trades']} ({data['win_rate']}%) "
                f"${data['pnl']:+.2f}"
            )

    send_telegram_paged("\n".join(lines), with_menu=True)


def cmd_noaa():
    """Vista Telegram del observed proxy NOAA para seguimiento de medicion/fidelity."""
    summary = build_dashboard_forecast_quality(audit=load_audit_data())
    level_icons = {"good": "🟢", "waiting": "🟡", "warn": "🟡", "bad": "🔴", "muted": "⚪"}

    lines = [
        "🛰 <b>NOAA / Observabilidad</b>",
        "",
        f"Muestra: <b>{summary['sample_display']}</b>",
        f"MAE global: <b>{summary['mae_display']}</b>",
        f"Bias global: <b>{summary['bias_display']}</b>",
        f"Cobertura: {summary['coverage_display']}",
        f"Ciudades interpretables: {summary['coverage_detail']}",
        f"Ultimo registro: {summary['last_record_display']}",
        "",
        f"<i>{summary['note']}</i>",
    ]

    if summary["city_rows"]:
        lines.append("")
        lines.append("<b>Ciudades operables / seguidas</b>")
        for row in summary["city_rows"]:
            icon = level_icons.get(row.get("status"), "⚪")
            lines.append(f"{icon} <b>{row['city']}</b>: {row['detail']}")

    if summary["latest_rows"]:
        lines.append("")
        lines.append("<b>Ultimos casos NOAA</b>")
        for row in summary["latest_rows"][:5]:
            lines.append(
                f"• {row['city']} {row['date']}: forecast {row['forecast_display']} | "
                f"obs {row['observed_display']} | error {row['error_display']}"
            )

    lines.append("")
    lines.append("<i>Caso NOAA = 1 fila city+date en observed_vs_forecast.</i>")
    lines.append("<i>NOAA es observed proxy; no equivale a la resolucion final de Polymarket.</i>")
    send_telegram_paged("\n".join(lines), with_menu=True)


def cmd_bankroll():
    report = run_bankroll_scaling_check_json()
    if not report:
        send_telegram("No pude calcular bankroll scaling check ahora; revisa logs.", with_menu=True)
        return
    send_telegram_paged(format_bankroll_scaling_telegram(report), with_menu=True)


COMMANDS = {
    "focus": cmd_focus, "estado": cmd_estado, "cartera": cmd_cartera, "ordenes": cmd_ordenes,
    "log": cmd_log, "logfull": cmd_logfull, "forzar": cmd_forzar,
    "modo": cmd_modo, "traders": cmd_traders, "rendimiento": cmd_rendimiento,
    "info": cmd_info, "postmortem": cmd_postmortem, "accuracy": cmd_accuracy,
    "noaa": cmd_noaa, "observabilidad": cmd_noaa,
    "bankroll": cmd_bankroll, "bankroll_status": cmd_bankroll,
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
                send_telegram(f" Error: {e}", with_menu=True)
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
                send_telegram(f" Error: {e}", with_menu=True)
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
        client.set_api_creds(client.create_or_derive_api_key())
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
    """GET a Open-Meteo con reintentos automaticos."""
    cache_ttl = max(0, int(globals().get("FORECAST_CACHE_TTL_SECONDS", 900) or 0))
    stale_grace = max(cache_ttl, int(globals().get("FORECAST_STALE_IF_ERROR_SECONDS", 21600) or 0))
    cooldown_floor = max(delay, int(globals().get("FORECAST_RATE_LIMIT_COOLDOWN_SECONDS", 120) or 0))
    cache_store = globals().setdefault("_forecast_http_cache", {})
    cache_key = f"{float(lat):.4f},{float(lon):.4f}"
    now_ts = time.time()
    cached_entry = cache_store.get(cache_key)
    stale_data = None
    if isinstance(cached_entry, dict):
        cached_at = float(cached_entry.get("fetched_at", 0) or 0)
        cached_data = cached_entry.get("data")
        cache_age = max(0.0, now_ts - cached_at)
        if cached_data:
            if cache_ttl and cache_age <= cache_ttl:
                return cached_data
            if stale_grace and cache_age <= stale_grace:
                stale_data = cached_data

    cooldown_until = float(globals().get("_forecast_rate_limited_until", 0.0) or 0.0)
    if now_ts < cooldown_until:
        cooldown_left = max(1, int(round(cooldown_until - now_ts)))
        if stale_data is not None:
            log.warning(
                f"Forecast rate limited: usando cache stale ({cooldown_left}s de cooldown activo)"
            )
            return stale_data
        raise RuntimeError(f"Forecast rate limited: cooldown activo {cooldown_left}s")

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
            cache_store[cache_key] = {"fetched_at": time.time(), "data": result}
            return result
        except urllib.error.HTTPError as e:
            last_error = e
            if getattr(e, "code", None) == 429:
                retry_after = ""
                try:
                    retry_after = str(e.headers.get("Retry-After", "") or "").strip()
                except Exception:
                    retry_after = ""
                wait_seconds = cooldown_floor
                if retry_after.isdigit():
                    wait_seconds = max(wait_seconds, int(retry_after))
                globals()["_forecast_rate_limited_until"] = max(
                    float(globals().get("_forecast_rate_limited_until", 0.0) or 0.0),
                    time.time() + wait_seconds,
                )
                if stale_data is not None:
                    log.warning(
                        f"Forecast rate limited (HTTP 429): usando cache stale y enfriando {wait_seconds}s"
                    )
                    return stale_data
                raise RuntimeError(f"Forecast rate limited (HTTP 429): cooldown {wait_seconds}s")
            if attempt < retries - 1:
                wait_seconds = delay * (2 ** attempt)
                log.warning(
                    f"Forecast error (intento {attempt+1}/{retries}): {e} - reintentando en {wait_seconds}s"
                )
                time.sleep(wait_seconds)
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                wait_seconds = delay * (2 ** attempt)
                log.warning(
                    f"Forecast error (intento {attempt+1}/{retries}): {e} - reintentando en {wait_seconds}s"
                )
                time.sleep(wait_seconds)
    if stale_data is not None:
        log.warning("Forecast error persistente: usando cache stale")
        return stale_data
    raise last_error

# =============================================================
# FUNCIONES: ÓRDENES
# =============================================================

def get_open_orders(client):
    try:
        orders = client.get_open_orders()
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

    Esto es CRTICO: sin esto, cada ciclo cree que tiene presupuesto completo
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
            # Fix Bug #15: posiciones redeemable son cash garantizado aunque
            # curPrice no haya llegado aún a 0.98 (ej: resolución en progreso).
            if p.get("redeemable"):
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

def recompute_position_edge(position, forecast_cache, lc_by_token=None):
    """
    Recalcula edge actual usando forecast fresco. Pura: no muta lifecycle.

    Args:
        position: dict del endpoint /positions
        forecast_cache: dict {city: forecast_dict} para amortizar NOAA calls dentro del check.
                        MUTADO in-place para agregar entradas de ciudades nuevas.
        lc_by_token: opcional, no usado (compat futura)

    Returns:
        dict {"edge_pct", "our_prob", "mkt_price", "forecast_max", "days_ahead", "city"}
        o None si no re-evaluable (sin station, sin forecast, date pasada, título no parseable)
    """
    title_full = position.get("title", "")
    outcome = position.get("outcome", "YES")
    cur_price = float(position.get("curPrice", 0))

    parsed = parse_temperature_question(title_full)
    if not parsed or not parsed.get("date_str"):
        return None

    city = parsed["city"]
    date_iso = date_text_to_iso(parsed["date_str"])
    if not date_iso:
        return None

    try:
        days_ahead = (date.fromisoformat(date_iso) - date.today()).days
    except ValueError:
        return None

    # Si ya pasó la fecha, no re-evaluar
    if days_ahead < 0:
        return None

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
        return None

    # Recalcular probabilidad con datos frescos
    forecast_max = fc[date_iso]["temp_max"]
    threshold = parsed["temp_threshold"]
    threshold_c = (threshold - 32) * 5 / 9 if parsed["unit"] == "F" else float(threshold)

    threshold_high = parsed.get("temp_threshold_high")
    threshold_high_c = None
    if threshold_high is not None:
        threshold_high_c = (threshold_high - 32) * 5 / 9 if parsed["unit"] == "F" else float(threshold_high)

    our_prob_yes = estimate_prob_with_city(
        forecast_max,
        threshold_c,
        parsed["condition"],
        days_ahead,
        threshold_high_c,
        city=city,
    )

    # ¿Qué lado tenemos? Calcular edge actual
    if outcome.upper() == "YES":
        our_prob = our_prob_yes
        mkt_price = cur_price
    else:
        our_prob = 1.0 - our_prob_yes
        mkt_price = 1.0 - cur_price

    edge_pct = (our_prob - mkt_price) * 100

    return {
        "edge_pct": edge_pct,
        "our_prob": our_prob,
        "mkt_price": mkt_price,
        "forecast_max": forecast_max,
        "days_ahead": days_ahead,
        "city": city,
    }


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
            # v10.5.12: Registrar pérdida aunque la posición ya no tenga valor vendible.
            # Antes estas posiciones se ignoraban con "continue" y el postmortem quedaba
            # en "open" para siempre, ocultando la pérdida real del balance.
            _mark_micro_as_loss_total(p, dl)
            continue

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
    record_trade_lifecycle_position_snapshots(temp_positions, source="manage_positions", stage="pre_checks")

    # ---- Cache de previsiones para re-evaluación ----
    forecast_cache = {}

    # ---- Cache de our_prob y entry_price por token_id para TP dinámico ----
    try:
        _lc_data = load_trade_lifecycle_data()
        _lc_by_token = {
            str(r.get("token_id", "") or "").strip(): float(
                (r.get("entry_context") or {}).get("our_prob")
            )
            for r in _lc_data.get("records", [])
            if str(r.get("token_id", "") or "").strip()
            and (r.get("entry_context") or {}).get("our_prob") is not None
        }
        _lc_by_token_price = {
            str(r.get("token_id", "") or "").strip(): float(
                (r.get("entry_context") or {}).get("price")
            )
            for r in _lc_data.get("records", [])
            if str(r.get("token_id", "") or "").strip()
            and (r.get("entry_context") or {}).get("price") is not None
        }
    except Exception:
        _lc_by_token = {}
        _lc_by_token_price = {}

    # ---- Evaluar cada posición ----
    to_sell = []        # lista de (posición, tipo, razón)
    keeping = []        # info de las que mantenemos
    n_resolved = 0      # mercados ya resueltos (curPrice >= 0.98)
    lifecycle_needs_sync = False

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
            dl.append(f"   RESUELTO ({outcome} @ {cur_price:.2f}) | {title} | Esperando pago")
            # v10.4 Fix Bug #12: NO añadir a keeping — son resueltas, no mantenidas
            n_resolved += 1
            lifecycle_needs_sync = True
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

        # ---- CHECK 2: Take-profit (dinámico por precio de entrada + convicción) ----
        _entry_prob = _lc_by_token.get(asset_id)
        _entry_price_lc = _lc_by_token_price.get(asset_id)
        effective_tp = effective_tp_pct(_entry_price_lc, _entry_prob)
        if pct_pnl >= effective_tp:
            _price_tag = f" [entry={_entry_price_lc:.2f}]" if _entry_price_lc is not None else ""
            reason = f"💰 TAKE-PROFIT ({pct_pnl:+.1f}% > +{effective_tp:.0f}%{_price_tag})"
            to_sell.append((p, "take_profit", reason))
            dl.append(f"  {reason} | {label} | ${cash_pnl:+.2f}")
            continue

        # ---- CHECK 3: Re-evaluación con previsión fresca ----
        fresh = recompute_position_edge(p, forecast_cache)
        if fresh is None:
            # No hay forecast o no parseable — verificar si es fecha pasada
            parsed_chk = parse_temperature_question(title_full)
            if parsed_chk and parsed_chk.get("date_str"):
                date_iso_chk = date_text_to_iso(parsed_chk["date_str"])
                if date_iso_chk:
                    try:
                        days_ahead_chk = (date.fromisoformat(date_iso_chk) - date.today()).days
                    except ValueError:
                        days_ahead_chk = 1
                    if days_ahead_chk < 0:
                        dl.append(f"   RESOLUCIÓN pendiente | {label}")
                        keeping.append(p)
                        continue
                    city_chk = parsed_chk.get("city", "")
                    if not RESOLUTION_STATIONS.get(city_chk):
                        dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | no parseable")
                    else:
                        dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | sin previsión")
                else:
                    dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | fecha inválida")
            else:
                dl.append(f"  ✓ MANTENER ({pct_pnl:+.1f}%) | {label} | no parseable")
            keeping.append(p)
            continue

        edge_pct = fresh["edge_pct"]
        our_prob = fresh["our_prob"]
        mkt_price = fresh["mkt_price"]
        forecast_max = fresh["forecast_max"]

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
        if lifecycle_needs_sync:
            try:
                _sync_trade_lifecycle_from_sources()
            except Exception as e:
                log.warning(f"Error sincronizando trade_lifecycle tras resolución: {e}")
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

        # Shares: vender todo. Truncar hacia abajo para no pedir más shares
        # de las disponibles (Fix Bug #15: round() puede redondear 9.48748 → 9.49
        # y Polymarket rechaza con "not enough balance").
        shares_to_sell = math.floor(size * 100) / 100
        if shares_to_sell < 0.1:
            dl.append(f"    ⚠ {outcome} {title} | muy pocas shares ({shares_to_sell})")
            continue

        estimated_return = round(shares_to_sell * sell_price, 2)

        # No intentar vender posiciones que no valen nada
        # Polymarket rechaza ventas con "not enough balance/allowance" si es muy poco
        if estimated_return < 0.10:
            dl.append(f"     {outcome} {title} | valor ~${estimated_return:.2f} < $0.10, no vale la pena")
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

            # v10.6.17: registrar cooldown post-SL para bloquear re-entrada en la misma ciudad
            if sell_type in ("stop_loss", "stop_loss_intra") and city:
                _sl_cooldown_register(city)
                dl.append(f"    🔒 SL cooldown activado: {city} bloqueada {SL_CITY_COOLDOWN_HOURS}h")

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
                f"<i> Pendiente de fill — precio real puede diferir</i>"
            )

            # v10.3 Fix Bug #7: Registrar como SELL_PENDING, NO como SELL
            # Solo se convierte en SELL cuando audit_check_sell_fills confirma el fill.
            # Bug real: Chongqing stop-loss se registró como vendida pero la orden
            # nunca se llenó (nadie quiso comprar a 1¢). Performance.json mentía.
            track_trade("SELL_PENDING",
                reason=sell_type,
                decision_note=reason,
                decision_source="manage_positions",
                city=city,
                side=outcome,
                date=market_date,
                question=title_full,
                token_id=asset_id,
                condition=parsed_sell.get("condition", "") if parsed_sell else "",
                price=sell_price,
                trigger_price=cur_price,
                shares=shares_to_sell,
                return_est=estimated_return,
                avg_buy_price=float(p.get("avgPrice", 0)),
                pnl_pct=pct,
                pnl_cash=float(p.get("cashPnl", 0)),
                current_value=float(p.get("currentValue", 0)),
                order_id=oid,
            )

            # Registrar para verificar fill en próximo ciclo
            audit_register_pending_sell(
                order_id=oid, city=city,
                side=outcome, price=sell_price, shares=shares_to_sell,
                return_est=estimated_return, reason=sell_type, token_id=asset_id,
            )

        except Exception as e:
            dl.append(f"     ERROR vendiendo {outcome} {title}: {e}")
            log.error(f"Error vendiendo posición: {e}")

    dl.append(f"\n  Resultado: {n_sold} vendidas | ~${capital_freed:.2f} liberados")
    if lifecycle_needs_sync:
        try:
            _sync_trade_lifecycle_from_sources()
        except Exception as e:
            log.warning(f"Error sincronizando trade_lifecycle tras resolución: {e}")
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

def _within_cooldown(last_reeval_at, cooldown_min, now_utc):
    """Devuelve True si last_reeval_at está dentro de cooldown_min minutos desde now_utc."""
    if not last_reeval_at:
        return False
    try:
        last_dt = datetime.fromisoformat(last_reeval_at.replace("Z", "+00:00"))
        return (now_utc - last_dt).total_seconds() < cooldown_min * 60
    except Exception:
        return False


def _log_shadow_intra_reeval_trigger(state, position, entry_ctx, fresh, pct_pnl):
    """Registra un trigger shadow y manda Telegram si pasó >60 min desde el último."""
    now = datetime.now(timezone.utc)
    trigger = {
        "ts": now.isoformat(),
        "city": fresh.get("city", ""),
        "side": position.get("outcome", ""),
        "token_id": position.get("asset", ""),
        "entry_price": float(entry_ctx.get("price") or 0),
        "cur_price": float(position.get("curPrice") or 0),
        "pnl_pct": pct_pnl,
        "fresh_edge_pct": fresh["edge_pct"],
        "entry_edge_pct": float(entry_ctx.get("edge_pct") or 0),
        "our_prob_now": fresh["our_prob"],
        "our_prob_entry": (float(entry_ctx.get("our_prob") or 0)) / 100.0,  # entry guarda como %; normalizar
        "would_sell": True,
    }
    shadow_log = state.setdefault("shadow_log", {
        "triggers": [],
        "first_trigger_at": "",
        "last_telegram_at": "",
        "review_alert_sent": False,
    })
    shadow_log.setdefault("triggers", []).append(trigger)
    # Cap a últimos 200 triggers para no crecer sin control
    shadow_log["triggers"] = shadow_log["triggers"][-200:]
    if not shadow_log.get("first_trigger_at"):
        shadow_log["first_trigger_at"] = now.isoformat()
    # Telegram rate-limit 60 min
    last_tg = shadow_log.get("last_telegram_at", "")
    if not last_tg or (now - datetime.fromisoformat(last_tg.replace("Z", "+00:00"))).total_seconds() >= 3600:
        msg = (
            f"\U0001f9ea <b>[INTRA-REEVAL SHADOW] habría vendido</b>\n"
            f"{position.get('outcome', '?')} {fresh.get('city', '?')} PnL={pct_pnl:+.1f}%\n"
            f"Edge entry={trigger['entry_edge_pct']:+.1f}% → ahora={fresh['edge_pct']:+.1f}%\n"
            f"Precio entry=${trigger['entry_price']:.2f} → ahora=${trigger['cur_price']:.2f}\n"
            f"<i>Shadow mode: no se vende. Review a los 7 días del primer trigger.</i>"
        )
        try:
            send_telegram(msg)
            shadow_log["last_telegram_at"] = now.isoformat()
        except Exception:
            pass


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

        observed_positions = []
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

            observed_positions.append(p)

        if observed_positions:
            record_trade_lifecycle_position_snapshots(
                observed_positions,
                source="intra_cycle_monitor",
                stage="sl_tp_check",
            )

        # TP dinámico: lookup our_prob de entrada por token_id
        # También construimos _lc_by_token_intra_full con el dict completo del entry_context
        try:
            _lc_data_intra = load_trade_lifecycle_data()
            _lc_by_token_intra = {}
            _lc_by_token_intra_full = {}
            for r in _lc_data_intra.get("records", []):
                tid = str(r.get("token_id", "") or "").strip()
                if not tid:
                    continue
                ec = r.get("entry_context") or {}
                if ec.get("our_prob") is not None:
                    try:
                        _lc_by_token_intra[tid] = float(ec["our_prob"])
                    except (ValueError, TypeError):
                        pass
                _lc_by_token_intra_full[tid] = ec
        except Exception:
            _lc_by_token_intra = {}
            _lc_by_token_intra_full = {}

        # v10.6.30: estado de re-evaluación intra-ciclo (purgar cooldown por token_ids observados)
        observed_token_ids = {p.get("asset", "") for p in observed_positions}
        reeval_state = load_intra_reeval_state(observed_token_ids=observed_token_ids)
        # Cache de forecasts local a esta ejecución (idéntico patrón a manage_positions)
        forecast_cache = {}
        now_utc = datetime.now(timezone.utc)
        reeval_state_changed = False

        n_checked = 0
        n_sold = 0
        n_guard_skipped = 0

        # v10.6.40: estado del guard SL_intra (cargado una vez por ciclo intra)
        guard_state = load_sl_intra_guard_state()
        guard_state_changed = False
        if SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION and not guard_state.get("guard_started_at"):
            guard_state["guard_started_at"] = now_utc.isoformat()
            guard_state_changed = True

        for p in observed_positions:
            title_full = p.get("title", "")
            asset_id = p.get("asset", "")
            cur_price = float(p.get("curPrice", 0))

            pct_pnl = float(p.get("percentPnl", 0))
            n_checked += 1

            # Determinar si hay que vender (TP dinámico por convicción)
            _entry_prob_intra = _lc_by_token_intra.get(asset_id)
            _entry_ctx_intra = _lc_by_token_intra_full.get(asset_id, {})
            _entry_price_intra = _entry_ctx_intra.get("price")
            if _entry_price_intra is not None:
                try:
                    _entry_price_intra = float(_entry_price_intra)
                except (ValueError, TypeError):
                    _entry_price_intra = None
            effective_tp_intra = effective_tp_pct(_entry_price_intra, _entry_prob_intra)

            # v10.6.40: guard SL_intra para condition=exact + days_ahead<=N.
            # Se calcula condition y days_ahead aquí; en el peor caso vuelve a parsear el title abajo,
            # pero el coste es despreciable y mantiene la lógica local al bloque de decisión.
            _guard_parsed = parse_temperature_question(title_full) or {}
            _guard_condition = (_guard_parsed.get("condition") or "").lower()
            _guard_days_ahead = _entry_ctx_intra.get("days_ahead")
            if _guard_days_ahead is None:
                _guard_date_str = _guard_parsed.get("date_str")
                _guard_market_date = date_text_to_iso(_guard_date_str) if _guard_date_str else ""
                if _guard_market_date:
                    try:
                        _guard_days_ahead = (date.fromisoformat(_guard_market_date) - date.today()).days
                    except (ValueError, TypeError):
                        _guard_days_ahead = None
            maybe_record_sl_intra_hazard_event(
                p,
                condition=_guard_condition,
                days_ahead=_guard_days_ahead,
                entry_price=_entry_price_intra,
                now_utc=now_utc,
            )
            _guard_skip_sl = (
                pct_pnl <= STOP_LOSS_PCT
                and _sl_intra_guard_should_skip(_guard_condition, _guard_days_ahead)
            )

            sell_type = None
            if _guard_skip_sl:
                # Guard activo: NO vender por SL_intra. Registrar skip + telegram (rate-limited).
                _city_for_skip = parse_city_from_title(title_full[:50]) or ""
                _outcome_for_skip = p.get("outcome", "?")
                _entry_pct_pnl_event = {
                    "skipped_at": now_utc.isoformat(),
                    "token_id": asset_id,
                    "city": _city_for_skip,
                    "outcome": _outcome_for_skip,
                    "title": title_full[:120],
                    "condition": _guard_condition,
                    "days_ahead": _guard_days_ahead,
                    "pct_pnl_at_skip": round(pct_pnl, 2),
                    "entry_price": _entry_price_intra,
                    "cur_price": cur_price,
                    "current_value": float(p.get("currentValue", 0)),
                    "shares": float(p.get("size", 0)),
                    "bot_version": BOT_VERSION,
                }
                _entry_pct_pnl_event.update(_sl_intra_guard_cohort_fields(_entry_pct_pnl_event.get("pct_pnl_at_skip")))
                guard_state.setdefault("skips", []).append(_entry_pct_pnl_event)
                guard_state_changed = True
                n_guard_skipped += 1
                log.info(
                    f"[INTRA-SL] GUARD skip: {_outcome_for_skip} {_city_for_skip} "
                    f"cond={_guard_condition} days={_guard_days_ahead} pnl={pct_pnl:+.1f}%"
                )
                _last_tg = guard_state.get("last_telegram_at", "")
                _send_tg = True
                if _last_tg:
                    try:
                        _last_tg_dt = datetime.fromisoformat(_last_tg.replace("Z", "+00:00"))
                        if (now_utc - _last_tg_dt).total_seconds() < SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN * 60:
                            _send_tg = False
                    except (ValueError, TypeError):
                        pass
                if _send_tg:
                    try:
                        send_telegram(
                            f"\U0001f6e1️ <b>[GUARD SL_intra] skip</b>\n"
                            f"{_outcome_for_skip} {_city_for_skip} "
                            f"({_guard_condition}, days={_guard_days_ahead})\n"
                            f"PnL actual: <b>{pct_pnl:+.1f}%</b> "
                            f"(${float(p.get('cashPnl', 0)):+.2f})\n"
                            f"Entry ${(_entry_price_intra or 0):.2f} → ahora ${cur_price:.2f}\n"
                            f"<i>v10.6.40: SL_intra suspendido para exact+days<={SL_INTRA_GUARD_DAYS_AHEAD_MAX}. "
                            f"Esperamos resolución del mercado.</i>"
                        )
                        guard_state["last_telegram_at"] = now_utc.isoformat()
                    except Exception:
                        pass
            elif pct_pnl <= STOP_LOSS_PCT:
                sell_type = "stop_loss_intra"
                icon, type_label = "\U0001f53b", "Stop-loss"
            elif pct_pnl >= effective_tp_intra:
                sell_type = "take_profit_intra"
                icon, type_label = "\U0001f4b0", "Take-profit"

            # v10.6.30: re-evaluación condicional intra-ciclo (solo si master switch activo y sin SL/TP)
            if INTRA_REEVAL_ENABLED and not sell_type:
                entry_ctx = _lc_by_token_intra_full.get(asset_id, {})
                entry_price_raw = entry_ctx.get("price")
                if entry_price_raw is not None:
                    try:
                        entry_price = float(entry_price_raw)
                        drift_pp = abs(cur_price - entry_price) * 100
                        if drift_pp >= INTRA_REEVAL_PRICE_DRIFT_PP:
                            # Cooldown check
                            last_reeval = reeval_state["cooldown"].get(asset_id, {}).get("last_reeval_at", "")
                            if not _within_cooldown(last_reeval, INTRA_REEVAL_COOLDOWN_MIN, now_utc):
                                fresh = recompute_position_edge(p, forecast_cache)
                                if fresh is not None:
                                    reeval_state["cooldown"][asset_id] = {
                                        "last_reeval_at": now_utc.isoformat(),
                                        "last_edge_pct": fresh["edge_pct"],
                                    }
                                    reeval_state_changed = True
                                    if fresh["edge_pct"] < INTRA_REEVAL_EDGE_THRESHOLD:
                                        if INTRA_REEVAL_SHADOW_MODE:
                                            # SHADOW: log + telegram (rate-limited) — NO vende
                                            _log_shadow_intra_reeval_trigger(
                                                reeval_state, p, entry_ctx, fresh, pct_pnl
                                            )
                                        else:
                                            # REAL: marca venta como reeval_intra
                                            sell_type = "reeval_intra"
                                            icon, type_label = "\U0001f504", "Re-evaluación intra"
                    except (ValueError, TypeError):
                        pass

            if not sell_type:
                continue

            outcome = p.get("outcome", "?")
            size = float(p.get("size", 0))
            title = title_full[:50]
            city = parse_city_from_title(title)
            parsed = parse_temperature_question(title_full)
            market_date = date_text_to_iso(parsed["date_str"]) if parsed and parsed.get("date_str") else ""

            sell_price = round(max(0.01, cur_price - SELL_AGGRESSION), 2)
            # Truncar hacia abajo (Fix Bug #15: igual que manage_positions)
            shares_to_sell = math.floor(size * 100) / 100
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
                    f"Venta: {shares_to_sell}sh × ${sell_price:.2f} (precio límite)\n"
                    f"PnL: {pct_pnl:+.1f}% (${float(p.get('cashPnl', 0)):+.2f})\n"
                    f"<i>Entre ciclos — próximo ciclo confirmará fill; precio real puede diferir</i>"
                )

                pct = float(p.get("percentPnl", 0))
                track_trade("SELL_PENDING",
                    reason=sell_type,
                    decision_note=f"[INTRA-SL] {type_label} {pct:+.1f}%",
                    decision_source="intra_cycle_monitor",
                    city=city,
                    side=outcome,
                    date=market_date,
                    question=title_full,
                    token_id=asset_id,
                    condition=parsed.get("condition", "") if parsed else "",
                    price=sell_price,
                    trigger_price=cur_price,
                    shares=shares_to_sell,
                    return_est=estimated_return,
                    avg_buy_price=float(p.get("avgPrice", 0)),
                    pnl_pct=pct,
                    pnl_cash=float(p.get("cashPnl", 0)),
                    current_value=float(p.get("currentValue", 0)),
                    order_id=oid,
                )

                audit_register_pending_sell(
                    order_id=oid, city=city,
                    side=outcome, price=sell_price, shares=shares_to_sell,
                    return_est=estimated_return, reason=sell_type, token_id=asset_id,
                )
                if sell_type in ("stop_loss", "stop_loss_intra") and city:
                    _sl_cooldown_register(city)
                    log.info(f"[INTRA-SL] SL cooldown activado: {city} {SL_CITY_COOLDOWN_HOURS}h")

            except Exception as e:
                log.error(f"[INTRA-SL] Error vendiendo {outcome} {city}: {e}")

        # v10.6.30: guardar reeval_state al final (no a mitad)
        if reeval_state_changed or INTRA_REEVAL_ENABLED:
            save_intra_reeval_state(reeval_state)

        # v10.6.40: guardar guard_state si hubo cambios.
        if guard_state_changed:
            save_sl_intra_guard_state(guard_state)

        log.info(
            f"[INTRA-SL] Check: {n_checked} posiciones, {n_sold} vendidas, "
            f"{n_guard_skipped} skipped por guard"
        )

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
FORECAST_AUDIT_KEY = "forecast_vs_real"  # Legacy key: hoy guarda forecast original vs forecast posterior Open-Meteo.
OBSERVED_AUDIT_KEY = "observed_vs_forecast"  # NOAA NCEI observed proxy vs forecast original.
NOAA_NCEI_ACCESS_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
NOAA_OBSERVED_LAG_DAYS = 2
OBSERVED_FORECAST_MIN_SAMPLE = 3
OBSERVED_FORECAST_GLOBAL_TARGET = 10
OBSERVED_AUDIT_MAX_SUCCESSES_PER_RUN = 10
OBSERVED_AUDIT_MAX_ATTEMPTS_PER_RUN = 40
OBSERVED_AUDIT_FAIL_COOLDOWN_HOURS = 12

def load_audit_data():
    """Carga datos de auditoría acumulativos."""
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                data.setdefault("pending_sells", [])
                data.setdefault(FORECAST_AUDIT_KEY, [])
                data.setdefault(OBSERVED_AUDIT_KEY, [])
                data.setdefault("errors", [])
                return data
        except Exception:
            pass
    return {"pending_sells": [], FORECAST_AUDIT_KEY: [], OBSERVED_AUDIT_KEY: [], "errors": []}


def save_audit_data(data):
    """Guarda datos de auditoría."""
    # Limitar tamaño
    for key in ["pending_sells", FORECAST_AUDIT_KEY, OBSERVED_AUDIT_KEY, "errors"]:
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
                dl.append(f"   Venta pendiente >12h: {sell.get('city', '?')} {sell.get('side', '?')} | ${sell.get('price', 0):.2f}")
                still_pending.append(sell)
            else:
                still_pending.append(sell)
        else:
            # Ya no esta en open_orders: normalmente se lleno. Intentar leer fills reales.
            enriched_sell = _enrich_pending_sell_with_fill(client, sell)
            filled.append(enriched_sell)
            fill_value = _safe_float(enriched_sell.get("fill_value"))
            fill_price = _safe_float(enriched_sell.get("fill_price"))
            if fill_value is not None and fill_price is not None:
                dl.append(
                    f"  ✅ Venta llenada: {sell.get('city', '?')} {sell.get('side', '?')} | "
                    f"${fill_value:.2f} reales @ ${fill_price:.4f}"
                )
            else:
                dl.append(f"  ✅ Venta llenada: {sell.get('city', '?')} {sell.get('side', '?')} | ~${sell.get('return_est', 0):.2f} estimados")

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
                + "\n".join(_format_confirmed_sell_fill_line(s) for s in filled)
            )


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_first_number(payload, keys):
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = _safe_float(payload.get(key))
        if value is not None:
            return value
    return None


def _order_id_seen_in_trade(trade, order_id):
    if not order_id:
        return True
    if not isinstance(trade, dict):
        return False
    wanted = str(order_id).lower()
    for key in [
        "order_id",
        "orderID",
        "orderId",
        "maker_order_id",
        "makerOrderId",
        "taker_order_id",
        "takerOrderId",
    ]:
        value = trade.get(key)
        if value is not None and str(value).lower() == wanted:
            return True
    try:
        return wanted in json.dumps(trade, ensure_ascii=False).lower()
    except Exception:
        return False


def _extract_fill_summary_from_trades(trades, order_id=""):
    rows = trades.get("data", []) if isinstance(trades, dict) else (trades or [])
    if not isinstance(rows, list):
        return None

    matched = [t for t in rows if isinstance(t, dict) and _order_id_seen_in_trade(t, order_id)]
    if not matched:
        return None

    total_size = 0.0
    total_value = 0.0
    normalized = []
    for trade in matched:
        price = _get_first_number(trade, ["price", "match_price", "fill_price", "execution_price"])
        size = _get_first_number(trade, ["size", "shares", "filled_size", "matched_size"])
        value = _get_first_number(trade, ["value", "notional", "proceeds", "usdc_amount", "amount_usdc", "amount"])
        if value is None and price is not None and size is not None:
            value = price * size
        if price is None and value is not None and size not in (None, 0):
            price = value / size
        if price is None or size in (None, 0):
            continue
        total_size += size
        total_value += value if value is not None else price * size
        normalized.append({
            "id": trade.get("id", ""),
            "price": round(price, 6),
            "size": round(size, 6),
            "value": round(value if value is not None else price * size, 6),
            "timestamp": trade.get("timestamp") or trade.get("match_time") or trade.get("created_at") or "",
            "transaction_hash": trade.get("transaction_hash") or trade.get("transactionHash") or "",
        })

    if total_size <= 0:
        return None

    return {
        "fill_price": round(total_value / total_size, 6),
        "fill_shares": round(total_size, 6),
        "fill_value": round(total_value, 6),
        "fill_source": "clob_trades",
        "fill_count": len(normalized),
        "fill_trades": normalized[:10],
    }


def _extract_fill_summary_from_order(order):
    if not isinstance(order, dict):
        return None
    matched_size = _get_first_number(order, ["size_matched", "matched_size", "filled_size"])
    if matched_size is None or matched_size <= 0:
        return None
    price = _get_first_number(order, ["average_price", "avg_price", "filled_price"])
    if price is None:
        return None
    return {
        "fill_price": round(price, 6),
        "fill_shares": round(matched_size, 6),
        "fill_value": round(price * matched_size, 6),
        "fill_source": "clob_order",
        "fill_count": None,
    }


def _fetch_sell_fill_summary(client, pending_sell):
    order_id = str((pending_sell or {}).get("order_id", "") or "").strip()
    if not order_id:
        return None

    try:
        trades = client.get_trades(TradeParams(id=order_id), only_first_page=True)
        summary = _extract_fill_summary_from_trades(trades, order_id)
        if summary:
            return summary
    except Exception as e:
        log.warning(f"fill lookup get_trades fallo para {order_id}: {e}")

    token_id = str((pending_sell or {}).get("token_id", "") or "").strip()
    if token_id:
        try:
            trades = client.get_trades(TradeParams(asset_id=token_id), only_first_page=True)
            summary = _extract_fill_summary_from_trades(trades, order_id)
            if summary:
                return summary
        except Exception as e:
            log.warning(f"fill lookup get_trades(asset_id) fallo para {order_id}: {e}")

    try:
        order = client.get_order(order_id)
        summary = _extract_fill_summary_from_order(order)
        if summary:
            return summary
    except Exception as e:
        log.warning(f"fill lookup get_order fallo para {order_id}: {e}")

    return None


def _enrich_pending_sell_with_fill(client, sell):
    enriched = dict(sell or {})
    summary = _fetch_sell_fill_summary(client, enriched)
    if summary:
        enriched.update(summary)
    return enriched


def _format_confirmed_sell_fill_line(sell):
    fill_value = _safe_float(sell.get("fill_value"))
    fill_price = _safe_float(sell.get("fill_price"))
    if fill_value is not None and fill_price is not None:
        return f"  {sell.get('city','?')} {sell.get('side','?')} ${fill_value:.2f} reales @ ${fill_price:.4f}"
    return f"  {sell.get('city','?')} {sell.get('side','?')} ~${sell.get('return_est',0):.2f} estimados"


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
    filled_by_id = {
        s.get("order_id", ""): s
        for s in filled
        if s.get("order_id", "")
    }

    updated = 0
    updated_entries = []
    for entry in history:
        if entry.get("action") != "SELL_PENDING":
            continue
        oid = entry.get("order_id", "")
        if oid in filled_ids:
            fill_info = filled_by_id.get(oid, {})
            fill_price = _safe_float(fill_info.get("fill_price"))
            fill_shares = _safe_float(fill_info.get("fill_shares"))
            fill_value = _safe_float(fill_info.get("fill_value"))
            entry["action"] = "SELL"
            entry["fill_confirmed"] = datetime.now(timezone.utc).isoformat()
            if fill_price is not None and fill_value is not None:
                entry["limit_price"] = entry.get("limit_price", entry.get("price"))
                entry["price"] = round(fill_price, 6)
                entry["fill_price"] = round(fill_price, 6)
                entry["fill_value"] = round(fill_value, 2)
                entry["return_est_limit"] = entry.get("return_est")
                entry["return_est"] = round(fill_value, 2)
                entry["fill_source"] = fill_info.get("fill_source", "")
                if fill_shares is not None:
                    entry["fill_shares"] = round(fill_shares, 6)
                    entry["shares"] = round(fill_shares, 6)
                if fill_info.get("fill_count") is not None:
                    entry["fill_count"] = fill_info.get("fill_count")
                if fill_info.get("fill_trades"):
                    entry["fill_trades"] = fill_info.get("fill_trades")
                avg_buy_price = _safe_float(entry.get("avg_buy_price"))
                shares_for_pnl = _safe_float(entry.get("shares"))
                if avg_buy_price is not None and shares_for_pnl not in (None, 0):
                    cost = avg_buy_price * shares_for_pnl
                    if cost > 0:
                        entry["pnl_cash"] = round(fill_value - cost, 2)
                        entry["pnl_pct"] = round((fill_value / cost - 1.0) * 100, 2)
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
            dl.append(f"   performance.json: {updated} entradas actualizadas")
            for entry in updated_entries:
                try:
                    update_postmortem(entry.get("action", ""), entry)
                except Exception as e:
                    log.warning(f"Error sincronizando postmortem con performance: {e}")
            try:
                _sync_trade_lifecycle_from_sources()
            except Exception as e:
                log.warning(f"Error sincronizando trade_lifecycle tras fills: {e}")
        except Exception as e:
            log.warning(f"Error actualizando performance.json: {e}")


def audit_register_pending_sell(order_id, city, side, price, shares, return_est, reason, token_id=""):
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
        "token_id": token_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_audit_data(audit)


def _parse_noaa_tmp_c(raw_value):
    """Convierte TMP de NOAA (+0123,1) a grados C o None si falta."""
    if raw_value in (None, ""):
        return None
    value_str = str(raw_value).strip()
    if not value_str:
        return None
    value_token = value_str.split(",", 1)[0].strip()
    try:
        value_tenths_c = int(value_token)
    except ValueError:
        return None
    if abs(value_tenths_c) >= 9999:
        return None
    return round(value_tenths_c / 10.0, 1)

def fetch_noaa_daily_tmax(noaa_daily_station_id, date_iso, retries=3, delay=5):
    """
    Devuelve TMAX diaria NOAA NCEI si existe en daily-summaries.

    Esta ruta es mas honesta para comparar forecast vs maxima diaria, pero la
    disponibilidad puede ir con mas lag que NOAA_OBSERVED_LAG_DAYS.
    """
    if not noaa_daily_station_id or not date_iso:
        return None

    try:
        market_date = date.fromisoformat(date_iso)
    except ValueError:
        return None

    days_ago = (datetime.now(timezone.utc).date() - market_date).days
    if days_ago < NOAA_OBSERVED_LAG_DAYS:
        return None

    params = urllib.parse.urlencode({
        "dataset": "daily-summaries",
        "stations": noaa_daily_station_id,
        "startDate": date_iso,
        "endDate": date_iso,
        "dataTypes": "TMAX",
        "format": "json",
        "units": "metric",
    })
    url = f"{NOAA_NCEI_ACCESS_URL}?{params}"

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-bot/0.10")
            resp = urllib.request.urlopen(req, timeout=30)
            rows = json.loads(resp.read())
            if not isinstance(rows, list):
                return None

            for row in rows:
                try:
                    return round(float(row.get("TMAX")), 1)
                except (TypeError, ValueError):
                    continue
            return None
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                log.warning(
                    f"NOAA daily-summaries error (intento {attempt+1}/{retries}) "
                    f"{noaa_daily_station_id} {date_iso}: {e} - reintentando en {delay}s"
                )
                time.sleep(delay)

    if last_error:
        log.warning(f"NOAA daily-summaries error {noaa_daily_station_id} {date_iso}: {last_error}")
    return None


def _fetch_noaa_observed_max_hourly(noaa_station_id, date_iso, retries=3, delay=5):
    """
    Devuelve la maxima observada NOAA NCEI para una fecha.

    Usa Access Data Service con station_id explicito (USAF+WBAN) ya resuelto en
    RESOLUTION_ICAO. Si la fecha es demasiado reciente o la consulta falla,
    devuelve None y deja solo warning en logs.
    """
    if not noaa_station_id or not date_iso:
        return None

    try:
        market_date = date.fromisoformat(date_iso)
    except ValueError:
        return None

    days_ago = (datetime.now(timezone.utc).date() - market_date).days
    if days_ago < NOAA_OBSERVED_LAG_DAYS:
        return None

    params = urllib.parse.urlencode({
        "dataset": "global-hourly",
        "stations": noaa_station_id,
        "startDate": f"{date_iso}T00:00:00",
        "endDate": f"{date_iso}T23:59:59",
        "dataTypes": "TMP",
        "format": "json",
    })
    url = f"{NOAA_NCEI_ACCESS_URL}?{params}"

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-bot/0.10")
            resp = urllib.request.urlopen(req, timeout=30)
            rows = json.loads(resp.read())
            if not isinstance(rows, list):
                return None

            observed_temps = []
            for row in rows:
                temp_c = _parse_noaa_tmp_c(row.get("TMP"))
                if temp_c is not None:
                    observed_temps.append(temp_c)

            if not observed_temps:
                return None
            return max(observed_temps)
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                log.warning(
                    f"NOAA observed proxy error (intento {attempt+1}/{retries}) "
                    f"{noaa_station_id} {date_iso}: {e} — reintentando en {delay}s"
                )
                time.sleep(delay)

    if last_error:
        log.warning(f"NOAA observed proxy error {noaa_station_id} {date_iso}: {last_error}")
    return None


def fetch_noaa_observed_max(noaa_station_id, date_iso, daily_station_id="", retries=3, delay=5):
    """
    Devuelve la maxima observada NOAA NCEI para una fecha y el dataset usado.

    Orden de preferencia:
      1. daily-summaries con TMAX si existe noaa_daily_station_id
      2. fallback a global-hourly reconstruyendo el maximo desde TMP
    """
    observed_daily_tmax = fetch_noaa_daily_tmax(
        daily_station_id,
        date_iso,
        retries=retries,
        delay=delay,
    )
    if observed_daily_tmax is not None:
        return observed_daily_tmax, "daily-summaries_tmax"

    observed_hourly_tmax = _fetch_noaa_observed_max_hourly(
        noaa_station_id,
        date_iso,
        retries=retries,
        delay=delay,
    )
    if observed_hourly_tmax is not None:
        return observed_hourly_tmax, "global-hourly_tmp_max"
    return None, None


def _iter_recent_noaa_cycle_markets(limit_cycles=12):
    """Itera snapshots ligeros de mercados escaneados para auditoria NOAA."""
    records = []

    summary_loader = globals().get("load_cycle_summary_data")
    if callable(summary_loader):
        try:
            cycle_summary = summary_loader()
        except Exception:
            cycle_summary = {}
        if isinstance(cycle_summary, dict):
            records.append(cycle_summary)

    history_loader = globals().get("load_cycle_history")
    if callable(history_loader):
        try:
            history = history_loader(limit=limit_cycles)
        except Exception:
            history = []
        if isinstance(history, list):
            records.extend(reversed(history))

    seen_cycles = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        cycle_key = (
            record.get("cycle_number"),
            record.get("logic_cycle_number"),
            record.get("timestamp_utc"),
        )
        if cycle_key in seen_cycles:
            continue
        seen_cycles.add(cycle_key)

        scanned_markets = record.get("scanned_markets", [])
        if not isinstance(scanned_markets, list):
            continue
        for item in scanned_markets:
            if isinstance(item, dict):
                yield item


def _get_noaa_candidate_dates(city, already_checked=None, limit=3):
    """
    Devuelve fechas NOAA pendientes usando una base durable de señales shadow.
    """
    city = str(city or "").strip()
    already_checked = already_checked or set()
    if not city or city not in OBSERVED_AUDIT_CITIES:
        return []

    resolution_meta = RESOLUTION_ICAO.get(city, {})
    if not resolution_meta.get("noaa_station_id"):
        return []

    today_utc = datetime.now(timezone.utc).date()
    candidates = []
    seen_dates = set()

    seed_rows = []
    shadow_loader = globals().get("load_shadow_city_tracking")
    if callable(shadow_loader):
        try:
            shadow_tracking = shadow_loader()
        except Exception:
            shadow_tracking = {}
        if isinstance(shadow_tracking, dict):
            for row in shadow_tracking.get("directional_history", []):
                if isinstance(row, dict):
                    seed_rows.append(row)
            if not seed_rows:
                for row in shadow_tracking.get("recent_opportunities", []):
                    if isinstance(row, dict):
                        seed_rows.append(row)

    durable_rows = _merge_shadow_signal_history([], seed_rows) if seed_rows else []
    if durable_rows:
        durable_rows = sorted(
            durable_rows,
            key=lambda item: (
                _normalize_shadow_market_date(item.get("date", "")),
                str(item.get("last_seen_at", "") or item.get("first_seen_at", "")),
            ),
            reverse=True,
        )

    for item in durable_rows:
        if str(item.get("city", "") or "").strip() != city:
            continue

        market_date = _normalize_shadow_market_date(item.get("date", "") or item.get("date_iso", ""))
        if not market_date:
            continue

        key = f"{city}|{market_date}"
        if key in already_checked or market_date in seen_dates:
            continue

        try:
            days_ago = (today_utc - date.fromisoformat(market_date)).days
        except ValueError:
            continue

        if days_ago < NOAA_OBSERVED_LAG_DAYS:
            continue

        try:
            forecast_temp = round(float(item.get("forecast_max")), 1)
        except (TypeError, ValueError):
            continue

        candidates.append({
            "city": city,
            "date": market_date,
            "forecast_max": forecast_temp,
            "side": item.get("side"),
            "edge_pct": item.get("best_edge_pct", item.get("edge_pct")),
        })
        seen_dates.add(market_date)
        already_checked.add(key)
        if len(candidates) >= limit:
            break

    if candidates:
        return candidates

    for item in _iter_recent_noaa_cycle_markets():
        if str(item.get("city", "") or "").strip() != city:
            continue

        market_date = str(item.get("date", "") or item.get("date_iso", "") or "").strip()
        if not market_date:
            continue

        key = f"{city}|{market_date}"
        if key in already_checked or market_date in seen_dates:
            continue

        try:
            days_ago = (today_utc - date.fromisoformat(market_date)).days
        except ValueError:
            continue

        if days_ago < NOAA_OBSERVED_LAG_DAYS:
            continue

        try:
            forecast_temp = round(float(item.get("forecast_max")), 1)
        except (TypeError, ValueError):
            continue

        candidates.append({
            "city": city,
            "date": market_date,
            "forecast_max": forecast_temp,
            "side": None,
            "edge_pct": None,
        })
        seen_dates.add(market_date)
        already_checked.add(key)
        if len(candidates) >= limit:
            break

    return candidates


def audit_check_resolution_truth(dl):
    """
    Observed proxy audit: forecast original vs observado NOAA NCEI.

    Importante: NOAA no es la fuente real de settlement de Polymarket. Esta capa
    vive separada de forecast_vs_real y se guarda como observed_vs_forecast con
    source=noaa_ncei para no mezclar proxy observado con resolucion real.
    """
    if not os.path.exists(PERFORMANCE_FILE):
        return

    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            perf = json.load(f)
    except Exception:
        return

    audit = load_audit_data()
    observed_rows = [row for row in audit.get(OBSERVED_AUDIT_KEY, []) if isinstance(row, dict)]
    already_checked = set(
        f"{v.get('city')}|{v.get('date')}"
        for v in observed_rows
    )
    city_sample_counts = {}
    for row in observed_rows:
        city = str(row.get("city", "") or "").strip()
        if not city:
            continue
        city_sample_counts[city] = city_sample_counts.get(city, 0) + 1

    now_utc = datetime.now(timezone.utc)
    fail_cooldown_until = {}
    for raw_error in audit.get("errors", []):
        if not isinstance(raw_error, dict):
            continue
        if raw_error.get("source") != "noaa_ncei":
            continue
        if raw_error.get("kind") != "observed_vs_forecast_fetch_failed":
            continue
        city = str(raw_error.get("city", "") or "").strip()
        market_date = str(raw_error.get("date", "") or "").strip()
        if not city or not market_date:
            continue
        attempted_at = str(raw_error.get("attempted_at", "") or "").strip()
        if not attempted_at:
            continue
        try:
            attempted_dt = datetime.fromisoformat(attempted_at)
        except ValueError:
            continue
        if attempted_dt.tzinfo is None:
            attempted_dt = attempted_dt.replace(tzinfo=timezone.utc)
        cooldown_until = attempted_dt + timedelta(hours=OBSERVED_AUDIT_FAIL_COOLDOWN_HOURS)
        key = f"{city}|{market_date}"
        previous_until = fail_cooldown_until.get(key)
        if previous_until is None or cooldown_until > previous_until:
            fail_cooldown_until[key] = cooldown_until

    def _candidate_sort_key(item):
        city = str(item.get("city", "") or "").strip()
        market_date = str(item.get("date", "") or "").strip()
        return (
            city_sample_counts.get(city, 0),
            0 if item.get("_source_kind") == "perf_buy" else 1,
            market_date,
        )

    def _merge_candidate(existing, candidate):
        if existing is None:
            return dict(candidate)

        merged = dict(existing)
        existing_source = 0 if existing.get("_source_kind") == "perf_buy" else 1
        candidate_source = 0 if candidate.get("_source_kind") == "perf_buy" else 1
        if candidate_source < existing_source:
            merged.update(candidate)
        else:
            if merged.get("side") is None and candidate.get("side") is not None:
                merged["side"] = candidate.get("side")
            if merged.get("edge_pct") is None and candidate.get("edge_pct") is not None:
                merged["edge_pct"] = candidate.get("edge_pct")
            if merged.get("forecast_max") is None and candidate.get("forecast_max") is not None:
                merged["forecast_max"] = candidate.get("forecast_max")
        return merged

    raw_candidates = []
    for entry in perf:
        if entry.get("action") != "BUY":
            continue
        city = entry.get("city", "")
        market_date = entry.get("date", "")
        if city not in OBSERVED_AUDIT_CITIES or not market_date:
            continue

        resolution_meta = RESOLUTION_ICAO.get(city, {})
        if not resolution_meta.get("noaa_station_id"):
            continue

        key = f"{city}|{market_date}"
        if key in already_checked:
            continue

        try:
            days_ago = (datetime.now(timezone.utc).date() - date.fromisoformat(market_date)).days
        except ValueError:
            continue

        if days_ago >= NOAA_OBSERVED_LAG_DAYS:
            candidate = {
                "city": city,
                "date": market_date,
                "forecast_max": entry.get("forecast_max"),
                "side": entry.get("side"),
                "edge_pct": entry.get("edge_pct"),
                "_source_kind": "perf_buy",
            }
            raw_candidates.append(candidate)

    for city in sorted(OBSERVED_AUDIT_CITIES):
        for candidate in _get_noaa_candidate_dates(city, already_checked=already_checked):
            candidate["_source_kind"] = "shadow_fallback"
            raw_candidates.append(candidate)

    deduped_candidates = {}
    for candidate in raw_candidates:
        city = str(candidate.get("city", "") or "").strip()
        market_date = str(candidate.get("date", "") or "").strip()
        if not city or not market_date:
            continue
        key = f"{city}|{market_date}"
        if key in already_checked:
            continue
        cooldown_until = fail_cooldown_until.get(key)
        if cooldown_until is not None and cooldown_until > now_utc:
            continue
        deduped_candidates[key] = _merge_candidate(deduped_candidates.get(key), candidate)

    to_check = sorted(deduped_candidates.values(), key=_candidate_sort_key)

    if not to_check:
        return

    n_checked = 0
    n_attempted = 0
    max_successes = int(globals().get("OBSERVED_AUDIT_MAX_SUCCESSES_PER_RUN", 10) or 10)
    max_attempts = int(globals().get("OBSERVED_AUDIT_MAX_ATTEMPTS_PER_RUN", 40) or 40)
    for entry in to_check:
        if n_checked >= max_successes or n_attempted >= max_attempts:
            break
        city = entry["city"]
        market_date = entry["date"]
        resolution_meta = RESOLUTION_ICAO.get(city, {})
        noaa_station_id = resolution_meta.get("noaa_station_id", "")
        noaa_daily_station_id = resolution_meta.get("noaa_daily_station_id", "")
        n_attempted += 1
        observed_temp_c, observed_dataset = fetch_noaa_observed_max(
            noaa_station_id,
            market_date,
            daily_station_id=noaa_daily_station_id,
        )
        if observed_temp_c is None:
            audit.setdefault("errors", []).append({
                "source": "noaa_ncei",
                "kind": "observed_vs_forecast_fetch_failed",
                "city": city,
                "date": market_date,
                "noaa_station_id": noaa_station_id,
                "noaa_daily_station_id": noaa_daily_station_id,
                "attempted_at": datetime.now(timezone.utc).isoformat(),
                "reason": "observed_temp_unavailable",
            })
            continue

        forecast_temp_c = entry.get("forecast_max", 0)
        error = round(observed_temp_c - forecast_temp_c, 1)
        record = {
            "city": city,
            "date": market_date,
            "icao_used": resolution_meta.get("icao", ""),
            "noaa_station_id": noaa_station_id,
            "noaa_daily_station_id": noaa_daily_station_id,
            "observed_temp_c": observed_temp_c,
            "forecast_temp_c": forecast_temp_c,
            "error_c": error,
            "abs_error_c": abs(error),
            "side": entry.get("side"),
            "edge_pct": entry.get("edge_pct"),
            "source": "noaa_ncei",
            "observed_dataset": observed_dataset or "unknown",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        audit[OBSERVED_AUDIT_KEY].append(record)
        n_checked += 1

        emoji = "✅" if abs(error) <= 1.0 else "⚠" if abs(error) <= 2.0 else ""
        dl.append(
            f"  {emoji} {city} {market_date}: "
            f"observado NOAA NCEI={observed_temp_c:.1f}°C | "
            f"prevision={forecast_temp_c:.1f}°C | "
            f"error={error:+.1f}°C"
            )

    if n_checked > 0:
        all_errors = [v["abs_error_c"] for v in audit.get(OBSERVED_AUDIT_KEY, []) if v.get("source") == "noaa_ncei"]
        if all_errors:
            avg_error = sum(all_errors) / len(all_errors)
            dl.append(
                f"  📊 Error medio observed proxy NOAA vs forecast: "
                f"{avg_error:.1f}°C ({len(all_errors)} mercados)"
            )
    elif n_attempted > 0:
        dl.append(
            f"  NOAA observed proxy sin casos nuevos: 0/{n_attempted} intentos útiles"
        )

    save_audit_data(audit)


def audit_check_open_meteo_forecast_drift(dl):
    """
    Pseudo-auditoria: forecast original vs forecast posterior de Open-Meteo.

    Importante: esto NO valida contra la fuente real de resolucion de
    Polymarket (Weather Underground). Solo mide cuanto deriva nuestro forecast
    original cuando volvemos a consultar el forecast endpoint de Open-Meteo
    para una fecha ya pasada.

    Se conserva la clave audit["forecast_vs_real"] por compatibilidad con el
    audit.json historico, pero sus registros nuevos son forecast-vs-forecast.
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
        for v in audit.get(FORECAST_AUDIT_KEY, [])
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

    # Reconsultar forecast Open-Meteo para cada ciudad/fecha pasada.
    checked_cities = {}
    n_checked = 0

    for entry in to_check[:10]:  # Max 10 por ciclo para no saturar API
        city = entry["city"]
        market_date = entry["date"]

        # Reusar el mismo forecast endpoint de Open-Meteo; esto no es WU.
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

        posterior_forecast_temp = fc[market_date]["temp_max"]
        forecast_temp = entry.get("forecast_max", 0)
        error = round(posterior_forecast_temp - forecast_temp, 1)

        record = {
            "city": city,
            "date": market_date,
            "forecast_original": forecast_temp,
            "forecast_posterior": posterior_forecast_temp,
            "comparison_type": "forecast_vs_forecast_posterior_open_meteo",
            "error_c": error,
            "abs_error_c": abs(error),
            "side": entry.get("side", "?"),
            "edge_pct": entry.get("edge_pct", 0),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        audit[FORECAST_AUDIT_KEY].append(record)
        n_checked += 1

        emoji = "✅" if abs(error) <= 1.0 else "⚠" if abs(error) <= 2.0 else ""
        dl.append(
            f"  {emoji} {city} {market_date}: "
            f"prevision original={forecast_temp:.1f}°C | "
            f"forecast posterior Open-Meteo={posterior_forecast_temp:.1f}°C | "
            f"deriva={error:+.1f}°C"
        )

    if n_checked > 0:
        # Calcular error medio global
        all_errors = [v["abs_error_c"] for v in audit.get(FORECAST_AUDIT_KEY, [])]
        if all_errors:
            avg_error = sum(all_errors) / len(all_errors)
            dl.append(
                f"  📊 Deriva media forecast original vs forecast posterior Open-Meteo: "
                f"{avg_error:.1f}°C ({len(all_errors)} mercados)"
            )

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


def _extract_threshold_canonical(question):
    """Normaliza el umbral de una pregunta de temperatura a Celsius."""
    parsed = parse_temperature_question(str(question or ""))
    if isinstance(parsed, dict):
        threshold = parsed.get("temp_threshold")
        if threshold is not None:
            try:
                value = float(threshold)
            except (TypeError, ValueError):
                value = None
            if value is not None:
                unit = str(parsed.get("unit", "C") or "C").upper()
                if unit == "F":
                    value = round((value - 32) * 5 / 9, 1)
                else:
                    value = round(value, 1)
                return value

    q = str(question or "")
    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*[^0-9A-Za-z]{0,3}\s*([FCfc])\s+or\s+(below|higher|above)",
        q,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"(?:above|below)\s+(-?\d+(?:\.\d+)?)\s*[^0-9A-Za-z]{0,3}\s*([FCfc])",
            q,
            re.IGNORECASE,
        )
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).upper()
    if unit == "F":
        value = round((value - 32) * 5 / 9, 1)
    else:
        value = round(value, 1)
    return value


# =============================================================
# FUNCIONES: MODELO
# =============================================================

def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


MODEL_SIGMA_REFERENCE = {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5}
EMPIRICAL_SIGMA = {
    "Chicago": {0: 2.57, 1: 2.59, 2: 3.0},
    "Atlanta": {0: 0.78, 1: 3.50, 2: 2.5},
    "Buenos Aires": {0: 1.10, 1: 1.5, 2: 2.0},
    "New York City": {0: 0.28, 1: 1.5, 2: 2.15},
    "Dallas": {0: 0.57, 1: 1.30, 2: 2.0},  # D0 actualizado NOAA n=3: MAE=0.57°C
}
EMPIRICAL_SIGMA_SAMPLES = {
    "Chicago": {0: 4, 1: 3, 2: 0},
    "Atlanta": {0: 5, 1: 1, 2: 0},
    "Buenos Aires": {0: 3, 1: 0, 2: 0},
    "New York City": {0: 2, 1: 0, 2: 1},
    "Dallas": {0: 3, 1: 1, 2: 0},  # D0: n=3 (NOAA sesión 82) — desbloquea sigma empírica
}
EMPIRICAL_SIGMA_GLOBAL = {0: 2.0, 1: 1.9, 2: 2.5, 3: 3.0}

# Corrección de sesgo sistemático Open-Meteo vs NOAA/WU, medida en sesión 82.
# Positivo = Open-Meteo subestima la temperatura real; se suma al forecast antes del cálculo de prob.
# Fuente: observed_vs_forecast NOAA daily-summaries (Chicago n=5, Atlanta n=5, Dallas n=3).
FORECAST_BIAS_C = {
    "Atlanta": 1.38,
    "Chicago": 1.40,
    "Dallas": 0.0,
}
_UNCERTAINTY_CITY_CONTEXT = None


def get_uncertainty(days_ahead, city=None):
    # v10.6: revertida a v10.3 — la sigma ampliada de v10.5 vendía posiciones ganadoras
    # en re-eval y bloqueaba entradas. El problema real es la fuente de datos (Open-Meteo
    # vs Weather Underground), no la confianza del modelo. Recoger datos con sigma original.
    selected_city = city or _UNCERTAINTY_CITY_CONTEXT
    city_samples = EMPIRICAL_SIGMA_SAMPLES.get(selected_city, {}) if selected_city else {}
    city_sigmas = EMPIRICAL_SIGMA.get(selected_city, {}) if selected_city else {}
    if int(city_samples.get(days_ahead, 0) or 0) >= 3 and city_sigmas.get(days_ahead) is not None:
        return float(city_sigmas[days_ahead])
    if days_ahead in EMPIRICAL_SIGMA_GLOBAL:
        return float(EMPIRICAL_SIGMA_GLOBAL[days_ahead])
    return MODEL_SIGMA_REFERENCE.get(days_ahead, 3.0 if days_ahead <= 5 else 3.5)


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


def estimate_prob_with_city(forecast_max, threshold_c, condition, days_ahead, threshold_high_c=None, city=None):
    global _UNCERTAINTY_CITY_CONTEXT
    previous_city = _UNCERTAINTY_CITY_CONTEXT
    _UNCERTAINTY_CITY_CONTEXT = city
    try:
        bias = FORECAST_BIAS_C.get(city, 0.0) if city else 0.0
        return estimate_prob(forecast_max + bias, threshold_c, condition, days_ahead, threshold_high_c)
    finally:
        _UNCERTAINTY_CITY_CONTEXT = previous_city


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
def _bump_reason_counter(counter, reason):
    if not reason:
        return
    counter[reason] = int(counter.get(reason, 0) or 0) + 1


def _classify_execution_failure_reason(message):
    text = str(message or "").lower()
    if not text:
        return "buy_order_error"
    if "invalid amount for a marketable buy order" in text:
        return "buy_min_notional"
    if "min size" in text or "lower than the minimum" in text:
        return "buy_min_size"
    if "insufficient" in text and "balance" in text:
        return "buy_insufficient_balance"
    return "buy_order_error"


def _normalize_buy_order_size(price, size):
    try:
        price = round(float(price or 0), 2)
        size = round(float(size or 0), 2)
    except Exception:
        return size
    if price <= 0 or size <= 0:
        return size
    notional = price * size
    if notional + 1e-9 >= ORDER_MIN_NOTIONAL:
        return size
    min_size = math.ceil((ORDER_MIN_NOTIONAL / price) * 100) / 100.0
    return round(max(size, min_size), 2)


def _parse_min_shares_from_error(message):
    """Extract required minimum shares from Polymarket 'lower than the minimum: N' error."""
    import re
    m = re.search(r'lower than the minimum:\s*(\d+(?:\.\d+)?)', str(message or ""), re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    return None


def build_cycle_slot_metrics(*, timestamp_utc, candidates, trades, selected, buys, skip_log_entries, execution_failures):
    slot_hour = timestamp_utc.hour if isinstance(timestamp_utc, datetime) else None
    same_day_candidates = sum(1 for c in (candidates or []) if isinstance(c, dict) and c.get("days_ahead") == 0)
    same_day_edges = sum(1 for t in (trades or []) if isinstance(t, dict) and t.get("days_ahead") == 0)
    same_day_selected = sum(1 for t in (selected or []) if isinstance(t, dict) and t.get("days_ahead") == 0)
    same_day_buys = sum(1 for b in (buys or []) if isinstance(b, dict) and b.get("days_ahead") == 0)
    reject_reasons = {}
    same_day_reject_reasons = {}
    execution_reject_reasons = {}
    for entry in (skip_log_entries or []):
        if not isinstance(entry, dict):
            continue
        reason = str(entry.get("skip_reason", "") or "").strip()
        _bump_reason_counter(reject_reasons, reason)
        if entry.get("days_ahead") == 0:
            _bump_reason_counter(same_day_reject_reasons, reason)
    for failure in (execution_failures or []):
        if not isinstance(failure, dict):
            continue
        reason = str(failure.get("reason", "") or "").strip()
        _bump_reason_counter(reject_reasons, reason)
        _bump_reason_counter(execution_reject_reasons, reason)
        if failure.get("days_ahead") == 0:
            _bump_reason_counter(same_day_reject_reasons, reason)
    selected_n = len(selected or [])
    buys_n = len(buys or [])
    return {
        "slot_hour_utc": slot_hour,
        "same_day_candidates": same_day_candidates,
        "same_day_edges": same_day_edges,
        "same_day_selected": same_day_selected,
        "same_day_buys": same_day_buys,
        "edges": len(trades or []),
        "selected": selected_n,
        "buys": buys_n,
        "buy_rate": round(buys_n / selected_n, 4) if selected_n > 0 else 0.0,
        "same_day_buy_rate": round(same_day_buys / same_day_selected, 4) if same_day_selected > 0 else 0.0,
        "reject_reasons": reject_reasons,
        "same_day_reject_reasons": same_day_reject_reasons,
        "execution_reject_reasons": execution_reject_reasons,
    }


def _extract_slot_metrics_record(rec):
    if not isinstance(rec, dict):
        return None
    scan = rec.get("scan")
    if not isinstance(scan, dict):
        return None
    slot_metrics = scan.get("slot_metrics")
    if not isinstance(slot_metrics, dict):
        return None
    ts_raw = rec.get("timestamp_utc", "")
    try:
        ts = datetime.fromisoformat(ts_raw)
    except Exception:
        return None
    item = dict(slot_metrics)
    item["_ts"] = ts
    item["_ts_raw"] = ts_raw
    return item


def _merge_reason_counts(records, key):
    merged = {}
    for rec in records:
        counts = rec.get(key) if isinstance(rec, dict) else None
        if not isinstance(counts, dict):
            continue
        for reason, count in counts.items():
            try:
                merged[reason] = int(merged.get(reason, 0) or 0) + int(count or 0)
            except Exception:
                continue
    return merged


def _top_reason(reason_counts):
    if not isinstance(reason_counts, dict) or not reason_counts:
        return None
    return max(reason_counts.items(), key=lambda kv: kv[1])[0]


def _format_reason_summary(reason_counts, max_items=3):
    if not isinstance(reason_counts, dict) or not reason_counts:
        return "sin rechazos relevantes"
    ordered = sorted(reason_counts.items(), key=lambda kv: (-int(kv[1] or 0), kv[0]))
    parts = [f"{reason}={count}" for reason, count in ordered[:max_items]]
    return ", ".join(parts)


def evaluate_slot_monetization(records, target_hour, min_cycles=3):
    slot_records = []
    for rec in records or []:
        item = _extract_slot_metrics_record(rec)
        if not item:
            continue
        if item.get("slot_hour_utc") != target_hour:
            continue
        slot_records.append(item)
    slot_records = sorted(slot_records, key=lambda x: x["_ts"])
    if len(slot_records) > 5:
        slot_records = slot_records[-5:]
    partial_totals = {
        "same_day_candidates": sum(int(r.get("same_day_candidates", 0) or 0) for r in slot_records),
        "same_day_edges": sum(int(r.get("same_day_edges", 0) or 0) for r in slot_records),
        "same_day_selected": sum(int(r.get("same_day_selected", 0) or 0) for r in slot_records),
        "same_day_buys": sum(int(r.get("same_day_buys", 0) or 0) for r in slot_records),
        "edges": sum(int(r.get("edges", 0) or 0) for r in slot_records),
        "selected": sum(int(r.get("selected", 0) or 0) for r in slot_records),
        "buys": sum(int(r.get("buys", 0) or 0) for r in slot_records),
    }
    partial_execution_reasons = _merge_reason_counts(slot_records, "execution_reject_reasons")
    partial_same_day_reasons = _merge_reason_counts(slot_records, "same_day_reject_reasons")
    if len(slot_records) < min_cycles:
        summary = "muestra insuficiente"
        if target_hour == 4:
            if partial_totals["same_day_buys"] > 0:
                summary = "muestra insuficiente; ya hubo buy same-day"
            elif partial_totals["same_day_selected"] > 0:
                summary = "muestra insuficiente; ya hubo selección same-day"
            elif partial_totals["same_day_edges"] > 0:
                summary = "muestra insuficiente; ya hubo edge same-day"
        return {
            "slot_hour_utc": target_hour,
            "cycles": len(slot_records),
            "decision": "insufficient_data",
            "status": "observe",
            "summary": summary,
            "buy_rate": round(partial_totals["buys"] / partial_totals["selected"], 4) if partial_totals["selected"] > 0 else 0.0,
            "same_day_buy_rate": round(partial_totals["same_day_buys"] / partial_totals["same_day_selected"], 4) if partial_totals["same_day_selected"] > 0 else 0.0,
            "execution_reject_reasons": partial_execution_reasons,
            "same_day_reject_reasons": partial_same_day_reasons,
            "range": {
                "from": slot_records[0]["_ts_raw"] if slot_records else None,
                "to": slot_records[-1]["_ts_raw"] if slot_records else None,
            },
            **partial_totals,
        }

    totals = {
        "same_day_candidates": sum(int(r.get("same_day_candidates", 0) or 0) for r in slot_records),
        "same_day_edges": sum(int(r.get("same_day_edges", 0) or 0) for r in slot_records),
        "same_day_selected": sum(int(r.get("same_day_selected", 0) or 0) for r in slot_records),
        "same_day_buys": sum(int(r.get("same_day_buys", 0) or 0) for r in slot_records),
        "edges": sum(int(r.get("edges", 0) or 0) for r in slot_records),
        "selected": sum(int(r.get("selected", 0) or 0) for r in slot_records),
        "buys": sum(int(r.get("buys", 0) or 0) for r in slot_records),
    }
    execution_reasons = _merge_reason_counts(slot_records, "execution_reject_reasons")
    same_day_reasons = _merge_reason_counts(slot_records, "same_day_reject_reasons")
    buy_rate = round(totals["buys"] / totals["selected"], 4) if totals["selected"] > 0 else 0.0
    same_day_buy_rate = round(totals["same_day_buys"] / totals["same_day_selected"], 4) if totals["same_day_selected"] > 0 else 0.0

    if target_hour == 4:
        if totals["same_day_buys"] > 0:
            decision = "validated"
            status = "keep"
            summary = "04h ya monetiza"
        elif totals["same_day_selected"] > 0:
            dominant = _top_reason(execution_reasons) or _top_reason(same_day_reasons) or "unknown"
            decision = "not_validated_yet"
            status = "keep"
            summary = f"04h produce selección same-day pero no convierte; cuello dominante={dominant}"
        elif totals["same_day_edges"] > 0:
            dominant = _top_reason(same_day_reasons) or "unknown"
            decision = "observe_post_edge"
            status = "keep"
            summary = f"04h produce edge same-day pero no selección; freno dominante={dominant}"
        else:
            dominant = _top_reason(same_day_reasons) or "no_same_day_signal"
            decision = "weak_signal"
            status = "observe"
            summary = f"04h aún no valida monetización; señal same-day débil ({dominant})"
    elif target_hour == 23:
        if totals["edges"] == 0 and totals["buys"] == 0:
            decision = "disable_candidate"
            status = "feature_flag"
            summary = "23h no aporta edge ni buys; candidato a desactivar"
        elif buy_rate == 0.0 and totals["same_day_edges"] == 0:
            decision = "low_value"
            status = "feature_flag"
            summary = "23h mantiene valor monetizable débil"
        else:
            decision = "keep"
            status = "observe"
            summary = "23h aún muestra alguna señal; no desactivar automáticamente"
    else:
        decision = "observe"
        status = "observe"
        summary = "slot no clasificado"

    return {
        "slot_hour_utc": target_hour,
        "cycles": len(slot_records),
        "decision": decision,
        "status": status,
        "summary": summary,
        "buy_rate": buy_rate,
        "same_day_buy_rate": same_day_buy_rate,
        "execution_reject_reasons": execution_reasons,
        "same_day_reject_reasons": same_day_reasons,
        "range": {
            "from": slot_records[0]["_ts_raw"],
            "to": slot_records[-1]["_ts_raw"],
        },
        **totals,
    }


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
    dl.append(f"BANKROLL: ${effective_bankroll:.2f} (tope ${BANKROLL:.2f}) | MIN_EDGE={MIN_EDGE}%")
    dl.append(f"{'='*50}")

    # R3: skip_log por ciclo — cycle_id determinista + bucket local para batch append al final
    cycle_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    skip_log_entries = []

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

    # ---- PASO 0.6: AUDITORA (v10.1 final) ----
    # Verificar si ventas anteriores se llenaron
    try:
        audit_check_sell_fills(client, dl)
    except Exception as e:
        log.warning(f"Error audit fills: {e}")

    # Comparar forecast original vs forecast posterior Open-Meteo (no WU).
    try:
        audit_check_open_meteo_forecast_drift(dl)
    except Exception as e:
        log.warning(f"Error audit forecast drift Open-Meteo: {e}")

    # Observed proxy audit: NOAA NCEI para las 4 ciudades activas.
    try:
        audit_check_resolution_truth(dl)
    except Exception as e:
        log.warning(f"Error audit observed proxy NOAA: {e}")

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

    discovered_markets_unique = count_discovered_markets_unique(all_markets)
    dl.append(f"\nMERCADOS: {len(all_markets)} encontrados")
    record_trade_lifecycle_market_observations(all_markets, source="cycle_market_scan")

    # ---- PASO 2: Parseo + filtro ----
    # v10.3: min_days es ahora PER-CITY (Bug #5 fix — zona horaria asiática)
    min_days_global = get_min_days_ahead()  # Solo para logging
    dl.append(f"MIN_DAYS_AHEAD base: {min_days_global} (hora UTC: {datetime.now(timezone.utc).hour:02d})")
    dl.append(f"  ↳ Ajuste por zona horaria activo: ciudades asiáticas pueden requerir min_days=1 incluso a las 08:00 UTC")
    policy_state = load_city_policy_state()
    city_windows = compute_city_windows()

    candidates = []
    parse_fail = 0
    date_fail = 0
    timezone_skip = 0  # v10.3: contador de filtrados por zona horaria
    blocked_city_skip = 0
    blocked_seen = set()
    allowlist_city_skip = 0
    allowlist_seen = set()
    price_fail = 0
    liq_fail = 0
    city_window_skipped = 0
    city_window_cities = set()

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)
        if not parsed or not parsed["date_str"]:
            parse_fail += 1
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                question=question,
                extras={"stage": "no_parsed_or_date_str"},
            ))
            continue

        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            parse_fail += 1
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                city=parsed.get("city"), question=question,
                extras={"stage": "date_text_to_iso", "date_str": parsed.get("date_str")},
            ))
            continue

        try:
            days_ahead = (date.fromisoformat(date_iso) - date.today()).days
        except ValueError:
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                city=parsed.get("city"), date_iso=date_iso, question=question,
                extras={"stage": "date_fromisoformat"},
            ))
            continue

        # v10.3: min_days PER-CITY según zona horaria (Bug #5 fix)
        city = parsed["city"]
        city_mode = get_effective_city_mode(city, policy_state=policy_state)
        if should_skip_observation(city):
            blocked_city_skip += 1
            blocked_seen.add(city)
            skip_log_entries.append(_make_skip_entry(
                "blocked_city", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=False, question=question,
            ))
            continue
        allowlisted = city_mode in {"active", "canary"}
        shadow_override = False
        if allowlisted and _is_shadow_only():
            # Shadow-only global: canary/active se observan pero NO ejecutan BUY real.
            # Se preserva auto_canary_cities (autopromoción sigue viva) para mantener la señal
            # de Phase 1 — solo se corta la ejecución.
            allowlisted = False
            shadow_override = True
        if not allowlisted:
            allowlist_city_skip += 1
            if city not in allowlist_seen:
                if shadow_override:
                    dl.append(f"SHADOW {city}: shadow-only override (era {city_mode}, se observa sin comprar)")
                else:
                    dl.append(f"SHADOW {city}: fuera de ACTIVE_TRADING_CITIES (se observa, no se compra)")
                allowlist_seen.add(city)
        # NOTA R3: ni fuera_allowlist ni shadow_only_override generan skip_log entry aquí.
        # El candidato continúa procesándose con allowlisted=False y llega a Loop B,
        # donde se loguea con datos ricos (edge_pct, our_prob, forecast_max).
        city_window_min_days = city_windows.get(city)
        if days_ahead == 0 and city_window_min_days is not None and city_window_min_days > 0:
            city_window_skipped += 1
            city_window_cities.add(city)
            continue

        min_days = get_min_days_for_city(city)

        if days_ahead < min_days:
            # Distinguir si fue por zona horaria o por filtro global
            if min_days > min_days_global:
                timezone_skip += 1
                skip_log_entries.append(_make_skip_entry(
                    "timezone_filter", cycle_id=cycle_id,
                    city=city, date_iso=date_iso, days_ahead=days_ahead,
                    city_mode=city_mode, allowlisted=allowlisted, question=question,
                    extras={"min_days_city": min_days, "min_days_global": min_days_global},
                ))
            else:
                date_fail += 1
                skip_log_entries.append(_make_skip_entry(
                    "date_out_of_range_past", cycle_id=cycle_id,
                    city=city, date_iso=date_iso, days_ahead=days_ahead,
                    city_mode=city_mode, allowlisted=allowlisted, question=question,
                    extras={"min_days": min_days},
                ))
            continue

        if days_ahead > MAX_DAYS_AHEAD:
            date_fail += 1
            skip_log_entries.append(_make_skip_entry(
                "date_out_of_range_future", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=allowlisted, question=question,
                extras={"max_days_ahead": MAX_DAYS_AHEAD},
            ))
            continue

        prices_raw = market.get("outcomePrices", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        except (json.JSONDecodeError, TypeError):
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=allowlisted, question=question,
                extras={"stage": "prices_decode"},
            ))
            continue
        if not prices:
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=allowlisted, question=question,
                extras={"stage": "prices_empty"},
            ))
            continue

        clob_ids_raw = market.get("clobTokenIds", "[]")
        try:
            clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        except (json.JSONDecodeError, TypeError):
            clob_ids = []
        if not clob_ids or len(clob_ids) < 2:
            skip_log_entries.append(_make_skip_entry(
                "parse_fail", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=allowlisted, question=question,
                extras={"stage": "clob_ids_insufficient", "count": len(clob_ids) if clob_ids else 0},
            ))
            continue

        mkt_prob_yes = float(prices[0])
        if mkt_prob_yes < MIN_PRICE or mkt_prob_yes > MAX_PRICE:
            mkt_prob_no = 1.0 - mkt_prob_yes
            if mkt_prob_no < MIN_PRICE or mkt_prob_no > MAX_PRICE:
                price_fail += 1
                skip_log_entries.append(_make_skip_entry(
                    "price_out_of_range", cycle_id=cycle_id,
                    city=city, date_iso=date_iso, days_ahead=days_ahead,
                    city_mode=city_mode, allowlisted=allowlisted, question=question,
                    mkt_prob=round(mkt_prob_yes * 100, 2),
                    extras={"min_price": MIN_PRICE, "max_price": MAX_PRICE},
                ))
                continue

        liquidity = float(market.get("liquidity", 0))
        if liquidity < MIN_LIQUIDITY:
            liq_fail += 1
            skip_log_entries.append(_make_skip_entry(
                "liquidity_low", cycle_id=cycle_id,
                city=city, date_iso=date_iso, days_ahead=days_ahead,
                city_mode=city_mode, allowlisted=allowlisted, question=question,
                extras={"liquidity": liquidity, "min_liquidity": MIN_LIQUIDITY},
            ))
            continue

        parsed.update({
            "question": question, "date_iso": date_iso, "days_ahead": days_ahead,
            "mkt_prob_yes": mkt_prob_yes, "mkt_prob_no": 1.0 - mkt_prob_yes,
            "volume_24h": float(market.get("volume24hr", 0)), "liquidity": liquidity,
            "token_id_yes": clob_ids[0], "token_id_no": clob_ids[1],
            "market_id": market.get("id") or None,
            "condition_id": market.get("conditionId") or None,
            "allowlisted": allowlisted,
            "city_mode": city_mode,
            "shadow_override_flag": shadow_override,  # R3: distingue fuera_allowlist vs shadow_only_override en Loop B
        })
        candidates.append(parsed)

    dl.append(f"FILTROS: {len(candidates)} pasan | {parse_fail} no parseables | {date_fail} fuera de fecha | {timezone_skip} bloqueados por zona horaria | {blocked_city_skip} bloqueados por ciudad | {allowlist_city_skip} fuera de ACTIVE_TRADING_CITIES | {price_fail} fuera de precio | {liq_fail} sin liquidez")
    if city_window_skipped:
        dl.append(f"VENTANA: {city_window_skipped} mercados same-day fuera de ventana ({', '.join(sorted(city_window_cities))})")
    if blocked_seen:
        dl.append(f"  🚫 Ciudades bloqueadas operativamente: {', '.join(sorted(blocked_seen))} (sin proxy observado util)")
    if allowlist_seen:
        dl.append(f"  ✅ Allowlist activa: {', '.join(sorted(ACTIVE_TRADING_CITIES))}")

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
    shadow_trades = []
    condition_filtered_shadow = []
    condition_filtered_skip = 0
    condition_filtered_seen = set()
    observed_cycle_markets = []
    observed_cycle_market_keys = set()
    skipped_dup = 0
    edge_analysis = []  # Para el log detallado
    exact_no_qt_eval_batch = []  # LOG_ONLY batch for exact/no-QT-match evals (v10.6.43)
    # v10.4 Fix Bug #9: token_ids vendidos en manage_positions → no re-comprar
    sold_this_cycle = mgmt.get("sold_token_ids", set())

    for c in candidates:
        city = c["city"]
        if city not in forecast_cache or c["date_iso"] not in forecast_cache[city]:
            skip_log_entries.append(_make_skip_entry(
                "forecast_missing", cycle_id=cycle_id,
                city=city, date_iso=c.get("date_iso"), days_ahead=c.get("days_ahead"),
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                question=c.get("question"),
                extras={"forecast_cached": city in forecast_cache},
            ))
            continue

        forecast_max = forecast_cache[city][c["date_iso"]]["temp_max"]
        if city in OBSERVED_AUDIT_CITIES:
            observed_key = f"{city}|{c['date_iso']}"
            if observed_key not in observed_cycle_market_keys:
                observed_cycle_markets.append({
                    "city": city,
                    "date": c["date_iso"],
                    "forecast_max": round(float(forecast_max), 1),
                    "question": c.get("question", ""),
                    "seen_at": datetime.now(timezone.utc).isoformat(),
                })
                observed_cycle_market_keys.add(observed_key)
        threshold = c["temp_threshold"]
        threshold_c = (threshold - 32) * 5 / 9 if c["unit"] == "F" else float(threshold)

        # v9: Soporte para rangos ("between 62-63°F")
        threshold_high = c.get("temp_threshold_high")
        threshold_high_c = None
        if threshold_high is not None:
            threshold_high_c = (threshold_high - 32) * 5 / 9 if c["unit"] == "F" else float(threshold_high)
        c["eval_key"] = _build_bot_eval_key(
            city,
            c["date_iso"],
            c["condition"],
            threshold,
            threshold_high,
            c["unit"],
        )

        # Label para logs (muestra rango si aplica)
        temp_label = f"{threshold}-{threshold_high}°{c['unit']}" if threshold_high else f"{threshold}°{c['unit']}"

        # R3: sigma efectivo para esta ciudad+días (para skip_log enrichment)
        try:
            sigma_used_val = get_uncertainty(c["days_ahead"], city=city)
        except Exception:
            sigma_used_val = None

        condition_name = str(c.get("condition", "") or "").strip().lower()
        if condition_name not in ALLOWED_CONDITIONS:
            # v10.6.15: Quality-trader-gated canary para exact/range
            # Si la condición está en QUALITY_TRADER_CONDITIONS, ciudad en whitelist,
            # y hay al menos un quality trader con señal → pasa al pipeline con flag canary.
            _qt_canary = False
            _early_key = c.get("eval_key")
            _qt_gate_reason = "condition_not_in_quality_trader_gate"
            if condition_name in QUALITY_TRADER_CONDITIONS:
                _qt_gate_reason = "city_not_in_quality_trader_whitelist"
                if city in QUALITY_TRADER_CITIES_WHITELIST:
                    if trader_signals.get(_early_key):
                        _qt_canary = True
                        _qt_gate_reason = "quality_trader_signal_match"
                    else:
                        _qt_gate_reason = "no_quality_trader_signal_match"

            if not _qt_canary:
                _filter_label = "CANARY-FILTER" if c.get("city_mode") in {"active", "canary"} else "SHADOW-FILTER"
                condition_filtered_skip += 1
                condition_filtered_shadow.append({
                    "question": c["question"],
                    "city": city,
                    "date": c["date_iso"],
                    "side": "FILTERED",
                    "edge_pct": 0.0,
                    "expected_value": 0.0,
                    "mkt_price": round(max(c["mkt_prob_yes"], c["mkt_prob_no"]) * 100, 1),
                    "our_prob": 0.0,
                    "forecast_max": forecast_max,
                    "condition": condition_name,
                })
                if condition_name not in condition_filtered_seen:
                    dl.append(
                        f"SKIP condicion '{condition_name}': fuera de ALLOWED_CONDITIONS "
                        f"(se mueve a shadow tracking, no se compra)"
                    )
                    condition_filtered_seen.add(condition_name)
                edge_analysis.append(
                    f"  {_filter_label} {city} {temp_label} {c['date_iso']} | "
                    f"condicion={condition_name} fuera de ALLOWED_CONDITIONS | motivo={_qt_gate_reason}"
                )
                skip_log_entries.append(_make_skip_entry(
                    "condition_filtered", cycle_id=cycle_id,
                    city=city, date_iso=c["date_iso"], days_ahead=c["days_ahead"],
                    city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                    forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                    unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                    question=c["question"],
                    extras={
                        "allowed_conditions": sorted(ALLOWED_CONDITIONS),
                        "filter_label": _filter_label,
                        "exact_range_gate_reason": _qt_gate_reason,
                        "qt_match_key": _early_key,
                    },
                ))
                # v10.6.43: LOG_ONLY capture for exact/no-QT-match (env var OFF by default)
                if (
                    os.getenv("LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED", "0") == "1"
                    and _qt_gate_reason == "no_quality_trader_signal_match"
                    and c.get("city_mode") in {"active", "canary"}
                ):
                    try:
                        _lonly_prob_yes = estimate_prob_with_city(
                            forecast_max, threshold_c, c["condition"],
                            c["days_ahead"], threshold_high_c, city=city,
                        )
                        _lonly_prob_no = 1.0 - _lonly_prob_yes
                        _lonly_edge_yes = _lonly_prob_yes - c["mkt_prob_yes"]
                        _lonly_edge_no = _lonly_prob_no - c["mkt_prob_no"]
                        if _lonly_edge_yes > 0 and _lonly_edge_yes >= _lonly_edge_no:
                            _lonly_best_side = "YES"
                            _lonly_best_edge = round(_lonly_edge_yes * 100, 4)
                        elif _lonly_edge_no > 0:
                            _lonly_best_side = "NO"
                            _lonly_best_edge = round(_lonly_edge_no * 100, 4)
                        else:
                            _lonly_best_side = None
                            _lonly_best_edge = None
                        _lonly_passes = (
                            _lonly_best_edge is not None and _lonly_best_edge >= MIN_EDGE
                        )
                        _lonly_mid = c.get("market_id")
                        _lonly_cid = c.get("condition_id")
                        _lonly_tyes = c.get("token_id_yes")
                        _lonly_tno = c.get("token_id_no")
                        exact_no_qt_eval_batch.append({
                            "schema_version": 1,
                            "ts_utc": datetime.now(timezone.utc).isoformat(),
                            "cycle_id": cycle_id,
                            "eval_key": c.get("eval_key") or _early_key,
                            "capture_id": str(uuid.uuid4()),
                            "market_id": _lonly_mid,
                            "condition_id": _lonly_cid,
                            "token_id_yes": _lonly_tyes,
                            "token_id_no": _lonly_tno,
                            "identity_resolvable": bool(
                                _lonly_mid or _lonly_cid or _lonly_tyes or _lonly_tno
                            ),
                            "city": city,
                            "city_mode": c.get("city_mode"),
                            "date_iso": c["date_iso"],
                            "days_ahead": c["days_ahead"],
                            "condition": condition_name,
                            "threshold": threshold,
                            "threshold_high": threshold_high,
                            "unit": c["unit"],
                            "qt_gate_reason": _qt_gate_reason,
                            "our_prob_yes": round(_lonly_prob_yes, 6),
                            "our_prob_no": round(_lonly_prob_no, 6),
                            "mkt_prob_yes": round(c["mkt_prob_yes"], 6),
                            "mkt_prob_no": round(c["mkt_prob_no"], 6),
                            "edge_yes_pct": round(_lonly_edge_yes * 100, 4),
                            "edge_no_pct": round(_lonly_edge_no * 100, 4),
                            "best_side_log_only": _lonly_best_side,
                            "best_edge_pct_log_only": _lonly_best_edge,
                            "min_edge_reference": MIN_EDGE,
                            "edge_passes_reference_threshold_log_only": bool(_lonly_passes),
                            "forecast_max": forecast_max,
                            "sigma_used": sigma_used_val,
                            "source_fidelity_status": "unknown",
                            "log_only": True,
                            "execution_authorized": False,
                            "skip_log_eval_key": c.get("eval_key") or _early_key,
                            "capture_meta": None,  # filled by write_exact_no_qt_match_evals
                        })
                    except Exception as _lonly_err:
                        log.warning(
                            f"exact_no_qt_match_eval capture error (fail-open): {_lonly_err}"
                        )
                continue
            # Quality-trader canary: marcar para edge buffer + size scale aguas abajo
            c["exact_range_canary"] = True

        our_prob_yes = estimate_prob_with_city(
            forecast_max,
            threshold_c,
            c["condition"],
            c["days_ahead"],
            threshold_high_c,
            city=city,
        )
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
            skip_log_entries.append(_make_skip_entry(
                "no_edge", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                our_prob=round(our_prob_yes * 100, 2),
                mkt_prob=round(c["mkt_prob_yes"] * 100, 2),
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"edge_yes_pct": round(edge_yes * 100, 2), "edge_no_pct": round(edge_no * 100, 2)},
            ))
            continue

        edge_pct = edge * 100

        # v10.6.15: edge mínimo diferenciado para exact/range canary
        _effective_min_edge = MIN_EDGE + MIN_EDGE_EXACT_RANGE_BUFFER_PP if c.get("exact_range_canary") else MIN_EDGE
        # v10.6.24: buffer adicional en posiciones baratas (<LOW_PRICE_THRESHOLD)
        if mkt_price < LOW_PRICE_THRESHOLD:
            _effective_min_edge += MIN_EDGE_LOW_PRICE_BUFFER_PP
        # v10.6.31: gate — exact + precio bajo → gap risk catastrófico (binary events a 0)
        if BLOCK_LOW_EXACT_ENTRIES and condition_name == "exact" and mkt_price < LOW_PRICE_THRESHOLD:
            edge_analysis.append(
                f"  ⊘ {city} {side} {temp_label} {c['date_iso']} | "
                f"mkt={mkt_price*100:.0f}¢ exact+LOW → gap_risk bloqueado"
            )
            skip_log_entries.append(_make_skip_entry(
                "low_exact_gap_risk", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=_effective_min_edge,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"skip_reason_detail": "low_exact_gap_risk"},
            ))
            continue
        # v10.6.18: exact/range canary YES-side requiere our_prob >= 65% exact / 72% range
        # (autopsia C1: YES range WR=9% vs exact WR=29% → range necesita floor más exigente)
        _yes_floor = 0.72 if condition_name == "range" else 0.65
        if c.get("exact_range_canary") and side == "YES" and our_prob < _yes_floor:
            edge_analysis.append(f"  \u29b5 {city} {side} {temp_label} {c['date_iso']} | our_prob={our_prob*100:.1f}% < {_yes_floor*100:.0f}% (exact/range YES low-conf skip)")
            skip_log_entries.append(_make_skip_entry(
                "below_min_edge", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=_effective_min_edge,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"skip_reason_detail": "exact_range_yes_low_confidence"},
            ))
            continue
        if edge_pct < _effective_min_edge:
            edge_analysis.append(f"  ✗ {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% → BAJO (min {_effective_min_edge}%)")
            skip_log_entries.append(_make_skip_entry(
                "below_min_edge", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=_effective_min_edge,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
            ))
            continue

        position = calculate_position(effective_bankroll, our_prob, mkt_price)
        if not position:
            edge_analysis.append(f"  ✗ {city} {side} | edge={edge_pct:.1f}% → KELLY MUY BAJO (no alcanza $1 mín)")
            skip_log_entries.append(_make_skip_entry(
                "kelly_too_low", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"min_bet": MIN_BET, "effective_bankroll": round(effective_bankroll, 2)},
            ))
            continue
        position = _scaled_position(position, our_prob, c.get("city_mode"))
        # v10.6.15: sizing adicional para exact/range canary (25% del normal: canary×exact_range)
        if c.get("exact_range_canary") and isinstance(position, dict) and position.get("amount"):
            _er_amount = max(MIN_BET, round(float(position["amount"]) * EXACT_RANGE_SIZE_SCALE, 2))
            _er_price = float(position.get("aggressive_price", position.get("market_price", 0)) or 0)
            if _er_price > 0:
                _er_shares = round(_er_amount / _er_price, 2)
                _er_profit = round(_er_shares * (1.0 - _er_price), 2)
                _er_ev = round(our_prob * _er_profit - (1 - our_prob) * _er_amount, 2)
                position = dict(position)
                position.update({
                    "amount": _er_amount,
                    "shares": _er_shares,
                    "profit_if_win": _er_profit,
                    "loss_if_lose": _er_amount,
                    "expected_value": _er_ev,
                    "fraction_pct": round(float(position.get("fraction_pct", 0) or 0) * EXACT_RANGE_SIZE_SCALE, 2),
                })
        # v10.6.23: evitar exact/range canary demasiado pequenos para una salida util.
        if c.get("exact_range_canary") and isinstance(position, dict) and position.get("amount"):
            _er_cap = round(max(MIN_BET, effective_bankroll * MAX_BET_PCT), 2)
            _er_floor = round(max(MIN_BET, min(EXACT_RANGE_MIN_AMOUNT, _er_cap)), 2)
            if float(position.get("amount", 0) or 0) < _er_floor:
                position = _resize_position_amount(position, _er_floor, our_prob)
                position["min_amount_floor_applied"] = _er_floor

        if not c.get("allowlisted", True):
            shadow_trades.append({
                "question": c["question"], "city": city, "date": c["date_iso"],
                "days_ahead": c["days_ahead"], "forecast_max": forecast_max,
                "threshold": threshold, "threshold_high": threshold_high,
                "unit": c["unit"], "condition": c["condition"],
                "side": side, "our_prob": round(our_prob * 100, 1),
                "mkt_price": round(mkt_price * 100, 1), "edge_pct": round(edge_pct, 1),
                "position": position, "volume_24h": c["volume_24h"],
                "liquidity": c["liquidity"], "token_id": token_id,
            })
            edge_analysis.append(f"  SHADOW {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% | ${position['amount']:.2f} virtual")
            # R3: distinguir fuera_allowlist puro vs shadow_only_override (ambos con datos ricos)
            _skip_reason_allow = "shadow_only_override" if c.get("shadow_override_flag") else "fuera_allowlist"
            skip_log_entries.append(_make_skip_entry(
                _skip_reason_allow, cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=False,
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"virtual_amount": position.get("amount"), "virtual_ev": position.get("expected_value")},
            ))
            continue

        if token_id in open_token_ids:
            skipped_dup += 1
            edge_analysis.append(f"   {city} {side} | edge={edge_pct:.1f}% → YA HAY ORDEN")
            skip_log_entries.append(_make_skip_entry(
                "existing_order", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"token_id": token_id},
            ))
            continue

        # v10.4 Fix Bug #9: no re-comprar lo que vendimos este ciclo
        if token_id in sold_this_cycle:
            skipped_dup += 1
            edge_analysis.append(f"   {city} {side} | edge={edge_pct:.1f}% → VENDIDO ESTE CICLO (no re-entrada)")
            skip_log_entries.append(_make_skip_entry(
                "sold_this_cycle", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"token_id": token_id},
            ))
            continue

        # v10.6.17: no re-comprar ciudad en cooldown post-SL
        if _sl_cooldown_check(city):
            skipped_dup += 1
            edge_analysis.append(f"   {city} {side} | edge={edge_pct:.1f}% → SL COOLDOWN activo ({SL_CITY_COOLDOWN_HOURS}h)")
            skip_log_entries.append(_make_skip_entry(
                "sl_city_cooldown", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"cooldown_hours": SL_CITY_COOLDOWN_HOURS},
            ))
            continue

        # v10.4 Fix Bug #3: no comprar si ya tenemos posición abierta
        if token_id in existing_position_tokens:
            skipped_dup += 1
            edge_analysis.append(f"   {city} {side} | edge={edge_pct:.1f}% → YA HAY POSICIÓN ABIERTA")
            skip_log_entries.append(_make_skip_entry(
                "existing_position", cycle_id=cycle_id,
                city=city, date_iso=c["date_iso"], side=side, days_ahead=c["days_ahead"],
                city_mode=c.get("city_mode"), allowlisted=c.get("allowlisted"),
                edge_pct=round(edge_pct, 2),
                our_prob=round(our_prob * 100, 2), mkt_prob=round(mkt_price * 100, 2),
                min_edge=MIN_EDGE,
                forecast_max=forecast_max, threshold=threshold, threshold_high=threshold_high,
                unit=c["unit"], condition=condition_name, sigma_used=sigma_used_val,
                question=c["question"],
                extras={"token_id": token_id},
            ))
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
            trader_confirm = f"  CONFIRMADO por: {', '.join(names)}"

        edge_analysis.append(f"  ✓ {city} {side} {temp_label} {c['date_iso']} | forecast={forecast_max:.1f}°C | nuestro={our_prob*100:.1f}% mercado={mkt_price*100:.1f}% | edge={edge_pct:.1f}% | ${position['amount']:.2f} EV=${position['expected_value']:+.2f}{trader_confirm}")

        resolution_meta = RESOLUTION_ICAO.get(city, {})
        trades.append({
            "question": c["question"], "city": city, "date": c["date_iso"],
            "days_ahead": c["days_ahead"], "forecast_max": forecast_max,
            "threshold": threshold, "threshold_high": threshold_high,
            "unit": c["unit"], "condition": c["condition"],
            "city_mode": c.get("city_mode", "active"),
            "side": side, "our_prob": round(our_prob * 100, 1),
            "mkt_price": round(mkt_price * 100, 1), "edge_pct": round(edge_pct, 1),
            "position": position, "volume_24h": c["volume_24h"],
            "liquidity": c["liquidity"],
            "station": RESOLUTION_STATIONS.get(city, {}).get("name", "?"),
            "resolution_icao": resolution_meta.get("icao", "?"),
            "resolution_wu_url": resolution_meta.get("wu_url", ""),
            "token_id": token_id,
            "eval_key": c.get("eval_key"),
            "trader_confirmed": [s["trader"] for s in matching_traders],  # v9
        })

    trades.sort(key=lambda x: x["position"]["expected_value"], reverse=True)
    bot_state["last_opportunities"] = len(trades)

    # v9: Guardar análisis completo para /logfull
    bot_state["last_edge_analysis"] = edge_analysis
    bot_state["last_trader_signals"] = trader_signals

    dl.append(f"\nANLISIS DE EDGE ({len(candidates)} mercados evaluados):")
    dl.extend(edge_analysis)
    if skipped_dup:
        dl.append(f"\n  {skipped_dup} saltados (orden ya abierta)")
    dl.append(f"\nRESULTADO: {len(trades)} oportunidades operables con edge")
    if shadow_trades:
        dl.append(f"SHADOW: {len(shadow_trades)} oportunidades fuera de allowlist registradas para aprendizaje")
    if condition_filtered_skip:
        allowed_display = ", ".join(sorted(ALLOWED_CONDITIONS)) if ALLOWED_CONDITIONS else "ninguna"
        dl.append(
            f"CONDICION FILTRADA: {condition_filtered_skip} mercados fuera de ALLOWED_CONDITIONS "
            f"({allowed_display}) enviados a shadow tracking"
        )

    for _skip_entry in list(skip_log_entries):
        _record_bot_evaluation_from_skip_entry(_skip_entry)

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
    execution_failures = []

    if not selected:
        dl.append(f"\nSin operaciones este ciclo.")
        bot_state["last_orders_placed"] = 0
        bot_state["last_trades"] = []
    else:
        results = []
        for i, trade in enumerate(selected):
            if not DRY_RUN:
                execution_price = round(trade["position"].get("aggressive_price", trade["mkt_price"] / 100.0), 2)
                original_size = round(trade["position"]["shares"], 2)
                normalized_size = _normalize_buy_order_size(execution_price, original_size)
                if normalized_size > original_size:
                    adjusted_position = dict(trade.get("position", {}))
                    adjusted_position["shares"] = normalized_size
                    adjusted_position["amount"] = round(execution_price * normalized_size, 2)
                    adjusted_position["loss_if_lose"] = adjusted_position["amount"]
                    trade["position"] = adjusted_position
                    dl.append(
                        f"  AJUSTE BUY MIN NOTIONAL: {trade['city']} {trade['side']} "
                        f"{original_size:.2f}sh -> {normalized_size:.2f}sh @ ${execution_price:.2f}"
                    )

            price_at_guard = round(trade["position"].get("aggressive_price", trade["mkt_price"] / 100.0), 2)
            amount_at_guard = round(float(trade.get("position", {}).get("amount", 0) or 0), 2)
            # price_raw is forensics only; trigger uses price_at_guard exclusively.
            price_raw = trade.get("position", {}).get("market_price")
            unsellable_guard = _unsellable_guard_decision(
                enabled=UNSELLABLE_GUARD_ENABLED,
                log_only=UNSELLABLE_GUARD_LOG_ONLY,
                condition=trade.get("condition"),
                days_ahead=trade.get("days_ahead"),
                price_at_guard=price_at_guard,
                amount=amount_at_guard,
                effective_bankroll=effective_bankroll,
            )
            if unsellable_guard.get("triggered"):
                guard_skip_reason = unsellable_guard["skip_reason"]
                skip_log_entries.append(_make_skip_entry(
                    guard_skip_reason, cycle_id=cycle_id,
                    city=trade.get("city"), date_iso=trade.get("date"), side=trade.get("side"),
                    days_ahead=trade.get("days_ahead"), city_mode=trade.get("city_mode"),
                    allowlisted=True, edge_pct=trade.get("edge_pct"),
                    our_prob=trade.get("our_prob"), mkt_prob=trade.get("mkt_price"),
                    min_edge=MIN_EDGE, forecast_max=trade.get("forecast_max"),
                    threshold=trade.get("threshold"), threshold_high=trade.get("threshold_high"),
                    unit=trade.get("unit"), condition=trade.get("condition"),
                    question=trade.get("question"),
                    extras={
                        "guard_version": UNSELLABLE_GUARD_VERSION,
                        "guard_action": unsellable_guard["guard_action"],
                        "trigger_reason": "micro_position_unsellable",
                        "match_zone_bucket": unsellable_guard["match_zone_bucket"],
                        "price_at_guard": price_at_guard,
                        "price_raw": price_raw,
                        "amount": amount_at_guard,
                        "effective_bankroll": effective_bankroll,
                        "size_ratio": round(unsellable_guard["size_ratio"], 6),
                        "edge_pct": trade.get("edge_pct"),
                        "city_mode": trade.get("city_mode"),
                        "label": trade.get("label"),
                        "question": trade.get("question"),
                        "side": trade.get("side"),
                        "counterfactual_resolved": None,
                    },
                ))
                dl.append(
                    f"  UNSELLABLE GUARD {unsellable_guard['guard_action']}: "
                    f"{trade.get('city')} {trade.get('side')} price=${price_at_guard:.2f} "
                    f"amount=${amount_at_guard:.2f} ratio={unsellable_guard['size_ratio']:.3f}"
                )
                # DORMANT until LOG_ONLY="0" — promotion requires Opus signoff
                if UNSELLABLE_GUARD_ENABLED and not UNSELLABLE_GUARD_LOG_ONLY:
                    record_bot_evaluation(
                        cycle_id,
                        trade.get("eval_key"),
                        False,
                        city=trade.get("city"),
                        date_iso=trade.get("date"),
                        condition=trade.get("condition"),
                        threshold=trade.get("threshold"),
                        threshold_high=trade.get("threshold_high"),
                        unit=trade.get("unit"),
                        edge_pct=trade.get("edge_pct"),
                        skip_or_block_reason=guard_skip_reason,
                        decision_gate=guard_skip_reason,
                        decision_confidence=trade.get("our_prob"),
                        our_prob=trade.get("our_prob"),
                        mkt_prob=trade.get("mkt_price"),
                        forecast_max=trade.get("forecast_max"),
                        days_ahead=trade.get("days_ahead"),
                    )
                    results.append({"ok": False, "msg": "unsellable_liquidity_guard"})
                    execution_failures.append({
                        "reason": guard_skip_reason,
                        "days_ahead": trade.get("days_ahead"),
                        "city": trade.get("city"),
                    })
                    continue

            # Guardar en known_tokens para que /ordenes lo encuentre
            known_tokens[trade["token_id"]] = {
                "question": trade["question"],
                "side": trade["side"],
            }

            record_bot_evaluation(
                cycle_id,
                trade.get("eval_key"),
                True,
                city=trade.get("city"),
                date_iso=trade.get("date"),
                condition=trade.get("condition"),
                threshold=trade.get("threshold"),
                threshold_high=trade.get("threshold_high"),
                unit=trade.get("unit"),
                edge_pct=trade.get("edge_pct"),
                skip_or_block_reason=None,
                decision_gate=None,
                decision_confidence=trade.get("our_prob"),
                our_prob=trade.get("our_prob"),
                mkt_prob=trade.get("mkt_price"),
                forecast_max=trade.get("forecast_max"),
                days_ahead=trade.get("days_ahead"),
            )
            result = execute_trade(client, trade, dry_run=DRY_RUN)

            # v10.6.23: retry once when Polymarket rejects due to share-count minimum.
            # The canary scale can reduce shares below per-market minimums (e.g. 2 < 5).
            # Hard cap: min_shares × price must stay within MAX_BET_PCT × bankroll.
            if not DRY_RUN and not result["ok"]:
                if _classify_execution_failure_reason(result.get("msg")) == "buy_min_size":
                    _min_sh = _parse_min_shares_from_error(result.get("msg"))
                    if _min_sh:
                        _req_notional = round(_min_sh * execution_price, 2)
                        _kelly_cap = round(effective_bankroll * MAX_BET_PCT, 2)
                        if _req_notional <= _kelly_cap:
                            _retry_pos = dict(trade["position"])
                            _retry_pos["shares"] = _min_sh
                            _retry_pos["amount"] = _req_notional
                            _retry_pos["loss_if_lose"] = _req_notional
                            trade["position"] = _retry_pos
                            dl.append(
                                f"  RETRY BUY MIN SHARES: {trade['city']} {trade['side']} "
                                f"{original_size:.2f}sh → {_min_sh:.0f}sh @ ${execution_price:.2f} = ${_req_notional:.2f}"
                            )
                            result = execute_trade(client, trade, dry_run=DRY_RUN)
                        else:
                            dl.append(
                                f"  SKIP RETRY MIN SHARES: {trade['city']} {trade['side']} "
                                f"min {_min_sh:.0f}sh = ${_req_notional:.2f} > Kelly cap ${_kelly_cap:.2f}"
                            )

            results.append(result)

            dl.append(f"\n  {'OK' if result['ok'] else 'FAIL'} #{i+1}: {trade['city']} {trade['side']} ${trade['position']['amount']:.2f} → {result['msg']}")

            if not DRY_RUN and result["ok"]:
                buy_summaries.append({
                    "city": trade["city"],
                    "days_ahead": trade.get("days_ahead"),
                    "side": trade["side"],
                    "amount": trade["position"]["amount"],
                    "edge": trade["edge_pct"],
                    "city_mode": trade.get("city_mode", ""),
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
                    cycle_number=bot_state["cycle_count"] + 1,
                    logic_cycle_number=bot_state.get("cycle_count_series", 0) + 1,
                )
            elif not result["ok"]:
                execution_failures.append({
                    "reason": _classify_execution_failure_reason(result.get("msg")),
                    "days_ahead": trade.get("days_ahead"),
                    "city": trade.get("city"),
                })

        ok = sum(1 for r in results if r["ok"])
        bot_state["last_orders_placed"] = ok
        bot_state["last_trades"] = selected

    shadow_payload = []
    shadow_seen_cities = set()
    shadow_timestamp = datetime.now(timezone.utc).isoformat()
    for trade in shadow_trades:
        shadow_payload.append({
            "city": trade["city"],
            "question": trade["question"],
            "date": trade["date"],
            "side": trade["side"],
            "edge_pct": trade["edge_pct"],
            "expected_value": trade["position"]["expected_value"],
            "mkt_price": trade["mkt_price"],
            "our_prob": trade["our_prob"],
            "forecast_max": trade["forecast_max"],
            "seen_at": shadow_timestamp,
            "edge_hit": True,
            "first_for_cycle": trade["city"] not in shadow_seen_cities,
        })
        shadow_seen_cities.add(trade["city"])
    for trade in condition_filtered_shadow:
        shadow_payload.append({
            "city": trade["city"],
            "question": trade["question"],
            "date": trade["date"],
            "side": trade["side"],
            "edge_pct": trade["edge_pct"],
            "expected_value": trade["expected_value"],
            "mkt_price": trade["mkt_price"],
            "our_prob": trade["our_prob"],
            "forecast_max": trade["forecast_max"],
            "seen_at": shadow_timestamp,
            "edge_hit": False,
            "first_for_cycle": trade["city"] not in shadow_seen_cities,
        })
        shadow_seen_cities.add(trade["city"])
    if shadow_payload:
        record_shadow_city_opportunities(
            shadow_payload,
            cycle_context={
                "cycle_number": bot_state["cycle_count"] + 1,
                "logic_cycle_number": bot_state.get("cycle_count_series", 0) + 1,
                "timestamp_utc": shadow_timestamp,
            },
        )

    # ---- R3: flush batch de skip_log entries al final del ciclo ----
    # El writer nunca lanza: errores se loggean y se descartan. Un log roto no frena trading.
    try:
        append_skip_log_entries(skip_log_entries)
    except Exception as _e_skip_log:
        log.warning(f"skip_log flush fallo: {_e_skip_log}")

    # v10.6.43: flush exact/no-QT-match LOG_ONLY batch (env var OFF by default)
    if exact_no_qt_eval_batch:
        write_exact_no_qt_match_evals(exact_no_qt_eval_batch)

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
            summary += f" {mgmt['resolved']} resueltas (esperando pago)\n"
        if mgmt["kept"] > 0:
            summary += f"✓ {mgmt['kept']} mantenidas\n"

        # Compras
        if buy_summaries:
            for b in buy_summaries:
                trader_tag = " " if b["traders"] else ""
                mode_tag = _format_buy_mode_tag(b.get("city_mode"))
                summary += (
                    f"🛒 Compra {mode_tag}: {b['side']} {b['city']} "
                    f"${b['amount']:.2f} edge={b['edge']:.0f}%{trader_tag}\n"
                )
        elif not mgmt["n_sold"]:
            summary += f"💤 Sin operaciones\n"

        # Estado
        summary += f"{'─' * 25}\n"
        summary += (
            f"Candidatos: {len(candidates)} | Con edge: {len(trades)} | "
            f"Shadow con edge: {len(shadow_trades)}\n"
        )
        summary += f"Condición filtrada: {condition_filtered_skip} mercados (range/exact)\n"
        summary += f"Exposición actual: ${current_exposure:.2f} | Presupuesto libre: ${budget_left:.2f}\n"

        send_telegram(summary, with_menu=True)

    dl.append(f"\n{'='*50}")

    # Guardar log de decisiones
    _save_decision_log(dl)

    # --- v10.4.1: Guardar resumen de ciclo para historial ---
    try:
        cycle_timestamp = datetime.now(timezone.utc)
        slot_metrics = build_cycle_slot_metrics(
            timestamp_utc=cycle_timestamp,
            candidates=candidates if 'candidates' in locals() else [],
            trades=trades if 'trades' in locals() else [],
            selected=selected if 'selected' in locals() else [],
            buys=buy_summaries if 'buy_summaries' in locals() else [],
            skip_log_entries=skip_log_entries if 'skip_log_entries' in locals() else [],
            execution_failures=execution_failures if 'execution_failures' in locals() else [],
        )
        cycle_data = {
            "version": BOT_VERSION,
            "logic_series": LOGIC_SERIES,
            "cycle_number": bot_state["cycle_count"] + 1,
            "logic_cycle_number": bot_state.get("cycle_count_series", 0) + 1,
            "timestamp_utc": cycle_timestamp.isoformat(),
            "mode": "DRY_RUN" if DRY_RUN else "REAL",
            "management": {
                "n_kept": mgmt.get("n_kept", 0),
                "n_sold": mgmt.get("n_sold", 0),
                "n_resolved": mgmt.get("n_resolved", 0),
                "n_loss_total": mgmt.get("n_loss_total", 0),
            },
            "scan": {
                "discovered_markets_unique": discovered_markets_unique if 'discovered_markets_unique' in locals() else None,
                "markets_evaluated": len(candidates) if 'candidates' in locals() else 0,
                "with_edge": len(trades) if 'trades' in locals() else 0,
                "selected": len(selected) if 'selected' in locals() else 0,
                "shadow": len(shadow_trades) if 'shadow_trades' in locals() else 0,
                "condition_filtered": condition_filtered_skip if 'condition_filtered_skip' in locals() else 0,
                "city_window_skipped": city_window_skipped if 'city_window_skipped' in locals() else 0,
                "city_window_cities": sorted(city_window_cities) if 'city_window_cities' in locals() else [],
                "slot_metrics": slot_metrics,
            },
            "buys": [
                {
                    "city": b.get("city", "?"),
                    "days_ahead": b.get("days_ahead"),
                    "side": b.get("side", "?"),
                    "amount": round(b.get("amount", 0), 2),
                    "edge": round(b.get("edge", 0), 1),
                    "city_mode": b.get("city_mode", ""),
                    "traders": bool(b.get("traders")),
                }
                for b in (buy_summaries if 'buy_summaries' in locals() else [])
            ],
            "scanned_markets": observed_cycle_markets if 'observed_cycle_markets' in locals() else [],
            "exposure_after": round(current_exposure, 2) if 'current_exposure' in locals() else None,
            "budget_left": round(budget_left, 2) if 'budget_left' in locals() else None,
        }
        # Último ciclo (se sobreescribe)
        with open(CYCLE_SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(cycle_data, f, indent=2, ensure_ascii=False)
        # Historial acumulativo (append-only, una línea JSON por ciclo)
        with open(CYCLES_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(cycle_data, ensure_ascii=False) + "\n")
        funnel_record = build_funnel_observability_record(
            cycle_data,
            discovered_markets_unique=discovered_markets_unique if 'discovered_markets_unique' in locals() else None,
        )
        write_funnel_observability_log_only(funnel_record)
        log.info("cycle_summary guardado OK")
    except Exception as e:
        log.warning(f"Error guardando cycle_summary: {e}")

    # --- v10.6.42: SQLite Recorder (Fase 0 — aditivo, fail-safe, no afecta trading) ---
    if SQLITE_RECORDER_ENABLED:
        try:
            import sqlite_recorder as _sr
            _sr.SQLiteRecorder(SQLITE_DB_PATH).record_cycle(cycle_data)
            log.info("SQLiteRecorder: ciclo persistido OK")
        except NameError:
            log.warning("SQLiteRecorder: cycle_data no disponible (ciclo abortado antes)")
        except Exception as _sqlite_err:
            log.warning(f"SQLiteRecorder: error no critico (ciclo continua): {_sqlite_err}")

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
            if "" in text:
                summary += f"🟢 {text}\n"
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
        elif line.strip().startswith(""):
            summary += f" {line.strip()[2:]}\n"
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
    if _SCHEDULE_HOURS_DISABLED:
        log.info(f"Schedule disabled hours: {sorted(_SCHEDULE_HOURS_DISABLED)} UTC")
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
        send_telegram(" <b>Error autenticación</b>")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        threading.Thread(target=telegram_polling_loop, daemon=True, name="TelegramPoller").start()
        log.info("Telegram polling: OK")

    # v10.5.1: Intra-cycle SL monitor
    if INTRA_SL_INTERVAL > 0 and clob_client is not None:
        threading.Thread(target=intra_sl_loop, args=(clob_client,), daemon=True, name="IntraSL").start()
        log.info(f"[INTRA-SL] Monitor cada {INTRA_SL_INTERVAL}min: OK")

    modo = "DRY RUN" if DRY_RUN else "REAL"
    schedule = ", ".join(f"{h:02d}:00" for h in sorted(SCHEDULE_HOURS_UTC))
    intra_str = f" | Intra-SL cada {INTRA_SL_INTERVAL}min" if INTRA_SL_INTERVAL > 0 else ""
    topology = _build_topology_line()
    send_telegram(
        f"🤖 <b>Bot {BOT_VERSION} arrancado</b>\n"
        f"Modo: {modo} | ${BANKROLL:.2f}\n"
        f"Min edge: {MIN_EDGE}% | Schedule: {schedule} UTC\n"
        f"🔧 SL/TP en ciclo: -{STOP_LOSS_PCT}%/+{TAKE_PROFIT_PCT}%{intra_str}\n"
        f"🗺 Ciudades: {topology}\n"
        f" Traders: auto-análisis diario, descubrimiento lunes",
        with_menu=True,
    )

    try:
        rebuilt = backfill_postmortem_from_performance()
        if rebuilt > 0:
            log.info(f"postmortem listo al arrancar: {rebuilt} registros")
    except Exception as e:
        log.warning(f"Error en backfill de postmortem al arrancar: {e}")

    try:
        lifecycle = _sync_trade_lifecycle_from_sources()
        log.info(f"trade_lifecycle listo al arrancar: {len(lifecycle.get('records', []))} registros")
    except Exception as e:
        log.warning(f"Error sincronizando trade_lifecycle al arrancar: {e}")

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
                            f" <b>Bot arrancado</b>\n"
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
            send_telegram(f" <b>Error</b>\n<code>{str(e)[:200]}</code>")

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
            send_telegram(f" <b>Error</b>\n<code>{str(e)[:200]}</code>")
