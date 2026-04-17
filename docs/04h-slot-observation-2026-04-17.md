# 04h Slot Observation - 2026-04-17

## Objetivo

Revisar, cinco días después de activar `SCHEDULE_HOURS_UTC=4,8,16,23`, si el nuevo slot `04h UTC` abrió throughput útil real, si `23h UTC` sigue aportando valor neto y cómo cambió el funnel reciente.

## Fuente y corte usado

- pull fresco de `data/runtime_import/` vía `tools/railway_runtime_snapshot_pull.ps1`
- `runtime_import_manifest.json` / snapshot actualizado hasta `2026-04-17T08:00:42Z`
- baseline `pre`: últimos `12` ciclos exactos `08/16/23 UTC` antes del rollout (`2026-04-08T16:00:50Z` -> `2026-04-12T08:00:37Z`)
- ventana `post`: `18` ciclos exactos `04/08/16/23 UTC` desde `2026-04-13T04:01:11Z` hasta `2026-04-17T08:00:42Z`

Nota canónica: `markets_evaluated` es alias legacy de `candidates_after_prefilters`, no universo bruto de Polymarket.

## Resumen ejecutivo

- El slot `04h` **sí abrió same-day real para Asia**. En la ventana `post`, `Tokyo`, `Seoul` y `Shanghai` solo aparecen con `days_ahead=0` en ciclos exactos `04h`; en `08h/16h/23h` no dejan ninguna fila same-day.
- El efecto sobre throughput ejecutado todavía es **cero buys nuevos**. El `post` sube ligeramente en `markets_evaluated` y `with_edge`, pero sigue en `0` buys/ciclo.
- El mejor dato nuevo no es cantidad de compras sino **calidad de ventana**: el ciclo `2026-04-17T04:00:45Z` llegó a `25` candidatos post-filtro, `2` edges y `2` seleccionadas; la evidencia visible apunta a `Shanghai NO 20°C` y `Tokyo NO 18°C` same-day, pero la ejecución cayó por constraints operativos de tamaño mínimo / Kelly.
- El slot `23h` aporta poco valor neto en esta muestra. Mantiene `17.0` candidatos/ciclo, pero `0` edges, `0` buys y un bucket same-day que ya llega estructuralmente tarde (`date_out_of_range_past`) o bloqueado.

## 1. Pre vs post

| Ventana | Ciclos | `markets_evaluated` / ciclo | `with_edge` / ciclo | `buys` / ciclo | `city_window_skipped` / ciclo |
|---|---:|---:|---:|---:|---:|
| `pre` (`08/16/23`) | 12 | `16.5` | `0.08` | `0.08` | `0.0` |
| `post` (`04/08/16/23`) | 18 | `16.94` | `0.17` | `0.00` | `118.56` |

Lectura corta:

- `markets_evaluated` queda prácticamente plano: `16.5 -> 16.94` por ciclo.
- `with_edge` mejora un poco: `0.08 -> 0.17` por ciclo, pero desde una base muy baja.
- `buys/ciclo` no mejora: `0.08 -> 0.00`.
- `city_window_skipped` aparece con fuerza en `post` porque ahora existe el city-window pre-filter y deja evidencia estructurada en `scan`.

## 2. Desglose por slot en la ventana post

| Slot | Ciclos | `markets_evaluated` / ciclo | `with_edge` / ciclo | `buys` / ciclo | `city_window_skipped` / ciclo |
|---|---:|---:|---:|---:|---:|
| `04h` | 5 | `20.8` | `0.40` | `0.00` | `11.0` |
| `08h` | 5 | `17.8` | `0.00` | `0.00` | `116.6` |
| `16h` | 4 | `11.0` | `0.25` | `0.00` | `189.75` |
| `23h` | 4 | `17.0` | `0.00` | `0.00` | `184.25` |

Lectura:

- `04h` es el mejor slot nuevo en throughput pre-edge: lidera `markets_evaluated` y también `with_edge`.
- `16h` conserva algo de edge residual, pero con city-window muy alto.
- `23h` no convierte nada en esta muestra: buen volumen post-filtro, cero edge, cero buys, mucha ventana estructural perdida.

## 3. Verificación específica: same-day real para Tokyo / Seoul / Shanghai

Hallazgo cerrado:

- `Tokyo`, `Seoul` y `Shanghai` tienen filas `same-day` (`days_ahead=0`) **solo en `04h`**.
- En ciclos exactos `08h`, `16h` y `23h` no aparece ninguna fila same-day de esas tres ciudades.

Conteo same-day en `04h`:

| Ciudad | Filas same-day | Motivo dominante |
|---|---:|---|
| `Seoul` | `33` | `price_out_of_range=29` |
| `Shanghai` | `33` | `price_out_of_range=28` |
| `Tokyo` | `33` | `price_out_of_range=29` |

Interpretación:

- El slot `04h` no solo abrió visibilidad teórica: abrió **mercados same-day reales** que ya no estaban muriendo por ventana horaria.
- El cuello ya no es temporal para esas plazas en `04h`; pasa a ser principalmente `price_out_of_range`, `condition_filtered`, `kelly_too_low` o límites operativos de orden.

## 4. Evidencia fuerte del 2026-04-17 04h UTC

El ciclo exacto `2026-04-17T04:00:45Z` es la mejor prueba de valor del slot:

- `25` candidatos post-filtro
- `2` edges (`with_edge=2`)
- `2` seleccionadas
- `city_window_skipped=11` y solo afecta a `Wellington`

Readout operativo visible en `decisions.log`:

- `Shanghai NO 20°C 2026-04-17` con `edge=25.4%`
- `Tokyo NO 18°C 2026-04-17` con `edge=24.6%`
- `Seoul` muestra también edge same-day, pero cae por `sold_this_cycle` / `kelly_too_low`

Veredicto:

- `04h` ya produjo **same-day asiático con edge útil real**.
- Lo que aún no produjo es monetización efectiva, por frenos posteriores al discovery (`min size`, Kelly, constraints de ejecución).

## 5. ¿Aporta valor neto el slot 23h?

En esta muestra exacta, el caso para `23h` es débil:

- `17.0` `markets_evaluated` por ciclo
- `0.0` `with_edge` por ciclo
- `0.0` buys por ciclo
- `184.25` `city_window_skipped` por ciclo

Además, el bucket same-day de `23h` es mala señal:

- `Amsterdam`: `date_out_of_range_past=33`
- `Istanbul`: `date_out_of_range_past=33`
- `Toronto`: `blocked_city=33`
- no aparece same-day útil para `Tokyo`, `Seoul` o `Shanghai`

Lectura:

- `23h` hoy parece servir más como slot tardío de observación/futuro que como slot con valor operativo inmediato.
- Si el objetivo principal del schedule es **throughput same-day útil**, `23h` ya es **candidato real a salir**.
- Si se quiere conservar por observación de mercados de mañana, el costo de oportunidad debería justificarse explícitamente; esta muestra no enseña edge ni buys que lo defiendan.

## 6. Price-out-of-range por ciudad y temporalidad

Top ciudades `post` por filas `price_out_of_range` en ciclos exactos:

| Ciudad | Filas | Same-day | Desglose relevante |
|---|---:|---:|---|
| `London` | `105` | `52` | `04h=34`, `08h=36`, `16h=18`, `23h=17` |
| `Seoul` | `101` | `29` | `04h=38` con `29` same-day; `23h=36` pero `0` same-day |
| `Tokyo` | `91` | `29` | `04h=38` con `29` same-day; `23h=35` pero `0` same-day |
| `Shanghai` | `62` | `28` | `04h=28` con `28` same-day; `23h=34` pero `0` same-day |

Lectura por ciudad:

- En `Tokyo`, `Seoul` y `Shanghai`, el `price_out_of_range` same-day es un fenómeno **casi enteramente de `04h`**.
- En `23h`, esas mismas ciudades siguen apareciendo en `price_out_of_range`, pero ya como mercados no same-day; o sea, `23h` no reemplaza el valor temporal que sí abre `04h`.
- `Shanghai` es especialmente limpio: `04h` concentra todo su `price_out_of_range` same-day (`28/28`) y `23h` concentra solo casos no same-day (`34/34`).

## Veredicto final

1. `04h UTC` **sí está justificando su existencia**: abrió same-day real para `Tokyo`, `Seoul` y `Shanghai`, y ya produjo edges asiáticos same-day que antes no existían en los slots exactos.
2. El experimento todavía **no convierte en buys**. El cuello se movió de ventana horaria a precio / condición / Kelly / mínimos operativos de orden.
3. `23h UTC` hoy tiene señal débil y sesgo tardío. Si el objetivo es throughput útil y no observación pasiva, queda como **candidato razonable a retirar** en la próxima revisión de scheduler.
4. La siguiente pregunta honesta ya no es “¿sirvió 04h?” sino “¿qué guardrail post-edge está evitando monetizar el edge same-day que 04h ya abrió?”.

## Decisión de sistema

- `04h UTC`: **keep**
- `23h UTC`: **feature flag**
- recomendación operativa concreta: mantener `SCHEDULE_HOURS_UTC=4,8,16,23` en código/base, pero dejar preparado `SCHEDULE_DISABLED_HOURS_UTC=23` como kill-switch reversible para cortar el slot de menor utilidad neta sin reescribir el scheduler

## Cambio aplicado tras la revisión

Se preparó patch de sistema para que esta revisión no quede solo en análisis:

- se elimina del bot el recordatorio one-shot `04h` porque ya cumplió su función y añade ruido operativo si sigue vivo
- se añade `SCHEDULE_DISABLED_HOURS_UTC` para apagar slots concretos detrás de feature flag
- se instrumenta `scan.slot_metrics` en `cycle_summary.json` / `cycles_history.jsonl` con:
  - `slot_hour_utc`
  - `same_day_candidates`
  - `same_day_edges`
  - `same_day_selected`
  - `same_day_buys`
  - `edges`
  - `selected`
  - `buys`
  - `buy_rate`
  - `same_day_buy_rate`
  - `reject_reasons`
  - `same_day_reject_reasons`
  - `execution_reject_reasons`
- se corrige además un cuello real de monetización: cuando una compra seleccionada caía justo por debajo del mínimo de notional por redondeo, el sistema ahora ajusta `shares` hacia arriba antes de ejecutar la orden

Lectura final:

- `04h` ya abrió valor hacia monetización
- el próximo corte debe medir conversión con la nueva instrumentación
- si `23h` sigue en `0` edge / `0` buy tras una ventana corta adicional con métricas automáticas, la acción operativa correcta pasa a ser activar `SCHEDULE_DISABLED_HOURS_UTC=23`
