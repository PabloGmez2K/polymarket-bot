from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def wallet_snapshots(
    start: datetime | None = None,
    count: int = 15,
    step_hours: int = 12,
    possible_deposit_at: datetime | None = None,
) -> list[dict]:
    start = start or datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        at = start + timedelta(hours=step_hours * index)
        row = {
            "schema_version": 1,
            "snapshot_at": at.isoformat().replace("+00:00", "Z"),
            "api_ok": True,
            "total_value": 100.0 + index,
        }
        if possible_deposit_at is not None and at == possible_deposit_at:
            row["possible_deposit"] = True
        rows.append(row)
    return rows


def cash_flow_row(
    start: datetime,
    end: datetime,
    flow_type: str = "no_cash_flow_attestation",
    **extra,
) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": extra.pop("entry_id", "WCF-20260508-0001"),
        "actor": extra.pop("actor", "pablo_manual"),
        "type": flow_type,
        "recorded_at": extra.pop("recorded_at", end.isoformat().replace("+00:00", "Z")),
        "period_start": start.isoformat().replace("+00:00", "Z"),
        "period_end": end.isoformat().replace("+00:00", "Z"),
    }
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        row["amount_usdc"] = extra.pop("amount_usdc", "0")
    row.update(extra)
    return row


def summarize_pnl_sources_for(module, data_dir: Path) -> dict:
    return module.summarize_pnl_sources(data_dir, module.build_source_quality([]))


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


def test_cash_flows_missing_keeps_wallet_pnl_blocked(tmp_path):
    module = load_tool_module()
    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "missing"
    assert pnl_sources["cash_flows"]["n_records"] == 0
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False
    assert pnl_sources["canonical_source"] == "none"
    assert pnl_sources["bankroll_readiness"] == "blocked"


def test_cash_flows_empty_unattested_does_not_unlock_wallet_pnl(tmp_path):
    module = load_tool_module()
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots())
    (tmp_path / "wallet_cash_flows.jsonl").write_text("", encoding="utf-8")

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "empty_unattested"
    assert pnl_sources["cash_flows"]["coverage_days_7d"] == 0
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_examples_only_are_rejected(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, end, entry_id="EXAMPLE-001"),
        cash_flow_row(start, end, entry_id="WCF-EXAMPLE-MARKER", marker="EXAMPLE_ONLY"),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)
    cash_flows = pnl_sources["cash_flows"]

    assert cash_flows["status"] == "rejected_examples_only"
    assert cash_flows["n_records_rejected"] >= 1
    assert "example_id" in cash_flows["rejection_reasons"]
    assert "example_marker" in cash_flows["rejection_reasons"]
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_schema_v1_legacy_is_invalid(tmp_path):
    module = load_tool_module()
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots())
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [{"date": "2026-05-06", "type": "deposit", "amount": 0}])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "invalid"
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_actor_mismatch_is_invalid(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, end, actor="not_pablo"),
    ])

    cash_flows = module.summarize_cash_flows(tmp_path)

    assert cash_flows["status"] == "invalid"
    assert "actor_mismatch" in cash_flows["rejection_reasons"]


def test_cash_flows_rejects_pure_date_periods(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    row = cash_flow_row(start, end)
    row["period_start"] = "2026-05-01"
    row["period_end"] = "2026-05-08"
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [row])

    cash_flows = module.summarize_cash_flows(tmp_path)

    assert cash_flows["status"] == "invalid"
    assert "period_format" in cash_flows["rejection_reasons"]


def test_cash_flows_three_day_attestation_is_partial(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(latest - timedelta(days=3), latest),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "attested_partial"
    assert pnl_sources["cash_flows"]["coverage_days_7d"] == 3
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_full_7d_attestation_unlocks_wallet_pnl_available(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, latest),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "attested_full_7d"
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is True
    assert pnl_sources["canonical_source"] == "none"
    assert pnl_sources["bankroll_readiness"] == "blocked"


def test_cash_flows_full_7d_with_unexplained_possible_deposit_is_unreconciled(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    possible_at = start + timedelta(days=3, hours=12)
    write_jsonl(
        tmp_path / "wallet_portfolio_snapshots.jsonl",
        wallet_snapshots(start=start, possible_deposit_at=possible_at),
    )
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, possible_at - timedelta(hours=12)),
        cash_flow_row(possible_at + timedelta(hours=12), latest, entry_id="WCF-20260508-0002"),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "unreconciled"
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_full_7d_with_pending_adjustment_review_is_unreconciled(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    review_at = start + timedelta(days=2)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, latest),
        cash_flow_row(
            review_at,
            review_at,
            flow_type="adjustment",
            entry_id="WCF-ADJ-REVIEW",
            review_required=True,
        ),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "unreconciled"
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_full_window_with_one_day_gap_is_partial(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, start + timedelta(days=3)),
        cash_flow_row(start + timedelta(days=4), latest, entry_id="WCF-20260508-0002"),
    ])

    pnl_sources = summarize_pnl_sources_for(module, tmp_path)

    assert pnl_sources["cash_flows"]["status"] == "attested_partial"
    assert pnl_sources["cash_flows"]["coverage_days_7d"] < 7
    assert pnl_sources["wallet_pnl"]["wallet_pnl_available"] is False


def test_cash_flows_valid_but_wallet_still_needs_history(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=1)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start, count=2, step_hours=24))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [
        cash_flow_row(latest - timedelta(days=7), latest),
    ])

    cash_flows = module.summarize_cash_flows(tmp_path)
    wallet_pnl = module.summarize_wallet_pnl(tmp_path, cash_flows)

    assert cash_flows["status"] == "attested_full_7d"
    assert cash_flows["n_records"] == 1
    assert wallet_pnl["status"] == "accumulating"
    assert wallet_pnl["phase2_ready"] is False
    assert wallet_pnl["phase2_ready_reason"] == "need_more_history"
    assert wallet_pnl["history_span_hours"] == 24.0
    assert wallet_pnl["wallet_pnl_available"] is False
    assert wallet_pnl["wallet_pnl_method"] == "insufficient_history"


def test_digest_would_send_stays_false_for_cash_flow_gate_states(tmp_path):
    module = load_tool_module()
    scenarios = [
        ("missing", None),
        ("empty_unattested", []),
        ("rejected_examples_only", "example"),
        ("attested_full_7d", "full"),
    ]

    for name, cash_fixture in scenarios:
        data_dir = tmp_path / name
        start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
        latest = start + timedelta(days=7)
        write_jsonl(data_dir / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
        if cash_fixture == []:
            data_dir.mkdir(parents=True, exist_ok=True)
            (data_dir / "wallet_cash_flows.jsonl").write_text("", encoding="utf-8")
        elif cash_fixture == "example":
            write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest, entry_id="EXAMPLE-001")])
        elif cash_fixture == "full":
            write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest)])

        digest = module.build_digest(data_dir)

        assert digest["would_send"] is False
        assert digest["pnl_sources"]["cash_flows"]["status"] == name


def test_daily_digest_does_not_execute_wallet_snapshot_tool():
    source = TOOL_PATH.read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "wallet_snapshot.py" not in source
