# Market Evidence Ledger — Contract v1

**Fecha:** 2026-05-23 (Sesión 381, Sonnet, docs-only)
**Clasificación:** `MONETIZATION_RELEVANT / ARCHITECTURE`
**Decisión Opus:** `DEFINE_MARKET_LEDGER_CONTRACT_BEFORE_ANY_REPORT`
**Veredicto de cierre:** `LEDGER_CONTRACT_READY_FOR_REVIEW`

---

## 1. Propósito y límites

### 1.1 Qué es el Ledger

El Market Evidence Ledger **no es una base de datos nueva**. Es un contrato común de identidad, provenance y clasificación que define cómo los artefactos runtime existentes pueden ser relacionados, consultados y acumulados en aprendizaje trazable.

Es una **vista derivable** sobre artefactos ya existentes — no un artefacto nuevo que deba mantenerse en el hot path del bot.

### 1.2 Qué NO es el Ledger

| No es | Razón |
|---|---|
| Una base de datos nueva | No hay schema de DB que implementar en Fase 1 |
| Un replicado de P&L o trade lifecycle | Esos artefactos son canónicos en sus propios esquemas |
| Un writer desde el hot path del bot | No se escribe desde el ciclo de trading |
| Una fuente de decisiones ejecutables | No autoriza BUY/SELL/SKIP, cambio de policy ni BANKROLL |
| Un replicado de logs raw | Opera sobre vistas derivadas y summaries, no sobre streams brutos |
| Un sustituto del Daily Digest / Telegram | Telegram y Digest son superficies de presentación, no fuente de verdad |

### 1.3 Principio de Pablo

En Polymarket, seleccionar qué mercados estudiar ya forma parte del edge. El sistema debe aprender de cada ciclo, descarte, shadow edge, señal externa, outcome y resultado real. Pero el aprendizaje debe ser **trazable y auditable**: ninguna conclusión `LOG_ONLY` autoriza automáticamente trading, cambios de ciudades, condiciones, thresholds, BANKROLL o guards.

### 1.4 Alcance de Fase 1

**Fase 1 — este documento:** contrato documental. Identidad, provenance, stages, joins, manifest y review queue. Sin código ni nuevos writers.

**Fase 2 — posterior, no implementar ahora:** `Trader vs Bot Gap Report v1` como primer consumer conforme al contrato. LOG_ONLY.

**Fase 3 — condicional, no autorizar ahora:** captura mínima de identidad para descartes `city_window` y `price`. Join de `skip_log` con outcomes. Solo si Fase 2 demuestra señal monetizable real.

---

## 2. Jerarquía de identidad

### 2.1 Niveles de identidad

No se usa un hash semántico como única identidad canónica. La jerarquía es:

#### Identidad primaria (cuando existe en el artefacto)

| Campo | Formato | Descripción |
|---|---|---|
| `condition_id` | Polymarket UUID | Identidad canónica de condición en Polymarket |
| `market_id` | Polymarket UUID | Identidad canónica de mercado en Polymarket |
| `token_id` | hex string | Identidad de posición/token en Polymarket |

Disponibles en: `blocked_signals_resolutions.jsonl` (v2), `trade_lifecycle.json`, `skip_log.jsonl` (token_id), `polymarket.db` (market_snapshots).

**Cuando existe identidad primaria, es la fuente de join canónica. No reemplazar por identidad semántica.**

#### Identidad de join operativo (clave de unión entre artefactos del bot)

| Campo | Formato | Presente en |
|---|---|---|
| `eval_key` | `city\|date_iso\|condition\|threshold[-threshold_high]\|unit` | `bot_signal_evaluations.jsonl` |
| `match_key` | mismo formato que `eval_key` | `blocked_signals_resolutions.jsonl`, `signals_crosscheck.jsonl` |
| `canonical_signal_id` | hash(`match_key` + ciclo) | `blocked_signals_resolutions.jsonl` v2 |

`eval_key` y `match_key` son equivalentes funcionales. El join `eval_key ↔ match_key` es el único join activo documentado y contractado en `docs/instrumentation/bot_evaluation_capture.md`.

#### Identidad semántica fallback (cuando no hay identidad primaria ni join key)

```
semantic_market_key = hash(city, date_iso, condition, threshold_low, threshold_high, unit, side cuando exista)
```

**Uso:** solo para artefactos que no tienen `eval_key`/`match_key` ni identidad Polymarket (ej. `funnel_observability_log_only.jsonl` a nivel ciclo, `skip_log.jsonl` cuando no hay `token_id`).

### 2.2 Reglas de equivalencia entre observaciones

