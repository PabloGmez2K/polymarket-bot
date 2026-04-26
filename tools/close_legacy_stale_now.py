"""
Cierre one-shot de posiciones legacy stale (sesión 242).

Posiciones abiertas sin snapshots ni evidencia de mercado, con resolution_date
vencida hace 27-30 días. Se cierran como LOSS_TOTAL / legacy_unresolved.

Uso: python /app/tools/close_legacy_stale_now.py
"""

import json
import shutil
from datetime import datetime, timezone

SESSION = "session_242"
NOW = datetime.now(timezone.utc).isoformat()

TRADE_LIFECYCLE_PATH = "/app/data/trade_lifecycle.json"
POSTMORTEM_PATH = "/app/data/postmortem.json"
AGENT_EVENTS_PATH = "/app/data/agent_events.jsonl"

LEGACY_TARGETS = {
    ("Ankara", "2026-03-26", "NO"),
    ("Ankara", "2026-03-26", "YES"),
    ("London", "2026-03-26", "NO"),
    ("Miami", "2026-03-26", "YES"),
    ("Shanghai", "2026-03-27", "NO"),
    ("Toronto", "2026-03-27", "NO"),
    ("Atlanta", "2026-03-28", "YES"),
    ("Buenos Aires", "2026-03-28", "NO"),
    ("Seattle", "2026-03-28", "YES"),
    ("Wellington", "2026-03-28", "NO"),
    ("Madrid", "2026-03-29", "YES"),
}


def backup(path):
    backup_path = f"{path}.bak_{SESSION}"
    shutil.copy2(path, backup_path)
    print(f"  backup: {backup_path}")


def is_target(r):
    key = (r.get("city"), r.get("date"), str(r.get("side", "")).upper())
    return key in LEGACY_TARGETS and r.get("status") == "open"


def close_trade_lifecycle():
    with open(TRADE_LIFECYCLE_PATH) as f:
        data = json.load(f)
    records = data.get("records", [])
    closed = 0
    for r in records:
        if not is_target(r):
            continue
        pnl_cash = -round(float(r.get("total_amount", 0) or 0), 2)
        r["status"] = "closed"
        r["closed_at"] = NOW
        r.setdefault("close_context", {}).update({
            "close_action": "LOSS_TOTAL",
            "close_reason": "legacy_unresolved",
            "close_subtype": "legacy_unresolved",
            "close_price": None,
            "close_shares": None,
            "return_est": None,
            "pnl_cash": pnl_cash,
            "pnl_pct": None,
            "order_id": "",
            "timestamp": NOW,
            "bot_version": "v10.6.36",
        })
        print(f"  trade_lifecycle closed: {r['city']} {r['date']} {r.get('side')} pnl_cash={pnl_cash}")
        closed += 1
    if closed == 0:
        print("  WARN: no targets found in trade_lifecycle — ya cerrados o no existen")
        return 0
    backup(TRADE_LIFECYCLE_PATH)
    with open(TRADE_LIFECYCLE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return closed


def close_postmortem():
    with open(POSTMORTEM_PATH) as f:
        records = json.load(f)
    closed = 0
    for r in records:
        if not is_target(r):
            continue
        pnl_cash = -round(float(r.get("total_amount", 0) or 0), 2)
        r["status"] = "closed"
        r["closed_at"] = NOW
        r["close_action"] = "LOSS_TOTAL"
        r["close_reason"] = "legacy_unresolved"
        r["close_subtype"] = "legacy_unresolved"
        r["close_price"] = None
        r["close_shares"] = 0.0
        r["return_est"] = None
        r["pnl_cash"] = pnl_cash
        r["pnl_pct"] = None
        r["order_id"] = None
        r["bot_version_closed"] = "v10.6.36"
        r["legacy_close"] = True
        print(f"  postmortem closed: {r['city']} {r['date']} {r.get('side')} pnl_cash={pnl_cash}")
        closed += 1
    if closed == 0:
        print("  WARN: no targets found in postmortem — ya cerrados o no existen")
        return 0
    backup(POSTMORTEM_PATH)
    with open(POSTMORTEM_PATH, "w") as f:
        json.dump(records, f, indent=2)
    return closed


def append_agent_event(tl_closed, pm_closed):
    targets_list = sorted(f"{c} {d} {s}" for c, d, s in LEGACY_TARGETS)
    event = {
        "session": SESSION,
        "timestamp": NOW,
        "action": "legacy_close_stale_positions",
        "description": (
            f"Cierre manual one-shot de {len(LEGACY_TARGETS)} posiciones legacy stale "
            f"sin snapshots ni evidencia de mercado (27-30 días vencidas). "
            f"trade_lifecycle: {tl_closed} cerrados, postmortem: {pm_closed} cerrados."
        ),
        "targets": targets_list,
        "close_action": "LOSS_TOTAL",
        "close_reason": "legacy_unresolved",
        "bot_version": "v10.6.36",
    }
    with open(AGENT_EVENTS_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"  agent_events.jsonl: evento escrito session={SESSION}")


if __name__ == "__main__":
    print(f"\n=== Cierre legacy stale one-shot (sesión 242) — {NOW} ===\n")

    print("[1] trade_lifecycle.json")
    tl_closed = close_trade_lifecycle()

    print("\n[2] postmortem.json")
    pm_closed = close_postmortem()

    print("\n[3] agent_events.jsonl")
    append_agent_event(tl_closed, pm_closed)

    print(f"\n=== DONE: trade_lifecycle={tl_closed}, postmortem={pm_closed} ===")
