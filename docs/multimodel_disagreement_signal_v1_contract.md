# H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1 — Contract

**Status:** `H3_TOOL_DEPLOYED_MANUAL_ONLY` (2026-05-29, repaired 2026-05-30)
**Approved by:** Pablo (2026-05-29, via session prompt; repair 2026-05-30)
**Implemented:** 2026-05-29 (Sonnet, CODE session); **Repaired:** 2026-05-30 (Sonnet, CODE REPAIR)
**Classification:** MONETIZATION_RELEVANT / RISK_CONTROL / BOT_BRAIN_CHECK_BUILD

---

## 0. Repair V1 → V1.1 (2026-05-30)

Tres bugs críticos detectados en smoke inicial corregidos antes de acumular evidencia:

| Bug | Síntoma | Fix |
|-----|---------|-----|
| Outcome falso en mercados abiertos | `resolve_outcome_from_gamma()` no verificaba `closed=True`; precio extremo de mercado abierto resolvía incorrectamente | Guard: `if not market.get("closed"): return None` antes de leer precios |
| Timezone UTC hardcodeado | `fetch_multimodel_tmax()` usaba `timezone=UTC` ignorando `timezone_str` de ciudad; día Open-Meteo podía no coincidir con día de resolución local | `_open_meteo_url_for_model()` helper; URL usa `timezone_str` contractual de ciudad |
| Semántica threshold sin ±0.5 | H3 usaba bare `CDF(threshold)` en vez del ajuste integer-rounding del bot | `at_or_above = 1-CDF(threshold-0.5)`; `at_or_below = CDF(threshold+0.5)` |

**V1 prereg cutoff:** `INVALIDATED_TECHNICAL_SMOKE_NOT_EVIDENCE` (2026-05-29T21:54:43Z)
**V1.1 prereg cutoff:** Se fijará en primera captura forward válida posterior al repair.
**valid_h3_resolved_holdout_n:** `0` tras reparación.
**Snapshots V1 smoke:** Renombrados `_invalidated_*.json` (skipped por loader). No son evidencia.

Version bumps: `H3_HYPOTHESIS_ID = H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1`, `H3_SCHEMA_VERSION = h3_v1_1`, `H3_FORMULA_VERSION = inter_model_disagreement_v1_1`.

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

## 5. Fórmula candidata H3 (V1.1 — ±0.5 integer-rounding semantics)

```python
# Modelos efectivos: ecmwf_ifs025, gfs_seamless, icon_seamless, jma_seamless, gem_seamless
consensus_mean_tmax = mean(per_model_tmax.values())
inter_model_disagreement_std = sample_std(per_model_tmax.values())
sigma_candidate = max(inter_model_disagreement_std, 0.8)

# at_or_above: P(temp >= threshold-0.5)  — integer rounding, replicates bot.py estimate_prob()
candidate_prob_yes = 1 - normal_cdf(threshold - 0.5, mu=consensus_mean_tmax, sigma=sigma_candidate)

# at_or_below: P(temp <= threshold+0.5)  — integer rounding, replicates bot.py estimate_prob()
candidate_prob_yes = normal_cdf(threshold + 0.5, mu=consensus_mean_tmax, sigma=sigma_candidate)

# exact, range: out of scope V1
candidate_formula_version = "inter_model_disagreement_v1_1"
```

Nota: `at_or_above(T) + at_or_below(T) > 1.0` es intencional (bin overlap de 1°C). Complemento exacto: `at_or_above(T) + at_or_below(T-1) = 1.0`.

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
| `market_day_timezone` | Timezone local contractual (alinea día Open-Meteo con día de mercado) |
| `source_fidelity_basis` | `"icao_station_coords"` |
| `target_date` | Fecha del mercado YYYY-MM-DD (en timezone local de la ciudad) |
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

## 7. Readiness por cohorte — H3_UNIQUE_MARKET_READINESS_GUARD_V1

**Reparado 2026-05-31 (Sonnet, CODE REPAIR / H3_UNIQUE_MARKET_READINESS_GUARD_V1)**

El reporte H3 distingue dos niveles:

### Nivel snapshot (diagnóstico)
Cuenta cada snapshot individualmente. Útil para análisis temporal (lead-time, drift de modelos). No se usa para gating de alpha.

| Campo | Descripción |
|-------|-------------|
| `n_snapshots_total` | Total de snapshots |
| `n_snapshots_resolved` | Snapshots con outcome cerrado |
| `n_snapshots_pending` | Snapshots aún pendientes |
| `brier_candidate_snapshot_weighted` | Brier candidato sobre todos los snapshots |
| `brier_market_snapshot_weighted` | Brier mercado sobre todos los snapshots |

