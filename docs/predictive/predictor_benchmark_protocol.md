# E2 — Predictor Benchmark Protocol — Design Spec

**Sprint:** Predictive Intelligence Sprint V1 · Entregable 2
**Modo del documento:** DESIGN-ONLY (este doc es el único artefacto producido; no hay código).
**Autor del diseño:** Opus · 2026-06-03
**Estado:** `E2_READY_FOR_CODE` **con precondición bloqueante nombrada** (`NEEDS_E1_ADJUSTMENT` — loader direccional + decision-time en la vista).
**Depende de:** E1 — Canonical Decision Dataset (`docs/predictive/decision_dataset_spec.md`, commits c3fef6b / f6170c0 / d6ed0b6).

---

## 0. Contrato de la sesión (no negociable)

Este spec **no** autoriza ni propone:

- live trading, BUY/SELL/SKIP, cambios en `bot.py`, trading core, sizing, scheduler, city modes, guards, SL, Fase C.
- subir BANKROLL (sigue **$25 HOLD**), lift de exact/NO.
- cambios de env vars, escrituras a Railway, escrituras a DB de producción.
- uso de `trades.log` como fuente.
- cambiar el dataset E1 (schema, builder, resolver) en esta sesión.
- **P&L canónico: sigue `none`.** Todo `sim_pnl` que E2 reporta es **simulado / contrafactual / non-canonical / not money**.

Separación dura heredada de E1, que atraviesa todo el documento:

> **Canónico para learning/eval** (lo que examina E2) **≠** **Canónico para P&L/cash** (R1/R2, no tocado aquí).

E2 es **read-only sobre el output de E1**. Abre la DB de E1 en modo `ro` (`PRAGMA query_only=ON`), nunca escribe en `truth_records`, nunca llama a Gamma, nunca re-resuelve outcomes.

---

## 1. Qué es E2 (y qué no)

E2 es **el examen del bot**, no otra herramienta de observabilidad. Responde una sola pregunta empresarial:

> **¿El predictor del bot bate al mercado en alguna cohorte defendible, con suficiente n, en holdout temporal, y con `sim_pnl` positivo?**

Diferencia con un dashboard: un dashboard *describe* el estado. E2 *adjudica* — produce un veredicto por celda (`BEATS_MARKET` / `NO_EDGE` / `INSUFFICIENT_N` / `NEEDS_MORE_DATA` / `KILL_MODEL_PATH` / `CANDIDATE_FOR_CANARY_REVIEW`) bajo reglas pre-registradas, con guardas anti-falso-positivo, y escala (o mata) un path de alpha.

E2 **no** computa outcomes (los hereda de E1), **no** mueve dinero, **no** autoriza nada live. Su salida es un advisory non-canonical.

---

## 2. Veredicto estratégico

### 2.1 Headline

**`E2_READY_FOR_CODE`** — el protocolo está completo y es codeable hoy de forma aditiva y segura. **Con una precondición bloqueante nombrada** para que el examen sea *significativo*:

### 2.2 Precondición bloqueante: `NEEDS_E1_ADJUSTMENT` (cobertura de datos)

E2 corre hoy, pero solo sobre **17 filas `exact|NO`** (`v_benchmark_input`). Eso es porque:

1. **El loader de `bot_signal_evaluations` en E1 es un stub.** En `tools/decision_dataset_builder.py::build_dataset`, solo se ingiere `exact_no_resolutions`; el parámetro `bot_signal_evaluations` se registra en `source_state` pero **nunca se normaliza ni se escribe** (no existe `normalize_bot_signal_evaluation`, ni un pase del resolver canónico sobre BSE). Resultado: las cohortes direccionales (`at_or_above`/`at_or_below`), **donde vive la señal real** (`_self_evaluation_engine` ya midió `brier_advantage = -0.0939` en `at_or_above`), tienen **0 filas** en el dataset.
2. **`v_benchmark_input` no expone el timestamp de decisión** (`snapshot_ts_utc`). Sin él, el holdout temporal (§5) no es definible desde la vista; hace falta o un join read-only a `truth_records`, o una extensión aditiva de la vista.