| Condición | Interpretación |
|---|---|
| Mismo `condition_id` | **Mismo mercado** — join canónico |
| Mismo `eval_key` / `match_key` | **Mismo ciclo de señal** — join operativo confirmado |
| Mismo `semantic_market_key` | **Posiblemente equivalentes** — requiere confirmación con precio/timestamp |
| Mismos `city` + `date_iso` + `condition` + `threshold` sin hash | **Candidatos a equivalencia** — pueden ser mercados distintos en mismo día |
| Solo `city` + `date_iso` | **Contexto compartido** — no suficiente para join de mercado |

**Regla dura:** dos observaciones no pueden considerarse el mismo mercado únicamente por `city` + `date_iso`. Requieren al menos `condition` + `threshold` para candidatura, o identidad primaria para confirmación.

---

## 3. Provenance y nivel de evidencia

### 3.1 Tipos de observación

Cada observación en el ledger debe clasificarse en uno de estos tipos:

| Tipo | Descripción | Ejemplos |
|---|---|---|
| `OBSERVED_RUNTIME` | Dato capturado automáticamente por el bot en Railway | `bot_signal_evaluations`, `blocked_signals_resolutions`, `trade_lifecycle` |
| `DERIVED_JOIN` | Conclusión derivada de unir dos o más artefactos | Gap report output, counterfactual estimate |
| `COUNTERFACTUAL_ESTIMATE` | Estimación de qué habría pasado bajo política alternativa | `bot_would_have_bought=true` si hubiera estado en modo activo |
| `EXTERNAL_SIGNAL` | Señal de origen externo al bot | `traders_intelligence`, METAR measurement |
| `HUMAN_DECISION` | Decisión documentada por Pablo u Opus | Veredictos de sesión, Audit confirmations |
| `DATA_QUALITY_WARNING` | Observación con limitación conocida que afecta confiabilidad | nulos de Fase C, gap fechas METAR, `bot_evaluation=null` |

### 3.2 Campos mínimos de provenance

Toda observación o conclusión que entre al ledger debe poder expresar:

| Campo | Tipo | Descripción |
|---|---|---|
| `source_artifact` | string | Archivo fuente (ej. `data/bot_signal_evaluations.jsonl`) |
| `source_environment` | enum | `railway_live` / `repo_doc` / `external_observability` / `derived` |
| `source_timestamp` | ISO datetime | Timestamp de la observación en el artefacto fuente |
| `generated_at` | ISO datetime | Cuándo se produjo este registro del ledger (puede diferir de source) |
| `freshness_status` | enum | `FRESH` / `STALE` / `UNKNOWN` |
| `join_confidence` | enum | `HIGH` (identidad primaria) / `MEDIUM` (eval_key/match_key) / `LOW` (semantic fallback) / `NONE` (sin join) |
| `data_quality_flags` | list[string] | Lista de flags conocidos (ej. `bot_evaluation_null`, `phase_c_fields_missing`, `metar_date_gap`) |

### 3.3 Jerarquía de confianza de fuentes

```
railway_live (OBSERVED_RUNTIME, HIGH)
    > repo_doc (HUMAN_DECISION, MEDIUM — depende de frescura del doc)
    > external_observability (EXTERNAL_SIGNAL, MEDIUM — depende de staleness)
    > derived (DERIVED_JOIN / COUNTERFACTUAL_ESTIMATE, LOW–MEDIUM — depende de join_confidence)
```

---

## 4. Stage enum — ciclo de vida de un mercado

### 4.1 Definición de stages

| Stage | Descripción |
|---|---|
| `DISCOVERED` | Mercado visto por el bot en señales Polymarket (puede ser contador sin identidad) |
| `PREFILTERED` | Pasó filtro de ciudad activa/canary; no salió por `city_window` ni fecha |
| `SKIPPED_CITY_WINDOW` | Ciudad disponible pero descartado por ventana horaria de ciudad |
| `SKIPPED_PRICE` | Descartado porque el precio estaba fuera de rango (OOR) |
| `SKIPPED_DATE` | Descartado porque `days_ahead` fuera de ventana |
| `SKIPPED_CONDITION` | Descartado por `condition_filtered` (condición no soportada por el bot) |
| `BLOCKED_POLICY_SOURCE` | Bloqueado por política de bot (ciudad blocked, source bloqueado, guard activo) |
| `EVALUATED_NO_EDGE` | Evaluado por el bot; `would_buy=false` o `bot_edge_pct < threshold` |
| `EVALUATED_EDGE` | Evaluado con edge suficiente; eligible para `SELECTED` |
| `SHADOW_EDGE` | Edge detectado en ciudad shadow (no se tradea, acumula evidencia) |
| `SELECTED` | Mercado seleccionado para BUY en ciclo |
| `BUY` | Posición abierta (trade real en Polymarket) |
| `RESOLVED` | Mercado resuelto; outcome conocido |

