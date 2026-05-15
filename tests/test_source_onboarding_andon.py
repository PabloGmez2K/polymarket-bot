"""Tests focales para Source Onboarding Andon v1 (LOG_ONLY)."""

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "source_onboarding_andon.py"


def load_module():
    spec = importlib.util.spec_from_file_location("source_onboarding_andon", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def source_payload(*records):
    return {
        "generated_at": "2026-05-15T08:00:00+00:00",
        "log_only": True,
        "disclaimer": "LOG_ONLY. No BUY, SELL, or SKIP decisions.",
        "summary": {"n_candidates": len(records)},
        "cities": list(records),
    }


def city_record(**overrides):
    record = {
        "city": "Chongqing",
        "primary_status": "SOURCE_CONFIRMED_WAITING_SHADOW",
        "source_audit_status": "READY_FOR_HUMAN_SOURCE_AUDIT",
        "shadow_evidence_status": "SHADOW_EVIDENCE_PARTIAL",
        "observation_pipeline_status": "OBSERVATION_WAITING_EVIDENCE",
        "priority_score": 1.7,
        "missing_inputs": ["noaa_station_id", "shadow_cycles_or_edges"],
        "operational_action": "NO_ACTION / LOG_ONLY",
        "trader_report": {
            "trader_wins": 24,
            "trader_n": 25,
            "trader_wr_pct": 96.0,
        },
        "shadow": {
            "cycles_seen": 9,
            "edge_hits": 1,
            "best_edge_pct": 28.8,
        },
    }
    record.update(overrides)
    return record


def args_for(module, tmp_path: Path):
    return module.parse_args(
        [
            "--source-json",
            str(tmp_path / "source_onboarding.json"),
            "--state",
            str(tmp_path / "source_onboarding" / "andon_state.json"),
            "--output",
            str(tmp_path / "source_onboarding" / "andon_latest.json"),
            "--agent-events",
            str(tmp_path / "agent_events.jsonl"),
            "--now",
            "2026-05-15T09:00:00+00:00",
        ]
    )


def test_no_alert_when_no_changes(tmp_path):
    module = load_module()
    write_json(tmp_path / "source_onboarding.json", source_payload(city_record()))
    args = args_for(module, tmp_path)

    first = module.build_run(args, env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})
    second = module.build_run(args, env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})

    assert first["should_notify"] is True
    assert second["should_notify"] is False
    assert second["telegram_message"] is None


def test_alert_new_human_source_audit_ready(tmp_path):
    module = load_module()
    write_json(
        tmp_path / "source_onboarding" / "andon_state.json",
        {
            "schema_version": module.SCHEMA_VERSION,
            "cities": {
                "Chongqing": {
                    "primary_status": "WAITING_EVIDENCE",
                    "source_audit_status": "SOURCE_TEXT_MISSING",
                    "priority_tier": "LOW",
                    "shadow_evidence_status": "SHADOW_EVIDENCE_PARTIAL",
                }
            },
        },
    )
    write_json(tmp_path / "source_onboarding.json", source_payload(city_record()))

    result = module.build_run(args_for(module, tmp_path), env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})

    assert result["should_notify"] is True
    assert "NEW_HUMAN_SOURCE_AUDIT_READY" in result["notification_reasons"]
    assert "NO_ACTION / LOG_ONLY" in result["telegram_message"]
    assert "Do not add to active/canary" in result["telegram_message"]


def test_alert_source_confirmed_waiting_shadow(tmp_path):
    module = load_module()
    write_json(
        tmp_path / "source_onboarding" / "andon_state.json",
        {
            "schema_version": module.SCHEMA_VERSION,
            "cities": {
                "Jeddah": {
                    "primary_status": "WAITING_EVIDENCE",
                    "source_audit_status": "READY_FOR_HUMAN_SOURCE_AUDIT",
                    "priority_tier": "MEDIUM",
                    "shadow_evidence_status": "SHADOW_EVIDENCE_PARTIAL",
                }
            },
        },
    )
    record = city_record(
        city="Jeddah",
        trader_report={"trader_wins": 7, "trader_n": 8, "trader_wr_pct": 87.5},
        shadow={"cycles_seen": 6, "edge_hits": 4, "best_edge_pct": 30.2},
    )
    write_json(tmp_path / "source_onboarding.json", source_payload(record))

    result = module.build_run(args_for(module, tmp_path), env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})

    assert result["should_notify"] is True
    assert "SOURCE_CONFIRMED_WAITING_SHADOW" in result["notification_reasons"]
    assert "wait for stronger shadow" in result["telegram_message"]


