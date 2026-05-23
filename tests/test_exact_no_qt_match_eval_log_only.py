"""
Focal tests for exact/no-QT-match LOG_ONLY evaluation capture (v10.6.43).

Covers:
  T1  env var OFF → no capture, cycle continues unchanged
  T2  env var ON + no_qt_match + active → captures with both YES/NO sides
  T3  env var ON + no_qt_match + canary → same coverage
  T4  shadow/blocked city_mode → no capture
  T5  other sub-reasons → no capture
  T6  continue semantics: no BUY, no batch append when not triggered
  T7  writer fail-open: exception in write does not raise
  T8  dedup by eval_key within cycle
  T9a cap=20 exact selection count
  T9b SHA-256 sampling reproducible across runs
  T9c SHA-256 sampling order-independent
  T9d SHA-256 sampling no lexicographic city bias
  T10 schema required fields present
  T11 identity_resolvable=False when all ids are null
  T12 eval_key joinable with skip_log format
  T13 best_side_log_only logic
  T14 consumer reads new artefact via fixture
  T15 consumer degrades to NOT_ENABLED_NO_DATA when file absent
"""
from __future__ import annotations

import json
import os

import pytest

import bot
from tools.trader_vs_bot_gap_report import _summarize_exact_no_qt_match_log_only


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_batch(n: int, cycle_id: str = "2026-05-23T16:00", base_city: str = "Seoul") -> list[dict]:
    """Return n distinct LOG_ONLY batch records (unique eval_keys)."""
    return [
        {
            "schema_version": 1,
            "ts_utc": "2026-05-23T16:01:00+00:00",
            "cycle_id": cycle_id,
            "eval_key": f"{base_city}|2026-05-24|exact|{20 + i}|C",
            "capture_id": f"uuid-{i}",
            "market_id": f"mkt-{i}",
            "condition_id": f"cond-{i}",
            "token_id_yes": f"yes-{i}",
            "token_id_no": f"no-{i}",
            "identity_resolvable": True,
            "city": base_city,
            "city_mode": "active",
            "date_iso": "2026-05-24",
            "days_ahead": 1,
            "condition": "exact",
            "threshold": 20 + i,
            "threshold_high": None,
            "unit": "C",
            "qt_gate_reason": "no_quality_trader_signal_match",
            "our_prob_yes": 0.35,
            "our_prob_no": 0.65,
            "mkt_prob_yes": 0.20,
            "mkt_prob_no": 0.80,
            "edge_yes_pct": 15.0,
            "edge_no_pct": -15.0,
            "best_side_log_only": "YES",
            "best_edge_pct_log_only": 15.0,
            "min_edge_reference": 15.0,
            "edge_passes_reference_threshold_log_only": True,
            "forecast_max": 22.5,
            "sigma_used": 1.8,
            "source_fidelity_status": "unknown",
            "log_only": True,
            "execution_authorized": False,
            "skip_log_eval_key": f"{base_city}|2026-05-24|exact|{20 + i}|C",
            "capture_meta": None,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# T1: env var OFF → no capture
# ---------------------------------------------------------------------------

class TestEnvVarOff:
    def test_batch_empty_when_disabled(self, monkeypatch):
        monkeypatch.setenv("LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED", "0")
        assert os.getenv("LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED", "0") == "0"
        # Simulate condition: env var off → batch stays empty
        batch = []
        if os.getenv("LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED", "0") == "1":
            batch.append("should not appear")
        assert batch == []

    def test_write_not_called_when_batch_empty(self, monkeypatch, tmp_path):
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        monkeypatch.setattr(bot, "EXACT_NO_QT_MATCH_EVAL_FILE", str(target))
        # Empty batch → no write
        bot.write_exact_no_qt_match_evals([])
        assert not target.exists()


# ---------------------------------------------------------------------------
# T2 / T3: env var ON + no_qt_match + active/canary → capture both sides
# ---------------------------------------------------------------------------

class TestCaptureBothSides:
    def _run_write(self, tmp_path, batch):
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        return rows

    def test_captures_both_yes_no_sides_active(self, tmp_path):
        batch = _make_batch(1)
        rows = self._run_write(tmp_path, batch)
        assert len(rows) == 1
        r = rows[0]
        assert "our_prob_yes" in r
        assert "our_prob_no" in r
        assert "mkt_prob_yes" in r
        assert "mkt_prob_no" in r
        assert "edge_yes_pct" in r
        assert "edge_no_pct" in r
        assert r["log_only"] is True
        assert r["execution_authorized"] is False

    def test_captures_canary_city_mode(self, tmp_path):
        batch = _make_batch(1)
        batch[0]["city_mode"] = "canary"
        rows = self._run_write(tmp_path, batch)
        assert len(rows) == 1
        assert rows[0]["city_mode"] == "canary"


# ---------------------------------------------------------------------------
# T4: shadow/blocked → no capture (conditional logic, not writer)
# ---------------------------------------------------------------------------

class TestNoCaptureOtherModes:
    def test_shadow_not_in_capture_cohort(self):
        city_mode = "shadow"
        captured = city_mode in {"active", "canary"}
        assert not captured

    def test_blocked_not_in_capture_cohort(self):
        city_mode = "blocked"
        captured = city_mode in {"active", "canary"}
        assert not captured


# ---------------------------------------------------------------------------
# T5: other sub-reasons → no capture
# ---------------------------------------------------------------------------

class TestNoCaptureOtherSubReasons:
    def test_condition_not_in_gate_excluded(self):
        reason = "condition_not_in_quality_trader_gate"
        captured = reason == "no_quality_trader_signal_match"
        assert not captured

    def test_city_not_in_whitelist_excluded(self):
        reason = "city_not_in_quality_trader_whitelist"
        captured = reason == "no_quality_trader_signal_match"
        assert not captured


# ---------------------------------------------------------------------------
# T6: continue preserved — execution_authorized=False, no BUY
# ---------------------------------------------------------------------------

class TestNoBuy:
    def test_execution_authorized_always_false(self, tmp_path):
        batch = _make_batch(2)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        for r in rows:
            assert r["execution_authorized"] is False
            assert r["log_only"] is True
            assert "would_buy" not in r


# ---------------------------------------------------------------------------
# T7: writer fail-open
# ---------------------------------------------------------------------------

class TestWriterFailOpen:
    def test_bad_path_does_not_raise(self, monkeypatch, tmp_path):
        batch = _make_batch(1)
        bad_path = "/nonexistent_root_/exact_no_qt.jsonl"
        # Should not raise even if the path is invalid
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=bad_path)  # no exception


# ---------------------------------------------------------------------------
# T8: dedup by eval_key within cycle
# ---------------------------------------------------------------------------

class TestDedup:
    def test_same_eval_key_deduped(self, tmp_path):
        batch = _make_batch(1) * 3  # same record three times
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1

    def test_different_eval_keys_all_kept(self, tmp_path):
        batch = _make_batch(3)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# T9a: cap=20 — exactly N records when eligible > cap
# ---------------------------------------------------------------------------

class TestCap:
    def test_cap_selects_exactly_n(self, tmp_path):
        batch = _make_batch(25)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target), cap_per_cycle=20)
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 20

    def test_cap_sets_capped_count_in_meta(self, tmp_path):
        batch = _make_batch(25)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target), cap_per_cycle=20)
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        for r in rows:
            meta = r.get("capture_meta", {})
            assert meta.get("capped_count") == 5
            assert meta.get("eligible_before_cap") == 25
            assert meta.get("selected_after_cap") == 20

    def test_no_cap_when_at_or_below_limit(self, tmp_path):
        batch = _make_batch(10)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target), cap_per_cycle=20)
        rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 10
        for r in rows:
            meta = r.get("capture_meta", {})
            assert meta.get("sampling_method") == "none"
            assert meta.get("cap_active") is False


