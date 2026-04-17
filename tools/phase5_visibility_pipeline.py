#!/usr/bin/env python3
"""Orchestrate the phase-5 visibility workflow in one read-only command."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "phase5_visibility_pipeline.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "phase5_visibility_pipeline_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta en cadena la fase 5 read-only: "
            "settlement probe opcional, tracker de visibilidad, snapshots de Shanghai/Chicago y comparador."
        )
    )
    parser.add_argument(
        "--refresh-probe",
        action="store_true",
        help="Si se activa, regenera settlement_fidelity_probe.json antes del resto.",
    )
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=12,
        help="Limite para settlement_fidelity_probe.py cuando se usa --refresh-probe.",
    )
    parser.add_argument("--targets", default="Shanghai,Chicago")
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


def render_markdown(payload):
    lines = [
        "# Phase 5 Visibility Pipeline",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Refresh probe: `{payload['refresh_probe']}`",
        f"- Overall status: `{payload['overall_status']}`",
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
            f"- Latest probe tracked: `{summary.get('latest_probe_generated_at')}`",
            f"- Visibility snapshots tracked: `{summary.get('visibility_snapshots')}`",
        f"- Simultaneous visibility count: `{summary.get('simultaneous_visibility_count')}`",
        f"- Shanghai next action: `{summary.get('shanghai_next_action')}`",
        f"- Chicago benchmark next action: `{summary.get('chicago_next_action')}`",
        f"- Dominant gap: `{summary.get('dominant_gap')}`",
        f"- Comparator recommendation: `{summary.get('comparator_next_step')}`",
        f"- Operational severity: `{summary.get('operational_severity')}`",
        f"- Operational action state: `{summary.get('operational_action_state')}`",
        f"- Operational next step: `{summary.get('operational_next_step')}`",
        "",
    ])
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    python_exe = sys.executable
    steps = []

    if args.refresh_probe:
        steps.append(
            run_step(
                "settlement_fidelity_probe",
                [python_exe, str(TOOLS_DIR / "settlement_fidelity_probe.py"), "--limit", str(args.probe_limit)],
            )
        )

    steps.append(
        run_step(
            "city_probe_visibility_tracker",
            [python_exe, str(TOOLS_DIR / "city_probe_visibility_tracker.py"), "--targets", args.targets],
        )
    )
    steps.append(
        run_step(
            "shanghai_shadow_test",
            [python_exe, str(TOOLS_DIR / "shanghai_shadow_test.py")],
        )
    )
    steps.append(
        run_step(
            "chicago_active_benchmark",
            [python_exe, str(TOOLS_DIR / "chicago_active_benchmark.py")],
        )
    )
    steps.append(
        run_step(
            "shanghai_vs_chicago_comparator",
            [python_exe, str(TOOLS_DIR / "shanghai_vs_chicago_comparator.py")],
        )
    )
    steps.append(
        run_step(
            "phase5_operational_action",
            [python_exe, str(TOOLS_DIR / "phase5_operational_action.py")],
        )
    )
    steps.append(
        run_step(
            "phase5_visibility_telegram_alert",
            [python_exe, str(TOOLS_DIR / "phase5_visibility_telegram_alert.py")],
        )
    )

    overall_status = "ok" if all(step["ok"] for step in steps) else "partial_failure"
    summary = {}
    if overall_status == "ok":
        tracker = load_json(REPO_ROOT / "data" / "city_probe_visibility_tracker.json")
        shanghai = load_json(REPO_ROOT / "data" / "shanghai_shadow_test.json")
        chicago = load_json(REPO_ROOT / "data" / "chicago_active_benchmark.json")
        comparator = load_json(REPO_ROOT / "data" / "shanghai_vs_chicago_comparator.json")
        operational_action = load_json(REPO_ROOT / "data" / "phase5_operational_action.json")
        alert_state = load_json(REPO_ROOT / "data" / "phase5_visibility_alert_state.json")
        summary = {
            "latest_probe_generated_at": tracker.get("summary", {}).get("latest_probe_generated_at"),
            "visibility_snapshots": tracker.get("summary", {}).get("n_snapshots"),
            "simultaneous_visibility_count": tracker.get("summary", {}).get("simultaneous_visibility_count"),
            "shanghai_next_action": shanghai.get("assessment", {}).get("next_action"),
            "chicago_next_action": chicago.get("benchmark_assessment", {}).get("next_action"),
            "dominant_gap": comparator.get("gap", {}).get("dominant_gap"),
            "comparator_next_step": comparator.get("recommendation", {}).get("next_step"),
            "operational_severity": operational_action.get("action", {}).get("severity"),
            "operational_action_state": operational_action.get("action", {}).get("action_state"),
            "operational_next_step": operational_action.get("action", {}).get("next_operational_step"),
            "last_simultaneous_alert_probe_generated_at": alert_state.get("last_simultaneous_alert_probe_generated_at"),
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "refresh_probe": args.refresh_probe,
        "targets": args.targets,
        "steps": steps,
        "overall_status": overall_status,
        "summary": summary,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Phase-5 pipeline written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps({"overall_status": overall_status, "summary": summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
