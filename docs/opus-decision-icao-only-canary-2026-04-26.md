# Decision Opus - ICAO-only canary review (2026-04-26)

## TL;DR

**Decision: Opcion 3 (estado intermedio sin BUY real), via open-meteo como proxy observado.**

No se abre canary ICAO-only hoy. No se exige NOAA estricto. Se cierra el hueco de `observed_vs_forecast=0` reusando la infra de open-meteo que ya existe en el repo (`tools/sl_retrospective.py`, `tools/forecast_accuracy_audit.py`).

Lucknow y Beijing entran a observacion formal con proxy open-meteo. Promocion a canary solo cuando el proxy acumule muestra y WR alineado. Warsaw y Chongqing quedan en muestra. No se toca trading core, NOAA core, scheduler ni reglas.

## Contexto leido

- `docs/claude-opus-prompt-icao-only-canary-review-2026-04-26.md`
- `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md`
- `CONTEXTO.md` sesiones 232-250
- Memoria: `canary_active_handoff_2026_04_13.md`, `next_session_blocked_signals.md`, `r1_gates_complete.md`
- `bot.py` lineas 195-260 (whitelist/canary), 5460-5500 (gate `interpretable`), 301, 5471, 5493 (uso de `OBSERVED_AUDIT_CITIES`)
- `AGENTS.md` lineas 27-36 (modos de ciudad, requisitos de `observed_vs_forecast`)

## Por que no Opcion 1 (canary ICAO-only directo)

1. **Estado actual del sistema lo desaconseja.** `ACTIVE_TRADING_CITIES=NONE` en Railway desde sesion 173. Phase 2 de recalibracion no cerrada (`RECALIBRATION_PHASE2_CLOSED=false`). El sistema esta deliberadamente en pausa esperando recalibracion sigma. Abrir canary nuevo en este momento es ruido sobre una decision ya tomada (checkpoint 2026-04-11: "saltar directo a monetizacion seria el anti-patron que el LEAN roadmap vino a evitar").
2. **WR=100% en blocked mide al trader, no al bot.** `19/19` en Lucknow significa "el quality trader acerto"; no significa "el forecast del bot habria predicho lo mismo". El alpha esta en el trader, no en una nueva senal del bot. Confundir ambas cosas justifica trades por la razon equivocada.
3. **El gate del propio sistema lo bloquea silenciosamente.** En `bot.py:5497`, `interpretable = noaa_configured and observed_count >= OBSERVED_FORECAST_MIN_SAMPLE`. Promover una ciudad con `observed_vs_forecast=0` a canary la deja `not interpretable` aguas abajo: rompe metricas de calidad, alerts de degradacion canary->shadow y comparativos WR. Reduced sizing mitiga magnitud de perdida; no mitiga la rotura del contrato.
4. **No hay loop de feedback independiente.** La fuente que decide settlement (Polymarket/WU) es la misma con la que el bot tendria que validarse. Si esa fuente se desvia (bug de zona horaria, retraso de WU, ambiguedad de codigo ICAO), el bot no lo ve. El proposito de `observed_vs_forecast` es justamente ese segundo dictamen.
5. **Bankroll $25 + n=14-19 con WR=100%.** El IC95% para Bernoulli con `n=14, p=1.0` baja a `[0.77, 1.0]`. Estadisticamente la senal es plausible pero fragil. La asimetria coste/beneficio favorece esperar muestra extra antes de comprometer capital.

## Por que no Opcion 2 (exigir NOAA estricto)

1. **ISD 2026 devuelve 404 para los 4 ICAO.** Puede ser migracion NOAA, retiro de estacion, embargo regional. No es una espera de dias, puede ser permanente.
2. **Renuncia al alpha sin razon tecnica.** El alpha existe; lo que falta es el segundo dictamen, no la senal.
3. **El repo ya tiene precedente de proxy.** Sesion 234 acepta `open-meteo archive` como fallback para SL retrospective. Sesion 240 lo usa en `forecast_accuracy_audit.py`. La regla "solo NOAA" ya es de facto "NOAA o proxy reconocido".

## Por que Opcion 3 (estado intermedio con proxy observado)

1. **Reusa infraestructura existente.** `tools/forecast_accuracy_audit.py` ya consulta open-meteo. No requiere desarrollo nuevo de fuente — solo extension de cobertura.
2. **Preserva el contrato del sistema.** `interpretable` sigue significando "tiene observed proxy + muestra suficiente". El gate canary actual (sesion 172, umbrales v1) sigue funcionando sin parches.
3. **Define camino claro de promocion.** Lucknow/Beijing tienen evidencia trader fuerte; el proxy observado abre la puerta a canary, no la cierra. Es "todavia no" con criterio operacional, no "nunca".
4. **No toca core.** Solo amplia `OBSERVED_AUDIT_CITIES` y configuracion de proxy. Trading core, NOAA core, scheduler, reglas de entrada/salida, sizing y whitelist quedan intactos.

