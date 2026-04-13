#!/usr/bin/env python3
"""Daily Railway service for the 07:00 UTC city intelligence summary."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / "tools" / "city_intelligence_daily_summary.py"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    return utc_now().isoformat(timespec="seconds")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Servicio diario Railway para el resumen city intelligence."
    )
    parser.add_argument(
        "--summary-hour-utc",
        type=int,
        default=int(os.getenv("CITY_INTELLIGENCE_DAILY_HOUR_UTC", "7")),
        help="Hora UTC del resumen diario. Default: env CITY_INTELLIGENCE_DAILY_HOUR_UTC o 7.",
    )
    parser.add_argument("--once", action="store_true", help="Ejecuta una sola vez y sale.")
    return parser.parse_args()


def next_daily_run(target_hour_utc: int) -> datetime:
    now = utc_now()
    candidate = now.replace(hour=target_hour_utc, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


def run_summary(python_exe: str) -> int:
    command = [python_exe, str(SUMMARY_PATH)]
    print(f"[{utc_now_str()}] city-intelligence-daily: running {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print(
        f"[{utc_now_str()}] city-intelligence-daily: summary exit_code={completed.returncode}",
        flush=True,
    )
    return int(completed.returncode)


def main() -> int:
    args = parse_args()
    if not 0 <= args.summary_hour_utc <= 23:
        raise SystemExit("--summary-hour-utc debe estar entre 0 y 23")

    python_exe = sys.executable or "python"

    try:
        while True:
            if not args.once:
                scheduled = next_daily_run(args.summary_hour_utc)
                sleep_seconds = max(0, int((scheduled - utc_now()).total_seconds()))
                if sleep_seconds > 0:
                    print(
                        f"[{utc_now_str()}] city-intelligence-daily: sleeping until {scheduled.isoformat(timespec='seconds')}",
                        flush=True,
                    )
                    time.sleep(sleep_seconds)
            exit_code = run_summary(python_exe)
            if args.once:
                return exit_code
    except KeyboardInterrupt:
        print(f"[{utc_now_str()}] city-intelligence-daily: interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
