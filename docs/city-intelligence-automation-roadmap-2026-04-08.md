# City Intelligence Automation Roadmap

## Objetivo

Diseñar una automatización read-only que aprenda de los traders exitosos que
operan en mercados comparables a nuestro universo actual y convierta esa
evidencia en una capa de recomendación operativa por ciudad.

La meta no es copiar trades ni tocar el core del bot por inercia. La meta es
acumular evidencia suficiente para responder, con trazabilidad:

- qué ciudades merecen más observabilidad;
- qué ciudades deberían entrar en una watchlist `shadow` reforzada;
- qué ciudades activas sirven como benchmark;
- qué traders parecen realmente comparables a nuestra operativa;
- y si las lecciones útiles vienen de selección, timing, estructura o fuente.

## Estado de Validación

Decisión vigente tras revisión estratégica independiente:

- `GO WITH CHANGES`

La automatización sigue teniendo sentido, pero solo si se implementa como una
capa de evidencia más estricta y no como un motor prematuro de ranking. La
versión validada de este roadmap incorpora cuatro correcciones obligatorias:

- separar `visibility_evidence` de `edge_evidence`;
- modelar `settlement_fidelity` / source-fidelity por ciudad;
- aplicar `timestamp + temporal_decay` a toda evidencia acumulada;
- bloquear recomendaciones fuertes cuando haya `insufficient_evidence`.

## Contexto Estratégico

Trabajo ya completado en este frente:

- baseline de la estrategia actual documentado en `docs/ESTRATEGIA_OPERATIVA.md`;
- research comparativo de traders en `RESEARCH_CODEX_TRADERS_2026-04-08.md`;
- contraste independiente con Opus;
- pipeline read-only de fase 5 desplegada en Railway;
- alerta Telegram cuando aparezca una coincidencia nueva `Shanghai + Chicago`;
- evidencia inicial de que el gap dominante observado hoy es
  `market_visibility_and_selection`.

Conclusión actual: antes de tocar el core, necesitamos una capa automática que
convierta actividad relevante de traders comparables en evidencia acumulativa
por ciudad.

## Resultado Esperado

Un sistema que produzca, de forma periódica:

1. un mapa de ciudades visibles en mercados comparables;
2. un mapa de traders de referencia por ciudad;
3. un ledger acumulativo de evidencia por ciudad;
4. una lectura legible de evidencia suficiente vs insuficiente por ciudad;
5. solo después, un ranking dinámico de ciudades por valor estratégico;
6. solo después, alertas accionables cuando una ciudad gane suficiente señal;
7. una recomendación explícita por ciudad:
   `ignore`, `observe`, `insufficient_evidence`, `watch_closely`,
   `shadow_reinforced`, `review_policy`, `candidate_for_controlled_test`.

## No Objetivos

- no copiar posiciones automáticamente;
- no abrir trades por seguimiento de wallets;
- no cambiar `bot.py`, `MIN_EDGE`, Kelly, scheduler o execution;
- no reinterpretar actividad visible como alpha real sin evidencia histórica;
- no promover una ciudad a `active/canary` automáticamente;
- no confundir `más actividad visible` con `más edge para nuestro modelo`;
- no emitir recomendaciones fuertes con muestra insuficiente o envejecida.

## Preguntas que debe responder la automatización

1. Qué traders exitosos son realmente comparables a nuestro universo actual.
2. En qué ciudades aparecen repetidamente esos traders.
3. Si una ciudad concentra actividad de calidad o solo actividad bruta.
4. Si una ciudad se repite por selección de mercados, por timing o por estructura.
5. Si una ciudad hoy `blocked`, `shadow` o no priorizada merece revisión.
6. Qué ciudades deben entrar en observabilidad reforzada antes de cualquier test.

## Principios de Diseño

- `read-only first`
- `evidence over speculation`
- `city-centric, not wallet-centric only`
- `separate visibility from edge`
- `recency matters more than raw accumulation`
- `insufficient evidence is a valid output`
- `separate active benchmark from shadow candidate`
- `one recommendation per city, with rationale`
- `never collapse visibility into automatic strategy change`
- `all outputs versioned or persisted with clear provenance`

## Guardrails Metodológicos

Antes de derivar cualquier recomendación por ciudad, el sistema debe respetar
estas reglas:

1. `visibility_evidence` y `edge_evidence` viven en campos separados.
   Ver traders comparables en una ciudad no basta para asumir que nuestro bot
   tendría ventaja allí.
2. `settlement_fidelity` es una dimensión de primer nivel del ledger.
   Una ciudad con visibilidad alta pero con mala alineación de fuentes no debe
   verse como candidata fuerte.
3. Toda evidencia lleva `first_seen_at`, `last_seen_at` y ponderación por
   recencia.
   Señales viejas deben perder peso de forma explícita.