## Criterio operativo decidido

### Gate de promocion canary para ciudades ICAO-only

Una ciudad sin `noaa_station_id` util puede promoverse a canary cuando se cumplan **todos**:

- Fuente Polymarket/WU verificada via ICAO (ya cumplido por las 4).
- En `OBSERVED_AUDIT_CITIES` con `observed_vs_forecast` >= **OBSERVED_FORECAST_MIN_SAMPLE** (constante actual del bot, no cambiar).
- Esa muestra observada via proxy debe tener WR alineado con el WR observado del bucket equivalente en el resto del sistema (no degradacion fuerte).
- Evidencia trader/blocked: `>= 10` resoluciones fuera de whitelist con WR `>= 80%`, ademas de `edge_hits >= 5` en shadow tracking en los ultimos 30 dias.
- Cumple los umbrales v1 ya congelados (`canary_trades>=5`, `WR>=60%`, `PnL>=+$1.00`, `days_since_promotion>=7`).

Una vez en canary, el gate `canary -> active` (umbrales v1 + Opcion B notificacion) sigue siendo el de sesion 172. Sin cambios.

### Aplicacion a las 4 candidatas

| Ciudad | Estado decidido | Accion concreta |
|---|---|---|
| Lucknow | observacion-only via proxy | Ya esta en `OBSERVED_AUDIT_CITIES`. Habilitar/verificar que `forecast_accuracy_audit.py` la cubra con open-meteo. Acumular muestra. |
| Beijing | observacion-only via proxy | **Agregar a `OBSERVED_AUDIT_CITIES`** (env var, no codigo). Cubrir con open-meteo. Acumular muestra. |
| Warsaw | seguir acumulando | `edge_hits=0` en shadow descarta evidencia bot. No agregar a observed audit todavia hasta que aparezca al menos 1 edge. |
| Chongqing | seguir acumulando | `cycles_seen=2` muestra muy corta. No tocar todavia. |

Lucknow primero, no Beijing: tiene mejor evidencia combinada (`19/19`, consenso `7`, shadow `edge_hits=8`, `best_edge=47.4%`). Beijing va segundo aunque tenga mas `cycles_seen`, porque el alpha trader en Lucknow es mas concentrado.

## Patch minimo permitido (si Pablo lo aprueba)

Tres cambios, todos read-only respecto a trading:

1. **Env var Railway** `OBSERVED_AUDIT_CITIES` agrega `Beijing` (y deja `Lucknow` que ya esta). No tocar codigo.
2. **`tools/forecast_accuracy_audit.py`** confirmar que open-meteo cubre `Lucknow/VILK` y `Beijing/ZBAA`. Si no, agregar coordenadas a la tabla del proxy. Cambio aislado al script de audit, no al pipeline NOAA.
3. **Daily summary** (`tools/city_intelligence_daily_summary.py` o builder existente) agrega seccion "ICAO-only audit" mostrando `observed_via_proxy_count`, ultimo dato y diferencia vs forecast por ciudad. Pure observability, no actuator.

Sin esos tres pasos el estado intermedio queda solo en doc. Con ellos, el sistema acumula muestra automaticamente y avisa cuando una ciudad cruce el gate.

**No incluido en este patch:**
- Modificar `RESOLUTION_ICAO` (no agregar `noaa_station_id` ficticio).
- Modificar `QUALITY_TRADER_CITIES_WHITELIST` (no abrir whitelist).
- Modificar `CANARY_TRADING_CITIES` (no canary todavia).
- Tocar sizing, sigma, MIN_EDGE, scheduler o reglas.

## Trigger de revision

Esta decision se revisa si:

- Lucknow acumula `OBSERVED_FORECAST_MIN_SAMPLE` muestras via proxy con WR alineado -> evaluar promocion canary con sizing reducido.
- Aparece evidencia de que open-meteo discrepa sistematicamente con la resolucion Polymarket en estos ICAO -> revertir a Opcion 2 (exigir NOAA estricto) o agregar tercera fuente.
- NOAA ISD vuelve a estar disponible para 2026 -> usar la via canonica.
- `RECALIBRATION_PHASE2_CLOSED=true` -> el contexto general permite mas tolerancia, pero el gate especifico de ICAO-only sigue valido.

## Guardrails respetados

- No tocar `bot.py` trading core.
- No tocar NOAA core ni scheduler.
- No tocar reglas de entrada/salida ni sizing.
- No usar `BLOCKED_CITIES` como pausa operativa.
- No abrir whitelist masiva.
- No promover canary sin evidencia observada (ni siquiera con sizing reducido).
