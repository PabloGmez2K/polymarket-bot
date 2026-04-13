# Shanghai Shadow Test

Extractor read-only especifico para `Shanghai`.

Su funcion es convertir el diseno de `docs/shanghai-shadow-test-design.md` en un snapshot ejecutable y repetible, sin tocar el core del bot.

---

## Objetivo

Medir, para `Shanghai`:

- senal shadow propia bajo nuestro baseline actual;
- calidad observacional disponible;
- comparabilidad con traders de referencia;
- y accion recomendada siguiente:
  - `stay_shadow`
  - `expand_observability`
  - `prepare_controlled_test`

---

## Inputs

Por defecto consume:

- `data/city_watch_reinforced.json`
- `data/reference_trader_city_market_cross.json`
- `data/directional_trader_enrichment.json`
- `data/settlement_fidelity_probe.json`

Y, si existen, tambien:

- `data/shadow_city_tracking.json`
- `data/audit.json`

Si estos dos ultimos no estan disponibles, la herramienta no falla: deja constancia de que faltan y sigue con el snapshot parcial.

---

## Comando base

```powershell
python tools/shanghai_shadow_test.py
```

### Variante util

```powershell
python tools/shanghai_shadow_test.py --city Shanghai
```

---

## Salidas

- `data/shanghai_shadow_test.json`
- `docs/shanghai_shadow_test_latest.md`

---

## Lectura recomendada

Mirar en este orden:

1. `assessment.next_action`
2. `assessment.rationale`
3. `probe_summary`
4. `shadow_tracking`
5. `audit_summary`

---

## Guardrails

- no toca `bot.py`
- no cambia `MIN_EDGE`
- no cambia policy de ciudades
- no promociona `Shanghai` por si sola
- no mezcla outputs con archivos productivos del runtime

La herramienta solo deja evidencia para decidir la siguiente fase.
