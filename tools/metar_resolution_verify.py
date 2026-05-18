#!/usr/bin/env python3
"""Verify official Polymarket/Gamma outcomes against derived METAR outcomes.

LOG_ONLY standalone tool. It does not import bot.py, does not write runtime
state, and does not authorize source policy, trading, promotion, scheduler,
Telegram runtime, DB, env var, BANKROLL, Fase C, Truth Pipeline, or BUY/SELL/SKIP
changes.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import metar_shadow_fetch as metar_fetch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOLUTIONS = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
DEFAULT_METAR_DIR = REPO_ROOT / "data" / "metar_shadow"
DEFAULT_JSON_OUT = REPO_ROOT / "data" / "metar_resolution_verify_report.json"
DEFAULT_MD_OUT = REPO_ROOT / "docs" / "source_audits" / "metar_resolution_verify_report.md"

SUPPORTED_CONDITIONS = {"exact", "at_or_above", "at_or_below"}
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY METAR/AviationWeather resolution source verification. This compares "
    "official Polymarket/Gamma outcomes with hypothetical METAR-derived outcomes "
    "and does not authorize source policy changes, BUY/SELL/SKIP, promotion, "
    "scheduler changes, Telegram runtime alerts, env vars, DB writes, BANKROLL, "
    "Fase C, Truth Pipeline, whitelist, or city mode changes."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_yyyy_mm_dd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_city_station_map() -> dict[str, list[str]]:
    city_to_icaos: dict[str, list[str]] = defaultdict(list)
    for icao, meta in {**metar_fetch.WAVE1_STATIONS, **metar_fetch.WAVE2_STATIONS}.items():
        city = str(meta.get("city") or "").strip()
        if city:
            city_to_icaos[city].append(str(icao).upper())
    return {city: sorted(icaos) for city, icaos in city_to_icaos.items()}


def parse_threshold(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("threshold") not in (None, ""):
        raw_value = row.get("threshold")
        unit = str(row.get("unit") or row.get("threshold_unit") or "C").upper()
    else:
        parts = str(row.get("match_key") or "").split("|")
        if len(parts) < 5:
            return {"threshold_raw": None, "threshold_unit": None, "threshold_c": None, "error": "MISSING_THRESHOLD"}
        raw_value = parts[3]
        unit = str(parts[4] or "C").upper()

    try:
        threshold = float(raw_value)
    except (TypeError, ValueError):
        return {"threshold_raw": raw_value, "threshold_unit": unit, "threshold_c": None, "error": "INVALID_THRESHOLD"}

    if unit == "F":
        threshold_c = (threshold - 32.0) * 5.0 / 9.0
    elif unit == "C":
        threshold_c = threshold
    else:
        return {"threshold_raw": raw_value, "threshold_unit": unit, "threshold_c": None, "error": "UNSUPPORTED_UNIT"}

    return {
        "threshold_raw": raw_value,
        "threshold_unit": unit,
        "threshold_c": round(threshold_c, 3),
        "error": None,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def filter_rows(rows: list[dict[str, Any]], city: str | None, days: int | None, limit: int | None) -> list[dict[str, Any]]:
    filtered = [row for row in rows if bool(row.get("resolved", True))]
    if city:
        filtered = [row for row in filtered if str(row.get("city") or "").casefold() == city.casefold()]
    if days:
        dated = [row for row in filtered if row.get("date")]
        if dated:
            max_day = max(_parse_yyyy_mm_dd(str(row["date"])) for row in dated)
            cutoff = max_day - timedelta(days=int(days) - 1)
            filtered = [
                row
                for row in filtered
                if row.get("date") and _parse_yyyy_mm_dd(str(row["date"])) >= cutoff
            ]
    if limit is not None:
        filtered = filtered[: int(limit)]
    return filtered


def load_metar_snapshot(metar_dir: Path, icao: str, day: str) -> dict[str, Any] | None:
    path = metar_dir / f"{icao}_{day}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path)
    return payload


def is_sufficient_metar(snapshot: dict[str, Any]) -> bool:
    coverage = snapshot.get("coverage") if isinstance(snapshot.get("coverage"), dict) else {}
    return (
        snapshot.get("status") == "ok"
        and coverage.get("coverage_ok") is True
        and snapshot.get("tmax_c") is not None
    )


def metric_for_condition(snapshot: dict[str, Any], condition: str) -> tuple[str, float | None]:
    if condition in {"exact", "at_or_above", "at_or_below"}:
        return "tmax_c", _coerce_float(snapshot.get("tmax_c"))
    return "unsupported", None


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def hypothetical_outcome(condition: str, observed_c: float, threshold_c: float) -> str | None:
    if condition == "exact":
        return "Yes" if round(observed_c) == round(threshold_c) else "No"
    if condition == "at_or_above":
        return "Yes" if observed_c >= threshold_c else "No"
    if condition == "at_or_below":
        return "Yes" if observed_c <= threshold_c else "No"
    return None


def normalize_outcome(value: Any) -> str | None:
    text = str(value or "").strip().casefold()
    if text == "yes":
        return "Yes"
    if text == "no":
        return "No"
    return None


def margin_to_flip(condition: str, observed_c: float, threshold_c: float) -> float:
    if condition == "exact":
        return round(abs(observed_c - threshold_c), 3)
    return round(abs(observed_c - threshold_c), 3)


def evaluate_row(row: dict[str, Any], metar_dir: Path, city_to_icaos: dict[str, list[str]]) -> dict[str, Any]:
    city = str(row.get("city") or "")
    day = str(row.get("date") or "")
    condition = str(row.get("condition") or "")
    icaos = city_to_icaos.get(city, [])
    threshold = parse_threshold(row)
    base = {
        "city": city,
        "date": day,
        "condition": condition,
        "official_outcome": normalize_outcome(row.get("outcome")),
        "close_price": row.get("close_price"),
        "match_key": row.get("match_key"),
        "threshold_raw": threshold["threshold_raw"],
        "threshold_unit": threshold["threshold_unit"],
        "threshold_c": threshold["threshold_c"],
        "icaos": icaos,
        "source_line_no": row.get("_line_no"),
    }
    if not icaos:
        return {**base, "status": "NO_DATA", "reason": "city_not_in_wave1_or_wave2_mapping"}
    if condition not in SUPPORTED_CONDITIONS:
        return {**base, "status": "UNSUPPORTED_CONDITION", "reason": f"condition={condition}"}
    if threshold["error"]:
        return {**base, "status": "NO_DATA", "reason": threshold["error"]}

    snapshots = [(icao, load_metar_snapshot(metar_dir, icao, day)) for icao in icaos]
    existing = [(icao, snapshot) for icao, snapshot in snapshots if snapshot is not None]
    if not existing:
        return {**base, "status": "NO_SNAPSHOT", "reason": "no_metar_file_for_city_date"}

    insufficient = []
    candidates = []
    for icao, snapshot in existing:
        assert snapshot is not None
        if not is_sufficient_metar(snapshot):
            insufficient.append(
                {
                    "icao": icao,
                    "status": snapshot.get("status"),
                    "coverage": snapshot.get("coverage"),
                    "path": snapshot.get("_path"),
                }
            )
            continue
        metric_name, observed_c = metric_for_condition(snapshot, condition)
        if observed_c is None:
            insufficient.append(
                {
                    "icao": icao,
                    "status": snapshot.get("status"),
                    "coverage": snapshot.get("coverage"),
                    "path": snapshot.get("_path"),
                    "reason": f"missing_{metric_name}",
                }
            )
            continue
        threshold_c = float(threshold["threshold_c"])
        metar_outcome = hypothetical_outcome(condition, observed_c, threshold_c)
        official = normalize_outcome(row.get("outcome"))
        delta_c = round(observed_c - threshold_c, 3)
        candidates.append(
            {
                "icao": icao,
                "snapshot_path": snapshot.get("_path"),
                "metric": metric_name,
                "observed_c": observed_c,
                "metar_outcome": metar_outcome,
                "delta_c": delta_c,
                "abs_delta_c": round(abs(delta_c), 3),
                "margin_to_flip": margin_to_flip(condition, observed_c, threshold_c),
                "status": "MATCH" if metar_outcome == official else "MISMATCH",
            }
        )

    if not candidates:
        return {
            **base,
            "status": "INSUFFICIENT_METAR",
            "reason": "snapshot_without_sufficient_tmax",
            "snapshots": insufficient,
        }

    chosen = sorted(candidates, key=lambda item: (item["status"] != "MATCH", item["abs_delta_c"], item["icao"]))[0]
    return {**base, **chosen, "station_results": candidates, "insufficient_snapshots": insufficient}


def classify_city(summary: dict[str, Any]) -> str:
    comparable = summary.get("n_compared", 0)
    if comparable <= 0:
        if summary.get("n_no_snapshot", 0):
            return "NO_SNAPSHOT"
        return "NO_DATA"
    if comparable < 20:
        return "INSUFFICIENT_SAMPLE"

    agree_rate = float(summary.get("agree_rate") or 0.0)
    median_abs_delta = summary.get("median_abs_delta_c")
    max_abs_delta = summary.get("max_abs_delta_c")
    dangerous_flips = summary.get("dangerous_flip_count", 0)
    exact_n = summary.get("by_condition", {}).get("exact", {}).get("n_compared", 0)

    if agree_rate < 90.0 or dangerous_flips:
        return "SOURCE_DRIFT_DETECTED"
    if comparable >= 50 and agree_rate == 100.0 and (max_abs_delta is not None and max_abs_delta <= 1.0):
        if exact_n == 0 or exact_n >= 20:
            return "SOURCE_VERIFIED_CANDIDATE"
    if comparable >= 30 and agree_rate >= 95.0 and (median_abs_delta is not None and median_abs_delta <= 0.3):
        if exact_n == 0 or exact_n >= 20:
            return "SOURCE_LIKELY_EQUIVALENT"
    if 20 <= comparable < 30:
        return "SOURCE_UNDER_TEST"
    return "SOURCE_UNDER_TEST"


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(result["status"] for result in results)
    city_summaries: dict[str, dict[str, Any]] = {}
    for city in sorted({result["city"] for result in results if result.get("city")}):
        rows = [result for result in results if result.get("city") == city]
        compared = [result for result in rows if result.get("status") in {"MATCH", "MISMATCH"}]
        abs_deltas = [float(result["abs_delta_c"]) for result in compared if result.get("abs_delta_c") is not None]
        by_condition: dict[str, dict[str, Any]] = {}
        for condition in sorted({result.get("condition") for result in rows if result.get("condition")}):
            condition_compared = [r for r in compared if r.get("condition") == condition]
            condition_matches = [r for r in condition_compared if r.get("status") == "MATCH"]
            by_condition[str(condition)] = {
                "n_compared": len(condition_compared),
                "n_match": len(condition_matches),
                "agree_rate": round(100.0 * len(condition_matches) / len(condition_compared), 2)
                if condition_compared
                else None,
            }
        dangerous = [
            result
            for result in compared
            if result.get("status") == "MISMATCH" and float(result.get("abs_delta_c") or 0.0) > 1.5
        ]
        summary = {
            "n_rows": len(rows),
            "n_compared": len(compared),
            "n_match": sum(1 for result in compared if result.get("status") == "MATCH"),
            "n_mismatch": sum(1 for result in compared if result.get("status") == "MISMATCH"),
            "n_no_snapshot": sum(1 for result in rows if result.get("status") == "NO_SNAPSHOT"),
            "n_insufficient_metar": sum(1 for result in rows if result.get("status") == "INSUFFICIENT_METAR"),
            "n_unsupported_condition": sum(1 for result in rows if result.get("status") == "UNSUPPORTED_CONDITION"),
            "agree_rate": round(
                100.0 * sum(1 for result in compared if result.get("status") == "MATCH") / len(compared), 2
            )
            if compared
            else None,
            "median_abs_delta_c": round(statistics.median(abs_deltas), 3) if abs_deltas else None,
            "max_abs_delta_c": round(max(abs_deltas), 3) if abs_deltas else None,
            "dangerous_flip_count": len(dangerous),
            "by_condition": by_condition,
        }
        summary["state"] = classify_city(summary)
        city_summaries[city] = summary
    return {"status_counts": dict(status_counts), "cities": city_summaries}


def build_alerts(summary: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for city, city_summary in summary.get("cities", {}).items():
        state = city_summary.get("state")
        if state in {"SOURCE_LIKELY_EQUIVALENT", "SOURCE_VERIFIED_CANDIDATE"}:
            alerts.append(
                {
                    "code": "A_RESOLUTION_SOURCE_CANDIDATE",
                    "city": city,
                    "state": state,
                    "message": "METAR outcome equivalence candidate. LOG_ONLY; no automatic source or trading change.",
                }
            )
        if state == "SOURCE_DRIFT_DETECTED":
            alerts.append(
                {
                    "code": "A_RESOLUTION_SOURCE_DRIFT",
                    "city": city,
                    "state": state,
                    "message": "METAR hypothetical outcome drift detected. Requires manual review.",
                }
            )
        if state == "SOURCE_VERIFIED_CANDIDATE":
            alerts.append(
                {
                    "code": "A_APPLY_PATCH_REVIEW",
                    "city": city,
                    "state": state,
                    "message": "Requires Opus review. This alert does not authorize an automatic patch.",
                }
            )
    return alerts


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    resolutions = Path(args.resolutions)
    metar_dir = Path(args.metar_dir)
    rows = filter_rows(load_jsonl(resolutions), args.city, args.days, args.limit)
    city_to_icaos = build_city_station_map()
    results = [evaluate_row(row, metar_dir, city_to_icaos) for row in rows]
    summary = summarize_results(results)
    return {
        "generated_at": getattr(args, "generated_at", None) or _now_iso(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "question": "If we had used METAR/AviationWeather as resolution source, would the official Polymarket/Gamma outcome have been the same?",
        "inputs": {
            "resolutions": str(resolutions),
            "metar_dir": str(metar_dir),
            "days": args.days,
            "city": args.city,
            "limit": args.limit,
        },
        "row_count": len(rows),
        "summary": summary,
        "alerts": build_alerts(summary),
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# METAR Resolution Source Verification",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Scope",
        "",
        report["disclaimer"],
        "",
        f"Question: {report['question']}",
        "",
        "## Gate",
        "",
        f"- Rows evaluated: {report['row_count']}",
        f"- Status counts: `{json.dumps(summary.get('status_counts', {}), sort_keys=True)}`",
        "",
        "## City States",
        "",
        "| City | State | Compared | Match | Mismatch | Agree % | Median abs delta C | Max abs delta C | No snapshot | Insufficient | Unsupported |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for city, city_summary in sorted(summary.get("cities", {}).items()):
        lines.append(
            "| {city} | {state} | {n_compared} | {n_match} | {n_mismatch} | {agree_rate} | "
            "{median_abs_delta_c} | {max_abs_delta_c} | {n_no_snapshot} | {n_insufficient_metar} | "
            "{n_unsupported_condition} |".format(city=city, **city_summary)
        )
    lines.extend(["", "## Alerts", ""])
    if report.get("alerts"):
        for alert in report["alerts"]:
            lines.append(f"- `{alert['code']}` {alert['city']}: {alert['message']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Sample Rows",
            "",
            "| City | Date | Condition | ICAO | Official | METAR | Status | Delta C | Reason |",
            "|---|---:|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for result in report.get("results", [])[:25]:
        lines.append(
            "| {city} | {date} | {condition} | {icao} | {official} | {metar} | {status} | {delta} | {reason} |".format(
                city=result.get("city"),
                date=result.get("date"),
                condition=result.get("condition"),
                icao=result.get("icao") or ",".join(result.get("icaos") or []),
                official=result.get("official_outcome"),
                metar=result.get("metar_outcome"),
                status=result.get("status"),
                delta=result.get("delta_c"),
                reason=result.get("reason", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Operational Note",
            "",
            "This report is evidence for manual review only. It does not change trading, DB, env vars, source policy, city modes, whitelist, scheduler, Telegram runtime, BANKROLL, Fase C, Truth Pipeline, or BUY/SELL/SKIP behavior.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolutions", default=str(DEFAULT_RESOLUTIONS))
    parser.add_argument("--metar-dir", default=str(DEFAULT_METAR_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUT))
    parser.add_argument("--city", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on mismatches or drift alerts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    write_outputs(report, Path(args.json_out), Path(args.md_out))
    if args.strict:
        codes = {alert.get("code") for alert in report.get("alerts", [])}
        if "A_RESOLUTION_SOURCE_DRIFT" in codes or report["summary"]["status_counts"].get("MISMATCH"):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