Ambos ítems son **handoff a un futuro patch de E1** (§8), no se ejecutan en esta sesión. Hasta cerrarlos, E2 clasifica:
- `exact|NO`: `INSUFFICIENT_N` (n=17 < N_REVIEW=20) y, aunque tuviera n, **`NON_PROMOTABLE_BY_POLICY`** por el firewall exact/NO (§6.6).
- direccional: **sin datos** (n=0).

### 2.3 Lectura preliminar (NO es el veredicto formal)

Con la evidencia que **ya existe** fuera del dataset E1:
- `at_or_above` direccional: `brier_advantage = -0.0939` (modelo **peor** que mercado) — `_self_evaluation_engine`.
- `exact|NO` maduro: `WR_NO = 58.82%` pero `sim_pnl = -1.6035` y `calibration_gap = +0.2476` (gana el lado NO más de la mitad de las veces, pero **pierde plata simulada** comprando NO caro y está sobre-confiado). Ya es `SHADOW_ONLY` / `REVIEW_BLOCK_LIVE` por decisión Opus vigente (2026-05-26 / 2026-06-01).

La hipótesis líder es **`KILL_CURRENT_MODEL_PATH_PRELIMINARY`** para el path de alpha "forecast-predictor". **No se declara formalmente** hasta que (a) E1 ingiera el esqueleto direccional y (b) `forward_holdout` alcance n. Es decir: el kill está **flagged como preliminar, no adjudicado**. E2 existe precisamente para convertir esa sospecha en veredicto con n y holdout, o para falsarla si alguna cohorte direccional sorprende.

### 2.4 Por qué `E2_READY_FOR_CODE` y no `WAIT_FOR_JUN9` ni `KILL_..._PRELIMINARY` como headline

- No `WAIT_FOR_JUN9`: el cierre de Phase 2 (2026-06-09) es una decisión sobre **trades reales** con sus propios criterios (n≥25, WR≥45%, PnL≥+$5…). E2 es **offline / non-canonical** y mide otra cosa (calibración predictor-vs-mercado). No comparten carril; E2 no debe esperar a Jun 9 para existir, y Jun 9 no debe esperar a E2 (§8.5).
- No `KILL_..._PRELIMINARY` como headline: matar el model path **antes** de instrumentar el dataset direccional sería matar a ciegas — exactamente el error que E1+E2 existen para evitar. Primero el examen, después la sentencia.

---

## 3. Qué consume E2 (entradas)

| Entrada | Rol | Cómo se abre | Obligatoria |
|---|---|---|---|
| `v_benchmark_input` (vista en `data/predictive/decision_dataset.db`) | **única fuente row-level** | SQLite `mode=ro`, `query_only=ON` | **sí** |
| `truth_records.snapshot_ts_utc` (join read-only por `decision_id`) | **decision-time** para holdout (mientras la vista no lo exponga) | mismo handle `ro` | sí (hasta §8 item B) |
| `data/predictive/decision_dataset_summary.json` | provenance + cross-check de conteos agregados (no se re-derivan outcomes) | lectura de archivo | sí (sanity) |

**E2 NO consume:**
- JSONL crudos (los outcomes ya están resueltos por el resolver canónico de E1).
- **Gamma API** — llamarla re-duplicaría el resolver y viola la regla de arquitectura E1 §5.6 (ningún consumidor nuevo hace su propio fetch Gamma). E2 hereda outcomes, no los produce.
- `bot.py`, `trades.log`, DB de producción, Railway, env vars de trading.
- Cualquier fila **no** `settled_mature` (la vista ya las filtra; E2 además lo asierta, §7).

**Dominio de probabilidad:** `v_benchmark_input.model_prob` y `market_prob_at_eval` ya están normalizados a `[0,1]` por el builder de E1 (exact/NO vienen 0-1; BSE vendría `/100` en su loader). E2 **no** re-normaliza; consume `[0,1]` y lo asierta en un test de cordura (`0 ≤ p ≤ 1`).

