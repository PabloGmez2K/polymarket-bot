#!/usr/bin/env python3
"""City Intelligence Digest v1 — LOG_ONLY read-only daily synthesis.

Merges outputs from:
  1. City Lifecycle Review Monitor  (data/city_lifecycle_review.json)
  2. Source Onboarding Scanner      (data/source_onboarding.json)
  3. Source Audit Workbench         (data/source_audits/*.json — optional dir)
  4. City Promotion Gate            (data/city_promotion_gate.json — optional)

Generates a unified daily digest:
  - data/city_intelligence_digest.json
  - docs/city_intelligence_digest_latest.md

Telegram integration is handled by maybe_run_city_intelligence_digest_alert()
in bot.py (wired from run_observability_alerts). This tool only writes JSON/MD.

NO BUY/SELL/SKIP. NO BANKROLL. NO Phase C. NO Telegram. NO Railway. NO DB writes.
NO city mode changes. NO env vars. NO auto-promotion.
Does NOT execute source_audit_workbench.py — only reads existing outputs.
Does NOT touch city_lifecycle_review_monitor.py — only reads its JSON output.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LIFECYCLE_REVIEW = REPO_ROOT / "data" / "city_lifecycle_review.json"
DEFAULT_SOURCE_ONBOARDING = REPO_ROOT / "data" / "source_onboarding.json"
DEFAULT_SOURCE_AUDITS_DIR = REPO_ROOT / "data" / "source_audits"
DEFAULT_PROMOTION_GATE = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_intelligence_digest.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_intelligence_digest_latest.md"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY — This digest is observational only. "
    "No BUY, SELL, or SKIP decisions. No BANKROLL changes. No Phase C. "
    "No city mode changes (whitelist/canary/active/blocked). No env vars. "
    "No Railway. No auto-promotion. "
    "All items require explicit human review before any policy action."
)

# Lifecycle transitions that go into the Review Queue (strongest first)
_REVIEW_QUEUE_PRIORITY = [
    "silent_promotion_detected",
    "manual_review_pending",
    "active_review",
    "canary_review",
    "preliminary_review_candidate",
    "observed_audit_review",
]
_REVIEW_QUEUE_TRANSITIONS = set(_REVIEW_QUEUE_PRIORITY)

# Source audit statuses that surface in the digest
_AUDIT_ACTIONABLE_STATUSES = {
    "NEEDS_MANUAL_SOURCE_LOOKUP",
    "READY_FOR_OBSERVED_AUDIT_REVIEW",
    "SOURCE_AUDIT_PASS",
    "SOURCE_AUDIT_FAIL",
}

# Source onboarding states that get full detail in digest
_ONBOARDING_READY_STATES = {"READY_FOR_SOURCE_AUDIT"}
_ONBOARDING_QUIET_STATES = {"WAITING_EVIDENCE", "RANGE_ONLY_NOT_OPERABLE"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="City Intelligence Digest v1 (LOG_ONLY)")
    p.add_argument("--lifecycle-review", default=str(DEFAULT_LIFECYCLE_REVIEW))
    p.add_argument("--source-onboarding", default=str(DEFAULT_SOURCE_ONBOARDING))
    p.add_argument("--source-audits-dir", default=str(DEFAULT_SOURCE_AUDITS_DIR))
    p.add_argument("--promotion-gate", default=str(DEFAULT_PROMOTION_GATE))
    p.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    p.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return p.parse_args(argv)


def _load_json_optional(path_str, label):
    """Load JSON file. Returns (data, None) on success or (None, error_str) on failure."""
    path = Path(path_str)
    if not path.exists():
        return None, f"{label} not found: {path_str}"
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return json.loads(raw.decode("utf-8")), None
    except Exception as exc:
        return None, f"{label} parse error: {exc}"


def _load_source_audits(audits_dir_str):
    """Load all JSON files from the source_audits directory.

    Returns (list_of_audit_dicts, warnings).
    Does NOT invoke source_audit_workbench.py — reads existing outputs only.
    """
    audits = []
    warnings = []
    audits_dir = Path(audits_dir_str)
    if not audits_dir.exists():
        warnings.append(f"source_audits dir not found: {audits_dir_str}")
        return audits, warnings
    for json_file in sorted(audits_dir.glob("*.json")):
        try:
            raw = json_file.read_bytes()
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]
            data = json.loads(raw.decode("utf-8"))
            audits.append(data)
        except Exception as exc:
            warnings.append(f"source_audit parse error {json_file.name}: {exc}")
    return audits, warnings


def load_inputs(args):
    """Load all inputs. Returns (inputs_dict, warnings)."""
    warnings = []
    inputs = {}

    lifecycle_data, err = _load_json_optional(args.lifecycle_review, "city_lifecycle_review")
    if err:
        warnings.append(f"lifecycle_review missing (will use empty): {err}")
        lifecycle_data = None
    inputs["lifecycle"] = lifecycle_data

    onboarding_data, err = _load_json_optional(args.source_onboarding, "source_onboarding")
    if err:
        warnings.append(f"source_onboarding missing (will use empty): {err}")
        onboarding_data = None
    inputs["onboarding"] = onboarding_data

    audits, audit_warns = _load_source_audits(args.source_audits_dir)
    warnings.extend(audit_warns)
    inputs["source_audits"] = audits

    promo_gate, err = _load_json_optional(args.promotion_gate, "city_promotion_gate")
    if err:
        warnings.append(f"promotion_gate optional missing: {err}")
        promo_gate = None
    inputs["promotion_gate"] = promo_gate

    return inputs, warnings


def build_review_queue(lifecycle_data):
    """Extract and prioritize lifecycle cities requiring human review."""
    if not lifecycle_data:
        return []
    cities = lifecycle_data.get("cities", [])
    queue = [
        c for c in cities
        if c.get("transition_proposed") in _REVIEW_QUEUE_TRANSITIONS
    ]
    priority_map = {t: i for i, t in enumerate(_REVIEW_QUEUE_PRIORITY)}
    queue.sort(key=lambda r: (
        priority_map.get(r.get("transition_proposed", ""), 99),
        r.get("city", ""),
    ))
    return queue


def build_onboarding_section(onboarding_data):
    """Extract and categorize source onboarding candidates."""
    if not onboarding_data:
        return {"ready": [], "blocked_high": [], "waiting_count": 0, "other_count": 0}

    cities = onboarding_data.get("cities", [])
    ready = []
    blocked_high = []
    waiting_count = 0
    other_count = 0

    for c in cities:
        state = c.get("state", "")
        if state == "READY_FOR_SOURCE_AUDIT":
            ready.append(c)
        elif state == "SOURCE_BLOCKED" and c.get("priority_score", -999) >= -0.5:
            blocked_high.append(c)
        elif state in _ONBOARDING_QUIET_STATES:
            waiting_count += 1
        else:
            other_count += 1

    ready.sort(key=lambda r: -r.get("priority_score", 0))
    blocked_high.sort(key=lambda r: -r.get("priority_score", 0))
    return {
        "ready": ready,
        "blocked_high": blocked_high,
        "waiting_count": waiting_count,
        "other_count": other_count,
        "degraded": onboarding_data.get("degraded", False),
    }


def build_source_audit_section(source_audits):
    """Summarize source audit package outputs (read-only, no execution)."""
    actionable = []
    quiet = []
    for audit in source_audits:
        status = audit.get("status", "")
        city = audit.get("city", "?")
        generated_at = audit.get("generated_at", "")
        if status in _AUDIT_ACTIONABLE_STATUSES:
            actionable.append({
                "city": city,
                "status": status,
                "generated_at": generated_at,
                "recommendation": audit.get("recommendation"),
                "proposed_next_step": audit.get("proposed_next_step"),
            })
        else:
            quiet.append({"city": city, "status": status})
    return {"actionable": actionable, "quiet": quiet}


def build_drift_section(review_queue):
    """Extract policy conflict / silent promotion items from review queue."""
    return [r for r in review_queue if r.get("transition_proposed") == "silent_promotion_detected"]


def build_digest(inputs):
    """Build the full digest payload from all inputs."""
    review_queue = build_review_queue(inputs["lifecycle"])
    onboarding = build_onboarding_section(inputs["onboarding"])
    source_audits = build_source_audit_section(inputs["source_audits"])
    drift = build_drift_section(review_queue)

    lifecycle_meta = {}
    if inputs["lifecycle"]:
        lifecycle_meta = {
            "generated_at": inputs["lifecycle"].get("generated_at"),
            "n_cities": inputs["lifecycle"].get("summary", {}).get("n_cities", 0),
            "transition_counts": inputs["lifecycle"].get("summary", {}).get("transition_counts", {}),
            "warnings": inputs["lifecycle"].get("warnings", []),
        }

    onboarding_meta = {}
    if inputs["onboarding"]:
        onboarding_meta = {
            "generated_at": inputs["onboarding"].get("generated_at"),
            "n_candidates": inputs["onboarding"].get("summary", {}).get("n_candidates", 0),
            "degraded": inputs["onboarding"].get("degraded", False),
        }

    return {
        "review_queue": review_queue,
        "onboarding": onboarding,
        "source_audits": source_audits,
        "drift": drift,
        "lifecycle_meta": lifecycle_meta,
        "onboarding_meta": onboarding_meta,
        "n_source_audit_packages": len(inputs["source_audits"]),
    }


def render_markdown(payload, digest, warnings):
    """Render the unified digest markdown."""
    review_queue = digest["review_queue"]
    onboarding = digest["onboarding"]
    audit_section = digest["source_audits"]
    drift = digest["drift"]

    lines = [
        "# City Intelligence Digest v1",
        "",
        f"> **{LOG_ONLY_DISCLAIMER}**",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Lifecycle reviewed: `{digest['lifecycle_meta'].get('n_cities', 'N/A')}` cities",
        f"- Onboarding candidates: `{digest['onboarding_meta'].get('n_candidates', 'N/A')}`",
        f"- Source audit packages: `{digest['n_source_audit_packages']}`",
    ]

    if warnings:
        lines += ["", "### Warnings", ""]
        for w in warnings:
            lines.append(f"- {w}")

    # Section 1: Review Queue
    lines += [
        "",
        "## 1. Review Queue",
        "",
        "Cities in lifecycle flow requiring human attention (strongest signal first):",
        "",
    ]
    if review_queue:
        for r in review_queue:
            transition = r.get("transition_proposed", "?")
            city = r.get("city", "?")
            stage = r.get("lifecycle_stage", "?")
            notes = r.get("notes") or []
            notes_str = "; ".join(notes[:2]) if notes else "-"
            lines.append(f"- **{city}** (`{transition}`) stage=`{stage}` — {notes_str}")
    else:
        lines.append("- None at this time.")

    # Section 2: Source Onboarding
    lines += [
        "",
        "## 2. Source Onboarding",
        "",
        "Cities outside the flow with significant external signal:",
        "",
    ]
    if onboarding.get("degraded"):
        lines.append("> ⚠ DEGRADED: RESOLUTION_ICAO unavailable — source feasibility unknown.")
        lines.append("")

    ready_cities = onboarding.get("ready", [])
    blocked_high = onboarding.get("blocked_high", [])
    waiting_count = onboarding.get("waiting_count", 0)

    if ready_cities:
        lines.append("### READY_FOR_SOURCE_AUDIT")
        lines.append("")
        for c in ready_cities:
            t = c.get("trader", {})
            b = c.get("blocked_signals", {})
            wr_str = f"WR={b['wr']:.0%} n={b['n']}" if b.get("wr") is not None and b.get("qualifies") else f"n={b.get('n', 0)}"
            lines.append(
                f"- **{c['city']}** score={c.get('priority_score', 0):.2f}"
                f" feasibility={c.get('source_feasibility', '?')}"
                f" traders={t.get('n_sources', 0)}/{t.get('n_days', 0)}d"
                f" blocked={wr_str}"
            )
        lines.append("")

    if blocked_high:
        lines.append("### SOURCE_BLOCKED (high score)")
        lines.append("")
        for c in blocked_high:
            lines.append(f"- **{c['city']}** score={c.get('priority_score', 0):.2f} — no ICAO/station found")
        lines.append("")

    if waiting_count > 0:
        lines.append(f"### Quiet / Waiting")
        lines.append("")
        lines.append(f"- {waiting_count} cities in WAITING_EVIDENCE or RANGE_ONLY_NOT_OPERABLE — no action needed yet.")
        lines.append("")

    if not ready_cities and not blocked_high and waiting_count == 0:
        lines.append("- No onboarding candidates at this time.")

    # Section 3: Source Audit Packages
    lines += [
        "",
        "## 3. Source Audit Packages",
        "",
        "Existing audit packages from source_audit_workbench (read-only — tool not re-executed):",
        "",
    ]
    actionable = audit_section.get("actionable", [])
    quiet_audits = audit_section.get("quiet", [])
    if actionable:
        for a in actionable:
            next_step = a.get("proposed_next_step") or a.get("recommendation") or "-"
            lines.append(
                f"- **{a['city']}** `{a['status']}` — next: {next_step}"
                f" (package: {a.get('generated_at', '?')[:10]})"
            )
    elif quiet_audits:
        for a in quiet_audits:
            lines.append(f"- **{a['city']}** `{a['status']}`")
    else:
        lines.append("- No source audit packages found.")

    # Section 4: Drift / Policy Conflicts
    lines += [
        "",
        "## 4. Drift / Policy Conflicts",
        "",
    ]
    if drift:
        lines.append("**ACTION REQUIRED — Policy inconsistency detected:**")
        lines.append("")
        for r in drift:
            notes_str = "; ".join(r.get("notes", [])) or "-"
            lines.append(f"- **{r['city']}** `silent_promotion_detected` — {notes_str}")
    else:
        lines.append("- No policy conflicts detected.")

    # Section 5: Quiet / Waiting summary
    lifecycle_waiting = 0
    if digest["lifecycle_meta"].get("transition_counts"):
        lifecycle_waiting = digest["lifecycle_meta"]["transition_counts"].get("none", 0)

    lines += [
        "",
        "## 5. Quiet / Waiting",
        "",
        f"- Lifecycle: {lifecycle_waiting} cities with no transition proposed.",
        f"- Onboarding: {onboarding.get('waiting_count', 0)} WAITING_EVIDENCE / RANGE_ONLY cities.",
        f"- Source audits quiet: {len(audit_section.get('quiet', []))} packages.",
    ]

    lines += [
        "",
        "---",
        "",
        f"*{LOG_ONLY_DISCLAIMER}*",
    ]
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)
    inputs, warnings = load_inputs(args)
    digest = build_digest(inputs)

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    payload = {
        "generated_at": now_iso,
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "warnings": warnings,
        "summary": {
            "review_queue_count": len(digest["review_queue"]),
            "review_queue_transitions": dict(Counter(
                r.get("transition_proposed", "?") for r in digest["review_queue"]
            )),
            "onboarding_ready": len(digest["onboarding"].get("ready", [])),
            "onboarding_blocked_high": len(digest["onboarding"].get("blocked_high", [])),
            "onboarding_waiting": digest["onboarding"].get("waiting_count", 0),
            "source_audit_packages": digest["n_source_audit_packages"],
            "source_audit_actionable": len(digest["source_audits"].get("actionable", [])),
            "drift_conflicts": len(digest["drift"]),
        },
        "review_queue": digest["review_queue"],
        "onboarding": digest["onboarding"],
        "source_audits": digest["source_audits"],
        "drift": digest["drift"],
        "lifecycle_meta": digest["lifecycle_meta"],
        "onboarding_meta": digest["onboarding_meta"],
    }

    out_json = Path(args.json_output)
    out_md = Path(args.md_output)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload, digest, warnings), encoding="utf-8")

    for w in warnings:
        print(f"  WARN: {w}")
    print(f"City Intelligence Digest written to {out_json}")
    print(f"Markdown summary written to {out_md}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
