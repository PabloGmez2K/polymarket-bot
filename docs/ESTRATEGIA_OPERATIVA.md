# ESTRATEGIA_OPERATIVA.md

## Objetivo

Este documento describe la operativa vigente del bot de forma compacta y comparable.

Su función es responder, sin releer `bot.py`, a estas preguntas:

- qué mercados opera el sistema;
- cómo decide entrar o no entrar;
- qué fuentes usa para decidir, medir y entender la resolución;
- cómo dimensiona posición;
- qué significa cada modo de ciudad;
- qué métricas usamos para juzgar si la estrategia está funcionando.

Debe servir como base para:

- comparar nuestra operativa con la de otros traders;
- detectar gaps de estrategia, cobertura o ejecución;
- evitar drift semántico entre código, Telegram, dashboard y análisis externos.

## Resumen ejecutivo

La estrategia actual es:

- operar mercados de temperatura diarios de Polymarket;
- usar `Open-Meteo` como fuente de forecast operativo;
- convertir ese forecast en probabilidad con un modelo normal `N(mu, sigma)`;
- limitar la operativa a mercados direccionales:
  - `at_or_above`
  - `at_or_below`
- exigir edge mínimo positivo y suficiente antes de comprar;
- dimensionar con `Half-Kelly`;
- usar `NOAA` como capa observada para medir forecast y policy;
- asumir que la resolución final real de Polymarket depende de `Weather Underground`, no de NOAA.

Contrato canónico de fuentes:

- `Open-Meteo decide`
- `NOAA mide`
- `Weather Underground resuelve`

## Universo operado

### Tipo de mercado

El bot opera mercados climáticos de temperatura máxima por ciudad y fecha.

La lectura operativa es:

- ciudad;
- fecha del mercado;
- umbral de temperatura;
- condición;
- precio implícito del mercado;
- forecast operativo;
- edge estimado.

### Condiciones permitidas

La operativa real está restringida por defecto a:

- `at_or_above`
- `at_or_below`

Los mercados `range` y `exact` no se compran. Se registran como `condition_filtered` para observabilidad y shadow tracking.

### Horizonte temporal

El scan filtra mercados por ventana temporal:

- mínimo dinámico por ciudad y momento del día;
- máximo global de `5` días (`MAX_DAYS_AHEAD = 5`).

### Filtros estructurales previos a la decisión

Antes de calcular edge, el mercado debe pasar:

- parseo correcto;
- ciudad válida y no bloqueada;
- fecha dentro de rango;
- precio dentro de rango utilizable;
- liquidez mínima;
- forecast disponible para esa ciudad/fecha.

Thresholds operativos vigentes:

- `MIN_LIQUIDITY = 100`
- `MIN_PRICE = 0.20`
- `MAX_PRICE = 0.80`
- `MAX_DAYS_AHEAD = 5`

## Modos de ciudad

Los modos son excluyentes y ordenados por prioridad:

| Modo | Tradea | Observa NOAA | Significado operativo |
|------|:------:|:------------:|-----------------------|
| `blocked` | no | no | ciudad descartada porque el pipeline de datos es estructuralmente poco fiable |
| `shadow` | no | sí | ciudad observada para aprendizaje, sin capital real |
| `canary` | sí, pequeño | sí | ciudad operable con sizing reducido |
| `active` | sí | sí | ciudad plenamente operable |

Regla práctica:

- no querer operar una ciudad no implica bloquearla;
- si se quiere seguir observándola, debe quedar en `shadow`;
- `blocked` se reserva para problemas de fuente o resolución, no para una pausa táctica.

## Pipeline de decisión de entrada

La lógica de entrada, simplificada, es esta:

1. El bot escanea mercados candidatos.
2. Filtra por ciudad, fecha, precio, liquidez y condición.
3. Obtiene forecast de `Open-Meteo`.
4. Convierte el forecast en probabilidad con una distribución normal.
5. Compara probabilidad modelo vs probabilidad implícita del mercado.
6. Elige el lado con mayor edge positivo (`YES` o `NO`).
7. Exige `MIN_EDGE`.
8. Calcula tamaño con `Half-Kelly`.
9. Si la ciudad no es operable, guarda la señal en `shadow`.
10. Si es operable, intenta comprar respetando presupuesto y protecciones anti-duplicado.