---

## 4. Definición de cohortes

### 4.1 Clave heredada de E1

Se usa `cohort_key` de E1 **tal cual**, sin re-derivarlo:
```
cohort_key = condition | side | days_ahead_bucket | edge_bucket
days_ahead_bucket ∈ {0-1, 2-3, 4-7, 8+, unknown}
edge_bucket       ∈ {<5%, 5-15%, 15-30%, 30%+, unknown}
```

**Realidad actual:** para `exact/NO`, `days_ahead` es `null` en el log de resoluciones ⇒ `days_ahead_bucket = "unknown"` en las 4 cohortes; hoy solo difieren por `edge_bucket`. Es esperado y se documenta; no se fuerza.

### 4.2 ¿Es suficiente el `cohort_key` actual? — Jerarquía de roll-up (la parte que E2 añade)

El leaf de 4 tuplas **fragmenta n** a escala chica (17 filas → 4 celdas de 3-6). E2 **no promueve sobre el leaf**. Define una jerarquía con una **superficie de promoción** estrecha:

| Nivel | Definición | Rol | ¿Promocionable? |
|---|---|---|---|
| **L0** (root) | todas las filas pooled | headline predictor-vs-mercado, **máxima n**, ancla anti-cherry-pick | solo **confirma signo** |
| **L1** | `condition | side` (p.ej. `exact|NO`, `at_or_above|YES`) | **superficie de promoción** (familia de modelo defendible) | **sí** (única) |
| **L2** | `cohort_key` completo (leaf) | ablation | **no** — solo puede **DEMOTE** |
| Ablations | por `city`, por `days_ahead_bucket`, por `edge_bucket` | diagnóstico on-demand | **no** — solo DEMOTE |

**Reglas duras de cohorte:**
- La **promoción se decide en L1**, con **confirmación de signo en L0** (el pooled no puede contradecir). Esto acota el número de comparaciones (K ≤ ~8 celdas L1) y mata el cherry-picking de leaf/edge_bucket.
- **Leaf y ablations solo pueden DEMOTE** (marcar riesgo / restar), **nunca PROMOTE**. Elegir "la mejor rodaja a posteriori" es estructuralmente imposible.
- **`city` nunca entra a `cohort_key`** (fragmentación; coherente con E1 §4.6). Entra solo como ablation de DEMOTION (una ciudad arrastrando una celda) o cuando E3 pida explícitamente un experimento city-scoped. Nunca para fabricar una cohorte ganadora.
- **`edge_bucket` no es superficie de promoción.** Un `edge_bucket` que "bate al mercado" aislado es el caso de cherry-pick más peligroso (la `15-30%` exact/NO da `brier_advantage=-0.253` y la `30%+` da `+0.0315` con n=3 — ruido). Solo informa, nunca promueve.

---

## 5. Métricas, holdout y umbrales

### 5.1 Métricas por celda × partición

Para cada celda (L0, L1, y ablations) y cada partición (`evidence_frozen`, `forward_holdout`):

| Métrica | Fórmula | Notas |
|---|---|---|
| `n` | filas | conteo |
| `WR` | `mean(outcome01)` | win-rate del lado evaluado (`outcome01 = 1[side == resolution_outcome]`) |
| `brier_model` | `mean((model_prob - outcome01)^2)` | menor = mejor |
| `brier_market` | `mean((market_prob_at_eval - outcome01)^2)` | baseline |
| **`brier_advantage`** | **`brier_market - brier_model`** | **+ ⇒ modelo bate al mercado.** Mismo signo y cálculo que `_self_evaluation_engine._score_cohort` (reproducibilidad, §7.1) |
| `calibration_gap` | `mean(model_prob - outcome01)` | signado; + ⇒ sobre-predice el lado |
| `sim_unit_pnl_total` / `_mean` | suma / media de `sim_unit_pnl` | **non-canonical, not money** |
| `mean_model_prob`, `mean_market_prob`, `observed_rate` | diagnóstico de calibración | — |
| `brier_advantage_ci` | bootstrap percentil (B=10000, seed fijo=`2026`) | **lower / upper bound** para significancia |

