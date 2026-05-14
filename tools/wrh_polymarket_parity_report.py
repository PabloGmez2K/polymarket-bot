#!/usr/bin/env python3
"""Offline WRH vs Polymarket parity report (LOG_ONLY).

Builds an isolated Istanbul parity package from blocked_signals_resolutions rows
and the weather.gov WRH client. No bot.py import, no runtime writes, no Telegram,
no scheduler, no observed audit, and no promotion-gate integration.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import weather_gov_wrh_client as wrh_client


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = [
    REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl",
    REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl",
]
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "source_audits" / "istanbul_wrh_parity_report.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "source_audits" / "istanbul_wrh_parity_report.md"

CITY = "Istanbul"
WRH_SITE = "LTFM"
OBSERVED_DATASET = wrh_client.OBSERVED_DATASET
REPORT_SOURCE = "weather_gov_wrh_synoptic"
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY offline source-parity report. This does not authorize execution, "
    "policy changes, city-mode changes, observed-audit inclusion, promotion, or bankroll changes."
)
OPUS_MIN_UNIQUE_MARKETS = 20
OPUS_MAX_MEAN_ABS_DELTA_C = 0.5
OPUS_MAX_ABS_BIAS_C = 0.3
OPUS_SECOND_WRH_CITY_CONFIRMED = False

CONFIRMED_LTFM_SLUGS = {
    "highest-temperature-in-istanbul-on-may-6-2026-20c",
    "highest-temperature-in-istanbul-on-may-6-2026-17c",
    "highest-temperature-in-istanbul-on-may-7-2026-22c",
    "highest-temperature-in-istanbul-on-may-7-2026-23c",
    "highest-temperature-in-istanbul-on-may-13-2026-23c",
}


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def choose_input_path(paths):
    for path in paths:
        path = Path(path)
        if path.exists():
            return path
    return None


def _get_first(row, names):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def normalize_outcome(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "1", "resolved_yes"}:
        return True
    if text in {"no", "n", "false", "0", "resolved_no"}:
        return False
    return None


def parse_match_key(match_key):
    parts = str(match_key or "").split("|")
    if len(parts) < 5:
        return {}
    return {
        "city": parts[0],
        "date_local": parts[1],
        "condition": parts[2],
        "strike": _to_float(parts[3]),
        "unit": parts[4],
    }


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None


def _extract_slug(row):
    slug = _get_first(row, ("slug", "market_slug", "question_slug"))
    if slug:
        return str(slug)
    question = str(row.get("question") or "")
    match = re.search(r"highest-temperature-in-istanbul-on-[a-z]+-\d+-2026-\d+c", question, re.I)
    return match.group(0).lower() if match else None


def extract_candidate(row):
    parsed = parse_match_key(row.get("match_key"))
    city = _get_first(row, ("city",)) or parsed.get("city")
    condition = _get_first(row, ("condition", "condition_type")) or parsed.get("condition")
    date_local = _get_first(row, ("date", "date_local", "date_iso", "target_date")) or parsed.get("date_local")
    strike = _to_float(_get_first(row, ("strike", "strike_c", "temp", "temperature", "threshold_c", "target_temp_c")))
    if strike is None:
        strike = parsed.get("strike")
    unit = _get_first(row, ("unit", "temp_unit", "temperature_unit")) or parsed.get("unit") or "C"
    slug = _extract_slug(row)
    outcome_yes = normalize_outcome(_get_first(row, ("outcome", "resolution_outcome", "polymarket_outcome")))
    return {
        "city": city,
        "date_local": str(date_local) if date_local else None,
        "condition": str(condition).lower() if condition else None,
        "strike_c": strike if str(unit).upper() == "C" else None,
        "unit": unit,
        "slug": slug,
        "market_id": _get_first(row, ("market_id", "marketId", "id")),
        "condition_id": _get_first(row, ("condition_id",)),
        "row_outcome_yes": outcome_yes,
        "source_citation_match": bool(slug and slug in CONFIRMED_LTFM_SLUGS),
        "raw": row,
    }


def is_istanbul_exact_candidate(candidate):
    return (
        str(candidate.get("city") or "").lower() == CITY.lower()
        and candidate.get("condition") == "exact"
        and candidate.get("date_local")
        and candidate.get("strike_c") is not None
    )


def expected_yes_for_exact(daily_max_c, strike_c):
    if daily_max_c is None or strike_c is None:
        return None
    return float(daily_max_c) == float(strike_c)


def _fetch_daily_max(date_local, site, fetcher):
    payload = fetcher(site, date_local)
    return {
        "date_local": date_local,
        "daily_max_c": payload.get("daily_max_c"),
        "raw_rows_count": payload.get("raw_rows_count", 0),
        "temp_column_found": bool(payload.get("temp_column_found")),
        "warnings": payload.get("warnings", []),
        "confidence": payload.get("confidence"),
        "source_url": payload.get("source_url") or wrh_client.build_source_url(site),
    }


def default_fetcher(site, date_local):
    data, source_url, data_url = wrh_client.fetch_wrh_timeseries(site, date_local)
    return wrh_client.parse_synoptic_timeseries_json(
        data,
        site,
        date_local,
        source_url=source_url,
        data_url=wrh_client._redact_token_from_url(data_url),
    )


def _canonical_market_key(row):
    for field in ("condition_id", "market_id", "slug"):
        value = row.get(field)
        if value not in (None, ""):
            return f"{field}:{value}"
    return None


def _fallback_market_key(row):
    outcome = (
        "YES" if row.get("polymarket_outcome_yes") is True
        else "NO" if row.get("polymarket_outcome_yes") is False
        else "UNKNOWN"
    )
    return "|".join(
        str(part)
        for part in (
            row.get("date_local") or "",
            row.get("condition") or "",
            row.get("strike_c") if row.get("strike_c") is not None else "",
            outcome,
        )
    )


def _unique_counts(report_rows):
    canonical_keys = {
        key for key in (_canonical_market_key(row) for row in report_rows) if key
    }
    fallback_keys = {_fallback_market_key(row) for row in report_rows}
    return {
        "unique_market_n": len(canonical_keys),
        "canonical_unique_market_n": len(canonical_keys),
        "fallback_estimated_unique_market_n": len(fallback_keys),
        "rows_without_canonical_market_id_n": sum(
            1 for row in report_rows if _canonical_market_key(row) is None
        ),
        "unique_market_key_strategy": "canonical condition_id/market_id/slug; fallback estimate date|condition|strike|outcome",
    }


def build_opus_gate(metrics):
    reasons = []
    canonical_n = metrics.get("canonical_unique_market_n", 0) or 0
    fallback_n = metrics.get("fallback_estimated_unique_market_n", 0) or 0
    mean_abs_delta = metrics.get("mean_abs_delta")
    bias = metrics.get("bias")

    unique_markets_ok = canonical_n >= OPUS_MIN_UNIQUE_MARKETS
    mean_delta_ok = mean_abs_delta is not None and mean_abs_delta <= OPUS_MAX_MEAN_ABS_DELTA_C
    bias_ok = bias is not None and abs(bias) <= OPUS_MAX_ABS_BIAS_C
    second_city_ok = OPUS_SECOND_WRH_CITY_CONFIRMED

    if not unique_markets_ok:
        reasons.append(
            "no_20_demonstrable_unique_markets:"
            f" canonical_unique_market_n={canonical_n}, "
            f"fallback_estimated_unique_market_n={fallback_n}, "
            f"required={OPUS_MIN_UNIQUE_MARKETS}"
        )
    if not mean_delta_ok:
        reasons.append(
            "mean_abs_delta_above_threshold:"
            f" mean_abs_delta={mean_abs_delta}, "
            f"threshold={OPUS_MAX_MEAN_ABS_DELTA_C}"
        )
    if not bias_ok:
        reasons.append(
            "directional_bias_above_threshold:"
            f" bias={bias}, "
            f"max_abs_bias={OPUS_MAX_ABS_BIAS_C}"
        )
    if not second_city_ok:
        reasons.append("missing_second_explicit_wrh_candidate_city")

    gate_met = unique_markets_ok and mean_delta_ok and bias_ok and second_city_ok
    return {
        "OPUS_REEVALUATION_GATE_MET": gate_met,
        "gate_met": gate_met,
        "reasons": reasons,
        "criteria": {
            "min_demonstrable_unique_markets": OPUS_MIN_UNIQUE_MARKETS,
            "max_mean_abs_delta_c": OPUS_MAX_MEAN_ABS_DELTA_C,
            "max_abs_bias_c": OPUS_MAX_ABS_BIAS_C,
            "requires_second_explicit_wrh_candidate_city": True,
        },
        "notes": [
            "WRH_PARITY_PASS_PRELIMINARY is outcome parity only; it is not operational authorization.",
            "Delta metrics measure distance between WRH daily max and strike, not direct parity failure when expected outcome matches resolution.",
            "Zero mismatches is positive source evidence, not promotion approval.",
        ],
    }


def build_report(rows, *, fetcher=default_fetcher, site=WRH_SITE, generated_at=None, input_path=None):
    generated_at = generated_at or _now_iso()
    warnings = []
    candidates = [extract_candidate(row) for row in rows]
    candidates = [candidate for candidate in candidates if is_istanbul_exact_candidate(candidate)]
    date_cache = {}
    report_rows = []

    for candidate in candidates:
        date_local = candidate["date_local"]
        if date_local not in date_cache:
            try:
                date_cache[date_local] = _fetch_daily_max(date_local, site, fetcher)
            except Exception as exc:
                date_cache[date_local] = {
                    "date_local": date_local,
                    "daily_max_c": None,
                    "raw_rows_count": 0,
                    "temp_column_found": False,
                    "warnings": [f"WRH fetch failed: {exc}"],
                    "confidence": "none",
                    "source_url": wrh_client.build_source_url(site),
                }
        observed = date_cache[date_local]
        daily_max_c = observed.get("daily_max_c")
        expected_yes = expected_yes_for_exact(daily_max_c, candidate["strike_c"])
        outcome_yes = candidate.get("row_outcome_yes")
        parity_match = expected_yes == outcome_yes if expected_yes is not None and outcome_yes is not None else None
        delta_c = round(float(daily_max_c) - float(candidate["strike_c"]), 3) if daily_max_c is not None else None
        status = "matched" if parity_match is True else "mismatch" if parity_match is False else "unknown"
        report_rows.append({
            "city": CITY,
            "date_local": date_local,
            "condition": "exact",
            "strike_c": candidate["strike_c"],
            "slug": candidate.get("slug"),
            "market_id": candidate.get("market_id"),
            "condition_id": candidate.get("condition_id"),
            "source": REPORT_SOURCE,
            "source_url": observed.get("source_url"),
            "observed_dataset": OBSERVED_DATASET,
            "source_citation_match": candidate.get("source_citation_match"),
            "daily_max_c": daily_max_c,
            "delta_c": delta_c,
            "expected_yes": expected_yes,
            "polymarket_outcome_yes": outcome_yes,
            "parity_match": parity_match,
            "status": status,
            "raw_rows_count": observed.get("raw_rows_count", 0),
            "temp_column_found": observed.get("temp_column_found", False),
            "confidence": observed.get("confidence"),
            "warnings": observed.get("warnings", []),
        })

    comparable = [row for row in report_rows if row["parity_match"] is not None]
    deltas = [row["delta_c"] for row in report_rows if row["delta_c"] is not None]
    n_compared = len(comparable)
    n_match = sum(1 for row in comparable if row["parity_match"] is True)
    n_unknown = sum(1 for row in report_rows if row["status"] == "unknown")
    unique_counts = _unique_counts(report_rows)
    metrics = {
        "input_row_n": len(rows),
        "candidate_row_n": len(candidates),
        "compared_row_n": n_compared,
        "n_rows_input": len(rows),
        "n_candidates": len(candidates),
        "n_compared": n_compared,
        "n_match": n_match,
        "n_mismatch": sum(1 for row in comparable if row["parity_match"] is False),
        "n_unknown": n_unknown,
        "mean_abs_delta": round(sum(abs(delta) for delta in deltas) / len(deltas), 3) if deltas else None,
        "max_abs_delta": round(max(abs(delta) for delta in deltas), 3) if deltas else None,
        "bias": round(sum(deltas) / len(deltas), 3) if deltas else None,
        "unique_dates_fetched": len(date_cache),
        **unique_counts,
    }
    verdict = determine_verdict(metrics)
    opus_gate = build_opus_gate(metrics)
    if not candidates:
        warnings.append("no Istanbul exact resolved candidates found in input")

    return {
        "generated_at": generated_at,
        "city": CITY,
        "site": site,
        "source": REPORT_SOURCE,
        "source_url": wrh_client.build_source_url(site),
        "observed_dataset": OBSERVED_DATASET,
        "log_only": True,
        "input_path": str(input_path) if input_path else None,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "verdict": verdict,
        "outcome_parity_verdict": verdict,
        "opus_reevaluation_gate": opus_gate,
        "metrics": metrics,
        "rows": report_rows,
        "warnings": warnings,
    }


def determine_verdict(metrics):
    if metrics["n_compared"] == 0:
        return "NEED_MORE_DATA"
    if metrics["n_match"] == metrics["n_compared"] and metrics["n_compared"] >= 5:
        return "WRH_PARITY_PASS_PRELIMINARY"
    if metrics["n_match"] == metrics["n_compared"]:
        return "WRH_PARITY_PARTIAL"
    if metrics["n_match"] > 0:
        return "WRH_PARITY_PARTIAL"
    return "WRH_PARITY_FAIL"


def render_markdown(report):
    metrics = report["metrics"]
    lines = [
        "# Istanbul WRH Parity Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Verdict: `{report['verdict']}`",
        "",
        "This verdict is about preliminary outcome parity only. It is not an",
        "observed-audit approval, source promotion, city-mode change, or trading",
        "authorization.",
        "",
        "## Scope",
        "",
        report["disclaimer"],
        "",
        "- Source is `weather_gov_wrh_synoptic`.",
        f"- Observed dataset is `{OBSERVED_DATASET}`.",
        "- This is separate from NCEI and does not write observed audit data.",
        "- `WRH_PARITY_PASS_PRELIMINARY` means compared outcomes matched; Opus",
        "  re-evaluation gates are evaluated separately below.",
        "",
        "## Outcome Parity Metrics",
        "",
        f"- input_row_n: `{metrics['input_row_n']}`",
        f"- candidate_row_n: `{metrics['candidate_row_n']}`",
        f"- compared_row_n: `{metrics['compared_row_n']}`",
        f"- n_match: `{metrics['n_match']}`",
        f"- n_mismatch: `{metrics['n_mismatch']}`",
        f"- n_unknown: `{metrics['n_unknown']}`",
        f"- unique_market_n: `{metrics['unique_market_n']}`",
        f"- canonical_unique_market_n: `{metrics['canonical_unique_market_n']}`",
        f"- fallback_estimated_unique_market_n: `{metrics['fallback_estimated_unique_market_n']}`",
        f"- rows_without_canonical_market_id_n: `{metrics['rows_without_canonical_market_id_n']}`",
        f"- unique_market_key_strategy: `{metrics['unique_market_key_strategy']}`",
        f"- mean_abs_delta: `{metrics['mean_abs_delta']}`",
        f"- max_abs_delta: `{metrics['max_abs_delta']}`",
        f"- bias: `{metrics['bias']}`",
        f"- unique_dates_fetched: `{metrics['unique_dates_fetched']}`",
        "",
        "Delta metrics measure the distance between WRH daily max and the market",
        "strike. They are not mismatches when the expected YES/NO outcome still",
        "matches the resolved outcome.",
        "",
        "## Opus Re-Evaluation Gate",
        "",
        f"- OPUS_REEVALUATION_GATE_MET: `{report['opus_reevaluation_gate']['OPUS_REEVALUATION_GATE_MET']}`",
        "",
        "Reasons:",
    ]
    gate_reasons = report["opus_reevaluation_gate"].get("reasons") or []
    if gate_reasons:
        lines.extend(f"- `{reason}`" for reason in gate_reasons)
    else:
        lines.append("- none")
    lines.extend([
        "",
        "A zero-mismatch outcome parity result is positive source evidence, but it",
        "does not authorize observed-audit inclusion, promotion gates, city modes,",
        "BUY/SELL/SKIP, BANKROLL, or Phase C changes.",
        "",
        "## Rows",
        "",
        "| Date | Strike C | WRH max C | Expected | Outcome | Match | Source citation | Warnings |",
        "|---|---:|---:|---|---|---|---|---|",
    ])
    for row in report["rows"]:
        expected = "YES" if row["expected_yes"] is True else "NO" if row["expected_yes"] is False else "UNKNOWN"
        outcome = (
            "YES" if row["polymarket_outcome_yes"] is True
            else "NO" if row["polymarket_outcome_yes"] is False
            else "UNKNOWN"
        )
        match = "yes" if row["parity_match"] is True else "no" if row["parity_match"] is False else "unknown"
        warnings = "; ".join(row.get("warnings") or []) or ""
        lines.append(
            f"| {row['date_local']} | {row['strike_c']} | {row['daily_max_c']} | "
            f"{expected} | {outcome} | {match} | {row['source_citation_match']} | {warnings} |"
        )
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def write_outputs(report, json_output, md_output):
    json_path = Path(json_output)
    md_path = Path(md_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Istanbul WRH vs Polymarket parity report (LOG_ONLY)")
    parser.add_argument("--input-jsonl", help="blocked_signals_resolutions JSONL path")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--output-md", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--site", default=WRH_SITE)
    parser.add_argument("--no-write", action="store_true", help="Build and print summary without writing outputs")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    input_path = Path(args.input_jsonl) if args.input_jsonl else choose_input_path(DEFAULT_INPUTS)
    if not input_path:
        print("ERROR: no blocked_signals_resolutions.jsonl input found", file=sys.stderr)
        return 1
    try:
        rows = load_jsonl(input_path)
        report = build_report(rows, site=args.site, input_path=input_path)
        if not args.no_write:
            write_outputs(report, args.output_json, args.output_md)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "verdict": report["verdict"],
        "metrics": report["metrics"],
        "output_json": None if args.no_write else args.output_json,
        "output_md": None if args.no_write else args.output_md,
        "warnings": report["warnings"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
