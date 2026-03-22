"""
verify_before_deploy.py — Verificación pre-deploy Fase 2
=========================================================

Ejecuta ANTES de hacer push para confirmar que todo funciona.
NO coloca órdenes reales. Solo verifica.

Uso:
    cd C:/Projects/polymarket-bot
    python verify_before_deploy.py
"""

import os
import sys
import json

# Verificar que estamos en el directorio correcto
if not os.path.exists("bot.py"):
    print("❌ Ejecuta desde C:\\Projects\\polymarket-bot")
    sys.exit(1)

print("=" * 60)
print("🔍 VERIFICACIÓN PRE-DEPLOY — Fase 2")
print("=" * 60)

errors = []
warnings = []
passes = []

# ============================================================
# TEST 1: Importar funciones del bot
# ============================================================
print("\n[1/13] Importando funciones del bot...")
try:
    from bot import (
        get_uncertainty, estimate_prob, kelly_fraction,
        calculate_position, parse_temperature_question,
        BANKROLL, MIN_BET, MAX_BET_PCT, MIN_EDGE,
        STOP_LOSS_PCT, TAKE_PROFIT_PCT, SELL_AGGRESSION,
        MAX_EXPOSURE_PCT,
    )
    passes.append("Importación OK")
    print(f"  ✅ Importación OK")
    print(f"  BANKROLL=${BANKROLL} | MIN_BET=${MIN_BET} | MAX_BET_PCT={MAX_BET_PCT}")
    print(f"  STOP_LOSS={STOP_LOSS_PCT}% | TAKE_PROFIT=+{TAKE_PROFIT_PCT}%")
    print(f"  MIN_EDGE={MIN_EDGE}% | MAX_EXPOSURE={MAX_EXPOSURE_PCT*100}%")
except Exception as e:
    errors.append(f"Importación FALLÓ: {e}")
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# ============================================================
# TEST 1b: BANKROLL = 25 (no 15)
# ============================================================
print("\n[1b/13] Verificando BANKROLL...")
env_bankroll = os.getenv("BANKROLL", "")
if BANKROLL == 25.0:
    passes.append("BANKROLL=$25 OK")
    print(f"  ✅ BANKROLL=${BANKROLL} (correcto para Fase 2)")
elif BANKROLL == 15.0:
    errors.append("BANKROLL sigue en $15 — actualizar .env o Railway")
    print(f"  ❌ BANKROLL=${BANKROLL} — sigue en $15! Debe ser $25")
else:
    warnings.append(f"BANKROLL=${BANKROLL} — verificar que es correcto")
    print(f"  ⚠ BANKROLL=${BANKROLL} — verificar")

# ============================================================
# TEST 1c: Funciones críticas existen
# ============================================================
print("\n[1c/13] Verificando funciones críticas...")
critical_missing = []
try:
    from bot import manage_positions
    print(f"  ✅ manage_positions() existe")
except ImportError:
    critical_missing.append("manage_positions")
    print(f"  ❌ manage_positions() NO existe")

try:
    from bot import track_trade, get_performance_summary
    print(f"  ✅ track_trade() + get_performance_summary() existen")
except ImportError:
    critical_missing.append("track_trade/get_performance_summary")
    print(f"  ❌ Performance tracker NO existe")

try:
    from bot import audit_check_sell_fills, audit_check_forecasts, audit_register_pending_sell
    print(f"  ✅ Audit functions existen (fills + forecasts)")
except ImportError:
    critical_missing.append("audit functions")
    print(f"  ❌ Audit functions NO existen")

try:
    from bot import get_effective_bankroll, get_current_exposure
    print(f"  ✅ get_effective_bankroll() + get_current_exposure() existen")
except ImportError:
    critical_missing.append("bankroll/exposure functions")
    print(f"  ❌ Bankroll/exposure functions NO existen")

try:
    from bot import parse_city_from_title
    print(f"  ✅ parse_city_from_title() existe")
except ImportError:
    critical_missing.append("parse_city_from_title")
    print(f"  ❌ parse_city_from_title() NO existe")