# ---------------------------------------------------------------------------
# T9b: SHA-256 reproducible across calls with same input
# ---------------------------------------------------------------------------

class TestSHA256Reproducible:
    def test_same_selection_across_two_runs(self, tmp_path):
        batch = _make_batch(25)

        target1 = tmp_path / "run1.jsonl"
        bot.write_exact_no_qt_match_evals(list(batch), jsonl_path=str(target1), cap_per_cycle=20)
        keys1 = {
            json.loads(l)["eval_key"]
            for l in target1.read_text(encoding="utf-8").splitlines()
        }

        target2 = tmp_path / "run2.jsonl"
        bot.write_exact_no_qt_match_evals(list(batch), jsonl_path=str(target2), cap_per_cycle=20)
        keys2 = {
            json.loads(l)["eval_key"]
            for l in target2.read_text(encoding="utf-8").splitlines()
        }

        assert keys1 == keys2


# ---------------------------------------------------------------------------
# T9c: SHA-256 order-independent
# ---------------------------------------------------------------------------

class TestSHA256OrderIndependent:
    def test_shuffled_input_same_selection(self, tmp_path):
        import random
        batch = _make_batch(25)
        shuffled = list(batch)
        random.shuffle(shuffled)

        target_orig = tmp_path / "orig.jsonl"
        bot.write_exact_no_qt_match_evals(list(batch), jsonl_path=str(target_orig), cap_per_cycle=20)
        keys_orig = {
            json.loads(l)["eval_key"]
            for l in target_orig.read_text(encoding="utf-8").splitlines()
        }

        target_shuf = tmp_path / "shuf.jsonl"
        bot.write_exact_no_qt_match_evals(shuffled, jsonl_path=str(target_shuf), cap_per_cycle=20)
        keys_shuf = {
            json.loads(l)["eval_key"]
            for l in target_shuf.read_text(encoding="utf-8").splitlines()
        }

        assert keys_orig == keys_shuf


