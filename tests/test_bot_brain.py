from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.bot_brain import build_brain_report, main, render_markdown


NOW = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_jsonl(
        data_dir / "cycles_history.jsonl",
        [
            {
                "cycle_number": 367,
                "logic_cycle_number": 20,
                "timestamp_utc": "2026-05-21T08:00:00+00:00",
                "mode": "REAL",
                "scan": {"markets_evaluated": 2, "with_edge": 1},
                "buys": [{"city": "Shanghai", "side": "YES"}],
                "scanned_markets": [{"city": "Shanghai", "question": "Shanghai temp"}],
            }
        ],
    )
    _write_jsonl(
        data_dir / "funnel_observability_log_only.jsonl",
        [
            {
                "cycle_number": 367,
                "logic_cycle_number": 20,
                "ts_utc": "2026-05-21T08:00:00+00:00",
                "discovered_markets_unique": 330,
                "prefiltered": 2,
                "edge": 1,
                "shadow_edge": 0,
                "selected": 1,
                "real_buy": 1,
            }
        ],
    )
    _write_json(data_dir / "funnel_observability_latest.json", {"cycle_number": 367})
    _write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [
            {
                "cycle_id": "2026-05-21T08:00",
                "eval_key": "Shanghai|2026-05-22|at_or_above|30||C",
                "ts_utc": "2026-05-21T08:00:01+00:00",
                "city": "Shanghai",
                "date_iso": "2026-05-22",
                "condition": "at_or_above",
                "would_buy": True,
            },
            {
                "cycle_id": "2026-05-21T08:00",
                "eval_key": "orphan-eval",
                "ts_utc": "2026-05-21T08:00:02+00:00",
                "city": "Milan",
                "would_buy": False,
            },
        ],
    )
    _write_jsonl(
        data_dir / "blocked_signals_resolutions.jsonl",
        [
            {
                "match_key": "Shanghai|2026-05-22|at_or_above|30||C",
                "city": "Shanghai",
                "date": "2026-05-22",
                "condition": "at_or_above",
                "bot_evaluation_join_status": "captured",
                "win_for_trader": True,
            },
            {
                "match_key": "orphan-resolution",
                "city": "Paris",
                "date": "2026-05-22",
            },
        ],
    )
    _write_json(data_dir / "trade_lifecycle.json", {"records": []})
    _write_jsonl(tmp_path / "agent_events.jsonl", [{"timestamp": "2026-05-21T09:00:00+00:00", "title": "Shanghai note"}])
    (tmp_path / "CONTEXTO.md").write_text("Shanghai live context note\n", encoding="utf-8")
    (tmp_path / "HISTORIAL_SESIONES.md").write_text("Session mentions Shanghai\n", encoding="utf-8")
    return repo_root, data_dir


def test_city_query_connects_artifacts(tmp_path: Path) -> None:
    repo_root, data_dir = _fixture(tmp_path)

    report = build_brain_report("city:Shanghai", "14d", repo_root=repo_root, data_dir=data_dir, now=NOW)

    assert report["log_only"] is True
    assert report["trading_authorization"] == "NO_ACTION"
    assert report["results"]["matches_found"] is True
    assert report["results"]["cycles_count"] == 1
    assert report["results"]["evaluations_count"] == 1
    assert report["results"]["blocked_resolutions_count"] == 1
    assert report["connections"]["eval_resolution_join"]["joined_count"] == 1
    assert any(pointer["artifact"] == "cycles_history" for pointer in report["evidence_pointers"])


def test_cycle_query_links_cycle_and_funnel(tmp_path: Path) -> None:
    repo_root, data_dir = _fixture(tmp_path)

    report = build_brain_report("cycle:367", "7d", repo_root=repo_root, data_dir=data_dir, now=NOW)

    assert report["results"]["matches_found"] is True
    assert report["results"]["cycles_count"] == 1
    assert report["results"]["funnel_records_count"] == 1
    assert report["results"]["funnel_records"][0]["discovered_markets_unique"] == 330


def test_eval_key_join(tmp_path: Path) -> None:
    repo_root, data_dir = _fixture(tmp_path)
    key = "Shanghai|2026-05-22|at_or_above|30||C"

    report = build_brain_report(f"eval_key:{key}", "7d", repo_root=repo_root, data_dir=data_dir, now=NOW)

    assert report["results"]["matches_found"] is True
    assert report["results"]["join_status"] == "joined"
    assert report["results"]["evaluation"]["city"] == "Shanghai"
    assert report["results"]["resolution"]["bot_evaluation_join_status"] == "captured"


def test_missing_artifacts_and_no_match(tmp_path: Path) -> None:
    repo_root = tmp_path
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_jsonl(data_dir / "cycles_history.jsonl", [])

    report = build_brain_report("city:Nowhere", "7d", repo_root=repo_root, data_dir=data_dir, now=NOW)

    assert "bot_signal_evaluations" in report["missing_artifacts"]
    assert report["no_match"] is True
    assert report["results"]["matches_found"] is False


def test_markdown_output(tmp_path: Path, capsys) -> None:
    repo_root, data_dir = _fixture(tmp_path)
    report = build_brain_report("overview", "7d", repo_root=repo_root, data_dir=data_dir, now=NOW)

    markdown = render_markdown(report)

    assert "# Bot Brain v0" in markdown
    assert "LOG_ONLY / NO_ACTION" in markdown
    assert "Evidence Pointers" in markdown

    exit_code = main(
        [
            "--scope",
            "overview",
            "--format",
            "md",
            "--repo-root",
            str(repo_root),
            "--data-dir",
            str(data_dir),
            "--now",
            NOW.isoformat(),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# Bot Brain v0" in captured.out