try:
    from py_clob_client.order_builder.constants import BUY, SELL
    print(f"  ✅ BUY y SELL importados")
except ImportError:
    critical_missing.append("BUY/SELL constants")
    print(f"  ❌ BUY/SELL NO importados")

if critical_missing:
    errors.append(f"Funciones críticas faltan: {', '.join(critical_missing)}")
else:
    passes.append("Todas las funciones críticas existen")

# ============================================================
# TEST 1d: Verificar que manage_positions tiene los 3 checks
# ============================================================
print("\n[1d/13] Verificando lógica de manage_positions...")
import inspect
try:
    source = inspect.getsource(manage_positions)
    has_stop_loss = "STOP_LOSS_PCT" in source
    has_take_profit = "TAKE_PROFIT_PCT" in source
    has_reeval = "RE-EVAL" in source or "re-eval" in source.lower() or "edge_pct < -3" in source
    has_forecast = "get_forecast" in source

    if has_stop_loss:
        print(f"  ✅ Check 1: Stop-loss (STOP_LOSS_PCT)")
    else:
        errors.append("manage_positions: falta stop-loss")
        print(f"  ❌ Check 1: Stop-loss NO encontrado")

    if has_take_profit:
        print(f"  ✅ Check 2: Take-profit (TAKE_PROFIT_PCT)")
    else:
        errors.append("manage_positions: falta take-profit")
        print(f"  ❌ Check 2: Take-profit NO encontrado")

    if has_reeval and has_forecast:
        print(f"  ✅ Check 3: Re-evaluación con previsión fresca")
    else:
        errors.append("manage_positions: falta re-evaluación")
        print(f"  ❌ Check 3: Re-evaluación NO encontrada")

    if has_stop_loss and has_take_profit and has_reeval:
        passes.append("manage_positions tiene los 3 checks")
except Exception as e:
    warnings.append(f"No pude inspeccionar manage_positions: {e}")
    print(f"  ⚠ No pude inspeccionar: {e}")

# ============================================================
# TEST 1e: Verificar fix bankroll Magic wallet
# ============================================================
print("\n[1e/13] Verificando fix bankroll (Magic wallet bug)...")
try:
    source_bankroll = inspect.getsource(get_effective_bankroll)
    has_fallback = "cash_balance < 0.01" in source_bankroll or "cash_balance == 0" in source_bankroll
    if has_fallback:
        passes.append("Fix bankroll Magic wallet OK (fallback a BANKROLL)")
        print(f"  ✅ Fallback cuando cash=0: usa BANKROLL=${BANKROLL}")
    else:
        errors.append("get_effective_bankroll NO tiene fallback para cash=0")
        print(f"  ❌ Sin fallback para cash=0 — repetirá el bug de hoy")
except Exception as e:
    warnings.append(f"No pude verificar bankroll fix: {e}")
    print(f"  ⚠ No pude verificar: {e}")

# ============================================================
# TEST 1f: Verificar filtro valor mínimo en ventas
# ============================================================
print("\n[1f/13] Verificando filtro valor mínimo en ventas...")
try:
    source_manage = inspect.getsource(manage_positions)
    has_min_filter = "estimated_return < 0.10" in source_manage or "< 0.10" in source_manage
    if has_min_filter:
        passes.append("Filtro valor mínimo $0.10 en ventas OK")
        print(f"  ✅ No intentará vender posiciones de <$0.10")
    else:
        errors.append("Sin filtro de valor mínimo — intentará vender posiciones de $0.01")
        print(f"  ❌ Sin filtro — repetirá el error 'not enough balance'")
except Exception as e:
    warnings.append(f"No pude verificar filtro mínimo: {e}")
    print(f"  ⚠ No pude verificar: {e}")

# ============================================================
# TEST 2: Sigma calibrada (v10)
# ============================================================
print("\n[2/13] Verificando sigma calibrada...")
sigma_0 = get_uncertainty(0)
sigma_1 = get_uncertainty(1)
sigma_2 = get_uncertainty(2)

if sigma_0 >= 1.0 and sigma_1 >= 1.2:
    passes.append(f"Sigma OK: día0={sigma_0}, día1={sigma_1}, día2={sigma_2}")
    print(f"  ✅ Sigma: día0={sigma_0}, día1={sigma_1}, día2={sigma_2}")
