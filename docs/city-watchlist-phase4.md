# City Watchlist - Phase 4

Fase 4 del plan operativo.

Convierte las fases anteriores en una salida operativa por ciudad:

- `prepare_test`
- `watch_active`
- `review_block_reason`
- `observe_closely`
- `background_watch`

---

## Objetivo

Responder:

**que ciudades merecen atencion inmediata y con que tipo de accion, sin tocar todavia el core del bot?**

---

## Comando base

```powershell
python tools/city_watchlist_phase4.py
```

---

## Salidas

Por defecto genera:

- `data/city_watchlist_phase4.json`
- `docs/city_watchlist_phase4_latest.md`

---

## Significado de cada accion

- `prepare_test`
  - ciudad puente muy fuerte: referencias reales + mercados visibles + policy favorable para observacion.
- `watch_active`
  - ciudad ya operativa donde aparecen traders de referencia; buena candidata para vigilancia reforzada.
- `review_block_reason`
  - ciudad con mucha señal externa pero bloqueada localmente; revisar bloqueo antes de pensar en trading.
- `observe_closely`
  - ciudad prometedora para seguimiento, aun sin prioridad inmediata.
- `background_watch`
  - mantener en radar, sin accion inmediata.

---

## Uso recomendado

La watchlist no cambia la policy por si sola.

Sirve para decidir el siguiente bloque:

1. observabilidad reforzada por ciudad;
2. revision de policy;
3. test controlado futuro;
4. o simplemente seguimiento.
