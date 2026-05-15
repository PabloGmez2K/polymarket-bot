# Source Onboarding Scanner — Design (Fase A)

> **Pieza de City Intelligence v2.** Ver diseño completo: `docs/city_intelligence_v2_design.md`.

## Qué hace

Detecta ciudades **fuera del flujo runtime** que muestran señal externa fuerte (traders,
blocked_signals, shadow leak) y las prioriza para auditoría manual de fuente.

**No emite BUY/SELL/SKIP. No cambia city modes. No auto-promueve. No Telegram. No Railway.**

## Universo

Solo ciudades **no presentes** en: `ACTIVE` | `CANARY` | `BLOCKED` | `auto_canary` |
`auto_shadow` | `shadow_tracking (cycles ≥ 10)` | `city_lifecycle_overrides.keys()`.

## Inputs (todos CLI, read-only)

| Flag | Default |
|---|---|
| `--signals-crosscheck` | `data/runtime_import_derived/signals_crosscheck.jsonl` |
| `--blocked-resolutions` | `data/runtime_import_derived/blocked_signals_resolutions.jsonl` |
| `--shadow-tracking` | `data/runtime_import/shadow_city_tracking.json` |
| `--policy-env` | `data/runtime_import/policy_env_snapshot.json` |
| `--policy-state` | `data/runtime_import/city_policy_state.json` |
| `--overrides` | `data/city_lifecycle_overrides.json` |
| `--traders-report` | `data/intelligence/traders_operational_questions_report.json` |
| `--json-output` | `data/source_onboarding.json` |
| `--md-output` | `docs/source_onboarding_latest.md` |

`RESOLUTION_ICAO` se carga via AST parse de `bot.py` (no import completo).
Si falla: `degraded=true`, `source_feasibility=unknown`, sin `SOURCE_BLOCKED`.
`OBSERVED_AUDIT_CITIES` tambien se lee via AST para excluir ciudades ya dentro del flujo observado.

## Estados Fase A v0.2

El scanner separa readiness de fuente, observacion y operacion. `primary_status`
resume el cuello principal, pero cada ciudad tambien expone:

- `trader_evidence_status`
- `shadow_evidence_status`
- `source_discovery_status`
- `mapping_status`
- `source_audit_status`
- `observation_pipeline_status`
- `missing_inputs`
- `blocking_reasons`
- `next_best_action`
- `source_discovery_recommended`
- `gamma_check_recommended`
- `source_audit_recommended`
- `observation_review_recommended`
- `opus_review_required`
- `operational_action`

`state` y `recommended_state` se mantienen como alias de `primary_status` para
compatibilidad con consumidores antiguos.

| Estado | Significado |
|---|---|
| `WAITING_EVIDENCE` | falta evidencia trader/blocked suficiente |
| `MARKET_IDS_MISSING` | faltan slugs, market_ids o condition_ids para descubrir fuente |
| `SOURCE_TEXT_MISSING` | hay identificadores, pero falta texto/reglas de fuente |
| `MAPPING_MISSING` | no hay mapping interno defendible en `RESOLUTION_ICAO` |
| `SOURCE_DISCOVERY_READY` | hay identificadores para descubrir fuente, sin accion runtime |
| `SOURCE_AUDIT_POSSIBLE` | hay mapping e identificadores suficientes para auditar fuente |
| `READY_FOR_HUMAN_SOURCE_AUDIT` | fuente/mapping/lista de evidencias lista para revision humana |
| `SOURCE_CONFIRMED_WAITING_SHADOW` | fuente confirmada, falta observacion shadow suficiente |
| `OBSERVATION_WAITING_EVIDENCE` | fuente/audit posible, pero shadow/observacion aun insuficiente |
| `SOURCE_AMBIGUOUS` | reglas/fuente externas no permiten una lectura unica |
| `SOURCE_MISMATCH` | fuente externa contradice el mapping interno |
| `NEEDS_OPUS_REVIEW` | decision semantica delicada antes de patch operativo |
| `RANGE_ONLY_NOT_OPERABLE` | ≥ 70% señales son range |
| `SOURCE_BLOCKED` | reservado para bloqueo fuerte real: fuente incompatible, settlement ambiguo, mismatch claro o mapping/fuente indefendible |

`SOURCE_BLOCKED` no se usa para una ciudad que simplemente no existe en
`RESOLUTION_ICAO`; ese caso es `MAPPING_MISSING`.

## Outputs

- `data/source_onboarding.json` — JSON estructurado con `log_only: true`
- `docs/source_onboarding_latest.md` — Markdown para revisión humana

Ambos están en `.gitignore` (regenerables).

## Prohibiciones

No Telegram, no Railway, no DB, no `/app/data`, no env vars, no BUY/SELL/SKIP,
no city modes, no BANKROLL, no Fase C, no modificar `city_lifecycle_review_monitor.py`.
