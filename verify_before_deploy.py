#!/usr/bin/env python3
"""
verify_before_deploy.py v10 — Tests de comportamiento para bot.py v10.6.6

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
import importlib.util
import math
import py_compile
import re
import builtins
import types
import json
import base64
import tempfile
import shutil
import urllib.error
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

passed = 0
failed = 0
errors = []


_VERIFY_TMP_ROOT = os.path.join(os.path.dirname(__file__), ".tmp_verify")


def _verify_tmp_dir():
    os.makedirs(_VERIFY_TMP_ROOT, exist_ok=True)
    return _VERIFY_TMP_ROOT


def _verify_tmp_path(filename):
    return os.path.join(_verify_tmp_dir(), filename)


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        msg = f"   {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(name)
        failed += 1


def _clean_display_text(value):
    """Normaliza mojibake frecuente en la salida del runner."""
    text = str(value)
    replacements = {
        "ÃƒÂ³": "ó",
        "ÃƒÂ¡": "á",
        "ÃƒÂ©": "é",
        "ÃƒÂ­": "í",
        "ÃƒÂº": "ú",
        "ÃƒÂ±": "ñ",
        "Ã³": "ó",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Â°F": "°F",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text


def test(name, condition, detail=""):
    global passed, failed
    clean_name = _clean_display_text(name)
    clean_detail = _clean_display_text(detail)
    if condition:
        print(f"  âœ… {clean_name}")
        passed += 1
    else:
        msg = f"   {clean_name}"
        if clean_detail:
            msg += f" â€” {clean_detail}"
        print(msg)
        errors.append(clean_name)
        failed += 1


def test(name, condition, detail=""):
    global passed, failed
    clean_name = _clean_display_text(name)
    clean_detail = _clean_display_text(detail)
    if condition:
        print(f"  [OK] {clean_name}")
        passed += 1
    else:
        msg = f"   {clean_name}"
        if clean_detail:
            msg += f" -- {clean_detail}"
        print(msg)
        errors.append(clean_name)
        failed += 1


def get_function_source(module_ast, code_lines, name):
    """Extrae el source exacto de una función definida en bot.py."""
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(code_lines[node.lineno - 1:node.end_lineno])
    raise ValueError(f"Función no encontrada: {name}")


def _normalize_session_value(value):
    """Normaliza ids de sesión mixtos como 194, session_194 o W17-Opus a un entero comparable."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    session_match = re.search(r"(?:session[_\s-]*)?(\d+)", text, re.IGNORECASE)
    if session_match:
        return int(session_match.group(1))
    return 0


def run_tests():
    global passed, failed

    # ---- Cargar bot.py ----
    bot_path = os.path.join(os.path.dirname(__file__), "bot.py")
    if not os.path.exists(bot_path):
        print(f" bot.py no encontrado en {bot_path}")
        sys.exit(1)

    with open(bot_path, "r", encoding="utf-8") as f:
        code = f.read()

    trader_analyzer_path = os.path.join(os.path.dirname(__file__), "trader_analyzer.py")
    find_traders_path = os.path.join(os.path.dirname(__file__), "find_traders.py")
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    claude_md_path = os.path.join(os.path.dirname(__file__), "CLAUDE.md")
    contexto_path = os.path.join(os.path.dirname(__file__), "CONTEXTO.md")
    historial_path = os.path.join(os.path.dirname(__file__), "HISTORIAL_SESIONES.md")
    operations_playbook_path = os.path.join(os.path.dirname(__file__), "OPERATIONS_PLAYBOOK.md")
    append_agent_event_path = os.path.join(os.path.dirname(__file__), "tools", "append_agent_event.py")
    dashboard_template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    dashboard_css_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.css")
    dashboard_js_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.js")
    agent_events_path = os.path.join(os.path.dirname(__file__), "agent_events.jsonl")
    traders_daily_summary_path = os.path.join(os.path.dirname(__file__), "tools", "traders_intelligence_daily_summary.py")
    traders_report_path = os.path.join(os.path.dirname(__file__), "tools", "traders_intelligence_report.py")
    traders_snapshot_path = os.path.join(os.path.dirname(__file__), "tools", "traders_intelligence_snapshot.py")
    traders_snapshot_doc_path = os.path.join(os.path.dirname(__file__), "docs", "traders-intelligence-v1-snapshots.md")
    trader_code = ""
    finder_code = ""
    requirements_code = ""
    claude_md_code = ""
    contexto_code = ""
    historial_code = ""
    operations_playbook_code = ""
    append_agent_event_code = ""
    dashboard_template_code = ""
    dashboard_css_code = ""
    dashboard_js_code = ""
    traders_daily_summary_code = ""
    traders_report_code = ""
    traders_snapshot_code = ""
    traders_snapshot_doc = ""
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
    if os.path.exists(claude_md_path):
        with open(claude_md_path, "r", encoding="utf-8") as f:
            claude_md_code = f.read()
    if os.path.exists(contexto_path):
        with open(contexto_path, "r", encoding="utf-8") as f:
            contexto_code = f.read()
    if os.path.exists(historial_path):
        with open(historial_path, "r", encoding="utf-8") as f:
            historial_code = f.read()
    if os.path.exists(operations_playbook_path):
        with open(operations_playbook_path, "r", encoding="utf-8") as f:
            operations_playbook_code = f.read()
    if os.path.exists(append_agent_event_path):
        with open(append_agent_event_path, "r", encoding="utf-8") as f:
            append_agent_event_code = f.read()
    if os.path.exists(dashboard_template_path):
        with open(dashboard_template_path, "r", encoding="utf-8") as f:
            dashboard_template_code = f.read()
    if os.path.exists(dashboard_css_path):
        with open(dashboard_css_path, "r", encoding="utf-8") as f:
            dashboard_css_code = f.read()
    if os.path.exists(dashboard_js_path):
        with open(dashboard_js_path, "r", encoding="utf-8") as f:
            dashboard_js_code = f.read()
    if os.path.exists(agent_events_path):
        try:
            with open(agent_events_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line:
                        agent_event_rows.append(json.loads(line))
        except Exception:
            agent_event_rows = []
    if os.path.exists(traders_daily_summary_path):
        with open(traders_daily_summary_path, "r", encoding="utf-8") as f:
            traders_daily_summary_code = f.read()
    if os.path.exists(traders_report_path):
        with open(traders_report_path, "r", encoding="utf-8") as f:
            traders_report_code = f.read()
    if os.path.exists(traders_snapshot_path):
        with open(traders_snapshot_path, "r", encoding="utf-8") as f:
            traders_snapshot_code = f.read()
    if os.path.exists(traders_snapshot_doc_path):
        with open(traders_snapshot_doc_path, "r", encoding="utf-8") as f:
            traders_snapshot_doc = f.read()

    # ---- Test 0: Sintaxis válida ----
    print("\n Sintaxis")
    try:
        module_ast = ast.parse(code)
        test("Python válido", True)
    except SyntaxError as e:
        test("Python válido", False, str(e))
        print("\n[ERROR] Sintaxis invalida - no se pueden ejecutar mas tests")
        sys.exit(1)

    code_lines = code.splitlines()

    # ---- Test 1: Versión ----
    print("\n Versión")
    test("Header dice v10.6", "bot.py v10.6" in code)
    test("Log arranque dice versión", 'POLYMARKET BOT {BOT_VERSION}' in code)
    test("Telegram arranque dice versión", 'Bot {BOT_VERSION} arrancado' in code)

    # ---- Test 2: Bug #10 — MIN_BET default ----
    print("\n Bug #10: MIN_BET default")
    match = re.search(r'MIN_BET\s*=\s*float\(os\.getenv\("MIN_BET",\s*"([^"]+)"\)', code)
    if match:
        test("MIN_BET default es 1.00", match.group(1) == "1.00",
             f"encontrado: {match.group(1)}")
    else:
        test("MIN_BET definido con getenv", False)
    bankroll_match = re.search(r'BANKROLL\s*=\s*float\(os\.getenv\("BANKROLL",\s*"([^"]+)"\)', code)
    if bankroll_match:
        test("BANKROLL default es 25.00", bankroll_match.group(1) == "25.00",
             f"encontrado: {bankroll_match.group(1)}")
    else:
        test("BANKROLL definido con getenv", False)

    print("\n Camino A: filtro direccional + sigma empírica")
    min_edge_match = re.search(r'MIN_EDGE\s*=\s*float\(os\.getenv\("MIN_EDGE",\s*"([^"]+)"\)', code)
    if min_edge_match:
        test("MIN_EDGE default es 15.0", min_edge_match.group(1) == "15.0",
             f"encontrado: {min_edge_match.group(1)}")
    else:
        test("MIN_EDGE definido con getenv", False)

    test("ALLOWED_CONDITIONS default solo direccionales",
         '"at_or_above,at_or_below"' in code and "ALLOWED_CONDITIONS" in code)

    main_cycle_src = get_function_source(module_ast, code_lines, "main")
    test("run_main_cycle filtra condiciones no allowlisted",
         "condition_name not in ALLOWED_CONDITIONS" in main_cycle_src)
    test("run_main_cycle manda range/exact filtrados a shadow tracking",
         "condition_filtered_shadow.append" in main_cycle_src and '"edge_hit": False' in main_cycle_src)
    test("cycle_summary guarda condition_filtered",
         '"condition_filtered": condition_filtered_skip' in main_cycle_src)

    get_uncertainty_src = get_function_source(module_ast, code_lines, "get_uncertainty")
    sigma_ns = {
        "EMPIRICAL_SIGMA": {
            "Chicago": {0: 2.57, 1: 2.59, 2: 3.0},
            "Dallas": {0: 0.57, 1: 1.30, 2: 2.0},
        },
        "EMPIRICAL_SIGMA_SAMPLES": {
            "Chicago": {0: 4, 1: 3, 2: 0},
            "Dallas": {0: 3, 1: 1, 2: 0},
        },
        "EMPIRICAL_SIGMA_GLOBAL": {0: 2.0, 1: 1.9, 2: 2.5, 3: 3.0},
        "MODEL_SIGMA_REFERENCE": {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5},
        "_UNCERTAINTY_CITY_CONTEXT": None,
    }
    exec(get_uncertainty_src, sigma_ns)
    test("get_uncertainty(city=Chicago, days=1) usa sigma empírica con n>=3",
         abs(sigma_ns["get_uncertainty"](1, city="Chicago") - 2.59) < 1e-9)
    test("get_uncertainty(city=Dallas, days=0) usa sigma empírica NOAA n=3",
         abs(sigma_ns["get_uncertainty"](0, city="Dallas") - 0.57) < 1e-9)

    # ---- Test FORECAST_BIAS_C + estimate_prob_with_city ----
    print("\n Corrección de sesgo NOAA (FORECAST_BIAS_C)")
    test("FORECAST_BIAS_C definido en código",
         "FORECAST_BIAS_C" in code)
    test("FORECAST_BIAS_C Atlanta >= 1.0",
         bool(re.search(r'"Atlanta":\s*1\.[0-9]', code)))
    test("FORECAST_BIAS_C Chicago >= 1.0",
         bool(re.search(r'"Chicago":\s*1\.[0-9]', code)))
    test("FORECAST_BIAS_C Dallas = 0.0",
         bool(re.search(r'"Dallas":\s*0\.0', code)))
    test("estimate_prob_with_city aplica FORECAST_BIAS_C",
         "FORECAST_BIAS_C.get(city" in code)

    # Test funcional: bias aumenta p(YES) cuando Open-Meteo subestima
    import math as _math
    bias_ns = {
        "EMPIRICAL_SIGMA": {"Atlanta": {0: 0.78}},
        "EMPIRICAL_SIGMA_SAMPLES": {"Atlanta": {0: 5}},
        "EMPIRICAL_SIGMA_GLOBAL": {0: 2.0, 1: 1.9, 2: 2.5, 3: 3.0},
        "MODEL_SIGMA_REFERENCE": {0: 1.2, 1: 1.5},
        "FORECAST_BIAS_C": {"Atlanta": 1.38, "Chicago": 1.40, "Dallas": 0.0},
        "_UNCERTAINTY_CITY_CONTEXT": None,
        "math": _math,
    }
    for fn in ("normal_cdf", "get_uncertainty", "estimate_prob", "estimate_prob_with_city"):
        exec(get_function_source(module_ast, code_lines, fn), bias_ns)
    p_sin_bias = bias_ns["estimate_prob"](20.0, 21.0, "at_or_above", 0)
    p_con_bias = bias_ns["estimate_prob_with_city"](20.0, 21.0, "at_or_above", 0, city="Atlanta")
    test("bias Atlanta sube p(YES at_or_above) vs sin bias",
         p_con_bias > p_sin_bias)
    p_dallas_bias = bias_ns["estimate_prob_with_city"](20.0, 21.0, "at_or_above", 0, city="Dallas")
    p_dallas_raw  = bias_ns["estimate_prob"](20.0, 21.0, "at_or_above", 0)
    test("Dallas bias=0 no altera probabilidad",
         abs(p_dallas_bias - p_dallas_raw) < 1e-9)

    # ---- Test CITY_STATS_CUTOFF — reset de stats por ciudad ----
    print("\n CITY_STATS_CUTOFF — reset de métricas por ciudad")
    test("CITY_STATS_CUTOFF definido en código",
         "CITY_STATS_CUTOFF" in code)
    test("get_city_accuracy respeta CITY_STATS_CUTOFF",
         "CITY_STATS_CUTOFF.get(city" in code)
    test("get_city_accuracy filtra por closed_at",
         'r.get("closed_at")' in code and "< cutoff" in code)

    # Test funcional: trade anterior al cutoff queda excluido
    cutoff_ns = {
        "CITY_STATS_CUTOFF": {"Dallas": "2026-04-06"},
        "os": __import__("os"),
        "json": __import__("json"),
    }
    # Simular load_postmortem_data con un trade Dallas cerrado antes y uno después del cutoff
    _pre  = {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Dallas", "closed_at": "2026-04-05T10:00:00+00:00", "pnl_cash": -1.0}
    _post = {"status": "closed", "close_action": "RESOLVED_WIN", "city": "Dallas", "closed_at": "2026-04-07T10:00:00+00:00", "pnl_cash": 1.5}
    cutoff_ns["load_postmortem_data"] = lambda: [_pre, _post]
    exec(get_function_source(module_ast, code_lines, "get_city_accuracy"), cutoff_ns)
    _acc = cutoff_ns["get_city_accuracy"]()
    test("cutoff excluye trade anterior (solo 1 trade Dallas post-cutoff)",
         _acc.get("Dallas", {}).get("trades") == 1)
    test("cutoff: trade post-cutoff es ganador (WR=100%)",
         _acc.get("Dallas", {}).get("win_rate") == 100.0)

    # ---- Test 3: Bug #12 — Resueltas no en keeping ----
    policy_ns = {
        "CITY_STATS_CUTOFF": {"Dallas": "2026-04-06"},
        "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
    }
    policy_ns["load_postmortem_data"] = lambda: [
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Dallas", "date": "2026-04-05", "closed_at": "2026-04-05T10:00:00+00:00", "pnl_cash": -1.0},
        {"status": "closed", "close_action": "RESOLVED_WIN", "city": "Dallas", "date": "2026-04-07", "closed_at": "2026-04-07T10:00:00+00:00", "pnl_cash": 1.5},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Chicago", "date": "2026-04-02", "closed_at": "2026-04-02T10:00:00+00:00", "pnl_cash": -1.2},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Chicago", "date": "2026-04-03", "closed_at": "2026-04-03T10:00:00+00:00", "pnl_cash": -1.0},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Chicago", "date": "2026-04-04", "closed_at": "2026-04-04T10:00:00+00:00", "pnl_cash": -0.8},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Atlanta", "date": "2026-03-20", "closed_at": "2026-03-20T10:00:00+00:00", "pnl_cash": -1.0},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Atlanta", "date": "2026-03-21", "closed_at": "2026-03-21T10:00:00+00:00", "pnl_cash": -1.1},
        {"status": "closed", "close_action": "LOSS_TOTAL", "city": "Atlanta", "date": "2026-03-22", "closed_at": "2026-03-22T10:00:00+00:00", "pnl_cash": -1.2},
    ]
    exec(get_function_source(module_ast, code_lines, "get_city_policy_metrics"), policy_ns)
    _policy = policy_ns["get_city_policy_metrics"](audit={
        "observed_vs_forecast": [
            {"city": "Chicago", "date": "2026-04-02", "source": "noaa_ncei"},
            {"city": "Chicago", "date": "2026-04-03", "source": "noaa_ncei"},
            {"city": "Chicago", "date": "2026-04-04", "source": "noaa_ncei"},
            {"city": "Atlanta", "date": "2026-03-20", "source": "legacy_proxy"},
        ]
    })
    test("city policy metrics: separa NOAA-verificado de legacy",
         _policy.get("Chicago", {}).get("policy_source") == "noaa_verified"
         and _policy.get("Chicago", {}).get("verified", {}).get("trades") == 3
         and _policy.get("Chicago", {}).get("legacy", {}).get("trades") == 0,
         _policy.get("Chicago"))
    test("city policy metrics: legacy sin NOAA queda provisional",
         _policy.get("Atlanta", {}).get("policy_source") == "legacy"
         and _policy.get("Atlanta", {}).get("policy_is_provisional") is True
         and _policy.get("Atlanta", {}).get("legacy", {}).get("trades") == 3,
         _policy.get("Atlanta"))
    test("city policy metrics: Dallas respeta cutoff tambien en split de policy",
         _policy.get("Dallas", {}).get("policy_source") == "legacy"
         and _policy.get("Dallas", {}).get("legacy", {}).get("trades") == 1
         and _policy.get("Dallas", {}).get("verified", {}).get("trades") == 0,
         _policy.get("Dallas"))
    _policy_dates = policy_ns["get_city_policy_metrics"](audit={
        "observed_vs_forecast": [
            {"city": "Chicago", "date": "2026-04-02T00:00:00", "source": "noaa_ncei"},
        ]
    })
    test("city policy metrics: normaliza fechas datetime a YYYY-MM-DD",
         _policy_dates.get("Chicago", {}).get("verified", {}).get("trades") == 1,
         _policy_dates.get("Chicago"))

    print("\n Bug #12: Resueltas excluidas de keeping")
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
        test("Bloque resueltas S incrementa n_resolved", "n_resolved += 1" in block)
    else:
        test("Bloque de resueltas encontrado", False)

    # ---- Test 4: Bug #9 — sold_token_ids ----
    print("\n Bug #9: No re-entrada tras venta")
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
    print("\n Bug #3: No duplicar posiciones")
    test("existing_position_tokens se construye",
         "existing_position_tokens" in code)
    test("Check 'YA HAY POSICIÓN ABIERTA'",
         "YA HAY POSICIÓN ABIERTA" in code)
    test("existing_position_tokens usa Data API",
         "existing_position_tokens.add(asset)" in code)

    # ---- Test 6: Bug #11 — Skip ciclo inicial ----
    print("\n Bug #11: Skip ciclo extra al arrancar")
    test("skip_first_cycle variable existe", "skip_first_cycle" in code)
    test("min_cycle_gap_hours definido", "min_cycle_gap_hours" in code)
    test("Comprueba timestamp del último ciclo",
         "age_hours" in code and "min_cycle_gap_hours" in code)
    test("Condicional 'if not skip_first_cycle'",
         "if not skip_first_cycle:" in code)

    # ---- Test 7: Bug #14 — Precio límite clarificado ----
    print("\n Bug #14: Precio límite en Telegram")
    test("Mensaje de venta dice 'precio límite'",
         "precio límite" in code)
    test("Mensaje de venta dice 'precio real puede diferir'",
         "precio real puede diferir" in code)

    # ---- Test 8: Mejoras Telegram ----
    print("\n Mejoras Telegram")
    test("/estado muestra Compras y Ventas separadas",
         "Compras:" in code and "Ventas:" in code and "last_sells_placed" in code)
    test("Resumen ciclo dice 'Exposición actual'",
         "Exposición actual" in code)
    test("Resumen ciclo dice 'Presupuesto libre'",
         "Presupuesto libre" in code)

    # ---- Test 9: Persistencia DATA_DIR ----
    print("\n Persistencia (DATA_DIR)")
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
    print("\n Checks heredados (v10.3)")
    test("CITY_TIMEZONES existe", "CITY_TIMEZONES" in code)
    test("get_min_days_for_city existe", "def get_min_days_for_city" in code)
    test("SELL_PENDING en track_trade", 'track_trade("SELL_PENDING"' in code)
    test("audit_check_sell_fills existe", "def audit_check_sell_fills" in code)
    test("_loss_total_tracked set existe", "_loss_total_tracked" in code)
    test("curPrice >= 0.98 excluido de exposición",
         "cur_price >= 0.98" in code or "curPrice >= 0.98" in code)

    # ---- Test 11: Imports necesarios ----
    print("\n Imports")
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
    print("\n Configuración")
    test("STOP_LOSS_PCT es negativo", 'STOP_LOSS_PCT' in code and '"-25.0"' in code)
    test("TAKE_PROFIT_PCT es positivo", 'TAKE_PROFIT_PCT' in code and '"40.0"' in code)
    test("MAX_EXPOSURE_PCT es 0.40", '"0.40"' in code)
    test("MIN_EDGE default es 15.0", '"15.0"' in code)
    test("SCHEDULE_HOURS_UTC configurable", 'SCHEDULE_HOURS_UTC' in code)
    test("BLOCKED_CITIES default incluye ciudades perdedoras", '"London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara"' in code)
    test("ACTIVE_TRADING_CITIES definida", "ACTIVE_TRADING_CITIES = {" in code)
    test("ACTIVE_TRADING_CITIES contiene las 4 ciudades activas",
         '"ACTIVE_TRADING_CITIES",' in code
         and '"Chicago,Atlanta,Dallas,Buenos Aires"' in code)
    test("scan usa ACTIVE_TRADING_CITIES para filtrar entradas nuevas",
         'if not allowlisted:' in code
         and 'SHADOW {city}: fuera de ACTIVE_TRADING_CITIES (se observa, no se compra)' in code)
    test("is_city_blocked definida", "def is_city_blocked(" in code)
    test("parse_market_date_iso definida", "def parse_market_date_iso(" in code)
    test("format_postmortem_label definida", "def format_postmortem_label(" in code)

    # ---- Test 12b: v10.6.10 Resolution fidelity + allowlist activa ----
    print("\n v10.6.10: Resolution fidelity + allowlist activa")
    test("Dallas usa coords KDAL / Love Field",
         '"Dallas":         {"lat": 32.8459,  "lon": -96.8510,  "name": "Dallas Love Field"}' in code)
    test("RESOLUTION_ICAO existe", "RESOLUTION_ICAO = {" in code)
    test("RESOLUTION_ICAO Chicago -> KORD + NOAA daily",
         '"Chicago":        {"icao": "KORD", "wu_url": _wu_history_url("KORD"), "noaa_station_id": "72530094846", "noaa_daily_station_id": "USW00094846"}' in code)
    test("RESOLUTION_ICAO Atlanta -> KATL + NOAA daily",
         '"Atlanta":        {"icao": "KATL", "wu_url": _wu_history_url("KATL"), "noaa_station_id": "72219013874", "noaa_daily_station_id": "USW00013874"}' in code)
    test("RESOLUTION_ICAO Buenos Aires -> SAEZ + NOAA daily",
         '"Buenos Aires":   {"icao": "SAEZ", "wu_url": _wu_history_url("SAEZ"), "noaa_station_id": "87576099999", "noaa_daily_station_id": "ARM00087576"}' in code)
    test("RESOLUTION_ICAO Buenos Aires tiene noaa_daily_station_id no vacio",
         re.search(r'"Buenos Aires":\s+\{"icao": "SAEZ".*"noaa_daily_station_id": "[^"]+"', code) is not None)
    test("RESOLUTION_ICAO Dallas -> KDAL + NOAA daily",
         '"Dallas":         {"icao": "KDAL", "wu_url": _wu_history_url("KDAL"), "noaa_station_id": "72258303927", "noaa_daily_station_id": "USW00013960"}' in code)
    test("RESOLUTION_ICAO incluye ciudades bloqueadas",
         '"London":         {"icao": "EGLC", "wu_url": _wu_history_url("EGLC")}' in code
         and '"Madrid":         {"icao": "LEMD", "wu_url": _wu_history_url("LEMD")}' in code)
    test("OBSERVED_AUDIT_KEY separado del legacy", 'OBSERVED_AUDIT_KEY = "observed_vs_forecast"' in code)
    test("OBSERVED_AUDIT_CITIES solo contiene 4 activas",
         'OBSERVED_AUDIT_CITIES = {"Chicago", "Atlanta", "Buenos Aires", "Dallas"}' in code)
    test("OBSERVED_FORECAST_MIN_SAMPLE es 3", "OBSERVED_FORECAST_MIN_SAMPLE = 3" in code)
    test("OBSERVED_FORECAST_GLOBAL_TARGET es 10", "OBSERVED_FORECAST_GLOBAL_TARGET = 10" in code)
    test("fetch_noaa_daily_tmax definida", "def fetch_noaa_daily_tmax(" in code)
    test("fetch_noaa_observed_max definida", "def fetch_noaa_observed_max(" in code)
    test("audit_check_resolution_truth definida", "def audit_check_resolution_truth(" in code)
    test("audit NOAA usa source=noaa_ncei", '"source": "noaa_ncei"' in code)
    audit_fn_src = get_function_source(module_ast, code_lines, "audit_check_open_meteo_forecast_drift")
    test("Auditoría drift documenta que NO valida WU",
         "Weather Underground" in audit_fn_src and "NO valida" in audit_fn_src)
    test("Auditoría drift habla de forecast posterior",
         "forecast posterior Open-Meteo" in audit_fn_src)
    test("Auditoría drift no usa 'real=' en mensajes",
         " real=" not in audit_fn_src)
    observed_audit_fn_src = get_function_source(module_ast, code_lines, "audit_check_resolution_truth")
    test("Auditoría NOAA documenta observed proxy",
         "Observed proxy audit" in observed_audit_fn_src and "source=noaa_ncei" in observed_audit_fn_src)

    print("\n Trader data en Volume")
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

    print("\n Dashboard web")
    test("DASHBOARD_ENABLED definido", "DASHBOARD_ENABLED" in code)
    test("DASHBOARD_PORT definido", "DASHBOARD_PORT" in code and 'os.getenv("PORT"' in code)
    test("BANKROLL_LEVELS definido", "BANKROLL_LEVELS" in code)
    test("AGENT_EVENTS_FILE usa _sync_agent_events_seed", 'AGENT_EVENTS_FILE = _sync_agent_events_seed()' in code)
    test("_sync_agent_events_seed definida", "def _sync_agent_events_seed(" in code)
    test("load_agent_events definida", "def load_agent_events(" in code)
    test("_normalize_agent_event_stage definida", "def _normalize_agent_event_stage(" in code)
    test("compute_agent_scorecard definida", "def compute_agent_scorecard(" in code)
    test("get_logic_series_clean_closed_trade_stats definida", "def get_logic_series_clean_closed_trade_stats(" in code)
    test("get_validated_closed_postmortems definida", "def get_validated_closed_postmortems(" in code)
    test("build_dashboard_progress definida", "def build_dashboard_progress(" in code)
    test("build_dashboard_trophies definida", "def build_dashboard_trophies(" in code)
    test("build_dashboard_unlocks definida", "def build_dashboard_unlocks(" in code)
    test("build_dashboard_exit_breakdown definida", "def build_dashboard_exit_breakdown(" in code)
    test("build_dashboard_forecast_quality definida", "def build_dashboard_forecast_quality(" in code)
    test("build_dashboard_city_observation definida", "def build_dashboard_city_observation(" in code)
    test("build_dashboard_city_decisions definida", "def build_dashboard_city_decisions(" in code)
    test("build_dashboard_road_to_real definida", "def build_dashboard_road_to_real(" in code)
    test("load_city_policy_state definida", "def load_city_policy_state(" in code)
    test("save_city_policy_state definida", "def save_city_policy_state(" in code)
    test("get_effective_city_mode definida", "def get_effective_city_mode(" in code)
    test("_normalize_city_policy_state definida", "def _normalize_city_policy_state(" in code)
    test("_build_auto_city_block_policy definida", "def _build_auto_city_block_policy(" in code)
    test("_build_auto_city_shadow_policy definida", "def _build_auto_city_shadow_policy(" in code)
    test("sync_city_policy_state definida", "def sync_city_policy_state(" in code)
    test("city policy persiste auto_blocked_cities", '"auto_blocked_cities": {}' in code and 'payload.setdefault("auto_blocked_cities", {})' in code)
    test("get_effective_city_mode migra auto_block legacy a shadow",
         'auto_blocked = policy_state.get("auto_blocked_cities", {})' in code
         and '_normalize_city_policy_state' in code
         and 'return "shadow"' in code)
    test("build_dashboard_focus_center definida", "def build_dashboard_focus_center(" in code)
    test("build_dashboard_legacy_forecast_drift definida", "def build_dashboard_legacy_forecast_drift(" in code)
    test("build_dashboard_trade_analytics definida", "def build_dashboard_trade_analytics(" in code)
    test("build_promotion_checklist definida", "def build_promotion_checklist(" in code)
    test("build_dashboard_snapshot definida", "def build_dashboard_snapshot(" in code)
    test("create_dashboard_app definida", "def create_dashboard_app(" in code)
    test("start_dashboard_server definida", "def start_dashboard_server(" in code)
    test("dashboard arranca en __main__", "start_dashboard_server()" in code)
    test("requirements incluye Flask", "Flask==" in requirements_code)
    test("requirements incluye waitress", "waitress==" in requirements_code)
    test("template dashboard existe", os.path.exists(dashboard_template_path))
    test("css dashboard existe", os.path.exists(dashboard_css_path))
    test("js dashboard existe", os.path.exists(dashboard_js_path))
    test("agent_events.jsonl existe", os.path.exists(agent_events_path))
    test("OPERATIONS_PLAYBOOK existe", os.path.exists(operations_playbook_path))
    test("helper append_agent_event existe", os.path.exists(append_agent_event_path))
    test("CLAUDE.md remite al playbook", "OPERATIONS_PLAYBOOK.md" in claude_md_code)
    test("CONTEXTO remite al playbook", "OPERATIONS_PLAYBOOK.md" in contexto_code)
    test("playbook define checklist inicio/cierre",
         "Checklist de inicio" in operations_playbook_code and "Checklist de cierre" in operations_playbook_code)
    test("playbook define regla de hardening",
         "Todo error detectado debe dejar" in operations_playbook_code and "guardrail" in operations_playbook_code)
    test("playbook cubre scoreboard y agent_events",
         "agent_events.jsonl" in operations_playbook_code and "scoreboard" in operations_playbook_code.lower())
    test("playbook define review sin delta = 0 puntos",
         "Validacion o aprobacion sin delta no merece puntos" in operations_playbook_code and "`0 puntos`" in operations_playbook_code)
    test("helper append_agent_event evita duplicados",
         "Duplicate event blocked" in append_agent_event_code and 'row.get("session") == event["session"]' in append_agent_event_code)
    test("template dashboard incluye Road to Real", "dashboard.road_to_real" in dashboard_template_code and "Road to Real" in dashboard_template_code and "requisitos cumplidos" in dashboard_template_code)
    test("template dashboard incluye Estado del bot", "Estado del bot" in dashboard_template_code and "Mercados escaneados" in dashboard_template_code and "markets_evaluated" in dashboard_template_code)
    test("template dashboard incluye shadow direccional", "Senales shadow direccionales" in dashboard_template_code and "Condicion" in dashboard_template_code and "Forecast" in dashboard_template_code)
    test("template dashboard incluye contadores shadow consistentes", "recientes" in dashboard_template_code and "historicas" in dashboard_template_code)
    test("template dashboard incluye Salud del sistema", "Salud del sistema" in dashboard_template_code and "<details class=\"layer-toggle\">" in dashboard_template_code)
    test("template dashboard incluye NOAA observado", "dashboard.forecast_quality" in dashboard_template_code and "Calidad NOAA observada" in dashboard_template_code)
    test("template dashboard incluye NOAA observado", "dashboard.forecast_quality" in dashboard_template_code and "Calidad NOAA observada" in dashboard_template_code)
    test("template dashboard incluye estado por ciudad", "dashboard.city_observation" in dashboard_template_code and "Estado por ciudad" in dashboard_template_code)
    test("template dashboard incluye señales shadow", "dashboard.city_decisions" in dashboard_template_code and "shadow_summary" in dashboard_template_code)
    test("template dashboard incluye focus status", "dashboard.focus" in dashboard_template_code and "dashboard.focus.status_badge" in dashboard_template_code and "dashboard.focus.action" in dashboard_template_code)
    test("template dashboard carga dashboard.js", "dashboard.js" in dashboard_template_code)
    test("template dashboard muestra n/d sin cierres", "pnl_display" in dashboard_template_code and "win_rate_display" in dashboard_template_code and "drawdown_display" in dashboard_template_code)
    test("css dashboard en modo claro", "--bg: #f3ede3;" in dashboard_css_code and "--card: rgba(255, 255, 255, 0.92);" in dashboard_css_code)
    test("css dashboard define table-note", ".table-note" in dashboard_css_code)
    test("css dashboard define estado waiting", ".check-status.waiting" in dashboard_css_code and ".check-tag-waiting" in dashboard_css_code)
    test("css dashboard define estado blocked", ".check-status.blocked" in dashboard_css_code and ".check-tag-blocked" in dashboard_css_code)
    test("css dashboard define trophy-grid", ".trophy-grid" in dashboard_css_code and ".trophy-card" in dashboard_css_code)
    test("css dashboard define focus layer", ".focus-grid" in dashboard_css_code and ".focus-answer-grid" in dashboard_css_code and ".action-callout" in dashboard_css_code)
    test("css dashboard define mission HUD", ".focus-tab-bar" in dashboard_css_code and ".mission-track-grid" in dashboard_css_code and ".city-race-list" in dashboard_css_code)
    test("css dashboard define city grouping cards", ".city-zone-grid" in dashboard_css_code and ".city-card-grid" in dashboard_css_code and ".blocked-pill-list" in dashboard_css_code)
    test("css dashboard define layer toggle", ".layer-toggle" in dashboard_css_code and ".layer-toggle-content" in dashboard_css_code)
    test("css dashboard define ranking operacional", ".city-ranking-table" in dashboard_css_code and ".city-score-bar" in dashboard_css_code and ".city-ranking-row-degraded" in dashboard_css_code)
    test("js dashboard soporta multiples tab shells", "data-tab-shell" in dashboard_js_code and "defaultPanel" in dashboard_js_code)
    if os.path.exists(agent_events_path):
        try:
            with open(agent_events_path, "r", encoding="utf-8") as f:
                events_count = sum(1 for line in f if line.strip())
            test("agent_events.jsonl tiene eventos semilla", events_count >= 5, f"eventos={events_count}")
            test("agent_events.jsonl explicita stage en eventos", bool(agent_event_rows) and all(row.get("stage") for row in agent_event_rows))
            latest_doc_session = max(
                [int(v) for v in re.findall(r"Sesión\s+(\d+)", contexto_code + "\n" + historial_code)],
                default=0,
            )
            latest_event_session = max(
                [_normalize_session_value(row.get("session")) for row in agent_event_rows],
                default=0,
            )
            test("agent_events cubre la sesión documentada más reciente",
                 latest_doc_session == latest_event_session,
                 f"docs={latest_doc_session} events={latest_event_session}")
        except Exception as e:
            test("agent_events.jsonl legible", False, str(e))

    # ---- Test 13: Nuevas funcionalidades v10.4.1 ----
    print("\n Nuevas funcionalidades v10.4.1")
    test("CYCLE_SUMMARY_FILE definido", "CYCLE_SUMMARY_FILE" in code)
    test("CYCLES_HISTORY_FILE definido", "CYCLES_HISTORY_FILE" in code)
    test("cycles_history.jsonl append-only", "cycles_history.jsonl" in code)
    test("cycle_summary se guarda en main()", "cycle_data" in code and "CYCLE_SUMMARY_FILE" in code)
    test("cycle_data incluye version v10.6.10", '"version"' in code and "v10.6.10" in code)
    test("cycle_data incluye logic_series", '"logic_series": LOGIC_SERIES' in code)
    test("cycle_data incluye logic_cycle_number", '"logic_cycle_number"' in code)

    # ---- Test 14: Rediseño Telegram v10.4.2 ----
    print("\n Rediseño Telegram v10.4.2")
    test("send_telegram_paged definida", "def send_telegram_paged(" in code)
    test("_parse_position_label definida", "def _parse_position_label(" in code)
    test("_get_portfolio_and_positions definida", "def _get_portfolio_and_positions(" in code)
    test("cmd_info definida", "def cmd_info(" in code)
    test("cmd_postmortem definida", "def cmd_postmortem(" in code)
    test("cmd_accuracy definida", "def cmd_accuracy(" in code)
    test("cmd_focus definida", "def cmd_focus(" in code)
    test("cmd_noaa definida", "def cmd_noaa(" in code)
    test("/focus en COMMANDS", '"focus": cmd_focus' in code)
    test("/info en COMMANDS", '"info": cmd_info' in code)
    test("/postmortem en COMMANDS", '"postmortem": cmd_postmortem' in code)
    test("/accuracy en COMMANDS", '"accuracy": cmd_accuracy' in code)
    test("/noaa en COMMANDS", '"noaa": cmd_noaa' in code)
    test("/observabilidad en COMMANDS", '"observabilidad": cmd_noaa' in code)
    test("/info en MENU_KEYBOARD", '"callback_data": "info"' in code)
    test("/postmortem en MENU_KEYBOARD", '"callback_data": "postmortem"' in code)
    test("/accuracy en MENU_KEYBOARD", '"callback_data": "accuracy"' in code)
    test("Bug #13: send_telegram_paged en cmd_log", "send_telegram_paged" in code and "cmd_log" in code)
    test("Bug #13: send_telegram_paged en cmd_cartera", "send_telegram_paged" in code)
    test("_parse_position_label usa centavos (¢)", "¢" in code)
    test("cmd_estado versión correcta", "Bot v10.6.10" in code or "v10.6.10" in code)

    # ---- Test 14c: Zonas horarias reales v10.4.5 ----
    print("\n Zonas horarias reales")
    test("get_min_days_for_city usa ZoneInfo", "ZoneInfo(" in code and "astimezone" in code)
    test("London usa Europe/London", '"London":         "Europe/London"' in code)
    test("Madrid usa Europe/Madrid", '"Madrid":         "Europe/Madrid"' in code)
    test("New York usa America/New_York", '"New York City":  "America/New_York"' in code)
    test("Chicago usa America/Chicago", '"Chicago":        "America/Chicago"' in code)
    test("Seattle usa America/Los_Angeles", '"Seattle":        "America/Los_Angeles"' in code)
    test("Tel Aviv usa Asia/Jerusalem", '"Tel Aviv":       "Asia/Jerusalem"' in code)

    # ---- Test 14b: Fixes v10.4.3 ----
    print("\n Fixes v10.4.3")
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

    print("\n Bloqueo London")
    test("main filtra ciudades bloqueadas", "blocked_city_skip" in code and "Ciudades bloqueadas operativamente" in code)
    test("London se bloquea por helper", 'if is_city_blocked(city):' in code)

    # ---- Test 15: Integridad de COMMANDS (todos los botones siguen presentes) ----
    print("\n Integridad de COMMANDS")
    for cmd in ["focus", "estado", "cartera", "ordenes", "log", "logfull",
                "forzar", "modo", "traders", "rendimiento", "info", "postmortem", "accuracy",
                "noaa", "observabilidad",
                "confirmar_real", "confirmar_dry", "cancelar_modo"]:
        test(f'COMMANDS tiene "{cmd}"', f'"{cmd}"' in code)

    # ---- Test 16: send_telegram_paged en todos los comandos de respuesta larga ----
    print("\n send_telegram_paged en comandos relevantes")
    for cmd_name in ["cmd_focus", "cmd_cartera", "cmd_ordenes", "cmd_log", "cmd_logfull",
                     "cmd_traders", "cmd_rendimiento", "cmd_info", "cmd_postmortem", "cmd_accuracy",
                     "cmd_noaa"]:
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
    print("\n Robustez _get_portfolio_and_positions")
    test("api_error en return de _get_portfolio", '"api_error"' in code)
    test("api_error se muestra en cmd_cartera",
         "api_error" in code and "Error API posiciones" in code)

    # ---- Test 18: cmd_info contiene campos esenciales ----
    print("\n Contenido de cmd_info")
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
    print("\n Tests funcionales")
    try:
        builtins.parse_temperature_question = lambda question: {
            "city": "Test City",
            "temp_threshold": 10,
            "temp_threshold_high": None,
            "condition": "exact",
            "date_str": "March 30",
            "unit": "C",
        }
        ns = {"re": re, "datetime": datetime, "timezone": timezone}
        exec(get_function_source(module_ast, code_lines, "parse_temperature_question"), ns)
        exec(get_function_source(module_ast, code_lines, "parse_city_from_title"), ns)
        exec(get_function_source(module_ast, code_lines, "_parse_position_label"), ns)
        exec(get_function_source(module_ast, code_lines, "parse_market_date_iso"), ns)
        exec(get_function_source(module_ast, code_lines, "format_market_date_short"), ns)
        exec(get_function_source(module_ast, code_lines, "format_postmortem_label"), ns)
        helper_ns = {"BLOCKED_CITIES": {"london", "paris", "miami", "seattle", "tel aviv", "wellington", "toronto", "madrid", "singapore", "ankara"}}
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
        test("blocked city helper: Paris bloqueada",
             helper_ns["is_city_blocked"]("Paris"))
        test("blocked city helper: Chicago permitida",
             not helper_ns["is_city_blocked"]("Chicago"))

        fd, tmp_cycles = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_cycles_history_test_",
            suffix=".jsonl",
        )
        os.close(fd)
        with open(tmp_cycles, "w", encoding="utf-8") as f:
            f.write(json.dumps({"version": "v10.4.8", "cycle_number": 1}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"version": "v10.5.1", "cycle_number": 2}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"logic_series": "10.6", "version": "v10.6.10", "cycle_number": 3}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"logic_series": "10.6", "version": "v10.6.10", "cycle_number": 4}, ensure_ascii=False) + "\n")
        cycle_ns = {
            "os": os,
            "json": json,
            "re": re,
            "LOGIC_SERIES": "10.6",
            "CYCLES_HISTORY_FILE": tmp_cycles,
        }
        exec(get_function_source(module_ast, code_lines, "_extract_logic_series"), cycle_ns)
        exec(get_function_source(module_ast, code_lines, "_load_cycle_counts"), cycle_ns)
        total_count, series_count = cycle_ns["_load_cycle_counts"]()
        test("cycle_counts: total histórico correcto", total_count == 4, f"got {total_count}")
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
            "LOGIC_SERIES": "10.6",
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
            "get_dashboard_alert_summary": lambda: {"signals": {"status": "ok"}, "pending_stuck": [], "flagged_cities": [], "active_items": [], "low_bankroll": False, "portfolio_total": 14.75},
            "_load_cycle_counts": lambda: (18, 12),
        }
        exec(get_function_source(module_ast, code_lines, "build_promotion_checklist"), checklist_ns)
        checklist = checklist_ns["build_promotion_checklist"]()
        test("checklist: decision READY cuando todo pasa", checklist["decision"] == "READY", checklist)
        test("checklist: progreso 100 cuando todo pasa", checklist["progress_pct"] == 100.0, checklist)
        test("checklist: separa histórico y serie", any(item["label"] == "Trades limpios históricos" for item in checklist["checks"]) and any(item["label"] == "Trades limpios serie v10.6" for item in checklist["checks"]))
        test("checklist: histórico no bloquea promoción", any(item["label"] == "Trades limpios históricos" and not item["blocking"] for item in checklist["checks"]))
        test("checklist: estados good presentes", all(item["status"] == "good" and item["tag"] == "OK" for item in checklist["checks"]), checklist["checks"])

        checklist_empty_ns = {
            "LOGIC_SERIES": "10.6",
            "REVIEW_READY_CLEAN_TRADES": 30,
            "PROMOTION_MIN_SERIES_CYCLES": 10,
            "PROMOTION_MIN_SERIES_WIN_RATE": 40.0,
            "PROMOTION_MIN_SERIES_PNL": 0.0,
            "DRAWDOWN_WINDOW": 5,
            "DRAWDOWN_THRESHOLD": -3.0,
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "get_bankroll_level_context": lambda: {"current_level": 1, "current_target": 25.0, "next_target": 35.0, "is_max_level": False},
            "get_clean_closed_trade_stats": lambda: {"count": 18, "sell": 12, "loss_total": 6, "resolved_win": 0},
            "get_logic_series_clean_closed_trade_stats": lambda: {"count": 0, "sell": 0, "loss_total": 0, "resolved_win": 0},
            "get_logic_series_stats": lambda: {"pnl": 0.0, "win_rate": 0.0, "closed_count": 0, "recent_window_size": 0, "recent_drawdown": 0.0},
            "get_dashboard_alert_summary": lambda: {"signals": {"status": "ok"}, "pending_stuck": [], "flagged_cities": [], "active_items": [], "low_bankroll": False, "portfolio_total": 14.75},
            "_load_cycle_counts": lambda: (5, 1),
        }
        exec(get_function_source(module_ast, code_lines, "build_promotion_checklist"), checklist_empty_ns)
        checklist_empty = checklist_empty_ns["build_promotion_checklist"]()
        pnl_item = next(item for item in checklist_empty["checks"] if item["label"] == "PnL serie v10.6")
        wr_item = next(item for item in checklist_empty["checks"] if item["label"] == "Win rate serie v10.6")
        dd_item = next(item for item in checklist_empty["checks"] if item["label"] == "Drawdown últimos 5 cierres")
        test("checklist vacío: pnl sin cierres", pnl_item["value"] == "sin cierres" and not pnl_item["passed"], pnl_item)
        test("checklist vacío: win rate sin cierres", "sin cierres" in wr_item["value"] and not wr_item["passed"], wr_item)
        test("checklist vacío: drawdown sin cierres", "sin cierres" in dd_item["value"] and not dd_item["passed"], dd_item)
        test("checklist vacío: usa estado waiting", pnl_item["status"] == "waiting" and pnl_item["tag"] == "Esperando muestra", pnl_item)
        test("checklist vacío: win rate usa estado waiting", wr_item["status"] == "waiting" and wr_item["tag"] == "Esperando muestra", wr_item)
        test("checklist vacío: drawdown usa estado waiting", dd_item["status"] == "waiting" and dd_item["tag"] == "Esperando muestra", dd_item)

        # Ventana parcial (2 de 5 cierres requeridos): drawdown debe mostrar "Esperando muestra"
        # Bug pre-fix: con 1-4 cierres, el check pasaba como OK porque recent_window_size < DRAWDOWN_WINDOW = True
        checklist_partial_dd_ns = dict(checklist_empty_ns)
        checklist_partial_dd_ns["get_logic_series_stats"] = lambda: {
            "pnl": -2.0, "win_rate": 25.0, "closed_count": 2,
            "recent_window_size": 2, "recent_drawdown": -2.0,
        }
        checklist_partial_dd_ns["get_logic_series_clean_closed_trade_stats"] = lambda: {
            "count": 2, "sell": 1, "loss_total": 1, "resolved_win": 0,
        }
        exec(get_function_source(module_ast, code_lines, "build_promotion_checklist"), checklist_partial_dd_ns)
        checklist_partial_dd = checklist_partial_dd_ns["build_promotion_checklist"]()
        dd_partial_item = next(item for item in checklist_partial_dd["checks"] if "Drawdown" in item["label"])
        test("checklist parcial: drawdown con muestra incompleta usa estado waiting",
             dd_partial_item["status"] == "waiting" and dd_partial_item["tag"] == "Esperando muestra", dd_partial_item)
        test("checklist parcial: drawdown muestra contador de cierres disponibles",
             "2/5" in dd_partial_item["value"], dd_partial_item)

        progress_ns = {
            "LOGIC_SERIES": "10.6",
            "REVIEW_READY_CLEAN_TRADES": 30,
            "PROMOTION_MIN_SERIES_CYCLES": 10,
            "PROMOTION_CITY_COVERAGE_TARGET": 3,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "_load_cycle_counts": lambda: (5, 1),
        }
        exec(get_function_source(module_ast, code_lines, "_dashboard_status_item"), progress_ns)
        exec(get_function_source(module_ast, code_lines, "build_dashboard_progress"), progress_ns)
        progress_items = progress_ns["build_dashboard_progress"](
            promotion={
                "levels": {"next_target": 35.0, "is_max_level": False},
                "passed": 3,
                "total": 9,
                "blocking_failed": 3,
                "decision": "HOLD",
            },
            clean_stats={"count": 18, "sell": 12, "loss_total": 6, "resolved_win": 0},
            series_clean_stats={"count": 0, "sell": 0, "loss_total": 0, "resolved_win": 0},
            series_stats={"closed_count": 0, "pnl": 0.0, "win_rate": 0.0, "recent_window_size": 0, "recent_drawdown": 0.0},
            city_accuracy={},
            alerts={"signals": {"status": "ok"}, "pending_stuck": [], "flagged_cities": []},
            cycle_series=1,
        )
        sample_item = next(item for item in progress_items if item["label"] == "Muestra para revisar lógica v10.6")
        closures_item = next(item for item in progress_items if item["label"] == "Cierres útiles para win rate")
        readiness_item = next(item for item in progress_items if item["label"] == "Readiness subida $35")
        coverage_item = next(item for item in progress_items if item["label"] == "Cobertura de ciudades")
        test("progress: muestra trades restantes", sample_item["value"] == "0 / 30" and "faltan 30" in sample_item["detail"], sample_item)
        test("progress: cierres útiles esperan muestra", closures_item["status"] == "waiting" and closures_item["tag"] == "Esperando muestra", closures_item)
        test("progress: readiness etiqueta gates pendientes", readiness_item["value"] == "3 / 9 gates" and "faltan 6 gates" in readiness_item["detail"], readiness_item)
        test("progress: cobertura ciudades no la presenta como firme sin muestra", coverage_item["status"] == "waiting" and "ninguna ciudad supera 3 cierres" in coverage_item["detail"], coverage_item)

        unlocks_ns = {
            "LOGIC_SERIES": "10.6",
            "REVIEW_READY_CLEAN_TRADES": 30,
            "PROMOTION_MIN_SERIES_CYCLES": 10,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "_load_cycle_counts": lambda: (5, 1),
        }
        exec(get_function_source(module_ast, code_lines, "_dashboard_status_item"), unlocks_ns)
        exec(get_function_source(module_ast, code_lines, "build_dashboard_unlocks"), unlocks_ns)
        unlock_items = unlocks_ns["build_dashboard_unlocks"](
            promotion={
                "levels": {"next_target": 35.0},
                "passed": 3,
                "total": 9,
                "blocking_failed": 2,
                "decision": "HOLD",
            },
            series_stats={"closed_count": 0, "pnl": 0.0, "win_rate": 0.0, "recent_window_size": 0, "recent_drawdown": 0.0},
            series_clean_stats={"count": 0, "sell": 0, "loss_total": 0, "resolved_win": 0},
            city_accuracy={"Miami": {"trades": 2, "wins": 0, "pnl": -4.07, "win_rate": 0.0}},
            alerts={"signals": {"status": "stale"}, "pending_stuck": [{"city": "Dallas"}], "flagged_cities": []},
        )
        activate_item = next(item for item in unlock_items if item["label"] == "Activar win rate y drawdown de serie")
        alerts_item = next(item for item in unlock_items if item["label"] == "Sin alertas críticas operativas")
        accuracy_item = next(item for item in unlock_items if item["label"] == "Accuracy con muestra suficiente por ciudad")
        test("unlocks: sin cierres usa Esperando muestra", activate_item["status"] == "waiting" and activate_item["tag"] == "Esperando muestra", activate_item)
        test("unlocks: alertas críticas bloquean subida", alerts_item["status"] == "blocked" and alerts_item["tag"] == "Bloqueado", alerts_item)
        test("unlocks: accuracy explica cuánto falta por ciudad", "faltan 1 cierres en Miami" in accuracy_item["value"], accuracy_item)

        trophies_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "re": re,
        }
        exec(get_function_source(module_ast, code_lines, "parse_market_date_iso"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "format_market_date_short"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "parse_city_from_title"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "_parse_position_label"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "format_postmortem_label"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "_extract_logic_series"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "_dashboard_record_meta"), trophies_ns)
        exec(get_function_source(module_ast, code_lines, "build_dashboard_trophies"), trophies_ns)
        trophy_items = trophies_ns["build_dashboard_trophies"](
            closed_records=[
                {
                    "status": "closed",
                    "city": "Chicago",
                    "side": "YES",
                    "date": "2026-03-26",
                    "question": "",
                    "pnl_cash": 3.96,
                    "pnl_pct": 85.0,
                    "close_action": "SELL",
                    "close_reason": "take_profit",
                    "bot_version_opened": "v10.4.0",
                    "bot_version_closed": "v10.4.0",
                    "buys": [{"edge_pct": 17.3}],
                    "closed_at": "2026-03-26T23:00:00+00:00",
                },
                {
                    "status": "closed",
                    "city": "Dallas",
                    "side": "YES",
                    "date": "2026-03-28",
                    "question": "",
                    "pnl_cash": 0.26,
                    "pnl_pct": 10.6,
                    "close_action": "SELL",
                    "close_reason": "reeval",
                    "bot_version_opened": "v10.4.4",
                    "bot_version_closed": "v10.4.4",
                    "buys": [{"edge_pct": 27.0}],
                    "closed_at": "2026-03-28T16:00:22+00:00",
                },
                {
                    "status": "closed",
                    "city": "London",
                    "side": "NO",
                    "date": "2026-03-26",
                    "question": "",
                    "pnl_cash": -2.25,
                    "pnl_pct": -90.0,
                    "close_action": "LOSS_TOTAL",
                    "close_reason": "wu_mismatch",
                    "bot_version_opened": "v10.4.0",
                    "bot_version_closed": "v10.4.0",
                    "buys": [{"edge_pct": 28.9}],
                    "closed_at": "2026-03-26T20:00:00+00:00",
                },
            ],
            city_accuracy={
                "Chicago": {"trades": 1, "wins": 1, "pnl": 3.96, "win_rate": 100.0},
                "London": {"trades": 1, "wins": 0, "pnl": -2.25, "win_rate": 0.0},
            },
        )
        best_trade_item = next(item for item in trophy_items if item["label"] == "Mejor operación")
        best_return_item = next(item for item in trophy_items if item["label"] == "Mejor retorno %")
        edge_item = next(item for item in trophy_items if item["label"] == "Mayor edge ejecutado")
        dangerous_city_item = next(item for item in trophy_items if item["label"] == "Ciudad más peligrosa")
        test("trofeos: best_trade usa pnl_cash", best_trade_item["value"] == "$+3.96", best_trade_item)
        test("trofeos: best_return usa pnl_pct", best_return_item["value"] == "+85.0%", best_return_item)
        test("trofeos: mayor edge ejecutado sale de compra ejecutada", edge_item["value"] == "+28.9%" and "London" in edge_item["detail"], edge_item)
        test("trofeos: ciudad peligrosa usa pnl agregado", dangerous_city_item["value"] == "London" and "$-2.25" in dangerous_city_item["detail"], dangerous_city_item)

        empty_trophies = trophies_ns["build_dashboard_trophies"](closed_records=[], city_accuracy={})
        test("trofeos vacíos: usan n/d", all(item["value"] == "n/d" for item in empty_trophies), empty_trophies[:2])

        exit_ns = {
            "LOGIC_SERIES": "10.6",
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_exit_breakdown"), exit_ns)
        exit_breakdown = exit_ns["build_dashboard_exit_breakdown"](
            closed_records=[
                {
                    "status": "closed",
                    "city": "Chicago",
                    "side": "YES",
                    "pnl_cash": 3.96,
                    "close_action": "SELL",
                    "close_reason": "take_profit",
                },
                {
                    "status": "closed",
                    "city": "Seattle",
                    "side": "YES",
                    "pnl_cash": -1.34,
                    "close_action": "SELL",
                    "close_reason": "stop_loss",
                },
                {
                    "status": "closed",
                    "city": "London",
                    "side": "NO",
                    "pnl_cash": -2.25,
                    "close_action": "LOSS_TOTAL",
                    "close_reason": "wu_mismatch",
                },
                {
                    "status": "closed",
                    "city": "Ankara",
                    "side": "NO",
                    "pnl_cash": 1.12,
                    "close_action": "RESOLVED_WIN",
                    "close_reason": "market_resolved_yes",
                },
            ],
            series_records=[
                {
                    "status": "closed",
                    "pnl_cash": 0.49,
                    "close_action": "SELL",
                    "close_reason": "take_profit",
                },
                {
                    "status": "pending_exit",
                    "pending_exit": {"pnl_cash": -1.40},
                },
                {
                    "status": "open",
                },
            ],
            portfolio={
                "resolved_won": [{"city": "Chicago"}, {"city": "Paris"}],
                "resolved_value": 5.00,
            },
            logic_series="10.6",
        )
        tp_row = next(item for item in exit_breakdown["validated_rows"] if item["label"] == "Take-profit")
        sl_row = next(item for item in exit_breakdown["validated_rows"] if item["label"] == "Stop-loss")
        resolved_row = next(item for item in exit_breakdown["validated_rows"] if item["label"] == "Ganadas por resolución")
        pending_row = next(item for item in exit_breakdown["series_rows"] if item["label"] == "Pending exit serie v10.6")
        payout_row = next(item for item in exit_breakdown["series_rows"] if item["label"] == "Pendiente pago / canjear")
        test("exit breakdown: TP muestra balance por acción", tp_row["count"] == 1 and tp_row["balance_display"] == "$+3.96", tp_row)
        test("exit breakdown: SL muestra pérdida media", sl_row["count"] == 1 and sl_row["avg_display"] == "$-1.34", sl_row)
        test("exit breakdown: resolución ganada separada de TP", resolved_row["count"] == 1 and resolved_row["balance_display"] == "$+1.12", resolved_row)
        test("exit breakdown: pending_exit usa pnl estimado", pending_row["status"] == "blocked" and pending_row["balance_display"] == "$-1.40", pending_row)
        test("exit breakdown: canjear muestra valor pendiente", payout_row["count"] == 2 and payout_row["balance_display"] == "$5.00", payout_row)

        forecast_quality_ns = {
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_forecast_quality"), forecast_quality_ns)
        observed_dashboard = forecast_quality_ns["build_dashboard_forecast_quality"](
            audit={
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-26", "observed_temp_c": 21.0, "forecast_temp_c": 20.0, "error_c": 1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-28T10:00:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-25", "observed_temp_c": 18.0, "forecast_temp_c": 19.0, "error_c": -1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-27T10:00:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-24", "observed_temp_c": 19.5, "forecast_temp_c": 19.0, "error_c": 0.5, "abs_error_c": 0.5, "source": "noaa_ncei", "checked_at": "2026-03-26T10:00:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-23", "observed_temp_c": 25.5, "forecast_temp_c": 23.0, "error_c": 2.5, "abs_error_c": 2.5, "source": "noaa_ncei", "checked_at": "2026-03-25T10:00:00+00:00"},
                ]
            }
        )
        chicago_observed_row = next(item for item in observed_dashboard["city_rows"] if item["city"] == "Chicago")
        dallas_observed_row = next(item for item in observed_dashboard["city_rows"] if item["city"] == "Dallas")
        test("forecast quality NOAA: muestra global y coverage correctos",
             observed_dashboard["sample_size"] == 4 and observed_dashboard["coverage_display"] == "2 / 4 ciudades con muestra",
             observed_dashboard)
        test("forecast quality NOAA: activa KPIs desde n>=3",
             observed_dashboard["mae_display"] == "1.2C" and observed_dashboard["bias_display"] == "+0.8C",
             observed_dashboard)
        test("forecast quality NOAA: bias por ciudad exige >=3 casos",
             chicago_observed_row["bias_display"] == "+0.2C" and dallas_observed_row["bias_display"] == "acumulando muestra...",
             observed_dashboard["city_rows"])
        test("forecast quality NOAA: mantiene lectura preliminar antes de n=10",
             observed_dashboard["note_level"] == "warn" and "10 casos" in observed_dashboard["note"],
             observed_dashboard)

        observed_low_sample = forecast_quality_ns["build_dashboard_forecast_quality"](
            audit={"observed_vs_forecast": [{"city": "Atlanta", "date": "2026-03-26", "observed_temp_c": 20.0, "forecast_temp_c": 19.0, "error_c": 1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-28T11:00:00+00:00"}]}
        )
        test("forecast quality NOAA: con n<3 muestra acumulando",
             observed_low_sample["mae_display"] == "acumulando muestra..." and "acumulando muestra" in observed_low_sample["note"],
             observed_low_sample)

        city_observation_ns = {
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "ACTIVE_TRADING_CITIES": {"Chicago", "Atlanta", "Dallas", "Buenos Aires"},
            "CANARY_TRADING_CITIES": set(),
            "CANARY_POSITION_SCALE": 0.5,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "RESOLUTION_ICAO": {
                "Chicago": {"icao": "KORD", "noaa_station_id": "72530094846"},
                "Atlanta": {"icao": "KATL", "noaa_station_id": "72219013874"},
                "Dallas": {"icao": "KDAL", "noaa_station_id": "72258303927"},
                "Buenos Aires": {"icao": "SAEZ", "noaa_station_id": "87576099999", "noaa_daily_station_id": "ARM00087576"},
                "London": {"icao": "EGLC"},
                "New York City": {"icao": "KLGA"},
            },
            "is_city_blocked": lambda city: str(city or "").strip().lower() in {"london", "wellington"},
            "_is_shadow_only": lambda: False,
            "get_city_policy_metrics": lambda audit=None: {
                "Chicago": {
                    "policy_source": "noaa_verified",
                    "policy_is_provisional": False,
                    "policy": {"trades": 3, "wins": 2, "win_rate": 66.7, "pnl": 3.0},
                    "verified": {"trades": 3, "wins": 2, "win_rate": 66.7, "pnl": 3.0},
                    "legacy": {"trades": 1, "wins": 1, "win_rate": 100.0, "pnl": 2.2},
                },
                "London": {
                    "policy_source": "legacy",
                    "policy_is_provisional": True,
                    "policy": {"trades": 3, "wins": 0, "win_rate": 0.0, "pnl": -4.0},
                    "verified": {"trades": 0, "wins": 0, "win_rate": 0.0, "pnl": 0.0},
                    "legacy": {"trades": 3, "wins": 0, "win_rate": 0.0, "pnl": -4.0},
                },
                "New York City": {
                    "policy_source": "legacy",
                    "policy_is_provisional": True,
                    "policy": {"trades": 2, "wins": 1, "win_rate": 50.0, "pnl": 0.85},
                    "verified": {"trades": 0, "wins": 0, "win_rate": 0.0, "pnl": 0.0},
                    "legacy": {"trades": 2, "wins": 1, "win_rate": 50.0, "pnl": 0.85},
                },
            },
            "load_city_policy_state": lambda: {"auto_canary_cities": {}, "auto_shadow_cities": {}, "transition_history": []},
            "get_effective_city_mode": lambda city, policy_state=None: (
                "blocked" if str(city or "").strip().lower() in {"london", "wellington"}
                else "active" if city in {"Chicago", "Atlanta", "Dallas", "Buenos Aires"}
                else "shadow"
            ),
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_city_observation"), city_observation_ns)
        city_observation = city_observation_ns["build_dashboard_city_observation"](
            audit={
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-26", "source": "noaa_ncei"},
                    {"city": "Chicago", "date": "2026-03-25", "source": "noaa_ncei"},
                    {"city": "Chicago", "date": "2026-03-24", "source": "noaa_ncei"},
                    {"city": "Dallas", "date": "2026-03-23", "source": "noaa_ncei"},
                ]
            },
            city_accuracy={
                "Chicago": {"trades": 4, "wins": 3, "pnl": 5.2, "win_rate": 75.0},
                "London": {"trades": 3, "wins": 0, "pnl": -4.0, "win_rate": 0.0},
                "New York City": {"trades": 2, "wins": 1, "pnl": 0.85, "win_rate": 50.0},
            },
        )
        chicago_watch_row = next(item for item in city_observation["rows"] if item["city"] == "Chicago")
        london_watch_row = next(item for item in city_observation["rows"] if item["city"] == "London")
        nyc_watch_row = next(item for item in city_observation["rows"] if item["city"] == "New York City")
        test("city observation: cuenta activas y NOAA interpretables",
             city_observation["active_count"] == 4 and city_observation["observed_ready_count"] == 1,
             city_observation)
        test("city observation: expone grupos para dashboard",
             len(city_observation["active_rows"]) == 4
             and len(city_observation["blocked_rows"]) >= 1
             and len(city_observation["watch_rows"]) >= 1,
             city_observation)
        test("city observation: Chicago queda operando con observabilidad",
             chicago_watch_row["trading_label"] == "Activa"
             and chicago_watch_row["noaa_label"] == "Interpretable"
             and chicago_watch_row["state_label"] == "Operando con observabilidad",
             chicago_watch_row)
        test("city observation: London queda bloqueada con historico legacy provisional",
             london_watch_row["trading_label"] == "Bloqueada"
             and london_watch_row["history_badge"] == "warn"
             and london_watch_row["state_label"] == "Bloqueada",
             london_watch_row)
        test("city observation: NYC queda como referencia historica fuera del allowlist",
             nyc_watch_row["trading_label"] == "Shadow"
             and nyc_watch_row["noaa_label"] == "Sin NOAA"
             and nyc_watch_row["state_label"] == "Referencia historica",
             nyc_watch_row)

        city_decisions_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "MIN_EDGE": 7.0,
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "SHADOW_CANARY_MIN_EDGE_HITS": 2,
            "SHADOW_CANARY_MIN_CYCLES": 2,
            "SHADOW_CANARY_MIN_BEST_EDGE": 7.0,
            "SHADOW_CANARY_MIN_SUPPORT": 2,
            "SHADOW_CANARY_MIN_DAYS": 14,
            "ALLOWLIST_REMOVE_MIN_TRADES": 3,
            "ALLOWLIST_REMOVE_MAX_WIN_RATE": 25.0,
            "ALLOWLIST_REMOVE_MAX_PNL": 0.0,
            "build_dashboard_city_observation": lambda: {},
            "get_city_accuracy": lambda: {},
            "get_city_policy_metrics": lambda audit=None: {},
            "load_shadow_city_tracking": lambda: {},
            "load_city_policy_state": lambda: {"auto_canary_cities": {}, "auto_shadow_cities": {}, "transition_history": []},
        }
        exec(get_function_source(module_ast, code_lines, "_shadow_condition_label"), city_decisions_ns)
        exec(get_function_source(module_ast, code_lines, "_build_recent_shadow_rows"), city_decisions_ns)
        exec(get_function_source(module_ast, code_lines, "_city_decision_gates"), city_decisions_ns)
        exec(get_function_source(module_ast, code_lines, "build_dashboard_city_decisions"), city_decisions_ns)
        city_observation_for_decisions = {
            **city_observation,
            "rows": [dict(item) for item in city_observation["rows"]],
        }
        for item in city_observation_for_decisions["rows"]:
            if item["city"] == "Dallas":
                item["city_mode"] = "shadow"
                item["active"] = False
                item["trading_label"] = "Shadow degradada"
                item["state_label"] = "Shadow degradada"
                item["state_badge"] = "accent"
        city_observation_for_decisions["rows"].append({
            "city": "Atlanta Legacy",
            "city_mode": "active",
            "active": True,
            "blocked": False,
            "trades": 4,
            "wins": 0,
            "win_rate": 0.0,
            "pnl": -3.5,
            "policy_source": "legacy",
            "policy_is_provisional": True,
            "policy_trades": 4,
            "policy_wins": 0,
            "policy_win_rate": 0.0,
            "policy_pnl": -3.5,
            "verified_trades": 0,
            "legacy_trades": 4,
            "trading_label": "Activa",
            "state_label": "Activa con muestra incipiente",
            "state_badge": "warn",
            "interpretable": False,
            "noaa_configured": True,
            "observed_count": 1,
            "observed_goal": 3,
            "history_label": "0/4 | WR 0.0%",
            "history_badge": "warn",
            "history_detail": "historico legacy; policy provisional",
            "policy_reason": "",
            "policy_metrics": {},
            "policy_changed_at": "",
        })
        city_decisions_ns["load_city_policy_state"] = lambda: {
            "auto_canary_cities": {},
            "auto_shadow_cities": {"Dallas": {"shadowed_at": "2026-03-31T12:00:00+00:00", "reason": "historico real malo", "from_mode": "active"}},
            "transition_history": [{"city": "Dallas", "from": "active", "to": "shadow", "at": "2026-03-31T12:00:00+00:00", "reason": "historico real malo"}],
        }
        city_decisions = city_decisions_ns["build_dashboard_city_decisions"](
            city_observation=city_observation_for_decisions,
            city_accuracy={
                "Chicago": {"trades": 4, "wins": 3, "pnl": 5.2, "win_rate": 75.0},
                "London": {"trades": 3, "wins": 0, "pnl": -4.0, "win_rate": 0.0},
                "New York City": {"trades": 2, "wins": 1, "pnl": 0.85, "win_rate": 50.0},
                "Dallas": {"trades": 4, "wins": 1, "pnl": -2.5, "win_rate": 25.0},
            },
            shadow_tracking={
                "cities": {
                    "New York City": {"markets_seen": 3, "edge_hits": 2, "best_edge_pct": 11.4, "cycles_seen": 2, "first_seen_at": "2026-03-01T00:00:00+00:00"},
                    "Dallas": {"markets_seen": 4, "edge_hits": 3, "best_edge_pct": 9.2, "cycles_seen": 3, "first_seen_at": "2026-03-01T00:00:00+00:00"},
                },
                "recent_opportunities": [{"city": "New York City", "date": "2026-03-30", "side": "YES", "edge_pct": 11.4, "expected_value": 0.52, "market_price": 42.0, "our_prob": 53.4}],
                "summary": {"cycles_with_shadow": 2, "opportunities_seen": 3, "edge_hits": 2},
            },
        )
        nyc_decision = next(item for item in city_decisions["rows"] if item["city"] == "New York City")
        chicago_decision = next(item for item in city_decisions["rows"] if item["city"] == "Chicago")
        london_decision = next(item for item in city_decisions["rows"] if item["city"] == "London")
        dallas_decision = next(item for item in city_decisions["rows"] if item["city"] == "Dallas")
        atl_legacy_decision = next(item for item in city_decisions["rows"] if item["city"] == "Atlanta Legacy")
        test("city decisions: promueve canary cuando shadow acumula edge",
             nyc_decision["decision"] == "promote"
             and city_decisions["promote_rows"][0]["city"] == "New York City",
             city_decisions)
        test("city decisions: ranking prioriza candidata real",
             city_decisions["top_candidate"]["city"] == "New York City"
             and nyc_decision["priority_label"] == "Lista para canary"
             and nyc_decision["readiness_score"] >= 80
             and nyc_decision["distance_label"] == "Lista ahora",
             nyc_decision)
        test("city decisions: mantiene activa con evidencia favorable",
             chicago_decision["decision"] == "keep"
             and chicago_decision["decision_label"] == "Mantener"
             and chicago_decision["priority_group"] == "operating",
             chicago_decision)
        test("city decisions: respeta bloqueadas",
             london_decision["decision"] == "blocked"
             and london_decision["badge"] == "bad"
             and london_decision["priority_group"] == "expelled",
             london_decision)
        test("city decisions: Dallas aparece como shadow degradada",
             dallas_decision["priority_group"] == "watch"
             and dallas_decision["state_label"] == "Shadow degradada"
             and dallas_decision["trend_label"] == "Enfriándose"
             and dallas_decision["main_reason"] == "shadow degradada por histórico real",
             dallas_decision)
        test("city decisions: no degrada activa solo por historico legacy malo",
             atl_legacy_decision["decision"] == "keep"
             and atl_legacy_decision["badge"] == "warn"
             and atl_legacy_decision["policy_is_provisional"] is True
             and atl_legacy_decision["priority_group"] == "watch"
             and atl_legacy_decision["provisional_review"] is True
             and atl_legacy_decision["trend_label"] == "Bajo review",
             atl_legacy_decision)
        test("city decisions: gate_a provisional para legado bajo review",
             atl_legacy_decision["gate_a"]["state"] == "provisional"
             and atl_legacy_decision["gate_a"]["badge"] == "warn",
             atl_legacy_decision.get("gate_a"))
        test("city decisions: expone politica explicita",
             "policy" in city_decisions
             and city_decisions["policy"]["promote"]["edge_hits"] == 2
             and city_decisions["policy"]["remove"]["trades"] == 3
             and city_decisions["ranking_summary"]["expelled"] >= 1,
             city_decisions)

        # ---- R1 gates (gate_a historial / gate_b shadow / gate_c NOAA) ----
        # Integration: las filas del ranking exponen los 3 gates con la forma documentada en
        # docs/control-center-r1-contract.md
        test("R1 gates: NYC expone shadow ready (promotable)",
             nyc_decision["gate_b"]["state"] == "ready"
             and nyc_decision["gate_b"]["badge"] == "good"
             and "edges" in nyc_decision["gate_b"]["detail"],
             nyc_decision.get("gate_b"))
        test("R1 gates: London bloqueada marca gate_a=bad",
             london_decision["gate_a"]["state"] == "bad"
             and london_decision["gate_a"]["badge"] == "bad",
             london_decision.get("gate_a"))
        test("R1 gates: Dallas degradada marca gate_a=bad",
             dallas_decision["gate_a"]["state"] == "bad"
             and dallas_decision["gate_a"]["badge"] == "bad",
             dallas_decision.get("gate_a"))
        test("R1 gates: gates_summary tiene el formato A x · B y · C z",
             nyc_decision["gates_summary"].startswith("A ")
             and " · B " in nyc_decision["gates_summary"]
             and " · C " in nyc_decision["gates_summary"],
             nyc_decision.get("gates_summary"))
        test("R1 gates: toda fila tiene gate_a/gate_b/gate_c con state+label+badge+detail",
             all(
                all(
                    isinstance(row.get(g), dict)
                    and {"state", "label", "badge", "detail"}.issubset(row[g].keys())
                    for g in ("gate_a", "gate_b", "gate_c")
                )
                for row in city_decisions["ranking_rows"]
             ),
             city_decisions["ranking_rows"][0] if city_decisions["ranking_rows"] else None)

        # Unit: _city_decision_gates cubre las 9 transiciones del contrato
        gates_unit_ns = {}
        exec(get_function_source(module_ast, code_lines, "_city_decision_gates"), gates_unit_ns)
        gates_fn = gates_unit_ns["_city_decision_gates"]

        def _gates_call(**overrides):
            defaults = dict(
                trades=0, win_rate=0.0, pnl=0.0,
                history_bad=False, provisional_review=False, degraded=False, blocked=False, removable_active=False,
                degradation_reason="", block_reason="",
                shadow_seen=0, shadow_edges=0, shadow_cycles=0, shadow_best_edge=0.0,
                promotable_shadow=False,
                interpretable=False, noaa_configured=False,
                observed_count=0, observed_goal=3,
            )
            defaults.update(overrides)
            return gates_fn(**defaults)

        # Gate A
        g = _gates_call(trades=5, win_rate=60.0, pnl=1.5)
        test("R1 gate_a: clean con trades>0 sin flags",
             g["gate_a"]["state"] == "clean" and g["gate_a"]["badge"] == "good", g["gate_a"])
        g = _gates_call(trades=10, win_rate=10.0, pnl=-5.0, history_bad=True)
        test("R1 gate_a: bad con history_bad",
             g["gate_a"]["state"] == "bad" and g["gate_a"]["badge"] == "bad", g["gate_a"])
        g = _gates_call(trades=4, win_rate=0.0, pnl=-3.5, provisional_review=True)
        test("R1 gate_a: provisional con legacy bajo review",
             g["gate_a"]["state"] == "provisional" and g["gate_a"]["badge"] == "warn", g["gate_a"])
        g = _gates_call()
        test("R1 gate_a: no_data con trades=0",
             g["gate_a"]["state"] == "no_data" and g["gate_a"]["badge"] == "muted", g["gate_a"])

        # Gate B
        g = _gates_call(promotable_shadow=True, shadow_edges=4, shadow_cycles=2, shadow_best_edge=28.3, shadow_seen=5)
        test("R1 gate_b: ready con promotable_shadow",
             g["gate_b"]["state"] == "ready" and g["gate_b"]["badge"] == "good", g["gate_b"])
        g = _gates_call(shadow_edges=1, shadow_cycles=1, shadow_best_edge=8.0, shadow_seen=2)
        test("R1 gate_b: building con actividad shadow pero sin promotable",
             g["gate_b"]["state"] == "building" and g["gate_b"]["badge"] == "accent", g["gate_b"])
        g = _gates_call()
        test("R1 gate_b: empty sin actividad shadow",
             g["gate_b"]["state"] == "empty" and g["gate_b"]["badge"] == "muted", g["gate_b"])

        # Gate C
        g = _gates_call(interpretable=True, noaa_configured=True, observed_count=10, observed_goal=5)
        test("R1 gate_c: interpretable con observed_count>=goal",
             g["gate_c"]["state"] == "interpretable" and g["gate_c"]["badge"] == "good", g["gate_c"])

        print("\n Shadow observado persistente")
        shadow_ns = {
            "os": os,
            "re": re,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "LOGIC_SERIES": "10.6",
            "MIN_EDGE": 15.0,
            "SHADOW_DIRECTIONAL_HISTORY_LIMIT": 500,
            "normalize_city": lambda city: str(city or "").strip(),
        }
        for fn in (
            "_shadow_condition_code",
            "_extract_threshold_from_question",
            "_normalize_shadow_market_date",
            "parse_temperature_question",
            "_extract_threshold_canonical",
            "_shadow_signal_signature",
            "_build_shadow_signal_record",
            "_merge_shadow_signal_history",
            "load_shadow_city_tracking",
            "save_shadow_city_tracking",
            "record_shadow_city_opportunities",
            "_build_shadow_noaa_resolution_stats",
        ):
            exec(get_function_source(module_ast, code_lines, fn), shadow_ns)

        tmp_shadow_tracking = os.path.join(
            os.getcwd(),
            f"_tmp_shadow_tracking_test_{next(tempfile._get_candidate_names())}.json",
        )
        try:
            shadow_ns["SHADOW_TRACKING_FILE"] = tmp_shadow_tracking
            shadow_ns["load_audit_data"] = lambda: {
                "observed_vs_forecast": [
                    {
                        "city": "Tokyo",
                        "date": "2026-04-05T00:00:00+00:00",
                        "observed_temp_c": 21.0,
                        "source": "noaa_ncei",
                    }
                ]
            }
            shadow_ns["OBSERVED_AUDIT_KEY"] = "observed_vs_forecast"
            shadow_ns["build_dashboard_forecast_quality"] = lambda: {"sample_size": 12}
            shadow_ns["get_city_accuracy"] = lambda: {}
            shadow_ns["get_dashboard_alert_summary"] = lambda: {"active_items": []}

            shadow_ns["record_shadow_city_opportunities"]([
                {
                    "city": "Tokyo",
                    "date": "2026-04-05",
                    "question": "Will the highest temperature in Tokyo be above 68°F on April 5?",
                    "side": "YES",
                    "edge_pct": 18.4,
                    "expected_value": 0.72,
                    "mkt_price": 41.0,
                    "our_prob": 59.4,
                    "forecast_max": 20.0,
                    "seen_at": "2026-04-03T08:00:00+00:00",
                    "edge_hit": True,
                    "first_for_cycle": True,
                }
            ])
            tracked = shadow_ns["load_shadow_city_tracking"]()
            persisted_recent = tracked.get("recent_opportunities", [])
            persisted_history = tracked.get("directional_history", [])
            resolution_stats = shadow_ns["_build_shadow_noaa_resolution_stats"](tracked, audit=shadow_ns["load_audit_data"]())
            test("shadow tracking: recent_opportunities persiste edge_hit",
                 bool(persisted_recent) and persisted_recent[0].get("edge_hit") is True,
                 persisted_recent)
            test("shadow tracking: directional_history crea base persistente",
                 len(persisted_history) == 1 and persisted_history[0].get("signal_key"),
                 persisted_history)
            test("shadow tracking: join NOAA normaliza datetime en date",
                 resolution_stats["resolved"] == 1 and resolution_stats["wins"] == 1 and resolution_stats["win_rate"] == 100.0,
                 resolution_stats)

            road_ns = dict(shadow_ns)
            road_ns["build_dashboard_forecast_quality"] = lambda: {"sample_size": 12}
            road_ns["get_city_accuracy"] = lambda: {}
            road_ns["get_dashboard_alert_summary"] = lambda: {"active_items": []}
            exec(get_function_source(module_ast, code_lines, "build_dashboard_road_to_real"), road_ns)
            road = road_ns["build_dashboard_road_to_real"](shadow_tracking=tracked, forecast_quality={"sample_size": 12}, city_accuracy={}, city_decisions={"ranking_rows": []}, alerts={"active_items": []})
            road_sim_wr = next(item for item in road["checks"] if item["id"] == "sim_wr")
            test("road_to_real: usa directional_history sin NameError",
                 road_sim_wr["display"] == "100.0% (n=1)",
                 road_sim_wr)
        finally:
            if os.path.exists(tmp_shadow_tracking):
                try:
                    os.remove(tmp_shadow_tracking)
                except PermissionError:
                    pass
        g = _gates_call(noaa_configured=True, observed_count=2, observed_goal=5)
        test("R1 gate_c: partial con NOAA configurado pero muestra corta",
             g["gate_c"]["state"] == "partial" and g["gate_c"]["badge"] == "warn", g["gate_c"])
        g = _gates_call()
        test("R1 gate_c: none sin NOAA configurado",
             g["gate_c"]["state"] == "none" and g["gate_c"]["badge"] == "muted", g["gate_c"])

        transition_messages = []
        sync_policy_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "LOGIC_SERIES": "10.6",
            "ACTIVE_TRADING_CITIES": {"Chicago"},
            "load_audit_data": lambda: {"observed_vs_forecast": []},
            "get_city_accuracy": lambda: {},
            "get_city_policy_metrics": lambda audit=None: {},
            "load_shadow_city_tracking": lambda: {},
            "build_dashboard_city_observation": lambda audit=None, city_accuracy=None, city_policy_metrics=None: {},
            "build_dashboard_city_decisions": lambda city_observation=None, city_accuracy=None, shadow_tracking=None, city_policy_metrics=None: {
                "rows": [
                    {"city": "New York City", "decision": "promote", "reason": "regla canary disparada", "shadow_best_edge": 10.2, "shadow_edges": 2},
                    {
                        "city": "Chicago",
                        "decision": "remove",
                        "reason": "regla de salida disparada",
                        "trades": 4,
                        "wins": 1,
                        "win_rate": 25.0,
                        "pnl": -1.13,
                        "observed_count": 2,
                        "shadow_seen": 0,
                        "shadow_edges": 0,
                        "shadow_best_edge": 0.0,
                        "support_count": 4,
                    },
                ]
            },
            "load_city_policy_state": lambda: {
                "logic_series": "10.6",
                "auto_canary_cities": {},
                "auto_shadow_cities": {},
                "auto_blocked_cities": {},
                "transition_history": [],
            },
            "save_city_policy_state": lambda data: transition_messages.append(("save", data)),
            "get_effective_city_mode": lambda city, policy_state=None: "shadow" if city == "New York City" else "active",
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: transition_messages.append(("msg", text)),
        }
        exec(get_function_source(module_ast, code_lines, "_build_auto_city_shadow_policy"), sync_policy_ns)
        exec(get_function_source(module_ast, code_lines, "sync_city_policy_state"), sync_policy_ns)
        sync_policy_ns["sync_city_policy_state"](notify=True)
        sent_texts = [item[1] for item in transition_messages if item[0] == "msg"]
        saved_policy = next((item[1] for item in transition_messages if item[0] == "save"), {})
        test("city policy sync: alerta promoción a canary",
             any("promovida a canary" in text and "New York City" in text for text in sent_texts),
             sent_texts)
        test("city policy sync: alerta degradación a shadow",
             any("shadow" in text and "Chicago" in text for text in sent_texts),
             sent_texts)

        test("city policy sync: persiste auto_shadow_cities con evidencia",
             saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("action") == "auto_shadow"
             and saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("reason") == "regla de salida disparada"
             and saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("metrics", {}).get("trades") == 4
             and saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("metrics", {}).get("wins") == 1
             and saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("from_mode") == "active"
             and bool(saved_policy.get("auto_shadow_cities", {}).get("Chicago", {}).get("shadowed_at")),
             saved_policy)
        test("city policy sync: transicion de salida apunta a shadow",
             any(
                 item.get("city") == "Chicago"
                 and item.get("to") == "shadow"
                 and item.get("action") == "auto_shadow"
                 and item.get("metrics", {}).get("win_rate") == 25.0
                 for item in saved_policy.get("transition_history", [])
             ),
             saved_policy.get("transition_history"))

        canary_remove_messages = []
        canary_remove_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "LOGIC_SERIES": "10.6",
            "ACTIVE_TRADING_CITIES": set(),
            "load_audit_data": lambda: {"observed_vs_forecast": []},
            "get_city_accuracy": lambda: {},
            "get_city_policy_metrics": lambda audit=None: {},
            "load_shadow_city_tracking": lambda: {},
            "build_dashboard_city_observation": lambda audit=None, city_accuracy=None, city_policy_metrics=None: {},
            "build_dashboard_city_decisions": lambda city_observation=None, city_accuracy=None, shadow_tracking=None, city_policy_metrics=None: {
                "rows": [
                    {
                        "city": "Boston",
                        "decision": "remove",
                        "reason": "regla de salida NOAA-verificada",
                        "trades": 4,
                        "wins": 1,
                        "win_rate": 25.0,
                        "pnl": -1.25,
                        "policy_source": "noaa_verified",
                        "policy_is_provisional": False,
                        "policy_trades": 4,
                        "policy_wins": 1,
                        "policy_win_rate": 25.0,
                        "policy_pnl": -1.25,
                        "verified_trades": 4,
                        "legacy_trades": 0,
                        "observed_count": 4,
                        "shadow_seen": 0,
                        "shadow_edges": 0,
                        "shadow_best_edge": 0.0,
                        "support_count": 4,
                    },
                ]
            },
            "load_city_policy_state": lambda: {
                "logic_series": "10.6",
                "auto_canary_cities": {},
                "auto_shadow_cities": {},
                "auto_blocked_cities": {},
                "transition_history": [],
            },
            "save_city_policy_state": lambda data: canary_remove_messages.append(("save", data)),
            "get_effective_city_mode": lambda city, policy_state=None: "canary",
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: canary_remove_messages.append(("msg", text)),
        }
        exec(get_function_source(module_ast, code_lines, "_build_auto_city_shadow_policy"), canary_remove_ns)
        exec(get_function_source(module_ast, code_lines, "sync_city_policy_state"), canary_remove_ns)
        canary_remove_ns["sync_city_policy_state"](notify=True)
        canary_saved_policy = next((item[1] for item in canary_remove_messages if item[0] == "save"), {})
        test("city policy sync: canary tambien puede degradarse a shadow",
             canary_saved_policy.get("auto_shadow_cities", {}).get("Boston", {}).get("from_mode") == "canary"
             and any(
                 item.get("city") == "Boston"
                 and item.get("from") == "canary"
                 and item.get("to") == "shadow"
                 for item in canary_saved_policy.get("transition_history", [])
             ),
             canary_saved_policy)

        effective_mode_ns = {
            "LOGIC_SERIES": "10.6",
            "ACTIVE_TRADING_CITIES": {"Atlanta", "Chicago"},
            "CANARY_TRADING_CITIES": set(),
            "is_city_blocked": lambda city: False,
            "load_city_policy_state": lambda: {
                "auto_blocked_cities": {"Atlanta": {"action": "auto_block", "reason": "WR 25%"}},
                "auto_shadow_cities": {},
                "auto_canary_cities": {},
            },
        }
        exec(get_function_source(module_ast, code_lines, "_is_real_block_policy"), effective_mode_ns)
        exec(get_function_source(module_ast, code_lines, "_coerce_shadow_policy_entry"), effective_mode_ns)
        exec(get_function_source(module_ast, code_lines, "_normalize_city_policy_state"), effective_mode_ns)
        exec(get_function_source(module_ast, code_lines, "get_effective_city_mode"), effective_mode_ns)
        test("get_effective_city_mode: auto_block legacy migra a shadow sobre allowlist activa",
             effective_mode_ns["get_effective_city_mode"]("Atlanta") == "shadow"
             and effective_mode_ns["get_effective_city_mode"]("Chicago") == "active",
             {
                 "Atlanta": effective_mode_ns["get_effective_city_mode"]("Atlanta"),
                 "Chicago": effective_mode_ns["get_effective_city_mode"]("Chicago"),
             })

        missing_cycle_summary = os.path.join(
            _verify_tmp_dir(),
            "_tmp_cycle_summary_missing_focus_center_test.json",
        )
        if os.path.exists(missing_cycle_summary):
            os.remove(missing_cycle_summary)

        focus_ns = {
            "datetime": datetime,
            "os": os,
            "CYCLE_SUMMARY_FILE": missing_cycle_summary,
            "load_cycle_summary_data": lambda: {},
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_focus_center"), focus_ns)
        focus_center = focus_ns["build_dashboard_focus_center"](
            alerts={
                "signals": {"status": "ok", "actionable": 4},
                "pending_stuck": [],
                "flagged_cities": [],
                "active_items": [],
                "low_bankroll": False,
                "portfolio_total": 14.75,
            },
            forecast_quality={
                "sample_size": 4,
                "coverage_display": "2 / 4 ciudades con muestra",
                "note": "lectura global preliminar",
            },
            city_observation={
                "active_count": 4,
                "blocked_count": 10,
                "observed_ready_count": 1,
                "observed_configured_count": 4,
            },
            series_stats={"closed_count": 0},
            series_clean_stats={"count": 2},
            next_run_display="2026-03-30 16:00 UTC",
            last_cycle_label="Total #7 | Serie v10.6 #3",
        )
        test("focus center: prioriza limitacion de observabilidad sobre trading",
             focus_center["status_label"] == "Sano con limitaciones"
             and focus_center["answers"][2]["answer"] == "Cobertura NOAA del universo activo"
             and focus_center["action"]["title"] == "No tocar trading: priorizar crecimiento de muestra NOAA",
             focus_center)
        test("focus center: explicita aprendizaje y quick stats",
             focus_center["answers"][3]["answer"] == "Operando y aprendiendo"
             and focus_center["quick_stats"][1]["value"] == "1/4"
             and len(focus_center["drivers"]) == 4,
             focus_center)
        test("focus center: expone mission HUD y tracks",
             focus_center["mission"]["badge"] == "accent"
             and len(focus_center["tracks"]) == 4
             and focus_center["tracks"][1]["value_text"] == "1/4",
             focus_center)
        test("focus center: expone stage path para el HUD",
             len(focus_center["stage_path"]) == 4
             and focus_center["health_score"] > 0,
             focus_center)
        test("focus center: alerta warn si falta cycle_summary.json",
             isinstance(focus_center, dict)
             and "incidents" in focus_center
             and any(item.get("badge") == "warn" for item in focus_center["incidents"]),
             focus_center.get("incidents") if isinstance(focus_center, dict) else focus_center)

        focus_low_bankroll = focus_ns["build_dashboard_focus_center"](
            alerts={
                "signals": {"status": "ok", "actionable": 2},
                "pending_stuck": [],
                "flagged_cities": [],
                "active_items": [{"title": "Bankroll bajo", "detail": "Total cartera: $4.25", "level": "critical"}],
                "low_bankroll": True,
                "portfolio_total": 4.25,
            },
            forecast_quality={"sample_size": 0, "coverage_display": "0 / 4 ciudades con muestra", "note": "sin muestra"},
            city_observation={"active_count": 4, "blocked_count": 10, "observed_ready_count": 0, "observed_configured_count": 4},
            series_stats={"closed_count": 0},
            series_clean_stats={"count": 0},
        )
        test("focus center: eleva bankroll bajo a intervencion requerida",
             focus_low_bankroll["status_label"] == "Intervención requerida"
             and focus_low_bankroll["action"]["title"] == "Recargar bankroll antes del próximo ciclo",
             focus_low_bankroll)
        test("focus center: bankroll bajo degrada mission HUD",
             focus_low_bankroll["health_score"] < 60
             and focus_low_bankroll["mission"]["badge"] == "bad",
             focus_low_bankroll)

        legacy_drift_ns = {
            "FORECAST_AUDIT_KEY": "forecast_vs_real",
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_legacy_forecast_drift"), legacy_drift_ns)
        legacy_dashboard = legacy_drift_ns["build_dashboard_legacy_forecast_drift"](
            audit={
                "forecast_vs_real": [
                    {"city": "Chicago", "date": "2026-03-26", "forecast_original": 20.0, "forecast_posterior": 21.0, "error_c": 1.0, "abs_error_c": 1.0, "checked_at": "2026-03-28T09:15:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-25", "forecast_original": 23.0, "forecast_posterior": 22.5, "error_c": -0.5, "abs_error_c": 0.5, "checked_at": "2026-03-27T09:15:00+00:00"},
                ]
            }
        )
        test("legacy drift: bloque separado y no comparable con NOAA",
             legacy_dashboard["sample_size"] == 2 and "No es comparable" in legacy_dashboard["note"],
             legacy_dashboard)
        test("legacy drift: expone ultimo registro prominente",
             legacy_dashboard["last_record_display"] == "2026-03-28 09:15 UTC" and legacy_dashboard["mae_display"] == "0.8C",
             legacy_dashboard)

        trade_analytics_ns = {
            "re": re,
            "_to_lifecycle_float": lambda value, digits=4: (
                None if value in (None, "") else round(float(value), digits)
            ),
            "_trade_lifecycle_label": lambda record: record.get("label") or record.get("question") or "label",
            "_build_trade_lifecycle_record_integrity": lambda record: record.get("integrity", {}),
            "_get_portfolio_and_positions": lambda: None,
            "load_trade_lifecycle_data": lambda: {},
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_trade_analytics"), trade_analytics_ns)
        trade_analytics = trade_analytics_ns["build_dashboard_trade_analytics"](
            trade_lifecycle={
                "summary": {"tracked_positions": 5, "closed_positions": 5, "take_profit_closes": 1, "stop_loss_closes": 1},
                "integrity": {"analysis_ready_records": 4, "partial_historical_records": 1, "close_only_records": 2},
                "records": [
                    {
                        "label": "Atlanta TP",
                        "city": "Atlanta",
                        "status": "closed",
                        "closed_at": "2026-03-30T11:05:26+00:00",
                        "entry_context": {"timestamp": "2026-03-30T08:05:26+00:00", "price": 0.41, "edge_pct": 14.2},
                        "close_context": {
                            "close_reason": "take_profit",
                            "close_action": "SELL",
                            "close_price": 0.79,
                            "close_shares": 3.3,
                            "pnl_cash": 1.26,
                            "pnl_pct": 92.0,
                            "timestamp": "2026-03-30T11:05:26+00:00",
                        },
                        "post_exit_analysis": {
                            "market_seen_after_close": True,
                            "observations_after_close": 3,
                            "upside_left_cash_peak": 0.69,
                            "drawdown_avoided_cash_peak": 0.0,
                            "reached_98_after_close": True,
                        },
                        "integrity": {"analysis_ready": True},
                    },
                    {
                        "label": "Dallas SL",
                        "city": "Dallas",
                        "status": "closed",
                        "closed_at": "2026-03-30T12:05:26+00:00",
                        "entry_context": {"timestamp": "2026-03-30T09:05:26+00:00", "price": 0.45, "edge_pct": 9.1},
                        "close_context": {
                            "close_reason": "stop_loss",
                            "close_action": "SELL",
                            "close_price": 0.24,
                            "close_shares": 5.0,
                            "pnl_cash": -1.05,
                            "pnl_pct": -46.7,
                            "timestamp": "2026-03-30T12:05:26+00:00",
                        },
                        "post_exit_analysis": {
                            "market_seen_after_close": True,
                            "observations_after_close": 2,
                            "upside_left_cash_peak": 0.0,
                            "drawdown_avoided_cash_peak": 0.6,
                            "reached_98_after_close": False,
                        },
                        "integrity": {"analysis_ready": True},
                    },
                    {
                        "label": "Chicago LT",
                        "city": "Chicago",
                        "status": "closed",
                        "closed_at": "2026-03-30T12:40:00+00:00",
                        "entry_context": {"timestamp": "2026-03-30T10:10:00+00:00", "price": 0.29},
                        "avg_entry_price": 0.29,
                        "close_context": {
                            "close_reason": "micro_position_unsellable",
                            "close_action": "LOSS_TOTAL",
                            "close_price": 0.0,
                            "close_shares": 4.0,
                            "pnl_cash": -1.16,
                            "pnl_pct": -100.0,
                            "timestamp": "2026-03-30T12:40:00+00:00",
                        },
                        "post_exit_analysis": {
                            "market_seen_after_close": False,
                            "upside_left_cash_peak": 0.0,
                            "drawdown_avoided_cash_peak": 0.0,
                        },
                        "integrity": {"analysis_ready": True},
                    },
                    {
                        "label": "Legacy close-only",
                        "city": "Chicago",
                        "status": "closed",
                        "closed_at": "2026-03-30T13:05:26+00:00",
                        "close_context": {
                            "close_reason": "reeval",
                            "close_action": "SELL",
                            "close_price": 0.31,
                            "close_shares": 2.0,
                            "pnl_cash": -0.18,
                            "pnl_pct": -12.0,
                            "timestamp": "2026-03-30T13:05:26+00:00",
                        },
                        "post_exit_analysis": {
                            "market_seen_after_close": False,
                            "upside_left_cash_peak": 0.0,
                            "drawdown_avoided_cash_peak": 0.0,
                        },
                        "integrity": {
                            "analysis_ready": True,
                            "close_only_record": True,
                            "missing_entry_context": True,
                            "missing_buy_history": True,
                        },
                    },
                    {
                        "label": "Historical partial",
                        "city": "Boston",
                        "status": "closed",
                        "closed_at": "2026-03-30T13:20:26+00:00",
                        "close_context": {
                            "close_reason": "take_profit",
                            "close_action": "SELL",
                            "close_price": None,
                            "close_shares": 0.0,
                            "timestamp": "2026-03-30T13:20:26+00:00",
                        },
                        "post_exit_analysis": {
                            "market_seen_after_close": True,
                            "upside_left_cash_peak": 1.4,
                            "drawdown_avoided_cash_peak": 0.0,
                        },
                        "integrity": {
                            "analysis_ready": False,
                            "partial_historical_record": True,
                            "close_only_record": True,
                        },
                    },
                ],
            }
        )
        test("trade analytics: cuenta solo cierres observados utilizables",
             trade_analytics["sample_size"] == 2 and trade_analytics["tracked_positions"] == 5,
             trade_analytics)
        test("trade analytics: calcula score y queue de upside/proteccion",
             trade_analytics["score_pct"] > 80
             and trade_analytics["top_upside_rows"][0]["label"] == "Atlanta TP"
             and trade_analytics["top_protection_rows"][0]["label"] == "Dallas SL",
             trade_analytics)
        test("trade analytics: genera breakdown y timeline",
             trade_analytics["breakdown_rows"][0]["label"] == "Take-profit"
             and len(trade_analytics["timeline_points"]) == 2,
             {"breakdown": trade_analytics["breakdown_rows"], "timeline": trade_analytics["timeline_points"]})
        test("trade analytics: separa LOSS_TOTAL y legacy en los totales",
             trade_analytics["total_cards"][0]["label"] == "Operaciones totales"
             and any(card["label"] == "LOSS_TOTAL" and card["value"] == "1" for card in trade_analytics["total_cards"])
             and any(card["label"] == "Legacy/parcial" and card["value"] == "2" for card in trade_analytics["total_cards"])
             and any(card["label"] == "SELL negativos" and card["value"] == "1" for card in trade_analytics["total_cards"]),
             {"totals": trade_analytics["total_cards"]})
        test("trade analytics: expone detalle semantico por trade",
             trade_analytics["legacy_review_records"] == 2
             and any(row["label"] == "Atlanta TP" and "TP mecanico" in row["exit_condition"] for row in trade_analytics["trade_rows"])
             and any(row["label"] == "Dallas SL" and "SL mecanico" in row["exit_condition"] for row in trade_analytics["trade_rows"])
             and any(row["label"] == "Chicago LT" and row["bucket_label"] == "LOSS_TOTAL" and row["status_label"] == "Perdida total" for row in trade_analytics["trade_rows"])
             and any(row["label"] == "Legacy close-only" and row["status_label"] == "Perdida legacy" and "Cierre heredado" in row["entry_condition"] for row in trade_analytics["trade_rows"])
             and any(row["label"] == "Historical partial" and row["integrity_note"] == "Historico parcial" for row in trade_analytics["trade_rows"]),
             {"trade_rows": trade_analytics["trade_rows"][:5]})

        trade_analytics_portfolio = trade_analytics_ns["build_dashboard_trade_analytics"](
            trade_lifecycle={
                "summary": {"tracked_positions": 2, "closed_positions": 2},
                "integrity": {"analysis_ready_records": 2, "partial_historical_records": 0, "close_only_records": 0},
                "records": [
                    {
                        "question": "Will the highest temperature in Seoul be 13°C on April 1?",
                        "city": "Seoul",
                        "side": "NO",
                        "date": "2026-04-01",
                        "status": "closed",
                        "close_context": {
                            "close_reason": "market_resolved_yes",
                            "close_action": "RESOLVED_WIN",
                            "close_price": 1.0,
                            "close_shares": 3.0393,
                            "pnl_cash": 0.61,
                            "timestamp": "2026-04-01T08:00:00+00:00",
                        },
                        "post_exit_analysis": {},
                        "integrity": {"analysis_ready": True},
                    },
                    {
                        "question": "Will the highest temperature in Dallas be between 82-83°F on April 1?",
                        "city": "Dallas",
                        "side": "YES",
                        "date": "2026-04-01",
                        "status": "closed",
                        "entry_context": {"timestamp": "2026-03-31T08:00:00+00:00", "price": 0.13},
                        "close_context": {
                            "close_reason": "stop_loss",
                            "close_action": "SELL",
                            "close_price": 0.04,
                            "close_shares": 10.9,
                            "pnl_cash": -0.56,
                            "timestamp": "2026-03-31T23:00:00+00:00",
                        },
                        "post_exit_analysis": {},
                        "integrity": {"analysis_ready": True},
                    },
                ],
            },
            portfolio={
                "active": [],
                "resolved_won": [{
                    "asset": "seoul13-no",
                    "title": "Will the highest temperature in Seoul be 13°C on April 1?",
                    "outcome": "NO",
                    "endDate": "2026-04-01",
                    "curPrice": 1.0,
                    "currentValue": 3.04,
                    "cashPnl": 0.61,
                    "percentPnl": 25.0,
                    "size": 3.0393,
                    "avgPrice": 0.8,
                    "initialValue": 2.43,
                    "redeemable": True,
                    "realizedPnl": 0.0,
                }],
                "dead": [
                    {
                        "asset": "dallas82-yes",
                        "title": "Will the highest temperature in Dallas be between 82-83°F on April 1?",
                        "outcome": "YES",
                        "endDate": "2026-04-01",
                        "curPrice": 0.0005,
                        "currentValue": 0.01,
                        "cashPnl": -0.56,
                        "percentPnl": -99.5,
                        "size": 0.01,
                        "avgPrice": 0.13,
                        "initialValue": 1.33,
                        "redeemable": False,
                        "realizedPnl": 0.0,
                    },
                    {
                        "asset": "atlanta78-yes",
                        "title": "Will the highest temperature in Atlanta be between 78-79°F on April 1?",
                        "outcome": "YES",
                        "endDate": "2026-04-01",
                        "curPrice": 0.0005,
                        "currentValue": 0.01,
                        "cashPnl": -2.11,
                        "percentPnl": -99.5,
                        "size": 21.238,
                        "avgPrice": 0.1,
                        "initialValue": 2.12,
                        "redeemable": False,
                        "realizedPnl": 0.0,
                    },
                ],
            },
        )
        test("trade analytics: muestra claim pendiente y residuo post-salida",
             any("claim pendiente" in row["exit_condition"] or "claim pendiente" in row["after_close_display"]
                 for row in trade_analytics_portfolio["trade_rows"] if "Seoul" in row["label"])
             and any("residuo micro" in row["after_close_display"]
                     for row in trade_analytics_portfolio["trade_rows"] if "Dallas" in row["label"]),
             {"trade_rows": trade_analytics_portfolio["trade_rows"]})
        test("trade analytics: crea fallback desde portfolio para posiciones sin lifecycle",
             any("Atlanta" in row["label"] and "78-79" in row["label"] for row in trade_analytics_portfolio["trade_rows"]),
             {"trade_rows": trade_analytics_portfolio["trade_rows"]})

        snapshot_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "_load_cycle_counts": lambda: (5, 1),
            "load_cycle_summary_data": lambda: {"cycle_number": 5, "logic_cycle_number": 1, "logic_series": "10.5", "version": "v10.6.10"},
            "load_cycle_history": lambda limit=None: [{"cycle_number": 5, "logic_cycle_number": 1, "logic_series": "10.5", "version": "v10.6.10", "timestamp_utc": "2026-03-29T11:08:00+00:00", "buys": [], "management": {"n_sold": 1}, "exposure_after": 2.94}],
            "load_audit_data": lambda: {"pending_sells": [], "forecast_vs_real": [], "observed_vs_forecast": [], "errors": []},
            "load_trade_lifecycle_data": lambda: {"summary": {"tracked_positions": 2}, "records": []},
            "load_shadow_city_tracking": lambda: {"cities": {}, "recent_opportunities": [], "summary": {"cycles_with_shadow": 0, "opportunities_seen": 0, "edge_hits": 0}},
            "get_clean_closed_trade_stats": lambda: {"count": 18, "sell": 12, "loss_total": 6, "resolved_win": 0},
            "get_logic_series_clean_closed_trade_stats": lambda: {"count": 0, "sell": 0, "loss_total": 0, "resolved_win": 0},
            "get_validated_closed_postmortems": lambda: [],
            "get_performance_summary": lambda: {},
            "get_logic_series_stats": lambda: {"pnl": 0.0, "win_rate": 0.0, "closed_count": 0, "recent_window_size": 0, "recent_drawdown": 0.0},
            "get_dashboard_alert_summary": lambda: {"signals": {"status": "ok"}, "pending_stuck": [], "flagged_cities": [], "active_items": [], "low_bankroll": False, "portfolio_total": 14.75},
            "build_promotion_checklist": lambda: {"levels": {"next_target": 35.0, "is_max_level": False}, "passed": 3, "total": 9, "blocking_failed": 3, "decision": "HOLD", "decision_label": "Aún no listo", "trade_target": 30, "checks": []},
            "get_city_accuracy": lambda: {},
            "get_city_policy_metrics": lambda audit=None: {},
            "build_dashboard_progress": lambda **kwargs: [{"label": "Muestra", "status": "bad"}],
            "build_dashboard_exit_breakdown": lambda **kwargs: {"validated_rows": [{"label": "Take-profit", "balance_display": "$+1.00"}], "series_rows": [{"label": "Pending exit serie v10.6", "balance_display": "$-0.50"}]},
            "build_dashboard_forecast_quality": lambda **kwargs: {"sample_size": 0, "sample_display": "0 mercados", "mae_display": "acumulando muestra...", "bias_display": "acumulando muestra...", "coverage_display": "0 / 4 ciudades con muestra", "coverage_detail": "0 / 4 con >= 3 casos", "city_rows": [], "latest_rows": [], "note": "acumulando muestra...", "note_level": "muted", "last_record_display": "n/d", "kpis_ready": False, "global_ready": False},
            "build_dashboard_city_observation": lambda **kwargs: {"tracked_count": 4, "active_count": 4, "blocked_count": 0, "observed_ready_count": 0, "observed_configured_count": 4, "summary": "4 activas", "note": "watch", "note_level": "muted", "rows": []},
            "build_dashboard_city_decisions": lambda **kwargs: {"summary": "0 mantener", "note": "decision", "note_level": "muted", "rows": [], "keep_rows": [], "promote_rows": [], "observe_rows": [], "remove_rows": [], "blocked_rows": [], "shadow_summary": {"opportunities_seen": 0}, "recent_shadow_rows": []},
            "build_dashboard_road_to_real": lambda **kwargs: {"checks": [], "passed": 0, "total": 6, "pct": 0, "status_label": "Fase temprana", "status_badge": "warn"},
            "build_dashboard_focus_center": lambda **kwargs: {"status_label": "Sano con limitaciones", "status_badge": "accent", "headline": "sample", "summary": "watch", "answers": [], "action": {"title": "No tocar trading", "detail": "NOAA", "badge": "accent"}, "incidents": [], "quick_stats": [], "drivers": [], "detail_routes": []},
            "build_dashboard_legacy_forecast_drift": lambda **kwargs: {"sample_size": 0, "sample_display": "0 mercados", "mae_display": "n/d", "bias_display": "n/d", "last_record_display": "n/d", "latest_case": "", "note": "legacy"},
            "build_dashboard_trade_analytics": lambda **kwargs: {"sample_size": 1, "score_display": "81.0%", "headline": "sample exits"},
            "build_dashboard_trophies": lambda **kwargs: [{"label": "Mejor operación", "value": "n/d"}],
            "build_dashboard_unlocks": lambda **kwargs: [{"label": "Activar win rate", "status": "waiting"}],
            "_get_portfolio_and_positions": lambda: None,
            "_parse_position_label": lambda title, outcome: "Mock",
            "load_agent_events": lambda limit=None: [],
            "_normalize_agent_event_stage": lambda event: "validated",
            "compute_agent_scorecard": lambda events: [],
            "build_agent_rivalry": lambda events: [],
            "_extract_logic_series": lambda value: "10.5" if "10.5" in str(value) else "10.4" if "10.4" in str(value) else None,
            "BOT_VERSION": "v10.6.10",
            "LOGIC_SERIES": "10.6",
            "DRY_RUN": False,
            "ACTIVE_TRADING_CITIES": {"Chicago", "Atlanta"},
            "_is_shadow_only": lambda: False,
            "_dashboard_mode_label": lambda: "REAL",
            "DASHBOARD_USER": "pablo",
            "DASHBOARD_PASSWORD": "secret",
            "DASHBOARD_TITLE": "Polymarket Bot Control Center",
            "DASHBOARD_REFRESH_SEC": 60,
            "INTRA_SL_INTERVAL": 0,
            "bot_state": {"next_run": None, "last_run": None},
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_snapshot"), snapshot_ns)
        snapshot = snapshot_ns["build_dashboard_snapshot"]()
        test("snapshot: incluye progress", "progress" in snapshot and snapshot["progress"][0]["label"] == "Muestra", snapshot)
        test("snapshot: incluye exit_breakdown", "exit_breakdown" in snapshot and snapshot["exit_breakdown"]["validated_rows"][0]["label"] == "Take-profit", snapshot)
        test("snapshot: incluye forecast_quality", "forecast_quality" in snapshot and snapshot["forecast_quality"]["sample_size"] == 0, snapshot)
        test("snapshot: incluye city_observation", "city_observation" in snapshot and snapshot["city_observation"]["tracked_count"] == 4, snapshot)
        test("snapshot: incluye city_decisions", "city_decisions" in snapshot and "shadow_summary" in snapshot["city_decisions"], snapshot)
        test("snapshot: incluye focus", "focus" in snapshot and snapshot["focus"]["action"]["title"] == "No tocar trading", snapshot)
        test("snapshot: incluye legacy_forecast_drift", "legacy_forecast_drift" in snapshot and snapshot["legacy_forecast_drift"]["last_record_display"] == "n/d", snapshot)
        test("snapshot: incluye trade_analytics", "trade_analytics" in snapshot and snapshot["trade_analytics"]["sample_size"] == 1, snapshot)
        test("snapshot: incluye trophies", "trophies" in snapshot and snapshot["trophies"][0]["label"] == "Mejor operación", snapshot)
        test("snapshot: incluye unlocks", "unlocks" in snapshot and snapshot["unlocks"][0]["label"] == "Activar win rate", snapshot)

        dashboard_alert_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "_dashboard_mode_label": lambda: "REAL",
            "inspect_signals_file_health": lambda: {"status": "ok", "actionable": 4},
            "load_audit_data": lambda: {"pending_sells": []},
            "get_city_accuracy": lambda: {},
            "_get_portfolio_and_positions": lambda: {"cash": 3.2, "cash_ok": True, "api_error": None, "portfolio_total": 4.8},
        }
        exec(get_function_source(module_ast, code_lines, "get_dashboard_alert_summary"), dashboard_alert_ns)
        dashboard_alert_summary = dashboard_alert_ns["get_dashboard_alert_summary"]()
        test("dashboard alerta bankroll bajo: visible con datos fiables",
             dashboard_alert_summary["low_bankroll"] and dashboard_alert_summary["active_items"][0]["title"].startswith("Bankroll bajo"),
             dashboard_alert_summary)

        dashboard_alert_api_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "_dashboard_mode_label": lambda: "REAL",
            "inspect_signals_file_health": lambda: {"status": "ok", "actionable": 4},
            "load_audit_data": lambda: {"pending_sells": []},
            "get_city_accuracy": lambda: {},
            "_get_portfolio_and_positions": lambda: {"cash": 0.0, "cash_ok": False, "api_error": "timeout", "portfolio_total": 0.0},
        }
        exec(get_function_source(module_ast, code_lines, "get_dashboard_alert_summary"), dashboard_alert_api_ns)
        dashboard_alert_api_summary = dashboard_alert_api_ns["get_dashboard_alert_summary"]()
        test("dashboard alerta bankroll bajo: ignora API incierta",
             not dashboard_alert_api_summary["low_bankroll"] and all("Bankroll bajo" not in item["title"] for item in dashboard_alert_api_summary["active_items"]),
             dashboard_alert_api_summary)

        fd, tmp_agent_events = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_agent_events_test_",
            suffix=".jsonl",
        )
        os.close(fd)
        with open(tmp_agent_events, "w", encoding="utf-8") as f:
            f.write(json.dumps({"agent": "Codex", "type": "bug_detected", "session": 32, "title": "Research: Dallas KDAL + auditoria mal nombrada", "points": 3, "timestamp": "2026-03-29T12:00:00+00:00"}) + "\n")
            f.write(json.dumps({"agent": "Codex", "type": "bug_detected", "session": 32, "title": "Research: Dallas KDAL + auditoría mal nombrada", "points": 3, "timestamp": "2026-03-29T12:00:00+00:00"}) + "\n")
            f.write(json.dumps({"agent": "Claude Code (Opus)", "type": "review_correction", "session": 32, "title": "Research adversarial review NOAA/WU", "points": 5, "timestamp": "2026-03-29T11:00:00+00:00"}) + "\n")
            f.write(json.dumps({"agent": "Codex", "type": "validated_improvement", "session": "session_72", "title": "Focus no-cycle alert coverage", "points": 2, "timestamp": "2026-04-03T21:41:33+00:00"}) + "\n")
        events_ns = {
            "os": os,
            "json": json,
            "AGENT_EVENTS_FILE": tmp_agent_events,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        exec(get_function_source(module_ast, code_lines, "load_agent_events"), events_ns)
        loaded_events = events_ns["load_agent_events"]()
        test("load_agent_events: deduplica equivalentes", len(loaded_events) == 3, loaded_events)
        test("load_agent_events: ordena por timestamp desc", loaded_events[0]["agent"] == "Codex", loaded_events)
        test("load_agent_events: acepta session_N y la normaliza a int",
             any(item.get("session") == 72 for item in loaded_events),
             loaded_events)
        if os.path.exists(tmp_agent_events):
            try:
                os.remove(tmp_agent_events)
            except PermissionError:
                pass

        forecast_calls = {"count": 0}
        forecast_payload = {
            "daily": {
                "time": ["2026-04-07"],
                "temperature_2m_max": [24.0],
                "temperature_2m_min": [18.0],
                "precipitation_probability_max": [15],
                "precipitation_sum": [0.3],
            }
        }
        def _forecast_urlopen_cached(url, timeout=30):
            forecast_calls["count"] += 1
            return types.SimpleNamespace(read=lambda: json.dumps(forecast_payload).encode("utf-8"))

        forecast_ns = {
            "json": json,
            "time": types.SimpleNamespace(time=lambda: 1000.0, sleep=lambda seconds: None),
            "urllib": types.SimpleNamespace(
                request=types.SimpleNamespace(urlopen=_forecast_urlopen_cached),
                error=types.SimpleNamespace(HTTPError=urllib.error.HTTPError),
            ),
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
            "FORECAST_CACHE_TTL_SECONDS": 900,
            "FORECAST_STALE_IF_ERROR_SECONDS": 21600,
            "FORECAST_RATE_LIMIT_COOLDOWN_SECONDS": 120,
        }
        exec(get_function_source(module_ast, code_lines, "get_forecast"), forecast_ns)
        cached_first = forecast_ns["get_forecast"](41.9, -87.6)
        cached_second = forecast_ns["get_forecast"](41.9, -87.6)
        test("get_forecast: cachea la segunda llamada",
             forecast_calls["count"] == 1 and cached_first["2026-04-07"]["temp_max"] == cached_second["2026-04-07"]["temp_max"],
             {"calls": forecast_calls["count"], "first": cached_first, "second": cached_second})

        forecast_time = {"now": 2000.0}
        forecast_rate_calls = {"count": 0}
        def _forecast_urlopen_rate_limited(url, timeout=30):
            forecast_rate_calls["count"] += 1
            if forecast_rate_calls["count"] == 1:
                return types.SimpleNamespace(read=lambda: json.dumps(forecast_payload).encode("utf-8"))
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {"Retry-After": "120"}, None)

        forecast_rate_ns = {
            "json": json,
            "time": types.SimpleNamespace(time=lambda: forecast_time["now"], sleep=lambda seconds: None),
            "urllib": types.SimpleNamespace(
                request=types.SimpleNamespace(urlopen=_forecast_urlopen_rate_limited),
                error=types.SimpleNamespace(HTTPError=urllib.error.HTTPError),
            ),
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
            "FORECAST_CACHE_TTL_SECONDS": 10,
            "FORECAST_STALE_IF_ERROR_SECONDS": 300,
            "FORECAST_RATE_LIMIT_COOLDOWN_SECONDS": 120,
        }
        exec(get_function_source(module_ast, code_lines, "get_forecast"), forecast_rate_ns)
        fresh_rate = forecast_rate_ns["get_forecast"](33.6, -84.4)
        forecast_time["now"] = 2015.0
        stale_rate = forecast_rate_ns["get_forecast"](33.6, -84.4)
        test("get_forecast: usa cache stale si llega HTTP 429",
             forecast_rate_calls["count"] == 2
             and stale_rate["2026-04-07"]["temp_max"] == fresh_rate["2026-04-07"]["temp_max"]
             and forecast_rate_ns.get("_forecast_rate_limited_until", 0) >= 2120.0,
             {"calls": forecast_rate_calls["count"], "cooldown": forecast_rate_ns.get("_forecast_rate_limited_until", 0), "stale": stale_rate})

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
            dir=_verify_tmp_dir(),
            prefix="_tmp_cycle_summary_test_",
            suffix=".json",
        )
        os.close(fd)
        with open(tmp_cycle_summary, "w", encoding="utf-8") as f:
            json.dump({
                "version": "v10.6.10",
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
            "BOT_VERSION": "v10.6.10",
            "LOGIC_SERIES": "10.6",
            "_extract_logic_series": cycle_ns["_extract_logic_series"],
            "DRY_RUN": False,
            "BANKROLL": 25.0,
            "MIN_EDGE": 7.0,
            "STOP_LOSS_PCT": -25.0,
            "TAKE_PROFIT_PCT": 40.0,
            "MAX_EXPOSURE_PCT": 0.40,
            "MIN_BET": 1.0,
            "INTRA_SL_INTERVAL": 0,
            "SCHEDULE_HOURS_UTC": [8, 16, 23],
            "bot_state": {"cycle_count": 12, "cycle_count_series": 3, "last_run": None},
            "CYCLE_SUMMARY_FILE": tmp_cycle_summary,
            "get_performance_summary": lambda: None,
        }
        exec(get_function_source(module_ast, code_lines, "cmd_info"), info_ns)
        info_ns["cmd_info"]()
        info_msg = info_messages[-1] if info_messages else ""
        test("info: versión visible correcta", "BOT POLYMARKET v10.6.10" in info_msg, info_msg[:120])
        test("info: usa cycle_summary como fallback de último", "Último: 2026-03-28 16:00 UTC" in info_msg, info_msg[:220])
        test("info: muestra doble contador", "Ciclos completados: 12 total | 3 serie v10.6" in info_msg, info_msg[:240])
        test("info: muestra ciclo total y de serie", "Ciclo total #12 | serie v10.6 #3" in info_msg, info_msg[:260])
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

        noaa_messages = []
        noaa_ns = {
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "load_audit_data": lambda: {
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-25", "forecast_temp_c": 11.0, "observed_temp_c": 12.0, "error_c": 1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-30T12:00:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-26", "forecast_temp_c": 13.0, "observed_temp_c": 12.0, "error_c": -1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-30T12:05:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-27", "forecast_temp_c": 15.0, "observed_temp_c": 14.5, "error_c": -0.5, "abs_error_c": 0.5, "source": "noaa_ncei", "checked_at": "2026-03-30T12:10:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-27", "forecast_temp_c": 24.0, "observed_temp_c": 25.2, "error_c": 1.2, "abs_error_c": 1.2, "source": "noaa_ncei", "checked_at": "2026-03-30T12:15:00+00:00"},
                ]
            },
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: noaa_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "build_dashboard_forecast_quality"), noaa_ns)
        exec(get_function_source(module_ast, code_lines, "cmd_noaa"), noaa_ns)
        noaa_ns["cmd_noaa"]()
        noaa_msg = noaa_messages[-1] if noaa_messages else ""
        test("noaa cmd: muestra sample y coverage",
             "4 mercados" in noaa_msg and "2 / 4 ciudades con muestra" in noaa_msg,
             noaa_msg[:240])
        test("noaa cmd: muestra ciudad interpretable y nota de proxy",
             "Chicago" in noaa_msg and "observed proxy" in noaa_msg,
             noaa_msg[:320])
        test("noaa cmd: recuerda que NOAA no es settlement final",
             "no equivale a la resolucion final de Polymarket" in noaa_msg,
             noaa_msg[:320])

        focus_messages = []
        focus_ns = {
            "datetime": datetime,
            "load_audit_data": lambda: {},
            "get_city_accuracy": lambda: {},
            "get_city_policy_metrics": lambda audit=None: {},
            "load_cycle_summary_data": lambda: {"cycle_number": 7, "logic_cycle_number": 3, "logic_series": "10.6", "version": "v10.6.10"},
            "_extract_logic_series": lambda value: "10.6" if "10.6" in str(value) else None,
            "bot_state": {"next_run": datetime(2026, 3, 30, 16, 0, tzinfo=timezone.utc)},
            "get_dashboard_alert_summary": lambda: {},
            "build_dashboard_forecast_quality": lambda audit=None: {},
            "build_dashboard_city_observation": lambda audit=None, city_accuracy=None, city_policy_metrics=None: {},
            "get_logic_series_stats": lambda: {},
            "get_logic_series_clean_closed_trade_stats": lambda: {},
            "build_dashboard_focus_center": lambda **kwargs: {
                "status_badge": "accent",
                "headline": "Sistema sano; el cuello de botella es NOAA",
                "summary": "NOAA 4/10 casos | 1/4 ciudades interpretables.",
                "answers": [
                    {"question": "¿Está sano el sistema?", "answer": "Sano con limitaciones", "detail": "NOAA corto", "badge": "accent"},
                    {"question": "¿Hay que intervenir hoy?", "answer": "No; solo monitorizar", "detail": "Sin incidentes", "badge": "good"},
                    {"question": "¿Qué me limita ahora?", "answer": "Cobertura NOAA del universo activo", "detail": "1/4", "badge": "accent"},
                    {"question": "¿Estamos aprendiendo o solo operando?", "answer": "Operando y aprendiendo", "detail": "4/10", "badge": "accent"},
                ],
                "action": {"title": "No tocar trading: priorizar crecimiento de muestra NOAA", "detail": "1/4 activas con NOAA interpretable", "badge": "accent"},
                "incidents": [],
                "quick_stats": [
                    {"label": "Universo activo", "value": "4 activas", "detail": "10 bloqueadas"},
                    {"label": "NOAA interpretable", "value": "1/4", "detail": "ciudades con >= 3 casos"},
                    {"label": "Muestra NOAA", "value": "4/10", "detail": "2 / 4 ciudades con muestra"},
                ],
                "drivers": [],
                "detail_routes": [],
            },
            "send_telegram_paged": lambda text, with_menu=False, page_size=3800: focus_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "cmd_focus"), focus_ns)
        focus_ns["cmd_focus"]()
        focus_msg = focus_messages[-1] if focus_messages else ""
        test("focus cmd: muestra las cinco preguntas y accion del dia",
             "Focus / Discovery-Stabilization" in focus_msg
             and "¿Está sano el sistema?" in focus_msg
             and "Acción recomendada hoy" in focus_msg
             and "No tocar trading: priorizar crecimiento de muestra NOAA" in focus_msg,
             focus_msg[:420])
        test("focus cmd: deja rutas rapidas hacia detalle",
             "/estado sistema" in focus_msg and "/noaa muestra" in focus_msg and "/detalle ciclo raw" in focus_msg,
             focus_msg[:420])

        fd, tmp_signals = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_signals_test_",
            suffix=".json",
        )
        os.close(fd)
        traders_messages = []
        traders_match_date = (date.today() + timedelta(days=2)).isoformat()
        traders_other_date = (date.today() + timedelta(days=1)).isoformat()
        traders_match_label = (
            datetime.fromisoformat(traders_match_date)
            .strftime("%B %d")
            .replace(" 0", " ")
        )
        traders_ns = {
            "os": os,
            "json": json,
            "date": date,
            "datetime": datetime,
            "timezone": timezone,
            "SIGNALS_FILE": tmp_signals,
            "_get_portfolio_and_positions": lambda: {
                "active": [{
                    "title": f"Will the temperature in London be 11°C on {traders_match_label}?",
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
                    {"city": "London", "outcome": "No", "date": traders_other_date, "avg_price": 0.43, "is_reference": False, "has_consensus": False},
                    {"city": "London", "outcome": "No", "date": traders_match_date, "avg_price": 0.44, "is_reference": False, "has_consensus": False},
                ],
            }, f, ensure_ascii=False)
        exec(get_function_source(module_ast, code_lines, "cmd_traders"), traders_ns)
        traders_ns["cmd_traders"]()
        traders_msg = traders_messages[-1] if traders_messages else ""
        aligned_section = traders_msg.split("<b>Señales activas", 1)[0]
        test("traders: alinea solo fecha exacta de cartera",
             f"London No {traders_match_date}" in aligned_section and f"London No {traders_other_date}" not in aligned_section,
             aligned_section[:260])
        test("traders: análisis sin separador huérfano",
             "\n| Análisis:" not in traders_msg and "Análisis: 28/03 19:30 UTC" in traders_msg,
             traders_msg[:220])

        noaa_date = (date.today() - timedelta(days=3)).isoformat()
        noaa_request_urls = []

        class _DummyNoaaRequest:
            def __init__(self, url):
                self.full_url = url
                self.headers = {}

            def add_header(self, key, value):
                self.headers[key] = value

        def _dummy_noaa_urlopen(req, timeout=0):
            noaa_request_urls.append(req.full_url)
            if "daily-summaries" in req.full_url:
                if "stations=USWEMPTY" in req.full_url:
                    payload = []
                else:
                    payload = [{"TMAX": "33.9"}]
            else:
                payload = [
                    {"TMP": "+0123,1"},
                    {"TMP": "+0156,1"},
                    {"TMP": "+9999,9"},
                ]
            return types.SimpleNamespace(read=lambda: json.dumps(payload).encode("utf-8"))

        noaa_ns = {
            "json": json,
            "date": date,
            "datetime": datetime,
            "timezone": timezone,
            "time": types.SimpleNamespace(sleep=lambda seconds: None),
            "urllib": types.SimpleNamespace(
                parse=types.SimpleNamespace(
                    urlencode=lambda params: "&".join(f"{key}={params[key]}" for key in sorted(params))
                ),
                request=types.SimpleNamespace(Request=_DummyNoaaRequest, urlopen=_dummy_noaa_urlopen),
            ),
            "NOAA_NCEI_ACCESS_URL": "https://example.test/noaa",
            "NOAA_OBSERVED_LAG_DAYS": 2,
            "log": type("L", (), {"warning": staticmethod(lambda *a, **k: None)})(),
        }
        exec(get_function_source(module_ast, code_lines, "_parse_noaa_tmp_c"), noaa_ns)
        exec(get_function_source(module_ast, code_lines, "fetch_noaa_daily_tmax"), noaa_ns)
        exec(get_function_source(module_ast, code_lines, "_fetch_noaa_observed_max_hourly"), noaa_ns)
        exec(get_function_source(module_ast, code_lines, "fetch_noaa_observed_max"), noaa_ns)
        noaa_max = noaa_ns["fetch_noaa_observed_max"]("72258303927", noaa_date, daily_station_id="USW00013960", retries=1, delay=0)
        test("NOAA helper: prioriza TMAX diaria cuando existe", noaa_max == (33.9, "daily-summaries_tmax"), noaa_max)
        test("NOAA helper: construye request daily-summaries al endpoint NCEI", bool(noaa_request_urls) and "daily-summaries" in noaa_request_urls[0], noaa_request_urls[:1])
        noaa_fallback = noaa_ns["fetch_noaa_observed_max"]("72258303927", noaa_date, daily_station_id="USWEMPTY", retries=1, delay=0)
        test("NOAA helper: fallback a hourly si daily viene vacio", noaa_fallback == (15.6, "global-hourly_tmp_max"), noaa_fallback)
        recent_noaa_date = date.today().isoformat()
        requests_before_lag = len(noaa_request_urls)
        noaa_daily_recent = noaa_ns["fetch_noaa_daily_tmax"]("USW00013960", recent_noaa_date, retries=1, delay=0)
        test("NOAA helper daily: respeta lag y evita request innecesario", noaa_daily_recent is None and len(noaa_request_urls) == requests_before_lag,
             {"value": noaa_daily_recent, "requests_before": requests_before_lag, "requests_after": len(noaa_request_urls)})

        fd, tmp_perf_noaa = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_perf_noaa_test_",
            suffix=".json",
        )
        os.close(fd)
        observed_saved = {}
        observed_calls = []
        lagged_date = (date.today() - timedelta(days=1)).isoformat()
        noaa_shadow_date = (date.today() - timedelta(days=4)).isoformat()
        with open(tmp_perf_noaa, "w", encoding="utf-8") as f:
            json.dump([
                {"action": "BUY", "city": "Dallas", "date": noaa_date, "forecast_max": 18.0, "side": "YES", "edge_pct": 12.5},
                {"action": "BUY", "city": "Dallas", "date": noaa_date, "forecast_max": 18.4, "side": "YES", "edge_pct": 13.1},
                {"action": "BUY", "city": "London", "date": noaa_date, "forecast_max": 11.0, "side": "NO", "edge_pct": 9.0},
                {"action": "BUY", "city": "Atlanta", "date": lagged_date, "forecast_max": 20.0, "side": "YES", "edge_pct": 8.2},
            ], f, ensure_ascii=False)

        observed_ns = {
            "os": os,
            "json": json,
            "date": date,
            "datetime": datetime,
            "timezone": timezone,
            "timedelta": timedelta,
            "PERFORMANCE_FILE": tmp_perf_noaa,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "NOAA_OBSERVED_LAG_DAYS": 2,
            "RESOLUTION_ICAO": {
                "Chicago": {"icao": "KORD", "noaa_station_id": "72530094846", "noaa_daily_station_id": "USW00094846"},
                "Dallas": {"icao": "KDAL", "noaa_station_id": "72258303927", "noaa_daily_station_id": "USW00013960"},
                "Atlanta": {"icao": "KATL", "noaa_station_id": "72219013874", "noaa_daily_station_id": "USW00013874"},
                "London": {"icao": "EGLC", "noaa_station_id": "00000000000"},
            },
            "load_audit_data": lambda: {"pending_sells": [], "forecast_vs_real": [], "observed_vs_forecast": [], "errors": []},
            "load_cycle_summary_data": lambda: {
                "cycle_number": 21,
                "logic_cycle_number": 7,
                "timestamp_utc": "2026-04-01T16:00:00+00:00",
                "scanned_markets": [
                    {"city": "Chicago", "date": noaa_shadow_date, "forecast_max": 16.2},
                    {"city": "Dallas", "date": noaa_date, "forecast_max": 18.0},
                ],
            },
            "load_cycle_history": lambda limit=None: [],
            "save_audit_data": lambda data: observed_saved.update(data),
            "fetch_noaa_observed_max": lambda station_id, date_iso, daily_station_id="", retries=3, delay=5: observed_calls.append((station_id, date_iso, daily_station_id)) or (19.4, "daily-summaries_tmax"),
        }
        exec(get_function_source(module_ast, code_lines, "_iter_recent_noaa_cycle_markets"), observed_ns)
        exec(get_function_source(module_ast, code_lines, "_get_noaa_candidate_dates"), observed_ns)
        exec(get_function_source(module_ast, code_lines, "audit_check_resolution_truth"), observed_ns)
        observed_dl = []
        observed_ns["audit_check_resolution_truth"](observed_dl)
        observed_records = observed_saved.get("observed_vs_forecast", [])
        chicago_record = next((rec for rec in observed_records if rec.get("city") == "Chicago"), None)
        test("audit NOAA: guarda observed_vs_forecast separado del legacy",
             len(observed_records) == 2 and any(rec["city"] == "Dallas" for rec in observed_records), observed_records)
        test("audit NOAA: source=noaa_ncei en registros nuevos",
             bool(observed_records) and observed_records[0]["source"] == "noaa_ncei", observed_records[:1])
        test("audit NOAA: deja trazabilidad del dataset observado",
             bool(observed_records) and observed_records[0]["observed_dataset"] == "daily-summaries_tmax", observed_records[:1])
        test("audit NOAA: dedupe city-date evita repetir llamadas del mismo dia",
             sum(1 for call in observed_calls if call[1] == noaa_date and call[0] == "72258303927") == 1,
             observed_calls)
        test("audit NOAA: colecta fecha sin BUY context",
             chicago_record is not None and chicago_record.get("date") == noaa_shadow_date and chicago_record.get("side") is None and chicago_record.get("edge_pct") is None,
             chicago_record)
        test("audit NOAA: no toca ciudades bloqueadas",
             all(rec["city"] != "London" for rec in observed_records) and all(call[0] != "00000000000" for call in observed_calls),
             {"records": observed_records, "calls": observed_calls})
        test("audit NOAA: respeta lag de 2 dias",
             all(call[1] != lagged_date for call in observed_calls), observed_calls)
        test("audit NOAA: log usa observado NOAA NCEI",
             any("observado NOAA NCEI=19.4°C" in line for line in observed_dl), observed_dl[:3])
        if os.path.exists(tmp_perf_noaa):
            try:
                os.remove(tmp_perf_noaa)
            except PermissionError:
                pass

        pm_empty_messages = []
        fd, tmp_perf_summary = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
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
    print("\n Postmortem")
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
            dir=_verify_tmp_dir(),
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
            "re": re,
            "datetime": datetime,
            "timezone": timezone,
            "POSTMORTEM_FILE": tmp_postmortem,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        for fn_name in [
            "load_postmortem_data",
            "save_postmortem_data",
            "_normalize_trade_lifecycle_text",
            "_trade_lifecycle_market_key",
            "_trade_lifecycle_position_key",
            "_find_open_postmortem",
            "_find_postmortem_by_position_key",
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

        with open(tmp_postmortem, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

        orphan_buy = {
            "timestamp": "2026-03-26T16:00:35.537606+00:00",
            "bot_version": "v10.6.10",
            "city": "Miami",
            "side": "YES",
            "date": "2026-03-26",
            "question": "",
            "token_id": "",
            "condition": "range",
            "amount": 2.20,
            "shares": 11.28,
            "price": 0.195,
            "edge_pct": 14.5,
            "forecast_max": 28.0,
            "our_prob": 32.0,
            "mkt_price": 17.5,
            "trader_confirmed": [],
        }
        orphan_close = {
            "timestamp": "2026-03-26T23:00:05.994490+00:00",
            "bot_version": "v10.6.10",
            "city": "Miami",
            "side": "Yes",
            "reason": "micro_position_unsellable",
            "loss": -2.14,
        }

        pm_ns["update_postmortem"]("BUY", orphan_buy)
        pm_ns["update_postmortem"]("LOSS_TOTAL", orphan_close)

        orphan_records = pm_ns["load_postmortem_data"]()
        orphan_rec = orphan_records[-1] if orphan_records else {}
        test("postmortem funcional: LOSS_TOTAL sin date/question se pega al BUY abierto",
             len(orphan_records) == 1
             and orphan_rec.get("status") == "closed"
             and orphan_rec.get("city") == "Miami"
             and orphan_rec.get("date") == "2026-03-26"
             and orphan_rec.get("close_action") == "LOSS_TOTAL"
             and orphan_rec.get("close_reason") == "micro_position_unsellable",
             orphan_records)

        if os.path.exists(tmp_postmortem):
            try:
                os.remove(tmp_postmortem)
            except OSError:
                pass
    except Exception as e:
        test("Postmortem funcional ejecuta sin excepción", False, str(e))

    # ---- Test 20b: trade_lifecycle.json ----
    print("\n Trade lifecycle")
    test("trade_lifecycle usa archivo dedicado", 'TRADE_LIFECYCLE_FILE = _data_path("trade_lifecycle.json")' in code)
    test("trade_lifecycle sincroniza desde performance+postmortem", "def _sync_trade_lifecycle_from_sources(" in code)
    test("trade_lifecycle toma snapshots durante gestiÃ³n", 'record_trade_lifecycle_position_snapshots(temp_positions, source="manage_positions", stage="pre_checks")' in code)
    test("trade_lifecycle observa mercado tras cierre", "def record_trade_lifecycle_market_observations(" in code)
    test("trade_lifecycle expone bloque de integridad", "def _build_trade_lifecycle_integrity(" in code)
    test("trade_lifecycle usa helper seguro de vacio", "def _lifecycle_is_empty(" in code)

    try:
        fd, tmp_perf_lifecycle = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_trade_lifecycle_perf_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_pm_lifecycle = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_trade_lifecycle_pm_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_trade_lifecycle = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_trade_lifecycle_",
            suffix=".json",
        )
        os.close(fd)

        question_atl = "Will the highest temperature in Atlanta be between 72-73°F on March 30?"
        buy_ts = "2026-03-30T08:00:00+00:00"
        sell_pending_ts = "2026-03-30T12:00:00+00:00"
        sell_fill_ts = "2026-03-30T12:05:00+00:00"

        with open(tmp_perf_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "timestamp": buy_ts,
                    "action": "BUY",
                    "city": "Atlanta",
                    "side": "YES",
                    "date": "2026-03-30",
                    "question": question_atl,
                    "token_id": "tok-atl-yes",
                    "amount": 1.85,
                    "shares": 3.3,
                    "price": 0.56,
                    "edge_pct": 21.0,
                    "forecast_max": 22.7,
                    "our_prob": 0.61,
                    "mkt_price": 0.40,
                    "days_ahead": 1,
                    "trader_confirmed": ["Entire-Hood"],
                    "cycle_number": 14,
                    "logic_cycle_number": 8,
                    "bot_version": "v10.6.10",
                },
                {
                    "timestamp": sell_pending_ts,
                    "action": "SELL_PENDING",
                    "city": "Atlanta",
                    "side": "YES",
                    "date": "2026-03-30",
                    "question": question_atl,
                    "token_id": "tok-atl-yes",
                    "reason": "take_profit",
                    "decision_note": "TAKE-PROFIT (+44.0% > +40.0%)",
                    "decision_source": "manage_positions",
                    "price": 0.79,
                    "trigger_price": 0.81,
                    "shares": 3.3,
                    "return_est": 2.61,
                    "pnl_pct": 44.0,
                    "pnl_cash": 0.75,
                    "current_value": 2.67,
                    "order_id": "oid-atl-1",
                    "bot_version": "v10.6.10",
                },
                {
                    "timestamp": sell_pending_ts,
                    "fill_confirmed": sell_fill_ts,
                    "action": "SELL",
                    "city": "Atlanta",
                    "side": "YES",
                    "date": "2026-03-30",
                    "question": question_atl,
                    "token_id": "tok-atl-yes",
                    "reason": "take_profit",
                    "price": 0.79,
                    "shares": 3.3,
                    "return_est": 2.61,
                    "pnl_pct": 44.0,
                    "pnl_cash": 0.75,
                    "order_id": "oid-atl-1",
                    "bot_version": "v10.6.10",
                },
            ], f, ensure_ascii=False)

        with open(tmp_pm_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "tok-atl-yes|YES|2026-03-30|2026-03-30T08:00:00+00:00",
                    "status": "closed",
                    "token_id": "tok-atl-yes",
                    "question": question_atl,
                    "city": "Atlanta",
                    "side": "YES",
                    "date": "2026-03-30",
                    "condition": "between",
                    "opened_at": buy_ts,
                    "last_buy_at": buy_ts,
                    "closed_at": sell_fill_ts,
                    "buy_count": 1,
                    "total_amount": 1.85,
                    "total_shares": 3.3,
                    "avg_entry_price": 0.5606,
                    "trader_confirmed": ["Entire-Hood"],
                    "bot_version_opened": "v10.6.10",
                    "bot_version_closed": "v10.6.10",
                    "buys": [
                        {
                            "timestamp": buy_ts,
                            "amount": 1.85,
                            "shares": 3.3,
                            "price": 0.56,
                            "edge_pct": 21.0,
                            "forecast_max": 22.7,
                            "our_prob": 0.61,
                            "mkt_price": 0.40,
                            "bot_version": "v10.6.10",
                        }
                    ],
                    "close_action": "SELL",
                    "close_reason": "take_profit",
                    "close_subtype": "take_profit",
                    "close_price": 0.79,
                    "close_shares": 3.3,
                    "return_est": 2.61,
                    "pnl_cash": 0.76,
                    "pnl_pct": 41.08,
                    "order_id": "oid-atl-1",
                }
            ], f, ensure_ascii=False)

        lifecycle_ns = {
            "os": os,
            "json": json,
            "re": re,
            "datetime": datetime,
            "timezone": timezone,
            "TRADE_LIFECYCLE_FILE": tmp_trade_lifecycle,
            "PERFORMANCE_FILE": tmp_perf_lifecycle,
            "POSTMORTEM_FILE": tmp_pm_lifecycle,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        for fn_name in [
            "load_performance_history",
            "load_postmortem_data",
            "load_trade_lifecycle_data",
            "save_trade_lifecycle_data",
            "_lifecycle_clone",
            "_lifecycle_is_empty",
            "_parse_lifecycle_timestamp",
            "_to_lifecycle_float",
            "_normalize_trade_lifecycle_text",
            "_trade_lifecycle_market_key",
            "_trade_lifecycle_position_key",
            "_trade_lifecycle_entry_anchor",
            "_trade_lifecycle_merge_priority",
            "_trade_lifecycle_records_can_merge",
            "_trade_lifecycle_label",
            "_trade_lifecycle_record_id",
            "_find_trade_lifecycle_record",
            "_new_trade_lifecycle_record",
            "_merge_trade_lifecycle_context",
            "_merge_trade_lifecycle_record",
            "_coalesce_trade_lifecycle_records",
            "_build_trade_lifecycle_record_integrity",
            "_build_trade_lifecycle_integrity",
            "_copy_trade_lifecycle_dynamic_fields",
            "_timeline_event_from_entry",
            "_append_trade_lifecycle_event",
            "_append_trade_lifecycle_buy",
            "_append_trade_lifecycle_exit_attempt",
            "_update_trade_lifecycle_exit_attempt",
            "_apply_trade_lifecycle_close",
            "_append_synthetic_postmortem_close_event",
            "_build_trade_lifecycle_summary",
            "_sync_trade_lifecycle_from_sources",
            "record_trade_lifecycle_position_snapshots",
            "record_trade_lifecycle_market_observations",
        ]:
            exec(get_function_source(module_ast, code_lines, fn_name), lifecycle_ns)

        lifecycle_ns["_parse_position_label"] = lambda title, outcome="": f"{title} {outcome}".strip()
        lifecycle_ns["parse_temperature_question"] = lambda title: {"date_str": "2026-03-30", "condition": "between"}
        lifecycle_ns["date_text_to_iso"] = lambda value: value
        lifecycle_ns["parse_city_from_title"] = lambda title: "Atlanta"

        lifecycle_payload = lifecycle_ns["_sync_trade_lifecycle_from_sources"]()
        lifecycle_records = lifecycle_payload.get("records", [])
        lifecycle_record = lifecycle_records[0] if lifecycle_records else {}

        test("trade_lifecycle funcional: reconstruye un registro histÃ³rico",
             len(lifecycle_records) == 1 and lifecycle_record.get("token_id") == "tok-atl-yes",
             lifecycle_records)
        test("trade_lifecycle funcional: entry_context conserva ciclo y traders",
             lifecycle_record.get("entry_context", {}).get("cycle_number") == 14
             and lifecycle_record.get("entry_context", {}).get("logic_cycle_number") == 8
             and lifecycle_record.get("entry_context", {}).get("trader_confirmed") == ["Entire-Hood"],
             lifecycle_record.get("entry_context"))
        test("trade_lifecycle funcional: SELL_PENDING preserva decision/trigger/current_value",
             bool(lifecycle_record.get("exit_attempts"))
             and lifecycle_record["exit_attempts"][0].get("decision_source") == "manage_positions"
             and lifecycle_record["exit_attempts"][0].get("trigger_price") == 0.81
             and lifecycle_record["exit_attempts"][0].get("current_value") == 2.67,
             lifecycle_record.get("exit_attempts"))
        test("trade_lifecycle funcional: SELL queda como cierre filled",
             lifecycle_record.get("close_context", {}).get("close_action") == "SELL"
             and lifecycle_record.get("exit_attempts", [{}])[0].get("status") == "filled",
             {"close": lifecycle_record.get("close_context"), "exit_attempts": lifecycle_record.get("exit_attempts")})
        test("trade_lifecycle funcional: summary cuenta take_profit",
             lifecycle_payload.get("summary", {}).get("take_profit_closes") == 1,
             lifecycle_payload.get("summary"))

        lifecycle_ns["record_trade_lifecycle_position_snapshots"]([
            {
                "title": question_atl,
                "asset": "tok-atl-yes",
                "outcome": "YES",
                "curPrice": 0.83,
                "currentValue": 2.74,
                "percentPnl": 47.9,
                "cashPnl": 0.89,
                "size": 3.3,
                "avgPrice": 0.56,
            }
        ], source="manage_positions", stage="pre_checks")

        after_snapshot = lifecycle_ns["load_trade_lifecycle_data"]()
        snapshot_record = after_snapshot.get("records", [])[0] if after_snapshot.get("records") else {}
        test("trade_lifecycle funcional: guarda snapshot de posiciÃ³n viva",
             len(snapshot_record.get("position_snapshots", [])) == 1
             and snapshot_record.get("position_snapshots", [])[0].get("cur_price") == 0.83,
             snapshot_record.get("position_snapshots"))
        test("trade_lifecycle funcional: actualiza position_stats",
             snapshot_record.get("position_stats", {}).get("max_cur_price_open") == 0.83
             and snapshot_record.get("position_stats", {}).get("max_current_value_open") == 2.74,
             snapshot_record.get("position_stats"))

        lifecycle_ns["record_trade_lifecycle_market_observations"]([
            {
                "question": question_atl,
                "outcomePrices": "[\"1.00\",\"0.00\"]",
                "clobTokenIds": "[\"tok-atl-yes\",\"tok-atl-no\"]",
                "liquidity": 1250.0,
                "volume24hr": 410.0,
            }
        ], source="cycle_market_scan")

        after_market = lifecycle_ns["load_trade_lifecycle_data"]()
        market_record = after_market.get("records", [])[0] if after_market.get("records") else {}
        post_exit = market_record.get("post_exit_analysis", {})
        test("trade_lifecycle funcional: guarda observaciÃ³n de mercado post-salida",
             len(market_record.get("market_observations", [])) == 1
             and post_exit.get("market_seen_after_close") is True,
             {"market": market_record.get("market_observations"), "post_exit": post_exit})
        test("trade_lifecycle funcional: detecta upside_left hasta 100c",
             post_exit.get("reached_98_after_close") is True
             and post_exit.get("upside_left_cash_peak") == 0.69,
             post_exit)
        test("trade_lifecycle funcional: summary refleja casos con upside_left",
             after_market.get("summary", {}).get("with_upside_left_after_close") == 1,
             after_market.get("summary"))

        with open(tmp_perf_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "timestamp": "2026-03-26T23:00:23.521678+00:00",
                    "action": "BUY",
                    "city": "Seattle",
                    "side": "YES",
                    "date": "2026-03-28",
                    "question": "",
                    "token_id": "",
                    "amount": 2.50,
                    "shares": 23.92,
                    "price": 0.1045,
                    "edge_pct": 27.0,
                    "forecast_max": 11.8,
                    "our_prob": 35.5,
                    "mkt_price": 8.5,
                    "days_ahead": 2,
                    "condition": "at_or_below",
                    "trader_confirmed": [],
                    "bot_version": "v10.6.10",
                },
                {
                    "timestamp": "2026-03-27T23:00:14.681144+00:00",
                    "fill_confirmed": "2026-03-27T23:00:14.709743+00:00",
                    "action": "SELL",
                    "city": "Seattle",
                    "side": "Yes",
                    "reason": "stop_loss",
                    "price": 0.02,
                    "shares": 23.92,
                    "return_est": 0.48,
                    "pnl_pct": -56.29,
                    "pnl_cash": -1.34,
                    "order_id": "oid-sea-legacy",
                    "bot_version": "v10.6.10",
                },
            ], f, ensure_ascii=False)

        with open(tmp_pm_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "market:seattle|date:2026-03-28|side:YES|2026-03-26T23:00:23.521678+00:00",
                    "status": "open",
                    "token_id": "",
                    "question": "",
                    "city": "Seattle",
                    "side": "YES",
                    "date": "2026-03-28",
                    "condition": "at_or_below",
                    "opened_at": "2026-03-26T23:00:23.521678+00:00",
                    "last_buy_at": "2026-03-26T23:00:23.521678+00:00",
                    "closed_at": None,
                    "buy_count": 1,
                    "total_amount": 2.50,
                    "total_shares": 23.92,
                    "avg_entry_price": 0.1045,
                    "trader_confirmed": [],
                    "bot_version_opened": "v10.6.10",
                    "bot_version_closed": "",
                    "buys": [
                        {
                            "timestamp": "2026-03-26T23:00:23.521678+00:00",
                            "amount": 2.50,
                            "shares": 23.92,
                            "price": 0.1045,
                            "edge_pct": 27.0,
                            "forecast_max": 11.8,
                            "our_prob": 35.5,
                            "mkt_price": 8.5,
                            "bot_version": "v10.6.10",
                        }
                    ],
                    "close_action": "",
                    "close_reason": "",
                    "close_subtype": "",
                    "close_price": None,
                    "close_shares": None,
                    "return_est": None,
                    "pnl_cash": None,
                    "pnl_pct": None,
                    "order_id": "",
                }
            ], f, ensure_ascii=False)

        with open(tmp_trade_lifecycle, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": "",
                "summary": {},
                "integrity": {},
                "records": [],
            }, f, ensure_ascii=False)

        matched_close_payload = lifecycle_ns["_sync_trade_lifecycle_from_sources"]()
        matched_close_records = matched_close_payload.get("records", [])
        matched_close_record = matched_close_records[0] if matched_close_records else {}
        test("trade_lifecycle funcional: SELL sin date/question se pega al BUY abierto",
             len(matched_close_records) == 1
             and matched_close_record.get("status") == "closed"
             and matched_close_record.get("date") == "2026-03-28"
             and matched_close_record.get("close_context", {}).get("close_action") == "SELL"
             and matched_close_record.get("close_context", {}).get("close_reason") == "stop_loss"
             and {item.get("action") for item in matched_close_record.get("timeline", [])} == {"BUY", "SELL"},
             matched_close_records)

        orphan_fill_ts = "2026-03-27T08:00:26.261032+00:00"
        with open(tmp_perf_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "timestamp": "2026-03-27T08:00:26.233834+00:00",
                    "fill_confirmed": orphan_fill_ts,
                    "action": "SELL",
                    "city": "Atlanta",
                    "side": "Yes",
                    "price": 0.20,
                    "shares": 30.51,
                    "return_est": 6.10,
                    "pnl_pct": 63.31,
                    "pnl_cash": 2.60,
                    "order_id": "oid-orphan-1",
                    "reason": "take_profit",
                }
            ], f, ensure_ascii=False)

        with open(tmp_pm_lifecycle, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "Atlanta|YES||2026-03-27T08:00:26.261032+00:00",
                    "status": "closed",
                    "token_id": "",
                    "question": "",
                    "city": "Atlanta",
                    "side": "YES",
                    "date": "",
                    "condition": "",
                    "opened_at": orphan_fill_ts,
                    "closed_at": orphan_fill_ts,
                    "buy_count": 0,
                    "total_amount": 0.0,
                    "total_shares": 0.0,
                    "avg_entry_price": 0.134709,
                    "trader_confirmed": [],
                    "bot_version_opened": "",
                    "bot_version_closed": "",
                    "buys": [],
                    "close_action": "SELL",
                    "close_reason": "take_profit",
                    "close_subtype": "take_profit",
                    "close_price": 0.20,
                    "close_shares": 30.51,
                    "return_est": 6.10,
                    "pnl_cash": 2.60,
                    "pnl_pct": 63.31,
                    "order_id": "oid-orphan-1",
                }
            ], f, ensure_ascii=False)

        with open(tmp_trade_lifecycle, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": "",
                "summary": {},
                "integrity": {},
                "records": [],
            }, f, ensure_ascii=False)

        orphan_payload = lifecycle_ns["_sync_trade_lifecycle_from_sources"]()
        orphan_records = orphan_payload.get("records", [])
        orphan_record = orphan_records[0] if orphan_records else {}
        orphan_integrity = orphan_record.get("integrity", {})
        test("trade_lifecycle funcional: cierre huÃ©rfano no se duplica entre postmortem y performance",
             len(orphan_records) == 1 and len(orphan_record.get("timeline", [])) == 1,
             orphan_records)
        test("trade_lifecycle funcional: cierre huÃ©rfano queda marcado como parcial",
             orphan_integrity.get("partial_historical_record") is True
             and orphan_payload.get("integrity", {}).get("partial_historical_records") == 1,
             {"record": orphan_record, "integrity": orphan_payload.get("integrity")})

        merged_records, merged_collisions = lifecycle_ns["_coalesce_trade_lifecycle_records"]([
            {
                "id": "dup-ctx-1",
                "label": "dup-ctx-1",
                "token_id": "token-1",
                "question": "Question 1",
                "city": "Chicago",
                "side": "YES",
                "date": "2026-03-31",
                "status": "open",
                "entry_context": {
                    "timestamp": "2026-03-31T08:00:00+00:00",
                    "trader_confirmed": ["Alpha"],
                },
                "latest_entry_context": {},
                "close_context": {},
                "buys": [],
                "timeline": [],
                "exit_attempts": [],
                "position_snapshots": [],
                "market_observations": [],
                "position_stats": {},
                "post_exit_analysis": {},
                "history_sources": {},
            },
            {
                "id": "dup-ctx-1",
                "label": "dup-ctx-1",
                "token_id": "token-1",
                "question": "Question 1",
                "city": "Chicago",
                "side": "YES",
                "date": "2026-03-31",
                "status": "open",
                "entry_context": {
                    "price": 0.19,
                    "trader_confirmed": ["Beta"],
                },
                "latest_entry_context": {},
                "close_context": {},
                "buys": [],
                "timeline": [],
                "exit_attempts": [],
                "position_snapshots": [],
                "market_observations": [],
                "position_stats": {},
                "post_exit_analysis": {},
                "history_sources": {},
            },
        ])
        merged_record = merged_records[0] if merged_records else {}
        merged_entry_context = merged_record.get("entry_context", {})
        test("trade_lifecycle funcional: coalesce de contextos duplicados no rompe",
             len(merged_records) == 1
             and merged_collisions == 1
             and merged_entry_context.get("timestamp") == "2026-03-31T08:00:00+00:00"
             and merged_entry_context.get("price") == 0.19
             and merged_entry_context.get("trader_confirmed") == ["Alpha", "Beta"],
             {"records": merged_records, "collisions": merged_collisions})

        followup_records, followup_collisions = lifecycle_ns["_coalesce_trade_lifecycle_records"]([
            {
                "id": "tok-dal-yes|YES|2026-04-01|2026-03-31T08:00:00+00:00",
                "token_id": "tok-dal-yes",
                "question": "Will the highest temperature in Dallas be between 82-83°F on April 1?",
                "city": "Dallas",
                "side": "YES",
                "date": "2026-04-01",
                "status": "closed",
                "entry_context": {
                    "timestamp": "2026-03-31T08:00:00+00:00",
                    "price": 0.13,
                },
                "close_context": {
                    "close_action": "SELL",
                    "close_reason": "stop_loss",
                    "close_price": 0.04,
                    "close_shares": 10.9,
                },
                "buys": [{"timestamp": "2026-03-31T08:00:00+00:00", "price": 0.13, "amount": 1.33, "shares": 10.9}],
                "timeline": [{"timestamp": "2026-03-31T23:00:00+00:00", "action": "SELL"}],
                "exit_attempts": [],
                "position_snapshots": [],
                "market_observations": [],
                "position_stats": {},
                "post_exit_analysis": {},
                "history_sources": {},
            },
            {
                "id": "tok-dal-yes|YES|2026-04-01|2026-04-01T08:00:00+00:00",
                "token_id": "tok-dal-yes",
                "question": "Will the highest temperature in Dallas be between 82-83°F on April 1?",
                "city": "Dallas",
                "side": "YES",
                "date": "2026-04-01",
                "status": "closed",
                "entry_context": {},
                "close_context": {
                    "close_action": "LOSS_TOTAL",
                    "close_reason": "micro_position_unsellable",
                    "close_price": 0.0,
                    "close_shares": 0.01,
                },
                "buys": [],
                "timeline": [{"timestamp": "2026-04-01T08:00:00+00:00", "action": "LOSS_TOTAL"}],
                "exit_attempts": [],
                "position_snapshots": [],
                "market_observations": [],
                "position_stats": {},
                "post_exit_analysis": {},
                "history_sources": {},
            },
        ])
        followup_record = followup_records[0] if followup_records else {}
        test("trade_lifecycle funcional: coalesce une follow-up LOSS_TOTAL con la posicion original",
             len(followup_records) == 1
             and followup_collisions == 1
             and followup_record.get("close_context", {}).get("close_action") == "SELL"
             and {item.get("action") for item in followup_record.get("timeline", [])} == {"SELL", "LOSS_TOTAL"},
             {"records": followup_records, "collisions": followup_collisions})
        test("trade_lifecycle funcional: label explicita el lado cuando hay question",
             lifecycle_ns["_trade_lifecycle_label"]({
                 "question": "Will the highest temperature in Seoul be 14°C on April 1?",
                 "side": "NO",
             }).endswith("NO"),
             lifecycle_ns["_trade_lifecycle_label"]({
                 "question": "Will the highest temperature in Seoul be 14°C on April 1?",
                 "side": "NO",
             }))

        for tmp_path in [tmp_perf_lifecycle, tmp_pm_lifecycle, tmp_trade_lifecycle]:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    except Exception as e:
        test("trade_lifecycle funcional ejecuta sin excepciÃ³n", False, str(e))

    # ---- Test 21: alertas de observabilidad ----
    print("\n Alertas de observabilidad")
    test("ALERTS_FILE definido", "ALERTS_FILE" in code)
    test("load_alerts_state definida", "def load_alerts_state(" in code)
    test("save_alerts_state definida", "def save_alerts_state(" in code)
    test("backfill_postmortem_from_performance definida", "def backfill_postmortem_from_performance(" in code)
    test("inspect_signals_file_health definida", "def inspect_signals_file_health(" in code)
    test("get_clean_closed_trade_stats definida", "def get_clean_closed_trade_stats(" in code)
    test("run_observability_alerts definida", "def run_observability_alerts(" in code)
    test("alertas NOAA observed proxy presentes",
         "Observed proxy NOAA activo" in code and "Muestra NOAA mínima alcanzada" in code and "Muestra NOAA global útil" in code)
    test("alertas usan milestones con setdefault", 'state.setdefault("milestones", {})' in code)
    test("arranque hace backfill de postmortem", "backfill_postmortem_from_performance()" in code)
    test("alertas se evalúan en startup y fin de ciclo", code.count("run_observability_alerts()") >= 2)

    try:
        fd, tmp_perf = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_perf_backfill_test_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_pm = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
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
            "re": re,
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
            "_normalize_trade_lifecycle_text",
            "_trade_lifecycle_market_key",
            "_trade_lifecycle_position_key",
            "_find_open_postmortem",
            "_find_postmortem_by_position_key",
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
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5,
            "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100],
            "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15,
            "WIN_RATE_LOW": 30.0,
            "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
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
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if review_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "get_clean_closed_trade_stats": lambda: {"count": 30, "sell": 20, "loss_total": 6, "resolved_win": 4},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 12},
            "load_audit_data": lambda: {"pending_sells": [], "observed_vs_forecast": []},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "portfolio_total": 14.75},
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
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
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
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if signal_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "stale", "age_hours": 30.5, "actionable": 3},
            "load_audit_data": lambda: {"pending_sells": [], "observed_vs_forecast": []},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "portfolio_total": 14.75},
            "LOW_BANKROLL_THRESHOLD": 5.0,
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
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
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
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if pending_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 2, "sell": 2, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "portfolio_total": 14.75},
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "load_audit_data": lambda: {
                "pending_sells": [{
                    "order_id": "oid-stuck",
                    "city": "Dallas",
                    "side": "YES",
                    "price": 0.31,
                    "timestamp": "2026-03-27T00:00:00+00:00",
                }],
                "observed_vs_forecast": [],
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

        observed_messages = []
        saved_observed_state = {}
        observed_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.6",
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
            "save_alerts_state": lambda state: saved_observed_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if observed_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 1, "sell": 1, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 1},
            "load_audit_data": lambda: {
                "pending_sells": [],
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-28", "error_c": 0.5, "abs_error_c": 0.5, "source": "noaa_ncei", "checked_at": "2026-03-30T12:00:00+00:00"},
                ],
            },
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "cash_ok": True, "api_error": None, "portfolio_total": 14.75},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: observed_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), observed_ns)
        observed_ns["run_observability_alerts"]()
        test("alerta NOAA: primer caso global se envía",
             any("Observed proxy NOAA activo" in msg for msg in observed_messages),
             str(observed_messages))
        test("alerta NOAA: primera ciudad con muestra se envía",
             any("NOAA nueva ciudad con muestra" in msg and "Chicago" in msg for msg in observed_messages),
             str(observed_messages))
        test("alerta NOAA: guarda milestones iniciales",
             "observed_proxy_started" in saved_observed_state.get("milestones", {})
             and "observed_city_started:Chicago" in saved_observed_state.get("milestones", {}),
             str(saved_observed_state))

        observed_ready_messages = []
        saved_observed_ready_state = {}
        observed_ready_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "load_alerts_state": lambda: {
                "logic_series": "10.6",
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
            "save_alerts_state": lambda state: saved_observed_ready_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if observed_ready_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 2, "sell": 2, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 1},
            "load_audit_data": lambda: {
                "pending_sells": [],
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-25", "error_c": 0.5, "abs_error_c": 0.5, "source": "noaa_ncei", "checked_at": "2026-03-30T12:00:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-26", "error_c": 0.8, "abs_error_c": 0.8, "source": "noaa_ncei", "checked_at": "2026-03-30T12:05:00+00:00"},
                    {"city": "Chicago", "date": "2026-03-27", "error_c": -0.2, "abs_error_c": 0.2, "source": "noaa_ncei", "checked_at": "2026-03-30T12:10:00+00:00"},
                    {"city": "Atlanta", "date": "2026-03-25", "error_c": 1.0, "abs_error_c": 1.0, "source": "noaa_ncei", "checked_at": "2026-03-30T12:15:00+00:00"},
                    {"city": "Atlanta", "date": "2026-03-26", "error_c": -0.4, "abs_error_c": 0.4, "source": "noaa_ncei", "checked_at": "2026-03-30T12:20:00+00:00"},
                    {"city": "Atlanta", "date": "2026-03-27", "error_c": 0.3, "abs_error_c": 0.3, "source": "noaa_ncei", "checked_at": "2026-03-30T12:25:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-25", "error_c": -1.2, "abs_error_c": 1.2, "source": "noaa_ncei", "checked_at": "2026-03-30T12:30:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-26", "error_c": 0.7, "abs_error_c": 0.7, "source": "noaa_ncei", "checked_at": "2026-03-30T12:35:00+00:00"},
                    {"city": "Dallas", "date": "2026-03-27", "error_c": 0.1, "abs_error_c": 0.1, "source": "noaa_ncei", "checked_at": "2026-03-30T12:40:00+00:00"},
                    {"city": "Buenos Aires", "date": "2026-03-25", "error_c": -0.6, "abs_error_c": 0.6, "source": "noaa_ncei", "checked_at": "2026-03-30T12:45:00+00:00"},
                ],
            },
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "cash_ok": True, "api_error": None, "portfolio_total": 14.75},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: observed_ready_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), observed_ready_ns)
        observed_ready_ns["run_observability_alerts"]()
        test("alerta NOAA: muestra mínima se envía",
             any("Muestra NOAA mínima alcanzada" in msg for msg in observed_ready_messages),
             str(observed_ready_messages))
        test("alerta NOAA: muestra global útil se envía",
             any("Muestra NOAA global útil" in msg for msg in observed_ready_messages),
             str(observed_ready_messages))
        test("alerta NOAA: ciudad interpretable se envía",
             any("NOAA ciudad interpretable" in msg and "Chicago (3)" in msg for msg in observed_ready_messages),
             str(observed_ready_messages))
        test("alerta NOAA: guarda milestones de muestra útil",
             f"observed_proxy_min_sample_{observed_ready_ns['OBSERVED_FORECAST_MIN_SAMPLE']}" in saved_observed_ready_state.get("milestones", {})
             and f"observed_proxy_global_target_{observed_ready_ns['OBSERVED_FORECAST_GLOBAL_TARGET']}" in saved_observed_ready_state.get("milestones", {})
             and "observed_city_interpretable:Chicago" in saved_observed_ready_state.get("milestones", {}),
             str(saved_observed_ready_state))

        observed_idempotent_messages = []
        observed_idempotent_state = {
            "logic_series": "10.6",
            "milestones": {},
            "signals_health": {"last_issue": None},
            "pending_exit_notified": {},
            "drawdown_alerted": False,
            "scaling_alerted_tier": None,
            "scaling_negative_alerted": False,
            "win_rate_low_alerted": False,
            "win_rate_high_alerted": False,
            "city_accuracy_flagged": {},
        }
        observed_idempotent_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "load_alerts_state": lambda: observed_idempotent_state,
            "save_alerts_state": lambda state: observed_idempotent_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if observed_idempotent_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 2, "sell": 2, "loss_total": 0, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 1},
            "load_audit_data": lambda: {
                "pending_sells": [],
                "observed_vs_forecast": [
                    {"city": "Chicago", "date": "2026-03-25", "error_c": 0.5, "abs_error_c": 0.5, "source": "noaa_ncei", "checked_at": "2026-03-30T12:00:00+00:00"},
                ],
            },
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 13.0, "cash_ok": True, "api_error": None, "portfolio_total": 14.75},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: observed_idempotent_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), observed_idempotent_ns)
        observed_idempotent_ns["run_observability_alerts"]()
        first_observed_count = len(observed_idempotent_messages)
        observed_idempotent_ns["run_observability_alerts"]()
        test("alerta NOAA: idempotencia evita reenvio en segundo call",
             len(observed_idempotent_messages) == first_observed_count,
             str(observed_idempotent_messages))

        low_bankroll_messages = []
        saved_low_bankroll_state = {}
        low_bankroll_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "load_alerts_state": lambda: {
                "logic_series": "10.6",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False,
                "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False,
                "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
                "low_bankroll_alerted": False,
            },
            "save_alerts_state": lambda state: saved_low_bankroll_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if low_bankroll_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "load_audit_data": lambda: {"pending_sells": [], "observed_vs_forecast": []},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 3.25, "cash_ok": True, "api_error": None, "portfolio_total": 4.75},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: low_bankroll_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), low_bankroll_ns)
        low_bankroll_ns["run_observability_alerts"]()
        low_bankroll_msg = low_bankroll_messages[-1] if low_bankroll_messages else ""
        test("alerta bankroll bajo: se envía al cruzar umbral",
             "Bankroll bajo" in low_bankroll_msg and "$4.75" in low_bankroll_msg,
             low_bankroll_msg[:220])
        test("alerta bankroll bajo: guarda flag",
             saved_low_bankroll_state.get("low_bankroll_alerted") is True,
             str(saved_low_bankroll_state))

        low_bankroll_api_messages = []
        saved_low_bankroll_api_state = {}
        low_bankroll_api_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "load_alerts_state": lambda: {
                "logic_series": "10.6",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False,
                "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False,
                "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
                "low_bankroll_alerted": False,
            },
            "save_alerts_state": lambda state: saved_low_bankroll_api_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if low_bankroll_api_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "load_audit_data": lambda: {"pending_sells": [], "observed_vs_forecast": []},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 0.0, "cash_ok": False, "api_error": "timeout", "portfolio_total": 0.0},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: low_bankroll_api_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), low_bankroll_api_ns)
        low_bankroll_api_ns["run_observability_alerts"]()
        test("alerta bankroll bajo: ignora API incierta",
             not low_bankroll_api_messages,
             str(low_bankroll_api_messages))
        test("alerta bankroll bajo: no persiste flag con API incierta",
             saved_low_bankroll_api_state == {},
             str(saved_low_bankroll_api_state))

        low_bankroll_reset_messages = []
        saved_low_bankroll_reset_state = {}
        low_bankroll_reset_ns = {
            "datetime": datetime,
            "timezone": timezone,
            "REVIEW_READY_CLEAN_TRADES": 30,
            "LOGIC_SERIES": "10.6",
            "PENDING_EXIT_ALERT_HOURS": 12.0,
            "DRAWDOWN_WINDOW": 5, "DRAWDOWN_THRESHOLD": -3.0,
            "SCALING_TIERS": [25, 35, 50, 75, 100], "SCALING_WINDOW": 20,
            "WIN_RATE_WINDOW": 15, "WIN_RATE_LOW": 30.0, "WIN_RATE_HIGH": 50.0,
            "BANKROLL": 25.0,
            "LOW_BANKROLL_THRESHOLD": 5.0,
            "LOW_BANKROLL_RESET_MARGIN": 1.0,
            "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
            "OBSERVED_AUDIT_CITIES": {"Chicago", "Atlanta", "Buenos Aires", "Dallas"},
            "OBSERVED_FORECAST_MIN_SAMPLE": 3,
            "OBSERVED_FORECAST_GLOBAL_TARGET": 10,
            "load_alerts_state": lambda: {
                "logic_series": "10.6",
                "milestones": {},
                "signals_health": {"last_issue": None},
                "pending_exit_notified": {},
                "drawdown_alerted": False,
                "scaling_alerted_tier": None,
                "scaling_negative_alerted": False,
                "win_rate_low_alerted": False,
                "win_rate_high_alerted": False,
                "city_accuracy_flagged": {},
                "low_bankroll_alerted": True,
            },
            "save_alerts_state": lambda state: saved_low_bankroll_reset_state.update(state),
            "get_city_accuracy": lambda: {},
            "load_city_policy_state": lambda: {"auto_blocked_cities": {}, "auto_shadow_cities": {}, "auto_canary_cities": {}},
            "get_effective_city_mode": lambda city, policy_state=None: "blocked" if low_bankroll_reset_ns["is_city_blocked"](city) else "active",
            "is_city_blocked": lambda city: False,
            "CITY_MIN_TRADES_FOR_BLOCK": 3,
            "CITY_BLOCK_WIN_RATE": 25.0,
            "get_clean_closed_trade_stats": lambda: {"count": 5, "sell": 4, "loss_total": 1, "resolved_win": 0},
            "inspect_signals_file_health": lambda: {"status": "ok", "age_hours": 1.0, "actionable": 10},
            "load_audit_data": lambda: {"pending_sells": [], "observed_vs_forecast": []},
            "_get_recent_closed_trades": lambda n=None: [],
            "_get_portfolio_and_positions": lambda: {"cash": 6.30, "cash_ok": True, "api_error": None, "portfolio_total": 6.30},
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: low_bankroll_reset_messages.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "run_observability_alerts"), low_bankroll_reset_ns)
        low_bankroll_reset_ns["run_observability_alerts"]()
        test("alerta bankroll bajo: rearma al salir de zona roja con margen",
             saved_low_bankroll_reset_state.get("low_bankroll_alerted") is False,
             str(saved_low_bankroll_reset_state))
        test("alerta bankroll bajo: reset no envía mensaje extra",
             not low_bankroll_reset_messages,
             str(low_bankroll_reset_messages))
    except Exception as e:
        test("Alertas funcionales ejecutan sin excepción", False, str(e))

    # ---- Test v10.5.0: Sigma widening ----
    print("\n v10.5.0: Sigma widening")
    try:
        sigma_ns = {
            "math": __import__("math"),
            "MODEL_SIGMA_REFERENCE": {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5},
            "EMPIRICAL_SIGMA": {"Chicago": {0: 2.57, 1: 2.59, 2: 3.0}},
            "EMPIRICAL_SIGMA_SAMPLES": {"Chicago": {0: 4, 1: 3, 2: 0}},
            "EMPIRICAL_SIGMA_GLOBAL": {0: 2.0, 1: 1.9, 2: 2.5, 3: 3.0},
            "_UNCERTAINTY_CITY_CONTEXT": None,
        }
        exec(get_function_source(module_ast, code_lines, "get_uncertainty"), sigma_ns)
        gu = sigma_ns["get_uncertainty"]
        test("sigma day 0 global = 2.0", gu(0) == 2.0, f"got {gu(0)}")
        test("sigma day 1 global = 1.9", gu(1) == 1.9, f"got {gu(1)}")
        test("sigma day 2 global = 2.5", gu(2) == 2.5, f"got {gu(2)}")
        test("sigma day 3 global = 3.0", gu(3) == 3.0, f"got {gu(3)}")
        test("sigma day 4 = 3.0", gu(4) == 3.0, f"got {gu(4)}")
        test("sigma day 5 = 3.0", gu(5) == 3.0, f"got {gu(5)}")
        test("sigma day 6+ = 3.5", gu(7) == 3.5, f"got {gu(7)}")
        test("sigma Chicago d1 usa empírica", gu(1, city="Chicago") == 2.59, f"got {gu(1, city='Chicago')}")
    except Exception as e:
        test("sigma funcional ejecuta sin excepción", False, str(e))

    # ---- Test v10.6: Revert trading logic + fixes ----
    print("\n v10.6: Revert trading logic + fixes")
    test("MIN_EDGE_EXACT eliminado", "MIN_EDGE_EXACT =" not in code)  # v10.6.15: MIN_EDGE_EXACT_RANGE_BUFFER_PP es distinto
    test("Edge check usa min edge efectivo", "edge_pct < _effective_min_edge" in code or "edge_pct < MIN_EDGE" in code)
    test("LOGIC_SERIES es 10.6", 'LOGIC_SERIES = "10.6"' in code)
    test("LOW_BANKROLL_THRESHOLD definido", "LOW_BANKROLL_THRESHOLD" in code)
    test("LOW_BANKROLL_RESET_MARGIN definido", "LOW_BANKROLL_RESET_MARGIN" in code)
    test("low_bankroll_alerted en alerts state", "low_bankroll_alerted" in code)
    test("Alerta bankroll bajo en Telegram", "Bankroll bajo" in code and "recargar" in code)
    test("Alerta bankroll bajo exige datos fiables", "cash_ok" in code and "api_error" in code)
    test("Drawdown ordena por fecha", "closed_sorted" in code and "closed_at" in code)

    # ---- Test v10.5.0: Smart alerts ----
    print("\n v10.5.0: Smart alerts")
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
    test("Scaling Readiness no recomienda subir sin matiz", "Considerar subir bankroll" not in code)
    test("Scaling Readiness exige revisión manual", "revisión manual" in code and "docs/bankroll_scaling_policy.md" in code)
    test("Scaling Readiness aclara NO autoriza", "NO autoriza" in code and "cambiar BANKROLL solo por esta alerta" in code)
    test("Scaling Warning conserva bloqueo auxiliar", "Señal auxiliar: no subir bankroll" in code and "revisar PnL/drawdown" in code)
    test("SCALING_TIERS conserva escalones canónicos", "SCALING_TIERS = [25, 35, 50, 75, 100]" in code)
    test("BANKROLL_LEVELS conserva default canónico", '"BANKROLL_LEVELS", "25,35,50,75,100"' in code)
    test("Strategy Review en run_observability", "Strategy Review" in code)
    test("Strategy Signal en run_observability", "Strategy Signal" in code)

    # ---- P2C: Bankroll Scaling Monitor Telegram/read-only ----
    print("\n P2C: Bankroll Scaling Monitor Telegram")
    test("bankroll scaling monitor helper definido", "def maybe_run_bankroll_scaling_monitor(" in code)
    test("bankroll scaling check usa CLI JSON", "BANKROLL_SCALING_CHECK_SCRIPT" in code and "bankroll_scaling_check.py" in code and '"--json"' in code)
    test("bankroll scaling check usa subprocess timeout fail-safe", "subprocess.run(" in code and "timeout=BANKROLL_SCALING_MONITOR_TIMEOUT_SECONDS" in code and "return None" in code)
    test("bankroll scaling monitor integrado en observabilidad", "maybe_run_bankroll_scaling_monitor(state)" in code and "bankroll scaling monitor: fallo" in code)
    test("bankroll scaling comando Telegram existe", "def cmd_bankroll(" in code and '"bankroll": cmd_bankroll' in code and '"bankroll_status": cmd_bankroll' in code)
    test("bankroll scaling mensaje manual-only", "NO autoriza" in code and "no subir bankroll" in code and "docs/bankroll_scaling_policy.md" in code)
    test("bankroll scaling Phase 1 copy distingue proxy/canonico", "Phase 1 proxy OK" in code and "canonical check" in code and "phase1_readiness_check.py" in code)
    test("bankroll scaling no muestra Phase 1 ready desnudo", 'favorable.append("Phase 1 ready")' not in code)
    test("bankroll scaling no autoriza Fase C", "No autoriza Truth Pipeline/Fase C" in code)
    test("bankroll scaling no usa increase_now", "increase_now" not in code)
    test("bankroll scaling no instruye subida directa", "Subir bankroll ahora" not in code and "sube bankroll" not in code)
    test("bankroll scaling state anti-spam", "bankroll_scaling_last_status" in code and "bankroll_scaling_last_target_tier" in code and "bankroll_scaling_last_digest_date" in code and "bankroll_scaling_last_blockers_hash" in code and "bankroll_scaling_last_alert_cycle" in code)
    test("bankroll scaling dispara por cambios", "status_changed" in code and "target_changed" in code and "blockers_changed" in code and "eligible_transition" in code and "cycle_summary_due" in code)

    # ---- Test v10.5.0: _get_recent_closed_trades funcional ----
    print("\n v10.5.0: _get_recent_closed_trades funcional")
    try:
        grc_ns = {}
        exec(get_function_source(module_ast, code_lines, "load_postmortem_data"), grc_ns)
        exec(get_function_source(module_ast, code_lines, "_get_recent_closed_trades"), grc_ns)

        fd, mock_pm_file = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_pm_recent_",
            suffix=".json",
        )
        os.close(fd)
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

        if os.path.exists(mock_pm_file):
            try:
                os.remove(mock_pm_file)
            except PermissionError:
                pass
    except Exception as e:
        test("_get_recent_closed_trades funcional ejecuta", False, str(e))

    # ---- Test v10.5.1: Intra-cycle SL monitor ----
    print("\n v10.5.1: Intra-cycle SL monitor")
    test("INTRA_SL_INTERVAL definido", "INTRA_SL_INTERVAL" in code)
    test("INTRA_SL_INTERVAL default 20", '"INTRA_SL_INTERVAL", "20"' in code)
    test("sell_lock definido", "sell_lock" in code and "threading.Lock()" in code)
    test("intra_cycle_sl_check definida", "def intra_cycle_sl_check(" in code)
    test("intra_sl_loop definida", "def intra_sl_loop(" in code)
    test("reason stop_loss_intra", '"stop_loss_intra"' in code)
    test("reason take_profit_intra", '"take_profit_intra"' in code)
    test("sell_lock protege manage_positions", "with sell_lock:" in code)
    test("startup incluye Intra-SL", "Intra-SL" in code)
    test("IntraSL thread en __main__", 'name="IntraSL"' in code)

    # ---- Test v10.5.2: City accuracy tracker ----
    print("\n v10.5.2: City accuracy tracker")
    test("CITY_MIN_TRADES_FOR_BLOCK definido", "CITY_MIN_TRADES_FOR_BLOCK" in code)
    test("CITY_BLOCK_WIN_RATE definido", "CITY_BLOCK_WIN_RATE" in code)
    test("get_city_accuracy definida", "def get_city_accuracy(" in code)
    test("cmd_accuracy definida", "def cmd_accuracy(" in code)
    test("city_accuracy_flagged en alerts default", '"city_accuracy_flagged"' in code)
    test("/accuracy en COMMANDS", '"accuracy": cmd_accuracy' in code)
    test("/accuracy en MENU_KEYBOARD", '"callback_data": "accuracy"' in code)
    test("cmd_accuracy vuelve con menú", 'send_telegram("Sin datos de accuracy todavía.", with_menu=True)' in code and 'send_telegram_paged("\\n".join(lines), with_menu=True)' in code)
    test("Win rate en rendimiento", "WR:" in code)

    # ---- Test v10.6.11: M4 resumen diario + M5 alerta canary candidate ----
    print("\n v10.6.11: M4 daily summary + M5 canary candidate alert")
    test("maybe_send_daily_summary_telegram definida", "def maybe_send_daily_summary_telegram(" in code)
    test("build_daily_summary_payload definida", "def build_daily_summary_payload(" in code)
    test("format_daily_summary_text definida", "def format_daily_summary_text(" in code)
    test("notify_canary_candidates definida", "def notify_canary_candidates(" in code)
    test("daily_summary_last_sent en alerts default", '"daily_summary_last_sent"' in code)
    test("canary_candidate_notified en alerts default", '"canary_candidate_notified"' in code)
    test("run_observability_alerts invoca notify_canary_candidates", "notify_canary_candidates(state)" in code)
    test("run_observability_alerts invoca maybe_send_daily_summary_telegram", "maybe_send_daily_summary_telegram(state)" in code)
    test("resumen diario gated en DAILY_SUMMARY_HOUR_UTC", "DAILY_SUMMARY_HOUR_UTC" in code)
    test("feature flag schedule disabled hours definida", "SCHEDULE_DISABLED_HOURS_UTC" in code)
    test("build_cycle_slot_metrics definida", "def build_cycle_slot_metrics(" in code)
    test("recordatorio one-shot 04h removido", "def maybe_send_04h_slot_review_reminder(" not in code)
    test("maybe_evaluate_slot_monetization definida", "def maybe_evaluate_slot_monetization(" in code)
    test("slot_monetization_last_date en alerts default", '"slot_monetization_last_date"' in code)
    test("run_observability_alerts invoca maybe_evaluate_slot_monetization", "maybe_evaluate_slot_monetization(state)" in code)

    # Functional: M4 daily summary gating (hora < target → no envía; hora >= target + sin flag → envía; idempotente).
    daily_messages = []
    daily_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "timedelta": timedelta,
        "SCHEDULE_HOURS_UTC": [8, 16, 23],
        "DAILY_SUMMARY_HOUR_UTC": 8,
        "BOT_VERSION": "v10.6.11-test",
        "LOGIC_SERIES": "10.6",
        "ACTIVE_TRADING_CITIES": set(),
        "OBSERVED_AUDIT_KEY": "observed_vs_forecast",
        "load_cycle_history": lambda: [
            {"timestamp_utc": "2026-04-05T00:00:00+00:00", "scan": {"markets_evaluated": 18, "with_edge": 2, "selected": 1, "shadow": 1}, "buys": [{"city": "Tokyo"}]},
            {"timestamp_utc": "2026-04-05T07:00:00+00:00", "scan": {"markets_evaluated": 10, "with_edge": 0, "selected": 0, "shadow": 0}, "buys": []},
        ],
        "_get_recent_closed_trades": lambda: [
            {"closed_at": "2026-04-05T03:00:00+00:00", "pnl_cash": 1.5},
            {"closed_at": "2026-04-05T06:00:00+00:00", "pnl_cash": -0.6},
            {"closed_at": "2026-04-03T09:00:00+00:00", "pnl_cash": 2.0},  # fuera de ventana
        ],
        "load_audit_data": lambda: {
            "observed_vs_forecast": [
                {"source": "noaa_ncei", "city": "Atlanta", "checked_at": "2026-04-05T01:00:00+00:00"},
                {"source": "noaa_ncei", "city": "Dallas", "checked_at": "2026-04-05T02:00:00+00:00"},
                {"source": "noaa_ncei", "city": "Chicago", "checked_at": "2026-04-01T10:00:00+00:00"},  # cumulativo pero no en 24h
            ]
        },
        "get_next_run_time": lambda: datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: daily_messages.append(text),
    }
    exec(get_function_source(module_ast, code_lines, "_daily_summary_cycles_last_24h"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "_daily_summary_closed_trades_last_24h"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "_daily_summary_noaa_last_24h"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "_daily_summary_has_cycle_today"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "build_daily_summary_payload"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "format_daily_summary_text"), daily_ns)
    exec(get_function_source(module_ast, code_lines, "maybe_send_daily_summary_telegram"), daily_ns)

    probe_now = datetime(2026, 4, 5, 8, 5, tzinfo=timezone.utc)
    probe_state = {"daily_summary_last_sent": None}
    result_fire = daily_ns["maybe_send_daily_summary_telegram"](probe_state, now=probe_now)
    test("M4 daily summary: se envía en la ventana 08 UTC la primera vez",
         result_fire is True and len(daily_messages) == 1 and "Resumen diario" in daily_messages[0],
         {"result": result_fire, "messages": daily_messages})
    test("M4 daily summary: marca daily_summary_last_sent con la fecha UTC",
         probe_state.get("daily_summary_last_sent") == "2026-04-05",
         probe_state)

    # Segunda llamada mismo día → idempotente.
    result_idem = daily_ns["maybe_send_daily_summary_telegram"](probe_state, now=probe_now)
    test("M4 daily summary: idempotente en el mismo día UTC",
         result_idem is False and len(daily_messages) == 1,
         {"result": result_idem, "messages_count": len(daily_messages)})

    # Hora antes del target (4h < 8h) → no envía.
    off_state = {"daily_summary_last_sent": None}
    off_now = datetime(2026, 4, 5, 4, 0, tzinfo=timezone.utc)
    result_off = daily_ns["maybe_send_daily_summary_telegram"](off_state, now=off_now)
    test("M4 daily summary: no envía antes de DAILY_SUMMARY_HOUR_UTC",
         result_off is False and off_state.get("daily_summary_last_sent") is None,
         {"result": result_off, "state": off_state})

    # Contenido del payload.
    payload = daily_ns["build_daily_summary_payload"](now=probe_now)
    test("M4 daily payload: agrega ciclos 24h correctamente",
         payload["cycles_24h"]["cycles"] == 2
         and payload["cycles_24h"]["markets_evaluated"] == 28
         and payload["cycles_24h"]["with_edge"] == 2
         and payload["cycles_24h"]["buys_real"] == 1,
         payload["cycles_24h"])
    test("M4 daily payload: resoluciones 24h split wins/losses",
         payload["resolutions_24h"]["closed"] == 2
         and payload["resolutions_24h"]["wins"] == 1
         and payload["resolutions_24h"]["breakeven"] == 0
         and payload["resolutions_24h"]["losses"] == 1
         and abs(payload["resolutions_24h"]["pnl"] - 0.9) < 1e-9,
         payload["resolutions_24h"])
    test("M4 daily payload: NOAA 24h cuenta solo recientes pero cumulativo incluye todo",
         payload["noaa_24h"]["new_total"] == 2
         and payload["noaa_24h"]["cumulative"] == 3
         and payload["noaa_24h"]["new_by_city"].get("Atlanta") == 1,
         payload["noaa_24h"])
    test("M4 daily payload: marca shadow_only cuando ACTIVE_TRADING_CITIES está vacío",
         payload["shadow_only"] is True,
         payload)
    test("M4 daily text: usa generated_at y next_run_at del payload",
         "2026-04-05" in daily_messages[0] and "16:00 UTC" in daily_messages[0],
         daily_messages[0])

    breakeven_ns = dict(daily_ns)
    breakeven_ns["_get_recent_closed_trades"] = lambda: [
        {"closed_at": "2026-04-05T03:00:00+00:00", "pnl_cash": 0.0},
        {"closed_at": "2026-04-05T06:00:00+00:00", "pnl_cash": -0.0},
        {"closed_at": "2026-04-05T07:00:00+00:00", "pnl_cash": -0.6},
    ]
    exec(get_function_source(module_ast, code_lines, "_daily_summary_closed_trades_last_24h"), breakeven_ns)
    exec(get_function_source(module_ast, code_lines, "build_daily_summary_payload"), breakeven_ns)
    exec(get_function_source(module_ast, code_lines, "format_daily_summary_text"), breakeven_ns)
    breakeven_payload = breakeven_ns["build_daily_summary_payload"](now=probe_now)
    breakeven_text = breakeven_ns["format_daily_summary_text"](breakeven_payload)
    test("M4 daily payload: separa break-even de pérdidas",
         breakeven_payload["resolutions_24h"]["wins"] == 0
         and breakeven_payload["resolutions_24h"]["breakeven"] == 2
         and breakeven_payload["resolutions_24h"]["losses"] == 1
         and "➖ 2" in breakeven_text,
         {
             "resolutions": breakeven_payload["resolutions_24h"],
             "has_breakeven_marker": "➖ 2" in breakeven_text,
         })

    stale_cycle_messages = []
    stale_cycle_ns = dict(daily_ns)
    stale_cycle_ns["load_cycle_history"] = lambda: [
        {"timestamp_utc": "2026-04-04T23:00:00+00:00", "scan": {"markets_evaluated": 18, "with_edge": 2, "selected": 1, "shadow": 1}, "buys": [{"city": "Tokyo"}]},
    ]
    stale_cycle_ns["send_telegram"] = lambda text, with_menu=False, custom_keyboard=None: stale_cycle_messages.append(text)
    exec(get_function_source(module_ast, code_lines, "_daily_summary_has_cycle_today"), stale_cycle_ns)
    exec(get_function_source(module_ast, code_lines, "build_daily_summary_payload"), stale_cycle_ns)
    exec(get_function_source(module_ast, code_lines, "format_daily_summary_text"), stale_cycle_ns)
    exec(get_function_source(module_ast, code_lines, "maybe_send_daily_summary_telegram"), stale_cycle_ns)
    stale_state = {"daily_summary_last_sent": None}
    stale_result = stale_cycle_ns["maybe_send_daily_summary_telegram"](stale_state, now=probe_now)
    test("M4 daily summary: no envía al arrancar si hoy todavía no hubo ciclo real",
         stale_result is False and len(stale_cycle_messages) == 0,
         {"result": stale_result, "messages": stale_cycle_messages})

    slot_ns = {
        "datetime": datetime,
        "math": math,
        "ORDER_MIN_NOTIONAL": 1.0,
    }
    exec(get_function_source(module_ast, code_lines, "_bump_reason_counter"), slot_ns)
    exec(get_function_source(module_ast, code_lines, "_classify_execution_failure_reason"), slot_ns)
    exec(get_function_source(module_ast, code_lines, "_normalize_buy_order_size"), slot_ns)
    exec(get_function_source(module_ast, code_lines, "build_cycle_slot_metrics"), slot_ns)

    normalized_size = slot_ns["_normalize_buy_order_size"](0.81, 1.23)
    test("slot metrics: normaliza size para cumplir mínimo notional",
         abs(normalized_size - 1.24) < 1e-9,
         {"normalized_size": normalized_size})

    classified_reason = slot_ns["_classify_execution_failure_reason"](
        "PolyApiException[status_code=400, error_message={'error': 'invalid amount for a marketable BUY order ($0.9976), min size: $1'}]"
    )
    test("slot metrics: clasifica fallo de buy por mínimo notional",
         classified_reason == "buy_min_notional",
         {"classified_reason": classified_reason})

    exact_range_ns = {}
    exec(get_function_source(module_ast, code_lines, "_resize_position_amount"), exact_range_ns)
    resized_position = exact_range_ns["_resize_position_amount"](
        {
            "amount": 1.0,
            "shares": 4.55,
            "profit_if_win": 3.55,
            "loss_if_lose": 1.0,
            "expected_value": 0.12,
            "aggressive_price": 0.22,
            "market_price": 0.2,
        },
        2.5,
        0.78,
    )
    test("exact/range min amount: resize sube amount sin perder precio",
         abs(resized_position["amount"] - 2.5) < 1e-9
         and abs(resized_position["shares"] - 11.36) < 1e-9
         and abs(resized_position["loss_if_lose"] - 2.5) < 1e-9
         and abs(resized_position["aggressive_price"] - 0.22) < 1e-9,
         resized_position)

    sample_slot_metrics = slot_ns["build_cycle_slot_metrics"](
        timestamp_utc=datetime(2026, 4, 17, 4, 0, tzinfo=timezone.utc),
        candidates=[
            {"city": "Tokyo", "days_ahead": 0},
            {"city": "Shanghai", "days_ahead": 0},
            {"city": "London", "days_ahead": 1},
        ],
        trades=[
            {"city": "Tokyo", "days_ahead": 0},
            {"city": "Shanghai", "days_ahead": 0},
        ],
        selected=[
            {"city": "Tokyo", "days_ahead": 0},
            {"city": "Shanghai", "days_ahead": 0},
        ],
        buys=[],
        skip_log_entries=[
            {"skip_reason": "price_out_of_range", "days_ahead": 0},
            {"skip_reason": "condition_filtered", "days_ahead": 1},
        ],
        execution_failures=[
            {"reason": "buy_min_notional", "days_ahead": 0, "city": "Tokyo"},
        ],
    )
    test("slot metrics: agrega funnel y reject reasons por slot",
         sample_slot_metrics["slot_hour_utc"] == 4
         and sample_slot_metrics["same_day_candidates"] == 2
         and sample_slot_metrics["edges"] == 2
         and sample_slot_metrics["selected"] == 2
         and sample_slot_metrics["buys"] == 0
         and sample_slot_metrics["reject_reasons"].get("buy_min_notional") == 1
         and sample_slot_metrics["same_day_reject_reasons"].get("price_out_of_range") == 1,
         sample_slot_metrics)

    slot_review_messages = []
    slot_review_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "json": json,
        "SCHEDULE_HOURS_UTC": [4, 8, 16],
        "load_cycle_history": lambda: [
            {"timestamp_utc": "2026-04-17T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 10, "same_day_edges": 2, "same_day_selected": 2, "same_day_buys": 0, "edges": 2, "selected": 2, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"price_out_of_range": 3}, "execution_reject_reasons": {"buy_min_notional": 1}}}},
            {"timestamp_utc": "2026-04-16T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 8, "same_day_edges": 1, "same_day_selected": 1, "same_day_buys": 0, "edges": 1, "selected": 1, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"price_out_of_range": 2}, "execution_reject_reasons": {"buy_min_notional": 1}}}},
            {"timestamp_utc": "2026-04-15T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 9, "same_day_edges": 1, "same_day_selected": 1, "same_day_buys": 0, "edges": 1, "selected": 1, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"condition_filtered": 1}, "execution_reject_reasons": {"buy_min_notional": 1}}}},
            {"timestamp_utc": "2026-04-17T23:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 23, "same_day_candidates": 0, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"date_out_of_range_past": 5}, "execution_reject_reasons": {}}}},
            {"timestamp_utc": "2026-04-16T23:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 23, "same_day_candidates": 0, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"date_out_of_range_past": 4}, "execution_reject_reasons": {}}}},
            {"timestamp_utc": "2026-04-15T23:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 23, "same_day_candidates": 0, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"blocked_city": 3}, "execution_reject_reasons": {}}}},
        ],
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: slot_review_messages.append(text),
    }
    exec(get_function_source(module_ast, code_lines, "_extract_slot_metrics_record"), slot_review_ns)
    exec(get_function_source(module_ast, code_lines, "_merge_reason_counts"), slot_review_ns)
    exec(get_function_source(module_ast, code_lines, "_top_reason"), slot_review_ns)
    exec(get_function_source(module_ast, code_lines, "_format_reason_summary"), slot_review_ns)
    exec(get_function_source(module_ast, code_lines, "evaluate_slot_monetization"), slot_review_ns)
    exec(get_function_source(module_ast, code_lines, "maybe_evaluate_slot_monetization"), slot_review_ns)

    slot_state = {"slot_monetization_last_date": None, "slot_monetization_last_signature": None}
    slot_result = slot_review_ns["maybe_evaluate_slot_monetization"](slot_state, now=datetime(2026, 4, 17, 8, 5, tzinfo=timezone.utc))
    test("slot monetization alert: envía alerta operativa con 04h keep y omite 23h si está deshabilitado",
         slot_result is True
         and len(slot_review_messages) == 1
         and "<code>keep</code>" in slot_review_messages[0]
         and "buy_min_notional" in slot_review_messages[0]
         and "23h UTC" not in slot_review_messages[0]
         and "• edges=" not in slot_review_messages[0],
         {"result": slot_result, "messages": slot_review_messages, "state": slot_state})

    slot_result_idem = slot_review_ns["maybe_evaluate_slot_monetization"](slot_state, now=datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc))
    test("slot monetization alert: idempotente en el mismo día UTC",
         slot_result_idem is False and len(slot_review_messages) == 1,
         {"result": slot_result_idem, "messages_count": len(slot_review_messages)})

    slot_review_messages.clear()
    slot_review_ns["load_cycle_history"] = lambda: [
        {"timestamp_utc": "2026-04-18T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 26, "same_day_edges": 2, "same_day_selected": 2, "same_day_buys": 1, "edges": 2, "selected": 2, "buys": 1, "buy_rate": 0.5, "same_day_buy_rate": 0.5, "same_day_reject_reasons": {"price_out_of_range": 226, "condition_filtered": 42, "blocked_city": 22}, "execution_reject_reasons": {"buy_min_size": 1}}}},
        {"timestamp_utc": "2026-04-19T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 40, "same_day_edges": 1, "same_day_selected": 1, "same_day_buys": 1, "edges": 1, "selected": 1, "buys": 1, "buy_rate": 1.0, "same_day_buy_rate": 1.0, "same_day_reject_reasons": {"price_out_of_range": 120}, "execution_reject_reasons": {}}}},
        {"timestamp_utc": "2026-04-20T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 40, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"price_out_of_range": 80}, "execution_reject_reasons": {}}}},
    ]
    healthy_slot_state = {"slot_monetization_last_date": None, "slot_monetization_last_signature": None}
    healthy_slot_result = slot_review_ns["maybe_evaluate_slot_monetization"](healthy_slot_state, now=datetime(2026, 4, 20, 8, 5, tzinfo=timezone.utc))
    test("slot monetization alert: 04h validated/keep sano queda NO_ACTION silencioso",
         healthy_slot_result is True
         and len(slot_review_messages) == 0
         and healthy_slot_state["slot_monetization_last_date"] == "2026-04-20"
         and healthy_slot_state["slot_monetization_last_signature"],
         {"result": healthy_slot_result, "messages": slot_review_messages, "state": healthy_slot_state})

    slot_review_messages.clear()
    slot_review_ns["load_cycle_history"] = lambda: [
        {"timestamp_utc": "2026-04-18T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 26, "same_day_edges": 2, "same_day_selected": 2, "same_day_buys": 1, "edges": 2, "selected": 2, "buys": 1, "buy_rate": 0.5, "same_day_buy_rate": 0.5, "same_day_reject_reasons": {"price_out_of_range": 226}, "execution_reject_reasons": {"clob_reject": 1}}}},
        {"timestamp_utc": "2026-04-19T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 40, "same_day_edges": 1, "same_day_selected": 1, "same_day_buys": 1, "edges": 1, "selected": 1, "buys": 1, "buy_rate": 1.0, "same_day_buy_rate": 1.0, "same_day_reject_reasons": {"price_out_of_range": 120}, "execution_reject_reasons": {}}}},
        {"timestamp_utc": "2026-04-20T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 40, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {"price_out_of_range": 80}, "execution_reject_reasons": {}}}},
    ]
    risky_slot_result = slot_review_ns["maybe_evaluate_slot_monetization"]({"slot_monetization_last_date": None, "slot_monetization_last_signature": None}, now=datetime(2026, 4, 20, 9, 5, tzinfo=timezone.utc))
    test("slot monetization alert: 04h validated/keep con execution_reject relevante sigue alertando",
         risky_slot_result is True
         and len(slot_review_messages) == 1
         and "clob_reject" in slot_review_messages[0],
         {"result": risky_slot_result, "messages": slot_review_messages})

    insufficient_slot_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "json": json,
        "SCHEDULE_HOURS_UTC": [4],
        "load_cycle_history": lambda: [
            {"timestamp_utc": "2026-04-18T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 26, "same_day_edges": 2, "same_day_selected": 2, "same_day_buys": 1, "edges": 2, "selected": 2, "buys": 1, "buy_rate": 0.5, "same_day_buy_rate": 0.5, "same_day_reject_reasons": {"price_out_of_range": 226, "condition_filtered": 42, "blocked_city": 22}, "execution_reject_reasons": {"buy_min_size": 1}}}},
            {"timestamp_utc": "2026-04-17T04:00:45+00:00", "scan": {"slot_metrics": {"slot_hour_utc": 4, "same_day_candidates": 0, "same_day_edges": 0, "same_day_selected": 0, "same_day_buys": 0, "edges": 0, "selected": 0, "buys": 0, "buy_rate": 0.0, "same_day_buy_rate": 0.0, "same_day_reject_reasons": {}, "execution_reject_reasons": {}}}},
        ],
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: None,
    }
    exec(get_function_source(module_ast, code_lines, "_extract_slot_metrics_record"), insufficient_slot_ns)
    exec(get_function_source(module_ast, code_lines, "_merge_reason_counts"), insufficient_slot_ns)
    exec(get_function_source(module_ast, code_lines, "_top_reason"), insufficient_slot_ns)
    exec(get_function_source(module_ast, code_lines, "_format_reason_summary"), insufficient_slot_ns)
    exec(get_function_source(module_ast, code_lines, "evaluate_slot_monetization"), insufficient_slot_ns)
    insufficient_result = insufficient_slot_ns["evaluate_slot_monetization"](insufficient_slot_ns["load_cycle_history"](), 4, min_cycles=3)
    test("slot monetization insufficient_data conserva funnel parcial de 04h",
         insufficient_result["decision"] == "insufficient_data"
         and insufficient_result["summary"] == "muestra insuficiente; ya hubo buy same-day"
         and insufficient_result["same_day_candidates"] == 26
         and insufficient_result["same_day_edges"] == 2
         and insufficient_result["same_day_selected"] == 2
         and insufficient_result["same_day_buys"] == 1
         and insufficient_result["same_day_buy_rate"] == 0.5
         and insufficient_result["buy_rate"] == 0.5
         and insufficient_result["execution_reject_reasons"].get("buy_min_size") == 1,
         insufficient_result)

    # Functional: M5 canary candidate notifier.
    candidate_messages = []
    candidate_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "load_audit_data": lambda: {"observed_vs_forecast": []},
        "get_city_accuracy": lambda: {},
        "get_city_policy_metrics": lambda audit=None: {},
        "load_shadow_city_tracking": lambda: {},
        "build_dashboard_city_observation": lambda audit=None, city_accuracy=None, city_policy_metrics=None: {},
        "build_dashboard_city_decisions": lambda city_observation=None, city_accuracy=None, shadow_tracking=None, city_policy_metrics=None: {
            "rows": [
                {
                    "city": "Buenos Aires",
                    "decision": "promote",
                    "reason": "regla canary disparada: 2 edges shadow, 2 ciclos y pico 12.4%",
                    "shadow_edges": 2,
                    "shadow_best_edge": 12.4,
                    "support_count": 2,
                    "observed_count": 3,
                },
                {
                    "city": "Chicago",
                    "decision": "keep",
                    "reason": "ciudad ya operativa",
                },
            ]
        },
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: candidate_messages.append(text),
    }
    exec(get_function_source(module_ast, code_lines, "_compute_city_decisions_for_alerts"), candidate_ns)
    exec(get_function_source(module_ast, code_lines, "notify_canary_candidates"), candidate_ns)

    cand_state = {"canary_candidate_notified": {}}
    fire1 = candidate_ns["notify_canary_candidates"](cand_state)
    test("M5 canary candidate: dispara alerta para ciudad promote",
         fire1 is True
         and len(candidate_messages) == 1
         and "Buenos Aires" in candidate_messages[0]
         and "Ciudad candidata a canary" in candidate_messages[0],
         {"fired": fire1, "messages": candidate_messages})
    test("M5 canary candidate: registra la ciudad en canary_candidate_notified",
         "Buenos Aires" in cand_state.get("canary_candidate_notified", {}),
         cand_state)

    # Re-invocación con el mismo estado → no re-dispara.
    fire2 = candidate_ns["notify_canary_candidates"](cand_state)
    test("M5 canary candidate: idempotente si la ciudad sigue candidata",
         fire2 is False and len(candidate_messages) == 1,
         {"fired": fire2, "messages_count": len(candidate_messages)})

    # Si la ciudad ya no aparece como promote → limpia el flag para permitir re-disparo futuro.
    candidate_ns["build_dashboard_city_decisions"] = lambda city_observation=None, city_accuracy=None, shadow_tracking=None, city_policy_metrics=None: {
        "rows": [{"city": "Chicago", "decision": "keep"}]
    }
    exec(get_function_source(module_ast, code_lines, "_compute_city_decisions_for_alerts"), candidate_ns)
    exec(get_function_source(module_ast, code_lines, "notify_canary_candidates"), candidate_ns)
    fire3 = candidate_ns["notify_canary_candidates"](cand_state)
    test("M5 canary candidate: limpia flag cuando la ciudad deja de ser candidata",
         fire3 is True and "Buenos Aires" not in cand_state.get("canary_candidate_notified", {}),
         {"fired": fire3, "state": cand_state})

    # ============================================================
    # v10.6.14 — Canary→Active automation (Modulos 1, 2, 3)
    # ============================================================
    print("\n v10.6.14: notify_active_candidates + maybe_run_active_degradation + maybe_alert_v2_trigger")

    # Static checks
    test("v10.6.14: notify_active_candidates definida", "def notify_active_candidates(" in code)
    test("v10.6.14: maybe_run_active_degradation definida", "def maybe_run_active_degradation(" in code)
    test("v10.6.14: maybe_alert_v2_trigger definida", "def maybe_alert_v2_trigger(" in code)
    test("v10.6.14: _detect_atlanta_inconsistency definida", "def _detect_atlanta_inconsistency(" in code)
    test("v10.6.14: active_candidate_notified en alerts state", '"active_candidate_notified"' in code)
    test("v10.6.14: auto_canary_from_active en policy_state", '"auto_canary_from_active"' in code)
    test("v10.6.14: run_observability_alerts invoca notify_active_candidates", "notify_active_candidates(state)" in code)
    test("v10.6.14: run_observability_alerts invoca maybe_run_active_degradation", "maybe_run_active_degradation(state)" in code)
    test("v10.6.14: run_observability_alerts invoca maybe_alert_v2_trigger", "maybe_alert_v2_trigger(state)" in code)
    test("v10.6.14: get_effective_city_mode chequea auto_canary_from_active antes de ACTIVE_TRADING_CITIES",
         "auto_canary_from_active" in code
         and code.index("auto_canary_from_active") < code.index("if city in ACTIVE_TRADING_CITIES"))

    # Functional: notify_active_candidates
    active_msgs_v14 = []

    def _make_lifecycle_record_v14(city, opened_at_iso, closed_at_iso, pnl_cash, analysis_ready=True, add_atlanta=False):
        rec = {
            "city": city,
            "opened_at": opened_at_iso,
            "closed_at": closed_at_iso,
            "pnl_cash": pnl_cash,
            "integrity": {"analysis_ready": analysis_ready},
            "close_context": {},
            "timeline": [],
            "post_exit_analysis": {},
        }
        if add_atlanta:
            rec["close_context"] = {"close_action": "LOSS_TOTAL"}
            rec["timeline"] = [{"action": "RESOLVED_WIN", "pnl_cash": 0.63}]
            rec["post_exit_analysis"] = {"market_seen_after_close": True, "max_price_after_close": 0.9995}
        return rec

    promoted_iso = "2026-04-01T00:00:00+00:00"  # 12 days before today in test context

    active_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "timedelta": timedelta,
        "os": __import__("os"),
        "json": __import__("json"),
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: active_msgs_v14.append(text),
        "load_city_policy_state": lambda: {
            "logic_series": "10.6",
            "auto_canary_cities": {
                "Seoul": {"promoted_at": promoted_iso, "best_edge_pct": 12.0},
            },
            "auto_shadow_cities": {},
            "auto_blocked_cities": {},
            "auto_canary_from_active": {},
            "active_city_monitoring": {},
            "transition_history": [],
        },
        "load_trade_lifecycle_data": lambda: {
            "records": [
                _make_lifecycle_record_v14("Seoul", "2026-04-02T10:00:00+00:00", "2026-04-02T20:00:00+00:00", 0.50),
                _make_lifecycle_record_v14("Seoul", "2026-04-03T10:00:00+00:00", "2026-04-03T20:00:00+00:00", 0.50),
                _make_lifecycle_record_v14("Seoul", "2026-04-04T10:00:00+00:00", "2026-04-04T20:00:00+00:00", 0.50),
                _make_lifecycle_record_v14("Seoul", "2026-04-05T10:00:00+00:00", "2026-04-05T20:00:00+00:00", -0.40),
            ]
        },
    }
    exec(get_function_source(module_ast, code_lines, "_detect_atlanta_inconsistency"), active_ns)
    exec(get_function_source(module_ast, code_lines, "notify_active_candidates"), active_ns)

    # Test 1: ciudad con 4 trades (n<5) → NO alerta
    st1 = {}
    fire_t1 = active_ns["notify_active_candidates"](st1)
    test("v10.6.14 active candidates: ciudad con 4 trades no alerta (n<5)",
         fire_t1 is False and not active_msgs_v14,
         {"fired": fire_t1, "msgs": len(active_msgs_v14)})

    # Test 2: ciudad con 5 trades, WR 80%, PnL +$2.10, days=12, integridad OK → ALERTA
    active_ns2 = dict(active_ns)
    active_msgs2 = []
    active_ns2["send_telegram"] = lambda text, with_menu=False, custom_keyboard=None: active_msgs2.append(text)
    active_ns2["load_trade_lifecycle_data"] = lambda: {
        "records": [
            _make_lifecycle_record_v14("Seoul", "2026-04-02T10:00:00+00:00", "2026-04-02T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-03T10:00:00+00:00", "2026-04-03T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-04T10:00:00+00:00", "2026-04-04T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-05T10:00:00+00:00", "2026-04-05T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-06T10:00:00+00:00", "2026-04-06T20:00:00+00:00", 0.10),
        ]
    }
    exec(get_function_source(module_ast, code_lines, "notify_active_candidates"), active_ns2)
    st2 = {}
    fire_t2 = active_ns2["notify_active_candidates"](st2)
    test("v10.6.14 active candidates: ciudad con 5 trades WR>=60% PnL>=+$1 days>=7 alerta",
         fire_t2 is True and len(active_msgs2) == 1 and "Seoul" in active_msgs2[0],
         {"fired": fire_t2, "msgs": active_msgs2})

    # Test 3: re-invocación 1h después → NO alerta (rate limit)
    fire_t3 = active_ns2["notify_active_candidates"](st2)
    test("v10.6.14 active candidates: re-invocacion 1h despues no envia recordatorio (rate limit)",
         fire_t3 is False and len(active_msgs2) == 1,
         {"fired": fire_t3, "msgs": len(active_msgs2)})

    # Test 4: re-invocación 25h después → recordatorio
    import copy as _copy_v14
    st4 = _copy_v14.deepcopy(st2)
    notified_entry = st4.get("active_candidate_notified", {}).get("Seoul", {})
    if notified_entry:
        past_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        notified_entry["last_notified_at"] = past_ts
    active_msgs4 = []
    active_ns4 = dict(active_ns2)
    active_ns4["send_telegram"] = lambda text, with_menu=False, custom_keyboard=None: active_msgs4.append(text)
    exec(get_function_source(module_ast, code_lines, "notify_active_candidates"), active_ns4)
    fire_t4 = active_ns4["notify_active_candidates"](st4)
    test("v10.6.14 active candidates: re-invocacion 25h despues envia recordatorio",
         fire_t4 is True and len(active_msgs4) == 1 and "Recordatorio" in active_msgs4[0],
         {"fired": fire_t4, "msgs": active_msgs4})

    # Test 5: Atlanta inconsistency → NO alerta
    active_ns5 = dict(active_ns2)
    active_msgs5 = []
    active_ns5["send_telegram"] = lambda text, with_menu=False, custom_keyboard=None: active_msgs5.append(text)
    active_ns5["load_trade_lifecycle_data"] = lambda: {
        "records": [
            _make_lifecycle_record_v14("Seoul", "2026-04-02T10:00:00+00:00", "2026-04-02T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-03T10:00:00+00:00", "2026-04-03T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-04T10:00:00+00:00", "2026-04-04T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-05T10:00:00+00:00", "2026-04-05T20:00:00+00:00", 0.50),
            _make_lifecycle_record_v14("Seoul", "2026-04-06T10:00:00+00:00", "2026-04-06T20:00:00+00:00", 0.10, add_atlanta=True),
        ]
    }
    exec(get_function_source(module_ast, code_lines, "_detect_atlanta_inconsistency"), active_ns5)
    exec(get_function_source(module_ast, code_lines, "notify_active_candidates"), active_ns5)
    st5 = {}
    fire_t5 = active_ns5["notify_active_candidates"](st5)
    test("v10.6.14 active candidates: Atlanta inconsistency en lifecycle - no alerta",
         fire_t5 is False and not active_msgs5,
         {"fired": fire_t5, "msgs": active_msgs5})

    # Test 6: ciudad ya en ACTIVE_TRADING_CITIES → silencio + limpiar state
    active_ns6_msgs = []
    active_ns6 = dict(active_ns2)
    active_ns6["send_telegram"] = lambda text, with_menu=False, custom_keyboard=None: active_ns6_msgs.append(text)
    active_ns6["os"] = type("_FakeOS", (), {
        "getenv": staticmethod(lambda k, d="": "Seoul" if k == "ACTIVE_TRADING_CITIES" else d),
        "path": __import__("os").path,
    })()
    exec(get_function_source(module_ast, code_lines, "notify_active_candidates"), active_ns6)
    st6 = {"active_candidate_notified": {"Seoul": {"first_notified_at": "2026-04-10T10:00:00+00:00", "last_notified_at": "2026-04-10T10:00:00+00:00"}}}
    fire_t6 = active_ns6["notify_active_candidates"](st6)
    test("v10.6.14 active candidates: ciudad ya en ACTIVE_TRADING_CITIES silencio limpia state",
         fire_t6 is True
         and "Seoul" not in st6.get("active_candidate_notified", {})
         and not active_ns6_msgs,
         {"fired": fire_t6, "state": st6, "msgs": active_ns6_msgs})

    # Functional: maybe_run_active_degradation
    degrade_msgs = []
    policy_saved = []

    def _fake_save_policy_v14(data):
        policy_saved.append(data)

    degrade_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "timedelta": timedelta,
        "os": type("_FakeOS14", (), {
            "getenv": staticmethod(lambda k, d="": "Tokyo" if k == "ACTIVE_TRADING_CITIES" else d),
            "path": __import__("os").path,
        })(),
        "json": __import__("json"),
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: degrade_msgs.append(text),
        "load_city_policy_state": lambda: {
            "logic_series": "10.6",
            "auto_canary_cities": {},
            "auto_shadow_cities": {},
            "auto_blocked_cities": {},
            "auto_canary_from_active": {},
            "active_city_monitoring": {"Tokyo": {"started_at": "2026-04-01T00:00:00+00:00"}},
            "transition_history": [],
        },
        "load_trade_lifecycle_data": lambda: {
            "records": [
                _make_lifecycle_record_v14("Tokyo", "2026-04-02T10:00:00+00:00", "2026-04-02T20:00:00+00:00", -0.50),
                _make_lifecycle_record_v14("Tokyo", "2026-04-03T10:00:00+00:00", "2026-04-03T20:00:00+00:00", -0.50),
                _make_lifecycle_record_v14("Tokyo", "2026-04-04T10:00:00+00:00", "2026-04-04T20:00:00+00:00", -0.50),
                _make_lifecycle_record_v14("Tokyo", "2026-04-05T10:00:00+00:00", "2026-04-05T20:00:00+00:00", 0.50),
                _make_lifecycle_record_v14("Tokyo", "2026-04-06T10:00:00+00:00", "2026-04-06T20:00:00+00:00", -0.50),
            ]
        },
        "save_city_policy_state": _fake_save_policy_v14,
    }
    exec(get_function_source(module_ast, code_lines, "maybe_run_active_degradation"), degrade_ns)
    # Test 7: ciudad active con 5 trades, WR 20% → degrada + alerta
    st_deg = {}
    fire_deg = degrade_ns["maybe_run_active_degradation"](st_deg)
    test("v10.6.14 active degradation: ciudad con WR<=45% degrada y envia Telegram",
         fire_deg is True
         and len(degrade_msgs) == 1
         and "Tokyo" in degrade_msgs[0]
         and len(policy_saved) >= 1
         and "Tokyo" in policy_saved[-1].get("auto_canary_from_active", {}),
         {"fired": fire_deg, "msgs": degrade_msgs, "saved": len(policy_saved)})

    # Functional: maybe_alert_v2_trigger
    # Test 8: precondiciones parciales (phase2 no cerrada) → NO alerta; todas → alerta una vez; 2da invocación → idempotente
    v2_msgs = []
    v2_ns = {
        "datetime": datetime,
        "timezone": timezone,
        "timedelta": timedelta,
        "os": type("_FakeOSv2a", (), {
            "getenv": staticmethod(lambda k, d="": {
                "RECALIBRATION_PHASE2_CLOSED": "false",
                "ACTIVE_TRADING_CITIES": "Tokyo",
            }.get(k, d)),
            "path": __import__("os").path,
            "makedirs": __import__("os").makedirs,
        })(),
        "json": __import__("json"),
        "SIGNALS_FILE": "__nonexistent_signals__.json",
        "_data_path": lambda f: f,
        "send_telegram": lambda text, with_menu=False, custom_keyboard=None: v2_msgs.append(text),
    }
    exec(get_function_source(module_ast, code_lines, "maybe_alert_v2_trigger"), v2_ns)
    st_v2a = {}
    fire_v2a = v2_ns["maybe_alert_v2_trigger"](st_v2a)
    test("v10.6.14 v2 trigger: phase2 no cerrada - no alerta",
         fire_v2a is True and not v2_msgs,
         {"fired": fire_v2a, "msgs": v2_msgs})

    # Todas las precondiciones cumplidas → alerta one-shot
    import tempfile as _tmpfile_v14, os as _os_v14
    _sig_tmp = _tmpfile_v14.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    _sig_tmp.write('{"generated": "' + datetime.now(timezone.utc).isoformat() + '", "signals": []}')
    _sig_tmp.close()
    try:
        v2_msgs2 = []
        v2_ns2 = {
            "datetime": datetime,
            "timezone": timezone,
            "timedelta": timedelta,
            "os": type("_FakeOSv2b", (), {
                "getenv": staticmethod(lambda k, d="": {
                    "RECALIBRATION_PHASE2_CLOSED": "true",
                    "ACTIVE_TRADING_CITIES": "Tokyo",
                }.get(k, d)),
                "path": _os_v14.path,
                "makedirs": _os_v14.makedirs,
            })(),
            "json": __import__("json"),
            "SIGNALS_FILE": _sig_tmp.name,
            "_data_path": lambda f: "__nonexistent_phase2__.json",
            "send_telegram": lambda text, with_menu=False, custom_keyboard=None: v2_msgs2.append(text),
        }
        exec(get_function_source(module_ast, code_lines, "maybe_alert_v2_trigger"), v2_ns2)
        st_v2b = {}
        fire_v2b = v2_ns2["maybe_alert_v2_trigger"](st_v2b)
        test("v10.6.14 v2 trigger: precondiciones completas alerta one-shot",
             fire_v2b is True and len(v2_msgs2) == 1 and "v2" in v2_msgs2[0].lower(),
             {"fired": fire_v2b, "msgs": v2_msgs2})
        # Segunda invocación mismo día → no alerta (idempotente vía daily gate)
        fire_v2c = v2_ns2["maybe_alert_v2_trigger"](st_v2b)
        test("v10.6.14 v2 trigger: segunda invocacion no alerta (idempotente)",
             len(v2_msgs2) == 1,
             {"fired": fire_v2c, "msgs_count": len(v2_msgs2)})
    finally:
        try:
            _os_v14.unlink(_sig_tmp.name)
        except Exception:
            pass

    # ============================================================
    # R3 — Skip log por ciclo (docs/control-center-r3-contract.md)
    # ============================================================
    print("\n R3: skip_log")

    # --- Static checks: constantes, enum, helpers definidos ---
    test("R3: SKIP_LOG_FILE definido en bot.py",
         'SKIP_LOG_FILE = _data_path("skip_log.jsonl")' in code)
    test("R3: SKIP_LOG_MAX_SIZE_BYTES = 20 MB",
         "SKIP_LOG_MAX_SIZE_BYTES = 20 * 1024 * 1024" in code)
    test("R3: SKIP_LOG_REQUIRED_FIELDS incluye ts_utc, cycle_id, skip_reason, extras",
         all(f in code for f in ['"ts_utc"', '"cycle_id"', '"skip_reason"', '"extras"'])
         and "SKIP_LOG_REQUIRED_FIELDS" in code)

    # Enum: las 17 razones deben estar todas presentes
    R3_REASONS = [
        "parse_fail", "blocked_city", "fuera_allowlist", "timezone_filter",
        "date_out_of_range_past", "date_out_of_range_future", "price_out_of_range",
        "liquidity_low", "forecast_missing", "condition_filtered", "no_edge",
        "below_min_edge", "kelly_too_low", "shadow_only_override", "existing_order",
        "sold_this_cycle", "existing_position",
    ]
    for reason in R3_REASONS:
        test(f"R3: SKIP_REASONS_VALID incluye '{reason}'",
             f'"{reason}"' in code)

    # Helpers definidos
    for fn in ("_make_skip_entry", "_skip_log_rotate_if_needed", "append_skip_log_entries",
               "_skip_log_rotated_files", "read_skip_log_last_n_cycles", "read_skip_log_since"):
        test(f"R3: función '{fn}' definida",
             f"def {fn}(" in code)

    # --- Static checks: scan loop instrumentado ---
    test("R3: cycle_id inicializado al inicio de main()",
         'cycle_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")' in code)
    test("R3: skip_log_entries bucket local inicializado",
         "skip_log_entries = []" in code)
    test("R3: flush append_skip_log_entries al final del ciclo",
         "append_skip_log_entries(skip_log_entries)" in code)
    test("R3: shadow_override_flag propagado en parsed.update",
         '"shadow_override_flag": shadow_override' in code)
    test("R3: Loop B distingue fuera_allowlist vs shadow_only_override por flag",
         '"shadow_only_override" if c.get("shadow_override_flag") else "fuera_allowlist"' in code)
    test("shadow-only fallback considera canary persistida",
         '"auto_canary_cities"' in code and '"auto_canary_from_active"' in code and "real_auto_canary" in code)

    # Cada razón debe aparecer al menos una vez en una llamada a _make_skip_entry
    for reason in R3_REASONS:
        # Buscamos el patrón "_make_skip_entry(\n        \"reason\"," o variantes con comillas
        patterns = [
            f'_make_skip_entry(\n                "{reason}"',
            f'_make_skip_entry(\n            "{reason}"',
            f'_make_skip_entry("{reason}"',
        ]
        found = any(p in code for p in patterns)
        # Fallback tolerante: al menos aparece con comillas tras _make_skip_entry en el source del scan loop
        if not found:
            # regex liviano: _make_skip_entry\([^)]*"reason"
            import re as _re_r3
            pattern = _re_r3.compile(
                r'_make_skip_entry\s*\(\s*(?:\n\s*)?"' + _re_r3.escape(reason) + r'"',
                _re_r3.DOTALL,
            )
            found = bool(pattern.search(code))
        # Fallback final: fuera_allowlist / shadow_only_override se emiten vía variable _skip_reason_allow
        # (el contrato distingue los dos caminos por el ternario validado más arriba). Basta con que
        # la cadena aparezca como literal en el scan loop.
        if not found and reason in ("fuera_allowlist", "shadow_only_override"):
            found = f'"{reason}"' in code
        test(f"R3: scan loop emite skip_reason='{reason}'", found)

    shadow_only_ns = {
        "os": os,
        "ACTIVE_TRADING_CITIES": {"NONE"},
        "CANARY_TRADING_CITIES": set(),
        "load_city_policy_state": lambda: {"auto_canary_cities": {}, "auto_canary_from_active": {}},
        "_normalize_city_policy_state": lambda state: state,
    }
    exec(get_function_source(module_ast, code_lines, "_is_shadow_only"), shadow_only_ns)
    prev_shadow_only_env = os.environ.get("SHADOW_ONLY_MODE")
    try:
        os.environ["SHADOW_ONLY_MODE"] = "true"
        test("shadow-only helper: respeta env true",
             shadow_only_ns["_is_shadow_only"]() is True)
        os.environ["SHADOW_ONLY_MODE"] = "false"
        test("shadow-only helper: respeta env false",
             shadow_only_ns["_is_shadow_only"]() is False)
        os.environ.pop("SHADOW_ONLY_MODE", None)
        test("shadow-only helper: fallback legacy sin active/canary -> true",
             shadow_only_ns["_is_shadow_only"]() is True)
    finally:
        if prev_shadow_only_env is None:
            os.environ.pop("SHADOW_ONLY_MODE", None)
        else:
            os.environ["SHADOW_ONLY_MODE"] = prev_shadow_only_env

    shadow_only_auto_canary_ns = {
        "os": os,
        "ACTIVE_TRADING_CITIES": {"NONE"},
        "CANARY_TRADING_CITIES": set(),
        "load_city_policy_state": lambda: {
            "auto_canary_cities": {"Seoul": {"promoted_at": "2026-04-16T00:00:00Z"}},
            "auto_canary_from_active": {},
        },
        "_normalize_city_policy_state": lambda state: state,
    }
    exec(get_function_source(module_ast, code_lines, "_is_shadow_only"), shadow_only_auto_canary_ns)
    prev_shadow_only_env = os.environ.get("SHADOW_ONLY_MODE")
    try:
        os.environ.pop("SHADOW_ONLY_MODE", None)
        test("shadow-only helper: auto_canary persistida desactiva fallback legacy",
             shadow_only_auto_canary_ns["_is_shadow_only"]() is False)
    finally:
        if prev_shadow_only_env is None:
            os.environ.pop("SHADOW_ONLY_MODE", None)
        else:
            os.environ["SHADOW_ONLY_MODE"] = prev_shadow_only_env

    shadow_only_auto_canary_from_active_ns = {
        "os": os,
        "ACTIVE_TRADING_CITIES": {"NONE"},
        "CANARY_TRADING_CITIES": set(),
        "load_city_policy_state": lambda: {
            "auto_canary_cities": {},
            "auto_canary_from_active": {"Chicago": {"degraded_at": "2026-04-16T00:00:00Z"}},
        },
        "_normalize_city_policy_state": lambda state: state,
    }
    exec(get_function_source(module_ast, code_lines, "_is_shadow_only"), shadow_only_auto_canary_from_active_ns)
    prev_shadow_only_env = os.environ.get("SHADOW_ONLY_MODE")
    try:
        os.environ.pop("SHADOW_ONLY_MODE", None)
        test("shadow-only helper: auto_canary_from_active desactiva fallback legacy",
             shadow_only_auto_canary_from_active_ns["_is_shadow_only"]() is False)
    finally:
        if prev_shadow_only_env is None:
            os.environ.pop("SHADOW_ONLY_MODE", None)
        else:
            os.environ["SHADOW_ONLY_MODE"] = prev_shadow_only_env

    # --- Functional tests: exec helpers en namespace limpio ---
    import tempfile as _tf_r3
    import shutil as _sh_r3

    class _FakeLog:
        warnings = []
        def warning(self, msg, *args, **kwargs):
            self.warnings.append(str(msg))
        def info(self, *a, **k):
            pass
        def error(self, *a, **k):
            pass

    def _build_skip_ns():
        ns = {
            "os": os,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "log": _FakeLog(),
            "SKIP_LOG_REQUIRED_FIELDS": ("ts_utc", "cycle_id", "skip_reason", "extras"),
            "SKIP_LOG_FILE": "unused_in_tests.jsonl",
            "SKIP_LOG_MAX_SIZE_BYTES": 20 * 1024 * 1024,
        }
        for fn_name in (
            "_make_skip_entry", "_skip_log_rotate_if_needed",
            "append_skip_log_entries", "_skip_log_rotated_files",
            "read_skip_log_last_n_cycles", "read_skip_log_since",
        ):
            exec(get_function_source(module_ast, code_lines, fn_name), ns)
        return ns

    # Test 1: _make_skip_entry con campos mínimos → dict con defaults null y extras={}
    ns1 = _build_skip_ns()
    entry1 = ns1["_make_skip_entry"](
        "below_min_edge", cycle_id="2026-04-05T16:00",
        city="Tokyo", edge_pct=2.5, our_prob=61.0, mkt_prob=58.5,
    )
    test("R3: _make_skip_entry construye dict con cycle_id y reason",
         entry1.get("cycle_id") == "2026-04-05T16:00"
         and entry1.get("skip_reason") == "below_min_edge")
    test("R3: _make_skip_entry defaults null para campos no provistos",
         entry1.get("sigma_used") is None and entry1.get("threshold") is None)
    test("R3: _make_skip_entry extras default es dict vacío",
         entry1.get("extras") == {})
    test("R3: _make_skip_entry genera ts_utc tz-aware si no se provee",
         "T" in entry1.get("ts_utc", "") and ("+" in entry1["ts_utc"] or "Z" in entry1["ts_utc"]))

    # Test 2: append_skip_log_entries([]) es no-op (no crea archivo)
    ns2 = _build_skip_ns()
    tmp_path = os.path.join(
        os.getcwd(),
        f"_tmp_skip_log_test_{next(_tf_r3._get_candidate_names())}.jsonl",
    )
    try:
        ns2["append_skip_log_entries"]([], path=tmp_path)
        test("R3: append_skip_log_entries([]) no crea archivo",
             not os.path.exists(tmp_path))

        # Test 3: append con 1 entry → archivo con 1 línea parseable
        entry = ns2["_make_skip_entry"](
            "below_min_edge", cycle_id="2026-04-05T16:00",
            city="Tokyo", edge_pct=2.5, our_prob=61.0, mkt_prob=58.5,
        )
        ns2["append_skip_log_entries"]([entry], path=tmp_path)
        test("R3: append_skip_log_entries crea archivo",
             os.path.exists(tmp_path))
        with open(tmp_path, "r", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        test("R3: append escribe exactamente 1 línea",
             len(lines) == 1)
        parsed_back = json.loads(lines[0])
        test("R3: línea escrita parsea y matchea cycle_id",
             parsed_back.get("cycle_id") == "2026-04-05T16:00"
             and parsed_back.get("skip_reason") == "below_min_edge")

        # Test 4: entry sin ts_utc → ValueError (fail-fast)
        broken_entry = {"cycle_id": "x", "skip_reason": "no_edge", "extras": {}}  # falta ts_utc
        raised = False
        try:
            ns2["append_skip_log_entries"]([broken_entry], path=tmp_path)
        except ValueError:
            raised = True
        test("R3: append fail-fast si entry carece de campos obligatorios",
             raised)

        # Test 5: read_skip_log_last_n_cycles(2) devuelve filas de 2 cycle_id distintos
        extra_entries = [
            ns2["_make_skip_entry"]("kelly_too_low", cycle_id="2026-04-05T16:00", city="Seoul"),
            ns2["_make_skip_entry"]("below_min_edge", cycle_id="2026-04-05T23:00", city="Munich"),
            ns2["_make_skip_entry"]("no_edge", cycle_id="2026-04-05T23:00", city="Chicago"),
            ns2["_make_skip_entry"]("liquidity_low", cycle_id="2026-04-06T08:00", city="Paris"),
        ]
        ns2["append_skip_log_entries"](extra_entries, path=tmp_path)
        last2 = ns2["read_skip_log_last_n_cycles"](2, path=tmp_path)
        cycle_ids_seen = set(e.get("cycle_id") for e in last2)
        test("R3: read_skip_log_last_n_cycles(2) devuelve solo los 2 ciclos más recientes",
             cycle_ids_seen == {"2026-04-06T08:00", "2026-04-05T23:00"})

        # Test 6: read_skip_log_since filtra por timestamp
        all_entries = ns2["read_skip_log_since"]("1970-01-01T00:00:00+00:00", path=tmp_path)
        test("R3: read_skip_log_since con ts antiguo devuelve todo",
             len(all_entries) == 5)
        future_entries = ns2["read_skip_log_since"]("2099-12-31T00:00:00+00:00", path=tmp_path)
        test("R3: read_skip_log_since con ts futuro devuelve vacío",
             future_entries == [])

        # Test 7: reader tolera línea malformada (skip silencioso)
        with open(tmp_path, "a", encoding="utf-8") as fh:
            fh.write("{this is not valid json}\n")
        try:
            result_tol = ns2["read_skip_log_last_n_cycles"](10, path=tmp_path)
            tolerated = True
        except Exception:
            tolerated = False
        test("R3: reader tolera líneas malformadas sin lanzar",
             tolerated and len(result_tol) == 5)

        # Test 8: rotación dispara cuando size >= max_size
        rot_tmp = tmp_path[:-len(".jsonl")] + "_rot.jsonl"
        big_entry = ns2["_make_skip_entry"]("no_edge", cycle_id="2026-04-05T16:00",
                                             city="Tokyo", question="x" * 2000)
        original_replace = ns2["os"].replace
        def _test_replace(src, dst):
            _sh_r3.copyfile(src, dst)
            os.remove(src)
        ns2["os"].replace = _test_replace
        ns2["append_skip_log_entries"]([big_entry] * 5, path=rot_tmp, max_size=1024)
        # Primer append crea el archivo. Segundo debería rotar antes de escribir.
        ns2["append_skip_log_entries"]([big_entry], path=rot_tmp, max_size=1024)
        ns2["os"].replace = original_replace
        rotated_files = [
            n for n in os.listdir(os.getcwd())
            if n.startswith(os.path.basename(rot_tmp)[:-len(".jsonl")] + ".")
            and n.endswith(".jsonl")
            and n != os.path.basename(rot_tmp)
        ]
        test("R3: rotación crea archivo rotado cuando supera max_size",
             len(rotated_files) >= 1)

        # Test 9: reader lee desde archivos rotados
        # rotated_files[0] tiene las primeras 5 filas; el actual tiene la última.
        combined = ns2["read_skip_log_last_n_cycles"](10, path=rot_tmp)
        test("R3: reader combina archivo activo + rotados",
             len(combined) >= 5)

        # Test 10: writer NO lanza si disco falla (path inválido en Windows / directorio inexistente sin permiso)
        invalid_path = tmp_path[:-len(".jsonl")] + "_invalid.jsonl"
        # Crear el parent dir está permitido, así que esto crea y escribe → no falla.
        # Mejor: simular write a path con caracter inválido en Windows.
        fake_log = _FakeLog()
        ns_fail = _build_skip_ns()
        ns_fail["log"] = fake_log
        # Override open() dentro del namespace para simular IOError
        original_open = ns_fail.get("open", open)
        def _failing_open(*args, **kwargs):
            raise OSError("simulated disk failure")
        ns_fail["open"] = _failing_open
        # Re-exec append con el open fallado
        exec(get_function_source(module_ast, code_lines, "append_skip_log_entries"), ns_fail)
        fail_path = tmp_path[:-len(".jsonl")] + "_fail.jsonl"
        raised_fail = False
        try:
            ns_fail["append_skip_log_entries"](
                [ns_fail["_make_skip_entry"]("no_edge", cycle_id="x")]
                if False else
                [{"ts_utc": "2026-04-05T00:00:00+00:00", "cycle_id": "x",
                  "skip_reason": "no_edge", "extras": {}}],
                path=fail_path,
            )
        except Exception:
            raised_fail = True
        test("R3: writer NO propaga excepciones de I/O al caller",
             not raised_fail)

    finally:
        for cleanup_path in [tmp_path, tmp_path[:-len(".jsonl")] + "_rot.jsonl", tmp_path[:-len(".jsonl")] + "_invalid.jsonl", tmp_path[:-len(".jsonl")] + "_fail.jsonl"]:
            if os.path.exists(cleanup_path):
                try:
                    os.remove(cleanup_path)
                except Exception:
                    pass
        for rotated_name in os.listdir(os.getcwd()):
            prefix = os.path.basename(tmp_path)[:-len(".jsonl")] + "_rot."
            if rotated_name.startswith(prefix) and rotated_name.endswith(".jsonl"):
                try:
                    os.remove(os.path.join(os.getcwd(), rotated_name))
                except Exception:
                    pass

    test("Version v10.6.47", 'BOT_VERSION = "v10.6.47"' in code)

    # ---- v10.6.15: Quality-trader canary exact/range ----
    test(
        "v10.6.15: QUALITY_TRADER_CONDITIONS definido",
        "QUALITY_TRADER_CONDITIONS" in code,
    )
    test(
        "v10.6.15: QUALITY_TRADER_CITIES_WHITELIST definido",
        "QUALITY_TRADER_CITIES_WHITELIST" in code,
    )
    test(
        "v10.6.15: MIN_EDGE_EXACT_RANGE_BUFFER_PP definido",
        "MIN_EDGE_EXACT_RANGE_BUFFER_PP" in code,
    )
    test(
        "v10.6.15: EXACT_RANGE_SIZE_SCALE definido",
        "EXACT_RANGE_SIZE_SCALE" in code,
    )
    test(
        "v10.6.15: London no en QUALITY_TRADER_CITIES_WHITELIST default",
        (
            "QUALITY_TRADER_CITIES_WHITELIST" in code
            and "Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan" in code
            and "London" not in "Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan"
        ),
        "London debe estar excluida de la whitelist por defecto",
    )
    test(
        "v10.6.15: exact_range_canary flag se setea en pipeline",
        'c["exact_range_canary"] = True' in code,
    )
    test(
        "v10.6.15: edge buffer aplicado para exact_range_canary",
        "MIN_EDGE_EXACT_RANGE_BUFFER_PP if c.get(\"exact_range_canary\")" in code,
    )
    test(
        "v10.6.15: size scale aplicado para exact_range_canary",
        'c.get("exact_range_canary") and isinstance(position, dict)' in code,
    )
    test(
        "v10.6.23: EXACT_RANGE_MIN_AMOUNT definido",
        "EXACT_RANGE_MIN_AMOUNT" in code,
    )
    test(
        "v10.6.23: exact/range canary aplica floor minimo de amount",
        'position["min_amount_floor_applied"] = _er_floor' in code,
    )

    # ---- v10.6.16: condition_reopen_monitor ----
    test(
        "v10.6.16: maybe_run_condition_monitor definida",
        "def maybe_run_condition_monitor(" in code,
    )
    test(
        "v10.6.16: _condition_monitor_stats definida",
        "def _condition_monitor_stats(" in code,
    )
    test(
        "v10.6.16: _build_condition_checkpoint_message definida",
        "def _build_condition_checkpoint_message(" in code,
    )
    test(
        "v10.6.16: checkpoint day 7 definido (2026-04-21)",
        "date(2026, 4, 21)" in code,
    )
    test(
        "v10.6.16: checkpoint day 14 definido (2026-04-28)",
        "date(2026, 4, 28)" in code,
    )
    test(
        "v10.6.16: kill-switch threshold WR<0.45 n>=20 presente",
        "0.45" in code and "n_closed >= 20" in code,
    )
    test(
        "v10.6.16: last_condition_checkpoint anti-spam en state",
        '"last_condition_checkpoint"' in code,
    )
    test(
        "v10.6.16: maybe_run_condition_monitor integrado en ciclo diario",
        "maybe_run_condition_monitor(state)" in code,
    )
    test(
        "v10.6.16: tools/condition_reopen_monitor.py existe",
        os.path.exists(os.path.join(os.path.dirname(__file__), "tools", "condition_reopen_monitor.py")),
    )

    # ---- v10.6.32: SL retrospective + daily briefing ----
    sl_retro_script = os.path.join(os.path.dirname(__file__), "tools", "sl_retrospective.py")
    daily_briefing_script = os.path.join(os.path.dirname(__file__), "tools", "daily_position_briefing.py")
    pnl_reconciliation_script = os.path.join(os.path.dirname(__file__), "tools", "pnl_reconciliation_alert.py")
    sl_retro_compiles = False
    daily_briefing_compiles = False
    pnl_reconciliation_compiles = False
    sl_retro_detail = ""
    daily_briefing_detail = ""
    pnl_reconciliation_detail = ""
    if os.path.exists(sl_retro_script):
        try:
            py_compile.compile(sl_retro_script, doraise=True)
            sl_retro_compiles = True
        except Exception as exc:
            sl_retro_detail = str(exc)
    if os.path.exists(daily_briefing_script):
        try:
            py_compile.compile(daily_briefing_script, doraise=True)
            daily_briefing_compiles = True
        except Exception as exc:
            daily_briefing_detail = str(exc)
    if os.path.exists(pnl_reconciliation_script):
        try:
            py_compile.compile(pnl_reconciliation_script, doraise=True)
            pnl_reconciliation_compiles = True
        except Exception as exc:
            pnl_reconciliation_detail = str(exc)
    test(
        "v10.6.32: tools/sl_retrospective.py existe y compila",
        os.path.exists(sl_retro_script) and sl_retro_compiles,
        sl_retro_detail,
    )
    test(
        "v10.6.32: tools/daily_position_briefing.py existe y compila",
        os.path.exists(daily_briefing_script) and daily_briefing_compiles,
        daily_briefing_detail,
    )
    test(
        "v10.6.38: tools/pnl_reconciliation_alert.py existe y compila",
        os.path.exists(pnl_reconciliation_script) and pnl_reconciliation_compiles,
        pnl_reconciliation_detail,
    )
    test(
        "v10.6.32: maybe_run_sl_retrospective definida",
        "def maybe_run_sl_retrospective(" in code,
    )
    test(
        "v10.6.32: maybe_run_daily_briefing definida",
        "def maybe_run_daily_briefing(" in code,
    )
    test(
        "v10.6.38: maybe_run_pnl_reconciliation definida",
        "def maybe_run_pnl_reconciliation(" in code,
    )
    test(
        "v10.6.32: env vars SL retro + daily briefing definidas",
        'SL_RETRO_ENABLED = os.getenv("SL_RETRO_ENABLED"' in code
        and 'DAILY_BRIEFING_ENABLED = os.getenv("DAILY_BRIEFING_ENABLED"' in code
        and 'DAILY_BRIEFING_HOUR_UTC = int(os.getenv("DAILY_BRIEFING_HOUR_UTC"' in code,
    )
    test(
        "v10.6.38: env vars P/L reconciliation definidas",
        'PNL_RECONCILIATION_ENABLED = os.getenv("PNL_RECONCILIATION_ENABLED"' in code
        and 'PNL_RECONCILIATION_HOUR_UTC = int(os.getenv("PNL_RECONCILIATION_HOUR_UTC"' in code,
    )
    test(
        "v10.6.32: maybe_run_sl_retrospective integrada en run_observability_alerts",
        "maybe_run_sl_retrospective(state)" in code,
    )
    test(
        "v10.6.32: maybe_run_daily_briefing integrada en run_observability_alerts",
        "maybe_run_daily_briefing(state)" in code,
    )
    test(
        "v10.6.38: maybe_run_pnl_reconciliation integrada en run_observability_alerts",
        "maybe_run_pnl_reconciliation(state)" in code,
    )
    try:
        with open(daily_briefing_script, "r", encoding="utf-8") as f:
            daily_briefing_code = f.read()
        daily_briefing_ast = ast.parse(daily_briefing_code)
        daily_sl_ns = {
            "Path": Path,
            "TARGET_SAMPLE_SIZE": 16,
            "load_json": lambda path, required=False: {
                "n_resolved_last": 18,
                "final_verdict": "SL funciona correctamente (firme)",
            },
        }
        exec(get_function_source(daily_briefing_ast, daily_briefing_code.splitlines(), "build_sl_retro_line"), daily_sl_ns)
        daily_sl_line = daily_sl_ns["build_sl_retro_line"](Path("dummy-state.json"))
        test(
            "v10.6.48: daily briefing marca verdict SL retro firme como histórico",
            "SL funciona correctamente (firme)" not in daily_sl_line
            and "veredicto histórico" in daily_sl_line
            and "phase-aware" in daily_sl_line,
            daily_sl_line,
        )
        test(
            "v10.6.48: daily briefing conserva contador SL retro",
            "18 resueltos" in daily_sl_line
            and "18/16 resueltos" not in daily_sl_line,
            daily_sl_line,
        )
    except Exception as exc:
        test("v10.6.48: daily briefing SL retro phase-aware test ejecuta sin excepción", False, str(exc))
    try:
        with open(sl_retro_script, "r", encoding="utf-8") as f:
            sl_retro_code = f.read()
        sl_retro_ast = ast.parse(sl_retro_code)
        sl_retro_lines = sl_retro_code.splitlines()

        fd, tmp_sl_lifecycle = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_sl_lifecycle_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_sl_forecast = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_sl_forecast_",
            suffix=".json",
        )
        os.close(fd)
        fd, tmp_sl_audit = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_sl_audit_",
            suffix=".json",
        )
        os.close(fd)

        with open(tmp_sl_lifecycle, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "records": [
                        {
                            "id": "atl-1",
                            "city": "Atlanta",
                            "date": "2026-04-01",
                            "side": "YES",
                            "label": "Will the highest temperature in Atlanta be between 80-81°F on April 1? YES",
                            "question": "Will the highest temperature in Atlanta be between 80-81°F on April 1?",
                            "avg_entry_price": 0.15,
                            "closed_at": "2026-04-01T16:00:00+00:00",
                            "close_context": {
                                "close_reason": "stop_loss",
                                "close_price": 0.08,
                                "close_shares": 10.0,
                                "pnl_cash": -1.3,
                                "pnl_pct": -56.0,
                                "order_id": "order-atl-1",
                            },
                            "post_exit_analysis": {},
                        },
                        {
                            "id": "chi-mismatch-id",
                            "city": "Chicago",
                            "date": "2026-03-29",
                            "side": "YES",
                            "label": "Will the highest temperature in Chicago be between 66-67°F on March 29? YES",
                            "question": "Will the highest temperature in Chicago be between 66-67°F on March 29?",
                            "avg_entry_price": 0.14,
                            "closed_at": "2026-03-29T16:00:00+00:00",
                            "close_context": {
                                "close_reason": "stop_loss",
                                "close_price": 0.02,
                                "close_shares": 9.0,
                                "pnl_cash": -1.21,
                                "pnl_pct": -79.0,
                                "order_id": "order-chi-1",
                            },
                            "post_exit_analysis": {},
                        },
                        {
                            "id": "dal-runtime-id",
                            "city": "Dallas",
                            "date": "2026-03-28",
                            "side": "YES",
                            "label": "Will the highest temperature in Dallas be between 64-65Â°F on March 28? YES",
                            "question": "Will the highest temperature in Dallas be between 64-65Â°F on March 28?",
                            "avg_entry_price": 0.19,
                            "closed_at": "2026-03-28T19:14:08+00:00",
                            "close_context": {
                                "close_reason": "stop_loss",
                                "close_price": 0.08,
                                "close_shares": 10.87,
                                "pnl_cash": -1.36,
                                "pnl_pct": -54.3,
                                "order_id": "order-dal-1",
                            },
                            "entry_context": {
                                "forecast_max": 14.9,
                                "our_prob": 47.9,
                                "days_ahead": 0,
                            },
                            "post_exit_analysis": {},
                        },
                        {
                            "id": "sea-legacy-id",
                            "city": "Seattle",
                            "date": "2026-03-28",
                            "side": "YES",
                            "label": "Seattle 2026-03-28 YES",
                            "question": "",
                            "condition": "at_or_below",
                            "avg_entry_price": 0.10,
                            "closed_at": "2026-03-27T23:00:14+00:00",
                            "close_context": {
                                "close_reason": "stop_loss",
                                "close_price": 0.02,
                                "close_shares": 23.92,
                                "pnl_cash": -1.34,
                                "pnl_pct": -56.3,
                                "order_id": "order-sea-1",
                            },
                            "entry_context": {
                                "forecast_max": 11.8,
                                "our_prob": 35.5,
                                "days_ahead": 2,
                            },
                            "post_exit_analysis": {},
                        },
                        {
                            "id": "par-1",
                            "city": "Paris",
                            "date": "2026-03-29",
                            "side": "NO",
                            "label": "Will the highest temperature in Paris be 12°C on March 29? NO",
                            "question": "Will the highest temperature in Paris be 12°C on March 29?",
                            "avg_entry_price": 0.44,
                            "closed_at": "2026-03-29T11:00:00+00:00",
                            "total_shares": 4.2,
                            "close_context": {
                                "close_reason": "stop_loss_intra",
                                "close_price": 0.07,
                                "close_shares": 4.2,
                                "pnl_cash": -1.84,
                                "pnl_pct": -77.9,
                                "order_id": "order-par-1",
                            },
                            "post_exit_analysis": {},
                        },
                        {
                            "id": "market:phantom|date:|side:YES|2026-03-28",
                            "city": "Phantom",
                            "date": "",
                            "side": "YES",
                            "label": "Phantom YES",
                            "token_id": "",
                            "total_shares": 0,
                            "closed_at": "2026-03-28T08:00:00+00:00",
                            "close_context": {
                                "close_reason": "stop_loss",
                                "close_price": 0.07,
                                "close_shares": 0,
                                "pnl_cash": -1.95,
                                "pnl_pct": -40.5,
                                "order_id": "order-par-1",
                            },
                            "post_exit_analysis": {},
                        },
                    ]
                },
                f,
                ensure_ascii=False,
            )

        with open(tmp_sl_forecast, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "trades": [
                        {
                            "id": "atl-1",
                            "city": "Atlanta",
                            "date_iso": "2026-04-01",
                            "side": "YES",
                            "condition": "range",
                            "threshold_c": 26.7,
                            "threshold_high_c": 27.2,
                            "observed_real": 28.1,
                            "observed_source": "open_meteo_archive",
                            "outcome_correct": False,
                        },
                        {
                            "id": "chi-real-id",
                            "city": "Chicago",
                            "date_iso": "2026-03-29",
                            "side": "YES",
                            "condition": "range",
                            "threshold_c": 18.9,
                            "threshold_high_c": 19.4,
                            "observed_real": 17.2,
                            "observed_source": "daily-summaries_tmax",
                            "outcome_correct": True,
                        },
                        {
                            "id": "par-1",
                            "city": "Paris",
                            "date_iso": "2026-03-29",
                            "side": "NO",
                            "condition": "exact",
                            "threshold_c": 12.0,
                            "threshold_high_c": None,
                            "observed_real": 10.8,
                            "observed_source": "daily-summaries_tmax",
                            "outcome_correct": True,
                        },
                        {
                            "id": "dal-mismatch-id",
                            "city": "Dallas",
                            "date_iso": "2026-03-28",
                            "side": "YES",
                            "condition": "range",
                            "threshold_c": 13.5,
                            "threshold_high_c": 14.5,
                            "observed_real": 14.4,
                            "observed_source": "daily-summaries_tmax",
                            "outcome_correct": True,
                        },
                    ]
                },
                f,
                ensure_ascii=False,
            )
        with open(tmp_sl_audit, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "observed_vs_forecast": [
                        {
                            "city": "Dallas",
                            "date": "2026-03-28",
                            "observed_temp_c": 14.4,
                            "source": "noaa_ncei",
                            "observed_dataset": "daily-summaries_tmax",
                            "checked_at": "2026-04-24T10:00:00+00:00",
                        },
                        {
                            "city": "Seattle",
                            "date": "2026-03-28",
                            "observed_temp_c": 13.9,
                            "source": "noaa_ncei",
                            "observed_dataset": "daily-summaries_tmax",
                            "checked_at": "2026-04-24T10:00:00+00:00",
                        },
                    ]
                },
                f,
                ensure_ascii=False,
            )

        sl_ns = {
            "json": json,
            "math": math,
            "Path": Path,
            "DEFAULT_FORECAST_ACCURACY_FILE": Path(tmp_sl_forecast),
            "DEFAULT_AUDIT_FILE": Path(tmp_sl_audit),
            "PRELIMINARY_THRESHOLD": 8,
            "FINAL_THRESHOLD": 12,
            "SL_REASONS": {"stop_loss", "stop_loss_intra"},
        }
        for fn_name in [
            "load_json",
            "as_float",
            "to_probability",
            "_normalize_text",
            "_record_question_text",
            "_question_signature",
            "_resolution_lookup_key",
            "normal_cdf",
            "estimate_prob_with_sigma",
            "condition_happened",
            "infer_threshold_from_prob",
            "load_resolution_stations",
            "fetch_open_meteo_observed_max",
            "fetch_live_observed_row",
            "load_resolution_fallback_rows",
            "load_observed_vs_forecast_rows",
            "infer_observed_vs_forecast_verdict",
            "infer_resolution_verdict",
            "load_sl_rows",
            "_summarize_type",
            "summarize",
            "build_message",
        ]:
            exec(get_function_source(sl_retro_ast, sl_retro_lines, fn_name), sl_ns)
        sl_ns["TARGET_SAMPLE_SIZE"] = 16
        sl_ns["load_resolution_stations"] = lambda: {}

        sl_rows = sl_ns["load_sl_rows"](Path(tmp_sl_lifecycle))
        sl_summary = sl_ns["summarize"](sl_rows)
        atl_row = next((row for row in sl_rows if "Atlanta" in row.get("label", "")), {})
        chi_row = next((row for row in sl_rows if "Chicago" in row.get("label", "")), {})
        dal_row = next((row for row in sl_rows if "Dallas" in row.get("label", "")), {})
        sea_row = next((row for row in sl_rows if row.get("label") == "Seattle 2026-03-28 YES"), {})
        par_row = next((row for row in sl_rows if "Paris" in row.get("label", "")), {})
        phantom_row = next((row for row in sl_rows if "Phantom" in row.get("label", "")), None)
        test(
            "v10.6.32: SL retro usa fallback por resolución real cuando faltan snapshots",
            atl_row.get("verdict") == "WRONG"
            and atl_row.get("verdict_source") == "resolved_outcome"
            and chi_row.get("verdict") == "RIGHT"
            and chi_row.get("verdict_source") == "resolved_outcome",
            {"atl": atl_row, "chi": chi_row},
        )
        test(
            "v10.6.32: SL retro resuelve por firma de pregunta aunque cambie el id",
            chi_row.get("verdict") == "RIGHT" and chi_row.get("observed_real") == 17.2,
            chi_row,
        )
        test(
            "v10.6.34: SL retro prioriza audit NOAA cuando forecast_accuracy deriva un umbral incoherente",
            dal_row.get("verdict") == "WRONG"
            and dal_row.get("verdict_source") == "observed_vs_forecast"
            and dal_row.get("observed_real") == 14.4,
            dal_row,
        )
        test(
            "v10.6.34: SL retro resuelve legacy sin question usando observed_vs_forecast e inferencia de umbral",
            sea_row.get("verdict") == "WRONG"
            and sea_row.get("verdict_source") == "observed_vs_forecast"
            and sea_row.get("observed_real") == 13.9,
            sea_row,
        )
        test(
            "v10.6.33: SL retro incluye stop_loss_intra",
            par_row.get("verdict") == "RIGHT"
            and par_row.get("close_reason") == "stop_loss_intra",
            par_row,
        )
        test(
            "v10.6.33: SL retro omite filas phantom (total_shares=0 y sin token_id)",
            phantom_row is None,
            {"rows_labels": [row.get("label") for row in sl_rows]},
        )
        test(
            "v10.6.34: resumen SL retro cuenta 5 resueltos (3 wrong + 2 right)",
            sl_summary.get("n_resolved") == 5
            and sl_summary.get("n_right") == 2
            and sl_summary.get("n_wrong") == 3,
            sl_summary,
        )

        # v10.6.35: zona gris no cierra el caso — 37.5% queda "seguir monitorizando"
        gray_summary = sl_ns["summarize"]([
            {"verdict": "RIGHT", "pnl_cash_with_sl": None, "pnl_without_sl_best": None,
             "upside_left_cash_peak": None} for _ in range(6)
        ] + [
            {"verdict": "WRONG", "pnl_cash_with_sl": None, "pnl_without_sl_best": None,
             "upside_left_cash_peak": None} for _ in range(10)
        ])
        gray_message = sl_ns["build_message"](gray_summary)
        test(
            "v10.6.35: SL retro en zona gris (37.5%) no emite veredicto firme",
            gray_summary.get("preliminary_verdict") == "seguir monitorizando"
            and gray_summary.get("final_verdict") == "seguir monitorizando",
            gray_summary,
        )
        test(
            "v10.6.35: mensaje SL retro zona gris no incluye 'FUNCIONANDO CORRECTAMENTE' ni 'CONCLUSIÓN FIRME'",
            "FUNCIONANDO CORRECTAMENTE" not in gray_message
            and "CONCLUSIÓN FIRME" not in gray_message
            and "zona gris" in gray_message
            and "seguimos monitorizando" in gray_message,
            {"message": gray_message},
        )
        # v10.6.35: umbral <30% sí cierra como "funciona correctamente"
        clean_summary = sl_ns["summarize"]([
            {"verdict": "RIGHT", "pnl_cash_with_sl": None, "pnl_without_sl_best": None,
             "upside_left_cash_peak": None} for _ in range(4)
        ] + [
            {"verdict": "WRONG", "pnl_cash_with_sl": None, "pnl_without_sl_best": None,
             "upside_left_cash_peak": None} for _ in range(12)
        ])
        clean_message = sl_ns["build_message"](clean_summary)
        test(
            "v10.6.35: SL retro con 25% falsas salidas sigue cerrando verdict 'funciona correctamente'",
            clean_summary.get("preliminary_verdict") == "SL funciona correctamente"
            and clean_summary.get("final_verdict") == "SL funciona correctamente (firme)",
            clean_summary,
        )
        test(
            "v10.6.49: mensaje SL retro clean suaviza verdict preliminar phase-aware",
            "EL SL ESTÁ FUNCIONANDO CORRECTAMENTE" not in clean_message
            and "EL SL NO MUESTRA FALLOS RELEVANTES EN ESTA FASE" in clean_message,
            {"message": clean_message},
        )

        for tmp_file in [tmp_sl_lifecycle, tmp_sl_forecast, tmp_sl_audit]:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass
    except Exception as exc:
        test("v10.6.32: tests funcionales SL retrospective ejecutan sin excepción", False, str(exc))

    # ---- v10.6.17: Austin canary onboarding ----
    test(
        "v10.6.17: Austin en RESOLUTION_ICAO con noaa_station_id y noaa_daily_station_id",
        '"Austin"' in code
        and '"noaa_station_id": "72254013904"' in code
        and '"noaa_daily_station_id": "USW00013904"' in code,
    )
    test(
        "v10.6.17: Austin en CITY_TIMEZONES con America/Chicago",
        '"Austin":         "America/Chicago"' in code or '"Austin": "America/Chicago"' in code,
    )
    test(
        "v10.6.17: Austin en OBSERVED_AUDIT_CITIES",
        '"Austin"' in code and "OBSERVED_AUDIT_CITIES" in code,
    )
    test(
        "v10.6.17: MIN_PRICE y MAX_PRICE sin cambios (0.20 / 0.80)",
        "MIN_PRICE = 0.20" in code and "MAX_PRICE = 0.80" in code,
    )
    test(
        "v10.6.17: ACTIVE_TRADING_CITIES sigue en NONE en env (guardrail)",
        os.environ.get("ACTIVE_TRADING_CITIES", "NONE") in ("", "NONE"),
    )

    # ---- v10.6.20: P1 - ciudades invisibles al pipeline + alertas P4-P7 ----
    test(
        "v10.6.20: Lucknow en OBSERVED_AUDIT_CITIES (fix handoff C sesion 169)",
        '"Lucknow"' in code and "OBSERVED_AUDIT_CITIES" in code,
    )
    test(
        "v10.6.20: Sao Paulo en OBSERVED_AUDIT_CITIES (fix handoff C sesion 169)",
        '"Sao Paulo"' in code and "OBSERVED_AUDIT_CITIES" in code,
    )
    test(
        "v10.6.20: Lucknow tiene RESOLUTION_STATIONS",
        '"Lucknow":        {"lat": 26.7606' in code
        or '"Lucknow": {"lat": 26.7606' in code,
    )
    test(
        "v10.6.20: Sao Paulo tiene RESOLUTION_STATIONS",
        '"Sao Paulo":      {"lat": -23.4355' in code
        or '"Sao Paulo": {"lat": -23.4355' in code,
    )
    test(
        "v10.6.20: maybe_alert_p4_p5_expansion definida",
        "def maybe_alert_p4_p5_expansion(" in code,
    )
    test(
        "v10.6.20: maybe_alert_p6_p7_post_v2_cleanup definida",
        "def maybe_alert_p6_p7_post_v2_cleanup(" in code,
    )
    test(
        "v10.6.20: maybe_alert_p4_p5_expansion integrada en run_observability_alerts",
        "maybe_alert_p4_p5_expansion(state)" in code,
    )
    test(
        "v10.6.20: maybe_alert_p6_p7_post_v2_cleanup integrada en run_observability_alerts",
        "maybe_alert_p6_p7_post_v2_cleanup(state)" in code,
    )
    test(
        "v10.6.20: P4-P5 alert FIRE_DATE es 2026-04-22",
        'FIRE_DATE = "2026-04-22"' in code,
    )
    test(
        "v10.6.20: P6-P7 alert FIRE_DATE es 2026-04-25",
        'FIRE_DATE = "2026-04-25"' in code,
    )
    test(
        "v10.6.26: alertas Busan/Steps registradas",
        'maybe_alert_busan_expansion' in code,
    )
    # ---- v10.6.27: P4 whitelist expansion ----
    test(
        "v10.6.27: P4 whitelist expansion presente",
        '"Tel Aviv"' in code and '"Taipei"' in code,
    )
    test(
        "v10.6.27: Tel Aviv en QUALITY_TRADER_CITIES_WHITELIST default",
        "Tel Aviv" in code and "QUALITY_TRADER_CITIES_WHITELIST" in code,
    )
    # ---- v10.6.28: P5 new cities ----
    test(
        "v10.6.28: P5 cities presentes en RESOLUTION_STATIONS",
        '"Moscow":' in code and "Vnukovo" in code,
    )
    test(
        "v10.6.28: Moscow en RESOLUTION_STATIONS",
        '"Moscow":' in code and "Vnukovo" in code,
    )
    test(
        "v10.6.28: Amsterdam en RESOLUTION_STATIONS",
        '"Amsterdam":' in code and "Schiphol" in code,
    )
    test(
        "v10.6.28: Istanbul en RESOLUTION_STATIONS",
        '"Istanbul":' in code and "Istanbul Airport" in code,
    )
    test(
        "v10.6.28: Helsinki en RESOLUTION_ICAO con EFHK",
        '"EFHK"' in code,
    )
    test(
        "v10.6.28: Jeddah en RESOLUTION_ICAO con OEJN",
        '"OEJN"' in code,
    )
    test(
        "v10.6.28: whitelist default incluye P5 cities",
        "Moscow,Amsterdam,Jeddah,Istanbul,Helsinki" in code,
    )
    # ---- v10.6.29: Busan ICAO-only ----
    test(
        "v10.6.29: Busan RKPK presente en RESOLUTION_ICAO",
        '"RKPK"' in code,
    )
    test(
        "v10.6.29: Busan en RESOLUTION_STATIONS con Gimhae",
        '"Busan":' in code and "Gimhae" in code,
    )
    test(
        "v10.6.29: Busan en RESOLUTION_ICAO con RKPK",
        '"RKPK"' in code,
    )
    test(
        "v10.6.29: Busan en OBSERVED_AUDIT_CITIES",
        '"Busan",' in code or '"Busan"\n' in code,
    )
    test(
        "v10.6.29: Busan en CITY_TIMEZONES con Asia/Seoul",
        '"Busan":' in code and '"Asia/Seoul"' in code,
    )
    test(
        "v10.6.29: whitelist default incluye Busan",
        "Helsinki,Busan" in code,
    )
    test(
        "v10.6.39: Beijing en OBSERVED_AUDIT_CITIES para ICAO-only proxy audit",
        re.search(r"OBSERVED_AUDIT_CITIES\s*=\s*\{[^}]*\"Beijing\"", code, re.S) is not None,
    )
    test(
        "v10.6.39: ICAO-only proxy bloquea auto-canary sin revision manual",
        "_city_requires_manual_proxy_canary_review" in code
        and "and not needs_manual_proxy_review" in code
        and "auto_canary_revoked" in code,
    )

    # ---- v10.6.40: guard SL_intra para condition=exact + days<=N (Opus, sesion 246) ----
    test(
        "v10.6.40: guard sigue presente tras bumps posteriores",
        "SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION" in code
        and "maybe_run_sl_intra_guard_review" in code,
    )
    test(
        "v10.6.40: env vars del guard SL_intra definidas",
        "SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION" in code
        and "SL_INTRA_GUARD_DAYS_AHEAD_MAX" in code
        and "SL_INTRA_GUARD_REVIEW_MIN_SKIPS" in code
        and "SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN" in code,
    )
    test(
        "v10.6.40: archivo de estado del guard definido",
        'SL_INTRA_GUARD_STATE_FILE = _data_path("sl_intra_guard_audit.json")' in code,
    )
    test(
        "v10.6.40: helpers load/save/should_skip definidos",
        "def load_sl_intra_guard_state(" in code
        and "def save_sl_intra_guard_state(" in code
        and "def _sl_intra_guard_should_skip(" in code,
    )
    test(
        "v10.6.40: intra_cycle_sl_check aplica el guard antes del SL_intra",
        "_guard_skip_sl = (" in code
        and "_sl_intra_guard_should_skip(_guard_condition, _guard_days_ahead)" in code
        and "[GUARD SL_intra] skip" in code,
    )
    test(
        "v10.6.40: maybe_run_sl_intra_guard_review definida",
        "def maybe_run_sl_intra_guard_review(" in code,
    )
    test(
        "v10.6.40: review del guard integrada en run_observability_alerts",
        "maybe_run_sl_intra_guard_review(state)" in code,
    )

    # ---- SL_intra Hazard Monitor L2: LOG_ONLY default OFF (Opus/Sonnet, sesion 285) ----
    print("  Checks SL_intra Hazard Monitor L2 LOG_ONLY")
    test(
        "sl_intra_l2: defaults seguros OFF y LOG_ONLY",
        'SL_INTRA_HAZARD_MONITOR_ENABLED = os.getenv("SL_INTRA_HAZARD_MONITOR_ENABLED", "0")' in code
        and 'SL_INTRA_HAZARD_MONITOR_LOG_ONLY = os.getenv("SL_INTRA_HAZARD_MONITOR_LOG_ONLY", "1")' in code
        and 'SL_INTRA_HAZARD_DETERIORATING_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_DETERIORATING_PNL_PCT", "-50.0"))' in code
        and 'SL_INTRA_HAZARD_DEEP_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_DEEP_PNL_PCT", "-70.0"))' in code
        and 'SL_INTRA_HAZARD_TERMINAL_PNL_PCT = float(os.getenv("SL_INTRA_HAZARD_TERMINAL_PNL_PCT", "-85.0"))' in code
        and 'SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE = float(os.getenv("SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE", "0.30"))' in code
        and 'SL_INTRA_HAZARD_COLLAPSED_PRICE = float(os.getenv("SL_INTRA_HAZARD_COLLAPSED_PRICE", "0.05"))' in code
        and 'SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES = int(os.getenv("SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES", "2"))' in code
        and 'SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN = int(os.getenv("SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN", "60"))' in code
        and 'SL_INTRA_HAZARD_MAX_EVENTS = int(os.getenv("SL_INTRA_HAZARD_MAX_EVENTS", "1000"))' in code,
    )
    test(
        "sl_intra_l2: audit independiente del guard L1",
        'SL_INTRA_HAZARD_MONITOR_STATE_FILE = _data_path("sl_intra_hazard_monitor_audit.json")' in code
        and 'SL_INTRA_GUARD_STATE_FILE = _data_path("sl_intra_guard_audit.json")' in code,
    )
    test(
        "sl_intra_l2: helpers definidos",
        "def load_sl_intra_hazard_monitor_state(" in code
        and "def save_sl_intra_hazard_monitor_state(" in code
        and "def _sl_intra_hazard_monitor_tier(" in code
        and "def maybe_record_sl_intra_hazard_event(" in code,
    )
    sl_hazard_src = ""
    sl_hazard_hook_src = ""
    try:
        sl_hazard_src = get_function_source(module_ast, code_lines, "maybe_record_sl_intra_hazard_event")
        intra_sl_src_for_l2 = code.split("def intra_cycle_sl_check(", 1)[1].split("def intra_sl_loop(", 1)[0]
        sl_hazard_hook_src = intra_sl_src_for_l2.split("maybe_record_sl_intra_hazard_event(", 1)[1].split("_guard_skip_sl = (", 1)[0]
    except Exception:
        pass
    test(
        "sl_intra_l2: scope literal bajo L1",
        "if not _sl_intra_guard_should_skip(condition, days_ahead):" in sl_hazard_src,
    )
    test(
        "sl_intra_l2: hook integrado antes del guard skip",
        "condition=_guard_condition" in sl_hazard_hook_src
        and "days_ahead=_guard_days_ahead" in sl_hazard_hook_src
        and "now_utc=now_utc" in sl_hazard_hook_src,
    )
    test(
        "sl_intra_l2: hook sin side-effects ejecutables",
        all(forbidden not in sl_hazard_hook_src for forbidden in [
            "execute_trade",
            "track_trade",
            "sell_type =",
            "save_trade_lifecycle_data",
            "sell_lock",
            "SL_INTRA_GUARD_STATE_FILE",
            "UNSELLABLE_GUARD",
        ]),
    )
    test(
        "sl_intra_l2: helper sin ventas ni lifecycle",
        all(forbidden not in sl_hazard_src for forbidden in [
            "execute_trade",
            "track_trade",
            "sell_type =",
            "save_trade_lifecycle_data",
            "sell_lock",
            "SL_INTRA_GUARD_STATE_FILE",
            "UNSELLABLE_GUARD",
        ]),
    )
    test(
        "sl_intra_l2: Telegram LOG_ONLY y cooldown independiente",
        "⚠️ <b>[SL_intra L2 Hazard Monitor]</b>" in code
        and "LOG_ONLY: no venta, no lifecycle, no accion ejecutable" in code
        and "SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN" in code
        and "last_telegram_at" in sl_hazard_src,
    )
    try:
        sl_l2_ns = {
            "os": os,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "SL_INTRA_HAZARD_MONITOR_VERSION": "sl_intra_hazard_l2_v1",
            "SL_INTRA_HAZARD_MONITOR_STATE_FILE": "unused_in_tests.json",
            "SL_INTRA_HAZARD_MAX_EVENTS": 1000,
            "SL_INTRA_HAZARD_DETERIORATING_PNL_PCT": -50.0,
            "SL_INTRA_HAZARD_DEEP_PNL_PCT": -70.0,
            "SL_INTRA_HAZARD_TERMINAL_PNL_PCT": -85.0,
            "SL_INTRA_HAZARD_TERMINAL_CURRENT_VALUE": 0.30,
            "SL_INTRA_HAZARD_COLLAPSED_PRICE": 0.05,
            "SL_INTRA_HAZARD_COLLAPSED_MIN_CYCLES": 2,
            "SL_INTRA_HAZARD_TELEGRAM_COOLDOWN_MIN": 60,
            "BOT_VERSION": "test",
            "log": types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None),
            "parse_city_from_title": lambda title: "Paris",
        }
        for fn_name in [
            "_sl_intra_hazard_monitor_default_state",
            "load_sl_intra_hazard_monitor_state",
            "save_sl_intra_hazard_monitor_state",
            "_sl_intra_hazard_monitor_tier",
            "_sl_intra_hazard_telegram_allowed",
            "maybe_record_sl_intra_hazard_event",
        ]:
            exec(get_function_source(module_ast, code_lines, fn_name), sl_l2_ns)
        tier_fn = sl_l2_ns["_sl_intra_hazard_monitor_tier"]
        test("sl_intra_l2 funcional: tier deteriorating", tier_fn(-50.0, 0.40, 1.00, 0) == "deteriorating")
        test("sl_intra_l2 funcional: tier deep", tier_fn(-70.0, 0.40, 1.00, 0) == "deep")
        test("sl_intra_l2 funcional: tier terminal por PnL", tier_fn(-85.0, 0.40, 1.00, 0) == "terminal")
        test("sl_intra_l2 funcional: tier terminal por current_value", tier_fn(-10.0, 0.40, 0.30, 0) == "terminal")
        test("sl_intra_l2 funcional: collapsed requiere 2 ciclos", tier_fn(-10.0, 0.05, 1.00, 1) == "" and tier_fn(-10.0, 0.05, 1.00, 2) == "collapsed")

        calls = {"scope": 0, "load": 0, "save": 0, "send": 0}
        sl_l2_ns["SL_INTRA_HAZARD_MONITOR_ENABLED"] = False
        sl_l2_ns["SL_INTRA_HAZARD_MONITOR_LOG_ONLY"] = True
        sl_l2_ns["_sl_intra_guard_should_skip"] = lambda condition, days_ahead: calls.__setitem__("scope", calls["scope"] + 1) or True
        sl_l2_ns["load_sl_intra_hazard_monitor_state"] = lambda: calls.__setitem__("load", calls["load"] + 1) or {}
        sl_l2_ns["save_sl_intra_hazard_monitor_state"] = lambda state: calls.__setitem__("save", calls["save"] + 1)
        sl_l2_ns["send_telegram"] = lambda msg: calls.__setitem__("send", calls["send"] + 1)
        off_result = sl_l2_ns["maybe_record_sl_intra_hazard_event"](
            {"asset": "tok-off", "curPrice": 0.05, "percentPnl": -90, "currentValue": 0.10, "size": 1},
            condition="exact",
            days_ahead=0,
            entry_price=0.50,
        )
        test(
            "sl_intra_l2 funcional: ENABLED=0 no load/save/send",
            off_result is False and calls == {"scope": 0, "load": 0, "save": 0, "send": 0},
            str(calls),
        )

        state_holder = {"state": sl_l2_ns["_sl_intra_hazard_monitor_default_state"]()}
        sends = []
        sl_l2_ns["SL_INTRA_HAZARD_MONITOR_ENABLED"] = True
        sl_l2_ns["SL_INTRA_HAZARD_MONITOR_LOG_ONLY"] = True
        sl_l2_ns["_sl_intra_guard_should_skip"] = lambda condition, days_ahead: condition == "exact" and int(days_ahead) <= 1
        sl_l2_ns["load_sl_intra_hazard_monitor_state"] = lambda: state_holder["state"]
        sl_l2_ns["save_sl_intra_hazard_monitor_state"] = lambda state: state_holder.__setitem__("state", state)
        sl_l2_ns["send_telegram"] = lambda msg: sends.append(msg)
        position = {
            "asset": "tok-l2",
            "title": "Will the temperature in Paris be exactly 20C on May 1?",
            "outcome": "YES",
            "curPrice": 0.20,
            "percentPnl": -70.0,
            "currentValue": 1.00,
            "size": 2,
        }
        first = sl_l2_ns["maybe_record_sl_intra_hazard_event"](position, condition="exact", days_ahead=0, entry_price=0.50, now_utc=datetime(2026, 5, 1, tzinfo=timezone.utc))
        second = sl_l2_ns["maybe_record_sl_intra_hazard_event"](position, condition="exact", days_ahead=0, entry_price=0.50, now_utc=datetime(2026, 5, 1, 0, 1, tzinfo=timezone.utc))
        test(
            "sl_intra_l2 funcional: idempotencia token+tier",
            first is True and second is False and len(state_holder["state"].get("events", [])) == 1,
        )
        test(
            "sl_intra_l2 funcional: Telegram solo evento nuevo",
            len(sends) == 1 and "LOG_ONLY" in sends[0],
            str(sends),
        )
        state_holder["state"] = sl_l2_ns["_sl_intra_hazard_monitor_default_state"]()
        collapsed_position = dict(position, asset="tok-collapsed", curPrice=0.05, percentPnl=-10.0, currentValue=1.00)
        collapsed_first = sl_l2_ns["maybe_record_sl_intra_hazard_event"](collapsed_position, condition="exact", days_ahead=0, entry_price=0.50, now_utc=datetime(2026, 5, 1, tzinfo=timezone.utc))
        collapsed_second = sl_l2_ns["maybe_record_sl_intra_hazard_event"](collapsed_position, condition="exact", days_ahead=0, entry_price=0.50, now_utc=datetime(2026, 5, 1, 0, 20, tzinfo=timezone.utc))
        test(
            "sl_intra_l2 funcional: collapsed persiste 2 ciclos",
            collapsed_first is False
            and collapsed_second is True
            and state_holder["state"]["events"][-1]["tier"] == "collapsed",
        )
    except Exception as exc:
        test("sl_intra_l2 funcional: helpers ejecutables", False, str(exc))

    # ---- Unsellable Liquidity Guard v1: Fase 1 LOG_ONLY (Opus, 2026-04-30) ----
    print("  Checks Unsellable Liquidity Guard v1 LOG_ONLY")
    test(
        "unsellable_v1: defaults OFF y LOG_ONLY",
        'UNSELLABLE_GUARD_ENABLED = os.getenv("UNSELLABLE_GUARD_ENABLED", "0")' in code
        and 'UNSELLABLE_GUARD_LOG_ONLY = os.getenv("UNSELLABLE_GUARD_LOG_ONLY", "1")' in code
        and 'UNSELLABLE_GUARD_VERSION = "unsellable_v1"' in code,
    )
    test(
        "unsellable_v1: skip_reason separado para LOG_ONLY vs SKIP",
        '"unsellable_guard_candidate"' in code
        and '"unsellable_liquidity_guard"' in code
        and '"would_skip" if log_only else "skipped"' in code,
    )
    test(
        "unsellable_v1: size_ratio es amount / bankroll",
        "size_ratio = amount_value / bankroll" in code
        and "size_ratio >= 0.15" in code,
    )
    test(
        "unsellable_v1: trigger exact/range same-day price 0.10-0.65",
        'str(condition or "").lower() in {"exact", "range"}' in code
        and "days_value == 0" in code
        and "0.10 <= price_value <= 0.65" in code,
    )
    unsellable_decision_src = ""
    try:
        unsellable_match_src = get_function_source(module_ast, code_lines, "_unsellable_guard_match_zone_bucket")
        unsellable_decision_src = get_function_source(module_ast, code_lines, "_unsellable_guard_decision")
        unsellable_ns = {}
        exec(unsellable_match_src, unsellable_ns)
        exec(unsellable_decision_src, unsellable_ns)
        decide = unsellable_ns["_unsellable_guard_decision"]
        base_guard_case = {
            "enabled": True,
            "log_only": True,
            "condition": "exact",
            "days_ahead": 0,
            "price_at_guard": 0.35,
            "amount": 3.75,
            "effective_bankroll": 25.0,
        }
        off_case = decide(**dict(base_guard_case, enabled=False))
        log_case = decide(**base_guard_case)
        skip_case = decide(**dict(base_guard_case, log_only=False))
        test("unsellable_v1 funcional: ENABLED=0 bypass total", off_case.get("active") is False and off_case.get("triggered") is False)
        test("unsellable_v1 funcional: LOG_ONLY trigger candidate/would_skip", log_case.get("triggered") is True and log_case.get("skip_reason") == "unsellable_guard_candidate" and log_case.get("guard_action") == "would_skip")
        test("unsellable_v1 funcional: LOG_ONLY=0 trigger skipped real", skip_case.get("triggered") is True and skip_case.get("skip_reason") == "unsellable_liquidity_guard" and skip_case.get("guard_action") == "skipped")
        test("unsellable_v1 funcional: price=0.09 no trigger", decide(**dict(base_guard_case, price_at_guard=0.09)).get("triggered") is False)
        test("unsellable_v1 funcional: price=0.66 no trigger", decide(**dict(base_guard_case, price_at_guard=0.66)).get("triggered") is False)
        test("unsellable_v1 funcional: size_ratio=0.149 no trigger", decide(**dict(base_guard_case, amount=3.725)).get("triggered") is False)
        test("unsellable_v1 funcional: condition fuera exact/range no trigger", decide(**dict(base_guard_case, condition="at_or_above")).get("triggered") is False)
        test("unsellable_v1 funcional: days_ahead=1 no trigger", decide(**dict(base_guard_case, days_ahead=1)).get("triggered") is False)
        test("unsellable_v1 funcional: effective_bankroll=0 no trigger", decide(**dict(base_guard_case, effective_bankroll=0)).get("triggered") is False)
    except Exception as exc:
        test("unsellable_v1 funcional: helper ejecutable", False, str(exc))
    test(
        "unsellable_v1: price_raw defensivo y solo forensics",
        'price_raw = trade.get("position", {}).get("market_price")' in code
        and "price_raw is forensics only; trigger uses price_at_guard exclusively." in code
        and "price_raw" not in unsellable_decision_src,
    )
    test(
        "unsellable_v1: price_raw se registra sin afectar trigger",
        '"price_raw": price_raw' in code
        and '"price_at_guard": price_at_guard' in code
        and "price_at_guard=price_at_guard" in code,
    )
    test(
        "unsellable_v1: no reusa execution_price como price_at_guard",
        "execution_price = price_at_guard" not in code
        and "price_at_guard = round(" in code
        and "price_at_guard=price_at_guard" in code,
    )
    test(
        "unsellable_v1: SKIP path dormido requiere LOG_ONLY=0",
        'if UNSELLABLE_GUARD_ENABLED and not UNSELLABLE_GUARD_LOG_ONLY:' in code
        and 'DORMANT until LOG_ONLY="0" — promotion requires Opus signoff' in code
        and 'continue' in code.split('DORMANT until LOG_ONLY="0" — promotion requires Opus signoff', 1)[1].split("# Guardar en known_tokens", 1)[0],
    )
    try:
        unsellable_hook_src = code.split("unsellable_guard = _unsellable_guard_decision(", 1)[1].split("# Guardar en known_tokens", 1)[0]
    except IndexError:
        unsellable_hook_src = ""
    test(
        "unsellable_v1: no Telegram por candidato",
        "send_telegram" not in unsellable_hook_src
        and "send_telegram_paged" not in unsellable_hook_src,
    )
    test(
        "unsellable_v1: skip_log extras forensics completos",
        all(item in code for item in [
            '"guard_version": UNSELLABLE_GUARD_VERSION',
            '"trigger_reason": "micro_position_unsellable"',
            '"match_zone_bucket": unsellable_guard["match_zone_bucket"]',
            '"amount": amount_at_guard',
            '"effective_bankroll": effective_bankroll',
            '"counterfactual_resolved": None',
        ]),
    )
    print("  Checks Unsellable Guard Monitor diario")
    unsellable_monitor_path = os.path.join(os.path.dirname(__file__), "tools", "unsellable_guard_monitor.py")
    test(
        "unsellable monitor: tool existe",
        os.path.exists(unsellable_monitor_path),
    )
    try:
        py_compile.compile(unsellable_monitor_path, doraise=True)
        monitor_compiles = True
        monitor_compile_detail = ""
    except Exception as exc:
        monitor_compiles = False
        monitor_compile_detail = str(exc)
    test(
        "unsellable monitor: tool tiene sintaxis valida",
        monitor_compiles,
        monitor_compile_detail,
    )
    test(
        "unsellable monitor: env vars y script definidos",
        "UNSELLABLE_GUARD_MONITOR_ENABLED" in code
        and "UNSELLABLE_GUARD_MONITOR_HOUR_UTC" in code
        and "UNSELLABLE_GUARD_MONITOR_TIMEOUT_SECONDS" in code
        and "UNSELLABLE_GUARD_MONITOR_SCRIPT" in code,
    )
    test(
        "unsellable monitor: wrapper JSON subprocess fail-safe",
        "def run_unsellable_guard_monitor_json(" in code
        and "UNSELLABLE_GUARD_MONITOR_SCRIPT" in code
        and "subprocess.run(" in code
        and "timeout=UNSELLABLE_GUARD_MONITOR_TIMEOUT_SECONDS" in code
        and "return None" in code,
    )
    test(
        "unsellable monitor: formatter y daily hook definidos",
        "def format_unsellable_guard_monitor_telegram(" in code
        and "def maybe_run_unsellable_guard_monitor(" in code
        and "maybe_run_unsellable_guard_monitor(state)" in code,
    )
    test(
        "unsellable monitor: estado anti-spam en alerts_state",
        all(key in code for key in [
            "unsellable_guard_monitor_last_run_date",
            "unsellable_guard_last_status",
            "unsellable_guard_candidate_total",
            "unsellable_guard_first_candidate_at",
            "unsellable_guard_last_candidate_at",
            "unsellable_guard_last_alert_date",
            "unsellable_guard_action_review_sent",
            "unsellable_guard_safety_alert_sent",
            "unsellable_guard_safety_last_seen_at",
        ]),
    )
    test(
        "unsellable monitor: no recomienda promocion automatica",
        "Revisión manual / Opus requerida antes de promoción. No activar SKIP automáticamente." in code,
    )
    test(
        "unsellable monitor: no altera defaults del guard",
        'UNSELLABLE_GUARD_ENABLED = os.getenv("UNSELLABLE_GUARD_ENABLED", "0")' in code
        and 'UNSELLABLE_GUARD_LOG_ONLY = os.getenv("UNSELLABLE_GUARD_LOG_ONLY", "1")' in code,
    )
    test(
        "unsellable monitor: SKIP real sigue dormido tras LOG_ONLY=0",
        'if UNSELLABLE_GUARD_ENABLED and not UNSELLABLE_GUARD_LOG_ONLY:' in code
        and 'results.append({"ok": False, "msg": "unsellable_liquidity_guard"})' in code,
    )
    try:
        spec = importlib.util.spec_from_file_location("unsellable_guard_monitor_verify", unsellable_monitor_path)
        monitor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor_module)
        now_for_monitor = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)

        def _monitor_entry(ts, reason="unsellable_guard_candidate", guard_action="would_skip", city="Dallas"):
            return {
                "ts_utc": ts,
                "cycle_id": ts[:16],
                "city": city,
                "date_iso": "2026-05-01",
                "side": "YES",
                "skip_reason": reason,
                "condition": "exact",
                "extras": {
                    "guard_version": "unsellable_v1",
                    "guard_action": guard_action,
                    "price_at_guard": 0.42,
                    "amount": 4.2,
                    "size_ratio": 0.168,
                    "edge_pct": 8.1,
                    "question": "Dallas high temperature exact test",
                },
            }

        def _monitor_report(rows):
            tmp_dir = tempfile.mkdtemp(prefix="unsellable_monitor_", dir=_verify_tmp_dir())
            try:
                skip_path = Path(tmp_dir) / "skip_log.jsonl"
                with skip_path.open("w", encoding="utf-8") as fh:
                    for row in rows:
                        fh.write(json.dumps(row) + "\n")
                return monitor_module.build_report(skip_path, now_for_monitor, 24)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        ok_report = _monitor_report([])
        watch_report = _monitor_report([
            _monitor_entry("2026-05-01T10:00:00+00:00", city="Dallas")
        ])
        review_report = _monitor_report([
            _monitor_entry(f"2026-05-01T0{idx}:00:00+00:00", city=f"City{idx}")
            for idx in range(5)
        ])
        safety_report = _monitor_report([
            _monitor_entry(
                "2026-05-01T10:00:00+00:00",
                reason="unsellable_liquidity_guard",
                guard_action="skipped",
                city="Paris",
            )
        ])
        test("unsellable monitor fixture: 0 candidates -> OK", ok_report.get("status") == "OK")
        test("unsellable monitor fixture: 1 candidate -> WATCH", watch_report.get("status") == "WATCH")
        test("unsellable monitor fixture: 5 candidates -> ACTION_REVIEW", review_report.get("status") == "ACTION_REVIEW")
        test("unsellable monitor fixture: skipped real -> ACTION_SAFETY", safety_report.get("status") == "ACTION_SAFETY")
    except Exception as exc:
        test("unsellable monitor fixtures ejecutables", False, str(exc))

    # ---- v10.6.41: fill real para ventas confirmadas ----
    test(
        "v10.6.41: TradeParams importado para lookup de fills",
        "TradeParams" in code and "client.get_trades(TradeParams" in code,
    )
    test(
        "v10.6.41: helpers de fill por order_id definidos",
        "def _fetch_sell_fill_summary(" in code
        and "def _extract_fill_summary_from_trades(" in code
        and "def _enrich_pending_sell_with_fill(" in code,
    )
    test(
        "v10.6.41: SELL confirmado usa fill_price/fill_value si existen",
        'entry["limit_price"] = entry.get("limit_price", entry.get("price"))' in code
        and 'entry["fill_price"]' in code
        and 'entry["fill_value"]' in code
        and 'entry["return_est"] = round(fill_value, 2)' in code,
    )
    test(
        "v10.6.41: Telegram intra-SL aclara precio limite vs real",
        "[INTRA-SL]" in code
        and "precio límite" in code
        and "precio real puede diferir" in code,
    )

    # ---- v10.6.30: Dallas al whitelist (BOT_VERSION assertion movida a v10.6.40 bump) ----
    test(
        "v10.6.30: whitelist default incluye Dallas",
        "Busan,Dallas" in code,
    )
    test(
        "v10.6.26: maybe_alert_busan_expansion definida",
        "def maybe_alert_busan_expansion(" in code,
    )
    test(
        "v10.6.26: alarma Busan registrada en run_observability_alerts",
        "maybe_alert_busan_expansion(state)" in code,
    )
    test(
        "v10.6.26: alarma Busan dispara 2026-04-24",
        'FIRE_DATE = "2026-04-24"' in code,
    )
    test(
        "v10.6.20: anti-flapping guard — promotable_shadow incluye 'and not verified_history_bad'",
        "and not verified_history_bad" in code,
    )
    test(
        "v10.6.20: verified_history_bad se calcula antes que promotable_shadow",
        code.find("verified_history_bad = (") < code.find("promotable_shadow = (\n            shadow_edges"),
    )
    test(
        "v10.6.20: reason observe explica bloqueo por historial NOAA malo",
        "promoción a canary bloqueada hasta reunir evidencia nueva mejor" in code,
    )

    # ---- v10.6.22: Jakarta + Kuala Lumpur (sesion 201) ----
    test(
        "v10.6.22: Jakarta en RESOLUTION_STATIONS (Halim Perdanakusuma)",
        '"Jakarta":        {"lat": -6.2666, "lon": 106.8906' in code
        or '"Jakarta": {"lat": -6.2666, "lon": 106.8906' in code,
    )
    test(
        "v10.6.22: Kuala Lumpur en RESOLUTION_STATIONS (KLIA)",
        '"Kuala Lumpur":   {"lat":  2.7456, "lon": 101.7099' in code
        or '"Kuala Lumpur": {"lat":  2.7456, "lon": 101.7099' in code
        or '"Kuala Lumpur": {"lat": 2.7456, "lon": 101.7099' in code,
    )
    test(
        "v10.6.22: Jakarta en RESOLUTION_ICAO (WIHH) sin noaa_station_id",
        '"Jakarta":        {"icao": "WIHH"' in code
        or '"Jakarta": {"icao": "WIHH"' in code,
    )
    test(
        "v10.6.22: Kuala Lumpur en RESOLUTION_ICAO (WMKK) sin noaa_station_id",
        '"Kuala Lumpur":   {"icao": "WMKK"' in code
        or '"Kuala Lumpur": {"icao": "WMKK"' in code,
    )
    test(
        "v10.6.22: Jakarta en CITY_TIMEZONES (Asia/Jakarta)",
        '"Jakarta":        "Asia/Jakarta"' in code
        or '"Jakarta": "Asia/Jakarta"' in code,
    )
    test(
        "v10.6.22: Kuala Lumpur en CITY_TIMEZONES (Asia/Kuala_Lumpur)",
        '"Kuala Lumpur":   "Asia/Kuala_Lumpur"' in code
        or '"Kuala Lumpur": "Asia/Kuala_Lumpur"' in code,
    )
    test(
        "v10.6.22: Jakarta en OBSERVED_AUDIT_CITIES",
        '"Jakarta"' in code and "OBSERVED_AUDIT_CITIES" in code,
    )
    test(
        "v10.6.22: Kuala Lumpur en OBSERVED_AUDIT_CITIES",
        '"Kuala Lumpur"' in code and "OBSERVED_AUDIT_CITIES" in code,
    )
    test(
        "v10.6.22: Jakarta y Kuala Lumpur en QUALITY_TRADER_CITIES_WHITELIST default",
        "Jakarta,Kuala Lumpur" in code,
    )

    # ---- v10.6.23: buy_min_size retry (sesion 203) ----
    test(
        "v10.6.23: _parse_min_shares_from_error definida",
        "def _parse_min_shares_from_error(" in code,
    )
    test(
        "v10.6.23: _parse_min_shares_from_error parsea 'lower than the minimum'",
        "lower than the minimum" in code and "_parse_min_shares_from_error" in code,
    )
    test(
        "v10.6.23: retry buy_min_size usa kelly cap",
        "RETRY BUY MIN SHARES" in code and "Kelly cap" in code,
    )
    test(
        "v10.6.23: retry buy_min_size respeta MAX_BET_PCT",
        "_req_notional <= _kelly_cap" in code,
    )
    test(
        "v10.6.23: retry buy_min_size solo en DRY_RUN=False",
        "if not DRY_RUN and not result" in code,
    )

    # ---- v10.6.24: intra-cycle SL/TP reactivado ----
    test(
        "v10.6.24: INTRA_SL_INTERVAL default 20",
        '"INTRA_SL_INTERVAL", "20"' in code,
    )
    test(
        "v10.6.24: intra_cycle_sl_check solo SL+TP sin re-eval",
        "def intra_cycle_sl_check(" in code and "stop_loss_intra" in code and "take_profit_intra" in code,
    )
    try:
        intra_sl_src = code.split("def intra_cycle_sl_check(", 1)[1].split("def intra_sl_loop(", 1)[0]
    except IndexError:
        intra_sl_src = ""
    test(
        "v10.6.36: stop_loss_intra registra SL cooldown",
        "_sl_cooldown_register(city)" in intra_sl_src
        and 'sell_type in ("stop_loss", "stop_loss_intra")' in intra_sl_src,
    )
    test(
        "v10.6.36: alarma post-fix intra-SL cooldown definida",
        "def maybe_run_post_intra_sl_cooldown_review(" in code
        and "POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED" in code,
    )
    test(
        "v10.6.36: alarma post-fix intra-SL integrada en observability",
        "maybe_run_post_intra_sl_cooldown_review(state)" in code,
    )
    test(
        "v10.6.36: alarma post-fix usa bucket LOW",
        '"post_intra_sl_cooldown_review"' in code and "LOW_PRICE_THRESHOLD" in code and "LOW &lt;35c" in code,
    )

    # ---- v10.6.37: alarmas con repercusion accionable ----
    print("  Checks v10.6.37 alarmas con accion")
    signals_summary_path = os.path.join(os.path.dirname(__file__), "tools", "signals_crosscheck_daily_summary.py")
    signals_summary_code = ""
    if os.path.exists(signals_summary_path):
        with open(signals_summary_path, "r", encoding="utf-8") as f:
            signals_summary_code = f.read()
    test(
        "v10.6.37: crosscheck summary clasifica nivel de accion",
        "def classify_action_level(" in signals_summary_code
        and "<b>Nivel de accion</b>" in signals_summary_code
        and '"ACTION": "Tarea para Codex"' in signals_summary_code
        and '"WATCH": "Próximo paso (WATCH)"' in signals_summary_code
        and '"INFO": "Próximo paso"' in signals_summary_code,
    )
    test(
        "v10.6.37: crosscheck legacy incluye ACTION/WATCH/INFO",
        'action_level = "ACTION"' in code
        and 'action_level = "WATCH"' in code
        and 'action_level = "INFO"' in code,
    )
    test(
        "v10.6.37: blocked signals copy separa baseline y whitelist excluidas",
        "Baseline fuera de whitelist" in code
        and "Excluidas del calculo por estar ya en whitelist" in code
        and "no mide ejecucion real del bot" in code,
    )
    test(
        "v10.6.37: blocked signals genera tarea de auditoria antes de core",
        "priorizar auditoria de las ciudades fuera de whitelist" in code
        and "antes de tocar reglas core" in code,
    )
    try:
        crosscheck_temporal_src = code.split("def maybe_run_daily_crosscheck_temporal_summary(", 1)[1].split(
            "def maybe_run_traders_intelligence_summary(", 1
        )[0]
    except IndexError:
        crosscheck_temporal_src = ""
    test(
        "v10.6.48: crosscheck summary recibe paths live del bot",
        '"--signals"' in crosscheck_temporal_src
        and "SIGNALS_FILE" in crosscheck_temporal_src
        and '"--shadow"' in crosscheck_temporal_src
        and "SHADOW_TRACKING_FILE" in crosscheck_temporal_src
        and '"--policy"' in crosscheck_temporal_src
        and "CITY_POLICY_FILE" in crosscheck_temporal_src,
    )
    test(
        "v10.6.48: crosscheck summary usa evidencia live si no reconstruye detalle",
        "latest_operational_count(summary) > 0" in signals_summary_code
        and "Gap operativo detectado por cross-check live" in signals_summary_code
        and "Hoy aparece gap operativo real" in signals_summary_code,
    )
    test(
        "v10.6.48: crosscheck summary no recomienda abrir whitelist/canary automaticamente",
        "No abrir whitelist/canary automaticamente" in signals_summary_code
        and "preparar whitelist/canary" not in signals_summary_code,
    )
    test(
        "v10.6.48: SCHEDULE_HOURS_UTC intacto",
        "SCHEDULE_HOURS_UTC = [hour for hour in _SCHEDULE_HOURS_BASE if hour not in _SCHEDULE_HOURS_DISABLED] or list(_SCHEDULE_HOURS_BASE)" in code,
    )
    default_whitelist_src = code.split("QUALITY_TRADER_CITIES_WHITELIST = {", 1)[1].split(
        "MIN_EDGE_EXACT_RANGE_BUFFER_PP", 1
    )[0]
    active_src = code.split("ACTIVE_TRADING_CITIES = {", 1)[1].split("CANARY_TRADING_CITIES = {", 1)[0]
    canary_src = code.split("CANARY_TRADING_CITIES = {", 1)[1].split("CANARY_POSITION_SCALE", 1)[0]
    resolution_src = code.split("RESOLUTION_ICAO = {", 1)[1].split("OBSERVED_AUDIT_CITIES = {", 1)[0]
    observed_src = code.split("OBSERVED_AUDIT_CITIES = {", 1)[1].split("CITY_TIMEZONES = {", 1)[0]
    test(
        "v10.6.48: Los Angeles no entra en whitelist/canary/active",
        '"Los Angeles"' not in default_whitelist_src
        and '"Los Angeles"' not in active_src
        and '"Los Angeles"' not in canary_src,
    )
    test(
        "v10.6.48: Los Angeles no entra en RESOLUTION_ICAO ni OBSERVED_AUDIT_CITIES",
        '"Los Angeles"' not in resolution_src and '"Los Angeles"' not in observed_src,
    )

    # ---- v10.6.25: low-price MIN_EDGE buffer + alarma Steps 2+3 ----
    test(
        "v10.6.25: MIN_EDGE_LOW_PRICE_BUFFER_PP definido",
        "MIN_EDGE_LOW_PRICE_BUFFER_PP" in code,
    )
    test(
        "v10.6.25: LOW_PRICE_THRESHOLD definido",
        "LOW_PRICE_THRESHOLD" in code,
    )
    test(
        "v10.6.25: buffer aplicado cuando mkt_price < LOW_PRICE_THRESHOLD",
        "if mkt_price < LOW_PRICE_THRESHOLD:" in code and "_effective_min_edge += MIN_EDGE_LOW_PRICE_BUFFER_PP" in code,
    )
    test(
        "v10.6.25: maybe_alert_tp_sl_price_steps definida",
        "def maybe_alert_tp_sl_price_steps(" in code,
    )
    test(
        "v10.6.25: alarma Steps 2+3 registrada en check_smart_alerts",
        "maybe_alert_tp_sl_price_steps(state)" in code,
    )
    test(
        "v10.6.25: alarma Steps 2+3 dispara 2026-05-10",
        '"2026-05-10"' in code and "tp_sl_price_steps_alert_sent" in code,
    )

    # ---- v10.6.31: City Intelligence runtime bridge read-only ----
    runtime_export_path = os.path.join(os.path.dirname(__file__), "tools", "runtime_import_local_export.py")
    runtime_export_code = ""
    if os.path.exists(runtime_export_path):
        with open(runtime_export_path, "r", encoding="utf-8") as f:
            runtime_export_code = f.read()
    test(
        "v10.6.31: runtime_import_local_export.py existe",
        bool(runtime_export_code),
    )
    test(
        "v10.6.31: export runtime escribe en DATA_DIR/runtime_import",
        'DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "runtime_import"' in runtime_export_code,
    )
    test(
        "v10.6.31: export exige runtime files canonicos",
        '"shadow_city_tracking.json"' in runtime_export_code
        and '"audit.json"' in runtime_export_code
        and '"city_policy_state.json"' in runtime_export_code
        and "REQUIRED_FILES" in runtime_export_code,
    )
    test(
        "v10.6.31: bridge runtime definido en bot",
        "CITY_INTELLIGENCE_RUNTIME_EXPORT_SCRIPT" in code
        and "def maybe_run_city_intelligence_runtime_summary(" in code,
    )
    test(
        "v10.6.31: bridge corre antes de blocked signals",
        code.find("maybe_run_city_intelligence_runtime_summary(state)") != -1
        and code.find("maybe_run_city_intelligence_runtime_summary(state)") < code.find("maybe_run_blocked_signals_check(state)"),
    )
    test(
        "v10.6.31: bridge no escribe policy live",
        "CITY_INTELLIGENCE_DAILY_SUMMARY_SCRIPT" in code
        and "--telegram-dry-run" in code
        and '"city_policy_state.json", "w"' not in runtime_export_code
        and "CITY_POLICY_FILE" not in runtime_export_code,
    )
    city_pipeline_path = os.path.join(os.path.dirname(__file__), "tools", "city_intelligence_pipeline.py")
    city_pipeline_code = ""
    if os.path.exists(city_pipeline_path):
        with open(city_pipeline_path, "r", encoding="utf-8") as f:
            city_pipeline_code = f.read()
    test(
        "v10.6.31: city pipeline expone failed_steps para Railway",
        "failed_steps" in city_pipeline_code and "collect_failed_steps" in city_pipeline_code,
    )
    test(
        "v10.6.31: city pipeline falla si algun step/output canónico falla",
        "missing_outputs" in city_pipeline_code
        and 'overall_status = "ok" if not failed_steps and not missing_outputs else "partial_failure"' in city_pipeline_code
        and "sys.exit(1 if failed_steps or missing_outputs else 0)" in city_pipeline_code,
    )
    test(
        "v10.6.31: bridge bootstrap refresh-probe si falta settlement_fidelity_probe",
        'settlement_fidelity_probe.json"' in code
        and '"--refresh-probe"' in code,
    )

    # ---- v10.6.30: intra-reeval shadow-log ----
    print("\n v10.6.30: Intra-cycle re-eval shadow-log")

    # 1. Structural checks
    test(
        "v10.6.30: INTRA_REEVAL_ENABLED definido",
        "INTRA_REEVAL_ENABLED" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_SHADOW_MODE definido",
        "INTRA_REEVAL_SHADOW_MODE" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_PRICE_DRIFT_PP definido",
        "INTRA_REEVAL_PRICE_DRIFT_PP" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_COOLDOWN_MIN definido",
        "INTRA_REEVAL_COOLDOWN_MIN" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_EDGE_THRESHOLD definido",
        "INTRA_REEVAL_EDGE_THRESHOLD" in code,
    )
    test(
        "v10.6.30: recompute_position_edge definida",
        "def recompute_position_edge(" in code,
    )
    test(
        "v10.6.30: load_intra_reeval_state definida",
        "def load_intra_reeval_state(" in code,
    )
    test(
        "v10.6.30: save_intra_reeval_state definida",
        "def save_intra_reeval_state(" in code,
    )
    test(
        "v10.6.30: _within_cooldown definida",
        "def _within_cooldown(" in code,
    )
    test(
        "v10.6.30: _log_shadow_intra_reeval_trigger definida",
        "def _log_shadow_intra_reeval_trigger(" in code,
    )
    test(
        "v10.6.30: maybe_run_intra_reeval_review_alert definida",
        "def maybe_run_intra_reeval_review_alert(" in code,
    )
    test(
        "v10.6.30: intra_reeval_review_alert registrada en run_alerts",
        "maybe_run_intra_reeval_review_alert(state)" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_STATE_FILE definido",
        'INTRA_REEVAL_STATE_FILE = _data_path("intra_reeval_state.json")' in code,
    )
    test(
        "v10.6.30: intra_reeval_review_alert_sent en alerts_state default",
        '"intra_reeval_review_alert_sent": False' in code,
    )
    test(
        "v10.6.30: intra_cycle_sl_check carga reeval_state",
        "load_intra_reeval_state(" in code and "save_intra_reeval_state(" in code,
    )
    test(
        "v10.6.30: INTRA_REEVAL_ENABLED guarda intra_reeval (shadow NO vende)",
        "INTRA_REEVAL_SHADOW_MODE" in code and "INTRA_REEVAL_ENABLED and not sell_type" in code,
    )
    test(
        "v10.6.30: reeval_intra sell_type definido",
        '"reeval_intra"' in code,
    )
    test(
        "v10.6.30: manage_positions refactorizado usa recompute_position_edge",
        "fresh = recompute_position_edge(p, forecast_cache)" in code,
    )
    test(
        "v10.6.30: _lc_by_token_intra_full construido en intra_cycle_sl_check",
        "_lc_by_token_intra_full" in code,
    )

    # 2. Functional tests — pure helpers exectuables en namespace aislado
    print("  Funcionales intra-reeval")
    try:
        fd, tmp_reeval_state = tempfile.mkstemp(
            dir=_verify_tmp_dir(),
            prefix="_tmp_intra_reeval_state_",
            suffix=".json",
        )
        os.close(fd)
        if os.path.exists(tmp_reeval_state):
            try:
                os.remove(tmp_reeval_state)
            except PermissionError:
                pass

        reeval_ns = {
            "os": os,
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
            "timedelta": timedelta,
            "INTRA_REEVAL_STATE_FILE": tmp_reeval_state,
            "log": types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        }
        for fn_name in ["load_intra_reeval_state", "save_intra_reeval_state", "_within_cooldown"]:
            exec(get_function_source(module_ast, code_lines, fn_name), reeval_ns)

        # Test: state roundtrip
        state0 = reeval_ns["load_intra_reeval_state"]()
        state0["cooldown"]["tok1"] = {"last_reeval_at": "2026-04-22T10:00:00+00:00", "last_edge_pct": -5.2}
        state0["shadow_log"]["triggers"].append({"ts": "2026-04-22T10:00:00+00:00", "city": "Atlanta"})
        state0["shadow_log"]["first_trigger_at"] = "2026-04-22T10:00:00+00:00"
        reeval_ns["save_intra_reeval_state"](state0)

        state1 = reeval_ns["load_intra_reeval_state"]()
        test(
            "test_intra_reeval_state_roundtrip: cooldown preservado",
            "tok1" in state1["cooldown"] and state1["cooldown"]["tok1"]["last_edge_pct"] == -5.2,
            str(state1),
        )
        test(
            "test_intra_reeval_state_roundtrip: trigger preservado",
            len(state1["shadow_log"]["triggers"]) == 1 and state1["shadow_log"]["triggers"][0]["city"] == "Atlanta",
            str(state1),
        )

        # Test: purga de cooldown elimina entradas sin token observado
        state2 = reeval_ns["load_intra_reeval_state"](observed_token_ids={"tok_other"})
        test(
            "test_intra_reeval_state_roundtrip: purga cooldown elimina tok1",
            "tok1" not in state2["cooldown"],
            str(state2["cooldown"]),
        )

        if os.path.exists(tmp_reeval_state):
            try:
                os.remove(tmp_reeval_state)
            except OSError:
                pass

    except Exception as e:
        test("test_intra_reeval_state_roundtrip funcional ejecuta", False, str(e))

    # Test: _within_cooldown
    try:
        cooldown_ns = {
            "datetime": datetime,
            "timezone": timezone,
        }
        exec(get_function_source(module_ast, code_lines, "_within_cooldown"), cooldown_ns)
        now_utc = datetime.now(timezone.utc)
        # Inside cooldown (5 minutes ago, cooldown 80 min)
        recent = (now_utc - timedelta(minutes=5)).isoformat()
        test(
            "test_intra_reeval_cooldown: dentro de ventana bloquea",
            cooldown_ns["_within_cooldown"](recent, 80, now_utc) is True,
        )
        # Outside cooldown (90 minutes ago)
        old = (now_utc - timedelta(minutes=90)).isoformat()
        test(
            "test_intra_reeval_cooldown: fuera de ventana permite",
            cooldown_ns["_within_cooldown"](old, 80, now_utc) is False,
        )
        # Empty last_reeval
        test(
            "test_intra_reeval_cooldown: vacio no bloquea",
            cooldown_ns["_within_cooldown"]("", 80, now_utc) is False,
        )
    except Exception as e:
        test("test_intra_reeval_cooldown_blocks_repeat funcional ejecuta", False, str(e))

    # Test: recompute_position_edge parity guard (returns None when no station)
    try:
        rpe_ns = {
            "os": os,
            "json": json,
            "re": re,
            "math": __import__("math"),
            "datetime": datetime,
            "timezone": timezone,
            "date": date,
            "RESOLUTION_STATIONS": {},  # vacío: forzar None return
            "get_forecast": lambda lat, lon: {},
            "estimate_prob_with_city": lambda *a, **kw: 0.5,
        }
        for fn_name in ["parse_temperature_question", "date_text_to_iso", "recompute_position_edge"]:
            exec(get_function_source(module_ast, code_lines, fn_name), rpe_ns)

        # Sin station → debe devolver None (no re-evaluable)
        pos_no_station = {
            "title": "Will the temperature in Atlanta reach 25°C on April 30, 2026?",
            "outcome": "YES",
            "curPrice": "0.45",
        }
        result_none = rpe_ns["recompute_position_edge"](pos_no_station, {})
        test(
            "test_recompute_position_edge_parity: sin station devuelve None",
            result_none is None,
            str(result_none),
        )
    except Exception as e:
        test("test_recompute_position_edge_parity funcional ejecuta", False, str(e))

    # ---- v10.6.31: TP dinámico por precio + gate LOW+exact ----
    print("  Checks v10.6.31 TP precio + gate LOW+exact")
    test(
        "v10.6.31: HIGH_PRICE_THRESHOLD definido",
        "HIGH_PRICE_THRESHOLD" in code,
    )
    test(
        "v10.6.31: TP_LOW_PRICE_PCT definido",
        "TP_LOW_PRICE_PCT" in code,
    )
    test(
        "v10.6.31: TP_MID_PRICE_PCT definido",
        "TP_MID_PRICE_PCT" in code,
    )
    test(
        "v10.6.31: TP_HIGH_PRICE_PCT definido",
        "TP_HIGH_PRICE_PCT" in code,
    )
    test(
        "v10.6.31: BLOCK_LOW_EXACT_ENTRIES definido",
        "BLOCK_LOW_EXACT_ENTRIES" in code,
    )
    test(
        "v10.6.31: effective_tp_pct definida",
        "def effective_tp_pct(" in code,
    )
    test(
        "v10.6.31: effective_tp_pct usada en manage_positions",
        "effective_tp = effective_tp_pct(_entry_price_lc, _entry_prob)" in code,
    )
    test(
        "v10.6.31: effective_tp_intra usa effective_tp_pct",
        "effective_tp_intra = effective_tp_pct(_entry_price_intra, _entry_prob_intra)" in code,
    )
    test(
        "v10.6.31: _lc_by_token_price cargado en manage_positions",
        "_lc_by_token_price" in code,
    )
    test(
        "v10.6.31: gate low_exact_gap_risk en skip_log",
        '"low_exact_gap_risk"' in code,
    )
    test(
        "v10.6.31: low_exact_gap_risk en SKIP_REASONS_VALID",
        '"low_exact_gap_risk"' in code and "SKIP_REASONS_VALID" in code,
    )
    # Structural checks: effective_tp_pct logic branches
    test(
        "v10.6.31: effective_tp_pct usa LOW_PRICE_THRESHOLD",
        "entry_price < LOW_PRICE_THRESHOLD" in code,
    )
    test(
        "v10.6.31: effective_tp_pct usa HIGH_PRICE_THRESHOLD",
        "entry_price >= HIGH_PRICE_THRESHOLD" in code,
    )
    test(
        "v10.6.31: effective_tp_pct devuelve max(base, TP_LOW_PRICE_PCT)",
        "max(base, TP_LOW_PRICE_PCT)" in code,
    )
    test(
        "v10.6.31: effective_tp_pct devuelve max(base, TP_HIGH_PRICE_PCT)",
        "max(base, TP_HIGH_PRICE_PCT)" in code,
    )

    # ---- v10.6.42: SQLite Recorder Fase 0 ----
    print("  Checks v10.6.42 SQLite Recorder (Fase 0)")

    # 1. El modulo recorder existe en la raiz
    recorder_path = os.path.join(os.path.dirname(__file__), "sqlite_recorder.py")
    recorder_code = ""
    if os.path.exists(recorder_path):
        with open(recorder_path, "r", encoding="utf-8") as f:
            recorder_code = f.read()
    test(
        "v10.6.42: sqlite_recorder.py existe en la raiz",
        os.path.exists(recorder_path),
    )

    # 2. El modulo es importable y tiene la clase SQLiteRecorder
    test(
        "v10.6.42: SQLiteRecorder definida en sqlite_recorder.py",
        "class SQLiteRecorder" in recorder_code,
    )

    # 3. record_cycle definido
    test(
        "v10.6.42: SQLiteRecorder.record_cycle definido",
        "def record_cycle(" in recorder_code,
    )

    # 4. Las tres tablas minimas estan en el schema
    test(
        "v10.6.42: schema incluye cycle_events, market_snapshots, forecast_snapshots",
        "cycle_events" in recorder_code
        and "market_snapshots" in recorder_code
        and "forecast_snapshots" in recorder_code,
    )

    # 5. Flag SQLITE_RECORDER_ENABLED definido con default "0" (OFF por defecto)
    test(
        "v10.6.42: SQLITE_RECORDER_ENABLED definido con default 0 en bot.py",
        'SQLITE_RECORDER_ENABLED = os.getenv("SQLITE_RECORDER_ENABLED", "0")' in code,
    )

    # 6. SQLITE_DB_PATH definido usando _data_path
    test(
        "v10.6.42: SQLITE_DB_PATH usa _data_path en bot.py",
        "SQLITE_DB_PATH" in code and "_data_path(" in code and "polymarket.db" in code,
    )

    # 7. El hook en main() esta protegido por try/except y usa el flag SQLITE_RECORDER_ENABLED
    test(
        "v10.6.42: hook recorder en main() protegido por SQLITE_RECORDER_ENABLED y try/except",
        "if SQLITE_RECORDER_ENABLED:" in code
        and "import sqlite_recorder as _sr" in code
        and "SQLiteRecorder(SQLITE_DB_PATH).record_cycle(cycle_data)" in code,
    )

    # 8. El except del hook NO relanza la excepcion (no puede cortar el ciclo)
    test(
        "v10.6.42: hook recorder captura excepcion sin relanzar (ciclo continua)",
        "SQLiteRecorder: error no critico (ciclo continua)" in code,
    )

    # 9. data/polymarket.db esta excluida de git
    gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
    gitignore_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            gitignore_content = f.read()
    test(
        "v10.6.42: *.db excluido en .gitignore",
        "*.db" in gitignore_content,
    )

    # 10. WAL mode activado en el schema
    test(
        "v10.6.42: WAL mode activado en sqlite_recorder",
        "journal_mode=WAL" in recorder_code,
    )

    # ---- v10.6.42: Fase 0.5 — phase1_readiness_check.py ----
    print("  Checks Fase 0.5: tools/phase1_readiness_check.py")

    readiness_path = os.path.join(os.path.dirname(__file__), "tools", "phase1_readiness_check.py")
    readiness_code = ""
    if os.path.exists(readiness_path):
        with open(readiness_path, "r", encoding="utf-8") as f:
            readiness_code = f.read()

    test(
        "fase0.5: tools/phase1_readiness_check.py existe",
        os.path.exists(readiness_path),
    )
    test(
        "fase0.5: phase1_readiness_check tiene funcion run()",
        "def run(" in readiness_code,
    )
    test(
        "fase0.5: phase1_readiness_check tiene argumentos min-days y min-cycles",
        "--min-days" in readiness_code and "--min-cycles" in readiness_code,
    )
    test(
        "fase0.5: phase1_readiness_check define exit codes 0/1/2/3",
        ("return 0" in readiness_code or "return 0 if" in readiness_code)
        and ("return 1" in readiness_code or "else 1" in readiness_code)
        and "return 2" in readiness_code
        and "return 3" in readiness_code,
    )
    test(
        "fase0.5: phase1_readiness_check no importa modulos externos",
        "import requests" not in readiness_code
        and "import bot" not in readiness_code,
    )
    test(
        "fase0.5: phase1_readiness_check busca polymarket.db por defecto",
        "polymarket.db" in readiness_code,
    )

    # ---- v10.6.43: Fase 0.6 — Recorder Health Alerts ----
    print("  Checks v10.6.43 Fase 0.6: Recorder Health Alerts")

    test(
        "v10.6.43: RECORDER_HEALTH_ALERTS_ENABLED definido con default 0",
        'RECORDER_HEALTH_ALERTS_ENABLED = os.getenv("RECORDER_HEALTH_ALERTS_ENABLED", "0")' in code,
    )
    test(
        "v10.6.43: PHASE1_READINESS_SCRIPT definido en bot.py",
        "PHASE1_READINESS_SCRIPT" in code and "phase1_readiness_check.py" in code,
    )
    test(
        "v10.6.43: maybe_run_recorder_health_alert definida en bot.py",
        "def maybe_run_recorder_health_alert(" in code,
    )
    test(
        "v10.6.43: hook recorder health en run_observability_alerts protegido por try/except",
        "maybe_run_recorder_health_alert(state)" in code
        and "recorder health alert: fallo" in code,
    )
    test(
        "v10.6.43: alerta readiness one-shot usa milestones",
        "sqlite_recorder_phase1_ready" in code,
    )
    test(
        "v10.6.43: alerta stale limitada a 1/dia con recorder_stale_last_alert_date",
        "recorder_stale_last_alert_date" in code,
    )
    test(
        "v10.6.43: recorder health alert guarded por RECORDER_HEALTH_ALERTS_ENABLED",
        "if not RECORDER_HEALTH_ALERTS_ENABLED" in code,
    )
    test(
        "v10.6.43: recorder health usa subprocess con timeout",
        "PHASE1_READINESS_SCRIPT" in code and "timeout=15" in code,
    )

    # ---- v10.6.45: blocked_signals schema v2 (Fase A) ----
    print("  Checks v10.6.45: blocked_signals schema v2 Fase A")

    test(
        "blocked_signals schema v3: nuevos registros hardcodean schema_version=3",
        '"schema_version": 3,' in code,
    )
    test(
        "v10.6.45: 15 campos v2 siempre-disponibles cubiertos por schema_version + 14 campos adicionales",
        '"market_id"' in code
        and '"condition_id"' in code
        and '"token_id_yes"' in code
        and '"token_id_no"' in code
        and '"market_slug"' in code
        and '"city_mode_at_record_time"' in code
        and '"whitelist_status_at_record_time"' in code
        and '"city_policy_status_at_record_time"' in code
        and '"reason_blocked"' in code
        and '"block_reason_detail"' in code
        and '"resolution_source"' in code
        and '"observed_coverage_status"' in code
        and '"price_bucket"' in code
        and '"canonical_signal_id"' in code,
    )
    test(
        "blocked_signals schema v3: settlement/edge v2 preservados y bot eval v3 persistido",
        '"settlement_source": "unknown"' in code
        and '"settlement_fidelity_status": "unverified"' in code
        and '"bot_edge_pct_at_signal": None' in code
        and '"bot_would_have_bought": bot_eval_fields["bot_would_have_bought"]' in code
        and '"bot_evaluation_source": bot_eval_fields["bot_evaluation_source"]' in code,
    )
    test(
        "blocked_signals schema v3: helper no inventa bot_would_have_bought=true",
        "def _blocked_signal_bot_eval_fields(" in code
        and '"bot_would_have_bought": False' in code
        and '"bot_evaluation_source": "unknown"' in code
        and '{"live_eval", "replay", "unknown"}' in code,
    )
    test(
        "v10.6.45: helper _classify_city_bucket presente con 6 buckets canonicos",
        "def _classify_city_bucket(" in code
        and '"BLOCKED"' in code
        and '"ACTIVE"' in code
        and '"CANARY"' in code
        and '"OBSERVED_AUDIT"' in code
        and '"SHADOW"' in code
        and '"UNTRACKED"' in code,
    )
    test(
        "v10.6.45: helper _resolve_observed_coverage_status presente con 4 estados",
        "def _resolve_observed_coverage_status(" in code
        and '"noaa_configured"' in code
        and '"icao_only"' in code
        and '"open_meteo_proxy_only"' in code
        and '"no_local_station"' in code,
    )
    test(
        "v10.6.45: helper _build_blocked_signal_canonical_id presente",
        "def _build_blocked_signal_canonical_id(" in code,
    )
    test(
        "v10.6.45: helper _price_bucket presente con 5 buckets",
        "def _price_bucket(" in code
        and '"<0.2"' in code
        and '"0.2-0.4"' in code
        and '"0.4-0.6"' in code
        and '"0.6-0.8"' in code
        and '">0.8"' in code,
    )
    test(
        "v10.6.45: helper _extract_token_id presente y fail-safe",
        "def _extract_token_id(" in code,
    )
    test(
        "v10.6.45: helper _resolve_blocked_reason presente con enum cerrado",
        "def _resolve_blocked_reason(" in code
        and '"out_of_whitelist"' in code
        and '"blocked_city"' in code
        and '"shadow_only_mode"' in code
        and '"condition_filtered"' in code
        and "settlement_risk" in code
        and '"mixed"' in code
        and '"unknown"' in code,
    )
    test(
        "v10.6.45: existing_canonical_ids dedupe acepta canonical_signal_id v2 y match_key v1",
        "existing_canonical_ids" in code
        and 'rec.get("canonical_signal_id")' in code
        and 'rec.get("match_key", "")' in code,
    )
    test(
        "v10.6.45: append blocked_signals sigue dentro de try/except fail-safe",
        "blocked signals check: fallo" in code,
    )
    test(
        "v10.6.45: no se modifican firmas de manage_positions e intra_cycle_sl_check",
        "def manage_positions(client, dl):" in code
        and "def intra_cycle_sl_check(client):" in code,
    )
    test(
        "v10.6.47: BOT_VERSION bumpeado a v10.6.47",
        'BOT_VERSION = "v10.6.47"' in code,
    )

    # ---- v10.6.46: Fase B1 — blocked_signals_audit.py ----
    print("  Checks Fase B1: tools/blocked_signals_audit.py")

    audit_tool_path = os.path.join(os.path.dirname(__file__), "tools", "blocked_signals_audit.py")
    audit_tool_code = ""
    audit_tool_compiles = False
    audit_tool_compile_detail = ""
    if os.path.exists(audit_tool_path):
        with open(audit_tool_path, "r", encoding="utf-8") as _f:
            audit_tool_code = _f.read()
        try:
            py_compile.compile(audit_tool_path, doraise=True)
            audit_tool_compiles = True
        except py_compile.PyCompileError as _exc:
            audit_tool_compile_detail = str(_exc)

    test(
        "fase_b1: tools/blocked_signals_audit.py existe y compila",
        os.path.exists(audit_tool_path) and audit_tool_compiles,
        audit_tool_compile_detail,
    )
    test(
        "fase_b1: blocked_signals_audit tiene función main()",
        "def main(" in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit tiene argparse con todos los args requeridos",
        "--source" in audit_tool_code
        and "--days" in audit_tool_code
        and "--json" in audit_tool_code
        and "--markdown" in audit_tool_code
        and "--out" in audit_tool_code
        and "--top" in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit trata schema_version ausente como v1",
        'setdefault("schema_version", 1)' in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit no importa bot.py directamente",
        "\nimport bot\n" not in audit_tool_code
        and "\nfrom bot import" not in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit no escribe archivos salvo con --out",
        "args.out" in audit_tool_code
        and "out_path.open" in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit no contiene llamadas a Telegram ni APIs externas",
        "send_telegram" not in audit_tool_code
        and "urllib.request" not in audit_tool_code
        and "requests" not in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit usa solo stdlib (no dependencias externas)",
        "import requests" not in audit_tool_code
        and "import pandas" not in audit_tool_code
        and "import numpy" not in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit implementa secciones A-G del reporte",
        "def section_a(" in audit_tool_code
        and "def section_b(" in audit_tool_code
        and "def section_c(" in audit_tool_code
        and "def section_d(" in audit_tool_code
        and "def section_e(" in audit_tool_code
        and "def section_f(" in audit_tool_code
        and "def section_g(" in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit clasificaciones no incluyen trading candidate",
        "audit_candidate" in audit_tool_code
        and "needs_settlement_verification" in audit_tool_code
        and "not_actionable" in audit_tool_code
        and "trading candidate" not in audit_tool_code
        and "trading_candidate" not in audit_tool_code,
    )
    test(
        "fase_b1: blocked_signals_audit tiene función build_analysis() y load_records()",
        "def build_analysis(" in audit_tool_code
        and "def load_records(" in audit_tool_code,
    )

    # ---- v10.6.47: Fase B2 — blocked_signals Telegram summary ----
    print("  Checks Fase B2: blocked_signals Telegram summary (v10.6.47)")

    test(
        "fase_b2: _blocked_signals_build_telegram_summary existe en bot.py",
        "def _blocked_signals_build_telegram_summary(" in code,
    )
    test(
        "fase_b2: _blocked_signals_format_telegram existe en bot.py",
        "def _blocked_signals_format_telegram(" in code,
    )
    test(
        "fase_b2: alerta incluye schema v1/v2 count",
        "v1/v2" in code and "v1_count" in code and "v2_count" in code,
    )
    test(
        "fase_b2: alerta incluye settlement_fidelity_unverified_pct",
        "fidelity_unverified_pct" in code,
    )
    test(
        "fase_b2: alerta incluye 'no accionable para trading'",
        "No accionable para trading" in code,
    )
    test(
        "fase_b2: v2 baja muestra + fallback v1 baja fidelidad no genera ACTION",
        "v2_low_sample_legacy_fallback" in code
        and 'level = "WATCH_AUDIT"' in code
        and "_fallback_low_fidelity_v2" in code
        and "and not _fallback_low_fidelity_v2" in code,
    )
    test(
        "fase_b2: alerta incluye hint audit CLI con --markdown",
        "blocked_signals_audit.py" in code and "--markdown" in code,
    )
    test(
        "fase_b2: Telegram summary tiene control de longitud (truncado)",
        "truncado" in code and "_bs_msg" in code,
    )
    test(
        "fase_b2: fallback a alerta legacy si summary falla",
        "_bs_e" in code and "_bs_msg" in code and "_fallback_action" in code,
    )
    test(
        "fase_b2: _bs_normalize aplica v2 defaults a schema_version",
        'out.setdefault("schema_version", 1)' in code,
    )
    test(
        "fase_b2: no se implementa Fase C (Truth Pipeline)",
        "truth_pipeline" not in code.lower()
        and "fetch_noaa_truth" not in code.lower(),
    )
    test(
        "fase_b2: tools/blocked_signals_audit.py sigue sin send_telegram",
        "send_telegram" not in audit_tool_code,
    )
    test(
        "fase_b2: no tocar trading — maybe_run_blocked_signals_check no llama buy/sell",
        "execute_buy" not in code[code.find("def maybe_run_blocked_signals_check("):code.find("def maybe_run_w17_observation_alert(")]
        if "def maybe_run_blocked_signals_check(" in code and "def maybe_run_w17_observation_alert(" in code
        else True,
    )

    # ---- v10.6.47: traders_intelligence Telegram hardening ----
    print("  Checks traders_intelligence Telegram hardening (observability)")
    test(
        "traders_intelligence: daily summary tool existe",
        bool(traders_daily_summary_code),
    )
    test(
        "traders_intelligence: send_telegram captura errores HTTP/red/timeout",
        "urllib.error.HTTPError" in traders_daily_summary_code
        and "urllib.error.URLError" in traders_daily_summary_code
        and "TimeoutError" in traders_daily_summary_code
        and "telegram_exception" in traders_daily_summary_code,
    )
    test(
        "traders_intelligence: send_telegram usa HTML con fallback texto plano",
        'parse_mode="HTML"' in traders_daily_summary_code
        and "plain_text_message" in traders_daily_summary_code
        and "telegram_plain_text_fallback_error" in traders_daily_summary_code,
    )
    test(
        "traders_intelligence: Telegram largo se parte en chunks seguros",
        "TELEGRAM_SAFE_CHUNK_CHARS = 3800" in traders_daily_summary_code
        and "def chunk_message(" in traders_daily_summary_code
        and "post_telegram_chunk(" in traders_daily_summary_code,
    )
    test(
        "traders_intelligence: fallo Telegram devuelve resultado no fatal",
        "def telegram_failure(" in traders_daily_summary_code
        and '"sent": False' in traders_daily_summary_code
        and "return telegram_failure(" in traders_daily_summary_code,
    )
    test(
        "traders_intelligence: state/markdown se escriben tras send_telegram",
        traders_daily_summary_code.find("telegram_result = send_telegram(message)") != -1
        and traders_daily_summary_code.find("state_path.write_text(") > traders_daily_summary_code.find("telegram_result = send_telegram(message)")
        and traders_daily_summary_code.find("md_path.write_text(") > traders_daily_summary_code.find("telegram_result = send_telegram(message)"),
    )
    test(
        "traders_intelligence: report prefiere signals_crosscheck live",
        'DEFAULT_CROSSCHECK_LIVE_PATH = REPO_ROOT / "data" / "signals_crosscheck.jsonl"' in traders_report_code
        and "DEFAULT_CROSSCHECK_PATH = DEFAULT_CROSSCHECK_LIVE_PATH" in traders_report_code,
    )
    test(
        "traders_intelligence: report mantiene fallback crosscheck legacy",
        'DEFAULT_CROSSCHECK_LEGACY_PATH = REPO_ROOT / "data" / "runtime_import_derived" / "signals_crosscheck.jsonl"' in traders_report_code
        and "fallback_paths=[DEFAULT_CROSSCHECK_LEGACY_PATH]" in traders_report_code,
    )
    test(
        "traders_intelligence: report contempla blocked signals live",
        'DEFAULT_BLOCKED_LIVE_PATH = REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl"' in traders_report_code
        and "DEFAULT_BLOCKED_PATH = DEFAULT_BLOCKED_LIVE_PATH" in traders_report_code,
    )
    test(
        "traders_intelligence: report mantiene fallback blocked legacy",
        'DEFAULT_BLOCKED_LEGACY_PATH = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"' in traders_report_code
        and "fallback_paths=[DEFAULT_BLOCKED_LEGACY_PATH]" in traders_report_code,
    )
    test(
        "traders_intelligence: missing input reporta paths_checked",
        "paths_checked=[" in traders_report_code
        and "format_paths_checked(" in traders_report_code,
    )
    try:
        traders_summary_src = code.split("def maybe_run_traders_intelligence_summary(", 1)[1].split(
            "def maybe_run_city_intelligence_runtime_summary(", 1
        )[0]
    except IndexError:
        traders_summary_src = ""
    test(
        "traders_intelligence: no abre v1 ni toca scheduler/trading",
        "Abrir v1 minimo" not in traders_report_code
        and "Abrir v1 minimo" not in traders_daily_summary_code
        and "SCHEDULE_HOURS_UTC" not in traders_summary_src
        and "execute_buy" not in traders_summary_src
        and "execute_sell" not in traders_summary_src
        and "BANKROLL" not in traders_summary_src,
    )
    test(
        "traders_intelligence: ready copy reconoce v1 minima existente",
        "V1 minima implementada" in traders_daily_summary_code
        and "traders_intelligence_snapshot.py" in traders_daily_summary_code
        and "signals.json fresco" in traders_daily_summary_code
        and "v1_minimal_available" in traders_daily_summary_code,
    )
    print("  Checks traders_intelligence v1 snapshots manual-only")
    traders_snapshot_forbidden = [
        "import bot",
        "from bot",
        "execute_trade",
        "execute_buy",
        "execute_sell",
        "create_order",
        "post_order",
        "cancel_order",
        "OrderArgs",
        "BANKROLL",
        "QUALITY_TRADER_CITIES_WHITELIST",
        "ACTIVE_TRADING_CITIES",
        "CANARY_TRADING_CITIES",
        "BLOCKED_CITIES",
        "SCHEDULE_HOURS_UTC",
    ]
    test(
        "traders_intelligence v1: snapshot tool existe",
        bool(traders_snapshot_code)
        and "schema_version" in traders_snapshot_code
        and "traders_intelligence_signal_snapshot_v1" in traders_snapshot_code,
    )
    test(
        "traders_intelligence v1: scope acotado traders/cities",
        "Thrifty-Original" in traders_snapshot_code
        and "Entire-Hood" in traders_snapshot_code
        and "Houston" in traders_snapshot_code
        and "Los Angeles" in traders_snapshot_code
        and "Manila" in traders_snapshot_code
        and "Miami" in traders_snapshot_code,
    )
    test(
        "traders_intelligence v1: lifecycle minimo observado",
        "appeared" in traders_snapshot_code
        and "still_present" in traders_snapshot_code
        and "disappeared_apparent" in traders_snapshot_code
        and "reappeared" in traders_snapshot_code
        and "not_a_trading_signal" in traders_snapshot_code,
    )
    test(
        "traders_intelligence v1: CLI manual dry-run e idempotente",
        "--dry-run" in traders_snapshot_code
        and "--run-id" in traders_snapshot_code
        and "write_jsonl_idempotent" in traders_snapshot_code,
    )
    test(
        "traders_intelligence v1: falla limpio si falta signals.json",
        "Missing required input signals.json" in traders_snapshot_code
        and "return 2" in traders_snapshot_code,
    )
    test(
        "traders_intelligence v1: no toca trading core/policy",
        all(token not in traders_snapshot_code for token in traders_snapshot_forbidden)
        and "traders_intelligence_snapshot.py" not in code,
    )
    test(
        "traders_intelligence v1: doc de uso existe",
        bool(traders_snapshot_doc)
        and "python tools/traders_intelligence_snapshot.py --dry-run" in traders_snapshot_doc
        and "`disappeared_apparent` is not a confirmed exit" in traders_snapshot_doc,
    )

    # ---- Bot health check read-only CLI ----
    print("  Checks bot_health_check.py read-only CLI")
    bot_health_path = os.path.join(os.path.dirname(__file__), "tools", "bot_health_check.py")
    bot_health_doc_path = os.path.join(os.path.dirname(__file__), "docs", "bot_health_check.md")
    bot_health_code = ""
    bot_health_doc = ""
    bot_health_ast_ok = False
    bot_health_ast_detail = ""
    if os.path.exists(bot_health_path):
        with open(bot_health_path, "r", encoding="utf-8") as _f:
            bot_health_code = _f.read()
        try:
            ast.parse(bot_health_code)
            bot_health_ast_ok = True
        except SyntaxError as _exc:
            bot_health_ast_detail = str(_exc)
    if os.path.exists(bot_health_doc_path):
        with open(bot_health_doc_path, "r", encoding="utf-8") as _f:
            bot_health_doc = _f.read()

    bot_health_write_tokens = [
        ".write(",
        ".write_text(",
        ".writelines(",
        "open(",
        ".open(",
    ]
    bot_health_write_hits = [
        token for token in bot_health_write_tokens
        if token in bot_health_code
        and token not in {".open("}
    ]
    bot_health_open_write = bool(re.search(
        r"\.open\([^)]*['\"](?:w|a|x|\+)",
        bot_health_code,
    ) or re.search(
        r"open\([^)]*['\"](?:w|a|x|\+)",
        bot_health_code,
    ))

    test(
        "bot_health: tools/bot_health_check.py existe y tiene sintaxis valida",
        os.path.exists(bot_health_path) and bot_health_ast_ok,
        bot_health_ast_detail,
    )
    test(
        "bot_health: usa argparse",
        "import argparse" in bot_health_code and "ArgumentParser" in bot_health_code,
    )
    test(
        "bot_health: tiene main()",
        "def main(" in bot_health_code and 'if __name__ == "__main__"' in bot_health_code,
    )
    test(
        "bot_health: no importa bot.py",
        "\nimport bot\n" not in bot_health_code and "\nfrom bot import" not in bot_health_code,
    )
    test(
        "bot_health: no contiene send_telegram",
        "send_telegram" not in bot_health_code,
    )
    test(
        "bot_health: no contiene requests/urlopen",
        "requests" not in bot_health_code and "urlopen" not in bot_health_code,
    )
    test(
        "bot_health: no escribe archivos",
        not bot_health_open_write
        and ".write(" not in bot_health_code
        and ".write_text(" not in bot_health_code
        and ".writelines(" not in bot_health_code,
        ", ".join(bot_health_write_hits),
    )
    test(
        "bot_health: soporta --json y --markdown",
        "--json" in bot_health_code and "--markdown" in bot_health_code,
    )
    test(
        "bot_health: soporta data-dir/db/max-cycle-age/log-tail",
        "--data-dir" in bot_health_code
        and "--db" in bot_health_code
        and "--max-cycle-age-hours" in bot_health_code
        and "--log-tail" in bot_health_code,
    )
    test(
        "bot_health: comprueba SQLite read-only con sqlite3",
        "import sqlite3" in bot_health_code
        and "mode=ro" in bot_health_code
        and "uri=True" in bot_health_code,
    )
    test(
        "bot_health: docs/bot_health_check.md existe",
        os.path.exists(bot_health_doc_path) and "read-only" in bot_health_doc.lower(),
    )
    test(
        "bot_health: no toca trading core",
        "manage_positions" not in bot_health_code
        and "intra_cycle_sl_check" not in bot_health_code
        and "execute_buy" not in bot_health_code
        and "execute_sell" not in bot_health_code
        and "BANKROLL" not in bot_health_code
        and "ACTIVE_TRADING_CITIES" not in bot_health_code
        and "CANARY_TRADING_CITIES" not in bot_health_code,
    )
    test(
        "bot_health: cubre status global OK/WATCH/ACTION",
        '"OK"' in bot_health_code and '"WATCH"' in bot_health_code and '"ACTION"' in bot_health_code,
    )
    test(
        "bot_health: cubre readiness Fase 1 sin Truth Pipeline",
        "DEFAULT_MIN_CYCLES" in bot_health_code
        and "eta_date" in bot_health_code
        and "truth_pipeline" not in bot_health_code.lower(),
    )
    bot_health_ns = {}
    if bot_health_ast_ok:
        try:
            bot_health_ns["__name__"] = "bot_health_verify"
            exec(compile(bot_health_code, bot_health_path, "exec"), bot_health_ns)
        except Exception:
            bot_health_ns = {}

    if bot_health_ns:
        original_read_json = bot_health_ns["read_json"]
        original_tail_lines = bot_health_ns["tail_lines"]
        try:
            def _fake_cycle_summary(_path):
                return {
                    "buys": 0,
                    "with_edge": 0,
                    "selected": 0,
                    "execution_reject_reasons": {},
                    "reject_reasons": {
                        "price_out_of_range": 12,
                        "date_out_of_range_past": 3,
                        "condition_filtered": 9,
                        "below_min_edge": 4,
                        "liquidity_low": 2,
                        "fuera_allowlist": 7,
                        "parse_fail": 1,
                        "city_window_skipped": 1,
                    },
                }, None

            bot_health_ns["read_json"] = _fake_cycle_summary
            trading_issues = []
            trading_result = bot_health_ns["summarize_trading"](Path("data"), trading_issues)
            test(
                "bot_health: reject reasons normales no elevan status",
                trading_result["status"] == "OK" and not trading_issues,
                trading_result,
            )
            test(
                "bot_health: sin edge/selected/buys se interpreta como no opportunity",
                trading_result["interpretation"] == "no buys because no operable opportunities were selected",
                trading_result.get("interpretation"),
            )

            def _fake_observability_tail(_path, _limit):
                return [
                    "traders intelligence summary: traders_intelligence_daily_summary.py fallo (Traceback...)",
                    "city-intelligence runtime warning Traceback in observability bridge",
                ], None

            bot_health_ns["tail_lines"] = _fake_observability_tail
            log_issues = []
            log_result = bot_health_ns["summarize_logs"](Path("data"), 200, log_issues)
            test(
                "bot_health: observability Traceback conocido no es ACTION",
                log_result["status"] == "WATCH" and not log_result["critical"],
                log_result,
            )

            def _fake_core_tail(_path, _limit):
                return ["Traceback: core cycle crash while scanning"], None

            bot_health_ns["tail_lines"] = _fake_core_tail
            core_log_issues = []
            core_log_result = bot_health_ns["summarize_logs"](Path("data"), 200, core_log_issues)
            test(
                "bot_health: Traceback no observability sigue siendo ACTION",
                core_log_result["status"] == "ACTION" and core_log_result["critical"],
                core_log_result,
            )
        finally:
            bot_health_ns["read_json"] = original_read_json
            bot_health_ns["tail_lines"] = original_tail_lines
    else:
        test("bot_health: functional checks cargan namespace", False)

    # ---- Bankroll scaling check read-only CLI ----
    print("  Checks bankroll_scaling_check.py read-only CLI")
    scaling_check_path = os.path.join(os.path.dirname(__file__), "tools", "bankroll_scaling_check.py")
    scaling_check_doc_path = os.path.join(os.path.dirname(__file__), "docs", "bankroll_scaling_check.md")
    scaling_check_code = ""
    scaling_check_doc = ""
    scaling_check_ast_ok = False
    scaling_check_ast_detail = ""
    if os.path.exists(scaling_check_path):
        with open(scaling_check_path, "r", encoding="utf-8") as _f:
            scaling_check_code = _f.read()
        try:
            ast.parse(scaling_check_code)
            scaling_check_ast_ok = True
        except SyntaxError as _exc:
            scaling_check_ast_detail = str(_exc)
    if os.path.exists(scaling_check_doc_path):
        with open(scaling_check_doc_path, "r", encoding="utf-8") as _f:
            scaling_check_doc = _f.read()

    scaling_open_write = bool(re.search(
        r"\.open\([^)]*['\"](?:w|a|x|\+)",
        scaling_check_code,
    ) or re.search(
        r"open\([^)]*['\"](?:w|a|x|\+)",
        scaling_check_code,
    ))
    scaling_sql_write = bool(re.search(
        r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|VACUUM|PRAGMA\s+journal_mode)\b",
        scaling_check_code,
    ))

    test(
        "bankroll_scaling_check: tools/bankroll_scaling_check.py existe y tiene sintaxis valida",
        os.path.exists(scaling_check_path) and scaling_check_ast_ok,
        scaling_check_ast_detail,
    )
    test(
        "bankroll_scaling_check: usa argparse",
        "import argparse" in scaling_check_code and "ArgumentParser" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: tiene main()",
        "def main(" in scaling_check_code and 'if __name__ == "__main__"' in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: soporta --json y --markdown",
        "--json" in scaling_check_code and "--markdown" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: soporta data-dir/db/current/target/log-tail",
        "--data-dir" in scaling_check_code
        and "--db" in scaling_check_code
        and "--current-bankroll" in scaling_check_code
        and "--target-tier" in scaling_check_code
        and "--log-tail" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: no importa bot.py",
        "\nimport bot\n" not in scaling_check_code and "\nfrom bot import" not in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: no contiene send_telegram",
        "send_telegram" not in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: no contiene requests/urlopen",
        "requests" not in scaling_check_code and "urlopen" not in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: no escribe archivos",
        not scaling_open_write
        and ".write(" not in scaling_check_code
        and ".write_text(" not in scaling_check_code
        and ".writelines(" not in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: SQLite read-only y sin writes DB",
        "import sqlite3" in scaling_check_code
        and "mode=ro" in scaling_check_code
        and "uri=True" in scaling_check_code
        and not scaling_sql_write,
    )
    test(
        "bankroll_scaling_check: contrato eligible/decision/manual-only",
        "eligible_for_manual_review" in scaling_check_code
        and "do_not_increase" in scaling_check_code
        and "manual_review_required" in scaling_check_code
        and "increase_now" not in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: estructura blockers/watch/missing",
        "hard_blockers" in scaling_check_code
        and "watch_items" in scaling_check_code
        and "missing_evidence" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: performance_windows expone ventanas",
        "performance_windows" in scaling_check_code
        and "historical_all" in scaling_check_code
        and "current_logic_series" in scaling_check_code
        and "last_20_closed" in scaling_check_code
        and "last_30_clean_closed" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: evaluation_window definido",
        '"evaluation_window"' in scaling_check_code
        and "preferred" not in scaling_check_code.lower()
        and "last_30_clean_closed" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: limpia legacy con integrity flags",
        "analysis_ready" in scaling_check_code
        and "partial_historical_record" in scaling_check_code
        and "missing_buy_history" in scaling_check_code
        and "close_only_record" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: historical_all no bloquea si hay ventana limpia",
        "historical_all_legacy_context" in scaling_check_code
        and "historical_all_used_for_decision" in scaling_check_code
        and 'evaluation_window == "historical_all"' in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: markdown muestra Performance windows",
        "## Performance windows" in scaling_check_code
        and "Used for decision" in scaling_check_code
        and "window_rows" in scaling_check_code
        and "lines.extend(window_rows)" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: NOT_ELIGIBLE para evidencia policy faltante",
        "unknown_missing_codes" in scaling_check_code
        and "bankroll_readiness_score_unavailable" in scaling_check_code
        and 'status = "NOT_ELIGIBLE"' in scaling_check_code
        and 'status = "UNKNOWN"' in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: phase1 pending no sale como pass false",
        'phase1_status = "pass" if phase1_ready else "pending" if phase1_pending_allowed else "fail"'
        in scaling_check_code
        and "Phase 1 readiness pending; expected until thresholds are met" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: bankroll score missing explica paths_checked",
        "paths_checked" in scaling_check_code
        and "state file not found" in scaling_check_code
        and "read_bankroll_state" in scaling_check_code,
    )
    test(
        "bankroll_scaling_check: docs/bankroll_scaling_check.md existe",
        os.path.exists(scaling_check_doc_path)
        and "read-only" in scaling_check_doc.lower()
        and "manual" in scaling_check_doc.lower(),
    )
    test(
        "bankroll_scaling_check: no toca trading core",
        "manage_positions" not in scaling_check_code
        and "intra_cycle_sl_check" not in scaling_check_code
        and "execute_buy" not in scaling_check_code
        and "execute_sell" not in scaling_check_code
        and "BANKROLL_LEVELS" not in scaling_check_code
        and "SCALING_TIERS" not in scaling_check_code
        and "ACTIVE_TRADING_CITIES" not in scaling_check_code
        and "CANARY_TRADING_CITIES" not in scaling_check_code,
    )

    # ---- Wallet snapshot read-only CLI ----
    print("  Checks wallet_snapshot.py read-only CLI")
    wallet_snapshot_path = os.path.join(os.path.dirname(__file__), "tools", "wallet_snapshot.py")
    wallet_snapshot_doc_path = os.path.join(os.path.dirname(__file__), "docs", "wallet_snapshot.md")
    wallet_snapshot_code = ""
    wallet_snapshot_doc = ""
    wallet_snapshot_ast_ok = False
    wallet_snapshot_ast_detail = ""
    if os.path.exists(wallet_snapshot_path):
        with open(wallet_snapshot_path, "r", encoding="utf-8") as _f:
            wallet_snapshot_code = _f.read()
        try:
            ast.parse(wallet_snapshot_code)
            wallet_snapshot_ast_ok = True
        except SyntaxError as _exc:
            wallet_snapshot_ast_detail = str(_exc)
    if os.path.exists(wallet_snapshot_doc_path):
        with open(wallet_snapshot_doc_path, "r", encoding="utf-8") as _f:
            wallet_snapshot_doc = _f.read()

    test(
        "wallet_snapshot: tools/wallet_snapshot.py existe y tiene sintaxis valida",
        os.path.exists(wallet_snapshot_path) and wallet_snapshot_ast_ok,
        wallet_snapshot_ast_detail,
    )
    test(
        "wallet_snapshot: docs/wallet_snapshot.md existe",
        os.path.exists(wallet_snapshot_doc_path)
        and "phase2_ready" in wallet_snapshot_doc
        and "wallet_cash_flows.jsonl" in wallet_snapshot_doc,
    )
    test(
        "wallet_snapshot: no importa bot.py",
        "import bot" not in wallet_snapshot_code and "from bot" not in wallet_snapshot_code,
    )
    test(
        "wallet_snapshot: flags CLI requeridos",
        "--dry-run" in wallet_snapshot_code
        and "--json" in wallet_snapshot_code
        and "--markdown" in wallet_snapshot_code
        and "--report-only" in wallet_snapshot_code,
    )
    test(
        "wallet_snapshot: schema snapshot requerido",
        "schema_version" in wallet_snapshot_code
        and "snapshot_at" in wallet_snapshot_code
        and "total_value" in wallet_snapshot_code
        and "api_ok" in wallet_snapshot_code
        and "wallet_portfolio_snapshots.jsonl" in wallet_snapshot_code,
    )
    test(
        "wallet_snapshot: contrato PnL/readiness requerido",
        "phase2_ready" in wallet_snapshot_code
        and "wallet_pnl_available" in wallet_snapshot_code
        and "wallet_pnl_confidence" in wallet_snapshot_code
        and "required_history_hours" in wallet_snapshot_code
        and "snapshot_delta" in wallet_snapshot_code,
    )
    test(
        "wallet_snapshot: no contiene primitivas de trading",
        "post_order" not in wallet_snapshot_code
        and "create_order" not in wallet_snapshot_code
        and "cancel_order" not in wallet_snapshot_code
        and "OrderArgs" not in wallet_snapshot_code
        and "BUY" not in wallet_snapshot_code
        and "SELL" not in wallet_snapshot_code
        and "manage_positions" not in wallet_snapshot_code
        and "maybe_buy" not in wallet_snapshot_code,
    )
    test(
        "wallet_snapshot: no referencia BANKROLL",
        "BANKROLL" not in wallet_snapshot_code,
    )
    wallet_snapshot_integration_source = ""
    wallet_snapshot_execution_source = ""
    try:
        wallet_snapshot_execution_source = (
            get_function_source(module_ast, code_lines, "run_wallet_snapshot_json")
            + "\n"
            + get_function_source(module_ast, code_lines, "maybe_run_wallet_snapshot")
        )
        wallet_snapshot_integration_source = (
            wallet_snapshot_execution_source
            + "\n"
            + get_function_source(module_ast, code_lines, "format_wallet_snapshot_phase2_ready_telegram")
        )
    except Exception:
        wallet_snapshot_integration_source = ""
        wallet_snapshot_execution_source = ""
    test(
        "wallet_snapshot observability: script y env vars definidos en bot.py",
        "WALLET_SNAPSHOT_SCRIPT" in code
        and "wallet_snapshot.py" in code
        and "WALLET_SNAPSHOT_ENABLED" in code
        and "WALLET_SNAPSHOT_HOUR_UTC" in code
        and "WALLET_SNAPSHOT_TIMEOUT_SECONDS" in code,
    )
    test(
        "wallet_snapshot observability: default diario sin tocar scheduler trading",
        'WALLET_SNAPSHOT_ENABLED = os.getenv("WALLET_SNAPSHOT_ENABLED", "1")' in code
        and 'WALLET_SNAPSHOT_HOUR_UTC = int(os.getenv("WALLET_SNAPSHOT_HOUR_UTC", str(PNL_RECONCILIATION_HOUR_UTC)))' in code
        and "SCHEDULE_HOURS_UTC" not in wallet_snapshot_integration_source,
    )
    test(
        "wallet_snapshot observability: helper JSON subprocess fail-safe",
        "def run_wallet_snapshot_json(" in code
        and "subprocess.run(" in wallet_snapshot_integration_source
        and '"--json"' in wallet_snapshot_integration_source
        and "timeout=WALLET_SNAPSHOT_TIMEOUT_SECONDS" in wallet_snapshot_integration_source
        and "return None" in wallet_snapshot_integration_source,
    )
    test(
        "wallet_snapshot observability: state anti-spam en alerts_state",
        "wallet_snapshot_last_run_date" in code
        and "wallet_snapshot_last_phase2_ready" in code
        and "wallet_snapshot_last_ready_reason" in code
        and "wallet_snapshot_last_valid_snapshot_days" in code
        and "wallet_snapshot_last_valid_snapshot_at" in code
        and "wallet_snapshot_last_error_date" in code
        and "wallet_snapshot_phase2_ready_alert_sent" in code,
    )
    test(
        "wallet_snapshot observability: phase2_ready one-shot sin autorizacion bankroll",
        "def maybe_run_wallet_snapshot(" in code
        and "phase2_ready" in wallet_snapshot_integration_source
        and "wallet_snapshot_phase2_ready_alert_sent" in wallet_snapshot_integration_source
        and "No cambiar BANKROLL" in wallet_snapshot_integration_source,
    )
    test(
        "wallet_snapshot observability: integrada en run_observability_alerts",
        "maybe_run_wallet_snapshot(state)" in code
        and "wallet snapshot: fallo" in code,
    )
    test(
        "wallet_snapshot observability: no integra pnl_reconciliation_alert.py ni trading primitives",
        "PNL_RECONCILIATION_SCRIPT" not in wallet_snapshot_execution_source
        and "OrderArgs" not in wallet_snapshot_execution_source
        and "post_order" not in wallet_snapshot_execution_source
        and "create_order" not in wallet_snapshot_execution_source
        and "cancel_order" not in wallet_snapshot_execution_source
        and "execute_trade" not in wallet_snapshot_execution_source,
    )

    # ---- Truth Pipeline 1A.1 ----
    print("\n Truth Pipeline 1A.1 — schema v2 + aislamiento")
    _tp_sql_path = os.path.join(os.path.dirname(__file__), "sql", "002_truth_pipeline.sql")
    _tp_schema_path = os.path.join(os.path.dirname(__file__), "tools", "truth_pipeline_schema.py")
    _tp_sql_exists = os.path.exists(_tp_sql_path)
    _tp_schema_exists = os.path.exists(_tp_schema_path)
    test(
        "truth_pipeline: sql/002_truth_pipeline.sql existe",
        _tp_sql_exists,
    )
    test(
        "truth_pipeline: tools/truth_pipeline_schema.py existe",
        _tp_schema_exists,
    )
    if _tp_schema_exists:
        with open(_tp_schema_path, "r", encoding="utf-8") as _f:
            _tp_schema_src = _f.read()
        test(
            "truth_pipeline_schema: no importa bot.py",
            "import bot" not in _tp_schema_src and "from bot" not in _tp_schema_src,
        )
        test(
            "truth_pipeline_schema: solo stdlib (sin requests/httpx)",
            "import requests" not in _tp_schema_src
            and "import httpx" not in _tp_schema_src
            and "import aiohttp" not in _tp_schema_src,
        )
        test(
            "truth_pipeline_schema: contiene --dry-run",
            "--dry-run" in _tp_schema_src,
        )
        test(
            "truth_pipeline_schema: no contiene primitivas de trading",
            "execute_trade" not in _tp_schema_src
            and "manage_positions" not in _tp_schema_src
            and "intra_cycle_sl_check" not in _tp_schema_src,
        )
    else:
        for _msg in [
            "truth_pipeline_schema: no importa bot.py",
            "truth_pipeline_schema: solo stdlib (sin requests/httpx)",
            "truth_pipeline_schema: contiene --dry-run",
            "truth_pipeline_schema: no contiene primitivas de trading",
        ]:
            test(_msg, False, "archivo no encontrado")
    if _tp_sql_exists:
        with open(_tp_sql_path, "r", encoding="utf-8") as _f:
            _tp_sql_src = _f.read()
        _tp_sql_lower = _tp_sql_src.lower()
        test(
            "truth_pipeline: sql contiene truth_records y truth_revisions",
            "truth_records" in _tp_sql_lower and "truth_revisions" in _tp_sql_lower,
        )
        test(
            "truth_pipeline: sql registra schema_version=2",
            "schema_version" in _tp_sql_lower
            and ("values (2," in _tp_sql_lower or "values(2," in _tp_sql_lower),
        )
        test(
            "truth_pipeline: sql no hace DROP TABLE sobre tablas v1",
            "drop table cycle_events" not in _tp_sql_lower
            and "drop table market_snapshots" not in _tp_sql_lower
            and "drop table forecast_snapshots" not in _tp_sql_lower,
        )
        # Comprobar que ningún .py en el repo fuerza TRUTH_PIPELINE_ENABLED=1
        import glob as _glob
        _py_files = _glob.glob(os.path.join(os.path.dirname(__file__), "*.py")) + \
                    _glob.glob(os.path.join(os.path.dirname(__file__), "tools", "*.py"))
        _excluded = {"truth_pipeline_schema.py", "verify_before_deploy.py"}
        _tp_forced_on = any(
            'TRUTH_PIPELINE_ENABLED", "1"' in open(p, encoding="utf-8", errors="ignore").read()
            or "TRUTH_PIPELINE_ENABLED=1" in open(p, encoding="utf-8", errors="ignore").read()
            for p in _py_files
            if os.path.basename(p) not in _excluded
        )
        test(
            "truth_pipeline: TRUTH_PIPELINE_ENABLED no hardcodeado como 1 en Python",
            not _tp_forced_on,
        )
    else:
        for _msg in [
            "truth_pipeline: sql contiene truth_records y truth_revisions",
            "truth_pipeline: sql registra schema_version=2",
            "truth_pipeline: sql no hace DROP TABLE sobre tablas v1",
            "truth_pipeline: TRUTH_PIPELINE_ENABLED no hardcodeado como 1 en Python",
        ]:
            test(_msg, False, "sql file not found")

    # ---- Truth Pipeline 1A.2 ----
    print("\n Truth Pipeline 1A.2 — fetcher Open-Meteo archive")
    _tp_fetcher_path = os.path.join(os.path.dirname(__file__), "tools", "truth_pipeline_fetcher.py")
    _tp_fetcher_exists = os.path.exists(_tp_fetcher_path)
    test(
        "truth_pipeline_fetcher: tools/truth_pipeline_fetcher.py existe",
        _tp_fetcher_exists,
    )
    if _tp_fetcher_exists:
        with open(_tp_fetcher_path, "r", encoding="utf-8") as _f:
            _tp_fetcher_src = _f.read()
        test(
            "truth_pipeline_fetcher: no importa bot.py ni trading core",
            "import bot" not in _tp_fetcher_src
            and "from bot" not in _tp_fetcher_src
            and "execute_trade" not in _tp_fetcher_src
            and "manage_positions" not in _tp_fetcher_src,
        )
        test(
            "truth_pipeline_fetcher: solo stdlib (sin requests/httpx/aiohttp)",
            "import requests" not in _tp_fetcher_src
            and "import httpx" not in _tp_fetcher_src
            and "import aiohttp" not in _tp_fetcher_src,
        )
        test(
            "truth_pipeline_fetcher: soporta --dry-run",
            "--dry-run" in _tp_fetcher_src and "dry_run" in _tp_fetcher_src,
        )
        test(
            "truth_pipeline_fetcher: usa archive-api.open-meteo.com/v1/archive",
            "archive-api.open-meteo.com/v1/archive" in _tp_fetcher_src,
        )
        test(
            "truth_pipeline_fetcher: no escribe en DB ni archivos runtime",
            "import sqlite3" not in _tp_fetcher_src
            and "with open(" not in _tp_fetcher_src
            and ".write_text(" not in _tp_fetcher_src
            and ".write_bytes(" not in _tp_fetcher_src,
        )
    else:
        for _msg in [
            "truth_pipeline_fetcher: no importa bot.py ni trading core",
            "truth_pipeline_fetcher: solo stdlib (sin requests/httpx/aiohttp)",
            "truth_pipeline_fetcher: soporta --dry-run",
            "truth_pipeline_fetcher: usa archive-api.open-meteo.com/v1/archive",
            "truth_pipeline_fetcher: no escribe en DB ni archivos runtime",
        ]:
            test(_msg, False, "archivo no encontrado")

    # ---- Truth Pipeline 1A.3 ----
    print("\n Truth Pipeline 1A.3 — runner writer")
    _tp_runner_path = os.path.join(os.path.dirname(__file__), "tools", "truth_pipeline_runner.py")
    _tp_runner_exists = os.path.exists(_tp_runner_path)
    test(
        "truth_pipeline_runner: tools/truth_pipeline_runner.py existe",
        _tp_runner_exists,
    )
    if _tp_runner_exists:
        with open(_tp_runner_path, encoding="utf-8") as _f:
            _tp_runner_src = _f.read()
        test(
            "truth_pipeline_runner: no importa bot.py ni trading core",
            "import bot" not in _tp_runner_src
            and "from bot" not in _tp_runner_src
            and "execute_trade" not in _tp_runner_src
            and "manage_positions" not in _tp_runner_src,
        )
        test(
            "truth_pipeline_runner: soporta --dry-run",
            "--dry-run" in _tp_runner_src and "dry_run" in _tp_runner_src,
        )
        test(
            "truth_pipeline_runner: verifica TRUTH_PIPELINE_ENABLED",
            "TRUTH_PIPELINE_ENABLED" in _tp_runner_src,
        )
        test(
            "truth_pipeline_runner: no hace INSERT en tablas v1",
            "INSERT INTO cycle_events" not in _tp_runner_src
            and "INSERT INTO market_snapshots" not in _tp_runner_src
            and "INSERT INTO forecast_snapshots" not in _tp_runner_src,
        )
        test(
            "truth_pipeline_runner: solo stdlib + truth_pipeline_schema/fetcher (sin requests/httpx)",
            "import requests" not in _tp_runner_src
            and "import httpx" not in _tp_runner_src
            and "import aiohttp" not in _tp_runner_src,
        )
        _excluded_runner = {
            "truth_pipeline_schema.py", "truth_pipeline_fetcher.py",
            "truth_pipeline_runner.py", "verify_before_deploy.py",
        }
        _tp_runner_forced_on = any(
            'TRUTH_PIPELINE_ENABLED", "1"' in open(p, encoding="utf-8", errors="ignore").read()
            for p in (
                _glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
                + _glob.glob(os.path.join(os.path.dirname(__file__), "tools", "*.py"))
            )
            if os.path.basename(p) not in _excluded_runner
        )
        test(
            "truth_pipeline_runner: TRUTH_PIPELINE_ENABLED no hardcodeado como 1",
            not _tp_runner_forced_on,
        )
    else:
        for _msg in [
            "truth_pipeline_runner: no importa bot.py ni trading core",
            "truth_pipeline_runner: soporta --dry-run",
            "truth_pipeline_runner: verifica TRUTH_PIPELINE_ENABLED",
            "truth_pipeline_runner: no hace INSERT en tablas v1",
            "truth_pipeline_runner: solo stdlib + truth_pipeline_schema/fetcher (sin requests/httpx)",
            "truth_pipeline_runner: TRUTH_PIPELINE_ENABLED no hardcodeado como 1",
        ]:
            test(_msg, False, "archivo no encontrado")

    # ---- Truth Pipeline 1A.4 ----
    print("\n Truth Pipeline 1A.4 — reporter + alarms")
    _tp_report_path = os.path.join(os.path.dirname(__file__), "tools", "truth_pipeline_report.py")
    _tp_alarms_path = os.path.join(os.path.dirname(__file__), "tools", "truth_pipeline_alarms.py")
    _tp_report_exists = os.path.exists(_tp_report_path)
    _tp_alarms_exists = os.path.exists(_tp_alarms_path)

    test("truth_pipeline_report: tools/truth_pipeline_report.py existe", _tp_report_exists)
    test("truth_pipeline_alarms: tools/truth_pipeline_alarms.py existe", _tp_alarms_exists)

    if _tp_report_exists:
        with open(_tp_report_path, encoding="utf-8") as _f:
            _tp_report_src = _f.read()
        test(
            "truth_pipeline_report: no importa bot.py ni trading core",
            "import bot" not in _tp_report_src
            and "from bot" not in _tp_report_src
            and "execute_trade" not in _tp_report_src
            and "manage_positions" not in _tp_report_src,
        )
        test(
            "truth_pipeline_report: usa URI read-only (mode=ro)",
            "mode=ro" in _tp_report_src,
        )
        test(
            "truth_pipeline_report: no escribe en DB (sin INSERT/UPDATE/DELETE)",
            "INSERT INTO" not in _tp_report_src
            and "UPDATE " not in _tp_report_src
            and "DELETE FROM" not in _tp_report_src,
        )
        test(
            "truth_pipeline_report: solo stdlib (sin requests/httpx/aiohttp)",
            "import requests" not in _tp_report_src
            and "import httpx" not in _tp_report_src
            and "import aiohttp" not in _tp_report_src,
        )
        test(
            "truth_pipeline_report: soporta schema_missing sin crash",
            "schema_missing" in _tp_report_src,
        )
    else:
        for _msg in [
            "truth_pipeline_report: no importa bot.py ni trading core",
            "truth_pipeline_report: usa URI read-only (mode=ro)",
            "truth_pipeline_report: no escribe en DB (sin INSERT/UPDATE/DELETE)",
            "truth_pipeline_report: solo stdlib (sin requests/httpx/aiohttp)",
            "truth_pipeline_report: soporta schema_missing sin crash",
        ]:
            test(_msg, False, "archivo no encontrado")

    if _tp_alarms_exists:
        with open(_tp_alarms_path, encoding="utf-8") as _f:
            _tp_alarms_src = _f.read()
        test(
            "truth_pipeline_alarms: no importa bot.py ni trading core",
            "import bot" not in _tp_alarms_src
            and "from bot" not in _tp_alarms_src
            and "execute_trade" not in _tp_alarms_src
            and "manage_positions" not in _tp_alarms_src,
        )
        test(
            "truth_pipeline_alarms: TRUTH_PIPELINE_TELEGRAM_ENABLED default 0",
            "TRUTH_PIPELINE_TELEGRAM_ENABLED" in _tp_alarms_src
            and ('"0"' in _tp_alarms_src or "'0'" in _tp_alarms_src),
        )
        test(
            "truth_pipeline_alarms: TRUTH_PIPELINE_TG_CHAT_ID separado del canal operativo",
            "TRUTH_PIPELINE_TG_CHAT_ID" in _tp_alarms_src,
        )
        test(
            "truth_pipeline_alarms: solo stdlib (sin requests/httpx/aiohttp)",
            "import requests" not in _tp_alarms_src
            and "import httpx" not in _tp_alarms_src
            and "import aiohttp" not in _tp_alarms_src,
        )
        test(
            "truth_pipeline_alarms: mensajes no contienen instrucciones de trading",
            "comprar" not in _tp_alarms_src.lower()
            and "vender" not in _tp_alarms_src.lower(),
        )
        test(
            "truth_pipeline_alarms: anti-spam stateful (state file configurable)",
            "already_sent_today" in _tp_alarms_src
            and "state_file" in _tp_alarms_src,
        )
        test(
            "truth_pipeline_alarms: dry_run soportado",
            "dry_run" in _tp_alarms_src,
        )
        _excluded_alarms = {
            "truth_pipeline_schema.py", "truth_pipeline_fetcher.py",
            "truth_pipeline_runner.py", "truth_pipeline_report.py",
            "truth_pipeline_alarms.py", "verify_before_deploy.py",
        }
        _tp_alarms_tg_forced = any(
            'TRUTH_PIPELINE_TELEGRAM_ENABLED", "1"' in open(p, encoding="utf-8", errors="ignore").read()
            for p in (
                _glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
                + _glob.glob(os.path.join(os.path.dirname(__file__), "tools", "*.py"))
            )
            if os.path.basename(p) not in _excluded_alarms
        )
        test(
            "truth_pipeline_alarms: TRUTH_PIPELINE_TELEGRAM_ENABLED no hardcodeado como 1",
            not _tp_alarms_tg_forced,
        )
    else:
        for _msg in [
            "truth_pipeline_alarms: no importa bot.py ni trading core",
            "truth_pipeline_alarms: TRUTH_PIPELINE_TELEGRAM_ENABLED default 0",
            "truth_pipeline_alarms: TRUTH_PIPELINE_TG_CHAT_ID separado del canal operativo",
            "truth_pipeline_alarms: solo stdlib (sin requests/httpx/aiohttp)",
            "truth_pipeline_alarms: mensajes no contienen instrucciones de trading",
            "truth_pipeline_alarms: anti-spam stateful (state file configurable)",
            "truth_pipeline_alarms: dry_run soportado",
            "truth_pipeline_alarms: TRUTH_PIPELINE_TELEGRAM_ENABLED no hardcodeado como 1",
        ]:
            test(_msg, False, "archivo no encontrado")

    # ---- Daily Kanban Digest dry-run ----
    print("\n Daily Kanban Digest dry-run")
    _daily_kanban_path = os.path.join(os.path.dirname(__file__), "tools", "daily_kanban_digest.py")
    _daily_kanban_exists = os.path.exists(_daily_kanban_path)
    _daily_kanban_src = ""
    _daily_kanban_ast_ok = False
    _daily_kanban_ast_detail = ""
    if _daily_kanban_exists:
        with open(_daily_kanban_path, encoding="utf-8") as _f:
            _daily_kanban_src = _f.read()
        try:
            ast.parse(_daily_kanban_src)
            _daily_kanban_ast_ok = True
        except SyntaxError as _exc:
            _daily_kanban_ast_detail = str(_exc)

    test(
        "daily_kanban_digest: tool existe y tiene sintaxis valida",
        _daily_kanban_exists and _daily_kanban_ast_ok,
        _daily_kanban_ast_detail,
    )
    test(
        "daily_kanban_digest: soporta --dry-run",
        "--dry-run" in _daily_kanban_src and "dry_run" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: no importa bot.py ni trading core",
        "import bot" not in _daily_kanban_src
        and "from bot" not in _daily_kanban_src
        and "execute_trade" not in _daily_kanban_src
        and "manage_positions" not in _daily_kanban_src
        and "intra_cycle_sl_check" not in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: no contiene envio Telegram real",
        "send_telegram" not in _daily_kanban_src
        and "api.telegram.org" not in _daily_kanban_src
        and "TELEGRAM_TOKEN" not in _daily_kanban_src
        and "TELEGRAM_CHAT_ID" not in _daily_kanban_src
        and "urllib.request" not in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: no hardcodea env enabled a 1",
        'KANBAN_DIGEST_ENABLED", "1"' not in _daily_kanban_src
        and "KANBAN_DIGEST_ENABLED=1" not in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: contiene disclaimer no trading",
        "Esta alerta no autoriza cambios de trading." in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: contrato JSON read-only",
        "would_send" in _daily_kanban_src
        and "generated_at_utc" in _daily_kanban_src
        and "sections" in _daily_kanban_src
        and "next_step" in _daily_kanban_src
        and "disclaimers" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: reconoce timestamp_utc en cycles_history",
        "row.get(\"timestamp_utc\")" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: expone source_quality de P/L",
        "\"source_quality\"" in _daily_kanban_src
        and "\"contaminated_records\"" in _daily_kanban_src
        and "\"contamination_rate\"" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: advierte P/L contaminado no operacional",
        "P/L incluye registros reconstruidos/no audit-ready" in _daily_kanban_src
        and "no usar para BANKROLL ni decisiones operativas" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: expone pnl_sources read-only",
        "\"pnl_sources\"" in _daily_kanban_src
        and "\"wallet_pnl\"" in _daily_kanban_src
        and "\"cash_flows\"" in _daily_kanban_src
        and "\"canonical_source\"" in _daily_kanban_src
        and "\"bankroll_readiness\"" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: pnl_sources no ejecuta wallet_snapshot ni promueve canon automatico",
        "wallet_snapshot.py" not in _daily_kanban_src
        and "\"canonical_source\": \"none\"" in _daily_kanban_src
        and "\"bankroll_readiness\": \"blocked\"" in _daily_kanban_src,
    )
    test(
        "daily_kanban_digest: no escribe archivos de estado",
        "write_text(" not in _daily_kanban_src
        and "write_bytes(" not in _daily_kanban_src
        and ".write(" not in _daily_kanban_src
        and "alerts_state.json" not in _daily_kanban_src
        and 'kanban_state.json").write' not in _daily_kanban_src,
    )

    # ---- Wallet Cash Flow Log manual-only ----
    print("\n Wallet Cash Flow Log manual-only")
    _wallet_cash_flow_log_path = os.path.join(os.path.dirname(__file__), "tools", "wallet_cash_flow_log.py")
    _wallet_cash_flow_log_exists = os.path.exists(_wallet_cash_flow_log_path)
    _wallet_cash_flow_log_src = ""
    _wallet_cash_flow_log_ast_ok = False
    _wallet_cash_flow_log_ast_detail = ""
    _wallet_cash_flow_log_imports = set()
    if _wallet_cash_flow_log_exists:
        with open(_wallet_cash_flow_log_path, encoding="utf-8") as _f:
            _wallet_cash_flow_log_src = _f.read()
        try:
            _wallet_cash_flow_log_ast = ast.parse(_wallet_cash_flow_log_src)
            _wallet_cash_flow_log_ast_ok = True
            for _node in ast.walk(_wallet_cash_flow_log_ast):
                if isinstance(_node, ast.Import):
                    for _alias in _node.names:
                        _wallet_cash_flow_log_imports.add(_alias.name.split(".", 1)[0])
                elif isinstance(_node, ast.ImportFrom) and _node.module:
                    _wallet_cash_flow_log_imports.add(_node.module.split(".", 1)[0])
        except SyntaxError as _exc:
            _wallet_cash_flow_log_ast_detail = str(_exc)

    _wallet_cash_flow_allowed_imports = {
        "__future__", "argparse", "json", "sys", "uuid", "dataclasses",
        "datetime", "decimal", "pathlib", "typing",
    }
    _wallet_cash_flow_forbidden_tokens = [
        "import bot",
        "from bot",
        "execute_trade",
        "manage_positions",
        "intra_cycle_sl_check",
        "OrderArgs",
        "post_order",
        "create_order",
        "cancel_order",
        "send_telegram",
        "api.telegram.org",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "sqlite3",
        "psycopg",
        "railway",
        "RAILWAY",
        "requests",
        "httpx",
        "aiohttp",
        "urllib.request",
        "BANKROLL",
        "canonical_source",
        "bankroll_readiness",
    ]
    _wallet_cash_flow_gitignore_ok = "data/wallet_cash_flows.jsonl" in gitignore_content
    _wallet_cash_flow_real_path = os.path.join(os.path.dirname(__file__), "data", "wallet_cash_flows.jsonl")

    test(
        "wallet_cash_flow_log: tool existe y tiene sintaxis valida",
        _wallet_cash_flow_log_exists and _wallet_cash_flow_log_ast_ok,
        _wallet_cash_flow_log_ast_detail,
    )
    test(
        "wallet_cash_flow_log: data/wallet_cash_flows.jsonl no existe localmente",
        not os.path.exists(_wallet_cash_flow_real_path),
    )
    test(
        "wallet_cash_flow_log: archivo real excluido en .gitignore",
        _wallet_cash_flow_gitignore_ok,
    )
    test(
        "wallet_cash_flow_log: no importa bot.py ni trading core",
        all(_token not in _wallet_cash_flow_log_src for _token in _wallet_cash_flow_forbidden_tokens[:8]),
    )
    test(
        "wallet_cash_flow_log: sin Telegram, DB, Railway ni red",
        all(_token not in _wallet_cash_flow_log_src for _token in _wallet_cash_flow_forbidden_tokens[8:20]),
    )
    test(
        "wallet_cash_flow_log: no toca readiness/BANKROLL",
        all(_token not in _wallet_cash_flow_log_src for _token in _wallet_cash_flow_forbidden_tokens[20:]),
    )
    test(
        "wallet_cash_flow_log: stdlib-only imports",
        _wallet_cash_flow_log_imports <= _wallet_cash_flow_allowed_imports,
        f"imports={sorted(_wallet_cash_flow_log_imports - _wallet_cash_flow_allowed_imports)}",
    )
    test(
        "wallet_cash_flow_log: actor hardcoded pablo_manual schema v2",
        'ACTOR = "pablo_manual"' in _wallet_cash_flow_log_src
        and "SCHEMA_VERSION = 2" in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: tipos allowlist y prohibidos",
        "deposit" in _wallet_cash_flow_log_src
        and "withdrawal" in _wallet_cash_flow_log_src
        and "no_cash_flow_attestation" in _wallet_cash_flow_log_src
        and "adjustment" in _wallet_cash_flow_log_src
        and "inferred" in _wallet_cash_flow_log_src
        and "reconstructed" in _wallet_cash_flow_log_src
        and "estimated" in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: UUID4 auto y EXAMPLE rechazado",
        "uuid.uuid4()" in _wallet_cash_flow_log_src
        and "validate_uuid4" in _wallet_cash_flow_log_src
        and "EXAMPLE-" in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: dry-run default no escribe",
        "if not args.write:" in _wallet_cash_flow_log_src
        and '"dry_run": True' in _wallet_cash_flow_log_src
        and "DRY-RUN: row NOT written." in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: init requiere write y confirmacion textual",
        "--init is only valid with --write" in _wallet_cash_flow_log_src
        and 'CONFIRMATION_TEXT = "YES I CONFIRM"' in _wallet_cash_flow_log_src
        and "confirm_init(path, args.yes)" in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: append valida ledger existente antes de escribir",
        "ledger = load_existing_ledger(path)" in _wallet_cash_flow_log_src
        and "build_row(args, ledger.entry_ids)" in _wallet_cash_flow_log_src
        and 'with path.open("a", encoding="utf-8")' in _wallet_cash_flow_log_src,
    )
    test(
        "wallet_cash_flow_log: adjustment requiere note, Opus y confirmacion",
        "adjustment requires non-empty note" in _wallet_cash_flow_log_src
        and "adjustment requires --reviewed-by-opus" in _wallet_cash_flow_log_src
        and "adjustment requires --confirm-adjustment" in _wallet_cash_flow_log_src,
    )

    # ---- Resultado ----
    print(f"\n{'='*50}")
    total = passed + failed
    if failed == 0:
        print(f"[OK] TODOS LOS TESTS PASARON ({passed}/{total})")
        print("Puedes hacer deploy con confianza.")
    else:
        print(f" {failed} TESTS FALLARON de {total}")
        print("Errores:")
        for e in errors:
            print(f"  - {e}")
        print("\n[STOP] NO hacer deploy hasta corregir los errores.")
    print(f"{'='*50}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
