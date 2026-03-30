# Investigacion Estrategica — Claude Code (Opus 4.6)

**Fecha:** 2026-03-30
**Autor:** Claude Code (Opus 4.6)
**Proposito:** Investigacion independiente + revision adversarial del trabajo de Codex

---

## PARTE 1: HALLAZGOS PROPIOS MAS IMPORTANTES

### Hallazgo 1: Dallas usa KDAL (Love Field), no KDFW — BUG ACTIVO CONFIRMADO

**Nivel de confianza: ALTO (verificado con fuente primaria)**

Polymarket resuelve los mercados de Dallas usando Dallas Love Field (KDAL), no Dallas Fort Worth (KDFW).

Evidencia:
- Reglas de mercado en polymarket.com para Dallas especifican textualmente: "Dallas Love Field Station" con URL `wunderground.com/history/daily/us/tx/dallas/KDAL`
- Verificado en multiples mercados de Dallas (March 2, March 4, 2026)
- wethr.net tiene dashboards separados para KDFW (`/market/dallas`) y KDAL (`/market/dallaslove`)

El bot actualmente usa:
```python
"Dallas": {"lat": 32.8972, "lon": -97.0377, "name": "Dallas Fort Worth"}  # KDFW
```

Deberia ser:
```python
"Dallas": {"lat": 32.8459, "lon": -96.8510, "name": "Dallas Love Field"}  # KDAL
```

**Impacto:** Las estaciones estan a ~19km de distancia. Diferencia de temperatura observada: hasta 3C (5F). En mercados que resuelven en buckets de 1-2F, esto es catastrofico. Dallas es una de las 4 ciudades activas del bot.

### Hallazgo 2: La auditoria forecast_vs_real NO compara contra observaciones reales

**Nivel de confianza: ALTO (verificado en codigo)**

La funcion de auditoria (bot.py ~linea 5007) llama a `get_forecast()` con coordenadas de RESOLUTION_STATIONS para obtener "datos reales". Pero `get_forecast()` llama a `api.open-meteo.com/v1/forecast` — el endpoint de **prediccion**, no de observaciones historicas.

Esto significa que la auditoria compara **forecast Open-Meteo vs forecast Open-Meteo en otro momento**. No hay ninguna comparacion contra observaciones reales en todo el sistema.

### Hallazgo 3: aviationweather.gov es gratis y sin API key, PERO es la fuente de Kalshi, no de Polymarket

**Nivel de confianza: ALTO (verificado con request real)**

El endpoint `aviationweather.gov/api/data/metar?ids=KJFK&format=json` devuelve JSON con temperatura, maxT24, minT24, raw METAR. Gratuito, sin autenticacion.

**PERO** — matiz critico que la investigacion inicial no distinguio bien:
- **Kalshi** resuelve con NWS Climate Report (CLI) — datos oficiales ASOS
- **Polymarket** resuelve con **Weather Underground History tab** — que puede incluir ajustes, formatting diferente, o datos PWS

wethr.net lo confirma explicitamente en su pagina `/market-resolution`:
- Kalshi -> NWS CLI
- Polymarket -> Weather Underground History

Esto NO invalida usar METAR como aproximacion (WU fundamentalmente muestra datos METAR de estaciones aeroportuarias), pero significa que puede haber discrepancias menores entre lo que aviationweather.gov reporta y lo que WU muestra.

### Hallazgo 4: Degen Doppler es real y sofisticado

**Nivel de confianza: ALTO (verificado con fetch)**

degendoppler.com esta activo. Usa GFS, ECMWF, HRRR, NAM, Open-Meteo, NWS. Muestra edge por bracket, tiene tiers de confianza (HIGH/MEDIUM/LONGSHOT), soporta Kalshi y Polymarket. Referencia Weather Underground para contexto de resolucion.

Esto es esencialmente una version mucho mas avanzada de lo que hace nuestro bot: multi-modelo ponderado vs nuestro single-source Gaussian.

### Hallazgo 5: WeatherClaw NO EXISTE como producto

**Nivel de confianza: ALTO (verificado)**

