#!/usr/bin/env python3
"""Source Onboarding Andon v1 - LOG_ONLY Telegram/digest trigger layer.

Consumes Source Onboarding Scanner v0.2 output and decides whether Pablo should
get a human-action alert. It owns only observability state: no trading, no
policy, no env mutation, no DB writes, no source mapping changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_JSON = REPO_ROOT / "data" / "source_onboarding.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "source_onboarding" / "andon_state.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "source_onboarding" / "andon_latest.json"
DEFAULT_AGENT_EVENTS_PATH = REPO_ROOT / "agent_events.jsonl"

SCHEMA_VERSION = "source_onboarding_andon_state_v1"
EVENT_SCHEMA_VERSION = "source_onboarding_andon_event_v1"
ENV_FLAG = "SOURCE_ONBOARDING_ANDON_ENABLED"
ON_VALUES = {"1", "true", "yes", "on"}
OFF_VALUES = {"0", "false", "no", "off"}

READY_AUDIT = "READY_FOR_HUMAN_SOURCE_AUDIT"
READY_AUDIT_LEGACY = "READY_FOR_SOURCE_AUDIT"
SOURCE_CONFIRMED_WAITING_SHADOW = "SOURCE_CONFIRMED_WAITING_SHADOW"
SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
SOURCE_MISMATCH = "SOURCE_MISMATCH"
SHADOW_READY = "SHADOW_EVIDENCE_READY"

ACTIONABLE_STATUSES = {
    READY_AUDIT,
    READY_AUDIT_LEGACY,
    SOURCE_CONFIRMED_WAITING_SHADOW,
    SOURCE_AMBIGUOUS,
    SOURCE_MISMATCH,
}

LOG_ONLY_DISCLAIMER = (
    "NO_ACTION / LOG_ONLY. Do not add to active/canary. "
    "No BUY/SELL/SKIP. No BANKROLL. No Phase C. Human review required."
)

PRIORITY_TIERS = [
    ("LOW", 0.5),
    ("MEDIUM", 1.5),
    ("HIGH", 2.5),
]


class AndonError(Exception):
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


def env_enabled(value: str | None) -> bool:
    text = str(value if value is not None else "true").strip().lower()
    if text in OFF_VALUES:
        return False
    if text in ON_VALUES:
        return True
    return True


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "last_success_at": None,
        "last_notification_at": None,
        "last_notification_signature": None,
        "cities": {},
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AndonError(f"invalid andon state: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise AndonError(f"andon state must be an object: {path}")
    state = default_state()
    state.update(payload)
    state["schema_version"] = SCHEMA_VERSION
    if not isinstance(state.get("cities"), dict):
        state["cities"] = {}
    return state


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.open("a", encoding="utf-8", newline="\n").write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def signature(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_source_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise AndonError(f"missing source onboarding scanner output: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AndonError(f"invalid source onboarding scanner output: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise AndonError(f"source onboarding scanner output must be an object: {path}")
    if payload.get("log_only") is not True:
        raise AndonError("source onboarding scanner output is not marked log_only=true")
    return payload


def priority_tier(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    tier = "BELOW_THRESHOLD"
    for label, threshold in PRIORITY_TIERS:
        if value >= threshold:
            tier = label
    return tier


def tier_rank(tier: str | None) -> int:
    order = {"UNKNOWN": -1, "BELOW_THRESHOLD": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    return order.get(str(tier or "UNKNOWN"), -1)


def normalize_city_record(record: dict[str, Any]) -> dict[str, Any]:
    shadow = record.get("shadow") if isinstance(record.get("shadow"), dict) else {}
    trader_report = record.get("trader_report") if isinstance(record.get("trader_report"), dict) else {}
    blocked = record.get("blocked_signals") if isinstance(record.get("blocked_signals"), dict) else {}
    primary = record.get("primary_status") or record.get("state") or record.get("recommended_state")
    source_audit = record.get("source_audit_status")
    score = record.get("priority_score")
    return {
        "city": str(record.get("city") or "").strip(),
        "primary_status": primary,
        "source_audit_status": source_audit,
        "shadow_evidence_status": record.get("shadow_evidence_status"),
        "observation_pipeline_status": record.get("observation_pipeline_status"),
        "priority_score": score,
        "priority_tier": priority_tier(score),
        "missing_inputs": list(record.get("missing_inputs") or []),
        "next_best_action": record.get("next_best_action"),
        "operational_action": record.get("operational_action") or "NO_ACTION / LOG_ONLY",
        "opus_review_required": bool(record.get("opus_review_required")),
        "trader_wins": trader_report.get("trader_wins"),
        "trader_n": trader_report.get("trader_n"),
        "trader_wr_pct": trader_report.get("trader_wr_pct"),
        "blocked_wr": blocked.get("wr"),
        "blocked_n": blocked.get("n"),
        "blocked_n_evaluated": blocked.get("n_evaluated"),
        "shadow_cycles": int(shadow.get("cycles_seen", 0) or 0),
        "shadow_edge_hits": int(shadow.get("edge_hits", 0) or 0),
        "shadow_best_edge_pct": shadow.get("best_edge_pct"),
    }


def compact_city_state(city: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_status": city.get("primary_status"),
        "source_audit_status": city.get("source_audit_status"),
        "shadow_evidence_status": city.get("shadow_evidence_status"),
        "observation_pipeline_status": city.get("observation_pipeline_status"),
        "shadow_cycles": city.get("shadow_cycles"),
        "shadow_edge_hits": city.get("shadow_edge_hits"),
        "priority_score": city.get("priority_score"),
        "priority_tier": city.get("priority_tier"),
        "last_fingerprint": city_fingerprint(city),
    }


def city_fingerprint(city: dict[str, Any]) -> str:
    return signature(
        {
            "city": city.get("city"),
            "primary_status": city.get("primary_status"),
            "source_audit_status": city.get("source_audit_status"),
            "shadow_evidence_status": city.get("shadow_evidence_status"),
            "shadow_cycles": city.get("shadow_cycles"),
            "shadow_edge_hits": city.get("shadow_edge_hits"),
            "priority_tier": city.get("priority_tier"),
        }
    )


def detect_city_events(city: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    previous = previous or {}
    events: list[str] = []
    current_primary = city.get("primary_status")
    current_audit = city.get("source_audit_status")
    previous_primary = previous.get("primary_status")
    previous_audit = previous.get("source_audit_status")

    if current_audit in {READY_AUDIT, READY_AUDIT_LEGACY} and previous_audit not in {READY_AUDIT, READY_AUDIT_LEGACY}:
        events.append("NEW_HUMAN_SOURCE_AUDIT_READY")

    if current_primary == SOURCE_CONFIRMED_WAITING_SHADOW and previous_primary != SOURCE_CONFIRMED_WAITING_SHADOW:
        events.append("SOURCE_CONFIRMED_WAITING_SHADOW")

    if (
        city.get("shadow_evidence_status") == SHADOW_READY
        and previous.get("shadow_evidence_status") != SHADOW_READY
    ):
        events.append("OBSERVATION_REVIEW_READY")

    if (
        (current_primary == SOURCE_AMBIGUOUS or current_audit == SOURCE_AMBIGUOUS)
        and previous_primary != SOURCE_AMBIGUOUS
        and previous_audit != SOURCE_AMBIGUOUS
    ):
        events.append("SOURCE_AMBIGUOUS")

    if (
        (current_primary == SOURCE_MISMATCH or current_audit == SOURCE_MISMATCH)
        and previous_primary != SOURCE_MISMATCH
        and previous_audit != SOURCE_MISMATCH
    ):
        events.append("SOURCE_MISMATCH")

    previous_tier = previous.get("priority_tier")
    current_tier = city.get("priority_tier")
    if previous and tier_rank(current_tier) > tier_rank(previous_tier):
        events.append("PRIORITY_UPGRADED")

    return events


def select_action_for_pablo(event_names: list[str], city: dict[str, Any]) -> str:
    if "SOURCE_MISMATCH" in event_names:
        return "ESCALATE_OPUS before any mapping or city-mode change."
    if "SOURCE_AMBIGUOUS" in event_names:
        return "ESCALATE_OPUS before any mapping or city-mode change."
    if "OBSERVATION_REVIEW_READY" in event_names:
        return "Observation review ready. Human/Opus review required before any promotion discussion."
    if "SOURCE_CONFIRMED_WAITING_SHADOW" in event_names:
        return "Human source audit ready, but wait for stronger shadow before promotion review."
    if "NEW_HUMAN_SOURCE_AUDIT_READY" in event_names:
        return "Human source audit ready. Review source evidence manually before any operational change."
    if "PRIORITY_UPGRADED" in event_names:
        return f"Priority upgraded to {city.get('priority_tier')}. Re-check evidence manually; keep LOG_ONLY."
    return "Review manually; keep LOG_ONLY."


def format_trader_line(city: dict[str, Any]) -> str:
    wins = city.get("trader_wins")
    n = city.get("trader_n")
    wr = city.get("trader_wr_pct")
    if wins is not None and n:
        return f"trader WR {wins}/{n} = {float(wr or 0):.1f}%"
    blocked_wr = city.get("blocked_wr")
    blocked_n = city.get("blocked_n")
    blocked_eval = city.get("blocked_n_evaluated")
    if blocked_wr is not None and blocked_n:
        return f"blocked WR {blocked_eval or blocked_n}/{blocked_n} = {float(blocked_wr) * 100:.1f}%"
    return "candidate evidence changed"


def format_shadow_line(city: dict[str, Any]) -> str:
    best = city.get("shadow_best_edge_pct")
    best_text = "n/a" if best is None else f"{float(best):.1f}%"
    return (
        f"cycles={city.get('shadow_cycles', 0)}, "
        f"edge_hits={city.get('shadow_edge_hits', 0)}, best_edge={best_text}"
    )


def build_telegram_message(events: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, event in enumerate(events[:5]):
        city = event["city"]
        event_names = event["events"]
        is_risk = any(name in {"SOURCE_AMBIGUOUS", "SOURCE_MISMATCH"} for name in event_names)
        title = "🔴 Source Onboarding Risk" if is_risk else "🟡 Source Onboarding Candidate"
        if index:
            lines.append("")
            lines.append("---")
            lines.append("")
        lines.extend(
            [
                f"<b>{title}</b>",
                "",
                f"City: {city.get('city')}",
                f"Event: {', '.join(event_names)}",
                f"Status: {city.get('primary_status')}",
                f"Why it matters: {format_trader_line(city)}",
                f"Shadow: {format_shadow_line(city)}",
                f"Source audit: {city.get('source_audit_status')}",
                f"Missing: {', '.join(city.get('missing_inputs') or []) or 'none'}",
                "",
                "Action for Pablo:",
                select_action_for_pablo(event_names, city),
                "",
                "Operational action:",
                LOG_ONLY_DISCLAIMER,
            ]
        )
    if len(events) > 5:
        lines.extend(["", f"... and {len(events) - 5} more source onboarding event(s)."])
    return "\n".join(lines)


def build_event(now: datetime, events: list[dict[str, Any]], ok: bool) -> dict[str, Any]:
    return {
        "timestamp": now.isoformat(),
        "session": "runtime",
        "agent": "Codex",
        "type": "source_onboarding_andon",
        "stage": "validated" if ok else "implemented",
        "title": "Source Onboarding Andon LOG_ONLY",
        "description": f"events={len(events)}",
        "points": 0,
        "impact": "low",
        "validated": bool(ok),
        "schema_version": EVENT_SCHEMA_VERSION,
        "events": [
            {"city": e["city"].get("city"), "reasons": e["events"]}
            for e in events
        ],
    }


def error_result(args: argparse.Namespace, state: dict[str, Any], now: datetime, exc: Exception) -> dict[str, Any]:
    message = str(exc)[:500]
    return {
        "ok": False,
        "status": "failed",
        "reason": message,
        "should_notify": False,
        "notification_reasons": [],
        "telegram_message": None,
        "state_written": False,
        "output_written": False,
        "event_written": False,
        "dry_run": bool(args.dry_run),
    }


def build_run(args: argparse.Namespace, env: dict[str, str] | None = None) -> dict[str, Any]:
    env_map = env or os.environ
    now = parse_time(args.now) if args.now else utc_now()
    if now is None:
        raise AndonError(f"invalid --now timestamp: {args.now}")

    state = load_state(Path(args.state))
    if not env_enabled(env_map.get(ENV_FLAG)):
        return {
            "ok": True,
            "status": "skipped",
            "reason": "env_off",
            "should_notify": False,
            "notification_reasons": [],
            "telegram_message": None,
            "state_written": False,
            "output_written": False,
            "event_written": False,
            "dry_run": bool(args.dry_run),
        }

    try:
        payload = load_source_payload(Path(args.source_json))
        cities = [
            normalize_city_record(record)
            for record in payload.get("cities", [])
            if isinstance(record, dict) and record.get("city")
        ]
    except Exception as exc:
        return error_result(args, state, now, exc)

    prior_cities = state.get("cities") or {}
    events: list[dict[str, Any]] = []
    next_cities: dict[str, Any] = {}
    for city in cities:
        city_name = city["city"]
        previous = prior_cities.get(city_name)
        city_events = detect_city_events(city, previous)
        fingerprint = city_fingerprint(city)
        if city_events and fingerprint != (previous or {}).get("last_alert_fingerprint"):
            events.append({"city": city, "events": city_events, "fingerprint": fingerprint})
        city_state = compact_city_state(city)
        if city_events:
            city_state["last_alert_fingerprint"] = fingerprint
            city_state["last_alert_at"] = now.isoformat()
            city_state["last_alert_events"] = city_events
        else:
            city_state["last_alert_fingerprint"] = (previous or {}).get("last_alert_fingerprint")
            city_state["last_alert_at"] = (previous or {}).get("last_alert_at")
            city_state["last_alert_events"] = (previous or {}).get("last_alert_events")
        next_cities[city_name] = city_state

    notification_reasons = sorted({reason for event in events for reason in event["events"]})
    should_notify = bool(events)
    notify_sig = signature([{"city": e["city"]["city"], "events": e["events"], "fp": e["fingerprint"]} for e in events])
    telegram_message = build_telegram_message(events) if should_notify else None

    output = {
        "ok": True,
        "status": "completed",
        "reason": None,
        "generated_at": now.isoformat(),
        "source_generated_at": payload.get("generated_at"),
        "should_notify": should_notify,
        "notification_reasons": notification_reasons,
        "events": [
            {
                "city": event["city"]["city"],
                "events": event["events"],
                "primary_status": event["city"].get("primary_status"),
                "source_audit_status": event["city"].get("source_audit_status"),
                "priority_tier": event["city"].get("priority_tier"),
            }
            for event in events
        ],
        "telegram_message": telegram_message,
        "dry_run": bool(args.dry_run),
        "guardrails": {
            "log_only": True,
            "does_not_trade": True,
            "does_not_change_policy": True,
            "does_not_write_db": True,
            "not_a_trading_signal": True,
        },
    }

    next_state = dict(state)
    next_state.update(
        {
            "schema_version": SCHEMA_VERSION,
            "last_success_at": now.isoformat(),
            "last_source_generated_at": payload.get("generated_at"),
            "cities": next_cities,
        }
    )
    if should_notify:
        next_state["last_notification_at"] = now.isoformat()
        next_state["last_notification_signature"] = notify_sig

    event_written = False
    if not args.dry_run:
        write_json(Path(args.state), next_state)
        write_json(Path(args.output), output)
        if should_notify:
            append_event(Path(args.agent_events), build_event(now, events, True))
            event_written = True

    output["state_written"] = not args.dry_run
    output["output_written"] = not args.dry_run
    output["event_written"] = event_written
    return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Source Onboarding Andon LOG_ONLY monitor.")
    parser.add_argument("--source-json", default=str(DEFAULT_SOURCE_JSON))
    parser.add_argument("--state", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--agent-events", default=str(DEFAULT_AGENT_EVENTS_PATH))
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
            "source_onboarding_andon "
            f"status={result.get('status')} "
            f"reason={result.get('reason') or 'none'} "
            f"notify={str(result.get('should_notify')).lower()}"
        )
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
