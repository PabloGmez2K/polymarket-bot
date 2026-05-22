from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "traders_intelligence_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("traders_intelligence_report", TOOL_PATH)
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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def minimal_inputs(tmp_path: Path) -> dict[str, Path]:
    signals = tmp_path / "signals.json"
    traders_db = tmp_path / "traders_db.json"
    census = tmp_path / "census.json"
    enrichment = tmp_path / "enrichment.json"
    city_cross = tmp_path / "city_cross.json"
    crosscheck = tmp_path / "crosscheck.jsonl"
    blocked = tmp_path / "blocked.jsonl"
    lifecycle = tmp_path / "trade_lifecycle.json"
    json_output = tmp_path / "traders_intelligence.json"
    md_output = tmp_path / "traders_intelligence.md"

    write_json(
        signals,
        {
            "generated": "2026-05-22T08:00:00+00:00",
            "signals": [
                {"trader": "Followed-Trader", "city": "Madrid", "condition": "exact", "outcome": "Yes"},
                {"trader": "No-Wallet", "city": "Paris", "condition": "exact", "outcome": "No"},
            ],
        },
    )
    write_json(
        traders_db,
        {
            "traders": {
                "Followed-Trader": {
                    "address": "0x1111111111111111111111111111111111111111",
                    "pseudonym": "Followed-Trader",
                    "source": "test",
                }
            }
        },
    )
    write_json(census, {"generated_at": "2026-05-22T08:00:00+00:00", "summary": {}, "traders": []})
    write_json(enrichment, {"generated_at": "2026-05-22T08:00:00+00:00", "summary": {}, "traders": []})
    write_json(city_cross, {"city_rows": []})
    write_jsonl(crosscheck, [])
    write_jsonl(blocked, [])
    write_json(lifecycle, {"summary": {"closed_positions": 0}})

    return {
        "signals": signals,
        "traders_db": traders_db,
        "census": census,
        "enrichment": enrichment,
        "city_cross": city_cross,
        "crosscheck": crosscheck,
        "blocked": blocked,
        "lifecycle": lifecycle,
        "json_output": json_output,
        "md_output": md_output,
    }


def run_report(module, paths: dict[str, Path], *, external: bool = False) -> dict:
    args = [
        "--signals",
        str(paths["signals"]),
        "--traders-db",
        str(paths["traders_db"]),
        "--census",
        str(paths["census"]),
        "--enrichment",
        str(paths["enrichment"]),
        "--city-cross",
        str(paths["city_cross"]),
        "--crosscheck-series",
        str(paths["crosscheck"]),
        "--blocked-resolutions",
        str(paths["blocked"]),
        "--trade-lifecycle",
        str(paths["lifecycle"]),
        "--json-output",
        str(paths["json_output"]),
        "--md-output",
        str(paths["md_output"]),
    ]
    if external:
        args.append("--external-observability")
    assert module.main(args) is None
    return json.loads(paths["json_output"].read_text(encoding="utf-8"))


def test_external_observability_resolves_wallet_from_traders_db_and_handles_weather_empty(monkeypatch, tmp_path):
    module = load_module()
    paths = minimal_inputs(tmp_path)
    requested_urls: list[str] = []

    def fake_request_json(url: str):
        requested_urls.append(url)
        parsed = urlparse(url)
        if parsed.netloc == "data-api.polymarket.com":
            params = parse_qs(parsed.query)
            assert params["timePeriod"] == ["ALL"]
            assert params["orderBy"] == ["PNL"]
            assert params["user"] == ["0x1111111111111111111111111111111111111111"]
            if params["category"] == ["OVERALL"]:
                return [
                    {
                        "proxyWallet": "0x1111111111111111111111111111111111111111",
                        "userName": "Followed-Trader",
                        "pnl": "12.345",
                        "vol": "456.7",
                        "rank": 9,
                    }
                ]
            if params["category"] == ["WEATHER"]:
                return []
        if parsed.netloc == "gamma-api.polymarket.com":
            return {
                "proxyWallet": "0x1111111111111111111111111111111111111111",
                "pseudonym": "Followed-Trader",
                "xUsername": "followed",
                "verifiedBadge": True,
            }
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(module, "request_json", fake_request_json)

    payload = run_report(module, paths, external=True)
    followed = next(row for row in payload["traders"] if row["pseudonym"] == "Followed-Trader")
    missing = next(row for row in payload["traders"] if row["pseudonym"] == "No-Wallet")
    external = followed["external_observability"]

    assert external["classification"] == "external_observability"
    assert external["source_quality"] == "external_opaque"
    assert external["operational_use"] == "LOG_ONLY_NOT_TRADING_SIGNAL"
    assert external["identity_source"] == "traders_db"
    assert external["proxy_wallet"] == "0x1111111111111111111111111111111111111111"
    assert external["leaderboard_overall_all"]["query_status"] == "ok"
    assert external["leaderboard_overall_all"]["pnl"] == 12.35
    assert external["leaderboard_overall_all"]["vol"] == 456.7
    assert external["leaderboard_overall_all"]["rank"] == 9
    assert external["leaderboard_weather_all"]["query_status"] == "empty"
    assert external["public_profile"]["query_status"] == "ok"
    assert external["public_profile"]["profile_url"].endswith("/0x1111111111111111111111111111111111111111")
    assert missing["external_observability"]["identity_status"] == "missing_identity"
    assert missing["external_observability"]["leaderboard_overall_all"]["query_status"] == "missing_identity"
    assert len(requested_urls) == 3


def test_external_observability_records_api_failure(monkeypatch):
    module = load_module()

    def fake_request_json(url: str):
        raise TimeoutError("timed out")

    monkeypatch.setattr(module, "request_json", fake_request_json)
    payload = module.build_external_observability(
        {
            "identity_status": "resolved",
            "proxy_wallet": "0x2222222222222222222222222222222222222222",
            "identity_source": "traders_db",
            "identity_sources_checked": ["traders_db"],
        },
        enabled=True,
    )

    assert payload["leaderboard_overall_all"]["query_status"] == "failed"
    assert "timed out" in payload["leaderboard_overall_all"]["api_error"]
    assert payload["leaderboard_weather_all"]["query_status"] == "failed"
    assert payload["public_profile"]["query_status"] == "failed"
    assert payload["operational_use"] == "LOG_ONLY_NOT_TRADING_SIGNAL"


def test_existing_output_remains_compatible_and_external_calls_are_opt_in(monkeypatch, tmp_path):
    module = load_module()
    paths = minimal_inputs(tmp_path)

    def forbidden_request_json(url: str):
        raise AssertionError(f"network should not be called without opt-in: {url}")

    monkeypatch.setattr(module, "request_json", forbidden_request_json)

    payload = run_report(module, paths, external=False)
    followed = next(row for row in payload["traders"] if row["pseudonym"] == "Followed-Trader")

    assert payload["schema_version"] == "v0"
    assert "activity" in followed
    assert "style" in followed
    assert "blocked_signal_performance" in followed
    assert followed["proxy_wallet"] == "0x1111111111111111111111111111111111111111"
    assert followed["external_observability"]["enabled"] is False
    assert followed["external_observability"]["leaderboard_overall_all"]["query_status"] == "disabled"