### Nivel mercado (evidencia de alpha)
Agrupa snapshots del mismo mercado. Un mercado con 3 snapshots cuenta como 1 punto de evidencia.

| Campo | Descripción |
|-------|-------------|
| `n_unique_markets_total` | Mercados únicos totales |
| `n_unique_markets_resolved` | Mercados únicos cerrados |
| `n_unique_markets_pending` | Mercados únicos pendientes |
| `brier_candidate_market_weighted` | Brier candidato (media de probs por mercado, 1 punto por mercado) |
| `brier_market_market_weighted` | Brier mercado (ídem) |
| `brier_advantage_market_weighted` | Ventaja H3 sobre mercado (>0 = H3 bate mercado) |

**Agregación por mercado:** media simple de `candidate_prob_yes` y `mkt_prob_yes_at_snapshot` sobre los snapshots del mismo mercado, antes de calcular Brier. Lead-time analysis (Brier por días de anticipación) queda pendiente / futuro.

### Clave de mercado único

```python
unique_market_key(snap):
    # Primary: market_id (Gamma ID globalmente único)
    if snap["market_id"]: return snap["market_id"]
    # Fallback: city|target_date|condition|threshold|unit|market_slug
    return f"{city}|{target_date}|{condition}|{threshold}|{unit}|{slug}"
```

### Gate de readiness

| Condición | Readiness |
|-----------|-----------|
| `n_unique_markets_resolved < 20` | `H3_HOLDOUT_ACCRUING` |
| `n_unique_markets_resolved >= 20` y `brier_advantage_market_weighted > 0` | `H3_BEATS_MARKET_OPUS_REVIEW` |
| `n_unique_markets_resolved >= 20` y `brier_advantage_market_weighted <= 0` | `H3_FALSIFIED_NO_INCREMENTAL_WEATHER_ALPHA` |

**Invariante:** 20 snapshots del mismo mercado no activan revisión. Solo 20 mercados únicos resueltos pueden activarla.

Policy no se autoriza automáticamente en ningún caso. Opus debe revisar.

---

## 8. Smoke inicial 2026-05-29 — INVALIDADO

Primera captura técnica (2 snapshots, Shanghai) capturados con `H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1` (V1 pre-repair):

| Snapshot | condition | threshold | mkt_prob_yes | consensus_mean | inter_model_std | candidate_prob (V1) |
|----------|-----------|-----------|-------------|---------------|----------------|---------------------|
| Shanghai/2026-05-30 | at_or_below | 24.0°C | 0.003 | 25.66 | 0.8503 | 0.0255 |
| Shanghai/2026-05-30 | at_or_above | 34.0°C | 0.0015 | 25.66 | 0.8503 | 0.0 |

**Estado post-repair:** `INVALIDATED_TECHNICAL_SMOKE_NOT_EVIDENCE`

- Los mercados de target_date=2026-05-30 fueron capturados el 2026-05-29 cuando aún estaban **abiertos**.
- `resolve_outcome_from_gamma()` (V1, con bug) los resolvió como "NO" por precio extremo.
- Eso es inválido: precio extremo ≠ mercado cerrado.
- Los archivos de snapshot fueron renombrados a `_invalidated_*.json` (loader los ignora).
- Marker prereg V1 renombrado a `_h3_prereg_cutoff_v1_INVALIDATED_2026-05-29T21-54-43Z.json`.
- `valid_h3_resolved_holdout_n = 0` tras reparación.
- Nuevo `H3_PREREG_CUTOFF_UTC` (V1.1) se fija en la primera captura forward válida post-repair.

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
| `tools/h3_auto_capture.py` | Wrapper automático LOG_ONLY para bot.py (H3_AUTOMATED_LOG_ONLY_CAPTURE_V1) |
| `tests/test_multimodel_shadow.py` | 29 tests (inyectando fetchers) |
| `tests/test_h3_auto_capture.py` | 31 tests wrapper automático |
| `tests/test_h3_research_capture.py` | 13 tests scheduled research capture |
| `tests/fixtures/multimodel_open_meteo_sample.json` | Fixture 5 modelos Shanghai |
| `data/multimodel_shadow/` | Snapshots locales (gitignored) |

---

## 14. H3_RESEARCH_CAPTURE_SCHEDULE_V1 (2026-05-30)

**Estado:** `H3_RESEARCH_CAPTURE_SCHEDULE_V1_DEFAULT_OFF`
**Implementado:** 2026-05-30 (Sonnet, CODE CONTROLADO)
**Autorizado por:** Pablo (2026-05-30, session prompt)

### Qué hace

`maybe_run_h3_research_capture(state, now)` en bot.py ejecuta `tools/multimodel_shadow.py --forward-snapshot` como subprocess desde el bloque de observabilidad (run_observability_alerts), al final del ciclo, fuera del loop de decisión de trading.

