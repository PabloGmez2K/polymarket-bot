"""
tests/test_truth_pipeline_isolation.py

Tests de aislamiento para Truth Pipeline subfase 1A.1.

Verifica:
- apply_schema crea truth_records, truth_revisions, forecast_truth_join, v_decision_truth
- apply_schema es idempotente (doble aplicación no falla ni duplica)
- apply_schema no altera tablas v1 (cycle_events, market_snapshots, forecast_snapshots)
- borrar tablas truth_* deja la DB en estado usable para readiness checks
- truth_pipeline_schema.py no importa bot.py ni módulos de trading core
- truth_pipeline_schema.py usa solo stdlib
- sql/002_truth_pipeline.sql no contiene DROP TABLE sobre tablas v1
- apply_schema --dry-run retorna status=dry_run sin escribir nada
"""
import importlib
import inspect
import sqlite3
import sys
from pathlib import Path

import pytest

# Añadir raíz del repo al path para importar el módulo
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.truth_pipeline_schema import apply_schema  # noqa: E402

SQL_FILE = REPO_ROOT / "sql" / "002_truth_pipeline.sql"

# ─── Schema v1 mínimo para simular DB existente ──────────────────────────────

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


def _make_v1_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.close()


def _table_names(path: str) -> set:
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def _view_names(path: str) -> set:
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def _schema_version(path: str) -> int | None:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def _column_names(path: str, table: str) -> set:
    conn = sqlite3.connect(path)
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    conn.close()
    return {r[1] for r in rows}


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestSchemaApplied:
    """La migración crea todas las tablas y vistas esperadas."""

    def test_truth_records_created(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        result = apply_schema(db)
        assert result["status"] == "applied"
        assert "truth_records" in _table_names(db)

    def test_truth_revisions_created(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        assert "truth_revisions" in _table_names(db)

    def test_forecast_truth_join_view_created(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        assert "forecast_truth_join" in _view_names(db)

    def test_v_decision_truth_view_created(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        assert "v_decision_truth" in _view_names(db)

    def test_schema_version_bumped_to_2(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        assert _schema_version(db) == 2

    def test_truth_records_columns(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        cols = _column_names(db, "truth_records")
        required = {
            "id", "city", "date_iso", "condition", "threshold_c",
            "forecast_high_c", "resolution_outcome", "bot_had_position",
            "bot_side", "snapshot_ts_utc", "payload_json",
        }
        assert required.issubset(cols), f"Missing columns: {required - cols}"

    def test_truth_revisions_columns(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        cols = _column_names(db, "truth_revisions")
        required = {"id", "truth_record_id", "field_changed", "revision_ts_utc"}
        assert required.issubset(cols), f"Missing columns: {required - cols}"


class TestIdempotency:
    """Aplicar el schema dos veces no falla ni duplica datos."""

    def test_double_apply_returns_already_applied(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        r1 = apply_schema(db)
        r2 = apply_schema(db)
        assert r1["status"] == "applied"
        assert r2["status"] == "already_applied"

    def test_double_apply_keeps_version_2(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        apply_schema(db)
        assert _schema_version(db) == 2

    def test_double_apply_no_duplicate_schema_version_rows(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM schema_version WHERE version=2"
        ).fetchone()[0]
        conn.close()
        assert count == 1


class TestV1TablesUntouched:
    """La migración no altera filas ni estructura de las tablas v1."""

    def test_cycle_events_columns_unchanged(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        cols_before = _column_names(db, "cycle_events")
        apply_schema(db)
        cols_after = _column_names(db, "cycle_events")
        assert cols_before == cols_after

    def test_market_snapshots_columns_unchanged(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        cols_before = _column_names(db, "market_snapshots")
        apply_schema(db)
        cols_after = _column_names(db, "market_snapshots")
        assert cols_before == cols_after

    def test_forecast_snapshots_columns_unchanged(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        cols_before = _column_names(db, "forecast_snapshots")
        apply_schema(db)
        cols_after = _column_names(db, "forecast_snapshots")
        assert cols_before == cols_after

    def test_v1_data_rows_preserved(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO cycle_events (ts_utc, payload_json) VALUES (?, ?)",
            ("2026-05-04T00:00:00Z", '{"test": 1}'),
        )
        conn.commit()
        conn.close()

        apply_schema(db)

        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM cycle_events").fetchone()[0]
        conn.close()
        assert count == 1


class TestDropTruthTablesLeavesDBUsable:
    """Borrar tablas truth_* deja la DB funcional para readiness checks."""

    def test_drop_truth_tables_db_still_readable(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)

        conn = sqlite3.connect(db)
        conn.execute("DROP VIEW IF EXISTS v_decision_truth")
        conn.execute("DROP VIEW IF EXISTS forecast_truth_join")
        conn.execute("DROP TABLE IF EXISTS truth_revisions")
        conn.execute("DROP TABLE IF EXISTS truth_records")
        conn.commit()
        conn.close()

        # Las tablas v1 siguen accesibles (simula readiness check)
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "cycle_events" in tables
        assert "market_snapshots" in tables
        assert "forecast_snapshots" in tables
        assert "schema_version" in tables

    def test_drop_truth_tables_v1_data_intact(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO market_snapshots (ts_utc, city, date_iso, payload_json) VALUES (?,?,?,?)",
            ("2026-05-04T00:00:00Z", "Paris", "2026-05-04", '{}'),
        )
        conn.commit()
        conn.close()

        apply_schema(db)

        conn = sqlite3.connect(db)
        conn.execute("DROP VIEW IF EXISTS v_decision_truth")
        conn.execute("DROP VIEW IF EXISTS forecast_truth_join")
        conn.execute("DROP TABLE IF EXISTS truth_revisions")
        conn.execute("DROP TABLE IF EXISTS truth_records")
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
        conn.close()
        assert count == 1


class TestDryRun:
    """--dry-run retorna status=dry_run sin escribir nada."""

    def test_dry_run_status(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        result = apply_schema(db, dry_run=True)
        assert result["status"] == "dry_run"
        assert result["version"] == 2

    def test_dry_run_does_not_create_tables(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db, dry_run=True)
        assert "truth_records" not in _table_names(db)
        assert "truth_revisions" not in _table_names(db)

    def test_dry_run_does_not_bump_schema_version(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db, dry_run=True)
        assert _schema_version(db) == 1


class TestIsolation:
    """truth_pipeline_schema.py no importa bot.py ni módulos de trading core."""

    def test_no_bot_import(self):
        source = Path(REPO_ROOT / "tools" / "truth_pipeline_schema.py").read_text(
            encoding="utf-8"
        )
        assert "import bot" not in source
        assert "from bot" not in source

    def test_no_trading_core_symbols(self):
        source = Path(REPO_ROOT / "tools" / "truth_pipeline_schema.py").read_text(
            encoding="utf-8"
        )
        forbidden = [
            "execute_trade", "manage_positions", "intra_cycle_sl_check",
            "BANKROLL", "execute_order", "post_order", "create_order",
        ]
        for sym in forbidden:
            assert sym not in source, f"Found forbidden symbol: {sym}"

    def test_stdlib_only(self):
        source = Path(REPO_ROOT / "tools" / "truth_pipeline_schema.py").read_text(
            encoding="utf-8"
        )
        forbidden_third_party = ["requests", "httpx", "aiohttp", "boto", "numpy", "pandas"]
        for lib in forbidden_third_party:
            assert lib not in source, f"Found third-party import: {lib}"

    def test_sql_no_drop_v1_tables(self):
        sql = SQL_FILE.read_text(encoding="utf-8").lower()
        v1_tables = ["cycle_events", "market_snapshots", "forecast_snapshots"]
        for table in v1_tables:
            assert f"drop table {table}" not in sql
            assert f"drop table if exists {table}" not in sql

    def test_sql_no_alter_v1_tables(self):
        sql = SQL_FILE.read_text(encoding="utf-8").lower()
        v1_tables = ["cycle_events", "market_snapshots", "forecast_snapshots"]
        for table in v1_tables:
            assert f"alter table {table}" not in sql


class TestViewsQueryable:
    """Las vistas son consultables sin errores una vez que hay datos."""

    def test_forecast_truth_join_queryable_empty(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM forecast_truth_join LIMIT 5").fetchall()
        conn.close()
        assert rows == []  # vacío pero sin error

    def test_v_decision_truth_queryable_empty(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM v_decision_truth LIMIT 5").fetchall()
        conn.close()
        assert rows == []

    def test_v_decision_truth_correct_forecast(self, tmp_path):
        """forecast_correct=1 cuando forecast>=threshold y outcome=YES (exact)."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        conn.execute(
            """INSERT INTO truth_records
               (city, date_iso, condition, threshold_c, forecast_high_c,
                resolution_outcome, bot_had_position, snapshot_ts_utc, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Paris", "2026-05-04", "exact", 20.0, 22.5, "YES", 0,
             "2026-05-04T12:00:00Z", "{}"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT forecast_correct FROM v_decision_truth WHERE city='Paris'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1

    def test_v_decision_truth_incorrect_forecast(self, tmp_path):
        """forecast_correct=0 cuando forecast<threshold pero outcome=YES (exact)."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        conn.execute(
            """INSERT INTO truth_records
               (city, date_iso, condition, threshold_c, forecast_high_c,
                resolution_outcome, bot_had_position, snapshot_ts_utc, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Seoul", "2026-05-04", "exact", 25.0, 18.0, "YES", 0,
             "2026-05-04T12:00:00Z", "{}"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT forecast_correct FROM v_decision_truth WHERE city='Seoul'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 0

    def test_v_decision_truth_unknown_outcome_null(self, tmp_path):
        """forecast_correct=NULL cuando outcome=UNKNOWN."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        apply_schema(db)
        conn = sqlite3.connect(db)
        conn.execute(
            """INSERT INTO truth_records
               (city, date_iso, condition, threshold_c, forecast_high_c,
                resolution_outcome, bot_had_position, snapshot_ts_utc, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Tokyo", "2026-05-04", "exact", 22.0, 23.0, "UNKNOWN", 0,
             "2026-05-04T12:00:00Z", "{}"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT forecast_correct FROM v_decision_truth WHERE city='Tokyo'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] is None
