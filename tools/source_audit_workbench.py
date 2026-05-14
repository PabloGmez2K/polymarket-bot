#!/usr/bin/env python3
"""Source Audit Workbench v1.0 - LOG_ONLY read-only tool.

Builds a human review package for one Source Onboarding candidate.

No Telegram. No Railway. No database writes. No production data path. No environment reads.
No bot.py edits. No city mode changes. No executable trade recommendation.
"""

import argparse
import ast
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CANDIDATE_SOURCE = REPO_ROOT / "data" / "source_onboarding.json"
DEFAULT_SIGNALS_CROSSCHECK = REPO_ROOT / "data" / "runtime_import_derived" / "signals_crosscheck.jsonl"
DEFAULT_BLOCKED_RESOLUTIONS = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
DEFAULT_POLICY_ENV = REPO_ROOT / "data" / "runtime_import" / "policy_env_snapshot.json"
DEFAULT_POLICY_STATE = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"

STATUS_SOURCE_AUDIT_PASS = "SOURCE_AUDIT_PASS"
STATUS_SOURCE_AUDIT_FAIL = "SOURCE_AUDIT_FAIL"
STATUS_NEEDS_MANUAL_SOURCE_LOOKUP = "NEEDS_MANUAL_SOURCE_LOOKUP"
STATUS_READY_FOR_OBSERVED_AUDIT_REVIEW = "READY_FOR_OBSERVED_AUDIT_REVIEW"
STATUS_ALREADY_OBSERVED = "ALREADY_OBSERVED"
STATUS_OUT_OF_SCOPE = "OUT_OF_SCOPE"

VALID_STATUSES = {
    STATUS_SOURCE_AUDIT_PASS,
    STATUS_SOURCE_AUDIT_FAIL,
    STATUS_NEEDS_MANUAL_SOURCE_LOOKUP,
    STATUS_READY_FOR_OBSERVED_AUDIT_REVIEW,
    STATUS_ALREADY_OBSERVED,
    STATUS_OUT_OF_SCOPE,
}

RECOMMEND_SOURCE_AUDIT_PASS = "source_audit_pass"
RECOMMEND_OBSERVED_AUDIT_REVIEW = "observed_audit_review"
RECOMMEND_WAIT = "wait"
RECOMMEND_DISCARD = "discard"

NEXT_MANUAL_SOURCE_LOOKUP = "manual source lookup"
NEXT_OPUS_REVIEW = "Opus review for OBSERVED_AUDIT-only"
NEXT_NO_ACTION = "no action"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY - human source-audit package only. It does not authorize execution, "
    "policy edits, city-mode changes, automation, bankroll changes, or Phase C."
)

FORBIDDEN_MARKDOWN_TERMS = (
    "B" + "UY",
    "S" + "ELL",
    "S" + "KIP",
    "BANK" + "ROLL",
    "Fase" + " C",
)

ICAO_RE = re.compile(r"^[A-Z]{4}$")
NOAA_DAILY_RE = re.compile(r"^[A-Z0-9]{8,12}$")
NOAA_ISD_RE = re.compile(r"^[0-9]{11}$")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Source Audit Workbench v1.0 (LOG_ONLY) - City Intelligence v2"
    )
    parser.add_argument("--city", required=True)
    parser.add_argument("--candidate-source", default=str(DEFAULT_CANDIDATE_SOURCE))
    parser.add_argument("--signals-crosscheck", default=str(DEFAULT_SIGNALS_CROSSCHECK))
    parser.add_argument("--blocked-resolutions", default=str(DEFAULT_BLOCKED_RESOLUTIONS))
    parser.add_argument("--policy-env", default=str(DEFAULT_POLICY_ENV))
    parser.add_argument("--policy-state", default=str(DEFAULT_POLICY_STATE))
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    parser.add_argument("--no-network", action="store_true", default=True)
    parser.add_argument("--icao")
    parser.add_argument("--noaa-daily-station-id")
    parser.add_argument("--noaa-station-id")
    parser.add_argument("--polymarket-source-url")
    parser.add_argument("--wu-url")
    return parser.parse_args(argv)


