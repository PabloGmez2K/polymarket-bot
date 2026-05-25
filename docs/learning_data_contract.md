# Learning Data Contract v1

**Versión:** 1.0  
**Fecha:** 2026-05-25  
**Sesión:** 390 (Sonnet)  
**Clasificación:** MONETIZATION_RELEVANT / DATA_GOVERNANCE  
**Decidido por:** Opus (veredicto: DATA_CONTRACT_REQUIRED_BEFORE_OUTCOME_RESOLVER)  
**Documentado por:** Sonnet (docs-only, sin código, sin Railway)

---

## 1. Estado, propósito y alcance

Este documento define el contrato semántico obligatorio para cualquier uso de datos de producción en PnL, market outcomes, calibración meteorológica y entrenamiento futuro. Es prerequisito bloqueante para el Outcome Resolver v1 y para cualquier pipeline de learning o calibración.

**Alcance:** artefactos de producción en Railway — `trades.log`, `postmortem.json`, `performance.json`, `trade_lifecycle.json`, artefacto Pre-Edge, settlement oficial de Polymarket.

**Fuera de alcance de este documento:** código de bot, trading core, sizing, BANKROLL, guards, scheduler, city modes, Fase C.

---

## 2. Problema que resuelve

### 2.1 Contaminación de artefactos de ciclo de vida

`trade_lifecycle.json` y `performance.json` tienen dos problemas estructurales confirmados por Opus:

1. **Shanghai NO — dos BUY reales separadas del mismo token/market:** la primera fue vendida prematuramente por el bug NO re-eval (corregido en commit `0882997`). `trade_lifecycle` mezcla ambas ejecuciones bajo un mismo `position_key`; no refleja correctamente la historia real de la posición.

2. **`performance.json` — cierres LOSS_TOTAL repetidos:** presenta duplicados que impiden usarlo directamente para PnL agregado, outcomes o training sin reconciliación previa.

Estos artefactos son **contaminated 1.0** (nomenclatura de [pnl_clean_source_policy.md](pnl_clean_source_policy.md)).

### 2.2 Separación conceptual requerida

Cuatro conceptos distintos que los artefactos actuales mezclan:

| Concepto | Definición canónica |
|----------|-------------------|
| **PnL realizado** | Ganancia/pérdida económica real basada en fills confirmados |
| **Market outcome** | Resultado del mercado según resolución oficial de Polymarket |
| **Forecast correctness** | Si la tesis meteorológica fue correcta (requiere settlement oficial) |
| **Liquidity exit** | Cierre forzado por micro_position_unsellable, sin relación con outcome |

---

## 3. Contrato canónico por artefacto

| Artefacto | Clasificación | Uso autorizado | Uso prohibido |
|-----------|--------------|----------------|---------------|
| `trades.log` / fills reconciliados por `order_id` + `fill_value` | **CANONICAL_FOR_REALIZED_PNL** | PnL realizado, reconciliación de fills | — |
| `postmortem.json` | **OBSERVABILITY_ONLY** | Seguimiento por-trade, auditoría interna | PnL agregado canónico, market outcomes, training |
| `performance.json` | **REQUIRES_RECONCILIATION + PROHIBITED_FOR_TRAINING_UNTIL_FIXED** | Consulta manual con disclaimer | PnL canónico, training, calibración, Outcome Resolver input |
| `trade_lifecycle.json` | **PROHIBITED_FOR_TRAINING_UNTIL_FIXED** (contaminated 1.0) | Telemetría interna con disclaimer `untrusted_pnl` | Training, calibración, Outcome Resolver input, BANKROLL readiness |
| Artefacto Pre-Edge (`exact_no_qt_match_evaluations_log_only.jsonl`) | **CANONICAL_FOR_FORECAST_IDENTITY** | Identidad de forecast pre-edge; input Outcome Resolver cuando diseño aprobado | Market outcome (todavía no hasta T+7d + diseño Opus) |
| Settlement oficial Polymarket (Gamma/WU verificado) | **CANONICAL_FOR_MARKET_OUTCOME** | Determinar si el mercado resolvió YES/NO | — |
| Output del Future Outcome Resolver | **CANONICAL_FOR_LEARNING** solo si cumple los requisitos de §6 | Training, calibración, WR de tesis meteorológica | Cualquier uso si lee artefactos contaminados |

---

## 4. Política micro_position_unsellable

