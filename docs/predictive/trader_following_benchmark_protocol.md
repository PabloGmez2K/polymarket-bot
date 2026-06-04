# E3 — Trader-Following Benchmark Protocol — Design Spec

**Sprint:** Predictive Intelligence Sprint V1 · Pivot de fuente de alpha (Camino A)
**Modo del documento:** DESIGN-ONLY (este doc es el único artefacto producido; no hay código).
**Autor del diseño:** Opus · 2026-06-03
**Estado:** `NEEDS_MORE_READONLY_INVENTORY` — protocolo completo y codeable, **bloqueado por una precondición read-only nombrada y barata** (§2.2: censo full-BSR de Railway). Flippea a `TRADER_BENCHMARK_READY_FOR_CODE` si el censo limpia los pisos de diversidad/holdout (§2.4).
**Depende de:** decisión Opus `ALPHA_SOURCE_PIVOT_STRATEGY_V1` (Sesión 420, `START_ALPHA_PIVOT_SPRINT`, Camino A) · E1 (`docs/predictive/decision_dataset_spec.md`) · E2 (`docs/predictive/predictor_benchmark_protocol.md`).

---

## 0. Contrato de la sesión (no negociable)

Este spec **no** autoriza ni propone:

- live trading, BUY/SELL/SKIP, cambios en `bot.py`, trading core, sizing, scheduler, city modes, whitelist, guards, SL, Fase C.
- subir BANKROLL (sigue **$25 HOLD**), lift de exact/NO.
- cambios de env vars, escrituras a Railway, escrituras a DB de producción.
- uso de `trades.log`, wallets, `order_id`s ni `reconciled_executions.jsonl` como fuente.
- crear dashboard, ni un sistema grande: un (1) tool read-only + un (1) summary agregado + tests, en la forma de E2.
- usar `sim_pnl` como P&L canónico. **P&L canónico sigue `none`.** Todo `sim_pnl`/`sim_unit_pnl` que E3 reporta es **simulado · contrafactual · non-canonical · not money**.
- No se usó Engram ni memoria externa en esta sesión.

Separación dura heredada de E1/E2, que atraviesa todo el documento:

> **Canónico para learning/eval** (lo que examina E3) **≠** **Canónico para P&L/cash** (R1/R2, no tocado).

E3 es **read-only sobre BSR** (`blocked_signals_resolutions.jsonl`). **Hereda los outcomes de BSR** (`resolved`/`close_price`/`win_for_trader`), **nunca** llama a Gamma, nunca re-resuelve — exactamente como E2 hereda de E1.

---

## 1. Qué es E3 (y qué no)

El predictor-forecast tiene evidencia congelada negativa y `forward_holdout n=0` (E2: L0 pooled `n=41 brier_advantage=-0.0657`; `at_or_above|YES n=20 brier_advantage=-0.1017`; exact/NO non-promotable). La tesis del pivot: **si el bot no predice el clima mejor que el mercado, quizá la fuente de alpha no es predecir, sino identificar selecciones de traders que ya baten al mercado.**

E3 es **el examen de esa tesis**, no un seguidor de traders ni un dashboard. Responde una sola pregunta empresarial, falsable:

> **¿Las selecciones de traders de calidad baten al mercado al precio medio de entrada (`avg_price_entered`), con suficiente n, suficiente diversidad de traders, en holdout fuera de muestra, con guardas anti-overfit, y `sim_pnl` positivo?**

E3 **adjudica** (produce un veredicto por celda bajo reglas pre-registradas), no describe. E3 **no** mueve dinero, **no** sigue a nadie en vivo, **no** autoriza canary ni exact/NO. Su salida es un advisory non-canonical.

---

## 2. Veredicto estratégico

### 2.1 Headline

**`NEEDS_MORE_READONLY_INVENTORY`.** El protocolo (§3-§10) está **completo y es codeable hoy** de forma aditiva y segura. Pero **no es responsable** entregar `READY_FOR_CODE` a Codex con la realidad de datos que muestra el BSR **local**, y existe **una sola precondición barata, read-only, falsable antes del 09-jun** que decide si el benchmark puede siquiera alcanzar sus pisos de diversidad. Mismo patrón que E2 (`READY_FOR_CODE` con precondición bloqueante nombrada), pero aquí la precondición precede al código.

### 2.2 Precondición bloqueante: censo full-BSR de Railway (read-only)

