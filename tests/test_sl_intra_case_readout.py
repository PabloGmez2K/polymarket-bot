from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "sl_intra_case_readout.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("sl_intra_case_readout", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def create_case_data(data_dir: Path) -> None:
    write_json(
        data_dir / "trade_lifecycle.json",
        {
            "records": [
                {
                    "token_id": "tok-seoul-no",
                    "label": "Seoul 21C May12 NO",
                    "question": "Will the highest temperature in Seoul be 21C on May 12?",
                    "city": "Seoul",
                    "side": "NO",
                    "status": "closed",
                    "total_amount": 2.0,
                    "total_shares": 5.0,
                    "entry_context": {
                        "condition": "exact",
                        "price": 0.4,
                        "edge_pct": 12.5,
                        "trader_confirmed": True,
                    },
                    "close_context": {
                        "close_action": "RESOLVED_WIN",
                        "close_reason": "resolution",
                        "pnl_cash": 1.52,
                    },
                    "timeline": [{"action": "BUY"}],
                }
            ]
        },
    )
    write_json(
        data_dir / "sl_intra_hazard_monitor_audit.json",
        {
            "events": [
                {
                    "timestamp": "2026-05-12T05:00:00Z",
                    "token_id": "tok-seoul-no",
                    "city": "Seoul",
                    "outcome": "NO",
                    "title": "Will the highest temperature in Seoul be 21C on May 12?",
                    "tier": "deep",
                    "pct_pnl": -80.3,
                    "cur_price": 0.08,
                },
                {
                    "timestamp": "2026-05-12T05:30:00Z",
                    "token_id": "tok-seoul-no",
                    "city": "Seoul",
                    "outcome": "NO",
                    "title": "Will the highest temperature in Seoul be 21C on May 12?",
                    "tier": "terminal",
                    "pct_pnl": -86.0,
                    "cur_price": 0.06,
                },
            ]
        },
    )
    write_json(
        data_dir / "intra_reeval_state.json",
        {
            "shadow_log": {
                "triggers": [
                    {
                        "ts": "2026-05-12T04:59:26Z",
                        "token_id": "tok-seoul-no",
                        "city": "Seoul",
                        "side": "NO",
                        "cur_price": 0.08,
                        "pnl_pct": -80.3,
                        "entry_edge_pct": 12.5,
                        "fresh_edge_pct": -5.0,
                        "would_sell": True,
                    }
                ]
            }
        },
    )
    write_json(
        data_dir / "sl_intra_guard_audit.json",
        {
            "skips": [
                {
                    "token_id": "tok-seoul-no",
                    "city": "Seoul",
                    "outcome": "NO",
                    "pct_pnl_at_skip": -80.3,
                    "condition": "exact",
                    "days_ahead": 0,
                }
            ]
        },
    )
    write_jsonl(
        data_dir / "skip_log.jsonl",
        [
            {
                "token_id": "other",
                "city": "Seoul",
                "date_iso": "2026-05-12",
                "skip_reason": "condition_filtered",
                "question": "Will the highest temperature in Seoul be 21C on May 12?",
            }
        ],
    )


def test_build_report_unifies_lifecycle_hazard_and_intra_reeval(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    create_case_data(data_dir)
    module = load_tool_module()

    args = module.parse_args(
        [
            "--data-dir",
            str(data_dir),
            "--city",
            "Seoul",
            "--date",
            "2026-05-12",
            "--side",
            "NO",
        ]
    )
    report = module.build_report(args)

    assert report["status"] == "ok"
    assert report["case_count"] == 1
    case = report["cases"][0]
    assert case["token_id"] == "tok-seoul-no"
    assert case["condition"] == "exact"
    assert case["buy_count"] == 1
    assert case["avg_entry_price"] == 0.4
    assert case["hazard_tiers_detected"] == ["deep", "terminal"]
    assert case["max_drawdown_observed"] == -86.0
    assert case["intra_reeval"]["would_sell"] is True
    assert case["intra_reeval"]["edge_now_vs_entry"] == -17.5
    assert case["real_pnl_cash"] == 1.52
    assert case["real_pnl_pct"] == 76.0
    assert case["classification"] == "REEVAL_WOULD_SELL_BUT_FINAL_WIN"


def test_missing_optional_sources_degrade_to_warnings(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_json(
        data_dir / "trade_lifecycle.json",
        {
            "records": [
                {
                    "token_id": "tok-open",
                    "question": "Will the highest temperature in Singapore be 32C on May 12?",
                    "city": "Singapore",
                    "side": "NO",
                    "status": "open",
                    "entry_context": {"condition": "exact"},
                }
            ]
        },
    )
    module = load_tool_module()

    args = module.parse_args(["--data-dir", str(data_dir), "--token-id", "tok-open"])
    report = module.build_report(args)

    assert report["status"] == "ok"
    assert report["cases"][0]["classification"] == "STILL_OPEN"
    assert "intra_reeval_state.json:missing" in report["warnings"]
    assert "sl_intra_hazard_monitor_audit.json:missing" in report["warnings"]
    assert "sl_intra_guard_audit.json:missing" in report["warnings"]
    assert "skip_log.jsonl:missing" in report["warnings"]


def test_cli_markdown_output(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    create_case_data(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--data-dir",
            str(data_dir),
            "--token-id",
            "tok-seoul-no",
            "--markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# SL_intra Case Readout" in result.stdout
    assert "REEVAL_WOULD_SELL_BUT_FINAL_WIN" in result.stdout
    assert "LOG_ONLY readout" in result.stdout


def test_would_sell_before_final_loss_is_good_shadow(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_json(
        data_dir / "trade_lifecycle.json",
        {
            "records": [
                {
                    "token_id": "tok-loss",
                    "question": "Will the highest temperature in Seoul be 21C on May 12?",
                    "city": "Seoul",
                    "side": "NO",
                    "status": "closed",
                    "total_amount": 4.75,
                    "entry_context": {"condition": "exact", "edge_pct": 21.9},
                    "close_context": {
                        "close_action": "LOSS_TOTAL",
                        "close_reason": "micro_position_unsellable",
                        "pnl_cash": -2.34,
                    },
                }
            ]
        },
    )
    write_json(
        data_dir / "intra_reeval_state.json",
        {
            "shadow_log": {
                "triggers": [
                    {
                        "token_id": "tok-loss",
                        "city": "Seoul",
                        "cur_price": 0.12,
                        "fresh_edge_pct": -7.1,
                        "entry_edge_pct": 21.9,
                        "would_sell": True,
                    }
                ]
            }
        },
    )
    module = load_tool_module()

    args = module.parse_args(["--data-dir", str(data_dir), "--token-id", "tok-loss"])
    report = module.build_report(args)

    case = report["cases"][0]
    assert case["classification"] == "REEVAL_GOOD_SHADOW"
    assert case["real_pnl_pct"] == -49.3
