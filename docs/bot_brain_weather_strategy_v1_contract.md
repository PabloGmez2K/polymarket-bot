# BOT_BRAIN_WEATHER_STRATEGY_DECISION_LAYER_V1 — Codex Contract

**Workstream:** `BOT_BRAIN_WEATHER_STRATEGY_DECISION_LAYER_V1`
**Status:** APPROVED_DESIGN — awaiting Codex CODE phase (not yet implemented)
**Date:** 2026-05-27
**Approver:** Pablo
**Mode:** DOCS-ONLY. No code, no runtime, no Railway writes, no env vars.

---

## 1. Decisión estratégica

- El nicho Polymarket Weather **no se abandona**.
- No se autoriza todavía: microfase, hold-to-resolution, reactivación de cohorts, ni cambios live.
- Objetivo: Bot Brain produce una **decisión weather reproducible desde evidencia existente**, sin que Pablo necesite pegar su dashboard manualmente.
- BANKROLL `$25 HOLD`. `$35` no autorizado.
- Fase C no autorizada. `SHADOW_EXACT_NO_GLOBAL` no se levanta. `SHADOW_ONLY_MODE` no se activa. `price_out_of_range` no se relaja.

---

## 2. Entry point y arquitectura aprobada

```powershell
python tools/bot_brain.py --scope weather_strategy
```

- **Un único entry point público.** No se crea un segundo CLI independiente.
- Se permite helper privado importado por `bot_brain.py` si evita monolito y duplicación.
- Modificación **acotada** de `tools/bot_brain.py` + helper privado si aplica.
- V1 estrictamente **read-only**.
- No `bot.py`, no env vars, no Railway writes, no Telegram, no Truth Pipeline backfill, no packet state file.
- No tocar: exits, SL, sizing, whitelist, scheduler, city modes, trading core.

---

## 3. Capacidades mínimas obligatorias de V1

### 3.1 `WEATHER_EXPERIMENT_REGISTRY`

Inventario mínimo de experimentos activos. Para cada línea: estado, trigger conocido, si está `accumulating / blocked / ready / gap` y qué decisión podría desbloquear.

Experimentos que deben aparecer:

| Clave | Descripción mínima |
|---|---|
| `PHASE_2` | Estado machine-readable si existe; emitir gap si no hay fuente legible por máquina |
| `SURVIVING_COHORTS_BY_SIDE` | Estado actual por side |
| `DIRECTIONAL_NO_FORWARD` | Calibración forward pasiva de señales `directional NO` (`at_or_above` / `at_or_below`), separada de `exact/NO`. No autoriza promoción live; `SHADOW_EXACT_NO_GLOBAL` sigue protegiendo exact/NO. Ver decision_exact_no_global_shadow_2026_05_26 y experiment_canary_exact_no_design_2026_05_17 |
| `PRICE_FILTER_COUNTERFACTUAL` | Estado LOG_ONLY, sin promoción live aún |
| `DENVER_KBKF` | Fuente alineada KBKF (commit 1421035); verificar si acumula correctamente |
| `TRADERS_INTELLIGENCE` | Trader-vs-bot gap alarm; ver trader_vs_bot_gap_alarm_severity_2026_05_21 |
| `PNL_BANKROLL` | Estado canonical_source; ver sección 5 |
| `EXITS_SL` | SL_intra guard v10.6.40; ver session_254_sl_intra_guard_v10_6_40 |

Regla: **No recomputar Phase 2** si no existe estado machine-readable; emitir `DATA_GAP`.

### 3.2 `TRADE_TRUTH_LEDGER`

Join read-only de trade / evaluation / outcome / provenance cuando sea reconstruible desde artefactos locales:

- `data/trade_lifecycle.json`
- `data/bot_signal_evaluations.jsonl`
- `data/blocked_signals_resolutions.jsonl`
- `data/cycles_history.jsonl`

Nota: `data/runtime_import` es fixture de desarrollo (`eligible_for_learning=false`). No es evidencia final para producción. Cualquier veredicto de estrategia o live debe usar snapshot fresco read-only obtenido desde Railway `/app/data/...` mediante `tools/railway_safe.ps1`.

Reglas:

- Distinguir **evidencia diagnóstica** de **evidencia elegible para live**.
- Clasificar o marcar `UNRESOLVED` los trades con P&L / outcome / identity no reconciliables. Una fila marcada `UNRESOLVED` en el ledger debe propagarse al `WEATHER_STRATEGY_VERDICT_PACKET` como `TRUTH_GAP_BLOCKS_DECISION` (si bloquea la decisión global) o `INSUFFICIENT_EVIDENCE` (si solo reduce el conjunto elegible), según corresponda.
- `identity_available` ≠ `joined_evidence` ≠ `temporally_aligned` ≠ `outcome_resolved`. No elevar `CONFIRMED_MISSED_OPPORTUNITY` sin los cuatro verificados.

### 3.3 `EPOCH_AND_REGIME_ATTRIBUTION`

- No afirmar cambio de régimen de mercado si bugs, source mismatch o gates/policies pueden explicar el drawdown.
- Si falta manifest durable de epochs en V1, emitir `EPOCH_MANIFEST_GAP`; no inventarlo ni generarlo automáticamente.
- No crear manifest de policy epochs en V1; el sistema debe funcionar **degradando con gap explícito**.