### 5.2 Baselines

- **Primario = el MERCADO** (`market_prob_at_eval`). `brier_advantage` vs mercado es el titular. Siempre.
- **Secundario (diagnóstico, NO gating):** *base-rate / always-NO constant* — Brier de predecir la tasa base empírica. Es el **piso de cordura**: un modelo que no bate la tasa base está muerto independientemente del mercado.
- **Diferidos a E3 (no en E2 V1):** *traders* (path de alpha distinto; E1 §2.3 mantiene columnas trader fuera del dataset) y *climatología* (requiere serie `observed_high_c` que `v_benchmark_input` no expone). Documentados como deferidos.

### 5.3 Holdout temporal (anti-lookahead)

- **Cutoff pre-registrado:** se **reutiliza** `SELF_EVAL_H1_PREREG_CUTOFF_UTC = 2026-05-29T00:00:00Z`, aliasado en E2 como `E2_PREREG_CUTOFF_UTC`.
  - Por qué reutilizar y **no** definir uno nuevo: ya está pre-registrado; reutilizarlo hace que el número direccional del self-eval sea **reproducible dentro de E2** (test §7.1); un cutoff más tardío tiraría evidencia forward acumulada; uno más temprano no está pre-registrado.
- **Partición** (idéntica a `_self_evaluation_engine._partition`):
  - `evidence_frozen` = decision-time `<` cutoff (o ts no parseable → frozen).
  - `forward_holdout` = decision-time `≥` cutoff.
- **La promoción mira SOLO `forward_holdout`.** `evidence_frozen` se usa únicamente para (a) **sign-consistency** y (b) generación de hipótesis. Nunca para el claim de promoción. Esto mata "elegí la cohorte que se veía bien en la historia".
- **Definición de "decision-time" (source-aware, para no introducir lookahead):**
  - **BSE direccional:** `snapshot_ts_utc` = ts del eval (verdadero decision-time). Idéntico al self-eval ⇒ reproducibilidad.
  - **exact/NO:** el ts real del eval vive en el upstream `exact_no_qt_match_evaluations_log_only.jsonl`, que E1 **no** ingirió (ingirió las *resoluciones*). En el dataset, `snapshot_ts_utc` de exact/NO = `resolved_at` (tiempo de **resolución**, no de decisión). Usarlo particionaría por fecha de settle ⇒ **incorrecto**. **Regla:** para exact/NO se particiona por **`date_iso`** (fecha del evento) como proxy conservador del decision-time (la predicción para `date_iso` se hizo necesariamente ≤ `date_iso`). Se documenta el proxy y su límite. Hacer riguroso el holdout exact/NO requiere que E1 cargue el `ts_utc` del eval upstream (futuro, §8) — **no** es requisito V1 porque exact/NO ya es non-promotable.

### 5.4 Umbrales y veredictos (pre-registrados)

Constantes pre-registradas en este doc **antes** de mirar resultados forward:
```
N_REVIEW          = 20     # celda se vuelve "revisable" (alineado con self-eval HOLDOUT_READY)
N_PROMOTE_FLOOR   = 30     # mínimo para siquiera considerar CANDIDATE
MARGIN            = 0.01   # effect-size mínimo de brier_advantage (evita "edge" por ruido)
SIMPNL_FLOOR      = 0.0    # sim_unit_pnl_mean forward debe ser > 0
FDR_Q             = 0.10   # Benjamini-Hochberg sobre las celdas L1 testeadas
BOOTSTRAP_B       = 10000  # seed fijo 2026 → determinismo
```

Veredicto por celda L0/L1 (evaluado en `forward_holdout`):

