# P0 — Revisión Opus B5/B6 P&L canónico / BANKROLL readiness

**Fecha:** 2026-05-13
**Agente:** Opus
**Modo:** FULL semántico / read-only
**Clasificación:** `MONETIZATION_RELEVANT / RISK_CONTROL`
**Entrada:** `docs/BACKLOG_ORI_operational_readiness_intelligence_v3_token_economics.md` §P0 + estado runtime atestado por Pablo (2026-05-12).

---

## Veredicto binario

```
KEEP_BLOCKED
NEED_MORE_RUNTIME_EVIDENCE
```

No abrir patch B5/B6 todavía. No promover `canonical_source` de `none` a ningún valor. `BANKROLL=$25` se mantiene. `$35` queda **no autorizado**. No abrir Codex como continuación de este P0.

---

## Estado de gates (snapshot 2026-05-12)

| Gate | Estado | Evidencia | Lectura Opus |
|---|---|---|---|
| **Phase 1 readiness** | `ready=true` | schema_v2, cycle_events=102, days_span=13.7, distinct_days=15, snapshots=622/622, gaps=[] | Cumple. No bloquea. |
| **Cash flow coverage** | `status=valid`, `coverage_days_7d=7.0` | `/app/data/wallet_cash_flows.jsonl`, rows=2, atestación manual 2026-05-08 → 2026-05-11, sin depósitos/retiradas | Cubre 1W. **No cubre 1M** (necesita ≥28-30d). |
| **Wallet snapshots** | OK | ≥15 días distintos | Suficiente para 1W provisional, **insuficiente para 1M canonical_candidate** (necesita ≥28 snapshots según `pnl_report_design.md` T5). |
| **pnl_report 1D** | `blocked` | `snapshot_gap_gt_2h` | Esperado por cadencia; no es bug. |
| **pnl_report 1W** | `provisional`, `value_usdc=+2.69` | — | Máximo alcanzable hoy es `provisional`; **no** puede saltar a `canonical_candidate` mientras la divergencia contra lifecycle siga abierta sin explicación documentada. |
| **pnl_report 1M** | `blocked` | `cash_flow_coverage_below_1M` | Bloqueo correcto. Hasta ~2026-06-08 no hay forma de levantarlo. |
| **pnl_report ALL** | `provisional`, `value_usdc=+2.40` | — | Mismo techo que 1W. |
| **trade_lifecycle** | `contaminated`, `realized_pnl_usdc=-18.63` | `contamination_rate=1.0` | `non_canonical_telemetry` por diseño (B3). No bloquea horizontes primarios, pero la divergencia sin diagnóstico documentado **sí** impide promoción. |
| **Divergencia 1W vs lifecycle** | `21.32 USDC` (umbral 1.5) | provisional +2.69 vs lifecycle −18.63 | Gap ~14× el umbral. Mientras no exista narrativa documentada (lifecycle contaminado por legacy batch + market_resolved antiguos), no puede usarse 1W como base canónica. |
| **canonical_source** | `none` | — | Correcto. Por diseño B3 la herramienta **nunca** puede emitir `canonical` por sí sola. |
| **bankroll_readiness** | `blocked` | `canonical_requires_B5_B6_opus_review_pablo_signoff` | Correcto. Mantener. |

---

## Respuestas a las preguntas del P0

**1. ¿Puede el P&L 1W provisional empezar a considerarse fuente canónica bajo condiciones estrictas?**
No. Aunque la cifra `+2.69 USDC` sea plausible:
- Solo hay 7d de cash-flow atestado, justo el mínimo. Una promoción canónica de 1W debería exigir colchón (≥14d limpios consecutivos sin depósitos/retiradas) para resistir un único cash-flow no detectado.
- La divergencia contra `trade_lifecycle` está 14× por encima del umbral. Aunque sea esperable por contaminación de lifecycle, **no existe documento que cierre la explicación**; sin ese cierre, la promoción carece de auditoría reproducible.
- La magnitud absoluta (+2.69 sobre $25) es del mismo orden que el ruido P&L diario observado. Una promoción aquí maximizaría riesgo de falso positivo.