else:
    errors.append(f"Sigma demasiado baja: día0={sigma_0} (mín 1.0)")
    print(f"  ❌ Sigma demasiado baja: {sigma_0}")

# ============================================================
# TEST 3: Kelly sizing con $25 bankroll
# ============================================================
print("\n[3/13] Verificando sizing con $25 bankroll...")

# Caso típico: edge 15%, precio mercado 30¢
pos = calculate_position(25.0, 0.45, 0.30)
if pos is None:
    errors.append("Kelly no genera posición para edge típico (15%)")
    print("  ❌ No genera posición para edge 15%")
else:
    amt = pos["amount"]
    if amt >= MIN_BET and amt <= 25.0 * MAX_BET_PCT:
        passes.append(f"Kelly sizing OK: ${amt:.2f} para edge 15%")
        print(f"  ✅ Posición: ${amt:.2f} ({pos['shares']:.1f}sh @ ${pos['aggressive_price']:.2f})")
    else:
        errors.append(f"Kelly sizing fuera de rango: ${amt:.2f}")
        print(f"  ❌ Sizing: ${amt:.2f} (rango: ${MIN_BET}-${25*MAX_BET_PCT:.2f})")

# Caso edge pequeño (7%): debería generar posición con $25
pos_small = calculate_position(25.0, 0.20, 0.13)
if pos_small is not None and pos_small["amount"] >= MIN_BET:
    passes.append(f"Kelly edge 7% OK: ${pos_small['amount']:.2f}")
    print(f"  ✅ Edge 7%: ${pos_small['amount']:.2f} — SÍ genera posición")
else:
    warnings.append("Edge 7% no genera posición con $25 — puede ser normal")
    print(f"  ⚠ Edge 7% no genera posición (puede ser normal para edges bajos)")

# Caso con $2 bankroll (lo que pasaba antes): DEBERÍA fallar
pos_broke = calculate_position(2.0, 0.45, 0.30)
if pos_broke is None or pos_broke["amount"] < MIN_BET:
    passes.append("Con $2 bankroll no genera posición (correcto)")
    print(f"  ✅ Con $2 bankroll: no genera posición (correcto, bug fix confirmado)")
else:
    warnings.append(f"Con $2 bankroll genera ${pos_broke['amount']:.2f}")
    print(f"  ⚠ Con $2 bankroll genera ${pos_broke['amount']:.2f}")

# ============================================================
# TEST 4: Presupuesto y exposición
# ============================================================
print("\n[4/13] Verificando presupuesto...")
max_exposure = 25.0 * MAX_EXPOSURE_PCT
max_per_trade = 25.0 * MAX_BET_PCT
n_trades_possible = int(max_exposure / max_per_trade) if max_per_trade > 0 else 0

print(f"  Máx exposición: ${max_exposure:.2f} (40% de $25)")
print(f"  Máx por trade: ${max_per_trade:.2f} (10% de $25)")
print(f"  Trades simultáneos: ~{n_trades_possible}")

if max_exposure >= 5.0 and n_trades_possible >= 3:
    passes.append(f"Presupuesto OK: ${max_exposure:.2f} exposición, {n_trades_possible} trades")
    print(f"  ✅ Presupuesto correcto")
else:
    errors.append(f"Presupuesto insuficiente: ${max_exposure:.2f}")
    print(f"  ❌ Presupuesto insuficiente")

# ============================================================
# TEST 5: Parseo de mercados
# ============================================================
print("\n[5/13] Verificando parseo de mercados...")
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
        errors.append(f"Parseo falló: {q[:50]}")
        print(f"  ❌ Parseo falló: {q[:50]}")

if all_parsed:
    passes.append("Parseo de mercados OK (3/3)")

# ============================================================
# TEST 6: Probabilidades con sigma nueva
# ============================================================
print("\n[6/13] Verificando modelo de probabilidad...")

