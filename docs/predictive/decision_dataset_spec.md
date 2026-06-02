# E1 — Canonical Decision Dataset — Design Spec

**Sprint:** Predictive Intelligence Sprint V1 · Entregable 1
**Modo del documento:** DESIGN-ONLY (este doc es el único artefacto producido; no hay código).
**Autor del diseño:** Opus · 2026-06-02
**Estado:** SPEC_READY_FOR_HANDOFF (implementa Codex/Sonnet contra este contrato)
**Veredicto que materializa:** `NEEDS_DATA_CONSOLIDATION_FIRST` ejecutado como `START_SPRINT_NOW`.

---

## 0. Contrato de la sesión (no negociable)

Este spec **no** autoriza ni propone:

- live trading, BUY/SELL/SKIP, cambios en `bot.py`, trading core, sizing, scheduler, city modes, guards, SL.
- subir BANKROLL (sigue $25 HOLD), Fase C, lift de exact/NO.
- cambios de env vars, escrituras a Railway, escrituras a la DB de producción.
- uso de `trades.log` como fuente canónica.
- P&L canónico: **sigue `none`**. Todo P&L de este dataset es **simulado/contrafactual** y vive en su propio carril.

Separación dura que atraviesa todo el documento:

> **Canónico para learning/eval** (lo que construye E1) **≠** **Canónico para P&L/cash** (R1/R2, no tocado aquí).

---

## 1. Problema que resuelve

El bot tiene ~100 herramientas en `tools/` y decenas de JSONL, pero **no tiene un libro único de verdad**. Consecuencia: el sistema *observa* pero no *aprende*. Las cinco fallas concretas:

1. **Datos fragmentados.** Las features de decisión viven en `bot_signal_evaluations.jsonl`; los outcomes en `exact_no_resolutions_log_only.jsonl` y `blocked_signals_resolutions.jsonl`; los features-de-forecast en `forecast_snapshots` (SQLite, solo prod). Nadie los junta en una fila por decisión.

2. **Resolvers duplicados.** `exact_no_proto_r2_resolver.py`, `_self_evaluation_engine.py`, `blocked_signals_settlement_tracker.py`, `cohort_intelligence_report.py` y otros **reimplementan cada uno** la misma lógica: fetch Gamma → `outcomePrices>=0.95` → dedup → madurez T+7 → WR/sim_pnl/calibration_gap. Es la misma función escrita ~6 veces, divergiendo silenciosamente.

3. **n dispersa por cohorte.** Como cada experimento solo ve su propia rodaja (exact/NO mature n=17, at_or_below "insuficiente", etc.), **ninguno alcanza significancia**. El n total del universo nunca se poolea.

4. **Falta de benchmark pooled contra mercado.** El único eval real (`_self_evaluation_engine.py`, Brier vs mercado) corre por-cohorte y ya dio señal negativa (`at_or_above brier_advantage=-0.0939`), pero no existe una tabla única predictor-vs-mercado sobre todo el universo.

5. **Observabilidad ≠ learning loop.** Un dashboard que muestra el estado es observabilidad. Un *learning loop* requiere: dataset → label → baseline → holdout → benchmark → criterio de promoción, sobre **una sola fuente**. E1 construye el **dataset** y el **label** de ese loop; E2 construye baseline/holdout/benchmark; E3 el criterio de promoción.

**E1 es la condición necesaria de E2 y E3.** Sin libro único, no hay examen.

---

## 2. Schema objetivo

Base: `sql/002_truth_pipeline.sql` (schema v2 ya existente: `truth_records`, `truth_revisions`, vistas `v_decision_truth`, `forecast_truth_join`). El delta es **aditivo** (nueva migración `003`), nunca destructivo, y mantiene idempotencia (`IF NOT EXISTS` / `ALTER TABLE ADD COLUMN`).

### 2.1 Columnas de `truth_records` que ya sirven (reutilizar tal cual)

| Columna | Rol en el dataset |
|---|---|
| `city`, `date_iso`, `condition`, `threshold_c` | identidad + feature de mercado |
| `question`, `market_id`, `token_id_yes`, `token_id_no` | identidad de mercado Gamma/CLOB |
| `forecast_high_c`, `forecast_source` | **FEATURE** (predicción meteorológica) |
| `observed_high_c`, `observed_source` | soporte de label (temperatura real observada) |
| `resolution_outcome`, `resolution_ts_utc`, `resolution_method` | **LABEL** (YES/NO/VOID/UNKNOWN oficial) |
| `bot_had_position`, `bot_side` | contexto: si el bot real tenía posición |
| `snapshot_ts_utc` | timestamp del snapshot de decisión |
| `payload_json` | replay completo (todo campo no promovido a columna vive aquí) |

Las vistas `v_decision_truth` (computa `forecast_correct`, `position_correct`) y `forecast_truth_join` se conservan y se **extienden** en §2.4.

### 2.2 Schema delta aditivo propuesto (migración `003`)

