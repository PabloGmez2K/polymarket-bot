# Opus Review - Throughput Alignment - 2026-04-10

## Veredicto

`GO WITH CHANGES`, pero no los cambios inicialmente sugeridos.

La lectura adversarial de Opus es que el problema no debe enmarcarse como "tenemos poco throughput, abramos una canary o ampliemos scope". El sistema no esta estrecho principalmente por throughput, sino por estado confiable. No se puede medir honestamente throughput mientras el cableado no diga de forma univoca:

- que ciudad esta en que modo efectivo;
- que archivos pertenecen al snapshot runtime;
- que metricas del funnel significan raw scan vs post-filtro;
- que capa es fuente de verdad y cual es solo analitica.

Prioridad de problemas:

1. `cableado / contracts`
2. `observabilidad / naming del funnel`
3. `throughput`

No invertir ese orden.

## Findings

1. El diagnostico "no estamos rotos, estamos demasiado estrechos" es solo medio correcto.

   Es cierto que las ultimas 3 operaciones canary cerraron ganadoras, no hay bug obvio de ejecucion ni pricing, y el funnel tiene datos. Pero la estrechez es en gran parte deliberada: `condition_filtered=142` contra solo `below_min_edge=8`. Como `exact/range` esta vetado, el principal techo de throughput viene de una restriccion estructural que no se debe tocar ahora.

2. Dallas esta correctamente en `auto_shadow`.

   `ACTIVE_TRADING_CITIES=Dallas` es el drift, no el runtime. `city_policy_state.json` tiene Dallas en `auto_shadow_cities` con `17` trades, `WR 11.8%` y `PnL -$1.60`. La regla de salida esta protegiendo al sistema. No forzar Dallas active.

3. Las 3 wins recientes son muestra insuficiente.

   `3/3` con `+$1.31` indica que el pipeline canary produce operaciones validas, pero no prueba edge real. Con p=0.5, `3/3` tiene probabilidad `12.5%`. Uso correcto de la senal: no romper el pipeline, seguir midiendo.

4. Chicago no debe convertirse manualmente en canary por un solo hit.

   El edge shadow de Chicago (`35.09%`) es `n=1`. Si Chicago tiene alpha real, la regla de auto-promocion deberia captarlo en ciclos posteriores. Si no lo capta porque el hit `fuera_allowlist` no se contabiliza bien, eso es un bug de shadow accounting que hay que auditar, no una razon para saltarse la regla.

5. El manifest runtime es incompleto y no representa el directorio.

   `runtime_import_manifest.json` lista 3 archivos, pero `data/runtime_import/` contiene mas artefactos, incluyendo outputs derivados y pulls manuales ampliados. Esto bloquea automatizar transporte: no se puede tener una integracion basada en "lee este directorio" cuando el manifest no describe el directorio.

6. `city-intelligence` mezcla inputs y outputs derivados.

   Tener `city_validation_ledger.runtime_import.json` y `city_promotion_gate.runtime_import.json` dentro del mismo directorio que inputs runtime rompe el contrato. Los inputs manifestados deben vivir separados de outputs derivados.

7. Los targets live de `city-intelligence` no derivan del runtime.

   Targets live: `Chicago,Dallas,Seattle,Munich,Madrid`. Runtime canaries: `Atlanta,Munich,New York City,Seoul,Shanghai,Tokyo`. Solo `Munich` coincide. Hay que separar `runtime_derived_targets` de `exploratory_targets`.

8. `phase5-visibility` no debe ser cuarta fuente de verdad.

   Mantenerlo vivo por ahora, pero como lector experimental con write surface limitado a su propio volumen. Migrar su alerta one-shot a `city-intelligence` antes de archivarlo funcionalmente.

## Required Before Throughput Change

- Manifest runtime atomico, completo y con staleness guard.
- Ningun archivo ambiente en `data/runtime_import/` fuera del manifest.
- Ningun archivo listado en el manifest ausente del disco.
- Pull atomico: escribir a tmp, completar, escribir manifest al final y renombrar.
- `runtime_policy_effective_view.json` read-only que resuelva env vars + `city_policy_state.json` en una sola vista por ciudad.
- `system_alignment_check.py` que falle con exit non-zero si cualquier contrato se rompe.
- Reauditar el caso Chicago: `fuera_allowlist` en una fila shadow con edge puede indicar bug de accounting.

## Required Before System Standardization

- Documento unico de fuente de verdad por artefacto.
- Separar inputs runtime manifestados de outputs derivados.
- Congelar phase5 como lector separado, sin write surface compartido.

## Safe Minimal Next Step

Paso 1: arreglar contrato de manifest.

Un PR read-only, sin `bot.py`, sin writes a `city_policy_state.json`, sin thresholds ni throughput:

