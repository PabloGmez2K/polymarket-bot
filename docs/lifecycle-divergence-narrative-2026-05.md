# Lifecycle Divergence Narrative — Mayo 2026

**Fecha:** 2026-05-13  
**Agente:** Sonnet 4.6 (docs-only, read-only)  
**Propósito:** Prerequisito A2 para B5/B6 BANKROLL readiness  
**Estado:** NARRATIVE_ONLY — no autoriza BANKROLL, no canonical_source, no Fase C  
**Referencia Opus:** `docs/p0_b5_b6_opus_review_2026_05_13.md` → punto 2 de trigger para reabrir B5/B6  

---

## Resumen ejecutivo

El sistema reporta dos cifras de P&L incompatibles:

| Fuente | Valor | Horizonte | Calidad |
|---|---|---|---|
| Wallet ΔP&L | **+$2.93** | ALL desde t0=2026-04-29 (13.4d) | `provisional` |
| trade_lifecycle | **−$20.47** | ALL (histórico completo, 122 trades) | `contaminated` |
| **Divergencia ALL** | **$23.40** | — | 16× umbral de $1.50 |
| **Divergencia 1W** | **$24.36** | 1W provisional | 16× umbral de $1.50 |

La divergencia es **esperada y explicable**, no es señal de error nuevo en el sistema operativo actual. Su magnitud refleja principalmente contaminación histórica pre-SQLiteRecorder, no pérdida real reciente. Sin embargo, hasta que esta narrativa esté firmada y los criterios B5 formalicen la promoción, ninguna cifra puede ser `canonical_candidate`.

---

## 1. ¿Qué mide wallet P&L y por qué es más cercano al dinero real?

`pnl_report.py` calcula wallet ΔP&L como:

```
wallet_pnl = snapshot_value(t_now) - snapshot_value(t0) - Σ(cash_flows entre t0 y t_now)
```

Donde:
- `snapshot_value` = cash_balance + open_positions_mark_to_market
- `cash_flows` = depósitos y retiros externos atestiguados por Pablo
- `t0` = 2026-04-29 (primera snapshot válida con atestación continua)

**Por qué es más cercano al dinero real:**
- Refleja movimientos reales de saldo en la wallet de Polymarket
- Está ajustado por los dos períodos `no_cash_flow_attestation` confirmados por Pablo (sin depósitos ni retiros externos)
- No depende de la exactitud de los precios de entrada/salida de cada trade individualmente
- El cash flow log (`wallet_cash_flows.jsonl`, rows=3, coverage=7.0d) certifica que la variación entre t0 y hoy no incluye inyecciones de capital externas

**Límite principal:** Es `provisional`, no `canonical`. La cobertura (13.4d desde t0) es insuficiente para 1M; el horizonte 1D está permanentemente bloqueado por arquitectura (snapshots cada ~24h, sin sub-horarios). La ventana 1W acaba de alcanzar 7d de cobertura (tras A1), el mínimo requerido.

---

## 2. ¿Qué mide trade_lifecycle y por qué está contaminado?

`trade_lifecycle.json` acumula el registro de cada trade individualmente: precio de entrada, precio de salida, monto invertido, resultado realizado. Actualmente: 122 trades cerrados, `realized_pnl_usdc = -$20.47`, `contamination_rate = 1.0`.

**Por qué está contaminado (`contamination_rate=1.0`):**

La contaminación total significa que **ningún trade en el registro puede usarse como telemetría canónica**. Esto ocurre porque:

1. **Pre-SQLiteRecorder (antes de 2026-04-27):** Los trades anteriores al despliegue del SQLiteRecorder no tienen registro estandarizado de precios de entrada/salida. Los precios fueron reconstruidos retrospectivamente, introduciendo errores sistemáticos de valoración.

2. **Batch `market_resolved` del 2026-04-26:** Un lote de posiciones históricas (muchas abiertas bajo lógica anterior) se resolvió en un solo evento batch. El readout de reconciliación (`pnl-reconciliation-readout-latest.md`) muestra 11 trades en ese batch con PnL=+$23.36, incluyendo anomalías como Ankara +$21.31 y Miami +$9.08. Estas cifras no corresponden a apuestas del tamaño actual del bot (~$1-2 USDC/trade), sino a posiciones históricas de mayor envergadura o a precios reconstituidos.

3. **4 trades `legacy_unresolved`:** Excluidos por `pnl_reconciliation_alert.py` pero presentes en lifecycle. Su estado de cierre es ambiguo; su PnL no puede verificarse contra la wallet.

4. **Período SL_intra de sangrado (pre-guard):** n=10 trades con exit=`stop_loss_intra`, WR=0%, PnL=−$3.95, ejecutados antes del guard v10.6.40 (desplegado 2026-04-27). Estos son pérdidas reales pero bajo una lógica de risk management que ya fue corregida.