Cada columna se justifica o se descarta. **Regla:** una columna entra solo si E2 (benchmark predictor-vs-mercado) o la idempotencia la necesitan; lo demás vive en `payload_json`.

| Columna nueva | Tipo | Justificación | ¿Añadir? |
|---|---|---|---|
| `market_prob_at_eval` | REAL | **Baseline del benchmark.** Precio/prob implícita de mercado del lado evaluado en el momento de la decisión (`mkt_prob` / `mkt_prob_no`). Sin esto no hay predictor-vs-mercado. `truth_records` hoy **no tiene ningún campo de precio de mercado.** | **SÍ — crítica** |
| `model_prob` | REAL | Probabilidad del predictor del bot en el momento de decisión (`our_prob` / `our_prob_no`). Necesaria para Brier del candidato. | **SÍ — crítica** |
| `side` | TEXT | Lado evaluado de la decisión ('YES'\|'NO'). Distinto de `bot_side`, que solo existe cuando hubo posición real. Para shadow/eval necesitamos el lado evaluado aunque no haya posición. | **SÍ** |
| `sim_unit_pnl` | REAL | P&L contrafactual por share del lado evaluado al precio de eval: `win → (1-price)`, `lose → -price`. Materializado para velocidad del benchmark. **No canónico** (ver §6). | **SÍ** |
| `eval_source` | TEXT | Artefacto/cohorte que originó la fila (`bot_signal_evaluations` \| `exact_no` \| `blocked_signals` \| `self_eval`). Provenance + filtrado + reproducción de tests por-cohorte. | **SÍ** |
| `resolution_status` | TEXT | Estado de resolución desacoplado del outcome: `settled` \| `pending` \| `void`. Permite distinguir "no resuelto aún" de "resuelto VOID". | **SÍ** |
| `maturity_bucket` | TEXT | Clasificación T+7: `settled_mature` (settled ∧ days≥7) \| `resolved_fresh` (settled ∧ days<7) \| `pending`. **Solo `settled_mature` es elegible para calibración/promoción.** | **SÍ — crítica** |
| `cohort_key` | TEXT | **Habilitador del pooling y de las ablations.** Clave de agrupación canónica (ver §4.6). Sin esto no se puede poolear n ni hacer ablations por condición/ciudad/days_ahead/edge_bucket. | **SÍ — crítica** |
| `days_ahead` | INTEGER | Días entre snapshot y `date_iso`. Ablation por horizonte. Derivable, pero se materializa para el benchmark. | **SÍ** |
| `edge_pct_at_eval` | REAL | Edge declarado al eval (`bot_edge_pct_at_signal` / `best_edge_pct_log_only`). Ablation por `edge_bucket`. Si falta, se deriva de `model_prob - market_prob_at_eval`. | **SÍ** |
| `decision_id` | TEXT | **Clave estable de idempotencia.** Hash determinista (ver §4.1). El `id` autoincrement de `truth_records` NO es estable entre rebuilds; `decision_id` sí. | **SÍ — crítica** |
| `data_provenance` | TEXT (JSON) | `{source_file, sha256, capture_method, capture_ts}` por fila. Reproducibilidad + "repo como fuente de verdad" (§9). | **SÍ** |
| `unit_raw` | TEXT | Unidad original ('C'\|'F') antes de normalizar a `threshold_c`. Auditoría de la conversión §4.5. | **SÍ** |

### 2.3 Columnas que NO deben añadirse (y por qué)

| Descartada | Motivo |
|---|---|
| `realized_pnl`, `cash_*`, `fee_*` | P&L canónico/cash es territorio R1/R2. Añadirlo aquí rompería la separación dura §6 y crearía la ilusión de que E1 autoriza accounting. **Prohibido.** |
| `order_id`, `fill_price`, `fill_size` | Pertenecen a R1 (`reconcile_executions.py`). Solo se *joinean* más tarde cuando existan fills reales (§6.4). No ahora. |
| `trader`, `trader_historical_wr`, `has_consensus` | Vienen de BSR y describen el **path de alpha "trader-following"**, que es un modelo distinto. Promoverlos a columnas mete scope creep del path-trader dentro de E1. Se conservan en `payload_json`. |
| `sigma_used`, `forecast_max` crudos como columnas | Features secundarias de modelo; viven en `payload_json` hasta que una ablation las requiera. Evita inflar el schema antes de tener señal. |

### 2.4 Extensión de vistas

- `v_decision_truth` se extiende con: `market_prob_at_eval`, `model_prob`, `side`, `sim_unit_pnl`, `maturity_bucket`, `cohort_key`, `days_ahead`, `edge_pct_at_eval`. Mantiene `forecast_correct` y `position_correct`.
- Nueva vista `v_benchmark_input`: filtra `maturity_bucket='settled_mature'` ∧ `model_prob IS NOT NULL` ∧ `market_prob_at_eval IS NOT NULL` ∧ `resolution_outcome IN ('YES','NO')`. **Esta es la única vista que E2 consume.** Aísla al benchmark de filas inmaduras o sin features.

---

