# System Alignment LEAN Roadmap - 2026-04-10

## Objetivo

Estandarizar el sistema antes de aumentar throughput.

La meta no es abrir mas trades ya. La meta es que `polymarket-bot`, `city-intelligence`, docs, outputs JSON, prompts y servicios Railway digan la misma verdad verificable sobre:

- que archivos runtime son input valido;
- que ciudad esta en que modo efectivo;
- que significa cada metrica del funnel;
- que capa puede escribir y cual solo puede leer;
- que checks deben pasar antes de una decision operacional.

## Resultado Esperado Al Completar El Plan

Al terminar este plan tendremos:

1. Un snapshot runtime atomico y confiable.
2. Un directorio de inputs runtime limpio, sin mezclar outputs derivados.
3. Una vista unica read-only de policy efectiva por ciudad.
4. Un glosario canonico del funnel de mercados/trades.
5. Un `system_alignment_check.py` que diga en un comando si el sistema esta alineado.
6. Una rutina pre-decision para que futuras sesiones no dependan de memoria humana ni prompts largos.
7. La capacidad de decidir throughput con evidencia real, no con artefactos desfasados.

## Estado Actual

Estado al `2026-04-11`:

- Step 1: cerrado
- Step 2: cerrado
- Step 3: cerrado
- Step 4: cerrado
- Target tagging complementario: cerrado
- Step 5: primera observacion read-only completada
- Phase 6 mini: decision preflight hardening
- Phase 6.5 mini: collision severity hardening

Artefactos de cierre de fase:

- `docs/system-alignment-phase-closeout-2026-04-11.md`
- `docs/system-alignment-artifact-map-2026-04-11.md`
- `docs/system-alignment-session-checklist-2026-04-11.md`
- `docs/step5-throughput-observation-2026-04-11.md`
- `docs/shadow-opportunity-shortlist-2026-04-11.md`
- `docs/bot-funnel-counter-contract-2026-04-11.md`
- `docs/decision-preflight-rules-2026-04-11.md`
- `docs/phase6-5-collision-severity-hardening-2026-04-11.md`

## Fuente Canonica

- Review de Opus: `docs/opus-review-throughput-alignment-2026-04-10.md`
- Auditoria Codex: `docs/throughput-alignment-audit-2026-04-10.md`
- Prompt usado: `docs/claude-opus-prompt-throughput-alignment-review-2026-04-10.md`
- Contexto resumido: bloque Sesion 130 en `CONTEXTO.md`

## Orden LEAN

### Step 1 - Manifest Runtime Atomico Y Completo

Objetivo:

`data/runtime_import/` debe ser bijectivo con `runtime_import_manifest.json`: todo archivo en el directorio esta listado en manifest, y todo archivo listado existe.

Archivos probables:

- `tools/railway_runtime_snapshot_pull.ps1`
- `tools/city_validation_ledger.py`
- `data/runtime_import/`
- nuevo directorio sugerido: `data/runtime_import_derived/`

No toca:

- `bot.py`
- `city_policy_state.json`
- thresholds
- allowlists
- Railway volumes
- trading core

Checks:

- Pull normal deja manifest completo.
- Si falta un archivo listado, ledger devuelve `runtime_inputs_status=manifest_drift`.
- Si sobra un archivo no listado, ledger devuelve `runtime_inputs_status=manifest_drift`.
- Outputs derivados no viven en `data/runtime_import/`.

Stop/go:

- GO a Step 2 solo si manifest y directorio son bijectivos.

### Step 2 - Runtime Policy Effective View

Objetivo:

Crear una vista read-only unica que resuelva env vars + `city_policy_state.json` en una respuesta efectiva por ciudad.

Archivos probables:

- nuevo `tools/runtime_policy_effective_view.py`
- nuevo `data/runtime_policy_effective_view.json`
- nuevo `docs/runtime_policy_effective_view_latest.md`

Campos minimos:

- `city`
- `env_declared_mode`
- `runtime_policy_mode`
- `effective_mode`
- `collision_flag`
- `source_of_truth`
- `rationale`

Validacion esperada con estado actual:

- Dallas: `env_declared_mode=active`, `runtime_policy_mode=auto_shadow`, `effective_mode=shadow`, `collision_flag=true`.
- Atlanta, Munich, New York City, Seoul, Shanghai, Tokyo: `effective_mode=canary`.
- Cero ciudades `active` efectivas.

Stop/go:

- GO a Step 3 solo si humanos/docs/prompts dejan de citar `ACTIVE_TRADING_CITIES` como verdad efectiva sin pasar por esta vista.

### Step 3 - Naming Canonico Del Funnel

Objetivo:

Eliminar la confusion entre mercados brutos y candidatos post-filtros.

Archivo nuevo:

- `docs/metrics-funnel-naming.md`

Nombres canonicos:

- `raw_markets_fetched`: mercados brutos descargados de Polymarket.
- `candidates_after_prefilters`: candidatos tras fecha/precio/zona/bloqueo/liquidez. Alias legacy: `markets_evaluated`.
- `condition_filtered_out`: mercados descartados por `ALLOWED_CONDITIONS`.
- `candidates_with_edge`: candidatos con edge suficiente antes de seleccion final.
- `shadow_opportunities_observed`: oportunidades con edge observadas pero no operables por modo/allowlist.
- `candidates_selected`: oportunidades seleccionadas para intentar trade.
- `trades_executed`: compras reales ejecutadas.
- `blocked_city_count`, `fuera_allowlist_count`, `date_out_of_range_count`, `price_out_of_range_count`: subrazones.

No toca:

- counters internos de `bot.py` en esta fase.

Stop/go:

- GO a Step 4 cuando docs/alerts/summaries relevantes usen nombres canonicos o mapeo legacy explicito.

### Step 4 - System Alignment Check

Objetivo:

Un solo comando read-only para validar contratos antes de cualquier decision operacional.

Archivo nuevo:

- `tools/system_alignment_check.py`

Checks minimos:

1. Manifest runtime completo y fresco.
2. No hay archivos ambiente en `data/runtime_import/`.
3. `runtime_policy_effective_view` existe y esta fresco.
4. Colisiones env/runtime listadas explicitamente.
5. Divergencias cross/runtime listadas explicitamente.
6. Targets de `city-intelligence` separados o etiquetados como runtime-derived/exploratory.
7. Docs latest no estan mas stale que sus JSON fuente.
8. No quedan usos ambiguos de `markets_evaluated` en docs sin alias canonico.

Comportamiento:

- Exit code `0`: alineado.
- Exit code non-zero: no tomar decisiones de throughput.

Stop/go:

- GO a Step 5 solo si el check pasa limpio o si sus warnings estan documentados como aceptados para esa decision.

### Step 5 - Observar Throughput Honestamente

Objetivo:

Medir `10-20` ciclos con nombres canonicos y snapshot manifestado antes de tocar policy.

Inputs:

- `cycles_history.jsonl`
- `skip_log.jsonl`
- `shadow_city_tracking.json`
- `city_policy_state.json`
- `postmortem.json`
- todos desde snapshot manifestado, no archivos sueltos.

Salida esperada:

- Markdown diario/semanal con funnel por ciclo.
- Lista de ciudades con shadow opportunities reales.
- Diagnostico de si Chicago fue senal aislada, bug de accounting o candidata que la regla auto-canary deberia captar.

Stop/go:

- Si aparece bug de accounting, arreglar correctness antes de policy.
- Si no hay bug, dejar trabajar reglas auto-canary.
- Solo considerar throughput despues de evidencia suficiente.

### Phase 6 Mini - Decision Preflight Hardening

Objetivo:

Endurecer `system_alignment_check.py` para que no solo lea artefactos, sino que tambien bloquee decisiones operacionales con drift semantico o frescura insuficiente.