| Veredicto | Condición |
|---|---|
| `INSUFFICIENT_N` | `n < N_REVIEW` |
| `NEEDS_MORE_DATA` | `N_REVIEW ≤ n < N_PROMOTE_FLOOR` (revisable, no alcanza para claim) — emite trigger+fecha |
| `NO_EDGE` | `n ≥ N_REVIEW` ∧ `brier_advantage ≤ 0` (no bate al mercado) |
| `KILL_MODEL_PATH` | `n ≥ N_PROMOTE_FLOOR` ∧ `brier_advantage_ci.upper < 0` (confiadamente **peor** que el mercado) |
| `BEATS_MARKET` | `n ≥ N_PROMOTE_FLOOR` ∧ `brier_advantage > MARGIN` ∧ `brier_advantage_ci.lower > 0` ∧ `sim_unit_pnl_mean > SIMPNL_FLOOR` ∧ **signo-consistente con `evidence_frozen`** |
| `CANDIDATE_FOR_CANARY_REVIEW` | `BEATS_MARKET` en L1 ∧ **L0 no contradice el signo** ∧ pasa significancia **corregida por multiplicidad** (FDR) ∧ **no** está bajo firewall (§6.6) |

- `CANDIDATE_FOR_CANARY_REVIEW` **no autoriza un canary.** Nomina la celda a revisión Opus con su packet de evidencia (§6.5). El canary es una decisión separada, futura y explícitamente autorizada.
- **Global `KILL_CURRENT_MODEL_PATH`:** si **toda** celda L1 con `n ≥ N_REVIEW` es `NO_EDGE` o `KILL_MODEL_PATH` y **ninguna** llega a `CANDIDATE` ⇒ el predictor-forecast no bate al mercado en ningún lado defendible ⇒ escala `KILL_CURRENT_MODEL_PATH` / pivot de fuente de alpha.

**Sobre los datos de hoy:** exact/NO total maduro n=17 `< N_REVIEW` ⇒ `INSUFFICIENT_N`; direccional n=0 ⇒ sin celda. Output honesto, sin edge fabricado.

### 5.5 Multiplicidad (anti-falso-positivo)

Probar muchas celdas infla falsos positivos. Guardas, en capas:
1. **Superficie estrecha:** promoción solo en L1 (K ≤ ~8). Reduce K en origen.
2. **Corrección FDR Benjamini-Hochberg (q=0.10)** sobre el test `brier_advantage_forward > 0` de las celdas L1 efectivamente testeadas (las que pasan `N_REVIEW`). Se reportan p-valores crudos **y** corregidos. (Bonferroni como variante conservadora si K es muy chico).
3. **Effect-size floor (`MARGIN`) + CI lower-bound > 0** (bootstrap percentil determinista): significancia **estadística y práctica**, no solo p<algo.
4. **Sign-consistency gate:** `forward` y `frozen` deben coincidir en signo para promover; una celda que **flipea signo es ruido**.
5. **No promoción en leaf/ablation:** solo DEMOTE.
6. **Firewall exact/NO (§6.6).**

---

## 6. Salidas de E2

### 6.1 `data/predictive/benchmark_summary.json` (commiteable, **solo agregado**)

Estructura:
```jsonc
{
  "schema_version": "predictor_benchmark_summary_v1",
  "generated_at_utc": "...",
  "prereg_cutoff_utc": "2026-05-29T00:00:00+00:00",
  "thresholds": { "N_REVIEW": 20, "N_PROMOTE_FLOOR": 30, "MARGIN": 0.01, "FDR_Q": 0.10, "bootstrap_b": 10000, "seed": 2026 },
  "baseline": { "primary": "market", "secondary_diagnostic": "base_rate", "deferred": ["traders", "climatology"] },
  "dataset_provenance": { "summary_sha256": "...", "decision_dataset_rows": 62, "benchmark_input_rows": 17 },
  "coverage_warnings": [
    "directional_bse_rows_absent: bot_signal_evaluations loader is a stub in E1 (no directional cohorts).",
    "exact_no_holdout_uses_date_iso_proxy: eval ts not ingested."
  ],
  "cells": [ { "level": "L1", "cohort": "exact|NO", "partition": "forward_holdout",
              "n": 0, "WR": null, "brier_model": null, "brier_market": null,
              "brier_advantage": null, "brier_advantage_ci": [null, null],
              "calibration_gap": null, "sim_unit_pnl_mean": null,
              "p_raw": null, "p_fdr": null, "verdict": "INSUFFICIENT_N" } ],
  "top_candidates": [],
  "killed_cohorts": [],
  "global_verdict": "INSUFFICIENT_N_PENDING_E1_DIRECTIONAL_LOADER",
  "disclaimer": "sim_pnl simulated_non_canonical_not_money. eligible_for_policy=false. market_truth_canonical=false. No trading authorization.",
  "eligible_for_policy": false
}
```