### 4.2 Tabla de mapping: artefacto → stage derivable

| Artefacto | Campos disponibles | Stage(s) derivable(s) | Campos ausentes críticos | Confianza de stage |
|---|---|---|---|---|
| `funnel_observability_log_only.jsonl` | `discovered`, `prefiltered`, `city_window_skipped`, `price_out_of_range`, `date_out_of_range`, `condition_filtered`, `policy_source_blocked`, `edge`, `shadow_edge`, `selected`, `real_buy` (como contadores) | `DISCOVERED` → `RESOLVED` (contadores agregados, no por mercado) | `condition_id`, `market_id` por mercado individual | BAJA — no hay identidad por mercado descartado |
| `bot_signal_evaluations.jsonl` | `eval_key`, `city`, `date_iso`, `condition`, `threshold`, `unit`, `would_buy`, `bot_edge_pct_at_signal`, `skip_or_block_reason`, `decision_gate`, `our_prob`, `mkt_prob`, `days_ahead` | `EVALUATED_NO_EDGE`, `EVALUATED_EDGE`, `BLOCKED_POLICY_SOURCE` | `condition_id`, `market_id` en mayoría de filas | MEDIA — join via eval_key disponible |
| `blocked_signals_resolutions.jsonl` (v2) | `canonical_signal_id`, `market_id`, `condition_id`, `match_key`, `reason_blocked`, `win_for_trader`, `resolution_source`, `price_bucket`, `city_mode_at_record_time` | `BLOCKED_POLICY_SOURCE`, `RESOLVED` (cuando `win_for_trader` conocido) | `bot_would_have_bought`, `settlement_source`, `settlement_fidelity_status` (Fase C nulos) | ALTA para stage `BLOCKED`; MEDIA para `RESOLVED` (depende de Fase C) |
| `signals_crosscheck.jsonl` | `eval_key` equivalente, `crosscheck_type` (`MATCH`/`BOT_ONLY`/`TRADER_ONLY`), ciudad, condición | `EVALUATED_EDGE` (bot), `EXTERNAL_SIGNAL` (trader) | join con `bot_evaluation` actualmente nulo en 133/133 filas (A7) | MEDIA para TRADER_ONLY signal; join botEval roto actualmente |
| `shadow_city_tracking.json` | `city`, `markets_seen`, `edge_hits`, `cycles_seen`, `best_edge_pct` | `SHADOW_EDGE` (agregado por ciudad) | outcome de resolución, identidad individual de mercado | BAJA — solo evidencia agregada de ciudad, no mercado |
| `city_validation_ledger.json` / `city_promotion_gate.json` | `city`, `gate_status`, `evidence_counts`, `promotion_criteria`, `phase2_status` | evidencia de ciudad para contexto de stage `BLOCKED_POLICY_SOURCE` vs `SHADOW_EDGE` | join directo con mercados individuales | MEDIA para contexto de ciudad |
| `traders_intelligence/` | traders fuertes, ciudades por trader, señales recientes | `EXTERNAL_SIGNAL` (señal trader) | `condition_id`/`market_id` en muchos casos | MEDIA — identidad a veces derivable por ciudad+fecha |
| `source_onboarding.json` / `docs/source_audits/` | ciudad, ICAO, source_status, audit_result | contexto de `BLOCKED_POLICY_SOURCE` cuando causa es source | no es artefacto por mercado individual | ALTA para contexto de ciudad/source; no para mercado |
| METAR `data/metar_shadow/<ICAO>_date.json` | ICAO, date, measured_temp/precip, comparación vs forecast | evidencia de `source_fidelity_status` para `RESOLVED` | gap de fechas: resoluciones abr vs METAR desde may (0 overlap histórico) | MUY BAJA actualmente (brecha de fechas) |
| `audit.json` (observed_vs_forecast) | ciudad, fecha, forecast vs observado real | contexto de fidelidad para city promotion gate | no hay join con mercados individuales | BAJA para mercado individual; MEDIA para evidencia de ciudad |
| `trade_lifecycle.json` | `token_id`, `market_id`, `condition_id`, precio compra, precio resolución, P&L real | `BUY`, `RESOLVED` con P&L | campo `canonical_source` aún no activo (BANKROLL blocked) | ALTA para operaciones reales; join via token_id |
| `skip_log.jsonl` | `token_id`, `city`, `date_iso`, `condition`, precio al momento del skip, razón | `SKIPPED_*` stages con identidad parcial | `market_id`/`condition_id` en muchas filas; sin consumer automático | MEDIA — dataset granular pero sin join a outcome |
| `sl_intra_guard_audit.json` | ciudad, condición, fecha, guard triggered, review_status | `BLOCKED_POLICY_SOURCE` por SL_intra guard | counterfactual de si habría ganado/perdido | ALTA para hecho de guard trigger; BAJA para evaluación de oportunidad |
| `polymarket.db` (cycle_events, market_snapshots, forecast_snapshots) | `cycle_id`, precios, forecast snapshots | `DISCOVERED`, `PREFILTERED` con mayor granularidad que funnel | `truth_records` no implementado (Fase 1 Truth Pipeline pendiente) | MEDIA — datos crudos sin capa de truth |
| Daily Digest / Telegram | bloques agregados de todos los módulos | **NO** es fuente de verdad — superficie de presentación | sin persistencia estructurada como artefacto de ledger | NO APLICA (superficie, no fuente) |

