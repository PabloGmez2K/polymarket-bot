"""
Reconciliación definitiva de 11 posiciones legacy stale (sesión 243).

Outcomes investigados en Polymarket (abr 2026). Revierte los cierres LOSS_TOTAL
incorrectos aplicados por close_legacy_stale_now.py y aplica el resultado real.

Fuentes de resolución:
- Ankara, London:  Wunderground / Esenboğa & Heathrow airports
- Miami, Atlanta, Seattle: NWS / KSEA (Wunderground, °F markets)
- Shanghai: Shanghai Met Service (°C)
- Toronto: Environment Canada / CYYZ (Wunderground, °C)
- Buenos Aires: SMN / Ministro Pistarini (Wunderground, °C)
- Wellington: MetService / Kelburn (°C)
- Madrid: AEMET / Barajas (Wunderground, °C)

Uso: python /app/tools/reconcile_legacy_stale_with_outcomes.py
"""

import json
import shutil
from datetime import datetime, timezone

SESSION = "session_243"
NOW = datetime.now(timezone.utc).isoformat()

TRADE_LIFECYCLE_PATH = "/app/data/trade_lifecycle.json"
POSTMORTEM_PATH = "/app/data/postmortem.json"
AGENT_EVENTS_PATH = "/app/data/agent_events.jsonl"

# (city, date, side) -> outcome spec
# close_action:   RESOLVED_WIN | LOSS_TOTAL
# resolved_temp:  temperatura real registrada
# our_token:      descripción del token que compramos
# confidence:     alta | media
OUTCOMES = {
    ("Ankara", "2026-03-26", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "10°C",
        "our_token": "NO on 11°C",
        "close_price": 1.0,
        "confidence": "alta",
        "source": "Polymarket / Wunderground Esenboğa Intl Airport",
    },
    ("Ankara", "2026-03-26", "YES"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "10°C",
        "our_token": "YES on 10°C",
        "close_price": 1.0,
        "confidence": "alta",
        "source": "Polymarket / Wunderground Esenboğa Intl Airport",
    },
    ("London", "2026-03-26", "NO"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved",
        "resolved_temp": "10°C",
        "our_token": "NO on 10°C",
        "close_price": 0.0,
        "confidence": "alta",
        "source": "Polymarket / Met Office Heathrow",
    },
    ("Miami", "2026-03-26", "YES"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "83°F (82-83°F range)",
        "our_token": "YES on 82-83°F",
        "close_price": 1.0,
        "confidence": "alta",
        "source": "Polymarket / NWS Miami Intl Airport",
    },
    ("Shanghai", "2026-03-27", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "19°C",
        "our_token": "NO on ~13°C",
        "close_price": 1.0,
        "confidence": "alta",
        "source": "Polymarket / Shanghai Met Service",
    },
    ("Toronto", "2026-03-27", "NO"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved",
        "resolved_temp": "0°C",
        "our_token": "NO on 0°C",
        "close_price": 0.0,
        "confidence": "media",
        "source": "Polymarket / Environment Canada CYYZ",
    },
    ("Atlanta", "2026-03-28", "YES"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved",
        "resolved_temp": "70°F (70-71°F range)",
        "our_token": "YES on 68-69°F",
        "close_price": 0.0,
        "confidence": "media",
        "source": "Polymarket / NWS KATL",
    },
    ("Buenos Aires", "2026-03-28", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "≥27°C",
        "our_token": "NO on ~26°C",
        "close_price": 1.0,
        "confidence": "media",
        "source": "Polymarket / SMN Ministro Pistarini",
    },
    ("Seattle", "2026-03-28", "YES"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved",
        "resolved_temp": "55°F (54-55°F range)",
        "our_token": "YES on 52-53°F",
        "close_price": 0.0,
        "confidence": "media",
        "source": "Polymarket / Wunderground KSEA",
    },
    ("Wellington", "2026-03-28", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved",
        "resolved_temp": "22°C",
        "our_token": "NO on ~20-21°C",
        "close_price": 1.0,
        "confidence": "alta",
        "source": "Polymarket / MetService Kelburn",
    },
    ("Madrid", "2026-03-29", "YES"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved",
        "resolved_temp": "13°C",
        "our_token": "YES on 12°C",
        "close_price": 0.0,
        "confidence": "alta",
        "source": "Polymarket / AEMET Barajas",
    },
}


def backup(path, suffix):
    backup_path = f"{path}.bak_{suffix}"
    shutil.copy2(path, backup_path)
    print(f"  backup: {backup_path}")


def compute_pnl(amount, shares, spec):
    amount = round(float(amount or 0), 2)
    shares = round(float(shares or 0), 4)
    if spec["close_action"] == "RESOLVED_WIN":
        return_est = round(shares, 2)
        pnl_cash = round(return_est - amount, 2)
        pnl_pct = round((return_est / amount - 1.0) * 100, 1) if amount > 0 else None
    else:
        return_est = 0.0
        pnl_cash = round(-amount, 2)
        pnl_pct = -100.0 if amount > 0 else None
    return return_est, pnl_cash, pnl_pct


