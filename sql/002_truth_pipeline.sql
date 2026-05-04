-- sql/002_truth_pipeline.sql — Schema v2 (Fase 1: Truth Pipeline)
-- Migración aditiva. No modifica tablas v1 (cycle_events, market_snapshots, forecast_snapshots).
-- Ejecutar solo sobre DB existente con schema_version=1 aplicado.
-- Todas las sentencias son idempotentes (IF NOT EXISTS).

-- ─── Tabla principal de verdad ────────────────────────────────────────────────
-- Una fila por mercado+ciudad resuelto. Solo observación; nunca ejecuta órdenes.
CREATE TABLE IF NOT EXISTS truth_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    city                TEXT NOT NULL,
    date_iso            TEXT NOT NULL,           -- YYYY-MM-DD
    condition           TEXT,                    -- 'exact', 'range', etc.
    threshold_c         REAL,                    -- umbral de temperatura
    question            TEXT,
    market_id           TEXT,
    token_id_yes        TEXT,
    token_id_no         TEXT,
    forecast_high_c     REAL,                    -- forecast al momento del snapshot
    forecast_source     TEXT,                    -- 'open_meteo', 'noaa', etc.
    observed_high_c     REAL,                    -- temperatura real (NULL hasta resolución)
    observed_source     TEXT,
    resolution_outcome  TEXT,                    -- 'YES', 'NO', 'VOID', 'UNKNOWN'
    resolution_ts_utc   TEXT,
    resolution_method   TEXT,
    bot_had_position    INTEGER DEFAULT 0,       -- 1 si el bot tenía posición
    bot_side            TEXT,                    -- 'YES' o 'NO'
    snapshot_ts_utc     TEXT NOT NULL,
    payload_json        TEXT NOT NULL            -- payload completo para replay
);

-- ─── Log de correcciones ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS truth_revisions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    truth_record_id   INTEGER NOT NULL,
    field_changed     TEXT NOT NULL,
    old_value         TEXT,
    new_value         TEXT,
    revision_ts_utc   TEXT NOT NULL,
    reason            TEXT,
    FOREIGN KEY (truth_record_id) REFERENCES truth_records(id)
);

-- ─── Índices de acceso frecuente ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_truth_city     ON truth_records (city, date_iso);
CREATE INDEX IF NOT EXISTS idx_truth_outcome  ON truth_records (resolution_outcome);
CREATE INDEX IF NOT EXISTS idx_truth_rev_rec  ON truth_revisions (truth_record_id);

-- ─── Vista forecast_truth_join ────────────────────────────────────────────────
-- Cruza truth_records con forecast_snapshots por (city, date_iso).
-- Permite analizar calibración sin joins manuales en cada consulta.
-- No acopla a bot.py; solo referencia tablas del schema SQLite.
CREATE VIEW IF NOT EXISTS forecast_truth_join AS
SELECT
    tr.id               AS truth_id,
    tr.city,
    tr.date_iso,
    tr.condition,
    tr.threshold_c,
    tr.forecast_high_c  AS truth_forecast_c,
    tr.forecast_source  AS truth_forecast_source,
    tr.observed_high_c,
    tr.observed_source,
    tr.resolution_outcome,
    tr.bot_had_position,
    tr.bot_side,
    tr.snapshot_ts_utc,
    fs.id               AS forecast_snapshot_id,
    fs.forecast_high_c  AS snapshot_forecast_c,
    fs.source           AS snapshot_source,
    fs.ts_utc           AS snapshot_recorded_at
FROM truth_records tr
LEFT JOIN forecast_snapshots fs
    ON fs.city = tr.city
   AND fs.target_date = tr.date_iso;

-- ─── Vista v_decision_truth ───────────────────────────────────────────────────
-- Vista de calibración: determina si el forecast del bot era correcto
-- (forecast_correct) y si la posición abierta era correcta (position_correct).
-- NULL cuando el outcome es UNKNOWN/VOID o el forecast está ausente.
-- Solo observación; no genera señales ejecutables.
CREATE VIEW IF NOT EXISTS v_decision_truth AS
SELECT
    tr.id,
    tr.city,
    tr.date_iso,
    tr.condition,
    tr.threshold_c,
    tr.forecast_high_c,
    tr.observed_high_c,
    tr.resolution_outcome,
    tr.bot_had_position,
    tr.bot_side,
    tr.snapshot_ts_utc,
    CASE
        WHEN tr.resolution_outcome IN ('UNKNOWN', 'VOID') THEN NULL
        WHEN tr.forecast_high_c IS NULL                  THEN NULL
        WHEN tr.condition = 'exact'
             AND tr.resolution_outcome = 'YES'
             AND tr.forecast_high_c >= tr.threshold_c    THEN 1
        WHEN tr.condition = 'exact'
             AND tr.resolution_outcome = 'NO'
             AND tr.forecast_high_c < tr.threshold_c     THEN 1
        WHEN tr.condition = 'range'
             AND tr.resolution_outcome = 'YES'
             AND tr.forecast_high_c >= tr.threshold_c    THEN 1
        WHEN tr.condition = 'range'
             AND tr.resolution_outcome = 'NO'
             AND tr.forecast_high_c < tr.threshold_c     THEN 1
        ELSE 0
    END AS forecast_correct,
    CASE
        WHEN tr.bot_had_position = 1
             AND tr.resolution_outcome NOT IN ('UNKNOWN', 'VOID')
        THEN
            CASE WHEN tr.bot_side = tr.resolution_outcome THEN 1 ELSE 0 END
        ELSE NULL
    END AS position_correct
FROM truth_records tr;

-- ─── Registrar versión ───────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (2, datetime('now'));