---

## 5. Clasificación de aprendizaje

### 5.1 Estados de aprendizaje

| Estado | Significado |
|---|---|
| `CANDIDATE_MISSED_OPPORTUNITY` | Evidencia preliminar de oportunidad no tomada, pero sin gates completos |
| `CONFIRMED_MISSED_OPPORTUNITY` | Todos los gates de confirmación cumplidos (ver §5.2) |
| `PROTECTIVE_FILTER_EVIDENCE` | El bot bloqueó correctamente: trader perdió o outcome adverso confirmado |
| `SOURCE_FIDELITY_BLOCKED` | La señal existe pero la fuente de datos no tiene confianza suficiente para operar |
| `SHADOW_HYPOTHESIS` | Evidencia acumulada en shadow que merece seguimiento pero sin resolución aún |
| `EXPERIMENT_CANDIDATE` | Hipótesis con suficiente evidencia para diseñar un experimento LOG_ONLY |
| `NO_ACTION_INSUFFICIENT_EVIDENCE` | No hay datos suficientes para clasificar en ninguna de las anteriores |

### 5.2 Gates para pasar de `CANDIDATE` a `CONFIRMED_MISSED_OPPORTUNITY`

`trader_won + bot_would_buy` **NO** equivale automáticamente a oportunidad perdida confirmada. Para confirmar se requiere:

1. **Identidad joinable con confianza suficiente:** mercado/lado unidos via `condition_id`/`market_id` o `eval_key/match_key` con `join_confidence >= MEDIUM`.
2. **Precio o ventana comparable:** el precio en el momento de la señal trader estaba dentro del rango operable del bot (no OOR).
3. **Outcome resuelto:** el mercado tiene resolución conocida (`win_for_trader` confirmado o `settlement_source` con fidelidad).
4. **Oportunidad ejecutable:** el mercado era ejecutable bajo política del bot en ese momento, O la política que lo bloqueó está identificada explícitamente como el bloqueador (ej. ciudad en modo shadow, source blocked).
5. **Contrafactual estimable:** `bot_would_have_bought` derivable del join `eval_key ↔ match_key` y `would_buy=true` en `bot_signal_evaluations`.
6. **Sin bloqueo crítico de data quality:** no hay `DATA_QUALITY_WARNING` que invalide la conclusión (ej. `bot_evaluation_null`, `settlement_fidelity_status=UNKNOWN`).

Si cualquier gate falla → estado es `CANDIDATE_MISSED_OPPORTUNITY`, no `CONFIRMED`.

---

## 6. Joined view schema — vista derivada conceptual

La vista derivada no es un archivo todavía. Es el schema que debe poder expresar cualquier consumer conforme al contrato (incluyendo el Trader vs Bot Gap Report v1).