Consulta Gamma directamente (sin pasar por candidatos del loop) y Open-Meteo para las 4 ciudades H3: Shanghai, Tokyo, Buenos Aires, Ankara. Condiciones: `at_or_above` y `at_or_below` únicamente.

### Gate de activación

```
H3_RESEARCH_CAPTURE_ENABLED=0   # default OFF
H3_RESEARCH_CAPTURE_COOLDOWN_HOURS=4    # entre ejecuciones (default 4)
H3_RESEARCH_CAPTURE_MAX_MARKETS=20      # informativo; cap efectivo en el script
H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS=120 # timeout subprocess
```

No activar en Railway sin revisión previa de Pablo.

### Guardrails

- `eligible_for_policy = False` invariante (hardcoded en engine)
- `live_policy_eligible = False` invariante (hardcoded en engine)
- No modifica BUY/SELL/SKIP, edge, gates, BANKROLL, sizing, city modes
- Fail-closed: subprocess error/timeout → log warning, ciclo no afectado
- Idempotente: `snapshot_key+ts_bucket` gestionado por multimodel_shadow.py
- Cooldown `h3_research_capture_last_run` en alerts_state
- Solo `at_or_above` / `at_or_below` (exact/range excluidos en la CLI)
- No DB / No env vars Railway / No push

### Diferencia con H3_AUTOMATED_LOG_ONLY_CAPTURE_V1

| | H3_AUTO_CAPTURE (loop) | H3_RESEARCH_CAPTURE (standalone) |
|--|--|--|
| Fuente de mercados | Candidatos del loop de bot.py | Gamma directo (`_discover_open_markets_for_city`) |
| Punto de ejecución | PASO 4 dentro del ciclo de mercado | Bloque observabilidad post-ciclo |
| Gate | `H3_AUTO_CAPTURE_ENABLED` | `H3_RESEARCH_CAPTURE_ENABLED` |
| Activado | Sí (Railway) | No (default OFF) |
| Produce datos hoy | No (mercados filtrados antes de llegar) | Sí (auditoría local confirmada) |

---

## 13. H3_AUTOMATED_LOG_ONLY_CAPTURE_V1 (2026-05-30)

**Estado:** `H3_AUTOMATED_LOG_ONLY_CAPTURE_V1_DEFAULT_OFF`
**Implementado:** 2026-05-30 (Sonnet, CODE CONTROLADO)
**Autorizado por:** Pablo (2026-05-30, session prompt)

### Qué hace

`tools/h3_auto_capture.py` — función `maybe_capture_h3_multimodel_shadow()` — se llama automáticamente en el PASO 4 del ciclo de bot.py (línea ~22348, tras `condition_name = ...` y antes del filtro de condiciones). Captura snapshots H3 por cada mercado direccional elegible usando los datos ya disponibles en el ciclo del bot.

### Punto de integración

| Campo | Fuente en bot.py |
|-------|-----------------|
| `city` | `c["city"]` |
| `target_date` | `c["date_iso"]` |
| `condition` | `condition_name` (ya normalizado) |
| `threshold` | `threshold` = `c["temp_threshold"]` |
| `unit` | `c["unit"]` |
| `mkt_prob_yes` | `c["mkt_prob_yes"]` |
| `market_id` | `c.get("market_id")` |
| `condition_id` | `c.get("condition_id")` |

**Cero nuevas consultas Gamma**: usa `market_id`/`mkt_prob_yes` ya disponibles en el ciclo (injected `market_fetch_fn`).  
**HTTP real**: ~5 llamadas Open-Meteo por snapshot (solo cuando no es idempotente).

### Gate de activación

```
H3_AUTO_CAPTURE_ENABLED=1   # default "0" = OFF
```

Mismo patrón que `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED`. No requiere cambio de código para activar.

### Guardrails

- `eligible_for_policy = False` invariante (hardcoded en engine)
- `live_policy_eligible = False` invariante (hardcoded en engine)
- No modifica BUY/SELL/SKIP, edge, gates
- `maybe_capture_h3_multimodel_shadow()` siempre retorna `None`
- Doble protección: excepciones capturadas en la función Y en el try/except de bot.py
- Idempotencia: check filesystem ANTES del compute HTTP
- Solo `at_or_above` / `at_or_below` (exact/range excluidos)
- Solo ciudades en `ACTIVE_CITY_COORDS` (Seoul excluido automáticamente)
- Solo `unit == "C"` (Open-Meteo siempre retorna Celsius)
- No DB / No env vars / No Railway writes

### Activación (próximo paso)

Para activar en Railway: añadir `H3_AUTO_CAPTURE_ENABLED=1` a las variables de entorno.  
Requiere autorización explícita de Pablo. No activar sin revisión previa del overhead de ciclo.

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
