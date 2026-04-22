#!/usr/bin/env python3
"""Export a local read-only runtime_import snapshot from the bot data volume."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path(os.getenv("DATA_DIR", REPO_ROOT / "data"))
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "runtime_import"
MANIFEST_NAME = "runtime_import_manifest.json"

DEFAULT_FILES = [
    "shadow_city_tracking.json",
    "cycles_history.jsonl",
    "cycle_summary.json",
    "decisions.log",
    "performance.json",
    "postmortem.json",
    "skip_log.jsonl",
    "trade_lifecycle.json",
    "audit.json",
    "city_policy_state.json",
    "signals.json",
]

REQUIRED_FILES = {
    "shadow_city_tracking.json",
    "audit.json",
    "city_policy_state.json",
}

POLICY_ENV_VARS = [
    "ACTIVE_TRADING_CITIES",
    "CANARY_TRADING_CITIES",
    "BLOCKED_CITIES",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create data/runtime_import from files already present in DATA_DIR."
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source-service", default="polymarket-bot-local")
    parser.add_argument("--remote-data-dir", default="/app/data")
    return parser.parse_args()


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    parent_dir = output_dir.parent
    tmp_dir = parent_dir / f"_{output_dir.name}.tmp.{uuid.uuid4().hex}"
    backup_dir = parent_dir / f"_{output_dir.name}.previous.{uuid.uuid4().hex}"

    if not data_dir.exists():
        raise SystemExit(f"DATA_DIR does not exist: {data_dir}")
    if output_dir == data_dir or data_dir in output_dir.parents:
        # Supported: DATA_DIR=/app/data and output=/app/data/runtime_import.
        pass

    parent_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "source_service": args.source_service,
        "remote_data_dir": args.remote_data_dir,
        "output_dir": rel_path(output_dir),
        "files": [],
    }

    try:
        missing_required = []
        for name in DEFAULT_FILES:
            if "/" in name or "\\" in name:
                raise SystemExit(f"Invalid file name: {name}")
            source_path = data_dir / name
            if not source_path.exists():
                if name in REQUIRED_FILES:
                    missing_required.append(name)
                continue
            if not source_path.is_file():
                continue

            target_path = tmp_dir / name
            shutil.copyfile(source_path, target_path)
            item = target_path.stat()
            manifest["files"].append({
                "name": name,
                "remote_path": f"{args.remote_data_dir}/{name}",
                "local_path": str((output_dir / name).resolve()),
                "bytes": item.st_size,
            })

        if missing_required:
            raise SystemExit(f"Missing required runtime files: {', '.join(missing_required)}")

        policy_snapshot = {
            "pulled_at": datetime.now(timezone.utc).isoformat(),
            "source_service": args.source_service,
            "variables": {name: os.getenv(name) for name in POLICY_ENV_VARS},
        }
        policy_path = tmp_dir / "policy_env_snapshot.json"
        write_json(policy_path, policy_snapshot)
        manifest["files"].append({
            "name": "policy_env_snapshot.json",
            "remote_path": "process:environment",
            "local_path": str((output_dir / "policy_env_snapshot.json").resolve()),
            "bytes": policy_path.stat().st_size,
        })

        expected = sorted(item["name"] for item in manifest["files"])
        actual = sorted(path.name for path in tmp_dir.iterdir() if path.is_file())
        if expected != actual:
            raise SystemExit(f"Manifest drift in temp snapshot. expected={expected} actual={actual}")

        write_json(tmp_dir / MANIFEST_NAME, manifest)

        if output_dir.exists():
            shutil.move(str(output_dir), str(backup_dir))
        try:
            shutil.move(str(tmp_dir), str(output_dir))
        except PermissionError:
            output_dir.mkdir(parents=True, exist_ok=True)
            for child in tmp_dir.iterdir():
                if child.is_file():
                    shutil.copyfile(child, output_dir / child.name)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception:
        if backup_dir.exists() and not output_dir.exists():
            shutil.move(str(backup_dir), str(output_dir))
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    print(f"Runtime import exported to {output_dir}")
    print(f"Manifest written to {output_dir / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
