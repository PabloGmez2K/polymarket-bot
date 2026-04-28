#!/usr/bin/env python3
"""
tools/blocked_signals_audit.py — Fase B1: Read-only audit CLI for blocked_signals_resolutions.jsonl.

Reads Railway's canonical blocked_signals_resolutions.jsonl (schema v1 and v2).
Supports filtering by date, output formats (text / markdown / JSON), and writing
a report file via --out.

Never contacts external APIs, Telegram, or any network endpoint.
Never writes state files. Only writes a report file when --out is specified.
Never imports bot.py.

Usage:
    python tools/blocked_signals_audit.py
    python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl
    python tools/blocked_signals_audit.py --days 30
    python tools/blocked_signals_audit.py --json
    python tools/blocked_signals_audit.py --markdown --out docs/blocked_audit_2026-04-28.md
    python tools/blocked_signals_audit.py --top 15
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────

DEFAULT_SOURCE_PATHS = [
    "data/blocked_signals_resolutions.jsonl",
    "/app/data/blocked_signals_resolutions.jsonl",
]
DEFAULT_TOP_N = 10
AUDIT_CANDIDATE_MIN_N = 10
AUDIT_CANDIDATE_MIN_WR = 70.0
AUDIT_CANDIDATE_PRICE_MIN = 0.20
AUDIT_CANDIDATE_PRICE_MAX = 0.90
CONCENTRATION_WARN_THRESHOLD_PCT = 60.0

# ─────────────────────────────────────────────────────────────────────
# Loading & normalizing
# ─────────────────────────────────────────────────────────────────────

def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    clean = ts[:26].replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(clean[:len(fmt) + 3], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            pass
    return None


def _normalize(rec: dict) -> dict:
    """Apply v1 defaults to records with missing v2 fields."""
    out = dict(rec)
    # schema_version absent → v1 implicit
    out.setdefault("schema_version", 1)
    out.setdefault("reason_blocked", "unknown")
    out.setdefault("city_policy_status_at_record_time", "unknown")
    out.setdefault("whitelist_status_at_record_time", "unknown")
    out.setdefault("settlement_fidelity_status", "unknown")
    out.setdefault("observed_coverage_status", "unknown")
    out.setdefault("price_bucket", "unknown")
    out.setdefault("canonical_signal_id", None)
    out.setdefault("market_id", None)
    # v1 compat: 'win_for_trader' already present in v1 schema from bot.py
    if "win_for_trader" not in out:
        out["win_for_trader"] = bool(out.get("win", False))
    # v1 compat: avg_price_entered might be stored as 'price' or 'avg_price'
    if "avg_price_entered" not in out:
        out["avg_price_entered"] = out.get("price") or out.get("avg_price") or 0
    return out


def load_records(source: Path, days: int | None = None) -> list[dict]:
    if not source.exists():
        return []
    cutoff: datetime | None = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records: list[dict] = []
    with source.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            rec = _normalize(rec)
            if cutoff is not None:
                ts = _parse_ts(rec.get("checked_at"))
                if ts and ts < cutoff:
                    continue
            records.append(rec)
    return records


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _wr(wins: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(wins / total * 100, 1)


def _wr_str(wins: int, total: int) -> str:
    w = _wr(wins, total)
    return f"{w}%" if w is not None else "n/d"


def _date_range(records: list[dict]) -> tuple[str | None, str | None]:
    dates = [r.get("checked_at") or r.get("date") for r in records]
    dates = [d[:10] for d in dates if d]
    if not dates:
        return None, None
    dates_sorted = sorted(dates)
    return dates_sorted[0], dates_sorted[-1]


# ─────────────────────────────────────────────────────────────────────
# Section A — Global summary
# ─────────────────────────────────────────────────────────────────────

def section_a(records: list[dict]) -> dict:
    total = len(records)
    v1 = sum(1 for r in records if r["schema_version"] == 1)
    resolved = [r for r in records if r.get("resolved")]
    wins = sum(1 for r in resolved if r.get("win_for_trader"))
    date_from, date_to = _date_range(records)
    cities = len({r.get("city") for r in records if r.get("city")})
    traders = len({r.get("trader") for r in records if r.get("trader")})
    return {
        "total": total,
        "v1_count": v1,
        "v2_count": total - v1,
        "resolved": len(resolved),
        "wins": wins,
        "losses": len(resolved) - wins,
        "wr_global": _wr(wins, len(resolved)),
        "date_from": date_from,
        "date_to": date_to,
        "cities": cities,
        "traders": traders,
    }


# ─────────────────────────────────────────────────────────────────────
# Section B — Whitelist split
# ─────────────────────────────────────────────────────────────────────

def section_b(records: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        status = r.get("whitelist_status_at_record_time", "unknown")
        if status not in ("in", "out"):
            status = "unknown"
        buckets[status].append(r)
    result = {}
    for key in ("in", "out", "unknown"):
        recs = buckets[key]
        res = [r for r in recs if r.get("resolved")]
        wins = sum(1 for r in res if r.get("win_for_trader"))
        result[key] = {
            "total": len(recs),
            "resolved": len(res),
            "wins": wins,
            "losses": len(res) - wins,
            "wr": _wr(wins, len(res)),
        }
    return result


# ─────────────────────────────────────────────────────────────────────
# Section C — Top cities
# ─────────────────────────────────────────────────────────────────────

def _city_stats(city: str, recs: list[dict]) -> dict:
    resolved = [r for r in recs if r.get("resolved")]
    wins = sum(1 for r in resolved if r.get("win_for_trader"))
    conditions = Counter(r.get("condition", "unknown") for r in recs)
    trader_counts = Counter(r.get("trader", "") for r in recs if r.get("trader"))
    prices = [r["avg_price_entered"] for r in recs if r.get("avg_price_entered")]
    avg_price = round(sum(prices) / len(prices), 3) if prices else None
    v1 = sum(1 for r in recs if r["schema_version"] == 1)
    top_bucket = Counter(r.get("price_bucket", "unknown") for r in recs).most_common(1)[0][0]
    top_reason = Counter(r.get("reason_blocked", "unknown") for r in recs).most_common(1)[0][0]
    top_policy = Counter(r.get("city_policy_status_at_record_time", "unknown") for r in recs).most_common(1)[0][0]
    top_coverage = Counter(r.get("observed_coverage_status", "unknown") for r in recs).most_common(1)[0][0]
    top_fidelity = Counter(r.get("settlement_fidelity_status", "unknown") for r in recs).most_common(1)[0][0]
    return {
        "city": city,
        "total": len(recs),
        "resolved": len(resolved),
        "wins": wins,
        "losses": len(resolved) - wins,
        "wr": _wr(wins, len(resolved)),
        "conditions": dict(conditions),
        "top_traders": [t for t, _ in trader_counts.most_common(3)],
        "avg_price_entered": avg_price,
        "price_bucket": top_bucket,
        "schema_v1": v1,
        "schema_v2": len(recs) - v1,
        "reason_blocked": top_reason,
        "city_policy_status_at_record_time": top_policy,
        "observed_coverage_status": top_coverage,
        "settlement_fidelity_status": top_fidelity,
    }


def section_c(records: list[dict], top_n: int = DEFAULT_TOP_N) -> list[dict]:
    city_map: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        city = r.get("city", "")
        if city:
            city_map[city].append(r)
    results = [_city_stats(city, recs) for city, recs in city_map.items()]
    results.sort(key=lambda x: x["total"], reverse=True)
    return results[:top_n]


def _build_all_city_map(records: list[dict]) -> dict[str, dict]:
    city_map: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        city = r.get("city", "")
        if city:
            city_map[city].append(r)
    return {city: _city_stats(city, recs) for city, recs in city_map.items()}


# ─────────────────────────────────────────────────────────────────────
# Section D — Concentration
# ─────────────────────────────────────────────────────────────────────

def section_d(records: list[dict], top_cities: list[dict]) -> dict:
    total = len(records)
    top3 = top_cities[:3]
    top3_total = sum(c["total"] for c in top3)
    top3_pct = round(top3_total / total * 100, 1) if total > 0 else 0.0
    return {
        "top3": [{"city": c["city"], "total": c["total"]} for c in top3],
        "top3_total": top3_total,
        "top3_pct": top3_pct,
        "concentration_warning": top3_pct > CONCENTRATION_WARN_THRESHOLD_PCT,
    }


# ─────────────────────────────────────────────────────────────────────
# Section E — Low actionability signals
# ─────────────────────────────────────────────────────────────────────

def section_e(records: list[dict]) -> dict:
    total = len(records)
    if total == 0:
        return {}
    n_fidelity = sum(
        1 for r in records
        if r.get("settlement_fidelity_status") in ("unverified", "unknown")
    )
    n_coverage = sum(
        1 for r in records
        if r.get("observed_coverage_status") in ("no_local_station", "icao_only")
    )
    n_out_wl = sum(1 for r in records if r.get("reason_blocked") == "out_of_whitelist")
    n_v1 = sum(1 for r in records if r["schema_version"] == 1)
    n_extreme = sum(
        1 for r in records
        if r.get("avg_price_entered") and (
            r["avg_price_entered"] > 0.9 or r["avg_price_entered"] < 0.10
        )
    )
    n_no_consensus = sum(1 for r in records if not r.get("has_consensus"))
    return {
        "settlement_fidelity_issues": {
            "count": n_fidelity,
            "pct": round(n_fidelity / total * 100, 1),
            "flag": (n_fidelity / total > 0.8),
        },
        "coverage_issues": {
            "count": n_coverage,
            "pct": round(n_coverage / total * 100, 1),
        },
        "out_of_whitelist_count": n_out_wl,
        "v1_count": n_v1,
        "v1_schema_pct": round(n_v1 / total * 100, 1),
        "extreme_price_count": n_extreme,
        "no_consensus_count": n_no_consensus,
        "no_consensus_pct": round(n_no_consensus / total * 100, 1),
    }


# ─────────────────────────────────────────────────────────────────────
# Section F — Duplicates
# ─────────────────────────────────────────────────────────────────────

def section_f(records: list[dict]) -> dict:
    canonical_ids = [r["canonical_signal_id"] for r in records if r.get("canonical_signal_id")]
    canonical_dupes = {k: v for k, v in Counter(canonical_ids).items() if v > 1}
    market_ids = [r["market_id"] for r in records if r.get("market_id")]
    market_dupes = {k: v for k, v in Counter(market_ids).items() if v > 1}
    n_v1 = sum(1 for r in records if r["schema_version"] == 1)
    return {
        "canonical_id_dupes": len(canonical_dupes),
        "canonical_dupe_examples": list(canonical_dupes.keys())[:5],
        "market_id_dupes": len(market_dupes),
        "market_id_dupe_examples": list(market_dupes.keys())[:5],
        "v1_dedupe_warning": n_v1 > 0,
        "v1_count": n_v1,
    }


# ─────────────────────────────────────────────────────────────────────
# Section G — Audit candidates
# ─────────────────────────────────────────────────────────────────────

_PRIORITY_ORDER = [
    "audit_candidate",
    "needs_settlement_verification",
    "monitor",
    "not_actionable",
    "ignore",
]


def _classify(
    n: int,
    n_resolved: int,
    wr: float | None,
    avg_price: float | None,
    n_traders: int,
    coverage: str,
    fidelity: str,
) -> str:
    if n < 5:
        return "ignore"
    if wr is None or n_resolved < 5:
        return "not_actionable"
    if fidelity in ("unverified", "unknown") and coverage in ("icao_only", "no_local_station"):
        return "needs_settlement_verification"
    if (
        n >= AUDIT_CANDIDATE_MIN_N
        and wr >= AUDIT_CANDIDATE_MIN_WR
        and (avg_price is None or AUDIT_CANDIDATE_PRICE_MIN <= avg_price <= AUDIT_CANDIDATE_PRICE_MAX)
        and n_traders >= 2
    ):
        return "audit_candidate"
    if n >= 10 and wr >= 55:
        return "monitor"
    if n >= 5 and wr >= 50:
        return "monitor"
    return "not_actionable"


def section_g(records: list[dict]) -> list[dict]:
    city_map: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        city = r.get("city", "")
        if city:
            city_map[city].append(r)

    candidates = []
    for city, recs in city_map.items():
        # Use most common whitelist_status
        wl_status = Counter(
            r.get("whitelist_status_at_record_time", "unknown") for r in recs
        ).most_common(1)[0][0]
        if wl_status != "out":
            continue

        resolved = [r for r in recs if r.get("resolved")]
        wins = sum(1 for r in resolved if r.get("win_for_trader"))
        wr = _wr(wins, len(resolved))
        prices = [r["avg_price_entered"] for r in recs if r.get("avg_price_entered")]
        avg_price = round(sum(prices) / len(prices), 3) if prices else None
        trader_counts = Counter(r.get("trader", "") for r in recs if r.get("trader"))
        n_traders = len(trader_counts)
        top_coverage = Counter(r.get("observed_coverage_status", "unknown") for r in recs).most_common(1)[0][0]
        top_fidelity = Counter(r.get("settlement_fidelity_status", "unknown") for r in recs).most_common(1)[0][0]
        classification = _classify(
            n=len(recs),
            n_resolved=len(resolved),
            wr=wr,
            avg_price=avg_price,
            n_traders=n_traders,
            coverage=top_coverage,
            fidelity=top_fidelity,
        )
        candidates.append({
            "city": city,
            "total": len(recs),
            "resolved": len(resolved),
            "wins": wins,
            "wr": wr,
            "avg_price": avg_price,
            "n_traders": n_traders,
            "top_traders": [t for t, _ in trader_counts.most_common(3)],
            "observed_coverage_status": top_coverage,
            "settlement_fidelity_status": top_fidelity,
            "classification": classification,
        })

    candidates.sort(key=lambda c: (
        _PRIORITY_ORDER.index(c["classification"]) if c["classification"] in _PRIORITY_ORDER else 99,
        -(c["wr"] or 0),
    ))
    return candidates


# ─────────────────────────────────────────────────────────────────────
# Report formatting — text
# ─────────────────────────────────────────────────────────────────────

def _fmt_text(a: dict) -> str:
    lines: list[str] = []
    W = 62
    lines.append("=" * W)
    lines.append("  Blocked Signals Audit — Fase B1")
    lines.append(f"  Fuente   : {a['source']}")
    lines.append(f"  Generado : {a['generated_at']}")
    if a.get("days_filter"):
        lines.append(f"  Filtro   : últimos {a['days_filter']} días")
    lines.append("=" * W)

    s = a["summary"]
    lines.append("\n[A] RESUMEN GLOBAL")
    lines.append(f"  Total registros  : {s['total']}")
    lines.append(f"  Schema v1        : {s['v1_count']}")
    lines.append(f"  Schema v2        : {s['v2_count']}")
    lines.append(f"  Resueltos        : {s['resolved']}")
    lines.append(f"  Wins             : {s['wins']}")
    lines.append(f"  Losses           : {s['losses']}")
    lines.append(f"  WR global        : {_wr_str(s['wins'], s['resolved'])}")
    lines.append(f"  Rango fechas     : {s['date_from'] or 'n/d'} → {s['date_to'] or 'n/d'}")
    lines.append(f"  Ciudades         : {s['cities']}")
    lines.append(f"  Traders          : {s['traders']}")

    lines.append("\n[B] SPLIT WHITELIST")
    lines.append(f"  {'Estado':<10} {'Total':>6} {'Wins':>6} {'Losses':>7} {'WR':>8}")
    lines.append("  " + "-" * 42)
    for key, label in (("in", "IN"), ("out", "OUT"), ("unknown", "Unknown")):
        b = a["whitelist_split"].get(key, {})
        lines.append(
            f"  {label:<10} {b.get('total',0):>6} "
            f"{b.get('wins',0):>6} {b.get('losses',0):>7} "
            f"{_wr_str(b.get('wins',0), b.get('resolved',0)):>8}"
        )

    top_n = a.get("top_n", DEFAULT_TOP_N)
    lines.append(f"\n[C] TOP {top_n} CIUDADES")
    for c in a["top_cities"]:
        lines.append(f"\n  {c['city']}")
        lines.append(f"    Total/Res/Wins : {c['total']} / {c['resolved']} / {c['wins']}   WR: {_wr_str(c['wins'], c['resolved'])}")
        conds_str = ", ".join(f"{k}={v}" for k, v in c["conditions"].items())
        lines.append(f"    Condiciones    : {conds_str or 'n/d'}")
        lines.append(f"    Traders top 3  : {', '.join(c['top_traders']) or 'n/d'}")
        if c.get("avg_price_entered") is not None:
            lines.append(f"    Avg price      : {c['avg_price_entered']} ({c['price_bucket']})")
        lines.append(f"    Schema v1/v2   : {c['schema_v1']}/{c['schema_v2']}")
        lines.append(f"    reason_blocked : {c['reason_blocked']}")
        lines.append(f"    policy_status  : {c['city_policy_status_at_record_time']}")
        lines.append(f"    coverage       : {c['observed_coverage_status']}")
        lines.append(f"    fidelity       : {c['settlement_fidelity_status']}")

    d = a["concentration"]
    lines.append("\n[D] CONCENTRACIÓN")
    for t in d["top3"]:
        lines.append(f"  {t['city']:<20} {t['total']:>4} señales")
    lines.append(f"  Top 3 = {d['top3_total']} / {a['summary']['total']} ({d['top3_pct']}%)")
    if d["concentration_warning"]:
        lines.append(f"  [ALERTA] Top 3 > {CONCENTRATION_WARN_THRESHOLD_PCT}% del total — alta concentración")

    e = a["actionability"]
    lines.append("\n[E] SEÑALES DE BAJA ACCIONABILIDAD")
    fi = e.get("settlement_fidelity_issues", {})
    lines.append(f"  settlement_fidelity issues       : {fi.get('count',0)} ({fi.get('pct',0)}%)")
    ci = e.get("coverage_issues", {})
    lines.append(f"  coverage issues (ICAO/no_station) : {ci.get('count',0)} ({ci.get('pct',0)}%)")
    lines.append(f"  out_of_whitelist                 : {e.get('out_of_whitelist_count',0)}")
    lines.append(f"  Schema v1 sin campos v2          : {e.get('v1_count',0)} ({e.get('v1_schema_pct',0)}%)")
    lines.append(f"  Precios extremos (<0.10 / >0.90) : {e.get('extreme_price_count',0)}")
    lines.append(f"  Sin consensus                    : {e.get('no_consensus_count',0)} ({e.get('no_consensus_pct',0)}%)")

    f_data = a["duplicates"]
    lines.append("\n[F] DUPLICADOS")
    lines.append(f"  canonical_signal_id dupes : {f_data.get('canonical_id_dupes',0)}")
    lines.append(f"  market_id dupes           : {f_data.get('market_id_dupes',0)}")
    if f_data.get("v1_dedupe_warning"):
        lines.append(f"  [AVISO] {f_data['v1_count']} registros v1 — dedupe real limitado (sin canonical_signal_id)")

    lines.append("\n[G] CANDIDATOS A AUDITORÍA (OUT whitelist)")
    candidates = a["audit_candidates"]
    if not candidates:
        lines.append("  (sin candidatos en el período analizado)")
    for c in candidates:
        lines.append(f"\n  {c['city']}  [{c['classification'].upper()}]")
        lines.append(f"    n={c['total']} | resueltos={c['resolved']} | WR={_wr_str(c['wins'], c['resolved'])}")
        if c.get("avg_price") is not None:
            lines.append(f"    avg_price={c['avg_price']} | traders={c['n_traders']}")
        lines.append(f"    coverage={c['observed_coverage_status']} | fidelity={c['settlement_fidelity_status']}")
        if c.get("top_traders"):
            lines.append(f"    traders: {', '.join(c['top_traders'])}")

    lines.append("\n" + "=" * W)
    lines.append("  Clasificaciones: ignore | monitor | audit_candidate |")
    lines.append("    needs_settlement_verification | not_actionable")
    lines.append("  Ninguna clasificación implica apertura de trading.")
    lines.append("=" * W)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Report formatting — markdown
# ─────────────────────────────────────────────────────────────────────

def _fmt_markdown(a: dict) -> str:
    lines: list[str] = []
    lines.append("# Blocked Signals Audit — Fase B1")
    lines.append(f"\n**Fuente:** `{a['source']}`  ")
    lines.append(f"**Generado:** {a['generated_at']}  ")
    if a.get("days_filter"):
        lines.append(f"**Filtro:** últimos {a['days_filter']} días  ")

    s = a["summary"]
    lines.append("\n## A. Resumen Global\n")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    for label, val in (
        ("Total registros", s["total"]),
        ("Schema v1", s["v1_count"]),
        ("Schema v2", s["v2_count"]),
        ("Resueltos", s["resolved"]),
        ("Wins", s["wins"]),
        ("Losses", s["losses"]),
        ("WR global", _wr_str(s["wins"], s["resolved"])),
        ("Rango fechas", f"{s['date_from'] or 'n/d'} → {s['date_to'] or 'n/d'}"),
        ("Ciudades", s["cities"]),
        ("Traders", s["traders"]),
    ):
        lines.append(f"| {label} | {val} |")

    lines.append("\n## B. Split Whitelist\n")
    lines.append("| Estado | Total | Wins | Losses | WR |")
    lines.append("|---|---|---|---|---|")
    for key, label in (("in", "IN"), ("out", "OUT"), ("unknown", "Unknown")):
        b = a["whitelist_split"].get(key, {})
        lines.append(
            f"| {label} | {b.get('total',0)} | {b.get('wins',0)} "
            f"| {b.get('losses',0)} | {_wr_str(b.get('wins',0), b.get('resolved',0))} |"
        )

    top_n = a.get("top_n", DEFAULT_TOP_N)
    lines.append(f"\n## C. Top {top_n} Ciudades\n")
    for c in a["top_cities"]:
        lines.append(f"### {c['city']}")
        lines.append(
            f"- **Total/Resueltos/Wins:** {c['total']} / {c['resolved']} / {c['wins']}"
            f" — WR: {_wr_str(c['wins'], c['resolved'])}"
        )
        conds_str = ", ".join(f"{k}={v}" for k, v in c["conditions"].items())
        lines.append(f"- **Condiciones:** {conds_str or 'n/d'}")
        lines.append(f"- **Traders top 3:** {', '.join(c['top_traders']) or 'n/d'}")
        if c.get("avg_price_entered") is not None:
            lines.append(f"- **Avg price:** {c['avg_price_entered']} (bucket: `{c['price_bucket']}`)")
        lines.append(f"- **Schema v1/v2:** {c['schema_v1']}/{c['schema_v2']}")
        lines.append(f"- **reason_blocked:** `{c['reason_blocked']}`")
        lines.append(f"- **policy_status:** `{c['city_policy_status_at_record_time']}`")
        lines.append(f"- **observed_coverage:** `{c['observed_coverage_status']}`")
        lines.append(f"- **settlement_fidelity:** `{c['settlement_fidelity_status']}`")

    d = a["concentration"]
    lines.append("\n## D. Concentración\n")
    lines.append("| Ciudad | Señales |")
    lines.append("|---|---|")
    for t in d["top3"]:
        lines.append(f"| {t['city']} | {t['total']} |")
    lines.append(
        f"\nTop 3 = **{d['top3_total']}** / {a['summary']['total']} (**{d['top3_pct']}%**)"
    )
    if d["concentration_warning"]:
        lines.append(
            f"\n> **ALERTA:** Top 3 > {CONCENTRATION_WARN_THRESHOLD_PCT}% del total — alta concentración de señales."
        )

    e = a["actionability"]
    lines.append("\n## E. Señales de Baja Accionabilidad\n")
    fi = e.get("settlement_fidelity_issues", {})
    lines.append(f"- **settlement_fidelity issues:** {fi.get('count',0)} ({fi.get('pct',0)}%)")
    ci = e.get("coverage_issues", {})
    lines.append(f"- **coverage issues (ICAO/no_station):** {ci.get('count',0)} ({ci.get('pct',0)}%)")
    lines.append(f"- **out_of_whitelist:** {e.get('out_of_whitelist_count',0)}")
    lines.append(f"- **Schema v1 sin campos v2:** {e.get('v1_count',0)} ({e.get('v1_schema_pct',0)}%)")
    lines.append(f"- **Precios extremos (<0.10 / >0.90):** {e.get('extreme_price_count',0)}")
    lines.append(f"- **Sin consensus:** {e.get('no_consensus_count',0)} ({e.get('no_consensus_pct',0)}%)")

    f_data = a["duplicates"]
    lines.append("\n## F. Duplicados\n")
    lines.append(f"- **canonical_signal_id dupes:** {f_data.get('canonical_id_dupes',0)}")
    lines.append(f"- **market_id dupes:** {f_data.get('market_id_dupes',0)}")
    if f_data.get("v1_dedupe_warning"):
        lines.append(
            f"\n> **Aviso:** {f_data['v1_count']} registros v1 — "
            "dedupe real limitado (sin `canonical_signal_id`)."
        )

    lines.append("\n## G. Candidatos a Auditoría (OUT whitelist)\n")
    candidates = a["audit_candidates"]
    if not candidates:
        lines.append("_(sin candidatos en el período analizado)_")
    else:
        lines.append("| Ciudad | n | WR | Avg Price | Traders | Coverage | Fidelity | Clasificación |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in candidates:
            lines.append(
                f"| {c['city']} | {c['total']} | {_wr_str(c['wins'], c['resolved'])} "
                f"| {c.get('avg_price') or 'n/d'} | {c['n_traders']} "
                f"| `{c['observed_coverage_status']}` | `{c['settlement_fidelity_status']}` "
                f"| **{c['classification']}** |"
            )

    lines.append("\n---")
    lines.append("> **Nota:** clasificaciones son solo para auditoría operativa.")
    lines.append("> Ninguna clasificación implica apertura de trading.")
    lines.append("> Valores válidos: `ignore` | `monitor` | `audit_candidate` |")
    lines.append("> `needs_settlement_verification` | `not_actionable`")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def build_analysis(records: list[dict], source: str, days: int | None, top_n: int) -> dict:
    top_cities = section_c(records, top_n)
    return {
        "source": source,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days_filter": days,
        "top_n": top_n,
        "total_records": len(records),
        "summary": section_a(records),
        "whitelist_split": section_b(records),
        "top_cities": top_cities,
        "concentration": section_d(records, top_cities),
        "actionability": section_e(records),
        "duplicates": section_f(records),
        "audit_candidates": section_g(records),
    }


def run(args: argparse.Namespace) -> int:
    if args.source:
        source = Path(args.source)
    else:
        source = None
        for candidate in DEFAULT_SOURCE_PATHS:
            p = Path(candidate)
            if p.exists():
                source = p
                break
        if source is None:
            msg = (
                "No se encontró blocked_signals_resolutions.jsonl.\n"
                "Usa --source para especificar la ruta, o descarga desde Railway:\n"
                "  railway_safe.ps1 ssh cat /app/data/blocked_signals_resolutions.jsonl"
            )
            if args.json:
                print(json.dumps({"error": "file_not_found", "message": msg}))
            else:
                print(f"[ERROR] {msg}", file=sys.stderr)
            return 1

    records = load_records(source, days=args.days)
    if not records:
        suffix = f" (filtro: {args.days}d)" if args.days else ""
        msg = f"Sin registros en {source}{suffix}"
        if args.json:
            print(json.dumps({"warning": "no_records", "message": msg}))
        else:
            print(f"[AVISO] {msg}")
        return 0

    analysis = build_analysis(records, str(source), args.days, args.top)

    if args.json:
        report = json.dumps(analysis, indent=2, default=str)
    elif args.markdown:
        report = _fmt_markdown(analysis)
    else:
        report = _fmt_text(analysis)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            f.write(report)
        print(f"[OK] Reporte escrito en {out_path}")
    else:
        print(report)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Auditoría read-only de blocked_signals_resolutions.jsonl (Fase B1). "
            "Soporta schema v1 y v2. No importa bot.py ni contacta APIs externas."
        )
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Ruta al JSONL (default: busca data/ o /app/data/)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Limitar análisis a los últimos N días (por checked_at)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida en JSON estructurado",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Salida en formato Markdown",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Escribir reporte a este archivo en vez de stdout",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Número de ciudades top a mostrar (default: {DEFAULT_TOP_N})",
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
