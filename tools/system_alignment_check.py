#!/usr/bin/env python3
"""Read-only preflight for system alignment before operational decisions."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "data" / "runtime_import"
DEFAULT_RUNTIME_MANIFEST = DEFAULT_RUNTIME_DIR / "runtime_import_manifest.json"
DEFAULT_EFFECTIVE_VIEW = REPO_ROOT / "data" / "runtime_policy_effective_view.json"
DEFAULT_EFFECTIVE_VIEW_DOC = REPO_ROOT / "docs" / "runtime_policy_effective_view_latest.md"
DEFAULT_METRICS_DOC = REPO_ROOT / "docs" / "metrics-funnel-naming.md"
DEFAULT_COUNTER_CONTRACT_DOC = REPO_ROOT / "docs" / "bot-funnel-counter-contract-2026-04-11.md"
DEFAULT_DECISION_RULES_DOC = REPO_ROOT / "docs" / "decision-preflight-rules-2026-04-11.md"
DEFAULT_LEDGER = REPO_ROOT / "data" / "runtime_import_derived" / "city_validation_ledger.runtime_import.json"
DEFAULT_PIPELINE = REPO_ROOT / "data" / "city_intelligence_pipeline.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "system_alignment_check.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "system_alignment_check_latest.md"
DEFAULT_OPERATIONAL_JSON_OUTPUT = REPO_ROOT / "data" / "system_alignment_check_operational.json"
DEFAULT_OPERATIONAL_MD_OUTPUT = REPO_ROOT / "docs" / "system_alignment_check_operational_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate read-only alignment contracts before operational decisions."
    )
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--runtime-manifest", default=str(DEFAULT_RUNTIME_MANIFEST))
    parser.add_argument("--effective-view", default=str(DEFAULT_EFFECTIVE_VIEW))
    parser.add_argument("--effective-view-doc", default=str(DEFAULT_EFFECTIVE_VIEW_DOC))
    parser.add_argument("--metrics-doc", default=str(DEFAULT_METRICS_DOC))
    parser.add_argument("--counter-contract-doc", default=str(DEFAULT_COUNTER_CONTRACT_DOC))
    parser.add_argument("--decision-rules-doc", default=str(DEFAULT_DECISION_RULES_DOC))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--decision-mode", choices=("observe", "operational"), default="observe")
    parser.add_argument("--max-runtime-snapshot-age-hours", type=float, default=24.0)
    parser.add_argument("--max-effective-view-age-hours", type=float, default=24.0)
    parser.add_argument("--operational-effective-view-max-age-hours", type=float, default=6.0)
    parser.add_argument("--operational-max-collision-count", type=int, default=5)
    parser.add_argument("--operational-max-blocking-collision-count", type=int, default=0)
    parser.add_argument("--operational-max-documented-drift-count", type=int, default=999)
    return parser.parse_args()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def parse_utc(value):
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


def age_hours(value):
    return (datetime.now(timezone.utc) - parse_utc(value)).total_seconds() / 3600


def result(name, status, message, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def doc_relpath(path):
    return str(Path(path).resolve().relative_to(REPO_ROOT))


def canonical_prompt_docs():
    patterns = [
        "claude-opus-prompt-*.md",
        "system-alignment-*.md",
        "next-session-handoff-*.md",
    ]
    seen = set()
    docs = []
    docs_dir = REPO_ROOT / "docs"
    for pattern in patterns:
        for path in sorted(docs_dir.glob(pattern)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            docs.append(path)
    return docs


def resolve_output_paths(args):
    json_output = Path(args.json_output)
    md_output = Path(args.md_output)
    if args.decision_mode == "operational":
        if json_output.resolve() == DEFAULT_JSON_OUTPUT.resolve():
            json_output = DEFAULT_OPERATIONAL_JSON_OUTPUT
        if md_output.resolve() == DEFAULT_MD_OUTPUT.resolve():
            md_output = DEFAULT_OPERATIONAL_MD_OUTPUT
    return json_output, md_output


def check_manifest(args):
    manifest_path = Path(args.runtime_manifest)
    runtime_dir = Path(args.runtime_dir)
    if not manifest_path.exists():
        return result("runtime_manifest", "error", "runtime manifest missing", {"path": str(manifest_path)})
    if not runtime_dir.exists():
        return result("runtime_manifest", "error", "runtime directory missing", {"path": str(runtime_dir)})

    try:
        manifest = load_json(manifest_path)
        files = manifest.get("files", [])
        if not isinstance(files, list):
            return result("runtime_manifest", "error", "manifest.files is not a list")
        expected = {item.get("name") for item in files if isinstance(item, dict)}
        expected.discard(None)
        actual = {item.name for item in runtime_dir.iterdir() if item.is_file() and item.name != manifest_path.name}
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        byte_mismatch = []
        for item in files:
            if not isinstance(item, dict) or item.get("name") not in actual:
                continue
            expected_bytes = item.get("bytes")
            if expected_bytes is not None:
                actual_bytes = (runtime_dir / item["name"]).stat().st_size
                if int(expected_bytes) != actual_bytes:
                    byte_mismatch.append({
                        "name": item["name"],
                        "manifest_bytes": int(expected_bytes),
                        "actual_bytes": actual_bytes,
                    })
        pulled_at = manifest.get("pulled_at")
        runtime_age = age_hours(pulled_at)
    except Exception as exc:
        return result("runtime_manifest", "error", "runtime manifest cannot be validated", {"error": f"{type(exc).__name__}: {exc}"})

    details = {
        "manifest_file_count": len(expected),
        "disk_file_count": len(actual),
        "missing": missing,
        "extra": extra,
        "byte_mismatch": byte_mismatch,
        "pulled_at": pulled_at,
        "age_hours": round(runtime_age, 2),
    }
    if missing or extra or byte_mismatch:
        return result("runtime_manifest", "error", "runtime manifest is not bijective", details)
    if runtime_age > float(args.max_runtime_snapshot_age_hours):
        return result("runtime_manifest", "error", "runtime snapshot is stale", details)
    return result("runtime_manifest", "ok", "runtime manifest is bijective and fresh", details)


def check_effective_view(args):
    view_path = Path(args.effective_view)
    doc_path = Path(args.effective_view_doc)
    if not view_path.exists():
        return result("runtime_policy_effective_view", "error", "effective view JSON missing", {"path": str(view_path)})
    try:
        payload = load_json(view_path)
        generated_at = payload.get("generated_at")
        view_age = age_hours(generated_at)
        rows = payload.get("cities", [])
        summary = payload.get("summary", {})
    except Exception as exc:
        return result("runtime_policy_effective_view", "error", "effective view cannot be parsed", {"error": f"{type(exc).__name__}: {exc}"})

    missing_fields = []
    required = {
        "city",
        "env_declared_mode",
        "runtime_policy_mode",
        "effective_mode",
        "collision_flag",
        "source_of_truth",
        "rationale",
    }
    for row in rows:
        missing = sorted(required - set(row))
        if missing:
            missing_fields.append({"city": row.get("city", "unknown"), "missing": missing})
    details = {
        "generated_at": generated_at,
        "age_hours": round(view_age, 2),
        "decision_mode": args.decision_mode,
        "operational_age_slo_hours": float(args.operational_effective_view_max_age_hours),
        "operational_max_collision_count": int(args.operational_max_collision_count),
        "operational_max_blocking_collision_count": int(args.operational_max_blocking_collision_count),
        "operational_max_documented_drift_count": int(args.operational_max_documented_drift_count),
        "n_cities": len(rows),
        "effective_mode_counts": summary.get("effective_mode_counts", {}),
        "collision_count": summary.get("collision_count", 0),
        "collision_category_counts": summary.get("collision_category_counts", {}),
        "blocking_operational_collision_count": summary.get("blocking_operational_collision_count", 0),
        "active_effective_count": summary.get("active_effective_count", 0),
        "missing_fields": missing_fields,
    }
    if view_age > float(args.max_effective_view_age_hours):
        return result("runtime_policy_effective_view", "error", "effective view is stale", details)
    if missing_fields:
        return result("runtime_policy_effective_view", "error", "effective view rows miss required fields", details)
    if not doc_path.exists():
        return result("runtime_policy_effective_view", "warning", "effective view JSON exists but markdown doc is missing", details)
    if doc_path.stat().st_mtime < view_path.stat().st_mtime:
        return result("runtime_policy_effective_view", "warning", "effective view markdown is older than JSON", details)
    collision_count = int(summary.get("collision_count", 0) or 0)
    blocking_collision_count = int(summary.get("blocking_operational_collision_count", 0) or 0)
    documented_drift_count = int((summary.get("collision_category_counts", {}) or {}).get("documented_drift", 0) or 0)
    if args.decision_mode == "operational" and view_age > float(args.operational_effective_view_max_age_hours):
        return result("runtime_policy_effective_view", "error", "effective view exceeds operational freshness SLO", details)
    if args.decision_mode == "operational" and blocking_collision_count > int(args.operational_max_blocking_collision_count):
        return result("runtime_policy_effective_view", "error", "blocking_operational_collision_count exceeds operational threshold", details)
    if args.decision_mode == "operational" and documented_drift_count > int(args.operational_max_documented_drift_count):
        return result("runtime_policy_effective_view", "error", "documented_drift count exceeds operational threshold", details)
    if collision_count > 0:
        return result("runtime_policy_effective_view", "warning", "policy collisions/divergences are explicitly listed", details)
    return result("runtime_policy_effective_view", "ok", "effective view exists and is fresh", details)


def check_ledger(args):
    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        return result("runtime_ledger", "warning", "runtime-import ledger is missing; run ledger against data/runtime_import before decisions", {"path": str(ledger_path)})
    try:
        ledger = load_json(ledger_path)
        summary = ledger.get("summary", {})
    except Exception as exc:
        return result("runtime_ledger", "error", "runtime-import ledger cannot be parsed", {"error": f"{type(exc).__name__}: {exc}"})
    details = {
        "runtime_inputs_status": summary.get("runtime_inputs_status"),
        "drift_flag_counts": summary.get("drift_flag_counts", {}),
        "runtime_policy_mode_counts": summary.get("runtime_policy_mode_counts", {}),
    }
    if summary.get("runtime_inputs_status") != "available":
        return result("runtime_ledger", "error", "runtime-import ledger does not have available runtime inputs", details)
    if summary.get("drift_flag_counts"):
        return result("runtime_ledger", "warning", "cross/runtime divergences are present and explicit", details)
    return result("runtime_ledger", "ok", "runtime-import ledger is available", details)


def check_metrics_doc(args):
    path = Path(args.metrics_doc)
    _, md_output = resolve_output_paths(args)
    md_output_path = md_output.resolve()
    if not path.exists():
        return result("metrics_funnel_naming", "error", "metrics naming contract missing", {"path": str(path)})
    text = path.read_text(encoding="utf-8")
    required_terms = [
        "raw_markets_fetched",
        "candidates_after_prefilters",
        "markets_evaluated",
        "condition_filtered_out",
        "shadow_opportunities_observed",
        "trades_executed",
    ]
    missing = [term for term in required_terms if term not in text]
    if missing:
        return result("metrics_funnel_naming", "error", "metrics naming contract misses required terms", {"missing": missing})

    ambiguous_docs = []
    for doc in (REPO_ROOT / "docs").glob("*.md"):
        if doc.resolve() == md_output_path:
            continue
        doc_text = doc.read_text(encoding="utf-8", errors="replace")
        if "markets_evaluated" in doc_text and "candidates_after_prefilters" not in doc_text:
            ambiguous_docs.append(str(doc.relative_to(REPO_ROOT)))
    status = "warning" if ambiguous_docs else "ok"
    message = (
        "legacy markets_evaluated mentions remain without canonical alias candidates_after_prefilters"
        if ambiguous_docs
        else "metrics naming contract is present"
    )
    return result("metrics_funnel_naming", status, message, {"ambiguous_docs": ambiguous_docs[:30], "ambiguous_docs_count": len(ambiguous_docs)})


def check_targets(args):
    pipeline_path = Path(args.pipeline)
    if not pipeline_path.exists():
        return result("city_intelligence_targets", "warning", "pipeline JSON missing; cannot inspect targets", {"path": str(pipeline_path)})
    try:
        pipeline = load_json(pipeline_path)
    except Exception as exc:
        return result("city_intelligence_targets", "warning", "pipeline JSON cannot be parsed", {"error": f"{type(exc).__name__}: {exc}"})
    tracker_targets = pipeline.get("tracker_targets")
    if tracker_targets and isinstance(tracker_targets, str):
        return result(
            "city_intelligence_targets",
            "warning",
            "city-intelligence tracker targets are still a flat string, not runtime-derived/exploratory tagged",
            {"tracker_targets": tracker_targets},
        )
    runtime_derived_targets = pipeline.get("runtime_derived_targets")
    exploratory_targets = pipeline.get("exploratory_targets")
    details = {
        "runtime_derived_targets": runtime_derived_targets,
        "exploratory_targets": exploratory_targets,
        "tracker_targets": tracker_targets,
    }
    if not isinstance(runtime_derived_targets, list) or not isinstance(exploratory_targets, list) or not isinstance(tracker_targets, list):
        return result(
            "city_intelligence_targets",
            "warning",
            "city-intelligence targets are not yet exposed as explicit runtime-derived/exploratory lists",
            details,
        )
    runtime_keys = {str(city).casefold() for city in runtime_derived_targets}
    overlap_targets = [city for city in exploratory_targets if str(city).casefold() in runtime_keys]
    details["overlap_targets"] = overlap_targets
    if overlap_targets:
        return result(
            "city_intelligence_targets",
            "warning",
            "city-intelligence target tags overlap between runtime-derived and exploratory lists",
            details,
        )
    return result("city_intelligence_targets", "ok", "city-intelligence targets are explicitly tagged", details)


def check_prompt_semantics(args):
    active_truth_docs = []
    ambiguous_funnel_docs = []
    scanned_docs = []
    for doc in canonical_prompt_docs():
        text = doc.read_text(encoding="utf-8", errors="replace")
        scanned_docs.append(doc_relpath(doc))
        if "ACTIVE_TRADING_CITIES" in text and "effective_mode" not in text and "runtime_policy_effective_view" not in text:
            active_truth_docs.append(doc_relpath(doc))
        if "markets_evaluated" in text and "candidates_after_prefilters" not in text:
            ambiguous_funnel_docs.append(doc_relpath(doc))
    details = {
        "scanned_docs": scanned_docs,
        "active_truth_docs": active_truth_docs,
        "ambiguous_funnel_docs": ambiguous_funnel_docs,
    }
    if active_truth_docs or ambiguous_funnel_docs:
        return result(
            "prompt_semantic_scan",
            "warning",
            "canonical prompts/docs still contain policy or funnel wording that can drift from the runtime contract",
            details,
        )
    return result("prompt_semantic_scan", "ok", "canonical prompts/docs respect effective-mode and funnel wording contracts", details)


def check_counter_contract(args):
    path = Path(args.counter_contract_doc)
    if not path.exists():
        return result("bot_funnel_counter_contract", "error", "bot funnel counter contract doc missing", {"path": str(path)})
    text = path.read_text(encoding="utf-8", errors="replace")
    required_terms = [
        "bot.py",
        "raw_markets_fetched",
        "MERCADOS:",
        "markets_evaluated",
        "candidates_after_prefilters",
        "with_edge",
        "candidates_with_edge",
        "selected",
        "candidates_selected",
        "buys_real",
        "trades_executed",
        "shadow",
        "shadow_opportunities_observed",
        "condition_filtered",
        "condition_filtered_out",
        "blocked_city",
        "blocked_city_count",
        "fuera_allowlist",
        "fuera_allowlist_count",
        "timezone_filter",
        "date_out_of_range_past",
        "date_out_of_range_future",
        "price_out_of_range",
    ]
    missing = [term for term in required_terms if term not in text]
    if missing:
        return result(
            "bot_funnel_counter_contract",
            "error",
            "bot funnel counter contract misses required mappings",
            {"path": str(path), "missing": missing},
        )
    return result(
        "bot_funnel_counter_contract",
        "ok",
        "bot funnel counter contract is documented",
        {"path": str(path.relative_to(REPO_ROOT))},
    )


def check_decision_rules(args):
    path = Path(args.decision_rules_doc)
    if not path.exists():
        return result("decision_preflight_rules", "error", "decision preflight rules doc missing", {"path": str(path)})
    text = path.read_text(encoding="utf-8", errors="replace")
    required_terms = [
        "collision_count",
        "blocking_operational_collision",
        "< 20",
        "effective view",
        "operational",
        "observe",
        "PnL",
    ]
    missing = [term for term in required_terms if term not in text]
    if missing:
        return result(
            "decision_preflight_rules",
            "error",
            "decision preflight rules doc misses required guardrails",
            {"path": str(path), "missing": missing},
        )
    return result(
        "decision_preflight_rules",
        "ok",
        "decision preflight guardrails are documented",
        {"path": str(path.relative_to(REPO_ROOT)), "decision_mode": args.decision_mode},
    )


def render_markdown(payload):
    lines = [
        "# System Alignment Check",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Decision mode: `{payload['decision_mode']}`",
        f"- Summary: `{payload['summary']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Message |",
        "| --- | --- | --- |",
    ]
    for item in payload["checks"]:
        lines.append(f"| {item['name']} | {item['status']} | {item['message']} |")
    lines.append("")

    warnings = [item for item in payload["checks"] if item["status"] == "warning"]
    errors = [item for item in payload["checks"] if item["status"] == "error"]
    if errors:
        lines.extend(["## Errors", ""])
        for item in errors:
            lines.append(f"- `{item['name']}`: {item['message']} `{item.get('details', {})}`")
        lines.append("")
    if warnings:
        lines.extend(["## Warnings", ""])
        for item in warnings:
            lines.append(f"- `{item['name']}`: {item['message']} `{item.get('details', {})}`")
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    json_path, md_path = resolve_output_paths(args)
    checks = [
        check_manifest(args),
        check_effective_view(args),
        check_ledger(args),
        check_metrics_doc(args),
        check_targets(args),
        check_prompt_semantics(args),
        check_counter_contract(args),
        check_decision_rules(args),
    ]
    counts = {
        "ok": sum(1 for item in checks if item["status"] == "ok"),
        "warning": sum(1 for item in checks if item["status"] == "warning"),
        "error": sum(1 for item in checks if item["status"] == "error"),
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "decision_mode": args.decision_mode,
        "summary": counts,
        "checks": checks,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
