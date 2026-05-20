from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.city_universe_audit import build_report, render_markdown


NOW = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _base_fixture(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    repo_data = tmp_path / "repo_data"
    repo_docs = tmp_path / "docs"
    repo_data.mkdir()
    repo_docs.mkdir()
    monkeypatch.setattr("tools.city_universe_audit.REPO_ROOT", tmp_path)

    (tmp_path / "bot.py").write_text(
        'ACTIVE_TRADING_CITIES = {city.strip() for city in os.getenv("ACTIVE_TRADING_CITIES", "ActiveDead").split(",")}\n'
        'CANARY_TRADING_CITIES = {city.strip() for city in os.getenv("CANARY_TRADING_CITIES", "").split(",")}\n'
        'BLOCKED_CITIES = {city.strip().lower() for city in os.getenv("BLOCKED_CITIES", "").split(",")}\n',
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "source_onboarding.json").write_text(
        json.dumps(
            {
                "cities": [
                    {
                        "city": "ShadowGood",
                        "source_fidelity_status": "SOURCE_MATCH_CONFIRMED",
                        "mapping_status": "MAPPING_FULL",
                    },
                    {
                        "city": "MismatchCity",
                        "source_fidelity_status": "SOURCE_MISMATCH",
                        "mapping_status": "MAPPING_FULL",
                    },
                    {
                        "city": "NoDataCity",
                        "source_fidelity_status": "SOURCE_MATCH_CONFIRMED",
                        "mapping_status": "MAPPING_FULL",
                    },
                    {
                        "city": "ActiveDead",
                        "source_fidelity_status": "SOURCE_MATCH_CONFIRMED",
                        "mapping_status": "MAPPING_FULL",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "city_promotion_gate.json").write_text(
        json.dumps({"review_queue": [{"city": "ShadowGood", "gate_status": "review_runtime_policy_gate"}]}),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "city_lifecycle_review_latest.md").write_text(
        "\n".join(
            [
                "| City | Stage | Transition | Override | Notes |",
                "| --- | --- | --- | --- | --- |",
                "| ShadowGood | shadow | canary_review | - | T2 gates pass |",
                "| ActiveDead | active | none | - | already active |",
            ]
        ),
        encoding="utf-8",
    )
    return data_dir


def _write_policy_env(data_dir: Path, active: str = "ActiveDead", read_capture: str = "1") -> None:
    (data_dir / "policy_env_snapshot.json").write_text(
        json.dumps(
            {
                "variables": {
                    "ACTIVE_TRADING_CITIES": active,
                    "CANARY_TRADING_CITIES": "",
                    "BLOCKED_CITIES": "",
                    "READ_BOT_EVAL_CAPTURE": read_capture,
                }
            }
        ),
        encoding="utf-8",
    )


def test_shadow_would_buy_candidate_promotes(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    evals = [
        {
            "city": "ShadowGood",
            "timestamp": "2026-05-19T00:00:00+00:00",
            "would_buy": True,
            "evaluation_source": "shadow",
            "edge": 0.12,
            "condition": "exact",
        }
        for _ in range(7)
    ]
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", evals)

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "ShadowGood")

    assert row["would_buy_shadow_count"] == 7
    assert row["recommended_action"] == "promote_to_canary_candidate"


def test_active_with_zero_evals_low_confidence_is_watch_not_demote(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "ActiveDead")

    assert row["current_mode"] == "active"
    assert row["total_evals_14d"] == 0
    assert report["report_context"]["confidence_banner"] == "LOW_CONFIDENCE_WINDOW"
    assert row["recommended_action"] == "active_throughput_watch"


def test_active_with_valid_window_and_regression_gets_demotion_review(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    _write_policy_env(data_dir, active="ActiveDead", read_capture="1")
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])
    (tmp_path / "data" / "city_promotion_gate.json").write_text(
        json.dumps(
            {
                "review_queue": [
                    {
                        "city": "ActiveDead",
                        "gate_status": "review_active_regression",
                        "recommendation": "demotion_review",
                        "drift_flags": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(data_dir, 21, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "ActiveDead")

    assert report["report_context"]["confidence_banner"] == "OK"
    assert row["recommended_action"] == "demotion_review_candidate"


def test_source_mismatch_blocks_promotion_despite_high_score(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    evals = [
        {
            "city": "MismatchCity",
            "timestamp": "2026-05-19T00:00:00+00:00",
            "would_buy": True,
            "evaluation_source": "shadow",
            "edge": 0.20,
            "condition": "exact",
        }
        for _ in range(8)
    ]
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", evals)

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "MismatchCity")

    assert row["score"] >= 10
    assert "source_critical" in row["risk_flags"]
    assert row["recommended_action"] == "source_blocked"


def test_city_without_data_has_none_confidence(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "NoDataCity")
    top = [r["city"] for r in report["ranked_cities"] if r["recommended_action"] == "promote_to_canary_candidate"]

    assert row["data_confidence"] == "none"
    assert row["scores"]["condition_compat"] == 0
    assert "NO_DATA_FOR_CONDITION_COMPAT" in row["reason_codes"]
    assert "NoDataCity" not in top


def test_markdown_drift_word_without_drift_column_flag_does_not_warn(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    (tmp_path / "data" / "city_promotion_gate.json").unlink()
    (tmp_path / "docs" / "city_promotion_gate_latest.md").write_text(
        "\n".join(
            [
                "| City | Gate | Priority | Runtime policy | Cross policy | Drift | Recommendation | Bottleneck |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| ActiveDead | observe_runtime_canary | watch | active | active | - | observe_runtime_canary | drift mentioned in text |",
            ]
        ),
        encoding="utf-8",
    )
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "ActiveDead")

    assert "drift_warning" not in row["risk_flags"]


def test_markdown_explicit_drift_column_sets_warning(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    (tmp_path / "data" / "city_promotion_gate.json").unlink()
    (tmp_path / "docs" / "city_promotion_gate_latest.md").write_text(
        "\n".join(
            [
                "| City | Gate | Priority | Runtime policy | Cross policy | Drift | Recommendation | Bottleneck |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| ActiveDead | observe_runtime_canary | watch | active | shadow | policy_divergence | audit_runtime_drift | canary_measurement |",
            ]
        ),
        encoding="utf-8",
    )
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])

    report = build_report(data_dir, 14, "low", NOW)
    row = next(r for r in report["ranked_cities"] if r["city"] == "ActiveDead")

    assert "drift_warning" in row["risk_flags"]


def test_jsonl_utf8_bom_first_line_is_parsed(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    row = {
        "city": "ShadowGood",
        "timestamp": "2026-05-19T00:00:00+00:00",
        "would_buy": True,
        "evaluation_source": "shadow",
        "edge": 0.12,
        "condition": "exact",
    }
    (data_dir / "bot_signal_evaluations.jsonl").write_bytes(
        b"\xef\xbb\xbf" + (json.dumps(row) + "\n").encode("utf-8")
    )

    report = build_report(data_dir, 14, "low", NOW)
    city = next(r for r in report["ranked_cities"] if r["city"] == "ShadowGood")

    assert city["total_evals_14d"] == 1
    assert not any("bot_signal_evaluations invalid JSON" in warning for warning in report["warnings"])


def test_markdown_contains_required_sections(tmp_path, monkeypatch):
    data_dir = _base_fixture(tmp_path, monkeypatch)
    _write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [
            {
                "city": "ShadowGood",
                "timestamp": "2026-05-19T00:00:00+00:00",
                "would_buy": True,
                "evaluation_source": "shadow",
                "edge": 0.15,
                "condition": "exact",
            }
            for _ in range(7)
        ],
    )

    report = build_report(data_dir, 14, "low", NOW)
    md = render_markdown(report)

    assert "## Ranking" in md
    assert "## Top 5 Candidatas A Canary" in md
    assert "## Bottom Active Cities" in md
    assert "ShadowGood" in md
    assert "ActiveDead" in md