## Modelo probabilístico

### Media (`mu`)

La media parte del forecast de `Open-Meteo`.

Sobre esa media puede aplicarse una corrección de sesgo por ciudad:

- `Atlanta: +1.38°C`
- `Chicago: +1.40°C`
- `Dallas: +0.0°C`

Esta corrección intenta compensar desvíos sistemáticos medidos frente a observado.

### Incertidumbre (`sigma`)

La sigma sigue una lógica híbrida:

- usa sigma empírica por ciudad si hay muestra suficiente (`n >= 3`);
- si no, cae a sigma empírica global;
- si tampoco hay, usa la referencia base del modelo.

### Conversión a probabilidad

La probabilidad se calcula con una normal `N(mu, sigma)`:

- `at_or_below`: `P(T <= umbral)`
- `at_or_above`: `P(T >= umbral)`
- con corrección de `±0.5` por el redondeo entero de temperatura

## Definición de edge

El bot calcula:

- `our_prob_yes`
- `our_prob_no`
- `mkt_prob_yes`
- `mkt_prob_no`

Y define:

- `edge_yes = our_prob_yes - mkt_prob_yes`
- `edge_no = our_prob_no - mkt_prob_no`

Luego:

- si `edge_yes > edge_no` y `edge_yes > 0`, elige `YES`;
- si `edge_no > 0`, elige `NO`;
- si ninguno es positivo, no entra.

Threshold vigente:

- `MIN_EDGE = 15.0%`

## Sizing y presupuesto

### Sizing por trade

La posición se dimensiona con `Half-Kelly`.

Reglas principales:

- si Kelly es `<= 0`, no hay trade;
- el tamaño se limita por `MAX_BET_PCT`;
- el tamaño final debe superar `MIN_BET`;
- se usa un precio agresivo moderado para la orden.

Thresholds vigentes:

- `BANKROLL = $25.00`
- `MIN_BET = $1.00`
- `MAX_EXPOSURE_PCT = 40%`
- `STOP_LOSS_PCT = -25%`
- `TAKE_PROFIT_PCT = +40%`

### Canary

En `canary`, la lógica de entrada no cambia, pero el tamaño sí:

- la posición se escala con `CANARY_POSITION_SCALE = 0.50`
- el objetivo es operar con riesgo reducido mientras la ciudad sigue validándose

### Presupuesto global

El bot no solo decide si un trade tiene edge; también decide si cabe dentro de la exposición máxima permitida.

Lógica práctica:

- calcula exposición actual;
- calcula presupuesto libre respecto al máximo;
- ordena trades por `expected_value`;
- selecciona hasta agotar presupuesto;
- si el último no cabe completo pero aún supera `MIN_BET`, lo reduce.

## Protecciones de ejecución

Aunque un trade tenga edge, el bot no recompra si:

- ya hay una orden abierta en ese token;
- ya existe una posición abierta en ese token;
- ese token se vendió en el mismo ciclo.

Esto evita:

- duplicados;
- reentrada inmediata accidental;
- sobreexposición no deseada.

## Shadow y aprendizaje sin capital

Si una ciudad no es operable pero el mercado tiene edge y pasa filtros, la señal no se pierde.

Se guarda como `shadow` para:

- medir oportunidades fuera de allowlist;
- observar qué habría pasado sin arriesgar capital;
- alimentar promoción futura a `canary`;
- construir `directional_history` y joins posteriores con NOAA.

`shadow` no es una ciudad rota. Es una ciudad observada pero no operada.

## Qué hace NOAA en la estrategia

`NOAA` no decide compras.

Se usa para:

- `observed_vs_forecast`
- cobertura observada por ciudad
- `MAE`
- `bias`
- señal `NOAA-verificado`
- policy y priorización por ciudad
- validación de `WR observado direccional`

