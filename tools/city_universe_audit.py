#!/usr/bin/env python3
"""City Universe Audit read-only CLI.

Ranks active/canary/shadow/blocked cities for human canary-rotation review.
No BUY/SELL/SKIP. No env var changes. No DB writes. No runtime writes.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "runtime_import_derived"
DEFAULT_JSON_OUT = REPO_ROOT / "data" / "city_universe_audit_report.json"
DEFAULT_MD_OUT = REPO_ROOT / "docs" / "city_universe_audit_latest.md"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, "
    "BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes."
)

CONFIDENCE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
PROMOTION_ACTIONS = {
    "keep_active",
    "demote_to_watch_candidate",
    "promote_to_canary_candidate",
    "observe_more",
    "source_blocked",
    "condition_policy_blocked",
}
CRITICAL_SOURCE_STATUSES = {"SOURCE_MISMATCH", "MAPPING_MISSING", "SOURCE_BLOCKED"}


@dataclass
class CityStats:
    city: str
    current_mode: str = "shadow"
    total_evals_14d: int = 0
    days_with_data: int = 0
    evals_per_day: float = 0.0
    condition_filtered_count: int = 0
    condition_filtered_pct: float = 0.0
    condition_mix: dict[str, int] = field(default_factory=dict)
    edge_positive_count: int = 0
    would_buy_true_count: int = 0
    would_buy_shadow_count: int = 0
    avg_edge: float = 0.0
    max_edge: float = 0.0
    near_miss_count: int = 0
    quality_trader_signal_matches: int = 0
    blocked_signals_wins: int = 0
    blocked_signals_losses: int = 0
    blocked_signals_wr: float | None = None
    bot_eval_join_captured_pct: float | None = None
    source_fidelity_status: str = "unknown"
    mapping_status: str = "unknown"
    promotion_gate: str = "unknown"
    lifecycle_stage: str = "unknown"
    lifecycle_transition: str = "unknown"
    latest_seen_at: str | None = None
    data_confidence: str = "none"
    scores: dict[str, int] = field(default_factory=dict)
    score: int = 0
    risk_flags: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    recommended_action: str = "observe_more"
    main_blockers: list[str] = field(default_factory=list)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="City Universe Audit (read-only)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--min-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUT))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    if len(text) == 10 and re.match(r"\d{4}-\d{2}-\d{2}", text):
        text = f"{text}T00:00:00+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_json(path: Path, warnings: list[str], label: str, default: Any) -> Any:
    if not path.exists():
        warnings.append(f"{label} missing: {path}")
        return default
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        warnings.append(f"{label} parse error: {exc}")
        return default


def _read_jsonl(path: Path, warnings: list[str], label: str) -> list[dict[str, Any]]:
    if not path.exists():
        warnings.append(f"{label} missing: {path}")
        return []
    rows: list[dict[str, Any]] = []
    try:
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"{label} line {idx} invalid JSON, skipped")
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception as exc:
        warnings.append(f"{label} read error: {exc}")
    return rows


def _city_key(city: Any) -> str:
    return str(city or "").strip().lower()


def _add_city(names: dict[str, str], city: Any) -> None:
    name = str(city or "").strip()
    if name:
        names.setdefault(_city_key(name), name)


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, dict):
        return [str(key).strip() for key in value if str(key).strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_edge(value: Any) -> float | None:
    try:
        edge = float(value)
    except (TypeError, ValueError):
        return None
    if abs(edge) <= 1.0:
        edge *= 100.0
    return edge


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _extract_bot_default_set(name: str, warnings: list[str]) -> list[str]:
    """Read default env fallback lists from bot.py without importing it."""
    bot_path = REPO_ROOT / "bot.py"
    if not bot_path.exists():
        warnings.append("bot.py missing; cannot use default city set fallback")
        return []
    try:
        tree = ast.parse(bot_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        warnings.append(f"bot.py AST parse failed for {name}: {exc}")
        return []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            if isinstance(call.func, ast.Attribute) and call.func.attr == "getenv" and len(call.args) >= 2:
                if isinstance(call.args[0], ast.Constant) and call.args[0].value == name:
                    if isinstance(call.args[1], ast.Constant):
                        return _as_list(call.args[1].value)
    return []


def _policy_paths(data_dir: Path) -> list[Path]:
    return [
        data_dir / "policy_env_snapshot.json",
        REPO_ROOT / "data" / "runtime_import" / "policy_env_snapshot.json",
    ]


def _load_policy(data_dir: Path, warnings: list[str]) -> dict[str, set[str]]:
    policy_state = _read_json(data_dir / "city_policy_state.json", warnings, "city_policy_state", {})
    policy_env: dict[str, Any] = {}
    for path in _policy_paths(data_dir):
        if path.exists():
            policy_env = _read_json(path, warnings, "policy_env_snapshot", {})
            break

    variables = policy_env.get("variables", {}) if isinstance(policy_env, dict) else {}
    active = set(_as_list(variables.get("ACTIVE_TRADING_CITIES")))
    canary = set(_as_list(variables.get("CANARY_TRADING_CITIES")))
    blocked = set(_as_list(variables.get("BLOCKED_CITIES")))

    if isinstance(policy_state, dict):
        active.update(_as_list(policy_state.get("active_cities") or policy_state.get("ACTIVE_TRADING_CITIES")))
        canary.update(_as_list(policy_state.get("canary_cities") or policy_state.get("CANARY_TRADING_CITIES")))
        blocked.update(_as_list(policy_state.get("blocked_cities") or policy_state.get("BLOCKED_CITIES")))

    if not active:
        active.update(_extract_bot_default_set("ACTIVE_TRADING_CITIES", warnings))
    if not canary:
        canary.update(_extract_bot_default_set("CANARY_TRADING_CITIES", warnings))
    if not blocked:
        blocked.update(_extract_bot_default_set("BLOCKED_CITIES", warnings))

    auto_canary = set(_as_list(policy_state.get("auto_canary_cities") if isinstance(policy_state, dict) else None))
    auto_shadow = set(_as_list(policy_state.get("auto_shadow_cities") if isinstance(policy_state, dict) else None))
    auto_blocked = set(_as_list(policy_state.get("auto_blocked_cities") if isinstance(policy_state, dict) else None))

    return {
        "active": active,
        "canary": canary,
        "blocked": blocked,
        "auto_canary": auto_canary,
        "auto_shadow": auto_shadow,
        "auto_blocked": auto_blocked,
    }


def _mode_for(city: str, policy: dict[str, set[str]]) -> str:
    key = _city_key(city)
    if key in {_city_key(c) for c in policy["blocked"] | policy["auto_blocked"]}:
        return "blocked"
    if key in {_city_key(c) for c in policy["active"]}:
        return "active"
    if key in {_city_key(c) for c in policy["canary"] | policy["auto_canary"]}:
        return "canary"
    if key in {_city_key(c) for c in policy["auto_shadow"]}:
        return "shadow"
    return "shadow"


def _filter_window(rows: list[dict[str, Any]], days: int, now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=days)
    out = []
    for row in rows:
        ts = _parse_ts(
            row.get("timestamp")
            or row.get("checked_at")
            or row.get("created_at")
            or row.get("open_timestamp")
            or row.get("date")
        )
        if ts is None or ts >= cutoff:
            out.append(row)
    return out


def _index_source_onboarding(warnings: list[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    path = REPO_ROOT / "data" / "source_onboarding.json"
    data = _read_json(path, warnings, "source_onboarding", {})
    rows = data.get("cities", []) if isinstance(data, dict) else []
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("city"):
            index[_city_key(row["city"])] = row
    return index, [str(path)] if path.exists() else []


def _load_json_or_md_index(base_name: str, warnings: list[str]) -> tuple[dict[str, dict[str, str]], list[str]]:
    json_path = REPO_ROOT / "data" / f"{base_name}.json"
    md_path = REPO_ROOT / "docs" / f"{base_name}_latest.md"
    if json_path.exists():
        data = _read_json(json_path, warnings, base_name, {})
        rows = []
        if isinstance(data, dict):
            rows = data.get("cities") or data.get("review_queue") or data.get("ranked_cities") or []
        index = {
            _city_key(row.get("city")): row
            for row in rows
            if isinstance(row, dict) and row.get("city")
        }
        return index, [str(json_path)]

    if not md_path.exists():
        warnings.append(f"{base_name} missing: {json_path} / {md_path}")
        return {}, []

    index: dict[str, dict[str, str]] = {}
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or line.startswith("| ---") or " City " in line:
                continue
            cells = [cell.strip(" `") for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0]:
                if base_name == "city_lifecycle_review":
                    index[_city_key(cells[0])] = {
                        "city": cells[0],
                        "stage": cells[1],
                        "transition": cells[2],
                        "notes": cells[4] if len(cells) > 4 else "",
                    }
                else:
                    index[_city_key(cells[0])] = {
                        "city": cells[0],
                        "gate_status": cells[1] if len(cells) > 1 else "unknown",
                        "review_priority": cells[2] if len(cells) > 2 else "unknown",
                    }
    except Exception as exc:
        warnings.append(f"{base_name} markdown parse error: {exc}")
    return index, [str(md_path)]


def _source_status(row: dict[str, Any] | None) -> tuple[str, str, int]:
    if not row:
        return "unknown", "unknown", 0
    mapping = str(row.get("mapping_status") or row.get("internal_mapping_status") or "unknown")
    source = str(
        row.get("source_fidelity_status")
        or row.get("source_audit_status")
        or row.get("primary_status")
        or row.get("state")
        or "unknown"
    )
    joined = f"{source} {mapping}".upper()
    if "SOURCE_MISMATCH" in joined or "SOURCE_BLOCKED" in joined or "MAPPING_MISSING" in joined:
        return source, mapping, 0
    if "SOURCE_MATCH_CONFIRMED" in joined or "SOURCE_CONFIRMED" in joined or "MAPPING_FULL" in joined:
        return source, mapping, 2
    if "SOURCE_PARTIAL" in joined or "AMBIGUOUS" in joined or "ICAO_ONLY" in joined:
        return source, mapping, 1
    return source, mapping, 0


def _trader_signal_score(stats: CityStats) -> int:
    resolved = stats.blocked_signals_wins + stats.blocked_signals_losses
    if stats.quality_trader_signal_matches >= 3 or (resolved >= 5 and (stats.blocked_signals_wr or 0) >= 70):
        return 2
    if stats.quality_trader_signal_matches >= 1 or resolved >= 1:
        return 1
    return 0


def _reason_codes(stats: CityStats) -> list[str]:
    codes: list[str] = []
    if stats.total_evals_14d == 0:
        codes.append("NO_EVALS_IN_WINDOW")
    if stats.condition_filtered_pct > 80:
        codes.append("CONDITION_FILTER_DOMINANT")
    elif stats.condition_filtered_count:
        codes.append("CONDITION_FILTER_PRESENT")
    if stats.would_buy_true_count == 0:
        codes.append("NO_WOULD_BUY_TRUE")
    if stats.edge_positive_count == 0:
        codes.append("NO_POSITIVE_EDGE")
    if stats.quality_trader_signal_matches == 0 and stats.blocked_signals_wins + stats.blocked_signals_losses == 0:
        codes.append("NO_TRADER_SIGNAL")
    if stats.source_fidelity_status in CRITICAL_SOURCE_STATUSES or stats.mapping_status in CRITICAL_SOURCE_STATUSES:
        codes.append("SOURCE_CRITICAL")
    elif stats.source_fidelity_status != "unknown" or stats.mapping_status != "unknown":
        if "AMBIGUOUS" in stats.source_fidelity_status.upper() or "ICAO_ONLY" in stats.mapping_status.upper():
            codes.append("SOURCE_AMBIGUOUS")
    if "drift_warning" in stats.risk_flags:
        codes.append("DRIFT_WARNING")
    if "settlement_warning" in stats.risk_flags:
        codes.append("SETTLEMENT_WARNING")
    return codes


def _score_and_action(stats: CityStats, source_score: int) -> None:
    positive_edges = [stats.avg_edge, stats.max_edge]
    avg_edge = stats.avg_edge
    stats.scores = {
        "throughput_score": 0 if stats.total_evals_14d == 0 else (2 if stats.evals_per_day >= 5 else 1),
        "edge_score": 0 if avg_edge <= 0 else (2 if avg_edge >= 10 else 1),
        "would_buy_shadow": 0 if stats.would_buy_shadow_count == 0 else (2 if stats.would_buy_shadow_count >= 5 else 1),
        "condition_compat": 0
        if stats.total_evals_14d and stats.condition_filtered_pct > 80
        else (1 if stats.total_evals_14d and stats.condition_filtered_pct >= 40 else 2),
        "source_fidelity": source_score,
        "trader_signal": _trader_signal_score(stats),
        "recency": 0,
        "data_confidence": 0 if stats.data_confidence == "none" else (1 if stats.data_confidence == "low" else 2),
    }
    if stats.latest_seen_at:
        latest = _parse_ts(stats.latest_seen_at)
        if latest:
            age_days = (datetime.now(timezone.utc) - latest).days
            stats.scores["recency"] = 2 if age_days < 5 else (1 if age_days <= 10 else 0)
    stats.score = sum(stats.scores.values())

    critical = set(stats.risk_flags) & {
        "drift_warning",
        "settlement_warning",
        "structural_block",
        "source_critical",
        "insufficient_data",
    }
    candidate_signal = stats.would_buy_shadow_count >= 5 or stats.edge_positive_count >= 8
    source_ok = source_score >= 1 and "source_critical" not in stats.risk_flags
    condition_ok = stats.condition_filtered_pct < 70 or stats.total_evals_14d == 0
    confident = stats.data_confidence in {"medium", "high"}

    if "source_critical" in stats.risk_flags or "structural_block" in stats.risk_flags:
        stats.recommended_action = "source_blocked"
    elif stats.total_evals_14d > 0 and stats.condition_filtered_pct >= 80:
        stats.recommended_action = "condition_policy_blocked"
    elif stats.current_mode == "active":
        if stats.total_evals_14d == 0 or stats.would_buy_true_count == 0:
            stats.recommended_action = "demote_to_watch_candidate"
        else:
            stats.recommended_action = "keep_active"
    elif candidate_signal and not critical and source_ok and condition_ok and confident:
        stats.recommended_action = "promote_to_canary_candidate"
    else:
        stats.recommended_action = "observe_more"

    if stats.recommended_action not in PROMOTION_ACTIONS:
        stats.recommended_action = "observe_more"
    stats.reason_codes = _reason_codes(stats)
    stats.main_blockers = [
        code
        for code in stats.reason_codes
        if code
        in {
            "CONDITION_FILTER_DOMINANT",
            "NO_WOULD_BUY_TRUE",
            "NO_EVALS_IN_WINDOW",
            "NO_TRADER_SIGNAL",
            "SOURCE_CRITICAL",
            "DRIFT_WARNING",
            "SETTLEMENT_WARNING",
        }
    ][:5]


def build_report(data_dir: Path, days: int, min_confidence: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    warnings: list[str] = []
    inputs_used: list[str] = []

    eval_rows = _filter_window(_read_jsonl(data_dir / "bot_signal_evaluations.jsonl", warnings, "bot_signal_evaluations"), days, now)
    blocked_rows = _filter_window(_read_jsonl(data_dir / "blocked_signals_resolutions.jsonl", warnings, "blocked_signals_resolutions"), days, now)
    trade_data = _read_json(data_dir / "trade_lifecycle.json", warnings, "trade_lifecycle", [])
    skip_rows = _filter_window(_read_jsonl(data_dir / "skip_log.jsonl", warnings, "skip_log"), days, now)
    policy = _load_policy(data_dir, warnings)
    source_index, source_inputs = _index_source_onboarding(warnings)
    lifecycle_index, lifecycle_inputs = _load_json_or_md_index("city_lifecycle_review", warnings)
    gate_index, gate_inputs = _load_json_or_md_index("city_promotion_gate", warnings)

    for path in [
        data_dir / "bot_signal_evaluations.jsonl",
        data_dir / "blocked_signals_resolutions.jsonl",
        data_dir / "trade_lifecycle.json",
        data_dir / "skip_log.jsonl",
        data_dir / "city_policy_state.json",
    ]:
        if path.exists():
            inputs_used.append(str(path))
    inputs_used.extend(source_inputs + lifecycle_inputs + gate_inputs)

    names: dict[str, str] = {}
    for group in policy.values():
        for city in group:
            _add_city(names, city)
    for row in eval_rows + blocked_rows + skip_rows:
        _add_city(names, row.get("city"))
    if isinstance(trade_data, dict):
        trade_rows = trade_data.get("trades") or trade_data.get("positions") or trade_data.get("closed") or []
    else:
        trade_rows = trade_data if isinstance(trade_data, list) else []
    for row in trade_rows:
        if isinstance(row, dict):
            _add_city(names, row.get("city"))
    for index in (source_index, lifecycle_index, gate_index):
        for row in index.values():
            _add_city(names, row.get("city"))

    per_city_edges: dict[str, list[float]] = defaultdict(list)
    day_sets: dict[str, set[str]] = defaultdict(set)
    latest_by_city: dict[str, datetime] = {}
    city_eval_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eval_rows:
        key = _city_key(row.get("city"))
        if not key:
            continue
        city_eval_rows[key].append(row)
        ts = _parse_ts(row.get("timestamp") or row.get("checked_at") or row.get("created_at"))
        if ts:
            day_sets[key].add(ts.date().isoformat())
            if key not in latest_by_city or ts > latest_by_city[key]:
                latest_by_city[key] = ts
        edge = _normalize_edge(row.get("edge") or row.get("edge_pct") or row.get("edge_percent"))
        if edge is not None and edge > 0:
            per_city_edges[key].append(edge)

    skip_counts: Counter[str] = Counter()
    for row in skip_rows:
        key = _city_key(row.get("city"))
        if not key:
            continue
        edge = _normalize_edge(row.get("edge") or row.get("edge_pct") or row.get("edge_percent"))
        if edge is None or edge > 0:
            skip_counts[key] += 1

    blocked_by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in blocked_rows:
        key = _city_key(row.get("city"))
        if key:
            blocked_by_city[key].append(row)

    ranked: list[CityStats] = []
    for key in sorted(names, key=lambda item: names[item].lower()):
        city = names[key]
        stats = CityStats(city=city, current_mode=_mode_for(city, policy))
        rows = city_eval_rows.get(key, [])
        stats.total_evals_14d = len(rows)
        stats.days_with_data = len(day_sets.get(key, set()))
        stats.evals_per_day = round(stats.total_evals_14d / max(1, min(days, stats.days_with_data or days)), 2)
        stats.condition_filtered_count = sum(1 for row in rows if _truthy(row.get("condition_filtered")) or "condition" in str(row.get("skip_reason") or "").lower())
        stats.condition_filtered_pct = round(stats.condition_filtered_count / stats.total_evals_14d * 100, 1) if stats.total_evals_14d else 0.0
        stats.condition_mix = dict(Counter(str(row.get("condition") or "unknown") for row in rows))
        stats.edge_positive_count = len(per_city_edges.get(key, []))
        stats.would_buy_true_count = sum(1 for row in rows if _truthy(row.get("would_buy")))
        stats.would_buy_shadow_count = sum(
            1
            for row in rows
            if _truthy(row.get("would_buy")) and str(row.get("evaluation_source") or row.get("city_mode") or "").lower() == "shadow"
        )
        stats.avg_edge = round(sum(per_city_edges.get(key, [])) / len(per_city_edges[key]), 2) if per_city_edges.get(key) else 0.0
        stats.max_edge = round(max(per_city_edges.get(key, [0.0])), 2)
        stats.near_miss_count = skip_counts[key]
        if key in latest_by_city:
            stats.latest_seen_at = latest_by_city[key].isoformat()
        stats.data_confidence = (
            "none"
            if stats.total_evals_14d == 0
            else "high"
            if stats.total_evals_14d >= 20
            else "medium"
            if stats.total_evals_14d >= 7
            else "low"
        )

        b_rows = blocked_by_city.get(key, [])
        stats.blocked_signals_wins = sum(1 for row in b_rows if _truthy(row.get("win_for_trader")))
        stats.blocked_signals_losses = sum(1 for row in b_rows if row.get("win_for_trader") is not None and not _truthy(row.get("win_for_trader")))
        resolved = stats.blocked_signals_wins + stats.blocked_signals_losses
        stats.blocked_signals_wr = round(stats.blocked_signals_wins / resolved * 100, 1) if resolved else None
        captured = sum(1 for row in b_rows if str(row.get("bot_evaluation_join_status") or "").lower() == "captured")
        stats.bot_eval_join_captured_pct = round(captured / len(b_rows) * 100, 1) if b_rows else None
        stats.quality_trader_signal_matches = len({row.get("trader") for row in b_rows if row.get("trader")})

        source_row = source_index.get(key)
        stats.source_fidelity_status, stats.mapping_status, source_score = _source_status(source_row)
        lifecycle_row = lifecycle_index.get(key, {})
        gate_row = gate_index.get(key, {})
        stats.lifecycle_stage = str(lifecycle_row.get("stage") or lifecycle_row.get("lifecycle_stage") or "unknown")
        stats.lifecycle_transition = str(lifecycle_row.get("transition") or "unknown")
        stats.promotion_gate = str(gate_row.get("gate_status") or gate_row.get("promotion_gate") or "unknown")

        joined_source = f"{stats.source_fidelity_status} {stats.mapping_status}".upper()
        if any(flag in joined_source for flag in CRITICAL_SOURCE_STATUSES):
            stats.risk_flags.append("source_critical")
        if stats.current_mode == "blocked":
            stats.risk_flags.append("structural_block")
        gate_text = " ".join(str(v) for v in gate_row.values()).lower() if isinstance(gate_row, dict) else ""
        life_text = " ".join(str(v) for v in lifecycle_row.values()).lower() if isinstance(lifecycle_row, dict) else ""
        if "drift" in gate_text or "drift" in life_text:
            stats.risk_flags.append("drift_warning")
        if "settlement" in gate_text or "settlement" in life_text or "mismatch" in gate_text:
            stats.risk_flags.append("settlement_warning")
        if stats.data_confidence == "none":
            stats.risk_flags.append("insufficient_data")

        _score_and_action(stats, source_score)
        ranked.append(stats)

    ranked.sort(key=lambda s: (-s.score, -s.would_buy_shadow_count, -s.edge_positive_count, s.city.lower()))
    min_rank = CONFIDENCE_ORDER[min_confidence]
    markdown_rows = [
        s for s in ranked if CONFIDENCE_ORDER[s.data_confidence] >= min_rank or s.current_mode == "active"
    ]

    return {
        "generated_at": now.isoformat(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "window_days": days,
        "min_confidence": min_confidence,
        "inputs": sorted(set(inputs_used)),
        "warnings": warnings,
        "summary": {
            "cities_ranked": len(ranked),
            "markdown_ranked": len(markdown_rows),
            "top_candidate_count": sum(1 for s in ranked if s.recommended_action == "promote_to_canary_candidate"),
            "bottom_active_count": sum(1 for s in ranked if s.current_mode == "active" and s.recommended_action == "demote_to_watch_candidate"),
            "mode_counts": dict(Counter(s.current_mode for s in ranked)),
            "action_counts": dict(Counter(s.recommended_action for s in ranked)),
        },
        "ranked_cities": [_city_to_dict(s, rank + 1) for rank, s in enumerate(ranked)],
        "markdown_ranked_cities": [_city_to_dict(s, rank + 1) for rank, s in enumerate(markdown_rows)],
    }


def _city_to_dict(stats: CityStats, rank: int) -> dict[str, Any]:
    out = {
        "rank": rank,
        "city": stats.city,
        "current_mode": stats.current_mode,
        "total_evals_14d": stats.total_evals_14d,
        "evals_per_day": stats.evals_per_day,
        "days_with_data": stats.days_with_data,
        "condition_filtered_count": stats.condition_filtered_count,
        "condition_filtered_pct": stats.condition_filtered_pct,
        "condition_mix": stats.condition_mix,
        "edge_positive_count": stats.edge_positive_count,
        "would_buy_true_count": stats.would_buy_true_count,
        "would_buy_shadow_count": stats.would_buy_shadow_count,
        "avg_edge": stats.avg_edge,
        "max_edge": stats.max_edge,
        "near_miss_count": stats.near_miss_count,
        "quality_trader_signal_matches": stats.quality_trader_signal_matches,
        "blocked_signals_wins": stats.blocked_signals_wins,
        "blocked_signals_losses": stats.blocked_signals_losses,
        "blocked_signals_wr": stats.blocked_signals_wr,
        "bot_eval_join_captured_pct": stats.bot_eval_join_captured_pct,
        "source_fidelity_status": stats.source_fidelity_status,
        "mapping_status": stats.mapping_status,
        "promotion_gate": stats.promotion_gate,
        "lifecycle_stage": stats.lifecycle_stage,
        "lifecycle_transition": stats.lifecycle_transition,
        "latest_seen_at": stats.latest_seen_at,
        "data_confidence": stats.data_confidence,
        "scores": stats.scores,
        "score": stats.score,
        "risk_flags": stats.risk_flags,
        "reason_codes": stats.reason_codes,
        "main_blockers": stats.main_blockers,
        "recommended_action": stats.recommended_action,
    }
    return out


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    rows = report["markdown_ranked_cities"]
    all_rows = report["ranked_cities"]
    top = [r for r in all_rows if r["recommended_action"] == "promote_to_canary_candidate"][:5]
    bottom = [
        r
        for r in all_rows
        if r["current_mode"] == "active" and r["recommended_action"] == "demote_to_watch_candidate"
    ]

    lines = [
        "# City Universe Audit",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Window: `{report['window_days']}` days",
        f"- Cities ranked: `{report['summary']['cities_ranked']}`",
        f"- Top canary candidates: `{len(top)}`",
        f"- Bottom active cities: `{len(bottom)}`",
        "",
        "## Ranking",
        "",
        "| Rank | City | Mode | Evals/day | WouldBuy Shadow | Edge+ | Score | Data | Risk Flags | Action |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        flags = ", ".join(row["risk_flags"]) if row["risk_flags"] else "-"
        lines.append(
            f"| {row['rank']} | {row['city']} | {row['current_mode']} | "
            f"{row['evals_per_day']:.2f} | {row['would_buy_shadow_count']} | "
            f"{row['edge_positive_count']} | {row['score']}/16 | {row['data_confidence']} | "
            f"{flags} | {row['recommended_action']} |"
        )

    lines.extend(["", "## Top 5 Candidatas A Canary", ""])
    if not top:
        lines.append("No clear promote_to_canary_candidate rows in this window.")
    for idx, row in enumerate(top, 1):
        lines.extend(
            [
                f"### {idx}. {row['city']} - Score: {row['score']}/16 - Action: {row['recommended_action']}",
                "",
                f"- Mode actual: {row['current_mode']}",
                f"- Evals/day: {row['evals_per_day']:.2f}",
                f"- Would_buy_shadow: {row['would_buy_shadow_count']}",
                f"- Edge+ count: {row['edge_positive_count']} | Avg edge: {_fmt_pct(row['avg_edge'])} | Max edge: {_fmt_pct(row['max_edge'])}",
                f"- Condition mix: {row['condition_mix']} | condition_filtered={_fmt_pct(row['condition_filtered_pct'])}",
                f"- Trader signals: {row['quality_trader_signal_matches']} matches, WR={_fmt_pct(row['blocked_signals_wr'])}",
                f"- Source fidelity: {row['source_fidelity_status']} / {row['mapping_status']}",
                f"- Main blockers: {row['main_blockers'] or []}",
                f"- Data confidence: {row['data_confidence']}",
                f"- Risk flags: {row['risk_flags'] or []}",
                "",
            ]
        )

    lines.extend(["", "## Bottom Active Cities", ""])
    if not bottom:
        lines.append("No active city met the dead-throughput demotion heuristic.")
    for row in bottom:
        dead = "DEAD" if row["evals_per_day"] < 1 or row["would_buy_true_count"] == 0 else "WATCH"
        lines.extend(
            [
                f"### {row['city']} - Score: {row['score']}/16 - Action: {row['recommended_action']}",
                "",
                f"- Mode actual: {row['current_mode']}",
                f"- Evals/day: {row['evals_per_day']:.2f} ({dead})",
                f"- Would_buy_true: {row['would_buy_true_count']}",
                f"- Main blockers: {row['main_blockers'] or []}",
                f"- Recommendation: {row['recommended_action']}",
                "",
            ]
        )

    lines.extend(["", "## Reason Codes", ""])
    lines.append("| City | Reason Codes | Recommended Action |")
    lines.append("| --- | --- | --- |")
    for row in all_rows:
        lines.append(f"| {row['city']} | {', '.join(row['reason_codes']) or '-'} | {row['recommended_action']} |")

    if report["warnings"]:
        lines.extend(["", "## Input Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")

    lines.extend(["", "---", "", f"*{LOG_ONLY_DISCLAIMER}*"])
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, Any], json_out: Path, md_out: Path) -> None:
    for path in (json_out, md_out):
        if path.is_absolute() and str(path).replace("\\", "/").startswith("/app/data/"):
            raise SystemExit(f"Refusing to write runtime path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = Path(args.data_dir)
    report = build_report(data_dir, args.days, args.min_confidence)
    summary = report["summary"]
    print(
        "City Universe Audit: "
        f"{summary['cities_ranked']} cities, "
        f"{summary['top_candidate_count']} promote candidates, "
        f"{summary['bottom_active_count']} bottom active cities."
    )
    if report["warnings"]:
        print(f"Warnings: {len(report['warnings'])} input issue(s); confidence degraded where needed.")
    if args.dry_run:
        top = [r for r in report["ranked_cities"] if r["recommended_action"] == "promote_to_canary_candidate"][:5]
        for row in top:
            print(f"- candidate: {row['city']} score={row['score']}/16 would_buy_shadow={row['would_buy_shadow_count']}")
        return 0
    write_outputs(report, Path(args.json_out), Path(args.md_out))
    print(f"Wrote JSON: {args.json_out}")
    print(f"Wrote Markdown: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
