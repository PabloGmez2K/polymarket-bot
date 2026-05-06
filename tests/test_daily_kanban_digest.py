from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
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
        "pnl_sources",
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


def test_cycles_history_timestamp_utc_counts_recent_cycles():
    module = load_tool_module()
    generated_at = datetime(2026, 5, 6, 7, 35, tzinfo=timezone.utc)
    cycle_rows = [
        {
            "cycle_number": 257,
            "timestamp_utc": "2026-05-06T07:29:25.720830+00:00",
            "bot_version": "v-test",
            "mode": "DRY_RUN",
        }
    ]
    original_load_json = module.load_json
    original_load_jsonl = module.load_jsonl

    def fake_load_json(path):
        return None

    def fake_load_jsonl(path, limit=500):
        if path.name == "cycles_history.jsonl":
            return cycle_rows
        return []

    module.load_json = fake_load_json
    module.load_jsonl = fake_load_jsonl

    try:
        operational = module.summarize_operational(MISSING_DATA_DIR, generated_at)
        activity = module.summarize_activity(MISSING_DATA_DIR, generated_at)
    finally:
        module.load_json = original_load_json
        module.load_jsonl = original_load_jsonl

    assert operational["recent_cycles_24h"] > 0
    assert activity["recent_cycles_7d"] > 0


def test_contaminated_lifecycle_marks_profitability_untrusted():
    module = load_tool_module()
    generated_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
    lifecycle = {
        "records": [
            {
                "status": "closed",
                "pnl_cash": 17.91,
                "closed_at": "2026-05-06T10:00:00+00:00",
                "integrity": {
                    "partial_historical_record": True,
                    "analysis_ready": False,
                },
                "history_sources": {"reconstructed": True},
                "decision_source": "postmortem_sync",
                "close_only_record": True,
            }
        ]
    }
    original_load_json = module.load_json

    def fake_load_json(path):
        if path.name == "trade_lifecycle.json":
            return lifecycle
        return None

    module.load_json = fake_load_json

    try:
        profitability = module.summarize_profitability(MISSING_DATA_DIR, generated_at)
    finally:
        module.load_json = original_load_json

    quality = profitability["source_quality"]
    assert quality["status"] == "contaminated"
    assert quality["closed_records"] == 1
    assert quality["contaminated_records"] == 1
    assert profitability["level"] == "WATCH_RISK"
    assert "no usar para BANKROLL ni decisiones operativas" in quality["warning"]


def test_contaminated_source_quality_visible_in_json_and_human_output():
    module = load_tool_module()
    lifecycle = {
        "records": [
            {
                "status": "closed",
                "pnl_cash": 17.91,
                "closed_at": "2026-05-06T10:00:00+00:00",
                "integrity": {"analysis_ready": False},
            }
        ]
    }
    cycle_rows = [{"timestamp_utc": "2026-05-06T11:00:00+00:00"}]
    fixed_now = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
    original_load_json = module.load_json
    original_load_jsonl = module.load_jsonl
    original_now_utc = module.now_utc

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
    module.now_utc = lambda: fixed_now

    try:
        digest = module.build_digest(MISSING_DATA_DIR)
        human = module.format_human(digest)
    finally:
        module.load_json = original_load_json
        module.load_jsonl = original_load_jsonl
        module.now_utc = original_now_utc

    quality = digest["sections"]["profitability"]["source_quality"]
    assert digest["would_send"] is False
    assert quality["status"] == "contaminated"
    assert "no usar para BANKROLL ni decisiones operativas" in quality["warning"]
    assert "Calidad fuente" in human
    assert "contaminated" in human
    assert "P/L incluye registros reconstruidos/no audit-ready" in human

    forbidden = [
        "comprar",
        "vender",
        "BUY",
        "SELL",
        "SKIP real",
        "subir BANKROLL",
        "activar Fase C",
    ]
    serialized = json.dumps(digest, ensure_ascii=False) + "\n" + human
    for needle in forbidden:
        assert needle not in serialized


