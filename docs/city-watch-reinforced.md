# Reinforced City Watch

Fase siguiente a la `city watchlist` general.

Produce un readout focalizado para las ciudades prioritarias del siguiente bloque operativo.

Por defecto:

- `Shanghai`
- `Chicago`
- `Seoul`

---

## Objetivo

Tener una vista compacta y accionable por ciudad:

- policy actual
- referencias reales
- snapshot de mercados visibles
- y siguiente paso recomendado

sin tener que releer todas las fases previas.

---

## Comando base

```powershell
python tools/city_watch_reinforced.py
```

### Variante util

```powershell
python tools/city_watch_reinforced.py --cities Shanghai,Chicago,Seoul
```

---

## Salidas

- `data/city_watch_reinforced.json`
- `docs/city_watch_reinforced_latest.md`

---

## Uso recomendado

Esta salida sirve como puente entre research y una futura fase operativa.

En particular ayuda a decidir si el siguiente bloque debe ser:

1. `prepare_shadow_test_design`
2. `watch_live_active_city`
3. `expand_shadow_observability`

sin tocar todavia el core del bot.
