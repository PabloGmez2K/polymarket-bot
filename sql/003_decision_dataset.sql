-- sql/003_decision_dataset.sql - E1 Canonical Decision Dataset delta
-- Additive schema for offline learning/eval. No trading or cash accounting.

-- NOTE: SQLite versions used in tests may not support
-- ALTER TABLE ... ADD COLUMN IF NOT EXISTS. The builder applies these columns
-- idempotently by checking PRAGMA table_info before each ALTER.

ALTER TABLE truth_records ADD COLUMN market_prob_at_eval REAL;
ALTER TABLE truth_records ADD COLUMN model_prob REAL;
ALTER TABLE truth_records ADD COLUMN side TEXT;
ALTER TABLE truth_records ADD COLUMN sim_unit_pnl REAL;
ALTER TABLE truth_records ADD COLUMN eval_source TEXT;
ALTER TABLE truth_records ADD COLUMN resolution_status TEXT;
ALTER TABLE truth_records ADD COLUMN maturity_bucket TEXT;
ALTER TABLE truth_records ADD COLUMN cohort_key TEXT;
ALTER TABLE truth_records ADD COLUMN days_ahead INTEGER;
ALTER TABLE truth_records ADD COLUMN edge_pct_at_eval REAL;
ALTER TABLE truth_records ADD COLUMN decision_id TEXT;
ALTER TABLE truth_records ADD COLUMN data_provenance TEXT;
ALTER TABLE truth_records ADD COLUMN unit_raw TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_truth_decision_id
    ON truth_records (decision_id);

CREATE INDEX IF NOT EXISTS idx_truth_dataset_benchmark
    ON truth_records (maturity_bucket, eval_source, cohort_key);

DROP VIEW IF EXISTS v_benchmark_input;
DROP VIEW IF EXISTS v_decision_truth;

CREATE VIEW v_decision_truth AS
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
    tr.market_prob_at_eval,
    tr.model_prob,
    tr.side,
    tr.sim_unit_pnl,
    tr.eval_source,
    tr.resolution_status,
    tr.maturity_bucket,
    tr.cohort_key,
    tr.days_ahead,
    tr.edge_pct_at_eval,
    tr.decision_id,
    tr.data_provenance,
    tr.unit_raw,
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

CREATE VIEW v_benchmark_input AS
SELECT
    id,
    decision_id,
    city,
    date_iso,
    snapshot_ts_utc,
    condition,
    threshold_c,
    side,
    resolution_outcome,
    CASE WHEN side = resolution_outcome THEN 1 ELSE 0 END AS outcome01,
    model_prob,
    market_prob_at_eval,
    sim_unit_pnl,
    eval_source,
    cohort_key,
    days_ahead,
    edge_pct_at_eval,
    maturity_bucket
FROM truth_records
WHERE maturity_bucket = 'settled_mature'
  AND model_prob IS NOT NULL
  AND market_prob_at_eval IS NOT NULL
  AND resolution_outcome IN ('YES', 'NO')
  AND side IN ('YES', 'NO');

INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (3, datetime('now'));