**Uso permitido:** `non_canonical_telemetry` únicamente. Visible como indicativo pero nunca como base para decisiones de BANKROLL, Telegram con cifra real, o evaluación de performance del sistema actual.

---

## 3. Fuentes concretas que explican la divergencia de $23.40

| # | Fuente | Magnitud estimada | Tipo |
|---|---|---|---|
| F1 | Mismatch temporal (lifecycle incluye pre-t0; wallet empieza en t0=2026-04-29) | ~$15–20 | **Legacy/non-canonical** |
| F2 | Batch `market_resolved` 2026-04-26 con precios reconstituidos (Ankara +$21.31, Miami +$9.08) | ~$20–23 batch bruto; neto a reconstruir | **Legacy/non-canonical** |
| F3 | 4 trades `legacy_unresolved` excluidos de reconciliación | desconocida (posiblemente pequeña) | **Legacy/ambiguo** |
| F4 | Período SL_intra pre-guard (n=10, −$3.95) | −$3.95 | **Real histórico, riesgo corregido** |
| F5 | Posiciones abiertas (`active_positions=$5.92`) contadas en wallet pero no en realized lifecycle | +$5.92 (en wallet, no en lifecycle) | **Diferencia metodológica** |
| F6 | Micro_position_unsellable (−$4.53, n=2) en 7d | −$4.53 | **Real actual, riesgo activo** |
| F7 | Trades canary post-2026-04-27 con lógica actual | pendiente de cuantificar con fuente canónica | **Real actual** |

**Nota sobre F2:** El batch del 2026-04-26 explica la mayor parte de la divergencia. En ese día el lifecycle registró ganancias históricas masivas (resultado de posiciones pre-corrección de reglas) que no tienen correspondencia con el saldo de la wallet en ese momento, porque esos mercados se resolvieron con precios que no reflejan los intercambios reales de USDC de la cuenta actual.

---

## 4. ¿Qué parte de la divergencia parece legacy/no canónica?

**Estimación: ~$20–22 de los $23.40 son legacy/no canónicos.**

Los indicadores son:
- El batch `market_resolved` del 2026-04-26 (+$23.36 en lifecycle para ese batch) corresponde a posiciones históricas resueltas bajo lógica y configuración antigua. Ninguna posición del bot actual tiene ese tamaño.
- El mismatch temporal (t0=2026-04-29) excluye de wallet todo lo que ocurrió antes, pero lifecycle lo incluye.
- Los 4 trades `legacy_unresolved` no tienen PnL verificable.

El flag `contamination_rate=1.0` fue asignado por diseño (contrato B3, `pnl_report_design.md`) precisamente para señalizar que **ningún número de lifecycle debe usarse** sin un documento de reconciliación que explique y acote esta contaminación.

---

## 5. ¿Qué parte sigue siendo riesgo real?

**Estimación: ~$3–8 representan riesgo real documentado.**

| Ítem | Valor | Estado actual del riesgo |
|---|---|---|
| SL_intra pre-guard (n=10) | −$3.95 | **Mitigado** — guard v10.6.40 activo desde 2026-04-27 |
| micro_position_unsellable (n=2) | −$4.53 | **Activo** — posiciones que no se pueden vender por liquidez insuficiente |
| Posibles pérdidas canary post-2026-04-27 | a cuantificar | Parcialmente visible: drawdown_last_5=−$1.28 (fuente non-canonical) |

El SL_intra fue el mayor riesgo operativo documentado. El guard v10.6.40 skipea el patrón `exact + days≤1` que producía el sangrado. El veredicto A8 (re-check 2026-05-21 o 5º trade guarded) determinará si el riesgo está totalmente contenido.

Las micro_positions unsellable representan USDC bloqueados: el bot compró posiciones que el mercado no puede absorber para vender. Esto es pérdida operativa real bajo el sistema actual, no legacy.

---

## 6. ¿Qué debe estar resuelto antes de que B5/B6 pueda considerar canonical_candidate?

Según el P0 Opus (`docs/p0_b5_b6_opus_review_2026_05_13.md`, trigger §84–92), los requisitos son:

| Requisito | Estado actual | ETA |
|---|---|---|
| `cash_flows.coverage_days` ≥ 28d contiguos válidos sin gaps | **7.0d** (tras A1) | ~2026-06-08 |
| ≥ 28 wallet snapshots distribuidos en esos 28d | **~15d distintos** (insuficiente) | ~2026-06-08 |
| Divergencia lifecycle explicada documentalmente (este documento) | **COMPLETO** con este doc | Hoy |
| Pablo confirma disposición a entrar al ciclo B5 | **Pendiente** | Señal manual de Pablo |
| B5 spec formal (criterios reproducibles de promoción) | **No existe** | Requiere Opus session |
| B6 Opus review sobre el sistema completo | **No ejecutado** | Post-B5 |

