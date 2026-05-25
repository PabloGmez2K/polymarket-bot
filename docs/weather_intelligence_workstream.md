# External Weather Intelligence Workstream

**Estado:** ACTIVE_RESEARCH — documentado para referencia y backlog  
**Creado:** 2026-05-25 (Sesión 387 — Sonnet)  
**Última actualización:** 2026-05-25 (Sesión 389 — Sonnet, docs-only: source fidelity sweep post-T+24)  
**Contexto durable:** [CONTEXTO.md](../CONTEXTO.md) §Sesiones 387–389  
**Archivo de fuentes externas:** [docs/research_inputs/external_weather_claims_2026-05-24.md](research_inputs/external_weather_claims_2026-05-24.md) — EXTERNAL_SOURCE_ARCHIVE / NO AUTHORITATIVE  

---

## Estado operativo al momento de escritura (2026-05-25)

- `SHADOW_ONLY_MODE=false` — trading real activo.
- `BANKROLL=25.00` — HOLD.
- `ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara`.
- `BLOCKED_CITIES=London,Paris,Atlanta,Chicago,Seoul`.
- `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1`.
- Pre-Edge: **PRE_EDGE_T5_HEALTH_OK_CONTINUE** / **PRE_EDGE_T24_IDENTITY_OK_CONTINUE** — T+24: 35 filas limpias non-Seoul (source_fidelity_confirmed), 8 ciclos; Seoul 8 filas source_fidelity_suspect/excluded; pending_verification=0. **PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED** (Sesión 389).
- Seoul: hard-blocked. Reactivación requiere evidencia RKSI limpia y decisión Opus.
- Phase 2 Recalibration abierta — T+30=2026-06-09.
- Fase C: no autorizada.

---

## Hechos materializados en repo/runtime

### M1 — Seoul source fidelity: KMA → RKSI + hard-block

**Commits:** `3307b4f` (patch RKSI), `BLOCKED_CITIES` actualizado en Railway (S386).

`RESOLUTION_STATIONS["Seoul"]` apuntaba a KMA Seoul City `(37.5665, 126.9780)`. El rules text de Polymarket declara Wunderground / Incheon Intl / RKSI `(37.4602, 126.4407)`, alineado con `RESOLUTION_ICAO["Seoul"].icao == RKSI`. El mismatch databa de Sesión 185 (cambio a KMA sin validar rules text). Las 8 filas Seoul Pre-Edge de ciclos `2026-05-24T12:00/16:00/20:00` quedan `source_fidelity_suspect` y se excluyen de outcomes y contrafactuales hasta que haya evidencia limpia RKSI.

Seoul no está autorizada para trading. Una futura reactivación requiere: (1) múltiples ciclos de evidencia Pre-Edge RKSI sin `source_fidelity_suspect`, (2) decisión Opus explícita.

**Validación runtime ciclo #395 (2026-05-25T08:00Z):** Seoul `effective_mode=blocked`, `source_of_truth=BLOCKED_CITIES`, sin posiciones abiertas, sin nuevas filas Pre-Edge Seoul post-hard-block. Deployment `93d11994` SUCCESS.

### M2 — Bug NO re-eval pricing

**Commit:** `0882997`.

`recompute_position_edge()` usaba `mkt_price = 1.0 - cur_price` para posiciones NO aunque Polymarket `/positions` ya entrega el precio del token NO directamente. Rama NO ahora usa `mkt_price = cur_price`. Tests focales en `tests/test_recompute_position_edge.py`.

**Validación runtime ciclo #395:** Wellington NO cerró `LOSS_TOTAL/micro_position_unsellable` (no por SELL reason=reeval). Toronto NO cerró `RESOLVED_WIN` (no por SELL reason=reeval). Madrid NO abierto en management sin SELL. Ningún evento `SELL reason=reeval` observado post-deploy. Veredicto: **NO_PATCH_NO_REEVAL_EVENT_YET_CONTINUE_WATCH** — no hay regresión; la validación matemática del patch con un SELL reeval live queda pendiente para cuando aparezca el próximo evento elegible.

### M3 — Pre-Edge LOG_ONLY T+5 validado

**Checkpoint:** PRE_EDGE_T5_HEALTH_OK_CONTINUE (2026-05-25T08:00Z).

