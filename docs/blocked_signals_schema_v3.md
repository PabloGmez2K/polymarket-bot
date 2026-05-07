# blocked_signals schema v3

Estado: contrato. No incluye patch ni implementación. No desbloquea señales por sí mismo.

## 1. Propósito

Schema v3 agrega los campos mínimos necesarios para evaluar si una señal bloqueada habría sido **ejecutable por el bot** en el momento real de evaluación pre-block.

v2 mide el rendimiento del **trader** (resolución de mercado vs `avg_price_entered`). Eso no responde si el bot habría podido entrar al mismo precio con sus filtros activos. Por eso A7 quedó `WAITING_SCHEMA`: la cohorte v2 condition_filtered + exact tiene n=95 WR=94.7%, pero `bot_would_have_bought=None` en 133/133 y `bot_evaluation_source=unknown` en 133/133. Sin estos campos poblados, no hay base para UNLOCK.

v3 produce evidencia bot-executable. No es condición suficiente para monetizar A7; sólo habilita el re-check.

## 2. Campos nuevos mínimos

Sobre el schema v2 existente, v3 añade dos campos obligatorios:

| Campo | Tipo | Valores |
|---|---|---|
| `bot_would_have_bought` | bool | `true` / `false` |
| `bot_evaluation_source` | enum | `live_eval` / `replay` / `unknown` |

Resto del schema v2 se preserva sin cambios.

## 3. Definición

- **`bot_would_have_bought = true`** solo si, en el punto real de evaluación pre-block, el bot habría pasado **todos sus filtros de compra** (edge, sizing, liquidez, price band, risk rules, whitelist, city mode, etc.) **excepto el bloqueo analizado** (`reason_blocked`). Es decir: la única razón por la que el bot no compró fue el filtro que estamos auditando.
- **`bot_would_have_bought = false`** si el bot habría sido bloqueado por al menos un filtro adicional al `reason_blocked` registrado, o si la evaluación pre-block no pasó.
- **`bot_evaluation_source = live_eval`** cuando los campos se capturan en runtime real durante el flujo de evaluación pre-block del bot, sobre el estado vigente de filtros y precios.
- **`bot_evaluation_source = replay`** cuando se reconstruyen offline contra snapshot de filtros/precios del momento (no live).
- **`bot_evaluation_source = unknown`** para registros históricos (v1/v2) o cualquier registro v3 donde no se pudo obtener evaluación confiable.

Sólo `live_eval` cuenta como evidencia primaria para el re-check A7. `replay` y `unknown` son referencia secundaria.

## 4. Punto de inyección

Los dos campos deben capturarse dentro del **flujo de evaluación pre-block**, antes de escribir el registro a `blocked_signals_resolutions.jsonl`. Es decir: el bot ya conoce el resultado de sus filtros internos en ese punto; v3 sólo persiste esa decisión junto al motivo de bloqueo.

Este documento define **el contrato del campo**, no la implementación. La selección de la función concreta de inyección, la propagación de estado y el manejo de errores son alcance de un patch posterior, fuera de este documento.

## 5. Migración

- v3 coexiste con v2. Registros nuevos llevan `schema_version: 3`; registros v2 existentes no se modifican.
- **No hay backfill** de registros v1 ni v2. El histórico actual permanece tal cual en `blocked_signals_resolutions.jsonl`.
- El histórico actual queda clasificado como **trader-level evidence**: válido para entender comportamiento de mercado y traders, no válido para decidir UNLOCK de filtros del bot.
- Los reportes A7 deben filtrar explícitamente por `schema_version >= 3` y `bot_evaluation_source = live_eval` para evidencia bot-executable.

## 6. Criterio A7 re-check

Re-evaluar A7 sólo cuando se cumplan todas estas condiciones simultáneamente sobre la cohorte v3:

- `schema_version = 3`
- `bot_evaluation_source = live_eval`
- `bot_would_have_bought = true`
- cohorte filtrada coincide con la cohorte candidata (p.ej. `reason_blocked = condition_filtered`, `condition = exact`)
- **n ≥ 60** registros que cumplen lo anterior

Recalcular WR sobre esa cohorte:

- **WR ≥ 70% con n ≥ 60 → UNLOCK_REVIEW** (handoff a Opus para verdict, no auto-unlock).
- **WR < 70%** con n ≥ 60 → mantener HOLD, registrar en memoria y cerrar A7 como no-oportunidad.
- **n < 60 al 2026-05-28** → extender la ventana **2 semanas** (a 2026-06-11). No degradar el criterio (no bajar n, no bajar WR threshold).
- Si tras la extensión sigue n < 60 → re-decidir scope, no relajar el contrato.

UNLOCK_REVIEW no implica unlock automático. Opus decide en base al memo.

## 7. Guardrails

Este documento no autoriza ninguna de las siguientes acciones:

- **No UNLOCK** de filtros con el dataset actual ni durante la ventana de captura v3.
- **No** modificar whitelist, city modes, scheduler, sizing ni risk rules.
- **No** tocar BANKROLL ni su flujo de readiness.
- **No** Fase C.
- **No** Telegram accionable derivado de A7 hasta UNLOCK_REVIEW formal.
- **No** cambios en DB, env vars, ni configuración Railway derivados de este contrato.
- **No** backfill de registros v1/v2.
- **No** patch al código en este commit; sólo documentación.

Cualquier cambio que toque estos puntos requiere handoff explícito a Opus.
