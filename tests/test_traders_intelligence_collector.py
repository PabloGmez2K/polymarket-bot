from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "traders_intelligence_collector.py"


@contextmanager
def local_tmp_dir():
    path = REPO_ROOT / f"_tmp_traders_intelligence_collector_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_tool():
    spec = importlib.util.spec_from_file_location("traders_intelligence_collector", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(REPO_ROOT / "tools"))
        except ValueError:
            pass
    return module


def write_signals(path: Path, generated: str = "2026-05-08T12:00:00+00:00") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": generated,
        "signals": [
            {
                "trader": "Entire-Hood",
                "city": "Houston",
                "date": "2026-05-08",
                "condition": "range",
                "temp": 75,
                "unit": "F",
                "outcome": "YES",
                "match_key": "Houston|2026-05-08|range|75|F",
                "avg_price": 0.42,
                "cur_price": 0.55,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_args(module, tmp_dir: Path, *extra: str):
    signals = tmp_dir / "signals.json"
    write_signals(signals)
    return module.parse_args(
        [
            "--signals",
            str(signals),
            "--state",
            str(tmp_dir / "collector_state.json"),
            "--agent-events",
            str(tmp_dir / "agent_events.jsonl"),
            "--snapshot-dir",
            str(tmp_dir / "snapshots"),
            "--report-dir",
            str(tmp_dir / "reports"),
            "--audit-log",
            str(tmp_dir / "pseudo_lifecycle_runs.jsonl"),
            "--now",
            "2026-05-08T12:10:00+00:00",
            *extra,
        ]
    )


def test_env_off_default_skips_without_writes():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        args = build_args(module, tmp_dir)
        result = module.build_run(args, env={})

        assert result["status"] == "skipped"
        assert result["reason"] == "env_off"
        assert result["state_written"] is False
        assert not (tmp_dir / "collector_state.json").exists()
        assert not (tmp_dir / "agent_events.jsonl").exists()
        assert not (tmp_dir / "snapshots").exists()


def test_dry_run_does_not_write_snapshots_state_or_events():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        args = build_args(module, tmp_dir, "--dry-run")
        result = module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "ON"})

        assert result["status"] == "completed"
        assert result["dry_run"] is True
        assert result["snapshot_written"] is False
        assert result["state_written"] is False
        assert result["event_written"] is False
        assert not list((tmp_dir / "snapshots").glob("*.json"))
        assert not (tmp_dir / "collector_state.json").exists()
        assert not (tmp_dir / "agent_events.jsonl").exists()


def test_write_run_persists_state_event_and_snapshot():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        args = build_args(module, tmp_dir)
        result = module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "1"})

        assert result["status"] == "completed"
        assert result["snapshot_written"] is True
        assert json.loads((tmp_dir / "collector_state.json").read_text(encoding="utf-8"))["last_run_id"] == result["run_id"]
        event = json.loads((tmp_dir / "agent_events.jsonl").read_text(encoding="utf-8").strip())
        assert event["type"] == "traders_intelligence_collector_run"
        assert event["ok"] is True
        assert len(list((tmp_dir / "snapshots").glob("*.json"))) == 1


def test_cooldown_skips_without_duplicate_run():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        state = {
            "schema_version": module.SCHEMA_VERSION,
            "last_run_id": "prior",
            "last_snapshot_at": "2026-05-08T12:00:00+00:00",
            "last_signals_generated_at": "2026-05-08T11:00:00+00:00",
            "consecutive_failures": 0,
            "kill_switch_active": False,
        }
        (tmp_dir / "collector_state.json").write_text(json.dumps(state), encoding="utf-8")
        args = build_args(module, tmp_dir, "--cooldown-minutes", "30")
        result = module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "ON"})

        assert result["status"] == "skipped"
        assert result["reason"] == "cooldown_active"
        assert not (tmp_dir / "agent_events.jsonl").exists()
        assert not list((tmp_dir / "snapshots").glob("*.json"))


def test_unchanged_signals_skip_without_duplicate_run():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        state = {
            "schema_version": module.SCHEMA_VERSION,
            "last_run_id": "prior",
            "last_snapshot_at": "2026-05-08T10:00:00+00:00",
            "last_signals_generated_at": "2026-05-08T12:00:00+00:00",
            "consecutive_failures": 0,
            "kill_switch_active": False,
        }
        (tmp_dir / "collector_state.json").write_text(json.dumps(state), encoding="utf-8")
        args = build_args(module, tmp_dir, "--cooldown-minutes", "0")
        result = module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "ON"})

        assert result["status"] == "skipped"
        assert result["reason"] == "signals_unchanged"
        assert not list((tmp_dir / "snapshots").glob("*.json"))


def test_state_kill_switch_blocks_execution():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        state = {
            "schema_version": module.SCHEMA_VERSION,
            "last_run_id": "prior",
            "last_snapshot_at": "2026-05-08T10:00:00+00:00",
            "last_signals_generated_at": "2026-05-08T11:00:00+00:00",
            "consecutive_failures": 5,
            "kill_switch_active": True,
        }
        (tmp_dir / "collector_state.json").write_text(json.dumps(state), encoding="utf-8")
        args = build_args(module, tmp_dir, "--cooldown-minutes", "0")
        result = module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "ON"})

        assert result["status"] == "skipped"
        assert result["reason"] == "kill_switch_active"
        assert not list((tmp_dir / "snapshots").glob("*.json"))


def test_failure_limit_auto_enables_kill_switch(monkeypatch):
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        state = {
            "schema_version": module.SCHEMA_VERSION,
            "last_run_id": "prior",
            "last_snapshot_at": "2026-05-08T10:00:00+00:00",
            "last_signals_generated_at": "2026-05-08T11:00:00+00:00",
            "consecutive_failures": 4,
            "kill_switch_active": False,
        }
        (tmp_dir / "collector_state.json").write_text(json.dumps(state), encoding="utf-8")
        monkeypatch.setattr(module, "run_snapshot_tool", lambda *args, **kwargs: (_ for _ in ()).throw(module.CollectorError("boom")))
        args = build_args(module, tmp_dir, "--cooldown-minutes", "0", "--failure-limit", "5")

        try:
            module.build_run(args, env={"TRADERS_INTELLIGENCE_COLLECTOR": "ON"})
        except module.CollectorError:
            pass
        else:
            raise AssertionError("CollectorError was not raised")

        written_state = json.loads((tmp_dir / "collector_state.json").read_text(encoding="utf-8"))
        assert written_state["consecutive_failures"] == 5
        assert written_state["kill_switch_active"] is True
