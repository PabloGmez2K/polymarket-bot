#!/usr/bin/env python3
"""
Build the offline canonical decision dataset for predictive evaluation.

This is a local LOG_ONLY builder. It reads only explicit allowlisted inputs,
writes only the requested SQLite DB plus data/predictive summaries/conflicts,
and does not import bot.py or touch live trading state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools._canonical_resolver import bsr_no_would_win

DATA_DIR = REPO_ROOT / "data"
PREDICTIVE_DIR = DATA_DIR / "predictive"

DEFAULT_DB = PREDICTIVE_DIR / "decision_dataset.db"
DEFAULT_EXACT_NO_RESOLUTIONS = DATA_DIR / "exact_no_resolutions_log_only.jsonl"
DEFAULT_BSR_RESOLUTIONS = DATA_DIR / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
FALLBACK_BSR_RESOLUTIONS = DATA_DIR / "blocked_signals_resolutions.jsonl"
DEFAULT_BOT_SIGNAL_EVALUATIONS = DATA_DIR / "runtime_import" / "bot_signal_evaluations.jsonl"
DEFAULT_SUMMARY = PREDICTIVE_DIR / "decision_dataset_summary.json"
DEFAULT_CONFLICTS = PREDICTIVE_DIR / "resolution_conflicts.jsonl"

ALLOWED_SOURCE_KEYS = frozenset(
    {
        "exact_no_resolutions",
        "blocked_signals_resolutions",
        "bot_signal_evaluations",
    }
)

DELTA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("market_prob_at_eval", "REAL"),
    ("model_prob", "REAL"),
    ("side", "TEXT"),
    ("sim_unit_pnl", "REAL"),
    ("eval_source", "TEXT"),
    ("resolution_status", "TEXT"),
    ("maturity_bucket", "TEXT"),
    ("cohort_key", "TEXT"),
    ("days_ahead", "INTEGER"),
    ("edge_pct_at_eval", "REAL"),
    ("decision_id", "TEXT"),
    ("data_provenance", "TEXT"),
    ("unit_raw", "TEXT"),
)

BASE_COLUMNS = {
    "city",
    "date_iso",
    "condition",
    "threshold_c",
    "question",
    "market_id",
    "token_id_yes",
    "token_id_no",
    "forecast_high_c",
    "forecast_source",
    "observed_high_c",
    "observed_source",
    "resolution_outcome",
    "resolution_ts_utc",
    "resolution_method",
    "bot_had_position",
    "bot_side",
    "snapshot_ts_utc",
    "payload_json",
}

WRITE_COLUMNS = [
    "city",
    "date_iso",
    "condition",
    "threshold_c",
    "question",
    "market_id",
    "token_id_yes",
    "token_id_no",
    "forecast_high_c",
    "forecast_source",
    "observed_high_c",
    "observed_source",
    "resolution_outcome",
    "resolution_ts_utc",
    "resolution_method",
    "bot_had_position",
    "bot_side",
    "snapshot_ts_utc",
    "payload_json",
    "market_prob_at_eval",
    "model_prob",
    "side",
    "sim_unit_pnl",
    "eval_source",
    "resolution_status",
    "maturity_bucket",
    "cohort_key",
    "days_ahead",
    "edge_pct_at_eval",
    "decision_id",
    "data_provenance",
    "unit_raw",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).strip())
            current = []
    if current:
        statements.append("\n".join(current).strip())
    return statements


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _apply_script(conn: sqlite3.Connection, path: Path) -> None:
    for stmt in _split_sql_statements(_read_text(path)):
        if stmt.upper().startswith("PRAGMA JOURNAL_MODE"):
            continue
        try:
            conn.execute(stmt)
        except sqlite3.Error as exc:
            preview = " ".join(stmt.split())[:220]
            raise sqlite3.OperationalError(f"{exc}; while applying {path.name}: {preview}") from exc


def apply_schema(db_path: Path) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        _apply_script(conn, REPO_ROOT / "sql" / "001_init.sql")
        _apply_script(conn, REPO_ROOT / "sql" / "002_truth_pipeline.sql")

        existing = _table_columns(conn, "truth_records")
        added: list[str] = []
        for name, coltype in DELTA_COLUMNS:
            if name not in existing:
                conn.execute(f"ALTER TABLE truth_records ADD COLUMN {name} {coltype}")
                added.append(name)

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_truth_decision_id
            ON truth_records (decision_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_truth_dataset_benchmark
            ON truth_records (maturity_bucket, eval_source, cohort_key)
            """
        )
        _replace_views(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (3, datetime('now'))"
        )
        conn.commit()
        return {"status": "applied", "version": 3, "columns_added": added}
    finally:
        conn.close()


