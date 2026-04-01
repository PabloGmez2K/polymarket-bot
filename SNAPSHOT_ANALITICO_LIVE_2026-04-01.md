# Snapshot Analitico Live — 1 abril 2026

**Fuente:** dashboard live de Railway  
**Snapshot JSON congelado:** `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json`  
**Momento de generacion del dashboard:** `2026-04-01 20:13 UTC`  
**Version live observada:** `v10.6.10`

## Lectura ejecutiva

- Estado focus live: `Sano con limitaciones`.
- Headline live: `La operativa parece estable; el cuello de botella ahora es learning / measurement.`
- Accion recomendada por el propio dashboard: `No tocar trading: priorizar crecimiento de muestra NOAA`.
- Salud operativa:
  - `portfolio_total = $31.91`
  - `low_bankroll = false`
  - `signals ok`
  - sin `pending_exit` atascadas
- Cuello de botella vigente:
  - `NOAA 2/10 casos`
  - `0/4 ciudades interpretables`
  - solo `Chicago` tiene muestra incipiente (`2/3`)

## Foto de exits y operativa

### Trade console live

- `Operaciones totales: 101`
- `Cerradas: 85`
- `Abiertas: 16`
- `TP: 5`
- `SL: 13`
- `Ganadas: 12`
- `Perdidas: 73`
- `PnL neto: $-37.53`
- `Dejado de ganar: $1.91`
- `Protegido: $6.16`

### Muestra observada post-salida

- `7/85` cierres con trayectoria post-salida util
- Headline de analitica observada: `La muestra observada sugiere buena proteccion`

### Breakdown validado por tipo de cierre

| Tipo | Count | Balance | Media |
|---|---:|---:|---:|
| Take-profit | 5 | $+12.23 | $+2.45 |
| Stop-loss | 13 | $-17.28 | $-1.33 |
| Re-evaluacion | 2 | $+0.32 | $+0.16 |
| LOSS_TOTAL | 60 | $-37.74 | $-0.63 |
| Ganadas por resolucion | 5 | $+4.94 | $+0.99 |

## Casos reales revisados

### Re-eval observado

- `Will the highest temperature in New York City be 74°F or higher on March 31?`
- Bucket live: `Re-eval`
- Resultado live: `Ganada`
- `PnL = $+0.06`
- `trade_value = $1.32`
- Observacion post-salida: `2 obs`
- Regla de salida: `Re-eval: edge recalculado < -3%`

**Lectura:** la muestra observada de `Re-eval` sigue siendo minima (`1/2` en cobertura observada) y en el dashboard live cae del lado `Revisar captura`, con `upside_left = $1.66` y `drawdown_avoided = $0.00`.

### Stop-loss observados

- `Will the highest temperature in Dallas be between 82-83°F on April 1?`
  - Bucket live: `Stop-loss`
  - Resultado live: `Perdida`
  - `PnL = $-0.56`
  - `trade_value = $0.41`
  - Observacion post-salida: `3 obs`
  - Regla: `SL mecanico: PnL <= -25%`

- `Will the highest temperature in Atlanta be between 80-81°F on April 1?`
  - Bucket live: `Stop-loss`
  - Resultado live: `Perdida`
  - `PnL = $-1.30`
  - `trade_value = $0.77`
  - Observacion post-salida: `sin obs`
  - Regla: `SL mecanico: PnL <= -25% | trigger 10.5c | limite 8.0c | STOP-LOSS (-56.2% < -25.0%)`

**Lectura:** la muestra observada de `Stop-loss` sigue siendo muy chica (`1/13` en cobertura observada), pero por ahora aparece `Mixto`, con `upside_left = $0.25` y `drawdown_avoided = $0.09`.

### Take-profit identificados en live

El payload live revisado no trae ningun `Take-profit` dentro de los `trade_rows` visibles/observados del snapshot actual, pero si los identifica en trofeos y breakdown validado:

- `Chicago YES`
  - `Mejor operacion`
  - `SELL · take_profit`
  - `PnL = $+3.96`

- `Atlanta Mar30 YES`
  - `Mejor retorno %`
  - `v10.6.10 · serie v10.6 · SELL · take_profit`
  - `return = +302.5%`

**Lectura:** hay `5` cierres `take_profit` ya validados y con balance agregado claramente positivo (`$+12.23`), pero en este snapshot live todavia no hay muestra observada post-salida suficiente para evaluar si los TP estan dejando demasiado upside (`coverage 0/5`).

## Hallazgo importante sobre la consola live

La lectura live confirma exactamente el problema semantico que quedaba pendiente:

- en la tabla visible del snapshot, `37` trades caen en bucket `Otro`;
- muchos de esos `Otro` muestran salida `Micro posicion incanjeable / perdida total`;
- el breakdown validado ya reconoce que hay `60 LOSS_TOTAL` reales.

**Conclusion operativa:** la consola live actual todavia mezcla `LOSS_TOTAL`, resoluciones y cierres legacy/parciales dentro de una lectura humana demasiado ambigua. La refinacion local hecha en esta sesion sigue siendo necesaria para que el panel deje de colapsar esas categorias en `Otro/Perdida`.

## Recomendacion siguiente

1. Desplegar la refinacion local de semantica del `trade console`.
2. Revalidar live esta misma consola con el mismo enfoque `TP / reeval / SL / LOSS_TOTAL / legacy`.
3. Si vuelve a abrirse auth completa de Railway CLI, descargar `trade_lifecycle.json` live para revisar casos TP antiguos que no entran en los `trade_rows[:40]` del snapshot JSON.
