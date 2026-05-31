"""R1 Reconciled Executions CLI — LOG_ONLY.

Produces reconciled_executions.jsonl from context snapshots and CLOB fills.
Does NOT call the API. Does NOT touch Railway. Does NOT import bot.py.
Does NOT write DB. Does NOT emit canonical P&L.

Usage:
  python tools/reconcile_executions.py \\
    --performance data/runtime_import/performance.json \\
    --postmortem  data/runtime_import/postmortem.json  \\
    --trade-lifecycle data/runtime_import/trade_lifecycle.json \\
    --provenance-json data/runtime_import/r1_context_provenance.json \\
    --output data/reconciled_executions.jsonl \\
    --dry-run

Add --offline-fills-json path/to/fills.json to inject fills without API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Engine is a pure sibling module — no bot.py, no Railway
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._reconcile_engine import (
    load_json_file,
    reconcile,
    compute_coverage_summary,
    SCHEMA_VERSION,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_provenance(provenance_json: str | None, args: argparse.Namespace) -> dict:
    """Build or load provenance metadata."""
    if provenance_json and Path(provenance_json).exists():
        raw = load_json_file(provenance_json)
        # Accept both flat and keyed-by-file structures
        return raw

    # Build minimal provenance from the supplied file paths
    prov: dict = {}
    ts = datetime.now(timezone.utc).isoformat()
    for key, path_str in [
        ("performance", args.performance),
        ("postmortem", args.postmortem),
        ("trade_lifecycle", getattr(args, "trade_lifecycle", None)),
    ]:
        if path_str and Path(path_str).exists():
            p = Path(path_str)
            prov[key] = {
                "source_path": f"/app/data/{p.name}",
                "capture_ts": ts,
                "capture_method": "railway_ssh_cat",
                "sha256": _sha256_file(p),
                "local_path": str(p),
                "bytes": p.stat().st_size,
                "note": "auto-generated provenance — prefer explicit --provenance-json",
            }
    return prov


def _print_summary(rows: list[dict], output_path: str | None, dry_run: bool) -> None:
    summary = compute_coverage_summary(rows)
    print("\n=== R1 Reconciled Executions — Coverage Report ===")
    print(f"  Schema version   : {SCHEMA_VERSION}")
    print(f"  Mode             : {'DRY-RUN' if dry_run else 'WRITE'}")
    if output_path:
        print(f"  Output path      : {output_path}")
    print()
    print(f"  Total rows       : {summary['total_rows']}")
    print(f"  Reconciled fills : {summary['reconciled_fills']}")
    print(f"  Needs recon      : {summary['needs_reconciliation']}")
    print(f"    missing_fill_identity : {summary['missing_fill_identity']}")
    print(f"    fill_not_found        : {summary['fill_not_found']}")
    print()
    print(f"  Eligible for learning  : {summary['eligible_for_learning']}")
    print(f"  Eligible for calibration: 0  (R2 required)")
    print(f"  Suspect fidelity       : {summary['suspect_fidelity']}")
    print(f"  Dev fixture            : {summary['dev_fixture']}")
    print()
    print(f"  Rows with order_id     : {summary['rows_with_order_id']}")
    print(f"  Rows missing order_id  : {summary['rows_missing_order_id']}")
    print()
    print("  P&L canonical status   : none — not emitted")
    print("  BANKROLL status        : HOLD — not touched")
    print("  Trading authorization  : none")
    print()

    # Sample rows
    reconciled = [r for r in rows if r.get("execution_id") and not r.get("needs_reconciliation")]
    if reconciled:
        print(f"  Sample reconciled execution(s):")
        for r in reconciled[:3]:
            print(f"    {r['execution_id']}  city={r['city']}  side={r['side']}"
                  f"  fidelity={r['source_fidelity']}  eligible={r['eligible_for_learning']}")
    blocked = [r for r in rows if r.get("reconciliation_blocker") == "missing_fill_identity"]
    if blocked:
        print(f"  Sample blocked (missing_fill_identity):")
        for r in blocked[:3]:
            print(f"    order_id=None  city={r['city']}  date={r['date_iso']}  action=BUY")

    print("=" * 50)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="R1 reconcile_executions LOG_ONLY — produces reconciled_executions.jsonl",
    )
    ap.add_argument("--performance", required=True, help="Path to performance.json")
    ap.add_argument("--postmortem", help="Path to postmortem.json (optional)")
    ap.add_argument("--trade-lifecycle", dest="trade_lifecycle",
                    help="Path to trade_lifecycle.json (context only, optional)")
    ap.add_argument("--provenance-json", dest="provenance_json",
                    help="Path to provenance JSON (r1_context_provenance.json)")
    ap.add_argument("--output", default="data/reconciled_executions.jsonl",
                    help="Output JSONL path (default: data/reconciled_executions.jsonl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print coverage summary, do not write output file")
    ap.add_argument("--offline-fills-json", dest="offline_fills_json",
                    help="Path to JSON dict {order_id: [fill_dicts]} for offline testing")
    args = ap.parse_args()

    # Validate required input
    perf_path = Path(args.performance)
    if not perf_path.exists():
        print(f"ERROR: --performance file not found: {args.performance}", file=sys.stderr)
        return 1

    # Load data
    try:
        performance_data = load_json_file(perf_path)
        if not isinstance(performance_data, list):
            print("ERROR: performance.json must be a JSON array", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"ERROR loading performance.json: {e}", file=sys.stderr)
        return 1

    postmortem_data: list[dict] | None = None
    if args.postmortem and Path(args.postmortem).exists():
        try:
            postmortem_data = load_json_file(args.postmortem)
        except Exception as e:
            print(f"WARNING: could not load postmortem.json: {e}", file=sys.stderr)

    lifecycle_data: dict | None = None
    if args.trade_lifecycle and Path(args.trade_lifecycle).exists():
        try:
            lifecycle_data = load_json_file(args.trade_lifecycle)
        except Exception as e:
            print(f"WARNING: could not load trade_lifecycle.json: {e}", file=sys.stderr)

    # Load offline fills
    offline_fills_map: dict[str, list[dict]] = {}
    if args.offline_fills_json and Path(args.offline_fills_json).exists():
        try:
            offline_fills_map = load_json_file(args.offline_fills_json)
        except Exception as e:
            print(f"WARNING: could not load offline-fills-json: {e}", file=sys.stderr)

    # Load/build provenance
    provenance = _load_provenance(args.provenance_json, args)
    if not provenance:
        print("ERROR: provenance missing and could not be auto-generated", file=sys.stderr)
        return 1

    # Run reconciliation
    rows = reconcile(
        performance_data=performance_data,
        postmortem_data=postmortem_data,
        lifecycle_data=lifecycle_data,
        context_provenance=provenance,
        offline_fills_map=offline_fills_map,
    )

    _print_summary(rows, args.output if not args.dry_run else None, dry_run=args.dry_run)

    if args.dry_run:
        print("[DRY-RUN] No file written.")
        return 0

    # Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[WRITE] {len(rows)} rows → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