Un cierre `micro_position_unsellable` es un cierre económico real limitado por liquidez. No equivale a market outcome ni a forecast correctness.

| Dimensión | Tratamiento |
|-----------|------------|
| **PnL económico** | Incluir como pérdida real; etiquetar `closure_reason="liquidity_exit"` |
| **Market outcome** | Excluir hasta settlement final real; `outcome="unresolved_at_exit"` |
| **WR de tesis meteorológica** | Excluir; reportar separado como `liquidity_loss_rate` |
| **Calibración** | Excluir hasta outcome resuelto por settlement oficial |
| **Training / forecast_correctness** | Excluir del label `forecast_correctness`; puede usarse en el futuro como señal de riesgo de liquidez |
| **Contrafactual P&L** | Dos pistas separadas: `pnl_realized` y `pnl_counterfactual_if_held_to_resolution` |

---

## 5. Reconciliation epoch y tratamiento histórico

### Epoch de reconciliación hacia adelante

La reconciliación limpia comienza desde los dos commits de corrección:

- `0882997` — fix: correct NO position re-eval pricing
- `3307b4f` — fix: align Seoul forecast station with RKSI

Trades y fills **posteriores** a estos commits pueden reconciliarse sobre `trades.log` con confianza.

### Tratamiento del histórico

- El bloque histórico de `trade_lifecycle.json` y `performance.json` previo a la reconciliation epoch se declara **legacy_observability / contaminated 1.0**.
- **No se retroetiqueta fila por fila ahora.** La reconciliación histórica queda como tarea opcional y gateada por ROI futuro.
- Los artefactos contaminados se mantienen en Railway para auditoría interna; no se borran, no se promueven.

---

## 6. Dependencia del Outcome Resolver v1

El Outcome Resolver CODE queda **BLOCKED** hasta que se cumplan todos los requisitos:

1. Este contrato documentado y aprobado (este archivo). ✅
2. Diseño Outcome Resolver aprobado por Opus (pendiente).
3. Pre-Edge T+7d checkpoint sano (~2026-05-31T11:15:04Z, Sesión siguiente).

El Outcome Resolver **solo puede declararse CANONICAL_FOR_LEARNING** si:
- Lee fills/trades reconciliados desde `trades.log` (no `trade_lifecycle`).
- Lee settlement oficial de Polymarket (Gamma/WU verificado) como fuente de market outcome.
- Excluye explícitamente artefactos contaminados (`trade_lifecycle`, `performance.json` no reconciliado).
- Trata `micro_position_unsellable` según §4.
- Excluye filas Seoul `source_fidelity_suspect` del artefacto Pre-Edge.

---

## 7. Qué sigue permitido ahora

- **Pre-Edge T+7d (~2026-05-31):** lectura read-only del artefacto en Railway. El Pre-Edge es upstream y no depende de `trade_lifecycle` ni `performance.json`. Puede ejecutarse normalmente.
- Observación operativa del bot (ciclos, Telegram, Railway logs).
- Consulta manual de `postmortem.json` como observabilidad con disclaimer.
- Trading real con las ciudades activas actuales.

---

## 8. Qué queda prohibido hasta cumplir §6

- Implementar código del Outcome Resolver.
- Usar `trade_lifecycle.json` o `performance.json` no reconciliado como input de training, calibración o Outcome Resolver.
- Etiquetar `forecast_correctness` en cierres `micro_position_unsellable`.
- Calcular WR de tesis meteorológica incluyendo liquidity exits sin separación.
- Usar artefactos contaminados para BANKROLL readiness o decisiones de sizing.

---

## 9. Siguiente paso técnico autorizado

**Codex /plan** — diseñar la reconciliation layer y la arquitectura del Outcome Resolver v1.

- Sin implementación antes de completar el Pre-Edge T+7d checkpoint.
- El plan debe especificar: schema join Pre-Edge ↔ settlement oficial, exclusión de artefactos contaminados, tratamiento `micro_position_unsellable`, dos pistas contrafactuales.
- Opus gate requerido antes de activar cualquier escritura del Outcome Resolver en Railway.

---

## 10. Historial de cambios

| Versión | Fecha | Autor | Cambio |
|---------|-------|-------|--------|
| 1.0 | 2026-05-25 | Opus (diseño) + Sonnet (documentación, Sesión 390) | Creación inicial |
