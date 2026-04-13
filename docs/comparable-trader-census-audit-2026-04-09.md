# Comparable Trader Census Audit

Fecha: 2026-04-09
Estado: investigacion nueva, separada de la sesion anterior
Scope: auditar si el sistema actual concluye correctamente que hoy hay muy pocos traders comparables, o si el censo los descarta demasiado pronto.

## Pregunta central

Queremos responder con evidencia a esta pregunta:

`¿De verdad hay muy pocos traders comparables a nuestra estrategia, o el flujo/censo los está descartando demasiado pronto o interpretando mal?`

## Restricciones de esta investigacion

- No tocar `bot.py`
- No tocar trading core
- No mezclar esto con refactor amplio de arquitectura
- Primero evidencia de mercado real
- Luego juicio sobre filtros
- Luego recomendacion concreta

## Punto de partida

Habia una conclusion operativa fuerte en el sistema:

- hoy `directional_trader_census.py` y `city-intelligence` pueden terminar en `0 traders after filter`
- la lectura implicita era: "hoy casi no hay traders comparables"

Esta investigacion cuestiona esa inferencia.

## Contexto tecnico relevante ya resuelto antes

- `city-intelligence` ya fue corregido para:
  - detectar degradacion de señal
  - marcar `signal_degraded`
  - no fingir `overall_status=ok`
- el bootstrap live de Railway ya fue arreglado
- hubo un problema local de proxies contaminados:
  - `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY -> 127.0.0.1:9`
  - eso podia devolver listas vacias falsas
- ese hardening ya se atacó

Esta sesion no trata del proxy. Trata del diseño del censo comparable.

## Archivos auditados

- `tools/directional_trader_census.py`
- `tools/city_intelligence_pipeline.py`
- `tools/city_intelligence_service.py`
- `docs/directional-trader-census.md`

## Hallazgos de codigo

### 1. Seleccion de mercados

`directional_trader_census.py` construye el universo desde `gamma-api` ordenando eventos por `volume24hr` descendente y tomando un numero limitado de mercados.

Puntos clave:

- `--markets` default del script: `40`
- `city-intelligence` usa `CITY_INTELLIGENCE_CENSUS_MARKETS`, que hoy defaulta a `20`
- el pipeline llama al censo como:
  - `python tools/directional_trader_census.py --markets <census_markets>`

Implicacion:

- si el top-volume inmediato esta dominado por mercados extremos, el censo parte ya de un slice sesgado

### 2. Prefiltro por precio demasiado temprano

En `tools/directional_trader_census.py`, cada BUY se descarta por precio antes de agregarse por wallet:

- si `price < min_price` o `price > max_price`, el trade no entra en el mapa efectivo del trader
- despues de ese recorte, se aplican `min_trades` y `min_markets`
- solo al final se calcula `avg_price`

Implicacion:

- el censo no construye primero la actividad real del trader y luego evalua comparabilidad
- construye directamente un subconjunto ya amputado por precio
- por tanto, el `avg_price` final no describe al trader real; describe solo el subconjunto sobreviviente

### 3. `avg_price` simple no captura traders mixtos

Hay traders con actividad total fuertemente extrema pero con una fraccion no trivial de entradas comparables.

Si la comparabilidad futura se decidiera por `avg_price` global simple por wallet, esos traders quedarian mal clasificados.

## Metodologia de medicion live

Se hizo una radiografia live del mercado direccional activo usando el mismo universo fuente del censo:

- mercados direccionales `at_or_above` / `at_or_below`
- trades `BUY`
- exclusión de `size < 0.1`
- bins de precio:
  - `<0.10`
  - `0.10-0.20`
  - `0.20-0.35`
  - `0.35-0.65`
  - `0.65-0.80`
  - `>0.80`

Ademas se midieron dos escalas:

- slice pequeño tipo pipeline actual: `20` y `40` mercados
- universo amplio: hasta `434` mercados direccionales activos detectados

## Estado real del mercado