| Métrica | Valor |
|---------|-------|
| Filas totales en artefacto | 40 |
| Filas Seoul excluidas (`source_fidelity_suspect`) | 8 |
| Filas limpias non-Seoul | 32 |
| cycle_ids distintos limpios | 7 |
| identity_resolvable_rate (limpias) | 32/32 = 100% |
| edges sobre threshold | 21/32 |
| execution_authorized=true | 0 |
| log_only=true violaciones | 0 |
| Overhead stdout (ms) — 7 ciclos | 0.20, 0.16, 0.16, 0.26, 0.16, 0.19, 0.18 |
| p95 overhead (nearest-rank) | **0.26 ms** |
| Kill-switches activos | 0 |

Kill-switches Opus: ninguno disparado.

**Addendum T+24h (Sesión 388–389):** checkpoint superado. n_clean=35≥30, identity_resolvable_rate=100%. PRE_EDGE_T24_IDENTITY_OK_CONTINUE. Source fidelity sweep completo: PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED. Ver M7.

Próximos checkpoints: T+7d (~2026-05-31, lectura intermedia), Phase 2 T+30=2026-06-09.

### M4 — Active cities source audit

**Sesión 356.** Shanghai (ZSPD), Tokyo (RJTT), Buenos Aires (SAEZ), Ankara (LTAC): `SOURCE_MATCH_CONFIRMED` vía Gamma/WU. Ver `docs/source_audits/active_cities_source_fidelity_audit.md`.

### M5 — Istanbul WRH shadow source

**Sesiones 351-354.** WRH/weather.gov timeseries (Synoptic API) aprobado como shadow source separado para Istanbul/LTFM. No es equivalente primario a NCEI. Ver `docs/source_audits/istanbul_source_audit.md`.

### M6 — METAR Measurement Layer Wave 1+2

**Sesiones 362-366.** Wave 1 (7 ciudades: Beijing/ZBAA, Shanghai/ZSPD+ZSSS, Tokyo/RJTT+RJAA, Jeddah/OEJN, Buenos Aires/SABE+SAEZ, Ankara/LTAC, Chongqing/ZUCK) + Wave 2 (7 ciudades: Seoul/RKSI, Singapore/WSSS, Toronto/CYYZ, Wellington/NZWN, Madrid/LEMD, Milan/LIMC, Munich/EDDM). LOG_ONLY. Resolution Verification Layer separado: `tools/metar_resolution_verify.py`. Ver `docs/metar_measurement_layer.md`.

### M7 — Pre-Edge Source Fidelity Sweep post-T+24

**Checkpoint:** PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED (Sesión 389, 2026-05-25).

Auditoría read-only Codex por ciudad de las 35 filas non-Seoul de la cohorte T+24. Fuente de reglas consultada: Polymarket market rules text vía Gamma.

| Ciudad | Filas Pre-Edge | ICAO repo | Fuente Polymarket rules | Resultado |
|--------|---------------|-----------|------------------------|-----------|
| Singapore | 12 | WSSS | WU sg/singapore/WSSS / Singapore Changi Airport / whole °C | SOURCE_MATCH_CONFIRMED |
| Wellington | 12 | NZWN | WU nz/wellington/NZWN / Wellington Intl Airport / whole °C | SOURCE_MATCH_CONFIRMED |
| Tokyo | 4 | RJTT | Sin drift vs audit durable S356 | NO_DRIFT_CONFIRMED |
| Munich | 3 | EDDM | WU de/munich/EDDM / Munich Airport / whole °C | SOURCE_MATCH_CONFIRMED |
| Toronto | 2 | CYYZ | WU ca/mississauga/CYYZ / Toronto Pearson Intl Airport / whole °C | SOURCE_MATCH_CONFIRMED |
| Shanghai | 2 | ZSPD | Sin drift vs audit durable S356 | NO_DRIFT_CONFIRMED |
| Madrid | — | LEMD | WU es/madrid/LEMD / Madrid-Barajas Airport / whole °C; BUY real canary autorizado, sin contradicción de policy | SOURCE_MATCH_CONFIRMED |

**Estado final de la cohorte T+24:**

| Categoría | Filas |
|-----------|-------|
| source_fidelity_confirmed (non-Seoul) | 35 |
| source_fidelity_suspect (Seoul, excluidas) | 8 |
| pending_verification | 0 |

**Implicaciones para Outcome Resolver:**
- Las 35 filas non-Seoul permanecen válidas técnicamente y quedan confirmadas en source fidelity.
- El Outcome Resolver debe excluir las 8 filas Seoul suspect; no necesita excluir P1/P2 por identidad de estación.
- El gate del Outcome Resolver ya no depende de nueva auditoría station mapping para P1/P2; sigue dependiendo de T+7d (~2026-05-31) y diseño aprobado por Opus.
- No hay riesgo source-fidelity inmediato en ciudades executable/canary auditadas.
- No se requiere acción runtime ni Opus ahora.

