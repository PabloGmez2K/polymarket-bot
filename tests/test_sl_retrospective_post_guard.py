import importlib.util
from pathlib import Path


def load_sl_retrospective():
    path = Path(__file__).resolve().parents[1] / "tools" / "sl_retrospective.py"
    spec = importlib.util.spec_from_file_location("sl_retrospective_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phase_summary(*, false_exits, correct, pending, false_with, false_without, protected_with, protected_without, main_false, main_correct, main_pending, intra_false, intra_correct, intra_pending):
    return {
        "F3": {
            "n_right": false_exits,
            "n_wrong": correct,
            "n_unknown": pending,
            "n_resolved": false_exits + correct,
            "accuracy_pct": false_exits / (false_exits + correct) * 100.0,
            "false_exit_with_sl_total": false_with,
            "false_exit_without_sl_best_total": false_without,
            "protected_with_sl_total": protected_with,
            "protected_without_sl_best_total": protected_without,
            "by_type": {
                "stop_loss": {
                    "n": main_false + main_correct + main_pending,
                    "n_right": main_false,
                    "n_wrong": main_correct,
                    "n_unknown": main_pending,
                    "n_resolved": main_false + main_correct,
                    "accuracy_pct": main_false / (main_false + main_correct) * 100.0 if main_false + main_correct else None,
                },
                "stop_loss_intra": {
                    "n": intra_false + intra_correct + intra_pending,
                    "n_right": intra_false,
                    "n_wrong": intra_correct,
                    "n_unknown": intra_pending,
                    "n_resolved": intra_false + intra_correct,
                    "accuracy_pct": intra_false / (intra_false + intra_correct) * 100.0 if intra_false + intra_correct else None,
                },
            },
        }
    }


def test_post_guard_live_shape_is_watch_not_opus_ready():
    sl = load_sl_retrospective()
    phases = phase_summary(
        false_exits=4,
        correct=4,
        pending=1,
        false_with=-2.29,
        false_without=4.78,
        protected_with=-1.52,
        protected_without=-1.52,
        main_false=2,
        main_correct=0,
        main_pending=1,
        intra_false=2,
        intra_correct=4,
        intra_pending=0,
    )

    status = sl._post_guard_status(phases)
    lines = sl._current_config_verdict_lines(phases)
    text = "\n".join(lines)

    assert status["status"] == "WATCH_RISK_INCREASING"
    assert status["net_vs_best_seen"] == -7.07
    assert "WATCH_RISK_INCREASING" in text
    assert "next_trigger: Opus si post_guard llega a 10 resueltos (2 faltan)" in text
    assert "no autoriza cambio de SL" in text


def test_post_guard_escalates_only_after_explicit_threshold():
    sl = load_sl_retrospective()
    phases = phase_summary(
        false_exits=6,
        correct=4,
        pending=0,
        false_with=-4.0,
        false_without=5.0,
        protected_with=-2.0,
        protected_without=-2.0,
        main_false=3,
        main_correct=2,
        main_pending=0,
        intra_false=3,
        intra_correct=2,
        intra_pending=0,
    )

    status = sl._post_guard_status(phases)

    assert status["status"] == "ESCALATE_OPUS_READY"
    assert any("post_guard resueltos=10" in reason for reason in status["reasons"])