def slugify_city(city):
    slug = re.sub(r"[^a-z0-9]+", "_", city.strip().lower())
    return slug.strip("_") or "city"


def _default_json_output(city):
    return REPO_ROOT / "data" / "source_audits" / f"{slugify_city(city)}_source_audit.json"


def _default_md_output(city):
    return REPO_ROOT / "docs" / "source_audits" / f"{slugify_city(city)}_source_audit.md"


def _load_json_optional(path_str, label, default):
    path = Path(path_str)
    if not path.exists():
        return default, f"{label} not found: {path}"
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return json.loads(raw.decode("utf-8")), None
    except Exception as exc:
        return default, f"{label} parse error: {exc}"


def _load_jsonl_optional(path_str, label):
    path = Path(path_str)
    if not path.exists():
        return [], f"{label} not found: {path}"
    rows = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line:
                rows.append(json.loads(line))
        return rows, None
    except Exception as exc:
        return [], f"{label} parse error: {exc}"


def _parse_csv(value):
    if not value:
        return set()
    return {part.strip() for part in str(value).split(",") if part and part.strip()}


def _literal_set(node):
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        values = set()
        for item in node.elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                values.add(item.value)
        return values
    return set()


def _literal_dict(node):
    if not isinstance(node, ast.Dict):
        return {}
    result = {}
    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            continue
        city = key_node.value
        if isinstance(value_node, ast.Constant):
            result[city] = value_node.value
        elif isinstance(value_node, ast.Dict):
            meta = {}
            for mk, mv in zip(value_node.keys, value_node.values):
                if not isinstance(mk, ast.Constant) or not isinstance(mk.value, str):
                    continue
                if isinstance(mv, ast.Constant):
                    meta[mk.value] = mv.value
                elif isinstance(mv, ast.Call) and mk.value == "wu_url":
                    meta[mk.value] = "<template>"
            result[city] = meta
    return result


def load_bot_reference(bot_path=None):
    """Read selected bot.py reference constants via AST without executing it."""
    path = Path(bot_path or (REPO_ROOT / "bot.py"))
    refs = {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    }
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        refs["warnings"].append(f"bot.py AST parse unavailable: {exc}")
        return refs

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "RESOLUTION_ICAO" in names:
            refs["resolution_icao"] = _literal_dict(node.value)
        elif "RESOLUTION_STATIONS" in names:
            refs["resolution_stations"] = _literal_dict(node.value)
        elif "OBSERVED_AUDIT_CITIES" in names:
            refs["observed_audit_cities"] = _literal_set(node.value)
        elif "CITY_TIMEZONES" in names:
            refs["city_timezones"] = _literal_dict(node.value)
    return refs


def find_candidate(city, candidate_source):
    for row in candidate_source.get("cities", []) or []:
        if row.get("city") == city:
            return row
    return None


def _iter_crosscheck_details(row):
    for key in ("trader_only_details", "match_details", "bot_only_details"):
        for detail in row.get(key, []) or []:
            yield key, detail


def aggregate_crosscheck(city, rows):
    trader_only_count = 0
    trader_only_runs = 0
    conditions = Counter()
    dates = set()
    max_wr = None
    consensus_count = 0

    for row in rows:
        found_in_run = False
        for bucket_key, detail in _iter_crosscheck_details(row):
            if detail.get("city") != city:
                continue
            for condition in detail.get("conditions", []) or []:
                if condition:
                    conditions[str(condition)] += 1
            for date_value in detail.get("dates", []) or []:
                if date_value:
                    dates.add(date_value)
            if detail.get("has_consensus_market"):
                consensus_count += 1
            wr = detail.get("max_trader_wr")
            if isinstance(wr, (int, float)):
                max_wr = wr if max_wr is None else max(max_wr, wr)
            if bucket_key == "trader_only_details":
                trader_only_count += int(detail.get("n_signals", 0) or 0)
                found_in_run = True
        if found_in_run:
            trader_only_runs += 1

    total_conditions = sum(conditions.values())
    range_count = conditions.get("range", 0)
    return {
        "trader_only_count": trader_only_count,
        "trader_only_runs": trader_only_runs,
        "persistence": trader_only_runs,
        "condition_mix": dict(sorted(conditions.items())),
        "range_only": total_conditions > 0 and range_count == total_conditions,
        "known_dates": sorted(dates),
        "max_trader_wr": max_wr,
        "consensus_count": consensus_count,
    }