---

## Líneas de investigación

### Línea A — Source fidelity y station mapping

**Qué:** La temperatura que Polymarket usa para resolver un mercado proviene de WU, que a su vez se nutre casi exclusivamente de METAR de la estación ICAO exacta del aeropuerto. El mapping de estación es la variable más crítica: un mismatch puede invertir el edge completamente.

**Estado actual:** active cities = `SOURCE_MATCH_CONFIRMED` (M4). Seoul = hard-blocked tras patch RKSI (M1).

**Pendiente — estaciones para ciudades bloqueadas con eventual unblock:**

El archivo de fuentes externas incluye un listado de estaciones atribuido a AlterEgo (X, mayo 2026) con correcciones notables: London → EGLC (City Airport, no EGLL Heathrow), Paris → LFPB (Le Bourget, no LFPG CDG), Denver → KBKF (no KDEN), HK → HK Observatory (no VHHH). Estos claims están clasificados como `EXTERNAL_CLAIM_PROVIDED` — no verificados contra Gamma/WU todavía. Se deben verificar individualmente contra rules text de al menos 1 mercado resuelto por ciudad antes de cualquier patch.

**Agente:** Codex (lectura Gamma + AST bot.py) por ciudad; Opus si implica cambio en `RESOLUTION_STATIONS` o promoción.

**Gate:** Solo cuando una ciudad entre en pipeline de unblock; no abrir antes.

---

### Línea B — Wethr.net como benchmark externo

**Qué:** Wethr.net fue mencionado en el archivo de fuentes externas como herramienta con "all info and models in one place", útil especialmente para mercados US. Potencial candidato a benchmark externo sin necesidad de scraping directo de WU.

**Clasificación del claim:** `EXTERNAL_CLAIM_PROVIDED` — no verificado funcionalmente.

**Nunca:** canonical_source, ni influencia en BUY/SELL/SKIP, ni reemplazo de Open-Meteo en runtime.

**Verificaciones mínimas antes de integrar:**
1. Confirmar que Wethr.net muestra temperatura WU por ICAO (no city-center ni modelo propio).
2. Comparar manualmente vs Open-Meteo para ≥3 mercados resueltos en ciudades activas.
3. Si alinea con Gamma-derived outcomes: candidato a shadow source de observabilidad.

**Agente:** Sonnet (investigación read-only) → Opus si resultado justifica integración.

**Gate:** Después de Phase 2 T+30 (2026-06-09) y solo si throughput lo justifica.

---

### Línea C — METAR, SPECI, ASOS, TAF y variables auxiliares

**Dos capas distintas:**

#### C1 — Settlement-compatible (METAR / SPECI)

El METAR report refleja la temperatura en el momento exacto de la observación; WU registra el daily max como el máximo de todas las lecturas METAR del día. Esto implica que el objetivo del bot no es predecir el "daily high absoluto" sino el máximo de las lecturas METAR. SPECI aparece cuando hay cambio significativo fuera del ciclo horario.

METAR Layer ya implementado (M6). Pendiente: completar parity METAR-WU con dataset WU real (n≥20 días por ciudad Wave 1) para promover el layer de observacional a fuente de audit.

**Variables auxiliares de METAR para anticipación (no settlement, predictive-only):**

El archivo de fuentes externas describe estas variables (atribuidas a js_dun, X, mayo 2026) — clasificación: `EXTERNAL_CLAIM_PROVIDED`:
- **Dew point:** cuanto más cercano a la temperatura, más humedad → riesgo de niebla → frena calentamiento.
- **Cloud cover:** BKN/OVC = menor calentamiento; CAVOK/SKC/FEW/SCT = calentamiento probable.
- **Wind:** sea breeze tapa el calentamiento en estaciones costeras; land wind = escenario más cálido.
- **Precipitation:** lluvia/tormenta detiene el crecimiento de temperatura.

Estas variables son Tier 2 respecto a la parity METAR-WU. No implementar como señal trading hasta tener parity confirmada (Línea C1) y diseño aprobado por Opus.

#### C2 — ASOS 5-minute (predictivo intra-hora, no settlement)