El dominio weatherclaw.com es un dominio aparcado en venta por $600,000 USD en Spaceship.com. No hay producto, servicio ni herramienta. Codex lo reporto como si fuera un competidor real con "122 ensemble forecast models" y "quarter-Kelly". **Esto fue un error de Codex** — posiblemente confundio fuentes o interpreto marketing de otro producto.

### Hallazgo 6: Buenos Aires puede tener un mismatch Ezeiza vs Aeroparque

**Nivel de confianza: MODERADO (inferido, no verificado en fuente primaria)**

El bot usa Ezeiza (SAEZ, a ~30km del centro, inland). Si Polymarket resuelve con Aeroparque Jorge Newbery (SABE, costero, en la ciudad), las temperaturas pueden diferir 1-2C. Necesita verificacion contra reglas reales de mercados de Buenos Aires.

Codex verifico un mercado de Buenos Aires que apunta a SAEZ, lo cual sugiere que el mapping actual es correcto. Pero esto merece auditoria continua.

### Hallazgo 7: suislanchez/polymarket-kalshi-weather-bot — mas reciente y menos maduro de lo que parece

**Nivel de confianza: ALTO (verificado en GitHub)**

- 84 stars, ultimo push 2026-03-02 (27 dias sin actividad)
- El componente de weather trading fue anadido el 2026-03-01 (hace <1 mes)
- La mayoria de commits estan co-authored con Claude Opus 4.6
- Usa el mismo Open-Meteo que nosotros (no resuelve el problema WU)
- Peak profits reportados de $1,800 pero backtest 86% WR que baja a ~60% live

No es un competidor maduro — es un proyecto paralelo al nuestro en fase similar.

### Hallazgo 8: Microestructura del mercado — los takers pierden sistematicamente

**Nivel de confianza: ALTO (estudio academico de 72.1M trades)**

Del paper de Jonathan Becker analizando Kalshi (microestructura similar a Polymarket):
- Takers tienen retornos negativos en exceso en 80 de 99 niveles de precio
- El favourite-longshot bias esta documentado: contratos <20c underperforman, >80c outperforman
- Solo 0.51% de wallets tienen profits >$1,000

Nuestro bot es un taker con GTC limit orders. El edge debe venir 100% del modelo.

### Hallazgo 9: Competidores con profits confirmados en weather

**Nivel de confianza: MODERADO (visible en leaderboard pero no auditado on-chain)**

- **gopfan2**: >$2M profit, visible en polymarket.com/@gopfan2. Pero Codex correctamente nota que parte de ese PnL puede venir de mercados climate/macro, no solo temperature diaria.
- **meropi**: ~$30K, micro-bets automatizados cada 2 min
- **neobrother**: >$20K, "temperature laddering" multi-bracket

### Hallazgo 10: El rounding problem F/C es real y no trivial

**Nivel de confianza: ALTO (verificable por logica METAR)**

Para ciudades US: ASOS graba en F enteros -> METAR transmite en C enteros -> WU muestra F original. Para ciudades internacionales en mercados en F, la doble conversion crea ambiguedad de +-1F. Esto puede causar resoluciones "sorpresa" en mercados de buckets estrechos.

---

## PARTE 2: COINCIDENCIAS FUERTES CON CODEX

### 2.1 Tesis central: "Resolution fidelity first"
**ACUERDO TOTAL.** Codex y yo llegamos a la misma conclusion por caminos independientes. Antes de mejorar el modelo, hay que alinear la fuente de datos con la fuente de resolucion.

### 2.2 Dallas KDAL vs KDFW
**ACUERDO TOTAL.** Codex lo encontro primero. Yo lo confirme con fuentes primarias adicionales (reglas de mercado, wethr.net dashboards separados, diferencia de temperatura medida). Bug critico activo.

### 2.3 Polymarket resuelve con Weather Underground
**ACUERDO TOTAL.** Verificado por ambos en multiples mercados. wethr.net lo confirma explicitamente en su pagina de market resolution.

