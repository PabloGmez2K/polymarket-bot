# Trader/Bot Review Backlog - 2026-04-26

Scope: backlog operativo read-only para el parte diario `traders vs bot` y `blocked signals` de `2026-04-26 UTC`. No cambia `bot.py`, whitelist, NOAA, scheduler, sizing, Railway ni reglas core.

## Fuente de la decision

- Parte Telegram 2026-04-26: `MATCH=23`, `BOT_ONLY=5`, `TRADER_ONLY=12`, nivel `WATCH`.
- Serie reciente reportada: 7 corridas, medianas `MATCH=19`, `BOT_ONLY=5`, `TRADER_ONLY=19`.
- Persistentes `TRADER_ONLY` en `7/7`: `Buenos Aires`, `Miami`, `Warsaw`.
- Casi persistentes `6/7`: `Chengdu`, `Lagos`.
- No hay gap operativo real hoy: los `TRADER_ONLY` actuales estan blocked o sin consenso/condicion operable.
- `Blocked signals` fuera de `QUALITY_TRADER_CITIES_WHITELIST`: 101 resueltas, 100 wins, WR 99.0%; excluidas por whitelist: 280. Nivel `ACTION`, pero solo para auditoria por ciudad/fuente/cobertura, no para tocar reglas core.

Nota de higiene: los artefactos locales de `docs/signals_crosscheck_daily_summary_latest.md` siguen stale frente al parte live pegado por el usuario, asi que este backlog usa el parte 2026-04-26 como fuente operativa y el repo local solo para configuracion.

## Gate de ejecucion

No ejecutar cambios por persistencia sola.

Una ciudad entra a auditoria concreta solo si aparece tambien como gap operativo real:

- fuera de `blocked`;
- con consenso trader o muestra trader fuerte;
- con condicion operable para el bot, o con evidencia `exact/range` suficiente para evaluar canary;
- con fuente de resolucion verificable antes de cualquier cambio de whitelist/canary.

Salidas permitidas por ciudad:

- `sin cambio`;
- `preparar whitelist/canary`;
- `bloqueo por fuente`;
- `seguir acumulando muestra`.

## Backlog por ciudad

| Prioridad | Ciudad | Estado repo actual | Hallazgo | Siguiente accion cuando haya gap real |
|---|---|---|---|---|
| P1 | Buenos Aires | No esta en `QUALITY_TRADER_CITIES_WHITELIST`; si esta en `OBSERVED_AUDIT_CITIES`; `RESOLUTION_ICAO` tiene `SAEZ`, `noaa_station_id=87576099999`, `noaa_daily_station_id=ARM00087576`. | La falta principal no parece ser fuente configurada, sino whitelist/cobertura efectiva: el `audit.json` local tiene `observed_vs_forecast=0` para la ciudad pese a estar configurada. En el JSONL local stale de blocked signals aparece fuera de whitelist con `2/2` wins. | Revisar live `audit.json` y `shadow_city_tracking` para confirmar si sigue sin muestra observada. Si hay gap real y fuente/cobertura live cierran, preparar decision `whitelist/canary`; si la cobertura sigue en cero, priorizar primero el motivo de starvation NOAA. |
| P2 | Miami | Esta en `QUALITY_TRADER_CITIES_WHITELIST`; esta en `OBSERVED_AUDIT_CITIES`; `RESOLUTION_ICAO` tiene `KMIA`, `noaa_station_id=72202012839`, `noaa_daily_station_id=USW00012839`. | No es un problema de whitelist. El snapshot live reciente la deja shadow y el local tiene 3 filas `observed_vs_forecast`; si sigue `TRADER_ONLY`, el cuello probable es que el bot no esta generando edge, no que falte permiso. Las senales locales stale eran `range` sin consenso y quedan excluidas del baseline fuera de whitelist. | Cuando aparezca gap real, auditar `shadow_city_tracking`/edge y filtros de mercado para entender por que whitelist+cobertura no producen `MATCH`. No abrir cambio de whitelist; cerrar como `sin cambio` salvo evidencia nueva de fuente o edge. |
| P3 | Warsaw | No esta en `QUALITY_TRADER_CITIES_WHITELIST`; no esta en `OBSERVED_AUDIT_CITIES`; `RESOLUTION_ICAO` tiene `EPWA` solo con WU/ICAO. | Caso mas claro de cobertura incompleta: esta mapeada, pero sin NOAA observado activo. El comentario del repo dice que EPWA tiene ISD confirmado pero sin TMAX local reciente; el JSONL local stale muestra `4` blocked signals fuera de whitelist con WR `50%`, insuficiente para promover por ciudad aunque el agregado live sea muy alto. | Antes de whitelist, verificar fuente Polymarket/WU y si sigue siendo ICAO-only. Si hay gap real con consenso, cerrar con `preparar whitelist/canary ICAO-only` solo si la evidencia trader actual lo justifica; si no, mantener `seguir acumulando muestra` o `bloqueo por fuente`. |

## Cola ACTION para blocked signals fuera de whitelist

El agregado `101/100` pide priorizacion, pero no identifica por si solo que ciudad debe moverse. La auditoria debe empezar por ranking city-level, no por cambiar reglas de entrada:

1. Pull/read del JSONL live de blocked signals o del readout diario equivalente.
2. Filtrar `city not in QUALITY_TRADER_CITIES_WHITELIST`.
3. Rankear por `resolved_count` desc, luego WR, separando consenso vs solo.
4. Para cada top city: confirmar whitelist, `RESOLUTION_ICAO`, `OBSERVED_AUDIT_CITIES`, cobertura `observed_vs_forecast` y fuente de resolucion Polymarket/WU/NOAA.
5. Solo si una top city tambien aparece como gap operativo real, preparar patch de whitelist/canary o documentar bloqueo por fuente.

En los artefactos locales stale, entre las tres ciudades de este backlog, `Warsaw` tiene la mayor muestra fuera de whitelist (`4`, WR `50%`), `Buenos Aires` tiene `2/2`, y `Miami` no cuenta porque ya esta en whitelist. Esto no sustituye el ranking live del 2026-04-26.

## Auditoria live asociada

La auditoria live read-only queda en `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md`.

Resultado principal: el `ACTION` fuera de whitelist no lo lideran las tres ciudades del backlog WATCH, sino `Lucknow`, `Warsaw`, `Chongqing` y `Beijing`. `Buenos Aires` baja prioridad por falta de consenso/edge y `Miami` no aplica porque ya esta en whitelist.