El archivo de fuentes externas describe ASOS como el sistema que alimenta los reportes METAR. Para mercados US (excepto Denver), habría disponibilidad de datos cada 5 minutos. **Claim clave (atribuido a js_dun):** WU NO usa los datos de 5 minutos — usa solo el METAR oficial. Un pico de temperatura entre METARs que cae antes del siguiente reporte no queda registrado en WU. ASOS 5-min es por tanto una herramienta de anticipación intra-hora del próximo METAR, no de tracking de settlement.

**Clasificación:** `EXTERNAL_CLAIM_PROVIDED`. No aplicable hasta que haya ciudades US en el universo activo.

#### C3 — TAF

El archivo de fuentes externas describe TAF como el forecast de aviación del aeropuerto (6-36h). Variables: viento esperado, cobertura de nubes, precipitación, temperatura estimada (orientativa). Útil para confirmar/refutar el regime atmosférico esperado antes de entrar a un mercado.

**Clasificación:** `EXTERNAL_CLAIM_PROVIDED`. Valor cualitativo. No implementar como señal trading hasta tener parity METAR-WU y diseño Opus.

---

### Línea D — Modelos numéricos, ensembles y calibración

#### D1 — Jerarquía de modelos por región

El archivo de fuentes externas incluye un listado de modelos atribuido a AlterEgo (X, mayo 2026) — clasificación: `EXTERNAL_CLAIM_PROVIDED`:

| Región | Modelos recomendados |
|--------|---------------------|
| Global (anchor) | ECMWF IFS (5-10d), ECMWF AIFS, GFS, ICON-Global |
| USA + Canada | HRRR (1h update, 3km), GEM, GFS |
| Europa | ICON-EU (más fuerte regional), AROME (W. Europa), UKMO (London+N. Europa) |
| C. Europa (binario) | **ICON-D2 EPS** (distribución, no forecast puntual) |
| Asia E. / Pacífico | JMA-GSM, JMA-MSM (Japón), ECMWF+ICON-Global |
| Medio Oriente / África | ECMWF dominant, GFS backup |

**Idea estratégica notable:** para mercados binary threshold (exact), un ensemble (distribución de probabilidad) es más informativo que un forecast determinístico. ICON-D2 EPS para ciudades europeas centrales es el ejemplo concreto.

**Workflow recomendado (externo):** ECMWF como anchor + modelo regional + ensemble donde disponible.

Nuestro bot actualmente usa Open-Meteo con modelo IFS (ECMWF) sin `bias_correction=true`. El parámetro `bias_correction=true` está disponible en la API de Open-Meteo — no lo estamos usando. Sin verificar si mejora accuracy para nuestras ciudades específicas.

**Gate:** n≥30 observaciones limpias por ciudad (Truth Pipeline) para comparar con outcomes reales antes de cambiar modelo o activar bias_correction. No cambiar antes de ese benchmark.

**Agente:** Sonnet (investigación Open-Meteo API docs + disponibilidad de modelos por ciudad) → Opus para decisión de cambio.

#### D2 — Calibración por ciudad y horizonte

El archivo de fuentes externas incluye código del weatherbot alteregoeth-ai/weatherbot que implementa calibración por ciudad y fuente: acumula MAE por mercado resuelto, lo convierte en sigma, usa distribución normal para P(temperatura en bucket). Clasificación del código: `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK`.

**Red flags observados en el código del archivo externo:**
- Usa Visual Crossing para obtener la temperatura actual post-resolución (calibración). No WU, no Gamma-derived. Esto significa su calibración está optimizada contra una fuente diferente del settlement real.
- Etiqueta la función de US como "HRRR" pero el código usa `models=gfs_seamless` (GFS Seamless, no HRRR puro).
- Paris en el código = LFPG, aunque el mismo autor corrigió en X que debería ser LFPB.

El concepto de calibración MAE ciudad+horizonte es correcto; la implementación de referencia tiene source mismatch. Nuestra calibración debe usar outcomes derivados de Gamma/WU (Truth Pipeline), no Visual Crossing.

**Gate:** Truth Pipeline canonizada + n≥30 resolved por ciudad.

---

### Línea E — Repositorios externos como references

El archivo de fuentes externas lista 10 repos de GitHub atribuidos a AlterEgo (X, mayo 2026). Clasificación: `EXTERNAL_CLAIM_PROVIDED` para el listado; `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` para el código alteregoeth incluido en el archivo.

**Repositorios con patterns arquitecturales aprovechables (sin validar):**

