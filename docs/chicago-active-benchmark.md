# Chicago Active Benchmark

Snapshot read-only de `Chicago` como ciudad `active` de referencia.

Su papel no es descubrir una nueva ciudad puente, sino ofrecer un benchmark operativo contra el que comparar `Shanghai` y otras ciudades `shadow`.

---

## Objetivo

Medir si `Chicago` puede funcionar como benchmark creible para:

- seleccion de mercados;
- timing de observacion;
- calidad de referencia trader;
- y contraste contra ciudades `shadow`.

---

## Comando base

```powershell
python tools/chicago_active_benchmark.py
```

---

## Salidas

- `data/chicago_active_benchmark.json`
- `docs/chicago_active_benchmark_latest.md`

---

## Lectura recomendada

1. `benchmark_assessment.next_action`
2. `benchmark_assessment.rationale`
3. `reference_traders`
4. `probe_summary`

---

## Guardrails

- no toca `bot.py`
- no cambia policy
- no decide trades
- solo deja un benchmark operativo reutilizable
