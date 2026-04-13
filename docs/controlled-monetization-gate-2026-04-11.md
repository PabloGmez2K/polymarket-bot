# Controlled Monetization Gate - 2026-04-11

## Objetivo

Dejar por escrito que evidencia futura haria honesto abrir una discusion de monetizacion controlada con bankroll `$25`, sin convertir esta sesion en una sesion de monetizacion ni de policy.

## Lo Que Esta Sesion Si Aporta

Sobre una base limpia y con preflight `operational` verde:

- `blocking_operational_collision_count=0`
- snapshot runtime fresco y manifestado
- `auto_canary` ya no parece puro etiquetado:
  - `4` trades reales en los ultimos `20` ciclos
  - todos en ciudades hoy `auto_canary`
  - `4/4` cerrados como `RESOLVED_WIN`
  - `PnL cerrado del tramo = +$1.69`

Eso alcanza para decir:

- el sistema vuelve a producir throughput real en el modo efectivo actual;
- ya no estamos mirando un sistema muerto o puramente declarativo.

## Lo Que Todavia No Permite Decir

Esto no alcanza para abrir todavia una discusion honesta de monetizacion controlada.

Razones:

- la muestra es minima: `4` cierres recientes es demasiado poco;
- el funnel sigue estrechado sobre todo por filtros estructurales, no por una fuente estable de edge realizable;
- `2/6` ciudades `auto_canary` no convierten nada en esta ventana (`Munich`, `New York City`);
- el throughput observado sigue siendo discontinuo: `3` ciclos con buys sobre `20` ciclos.

## Gate Propuesto Para Una Conversacion Honesta

Abrir la discusion solo si se acumula evidencia adicional del mismo sistema efectivo, sin tocar por el camino:

- `bot.py`
- `city_policy_state.json`
- thresholds
- allowlists
- bankroll
- `exact/range`

Evidencia minima sugerida:

1. Otra ventana read-only de al menos `20` ciclos adicionales con preflight `operational` verde al inicio.
2. Al menos `10` trades cerrados recientes agregados bajo el modo efectivo actual.
3. Que esos cierres no dependan de una sola ciudad, sino de varias `auto_canary`.
4. Que el throughput siga viniendo de trades reales y no solo de shadow opportunities.
5. Que no aparezca ningun bug de accounting/counters/cierre durante esa observacion extendida.

## Señales Que Si Habilitarian La Conversacion

- repeticion de trades reales en varias `auto_canary`;
- mas cierres confirmados bajo la misma politica efectiva;
- continuidad de `operational` en verde;
- persistencia de PnL positivo o al menos no contradictorio con el readout operativo, sobre una muestra menos frágil.

## Señales Que Deben Frenarla

- reapertura de `blocking_operational_collision_count > 0`;
- aparicion de drift o stale snapshot que degrade la confianza del preflight;
- evidencia de bug de correctness/accounting;
- throughput nuevo que siga siendo casi enteramente una sola ciudad o uno o dos ciclos aislados.

## Veredicto Operativo De Esta Sesion

No abrir todavia la discusion de monetizacion controlada.

Lo honesto hoy es:

- mantener observacion read-only;
- acumular muestra adicional bajo la politica efectiva actual;
- volver a evaluar solo cuando exista una base menos fragil que `4` cierres recientes.