### Universo amplio live

- mercados direccionales activos detectados: `434`
- mercados con `market_prob_yes` dentro de `0.20-0.80`: `39`
- BUY trades observados: `19569`
- wallets unicas: `3281`
- wallets en 2+ mercados: `1364`
- wallets en 3+ mercados: `853`

Distribucion real de BUYs por precio:

- `<0.10`: `2216`
- `0.10-0.20`: `496`
- `0.20-0.35`: `630`
- `0.35-0.65`: `1303`
- `0.65-0.80`: `976`
- `>0.80`: `13948`

Lectura:

- el mercado real esta muy sesgado a extremos
- pero no esta vacio de actividad comparable
- el rango `0.20-0.80` representa `2909` BUYs, aproximadamente `14.9%` del total observado

### Participacion comparable en universo amplio

- wallets con al menos un BUY comparable: `889`
- wallets con 2+ BUYs comparables en 2+ mercados: `311`
- wallets multi-mercado con al menos un trade comparable: `535`
- wallets con 2+ mercados cuyo `market-level avg price` cae en `0.20-0.80`: `305`

Lectura:

- el subuniverso comparable existe hoy
- no es dominante, pero tampoco es marginal en terminos de observabilidad

### Ciudades relevantes para nuestra policy

Se cruzo contra ciudades activas, canary u observadas del repo.

Wallets con BUY comparable por ciudad relevante:

- `Munich`: `126`
- `Seattle`: `106`
- `Chicago`: `102`
- `Madrid`: `94`
- `Milan`: `89`
- `London`: `88`
- `Chengdu`: `82`
- `Tokyo`: `72`
- `Paris`: `47`
- `Ankara`: `46`
- `Dallas`: `39`

Lectura:

- en ciudades importantes para nuestro sistema si hay actividad comparable observable hoy
- por tanto, el problema no es simplemente "nuestro universo no existe"

## Donde se pierden los traders en el flujo actual

### Con `20` mercados

Medicion live:

- BUY trades: `1765`
- wallets: `738`
- BUYs en `0.20-0.80`: `0`
- resultado final: `0 traders after filter`

Detalle importante:

- esos 20 mercados estaban practicamente todos fuera del rango comparable
- distribucion por trade:
  - `<0.10`: `338`
  - `0.10-0.20`: `1`
  - `0.20-0.80`: `0`
  - `>0.80`: `1426`

Lectura:

- el `0` no demuestra ausencia de traders comparables en el mercado total
- demuestra ausencia de trades comparables en el top-volume inmediato que el pipeline decidió mirar

### Con `40` mercados

- wallets vistas: `1257`
- sobreviven al prefilter de precio: `30`
- caen por `min_trades`: `29`
- cae por `min_markets`: `1`
- pasan: `0`

Lectura:

- en ventanas pequeñas, la combinacion `slice top-volume + prefilter por precio + min_trades/min_markets` destruye la muestra

### Con `200` mercados

- wallets vistas: `3113`
- sobreviven al prefilter de precio: `830`
- caen por `min_trades`: `467`
- caen por `min_markets`: `88`
- pasan filtros actuales: `275`

### Con `434` mercados

- wallets vistas: `3283`
- sobreviven al prefilter de precio: `889`
- caen por `min_trades`: `488`
- caen por `min_markets`: `90`
- pasan filtros actuales: `311`

Diagnostico:

- el gran hachazo no es `avg_price`
- el gran hachazo es el prefilter trade-level por precio combinado con un universo de mercados demasiado estrecho

## Ejemplos de perfiles observados

### Traders mixtos con actividad comparable real

Hay traders conocidos del repo que son extremos en el agregado global, pero muestran actividad comparable real no trivial.

Ejemplos:

- `Academic-Maniac`
  - `all_markets=182`
  - `all_avg_price=0.94`
  - `in_trades=73`
  - `in_markets=25`
  - `in_avg_price=0.5863`

