"""
Cierre de filas legacy Chicago (sesion 72).
Fechas: 2026-03-26, 2026-03-27, 2026-03-28
Accion: LOSS_TOTAL / legacy_unresolved
"""

import json
import shutil
from datetime import datetime, timezone

SESSION = "session_72"
NOW = datetime.now(timezone.utc).isoformat()
LEGACY_DATES = {"2026-03-26", "2026-03-27", "2026-03-28"}

TRADE_LIFECYCLE_PATH = "/app/data/trade_lifecycle.json"
POSTMORTEM_PATH = "/app/data/postmortem.json"
AGENT_EVENTS_PATH = "/app/data/agent_events.jsonl"


def backup(path):
    backup_path = path + ".bak_session72_chicago"
    shutil.copy2(path, backup_path)
    print(f"  backup: {backup_path}")


def close_trade_lifecycle():
    with open(TRADE_LIFECYCLE_PATH) as f:
        data = json.load(f)

    records = data.get("records", [])
    closed_count = 0

    for r in records:
        if r.get("city") != "Chicago":
            continue
        if r.get("status") != "open":
            continue
        date = r.get("date", "")
        if date not in LEGACY_DATES:
            continue

        pnl_cash = -round(float(r.get("total_amount", 0) or 0), 2)

        r["status"] = "closed"
        r["closed_at"] = NOW
        r.setdefault("close_context", {})
        r["close_context"].update({
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
            "bot_version": "v10.6.10",
        })

        print(f"  trade_lifecycle closed: Chicago {date} pnl_cash={pnl_cash}")
        closed_count += 1

    if closed_count == 0:
        print("  WARN: no legacy open Chicago records found in trade_lifecycle.json")
        return 0

    backup(TRADE_LIFECYCLE_PATH)
    with open(TRADE_LIFECYCLE_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return closed_count


def close_postmortem():
    with open(POSTMORTEM_PATH) as f:
        records = json.load(f)

    closed_count = 0

    for r in records:
        if r.get("city") != "Chicago":
            continue
        if r.get("status") != "open":
            continue
        date = r.get("date", "")
        if date not in LEGACY_DATES:
            continue

        total_amount = float(r.get("total_amount", 0) or 0)
        pnl_cash = -round(total_amount, 2)

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
        r["bot_version_closed"] = "v10.6.10"
        r["legacy_close"] = True

        print(f"  postmortem closed: Chicago {date} pnl_cash={pnl_cash}")
        closed_count += 1

    if closed_count == 0:
        print("  WARN: no legacy open Chicago records found in postmortem.json")
        return 0

    backup(POSTMORTEM_PATH)
    with open(POSTMORTEM_PATH, "w") as f:
        json.dump(records, f, indent=2)

    return closed_count


def get_city_accuracy_chicago():
    """Recalcula city_accuracy[Chicago] desde postmortem.json."""
    with open(POSTMORTEM_PATH) as f:
        records = json.load(f)

    closed = [
        r for r in records
        if r.get("city") == "Chicago"
        and r.get("status") == "closed"
        and r.get("close_action") in {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}
    ]

    trades = len(closed)
    wins = sum(1 for r in closed if (r.get("pnl_cash") or 0) > 0)
    pnl = round(sum(r.get("pnl_cash", 0) or 0 for r in closed), 2)
    win_rate = round(wins / trades * 100, 1) if trades > 0 else 0.0

    return {"trades": trades, "wins": wins, "pnl": pnl, "win_rate": win_rate}


def append_agent_event(tl_closed, pm_closed, city_acc):
    event = {
        "session": SESSION,
        "timestamp": NOW,
        "action": "legacy_close_chicago",
        "description": (
            f"Cierre manual de filas legacy Chicago: "
            f"{', '.join(sorted(LEGACY_DATES))}. "
            f"trade_lifecycle: {tl_closed} cerrados, postmortem: {pm_closed} cerrados. "
            f"city_accuracy[Chicago]: trades={city_acc['trades']}, wins={city_acc['wins']}, "
            f"pnl={city_acc['pnl']}, win_rate={city_acc['win_rate']}%"
        ),
        "city_accuracy_chicago": city_acc,
        "dates_closed": sorted(LEGACY_DATES),
        "close_action": "LOSS_TOTAL",
        "close_reason": "legacy_unresolved",
        "bot_version": "v10.6.10",
    }
    with open(AGENT_EVENTS_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"  agent_events.jsonl: evento escrito session={SESSION}")


if __name__ == "__main__":
    print("\n=== Cierre legacy Chicago (sesion 72) ===\n")

    print("[1] trade_lifecycle.json")
    tl_closed = close_trade_lifecycle()

    print("\n[2] postmortem.json")
    pm_closed = close_postmortem()

    print("\n[3] city_accuracy[Chicago] recalculado")
    city_acc = get_city_accuracy_chicago()
    print(f"  {city_acc}")

    print("\n[4] agent_events.jsonl")
    append_agent_event(tl_closed, pm_closed, city_acc)

    print(f"\n=== DONE: trade_lifecycle={tl_closed}, postmortem={pm_closed} ===")
    print(f"city_accuracy[Chicago]: {city_acc}")
