# BOT_SELF_EVALUATION_OUTCOME_LOOP_V1 — Contract

**Status:** `REPAIRED_LOCAL_PENDING_PUSH` (repair commit 2026-05-29)
**Approved by:** Pablo (2026-05-29)
**Implemented:** 2026-05-29 (Sonnet, code session); repaired 2026-05-29 (Sonnet, CODE REPAIR)
**Classification:** MONETIZATION_RELEVANT / RISK_CONTROL

---

## 1. Objetivo

Evaluar la calibración Brier del predictor del bot frente al mercado, usando
predicciones propias ya capturadas en `bot_signal_evaluations.jsonl` y
outcomes observados vía BSR o lookup Gamma read-only.

No introduce ledger runtime nuevo. No autoriza policy live. No modifica bot.py.

---

## 2. Arquitectura stateless read-only

```
bot_signal_evaluations.jsonl
  → filter {at_or_above, at_or_below}
  → exclude Seoul (source_fidelity_suspect)
  → deduplicate by eval_key (última predicción por ts_utc)
  → partition: evidence_frozen / forward_holdout (por SELF_EVAL_H1_PREREG_CUTOFF_UTC)
  → lookup outcomes: BSR match_key=eval_key (fallback), o gamma_lookup_fn inyectable
  → Brier bot vs mercado por cohort (condition × probability_basis=YES)
  → reporte stateless
```

Entry point CLI:
```
python tools/bot_brain.py --scope self_evaluation
python tools/bot_brain.py --scope self_evaluation --format md
```

Helper privado: `tools/_self_evaluation_engine.py`
Tests: `tests/test_self_evaluation.py`
Fixture: `tests/fixtures/self_evaluation_directional_evidence_frozen_v1.json`

---

## 3. Fuentes raw

| Fuente | Rol |
|--------|-----|
| `data/bot_signal_evaluations.jsonl` | Predicciones propias del bot |
| `data/blocked_signals_resolutions.jsonl` | Outcomes observados (fallback vía match_key) |
| Gamma API read-only | Outcomes observados (lookup inyectable en tests) |

BSR/traders NO son fuente de predicción del bot. Solo como fuente secundaria
de outcomes observados cuando `outcome` field presente en BSR.

---

## 4. Partition por cutoff de preregistro

```python
SELF_EVAL_H1_PREREG_CUTOFF_UTC = datetime(2026, 5, 29, 0, 0, 0, tzinfo=timezone.utc)
```

- `ts_utc < cutoff` → `partition="evidence_frozen"`
- `ts_utc >= cutoff` → `partition="forward_holdout"`

Toda predicción anterior al cutoff queda en evidence, resuelta o no.
Solo predicciones posteriores pueden validar mejora futura (H1).

---

## 5. H1 pre-registrada

```
El predictor actual sobreestima YES en at_or_above.
Una modificación futura de calibración solo podrá considerarse útil
si obtiene brier_advantage > 0 frente al mercado
en forward_holdout independiente.
```

No implementar recalibración hasta que forward_holdout cumpla gate.

---

## 6. Schema output por cohort

| Campo | Descripción |
|-------|-------------|
| `condition` | at_or_above / at_or_below |
| `probability_basis` | "YES" (scoring en probabilidad YES) |
| `partition` | evidence_frozen / forward_holdout |
| `n_resolved` | Filas con outcome conocido |
| `n_pending` | Filas sin outcome |
| `n_side_explicit` | Filas con side explícito en BSE |
| `n_side_inferred_legacy` | Filas sin side explícito |
| `mean_our_prob_yes` | Media our_prob / 100 |
| `mean_mkt_prob_yes` | Media mkt_prob / 100 |
| `observed_yes_rate` | Tasa YES observada |
| `brier_our` | Brier score del bot |
| `brier_mkt` | Brier score del mercado |
| `brier_advantage` | brier_mkt - brier_our (>0 = bot mejor) |
| `eligible_for_policy` | false invariante V1 |
| `live_policy_eligible` | false invariante V1 |
| `readiness` | Ver §8 |

Global:

| Campo | Valor fijo |
|-------|-----------|
| `market_truth_canonical` | false |
| `weather_truth_available` | false |
| `pnl_canonical_confirmed` | false |
| `prediction_provenance` | "bot_forecast_self_eval" |
| `market_outcome_source` | "polymarket_market_price" |

---

## 7. Diferencias respecto a otros workstreams

| Workstream | Diferencia |
|-----------|------------|
| BSR/Traders Intelligence | BSR provee outcomes; nunca predictor |
| Cohort Intelligence Report | Cohort Intelligence usa win_for_trader/policy; este engine usa Brier calibration |
| Outcome Resolver (R1/R2) | R1 es fills canónicos; este engine usa our_prob vs market_outcome observado |
| Weather Truth | Temperatura oficial no usada; solo precio de mercado observado |

---

## 8. Readiness por cohort

### Evidence frozen
| Cohort | Readiness |
|--------|-----------|
| at_or_above × YES (evidence) | `CURRENT_PREDICTOR_NOT_CANDIDATE` |
| at_or_below × YES (evidence) | `HYPOTHESIS_ONLY_INSUFFICIENT_SAMPLE` |

### Forward holdout
| Condición | Readiness |
|-----------|-----------|
| n_resolved < 20 | `HOLDOUT_ACCRUING` |
| n_resolved >= 20 | `HOLDOUT_READY_FOR_OPUS_EXPERIMENT_REVIEW` |

No autorizar policy automáticamente aunque holdout sea READY.
Opus debe revisar antes de cualquier cambio.

---

## 9. Métricas evidence frozen (baseline pre-registrado)

Establecidas por Gamma lookup manual en sesión previa (25 eval_keys no-Seoul):