## 3. Fuentes de datos (inventario)

Leyenda de rol: **F**=feature · **L**=label/outcome · **M**=market price · **C**=contexto.

### 3.1 `bot_signal_evaluations.jsonl` — fuente primaria de features (todas las condiciones)
- **Contiene:** una fila por evaluación de señal por ciclo. Campos confirmados: `schema_version, ts_utc, cycle_id, eval_key, city, date_iso, condition, threshold, threshold_high, unit, would_buy, bot_edge_pct_at_signal, evaluation_source, skip_or_block_reason, decision_gate, decision_confidence, our_prob, mkt_prob, forecast_max, sigma_used, days_ahead`.
- **Vive en:** runtime / Railway (`/app/data/`), importado vía `runtime_import`; observado local en `_tmp_bot_brain_runtime/`. **Gitignored.**
- **Rol:** **F + M + C** (`our_prob`→`model_prob`, `mkt_prob`→`market_prob_at_eval`, `bot_edge_pct_at_signal`→`edge_pct_at_eval`, `forecast_max`→feature). `would_buy`/`decision_gate`/`skip_or_block_reason`→contexto.
- **Canónica:** no (no resuelve outcome). Es el **esqueleto de filas** del dataset.
- **Riesgos:** `our_prob`/`mkt_prob` frecuentemente `null` cuando `decision_gate=condition_filtered` → esas filas no son elegibles para benchmark (caen fuera de `v_benchmark_input`); BOM UTF-8 al inicio del archivo (visto: `﻿`); `threshold` numérico crudo (no convertido a °C).

### 3.2 `exact_no_qt_match_evaluations_log_only.jsonl` — features cohorte exact/NO
- **Contiene:** evaluaciones exact/NO con `market_id, condition_id, eval_key, date_iso, our_prob_no, mkt_prob_no, best_edge_pct_log_only, best_side_log_only, city, condition, threshold, unit, ts_utc`.
- **Vive en:** **prod/gitignored — NO está local.** Solo accesible vía runtime_import / Railway SSH.
- **Rol:** **F + M** del cohorte exact/NO (`our_prob_no`→`model_prob` con `side='NO'`, `mkt_prob_no`→`market_prob_at_eval`).
- **Canónica:** no. Es el *input* del proto-R2.
- **Riesgos:** ausencia local obliga a un pull SSH read-only; `our_prob_no` es prob del lado NO (no YES) — `side` debe fijarse explícito.

### 3.3 `exact_no_resolutions_log_only.jsonl` — outcomes resueltos cohorte exact/NO (proto-R2 output)
- **Contiene:** salida del proto-R2 (62 filas local). Campos: `eval_key, market_id, condition_id, city, date_iso, condition, threshold, unit, best_side_log_only, entry_edge_log_only, market_outcome, no_would_win, resolution_source(gamma_official), resolved_at, settlement_mature_t7, days_since_date, p_model_no, p_market_no_at_eval, simulated_unit_pnl, calibration_gap_component, bucket`.
- **Vive en:** repo local (`data/`), **gitignored** por contenido runtime.
- **Rol:** **L + M + sim_pnl** del cohorte exact/NO. `market_outcome`→`resolution_outcome`, `bucket`→`maturity_bucket`, `simulated_unit_pnl`→`sim_unit_pnl`.
- **Canónica para outcome:** **sí** (`resolution_source=gamma_official`) — pero solo para su cohorte. E1 lo trata como un cohorte más, no como el resolver.
- **Riesgos:** está marcado `calibration_audit_only`; es el **oráculo de los acceptance tests** (§8) — la implementación canónica debe **reproducirlo**, no reemplazar sus números.

### 3.4 `blocked_signals_resolutions.jsonl` — outcomes vía señales de trader
- **Contiene:** 113 filas (`runtime_import_derived/`). Campos: `checked_at, match_key, city, date, condition, trader, trader_historical_wr, outcome(Yes/No), avg_price_entered, close_price, yes_price, no_price, resolved, win_for_trader, has_consensus`.
- **Vive en:** `data/runtime_import_derived/` (importado de Railway).
- **Rol:** **L + cross-check**. `outcome`→outcome oficial (close_price=1.0 confirma settle); `match_key` usa el **mismo formato** que `eval_key` (`City|date|condition|threshold|unit`).
- **Canónica para outcome:** sí (close prices oficiales), pero su lente es **trader-céntrica** (qué lado tomó un trader), no bot-céntrica.
- **Riesgos:** `outcome` describe el lado del trader, no del bot → para derivar "ganó NO" hay que combinar `outcome` + `win_for_trader` (lógica ya en proto-R2 `bsr_no_would_win`); los campos `trader*`/`has_consensus` NO se promueven a columnas (§2.3). Uso principal: **cross-check de outcomes** (§5.5), no como fuente de features.

