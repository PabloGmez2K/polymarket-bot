# Directional Trader Enrichment

Fase 2.5 del plan operativo.

Toma la shortlist del `Directional Trader Census` y la enriquece con:

- `closed positions`
- `win rate`
- `cash PnL`
- actividad direccional activa

para separar traders solo activos de traders que merecen convertirse en referencia real.

---

## Objetivo

Responder:

**de la shortlist direccional comparable, cuales parecen realmente buenos y cuales solo estan presentes?**

---

## Comando base

```powershell
python tools/directional_trader_enrichment.py
```

### Variantes utiles

```powershell
python tools/directional_trader_enrichment.py --top 10
python tools/directional_trader_enrichment.py --closed-limit 150
python tools/directional_trader_enrichment.py --input data/directional_trader_census.json
```

---

## Salidas

Por defecto genera:

- `data/directional_trader_enrichment.json`
- `docs/directional_trader_enrichment_latest.md`

---

## Campos clave

Por trader:

- `reference_quality`
- `closed_summary.win_rate`
- `closed_summary.total_closed_pnl`
- `closed_summary.n_closed_directional_weather`
- `active_summary.n_active_directional`
- `census_snapshot`

---

## Interpretacion de `reference_quality`

- `high_priority_reference`
  - suficiente muestra direccional cerrada + WR >= 55 + PnL > 0
- `candidate_reference`
  - PnL positivo y WR >= 50, pero con menos conviccion
- `active_but_unproven`
  - activo ahora, pero sin evidencia historica suficiente
- `low_signal`
  - poco util como referencia por ahora

---

## Limites honestos

1. Usa el endpoint de posiciones cerradas del ecosistema, no una reconstruccion on-chain completa.
2. No prueba causalidad; solo prioriza referencia util.
3. No detecta si el trader gana por timing, forecast o estructura por si solo.

---

## Siguiente paso sugerido

Cuando esta fase ya este poblada:

1. cruzar `reference_quality` con nuestras ciudades/markets;
2. decidir si conviene observar:
   - traders concretos,
   - ciudades concretas,
   - o patrones de entrada/salida.
