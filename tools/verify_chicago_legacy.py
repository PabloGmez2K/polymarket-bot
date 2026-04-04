"""Verificacion rapida de filas legacy Chicago en produccion."""
import json

print("=== trade_lifecycle.json ===")
with open('/app/data/trade_lifecycle.json') as f:
    d = json.load(f)
DATES = {'2026-03-26', '2026-03-27', '2026-03-28'}
hits = [r for r in d['records'] if r.get('city') == 'Chicago' and r.get('status') == 'open' and r.get('date', '') in DATES]
print(f"Filas legacy open: {len(hits)}")
for r in hits:
    print(f"  - {r.get('date')}  total_amount={r.get('total_amount')}")

print()
print("=== postmortem.json ===")
with open('/app/data/postmortem.json') as f:
    pm = json.load(f)
hits2 = [r for r in pm if r.get('city') == 'Chicago' and r.get('status') == 'open' and r.get('date', '') in DATES]
print(f"Filas legacy open: {len(hits2)}")
for r in hits2:
    print(f"  - {r.get('date')}  total_amount={r.get('total_amount')}")
