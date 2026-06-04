#!/usr/bin/env python3
"""Offline trader-following benchmark over blocked_signals_resolutions.jsonl.

Read-only, aggregate-only E3 tool. It does not import runtime trading modules,
does not contact external APIs, and does not emit row-level identifiers or
trader handles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_SUMMARY = REPO_ROOT / "data" / "predictive" / "trader_benchmark_summary.json"

SCHEMA_VERSION = "trader_benchmark_summary_v1"
DISCLAIMER = (
    "sim_pnl simulated_non_canonical_not_money. eligible_for_policy=false. "
    "market_truth_canonical=false. No trading authorization. exact_no_live_remains_blocked."
)
DEFAULT_CUTOFF_UTC = "2026-05-29T00:00:00+00:00"
DEFAULT_BOOTSTRAP_SAMPLES = 10000
DEFAULT_SEED = 2026

N_REVIEW = 20
N_PROMOTE_FLOOR = 30
N_TRADER_MIN = 12
N_TRADER_CELL_MIN = 5
LTO_MIN_N = 20
LTO_MIN_WR = 0.70
FORWARD_MIN_N = 10
MARGIN = 0.02
SIMPNL_FLOOR = 0.0
FDR_Q = 0.10
DOMINANCE_MAX_PCT = 50.0

ALLOWED_INPUT_BASENAMES = {"blocked_signals_resolutions.jsonl"}
QUALITY_BUCKETS = ("<60", "60-70", "70-80", ">=80")
SIDES = ("trader_YES", "trader_NO")
CONSENSUS = ("yes", "no")


@dataclass(frozen=True)
class BsrRow:
    match_key: str
    city: str
    date: str
    condition: str
    trader: str
    trader_historical_wr: float
    side: str
    avg_price_entered: float
    resolved: bool
    win_for_trader: float
    has_consensus: str
    checked_at: str

    @property
    def quality_bucket(self) -> str:
        return quality_bucket(self.trader_historical_wr)

    @property
    def cohort(self) -> str:
        return f"{self.quality_bucket}|{self.side}|{self.has_consensus}"

    @property
    def sim_unit_pnl(self) -> float:
        return self.win_for_trader - self.avg_price_entered


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def _not_null(value: Any) -> bool:
    return value is not None and value != ""


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_side(value: Any) -> str | None:
    lowered = str(value).strip().lower() if value is not None else ""
    if lowered in {"yes", "y", "trader_yes"}:
        return "trader_YES"
    if lowered in {"no", "n", "trader_no"}:
        return "trader_NO"
    return None


def normalize_consensus(value: Any) -> str | None:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    lowered = str(value).strip().lower() if value is not None else ""
    if lowered in {"true", "1", "yes", "y"}:
        return "yes"
    if lowered in {"false", "0", "no", "n"}:
        return "no"
    return None


def quality_bucket(value: float) -> str:
    if value < 60:
        return "<60"
    if value < 70:
        return "60-70"
    if value < 80:
        return "70-80"
    return ">=80"


def _date_key(value: str | None) -> str:
    return str(value or "")[:10]


def _parse_cutoff(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date().isoformat()


def row_from_json(raw: dict[str, Any]) -> BsrRow | None:
    if not _is_true(raw.get("resolved")):
        return None
    if str(raw.get("city", "")).strip().lower() == "seoul":
        return None
    side = normalize_side(raw.get("outcome"))
    consensus = normalize_consensus(raw.get("has_consensus"))
    wr = _to_float(raw.get("trader_historical_wr"))
    avg_price = _to_float(raw.get("avg_price_entered"))
    win = _to_float(raw.get("win_for_trader"))
    if (
        side is None
        or consensus is None
        or wr is None
        or avg_price is None
        or win is None
        or not _not_null(raw.get("match_key"))
        or not _not_null(raw.get("condition"))
        or not _not_null(raw.get("trader"))
    ):
        return None
    return BsrRow(
        match_key=str(raw["match_key"]),
        city=str(raw.get("city") or ""),
        date=_date_key(str(raw.get("date") or "")),
        condition=str(raw.get("condition") or ""),
        trader=str(raw.get("trader")),
        trader_historical_wr=wr,
        side=side,
        avg_price_entered=avg_price,
        resolved=True,
        win_for_trader=win,
        has_consensus=consensus,
        checked_at=str(raw.get("checked_at") or ""),
    )


def _validate_input_path(path: Path) -> None:
    if path.name not in ALLOWED_INPUT_BASENAMES:
        allowed = ", ".join(sorted(ALLOWED_INPUT_BASENAMES))
        raise ValueError(f"E3 input must be one of explicit allowlist basenames: {allowed}")


def load_jsonl_from_stream(stream: TextIO) -> tuple[list[dict[str, Any]], list[BsrRow]]:
    raw_rows: list[dict[str, Any]] = []
    eligible: list[BsrRow] = []
    for line in stream:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        parsed = json.loads(line)
        raw_rows.append(parsed)
        row = row_from_json(parsed)
        if row is not None:
            eligible.append(row)
    return raw_rows, eligible


def load_jsonl(path: Path | None) -> tuple[list[dict[str, Any]], list[BsrRow]]:
    if path is None:
        return load_jsonl_from_stream(sys.stdin)
    _validate_input_path(path)
    with path.open("r", encoding="utf-8") as fh:
        return load_jsonl_from_stream(fh)


def dedup_by_match_key(rows: Iterable[BsrRow]) -> list[BsrRow]:
    best: dict[str, tuple[tuple[int, str], BsrRow]] = {}
    for row in rows:
        key = (0 if row.resolved else 1, row.checked_at)
        current = best.get(row.match_key)
        if current is None or key < current[0]:
            best[row.match_key] = (key, row)
    return list(best_row for _, best_row in best.values())


def _stable_seed(seed: int, seed_key: str) -> int:
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:12]
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


def bootstrap_edge_by_trader(
    rows: list[BsrRow],
    samples: int,
    seed: int,
    seed_key: str,
) -> tuple[tuple[float | None, float | None], float | None]:
    if not rows or samples <= 0:
        return (None, None), None
    grouped: dict[str, list[BsrRow]] = defaultdict(list)
    for row in rows:
        grouped[row.trader].append(row)
    traders = sorted(grouped)
    if not traders:
        return (None, None), None
    rng = random.Random(_stable_seed(seed, seed_key))
    values: list[float] = []
    for _ in range(samples):
        sample: list[BsrRow] = []
        for _ in traders:
            sample.extend(grouped[traders[rng.randrange(len(traders))]])
        edge = _mean([row.sim_unit_pnl for row in sample])
        if edge is not None:
            values.append(edge)
    values.sort()
    if not values:
        return (None, None), None
    lower = _percentile(values, 0.025)
    upper = _percentile(values, 0.975)
    p_raw = sum(1 for value in values if value <= 0.0) / len(values)
    return (lower, upper), p_raw


def _trader_concentration(rows: list[BsrRow]) -> dict[str, Any]:
    counts = [count for _, count in Counter(row.trader for row in rows).most_common()]
    n = len(rows)
    def pct(count: int) -> float | None:
        return (100.0 * count / n) if n else None
    return {
        "top1_n": counts[0] if len(counts) >= 1 else 0,
        "top1_pct": _round(pct(counts[0])) if len(counts) >= 1 else None,
        "top2_n": sum(counts[:2]),
        "top2_pct": _round(pct(sum(counts[:2]))) if counts else None,
        "top5_n": sum(counts[:5]),
        "top5_pct": _round(pct(sum(counts[:5]))) if counts else None,
    }


def metrics_for_rows(
    rows: list[BsrRow],
    bootstrap_samples: int,
    seed: int,
    seed_key: str,
) -> dict[str, Any]:
    n = len(rows)
    if not rows:
        return {
            "n": 0,
            "n_traders": 0,
            "WR": None,
            "mean_price": None,
            "sim_unit_pnl_mean": None,
            "sim_unit_pnl_total": None,
            "edge_ci": {"lower": None, "upper": None},
            "p_raw": None,
            "top1_pct": None,
            "top2_pct": None,
        }
    wins = [row.win_for_trader for row in rows]
    prices = [row.avg_price_entered for row in rows]
    pnls = [row.sim_unit_pnl for row in rows]
    ci, p_raw = bootstrap_edge_by_trader(rows, bootstrap_samples, seed, seed_key)
    concentration = _trader_concentration(rows)
    return {
        "n": n,
        "n_traders": len({row.trader for row in rows}),
        "WR": _round(_mean(wins), 4),
        "mean_price": _round(_mean(prices)),
        "sim_unit_pnl_mean": _round(_mean(pnls)),
        "sim_unit_pnl_total": _round(sum(pnls)),
        "edge_ci": {"lower": _round(ci[0]), "upper": _round(ci[1])},
        "p_raw": _round(p_raw),
        "top1_pct": concentration["top1_pct"],
        "top2_pct": concentration["top2_pct"],
    }


def leave_top_trader_out(rows: list[BsrRow]) -> tuple[list[BsrRow], dict[str, Any]]:
    if not rows:
        return [], {"removed_label": None, "removed_n": 0, "removed_pct": None}
    counts = Counter(row.trader for row in rows)
    top_trader, top_n = counts.most_common(1)[0]
    remaining = [row for row in rows if row.trader != top_trader]
    return remaining, {
        "removed_label": "T1",
        "removed_n": top_n,
        "removed_pct": _round(100.0 * top_n / len(rows)),
    }


def _l1_groups(rows: list[BsrRow]) -> dict[str, list[BsrRow]]:
    groups: dict[str, list[BsrRow]] = {}
    for quality in QUALITY_BUCKETS:
        for side in SIDES:
            for consensus in CONSENSUS:
                groups[f"{quality}|{side}|{consensus}"] = []
    for row in rows:
        groups[row.cohort].append(row)
    return groups


def _apply_bh(cells: list[dict[str, Any]]) -> None:
    tested = [cell for cell in cells if cell.get("p_raw") is not None]
    tested.sort(key=lambda cell: cell["p_raw"])
    m = len(tested)
    prev = 1.0
    for index in range(m - 1, -1, -1):
        rank = index + 1
        p_fdr = min(prev, tested[index]["p_raw"] * m / rank)
        tested[index]["p_fdr"] = _round(min(1.0, p_fdr))
        prev = p_fdr


def verdict_for_cell(cell: dict[str, Any]) -> str:
    n = cell["n"]
    n_traders = cell["n_traders"]
    edge = cell["sim_unit_pnl_mean"]
    top1 = cell["top1_pct"]
    lto = cell["lto"]
    forward = cell["forward"]
    ci_lower = cell["edge_ci"]["lower"]
    p_fdr = cell.get("p_fdr")

    if n < N_REVIEW or n_traders < N_TRADER_CELL_MIN:
        return "INSUFFICIENT_N"
    if edge is not None and edge <= 0:
        return "NO_TRADER_EDGE"
    if top1 is not None and top1 > DOMINANCE_MAX_PCT:
        return "NON_PROMOTABLE_BY_DOMINANCE"
    if lto["n"] < LTO_MIN_N or lto["WR"] is None or lto["WR"] < LTO_MIN_WR:
        return "NON_PROMOTABLE_LTO_FAIL"
    if forward["n"] < FORWARD_MIN_N:
        return "NEEDS_FORWARD_CONFIRMATION"
    if forward["top1_pct"] is not None and forward["top1_pct"] > DOMINANCE_MAX_PCT:
        return "FORWARD_DOMINATED"
    candidate = (
        n >= N_PROMOTE_FLOOR
        and n_traders >= N_TRADER_CELL_MIN
        and edge is not None
        and edge > SIMPNL_FLOOR
        and edge > MARGIN
        and ci_lower is not None
        and ci_lower > 0
        and (p_fdr is None or p_fdr <= FDR_Q)
    )
    return "TRADER_ALPHA_CANDIDATE" if candidate else "DIAGNOSTIC_ONLY"


def build_summary(
    raw_rows: list[dict[str, Any]],
    eligible_rows: list[BsrRow],
    *,
    source_description: str,
    bootstrap_samples: int,
    seed: int,
    cutoff_utc: str,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    cutoff_date = _parse_cutoff(cutoff_utc)
    deduped = dedup_by_match_key(eligible_rows)
    global_metrics = metrics_for_rows(deduped, bootstrap_samples, seed, "global")
    global_concentration = _trader_concentration(deduped)
    dates = [row.date for row in deduped if row.date]
    forward_global = [row for row in deduped if row.date >= cutoff_date]
    l1_cells: list[dict[str, Any]] = []
    for cohort, rows in sorted(_l1_groups(deduped).items()):
        metrics = metrics_for_rows(rows, bootstrap_samples, seed, f"L1|{cohort}")
        lto_rows, removed = leave_top_trader_out(rows)
        lto_metrics = metrics_for_rows(lto_rows, bootstrap_samples, seed, f"LTO|{cohort}")
        forward_rows = [row for row in rows if row.date >= cutoff_date]
        forward_metrics = metrics_for_rows(forward_rows, bootstrap_samples, seed, f"FORWARD|{cohort}")
        cell = {
            "level": "L1",
            "cohort": cohort,
            "promotion_surface": True,
            **metrics,
            "lto": {
                "n": lto_metrics["n"],
                "n_traders": lto_metrics["n_traders"],
                "WR": lto_metrics["WR"],
                "mean_price": lto_metrics["mean_price"],
                "sim_unit_pnl_mean": lto_metrics["sim_unit_pnl_mean"],
                "removed_top_trader": removed,
            },
            "forward": {
                "n": forward_metrics["n"],
                "n_traders": forward_metrics["n_traders"],
                "WR": forward_metrics["WR"],
                "mean_price": forward_metrics["mean_price"],
                "sim_unit_pnl_mean": forward_metrics["sim_unit_pnl_mean"],
                "top1_pct": forward_metrics["top1_pct"],
            },
            "dominance": {
                "top1_label": "T1" if rows else None,
                "post_dedup_top1_pct": metrics["top1_pct"],
                "post_dedup_top2_pct": metrics["top2_pct"],
                "forward_top1_pct": forward_metrics["top1_pct"],
            },
            "p_fdr": None,
        }
        l1_cells.append(cell)

    _apply_bh(l1_cells)
    for cell in l1_cells:
        cell["verdict"] = verdict_for_cell(cell)

    top_candidates = [cell for cell in l1_cells if cell["verdict"] == "TRADER_ALPHA_CANDIDATE"]
    non_promotable = [
        cell
        for cell in l1_cells
        if cell["verdict"]
        in {
            "NON_PROMOTABLE_BY_DOMINANCE",
            "FORWARD_DOMINATED",
            "NON_PROMOTABLE_LTO_FAIL",
            "NEEDS_FORWARD_CONFIRMATION",
            "INSUFFICIENT_N",
        }
    ]
    edge_cells = [
        cell
        for cell in l1_cells
        if cell["n"] >= N_REVIEW and cell["sim_unit_pnl_mean"] is not None and cell["sim_unit_pnl_mean"] > 0
    ]
    if top_candidates:
        global_verdict = "TRADER_ALPHA_CANDIDATE"
    elif edge_cells and any(cell["verdict"] == "NON_PROMOTABLE_BY_DOMINANCE" for cell in l1_cells):
        global_verdict = "NO_PROMOTABLE_CELLS_DOMINANCE_GATED"
    elif edge_cells:
        global_verdict = "NEEDS_FORWARD_CONFIRMATION"
    else:
        global_verdict = "KILL_TRADER_PATH"

    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "source_description": source_description,
        "prereg_cutoff_utc": cutoff_utc,
        "lto_fold_seed": seed,
        "thresholds": {
            "N_REVIEW": N_REVIEW,
            "N_PROMOTE_FLOOR": N_PROMOTE_FLOOR,
            "N_TRADER_MIN": N_TRADER_MIN,
            "N_TRADER_CELL_MIN": N_TRADER_CELL_MIN,
            "LTO_MIN_N": LTO_MIN_N,
            "LTO_MIN_WR": LTO_MIN_WR,
            "FORWARD_MIN_N": FORWARD_MIN_N,
            "MARGIN": MARGIN,
            "SIMPNL_FLOOR": SIMPNL_FLOOR,
            "FDR_Q": FDR_Q,
            "DOMINANCE_MAX_PCT": DOMINANCE_MAX_PCT,
            "bootstrap_samples": bootstrap_samples,
            "seed": seed,
        },
        "baseline": {
            "primary": "market_at_avg_price_entered",
            "secondary_diagnostic": "base_rate",
            "tertiary_reference_only": "bot_forecast_via_E1_join",
        },
        "inventory": {
            "raw_rows": len(raw_rows),
            "eligible_rows_pre_dedup": len(eligible_rows),
            "eligible_rows_post_dedup": len(deduped),
            "n_traders_distinct": global_metrics["n_traders"],
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "forward_n": len(forward_global),
            **global_concentration,
        },
        "global_metrics": global_metrics,
        "l1_cells": l1_cells,
        "top_candidates": [
            {
                "level": cell["level"],
                "cohort": cell["cohort"],
                "n": cell["n"],
                "n_traders": cell["n_traders"],
                "sim_unit_pnl_mean": cell["sim_unit_pnl_mean"],
                "verdict": cell["verdict"],
            }
            for cell in top_candidates
        ],
        "non_promotable_cells": [
            {
                "cohort": cell["cohort"],
                "n": cell["n"],
                "n_traders": cell["n_traders"],
                "top1_pct": cell["top1_pct"],
                "forward_n": cell["forward"]["n"],
                "forward_top1_pct": cell["forward"]["top1_pct"],
                "verdict": cell["verdict"],
            }
            for cell in non_promotable
        ],
        "global_verdict": global_verdict,
        "triggers": [
            "opus_review_required_before_any_live_use",
            "if_all_positive_cells_are_dominance_gated_decide_accumulate_or_close_camino_a",
            "rerun_when_new_forward_cells_have_n>=10_and_top1<=50pct",
        ],
        "coverage_warnings": [
            "dedup_by_signal_key_applied_before_metrics",
            "single_trader_dominance_gate_hard_enabled",
            "yes_price_no_price_absent_ok_baseline_avg_price_entered",
        ],
        "disclaimer": DISCLAIMER,
        "eligible_for_policy": False,
    }
    assert_summary_sanitized(summary)
    return summary


def assert_summary_sanitized(summary: dict[str, Any]) -> None:
    text = json.dumps(summary, sort_keys=True)
    forbidden = ("match_key", "order_id", "wallet", "trades.log")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise ValueError(f"summary contains forbidden row-level/sensitive token(s): {hits}")


def run_benchmark(
    input_path: Path | None,
    output_summary: Path,
    *,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = DEFAULT_SEED,
    cutoff_utc: str = DEFAULT_CUTOFF_UTC,
    source_description: str | None = None,
) -> dict[str, Any]:
    raw_rows, eligible_rows = load_jsonl(input_path)
    source = source_description or (
        "stdin:blocked_signals_resolutions.jsonl" if input_path is None else str(input_path)
    )
    summary = build_summary(
        raw_rows,
        eligible_rows,
        source_description=source,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
        cutoff_utc=cutoff_utc,
    )
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E3 trader-following benchmark")
    parser.add_argument(
        "--input",
        default="-",
        help="Path to blocked_signals_resolutions.jsonl, or '-' for stdin.",
    )
    parser.add_argument(
        "--output-summary",
        default=str(DEFAULT_OUTPUT_SUMMARY),
        help="Aggregate summary JSON path.",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=DEFAULT_BOOTSTRAP_SAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cutoff-utc", default=DEFAULT_CUTOFF_UTC)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = None if args.input == "-" else Path(args.input)
    summary = run_benchmark(
        input_path,
        Path(args.output_summary),
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
        cutoff_utc=args.cutoff_utc,
    )
    print(
        json.dumps(
            {
                "output_summary": args.output_summary,
                "global_verdict": summary["global_verdict"],
                "eligible_rows_post_dedup": summary["inventory"]["eligible_rows_post_dedup"],
                "top_candidates": len(summary["top_candidates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
