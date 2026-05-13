# BACKLOG ORI — Operational Readiness & Intelligence

**Proyecto:** Polymarket Bot
**Fecha:** 2026-05-12 (revisado 2026-05-13)
**Versión:** v3 token-economics / agent-driver
**Ruta canónica:** `docs/BACKLOG_ORI_operational_readiness_intelligence.md`
**Uso:** cola operativa para Claude Code / Codex / Opus con gates de prioridad, ahorro de tokens y autonomía controlada.

## Estado de la cola (2026-05-13)

- **P0 — CERRADO.** Veredicto Opus: `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`. Cierre en [docs/p0_b5_b6_opus_review_2026_05_13.md](p0_b5_b6_opus_review_2026_05_13.md). BANKROLL **$25 KEEP**, **$35 no autorizado**. **No reabrir** hasta cumplir triggers: ≥28d `cash_flow` valid contiguo + ≥28 wallet snapshots + divergencia 1W vs `trade_lifecycle` reconciliada en documento corto + Pablo dispuesto a iniciar ciclo B5. Calendario estimado: **no antes de 2026-06-08**.
- **P1 — CERRADO 2026-05-13.** Readout unificado lifecycle + Hazard + INTRA-REEVAL implementado en `tools/sl_intra_case_readout.py`, desplegado y smokeado contra `/app/data`.
- **P2 — CERRADO 2026-05-13.** `NO_ACTION operativo / REPORTING_GAP menor`: `/app/data/alerts_state.json` ya tiene `intra_reeval_review_alert_sent=true`; `shadow_log.review_alert_sent=false` en `intra_reeval_state.json` no es autoritativo.
- **P3 — CERRADO 2026-05-13.** `KEEP_MONITORING`: no patch sin muestra post-guard mayor o decisión Opus.
- **P5 — CERRADO 2026-05-13.** Veredicto Opus: `KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER`; revisión obligatoria **2026-06-09** o antes solo si se cumplen triggers documentados de Phase 2.
- **P4 Los Angeles** y **P6 Blocked signals**: `WATCH`.
- **M0**: manual recurrente cuando haya `signals.json` fresco.
- **Estado ORI:** cola activa cerrada; queda solo vigilancia residual P4/P6 y rutina manual M0.

---

## 0. Objetivo del backlog

Este backlog no es una lista abierta de ideas. Es una cola de trabajo orientada a:

1. Desbloquear decisiones monetizables con evidencia.
2. Mejorar P&L canónico y readiness de BANKROLL.
3. Aumentar inteligencia operativa del bot sin activar ejecución prematura.
4. Reducir gasto de tokens evitando revisiones minuciosas que no cambian decisiones.
5. Permitir que un agente trabaje varias tareas compatibles en una misma sesión sin pedir prompts nuevos.

---

## 1. Principio rector

No hacer tooling por tooling.

Una tarea solo merece sesión si puede cambiar al menos una de estas cosas:

- P&L interpretable.
- BANKROLL readiness.
- throughput real.
- calidad de señales.
- control de riesgo.
- bug runtime.
- decisión operativa futura.

Si una tarea probablemente acaba en `KEEP`, `WATCH`, `WAITING_EVIDENCE` o `NO_ACTION`, cerrarla con diagnóstico mínimo y no expandir.

---

## 2. Reglas token-economics

### 2.1 Clasificación obligatoria antes de trabajar

Cada tarea debe clasificarse al inicio:

- `ACTION_NOW`
- `MONETIZATION_RELEVANT`
- `RISK_CONTROL`
- `WATCH_ONLY`
- `DEFER_STOP`

### 2.2 Gates de gasto

| Clasificación | Acción |
|---|---|
| `ACTION_NOW` | Trabajar ahora. Puede justificar patch si no toca semántica sensible. |
| `MONETIZATION_RELEVANT` | Trabajar si mueve P&L, throughput, BANKROLL o calidad de trades. |
| `RISK_CONTROL` | Trabajar con guardrails; Opus si implica semántica ejecutable. |
| `WATCH_ONLY` | No abrir sesión larga; cerrar con veredicto y trigger futuro. |
| `DEFER_STOP` | No trabajar. Documentar solo si cambia el roadmap. |

### 2.3 Stop conditions

Parar la sesión y entregar cierre si aparece cualquiera:

- Hace falta decisión Opus.
- Hace falta confirmación literal de Pablo.
- La tarea deriva a `BANKROLL`, sizing, whitelist, city modes, scheduler, SL ejecutable, guards o Fase C.
- Se detecta contradicción runtime crítica.
- El worktree queda sucio fuera del scope.
- El agente necesita leer demasiados archivos sin haber acotado pregunta.
- La siguiente acción sería “seguir investigando” sin cambiar veredicto.

### 2.4 Budget máximo por tarea

El agente debe intentar cerrar cada tarea con el mínimo contexto:

- Preflight corto.
- Lectura de archivos directamente relevantes.
- Evidencia mínima.
- Veredicto.
- Siguiente acción.

No hacer auditoría global salvo que el backlog lo pida.

---

## 3. Autonomía permitida en una misma sesión

El agente puede hacer varias tareas en una sola sesión si se cumplen todas:

1. Tienen el mismo modo de riesgo.
2. No requieren Opus.
3. No tocan trading core semántico.
4. No cambian env vars.
5. No escriben DB runtime.
6. No cambian BANKROLL/Fase C.
7. El worktree queda limpio o con cambios versionados intencionales.
8. Cada tarea termina con veredicto claro antes de pasar a la siguiente.

### Agrupaciones permitidas

#### Lote LOG_ONLY / reporting

Puede agrupar:

- `P1` readout lifecycle + Hazard + INTRA-REEVAL.
- `P2` diagnóstico `review_alert_sent=false`, si primero queda claro que no requiere cambio ejecutable.

#### Lote WATCH read-only

Puede agrupar:

- Los Angeles recurrence check.
- DB Throughput watch.
- Blocked signals watch.

Solo si el objetivo es cerrar `NO_ACTION/WATCH`, no abrir diseño.

### Agrupaciones prohibidas

No mezclar en la misma sesión:

- `P0 BANKROLL/P&L` con tareas de SL/INTRA.
- Decisiones de whitelist/city modes con patches de reporting.
- Env vars Railway con cambios de código.
- Trading core con documentación.
- Fase C con cualquier otro bloque.

---

## 4. Agentes y modos

### Opus

Usar para:

- BANKROLL.
- P&L canónico.
- riesgo.
- SL/INTRA semántico.
- city modes / whitelist / canary.
- decisiones de promoción.
- Fase C.
- cambios que puedan alterar BUY/SELL/SKIP.

### Codex

Usar para:

- patches acotados.
- CLIs read-only.
- tests.
- verify_before_deploy.py.
- reportes LOG_ONLY.
- checks técnicos.
- Railway read-only si está documentado.

### Sonnet

Usar para:

- síntesis.
- docs.
- diseño read-only no sensible.
- cierres.
- preparar prompts.
- auditorías ligeras.

---

## 5. Guardrails globales

No cambiar sin autorización explícita:

- `BANKROLL`.
- Fase C.
- Truth Pipeline ejecutable.
- `bot.py` trading core semántico.
- sizing.
- whitelist.
- city modes.
- scheduler.
- guards / SL ejecutables.
- reglas BUY/SELL/SKIP.
- env vars Railway.
- DB schema.
- datos runtime, salvo comandos read-only/LOG_ONLY claramente autorizados.

Railway:

- Usar siempre:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ...
  ```
- Solo read-only salvo confirmación explícita.
- Si hay push a `main`, observar Railway hasta `SUCCESS/FAILED`.

Git:

- Antes y después:
  ```powershell
  git status --short --untracked-files=all
  git log -1 --oneline
  ```
- El untracked `2026-04-27]` es preexistente; no tocar.
- No commit/push si no hay cambios versionados.
- Si se hace commit, mensaje claro y cierre con hash.

---

## 6. Estado operativo actual

### 6.1 BANKROLL / P&L

Revisión manual reciente:

- `phase1_readiness_check.py` ejecutado en Railway contra `/app/data/polymarket.db`.
- Resultado:
  - `schema_version=2`
  - `cycle_events.total=102`
  - `days_span=13.7`
  - `distinct_days=15`
  - `market_snapshots=622`
  - `forecast_snapshots=622`
  - `gaps=[]`
  - `readiness.ready=true`

Cash flow:

- `/app/data/wallet_cash_flows.jsonl`
- `rows=2`
- `status=valid`
- `coverage_days_7d=7.0`
- Pablo confirmó y se atestó manualmente:
  - `2026-05-08T08:01:04.117648Z → 2026-05-11T08:00:53Z`
  - sin depósitos, retiradas ni otros cash flows externos de Polymarket.

`pnl_report.py --data-dir /app/data --json`:

- `bankroll_readiness=blocked`
- `canonical_source=none`
- `1W.status=provisional`
- `1W.value_usdc=+2.69`
- `ALL.status=provisional`
- `ALL.value_usdc=+2.40`
- `1D` bloqueado por `snapshot_gap_gt_2h`
- `1M` bloqueado por `cash_flow_coverage_below_1M`
- `trade_lifecycle.status=contaminated`
- `trade_lifecycle.realized_pnl_usdc=-18.63`
- `1W.divergence_actual_usdc=21.32 > threshold 1.5`
- Bloqueo principal:
  - `canonical_requires_B5_B6_opus_review_pablo_signoff`

Conclusión:

- `BANKROLL $25`: mantener.
- `$35`: no autorizado.
- Siguiente gate real: revisión B5/B6 con Opus.

---

### 6.2 SL / INTRA / Hazard — Seoul y Singapore

Caso revisado manualmente:

- Singapore 32°C May12 NO.
- Seoul 21°C May12 NO.

Archivos donde queda evidencia:

- `/app/data/trade_lifecycle.json`
- `/app/data/sl_intra_hazard_monitor_audit.json`
- `/app/data/intra_reeval_state.json`
- `/app/data/sl_intra_guard_audit.json`
- `/app/data/skip_log.jsonl`

Conclusión:

- El sistema sí almacena evidencia.
- No ejecutar venta fue correcto en estos casos.
- No tocar SL ni activar INTRA-REEVAL real con esta muestra.
- Gap útil: falta readout unificado que una lifecycle + hazard + intra_reeval + outcome final.

---

### 6.3 Los Angeles trader-vs-bot gap

Revisión manual posterior:

- Aparece gap operativo:
  - Los Angeles: 2 señales, consenso=2, WR max 80%.
- Pero el summary indica:
  - serie todavía corta; no hay base suficiente para decidir.

Conclusión:

- `WATCH_DIAGNOSTIC`.
- No P1.
- No Codex todavía salvo repetición clara en próximas corridas.
- No whitelist/canary.
- No Opus todavía.

---

## 7. Cola priorizada

---

# P0 — Opus — Revisión B5/B6 de P&L canónico y BANKROLL readiness — **CERRADO 2026-05-13**

**Clasificación:** `MONETIZATION_RELEVANT / RISK_CONTROL`
**Agente:** Opus
**Modo:** FULL semántico/read-only
**Prioridad:** Alta
**Estado:** **CERRADO 2026-05-13** — `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`
**Cierre:** [docs/p0_b5_b6_opus_review_2026_05_13.md](p0_b5_b6_opus_review_2026_05_13.md)
**Batch:** no mezclar con otras tareas.

## Resultado

- **Veredicto:** `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`.
- `canonical_source=none` y `bankroll_readiness=blocked` se mantienen.
- `BANKROLL=$25` KEEP. `$35` **no autorizado**.
- No abrir patch B5/B6 ni Codex como continuación inmediata de P0.

## Triggers para reabrir (todos deben cumplirse)

1. `cash_flows.coverage_days` ≥ 28d contiguos `valid` sin gaps.
2. `wallet_snapshots` ≥ 28 distribuidos en esos 28d.
3. Divergencia 1W vs `trade_lifecycle` reconciliada en documento corto (no requiere que el número baje; sí narrativa firmada).
4. Pablo confirma disposición a iniciar el ciclo B5 (diseño criterios → patch → B6 Opus → signoff).

**Calendario estimado: no antes de 2026-06-08.** Hasta entonces P0 no se reabre.

---

## Sección original (referencia histórica)

## Objetivo

Decidir si el P&L provisional basado en `wallet_snapshot + cash_flow_log` puede avanzar hacia fuente canónica, o si BANKROLL debe seguir bloqueado hasta más evidencia.

## Preguntas

- ¿Puede el P&L 1W provisional empezar a considerarse fuente canónica bajo condiciones estrictas?
- ¿La divergencia contra `trade_lifecycle` contaminado debe bloquear, ignorarse o investigarse aparte?
- ¿Qué falta exactamente para que `canonical_source` deje de ser `none`?
- ¿Tiene sentido preparar un patch B5/B6 de promoción canónica?
- ¿O lo correcto es mantener `KEEP_BLOCKED` hasta más snapshots/cobertura/limpieza lifecycle?

## Veredicto esperado

Una opción:

- `KEEP_BLOCKED`
- `READY_FOR_CANONICAL_PROMOTION_PATCH`
- `READY_FOR_MANUAL_BANKROLL_REVIEW`
- `NEED_MORE_RUNTIME_EVIDENCE`
- `BUG_OR_SEMANTIC_GAP_FOUND`

## Entrega esperada

- Veredicto binario.
- Estado de gates:
  - Phase 1
  - cash flow coverage
  - wallet snapshots
  - pnl_report
  - trade_lifecycle divergence
  - canonical_source
  - bankroll_readiness
- Decidir si abrir Codex después.
- Prompt corto para Codex si procede.
- Confirmación explícita:
  - `BANKROLL $25` se mantiene.
  - `$35` no queda autorizado salvo revisión separada.

---

# P1 — Codex — Readout unificado lifecycle + Hazard + INTRA-REEVAL

**Clasificación:** `MONETIZATION_RELEVANT / LEARNING_EVIDENCE`  
**Agente:** Codex  
**Modo:** NORMAL  
**Prioridad:** Alta-media  
**Estado:** **CERRADO 2026-05-13** — `NO_EXISTING_TOOL_PATCH_READY` implementado, desplegado y smoke runtime OK  
**Batch compatible:** puede agruparse con P2 solo si P2 queda read-only/reporting.

## Resultado 2026-05-13

- Tool: `tools/sl_intra_case_readout.py`.
- Commits:
  - `5adc6d6` `feat: add sl intra case readout`
  - `b6b2ead` `fix: classify intra reeval shadow losses`
  - `ffec13b` `fix: prefer resolved action in case readout`
- Deploy Railway final observado: `61528517-88df-44f9-b0cc-b2da0be6f955` → `SUCCESS`.
- Smoke read-only runtime:
  - Seoul 21°C May12 NO: `status=ok`, `case_count=1`, lifecycle + Hazard + guard + INTRA-REEVAL presentes, `would_sell=true`, tiers `deep/deteriorating/terminal`, `max_drawdown=-94.26`, final runtime `LOSS_TOTAL`, `pnl_cash=-2.34`, clasificación `REEVAL_GOOD_SHADOW`.
  - Singapore 32°C May12 NO: `status=ok`, `case_count=1`, lifecycle + Hazard + guard presentes, tiers `deep/terminal`, `max_drawdown=-95.1`, final `RESOLVED_WIN`, `pnl_cash=+1.92`, clasificación `HAZARD_OBSERVED_WIN`.
- Guardrails confirmados: no P0, no BANKROLL, no Fase C, no `bot.py`, no trading core, no SL/guards/INTRA ejecutable, no city modes, no whitelist, no scheduler, no env vars, no DB runtime writes, no Telegram real.

## Objetivo

Crear o diseñar un reporte read-only que una la evidencia repartida entre:

- `trade_lifecycle.json`
- `sl_intra_hazard_monitor_audit.json`
- `intra_reeval_state.json`
- `sl_intra_guard_audit.json`
- `skip_log.jsonl`

## Problema

El sistema sí guarda la evidencia, pero para entender un caso concreto hay que hacer grep manual en varios archivos.

## Resultado deseado

Un CLI/report, por ejemplo:

```powershell
python tools/sl_intra_case_readout.py --data-dir /app/data --city Seoul --date 2026-05-12 --json
python tools/sl_intra_case_readout.py --data-dir /app/data --token-id <token> --markdown
```

Nombre orientativo; Codex puede proponer otro si encaja mejor.

## Campos deseados

- token_id
- city
- title/question
- condition
- date
- side
- buy_count
- total_amount
- avg_entry_price
- entry edge
- latest entry edge
- trader_confirmed
- hazard tiers detectados
- max drawdown observado
- intra_reeval `would_sell`
- price at would_sell
- edge_now vs edge_entry
- final status
- close_action
- close_reason
- real PnL cash
- real PnL pct
- clasificación:
  - `HAZARD_OBSERVED_WIN`
  - `REEVAL_WOULD_SELL_BUT_FINAL_WIN`
  - `HAZARD_OBSERVED_LOSS`
  - `REEVAL_GOOD_SHADOW`
  - `REEVAL_BAD_SHADOW`
  - `STILL_OPEN`
  - `INSUFFICIENT_DATA`

## Casos de prueba

- Singapore 32°C May12 NO:
  - L2 deep/terminal
  - max drawdown aprox `-95.1%`
  - final `RESOLVED_WIN`
  - `pnl_cash=+1.92`

- Seoul 21°C May12 NO:
  - INTRA-REEVAL `would_sell=true` a `-80.3%`
  - L2 deep/terminal
  - final `RESOLVED_WIN`
  - `pnl_cash=+1.52`

## Guardrails

- Read-only.
- No modificar runtime.
- No escribir DB.
- No cambiar `trade_lifecycle`.
- No cambiar SL/guards/INTRA-REEVAL.
- No Telegram real.
- No BANKROLL.
- No Fase C.
- No BUY/SELL/SKIP.

## Veredicto esperado

- `NO_EXISTING_TOOL_PATCH_READY`
- `EXISTING_TOOL_SUFFICIENT`
- `REPORT_DESIGN_ONLY`
- `STOP_NEEDS_OPUS`

---

# P2 — Codex read-only — Verificar `review_alert_sent=false` en INTRA-REEVAL

**Clasificación:** `WATCH_RISK / OBSERVABILITY`  
**Agente:** Codex  
**Modo:** NORMAL read-only primero  
**Prioridad:** Media  
**Estado:** CERRADO 2026-05-13
**Batch compatible:** P1, solo si no requiere cambio ejecutable.

## Contexto

En `/app/data/intra_reeval_state.json`:

- `first_trigger_at=2026-04-24T01:30:26Z`
- `last_telegram_at=2026-05-12T04:59:26Z`
- `review_alert_sent=false`

Hay que confirmar si:

1. Es esperado porque faltan resoluciones/casos clasificables.
2. Es esperado porque la review se calcula en otro sitio.
3. Hay un gap de reporting.
4. Hay un bug de scheduler/trigger.

## Veredicto esperado

- `EXPECTED_WAIT`
- `REPORTING_GAP`
- `BUG_PATCH_READY`
- `NO_ACTION`

## Cierre 2026-05-13

Veredicto: `NO_ACTION operativo / REPORTING_GAP menor`.

Evidencia:

- `/app/data/alerts_state.json` contiene `intra_reeval_review_alert_sent=true`.
- El campo `shadow_log.review_alert_sent=false` en `intra_reeval_state.json` no es autoritativo; la idempotencia real de la review vive en `alerts_state`.
- No hay bug de scheduler actual.

Siguiente: P3 queda solo como `WATCH_RISK / triage`.

## Guardrails

- Read-only primero.
- No activar ventas.
- No cambiar `INTRA_REEVAL_ENABLED`.
- No cambiar `INTRA_REEVAL_SHADOW_MODE`.
- No tocar env vars.
- No Telegram real.

---

# P3 — Opus / Codex read-only — SL Retrospective cohort review post-guard

**Clasificación:** `RISK_CONTROL / WATCH_RISK`  
**Agente:** Opus si se interpreta semántica; Codex si solo se audita reporte  
**Modo:** NORMAL/FULL según alcance  
**Prioridad:** Media-baja  
**Estado:** WATCH / triage read-only 2026-05-13
**Batch:** no abrir salvo nueva alarma o si P1 revela métrica accionable.

## Contexto

SL Retrospective muestra:

- falsas salidas: 39%
- correctos: 61%
- ciclo principal con 62% falsas salidas
- intra-ciclo con 27% falsas salidas
- config post-guard v10.6.40:
  - n=7, falsas=3, correctos=3, pendientes=1

## Lectura actual

No tocar SL ejecutable.

Motivos:

- histórico mezclado F1+F2+F3
- muestra post-guard pequeña
- `mejor precio visto después` no equivale automáticamente a estrategia realizable
- Seoul/Singapore recientes muestran que ventas shadow por drawdown extremo habrían sido malas

## Veredicto esperado

- `KEEP_MONITORING`
- `REPORTING_PATCH_READY`
- `ESCALATE_OPUS_RISK_DECISION`
- `NO_ACTION`

## Triage Codex 2026-05-13

Veredicto: `KEEP_MONITORING`.

Evidencia minima:

- El bloque actual ya separa la config post-guard v10.6.40 y la muestra sigue pequena (`n=7`, `resueltos=6`, `pendientes=1`).
- `tools/sl_retrospective.py` ya tiene bloque de config actual post-guard y veredicto de muestra insuficiente / zona gris antes de sacar conclusiones.
- Cualquier cambio de SL ejecutable o interpretacion de si una falsa salida era estrategicamente realizable requiere decision semantica de Opus.

No patch. No cambiar SL/guards. Reabrir solo con muestra post-guard mayor o nueva alarma.

Prompt corto para Opus si se reabre: "Revisar P3 SL Retrospective post-guard: con muestra F3 actualizada, decidir si la tasa de falsas salidas justifica cambio semantico de SL o si se mantiene monitorizacion; no tocar BANKROLL/Fase C sin evidencia separada."

---

# P4 — WATCH_DIAGNOSTIC — Los Angeles trader-vs-bot recurrence check

**Clasificación:** `WATCH_DIAGNOSTIC`  
**Agente:** ninguno por defecto  
**Prioridad:** Baja hasta repetición  
**Estado:** no abrir aún  
**Batch:** puede revisarse en lote WATCH.

## Contexto

El cross-check mostró:

- Los Angeles: 2 señales.
- Consenso=2.
- WR max 80%.
- Pero la serie todavía es corta y no hay base suficiente para decidir.

## Trigger para subir a P1

Abrir auditoría Codex read-only solo si se repite en próximas 2-3 corridas con:

- consenso >= 2
- condición operable
- fuera de blocked
- no explicado por price/date/stale
- persistencia en `TRADER_ONLY`

## Veredicto esperado si se abre

- `NO_CHANGE_SOURCE_EXPLAINED`
- `BACKLOG_WHITELIST_CANARY_REVIEW`
- `BLOCKED_BY_SOURCE_OR_NOAA`
- `BUG_PATCH_READY`
- `NEED_OPUS_CITY_POLICY_DECISION`

## Guardrails

- No whitelist.
- No canary.
- No city mode changes.
- No trading core.

---

# P5 — Opus posterior — DB Throughput slots/condition mix strategy — **CERRADO 2026-05-13**

**Clasificación:** `MONETIZATION_RELEVANT / STRATEGY_WATCH`  
**Agente:** Opus  
**Modo:** diseño/read-only  
**Prioridad:** Baja-media  
**Estado:** cerrado por Opus — `KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER`

## Contexto

DB Throughput LOG_ONLY:

- `REVIEW_READY`
- gaps=0
- slots flojos:
  - 12h: 166 eval / 0 buys
  - 09h: 107 eval / 0 buys
  - 15h: 31 eval / 0 buys
- condición dominante:
  - exact `447/631`

## Lectura actual

No es bug inmediato.

Puede apuntar a:

- mala mezcla de condiciones
- slots con poco valor
- necesidad de revisar exact/range filtering
- city modes o horario de escaneo

Cualquier cambio de estrategia requiere Opus.

## Veredicto

Opus cierra P5 como `KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER`.

No cambiar slots, condition mix, city modes, whitelist ni scheduler por este backlog. La estrategia actual se mantiene hasta el primer trigger aplicable:

- **Revisión obligatoria:** 2026-06-09 (T+30 de Phase 2 Recalibration).
- **Rollback temprano mixed-condition:** WR mixed-condition <40% con n>=20 trades cerrados.
- **Rollback temprano exact-slice:** WR exact <40% con n>=10 trades cerrados.
- **Review T+30:** n mixed-condition >=25, WR mixed-condition >=45%, PnL absoluto >=+$5, drawdown maximo no peor que -$6, al menos 2/4 ciudades Active con n>=3 y WR>=40%, y slice exact n>=10 con WR>=45%.
- **Si falla cualquier criterio T+30:** `RECOMMEND_KILL_MODEL_PATH` / pivot leaderboard intelligence.

---

# P6 — WATCH_AUDIT — Blocked signals Beijing / OUT whitelist

**Clasificación:** `WATCH_AUDIT`  
**Agente:** ninguno por defecto  
**Prioridad:** Baja  
**Estado:** no accionable

## Contexto

Blocked signals daily audit:

- OUT whitelist WR 97.6%
- Beijing top candidato
- settlement unknown/unverified 100%
- v2 OUT resolved <50

## Lectura

No autoriza trading.

Solo abrir tarea si:

- Beijing aparece con consenso trader real
- fuente/resolution coverage queda clara
- Opus/Pablo decide evaluar ciudad nueva

---

# M0 — Manual sin agente — Traders Intelligence snapshots

**Clasificación:** `WATCH_ONLY / DATA_ACCUMULATION`  
**Agente:** ninguno  
**Prioridad:** continua  
**Estado:** manual

## Acción

Cuando haya `signals.json` fresco:

```powershell
cd C:\Projects\polymarket-bot
python tools/traders_intelligence_snapshot.py
git status --short --untracked-files=all
```

## Guardrails

- No trading core.
- No NOAA.
- No policy.
- No BANKROLL.
- No Fase C.
- No interpretar como señal ejecutable.

---

## 8. Driver prompt único para VS Code

Pegar este prompt al agente dentro de VS Code / Claude Code / Codex:

```text
Trabaja como agente del repo C:\Projects\polymarket-bot usando docs/BACKLOG_ORI_operational_readiness_intelligence.md como cola de tareas y fuente de prioridad.