def reconcile_trade_lifecycle():
    with open(TRADE_LIFECYCLE_PATH) as f:
        data = json.load(f)
    records = data.get("records", [])
    patched = 0
    summary = []
    for r in records:
        key = (r.get("city"), r.get("date"), str(r.get("side", "")).upper())
        spec = OUTCOMES.get(key)
        if spec is None:
            continue
        # Only patch positions closed as legacy_unresolved today
        cc = r.get("close_context") or {}
        if cc.get("close_reason") != "legacy_unresolved":
            print(f"  SKIP {key}: close_reason={cc.get('close_reason')} (not legacy_unresolved)")
            continue
        return_est, pnl_cash, pnl_pct = compute_pnl(r.get("total_amount"), r.get("total_shares"), spec)
        r["close_context"].update({
            "close_action": spec["close_action"],
            "close_reason": spec["close_reason"],
            "close_subtype": "market_resolved",
            "close_price": spec["close_price"],
            "close_shares": round(float(r.get("total_shares") or 0), 4),
            "return_est": return_est,
            "pnl_cash": pnl_cash,
            "pnl_pct": pnl_pct,
            "timestamp": NOW,
            "bot_version": "v10.6.36",
            "resolved_temp": spec["resolved_temp"],
            "our_token": spec["our_token"],
            "reconciliation_confidence": spec["confidence"],
            "resolution_source": spec["source"],
            "reconciled_session": SESSION,
        })
        summary.append({
            "key": f"{key[0]} {key[1]} {key[2]}",
            "action": spec["close_action"],
            "pnl_cash": pnl_cash,
            "confidence": spec["confidence"],
            "resolved_temp": spec["resolved_temp"],
        })
        print(
            f"  TL patched: {key[0]} {key[1]} {key[2]} → "
            f"{spec['close_action']} | pnl={pnl_cash:+.2f} | "
            f"temp={spec['resolved_temp']} | conf={spec['confidence']}"
        )
        patched += 1
    if patched:
        backup(TRADE_LIFECYCLE_PATH, SESSION)
        with open(TRADE_LIFECYCLE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    return patched, summary


def reconcile_postmortem():
    with open(POSTMORTEM_PATH) as f:
        records = json.load(f)
    patched = 0
    for r in records:
        key = (r.get("city"), r.get("date"), str(r.get("side", "")).upper())
        spec = OUTCOMES.get(key)
        if spec is None:
            continue
        if r.get("close_reason") != "legacy_unresolved":
            print(f"  SKIP PM {key}: close_reason={r.get('close_reason')}")
            continue
        return_est, pnl_cash, pnl_pct = compute_pnl(r.get("total_amount"), r.get("total_shares"), spec)
        r["close_action"] = spec["close_action"]
        r["close_reason"] = spec["close_reason"]
        r["close_subtype"] = "market_resolved"
        r["close_price"] = spec["close_price"]
        r["close_shares"] = round(float(r.get("total_shares") or 0), 4)
        r["return_est"] = return_est
        r["pnl_cash"] = pnl_cash
        r["pnl_pct"] = pnl_pct
        r["resolved_temp"] = spec["resolved_temp"]
        r["our_token"] = spec["our_token"]
        r["reconciliation_confidence"] = spec["confidence"]
        r["resolution_source"] = spec["source"]
        r["reconciled_session"] = SESSION
        print(
            f"  PM patched: {key[0]} {key[1]} {key[2]} → "
            f"{spec['close_action']} | pnl={pnl_cash:+.2f} | conf={spec['confidence']}"
        )
        patched += 1
    if patched:
        backup(POSTMORTEM_PATH, SESSION)
        with open(POSTMORTEM_PATH, "w") as f:
            json.dump(records, f, indent=2)
    return patched


def append_agent_event(tl_patched, pm_patched, summary):
    wins = [s for s in summary if s["action"] == "RESOLVED_WIN"]
    losses = [s for s in summary if s["action"] == "LOSS_TOTAL"]
    net_pnl = round(sum(s["pnl_cash"] for s in summary), 2)
    event = {
        "session": SESSION,
        "timestamp": NOW,
        "action": "legacy_reconcile_with_outcomes",
        "description": (
            f"Reconciliación definitiva de {len(summary)} posiciones legacy stale con outcomes reales de Polymarket. "
            f"WIN={len(wins)}, LOSS={len(losses)}, net_pnl={net_pnl:+.2f}. "
            f"Sustituye los cierres LOSS_TOTAL/legacy_unresolved de session_242."
        ),
        "wins": [s["key"] for s in wins],
        "losses": [s["key"] for s in losses],
        "net_pnl": net_pnl,
        "tl_patched": tl_patched,
        "pm_patched": pm_patched,
        "detail": summary,
        "bot_version": "v10.6.36",
    }
    with open(AGENT_EVENTS_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"  agent_events.jsonl: evento escrito")


if __name__ == "__main__":
    print(f"\n=== Reconciliación legacy stale con outcomes reales ({SESSION}) — {NOW} ===\n")

    print("[1] trade_lifecycle.json")
    tl_patched, summary = reconcile_trade_lifecycle()

    print(f"\n[2] postmortem.json")
    pm_patched = reconcile_postmortem()

    print(f"\n[3] agent_events.jsonl")
    append_agent_event(tl_patched, pm_patched, summary)

    wins = [s for s in summary if s["action"] == "RESOLVED_WIN"]
    losses = [s for s in summary if s["action"] == "LOSS_TOTAL"]
    net_pnl = round(sum(s["pnl_cash"] for s in summary), 2)

    print(f"\n=== DONE ===")
    print(f"  trade_lifecycle patched: {tl_patched}")
    print(f"  postmortem patched:      {pm_patched}")
    print(f"  WIN: {len(wins)} | LOSS: {len(losses)}")
    print(f"  Net P&L (trade_lifecycle amounts): {net_pnl:+.2f}")
    print(f"\n  Wins:   {', '.join(s['key'] for s in wins)}")
    print(f"  Losses: {', '.join(s['key'] for s in losses)}")