### 2.4 Lo que es commodity vs edge real
**ACUERDO FUERTE.** Codex y yo coincidimos en que forecast basico + Kelly + dashboard + execution plumbing ya es commodity. El edge real esta en: mapping correcto de estacion, fuente de resolucion correcta, timing de datos, especializacion por ciudad.

### 2.5 La auditoria del bot compara forecast vs forecast
**ACUERDO TOTAL.** Ambos identificamos que no hay comparacion contra observaciones reales.

---

## PARTE 3: DESACUERDOS REALES CON CODEX

### 3.1 WeatherClaw como competidor real
**DESACUERDO — Codex se equivoco.**

Codex reporto WeatherClaw como un competidor con claims de "122 ensemble forecast models", "quarter-Kelly", "circuit breaker", "30-minute scans". Verificacion: weatherclaw.com es un dominio aparcado en venta por $600,000. No existe como producto.

Codex probablemente confundio fuentes. Los claims que describe (122 modelos, quarter-Kelly, circuit breaker) pueden corresponder a otro producto — posiblemente PolyTraderBot o una combinacion de fuentes. Esto es un error factual significativo porque influyo en su analisis de la competencia.

**Impacto en roadmap:** Ninguno — la conclusion de Codex no dependia de WeatherClaw.

### 3.2 aviationweather.gov como solucion directa al problema de resolucion
**DESACUERDO PARCIAL — matiz importante.**

Mi investigacion inicial (y muchas fuentes) sugirieron que aviationweather.gov/METAR seria equivalente a WU. Codex fue mas cauteloso y no lo propuso como fix directo.

La realidad verificada: METAR es la fuente subyacente que WU consume, pero WU puede mostrar datos de forma ligeramente diferente (formatting, timezone handling, inclusion de SPECIs). Para Polymarket, la resolucion es lo que aparece en la **History tab** de wunderground.com, no el raw METAR.

**Correccion al roadmap:** METAR/aviationweather es util como **aproximacion y validacion**, no como source of truth para resolucion. Para resolucion exacta, se necesita scrapear WU History directamente o usar wethr.net que ya pre-procesa esto.

### 3.3 Prioridad de timing/microestructura vs modelo
**DESACUERDO MENOR.**

Codex pone timing-aware execution (Priority 4) antes de evaluar mejoras de modelo (Priority 5). Yo pondria el ensemble GFS antes del timing, porque:
- El ensemble GFS esta disponible gratis en Open-Meteo (mismo endpoint, solo cambiar URL)
- El impacto de pasar de Gaussian con sigma manual a 31-member ensemble es alto y el esfuerzo es bajo
- Timing-aware execution requiere investigacion de release schedules por ciudad y cambios en el scheduler — mas esfuerzo

**Mi orden:** Resolution fix -> Ensemble GFS -> Timing-aware execution

### 3.4 Buenos Aires como "safe"
**DESACUERDO MENOR.**

Codex verifico un mercado de Buenos Aires que apunta a SAEZ (Ezeiza) y lo marco como correcto. Pero la posibilidad de que algunos mercados usen Aeroparque (SABE, costero) merece auditoria. La diferencia costera vs inland puede ser 1-2C. Sin embargo, dado que Codex encontro evidencia de SAEZ, mantengo esto como "monitorear" no "urgente".

---

## PARTE 4: ERRORES O LAGUNAS DEL INFORME DE CODEX

### 4.1 WeatherClaw no existe — ERROR FACTUAL
Como se detallo arriba, es un dominio aparcado. Codex dedico una seccion significativa a analizarlo como competidor real con claims especificos. Esto debilita la credibilidad de esa parte del analisis, aunque la conclusion estrategica no depende de ello.

### 4.2 No menciona Degen Doppler — LAGUNA SIGNIFICATIVA
degendoppler.com es probablemente la herramienta mas directamente comparable a lo que nuestro bot intenta hacer, y Codex no lo menciona. Es un edge finder multi-modelo para Polymarket weather con soporte para Kalshi.

### 4.3 No menciona el favourite-longshot bias — LAGUNA MODERADA
El estudio de 72.1M trades sobre microestructura de prediction markets es relevante para nuestra estrategia de seleccion de contratos. Sesgar hacia contratos >60c tiene evidencia academica solida.