Objetivo: avanzar el máximo posible en esta sesión sin gastar tokens en tareas WATCH/NO_ACTION y sin mezclar riesgos.

Primero:
1. Ejecuta git status --short --untracked-files=all y git log -1 --oneline.
2. Lee ORCHESTRATOR.md, AGENTS.md y el backlog ORI.
3. Lee solo los documentos adicionales necesarios para la tarea elegida.

Selección de tarea:
- Si eres Opus: P0 ya está CERRADO (veredicto 2026-05-13: KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE). No reabrir P0 salvo que Pablo lo pida explícitamente o se cumplan los triggers documentados (≥28d cash_flow valid + ≥28 snapshots + divergencia reconciliada + Pablo dispuesto). Si Pablo pide trabajo nuevo Opus fuera de P0, pedir scope explícito antes de tocar nada.
- Si eres Codex: empezar por P1 (readout unificado lifecycle + Hazard + INTRA-REEVAL). Si P1 termina limpiamente y P2 sigue siendo read-only/reporting, puedes continuar con P2 en la misma sesión. No tocar P0.
- Si eres Sonnet: no implementes. Resume, diseña o prepara handoff si el backlog lo pide.

Token economics:
- Clasifica cada tarea antes de trabajar: ACTION_NOW / MONETIZATION_RELEVANT / RISK_CONTROL / WATCH_ONLY / DEFER_STOP.
- No abras tareas WATCH_ONLY salvo para cerrarlas con veredicto mínimo.
- No hagas auditoría global.
- No leas HISTORIAL completo; usa grep/últimas entradas si hace falta.
- Si una tarea no puede cambiar P&L, throughput, calidad de trades, BANKROLL readiness, riesgo real o bug runtime, ciérrala como NO_ACTION/WATCH.

