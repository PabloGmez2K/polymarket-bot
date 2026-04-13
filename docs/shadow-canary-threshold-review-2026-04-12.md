# Shadow Canary Threshold Review - 2026-04-12

## Objetivo

Evaluar que ciudades `shadow` tienen evidencia acumulada suficiente para justificar una revision del umbral `canary`, sin tocar `bot.py`, Railway, thresholds ni listas live.

Este documento no recomienda promover ciudades directamente. Solo separa:

- casos con base para abrir una revision del umbral;
- casos que siguen en observacion;
- casos demasiado recientes o demasiado debiles para mover la conversacion.

## Fuentes

- `docs/runtime_policy_effective_view_latest.md`
- `docs/shadow-opportunity-shortlist-2026-04-11.md`
- `docs/city_validation_ledger_latest.md`
- `data/city_validation_ledger.json`
- `data/runtime_import/shadow_city_tracking.json`
- `data/runtime_import/skip_log.jsonl`
- bloque reciente de `CONTEXTO.md`

## Criterio de esta revision

Una ciudad `shadow` merece revision de umbral `canary` solo si combina, como minimo:

1. evidencia acumulada real en `shadow` y no solo un caso aislado;
2. base estructural razonable de fuente/resolucion;
3. mercados recientes realmente visibles en el funnel;
4. una lectura en la que el cuello no sea simplemente "no aparece nada" o "todo sigue muriendo por constraints basicos".

## Foto actual

Segun `docs/runtime_policy_effective_view_latest.md` tras el snapshot post-deploy:

- `blocked=3`: `London`, `Toronto`, `Singapore`
- `canary=6`: `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`
- `shadow=19`

Las cinco ciudades recien liberadas desde `blocked` a `shadow` (`Ankara`, `Paris`, `Madrid`, `Wellington`, `Tel Aviv`) no son buenas candidatas para este bloque: acaban de entrar en observacion y todavia no tienen una ventana acumulada comparable.

## Ciudades revisadas

### Dallas

Evidencia:

- `effective_mode=shadow` y `runtime=auto_shadow` en `runtime_policy_effective_view`.
- `shadow_city_tracking`: `edge_hits=8`, `cycles_seen=5`, `markets_seen=9`, `best_edge_pct=45.8`.
- `city_validation_ledger`: `source_risk=low`, `settlement_score=4`, `recommendation=insufficient_evidence`, `bottleneck=trader_discovery`.
- `skip_log` reciente: `55` skips en last10 y `55` en last12, todos `price_out_of_range`.

Lectura:

- Es la señal `shadow` repetida mas fuerte entre las ciudades hoy fuera de `auto_canary`.
- No falla por un problema estructural de fuente; falla por discovery/price.
- Ya no hay el drift operativo viejo de `Dallas active`; esa parte esta cerrada.

Veredicto:

- `SI amerita revision de umbral canary`
- No amerita aun promocion directa ni cambio live automatico.

### Chicago

Evidencia:

- `effective_mode=shadow` en `runtime_policy_effective_view`.
- `shadow_city_tracking`: `edge_hits=1`, `cycles_seen=7`, `markets_seen=16`, `best_edge_pct=35.1`.
- `city_validation_ledger`: `source_risk=low`, `settlement_score=4`, `edge=29`, `recommendation=insufficient_evidence`, `bottleneck=trader_discovery`.
- `skip_log` reciente: `209` skips en last12 y `187` en last10, dominados por `price_out_of_range`, con algo de `date_out_of_range_past` y apenas `below_min_edge=1`.
- `docs/shadow-opportunity-shortlist-2026-04-11.md` ya la dejaba como principal caso exploratorio a vigilar.

Lectura:

- Sigue siendo la ciudad `shadow` mas interesante desde el punto de vista exploratorio.
- La evidencia no es tan repetida como en `Dallas`, pero si es suficiente para reabrir la conversacion sobre umbral porque hay visibilidad real y buena base estructural.
- El cuello reciente parece ser mas `price_out_of_range` que falta total de edge.

Veredicto:

- `SI amerita revision de umbral canary`
- Sigue sin haber base para saltar directamente a `canary` en esta sesion.

### Buenos Aires

Evidencia:

- `effective_mode=shadow`.
- `shadow_city_tracking`: `edge_hits=0`, `cycles_seen=7`, `markets_seen=15`, `best_edge_pct=0.0`.
- `city_validation_ledger`: `source_risk=medium`, `settlement_score=3`, `recommendation=insufficient_evidence`.
- `skip_log` reciente: mezcla de `date_out_of_range_past`, `price_out_of_range` y algo de `condition_filtered`.

Lectura:

- Tiene visibilidad suficiente para seguir observando.
- No tiene acumulacion reciente de edge que justifique una revision de umbral ahora mismo.

Veredicto:

- `NO amerita revision de umbral canary todavia`

### Denver

Evidencia:

- `skip_log` reciente: `110` skips tanto en last10 como en last12, repartidos entre `price_out_of_range` y `date_out_of_range_past`.
- `CONTEXTO.md` documenta que `Denver` venia afectada por el bug de `CITY_TIMEZONES` y acaba de recuperar visibilidad real.
- No aparece aun con base consolidada en `city_validation_ledger.json` ni en `shadow_city_tracking.json`.

Lectura:

- La ciudad acaba de salir de un sesgo de observabilidad.
- Tiene mercado visible, pero la muestra comparable post-fix todavia es demasiado nueva para usarla como caso de revision de umbral.

Veredicto:

- `NO amerita revision de umbral canary todavia`

### Los Angeles

Evidencia:

- `skip_log` reciente: `66` skips en last12 y `55` en last10, dominados por `date_out_of_range_past`.
- `CONTEXTO.md` la incluye en el grupo afectado por el bug de timezone ya corregido.
- Tampoco aparece todavia con trayectoria consolidada en `city_validation_ledger.json` ni `shadow_city_tracking.json`.

Lectura:

- Misma situacion que `Denver`: visibilidad recuperada, pero evidencia acumulada aun insuficiente.

Veredicto:

- `NO amerita revision de umbral canary todavia`

### Houston

Evidencia:

- `effective_mode=shadow`.
- `city_validation_ledger`: `visibility=6`, `edge=0`, `source_risk=high`, `settlement_score=0`, `recommendation=insufficient_evidence`.
- No aparece en `shadow_city_tracking`.
- `skip_log` reciente: `0` skips en last10 y `0` en last12.

Lectura:

- No hay ni edge acumulado ni mercado reciente suficiente para sostener una revision de umbral.

Veredicto:

- `NO amerita revision de umbral canary`

### San Francisco

Evidencia:

- `effective_mode=shadow`.
- `city_validation_ledger`: `edge=0`, `source_risk=high`, `settlement_score=0`, `recommendation=insufficient_evidence`.
- No aparece en `shadow_city_tracking`.
- `skip_log` reciente: `55` skips en last12 y `44` en last10, todos `date_out_of_range_past`.

Lectura:

- Hay algo de visibilidad de mercados, pero sin edge acumulado ni base estructural suficiente para mover umbral.

Veredicto:

- `NO amerita revision de umbral canary`

### Mexico City

Evidencia:

- `effective_mode=shadow`.
- `city_validation_ledger`: `visibility=3`, `edge=0`, `source_risk=high`, `settlement_score=0`, `recommendation=insufficient_evidence`.
- No aparece en `shadow_city_tracking`.
- `skip_log` reciente: `0` skips en last10 y `0` en last12.

Lectura:

- La ciudad todavia no tiene base comparable suficiente para discutir umbral.

Veredicto:

- `NO amerita revision de umbral canary`

## Veredicto global de Bloque B

Las unicas ciudades `shadow` con evidencia suficiente para justificar una revision del umbral `canary` son:

- `Dallas`
- `Chicago`

El resto queda en dos grupos:

- `Buenos Aires`: observar mas, sin abrir revision todavia.
- `Denver`, `Los Angeles`, `Houston`, `San Francisco`, `Mexico City`: demasiado verdes o demasiado debiles para sostener la conversacion ahora.

## Implicacion operativa correcta

El siguiente paso sano no es cambiar Railway ni promover ciudades hoy. El siguiente paso sano es, si se quiere abrir Bloque B de decision, discutir si `Dallas` y `Chicago` justifican una revision acotada del umbral `canary` con la evidencia actual.

Para las cinco ciudades que acaban de pasar de `blocked` a `shadow` (`Ankara`, `Paris`, `Madrid`, `Wellington`, `Tel Aviv`), la lectura correcta hoy es observacion pura hasta que acumulen ciclos.
