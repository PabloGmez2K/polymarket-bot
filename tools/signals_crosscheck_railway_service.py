#!/usr/bin/env python3
"""Railway loop for automated trader-vs-bot crosscheck ingestion and daily summary."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / "tools" / "signals_crosscheck_daily_summary.py"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    return utc_now().isoformat(timespec="seconds")


def next_hour_event(hour: int, now: datetime) -> datetime:
    candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate > now:
        return candidate
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)


def run_command(command: list[str], label: str) -> int:
    print(f"[{utc_now_str()}] {label}: running {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print(f"[{utc_now_str()}] {label}: exit_code={completed.returncode}", flush=True)
    return int(completed.returncode)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Servicio Railway diario para resumir el cross-check traders vs bot."
    )
    parser.add_argument(
        "--daily-hour-utc",
        type=int,
        default=int(os.getenv("SIGNALS_CROSSCHECK_DAILY_HOUR_UTC", "9")),
        help="Hora UTC del resumen diario.",
    )
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def build_summary_command(python_exe: str) -> list[str]:
    return [python_exe, str(SUMMARY_PATH), "--ingest-if-missing-today"]


def main() -> int:
    args = parse_args()
    if not 0 <= args.daily_hour_utc <= 23:
        raise SystemExit("--daily-hour-utc debe estar entre 0 y 23")

    python_exe = sys.executable or "python"
    summary_command = build_summary_command(python_exe)

    try:
        if args.once:
            return run_command(summary_command, "signals-crosscheck-daily")

        while True:
            scheduled = next_hour_event(args.daily_hour_utc, utc_now())
            sleep_seconds = max(0, int((scheduled - utc_now()).total_seconds()))
            if sleep_seconds > 0:
                print(
                    f"[{utc_now_str()}] signals-crosscheck-railway: sleeping until {scheduled.isoformat(timespec='seconds')}",
                    flush=True,
                )
                time.sleep(sleep_seconds)
            run_command(summary_command, "signals-crosscheck-daily")
    except KeyboardInterrupt:
        print(f"[{utc_now_str()}] signals-crosscheck-railway: interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
