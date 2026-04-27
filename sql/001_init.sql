-- sql/001_init.sql — Schema v1 (Fase 0: SQLite Recorder)
-- Referencia canónica del esquema. La aplicación real usa sqlite_recorder.py.
-- Fase 1 añadirá: truth_records, truth_revisions

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Un registro por ciclo completo de bot.py (main())
CREATE TABLE IF NOT EXISTS cycle_events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_number       INTEGER,
    logic_cycle_number INTEGER,
    ts_utc             TEXT NOT NULL,
    bot_version        TEXT,
    logic_series       TEXT,
    mode               TEXT,           -- 'REAL' | 'DRY_RUN'
    markets_evaluated  INTEGER,
    buys_count         INTEGER,
    exposure_after     REAL,
    budget_left        REAL,
    payload_json       TEXT NOT NULL   -- cycle_data completo para replay
);

-- Una fila por ciudad/fecha observada en OBSERVED_AUDIT_CITIES por ciclo
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

-- Una fila por ciudad/fecha con forecast disponible (subset de market_snapshots)
CREATE TABLE IF NOT EXISTS forecast_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_number    INTEGER,
    ts_utc          TEXT NOT NULL,
    city            TEXT NOT NULL,
    target_date     TEXT NOT NULL,
    forecast_high_c REAL,
    source          TEXT,          -- 'observed_audit_city' en Fase 0
    payload_json    TEXT NOT NULL
);

-- Índices de acceso frecuente
CREATE INDEX IF NOT EXISTS idx_cycle_events_ts   ON cycle_events (ts_utc);
CREATE INDEX IF NOT EXISTS idx_market_snaps_city ON market_snapshots (city, date_iso);
CREATE INDEX IF NOT EXISTS idx_forecast_city     ON forecast_snapshots (city, target_date);

-- Registrar esta versión
INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (1, datetime('now'));
