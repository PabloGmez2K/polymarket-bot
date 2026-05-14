#!/usr/bin/env python3
"""weather.gov WRH timeseries client (LOG_ONLY, isolated).

Manual tool for parsing weather.gov/wrh/timeseries source pages. It does not
import bot.py, does not write runtime data, and is not connected to observed
audit, promotion gates, Telegram, scheduler, or trading.
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


OBSERVED_DATASET = "weather_gov_wrh_timeseries"
WRH_TIMESERIES_BASE_URL = "https://www.weather.gov/wrh/timeseries"
WRH_API_KEY_URL = "https://www.weather.gov/source/wrh/apiKey.js"
SYNOPTIC_TIMESERIES_URL = "https://api.synopticdata.com/v2/stations/timeseries"


def build_source_url(site):
    site_clean = normalize_site(site)
    return f"{WRH_TIMESERIES_BASE_URL}?site={quote(site_clean)}"


def normalize_site(site):
    site_clean = str(site or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{3,8}", site_clean):
        raise ValueError(f"Invalid WRH site: {site!r}")
    return site_clean


def normalize_date_local(value):
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"date_local must be YYYY-MM-DD, got {value!r}") from exc


class _TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_row = False
        self._in_cell = False
        self._current_row = []
        self._current_cell = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(_clean_cell("".join(self._current_cell)))
            self._current_cell = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if any(cell for cell in self._current_row):
                self.tables.append(self._current_row)
            self._current_row = []
            self._in_row = False
            self._in_cell = False

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell.append(data)


def _clean_cell(value):
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def _normalize_header(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _rows_from_matrix(matrix):
    if len(matrix) < 2:
        return []
    headers = [_clean_cell(cell) for cell in matrix[0]]
    rows = []
    for raw in matrix[1:]:
        if not any(_clean_cell(cell) for cell in raw):
            continue
        row = {}
        for idx, header in enumerate(headers):
            key = header or f"column_{idx + 1}"
            row[key] = _clean_cell(raw[idx]) if idx < len(raw) else ""
        rows.append(row)
    return rows


def _extract_html_rows(text):
    parser = _TableHTMLParser()
    parser.feed(text)
    candidates = []
    current = []
    for row in parser.tables:
        if row:
            current.append(row)
    if current:
        candidates.append(_rows_from_matrix(current))
    return [row for rows in candidates for row in rows]


def _extract_delimited_rows(text):
    sample = "\n".join(line for line in text.splitlines() if line.strip())[:4096]
    if not sample:
        return []
    delimiters = [",", "\t", "|", ";"]
    dialect = None
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(delimiters))
    except csv.Error:
        for delimiter in delimiters:
            if delimiter in sample:
                class _Dialect(csv.excel):
                    pass
                _Dialect.delimiter = delimiter
                dialect = _Dialect
                break
    if dialect is None:
        return []
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []
    return [
        {str(key): _clean_cell(value) for key, value in row.items() if key is not None}
        for row in reader
        if any(_clean_cell(value) for value in row.values())
    ]


def extract_raw_rows(text):
    """Extract best-effort raw rows from HTML tables or delimited text."""
    if not text or not str(text).strip():
        return [], ["empty response"]
    text = str(text)
    warnings = []
    rows = _extract_html_rows(text) if re.search(r"<\s*(table|tr|td|th)\b", text, re.I) else []
    if not rows:
        rows = _extract_delimited_rows(text)
    if not rows:
        warnings.append("no parseable tabular rows found")
    return rows, warnings


def find_temp_column(rows):
    if not rows:
        return None
    headers = list(rows[0].keys())
    for header in headers:
        normalized = _normalize_header(header)
        if normalized in {"temp", "temperature", "airtemp", "airtemperature"}:
            return header
    for header in headers:
        normalized = _normalize_header(header)
        if "temp" in normalized and "dew" not in normalized and "wetbulb" not in normalized:
            return header
    return None


DATE_PATTERNS = (
    re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"),
    re.compile(r"\b(\d{4})/(\d{1,2})/(\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
)


def _extract_date_local(row):
    priority_values = []
    other_values = []
    for key, value in row.items():
        normalized = _normalize_header(key)
        if any(token in normalized for token in ("date", "time", "valid", "local")):
            priority_values.append(value)
        else:
            other_values.append(value)
    for value in priority_values + other_values:
        parsed = _parse_date_from_text(value)
        if parsed:
            return parsed
    return None


def _parse_date_from_text(value):
    text = str(value or "")
    for idx, pattern in enumerate(DATE_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        parts = [int(part) for part in match.groups()]
        try:
            if idx < 2:
                return date(parts[0], parts[1], parts[2]).isoformat()
            return date(parts[2], parts[0], parts[1]).isoformat()
        except ValueError:
            return None
    return None


def _parse_temperature_c(value, header):
    text = str(value or "").strip()
    if not text or text.upper() in {"M", "NA", "N/A", "NULL", "--"}:
        return None, None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None, None
    temp = float(match.group(0))
    unit_text = f"{header} {text}".lower()
    if re.search(r"\bdeg\s*f\b|\bf\b|fahrenheit", unit_text) and not re.search(r"\bc\b|celsius", unit_text):
        return round((temp - 32.0) * 5.0 / 9.0, 3), "converted_f_to_c"
    return temp, None


def _base_payload(site_clean, date_clean, source_url, warnings):
    return {
        "site": site_clean,
        "date_local": date_clean,
        "source_url": source_url,
        "observed_dataset": OBSERVED_DATASET,
        "temp_column_found": False,
        "temp_column": None,
        "daily_max_c": None,
        "raw_rows_count": 0,
        "raw_rows": [],
        "warnings": warnings,
        "confidence": "none",
    }


def parse_wrh_timeseries(text, site, date_local, source_url=None):
    """Parse WRH timeseries text/HTML and return a structured LOG_ONLY payload."""
    site_clean = normalize_site(site)
    date_clean = normalize_date_local(date_local)
    source_url = source_url or build_source_url(site_clean)
    rows, warnings = extract_raw_rows(text)
    temp_column = find_temp_column(rows)
    matching_values = []
    matched_date_rows = 0
    rows_with_dates = 0
    converted_f = False

    if not temp_column:
        warnings.append("Temp column not found")
    else:
        for row in rows:
            row_date = _extract_date_local(row)
            if row_date:
                rows_with_dates += 1
            if row_date != date_clean:
                continue
            matched_date_rows += 1
            temp_c, unit_warning = _parse_temperature_c(row.get(temp_column), temp_column)
            if unit_warning == "converted_f_to_c":
                converted_f = True
            if temp_c is not None:
                matching_values.append(temp_c)

    if rows and not rows_with_dates:
        warnings.append("no local date values found; cannot calculate requested daily max")
    elif rows_with_dates and not matched_date_rows:
        warnings.append(f"no rows matched date_local={date_clean}")
    if temp_column and matched_date_rows and not matching_values:
        warnings.append("matched rows did not contain numeric Temp values")
    if converted_f:
        warnings.append("explicit Fahrenheit values converted to Celsius")

    daily_max_c = round(max(matching_values), 3) if matching_values else None
    confidence = "high" if temp_column and daily_max_c is not None else "low" if rows else "none"

    return {
        "site": site_clean,
        "date_local": date_clean,
        "source_url": source_url,
        "observed_dataset": OBSERVED_DATASET,
        "temp_column_found": temp_column is not None,
        "temp_column": temp_column,
        "daily_max_c": daily_max_c,
        "raw_rows_count": len(rows),
        "raw_rows": rows,
        "warnings": warnings,
        "confidence": confidence,
    }


def _parse_synoptic_datetime_local(value):
    text = str(value or "").strip()
    if not text:
        return None
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", text)
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        parsed_date = _parse_date_from_text(text)
        return datetime.strptime(parsed_date, "%Y-%m-%d") if parsed_date else None


def parse_synoptic_timeseries_json(data, site, date_local, source_url=None, data_url=None):
    """Parse Synoptic JSON used by WRH timeseries and return the standard payload."""
    site_clean = normalize_site(site)
    date_clean = normalize_date_local(date_local)
    source_url = source_url or build_source_url(site_clean)
    payload = _base_payload(site_clean, date_clean, source_url, [])
    if data_url:
        payload["source_data_url"] = data_url
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        payload["warnings"].append("Synoptic payload is not a JSON object")
        return payload

    summary = data.get("SUMMARY") if isinstance(data.get("SUMMARY"), dict) else {}
    if summary.get("RESPONSE_CODE") not in (1, "1", None):
        payload["warnings"].append(
            f"Synoptic response not successful: {summary.get('RESPONSE_MESSAGE') or summary.get('RESPONSE_CODE')}"
        )
        return payload

    stations = data.get("STATION") or []
    if not stations:
        payload["warnings"].append("Synoptic payload has no STATION records")
        return payload
    station = stations[0] if isinstance(stations[0], dict) else {}
    observations = station.get("OBSERVATIONS") if isinstance(station.get("OBSERVATIONS"), dict) else {}
    timestamps = observations.get("date_time") or []
    temps = observations.get("air_temp_set_1") or []
    payload["temp_column_found"] = isinstance(temps, list) and bool(temps)
    payload["temp_column"] = "air_temp_set_1" if payload["temp_column_found"] else None

    if not timestamps:
        payload["warnings"].append("Synoptic payload has no date_time observations")
    if not payload["temp_column_found"]:
        payload["warnings"].append("Temp column not found")

    rows = []
    matching_values = []
    for idx, stamp in enumerate(timestamps):
        temp_value = temps[idx] if isinstance(temps, list) and idx < len(temps) else None
        row = {
            "date_time": stamp,
            "air_temp_set_1": temp_value,
        }
        rows.append(row)
        parsed_dt = _parse_synoptic_datetime_local(stamp)
        if not parsed_dt or parsed_dt.date().isoformat() != date_clean:
            continue
        temp_c, _ = _parse_temperature_c(temp_value, "air_temp_set_1")
        if temp_c is not None:
            matching_values.append(temp_c)

    payload["raw_rows"] = rows
    payload["raw_rows_count"] = len(rows)
    if timestamps and not matching_values:
        payload["warnings"].append(f"no numeric Temp values matched date_local={date_clean}")
    if matching_values:
        payload["daily_max_c"] = round(max(matching_values), 3)
    payload["confidence"] = "high" if payload["temp_column_found"] and payload["daily_max_c"] is not None else "low" if rows else "none"
    return payload


def _read_url(url, timeout=30, headers=None):
    request = Request(url, headers=headers or {"User-Agent": "polymarket-bot-wrh-audit/1.0"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_wrh_api_token(timeout=30):
    text = _read_url(WRH_API_KEY_URL, timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": WRH_TIMESERIES_BASE_URL,
    })
    match = re.search(r"mesoToken\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        raise ValueError("Could not find mesoToken in WRH apiKey.js")
    return match.group(1)


def build_synoptic_data_url(site, date_local, token):
    site_clean = normalize_site(site)
    date_obj = datetime.strptime(normalize_date_local(date_local), "%Y-%m-%d").date()
    start_date = date_obj - timedelta(days=1)
    end_date = date_obj + timedelta(days=1)
    query = {
        "STID": site_clean,
        "showemptystations": "1",
        "start": start_date.strftime("%Y%m%d") + "0000",
        "end": end_date.strftime("%Y%m%d") + "2359",
        "complete": "1",
        "token": token,
        "obtimezone": "local",
    }
    return f"{SYNOPTIC_TIMESERIES_URL}?{urlencode(query)}"


def _redact_token_from_url(url):
    return re.sub(r"([?&]token=)[^&]+", r"\1<redacted>", url)


def fetch_wrh_timeseries(site, date_local, timeout=30):
    source_url = build_source_url(site)
    token = fetch_wrh_api_token(timeout=timeout)
    data_url = build_synoptic_data_url(site, date_local, token)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": source_url,
        "Origin": "https://www.weather.gov",
    }
    text = _read_url(data_url, timeout=timeout, headers=headers)
    return json.loads(text), source_url, data_url


def fetch_wrh_page_html(site, timeout=30):
    url = build_source_url(site)
    return _read_url(url, timeout=timeout), url


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="weather.gov WRH timeseries parser (LOG_ONLY, isolated)"
    )
    parser.add_argument("--site", required=True, help="WRH site/ICAO, e.g. LTFM")
    parser.add_argument("--date-local", required=True, help="Local date YYYY-MM-DD")
    parser.add_argument("--input-file", help="Parse a saved fixture instead of fetching")
    parser.add_argument("--fetch", action="store_true", help="Fetch WRH-backed Synoptic JSON used by weather.gov")
    parser.add_argument("--fetch-html", action="store_true", help="Fetch and parse only the initial weather.gov HTML page")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print full JSON payload")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.input_file:
            text = Path(args.input_file).read_text(encoding="utf-8")
            source_url = build_source_url(args.site)
            payload = parse_wrh_timeseries(text, args.site, args.date_local, source_url=source_url)
        elif args.fetch:
            data, source_url, data_url = fetch_wrh_timeseries(args.site, args.date_local, timeout=args.timeout)
            payload = parse_synoptic_timeseries_json(
                data,
                args.site,
                args.date_local,
                source_url=source_url,
                data_url=_redact_token_from_url(data_url),
            )
        elif args.fetch_html:
            text, source_url = fetch_wrh_page_html(args.site, timeout=args.timeout)
            payload = parse_wrh_timeseries(text, args.site, args.date_local, source_url=source_url)
        else:
            raise ValueError("provide --input-file for fixture parsing, --fetch for data mode, or --fetch-html")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({
            "site": payload["site"],
            "date_local": payload["date_local"],
            "observed_dataset": payload["observed_dataset"],
            "daily_max_c": payload["daily_max_c"],
            "raw_rows_count": payload["raw_rows_count"],
            "temp_column_found": payload["temp_column_found"],
            "confidence": payload["confidence"],
            "warnings": payload["warnings"],
        }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
