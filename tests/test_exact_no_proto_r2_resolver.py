"""
Tests for tools/exact_no_proto_r2_resolver.py (Proto-R2 LOG_ONLY resolver).

Coverage:
  T1  settled_mature: resolved + old date → correct bucket and unit pnl
  T2  resolved_fresh: resolved + recent date → fresh bucket, pnl=None
  T3  pending: not settled → pending bucket, outcome=None
  T4  BSR mismatch resolved=True → abort, no output written
  T5  dedup: entry_edge = first, max_edge = metadata only, count tracked
  T6  idempotency: re-run overwrites, same row count
  T7  calibration_gap_component is null if p_model_no missing
  T8  output row always has calibration_audit_only=True
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.exact_no_proto_r2_resolver import (
    bsr_no_would_win,
    calibration_gap_component,
    classify_bucket,
    cross_check_bsr,
    dedup_groups,
    determine_settlement,
    simulated_unit_pnl,
    resolve,
    load_bsr,
)

TODAY = date(2026, 6, 1)
MATURE_DATE = "2026-05-20"   # 12 days ago → >= T7
FRESH_DATE = "2026-05-30"    # 2 days ago → < T7
FUTURE_DATE = "2026-06-02"   # future → pending


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_source_row(
    eval_key: str = "Tokyo|2026-05-20|exact|25|C",
    market_id: str = "111",
    condition_id: str = "0xabc",
    date_iso: str = MATURE_DATE,
    ts_utc: str = "2026-05-20T10:00:00+00:00",
    our_prob_no: float = 0.85,
    mkt_prob_no: float = 0.79,
    best_edge_pct_log_only: float = 7.0,
) -> dict:
    return {
        "schema_version": 1,
        "ts_utc": ts_utc,
        "eval_key": eval_key,
        "market_id": market_id,
        "condition_id": condition_id,
        "city": eval_key.split("|")[0],
        "date_iso": date_iso,
        "condition": "exact",
        "threshold": int(eval_key.split("|")[3]) if len(eval_key.split("|")) > 3 else 25,
        "unit": "C",
        "best_side_log_only": "NO",
        "best_edge_pct_log_only": best_edge_pct_log_only,
        "our_prob_no": our_prob_no,
        "mkt_prob_no": mkt_prob_no,
    }


def _gamma_market(yes_price: float, no_price: float, end_date: str = "2026-05-21") -> dict:
    return {
        "outcomePrices": json.dumps([str(yes_price), str(no_price)]),
        "endDate": end_date,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------------------
# Unit tests (pure functions)
# ---------------------------------------------------------------------------

class TestDetermineSettlement:
    def test_no_wins(self):
        market = _gamma_market(yes_price=0.02, no_price=0.98)
        settled, yes_p, no_p, _ = determine_settlement(market)
        assert settled is True
        assert no_p >= 0.95

    def test_yes_wins(self):
        market = _gamma_market(yes_price=0.97, no_price=0.03)
        settled, yes_p, no_p, _ = determine_settlement(market)
        assert settled is True

    def test_unsettled(self):
        market = _gamma_market(yes_price=0.55, no_price=0.45)
        settled, _, _, _ = determine_settlement(market)
        assert settled is False

    def test_none_market(self):
        settled, _, _, _ = determine_settlement(None)
        assert settled is False


class TestClassifyBucket:
    def test_mature(self):
        assert classify_bucket(MATURE_DATE, True, TODAY) == "settled_mature"

    def test_fresh(self):
        assert classify_bucket(FRESH_DATE, True, TODAY) == "resolved_fresh"

    def test_pending_unsettled(self):
        assert classify_bucket(MATURE_DATE, False, TODAY) == "pending"

    def test_pending_future(self):
        assert classify_bucket(FUTURE_DATE, True, TODAY) == "pending"


class TestSimulatedPnl:
    def test_win(self):
        pnl = simulated_unit_pnl(True, 0.79)
        assert abs(pnl - (1.0 - 0.79)) < 1e-9

    def test_loss(self):
        pnl = simulated_unit_pnl(False, 0.79)
        assert abs(pnl - (-0.79)) < 1e-9

    def test_null_if_no_outcome(self):
        assert simulated_unit_pnl(None, 0.79) is None

    def test_null_if_no_price(self):
        assert simulated_unit_pnl(True, None) is None


class TestCalibrationGap:
    def test_win(self):
        gap = calibration_gap_component(0.85, True)
        assert abs(gap - (0.85 - 1.0)) < 1e-6

    def test_loss(self):
        gap = calibration_gap_component(0.85, False)
        assert abs(gap - 0.85) < 1e-6

    def test_null_if_missing_model(self):
        assert calibration_gap_component(None, True) is None

    def test_null_if_missing_outcome(self):
        assert calibration_gap_component(0.85, None) is None


class TestBsrNoWouldWin:
    def test_trader_bet_no_and_won(self):
        row = {"outcome": "No", "win_for_trader": True}
        assert bsr_no_would_win(row) is True

    def test_trader_bet_no_and_lost(self):
        row = {"outcome": "No", "win_for_trader": False}
        assert bsr_no_would_win(row) is False

    def test_trader_bet_yes_and_won(self):
        # Yes won → No lost
        row = {"outcome": "Yes", "win_for_trader": True}
        assert bsr_no_would_win(row) is False

    def test_trader_bet_yes_and_lost(self):
        # Yes lost → No won
        row = {"outcome": "Yes", "win_for_trader": False}
        assert bsr_no_would_win(row) is True


class TestCrossCheckBsr:
    def test_no_entry_in_bsr(self):
        ok, msg = cross_check_bsr("Tokyo|2026-05-20|exact|25|C", True, {})
        assert ok is True
        assert msg is None

    def test_match_agrees(self):
        bsr_index = {
            "Tokyo|2026-05-20|exact|25|C": {"outcome": "No", "win_for_trader": True}
        }
        ok, msg = cross_check_bsr("Tokyo|2026-05-20|exact|25|C", True, bsr_index)
        assert ok is True

    def test_mismatch_triggers_abort(self):
        bsr_index = {
            "Tokyo|2026-05-20|exact|25|C": {"outcome": "No", "win_for_trader": False}
        }
        ok, msg = cross_check_bsr("Tokyo|2026-05-20|exact|25|C", True, bsr_index)
        assert ok is False
        assert "MISMATCH" in msg


class TestDedup:
    def test_single_row(self):
        rows = [_make_source_row(market_id="1", eval_key="A|2026-05-20|exact|25|C")]
        groups = dedup_groups(rows)
        assert len(groups) == 1
        assert groups[0]["_duplicate_count"] == 1

    def test_dedup_uses_first_edge(self):
        rows = [
            _make_source_row(
                market_id="1",
                eval_key="A|2026-05-20|exact|25|C",
                ts_utc="2026-05-20T10:00:00+00:00",
                best_edge_pct_log_only=5.0,
            ),
            _make_source_row(
                market_id="1",
                eval_key="A|2026-05-20|exact|25|C",
                ts_utc="2026-05-20T12:00:00+00:00",
                best_edge_pct_log_only=9.0,
            ),
        ]
        groups = dedup_groups(rows)
        assert len(groups) == 1
        g = groups[0]
        assert g["_entry_edge"] == 5.0   # first capture
        assert g["_max_edge"] == 9.0     # metadata only
        assert g["_duplicate_count"] == 2

    def test_distinct_eval_keys_not_merged(self):
        rows = [
            _make_source_row(market_id="1", eval_key="A|2026-05-20|exact|25|C"),
            _make_source_row(market_id="2", eval_key="B|2026-05-20|exact|26|C"),
        ]
        groups = dedup_groups(rows)
        assert len(groups) == 2


# ---------------------------------------------------------------------------
# Integration tests (resolve() with mocked Gamma API)
# ---------------------------------------------------------------------------

class TestResolveIntegration:

    def _run(self, source_rows, bsr_rows, gamma_markets, today=TODAY):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "source.jsonl"
            bsr = tmp_path / "bsr.jsonl"
            out = tmp_path / "output.jsonl"

            _write_jsonl(src, source_rows)
            _write_jsonl(bsr, bsr_rows)

            def fake_fetch(market_id):
                return gamma_markets.get(market_id)

            with patch(
                "tools.exact_no_proto_r2_resolver.fetch_market_by_id",
                side_effect=fake_fetch,
            ):
                summary = resolve(src, bsr, out, today=today)

            out_rows = []
            if out.exists():
                with open(out, encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            out_rows.append(json.loads(line))

            return summary, out_rows

    # T1 — settled_mature
    def test_settled_mature(self):
        source = [_make_source_row(date_iso=MATURE_DATE, market_id="111", mkt_prob_no=0.79)]
        gamma = {"111": _gamma_market(yes_price=0.02, no_price=0.98)}
        summary, rows = self._run(source, [], gamma)

        assert summary["n_settled_mature"] == 1
        assert summary["n_resolved_fresh"] == 0
        assert summary["n_pending"] == 0
        assert len(rows) == 1
        row = rows[0]
        assert row["bucket"] == "settled_mature"
        assert row["no_would_win"] is True
        assert row["calibration_audit_only"] is True
        assert row["settlement_mature_t7"] is True
        # pnl = 1 - 0.79
        assert abs(row["simulated_unit_pnl"] - (1.0 - 0.79)) < 1e-6
        assert summary["settled_mature"]["WR_NO"] == 1.0

    # T2 — resolved_fresh
    def test_resolved_fresh(self):
        source = [_make_source_row(date_iso=FRESH_DATE, market_id="222", mkt_prob_no=0.72)]
        gamma = {"222": _gamma_market(yes_price=0.03, no_price=0.97)}
        summary, rows = self._run(source, [], gamma)

        assert summary["n_resolved_fresh"] == 1
        assert summary["n_settled_mature"] == 0
        row = rows[0]
        assert row["bucket"] == "resolved_fresh"
        assert row["simulated_unit_pnl"] is None   # fresh → no pnl
        assert row["calibration_gap_component"] is None

    # T3 — pending (not settled)
    def test_pending_not_settled(self):
        source = [_make_source_row(date_iso=MATURE_DATE, market_id="333")]
        gamma = {"333": _gamma_market(yes_price=0.55, no_price=0.45)}
        summary, rows = self._run(source, [], gamma)

        assert summary["n_pending"] == 1
        row = rows[0]
        assert row["bucket"] == "pending"
        assert row["market_outcome"] is None
        assert row["no_would_win"] is None

    # T4 — BSR mismatch → abort, no output
    def test_bsr_mismatch_aborts(self):
        eval_key = "Tokyo|2026-05-20|exact|25|C"
        source = [_make_source_row(
            eval_key=eval_key, date_iso=MATURE_DATE, market_id="444"
        )]
        # BSR says: trader bet No and LOST (i.e., NO lost = YES won)
        bsr = [{"match_key": eval_key, "outcome": "No", "win_for_trader": False, "resolved": True}]
        # Gamma says: NO wins
        gamma = {"444": _gamma_market(yes_price=0.02, no_price=0.98)}

        with pytest.raises(SystemExit) as exc_info:
            self._run(source, bsr, gamma)
        assert exc_info.value.code == 2

    # T5 — dedup uses first edge, max_edge only metadata
    def test_dedup_entry_vs_max_edge(self):
        eval_key = "Seoul|2026-05-20|exact|26|C"
        source = [
            _make_source_row(
                eval_key=eval_key, market_id="555", date_iso=MATURE_DATE,
                ts_utc="2026-05-20T08:00:00+00:00", best_edge_pct_log_only=5.0,
            ),
            _make_source_row(
                eval_key=eval_key, market_id="555", date_iso=MATURE_DATE,
                ts_utc="2026-05-20T12:00:00+00:00", best_edge_pct_log_only=12.0,
            ),
        ]
        gamma = {"555": _gamma_market(yes_price=0.02, no_price=0.98)}
        summary, rows = self._run(source, [], gamma)

        assert len(rows) == 1
        row = rows[0]
        assert row["entry_edge_log_only"] == 5.0    # first
        assert row["max_edge_log_only"] == 12.0     # metadata
        assert row["duplicate_count"] == 2

    # T6 — idempotency: re-run overwrites, same row count
    def test_idempotency(self):
        source = [_make_source_row(date_iso=MATURE_DATE, market_id="666")]
        gamma = {"666": _gamma_market(yes_price=0.02, no_price=0.98)}

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "source.jsonl"
            bsr = tmp_path / "bsr.jsonl"
            out = tmp_path / "output.jsonl"

            _write_jsonl(src, source)
            _write_jsonl(bsr, [])

            def fake_fetch(market_id):
                return gamma.get(market_id)

            with patch(
                "tools.exact_no_proto_r2_resolver.fetch_market_by_id",
                side_effect=fake_fetch,
            ):
                resolve(src, bsr, out, today=TODAY)
                resolve(src, bsr, out, today=TODAY)

            with open(out, encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh if l.strip()]
            assert len(rows) == 1

    # T7 — calibration_gap is null if p_model_no is missing
    def test_calibration_gap_null_if_no_model_prob(self):
        src_row = _make_source_row(date_iso=MATURE_DATE, market_id="777")
        src_row["our_prob_no"] = None
        gamma = {"777": _gamma_market(yes_price=0.02, no_price=0.98)}
        _, rows = self._run([src_row], [], gamma)

        assert rows[0]["calibration_gap_component"] is None

    # T8 — output row always has calibration_audit_only=True
    def test_calibration_audit_only_flag(self):
        source = [_make_source_row(date_iso=MATURE_DATE, market_id="888")]
        gamma = {"888": _gamma_market(yes_price=0.97, no_price=0.03)}
        _, rows = self._run(source, [], gamma)

        assert rows[0]["calibration_audit_only"] is True
        assert rows[0]["source_artifact"] == "exact_no_qt_match_evaluations_log_only.jsonl"
