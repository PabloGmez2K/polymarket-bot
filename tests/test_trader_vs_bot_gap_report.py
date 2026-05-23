"""
Focal tests for tools/trader_vs_bot_gap_report.py.

Tests cover:
  - Classification logic (3 dimensions: win_for_trader x would_buy x exec_status)
  - actual_execution_status derivation from city_mode + reason_blocked
  - blocking_gate derivation
  - Honest join semantics: bot_eval_joined vs join_confidence (identity) vs summary counts
  - Temporal alignment status derivation
  - data_quality_flags including temporal_alignment_unverified
  - gates_passed / gates_missing including temporal_alignment_verified gate
  - v1 BSR rows -> NO_ACTION_INSUFFICIENT_EVIDENCE
  - Report structure and data_gaps
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from tools.trader_vs_bot_gap_report import (
    _classify_row,
    _derive_blocking_gate,
    _derive_execution_status,
    _gates_status,
    _temporal_alignment_status,
    build_report,
)


# ---------------------------------------------------------------------------
# _derive_execution_status
# ---------------------------------------------------------------------------

class TestDeriveExecutionStatus:
    def test_blocked_city(self):
        assert _derive_execution_status({"city_mode_at_record_time": "blocked"}) == "BLOCKED_POLICY"

    def test_shadow_city(self):
        assert _derive_execution_status({"city_mode_at_record_time": "shadow"}) == "SHADOW_ONLY"

    def test_active_with_source_reason(self):
        r = {"city_mode_at_record_time": "active", "reason_blocked": "source_fidelity"}
        assert _derive_execution_status(r) == "SOURCE_BLOCKED"

    def test_canary_with_source_reason(self):
        r = {"city_mode_at_record_time": "canary", "reason_blocked": "source_blocked"}
        assert _derive_execution_status(r) == "SOURCE_BLOCKED"

    def test_active_no_source(self):
        r = {"city_mode_at_record_time": "active", "reason_blocked": "condition_filtered"}
        assert _derive_execution_status(r) == "BLOCKED_POLICY"

    def test_missing_city_mode_returns_unknown(self):
        assert _derive_execution_status({}) == "UNKNOWN"

    def test_v1_no_fields_returns_unknown(self):
        r = {"city": "Tokyo", "match_key": "Tokyo|2026-04-10|exact|19|C"}
        assert _derive_execution_status(r) == "UNKNOWN"


# ---------------------------------------------------------------------------
# _derive_blocking_gate
# ---------------------------------------------------------------------------

class TestDeriveBlockingGate:
    def test_blocked_city_mode(self):
        assert _derive_blocking_gate({"city_mode_at_record_time": "blocked"}) == "city_mode"

    def test_shadow_city_mode(self):
        assert _derive_blocking_gate({"city_mode_at_record_time": "shadow"}) == "city_mode"

    def test_condition_filtered(self):
        r = {"city_mode_at_record_time": "active", "reason_blocked": "condition_filtered"}
        assert _derive_blocking_gate(r) == "condition_policy"

    def test_fuera_allowlist(self):
        r = {"city_mode_at_record_time": "active", "reason_blocked": "fuera_allowlist"}
        assert _derive_blocking_gate(r) == "condition_policy"

    def test_mixed_blocked_city_detail(self):
        r = {
            "city_mode_at_record_time": "blocked",
            "reason_blocked": "mixed",
            "block_reason_detail": "blocked_city+condition_filtered",
        }
        assert _derive_blocking_gate(r) == "city_mode"

    def test_none_mode_v1_returns_none(self):
        assert _derive_blocking_gate({"city": "London"}) is None


# ---------------------------------------------------------------------------
# _temporal_alignment_status
# ---------------------------------------------------------------------------

class TestTemporalAlignmentStatus:
    def test_not_available_when_no_bse(self):
        assert _temporal_alignment_status(None, "2026-05-22") == "NOT_AVAILABLE"

    def test_verified_when_bse_ts_before_market_date(self):
        bse = {"ts_utc": "2026-05-20T10:00:00+00:00"}
        assert _temporal_alignment_status(bse, "2026-05-22") == "VERIFIED"

    def test_unverified_when_bse_ts_same_day(self):
        bse = {"ts_utc": "2026-05-22T08:00:00+00:00"}
        assert _temporal_alignment_status(bse, "2026-05-22") == "UNVERIFIED"

    def test_unverified_when_bse_ts_after_market_date(self):
        bse = {"ts_utc": "2026-05-23T00:00:00+00:00"}
        assert _temporal_alignment_status(bse, "2026-05-22") == "UNVERIFIED"

    def test_unverified_when_no_ts(self):
        bse = {}
        assert _temporal_alignment_status(bse, "2026-05-22") == "UNVERIFIED"

    def test_unverified_when_no_market_date(self):
        bse = {"ts_utc": "2026-05-20T10:00:00+00:00"}
        assert _temporal_alignment_status(bse, None) == "UNVERIFIED"


# ---------------------------------------------------------------------------
# _classify_row
# ---------------------------------------------------------------------------

class TestClassifyRow:
    def test_candidate_missed_opportunity_blocked(self):
        assert _classify_row(True, True, "BLOCKED_POLICY") == "CANDIDATE_MISSED_OPPORTUNITY"

    def test_candidate_missed_opportunity_shadow(self):
        assert _classify_row(True, True, "SHADOW_ONLY") == "CANDIDATE_MISSED_OPPORTUNITY"

    def test_source_fidelity_blocked(self):
        assert _classify_row(True, True, "SOURCE_BLOCKED") == "SOURCE_FIDELITY_BLOCKED"

    def test_candidate_filtered_winner(self):
        assert _classify_row(True, False, "FILTERED_NO_EDGE") == "CANDIDATE_FILTERED_WINNER"

    def test_candidate_filtered_winner_any_exec(self):
        assert _classify_row(True, False, "BLOCKED_POLICY") == "CANDIDATE_FILTERED_WINNER"

    def test_protective_policy_evidence(self):
        assert _classify_row(False, True, "BLOCKED_POLICY") == "PROTECTIVE_POLICY_EVIDENCE"

    def test_protective_policy_evidence_shadow(self):
        assert _classify_row(False, True, "SHADOW_ONLY") == "PROTECTIVE_POLICY_EVIDENCE"

    def test_protective_filter_evidence(self):
        assert _classify_row(False, False, "FILTERED_NO_EDGE") == "PROTECTIVE_FILTER_EVIDENCE"

    def test_no_action_unknown_exec(self):
        assert _classify_row(True, True, "UNKNOWN") == "NO_ACTION_INSUFFICIENT_EVIDENCE"

    def test_no_action_unknown_would_buy(self):
        assert _classify_row(True, None, "BLOCKED_POLICY") == "NO_ACTION_INSUFFICIENT_EVIDENCE"

    def test_no_action_unknown_win(self):
        assert _classify_row(None, True, "BLOCKED_POLICY") == "NO_ACTION_INSUFFICIENT_EVIDENCE"

    def test_no_action_trader_won_bot_buy_but_wrong_exec(self):
        # exec_status FILTERED_NO_EDGE + would_buy=True is contradictory; no action
        assert _classify_row(True, True, "FILTERED_NO_EDGE") == "NO_ACTION_INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# _gates_status
# ---------------------------------------------------------------------------

class TestGatesStatus:
    def _row(self, **kw):
        defaults = {
            "join_confidence": "MEDIUM",
            "actual_execution_status": "BLOCKED_POLICY",
            "bot_eval_joined": True,
            "temporal_alignment_status": "VERIFIED",
            "data_quality_flags": [],
        }
        defaults.update(kw)
        return defaults

    def _bsr(self, **kw):
        defaults = {"resolved": True, "win_for_trader": True, "price_bucket": "0.4-0.6"}
        defaults.update(kw)
        return defaults

    def _bse(self, **kw):
        defaults = {"would_buy": True}
        defaults.update(kw)
        return defaults

    def test_all_gates_passed(self):
        row = self._row()
        bsr = self._bsr()
        bse = self._bse()
        passed, missing = _gates_status(row, bsr, bse)
        assert "identity_joinable" in passed
        assert "outcome_resolved" in passed
        assert "execution_status_known" in passed
        assert "counterfactual_estimable" in passed
        assert "temporal_alignment_verified" in passed
        assert "no_blocking_data_quality" in passed
        assert not missing

    def test_gate1_fails_low_confidence(self):
        row = self._row(join_confidence="NONE")
        passed, missing = _gates_status(row, self._bsr(), self._bse())
        assert "identity_joinable" in missing

    def test_gate5_fails_no_bse_join(self):
        row = self._row(bot_eval_joined=False)
        passed, missing = _gates_status(row, self._bsr(), None)
        assert "counterfactual_estimable" in missing

    def test_gate5b_fails_unverified_temporal(self):
        row = self._row(temporal_alignment_status="UNVERIFIED",
                        data_quality_flags=["temporal_alignment_unverified"])
        passed, missing = _gates_status(row, self._bsr(), self._bse())
        assert "temporal_alignment_verified" in missing
        assert "no_blocking_data_quality" in missing

    def test_gate5b_fails_not_available_temporal(self):
        row = self._row(temporal_alignment_status="NOT_AVAILABLE", bot_eval_joined=False)
        passed, missing = _gates_status(row, self._bsr(), None)
        assert "temporal_alignment_verified" in missing

    def test_gate6_fails_blocking_dq(self):
        row = self._row(data_quality_flags=["settlement_fidelity_unknown"])
        passed, missing = _gates_status(row, self._bsr(), self._bse())
        assert "no_blocking_data_quality" in missing


# ---------------------------------------------------------------------------
# build_report integration
# ---------------------------------------------------------------------------

def _write_jsonl(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


BSE_ROW_CONDITION_FILTERED = {
    "schema_version": 1,
    "ts_utc": "2026-05-20T10:00:00+00:00",
    "cycle_id": "2026-05-20T10:00",
    "eval_key": "Istanbul|2026-05-22|exact|18|C",
    "city": "Istanbul",
    "date_iso": "2026-05-22",
    "condition": "exact",
    "threshold": 18,
    "threshold_high": None,
    "unit": "C",
    "would_buy": False,
    "bot_edge_pct_at_signal": None,
    "evaluation_source": "live_eval",
    "skip_or_block_reason": "condition_filtered",
    "decision_gate": "condition_filtered",
    "decision_confidence": None,
    "our_prob": None,
    "mkt_prob": None,
    "days_ahead": 2,
}

BSR_V3_SHADOW = {
    "schema_version": 3,
    "canonical_signal_id": "Istanbul|2026-05-22|exact|18|C|Yes|Entire-Hood",
    "checked_at": "2026-05-23T00:01:15+00:00",
    "match_key": "Istanbul|2026-05-22|exact|18|C",
    "city": "Istanbul",
    "date": "2026-05-22",
    "condition": "exact",
    "trader": "Entire-Hood",
    "trader_historical_wr": 84.0,
    "outcome": "Yes",
    "avg_price_entered": 0.5473,
    "close_price": 1.0,
    "resolved": True,
    "win_for_trader": True,
    "has_consensus": False,
    "market_id": "2309524",
    "condition_id": "0xec23386e5e91c329",
    "city_mode_at_record_time": "shadow",
    "reason_blocked": "condition_filtered",
    "block_reason_detail": "condition=exact fuera de ALLOWED_CONDITIONS",
    "resolution_source": "polymarket_market_price",
    "settlement_fidelity_status": "unverified",
    "bot_edge_pct_at_signal": None,
    "bot_would_have_bought": False,
    "bot_evaluation_source": "unknown",
    "bot_evaluation_join_status": "missing",
    "price_bucket": "0.4-0.6",
}

BSR_V1_LEGACY = {
    "checked_at": "2026-04-13T15:35:49+00:00",
    "match_key": "Ankara|2026-04-08|exact|9|C",
    "city": "Ankara",
    "date": "2026-04-08",
    "condition": "exact",
    "trader": "Loyal-Aggression",
    "trader_historical_wr": 95.0,
    "outcome": "Yes",
    "avg_price_entered": 0.33,
    "close_price": 1.0,
    "resolved": True,
    "win_for_trader": True,
    "has_consensus": False,
}


class TestBuildReport:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

    def _paths(self):
        return (
            os.path.join(self.tmp, "bot_signal_evaluations.jsonl"),
            os.path.join(self.tmp, "blocked_signals_resolutions.jsonl"),
            os.path.join(self.tmp, "signals_crosscheck.jsonl"),
        )

    def test_empty_data_dir(self):
        report = build_report(self.tmp)
        assert report["summary"]["total_bsr_rows"] == 0
        assert report["rows"] == []

    def test_v1_row_is_no_action_and_legacy_unjoinable(self):
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [])
        _write_jsonl(bsr_p, [BSR_V1_LEGACY])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        assert len(report["rows"]) == 1
        row = report["rows"][0]
        assert row["learning_classification"] == "NO_ACTION_INSUFFICIENT_EVIDENCE"
        assert row["actual_execution_status"] == "UNKNOWN"
        assert row["bot_eval_joined"] is False
        assert "v1_schema_missing_fields" in row["data_quality_flags"]
        s = report["summary"]
        assert s["legacy_unjoinable_rows"] == 1
        assert s["bot_evaluation_joined_rows"] == 0
        assert s["identity_available_rows"] == 0

    def test_v3_row_without_bse_match_counts_correctly(self):
        """BSR v3 with Polymarket identity but no BSE match: identity_available but not bot_eval_joined."""
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        # Identity available (condition_id present)
        assert row["has_polymarket_identity"] is True
        assert row["join_confidence"] == "HIGH"
        # NOT bot eval joined
        assert row["bot_eval_joined"] is False
        assert row["bot_would_buy"] is None
        # Classification requires would_buy -> NO_ACTION
        assert row["learning_classification"] == "NO_ACTION_INSUFFICIENT_EVIDENCE"
        s = report["summary"]
        assert s["identity_available_rows"] == 1
        assert s["bot_evaluation_joined_rows"] == 0
        assert s["bot_evaluation_missing_rows"] == 1

    def test_v3_row_with_bse_join_candidate_filtered_winner(self):
        """BSR v3 shadow + win_for_trader=True + BSE would_buy=False -> CANDIDATE_FILTERED_WINNER."""
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [BSE_ROW_CONDITION_FILTERED])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        assert row["bot_eval_joined"] is True
        assert row["bot_would_buy"] is False
        assert row["win_for_trader"] is True
        assert row["learning_classification"] == "CANDIDATE_FILTERED_WINNER"
        s = report["summary"]
        assert s["bot_evaluation_joined_rows"] == 1
        assert s["identity_available_rows"] == 1

    def test_bse_earliest_selected(self):
        """When multiple BSE rows exist for same eval_key, EARLIEST ts_utc is used."""
        bse_p, bsr_p, scx_p = self._paths()
        bse_early = dict(BSE_ROW_CONDITION_FILTERED)
        bse_early["ts_utc"] = "2026-05-19T06:00:00+00:00"
        bse_early["would_buy"] = True  # early: would_buy=True
        bse_late = dict(BSE_ROW_CONDITION_FILTERED)
        bse_late["ts_utc"] = "2026-05-21T18:00:00+00:00"
        bse_late["would_buy"] = False  # late: would_buy=False
        _write_jsonl(bse_p, [bse_late, bse_early])  # late written first
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        # Should use EARLIEST (2026-05-19) which has would_buy=True
        assert row["bot_would_buy"] is True
        assert row["bot_eval_ts_utc"] == "2026-05-19T06:00:00+00:00"

    def test_temporal_alignment_verified_when_bse_before_market_date(self):
        """BSE ts_utc before market date -> VERIFIED."""
        bse_p, bsr_p, scx_p = self._paths()
        bse = dict(BSE_ROW_CONDITION_FILTERED)
        bse["ts_utc"] = "2026-05-20T10:00:00+00:00"  # before 2026-05-22
        _write_jsonl(bse_p, [bse])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        assert row["temporal_alignment_status"] == "VERIFIED"
        assert "temporal_alignment_unverified" not in row["data_quality_flags"]
        assert "temporal_alignment_verified" in row["gates_passed"]

    def test_temporal_alignment_unverified_when_bse_same_day(self):
        """BSE ts_utc on market date -> UNVERIFIED."""
        bse_p, bsr_p, scx_p = self._paths()
        bse = dict(BSE_ROW_CONDITION_FILTERED)
        bse["ts_utc"] = "2026-05-22T06:00:00+00:00"  # same day
        _write_jsonl(bse_p, [bse])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        assert row["temporal_alignment_status"] == "UNVERIFIED"
        assert "temporal_alignment_unverified" in row["data_quality_flags"]
        assert "temporal_alignment_verified" in row["gates_missing"]

    def test_candidate_missed_opportunity_blocked(self):
        """would_buy=True + win=True + BLOCKED_POLICY -> CANDIDATE_MISSED_OPPORTUNITY."""
        bse_p, bsr_p, scx_p = self._paths()
        bse_row = dict(BSE_ROW_CONDITION_FILTERED)
        bse_row["would_buy"] = True
        bse_row["decision_gate"] = None
        bse_row["skip_or_block_reason"] = None
        bsr_row = dict(BSR_V3_SHADOW)
        bsr_row["city_mode_at_record_time"] = "blocked"
        _write_jsonl(bse_p, [bse_row])
        _write_jsonl(bsr_p, [bsr_row])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        assert row["learning_classification"] == "CANDIDATE_MISSED_OPPORTUNITY"
        assert row["actual_execution_status"] == "BLOCKED_POLICY"
        assert row["blocking_gate"] == "city_mode"
        assert row["bot_eval_joined"] is True

    def test_protective_policy_evidence(self):
        """would_buy=True + win=False + SHADOW_ONLY -> PROTECTIVE_POLICY_EVIDENCE."""
        bse_p, bsr_p, scx_p = self._paths()
        bse_row = dict(BSE_ROW_CONDITION_FILTERED)
        bse_row["would_buy"] = True
        bsr_row = dict(BSR_V3_SHADOW)
        bsr_row["win_for_trader"] = False
        bsr_row["city_mode_at_record_time"] = "shadow"
        _write_jsonl(bse_p, [bse_row])
        _write_jsonl(bsr_p, [bsr_row])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        row = report["rows"][0]
        assert row["learning_classification"] == "PROTECTIVE_POLICY_EVIDENCE"

    def test_summary_separate_counts(self):
        """Summary correctly separates identity_available, bot_eval_joined, missing, legacy."""
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [BSE_ROW_CONDITION_FILTERED])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW, BSR_V1_LEGACY])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        s = report["summary"]
        assert s["total_bsr_rows"] == 2
        assert s["identity_available_rows"] == 1    # BSR_V3_SHADOW has condition_id
        assert s["bot_evaluation_joined_rows"] == 1  # BSR_V3_SHADOW matched BSE
        assert s["bot_evaluation_missing_rows"] == 0 # no v2+ unmatched (v3 matched)
        assert s["legacy_unjoinable_rows"] == 1      # BSR_V1_LEGACY

    def test_joined_rows_not_inflated_by_identity(self):
        """Identity-available rows without BSE match must NOT count as bot_eval_joined."""
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [])  # no BSE at all
        _write_jsonl(bsr_p, [BSR_V3_SHADOW])  # has condition_id/market_id
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        s = report["summary"]
        assert s["identity_available_rows"] == 1    # identity exists
        assert s["bot_evaluation_joined_rows"] == 0 # NO bot eval join

    def test_data_gaps_present(self):
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [])
        _write_jsonl(bsr_p, [BSR_V1_LEGACY])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        gap_types = [g["gap_type"] for g in report["data_gaps"]]
        assert "v1_schema_missing_fields" in gap_types
        assert "settlement_fidelity_unknown" in gap_types
        assert "temporal_alignment_unverified" in gap_types
        assert "crosscheck_is_aggregate_only" in gap_types

    def test_report_structure(self):
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [])
        _write_jsonl(bsr_p, [])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        assert report["consumer_type"] == "LOG_ONLY"
        assert "ledger_contract_ref" in report
        assert "data_gaps" in report
        assert "rows" in report
        assert "summary" in report
        s = report["summary"]
        assert "identity_available_rows" in s
        assert "bot_evaluation_joined_rows" in s
        assert "bot_evaluation_missing_rows" in s
        assert "legacy_unjoinable_rows" in s
        assert "temporal_alignment_distribution" in s

    def test_no_bot_py_import(self):
        """Confirm the module does not import bot.py."""
        import importlib
        import sys
        if "tools.trader_vs_bot_gap_report" in sys.modules:
            del sys.modules["tools.trader_vs_bot_gap_report"]
        mod = importlib.import_module("tools.trader_vs_bot_gap_report")
        assert "bot" not in dir(mod), "Module must not import bot.py"

    def test_sample_for_opus_uses_bot_eval_joined(self):
        """sample_for_opus must only contain rows with bot_eval_joined=True."""
        bse_p, bsr_p, scx_p = self._paths()
        _write_jsonl(bse_p, [BSE_ROW_CONDITION_FILTERED])
        _write_jsonl(bsr_p, [BSR_V3_SHADOW, BSR_V1_LEGACY])
        _write_jsonl(scx_p, [])
        report = build_report(self.tmp)
        for r in report["sample_for_opus_review"]:
            assert r["bot_eval_joined"] is True, "Sample must only include bot_eval_joined rows"