El BSR **local** (`data/runtime_import_derived/blocked_signals_resolutions.jsonl`) es un **subconjunto stale**: **113 filas**, todas `resolved=true`, pero con dos propiedades que, de tomarse como universo, harían el benchmark un cherry-pick:

1. **Concentración de traders letal.** Solo **6 traders distintos**. Dos wallets — `Thrifty-Original` (n=55, WR 80.0%) y `Entire-Hood` (n=30, WR 93.3%) — son el **75% de la muestra**. Cualquier "alfa" agregada es, literalmente, *"a 2 traders les fue bien en abril"*. Es el caso de cherry-pick por trader individual que la tarea 7 pide evitar.
2. **Cero spread temporal forward.** Todas las filas son `date` **2026-04-08 → 2026-04-19** (`checked_at` 04-13 → 04-21). Contra el cutoff pre-registrado `2026-05-29` (heredado de E2), **`forward_holdout` temporal n=0** — exactamente el muro que ya paralizó al predictor. Un holdout temporal "fresco" **no está disponible rápido**.
3. **El universo real vive en Railway.** Las sesiones S405/S406 reportaron BSR de **409–754 filas** en producción (43 ciudades). El conteo real de **traders distintos** y el **spread temporal** del BSR completo son **desconocidos desde el repo**. La potencia del benchmark y todas sus guardas anti-overfit dependen de esos dos números.

**La precondición** (handoff §11, paso 0): un **censo agregado, read-only**, vía `tools/railway_safe.ps1 ssh cat data/blocked_signals_resolutions.jsonl` (lectura, no escritura — coherente con E1 §9.3 y `railway_ssh_access`), que reporte **solo**: n total resuelto, **# traders distintos**, n por trader (sin identidades sensibles en el output committeable, ver §9), rango de `date`/`checked_at`, mezcla `condition`/`side`/`has_consensus`. **No** filas crudas, **no** wallets al repo.

### 2.3 Lectura preliminar (NO es el veredicto formal)

Con la evidencia que **ya existe** en el BSR local (n=113, todas frozen, 6 traders) — métrica núcleo `sim_unit_pnl = win_for_trader − avg_price_entered` (§5.1):

| Cohorte | n | n_traders | WR | mean price | mean sim_pnl | nota |
|---|---|---|---|---|---|---|
| L0 pooled | 113 | 6 | 0.823 | 0.6385 | **+0.1846** | dominado por 2 wallets |
| `wr≥80` | 58 | — | 0.914 | 0.685 | +0.2284 | casi circular (los 2 wallets) |
| `wr 70-80` | 17 | — | 0.882 | 0.623 | +0.2592 | |
| `wr 60-70` | 24 | — | 0.708 | 0.664 | +0.0438 | |
| `wr 50-60` | 14 | — | 0.571 | 0.418 | +0.1536 | |
| `has_consensus=True` | 12 | — | **0.667** | — | +0.0297 | **peor** que no-consensus (0.842) — contra-intuitivo |
| `condition=range` | 15 | — | 1.000 | — | +0.2916 | n chico, sospechoso |
| `condition=exact` | 98 | — | 0.796 | — | +0.1682 | |

El headline pooled es **positivo** (+0.185/unit, +20.85 total) e incluso casi-monótono por bucket de `trader_historical_wr`. **No se declara `TRADER_ALPHA_CANDIDATE`** porque:

- **Es in-sample y dominado por 2 traders.** Sin holdout fuera de muestra (leave-traders-out, §5.3), "el bucket `wr≥80` gana" es indistinguible de "los 2 wallets de mayor volumen ganaron". La varianza honesta exige bootstrap **clusterizado por trader** (§5.1), no por fila.
- **Riesgo de fuga (leakage) en `trader_historical_wr`.** Si ese WR se computó incluyendo el outcome de la propia fila, condicionar por bucket de WR y medir `win_for_trader` sobre los mismos traders es selección-sobre-el-label (§7.8).
- **Survivorship.** BSR solo registra a los traders que el tracker decidió seguir; los que explotaron no están. "Trader de calidad" está definido a posteriori.
- **`has_consensus` contradice la tesis** (consenso → peor WR), señal de que la estructura de cohortes "obvia" no es la fuente de alfa.

La hipótesis líder preliminar — **no adjudicada** — es que el BSR local **no tiene diversidad de traders suficiente** para sostener un claim de alpha falsable; el censo (§2.2) lo confirma o lo refuta.

### 2.4 Condición de flip a `READY_FOR_CODE` (falsable, pre-registrada)

