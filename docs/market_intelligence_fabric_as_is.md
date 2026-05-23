# Market Intelligence Fabric — AS-IS Audit

**Fecha:** 2026-05-23 (Sesión 380, Sonnet, read-only)
**Alcance:** arquitectura de inteligencia del bot como estado vivo. No cambia código, runtime, env vars ni trading.
**Veredicto final:** `FRAGMENTED_DATA_FABRIC_CONNECTIVITY_FIRST`

---

## 1. Propósito y alcance

Este documento mapea la arquitectura de inteligencia existente: qué produce cada capa, qué consume, cómo se unen, y dónde el sistema no puede responder preguntas monetizables.

El objetivo no es diseñar nuevas herramientas. Es saber con exactitud qué existe, qué se puede unir ya, y qué conexión única desbloquea el mayor aprendizaje.

---

## 2. Inventario de herramientas por capa

### 2.1 Funnel Observability

| Atributo | Valor |
|---|---|
| Scripts | `bot.py` (hooks), `tools/daily_bot_digest.py` (consumer) |
| Artefacto | `data/funnel_observability_log_only.jsonl`, `data/funnel_observability_latest.json` |
| Ubicación runtime | `/app/data/` en Railway |
| Frecuencia | Por ciclo (automático) |
| Estado | LIVE / LOG_ONLY |
| Consumer | `daily_bot_digest.py` → Telegram bloque compacto 24h |

Captura: `discovered`, `prefiltered`, `city_window_skipped`, `price_out_of_range`, `date_out_of_range`, `condition_filtered`, `policy_source_blocked`, `edge`, `shadow_edge`, `selected`, `real_buy`. Disponible desde 2026-05-21. Baseline 24h: `discovered=2970 prefiltered=246 edge=0 shadow_edge=7 selected=0 BUY=0`.

Limitación: captura contadores agregados por ciclo, no identidades de mercado individual. No hay `condition_id`/`market_id` por mercado descartado.

---

### 2.2 Bot Signal Evaluations

| Atributo | Valor |
|---|---|
| Scripts | `bot.py` (writer) |
| Artefacto | `data/bot_signal_evaluations.jsonl` |
| Ubicación runtime | `/app/data/` en Railway |
| Frecuencia | Por ciclo (automático, `DISABLE_BOT_EVAL_CAPTURE=1` kill switch) |
| Estado | LIVE / LOG_ONLY |
| Consumer | Resolver en `bot.py` cuando `READ_BOT_EVAL_CAPTURE=1` |

Campos clave: `eval_key`, `cycle_id`, `city`, `date_iso`, `condition`, `threshold`, `unit`, `would_buy`, `bot_edge_pct_at_signal`, `skip_or_block_reason`, `decision_gate`, `our_prob`, `mkt_prob`, `days_ahead`.

Disponible desde 2026-05-19. Railway live: 357 filas en 14 ciclos. `READ_BOT_EVAL_CAPTURE=1` activo → el resolver puede marcar matches en `blocked_signals_resolutions.jsonl` como `live_eval/captured`.

---

### 2.3 Blocked Signals Resolutions

| Atributo | Valor |
|---|---|
| Scripts | `bot.py` (appender), `tools/blocked_signals_audit.py`, `tools/signals_crosscheck_daily_summary.py` |
| Artefacto | `data/blocked_signals_resolutions.jsonl` |
| Ubicación runtime | `/app/data/` en Railway (660 filas live) |
| Frecuencia | Por señal bloqueada (automático) |
| Estado | LIVE / Schema v2 |
| Consumer | Blocked signals audit (manual), crosscheck summary (automático), daily Telegram |

Schema v2 (33 campos): `canonical_signal_id`, `market_id`, `condition_id`, `city_mode_at_record_time`, `reason_blocked`, `resolution_source`, `price_bucket`, `observed_coverage_status`, `whitelist_status_at_record_time`, `win_for_trader`, etc.

**Campos nulos hasta Fase C (5):** `settlement_source`, `settlement_fidelity_status`, `bot_edge_pct_at_signal`, `bot_would_have_bought`, `bot_evaluation_source`. Estos campos son la diferencia entre "trader ganó" y "bot habría comprado y ganado".

Join activo: `match_key` ↔ `bot_signal_evaluations.eval_key` (via resolver cuando `READ_BOT_EVAL_CAPTURE=1`).

---

### 2.4 Signals Crosscheck

