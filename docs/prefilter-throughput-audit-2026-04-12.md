# Prefilter Throughput Audit - 2026-04-12

## Objetivo

Auditar el cuello real de throughput antes de edge usando evidencia runtime ya manifestada, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.

## Preflight Obligatorio

- `python tools/system_alignment_check.py` -> `ok=7`, `warning=1`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7`, `warning=1`, `error=0`
- checks ejecutados a `2026-04-12T10:36:27+00:00`
- runtime snapshot base: `data/runtime_import/`, `pulled_at=2026-04-12T10:15:51.3083432+00:00`

## Fuente y Metodo

- fuente principal: `data/runtime_import/skip_log.jsonl`
- ventana total realmente leida: `29` ciclos, `9896` skips
- cortes auxiliares usados:
  - vista completa de la ventana
  - `last12` ciclos (`3959` skips) para leer el funnel mas reciente
  - `last6` ciclos (`1980` skips) como confirmacion corta de tendencia

## Resumen Ejecutivo

- el cuello dominante sigue estando antes de edge
- en la ventana completa, los filtros pesan:
  - `date_out_of_range_past`: `4475` (`45.2%`)
  - `price_out_of_range`: `2249` (`22.7%`)
  - `blocked_city`: `1678` (`17.0%`)
  - `timezone_filter`: `1045` (`10.6%`)
- pero en el tramo mas reciente (`last12`) la composicion cambia con claridad:
  - `date_out_of_range_past`: `1681` (`42.5%`)
  - `price_out_of_range`: `1279` (`32.3%`)
  - `timezone_filter`: `605` (`15.3%`)
  - `blocked_city`: `176` (`4.4%`)
- conclusion operativa: hoy el throughput real se pierde sobre todo por `tiempo + precio`; la composicion por ciudad/modo pesa menos en el funnel reciente, en parte por cambio de policy (`Miami`/`Seattle`) y no solo por evolucion estructural

## 1. `date_out_of_range_past`: llegada tarde normal vs mercado realmente inutil

Hallazgo principal:

- de `4475` skips por `date_out_of_range_past`, `3980` (`88.9%`) caen el mismo dia del mercado (`days_late=0`)
- solo `495` (`11.1%`) llegan un dia tarde (`days_late=1`)
- no aparece masa material de mercados mucho mas viejos dentro de esta muestra

Lectura:

- la mayor parte del bucket parece venir de mercados que entran demasiado tarde dentro del flujo normal del mismo dia, no de basura claramente inutil
- esto es aun mas cierto en el tramo reciente: en `last12`, `1472` de `1681` skips de fecha (`87.6%`) siguen siendo del mismo dia

Señales que empujan a esa lectura:

- el bucket esta dominado por `city_mode=shadow` (`3738`) y luego `canary` (`737`), no por `blocked`
- hay `2136` combinaciones unicas `city + date + question` dentro del bucket same-day, asi que no es solo un residuo de unos pocos mercados repetidos
- el subbucket `days_late=1` se concentra mas en ciudades concretas como `Los Angeles` (`99`), `San Francisco` (`66`), `Seattle` (`55`) y `Miami` (`22`), lo que parece mas cercano a residuo/staleness geografico o de calendario que al patron dominante del funnel

Veredicto de fecha:

- `date_out_of_range_past` domina de verdad
- y su mayor parte parece recuperable en principio por palanca temporal, no descartable como universo muerto

## 2. Distribucion real de `price_out_of_range`

Hallazgo principal:

- `2249` skips por precio en la ventana completa
- `2194` (`97.6%`) tienen `mkt_prob < 20`
- solo `55` (`2.4%`) tienen `mkt_prob > 80`
- no hay practicamente nada en el medio:
  - `20-25`: `0`
  - `25-75`: `0`
  - `75-80`: `0`

Forma del bucket:

- `0-5`: `1866` (`83.0%`)
- `5-10`: `147` (`6.5%`)
- `10-15`: `90` (`4.0%`)
- `15-20`: `91` (`4.0%`)
- `95-100`: `44` (`2.0%`)

Cuantiles:

- `min=0.0`
- `p25=0.05`
- `median=0.3`
- `p75=2.2`
- `p90=10.5`
- `max=99.95`

Lectura:

- el filtro de precio no esta recortando una nube equilibrada alrededor del rango permitido
- esta recortando casi por completo mercados pegados al suelo de precio
- en el tramo reciente la historia se mantiene: en `last12`, `1239` de `1279` (`96.9%`) siguen por debajo de `20`

Veredicto de precio:

- el bucket es real y grande
- pero la evidencia sugiere que el problema no es un margen fino cerca del bound, sino una bolsa grande de mercados extremadamente baratos

## 3. Miami y Seattle en shadow: universo visible adicional o impacto material

Estado efectivo actual:

- `runtime_policy_effective_view_latest.md` ya las muestra como `effective_mode=shadow`

Evidencia reciente en `skip_log` (`last12`):

- `Miami`: `110` filas, `10` ciclos presentes, `44` preguntas distintas
  - `date_out_of_range_past`: `55` (`50.0%`)
  - `price_out_of_range`: `45` (`40.9%`)
  - `condition_filtered`: `10` (`9.1%`)
- `Seattle`: `121` filas, `10` ciclos presentes, `44` preguntas distintas
  - `date_out_of_range_past`: `88` (`72.7%`)
  - `price_out_of_range`: `27` (`22.3%`)
  - `condition_filtered`: `5` (`4.1%`)
  - `below_min_edge`: `1` (`0.8%`)

Lectura:

- si, ambas estan aportando universo visible adicional real
- ya no aparecen en el tramo reciente como `blocked_city`; aparecen 100% como `shadow`
- ademas se ven de forma sostenida en `10` de los ultimos `12` ciclos, no como apariciones puntuales

Pero el impacto material sigue siendo limitado:

- `Miami + Seattle` suman `231` filas de `3959` en `last12`, o `5.8%` del funnel visible reciente
- ese nuevo universo no cambia el cuello dominante:
  - casi todo termina en `date_out_of_range_past` o `price_out_of_range`
  - solo `1` fila total entre ambas llega a `below_min_edge`

Veredicto Miami/Seattle:

- aportan visibilidad adicional real
- pero todavia no cambian materialmente la historia del funnel

## 4. Siguiente palanca prometedora

Comparacion honesta:

- `composicion por ciudad/modo` pierde fuerza como siguiente palanca:
  - `blocked_city` cae a solo `4.4%` en `last12`
  - el funnel reciente ya es `70.6% shadow`, `24.4% canary`, `4.4% blocked`
- `precio` sigue siendo importante (`32.3%` en `last12`), pero su bucket es muy extremo y hoy parece mas "universo muy barato" que "margen fino recuperable"
- `tiempo` sigue siendo el mayor bucket (`42.5%` en `last12`) y ademas su mayor parte parece venir de llegada tarde normal del mismo dia, no de mercado muerto

## Veredicto Corto

El prefiltro que domina de verdad el throughput hoy es `date_out_of_range_past`. El bucket same-day (`88.9%`) es la señal mas prometedora, pero la recuperabilidad real por palanca temporal queda como hipotesis y no como conclusion cerrada hasta abrir ese modulo.

## Siguiente Sesion Logica

Abrir un modulo separado, todavia pre-edge y todavia sin tocar `MIN_EDGE`, para auditar la palanca temporal con una pregunta concreta:

- cuanto del bucket same-day de `date_out_of_range_past` parece realmente recuperable con granularidad horaria, frente a cuanto ya llega demasiado tarde incluso dentro del mismo dia

## No Concluir Aun

- no hay base en esta auditoria para priorizar `MIN_EDGE`
- no hay base en esta auditoria para reabrir composicion por `blocked_city` como cuello principal
- no hay base en esta auditoria para mezclar este readout con monetizacion
