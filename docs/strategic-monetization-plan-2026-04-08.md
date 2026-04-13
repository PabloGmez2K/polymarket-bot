# Plan operativo - monetizacion incremental

**Fecha de planificacion:** 8 de abril de 2026
**Base analitica:** `RESEARCH_CODEX_TRADERS_2026-04-08.md` + `RESEARCH_OPUS_TRADERS_2026-04-08.md`
**Objetivo:** convertir la investigacion de traders y edge en una secuencia operativa pequena, trazable y retomable por Codex o Claude sin tocar el core antes de tener evidencia nueva.

---

## Direccion elegida

No vamos a saltar todavia a:

- cambiar el modelo forecast;
- abrir `exact/range`;
- subir frecuencia real;
- subir bankroll;
- ni reescribir la logica de entrada/salida.

Primero vamos a medir dos cuellos de botella con herramientas read-only:

1. **Settlement fidelity**
   - cuanto difieren `Open-Meteo`, la capa observada disponible y el precio de mercado.
   - si el gap mas importante parece venir de la fuente / settlement gap.

2. **Directional trader census**
   - que wallets operan de verdad en `at_or_above` / `at_or_below`.
   - si esas wallets parecen forecast traders, structure traders o perfiles de timing.

---

## Orden de ejecucion

### Fase 1 - Settlement Fidelity Probe v1

**Estado:** en implementacion

**Objetivo**

Dejar una herramienta independiente que, para mercados direccionales activos, genere una foto legible de:

- mercado y precio implicito;
- forecast `Open-Meteo`;
- metadata de resolucion (`icao`, `wu_url`);
- proxy observado NOAA cuando la fecha ya este resuelta y haya datos;
- gaps medibles para decidir si el problema principal es fuente/modelo o seleccion.

**Entregables**

- `tools/settlement_fidelity_probe.py`
- `docs/settlement-fidelity-probe.md`
- salida por defecto:
  - `data/settlement_fidelity_probe.json`
  - `docs/settlement_fidelity_probe_latest.md`

**Preguntas que debe responder**

1. Que mercados direccionales activos estamos viendo hoy.
2. En que ciudades tenemos metadata de resolucion y NOAA util.
3. Cuantos mercados tienen `forecast Open-Meteo` disponible.
4. Cuando el mercado ya es pasado, cuanto se desvia `Open-Meteo` del observado NOAA.
5. Que huecos impiden todavia una comparacion mas cercana a settlement.

**Guardrails**

- no toca `bot.py`;
- no cambia decision engine ni scheduler;
- no escribe sobre archivos productivos del bot;
- solo produce artefactos analiticos nuevos.

### Fase 2 - Directional Trader Census v1

**Estado:** pendiente

**Objetivo**

Rehacer el descubrimiento de traders para el universo operable real del bot:

- solo `at_or_above`
- solo `at_or_below`

**Entregables previstos**

- `tools/directional_trader_census.py`
- `docs/directional-trader-census.md`
- salida por defecto:
  - `data/directional_trader_census.json`
  - posible DB separada, no mezclar de inicio con `traders_db.json`

**Preguntas que debe responder**

1. Que wallets operan mercados direccionales hoy.
2. Que ciudades y horizontes concentran.
3. Si se parecen a forecast traders, timing traders o settlement-aware traders.
4. Si existe una shortlist de wallets realmente comparable a nuestra operativa.

### Fase 3 - Gate de decision

**Estado:** pendiente

No se toca estrategia hasta cruzar Fase 1 + Fase 2 y responder:

1. El gap dominante parece ser `fuente/settlement`, `timing`, `market selection` o `microstructure`.
2. Existe una mejora pequena y trazable con mejor ROI que tocar el core.

---

## Entregable minimo de esta sesion

La sesion se considera bien cerrada si deja:

- plan operativo persistido en el repo;
- Fase 1 implementada al menos como herramienta ejecutable y documentada;
- handoff claro para que Claude pueda continuar Fase 1 o arrancar Fase 2 sin reinterpretar la estrategia.

---

## Handoff para Claude

Si Claude retoma desde aqui, el punto correcto es:

1. leer `docs/ESTRATEGIA_OPERATIVA.md`;
2. leer `RESEARCH_CODEX_TRADERS_2026-04-08.md`;
3. leer `RESEARCH_OPUS_TRADERS_2026-04-08.md`;
4. leer este plan;
5. continuar desde la fase marcada como `pendiente` mas cercana.

### Regla de continuidad

Claude no debe reinterpretar el objetivo como "mejorar ya el bot". Debe seguir el orden:

1. observabilidad read-only,
2. evidencia,
3. solo despues propuesta de cambio funcional.

---

## Proxima accion concreta

**Implementar y validar `tools/settlement_fidelity_probe.py`.**

Si esa herramienta queda estable:

- correrla localmente con una muestra pequena;
- revisar la salida;
- y abrir despues la Fase 2 sobre traders direccionales.
