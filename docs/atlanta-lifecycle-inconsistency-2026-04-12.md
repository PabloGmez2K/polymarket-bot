# Atlanta trade_lifecycle inconsistency

Fecha de auditoría: 2026-04-12

Fuentes usadas:
- `data/runtime_import/trade_lifecycle.json`
- `docs/canary-to-active-readiness-2026-04-12.md`

## Trade afectado

- `Atlanta 76°F Apr7 YES`
- `id=36458329612369948500712328628712399601085721196444383048533447437032218031300|YES|2026-04-07|2026-04-09T23:00:23.088594+00:00`

## Conflicto interno

El record contiene dos lecturas incompatibles:

1. `close_context` lo deja como cierre final de pérdida micro:
   - `close_action=LOSS_TOTAL`
   - `close_reason=micro_position_unsellable`
   - `close_price=0.9995`
   - `pnl_cash=-0.0`

2. La `timeline` registra antes una resolución ganadora explícita:
   - `2026-04-07T23:00:13.948928+00:00`
   - `action=RESOLVED_WIN`
   - `reason=market_resolved_yes`
   - `price=0.9995`
   - `pnl_cash=+0.63`

Además, `post_exit_analysis` confirma que tras el cierre el mercado siguió visto a `0.9995`:

- `market_seen_after_close=true`
- `max_price_after_close=0.9995`
- `reached_98_after_close=true`

## Lectura correcta

La lectura operativa correcta es que fue una operación ganadora que quedó mal etiquetada en `trade_lifecycle`.

No hay evidencia aquí de una señal perdedora real ni de un mismatch forecast/settlement para Atlanta en este trade. Lo que aparece es una colisión entre:

- una resolución correcta a favor (`RESOLVED_WIN`, `pnl_cash=+0.63`)
- y un cierre posterior de residuo micro (`LOSS_TOTAL`, `micro_position_unsellable`, `pnl_cash=-0.0`)

Ese evento micro no debe reinterpretarse como resultado económico real de la operación.

## Impacto de lectura

Para la tabla `canary-to-active-readiness`, Atlanta debe leerse como:

- trade canary con señal ganadora real
- record contaminado por inconsistencia interna de `trade_lifecycle`
- no como pérdida operativa genuina

## Guardrail de esta nota

Esta sesión no cambia:

- el resultado real persistido del trade
- el mecanismo de cierre
- `bot.py`

Solo deja documentado que el etiquetado final de `trade_lifecycle` es inconsistente con la evidencia del propio record y que, para lectura humana, Atlanta debe tratarse como win mal etiquetada.