```
market_evidence_view {

  // identidad
  condition_id          : string | null          // Polymarket primary key cuando existe
  market_id             : string | null          // Polymarket market key cuando existe
  token_id              : string | null          // solo si hubo posición abierta
  eval_key              : string | null          // clave de join operativo bot
  match_key             : string | null          // clave de join en blocked_signals
  semantic_market_key   : string | null          // fallback semántico
  city                  : string
  date_iso              : string                 // YYYY-MM-DD
  condition             : string
  threshold_low         : float | null
  threshold_high        : float | null
  unit                  : string | null
  side                  : string | null          // YES/NO cuando conocido
  join_confidence       : enum[HIGH,MEDIUM,LOW,NONE]

  // ciclo de vida
  stage                 : enum[DISCOVERED..RESOLVED]
  stage_confidence      : enum[HIGH,MEDIUM,LOW]
  reason_or_gate        : string | null          // razón de skip/block/evaluation

  // evaluación del bot
  bot_would_buy         : bool | null
  bot_edge_pct          : float | null
  bot_decision_gate     : string | null
  bot_skip_reason       : string | null
  bot_evaluation_source : enum[OBSERVED_RUNTIME, DERIVED_JOIN, null]

  // señal trader
  trader_signal_present : bool
  trader_won            : bool | null
  trader_side           : string | null
  crosscheck_type       : enum[MATCH, BOT_ONLY, TRADER_ONLY, null]

  // ciudad y fuente
  city_mode_at_record   : enum[active, canary, shadow, blocked]
  source_fidelity_status: string | null
  metar_available       : bool

  // resolución
  resolution_outcome    : string | null          // YES/NO/AMBIGUOUS
  resolution_source     : string | null
  settlement_fidelity   : string | null

  // P&L o contrafactual
  real_pnl              : float | null           // solo si hubo BUY real
  counterfactual_pnl_estimate : float | null     // estimado si bot habría comprado
  counterfactual_confidence   : enum[HIGH,MEDIUM,LOW,NONE]

  // provenance
  source_artifact       : string
  source_environment    : enum[railway_live, repo_doc, external_observability, derived]
  source_timestamp      : ISO datetime
  generated_at          : ISO datetime
  freshness_status      : enum[FRESH, STALE, UNKNOWN]
  data_quality_flags    : list[string]

  // clasificación de aprendizaje
  learning_classification : enum[
    CANDIDATE_MISSED_OPPORTUNITY,
    CONFIRMED_MISSED_OPPORTUNITY,
    PROTECTIVE_FILTER_EVIDENCE,
    SOURCE_FIDELITY_BLOCKED,
    SHADOW_HYPOTHESIS,
    EXPERIMENT_CANDIDATE,
    NO_ACTION_INSUFFICIENT_EVIDENCE
  ]

  // revisión
  review_status         : enum[PENDING, REVIEWED, CLOSED_NO_ACTION, IN_QUEUE]
}
```

---

## 7. Agent Manifest — índice compacto para LLMs

### 7.1 Qué es el Manifest

El Agent Manifest es un artefacto índice generado periódicamente (no en hot path) que permite a Opus/Sonnet/Codex responder preguntas sobre el estado actual del ledger sin leer millones de líneas.

**No es fuente de verdad.** Es regenerable desde los artefactos originales. Tiene un campo `as_of` obligatorio; si está stale, el consumer debe leer los artefactos originales.

### 7.2 Preguntas que debe poder responder el Manifest

- Top oportunidades perdidas candidatas en los últimos 7 días.
- Filtros protectores demostrados (bot bloqueó, trader perdió).
- Shadow hypotheses con evidencia acumulada suficiente para experimento.
- Source blockers monetizables (ciudades con señal pero source no confiable).
- Data quality gaps que bloquean conclusiones.

### 7.3 Schema conceptual del Manifest

```
agent_manifest {
  as_of                 : ISO datetime
  generated_at          : ISO datetime
  freshness_status      : enum[FRESH, STALE]
  coverage_period       : { from: date, to: date }

  summary_counts {
    total_observations         : int
    joinable_with_identity     : int    // tienen condition_id o eval_key
    with_resolved_outcome      : int
    candidate_missed_opps_7d   : int
    confirmed_missed_opps      : int
    protective_filter_evidence : int
    shadow_hypotheses_active   : int
    data_quality_blocked       : int
  }

  top_candidate_missed_opportunities : [
    {
      rank              : int
      market_identity   : { condition_id, eval_key, city, date_iso, condition }
      learning_class    : "CANDIDATE_MISSED_OPPORTUNITY"
      gates_passed      : list[string]
      gates_missing     : list[string]
      counterfactual_pnl_estimate : float | null
      provenance_pointer: string       // path al artefacto fuente
    }
  ]

  top_protective_filters : [
    {
      filter_type       : string       // ej. SL_intra_guard, city_blocked, source_blocked
      n_cases           : int
      n_trader_lost     : int
      estimated_loss_avoided : float | null
      evidence_grade    : enum[HIGH, MEDIUM, LOW]
    }
  ]

  shadow_hypotheses : [
    {
      hypothesis_id     : string
      city              : string
      condition         : string | null
      n_shadow_edges    : int
      best_edge_pct     : float
      evidence_since    : date
      status            : enum[WATCH, READY_FOR_DESIGN, INSUFFICIENT]
    }
  ]

  source_blockers : [
    {
      city              : string
      source_status     : string
      trader_signals_count : int
      monetizable_if_fixed  : bool
    }
  ]

  data_quality_gaps : [
    {
      artifact          : string
      gap_type          : string
      rows_affected     : int | null
      impact            : string
    }
  ]

  artifact_freshness : {
    [artifact_name]     : { last_updated: ISO datetime, status: enum[FRESH,STALE,UNKNOWN] }
  }
}
```

