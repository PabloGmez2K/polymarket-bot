#!/usr/bin/env python3
"""LOG_ONLY monitor for trader operational intelligence evidence.

This wrapper reuses the full snapshot collector and the six-question report,
then decides whether a compact Telegram/digest message is warranted. It owns
only observability state: no trading, no policy, no env mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_SNAPSHOTS_PATH = REPO_ROOT / "data" / "intelligence" / "trader_signals_snapshots.jsonl"
DEFAULT_REPORT_JSON_PATH = REPO_ROOT / "data" / "intelligence" / "traders_operational_questions_report.json"
DEFAULT_REPORT_MD_PATH = REPO_ROOT / "docs" / "traders_operational_questions_report_latest.md"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "intelligence" / "traders_operational_monitor_state.json"
DEFAULT_AGENT_EVENTS_PATH = REPO_ROOT / "agent_events.jsonl"
COLLECTOR_PATH = REPO_ROOT / "tools" / "trader_signals_full_snapshot_collector.py"
REPORT_PATH = REPO_ROOT / "tools" / "traders_operational_questions_report.py"

SCHEMA_VERSION = "traders_operational_intelligence_monitor_state_v1"
EVENT_SCHEMA_VERSION = "traders_operational_intelligence_monitor_event_v1"
ENV_FLAG = "TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED"
ON_VALUES = {"1", "true", "yes", "on"}
OFF_VALUES = {"0", "false", "no", "off"}
DEFAULT_DAILY_DIGEST_HOUR_UTC = 8
DEFAULT_STALE_HOURS = 26.0
DEFAULT_ERROR_COOLDOWN_MINUTES = 360
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY. No BUY/SELL/SKIP. No city mode changes. Human review required."
)


class MonitorError(Exception):
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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MonitorError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_enabled(value: str | None) -> bool:
    text = str(value if value is not None else "true").strip().lower()
    if text in OFF_VALUES:
        return False
    if text in ON_VALUES:
        return True
    return True


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise MonitorError(f"missing signals.json: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MonitorError(f"invalid signals.json: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise MonitorError(f"signals.json must be an object: {path}")
    return payload


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "last_success_at": None,
        "last_signals_generated_at": None,
        "last_activity_answerability": None,
        "known_not_observed_keys": [],
        "known_gap_sufficient_keys": [],
        "last_digest_date": None,
        "last_notification_at": None,
        "last_notification_signature": None,
        "last_error_signature": None,
        "last_error_at": None,
        "last_stale": False,
        "consecutive_failures": 0,
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise MonitorError(f"invalid monitor state: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise MonitorError(f"monitor state must be an object: {path}")
    state = default_state()
    state.update(payload)
    state["schema_version"] = SCHEMA_VERSION
    for key in ("known_not_observed_keys", "known_gap_sufficient_keys"):
        if not isinstance(state.get(key), list):
            state[key] = []
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.open("a", encoding="utf-8", newline="\n").write(json.dumps(event, sort_keys=True) + "\n")


def signature(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def answerability_map(report: dict[str, Any]) -> dict[str, str]:
    labels = [
        "activity_by_hour",
        "cities_activity",
        "traders_activity_wr",
        "traders_wr",
        "winning_not_observed",
        "winning_bot_gap",
    ]
    questions = report.get("questions") or []
    return {
        label: str((questions[index] if index < len(questions) else {}).get("answerability", "NO"))
        for index, label in enumerate(labels)
    }


def row_key(row: dict[str, Any], *fields: str) -> str:
    return "|".join(str(row.get(field, "")) for field in fields)


def classify_signals_staleness(signals_payload: dict[str, Any], now: datetime, stale_hours: float) -> dict[str, Any]:
    generated = signals_payload.get("generated")
    generated_dt = parse_time(generated)
    if generated_dt is None:
        return {"stale": True, "age_hours": None, "reason": "generated_missing_or_invalid"}
    age_hours = (now - generated_dt).total_seconds() / 3600
    return {
        "stale": age_hours > stale_hours,
        "age_hours": round(age_hours, 1),
        "reason": "stale" if age_hours > stale_hours else "fresh",
    }


def run_collector(args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    collector = load_module(COLLECTOR_PATH, "trader_signals_full_snapshot_collector")
    collector_args = collector.parse_args(
        [
            "--signals",
            str(args.signals),
            "--output",
            str(args.snapshots),
            "--snapshot-at",
            now.isoformat(),
        ]
        + (["--dry-run"] if args.dry_run else [])
    )
    return collector.build_run(collector_args)


def run_report(args: argparse.Namespace) -> dict[str, Any]:
    report_mod = load_module(REPORT_PATH, "traders_operational_questions_report")
    report_args = report_mod.parse_args(
        [
            "--signals",
            str(args.signals),
            "--snapshots",
            str(args.snapshots),
            "--blocked-resolutions",
            str(args.blocked_resolutions),
            "--blocked-fallback",
            str(args.blocked_fallback),
            "--trade-lifecycle",
            str(args.trade_lifecycle),
            "--json-output",
            str(args.report_json),
            "--md-output",
            str(args.report_md),
            "--min-hourly-snapshots",
            str(args.min_hourly_snapshots),
            "--min-trader-n",
            str(args.min_trader_n),
            "--min-bot-n",
            str(args.min_bot_n),
        ]
        + (["--dry-run"] if args.dry_run else [])
    )
    payload = report_mod.build_report(report_args)
    if not args.dry_run:
        json_path = Path(args.report_json)
        md_path = Path(args.report_md)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(report_mod.render_markdown(payload), encoding="utf-8")
    return payload


def build_telegram_message(report: dict[str, Any], reasons: list[str], staleness: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    tables = report.get("tables") or {}
    answers = answerability_map(report)
    snapshot_count = summary.get("distinct_snapshot_at", 0)

    lines = [
        "<b>Traders Operational Intelligence</b> (LOG_ONLY)",
        f"Reasons: {', '.join(reasons)}",
        f"Snapshots: {snapshot_count} | rows={summary.get('snapshot_rows', 0)}",
        "Answerability: "
        + ", ".join(
            f"{key}={value}" for key, value in answers.items()
        ),
    ]

    if staleness.get("stale"):
        age = staleness.get("age_hours")
        age_text = "unknown" if age is None else f"{age:.1f}h"
        lines.append(f"signals.json stale: age={age_text} reason={staleness.get('reason')}")

    if answers.get("activity_by_hour") == "NO":
        lines.append(
            "Activity by hour: NO "
            f"(snapshots={snapshot_count}; needs at least 2 distinct full snapshots)."
        )
    elif tables.get("top_activity_hours_utc"):
        top_hour = tables["top_activity_hours_utc"][0]
        lines.append(
            "Activity by hour: "
            f"{top_hour.get('hour_utc')} new={top_hour.get('new_signal_appearances')}"
        )

    top_traders = tables.get("top_traders_by_activity") or []
    if top_traders:
        parts = []
        for row in top_traders[:3]:
            wr = row.get("blocked_wr_pct")
            wr_text = "WR=n/a" if wr is None else f"WR={wr}%"
            parts.append(f"{row.get('trader')} sig={row.get('current_signals')} {wr_text} n={row.get('blocked_n')}")
        lines.append("Top traders: " + " | ".join(parts))

    not_observed = tables.get("trader_winning_not_observed") or []
    if not_observed:
        row = not_observed[0]
        lines.append(
            "Top trader-winning-not-observed: "
            f"{row.get('city')} WR={row.get('trader_wr_pct')}% n={row.get('trader_n')}"
        )

    gaps = tables.get("trader_winning_bot_gap") or []
    if gaps:
        gap_parts = []
        for row in gaps[:3]:
            label = row.get("classification")
            if label == "TRADER_WINNING_BOT_INSUFFICIENT_N":
                label = "INSUFFICIENT_N"
            gap_parts.append(
                f"{row.get('city')} {label} trader={row.get('trader_wr_pct')}%/{row.get('trader_n')} "
                f"bot_n={row.get('bot_n')}"
            )
        lines.append("Trader-vs-bot gaps: " + " | ".join(gap_parts))

    lines.append(LOG_ONLY_DISCLAIMER)
    return "\n".join(lines)


def detect_reasons(
    *,
    report: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
    staleness: dict[str, Any],
    daily_digest_hour_utc: int,
) -> tuple[list[str], dict[str, Any]]:
    answers = answerability_map(report)
    tables = report.get("tables") or {}
    today = now.date().isoformat()
    reasons: list[str] = []

    if not state.get("last_success_at"):
        reasons.append("first_run")

    prev_activity = state.get("last_activity_answerability")
    current_activity = answers.get("activity_by_hour")
    if prev_activity == "NO" and current_activity in {"PARTIAL", "YES"}:
        reasons.append(f"activity_by_hour_{prev_activity}_to_{current_activity}")

    known_not_observed = set(state.get("known_not_observed_keys") or [])
    current_not_observed = {
        row_key(row, "city") for row in tables.get("trader_winning_not_observed", [])
        if int(row.get("trader_n") or 0) >= 3
    }
    new_not_observed = sorted(current_not_observed - known_not_observed)
    if new_not_observed:
        reasons.append("new_trader_winning_not_observed")

    known_gaps = set(state.get("known_gap_sufficient_keys") or [])
    current_gaps = {
        row_key(row, "city", "classification") for row in tables.get("trader_winning_bot_gap", [])
        if int(row.get("bot_n") or 0) >= 3
        and row.get("classification") == "TRADER_WINNING_BOT_NOT_WINNING"
    }
    new_gaps = sorted(current_gaps - known_gaps)
    if new_gaps:
        reasons.append("new_trader_gap_bot_n_sufficient")

    if staleness.get("stale") and not state.get("last_stale"):
        reasons.append("signals_stale")

    if now.hour >= daily_digest_hour_utc % 24 and state.get("last_digest_date") != today:
        reasons.append("daily_digest")

    observed = {
        "answers": answers,
        "current_not_observed_keys": sorted(current_not_observed),
        "current_gap_sufficient_keys": sorted(current_gaps),
        "new_not_observed_keys": new_not_observed,
        "new_gap_sufficient_keys": new_gaps,
        "today": today,
    }
    return reasons, observed


def build_event(now: datetime, status: str, reasons: list[str], ok: bool, report: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = (report or {}).get("summary") or {}
    return {
        "timestamp": now.isoformat(),
        "session": "runtime",
        "agent": "Codex",
        "type": "traders_operational_intelligence_monitor",
        "stage": "validated" if ok else "implemented",
        "title": "Traders Operational Intelligence monitor LOG_ONLY",
        "description": f"status={status} reasons={','.join(reasons) or 'none'}",
        "points": 0,
        "impact": "low",
        "validated": bool(ok),
        "schema_version": EVENT_SCHEMA_VERSION,
        "status": status,
        "reasons": reasons,
        "snapshot_count": summary.get("distinct_snapshot_at"),
        "answerability": answerability_map(report or {}),
    }


def error_result(args: argparse.Namespace, state: dict[str, Any], now: datetime, exc: Exception) -> dict[str, Any]:
    message = str(exc)[:500]
    error_sig = signature(message)
    last_error_at = parse_time(state.get("last_error_at"))
    cooldown = timedelta(minutes=args.error_cooldown_minutes)
    should_notify = error_sig != state.get("last_error_signature") or not last_error_at or now - last_error_at >= cooldown
    next_state = dict(state)
    next_state.update(
        {
            "schema_version": SCHEMA_VERSION,
            "last_error_signature": error_sig,
            "last_error_at": now.isoformat(),
            "consecutive_failures": int(state.get("consecutive_failures", 0) or 0) + 1,
        }
    )
    telegram_message = None
    if should_notify:
        telegram_message = "\n".join(
            [
                "<b>Traders Operational Intelligence</b> (LOG_ONLY)",
                "Status: ERROR",
                f"Detail: <code>{message}</code>",
                LOG_ONLY_DISCLAIMER,
            ]
        )
        next_state["last_notification_at"] = now.isoformat()
        next_state["last_notification_signature"] = error_sig
    if not args.dry_run:
        write_state(Path(args.state), next_state)
        if should_notify:
            append_event(Path(args.agent_events), build_event(now, "failed", ["error"], False))
    return {
        "ok": False,
        "status": "failed",
        "reason": message,
        "should_notify": should_notify,
        "telegram_message": telegram_message,
        "state_written": not args.dry_run,
        "event_written": bool(should_notify and not args.dry_run),
        "dry_run": bool(args.dry_run),
    }


def build_run(args: argparse.Namespace, env: dict[str, str] | None = None) -> dict[str, Any]:
    env_map = env or os.environ
    now = parse_time(args.now) if args.now else utc_now()
    if now is None:
        raise MonitorError(f"invalid --now timestamp: {args.now}")

    state = load_state(Path(args.state))
    if not env_enabled(env_map.get(ENV_FLAG)):
        return {
            "ok": True,
            "status": "skipped",
            "reason": "env_off",
            "should_notify": False,
            "telegram_message": None,
            "state_written": False,
            "event_written": False,
            "dry_run": bool(args.dry_run),
        }

    try:
        signals_payload = load_json(Path(args.signals))
        staleness = classify_signals_staleness(signals_payload, now, args.stale_hours)
        collector_result = run_collector(args, now)
        report = run_report(args)
        reasons, observed = detect_reasons(
            report=report,
            state=state,
            now=now,
            staleness=staleness,
            daily_digest_hour_utc=args.daily_digest_hour_utc,
        )
    except Exception as exc:
        return error_result(args, state, now, exc)

    should_notify = bool(reasons)
    notify_sig = signature({"reasons": reasons, "report": report.get("tables", {}), "stale": staleness})
    telegram_message = build_telegram_message(report, reasons, staleness) if should_notify else None

    next_state = dict(state)
    next_state.update(
        {
            "schema_version": SCHEMA_VERSION,
            "last_success_at": now.isoformat(),
            "last_signals_generated_at": signals_payload.get("generated"),
            "last_activity_answerability": observed["answers"].get("activity_by_hour"),
            "known_not_observed_keys": observed["current_not_observed_keys"],
            "known_gap_sufficient_keys": observed["current_gap_sufficient_keys"],
            "last_stale": bool(staleness.get("stale")),
            "consecutive_failures": 0,
        }
    )
    if "daily_digest" in reasons:
        next_state["last_digest_date"] = observed["today"]
    if should_notify:
        next_state["last_notification_at"] = now.isoformat()
        next_state["last_notification_signature"] = notify_sig

    event_written = False
    if not args.dry_run:
        write_state(Path(args.state), next_state)
        if should_notify:
            append_event(Path(args.agent_events), build_event(now, "completed", reasons, True, report))
            event_written = True

    return {
        "ok": True,
        "status": "completed",
        "reason": None,
        "should_notify": should_notify,
        "notification_reasons": reasons,
        "telegram_message": telegram_message,
        "collector_result": collector_result,
        "report_summary": report.get("summary", {}),
        "answerability": observed["answers"],
        "staleness": staleness,
        "state_written": not args.dry_run,
        "event_written": event_written,
        "dry_run": bool(args.dry_run),
        "guardrails": {
            "log_only": True,
            "does_not_trade": True,
            "does_not_change_policy": True,
            "not_a_trading_signal": True,
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Traders Operational Intelligence LOG_ONLY monitor.")
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH))
    parser.add_argument("--snapshots", default=str(DEFAULT_SNAPSHOTS_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON_PATH))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD_PATH))
    parser.add_argument("--state", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--agent-events", default=str(DEFAULT_AGENT_EVENTS_PATH))
    parser.add_argument("--blocked-resolutions", default=str(REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl"))
    parser.add_argument("--blocked-fallback", default=str(REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"))
    parser.add_argument("--trade-lifecycle", default=str(REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"))
    parser.add_argument("--daily-digest-hour-utc", type=int, default=DEFAULT_DAILY_DIGEST_HOUR_UTC)
    parser.add_argument("--stale-hours", type=float, default=DEFAULT_STALE_HOURS)
    parser.add_argument("--error-cooldown-minutes", type=int, default=DEFAULT_ERROR_COOLDOWN_MINUTES)
    parser.add_argument("--min-hourly-snapshots", type=int, default=2)
    parser.add_argument("--min-trader-n", type=int, default=3)
    parser.add_argument("--min-bot-n", type=int, default=3)
    parser.add_argument("--now")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = build_run(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(
            "traders_operational_intelligence_monitor "
            f"status={result.get('status')} "
            f"reason={result.get('reason') or 'none'} "
            f"notify={str(result.get('should_notify')).lower()}"
        )
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
