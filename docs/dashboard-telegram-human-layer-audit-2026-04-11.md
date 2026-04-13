# Dashboard + Telegram Human-Layer Audit - 2026-04-11

## Alcance

Auditoria read-only de la capa humana contra la capa canonica actual.

- sin tocar `bot.py`
- sin escribir `city_policy_state.json`
- sin tocar policy live, thresholds, allowlists, bankroll ni `exact/range`

## Preflight canonico

- `python tools/system_alignment_check.py` -> `ok=7`, `warning=1`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7`, `warning=1`, `error=0`
- `blocking_operational_collision_count=0`

Base canonica usada para comparar:

- `runtime_policy_effective_view_latest.md`: `blocked=10`, `canary=6`, `shadow=14`, `active=0`
- `system_alignment_check_latest.md` y `system_alignment_check_operational_latest.md`: base verde; el unico warning restante es drift explicitado, no blocker
- `step5-throughput-observation-extended-2026-04-11.md`: ventana de `20` ciclos con `raw_markets_fetched ~330`, `candidates_after_prefilters=307`, `condition_filtered_out=285`, `trades_executed=4`, `shadow_opportunities_observed=2`
- `throughput-observation-readout-followup-2026-04-11.md`: no hay ciclos nuevos; el siguiente paso sigue siendo observacion, no correctness ni policy

## Dashboard

### Alineado

- La accion principal no empuja monetizacion ni cambios de trading; el framing de "no tocar trading" sigue siendo compatible con el guardrail actual.
- No presenta el sistema como listo para expansion ni como base suficiente para policy.

### No alineado

1. La historia factual de modos por ciudad no coincide con la effective view canonica.
   - Snapshot local del dashboard: `active_count=4` y ciudades activas `Atlanta`, `Buenos Aires`, `Chicago`, `Dallas`
   - Capa canonica: `active_effective_count=0`; canary efectivas `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`; `Chicago`, `Buenos Aires` y `Dallas` quedan `shadow`
   - Importancia operacional: la UI esta contando otra topologia de riesgo/tradabilidad.

2. El dashboard cuenta una historia de throughput vacio que contradice la foto runtime manifestada.
   - Snapshot local del dashboard: `cycle_summary_scan=null`, `0` shadow recientes, `0` cierres, "sin ciclo registrado todavia"
   - Capa canonica: la observacion extendida ya documenta `20` ciclos manifestados, `4` buys reales y `4` cierres `RESOLVED_WIN`
   - Importancia operacional: empuja a leer "no hay actividad" cuando la verdad canonica es "si hay actividad, pero la muestra nueva aun no alcanza para otra conclusion"

3. El wording del funnel en la plantilla sigue mezclando capas que el contrato ya separo.
   - `templates/dashboard.html` rotula `markets_evaluated` como "Mercados escaneados"
   - `metrics-funnel-naming.md` fija que `markets_evaluated` es alias legacy de `candidates_after_prefilters`, no de `raw_markets_fetched`
   - Importancia operacional: el bloque puede hacer creer que el bot vio pocos mercados brutos, cuando esa cifra ya es post-filtros

4. `Road to Real` y parte de la guia siguen anclados a una narrativa anterior.
   - `docs/guia-lectura-dashboard.md` sigue hablando de "volver a operar con dinero real", promociones y readiness como marco principal
   - La capa canonica actual fija otra prioridad: preflight verde, observacion honesta, y auditoria de lectura humana sin mezclar monetizacion/policy
   - Importancia operacional: no rompe datos por si solo, pero sesga la lectura hacia una conversacion que hoy no toca

## Telegram

### Alineado

- `docs/city_intelligence_alert_latest.md` no dispara una alerta falsa; al menos no introduce una accion incorrecta nueva.

### No alineado

1. El resumen diario esta stale respecto de la capa canonica actual.
   - `docs/city_intelligence_daily_summary_latest.md` fue generado el `2026-04-10T14:33:45+00:00`
   - Sigue diciendo `runtime_inputs_missing` y que `city-intelligence` no tiene acceso al runtime del bot
   - La capa canonica usada hoy para decidir ya no esta ahi: `runtime_manifest` bijectivo y fresco, `runtime_ledger` disponible, preflight `observe/operational` en verde
   - Importancia operacional: Telegram sigue explicando el sistema desde un cuello ya superado en la capa canonica usada para esta fase

2. El daily summary manda a repetir una accion ya cerrada.
   - Instruccion actual: "Validar el transporte read-only del runtime y su manifest"
   - Estado canonico actual: ese transporte ya esta validado y es la base de sesiones `141-143`
   - Importancia operacional: la recomendacion ya no ayuda a decidir el siguiente paso real

3. La capa Telegram no refleja el frente actual.
   - No menciona `effective_mode`, `blocking_operational_collision_count=0`, ni el veredicto actual de "observacion siguiente, no correctness"
   - Tampoco refleja que el drift nuevo vive en la lectura humana misma
   - Importancia operacional: la historia esta atrasada una fase completa

## Veredicto

La capa humana no esta alineada hoy con la capa canonica.

- El dashboard tiene drift de correctness de lectura: modos, universo activo y throughput visible no coinciden con la effective view ni con los readouts runtime manifestados.
- Telegram tiene drift de staleness: el daily summary sigue describiendo un estado pre-runtime-import estable.
- El problema principal ya no es copy cosmetico; es que la lectura humana se apoya en fuentes o contratos distintos de los que hoy usamos como canon.

## Siguiente paso recomendado

`correctness de lectura` primero.

Antes de una sesion de copy/UI, conviene reanclar Dashboard y Telegram a la misma fuente canonica que hoy manda:

- `runtime_policy_effective_view`
- `system_alignment_check`
- `runtime_import/*`
- naming canonico del funnel

Luego si, una pasada corta de copy/UI para limpiar wording legacy (`Road to Real`, promociones, `mercados escaneados`) y dejar la capa humana contando exactamente la historia correcta.