---

## 8. Learning Review Queue

### 8.1 Propósito

La queue centraliza hipótesis priorizadas que merecen revisión por un agente. No es una lista de alertas — es una lista de hipótesis con evidencia suficiente para ser juzgadas.

**Regla cardinal:** la queue prioriza revisión; **nunca autoriza BUY/SELL/SKIP ni cambios de policy por sí sola.**

### 8.2 Schema de hipótesis

```
learning_review_queue_entry {
  hypothesis_id         : string               // ej. "LRQ-2026-05-001"
  created_at            : ISO datetime
  updated_at            : ISO datetime

  hypothesis_type       : enum[
    MISSED_OPPORTUNITY,
    PROTECTIVE_FILTER_VALIDATION,
    SOURCE_FIDELITY_BLOCKER,
    SHADOW_CITY_CANDIDATE,
    CONDITION_FILTER_REVIEW,
    DATA_QUALITY_RESOLUTION
  ]

  market_scope {
    city                : string | null
    condition           : string | null
    filter_type         : string | null         // ej. "condition_filtered", "city_blocked"
    date_range          : { from: date, to: date } | null
  }

  evidence_summary      : string               // texto breve (≤3 oraciones)
  sample_size           : int
  sample_since          : date
  join_confidence       : enum[HIGH, MEDIUM, LOW, NONE]

  counterfactual_pnl_status : enum[
    ESTIMABLE,
    NOT_ESTIMABLE_MISSING_FIELDS,
    NOT_APPLICABLE
  ]

  source_fidelity_status : string | null

  risk_constraints      : list[string]         // ej. ["bankroll_blocked", "phase_c_pending"]

  recommended_agent     : enum[Opus, Sonnet, Codex]
  allowed_next_action   : string               // ej. "design_experiment_log_only", "read_only_audit"

  stop_criterion        : string               // cuándo cerrar aunque no haya conclusión
  reopen_trigger        : string               // qué evidencia nueva reabriría esta hipótesis

  status                : enum[
    WATCH,
    READY_FOR_DESIGN,
    DATA_GAP,
    CLOSED_NO_ACTION,
    IN_PROGRESS
  ]

  closing_verdict       : string | null        // cuando status = CLOSED_NO_ACTION
}
```

### 8.3 Priorización de la queue

Orden de revisión sugerido (de mayor a menor prioridad):

1. Hipótesis con `join_confidence >= MEDIUM` + `counterfactual_pnl_status = ESTIMABLE` + `sample_size >= 15`.
2. `PROTECTIVE_FILTER_VALIDATION` con `n_trader_lost >= 5` (confirmación de guardrail activo).
3. `SOURCE_FIDELITY_BLOCKER` con ciudades que tienen `trader_signals_count >= 3` (monetizable si se resuelve).
4. `SHADOW_CITY_CANDIDATE` con `n_shadow_edges >= 10` y `best_edge_pct >= 30%`.
5. Todo lo demás: `WATCH` o `DATA_GAP`.

---

## 9. Trader vs Bot Gap Report v1 — primer consumer del contrato

### 9.1 Descripción

El Trader vs Bot Gap Report v1 es una **query/vista conforme a este contrato**, no una herramienta aislada con arquitectura propia. Consume exactamente los artefactos definidos en §4 usando las claves de join de §2.

**Estado:** Fase 2. No implementar todavía.

### 9.2 Join operativo

```
bot_signal_evaluations.eval_key
    ↔ blocked_signals_resolutions.match_key
    ↔ signals_crosscheck (por ciudad/fecha/condición cuando no hay eval_key directo)
```

El join `eval_key ↔ match_key` está contractado en `docs/instrumentation/bot_evaluation_capture.md` y activo via `READ_BOT_EVAL_CAPTURE=1`.

### 9.3 Cuadrantes que debe identificar

| Cuadrante | Trader | Bot | Clasificación de aprendizaje |
|---|---|---|---|
| Q1 | ganó | habría comprado | `CANDIDATE_MISSED_OPPORTUNITY` (requiere gates de §5.2 para `CONFIRMED`) |
| Q2 | ganó | no habría comprado / bloqueado | `PROTECTIVE_FILTER_EVIDENCE` o `SOURCE_FIDELITY_BLOCKED` |
| Q3 | perdió | habría comprado | riesgo evitado (el bot evitó la pérdida del trader) |
| Q4 | perdió | no habría comprado | filtro correcto o señal incorrecta sin consecuencia |

### 9.4 Output del reporte