Tras el censo §2.2, el veredicto se resuelve **mecánicamente**:

- **→ `TRADER_BENCHMARK_READY_FOR_CODE`** si el BSR completo tiene **≥ `N_TRADER_MIN` (12) traders distintos resueltos** y al menos **una celda L1 candidata con ≥ `N_TRADER_CELL_MIN` (5) traders** y **≥ `N_PROMOTE_FLOOR` (30) filas**. Hay sustrato para un leave-traders-out con poder.
- **→ se mantiene `NEEDS_MORE_READONLY_INVENTORY` / vira a `NEEDS_FORWARD_CONFIRMATION`** si hay filas pero la diversidad o el spread no alcanzan: el protocolo corre, devuelve `INSUFFICIENT_N` honesto y un trigger de acumulación.
- **→ `DO_NOT_BUILD_TRADER_PATH`** si el censo confirma ~6 traders dominados por 2 y ventana ~abril: el "edge" es 2 wallets, **no es falsable como alpha**; construir el benchmark solo formalizaría un cherry-pick. Se pivota a Camino B (Forecast Autopsy) o se acumula BSR forward antes de reintentar.

### 2.5 Por qué no `READY_FOR_CODE` directo ni `DO_NOT_BUILD` directo

- **No `READY_FOR_CODE`:** entregar a Codex un benchmark que mecánicamente produce un headline positivo a partir de 2 wallets de abril, y llamarlo "trader alpha", es **exactamente** la trampa de overfit que E1/E2/E3 existen para evitar. El censo cuesta minutos y es decisivo.
- **No `DO_NOT_BUILD`:** matar el Camino A **antes** de mirar el BSR completo de Railway sería matar a ciegas — el universo real (409–754 filas, 43 ciudades) puede tener la diversidad que el subconjunto local no muestra. Primero el censo, después la sentencia.

---

## 3. Qué consume E3 (entradas)

| Entrada | Rol | Cómo se abre | Obligatoria |
|---|---|---|---|
| `blocked_signals_resolutions.jsonl` (BSR, **full Railway** vía pull read-only; local solo para tests/dev) | **única fuente row-level + outcomes** | lectura de archivo (allowlist, sin glob) | **sí** |
| `data/predictive/decision_dataset.db` → `v_benchmark_input` (join read-only por `match_key`=`eval_key`) | **referencia terciaria**: prob del forecast del bot, solo como contexto | SQLite `mode=ro`, `query_only=ON` | no (diagnóstico) |

**Campos BSR usados** (confirmados en datos): `match_key`, `city`, `date`, `condition`, `trader`, `trader_historical_wr`, `outcome` (lado del trader: `Yes`/`No`), `avg_price_entered`, `close_price`, `yes_price`, `no_price`, `resolved`, `win_for_trader`, `has_consensus`, `checked_at`.

**E3 NO consume:**
- **Gamma API** — los outcomes ya están en BSR (`resolved`+`close_price`). Llamarla reduplicaría el resolver (viola E1 §5.6). E3 hereda, no produce.
- `bot.py`, `trades.log`, wallets, `order_id`, `reconciled_executions.jsonl`, DB de producción de trading, Railway writes, env vars.
- Cualquier fila no resuelta (filtradas en §4).

---

## 4. Dataset: feature / label / baseline / exclusiones

**Unidad de observación:** una selección-de-trader resuelta = una fila BSR con `resolved=true`.

| Elemento | Definición |
|---|---|
| **Label** | `win_for_trader ∈ {0,1}` — el lado elegido por el trader (`outcome`) resolvió a su favor. Es el outcome heredado de BSR, no recomputado. |
| **Baseline de mercado** | `avg_price_entered` = prob implícita por el mercado del **lado del trader** al entrar. **Este es el baseline primario y siempre.** |
| **Métrica núcleo / edge** | `sim_unit_pnl = win_for_trader − avg_price_entered` (= `1−p` si gana, `−p` si pierde). `mean(sim_unit_pnl) = WR − mean(price)`: positivo ⟺ la selección gana más seguido que su precio implícito ⟺ bate al mercado. **non-canonical**. |
| **Features (cohorte, conocidas al entrar)** | `trader_historical_wr` (bucket, §5), `has_consensus`, `condition`, `trader_side` (=`outcome` normalizado YES/NO), `city` (solo ablation), `days_ahead` si derivable de `date`−`checked_at` o de E1. |
| **Provenance** | `trader` (id) se usa **solo** para clusterizar bootstrap, asignar folds LTO y contar diversidad; **nunca** se promueve a columna de cohorte de promoción ni se emite al summary committeable como identidad (§9). |

