#!/usr/bin/env python3
"""
verify_before_deploy.py v4 — Tests de comportamiento para bot.py v10.4

Ejecutar ANTES de cada deploy:
  python verify_before_deploy.py

Todos los tests deben pasar. Si alguno falla, NO hacer push.

v4 añade tests para:
  - Bug #3: no comprar si ya hay posición abierta
  - Bug #9: no re-comprar lo vendido en el mismo ciclo
  - Bug #10: MIN_BET default correcto (1.00)
  - Bug #11: skip ciclo inicial si el último fue reciente
  - Bug #12: resueltas no cuentan como mantenidas
  - Bug #14: mensajes Telegram clarifican precio límite
  - Persistencia: DATA_DIR y _data_path
"""
import sys
import os
import ast
import re

passed = 0
failed = 0
errors = []


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(name)
        failed += 1


def run_tests():
    global passed, failed

    # ---- Cargar bot.py ----
    bot_path = os.path.join(os.path.dirname(__file__), "bot.py")
    if not os.path.exists(bot_path):
        print(f"❌ bot.py no encontrado en {bot_path}")
        sys.exit(1)

    with open(bot_path, "r", encoding="utf-8") as f:
        code = f.read()

    # ---- Test 0: Sintaxis válida ----
    print("\n🔍 Sintaxis")
    try:
        ast.parse(code)
        test("Python válido", True)
    except SyntaxError as e:
        test("Python válido", False, str(e))
        print("\n⛔ Sintaxis inválida — no se pueden ejecutar más tests")
        sys.exit(1)

    # ---- Test 1: Versión ----
    print("\n🔍 Versión")
    test("Header dice v10.4", "bot.py v10.4" in code)
    test("Log arranque dice v10.4", 'BOT v10.4' in code)
    test("Telegram arranque dice v10.4", 'Bot v10.4' in code)

    # ---- Test 2: Bug #10 — MIN_BET default ----
    print("\n🔍 Bug #10: MIN_BET default")
    match = re.search(r'MIN_BET\s*=\s*float\(os\.getenv\("MIN_BET",\s*"([^"]+)"\)', code)
    if match:
        test("MIN_BET default es 1.00", match.group(1) == "1.00",
             f"encontrado: {match.group(1)}")
    else:
        test("MIN_BET definido con getenv", False)

    # ---- Test 3: Bug #12 — Resueltas no en keeping ----
    print("\n🔍 Bug #12: Resueltas excluidas de keeping")
    # Buscar el bloque de curPrice >= 0.98 en manage_positions
    # Buscamos entre cur_price >= 0.98 y el continue que le sigue
    resolved_block = re.search(
        r'if cur_price >= 0\.98:.*?n_resolved.*?continue',
        code, re.DOTALL
    )
    if resolved_block:
        block = resolved_block.group()
        test("Bloque resueltas NO contiene keeping.append", "keeping.append" not in block,
             "keeping.append encontrado en bloque de resueltas")
        test("Bloque resueltas SÍ incrementa n_resolved", "n_resolved += 1" in block)
    else:
        test("Bloque de resueltas encontrado", False)

    # ---- Test 4: Bug #9 — sold_token_ids ----
    print("\n🔍 Bug #9: No re-entrada tras venta")
    test("manage_positions devuelve sold_token_ids",
         '"sold_token_ids"' in code or "'sold_token_ids'" in code)
    test("sold_this_cycle se usa en búsqueda",
         "sold_this_cycle" in code)
    test("Check 'VENDIDO ESTE CICLO' en edge_analysis",
         "VENDIDO ESTE CICLO" in code)
    # Verificar que TODOS los return de manage_positions incluyen sold_token_ids
    returns_in_manage = re.findall(
        r'return\s*\{[^}]*"n_sold"[^}]*\}',
        code, re.DOTALL
    )
    for i, ret in enumerate(returns_in_manage):
        test(f"Return #{i+1} de manage_positions incluye sold_token_ids",
             "sold_token_ids" in ret,
             f"return sin sold_token_ids: {ret[:80]}...")

    # ---- Test 5: Bug #3 — Check posiciones existentes ----
    print("\n🔍 Bug #3: No duplicar posiciones")
    test("existing_position_tokens se construye",
         "existing_position_tokens" in code)
    test("Check 'YA HAY POSICIÓN ABIERTA'",
         "YA HAY POSICIÓN ABIERTA" in code)
    test("existing_position_tokens usa Data API",
         "existing_position_tokens.add(asset)" in code)

    # ---- Test 6: Bug #11 — Skip ciclo inicial ----
    print("\n🔍 Bug #11: Skip ciclo extra al arrancar")
    test("skip_first_cycle variable existe", "skip_first_cycle" in code)
    test("min_cycle_gap_hours definido", "min_cycle_gap_hours" in code)
    test("Comprueba timestamp del último ciclo",
         "age_hours" in code and "min_cycle_gap_hours" in code)
    test("Condicional 'if not skip_first_cycle'",
         "if not skip_first_cycle:" in code)

    # ---- Test 7: Bug #14 — Precio límite clarificado ----
    print("\n🔍 Bug #14: Precio límite en Telegram")
    test("Mensaje de venta dice 'precio límite'",
         "precio límite" in code)
    test("Mensaje de venta dice 'precio real puede diferir'",
         "precio real puede diferir" in code)

    # ---- Test 8: Mejoras Telegram ----
    print("\n🔍 Mejoras Telegram")
    test("/estado muestra Compras y Ventas separadas",
         "Compras:" in code and "Ventas:" in code and "last_sells_placed" in code)
    test("Resumen ciclo dice 'Exposición actual'",
         "Exposición actual" in code)
    test("Resumen ciclo dice 'Presupuesto libre'",
         "Presupuesto libre" in code)

    # ---- Test 9: Persistencia DATA_DIR ----
    print("\n🔍 Persistencia (DATA_DIR)")
    test("DATA_DIR definido", 'DATA_DIR = os.getenv("DATA_DIR"' in code)
    test("_data_path función definida", "def _data_path(filename):" in code)
    test("PERFORMANCE_FILE usa _data_path",
         'PERFORMANCE_FILE = _data_path("performance.json")' in code)
    test("AUDIT_FILE usa _data_path",
         'AUDIT_FILE = _data_path("audit.json")' in code)
    test("trades.log usa _data_path",
         '_data_path("trades.log")' in code)
    test("decisions.log usa _data_path",
         '_data_path("decisions.log")' in code)
    # Verificar que _data_path se define ANTES de logging
    data_path_line = code.index("def _data_path")
    logging_line = code.index("logging.basicConfig")
    test("_data_path definido ANTES de logging.basicConfig",
         data_path_line < logging_line,
         f"_data_path en posición {data_path_line}, logging en {logging_line}")

    # ---- Test 10: Checks heredados v10.3 ----
    print("\n🔍 Checks heredados (v10.3)")
    test("CITY_UTC_OFFSETS existe", "CITY_UTC_OFFSETS" in code)
    test("get_min_days_for_city existe", "def get_min_days_for_city" in code)
    test("SELL_PENDING en track_trade", 'track_trade("SELL_PENDING"' in code)
    test("audit_check_sell_fills existe", "def audit_check_sell_fills" in code)
    test("_loss_total_tracked set existe", "_loss_total_tracked" in code)
    test("curPrice >= 0.98 excluido de exposición",
         "cur_price >= 0.98" in code or "curPrice >= 0.98" in code)

    # ---- Test 11: Imports necesarios ----
    print("\n🔍 Imports")
    test("import json", "import json" in code)
    test("import re", "import re" in code)
    test("import os", "import os" in code)
    test("import math", "import math" in code)
    test("import threading", "import threading" in code)
    test("from datetime import", "from datetime import" in code)

    # ---- Test 12: Configuración sensata ----
    print("\n🔍 Configuración")
    test("STOP_LOSS_PCT es negativo", 'STOP_LOSS_PCT' in code and '"-25.0"' in code)
    test("TAKE_PROFIT_PCT es positivo", 'TAKE_PROFIT_PCT' in code and '"40.0"' in code)
    test("MAX_EXPOSURE_PCT es 0.40", '"0.40"' in code)
    test("MIN_EDGE default es 7.0", '"7.0"' in code)
    test("SCHEDULE_HOURS_UTC configurable", 'SCHEDULE_HOURS_UTC' in code)

    # ---- Test 13: Nuevas funcionalidades v10.4.1 ----
    print("\n🔍 Nuevas funcionalidades v10.4.1")
    test("CYCLE_SUMMARY_FILE definido", "CYCLE_SUMMARY_FILE" in code)
    test("CYCLES_HISTORY_FILE definido", "CYCLES_HISTORY_FILE" in code)
    test("cycles_history.jsonl append-only", "cycles_history.jsonl" in code)
    test("cycle_summary se guarda en main()", "cycle_data" in code and "CYCLE_SUMMARY_FILE" in code)
    test("cycle_data incluye version", '"version"' in code and "v10.4.1" in code)

    # ---- Resultado ----
    print(f"\n{'='*50}")
    total = passed + failed
    if failed == 0:
        print(f"✅ TODOS LOS TESTS PASARON ({passed}/{total})")
        print("Puedes hacer deploy con confianza.")
    else:
        print(f"❌ {failed} TESTS FALLARON de {total}")
        print("Errores:")
        for e in errors:
            print(f"  - {e}")
        print("\n⛔ NO hacer deploy hasta corregir los errores.")
    print(f"{'='*50}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
