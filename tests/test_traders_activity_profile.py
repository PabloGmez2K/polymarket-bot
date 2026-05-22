from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "traders_activity_profile.py"
NOW_TS = 1_800_000_000


def load_module():
    spec = importlib.util.spec_from_file_location("traders_activity_profile", TOOL_PATH)
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


def base_paths(tmp_path: Path, traders: dict[str, str] | None = None) -> dict[str, Path]:
    traders = traders or {"Test-Trader": "0x1111111111111111111111111111111111111111"}
    traders_db = tmp_path / "traders_db.json"
    intelligence = tmp_path / "traders_intelligence.json"
    write_json(
        traders_db,
        {"traders": {name: {"address": wallet, "pseudonym": name} for name, wallet in traders.items()}},
    )
    write_json(intelligence, {"schema_version": "v0", "traders": []})
    return {"traders_db": traders_db, "intelligence": intelligence}


def run_payload(module, tmp_path: Path, activity: dict[tuple[str, str], list[dict]], *, extra_args=None, traders=None):
    paths = base_paths(tmp_path, traders=traders)
    requested: list[str] = []

    def fake_request_json(url: str):
        requested.append(url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        wallet = params["user"][0].lower()
        side = params["side"][0].upper()
        assert parsed.path == "/activity"
        assert params["type"] == ["TRADE"]
        assert "startTs" in params
        rows = activity.get((wallet, side), [])
        if rows == "RAISE":
            raise TimeoutError("timed out")
        return rows

    module.request_json = fake_request_json
    args = [
        "--traders-db",
        str(paths["traders_db"]),
        "--traders-intelligence",
        str(paths["intelligence"]),
        "--rate-limit-ms",
        "0",
        "--max-wallets",
        str(len(traders or {"x": "y"})),
    ]
    if extra_args:
        args.extend(extra_args)
    return module.build_payload(module.parse_args(args), now_ts=NOW_TS), requested


def fill(ts: int, *, side="BUY", wallet_market="m1", city="Shanghai", condition="exact", threshold=20, price=0.5, outcome="Yes", event="event-2026-05-22"):
    if condition == "range":
        title = f"Will the high temperature in {city} be between {threshold}-{threshold + 1}°C on May 22?"
    elif condition == "at_or_above":
        title = f"Will the high temperature in {city} be {threshold}°C or higher on May 22?"
    elif condition == "at_or_below":
        title = f"Will the high temperature in {city} be {threshold}°C or below on May 22?"
    else:
        title = f"Will the high temperature in {city} be {threshold}°C on May 22?"
    return {
        "timestamp": ts,
        "market": wallet_market,
        "slug": f"{event}-{city.lower()}-{condition}-{threshold}-{outcome.lower()}",
        "eventSlug": event,
        "title": title,
        "side": side,
        "outcome": outcome,
        "price": price,
        "size": 10,
    }


def trader(payload: dict, alias: str = "Test-Trader") -> dict:
    return next(row for row in payload["traders"] if row["alias"] == alias)


def test_basket_burst_detected_correctly(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    rows = [
        fill(NOW_TS - 10, wallet_market=f"m{i}", threshold=20 + i, event="shanghai-2026-05-22")
        for i in range(4)
    ]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): rows, (wallet, "SELL"): []})
    row = trader(payload)
    assert "BASKET_BURST" in row["style_labels"]
    assert row["metrics"]["bursts"][0]["n_fills"] == 4
    assert row["lane_suggestion"] == "REVIEW_REQUIRED"
    assert row["lane_reason"] == "mixed_style_evidence"


def test_oookey_like_related_event_basket_burst_from_slug_grouping(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    rows = []
    for i, threshold in enumerate([17, 18, 19, 20, 21]):
        rows.append(
            {
                "timestamp": NOW_TS - 100 + i,
                "market": f"ankara-{threshold}",
                "slug": f"highest-temperature-in-ankara-on-may-22-2026-{threshold}c",
                "side": "BUY",
                "outcome": "Yes",
                "price": 0.5,
                "size": 10,
            }
        )
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): rows, (wallet, "SELL"): []})
    row = trader(payload)
    assert "MULTI_OUTCOME_BASKET" in row["style_labels"]
    assert "BASKET_BURST" in row["style_labels"]
    assert row["metrics"]["basket_grouping"]["groups_with_multi_legs"] == 1


def test_high_price_activity(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    rows = [fill(NOW_TS - i, wallet_market=f"m{i}", price=0.96 if i == 0 else 0.5) for i in range(10)]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): rows, (wallet, "SELL"): []})
    row = trader(payload)
    assert "HIGH_PRICE_ACTIVITY" in row["style_labels"]
    assert row["metrics"]["high_price_fills"]["count"] == 1
    assert row["lane_suggestion"] == "REVIEW_REQUIRED"
    assert row["lane_reason"] == "mixed_style_evidence"


