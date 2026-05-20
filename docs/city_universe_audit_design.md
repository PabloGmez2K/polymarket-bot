# City Universe Audit — Design Document

> **Status**: Design only. No implementation in this commit.  
> **Scope**: docs-only. No code, no env vars, no Railway, no BANKROLL, no Phase C, no city_mode changes, no source_policy changes.  
> **Trigger**: Opus verdict 2026-05-20 — principal monetization bottleneck is city universe, not BANKROLL.  
> **Authored by**: Sonnet (Sesión 372, 2026-05-20).

---

## 1. Problema de negocio

BANKROLL está en HOLD $25. No subirlo. El bot no monetiza porque el universo activo está
muerto, no por falta de capital.

Estado actual (ciclo 16:00 UTC 2026-05-20):

- 17 evaluaciones `live_eval`
- 0 evaluaciones de ciudades activas
- 0 `would_buy=true`
- `CONDITION_FILTER` dominante
- ACTIVE_TRADING_CITIES: Shanghai, Tokyo, Buenos Aires, Ankara
- 3 de 4 ciudades activas generan 0 evaluaciones operables
- Shanghai aporta evaluaciones pero caen por `condition_filtered` / `no_quality_trader_signal_match`

La siguiente palanca monetizable es identificar ciudades fuera del active set con señales
shadow/canary mejores que las activas. Este tool responde esa pregunta sin tocar runtime.

---

## 2. Pregunta principal

**¿Qué ciudades fuera del active set están generando mejores señales que las ciudades activas actuales?**

Sub-preguntas:

1. ¿Qué ciudades watch/canary/shadow generan `would_buy=true` en shadow o edge positivo?
2. ¿Qué ciudades tienen trader signals que el bot no está observando?
3. ¿Qué ciudades activas merecen ser demotadas a watch?
4. ¿Cuáles son candidatas reales para rotación canary?

---

## 3. Inputs — artifacts requeridos

### Primario (Railway `/app/data/`)

| Artifact | Campos necesarios | Uso |
|---|---|---|
| `bot_signal_evaluations.jsonl` | `city`, `eval_key`, `would_buy`, `condition_filtered`, `edge`, `condition`, `evaluation_source`, `timestamp` | Fuente principal de señales por ciudad |
| `blocked_signals_resolutions.jsonl` | `city`, `condition`, `date`, `outcome`, `bot_evaluation_join_status`, `win_for_trader`, `match_key` | Shadow wins/losses, trader vs bot |
| `trade_lifecycle.json` | `city`, `city_mode`, `outcome`, `pnl_cash`, `condition`, `open_timestamp` | Outcomes reales canary/active (read-only) |
| `skip_log.jsonl` | `city`, `reason`, `skip_reason`, `timestamp` | Near-misses, condition_blocked counts |
| `city_policy_state.json` | `auto_canary_cities`, `auto_shadow_cities`, `blocked_cities` | Policy effectiva por ciudad |

### Secundario (local `data/runtime_import_derived/` o SSH)

| Artifact | Campos necesarios | Uso |
|---|---|---|
| `source_onboarding.json` | `city`, `primary_status`, `mapping_status`, `source_audit_status`, `shadow_evidence_status`, `trader_evidence_status` | Fidelidad source + readiness |
| `city_lifecycle_review_latest.md` / JSON | `city`, `stage`, `transition`, `bottleneck` | Stage actual por ciudad |
| `city_promotion_gate_latest.md` / JSON | `city`, `gate`, `priority`, `bottleneck` | Gate de promoción actual |
| `signals.json` (traders) | `city`, `signals`, `win_rate`, `activity_by_hour` | Evidence trader signals |

### Opcional (si existen en Railway)

| Artifact | Uso |
|---|---|
| `data/intelligence/trader_signals_snapshots.jsonl` | Historial snapshots traders |
| `data/metar_shadow_report.json` | Source fidelity METAR por ciudad |
| `data/city_validation_ledger_*.json` | Historial validación source |

### Ventana temporal

14 días rolling desde fecha de ejecución. Mínimo 7 días si datos escasos.

---

## 4. Métricas por ciudad

Para cada ciudad en el universo conocido (active + canary + watch/shadow + blocked + fuera-del-flow):