# London 16°C, forecast 15.7°C, día 1 → no debería ser 99%
prob = estimate_prob(15.7, 16.0, "exact", 1)
print(f"  London 16°C, forecast 15.7°C, día 1: P={prob*100:.1f}%")
if 15 < prob * 100 < 40:
    passes.append(f"Probabilidad razonable: {prob*100:.1f}%")
    print(f"  ✅ Razonable (no sobreconfiado)")
else:
    warnings.append(f"Probabilidad sospechosa: {prob*100:.1f}%")
    print(f"  ⚠ Revisar: {prob*100:.1f}%")

# NYC 60°F (15.6°C), forecast 10°C, día 0 → debería ser baja
prob2 = estimate_prob(10.0, 15.6, "exact", 0)
print(f"  NYC 60°F, forecast 10°C, día 0: P={prob2*100:.1f}%")
if prob2 * 100 < 5:
    passes.append(f"Probabilidad baja correcta: {prob2*100:.1f}%")
    print(f"  ✅ Correctamente baja")
else:
    warnings.append(f"Debería ser más baja: {prob2*100:.1f}%")
    print(f"  ⚠ Debería ser más baja")

# ============================================================
# TEST 7: Conectar a Polymarket API
# ============================================================
print("\n[7/13] Verificando conexión a Polymarket...")
try:
    import urllib.request
    req = urllib.request.Request("https://gamma-api.polymarket.com/events?tag_id=103040&limit=1")
    req.add_header("User-Agent", "verify/1.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    n_markets = sum(len(e.get("markets", [])) for e in data)
    passes.append(f"API Polymarket OK ({n_markets} mercados)")
    print(f"  ✅ API OK — {n_markets} mercados de temperatura")
except Exception as e:
    errors.append(f"API Polymarket falló: {e}")
    print(f"  ❌ Error: {e}")

# ============================================================
# TEST 8: Verificar cartera real
# ============================================================
print("\n[8/13] Verificando cartera real...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    import urllib.parse

    funder = os.getenv("FUNDER", "")
    if not funder:
        warnings.append("No hay FUNDER en .env")
        print("  ⚠ No hay FUNDER en .env — no puedo verificar cartera")
    else:
        params = urllib.parse.urlencode({
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "20",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        url = f"https://data-api.polymarket.com/positions?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "verify/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        positions = json.loads(resp.read())

        total_value = sum(float(p.get("currentValue", 0)) for p in positions)
        total_invested = sum(float(p.get("initialValue", 0)) for p in positions)
        temp_pos = [p for p in positions if "temperature" in p.get("title", "").lower()]

        print(f"  Posiciones totales: {len(positions)} ({len(temp_pos)} de temperatura)")
        print(f"  Invertido: ${total_invested:.2f} | Valor actual: ${total_value:.2f}")

        # Verificar exposición actual
        exposure_pct = (total_invested / 25.0 * 100) if total_invested > 0 else 0
        print(f"  Exposición actual: ${total_invested:.2f} ({exposure_pct:.0f}% de $25)")

        if exposure_pct <= 50:
            passes.append(f"Exposición OK: {exposure_pct:.0f}%")
            print(f"  ✅ Exposición dentro de límites")
        else:
            warnings.append(f"Exposición alta: {exposure_pct:.0f}%")
            print(f"  ⚠ Exposición alta: {exposure_pct:.0f}%")

        # Mostrar posiciones activas
        for p in temp_pos:
            title = p.get("title", "?")[:50]
            outcome = p.get("outcome", "?")
            pct = float(p.get("percentPnl", 0))
            val = float(p.get("currentValue", 0))
            icon = "🟢" if pct >= 0 else "🔴"
            print(f"    {icon} {outcome} ${val:.2f} ({pct:+.1f}%) | {title}")

except Exception as e:
    warnings.append(f"Error verificando cartera: {e}")
    print(f"  ⚠ Error: {e}")

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
    print(f"\n  ⛔ NO HACER PUSH — hay errores que corregir")
else:
    print(f"\n  🟢 TODO OK — puedes hacer push")
    print(f"\n  git add .")
    print(f"  git commit -m \"v10.1: fase 2 inicio verificado\"")
    print(f"  git push")

print()
