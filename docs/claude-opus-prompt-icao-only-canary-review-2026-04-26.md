# Prompt para Opus - decision ICAO-only canary

## Contexto

Repo: `polymarket-bot`.

Fecha: 2026-04-26.

Codex cerro una auditoria read-only del `ACTION` diario `Blocked signals (fuera de whitelist)`.
No se toco `bot.py`, whitelist, NOAA core, scheduler, sizing, Railway env ni reglas de trading.

Documento base:

- `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md`

## Tarea para Opus

Decidir criterio operativo para ciudades con:

- fuente Polymarket/WU verificada via ICAO;
- alpha fuerte en blocked signals exact/range fuera de whitelist;
- `observed_vs_forecast=0`;
- sin `noaa_station_id` / `noaa_daily_station_id` util en 2026.

La pregunta no es si la fuente esta rota. La fuente Polymarket/WU esta confirmada. La pregunta es si se puede abrir un canary ICAO-only controlado sin evidencia NOAA observada.

## Evidencia factual

Polymarket Apr-26 confirma Wunderground/ICAO:

- `Lucknow` -> `VILK`, Chaudhary Charan Singh Intl.
- `Warsaw` -> `EPWA`, Warsaw Chopin.
- `Beijing` -> `ZBAA`, Beijing Capital.
- `Chongqing` -> `ZUCK`, Chongqing Jiangbei.

Repo/local:

- Las cuatro tienen `RESOLUTION_STATIONS`, `RESOLUTION_ICAO` y `CITY_TIMEZONES`.
- Ninguna tiene `noaa_station_id` ni `noaa_daily_station_id`.
- Solo `Lucknow` esta en `OBSERVED_AUDIT_CITIES`.

Railway live:

- `/app/data/audit.json`: `observed_vs_forecast=0` para las cuatro.
- `/app/data/shadow_city_tracking.json`:
  - `Lucknow`: `edge_hits=8`, `best_edge_pct=47.4`, `cycles_seen=6`, `markets_seen=13`.
  - `Beijing`: `edge_hits=5`, `best_edge_pct=37.9`, `cycles_seen=20`, `markets_seen=42`.
  - `Warsaw`: `edge_hits=0`, `cycles_seen=7`, `markets_seen=15`.
  - `Chongqing`: `edge_hits=1`, `best_edge_pct=28.8`, `cycles_seen=2`, `markets_seen=4`.

Blocked signals live:

- `Lucknow`: `19/19`, consenso `7`, exact-only.
- `Warsaw`: `17/17`, consenso `8`, exact-only.
- `Beijing`: `14/14`, consenso `4`, exact-only.
- `Chongqing`: `16/16`, consenso `2`, exact-only.

NOAA/NCEI `global-hourly/access/2026`:

- `ZBAA` / `54511099999` -> 404.
- `EPWA` / `12375099999` -> 404.
- `ZUCK` / `57516099999` -> 404.
- `VILK` / `42369099999` -> 404.

## Decision requerida

Elegir una politica antes de cualquier patch:

1. Permitir canary ICAO-only con sizing reducido si fuente Polymarket/WU esta verificada y la evidencia blocked + shadow supera umbrales.
2. Exigir `noaa_station_id`/`noaa_daily_station_id` o filas `observed_vs_forecast` antes de cualquier whitelist/canary nueva.
3. Crear estado intermedio: seguimiento formal o whitelist de lectura/trader-only sin BUY real hasta tener NOAA o proxy observado alternativo.

## Recomendacion preliminar de Codex

Si Opus acepta canary ICAO-only, limitar el primer patch a:

1. `Lucknow` - mejor evidencia combinada: `19/19`, consenso `7`, shadow `edge_hits=8`.
2. `Beijing` - mejor caso operacional: shadow `edge_hits=5`, `cycles_seen=20`, blocked `14/14`.

No incluir todavia:

- `Warsaw`: blocked fuerte pero `edge_hits=0`.
- `Chongqing`: fuente OK pero muestra bot corta (`cycles_seen=2`, `edge_hits=1`).

## Guardrails

- No tocar trading core.
- No tocar NOAA core.
- No tocar scheduler.
- No tocar reglas de entrada/salida.
- No usar `BLOCKED_CITIES` como pausa operativa.
- Si hay patch posterior, que sea minimo y explicito: whitelist/canary/config observability segun la decision de politica.