def test_pnl_sources_marks_policy_state_without_canonical_pnl():
    module = load_tool_module()
    lifecycle = {
        "records": [
            {
                "status": "closed",
                "pnl_cash": 17.91,
                "closed_at": "2026-05-06T10:00:00+00:00",
                "integrity": {"analysis_ready": False},
            },
            {
                "status": "closed",
                "pnl_cash": -1.0,
                "closed_at": "2026-05-05T10:00:00+00:00",
                "integrity": {"analysis_ready": False},
            },
        ]
    }
    snapshot_rows = [
        {
            "schema_version": 1,
            "snapshot_at": "2026-05-06T10:00:00+00:00",
            "api_ok": True,
            "total_value": 19.90,
        }
    ]
    fixed_now = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
    original_load_json = module.load_json
    original_load_jsonl = module.load_jsonl
    original_now_utc = module.now_utc

    def fake_load_json(path):
        if path.name == "trade_lifecycle.json":
            return lifecycle
        return None

    def fake_load_jsonl(path, limit=500):
        if path.name == "wallet_portfolio_snapshots.jsonl":
            return snapshot_rows
        return []

    module.load_json = fake_load_json
    module.load_jsonl = fake_load_jsonl
    module.now_utc = lambda: fixed_now

    try:
        digest = module.build_digest(MISSING_DATA_DIR)
        human = module.format_human(digest)
    finally:
        module.load_json = original_load_json
        module.load_jsonl = original_load_jsonl
        module.now_utc = original_now_utc

    pnl_sources = digest["pnl_sources"]
    assert pnl_sources["lifecycle"]["status"] == "contaminated"
    assert pnl_sources["lifecycle"]["closed_records"] == 2
    assert pnl_sources["lifecycle"]["contaminated_records"] == 2
    assert pnl_sources["lifecycle"]["contamination_rate"] == 1.0
    assert pnl_sources["lifecycle"]["operational_use"] == "untrusted_only"
    assert pnl_sources["wallet_pnl"]["status"] == "accumulating"
    assert pnl_sources["wallet_pnl"]["phase2_ready"] is False
    assert pnl_sources["wallet_pnl"]["phase2_ready_reason"] == "cash_flow_unknown"
    assert pnl_sources["wallet_pnl"]["valid_snapshots"] == 1
    assert pnl_sources["wallet_pnl"]["valid_snapshot_days"] == 1
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False
    assert pnl_sources["wallet_pnl"]["wallet_pnl_7d"] is None
    assert pnl_sources["cash_flows"]["status"] == "missing"
    assert pnl_sources["cash_flows"]["n_records"] == 0
    assert pnl_sources["dashboard"]["status"] == "manual_only"
    assert pnl_sources["dashboard"]["auto_extractor_authorized"] is False
    assert pnl_sources["canonical_source"] == "none"
    assert pnl_sources["bankroll_readiness"] == "blocked"
    assert "P/L Sources" in human
    assert "Canonical source: none" in human
    assert "BANKROLL ready: blocked" in human


def test_pnl_sources_cash_flows_present_but_wallet_still_needs_history():
    module = load_tool_module()
    snapshot_rows = [
        {
            "schema_version": 1,
            "snapshot_at": "2026-05-05T10:00:00+00:00",
            "api_ok": True,
            "total_value": 20.0,
        },
        {
            "schema_version": 1,
            "snapshot_at": "2026-05-06T10:00:00+00:00",
            "api_ok": True,
            "total_value": 21.0,
        },
    ]
    cash_flow_rows = [{"date": "2026-05-06", "type": "deposit", "amount": 0}]
    original_load_jsonl = module.load_jsonl

    class FakePath:
        def __init__(self, name: str):
            self.name = name

        def exists(self):
            return self.name in {"wallet_portfolio_snapshots.jsonl", "wallet_cash_flows.jsonl"}

    class FakeDataDir:
        def __truediv__(self, name: str):
            return FakePath(name)

    def fake_load_jsonl(path, limit=500):
        if path.name == "wallet_portfolio_snapshots.jsonl":
            return snapshot_rows
        if path.name == "wallet_cash_flows.jsonl":
            return cash_flow_rows
        return []

    module.load_jsonl = fake_load_jsonl

    try:
        cash_flows = module.summarize_cash_flows(FakeDataDir())
        wallet_pnl = module.summarize_wallet_pnl(FakeDataDir(), cash_flows)
    finally:
        module.load_jsonl = original_load_jsonl

    assert cash_flows["status"] == "present"
    assert cash_flows["n_records"] == 1
    assert wallet_pnl["status"] == "accumulating"
    assert wallet_pnl["phase2_ready"] is False
    assert wallet_pnl["phase2_ready_reason"] == "need_more_history"
    assert wallet_pnl["history_span_hours"] == 24.0
    assert wallet_pnl["wallet_pnl_available"] is False
    assert wallet_pnl["wallet_pnl_method"] == "insufficient_history"


def test_daily_digest_does_not_execute_wallet_snapshot_tool():
    source = TOOL_PATH.read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "wallet_snapshot.py" not in source
