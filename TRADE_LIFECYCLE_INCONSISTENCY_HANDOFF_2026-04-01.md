# Trade Lifecycle Inconsistency Handoff - 1 abril 2026

## Objetivo de la proxima sesion

Sanear la trazabilidad de `trade_lifecycle` y la consola de trades para que cada posicion reciente tenga una sola historia coherente y legible:

- por que entro;
- por que intento salir;
- por que cerro;
- que hizo el mercado despues;
- y, si hubo `redeem/claim`, dejar claro que parte fue resolucion y que parte fue cobro manual.

## Evidencias confirmadas en esta auditoria

1. `Seoul 14C on April 1` aparece con desenlace contradictorio en el snapshot congelado.
   - En `trade_rows` aparece una fila como `Perdida` con salida `Micro posicion incanjeable / perdida total` y `pnl_cash = -1.05`.
   - El mismo mercado aparece tambien como `Ganada` con salida `market_resolved_yes` y `pnl_cash = +0.61`.
   - Esto rompe la lectura "un trade = una historia".

2. `Seoul 13C on April 1` sale como ganada pero conserva entrada parcial pese a ser un caso reciente.
   - La fila visible marca `status = Ganada`, `trade_value = $3.04`.
   - Pero `entry_condition` muestra `Historico parcial: faltan datos claros de entrada.`
   - Para un trade reciente deberiamos conservar la entrada real, no degradarlo a historico parcial.

3. `Atlanta 70-71F on March 30` sigue saliendo duplicada.
   - Aparece una fila "completa" con entrada `20.0c | edge 25.3% | forecast 23.1C` y perdida `-1.33`.
   - Ademas aparecen filas heredadas/parciales del mismo mercado con `trade_value = $0.00`.
   - Esto indica que el coalescing / matching aun no deja una unica traza humana limpia.

4. `Atlanta 78-79F on April 1` existe en cartera muerta pero no quedo visible en la tabla extraida de `trade_rows`.
   - En `portfolio.dead` aparece con `initialValue = 2.1238`, `currentValue = 0.010619`, `cashPnl = -2.113181`.
   - En la extraccion auditada de `trade_rows` no aparecio una fila equivalente.
   - Hay que comprobar si es un problema de generacion del row, de filtrado, de orden o de semantica del cierre.

5. La etiqueta visible del trade no incorpora el lado cuando existe `question`.
   - `_trade_lifecycle_label()` devuelve primero `question` y solo cae a `city/date/side` si falta `question`.
   - Eso dificulta distinguir rapido mercados hermanos `YES/NO` cuando la pregunta es casi identica.
   - Referencia: `bot.py`, helper `_trade_lifecycle_label()`.

6. El cobro manual (`redeem/claim`) no se registra como evento propio.
   - La capa registra `BUY`, `SELL_PENDING`, `SELL`, `SELL_FAILED`, `LOSS_TOTAL`, `RESOLVED_WIN`.
   - `RESOLVED_WIN` se infiere al detectar `curPrice >= 0.98`, pero no existe un evento explicito de `REDEEM`.
   - Por tanto hoy sabemos "el mercado resolvio a favor", pero no "cuando se cobro manualmente".

7. Hay una diferencia entre lo que la capa intenta guardar y lo que realmente llega limpio a la consola.
   - En origen, los BUYs guardan `price`, `shares`, `amount`, `edge_pct`, `our_prob`, `mkt_price`, `forecast_max`, `trader_confirmed`, `cycle_number` y `logic_cycle_number`.
   - Los SELL_PENDING guardan `reason`, `decision_note`, `decision_source`, `trigger_price`, `limit_price`, `pnl_pct`, `pnl_cash`, `current_value` y `order_id`.
   - Ademas existen `position_snapshots`, `market_observations` y `post_exit_analysis`.
   - La inconsistencia no parece estar en ausencia total de datos, sino en reconciliacion / coalescing / presentacion final.

## Que si parece estar bien

- La entrada de BUY esta bien instrumentada.
- La razon de salida mecanica tambien esta bien instrumentada cuando pasa por `SELL_PENDING`.
- La confirmacion de fills `SELL_PENDING -> SELL` existe.
- Hay snapshots de posicion abierta y observacion post-salida.

## Hipotesis de trabajo para la proxima sesion

1. Auditar el matching por `id`, `token_id`, `question + side` y `city + side + date` para casos recientes.
2. Separar claramente:
   - cierre de mercado;
   - perdida total / micro posicion incanjeable;
   - cobro por resolucion;
   - redeem manual.
3. Revisar por que algunos casos recientes caen en `Historico parcial`.
4. Revisar por que algunos casos aparecen duplicados o contradictorios.
5. Hacer que la tabla visible incluya `side` de forma explicita aunque exista `question`.
6. Validar con los mercados concretos de esta auditoria antes de tocar cualquier otra cosa.

## Prompt sugerido para la nueva sesion

```text
Quiero dedicar esta sesion solo a sanear las inconsistencias de `trade_lifecycle` y de la trade console. Usa `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` como punto de partida y verifica/corrige especificamente estos casos recientes: `Seoul 14C Apr 1`, `Seoul 13C Apr 1`, `Atlanta 70-71F Mar 30`, `Atlanta 78-79F Apr 1`, `Atlanta 80-81F Apr 1`, `Tokyo 18C Apr 1`, `Buenos Aires 28C Apr 1`, `Chicago 40-41F Apr 1`, `Dallas 82-83F Apr 1`. Quiero que cada posicion tenga una sola historia coherente: por que entro, por que salio o resolvio, que paso despues y si hubo `redeem/claim`. No toques reglas de trading ni NOAA; enfocate solo en trazabilidad, reconciliacion y presentacion. Termina con validacion concreta sobre esos trades y actualiza `CONTEXTO.md` y `HISTORIAL_SESIONES.md`.
```

## Alcance de esta sesion

- No se tocaron reglas de trading.
- No se desplego nada.
- No se modifico la logica del bot.
- Solo se auditaron inconsistencias y se dejo handoff persistente para la siguiente sesion.