Archivos probables:

- `tools/system_alignment_check.py`
- `docs/bot-funnel-counter-contract-2026-04-11.md`
- `docs/decision-preflight-rules-2026-04-11.md`

No toca:

- `bot.py`
- `city_policy_state.json`
- thresholds
- allowlists
- bankroll
- `exact/range`
- trading core

Validacion esperada:

- `python tools/system_alignment_check.py` sigue sirviendo para `observe`.
- `python tools/system_alignment_check.py --decision-mode operational` falla si el effective view esta fuera del SLO o si `collision_count > 5`.
- prompts y docs canonicos no citan `ACTIVE_TRADING_CITIES` como verdad efectiva ni `markets_evaluated` sin alias canonico.
- existe un contrato explicito entre counters legacy de `bot.py` y nombres canonicos del funnel.

Stop/go:

- GO a discusiones futuras de throughput/policy solo si la sesion puede pasar por este preflight endurecido sin reabrir los contratos base.

### Phase 6.5 Mini - Collision Severity Hardening

Objetivo:

Separar ruido visible, drift documentado y blockers operativos reales para que
el preflight `operational` no dependa de un contador ciego.

Archivos probables:

- `tools/runtime_policy_effective_view.py`
- `tools/reference_trader_city_market_cross.py`
- `tools/system_alignment_check.py`
- `docs/decision-preflight-rules-2026-04-11.md`
- `docs/phase6-5-collision-severity-hardening-2026-04-11.md`

No toca:

- `bot.py`
- `city_policy_state.json`
- policy live
- thresholds
- allowlists
- bankroll
- `exact/range`

Validacion esperada:

- `runtime_policy_effective_view` clasifica:
  - `collision_noise`
  - `documented_drift`
  - `blocking_operational_collision`
- `reference_trader_city_market_cross` deja de arrastrar claims legacy incompatibles cuando existe la effective view.
- `system_alignment_check.py --decision-mode operational` bloquea por blockers reales, no por el total bruto de colisiones.

Stop/go:

- GO a una futura discusion operacional solo si el preflight deja de tener `blocking_operational_collision`.

## Checks Antes De Cualquier Cambio Operacional

Ejecutar en este orden:

1. `python verify_before_deploy.py`
2. pull runtime manifestado o confirmar snapshot fresco
3. `python tools/system_alignment_check.py`
4. revisar `runtime_policy_effective_view_latest.md`
5. revisar funnel con nombres canonicos
6. confirmar que `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` no contradicen el estado
7. si la sesion quiere tocar policy/throughput/correctness, repetir `python tools/system_alignment_check.py --decision-mode operational`

## Como Empezar Una Sesion Nueva Sin Friccion

Mensaje sugerido:

```text
Lee AGENTS.md, el bloque Sesion 132 de CONTEXTO.md, docs/opus-review-throughput-alignment-2026-04-10.md y docs/system-alignment-lean-roadmap-2026-04-10.md.

No tocar bot.py, no escribir city_policy_state.json, no cambiar thresholds ni allowlists.

Primero corre:
- python tools/system_alignment_check.py

Luego revisa:
- docs/system_alignment_check_latest.md
- docs/runtime_policy_effective_view_latest.md
- docs/metrics-funnel-naming.md

Empieza por el warning restante de targets: separar `runtime_derived_targets` y `exploratory_targets` en city-intelligence, dejarlo reflejado en JSON/docs/checks y mantener todo read-only respecto a polymarket-bot.
```

## Que No Implementar Todavia

- No Chicago manual canary.
- No Dallas active.
- No `exact/range`.
- No subir bankroll.
- No tocar `bot.py`.
- No escribir `city_policy_state.json`.
- No automatizar Railway sync roto.
- No montar volumen de `polymarket-bot` en `city-intelligence`.
- No matar phase5.
- No cambiar `MIN_EDGE`, thresholds ni allowlists.
