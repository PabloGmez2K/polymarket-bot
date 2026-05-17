import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import source_parity_audit as parity


def _config(city="Jeddah", icao="OEJN"):
    return parity.AuditConfig(
        city=city,
        icao=icao,
        lat=21.6796,
        lon=39.1565,
        tz="Asia/Riyadh",
        wu_url=f"https://www.wunderground.com/history/daily/sa/jeddah/{icao}",
    )


def _gamma_market(slug, icao="OEJN", yes=True):
    return {
        "id": slug,
        "slug": slug,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["1", "0"]' if yes else '["0", "1"]',
        "resolutionSource": f"https://www.wunderground.com/history/daily/sa/jeddah/{icao}",
    }


def test_generic_exact_slug_round_trips_city_and_date():
    slug = parity.build_exact_slug("Jeddah", "2026-04-18", 39)

    assert slug == "highest-temperature-in-jeddah-on-april-18-2026-39c"
    assert parity.parse_exact_slug(slug, "Jeddah") == {
        "date_local": "2026-04-18",
        "strike_c": 39.0,
    }
    assert parity.parse_exact_slug(slug, "Beijing") is None


def test_gamma_settlement_comparison_uses_generic_city_and_icao():
    config = _config()
    dates = [f"2026-04-{day:02d}" for day in range(1, 11)]
    blocked = []
    for day in dates:
        blocked.append({"date_local": day, "condition": "exact", "strike_c": 38.0, "outcome": "No"})
        blocked.append({"date_local": day, "condition": "exact", "strike_c": 39.0, "outcome": "Yes"})

    def fetcher(slug):
        if not (slug.endswith("-38c") or slug.endswith("-39c")):
            raise ValueError("not found")
        return _gamma_market(slug, yes=slug.endswith("-39c"))

    report = parity.build_gamma_settlement_comparisons(
        blocked,
        {day: 37.0 for day in dates},
        config,
        fetcher=fetcher,
        neighbor_radius=0,
    )

    assert report["verdict"] == "SETTLEMENT_GAMMA_PARITY_FAIL"
    assert report["comparisons"][0]["settlement_temp_c"] == 39.0
    assert report["comparisons"][0]["delta_c"] == -2.0


def test_build_report_filters_requested_city(tmp_path):
    blocked = tmp_path / "blocked.jsonl"
    blocked.write_text(
        '{"match_key":"Jeddah|2026-04-18|exact|39|C","city":"Jeddah","date":"2026-04-18","condition":"exact","outcome":"Yes"}\n'
        '{"match_key":"Beijing|2026-04-18|exact|27|C","city":"Beijing","date":"2026-04-18","condition":"exact","outcome":"Yes"}\n',
        encoding="utf-8",
    )
    om_csv = tmp_path / "om.csv"
    om_csv.write_text("date,open_meteo_max_c\n2026-04-18,37\n", encoding="utf-8")

    args = SimpleNamespace(
        city="Jeddah",
        icao="OEJN",
        lat=21.6796,
        lon=39.1565,
        tz="Asia/Riyadh",
        wu_url="https://www.wunderground.com/history/daily/sa/jeddah/OEJN",
        start="2026-04-18",
        end="2026-04-18",
        days=60,
        open_meteo_csv=str(om_csv),
        wu_csv=None,
        settlement_from_gamma=False,
        gamma_neighbor_radius=3,
        blocked_jsonl=str(blocked),
    )

    report = parity.build_report(args)

    assert report["verdict"] == "WU_FETCHER_MISSING"
    assert report["city"] == "Jeddah"
    assert len(report["blocked_table"]) == 1
    assert report["blocked_table"][0]["match_key"].startswith("Jeddah|")
