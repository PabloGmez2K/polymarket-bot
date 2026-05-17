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
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "metar_shadow_report.json"

FUTURE_MIN_N = 30
FUTURE_MAX_MEDIAN_ABS_DELTA_C = 0.3
FUTURE_MAX_ABS_DELTA_C = 1.0
FUTURE_MIN_COVERAGE_PCT = 80.0
METAR_OPEN_METEO_DELTA_ALERT_C = 1.0

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


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def build_station_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row.get("city") or ""), str(row.get("icao") or "")), []).append(row)

    summary = []
    for (city, icao), station_rows in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        coverage_ok = sum(1 for row in station_rows if row.get("coverage_ok"))
        comparable = [row for row in station_rows if row.get("metar_wu_delta_c") is not None]
        abs_deltas = [abs(float(row["metar_wu_delta_c"])) for row in comparable]
        om_abs_deltas = [
            abs(float(row["metar_open_meteo_delta_c"]))
            for row in station_rows
            if row.get("metar_open_meteo_delta_c") is not None
        ]
        insufficient = [
            row for row in station_rows
            if row.get("metar_status") == "insufficient_metar_coverage" or not row.get("coverage_ok")
        ]
        summary.append(
            {
                "city": city or None,
                "icao": icao,
                "n_rows": len(station_rows),
                "coverage_ok_rows": coverage_ok,
                "coverage_pct": _pct(coverage_ok, len(station_rows)),
                "n_compared_metar_wu": len(comparable),
                "median_abs_metar_wu_delta_c": _median(abs_deltas),
                "max_abs_metar_wu_delta_c": round(max(abs_deltas), 2) if abs_deltas else None,
                "max_abs_metar_open_meteo_delta_c": round(max(om_abs_deltas), 2) if om_abs_deltas else None,
                "insufficient_coverage_rows": len(insufficient),
                "parity_status": _station_parity_status(len(comparable), abs_deltas, len(insufficient)),
            }
        )
    return summary


