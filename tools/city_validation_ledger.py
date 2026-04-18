#!/usr/bin/env python3
"""Build a city validation ledger from external trader intelligence and local observability."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

bot = None


DEFAULT_CROSS_PATH = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_TRACKER_PATH = REPO_ROOT / "data" / "city_probe_visibility_tracker.json"
DEFAULT_SHADOW_TRACKING_PATH = REPO_ROOT / "data" / "runtime_import" / "shadow_city_tracking.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "data" / "runtime_import" / "audit.json"
DEFAULT_CITY_POLICY_STATE_PATH = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"
DEFAULT_SKIP_LOG_PATH = REPO_ROOT / "data" / "runtime_import" / "skip_log.jsonl"
DEFAULT_RUNTIME_MANIFEST_PATH = REPO_ROOT / "data" / "runtime_import" / "runtime_import_manifest.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_validation_ledger.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_validation_ledger_latest.md"
RUNTIME_MANIFEST_NAME = "runtime_import_manifest.json"

RUNTIME_POLICY_TO_EFFECTIVE = {
    "auto_blocked": "blocked",
    "auto_canary": "canary",
    "auto_shadow": "shadow",
}

STRUCTURAL_BLOCK_GUARDRAILS = {
    "London": {
        "reason": "weather_underground_openmeteo_mismatch",
        "detail": "Explicit documented settlement/source mismatch with repeated losses; keep blocked until revalidated.",
    }
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Convierte discovery externo + observabilidad local en un ledger de validacion por ciudad."
        )
    )
    parser.add_argument("--cross", default=str(DEFAULT_CROSS_PATH))
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--tracker", default=str(DEFAULT_TRACKER_PATH))
    parser.add_argument("--shadow-tracking", default=str(DEFAULT_SHADOW_TRACKING_PATH))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument("--city-policy-state", default=str(DEFAULT_CITY_POLICY_STATE_PATH))
    parser.add_argument("--skip-log", default=str(DEFAULT_SKIP_LOG_PATH))
    parser.add_argument("--runtime-manifest", default=str(DEFAULT_RUNTIME_MANIFEST_PATH))
    parser.add_argument("--max-runtime-snapshot-age-hours", type=float, default=24.0)
    parser.add_argument("--min-reference-traders", type=int, default=3)
    parser.add_argument("--min-visible-snapshots", type=int, default=2)
    parser.add_argument("--recent-skip-cycles", type=int, default=2)
    parser.add_argument("--recent-skip-min-edge", type=float, default=15.0)
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str, required=True):
    path = Path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_jsonl(path_str):
    path = Path(path_str)
    if not path.exists():
        return []
    rows = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def parse_utc_datetime(value):
    if not value:
        raise ValueError("empty datetime")
    text = str(value).strip().replace("Z", "+00:00")
    if "." in text:
        head, tail = text.split(".", 1)
        if "+" in tail:
            fraction, offset = tail.split("+", 1)
            text = f"{head}.{fraction[:6]}+{offset}"
        elif "-" in tail:
            fraction, offset = tail.split("-", 1)
            text = f"{head}.{fraction[:6]}-{offset}"
        else:
            text = f"{head}.{tail[:6]}"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_runtime_manifest_status(args):
    manifest_path = Path(args.runtime_manifest)
    if not manifest_path.exists():
        return {
            "status": "stale",
            "manifest_path": str(manifest_path),
            "stale_inputs": [{
                "name": "runtime_manifest",
                "path": str(manifest_path),
                "reason": "missing_manifest",
            }],
        }
    try:
        manifest = load_json(manifest_path, required=True)
        pulled_at = parse_utc_datetime(manifest.get("pulled_at"))
        manifest_files = manifest.get("files")
        if not isinstance(manifest_files, list):
            raise ValueError("manifest.files must be a list")
    except Exception as exc:
        return {
            "status": "stale",
            "manifest_path": str(manifest_path),
            "stale_inputs": [{
                "name": "runtime_manifest",
                "path": str(manifest_path),
                "reason": "invalid_manifest",
                "error": f"{type(exc).__name__}: {exc}",
            }],
        }

    manifest_dir = manifest_path.parent
    expected_names = []
    drift_inputs = []
    for index, item in enumerate(manifest_files):
        name = item.get("name") if isinstance(item, dict) else None
        if not name or "/" in str(name) or "\\" in str(name):
            drift_inputs.append({
                "name": str(name or f"files[{index}]"),
                "path": str(manifest_path),
                "reason": "invalid_manifest_file_name",
            })
            continue
        expected_names.append(str(name))

    duplicate_names = sorted(name for name, count in Counter(expected_names).items() if count > 1)
    for name in duplicate_names:
        drift_inputs.append({
            "name": name,
            "path": str(manifest_path),
            "reason": "duplicate_manifest_entry",
        })

    expected_set = set(expected_names)
    actual_set = {
        child.name
        for child in manifest_dir.iterdir()
        if child.is_file() and child.name != manifest_path.name
    }
    for name in sorted(expected_set - actual_set):
        drift_inputs.append({
            "name": name,
            "path": str(manifest_dir / name),
            "reason": "listed_file_missing",
        })
    for name in sorted(actual_set - expected_set):
        drift_inputs.append({
            "name": name,
            "path": str(manifest_dir / name),
            "reason": "unlisted_file_present",
        })
    for item in manifest_files:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if name not in actual_set:
            continue
        expected_bytes = item.get("bytes")
        if expected_bytes is None:
            continue
        actual_bytes = (manifest_dir / name).stat().st_size
        if int(expected_bytes) != actual_bytes:
            drift_inputs.append({
                "name": name,
                "path": str(manifest_dir / name),
                "reason": "byte_count_mismatch",
                "manifest_bytes": int(expected_bytes),
                "actual_bytes": actual_bytes,
            })

    if drift_inputs:
        return {
            "status": "drift",
            "manifest_path": str(manifest_path),
            "pulled_at": pulled_at.isoformat(),
            "manifest_dir": str(manifest_dir),
            "manifest_file_count": len(expected_set),
            "disk_file_count": len(actual_set),
            "drift_inputs": drift_inputs,
        }

    now = datetime.now(timezone.utc)
    age_hours = (now - pulled_at).total_seconds() / 3600
    max_age_hours = float(args.max_runtime_snapshot_age_hours)
    if age_hours > max_age_hours:
        return {
            "status": "stale",
            "manifest_path": str(manifest_path),
            "pulled_at": pulled_at.isoformat(),
            "age_hours": round(age_hours, 2),
            "max_age_hours": max_age_hours,
            "stale_inputs": [{
                "name": "runtime_manifest",
                "path": str(manifest_path),
                "reason": "snapshot_stale",
                "pulled_at": pulled_at.isoformat(),
                "age_hours": round(age_hours, 2),
                "max_age_hours": max_age_hours,
            }],
        }

    return {
        "status": "fresh",
        "manifest_path": str(manifest_path),
        "pulled_at": pulled_at.isoformat(),
        "manifest_dir": str(manifest_dir),
        "manifest_file_count": len(expected_set),
        "disk_file_count": len(actual_set),
        "age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
        "stale_inputs": [],
        "drift_inputs": [],
    }


def build_runtime_input_status(args):
    required_inputs = {
        "shadow_tracking": args.shadow_tracking,
        "audit": args.audit,
        "city_policy_state": args.city_policy_state,
    }
    missing = [
        {"name": name, "path": path}
        for name, path in required_inputs.items()
        if not Path(path).exists()
    ]
    manifest_status = build_runtime_manifest_status(args)
    if manifest_status["status"] == "drift":
        return {
            "status": "manifest_drift",
            "required_inputs": required_inputs,
            "missing_inputs": [],
            "stale_inputs": [],
            "manifest_drift_inputs": manifest_status.get("drift_inputs", []),
            "manifest": manifest_status,
        }
    if missing:
        return {
            "status": "missing",
            "required_inputs": required_inputs,
            "missing_inputs": missing,
            "stale_inputs": [],
            "manifest_drift_inputs": [],
            "manifest": {},
        }
    return {
        "status": "stale" if manifest_status["status"] == "stale" else "available",
        "required_inputs": required_inputs,
        "missing_inputs": [],
        "stale_inputs": manifest_status.get("stale_inputs", []),
        "manifest_drift_inputs": [],
        "manifest": manifest_status,
    }


def build_runtime_missing_payload(args, runtime_input_status):
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "generated_at": now,
        "inputs": {
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
            "tracker": args.tracker,
            "shadow_tracking": args.shadow_tracking,
            "audit": args.audit,
            "city_policy_state": args.city_policy_state,
            "runtime_manifest": args.runtime_manifest,
        },
        "summary": {
            "n_cities": 0,
            "runtime_inputs_status": runtime_input_status["status"],
            "missing_runtime_inputs": runtime_input_status["missing_inputs"],
            "stale_runtime_inputs": runtime_input_status.get("stale_inputs", []),
            "manifest_drift_inputs": runtime_input_status.get("manifest_drift_inputs", []),
            "runtime_manifest": runtime_input_status.get("manifest", {}),
            "evidence_status_counts": {},
            "recommendation_counts": {},
            "bottleneck_counts": {f"runtime_inputs_{runtime_input_status['status']}": 1},
            "enrichment_health": {},
        },
        "cities": [],
    }


def load_bot_module():
    global bot
    if bot is None:
        import bot as bot_module  # type: ignore
        bot = bot_module
    return bot


def build_bot_import_failed_status(args, error):
    runtime_input_status = build_runtime_input_status(args)
    runtime_input_status["status"] = "missing"
    runtime_input_status["missing_inputs"].append({
        "name": "bot_module",
        "path": str(REPO_ROOT / "bot.py"),
        "error": f"{type(error).__name__}: {error}",
    })
    return runtime_input_status


def build_probe_by_city(probe):
    probe_by_city = {}
    for market in probe.get("markets", []):
        city = market.get("city") or ""
        probe_by_city.setdefault(city, []).append(market)
    return probe_by_city


def build_tracker_lookup(tracker):
    lookup = {}
    if not isinstance(tracker, dict):
        return lookup
    for snapshot in tracker.get("history", []):
        if not isinstance(snapshot, dict):
            continue
        probe_generated_at = snapshot.get("probe_generated_at")
        visible_cities = set(snapshot.get("visible_cities", []))
        for city, row in (snapshot.get("cities") or {}).items():
            state = lookup.setdefault(city, {
                "n_visible_snapshots": 0,
                "n_comparable_snapshots": 0,
                "total_markets_seen": 0,
                "last_seen_at": None,
                "latest_market_count": 0,
            })
            market_count = int(row.get("market_count", 0) or 0)
            comparable_count = int(row.get("comparable_market_count", 0) or 0)
            if city in visible_cities and market_count > 0:
                state["n_visible_snapshots"] += 1
                state["total_markets_seen"] += market_count
                state["latest_market_count"] = market_count
                state["last_seen_at"] = probe_generated_at
            if comparable_count > 0:
                state["n_comparable_snapshots"] += 1
    return lookup


def build_enrichment_lookup(enrichment):
    lookup = {}
    for trader in enrichment.get("traders", []):
        label = trader.get("pseudonym") or trader.get("address", "")[:10]
        lookup[label] = trader
    return lookup


def summarize_enrichment_health(enrichment):
    summary = enrichment.get("summary", {}) if isinstance(enrichment, dict) else {}
    reference_quality_counts = summary.get("reference_quality_counts", {}) or {}
    quality_reference_traders = int(summary.get("quality_reference_traders", 0) or 0)
    active_directional_traders = int(summary.get("active_directional_traders", 0) or 0)
    traders_with_closed_positions = int(summary.get("traders_with_closed_positions", 0) or 0)
    traders_with_active_positions = int(summary.get("traders_with_active_positions", 0) or 0)
    likely_input_degraded = bool(summary.get("likely_input_degraded", False))
    health_status = summary.get("health_status") or "unknown"
    return {
        "reference_quality_counts": reference_quality_counts,
        "quality_reference_traders": quality_reference_traders,
        "active_directional_traders": active_directional_traders,
        "traders_with_closed_positions": traders_with_closed_positions,
        "traders_with_active_positions": traders_with_active_positions,
        "health_status": health_status,
        "likely_input_degraded": likely_input_degraded,
    }


def build_runtime_policy_lookup(city_policy_state):
    lookup = {}
    if not isinstance(city_policy_state, dict):
        return lookup

    sections = [
        ("auto_blocked_cities", "auto_blocked"),
        ("auto_canary_cities", "auto_canary"),
        ("auto_shadow_cities", "auto_shadow"),
    ]
    for section_name, runtime_policy_mode in sections:
        section = city_policy_state.get(section_name, {})
        if not isinstance(section, dict):
            continue
        for city, details in section.items():
            if not city:
                continue
            if city in lookup:
                lookup[city].setdefault("runtime_policy_collisions", []).append({
                    "section": section_name,
                    "runtime_policy_mode": runtime_policy_mode,
                    "details": details if isinstance(details, dict) else {},
                })
                continue
            lookup[city] = {
                "runtime_policy_mode": runtime_policy_mode,
                "runtime_policy_source": section_name,
                "runtime_policy_details": details if isinstance(details, dict) else {},
                "runtime_policy_collisions": [],
            }
    return lookup


def normalize_runtime_policy(runtime_policy_mode):
    return RUNTIME_POLICY_TO_EFFECTIVE.get(runtime_policy_mode)


def resolve_effective_policy_mode(cross_policy_mode, effective_runtime_policy):
    if "blocked" in {cross_policy_mode, effective_runtime_policy}:
        return "blocked"
    if cross_policy_mode == "active":
        return "active"
    if "canary" in {cross_policy_mode, effective_runtime_policy}:
        return "canary"
    if "shadow" in {cross_policy_mode, effective_runtime_policy}:
        return "shadow"
    return effective_runtime_policy or cross_policy_mode


def build_policy_context(city_row, runtime_policy_lookup):
    city = city_row.get("city", "")
    cross_policy_mode = city_row.get("policy_mode", "unknown")
    runtime_policy = runtime_policy_lookup.get(city, {})
    runtime_policy_mode = runtime_policy.get("runtime_policy_mode", "runtime_unknown")
    effective_runtime_policy = normalize_runtime_policy(runtime_policy_mode)
    effective_policy_mode = resolve_effective_policy_mode(
        cross_policy_mode=cross_policy_mode,
        effective_runtime_policy=effective_runtime_policy,
    )

    drift_flags = []
    if (
        effective_runtime_policy
        and cross_policy_mode not in {effective_runtime_policy, "runtime_only"}
    ):
        drift_flags.append("policy_divergence")
    if runtime_policy.get("runtime_policy_collisions"):
        drift_flags.append("runtime_policy_collision")

    return {
        "cross_policy_mode": cross_policy_mode,
        "runtime_policy_mode": runtime_policy_mode,
        "runtime_policy_source": runtime_policy.get("runtime_policy_source"),
        "runtime_policy_details": runtime_policy.get("runtime_policy_details", {}),
        "runtime_policy_collisions": runtime_policy.get("runtime_policy_collisions", []),
        "policy_mode": effective_policy_mode,
        "drift_flags": drift_flags,
    }


def build_runtime_only_city_rows(cross_city_rows, runtime_policy_lookup):
    existing = {
        row.get("city")
        for row in cross_city_rows
        if isinstance(row, dict) and row.get("city")
    }
    rows = []
    for city in sorted(runtime_policy_lookup):
        if city in existing:
            continue
        rows.append({
            "city": city,
            "row_kind": "runtime_only",
            "policy_mode": "runtime_only",
            "reference_traders": [],
            "reference_quality_counts": {},
            "current_probe_markets": 0,
        })
    return rows


def summarize_shadow_tracking(city, shadow_tracking):
    if not isinstance(shadow_tracking, dict):
        return {
            "available": False,
            "markets_seen": 0,
            "edge_hits": 0,
            "cycles_seen": 0,
            "best_edge_pct": 0.0,
            "support_count": 0,
            "resolved_directional_count": 0,
        }

    city_metrics = {}
    cities = shadow_tracking.get("cities", {})
    if isinstance(cities, dict):
        city_metrics = cities.get(city, {}) or {}

    directional_history = shadow_tracking.get("directional_history", [])
    matching_history = [
        row for row in directional_history
        if isinstance(row, dict) and row.get("city") == city
    ]

    return {
        "available": True,
        "markets_seen": int(city_metrics.get("markets_seen", 0) or 0),
        "edge_hits": int(city_metrics.get("edge_hits", 0) or 0),
        "cycles_seen": int(city_metrics.get("cycles_seen", 0) or 0),
        "best_edge_pct": round(float(city_metrics.get("best_edge_pct", 0) or 0), 1),
        "support_count": len(city_metrics.get("recent_edges", []) if isinstance(city_metrics.get("recent_edges"), list) else []),
        "resolved_directional_count": len(matching_history),
    }


def summarize_audit(city, audit):
    if not isinstance(audit, dict):
        return {
            "available": False,
            "noaa_rows": 0,
            "latest_date": "",
        }

    rows = []
    for row in audit.get(bot.OBSERVED_AUDIT_KEY, []):
        if not isinstance(row, dict):
            continue
        if row.get("city") != city:
            continue
        if row.get("source") != "noaa_ncei":
            continue
        rows.append(row)
    rows.sort(key=lambda row: str(row.get("date", "")), reverse=True)
    return {
        "available": True,
        "noaa_rows": len(rows),
        "latest_date": rows[0].get("date", "") if rows else "",
    }


def summarize_recent_skip_log(city, skip_rows, recent_skip_cycles, recent_skip_min_edge):
    if not isinstance(skip_rows, list) or not skip_rows:
        return {
            "available": False,
            "recent_cycles": [],
            "total_recent_skips": 0,
            "reason_counts": {},
            "useful_skip_count": 0,
            "useful_reason_counts": {},
            "useful_policy_gate_count": 0,
            "useful_examples": [],
        }

    cycle_ids = sorted(
        {
            str(row.get("cycle_id", "")).strip()
            for row in skip_rows
            if isinstance(row, dict) and str(row.get("cycle_id", "")).strip()
        }
    )
    if not cycle_ids:
        return {
            "available": True,
            "recent_cycles": [],
            "total_recent_skips": 0,
            "reason_counts": {},
            "useful_skip_count": 0,
            "useful_reason_counts": {},
            "useful_policy_gate_count": 0,
            "useful_examples": [],
        }

    recent_cycles = cycle_ids[-max(1, int(recent_skip_cycles)):]
    recent_rows = [
        row for row in skip_rows
        if isinstance(row, dict)
        and row.get("city") == city
        and row.get("cycle_id") in recent_cycles
    ]
    useful_rows = []
    for row in recent_rows:
        edge_pct = row.get("edge_pct")
        if edge_pct is None:
            continue
        try:
            if float(edge_pct) >= float(recent_skip_min_edge):
                useful_rows.append(row)
        except (TypeError, ValueError):
            continue

    useful_policy_gate_count = sum(
        1 for row in useful_rows
        if row.get("skip_reason") in {"shadow_only_override", "fuera_allowlist"}
    )

    useful_examples = []
    for row in useful_rows[:3]:
        useful_examples.append({
            "cycle_id": row.get("cycle_id"),
            "skip_reason": row.get("skip_reason"),
            "condition": row.get("condition"),
            "edge_pct": row.get("edge_pct"),
            "question": row.get("question"),
            "city_mode": row.get("city_mode"),
        })

    return {
        "available": True,
        "recent_cycles": recent_cycles,
        "total_recent_skips": len(recent_rows),
        "reason_counts": dict(Counter(row.get("skip_reason") for row in recent_rows)),
        "useful_skip_count": len(useful_rows),
        "useful_reason_counts": dict(Counter(row.get("skip_reason") for row in useful_rows)),
        "useful_policy_gate_count": useful_policy_gate_count,
        "useful_examples": useful_examples,
    }


def compute_settlement_fidelity(city, resolution_meta, probe_markets, audit_summary):
    score = 0
    rationale = []

    if resolution_meta.get("icao"):
        score += 1
        rationale.append("icao")
    if resolution_meta.get("wu_url"):
        score += 1
        rationale.append("wu_url")
    if resolution_meta.get("noaa_station_id") or resolution_meta.get("noaa_daily_station_id"):
        score += 1
        rationale.append("noaa_station")
    if any(row.get("openmeteo_forecast_max_c") is not None for row in probe_markets):
        score += 1
        rationale.append("probe_openmeteo")
    if audit_summary.get("noaa_rows", 0) > 0 or any(row.get("noaa_observed_max_c") is not None for row in probe_markets):
        score += 1
        rationale.append("observed_data")

    gap_values = [
        abs(float(row.get("forecast_vs_noaa_gap_c")))
        for row in probe_markets
        if row.get("forecast_vs_noaa_gap_c") is not None
    ]
    avg_gap = round(sum(gap_values) / len(gap_values), 2) if gap_values else None

    if score >= 4:
        risk = "low"
    elif score >= 3:
        risk = "medium"
    else:
        risk = "high"

    return {
        "score": score,
        "max_score": 5,
        "risk": risk,
        "avg_probe_gap_c": avg_gap,
        "rationale": rationale,
    }


def get_structural_block_guardrail(city, policy_mode):
    if policy_mode != "blocked":
        return None
    return STRUCTURAL_BLOCK_GUARDRAILS.get(city)


def classify_bottleneck(
    structural_block_guardrail,
    n_reference_traders,
    visible_snapshots,
    settlement_fidelity,
    shadow_summary,
    recent_skip_summary,
    quality_reference_count,
    active_signal_reference_count,
    enrichment_health,
    runtime_policy_mode,
):
    if enrichment_health.get("likely_input_degraded"):
        return "trader_input_degraded"
    if structural_block_guardrail:
        return "source_fidelity"
    if recent_skip_summary.get("useful_policy_gate_count", 0) > 0:
        return "policy_execution_gate"
    if runtime_policy_mode == "auto_canary":
        return "canary_measurement"
    if n_reference_traders < 3:
        return "trader_discovery"
    if quality_reference_count == 0 and active_signal_reference_count == 0:
        return "trader_input_quality"
    if settlement_fidelity["risk"] == "high":
        return "source_fidelity"
    if (
        shadow_summary["edge_hits"] == 0
        and shadow_summary["cycles_seen"] >= 5
        and shadow_summary["markets_seen"] >= 8
    ):
        return "weak_city_hypothesis"
    if visible_snapshots < 2:
        return "market_visibility"
    if shadow_summary["edge_hits"] < bot.SHADOW_CANARY_MIN_EDGE_HITS or shadow_summary["cycles_seen"] < bot.SHADOW_CANARY_MIN_CYCLES:
        return "shadow_validation"
    return "canary_confirmation"


def compute_evidence_status(
    policy_mode,
    n_reference_traders,
    visible_snapshots,
    settlement_fidelity,
    shadow_summary,
    min_reference_traders,
    min_visible_snapshots,
    quality_reference_count,
    active_signal_reference_count,
    enrichment_health,
):
    if enrichment_health.get("likely_input_degraded"):
        return "insufficient"
    if n_reference_traders < min_reference_traders:
        return "insufficient"
    if quality_reference_count == 0 and active_signal_reference_count == 0 and shadow_summary["edge_hits"] == 0:
        return "insufficient"
    if settlement_fidelity["risk"] == "high":
        return "insufficient"
    if visible_snapshots < min_visible_snapshots:
        return "building"
    if (
        shadow_summary["edge_hits"] >= bot.SHADOW_CANARY_MIN_EDGE_HITS
        and shadow_summary["cycles_seen"] >= bot.SHADOW_CANARY_MIN_CYCLES
        and settlement_fidelity["risk"] in {"low", "medium"}
    ):
        return "actionable"
    if policy_mode in {"shadow", "active", "canary"}:
        return "building"
    return "insufficient"


def compute_recommendation(policy_mode, evidence_status, shadow_summary, settlement_fidelity, bottleneck):
    if bottleneck in {"trader_input_degraded", "trader_input_quality"}:
        return "audit_trader_input"
    if bottleneck == "policy_execution_gate":
        return "review_runtime_policy_gate"
    if bottleneck == "canary_measurement":
        return "observe_runtime_canary"
    if bottleneck == "weak_city_hypothesis":
        return "background_watch"
    if evidence_status == "insufficient":
        return "insufficient_evidence"
    if evidence_status == "actionable":
        if policy_mode == "blocked":
            return "review_block_reason"
        if policy_mode == "shadow":
            if shadow_summary["edge_hits"] >= bot.SHADOW_CANARY_MIN_EDGE_HITS:
                return "candidate_for_canary_validation"
            return "shadow_reinforced"
        if policy_mode in {"active", "canary"}:
            return "watch_active_benchmark"
        return "review_policy"
    if settlement_fidelity["risk"] == "medium":
        return "observe_with_source_caution"
    if policy_mode == "shadow":
        return "watch_closely"
    return "observe"


def reconcile_runtime_recommendation(recommendation, runtime_policy_mode, drift_flags):
    if recommendation == "review_runtime_policy_gate":
        return recommendation
    if any(flag in drift_flags for flag in {"policy_divergence", "runtime_policy_collision"}):
        return "audit_runtime_drift"
    if runtime_policy_mode == "auto_canary":
        return "observe_runtime_canary"
    if runtime_policy_mode == "auto_blocked":
        return "observe_runtime_blocked"
    return recommendation


def build_city_row(
    city_row,
    enrichment_lookup,
    probe_by_city,
    tracker_lookup,
    shadow_tracking,
    audit,
    skip_rows,
    min_reference_traders,
    min_visible_snapshots,
    recent_skip_cycles,
    recent_skip_min_edge,
    enrichment_health,
    runtime_policy_lookup,
):
    city = city_row.get("city", "")
    policy_context = build_policy_context(city_row, runtime_policy_lookup)
    policy_mode = policy_context["policy_mode"]
    cross_policy_mode = policy_context["cross_policy_mode"]
    runtime_policy_mode = policy_context["runtime_policy_mode"]
    drift_flags = policy_context["drift_flags"]
    reference_traders = city_row.get("reference_traders", [])
    reference_quality_counts = city_row.get("reference_quality_counts", {})
    tracker_state = tracker_lookup.get(city, {})
    probe_markets = probe_by_city.get(city, [])
    shadow_summary = summarize_shadow_tracking(city, shadow_tracking)
    audit_summary = summarize_audit(city, audit)
    recent_skip_summary = summarize_recent_skip_log(
        city=city,
        skip_rows=skip_rows,
        recent_skip_cycles=recent_skip_cycles,
        recent_skip_min_edge=recent_skip_min_edge,
    )
    resolution_meta = bot.RESOLUTION_ICAO.get(city, {})
    settlement_fidelity = compute_settlement_fidelity(city, resolution_meta, probe_markets, audit_summary)
    structural_block_guardrail = get_structural_block_guardrail(city, policy_mode)

    current_probe_markets = int(city_row.get("current_probe_markets", 0) or 0)
    visible_snapshots = int(tracker_state.get("n_visible_snapshots", 0) or 0)
    comparable_snapshots = int(tracker_state.get("n_comparable_snapshots", 0) or 0)
    n_reference_traders = len(reference_traders)
    high_refs = int(reference_quality_counts.get("high_priority_reference", 0) or 0)
    candidate_refs = int(reference_quality_counts.get("candidate_reference", 0) or 0)
    active_unproven_refs = int(reference_quality_counts.get("active_but_unproven", 0) or 0)
    quality_reference_count = high_refs + candidate_refs

    single_trader_dependency = round(1.0 / n_reference_traders, 2) if n_reference_traders else 1.0

    visibility_score = (
        high_refs * 3
        + candidate_refs
        + current_probe_markets
        + visible_snapshots
        + comparable_snapshots
    )
    edge_score = (
        shadow_summary["edge_hits"] * 3
        + shadow_summary["cycles_seen"] * 2
        + min(12, int(shadow_summary["best_edge_pct"] // 5))
        + min(6, audit_summary["noaa_rows"])
    )

    evidence_status = compute_evidence_status(
        policy_mode=policy_mode,
        n_reference_traders=n_reference_traders,
        visible_snapshots=visible_snapshots,
        settlement_fidelity=settlement_fidelity,
        shadow_summary=shadow_summary,
        min_reference_traders=min_reference_traders,
        min_visible_snapshots=min_visible_snapshots,
        quality_reference_count=quality_reference_count,
        active_signal_reference_count=active_unproven_refs,
        enrichment_health=enrichment_health,
    )
    base_evidence_status = evidence_status
    if cross_policy_mode == "runtime_only":
        evidence_status = "runtime_only"
    bottleneck = classify_bottleneck(
        structural_block_guardrail=structural_block_guardrail,
        n_reference_traders=n_reference_traders,
        visible_snapshots=visible_snapshots,
        settlement_fidelity=settlement_fidelity,
        shadow_summary=shadow_summary,
        recent_skip_summary=recent_skip_summary,
        quality_reference_count=quality_reference_count,
        active_signal_reference_count=active_unproven_refs,
        enrichment_health=enrichment_health,
        runtime_policy_mode=runtime_policy_mode,
    )
    base_recommendation = compute_recommendation(
        policy_mode=policy_mode,
        evidence_status=base_evidence_status,
        shadow_summary=shadow_summary,
        settlement_fidelity=settlement_fidelity,
        bottleneck=bottleneck,
    )
    recommendation = reconcile_runtime_recommendation(
        recommendation=base_recommendation,
        runtime_policy_mode=runtime_policy_mode,
        drift_flags=drift_flags,
    )

    rationale = []
    if n_reference_traders:
        rationale.append(f"{n_reference_traders} reference traders")
    if high_refs:
        rationale.append(f"{high_refs} high-priority refs")
    if candidate_refs:
        rationale.append(f"{candidate_refs} candidate refs")
    if active_unproven_refs:
        rationale.append(f"{active_unproven_refs} active-but-unproven refs")
    if visible_snapshots:
        rationale.append(f"{visible_snapshots} visible snapshots")
    if current_probe_markets:
        rationale.append(f"{current_probe_markets} probe markets now")
    if shadow_summary["edge_hits"]:
        rationale.append(f"{shadow_summary['edge_hits']} shadow edge hits")
    if audit_summary["noaa_rows"]:
        rationale.append(f"{audit_summary['noaa_rows']} NOAA rows")
    if structural_block_guardrail:
        rationale.append(f"blocked guardrail {structural_block_guardrail['reason']}")
    rationale.append(f"source risk {settlement_fidelity['risk']}")

    reference_examples = []
    for label in reference_traders[:5]:
        trader = enrichment_lookup.get(label)
        if not trader:
            continue
        reference_examples.append({
            "trader": label,
            "reference_quality": trader.get("reference_quality", ""),
            "closed_win_rate": trader.get("closed_summary", {}).get("win_rate"),
            "closed_pnl": trader.get("closed_summary", {}).get("total_closed_pnl"),
            "active_directional": trader.get("active_summary", {}).get("n_active_directional"),
        })

    return {
        "city": city,
        "policy_mode": policy_mode,
        "cross_policy_mode": cross_policy_mode,
        "runtime_policy_mode": runtime_policy_mode,
        "runtime_policy_source": policy_context["runtime_policy_source"],
        "runtime_policy_details": policy_context["runtime_policy_details"],
        "runtime_policy_collisions": policy_context["runtime_policy_collisions"],
        "drift_flags": drift_flags,
        "row_kind": city_row.get("row_kind", "cross"),
        "reference_traders": reference_traders,
        "reference_quality_counts": reference_quality_counts,
        "n_reference_traders": n_reference_traders,
        "single_trader_dependency_rate": single_trader_dependency,
        "visibility_evidence": {
            "score": visibility_score,
            "current_probe_markets": current_probe_markets,
            "visible_snapshots": visible_snapshots,
            "comparable_snapshots": comparable_snapshots,
            "last_seen_at": tracker_state.get("last_seen_at"),
        },
        "edge_evidence": {
            "score": edge_score,
            "shadow_edge_hits": shadow_summary["edge_hits"],
            "shadow_cycles_seen": shadow_summary["cycles_seen"],
            "shadow_best_edge_pct": shadow_summary["best_edge_pct"],
            "resolved_directional_count": shadow_summary["resolved_directional_count"],
            "noaa_rows": audit_summary["noaa_rows"],
            "latest_noaa_date": audit_summary["latest_date"],
        },
        "settlement_fidelity": settlement_fidelity,
        "recent_skip_evidence": recent_skip_summary,
        "structural_block_guardrail": structural_block_guardrail,
        "bottleneck": bottleneck,
        "base_evidence_status": base_evidence_status,
        "evidence_status": evidence_status,
        "base_recommendation": base_recommendation,
        "recommendation": recommendation,
        "rationale": "; ".join(rationale),
        "reference_examples": reference_examples,
    }


def render_markdown(payload):
    runtime_status = payload.get("summary", {}).get("runtime_inputs_status", "available")
    if runtime_status in {"missing", "stale"}:
        input_rows = (
            payload.get("summary", {}).get("missing_runtime_inputs", [])
            if runtime_status == "missing"
            else payload.get("summary", {}).get("stale_runtime_inputs", [])
        )
        lines = [
            "# City Validation Ledger",
            "",
            f"- Generated: `{payload['generated_at']}`",
            f"- Runtime inputs status: `{runtime_status}`",
            "- Cities evaluated: `0`",
            "",
            "## Runtime Inputs",
            "",
            "| Input | Path | Reason |",
            "| --- | --- | --- |",
        ]
        for row in input_rows:
            lines.append(f"| {row.get('name')} | `{row.get('path')}` | {row.get('reason', '')} |")
        lines.extend([
            "",
            "## Decision",
            "",
            "`city-intelligence` no tiene runtime fresco del bot. No se puede interpretar `edge_evidence=0` como ausencia real de edge.",
            "",
        ])
        return "\n".join(lines)

    lines = [
        "# City Validation Ledger",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Runtime inputs status: `{runtime_status}`",
        f"- Cities evaluated: `{payload['summary']['n_cities']}`",
        f"- Evidence status counts: `{payload['summary']['evidence_status_counts']}`",
        f"- Recommendation counts: `{payload['summary']['recommendation_counts']}`",
        f"- Bottleneck counts: `{payload['summary']['bottleneck_counts']}`",
        f"- Recent useful skips: `{payload['summary'].get('recent_useful_skip_reason_counts', {})}`",
        "",
        "## Top Cities",
        "",
        "| City | Policy | Runtime policy | Cross policy | Drift | Evidence | Recommendation | Visibility | Edge | Useful skips | Source risk | Bottleneck |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["cities"][:15]:
        lines.append(
            f"| {row['city']} | {row['policy_mode']} | {row.get('runtime_policy_mode')} | "
            f"{row.get('cross_policy_mode')} | {','.join(row.get('drift_flags', [])) or '-'} | "
            f"{row['evidence_status']} | {row['recommendation']} | "
            f"{row['visibility_evidence']['score']} | {row['edge_evidence']['score']} | "
            f"{row.get('recent_skip_evidence', {}).get('useful_reason_counts', {})} | "
            f"{row['settlement_fidelity']['risk']} | {row['bottleneck']} |"
        )

    lines.extend([
        "",
        "## Review Notes",
        "",
    ])
    for row in payload["cities"][:8]:
        lines.append(
            f"- `{row['city']}` -> `{row['recommendation']}` | bottleneck `{row['bottleneck']}` | {row['rationale']}"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    runtime_input_status = build_runtime_input_status(args)
    if runtime_input_status["status"] in {"missing", "stale", "manifest_drift"}:
        payload = build_runtime_missing_payload(args, runtime_input_status)
        json_path = ensure_parent(args.json_output)
        md_path = ensure_parent(args.md_output)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")

        print(f"City validation ledger written to {json_path}")
        print(f"Markdown summary written to {md_path}")
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
        return

    try:
        load_bot_module()
    except Exception as exc:
        runtime_input_status = build_bot_import_failed_status(args, exc)
        payload = build_runtime_missing_payload(args, runtime_input_status)
        json_path = ensure_parent(args.json_output)
        md_path = ensure_parent(args.md_output)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")

        print(f"City validation ledger written to {json_path}")
        print(f"Markdown summary written to {md_path}")
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
        return

    cross = load_json(args.cross, required=True)
    enrichment = load_json(args.enrichment, required=True)
    probe = load_json(args.probe, required=True)
    tracker = load_json(args.tracker, required=False)
    shadow_tracking = load_json(args.shadow_tracking, required=False)
    audit = load_json(args.audit, required=False)
    city_policy_state = load_json(args.city_policy_state, required=False)
    skip_rows = load_jsonl(args.skip_log)

    enrichment_lookup = build_enrichment_lookup(enrichment)
    enrichment_health = summarize_enrichment_health(enrichment)
    probe_by_city = build_probe_by_city(probe)
    tracker_lookup = build_tracker_lookup(tracker)
    runtime_policy_lookup = build_runtime_policy_lookup(city_policy_state)

    rows = []
    cross_city_rows = cross.get("city_rows", [])
    city_rows = list(cross_city_rows) + build_runtime_only_city_rows(
        cross_city_rows,
        runtime_policy_lookup,
    )
    for city_row in city_rows:
        rows.append(
            build_city_row(
                city_row=city_row,
                enrichment_lookup=enrichment_lookup,
                probe_by_city=probe_by_city,
                tracker_lookup=tracker_lookup,
                shadow_tracking=shadow_tracking,
                audit=audit,
                skip_rows=skip_rows,
                min_reference_traders=args.min_reference_traders,
                min_visible_snapshots=args.min_visible_snapshots,
                recent_skip_cycles=args.recent_skip_cycles,
                recent_skip_min_edge=args.recent_skip_min_edge,
                enrichment_health=enrichment_health,
                runtime_policy_lookup=runtime_policy_lookup,
            )
        )

    rows.sort(
        key=lambda row: (
            row["evidence_status"] != "actionable",
            row["evidence_status"] != "building",
            -row["visibility_evidence"]["score"],
            -row["edge_evidence"]["score"],
            row["city"],
        )
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
            "tracker": args.tracker,
            "shadow_tracking": args.shadow_tracking,
            "audit": args.audit,
            "city_policy_state": args.city_policy_state,
            "skip_log": args.skip_log,
            "runtime_manifest": args.runtime_manifest,
        },
        "summary": {
            "n_cities": len(rows),
            "runtime_inputs_status": runtime_input_status["status"],
            "missing_runtime_inputs": [],
            "stale_runtime_inputs": [],
            "manifest_drift_inputs": [],
            "runtime_manifest": runtime_input_status.get("manifest", {}),
            "evidence_status_counts": dict(Counter(row["evidence_status"] for row in rows)),
            "recommendation_counts": dict(Counter(row["recommendation"] for row in rows)),
            "bottleneck_counts": dict(Counter(row["bottleneck"] for row in rows)),
            "recent_useful_skip_reason_counts": dict(
                Counter(
                    reason
                    for row in rows
                    for reason, count in (row.get("recent_skip_evidence", {}).get("useful_reason_counts", {}) or {}).items()
                    for _ in range(int(count))
                )
            ),
            "drift_flag_counts": dict(Counter(flag for row in rows for flag in row.get("drift_flags", []))),
            "runtime_policy_mode_counts": dict(Counter(row["runtime_policy_mode"] for row in rows)),
            "enrichment_health": enrichment_health,
        },
        "cities": rows,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"City validation ledger written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
