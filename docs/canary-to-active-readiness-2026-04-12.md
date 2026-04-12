# Canary to Active Readiness

Fecha de auditoría: 2026-04-12

Fuentes usadas:
- `data/runtime_import/city_policy_state.json`
- `data/runtime_import/trade_lifecycle.json`
- `data/runtime_import/cycles_history.jsonl`

Nota de snapshot:
- El snapshot actual ya no tiene solo 6 canary. `London` aparece en `auto_canary_cities` con `promoted_at=2026-04-12T15:03:51Z`.
- Esta auditoría respeta las 6 ciudades pedidas: `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`.

## Tabla de evidencia

Trades contados:
- Solo records de `trade_lifecycle` con `opened_at >= promoted_at` de cada ciudad.
- No se cuentan trades anteriores a la promoción a canary.

| Ciudad | `promoted_at` | Trades canary | WR canary | PnL canary | Mejor edge canary | Señales de fuente/settlement | Evaluación corta |
|------|------|------:|------:|------:|------:|------|------|
| Atlanta | `2026-04-06T09:29:24Z` | 1 | Lectura humana: 100.0% | Lectura humana: +$0.63 | 16.7% | Sí: win mal etiquetada en `trade_lifecycle` | No lista; el record sigue inconsistente aunque la señal real fue ganadora |
| Munich | `2026-04-06T07:20:18Z` | 0 | n/d | $0.00 | n/d | No señal de fuente rota; sí falta muestra | Necesita más ciclos y primer trade canary |
| New York City | `2026-04-06T21:37:22Z` | 0 | n/d | $0.00 | n/d | No señal de fuente rota; sí falta muestra | Necesita más ciclos y primer trade canary |
| Seoul | `2026-04-06T07:20:18Z` | 1 | 100.0% | +$0.28 | 17.6% | No | Aún muy poca muestra; lectura sana |
| Shanghai | `2026-04-06T12:33:22Z` | 1 | 100.0% | +$0.40 | 22.7% | No | Aún muy poca muestra; lectura sana |
| Tokyo | `2026-04-06T07:20:18Z` | 1 | 100.0% | +$0.38 | 24.8% | No | Aún muy poca muestra; lectura sana |

## Evidencia por ciudad

### Atlanta

Resumen:
- `trade_lifecycle` post-promoción: `1` record
- `cycles_history` con scan de Atlanta desde promoción: `18`
- Mejor edge visto en canary: `16.7%`

Hallazgo clave:
- El único trade canary (`Atlanta 76°F Apr7 YES`) está inconsistente dentro de `trade_lifecycle`.
- `close_context` dice:
  - `close_action=LOSS_TOTAL`
  - `close_reason=micro_position_unsellable`
  - `pnl_cash=-0.0`
- Pero la `timeline` del mismo record contiene antes:
  - `RESOLVED_WIN`
  - `pnl_cash=0.63`
- Y `post_exit_analysis` ve el mercado en `0.9995` tras el cierre.
- La lectura humana correcta queda documentada en `docs/atlanta-lifecycle-inconsistency-2026-04-12.md`: fue una operación ganadora que quedó mal etiquetada por el cierre micro posterior.

Lectura:
- No parece un problema de fuente rota.
- La señal económica real fue ganadora.
- Sí parece un problema de settlement/reconstrucción o de prioridad entre eventos de cierre dentro de `trade_lifecycle`.
- Mientras ese record no esté reconciliado, Atlanta no da una base limpia para evaluar paso a Active, aunque tampoco debe leerse como loss genuina.

### Munich

Resumen:
- `trade_lifecycle` post-promoción: `0` trades
- `cycles_history` con scan de Munich desde promoción: `5`
- `shadow_city_tracking.best_edge_pct`: `24.3%` pre-canary, pero no hay edge/trade canary registrado después

Lectura:
- No hay señal de fuente rota ni settlement inconsistente en los artefactos revisados.
- Lo que falta es muestra real post-promoción.
- Hoy no hay base operativa para evaluar Active.

### New York City

Resumen:
- `trade_lifecycle` post-promoción: `0` trades
- `cycles_history` con scan de NYC desde promoción: `21`
- Mejor edge canary en trades: `n/d`

Lectura:
- Tampoco aparecen señales de fuente rota o settlement inconsistente.
- Sí hay visibilidad y ciclos escaneados, pero cero conversiones a trade canary desde la promoción vigente (`2026-04-06T21:37:22Z`).
- Necesita más muestra o al menos el primer trade canary cerrado.

### Seoul

Resumen:
- `trade_lifecycle` post-promoción: `1` trade
- Resultado: `RESOLVED_WIN`
- `pnl_cash=+0.28`
- Edge de entrada: `17.6%`
- `cycles_history` con scan desde promoción: `27`

Calidad del cierre:
- `integrity.analysis_ready=true`
- `post_exit_analysis.market_seen_after_close=true`
- `reached_98_after_close=true`
- Sin incoherencias visibles

Lectura:
- Señal sana, pero muestra mínima.
- Está en estado “vale la pena seguir mirando”, no en estado de decisión fuerte.

### Shanghai

Resumen:
- `trade_lifecycle` post-promoción: `1` trade
- Resultado: `RESOLVED_WIN`
- `pnl_cash=+0.40`
- Edge de entrada: `22.7%`
- `cycles_history` con scan desde promoción: `23`

Calidad del cierre:
- `integrity.analysis_ready=true`
- `post_exit_analysis.market_seen_after_close=true`
- `reached_98_after_close=true`
- Sin señales de inconsistencia

Lectura:
- Es la evidencia más limpia del grupo junto con Tokyo.
- Aun así, sigue siendo solo un trade canary.

### Tokyo

Resumen:
- `trade_lifecycle` post-promoción: `1` trade
- Resultado: `RESOLVED_WIN`
- `pnl_cash=+0.38`
- Edge de entrada: `24.8%`
- `cycles_history` confirma buy canary en ciclo `62` (`2026-04-10T16:00:55Z`)

Calidad del cierre:
- `integrity.analysis_ready=true`
- `post_exit_analysis.market_seen_after_close=true`
- `reached_98_after_close=true`
- Sin señales de inconsistencia

Lectura:
- Evidencia limpia pero todavía demasiado corta.

## Lectura comparada

Lo que falta hoy para una evaluación manual seria hacia Active no es una sola cosa común:

- `Munich` y `New York City`: falta muestra operativa básica en canary.
- `Seoul`, `Shanghai` y `Tokyo`: ya tienen una primera señal positiva y limpia, pero todavía con `n=1`.
- `Atlanta`: tiene una señal ganadora real, pero el record actual está internamente inconsistente y contamina cualquier lectura automática de WR/PnL.

## Veredicto operativo

Con este snapshot, ninguna de las 6 tiene todavía una base canary suficientemente robusta para una lectura fuerte hacia Active.

La foto útil para Pablo hoy es:
- `Seoul`, `Shanghai` y `Tokyo`: sanas, pero todavía demasiado tempranas.
- `Munich` y `New York City`: necesitan convertir primero.
- `Atlanta`: su única señal canary fue ganadora, pero necesita reconciliar la inconsistencia de `trade_lifecycle` antes de usar el record como evidencia robusta.