### 3.5 `price_filter_counterfactual_log_only.jsonl` — contrafactual de filtro de precio
- **Contiene:** contrafactual de qué habría pasado sin el filtro de precio (señales filtradas por precio).
- **Vive en:** prod/gitignored — **no local**.
- **Rol:** **C** (contexto) en V1. *Opcional.* Solo se ingiere si aporta `our_prob`/`mkt_prob` resolubles; si no, se difiere a V2.
- **Canónica:** no.
- **Riesgos:** scope creep — **no incluir en V1 salvo que ya tenga features+market resolubles.** Marcar como diferido.

### 3.6 multimodel / H3 snapshots
- **Rol en V1:** **diferido.** H3 (multimodelo) y sus snapshots son una fuente de features candidata para ablations futuras, pero añadirla ahora multiplica la complejidad de normalización. Documentar como "fuente V2", no ingerir.

### 3.7 self-evaluation evidence (`_self_evaluation_engine.py`)
- **Contiene:** no es un JSONL persistente propio; el engine **lee** `bot_signal_evaluations.jsonl` (condiciones `at_or_above`/`at_or_below`), resuelve vía Gamma y computa Brier (`brier_advantage`, `n_resolved`, particiones `evidence_frozen`/`forward_holdout` con cutoff `2026-05-29`).
- **Rol:** **define el contrato del benchmark** (E2), no una fuente de filas nueva. Su cutoff de pre-registro y su lógica Brier se reutilizan en E2.
- **Canónica:** su outcome (Gamma) sí; su salida es reporte read-only (`eligible_for_policy=false`).
- **Riesgos:** E1 debe garantizar que las filas `at_or_above`/`at_or_below` que produce el dataset son **las mismas** que el self-eval resuelve, para que `brier_advantage=-0.0939` sea reproducible (§8).

### 3.8 R1 reconciled executions (`reconcile_executions.py` → `reconciled_executions.jsonl`)
- **Contiene:** fills reconciliados desde snapshots de contexto (`performance.json`, `postmortem.json`, `trade_lifecycle.json`, `r1_context_provenance.json`) + fills CLOB (`get_trades(order_id)` cuando exista `order_id`). LOG_ONLY, sin P&L canónico.
- **Vive en:** `data/reconciled_executions.jsonl` (cuando se genere).
- **Rol en E1:** **diferido — solo carril de conexión futura** (§6.4). NO se ingiere como feature/label en V1. Es la futura puerta a P&L real, no parte del dataset de learning de V1.
- **Riesgos:** confundir fills reales con sim_pnl rompería la separación §6. Mantener fuera de `truth_records` en V1.

### 3.9 `forecast_snapshots` (SQLite, schema v1)
- **Contiene:** `cycle_number, ts_utc, city, target_date, forecast_high_c, source, payload_json`.
- **Vive en:** **SQLite de producción** (`data/polymarket.db` en Railway). **No existe DB local.**
- **Rol:** **F** — enriquece `forecast_high_c`/`forecast_source` vía `forecast_truth_join` (`fs.city=tr.city AND fs.target_date=tr.date_iso`).
- **Canónica:** sí para el feature de forecast.
- **Riesgos:** requiere pull SSH read-only; `source` vs `observed_source`/`forecast_source` naming (§4.4).

### 3.10 Resumen de inventario

| Fuente | Local | Rol | Canónica outcome | V1 |
|---|---|---|---|---|
| `bot_signal_evaluations.jsonl` | runtime/gitignored | F+M+C | no | **incluir (esqueleto)** |
| `exact_no_qt_match_evaluations_log_only.jsonl` | prod SSH | F+M | no | **incluir** |
| `exact_no_resolutions_log_only.jsonl` | local/gitignored | L+M+sim | sí (cohorte) | **incluir (oráculo test)** |
| `blocked_signals_resolutions.jsonl` | runtime_import | L+cross-check | sí | **incluir (cross-check)** |
| `forecast_snapshots` (SQLite) | prod SSH | F | sí (forecast) | **incluir (enrich)** |
| `price_filter_counterfactual_log_only.jsonl` | prod | C | no | diferir |
| multimodel/H3 | prod | F | no | diferir |
| `reconciled_executions.jsonl` (R1) | local futuro | P&L real | n/a | **diferir (carril §6.4)** |

---

## 4. Reglas de identidad

### 4.1 `decision_id` (clave estable de idempotencia)
```
decision_id = sha256_short( eval_key + "|" + side + "|" + eval_source + "|" + snapshot_bucket )
```
donde `snapshot_bucket` = `ts_utc` truncado al ciclo (p. ej. `cycle_id` si existe, o `ts_utc` redondeado a hora). Garantiza que **el mismo eval del mismo lado por la misma fuente en el mismo ciclo** colapsa a una fila estable entre reruns. Es la base de la idempotencia (§5.4), independiente del `id` autoincrement de SQLite.

### 4.2 Jerarquía de claves
- `eval_key` = **`City|date|condition|threshold|unit`** (confirmado en datos: `"Toronto|2026-05-24|exact|17|C"`). Clave humana primaria.
- `match_key` (BSR) = **mismo formato** que `eval_key` → join directo BSR↔dataset por igualdad de string normalizado.
- `market_id` = id numérico Gamma (`"2328298"`). Clave para resolución de outcome.
- `condition_id` = hash CLOB `0x...`. Clave de mercado on-chain; se conserva pero no es la clave de join principal.
- `cohort_key` (§4.6) = clave de agrupación para pooling.