| Repo | Pattern de referencia | Red flag conocido |
|------|----------------------|------------------|
| alteregoeth-ai/weatherbot | ECMWF+METAR+calibración MAE; snapshot history por mercado; loop de calibración | Visual Crossing para temp actual (no WU); `gfs_seamless` etiquetado como HRRR; LFPG para Paris |
| yangyuan-zhen/PolyWeather | DEB (Dynamic Error Balancing): pesos por modelo según accuracy reciente; 52 ciudades | Source fidelity no documentada |
| suislanchez/polymarket-kalshi-weather-bot | GFS 31-member ensemble → probabilidad de acuerdo; edge>8% threshold | GFS ensemble inferior a ECMWF para EU/Asia |

No abrir auditoría técnica de repos como tarea aislada. Solo si surge necesidad concreta de adoptar un patrón específico.

---

### Línea F — ColdMath / Traders Intelligence

**Hechos observables del archivo externo** (atribuidos a AlterEgo analizando >1,200 trades vía Parity, mayo 2026) — clasificación: `EXTERNAL_CLAIM_PROVIDED`:
1. Opera mercados exact con bins de 1°C (Singapore 34°C, Kuala Lumpur 29°C, Houston 70-71°F).
2. Scaling: 8-10 compras separadas misma posición (7, 10, 16, 46, 115, 290 shares). Minimiza slippage, promedia precio de entrada.
3. Alto volumen de trades — indicador de bot automatizado.
4. Construye posiciones masivas en outcomes a 1¢.
5. WR observado: ~63-65%.

**Inferencias no verificadas** — clasificación: `HYPOTHESIS_ONLY`:
- Multi-model blend.
- Bias correction ciudad+horizonte.
- Dynamic weights por performance reciente.
- Énfasis en datos real-time METAR.

**Implicación para Traders Intelligence:** ColdMath opera mercados exact con narrow bins que actualmente el bot bloquea por ausencia de quality-trader signal match. Si ColdMath aparece en `directional_trader_census.py` con criterios de directionality suficientes → candidato a QT whitelist → Opus. El Pre-Edge LOG_ONLY ya captura evaluaciones de esas señales.

**Gate:** verificar ColdMath en census + Opus antes de cualquier cambio en whitelist o gate exact. No traducir su patrón de micro-scaling a sizing/trading sin BANKROLL policy aprobada.

---

### Línea G — Liquidez e information asymmetry

El archivo de fuentes externas incluye un hilo de Maskache (X, 19 mayo 2026) sobre asimetría de información en mercados weather y caída reciente de liquidez. Clasificación: `EXTERNAL_CLAIM_PROVIDED`.

**Implicación contextual:** el mercado tiene asimetría estructural entre traders con datos precisos (estación ICAO correcta + METAR + modelo adecuado) y traders sin esa información. El bot está posicionado del lado correcto en station mapping; la calidad del forecast es la variable diferenciante.

**Liquidez:** la caída de liquidez mencionada amplía spreads y aumenta slippage. El bot no tiene métrica propia de slippage todavía.

**Clasificación backlog:** `WATCH_ONLY`. No accionable con datos propios actuales.

---

## Claim Register

