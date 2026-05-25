# Outcome Resolver v1 — Diseño aprobado

**Estado:** `DESIGN_APPROVED / CODE_BLOCKED_PENDING_T7_AND_PABLO_SIGNOFF`
**Aprobado por:** Opus — `APPROVE_RECONCILIATION_ARCHITECTURE_PENDING_T7_FOR_CODE`
**Documentado:** 2026-05-25 (Sesión 391 — Sonnet, docs-only)
**Dependencias canónicas:**
- [`docs/learning_data_contract.md`](learning_data_contract.md) v1.0
- [`docs/pnl_clean_source_policy.md`](pnl_clean_source_policy.md) v1.2

---

## 1. Estado y bloqueo de CODE

| Ítem | Estado |
|------|--------|
| Diseño Opus aprobado | ✅ `APPROVE_RECONCILIATION_ARCHITECTURE_PENDING_T7_FOR_CODE` |
| docs/learning_data_contract.md v1.0 | ✅ creado S390 |
| docs/pnl_clean_source_policy.md v1.2 | ✅ actualizado S390 |
| Diseño documentado en repo | ✅ este archivo (S391) |
| Pre-Edge T+7d sano (~2026-05-31) | ⏳ pendiente |
| Autorización explícita Pablo para CODE | ⏳ pendiente |

**CODE permanece bloqueado hasta:**
1. Pre-Edge T+7d sano (trigger ~2026-05-31T11:15:04Z, ejecutar tras ciclo natural posterior a las 14:05 CEST).
2. Este diseño documentado ✅.
3. Autorización explícita de Pablo para pasar a CODE.

**T+7 sano no autoriza automáticamente la implementación.**

---

## 2. Objetivo

Construir una capa de reconciliación que una fills/ejecuciones reales con outcomes oficiales Polymarket para generar datos de aprendizaje limpios y contrafactuales verificables.

**No-objetivos:**
- No presentar PnL agregado como fuente canónica para BANKROLL, readiness, Telegram accionable o decisiones operativas sin gate/decisión separada. `canonical_source=none` se refiere al PnL agregado/operativo; no al campo técnico `pnl_realized` por ejecución reconciliada que R1 sí puede materializar.
- No reemplazar `trades.log` ni `postmortem.json` como fuentes de trazabilidad operativa.
- No tocar BUY/SELL/SKIP, guards, SL, BANKROLL, sizing, whitelist, scheduler, city modes ni Fase C.
- No retroetiquetar histórico pre-reconciliación (`legacy_observability / contaminated 1.0`).
- No activar R4 sin decisión Opus separada.

---

## 3. Arquitectura R1–R4

### R1 — Reconciled executions (LOG_ONLY)

**Propósito:** separar fills/ejecuciones reales y realized PnL como primer artefacto canónico reconciliado.

**Input productivo canónico:**
```
/app/data/trades.log
```
o export controlado con provenance explícita que incluya obligatoriamente:
- `source_path`
- `capture_ts`
- `capture_method`
- `sha256`

**Output futuro:** `reconciled_executions.jsonl`

**Restricción crítica:** `data/runtime_import/...` solo puede servir como fixture/snapshot de desarrollo. Cualquier fila basada en `data/runtime_import` debe quedar:
- `eligible_for_learning=false`
- `provenance_class="dev_fixture"`

**Política de identidad:** `execution_id` = `order_id + fill_index` derivado directamente de fills. Prohibido generar `execution_id` por hash heurístico de market/side/timestamp/amount.

Si falta identidad suficiente:
- `needs_reconciliation=true`
- `eligible_for_learning=false`
- `reconciliation_blocker="missing_fill_identity"`

El campo `provenance` es **obligatorio**; si falta, la fila se **rechaza**.

**`pnl_realized` en R1:** R1 puede materializar `pnl_realized` por ejecución como resultado LOG_ONLY reconciliado desde fills canónicos de `trades.log`, siempre con provenance e identidad suficientes. R2 **no** es prerequisito para reconocer PnL económico realizado por ejecución; R2 es prerequisito para añadir `market_outcome` y contrafactuales ligados a settlement. Lo que permanece prohibido es presentar cualquier suma/agregado de `pnl_realized` como fuente canónica para BANKROLL, readiness o reporting operativo sin gate/decisión separada.

**Primer bloque implementable** tras Pre-Edge T+7 sano + autorización Pablo.

---

### R2 — Settlement join (LOG_ONLY)

