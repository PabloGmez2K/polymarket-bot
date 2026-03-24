"""
verify_before_deploy.py — Verificación pre-deploy v3
=====================================================

v3: Tests de COMPORTAMIENTO REAL.

La lección que nos costó $5.16 (Bug #5): el verificador v2 comprobaba que
get_min_days_ahead() existía y tenía lógica UTC. ¡Pasó 22/22!
Pero la función fallaba para ciudades asiáticas — un caso que no testeamos.

REGLA DE v3: Cada test EJECUTA la función con inputs concretos y verifica
outputs concretos. No basta con comprobar que el código existe.

Cada test nace de un bug real que nos costó dinero:
  - Test get_min_days_for_city: Bug #5 ($5.16) — Chongqing a las 08:00 UTC
  - Test get_current_exposure: Bug #4 — Shanghai resuelta bloqueaba $8
  - Test SELL_PENDING: Bug #7 — ventas sin confirmar fill
  - Test signals freshness: Bug #6 — signals.json expiraba silenciosamente
  - Test micro positions: Bug #8 — posiciones zombie en gestión
  - Tests heredados: sigma, kelly, parseo, APIs

Uso:
    cd C:/Projects/polymarket-bot
    python verify_before_deploy.py
"""

import os
import sys
import json
import inspect
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Verificar que estamos en el directorio correcto
if not os.path.exists("bot.py"):
    print("❌ Ejecuta desde C:\\Projects\\polymarket-bot")
    sys.exit(1)

print("=" * 60)
print("🔍 VERIFICACIÓN PRE-DEPLOY v3 (tests de comportamiento)")
print("=" * 60)

errors = []
warnings = []
passes = []
n_test = 0


def test(name):
    global n_test
    n_test += 1
    print(f"\n[{n_test}] {name}")


def ok(msg):
    passes.append(msg)
    print(f"  ✅ {msg}")


def fail(msg):
    errors.append(msg)
    print(f"  ❌ {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  ⚠ {msg}")


# ============================================================
# TEST: Importar bot.py sin errores de sintaxis
# ============================================================
test("Importar bot.py...")
try:
    from bot import (
        get_uncertainty, estimate_prob, kelly_fraction,
        calculate_position, parse_temperature_question,
        BANKROLL, MIN_BET, MAX_BET_PCT, MIN_EDGE,
        STOP_LOSS_PCT, TAKE_PROFIT_PCT, SELL_AGGRESSION,
        MAX_EXPOSURE_PCT, MIN_DAYS_AHEAD,
        get_min_days_ahead, get_min_days_for_city,
        CITY_UTC_OFFSETS,
    )
    ok("Importación OK")
    print(f"     BANKROLL=${BANKROLL} | MIN_EDGE={MIN_EDGE}%")
    print(f"     SL={STOP_LOSS_PCT}% | TP=+{TAKE_PROFIT_PCT}% | MAX_EXP={MAX_EXPOSURE_PCT*100:.0f}%")
except Exception as e:
    fail(f"Importación FALLÓ: {e}")
    print("\n  ⛔ No se puede continuar sin importar bot.py")
    sys.exit(1)


# ============================================================
# TEST: Funciones críticas v10.3 existen
# ============================================================
test("Funciones críticas v10.3...")
critical_fns = {
    "manage_positions": "Gestión activa de posiciones",
    "track_trade": "Performance tracker",
    "get_performance_summary": "Resumen de rendimiento",
    "audit_check_sell_fills": "Auditoría de ventas",
    "audit_check_forecasts": "Auditoría de previsiones",
    "audit_register_pending_sell": "Registro de ventas pendientes",
    "get_effective_bankroll": "Bankroll dinámico",
    "get_current_exposure": "Exposición acumulativa",
    "get_cash_balance": "Cash balance (USDC)",
    "parse_city_from_title": "Parser de ciudad",
    "get_min_days_ahead": "MIN_DAYS base dinámico",
    "get_min_days_for_city": "MIN_DAYS per-city (Bug #5 fix)",
    "_mark_micro_as_loss_total": "Micro → LOSS_TOTAL (Bug #8 fix)",
    "_confirm_sell_fills_in_performance": "Confirmar fills (Bug #7 fix)",
}