4. Con menos de `3` traders de referencia activos e independientes y menos de
   `5` snapshots útiles, la salida por defecto debe ser
   `insufficient_evidence`.
5. El sistema debe poder decir "no sé" sin inventar estabilidad.

## Flujo Propuesto

### 1. Comparable Trader Universe

Input:

- outputs existentes de `directional_trader_census`
- outputs existentes de `directional_trader_enrichment`
- filtros del universo vigente (`at_or_above`, `at_or_below`)

Proceso:

- excluir traders no comparables por tipo de mercado;
- priorizar traders con evidencia de `closed positions`, `win rate`, `cash PnL`;
- clasificar estilo operativo por trader:
  `forecast_like`, `selection_like`, `timing_like`, `structure_like`, `mixed`.

Output:

- shortlist viva de `reference traders`
- score de comparabilidad por trader

### 2. Trader-City Linker

Input:

- shortlist de traders de referencia
- mercados activos/recientes comparables
- posiciones activas/cerradas observables

Proceso:

- asociar trader -> ciudad -> fecha -> tipo de contrato -> precio medio;
- detectar recurrencias por ciudad;
- separar presencia histórica y presencia activa;
- distinguir ciudades dominadas por uno o varios traders fuertes;
- registrar `first_seen_at`, `last_seen_at`, `days_since_last_seen`;
- dejar explícito si la señal de una ciudad depende de un solo trader dominante.

Output:

- tabla trader-ciudad
- score por pareja `trader x city`

### 3. City Evidence Ledger

Input:

- visibility tracker
- settlement probe
- trader-city linker
- snapshots Shanghai/Chicago y futuros equivalentes

Proceso:

- acumular por ciudad:
  - `n_visible_snapshots`
  - `n_visible_with_reference_traders`
  - `n_reference_traders`
  - `n_active_reference_traders`
  - `visibility_evidence`
  - `edge_evidence`
  - `policy_mode`
  - `probe_markets_seen`
  - `conditions_seen`
  - `lead_times_seen`
  - `settlement_fidelity_score`
  - `om_wu_delta_proxy`
  - `source_fidelity_risk`
  - `last_seen_at`
  - `first_seen_at`
  - `temporal_decay_weight`
  - `benchmark_overlap_count`
  - `observability_quality`
- guardar histórico incremental sin perder snapshots previos;
- marcar explícitamente `evidence_status`:
  `insufficient`, `building`, `actionable`;
- no derivar `edge_evidence` solo desde wallets visibles.

Output:

- ledger persistente por ciudad
- resumen latest

### 4. City Ranking Engine

Input:

- city evidence ledger
- policy actual del bot
- comparabilidad con nuestro universo

Proceso:

- puntuar cada ciudad por dimensiones separadas:
  - `reference_trader_density`
  - `visibility_recurrence`
  - `comparability_to_bot`
  - `observability_quality`
  - `settlement_fidelity`
  - `policy_alignment`
  - `benchmark_value`
- derivar una recomendación final con rationale;
- bloquear recomendaciones fuertes si `evidence_status != actionable`.

Output:

- ranking dinámico de ciudades
- recomendación operativa por ciudad

### 5. Alerts and Review Triggers

Input:

- ranking dinámico
- cambios del ledger
- coincidencias o cambios de estado

Proceso:

- alertar cuando:
  - una ciudad supera un umbral de evidencia;
  - una ciudad `blocked` acumula demasiada señal externa;
  - una ciudad `shadow` gana densidad suficiente de traders fuertes;
  - una ciudad `active` pierde relevancia frente a otras;
  - aparece una coincidencia benchmark útil.

Output:

- alertas Telegram resumidas
- snapshot post-alerta para lectura humana/LLM

## Arquitectura Propuesta

### Artefactos nuevos

- `tools/city_reference_ledger.py`
- `tools/trader_city_linker.py`
- `tools/city_ranking_engine.py`
- `tools/city_intelligence_pipeline.py`
- `tools/city_intelligence_telegram_alert.py`

### Datos persistidos

- `data/trader_city_linker.json`
- `data/city_reference_ledger.json`
- `data/city_ranking_engine.json`
- `data/city_intelligence_pipeline.json`
- `data/city_intelligence_alert_state.json`

### Runbooks / docs

- `docs/city-reference-ledger.md`
- `docs/trader-city-linker.md`
- `docs/city-ranking-engine.md`
- `docs/city-intelligence-pipeline.md`
- `docs/city-intelligence-alerts.md`

## Hoja de Ruta por Fases

### Fase A — Diseño y validación estratégica

Objetivo:

- validar que la automatización persigue la señal correcta;
- confirmar que no estamos confundiendo actividad visible con edge real.

Entregables:

- este roadmap;
- revisión crítica por Claude Opus;
- lista de objeciones/gaps antes de implementar.

Gate:

- no empezar implementación hasta que Opus valide o corrija el enfoque.

