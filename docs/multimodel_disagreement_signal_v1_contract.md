# H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1 — Contract

**Status:** `H3_TOOL_DEPLOYED_MANUAL_ONLY` (2026-05-29)
**Approved by:** Pablo (2026-05-29, via session prompt)
**Implemented:** 2026-05-29 (Sonnet, CODE session)
**Classification:** MONETIZATION_RELEVANT / RISK_CONTROL / BOT_BRAIN_CHECK_BUILD

---

## 1. Hipótesis H3 (pre-registrada)

```
H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1:
El baseline actual usa un forecast único/blended y una sigma estática.
El desacuerdo entre varios modelos meteorológicos deterministas capturados
en el mismo instante que el precio del mercado puede aportar una señal
independiente.

Una probabilidad candidata derivada del consenso multi-modelo y del
inter_model_disagreement_std solo merecerá revisión si bate al mercado
en holdout forward independiente.
```

---

## 2. Correcciones conceptuales (hardcoded en contrato)

1. **No `ensemble_spread`**: V1 usa modelos deterministas. Campo correcto: `inter_model_disagreement_std`. La Ensemble API real queda fuera de scope / Tier-2 futuro.
2. **No Historical Forecast sin caveat**: `historical-forecast-api` produce series seamless y no reconstruye el forecast disponible en el `ts_utc` de una decisión. Backfill no implementado por imposibilidad de demostrar alineación temporal sin look-ahead. Ver `H3_BACKFILL_NOT_DECISION_COMPARABLE_USE_FORWARD_ONLY`.
3. **Snapshot contemporáneo**: market price y NWP models capturados en la misma ejecución. No se une forecast capturado ahora con `mkt_prob` antiguo de BSE.

---

## 3. Preflight de modelos (2026-05-29)

Modelos deterministas validados en Open-Meteo para las 4 ACTIVE cities:

| Modelo | Shanghai | Tokyo | Buenos Aires | Ankara |
|--------|----------|-------|--------------|--------|
| `ecmwf_ifs025` | OK | OK | OK | OK |
| `gfs_seamless` | OK | OK | OK | OK |
| `icon_seamless` | OK | OK | OK | OK |
| `jma_seamless` | OK | OK | OK | OK |
| `gem_seamless` | OK | OK | OK | OK |
| `ecmwf_aifs025` | FAIL | FAIL | FAIL | FAIL |

**Modelos efectivos V1** (5/5 ciudades ACTIVE): `ecmwf_ifs025`, `gfs_seamless`, `icon_seamless`, `jma_seamless`, `gem_seamless`

**Gate cumplido**: 5 modelos >= 4 mínimo. Target preferido = 5 (alcanzado).

---

## 4. H3_PREREG_CUTOFF_UTC

```
H3_PREREG_CUTOFF_UTC = 2026-05-29T21:54:43.810836Z
```

Registrado en la primera captura forward válida. Archivado en `data/multimodel_shadow/_h3_prereg_cutoff.json` (gitignored, local).

- Predicciones `snapshot_ts_utc >= H3_PREREG_CUTOFF_UTC` → `partition="h3_forward_holdout"`
- No reutilizar H2 cutoff. No retroactivamente modificable.

---

## 5. Fórmula candidata H3 (pre-registrada)

```python
# Modelos efectivos: ecmwf_ifs025, gfs_seamless, icon_seamless, jma_seamless, gem_seamless
consensus_mean_tmax = mean(per_model_tmax.values())
inter_model_disagreement_std = sample_std(per_model_tmax.values())
sigma_candidate = max(inter_model_disagreement_std, 0.8)

# at_or_above: P(temp >= threshold)
candidate_prob_yes = 1 - normal_cdf(threshold, mu=consensus_mean_tmax, sigma=sigma_candidate)

# at_or_below: P(temp <= threshold)
candidate_prob_yes = normal_cdf(threshold, mu=consensus_mean_tmax, sigma=sigma_candidate)

# exact, range: out of scope V1
candidate_formula_version = "inter_model_disagreement_v1"
```

`sigma_candidate` NO está calibrada. Es una hipótesis falsable. No afirmar que mejora el predictor sin holdout.

---

## 6. Schema de snapshot forward

Cada snapshot JSON en `data/multimodel_shadow/` contiene:

