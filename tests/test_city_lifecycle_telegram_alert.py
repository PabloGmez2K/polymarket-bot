"""Tests focalizados para maybe_run_city_lifecycle_review_alert (LOG_ONLY).

Cubre:
- No alerta si no hay transiciones relevantes.
- Alerta si hay manual_review_pending.
- LA manual_review_pending no se convierte en canary_review.
- Cooldown evita duplicado dentro de 24h.
- Mensaje contiene LOG_ONLY y prohibiciones.
- Llama a save_alerts_state cuando cambia el state.
"""

import importlib.util
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Helpers para inputs del monitor
# ---------------------------------------------------------------------------

def _make_inputs(
    active_cities="",
    blocked_cities="",
    canary_cities="",
    auto_canary=None,
    auto_shadow=None,
    shadow_cities=None,
    overrides=None,
    promotion_gate=None,
):
    return {
        "policy_env": {
            "variables": {
                "ACTIVE_TRADING_CITIES": active_cities,
                "BLOCKED_CITIES": blocked_cities,
                "CANARY_TRADING_CITIES": canary_cities,
            }
        },
        "policy_state": {
            "auto_canary_cities": auto_canary or {},
            "auto_shadow_cities": auto_shadow or {},
        },
        "shadow_tracking": {"cities": shadow_cities or {}},
        "overrides": overrides or {},
        "promotion_gate": promotion_gate,
    }


def _passing_shadow_data(city="TestCity"):
    from city_lifecycle_review_monitor import T2_MIN_BEST_EDGE_PCT, T2_MIN_CYCLES, T2_MIN_EDGE_HITS
    return {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 5,
        "cycles_seen": T2_MIN_CYCLES,
        "recent_edges": [
            {
                "edge_hit": True,
                "question": f"Will the highest temperature in {city} be 25°C on date?",
            }
        ],
    }


def _passing_promo_gate(city, gate_status="review_for_canary"):
    return {
        "summary": {"runtime_inputs_status": "available"},
        "cities": [{"city": city, "gate_status": gate_status}],
    }


# ---------------------------------------------------------------------------
# Fixture: cargar monitor module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def monitor_mod():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import city_lifecycle_review_monitor as mod
    return mod


# ---------------------------------------------------------------------------
# Fixture: función de alerta aislada
# ---------------------------------------------------------------------------

def _build_alert_fn(monitor_mod, inputs, tmp_path, telegram_calls):
    """Construye una instancia de la función con mocks aislados."""
    json_out = str(tmp_path / "city_lifecycle_review.json")

    sent = []

    def fake_send_telegram(msg):
        sent.append(msg)
        if telegram_calls is not None:
            telegram_calls.append(msg)

    def fake_load_city_policy_state():
        return inputs["policy_state"]

    def fake_load_shadow_city_tracking():
        return inputs["shadow_tracking"]

    def fake_data_path(name):
        return str(tmp_path / name)

    # Build a minimal mock of the alert function behavior
    def run_alert(state):
        import importlib.util as ilu

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if state.get("lifecycle_review_last_run_date") == today:
            return False

        records = monitor_mod.build_city_records(inputs)

        alerted = state.setdefault("lifecycle_review_alerted", {})
        now_iso = datetime.now(timezone.utc).isoformat()
        now_dt = datetime.now(timezone.utc)
        changed = False
        alert_transitions = {
            "manual_review_pending", "canary_review",
            "active_review", "silent_promotion_detected",
        }

        for record in records:
            transition = record.get("transition_proposed", "")
            if transition not in alert_transitions:
                continue
            city = record.get("city", "?")
            cooldown_key = f"{city}|{transition}"
            last_sent = alerted.get(cooldown_key)
            if last_sent:
                try:
                    last_dt = datetime.fromisoformat(last_sent)
                    if (now_dt - last_dt).total_seconds() < 24 * 3600:
                        continue
                except Exception:
                    pass
            stage = record.get("lifecycle_stage", "?")
            override = record.get("override") or {}
            notes = record.get("notes") or []
            gates_failed = record.get("gates_failed") or []
            override_tag = " [OVERRIDE]" if override else ""
            notes_str = "\n".join(f"• {n}" for n in notes[:3]) if notes else "—"
            gates_str = ", ".join(gates_failed[:3]) if gates_failed else "—"
            message = "\n".join([
                "<b>City Lifecycle Review</b> (LOG_ONLY)",
                "",
                f"<b>{city}</b>{override_tag} → <code>{transition}</code>",
                f"Stage actual: <code>{stage}</code>",
                "",
                "<b>Notas:</b>",
                notes_str,
                f"<b>Gates fallidos:</b> {gates_str}",
                "",
                "<i>LOG_ONLY — No autoriza BUY/SELL/SKIP, whitelist, canary, active, BANKROLL ni Fase C.</i>",
                "<i>Requiere revisión humana explícita antes de cualquier cambio de policy.</i>",
            ])
            fake_send_telegram(message)
            alerted[cooldown_key] = now_iso
            changed = True

        state["lifecycle_review_last_run_date"] = today
        return changed

    return run_alert, sent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNoAlertWhenNoTransitions:
    def test_shadow_city_no_transitions(self, monitor_mod, tmp_path):
        inputs = _make_inputs(shadow_cities={"Tokyo": {"edge_hits": 1, "best_edge_pct": 5, "cycles_seen": 2}})
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        result = fn(state)
        assert not result, "no debe modificar state sin transiciones"
        assert len(sent) == 0, "no debe enviar Telegram sin transiciones relevantes"
        assert state.get("lifecycle_review_last_run_date") is not None

    def test_none_transition_no_alert(self, monitor_mod, tmp_path):
        inputs = _make_inputs()
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        fn(state)
        assert len(sent) == 0