def build_city_summary(station_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for station in station_summary:
        grouped.setdefault(str(station.get("city") or "Unknown"), []).append(station)

    cities = []
    for city, stations in sorted(grouped.items()):
        rows = sum(int(station.get("n_rows") or 0) for station in stations)
        coverage_ok = sum(int(station.get("coverage_ok_rows") or 0) for station in stations)
        compared = sum(int(station.get("n_compared_metar_wu") or 0) for station in stations)
        max_abs = [
            float(station["max_abs_metar_wu_delta_c"])
            for station in stations
            if station.get("max_abs_metar_wu_delta_c") is not None
        ]
        max_om_abs = [
            float(station["max_abs_metar_open_meteo_delta_c"])
            for station in stations
            if station.get("max_abs_metar_open_meteo_delta_c") is not None
        ]
        insufficient = sum(int(station.get("insufficient_coverage_rows") or 0) for station in stations)
        cities.append(
            {
                "city": city,
                "stations": [station.get("icao") for station in stations],
                "n_rows": rows,
                "coverage_pct": _pct(coverage_ok, rows),
                "n_compared_metar_wu": compared,
                "max_abs_metar_wu_delta_c": round(max(max_abs), 2) if max_abs else None,
                "max_abs_metar_open_meteo_delta_c": round(max(max_om_abs), 2) if max_om_abs else None,
                "insufficient_coverage_rows": insufficient,
                "parity_status": _city_parity_status(stations),
            }
        )
    return cities


def _station_parity_status(n_compared: int, abs_deltas: list[float], insufficient_coverage_rows: int) -> str:
    if insufficient_coverage_rows:
        return "COVERAGE_GAP"
    if not n_compared:
        return "WAITING_WU_OR_GAMMA"
    if max(abs_deltas) > FUTURE_MAX_ABS_DELTA_C:
        return "DRIFT"
    if n_compared < FUTURE_MIN_N:
        return "WATCH_MORE_DATA"
    median_abs = statistics.median(abs_deltas)
    if median_abs > FUTURE_MAX_MEDIAN_ABS_DELTA_C:
        return "DRIFT"
    return "PROMISING_LOG_ONLY"


def _city_parity_status(stations: list[dict[str, Any]]) -> str:
    statuses = {str(station.get("parity_status") or "") for station in stations}
    if "COVERAGE_GAP" in statuses:
        return "COVERAGE_GAP"
    if "DRIFT" in statuses:
        return "DRIFT"
    if statuses == {"PROMISING_LOG_ONLY"}:
        return "PROMISING_LOG_ONLY"
    if "WATCH_MORE_DATA" in statuses:
        return "WATCH_MORE_DATA"
    return "WAITING_WU_OR_GAMMA"


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


def build_alerts(report: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for station in report.get("station_summary", []):
        city = station.get("city")
        icao = station.get("icao")
        coverage_pct = station.get("coverage_pct")
        if station.get("insufficient_coverage_rows") or (coverage_pct is not None and coverage_pct < FUTURE_MIN_COVERAGE_PCT):
            alerts.append(
                {
                    "code": "A_METAR_COVERAGE_GAP",
                    "city": city,
                    "icao": icao,
                    "severity": "watch",
                    "message": (
                        f"{city or icao} {icao}: coverage={coverage_pct}% "
                        f"insufficient_rows={station.get('insufficient_coverage_rows')}"
                    ),
                    "operational_action": "NO_ACTION_LOG_ONLY",
                }
            )
        max_abs = station.get("max_abs_metar_wu_delta_c")
        if max_abs is not None and max_abs > FUTURE_MAX_ABS_DELTA_C:
            alerts.append(
                {
                    "code": "A_METAR_PARITY_DRIFT",
                    "city": city,
                    "icao": icao,
                    "severity": "review",
                    "message": f"{city or icao} {icao}: max abs METAR-WU delta={max_abs}C",
                    "operational_action": "NO_ACTION_LOG_ONLY",
                }
            )
        max_om_abs = station.get("max_abs_metar_open_meteo_delta_c")
        if max_om_abs is not None and max_om_abs >= METAR_OPEN_METEO_DELTA_ALERT_C:
            alerts.append(
                {
                    "code": "A_METAR_VS_OM_DELTA",
                    "city": city,
                    "icao": icao,
                    "severity": "info",
                    "message": f"{city or icao} {icao}: max abs METAR-Open-Meteo delta={max_om_abs}C",
                    "operational_action": "NO_ACTION_LOG_ONLY",
                }
            )

    lucknow_compared = sum(
        1
        for row in report.get("rows", [])
        if str(row.get("city") or "").strip().lower() == "lucknow"
        and row.get("metar_wu_delta_c") is not None
    )
    if lucknow_compared < FUTURE_MIN_N:
        alerts.append(
            {
                "code": "LUCKNOW_COMPARABLE_DAYS_WATCH",
                "city": "Lucknow",
                "icao": None,
                "severity": "watch",
                "message": f"Lucknow comparable-days watch: n={lucknow_compared}/{FUTURE_MIN_N}; outside Wave 1 until threshold is met.",
                "operational_action": "NO_ACTION_LOG_ONLY",
            }
        )
    return alerts


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
        "## Operational Readout",
        "",
        "### By City",
        "",
        "| City | Stations | Coverage | Compared | Max METAR-WU | Max METAR-OM | Insufficient | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for city in report.get("city_summary", []):
        lines.append(
            f"| {city.get('city')} | {', '.join(city.get('stations') or [])} | {city.get('coverage_pct')} | "
            f"{city.get('n_compared_metar_wu')} | {city.get('max_abs_metar_wu_delta_c')} | "
            f"{city.get('max_abs_metar_open_meteo_delta_c')} | {city.get('insufficient_coverage_rows')} | "
            f"{city.get('parity_status')} |"
        )
    lines.extend(
        [
            "",
            "### By Station",
            "",
            "| City | ICAO | Coverage | Compared | Median METAR-WU | Max METAR-WU | Max METAR-OM | Insufficient | Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for station in report.get("station_summary", []):
        lines.append(
            f"| {station.get('city') or ''} | {station.get('icao')} | {station.get('coverage_pct')} | "
            f"{station.get('n_compared_metar_wu')} | {station.get('median_abs_metar_wu_delta_c')} | "
            f"{station.get('max_abs_metar_wu_delta_c')} | {station.get('max_abs_metar_open_meteo_delta_c')} | "
            f"{station.get('insufficient_coverage_rows')} | {station.get('parity_status')} |"
        )
    lines.extend(
        [
            "",
            "### LOG_ONLY Alerts",
            "",
        ]
    )
    if report.get("alerts"):
        for alert in report["alerts"]:
            target = f"{alert.get('city') or ''} {alert.get('icao') or ''}".strip()
            lines.append(f"- `{alert.get('code')}` {target}: {alert.get('message')}")
    else:
        lines.append("- None.")
    lines.extend(
        [
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
    )
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
    station_summary = build_station_summary(rows)
    city_summary = build_city_summary(station_summary)
    report = {
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
        "city_summary": city_summary,
        "station_summary": station_summary,
        "rows": rows,
    }
    report["alerts"] = build_alerts(report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metar-dir", default=str(DEFAULT_METAR_DIR))
    parser.add_argument("--icao", action="append", help="Optional ICAO filter. Repeatable.")
    parser.add_argument("--wu-csv", help="Optional CSV with icao,date,wu_high_c.")
    parser.add_argument("--gamma-csv", help="Optional CSV with icao,date,gamma_settlement_c.")
    parser.add_argument("--open-meteo-csv", help="Optional CSV with icao,date,open_meteo_max_c.")
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUTPUT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--no-write-csv", action="store_true")
    parser.add_argument("--no-write-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    if not args.no_write_csv:
        write_csv(report["rows"], Path(args.csv_out))
    if not getattr(args, "no_write_json", False):
        json_path = Path(getattr(args, "json_out", DEFAULT_JSON_OUTPUT))
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "metrics": report["metrics"],
                "alerts": len(report.get("alerts", [])),
                "md_out": str(md_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