- **Sin filas crudas.** Sin `eval_key`/`decision_id` listados, sin precios por trader, sin wallets, sin order_ids, sin identidades.
- `sim_pnl` **siempre** etiquetado `simulated · non-canonical · not money`.
- `top_candidates` = celdas `CANDIDATE_FOR_CANARY_REVIEW` con su packet. `killed_cohorts` = celdas `KILL_MODEL_PATH`.

### 6.2 `docs/predictive/benchmark_summary.md` (opcional, render humano, **no autoritativo**)

Tabla por celda + veredictos. Derivado del JSON; el JSON manda.

### 6.3 Packet de candidato (cuando exista `CANDIDATE_FOR_CANARY_REVIEW`)

Bloque dentro del JSON: definición de celda L1, n forward, `brier_advantage` + CI, `sim_unit_pnl_mean`, evidencia de sign-consistency frozen↔forward, p-FDR. Es el insumo para revisión Opus, **no** una autorización.

### 6.4 Qué NO genera E2

No live trading, no BANKROLL, no Fase C, no env vars, no city modes, no BUY/SELL/SKIP, no P&L canónico, no `trades.log`, no escritura en el dataset E1, no filas crudas en repo, no llamadas a Gamma.

### 6.5 Firewall exact/NO (regla dura)

Las celdas `exact|NO` se **evalúan y reportan** descriptivamente (incluido un eventual `brier_advantage>0` aislado), pero su campo `verdict` se **fuerza a `NON_PROMOTABLE_BY_POLICY (exact_no_firewall)`** y **no pueden** convertirse en `CANDIDATE_FOR_CANARY_REVIEW`. Honra las decisiones Opus vigentes (`SHADOW_ONLY` global 2026-05-26, `KEEP_EXACT_NO_BLOCK` 2026-06-01). E2 **no reabre exact/NO**; solo lo haría un criterio futuro, explícito y separado, no este benchmark.

---

## 7. Acceptance tests (lo que la implementación DEBE cumplir)

1. **Fidelidad direccional (oráculo).** Filtrando `v_benchmark_input` a `condition=at_or_above ∧ side=YES ∧ partition=evidence_frozen` con `E2_PREREG_CUTOFF_UTC`, E2 reproduce `brier_advantage = -0.0939` del `_self_evaluation_engine`. **Si BSE no está ingerido** (hoy), el test se marca `skip` con razón explícita (`directional_rows_absent`) — no se inventa.
2. **Firewall + no-promoción exact/NO.** Toda celda `exact|NO` termina en `{INSUFFICIENT_N, NO_EDGE, NON_PROMOTABLE_BY_POLICY}` y **nunca** en `CANDIDATE`. Sobre datos de hoy: `INSUFFICIENT_N` (n=17<20) y assert `verdict != CANDIDATE_FOR_CANARY_REVIEW`.
3. **No ingiere filas inmaduras.** Con una DB que tenga filas `resolved_fresh`/`pending`, ninguna entra a ninguna celda (E2 solo lee `v_benchmark_input`, que ya filtra `settled_mature`; además se asierta el filtro).
4. **No usa `resolved_fresh` para promoción.** Assert: ninguna métrica de promoción se computa sobre `maturity_bucket != 'settled_mature'`.
5. **Aislamiento.** El módulo E2 no importa `bot.py`, no usa `glob`, no usa `urllib`/red (no llama a Gamma), abre la DB `mode=ro`/`query_only=ON`, no escribe en `truth_records`. Tests de import-introspection + spy de `open`.
6. **Output solo agregado.** `benchmark_summary.json` no contiene claves row-level (no lista de `eval_key`/`decision_id`, no precios por trader). Test de sustring + schema.
7. **`sim_pnl` etiquetado non-canonical; `eligible_for_policy=false`.** Assert en el JSON.
8. **Determinismo.** Mismo DB ⇒ mismos veredictos y mismos CI (bootstrap con seed fijo, FDR determinista).
9. **No-lookahead.** Ninguna celda `forward_holdout` incluye una fila con decision-time `<` cutoff (por la regla source-aware §5.3).
10. **Degradación honesta.** Con solo 17 filas exact/NO, E2 devuelve `INSUFFICIENT_N` + `global_verdict=INSUFFICIENT_N_PENDING_E1_DIRECTIONAL_LOADER` sin crash y sin edge fabricado.

