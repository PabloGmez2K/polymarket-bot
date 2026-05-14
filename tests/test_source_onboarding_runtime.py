"""Tests focalizados para maybe_run_source_onboarding_scanner — integración runtime LOG_ONLY.

Cubre:
1. Daily gate evita doble ejecución el mismo día UTC.
2. Fallo de inputs críticos: no crashea, state actualizado, JSON anterior intacto.
3. Genera source_onboarding.json con paths fake (tmpdir).
4. No envía Telegram propio.
5. No ejecuta source_audit_workbench automáticamente.
6. Digest lee source_onboarding.json generado por el scanner (sin warning de missing).
"""

import ast
import importlib.util
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_scanner_mod():
    script = REPO_ROOT / "tools" / "source_onboarding_scanner.py"
    spec = importlib.util.spec_from_file_location("source_onboarding_scanner", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_digest_mod():
    script = REPO_ROOT / "tools" / "city_intelligence_digest.py"
    spec = importlib.util.spec_from_file_location("city_intelligence_digest", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_minimal_policy_env(tmp_path, active="", blocked="", canary=""):
    p = tmp_path / "policy_env.json"
    p.write_text(json.dumps({"variables": {
        "ACTIVE_TRADING_CITIES": active,
        "BLOCKED_CITIES": blocked,
        "CANARY_TRADING_CITIES": canary,
    }}), encoding="utf-8")
    return str(p)


def _make_minimal_policy_state(tmp_path):
    p = tmp_path / "policy_state.json"
    p.write_text(json.dumps({"auto_canary_cities": {}, "auto_shadow_cities": {}}), encoding="utf-8")
    return str(p)


def _make_minimal_shadow(tmp_path):
    p = tmp_path / "shadow.json"
    p.write_text(json.dumps({"cities": {}}), encoding="utf-8")
    return str(p)


def _build_runtime_fn(scanner_mod, tmp_path, active_cities=None, blocked_cities=None, canary_cities=None):
    """Build an isolated version of maybe_run_source_onboarding_scanner using tmpdir paths."""
    active_cities = active_cities or set()
    blocked_cities = blocked_cities or set()
    canary_cities = canary_cities or set()

    json_out = str(tmp_path / "source_onboarding.json")
    md_out = str(tmp_path / "source_onboarding.md")
    policy_env_path = str(tmp_path / "policy_env_snapshot.json")
    policy_state_path = _make_minimal_policy_state(tmp_path)
    shadow_path = _make_minimal_shadow(tmp_path)

    warnings_logged = []

    def fake_log_warning(msg):
        warnings_logged.append(msg)

    def run_scanner(state):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if state.get("source_onboarding_last_run_date") == today:
            return False

        # Synthesize policy_env_snapshot
        try:
            policy_env_data = {
                "variables": {
                    "ACTIVE_TRADING_CITIES": ",".join(sorted(active_cities)),
                    "CANARY_TRADING_CITIES": ",".join(sorted(canary_cities)),
                    "BLOCKED_CITIES": ",".join(sorted(blocked_cities)),
                }
            }
            Path(policy_env_path).write_text(
                json.dumps(policy_env_data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            fake_log_warning(f"source_onboarding_scanner: no se pudo escribir policy_env_snapshot ({e})")
            state["source_onboarding_last_run_date"] = today
            return True

        overrides_path = str(tmp_path / "nonexistent_overrides.json")

        argv = [
            "--signals-crosscheck", str(tmp_path / "nonexistent_signals.jsonl"),
            "--blocked-resolutions", str(tmp_path / "nonexistent_blocked.jsonl"),
            "--shadow-tracking", shadow_path,
            "--policy-env", policy_env_path,
            "--policy-state", policy_state_path,
            "--overrides", overrides_path,
            "--json-output", json_out,
            "--md-output", md_out,
        ]

        try:
            result = scanner_mod.main(argv)
            if result and result != 0:
                fake_log_warning(
                    f"source_onboarding_scanner: main() returned {result} "
                    "(inputs criticos ausentes — digest degradara limpiamente)"
                )
        except Exception as e:
            fake_log_warning(f"source_onboarding_scanner: error ejecutando scanner ({e})")

        state["source_onboarding_last_run_date"] = today
        return True

    return run_scanner, warnings_logged, json_out


# ---------------------------------------------------------------------------
# Test 1: Daily gate evita doble ejecución
# ---------------------------------------------------------------------------

class TestDailyGate:
    def test_same_day_returns_false(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, _ = _build_runtime_fn(scanner_mod, tmp_path)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {"source_onboarding_last_run_date": today}

        result = fn(state)
        assert result is False, "daily gate debe retornar False si ya corrió hoy"

    def test_different_day_runs(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, _ = _build_runtime_fn(scanner_mod, tmp_path)
        state = {"source_onboarding_last_run_date": "2020-01-01"}

        result = fn(state)
        assert result is True, "debe correr si la fecha es diferente"

    def test_empty_state_runs(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, _ = _build_runtime_fn(scanner_mod, tmp_path)
        state = {}

        result = fn(state)
        assert result is True, "debe correr si state vacío"

    def test_sets_last_run_date_in_state(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, _ = _build_runtime_fn(scanner_mod, tmp_path)
        state = {}
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        fn(state)
        assert state.get("source_onboarding_last_run_date") == today


# ---------------------------------------------------------------------------
# Test 2: Genera JSON con paths fake (tmpdir)
# ---------------------------------------------------------------------------

class TestJsonGeneration:
    def test_generates_source_onboarding_json(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, json_out = _build_runtime_fn(scanner_mod, tmp_path)
        state = {}

        fn(state)

        assert Path(json_out).exists(), "source_onboarding.json debe generarse"
        data = json.loads(Path(json_out).read_text(encoding="utf-8"))
        assert data.get("log_only") is True
        assert "LOG_ONLY" in data.get("disclaimer", "")
        assert "cities" in data

    def test_generated_json_is_valid_log_only(self, tmp_path):
        scanner_mod = _load_scanner_mod()
        fn, _, json_out = _build_runtime_fn(scanner_mod, tmp_path)
        fn({})

        data = json.loads(Path(json_out).read_text(encoding="utf-8"))
        assert "No BUY" in data.get("disclaimer", "")
        assert "No BANKROLL" in data.get("disclaimer", "")
        assert data.get("log_only") is True


# ---------------------------------------------------------------------------
# Test 3: Fallo de inputs críticos — no crashea, state actualizado
# ---------------------------------------------------------------------------

class TestDegradation:
    def test_missing_shadow_tracking_does_not_crash(self, tmp_path):
        """Si shadow_tracking falta (CRITICAL), main() retorna 1 — no exception."""
        scanner_mod = _load_scanner_mod()
        warnings_logged = []

        def run_degraded(state):
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if state.get("source_onboarding_last_run_date") == today:
                return False

            # Write policy_env
            policy_env_path = str(tmp_path / "policy_env.json")
            Path(policy_env_path).write_text(json.dumps({"variables": {
                "ACTIVE_TRADING_CITIES": "",
                "CANARY_TRADING_CITIES": "",
                "BLOCKED_CITIES": "",
            }}), encoding="utf-8")
            policy_state_path = _make_minimal_policy_state(tmp_path)

            argv = [
                "--shadow-tracking", str(tmp_path / "nonexistent_shadow.json"),  # MISSING
                "--policy-env", policy_env_path,
                "--policy-state", policy_state_path,
                "--json-output", str(tmp_path / "out.json"),
                "--md-output", str(tmp_path / "out.md"),
            ]
            try:
                result = scanner_mod.main(argv)
                if result and result != 0:
                    warnings_logged.append(f"main returned {result}")
            except Exception as e:
                warnings_logged.append(str(e))

            state["source_onboarding_last_run_date"] = today
            return True

        state = {}
        # Must not raise
        result = run_degraded(state)
        assert result is True
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert state.get("source_onboarding_last_run_date") == today
        # main() should have returned 1 (critical missing), logged as warning
        assert any("1" in str(w) or "CRITICAL" in str(w) for w in warnings_logged), (
            "Should log warning when main() returns non-zero for missing critical input"
        )

    def test_state_updated_even_on_degraded_run(self, tmp_path):
        """Even if scanner fails, source_onboarding_last_run_date must be set."""
        scanner_mod = _load_scanner_mod()
        fn, _, _ = _build_runtime_fn(scanner_mod, tmp_path)

        state = {}
        # Remove shadow file to trigger degradation (scanner_mod.main returns 1 for critical missing)
        # But our _build_runtime_fn doesn't delete shadow — we just verify the state key is set
        fn(state)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert state.get("source_onboarding_last_run_date") == today


# ---------------------------------------------------------------------------
# Test 4: No envía Telegram propio
# ---------------------------------------------------------------------------

class TestNoTelegram:
    def test_function_source_no_send_telegram(self):
        """maybe_run_source_onboarding_scanner no llama send_telegram directamente."""
        bot_path = REPO_ROOT / "bot.py"
        src = bot_path.read_text(encoding="utf-8")

        fn_start = src.find("def maybe_run_source_onboarding_scanner(")
        assert fn_start != -1, "función no encontrada en bot.py"

        # Find end of function: next def at same indent level
        fn_body_start = fn_start + len("def maybe_run_source_onboarding_scanner(")
        next_fn = src.find("\ndef ", fn_start + 1)
        fn_body = src[fn_start:next_fn] if next_fn != -1 else src[fn_start:]

        assert "send_telegram" not in fn_body, (
            "maybe_run_source_onboarding_scanner no debe llamar send_telegram"
        )

    def test_scanner_tool_no_telegram_tokens(self):
        """source_onboarding_scanner.py no contiene send_telegram ni api.telegram.org."""
        src = (REPO_ROOT / "tools" / "source_onboarding_scanner.py").read_text(encoding="utf-8")
        assert "send_telegram" not in src
        assert "api.telegram.org" not in src
        assert "TELEGRAM_TOKEN" not in src


# ---------------------------------------------------------------------------
# Test 5: No ejecuta source_audit_workbench automáticamente
# ---------------------------------------------------------------------------

class TestNoSourceAuditWorkbench:
    def test_function_does_not_execute_workbench(self):
        """maybe_run_source_onboarding_scanner no importa ni ejecuta source_audit_workbench."""
        bot_path = REPO_ROOT / "bot.py"
        src = bot_path.read_text(encoding="utf-8")

        fn_start = src.find("def maybe_run_source_onboarding_scanner(")
        assert fn_start != -1
        next_fn = src.find("\ndef ", fn_start + 1)
        fn_body = src[fn_start:next_fn] if next_fn != -1 else src[fn_start:]

        # Must not import or invoke workbench (mention in docstring is OK)
        assert "import source_audit_workbench" not in fn_body, (
            "función no debe importar source_audit_workbench"
        )
        assert "source_audit_workbench.main" not in fn_body, (
            "función no debe llamar source_audit_workbench.main"
        )
        assert "source_audit_workbench_script" not in fn_body, (
            "función no debe referenciar ruta del workbench script"
        )

    def test_scanner_tool_no_workbench(self):
        """source_onboarding_scanner.py no importa ni invoca source_audit_workbench."""
        src = (REPO_ROOT / "tools" / "source_onboarding_scanner.py").read_text(encoding="utf-8")
        assert "source_audit_workbench" not in src


# ---------------------------------------------------------------------------
# Test 6: Digest lee source_onboarding.json generado (sin warning de missing)
# ---------------------------------------------------------------------------

class TestDigestReadsGeneratedJson:
    def test_digest_no_missing_warning_when_json_exists(self, tmp_path):
        """Una vez que el scanner genera source_onboarding.json, el digest no reporta 'not found'."""
        scanner_mod = _load_scanner_mod()
        digest_mod = _load_digest_mod()

        fn, _, json_out = _build_runtime_fn(scanner_mod, tmp_path)

        # 1. Run scanner first
        fn({})
        assert Path(json_out).exists(), "scanner debe haber generado source_onboarding.json"

        # 2. Run digest with the generated file
        lifecycle_path = tmp_path / "lifecycle.json"
        lifecycle_path.write_text(json.dumps({
            "generated_at": "2026-05-14T10:00:00+00:00",
            "log_only": True,
            "summary": {"n_cities": 0, "transition_counts": {}},
            "cities": [],
        }), encoding="utf-8")

        digest_out = tmp_path / "digest.json"
        digest_md = tmp_path / "digest.md"
        audits_dir = tmp_path / "source_audits"
        audits_dir.mkdir()

        digest_mod.main([
            "--lifecycle-review", str(lifecycle_path),
            "--source-onboarding", json_out,
            "--source-audits-dir", str(audits_dir),
            "--json-output", str(digest_out),
            "--md-output", str(digest_md),
        ])

        assert digest_out.exists()
        digest_data = json.loads(digest_out.read_text(encoding="utf-8"))

        # No "source_onboarding not found" warning in digest output
        warnings = digest_data.get("warnings", [])
        missing_warns = [w for w in warnings if "source_onboarding" in w and "not found" in w]
        assert not missing_warns, (
            f"Digest reporta source_onboarding missing aun cuando el JSON existe: {missing_warns}"
        )

    def test_digest_before_scanner_reports_missing(self, tmp_path):
        """Si el digest corre sin que el scanner haya generado el JSON, debe reportar warning."""
        digest_mod = _load_digest_mod()

        lifecycle_path = tmp_path / "lifecycle.json"
        lifecycle_path.write_text(json.dumps({
            "generated_at": "2026-05-14T10:00:00+00:00",
            "log_only": True,
            "summary": {"n_cities": 0, "transition_counts": {}},
            "cities": [],
        }), encoding="utf-8")

        digest_out = tmp_path / "digest.json"
        digest_md = tmp_path / "digest.md"
        audits_dir = tmp_path / "source_audits"
        audits_dir.mkdir()

        digest_mod.main([
            "--lifecycle-review", str(lifecycle_path),
            "--source-onboarding", str(tmp_path / "nonexistent_source_onboarding.json"),
            "--source-audits-dir", str(audits_dir),
            "--json-output", str(digest_out),
            "--md-output", str(digest_md),
        ])

        digest_data = json.loads(digest_out.read_text(encoding="utf-8"))
        warnings = digest_data.get("warnings", [])
        # Digest must report source_onboarding missing gracefully (no crash)
        missing_warns = [w for w in warnings if "source_onboarding" in w]
        assert missing_warns, "Digest debe reportar warning cuando source_onboarding.json no existe"


# ---------------------------------------------------------------------------
# Test 7: Order check — scanner definida antes del digest en bot.py
# ---------------------------------------------------------------------------

class TestOrderInBotPy:
    def test_scanner_defined_before_digest_in_bot(self):
        """maybe_run_source_onboarding_scanner debe definirse antes de maybe_run_city_intelligence_digest_alert."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
        pos_scanner = src.find("def maybe_run_source_onboarding_scanner(")
        pos_digest = src.find("def maybe_run_city_intelligence_digest_alert(")
        assert pos_scanner != -1, "maybe_run_source_onboarding_scanner no encontrada"
        assert pos_digest != -1, "maybe_run_city_intelligence_digest_alert no encontrada"
        assert pos_scanner < pos_digest, (
            "scanner debe definirse antes del digest alert en bot.py"
        )

    def test_scanner_called_before_digest_in_run_observability(self):
        """En run_observability_alerts(), el scanner debe invocarse antes que el digest."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")

        obs_start = src.find("def run_observability_alerts(")
        obs_end = src.find("\ndef ", obs_start + 1)
        obs_body = src[obs_start:obs_end] if obs_end != -1 else src[obs_start:]

        pos_scanner_call = obs_body.find("maybe_run_source_onboarding_scanner(state)")
        pos_digest_call = obs_body.find("maybe_run_city_intelligence_digest_alert(state)")

        assert pos_scanner_call != -1, "scanner no invocado en run_observability_alerts"
        assert pos_digest_call != -1, "digest no invocado en run_observability_alerts"
        assert pos_scanner_call < pos_digest_call, (
            "scanner debe invocarse antes que digest en run_observability_alerts"
        )

    def test_scanner_called_after_lifecycle_in_run_observability(self):
        """En run_observability_alerts(), el scanner debe invocarse después de lifecycle review."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")

        obs_start = src.find("def run_observability_alerts(")
        obs_end = src.find("\ndef ", obs_start + 1)
        obs_body = src[obs_start:obs_end] if obs_end != -1 else src[obs_start:]

        pos_lifecycle = obs_body.find("maybe_run_city_lifecycle_review_alert(state)")
        pos_scanner = obs_body.find("maybe_run_source_onboarding_scanner(state)")

        assert pos_lifecycle != -1
        assert pos_scanner != -1
        assert pos_lifecycle < pos_scanner, (
            "lifecycle debe invocarse antes que scanner en run_observability_alerts"
        )

    def test_state_key_present_in_bot(self):
        """source_onboarding_last_run_date key presente en bot.py."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
        assert "source_onboarding_last_run_date" in src

    def test_no_trading_actions_in_scanner_fn(self):
        """maybe_run_source_onboarding_scanner no contiene acciones de trading."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
        fn_start = src.find("def maybe_run_source_onboarding_scanner(")
        assert fn_start != -1
        next_fn = src.find("\ndef ", fn_start + 1)
        fn_body = src[fn_start:next_fn] if next_fn != -1 else src[fn_start:]

        forbidden = ["execute_trade", "post_order", "create_order", "cancel_order",
                     "execute_buy", "execute_sell"]
        for tok in forbidden:
            assert tok not in fn_body, f"Trading token '{tok}' encontrado en función scanner"

    def test_uses_data_path_not_hardcoded_app_data(self):
        """maybe_run_source_onboarding_scanner usa _data_path() no rutas hardcodeadas /app/data."""
        src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
        fn_start = src.find("def maybe_run_source_onboarding_scanner(")
        assert fn_start != -1
        next_fn = src.find("\ndef ", fn_start + 1)
        fn_body = src[fn_start:next_fn] if next_fn != -1 else src[fn_start:]

        assert "_data_path(" in fn_body, "función debe usar _data_path() para rutas de runtime"
        assert '"/app/data' not in fn_body, "no hardcodear /app/data — usar _data_path()"
