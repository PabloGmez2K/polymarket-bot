#!/usr/bin/env python3
"""Unified Railway service for city intelligence intraday pipeline and daily summary."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = REPO_ROOT / "tools" / "city_intelligence_pipeline.py"
DAILY_SUMMARY_PATH = REPO_ROOT / "tools" / "city_intelligence_daily_summary.py"
CENSUS_PATH = REPO_ROOT / "data" / "directional_trader_census.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    return utc_now().isoformat(timespec="seconds")


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def parse_hours(raw: str) -> list[int]:
    hours = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            hours.append(hour)
    return sorted(set(hours))


def next_hour_event(hours: list[int], now: datetime) -> datetime:
    for hour in hours:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hours[0], minute=0, second=0, microsecond=0)


def run_command(command: list[str], label: str) -> int:
    print(f"[{utc_now_str()}] {label}: running {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print(f"[{utc_now_str()}] {label}: exit_code={completed.returncode}", flush=True)
    return int(completed.returncode)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Servicio Railway unificado para city intelligence."
    )
    parser.add_argument(
        "--pipeline-hours-utc",
        default=os.getenv("CITY_INTELLIGENCE_ALIGN_UTC_HOURS", "0,6,12,18"),
        help="Horas UTC para el pipeline intradia.",
    )
    parser.add_argument(
        "--daily-hour-utc",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_DAILY_HOUR_UTC", "7")),
        help="Hora UTC del resumen diario.",
    )
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_PROBE_LIMIT", "12")),
    )
    parser.add_argument(
        "--census-markets",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_CENSUS_MARKETS", "200")),
    )
    parser.add_argument(
        "--exploratory-targets",
        default=os.getenv("CITY_INTELLIGENCE_EXPLORATORY_TARGETS", os.getenv("CITY_INTELLIGENCE_TARGETS", "Chicago")),
    )
    parser.add_argument("--tracker-targets", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--refresh-probe",
        action="store_true",
        default=parse_bool(os.getenv("CITY_INTELLIGENCE_REFRESH_PROBE"), True),
    )
    parser.add_argument(
        "--refresh-census",
        action="store_true",
        default=parse_bool(os.getenv("CITY_INTELLIGENCE_REFRESH_CENSUS"), False),
    )
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def should_refresh_census(args: argparse.Namespace) -> bool:
    if args.refresh_census:
        return True
    if CENSUS_PATH.exists():
        return False
    print(
        f"[{utc_now_str()}] city-intelligence-railway: missing {CENSUS_PATH.name}; forcing --refresh-census for bootstrap",
        flush=True,
    )
    return True


def build_pipeline_command(
    python_exe: str,
    args: argparse.Namespace,
    refresh_census: bool | None = None,
) -> list[str]:
    effective_refresh_census = should_refresh_census(args) if refresh_census is None else refresh_census
    command = [python_exe, str(PIPELINE_PATH)]
    if args.refresh_probe:
        command.append("--refresh-probe")
    if effective_refresh_census:
        command.append("--refresh-census")
    command.extend(["--probe-limit", str(args.probe_limit)])
    command.extend(["--census-markets", str(args.census_markets)])
    exploratory_targets = args.exploratory_targets or args.tracker_targets or ""
    if exploratory_targets:
        command.extend(["--exploratory-targets", exploratory_targets])
    return command


def build_daily_command(python_exe: str) -> list[str]:
    return [python_exe, str(DAILY_SUMMARY_PATH)]


def next_event_time(pipeline_hours: list[int], daily_hour: int, now: datetime) -> tuple[str, datetime]:
    pipeline_next = next_hour_event(pipeline_hours, now)
    daily_next = next_hour_event([daily_hour], now)
    if daily_next <= pipeline_next:
        return "daily", daily_next
    return "pipeline", pipeline_next


def main() -> int:
    args = parse_args()
    if not 0 <= args.daily_hour_utc <= 23:
        raise SystemExit("--daily-hour-utc debe estar entre 0 y 23")
    pipeline_hours = parse_hours(args.pipeline_hours_utc)
    if not pipeline_hours:
        raise SystemExit("--pipeline-hours-utc no contiene horas validas")

    python_exe = sys.executable or "python"
    daily_command = build_daily_command(python_exe)

    try:
        if args.once:
            pipeline_command = build_pipeline_command(python_exe, args)
            pipeline_code = run_command(pipeline_command, "city-intelligence-pipeline")
            daily_code = run_command(daily_command, "city-intelligence-daily")
            return pipeline_code or daily_code

        while True:
            event_name, scheduled = next_event_time(pipeline_hours, args.daily_hour_utc, utc_now())
            sleep_seconds = max(0, int((scheduled - utc_now()).total_seconds()))
            if sleep_seconds > 0:
                print(
                    f"[{utc_now_str()}] city-intelligence-railway: sleeping until {scheduled.isoformat(timespec='seconds')} for {event_name}",
                    flush=True,
                )
                time.sleep(sleep_seconds)

            if event_name == "pipeline":
                pipeline_command = build_pipeline_command(python_exe, args)
                run_command(pipeline_command, "city-intelligence-pipeline")
            else:
                run_command(daily_command, "city-intelligence-daily")
    except KeyboardInterrupt:
        print(f"[{utc_now_str()}] city-intelligence-railway: interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