| Métrica | Fuente | Descripción |
|---|---|---|
| `current_mode` | `city_policy_state.json` + `ACTIVE_TRADING_CITIES` env | active / canary / shadow / watch / blocked / unknown |
| `total_evals_14d` | `bot_signal_evaluations.jsonl` | Total evaluaciones en ventana |
| `evals_per_day` | derivado | `total_evals_14d / days_with_data` |
| `condition_filtered_count` | `bot_signal_evaluations.jsonl` | Evaluaciones filtradas por condition |
| `condition_filtered_pct` | derivado | `condition_filtered / total_evals` |
| `condition_mix` | `bot_signal_evaluations.jsonl` | Distribución exact/at_or_above/at_or_below/range |
| `edge_positive_count` | `bot_signal_evaluations.jsonl` | Evals con `edge > 0` |
| `would_buy_true_count` | `bot_signal_evaluations.jsonl` | Evals con `would_buy=True` |
| `would_buy_shadow_count` | `bot_signal_evaluations.jsonl` filter `evaluation_source=shadow` | Would-buy en shadow (no ejecutado) |
| `avg_edge` | `bot_signal_evaluations.jsonl` | Media edge en evals positivas |
| `max_edge` | `bot_signal_evaluations.jsonl` | Mejor edge observado |
| `near_miss_count` | `skip_log.jsonl` | Skips con edge>0 pero otra razón |
| `quality_trader_signal_matches` | `signals.json` cruzado con ciudad | Traders activos con señal en esa ciudad |
| `blocked_signals_wins` | `blocked_signals_resolutions.jsonl` `win_for_trader=True` | Resoluciones ganadas (traders correctos) |
| `blocked_signals_losses` | `blocked_signals_resolutions.jsonl` `win_for_trader=False` | Resoluciones perdidas |
| `blocked_signals_wr` | derivado | `wins / (wins + losses)` si n>=5 |
| `bot_eval_join_captured_pct` | `blocked_signals_resolutions.jsonl` `bot_evaluation_join_status=captured` | % resoluciones con bot_eval capturada |
| `estimated_shadow_wr` | derivado | WR aproximado si `would_buy_shadow_count > 0` y hay resolución |
| `estimated_shadow_pnl` | derivado | PnL shadow si hay outcomes resueltos |
| `source_fidelity_status` | `source_onboarding.json` | `SOURCE_MATCH_CONFIRMED` / `SOURCE_AMBIGUOUS` / `SOURCE_MISMATCH` / `unknown` |
| `mapping_status` | `source_onboarding.json` | `MAPPING_ICAO_ONLY` / `MAPPING_FULL` / `MAPPING_MISSING` |
| `promotion_gate` | `city_promotion_gate_latest.md` | Gate actual según lifecycle monitor |
| `lifecycle_stage` | `city_lifecycle_review_latest.md` | Stage según monitor |
| `main_blockers` | aggregado | Lista de razones bloqueantes principales |
| `data_confidence` | derivado | `high` (n>=20), `medium` (n>=7), `low` (n<7), `none` (0) |

---

## 5. Scoring de candidatas

Scoring simple, transparente y auditable. Sin ML ni magia. Cada dimensión vale 0–2 puntos.

| Dimensión | 0 | 1 | 2 |
|---|---|---|---|
| **throughput_score** | 0 evals 14d | 1–4 evals/day | >=5 evals/day |
| **edge_score** | avg_edge<=0 | avg_edge 1–9% | avg_edge>=10% |
| **would_buy_shadow** | 0 | 1–4 would_buy_shadow | >=5 would_buy_shadow |
| **condition_compat** | >80% condition_filtered | 40–80% filtered | <40% filtered |
| **source_fidelity** | MISMATCH o MISSING | AMBIGUOUS o ICAO_ONLY | CONFIRMED |
| **trader_signal** | 0 matches | 1–2 matches | >=3 matches o WR>=70% n>=5 |
| **recency** | últimos datos >10d | 5–10d | <5d |
| **data_confidence** | none | low | medium/high |

**Total máximo: 16 puntos.**

**Risk flags** (no restan puntos pero bloquean `promote_to_canary_candidate`):