def test_sell_presence_informative_does_not_degrade_lane(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    buys = [fill(NOW_TS - 300 - i * 10, wallet_market=f"m{i}", condition="exact") for i in range(3)]
    sells = [fill(NOW_TS - 10, side="SELL", wallet_market="other", condition="exact")]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): buys, (wallet, "SELL"): sells})
    row = trader(payload)
    assert "BUY_SELL_PRESENT" in row["style_labels"]
    assert "FREQUENT_BUY_SELL_ROTATION" not in row["style_labels"]
    assert row["lane_suggestion"] == "COMPARABLE_CANDIDATE"


def test_frequent_buy_sell_rotation_degrades_lane(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    buys = [fill(NOW_TS - 600 + i * 60, wallet_market=f"m{i}", price=0.5) for i in range(3)]
    sells = [fill(NOW_TS - 570 + i * 60, side="SELL", wallet_market=f"m{i}", price=0.55) for i in range(3)]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): buys, (wallet, "SELL"): sells})
    row = trader(payload)
    assert "FREQUENT_BUY_SELL_ROTATION" in row["style_labels"]
    assert row["lane_suggestion"] == "LEARNING_REFERENCE_CANDIDATE"


def test_single_outcome_directional_city_overlap_comparable(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    buys = [fill(NOW_TS - i * 60, wallet_market=f"m{i}", city="Tokyo", condition="at_or_above") for i in range(4)]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): buys, (wallet, "SELL"): []})
    row = trader(payload)
    assert "SINGLE_OUTCOME_DIRECTIONAL" in row["style_labels"]
    assert row["lane_suggestion"] == "COMPARABLE_CANDIDATE"


def test_incompatible_mix_sets_manual_review(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    buys = [fill(NOW_TS - i * 20, wallet_market=f"m{i}", threshold=18 + i, event="tokyo-2026-05-22") for i in range(4)]
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): buys, (wallet, "SELL"): []})
    row = trader(payload)
    assert {"SINGLE_OUTCOME_DIRECTIONAL", "BASKET_BURST"}.issubset(set(row["style_labels"]))
    assert row["manual_review_required"] is True
    assert row["lane_suggestion"] == "REVIEW_REQUIRED"
    assert row["lane_reason"] == "mixed_style_evidence"