**Exclusiones (pre-registradas):**
- `resolved != true`.
- `close_price ∉ {0.0, 1.0}` (no settled/ambiguo) o `win_for_trader` / `avg_price_entered` nulos.
- madurez: settled + `date` con antigüedad ≥ 7 días (T+7, paridad con E1/E2). Filas frescas → observabilidad, no elegibles.
- **Seoul** excluida (paridad con self-eval/E1).
- `outcome` fuera de `{Yes,No}` → cuarentena, no descartado silenciosamente.

---

## 5. Cohortes, métricas, holdout

### 5.1 Métricas por celda × partición

Para cada celda (L0/L1/ablations) y cada partición (§5.3):

| Métrica | Fórmula | Notas |
|---|---|---|
| `n` | filas | conteo |
| **`n_traders`** | # traders distintos en la celda | **guarda de diversidad — nueva y crítica** |
| `WR` | `mean(win_for_trader)` | win-rate del lado del trader |
| `mean_price` | `mean(avg_price_entered)` | **baseline de mercado** |
| **`edge`** | `WR − mean_price` (= `mean(sim_unit_pnl)`) | **titular; + ⇒ bate al mercado** |
| `sim_unit_pnl_total` / `_mean` | suma / media | **non-canonical, not money** |
| `brier_advantage` | `brier_market − brier_model`, con `model_prob = trader_historical_wr/100` | **secundario/diagnóstico** (leakage-prone, §7.8); mismo signo que E2 |
| `calibration_gap` | `mean(trader_historical_wr/100 − win_for_trader)` | diagnóstico |
| `edge_ci` | **bootstrap clusterizado POR TRADER** (B=10000, seed=2026) | resamplea traders, no filas — varianza honesta ante dominancia de 2 wallets |
| `sim_drawdown` (opcional) | peor caída de la suma acumulada de `sim_unit_pnl` ordenada por `date` | diagnóstico de riesgo |

### 5.2 Jerarquía de cohortes (superficie de promoción estrecha)

| Nivel | Definición | Rol | ¿Promocionable? |
|---|---|---|---|
| **L0** (root) | todas las filas elegibles pooled | headline, ancla anti-cherry-pick | solo **confirma signo** |
| **L1** | `trader_quality_bucket × side` (y `× has_consensus`) | **superficie de promoción** (familia defendible) | **sí** (única) |
| **L2 / ablations** | `+ condition`, `+ city`, `+ trader individual` | diagnóstico | **no** — solo **DEMOTE** |

`trader_quality_bucket` desde `trader_historical_wr`: `{<60, 60-70, 70-80, ≥80}`. `side ∈ {trader_YES, trader_NO}`. `has_consensus ∈ {yes,no}`.

**Reglas duras de cohorte:**
- **El trader individual NUNCA es superficie de promoción** — es ablation que solo puede DEMOTE. Esto mata el cherry-pick de los 2 wallets en origen.
- **`city` nunca entra a la clave de promoción** (fragmentación; paridad E1 §4.6); solo ablation de DEMOTE.
- Promoción se decide en **L1** con **confirmación de signo en L0** (el pooled no puede contradecir). Acota K (≤ ~16 celdas L1).
- Leaf/ablation **solo DEMOTE**, nunca PROMOTE.

### 5.3 Holdout — el núcleo, dado que no hay forward fresco

Como un forward temporal fresco **no está disponible rápido** (todo el BSR local es abril; §2.2), E3 usa **dos splits complementarios**, y el claim falsable de HOY recae en el primero:

1. **Leave-Traders-Out (LTO) — holdout primario.** Se particionan los **traders** (no las filas) en *discovery* y *confirmation* por **hash determinista pre-registrado del id del trader** (k-fold, k=5 si hay traders; asignación fijada **antes** de mirar outcomes). Las reglas de cohorte (qué bucket/consenso) se **eligen** sobre discovery; el claim WR-vs-price se **mide** sobre confirmation (traders **nunca** usados para elegir la regla). Esto prueba *"el signo de calidad generaliza a traders NUEVOS"*, no *"2 wallets ganaron en abril"*. **Es el holdout correcto para este dataset.**
2. **Forward temporal — confirmación diferida.** Se **reutiliza** `E2_PREREG_CUTOFF_UTC = 2026-05-29` (compatibilidad E1/E2). Con datos de hoy → `n_forward = 0` ⇒ el claim temporal es `NEEDS_FORWARD_CONFIRMATION` hasta que BSR fresco acumule. Sirve como sign-consistency cuando exista.
3. **Anti-cherry-pick de la partición:** la asignación trader→fold y el cutoff temporal se **pre-registran**; no se puede elegir qué traders caen en confirmation.