### 4.3 `date` vs `date_iso`
Normalizar **siempre a `date_iso`** (`YYYY-MM-DD`). BSR usa `date`; `bot_signal_evaluations`/proto-R2 usan `date_iso`; `truth_records` usa `date_iso`. La normalización ocurre en el loader, no en el schema.

### 4.4 `source` vs `observed_source` vs `forecast_source`
- `forecast_snapshots.source` → mapea a `truth_records.forecast_source` (origen del forecast: `open_meteo`, `noaa`, ...).
- `observed_source` → origen de la **temperatura observada** (label meteorológico), distinto del origen del **outcome de mercado** (`resolution_method='gamma_official'`).
- Regla: **forecast_source ≠ observed_source ≠ resolution_method.** Tres orígenes distintos, tres columnas distintas. Nunca colapsar.

### 4.5 Naming de condición y unidades
- Condiciones canónicas: **`exact` · `range` · `at_or_above` · `at_or_below`** (set cerrado; cualquier otra → `UNKNOWN`, fila cuarentenada, no descartada silenciosamente).
- Unidades: conservar `unit_raw` ('C'\|'F') y derivar `threshold_c` (única columna numérica de umbral). Conversión F→C explícita y auditada; `threshold_high` (rango) va a `payload_json` en V1.

### 4.6 `cohort_key` (clave de pooling)
Definición canónica para que E2 poolee n y haga ablations sin re-derivar:
```
cohort_key = condition + "|" + side + "|" + days_ahead_bucket + "|" + edge_bucket
```
- `days_ahead_bucket`: `{0-1, 2-3, 4-7, 8+}`.
- `edge_bucket`: `{<5%, 5-15%, 15-30%, 30%+}` sobre `edge_pct_at_eval`.
- `city` **no** entra en `cohort_key` por defecto (fragmentaría demasiado), pero es columna independiente para ablation por ciudad on-demand.
- Justificación: este es el nivel de granularidad donde el pooling tiene n suficiente y las ablations son interpretables. Ajustable en E3 si el benchmark lo pide.

### 4.7 `side` (YES/NO)
- Fuente exact/NO: `best_side_log_only` ∈ {`YES`,`NO`} → `side` directo.
- Fuente `bot_signal_evaluations`: derivar `side` del lado evaluado (si `our_prob` es prob-YES, `side='YES'`; documentar la convención por `evaluation_source`).
- BSR: `outcome` ∈ {`Yes`,`No`} es el lado del **trader** → normalizar a mayúsculas pero **no** usar como `side` del dataset (es cross-check de outcome, no de decisión).

### 4.8 Duplicados (mismo mercado en varios ciclos)
Dedup por `decision_id`. Dentro de un grupo (mismo eval visto en N ciclos):
- `model_prob`/`market_prob_at_eval`/`edge_pct_at_eval` = valores del **primer** ciclo (por `ts_utc` ascendente) → "edge de entrada".
- `max_edge` (a `payload_json`) = máximo edge observado en el grupo.
- `duplicate_count` (a `payload_json`) = N.
Esta es exactamente la lógica `dedup_groups` del proto-R2; se extrae al resolver canónico (§5) para que no se reimplemente.

---

## 5. Resolución de outcomes (pase único canónico)

**Principio rector:** existe **un solo** resolver de outcomes. Reemplaza las ~6 copias. Toda fila del dataset obtiene su label por este pase; ningún cohorte vuelve a llamar Gamma por su cuenta.

### 5.1 Fuente de outcome
- **Solo oficial Polymarket/Gamma:** `outcomePrices >= 0.95` en un lado ⇒ `settled`, ese lado ganó.
- **Prohibido** derivar outcome de NOAA / Open-Meteo / forecast / temperatura observada. La temperatura observada (`observed_high_c`) es **feature de calibración**, no label de mercado. El label es la resolución de mercado, no la verdad meteorológica.

### 5.2 Madurez
- `settled_mature`: `settled` ∧ `days_since(date_iso) >= 7` (T+7). **Único bucket elegible para calibración/promoción.**
- `resolved_fresh`: `settled` ∧ `days < 7`. Observabilidad; **no elegible**.
- `pending`: no settled aún.
- `void`/`unknown`: `resolution_status='void'`, fuera del benchmark.

### 5.3 Resolver canónico (módulo único)
Extraer la lógica común (hoy duplicada en proto-R2 y self-eval) a un módulo sibling, p. ej. `tools/_canonical_resolver.py`, con la interfaz:
- `fetch_outcome(market_id) -> {settled, yes_price, no_price, resolved_at}`
- `classify_maturity(date_iso, settled, today) -> maturity_bucket`
- `simulated_unit_pnl(side_won, price_at_eval) -> float`
- `calibration_gap_component(model_prob, outcome01) -> float`
Estas funciones ya existen en `exact_no_proto_r2_resolver.py` — se **mueven**, no se reescriben. Proto-R2 y self-eval pasan a importarlas (refactor diferido, no obligatorio para E1, pero el resolver canónico debe ser bit-compatible con proto-R2 — ver §8).

