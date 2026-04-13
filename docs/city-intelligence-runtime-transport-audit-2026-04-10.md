# City Intelligence Runtime Transport Audit

**Fecha:** 2026-04-10  
**Alcance:** Railway read-only + prueba local de consumo runtime  
**Estado:** evidencia para decidir siguiente paso LEAN

## Decision

No usar `railway volume attach` para montar `polymarket-bot-volume` en `city-intelligence` como supuesto read-only.

La CLI de Railway muestra `volume attach`, `detach` y `update`, pero no expone una opcion read-only. Cada servicio tiene su propio volumen montado en `/app/data`; adjuntar o mover volumenes sin garantia read-only es demasiado arriesgado para este paso.

La ruta LEAN validada es:

1. leer artefactos desde `polymarket-bot` via SSH en modo read-only;
2. copiarlos localmente a `data/runtime_import/`;
3. ejecutar `city_validation_ledger.py` apuntando a esas copias;
4. revisar semantica antes de automatizar cualquier sync hacia Railway.

## Evidencia Railway

Proyecto:

- `enchanting-respect`
- environment `production`

Servicios:

- `polymarket-bot`
- `city-intelligence`
- `phase5-visibility`

Volumenes:

| Volume | Attached to | Mount path | Used |
| --- | --- | --- | --- |
| `polymarket-bot-volume` | `polymarket-bot` | `/app/data` | ~57MB/500MB |
| `city-intelligence-volume` | `city-intelligence` | `/app/data` | ~50MB/500MB |
| `phase5-visibility-volume` | `phase5-visibility` | `/app/data` | ~50MB/500MB |

Ayuda CLI:

- `railway volume attach` permite `--volume`, `--yes`, `--json`.
- `railway volume update` permite `--mount-path` y `--name`.
- No aparece flag read-only.

Conclusión:

- el multi-mount read-only no queda demostrado;
- no se debe intentar attach del volumen del bot a `city-intelligence` en este bloque.

## Artefactos Runtime En Live

En `polymarket-bot`:

```text
/app/data/audit.json                 exists
/app/data/city_policy_state.json     exists
/app/data/cycles_history.jsonl       exists
/app/data/shadow_city_tracking.json  exists
```

En `city-intelligence`:

```text
/app/data/shadow_city_tracking.json  missing
/app/data/audit.json                 missing
/app/data/city_policy_state.json     missing
/app/data/cycles_history.jsonl       missing
/app/data/city_validation_ledger.json exists
/app/data/city_promotion_gate.json    exists
```

Esto confirma el diagnostico: `city-intelligence` no tiene runtime, aunque el bot si.

## Pull Local Read-only

Se crea `tools/railway_runtime_snapshot_pull.ps1`.

Funcion:

- usa `tools/railway_safe.ps1 ssh -s polymarket-bot`;
- lee con `cat` desde `/app/data`;
- escribe copias locales en `data/runtime_import/`;
- genera `data/runtime_import/runtime_import_manifest.json`.

No escribe en Railway.
No toca `bot.py`.
No toca `city_policy_state.json`.
No modifica volumenes.

Archivos importados:

- `data/runtime_import/shadow_city_tracking.json`
- `data/runtime_import/audit.json`
- `data/runtime_import/city_policy_state.json`

Nota tecnica:

- PowerShell escribio las copias con BOM UTF-8.
- `tools/city_validation_ledger.py` se ajusto para leer JSON con `utf-8-sig`, compatible con UTF-8 normal y BOM.

## Resultado Del Ledger Con Runtime Real

Comando:

```powershell
python tools/city_validation_ledger.py `
  --shadow-tracking data/runtime_import/shadow_city_tracking.json `
  --audit data/runtime_import/audit.json `
  --city-policy-state data/runtime_import/city_policy_state.json `
  --json-output data/runtime_import/city_validation_ledger.runtime_import.json `
  --md-output docs/city_validation_ledger_runtime_import.md
```

Resultado:

- `runtime_inputs_status=available`
- `n_cities=22`
- `actionable=1`
- `building=4`
- `insufficient=17`
- `bottleneck_counts`:
  - `canary_confirmation=1`
  - `market_visibility=4`
  - `source_fidelity=3`
  - `trader_discovery=14`

## Shanghai

Con runtime importado, Shanghai aparece en el ledger:

- `policy_mode=shadow`
- `evidence_status=actionable`
- `recommendation=candidate_for_canary_validation`
- `bottleneck=canary_confirmation`
- `shadow_edge_hits=19`
- `shadow_cycles_seen=30`
- `shadow_best_edge_pct=38.7`
- `resolved_directional_count=0`
- `noaa_rows=0`

Lectura:

- El transporte de `shadow_city_tracking.json` funciona: el ledger ya ve los agregados runtime reales.
- La semantica de policy sigue mal: `policy_mode=shadow` viene del cross analitico, no de `city_policy_state.json`.
- Aunque `city_policy_state.json` se importa, el ledger aun no lo parsea para producir `runtime_policy_mode`.
- Por tanto, el siguiente paso no es mover Shanghai ni tocar trading; es anadir lectura read-only de `city_policy_state.json` y separar `cross_policy_mode` de `runtime_policy_mode`.

## Siguiente Paso LEAN Recomendado

Antes de automatizar sync en Railway:

1. hacer que `city_validation_ledger.py` lea `city_policy_state.json` en modo read-only;
2. exponer por ciudad:
   - `cross_policy_mode`;
   - `runtime_policy_mode`;
   - `policy_drift`;
3. hacer que Shanghai caiga en una categoria de auditoria posterior a canary, no en `candidate_for_canary_validation`.

No tocar:

- `bot.py`;
- allowlists;
- `city_policy_state.json`;
- thresholds;
- trading;
- volumenes Railway.

## Pregunta Para Opus

El transporte read-only por pull local prueba que el ledger puede consumir runtime real. Pero antes de automatizarlo en Railway, el primer valor semantico que falta es leer `city_policy_state.json`.

Pregunta:

- ¿GO para implementar `runtime_policy_mode` read-only en el ledger como siguiente paso LEAN?
- ¿O primero prefieres convertir el pull local en sync operacional hacia el volumen de `city-intelligence`?

