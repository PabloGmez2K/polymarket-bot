# Phase 5 Visibility Pipeline

Pipeline read-only para ejecutar en un solo comando la fase actual de observabilidad:

1. `settlement_fidelity_probe.py` opcional
2. `city_probe_visibility_tracker.py`
3. `shanghai_shadow_test.py`
4. `chicago_active_benchmark.py`
5. `shanghai_vs_chicago_comparator.py`
6. `phase5_visibility_telegram_alert.py`

---

## Objetivo

Evitar correr manualmente cada pieza de la fase 5 y dejar una salida consistente con:

- visibilidad persistida;
- snapshot actualizado de Shanghai;
- benchmark actualizado de Chicago;
- y comparador final del gap dominante.
- ademas de una alerta Telegram one-shot cuando aparezca una coincidencia nueva `Shanghai + Chicago`.
- y una clasificacion operativa que fuerce un cierre util: `cambio ejecutado`, `patch listo`, `gate definido` o `alarma reescrita`.

---

## Comando base

```powershell
python tools/phase5_visibility_pipeline.py
```

### Variante con refresh del probe

```powershell
python tools/phase5_visibility_pipeline.py --refresh-probe --probe-limit 12
```

---

## Salidas

- `data/phase5_visibility_pipeline.json`
- `docs/phase5_visibility_pipeline_latest.md`

---

## Guardrails

- sigue siendo `read-only`
- no toca `bot.py`
- no cambia policy de ciudades
- si no usas `--refresh-probe`, trabaja sobre el snapshot actual ya existente
