"""Tests for Source Audit Workbench v1.0 (LOG_ONLY)."""

import json
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import source_audit_workbench as workbench


def _repo_tmp_path():
    base = REPO_ROOT / f"_tmp_source_audit_tests_{uuid.uuid4().hex}"
    base.mkdir(parents=True)
    return base


def _cleanup(path):
    # Windows ACLs in this repo can leave temp files non-deletable during pytest.
    # The directory prefix is gitignored; leaving it is safer than failing tests
    # during cleanup.
    return None


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def _base_files(tmp_path, *, city="San Francisco", candidate_state="SOURCE_BLOCKED", condition="exact"):
    candidate_source = tmp_path / "source_onboarding.json"
    signals = tmp_path / "signals_crosscheck.jsonl"
    blocked = tmp_path / "blocked_signals_resolutions.jsonl"
    policy_env = tmp_path / "policy_env_snapshot.json"
    policy_state = tmp_path / "city_policy_state.json"

    _write_json(candidate_source, {
        "cities": [{
            "city": city,
            "state": candidate_state,
            "priority_score": 0.42,
            "source_feasibility": "no_icao",
        }]
    })
    _write_jsonl(signals, [{
        "run_at": "2026-05-14T00:00:00+00:00",
        "trader_only_details": [{
            "city": city,
            "n_signals": 2,
            "n_consensus": 0,
            "has_consensus_market": False,
            "max_trader_wr": 80.3,
            "conditions": [condition],
            "dates": ["2026-05-13"],
        }],
    }])
    _write_jsonl(blocked, [{
        "city": city,
        "bot_evaluation": "evaluated",
        "win_for_trader": True,
    }])
    _write_json(policy_env, {
        "variables": {
            "ACTIVE_TRADING_CITIES": "",
            "CANARY_TRADING_CITIES": "",
            "BLOCKED_CITIES": "",
        }
    })
    _write_json(policy_state, {
        "auto_canary_cities": {},
        "auto_shadow_cities": {},
        "auto_blocked_cities": {},
    })
    return candidate_source, signals, blocked, policy_env, policy_state


def _args(tmp_path, city="San Francisco", **extra):
    candidate_source, signals, blocked, policy_env, policy_state = _base_files(
        tmp_path,
        city=city,
        condition=extra.pop("condition", "exact"),
    )
    argv = [
        "--city", city,
        "--candidate-source", str(candidate_source),
        "--signals-crosscheck", str(signals),
        "--blocked-resolutions", str(blocked),
        "--policy-env", str(policy_env),
        "--policy-state", str(policy_state),
        "--output-json", str(tmp_path / "audit.json"),
        "--output-md", str(tmp_path / "audit.md"),
        "--no-network",
    ]
    for flag, value in extra.items():
        cli_flag = "--" + flag.replace("_", "-")
        if value is not None:
            argv.extend([cli_flag, value])
    return workbench.parse_args(argv)


def test_city_already_observed_returns_already_observed(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(tmp_path, city="Los Angeles")
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {"Los Angeles": {"icao": "KLAX", "noaa_daily_station_id": "USW00023174"}},
        "resolution_stations": {"Los Angeles": {"name": "LAX", "lat": 33.9, "lon": -118.4}},
        "observed_audit_cities": {"Los Angeles"},
        "city_timezones": {"Los Angeles": "America/Los_Angeles"},
        "warnings": [],
    })

    try:
        payload = workbench.build_audit(args, now="2026-05-14T00:00:00+00:00")
    finally:
        _cleanup(tmp_path)

    assert payload["status"] == workbench.STATUS_ALREADY_OBSERVED
    assert payload["proposed_next_step"] == workbench.NEXT_NO_ACTION


def test_candidate_without_source_or_ids_needs_manual_lookup(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(tmp_path)
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    })

    try:
        payload = workbench.build_audit(args, now="2026-05-14T00:00:00+00:00")
    finally:
        _cleanup(tmp_path)

    assert payload["status"] == workbench.STATUS_NEEDS_MANUAL_SOURCE_LOOKUP
    assert payload["risk"]["source_unverified"] is True
    assert payload["proposed_next_step"] == workbench.NEXT_MANUAL_SOURCE_LOOKUP


def test_city_with_cli_icao_and_noaa_daily_is_review_ready(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(
        tmp_path,
        icao="KSFO",
        noaa_daily_station_id="USW00023234",
        noaa_station_id="72494023234",
        wu_url="https://www.wunderground.com/history/daily/KSFO/date/{date}",
    )
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    })

    try:
        payload = workbench.build_audit(args, now="2026-05-14T00:00:00+00:00")
    finally:
        _cleanup(tmp_path)

    assert payload["status"] in {
        workbench.STATUS_SOURCE_AUDIT_PASS,
        workbench.STATUS_READY_FOR_OBSERVED_AUDIT_REVIEW,
    }
    assert payload["recommendation"] in {
        workbench.RECOMMEND_SOURCE_AUDIT_PASS,
        workbench.RECOMMEND_OBSERVED_AUDIT_REVIEW,
    }
    assert payload["source_candidate"]["icao"] == "KSFO"


def test_range_only_sets_risk_and_does_not_recommend_canary(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(
        tmp_path,
        condition="range",
        icao="KSFO",
        noaa_daily_station_id="USW00023234",
    )
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    })

    try:
        payload = workbench.build_audit(args, now="2026-05-14T00:00:00+00:00")
    finally:
        _cleanup(tmp_path)

    assert payload["risk"]["range_only_not_operable"] is True
    assert "canary" not in payload["recommendation"].lower()
    assert "canary" not in payload["proposed_next_step"].lower()


def test_markdown_contains_log_only_and_forbidden_terms_absent(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(tmp_path, icao="KSFO", noaa_daily_station_id="USW00023234")
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    })
    try:
        payload = workbench.build_audit(args, now="2026-05-14T00:00:00+00:00")
        markdown = workbench.render_markdown(payload)
    finally:
        _cleanup(tmp_path)

    assert "LOG_ONLY" in markdown
    for term in ("BUY", "SELL", "SKIP", "BANKROLL", "Fase C"):
        assert term not in markdown


def test_main_writes_outputs_without_network(monkeypatch):
    tmp_path = _repo_tmp_path()
    args = _args(tmp_path, icao="KSFO", noaa_daily_station_id="USW00023234")
    monkeypatch.setattr(workbench, "load_bot_reference", lambda: {
        "resolution_icao": {},
        "resolution_stations": {},
        "observed_audit_cities": set(),
        "city_timezones": {},
        "warnings": [],
    })

    try:
        result = workbench.main([
            "--city", args.city,
            "--candidate-source", args.candidate_source,
            "--signals-crosscheck", args.signals_crosscheck,
            "--blocked-resolutions", args.blocked_resolutions,
            "--policy-env", args.policy_env,
            "--policy-state", args.policy_state,
            "--output-json", args.output_json,
            "--output-md", args.output_md,
            "--icao", "KSFO",
            "--noaa-daily-station-id", "USW00023234",
            "--no-network",
        ])

        assert result == 0
        assert Path(args.output_json).exists()
        assert Path(args.output_md).exists()
    finally:
        _cleanup(tmp_path)

    source = Path(workbench.__file__).read_text(encoding="utf-8")
    assert "urllib.request" not in source
    assert "requests" not in source