### 5.4 Idempotencia
- Upsert por `decision_id`: rerun no crea filas nuevas.
- Si cambia `observed_high_c` o `resolution_outcome` de una fila existente → actualizar campo + insertar fila en `truth_revisions` (mecanismo ya implementado en `truth_pipeline_runner.py`, `_TRACKED_FIELDS`). Extender `_TRACKED_FIELDS` con `resolution_status`, `maturity_bucket`.
- Rerun sobre datos sin cambios ⇒ **0 inserts, 0 revisions**.

### 5.5 Cross-check con BSR
- Donde un `eval_key` tiene contraparte en BSR con `resolved=true`, comparar `no_would_win` derivado de Gamma vs `bsr_no_would_win(BSR)`.
- **Mejora sobre proto-R2:** proto-R2 **aborta toda la corrida** ante un mismatch. E1 en cambio **cuarentena la fila** (no la escribe en `truth_records`, la registra en un log de conflictos `data/predictive/resolution_conflicts.jsonl`) y **continúa**. Un mismatch aislado no debe tirar el dataset entero; un patrón de mismatches dispara retorno a Opus (§10).

### 5.6 Cómo se evita la reduplicación futura
- **Regla de arquitectura (a documentar en `AGENTS.md` cuando se implemente):** ningún cohorte nuevo implementa su propio fetch Gamma. Si necesita outcomes, lee de `v_decision_truth` o llama a `_canonical_resolver`. proto-R2 queda como **el último** resolver por-cohorte; se congela.

---

## 6. P&L simulado vs P&L canónico

### 6.1 Qué ES `sim_unit_pnl`
Contrafactual de decisión por share: si la decisión hubiera comprado 1 share del lado evaluado al `market_prob_at_eval`, `win → (1 - price)`, `lose → -price`. Es una **métrica de calidad de decisión**, no dinero.

### 6.2 Qué NO es
- **No** sustituye P&L canónico R1/R2. P&L canónico sigue `none`.
- **No** autoriza BANKROLL (sigue $25 HOLD).
- **No** autoriza trading ni levanta gates.
- **No** alimenta cash accounting, wallet, ni reconciliación financiera.
- **No** asume fills, slippage, fees, ni tamaño real. Es 1 share teórico.

### 6.3 Aislamiento
- `sim_unit_pnl` vive en `truth_records` (carril learning) y **nunca** se escribe en artefactos de cash (`wallet_*`, `pnl_*`, `reconciled_executions.jsonl`).
- El benchmark E2 reporta `sim_unit_pnl` **siempre** con la etiqueta `simulated · non-canonical · not money`.

### 6.4 Conexión futura con R1 (carril separado, fuera de V1)
Cuando existan fills reales (`order_id` → CLOB `get_trades`, vía `reconcile_executions.py` → `reconciled_executions.jsonl`):
- Se podrá **joinear** `reconciled_executions` ↔ `truth_records` por `market_id` + `date_iso` para comparar `sim_unit_pnl` (contrafactual) vs P&L realizado (canónico R1).
- Ese join es **lectura cruzada**, no fusión: las dos tablas permanecen separadas. El P&L canónico siempre proviene de R1, nunca de `sim_unit_pnl`.
- **Esto es V2+, no E1.** Aquí solo se documenta el punto de sutura para que el schema no lo impida (de ahí `market_id` + `date_iso` siempre poblados).

---

## 7. Benchmark readiness (cómo E1 alimenta E2)

`v_benchmark_input` (§2.4) es la **única** entrada de E2. Provee, por fila madura:

- `model_prob` (candidato) y `market_prob_at_eval` (**baseline = mercado**).
- `resolution_outcome` ∈ {YES,NO} → `outcome01` ∈ {1,0} por `side`.
- `cohort_key` + columnas de ablation (`condition`, `city`, `days_ahead`, `edge_pct_at_eval`).

E2 computará, por `cohort_key` (y ablations):
- **WR** (`win rate` del lado evaluado).
- **Brier del candidato** vs **Brier del mercado** → `brier_advantage = brier_mkt - brier_our` (mismo cálculo que `_self_evaluation_engine._score_cohort`).
- **`calibration_gap`** = media de (`model_prob - outcome01`).
- **`sim_pnl`** agregado (no canónico).
- **Holdout temporal**: partición `evidence_frozen` (< cutoff `2026-05-29`) / `forward_holdout` (≥ cutoff). Promoción solo mira `forward_holdout`.
- **Ablations**: por `condition` / `city` / `days_ahead_bucket` / `edge_bucket`.
- **Veredicto por celda**: `{BEATS_MARKET, NO_EDGE, INSUFFICIENT_N}` (umbrales numéricos los fija E3).