| Claim | Fuente | Estado | Utilidad | Gate antes de actuar |
|-------|--------|--------|----------|----------------------|
| Seoul → RKSI | Nuestro audit + AlterEgo (confirma) | `VERIFIED_IN_REPO` | — | — |
| Shanghai/Tokyo/BsAs/Ankara SOURCE_MATCH_CONFIRMED | S356 Gamma audit | `VERIFIED_IN_REPO` | — | — |
| Istanbul → LTFM (WRH shadow source) | S351-S354 audit | `VERIFIED_IN_REPO` | — | — |
| METAR Wave 1+2 operativo | Sesiones 362-366 | `VERIFIED_IN_REPO` | — | — |
| Pre-Edge T+5 HEALTH_OK, p95=0.26ms | Ciclo #395 leído en Railway | `VERIFIED_IN_REPO` | — | — |
| Pre-Edge T+24h identity_rate=100% n=35, PRE_EDGE_T24_IDENTITY_OK_CONTINUE | S388 Railway read-only | `VERIFIED_IN_REPO` | — | — |
| Singapore/WSSS SOURCE_MATCH_CONFIRMED (Pre-Edge T+24) | S389 Codex audit Polymarket rules | `VERIFIED_IN_REPO` | — | — |
| Wellington/NZWN SOURCE_MATCH_CONFIRMED (Pre-Edge T+24) | S389 Codex audit Polymarket rules | `VERIFIED_IN_REPO` | — | — |
| Munich/EDDM SOURCE_MATCH_CONFIRMED (Pre-Edge T+24) | S389 Codex audit Polymarket rules | `VERIFIED_IN_REPO` | — | — |
| Toronto/CYYZ SOURCE_MATCH_CONFIRMED (Pre-Edge T+24) | S389 Codex audit Polymarket rules | `VERIFIED_IN_REPO` | — | — |
| Madrid/LEMD SOURCE_MATCH_CONFIRMED; BUY canary autorizado, sin contradicción policy | S389 Codex audit Polymarket rules | `VERIFIED_IN_REPO` | — | — |
| Shanghai/ZSPD, Tokyo/RJTT sin drift vs S356 (cohorte T+24) | S389 Codex read-only | `VERIFIED_IN_REPO` | — | — |
| PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED: 35 non-Seoul confirmed, 8 Seoul suspect/excluded, pending_verification=0 | S389 | `VERIFIED_IN_REPO` | — | — |
| Wellington NO → LOSS_TOTAL (no reeval), Toronto NO → RESOLVED_WIN (no reeval) | Ciclo #395 | `VERIFIED_IN_REPO` | Sin regresión observada | Próximo SELL NO reeval |
| WU resuelve de METAR de la estación ICAO exacta | Archivo externo (Maskache + js_dun) | `EXTERNAL_CLAIM_PROVIDED` | Alta — confirma source fidelity thesis | Verificar 1 mercado resuelto propio contra METAR |
| Objetivo: predecir temp en momento del METAR, no daily max absoluto | Archivo externo (Maskache) | `EXTERNAL_CLAIM_PROVIDED` | Alta — matiza interpretación de outcome | Verificar contra Gamma-derived outcome |
| London → EGLC (City Airport, no EGLL Heathrow) | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Alta para futura unblock London | Verificar Gamma rules text ≥1 mercado London |
| Paris → LFPB (Le Bourget, no LFPG CDG) | Archivo externo (AlterEgo tweet) | `EXTERNAL_CLAIM_PROVIDED` | Alta para futura unblock Paris | Verificar Gamma rules text ≥1 mercado Paris |
| Denver → KBKF (no KDEN) | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Media (ciudad fuera del universo) | Verificar Gamma si Denver se añade |
| HK → HK Observatory (no VHHH) | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Media (ciudad fuera del universo) | HK Observatory no es ICAO estándar — audit específico |
| ASOS 5-min: WU NO usa 5-min, solo METAR oficial | Archivo externo (js_dun) | `EXTERNAL_CLAIM_PROVIDED` | Alta — ASOS es predictivo intra-hora, no settlement | — |
| ASOS 5-min disponible para US (excepto Denver) | Archivo externo (js_dun) | `EXTERNAL_CLAIM_PROVIDED` | Media — solo si bot opera US | Verificar disponibilidad KBKF |
| Wethr.net: all info and models, útil para US | Archivo externo (Maskache) | `EXTERNAL_CLAIM_PROVIDED` | Media — benchmark potencial | Verificación manual ≥3 mercados activos |
| ECMWF gold standard global; HRRR para US corto plazo; ICON-EU Europa | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Alta contextual | Benchmark n≥30 outcomes por ciudad vs modelo actual |
| ICON-D2 EPS: distribución probabilística para binarios | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Alta estratégica | n≥30 outcomes ciudades EU + ciudades EU en universo |
| Open-Meteo soporta `bias_correction=true` para ECMWF | Archivo externo (alteregoeth código) | `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` | Media — potencial mejora gratuita | Verificar API docs Open-Meteo + benchmark n≥30 |
| alteregoeth weatherbot usa Visual Crossing para temp actual (no WU) | Archivo externo (alteregoeth código) | `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` | Alta — red flag source mismatch | No usar su calibración como referencia directa |
| alteregoeth weatherbot usa `gfs_seamless`, no HRRR puro | Archivo externo (alteregoeth código) | `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` | Media — nomenclatura imprecisa en repo externo | — |
| alteregoeth weatherbot código tiene Paris = LFPG (no LFPB) | Archivo externo (alteregoeth código) | `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` | Media — inconsistente con tweet del propio autor | Verificar Gamma |
| ColdMath: narrow 1°C bins, scaling, ~63-65% WR (observable en Parity) | Archivo externo (AlterEgo, >1200 trades) | `EXTERNAL_CLAIM_PROVIDED` | Alta — patrón de referencia para gate exact | — |
| ColdMath: multi-model blend, bias correction, dynamic weights | Archivo externo (AlterEgo, inferencia) | `HYPOTHESIS_ONLY` | Media — no confirmado | n/a — no actuar |
| ColdMath posible en QT census | Este análisis | `HYPOTHESIS_ONLY` | Alta diferida | Verificar en `directional_trader_census.py` + Opus |
| Micro-scaling (múltiples compras misma posición) | Archivo externo (AlterEgo) | `EXTERNAL_CLAIM_PROVIDED` | Alta diferida | Opus + BANKROLL policy antes de adoptar |
| Información asimétrica como driver de spreads/liquidez | Archivo externo (Maskache) | `EXTERNAL_CLAIM_PROVIDED` | Baja accionable actualmente | Métrica de slippage propia |

