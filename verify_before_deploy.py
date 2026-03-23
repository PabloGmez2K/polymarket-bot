"""
verify_before_deploy.py — Verificación pre-deploy v2
=====================================================

Verifica que bot.py está listo para producción ANTES de hacer push.
NO coloca órdenes reales. Solo verifica lógica, APIs y configuración.

Cada test nace de un bug real que nos costó dinero:
  - Test de exposición: bug de $9.23 fantasma bloqueando presupuesto
  - Test MIN_DAYS: bug de -$7.50 comprando contra info conocida
  - Test mercados resueltos: error "orderbook does not exist"
  - Test sigma: 5/5 pérdidas por sobreconfianza en v9

Uso:
    cd C:/Projects/polymarket-bot
    python verify_before_deploy.py
"""

import os
import sys
import json
import inspect

# Verificar que estamos en el directorio correcto
if not os.path.exists("bot.py"):
    print("❌ Ejecuta desde C:\\Projects\\polymarket-bot")
    sys.exit(1)

print("=" * 60)
print("🔍 VERIFICACIÓN PRE-DEPLOY v2")
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
    )
    ok("Importación OK")
    print(f"     BANKROLL=${BANKROLL} | MIN_EDGE={MIN_EDGE}%")
    print(f"     SL={STOP_LOSS_PCT}% | TP=+{TAKE_PROFIT_PCT}% | MAX_EXP={MAX_EXPOSURE_PCT*100:.0f}%")
except Exception as e:
    fail(f"Importación FALLÓ: {e}")
    print("\n  ⛔ No se puede continuar sin importar bot.py")
    sys.exit(1)