**Honestidad estructural:** con 6 traders, el fold de confirmation tiene n diminuto ⇒ LTO devolverá `INSUFFICIENT_N` — lo cual **es** el hallazgo falsable: el dataset es demasiado *trader-thin* para sostener alpha. Por eso el censo §2.2 es la precondición.

### 5.4 Umbrales y veredictos (pre-registrados, antes de mirar resultados forward/LTO)

```
N_REVIEW            = 20     # celda revisable
N_PROMOTE_FLOOR     = 30     # mínimo de filas para considerar candidato
N_TRADER_MIN        = 12     # # traders distintos en el universo para que el path sea evaluable
N_TRADER_CELL_MIN   = 5      # # traders distintos en una celda L1 para que sea promocionable
MARGIN              = 0.02   # edge mínimo (sim_unit_pnl_mean) fuera de ruido
SIMPNL_FLOOR        = 0.0    # edge out-of-sample debe ser > 0
FDR_Q               = 0.10   # Benjamini-Hochberg sobre celdas L1 testeadas
BOOTSTRAP_B         = 10000  # seed 2026, CLUSTERIZADO POR TRADER
```

Veredicto por celda L1 (evaluado en **LTO confirmation**; forward temporal como confirmación adicional):

| Veredicto | Condición |
|---|---|
| `INSUFFICIENT_N` | `n < N_REVIEW` ∨ `n_traders < N_TRADER_CELL_MIN` ∨ fold de confirmation vacío |
| `NO_TRADER_EDGE` | `n ≥ N_REVIEW` ∧ `edge_out_of_sample ≤ 0` |
| `KILL_TRADER_PATH` (celda) | `n ≥ N_PROMOTE_FLOOR` ∧ `edge_ci.upper < 0` (confiadamente sin edge) |
| `NEEDS_FORWARD_CONFIRMATION` | pasa LTO in-fold pero `n_forward_temporal = 0` (estado de la mayoría de los datos hoy) |
| `TRADER_ALPHA_CANDIDATE` | `n ≥ N_PROMOTE_FLOOR` ∧ `n_traders ≥ N_TRADER_CELL_MIN` ∧ `edge_out_of_sample > MARGIN` ∧ `edge_ci(clusterizado).lower > 0` ∧ `sim_unit_pnl_mean > SIMPNL_FLOOR` ∧ **signo-consistente L0/LTO** ∧ pasa **FDR** ∧ **pasa single-trader-dominance** (§7.7) |

- **Global `KILL_TRADER_PATH`:** si **toda** celda L1 con `n ≥ N_REVIEW` es `NO_TRADER_EDGE`/`KILL` y ninguna llega a `CANDIDATE` ⇒ la fuente trader-following no bate al mercado ⇒ se escala pivot (Camino B o acumular forward).
- **`TRADER_ALPHA_CANDIDATE` NO autoriza nada live.** Nomina la celda a revisión Opus con su packet (§6.3). Canary/lift es decisión separada, futura, explícita. **exact/NO live sigue bloqueado** sin importar el veredicto E3.

---

## 6. Salidas

### 6.1 `data/predictive/trader_benchmark_summary.json` (committeable, **solo agregado**)

