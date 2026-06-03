#!/usr/bin/env python3
"""Offline predictor-vs-market benchmark for the E1 decision dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB = REPO_ROOT / "data" / "predictive" / "decision_dataset_runtime.db"
DEFAULT_OUTPUT_SUMMARY = REPO_ROOT / "data" / "predictive" / "benchmark_summary.json"
DEFAULT_DATASET_SUMMARY = REPO_ROOT / "data" / "predictive" / "decision_dataset_summary.json"

SCHEMA_VERSION = "predictor_benchmark_summary_v1"
DISCLAIMER = (
    "sim_pnl simulated_non_canonical_not_money. eligible_for_policy=false. "
    "market_truth_canonical=false. No trading authorization."
)
DEFAULT_CUTOFF_UTC = "2026-05-29T00:00:00+00:00"
DEFAULT_BOOTSTRAP_SAMPLES = 1000
DEFAULT_SEED = 2026

N_REVIEW = 20
N_PROMOTE_FLOOR = 30
MARGIN = 0.01
SIMPNL_FLOOR = 0.0
FDR_Q = 0.10

PARTITIONS = ("evidence_frozen", "forward_holdout")
LEVELS = ("L0", "L1", "L2")
FORBIDDEN_OUTPUT_TOKENS = ("eval_key", "decision_id", "order_id", "wallet")


@dataclass(frozen=True)
class InputRow:
    city: str | None
    date_iso: str | None
    snapshot_ts_utc: str | None
    condition: str
    side: str
    resolution_outcome: str
    outcome01: int
    model_prob: float
    market_prob_at_eval: float
    sim_unit_pnl: float | None
    eval_source: str | None
    cohort_key: str
    days_ahead: int | None
    edge_pct_at_eval: float | None
    maturity_bucket: str | None


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def partition_for_snapshot(snapshot_ts_utc: str | None, cutoff: datetime) -> str:
    parsed = _parse_ts(snapshot_ts_utc)
    if parsed is None:
        return "evidence_frozen"
    return "forward_holdout" if parsed >= cutoff else "evidence_frozen"


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def _brier_advantage(rows: list[InputRow]) -> float | None:
    if not rows:
        return None
    brier_model = _mean([(r.model_prob - r.outcome01) ** 2 for r in rows])
    brier_market = _mean([(r.market_prob_at_eval - r.outcome01) ** 2 for r in rows])
    if brier_model is None or brier_market is None:
        return None
    return brier_market - brier_model


def _stable_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return seed + int(digest, 16)


def _percentile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return sorted_values[int(pos)]
    weight = pos - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def bootstrap_advantage(
    rows: list[InputRow],
    samples: int,
    seed: int,
    seed_key: str,
) -> tuple[tuple[float | None, float | None], float | None]:
    if not rows or samples <= 0:
        return (None, None), None
    rng = random.Random(_stable_seed(seed, seed_key))
    n = len(rows)
    values: list[float] = []
    for _ in range(samples):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        adv = _brier_advantage(sample)
        if adv is not None:
            values.append(adv)
    values.sort()
    if not values:
        return (None, None), None
    lower = _percentile(values, 0.025)
    upper = _percentile(values, 0.975)
    p_raw = sum(1 for value in values if value <= 0.0) / len(values)
    return (lower, upper), p_raw


def _cell_key(level: str, row: InputRow) -> str:
    if level == "L0":
        return "pooled"
    if level == "L1":
        return f"{row.condition}|{row.side}"
    return row.cohort_key


def _firewalled_exact_no(cohort: str) -> bool:
    parts = cohort.split("|")
    return len(parts) >= 2 and parts[0] == "exact" and parts[1] == "NO"


def _metrics_for_rows(rows: list[InputRow], samples: int, seed: int, seed_key: str) -> dict[str, Any]:
    n = len(rows)
    if not rows:
        return {
            "n": 0,
            "WR": None,
            "brier_model": None,
            "brier_market": None,
            "brier_advantage": None,
            "calibration_gap": None,
            "sim_unit_pnl_total": None,
            "sim_unit_pnl_mean": None,
            "mean_model_prob": None,
            "mean_market_prob": None,
            "observed_rate": None,
            "brier_advantage_ci": {"lower": None, "upper": None},
            "p_raw": None,
        }

    wins = [float(r.outcome01) for r in rows]
    model_probs = [r.model_prob for r in rows]
    market_probs = [r.market_prob_at_eval for r in rows]
    sim_pnls = [float(r.sim_unit_pnl) for r in rows if r.sim_unit_pnl is not None]
    brier_model = _mean([(r.model_prob - r.outcome01) ** 2 for r in rows])
    brier_market = _mean([(r.market_prob_at_eval - r.outcome01) ** 2 for r in rows])
    brier_adv = (brier_market - brier_model) if brier_model is not None and brier_market is not None else None
    ci, p_raw = bootstrap_advantage(rows, samples=samples, seed=seed, seed_key=seed_key)
    return {
        "n": n,
        "WR": _round(_mean(wins), 4),
        "brier_model": _round(brier_model),
        "brier_market": _round(brier_market),
        "brier_advantage": _round(brier_adv),
        "calibration_gap": _round(_mean([r.model_prob - r.outcome01 for r in rows])),
        "sim_unit_pnl_total": _round(sum(sim_pnls) if sim_pnls else None),
        "sim_unit_pnl_mean": _round(_mean(sim_pnls)),
        "mean_model_prob": _round(_mean(model_probs)),
        "mean_market_prob": _round(_mean(market_probs)),
        "observed_rate": _round(_mean(wins), 4),
        "brier_advantage_ci": {"lower": _round(ci[0]), "upper": _round(ci[1])},
        "p_raw": _round(p_raw),
    }


def _sign_consistent(forward_adv: float | None, frozen_adv: float | None) -> bool:
    if forward_adv is None or frozen_adv is None:
        return False
    return (forward_adv > 0 and frozen_adv > 0) or (forward_adv < 0 and frozen_adv < 0)


def _base_verdict(metrics: dict[str, Any], frozen_metrics: dict[str, Any] | None) -> str:
    n = int(metrics["n"])
    adv = metrics["brier_advantage"]
    ci = metrics["brier_advantage_ci"]
    sim_mean = metrics["sim_unit_pnl_mean"]
    frozen_adv = frozen_metrics.get("brier_advantage") if frozen_metrics else None
    if n < N_REVIEW:
        return "INSUFFICIENT_N"
    if n < N_PROMOTE_FLOOR:
        return "NEEDS_MORE_DATA"
    if adv is not None and ci["upper"] is not None and ci["upper"] < 0:
        return "KILL_MODEL_PATH"
    if adv is not None and adv <= 0:
        return "NO_EDGE"
    if (
        adv is not None
        and adv > MARGIN
        and ci["lower"] is not None
        and ci["lower"] > 0
        and sim_mean is not None
        and sim_mean > SIMPNL_FLOOR
        and _sign_consistent(adv, frozen_adv)
    ):
        return "BEATS_MARKET"
    return "NO_EDGE"


def _bh_adjust(pairs: list[tuple[int, float]], total_cells: int) -> dict[int, float]:
    if not pairs:
        return {}
    ordered = sorted(pairs, key=lambda item: item[1])
    adjusted: dict[int, float] = {}
    running = 1.0
    for rank_from_end, (idx, p_value) in enumerate(reversed(ordered), start=1):
        rank = total_cells - rank_from_end + 1
        running = min(running, p_value * total_cells / rank)
        adjusted[idx] = min(1.0, running)
    return adjusted


def _summary_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_dataset_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def open_readonly_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Decision dataset DB not found: {db_path}. Run tools/decision_dataset_builder.py before E2."
        )
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def load_rows(db_path: Path) -> tuple[list[InputRow], list[str]]:
    warnings: list[str] = []
    conn = open_readonly_db(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(v_benchmark_input)").fetchall()}
        if "maturity_bucket" in columns:
            bad = conn.execute(
                "SELECT COUNT(*) FROM v_benchmark_input WHERE maturity_bucket!='settled_mature'"
            ).fetchone()[0]
            if bad:
                raise ValueError("v_benchmark_input exposed non-settled_mature rows")
        rows = conn.execute(
            """
            SELECT city, date_iso, snapshot_ts_utc, condition, side, resolution_outcome,
                   outcome01, model_prob, market_prob_at_eval, sim_unit_pnl,
                   eval_source, cohort_key, days_ahead, edge_pct_at_eval, maturity_bucket
            FROM v_benchmark_input
            """
        ).fetchall()
    finally:
        conn.close()

    parsed: list[InputRow] = []
    for row in rows:
        model_prob = float(row["model_prob"])
        market_prob = float(row["market_prob_at_eval"])
        if not 0.0 <= model_prob <= 1.0 or not 0.0 <= market_prob <= 1.0:
            raise ValueError("v_benchmark_input contains probability outside [0,1]")
        parsed.append(
            InputRow(
                city=row["city"],
                date_iso=row["date_iso"],
                snapshot_ts_utc=row["snapshot_ts_utc"],
                condition=row["condition"],
                side=row["side"],
                resolution_outcome=row["resolution_outcome"],
                outcome01=int(row["outcome01"]),
                model_prob=model_prob,
                market_prob_at_eval=market_prob,
                sim_unit_pnl=float(row["sim_unit_pnl"]) if row["sim_unit_pnl"] is not None else None,
                eval_source=row["eval_source"],
                cohort_key=row["cohort_key"],
                days_ahead=row["days_ahead"],
                edge_pct_at_eval=row["edge_pct_at_eval"],
                maturity_bucket=row["maturity_bucket"] if "maturity_bucket" in row.keys() else None,
            )
        )
    return parsed, warnings


def _coverage_warnings(rows: list[InputRow], dataset_summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not any(row.condition in {"at_or_above", "at_or_below"} for row in rows):
        warnings.append("directional_bse_rows_absent")
    if any(row.condition == "exact" and row.side == "NO" for row in rows):
        warnings.append("exact_no_firewall_applied")
    bse = dataset_summary.get("bse_directional_at_or_above", {})
    if bse.get("acceptance_status") and bse.get("acceptance_status") != "REPRODUCED":
        warnings.append(f"bse_directional_acceptance_status:{bse.get('acceptance_status')}")
    return warnings


def build_summary(
    rows: list[InputRow],
    dataset_summary: dict[str, Any],
    dataset_summary_sha: str | None,
    cutoff_utc: str,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    cutoff = _parse_ts(cutoff_utc)
    if cutoff is None:
        raise ValueError(f"Invalid cutoff UTC: {cutoff_utc}")

    grouped: dict[tuple[str, str, str], list[InputRow]] = defaultdict(list)
    for row in rows:
        partition = partition_for_snapshot(row.snapshot_ts_utc, cutoff)
        for level in LEVELS:
            grouped[(level, _cell_key(level, row), partition)].append(row)

    cells: list[dict[str, Any]] = []
    by_level_cohort_partition: dict[tuple[str, str, str], dict[str, Any]] = {}
    all_level_cohorts = sorted({(level, cohort) for level, cohort, _ in grouped.keys()})
    for level, cohort in all_level_cohorts:
        for partition in PARTITIONS:
            cell_rows = grouped.get((level, cohort, partition), [])
            metrics = _metrics_for_rows(
                cell_rows,
                samples=bootstrap_samples,
                seed=seed,
                seed_key=f"{level}|{cohort}|{partition}",
            )
            cell = {
                "level": level,
                "cohort": cohort,
                "partition": partition,
                "promotion_surface": level == "L1",
                "policy_firewall": "exact_no_firewall" if _firewalled_exact_no(cohort) else None,
                **metrics,
                "p_fdr": None,
                "diagnostic_verdict": None,
                "verdict": None,
            }
            by_level_cohort_partition[(level, cohort, partition)] = cell
            cells.append(cell)

    for cell in cells:
        if cell["partition"] != "forward_holdout":
            cell["verdict"] = "DIAGNOSTIC_ONLY"
            continue
        frozen = by_level_cohort_partition.get((cell["level"], cell["cohort"], "evidence_frozen"))
        diagnostic = _base_verdict(cell, frozen)
        cell["diagnostic_verdict"] = diagnostic
        if cell["policy_firewall"]:
            cell["verdict"] = "NON_PROMOTABLE_BY_POLICY"
        elif cell["level"] == "L2":
            cell["verdict"] = f"{diagnostic}_DIAGNOSTIC_ONLY"
        else:
            cell["verdict"] = diagnostic

    tested = [
        (idx, float(cell["p_raw"]))
        for idx, cell in enumerate(cells)
        if cell["level"] == "L1"
        and cell["partition"] == "forward_holdout"
        and cell["n"] >= N_REVIEW
        and cell["p_raw"] is not None
        and not cell["policy_firewall"]
    ]
    fdr_adjusted = _bh_adjust(tested, len(tested))
    for idx, p_fdr in fdr_adjusted.items():
        cells[idx]["p_fdr"] = _round(p_fdr)

    l0_forward = by_level_cohort_partition.get(("L0", "pooled", "forward_holdout"))
    l0_adv = l0_forward.get("brier_advantage") if l0_forward else None
    for cell in cells:
        if (
            cell["level"] == "L1"
            and cell["partition"] == "forward_holdout"
            and cell["verdict"] == "BEATS_MARKET"
        ):
            if l0_adv is None or l0_adv < 0:
                cell["verdict"] = "BEATS_MARKET_L0_SIGN_CONTRADICTED"
            elif cell["p_fdr"] is None or cell["p_fdr"] > FDR_Q:
                cell["verdict"] = "BEATS_MARKET_FDR_NOT_PASSED"
            else:
                cell["verdict"] = "CANDIDATE_FOR_CANARY_REVIEW"

    top_candidates = [
        {
            "cohort": cell["cohort"],
            "n": cell["n"],
            "brier_advantage": cell["brier_advantage"],
            "brier_advantage_ci": cell["brier_advantage_ci"],
            "sim_unit_pnl_mean": cell["sim_unit_pnl_mean"],
            "p_fdr": cell["p_fdr"],
            "verdict": cell["verdict"],
        }
        for cell in cells
        if cell["verdict"] == "CANDIDATE_FOR_CANARY_REVIEW"
    ]
    killed_cohorts = [
        {"level": cell["level"], "cohort": cell["cohort"], "n": cell["n"], "verdict": cell["verdict"]}
        for cell in cells
        if cell["partition"] == "forward_holdout" and "KILL_MODEL_PATH" in str(cell["verdict"])
    ]

    l1_forward = [
        cell for cell in cells if cell["level"] == "L1" and cell["partition"] == "forward_holdout"
    ]
    if top_candidates:
        global_verdict = "CANDIDATE_FOR_CANARY_REVIEW"
    elif not any(cell["n"] >= N_REVIEW for cell in l1_forward):
        global_verdict = "INSUFFICIENT_N"
    elif any(N_REVIEW <= cell["n"] < N_PROMOTE_FLOOR for cell in l1_forward):
        global_verdict = "NEEDS_MORE_DATA"
    elif any(cell["diagnostic_verdict"] == "KILL_MODEL_PATH" for cell in l1_forward):
        global_verdict = "KILL_CURRENT_MODEL_PATH"
    else:
        global_verdict = "NO_EDGE_GLOBAL"

    triggers = []
    if not top_candidates:
        triggers.append(f"rerun_when_l1_forward_holdout_n_reaches_{N_PROMOTE_FLOOR}")
    if any(row.condition in {"at_or_above", "at_or_below"} for row in rows):
        triggers.append("directional_loader_present_monitor_forward_holdout")

    benchmark_rows = dataset_summary.get("dataset", {}).get("benchmark_input_rows")
    if benchmark_rows is None:
        benchmark_rows = len(rows)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "prereg_cutoff_utc": cutoff.isoformat(),
        "thresholds": {
            "N_REVIEW": N_REVIEW,
            "N_PROMOTE_FLOOR": N_PROMOTE_FLOOR,
            "MARGIN": MARGIN,
            "SIMPNL_FLOOR": SIMPNL_FLOOR,
            "FDR_Q": FDR_Q,
            "bootstrap_samples": bootstrap_samples,
            "seed": seed,
        },
        "multiplicity": {
            "method": "benjamini_hochberg",
            "q": FDR_Q,
            "tested_l1_cells": len(tested),
            "status": "applied" if tested else "not_applicable",
        },
        "dataset_provenance": {
            "summary_sha256": dataset_summary_sha,
            "benchmark_input_rows": benchmark_rows,
        },
        "coverage_warnings": _coverage_warnings(rows, dataset_summary),
        "cells": sorted(cells, key=lambda c: (c["level"], c["cohort"], c["partition"])),
        "top_candidates": top_candidates,
        "killed_cohorts": killed_cohorts,
        "global_verdict": global_verdict,
        "triggers": triggers,
        "disclaimer": DISCLAIMER,
        "eligible_for_policy": False,
    }


def _assert_sanitized(summary: dict[str, Any]) -> None:
    payload = json.dumps(summary, sort_keys=True)
    lowered = payload.lower()
    for token in FORBIDDEN_OUTPUT_TOKENS:
        if token in lowered:
            raise ValueError(f"benchmark summary contains forbidden row-level token: {token}")


def run_benchmark(
    db_path: Path,
    output_summary: Path,
    cutoff_utc: str = DEFAULT_CUTOFF_UTC,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = DEFAULT_SEED,
    dataset_summary_path: Path = DEFAULT_DATASET_SUMMARY,
) -> dict[str, Any]:
    rows, load_warnings = load_rows(db_path)
    dataset_summary = _load_dataset_summary(dataset_summary_path)
    summary = build_summary(
        rows=rows,
        dataset_summary=dataset_summary,
        dataset_summary_sha=_summary_sha256(dataset_summary_path),
        cutoff_utc=cutoff_utc,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    summary["coverage_warnings"] = sorted(set(summary["coverage_warnings"] + load_warnings))
    _assert_sanitized(summary)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E2 predictor-vs-market benchmark")
    parser.add_argument("--db", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--cutoff-utc", default=DEFAULT_CUTOFF_UTC)
    parser.add_argument("--bootstrap-samples", type=int, default=DEFAULT_BOOTSTRAP_SAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dataset-summary", default=str(DEFAULT_DATASET_SUMMARY))
    args = parser.parse_args(argv)

    try:
        summary = run_benchmark(
            db_path=Path(args.db),
            output_summary=Path(args.output_summary),
            cutoff_utc=args.cutoff_utc,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
            dataset_summary_path=Path(args.dataset_summary),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "status": "ok",
                "benchmark_input_rows": summary["dataset_provenance"]["benchmark_input_rows"],
                "global_verdict": summary["global_verdict"],
                "top_candidates": len(summary["top_candidates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
