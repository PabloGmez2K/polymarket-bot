#!/usr/bin/env python3
"""Manual Visual Crossing backfill runner for METAR resolution verification.

LOG_ONLY Railway/manual tool. This does not authorize trading, scheduler,
digest hooks, Telegram runtime alerts, env vars, DB writes, source switches,
city mode changes, BANKROLL, Fase C, Truth Pipeline, whitelist, or
BUY/SELL/SKIP behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import metar_resolution_verify as verifier
import visual_crossing_historical_fetch as vc_fetch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_BUDGET = 100
DEFAULT_MAX_CALLS_PER_RUN = 20
STATE_FILE_NAME = "visual_crossing_backfill_state.json"
RESOLUTIONS_FILE_NAME = "blocked_signals_resolutions.jsonl"
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY manual Visual Crossing backfill for METAR Resolution Verification. "
    "Manual execution only; no scheduler, digest hook, Telegram runtime alert, "
    "source switch, trading, DB write, env var change, BANKROLL, Fase C, Truth "
    "Pipeline, whitelist, city mode, or BUY/SELL/SKIP authorization."
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _now_iso() -> str:
    return _now().isoformat()


def _today_utc() -> str:
    return _now().date().isoformat()


def resolve_data_dir(value: str | None = None) -> Path:
    if value:
        return Path(value)
    env_value = os.environ.get("DATA_DIR", "").strip()
    if env_value:
        return Path(env_value)
    app_data = Path("/app/data")
    if app_data.exists():
        return app_data
    return REPO_ROOT / "data"


def resolve_resolutions_path(data_dir: Path, value: str | None = None) -> Path:
    if value:
        path = Path(value)
        if path.exists():
            return path
        raise SystemExit(f"ERROR: resolutions file not found: {path}")

    candidates = [
        data_dir / "runtime_import_derived" / RESOLUTIONS_FILE_NAME,
        data_dir / RESOLUTIONS_FILE_NAME,
        REPO_ROOT / "data" / "runtime_import_derived" / RESOLUTIONS_FILE_NAME,
    ]
    for path in candidates:
        if path.exists():
            return path

    checked = ", ".join(str(path) for path in candidates)
    raise SystemExit(f"ERROR: resolutions file not found. Checked: {checked}")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"ERROR: {name} must be an integer") from None
    if value < 0:
        raise SystemExit(f"ERROR: {name} must be >= 0")
    return value


def load_state(path: Path, today: str | None = None) -> dict[str, Any]:
    today = today or _today_utc()
    if not path.exists():
        return {"date_utc": today, "calls_used": 0, "runs": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        state = {}
    if state.get("date_utc") != today:
        return {"date_utc": today, "calls_used": 0, "runs": []}
    runs = state.get("runs")
    if not isinstance(runs, list):
        runs = []
    return {
        "date_utc": today,
        "calls_used": int(state.get("calls_used") or 0),
        "runs": runs[-20:],
    }


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_verify_args(data_dir: Path, metar_dir: Path, resolutions_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        resolutions=str(resolutions_path),
        metar_dir=str(metar_dir),
        json_out=str(data_dir / "metar_resolution_verify_report.json"),
        md_out=str(verifier.DEFAULT_MD_OUT),
        city=None,
        limit=None,
        days=60,
        generated_at=None,
    )


def status_counts(report: dict[str, Any]) -> dict[str, int]:
    counts = report.get("summary", {}).get("status_counts", {})
    return {str(key): int(value) for key, value in counts.items()}


def snapshot_path(metar_dir: Path, icao: str, day: str) -> Path:
    return metar_dir / f"{icao.upper()}_{day}.json"


def collect_existing_wave_snapshots(report: dict[str, Any], metar_dir: Path) -> set[tuple[str, str]]:
    existing: set[tuple[str, str]] = set()
    for result in report.get("results", []):
        day = str(result.get("date") or "")
        if not day:
            continue
        for icao in result.get("icaos") or []:
            icao = str(icao).upper()
            if snapshot_path(metar_dir, icao, day).exists():
                existing.add((icao, day))
    return existing


def collect_missing_snapshots(report: dict[str, Any], metar_dir: Path) -> list[dict[str, str]]:
    missing: dict[tuple[str, str], dict[str, str]] = {}
    for result in report.get("results", []):
        if result.get("status") != "NO_SNAPSHOT":
            continue
        day = str(result.get("date") or "")
        city = str(result.get("city") or "")
        if not day:
            continue
        for icao in result.get("icaos") or []:
            icao = str(icao).upper()
            if snapshot_path(metar_dir, icao, day).exists():
                continue
            meta = verifier.metar_fetch.METAR_STATIONS.get(icao, {})
            missing[(icao, day)] = {
                "icao": icao,
                "date": day,
                "city": city or str(meta.get("city") or ""),
                "tz": str(meta.get("tz") or "UTC"),
            }
    return sorted(missing.values(), key=lambda item: (item["date"], item["city"], item["icao"]))


def write_snapshot(out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{str(payload['icao']).upper()}_{payload['date_local']}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def run_verifier(data_dir: Path, metar_dir: Path, resolutions_path: Path, write: bool) -> dict[str, Any]:
    verify_args = build_verify_args(data_dir, metar_dir, resolutions_path)
    report = verifier.build_report(verify_args)
    if write:
        verifier.write_outputs(report, Path(verify_args.json_out), Path(verify_args.md_out))
    return report


def build_summary(
    *,
    calls_used: int,
    budget_remaining: int,
    new_snapshots: int,
    skipped_existing: int,
    before_counts: dict[str, int],
    after_counts: dict[str, int],
    report_path: Path,
    dry_run: bool,
    planned_calls: int,
) -> dict[str, Any]:
    def delta(status: str) -> int:
        return int(after_counts.get(status, 0)) - int(before_counts.get(status, 0))

    return {
        "log_only": True,
        "dry_run": dry_run,
        "calls_used": calls_used,
        "budget_remaining": budget_remaining,
        "new_snapshots": new_snapshots,
        "skipped_existing": skipped_existing,
        "new_match": delta("MATCH"),
        "new_mismatch": delta("MISMATCH"),
        "new_no_snapshot": delta("NO_SNAPSHOT"),
        "new_no_data": delta("NO_DATA"),
        "planned_calls": planned_calls,
        "final_status_counts": after_counts,
        "report_path": str(report_path),
        "disclaimer": LOG_ONLY_DISCLAIMER,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=None, help="Data dir. Default: DATA_DIR, /app/data, then data/.")
    parser.add_argument(
        "--resolutions",
        default=None,
        help="Path to blocked_signals_resolutions.jsonl. Default: DATA_DIR/runtime_import_derived, DATA_DIR, then local data/runtime_import_derived.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no API calls, state writes, or report writes.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = resolve_data_dir(args.data_dir)
    metar_dir = data_dir / "metar_shadow"
    state_path = data_dir / STATE_FILE_NAME
    resolutions_path = resolve_resolutions_path(data_dir, args.resolutions)
    daily_budget = _env_int("VISUAL_CROSSING_DAILY_BUDGET", DEFAULT_DAILY_BUDGET)
    max_calls_per_run = _env_int("VISUAL_CROSSING_MAX_CALLS_PER_RUN", DEFAULT_MAX_CALLS_PER_RUN)

    before_report = run_verifier(data_dir, metar_dir, resolutions_path, write=False)
    before_counts = status_counts(before_report)
    skipped_existing = len(collect_existing_wave_snapshots(before_report, metar_dir))
    missing = collect_missing_snapshots(before_report, metar_dir)

    state = load_state(state_path)
    used_today = int(state.get("calls_used") or 0)
    daily_remaining = max(0, daily_budget - used_today)
    calls_allowed = min(max_calls_per_run, daily_remaining, len(missing))
    report_path = Path(build_verify_args(data_dir, metar_dir, resolutions_path).md_out)

    if args.dry_run:
        after_counts = before_counts
        summary = build_summary(
            calls_used=0,
            budget_remaining=daily_remaining,
            new_snapshots=0,
            skipped_existing=skipped_existing,
            before_counts=before_counts,
            after_counts=after_counts,
            report_path=report_path,
            dry_run=True,
            planned_calls=calls_allowed,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    api_key = os.environ.get("VISUAL_CROSSING_API_KEY", "").strip()
    if calls_allowed and not api_key:
        print("ERROR: VISUAL_CROSSING_API_KEY is not set. No network call made.", file=sys.stderr)
        return 1

    calls_used = 0
    new_snapshots = 0
    for item in missing[:calls_allowed]:
        payload = vc_fetch.build_payload(
            icao=item["icao"],
            date_str=item["date"],
            tz_name=item["tz"],
            city=item["city"],
            location=vc_fetch.resolve_location(item["icao"], None, None),
            api_key=api_key,
        )
        calls_used += 1
        state["calls_used"] = int(state.get("calls_used") or 0) + 1
        state["updated_at"] = _now_iso()
        save_state(state_path, state)
        out_path = write_snapshot(metar_dir, payload)
        if out_path.exists():
            new_snapshots += 1

    after_report = run_verifier(data_dir, metar_dir, resolutions_path, write=True)
    after_counts = status_counts(after_report)
    state["runs"] = (state.get("runs") or [])[-19:] + [
        {
            "at": _now_iso(),
            "calls_used": calls_used,
            "new_snapshots": new_snapshots,
            "remaining_missing_snapshots": max(0, len(missing) - calls_used),
        }
    ]
    state["updated_at"] = _now_iso()
    save_state(state_path, state)

    budget_remaining = max(0, daily_budget - int(state.get("calls_used") or 0))
    summary = build_summary(
        calls_used=calls_used,
        budget_remaining=budget_remaining,
        new_snapshots=new_snapshots,
        skipped_existing=skipped_existing,
        before_counts=before_counts,
        after_counts=after_counts,
        report_path=report_path,
        dry_run=False,
        planned_calls=calls_allowed,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
