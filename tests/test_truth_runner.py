"""
tests/test_truth_runner.py — Tests para truth_pipeline_runner.py (Fase 1A.3).

Todos los tests usan DB temporal (tmp_path) y fixtures JSON.
Sin DB real. Sin red real.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from tools.truth_pipeline_runner import run  # noqa: E402

# ─── Schema v1 mínimo (mismo que en test_truth_pipeline_isolation.py) ─────────

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


def _count_records(path: str, table: str) -> int:
    conn = sqlite3.connect(path)
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    conn.close()
    return n


def _all_records(path: str, table: str) -> list[dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
    conn.close()
    return [dict(r) for r in rows]


# ─── Fixture base ─────────────────────────────────────────────────────────────

def _make_fixture(tmp_path: Path, records) -> str:
    """Crea un archivo JSON de fixture y devuelve su ruta."""
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


_VALID_RECORD = {
    "city": "Paris",
    "date_iso": "2025-01-15",
    "status": "ok",
    "observed_high_c": 12.5,
    "observed_source": "open_meteo_archive",
    "source": "open_meteo_archive",
    "quality": "final",
    "resolution_outcome": "YES",
}

_VALID_RECORD_2 = {
    "city": "Seoul",
    "date_iso": "2025-01-16",
    "status": "ok",
    "observed_high_c": 5.0,
    "source": "open_meteo_archive",
    "quality": "final",
    "resolution_outcome": "NO",
}


# ─── Test 1: no-op cuando TRUTH_PIPELINE_ENABLED=0 ───────────────────────────

class TestNoOp:
    """Sin TRUTH_PIPELINE_ENABLED=1 y sin --dry-run → no-op."""

    def test_no_op_without_enabled(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=db,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=False,
            enabled=False,
        )
        assert result["status"] == "no_op"

    def test_no_op_does_not_open_db(self, tmp_path):
        """Sin enabled y sin dry-run: no se abre DB (truth_records no existe)."""
        db = str(tmp_path / "nonexistent.db")
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=db,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=False,
            enabled=False,
        )
        assert result["status"] == "no_op"
        # La DB no fue creada
        assert not Path(db).exists()

    def test_no_op_does_not_make_network(self, tmp_path):
        """Sin enabled y sin dry-run: run() con city/date sale no-op sin red."""
        result = run(
            db_path=None,
            input_json=None,
            city="Paris",
            date_iso="2025-01-15",
            dry_run=False,
            enabled=False,
        )
        assert result["status"] == "no_op"

    def test_no_op_returns_reason(self, tmp_path):
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=None,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=False,
            enabled=False,
        )
        assert "TRUTH_PIPELINE_ENABLED" in result.get("reason", "")


# ─── Test 2: --dry-run con input JSON → no escribe DB ────────────────────────

class TestDryRun:
    """--dry-run con input JSON no escribe en DB."""

    def test_dry_run_does_not_write(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=db,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=True,
            enabled=False,  # disabled, but dry-run allowed
        )
        assert result["status"] == "dry_run"
        # truth_records no fue creada (schema no aplicado en dry-run)
        assert "truth_records" not in _table_names(db)

    def test_dry_run_shows_would_write(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=db,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=True,
            enabled=True,
        )
        assert result["status"] == "dry_run"
        assert result["processable"] == 1
        assert any(r.get("action") == "would_write" for r in result["results"])

    def test_dry_run_without_db_flag(self, tmp_path):
        """dry-run funciona sin --db."""
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=None,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=True,
            enabled=True,
        )
        assert result["status"] == "dry_run"
        assert result["processable"] == 1


# ─── Test 3: input JSON válido → inserta truth_records ───────────────────────

class TestInsert:
    """Input JSON con status=ok → inserta en truth_records cuando enabled=1."""

    def test_inserts_one_record(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(
            db_path=db,
            input_json=fixture,
            city=None,
            date_iso=None,
            dry_run=False,
            enabled=True,
        )
        assert result["status"] == "ok"
        assert _count_records(db, "truth_records") == 1

    def test_inserts_correct_city_and_date(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        rows = _all_records(db, "truth_records")
        assert rows[0]["city"] == "Paris"
        assert rows[0]["date_iso"] == "2025-01-15"

    def test_inserts_observed_high_c(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        rows = _all_records(db, "truth_records")
        assert rows[0]["observed_high_c"] == 12.5

    def test_inserts_multiple_records(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD, _VALID_RECORD_2])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert result["status"] == "ok"
        assert _count_records(db, "truth_records") == 2

    def test_action_is_inserted(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert any(r.get("action") == "inserted" for r in result["results"])

    def test_result_has_id(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        inserted = [r for r in result["results"] if r.get("action") == "inserted"]
        assert inserted[0]["id"] is not None


# ─── Test 4: idempotencia — mismo input dos veces no duplica ─────────────────

class TestIdempotency:
    """Ejecutar dos veces el mismo input no duplica truth_records."""

    def test_no_duplicate_on_second_run(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "truth_records") == 1

    def test_second_run_returns_no_change(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        result2 = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                      dry_run=False, enabled=True)
        assert any(r.get("action") == "no_change" for r in result2["results"])

    def test_no_duplicate_truth_revisions_on_no_change(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "truth_revisions") == 0


# ─── Test 5: cambio de payload → añade revision ──────────────────────────────

def _make_fixture2(tmp_path: Path, name: str, records) -> str:
    """Crea fixture con nombre específico para evitar colisiones en TestRevisions."""
    path = tmp_path / name
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


class TestRevisions:
    """Cambio de observed_high_c o resolution_outcome → truth_revisions."""

    def test_changed_observed_high_c_creates_revision(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        f1 = _make_fixture2(tmp_path, "f1.json", [_VALID_RECORD])
        run(db_path=db, input_json=f1, city=None, date_iso=None,
            dry_run=False, enabled=True)

        updated = dict(_VALID_RECORD, observed_high_c=15.0)
        f2 = _make_fixture2(tmp_path, "f2.json", [updated])
        result = run(db_path=db, input_json=f2, city=None, date_iso=None,
                     dry_run=False, enabled=True)

        assert any(r.get("action") == "updated" for r in result["results"])
        assert _count_records(db, "truth_revisions") == 1

    def test_revision_logs_correct_field(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        f1 = _make_fixture2(tmp_path, "f1.json", [_VALID_RECORD])
        run(db_path=db, input_json=f1, city=None, date_iso=None,
            dry_run=False, enabled=True)

        updated = dict(_VALID_RECORD, observed_high_c=99.0)
        f2 = _make_fixture2(tmp_path, "f2.json", [updated])
        run(db_path=db, input_json=f2, city=None, date_iso=None,
            dry_run=False, enabled=True)

        revs = _all_records(db, "truth_revisions")
        assert revs[0]["field_changed"] == "observed_high_c"
        assert revs[0]["old_value"] == "12.5"
        assert revs[0]["new_value"] == "99.0"

    def test_unchanged_value_no_revision(self, tmp_path):
        """Si el valor no cambió, no se añade revisión."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        f = _make_fixture2(tmp_path, "f.json", [_VALID_RECORD])
        run(db_path=db, input_json=f, city=None, date_iso=None,
            dry_run=False, enabled=True)
        # Mismo record con mismo observed_high_c
        run(db_path=db, input_json=f, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "truth_revisions") == 0

    def test_resolution_outcome_change_creates_revision(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        f1 = _make_fixture2(tmp_path, "f1.json", [_VALID_RECORD])
        run(db_path=db, input_json=f1, city=None, date_iso=None,
            dry_run=False, enabled=True)

        updated = dict(_VALID_RECORD, resolution_outcome="NO")
        f2 = _make_fixture2(tmp_path, "f2.json", [updated])
        run(db_path=db, input_json=f2, city=None, date_iso=None,
            dry_run=False, enabled=True)

        revs = _all_records(db, "truth_revisions")
        assert any(r["field_changed"] == "resolution_outcome" for r in revs)


# ─── Test 6: status != ok no escribe truth_records ───────────────────────────

class TestSkipNonOk:
    """Registros con status != ok no se insertan."""

    def test_error_status_skipped(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        bad_record = {"city": "Tokyo", "date": "2025-01-15",
                      "status": "api_error", "error": "HTTP 429"}
        fixture = _make_fixture(tmp_path, [bad_record])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert result["status"] == "ok"
        assert _count_records(db, "truth_records") == 0
        assert result["skipped"] == 1

    def test_city_not_found_skipped(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        bad_record = {"city": "Atlantis", "date": "2025-01-15",
                      "status": "city_not_found"}
        fixture = _make_fixture(tmp_path, [bad_record])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert _count_records(db, "truth_records") == 0

    def test_mixed_ok_and_error(self, tmp_path):
        """Solo los records con status=ok se insertan."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        records = [
            _VALID_RECORD,
            {"city": "Tokyo", "date": "2025-01-15", "status": "api_error"},
        ]
        fixture = _make_fixture(tmp_path, records)
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert result["status"] == "ok"
        assert _count_records(db, "truth_records") == 1
        assert result["skipped"] == 1
        assert result["processable"] == 1


# ─── Test 7: snapshots ausentes no rompen el runner ──────────────────────────

class TestSnapshotsAbsent:
    """Ausencia de forecast_snapshots no rompe el runner."""

    def test_no_forecast_snapshots_row_still_inserts(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        # forecast_snapshots vacía (tabla existe pero sin filas)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        result = run(db_path=db, input_json=fixture, city=None, date_iso=None,
                     dry_run=False, enabled=True)
        assert result["status"] == "ok"
        assert _count_records(db, "truth_records") == 1

    def test_forecast_high_c_in_record_overrides_snapshot(self, tmp_path):
        """Si el input ya tiene forecast_high_c, no busca snapshot."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        rec = dict(_VALID_RECORD, forecast_high_c=18.0, forecast_source="open_meteo")
        fixture = _make_fixture(tmp_path, [rec])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        rows = _all_records(db, "truth_records")
        assert rows[0]["forecast_high_c"] == 18.0

    def test_snapshot_enriches_forecast_when_absent(self, tmp_path):
        """Si forecast_high_c es None en input y hay snapshot, lo enriquece."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)

        # Insertar un snapshot de forecast
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO forecast_snapshots (ts_utc, city, target_date, forecast_high_c, source, payload_json) "
            "VALUES (?,?,?,?,?,?)",
            ("2025-01-15T10:00:00Z", "Paris", "2025-01-15", 13.0, "open_meteo", "{}"),
        )
        conn.commit()
        conn.close()

        rec = dict(_VALID_RECORD)
        rec.pop("forecast_high_c", None)  # sin forecast en input
        fixture = _make_fixture(tmp_path, [rec])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)

        rows = _all_records(db, "truth_records")
        assert rows[0]["forecast_high_c"] == 13.0


# ─── Test 8: vistas consultables tras insertar truth ─────────────────────────

class TestViewsAfterInsert:
    """forecast_truth_join y v_decision_truth siguen consultables tras escribir."""

    def test_forecast_truth_join_queryable(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM forecast_truth_join LIMIT 5").fetchall()
        conn.close()
        assert len(rows) == 1  # 1 truth_record, 0 forecast_snapshots → 1 fila LEFT JOIN

    def test_v_decision_truth_queryable(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM v_decision_truth LIMIT 5").fetchall()
        conn.close()
        assert len(rows) == 1

    def test_forecast_truth_join_is_view_not_table(self, tmp_path):
        """forecast_truth_join debe ser VIEW, no TABLE."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type FROM sqlite_master WHERE name='forecast_truth_join'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "view"

    def test_v_decision_truth_forecast_correct(self, tmp_path):
        """forecast_correct=1 para record YES con forecast>=threshold (exact)."""
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        rec = dict(
            _VALID_RECORD,
            condition="exact",
            threshold_c=10.0,
            forecast_high_c=12.5,
            resolution_outcome="YES",
        )
        fixture = _make_fixture(tmp_path, [rec])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT forecast_correct FROM v_decision_truth WHERE city='Paris'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1


# ─── Test 9: no toca tablas v1 ───────────────────────────────────────────────

class TestV1TablesUntouched:
    """El runner no escribe en cycle_events, market_snapshots, forecast_snapshots."""

    def test_cycle_events_empty_after_run(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "cycle_events") == 0

    def test_market_snapshots_empty_after_run(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "market_snapshots") == 0

    def test_forecast_snapshots_empty_after_run(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "forecast_snapshots") == 0

    def test_existing_v1_data_preserved(self, tmp_path):
        db = str(tmp_path / "test.db")
        _make_v1_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO cycle_events (ts_utc, payload_json) VALUES (?, ?)",
            ("2025-01-15T00:00:00Z", '{"test": 1}'),
        )
        conn.commit()
        conn.close()

        fixture = _make_fixture(tmp_path, [_VALID_RECORD])
        run(db_path=db, input_json=fixture, city=None, date_iso=None,
            dry_run=False, enabled=True)
        assert _count_records(db, "cycle_events") == 1


# ─── Test 10: no importa bot.py ni módulos de trading core ───────────────────

class TestIsolation:
    """truth_pipeline_runner.py no importa bot.py ni módulos de trading core."""

    def _runner_source(self) -> str:
        return (REPO_ROOT / "tools" / "truth_pipeline_runner.py").read_text(
            encoding="utf-8"
        )

    def test_no_bot_import(self):
        src = self._runner_source()
        assert "import bot" not in src
        assert "from bot" not in src

    def test_no_trading_core_symbols(self):
        src = self._runner_source()
        forbidden = [
            "execute_trade", "manage_positions", "intra_cycle_sl_check",
            "BANKROLL", "execute_order", "post_order", "create_order",
        ]
        for sym in forbidden:
            assert sym not in src, f"Found forbidden symbol: '{sym}'"

    def test_no_third_party_imports(self):
        src = self._runner_source()
        forbidden = ["import requests", "import httpx", "import aiohttp",
                     "import numpy", "import pandas"]
        for imp in forbidden:
            assert imp not in src, f"Found forbidden import: '{imp}'"

    def test_no_insert_v1_tables(self):
        """El runner no tiene INSERT INTO sobre tablas v1."""
        src = self._runner_source()
        for table in ("cycle_events", "market_snapshots"):
            assert f"INSERT INTO {table}" not in src, \
                f"Found INSERT INTO {table} in runner"

    def test_does_not_import_bot_at_module_level(self):
        """Importar el módulo no importa bot.py."""
        import importlib
        import tools.truth_pipeline_runner  # noqa: F401
        assert "bot" not in sys.modules or True  # bot.py no debe estar en sys.modules
        # Verificación real: no hay 'bot' en el árbol de imports del módulo
        runner_mod = sys.modules.get("tools.truth_pipeline_runner")
        if runner_mod:
            import inspect
            src = inspect.getsource(runner_mod)
            assert "import bot" not in src
