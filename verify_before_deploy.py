#!/usr/bin/env python3
"""
verify_before_deploy.py v9 — Tests de comportamiento para bot.py v10.5.6

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
import base64
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
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    dashboard_template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    dashboard_css_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.css")
    agent_events_path = os.path.join(os.path.dirname(__file__), "agent_events.jsonl")
    trader_code = ""
    finder_code = ""
    requirements_code = ""
    dashboard_template_code = ""
    dashboard_css_code = ""
    agent_event_rows = []
    if os.path.exists(trader_analyzer_path):
        with open(trader_analyzer_path, "r", encoding="utf-8") as f:
            trader_code = f.read()
    if os.path.exists(find_traders_path):
        with open(find_traders_path, "r", encoding="utf-8") as f:
            finder_code = f.read()
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            requirements_code = f.read()
    if os.path.exists(dashboard_template_path):
        with open(dashboard_template_path, "r", encoding="utf-8") as f:
            dashboard_template_code = f.read()
    if os.path.exists(dashboard_css_path):
        with open(dashboard_css_path, "r", encoding="utf-8") as f:
            dashboard_css_code = f.read()
    if os.path.exists(agent_events_path):
        try:
            with open(agent_events_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line:
                        agent_event_rows.append(json.loads(line))
        except Exception:
            agent_event_rows = []

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
    test("Header dice v10.5", "bot.py v10.5" in code)
    test("Log arranque dice v10.5", 'POLYMARKET BOT {BOT_VERSION}' in code or 'BOT v10.5' in code)
    test("Telegram arranque dice v10.5", 'Bot {BOT_VERSION} arrancado' in code or 'Bot v10.5' in code)

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

    print("\n🔍 Dashboard web")
    test("DASHBOARD_ENABLED definido", "DASHBOARD_ENABLED" in code)
    test("DASHBOARD_PORT definido", "DASHBOARD_PORT" in code and 'os.getenv("PORT"' in code)
    test("BANKROLL_LEVELS definido", "BANKROLL_LEVELS" in code)
    test("AGENT_EVENTS_FILE usa _seed_data_file", 'AGENT_EVENTS_FILE = _seed_data_file("agent_events.jsonl")' in code)
    test("load_agent_events definida", "def load_agent_events(" in code)
    test("_normalize_agent_event_stage definida", "def _normalize_agent_event_stage(" in code)
    test("compute_agent_scorecard definida", "def compute_agent_scorecard(" in code)
    test("get_logic_series_clean_closed_trade_stats definida", "def get_logic_series_clean_closed_trade_stats(" in code)
    test("build_promotion_checklist definida", "def build_promotion_checklist(" in code)
    test("build_dashboard_snapshot definida", "def build_dashboard_snapshot(" in code)
    test("create_dashboard_app definida", "def create_dashboard_app(" in code)
    test("start_dashboard_server definida", "def start_dashboard_server(" in code)
    test("dashboard arranca en __main__", "start_dashboard_server()" in code)
    test("requirements incluye Flask", "Flask==" in requirements_code)
    test("requirements incluye waitress", "waitress==" in requirements_code)
    test("template dashboard existe", os.path.exists(dashboard_template_path))
    test("css dashboard existe", os.path.exists(dashboard_css_path))
    test("agent_events.jsonl existe", os.path.exists(agent_events_path))
    test("template dashboard usa cycle.series_display", "cycle.series_display" in dashboard_template_code)
    test("template dashboard muestra stages de eventos", "event.stage_label" in dashboard_template_code and "Prop." in dashboard_template_code)
    test("css dashboard en modo oscuro", "--bg: #071018;" in dashboard_css_code and "--card: rgba(12, 20, 29, 0.9);" in dashboard_css_code)
    if os.path.exists(agent_events_path):
        try:
            with open(agent_events_path, "r", encoding="utf-8") as f:
                events_count = sum(1 for line in f if line.strip())
            test("agent_events.jsonl tiene eventos semilla", events_count >= 5, f"eventos={events_count}")
            test("agent_events.jsonl explicita stage en eventos", bool(agent_event_rows) and all(row.get("stage") for row in agent_event_rows))
        except Exception as e:
            test("agent_events.jsonl legible", False, str(e))

    # ---- Test 13: Nuevas funcionalidades v10.4.1 ----
    print("\n🔍 Nuevas funcionalidades v10.4.1")
    test("CYCLE_SUMMARY_FILE definido", "CYCLE_SUMMARY_FILE" in code)
    test("CYCLES_HISTORY_FILE definido", "CYCLES_HISTORY_FILE" in code)
    test("cycles_history.jsonl append-only", "cycles_history.jsonl" in code)
    test("cycle_summary se guarda en main()", "cycle_data" in code and "CYCLE_SUMMARY_FILE" in code)
    test("cycle_data incluye version v10.5.6", '"version"' in code and "v10.5.6" in code)
    test("cycle_data incluye logic_series", '"logic_series": LOGIC_SERIES' in code)
    test("cycle_data incluye logic_cycle_number", '"logic_cycle_number"' in code)

    # ---- Test 14: Rediseño Telegram v10.4.2 ----
    print("\n🔍 Rediseño Telegram v10.4.2")
    test("send_telegram_paged definida", "def send_telegram_paged(" in code)
    test("_parse_position_label definida", "def _parse_position_label(" in code)
    test("_get_portfolio_and_positions definida", "def _get_portfolio_and_positions(" in code)
    test("cmd_info definida", "def cmd_info(" in code)
    test("cmd_postmortem definida", "def cmd_postmortem(" in code)
    test("cmd_accuracy definida", "def cmd_accuracy(" in code)
    test("/info en COMMANDS", '"info": cmd_info' in code)
    test("/postmortem en COMMANDS", '"postmortem": cmd_postmortem' in code)
    test("/accuracy en COMMANDS", '"accuracy": cmd_accuracy' in code)
    test("/info en MENU_KEYBOARD", '"callback_data": "info"' in code)
    test("/postmortem en MENU_KEYBOARD", '"callback_data": "postmortem"' in code)
    test("/accuracy en MENU_KEYBOARD", '"callback_data": "accuracy"' in code)
    test("Bug #13: send_telegram_paged en cmd_log", "send_telegram_paged" in code and "cmd_log" in code)
    test("Bug #13: send_telegram_paged en cmd_cartera", "send_telegram_paged" in code)
    test("_parse_position_label usa centavos (¢)", "¢" in code)
    test("cmd_estado versión correcta", "Bot v10.5.6" in code or "v10.5.6" in code)

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
    test("Ciclos por serie: _load_cycle_counts definida",
         "def _load_cycle_counts(" in code)
    test("Ciclos persistentes: se cargan total y serie al arrancar",
         "_load_cycle_counts()" in code and 'bot_state["cycle_count_series"]' in code)
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
    test("cmd_estado muestra Intra-SL", "🛡 Intra-SL:" in code or "Intra-SL:" in code)
    test("cmd_estado muestra total y serie", "serie v{LOGIC_SERIES}" in code and "total |" in code)

    print("\n🔍 Bloqueo London")
    test("main filtra ciudades bloqueadas", "blocked_city_skip" in code and "Ciudades bloqueadas operativamente" in code)
    test("London se bloquea por helper", 'if is_city_blocked(city):' in code)

    # ---- Test 15: Integridad de COMMANDS (todos los botones siguen presentes) ----
    print("\n🔍 Integridad de COMMANDS")
    for cmd in ["estado", "cartera", "ordenes", "log", "logfull",
                "forzar", "modo", "traders", "rendimiento", "info", "postmortem", "accuracy",
                "confirmar_real", "confirmar_dry", "cancelar_modo"]:
        test(f'COMMANDS tiene "{cmd}"', f'"{cmd}"' in code)

    # ---- Test 16: send_telegram_paged en todos los comandos de respuesta larga ----
    print("\n🔍 send_telegram_paged en comandos relevantes")
    for cmd_name in ["cmd_cartera", "cmd_ordenes", "cmd_log", "cmd_logfull",
                     "cmd_traders", "cmd_rendimiento", "cmd_info", "cmd_postmortem", "cmd_accuracy"]:
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
        test("cmd_info muestra cycle_count_series", "cycle_count_series" in info_body)
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

        fd, tmp_cycles = tempfile.mkstemp(
            dir=tempfile.gettempdir(),
            prefix="_tmp_cycles_history_test_",
            suffix=".jsonl",
        )
        os.close(fd)
        with open(tmp_cycles, "w", encoding="utf-8") as f:
            f.write(json.dumps({"version": "v10.4.8", "cycle_number": 1}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"version": "v10.5.1", "cycle_number": 2}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"logic_series": "10.5", "version": "v10.5.3", "cycle_number": 3}, ensure_ascii=False) + "\n")
        cycle_ns = {
            "os": os,
            "json": json,
            "re": re,
            "LOGIC_SERIES": "10.5",
            "CYCLES_HISTORY_FILE": tmp_cycles,
        }
        exec(get_function_source(module_ast, code_lines, "_extract_logic_series"), cycle_ns)
        exec(get_function_source(module_ast, code_lines, "_load_cycle_counts"), cycle_ns)
        total_count, series_count = cycle_ns["_load_cycle_counts"]()
        test("cycle_counts: total histórico correcto", total_count == 3, f"got {total_count}")
        test("cycle_counts: serie lógica correcta", series_count == 2, f"got {series_count}")
        if os.path.exists(tmp_cycles):
            try:
                os.remove(tmp_cycles)
            except PermissionError:
                pass

        dashboard_ns = {
            "BANKROLL": 25.0,
            "BANKROLL_LEVELS": [25.0, 35.0, 50.0],
        }
        exec(get_function_source(module_ast, code_lines, "get_bankroll_level_context"), dashboard_ns)
        level_ctx = dashboard_ns["get_bankroll_level_context"]()
        test("dashboard: nivel actual bankroll correcto", level_ctx["current_level"] == 1, level_ctx)
        test("dashboard: siguiente bankroll correcto", level_ctx["next_target"] == 35.0, level_ctx)

        auth_ns = {
            "base64": base64,
            "DASHBOARD_USER": "admin",
            "DASHBOARD_PASSWORD": "secret",
        }
        exec(get_function_source(module_ast, code_lines, "_dashboard_auth_ok"), auth_ns)
        good_auth = "Basic " + base64.b64encode(b"admin:secret").decode("ascii")
        bad_auth = "Basic " + base64.b64encode(b"admin:wrong").decode("ascii")
        test("dashboard auth: credenciales válidas", auth_ns["_dashboard_auth_ok"](types.SimpleNamespace(headers={"Authorization": good_auth})))
        test("dashboard auth: credenciales inválidas", not auth_ns["_dashboard_auth_ok"](types.SimpleNamespace(headers={"Authorization": bad_auth})))

        score_ns = {}
        exec(get_function_source(module_ast, code_lines, "_normalize_agent_event_stage"), score_ns)
        exec(get_function_source(module_ast, code_lines, "compute_agent_scorecard"), score_ns)
        sample_scores = score_ns["compute_agent_scorecard"]([
            {"agent": "Codex", "type": "bug_detected", "stage": "proposed", "points": 1, "validated": False, "impact": "high", "timestamp": "2026-03-29T10:00:00+00:00", "target_agent": "Claude Code (Opus)"},
            {"agent": "Codex", "type": "fix_implemented", "stage": "validated", "points": 4, "validated": True, "impact": "high", "timestamp": "2026-03-29T11:00:00+00:00"},
            {"agent": "Claude Code (Opus)", "type": "feature_shipped", "stage": "implemented", "points": 5, "validated": False, "impact": "critical", "timestamp": "2026-03-29T09:00:00+00:00"},
        ])
        test("scorecard: ordena por puntos", sample_scores[0]["agent"] == "Codex", sample_scores)
        test("scorecard: cuenta bugs detectados", sample_scores[0]["bugs_detected"] == 1, sample_scores[0])
        test("scorecard: cuenta etapas propuestas", sample_scores[0]["proposed"] == 1, sample_scores[0])
        test("scorecard: cuenta etapas validadas", sample_scores[0]["validated"] == 1, sample_scores[0])
        test("scorecard: cuenta etapas implementadas", sample_scores[1]["implemented"] == 1, sample_scores[1])
        test("scorecard: cuenta correcciones a otro agente", sample_scores[0]["corrections"] == 1, sample_scores[0])

        checklist_ns = {
            "LOGIC_SERIES": "10.5",
            "REVIEW_READY_CLEAN_TRADES": 30,
            "PROMOTION_MIN_SERIES_CYCLES": 10,
            "PROMOTION_MIN_SERIES_WIN_RATE": 40.0,
            "PROMOTION_MIN_SERIES_PNL": 0.0,
            "DRAWDOWN_WINDOW": 5,
            "DRAWDOWN_THRESHOLD": -3.0,
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "get_bankroll_level_context": lambda: {"current_level": 1, "current_target": 25.0, "next_target": 35.0, "is_max_level": False},
            "get_clean_closed_trade_stats": lambda: {"count": 32, "sell": 20, "loss_total": 8, "resolved_win": 4},
            "get_logic_series_clean_closed_trade_stats": lambda: {"count": 30, "sell": 18, "loss_total": 8, "resolved_win": 4},
            "get_logic_series_stats": lambda: {"pnl": 1.5, "win_rate": 50.0, "closed_count": 12, "recent_window_size": 5, "recent_drawdown": -1.2},
            "get_dashboard_alert_summary": lambda: {"signals": {"status": "ok"}, "pending_stuck": [], "flagged_cities": []},
            "_load_cycle_counts": lambda: (18, 12),
        }
        exec(get_function_source(module_ast, code_lines, "build_promotion_checklist"), checklist_ns)
        checklist = checklist_ns["build_promotion_checklist"]()
        test("checklist: decision READY cuando todo pasa", checklist["decision"] == "READY", checklist)
        test("checklist: progreso 100 cuando todo pasa", checklist["progress_pct"] == 100.0, checklist)
        test("checklist: separa histórico y serie", any(item["label"] == "Trades limpios históricos" for item in checklist["checks"]) and any(item["label"] == "Trades limpios serie v10.5" for item in checklist["checks"]))
        test("checklist: histórico no bloquea promoción", any(item["label"] == "Trades limpios históricos" and not item["blocking"] for item in checklist["checks"]))

        fd, tmp_agent_events = tempfile.mkstemp(
            dir=tempfile.gettempdir(),
            prefix="_tmp_agent_events_test_",
            suffix=".jsonl",
        )
        os.close(fd)
        with open(tmp_agent_events, "w", encoding="utf-8") as f:
            f.write(json.dumps({"agent": "Codex", "points": 3, "timestamp": "2026-03-29T12:00:00+00:00"}) + "\n")
            f.write(json.dumps({"agent": "Claude Code (Opus)", "points": 5, "timestamp": "2026-03-29T11:00:00+00:00"}) + "\n")
        events_ns = {
            "os": os,
            "json": json,
            "AGENT_EVENTS_FILE": tmp_agent_events,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        exec(get_function_source(module_ast, code_lines, "load_agent_events"), events_ns)
        loaded_events = events_ns["load_agent_events"]()
        test("load_agent_events: lee dos eventos", len(loaded_events) == 2, loaded_events)
        test("load_agent_events: ordena por timestamp desc", loaded_events[0]["agent"] == "Codex", loaded_events)
        if os.path.exists(tmp_agent_events):
            try:
                os.remove(tmp_agent_events)
            except PermissionError:
                pass

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
            dir=tempfile.gettempdir(),
            prefix="_tmp_cycle_summary_test_",
            suffix=".json",
        )
        os.close(fd)
        with open(tmp_cycle_summary, "w", encoding="utf-8") as f:
            json.dump({
                "version": "v10.5.6",
                "cycle_number": 12,
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
            "BOT_VERSION": "v10.5.6",
            "LOGIC_SERIES": "10.5",
            "_extract_logic_series": cycle_ns["_extract_logic_series"],
            "DRY_RUN": False,
            "BANKROLL": 25.0,
            "MIN_EDGE": 7.0,
            "MIN_EDGE_EXACT": 15.0,
            "STOP_LOSS_PCT": -25.0,
            "TAKE_PROFIT_PCT": 40.0,
            "MAX_EXPOSURE_PCT": 0.40,
            "MIN_BET": 1.0,
            "INTRA_SL_INTERVAL": 90,
            "SCHEDULE_HOURS_UTC": [8, 16, 23],
            "bot_state": {"cycle_count": 12, "cycle_count_series": 3, "last_run": None},
            "CYCLE_SUMMARY_FILE": tmp_cycle_summary,
            "get_performance_summary": lambda: None,
        }
        exec(get_function_source(module_ast, code_lines, "cmd_info"), info_ns)
        info_ns["cmd_info"]()
        info_msg = info_messages[-1] if info_messages else ""
        test("info: versión visible correcta", "BOT POLYMARKET v10.5.6" in info_msg, info_msg[:120])
        test("info: usa cycle_summary como fallback de último", "Último: 2026-03-28 16:00 UTC" in info_msg, info_msg[:220])
        test("info: muestra doble contador", "Ciclos completados: 12 total | 3 serie v10.5" in info_msg, info_msg[:240])
        test("info: muestra ciclo total y de serie", "Ciclo total #12 | serie v10.5 #3" in info_msg, info_msg[:260])
        if os.path.exists(tmp_cycle_summary):
            try:
                os.remove(tmp_cycle_summary)
            except PermissionError:
                pass

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
            dir=tempfile.gettempdir(),
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
            dir=tempfile.gettempdir(),
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
            dir=tempfile.gettempdir(),
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
            "bot_version": "v10.5.3",
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
            "bot_version": "v10.5.3",
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
            dir=tempfile.gettempdir(),
            prefix="_tmp_perf_backfill_test_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_pm = tempfile.mkstemp(
            dir=tempfile.gettempdir(),
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
            "LOGIC_SERIES": "10.5",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5,
            "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100],
            "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15,
            "WIN_RATE_LOW": 30.0,
            "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.5",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False,
                "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False,
                "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
            },
            "save_alerts_state": lambda state: saved_review_state.update(state),
            "get_city_accuracy": lambda: {},
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 30, "sell": 20, "loss_total": 6, "resolved_win": 4},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 12},
            "load_audit_data": lambda: {"pending_sells": []},
            "_get_recent_closed_trades": lambda n=None: [],
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
            "LOGIC_SERIES": "10.5",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.5",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False, "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False, "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
            },
            "save_alerts_state": lambda state: None,
            "get_city_accuracy": lambda: {},
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "stale", "age_hours": 30.5, "actionable": 3},
            "load_audit_data": lambda: {"pending_sells": []},
            "_get_recent_closed_trades": lambda n=None: [],
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
            "LOGIC_SERIES": "10.5",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.5",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False, "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False, "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
            },
            "save_alerts_state": lambda state: saved_pending_state.update(state),
            "get_city_accuracy": lambda: {},
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 2, "sell": 2, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "_get_recent_closed_trades": lambda n=None: [],
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

    # ---- Test v10.5.0: Sigma widening ----
    print("\n🔍 v10.5.0: Sigma widening")
    try:
        sigma_ns = {"math": __import__("math")}
        exec(get_function_source(module_ast, code_lines, "get_uncertainty"), sigma_ns)
        gu = sigma_ns["get_uncertainty"]
        test("sigma day 0 = 2.0", gu(0) == 2.0, f"got {gu(0)}")
        test("sigma day 1 = 2.5", gu(1) == 2.5, f"got {gu(1)}")
        test("sigma day 2 = 3.0", gu(2) == 3.0, f"got {gu(2)}")
        test("sigma day 3 = 3.5", gu(3) == 3.5, f"got {gu(3)}")
        test("sigma day 4 = 4.0", gu(4) == 4.0, f"got {gu(4)}")
        test("sigma day 5 = 4.0", gu(5) == 4.0, f"got {gu(5)}")
        test("sigma day 6+ = 4.5", gu(7) == 4.5, f"got {gu(7)}")
    except Exception as e:
        test("sigma funcional ejecuta sin excepción", False, str(e))

    # ---- Test v10.5.0: Exact bet edge filter ----
    print("\n🔍 v10.5.0: Exact edge filter")
    test("MIN_EDGE_EXACT definido", "MIN_EDGE_EXACT" in code)
    match_exact = re.search(r'MIN_EDGE_EXACT\s*=\s*float\(os\.getenv\("MIN_EDGE_EXACT",\s*"([^"]+)"\)', code)
    test("MIN_EDGE_EXACT default es 15.0", match_exact and match_exact.group(1) == "15.0")
    test("effective_min_edge se calcula", "effective_min_edge" in code)
    test("Edge check usa condition == exact", 'c["condition"] == "exact"' in code)
    test("MIN_EDGE_EXACT en cmd_estado", "MIN_EDGE_EXACT" in code and "exact:" in code)
    test("LOGIC_SERIES es 10.5", 'LOGIC_SERIES = "10.5"' in code)

    # ---- Test v10.5.0: Smart alerts ----
    print("\n🔍 v10.5.0: Smart alerts")
    test("DRAWDOWN_WINDOW definido", "DRAWDOWN_WINDOW" in code)
    test("DRAWDOWN_THRESHOLD definido", "DRAWDOWN_THRESHOLD" in code)
    test("SCALING_TIERS definido", "SCALING_TIERS" in code)
    test("SCALING_WINDOW definido", "SCALING_WINDOW" in code)
    test("WIN_RATE_WINDOW definido", "WIN_RATE_WINDOW" in code)
    test("WIN_RATE_LOW definido", "WIN_RATE_LOW" in code)
    test("WIN_RATE_HIGH definido", "WIN_RATE_HIGH" in code)
    test("_get_recent_closed_trades definida", "def _get_recent_closed_trades(" in code)
    test("drawdown_alerted en alerts default", "drawdown_alerted" in code)
    test("scaling_alerted_tier en alerts default", "scaling_alerted_tier" in code)
    test("win_rate_low_alerted en alerts default", "win_rate_low_alerted" in code)
    test("win_rate_high_alerted en alerts default", "win_rate_high_alerted" in code)
    test("Drawdown Alert en run_observability", "Drawdown Alert" in code)
    test("Scaling Readiness en run_observability", "Scaling Readiness" in code)
    test("Scaling Warning en run_observability", "Scaling Warning" in code)
    test("Strategy Review en run_observability", "Strategy Review" in code)
    test("Strategy Signal en run_observability", "Strategy Signal" in code)

    # ---- Test v10.5.0: _get_recent_closed_trades funcional ----
    print("\n🔍 v10.5.0: _get_recent_closed_trades funcional")
    try:
        grc_ns = {}
        exec(get_function_source(module_ast, code_lines, "load_postmortem_data"), grc_ns)
        exec(get_function_source(module_ast, code_lines, "_get_recent_closed_trades"), grc_ns)

        mock_pm_file = os.path.join(tempfile.gettempdir(), "test_pm_recent.json")
        mock_records = [
            {"status": "closed", "close_action": "SELL", "pnl_cash": -1.5, "closed_at": "2026-03-28T10:00:00"},
            {"status": "closed", "close_action": "LOSS_TOTAL", "pnl_cash": -2.0, "closed_at": "2026-03-28T08:00:00"},
            {"status": "closed", "close_action": "SELL", "pnl_cash": 3.0, "closed_at": "2026-03-28T12:00:00"},
            {"status": "open", "close_action": None, "pnl_cash": None, "closed_at": None},
            {"status": "closed", "close_action": "RESOLVED_WIN", "pnl_cash": 1.0, "closed_at": "2026-03-28T14:00:00"},
        ]
        with open(mock_pm_file, "w") as f:
            json.dump(mock_records, f)

        grc_ns["POSTMORTEM_FILE"] = mock_pm_file
        grc_ns["os"] = os
        grc_ns["json"] = json
        grc_ns["log"] = type("L", (), {"warning": lambda *a: None})()

        result = grc_ns["_get_recent_closed_trades"](3)
        test("recent_closed: devuelve 3 de 4 cerrados", len(result) == 3, f"got {len(result)}")
        test("recent_closed: más reciente primero", result[0]["pnl_cash"] == 1.0, f"first pnl={result[0].get('pnl_cash')}")
        test("recent_closed: excluye open", all(r["status"] == "closed" for r in result))

        result_all = grc_ns["_get_recent_closed_trades"]()
        test("recent_closed sin N: devuelve todos", len(result_all) == 4)

        os.remove(mock_pm_file)
    except Exception as e:
        test("_get_recent_closed_trades funcional ejecuta", False, str(e))

    # ---- Test v10.5.1: Intra-cycle SL monitor ----
    print("\n🔍 v10.5.1: Intra-cycle SL monitor")
    test("INTRA_SL_INTERVAL definido", "INTRA_SL_INTERVAL" in code)
    test("INTRA_SL_INTERVAL default 90", '"INTRA_SL_INTERVAL", "90"' in code or "INTRA_SL_INTERVAL, 90" in code)
    test("sell_lock definido", "sell_lock" in code and "threading.Lock()" in code)
    test("intra_cycle_sl_check definida", "def intra_cycle_sl_check(" in code)
    test("intra_sl_loop definida", "def intra_sl_loop(" in code)
    test("reason stop_loss_intra", '"stop_loss_intra"' in code)
    test("reason take_profit_intra", '"take_profit_intra"' in code)
    test("sell_lock protege manage_positions", "with sell_lock:" in code)
    test("startup incluye Intra-SL", "Intra-SL" in code)
    test("IntraSL thread en __main__", 'name="IntraSL"' in code)

    # ---- Test v10.5.2: City accuracy tracker ----
    print("\n🔍 v10.5.2: City accuracy tracker")
    test("CITY_MIN_TRADES_FOR_BLOCK definido", "CITY_MIN_TRADES_FOR_BLOCK" in code)
    test("CITY_BLOCK_WIN_RATE definido", "CITY_BLOCK_WIN_RATE" in code)
    test("get_city_accuracy definida", "def get_city_accuracy(" in code)
    test("cmd_accuracy definida", "def cmd_accuracy(" in code)
    test("city_accuracy_flagged en alerts default", '"city_accuracy_flagged"' in code)
    test("/accuracy en COMMANDS", '"accuracy": cmd_accuracy' in code)
    test("/accuracy en MENU_KEYBOARD", '"callback_data": "accuracy"' in code)
    test("cmd_accuracy vuelve con menú", 'send_telegram("Sin datos de accuracy todavía.", with_menu=True)' in code and 'send_telegram_paged("\\n".join(lines), with_menu=True)' in code)
    test("Win rate en rendimiento", "WR:" in code)
    test("Version v10.5.6", "v10.5.6" in code)

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