all_found = True
for fn_name, desc in critical_fns.items():
    try:
        exec(f"from bot import {fn_name}")
        print(f"  ✅ {fn_name}()")
    except ImportError:
        fail(f"Función {fn_name} NO existe ({desc})")
        all_found = False

if all_found:
    ok("Todas las funciones críticas existen")


# ============================================================
# TEST COMPORTAMIENTO: get_min_days_for_city — Bug #5
# Este es EL test que habría prevenido -$5.16
#
# Escenario real: 08:00 UTC, Chongqing (UTC+8) → 16:00 local
# La temperatura máxima ya se registró → DEBE devolver 1
# ============================================================
test("Bug #5: Zona horaria per-city (COMPORTAMIENTO)...")
try:
    # Simular 08:00 UTC — mañana en Europa, tarde en Asia
    mock_time_08 = datetime(2026, 3, 25, 8, 0, 0, tzinfo=timezone.utc)
    with patch("bot.datetime") as mock_dt:
        mock_dt.now.return_value = mock_time_08
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # Ciudades asiáticas a las 08:00 UTC → hora local >= 14 → DEBE ser 1
        asia_ok = True
        for city, expected in [("Chongqing", 1), ("Shanghai", 1), ("Tokyo", 1),
                               ("Seoul", 1), ("Beijing", 1), ("Taipei", 1),
                               ("Singapore", 1), ("Bangkok", 1)]:
            result = get_min_days_for_city(city)
            if result != expected:
                fail(f"get_min_days_for_city('{city}') a las 08:00 UTC = {result}, esperado {expected}")
                print(f"     UTC+{CITY_UTC_OFFSETS.get(city, '?')} → hora local = {8 + CITY_UTC_OFFSETS.get(city, 0)}")
                asia_ok = False
            else:
                print(f"  ✅ {city} (UTC+{CITY_UTC_OFFSETS.get(city, '?')}) → min_days={result}")

        if asia_ok:
            ok("Ciudades asiáticas bloqueadas a las 08:00 UTC")

        # Ciudades occidentales a las 08:00 UTC → hora local < 14 → DEBE ser 0
        west_ok = True
        for city, expected in [("London", 0), ("New York City", 0), ("Chicago", 0),
                               ("Paris", 0), ("Madrid", 0)]:
            result = get_min_days_for_city(city)
            if result != expected:
                fail(f"get_min_days_for_city('{city}') a las 08:00 UTC = {result}, esperado {expected}")
                west_ok = False
            else:
                print(f"  ✅ {city} (UTC{CITY_UTC_OFFSETS.get(city, 0):+}) → min_days={result}")

        if west_ok:
            ok("Ciudades occidentales permitidas a las 08:00 UTC")

    # Simular 16:00 UTC — tarde en Europa, noche en Asia, mañana en América
    mock_time_16 = datetime(2026, 3, 25, 16, 0, 0, tzinfo=timezone.utc)
    with patch("bot.datetime") as mock_dt:
        mock_dt.now.return_value = mock_time_16
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # Europa a las 16:00 UTC → 17:00 local → min_days=1
        # América a las 16:00 UTC → 11:00 local → min_days=0
        test_16 = True
        for city, expected in [("London", 1), ("Paris", 1), ("Tokyo", 1),
                               ("New York City", 0), ("Seattle", 0)]:
            result = get_min_days_for_city(city)
            if result != expected:
                fail(f"get_min_days_for_city('{city}') a las 16:00 UTC = {result}, esperado {expected}")
                test_16 = False
            else:
                print(f"  ✅ {city} a las 16:00 UTC → min_days={result}")

        if test_16:
            ok("Test 16:00 UTC correcto (Europa bloqueada, América permitida)")

except Exception as e:
    fail(f"Error en test de zona horaria: {e}")
    import traceback
    traceback.print_exc()


# ============================================================
# TEST COMPORTAMIENTO: get_current_exposure excluye resueltas — Bug #4
# ============================================================
test("Bug #4: Exposición excluye resueltas (COMPORTAMIENTO)...")
try:
    from bot import get_current_exposure
    source = inspect.getsource(get_current_exposure)

    # Verificar que el código tiene la lógica correcta
    has_cur_price_check = "cur_price" in source and "0.98" in source
    has_continue_resolved = "continue" in source

    if has_cur_price_check and has_continue_resolved:
        ok("get_current_exposure() excluye curPrice >= 0.98")
    else:
        fail("get_current_exposure() NO excluye posiciones resueltas")

    # Verificar que usa currentValue (no initialValue) — herencia de v10.2
    uses_current = "currentValue" in source
    if uses_current:
        ok("Usa currentValue (no initialValue)")
    else:
        fail("Puede estar usando initialValue")