def aggregate_blocked(city, rows):
    total = 0
    evaluated = 0
    wins = 0
    for row in rows:
        if row.get("city") != city:
            continue
        total += 1
        bot_eval = row.get("bot_evaluation")
        if bot_eval is not None and str(bot_eval).strip():
            evaluated += 1
            if row.get("win_for_trader") is True:
                wins += 1
            else:
                outcome = str(row.get("outcome", "") or row.get("resolution", "")).lower()
                if outcome in {"win", "correct", "true", "yes", "1"}:
                    wins += 1
    wr = wins / evaluated if evaluated else None
    return {"n": total, "n_evaluated": evaluated, "wr": wr}


def build_policy_status(city, policy_env, policy_state, refs):
    variables = policy_env.get("variables", {}) if isinstance(policy_env, dict) else {}
    active = _parse_csv(variables.get("ACTIVE_TRADING_CITIES"))
    canary = _parse_csv(variables.get("CANARY_TRADING_CITIES"))
    blocked = _parse_csv(variables.get("BLOCKED_CITIES"))
    auto_canary = set((policy_state.get("auto_canary_cities", {}) or {}).keys())
    auto_shadow = set((policy_state.get("auto_shadow_cities", {}) or {}).keys())
    auto_blocked = set((policy_state.get("auto_blocked_cities", {}) or {}).keys())
    return {
        "active": city in active,
        "canary": city in canary,
        "blocked": city in blocked or city.lower() in {c.lower() for c in blocked},
        "auto_canary": city in auto_canary,
        "auto_shadow": city in auto_shadow,
        "auto_blocked": city in auto_blocked,
        "observed_audit": city in refs["observed_audit_cities"],
        "has_resolution_icao": city in refs["resolution_icao"],
        "has_resolution_station": city in refs["resolution_stations"],
        "has_timezone": city in refs["city_timezones"],
    }


def validate_source_fields(icao=None, noaa_daily_station_id=None, noaa_station_id=None):
    errors = []
    if icao and not ICAO_RE.match(icao):
        errors.append("icao must be four uppercase letters")
    if noaa_daily_station_id and not NOAA_DAILY_RE.match(noaa_daily_station_id):
        errors.append("noaa_daily_station_id has invalid structure")
    if noaa_station_id and not NOAA_ISD_RE.match(noaa_station_id):
        errors.append("noaa_station_id must be eleven digits")
    return errors


def _select_source_candidate(city, args, refs):
    existing_meta = refs["resolution_icao"].get(city, {}) or {}
    station_meta = refs["resolution_stations"].get(city, {}) or {}
    icao = args.icao or existing_meta.get("icao")
    noaa_daily = args.noaa_daily_station_id or existing_meta.get("noaa_daily_station_id")
    noaa_station = args.noaa_station_id or existing_meta.get("noaa_station_id")
    wu_url = args.wu_url or existing_meta.get("wu_url")
    if wu_url == "<template>" and icao:
        wu_url = f"https://www.wunderground.com/history/daily/{icao}/date/{{date}}"
    return {
        "icao": icao,
        "noaa_daily_station_id": noaa_daily,
        "noaa_station_id": noaa_station,
        "station_name": station_meta.get("name"),
        "lat": station_meta.get("lat"),
        "lon": station_meta.get("lon"),
        "source_primary": args.polymarket_source_url or wu_url,
        "source_secondary": args.wu_url if args.polymarket_source_url else None,
    }


