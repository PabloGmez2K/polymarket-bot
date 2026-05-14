from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = REPO_ROOT / "tools" / "trader_signals_full_snapshot_collector.py"
REPORT_PATH = REPO_ROOT / "tools" / "traders_operational_questions_report.py"


@contextmanager
def local_tmp_dir():
    path = REPO_ROOT / f"_tmp_trader_ops_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(REPO_ROOT / "tools"))
        except ValueError:
            pass
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def sample_signals(generated: str = "2026-05-13T08:00:00+00:00") -> dict:
    return {
        "generated": generated,
        "signals": [
            {
                "trader": "Entire-Hood",
                "title": "Will the highest temperature in Houston be 80°F on May 13?",
                "city": "Houston",
                "condition": "at_or_above",
                "date": "2026-05-13",
                "temp": 80,
                "unit": "F",
                "outcome": "Yes",
                "avg_price": 0.42,
                "cur_price": 0.55,
                "match_key": "Houston|2026-05-13|at_or_above|80|F",
                "has_consensus": True,
                "consensus_with": ["Thrifty-Original"],
            },
            {
                "trader": "Thrifty-Original",
                "city": "Seattle",
                "condition": "exact",
                "date": "2026-05-13",
                "temp": 57,
                "unit": "F",
                "outcome": "No",
                "avg_price": 0.31,
                "cur_price": 0.80,
                "match_key": "Seattle|2026-05-13|exact|57|F",
                "has_consensus": False,
                "consensus_with": [],
            },
        ],
    }


def report_args(module, tmp_dir: Path, *, snapshots: Path | None = None, lifecycle: Path | None = None):
    signals = tmp_dir / "signals.json"
    blocked = tmp_dir / "blocked.jsonl"
    fallback = tmp_dir / "missing_fallback.jsonl"
    lifecycle_path = lifecycle or (tmp_dir / "trade_lifecycle.json")
    write_json(signals, sample_signals())
    write_jsonl(
        blocked,
        [
            {"city": "Seattle", "trader": "Thrifty-Original", "resolved": True, "win_for_trader": True},
            {"city": "Seattle", "trader": "Thrifty-Original", "resolved": True, "win_for_trader": True},
            {"city": "Seattle", "trader": "Entire-Hood", "resolved": True, "win_for_trader": True},
        ],
    )
    if not lifecycle_path.exists():
        write_json(lifecycle_path, {"records": []})
    return module.parse_args(
        [
            "--signals",
            str(signals),
            "--snapshots",
            str(snapshots or (tmp_dir / "snapshots.jsonl")),
            "--blocked-resolutions",
            str(blocked),
            "--blocked-fallback",
            str(fallback),
            "--trade-lifecycle",
            str(lifecycle_path),
            "--json-output",
            str(tmp_dir / "report.json"),
            "--md-output",
            str(tmp_dir / "report.md"),
            "--dry-run",
        ]
    )


def test_collector_deduplicates_same_generated_snapshot():
    module = load_module(COLLECTOR_PATH, "trader_signals_full_snapshot_collector")
    with local_tmp_dir() as tmp_dir:
        signals = tmp_dir / "signals.json"
        output = tmp_dir / "snapshots.jsonl"
        write_json(signals, sample_signals())
        args = module.parse_args(
            [
                "--signals",
                str(signals),
                "--output",
                str(output),
                "--snapshot-at",
                "2026-05-13T08:05:00+00:00",
            ]
        )

        first = module.build_run(args)
        second = module.build_run(args)

        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        assert first["status"] == "completed"
        assert second["status"] == "skipped"
        assert second["reason"] == "duplicate_snapshot"
        assert len(rows) == 2