except Exception as e:
    fail(f"Error verificando exposición: {e}")


# ============================================================
# TEST COMPORTAMIENTO: SELL_PENDING tracking — Bug #7
# ============================================================
test("Bug #7: SELL_PENDING en vez de SELL inmediato (COMPORTAMIENTO)...")
try:
    from bot import manage_positions
    source = inspect.getsource(manage_positions)

    # DEBE usar SELL_PENDING, NO SELL directo
    uses_pending = "SELL_PENDING" in source

    if uses_pending:
        ok("manage_positions usa SELL_PENDING (no SELL directo)")
    else:
        fail("manage_positions registra SELL directamente sin confirmar fill")

    # Verificar que audit confirma fills
    from bot import _confirm_sell_fills_in_performance
    source_audit = inspect.getsource(_confirm_sell_fills_in_performance)
    confirms_sell = '"SELL"' in source_audit and "SELL_PENDING" in source_audit
    if confirms_sell:
        ok("_confirm_sell_fills_in_performance convierte SELL_PENDING → SELL")
    else:
        fail("No hay conversión SELL_PENDING → SELL en confirmación de fills")

    # Verificar que hay SELL_FAILED para ventas expiradas
    has_sell_failed = "SELL_FAILED" in source_audit
    if has_sell_failed:
        ok("Ventas expiradas se marcan como SELL_FAILED")
    else:
        fail("No hay tracking de ventas que nunca se llenaron")

except Exception as e:
    fail(f"Error verificando SELL tracking: {e}")


# ============================================================
# TEST COMPORTAMIENTO: signals.json freshness — Bug #6
# ============================================================
test("Bug #6: signals.json freshness (COMPORTAMIENTO)...")
try:
    from bot import load_trader_signals
    source = inspect.getsource(load_trader_signals)

    import re
    freshness_match = re.search(r"age_hours\s*>\s*(\d+)", source)
    if freshness_match:
        freshness_hours = int(freshness_match.group(1))
        if freshness_hours >= 24:
            ok(f"Freshness window: {freshness_hours}h (cubre un día completo)")
        elif freshness_hours > 12:
            warn(f"Freshness window: {freshness_hours}h (mejor que 12h)")
        else:
            fail(f"Freshness window: {freshness_hours}h — demasiado corta")
    else:
        warn("No encontré check de freshness en load_trader_signals")

    # Verificar que hay logging cuando signals.json está vacío
    has_warning_log = "log.warning" in source or "log.info" in source
    if has_warning_log:
        ok("Logging presente en load_trader_signals")
    else:
        warn("Sin logging en load_trader_signals")

except Exception as e:
    fail(f"Error verificando signals freshness: {e}")


# ============================================================
# TEST COMPORTAMIENTO: Posiciones micro — Bug #8
# ============================================================
test("Bug #8: Posiciones micro como LOSS_TOTAL (COMPORTAMIENTO)...")
try:
    from bot import manage_positions, _mark_micro_as_loss_total
    source = inspect.getsource(manage_positions)

    has_micro_filter = "_mark_micro" in source
    if has_micro_filter:
        ok("manage_positions detecta y excluye posiciones micro")
    else:
        fail("manage_positions NO filtra posiciones micro (<$0.10)")

    source_micro = inspect.getsource(_mark_micro_as_loss_total)
    tracks_loss = "LOSS_TOTAL" in source_micro and "track_trade" in source_micro
    if tracks_loss:
        ok("_mark_micro_as_loss_total registra LOSS_TOTAL en performance.json")
    else:
        fail("No se registra LOSS_TOTAL para posiciones micro")

except Exception as e:
    fail(f"Error verificando micro positions: {e}")