| Atributo | Valor |
|---|---|
| Scripts | `tools/signals_vs_edge_crosscheck.py`, `tools/signals_crosscheck_railway_service.py`, `tools/signals_crosscheck_daily_summary.py` |
| Artefacto | `data/signals_crosscheck.jsonl` |
| Ubicación runtime | `/app/data/` en Railway |
| Frecuencia | Automático por ciclo (hook en `bot.py`) |
| Estado | LIVE |
| Consumer | `traders_intelligence_report.py`, daily Telegram summary (`MATCH`, `BOT_ONLY`, `TRADER_ONLY`) |

Cruza señales de traders activos vs señales del bot en el mismo mercado. Emite `MATCH` (ambos), `BOT_ONLY` (solo bot), `TRADER_ONLY` (trader sin bot). Baseline reciente: `MATCH=19`, `BOT_ONLY=5`, `TRADER_ONLY=13`. Ciudades `TRADER_ONLY` persistentes: Buenos Aires, Miami, Warsaw, Chengdu, Lagos.

---

### 2.5 Traders Intelligence

| Atributo | Valor |
|---|---|
| Scripts | `tools/traders_intelligence_collector.py`, `tools/traders_intelligence_snapshot.py`, `tools/directional_trader_census.py`, `tools/directional_trader_enrichment.py`, `tools/traders_intelligence_report.py`, `tools/traders_intelligence_daily_summary.py` |
| Artefactos (gitignored) | `data/traders_intelligence/snapshots/`, `data/traders_intelligence/pseudo_lifecycle_runs.jsonl`, `data/traders_intelligence.json` |
| Ubicación runtime | `/app/data/traders_intelligence/` en Railway |
| Frecuencia | Automático (`TRADERS_INTELLIGENCE_COLLECTOR=ON`, cooldown 30min) |
| Estado | V1.1 ACTIVE / LOG_ONLY |
| Consumer | `traders_intelligence_daily_summary.py` → Telegram daily, `traders_intelligence_report.py` |

Traders fuertes activos: `Entire-Hood`, `Dimpled-Boy`, `Loyal-Aggression`, `Villainous-Wave`. Ciudades trader-only relevantes: Los Angeles, Miami, San Francisco, Tel Aviv.

---

### 2.6 Traders Operational Intelligence / Gap Monitor

| Atributo | Valor |
|---|---|
| Scripts | `tools/trader_signals_full_snapshot_collector.py`, `tools/traders_operational_questions_report.py`, `tools/traders_operational_intelligence_monitor.py` |
| Artefactos (gitignored) | `data/intelligence/trader_signals_snapshots.jsonl`, `data/intelligence/traders_operational_monitor_state.json` |
| Frecuencia | Automático (hook en `run_observability_alerts()`, `TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED`) |
| Estado | LIVE / LOG_ONLY |
| Consumer | Telegram LOG_ONLY (no BUY/SELL/SKIP) |

**Gap crítico documentado (A7, 2026-05-07):** 133/133 filas con `bot_evaluation=null`. El crosscheck de blocked signals no tiene el campo `bot_evaluation` rellenado porque la unión con `bot_signal_evaluations.jsonl` aún no está instrumentada en el reporte. Esto convierte la pregunta "¿qué habrían comprado traders que el bot no evaluó?" en `DATA_EXISTS_NOT_JOINED`.

---

### 2.7 METAR Measurement Layer

| Atributo | Valor |
|---|---|
| Scripts | `tools/metar_shadow_fetch.py`, `tools/metar_parity_report.py`, `tools/metar_resolution_verify.py`, `tools/visual_crossing_backfill_run.py` |
| Artefactos (gitignored) | `data/metar_shadow/<ICAO>_<YYYY-MM-DD>.json`, `data/metar_shadow_report.json` |
| Frecuencia | Manual semanal (no scheduler) |
| Estado | LOG_ONLY / manual |
| Consumer | `daily_bot_digest.py` lee `metar_shadow_report.json` → Telegram bloque METAR LOG_ONLY |

Wave 1: 10 estaciones (ciudades active/canary principales). Wave 2: 7 estaciones adicionales (Seoul/Singapore/Toronto/Wellington/Madrid/Milan/Munich). Estado actual: `METAR_PARITY_INSUFFICIENT_DATA` (insuficiente comparación METAR vs WU en días comparables).

**Gap de fechas crítico:** resoluciones en `blocked_signals_resolutions.jsonl` son de 2026-04-08 a 2026-04-19. Snapshots METAR disponibles desde 2026-05-13. Sin solapamiento → 0 filas MATCH en resolution verification. No hay join posible sobre el histórico real aún.

