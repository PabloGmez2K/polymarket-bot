"""
tests/test_truth_pipeline_report.py — Tests para truth_pipeline_report.py (Fase 1A.4).

Todos los tests usan DB temporal (tmp_path). Sin DB real. Sin red. Sin Telegram.
Cubre:
- schema_missing → no crashea, status claro
- DB vacía + schema aplicado → status empty
- DB con datos → estadísticas correctas
- calibración baja + n≥10 → watch
- drift ≥3 → action_design
- DB no encontrada → watch_tech
- No importa bot.py ni módulos de trading core
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from tools.truth_pipeline_report import generate_report  # noqa: E402

# ─── Schema v1 mínimo ─────────────────────────────────────────────────────────

_V1_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cycle_events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_number       INTEGER,
    logic_cycle_number INTEGER,
    ts_utc             TEXT NOT NULL,
    bot_version        TEXT,
    logic_series       TEXT,
    mode               TEXT,
    markets_evaluated  INTEGER,
    buys_count         INTEGER,
    exposure_after     REAL,
    budget_left        REAL,
    payload_json       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_number    INTEGER,
    ts_utc          TEXT NOT NULL,
    city            TEXT NOT NULL,
    date_iso        TEXT NOT NULL,
    forecast_high_c REAL,
    question        TEXT,
    payload_json    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forecast_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_number    INTEGER,
    ts_utc          TEXT NOT NULL,
    city            TEXT NOT NULL,
    target_date     TEXT NOT NULL,
    forecast_high_c REAL,
    source          TEXT,
    payload_json    TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (1, datetime('now'));
"""

_V2_EXTRA = """
CREATE TABLE IF NOT EXISTS truth_records (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    city               TEXT NOT NULL,
    date_iso           TEXT NOT NULL,
    condition          TEXT,
    threshold_c        REAL,
    question           TEXT,
    market_id          TEXT,
    token_id_yes       TEXT,
    token_id_no        TEXT,
    forecast_high_c    REAL,
    forecast_source    TEXT,
    observed_high_c    REAL,
    observed_source    TEXT,
    resolution_outcome TEXT,
    resolution_ts_utc  TEXT,
    resolution_method  TEXT,
    bot_had_position   INTEGER DEFAULT 0,
    bot_side           TEXT,
    snapshot_ts_utc    TEXT NOT NULL,
    payload_json       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS truth_revisions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    truth_record_id  INTEGER NOT NULL,
    field_changed    TEXT NOT NULL,
    old_value        TEXT,
    new_value        TEXT,
    revision_ts_utc  TEXT NOT NULL,
    reason           TEXT
);

CREATE VIEW IF NOT EXISTS forecast_truth_join AS
SELECT
    tr.id              AS truth_id,
    tr.city,
    tr.date_iso,
    tr.condition,
    tr.threshold_c,
    tr.forecast_high_c AS tr_forecast_high_c,
    tr.observed_high_c,
    tr.resolution_outcome,
    fs.forecast_high_c AS fs_forecast_high_c,
    fs.source          AS fs_source,
    fs.ts_utc          AS fs_ts_utc
FROM truth_records tr
LEFT JOIN forecast_snapshots fs
    ON fs.city = tr.city AND fs.target_date = tr.date_iso;

CREATE VIEW IF NOT EXISTS v_decision_truth AS
SELECT
    tr.id,
    tr.city,
    tr.date_iso,
    tr.condition,
    tr.threshold_c,
    tr.forecast_high_c,
    tr.resolution_outcome,
    tr.bot_had_position,
    tr.bot_side,
    CASE
        WHEN tr.condition = 'exact'
             AND tr.forecast_high_c IS NOT NULL
             AND tr.threshold_c IS NOT NULL
             AND tr.resolution_outcome IN ('YES','NO')
        THEN CASE
            WHEN tr.forecast_high_c >= tr.threshold_c AND tr.resolution_outcome = 'YES' THEN 1
            WHEN tr.forecast_high_c < tr.threshold_c  AND tr.resolution_outcome = 'NO'  THEN 1
            ELSE 0
        END
        ELSE NULL
    END AS forecast_correct,
    CASE
        WHEN tr.bot_had_position = 1
             AND tr.bot_side IS NOT NULL
             AND tr.resolution_outcome IN ('YES','NO')
        THEN CASE
            WHEN tr.bot_side = tr.resolution_outcome THEN 1 ELSE 0
        END
        ELSE NULL
    END AS position_correct
FROM truth_records tr;

INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (2, datetime('now'));
"""


def _make_v1_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.close()


def _make_v2_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.executescript(_V2_EXTRA)
    conn.close()