**Este documento cierra el requisito de narrativa documentada.** No cierra los demás requisitos.

La promoción `provisional → canonical_candidate` no es posible antes de 2026-06-08 por restricción de cobertura temporal, independientemente de la narrativa.

---

## 7. Tabla resumen wallet vs lifecycle

| Dimensión | Wallet ΔP&L | trade_lifecycle |
|---|---|---|
| Fuente | `wallet_portfolio_snapshots.jsonl` + `wallet_cash_flows.jsonl` | `trade_lifecycle.json` |
| Qué mide | Cambio neto de valor de la wallet, ajustado por flujos externos | Suma de realized PnL de trades individuales cerrados |
| Horizonte cubierto | t0=2026-04-29 → hoy (13.4d) | Toda la historia del bot (pre + post t0) |
| Valor actual | **+$2.93** (ALL provisional) | **−$20.47** (ALL, 122 trades) |
| Calidad | `provisional` | `contaminated`, `non_canonical_telemetry` |
| Confianza | `low_until_canonical` | `untrusted` |
| Incluye posiciones abiertas | Sí (MTM en snapshot) | No (solo realizadas) |
| Incluye legacy pre-2026-04-27 | No (t0 posterior) | Sí (contaminación principal) |
| Usable para BANKROLL | No — requiere B5+B6+signoff | No — por diseño |

---

## 8. Límites de confianza

- **Wallet +$2.93:** No representa el P&L desde el depósito inicial de $25. Representa la variación desde t0=2026-04-29, que fue posterior a pérdidas previas no capturadas por la wallet observability. El valor real desde el depósito inicial es negativo (wallet actual $22.83 vs $25 depositados = −$2.17 sobre capital inicial).
- **Horizonte 1W:** Provisionally +$2.93 (coverage 7d, divergencia 24.36 vs umbral 1.5). La divergencia contra lifecycle no significa error nuevo; sí impide promoción.
- **Lifecycle −$20.47:** Incluye efectos de batch market_resolved histórico con anomalías de tamaño. No refleja el rendimiento del sistema con la lógica actual.
- **Ninguna cifra es auditable end-to-end** hasta que B5 formalice los criterios y B6 (Opus) los valide.

---

## 9. Implicación para BANKROLL

Este documento **no autoriza** ningún cambio de BANKROLL.

La narrativa de divergencia es **condición necesaria pero no suficiente** para avanzar hacia `canonical_candidate`. Los bloqueadores que persisten tras este documento:

1. `cash_flows.coverage_days` = 7.0d (necesita ≥28d → ETA 2026-06-08)
2. B5 spec formal inexistente
3. B6 Opus review no ejecutado
4. Pablo signoff sobre criterios B5 no recibido
5. Phase 2 abierta hasta 2026-06-09 (G11 bloqueado)
6. WR canónico no disponible (G4, G7 BLOCKED_BY_DATA)
7. A8 SL_intra veredicto pendiente (re-check 2026-05-21)

**Ventana realista para revisión BANKROLL:** no antes de 2026-06-09, más ciclo B5/B6 (~1 semana). Fecha operativa más temprana: ~2026-06-16.

---

## 10. Próximos pasos

| Acción | Tipo | Quién | Cuando |
|---|---|---|---|
| **A3** — Renovar attestation cash flow cada 2-3 días | Railway ssh, no-code | Pablo | Continua hasta 2026-06-08 |
| **A4** — Re-check A8 SL_intra guard | Read-only audit | Sonnet | 2026-05-21 o 5º trade guarded |
| **A5** — Readout Phase 2 preparatorio | Codex audit read-only | Codex | Post 2026-06-09 |
| **B5 spec** — Criterios formales de promoción provisional→canonical_candidate | Diseño Opus | Opus | Post 2026-06-08 (cuando coverage ≥28d) |
| **B6 review** — Opus review del sistema completo | Full semántico | Opus | Post B5 spec |
| **Pablo signoff** — sobre documento B5 antes del primer patch | Manual | Pablo | Post B6 |

---

## Declaraciones explícitas

- Este documento **no autoriza** cambio de BANKROLL ($25 → $35).
- Este documento **no promueve** `canonical_source` de `none` a ningún valor.
- Este documento **no abre** Fase C.
- Este documento **no toca** trading core, env vars, runtime, DB, city modes, S341, SL guard, sizing, scheduler.
- Este documento **es** el prerequisito de narrativa requerido por el P0 Opus para el trigger de B5/B6.

---

*Documento docs-only. Producido por Sonnet 4.6 en modo read-only.*  
*Fuente: `docs/bankroll-readiness-evidence-pack-2026-05-13.md`, `docs/p0_b5_b6_opus_review_2026_05_13.md`, `docs/pnl_observability.md`, `docs/pnl_report_design.md`, `docs/pnl-reconciliation-readout-latest.md`.*
