#!/usr/bin/env python3
"""Generic source fidelity resolver (LOG_ONLY, read-only).

Builds a human review package for one city by joining local runtime evidence,
available market identifiers, optional Polymarket Gamma metadata, and the
bot's internal source mapping. It does not import bot.py, does not touch
runtime data, and does not authorize operational changes.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOCKED_RESOLUTIONS = [
    REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl",
    REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl",
]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "source_audits"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs" / "source_audits"
GAMMA_MARKET_BY_SLUG = "https://gamma-api.polymarket.com/markets/slug/{slug}"

SOURCE_MATCH_CONFIRMED = "SOURCE_MATCH_CONFIRMED"
SOURCE_PARTIAL = "SOURCE_PARTIAL"
SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
SOURCE_MISMATCH = "SOURCE_MISMATCH"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY / human review only. This package is read-only and does not "
    "authorize trading actions, policy edits, city-mode changes, automation, "
    "bankroll changes, promotion gates, observed-audit inclusion, or Phase C."
)

OPERATIONAL_AUTHORIZATION_MARKERS = (
    "APPROVE_FOR_TRADING",
    "APPROVED_FOR_TRADING",
    "EXECUTE_TRADE",
    "PROMOTE_CITY",
    "SET_ACTIVE_CITY",
    "ENABLE_BANKROLL",
    "PHASE_C_APPROVED",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify_city(city: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", city.strip().lower())
    return slug.strip("_") or "city"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Source Fidelity Resolver v0 (LOG_ONLY)")
    parser.add_argument("--city", required=True)
    parser.add_argument("--blocked-resolutions", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    parser.add_argument("--bot-path", default=str(REPO_ROOT / "bot.py"))
    parser.add_argument("--fetch-gamma", action="store_true", help="Read-only Gamma lookup for discovered slugs")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--slug", action="append", default=[], help="Additional market slug to inspect")
    parser.add_argument("--no-write", action="store_true", help="Build and print summary without writing outputs")
    return parser.parse_args(argv)


def load_jsonl_optional(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    if not path.exists():
        return [], f"missing jsonl: {path}"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for line_no, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                row = json.loads(line)
                if isinstance(row, dict):
                    row["_source_path"] = str(path)
                    row["_line_no"] = line_no
                    rows.append(row)
        return rows, None
    except Exception as exc:  # pragma: no cover - defensive parse detail
        return [], f"jsonl parse error {path}: {exc}"


def choose_existing_inputs(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    rows: list[dict[str, Any]] = []
    used: list[str] = []
    warnings: list[str] = []
    for path in paths:
        loaded, warning = load_jsonl_optional(path)
        if warning:
            warnings.append(warning)
            continue
        rows.extend(loaded)
        used.append(str(path))
    return rows, used, warnings


def _literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_wu_history_url":
        if node.args and isinstance(node.args[0], ast.Constant):
            return f"https://www.wunderground.com/history/daily/{node.args[0].value}/date/{{date}}"
    return None


def _literal_dict(node: ast.AST) -> dict[str, Any]:
    if not isinstance(node, ast.Dict):
        return {}
    result: dict[str, Any] = {}
    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            continue
        key = key_node.value
        if isinstance(value_node, ast.Dict):
            meta: dict[str, Any] = {}
            for mk, mv in zip(value_node.keys, value_node.values):
                if isinstance(mk, ast.Constant) and isinstance(mk.value, str):
                    value = _literal_value(mv)
                    if value is not None:
                        meta[mk.value] = value
            result[key] = meta
        else:
            value = _literal_value(value_node)
            if value is not None:
                result[key] = value
    return result


def load_internal_mapping(bot_path: Path, city: str) -> dict[str, Any]:
    refs = {
        "city": city,
        "resolution_icao": {},
        "resolution_station": {},
        "warnings": [],
    }
    try:
        tree = ast.parse(bot_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        refs["warnings"].append(f"bot.py AST parse unavailable: {exc}")
        return refs

    resolution_icao: dict[str, Any] = {}
    resolution_stations: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "RESOLUTION_ICAO" in names:
            resolution_icao = _literal_dict(node.value)
        elif "RESOLUTION_STATIONS" in names:
            resolution_stations = _literal_dict(node.value)

    refs["resolution_icao"] = resolution_icao.get(city, {}) or {}
    refs["resolution_station"] = resolution_stations.get(city, {}) or {}
    return refs


def _first_present(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _slug_from_text(value: str) -> str | None:
    text = str(value or "")
    match = re.search(r"\bhighest-temperature-in-[a-z0-9-]+-\d{4}-\d+c\b", text, re.I)
    if match:
        return match.group(0).lower()
    match = re.search(r"\bhighest-temperature-in-[a-z0-9-]+-on-[a-z]+-\d{1,2}-\d{4}-\d+c\b", text, re.I)
    return match.group(0).lower() if match else None


def extract_market_ref(row: dict[str, Any]) -> dict[str, Any]:
    slug = _first_present(row, ("slug", "market_slug", "question_slug"))
    if not slug:
        slug = _slug_from_text(str(row.get("question") or ""))
    return {
        "slug": str(slug) if slug else None,
        "market_id": _first_present(row, ("market_id", "marketId", "id")),
        "condition_id": _first_present(row, ("condition_id", "conditionId")),
        "question": row.get("question"),
        "date": _first_present(row, ("date", "date_local", "date_iso", "target_date")),
        "condition": _first_present(row, ("condition", "condition_type")),
        "outcome": _first_present(row, ("outcome", "resolution_outcome", "polymarket_outcome")),
        "source_path": row.get("_source_path"),
        "line_no": row.get("_line_no"),
    }


def collect_local_evidence(city: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    city_rows = [row for row in rows if str(row.get("city") or "").strip().lower() == city.lower()]
    refs = [extract_market_ref(row) for row in city_rows]
    slugs = sorted({ref["slug"] for ref in refs if ref.get("slug")})
    market_ids = sorted({str(ref["market_id"]) for ref in refs if ref.get("market_id")})
    condition_ids = sorted({str(ref["condition_id"]) for ref in refs if ref.get("condition_id")})
    outcomes = Counter(str(ref.get("outcome") or "unknown") for ref in refs)
    return {
        "city_row_n": len(city_rows),
        "market_refs": refs,
        "slugs": slugs,
        "market_ids": market_ids,
        "condition_ids": condition_ids,
        "outcomes": dict(outcomes),
    }


def extract_slugs_from_existing_docs(city: str, docs_dir: Path) -> list[str]:
    doc_path = docs_dir / f"{slugify_city(city)}_source_audit.md"
    if not doc_path.exists():
        return []
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    slugs = set(re.findall(r"\bhighest-temperature-in-[a-z0-9-]+-\d{4}-\d+c\b", text, re.I))
    slugs.update(re.findall(r"\bhighest-temperature-in-[a-z0-9-]+-on-[a-z]+-\d{1,2}-\d{4}-\d+c\b", text, re.I))
    return sorted({slug.lower() for slug in slugs})


def extract_gamma_evidence_text_from_doc(city: str, docs_dir: Path) -> str:
    doc_path = docs_dir / f"{slugify_city(city)}_source_audit.md"
    if not doc_path.exists():
        return ""
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"## Polymarket Gamma API Evidence(?P<section>.*?)(?:\n## |\Z)",
        text,
        re.S,
    )
    return match.group("section") if match else text


def fetch_gamma_market_by_slug(slug: str, timeout: int = 30) -> dict[str, Any]:
    encoded = urllib.parse.quote(slug, safe="")
    url = GAMMA_MARKET_BY_SLUG.format(slug=encoded)
    request = urllib.request.Request(url, headers={"User-Agent": "source-fidelity-resolver/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _stringify_jsonish(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def parse_gamma_source_text(market: dict[str, Any]) -> dict[str, Any]:
    """Extract source/rules hints from a Gamma market/event payload."""
    text_parts: list[str] = []
    for key in (
        "question",
        "title",
        "description",
        "rules",
        "resolutionSource",
        "resolution_source",
        "source",
        "marketResolutionText",
    ):
        if key in market:
            text_parts.append(_stringify_jsonish(market.get(key)))
    event = market.get("event")
    if isinstance(event, dict):
        for key in ("title", "description", "resolutionSource", "rules"):
            if key in event:
                text_parts.append(_stringify_jsonish(event.get(key)))
    events = market.get("events")
    if isinstance(events, list):
        for event_row in events:
            if isinstance(event_row, dict):
                for key in ("title", "description", "resolutionSource", "rules"):
                    if key in event_row:
                        text_parts.append(_stringify_jsonish(event_row.get(key)))

    combined = "\n".join(part for part in text_parts if part)
    urls = sorted(set(re.findall(r"https?://[^\s)>\]\"']+", combined)))
    wrh_sites = sorted({match.upper() for match in re.findall(r"weather\.gov/wrh/timeseries\?site=([A-Za-z0-9]+)", combined)})
    icao_mentions = sorted({match.upper() for match in re.findall(r"\(([A-Z]{4})\)", combined)})

    source_types: set[str] = set()
    lowered = combined.lower()
    if wrh_sites or "weather.gov/wrh/timeseries" in lowered:
        source_types.add("weather_gov_wrh")
    if "ncei" in lowered or "global-hourly" in lowered or "daily-summaries" in lowered:
        source_types.add("noaa_ncei")
    if "wunderground.com" in lowered or "weather underground" in lowered:
        source_types.add("wunderground")
    if "noaa" in lowered:
        source_types.add("noaa")

    station_label = None
    label_match = re.search(r"recorded by NOAA at the ([A-Za-z0-9 .'\-]+?)(?:\.|,|\n| readings|\()", combined)
    if label_match:
        station_label = re.sub(r"\s+", " ", label_match.group(1)).strip()

    return {
        "raw_text": combined,
        "source_types": sorted(source_types),
        "source_urls": urls,
        "weather_gov_sites": wrh_sites,
        "icao_mentions": icao_mentions,
        "station_label": station_label,
        "mentions_temp_column": bool(re.search(r"\bTemp\b", combined)),
        "mentions_metric_units": bool(re.search(r"metric|celsius|degrees celsius|°c", combined, re.I)),
    }


def source_types_for_internal_mapping(mapping: dict[str, Any]) -> list[str]:
    meta = mapping.get("resolution_icao") or {}
    types: set[str] = set()
    if meta.get("weather_gov_timeseries_site"):
        types.add("weather_gov_wrh")
    if meta.get("noaa_station_id") or meta.get("noaa_daily_station_id"):
        types.add("noaa_ncei")
    if meta.get("wu_url"):
        types.add("wunderground")
    return sorted(types)


def compare_sources(internal_mapping: dict[str, Any], parsed_sources: list[dict[str, Any]]) -> dict[str, Any]:
    meta = internal_mapping.get("resolution_icao") or {}
    internal_types = source_types_for_internal_mapping(internal_mapping)
    external_types = sorted({stype for parsed in parsed_sources for stype in parsed.get("source_types", [])})
    external_wrh_sites = sorted({site for parsed in parsed_sources for site in parsed.get("weather_gov_sites", [])})
    external_icaos = sorted({icao for parsed in parsed_sources for icao in parsed.get("icao_mentions", [])})
    internal_icao = str(meta.get("icao") or "").upper() or None
    internal_wrh_site = str(meta.get("weather_gov_timeseries_site") or "").upper() or None
    reasons: list[str] = []
    warnings: list[str] = []

    if "weather_gov_wrh" in external_types and "noaa_ncei" in external_types:
        warnings.append("external_source_text_mentions_wrh_and_ncei; do not merge datasets")
    if "weather_gov_wrh" in internal_types and "noaa_ncei" in internal_types:
        warnings.append("internal_mapping_has_wrh_and_ncei_fields; human review required to keep datasets separate")

    if not parsed_sources:
        return {
            "verdict": SOURCE_AMBIGUOUS,
            "reasons": ["no_gamma_or_documented_source_text_available"],
            "warnings": warnings,
            "internal_source_types": internal_types,
            "external_source_types": external_types,
            "wrh_ncei_separation": "separate_not_equivalent",
        }

    if external_wrh_sites:
        if internal_wrh_site and set(external_wrh_sites) == {internal_wrh_site}:
            if "weather_gov_wrh" in internal_types and "noaa_ncei" not in internal_types:
                verdict = SOURCE_MATCH_CONFIRMED
                reasons.append(f"weather_gov_wrh_site_matches:{internal_wrh_site}")
            else:
                verdict = SOURCE_PARTIAL
                reasons.append(f"wrh_site_matches_but_internal_mapping_has_extra_source_types:{internal_types}")
        elif internal_wrh_site:
            verdict = SOURCE_MISMATCH
            reasons.append(f"weather_gov_wrh_site_mismatch: external={external_wrh_sites} internal={internal_wrh_site}")
        elif "noaa_ncei" in internal_types:
            verdict = SOURCE_MISMATCH
            reasons.append("external_wrh_source_cannot_be_satisfied_by_internal_ncei_mapping")
        elif internal_icao and set(external_wrh_sites) == {internal_icao}:
            verdict = SOURCE_PARTIAL
            reasons.append("external_wrh_site_matches_internal_icao_but_internal_wrh_field_absent")
        else:
            verdict = SOURCE_AMBIGUOUS
            reasons.append(f"external_wrh_site_not_supported_by_internal_mapping:{external_wrh_sites}")
    elif "noaa_ncei" in external_types:
        if "noaa_ncei" in internal_types and "weather_gov_wrh" not in internal_types:
            verdict = SOURCE_MATCH_CONFIRMED
            reasons.append("ncei_source_text_matches_internal_noaa_station_fields")
        elif "noaa_ncei" in internal_types:
            verdict = SOURCE_PARTIAL
            reasons.append("ncei_fields_present_but_internal_mapping_has_additional_source_types")
        else:
            verdict = SOURCE_MISMATCH if "weather_gov_wrh" in internal_types else SOURCE_AMBIGUOUS
            reasons.append("ncei_source_text_not_supported_by_internal_mapping")
    elif "wunderground" in external_types:
        if "wunderground" in internal_types:
            verdict = SOURCE_MATCH_CONFIRMED
            reasons.append("wunderground_source_text_matches_internal_wu_url")
        else:
            verdict = SOURCE_AMBIGUOUS
            reasons.append("wunderground_source_text_without_internal_wu_url")
    elif "noaa" in external_types:
        if "noaa_ncei" in internal_types or "weather_gov_wrh" in internal_types:
            verdict = SOURCE_PARTIAL
            reasons.append("source_text_mentions_noaa_but_dataset_contract_needs_human_review")
        else:
            verdict = SOURCE_AMBIGUOUS
            reasons.append("source_text_mentions_noaa_without_internal_noaa_mapping")
    else:
        verdict = SOURCE_AMBIGUOUS
        reasons.append("source_text_does_not_identify_supported_dataset")

    if external_icaos and internal_icao and internal_icao not in external_icaos and external_wrh_sites and internal_icao not in external_wrh_sites:
        verdict = SOURCE_MISMATCH
        reasons.append(f"external_icao_mentions_do_not_include_internal_icao:{external_icaos} vs {internal_icao}")

    return {
        "verdict": verdict,
        "reasons": reasons,
        "warnings": warnings,
        "internal_source_types": internal_types,
        "external_source_types": external_types,
        "external_wrh_sites": external_wrh_sites,
        "external_icao_mentions": external_icaos,
        "internal_icao": internal_icao,
        "internal_wrh_site": internal_wrh_site,
        "wrh_ncei_separation": "separate_not_equivalent",
    }


def build_report(args: argparse.Namespace, now: str | None = None) -> dict[str, Any]:
    city = args.city.strip()
    warnings: list[str] = []
    input_paths = [Path(path) for path in args.blocked_resolutions] or DEFAULT_BLOCKED_RESOLUTIONS
    rows, used_inputs, input_warnings = choose_existing_inputs(input_paths)
    warnings.extend(input_warnings)

    evidence = collect_local_evidence(city, rows)
    docs_dir = Path(args.docs_dir)
    doc_slugs = extract_slugs_from_existing_docs(city, docs_dir)
    all_slugs = sorted(set(evidence["slugs"]) | set(doc_slugs) | set(args.slug or []))

    gamma_markets: list[dict[str, Any]] = []
    gamma_errors: list[dict[str, str]] = []
    if args.fetch_gamma:
        for slug in all_slugs:
            try:
                market = fetch_gamma_market_by_slug(slug, timeout=args.timeout)
                if isinstance(market, dict):
                    gamma_markets.append(market)
            except Exception as exc:
                gamma_errors.append({"slug": slug, "error": str(exc)})

    source_payloads = [parse_gamma_source_text(market) for market in gamma_markets]
    if not source_payloads and doc_slugs:
        source_payloads.append(parse_gamma_source_text({"description": extract_gamma_evidence_text_from_doc(city, docs_dir)}))

    internal_mapping = load_internal_mapping(Path(args.bot_path), city)
    warnings.extend(internal_mapping.get("warnings") or [])
    comparison = compare_sources(internal_mapping, source_payloads)
    warnings.extend(comparison.get("warnings") or [])
    if gamma_errors:
        warnings.append(f"gamma_lookup_errors={len(gamma_errors)}")

    return {
        "generated_at": now or utc_now_iso(),
        "tool": "source_fidelity_resolver_v0",
        "city": city,
        "log_only": True,
        "human_review_required": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "verdict": comparison["verdict"],
        "comparison": comparison,
        "inputs": {
            "blocked_resolutions": used_inputs,
            "docs_dir": str(docs_dir),
            "bot_path": str(args.bot_path),
            "fetch_gamma": bool(args.fetch_gamma),
            "slugs_from_docs_n": len(doc_slugs),
        },
        "local_evidence": evidence,
        "market_identifiers": {
            "slugs": all_slugs,
            "market_ids": evidence["market_ids"],
            "condition_ids": evidence["condition_ids"],
        },
        "gamma": {
            "fetched": bool(args.fetch_gamma),
            "markets_n": len(gamma_markets),
            "errors": gamma_errors,
            "parsed_sources": [
                {
                    key: value
                    for key, value in parsed.items()
                    if key != "raw_text"
                }
                for parsed in source_payloads
            ],
        },
        "internal_mapping": internal_mapping,
        "limitations": [
            "v0 is read-only and does not update runtime rows or bot mappings.",
            "Gamma lookup is optional; without --fetch-gamma the resolver uses local evidence and existing source-audit docs only.",
            "Source text parsing is heuristic and requires human review before any operational interpretation.",
            "WRH/weather.gov and NOAA NCEI datasets are reported as separate and not interchangeable.",
        ],
        "warnings": warnings,
    }


def _clip(value: Any, max_len: int = 96) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def render_markdown(report: dict[str, Any]) -> str:
    local = report["local_evidence"]
    ids = report["market_identifiers"]
    comparison = report["comparison"]
    mapping = report["internal_mapping"]
    meta = mapping.get("resolution_icao") or {}
    station = mapping.get("resolution_station") or {}
    lines = [
        f"# Source Fidelity Resolver - {report['city']}",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Verdict: `{report['verdict']}`",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        "## Scope",
        "",
        "- Classification: `NORMAL / LOG_ONLY`.",
        "- Human review is required before any operational interpretation.",
        "- WRH/weather.gov and NOAA NCEI are separate datasets and are not treated as equivalent.",
        "",
        "## Local Evidence",
        "",
        f"- City evidence rows: `{local['city_row_n']}`",
        f"- Slugs: `{len(ids['slugs'])}`",
        f"- Market IDs: `{len(ids['market_ids'])}`",
        f"- Condition IDs: `{len(ids['condition_ids'])}`",
        f"- Outcomes: `{local['outcomes']}`",
        "",
        "## Source Comparison",
        "",
        f"- Internal source types: `{comparison.get('internal_source_types')}`",
        f"- External source types: `{comparison.get('external_source_types')}`",
        f"- External WRH sites: `{comparison.get('external_wrh_sites')}`",
        f"- Internal ICAO: `{comparison.get('internal_icao')}`",
        f"- Internal WRH site: `{comparison.get('internal_wrh_site')}`",
        f"- WRH/NCEI separation: `{comparison.get('wrh_ncei_separation')}`",
        "",
        "Reasons:",
    ]
    lines.extend(f"- `{reason}`" for reason in comparison.get("reasons") or ["none"])
    lines.extend([
        "",
        "## Internal Mapping",
        "",
        f"- ICAO: `{meta.get('icao')}`",
        f"- Weather.gov WRH site: `{meta.get('weather_gov_timeseries_site')}`",
        f"- NOAA station ID: `{meta.get('noaa_station_id')}`",
        f"- NOAA daily station ID: `{meta.get('noaa_daily_station_id')}`",
        f"- WU URL: `{meta.get('wu_url')}`",
        f"- Station label: `{station.get('name')}`",
        "",
        "## Market Identifiers",
        "",
    ])
    for slug in ids["slugs"][:20]:
        lines.append(f"- `{slug}`")
    if len(ids["slugs"]) > 20:
        lines.append(f"- ... `{len(ids['slugs']) - 20}` more slugs")
    lines.extend([
        "",
        "## Gamma Source Hints",
        "",
        f"- Gamma fetched: `{report['gamma']['fetched']}`",
        f"- Gamma markets parsed: `{report['gamma']['markets_n']}`",
    ])
    for parsed in report["gamma"]["parsed_sources"][:8]:
        lines.append(
            "- "
            f"types=`{parsed.get('source_types')}` "
            f"wrh_sites=`{parsed.get('weather_gov_sites')}` "
            f"station=`{_clip(parsed.get('station_label'))}`"
        )
    lines.extend([
        "",
        "## Limitations",
        "",
    ])
    lines.extend(f"- {item}" for item in report["limitations"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in report["warnings"])

    markdown = "\n".join(lines) + "\n"
    for marker in OPERATIONAL_AUTHORIZATION_MARKERS:
        if marker in markdown:
            raise ValueError(f"output contains operational authorization marker: {marker}")
    return markdown


def write_outputs(report: dict[str, Any], output_dir: Path, docs_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify_city(report['city'])}_source_fidelity_resolver"
    json_path = output_dir / f"{stem}.json"
    md_path = docs_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args)
        json_path = md_path = None
        if not args.no_write:
            json_path, md_path = write_outputs(report, Path(args.output_dir), Path(args.docs_dir))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "city": report["city"],
        "verdict": report["verdict"],
        "log_only": report["log_only"],
        "human_review_required": report["human_review_required"],
        "output_json": str(json_path) if json_path else None,
        "output_md": str(md_path) if md_path else None,
        "warnings": report["warnings"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