- `drift_warning`: policy divergence detectada
- `settlement_warning`: mismatch source en resoluciones
- `structural_block`: BLOCKED_CITIES hard + no proxy operativo
- `source_critical`: `SOURCE_MISMATCH` o `MAPPING_MISSING` sin plan
- `insufficient_data`: data_confidence=none

El score es orientativo. Opus decide. No hay umbral mágico de auto-promoción.

---

## 6. Criterios de candidata a canary rotation

Para que una ciudad sea **propuesta** a Opus para rotación canary, debe cumplir:

**Criterios mínimos (todos obligatorios):**

1. `would_buy_shadow_count >= 5` OR `edge_positive_count >= 8` en últimos 7–14d
2. `source_fidelity_status` ∈ {`SOURCE_MATCH_CONFIRMED`, `SOURCE_PARTIAL`} — no critical
3. `mapping_status` ≠ `MAPPING_MISSING`
4. Condition mix: `condition_filtered_pct < 70%` (alguna condición pasaría el filtro actual)
5. Sin `drift_warning` ni `settlement_warning` activos
6. Sin `structural_block` (no está en BLOCKED_CITIES sin proxy observado)
7. `data_confidence` ∈ {`medium`, `high`} — n>=7 evals

**Criterios deseables (suma a score pero no son bloqueantes):**

- Trader signal confirmada con WR>=60% n>=5
- `lifecycle_stage` = `canary` o `shadow` con transición `active_review`
- `blocked_signals_wr >= 55%` con n>=5
- METAR parity disponible para la ciudad

---

## 7. Output esperado del futuro tool

### Formato del reporte

#### Tabla principal — ranking todas las ciudades

```
| Rank | City | Mode | Evals/day | WouldBuy Shadow | Edge+ | Score | Risk Flags | Action |
```

Ordenado por `score DESC`, luego `would_buy_shadow_count DESC`.

#### Sección: Top 5 candidatas a canary rotation

Para cada candidata:

```markdown
### [N]. CIUDAD — Score: X/16 — Action: promote_to_canary_candidate

- Mode actual: shadow/watch
- Evals/day: X
- Would_buy_shadow: X
- Edge+ count: X | Avg edge: X% | Max edge: X%
- Condition mix: exact=X%, at_or_above=X%, condition_filtered=X%
- Trader signals: X matches, WR=X% (n=X)
- Source fidelity: SOURCE_MATCH_CONFIRMED / MAPPING_ICAO_ONLY
- Main blockers: [lista]
- Data confidence: medium/high
- Risk flags: ninguno / [lista]
```

#### Sección: Bottom active cities — ciudades activas muertas

Para cada ciudad activa con `evals_per_day < 1` o `would_buy_true_count == 0` en 14d:

```markdown
### CIUDAD — Score: X/16 — Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: X (DEAD)
- Would_buy_true: 0
- Main blockers: condition_filtered=X%, no_quality_trader=X%
- Recommendation: observe_more or demote_to_watch_candidate
```

#### Reason codes por ciudad

Cada ciudad incluye:

```json
{
  "city": "...",
  "reason_codes": ["CONDITION_FILTER_DOMINANT", "NO_TRADER_SIGNAL", "SOURCE_AMBIGUOUS"],
  "recommended_action": "observe_more"
}
```

**Acciones posibles:**

| Código | Descripción |
|---|---|
| `keep_active` | Ciudad activa con throughput suficiente, sin acción |
| `demote_to_watch_candidate` | Ciudad activa sin throughput, proponer revisión humana |
| `promote_to_canary_candidate` | Ciudad fuera del active set con señales suficientes |
| `observe_more` | Señales prometedoras pero datos insuficientes aún |
| `source_blocked` | Bloqueada por fidelidad/mapping crítico |
| `condition_policy_blocked` | Señales presentes pero todas condition_filtered |

**Nota**: ninguna acción es ejecutable automáticamente. Todo pasa por revisión Opus.

---

## 8. Relación con Canary Rotation

El reporte no cambia nada. Opus usa el reporte así:

