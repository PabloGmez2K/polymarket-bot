#!/usr/bin/env python3
"""Rolling METAR measurement-layer parity report (LOG_ONLY)."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METAR_DIR = REPO_ROOT / "data" / "metar_shadow"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "source_audits" / "metar_measurement_layer_report.md"
DEFAULT_CSV_OUTPUT = REPO_ROOT / "data" / "metar_shadow_report.csv"

FUTURE_MIN_N = 30
FUTURE_MAX_MEDIAN_ABS_DELTA_C = 0.3
FUTURE_MAX_ABS_DELTA_C = 1.0
FUTURE_MIN_COVERAGE_PCT = 80.0

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY METAR/AviationWeather measurement-layer report. This does not "
    "authorize runtime integration, promotion, scheduler changes, env vars, DB "
    "writes, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, or canonical source changes."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_csv_values(path: Path | None, value_columns: tuple[str, ...]) -> dict[tuple[str, str], float]:
    if not path:
        return {}
    values: dict[tuple[str, str], float] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date_local = row.get("date") or row.get("date_local") or row.get("day")
            icao = str(row.get("icao") or row.get("station") or "").upper()
            if not date_local or not icao:
                continue
            value = None
            for column in value_columns:
                value = _to_float(row.get(column))
                if value is not None:
                    break
            if value is not None:
                values[(icao, str(date_local))] = round(value, 2)
    return values


def load_metar_payloads(metar_dir: Path, icao_filter: set[str] | None = None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(Path(metar_dir).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        icao = str(payload.get("icao") or "").upper()
        if icao_filter and icao not in icao_filter:
            continue
        rows.append(payload)
    return rows


def build_rows(
    metar_payloads: list[dict[str, Any]],
    wu_values: dict[tuple[str, str], float],
    open_meteo_values: dict[tuple[str, str], float],
    gamma_values: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    rows = []
    for payload in metar_payloads:
        icao = str(payload.get("icao") or "").upper()
        date_local = str(payload.get("date_local") or payload.get("date") or "")
        key = (icao, date_local)
        metar_tmax = _to_float(payload.get("tmax_c"))
        wu_high = wu_values.get(key) or gamma_values.get(key)
        open_meteo = open_meteo_values.get(key)
        metar_wu_delta = round(metar_tmax - wu_high, 2) if metar_tmax is not None and wu_high is not None else None
        metar_om_delta = round(metar_tmax - open_meteo, 2) if metar_tmax is not None and open_meteo is not None else None
        coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
        rows.append(
            {
                "city": payload.get("city"),
                "icao": icao,
                "date_local": date_local,
                "metar_status": payload.get("status"),
                "metar_tmax_c": metar_tmax,
                "wu_high_c": wu_high,
                "wu_source": "wu_csv" if key in wu_values else "gamma_csv" if key in gamma_values else None,
                "open_meteo_max_c": open_meteo,
                "metar_wu_delta_c": metar_wu_delta,
                "metar_open_meteo_delta_c": metar_om_delta,
                "coverage_ok": bool(coverage.get("coverage_ok")),
                "obs_count": coverage.get("obs_count"),
                "status": "compared" if metar_wu_delta is not None else "missing_wu_or_metar",
            }
        )
    return rows


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparable = [row for row in rows if row.get("metar_wu_delta_c") is not None]
    deltas = [float(row["metar_wu_delta_c"]) for row in comparable]
    abs_deltas = [abs(value) for value in deltas]
    om_deltas = [abs(float(row["metar_open_meteo_delta_c"])) for row in rows if row.get("metar_open_meteo_delta_c") is not None]
    n_requested = len(rows)
    coverage_ok = sum(1 for row in rows if row.get("coverage_ok"))
    return {
        "n_rows": n_requested,
        "n_compared_metar_wu": len(comparable),
        "coverage_pct": round(100.0 * coverage_ok / n_requested, 1) if n_requested else None,
        "median_abs_metar_wu_delta_c": _median(abs_deltas),
        "max_abs_metar_wu_delta_c": round(max(abs_deltas), 2) if abs_deltas else None,
        "pct_abs_metar_wu_delta_ge_1c": round(100.0 * sum(1 for value in abs_deltas if value >= 1.0) / len(abs_deltas), 1) if abs_deltas else None,
        "median_abs_metar_open_meteo_delta_c": _median(om_deltas),
        "max_abs_metar_open_meteo_delta_c": round(max(om_deltas), 2) if om_deltas else None,
    }


def classify_parity_drift(metrics: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    n = metrics.get("n_compared_metar_wu") or 0
    if n < FUTURE_MIN_N:
        reasons.append(f"n_compared_metar_wu={n} < {FUTURE_MIN_N}")
    median_abs = metrics.get("median_abs_metar_wu_delta_c")
    max_abs = metrics.get("max_abs_metar_wu_delta_c")
    coverage = metrics.get("coverage_pct")
    if median_abs is None:
        reasons.append("median_abs_metar_wu_delta_c=None")
    elif median_abs > FUTURE_MAX_MEDIAN_ABS_DELTA_C:
        reasons.append(f"median_abs_metar_wu_delta_c={median_abs} > {FUTURE_MAX_MEDIAN_ABS_DELTA_C}")
    if max_abs is None:
        reasons.append("max_abs_metar_wu_delta_c=None")
    elif max_abs > FUTURE_MAX_ABS_DELTA_C:
        reasons.append(f"max_abs_metar_wu_delta_c={max_abs} > {FUTURE_MAX_ABS_DELTA_C}")
    if coverage is None:
        reasons.append("coverage_pct=None")
    elif coverage < FUTURE_MIN_COVERAGE_PCT:
        reasons.append(f"coverage_pct={coverage} < {FUTURE_MIN_COVERAGE_PCT}")

    metric_fail = any(reason.startswith(("median_abs", "max_abs", "coverage_pct")) for reason in reasons)
    if n == 0:
        return "METAR_PARITY_INSUFFICIENT_DATA", reasons
    if metric_fail:
        return "A_METAR_PARITY_DRIFT", reasons
    if reasons:
        return "METAR_PARITY_WATCH_MORE_DATA", reasons
    return "METAR_PARITY_LOG_ONLY_PROMISING", ["future criteria met; still no promotion authorization"]


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# METAR Measurement Layer Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Verdict:** **{report['verdict']}**",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| n rows | {metrics.get('n_rows')} |",
        f"| n compared METAR-WU | {metrics.get('n_compared_metar_wu')} |",
        f"| coverage pct | {metrics.get('coverage_pct')} |",
        f"| median abs METAR-WU delta C | {metrics.get('median_abs_metar_wu_delta_c')} |",
        f"| max abs METAR-WU delta C | {metrics.get('max_abs_metar_wu_delta_c')} |",
        f"| pct abs METAR-WU delta >= 1C | {metrics.get('pct_abs_metar_wu_delta_ge_1c')} |",
        f"| median abs METAR-Open-Meteo delta C | {metrics.get('median_abs_metar_open_meteo_delta_c')} |",
        f"| max abs METAR-Open-Meteo delta C | {metrics.get('max_abs_metar_open_meteo_delta_c')} |",
        "",
        "## Future Criteria",
        "",
        f"- rolling n >= {FUTURE_MIN_N}",
        f"- median abs METAR-WU delta <= {FUTURE_MAX_MEDIAN_ABS_DELTA_C}C",
        f"- max abs METAR-WU delta <= {FUTURE_MAX_ABS_DELTA_C}C",
        f"- coverage >= {FUTURE_MIN_COVERAGE_PCT}%",
        "",
        "Reasons:",
    ]
    lines.extend(f"- {reason}" for reason in report["verdict_reasons"])
    lines.extend(["", "## Rows", "", "| City | ICAO | Date | METAR | WU/Gamma | Delta | Coverage | Open-Meteo | METAR-OM | Status |", "|---|---|---|---:|---:|---:|---|---:|---:|---|"])
    for row in report["rows"]:
        lines.append(
            f"| {row.get('city') or ''} | {row.get('icao')} | {row.get('date_local')} | {row.get('metar_tmax_c')} | "
            f"{row.get('wu_high_c')} | {row.get('metar_wu_delta_c')} | {row.get('coverage_ok')} | "
            f"{row.get('open_meteo_max_c')} | {row.get('metar_open_meteo_delta_c')} | {row.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "This report is informational only. It does not write runtime state, does not change rankings or gates, and does not promote METAR to canonical or trading use.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "city",
        "icao",
        "date_local",
        "metar_status",
        "metar_tmax_c",
        "wu_high_c",
        "wu_source",
        "open_meteo_max_c",
        "metar_wu_delta_c",
        "metar_open_meteo_delta_c",
        "coverage_ok",
        "obs_count",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    icao_filter = {item.upper() for item in args.icao} if args.icao else None
    metar = load_metar_payloads(Path(args.metar_dir), icao_filter=icao_filter)
    wu = load_csv_values(Path(args.wu_csv), ("wu_high_c", "high_c", "tmax_c", "max_c")) if args.wu_csv else {}
    gamma = load_csv_values(Path(args.gamma_csv), ("gamma_settlement_c", "settlement_temp_c", "wu_high_c", "tmax_c")) if args.gamma_csv else {}
    open_meteo = load_csv_values(Path(args.open_meteo_csv), ("open_meteo_max_c", "temperature_2m_max", "max_c")) if args.open_meteo_csv else {}
    rows = build_rows(metar, wu, open_meteo, gamma)
    metrics = compute_metrics(rows)
    verdict, reasons = classify_parity_drift(metrics)
    return {
        "generated_at": _now_iso(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "inputs": {
            "metar_dir": str(args.metar_dir),
            "wu_csv": args.wu_csv,
            "gamma_csv": args.gamma_csv,
            "open_meteo_csv": args.open_meteo_csv,
        },
        "metrics": metrics,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "rows": rows,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metar-dir", default=str(DEFAULT_METAR_DIR))
    parser.add_argument("--icao", action="append", help="Optional ICAO filter. Repeatable.")
    parser.add_argument("--wu-csv", help="Optional CSV with icao,date,wu_high_c.")
    parser.add_argument("--gamma-csv", help="Optional CSV with icao,date,gamma_settlement_c.")
    parser.add_argument("--open-meteo-csv", help="Optional CSV with icao,date,open_meteo_max_c.")
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUTPUT))
    parser.add_argument("--no-write-csv", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    if not args.no_write_csv:
        write_csv(report["rows"], Path(args.csv_out))
    print(json.dumps({"verdict": report["verdict"], "metrics": report["metrics"], "md_out": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
