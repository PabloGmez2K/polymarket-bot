#!/usr/bin/env python3
"""Periodic Railway service for city intelligence pipeline."""

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Servicio periodico Railway para city intelligence."
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_INTERVAL_MINUTES", "360")),
        help="Minutos entre corridas. Default: env CITY_INTELLIGENCE_INTERVAL_MINUTES o 360.",
    )
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_PROBE_LIMIT", "12")),
        help="Limite para settlement_fidelity_probe cuando se refresca.",
    )
    parser.add_argument(
        "--census-markets",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_CENSUS_MARKETS", "200")),
        help="Numero de mercados para el refresh del censo.",
    )
    parser.add_argument(
        "--exploratory-targets",
        default=os.getenv("CITY_INTELLIGENCE_EXPLORATORY_TARGETS", os.getenv("CITY_INTELLIGENCE_TARGETS", "Chicago")),
        help="Ciudades exploratorias explicitas; las runtime-derived salen de runtime_policy_effective_view.",
    )
    parser.add_argument("--tracker-targets", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--refresh-probe",
        action="store_true",
        default=parse_bool(os.getenv("CITY_INTELLIGENCE_REFRESH_PROBE"), True),
        help="Refresca settlement_fidelity_probe antes de la pipeline.",
    )
    parser.add_argument(
        "--refresh-census",
        action="store_true",
        default=parse_bool(os.getenv("CITY_INTELLIGENCE_REFRESH_CENSUS"), False),
        help="Refresca directional_trader_census antes de la pipeline.",
    )
    parser.add_argument(
        "--align-utc-hours",
        default=os.getenv("CITY_INTELLIGENCE_ALIGN_UTC_HOURS", "0,6,12,18"),
        help="Horas UTC alineadas para correr. Si se define, prioriza estas horas sobre interval-minutes.",
    )
    parser.add_argument("--once", action="store_true", help="Ejecuta una sola corrida y sale.")
    return parser.parse_args()


def next_aligned_run(raw_hours: str) -> datetime:
    hours = []
    for part in raw_hours.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            hours.append(hour)
    hours = sorted(set(hours))
    now = utc_now()
    if not hours:
        return now
    for hour in hours:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hours[0], minute=0, second=0, microsecond=0)


def build_command(python_exe: str, args: argparse.Namespace) -> list[str]:
    command = [python_exe, str(PIPELINE_PATH)]
    if args.refresh_probe:
        command.append("--refresh-probe")
    if args.refresh_census:
        command.append("--refresh-census")
    if args.probe_limit is not None:
        command.extend(["--probe-limit", str(args.probe_limit)])
    if args.census_markets is not None:
        command.extend(["--census-markets", str(args.census_markets)])
    exploratory_targets = args.exploratory_targets or args.tracker_targets
    if exploratory_targets:
        command.extend(["--exploratory-targets", exploratory_targets])
    return command


def run_pipeline(command: list[str]) -> int:
    print(f"[{utc_now_str()}] city-intelligence-service: running {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print(
        f"[{utc_now_str()}] city-intelligence-service: pipeline exit_code={completed.returncode}",
        flush=True,
    )
    return int(completed.returncode)


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0:
        raise SystemExit("--interval-minutes debe ser > 0")

    python_exe = sys.executable or "python"
    command = build_command(python_exe, args)
    first_iteration = True

    try:
        while True:
            if not args.once:
                if not first_iteration:
                    if args.align_utc_hours:
                        scheduled = next_aligned_run(args.align_utc_hours)
                        sleep_seconds = max(0, int((scheduled - utc_now()).total_seconds()))
                        if sleep_seconds > 0:
                            print(
                                f"[{utc_now_str()}] city-intelligence-service: sleeping until {scheduled.isoformat(timespec='seconds')}",
                                flush=True,
                            )
                            time.sleep(sleep_seconds)
                    else:
                        print(
                            f"[{utc_now_str()}] city-intelligence-service: sleeping {args.interval_minutes * 60}s",
                            flush=True,
                        )
                        time.sleep(args.interval_minutes * 60)

            exit_code = run_pipeline(command)
            first_iteration = False
            if args.once:
                return exit_code
    except KeyboardInterrupt:
        print(f"[{utc_now_str()}] city-intelligence-service: interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