---

### 2.8 Source Fidelity / Onboarding Scanner

| Atributo | Valor |
|---|---|
| Scripts | `tools/source_fidelity_resolver.py`, `tools/source_onboarding_scanner.py`, `tools/source_onboarding_andon.py`, `tools/settlement_fidelity_probe.py` |
| Artefactos | `data/source_onboarding.json` (gitignored), `docs/source_audits/` (versionado) |
| Frecuencia | Andon: automático (hook `bot.py`). Scanner: manual. |
| Estado | Andon LIVE / Scanner manual |
| Consumer | Andon → Telegram (`NEW_HUMAN_SOURCE_AUDIT_READY`, `SOURCE_CONFIRMED_WAITING_SHADOW`, etc.) |

Active cities auditadas: Shanghai/ZSPD, Tokyo/RJTT, Buenos Aires/SAEZ, Ankara/LTAC → `SOURCE_MATCH_CONFIRMED`. Istanbul/LTFM → `SOURCE_CONFIRMED` via WRH shadow source. Candidatos shadow (Jeddah, Chongqing): `OBSERVATION_WAITING_EVIDENCE`.

---

### 2.9 City Intelligence / Lifecycle Review

| Atributo | Valor |
|---|---|
| Scripts | `tools/city_intelligence_pipeline.py`, `tools/city_validation_ledger.py`, `tools/city_promotion_gate.py`, `tools/city_lifecycle_review_monitor.py`, `tools/city_intelligence_digest.py` |
| Artefactos | `data/city_validation_ledger.json`, `data/city_promotion_gate.json`, `data/settlement_fidelity_probe.json` |
| Frecuencia | Automático (bridge en `bot.py` post-07 UTC) |
| Estado | LIVE |
| Consumer | `city_intelligence_digest.py` → Telegram, `maybe_run_city_lifecycle_review` |

Topología actual (Railway live): `active=4` (Shanghai/Tokyo/Buenos Aires/Ankara), `blocked=4` (London/Paris/Atlanta/Chicago), `canary=varios` (Seoul + candidatos), `shadow=resto`. Phase 2 Recalibration abierta: T+30 = 2026-06-09.

---

### 2.10 Shadow City Tracking

| Atributo | Valor |
|---|---|
| Script | `bot.py` interno |
| Artefacto | `data/shadow_city_tracking.json` (local: 205.6KB) |
| Frecuencia | Por ciclo (automático) |
| Estado | LIVE |
| Consumer | City Intelligence pipeline, promotion gates |

Acumula `markets_seen`, `edge_hits`, `cycles_seen`, `best_edge_pct` por ciudad shadow. Es el único mecanismo de acumulación de evidencia pre-canary. No contiene outcome de resolución.

---

### 2.11 Trade Lifecycle / P&L

| Atributo | Valor |
|---|---|
| Scripts | `tools/pnl_report.py`, `tools/wallet_snapshot.py`, `tools/wallet_cash_flow_log.py`, `tools/sl_intra_case_readout.py`, `tools/daily_position_briefing.py`, `tools/pnl_reconciliation_alert.py`, `tools/leaderboard_pnl_snapshot.py` |
| Artefactos | `trade_lifecycle.json` (1.4MB local), `performance.json`, `wallet_portfolio_snapshots.jsonl`, `wallet_cash_flows.jsonl` |
| Frecuencia | Por ciclo y por resolución de mercado (automático) |
| Estado | LIVE |
| Consumer | Daily briefing Telegram, P&L reconciliation alert, SL retrospective, Kanban digest, `pnl_report.py` |

Estado P&L: `canonical_source=none`, `bankroll_readiness=blocked`. Horizonte 1W: `provisional` (+$4.43 con attestation de mayo). Horizonte 1M: `blocked` por cobertura insuficiente de cash flows. BANKROLL $25 HOLD.

---

### 2.12 SL / Guards / L2 Hazard

| Atributo | Valor |
|---|---|
| Scripts/Módulos | `bot.py` (SL_intra guard, INTRA-REEVAL shadow, Unsellable Guard, L2 Hazard monitor) |
| Artefactos | `data/sl_intra_guard_audit.json`, `data/intra_reeval_state.json`, `data/skip_log.jsonl` (8.2MB) |
| Estado | SL_intra guard: ACTIVE. INTRA-REEVAL: shadow LOG_ONLY. Unsellable Guard: LOG_ONLY dormant. L2: LOG_ONLY. |
| Consumer | `tools/sl_intra_case_readout.py` (manual join), SL retrospective Telegram |

