# Next Session Handoff - 2026-04-15

## Objetivo

Usar los avisos operativos del sistema para tomar una decision accionable orientada a monetizacion, no solo para documentar.

## Estado actual relevante

- El handoff original de `policy_execution_gate` ya no es el frente principal de esta linea.
- Desde las sesiones 188-189, el bot ya:
  - instrumenta `scan.slot_metrics` por slot
  - evalua automaticamente `04h` y `23h`
  - envia una alerta operativa pensada para abrir sesion Codex con salida de decision
- La recomendacion de sistema actual es:
  - `04h UTC`: `keep`
  - `23h UTC`: `disable_candidate` via `SCHEDULE_DISABLED_HOURS_UTC=23`
- A 17 de abril de 2026, Railway sigue con:
  - `SCHEDULE_HOURS_UTC=4,8,16,23`
  - sin `SCHEDULE_DISABLED_HOURS_UTC`
  - y con la env obsoleta `SLOT_04H_REVIEW_REMINDER_DATE`

## Decision operativa pendiente

Cerrar el loop live del scheduler:

1. aplicar o no `SCHEDULE_DISABLED_HOURS_UTC=23` en Railway
2. verificar que `04h` siga midiendo y que `23h` deje de correr
3. retirar cualquier env var obsoleta asociada al reminder manual si sigue viva

## Evidencia ya cerrada

- `04h UTC` ya demostro valor de discovery same-day real para `Tokyo`, `Seoul` y `Shanghai`.
- `23h UTC` quedo como slot de valor esperado muy bajo en la ventana analizada: sin edge y sin buys.
- El cuello principal de conversion detectado en `04h` fue ejecucion, no falta de edge.
- El aviso manual anterior ya fue retirado del runtime; ahora la revision la dispara el sistema con `slot_metrics`.

## Alcance recomendado

Sesion corta y accionable, enfocada en scheduler live y monetizacion por slot.

Leer:

- `AGENTS.md`
- bloque reciente de `CONTEXTO.md`
- [docs/04h-slot-observation-2026-04-17.md](/c:/Projects/polymarket-bot/docs/04h-slot-observation-2026-04-17.md)
- `cycle_summary.json` / `cycles_history.jsonl` con `scan.slot_metrics`
- variables live de Railway

## Foco analitico recomendado

1. Confirmar si `23h` sigue en `0 edge / 0 buys` en la ventana automatizada.
2. Verificar si el freno dominante de `04h` sigue siendo ejecucion (`buy_min_notional`) o cambia.
3. Decidir si el cambio debe ser:
   - aplicar env var live ya
   - observar una ventana corta mas
   - o promover una automatizacion reversible adicional

## No hacer de entrada

- No tocar `MIN_PRICE`, `MAX_PRICE`, Kelly, sigma, filtros de condicion ni trading core.
- No reabrir `policy_execution_gate` o `Phase 5` salvo que la nueva alerta lo pida explicitamente.
- No convertir la sesion en otra auditoria abierta sin salida de sistema.

## Salida ideal de la proxima sesion

Una de estas tres:

1. `SCHEDULE_DISABLED_HOURS_UTC=23` aplicado live y verificado.
2. Cambio preparado pero no aplicado, con criterio de validacion corto y automatico.
3. Reversion argumentada de la recomendacion si la evidencia nueva contradice el `disable_candidate`.