| Cohort | n | Brier(bot) | Brier(mkt) | brier_advantage |
|--------|---|-----------|-----------|----------------|
| at_or_above × YES | 21 | 0.4242 | 0.3303 | -0.0939 |
| at_or_below × YES | 4 | 0.1768 | 0.2473 | +0.0705 |
| Combined directional | 25 | 0.3846 | 0.3170 | -0.0676 |

`at_or_above` → predictor peor que mercado, NO candidato para live.
`at_or_below` → hipótesis, muestra insuficiente.

---

## 10. Forward schema inspection (2026-05-29)

Railway BSE snapshot (sesión anterior):
- total_raw: 1479 | directional_rows: 111 | eval_keys_unique: 34
- our_prob: 100% | mkt_prob: 100% → Brier scoring posible
- side: 12% → `FORWARD_CAPTURE_GAP_DETECTED` (policy evaluation gap)
- market_id/condition_id: 1% → gap menor para este scope

Veredicto: **`FORWARD_CAPTURE_GAP_DETECTED`** para policy. Brier scoring funcional.
No se modifica `bot.py` en esa sesión.

## 10b. SELF_EVAL_CANDIDATE_SIDE_PROVENANCE_V1 (2026-05-29)

Scope: mejora de provenance/observabilidad del writer BSE. No amplía cobertura de trades candidatos ni autoriza policy. No cierra un gap de side en filas `no_edge`.

Patch aplicado y pusheado (amend sesión 409).

Campos nuevos en `bot_signal_evaluations.jsonl` desde este patch:

| Campo | Tipo | Valor cuando runtime seleccionó side | Valor cuando no existe side por diseño |
|-------|------|---------------------------------------|----------------------------------------|
| `candidate_side_source` | str | `"runtime_evaluation_explicit"` | `"not_captured_v2"` |
| `eligible_for_policy_evaluation` | bool | `False` | `False` |

- `candidate_side_source="runtime_evaluation_explicit"`: filas post-edge donde el runtime ya eligió un lado (`below_min_edge`, `fuera_allowlist/shadow_only_override`, `kelly_too_low`, `sl_city_cooldown`, `existing_order/existing_position/sold_this_cycle`). Solo prueba que el runtime produjo un lado explícito; no convierte la fila en candidata para policy.
- `candidate_side_source="not_captured_v2"`: filas `no_edge` donde no existe candidate side bajo la policy evaluada (ambos edges no producen candidato positivo). Correcto por diseño. Estas filas son aptas para calibración probabilística YES/NO, no para evaluación de una decisión tradable. No existe candidate side capturable sin inventarla o cambiar trading semantics.
- `eligible_for_policy_evaluation=False` invariante en todas las filas.
- `schema_version=2` ya existente, no se duplica.
- Campos no disponibles sin scope nuevo: `policy_version`, `token_id_yes/no`.
- `market_id`/`condition_id` ya en el writer cuando el caller los pasa; sin cambio.

Cambio en `_self_evaluation_engine.py`:
- `n_side_explicit`: solo cuenta filas con `candidate_side_source="runtime_evaluation_explicit"` + side no vacío.
- Filas legacy sin `candidate_side_source` → `n_side_inferred_legacy` (diagnóstico, no policy).
- Brier scores e invariantes `eligible_for_policy=false` sin cambio.

El smoke previo validó clasificación de filas explícitas/no explícitas; no capturó side nueva para filas `no_edge`.
Smoke local: Paris (runtime_explicit) → n_side_explicit=1; Oslo (not_captured) → n_side_inferred=1.
Sesión: 872 pytest + 1258 verify_before_deploy, todos passing.

---

## 11. Guardrails

- `eligible_for_policy=false` invariante en todos los cohorts
- `live_policy_eligible=false` invariante global
- `market_truth_canonical=false` invariante
- No settlement canónico, no Weather Truth, no P&L canónico
- No BUY/SELL/SKIP, no BANKROLL, no city modes, no guards, no SL
- No Railway writes, no DB, no env vars, no bot.py
- SHADOW_EXACT_NO_GLOBAL intacto
- SHADOW_ONLY_MODE intacto
- at_or_above × YES no candidata inmediata
- at_or_below × YES no autoriza live

---

## 12. Criterio de éxito/abandono

**Éxito** (SELF_EVAL_REPAIRED_REAL_SMOKE_PASS): Tests pasan. Smoke reproduce
métricas evidence_frozen con Gamma lookup real. Fixture reproduce n=21/n=4 y
brier_advantages dentro de tolerancia ±0.001.

**Estado 2026-05-29**: ÉXITO POST-REPAIR. Smoke real Railway: evidence_frozen=25,
n_resolved=21+4=25, gamma_failed=3 (holdout aún abiertos), HOLDOUT_ACCRUING.
93/93 tests + 1258/1258 verify_before_deploy.

**Abandono `SELF_EVAL_REPORT_BLOCKED_BY_CAPTURE_GAP`**: si para implementar el
reporte fuera necesario modificar `bot.py`. NO ocurrió en esta sesión.

**Abandono `GAMMA_LOOKUP_IMPLEMENTATION_BLOCKED`**: si Gamma lookup no es
reproducible. Resuelto: `build_gamma_lookup_fn()` operativa, 25/25 frozen resueltos.

**Abandono `EVIDENCE_BASELINE_MISMATCH`**: si tests contradicen métricas fijadas.
Resuelto: datos reales reproducen exactamente baselines documentados.

---

## 13. Próximos pasos (no autorizados aún)

- Forward holdout gate: `n_resolved >= 20` → Opus review → ¿recalibrar?
- Conectar con Outcome Resolver R1 cuando disponible para fills canónicos
- Captura de `side` en BSE forward (requiere patch bot.py separado + Pablo auth)