```
SI >=2 candidatas claras (criterios §6 cumplidos, sin risk flags críticos)
→ Opus decide: ¿rotar canary? ¿qué ciudad sale? ¿qué ciudad entra?
→ Acción manual en Railway (ACTIVE_TRADING_CITIES / CANARY_TRADING_CITIES)

SI 0–1 candidatas claras
→ Opus decide: ¿revisar condition policy? ¿mejorar instrumentación? ¿cambiar ventana?
→ No rotación

SI todas las ciudades activas están muertas + no hay candidatas
→ Opus decide: ¿experimento condition policy? ¿ACTIVE_TRADING_CITIES=NONE temporal?
→ Acción manual, no automática
```

**Nunca:**
- Promoción automática de shadow → canary → active
- Cambio directo de `ACTIVE_TRADING_CITIES` sin confirmación Opus + Pablo
- Active promotion directa (shadow → active sin canary)

---

## 9. Guardrails del futuro tool

El tool debe ser **estrictamente read-only**:

```python
# Prohibido absolutamente
# - escribir a bot.py, bot_signal_evaluations.jsonl, city_policy_state.json
# - cambiar env vars (ACTIVE_TRADING_CITIES, CANARY_TRADING_CITIES, BANKROLL)
# - emitir BUY/SELL/SKIP
# - modificar city_mode en ningún artifact
# - escribir a BLOCKED_CITIES ni whitelist
# - tocar source_policy, scheduler, sizing
# - activar Fase C

# Permitido
# - leer Railway via SSH (railway run cat /app/data/...)
# - leer archivos locales bajo data/runtime_import_derived/
# - escribir reporte a docs/ (markdown) y data/ (json, gitignored)
# - imprimir a stdout
```

**Output files del tool** (nunca en paths runtime):

- `docs/city_universe_audit_latest.md` — versionable, commitable
- `data/city_universe_audit_report.json` — gitignored
- `data/city_universe_audit_report.md` — gitignored (copia local)

---

## 10. Validación futura (cuando se implemente)

### Fixture / test local

1. Crear `tests/fixtures/city_universe_audit/` con sample de 10-20 filas de cada artifact.
2. Test principal: dado fixture, output determinístico, tabla correcta, scores correctos.
3. Test: ciudad sin datos → `data_confidence=none`, no aparece en top candidatas.
4. Test: ciudad con risk flag crítico → score alto pero `promote_to_canary_candidate` bloqueado.
5. Test: ciudad activa con 0 evals → `demote_to_watch_candidate`.

### Smoke run local

```bash
python tools/city_universe_audit.py --dry-run --data-dir data/runtime_import_derived/
```

Debe completar sin errores, sin escribir en paths runtime, output a `data/`.

### Criterios de aceptación

- `git diff --check` OK
- `py_compile` OK en todos los archivos tocados
- `verify_before_deploy.py` pasa (si hay código nuevo)
- Tests focales pasan sin sandbox ACL issues
- Output es determinístico dado mismo input
- No requiere Railway para smoke local (usa fallback derived/)
- No requiere API keys para correr

---

## 11. Auditorías anteriores y evolución

### Trabajos previos relacionados