def _replace_views(conn: sqlite3.Connection) -> None:
    sql = _read_text(REPO_ROOT / "sql" / "003_decision_dataset.sql")
    view_started = False
    statements: list[str] = []
    for stmt in _split_sql_statements(sql):
        upper = stmt.upper()
        if upper.startswith("DROP VIEW") or upper.startswith("CREATE VIEW"):
            view_started = True
        if view_started and (
            upper.startswith("DROP VIEW")
            or upper.startswith("CREATE VIEW")
            or upper.startswith("CREATE UNIQUE INDEX")
            or upper.startswith("CREATE INDEX")
        ):
            statements.append(stmt)
    for stmt in statements:
        conn.execute(stmt)


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _threshold_c(value: Any, unit: str | None) -> float | None:
    raw = _to_float(value)
    if raw is None:
        return None
    if (unit or "").upper() == "F":
        return round((raw - 32.0) * 5.0 / 9.0, 6)
    return raw


def _days_bucket(days_ahead: int | None) -> str:
    if days_ahead is None:
        return "unknown"
    if days_ahead <= 1:
        return "0-1"
    if days_ahead <= 3:
        return "2-3"
    if days_ahead <= 7:
        return "4-7"
    return "8+"


def _edge_bucket(edge_pct: float | None) -> str:
    if edge_pct is None:
        return "unknown"
    edge = abs(edge_pct)
    if edge < 5.0:
        return "<5%"
    if edge < 15.0:
        return "5-15%"
    if edge < 30.0:
        return "15-30%"
    return "30%+"


def build_cohort_key(condition: str | None, side: str | None, days_ahead: int | None, edge_pct: float | None) -> str:
    return "|".join(
        [
            condition or "UNKNOWN",
            side or "UNKNOWN",
            _days_bucket(days_ahead),
            _edge_bucket(edge_pct),
        ]
    )


def stable_decision_id(eval_key: str, side: str, eval_source: str, snapshot_bucket: str) -> str:
    raw = f"{eval_key}|{side}|{eval_source}|{snapshot_bucket}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _status_from_row(row: dict[str, Any]) -> str:
    if row.get("market_outcome") in {"YES", "NO"}:
        return "settled"
    if row.get("bucket") == "void":
        return "void"
    return "pending"


def _resolved_at_or_now(row: dict[str, Any]) -> str:
    return row.get("resolved_at") or row.get("ts_utc") or datetime.now(timezone.utc).isoformat()


