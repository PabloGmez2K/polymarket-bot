from __future__ import annotations

import json

import trader_analyzer


def test_generate_signals_file_adds_forward_only_wr_provenance(monkeypatch, tmp_path):
    target = tmp_path / "signals.json"
    monkeypatch.setattr(trader_analyzer, "SIGNALS_FILE", str(target))

    output = trader_analyzer.generate_signals_file(
        [
            {
                "name": "Quality-Trader",
                "is_reference": False,
                "win_rate": 81.0,
                "wins": 30,
                "losses": 7,
                "pnl_closed": 12.5,
                "signals": [
                    {
                        "trader": "Quality-Trader",
                        "match_key": "Reykjavik|2026-05-05|exact|7|C",
                        "outcome": "Yes",
                        "avg_price": 0.42,
                    }
                ],
            }
        ],
        consensus={},
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    signal = payload["signals"][0]

    assert output["generated"] == output["signals_generated_at"]
    assert payload["signals_generated_at"] == payload["generated"]
    assert signal["signals_generated_at"] == payload["generated"]
    assert signal["trader_win_rate"] == 81.0
    assert signal["trader_win_rate_source"] == "polymarket_data_api_closed_positions_cashPnl"
    assert signal["trader_win_rate_closed_positions_count"] == 37
    assert signal["trader_win_rate_asof_method"] == "snapshot_at_signals_generation_no_entry_cutoff"
    assert signal["trader_win_rate_cutoff_at"] == "unknown"
    assert signal["trader_win_rate_leakage_status"] == "not_auditable_no_entry_or_closed_position_cutoff"
