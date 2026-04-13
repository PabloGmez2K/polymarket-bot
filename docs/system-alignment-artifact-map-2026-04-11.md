# System Alignment Artifact Map - 2026-04-11

## Objetivo

Responder rapido que artefacto mirar segun la pregunta operativa.

## Fuente De Verdad Por Pregunta

### 1. Que snapshot runtime es valido

- JSON: `data/runtime_import/runtime_import_manifest.json`
- Check: `python tools/system_alignment_check.py`
- Lectura humana: `docs/system_alignment_check_latest.md`

### 2. Que ciudad esta en que modo efectivo

- JSON: `data/runtime_policy_effective_view.json`
- Lectura humana: `docs/runtime_policy_effective_view_latest.md`
- Regla: citar `effective_mode`, no `ACTIVE_TRADING_CITIES` a pelo

### 3. Que significa cada etapa del funnel

- Doc canonico: `docs/metrics-funnel-naming.md`
- Runtime bruto: `data/runtime_import/decisions.log`
- Resumen por ciclo: `data/runtime_import/cycles_history.jsonl`
- Regla: `markets_evaluated` es alias legacy de `candidates_after_prefilters`

### 4. Si el sistema esta alineado antes de decidir algo

- Comando: `python tools/system_alignment_check.py`
- JSON: `data/system_alignment_check.json`
- Markdown: `docs/system_alignment_check_latest.md`

### 4b. Si una sesion esta autorizada a discutir un cambio operacional

- Comando: `python tools/system_alignment_check.py --decision-mode operational`
- Markdown: `docs/system_alignment_check_operational_latest.md`
- JSON: `data/system_alignment_check_operational.json`
- Reglas: `docs/decision-preflight-rules-2026-04-11.md`
- Contrato funnel/bot: `docs/bot-funnel-counter-contract-2026-04-11.md`

### 5. Que targets usa city-intelligence y de donde salen

- JSON: `data/city_intelligence_pipeline.json`
- Markdown: `docs/city_intelligence_pipeline_latest.md`
- Regla:
  - `runtime_derived_targets` salen de `runtime_policy_effective_view`
  - `exploratory_targets` son extras explicitos

### 6. Si el throughput reciente esta estrecho y por que

- Doc de lectura actual: `docs/step5-throughput-observation-2026-04-11.md`
- Inputs:
  - `data/runtime_import/cycles_history.jsonl`
  - `data/runtime_import/skip_log.jsonl`
  - `data/runtime_import/postmortem.json`
  - `data/runtime_import/shadow_city_tracking.json`

### 7. Que ciudades shadow merecen vigilancia real

- Doc de lectura actual: `docs/shadow-opportunity-shortlist-2026-04-11.md`
- Inputs:
  - `data/runtime_import/shadow_city_tracking.json`
  - `data/runtime_import_derived/city_validation_ledger.runtime_import.json`
  - `data/runtime_import/skip_log.jsonl`

## Regla De Lectura Minima

Para una sesion normal de esta fase no hace falta abrir todo.

Orden corto recomendado:

1. `AGENTS.md`
2. bloque vigente de `CONTEXTO.md`
3. `python tools/system_alignment_check.py`
4. `docs/system_alignment_check_latest.md`
5. el artefacto concreto que responde la pregunta de la sesion

## Regla De Escalado

Si la pregunta no puede responderse con este mapa, puede haber:

- una contradiccion nueva de arquitectura;
- una laguna real del sistema;
- o una tarea que ya no pertenece a la fase de alignment sino a policy/throughput/correctness.