- `White-Donkey`
  - `all_markets=190`
  - `all_avg_price=0.9488`
  - `in_trades=62`
  - `in_markets=24`
  - `in_avg_price=0.5783`

- `Motionless-Stalk`
  - `all_markets=165`
  - `all_avg_price=0.8816`
  - `in_trades=51`
  - `in_markets=16`
  - `in_avg_price=0.6361`

Lectura:

- si se usara `avg_price` global simple como criterio duro, estos traders parecerian no comparables
- pero si se observa su actividad comparable parcial, si son informativos para nuestro universo

### Traders mas "puros" dentro del rango comparable

Tambien aparecen wallets con una fraccion alta de actividad comparable:

- `Tame-Scalp`
  - `in_trade_ratio=0.677`
  - `in_markets=19`

- `0x8f936dbe`
  - `in_trade_ratio=0.750`
  - `in_markets=17`

- `0x643d91fe`
  - `in_trade_ratio=0.704`
  - `in_markets=17`

- `Wilted-Eyeglasses`
  - `in_trade_ratio=0.797`
  - `in_markets=9`
  - top ciudades comparables: `Seattle`, `Munich`, `Chengdu`, `Chicago`

Lectura:

- hoy si existen traders bastante comparables al tipo de entradas que nos interesan
- no son una ilusion metodologica

## Juicio provisional de Codex

### Lo que si parece cierto

- el mercado direccional actual esta dominado por extremos
- el top-volume de muy corto plazo puede quedar casi sin comparables
- por eso un refresh estrecho puede devolver `0`

### Lo que no esta bien demostrado por el sistema actual

- que "hoy casi no hay traders comparables"
- esa conclusion es demasiado fuerte para la evidencia que el censo actual realmente recolecta

### Diagnostico provisional

La conclusion correcta no es:

- `no hay traders comparables`

La conclusion correcta es mas bien:

- `el pipeline actual mira un slice demasiado estrecho y aplica el filtro comparable demasiado pronto`

## Preguntas abiertas que queremos que Opus resuelva

1. Conceptualmente, ¿cuál debe ser la definicion correcta de "trader comparable" para nuestro sistema?
2. ¿Debemos tratar como comparables solo a traders con alta pureza dentro del rango, o tambien a traders mixtos con suficiente actividad comparable parcial?
3. ¿El rango `0.20-0.80` es una buena definicion primaria de comparabilidad, o deberia cambiarse por algo mas matizado?
4. ¿La comparabilidad debe medirse por:
   - trade-level inclusion
   - market-level average
   - share of activity in comparable range
   - o una combinacion de señales?
5. ¿Es metodologicamente correcto que `city-intelligence` refresque el censo con solo `20` mercados, si el objetivo es descubrir traders comparables y no solo medir top-volume extremo?
6. ¿Cual es el siguiente cambio mas alineado con el objetivo del sistema sin contaminarlo con sobreingenieria?

## Opciones concretas para que Opus juzgue

### Opcion A

Mantener el rango `0.20-0.80`, pero:

- ampliar universo de mercados escaneados
- separar metrica `all_activity` de `comparable_activity`
- rankear por `comparable_markets`, `comparable_trades`, `comparable_notional`

### Opcion B

Mantener universo amplio, pero redefinir comparabilidad como:

- wallet con al menos `N` mercados con `market-level avg price` comparable
- sin exigir que la media global de la wallet sea comparable

### Opcion C

Separar dos clases de traders:

- `pure_comparable`
- `mixed_but_informative`

y dejar que las etapas posteriores del sistema usen una u otra clase según el caso.

## Lo que no queremos de la respuesta de Opus

- un resumen complaciente
- una defensa automática del diseño actual
- una propuesta vaga de "ampliar datos" sin criterio metodologico

## Lo que si queremos de la respuesta de Opus

- una decision fuerte
- un juicio metodologico claro
- un criterio explicito para distinguir:
  - extremo puro
  - mixto util
  - comparable real
- una recomendacion concreta del siguiente cambio mas util