---

## 8. Handoff a implementación (Codex / Sonnet)

### 8.1 Orden de implementación

1. **(Precondición A — E1 patch) Loader direccional `bot_signal_evaluations`** en `decision_dataset_builder.py`: `normalize_bot_signal_evaluation` (`our_prob/100→model_prob`, `mkt_prob/100→market_prob_at_eval`, conserva `side` explícito YES/NO; sin side mantiene el fallback histórico YES, `days_ahead`, `bot_edge_pct_at_signal→edge_pct_at_eval`) + **pase del resolver canónico** (`_canonical_resolver.fetch_outcome` → `resolution_outcome`/`maturity_bucket`/`sim_unit_pnl`) sobre BSE. Allowlist explícita, sin glob. Excluir Seoul (paridad con self-eval). Acceptance: reproduce `brier_advantage=-0.0939` al pasar por `v_benchmark_input`.
2. **(Precondición B — E1 patch, aditivo)** Exponer **decision-time** para el holdout: o bien añadir `snapshot_ts_utc` (y opcional `date_iso`) a `v_benchmark_input`, o documentar el join read-only `truth_records.snapshot_ts_utc` por `decision_id`. Recomendado: extensión aditiva de la vista (contrato limpio).
3. **(E2)** `tools/predictor_benchmark.py` read-only: carga `v_benchmark_input` (+ decision-time) → roll-up L0/L1/ablations → métricas §5.1 → holdout §5.3 → veredictos §5.4 → multiplicidad §5.5 → `benchmark_summary.json` §6.
4. **(E2)** `tests/test_predictor_benchmark.py`: los 10 de §7. Gate duro = §7.1 (fidelidad) + §7.2 (firewall) + §7.9 (no-lookahead).
5. **(E2)** Render `benchmark_summary.md` (opcional).

### 8.2 Archivos candidatos

| Archivo | Acción | Agente |
|---|---|---|
| `tools/decision_dataset_builder.py` | **patch E1** (loader BSE + resolver pass) | Codex |
| `sql/003_decision_dataset.sql` | **patch E1** aditivo (decision-time en `v_benchmark_input`) | Codex |
| `tools/predictor_benchmark.py` | crear (E2) | Codex/Sonnet |
| `tests/test_predictor_benchmark.py` | crear (§7) | Codex/Sonnet |
| `data/predictive/benchmark_summary.json` | output generado | (E2) |
| `docs/predictive/benchmark_summary.md` | output opcional | (E2) |

### 8.3 Qué NO tocar

`bot.py`, trading core, sizing, scheduler, city modes, guards, SL, whitelist; env vars, Railway writes, BANKROLL, Fase C, lift exact/NO; P&L canónico/cash/wallet; `trades.log`; Gamma desde E2; ingestión por glob; el contrato de outcomes de E1 (E2 hereda, no re-resuelve).

### 8.4 Cuándo volver a Opus

