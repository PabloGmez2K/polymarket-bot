#!/usr/bin/env python3
"""Orchestrate trader discovery, city validation, promotion gate and Telegram alerts."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_EFFECTIVE_VIEW = REPO_ROOT / "data" / "runtime_policy_effective_view.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_intelligence_pipeline.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_intelligence_pipeline_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline funcional de city intelligence: traders -> cross -> ledger -> gate -> alert."
        )
    )
    parser.add_argument("--refresh-probe", action="store_true")
    parser.add_argument("--refresh-census", action="store_true")
    parser.add_argument("--probe-limit", type=int, default=12)
    parser.add_argument("--census-markets", type=int, default=200)
    parser.add_argument("--effective-view", default=str(DEFAULT_EFFECTIVE_VIEW))
    parser.add_argument("--exploratory-targets", default="Chicago")
    parser.add_argument("--tracker-targets", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--telegram-dry-run", action="store_true")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_step(step_name, command):
    proc = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "step": step_name,
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0,
    }


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_targets(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        items = str(raw).split(",")
    targets = []
    seen = set()
    for item in items:
        city = str(item).strip()
        if not city:
            continue
        key = city.casefold()
        if key in seen:
            continue
        seen.add(key)
        targets.append(city)
    return targets


def load_runtime_derived_targets(path_str):
    path = Path(path_str)
    if not path.exists():
        return []
    try:
        payload = load_json(path)
    except Exception:
        return []
    rows = payload.get("cities", [])
    return normalize_targets(
        [row.get("city") for row in rows if row.get("effective_mode") in {"canary", "active"}]
    )


def build_target_contract(args):
    runtime_derived_targets = load_runtime_derived_targets(args.effective_view)
    exploratory_source = args.exploratory_targets
    if args.tracker_targets and not exploratory_source:
        exploratory_source = args.tracker_targets
    exploratory_targets = normalize_targets(exploratory_source)

    runtime_keys = {city.casefold() for city in runtime_derived_targets}
    overlap_targets = [city for city in exploratory_targets if city.casefold() in runtime_keys]
    exploratory_targets = [city for city in exploratory_targets if city.casefold() not in runtime_keys]
    tracker_targets = normalize_targets(runtime_derived_targets + exploratory_targets)
    return {
        "effective_view_path": str(Path(args.effective_view)),
        "runtime_derived_targets": runtime_derived_targets,
        "exploratory_targets": exploratory_targets,
        "overlap_targets": overlap_targets,
        "tracker_targets": tracker_targets,
        "tracker_targets_csv": ",".join(tracker_targets),
    }


def compute_signal_health(enrichment, ledger, gate):
    if ledger.get("summary", {}).get("runtime_inputs_status") == "missing":
        return {
            "status": "runtime_inputs_missing",
            "warning": "city-intelligence no tiene acceso a los artefactos runtime del bot.",
            "quality_reference_traders": 0,
            "active_directional_traders": 0,
            "traders_with_closed_positions": 0,
            "traders_with_active_positions": 0,
            "low_signal_traders": 0,
        }
    if ledger.get("summary", {}).get("runtime_inputs_status") == "stale":
        return {
            "status": "runtime_inputs_stale",
            "warning": "city-intelligence tiene un snapshot runtime obsoleto o sin manifest fresco.",
            "quality_reference_traders": 0,
            "active_directional_traders": 0,
            "traders_with_closed_positions": 0,
            "traders_with_active_positions": 0,
            "low_signal_traders": 0,
        }
    if ledger.get("summary", {}).get("runtime_inputs_status") == "manifest_drift":
        return {
            "status": "runtime_inputs_manifest_drift",
            "warning": "city-intelligence tiene drift entre manifest runtime y archivos locales.",
            "quality_reference_traders": 0,
            "active_directional_traders": 0,
            "traders_with_closed_positions": 0,
            "traders_with_active_positions": 0,
            "low_signal_traders": 0,
        }

    enrichment_summary = enrichment.get("summary", {}) if isinstance(enrichment, dict) else {}
    quality_reference_traders = int(enrichment_summary.get("quality_reference_traders", 0) or 0)
    active_directional_traders = int(enrichment_summary.get("active_directional_traders", 0) or 0)
    traders_with_closed_positions = int(enrichment_summary.get("traders_with_closed_positions", 0) or 0)
    traders_with_active_positions = int(enrichment_summary.get("traders_with_active_positions", 0) or 0)
    low_signal_traders = int((enrichment_summary.get("reference_quality_counts", {}) or {}).get("low_signal", 0) or 0)
    likely_input_degraded = bool(enrichment_summary.get("likely_input_degraded", False))

    if likely_input_degraded:
        status = "input_degraded"
        warning = "Trader enrichment devolvio cero actividad/cierres para toda la shortlist."
    elif quality_reference_traders == 0:
        status = "low_signal"
        warning = "No hay reference traders con senal util en esta corrida."
    else:
        status = "usable_signal"
        warning = ""

    return {
        "status": status,
        "warning": warning,
        "quality_reference_traders": quality_reference_traders,
        "active_directional_traders": active_directional_traders,
        "traders_with_closed_positions": traders_with_closed_positions,
        "traders_with_active_positions": traders_with_active_positions,
        "low_signal_traders": low_signal_traders,
    }


def render_markdown(payload):
    target_contract = payload.get("target_contract", {})
    lines = [
        "# City Intelligence Pipeline",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Overall status: `{payload['overall_status']}`",
        f"- Runtime-derived targets: `{', '.join(target_contract.get('runtime_derived_targets', []))}`",
        f"- Exploratory targets: `{', '.join(target_contract.get('exploratory_targets', []))}`",
        f"- Tracker targets: `{', '.join(target_contract.get('tracker_targets', []))}`",
        "",
        "## Steps",
        "",
        "| Step | OK | Return code |",
        "| --- | --- | --- |",
    ]
    for step in payload["steps"]:
        lines.append(f"| {step['step']} | {step['ok']} | {step['returncode']} |")

    summary = payload.get("summary", {})
    if summary:
        lines.extend([
            "",
            "## Summary",
            "",
            f"- Dominant bottleneck: `{summary.get('dominant_bottleneck')}`",
            f"- Runtime inputs status: `{summary.get('runtime_inputs_status')}`",
            f"- Review queue size: `{summary.get('review_queue_size')}`",
            f"- Top now-city: `{summary.get('top_now_city')}`",
            f"- Top now-instruction: `{summary.get('top_now_instruction')}`",
            f"- Actionable cities: `{summary.get('actionable_cities')}`",
            f"- Building cities: `{summary.get('building_cities')}`",
            f"- Insufficient cities: `{summary.get('insufficient_cities')}`",
            f"- Signal health: `{summary.get('signal_health')}`",
            f"- Quality references: `{summary.get('quality_reference_traders')}`",
            f"- Trader input warning: `{summary.get('trader_input_warning')}`",
            "",
        ])
    return "\n".join(lines) + "\n"


def collect_failed_steps(steps):
    return [step["step"] for step in steps if not step.get("ok")]


def collect_missing_outputs():
    expected_outputs = {
        "directional_trader_enrichment": REPO_ROOT / "data" / "directional_trader_enrichment.json",
        "reference_trader_city_market_cross": REPO_ROOT / "data" / "reference_trader_city_market_cross.json",
        "city_probe_visibility_tracker": REPO_ROOT / "data" / "city_probe_visibility_tracker.json",
        "city_validation_ledger": REPO_ROOT / "data" / "city_validation_ledger.json",
        "city_promotion_gate": REPO_ROOT / "data" / "city_promotion_gate.json",
    }
    missing = []
    for step_name, path in expected_outputs.items():
        if not path.exists():
            missing.append({"step": step_name, "path": str(path)})
    return missing


def main():
    args = parse_args()
    python_exe = sys.executable
    steps = []
    target_contract = build_target_contract(args)

    if args.refresh_probe:
        steps.append(
            run_step(
                "settlement_fidelity_probe",
                [python_exe, str(TOOLS_DIR / "settlement_fidelity_probe.py"), "--limit", str(args.probe_limit)],
            )
        )
    if args.refresh_census:
        steps.append(
            run_step(
                "directional_trader_census",
                [python_exe, str(TOOLS_DIR / "directional_trader_census.py"), "--markets", str(args.census_markets)],
            )
        )

    steps.append(run_step("directional_trader_enrichment", [python_exe, str(TOOLS_DIR / "directional_trader_enrichment.py")]))
    steps.append(run_step("reference_trader_city_market_cross", [python_exe, str(TOOLS_DIR / "reference_trader_city_market_cross.py")]))
    steps.append(
        run_step(
            "city_probe_visibility_tracker",
            [
                python_exe,
                str(TOOLS_DIR / "city_probe_visibility_tracker.py"),
                "--targets",
                target_contract["tracker_targets_csv"],
            ],
        )
    )
    steps.append(run_step("city_validation_ledger", [python_exe, str(TOOLS_DIR / "city_validation_ledger.py")]))
    steps.append(run_step("city_promotion_gate", [python_exe, str(TOOLS_DIR / "city_promotion_gate.py")]))

    alert_command = [python_exe, str(TOOLS_DIR / "city_intelligence_telegram_alert.py")]
    if args.telegram_dry_run:
        alert_command.append("--dry-run")
    steps.append(run_step("city_intelligence_telegram_alert", alert_command))

    failed_steps = collect_failed_steps(steps)
    missing_outputs = collect_missing_outputs()
    overall_status = "ok" if not failed_steps and not missing_outputs else "partial_failure"
    summary = {}
    try:
        enrichment = load_json(REPO_ROOT / "data" / "directional_trader_enrichment.json")
        ledger = load_json(REPO_ROOT / "data" / "city_validation_ledger.json")
        gate = load_json(REPO_ROOT / "data" / "city_promotion_gate.json")
        signal_health = compute_signal_health(enrichment, ledger, gate)
        now_rows = [row for row in gate.get("review_queue", []) if row.get("review_priority") == "now"]
        summary = {
            "dominant_bottleneck": gate.get("summary", {}).get("dominant_bottleneck"),
            "runtime_inputs_status": ledger.get("summary", {}).get("runtime_inputs_status", "available"),
            "missing_runtime_inputs": ledger.get("summary", {}).get("missing_runtime_inputs", []),
            "stale_runtime_inputs": ledger.get("summary", {}).get("stale_runtime_inputs", []),
            "manifest_drift_inputs": ledger.get("summary", {}).get("manifest_drift_inputs", []),
            "runtime_manifest": ledger.get("summary", {}).get("runtime_manifest", {}),
            "review_queue_size": len(gate.get("review_queue", [])),
            "top_now_city": now_rows[0]["city"] if now_rows else "",
            "top_now_instruction": now_rows[0]["codex_instruction"] if now_rows else "",
            "actionable_cities": ledger.get("summary", {}).get("evidence_status_counts", {}).get("actionable", 0),
            "building_cities": ledger.get("summary", {}).get("evidence_status_counts", {}).get("building", 0),
            "insufficient_cities": ledger.get("summary", {}).get("evidence_status_counts", {}).get("insufficient", 0),
            "signal_health": signal_health.get("status"),
            "quality_reference_traders": signal_health.get("quality_reference_traders"),
            "trader_input_warning": signal_health.get("warning"),
        }
        if signal_health.get("status") == "runtime_inputs_missing":
            overall_status = "runtime_inputs_missing"
        elif signal_health.get("status") == "runtime_inputs_stale":
            overall_status = "runtime_inputs_stale"
        elif signal_health.get("status") == "runtime_inputs_manifest_drift":
            overall_status = "runtime_inputs_manifest_drift"
        elif overall_status == "ok" and signal_health.get("status") in {"input_degraded", "low_signal"}:
            overall_status = "signal_degraded"
    except FileNotFoundError:
        summary = {}

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "refresh_probe": args.refresh_probe,
        "refresh_census": args.refresh_census,
        "target_contract": target_contract,
        "runtime_derived_targets": target_contract["runtime_derived_targets"],
        "exploratory_targets": target_contract["exploratory_targets"],
        "tracker_targets": target_contract["tracker_targets"],
        "steps": steps,
        "failed_steps": failed_steps,
        "missing_outputs": missing_outputs,
        "overall_status": overall_status,
        "summary": summary,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    result_summary = {"overall_status": overall_status, "summary": summary}
    if failed_steps:
        result_summary["failed_steps"] = failed_steps
    if missing_outputs:
        result_summary["missing_outputs"] = missing_outputs

    print(f"City intelligence pipeline written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(result_summary, indent=2, ensure_ascii=False))
    sys.exit(1 if failed_steps or missing_outputs else 0)


if __name__ == "__main__":
    main()
