#!/usr/bin/env python3
"""Bot Brain v0 read-only query tool.

Connects existing LOG_ONLY artifacts so humans can ask what the bot already
knows about a city, cycle, eval key, match key, or recent overview.

No BUY/SELL/SKIP. No BANKROLL. No DB writes. No runtime/env/Railway changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY/read-only. Pointer and linkage report only; no trading "
    "authorization, no BANKROLL, no BUY/SELL/SKIP, no city-mode, scheduler, "
    "env var, DB, Railway, Telegram, guard, stop-loss, Fase C, or Truth "
    "Pipeline change."
)


ARTIFACTS = {
    "cycles_history": ("jsonl", "data/cycles_history.jsonl"),
    "funnel_observability": ("jsonl", "data/funnel_observability_log_only.jsonl"),
    "funnel_latest": ("json", "data/funnel_observability_latest.json"),
    "bot_signal_evaluations": ("jsonl", "data/bot_signal_evaluations.jsonl"),
    "blocked_signals_resolutions": ("jsonl", "data/blocked_signals_resolutions.jsonl"),
    "trade_lifecycle": ("json", "data/trade_lifecycle.json"),
    "agent_events": ("jsonl", "agent_events.jsonl"),
    "context": ("text", "CONTEXTO.md"),
    "history": ("text", "HISTORIAL_SESIONES.md"),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bot Brain v0 LOG_ONLY read-only query tool")
    parser.add_argument("--scope", required=True, help="overview, city:<name>, cycle:<n>, eval_key:<key>, or match_key:<key>")
    parser.add_argument("--window", default="7d", help="Lookback window such as 7d, 14d, 24h, or all")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    parser.add_argument("--data-dir", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--now", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def record_ts(record: dict[str, Any]) -> datetime | None:
    for key in ("timestamp_utc", "ts_utc", "timestamp", "created_at", "resolved_at", "closed_at"):
        ts = parse_ts(record.get(key))
        if ts:
            return ts
    return None


def parse_window(window: str | None, now: datetime) -> tuple[datetime | None, str]:
    text = str(window or "7d").strip().lower()
    if text in {"all", "none", "0", "0d"}:
        return None, "all"
    match = re.fullmatch(r"(\d+)([dh])", text)
    if not match:
        return now - timedelta(days=7), "7d"
    amount = int(match.group(1))
    unit = match.group(2)
    delta = timedelta(days=amount) if unit == "d" else timedelta(hours=amount)
    return now - delta, text


def source_pointer(path: Path, line: int | None = None) -> dict[str, Any]:
    pointer: dict[str, Any] = {"path": str(path)}
    if line is not None:
        pointer["line"] = line
    return pointer


def read_json(path: Path) -> tuple[Any, dict[str, Any]]:
    meta = {"path": str(path), "present": path.exists(), "rows": 0, "errors": []}
    if not path.exists():
        return None, meta
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        meta["errors"].append(f"parse_error: {exc}")
        return None, meta
    meta["rows"] = len(data) if isinstance(data, list) else 1
    return data, meta


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta = {"path": str(path), "present": path.exists(), "rows": 0, "errors": []}
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows, meta
    try:
        for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                meta["errors"].append(f"line {line_no}: invalid_json")
                continue
            if isinstance(parsed, dict):
                parsed["_source_file"] = str(path)
                parsed["_source_line"] = line_no
                rows.append(parsed)
    except Exception as exc:
        meta["errors"].append(f"read_error: {exc}")
    meta["rows"] = len(rows)
    return rows, meta


def read_text(path: Path) -> tuple[str, dict[str, Any]]:
    meta = {"path": str(path), "present": path.exists(), "rows": 0, "errors": []}
    if not path.exists():
        return "", meta
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        meta["errors"].append(f"read_error: {exc}")
        return "", meta
    meta["rows"] = len(text.splitlines())
    return text, meta


def artifact_path(repo_root: Path, data_dir: Path, rel_path: str) -> Path:
    if rel_path.startswith("data/"):
        return data_dir / rel_path.removeprefix("data/")
    return repo_root / rel_path


def load_artifacts(repo_root: Path, data_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    loaded: dict[str, Any] = {}
    inventory: dict[str, dict[str, Any]] = {}
    for name, (kind, rel_path) in ARTIFACTS.items():
        path = artifact_path(repo_root, data_dir, rel_path)
        if kind == "jsonl":
            data, meta = read_jsonl(path)
        elif kind == "json":
            data, meta = read_json(path)
        else:
            data, meta = read_text(path)
        loaded[name] = data
        inventory[name] = meta
    return loaded, inventory


def apply_window(rows: list[dict[str, Any]], cutoff: datetime | None) -> list[dict[str, Any]]:
    if cutoff is None:
        return list(rows)
    filtered = []
    for row in rows:
        ts = record_ts(row)
        if ts is None or ts >= cutoff:
            filtered.append(row)
    return filtered


def normalize_city(value: Any) -> str:
    return str(value or "").strip().casefold()


def json_mentions(record: Any, needle: str) -> bool:
    try:
        return needle.casefold() in json.dumps(record, ensure_ascii=False, default=str).casefold()
    except Exception:
        return False


def record_mentions_city(record: dict[str, Any], city: str) -> bool:
    target = normalize_city(city)
    if normalize_city(record.get("city")) == target:
        return True
    for key in ("buys", "scanned_markets", "records", "positions"):
        value = record.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and normalize_city(item.get("city")) == target:
                    return True
    return json_mentions(record, city)


def compact_record(record: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    compact = {key: record.get(key) for key in keys if key in record}
    pointer = source_pointer(Path(str(record.get("_source_file"))), record.get("_source_line")) if record.get("_source_file") else None
    if pointer:
        compact["evidence_pointer"] = pointer
    return compact


def cycle_matches(record: dict[str, Any], cycle_value: str) -> bool:
    return (
        str(record.get("cycle_number", "")).strip() == cycle_value
        or str(record.get("logic_cycle_number", "")).strip() == cycle_value
        or str(record.get("cycle_id", "")).strip() == cycle_value
    )


def build_eval_resolution_join(evals: list[dict[str, Any]], resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    eval_by_key = {str(row.get("eval_key")): row for row in evals if row.get("eval_key")}
    resolution_by_key = {str(row.get("match_key")): row for row in resolutions if row.get("match_key")}
    eval_keys = set(eval_by_key)
    match_keys = set(resolution_by_key)
    joined = sorted(eval_keys & match_keys)
    orphan_evals = sorted(eval_keys - match_keys)
    orphan_resolutions = sorted(match_keys - eval_keys)
    return {
        "joined_count": len(joined),
        "orphan_eval_count": len(orphan_evals),
        "orphan_resolution_count": len(orphan_resolutions),
        "sample_joined_keys": joined[:10],
        "sample_orphan_eval_keys": orphan_evals[:10],
        "sample_orphan_resolution_keys": orphan_resolutions[:10],
        "_eval_by_key": eval_by_key,
        "_resolution_by_key": resolution_by_key,
    }


def build_cycle_funnel_link(cycles: list[dict[str, Any]], funnels: list[dict[str, Any]]) -> dict[str, Any]:
    funnel_keys = {
        (
            str(row.get("cycle_number", "")).strip(),
            str(row.get("logic_cycle_number", "")).strip(),
        )
        for row in funnels
    }
    missing = []
    for cycle in cycles:
        key = (
            str(cycle.get("cycle_number", "")).strip(),
            str(cycle.get("logic_cycle_number", "")).strip(),
        )
        if key not in funnel_keys:
            missing.append(
                {
                    "cycle_number": cycle.get("cycle_number"),
                    "logic_cycle_number": cycle.get("logic_cycle_number"),
                    "timestamp_utc": cycle.get("timestamp_utc"),
                }
            )
    return {"cycle_without_funnel_count": len(missing), "sample_cycle_without_funnel": missing[:10]}


def text_matches(text: str, term: str, path: str, max_matches: int = 5) -> list[dict[str, Any]]:
    if not term or not text:
        return []
    term_cf = term.casefold()
    matches = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if term_cf in line.casefold():
            matches.append({"path": path, "line": line_no, "snippet": line.strip()[:220]})
            if len(matches) >= max_matches:
                break
    return matches


def collect_evidence_pointers(report: dict[str, Any], inventory: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pointers = []
    for name, meta in inventory.items():
        if meta.get("present"):
            pointers.append({"artifact": name, "path": meta.get("path"), "rows": meta.get("rows", 0)})
    return pointers


def summarize_artifacts(inventory: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    present = {name: meta for name, meta in inventory.items() if meta.get("present")}
    missing = [name for name, meta in inventory.items() if not meta.get("present")]
    return {
        name: {
            "path": meta.get("path"),
            "present": bool(meta.get("present")),
            "rows": meta.get("rows", 0),
            "errors": meta.get("errors", []),
        }
        for name, meta in inventory.items()
    }, missing


def build_brain_report(
    scope: str,
    window: str = "7d",
    repo_root: Path | None = None,
    data_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root or REPO_ROOT)
    data_dir = Path(data_dir or (repo_root / "data"))
    now = now or datetime.now(timezone.utc)
    cutoff, normalized_window = parse_window(window, now)
    loaded, inventory = load_artifacts(repo_root, data_dir)

    cycles = apply_window(loaded["cycles_history"], cutoff)
    funnels = apply_window(loaded["funnel_observability"], cutoff)
    evals = apply_window(loaded["bot_signal_evaluations"], cutoff)
    resolutions = apply_window(loaded["blocked_signals_resolutions"], cutoff)
    agent_events = apply_window(loaded["agent_events"], cutoff)
    join = build_eval_resolution_join(evals, resolutions)
    cycle_funnel = build_cycle_funnel_link(cycles, funnels)
    artifact_inventory, missing_artifacts = summarize_artifacts(inventory)

    parsed_scope = parse_scope(scope)
    report: dict[str, Any] = {
        "schema_version": "bot_brain_v0",
        "generated_at": now.isoformat(),
        "scope": scope,
        "scope_type": parsed_scope["type"],
        "scope_value": parsed_scope.get("value"),
        "window": normalized_window,
        "log_only": True,
        "trading_authorization": "NO_ACTION",
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "artifact_inventory": artifact_inventory,
        "missing_artifacts": missing_artifacts,
        "undersampled": False,
        "no_match": False,
        "evidence_pointers": [],
        "connections": {
            "eval_resolution_join": {
                key: value for key, value in join.items() if not key.startswith("_")
            },
            "cycle_funnel_link": cycle_funnel,
        },
        "results": {},
    }

    scope_type = parsed_scope["type"]
    scope_value = str(parsed_scope.get("value") or "")

    if scope_type == "overview":
        report["results"] = build_overview(cycles, funnels, evals, resolutions, agent_events)
    elif scope_type == "city":
        report["results"] = build_city_result(scope_value, cycles, funnels, evals, resolutions, loaded, inventory)
    elif scope_type == "cycle":
        report["results"] = build_cycle_result(scope_value, cycles, funnels, evals, resolutions)
    elif scope_type in {"eval_key", "match_key"}:
        report["results"] = build_key_result(scope_type, scope_value, join)
    else:
        report["no_match"] = True
        report["results"] = {"error": "unsupported_scope"}

    report["evidence_pointers"] = collect_evidence_pointers(report, inventory)
    report["no_match"] = bool(report["no_match"] or not report["results"].get("matches_found", True))
    report["undersampled"] = bool(
        report["undersampled"]
        or (scope_type == "overview" and report["results"].get("cycles_count", 0) < 2)
        or (scope_type == "city" and report["results"].get("total_mentions", 0) < 3)
    )
    return report


def parse_scope(scope: str) -> dict[str, str]:
    text = str(scope or "").strip()
    if text == "overview":
        return {"type": "overview"}
    if ":" not in text:
        return {"type": "unknown", "value": text}
    kind, value = text.split(":", 1)
    kind = kind.strip()
    value = value.strip()
    if kind in {"city", "cycle", "eval_key", "match_key"} and value:
        return {"type": kind, "value": value}
    return {"type": "unknown", "value": text}


def build_overview(
    cycles: list[dict[str, Any]],
    funnels: list[dict[str, Any]],
    evals: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    agent_events: list[dict[str, Any]],
) -> dict[str, Any]:
    cities = set()
    for rows in (cycles, evals, resolutions):
        for row in rows:
            if row.get("city"):
                cities.add(str(row.get("city")))
            for key in ("buys", "scanned_markets"):
                value = row.get(key)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get("city"):
                            cities.add(str(item.get("city")))
    return {
        "matches_found": bool(cycles or funnels or evals or resolutions),
        "cycles_count": len(cycles),
        "funnel_records_count": len(funnels),
        "bot_signal_evaluations_count": len(evals),
        "blocked_resolutions_count": len(resolutions),
        "agent_events_count": len(agent_events),
        "cities_seen_count": len(cities),
        "sample_cities_seen": sorted(cities)[:20],
    }


def build_city_result(
    city: str,
    cycles: list[dict[str, Any]],
    funnels: list[dict[str, Any]],
    evals: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    loaded: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cycle_hits = [row for row in cycles if record_mentions_city(row, city)]
    eval_hits = [row for row in evals if record_mentions_city(row, city)]
    resolution_hits = [row for row in resolutions if record_mentions_city(row, city)]
    funnel_hits = [row for row in funnels if record_mentions_city(row, city)]
    text_hits = (
        text_matches(loaded.get("context") or "", city, inventory["context"]["path"], 3)
        + text_matches(loaded.get("history") or "", city, inventory["history"]["path"], 3)
    )
    total = len(cycle_hits) + len(eval_hits) + len(resolution_hits) + len(funnel_hits) + len(text_hits)
    return {
        "matches_found": total > 0,
        "city": city,
        "total_mentions": total,
        "cycles_count": len(cycle_hits),
        "funnel_records_count": len(funnel_hits),
        "evaluations_count": len(eval_hits),
        "blocked_resolutions_count": len(resolution_hits),
        "text_matches_count": len(text_hits),
        "sample_cycles": [
            compact_record(row, ["cycle_number", "logic_cycle_number", "timestamp_utc", "mode", "scan", "buys"])
            for row in cycle_hits[:5]
        ],
        "sample_evaluations": [
            compact_record(row, ["cycle_id", "eval_key", "ts_utc", "city", "date_iso", "condition", "would_buy", "skip_or_block_reason"])
            for row in eval_hits[:5]
        ],
        "sample_blocked_resolutions": [
            compact_record(row, ["match_key", "city", "date", "date_iso", "condition", "bot_evaluation_join_status", "win_for_trader"])
            for row in resolution_hits[:5]
        ],
        "text_matches": text_hits,
    }


def build_cycle_result(
    cycle_value: str,
    cycles: list[dict[str, Any]],
    funnels: list[dict[str, Any]],
    evals: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> dict[str, Any]:
    cycle_hits = [row for row in cycles if cycle_matches(row, cycle_value)]
    funnel_hits = [row for row in funnels if cycle_matches(row, cycle_value)]
    eval_hits = [row for row in evals if cycle_matches(row, cycle_value)]
    resolution_hits = [row for row in resolutions if cycle_matches(row, cycle_value)]
    return {
        "matches_found": bool(cycle_hits or funnel_hits or eval_hits or resolution_hits),
        "cycle": cycle_value,
        "cycles_count": len(cycle_hits),
        "funnel_records_count": len(funnel_hits),
        "evaluations_count": len(eval_hits),
        "blocked_resolutions_count": len(resolution_hits),
        "cycles": [
            compact_record(row, ["cycle_number", "logic_cycle_number", "timestamp_utc", "mode", "scan", "buys", "scanned_markets"])
            for row in cycle_hits[:5]
        ],
        "funnel_records": [
            compact_record(row, ["cycle_number", "logic_cycle_number", "ts_utc", "discovered_markets_unique", "prefiltered", "edge", "shadow_edge", "selected", "real_buy"])
            for row in funnel_hits[:5]
        ],
        "sample_evaluations": [
            compact_record(row, ["cycle_id", "eval_key", "city", "date_iso", "would_buy", "skip_or_block_reason"])
            for row in eval_hits[:5]
        ],
    }


def build_key_result(scope_type: str, key: str, join: dict[str, Any]) -> dict[str, Any]:
    eval_row = join["_eval_by_key"].get(key)
    resolution_row = join["_resolution_by_key"].get(key)
    if scope_type == "eval_key" and not eval_row:
        return {"matches_found": False, "key": key, "join_status": "no_match"}
    if scope_type == "match_key" and not resolution_row:
        return {"matches_found": False, "key": key, "join_status": "no_match"}
    if eval_row and resolution_row:
        status = "joined"
    elif eval_row:
        status = "eval_without_resolution"
    else:
        status = "resolution_without_eval"
    return {
        "matches_found": True,
        "key": key,
        "join_status": status,
        "evaluation": compact_record(
            eval_row or {},
            ["cycle_id", "eval_key", "ts_utc", "city", "date_iso", "condition", "threshold", "would_buy", "bot_edge_pct_at_signal", "skip_or_block_reason"],
        )
        if eval_row
        else None,
        "resolution": compact_record(
            resolution_row or {},
            ["match_key", "city", "date", "date_iso", "condition", "threshold", "bot_evaluation_join_status", "win_for_trader", "reason_blocked"],
        )
        if resolution_row
        else None,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Bot Brain v0",
        "",
        f"Scope: `{report.get('scope')}`",
        f"Window: `{report.get('window')}`",
        "",
        "LOG_ONLY / NO_ACTION. No trading authorization.",
        "",
        "## Result",
    ]
    results = report.get("results", {})
    for key in ("matches_found", "city", "cycle", "key", "join_status", "cycles_count", "funnel_records_count", "evaluations_count", "blocked_resolutions_count", "total_mentions"):
        if key in results:
            lines.append(f"- `{key}`: `{results.get(key)}`")
    if report.get("missing_artifacts"):
        lines.extend(["", "## Missing Artifacts"])
        for name in report["missing_artifacts"]:
            lines.append(f"- `{name}`")
    lines.extend(["", "## Connections"])
    join = report.get("connections", {}).get("eval_resolution_join", {})
    lines.append(
        f"- eval/resolution joins: `{join.get('joined_count', 0)}`; "
        f"eval orphans: `{join.get('orphan_eval_count', 0)}`; "
        f"resolution orphans: `{join.get('orphan_resolution_count', 0)}`"
    )
    cycle_link = report.get("connections", {}).get("cycle_funnel_link", {})
    lines.append(f"- cycles without funnel sample count: `{cycle_link.get('cycle_without_funnel_count', 0)}`")
    lines.extend(["", "## Evidence Pointers"])
    for pointer in report.get("evidence_pointers", [])[:10]:
        lines.append(f"- `{pointer.get('artifact')}`: `{pointer.get('path')}` rows=`{pointer.get('rows')}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    now = parse_ts(args.now) if args.now else None
    repo_root = Path(args.repo_root)
    data_dir = Path(args.data_dir) if args.data_dir else repo_root / "data"
    report = build_brain_report(args.scope, args.window, repo_root=repo_root, data_dir=data_dir, now=now)
    if args.format == "md":
        print(render_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