```jsonc
{
  "schema_version": "trader_benchmark_summary_v1",
  "generated_at_utc": "...",
  "prereg_cutoff_utc": "2026-05-29T00:00:00+00:00",
  "lto_fold_seed": 2026,
  "thresholds": { "N_REVIEW":20, "N_PROMOTE_FLOOR":30, "N_TRADER_MIN":12,
                  "N_TRADER_CELL_MIN":5, "MARGIN":0.02, "FDR_Q":0.10,
                  "bootstrap_b":10000, "seed":2026 },
  "baseline": { "primary":"market_at_avg_price_entered",
                "secondary_diagnostic":"base_rate",
                "tertiary_reference_only":"bot_forecast_via_E1_join" },
  "inventory": { "n_resolved":0, "n_traders_distinct":0,
                 "date_min":null, "date_max":null,
                 "trader_concentration_top2_pct":null },
  "coverage_warnings": [
    "bsr_local_subset_only: full census from Railway pending (precondition §2.2).",
    "forward_temporal_n_zero: all rows pre-cutoff; holdout via leave-traders-out."
  ],
  "cells": [ { "level":"L1", "cohort":"wr>=80|trader_NO", "partition":"lto_confirmation",
               "n":0, "n_traders":0, "WR":null, "mean_price":null, "edge":null,
               "edge_ci":[null,null], "sim_unit_pnl_mean":null,
               "brier_advantage":null, "calibration_gap":null,
               "p_raw":null, "p_fdr":null,
               "single_trader_dominance_pass":null, "verdict":"INSUFFICIENT_N" } ],
  "top_candidates": [],
  "killed_cohorts": [],
  "global_verdict": "NEEDS_MORE_READONLY_INVENTORY",
  "disclaimer": "sim_pnl simulated_non_canonical_not_money. eligible_for_policy=false. market_truth_canonical=false. No trading authorization. exact_no_live_remains_blocked.",
  "eligible_for_policy": false
}
```

- **Sin filas crudas, sin wallets, sin `match_key` listados, sin precios por trader, sin identidades.** `trader` aparece **solo** como conteo (`n_traders`, `trader_concentration_top2_pct`) o como **hash salteado** si una celda DEMOTE necesita señalar dominancia — nunca el handle real.
- `sim_pnl` **siempre** etiquetado `simulated · non-canonical · not money`.
- `eligible_for_policy=false`.

### 6.2 `docs/predictive/trader_benchmark_summary.md` (opcional, render humano, no autoritativo). El JSON manda.

### 6.3 Packet de candidato (si existe `TRADER_ALPHA_CANDIDATE`): definición de celda L1, n + n_traders, edge + CI clusterizado, sim_unit_pnl_mean, sign-consistency LTO↔L0, p-FDR, resultado single-trader-dominance. Insumo para revisión Opus — **no** una autorización.

### 6.4 Qué NO genera E3
No live trading, no BANKROLL, no Fase C, no env vars, no city modes, no BUY/SELL/SKIP, no P&L canónico, no `trades.log`, no wallets/order_ids, no filas crudas en repo, no llamadas a Gamma, no lift exact/NO.

---

## 7. Guardas anti-overfit

