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

## Estados Fase A

| Estado | Significado |
|---|---|
| `READY_FOR_SOURCE_AUDIT` | score ≥ 1.5 + ICAO disponible |
| `WAITING_EVIDENCE` | score ≥ 0.5 (o degraded) |
| `RANGE_ONLY_NOT_OPERABLE` | ≥ 70% señales son range |
| `SOURCE_BLOCKED` | RESOLUTION_ICAO cargado + ciudad sin ICAO |

## Outputs

- `data/source_onboarding.json` — JSON estructurado con `log_only: true`
- `docs/source_onboarding_latest.md` — Markdown para revisión humana

Ambos están en `.gitignore` (regenerables).

## Prohibiciones

No Telegram, no Railway, no DB, no `/app/data`, no env vars, no BUY/SELL/SKIP,
no city modes, no BANKROLL, no Fase C, no modificar `city_lifecycle_review_monitor.py`.