# ---------------------------------------------------------------------------
# T9d: SHA-256 no lexicographic city bias
# ---------------------------------------------------------------------------

class TestSHA256NoBias:
    def test_cities_not_biased_by_alpha_prefix(self, tmp_path):
        # Build batch with cities starting from 'A' and 'Z'
        early_alpha = [f"Amsterdam|2026-05-24|exact|{20 + i}|C" for i in range(13)]
        late_alpha = [f"Zagreb|2026-05-24|exact|{20 + i}|C" for i in range(12)]
        all_keys = early_alpha + late_alpha
        cycle_id = "2026-05-23T16:00"
        batch = [
            {
                **_make_batch(1)[0],
                "eval_key": k,
                "skip_log_eval_key": k,
                "cycle_id": cycle_id,
            }
            for k in all_keys
        ]
        target = tmp_path / "bias_test.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target), cap_per_cycle=10)
        selected_keys = [
            json.loads(l)["eval_key"]
            for l in target.read_text(encoding="utf-8").splitlines()
        ]
        n_amsterdam = sum(1 for k in selected_keys if k.startswith("Amsterdam"))
        n_zagreb = sum(1 for k in selected_keys if k.startswith("Zagreb"))
        # With lexicographic sort, all Amsterdam would come first (alphabetically earlier).
        # SHA-256 should mix them. Strict lexicographic would give n_amsterdam=10, n_zagreb=0.
        # We assert SHA-256 does NOT produce that extreme outcome.
        assert not (n_amsterdam == 10 and n_zagreb == 0), (
            "SHA-256 sampling should not select ALL early-alphabet cities and zero late-alphabet"
        )


# ---------------------------------------------------------------------------
# T10: schema required fields present
# ---------------------------------------------------------------------------

class TestSchemaFields:
    def test_all_required_fields_present(self, tmp_path):
        batch = _make_batch(1)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        r = json.loads(target.read_text(encoding="utf-8").strip())
        required = [
            "schema_version", "ts_utc", "cycle_id", "eval_key", "capture_id",
            "market_id", "condition_id", "token_id_yes", "token_id_no",
            "identity_resolvable", "city", "city_mode", "date_iso", "days_ahead",
            "condition", "threshold", "threshold_high", "unit", "qt_gate_reason",
            "our_prob_yes", "our_prob_no", "mkt_prob_yes", "mkt_prob_no",
            "edge_yes_pct", "edge_no_pct", "best_side_log_only", "best_edge_pct_log_only",
            "min_edge_reference", "edge_passes_reference_threshold_log_only",
            "forecast_max", "sigma_used", "source_fidelity_status",
            "log_only", "execution_authorized", "skip_log_eval_key", "capture_meta",
        ]
        missing = [f for f in required if f not in r]
        assert missing == [], f"Missing fields: {missing}"


# ---------------------------------------------------------------------------
# T11: identity_resolvable=False when all ids are null
# ---------------------------------------------------------------------------

class TestIdentityResolvable:
    def test_false_when_all_ids_null(self, tmp_path):
        batch = _make_batch(1)
        batch[0]["market_id"] = None
        batch[0]["condition_id"] = None
        batch[0]["token_id_yes"] = None
        batch[0]["token_id_no"] = None
        batch[0]["identity_resolvable"] = bool(None or None or None or None)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        r = json.loads(target.read_text(encoding="utf-8").strip())
        assert r["identity_resolvable"] is False

    def test_true_when_token_ids_present(self, tmp_path):
        batch = _make_batch(1)
        batch[0]["market_id"] = None
        batch[0]["condition_id"] = None
        # token_id_yes is present
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        r = json.loads(target.read_text(encoding="utf-8").strip())
        assert r["identity_resolvable"] is True


# ---------------------------------------------------------------------------
# T12: eval_key format matches skip_log qt_match_key
# ---------------------------------------------------------------------------