def test_wallet_without_activity_waiting_evidence(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    payload, _ = run_payload(module, tmp_path, {(wallet, "BUY"): [], (wallet, "SELL"): []})
    row = trader(payload)
    assert row["style_labels"] == ["UNKNOWN_STYLE"]
    assert row["lane_suggestion"] == "WAITING_EVIDENCE"


def test_query_failed_does_not_block_following_wallets(tmp_path):
    module = load_module()
    w1 = "0x1111111111111111111111111111111111111111"
    w2 = "0x2222222222222222222222222222222222222222"
    payload, _ = run_payload(
        module,
        tmp_path,
        {
            (w1, "BUY"): "RAISE",
            (w1, "SELL"): "RAISE",
            (w2, "BUY"): [fill(NOW_TS - i * 60, wallet_market=f"m{i}") for i in range(3)],
            (w2, "SELL"): [],
        },
        traders={"Failed-Trader": w1, "Next-Trader": w2},
    )
    failed = trader(payload, "Failed-Trader")
    following = trader(payload, "Next-Trader")
    assert failed["query_status"] == "failed"
    assert failed["manual_review_required"] is True
    assert following["query_status"] == "ok_complete"
    assert following["metrics"]["n_fills"] == 3


def test_one_side_failed_is_partial_and_manual_review(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    payload, _ = run_payload(
        module,
        tmp_path,
        {(wallet, "BUY"): [fill(NOW_TS - i * 60, wallet_market=f"m{i}") for i in range(3)], (wallet, "SELL"): "RAISE"},
    )
    row = trader(payload)
    assert row["query_status"] == "partial"
    assert row["sell_query_status"] == "failed"
    assert row["manual_review_required"] is True


def test_cap_detection_marks_ok_capped_and_manual_review(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    buys = [fill(NOW_TS - i, wallet_market=f"m{i}") for i in range(3)]
    payload, _ = run_payload(
        module,
        tmp_path,
        {(wallet, "BUY"): buys, (wallet, "SELL"): []},
        extra_args=["--max-fills-per-wallet", "6"],
    )
    row = trader(payload)
    assert row["buy_capped"] is True
    assert row["sell_capped"] is False
    assert row["max_fills_buy"] == 3
    assert row["max_fills_sell"] == 3
    assert row["query_status"] == "ok_capped"
    assert row["manual_review_required"] is True


def test_external_report_read_and_without_it_external_not_loaded(tmp_path):
    module = load_module()
    wallet = "0x1111111111111111111111111111111111111111"
    paths = base_paths(tmp_path, {"Local-Alias": wallet})
    external = tmp_path / "external.json"
    write_json(
        external,
        {
            "traders": [
                {
                    "pseudonym": "External-Alias",
                    "external_observability": {
                        "proxy_wallet": wallet,
                        "public_profile": {"userName": "Display", "profile_url": "https://example.test/profile"},
                        "leaderboard_weather_all": {"pnl": 12.3},
                        "leaderboard_overall_all": {"vol": 456.7},
                    },
                }
            ]
        },
    )

    def fake_request_json(url: str):
        return []

    module.request_json = fake_request_json
    with_external = module.build_payload(
        module.parse_args(
            [
                "--external-report",
                str(external),
                "--traders-db",
                str(paths["traders_db"]),
                "--traders-intelligence",
                str(paths["intelligence"]),
                "--rate-limit-ms",
                "0",
            ]
        ),
        now_ts=NOW_TS,
    )
    assert with_external["traders"][0]["alias"] == "External-Alias"
    assert with_external["traders"][0]["external"]["pnl_weather_all"] == 12.3
    assert with_external["cohort"]["cohort_mode"] == "external-report"
    assert with_external["cohort"]["n_external_report_wallets"] == 1
    assert with_external["cohort"]["n_deduplicated"] == 0
    assert with_external["traders"][0]["cohort_source"] == "external_report"

    without_external = module.build_payload(
        module.parse_args(
            [
                "--traders-db",
                str(paths["traders_db"]),
                "--traders-intelligence",
                str(paths["intelligence"]),
                "--rate-limit-ms",
                "0",
            ]
        ),
        now_ts=NOW_TS,
    )
    assert without_external["traders"][0]["external"]["profile_url"] == "not_loaded"
    assert without_external["traders"][0]["cohort_source"] == "traders_db"


def test_external_report_default_uses_only_resolved_report_wallets(tmp_path):
    module = load_module()
    external_wallet = "0x1111111111111111111111111111111111111111"
    local_wallet = "0x2222222222222222222222222222222222222222"
    paths = base_paths(tmp_path, {"Local-Only": local_wallet})
    external = tmp_path / "external.json"
    write_json(
        external,
        {
            "traders": [
                {"pseudonym": "External-One", "address": external_wallet},
                {"pseudonym": "Missing-Wallet"},
            ]
        },
    )

    module.request_json = lambda url: []
    payload = module.build_payload(
        module.parse_args(
            [
                "--external-report",
                str(external),
                "--traders-db",
                str(paths["traders_db"]),
                "--traders-intelligence",
                str(paths["intelligence"]),
                "--rate-limit-ms",
                "0",
            ]
        ),
        now_ts=NOW_TS,
    )

    assert payload["cohort"]["cohort_mode"] == "external-report"
    assert payload["cohort"]["n_external_report_rows"] == 2
    assert payload["cohort"]["n_external_report_wallets"] == 1
    assert payload["cohort"]["n_external_report_missing_wallets"] == 1
    assert payload["cohort"]["n_wallets_before_wallet_filter"] == 1
    assert [row["wallet"] for row in payload["traders"]] == [external_wallet]


def test_cohort_union_keeps_broad_registry_behavior(tmp_path):
    module = load_module()
    external_wallet = "0x1111111111111111111111111111111111111111"
    local_wallet = "0x2222222222222222222222222222222222222222"
    paths = base_paths(tmp_path, {"Local-Only": local_wallet})
    external = tmp_path / "external.json"
    write_json(external, {"traders": [{"pseudonym": "External-One", "address": external_wallet}]})

    module.request_json = lambda url: []
    payload = module.build_payload(
        module.parse_args(
            [
                "--external-report",
                str(external),
                "--cohort",
                "union",
                "--traders-db",
                str(paths["traders_db"]),
                "--traders-intelligence",
                str(paths["intelligence"]),
                "--rate-limit-ms",
                "0",
            ]
        ),
        now_ts=NOW_TS,
    )

    assert payload["cohort"]["cohort_mode"] == "union"
    assert payload["cohort"]["cohort_warning"]
    assert payload["cohort"]["n_wallets_before_wallet_filter"] == 2
    assert {row["wallet"] for row in payload["traders"]} == {external_wallet, local_wallet}


def test_cohort_external_report_without_file_fails_clearly():
    module = load_module()
    args = module.parse_args(["--cohort", "external-report"])
    try:
        module.build_payload(args, now_ts=NOW_TS)
    except SystemExit as exc:
        assert "--cohort external-report requires --external-report" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_wallets_filter_applies_after_selected_cohort(tmp_path):
    module = load_module()
    w1 = "0x1111111111111111111111111111111111111111"
    w2 = "0x2222222222222222222222222222222222222222"
    paths = base_paths(tmp_path, {"Local-One": w1, "Local-Two": w2})

    module.request_json = lambda url: []
    payload = module.build_payload(
        module.parse_args(
            [
                "--cohort",
                "local-registry",
                "--wallets",
                w2,
                "--traders-db",
                str(paths["traders_db"]),
                "--traders-intelligence",
                str(paths["intelligence"]),
                "--rate-limit-ms",
                "0",
            ]
        ),
        now_ts=NOW_TS,
    )

    assert payload["cohort"]["cohort_mode"] == "local-registry"
    assert payload["cohort"]["n_wallets_before_wallet_filter"] == 2
    assert payload["cohort"]["n_wallets_after_wallet_filter"] == 1
    assert [row["wallet"] for row in payload["traders"]] == [w2]