SL_intra Guard: skipea exact+days_ahead≤1. Audit A8 (2026-05-07): `ESPERAR_MÁS_MUESTRA` (n=2 leverage-real). Re-check en 5º guarded o 2026-05-21 (ya cumplido — pendiente lectura).

---

### 2.13 SQLite / DB Throughput

| Atributo | Valor |
|---|---|
| Scripts | `sqlite_recorder.py`, `tools/truth_pipeline_*.py`, `tools/db_throughput_report.py` |
| Artefacto | `/app/data/polymarket.db` (Railway) |
| Estado | `SQLITE_RECORDER_ENABLED=1` LIVE. Truth Pipeline Phase 1 (truth_records) NO implementado. |
| Consumer | `db_throughput_report.py` → Daily Bot Digest Telegram bloque DB Throughput |

Tablas activas: `cycle_events`, `market_snapshots`, `forecast_snapshots`. Tablas pendientes: `truth_records`, `truth_revisions` (Fase 1 Truth Pipeline).

---

### 2.14 Daily Digest / Telegram

| Atributo | Valor |
|---|---|
| Scripts | `tools/daily_bot_digest.py`, `tools/daily_bot_observability_run.py`, `tools/daily_kanban_digest.py` |
| Frecuencia | Automático diario (Railway scheduler, `DAILY_BRIEFING_HOUR_UTC`) |
| Estado | LIVE |
| Bloques activos | Funnel LOG_ONLY, METAR LOG_ONLY, DB Throughput, Wallet/P&L (pending attestation), Traders Intelligence, Phase 2 monitor, SL Retro, City Intelligence |

Es la única superficie de agregación visible para Pablo. Tous los módulos convergen aquí. Sin embargo, los bloques son independientes entre sí — el digest no produce joins ni síntesis cruzada.

---

### 2.15 Skip Log

| Atributo | Valor |
|---|---|
| Script | `bot.py` (writer), `tools/analyze_skip_log.py` |
| Artefacto | `data/skip_log.jsonl` (8.2MB local) |
| Estado | LIVE (automático) |
| Consumer | Manual via `analyze_skip_log.py`. `sl_intra_case_readout.py` lo usa para join por token_id. |

Contiene cada skip con razón, ciudad, condición, fecha, precio. El dataset más granular del funnel, pero sin consumer automatizado que cruce con outcome.

---

### 2.16 NOAA / Open-Meteo / Observed-vs-Forecast

| Atributo | Valor |
|---|---|
| Módulo | `bot.py` interno |
| Artefacto | `data/audit.json` (local 91.3KB) — `observed_vs_forecast` dentro |
| Estado | LIVE |
| Consumer | City Intelligence pipeline, promotion gates, SL retrospective (como fallback), `tools/forecast_accuracy_audit.py` |

Acumula comparaciones forecast vs observado real por ciudad/fecha. Es la base de evidencia para parity/source verification. Sin join automatizado con `blocked_signals_resolutions.jsonl` por fecha/ciudad.

---

## 3. Tabla producer → artifact → consumer → decisión

| Producer | Artefacto | Consumer principal | Superficie de decisión |
|---|---|---|---|
| `bot.py` cycle | `funnel_observability_log_only.jsonl` | `daily_bot_digest.py` | Telegram LOG_ONLY (no decisión) |
| `bot.py` cycle | `bot_signal_evaluations.jsonl` | Resolver `blocked_signals_resolutions.jsonl` | `bot_evaluation_join_status` (captura, no decisión) |
| `bot.py` blocked signal | `blocked_signals_resolutions.jsonl` | `blocked_signals_audit.py`, `signals_crosscheck_daily_summary.py` | Telegram ACTION / audit manual |
| `signals_vs_edge_crosscheck.py` | `signals_crosscheck.jsonl` | `traders_intelligence_report.py`, Telegram daily | TRADER_ONLY alert (no ejecutable) |
| `traders_intelligence_collector.py` | `data/traders_intelligence/` | `traders_intelligence_daily_summary.py` | Telegram daily LOG_ONLY |
| `traders_operational_intelligence_monitor.py` | `data/intelligence/` state | Telegram LOG_ONLY | Gap alert (no ejecutable — bot_evaluation null) |
| `metar_shadow_fetch.py` (manual) | `data/metar_shadow/<ICAO>_date.json` | `metar_parity_report.py` → `daily_bot_digest.py` | Telegram METAR LOG_ONLY (sin join histórico) |
| `source_onboarding_andon.py` | `data/source_onboarding/andon_state.json` | Telegram ANDON | Alert source audit manual |
| `city_intelligence_pipeline.py` | `city_validation_ledger.json`, `city_promotion_gate.json` | `city_intelligence_digest.py` | Telegram city review / promotion gate |
| `bot.py` shadow | `shadow_city_tracking.json` | City Intelligence pipeline | Promotion candidate gate |
| `bot.py` trade | `trade_lifecycle.json`, `performance.json` | `pnl_report.py`, `daily_position_briefing.py` | Telegram briefing / BANKROLL gate |
| `wallet_snapshot.py` | `wallet_portfolio_snapshots.jsonl` | `pnl_report.py` | BANKROLL readiness (blocked) |
| `bot.py` SL_intra guard | `sl_intra_guard_audit.json` | `maybe_run_sl_intra_guard_review` | Telegram one-shot review |
| `bot.py` cycle | `skip_log.jsonl` | `sl_intra_case_readout.py` (manual) | Manual audit only |
| `sqlite_recorder.py` | `polymarket.db` | `db_throughput_report.py` | Telegram DB Throughput LOG_ONLY |
| `bot.py` NOAA | `audit.json` (observed_vs_forecast) | City Intelligence, promotion gates, SL retro | Promotion gate (evidencia) |