| Doc / Tool | Fecha | Objetivo | Ciudades involucradas | Veredicto |
|---|---|---|---|---|
| `docs/city-watchlist-phase4.md` + `tools/city_watchlist_phase4.py` | ~Apr 2026 | Watchlist de candidatas fuera del active set | Madrid, Milan, Seoul, Dallas, Singapore, Toronto, Wellington, Munich | Candidatas identificadas, sin rotación |
| `docs/city-phase5-contrast.md` + `tools/city_phase5_contrast.py` | ~Apr 2026 | Contraste entre ciudades: active vs shadow vs canary | Shanghai, Tokyo, Buenos Aires, Ankara vs candidatas | Bottleneck en condition filter + shadow leaks |
| `docs/shadow-opportunity-shortlist-2026-04-11.md` | 2026-04-11 | Lista de oportunidades shadow con señal positiva | Dallas, Madrid, Milan, Seoul, Singapore, Toronto, Wellington | Shortlist generada, sin ejecución |
| `docs/throughput-alignment-audit-2026-04-10.md` | 2026-04-10 | Auditoría de throughput por ciudad y condición | Todas activas + canary | `CONDITION_FILTER` dominante, mismo patrón |
| `docs/auto-promotion-trigger-diagnosis-2026-04-13.md` | 2026-04-13 | Diagnóstico de auto-promoción canary | Dallas, Madrid, Milan, Singapore, Toronto, Wellington | `observe_runtime_canary` para las 6 ciudades |
| `docs/city-intelligence-phase5-operational-transition-plan-2026-04-23.md` | 2026-04-23 | Transición Phase 5 operacional | Ciudad intelligence pipeline completa | Pipeline construida, sin rotación de active |
| `tools/city_lifecycle_review_monitor.py` (latest: 2026-05-13) | continuo | Stage review de 46 ciudades | 46 ciudades universo | 6 ciudades en `active_review`, 3 en `preliminary_review_candidate` |
| `tools/city_promotion_gate.py` (latest: 2026-05-08) | continuo | Gates de promoción por ciudad | 16 ciudades con gate | Bottleneck: `policy_execution_gate` (13 ciudades `observe_runtime_canary`) |
| `docs/source_audits/candidate_source_onboarding_audit.md` | 2026-05-15 | Source audit Jeddah/Chongqing/Amsterdam | Jeddah, Chongqing, Amsterdam | `SOURCE_CONFIRMED_WAITING_SHADOW`, sin noaa_station_id |
| `docs/blocked_signals_audit_tool.md` + `tools/blocked_signals_audit.py` | 2026-04-28 | Audit blocked signals por ciudad/condition | Blocked signals universe | Señal en exact/range identificada |

### Ciudades candidatas identificadas en auditorías previas

En trabajos anteriores (Apr–May 2026) las siguientes ciudades aparecieron recurrentemente como candidatas:

**Grupo A — canary con `active_review` (lifecycle monitor 2026-05-13):**
Dallas, Madrid, Milan, Singapore, Toronto, Wellington

**Grupo B — shadow con señal trader (source onboarding scanner):**
Jeddah (WR trader 87.5%), Chongqing (WR trader 96%), Amsterdam (WR blocked 100% n pequeño)

**Grupo C — shadow con `preliminary_review_candidate`:**
Istanbul (canary_review), Austin, Hong Kong, Lucknow

### Blockers detectados antes vs ahora

| Blocker | Detectado en | Sigue igual |
|---|---|---|
| `CONDITION_FILTER` dominante en active set | Abr 2026 | **Sí** — mismo patrón en ciclo 2026-05-20 |
| Active cities sin throughput (Tokyo, Buenos Aires, Ankara) | Abr 2026 | **Sí** — 0 evaluaciones operables |
| `observe_runtime_canary` sin conversión a active | Abr 2026 | **Sí** — 13 ciudades en ese gate (May-08) |
| Source fidelity ICAO-only para candidatas shadow | Abr 2026 | **Parcial** — activas confirmadas S356, candidatas aún ICAO-only |
| bot_evaluation null en blocked_signals (impide Gap Report) | May 2026 | **Mitigado** — `READ_BOT_EVAL_CAPTURE=1` activado S371 |
| Phase 2 mixed-condition sin n suficiente | May 2026 | **Nuevo** — Phase 2 abierta 2026-05-10, T+30 = 2026-06-09 |

### Qué ha cambiado desde auditorías anteriores

**Nuevo desde Apr 2026:**

1. **bot_signal_evaluations.jsonl** disponible (S369 + S371): 180+ líneas, `READ_BOT_EVAL_CAPTURE=1` activo.
2. **Source Onboarding Scanner v0.2** (S359): primario_status, trader_evidence, shadow_evidence por ciudad fuera del flow.
3. **Source Fidelity Resolver** (S355/S356): activas confirmadas `SOURCE_MATCH_CONFIRMED`.
4. **METAR Measurement Layer** (S362–S366): Wave 1+2 parity para 17 estaciones, conexión con promoción.
5. **Traders Operational Intelligence Monitor** (S349–S350): monitor automático en bot, snapshots trader archivados.
6. **City Lifecycle Review Monitor v2** (S361): 46 ciudades, `effective_policy_status`, drift blocked-effective.
7. **Phase 2 abierta**: mixed-condition (exact via quality-trader + at_or_above/at_or_below), T+30 = 2026-06-09.
8. **BLOCKED_CITIES hard-block fix** (S347): Paris/Chicago ya no contaminan admisión.