- JSON compacto en `data/intelligence/` (gitignored, Railway).
- Markdown legible en `docs/intelligence/` (versionado).
- LOG_ONLY — sin consumer ejecutable en Fase 2.
- Alimenta Agent Manifest y Review Queue en iteraciones posteriores.

### 9.5 Campos ya disponibles para el join

| Campo | Disponibilidad | Fuente |
|---|---|---|
| `eval_key` / `match_key` | ✅ Activo | `bot_signal_evaluations`, `blocked_signals_resolutions` |
| `would_buy` | ✅ Activo | `bot_signal_evaluations` |
| `win_for_trader` | ✅ Activo (cuando resuelto) | `blocked_signals_resolutions` v2 |
| `reason_blocked` | ✅ Activo | `blocked_signals_resolutions` v2 |
| `crosscheck_type` | ✅ Activo | `signals_crosscheck.jsonl` |
| `city_mode_at_record_time` | ✅ Activo | `blocked_signals_resolutions` v2 |
| `price_bucket` | ✅ Activo | `blocked_signals_resolutions` v2 |

### 9.6 Campos ausentes que limitarán las conclusiones en Fase 2

| Campo ausente | Impacto |
|---|---|
| `bot_would_have_bought` (nulo, Fase C) | Q1 no puede confirmarse sin este campo; solo es `CANDIDATE` |
| `settlement_source` / `settlement_fidelity_status` (Fase C) | Outcomes de resolución sin fidelidad verificada |
| `bot_evaluation=null` en 133/133 filas de `signals_crosscheck` (A7) | Cuadrante TRADER_ONLY no puede cruzarse con evaluación del bot hasta que se resuelva el gap A7 |
| market identity en `funnel_observability` | Descartes previos a `EVALUATED` no pueden trazarse como candidatos |

El reporte debe documentar estas limitaciones explícitamente en su output y clasificar apropiadamente como `CANDIDATE` vs `CONFIRMED`.

---

## 10. Capturas futuras — documentadas, no autorizadas

Las siguientes capturas son candidatas a Fase 3. No implementar hasta que Fase 2 demuestre señal monetizable real.

### 10.1 Sample top-N con identidad para `city_window` discards

**Por qué:** convierte `Q1` de `CAPTURE_MISSING` a potencialmente `ANSWERABLE`.
**Qué sería:** top-N `condition_id`/`market_id` por ciclo en `SKIPPED_CITY_WINDOW` (patrón existente: `sample_shadow_edges`).
**Trigger de autorización:** Fase 2 produce ≥1 `CONFIRMED_MISSED_OPPORTUNITY` con join completo.

### 10.2 Sample top-N con identidad/precio para `price` discards

**Por qué:** convierte `Q3` de `CAPTURE_MISSING` a potencialmente `ANSWERABLE`.
**Qué sería:** top-N `market_id` + precio OOR por ciclo en `SKIPPED_PRICE`.
**Trigger de autorización:** igual que 10.1.

### 10.3 Skip log → outcome join

**Por qué:** convierte Q2 de `DATA_EXISTS_NOT_JOINED` a `PARTIALLY_CONNECTED`.
**Qué sería:** join `skip_log.jsonl` (city+date+condition) ↔ `blocked_signals_resolutions.match_key`.
**Limitación actual:** `skip_log` no tiene `market_id` en mayoría de filas; join es aproximado.
**Trigger de autorización:** `skip_log` instrumentado con `token_id` consistente, y hay ≥20 resoluciones con match.

### 10.4 Source fidelity → evidence ledger link

**Por qué:** convierte `SOURCE_FIDELITY_BLOCKED` de contextual a verificable.
**Qué sería:** join automático `source_onboarding.json` por ciudad ↔ `blocked_signals_resolutions` por ciudad.
**Trigger de autorización:** ≥3 ciudades con `SOURCE_FIDELITY_BLOCKED` y trader signals.

### 10.5 METAR alignment cuando exista muestra suficiente

**Por qué:** necesario para validar resoluciones con fidelidad de medición real.
**Qué falta:** solapamiento de fechas (resoluciones abr, METAR desde may).
**Trigger de autorización:** ≥10 resoluciones nuevas con METAR contemporáneo disponible.

---

## 11. Métricas de éxito del ledger

Las métricas deben medir **aprendizaje real** y no volumen de reporting.

### 11.1 Métricas de cobertura

| Métrica | Descripción | Meta v1 |
|---|---|---|
| `joinable_identity_coverage` | % de observaciones con `condition_id` o `eval_key` | > 40% para Fase 2 |
| `resolved_outcome_coverage` | % de observaciones con outcome conocido | > 30% |
| `sufficient_sample_hypotheses` | hipótesis en queue con `sample_size >= 15` | > 0 tras 30d |

