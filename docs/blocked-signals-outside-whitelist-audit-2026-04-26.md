# Blocked Signals Outside Whitelist Audit - 2026-04-26

Scope: auditoria operativa read-only del `ACTION` diario `Blocked signals (fuera de whitelist)`. No cambia `bot.py`, whitelist, NOAA, scheduler, sizing, Railway ni reglas core.

## Fuente live

Comando usado: lectura remota read-only de `/app/data/blocked_signals_resolutions.jsonl` en Railway `polymarket-bot`.

- `QUALITY_TRADER_CITIES_WHITELIST` live: coincide con el default actual hasta `Dallas`.
- `BLOCKED_CITIES` live: `London`.
- JSONL live: `381` registros, todos resueltos.
- Fuera de whitelist: `101` resueltos, `100` wins, WR `99.0%`.
- Excluidos por whitelist: `280`.

## Ranking fuera de whitelist

| Rank | Ciudad | Resueltas | Wins | WR | Consenso | Condiciones | Estado config | Shadow live | Observed live | Lectura |
|---:|---|---:|---:|---:|---:|---|---|---|---:|---|
| 1 | Lucknow | 19 | 19 | 100.0% | 7/7 | exact 19 | `RESOLUTION_ICAO=VILK`, `RESOLUTION_STATIONS` y timezone; no whitelist; si `OBSERVED_AUDIT_CITIES`; sin NOAA ids | `edge_hits=8`, `best_edge=47.4%`, `cycles=6`, last seen Apr 22 | 0 | Mejor candidata cuantitativa, pero requiere verificacion de fuente/ICAO-only antes de whitelist/canary. |
| 2 | Warsaw | 17 | 17 | 100.0% | 8/8 | exact 17 | `RESOLUTION_ICAO=EPWA`, station y timezone; no whitelist; no observed; sin NOAA ids | `edge_hits=0`, `cycles=7`, last seen Apr 26 | 0 | Candidata fuerte por traders y persistencia; cuello claro: cobertura/fuente, no regla core. |
| 3 | Chongqing | 16 | 16 | 100.0% | 2/2 | exact 16 | `RESOLUTION_ICAO=ZUCK`, station y timezone; no whitelist; no observed; sin NOAA ids | `edge_hits=1`, `best_edge=28.8%`, `cycles=2`, last seen Apr 21 | 0 | Buena muestra trader, pero muestra bot corta y fuente ICAO-only pendiente. |
| 4 | Beijing | 14 | 14 | 100.0% | 4/4 | exact 14 | `RESOLUTION_ICAO=ZBAA`, station y timezone; no whitelist; no observed; sin NOAA ids | `edge_hits=5`, `best_edge=37.9%`, `cycles=20`, last seen Apr 26 | 0 | Candidata operacionalmente interesante: ya tiene edge bot y muestra trader; falta cobertura observada/fuente. |
| 5 | Buenos Aires | 7 | 7 | 100.0% | 0/0 | exact 7 | `SAEZ` + NOAA ids, no whitelist, si observed | `edge_hits=0`, `cycles=10`, last seen Apr 15 | 0 | Menos urgente por falta de consenso y edge; revisar starvation observed antes de whitelist. |
| 6 | Lagos | 7 | 7 | 100.0% | 0/0 | exact 7 | Sin `RESOLUTION_ICAO`, station ni timezone | `edge_hits=0`, `cycles=5`, last seen Apr 19 | 0 | No preparar whitelist: primero discovery de fuente/resolucion. |

Resto con muestra menor: `Guangzhou 6/6`, `Karachi 4/4`, `Cape Town 3/3`, `Los Angeles 2/2`, y ciudades de n=1. Sirven como watchlist, no como primer lote.

## Decision Codex

No tocar reglas core. No abrir whitelist masiva.

El siguiente bloque logico es un paquete de verificacion de fuente/cobertura para 4 ciudades, en este orden:

1. `Lucknow`: confirmar fuente de resolucion Polymarket/WU `VILK`, documentar que sigue ICAO-only o encontrar NOAA id util; si cierra, candidata a `preparar whitelist/canary`.
2. `Warsaw`: confirmar `EPWA` y motivo actual de no-observed; si cierra, candidata fuerte por consenso `8/8` y persistencia `TRADER_ONLY`.
3. `Beijing`: confirmar `ZBAA` y cobertura; es la mas interesante para Codex porque ya tiene `edge_hits=5`.
4. `Chongqing`: confirmar `ZUCK`; mantener detras de Beijing porque el bot tiene poca muestra (`cycles=2`).

`Buenos Aires` queda en backlog, pero no lidera el `ACTION`: tiene buena fuente configurada, pero sin consenso, sin edge y con `observed_vs_forecast=0`. Eso apunta a revisar cola/cobertura live, no a whitelist inmediata.

`Lagos` no se debe mover sin discovery previo: hoy no tiene ninguna estructura base en `bot.py`.

## Delegacion recomendada

Codex puede continuar con el siguiente paso si la tarea es repo/local: crear un readout de fuente por ciudad y preparar un patch solo si la verificacion es clara.

Delegar a Sonnet si se quiere una segunda lectura rapida del ranking y del gate antes de tocar whitelist.

Delegar a Opus si aparece una decision de criterio: aceptar nuevas ciudades ICAO-only en canary, cambiar el estandar de `OBSERVED_AUDIT_CITIES`, o ampliar `QUALITY_TRADER_CITIES_WHITELIST` pese a `observed_vs_forecast=0`.

## Cierre operativo

La alarma no dice "tradear ya". Dice: el alpha de exact/range fuera de whitelist es muy fuerte y ya se puede convertir en auditoria por ciudad. El primer trabajo accionable no es `Buenos Aires/Miami/Warsaw`; es fuente/cobertura para `Lucknow`, `Warsaw`, `Beijing` y `Chongqing`.

## Readout fuente/cobertura - continuacion Codex

Fecha de comprobacion: 2026-04-26. Lecturas read-only: `bot.py`, docs de contrato NOAA, Railway `/app/data/audit.json`, `/app/data/shadow_city_tracking.json`, `/app/data/blocked_signals_resolutions.jsonl`, paginas Polymarket Apr-26 y HTTP HEAD contra NOAA/NCEI `global-hourly/access/2026`.

### Evidencia comun

- Polymarket Apr-26 confirma fuente Wunderground/ICAO para las cuatro estaciones:
  - `Lucknow` -> Chaudhary Charan Singh Intl Airport, `https://www.wunderground.com/history/daily/in/lucknow/VILK`.
  - `Warsaw` -> Warsaw Chopin Airport, `https://www.wunderground.com/history/daily/pl/warsaw/EPWA`.
  - `Beijing` -> Beijing Capital International Airport, `https://www.wunderground.com/history/daily/cn/beijing/ZBAA`.
  - `Chongqing` -> Chongqing Jiangbei International Airport, `https://www.wunderground.com/history/daily/cn/chongqing/ZUCK`.
- `bot.py` ya tiene `RESOLUTION_STATIONS`, `RESOLUTION_ICAO` y `CITY_TIMEZONES` para las cuatro.
- Ninguna de las cuatro tiene `noaa_station_id` ni `noaa_daily_station_id` en `RESOLUTION_ICAO`.
- `OBSERVED_AUDIT_CITIES`: solo `Lucknow` esta incluida; `Warsaw`, `Beijing` y `Chongqing` no.
- Live `/app/data/audit.json`: `observed_vs_forecast=0` para las cuatro.
- NOAA/NCEI global-hourly 2026 devuelve `404` para los ISD comentados en `bot.py`:
  - `ZBAA` -> `54511099999`
  - `EPWA` -> `12375099999`
  - `ZUCK` -> `57516099999`
  - `VILK` -> `42369099999`

### Cierre por ciudad