### Fase B — Trader-City Linker v1

Objetivo:

- construir la primera tabla persistente de `trader x city`.

Entregables:

- `tools/trader_city_linker.py`
- `data/trader_city_linker.json`
- `docs/trader-city-linker.md`

Gate:

- comprobar que identifica recurrentemente `Shanghai`, `Chicago`, `Wuhan`,
  `Seoul`, `Ankara` u otras ciudades con señal comparable;
- comprobar que puede distinguir `recurring_city_signal` de
  `single_trader_dependency`;
- incluir timestamps y recencia desde v1.

### Fase C — City Evidence Ledger v1

Objetivo:

- convertir actividad recurrente en evidencia acumulativa por ciudad.

Entregables:

- `tools/city_reference_ledger.py`
- `data/city_reference_ledger.json`
- `docs/city-reference-ledger.md`

Gate:

- cada ciudad debe tener rationale legible aunque el score aún sea básico;
- cada ciudad debe separar `visibility_evidence` vs `edge_evidence`;
- cada ciudad debe incluir `settlement_fidelity` y estado
  `insufficient/building/actionable`.

### Fase C' — Pausa de evaluación

Objetivo:

- comprobar si el ledger produce señal diferenciada real antes de automatizar
  ranking o alertas.

Entregables:

- revisión manual/LLM del ledger tras al menos `1-2` semanas de acumulación;
- decisión explícita `continue` / `stop` / `redesign`.

Gate:

- no pasar a ranking si el sistema no puede distinguir de forma estable entre
  ciudades prioritarias y ciudades con evidencia insuficiente;
- no pasar a ranking si la salida sigue dominada por `N` pequeño o por un solo
  trader.

### Fase D — Ranking Engine v1

Objetivo:

- derivar recomendaciones operativas por ciudad.

Entregables:

- `tools/city_ranking_engine.py`
- `data/city_ranking_engine.json`
- `docs/city-ranking-engine.md`

Gate:

- ranking interpretable para humano y para Claude;
- ranking bloqueado automáticamente cuando una ciudad esté en
  `insufficient_evidence`;
- no promover ciudades automáticamente a trading.

### Fase E — Pipeline y alertas

Objetivo:

- automatizar todo el flujo en Railway, separado del bot principal.

Entregables:

- `tools/city_intelligence_pipeline.py`
- `tools/city_intelligence_telegram_alert.py`
- servicio Railway separado, análogo a `phase5-visibility`

Gate:

- alertas útiles, sin spam;
- no alertar sobre ciudades cuya evidencia siga siendo `insufficient`;
- outputs persistentes y consistentes.

### Fase F — Review de estrategia

Objetivo:

- usar la evidencia acumulada para proponer mejoras de estrategia.

Entregables:

- informe de lectura de evidencia;
- propuestas separadas en:
  - `research`
  - `observability`
  - `future strategy changes`

Gate:

- ninguna propuesta toca el core sin revisión explícita.

## Métricas Clave

- `reference_traders_per_city`
- `successful_reference_traders_per_city`
- `active_reference_presence_rate`
- `city_visibility_recurrence`
- `single_trader_dependency_rate`
- `evidence_freshness`
- `settlement_fidelity_score`
- `insufficient_evidence_rate`
- `benchmark_overlap_count`
- `comparable_market_count`
- `city_recommendation_stability`
- `policy_mismatch_count`

## Riesgos a vigilar

- sobreajuste a wallets ruidosas;
- confundir market-making o rewards con alpha;
- confundir ciudades frecuentes con ciudades rentables;
- confundir `visibility_evidence` con `edge_evidence`;
- dejar que evidencia vieja siga pesando como si fuera actual;
- sobrediseñar infraestructura antes de validar que existe señal útil;
- sesgo por falta de simultaneidad entre snapshots;
- promover una ciudad solo por narrativa;
- drift entre la policy del bot y la inteligencia de research.

## Criterios de Éxito

La automatización habrá valido la pena si consigue:

1. explicar con evidencia qué ciudades merecen `shadow` reforzado;
2. detectar ciudades ignoradas por la policy actual pero repetidas por traders fuertes;
3. separar claramente ciudades benchmark de ciudades candidatas;
4. distinguir con honestidad entre `evidencia útil` y `insufficient_evidence`;
5. producir recomendaciones estables y legibles;
6. reducir la incertidumbre antes de tocar la estrategia.

## Relación con Claude Opus

Rol esperado de Claude Opus:

- revisar el diseño estratégico, no reimplementar todavía;
- buscar sesgos, agujeros lógicos y riesgos de inferencia;
- decir si la automatización propuesta sirve realmente para aprender estrategia;
- aprobar o corregir el enfoque antes de que Codex implemente.

Salida esperada de Opus:

- `GO`
- `GO WITH CHANGES`
- `NO-GO`

Con justificación explícita y recomendaciones priorizadas.