def classify_audit(city, candidate, source_candidate, evidence, policy_status, validation_errors):
    has_public_source = bool(
        source_candidate.get("icao")
        and (source_candidate.get("noaa_daily_station_id") or source_candidate.get("noaa_station_id"))
    )
    user_supplied_source = bool(
        source_candidate.get("icao")
        and (
            source_candidate.get("noaa_daily_station_id")
            or source_candidate.get("noaa_station_id")
            or source_candidate.get("source_primary")
        )
    )
    source_unverified = not user_supplied_source
    no_local_station = not (
        source_candidate.get("noaa_daily_station_id") or source_candidate.get("noaa_station_id")
    )
    range_only = bool(evidence.get("range_only"))

    if policy_status["observed_audit"]:
        status = STATUS_ALREADY_OBSERVED
        recommendation = RECOMMEND_WAIT
        next_step = NEXT_NO_ACTION
    elif policy_status["active"] or policy_status["canary"] or policy_status["auto_canary"]:
        status = STATUS_OUT_OF_SCOPE
        recommendation = RECOMMEND_WAIT
        next_step = NEXT_NO_ACTION
    elif validation_errors:
        status = STATUS_SOURCE_AUDIT_FAIL
        recommendation = RECOMMEND_DISCARD
        next_step = NEXT_MANUAL_SOURCE_LOOKUP
    elif not user_supplied_source:
        status = STATUS_NEEDS_MANUAL_SOURCE_LOOKUP
        recommendation = RECOMMEND_WAIT
        next_step = NEXT_MANUAL_SOURCE_LOOKUP
    elif has_public_source and not range_only:
        status = STATUS_READY_FOR_OBSERVED_AUDIT_REVIEW
        recommendation = RECOMMEND_OBSERVED_AUDIT_REVIEW
        next_step = NEXT_OPUS_REVIEW
    elif has_public_source:
        status = STATUS_SOURCE_AUDIT_PASS
        recommendation = RECOMMEND_SOURCE_AUDIT_PASS
        next_step = NEXT_OPUS_REVIEW
    else:
        status = STATUS_NEEDS_MANUAL_SOURCE_LOOKUP
        recommendation = RECOMMEND_WAIT
        next_step = NEXT_MANUAL_SOURCE_LOOKUP

    mismatch_risk = "unknown"
    if validation_errors:
        mismatch_risk = "high"
    elif has_public_source and source_candidate.get("source_primary"):
        mismatch_risk = "low"
    elif source_candidate.get("icao") and no_local_station:
        mismatch_risk = "medium"

    if range_only and recommendation == RECOMMEND_OBSERVED_AUDIT_REVIEW:
        recommendation = RECOMMEND_SOURCE_AUDIT_PASS

    return {
        "status": status,
        "risk": {
            "mismatch_risk": mismatch_risk,
            "no_local_station": no_local_station,
            "source_unverified": source_unverified,
            "range_only_not_operable": range_only,
        },
        "recommendation": recommendation,
        "proposed_next_step": next_step,
    }


def build_audit(args, now=None):
    city = args.city.strip()
    warnings = []

    candidate_source, err = _load_json_optional(args.candidate_source, "candidate_source", {})
    if err:
        warnings.append(err)
    policy_env, err = _load_json_optional(args.policy_env, "policy_env", {})
    if err:
        warnings.append(err)
    policy_state, err = _load_json_optional(args.policy_state, "policy_state", {})
    if err:
        warnings.append(err)
    signal_rows, err = _load_jsonl_optional(args.signals_crosscheck, "signals_crosscheck")
    if err:
        warnings.append(err)
    blocked_rows, err = _load_jsonl_optional(args.blocked_resolutions, "blocked_resolutions")
    if err:
        warnings.append(err)

    refs = load_bot_reference()
    warnings.extend(refs["warnings"])

    candidate = find_candidate(city, candidate_source)
    source_candidate = _select_source_candidate(city, args, refs)
    crosscheck = aggregate_crosscheck(city, signal_rows)
    blocked = aggregate_blocked(city, blocked_rows)
    policy_status = build_policy_status(city, policy_env, policy_state, refs)
    validation_errors = validate_source_fields(
        source_candidate.get("icao"),
        source_candidate.get("noaa_daily_station_id"),
        source_candidate.get("noaa_station_id"),
    )

    evidence = {
        "trader_only_count": crosscheck["trader_only_count"],
        "persistence": crosscheck["persistence"],
        "blocked_signals": blocked,
        "condition_mix": crosscheck["condition_mix"],
        "range_only": crosscheck["range_only"],
        "existing_policy_status": policy_status,
        "candidate_state": candidate.get("state") if candidate else None,
        "candidate_priority_score": candidate.get("priority_score") if candidate else None,
        "known_dates": crosscheck["known_dates"],
        "max_trader_wr": crosscheck["max_trader_wr"],
        "consensus_count": crosscheck["consensus_count"],
    }
    decision = classify_audit(city, candidate, source_candidate, evidence, policy_status, validation_errors)

    generated_at = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "generated_at": generated_at,
        "tool": "source_audit_workbench_v1",
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "city": city,
        "status": decision["status"],
        "source_candidate": source_candidate,
        "evidence": evidence,
        "risk": decision["risk"],
        "recommendation": decision["recommendation"],
        "proposed_next_step": decision["proposed_next_step"],
        "validation": {
            "no_network": bool(args.no_network),
            "network_validation": "skipped",
            "errors": validation_errors,
            "candidate_found": candidate is not None,
        },
        "inputs": {
            "candidate_source": args.candidate_source,
            "signals_crosscheck": args.signals_crosscheck,
            "blocked_resolutions": args.blocked_resolutions,
            "policy_env": args.policy_env,
            "policy_state": args.policy_state,
        },
        "warnings": warnings,
    }


