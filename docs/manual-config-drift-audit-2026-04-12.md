# Manual Config Drift Audit - 2026-04-12

## Closure Checkpoint - 2026-04-12

Estado actual tras el bloque de cierre posterior:

- `tools/reference_trader_city_market_cross.py` ya no usa `legacy_bot_lists`; cae a `runtime_policy_effective_view` y, si falta ciudad, al default canónico `shadow`.
- los fósiles `normal_pull_check/final_check` ya no están en `data/runtime_import_derived/`
- `python tools/system_alignment_check.py --decision-mode operational` sigue cerrando con `error=0`

Lectura de cierre:

este audit ya no debe leerse como módulo abierto. Queda como artefacto de transición que explica el drift encontrado y la lógica de limpieza, pero sus dos deudas técnicas principales ya quedaron resueltas.

## Preflight

Base de trabajo validada antes de auditar:

- `python tools/runtime_policy_effective_view.py`
- `python tools/system_alignment_check.py` -> `ok=6`, `warning=2`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=6`, `warning=2`, `error=0`

## Inventario Corto

### 1. `DEFAULT_ACTIVE_CITIES = ""` en `tools/runtime_policy_effective_view.py`

Estado: `alineada`

Evidencia:

- el fallback viejo `Dallas` ya fue limpiado en `docs/dallas-claim-readout-2026-04-11.md`
- hoy el tool deja `active_cities: []` y `active_effective_count: 0`
- evita volver a fabricar una verdad declarativa `active` cuando runtime efectivo dice otra cosa

Lectura:

este fallback ya migro correctamente a la semantica canonica actual: sin snapshot/env explicito, no se inventa `active`.

### 2. `DEFAULT_CANARY_CITIES = ""` en `tools/runtime_policy_effective_view.py`

Estado: `alineada`

Evidencia:

- el tool deja `canary_cities: []`
- las ciudades hoy `canary` salen de `city_policy_state.auto_canary_cities`, no de una lista manual local
- `runtime_policy_effective_view_latest.md` muestra `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo` y `Atlanta`/`Tokyo` via runtime, no via env local

Lectura:

correcto que `canary` viva en overlay runtime y no en fallback manual local.

### 3. `DEFAULT_BLOCKED_CITIES` en `tools/runtime_policy_effective_view.py`

Estado: `alineada`, con deuda de explicacion por ciudad

Lista viva actual:

- `London, Miami, Seattle, Paris, Tel Aviv, Wellington, Toronto, Madrid, Singapore, Ankara`

Evidencia:

- `runtime_policy_effective_view_latest.md` deja las 10 como `effective_mode=blocked`
- ninguna de esas 10 tiene `runtime_policy_mode` que las contradiga
- la regla canonica de `AGENTS.md` y `docs/ESTRATEGIA_OPERATIVA.md` reserva `blocked` para ciudades con problema estructural de fuente/resolucion, no para pausa tactica
- `city_validation_ledger.runtime_import.json` sigue tratando varias de estas ciudades con `recommendation=observe_with_source_caution` o `insufficient_evidence`, nunca como candidatas operables

Lectura:

`BLOCKED_CITIES` hoy sigue siendo defendible como guardrail manual de seguridad estructural. No compite con runtime; manda solo donde no hay auto-policy y evita que una ciudad entre por default shadow cuando el criterio historico es "no operar/no observar por fiabilidad de fuente".

Reserva importante:

la lista es operativamente coherente, pero la justificacion actual no esta centralizada ciudad por ciudad en un artefacto corto. O sea: la semantica esta alineada; la trazabilidad fina aun no.

### 4. `ACTIVE_TRADING_CITIES`

Estado: `fosil` como fuente de verdad; `alineada` solo como input opcional

Evidencia:

- `docs/system-alignment-artifact-map-2026-04-11.md` fija que la pregunta correcta es `effective_mode`, no `ACTIVE_TRADING_CITIES` a pelo
- `docs/decision-preflight-rules-2026-04-11.md` explicita que `ACTIVE_TRADING_CITIES` no autoriza lectura operativa por si solo
- la effective view actual tiene `active_effective_count: 0`
- el bug Dallas vino exactamente de tratar `ACTIVE_TRADING_CITIES` como verdad declarativa local

Lectura:

la semantica canonica nueva ya absorbio este punto: `ACTIVE_TRADING_CITIES` puede existir como input, pero citarlo como policy real hoy seria drift fosil.

### 5. Fallback `legacy_bot_lists` en `tools/reference_trader_city_market_cross.py`

Estado: `dudosa`

Evidencia:

- el tool prioriza `runtime_policy_effective_view`, pero si una ciudad no esta ahi cae a `bot.BLOCKED_CITIES / ACTIVE_TRADING_CITIES / CANARY_TRADING_CITIES / OBSERVED_AUDIT_CITIES`
- eso produce todavia `policy_source = legacy_bot_lists` y `policy_mode = untracked` para ciudades como `Amsterdam`, `Houston`, `Istanbul`, `Moscow`, `Warsaw`
- esos modos no pertenecen al contrato canonico de cuatro modos (`blocked/shadow/canary/active`)

Lectura:

no esta rompiendo el preflight, pero sigue vivo un fallback que puede reintroducir semantica vieja fuera de la vista efectiva canónica. Es deuda de migracion, no blocker inmediato.

### 6. Artefactos `normal_pull_check/final_check` en `data/runtime_import_derived`

Estado: `fosil`

Evidencia:

- `city_validation_ledger.normal_pull_check.md` y `city_validation_ledger.final_check.md` siguen mostrando:
  - `Chicago | Policy active`
  - `Dallas | Cross policy active`
  - varias `policy_divergence` que ya no reflejan la effective view actual
- esos artefactos son de `2026-04-10`, anteriores a la limpieza de claims y a la effective view regenerada hoy

Lectura:

no mandan sobre runtime live, pero siguen contando una historia vieja si alguien los toma como lectura vigente. Son fósiles documentales.

## Veredicto De Alineacion

Sigue alineado hoy:

- `DEFAULT_ACTIVE_CITIES = ""`
- `DEFAULT_CANARY_CITIES = ""`
- usar `BLOCKED_CITIES` como override manual de seguridad estructural
- usar `effective_mode` como lectura operativa final

No sigue alineado como fuente de verdad:

- leer `ACTIVE_TRADING_CITIES` directamente
- confiar en artefactos `normal_pull_check/final_check` para policy actual

Queda dudoso y conviene migrar:

- fallback `legacy_bot_lists` en `reference_trader_city_market_cross.py`

## BLOCKED_CITIES Con Criterio Defendible

La defensa canónica hoy no es "estas ciudades están pausadas", sino esta:

- `blocked` se usa solo para riesgo estructural de fuente/resolucion
- si solo no queremos operar una ciudad, debe quedar `shadow`, no `blocked`
- por tanto, `BLOCKED_CITIES` funciona como una lista manual de exclusión fuerte que evita observación/trading accidental en ciudades cuya lectura no queremos tratar como fiable

Con la evidencia actual:

- la lista no contradice runtime
- no hay auto-policy que la desmienta
- la effective view la resuelve de forma estable
- pero falta una ficha corta por ciudad que diga por que cada una sigue mereciendo `blocked` hoy

## Migracion Recomendada A La Semantica Canonica

1. Mantener `BLOCKED_CITIES` solo como override manual de seguridad, no como cajon de "no operar ahora".
2. Eliminar o encapsular fallbacks `legacy_bot_lists` en herramientas read-only para que devuelvan `shadow` o `unknown` solo desde la effective view, nunca desde listas heredadas de `bot.py`.
3. Regenerar o retirar artefactos `normal_pull_check/final_check` que hoy muestran policy vieja (`Chicago active`, `Dallas cross active`).
4. Crear un artefacto corto tipo `blocked-cities-rationale-latest.md` con una fila por ciudad y criterio actual.

## Siguiente Paso Limpio Recomendado

Sesion read-only dedicada a:

- regenerar/limpiar artefactos derivados que aún arrastran policy vieja
- recortar el fallback `legacy_bot_lists` en `reference_trader_city_market_cross.py`
- escribir la justificacion corta ciudad por ciudad de `BLOCKED_CITIES`

Sin tocar:

- `bot.py`
- `city_policy_state.json`
- policy live
- thresholds
- allowlists
- bankroll
- `exact/range`

## Estado De Cierre

Este audit queda cerrado como módulo.

Lo que sigue vivo después de este documento no es un frente abierto de alignment, sino backlog o deuda documental menor.

Regla de no reapertura:

- no reabrir este módulo por ciudades individuales con hallazgos nuevos
- no reabrirlo por fichas más ricas de `BLOCKED_CITIES`
- solo reabrir si vuelve a fallar `system_alignment_check.py --decision-mode operational` o aparece una contradicción real de fuente de verdad