### 4.4 No menciona la bond strategy / high-probability plays — LAGUNA MODERADA
Comprar contratos a >95c cuando las observaciones METAR ya confirman el outcome (dia de resolucion) es una estrategia con 1,800% annualizado documentado. Para un bankroll de $18.89, esto puede ser mas valioso que edge-based betting con modelo imperfecto.

### 4.5 No cuantifica el impacto del mismatch Dallas — LAGUNA MENOR
Codex identifica el bug pero no investiga cuanto habria costado. Verificacion: 3C de diferencia actual entre KDAL y KDFW. En mercados de 1-2F buckets, esto es ~5F de error sistematico.

### 4.6 No investiga la funcion de auditoria en profundidad — LAGUNA MENOR
Codex nota correctamente que el bot usa Open-Meteo para "historical observed logic" pero no verifica que `get_forecast()` es la misma funcion para forecast y "observaciones". Es decir, no hay ninguna comparacion contra datos reales en todo el sistema.

---

## PARTE 5: QUE ESTA VERIFICADO, QUE ES INFERENCIA, QUE SIGUE INCIERTO

### VERIFICADO (evidencia primaria directa)

| Claim | Fuente |
|-------|--------|
| Polymarket resuelve Dallas con KDAL/Love Field | Reglas de mercado polymarket.com |
| Bot usa KDFW para Dallas | bot.py linea 2877 |
| Diferencia KDAL-KDFW: ~3C/5F | Observaciones actuales verificadas |
| Polymarket resuelve con Weather Underground | Multiples paginas de mercado verificadas |
| Bot usa Open-Meteo forecast para todo (incluida auditoria) | bot.py lineas 4037-4066, 5007-5011 |
| aviationweather.gov API es gratis y sin key | Request real verificado, JSON valido |
| Kalshi resuelve con NWS CLI, no WU | wethr.net/market-resolution |
| degendoppler.com esta activo con multi-modelo | Fetch verificado |
| weatherclaw.com NO es un producto real | Fetch verificado — dominio aparcado |
| suislanchez bot: ultimo commit 2026-03-02, weather anadido 2026-03-01 | GitHub API |
| Open-Meteo ofrece endpoint de ensemble GFS gratis | Documentacion Open-Meteo |

### INFERIDO (logica solida pero sin verificacion directa)

| Claim | Base |
|-------|------|
| METAR es la fuente subyacente de WU | Documentacion WU + conocimiento meteorologico |
| Buenos Aires probablemente correcto (SAEZ) | Un mercado verificado por Codex |
| gopfan2 usa multi-modelo o similar | Inferido de volumen y PnL, no verificado |
| El favourite-longshot bias aplica a weather markets | Documentado en Kalshi, inferido para Polymarket |
| Quarter-Kelly seria mejor que Half-Kelly con incertidumbre actual | Paper academico, no backtested con nuestros datos |

### SIGUE INCIERTO

| Pregunta | Por que |
|----------|---------|
| Que fraccion del PnL de gopfan2 viene de daily temp vs climate/macro? | No hay desglose publico |
| WU History muestra exactamente lo mismo que raw METAR? | Posibles diferencias de formatting/rounding |
| Chicago (KORD) es correcta para todos los mercados de Chicago? | No verificado en reglas — podria ser Midway (KMDW) |
| Cuantos trades de Dallas se perdieron por el mismatch KDAL/KDFW? | Necesita backtest con datos reales |
| meropi realmente opera cada 2 min? | Citado en articulos, no verificado on-chain |
| Hay otros station mismatches en ciudades bloqueadas? | No investigado — London EGLC ya se confirmo |

---

## PARTE 6: ROADMAP FINAL PRIORIZADO

### Prioridad 1: FIX DALLAS KDAL (Impacto: CRITICO, Esfuerzo: 5 MINUTOS)

Cambiar coordenadas de Dallas de KDFW a KDAL en bot.py. Este es un bug activo en una de las 4 ciudades operativas. Error sistematico de ~5F.

