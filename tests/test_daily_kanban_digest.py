from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "daily_kanban_digest.py"
MISSING_DATA_DIR = REPO_ROOT / "__missing_daily_kanban_fixture__"
MISSING_DB = REPO_ROOT / "__missing_daily_kanban_fixture__.db"


def run_cli(*args: str, data_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(TOOL_PATH), *args]
    if data_dir is not None:
        command.extend(["--data-dir", str(data_dir)])
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=30)


def load_tool_module():
    spec = importlib.util.spec_from_file_location("daily_kanban_digest", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_dry_run_text_exit_zero():
    result = run_cli("--dry-run", data_dir=MISSING_DATA_DIR)

    assert result.returncode == 0, result.stderr
    assert "Daily Bot Kanban Digest" in result.stdout
    assert "dry-run / LOG_ONLY / default OFF" in result.stdout
    assert "would_send: false" in result.stdout


def test_cli_json_dry_run_valid_json():
    result = run_cli("--json", "--dry-run", data_dir=MISSING_DATA_DIR)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["would_send"] is False
    assert payload["level"] in {
        "NO_ACTION",
        "WATCH",
        "WATCH_TECH",
        "WATCH_RISK",
        "ACTION_ANALYSIS",
        "ACTION_DESIGN",
        "ACTION_SAFETY",
    }
    assert set(payload) == {
        "generated_at_utc",
        "level",
        "sections",
        "next_step",
        "disclaimers",
        "would_send",
    }


def test_missing_local_data_does_not_crash():
    result = run_cli("--dry-run", data_dir=MISSING_DATA_DIR)

    assert result.returncode == 0, result.stderr
    assert "unknown" in result.stdout
    assert "data_missing" in result.stdout


def test_truth_pipeline_db_missing_controlled_status():
    result = run_cli(
        "--json",
        "--dry-run",
        "--db",
        str(MISSING_DB),
        data_dir=MISSING_DATA_DIR,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    truth = payload["sections"]["truth_pipeline"]
    assert truth["status"] in {"schema_missing", "unknown"}
    assert truth["truth_records"] is None


def test_message_contains_required_disclaimer_and_next_step():
    result = run_cli("--dry-run", data_dir=MISSING_DATA_DIR)

    assert "Esta alerta no autoriza cambios de trading." in result.stdout
    assert "Siguiente paso concreto" in result.stdout


def test_message_has_no_operational_instructions():
    result = run_cli("--dry-run", data_dir=MISSING_DATA_DIR)
    forbidden = [
        "comprar",
        "vender",
        "BUY",
        "SELL",
        "SKIP real",
        "subir BANKROLL",
        "activar Fase C",
    ]

    for needle in forbidden:
        assert needle not in result.stdout


def test_tool_does_not_import_bot_or_trading_core():
    source = TOOL_PATH.read_text(encoding="utf-8")

    assert "import bot" not in source
    assert "from bot" not in source
    assert "execute_trade" not in source
    assert "manage_positions" not in source
    assert "intra_cycle_sl_check" not in source


def test_tool_does_not_use_telegram():
    source = TOOL_PATH.read_text(encoding="utf-8")

    assert "send_telegram" not in source
    assert "api.telegram.org" not in source
    assert "TELEGRAM_TOKEN" not in source
    assert "TELEGRAM_CHAT_ID" not in source
    assert "urllib.request" not in source


def test_dry_run_does_not_write_state_files():
    assert not MISSING_DATA_DIR.exists()
    result = run_cli("--dry-run", data_dir=MISSING_DATA_DIR)

    assert result.returncode == 0, result.stderr
    assert not MISSING_DATA_DIR.exists()
    assert not (REPO_ROOT / "data" / "kanban_state.json").exists()


def test_build_digest_contract_with_fixture():
    data_dir = MISSING_DATA_DIR
    lifecycle = {
        "records": [
            {
                "status": "closed",
                "pnl_cash": 1.25,
                "closed_at": "2026-05-06T10:00:00+00:00",
                "opened_at": "2026-05-06T09:00:00+00:00",
                "side": "yes",
            },
            {"status": "open", "opened_at": "2026-05-06T11:00:00+00:00", "side": "no"},
        ]
    }
    cycle_rows = [{"ts_utc": "2026-05-06T12:00:00+00:00", "bot_version": "v-test", "mode": "DRY_RUN"}]
    module = load_tool_module()
    original_load_json = module.load_json
    original_load_jsonl = module.load_jsonl

    def fake_load_json(path):
        if path.name == "trade_lifecycle.json":
            return lifecycle
        return None

    def fake_load_jsonl(path, limit=500):
        if path.name == "cycles_history.jsonl":
            return cycle_rows
        return []

    module.load_json = fake_load_json
    module.load_jsonl = fake_load_jsonl

    try:
        digest = module.build_digest(data_dir)
    finally:
        module.load_json = original_load_json
        module.load_jsonl = original_load_jsonl

    assert digest["would_send"] is False
    assert digest["sections"]["profitability"]["windows"]["all"]["pnl"] == 1.25
    assert digest["sections"]["activity"]["open_positions"] == 1