---

## 4. Grafo lógico textual de conexiones existentes

```
signals.json (Polymarket live)
    │
    ├── signals_crosscheck.jsonl
    │       └── signals_crosscheck_daily_summary.py → Telegram TRADER_ONLY alert
    │       └── traders_intelligence_report.py
    │               └── traders_intelligence_daily_summary.py → Telegram LOG_ONLY
    │
    └── traders_intelligence_collector.py → data/traders_intelligence/ → Telegram daily
    
bot.py cycle (core trading loop)
    │
    ├── funnel_observability_log_only.jsonl → daily_bot_digest.py → Telegram Funnel block
    │
    ├── bot_signal_evaluations.jsonl
    │       └── [resolver, READ_BOT_EVAL_CAPTURE=1] → blocked_signals_resolutions.jsonl
    │               (bot_evaluation_join_status = captured/missing)
    │
    ├── blocked_signals_resolutions.jsonl
    │       ├── blocked_signals_audit.py → manual readout
    │       └── signals_crosscheck_daily_summary.py → Telegram ACTION level
    │
    ├── shadow_city_tracking.json
    │       └── city_intelligence_pipeline.py
    │               ├── city_validation_ledger.json
    │               ├── city_promotion_gate.json
    │               └── city_intelligence_digest.py → Telegram City Review
    │
    ├── trade_lifecycle.json + performance.json
    │       ├── pnl_report.py → daily_kanban_digest.py → Telegram P&L
    │       ├── daily_position_briefing.py → Telegram Briefing
    │       ├── sl_retrospective.py → Telegram SL Retro
    │       └── sl_intra_case_readout.py (manual join)
    │
    ├── skip_log.jsonl
    │       └── analyze_skip_log.py (manual only)
    │
    ├── sl_intra_guard_audit.json
    │       └── maybe_run_sl_intra_guard_review → Telegram one-shot
    │
    └── audit.json (observed_vs_forecast)
            ├── city_intelligence_pipeline.py (promotion gate input)
            └── sl_retrospective.py (fallback)

polymarket.db (SQLite)
    └── db_throughput_report.py → daily_bot_digest.py → Telegram DB block

metar_shadow/ (manual fetch)
    └── metar_parity_report.py → metar_shadow_report.json
            └── daily_bot_digest.py → Telegram METAR block

source_onboarding_andon.py (hook in bot.py)
    └── Telegram ANDON source alerts

traders_operational_intelligence_monitor.py (hook in bot.py)
    └── Telegram gap alert [BROKEN: bot_evaluation=null]
```

---

## 5. Identificadores y schemas de unión

