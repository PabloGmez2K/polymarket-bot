"""
tests/test_truth_pipeline_alarms.py — Tests para truth_pipeline_alarms.py (Fase 1A.4).

Todos los tests usan fixtures y tmp_path. Sin DB real. Sin red. Sin Telegram real.

Taxonomía canónica (post-revisión):
    NO_ACTION     — datos sanos (sin alerta)
    WATCH         — calibración baja + n≥10
    WATCH_TECH    — schema_missing o DB inaccesible
    ACTION_DESIGN — drift ≥3 en 1 ciudad
    ACTION_SAFETY — drift ≥3 en 2+ ciudades

Cubre:
- classify_alarm_level: schema_missing → WATCH_TECH
- classify_alarm_level: drift 1 ciudad → ACTION_DESIGN
- classify_alarm_level: drift 2+ ciudades → ACTION_SAFETY
- classify_alarm_level: calibración baja + n≥10 → WATCH
- classify_alarm_level: sano → NO_ACTION
- format_alarm_message: no contiene instrucciones de trading
- format_alarm_message: contiene "no autoriza cambios de trading"
- format_alarm_message: ACTION_DESIGN/ACTION_SAFETY mencionan Opus
- run_alarm: enabled=False → disabled
- run_alarm: dry_run=True → dry_run, no escribe state file
- run_alarm: already_sent_today → suppressed
- run_alarm: NO_ACTION level → no_change
- Estado anti-spam: record_sent + already_sent_today
- No importa bot.py ni módulos de trading core
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from tools.truth_pipeline_alarms import (  # noqa: E402
    already_sent_today,
    classify_alarm_level,
    format_alarm_message,
    record_sent,
    run_alarm,
)

# ─── Fixtures de reporte ──────────────────────────────────────────────────────

_REPORT_SCHEMA_MISSING = {
    "status": "schema_missing",
    "message": "truth_records table not found",
}

_REPORT_EMPTY = {
    "status": "empty",
    "truth_records": 0,
    "n_resolved": 0,
    "calibration_global": None,
    "drift_alert_cities": [],
}

_REPORT_NO_ACTION = {
    "status": "no_action",
    "truth_records": 5,
    "n_resolved": 5,
    "calibration_global": 0.8,
    "drift_alert_cities": [],
    "calibration_by_city": [
        {"city": "Paris", "n": 5, "n_ok": 4, "calibration": 0.8},
    ],
}

_REPORT_WATCH = {
    "status": "watch",
    "truth_records": 10,
    "n_resolved": 10,
    "calibration_global": 0.3,
    "drift_alert_cities": [],
    "calibration_by_city": [
        {"city": "Paris", "n": 10, "n_ok": 3, "calibration": 0.3},
    ],
}

_REPORT_ACTION_DESIGN = {
    "status": "action_design",
    "truth_records": 8,
    "n_resolved": 6,
    "calibration_global": 0.33,
    "drift_alert_cities": [
        {"city": "Paris", "condition": "exact", "n_wrong": 3},
    ],
}

_REPORT_ACTION_SAFETY = {
    "status": "action_safety",
    "truth_records": 15,
    "n_resolved": 12,
    "calibration_global": 0.25,
    "drift_alert_cities": [
        {"city": "Paris", "condition": "exact", "n_wrong": 4},
        {"city": "Seoul", "condition": "exact", "n_wrong": 3},
    ],
}

_REPORT_WATCH_TECH = {
    "status": "watch_tech",
    "error": "DB not found",
}


# ─── Test 1: classify_alarm_level ────────────────────────────────────────────

class TestClassifyAlarmLevel:

    def test_schema_missing_returns_watch_tech(self):
        assert classify_alarm_level(_REPORT_SCHEMA_MISSING) == "WATCH_TECH"

    def test_watch_tech_report_returns_watch_tech(self):
        assert classify_alarm_level(_REPORT_WATCH_TECH) == "WATCH_TECH"

    def test_drift_one_city_returns_action_design(self):
        assert classify_alarm_level(_REPORT_ACTION_DESIGN) == "ACTION_DESIGN"

    def test_drift_two_cities_returns_action_safety(self):
        assert classify_alarm_level(_REPORT_ACTION_SAFETY) == "ACTION_SAFETY"

    def test_watch_status_returns_watch(self):
        assert classify_alarm_level(_REPORT_WATCH) == "WATCH"

    def test_no_action_report_returns_no_action(self):
        assert classify_alarm_level(_REPORT_NO_ACTION) == "NO_ACTION"

    def test_empty_report_returns_no_action(self):
        assert classify_alarm_level(_REPORT_EMPTY) == "NO_ACTION"

    def test_action_safety_takes_priority_over_watch(self):
        report = dict(_REPORT_ACTION_SAFETY, calibration_global=0.1, n_resolved=20)
        assert classify_alarm_level(report) == "ACTION_SAFETY"

    def test_action_design_takes_priority_over_watch(self):
        report = dict(_REPORT_ACTION_DESIGN, calibration_global=0.1, n_resolved=20)
        assert classify_alarm_level(report) == "ACTION_DESIGN"

    def test_no_action_audit_level_exists(self):
        """ACTION_AUDIT no es parte de la taxonomía canónica Fase 1."""
        for report in [_REPORT_NO_ACTION, _REPORT_EMPTY, _REPORT_WATCH,
                       _REPORT_ACTION_DESIGN, _REPORT_ACTION_SAFETY]:
            level = classify_alarm_level(report)
            assert level != "ACTION_AUDIT", f"ACTION_AUDIT no debe usarse en Fase 1, got: {level}"


# ─── Test 2: format_alarm_message ────────────────────────────────────────────

class TestFormatAlarmMessage:

    def test_no_buy_in_message(self):
        combos = [
            (_REPORT_NO_ACTION, "NO_ACTION"),
            (_REPORT_WATCH, "WATCH"),
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
            (_REPORT_ACTION_SAFETY, "ACTION_SAFETY"),
        ]
        for report, level in combos:
            msg = format_alarm_message(report, level)
            assert "BUY" not in msg, f"'BUY' found in {level} message"

    def test_no_sell_in_message(self):
        combos = [
            (_REPORT_NO_ACTION, "NO_ACTION"),
            (_REPORT_WATCH, "WATCH"),
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
        ]
        for report, level in combos:
            msg = format_alarm_message(report, level)
            assert "SELL" not in msg, f"'SELL' found in {level} message"

    def test_no_operational_trading_instructions(self):
        combos = [
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
            (_REPORT_ACTION_SAFETY, "ACTION_SAFETY"),
            (_REPORT_WATCH, "WATCH"),
        ]
        for report, level in combos:
            msg = format_alarm_message(report, level)
            assert "SKIP real" not in msg
            assert "comprar" not in msg.lower()
            assert "vender" not in msg.lower()

    def test_no_bankroll_escalation_in_any_level(self):
        combos = [
            (_REPORT_NO_ACTION, "NO_ACTION"),
            (_REPORT_WATCH, "WATCH"),
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
            (_REPORT_ACTION_SAFETY, "ACTION_SAFETY"),
        ]
        for report, level in combos:
            msg = format_alarm_message(report, level)
            assert "Fase C" not in msg
            # No debe recomendar escalado de bankroll
            assert "escalar bankroll" not in msg.lower()

    def test_contains_no_autoriza_trading(self):
        combos = [
            (_REPORT_NO_ACTION, "NO_ACTION"),
            (_REPORT_WATCH, "WATCH"),
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
            (_REPORT_ACTION_SAFETY, "ACTION_SAFETY"),
        ]
        for report, level in combos:
            msg = format_alarm_message(report, level)
            assert "no autoriza cambios de trading" in msg.lower(), \
                f"Missing trading disclaimer in {level} message"

    def test_action_design_mentions_opus(self):
        msg = format_alarm_message(_REPORT_ACTION_DESIGN, "ACTION_DESIGN")
        assert "Opus" in msg

    def test_action_safety_mentions_opus(self):
        msg = format_alarm_message(_REPORT_ACTION_SAFETY, "ACTION_SAFETY")
        assert "Opus" in msg

    def test_watch_mentions_sonnet(self):
        msg = format_alarm_message(_REPORT_WATCH, "WATCH")
        assert "Sonnet" in msg

    def test_watch_tech_mentions_sonnet(self):
        msg = format_alarm_message(_REPORT_WATCH_TECH, "WATCH_TECH")
        assert "Sonnet" in msg

    def test_message_has_level_header(self):
        msg = format_alarm_message(_REPORT_WATCH, "WATCH")
        assert "WATCH" in msg
        assert "Truth Pipeline" in msg

    def test_message_has_component_and_date(self):
        msg = format_alarm_message(_REPORT_NO_ACTION, "NO_ACTION")
        assert "Truth Pipeline" in msg
        assert "Fase 1" in msg

    def test_message_shows_calibration(self):
        msg = format_alarm_message(_REPORT_NO_ACTION, "NO_ACTION")
        assert "80%" in msg or "Calibración" in msg

    def test_action_design_shows_drift_city(self):
        msg = format_alarm_message(_REPORT_ACTION_DESIGN, "ACTION_DESIGN")
        assert "Paris" in msg
        assert "exact" in msg

    def test_action_safety_shows_all_drift_cities(self):
        msg = format_alarm_message(_REPORT_ACTION_SAFETY, "ACTION_SAFETY")
        assert "Paris" in msg
        assert "Seoul" in msg

    def test_no_tarea_para_codex_header(self):
        """Prohibido header engañoso 'Tarea para Codex' si no hay acción real."""
        msg = format_alarm_message(_REPORT_WATCH, "WATCH")
        assert "Tarea para Codex" not in msg

    def test_codex_only_if_patch_approved(self):
        """Si se menciona Codex, debe ser condicional a patch aprobado."""
        for report, level in [
            (_REPORT_ACTION_DESIGN, "ACTION_DESIGN"),
            (_REPORT_ACTION_SAFETY, "ACTION_SAFETY"),
        ]:
            msg = format_alarm_message(report, level)
            if "Codex" in msg:
                assert "aprobado" in msg or "patch" in msg.lower(), \
                    f"Codex mention without approval condition in {level}"


# ─── Test 3: run_alarm con enabled=False ─────────────────────────────────────

class TestRunAlarmDisabled:

    def test_disabled_returns_disabled_action(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, enabled=False, state_file=state)
        assert result["action"] == "disabled"

    def test_disabled_does_not_write_state_file(self, tmp_path):
        state = str(tmp_path / "state.json")
        run_alarm(_REPORT_WATCH, enabled=False, state_file=state)
        assert not Path(state).exists()

    def test_disabled_still_has_level(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, enabled=False, state_file=state)
        assert result.get("level") == "WATCH"

    def test_disabled_still_has_message(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, enabled=False, state_file=state)
        assert result.get("message")


# ─── Test 4: run_alarm dry_run ────────────────────────────────────────────────

class TestRunAlarmDryRun:

    def test_dry_run_returns_dry_run_action(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, dry_run=True, enabled=False, state_file=state)
        assert result["action"] == "dry_run"

    def test_dry_run_does_not_write_state_file(self, tmp_path):
        state = str(tmp_path / "state.json")
        run_alarm(_REPORT_WATCH, dry_run=True, enabled=True, state_file=state)
        assert not Path(state).exists()

    def test_dry_run_has_message(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, dry_run=True, enabled=True, state_file=state)
        assert result.get("message")

    def test_dry_run_has_level(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_WATCH, dry_run=True, enabled=True, state_file=state)
        assert result.get("level") == "WATCH"

    def test_dry_run_action_design(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_ACTION_DESIGN, dry_run=True, enabled=True, state_file=state)
        assert result["action"] == "dry_run"
        assert result["level"] == "ACTION_DESIGN"
        assert "Opus" in result["message"]

    def test_dry_run_action_safety(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_ACTION_SAFETY, dry_run=True, enabled=True, state_file=state)
        assert result["action"] == "dry_run"
        assert result["level"] == "ACTION_SAFETY"
        assert "Opus" in result["message"]


# ─── Test 5: anti-spam ───────────────────────────────────────────────────────

class TestAntiSpam:

    def test_record_sent_marks_today(self, tmp_path):
        state = str(tmp_path / "state.json")
        assert not already_sent_today(state)
        record_sent(state, "WATCH")
        assert already_sent_today(state)

    def test_record_sent_writes_level(self, tmp_path):
        state = str(tmp_path / "state.json")
        record_sent(state, "ACTION_DESIGN")
        data = json.loads(Path(state).read_text(encoding="utf-8"))
        assert data.get("last_level") == "ACTION_DESIGN"

    def test_already_sent_today_false_on_empty_state(self, tmp_path):
        state = str(tmp_path / "state.json")
        assert not already_sent_today(state)

    def test_already_sent_today_false_on_missing_file(self, tmp_path):
        state = str(tmp_path / "nonexistent.json")
        assert not already_sent_today(state)

    def test_suppressed_when_already_sent(self, tmp_path):
        state = str(tmp_path / "state.json")
        record_sent(state, "WATCH")
        result = run_alarm(_REPORT_WATCH, enabled=True, state_file=state)
        assert result["action"] == "suppressed"

    def test_suppressed_has_reason(self, tmp_path):
        state = str(tmp_path / "state.json")
        record_sent(state, "WATCH")
        result = run_alarm(_REPORT_WATCH, enabled=True, state_file=state)
        assert result.get("reason") == "already_sent_today"

    def test_force_bypasses_antispam(self, tmp_path, monkeypatch):
        """force=True bypasses anti-spam pero falla por falta de credenciales."""
        state = str(tmp_path / "state.json")
        record_sent(state, "WATCH")
        monkeypatch.delenv("TRUTH_PIPELINE_TG_CHAT_ID", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        result = run_alarm(
            _REPORT_WATCH, enabled=True, state_file=state, force=True
        )
        assert result["action"] != "suppressed"


# ─── Test 6: NO_ACTION level → no_change ─────────────────────────────────────

class TestNoActionLevel:

    def test_no_action_returns_no_change(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_NO_ACTION, enabled=True, state_file=state)
        assert result["action"] == "no_change"

    def test_no_action_does_not_write_state(self, tmp_path):
        state = str(tmp_path / "state.json")
        run_alarm(_REPORT_NO_ACTION, enabled=True, state_file=state)
        assert not Path(state).exists()

    def test_empty_report_gives_no_change(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_EMPTY, enabled=True, state_file=state)
        assert result["action"] == "no_change"

    def test_no_action_level_in_result(self, tmp_path):
        state = str(tmp_path / "state.json")
        result = run_alarm(_REPORT_NO_ACTION, enabled=True, state_file=state)
        assert result.get("level") == "NO_ACTION"


# ─── Test 7: aislamiento ─────────────────────────────────────────────────────

class TestIsolation:
    """truth_pipeline_alarms.py no importa bot.py ni módulos de trading core."""

    def _src(self) -> str:
        return (REPO_ROOT / "tools" / "truth_pipeline_alarms.py").read_text(encoding="utf-8")

    def test_no_bot_import(self):
        src = self._src()
        assert "import bot" not in src
        assert "from bot" not in src

    def test_no_trading_core_symbols(self):
        src = self._src()
        forbidden = [
            "execute_trade", "manage_positions",
            "execute_order", "post_order", "create_order",
        ]
        for sym in forbidden:
            assert sym not in src, f"Found forbidden symbol: {sym}"

    def test_stdlib_only(self):
        src = self._src()
        forbidden = ["import requests", "import httpx", "import aiohttp"]
        for imp in forbidden:
            assert imp not in src, f"Found forbidden import: {imp}"

    def test_default_telegram_disabled(self):
        src = self._src()
        assert 'TRUTH_PIPELINE_TELEGRAM_ENABLED' in src
        assert '"0"' in src or "'0'" in src

    def test_no_operational_channel_hardcoded(self):
        """No usa TELEGRAM_CHAT_ID del canal operativo del bot."""
        src = self._src()
        assert 'TELEGRAM_CHAT_ID"' not in src or 'TRUTH_PIPELINE_TG_CHAT_ID' in src

    def test_no_action_audit_in_source(self):
        """ACTION_AUDIT no debe aparecer como nivel en el código fuente."""
        src = self._src()
        assert '"ACTION_AUDIT"' not in src
        assert "'ACTION_AUDIT'" not in src

    def test_canonical_levels_present(self):
        """Los 5 niveles canónicos están en el source."""
        src = self._src()
        for level in ("NO_ACTION", "WATCH", "WATCH_TECH", "ACTION_DESIGN", "ACTION_SAFETY"):
            assert level in src, f"Missing canonical level: {level}"

    def test_format_messages_have_no_operational_trading(self):
        """Los mensajes generados no deben contener lenguaje operativo de trading."""
        for report in [_REPORT_NO_ACTION, _REPORT_WATCH, _REPORT_ACTION_DESIGN, _REPORT_ACTION_SAFETY]:
            level = classify_alarm_level(report)
            msg = format_alarm_message(report, level)
            assert "comprar" not in msg.lower()
            assert "vender" not in msg.lower()
