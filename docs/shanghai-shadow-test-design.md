# Shanghai Shadow Test Design

**Fecha:** 2026-04-08
**Estado:** design-only
**Objetivo:** definir un test en `shadow` para `Shanghai` que permita medir si esta ciudad merece una futura prueba controlada, sin tocar todavia el core de trading.

---

## Por que Shanghai

Shanghai es hoy la mejor ciudad puente entre research y operativa:

- `policy_mode=shadow`, asi que ya encaja con la regla canonica del repo para observar sin comprar;
- tiene `4` traders de referencia comparables al universo actual;
- aparecio con `2` mercados visibles en el snapshot reciente del probe;
- ya tiene metadata de resolucion y NOAA configurada en `RESOLUTION_ICAO` y `OBSERVED_AUDIT_CITIES`.

La prioridad no viene de intuicion abstracta, sino de evidencia ya persistida en:

- `data/reference_trader_city_market_cross.json`
- `data/city_watchlist_phase4.json`
- `data/city_watch_reinforced.json`

---

## Baseline actual

El baseline vigente del bot sigue siendo:

- `Open-Meteo decide`
- `NOAA mide`
- `Weather Underground resuelve`
- universo operable real: `at_or_above` y `at_or_below`
- `MIN_EDGE = 15%`
- sizing `Half-Kelly`
- ciudad fuera de allowlist -> `shadow`

Este test **no** cambia ese baseline. Solo busca responder si `Shanghai` merece un siguiente escalon de observabilidad o un futuro test controlado.

---

## Estado actual de Shanghai

### Policy y observabilidad

- modo actual: `shadow`
- `RESOLUTION_ICAO["Shanghai"]` existe con `icao=ZSPD`
- `Shanghai` ya forma parte de `OBSERVED_AUDIT_CITIES`
- por tanto la ciudad es observable sin necesidad de pasarla a `active`

### Evidencia trader comparable

Referencias detectadas en fases previas:

- `Academic-Maniac` - `high_priority_reference`
- `Entire-Hood` - `high_priority_reference`
- `Motionless-Stalk` - `high_priority_reference`
- `White-Donkey` - `candidate_reference`

### Snapshot reciente de mercado

Ultimo probe visible:

- `at_or_below 13C` con `market_prob_yes=0.0` y `Open-Meteo=15.5C`
- `at_or_above 23C` con `market_prob_yes=0.002` y `Open-Meteo=15.5C`

Lectura:

- el snapshot visto no era una oportunidad de edge para nuestro baseline;
- aun asi confirma que Shanghai tiene mercado visible y trazable dentro del pipeline read-only;
- el valor del test no es forzar trades, sino medir si la ciudad genera suficiente señal shadow y suficiente comparabilidad con traders de referencia.

### Limitacion honesta hoy

En local no habia base persistida live de `shadow_city_tracking.json` ni `audit.json`, asi que este diseno debe asumir que la validacion fuerte se apoyara en futuros snapshots y/o datos live, no solo en el repo local.

---

## Preguntas que debe responder el test

1. `Shanghai` genera suficientes oportunidades shadow direccionales bajo nuestro baseline actual.
2. Cuando aparecen oportunidades, estan alineadas o desalineadas con traders de referencia comparables.
3. El cuello de botella dominante en Shanghai parece ser:
   - seleccion de mercado
   - timing de entrada/salida
   - settlement/source gap
   - o simple falta de edge
4. La ciudad merece:
   - seguir en `shadow` sin cambios
   - pasar a observabilidad reforzada permanente
   - o preparar un futuro test controlado mas cercano a `canary`

---

## Alcance del test

### Incluye

- observacion read-only de mercados `Shanghai` en `at_or_above` y `at_or_below`
- snapshot de precio, forecast y metadatos de resolucion
- lectura de huella shadow local cuando exista (`shadow_city_tracking`)
- cruce con traders de referencia ya detectados
- documentacion de hipotesis y decision al cierre

### No incluye

- mover `Shanghai` a `canary` o `active`
- cambiar `MIN_EDGE`, sizing o decision engine
- introducir nuevas fuentes decisoras en el core
- abrir `exact` o `range`
- alterar scheduler, exits o reglas de entrada

---

## Artefactos a usar

### Entradas ya existentes

- `data/city_watch_reinforced.json`
- `data/reference_trader_city_market_cross.json`
- `data/directional_trader_enrichment.json`
- `data/settlement_fidelity_probe.json`
- `bot.py` como fuente de verdad para thresholds y semantica de modos