| Clave | Formato | Presente en |
|---|---|---|
| `eval_key` / `match_key` | `city\|date_iso\|condition\|threshold[-threshold_high]\|unit` | `bot_signal_evaluations.jsonl`, `blocked_signals_resolutions.jsonl`, `signals_crosscheck.jsonl` |
| `token_id` | hex string | `trade_lifecycle.json`, `skip_log.jsonl`, `sl_intra_guard_audit.json`, `performance.json` |
| `canonical_signal_id` | hash de `match_key` + ciclo | `blocked_signals_resolutions.jsonl` v2 |
| `cycle_id` / `cycle_number` | integer + ts_utc | `funnel_observability_log_only.jsonl`, `bot_signal_evaluations.jsonl`, `cycles_history.jsonl`, `polymarket.db` |
| `market_id` / `condition_id` | Polymarket IDs | `blocked_signals_resolutions.jsonl` v2, `trade_lifecycle.json` |
| `city` | string normalizado | Prácticamente todos |
| `date_iso` | `YYYY-MM-DD` | `bot_signal_evaluations.jsonl`, `blocked_signals_resolutions.jsonl`, `skip_log.jsonl` |
| ICAO | 4-char string | `RESOLUTION_ICAO` (bot.py), `metar_shadow/<ICAO>_date.json` |
| `market_slug` | Polymarket slug | `blocked_signals_resolutions.jsonl`, `settlement_fidelity_probe.json` |

**Join documentado y activo:**
`bot_signal_evaluations.eval_key` ↔ `blocked_signals_resolutions.match_key` vía resolver (`READ_BOT_EVAL_CAPTURE=1`).

**Joins posibles pero no implementados:**
- `skip_log` city+date+condition → `blocked_signals_resolutions` match_key (podrían unirse, pero skip_log no tiene market_id)
- `funnel_observability_log_only.jsonl` cycle → `skip_log.jsonl` timestamp (ventana temporal, no join directo)
- `shadow_city_tracking` city+date → METAR snapshot (si fechas coinciden)
- `observed_vs_forecast` (audit.json) city+date → `blocked_signals_resolutions` city+date

---

## 6. Herramientas conectadas versus islas

### Conectadas (join activo o consumidor automático)

| Herramienta | Conexión |
|---|---|
| Funnel Observability → Daily Digest | ✅ Telegram bloque automático |
| bot_signal_evaluations → blocked_signals_resolutions | ✅ Resolver activo (READ_BOT_EVAL_CAPTURE=1) |
| signals_crosscheck → traders_intelligence_report | ✅ Join vía crosscheck series |
| shadow_city_tracking → city_intelligence_pipeline → city_promotion_gate | ✅ Pipeline automático |
| trade_lifecycle → pnl_report / briefing | ✅ Daily automático |
| sl_intra_guard_audit → guard review Telegram | ✅ One-shot review |
| metar_shadow_report → daily_bot_digest | ✅ Bloque Telegram (manual refresh previo) |
| polymarket.db → db_throughput_report → daily_digest | ✅ Automático |

### Islas (sin consumer automatizado o join roto)

| Herramienta | Estado de isla |
|---|---|
| `skip_log.jsonl` (8.2MB) | Sin consumer automático. Solo lectura manual via `analyze_skip_log.py`. |
| `traders_operational_questions_report.py` | `bot_evaluation=null` en 133/133 filas. Monitor activo pero respuesta vacía. |
| `metar_resolution_verify.py` | 0 comparables (brecha de fechas: resoluciones abr, METAR desde may). Reporte existe pero sin datos. |
| `blocked_signals_resolutions` campos Fase C | `settlement_source`, `settlement_fidelity_status` nulos. Sin implementar Fase C. |
| `source_fidelity_resolver.py` (manual) | Sin join automático con funnel ni blocked signals. Docs versionadas, no consumidas. |
| `sl_intra_case_readout.py` | Manual. Útil para auditoría pero no conectado a flujo automático. |
| Funnel per-market identity | Funnel cuenta agregados, no identidades. Mercados descartados son invisibles individualmente. |

---

## 7. Matriz de preguntas monetizables