### 11.2 Métricas de aprendizaje

| Métrica | Descripción |
|---|---|
| `candidate_missed_opps_7d` | Candidatos de oportunidad perdida en últimos 7 días |
| `confirmed_missed_opps` | Candidatos que pasaron todos los gates de §5.2 |
| `protective_filters_confirmed` | Filtros donde bot bloqueó y trader perdió (evidencia de guardrail) |
| `opus_decisions_enabled` | Decisiones Opus tomadas que citan evidencia del ledger |
| `hypotheses_closed_no_action` | Hipótesis cerradas como `NO_ACTION` (aprendizaje negativo también cuenta) |

### 11.3 Anti-métrica

> **Más alertas sin decisiones nuevas** = fracaso del ledger.

Si el número de observaciones en la queue crece pero el número de `opus_decisions_enabled` + `confirmed_missed_opps` + `hypotheses_closed_no_action` no crece, el ledger está produciendo ruido, no aprendizaje.

---

## 12. Primera tarea posterior propuesta

### Trader vs Bot Gap Report v1 — first ledger consumer

**Trigger:** este contrato queda aprobado por Pablo/ChatGPT.
**Agente recomendado:** Codex (implementación) precedido de diseño Sonnet (schema del output y join logic).
**Alcance:** implementar `tools/trader_vs_bot_gap_report.py` que:
  1. Lee `bot_signal_evaluations.jsonl` + `blocked_signals_resolutions.jsonl` + `signals_crosscheck.jsonl`.
  2. Hace join por `eval_key ↔ match_key`.
  3. Segmenta los 4 cuadrantes de §9.3.
  4. Clasifica cada fila según §5.1.
  5. Documenta en output cuáles gates de §5.2 están satisfechos y cuáles no.
  6. Emite JSON en `data/intelligence/trader_vs_bot_gap_report_<date>.json` y Markdown en `docs/intelligence/`.
  7. Queda LOG_ONLY. Sin consumer ejecutable.

**Criterio de parada:** reporte con n≥30 filas joined, distribución por cuadrante, y documentación explícita de campos ausentes que limitan conclusiones.

**Guardrail de cierre:** el reporte no autoriza BUY/SELL/SKIP ni cambios de policy. Su único output accionable es alimentar la Learning Review Queue con hipótesis clasificadas.

---

## 13. Validación de cobertura de producers AS-IS

Verificación de que los 16 producers/capas del audit AS-IS quedan mapeados en este contrato:

| Producer (AS-IS §2) | Cubierto en contrato | Sección |
|---|---|---|
| Funnel Observability (`funnel_observability_log_only.jsonl`) | ✅ | §4.2, §10.1, §10.2 |
| Bot Signal Evaluations (`bot_signal_evaluations.jsonl`) | ✅ | §2.1, §4.2, §9.5 |
| Blocked Signals Resolutions (`blocked_signals_resolutions.jsonl`) | ✅ | §2.1, §4.2, §9.5 |
| Signals Crosscheck (`signals_crosscheck.jsonl`) | ✅ | §4.2, §9.2, §9.6 |
| Traders Intelligence (`data/traders_intelligence/`) | ✅ | §3.1 (EXTERNAL_SIGNAL), §4.2 |
| Traders Operational Intelligence / Gap Monitor | ✅ | §4.2 (gap A7 documentado), §9.6 |
| METAR Measurement Layer (`data/metar_shadow/`) | ✅ | §4.2, §10.5 |
| Source Fidelity / Onboarding Scanner | ✅ | §4.2, §10.4 |
| City Intelligence / Lifecycle Review | ✅ | §4.2 |
| Shadow City Tracking (`shadow_city_tracking.json`) | ✅ | §4.2 |
| Trade Lifecycle / P&L (`trade_lifecycle.json`) | ✅ | §4.2 |
| SL / Guards / L2 Hazard (`sl_intra_guard_audit.json`) | ✅ | §4.2 |
| SQLite / DB Throughput (`polymarket.db`) | ✅ | §4.2 |
| Daily Digest / Telegram | ✅ (superficie, no fuente) | §1.2, §4.2 |
| Skip Log (`skip_log.jsonl`) | ✅ | §4.2, §10.3 |
| NOAA / Open-Meteo / Observed-vs-Forecast (`audit.json`) | ✅ | §4.2, §10.5 |

**Cobertura: 16/16 producers mapeados o marcados fuera de scope con justificación.**

---

*Documento generado por Sonnet en Sesión 381, 2026-05-23. Docs-only. Sin código, runtime, env vars, DB ni cambios de trading.*