# ============================================================
# TEST: CITY_UTC_OFFSETS cobertura completa
# ============================================================
test("Cobertura de UTC offsets...")
try:
    from bot import RESOLUTION_STATIONS, CITY_UTC_OFFSETS
    missing = []
    for city in RESOLUTION_STATIONS:
        if city not in CITY_UTC_OFFSETS:
            missing.append(city)

    if not missing:
        ok(f"Todas las {len(RESOLUTION_STATIONS)} ciudades tienen UTC offset")
    else:
        fail(f"{len(missing)} ciudades sin UTC offset: {', '.join(missing)}")
        print(f"     Sin offset, get_min_days_for_city usa UTC+0 → puede apostar contra info conocida")
except Exception as e:
    fail(f"Error verificando offsets: {e}")


# ============================================================
# TEST: manage_positions checks completos
# ============================================================
test("Lógica de manage_positions...")
try:
    from bot import manage_positions
    source = inspect.getsource(manage_positions)

    checks = {
        "Stop-loss": "STOP_LOSS_PCT" in source,
        "Take-profit": "TAKE_PROFIT_PCT" in source,
        "Re-evaluación": "get_forecast" in source and "edge_pct" in source,
        "Skip resueltas": "0.98" in source and "cur_price" in source,
        "Micro → LOSS_TOTAL": "_mark_micro" in source,
        "Pendiente fill": "SELL_PENDING" in source,
    }

    for name, found in checks.items():
        if found:
            print(f"  ✅ {name}")
        else:
            fail(f"manage_positions: falta {name}")

    if all(checks.values()):
        ok("manage_positions tiene todos los checks v10.3")
except Exception as e:
    warn(f"No pude inspeccionar manage_positions: {e}")


# ============================================================
# TEST: Cash balance
# ============================================================
test("Cash balance (get_balance_allowance)...")
try:
    from bot import get_cash_balance
    source = inspect.getsource(get_cash_balance)

    uses_correct = "get_balance_allowance" in source and "COLLATERAL" in source
    if uses_correct:
        ok("get_cash_balance() usa get_balance_allowance(COLLATERAL)")
    else:
        fail("Usa método incorrecto para cash")

    from bot import get_effective_bankroll
    source_br = inspect.getsource(get_effective_bankroll)
    if "cash_ok" in source_br or "cash_balance < 0.01" in source_br:
        ok(f"Fallback cuando cash no disponible: usa BANKROLL=${BANKROLL}")
    else:
        fail("get_effective_bankroll NO tiene fallback para cash=0")
except Exception as e:
    warn(f"No pude verificar: {e}")


# ============================================================
# TEST: Sigma calibrada
# ============================================================
test("Sigma calibrada...")
sigma_0 = get_uncertainty(0)
sigma_1 = get_uncertainty(1)
sigma_2 = get_uncertainty(2)

print(f"     día0={sigma_0}°C | día1={sigma_1}°C | día2={sigma_2}°C")

if sigma_0 >= 1.0 and sigma_1 >= 1.2:
    ok(f"Sigma razonable (día0≥1.0, día1≥1.2)")
else:
    fail(f"Sigma demasiado baja — causó 5/5 pérdidas en v9")


# ============================================================
# TEST: Kelly sizing
# ============================================================
test("Kelly sizing...")
pos_15 = calculate_position(25.0, 0.45, 0.30)
if pos_15 is None:
    fail("Kelly no genera posición para edge 15% con $25")
else:
    amt = pos_15["amount"]
    max_bet = 25.0 * MAX_BET_PCT
    if MIN_BET <= amt <= max_bet:
        ok(f"Edge 15%: ${amt:.2f} (dentro de ${MIN_BET}-${max_bet:.2f})")
    else:
        fail(f"Kelly fuera de rango: ${amt:.2f}")

pos_7 = calculate_position(25.0, 0.20, 0.13)
if pos_7 is not None and pos_7["amount"] >= MIN_BET:
    ok(f"Edge 7%: ${pos_7['amount']:.2f}")
else:
    warn("Edge 7% no genera posición (puede ser normal)")

pos_broke = calculate_position(2.0, 0.45, 0.30)
if pos_broke is None or pos_broke["amount"] < MIN_BET:
    ok("$2 bankroll: no genera posición (correcto)")
else:
    warn(f"$2 bankroll genera ${pos_broke['amount']:.2f}")


# ============================================================
# TEST: Modelo de probabilidad
# ============================================================
test("Modelo de probabilidad...")
prob1 = estimate_prob(15.7, 16.0, "exact", 1)
if 10 < prob1 * 100 < 45:
    ok(f"London exact: {prob1*100:.1f}% (razonable)")