| Pregunta | Estado | Bloqueador |
|---|---|---|
| Q1. ¿Cuáles mercados descartados por `city_window` habrían sido rentables? | `CAPTURE_MISSING` | Funnel captura contador pero no `condition_id`/`market_id` por descarte. Sin resolución posterior posible. |
| Q2. ¿Cuáles descartados por `condition` habrían generado edge/P&L positivo? | `DATA_EXISTS_NOT_JOINED` | `skip_log` tiene city+date+condition, `blocked_signals_resolutions` tiene outcome trader. Join posible pero no implementado. |
| Q3. ¿Cuáles descartados por `price` eran oportunidades perdidas? | `CAPTURE_MISSING` | `price_out_of_range` solo como contador. No se guarda market identity ni precio histórico. |
| Q4. ¿Qué ciudades/condiciones acumulan shadow_edge positivo? | `PARTIALLY_CONNECTED` | `shadow_city_tracking` existe y alimenta promotion gate. No hay outcome de resolución linkado. |
| Q5. ¿Qué mercados encuentran traders fuertes que bot no evalúa/descarta? | `DATA_EXISTS_NOT_JOINED` | `signals_crosscheck` identifica TRADER_ONLY. `bot_signal_evaluations.jsonl` existe. Join via `eval_key` contractado pero **el Gap Report no está construido**. `bot_evaluation=null` en operational questions. |
| Q6. ¿Qué oportunidades están bloqueadas solo por falta de source fidelity? | `PARTIALLY_CONNECTED` | Source onboarding scanner corre manualmente. Andon alerta. Sin join automático con funnel o blocked signals por ciudad. |
| Q7. ¿Qué reglas de filtrado evitan pérdidas de forma demostrable? | `PARTIALLY_CONNECTED` | SL_intra guard tiene audit. `blocked_signals_resolutions` tiene `win_for_trader` (trader ganó cuando el bot bloqueó). Pero `bot_would_have_bought` = null → no se puede separar "protección correcta" de "oportunidad perdida". |

---

## 8. Necesidades para agentes LLM

Para que Opus/Sonnet/Codex puedan explotar esta inteligencia sin leer logs masivos:

**Lo que existe y es usable:**
- `funnel_observability_latest.json` — snapshot compacto de último ciclo, legible directamente.
- `traders_intelligence.json` — resumen de traders, health_status, top traders.
- `signals_crosscheck.jsonl` — serie de crosschecks con MATCH/BOT_ONLY/TRADER_ONLY.
- `blocked_signals_resolutions.jsonl` — con v2 schema (33 campos), base más rica.
- `city_promotion_gate.json` — estado de cada ciudad vs gate.
- `pnl_report.py --json` — output estructurado del estado P&L.

**Lo que falta para un agente:**
1. **Joined artifact compacto**: un reporte que cruce `bot_signal_evaluations` + `blocked_signals_resolutions` + `signals_crosscheck` por `eval_key/match_key`. Hoy el agente tiene que hacer el join manualmente o leer 3 archivos separados.
2. **Market identity tracking**: sin `condition_id`/`market_id` por mercado descartado en funnel, no hay provenance desde "descartado" hasta "resolución".
3. **Counterfactual summary compacto**: "¿qué habría pasado si el bot hubiera comprado los TRADER_ONLY de esta semana?" No existe como artefacto.
4. **Schema dictionary**: los schemas de todos los artefactos no están en un lugar único consultable. El agente tiene que leer múltiples docs.
5. **Review queue priorizada**: los distintos monitores generan alertas independientes. No hay una cola unificada de "esto merece atención humana hoy" con razón y evidencia.
6. **Outputs Telegram-only**: múltiples alertas van a Telegram pero no quedan como artefacto reutilizable en `/app/data`. Por ejemplo, el bloque Phase 2 monitor no escribe un JSON de estado consumible por el siguiente agente.

---

## 9. Top gaps por impacto

### Gap 1 — Trader vs Bot Gap Report (ALTA PRIORIDAD)
**Impacto:** Convierte Q5 de `DATA_EXISTS_NOT_JOINED` a `ANSWERABLE_NOW`.
**Qué falta:** Construir el join `bot_signal_evaluations.eval_key` ↔ `blocked_signals_resolutions.match_key` ↔ `signals_crosscheck` en un reporte que segmente: trader ganó + bot habría comprado (oportunidad perdida real), trader ganó + bot no habría comprado (filtro correcto), trader perdió + bot habría comprado (riesgo evitado). La infraestructura existe. El join está contractado en `docs/instrumentation/bot_evaluation_capture.md`. Falta construir el reporte. Impacto directo: saber si las ≥13 señales TRADER_ONLY por ciclo son oportunidades perdidas o ruido filtrable.

### Gap 2 — Market identity en discards (ALTO)
**Impacto:** Convierte Q1, Q3 de `CAPTURE_MISSING` a potencialmente `ANSWERABLE_NOW` (si se añade market_id a funnel).
**Qué falta:** El funnel captura contadores por etapa pero no identidad de mercado. Si se añade un sample de `condition_id`/`market_id` por etapa de descarte (no requiere cambio de schema — ya existe `sample_shadow_edges` como patrón), los mercados descartados pueden seguirse hasta resolución. Mínima captura nueva: `top_city_window_discards`, `top_price_oor_discards` por ciclo con market identity.

