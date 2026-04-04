"""Muestra todos los registros Chicago con su status en ambos archivos."""
import json

DATES = ["2026-03-26", "2026-03-27", "2026-03-28"]

print("=== trade_lifecycle.json — todos los Chicago ===")
with open('/app/data/trade_lifecycle.json') as f:
    d = json.load(f)
chi = [r for r in d['records'] if r.get('city') == 'Chicago']
print(f"Total Chicago: {len(chi)}")
for r in chi:
    cc = r.get('close_context') or {}
    print(f"  {r.get('date')}  status={r.get('status')}  action={cc.get('close_action', '-')}  reason={cc.get('close_reason', '-')}")

print()
print("=== postmortem.json — todos los Chicago ===")
with open('/app/data/postmortem.json') as f:
    pm = json.load(f)
chi2 = [r for r in pm if r.get('city') == 'Chicago']
print(f"Total Chicago: {len(chi2)}")
for r in chi2:
    print(f"  {r.get('date')}  status={r.get('status')}  action={r.get('close_action', '-')}  reason={r.get('close_reason', '-')}  pnl={r.get('pnl_cash', '-')}")

print()
print("=== city_accuracy Chicago (postmortem closed) ===")
closed = [r for r in chi2 if r.get('status') == 'closed' and r.get('close_action') in ['SELL', 'LOSS_TOTAL', 'RESOLVED_WIN']]
trades = len(closed)
wins = sum(1 for r in closed if (r.get('pnl_cash') or 0) > 0)
pnl = round(sum(r.get('pnl_cash', 0) or 0 for r in closed), 2)
wr = round(wins / trades * 100, 1) if trades > 0 else 0.0
print(f"trades={trades}  wins={wins}  WR={wr}%  PnL={pnl}")