E1 **no** computa nada de esto; solo garantiza que las columnas existen, están pobladas y son consistentes. La división es estricta: **E1 = libro; E2 = examen.**

---

## 8. Acceptance tests (lo que la implementación DEBE reproducir)

La implementación de E1 no se considera correcta hasta pasar:

1. **Proto-R2 exact/NO (oráculo de fidelidad).** Cargando el cohorte exact/NO por el resolver canónico, la celda `maturity_bucket='settled_mature'` debe reproducir **exactamente**:
   - `n = 17`
   - `WR_NO = 58.82%`
   - `sim_pnl = -1.6035`
   - `calibration_gap = +0.2476`
   Tolerancia: cero en n; ±0.0001 en métricas (redondeo). Si no reproduce ⇒ la consolidación perdió fidelidad ⇒ **bug, no avance**.

2. **`blocked_signals_resolutions` conteos básicos.** Total filas ingeribles = 113; subconjunto `resolved=true`; cross-check ejecutado sin abortar la corrida.

3. **self-eval `at_or_above`** (si los datos de `bot_signal_evaluations` at_or_above están disponibles en el entorno): `brier_advantage = -0.0939` reproducible desde `v_benchmark_input` filtrado a esa condición. Si los datos no están local, el test se marca `skip` con razón explícita (no se inventa).

4. **Idempotencia.** Rerun del builder ⇒ 0 inserts nuevos, 0 revisions. Cambio simulado de un outcome ⇒ 1 update + 1 fila en `truth_revisions`.

5. **No `trades.log`.** Test que asierta que el builder **no abre** `trades.log` (ni por path ni por glob).

6. **No ingestión accidental por glob.** El builder usa una **allowlist explícita** de archivos fuente (§3.10), nunca `glob("*.jsonl")`. Test que verifica que un JSONL extraño en `data/` no entra al dataset.

7. **No cambio de policy/trading.** Tests que asiertan: cero escrituras fuera de la DB de dataset y `data/predictive/`; cero imports de `bot.py`; cero llamadas a env vars de trading; `eligible_for_policy=false` propagado.

8. **Provenance poblado.** Toda fila tiene `data_provenance` con `source_file` + `sha256`.

---

## 9. Repo como fuente de verdad

### 9.1 Versionado (commiteable)
- `sql/003_decision_dataset.sql` (schema delta).
- `tools/decision_dataset_builder.py`, `tools/_canonical_resolver.py` (código).
- `tests/test_decision_dataset_builder.py` + **fixtures sanitizados pequeños** (sin wallet, sin order_id, sin PII).
- **Resumen sanitario commiteable**: `data/predictive/decision_dataset_summary.json` — agregados por `cohort_key` (n, WR, brier_advantage, sim_pnl, calibration_gap, maturity counts). **Sin filas crudas, sin precios por trader, sin identidades.** Es el "model card" del dataset que una sesión nueva lee para reconstruir contexto.
- Este spec.

### 9.2 Gitignored
- La DB poblada (`data/polymarket.db` / DB de dataset local).
- Export row-level completo del dataset.
- Runtime JSONL crudo con datos sensibles (`reconciled_executions.jsonl`, wallet, order_id).
- `data/predictive/resolution_conflicts.jsonl` (log de cuarentena).

### 9.3 Vive en Railway (nunca se commitea)
- SQLite de producción (`forecast_snapshots`, `market_snapshots`, `cycle_events`).
- JSONL runtime crudos (`exact_no_qt_match_evaluations_log_only.jsonl`, etc.).
- Acceso: **solo lectura** vía `tools/railway_safe.ps1 ssh cat ...`.

### 9.4 Cómo una sesión nueva reconstruye estado SIN memoria externa
1. Lee este spec (`docs/predictive/decision_dataset_spec.md`) → conoce el contrato.
2. Lee `data/predictive/decision_dataset_summary.json` → conoce el estado agregado del dataset (qué cohortes, qué n, qué veredictos).
3. Si necesita filas crudas: corre `decision_dataset_builder.py` que pulla snapshots read-only de Railway + lee los JSONL de la allowlist → reconstruye la DB local determinísticamente.
4. **No requiere Engram ni memoria externa**: el repo (spec + builder + summary + fixtures) es autosuficiente para regenerar el dataset.

### 9.5 Evitar copiar datos sensibles / runtime crudo
- El builder pulla de Railway **solo** las columnas necesarias (`forecast_snapshots` para enrich); no copia `payload_json` masivos a menos que se necesiten para replay.
- El summary commiteado es **agregado**: nunca expone precios por trader, wallets, ni order_ids.
- `.gitignore` debe cubrir `data/predictive/*.jsonl` y la DB; solo `decision_dataset_summary.json` y fixtures sanitizados entran al repo.

---

## 10. Handoff a implementación (Sonnet/Codex)