1. `tools/railway_runtime_snapshot_pull.ps1` escribe los archivos de snapshot de forma atomica y el manifest al final.
2. El pull no debe considerar success si el directorio no queda bijectivo con el manifest.
3. `tools/city_validation_ledger.py` debe extender su staleness guard a `manifest_drift`.
4. Mover outputs derivados fuera de `data/runtime_import/`, por ejemplo a `data/runtime_import_derived/`.

## LEAN Roadmap

### Step 1 - Manifest atomicity and completeness

Objetivo: `data/runtime_import/` debe ser bijectivo con su manifest.

Afecta:

- `tools/railway_runtime_snapshot_pull.ps1`
- `tools/city_validation_ledger.py`
- higiene de `data/runtime_import/`

No toca:

- `bot.py`
- `city_policy_state.json`
- trading
- Railway volumes
- thresholds
- allowlist

Validacion:

- pull normal: manifest lista exactamente los archivos en disco;
- borrar un archivo listado: ledger reporta `manifest_drift`;
- agregar un archivo manual: ledger reporta `manifest_drift`.

### Step 2 - Runtime policy effective view

Objetivo: una vista read-only unica para responder que ciudades estan activas/canary/shadow/blocked efectivamente.

Nuevo:

- `tools/runtime_policy_effective_view.py`
- `data/runtime_policy_effective_view.json`
- `docs/runtime_policy_effective_view_latest.md`

Validacion esperada hoy:

- Dallas: `env_declared=active`, `runtime_mode=auto_shadow`, `effective_mode=auto_shadow`, `collision_flag=true`.
- Atlanta/Munich/NYC/Seoul/Shanghai/Tokyo: `effective_mode=auto_canary`.
- Cero ciudades `active` efectivas.

### Step 3 - Funnel naming contract

Objetivo: eliminar la ambiguedad `markets_evaluated = raw scan`.

Nuevo:

- `docs/metrics-funnel-naming.md`

Nombres canonicos sugeridos:

- `raw_markets_fetched`
- `candidates_after_prefilters` alias legacy `markets_evaluated`
- `candidates_with_edge`
- `candidates_selected`
- `trades_executed`
- `condition_filtered_out`
- `shadow_opportunities_observed`
- `blocked_city_count`
- `fuera_allowlist_count`

No tocar counters internos de `bot.py` todavia; traducir en docs/alertas/summaries.

### Step 4 - System alignment check

Objetivo: un pre-flight obligatorio antes de cualquier decision operacional.

Nuevo:

- `tools/system_alignment_check.py`

Checks minimos:

- manifest completeness/freshness;
- effective policy view fresh;
- city policy collisions;
- cross/runtime divergence;
- overlap targets `city-intelligence` vs runtime;
- archivos ambiente fuera del manifest;
- naming consistency en docs;
- staleness de docs latest vs JSON.

Debe fallar hoy y listar problemas legibles. Despues de corregirlos, debe pasar limpio.

### Step 5 - Observe throughput honestly

Objetivo: medir el funnel con nombres canonicos durante `10-20` ciclos antes de tocar policy.

Si Chicago revela bug de shadow accounting, el siguiente ticket es correctness fix. Si no, no se toca throughput y se deja trabajar a la regla auto-canary.

## Architecture Answers

- Contrato bot -> city-intelligence: bundle manifestado, atomico, timestamped, read-only. `city-intelligence` solo lee snapshots manifestados y falla cerrado ante drift.
- No shared volume entre servicios para runtime.
- No ambient file reads.
- Outputs derivados nunca van en el directorio de inputs runtime.
- `ACTIVE_TRADING_CITIES` no debe citarse como verdad operativa; debe pasar por effective view.
- Targets de `city-intelligence` deben separarse en `runtime_derived_targets` y `exploratory_targets`.
- `phase5-visibility` queda como lector experimental hasta migrar alerta y archivar su rol decisional.

## Do Not Implement Yet

- No manual canary para Chicago.
- No reactivar Dallas.
- No tocar `exact/range`.
- No subir bankroll.
- No automatizar Railway pull/sync a `city-intelligence` hasta arreglar manifest + alignment check.
- No montar volumen de `polymarket-bot` en `city-intelligence`.
- No tocar `bot.py`.
- No matar phase5.
- No cambiar thresholds, `MIN_EDGE` ni allowlist.
- No enviar nuevos prompts operacionales a Opus sin adjuntar output de `system_alignment_check.py` cuando exista.

## One-Line Summary

La intuicion de que el sistema esta estrecho es correcta, pero no se arregla abriendo throughput. Primero hay que estandarizar el cableado: manifest bijectivo, vista efectiva de policy y check de alineacion. Despues se deja trabajar a la regla auto-canary.