1. **Superficie estrecha:** promoción solo en L1 (`quality×side[×consensus]`), nunca leaf/ciudad/**trader individual**.
2. **Diversidad de traders:** `n_traders ≥ N_TRADER_CELL_MIN (5)` por celda y `≥ N_TRADER_MIN (12)` en el universo, o no se promueve. Mata el cohorte-de-2-wallets.
3. **Bootstrap CLUSTERIZADO por trader** (no por fila): resamplea traders → la CI refleja que la evidencia son ~pocos traders, no ~muchas filas independientes.
4. **Leave-Traders-Out** como gate de promoción (§5.3): generalización a traders nuevos, no memorización in-sample.
5. **FDR Benjamini-Hochberg (q=0.10)** sobre celdas L1 testeadas; se reportan p crudos y corregidos.
6. **Effect-size floor (`MARGIN`) + CI lower-bound > 0**: significancia práctica y estadística.
7. **Single-trader-dominance:** si quitar el trader top-1 de la celda flippea el signo del edge, o baja `n_traders` bajo el mínimo, la celda **DEMOTE** (no candidata).
8. **Leakage guard de `trader_historical_wr`:** si ese WR incorpora el outcome de la propia fila (a verificar en el censo/origen), las cohortes condicionadas por bucket de WR son **diagnóstico-only**; el claim primario usa `edge = WR − price`, que **no** depende de `trader_historical_wr`.
9. **Sign-consistency:** el signo del edge debe coincidir entre folds LTO (y, cuando exista, entre frozen/forward temporal). Flip de signo = ruido.

---

## 8. Acceptance tests (lo que la implementación DEBE cumplir)

1. **Métrica núcleo (oráculo).** Sobre el BSR local (n=113), E3 reproduce `mean(sim_unit_pnl)=+0.1846`, `WR=0.8230`, `mean_price=0.6385`, `total=+20.8546` (±0.0001). Si difiere ⇒ bug de carga, no avance.
2. **Aggregate-only.** `trader_benchmark_summary.json` no contiene `match_key`/wallet/`trader` handle crudo/precio por fila. Test de substring + schema.
3. **Bootstrap clusterizado determinista.** Mismo BSR ⇒ mismas CIs (resample por trader, seed fijo). Test de determinismo + test de que resamplea traders (no filas): una celda con n grande pero 1 trader produce CI ancha, no angosta.
4. **LTO determinista y pre-registrado.** Asignación trader→fold por hash fijo; un trader nunca está en discovery y confirmation a la vez; cambiar el seed cambia folds de forma reproducible.
5. **No promoción de trader individual / leaf.** Assert: ninguna celda con `level∈{L2,ablation}` ni clave que incluya trader puede tener `verdict=TRADER_ALPHA_CANDIDATE`.
6. **Diversidad gate.** Una celda con `n≥30` pero `n_traders<5` ⇒ `INSUFFICIENT_N`, nunca candidato.
7. **Single-trader-dominance.** Fixture donde el top-1 trader carga el edge ⇒ celda DEMOTE; assert.
8. **Aislamiento.** El módulo no importa `bot.py`, no usa `glob`, no usa red (no Gamma), abre cualquier DB `mode=ro`/`query_only=ON`, no escribe fuera de `data/predictive/`. Import-introspection + spy de `open`/`socket`.
9. **Degradación honesta.** Con el BSR local (6 traders, todo frozen), E3 devuelve `global_verdict=NEEDS_MORE_READONLY_INVENTORY` o `INSUFFICIENT_N` sin crash y **sin edge fabricado**; `top_candidates=[]`.
10. **Invariantes de negocio.** `eligible_for_policy=false`, `sim_pnl` etiquetado non-canonical, disclaimer incluye `exact_no_live_remains_blocked`; ninguna salida autoriza BUY/SELL/SKIP.

---

## 9. Repo como fuente de verdad / datos sensibles

- **Committeable:** `tools/trader_benchmark.py`, `tests/test_trader_benchmark.py` (+ fixtures sanitizados, traders renombrados `T1..Tn`, sin wallets), `docs/predictive/trader_benchmark_summary.md` (opcional), `data/predictive/trader_benchmark_summary.json` (**agregado**), este spec.
- **Gitignored / Railway-only:** BSR crudo full (`blocked_signals_resolutions.jsonl`), cualquier export row-level, identidades de trader/wallet.
- **El summary committeado nunca expone** wallets, `match_key`, precios por trader ni handles crudos — solo conteos y, si hace falta para DEMOTE, hashes salteados.
- Una sesión nueva reconstruye estado leyendo este spec + el summary agregado + (si necesita filas) re-pulleando BSR read-only de Railway. **Sin Engram ni memoria externa.**

---

## 10. Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Cherry-pick por 2 wallets dominantes | **alta** | `n_traders` gate + bootstrap clusterizado + LTO + single-trader-dominance + no-promoción-de-trader |
| Leakage en `trader_historical_wr` | **alta** | claim primario en `edge=WR−price` (independiente del WR histórico); WR-buckets diagnóstico-only hasta verificar el cómputo |
| Survivorship (solo traders seguidos) | media | documentado; el claim es relativo al mercado, no absoluto; censo mide cobertura |
| Forward temporal n=0 (mismo muro que E2) | media | holdout primario = LTO; forward = confirmación diferida con trigger |
| `has_consensus` contradice la tesis | media | consensus es feature de cohorte, no asunción; el benchmark lo testea, no lo presume |
| Confundir `sim_pnl` con P&L canónico | **alta** | separación dura §0/§6; etiquetado non-canonical siempre |
| Scope creep (dashboard, seguir traders live) | media | un tool + un summary + tests; sin live; candidato ≠ autorización |
| Reabrir exact/NO por la ventana | media | disclaimer `exact_no_live_remains_blocked`; candidato E3 nunca levanta exact/NO |

---

## 11. Handoff a Codex

### 11.1 Orden de implementación
0. **(Precondición §2.2 — read-only, antes de codear)** Censo full-BSR de Railway vía `tools/railway_safe.ps1 ssh cat data/blocked_signals_resolutions.jsonl` → reportar agregado: n resuelto, # traders distintos, n por trader, rango `date`/`checked_at`, mezcla condition/side/consensus. **Resuelve el veredicto §2.4.** Sin escribir nada.
1. **(E3)** `tools/trader_benchmark.py` read-only: loader BSR (allowlist, sin glob) → exclusiones §4 → roll-up L0/L1/ablations → métricas §5.1 (bootstrap clusterizado) → holdout LTO + forward §5.3 → veredictos §5.4 → guardas §7 → `trader_benchmark_summary.json` §6.
2. **(E3)** `tests/test_trader_benchmark.py`: los 10 de §8. Gate duro = §8.1 (oráculo), §8.2 (aggregate-only), §8.3/§8.4 (clustered bootstrap + LTO), §8.6 (diversidad).
3. **(E3)** Render `.md` opcional.

### 11.2 Archivos candidatos
| Archivo | Acción | Agente |
|---|---|---|
| `tools/trader_benchmark.py` | crear (E3) | Codex |
| `tests/test_trader_benchmark.py` | crear (§8) | Codex |
| `data/predictive/trader_benchmark_summary.json` | output generado | (E3) |
| `docs/predictive/trader_benchmark_summary.md` | output opcional | (E3) |
| `.gitignore` | confirmar BSR crudo ignorado | Codex |

### 11.3 Qué NO tocar
`bot.py`, trading core, sizing, scheduler, city modes, guards, SL, whitelist; env vars, Railway writes, BANKROLL, Fase C, lift exact/NO; P&L canónico/cash/wallet; `trades.log`; Gamma desde E3; ingestión por glob; el contrato de outcomes (E3 hereda de BSR, no re-resuelve); E1/E2 (congelados salvo join read-only).

### 11.4 Cuándo volver a Opus
- El censo §2.2 resuelve `READY_FOR_CODE` / `DO_NOT_BUILD` → Opus ratifica antes de codear si es borderline.
- Cualquier celda llega a `TRADER_ALPHA_CANDIDATE` → Opus revisa el packet antes de cualquier paso live; exact/NO sigue bloqueado.
- `global_verdict = KILL_TRADER_PATH` → Opus decide pivot (Camino B Forecast Autopsy o acumular forward).
- Se descubre leakage en `trader_historical_wr` (§7.8) → Opus revisa antes de usar WR-buckets como algo más que diagnóstico.
- Se propone tocar el firewall exact/NO, el cutoff pre-registrado, o seguir traders en vivo.

### 11.5 Conexión con Phase 2 (2026-06-09)
Carriles distintos (idéntico a E2 §8.5): Phase 2 es la decisión **canónica** sobre trades reales; E3 es auditoría **offline/non-canonical** del path trader-following. E3 produce un advisory adjuntable a la revisión 06-09; si discrepan, Phase 2 manda para lo live. E3 no es gate de Phase 2 ni viceversa.

---

## 12. Confirmaciones de no cambios live

Este documento es **DESIGN-ONLY**. No modifica `bot.py`, trading core, env vars, Railway, DB de producción, scheduler, guards, SL, city modes, ni E1/E2. Y deja constancia:

- **BANKROLL sigue $25** (HOLD).
- **Fase C no autorizada.**
- **No live trading.**
- **No env vars.**
- **No city modes.**
- **No BUY/SELL/SKIP.**
- **P&L canónico sigue `none`** — todo `sim_pnl` de E3 es `simulated · non-canonical · not money`.
- **exact/NO live sigue bloqueado**; E3 no lo reabre.
- No se usó `trades.log`, wallets ni `order_id`. No se usó Engram ni memoria externa.

---

## 13. Resumen ejecutivo

E3 es el **examen del pivot de alpha (Camino A)**: lee BSR (outcomes heredados, sin Gamma), agrega en una jerarquía L0/L1 con superficie de promoción estrecha (`trader_quality × side`), mide el **edge contra el mercado al `avg_price_entered`** (`edge = WR − precio = mean sim_unit_pnl`), y adjudica veredictos con guardas anti-overfit centradas en el riesgo dominante de este dataset: **pocos traders, dos wallets, una sola ventana temporal**. Las guardas clave son **diversidad de traders (`n_traders`), bootstrap clusterizado por trader, y holdout leave-traders-out** (porque un forward temporal fresco no llega a tiempo). El protocolo está **completo y codeable**, pero el veredicto es **`NEEDS_MORE_READONLY_INVENTORY`**: el BSR local (113 filas, 6 traders, 75% en 2 wallets, todo abril) no permite distinguir alfa de cherry-pick, y el universo real vive en Railway. Una **precondición read-only barata** (censo full-BSR) resuelve mecánicamente §2.4: `READY_FOR_CODE` si hay diversidad, `DO_NOT_BUILD_TRADER_PATH` si confirma 2-wallets-de-abril. Sin tocar nada live, con BANKROLL $25 HOLD, Fase C no autorizada, P&L canónico `none` y exact/NO bloqueado.