### 10.1 Archivos candidatos
| Archivo | Acción | Agente |
|---|---|---|
| `sql/003_decision_dataset.sql` | crear (delta aditivo §2.2) | Codex |
| `tools/_canonical_resolver.py` | crear (extraer de proto-R2 §5.3) | Codex |
| `tools/decision_dataset_builder.py` | crear (loaders + normalización + upsert) | Codex/Sonnet |
| `tests/test_decision_dataset_builder.py` | crear (acceptance §8) | Codex/Sonnet |
| `data/predictive/decision_dataset_summary.json` | output generado | (builder) |
| `data/predictive/` `.gitignore` entries | añadir | Codex |

### 10.2 Orden de implementación
1. `sql/003` delta + applier idempotente (espejo de `truth_pipeline_schema.py`).
2. `_canonical_resolver.py`: mover funciones de proto-R2; test bit-compatibilidad contra `exact_no_resolutions_log_only.jsonl` (§8.1) **antes** de seguir.
3. Loaders por fuente (§3) con reglas de identidad (§4): `bot_signal_evaluations` (esqueleto) → exact/NO → BSR (cross-check). Allowlist explícita, no glob.
4. Builder: normaliza → resuelve (pase único) → upsert `truth_records` con delta columns → emite `decision_dataset_summary.json`.
5. Vistas `v_decision_truth` extendida + `v_benchmark_input`.
6. Acceptance tests completos (§8).

### 10.3 Pruebas focales (gate de aceptación)
Las 8 de §8. El **gate duro** es §8.1 (reproducir proto-R2) y §8.4 (idempotencia). Sin esos dos, no hay merge.

### 10.4 Criterio de parada
E1 termina cuando: todos los cohortes de la allowlist están cargados; §8.1 reproduce proto-R2 exacto; rerun es idempotente; `decision_dataset_summary.json` commiteado; `v_benchmark_input` puebla filas maduras. **No** se persigue n adicional ni nuevas fuentes (price_filter, H3, R1 fills = diferidas).

### 10.5 Qué NO tocar
- `bot.py`, trading core, sizing, scheduler, city modes, guards, SL, whitelist.
- env vars, Railway writes, BANKROLL, Fase C, lift exact/NO.
- P&L canónico / cash / wallet / `reconciled_executions.jsonl`.
- `trades.log` (prohibido como fuente).
- Ingestión por glob (solo allowlist).

### 10.6 Cuándo volver a Opus
- **Antes de E2**: el protocolo del benchmark (umbrales de promoción, guarda de comparaciones múltiples, definición final de `cohort_key`) es decisión de Opus.
- Si el delta de schema necesita ser **no aditivo** (cambiar/borrar columna existente).
- Si el cross-check BSR↔Gamma revela **mismatch sistemático** (patrón, no caso aislado) → puede invalidar la fidelidad de outcomes.
- Si §8.1 **no logra** reproducir proto-R2 → significa que la consolidación pierde información; Opus revisa el diseño antes de forzar el merge.

---

## 11. Resumen ejecutivo

E1 convierte ~6 resolvers por-cohorte y N JSONL dispersos en **un solo libro de verdad**: la tabla `truth_records` (schema v2 ya existente) + un delta aditivo de 13 columnas que aportan lo único que falta para un benchmark predictor-vs-mercado — **el precio de mercado al eval, la prob del modelo, el lado, la madurez y la clave de cohorte**. Un pase único de resolución Gamma (T+7) reemplaza la lógica duplicada. El P&L es estrictamente simulado y aislado del carril canónico R1. La vista `v_benchmark_input` queda lista para que E2 corra el examen. Repo autosuficiente vía spec + builder + summary agregado; sin Engram. Ejecutable en **pocos días**, sin tocar nada live.

## 12. Riesgos (consolidados)

| Riesgo | Severidad | Mitigación |
|---|---|---|
| §8.1 no reproduce proto-R2 (pérdida de fidelidad) | **alta** | gate duro de merge; resolver canónico bit-compatible |
| Features (`our_prob`/`mkt_prob`) null en muchas filas filtradas | media | `v_benchmark_input` las excluye; n se reporta honesto |
| DB y fuentes solo en prod (SSH) | media | builder pulla read-only; repo guarda builder+summary, no DB |
| Mismatch BSR↔Gamma | media | cuarentena por fila (no abort), log de conflictos, escalada a Opus si patrón |
| Scope creep (price_filter/H3/R1 fills/trader path) | media | diferidos explícitos; allowlist; columnas trader no promovidas |
| Confundir sim_pnl con P&L canónico | **alta** | separación dura §6; etiquetado `non-canonical` siempre |
| Ingestión accidental por glob | baja | allowlist explícita + test §8.6 |

## 13. Confirmación de no cambios live

Este documento es **DESIGN-ONLY**. No modifica `bot.py`, trading core, env vars, Railway, DB de producción, BANKROLL ($25 HOLD), city modes, scheduler, guards, SL, ni Fase C. No autoriza BUY/SELL/SKIP. No levanta exact/NO. No usa `trades.log`. P&L canónico permanece `none`. No se usó Engram ni memoria externa.