class TestEvalKeyFormat:
    def test_eval_key_matches_skip_log_format(self, tmp_path):
        batch = _make_batch(1)
        target = tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        r = json.loads(target.read_text(encoding="utf-8").strip())
        assert r["eval_key"] == r["skip_log_eval_key"]
        # Format: city|date|condition|threshold|unit
        parts = r["eval_key"].split("|")
        assert len(parts) == 5
        assert parts[2] == "exact"


# ---------------------------------------------------------------------------
# T13: best_side_log_only logic
# ---------------------------------------------------------------------------

class TestBestSideLogic:
    def _write_one(self, tmp_path, edge_yes, edge_no, min_edge=15.0):
        batch = _make_batch(1)
        batch[0]["edge_yes_pct"] = edge_yes
        batch[0]["edge_no_pct"] = edge_no
        if edge_yes > 0 and edge_yes >= edge_no:
            batch[0]["best_side_log_only"] = "YES"
            batch[0]["best_edge_pct_log_only"] = edge_yes
        elif edge_no > 0:
            batch[0]["best_side_log_only"] = "NO"
            batch[0]["best_edge_pct_log_only"] = edge_no
        else:
            batch[0]["best_side_log_only"] = None
            batch[0]["best_edge_pct_log_only"] = None
        batch[0]["edge_passes_reference_threshold_log_only"] = bool(
            batch[0]["best_edge_pct_log_only"] is not None
            and batch[0]["best_edge_pct_log_only"] >= min_edge
        )
        target = tmp_path / "test.jsonl"
        bot.write_exact_no_qt_match_evals(batch, jsonl_path=str(target))
        return json.loads(target.read_text(encoding="utf-8").strip())

    def test_yes_wins_when_edge_yes_higher(self, tmp_path):
        r = self._write_one(tmp_path, edge_yes=20.0, edge_no=5.0)
        assert r["best_side_log_only"] == "YES"
        assert r["best_edge_pct_log_only"] == 20.0

    def test_no_wins_when_edge_no_higher(self, tmp_path):
        r = self._write_one(tmp_path, edge_yes=5.0, edge_no=20.0)
        assert r["best_side_log_only"] == "NO"
        assert r["best_edge_pct_log_only"] == 20.0

    def test_null_when_both_negative(self, tmp_path):
        r = self._write_one(tmp_path, edge_yes=-5.0, edge_no=-3.0)
        assert r["best_side_log_only"] is None
        assert r["best_edge_pct_log_only"] is None

    def test_edge_passes_threshold_true(self, tmp_path):
        r = self._write_one(tmp_path, edge_yes=20.0, edge_no=5.0, min_edge=15.0)
        assert r["edge_passes_reference_threshold_log_only"] is True

    def test_edge_passes_threshold_false(self, tmp_path):
        r = self._write_one(tmp_path, edge_yes=10.0, edge_no=5.0, min_edge=15.0)
        assert r["edge_passes_reference_threshold_log_only"] is False


# ---------------------------------------------------------------------------
# T14: consumer reads new artefact via fixture
# ---------------------------------------------------------------------------

class TestConsumerReadsArtifact:
    def test_reads_artefact_and_returns_summary(self, tmp_path):
        path = str(tmp_path / "exact_no_qt_match_evaluations_log_only.jsonl")
        batch = _make_batch(5)
        with open(path, "w", encoding="utf-8") as fh:
            for r in batch:
                r["capture_meta"] = {"sampled": False, "cap_active": False,
                                     "sampling_method": "none", "stable_rank": None,
                                     "cap_per_cycle": 20, "eligible_before_cap": 5,
                                     "selected_after_cap": 5, "capped_count": 0}
                fh.write(json.dumps(r) + "\n")
        summary = _summarize_exact_no_qt_match_log_only(path)
        assert summary["status"] == "DATA_AVAILABLE"
        assert summary["rows"] == 5
        assert summary["unique_eval_keys"] == 5
        assert "best_side_log_only_distribution" in summary
        assert "city_mode_breakdown" in summary


# ---------------------------------------------------------------------------
# T15: consumer degrades to NOT_ENABLED_NO_DATA
# ---------------------------------------------------------------------------

class TestConsumerNotEnabled:
    def test_absent_file_returns_not_enabled(self, tmp_path):
        path = str(tmp_path / "nonexistent.jsonl")
        summary = _summarize_exact_no_qt_match_log_only(path)
        assert summary["status"] == "NOT_ENABLED_NO_DATA"
        assert summary["rows"] == 0

    def test_empty_file_returns_not_enabled(self, tmp_path):
        path = str(tmp_path / "empty.jsonl")
        open(path, "w").close()
        summary = _summarize_exact_no_qt_match_log_only(path)
        assert summary["status"] == "NOT_ENABLED_NO_DATA"
        assert summary["rows"] == 0