- Cualquier celda llega a `CANDIDATE_FOR_CANARY_REVIEW` → Opus revisa el packet antes de cualquier paso live.
- `global_verdict = KILL_CURRENT_MODEL_PATH` → Opus decide pivot de fuente de alpha.
- El loader direccional revela que `brier_advantage=-0.0939` **no** se reproduce → bug de consolidación (igual que E1 §8.1), Opus revisa antes de seguir.
- Se propone tocar el firewall exact/NO o introducir un cutoff distinto al pre-registrado.

### 8.5 Conexión con el cierre Phase 2 (2026-06-09)

E2 y Phase 2 son **carriles distintos**:
- **Phase 2 (06-09):** decisión sobre **trades reales** (criterios n≥25, WR≥45%, PnL≥+$5, drawdown ≥ −$6, etc.). **Canónico** para la decisión live.
- **E2:** auditoría **offline / non-canonical** de calibración predictor-vs-mercado (sim_pnl).

Handshake: E2 produce un **advisory** que puede **adjuntarse** a la revisión del 06-09 como evidencia de soporte ("el predictor [no] bate al mercado en holdout"). **Si E2 y Phase 2 discrepan, los criterios de trades reales de Phase 2 mandan** para la decisión live (canonicidad). E2 puede, de forma independiente, justificar `KILL_MODEL_PATH` / pivot aunque Phase 2 pase, y viceversa. E2 **no** es el gate de Phase 2 ni Phase 2 el gate de E2.

### 8.6 Desbloqueo de decisión

- **Si alguna cohorte → `CANDIDATE_FOR_CANARY_REVIEW`:** packet a Opus; canary es decisión separada futura. exact/NO excluido por firewall.
- **Si ninguna cohorte bate al mercado:** `KILL_CURRENT_MODEL_PATH` / pivot de fuente de alpha (p.ej. hacia leaderboard/trader-following, que es **otro** modelo, fuera de E1/E2, el pivot natural).
- **Si falta n:** trigger concreto = `n_forward_holdout ≥ N_PROMOTE_FLOOR (30)` por celda L1; fecha = re-run tras cerrar Precondición A (loader BSE) y acumular holdout. Hasta entonces, `NEEDS_MORE_DATA`.
- **exact/NO:** queda **`NON_PROMOTABLE`**; E2 no lo reabre.

---

## 9. Confirmaciones de no cambios live

Este documento es **DESIGN-ONLY**. No modifica `bot.py`, trading core, env vars, Railway, DB de producción, scheduler, guards, SL, city modes, ni el dataset E1. Y deja constancia:

- **BANKROLL sigue $25** (HOLD).
- **Fase C no autorizada.**
- **No live trading changes.**
- **No env vars.**
- **No city modes.**
- **No BUY/SELL/SKIP.**
- **P&L canónico sigue `none`** — todo `sim_pnl` de E2 es `simulated · non-canonical · not money`.
- No se levanta exact/NO. No se usa `trades.log`. No se usó Engram ni memoria externa.

---

## 10. Resumen ejecutivo

E2 es el **examen** del predictor: lee la única vista madura de E1 (`v_benchmark_input`), agrega en una jerarquía L0/L1 con superficie de promoción estrecha, mide `brier_advantage` vs mercado (más `WR`, `calibration_gap`, `sim_pnl` non-canonical), parte por holdout temporal pre-registrado (`2026-05-29`), y adjudica veredictos con guardas anti-falso-positivo (FDR + CI bootstrap + sign-consistency + no-promoción-de-leaf + firewall exact/NO). **El protocolo está listo para código (`E2_READY_FOR_CODE`)**, pero su primer examen *significativo* está **gateado por dos parches aditivos de E1**: el loader direccional `bot_signal_evaluations` (hoy un stub ⇒ 0 filas direccionales) y la exposición del decision-time en la vista. Sobre los datos de hoy (17 filas exact/NO, ya non-promotable), E2 devuelve `INSUFFICIENT_N`. La lectura **preliminar** —no adjudicada— apunta a `KILL_CURRENT_MODEL_PATH` para el path forecast-predictor; E2 existe para convertir esa sospecha en veredicto con n y holdout, o falsarla.