Autonomía:
- Puedes hacer varias tareas en esta sesión solo si son compatibles en riesgo, no requieren Opus, no cambian env vars, no tocan trading core y no escriben DB runtime.
- Cierra cada tarea con veredicto antes de pasar a la siguiente.
- Para patches LOG_ONLY/read-only, puedes diagnosticar → implementar → validar → commit/push si las validaciones pasan y el backlog autoriza ese tipo de cambio.
- Si haces push a main, observa Railway hasta SUCCESS/FAILED.

Stop inmediato:
- Para si aparece BANKROLL, sizing, whitelist, city modes, scheduler, SL ejecutable, guards, BUY/SELL/SKIP, Fase C, env vars o DB writes no autorizados.
- Para si necesitas confirmación humana.
- Para si la conclusión requiere decisión Opus.
- Para si el worktree queda sucio fuera de scope.

Entrega final obligatoria:
- Tarea(s) trabajadas.
- Clasificación.
- Veredicto por tarea.
- Archivos tocados.
- Commit/push/deploy si aplica.
- Validaciones ejecutadas.
- Git status final.
- Confirmar explícitamente: BANKROLL, Fase C, trading core, env vars y DB runtime no tocados, salvo que se haya autorizado lo contrario.
- Siguiente tarea recomendada del backlog.
```

---

## 9. Cómo trabajar este backlog en VS Code

### Opción recomendada

1. Guardar este archivo en:
   ```text
   docs/BACKLOG_ORI_operational_readiness_intelligence.md
   ```

2. Abrir Claude Code o Codex en VS Code.

3. Pegar solo el **Driver prompt único**.

4. El agente debe escoger tarea según su tipo:
   - Opus → P0.
   - Codex → P1 y quizá P2.
   - Sonnet → diseño/cierre/handoff.

5. No pegar contexto adicional salvo:
   - resultados nuevos de runtime,
   - output de validaciones,
   - o una confirmación humana requerida.

### Cómo evitar bucles

Si el agente empieza a investigar demasiado, responder:

```text
Cierra con el veredicto disponible. No sigas investigando si no cambia la decisión. Clasifica como KEEP/WATCH/NEED_OPUS/BUG_PATCH_READY y entrega cierre.
```

Si el agente intenta abrir una tarea WATCH:

```text
No abras tareas WATCH_ONLY. Cierra con NO_ACTION y vuelve a la siguiente tarea monetizable del backlog.
```

Si el agente mezcla riesgos:

```text
Para. Esa parte requiere Opus/Pablo. Cierra la tarea actual y deja prompt corto para la decisión separada.
```

---

## 10. Orden recomendado

1. ~~`P0` con Opus.~~ **CERRADO 2026-05-13** (`KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`). No reabrir hasta cumplir triggers documentados.
2. ~~`P1` con Codex — readout unificado lifecycle + Hazard + INTRA-REEVAL.~~ **CERRADO 2026-05-13** (`NO_EXISTING_TOOL_PATCH_READY`).
3. ~~`P2`.~~ **CERRADO 2026-05-13** (`NO_ACTION operativo / REPORTING_GAP menor`).
4. ~~`P3`.~~ **CERRADO 2026-05-13** (`KEEP_MONITORING`).
5. ~~`P5`.~~ **CERRADO 2026-05-13** (`KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER`; review 2026-06-09 o triggers Phase 2).
6. Mantener `P4/P6` en WATCH salvo alarma nueva.
7. Ejecutar `M0` manual cuando haya `signals.json` fresco.

---

## 11. Cierre actual (revisado 2026-05-13)

- P0 cerrado por Opus: `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`. Doc cierre `docs/p0_b5_b6_opus_review_2026_05_13.md`.
- Renombrado canónico del backlog: ahora vive en `docs/BACKLOG_ORI_operational_readiness_intelligence.md`.
- P1 cerrado por Codex: readout unificado `tools/sl_intra_case_readout.py` implementado, desplegado y smokeado contra `/app/data`.
- P2 cerrado: `NO_ACTION operativo / REPORTING_GAP menor`; no hay bug scheduler actual.
- P3 triage Codex: `KEEP_MONITORING`; no patch sin muestra post-guard mayor o decision Opus.
- P5 cerrado por Opus: `KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER`; revisión obligatoria 2026-06-09 o triggers Phase 2 documentados.
- P4/P6 quedan `WATCH`; M0 sigue como manual recurrente.
- ORI deja de ser backlog activo: no hay P0-P6 accionable abierto.
- No se tocaron: BANKROLL, Fase C, trading core, env vars Railway, DB runtime, sizing, whitelist, city modes, scheduler, SL, guards ni reglas BUY/SELL/SKIP.

Veredicto general:

```text
BANKROLL $25: KEEP
$35: BLOCKED — no reabrir antes de 2026-06-08 y solo si se cumplen los triggers documentados
P0: CERRADO (KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE)
P1: CERRADO (Codex, readout unificado lifecycle + Hazard + INTRA-REEVAL)
P2: CERRADO (NO_ACTION operativo / REPORTING_GAP menor)
Los Angeles: WATCH_DIAGNOSTIC, no P1 todavía
SL Retrospective: KEEP_MONITORING
DB Throughput: CERRADO — KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER; review 2026-06-09 o triggers Phase 2
Los Angeles: WATCH_DIAGNOSTIC
Traders Intelligence: snapshots manuales
Blocked signals: WATCH_AUDIT
ORI backlog activo: CERRADO
```
