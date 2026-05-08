from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "db_throughput_report.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("db_throughput_report", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        INSERT INTO schema_version (version, applied_at) VALUES (1, '2026-05-01T00:00:00Z');

        CREATE TABLE cycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            logic_cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            bot_version TEXT,
            logic_series TEXT,
            mode TEXT,
            markets_evaluated INTEGER,
            buys_count INTEGER,
            exposure_after REAL,
            budget_left REAL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            city TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            forecast_high_c REAL,
            question TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE forecast_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            city TEXT NOT NULL,
            target_date TEXT NOT NULL,
            forecast_high_c REAL,
            source TEXT,
            payload_json TEXT NOT NULL
        );
        """
    )
    cycles = [
        (
            1,
            "2026-05-01T09:00:00Z",
            10,
            0,
            {"scan": {"markets_evaluated": 10, "with_edge": 2, "selected": 1, "condition_filtered": 3}},
        ),
        (
            2,
            "2026-05-01T12:00:00Z",
            20,
            1,
            {"scan": {"markets_evaluated": 20, "with_edge": 4, "selected": 2, "condition_filtered": 5}},
        ),
        (
            3,
            "2026-05-02T12:00:00Z",
            15,
            0,
            {"scan": {"markets_evaluated": 15, "with_edge": 3, "selected": 1, "condition_filtered": 4}},
        ),
    ]
    for cycle_number, ts_utc, evaluated, buys, payload in cycles:
        conn.execute(
            """
            INSERT INTO cycle_events
                (cycle_number, logic_cycle_number, ts_utc, bot_version, logic_series, mode,
                 markets_evaluated, buys_count, exposure_after, budget_left, payload_json)
            VALUES (?, ?, ?, 'v-test', '10.6', 'REAL', ?, ?, 0, 0, ?)
            """,
            (cycle_number, cycle_number, ts_utc, evaluated, buys, json.dumps(payload)),
        )

    snapshots = [
        (
            1,
            "2026-05-01T09:00:00Z",
            "Paris",
            "2026-05-01",
            20.0,
            "Will the highest temperature in Paris be exactly 20C on May 1?",
            {},
        ),
        (
            1,
            "2026-05-01T09:00:00Z",
            "Paris",
            "2026-05-01",
            20.0,
            "Will the highest temperature in Paris be at or above 20C on May 1?",
            {},
        ),
        (
            2,
            "2026-05-01T12:00:00Z",
            "London",
            "2026-05-01",
            18.0,
            "Will the highest temperature in London be between 17C and 19C on May 1?",
            {},
        ),
        (
            3,
            "2026-05-02T12:00:00Z",
            "Seoul",
            "2026-05-02",
            16.0,
            "Will the highest temperature in Seoul be at most 16C on May 2?",
            {},
        ),
    ]
    for row in snapshots:
        conn.execute(
            """
            INSERT INTO market_snapshots
                (cycle_number, ts_utc, city, date_iso, forecast_high_c, question, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (*row[:-1], json.dumps(row[-1])),
        )
    conn.commit()
    conn.close()


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_json_report_groups_by_slot_and_buy_rate(tmp_path):
    db = tmp_path / "polymarket.db"
    create_db(db)

    result = run_cli("--db", str(db), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    slots = {row["slot_utc"]: row for row in payload["cycles"]["by_slot_utc"]}
    assert slots[9]["cycles"] == 1
    assert slots[9]["markets_evaluated"] == 10
    assert slots[9]["buys"] == 0
    assert slots[12]["cycles"] == 2
    assert slots[12]["markets_evaluated"] == 35
    assert slots[12]["buys"] == 1
    assert slots[12]["buy_rate_per_market_evaluated"] == round(1 / 35, 4)


def test_condition_inference_and_city_snapshots(tmp_path):
    db = tmp_path / "polymarket.db"
    create_db(db)
    module = load_tool_module()

    report = module.build_report(str(db))

    conditions = report["markets"]["condition_distribution"]
    assert conditions["exact"] == 1
    assert conditions["at_or_above"] == 1
    assert conditions["range"] == 1
    assert conditions["at_or_below"] == 1
    assert report["markets"]["condition_source_counts"]["question_inferred"] == 4
    cities = {row["city"]: row for row in report["markets"]["snapshots_by_city"]}
    assert cities["Paris"]["snapshots"] == 2
    assert cities["London"]["snapshots"] == 1


def test_gaps_are_reported(tmp_path):
    db = tmp_path / "polymarket.db"
    create_db(db)
    module = load_tool_module()

    report = module.build_report(str(db))

    assert report["cycles"]["gaps"]
    assert report["cycles"]["gaps"][0]["gap_hours"] == 24.0
    assert any(item["type"] == "cycle_gap" for item in report["top_bottlenecks"])


def test_markdown_output_is_valid_enough(tmp_path):
    db = tmp_path / "polymarket.db"
    create_db(db)

    result = run_cli("--db", str(db), "--markdown")

    assert result.returncode == 0, result.stderr
    assert "# DB Throughput Report" in result.stdout
    assert "| Slot | Cycles | Evaluated | Edge | Selected | Buys | Buy/Eval | Buy/Selected |" in result.stdout
    assert "LOG_ONLY" in result.stdout
    assert "OPUS_REVIEW_REQUIRED" in result.stdout


def test_missing_table_degrades_with_warning(tmp_path):
    db = tmp_path / "partial.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE cycle_events (
            id INTEGER PRIMARY KEY,
            ts_utc TEXT NOT NULL,
            markets_evaluated INTEGER,
            buys_count INTEGER,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO cycle_events (ts_utc, markets_evaluated, buys_count, payload_json) VALUES (?, ?, ?, ?)",
        ("2026-05-01T12:00:00Z", 3, 0, "{}"),
    )
    conn.commit()
    conn.close()

    payload = json.loads(run_cli("--db", str(db), "--json").stdout)

    assert payload["status"] == "degraded"
    assert payload["source_quality"]["status"] == "degraded_missing_tables"
    assert "market_snapshots" in payload["source_quality"]["missing_tables"]


def test_open_readonly_db_blocks_writes(tmp_path):
    db = tmp_path / "polymarket.db"
    create_db(db)
    module = load_tool_module()

    conn = module.open_readonly_db(db)
    try:
        try:
            conn.execute("CREATE TABLE should_fail (id INTEGER)")
        except sqlite3.OperationalError as exc:
            assert "readonly" in str(exc).lower() or "query only" in str(exc).lower()
        else:
            raise AssertionError("read-only connection allowed a write")
    finally:
        conn.close()


def test_output_flag_writes_local_file(tmp_path):
    db = tmp_path / "polymarket.db"
    out = tmp_path / "report.json"
    create_db(db)

    result = run_cli("--db", str(db), "--output", str(out))

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "LOG_ONLY"