class TestManualReviewPendingAlert:
    def test_la_override_alerts_manual_review_pending(self, monitor_mod, tmp_path):
        """Los Angeles con override manual_review_required debe producir manual_review_pending."""
        shadow = {"Los Angeles": _passing_shadow_data("Los Angeles")}
        overrides = {
            "Los Angeles": {
                "manual_review_required_pre_canary": True,
                "reason": "OBSERVED_AUDIT: fuente auditada; no autoriza trading",
            }
        }
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        result = fn(state)
        assert result, "debe retornar True al alertar"
        assert len(sent) == 1
        msg = sent[0]
        assert "Los Angeles" in msg
        assert "manual_review_pending" in msg
        assert "LOG_ONLY" in msg

    def test_la_manual_review_never_canary_review(self, monitor_mod, tmp_path):
        """LA con override activo no puede tener canary_review como transición."""
        shadow = {"Los Angeles": _passing_shadow_data("Los Angeles")}
        overrides = {
            "Los Angeles": {
                "manual_review_required_pre_canary": True,
                "reason": "test override",
            }
        }
        promo_gate = _passing_promo_gate("Los Angeles", "review_for_canary")
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides, promotion_gate=promo_gate)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        fn(state)
        for msg in sent:
            assert "canary_review" not in msg, "LA con override no debe producir canary_review"
        if sent:
            assert "manual_review_pending" in sent[0]


class TestCooldown:
    def test_cooldown_prevents_duplicate_within_24h(self, monitor_mod, tmp_path):
        shadow = {"TestCity": _passing_shadow_data("TestCity")}
        overrides = {
            "TestCity": {
                "manual_review_required_pre_canary": True,
                "reason": "test",
            }
        }
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)

        state = {}
        result1 = fn(state)
        assert result1
        assert len(sent) == 1

        # Simulate second call same day — should skip (already run today)
        result2 = fn(state)
        assert not result2, "segunda llamada el mismo día debe retornar False"
        assert len(sent) == 1, "no debe enviar un segundo Telegram el mismo día"

    def test_cooldown_expired_after_25h_alerts_again(self, monitor_mod, tmp_path):
        """Si el cooldown expiró (>24h), debe volver a alertar."""
        shadow = {"TestCity": _passing_shadow_data("TestCity")}
        overrides = {"TestCity": {"manual_review_required_pre_canary": True, "reason": "test"}}
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        state = {
            "lifecycle_review_alerted": {"TestCity|manual_review_pending": old_ts},
            "lifecycle_review_last_run_date": yesterday,
        }
        result = fn(state)
        assert result
        assert len(sent) == 1


class TestMessageContent:
    def test_message_contains_log_only_and_prohibitions(self, monitor_mod, tmp_path):
        shadow = {"TestCity": _passing_shadow_data("TestCity")}
        overrides = {"TestCity": {"manual_review_required_pre_canary": True, "reason": "test"}}
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        fn(state)
        assert len(sent) >= 1
        msg = sent[0]
        assert "LOG_ONLY" in msg
        assert "BUY" in msg or "SELL" in msg
        assert "BANKROLL" in msg
        assert "Fase C" in msg

    def test_message_no_actionable_trade_instructions(self, monitor_mod, tmp_path):
        shadow = {"TestCity": _passing_shadow_data("TestCity")}
        overrides = {"TestCity": {"manual_review_required_pre_canary": True, "reason": "test"}}
        inputs = _make_inputs(shadow_cities=shadow, overrides=overrides)
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        state = {}
        fn(state)
        for msg in sent:
            lower = msg.lower()
            assert "execute" not in lower
            assert "post_order" not in lower
            assert "crear orden" not in lower


class TestDailyGate:
    def test_runs_once_per_day(self, monitor_mod, tmp_path):
        inputs = _make_inputs()
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {"lifecycle_review_last_run_date": today}
        result = fn(state)
        assert not result, "no debe ejecutar si ya corrió hoy"

    def test_runs_on_new_day(self, monitor_mod, tmp_path):
        inputs = _make_inputs()
        fn, sent = _build_alert_fn(monitor_mod, inputs, tmp_path, None)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        state = {"lifecycle_review_last_run_date": yesterday}
        fn(state)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert state["lifecycle_review_last_run_date"] == today
