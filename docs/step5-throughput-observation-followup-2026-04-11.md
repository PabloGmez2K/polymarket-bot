# Step 5 Throughput Observation Follow-Up - 2026-04-11

## Objetivo

Intentar una nueva extension read-only de `Step 5` sobre snapshot runtime fresco y preflight limpio, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.

## Preflight

- snapshot refrescado por via canonica read-only: `tools/railway_runtime_snapshot_pull.ps1`
- `data/runtime_import/runtime_import_manifest.json` fresco con `pulled_at=2026-04-11T11:01:40.7730763+00:00`
- `python tools/system_alignment_check.py` -> `ok=7`, `warning=1`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7`, `warning=1`, `error=0`
- `blocking_operational_collision_count=0`

## Resultado

No hay `20` ciclos adicionales nuevos para medir.

El snapshot live esta fresco, pero los artefactos manifestados siguen cerrando en el mismo techo ya usado por la observacion extendida anterior:

- ultimo ciclo disponible: `cycle_number=64`
- ultimo timestamp visible en `cycles_history.jsonl`: `2026-04-11T08:00:38.111156+00:00`
- `shadow_city_tracking.updated_at`: `2026-04-11T08:00:38.036104+00:00`

La ventana de los ultimos `20` ciclos sigue siendo exactamente la misma ya documentada:

- rango: `2026-04-06T16:01:14.997875+00:00` -> `2026-04-11T08:00:38.111156+00:00`
- `candidates_after_prefilters=307`
- `condition_filtered_out=285`
- `candidates_with_edge=4`
- `candidates_selected=4`
- `trades_executed=4`
- `shadow_opportunities_observed=2`

## Lectura Operativa

- no reaparece ningun blocker operacional;
- no aparece ningun bug nuevo de accounting/counters en los artefactos manifestados;
- pero tampoco existe muestra incremental para afirmar que la senal de `auto_canary` se sostiene mas alla del tramo ya auditado.

## Conclusion

La conclusion honesta de esta sesion no es abrir correctness ni policy.

La conclusion correcta es mas simple:

- el sistema sigue alineado para seguir observando;
- la extension pedida no puede completarse todavia porque el runtime manifestado no aporta ciclos nuevos;
- el siguiente paso sigue siendo observacion read-only cuando exista una nueva ventana material de ciclos frescos.