### Artefactos recomendados para la siguiente implementacion

- `data/shanghai_shadow_test.json`
- `docs/shanghai_shadow_test_latest.md`

No deben mezclarse con artefactos productivos del runtime.

---

## Metricas del test

### A. Senal propia del baseline

Medir por ventana de observacion:

- mercados `Shanghai` evaluados
- oportunidades shadow totales
- oportunidades con `edge_hit=True`
- mejor `edge_pct`
- ciclos con senal
- distribucion por `at_or_above` vs `at_or_below`
- distancia forecast-threshold

### B. Calidad observacional

Medir:

- si hay `Open-Meteo` disponible
- si la ciudad sigue resolviendo correctamente por `icao/wu_url`
- si aparece `NOAA observado` una vez madure la fecha
- gap `Open-Meteo vs NOAA observado` cuando exista

### C. Comparabilidad trader

Para cada snapshot con mercado Shanghai:

- referencias presentes para la ciudad
- si hay actividad trader comparable reciente o solo historial cerrado
- si nuestra lectura cae del mismo lado del mercado que la referencia visible
- si la divergencia parece de `timing`, `selection` o `forecast`

### D. Gate de continuidad

Usar dos planos distintos:

- `gate interno del bot`: los criterios ya existentes de `shadow -> canary`
  - `SHADOW_CANARY_MIN_EDGE_HITS = 2`
  - `SHADOW_CANARY_MIN_CYCLES = 2`
  - `SHADOW_CANARY_MIN_BEST_EDGE = MIN_EDGE`
  - `SHADOW_CANARY_MIN_SUPPORT = 2`
- `gate del experimento`: evidencia suficiente para justificar una conversacion sobre siguiente paso

El test no promociona por si solo; solo produce evidencia para decidir.

---

## Criterios de exito del experimento

El test se considerara util si deja una conclusion clara en una de estas categorias:

### Resultado A - `No signal`

- Shanghai casi no genera oportunidades shadow reales
- o las genera solo en precios/condiciones no comparables

Accion:

- mantener `shadow`
- no abrir siguiente fase hasta nueva evidencia

### Resultado B - `Signal but weak monetization case`

- hay senal shadow, pero no aparece confirmacion por traders comparables
- o el settlement/source gap hace la lectura poco fiable

Accion:

- reforzar observabilidad
- no tocar trading core todavia

### Resultado C - `Promising bridge city`

- hay senales shadow repetidas
- NOAA / resolucion son trazables
- y la ciudad sigue apareciendo en referencias comparables o snapshots utiles

Accion:

- abrir propuesta de `test controlado` posterior
- sin saltar directamente a `active`

---

## Orden recomendado de implementacion

1. Crear extractor read-only especifico para Shanghai.
2. Guardar snapshot estructurado separado del probe general.
3. Generar readout markdown corto por corrida.
4. Esperar varias corridas o una pequena ventana temporal antes de concluir.
5. Cerrar con decision explicita: `stay shadow`, `expand observability`, o `prepare controlled test`.

---

## Forma minima de la siguiente herramienta

Nombre sugerido:

- `tools/shanghai_shadow_test.py`

Salida minima esperada:

```json
{
  "generated_at": "ISO8601",
  "city": "Shanghai",
  "policy_mode": "shadow",
  "probe_markets": [],
  "shadow_tracking": {
    "markets_seen": 0,
    "edge_hits": 0,
    "cycles_seen": 0,
    "best_edge_pct": 0.0
  },
  "reference_traders": [],
  "assessment": {
    "signal_status": "none|building|promising",
    "data_quality": "weak|ok|strong",
    "next_action": "stay_shadow|expand_observability|prepare_controlled_test"
  }
}
```

---

## Handoff para Claude

Si Claude retoma desde aqui, el siguiente punto correcto es:

1. leer este documento;
2. leer `docs/city_watch_reinforced_latest.md`;
3. leer `data/city_watch_reinforced.json`;
4. implementar solo la capa read-only del test Shanghai;
5. no reinterpretar esta fase como permiso para cambiar `bot.py`.

Regla de continuidad:

- primero `snapshot + evidencia`
- luego `decision`
- y solo despues, si hay base real, propuesta de test controlado

---

## Decision de esta sesion

Queda aprobado el siguiente paso operativo:

- **implementar un extractor read-only especifico para `Shanghai`**, separado del core y separado del probe general, para medir si la ciudad merece una fase posterior de test controlado.