**Propósito:** unir ejecuciones reconciliadas con outcomes oficiales Polymarket/Gamma.

**Input:** settlement Polymarket/Gamma verificado.

**Output futuro:** `reconciled_outcomes.jsonl`

**Gate R2:** solo después de R1 ejecutándose **≥7 días LOG_ONLY sin discrepancia material** frente a `trades.log`.

**Settlement semántica:**
```
market_outcome ∈ {YES, NO, unresolved}
```
Derivado de evidencia Gamma/Polymarket cuando el mercado esté resuelto.

**`official_settlement_temp`** solo se materializa si concurren las tres condiciones:
1. Resolution source text contractual verificado.
2. Evidencia reproducible con URL/capture/sha256.
3. Estación oficial cruzada con `RESOLUTION_ICAO`.

Si falta cualquiera:
```
official_settlement_temp = null
settlement_temp_status = "evidence_insufficient"
```

---

### R3 — Reconciled report/digest (LOG_ONLY)

**Propósito:** consumer read-only de R1+R2.

**Preautorizado en diseño** siempre que:
- No envíe Telegram con cifra PnL canónica.
- Incluya `source_quality` y `eligible_for_learning` por fila.
- No toque BANKROLL, sizing, whitelist, scheduler, guards, SL ni trading.

**Implementar después de R1+R2.**

---

### R4 — Calibration candidate (Opus-gated)

**Estado:** `NOT_PREAUTHORIZED_FOR_CODE`

Convierte datos reconciliados en calibration/training. Requiere nueva decisión Opus porque eleva el scope a modificar sigma, thresholds, city weights o Phase 2 calibration.

R4 no podrá usar filas sin `official_settlement_temp` verificada para calibración de magnitudes.

---

## 4. Inputs, outputs y provenance

| Bloque | Input canónico | Output futuro | Provenance requerida |
|--------|---------------|---------------|---------------------|
| R1 | `/app/data/trades.log` (o export con sha256) | `reconciled_executions.jsonl` | `source_path`, `capture_ts`, `capture_method`, `sha256` — obligatorio por fila |
| R2 | R1 output + settlement Gamma/Polymarket | `reconciled_outcomes.jsonl` | Settlement: URL/capture/sha256 verificado |
| R3 | R1+R2 outputs (read-only) | Digest/report | N/A (consumer) |
| R4 | R2 output (solo filas elegibles) | Calibration dataset | Nueva decisión Opus |

**Nomenclatura:** usar únicamente R1/R2/R3/R4. Prohibido llamar "Fase C" a cualquier parte del Outcome Resolver.

---

## 5. Identidades y deduplicación

- `execution_id` canónico: `order_id + fill_index` derivado de fills.
- Prohibido generar `execution_id` por hash heurístico de market/side/timestamp/amount.
- Fila sin identidad suficiente → `needs_reconciliation=true`, `eligible_for_learning=false`, `reconciliation_blocker="missing_fill_identity"`.

**Fixture obligatorio futuro:** las dos ejecuciones Shanghai NO deben reconciliarse como dos fills separados con `fill_index` distinto. El SELL intermedio debe conservar identidad propia derivada de fills, no de heurística.

---

## 6. Settlement semántica (detalle)

```
market_outcome ∈ {YES, NO, unresolved}
```

- `YES` / `NO`: cuando el mercado está resuelto y la evidencia Gamma/Polymarket es verificable.
- `unresolved`: mercado no resuelto al momento de la reconciliación, o liquidado por `micro_position_unsellable`.

**Temperatura de settlement** (`official_settlement_temp`):
- Solo se escribe si hay evidencia reproducible completa (ver sección 3, R2).
- Si falta, `official_settlement_temp=null`, `settlement_temp_status="evidence_insufficient"`.
- R4 no puede usar filas con `official_settlement_temp=null` para calibración de magnitudes.

---

## 7. Política micro_position_unsellable

Referencia canónica: [`docs/learning_data_contract.md`](learning_data_contract.md) §micro_position_unsellable.

En R1/R2:
- `closure_reason=liquidity_exit` — la posición se cerró por liquidez, no por resolución del mercado.
- `market_outcome=unresolved_at_exit` — el mercado no estaba resuelto al momento del cierre.
- `forecast_correctness` excluido del cálculo (no hay outcome verificable al momento del exit).
- `eligible_for_calibration=false`.
- Dos pistas contrafactuales separadas: (a) PnL económico realizado, (b) contrafactual hipotético hasta resolución (solo si hay outcome posterior verificable).