| Campo | Descripción |
|-------|-------------|
| `schema_version` | `"h3_v1"` |
| `h3_hypothesis_id` | `"H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1"` |
| `h3_candidate_model_id` | `"multimodel_disagreement_candidate_v1"` |
| `h3_prereg_cutoff_utc` | Fijado en primera captura |
| `snapshot_ts_utc` | Timestamp UTC de captura |
| `snapshot_key` | Clave determinista idempotente |
| `city` | Ciudad ACTIVE |
| `icao` | ICAO de la ciudad (source fidelity) |
| `target_date` | Fecha del mercado YYYY-MM-DD |
| `condition` | `at_or_above` o `at_or_below` |
| `threshold` | Umbral numérico |
| `unit` | `C` o `F` |
| `market_id` | ID Gamma del mercado |
| `condition_id` | ID condición Gamma |
| `market_slug` | Slug del mercado |
| `mkt_prob_yes_at_snapshot` | Precio YES en el momento de captura |
| `model_ids_effective` | Lista de modelos usados |
| `per_model_tmax` | Dict {model_id: tmax} |
| `n_models_available` | Modelos con dato válido |
| `consensus_mean_tmax` | Media de los modelos |
| `inter_model_disagreement_std` | Std de la muestra |
| `sigma_candidate` | max(std, 0.8) |
| `candidate_prob_yes` | Probabilidad candidata H3 |
| `candidate_formula_version` | Versión de fórmula |
| `partition` | `"h3_forward_holdout"` siempre |
| `market_outcome_observed` | null hasta resolución |
| `eligible_for_policy` | **false** invariante |
| `live_policy_eligible` | **false** invariante |
| `market_truth_canonical` | false |
| `weather_truth_canonical` | false |
| `pnl_canonical_confirmed` | false |
| `provenance` | Fuentes + snapshot_contemporaneous=true |

**Idempotencia**: clave = `{city}|{market_id}|{target_date}|{condition}|{threshold}|{unit}|{ts_bucket_hourly}|{candidate_model_id}`

---

## 7. Readiness por cohorte

| Condición | Readiness |
|-----------|-----------|
| `n_resolved < 20` | `H3_HOLDOUT_ACCRUING` |
| `n_resolved >= 20` y `brier_advantage_market > 0` | `H3_BEATS_MARKET_OPUS_REVIEW` |
| `n_resolved >= 20` y `brier_advantage_market <= 0` | `H3_FALSIFIED_NO_INCREMENTAL_WEATHER_ALPHA` |

Policy no se autoriza automáticamente en ningún caso. Opus debe revisar.

---

## 8. Métricas smoke forward inicial (2026-05-29)

Primera captura válida (2 snapshots, Shanghai):

| Snapshot | condition | threshold | mkt_prob_yes | consensus_mean | inter_model_std | candidate_prob |
|----------|-----------|-----------|-------------|---------------|----------------|----------------|
| Shanghai/2026-05-30 | at_or_below | 24.0°C | 0.003 | 25.66 | 0.8503 | 0.0255 |
| Shanghai/2026-05-30 | at_or_above | 34.0°C | 0.0015 | 25.66 | 0.8503 | 0.0 |

Ambos mercados resolvieron NO (precios extremos ya efectivamente resueltos).
`readiness: H3_HOLDOUT_ACCRUING` (n=2 < 20).

---

## 9. Backfill

**No implementado**: `H3_BACKFILL_NOT_DECISION_COMPARABLE_USE_FORWARD_ONLY`

No es posible demostrar alineación temporal entre el forecast disponible antes de `ts_utc` de una decisión histórica y la respuesta actual de Open-Meteo Historical Forecast API sin look-ahead. El backfill no bloquea la captura forward ni el commit.

---

## 10. Archivos

| Archivo | Rol |
|---------|-----|
| `tools/_multimodel_engine.py` | Motor privado LOG_ONLY |
| `tools/multimodel_shadow.py` | CLI standalone |
| `tests/test_multimodel_shadow.py` | 19 tests (todos inyectando fetchers) |
| `tests/fixtures/multimodel_open_meteo_sample.json` | Fixture 5 modelos Shanghai |
| `data/multimodel_shadow/` | Snapshots locales (gitignored) |

---

## 11. Guardrails (no negociables)

- `eligible_for_policy = False` invariante
- `live_policy_eligible = False` invariante
- No `bot.py` import
- No scheduler ni activación automática
- No DB / env vars / Railway writes
- No trading / BANKROLL / BUY/SELL/SKIP
- No city mode changes
- No H2 modification
- No usar H3 para autorizar live en ningún caso
- `exact` y `range` fuera de scope V1
- Backfill histórico no implementado (no comparable sin look-ahead)

---

## 12. Siguiente integración automática mínima (no autorizada en este bloque)

Para que H3 capture automáticamente en cada ciclo del bot (sin autorización aún):

1. **Integrar `build_snapshot()` en el hot-path del bot** como LOG_ONLY call después de resolver el precio del mercado y antes de la decisión BUY/SKIP. El snapshot se escribiría a `data/multimodel_shadow/` por ciudad/mercado activo.
2. **Throttle**: máximo 1 snapshot por mercado por hora (ya garantizado por `ts_bucket` idempotente).
3. **Compute cost**: ~5 llamadas HTTP Open-Meteo + 0 llamadas Gamma adicionales (precio ya disponible en el ciclo). Overhead estimado: <500ms por ciudad activa.
4. **Gate de activación automática**: requiere autorización Pablo + Opus explícita. No implementar sin esa autorización.

No ejecutar este paso en este bloque.