def normalize_exact_no_resolution(row: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    side = (row.get("best_side_log_only") or "NO").upper()
    eval_source = "exact_no"
    eval_key = row.get("eval_key") or ""
    snapshot_bucket = row.get("resolved_at") or row.get("date_iso") or row.get("market_id") or "unknown"
    decision_id = stable_decision_id(eval_key, side, eval_source, snapshot_bucket)
    market_prob = _to_float(row.get("p_market_no_at_eval"))
    model_prob = _to_float(row.get("p_model_no"))
    edge = _to_float(row.get("entry_edge_log_only"))
    if edge is None and market_prob is not None and model_prob is not None:
        edge = round((model_prob - market_prob) * 100.0, 6)
    days_ahead = _to_int(row.get("days_ahead"))
    condition = row.get("condition") or "UNKNOWN"
    resolution_outcome = row.get("market_outcome") or "UNKNOWN"
    maturity_bucket = row.get("bucket") or "pending"
    payload = {
        "source_row": row,
        "sim_unit_pnl_is": "simulated_non_canonical_not_money",
        "eligible_for_policy": False,
    }
    return {
        "city": row.get("city"),
        "date_iso": row.get("date_iso"),
        "condition": condition,
        "threshold_c": _threshold_c(row.get("threshold"), row.get("unit")),
        "question": None,
        "market_id": str(row.get("market_id") or ""),
        "token_id_yes": None,
        "token_id_no": None,
        "forecast_high_c": None,
        "forecast_source": None,
        "observed_high_c": None,
        "observed_source": None,
        "resolution_outcome": resolution_outcome,
        "resolution_ts_utc": row.get("resolved_at"),
        "resolution_method": row.get("resolution_source") or None,
        "bot_had_position": 0,
        "bot_side": None,
        "snapshot_ts_utc": _resolved_at_or_now(row),
        "payload_json": _json_dumps(payload),
        "market_prob_at_eval": market_prob,
        "model_prob": model_prob,
        "side": side,
        "sim_unit_pnl": _to_float(row.get("simulated_unit_pnl")),
        "eval_source": eval_source,
        "resolution_status": _status_from_row(row),
        "maturity_bucket": maturity_bucket,
        "cohort_key": build_cohort_key(condition, side, days_ahead, edge),
        "days_ahead": days_ahead,
        "edge_pct_at_eval": edge,
        "decision_id": decision_id,
        "data_provenance": _json_dumps(provenance),
        "unit_raw": row.get("unit"),
    }


def _load_bsr_rows(path: Path) -> dict[str, dict[str, Any]]:
    return {row.get("match_key"): row for row in _iter_jsonl(path) if row.get("match_key") and row.get("resolved")}


def _write_conflicts(conflicts_path: Path, conflicts: list[dict[str, Any]]) -> None:
    if not conflicts:
        return
    conflicts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(conflicts_path, "w", encoding="utf-8") as fh:
        for row in conflicts:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _cross_check_exact_with_bsr(rows: list[dict[str, Any]], bsr_index: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        eval_key = row.get("eval_key") or ""
        bsr = bsr_index.get(eval_key)
        if not bsr:
            accepted.append(row)
            continue
        gamma_no = row.get("no_would_win")
        bsr_no = bsr_no_would_win(bsr)
        if gamma_no is not None and bsr_no is not None and bool(gamma_no) != bool(bsr_no):
            conflicts.append(
                {
                    "eval_key": eval_key,
                    "market_id": row.get("market_id"),
                    "gamma_no_would_win": gamma_no,
                    "bsr_no_would_win": bsr_no,
                    "reason": "gamma_bsr_mismatch",
                }
            )
            continue
        accepted.append(row)
    return accepted, conflicts


def upsert_records(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> dict[str, int]:
    inserted = 0
    updated = 0
    placeholders = ",".join("?" for _ in WRITE_COLUMNS)
    update_cols = [col for col in WRITE_COLUMNS if col != "decision_id"]
    assignments = ",".join(f"{col}=excluded.{col}" for col in update_cols)
    sql = (
        f"INSERT INTO truth_records ({','.join(WRITE_COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(decision_id) DO UPDATE SET {assignments}"
    )
    for record in records:
        existed = conn.execute(
            "SELECT 1 FROM truth_records WHERE decision_id=?",
            (record["decision_id"],),
        ).fetchone()
        conn.execute(sql, [record.get(col) for col in WRITE_COLUMNS])
        if existed:
            updated += 1
        else:
            inserted += 1
    return {"inserted": inserted, "updated": updated}


def _summary_from_db(conn: sqlite3.Connection, inputs: dict[str, Any], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT eval_source, cohort_key, maturity_bucket, side, resolution_outcome,
               sim_unit_pnl, model_prob, market_prob_at_eval
        FROM truth_records
        WHERE eval_source IS NOT NULL
        """
    ).fetchall()
    by_cohort: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["cohort_key"] or "UNKNOWN"
        bucket_counts = by_cohort.setdefault(
            key,
            {
                "eval_source": row["eval_source"],
                "n": 0,
                "maturity_counts": Counter(),
                "settled_mature": {
                    "n": 0,
                    "wins": 0,
                    "sim_pnl": 0.0,
                    "calibration_components": [],
                    "brier_model": [],
                    "brier_market": [],
                },
            },
        )
        bucket_counts["n"] += 1
        bucket_counts["maturity_counts"][row["maturity_bucket"] or "UNKNOWN"] += 1
        if row["maturity_bucket"] == "settled_mature" and row["resolution_outcome"] in {"YES", "NO"}:
            sm = bucket_counts["settled_mature"]
            outcome01 = 1.0 if row["side"] == row["resolution_outcome"] else 0.0
            sm["n"] += 1
            sm["wins"] += int(outcome01)
            if row["sim_unit_pnl"] is not None:
                sm["sim_pnl"] += float(row["sim_unit_pnl"])
            if row["model_prob"] is not None:
                model = float(row["model_prob"])
                sm["calibration_components"].append(model - outcome01)
                sm["brier_model"].append((model - outcome01) ** 2)
            if row["market_prob_at_eval"] is not None:
                market = float(row["market_prob_at_eval"])
                sm["brier_market"].append((market - outcome01) ** 2)

    cohorts: dict[str, Any] = {}
    for key, value in sorted(by_cohort.items()):
        sm = value["settled_mature"]
        n = sm["n"]
        brier_advantage = None
        if sm["brier_model"] and sm["brier_market"]:
            brier_advantage = round(
                (sum(sm["brier_market"]) / len(sm["brier_market"]))
                - (sum(sm["brier_model"]) / len(sm["brier_model"])),
                6,
            )
        cohorts[key] = {
            "eval_source": value["eval_source"],
            "n": value["n"],
            "maturity_counts": dict(value["maturity_counts"]),
            "settled_mature": {
                "n": n,
                "win_rate": round(sm["wins"] / n, 4) if n else None,
                "sim_pnl": round(sm["sim_pnl"], 4) if n else None,
                "calibration_gap": (
                    round(sum(sm["calibration_components"]) / len(sm["calibration_components"]), 4)
                    if sm["calibration_components"]
                    else None
                ),
                "brier_advantage": brier_advantage,
            },
        }

    total = conn.execute("SELECT COUNT(*) FROM truth_records WHERE eval_source IS NOT NULL").fetchone()[0]
    benchmark_n = conn.execute("SELECT COUNT(*) FROM v_benchmark_input").fetchone()[0]
    exact = conn.execute(
        """
        SELECT COUNT(*) AS n,
               SUM(CASE WHEN resolution_outcome='NO' THEN 1 ELSE 0 END) AS no_wins,
               SUM(COALESCE(sim_unit_pnl, 0)) AS sim_pnl,
               AVG(model_prob - CASE WHEN resolution_outcome='NO' THEN 1.0 ELSE 0.0 END) AS calibration_gap
        FROM truth_records
        WHERE eval_source='exact_no' AND maturity_bucket='settled_mature'
        """
    ).fetchone()

    return {
        "schema_version": "decision_dataset_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "rows": total,
            "benchmark_input_rows": benchmark_n,
            "pnl_label": "simulated_non_canonical_not_money",
            "eligible_for_policy": False,
        },
        "inputs": inputs,
        "conflicts": {"count": len(conflicts)},
        "proto_r2_exact_no": {
            "settled_mature_n": exact["n"],
            "WR_NO": round((exact["no_wins"] or 0) / exact["n"], 4) if exact["n"] else None,
            "sim_pnl": round(exact["sim_pnl"], 4) if exact["n"] else None,
            "calibration_gap": round(exact["calibration_gap"], 4) if exact["n"] else None,
        },
        "cohorts": cohorts,
    }


def build_dataset(
    db_path: Path,
    exact_no_resolutions: Path | None,
    blocked_signals_resolutions: Path | None,
    bot_signal_evaluations: Path | None,
    output_summary: Path,
    conflicts_path: Path = DEFAULT_CONFLICTS,
) -> dict[str, Any]:
    apply_schema(db_path)

    exact_path = exact_no_resolutions
    bsr_path = blocked_signals_resolutions
    if bsr_path is None or not bsr_path.exists():
        bsr_path = FALLBACK_BSR_RESOLUTIONS if FALLBACK_BSR_RESOLUTIONS.exists() else bsr_path

    source_state: dict[str, Any] = {
        "allowlist": sorted(ALLOWED_SOURCE_KEYS),
        "exact_no_resolutions": {"path": str(exact_path) if exact_path else None, "present": bool(exact_path and exact_path.exists())},
        "blocked_signals_resolutions": {"path": str(bsr_path) if bsr_path else None, "present": bool(bsr_path and bsr_path.exists())},
        "bot_signal_evaluations": {"path": str(bot_signal_evaluations) if bot_signal_evaluations else None, "present": bool(bot_signal_evaluations and bot_signal_evaluations.exists()), "status": "deferred_if_absent"},
    }

    records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    if exact_path and exact_path.exists():
        provenance = {
            "source_file": exact_path.name,
            "sha256": _file_sha256(exact_path),
            "capture_method": "local_allowlist",
            "capture_ts": datetime.now(timezone.utc).isoformat(),
        }
        exact_rows = _iter_jsonl(exact_path)
        bsr_index = _load_bsr_rows(bsr_path) if bsr_path and bsr_path.exists() else {}
        accepted, conflicts = _cross_check_exact_with_bsr(exact_rows, bsr_index)
        records.extend(normalize_exact_no_resolution(row, provenance) for row in accepted)
        source_state["exact_no_resolutions"]["rows"] = len(exact_rows)
        source_state["exact_no_resolutions"]["accepted_rows"] = len(accepted)
        source_state["blocked_signals_resolutions"]["resolved_index_rows"] = len(bsr_index)

    _write_conflicts(conflicts_path, conflicts)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        counts = upsert_records(conn, records)
        conn.commit()
        summary = _summary_from_db(conn, source_state, conflicts)
        summary["write_counts"] = counts
    finally:
        conn.close()

    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build offline canonical decision dataset")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--exact-no-resolutions", default=str(DEFAULT_EXACT_NO_RESOLUTIONS))
    parser.add_argument("--blocked-signals-resolutions", default=str(DEFAULT_BSR_RESOLUTIONS))
    parser.add_argument("--bot-signal-evaluations", default=str(DEFAULT_BOT_SIGNAL_EVALUATIONS))
    parser.add_argument("--output-summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--today", default=None, help="Reserved for resolver-compatible deterministic runs")
    args = parser.parse_args(argv)

    summary = build_dataset(
        db_path=Path(args.db),
        exact_no_resolutions=Path(args.exact_no_resolutions) if args.exact_no_resolutions else None,
        blocked_signals_resolutions=Path(args.blocked_signals_resolutions) if args.blocked_signals_resolutions else None,
        bot_signal_evaluations=Path(args.bot_signal_evaluations) if args.bot_signal_evaluations else None,
        output_summary=Path(args.output_summary),
    )
    print(json.dumps({"status": "ok", "summary": summary["dataset"], "proto_r2_exact_no": summary["proto_r2_exact_no"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