**2. ¿La divergencia contra `trade_lifecycle` contaminado debe bloquear, ignorarse o investigarse aparte?**
Investigarse aparte, **no bloqueando** la operación del bot (ya es `non_canonical_telemetry`), pero **sí bloqueando** cualquier promoción a `canonical` hasta tener un documento corto que ate:
- qué fracción de `−18.63` viene de batch `market_resolved` antiguo / `legacy_unresolved` / contaminación 1.0,
- por qué la diferencia es consistente con el comportamiento histórico (Madrid −4.89, London −2.50, etc., ya visibles en `pnl-reconciliation-readout-latest.md`).
Sin este cierre, no se puede afirmar que 1W provisional sea libre de error sistemático no auditado.

**3. ¿Qué falta exactamente para que `canonical_source` deje de ser `none`?**

Mínimo accionable, en orden:

- **B5 spec formal** documentado: criterios reproducibles de promoción `provisional → canonical_candidate` (cobertura mínima, divergencia máxima permitida, ventana de attestation continua, política de re-degradación si llega cash-flow nuevo).
- **B6 Opus review** sobre el sistema completo (esta revisión P0 **no** es B6; es solo el chequeo de readiness).
- **Cobertura cash-flow** ≥28d contiguos limpios.
- **≥28 wallet snapshots** distribuidos en esos 28d (gating para 1M canonical_candidate).
- **Reconciliación documentada** de la divergencia 1W vs lifecycle (no necesita arreglar lifecycle; necesita explicar y firmar).
- **Pablo signoff explícito** sobre el documento B5 antes del primer patch de promoción.

**4. ¿Tiene sentido preparar un patch B5/B6 de promoción canónica ahora?**
No. Un patch hoy promovería contra criterios que aún no existen (B5 vacío) y sobre cobertura insuficiente. Sería tooling por tooling y abriría riesgo de promover una cifra inestable.

**5. ¿O lo correcto es mantener `KEEP_BLOCKED` hasta más snapshots/cobertura/limpieza lifecycle?**
Sí. Esta es la opción correcta. La economía de tokens favorece **dejar que el runtime acumule** y reabrir B5 con datos suficientes, en lugar de invertir tokens hoy en un diseño cuyos criterios no podrían testarse aún.

---

## Decisiones colaterales

- **No abrir Codex** como continuación inmediata de este P0. No hay patch monetizable disponible.
- **No tocar** `pnl_report.py`, `pnl_observability.md`, `pnl_clean_source_policy.md`, `wallet_snapshot.py`, `wallet_cash_flow_log.py`, `trade_lifecycle.json`.
- **No tocar** BANKROLL, sizing, whitelist, city modes, scheduler, SL, guards, env vars, DB runtime, Fase C, trading core.
- **Mantener** el bloqueo `bankroll_readiness=blocked` y `canonical_source=none`.
- **Confirmar**: `BANKROLL=$25` KEEP. `$35` no autorizado.

---

## Trigger para reabrir B5/B6 (criterio objetivo)

Reabrir esta revisión cuando **todos** se cumplan:

1. `cash_flows.coverage_days` ≥ 28d contiguos `valid` sin gaps.
2. `wallet_snapshots` ≥ 28 distribuidos en esos 28d.
3. Divergencia `1W` vs `trade_lifecycle` **explicada en un documento corto** (no es necesario que el número baje, sí que esté narrativamente reconciliado).
4. Pablo confirma que está dispuesto a entrar al ciclo B5 (diseño de criterios → patch → Opus B6 → signoff).

Estimado calendario: no antes de **2026-06-08** (28d desde el primer cash-flow valid 2026-05-08).

Hasta entonces este P0 queda en `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`.

---

## Siguiente tarea recomendada del backlog

`P1 — Codex — Readout unificado lifecycle + Hazard + INTRA-REEVAL` (NORMAL, read-only, sin Opus).

Razón: es la tarea inmediatamente siguiente compatible con Codex; produce evidencia interpretable de casos Seoul/Singapore sin tocar trading core. Su entrega además es input útil cuando, más adelante, haya que reconciliar la divergencia 1W vs lifecycle para B5.

---

## Confirmaciones finales

- BANKROLL: **no tocado** (KEEP $25).
- Fase C: **no tocada**.
- Trading core: **no tocado**.
- Env vars Railway: **no tocadas**.
- DB runtime: **no tocada**.
- Sizing / whitelist / city modes / scheduler / SL / guards: **no tocados**.

Worktree esperado: solo este documento nuevo en `docs/` + entry en `HISTORIAL_SESIONES.md` si Pablo decide registrar.