### Gap 3 — `bot_would_have_bought` en blocked signals (MEDIO)
**Impacto:** Convierte Q7 de `PARTIALLY_CONNECTED` a `ANSWERABLE_NOW`.
**Qué falta:** El campo `bot_would_have_bought` en `blocked_signals_resolutions.jsonl` es null (Fase C no implementada). Con `READ_BOT_EVAL_CAPTURE=1` activo, el resolver ya puede marcar `captured/missing`. El paso siguiente es rellenar `bot_would_have_bought` desde `bot_signal_evaluations.would_buy` en el momento del join. Esto convierte el dataset de blocked signals en un dataset causal: "trader ganó, bot habría comprado" → oportunidad perdida demostrable.

### Gap 4 — Skip log → outcome join (MEDIO)
**Impacto:** Convierte Q2 de `DATA_EXISTS_NOT_JOINED` a `PARTIALLY_CONNECTED`.
**Qué falta:** `skip_log.jsonl` tiene city+date+condition+precio en el momento del skip. `blocked_signals_resolutions.jsonl` tiene city+date+condition+outcome. Un join por ciudad+fecha+condición daría una estimación de si los skips por `condition_filtered` o `price_out_of_range` coincidían con mercados que después resolvieron a favor del lado skipeado.

### Gap 5 — METAR fecha alignment (BAJO/ESPERAR)
**Impacto:** necesario para Q6 en historical pero no bloqueante ahora.
**Qué falta:** Las resoluciones históricas (abr-8 a abr-19) no tienen METAR contemporáneo. Sólo cuando pasen 30+ días de captura METAR habrá solapamiento con resoluciones futuras. `visual_crossing_backfill_run.py` puede rellenar el histórico pero requiere presupuesto de API. Diferir hasta que haya n≥10 resoluciones nuevas con METAR.

### Lo que NO debe construirse todavía

- Trader-vs-bot gap → BUY automático: cualquier inferencia de oportunidad requiere decisión humana/Opus.
- Market identity capture masiva sin sample: añadir top-N sample, no todos los discards.
- Counterfactual P&L sin `canonical_source`: P&L sigue `blocked`, no usar para decisiones de BANKROLL.
- Fase C Truth Pipeline: esperar a que Phase 1 SQLite truth_records esté implementada.
- Nuevas ciudades/conditions sin trigger de evidencia.

---

## 10. Única recomendación para el siguiente bloque Opus

> **Construir el Trader vs Bot Gap Report Phase 1.**

La infraestructura existe y está contractada:
- `bot_signal_evaluations.jsonl` con 357+ filas desde 2026-05-19, `eval_key` estable.
- `blocked_signals_resolutions.jsonl` con 660 filas, `match_key` = `eval_key`.
- `READ_BOT_EVAL_CAPTURE=1` activo → resolver ya une ambos.
- `signals_crosscheck.jsonl` identifica TRADER_ONLY por ciclo.

Lo que falta es un script `tools/trader_vs_bot_gap_report.py` que:
1. Lea los tres artefactos.
2. Haga el join por `eval_key/match_key`.
3. Segmente los 4 cuadrantes: (trader_won ∩ bot_would_buy), (trader_won ∩ bot_skip), (trader_lost ∩ bot_would_buy), (trader_lost ∩ bot_skip).
4. Emita JSON compacto en `data/intelligence/` + Markdown versionable en `docs/`.
5. Quede como LOG_ONLY, sin consumer ejecutable.

**Impacto:** convierte `TRADER_ONLY=13/ciclo` de observación ciega en datos casuales. Si la mayoría cae en (trader_won ∩ bot_skip → filtro correcto), confirma los filtros actuales. Si cae en (trader_won ∩ bot_would_buy → ciudad/policy blocked), identifica el cuello de botella real.

**Criterio de parada:** reporte con n≥30 filas joined, distribución por cuadrante, y 3 ciudades con suficiente muestra para decisión Opus.

---

## Veredicto final

**`FRAGMENTED_DATA_FABRIC_CONNECTIVITY_FIRST`**

La razón: el sistema tiene datos suficientes para responder Q5 (la pregunta de más alto impacto monetizable) pero la respuesta está atrapada en 3 artefactos que no están unidos en un reporte. La infraestructura de join existe, el contrato está documentado, y el único paso faltante es implementar el reporte. Todas las demás preguntas (Q1, Q3) requieren nueva captura. Q5 solo requiere conectar lo que ya existe.

Los módulos actuales no son islas irrecuperables — son islas con puentes sin terminar. El Gap Report es el puente de mayor ROI.