### 3.4 `WEATHER_STRATEGY_VERDICT_PACKET`

Salida global read-only. `LIVE_POLICY_ELIGIBLE=false` hardcodeado en V1.

Veredictos diagnósticos permitidos en V1:

```
KEEP_ACCUMULATING_UNTIL_TRIGGER
TRUTH_GAP_BLOCKS_DECISION
EXIT_POLICY_DESIGN_CANDIDATE
COHORT_REVIEW_CANDIDATE
INSUFFICIENT_EVIDENCE
```

**Nunca autoejecuta ni autoriza live.**

---

## 4. Provenance y P&L

- `ALPHA_SIGNAL_SUPPORTED_DIAGNOSTICALLY` no equivale a settlement oficial.
- NOAA / Open-Meteo / postmortem pueden aportar diagnóstico; **no se promocionan automáticamente a verdad live**.
- `polymarket_api_pnl` es external observability / cross-check, **nunca canonical source**.
- Con estado actual `canonical_source=none`, el packet debe emitir:
  - `P&L_CANONICAL_CONFIRMED=false`
  - `LIVE_POLICY_ELIGIBLE=false`
- Truth Pipeline y Phase 2 deben aparecer como **gaps explícitos** cuando no puedan aportar verdad machine-readable.

---

## 5. Caso Madrid — test obligatorio

- Madrid 32°C NO debe figurar como acceptance case de reconciliación.
- El snapshot local inspeccionado por Opus (May 21) **no se considera evidencia final de producción**.
- Test sintético obligatorio: cuando se pide May 25 y solo existe May 21, el `TRADE_TRUTH_LEDGER` debe clasificar esa fila como `UNRESOLVED_PNL_DISCREPANCY` con `nearest_match`. Esa clasificación de fila debe propagarse al `WEATHER_STRATEGY_VERDICT_PACKET` global: si bloquea la decisión de estrategia → `TRUTH_GAP_BLOCKS_DECISION`; si solo reduce la muestra elegible → `INSUFFICIENT_EVIDENCE`. El packet no puede emitir un veredicto positivo de estrategia ignorando filas `UNRESOLVED`.
- Smoke runtime posterior obligatorio: verificar contra snapshot fresco read-only de Railway (`tools/railway_safe.ps1 ssh "cat /app/data/<archivo>"`) si May 25 existe realmente y clasificar según datos autoritativos.
- **No hardcodear** que Madrid May 25 no existe en producción.

---

## 6. Tests requeridos (Codex CODE phase)

Los tests deben cubrir:

1. V1 siempre retorna `LIVE_POLICY_ELIGIBLE=false` (no-live invariant).
2. Provenance: `ALPHA_SIGNAL_SUPPORTED_DIAGNOSTICALLY` no eleva a settlement oficial.
3. Gaps: `EPOCH_MANIFEST_GAP` y `DATA_GAP` cuando faltan fuentes machine-readable.
4. Registry mínimo: los 8 experimentos de la tabla 3.1 aparecen en el output.
5. Ledger unresolved: trade con outcome no reconciliable → marcado `UNRESOLVED`.
6. Verdict global: packet incluye `P&L_CANONICAL_CONFIRMED`, `LIVE_POLICY_ELIGIBLE` y al menos un veredicto diagnóstico.
7. Madrid sintético: solicitud May 25 con solo May 21 disponible → `UNRESOLVED_PNL_DISCREPANCY` con `nearest_match`.

Tests de cobertura mínima — **no solo filas escritas en artefacto**; medir llamadas reales al compute/hook.

---

## 7. Archivos candidatos para CODE phase

| Archivo | Operación |
|---|---|
| `tools/bot_brain.py` | Añadir `--scope weather_strategy` + orquestar helper |
| `tools/_weather_strategy_engine.py` | Helper privado (nuevo, si evita monolito) |
| `tests/test_bot_brain_weather_strategy.py` | Tests focales (nuevo) |

No crear todavía `data/policy_epochs_manifest.json` ni ningún state file.

---

## 8. Flujo de aprobación posterior

1. **Codex CODE** solo tras aprobación explícita de Pablo en sesión nueva.
2. Codex implementa, testea y valida; **no decide semántica de trading/riesgo**.
3. Antes de push/deploy: `python verify_before_deploy.py`.
4. No push hasta autorización explícita de Pablo.
5. Smoke read-only de Railway: `tools/railway_safe.ps1 ssh "cat /app/data/<archivo>"` — lectura read-only de `/app/data/...` en Railway. Usar antes de considerar V1 completo. El packet puede desarrollarse y probarse con snapshots temporales locales; cualquier veredicto estratégico o live requiere snapshot fresco obtenido así.

---

## Referencias de memoria y docs relacionados

- `docs/bot_brain_v0.md` — v0 implementado (scope overview/city/cycle/eval_key/match_key)
- `docs/pnl_report_design.md` — B3 P&L report design (Opus, 2026-05-06)
- `memory/decision_canary_exact_no_design_2026_05_17.md`
- `memory/trader_vs_bot_gap_alarm_severity_2026_05_21.md`
- `memory/session_254_sl_intra_guard_v10_6_40.md`
- `memory/universe_recovery_decision_2026_05_26.md`
- `memory/sl_intra_post_fix_still_bleeds_2026_04_26.md`