# ============================================================
# TEST: Funciones críticas existen
# ============================================================
test("Funciones críticas...")
critical_fns = {
    "manage_positions": "Gestión activa de posiciones",
    "track_trade": "Performance tracker",
    "get_performance_summary": "Resumen de rendimiento",
    "audit_check_sell_fills": "Auditoría de ventas",
    "audit_check_forecasts": "Auditoría de previsiones",
    "audit_register_pending_sell": "Registro de ventas pendientes",
    "get_effective_bankroll": "Bankroll dinámico",
    "get_current_exposure": "Exposición acumulativa",
    "parse_city_from_title": "Parser de ciudad",
    "get_min_days_ahead": "MIN_DAYS dinámico",
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
# TEST: get_current_exposure usa currentValue (NO initialValue)
# Bug real: posiciones de $0.11 contaban como $9.23 de exposición
# ============================================================
test("Fix exposición fantasma (currentValue vs initialValue)...")
try:
    from bot import get_current_exposure
    source = inspect.getsource(get_current_exposure)

    # DEBE usar currentValue para calcular exposición
    uses_current = "current_value" in source or "currentValue" in source
    # NO DEBE sumar initialValue como exposición
    sums_initial = "initial_value" in source and "total" in source.lower()
    # Variable de acumulación debe ser current, no initial
    uses_total_exposure = "total_exposure" in source

    if uses_current and uses_total_exposure and not sums_initial:
        ok("Exposición usa currentValue (lo que vale, no lo que pagamos)")
    elif uses_current and "initial_value" not in source:
        ok("Exposición usa currentValue")
    else:
        fail("get_current_exposure puede estar usando initialValue — esto bloqueó el bot con $9.23 fantasma")
        print("     Debe sumar currentValue de cada posición, NO initialValue")
except Exception as e:
    warn(f"No pude verificar get_current_exposure: {e}")


# ============================================================
# TEST: MIN_DAYS_AHEAD dinámico (get_min_days_ahead)
# Bug real: -$7.50 comprando día-0 a las 16:00 UTC
# ============================================================
test("MIN_DAYS_AHEAD dinámico...")
try:
    from bot import get_min_days_ahead, MIN_DAYS_AHEAD

    # Verificar que la función existe y tiene lógica horaria
    source = inspect.getsource(get_min_days_ahead)
    has_hour_check = "hour" in source.lower()
    has_return_0 = "return 0" in source
    has_return_1 = "return 1" in source

    if has_hour_check and has_return_0 and has_return_1:
        ok(f"get_min_days_ahead() tiene lógica por hora UTC")
    else:
        fail("get_min_days_ahead() no diferencia mañana/tarde")

    # Verificar el default
    if MIN_DAYS_AHEAD == -1:
        ok("MIN_DAYS_AHEAD=-1 (modo automático)")
    elif MIN_DAYS_AHEAD >= 0:
        warn(f"MIN_DAYS_AHEAD={MIN_DAYS_AHEAD} (override manual — ¿es intencional?)")
    else:
        warn(f"MIN_DAYS_AHEAD={MIN_DAYS_AHEAD} (valor inesperado)")

except ImportError:
    fail("get_min_days_ahead NO existe — el bot comprará día-0 por la tarde")
except Exception as e:
    warn(f"No pude verificar MIN_DAYS_AHEAD: {e}")


# ============================================================
# TEST: manage_positions skip mercados resueltos (curPrice>=0.98)
# Bug real: error "orderbook does not exist" en mercados ya pagados
# ============================================================
test("Skip mercados resueltos en manage_positions...")
try:
    from bot import manage_positions
    source = inspect.getsource(manage_positions)

    if "0.98" in source and "cur_price" in source:
        ok("Skip curPrice >= 0.98 (mercados resueltos)")
    else:
        fail("manage_positions NO skipea mercados resueltos — dará error 'orderbook does not exist'")
except Exception as e:
    warn(f"No pude verificar: {e}")


# ============================================================
# TEST: manage_positions tiene los 3 checks + filtro $0.10
# ============================================================
test("Lógica de manage_positions...")
try:
    from bot import manage_positions
    source = inspect.getsource(manage_positions)

    checks = {
        "Stop-loss": "STOP_LOSS_PCT" in source,
        "Take-profit": "TAKE_PROFIT_PCT" in source,
        "Re-evaluación": "get_forecast" in source and "edge_pct" in source,
        "Filtro $0.10": "0.10" in source,
    }

    for name, found in checks.items():
        if found:
            print(f"  ✅ {name}")
        else:
            fail(f"manage_positions: falta {name}")

    if all(checks.values()):
        ok("manage_positions tiene los 3 checks + filtro mínimo")
except Exception as e:
    warn(f"No pude inspeccionar manage_positions: {e}")


# ============================================================
# TEST: Fix bankroll Magic wallet (fallback cuando cash=0)
# ============================================================
test("Fix bankroll Magic wallet...")
try:
    from bot import get_effective_bankroll
    source = inspect.getsource(get_effective_bankroll)

    if "cash_balance < 0.01" in source or "cash_balance == 0" in source:
        ok(f"Fallback cuando cash=0: usa BANKROLL=${BANKROLL}")
    else:
        fail("get_effective_bankroll NO tiene fallback para cash=0")
except Exception as e:
    warn(f"No pude verificar: {e}")


# ============================================================
# TEST: Sigma calibrada (v10) — no sobreconfiada
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
    print(f"     Mínimo: día0=1.0, día1=1.2. Actual: día0={sigma_0}, día1={sigma_1}")


# ============================================================
# TEST: Kelly sizing
# ============================================================
test("Kelly sizing...")

# Edge 15%: debería generar posición razonable
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

# Edge 7%: debería funcionar
pos_7 = calculate_position(25.0, 0.20, 0.13)
if pos_7 is not None and pos_7["amount"] >= MIN_BET:
    ok(f"Edge 7%: ${pos_7['amount']:.2f}")
else:
    warn("Edge 7% no genera posición (puede ser normal)")

# $2 bankroll: NO debería generar posición
pos_broke = calculate_position(2.0, 0.45, 0.30)
if pos_broke is None or pos_broke["amount"] < MIN_BET:
    ok("$2 bankroll: no genera posición (correcto)")
else:
    warn(f"$2 bankroll genera ${pos_broke['amount']:.2f}")


# ============================================================
# TEST: Modelo de probabilidad
# ============================================================
test("Modelo de probabilidad...")

# London 16°C exact, forecast 15.7°C, día 1 → debería ser ~20-35%
prob1 = estimate_prob(15.7, 16.0, "exact", 1)
if 10 < prob1 * 100 < 45:
    ok(f"London exact: {prob1*100:.1f}% (razonable)")
else:
    warn(f"London exact: {prob1*100:.1f}% (revisar)")

# NYC 60°F, forecast 10°C, día 0 → debería ser muy baja
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
    req.add_header("User-Agent", "verify/2.0")
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
# TEST: API Open-Meteo (previsiones meteorológicas)
# ============================================================
test("API Open-Meteo...")
try:
    import urllib.request
    # Test con coordenadas de London City Airport
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
    fail(f"Open-Meteo falló: {e} — el bot no podrá calcular probabilidades")


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
        req.add_header("User-Agent", "verify/2.0")
        resp = urllib.request.urlopen(req, timeout=10)
        positions = json.loads(resp.read())

        # Usar currentValue (no initialValue) — ¡el mismo fix del bot!
        active = [p for p in positions if float(p.get("currentValue", 0)) >= 0.10]
        dead = [p for p in positions if float(p.get("currentValue", 0)) < 0.10 and float(p.get("currentValue", 0)) > 0]
        total_current = sum(float(p.get("currentValue", 0)) for p in positions)
        active_value = sum(float(p.get("currentValue", 0)) for p in active)
        dead_invested = sum(float(p.get("initialValue", 0)) for p in dead)

        print(f"     Posiciones: {len(active)} activas (${active_value:.2f}) + {len(dead)} muertas (${dead_invested:.2f} invertido)")
        print(f"     Valor total: ${total_current:.2f}")

        # Exposición basada en currentValue (lo correcto)
        exposure_pct = (active_value / BANKROLL * 100)
        print(f"     Exposición real: ${active_value:.2f} ({exposure_pct:.0f}% de ${BANKROLL})")

        if exposure_pct <= 50:
            ok(f"Exposición {exposure_pct:.0f}% — dentro de límites")
        else:
            warn(f"Exposición {exposure_pct:.0f}% — alta pero puede ser temporal")

        for p in active:
            title = p.get("title", "?")[:45]
            outcome = p.get("outcome", "?")
            pct = float(p.get("percentPnl", 0))
            val = float(p.get("currentValue", 0))
            icon = "🟢" if pct >= 0 else "🔴"
            print(f"     {icon} {outcome} ${val:.2f} ({pct:+.1f}%) | {title}")

except Exception as e:
    warn(f"Error verificando cartera: {e}")


# ============================================================
# TEST: Telegram (enviar mensaje de test)
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
        # Solo verificar que el token es válido (getMe), no enviar mensaje
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
        content = f.read(3000)  # Solo el header

    import re
    version_match = re.search(r"bot\.py (v\d+\.\d+)", content)
    if version_match:
        version = version_match.group(1)
        ok(f"Versión: {version}")
    else:
        warn("No encontré versión en el header de bot.py")
except Exception as e:
    warn(f"No pude leer versión: {e}")


# ============================================================
# TEST: Archivos necesarios existen
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

# Verificar que .gitignore tiene .env
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
print(f"📊 RESUMEN DE VERIFICACIÓN")
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
    # Detectar versión para el commit sugerido
    version = "v10.2"
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
    print(f'  git commit -m "{version}: verificado y listo"')
    print(f"  git push")

print()