**Qué NO ha cambiado:**

1. `ACTIVE_TRADING_CITIES` sigue siendo las 4 mismas (Shanghai, Tokyo, Buenos Aires, Ankara).
2. 3 de 4 activas siguen sin throughput operable.
3. `CONDITION_FILTER` sigue siendo el blocker dominante.
4. Ninguna ciudad shadow ha sido promovida a active en este período.
5. Las 6 ciudades en `active_review` (Dallas, Madrid, Milan, Singapore, Toronto, Wellington) siguen en ese estado desde ~Apr 2026 sin decisión de rotación.
6. Gap Report (trader vs bot) sigue en construcción — desbloqueado instrumentalmente pero no ejecutado.

### Veredicto comparativo

**BETTER_DATA_SAME_DECISION**

Hay más y mejor instrumentación que en auditorías previas (bot_evaluation, source fidelity, METAR, traders monitor), pero el diagnóstico de fondo es el mismo desde al menos S326 (Apr 2026): el universo activo está muerto por condition filter, y hay un grupo de ciudades canary/shadow con mejores señales que nunca llegan a rotación.

**Esta auditoría (Fase A) es diferente en un aspecto crítico**: por primera vez hay datos directos de `bot_signal_evaluations.jsonl` con `would_buy` real del bot por ciudad, no inferidos de proxies. Eso hace que el scoring §5 sea ejecutable sobre datos reales, no solo estimaciones. La pregunta ya no es "¿hay señal?" sino "¿qué ciudad tiene más would_buy_shadow en los últimos 14 días?"

---

## 12. Próximo paso — prompt de implementación para Codex

```
Implementar tools/city_universe_audit.py como CLI read-only.

Objetivo: generar el reporte de City Universe Audit según el diseño en
docs/city_universe_audit_design.md sin tocar ningún archivo runtime ni
env var.

Inputs a leer:
- data/runtime_import_derived/bot_signal_evaluations.jsonl (o /app/data/ en Railway)
- data/runtime_import_derived/blocked_signals_resolutions.jsonl
- data/runtime_import_derived/trade_lifecycle.json
- data/runtime_import_derived/skip_log.jsonl (si existe)
- data/runtime_import_derived/city_policy_state.json (si existe)
- data/source_onboarding.json (si existe)
- docs/city_lifecycle_review_latest.md o JSON equivalente (read-only)
- docs/city_promotion_gate_latest.md o JSON equivalente (read-only)

Outputs:
- docs/city_universe_audit_latest.md (versionable)
- data/city_universe_audit_report.json (gitignored)

CLI flags:
- --data-dir PATH (default: data/runtime_import_derived/)
- --days N (default: 14)
- --min-confidence [low|medium|high] (default: low, incluye todas)
- --json-out PATH (default: data/city_universe_audit_report.json)
- --md-out PATH (default: docs/city_universe_audit_latest.md)
- --dry-run (no escribe outputs, solo imprime)

Guardrails:
- No importar bot.py como módulo ejecutable; leer via AST si necesita constantes
- No escribir a /app/data/ ni paths runtime
- No cambiar env vars
- No emitir BUY/SELL/SKIP
- No modificar city modes ni whitelist

Tests focales (tests/test_city_universe_audit.py):
- fixture con 5 ciudades, data determinística
- scoring correcto para ciudad con would_buy_shadow=6 sin risk flags → promote_to_canary_candidate
- ciudad activa con 0 evals → demote_to_watch_candidate
- ciudad con SOURCE_MISMATCH risk flag → score alto bloqueado
- ciudad sin datos → data_confidence=none, no en top candidatas
- output markdown generado correctamente

Validaciones:
- py_compile OK
- tests focales pasan sin sandbox issues
- git diff --check OK
- verify_before_deploy.py pasa
- dry-run local sin API keys ni Railway OK

No tocar: bot.py, BANKROLL, Fase C, env vars, city modes, whitelist, scheduler,
trading core, ACTIVE_TRADING_CITIES, BLOCKED_CITIES, source_policy, sizing.
```

---

*Documento creado: Sesión 372, 2026-05-20. Diseño únicamente — sin implementación.*