---

## Backlog priorizado

| Candidato | Estado | ROI | Riesgo | Gate exacto | Criterio de parada |
|-----------|--------|-----|--------|-------------|-------------------|
| M1-M6 (source audits, METAR, Pre-Edge) | `DONE / ALREADY_MATERIALIZED` | — | — | — | — |
| Próximo SELL NO reeval — validación matemática del patch | `ACTION_AFTER_RUNTIME_VALIDATION` | Medio — confirma patch completo | Bajo | Primer SELL reason=reeval post-deploy | Verificar `mkt_price=cur_price` applied correctly |
| Pre-Edge T+24h identity_rate n≥30 + source fidelity sweep | `DONE — PRE_EDGE_T24_IDENTITY_OK_CONTINUE + PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED` | Alto — gate kill-switch Phase 2 | Bajo | Completado S388+S389 | identity_resolvable_rate=100% n=35; source_fidelity_confirmed=35; pending_verification=0 |
| Pre-Edge T+7d lectura intermedia (~2026-05-31) | `ACTION_AFTER_RUNTIME_VALIDATION` | Alto diferido | Bajo | Sonnet read-only, 2026-05-31 | Separar Seoul suspect; input Outcome Resolver |
| Outcome Resolver v1 design | `CANDIDATE_LOG_ONLY_AFTER_PRE_EDGE_GATE` | Alto — cierra loop Pre-Edge → P&L contrafactual | Bajo | T+7d completado (~2026-05-31); source fidelity ya confirmada (S389, no bloqueante para P1/P2) | Sonnet doc → Codex impl → Opus gate exact-no-QT |
| Seoul evidencia RKSI limpia → Opus | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Alto — reabre ciudad | Bajo (patch aplicado) | Múltiples ciclos Pre-Edge limpios RKSI post-patch | Opus: `REACTIVATION_AUTHORIZED` o `KEEP_BLOCKED` |
| Verificación London EGLC vs RESOLUTION_ICAO | `CANDIDATE_LOG_ONLY_AFTER_PRE_EDGE_GATE` | Medio — gate para unblock London | Bajo | Solo cuando London entre en pipeline de unblock | Gamma rules text 1 mercado resuelto |
| Verificación Paris LFPB vs RESOLUTION_ICAO | `CANDIDATE_LOG_ONLY_AFTER_PRE_EDGE_GATE` | Medio — gate para unblock Paris | Bajo | Solo cuando Paris entre en pipeline de unblock | Igual que London |
| METAR parity METAR vs WU dataset real (Wave 1) | `CANDIDATE_LOG_ONLY_AFTER_PRE_EDGE_GATE` | Medio — desbloquea Beijing candidato | Bajo | n≥20 días METAR + WU CSV o Gamma-derivado suficiente | |delta|_mediana >1°C: `METAR_PARITY_FAIL` |
| Open-Meteo bias_correction=true benchmark | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Medio — mejora gratuita potencial | Bajo | n≥30 outcomes limpios por ciudad vs sin bias_correction | Opus aprueba si mejora MAE en >0.5°C |
| ColdMath en Traders Intelligence census | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Alto diferido | Medio | ColdMath en census + directionality suficiente | Opus gate antes de whitelist |
| ICON-D2 EPS para ciudades EU (distribución probabilística) | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Alto estratégico | Medio | n≥30 outcomes ciudades EU; ciudades EU en universo activo | Opus aprueba si mejora WR vs ECMWF determinístico |
| Bias correction ciudad+horizonte (Truth Pipeline) | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Alto diferido | Medio | n≥30 observaciones limpias `observed_vs_forecast` + Truth Pipeline canonical | Opus aprueba; bias inestable → DISCARD |
| Wethr.net como benchmark | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Medio incierto | Bajo | Verificación manual ≥3 mercados activos | Wethr = WU en n≥3: `WETHR_PARITY_CONFIRMED`; si no: DISCARD |
| Istanbul WRH parity n≥20 | `CANDIDATE_LOG_ONLY_AFTER_PRE_EDGE_GATE` | Medio | Bajo | n≥20 mercados Istanbul resueltos con WRH observado | |delta|_mediana >0.5°C: no promover |
| ASOS 5-minute (US cities) | `WATCH_ONLY` | Bajo (sin US en universo) | Bajo | US cities en ACTIVE_TRADING_CITIES | DISCARD si no |
| TAF como señal auxiliar | `WATCH_ONLY` | Bajo directo | Bajo | Completar parity METAR-WU primero | DISCARD si no mejora WR en backtesting |
| Estaciones Denver/NYC/HK/Taipei | `WATCH_ONLY` | Bajo (fuera de universo) | Bajo | Solo si esas ciudades entran en pipeline | Gamma audit individual |
| Repos externos (9 de los 10 listados) | `WATCH_ONLY` | Bajo directo | Bajo | Necesidad concreta de un patrón específico | DISCARD si no surge necesidad |
| ColdMath micro-scaling (sizing policy) | `CANDIDATE_OPUS_STRATEGY_REVIEW` | Alto diferido | Alto | Opus + Pablo sign-off + BANKROLL >$100 | Fuera de scope actual |
| Liquidez / slippage monitoring | `WATCH_ONLY` | Bajo | Bajo | Métrica propia de slippage | DISCARD si datos insuficientes |