---

## 8. Seoul suspect exclusion

Las 8 filas Seoul Pre-Edge de ciclos `2026-05-24T12:00/16:00/20:00Z` son `source_fidelity_suspect` porque fueron capturadas con la estación KMA (mismatch vs RKSI oficial).

En R1/R2:
- Filas Seoul pre-patch: `source_fidelity="suspect"`, `eligible_for_learning=false`, `exclusion_reason="station_mismatch_kma_vs_rksi_pre_patch"`.
- Filas Seoul post-patch (futuras, si Seoul se reactiva): evaluar con `source_fidelity="confirmed"` solo si la evidencia RKSI es limpia.

El Outcome Resolver no necesita excluir P1/P2 (Singapore/Wellington/Munich/Toronto/Madrid/Shanghai/Tokyo) por identidad de estación; source fidelity confirmada para esas ciudades en S389.

---

## 9. Orden de implementación y gates

| Paso | Acción | Gate |
|------|--------|------|
| 1 | Implementar R1 | Pre-Edge T+7d sano + autorización Pablo |
| 2 | Operar R1 ≥7 días LOG_ONLY | Sin discrepancia material vs `trades.log` |
| 3 | Implementar R2 | R1 gate cumplido (paso 2) |
| 4 | Implementar R3 | R1+R2 operativos, dentro de límites read-only |
| 5 | Considerar R4 | Nueva decisión Opus — no preautorizado |

---

## 10. Tests y fixtures futuros

Los siguientes casos deben cubrirse en el test suite antes de activar R1 en producción:

| Fixture | Propósito | Criterio |
|---------|-----------|----------|
| Shanghai doble BUY + SELL intermedio | Identidad fill_index no heurística | Los dos BUY tienen `fill_index` 0 y 1 respectivamente; el SELL tiene su propio `execution_id` derivado |
| Wellington `liquidity_exit` | micro_position_unsellable policy | `market_outcome=unresolved_at_exit`, `eligible_for_calibration=false`, `closure_reason=liquidity_exit` |
| Seoul `source_fidelity_suspect` | Exclusión filas KMA | `eligible_for_learning=false`, `exclusion_reason="station_mismatch_kma_vs_rksi_pre_patch"` |
| `provenance_class="dev_fixture"` | Rechazo para learning | `eligible_for_learning=false` para toda fila de `data/runtime_import` |
| Fill sin `order_id` | Missing fill identity | `needs_reconciliation=true`, `reconciliation_blocker="missing_fill_identity"`, `eligible_for_learning=false` |
| `official_settlement_temp=null` | Gate R4 | Fila no usable para calibración de magnitudes |

---

## 11. Stop conditions / cuándo volver a Opus

Escalar a Opus si ocurre cualquiera de:

- R1 produce discrepancia material vs `trades.log` (PnL delta >$0.50 en cualquier trade individual).
- R1 no puede resolver identidad en >5% de filas tras 7 días de operación.
- R2 join rate <80% (mercados resueltos no encontrados en settlement source).
- Aparece un artefacto de settlement no previsto en el contrato (nuevos formatos Gamma).
- Cualquier resultado de R3 que pudiera confundirse con PnL canónico.
- Cualquier propuesta de activar R4.
- Cualquier cambio en `trades.log` schema de Railway.
- Cualquier situación que requiera backfill retroactivo pre-reconciliación epoch.

---

## 12. Guardrails generales

- No retroetiquetar histórico pre-epoch (pre-commits `0882997`+`3307b4f`).
- No usar `performance.json` ni `trade_lifecycle.json` como input de R1 (prohibidos por data contract hasta reconciliación).
- No emitir PnL canónico hasta R2 operativo ≥7 días y decisión Pablo.
- No activar R4 sin nueva sesión Opus.
- **Durante diseño y hasta autorización CODE:** no acceder ni mutar Railway.
- **En futura implementación/validación autorizada de R1:** se permite lectura read-only de `/app/data/trades.log` mediante `tools/railway_safe.ps1`, o exportación controlada con provenance (sha256 incluido). Queda prohibida cualquier mutación Railway (env vars, state files, data files) salvo autorización explícita separada.
- No tocar: `bot.py`, trading core, `BANKROLL`, sizing, whitelist, scheduler, guards, SL, city modes, env vars, DB, Fase C, BUY/SELL/SKIP.