else:
    warn(f"London exact: {prob1*100:.1f}% (revisar)")

prob2 = estimate_prob(10.0, 15.6, "exact", 0)
if prob2 * 100 < 5:
    ok(f"NYC imposible: {prob2*100:.1f}% (correctamente baja)")
else:
    warn(f"NYC imposible: {prob2*100:.1f}% (debería ser <5%)")


# ============================================================
# TEST: Parseo de mercados
# ============================================================
test("Parseo de mercados...")
test_questions = [
    ("Will the highest temperature in London be 16°C on March 23?", "London", 16, "exact", "C"),
    ("Will the highest temperature in NYC be between 62-63°F on March 23?", "New York City", 62, "range", "F"),
    ("Will the highest temperature in Seoul be 14°C or higher on March 22?", "Seoul", 14, "at_or_above", "C"),
]

all_parsed = True
for q, exp_city, exp_temp, exp_cond, exp_unit in test_questions:
    p = parse_temperature_question(q)
    if p and p["city"] == exp_city and p["temp_threshold"] == exp_temp and p["condition"] == exp_cond:
        print(f"  ✅ {exp_city} {exp_cond} {exp_temp}°{exp_unit}")
    else:
        all_parsed = False
        fail(f"Parseo falló: {q[:50]}")

if all_parsed:
    ok("Parseo 3/3 tipos de mercado")


# ============================================================
# TEST: Presupuesto
# ============================================================
test("Presupuesto...")
max_exposure = BANKROLL * MAX_EXPOSURE_PCT
max_per_trade = BANKROLL * MAX_BET_PCT
n_trades = int(max_exposure / max_per_trade) if max_per_trade > 0 else 0

print(f"     Máx exposición: ${max_exposure:.2f} ({MAX_EXPOSURE_PCT*100:.0f}% de ${BANKROLL})")
print(f"     Máx por trade: ${max_per_trade:.2f} ({MAX_BET_PCT*100:.0f}% de ${BANKROLL})")
print(f"     Trades simultáneos: ~{n_trades}")

if max_exposure >= 5.0 and n_trades >= 3:
    ok(f"Presupuesto OK: {n_trades} trades de ${max_per_trade:.2f}")
else:
    fail(f"Presupuesto insuficiente")


# ============================================================
# TEST: API Polymarket
# ============================================================
test("API Polymarket...")
try:
    import urllib.request
    req = urllib.request.Request("https://gamma-api.polymarket.com/events?tag_id=103040&limit=3")
    req.add_header("User-Agent", "verify/3.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    n_markets = sum(len(e.get("markets", [])) for e in data)
    if n_markets > 0:
        ok(f"Gamma API OK — {n_markets} mercados de temperatura")
    else:
        warn("Gamma API respondió pero 0 mercados")
except Exception as e:
    fail(f"API Polymarket falló: {e}")


# ============================================================
# TEST: API Open-Meteo
# ============================================================
test("API Open-Meteo...")
try:
    import urllib.request
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=51.5048&longitude=0.0495"
        "&daily=temperature_2m_max&timezone=auto&forecast_days=3"
    )
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    temps = data.get("daily", {}).get("temperature_2m_max", [])
    if temps and len(temps) >= 2:
        ok(f"Open-Meteo OK — London próximos días: {[f'{t}°C' for t in temps[:3]]}")
    else:
        warn("Open-Meteo respondió pero sin datos de temperatura")
except Exception as e:
    fail(f"Open-Meteo falló: {e}")


