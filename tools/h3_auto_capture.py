"""H3_AUTOMATED_LOG_ONLY_CAPTURE_V1 — integration wrapper for bot.py hot path.

Drop-in, fail-closed hook. Captures H3 multimodel disagreement snapshots
automatically for directional temperature markets (at_or_above, at_or_below)
during the bot's normal evaluation cycle, without modifying any trading decision.

Guardrails (non-negotiable):
  - eligible_for_policy = False invariant (hardcoded in engine)
  - live_policy_eligible = False invariant (hardcoded in engine)
  - No BUY/SELL/SKIP modification — never returns a value that affects decisions
  - No DB writes
  - No Railway writes
  - No new Gamma fetches — uses market_id/mkt_prob_yes already in the bot cycle
  - All exceptions degrade to warning log only; never raises
  - Gate: H3_AUTO_CAPTURE_ENABLED env var, default "0" (OFF)
  - Only at_or_above / at_or_below conditions (exact/range excluded)
  - Only cities in ACTIVE_CITY_COORDS (Shanghai, Tokyo, Buenos Aires, Ankara)
  - Only unit == "C" (Celsius; Open-Meteo always returns Celsius)
  - Idempotent by snapshot_key + ts_bucket_hourly (max 1 per market per hour)
  - Dedup/idempotency check happens BEFORE the expensive HTTP compute

Status: H3_AUTOMATED_LOG_ONLY_CAPTURE_V1 — default OFF pending Pablo authorization
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from _multimodel_engine import (  # noqa: E402
    ACTIVE_CITY_COORDS,
    H3_HYPOTHESIS_ID,
    build_snapshot,
    snapshot_key,
    ts_bucket_from_ts,
)

_LOG = logging.getLogger("h3_auto_capture")

OUT_DIR = _REPO_ROOT / "data" / "multimodel_shadow"
PREREG_MARKER_FILE = OUT_DIR / "_h3_prereg_cutoff.json"

_SUPPORTED_CONDITIONS = frozenset({"at_or_above", "at_or_below"})


# ── Prereg cutoff helpers ─────────────────────────────────────────────────────

def _load_prereg_cutoff() -> str | None:
    try:
        data = json.loads(PREREG_MARKER_FILE.read_text(encoding="utf-8"))
        return data.get("h3_prereg_cutoff_utc")
    except Exception:
        return None


def _save_prereg_cutoff(ts: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREREG_MARKER_FILE.write_text(
        json.dumps(
            {"h3_prereg_cutoff_utc": ts, "note": "Fixed at first valid forward snapshot. Never change."},
            indent=2,
        ),
        encoding="utf-8",
    )


# ── Snapshot path ─────────────────────────────────────────────────────────────

def _snapshot_path(snap_key: str) -> Path:
    safe_key = snap_key.replace("|", "_").replace(":", "-").replace(" ", "_")[:160]
    return OUT_DIR / f"{safe_key}.json"


# ── Public API ────────────────────────────────────────────────────────────────

def maybe_capture_h3_multimodel_shadow(
    *,
    city: str,
    target_date: str,
    condition: str,
    threshold: float,
    unit: str,
    mkt_prob_yes: float,
    market_id: str | None,
    condition_id: str | None = None,
    market_slug: str | None = None,
) -> None:
    """Attempt to capture an H3 multimodel snapshot from within the bot cycle.

    Fail-closed: catches all exceptions and degrades to warning log only.
    Never raises. Never modifies trading decisions.

    Uses pre-available market data from the bot's evaluation loop — no extra
    Gamma fetches. Open-Meteo models (~5 HTTP calls) are fetched inside
    build_snapshot; these are the only network calls added per eligible market.

    Idempotency is checked BEFORE the expensive HTTP compute:
    if a snapshot for this market/hour already exists, returns immediately.
    """
    # Gate: default OFF
    if os.getenv("H3_AUTO_CAPTURE_ENABLED", "0") != "1":
        return

    # Eligibility guards (fast, before any I/O)
    condition = str(condition or "").strip().lower()
    if condition not in _SUPPORTED_CONDITIONS:
        return
    if unit != "C":
        return
    if city not in ACTIVE_CITY_COORDS:
        return
    if not market_id:
        return

    try:
        ts_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bucket = ts_bucket_from_ts(ts_now)
        sk = snapshot_key(city, market_id, target_date, condition, float(threshold), unit, bucket)
        path = _snapshot_path(sk)

        # Idempotency: skip if snapshot already exists for this market/hour
        if path.exists():
            return

        prereg = _load_prereg_cutoff()

        # Inject pre-available market data — avoids extra Gamma fetch in hot path
        _market_info: dict[str, Any] = {
            "market_id": market_id,
            "condition_id": condition_id or "",
            "slug": market_slug or "",
            "mkt_prob_yes": float(mkt_prob_yes),
            "question": "",
        }

        def _preseeded_market_fetch(c: str, td: str, cond: str, thr: float, u: str) -> dict[str, Any]:
            return _market_info

        snap = build_snapshot(
            city=city,
            target_date=target_date,
            condition=condition,
            threshold=float(threshold),
            unit=unit,
            h3_prereg_cutoff_utc=prereg,
            market_fetch_fn=_preseeded_market_fetch,
        )

        # Register prereg cutoff on first successful snapshot
        if prereg is None:
            prereg = snap["snapshot_ts_utc"]
            _save_prereg_cutoff(prereg)
            snap["h3_prereg_cutoff_utc"] = prereg
            _LOG.info("[H3] H3_PREREG_CUTOFF_UTC registered: %s", prereg)

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")
        _LOG.debug(
            "[H3] snapshot saved: %s/%s/%s/%.1f -> %s",
            city, target_date, condition, threshold, path.name,
        )

    except Exception as exc:
        _LOG.warning("[H3] h3_auto_capture failed (non-fatal, cycle unaffected): %s", exc)
