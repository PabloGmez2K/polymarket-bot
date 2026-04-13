# Shadow Opportunity Shortlist - 2026-04-11

## Objetivo

Separar ciudades con señal shadow repetida de:

- casos ya absorbidos por runtime canary;
- casos aislados;
- casos que hoy se frenan por restricciones estructurales antes de convertirse en throughput operable.

Todo en modo read-only, sin tocar `bot.py`, policy live, thresholds, allowlists ni bankroll.

## Fuente

- `data/runtime_import/shadow_city_tracking.json`
- `data/runtime_import_derived/city_validation_ledger.runtime_import.json`
- `data/runtime_import/skip_log.jsonl`

## Lectura Rapida

Las ciudades con mas `edge_hits` recientes en shadow tracking no implican automaticamente "abrir throughput".

Patron observado:

1. varias de las ciudades con señal fuerte ya fueron absorbidas por `auto_canary` y por eso ya no son candidatas a "siguiente ciudad shadow a promover manualmente";
2. otras ciudades tienen edge histórico, pero siguen chocando con restricciones estructurales (`condition_filtered`, `date/time gating`, `price_out_of_range`) o con baja calidad de evidencia;
3. Chicago sigue siendo el caso exploratorio mas interesante para vigilar, pero con la evidencia actual sigue siendo una señal aislada, no repetida.

## Top Shadow Cities Por Repeticion Bruta

Snapshot reciente de `shadow_city_tracking.json`:

- `Shanghai`: `edge_hits=19`, `cycles_seen=31`, `best_edge_pct=38.7`
- `Dallas`: `edge_hits=8`, `cycles_seen=5`, `best_edge_pct=45.8`
- `Lucknow`: `edge_hits=8`, `cycles_seen=4`, `best_edge_pct=47.4`
- `New York City`: `edge_hits=6`, `cycles_seen=16`, `best_edge_pct=47.3`
- `Atlanta`: `edge_hits=5`, `cycles_seen=13`, `best_edge_pct=31.5`
- `Istanbul`: `edge_hits=5`, `cycles_seen=4`, `best_edge_pct=37.9`
- `Sao Paulo`: `edge_hits=4`, `cycles_seen=8`, `best_edge_pct=52.8`
- `Tokyo`: `edge_hits=4`, `cycles_seen=8`, `best_edge_pct=28.3`
- `Beijing`: `edge_hits=3`, `cycles_seen=7`, `best_edge_pct=24.1`
- `Munich`: `edge_hits=3`, `cycles_seen=4`, `best_edge_pct=24.3`
- `Seoul`: `edge_hits=2`, `cycles_seen=28`, `best_edge_pct=15.0`
- `Hong Kong`: `edge_hits=2`, `cycles_seen=5`, `best_edge_pct=37.9`

## Shortlist Operativa

### 1. Ya absorbidas por runtime canary

Estas ciudades ya no son la siguiente frontera de decision manual:

- `Shanghai`
- `Atlanta`
- `New York City`
- `Munich`
- `Tokyo`
- `Seoul`

Lectura:

- su señal shadow histórica ya cumplió la función de alimentar `auto_canary`;
- si se quiere debatir algo sobre ellas, ya no es "promocion shadow", sino evaluación de throughput/policy sobre canaries existentes.

### 2. Interesantes pero no listas para decision

- `Chicago`
  - `edge_hits=1`, `cycles_seen=7`, `best_edge_pct=35.1`
  - caso reciente relevante: `fuera_allowlist` el `2026-04-09T23:00`
  - al ciclo siguiente cae a `below_min_edge=6.48%`
  - despues vuelve a `condition_filtered` en mercados `range`
  - lectura: sigue siendo la ciudad exploratoria mas interesante, pero no hay repeticion suficiente

- `Hong Kong`
  - `edge_hits=2`, `cycles_seen=5`, `best_edge_pct=37.9`
  - en skips recientes aparece repetidamente en `below_min_edge` alrededor de `10%`
  - lectura: hay señal, pero no sostenida por encima del umbral actual

- `Beijing`
  - `edge_hits=3`, `cycles_seen=7`, `best_edge_pct=24.1`
  - en los ciclos recientes visibles termina otra vez en `condition_filtered`
  - lectura: mas consistente que Chicago en volumen histórico, pero no emerge hoy como caso operable nuevo

### 3. Casos con edge histórico pero mala base actual para actuar

- `Lucknow`
- `Istanbul`
- `Sao Paulo`
- `Dallas`

Lectura:

- tienen `edge_hits` altos en tracking bruto;
- pero en esta fase no son buen siguiente paso operativo porque faltan mejores garantías de visibilidad, comparabilidad o encaje con el contrato actual;
- en `Dallas`, ademas, ya sabemos que no debe reabrirse manualmente mientras runtime la mantenga fuera.

## Restricciones Estructurales Que Siguen Ganando

Desde `2026-04-07`, las ciudades con mas `condition_filtered` en `skip_log.jsonl` son:

- `Seoul`: `33`
- `New York City`: `25`
- `Shanghai`: `22`
- `Miami`: `18`
- `London`: `17`
- `Beijing`: `12`
- `Wellington`: `11`
- `Atlanta`: `11`
- `Sao Paulo`: `9`
- `Buenos Aires`: `7`
- `Tokyo`: `6`
- `Ankara`: `6`

Lectura:

- muchas ciudades con señal útil no mueren por falta de edge, sino porque el mercado visible cae en `exact/range` y hoy esa rama esta fuera del scope;
- esto refuerza que el principal cuello actual sigue siendo estructural, no simplemente "faltan mejores ciudades".

## Conclusion

La shortlist de vigilancia real queda asi:

1. `Chicago` como principal caso exploratorio a observar por si repite oportunidades shadow operables.
2. `Hong Kong` y `Beijing` como secundarios, pero sin fuerza suficiente todavia para escalar.
3. Las canaries runtime actuales ya no deben contaminar la pregunta "que ciudad shadow nueva merece accion".

## Siguiente Paso Recomendado

Seguir observando en read-only y pedir una revision de Opus solo si ocurre una de estas dos cosas:

- `Chicago` acumula varias oportunidades shadow operables y consistentes;
- aparece una contradiccion nueva entre tracking shadow, funnel y policy efectiva que huela a bug de correctness en vez de restriccion estructural.
