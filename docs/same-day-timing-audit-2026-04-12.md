# Same-Day Timing Audit - 2026-04-12

## Objetivo

Auditar el subbucket same-day dentro de `date_out_of_range_past` con granularidad horaria para distinguir cuánto parece realmente recuperable por timing y cuánto ya entra demasiado tarde incluso dentro del mismo día.

## Preflight Obligatorio

- `python tools/system_alignment_check.py` -> `ok=7`, `warning=1`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7`, `warning=1`, `error=0`
- checks ejecutados a `2026-04-12T10:56:05+00:00`

## Fuente y Metodo

- fuente principal: `data/runtime_import/skip_log.jsonl`
- ventana leída: `29` ciclos, `9896` skips
- bucket auditado: `date_out_of_range_past = 4475`
- definición de same-day usada aquí: `(ts_utc.date() - date_iso).days = 0`
- definición de "too late in practice": la misma regla operativa ya usada por `bot.py`
  - `get_min_days_ahead()`: desde `12:00 UTC`, `min_days_global=1`
  - `get_min_days_for_city()`: si la ciudad ya está en el día siguiente local o si está en el mismo día local pero `hora_local >= 14`, el bot considera que "hoy" ya es demasiado tarde
- para traducir `ts_utc -> hora_local` se usaron offsets fijos por ciudad para esta foto de abril de 2026, sin instalar dependencias nuevas ni tocar el runtime

## Resumen Ejecutivo

- el hallazgo fuerte no es que el same-day sea una bolsa claramente recuperable
- el hallazgo fuerte es casi el contrario: dentro de `date_out_of_range_past`, el same-day existe masivamente, pero casi todo ya cae después del cutoff horario práctico del propio bot
- sobre `3980` filas same-day, solo `55` (`1.4%`) quedan en la zona `late but plausibly recoverable`
- las otras `3925` (`98.6%`) ya están `too late in practice`
- en `last12` la señal no mejora:
  - `1472` filas same-day
  - `33` (`2.2%`) plausibly recoverable
  - `1439` (`97.8%`) already too late

## 1. Distribucion horaria real del same-day

Dentro de `date_out_of_range_past`:

- total bucket: `4475`
- same-day: `3980` (`88.9%`)
- one-day late: `495` (`11.1%`)

Distribución real del same-day por slot UTC:

| Slot UTC | Filas | % same-day |
| --- | ---: | ---: |
| `12-13 UTC` | `308` | `7.7%` |
| `14-15 UTC` | `440` | `11.1%` |
| `16-17 UTC` | `1415` | `35.6%` |
| `18-19 UTC` | `0` | `0.0%` |
| `20-21 UTC` | `462` | `11.6%` |
| `22-23 UTC` | `1355` | `34.0%` |

Lectura:

- el bucket no aparece por la mañana UTC; empieza cuando el sistema ya cambió a `min_days_global=1`
- tampoco está concentrado en una única hora rara: aparece en casi todos los slots post-mediodía que efectivamente corrieron en esta foto
- pero sí hay masa dominante en `16-17 UTC` y `22-23 UTC`

Normalizando por ciclo para no confundir "más filas" con "más ciclos":

- `12 UTC`: `154.0` filas same-day por ciclo
- `14 UTC`: `220.0` filas same-day por ciclo
- `16 UTC`: `202.1` filas same-day por ciclo
- `20 UTC`: `308.0` filas same-day por ciclo
- `21 UTC`: `154.0` filas same-day por ciclo
- `23 UTC`: `193.6` filas same-day por ciclo

Lectura:

- no es solo un artefacto de haber tenido más ciclos a `16` y `23`
- incluso por ciclo, el same-day sigue siendo alto en todos los slots post-`12 UTC`

## 2. Si el same-day se concentra en una ventana concreta o es estructural

La respuesta corta es: aparece de forma estructural dentro de las ventanas post-`12 UTC`, no como un borde fino y breve.

Evidencia:

- en la ventana completa, el same-day aparece en `5` bloques UTC distintos: `12-13`, `14-15`, `16-17`, `20-21`, `22-23`
- en `last12` la señal sigue viva en los dos slots reales recientes:
  - `16-17 UTC`: `656`
  - `22-23 UTC`: `816`
- en `last12`, el same-day representa:
  - `66.3%` de todos los skips del slot `16 UTC`
  - `61.8%` de todos los skips del slot `23 UTC`

Lectura:

- no estamos viendo una ventana estrecha tipo "solo justo al mediodía UTC"
- el problema persiste durante gran parte del tramo operativo posterior al cambio de `min_days_global`
- por eso la historia es más "same-day estructuralmente tardío" que "unos pocos mercados que llegan un poco tarde"

## 3. Recuperable por timing vs ya demasiado tarde en la práctica

Usando el cutoff local ya vigente en `bot.py`:

| Clasificación | Filas | % same-day |
| --- | ---: | ---: |
| `late but plausibly recoverable` | `55` | `1.4%` |
| `already too late in practice` | `3925` | `98.6%` |

Desglose del bucket `already too late in practice`:

- `same_local_day_after_14`: `2317`
- `local_next_day`: `1608`

Esto importa porque separa dos casos distintos:

- una parte grande ya entra en el mismo día local, pero pasado el umbral de `14:00`
- otra parte ni siquiera entra en el mismo día local: la ciudad ya está en el día siguiente

Mercados únicos same-day:

- `2136` mercados únicos (`city + date_iso + question`)
- clasificación por primera observación:
  - `44` (`2.1%`) plausibly recoverable
  - `2092` (`97.9%`) already too late
- clasificación por última observación:
  - `22` (`1.0%`) plausibly recoverable
  - `2114` (`99.0%`) already too late

Lectura:

- incluso quitando el efecto de reescaneo repetido, la mayor parte del same-day ya nace tarde
- el bucket recuperable existe, pero es pequeño y no parece un unlock general del funnel

## 4. Donde vive el subbucket recuperable

El subbucket recuperable no está repartido por todo el universo; está extremadamente concentrado.

Filas recoverable:

- `Los Angeles`: `22`
- `Denver`: `22`
- `Mexico City`: `11`

Horas UTC recoverable:

- `16 UTC`: `33`
- `20 UTC`: `22`

Lectura:

- la parte plausibly recoverable aparece casi solo en ciudades del oeste/hemisferio americano todavía por debajo del cutoff local
- no hay evidencia de un bucket recoverable grande y distribuido por Asia o Europa
- eso debilita la lectura de "same-day = throughput temporal global recuperable"

## 5. Composición por modo

Dentro del same-day:

- `shadow`: `3276` (`82.3%`)
- `canary`: `704` (`17.7%`)
- `blocked`: `0`

Lectura:

- el problema no depende de `blocked_city`
- tampoco parece ser una rareza de solo unas pocas canaries
- está incrustado sobre todo en el universo visible `shadow`, pero casi siempre en estado ya tardío

## Veredicto Corto

`tiempo` como hipótesis amplia de recuperación de throughput queda debilitada por esta auditoría.

El reason `date_out_of_range_past` sigue dominando el funnel y el same-day sigue siendo masivo, pero la evidencia horaria muestra que ese same-day casi nunca llega dentro de una ventana todavía operable según el propio cutoff local del bot. La parte plausibly recoverable existe, pero hoy parece un nicho pequeño y geográficamente acotado, no una palanca general.

## Respuesta a las 4 preguntas

1. Dentro de `date_out_of_range_past`, el same-day pesa `3980/4475` (`88.9%`), pero su distribución horaria real cae por completo en slots post-`12 UTC`, con mayor masa en `16-17 UTC` (`35.6%`) y `22-23 UTC` (`34.0%`).
2. El skip same-day no parece concentrado en una única ventana estrecha; aparece de forma estructural en casi todos los slots operativos posteriores al cambio de `min_days_global`, y en `last12` sigue muy vivo en `16 UTC` y `23 UTC`.
3. La parte plausibly recoverable es pequeña: `55/3980` filas (`1.4%`) y `44/2136` mercados únicos (`2.1%`) por primera observación. El resto ya entra demasiado tarde en la práctica: `3925/3980` filas (`98.6%`).
4. La siguiente discusión de throughput ya no debería priorizar `tiempo` como palanca general con el mismo entusiasmo que antes. Si se reabre, debería tratarse como hipótesis acotada por ciudad/slot, no como unlock horizontal del funnel.

## Siguiente Paso Logico

Si se quiere seguir abriendo throughput sin tocar `bot.py`, lo más lógico ya no parece ser "timing global same-day", sino elegir entre:

- auditar si existe una micro-oportunidad temporal solo en ciudades americanas/slots concretos
- o mover la siguiente discusión hacia otro cuello pre-edge con mejor pinta de recuperabilidad real

Lo que esta auditoría sí deja cerrado es esto:

- `same-day` no debe leerse como sinónimo de `recuperable`
- y hoy no hay evidencia para vender `tiempo` como la palanca general más prometedora
