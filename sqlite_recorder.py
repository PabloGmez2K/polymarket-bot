"""
sqlite_recorder.py — Fase 0: Persistencia SQLite pasiva para polymarket-bot.

Solo librería estándar (sqlite3, json, pathlib). Sin dependencias externas.
Fail-safe: si falla, el bot continúa sin interrupción.

Activar: SQLITE_RECORDER_ENABLED=1 en Railway o .env.
Path por defecto: DATA_DIR/polymarket.db (o data/polymarket.db en local).

Tablas (v1):
  cycle_events       — un registro por ciclo completo
  market_snapshots   — una fila por ciudad/fecha observada en el ciclo
  forecast_snapshots — una fila por ciudad/fecha con forecast disponible

Extensible: Fase 1 añadirá truth_records y truth_revisions sin romper este schema.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_cycle_events_ts   ON cycle_events (ts_utc);
CREATE INDEX IF NOT EXISTS idx_market_snaps_city ON market_snapshots (city, date_iso);
CREATE INDEX IF NOT EXISTS idx_forecast_city     ON forecast_snapshots (city, target_date);
"""


class SQLiteRecorder:
    """Recorder SQLite pasivo para polymarket-bot.

    Uso mínimo:
        rec = SQLiteRecorder("data/polymarket.db")
        rec.record_cycle(cycle_data)   # cycle_data = dict de main()
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._init_schema()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def record_cycle(self, cycle_data: dict[str, Any]) -> None:
        """Persiste un ciclo completo en las tres tablas.

        Transacción única: si falla cualquier INSERT, hace rollback completo.
        El caller (bot.py) envuelve esta llamada en try/except.
        """
        ts = cycle_data.get("timestamp_utc", "")
        cycle_num = cycle_data.get("cycle_number")
        logic_cycle_num = cycle_data.get("logic_cycle_number")
        bot_version = cycle_data.get("version", "")
        logic_series = cycle_data.get("logic_series", "")
        mode = cycle_data.get("mode", "")
        scan = cycle_data.get("scan") or {}
        markets_evaluated = scan.get("markets_evaluated", 0)
        buys = cycle_data.get("buys") or []
        exposure_after = cycle_data.get("exposure_after")
        budget_left = cycle_data.get("budget_left")

        with self._conn() as con:
            # 1. cycle_events — un registro por ciclo
            con.execute(
                "INSERT INTO cycle_events "
                "(cycle_number, logic_cycle_number, ts_utc, bot_version, logic_series, "
                " mode, markets_evaluated, buys_count, exposure_after, budget_left, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cycle_num, logic_cycle_num, ts, bot_version, logic_series,
                    mode, markets_evaluated, len(buys),
                    exposure_after, budget_left,
                    json.dumps(cycle_data, ensure_ascii=False, default=str),
                ),
            )

            # 2. market_snapshots + forecast_snapshots — una fila por ciudad/fecha observada
            for mkt in cycle_data.get("scanned_markets") or []:
                city = mkt.get("city", "")
                date_iso = mkt.get("date", "")
                forecast_high_c = mkt.get("forecast_max")
                question = mkt.get("question", "")
                payload = json.dumps(mkt, ensure_ascii=False, default=str)

                con.execute(
                    "INSERT INTO market_snapshots "
                    "(cycle_number, ts_utc, city, date_iso, forecast_high_c, question, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cycle_num, ts, city, date_iso, forecast_high_c, question, payload),
                )

                if city and date_iso and forecast_high_c is not None:
                    con.execute(
                        "INSERT INTO forecast_snapshots "
                        "(cycle_number, ts_utc, city, target_date, forecast_high_c, source, payload_json) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            cycle_num, ts, city, date_iso, float(forecast_high_c),
                            "observed_audit_city",
                            json.dumps(
                                {"city": city, "date": date_iso, "forecast_high_c": forecast_high_c},
                                ensure_ascii=False,
                            ),
                        ),
                    )

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.executescript(_SCHEMA_SQL)
            existing = con.execute(
                "SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,)
            ).fetchone()
            if not existing:
                con.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
                    (SCHEMA_VERSION,),
                )

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self._db_path, timeout=10)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
