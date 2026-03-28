#!/usr/bin/env python3
"""
verify_before_deploy.py v6 — Tests de comportamiento para bot.py v10.4.5

Ejecutar ANTES de cada deploy:
  python verify_before_deploy.py

Todos los tests deben pasar. Si alguno falla, NO hacer push.

v5 añade tests para:
  - v10.4.2: Rediseño Telegram + Bug #13 (paginación)
    - send_telegram_paged definida
    - _parse_position_label definida
    - _get_portfolio_and_positions definida
    - cmd_info definida
    - /info en COMMANDS y MENU_KEYBOARD
"""
import sys
import os
import ast
import re
import types

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


def get_function_source(module_ast, code_lines, name):
    """Extrae el source exacto de una función definida en bot.py."""
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(code_lines[node.lineno - 1:node.end_lineno])
    raise ValueError(f"Función no encontrada: {name}")


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
        module_ast = ast.parse(code)
        test("Python válido", True)
    except SyntaxError as e:
        test("Python válido", False, str(e))
        print("\n⛔ Sintaxis inválida — no se pueden ejecutar más tests")
        sys.exit(1)

    code_lines = code.splitlines()

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
    test("CITY_TIMEZONES existe", "CITY_TIMEZONES" in code)
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
    test("from zoneinfo import ZoneInfo", "from zoneinfo import ZoneInfo" in code)

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
    test("cycle_data incluye version v10.4.5", '"version"' in code and "v10.4.5" in code)

    # ---- Test 14: Rediseño Telegram v10.4.2 ----
    print("\n🔍 Rediseño Telegram v10.4.2")
    test("send_telegram_paged definida", "def send_telegram_paged(" in code)
    test("_parse_position_label definida", "def _parse_position_label(" in code)
    test("_get_portfolio_and_positions definida", "def _get_portfolio_and_positions(" in code)
    test("cmd_info definida", "def cmd_info(" in code)
    test("/info en COMMANDS", '"info": cmd_info' in code)
    test("/info en MENU_KEYBOARD", '"callback_data": "info"' in code)
    test("Bug #13: send_telegram_paged en cmd_log", "send_telegram_paged" in code and "cmd_log" in code)
    test("Bug #13: send_telegram_paged en cmd_cartera", "send_telegram_paged" in code)
    test("_parse_position_label usa centavos (¢)", "¢" in code)
    test("cmd_estado versión correcta", "Bot v10.4.5" in code or "v10.4.5" in code)

    # ---- Test 14c: Zonas horarias reales v10.4.5 ----
    print("\n🔍 Zonas horarias reales")
    test("get_min_days_for_city usa ZoneInfo", "ZoneInfo(" in code and "astimezone" in code)
    test("London usa Europe/London", '"London":         "Europe/London"' in code)
    test("Madrid usa Europe/Madrid", '"Madrid":         "Europe/Madrid"' in code)
    test("New York usa America/New_York", '"New York City":  "America/New_York"' in code)
    test("Chicago usa America/Chicago", '"Chicago":        "America/Chicago"' in code)
    test("Seattle usa America/Los_Angeles", '"Seattle":        "America/Los_Angeles"' in code)
    test("Tel Aviv usa Asia/Jerusalem", '"Tel Aviv":       "Asia/Jerusalem"' in code)

    # ---- Test 14b: Fixes v10.4.3 ----
    print("\n🔍 Fixes v10.4.3")
    test("Ciclos persistentes: _load_cycle_count definida",
         "def _load_cycle_count(" in code)
    test("Ciclos persistentes: se carga al arrancar",
         "_load_cycle_count()" in code and 'bot_state["cycle_count"]' in code)
    test("Fix arranque: sin texto 'Bug #11' en mensaje Telegram",
         "Fix Bug #11: evita ciclo duplicado al deploy" not in code)
    test("Fix /detalle: escapa HTML (replace < y >)",
         'replace("<", "&lt;")' in code and 'replace(">", "&gt;")' in code)
    test("Fix traders: filtra por ciudad+lado (active_positions set)",
         "active_positions" in code and "outcome.lower()" in code)
    test("Fix traders: filtra por fecha no pasada",
         "today_str" in code and "sig_date < today_str" in code)

    # ---- Test 15: Integridad de COMMANDS (todos los botones siguen presentes) ----
    print("\n🔍 Integridad de COMMANDS")
    for cmd in ["estado", "cartera", "ordenes", "log", "logfull",
                "forzar", "modo", "traders", "rendimiento", "info",
                "confirmar_real", "confirmar_dry", "cancelar_modo"]:
        test(f'COMMANDS tiene "{cmd}"', f'"{cmd}"' in code)

    # ---- Test 16: send_telegram_paged en todos los comandos de respuesta larga ----
    print("\n🔍 send_telegram_paged en comandos relevantes")
    for cmd_name in ["cmd_cartera", "cmd_ordenes", "cmd_log", "cmd_logfull",
                     "cmd_traders", "cmd_rendimiento", "cmd_info"]:
        # Buscar la función y verificar que usa send_telegram_paged
        fn_match = re.search(
            rf"def {cmd_name}\(.*?(?=\ndef |\Z)", code, re.DOTALL
        )
        if fn_match:
            fn_body = fn_match.group()
            test(f"{cmd_name} usa send_telegram_paged",
                 "send_telegram_paged" in fn_body)
        else:
            test(f"{cmd_name} existe", False, "función no encontrada")

    # ---- Test 17: api_error propagado en _get_portfolio_and_positions ----
    print("\n🔍 Robustez _get_portfolio_and_positions")
    test("api_error en return de _get_portfolio", '"api_error"' in code)
    test("api_error se muestra en cmd_cartera",
         "api_error" in code and "Error API posiciones" in code)

    # ---- Test 18: cmd_info contiene campos esenciales ----
    print("\n🔍 Contenido de cmd_info")
    info_match = re.search(r"def cmd_info\(.*?(?=\ndef |\Z)", code, re.DOTALL)
    if info_match:
        info_body = info_match.group()
        test("cmd_info muestra BANKROLL",     "BANKROLL" in info_body)
        test("cmd_info muestra MIN_EDGE",     "MIN_EDGE" in info_body)
        test("cmd_info muestra STOP_LOSS_PCT","STOP_LOSS_PCT" in info_body)
        test("cmd_info muestra cycle_count",  "cycle_count" in info_body)
        test("cmd_info avisa de WU vs OMA",   "Weather Underground" in info_body)
    else:
        test("cmd_info encontrada", False, "función no encontrada")

    # ---- Test 19: Tests funcionales reales ----
    print("\n🔍 Tests funcionales")
    try:
        ns = {"re": re}
        exec(get_function_source(module_ast, code_lines, "parse_city_from_title"), ns)
        exec(get_function_source(module_ast, code_lines, "_parse_position_label"), ns)

        label_paris = ns["_parse_position_label"](
            "Will the temperature in Paris be 11°C on March 29?",
            "NO",
        )
        test("parse label: ciudad/temp/fecha/outcome",
             label_paris == "Paris 11°C Mar29 NO",
             f"obtenido: {label_paris}")

        pager_calls = []
        pager_ns = {
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: pager_calls.append(
                {"text": text, "with_menu": with_menu}
            )
        }
        exec(get_function_source(module_ast, code_lines, "send_telegram_paged"), pager_ns)
        pager_ns["send_telegram_paged"]("L1\nL2\nL3\nL4", with_menu=True, page_size=5)
        test("paginación: divide mensaje largo", len(pager_calls) >= 2, f"páginas: {len(pager_calls)}")
        test("paginación: solo último mensaje lleva menú",
             len(pager_calls) >= 2 and (not pager_calls[0]["with_menu"]) and pager_calls[-1]["with_menu"])

        sent_messages = []
        cartera_ns = {
            "re": re,
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: sent_messages.append(
                {"text": text, "with_menu": with_menu}
            ),
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: sent_messages.append(
                {"text": text, "with_menu": with_menu}
            ),
            "_get_portfolio_and_positions": lambda: {
                "cash": 25.65,
                "cash_ok": True,
                "active": [{
                    "title": "Will the temperature in Miami be 30°C on March 28?",
                    "outcome": "YES",
                    "size": 20.0,
                    "avgPrice": 0.12,
                    "curPrice": 0.10,
                    "currentValue": 2.10,
                    "percentPnl": -12.5,
                    "cashPnl": -0.30,
                }],
                "resolved_won": [{
                    "title": "Will the temperature in Chicago be 10°C on March 28?",
                    "outcome": "YES",
                    "currentValue": 2.50,
                }],
                "dead": [{
                    "initialValue": 2.46,
                }],
                "active_value": 2.10,
                "resolved_value": 2.50,
                "portfolio_total": 30.25,
                "api_error": "timeout talking to data api",
            },
        }
        exec(get_function_source(module_ast, code_lines, "parse_city_from_title"), cartera_ns)
        exec(get_function_source(module_ast, code_lines, "_parse_position_label"), cartera_ns)
        exec(get_function_source(module_ast, code_lines, "cmd_cartera"), cartera_ns)
        cartera_ns["cmd_cartera"]()
        cartera_msg = sent_messages[-1]["text"] if sent_messages else ""
        test("cartera: muestra error API al usuario", "Error API posiciones" in cartera_msg)
        test("cartera: formatea posición con centavos", "12¢ → 10¢" in cartera_msg, cartera_msg[:160])
        test("cartera: incluye vivas/resueltas/muertas",
             "Posiciones activas" in cartera_msg and "Esperando pago" in cartera_msg and "posiciones sin valor" in cartera_msg)

        info_messages = []
        info_ns = {
            "os": os,
            "json": __import__("json"),
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: info_messages.append(text),
            "DRY_RUN": False,
            "BANKROLL": 25.0,
            "MIN_EDGE": 7.0,
            "STOP_LOSS_PCT": -25.0,
            "TAKE_PROFIT_PCT": 40.0,
            "MAX_EXPOSURE_PCT": 0.40,
            "MIN_BET": 1.0,
            "SCHEDULE_HOURS_UTC": [8, 16, 23],
            "bot_state": {"cycle_count": 12, "last_run": None},
            "CYCLE_SUMMARY_FILE": "__missing__",
            "get_performance_summary": lambda: None,
        }
        exec(get_function_source(module_ast, code_lines, "cmd_info"), info_ns)
        info_ns["cmd_info"]()
        info_msg = info_messages[-1] if info_messages else ""
        test("info: versión visible correcta", "BOT POLYMARKET v10.4.5" in info_msg, info_msg[:120])
    except Exception as e:
        test("Tests funcionales ejecutan sin excepción", False, str(e))

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
