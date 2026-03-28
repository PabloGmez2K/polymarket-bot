#!/usr/bin/env python3
"""
verify_before_deploy.py v7 — Tests de comportamiento para bot.py v10.4.8

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
import json
import tempfile
from datetime import date, datetime, timezone

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

    trader_analyzer_path = os.path.join(os.path.dirname(__file__), "trader_analyzer.py")
    find_traders_path = os.path.join(os.path.dirname(__file__), "find_traders.py")
    trader_code = ""
    finder_code = ""
    if os.path.exists(trader_analyzer_path):
        with open(trader_analyzer_path, "r", encoding="utf-8") as f:
            trader_code = f.read()
    if os.path.exists(find_traders_path):
        with open(find_traders_path, "r", encoding="utf-8") as f:
            finder_code = f.read()

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
    test("Log arranque dice v10.4", 'POLYMARKET BOT {BOT_VERSION}' in code or 'BOT v10.4' in code)
    test("Telegram arranque dice v10.4", 'Bot {BOT_VERSION} arrancado' in code or 'Bot v10.4' in code)

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
    test("POSTMORTEM_FILE usa _data_path",
         'POSTMORTEM_FILE = _data_path("postmortem.json")' in code)
    test("ALERTS_FILE usa _data_path",
         'ALERTS_FILE = _data_path("alerts_state.json")' in code)
    test("SIGNALS_FILE usa _seed_data_file",
         'SIGNALS_FILE = _seed_data_file("signals.json")' in code)
    test("TRADERS_DB_FILE usa _seed_data_file",
         'TRADERS_DB_FILE = _seed_data_file("traders_db.json")' in code)
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
    test("trader_analyzer.py presente", bool(trader_code))
    test("find_traders.py presente", bool(finder_code))

    # ---- Test 12: Configuración sensata ----
    print("\n🔍 Configuración")
    test("STOP_LOSS_PCT es negativo", 'STOP_LOSS_PCT' in code and '"-25.0"' in code)
    test("TAKE_PROFIT_PCT es positivo", 'TAKE_PROFIT_PCT' in code and '"40.0"' in code)
    test("MAX_EXPOSURE_PCT es 0.40", '"0.40"' in code)
    test("MIN_EDGE default es 7.0", '"7.0"' in code)
    test("SCHEDULE_HOURS_UTC configurable", 'SCHEDULE_HOURS_UTC' in code)
    test("BLOCKED_CITIES default incluye London", 'os.getenv("BLOCKED_CITIES", "London")' in code)
    test("is_city_blocked definida", "def is_city_blocked(" in code)
    test("parse_market_date_iso definida", "def parse_market_date_iso(" in code)
    test("format_postmortem_label definida", "def format_postmortem_label(" in code)

    print("\n🔍 Trader data en Volume")
    try:
        if trader_code:
            ast.parse(trader_code)
            test("trader_analyzer.py sintaxis válida", True)
            test("trader_analyzer usa DATA_DIR", 'DATA_DIR = os.getenv("DATA_DIR", "")' in trader_code)
            test("trader_analyzer mueve traders_db al Volume", 'DB_FILE      = _seed_data_file("traders_db.json")' in trader_code)
            test("trader_analyzer mueve signals al Volume", 'SIGNALS_FILE = _seed_data_file("signals.json")' in trader_code)
            test("trader_analyzer mueve trader_history al Volume", 'HISTORY_FILE = _seed_data_file("trader_history.json")' in trader_code)
        if finder_code:
            ast.parse(finder_code)
            test("find_traders.py sintaxis válida", True)
            test("find_traders usa DATA_DIR", 'DATA_DIR = os.getenv("DATA_DIR", "")' in finder_code)
            test("find_traders mueve traders_db al Volume", 'DB_FILE = _seed_data_file("traders_db.json")' in finder_code)
    except SyntaxError as e:
        test("Scripts trader sintaxis válida", False, str(e))

    # ---- Test 13: Nuevas funcionalidades v10.4.1 ----
    print("\n🔍 Nuevas funcionalidades v10.4.1")
    test("CYCLE_SUMMARY_FILE definido", "CYCLE_SUMMARY_FILE" in code)
    test("CYCLES_HISTORY_FILE definido", "CYCLES_HISTORY_FILE" in code)
    test("cycles_history.jsonl append-only", "cycles_history.jsonl" in code)
    test("cycle_summary se guarda en main()", "cycle_data" in code and "CYCLE_SUMMARY_FILE" in code)
    test("cycle_data incluye version v10.4.8", '"version"' in code and "v10.4.8" in code)

    # ---- Test 14: Rediseño Telegram v10.4.2 ----
    print("\n🔍 Rediseño Telegram v10.4.2")
    test("send_telegram_paged definida", "def send_telegram_paged(" in code)
    test("_parse_position_label definida", "def _parse_position_label(" in code)
    test("_get_portfolio_and_positions definida", "def _get_portfolio_and_positions(" in code)
    test("cmd_info definida", "def cmd_info(" in code)
    test("cmd_postmortem definida", "def cmd_postmortem(" in code)
    test("/info en COMMANDS", '"info": cmd_info' in code)
    test("/postmortem en COMMANDS", '"postmortem": cmd_postmortem' in code)
    test("/info en MENU_KEYBOARD", '"callback_data": "info"' in code)
    test("/postmortem en MENU_KEYBOARD", '"callback_data": "postmortem"' in code)
    test("Bug #13: send_telegram_paged en cmd_log", "send_telegram_paged" in code and "cmd_log" in code)
    test("Bug #13: send_telegram_paged en cmd_cartera", "send_telegram_paged" in code)
    test("_parse_position_label usa centavos (¢)", "¢" in code)
    test("cmd_estado versión correcta", "Bot v10.4.8" in code or "v10.4.8" in code)

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
    test("Fix /detalle: toma el último ciclo completo del archivo",
         "lines[last_start:]" in code)
    test("Fix traders: filtra por ciudad+lado", "active_positions" in code and "outcome.lower()" in code)
    test("Fix traders: filtra por fecha exacta del mercado",
         "matching_dates" in code and "sig_date_iso not in matching_dates" in code)
    test("Fix traders: línea Scan/Análisis sin separador huérfano",
         "timing_bits = []" in code and "' | '.join(timing_bits)" in code)

    print("\n🔍 Bloqueo London")
    test("main filtra ciudades bloqueadas", "blocked_city_skip" in code and "Ciudades bloqueadas operativamente" in code)
    test("London se bloquea por helper", 'if is_city_blocked(city):' in code)

    # ---- Test 15: Integridad de COMMANDS (todos los botones siguen presentes) ----
    print("\n🔍 Integridad de COMMANDS")
    for cmd in ["estado", "cartera", "ordenes", "log", "logfull",
                "forzar", "modo", "traders", "rendimiento", "info", "postmortem",
                "confirmar_real", "confirmar_dry", "cancelar_modo"]:
        test(f'COMMANDS tiene "{cmd}"', f'"{cmd}"' in code)

    # ---- Test 16: send_telegram_paged en todos los comandos de respuesta larga ----
    print("\n🔍 send_telegram_paged en comandos relevantes")
    for cmd_name in ["cmd_cartera", "cmd_ordenes", "cmd_log", "cmd_logfull",
                     "cmd_traders", "cmd_rendimiento", "cmd_info", "cmd_postmortem"]:
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
        ns = {"re": re, "datetime": datetime, "timezone": timezone}
        exec(get_function_source(module_ast, code_lines, "parse_city_from_title"), ns)
        exec(get_function_source(module_ast, code_lines, "_parse_position_label"), ns)
        exec(get_function_source(module_ast, code_lines, "parse_market_date_iso"), ns)
        exec(get_function_source(module_ast, code_lines, "format_market_date_short"), ns)
        exec(get_function_source(module_ast, code_lines, "format_postmortem_label"), ns)
        helper_ns = {"BLOCKED_CITIES": {"london"}}
        exec(get_function_source(module_ast, code_lines, "is_city_blocked"), helper_ns)

        label_paris = ns["_parse_position_label"](
            "Will the temperature in Paris be 11°C on March 29?",
            "NO",
        )
        test("parse label: ciudad/temp/fecha/outcome",
             label_paris == "Paris 11°C Mar29 NO",
             f"obtenido: {label_paris}")
        test("parse market date: título largo a ISO",
             ns["parse_market_date_iso"]("Will the temperature in Paris be 11°C on March 29?") == "2026-03-29")
        test("postmortem label fallback: city+fecha+lado",
             ns["format_postmortem_label"]({"city": "Dallas", "date": "2026-03-28", "side": "YES"}) == "Dallas Mar28 YES")

        test("blocked city helper: London bloqueada",
             helper_ns["is_city_blocked"]("London") and helper_ns["is_city_blocked"]("london"))
        test("blocked city helper: Paris permitida",
             not helper_ns["is_city_blocked"]("Paris"))

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
        fd, tmp_cycle_summary = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_cycle_summary_test_",
            suffix=".json",
        )
        os.close(fd)
        with open(tmp_cycle_summary, "w", encoding="utf-8") as f:
            json.dump({
                "cycle_number": 1,
                "timestamp_utc": "2026-03-28T16:00:33.073674+00:00",
                "management": {"n_kept": 0, "n_sold": 1, "n_resolved": 0},
                "scan": {"markets_evaluated": 46, "selected": 2},
                "buys": [],
            }, f)
        info_ns = {
            "os": os,
            "json": __import__("json"),
            "datetime": datetime,
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: info_messages.append(text),
            "BOT_VERSION": "v10.4.8",
            "DRY_RUN": False,
            "BANKROLL": 25.0,
            "MIN_EDGE": 7.0,
            "STOP_LOSS_PCT": -25.0,
            "TAKE_PROFIT_PCT": 40.0,
            "MAX_EXPOSURE_PCT": 0.40,
            "MIN_BET": 1.0,
            "SCHEDULE_HOURS_UTC": [8, 16, 23],
            "bot_state": {"cycle_count": 12, "last_run": None},
            "CYCLE_SUMMARY_FILE": tmp_cycle_summary,
            "get_performance_summary": lambda: None,
        }
        exec(get_function_source(module_ast, code_lines, "cmd_info"), info_ns)
        info_ns["cmd_info"]()
        info_msg = info_messages[-1] if info_messages else ""
        test("info: versión visible correcta", "BOT POLYMARKET v10.4.8" in info_msg, info_msg[:120])
        test("info: usa cycle_summary como fallback de último", "Último: 2026-03-28 16:00 UTC" in info_msg, info_msg[:220])

        pm_messages = []
        pm_ns = {
            "load_postmortem_data": lambda: [
                {
                    "status": "closed",
                    "question": "Will the temperature in Dallas be 18°C on March 28?",
                    "city": "Dallas",
                    "side": "YES",
                    "close_action": "SELL",
                    "close_reason": "reeval",
                    "pnl_cash": 0.26,
                    "closed_at": "2026-03-28T16:00:10+00:00",
                },
                {
                    "status": "open",
                    "question": "",
                    "city": "Dallas",
                    "side": "YES",
                    "date": "2026-03-28",
                    "total_amount": 2.50,
                    "latest_edge_pct": 21.3,
                    "opened_at": "2026-03-28T11:02:42+00:00",
                },
            ],
            "format_postmortem_label": ns["format_postmortem_label"],
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: pm_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "cmd_postmortem"), pm_ns)
        pm_ns["cmd_postmortem"]()
        pm_msg = pm_messages[-1] if pm_messages else ""
        test("postmortem cmd: muestra resumen de estados", "Open:" in pm_msg and "Closed:" in pm_msg, pm_msg[:160])
        test("postmortem cmd: muestra últimos cierres", "reeval" in pm_msg and "$+0.26" in pm_msg, pm_msg[:200])
        test("postmortem cmd: fallback legacy evita '? YES'",
             "Dallas Mar28 YES" in pm_msg and "? YES" not in pm_msg,
             pm_msg[:220])

        fd, tmp_signals = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_signals_test_",
            suffix=".json",
        )
        os.close(fd)
        traders_messages = []
        traders_ns = {
            "os": os,
            "json": json,
            "date": date,
            "datetime": datetime,
            "timezone": timezone,
            "SIGNALS_FILE": tmp_signals,
            "_get_portfolio_and_positions": lambda: {
                "active": [{
                    "title": "Will the temperature in London be 11°C on March 29?",
                    "outcome": "NO",
                }]
            },
            "parse_city_from_title": ns["parse_city_from_title"],
            "parse_market_date_iso": ns["parse_market_date_iso"],
            "bot_state": {
                "last_trader_scan": None,
                "last_trader_analysis": datetime(2026, 3, 28, 19, 30, tzinfo=timezone.utc),
            },
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: traders_messages.append(text),
        }
        with open(tmp_signals, "w", encoding="utf-8") as f:
            json.dump({
                "generated": "2026-03-28T19:30:00+00:00",
                "n_actionable_signals": 2,
                "n_consensus_markets": 0,
                "n_traders_analyzed": 34,
                "n_quality_traders": 8,
                "quality_traders": [],
                "n_skipped_low_quality": 10,
                "signals": [
                    {"city": "London", "outcome": "No", "date": "2026-03-28", "avg_price": 0.43, "is_reference": False, "has_consensus": False},
                    {"city": "London", "outcome": "No", "date": "2026-03-29", "avg_price": 0.44, "is_reference": False, "has_consensus": False},
                ],
            }, f, ensure_ascii=False)
        exec(get_function_source(module_ast, code_lines, "cmd_traders"), traders_ns)
        traders_ns["cmd_traders"]()
        traders_msg = traders_messages[-1] if traders_messages else ""
        aligned_section = traders_msg.split("<b>Señales activas", 1)[0]
        test("traders: alinea solo fecha exacta de cartera",
             "London No 2026-03-29" in aligned_section and "London No 2026-03-28" not in aligned_section,
             aligned_section[:260])
        test("traders: análisis sin separador huérfano",
             "\n| Análisis:" not in traders_msg and "Análisis: 28/03 19:30 UTC" in traders_msg,
             traders_msg[:220])

        pm_empty_messages = []
        fd, tmp_perf_summary = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_postmortem_perf_test_",
            suffix=".json",
        )
        os.close(fd)
        pm_empty_ns = {
            "os": os,
            "json": json,
            "PERFORMANCE_FILE": tmp_perf_summary,
            "load_postmortem_data": lambda: [],
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: pm_empty_messages.append(text),
        }
        with open(tmp_perf_summary, "w", encoding="utf-8") as f:
            json.dump([{"action": "BUY"}], f)
        exec(get_function_source(module_ast, code_lines, "cmd_postmortem"), pm_empty_ns)
        pm_empty_ns["cmd_postmortem"]()
        pm_empty_msg = pm_empty_messages[-1] if pm_empty_messages else ""
        test("postmortem vacío: explica falta de backfill histórico",
             "performance.json" in pm_empty_msg and "todavía no se ha rellenado" in pm_empty_msg,
             pm_empty_msg[:220])
        if os.path.exists(tmp_cycle_summary):
            try:
                os.remove(tmp_cycle_summary)
            except PermissionError:
                pass
        if os.path.exists(tmp_signals):
            try:
                os.remove(tmp_signals)
            except PermissionError:
                pass
        if os.path.exists(tmp_perf_summary):
            try:
                os.remove(tmp_perf_summary)
            except PermissionError:
                pass
    except Exception as e:
        test("Tests funcionales ejecutan sin excepción", False, str(e))

    # ---- Test 20: postmortem.json ----
    print("\n🔍 Postmortem")
    test("POSTMORTEM_FILE definido", "POSTMORTEM_FILE" in code)
    test("load_postmortem_data definida", "def load_postmortem_data(" in code)
    test("save_postmortem_data definida", "def save_postmortem_data(" in code)
    test("update_postmortem definida", "def update_postmortem(" in code)
    test("track_trade sincroniza postmortem", "update_postmortem(action, entry)" in code)
    test("SELL/SELL_FAILED sincronizan postmortem desde performance",
         'update_postmortem(entry.get("action", ""), entry)' in code)
    test("manage_positions marca RESOLVED_WIN en postmortem", 'update_postmortem("RESOLVED_WIN"' in code)
    test("BUY guarda question/token_id para postmortem",
         'question=trade["question"]' in code and 'token_id=trade["token_id"]' in code)

    try:
        fd, tmp_postmortem = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_postmortem_test_",
            suffix=".json",
        )
        os.close(fd)
        if os.path.exists(tmp_postmortem):
            try:
                os.remove(tmp_postmortem)
            except PermissionError:
                pass

        pm_ns = {
            "os": os,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "POSTMORTEM_FILE": tmp_postmortem,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        for fn_name in [
            "load_postmortem_data",
            "save_postmortem_data",
            "_find_open_postmortem",
            "update_postmortem",
        ]:
            exec(get_function_source(module_ast, code_lines, fn_name), pm_ns)

        buy_entry = {
            "timestamp": "2026-03-28T08:00:00+00:00",
            "bot_version": "v10.4.8",
            "city": "Dallas",
            "side": "YES",
            "date": "2026-03-28",
            "question": "Will the temperature in Dallas be 18°C on March 28?",
            "token_id": "tok-dallas-yes",
            "condition": "exact",
            "amount": 2.50,
            "shares": 10.0,
            "price": 0.25,
            "edge_pct": 18.0,
            "forecast_max": 18.2,
            "our_prob": 48.0,
            "mkt_price": 21.0,
            "trader_confirmed": ["Trader A"],
        }
        buy_entry_2 = dict(buy_entry)
        buy_entry_2["timestamp"] = "2026-03-28T09:00:00+00:00"
        buy_entry_2["amount"] = 1.25
        buy_entry_2["shares"] = 5.0
        buy_entry_2["price"] = 0.25

        sell_pending = {
            "timestamp": "2026-03-28T16:00:00+00:00",
            "bot_version": "v10.4.8",
            "city": "Dallas",
            "side": "Yes",
            "date": "2026-03-28",
            "question": "Will the temperature in Dallas be 18°C on March 28?",
            "token_id": "tok-dallas-yes",
            "reason": "reeval",
            "price": 0.30,
            "shares": 15.0,
            "return_est": 4.50,
            "pnl_pct": 20.0,
            "pnl_cash": 0.75,
            "order_id": "oid-1",
        }
        sell_filled = dict(sell_pending)
        sell_filled["fill_confirmed"] = "2026-03-28T16:00:10+00:00"

        pm_ns["update_postmortem"]("BUY", buy_entry)
        pm_ns["update_postmortem"]("BUY", buy_entry_2)
        pm_ns["update_postmortem"]("SELL_PENDING", sell_pending)
        pm_ns["update_postmortem"]("SELL", sell_filled)

        records = pm_ns["load_postmortem_data"]()
        rec = records[-1] if records else {}

        test("postmortem funcional: un registro agregado", len(records) == 1, f"registros: {len(records)}")
        test("postmortem funcional: buy_count agregado", rec.get("buy_count") == 2, str(rec))
        test("postmortem funcional: total_amount agregado", abs(rec.get("total_amount", 0) - 3.75) < 0.001, str(rec))
        test("postmortem funcional: cierre SELL", rec.get("status") == "closed" and rec.get("close_action") == "SELL", str(rec))
        test("postmortem funcional: reason y order_id preservados",
             rec.get("close_reason") == "reeval" and rec.get("order_id") == "oid-1", str(rec))

        if os.path.exists(tmp_postmortem):
            try:
                os.remove(tmp_postmortem)
            except OSError:
                pass
    except Exception as e:
        test("Postmortem funcional ejecuta sin excepción", False, str(e))

    # ---- Test 21: alertas de observabilidad ----
    print("\n🔍 Alertas de observabilidad")
    test("ALERTS_FILE definido", "ALERTS_FILE" in code)
    test("load_alerts_state definida", "def load_alerts_state(" in code)
    test("save_alerts_state definida", "def save_alerts_state(" in code)
    test("backfill_postmortem_from_performance definida", "def backfill_postmortem_from_performance(" in code)
    test("inspect_signals_file_health definida", "def inspect_signals_file_health(" in code)
    test("get_clean_closed_trade_stats definida", "def get_clean_closed_trade_stats(" in code)
    test("run_observability_alerts definida", "def run_observability_alerts(" in code)
    test("arranque hace backfill de postmortem", "backfill_postmortem_from_performance()" in code)
    test("alertas se evalúan en startup y fin de ciclo", code.count("run_observability_alerts()") >= 2)

    try:
        fd, tmp_perf = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_perf_backfill_test_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_pm = tempfile.mkstemp(
            dir=os.path.dirname(__file__),
            prefix="_tmp_pm_backfill_test_",
            suffix=".json",
        )
        os.close(fd)
        if os.path.exists(tmp_pm):
            try:
                os.remove(tmp_pm)
            except PermissionError:
                pass

        with open(tmp_perf, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "timestamp": "2026-03-28T08:00:00+00:00",
                    "action": "BUY",
                    "city": "Dallas",
                    "side": "YES",
                    "date": "2026-03-28",
                    "question": "Will the temperature in Dallas be 18°C on March 28?",
                    "token_id": "tok-dallas",
                    "amount": 2.5,
                    "shares": 10.0,
                    "price": 0.25,
                    "edge_pct": 18.0,
                    "forecast_max": 18.2,
                    "our_prob": 48.0,
                    "mkt_price": 21.0,
                    "trader_confirmed": [],
                },
                {
                    "timestamp": "2026-03-28T16:00:00+00:00",
                    "fill_confirmed": "2026-03-28T16:00:10+00:00",
                    "action": "SELL",
                    "city": "Dallas",
                    "side": "YES",
                    "date": "2026-03-28",
                    "question": "Will the temperature in Dallas be 18°C on March 28?",
                    "token_id": "tok-dallas",
                    "reason": "reeval",
                    "price": 0.30,
                    "shares": 10.0,
                    "return_est": 3.0,
                    "pnl_cash": 0.5,
                    "pnl_pct": 20.0,
                    "order_id": "oid-backfill",
                },
            ], f, ensure_ascii=False)

        backfill_ns = {
            "os": os,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "PERFORMANCE_FILE": tmp_perf,
            "POSTMORTEM_FILE": tmp_pm,
            "log": types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None),
        }
        for fn_name in [
            "load_performance_history",
            "load_postmortem_data",
            "save_postmortem_data",
            "_find_open_postmortem",
            "update_postmortem",
            "backfill_postmortem_from_performance",
        ]:
            exec(get_function_source(module_ast, code_lines, fn_name), backfill_ns)

        rebuilt = backfill_ns["backfill_postmortem_from_performance"]()
        rebuilt_records = backfill_ns["load_postmortem_data"]()
        rebuilt_rec = rebuilt_records[-1] if rebuilt_records else {}
        test("backfill postmortem: reconstruye registros", rebuilt >= 1 and len(rebuilt_records) == 1, str(rebuilt_records))
        test("backfill postmortem: deja cierre SELL", rebuilt_rec.get("status") == "closed" and rebuilt_rec.get("close_action") == "SELL", str(rebuilt_rec))
        test("backfill postmortem: preserva order_id", rebuilt_rec.get("order_id") == "oid-backfill", str(rebuilt_rec))

        for tmp_file in [tmp_perf, tmp_pm]:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except PermissionError:
                    pass

        review_messages = []
        saved_review_state = {}
        review_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.4",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.4",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
            },
            "save_alerts_state": lambda state: saved_review_state.update(state),
            "get_clean_closed_trade_stats": lambda: {"count": 30, "sell": 20, "loss_total": 6, "resolved_win": 4},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 12},
            "load_audit_data": lambda: {"pending_sells": []},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: review_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), review_ns)
        review_ns["run_observability_alerts"]()
        review_msg = review_messages[-1] if review_messages else ""
        test("alerta review trigger: se envía al llegar a 30 trades", "Review Trigger" in review_msg and "30 trades limpios" in review_msg, review_msg[:220])
        test("alerta review trigger: guarda milestone", "clean_trades_30" in saved_review_state.get("milestones", {}), str(saved_review_state))

        signal_messages = []
        signal_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.4",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.4",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
            },
            "save_alerts_state": lambda state: None,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "stale", "age_hours": 30.5, "actionable": 3},
            "load_audit_data": lambda: {"pending_sells": []},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: signal_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), signal_ns)
        signal_ns["run_observability_alerts"]()
        signal_msg = signal_messages[-1] if signal_messages else ""
        test("alerta signals stale: se envía", "signals.json está expirado" in signal_msg, signal_msg[:220])

        pending_messages = []
        saved_pending_state = {}
        pending_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.4",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.4",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
            },
            "save_alerts_state": lambda state: saved_pending_state.update(state),
            "get_clean_closed_trade_stats": lambda: {"count": 2, "sell": 2, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "load_audit_data": lambda: {
                "pending_sells": [{
                    "order_id": "oid-stuck",
                    "city": "Dallas",
                    "side": "YES",
                    "price": 0.31,
                    "timestamp": "2026-03-27T00:00:00+00:00",
                }]
            },
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: pending_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), pending_ns)
        pending_ns["run_observability_alerts"]()
        pending_msg = pending_messages[-1] if pending_messages else ""
        test("alerta pending_exit atascada: se envía", "Ventas pendientes atascadas" in pending_msg and "Dallas YES" in pending_msg, pending_msg[:220])
        test("alerta pending_exit atascada: guarda order_id notificado",
             "oid-stuck" in saved_pending_state.get("pending_exit_notified", {}),
             str(saved_pending_state))
    except Exception as e:
        test("Alertas funcionales ejecutan sin excepción", False, str(e))

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