### Prioridad 2: VERIFICAR ESTACIONES DE TODAS LAS CIUDADES ACTIVAS (Impacto: ALTO, Esfuerzo: 1-2 HORAS)

Para Chicago, Atlanta, Buenos Aires: abrir una pagina de mercado real en Polymarket y verificar que la estacion en las reglas coincide con lo que el bot tiene. Esto incluye Chicago (O'Hare vs Midway?) y Buenos Aires (Ezeiza vs Aeroparque?).

### Prioridad 3: INTEGRAR VALIDACION METAR PRE-APUESTA (Impacto: ALTO, Esfuerzo: 2-3 HORAS)

Antes de cada apuesta, consultar aviationweather.gov para la estacion ICAO correcta. Si la temperatura observada actual ya diverge >2C del forecast Open-Meteo para hoy, skip. Esto funciona como "circuit breaker" contra discrepancias de fuente.

No es la fuente de resolucion exacta (esa es WU), pero es una aproximacion gratuita y sin friccion que eliminaria los peores errores.

### Prioridad 4: CREAR LAYER DE RESOLUCION FORMAL (Impacto: ALTO, Esfuerzo: 3-4 HORAS)

Como propone Codex: `market -> ICAO code -> WU URL -> timezone -> unit -> finalization rule`.

Esto formaliza el mapping y permite:
- Verificacion automatica contra reglas de mercado
- Shadow monitoring (comparar prediccion vs observacion real WU)
- Backtest contra la fuente correcta

### Prioridad 5: UPGRADE A ENSEMBLE GFS (Impacto: ALTO, Esfuerzo: 2-3 HORAS)

Reemplazar `api.open-meteo.com/v1/forecast` por `ensemble-api.open-meteo.com/v1/ensemble` con 31 miembros GFS. Calcular probabilidad contando miembros que superan threshold en vez de Gaussian con sigma manual.

Esto es el cambio de modelo con mejor ratio impacto/esfuerzo. No requiere nueva fuente de datos, solo cambiar el endpoint y la logica de calculo de probabilidad.

### Prioridad 6: CONSIDERAR BOND STRATEGY PARA DIA DE RESOLUCION (Impacto: MODERADO, Esfuerzo: 3-4 HORAS)

Cuando un mercado resuelve en <12h y las observaciones METAR confirman el bracket, comprar a >93c para 3-7% return cuasi-seguro. Con $18.89, compounding 5% cada 1-3 dias compone mas rapido que edge betting con modelo imperfecto.

### Prioridad 7: TIMING-AWARE EXECUTION (Impacto: MODERADO, Esfuerzo: 4-6 HORAS)

Sincronizar ciclos con model runs GFS (00Z, 06Z, 12Z, 18Z) para first-mover advantage. Evitar tener ordenes expuestas durante ventanas de release de datos (DSM, 6-hour).

### Prioridad 8: SESGAR SELECCION HACIA FAVOURITES (Impacto: MODERADO, Esfuerzo: 1 HORA)

Preferir contratos >60c donde el favourite-longshot bias trabaja a favor del taker. Anadir un peso o filtro que penalice longshots (<20c) donde el bias es adverso.

### Prioridad 9: EXPLORAR WETHR.NET Y DEGEN DOPPLER COMO INPUTS (Impacto: VARIABLE, Esfuerzo: INVESTIGACION)

Evaluar si consumir datos de wethr.net (free tier, 3min delay) o Degen Doppler anade valor vs construir todo in-house. El trade-off es dependencia externa vs velocidad de mejora.

---

## PARTE 7: RESPUESTAS EXPLICITAS A LAS PREGUNTAS DE CODEX

### 1. Acuerdo con "resolution fidelity first"?
**SI, acuerdo total.** Es la conclusion mas solida de ambas investigaciones. El fix de Dallas solo (5 minutos de trabajo) probablemente tiene mas impacto que semanas de mejora de modelo.

### 2. Confirmacion Dallas KDAL vs KDFW?
**CONFIRMADO con evidencia adicional.** Reglas de mercado, wethr.net dashboards separados, 3C de diferencia medida.

### 3. Otras ciudades con mismatch comparable?
**Chicago merece verificacion.** KORD (O'Hare) vs KMDW (Midway) es una pregunta abierta. wethr.net tiene dashboard para KMDW (Chicago Midway). Si Polymarket resuelve con Midway, el bot tiene otro mismatch activo. Buenos Aires probablemente correcto pero merece confirmacion.

### 4. Wethr como timing aid vs settlement truth?
**PARCIALMENTE DE ACUERDO.** Codex tiene razon en que wethr.net no debe ser la fuente final de verdad — esa son las reglas del mercado de Polymarket. Pero wethr.net SI identifica correctamente que Polymarket usa WU (su pagina /market-resolution lo dice explicitamente). Wethr es util como: (1) referencia de que fuente usa cada plataforma, (2) datos METAR procesados, (3) timing/microestructura, (4) model accuracy metrics.

### 5. Competidor mas peligroso para daily temperature?
**Degen Doppler** (que Codex no identifico). Es un edge finder multi-modelo para exactamente los mismos mercados. Alguien usando Degen Doppler con capital y execution esta operando con informacion superior a la nuestra en cada dimension (multi-modelo, WU-aware, edge visualization).

gopfan2 es el mas rentable, pero no sabemos si su PnL viene de daily temp o climate/macro.

### 6. Fuentes primarias mejores?
**Si.** Las reglas de mercado de Polymarket son la fuente primaria definitiva. Para cada ciudad, la pagina del evento dice explicitamente la estacion y la URL de WU. Esto supera cualquier fuente secundaria (wethr.net, articulos, etc.).

### 7. Cambiaria el orden del roadmap?
**SI — un cambio.** Pondria ensemble GFS (Prioridad 5) antes de timing-aware execution (Prioridad 7). El ensemble es cambio de endpoint + logica, bajo esfuerzo, alto impacto. Timing requiere investigacion de schedules por ciudad y cambios en scheduling, mas esfuerzo, impacto menos claro.

---

## CONCLUSION ESTRATEGICA FINAL

> **Si tuviera que elegir solo una direccion estrategica para las proximas sesiones, cual seria y por que?**

### Direccion: ALINEAR EL BOT CON LA REALIDAD DE RESOLUCION DE POLYMARKET

No "mejorar el modelo". No "anadir mas ciudades". No "mas features".

**Hacer que el bot juegue el mismo juego que Polymarket esta liquidando.**

Esto significa, en orden:

1. **Fix Dallas KDAL ahora** (5 minutos, bug critico activo)
2. **Verificar Chicago y Buenos Aires** contra reglas de mercado reales (1 hora)
3. **Anadir gate METAR pre-apuesta** como circuit breaker (2-3 horas)
4. **Crear tabla formal `ciudad -> ICAO -> WU URL`** para las 4 ciudades activas (1 hora)

**Por que esta direccion y no otra:**

- **Es donde esta el dinero perdido.** Dallas con 5F de error sistematico, la auditoria que compara forecast vs forecast, 10 ciudades ya bloqueadas por discrepancias. El pattern es claro: el bot pierde cuando la fuente esta mal.
- **Es de bajo esfuerzo y alto impacto.** El fix de Dallas es trivial. La verificacion de estaciones es 1 hora de trabajo manual. El gate METAR es una funcion de 20 lineas.
- **Todo lo demas se construye sobre esta base.** Ensemble GFS no sirve si las coordenadas apuntan al aeropuerto equivocado. Bond strategy no sirve si no sabes que estacion mira WU. Timing no sirve si el forecast que usas no corresponde a la realidad de resolucion.
- **Es lo que hacen los que ganan.** Degen Doppler referencia WU. wethr.net muestra datos METAR de la estacion correcta. gopfan2 probablemente opera con la fuente correcta. Nadie rentable esta apostando contra su propia fuente de resolucion.

El edge real en weather markets no esta en el modelo mas sofisticado. Esta en **predecir lo que Weather Underground va a mostrar manana para la estacion exacta que Polymarket mira.** Hasta que eso no este resuelto, todo lo demas es optimizar en la direccion equivocada.