Un caso NOAA es:

- una fila `city + date` en `observed_vs_forecast`

Esto mide calidad del forecast y calidad del sistema, no settlement final.

## Qué hace Weather Underground

`Weather Underground` es la referencia de resolución real de Polymarket.

Esto implica:

- una decisión puede estar bien según `Open-Meteo`;
- una medición puede verse razonable según `NOAA`;
- y aun así el settlement final puede diferir si `WU` resuelve distinto.

Por eso:

- `NOAA` no debe interpretarse como settlement;
- `NOAA-verificado` no es idéntico a PnL final;
- `postmortem trading` y `observabilidad NOAA` responden preguntas distintas.

## Cómo evaluamos la estrategia hoy

La operativa no se juzga con una sola métrica.

Las capas principales son:

### 1. Resultado de trading

Mide:

- BUYs
- SELLs
- win rate
- PnL
- postmortem por ciudad

Pregunta que responde:

- `¿estamos ganando dinero y cómo están cerrando los trades?`

### 2. Calidad de forecast / medición

Mide:

- muestra NOAA
- cobertura por ciudad
- `MAE`
- `bias`
- ciudades interpretables

Pregunta que responde:

- `¿estamos midiendo bien y aprendiendo algo fiable?`

### 3. Evidencia por ciudad / policy

Mide:

- histórico `NOAA-verificado`
- shadow edges
- canary readiness
- overlays `active/canary/shadow/blocked`

Pregunta que responde:

- `¿qué ciudades merecen operar, seguir en canary o volver a shadow?`

### 4. Shadow observado direccional

Mide:

- señales shadow direccionales persistidas;
- join con NOAA por `city + date`;
- `WR observado direccional`

Pregunta que responde:

- `si hubiéramos operado más señales fuera de allowlist, qué evidencia tendríamos a favor o en contra`

## Qué no hace todavía la estrategia

Importante para compararnos con otros traders:

- no usa NOAA como feed operativo de entrada;
- no usa Weather Underground como feed automático de pricing;
- no opera `range` ni `exact` por defecto;
- no autooptimiza la estrategia en producción;
- no promueve o degrada ciudades solo por histórico legacy si falta base `NOAA-verificada`;
- no tiene todavía la fuente de settlement real integrada como capa automática de auditoría;
- no tiene aún una capa completa de benchmark externo contra traders ganadores.

## Checklist comparativo para investigar otros traders

Cuando investiguemos otros traders, esta es la comparación que conviene hacer:

1. Qué mercados operan realmente:
   direccionales, rango, exactos, horizonte temporal, ciudades, liquidez.
2. Qué fuente usan para decidir:
   forecast público, ensembles, datos propios, orderflow, señales sociales.
3. Cómo convierten forecast en probabilidad:
   heurística, modelo estadístico, calibration, sesgo por ciudad.
4. Qué umbral de edge exigen:
   fijo, dinámico, condicionado por ciudad, horario o volatilidad.
5. Cómo dimensionan:
   Kelly, fractional Kelly, flat bet, sizing discrecional.
6. Cómo distinguen exploración de producción:
   shadow, canary, live completo.
7. Qué miden después:
   forecast quality, hit rate, PnL, settlement fidelity, source drift.
8. Qué hacen mejor que nosotros:
   más cobertura, mejor timing, mejor ejecución, mejor selección de mercados, mejor gestión de ciudades.

## Fuente de verdad

Este documento es descriptivo, no normativo por sí solo.

Si hay conflicto:

- la fuente de verdad operativa sigue siendo [bot.py](/c:/Projects/polymarket-bot/bot.py)
- la semántica de modos de ciudad vive en [AGENTS.md](/c:/Projects/polymarket-bot/AGENTS.md)
- la capa de aprendizaje y observabilidad vive en [OBSERVABILIDAD_Y_APRENDIZAJE.md](/c:/Projects/polymarket-bot/OBSERVABILIDAD_Y_APRENDIZAJE.md)

Pero este archivo debe mantenerse como la mejor explicación compacta y comparable de la estrategia vigente.
