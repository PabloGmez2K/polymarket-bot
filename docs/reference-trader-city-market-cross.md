# Reference Trader x City x Market Cross

Fase 3 del plan operativo.

Cruza tres capas ya construidas:

- referencias reales de traders (`directional_trader_enrichment.json`)
- snapshot actual de mercados (`settlement_fidelity_probe.json`)
- policy local del bot (`ACTIVE`, `CANARY`, `BLOCKED`, `OBSERVED`)

---

## Objetivo

Responder una pregunta operativa:

**donde coinciden traders de referencia, mercados activos y policy del bot, y donde hay mismatch util para research o expansion futura?**

---

## Comando base

```powershell
python tools/reference_trader_city_market_cross.py
```

---

## Salidas

Por defecto genera:

- `data/reference_trader_city_market_cross.json`
- `docs/reference_trader_city_market_cross_latest.md`

---

## Que prioriza

La salida ordena:

1. ciudades con mas referencias reales;
2. ciudades con mercados actuales visibles en el probe;
3. ciudades mas cercanas a la policy del bot (`active`, `shadow`, `blocked`).

---

## Como leerla

### `city_rows`

Para cada ciudad:

- `policy_mode`
- `priority_score`
- `reference_traders`
- `reference_quality_counts`
- `current_probe_markets`
- `probe_conditions`

### `trader_rows`

Para cada trader enriquecido:

- `reference_quality`
- `closed_win_rate`
- `closed_pnl`
- `dominant_city`
- `policy_modes_seen`
- `cities_in_probe_now`

---

## Uso recomendado

Si una ciudad sale alta en prioridad y esta en `active` o `shadow`, suele ser buena candidata para:

- observabilidad adicional;
- seguimiento de wallets;
- o test controlado posterior.

Si una ciudad sale alta pero esta en `blocked`, normalmente la lectura correcta no es “operarla ya”, sino revisar si el bloqueo sigue siendo estructural o solo historico.
