#!/usr/bin/env python3
"""LOG_ONLY collector wrapper for Traders Intelligence V1 snapshots.

The collector is a safety wrapper around tools/traders_intelligence_snapshot.py.
It adds state, cooldown, idempotency, dry-run support, and a kill switch. It
does not inspect, rank, or act on signals beyond invoking the existing V1
snapshot archivist.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "traders_intelligence" / "collector_state.json"
DEFAULT_AGENT_EVENTS_PATH = REPO_ROOT / "agent_events.jsonl"
SNAPSHOT_TOOL_PATH = REPO_ROOT / "tools" / "traders_intelligence_snapshot.py"

SCHEMA_VERSION = "traders_intelligence_collector_state_v1"
EVENT_SCHEMA_VERSION = "traders_intelligence_collector_event_v1"
ENV_FLAG = "TRADERS_INTELLIGENCE_COLLECTOR"
DEFAULT_COOLDOWN_MINUTES = 30
DEFAULT_FAILURE_LIMIT = 5
ON_VALUES = {"1", "true", "yes", "on"}


class CollectorError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clean_run_id(value: str) -> str:
    import re

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or "collector_run"


def timestamp_to_run_id(value: str) -> str:
    return clean_run_id(value.replace("+00:00", "Z").replace(":", "").replace("-", ""))


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise CollectorError(f"missing signals.json: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CollectorError(f"invalid signals.json: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise CollectorError(f"signals.json must contain an object: {path}")
    return payload


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "last_run_id": None,
            "last_snapshot_at": None,
            "last_signals_generated_at": None,
            "consecutive_failures": 0,
            "kill_switch_active": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CollectorError(f"invalid collector_state.json: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise CollectorError(f"collector_state.json must contain an object: {path}")
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("last_run_id", None)
    payload.setdefault("last_snapshot_at", None)
    payload.setdefault("last_signals_generated_at", None)
    payload.setdefault("consecutive_failures", 0)
    payload.setdefault("kill_switch_active", False)
    return payload


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.open("a", encoding="utf-8", newline="\n").write(json.dumps(event, sort_keys=True) + "\n")


def env_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in ON_VALUES


def build_event(
    *,
    now: datetime,
    status: str,
    ok: bool,
    run_id: str | None,
    dry_run: bool,
    reason: str | None = None,
    snapshot_result: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = (snapshot_result or {}).get("status_counts") or {}
    return {
        "timestamp": now.isoformat(),
        "session": "runtime",
        "agent": "Codex",
        "type": "traders_intelligence_collector_run",
        "stage": "validated" if ok else "implemented",
        "title": "Traders Intelligence collector LOG_ONLY",
        "description": f"status={status} reason={reason or 'none'} run_id={run_id or 'none'}",
        "points": 0,
        "impact": "low",
        "validated": bool(ok),
        "schema_version": EVENT_SCHEMA_VERSION,
        "run_id": run_id,
        "dry_run": bool(dry_run),
        "ok": bool(ok),
        "collector_status": status,
        "reason": reason,
        "n_signals": (snapshot_result or {}).get("n_current_signals"),
        "status_counts": summary,
        "consecutive_failures": int((state or {}).get("consecutive_failures", 0) or 0),
        "kill_switch_active": bool((state or {}).get("kill_switch_active", False)),
    }


def should_skip(
    *,
    state: dict[str, Any],
    signals_generated_at: str | None,
    now: datetime,
    cooldown_minutes: int,
) -> tuple[bool, str | None]:
    if state.get("kill_switch_active"):
        return True, "kill_switch_active"
    if signals_generated_at and signals_generated_at == state.get("last_signals_generated_at"):
        return True, "signals_unchanged"
    last_snapshot_at = parse_time(state.get("last_snapshot_at"))
    if last_snapshot_at and now - last_snapshot_at < timedelta(minutes=cooldown_minutes):
        return True, "cooldown_active"
    return False, None


def run_snapshot_tool(args: argparse.Namespace, run_id: str, snapshot_at: str) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SNAPSHOT_TOOL_PATH),
        "--signals",
        str(args.signals),
        "--snapshot-dir",
        str(args.snapshot_dir),
        "--report-dir",
        str(args.report_dir),
        "--audit-log",
        str(args.audit_log),
        "--run-id",
        run_id,
        "--snapshot-at",
        snapshot_at,
    ]
    if args.dry_run:
        command.append("--dry-run")

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=args.timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no detail").strip()
        raise CollectorError(f"snapshot tool failed: {detail[:500]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CollectorError(f"snapshot tool returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CollectorError("snapshot tool returned a non-object JSON payload")
    return payload


def build_run(args: argparse.Namespace, env: dict[str, str] | None = None) -> dict[str, Any]:
    env_map = env or os.environ
    now = parse_time(args.now) if args.now else utc_now()
    if now is None:
        raise CollectorError(f"invalid --now timestamp: {args.now}")

    state_path = Path(args.state)
    state = load_state(state_path)

    if not env_enabled(env_map.get(ENV_FLAG)):
        return {
            "ok": True,
            "status": "skipped",
            "reason": "env_off",
            "dry_run": bool(args.dry_run),
            "state_written": False,
            "snapshot_written": False,
            "event_written": False,
            "state": state,
        }

    signals_path = Path(args.signals)
    signals_payload = load_json(signals_path)
    signals_generated_at = signals_payload.get("generated")
    if signals_generated_at is not None:
        signals_generated_at = str(signals_generated_at)

    skip, reason = should_skip(
        state=state,
        signals_generated_at=signals_generated_at,
        now=now,
        cooldown_minutes=args.cooldown_minutes,
    )
    if skip:
        return {
            "ok": True,
            "status": "skipped",
            "reason": reason,
            "dry_run": bool(args.dry_run),
            "state_written": False,
            "snapshot_written": False,
            "event_written": False,
            "state": state,
        }

    snapshot_at = now.isoformat()
    run_id = clean_run_id(args.run_id) if args.run_id else timestamp_to_run_id(snapshot_at) + "-v11-collector"

    try:
        snapshot_result = run_snapshot_tool(args, run_id, snapshot_at)
    except Exception as exc:
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0) or 0) + 1
        state["last_failure_at"] = now.isoformat()
        state["last_error"] = str(exc)[:500]
        if state["consecutive_failures"] >= args.failure_limit:
            state["kill_switch_active"] = True
        if not args.dry_run:
            write_state(state_path, state)
            append_event(
                Path(args.agent_events),
                build_event(
                    now=now,
                    status="failed",
                    ok=False,
                    run_id=run_id,
                    dry_run=args.dry_run,
                    reason=str(exc)[:200],
                    state=state,
                ),
            )
        raise

    next_state = dict(state)
    next_state.update(
        {
            "schema_version": SCHEMA_VERSION,
            "last_run_id": run_id,
            "last_snapshot_at": snapshot_at,
            "last_signals_generated_at": signals_generated_at,
            "last_success_at": now.isoformat(),
            "consecutive_failures": 0,
            "kill_switch_active": False,
            "last_error": None,
        }
    )

    event = build_event(
        now=now,
        status="completed",
        ok=True,
        run_id=run_id,
        dry_run=args.dry_run,
        snapshot_result=snapshot_result,
        state=next_state,
    )
    state_written = False
    event_written = False
    if not args.dry_run:
        write_state(state_path, next_state)
        state_written = True
        append_event(Path(args.agent_events), event)
        event_written = True

    return {
        "ok": True,
        "status": "completed",
        "reason": None,
        "run_id": run_id,
        "dry_run": bool(args.dry_run),
        "state_written": state_written,
        "snapshot_written": not args.dry_run,
        "event_written": event_written,
        "signals_generated_at": signals_generated_at,
        "snapshot_result": snapshot_result,
        "state": next_state if state_written else state,
        "event": event,
        "guardrails": {
            "log_only": True,
            "default_off": True,
            "does_not_trade": True,
            "does_not_change_policy": True,
            "not_a_trading_signal": True,
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Traders Intelligence V1.1 LOG_ONLY collector.")
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH), help="Path to signals.json.")
    parser.add_argument("--state", default=str(DEFAULT_STATE_PATH), help="Collector state JSON path.")
    parser.add_argument("--agent-events", default=str(DEFAULT_AGENT_EVENTS_PATH), help="agent_events.jsonl path.")
    parser.add_argument("--snapshot-dir", default=str(REPO_ROOT / "data" / "traders_intelligence" / "snapshots"))
    parser.add_argument("--report-dir", default=str(REPO_ROOT / "data" / "traders_intelligence" / "reports"))
    parser.add_argument("--audit-log", default=str(REPO_ROOT / "data" / "traders_intelligence" / "pseudo_lifecycle_runs.jsonl"))
    parser.add_argument("--run-id", help="Optional deterministic run id.")
    parser.add_argument("--cooldown-minutes", type=int, default=DEFAULT_COOLDOWN_MINUTES)
    parser.add_argument("--failure-limit", type=int, default=DEFAULT_FAILURE_LIMIT)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--now", help="UTC timestamp override for tests/audits.")
    parser.add_argument("--dry-run", action="store_true", help="Run the snapshot tool in dry-run mode and do not write collector state/events.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = build_run(args)
    except CollectorError as exc:
        print(f"traders_intelligence_collector error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"traders_intelligence_collector unexpected error: {str(exc)[:500]}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "traders_intelligence_collector "
            f"status={result.get('status')} "
            f"reason={result.get('reason') or 'none'} "
            f"run_id={result.get('run_id') or 'none'} "
            f"dry_run={str(result.get('dry_run')).lower()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
