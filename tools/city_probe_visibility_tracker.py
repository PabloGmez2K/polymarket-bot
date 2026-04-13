#!/usr/bin/env python3
"""Persist visibility history for target cities from settlement probe snapshots."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_TRACKER_PATH = REPO_ROOT / "data" / "city_probe_visibility_tracker.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_probe_visibility_tracker_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Persiste la visibilidad de ciudades objetivo a partir de snapshots del settlement probe."
    )
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--targets", default="Shanghai,Chicago")
    parser.add_argument("--tracker-output", default=str(DEFAULT_TRACKER_PATH))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str, required=True):
    path = Path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_targets(raw):
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_probe_snapshot(probe, targets):
    generated_at = probe.get("generated_at") or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    markets = probe.get("markets", [])
    cities = {}
    for city in targets:
        rows = [row for row in markets if row.get("city") == city]
        conditions = Counter(row.get("condition", "") for row in rows)
        cities[city] = {
            "market_count": len(rows),
            "comparable_market_count": sum(
                1 for row in rows
                if row.get("market_prob_yes") is not None and 0.20 <= float(row.get("market_prob_yes")) <= 0.80
            ),
            "conditions": dict(conditions),
            "questions": [row.get("question") for row in rows[:6]],
        }
    visible_cities = [city for city, row in cities.items() if row["market_count"] > 0]
    simultaneous_visibility = len(visible_cities) == len(targets) and bool(targets)
    return {
        "probe_generated_at": generated_at,
        "targets": targets,
        "visible_cities": visible_cities,
        "simultaneous_visibility": simultaneous_visibility,
        "cities": cities,
    }


def merge_history(existing, snapshot):
    payload = existing if isinstance(existing, dict) else {}
    history = payload.setdefault("history", [])
    known_keys = {
        (row.get("probe_generated_at"), tuple(row.get("targets", [])))
        for row in history
        if isinstance(row, dict)
    }
    key = (snapshot.get("probe_generated_at"), tuple(snapshot.get("targets", [])))
    if key not in known_keys:
        history.append(snapshot)
    history.sort(key=lambda row: str(row.get("probe_generated_at", "")))
    return payload


def summarize(payload, targets):
    history = payload.get("history", [])
    city_counts = {city: 0 for city in targets}
    city_market_totals = {city: 0 for city in targets}
    simultaneous_count = 0
    for row in history:
        if not isinstance(row, dict):
            continue
        if row.get("simultaneous_visibility"):
            simultaneous_count += 1
        for city in targets:
            city_row = row.get("cities", {}).get(city, {})
            market_count = int(city_row.get("market_count", 0) or 0)
            if market_count > 0:
                city_counts[city] += 1
                city_market_totals[city] += market_count
    latest = history[-1] if history else {}
    return {
        "n_snapshots": len(history),
        "simultaneous_visibility_count": simultaneous_count,
        "city_visibility_counts": city_counts,
        "city_market_totals": city_market_totals,
        "latest_probe_generated_at": latest.get("probe_generated_at"),
    }


def render_markdown(payload):
    summary = payload["summary"]
    latest = payload["history"][-1] if payload.get("history") else {}
    lines = [
        "# City Probe Visibility Tracker",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Snapshots tracked: `{summary['n_snapshots']}`",
        f"- Simultaneous visibility count: `{summary['simultaneous_visibility_count']}`",
        f"- Latest probe: `{summary['latest_probe_generated_at']}`",
        "",
        "## Visibility Counts",
        "",
        "| City | Snapshots visible | Total markets seen |",
        "| --- | --- | --- |",
    ]
    for city, count in summary["city_visibility_counts"].items():
        lines.append(f"| {city} | {count} | {summary['city_market_totals'].get(city, 0)} |")
    lines.extend([
        "",
        "## Latest Snapshot",
        "",
        f"- Simultaneous visibility: `{latest.get('simultaneous_visibility')}`",
        f"- Visible cities: `{', '.join(latest.get('visible_cities', []))}`",
        "",
        "| City | Market count | Comparable markets | Conditions |",
        "| --- | --- | --- | --- |",
    ])
    for city, row in (latest.get("cities", {}) or {}).items():
        conditions = ", ".join(f"{k}:{v}" for k, v in row.get("conditions", {}).items())
        lines.append(
            f"| {city} | {row.get('market_count', 0)} | {row.get('comparable_market_count', 0)} | {conditions} |"
        )
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    targets = normalize_targets(args.targets)
    probe = load_json(args.probe, required=True)
    existing = load_json(args.tracker_output, required=False)
    snapshot = build_probe_snapshot(probe, targets)
    payload = merge_history(existing, snapshot)
    payload["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload["targets"] = targets
    payload["summary"] = summarize(payload, targets)

    tracker_path = ensure_parent(args.tracker_output)
    md_path = ensure_parent(args.md_output)
    tracker_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Visibility tracker written to {tracker_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