def render_markdown(payload):
    source = payload["source_candidate"]
    evidence = payload["evidence"]
    blocked = evidence["blocked_signals"]
    risk = payload["risk"]
    lines = [
        f"# Source Audit - {payload['city']}",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        "## Verdict",
        "",
        f"- Status: `{payload['status']}`",
        f"- Recommendation: `{payload['recommendation']}`",
        f"- Proposed next step: `{payload['proposed_next_step']}`",
        "",
        "## Evidence",
        "",
        f"- Trader-only count: `{evidence['trader_only_count']}`",
        f"- Persistence: `{evidence['persistence']}`",
        f"- Blocked signals: `n={blocked['n']}`, `wr={blocked['wr']}`",
        f"- Condition mix: `{evidence['condition_mix']}`",
        f"- Range-only: `{evidence['range_only']}`",
        f"- Existing policy status: `{evidence['existing_policy_status']}`",
        "",
        "## Candidate Source",
        "",
        f"- ICAO: `{source.get('icao')}`",
        f"- NOAA daily station: `{source.get('noaa_daily_station_id')}`",
        f"- NOAA station: `{source.get('noaa_station_id')}`",
        f"- Station name: `{source.get('station_name')}`",
        f"- Lat/lon: `{source.get('lat')}`, `{source.get('lon')}`",
        f"- Primary source: `{source.get('source_primary')}`",
        f"- Secondary source: `{source.get('source_secondary')}`",
        "",
        "## Mismatch Risk",
        "",
        f"- Mismatch risk: `{risk['mismatch_risk']}`",
        f"- No local station: `{risk['no_local_station']}`",
        f"- Source unverified: `{risk['source_unverified']}`",
        f"- Range-only not operable: `{risk['range_only_not_operable']}`",
        "",
        "## LOG_ONLY Disclaimer",
        "",
        LOG_ONLY_DISCLAIMER,
    ]
    md = "\n".join(lines)
    for term in FORBIDDEN_MARKDOWN_TERMS:
        if term in md:
            raise ValueError(f"Markdown contains forbidden term: {term}")
    return md


def write_outputs(payload, output_json, output_md):
    out_json = Path(output_json)
    out_md = Path(output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")


def main(argv=None):
    args = parse_args(argv)
    city = args.city.strip()
    if not args.output_json:
        args.output_json = str(_default_json_output(city))
    if not args.output_md:
        args.output_md = str(_default_md_output(city))

    payload = build_audit(args)
    try:
        write_outputs(payload, args.output_json, args.output_md)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for warning in payload.get("warnings", []):
        print(f"  WARN: {warning}")
    print(f"Source audit JSON written to {args.output_json}")
    print(f"Source audit Markdown written to {args.output_md}")
    print(json.dumps({
        "city": payload["city"],
        "status": payload["status"],
        "recommendation": payload["recommendation"],
        "proposed_next_step": payload["proposed_next_step"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