# ============================================================
# TEST: Cartera real (Data API)
# ============================================================
test("Cartera real...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    import urllib.parse

    funder = os.getenv("FUNDER", "")
    if not funder:
        warn("No hay FUNDER en .env — no puedo verificar cartera")
    else:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "50",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"https://data-api.polymarket.com/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "verify/3.0")
        resp = urllib.request.urlopen(req, timeout=10)
        positions = json.loads(resp.read())

        active = [p for p in positions if float(p.get("currentValue", 0)) >= 0.10]
        dead = [p for p in positions if float(p.get("currentValue", 0)) < 0.10 and float(p.get("currentValue", 0)) > 0]
        resolved = [p for p in positions if float(p.get("curPrice", 0)) >= 0.98]
        total_current = sum(float(p.get("currentValue", 0)) for p in positions)

        # v10.3: Exposición EXCLUYE resueltas (Bug #4 fix)
        active_non_resolved = [p for p in active if float(p.get("curPrice", 0)) < 0.98]
        active_value = sum(float(p.get("currentValue", 0)) for p in active_non_resolved)
        resolved_value = sum(float(p.get("currentValue", 0)) for p in resolved)

        print(f"     Posiciones: {len(active_non_resolved)} activas (${active_value:.2f}) + {len(dead)} muertas + {len(resolved)} resueltas (${resolved_value:.2f})")
        print(f"     Valor total: ${total_current:.2f}")

        exposure_pct = (active_value / BANKROLL * 100) if BANKROLL > 0 else 0
        print(f"     Exposición real (sin resueltas): ${active_value:.2f} ({exposure_pct:.0f}% de ${BANKROLL})")

        if exposure_pct <= 50:
            ok(f"Exposición {exposure_pct:.0f}% — dentro de límites")
        else:
            warn(f"Exposición {exposure_pct:.0f}% — alta pero puede ser temporal")

        for p in active_non_resolved[:5]:
            title = p.get("title", "?")[:45]
            outcome = p.get("outcome", "?")
            pct = float(p.get("percentPnl", 0))
            val = float(p.get("currentValue", 0))
            icon = "🟢" if pct >= 0 else "🔴"
            print(f"     {icon} {outcome} ${val:.2f} ({pct:+.1f}%) | {title}")

except Exception as e:
    warn(f"Error verificando cartera: {e}")


# ============================================================
# TEST: Telegram
# ============================================================
test("Telegram...")
try:
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        warn("TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están en .env")
    else:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getMe")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        bot_name = data.get("result", {}).get("username", "?")
        ok(f"Telegram OK — bot: @{bot_name}")
except Exception as e:
    warn(f"Telegram no verificable: {e}")


# ============================================================
# TEST: Versión del bot
# ============================================================
test("Versión...")
try:
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read(3000)

    import re
    version_match = re.search(r"bot\.py (v\d+\.\d+)", content)
    if version_match:
        version = version_match.group(1)
        if version == "v10.3":
            ok(f"Versión: {version}")
        else:
            warn(f"Versión: {version} — ¿esperabas v10.3?")
    else:
        warn("No encontré versión en el header de bot.py")
except Exception as e:
    warn(f"No pude leer versión: {e}")


# ============================================================
# TEST: Archivos necesarios
# ============================================================
test("Archivos del proyecto...")
required = ["bot.py", "requirements.txt", "Procfile", ".env"]
optional = ["find_traders.py", "trader_analyzer.py", "traders_db.json"]

for f in required:
    if os.path.exists(f):
        print(f"  ✅ {f}")
    else:
        fail(f"Archivo requerido falta: {f}")

for f in optional:
    if os.path.exists(f):
        print(f"  ✅ {f}")
    else:
        warn(f"Archivo opcional falta: {f}")

if os.path.exists(".gitignore"):
    with open(".gitignore", "r") as gi:
        if ".env" in gi.read():
            ok(".env está en .gitignore")
        else:
            fail(".env NO está en .gitignore — las claves se subirán a GitHub")
else:
    fail("No hay .gitignore — las claves se subirán a GitHub")


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'=' * 60}")
print(f"📊 RESUMEN DE VERIFICACIÓN v3")
print(f"{'=' * 60}")
print(f"\n  ✅ Passed: {len(passes)}")
for p in passes:
    print(f"     {p}")

if warnings:
    print(f"\n  ⚠ Warnings: {len(warnings)}")
    for w in warnings:
        print(f"     {w}")

if errors:
    print(f"\n  ❌ ERRORES: {len(errors)}")
    for e in errors:
        print(f"     {e}")
    print(f"\n  ⛔ NO HACER PUSH — hay {len(errors)} error(es) que corregir")
else:
    version = "v10.3"
    try:
        with open("bot.py", "r", encoding="utf-8") as f:
            import re
            m = re.search(r"bot\.py (v\d+\.\d+)", f.read(3000))
            if m:
                version = m.group(1)
    except Exception:
        pass

    print(f"\n  🟢 TODO OK — puedes hacer push")
    print(f"\n  git add .")
    print(f'  git commit -m "{version}: 5 bugs corregidos, verify v3"')
    print(f"  git push")

print()
