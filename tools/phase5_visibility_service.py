#!/usr/bin/env python3
"""Servicio periodico separado para la pipeline de visibilidad fase 5.

No toca el core del bot. Ejecuta `phase5_visibility_pipeline.py` en bucle,
durmiendo entre corridas para acumular evidencia temporal y disparar la alerta
Telegram cuando aparezca una coincidencia nueva Shanghai + Chicago.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = REPO_ROOT / "tools" / "phase5_visibility_pipeline.py"
SEED_DIR = REPO_ROOT / "seed_data" / "phase5"
SEED_FILES = (
    "city_watch_reinforced.json",
    "reference_trader_city_market_cross.json",
    "directional_trader_enrichment.json",
)


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_command(python_exe: str, args: argparse.Namespace) -> list[str]:
    command = [python_exe, str(PIPELINE_PATH)]
    if args.refresh_probe:
        command.append("--refresh-probe")
    if args.probe_limit is not None:
        command.extend(["--probe-limit", str(args.probe_limit)])
    if args.targets:
        command.extend(["--targets", args.targets])
    return command


def seed_baseline_inputs() -> None:
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename in SEED_FILES:
        source = SEED_DIR / filename
        target = data_dir / filename
        if target.exists() or not source.exists():
            continue
        shutil.copy2(source, target)
        print(
            f"[{utc_now()}] phase5-service: seeded {filename} into {target}",
            flush=True,
        )


def run_pipeline(command: list[str]) -> int:
    print(f"[{utc_now()}] phase5-service: running {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print(
        f"[{utc_now()}] phase5-service: pipeline exit_code={completed.returncode}",
        flush=True,
    )
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Servicio periodico para la pipeline de visibilidad fase 5."
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=int(os.getenv("PHASE5_INTERVAL_MINUTES", "180")),
        help="Minutos entre corridas. Default: env PHASE5_INTERVAL_MINUTES o 180.",
    )
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=int(os.getenv("PHASE5_PROBE_LIMIT", "20")),
        help="Numero de mercados que refresca el probe. Default: env PHASE5_PROBE_LIMIT o 20.",
    )
    parser.add_argument(
        "--targets",
        default=os.getenv("PHASE5_TARGETS", "Shanghai,Chicago"),
        help="Ciudades objetivo para tracker/comparador.",
    )
    parser.add_argument(
        "--refresh-probe",
        action="store_true",
        default=parse_bool(os.getenv("PHASE5_REFRESH_PROBE"), True),
        help="Refresca settlement_fidelity_probe antes de la pipeline.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecuta una sola corrida y sale.",
    )
    args = parser.parse_args()

    if args.interval_minutes <= 0:
        raise SystemExit("--interval-minutes debe ser > 0")

    python_exe = sys.executable or "python"
    seed_baseline_inputs()
    command = build_command(python_exe, args)

    try:
        while True:
            exit_code = run_pipeline(command)
            if args.once:
                return exit_code
            sleep_seconds = args.interval_minutes * 60
            print(
                f"[{utc_now()}] phase5-service: sleeping {sleep_seconds}s",
                flush=True,
            )
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        print(f"[{utc_now()}] phase5-service: interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