def test_collector_normalizes_minimum_signal_fields():
    module = load_module(COLLECTOR_PATH, "trader_signals_full_snapshot_collector")
    with local_tmp_dir() as tmp_dir:
        signals = tmp_dir / "signals.json"
        output = tmp_dir / "snapshots.jsonl"
        write_json(signals, sample_signals())
        args = module.parse_args(
            [
                "--signals",
                str(signals),
                "--output",
                str(output),
                "--run-id",
                "fixture-run",
                "--snapshot-at",
                "2026-05-13T08:05:00+00:00",
            ]
        )

        result = module.build_run(args)
        row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

        assert result["written_rows"] == 2
        assert row["schema_version"] == module.SCHEMA_VERSION
        assert row["run_id"] == "fixture-run"
        assert row["source_generated_at"] == "2026-05-13T08:00:00+00:00"
        assert row["trader"] == "Entire-Hood"
        assert row["city"] == "Houston"
        assert row["condition"] == "at_or_above"
        assert row["avg_price"] == 0.42
        assert row["cur_price"] == 0.55
        assert row["match_key"] == "Houston|2026-05-13|at_or_above|80|F"
        assert row["has_consensus"] is True
        assert row["consensus_with"] == ["Thrifty-Original"]


def test_report_marks_activity_by_hour_no_without_enough_snapshots():
    module = load_module(REPORT_PATH, "traders_operational_questions_report")
    with local_tmp_dir() as tmp_dir:
        payload = module.build_report(report_args(module, tmp_dir))
        hourly = payload["questions"][0]

        assert hourly["answerability"] == "NO"
        assert hourly["confidence"] == "insufficient_data"
        assert payload["tables"]["top_activity_hours_utc"] == []


def test_report_calculates_hourly_activity_from_new_snapshot_appearances():
    module = load_module(REPORT_PATH, "traders_operational_questions_report")
    with local_tmp_dir() as tmp_dir:
        snapshots = tmp_dir / "snapshots.jsonl"
        write_jsonl(
            snapshots,
            [
                {
                    "row_type": "signal",
                    "snapshot_at": "2026-05-13T08:00:00+00:00",
                    "trader": "Entire-Hood",
                    "city": "Houston",
                    "signal_id": "Houston|2026-05-13|at_or_above|80|F",
                    "match_key": "Houston|2026-05-13|at_or_above|80|F",
                },
                {
                    "row_type": "signal",
                    "snapshot_at": "2026-05-13T09:00:00+00:00",
                    "trader": "Entire-Hood",
                    "city": "Houston",
                    "signal_id": "Houston|2026-05-13|at_or_above|80|F",
                    "match_key": "Houston|2026-05-13|at_or_above|80|F",
                },
                {
                    "row_type": "signal",
                    "snapshot_at": "2026-05-13T09:00:00+00:00",
                    "trader": "Thrifty-Original",
                    "city": "Seattle",
                    "signal_id": "Seattle|2026-05-13|exact|57|F",
                    "match_key": "Seattle|2026-05-13|exact|57|F",
                },
            ],
        )

        payload = module.build_report(report_args(module, tmp_dir, snapshots=snapshots))
        hourly = payload["questions"][0]

        assert hourly["answerability"] == "YES"
        assert payload["tables"]["top_activity_hours_utc"] == [
            {"hour_utc": "08:00Z", "new_signal_appearances": 1},
            {"hour_utc": "09:00Z", "new_signal_appearances": 1},
        ]
        assert payload["tables"]["top_cities_by_snapshot_activity"][0]["city"] == "Houston"


def test_report_marks_bot_gap_low_bot_n_as_insufficient_n():
    module = load_module(REPORT_PATH, "traders_operational_questions_report")
    with local_tmp_dir() as tmp_dir:
        lifecycle = tmp_dir / "trade_lifecycle.json"
        write_json(
            lifecycle,
            {
                "records": [
                    {
                        "city": "Seattle",
                        "close_context": {"close_action": "LOSS_TOTAL"},
                    }
                ]
            },
        )

        payload = module.build_report(report_args(module, tmp_dir, lifecycle=lifecycle))
        rows = payload["tables"]["trader_winning_bot_gap"]
        seattle = next(row for row in rows if row["city"] == "Seattle")

        assert seattle["trader_wr_pct"] == 100.0
        assert seattle["bot_n"] == 1
        assert seattle["classification"] == "TRADER_WINNING_BOT_INSUFFICIENT_N"