| Ciudad | Fuente Polymarket/WU | Cobertura NOAA/live | Evidencia operativa | Cierre |
|---|---|---|---|---|
| Lucknow | Confirmada `VILK` / Chaudhary Charan Singh Intl. | ICAO-only; en `OBSERVED_AUDIT_CITIES`, pero `observed_vs_forecast=0`; ISD 2026 `42369099999` = 404. | Blocked live `19/19`, consenso `7`, exact-only; shadow `edge_hits=8`, `best_edge_pct=47.4`, `cycles_seen=6`, `markets_seen=13`. | `preparar whitelist-canary` solo como propuesta ICAO-only; requiere Opus por criterio `observed_vs_forecast=0`. |
| Warsaw | Confirmada `EPWA` / Warsaw Chopin. | ICAO-only; no esta en `OBSERVED_AUDIT_CITIES`; `observed_vs_forecast=0`; ISD 2026 `12375099999` = 404. | Blocked live `17/17`, consenso `8`, exact-only; shadow `edge_hits=0`, `cycles_seen=7`, `markets_seen=15`. | `seguir acumulando muestra`; no preparar canary local sin resolver criterio ICAO-only y sin edge bot. |
| Beijing | Confirmada `ZBAA` / Beijing Capital. | ICAO-only; no esta en `OBSERVED_AUDIT_CITIES`; `observed_vs_forecast=0`; ISD 2026 `54511099999` = 404. | Blocked live `14/14`, consenso `4`, exact-only; shadow `edge_hits=5`, `best_edge_pct=37.9`, `cycles_seen=20`, `markets_seen=42`. | `preparar whitelist-canary` solo como propuesta ICAO-only; requiere Opus por criterio `observed_vs_forecast=0`. |
| Chongqing | Confirmada `ZUCK` / Chongqing Jiangbei. | ICAO-only; no esta en `OBSERVED_AUDIT_CITIES`; `observed_vs_forecast=0`; ISD 2026 `57516099999` = 404. | Blocked live `16/16`, consenso `2`, exact-only; shadow `edge_hits=1`, `best_edge_pct=28.8`, `cycles_seen=2`, `markets_seen=4`. | `seguir acumulando muestra`; fuente no rota, pero muestra bot corta. |

No hay `bloqueo por fuente` para ninguna de las cuatro: la fuente de settlement Polymarket/WU coincide con el ICAO declarado. El bloqueo seria excesivo; el cuello real es si el sistema acepta canary/whitelist ICAO-only con NOAA observado en cero.

## Handoff Opus - decision ICAO-only / observed_vs_forecast=0

### Pregunta

Para ciudades con fuente Polymarket/WU verificada y alpha blocked exact/range fuerte, pero sin `noaa_station_id` util y con `observed_vs_forecast=0`, decidir si se permite una promocion controlada a whitelist/canary ICAO-only.

### Candidatas que plantean la decision

1. `Lucknow`: mejor candidata cuantitativa (`19/19`, consenso `7`, shadow `edge_hits=8`, `best_edge_pct=47.4`), pero solo WU/ICAO y sin observado NOAA pese a estar en `OBSERVED_AUDIT_CITIES`.
2. `Beijing`: candidata operacional (`14/14`, consenso `4`, shadow `edge_hits=5`, `cycles_seen=20`), pero solo WU/ICAO y fuera de `OBSERVED_AUDIT_CITIES`.

### No candidatas inmediatas

- `Warsaw`: fuente confirmada y blocked `17/17`, pero `edge_hits=0`; mantener en muestra hasta que haya edge bot o gap operativo mas claro.
- `Chongqing`: fuente confirmada y blocked `16/16`, pero solo `cycles_seen=2` y `edge_hits=1`; mantener en muestra.

### Decision requerida

Opus debe elegir uno de estos criterios antes de patch:

1. Permitir canary ICAO-only con sizing reducido si la fuente Polymarket/WU esta verificada y blocked exact/range + shadow edge superan umbrales, aceptando que `observed_vs_forecast` no validara WR NOAA.
2. Exigir `noaa_station_id`/`noaa_daily_station_id` o filas `observed_vs_forecast` antes de cualquier whitelist/canary nueva.
3. Crear una categoria intermedia: whitelist de lectura/trader-only sin BUY real hasta que NOAA vuelva o exista proxy observado alternativo.

Patch local solo despues de esa decision: como maximo tocaria whitelist/canary config y, si aplica, `OBSERVED_AUDIT_CITIES` para formalizar seguimiento; no tocar trading core, NOAA core, scheduler ni reglas.