def _insert_truth_record(
    path: str,
    *,
    city: str = "Paris",
    date_iso: str = "2025-01-15",
    condition: str = "exact",
    threshold_c: float = 10.0,
    forecast_high_c: float = 12.5,
    observed_high_c: float | None = 11.0,
    resolution_outcome: str = "YES",
    bot_had_position: int = 0,
    bot_side: str | None = None,
    snapshot_ts_utc: str = "2025-01-16T08:00:00Z",
) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """INSERT INTO truth_records
           (city, date_iso, condition, threshold_c, forecast_high_c,
            observed_high_c, resolution_outcome, bot_had_position, bot_side,
            snapshot_ts_utc, payload_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (city, date_iso, condition, threshold_c, forecast_high_c,
         observed_high_c, resolution_outcome, bot_had_position, bot_side,
         snapshot_ts_utc, "{}"),
    )
    conn.commit()
    conn.close()


# ─── Test 1: schema_missing ───────────────────────────────────────────────────

class TestSchemaMissing:
    """Reporter no crashea si truth_records no existe."""

    def test_v1_only_db_returns_schema_missing(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        report = generate_report(db)
        assert report["status"] == "schema_missing"

    def test_schema_missing_has_message(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        report = generate_report(db)
        assert "message" in report
        assert report["message"]

    def test_schema_missing_no_crash_on_empty_v1(self, tmp_path):
        db = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db)
        conn.close()
        report = generate_report(db)
        assert report["status"] == "schema_missing"

    def test_db_not_found_returns_watch_tech(self, tmp_path):
        db = str(tmp_path / "nonexistent.db")
        report = generate_report(db)
        assert report["status"] == "watch_tech"

    def test_db_not_found_has_error(self, tmp_path):
        db = str(tmp_path / "nonexistent.db")
        report = generate_report(db)
        assert "error" in report


# ─── Test 2: DB vacía con schema v2 ──────────────────────────────────────────

class TestEmptyDB:
    """Schema v2 aplicado pero sin filas → status empty."""

    def test_empty_returns_empty_status(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        report = generate_report(db)
        assert report["status"] == "empty"

    def test_empty_truth_records_count_zero(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        report = generate_report(db)
        assert report["truth_records"] == 0

    def test_empty_has_views_info(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        report = generate_report(db)
        assert "view_forecast_truth_join" in report or "views" in report

    def test_empty_has_message(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        report = generate_report(db)
        assert "message" in report


# ─── Test 3: datos básicos → no_action ───────────────────────────────────────

class TestBasicData:
    """Con datos sanos → no_action."""

    def test_single_record_returns_no_action(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        _insert_truth_record(db)
        report = generate_report(db)
        assert report["status"] == "no_action"

    def test_truth_records_count_correct(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        _insert_truth_record(db, city="Paris", date_iso="2025-01-15")
        _insert_truth_record(db, city="Seoul", date_iso="2025-01-16")
        report = generate_report(db)
        assert report["truth_records"] == 2

    def test_city_coverage_included(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        _insert_truth_record(db, city="Paris")
        _insert_truth_record(db, city="Seoul", date_iso="2025-01-16")
        report = generate_report(db)
        cities = {c["city"] for c in report.get("city_coverage", [])}
        assert "Paris" in cities
        assert "Seoul" in cities

    def test_n_resolved_counts_yes_no(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        _insert_truth_record(db, resolution_outcome="YES")
        _insert_truth_record(db, city="Seoul", date_iso="2025-01-16", resolution_outcome="NO")
        _insert_truth_record(db, city="Tokyo", date_iso="2025-01-17", resolution_outcome="UNKNOWN")
        report = generate_report(db)
        assert report["n_resolved"] == 2
        assert report["n_unknown"] == 1

    def test_last_update_ts_present(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        _insert_truth_record(db)
        report = generate_report(db)
        assert report.get("last_update_ts") is not None

    def test_calibration_global_computed(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        # forecast>=threshold, outcome=YES → forecast_correct=1
        _insert_truth_record(
            db, condition="exact", threshold_c=10.0, forecast_high_c=12.5,
            resolution_outcome="YES"
        )
        report = generate_report(db)
        assert report.get("calibration_global") is not None
        assert report["calibration_global"] == 1.0


# ─── Test 4: calibración baja + n≥10 → watch ─────────────────────────────────

class TestWatchStatus:
    """Calibración global <50% con n_resolved≥10 → watch."""

    def _insert_wrong_record(self, db: str, city: str, date_iso: str) -> None:
        # forecast_high_c >= threshold pero outcome=NO → forecast_correct=0
        _insert_truth_record(
            db,
            city=city,
            date_iso=date_iso,
            condition="exact",
            threshold_c=10.0,
            forecast_high_c=15.0,
            resolution_outcome="NO",
        )

    def test_low_calibration_n10_returns_watch(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        # 10 registros con forecast incorrecto
        cities = ["Paris", "Seoul", "Tokyo", "London", "Berlin",
                  "Madrid", "Rome", "Vienna", "Lisbon", "Athens"]
        for i, city in enumerate(cities):
            self._insert_wrong_record(db, city, f"2025-01-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] == "watch"

    def test_low_calibration_n9_returns_no_action(self, tmp_path):
        """Con n_resolved=9 (< 10) no dispara watch por calibración."""
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        cities = ["Paris", "Seoul", "Tokyo", "London", "Berlin",
                  "Madrid", "Rome", "Vienna", "Lisbon"]
        for i, city in enumerate(cities):
            self._insert_wrong_record(db, city, f"2025-01-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] in ("no_action", "watch")
        # Con n<10 no debe ser watch por calibración (puede ser no_action)
        n_resolved = report.get("n_resolved", 0)
        if n_resolved < 10:
            assert report["status"] == "no_action"


# ─── Test 5: drift ≥3 → action_design ────────────────────────────────────────

class TestDriftStatus:
    """Drift ≥3 incorrectos en misma ciudad/condición → action_design."""

    def _insert_drift_record(self, db: str, city: str, date_iso: str) -> None:
        # forecast_high_c >= threshold pero outcome=NO (error forecast)
        _insert_truth_record(
            db,
            city=city,
            date_iso=date_iso,
            condition="exact",
            threshold_c=10.0,
            forecast_high_c=15.0,
            resolution_outcome="NO",
        )

    def test_three_wrong_same_city_returns_action_design(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] == "action_design"

    def test_drift_alert_cities_populated(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Seoul", f"2025-01-{15+i:02d}")
        report = generate_report(db)
        drift = report.get("drift_alert_cities", [])
        assert any(d["city"] == "Seoul" for d in drift)

    def test_two_wrong_no_drift_alert(self, tmp_path):
        """Solo 2 incorrectos no dispara action_design."""
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(2):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] != "action_design"
        assert not report.get("drift_alert_cities")


# ─── Test 5b: drift en 2+ ciudades → action_safety ───────────────────────────

class TestActionSafetyStatus:
    """Drift ≥3 en 2+ ciudades → action_safety (inconsistencia grave)."""

    def _insert_drift_record(self, db: str, city: str, date_iso: str) -> None:
        _insert_truth_record(
            db,
            city=city,
            date_iso=date_iso,
            condition="exact",
            threshold_c=10.0,
            forecast_high_c=15.0,
            resolution_outcome="NO",
        )

    def test_drift_two_cities_returns_action_safety(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        for i in range(3):
            self._insert_drift_record(db, "Seoul", f"2025-02-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] == "action_safety"

    def test_action_safety_drift_cities_has_two_entries(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        for i in range(3):
            self._insert_drift_record(db, "Seoul", f"2025-02-{15+i:02d}")
        report = generate_report(db)
        drift = report.get("drift_alert_cities", [])
        assert len(drift) >= 2

    def test_one_city_drift_still_action_design(self, tmp_path):
        """Solo 1 ciudad con drift → action_design (no action_safety)."""
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] == "action_design"

    def test_action_safety_higher_than_action_design(self, tmp_path):
        """action_safety es más grave que action_design."""
        db = str(tmp_path / "test.db")
        _make_v2_db(db)
        for i in range(3):
            self._insert_drift_record(db, "Paris", f"2025-01-{15+i:02d}")
        for i in range(3):
            self._insert_drift_record(db, "Tokyo", f"2025-02-{15+i:02d}")
        report = generate_report(db)
        assert report["status"] != "action_design"
        assert report["status"] == "action_safety"


# ─── Test 6: aislamiento — no importa bot.py ─────────────────────────────────

class TestIsolation:
    """truth_pipeline_report.py no importa bot.py ni módulos de trading core."""

    def _src(self) -> str:
        return (REPO_ROOT / "tools" / "truth_pipeline_report.py").read_text(encoding="utf-8")

    def test_no_bot_import(self):
        src = self._src()
        assert "import bot" not in src
        assert "from bot" not in src

    def test_no_trading_core_symbols(self):
        src = self._src()
        forbidden = [
            "execute_trade", "manage_positions", "intra_cycle_sl_check",
            "BANKROLL", "execute_order", "post_order",
        ]
        for sym in forbidden:
            assert sym not in src, f"Found forbidden symbol: {sym}"

    def test_stdlib_only(self):
        src = self._src()
        forbidden = ["import requests", "import httpx", "import aiohttp",
                     "import numpy", "import pandas"]
        for imp in forbidden:
            assert imp not in src, f"Found forbidden import: {imp}"

    def test_uses_read_only_uri(self):
        src = self._src()
        assert "mode=ro" in src

    def test_no_write_to_db(self):
        src = self._src()
        assert "INSERT INTO" not in src
        assert "UPDATE " not in src
        assert "DELETE FROM" not in src
