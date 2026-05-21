# Trader vs Bot Gap Alert Severity Contract

Fecha: 2026-05-21
Decision Opus: `SPLIT_ACTION_LEVELS`
Scope: alarma diaria trader-vs-bot gap.

Este documento fija el contrato de severidad para evitar que una brecha real
trader-only se eleve a `ACTION` cuando la fuente o el mapping aun no permiten
una decision operativa segura. No autoriza cambios de codigo, city modes,
whitelist, canary, source unlock, env vars, DB, BANKROLL ni Fase C.

## Principios

- Primero se separa magnitud del gap y readiness de fuente.
- `ACTION` queda reservado para casos con magnitud suficiente y fuente lista.
- Las ciudades con fuente incompleta pueden requerir observacion, no decision
  operativa automatica.
- El estado `MAPPING_MISSING` o `no_icao` bloquea siempre `ACTION`.

## Niveles

### INFO

Uso:

- Menos de 2 senales trader operables, o evidencia de 1 solo dia.
- Cualquier estado de fuente.

Accion:

- Log only.
- No notifica.
- No abre tarea Opus.

### WATCH_SOURCE

Uso:

- Gap trader-only operable real, pero sin cumplir gates de magnitud.
- O fuente bloqueada/incompleta:
  - `MAPPING_MISSING`
  - `no_icao`
  - ciudad sin `OBSERVED_AUDIT_CITIES` cuando ese seguimiento sea requisito

Accion:

- Notificacion de baja prioridad.
- No abre tarea Opus automaticamente.
- No implica source unlock, mapping patch, whitelist, canary ni cambio de modo.

### WATCH

Uso:

- Gates de magnitud cumplidos.
- Mapping listo.
- Ciudad fuera de `active`/`canary`.

Accion:

- Candidato a observacion extendida.
- No abre por si mismo una decision operativa inmediata.

### ACTION

Uso:

- Gates de magnitud cumplidos.
- Mapping listo.
- Ciudad en `active`/`canary`, o ciudad en `OBSERVED_AUDIT_CITIES` con ciclo
  limpio.

Accion:

- Abre tarea Opus de decision operativa.
- La tarea Opus decide si procede patch posterior; la alarma no muta runtime.

## Gates de magnitud

Una ciudad puede subir de `INFO` a `WATCH_SOURCE`, `WATCH` o `ACTION` si cumple
al menos uno de estos gates en la ventana evaluada:

- Al menos 3 dias distintos con gap trader-only operable en ventana de 14 dias.
- `n >= 5` senales trader operables `at_or_above`/`at_or_below`, excluyendo
  `range`, con consenso de al menos 2 traders.
- `shadow_city_tracking.markets_seen >= 15` y
  `shadow_city_tracking.edge_hits >= 1`.

Estos gates miden magnitud. No sustituyen el requisito de source readiness para
`WATCH` o `ACTION`.

## Regla dura

Ninguna ciudad con `source_onboarding = MAPPING_MISSING` o `no_icao` puede
emitir `ACTION`, aunque exista gap trader-only real.

En esos casos la severidad maxima permitida es `WATCH_SOURCE` hasta que un
patch posterior, aprobado de forma separada, resuelva el mapping/fuente y deje
evidencia limpia.

## Ejemplo: San Francisco

Caso observado:

- Gap trader-only real.
- 3 senales trader detectadas.
- Solo 2 senales operables.
- `source_onboarding = MAPPING_MISSING` / `no_icao`.
- `shadow_city_tracking.cycles_seen = 1`.
- `shadow_city_tracking.markets_seen = 3`.
- `shadow_city_tracking.edge_hits = 0`.

Clasificacion correcta:

- `WATCH_SOURCE`.

Razon:

- Hay gap real, pero no hay magnitud suficiente para `WATCH`/`ACTION`.
- El mapping/fuente no esta listo.
- La regla dura impide `ACTION` con `MAPPING_MISSING` o `no_icao`.

Decision explicita para San Francisco hoy:

- No source unlock.
- No mapping patch.
- No whitelist.
- No canary.
- No cambio de city modes.
- No tarea Opus automatica de decision operativa por esta alarma.

## Siguiente patch recomendado

Implementar despues, como cambio separado, la reclasificacion de la alarma
diaria para aplicar `SPLIT_ACTION_LEVELS`:

- Calcular primero gates de magnitud.
- Separar source readiness de magnitud.
- Forzar `WATCH_SOURCE` cuando exista `MAPPING_MISSING` o `no_icao`.
- Emitir `ACTION` solo si los gates y la readiness cumplen el contrato.
- Cubrir el caso San Francisco como fixture/regresion.