---

## Orden de ejecución recomendado

1. ~~**Pre-Edge T+24h identity_rate**~~ **DONE** — PRE_EDGE_T24_IDENTITY_OK_CONTINUE (S388) + PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED (S389): identity_rate=100% n=35; source_fidelity_confirmed=35; pending_verification=0.
2. **Próximo SELL NO reeval** (cuando ocurra): verificar que `mkt_price=cur_price` se aplicó correctamente — `NO_PATCH_NO_REEVAL_EVENT_YET_CONTINUE_WATCH` mientras no ocurra.
3. **Pre-Edge T+7d lectura (~2026-05-31)** (Sonnet, read-only): artefacto completo, separar Seoul suspect, input para Outcome Resolver.
4. **Outcome Resolver v1 design** (Sonnet, docs-only): schema join Pre-Edge ↔ blocked_signals_resolutions. Gate: completar Paso 3.
5. **Outcome Resolver v1 implementation** (Codex, NORMAL): según diseño Paso 4.
6. **Seoul evidencia RKSI limpia** (Codex read-only → Opus): múltiples ciclos Pre-Edge limpios RKSI. Opus decide reactivación.
7. **METAR parity vs WU** (Codex, NORMAL): Wave 1 con WU CSV si disponible. Si Beijing parity pass → candidato a unblock.
8. **Phase 2 T+30 (2026-06-09)** (Sonnet/Opus): cierre mixed-condition experiment. Input del Outcome Resolver para slice exact-no-QT. Decisión Opus sobre gate exact-no-QT.
9. **Wethr.net / modelos regionales / ColdMath** (diferido): solo si Paso 8 concluye con datos limpios y WR Phase 2 ≥45%.

---

## Guardrails

- El archivo de fuentes externas (`docs/research_inputs/external_weather_claims_2026-05-24.md`) es `EXTERNAL_SOURCE_ARCHIVE`. No es fuente de verdad. No autoriza cambios en BUY/SELL/SKIP, BANKROLL, sizing, city modes, thresholds, whitelist, guards, scheduler o Fase C.
- Los claims `EXTERNAL_CLAIM_PROVIDED` requieren verificación independiente (Gamma/WU/repo propio) antes de cualquier acción.
- Los claims `EXTERNAL_CODE_EXCERPT_PROVIDED_NEEDS_DIRECT_RECHECK` requieren lectura directa del repo referenciado antes de adoptar cualquier patrón.
- Los claims `HYPOTHESIS_ONLY` no generan ninguna acción sin evidencia propia.
- Station mapping de ciudades bloqueadas (London EGLC, Paris LFPB): verificar contra Gamma antes de cualquier patch, no asumir el listado externo como canónico.
- Seoul: bloqueada. No reactivar sin evidencia RKSI limpia + Opus.
- Fase C: no autorizada.
- BANKROLL: HOLD $25.