def test_source_ambiguous_and_mismatch_escalate_opus(tmp_path):
    module = load_module()
    ambiguous = city_record(city="X", primary_status="SOURCE_AMBIGUOUS", source_audit_status="SOURCE_AMBIGUOUS")
    mismatch = city_record(city="Y", primary_status="SOURCE_MISMATCH", source_audit_status="SOURCE_MISMATCH")
    write_json(tmp_path / "source_onboarding.json", source_payload(ambiguous, mismatch))

    result = module.build_run(args_for(module, tmp_path), env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})

    assert result["should_notify"] is True
    assert "SOURCE_AMBIGUOUS" in result["notification_reasons"]
    assert "SOURCE_MISMATCH" in result["notification_reasons"]
    assert result["telegram_message"].count("ESCALATE_OPUS") == 2
    assert "No BUY/SELL/SKIP" in result["telegram_message"]


def test_observation_review_ready_on_shadow_threshold_cross(tmp_path):
    module = load_module()
    write_json(
        tmp_path / "source_onboarding" / "andon_state.json",
        {
            "schema_version": module.SCHEMA_VERSION,
            "cities": {
                "Chongqing": {
                    "primary_status": "SOURCE_CONFIRMED_WAITING_SHADOW",
                    "source_audit_status": "READY_FOR_HUMAN_SOURCE_AUDIT",
                    "priority_tier": "MEDIUM",
                    "shadow_evidence_status": "SHADOW_EVIDENCE_PARTIAL",
                }
            },
        },
    )
    record = city_record(
        primary_status="READY_FOR_HUMAN_SOURCE_AUDIT",
        shadow_evidence_status="SHADOW_EVIDENCE_READY",
        observation_pipeline_status="OBSERVATION_READY",
        shadow={"cycles_seen": 10, "edge_hits": 1, "best_edge_pct": 28.8},
    )
    write_json(tmp_path / "source_onboarding.json", source_payload(record))

    result = module.build_run(args_for(module, tmp_path), env={"SOURCE_ONBOARDING_ANDON_ENABLED": "true"})

    assert result["should_notify"] is True
    assert "OBSERVATION_REVIEW_READY" in result["notification_reasons"]
    assert "Human/Opus review required" in result["telegram_message"]


def test_kill_switch_disables_hook(tmp_path):
    module = load_module()
    write_json(tmp_path / "source_onboarding.json", source_payload(city_record()))

    result = module.build_run(args_for(module, tmp_path), env={"SOURCE_ONBOARDING_ANDON_ENABLED": "false"})

    assert result["ok"] is True
    assert result["status"] == "skipped"
    assert result["reason"] == "env_off"
    assert result["should_notify"] is False


def test_bot_hook_has_kill_switch_and_order():
    src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
    assert "SOURCE_ONBOARDING_ANDON_ENABLED" in src
    assert "def maybe_run_source_onboarding_andon(" in src

    obs_start = src.find("def run_observability_alerts(")
    obs_end = src.find("\ndef ", obs_start + 1)
    obs_body = src[obs_start:obs_end] if obs_end != -1 else src[obs_start:]

    pos_scanner = obs_body.find("maybe_run_source_onboarding_scanner(state)")
    pos_andon = obs_body.find("maybe_run_source_onboarding_andon()")
    pos_digest = obs_body.find("maybe_run_city_intelligence_digest_alert(state)")

    assert pos_scanner != -1
    assert pos_andon != -1
    assert pos_digest != -1
    assert pos_scanner < pos_andon < pos_digest
