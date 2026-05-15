import sys
from argparse import Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import source_fidelity_resolver as resolver


def _mapping(**meta):
    return {
        "city": "Istanbul",
        "resolution_icao": meta,
        "resolution_station": {"name": "Istanbul Airport"},
        "warnings": [],
    }


def test_parse_gamma_rules_extracts_wrh_site_and_temp_column():
    parsed = resolver.parse_gamma_source_text({
        "question": "Will the highest temperature in Istanbul be 23C on May 13?",
        "description": (
            "This market will resolve to the temperature range that contains the highest "
            "temperature recorded by NOAA at the Istanbul Airport (LTFM). The resolution "
            "source is https://www.weather.gov/wrh/timeseries?site=LTFM, specifically "
            "the highest reading under the Temp column after switching to metric units."
        ),
    })

    assert parsed["source_types"] == ["noaa", "weather_gov_wrh"]
    assert parsed["weather_gov_sites"] == ["LTFM"]
    assert parsed["icao_mentions"] == ["LTFM"]
    assert parsed["station_label"] == "Istanbul Airport"
    assert parsed["mentions_temp_column"] is True
    assert parsed["mentions_metric_units"] is True


def test_source_match_confirmed_for_explicit_wrh_site_mapping():
    parsed = resolver.parse_gamma_source_text({
        "description": "NOAA source: https://www.weather.gov/wrh/timeseries?site=LTFM Temp column"
    })

    comparison = resolver.compare_sources(
        _mapping(icao="LTFM", weather_gov_timeseries_site="LTFM", wu_url="https://www.wunderground.com/history/daily/LTFM/date/{date}"),
        [parsed],
    )

    assert comparison["verdict"] == resolver.SOURCE_MATCH_CONFIRMED
    assert comparison["wrh_ncei_separation"] == "separate_not_equivalent"


def test_source_partial_for_noaa_without_dataset_specificity():
    parsed = resolver.parse_gamma_source_text({
        "description": "The resolution source will be information from NOAA at Haneda Airport."
    })

    comparison = resolver.compare_sources(
        _mapping(icao="RJTT", noaa_station_id="47671099999", noaa_daily_station_id="JA000047670"),
        [parsed],
    )

    assert comparison["verdict"] == resolver.SOURCE_PARTIAL
    assert any("dataset_contract_needs_human_review" in reason for reason in comparison["reasons"])


def test_source_ambiguous_when_no_source_text_available():
    comparison = resolver.compare_sources(_mapping(icao="RJTT"), [])

    assert comparison["verdict"] == resolver.SOURCE_AMBIGUOUS
    assert comparison["reasons"] == ["no_gamma_or_documented_source_text_available"]


def test_source_mismatch_for_different_wrh_site():
    parsed = resolver.parse_gamma_source_text({
        "description": "Resolution source: https://www.weather.gov/wrh/timeseries?site=KXYZ"
    })

    comparison = resolver.compare_sources(
        _mapping(icao="LTFM", weather_gov_timeseries_site="LTFM"),
        [parsed],
    )

    assert comparison["verdict"] == resolver.SOURCE_MISMATCH
    assert any("weather_gov_wrh_site_mismatch" in reason for reason in comparison["reasons"])


def test_wrh_and_ncei_are_not_classified_as_same_source():
    parsed = resolver.parse_gamma_source_text({
        "description": "Resolution source: https://www.weather.gov/wrh/timeseries?site=LTFM"
    })

    comparison = resolver.compare_sources(
        _mapping(icao="LTFM", noaa_station_id="99999999999", noaa_daily_station_id="TUM00000000"),
        [parsed],
    )

    assert comparison["verdict"] == resolver.SOURCE_MISMATCH
    assert comparison["internal_source_types"] == ["noaa_ncei"]
    assert comparison["external_source_types"] == ["weather_gov_wrh"]
    assert comparison["wrh_ncei_separation"] == "separate_not_equivalent"


def test_markdown_has_log_only_and_no_operational_authorization_markers():
    args = Namespace(
        city="Istanbul",
        blocked_resolutions=[],
        output_dir=str(REPO_ROOT / "data" / "source_audits"),
        docs_dir=str(REPO_ROOT / "docs" / "source_audits"),
        bot_path=str(REPO_ROOT / "bot.py"),
        fetch_gamma=False,
        timeout=30,
        slug=[],
        no_write=True,
    )
    report = resolver.build_report(args, now="2026-05-15T00:00:00+00:00")

    markdown = resolver.render_markdown(report)

    assert "LOG_ONLY" in markdown
    assert "Human review is required" in markdown
    for marker in resolver.OPERATIONAL_AUTHORIZATION_MARKERS:
        assert marker not in markdown


def test_bypasses_poisoned_proxy_env(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    assert resolver.should_bypass_proxy_env() is True
