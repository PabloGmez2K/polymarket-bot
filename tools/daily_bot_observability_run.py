#!/usr/bin/env python3
"""Run the local daily leaderboard snapshot + digest observability flow.

This runner is local-only. It can write the leaderboard JSONL snapshot when
explicitly requested. Telegram delivery is manual-only behind an explicit flag;
it never touches runtime state, DB, Railway, scheduler, or trading code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import daily_bot_digest
import db_throughput_report
import leaderboard_pnl_snapshot

try:
    import cohort_intelligence_report as _cohort
    _COHORT_AVAILABLE = True
except Exception:
    _cohort = None  # type: ignore[assignment]
    _COHORT_AVAILABLE = False

try:
    import traders_activity_profile as _tap
    _TAP_AVAILABLE = True
except Exception:
    _tap = None  # type: ignore[assignment]
    _TAP_AVAILABLE = False


DEFAULT_SNAPSHOT_PATH = leaderboard_pnl_snapshot.DEFAULT_SNAPSHOT_PATH
DEFAULT_DB_PATH = Path("data") / "polymarket.db"
TRADERS_ACTIVITY_SNAPSHOT_DIR = Path("data") / "traders_intelligence" / "activity_snapshots"
# Cover the full operational cohort (traders_db.json + traders_intelligence.json).
# At 44 wallets × 2 sides × ~850ms/call = ~75s, safely within the 120s bot.py timeout.
TRADERS_ACTIVITY_MAX_WALLETS = 50
TRADERS_ACTIVITY_MAX_FILLS_PER_WALLET = 100


class RunnerError(Exception):
    pass


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def snapshot_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        wallet=args.wallet,
        env_file=args.env_file,
        user=args.user,
        dashboard_1d=None,
        dashboard_1w=None,
        dashboard_1m=None,
        dashboard_1y=None,
        dashboard_captured_at=None,
    )


def existing_rows(path: Path) -> list[dict[str, Any]]:
    try:
        return leaderboard_pnl_snapshot.read_snapshots(path)
    except leaderboard_pnl_snapshot.SnapshotError as exc:
        raise RunnerError(str(exc)) from exc


def summarize_db_throughput(report: dict[str, Any]) -> dict[str, Any]:
    cycles = report.get("cycles") or {}
    markets = report.get("markets") or {}
    freshness = cycles.get("freshness") or {}
    by_slot = cycles.get("by_slot_utc") or []
    weak_slots = [
        {
            "slot_label": row.get("slot_label"),
            "slot_utc": row.get("slot_utc"),
            "cycles": row.get("cycles", 0),
            "markets_evaluated": row.get("markets_evaluated", 0),
            "buys": row.get("buys", 0),
        }
        for row in sorted(by_slot, key=lambda item: (item.get("buys", 0), -item.get("markets_evaluated", 0)))
        if row.get("markets_evaluated", 0) and row.get("buys", 0) == 0
    ][:3]
    condition_distribution = markets.get("condition_distribution") or {}
    condition_total = sum(int(value or 0) for value in condition_distribution.values())
    dominant_condition = "unknown"
    dominant_condition_count = 0
    if condition_distribution:
        dominant_condition, dominant_condition_count = max(
            condition_distribution.items(),
            key=lambda item: int(item[1] or 0),
        )
    bottlenecks = report.get("top_bottlenecks") or []
    gap_count = len(cycles.get("gaps") or [])
    status = "KEEP"
    suggested_action = "Mantener observacion; no hay accion operativa."
    if report.get("status") != "ok" or not freshness.get("is_fresh") or gap_count:
        status = "WATCH"
        suggested_action = "Revision manual de frescura/gaps antes de interpretar throughput."
    if weak_slots or any(item.get("severity") == "WATCH_RISK" for item in bottlenecks):
        status = "REVIEW_READY"
        suggested_action = "Revision manual; si toca estrategia, llevar a Opus antes de cambiar nada."
    return {
        "mode": "LOG_ONLY",
        "db_status": report.get("status"),
        "source_quality": (report.get("source_quality") or {}).get("status"),
        "fresh": bool(freshness.get("is_fresh")),
        "hours_ago": freshness.get("hours_ago"),
        "gap_count": gap_count,
        "weak_slots": weak_slots,
        "dominant_condition": dominant_condition,
        "dominant_condition_count": int(dominant_condition_count or 0),
        "condition_total": condition_total,
        "review_status": status,
        "suggested_action": suggested_action,
    }


def build_db_throughput_summary(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.db_throughput_report:
        return None
    report = db_throughput_report.build_report(args.db)
    return summarize_db_throughput(report)


def build_traders_activity_summary(args: argparse.Namespace) -> dict[str, Any]:
    """Run traders activity profile for local-registry cohort. Always fail-open."""
    if not getattr(args, "traders_activity_profile", False):
        return {"ok": False, "error": "disabled"}
    if not _TAP_AVAILABLE or _tap is None:
        return {"ok": False, "error": "module_not_available"}
    snapshot_dir = str(TRADERS_ACTIVITY_SNAPSHOT_DIR)
    try:
        profile_args = _tap.parse_args([
            "--cohort", "local-registry",
            "--max-wallets", str(TRADERS_ACTIVITY_MAX_WALLETS),
            "--max-fills-per-wallet", str(TRADERS_ACTIVITY_MAX_FILLS_PER_WALLET),
            "--snapshot-dir", snapshot_dir,
        ])
        payload = _tap.build_payload(profile_args)
        if getattr(args, "write_snapshot", False):
            _tap.write_snapshot(payload, snapshot_dir)
        summary = payload.get("summary", {})
        traders = payload.get("traders", [])
        cohort_meta = payload.get("cohort", {})
        failures = [t for t in traders if t.get("query_status") == "failed"]
        comparable = [
            t.get("alias") or t["wallet"][:10]
            for t in traders
            if t.get("lane_suggestion") == "COMPARABLE_CANDIDATE"
        ]
        return {
            "ok": True,
            "generated_at": payload.get("generated_at"),
            "cohort_mode": cohort_meta.get("cohort_mode"),
            "cohort_warning": cohort_meta.get("cohort_warning"),
            "n_wallets": summary.get("n_wallets", 0),
            "lane_counts": summary.get("lane_counts", {}),
            "query_status_counts": summary.get("query_status_counts", {}),
            "capped_wallets": summary.get("capped_wallets", 0),
            "n_failures": len(failures),
            "comparable_candidates": comparable,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def build_cohort_intelligence_summary(args: argparse.Namespace) -> dict[str, Any]:
    """Build cohort intelligence summary. Fail-open; LOG_ONLY only."""
    if not getattr(args, "cohort_intelligence", True):
        return {"ok": False, "error": "disabled"}
    if not _COHORT_AVAILABLE or _cohort is None:
        return {"ok": False, "error": "module_not_available"}
    try:
        data_dir = Path(args.cohort_data_dir)
        report = _cohort.build_report(data_dir=data_dir)
        return {
            "ok": True,
            "generated_at": report.get("generated_at"),
            "main_cohorts": report.get("main_cohorts", []),
            "live_side_visibility_forward": report.get("live_side_visibility_forward", {}),
            "surviving_cohorts_by_side": report.get("surviving_cohorts_by_side", []),
            "best_directional_no_subcohort": report.get("best_directional_no_subcohort"),
            "summary_verdicts": report.get("summary_verdicts", {}),
            "directional_no_next_trigger": report.get("directional_no_next_trigger", {}),
            "directional_forward_capture": report.get("directional_forward_capture", {}),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def render_cohort_intelligence_telegram(summary: dict[str, Any]) -> str:
    """Render compact cohort intelligence section for Telegram."""
    error = summary.get("error", "")
    if not summary.get("ok"):
        if error == "disabled":
            return ""
        return (
            "\n\n<b>Cohort Intelligence (LOG_ONLY)</b>"
            f"\nError: <code>{str(error)[:120]}</code>"
        )

    def fmt_pct(value: Any) -> str:
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return "n/a"

    def fmt_money(value: Any) -> str:
        try:
            return f"{float(value):+.2f}"
        except (TypeError, ValueError):
            return "n/a"

    rows = {row.get("cohort"): row for row in summary.get("main_cohorts", [])}
    near = rows.get("exact/NO near-threshold", {})
    far = rows.get("exact/NO far", {})
    directional = rows.get("directional NO", {})
    best = summary.get("best_directional_no_subcohort") or {}
    verdicts = summary.get("summary_verdicts", {})
    trigger = summary.get("directional_no_next_trigger", {})
    forward = summary.get("directional_forward_capture", {})
    side_forward = summary.get("live_side_visibility_forward", {})
    surviving = summary.get("surviving_cohorts_by_side", [])
    lines = [
        "",
        "<b>Cohort Intelligence (LOG_ONLY)</b>",
        (
            "exact/NO near: "
            f"raw={near.get('n_closed_raw', near.get('n_closed', 0))} "
            f"cal={near.get('n_closed_calibration_unique', near.get('n_closed', 0))} "
            f"exec={near.get('n_executed_trades_unique', 0)} "
            f"WR={fmt_pct(near.get('wr_calibration', near.get('wr_observed')))} "
            f"gap={fmt_pct(near.get('calibration_gap'))} "
            f"sim={fmt_money(near.get('pnl_simulated_unit_calibration', near.get('pnl_simulated_unit')))} "
            f"real={fmt_money(near.get('pnl_real_reported_noncanonical'))} "
            f"-> {near.get('decision_verdict', near.get('verdict', 'INSUFFICIENT_SAMPLE'))}"
        ),
        (
            "exact/NO far: "
            f"raw={far.get('n_closed_raw', far.get('n_closed', 0))} "
            f"cal={far.get('n_closed_calibration_unique', far.get('n_closed', 0))} "
            f"exec={far.get('n_executed_trades_unique', 0)} "
            f"WR={fmt_pct(far.get('wr_calibration', far.get('wr_observed')))} "
            f"gap={fmt_pct(far.get('calibration_gap'))} "
            f"sim={fmt_money(far.get('pnl_simulated_unit_calibration', far.get('pnl_simulated_unit')))} "
            f"real={fmt_money(far.get('pnl_real_reported_noncanonical'))} "
            f"-> {far.get('decision_verdict', far.get('verdict', 'INSUFFICIENT_SAMPLE'))}"
        ),
        (
            "directional NO: "
            f"raw={directional.get('n_closed_raw', directional.get('n_closed', 0))} "
            f"cal={directional.get('n_closed_calibration_unique', directional.get('n_closed', 0))} "
            f"exec={directional.get('n_executed_trades_unique', 0)} "
            f"WR={fmt_pct(directional.get('wr_calibration', directional.get('wr_observed')))} "
            f"gap={fmt_pct(directional.get('calibration_gap'))} "
            f"sim={fmt_money(directional.get('pnl_simulated_unit_calibration', directional.get('pnl_simulated_unit')))} "
            f"real={fmt_money(directional.get('pnl_real_reported_noncanonical'))} "
            f"-> {directional.get('decision_verdict', directional.get('verdict', 'INSUFFICIENT_SAMPLE'))}"
        ),
    ]
    if best:
        lines.append(
            "best subcohort: "
            f"{best.get('cohort')} | cal={best.get('n_closed_calibration_unique', best.get('n_closed', 0))} "
            f"WR={fmt_pct(best.get('wr_calibration', best.get('wr_observed')))} "
            f"-> {best.get('decision_verdict', best.get('verdict', 'INSUFFICIENT_SAMPLE'))}"
        )
    lines.append(
        "verdicts: "
        f"exact_near_shadow={verdicts.get('EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED', 'INSUFFICIENT_SAMPLE')} | "
        f"directional_candidate={verdicts.get('DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND', 'INSUFFICIENT_SAMPLE')} | "
        f"opus_now={verdicts.get('OPUS_REVIEW_REQUIRED_NOW', 'NO')}"
    )
    lines.append(
        "directional forward: "
        f"seen={forward.get('directional_forward_seen', 0)} | "
        f"cal={forward.get('directional_forward_resolved_calibration_unique', 0)} | "
        f"{forward.get('status', 'CAPTURE_ACTIVE_NO_RESOLUTIONS_YET')}"
    )
    if surviving:
        compact_rows = []
        for row in surviving[:4]:
            compact_rows.append(
                f"{row.get('cohort')}/{row.get('city_mode')}: "
                f"eval={row.get('n_eval_forward', 0)} buy={row.get('n_would_buy', 0)} "
                f"sh={row.get('n_shadow', 0)} blk={row.get('n_blocked', 0)} "
                f"cal={row.get('n_resolved_calibration_unique', 0)} "
                f"-> {row.get('manual_review_state', 'ACCUMULATING_FORWARD_EVIDENCE')}"
            )
        lines.append("surviving by side: " + " | ".join(compact_rows))
    else:
        lines.append(
            "surviving by side: "
            f"start={side_forward.get('forward_visibility_start', 'n/a')} | "
            "no forward rows with recorded side yet"
        )
    lines.append(
        "trigger: Opus review only when directional NO forward linked outcomes reach CANDIDATE_FOR_CANARY_REVIEW; "
        f"missing_to_min_sample={trigger.get('resolutions_missing_for_min_sample', 0)}."
    )
    lines.append("Manual review only. No BUY/SELL/SKIP, BANKROLL, sizing, city modes, whitelist, env vars, or Fase C.")
    lines.append("Units: raw signals, calibration-unique outcomes, executed-trade P&L.")
    return "\n".join(lines)


def render_traders_activity_telegram(summary: dict[str, Any]) -> str:
    """Render compact traders activity section for Telegram. Returns empty string if disabled."""
    error = summary.get("error", "")
    if not summary.get("ok"):
        if error == "disabled":
            return ""
        return (
            "\n\n🔬 <b>Traders Activity (LOG_ONLY)</b>"
            f"\n⚠️ Error: <code>{error[:120]}</code>"
        )
    lanes = summary.get("lane_counts", {})
    comparable = summary.get("comparable_candidates", [])
    n_wallets = summary.get("n_wallets", 0)
    n_failures = summary.get("n_failures", 0)
    q_counts = summary.get("query_status_counts", {})
    ok_count = sum(v for k, v in q_counts.items() if k.startswith("ok_"))
    lines = [
        "",
        "🔬 <b>Traders Activity (LOG_ONLY)</b>",
        f"• Wallets: {n_wallets} | OK: {ok_count} | Fallos: {n_failures}",
    ]
    if lanes:
        lane_summary = ", ".join(f"{k}={v}" for k, v in sorted(lanes.items()))
        lines.append(f"• Lanes: {lane_summary}")
    if comparable:
        lines.append(f"• Comparable: {', '.join(comparable[:3])}")
    else:
        lines.append("• Comparable: ninguno provisional")
    if summary.get("cohort_warning"):
        lines.append("• ⚠️ local-registry: puede incluir wallets históricas, no solo activas.")
    lines.append("• LOG_ONLY. No BUY/SELL/SKIP. Revisar antes de usar.")
    return "\n".join(lines)


def build_run(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.snapshot_file)
    payload = leaderboard_pnl_snapshot.build_snapshot(snapshot_args(args))
    payload["runner_mode"] = "write_snapshot" if args.write_snapshot else "dry_run"
    payload["usable_for_bankroll"] = False
    payload["dashboard_equivalent"] = False
    payload["usable_for_digest"] = True
    payload["usable_for_trend"] = True

    written = False
    db_summary = build_db_throughput_summary(args)

    if args.write_snapshot:
        leaderboard_pnl_snapshot.append_snapshot(path, payload)
        written = True
        digest = daily_bot_digest.build_digest(path, db_throughput=db_summary)
    else:
        rows = existing_rows(path)
        temp_payload = dict(payload)
        temp_payload["temporary_snapshot"] = True
        digest = daily_bot_digest.build_digest_from_rows(rows + [temp_payload], path, db_throughput=db_summary)

    traders_activity = build_traders_activity_summary(args)
    traders_section = render_traders_activity_telegram(traders_activity)
    cohort_intelligence = build_cohort_intelligence_summary(args)
    cohort_section = render_cohort_intelligence_telegram(cohort_intelligence)
    extended_preview = (
        digest["telegram_preview"]
        + (cohort_section if cohort_section else "")
        + (traders_section if traders_section else "")
    )

    telegram_send_result = {"sent": False, "reason": "not_attempted"}
    if args.send_telegram_manual:
        telegram_send_result = daily_bot_digest.send_telegram_manual(extended_preview)

    return {
        "mode": "write_snapshot" if args.write_snapshot else "dry_run",
        "snapshot_file": str(path),
        "snapshot_written": written,
        "snapshot": payload,
        "query_status": payload.get("query_status", "unknown"),
        "source": "polymarket_leaderboard",
        "source_quality": "external_opaque",
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "db_throughput": db_summary,
        "cohort_intelligence": cohort_intelligence,
        "traders_activity": traders_activity,
        "decision": {
            "bankroll": "No BANKROLL increase.",
            "operational_use": "Observability only.",
            "trading": "No BUY/SELL/SKIP.",
            "fase_c": "No Fase C.",
        },
        "digest": digest,
        "message": render_run_message(
            digest,
            payload,
            written,
            args.telegram_preview or args.send_telegram_manual,
            telegram_send_result if args.send_telegram_manual else None,
            telegram_preview=extended_preview,
        ),
        "telegram_preview": extended_preview,
        "telegram_manual_send": telegram_send_result,
    }


def render_run_message(
    digest: dict[str, Any],
    snapshot: dict[str, Any],
    written: bool,
    include_telegram_preview: bool,
    telegram_send_result: dict[str, Any] | None = None,
    telegram_preview: str | None = None,
) -> str:
    preview = telegram_preview if telegram_preview is not None else digest["telegram_preview"]
    lines = [
        "DAILY BOT OBSERVABILITY RUN",
        f"snapshot_written={str(written).lower()}",
        f"query_status={snapshot.get('query_status', 'unknown')}",
        "source_quality=external_opaque",
        "dashboard_equivalent=false",
        "usable_for_digest=true",
        "usable_for_trend=true",
        "usable_for_bankroll=false",
        "Observability only.",
        "",
        digest["message"],
    ]
    if include_telegram_preview:
        heading = "TELEGRAM MANUAL SEND PREVIEW" if telegram_send_result is not None else "TELEGRAM PREVIEW ONLY"
        lines.extend(["", heading, preview])
    if telegram_send_result is not None:
        lines.extend(["", f"telegram_manual_send={telegram_send_result.get('reason')}"])
        if telegram_send_result.get("missing_env"):
            lines.append("missing_env=" + ",".join(telegram_send_result["missing_env"]))
        if telegram_send_result.get("error"):
            lines.append("telegram_error=" + str(telegram_send_result["error"]))
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily local snapshot + digest observability runner.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build a temporary snapshot and digest without writing JSONL.")
    mode.add_argument("--write-snapshot", action="store_true", help="Append a snapshot JSONL row before building the digest.")
    parser.add_argument("--telegram-preview", action="store_true", help="Print Telegram-ready preview text only; never sends.")
    parser.add_argument(
        "--send-telegram-manual",
        action="store_true",
        help="Manually send the Telegram digest after printing the preview. No scheduler or retries.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="Leaderboard snapshot JSONL path.")
    parser.add_argument(
        "--db-throughput-report",
        action="store_true",
        help="Append a brief read-only DB throughput section to the digest.",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path for --db-throughput-report.")
    parser.add_argument("--wallet", help="Manual wallet/proxy wallet override. Output only shows masked wallet.")
    parser.add_argument("--env-file", default=".env", help=argparse.SUPPRESS)
    parser.add_argument("--user", help="Optional manual user label override.")
    parser.add_argument(
        "--traders-activity-profile",
        action="store_true",
        help=(
            "Include a compact traders activity section (local-registry cohort, max "
            f"{TRADERS_ACTIVITY_MAX_WALLETS} wallets). LOG_ONLY. Fail-open."
        ),
    )
    parser.add_argument(
        "--cohort-intelligence",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include Cohort Intelligence Loop v1 in the daily digest. LOG_ONLY, fail-open.",
    )
    parser.add_argument(
        "--cohort-data-dir",
        default="data",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if not args.write_snapshot:
        args.dry_run = True
    return args


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv or sys.argv[1:])
    try:
        result = build_run(args)
    except (RunnerError, leaderboard_pnl_snapshot.SnapshotError, daily_bot_digest.DigestError) as exc:
        print(f"daily_bot_observability_run error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"daily_bot_observability_run unexpected error: {leaderboard_pnl_snapshot.compact_error(str(exc))}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.send_telegram_manual and result["telegram_manual_send"].get("reason") == "TELEGRAM_API_ERROR":
            return 2
        return 0
    print(result["message"])
    if args.send_telegram_manual and result["telegram_manual_send"].get("reason") == "TELEGRAM_API_ERROR":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
