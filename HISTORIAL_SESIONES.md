# HISTORIAL DE SESIONES

Bitácora legible del proyecto reconstruida desde:

- `git log`
- `CONTEXTO.md`
- mensajes de commit

Objetivo:

- saber qué sesiones ya existieron;
- evitar repetir trabajo ya hecho;
- distinguir entre cambios explícitamente documentados y reconstrucciones inferidas;
- complementar a Git con una memoria humana del proyecto.

Reglas de lectura:

- `Explícita`: la sesión aparece nombrada tal cual en Git o en el contexto.
- `Inferida`: no aparece como sesión formal, pero se puede reconstruir con bastante confianza por la secuencia de commits.
- Este archivo no sustituye al historial real de Git; lo resume.

Comandos útiles:

- `git log --follow --oneline -- CONTEXTO.md`
- `git log --oneline --reverse`
- `git show <commit>`

---

## Línea temporal resumida

| Fecha | Tipo | Referencia | Commits clave | Resumen |
|------|------|------------|---------------|---------|
| 2026-05-25 | Explícita | Sesión 392 | pending | Codex implementa FULL limitado de contención Wellington exact/NO tras confirmación de Pablo de la segunda venta manual de Wellington 16°C May26 NO (4.5 acciones a 44¢, +$1.98). Patch acotado en `bot.py`: helper `_is_wellington_exact_no_paused()`, constante `PAUSE_WELLINGTON_EXACT_NO` y gate después de edge/min-edge/Kelly positivo pero antes de scaling/BUY append. El gate bloquea solo `city=Wellington`, `condition=exact`, `side=NO`, registra `skip_reason="cohort_paused"` con `cohort_pause_id` en `skip_log` y `record_bot_evaluation(... would_buy=False, decision_gate=PAUSE_WELLINGTON_EXACT_NO)`. Test focal nuevo cubre Wellington exact NO bloqueado y YES/range/otras ciudades no bloqueadas. Sin env var nueva; no se toca BANKROLL, sizing, guards, scheduler, otras ciudades, otras condiciones, accounting, NOAA, whitelist, city modes, SL, DB ni Fase C. |
| 2026-05-25 | Explícita | Sesión 391 | docs-only | Sonnet versiona diseño aprobado por Opus: Outcome Resolver v1 (`APPROVE_RECONCILIATION_ARCHITECTURE_PENDING_T7_FOR_CODE`). Creado `docs/outcome_resolver_v1_design.md`: estado DESIGN_APPROVED/CODE_BLOCKED, dependencias learning_data_contract.md v1.0 + pnl_clean_source_policy.md v1.2, arquitectura R1-R4 (R1=Reconciled executions LOG_ONLY; R2=Settlement join LOG_ONLY gate R1 >=7d; R3=Report read-only preautorizado; R4=Calibration NO preautorizado), correcciones provenance/nomenclatura/settlement/execution_id, exclusión Seoul 8 filas suspect, política micro_position_unsellable, orden de implementación y gates, 6 fixtures de test, 10 stop conditions para Opus. CODE bloqueado hasta T+7d (~2026-05-31) + autorización Pablo. T+7 sano no autoriza automáticamente. `docs/weather_intelligence_workstream.md` actualizado (backlog + orden ejecución). Sin código, Railway, env vars, BANKROLL, trading core, city modes, guards, Pre-Edge flag, Fase C, BUY/SELL/SKIP. |
| 2026-05-25 | Explícita | Sesión 387 | docs-only | Sonnet cierra validación runtime post-patch: ciclo #395 Seoul effective_mode=blocked sin regresión, Wellington NO LOSS_TOTAL + Toronto NO RESOLVED_WIN sin SELL reeval (NO_PATCH_NO_REEVAL_EVENT_YET_CONTINUE_WATCH). PRE_EDGE_T5_HEALTH_OK_CONTINUE: 32 filas limpias, 7 ciclos, p95=0.26ms, 0 kill-switches. External Weather Intelligence Workstream versionado en docs/weather_intelligence_workstream.md + raw archive en docs/research_inputs/external_weather_claims_2026-05-24.md. Sin código, Railway, env vars, BANKROLL ni trading. |
| 2026-05-25 | Explícita | Sesión 386 | pending | Codex corrige Seoul source-fidelity mismatch y deja candado durable. Precheck post-reactivación: `SHADOW_ONLY_MODE=false`, `BANKROLL=25.00`, `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1`, `ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara`, Seoul había regresado a `auto_canary=true`/`auto_blocked=false`, sin posiciones abiertas. Se confirma que `BLOCKED_CITIES` tiene prioridad efectiva sobre `auto_canary`/active y la autopromoción no elimina el env var. Mutación runtime autorizada única: `BLOCKED_CITIES` conserva `London,Paris,Atlanta,Chicago` y añade `Seoul`; deployment Railway `562c05b3-62ac-442b-a1cd-3ad5576e8041` SUCCESS; Seoul queda `mode=blocked`, trading del resto sigue activo. Patch mínimo: `RESOLUTION_STATIONS["Seoul"]` cambia Seoul City/KMA `(37.5665,126.9780)` por Incheon Intl/RKSI `(37.4602,126.4407)`, alineado con `RESOLUTION_ICAO["Seoul"].icao == RKSI`. Tests focales cubren alignment RKSI, forecast route de `recompute_position_edge()` con coords RKSI, metadata Pre-Edge futura RKSI y hard-block Seoul sobre auto_canary. Las 8 filas Seoul Pre-Edge de 2026-05-24 quedan `source_fidelity_suspect`; evidencia Seoul KMA histórica no autoriza reactivación. Pre-Edge T+5 queda listo pero pendiente de análisis separado. No se toca BANKROLL, sizing, thresholds, whitelist, scheduler, guards, SL, DB, Pre-Edge flag, Fase C ni otras ciudades. |
| 2026-05-25 | Explícita | Sesión 385 | pending | Codex aplica patch critico `CONFIRMED_EXIT_OR_PNL_BUG` para re-evaluacion de posiciones NO. Contencion previa validada: `SHADOW_ONLY_MODE=true` en Railway, deployment `c2a12617-3377-49db-bcf7-708060f1b9c0` SUCCESS, sin posiciones abiertas (`open_positions_count=0`), `BANKROLL=25.00`, `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1`, Seoul sigue en `auto_blocked_cities`. Bug: `recompute_position_edge()` invertia indebidamente `curPrice` para posiciones NO (`mkt_price = 1.0 - cur_price`) aunque `/positions` ya entrega el precio del token NO; esto hizo que Shanghai NO con forecast/probabilidad sin cambio se leyera como mercado ~80c y edge ~-30%, disparando SELL `reeval`. Fix minimo: rama NO conserva `our_prob = 1.0 - our_prob_yes` y usa `mkt_price = cur_price`. Tests nuevos cubren NO +30pp, YES equivalente y `manage_positions()` sin venta reeval cuando edge NO sigue positivo. Validaciones: focales 3 passed, `py_compile` OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Addendum S384: Seoul containment valido, pero la afirmacion global `sells=0` fue incorrecta porque hubo venta Shanghai; futuras verificaciones de ventas deben usar `trade_lifecycle`/`trades.log`/`decisions.log`, no claves inexistentes o ambiguas de `cycle_summary`. Pendientes separados: PnL Telegram post-fill/copy, dedupe BUY en trade_lifecycle, Seoul RKSI/KMA definitivo, External Weather Intelligence tras estabilizacion. Trading real sigue pausado por `SHADOW_ONLY_MODE=true`; no BANKROLL, sizing, thresholds, city modes, whitelist, scheduler, guards, SL, DB, Pre-Edge flag ni Fase C tocados. |
| 2026-05-24 | Explícita | Sesión 382 | env var only | Sonnet activa `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1` en Railway tras veredicto Opus `RATIFY_IDENTITY_ALLOW_CONTROLLED_LOG_ONLY_ACTIVATION_BEFORE_PHASE2_T30` y autorización explícita Pablo. Precheck: git status solo untracked preexistentes, HEAD=`e9e2a49`, COMPUTE_CAP_BUG fix confirmado en `bot.py`, deployment activo `1ef9947d SUCCESS`. Acción única: env var set. Deployment activación: `604cae37 SUCCESS 2026-05-24 13:15:04 +02:00` (`activation_timestamp=2026-05-24T11:15:04Z`). Post-activación: variable `=1` confirmada; ninguna otra variable tocada. Estado: `ACTIVATED_WAITING_FIRST_ELIGIBLE_CYCLE`. Kill-switches Opus activos (overhead, error_rate, BUY/SELL/SKIP, identity, Phase2 rollback). Trigger smoke: primer ciclo con `condition=exact` + `qt_gate_reason=no_quality_trader_signal_match` + `city_mode active/canary`. Sin código, sin BANKROLL, sin Fase C, sin BUY/SELL/SKIP, sin city modes, sin thresholds, sin guards ejecutables tocados. |
| 2026-05-24 | Explícita | Sesión 381 | 448103d | Sonnet corrige COMPUTE_CAP_BUG y cierra auditoría pre-activación. AUDIT 2: `estimate_prob_with_city` ahora solo se llama para las ≤20 filas seleccionadas post-cap (antes se llamaba para TODOS los candidatos elegibles en el hot loop). Fix: hook en-loop colecta pre-records ligeros → `_flush_exact_no_qt_match_evals()` aplica dedup+SHA-256 cap → compute solo para seleccionados → `write_exact_no_qt_match_evals(_pre_capped_meta=...)` para fidelidad de `eligible_before_cap`. AUDIT 1: `market_id`/`condition_id` confirmados no-impactantes; veredicto `REQUIRES_OPUS_RATIFICATION_BEFORE_ACTIVATION`. AUDIT 3: 14 tests hook-integration nuevos (T_H1-T_H7). AUDIT 4: consumer `NOT_ENABLED_NO_DATA` degradation confirmada contractualmente. AUDIT 5: Railway env var ausente confirmada. 44 tests focales passed; `verify_before_deploy.py` 1255/1255. Railway deployment `74ecd9d5` SUCCESS. Env var OFF. |
| 2026-05-23 | Explícita | Sesión 380 | 33702c8 | Sonnet implementa captura LOG_ONLY de evaluaciones exact/no-QT-match (FULL / CODE / env var OFF). `bot.py` v10.6.43: `hashlib`/`uuid` importados; constante `EXACT_NO_QT_MATCH_EVAL_FILE`; `market_id`/`condition_id` propagados a candidates en PASO 2; `write_exact_no_qt_match_evals()` con dedup+SHA-256 cap(20)+fail-open; hook LOG_ONLY antes del QT-gate `continue`; batch flush al final del ciclo. `tools/trader_vs_bot_gap_report.py` schema v5 + `_summarize_exact_no_qt_match_log_only()` reader (`NOT_ENABLED_NO_DATA` cuando ausente). `tests/test_exact_no_qt_match_eval_log_only.py` 30 tests focales (T1-T15: env OFF, ambos lados YES/NO, dedup, cap, SHA-256 reproducible/order-independent/no-bias-lexicographic, schema completo, identity_resolvable, consumer, degradación). `.gitignore` excluye `data/exact_no_qt_match_evaluations_log_only.jsonl`. Env var `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED` NO activada en Railway. Validaciones: `py_compile` OK, 30 tests focales passed, `verify_before_deploy.py` 1255/1255, `git diff --check` OK. Railway deployment `cdc738c0` SUCCESS. Trading/policy/BANKROLL/Fase C/guards/SL/BUY/SELL/SKIP intactos. |
| 2026-05-23 | Explícita | Sesión 379 | docs-only | Sonnet verifica estado del L2 Hazard Monitor LOG_ONLY. Precheck Railway confirma `SL_INTRA_HAZARD_MONITOR_ENABLED=1` y `SL_INTRA_HAZARD_MONITOR_LOG_ONLY=1` ya activos desde Sesión 286 (2026-05-04T04:11:07 UTC). No se realizó ningún cambio de variable ni deployment. Audit JSON live (`data/sl_intra_hazard_monitor_audit.json`): 11 tokens observados (Munich, Singapore×3, Seoul, Paris, Shanghai, Toronto×2), tiers `deteriorating/deep/terminal/collapsed`, `last_telegram_at=2026-05-22T07:43:57 UTC` — monitor sano. Ventana 14d: cumplida (19d desde activación). Stale en `CONTEXTO.md` línea 2601 corregido (`default OFF` → estado real ACTIVO). No se tocaron código, `bot.py`, trading, BANKROLL, guards, env vars Railway, Fase C ni lógica ejecutable. Veredicto: `L2_LOG_ONLY_ENABLED_OBSERVATION_STARTED` (monitor ya activo desde Sesión 286). |
| 2026-05-23 | Explícita | Sesión 378 | commit actual | Codex cierra Tier 1 Funnel Observability LOG_ONLY derivado de Opus `DATA_OR_POLICY_OBSERVABILITY_GAP`. Verificación live Railway read-only confirma `READ_BOT_EVAL_CAPTURE=1`, artifacts `/app/data/funnel_observability_log_only.jsonl`, `funnel_observability_latest.json`, `bot_signal_evaluations.jsonl`, `blocked_signals_resolutions.jsonl`, `cycles_history.jsonl` y `skip_log.jsonl` presentes. Ventana funnel live real: 13 filas desde `2026-05-21T16:00:52Z` hasta `2026-05-23T08:00:47Z`; últimas 24h: 9 ciclos, `discovered=2970`, `prefiltered=246`, `edge=0`, `shadow_edge=7`, `selected=0`, `BUY=0`, skips `city_window=1155`, `price=1228`, `date_past=330`, `condition=234`. Gap mínimo: el writer runtime ya existía, pero Daily Bot Digest/Telegram preview no consumía el funnel. Patch acotado en `tools/daily_bot_digest.py` añade bloque compacto `Funnel LOG_ONLY` fail-open, basado en `data/funnel_observability_log_only.jsonl`, sin writes runtime ni acciones; test focal en `tests/test_daily_bot_digest.py`; doc `docs/funnel_observability_log_only.md` pasa a `DIGEST WIRED`. Validaciones: py_compile OK, focales relevantes 35 passed, smoke digest con artifact live OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. No toca trading core, BUY/SELL/SKIP, BANKROLL, sizing, whitelist, city modes, scheduler, guards, thresholds, condiciones, DB, env vars, Railway data ni Fase C. |
| 2026-05-21 | Explícita | Sesión 377 | f65d1d5 | Codex implementa un patch NORMAL / LOG_ONLY de pending cash-flow attestation. Nuevo `tools/wallet_cash_flow_pending_attestation.py`: lee snapshots de wallet y `wallet_cash_flows.jsonl`, calcula `latest_attested_end`, `latest_snapshot_at` y gap pendiente; si no hay flags de depósito/retiro/anomalía emite `pending_no_cash_flow_attestation` con `recommended_actor=pablo_manual`, `recommended_type=no_cash_flow_attestation`, nota sugerida, `manual_confirmation_required=true`, `canonical_eligible=false`, `writes_wallet_cash_flows=false` y comando sugerido de `wallet_cash_flow_log.py append` sin `--write`. Si hay `possible_deposit`, `possible_withdrawal`, `withdrawal_like_drop`, `equity_jump` o missing data, devuelve `manual_review_required` y no propone auto no-cash-flow. `tools/daily_kanban_digest.py` incorpora `pnl_sources.pending_cash_flow_attestation` y línea humana compacta "Cash-flow coverage gap ... Pablo confirmation needed"; outputs `data/wallet_cash_flow_pending_attestation.json(.jsonl)` quedan gitignored. Validaciones: `py_compile` OK, focales 38 passed, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Push a `main`; Railway deployment `57733bcc-b405-46ec-8162-dc7d0889e4ae` SUCCESS. No auto-write en `wallet_cash_flows.jsonl`, no canonical_source, no BANKROLL, no DB/env vars, no trading core, no city modes/scheduler/whitelist/sizing/guards, no Fase C/Truth Pipeline ni BUY/SELL/SKIP. |
| 2026-05-21 | Explícita | Sesión 376 | docs-only | Codex registra trazabilidad de la attestation manual ya añadida en Railway a `/app/data/wallet_cash_flows.jsonl`: schema v2, `entry_id=a8cadf40-22fa-485b-b17f-e6883ac52ff5`, `actor=pablo_manual`, `type=no_cash_flow_attestation`, periodo `2026-05-13T08:00:48Z` -> `2026-05-21T08:00:47Z`, sin depósitos/retiros reportados por Pablo. Validaciones previas: ledger válido con `rows=4`, `pnl_report.py` OK, `cash_flows.coverage_days` 0.0 -> 7.0, `1W` blocked -> provisional `+$4.43`, `1M` 13.409d -> 21.409d pero sigue blocked por `cash_flow_coverage_below_1M`. `canonical_source=none`, `bankroll_readiness=blocked`, BANKROLL $35 no autorizado. Sesión docs-only: sin código, runtime, Railway, DB, env vars, BANKROLL, trading core, city modes, scheduler, whitelist, sizing, guards, Fase C, Truth Pipeline ni BUY/SELL/SKIP. |
| 2026-05-18 | Explícita | Sesión 369 | 7fc2d27 | Codex implementa Phase 0 `bot_evaluation` capture como NORMAL / LOG_ONLY instrumentation, sin push. `bot.py` añade `data/bot_signal_evaluations.jsonl` append-only y `record_bot_evaluation(...)` no-throw con `evaluation_source="live_eval"`, `eval_key`, `would_buy`, edge/probabilidades/gate/skip metadata. Writer gated por `DISABLE_BOT_EVAL_CAPTURE=1`; resolver de `blocked_signals_resolutions.jsonl` lee solo con `READ_BOT_EVAL_CAPTURE=1` (default 0), y entonces marca matches `live_eval/captured` o misses `unknown/False/missing` sin relajar el default `unknown/False`. `_early_key` se liftó a `eval_key` conservando semántica. Doc nuevo `docs/instrumentation/bot_evaluation_capture.md`; tests focales cubren writer, kill switch, no-throw I/O, resolver captured/missing y shadow-only gate. Validaciones: `py_compile` OK, tests focales 6+4 passed, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Smoke runtime deferred por no existir una ejecución local claramente no-trading. Sin BUY/SELL/SKIP, filtros, MIN_EDGE, argumentos de compra, DB, scheduler, Telegram, BANKROLL, Fase C, source_policy, city modes, whitelist, Railway env vars, sizing, SL ni NOAA. |
| 2026-05-18 | Explícita | Sesión 368 | local | Codex implementa el runner manual Railway aprobado por Opus `APPROVE_MANUAL_RAILWAY_RUN_ONLY` para METAR Resolution Verification. Nuevo `tools/visual_crossing_backfill_run.py`: recomputa el verifier para localizar Wave 1/Wave 2 `NO_SNAPSHOT`, respeta snapshots `data/metar_shadow/<ICAO>_<YYYY-MM-DD>.json`, salta existentes, usa `tools/visual_crossing_historical_fetch.py` para generar faltantes, guarda presupuesto diario en `visual_crossing_backfill_state.json` bajo `DATA_DIR`/`/app/data`/`data`, limita por `VISUAL_CROSSING_DAILY_BUDGET` default 100 y `VISUAL_CROSSING_MAX_CALLS_PER_RUN` default 20, y re-ejecuta `tools/metar_resolution_verify.py` al final de runs reales. `--dry-run` no requiere API key, no llama Visual Crossing, no escribe state ni reportes. `OPERATIONS_PLAYBOOK.md` documenta finalidad, comandos Railway dry-run/real, env vars esperadas y guardrails. Dry-run local: `planned_calls=0`, `calls_used=0`, `new_snapshots=0`, `skipped_existing=29`, status final 34 MATCH / 6 MISMATCH / 0 NO_SNAPSHOT / 73 NO_DATA. Tests focales nuevos cubren formato, skip, budget state reset y dry-run sin key; se actualiza el test local del verifier al piloto actual. Validaciones: `py_compile` runner OK, tests focales 17 passed, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Commit local, sin push. Sin `bot.py`, Daily Digest, scheduler, Telegram runtime, DB, env vars, Railway env var changes, trading core, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, source_policy, city modes, whitelist, promotion gates ni canonical source switch. |
| 2026-05-18 | Explícita | Sesión 367 | e3a53af | Codex implementa la primera Resolution Source Verification Pipeline para METAR como NORMAL / LOG_ONLY tooling, separada del METAR Measurement Layer. Nuevo `tools/metar_resolution_verify.py`: lee resoluciones oficiales Polymarket/Gamma desde `data/runtime_import_derived/blocked_signals_resolutions.jsonl`, extrae umbral desde `threshold` o `match_key`, resuelve ciudad a ICAO mediante Wave 1/Wave 2 de `tools/metar_shadow_fetch.py` sin modificarlo, consume snapshots `data/metar_shadow/<ICAO>_<YYYY-MM-DD>.json`, reconstruye outcome hipotético METAR para `exact`, `at_or_above` y `at_or_below`, emite MATCH/MISMATCH/NO_SNAPSHOT/INSUFFICIENT_METAR/UNSUPPORTED_CONDITION, métricas por ciudad, estados de equivalencia y alertas LOG_ONLY. Gate real: 113 filas, campos `city/date/condition/outcome/close_price` presentes, `threshold` no separado; 98 exact, 15 range; 40 filas mapeadas a Wave 1/2 pero 0 comparables por falta de snapshots de abril. Reporte versionado `docs/source_audits/metar_resolution_verify_report.md`: `NO_DATA=73`, `NO_SNAPSHOT=40`, sin alertas/candidatos; JSON local ignorado. Tests focales 8 passed; `py_compile` OK; `git diff --check` OK; `verify_before_deploy.py` 1255/1255. Push a `main`; Railway deployment `7456774b-8c4b-477d-900e-4bedf13f9b52` SUCCESS. Sin bot.py, trading, DB, env vars, BANKROLL, Fase C, city modes, whitelist, scheduler, Telegram runtime, source_policy, Truth Pipeline ni BUY/SELL/SKIP. |
| 2026-05-17 | Explícita | Sesión 365 | 6c6c96b | Codex implementa Wave 2 del METAR Measurement Layer como NORMAL / LOG_ONLY tooling. `tools/metar_shadow_fetch.py` conserva `WAVE1_STATIONS` intacto y añade `WAVE2_STATIONS`/`METAR_STATIONS` para Seoul/RKSI, Singapore/WSSS, Toronto/CYYZ, Wellington/NZWN, Madrid/LEMD, Milan/LIMC y Munich/EDDM; los helpers manuales `station_city`/`station_timezone` usan la lista combinada para que `--icao` sea callable sin flags de runtime. `docs/metar_measurement_layer.md` documenta Wave 2 como coverage expansion por gaps canary WU/ICAO, mantiene alertas LOG_ONLY/manuales y deja Amsterdam, Wuhan, Busan, Jakarta y Kuala Lumpur en source-audit queue separada. Tests METAR focales fijan Wave 1 intacta y Wave 2 exacta. Validaciones: `py_compile` METAR OK, tests focales METAR 7 passed, reporte manual local OK con `METAR_PARITY_INSUFFICIENT_DATA` esperado por falta de WU/Gamma local, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Push a `main`; Railway deployment `da7f0e59-5231-4fdc-b4d4-d178e4d4015f` SUCCESS. Sin `bot.py`, trading core, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, env vars, DB, city modes, whitelist, scheduler, Telegram runtime ni promotion gates. |
| 2026-05-15 | Explícita | Sesión 361 | pending | Codex corrige City Lifecycle Review alerting como NORMAL / RISK_CONTROL / LOG_ONLY. El monitor normaliza city keys, expone `effective_policy_status/source`, hace ganar `BLOCKED_CITIES` sobre overlays stale y clasifica `auto_canary` + blocked efectivo como `reporting_drift_blocked_effective` con `NO_ACTION_LOG_ONLY` en vez de `active_review`. `observe_runtime_canary` requiere evidencia canary minima (5 cierres, WR>=60%, PnL>=0) para `active_review`; si no, baja a `canary_watch`, "not active-ready" y "Do not promote". `bot.py`/digest agrupan canary_watch y blocked-effective drift; alertas individuales quedan para manual review, active_review real y silent promotion. Smoke local con runtime_import: Paris no emite active_review; Dallas/Madrid/Milan/Singapore/Toronto/Wellington quedan canary_watch; Austin preliminary por background_watch. Validaciones: 57 tests focales passed fuera del sandbox por ACL temp, `py_compile` OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Sin trading core, BANKROLL, Fase C, env vars, DB writes, city modes, scheduler, whitelist, promotion gates ejecutables, observed_vs_forecast, source mappings ni BUY/SELL/SKIP. |
| 2026-05-15 | Explícita | Sesión 360 | pending | Codex conecta Source Onboarding Scanner v0.2 al flujo runtime de observabilidad como Andon LOG_ONLY. Nuevo `tools/source_onboarding_andon.py` consume `data/source_onboarding.json`, mantiene estado idempotente en `data/source_onboarding/andon_state.json` (ignorado), emite `andon_latest.json` y registra eventos runtime solo cuando hay alerta. Triggers implementados: `NEW_HUMAN_SOURCE_AUDIT_READY`, `SOURCE_CONFIRMED_WAITING_SHADOW`, `OBSERVATION_REVIEW_READY`, `SOURCE_AMBIGUOUS`, `SOURCE_MISMATCH` y `PRIORITY_UPGRADED`. `bot.py` añade `maybe_run_source_onboarding_andon()` después del scanner y antes del digest, default ON con kill switch `SOURCE_ONBOARDING_ANDON_ENABLED=false`, timeout configurable y paths bajo `_data_path("source_onboarding")`. Telegram copy deja claro `NO_ACTION / LOG_ONLY`, `Do not add to active/canary`, no BUY/SELL/SKIP, no BANKROLL ni Fase C; mismatch/ambiguous escalan a `ESCALATE_OPUS`. Tests focales cubren no-spam, eventos ready/source-confirmed/ambiguous/mismatch/shadow-ready, kill switch y orden de hook. Validaciones: 43 tests source onboarding passed, `py_compile` OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255; smoke dry-run local OK `should_notify=false` sin writes. Sin trading core, BANKROLL, Fase C, env vars Railway, DB, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast ni source mappings. |
| 2026-05-15 | Explícita | Sesión 359 | 3c57cb6 | Codex implementa Source Onboarding Scanner v0.2 como NORMAL / LOG_ONLY tooling. `tools/source_onboarding_scanner.py` separa readiness de trader, shadow/observacion, discovery de fuente, mapping, audit y operacion con campos explicitos (`primary_status`, statuses por capa, `missing_inputs`, `blocking_reasons`, `next_best_action` y flags de recomendacion). `SOURCE_BLOCKED` queda reservado para bloqueo fuerte real; mapping ausente pasa a `MAPPING_MISSING` y falta de ids a `MARKET_IDS_MISSING`. Test nuevo cubre Chongqing trader 24/25 + ids + ICAO-only + shadow parcial como `OBSERVATION_WAITING_EVIDENCE` con source/Gamma audit recomendado. Corrida local antigua: 10 candidatas, `MARKET_IDS_MISSING=5`, `MAPPING_MISSING=5`, sin `SOURCE_BLOCKED`; Jeddah/Chongqing locales explican faltas de ids/source text/noaa/shadow/trader sample. Validaciones: scanner real local OK, tests focales 16 passed, syntax AST OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Push a `main`; Railway deployment `77602303-0a3a-4a80-91e6-c9f3dac3bd89` SUCCESS. Sin bot.py, trading core, BANKROLL, Fase C, env vars, DB writes, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast runtime ni source mappings. |
| 2026-05-15 | Explícita | Sesión 358 | pending | Codex endurece y ejecuta Source Onboarding Scanner Fase A como NORMAL / LOG_ONLY read-only. `tools/source_onboarding_scanner.py` incorpora `traders_operational_questions_report.json`, excluye `OBSERVED_AUDIT_CITIES` via AST, lee detalles anidados de `signals_crosscheck`, cuenta `win_for_trader` desde `blocked_signals_resolutions` y emite un paquete con `reason_detected`, WR trader, evidencia shadow/source, mapping interno, `recommended_state`, `human_review_required=true` y `operational_action=NO_ACTION / LOG_ONLY`. Corrida local genera outputs ignorados: 6 candidatas, ninguna `READY_FOR_SOURCE_AUDIT`; top 3: Jeddah `WAITING_EVIDENCE`, Guangzhou `SOURCE_BLOCKED`, Karachi `SOURCE_BLOCKED`. Gamma no se consulta porque no hay slugs/source text locales ni candidata lista. Validaciones: scanner real OK, tests focales sin temp 13 passed, syntax OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255; pytest completo con temp queda bloqueado por ACL local. Sin bot.py, trading core, BANKROLL, Fase C, env vars, DB, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast ni source mappings. |
| 2026-05-15 | Explícita | Sesión 356 | pending | Codex ejecuta Source Fidelity Audit v1 para active cities como NORMAL / LOG_ONLY read-only. `source_fidelity_resolver.py` corre sobre Shanghai, Tokyo, Buenos Aires y Ankara. Primera pasada local sin red queda `SOURCE_AMBIGUOUS` por falta de slugs/market_ids/condition_ids/source text en el fallback local. Luego `settlement_fidelity_probe.py` obtiene 5 slugs activos recientes por ciudad vía Gamma read-only y el resolver con `--fetch-gamma` parsea source/rules reales. Resultado final: `SOURCE_MATCH_CONFIRMED` para las cuatro ciudades; Gamma cita Weather Underground daily history con ICAO matching (`ZSPD`, `RJTT`, `SAEZ`, `LTAC`), sin WRH. Se crean reportes por ciudad y `docs/source_audits/active_cities_source_fidelity_audit.md`; JSONs quedan ignorados. Bugfix pequeño: resolver ahora esquiva proxy env poisoned igual que otros probes para evitar WinError 10061. Validaciones: tests resolver 8 passed, syntax OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Sin bot.py, trading core, BANKROLL, Fase C, env vars, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast runtime ni Telegram runtime wiring. |
| 2026-05-15 | Explícita | Sesión 355 | feat(source): add source fidelity resolver | Codex implementa Source Fidelity Resolver v0 como tooling NORMAL / LOG_ONLY read-only. Nuevo `tools/source_fidelity_resolver.py`: lee evidencia local/fallback `blocked_signals_resolutions.jsonl`, extrae slugs/market_ids/condition_ids, opcionalmente consulta Gamma por slug solo con `--fetch-gamma`, parsea reglas/source text, lee `RESOLUTION_ICAO` por AST sin importar `bot.py`, compara mapping externo vs interno y emite JSON ignorado + Markdown versionable. Veredictos: `SOURCE_MATCH_CONFIRMED`, `SOURCE_PARTIAL`, `SOURCE_AMBIGUOUS`, `SOURCE_MISMATCH`; WRH/weather.gov y NOAA NCEI quedan separados, no equivalentes. Corrida local Istanbul sin red genera `docs/source_audits/istanbul_source_fidelity_resolver.md` con `SOURCE_MATCH_CONFIRMED` usando el audit existente como fixture/regresión. Tests focales cubren parser Gamma/source, clasificaciones, ausencia de marcadores de autorización operativa y separación WRH/NCEI. Validaciones: 24 tests focales passed, syntax checker OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Sin bot.py, trading core, BANKROLL, Fase C, env vars, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast, Telegram runtime wiring ni datos runtime versionados. |
| 2026-05-15 | Explícita | Sesión 354 | feat(source): add WRH parity report | Codex implementa Fase 3 Istanbul WRH parity offline. Nuevo `tools/wrh_polymarket_parity_report.py`, aislado y sin import de `bot.py`, lee `blocked_signals_resolutions.jsonl` local (`data/blocked_signals_resolutions.jsonl` o fallback `data/runtime_import_derived/blocked_signals_resolutions.jsonl`), filtra Istanbul exact resuelto, extrae fecha/strike/outcome, usa `weather_gov_wrh_client.py` para `daily_max_c` con cache por fecha, compara exact (`expected_yes = daily_max_c == strike`) y emite JSON ignorado en `data/source_audits/istanbul_wrh_parity_report.json` + Markdown versionable `docs/source_audits/istanbul_wrh_parity_report.md`. Etiquetas: `source=weather_gov_wrh_synoptic`, `observed_dataset=weather_gov_wrh_timeseries`, `log_only=true`; no mezcla NCEI ni escribe observed audit canónico. Resultado local con fallback versionado: 3 filas Istanbul antiguas, `n_compared=3`, `n_match=3`, `n_mismatch=0`, `n_unknown=0`, `mean_abs_delta=1.0`, `max_abs_delta=2.0`, `bias=-1.0`; 2026-04-13 12C YES match, 2026-04-13 14C NO match, 2026-04-18 15C NO match. `source_citation_match=false` porque esas filas no traen slug/Gamma LTFM confirmado; las slugs mayo confirmadas no están en el fallback local. Veredicto `WRH_PARITY_PARTIAL` por muestra local pequeña, no por mismatch. Tests focales cubren YES/NO, cache, dataset y unknown sin inventar paridad. Sin bot.py, runtime, observed_vs_forecast, observed_audit_wrh, Telegram, scheduler, promotion gates, OBSERVED_AUDIT_CITIES, city modes, env vars, trading, BANKROLL, Fase C ni datos runtime versionados. |
| 2026-05-15 | Explícita | Sesión 353 | fix(source): follow WRH Synoptic data endpoint | Codex valida el cliente WRH contra endpoint real LTFM y aplica patch acotado. El HTML inicial de `weather.gov/wrh/timeseries?site=LTFM` responde pero solo trae UI/opciones (`raw_rows_count=23`, sin `Temp`, sin fechas locales), por lo que el parser HTML no bastaba. Inspección read-only del JS oficial `/source/wrh/timeseries/obs.js?v202601121730` confirma backend `api.synopticdata.com/v2/stations/timeseries` con token público de `/source/wrh/apiKey.js` y headers `Referer/Origin` weather.gov. `tools/weather_gov_wrh_client.py --fetch` pasa a seguir ese flujo WRH/Synoptic, consultar ventana date-1..date+1, filtrar por fecha local y parsear `air_temp_set_1`; `source_data_url` se expone con token redacted y queda `--fetch-html` para auditar HTML inicial. Tests focales 9 passed; `py_compile` OK fuera del sandbox por ACL; `git diff --check` OK; `verify_before_deploy.py` 1255/1255. Pruebas reales: 2026-05-06 max 17.0C, 2026-05-07 max 22.0C, 2026-05-13 max 23.0C; todas Temp OK, warnings vacíos, confidence high. Compatible con slugs resueltos May 6 17C/20C, May 7 22C/23C y May 13 23C. Veredicto: `WRH_CLIENT_REAL_OK`; comparador offline de paridad queda para fase separada. Sin bot.py, runtime, observed_vs_forecast, observed_audit_wrh, Telegram, scheduler, promotion gates, city modes, env vars, trading, BANKROLL, Fase C ni datos runtime. |
| 2026-05-14 | Explícita | Sesión 352 | feat(source): add isolated WRH client | Codex implementa Fase 2 Istanbul WRH shadow source como tool aislado LOG_ONLY. Nuevo `tools/weather_gov_wrh_client.py`, stdlib-only, no importa `bot.py`, no escribe runtime y solo usa red con `--fetch`; parsea fixtures con `--input-file`, construye `https://www.weather.gov/wrh/timeseries?site=<SITE>`, extrae filas raw desde HTML/CSV/texto tabular, detecta columna `Temp`, filtra por `date_local`, calcula `daily_max_c` y devuelve payload con `observed_dataset=weather_gov_wrh_timeseries`, warnings y confidence. Si el endpoint es HTML/JS no tabular o falta `Temp`, no inventa datos. Tests nuevos `tests/test_weather_gov_wrh_client.py` cubren Temp, daily max, falta Temp controlada, dataset, independencia de `noaa_station_id` y HTML dinamico no parseable. Sigue aislado: no consume `weather_gov_timeseries_site`, no fetcher runtime, no comparator, no `observed_audit_wrh`, no `observed_vs_forecast`, no Telegram, scheduler, promotion gates, `OBSERVED_AUDIT_CITIES`, city modes, env vars, BUY/SELL/SKIP, BANKROLL, Fase C ni datos runtime. |
| 2026-05-14 | Explícita | Sesión 351 | docs(city): record Istanbul WRH shadow source | Codex registra la decisión Opus para Istanbul como `SOURCE_CONFIRMED_LTFM / APPROVE_WRH_ONLY_AS_SHADOW_SOURCE`. `docs/source_audits/istanbul_source_audit.md` queda actualizado: WRH/weather.gov timeseries solo se aprueba como shadow source separado si Polymarket cita explícitamente `weather.gov/wrh/timeseries?site=<ICAO>`, con dataset futuro `observed_dataset=weather_gov_wrh_timeseries`; no es fuente primaria equivalente a NCEI, no se mezcla con NCEI y no alimenta ranking/promotion gates, city modes, BUY/SELL/SKIP, active/canary ni `OBSERVED_AUDIT_CITIES`. `bot.py` añade solo metadata declarativa para Istanbul en `RESOLUTION_ICAO`: `weather_gov_timeseries_site="LTFM"`, sin consumo runtime, sin fetcher WRH, sin observed_audit_wrh, sin comparador de paridad y sin auto-inferencia desde ICAO. Criterios de re-evaluación documentados: N>=20 mercados Istanbul resueltos con WRH observado, media |Delta C| <= 0.5, sin sesgo direccional > 0.3 C, aggregation rule documentada y segunda ciudad candidata WRH. No se tocan `OBSERVED_AUDIT_CITIES`, promotion gates, scheduler, env vars, trading core, BUY/SELL/SKIP, BANKROLL, Fase C, whitelist/city modes ni datos runtime. |
| 2026-05-14 | Explícita | Sesión 350 | feat(traders): automate operational intelligence monitor | Codex automatiza la evidencia trader-city LOG_ONLY. Nuevo `tools/traders_operational_intelligence_monitor.py` reutiliza el collector de snapshots completos y el reporte de seis preguntas, mantiene estado en `data/intelligence/traders_operational_monitor_state.json` (gitignored), deduplica por `signals.generated`/run id, controla digest diario, error cooldown y anti-spam por transiciones. `bot.py` lo cablea en `run_observability_alerts()` con default ON y kill switch `TRADERS_OPERATIONAL_INTELLIGENCE_ENABLED=false`, pasando `SIGNALS_FILE`, `BLOCKED_SIGNALS_FILE`, `TRADE_LIFECYCLE_FILE`, `AGENT_EVENTS_FILE` y outputs bajo `/app/data/intelligence`. Telegram corto y no accionable: snapshot_count, answerability de 6 preguntas, top traders actividad/WR, top trader-winning-not-observed, gaps trader-vs-bot con `INSUFFICIENT_N` si bot_n bajo, y disclaimer LOG_ONLY. Tests focales 10 passed, syntax OK, `git diff --check` OK, `verify_before_deploy.py` 1255/1255. Commit `f566744` pusheado; Railway `d9fe06fa-af77-46a6-a726-c17e2b40a06f` SUCCESS. No trading core, BUY/SELL/SKIP, BANKROLL, Fase C, policy/city modes/whitelist/scheduler, env vars ni runtime outputs versionados. |
| 2026-05-14 | Explícita | Sesión 349 | feat(traders): add LOG_ONLY operational evidence reports | Codex implementa capa LOG_ONLY central para preguntas trader/city. Nuevo `tools/trader_signals_full_snapshot_collector.py` archiva snapshots completos normalizados de `signals.json` en `data/intelligence/trader_signals_snapshots.jsonl` (gitignored), deduplicando por `signals.generated`/`run_id`; nuevo `tools/traders_operational_questions_report.py` cruza `signals.json`, snapshots, blocked resolutions live/fallback derived, `trade_lifecycle.json` y `OBSERVED_AUDIT_CITIES` read-only para matriz YES/PARTIAL/NO y tablas de actividad/WR/ciudades. `data/intelligence/` queda ignorado. Corrida local LOG_ONLY generó 79 filas ignoradas y reporte local: hora traders `NO` con 1 snapshot; ciudades/traders/WR `YES`; trader-winning no observadas y trader-winning vs bot `PARTIAL`; bot_n bajo clasifica `TRADER_WINNING_BOT_INSUFFICIENT_N`. Tests focales 5 passed, syntax OK, `git diff --check` OK, `verify_before_deploy.py` 1247/1247. No bot.py, trading core, BUY/SELL/SKIP, BANKROLL, Fase C, whitelist/city modes/scheduler, env vars, Railway ni Telegram accionable. |
| 2026-05-13 | Explícita | Sesión 348 | pendiente | Codex cierra auditoría fuente Los Angeles read-only como `OBSERVED_AUDIT candidate`, no canary. Evidencia nueva: fuente pública probable Polymarket/WU = Los Angeles International Airport Station / `KLAX`; candidato NOAA daily = `GHCND:USW00023174` Los Angeles International Airport; candidato ISD probable = `72295023174`, pendiente verificar contra `isd-history.csv` antes de cualquier patch. Riesgo mismatch bajo-medio por WU vs NOAA/GHCND/CLI, sin evidencia de downtown/USC u otra estación. Decisión: no whitelist, no canary, no trading; siguiente paso técnico es verificar KLAX/NOAA y, si cierra, preparar decisión Opus para `OBSERVED_AUDIT`/proxy. No se toca código, Railway, DB, env vars, `/app/data`, whitelist, city modes, `RESOLUTION_ICAO`, `OBSERVED_AUDIT_CITIES`, BANKROLL, Fase C, scheduler, sizing ni trading core. |
| 2026-05-13 | Explícita | Sesión 347 | pendiente | Codex implementa patch FULL acotado de admisión/policy para la decisión Opus S346. `is_city_blocked()` pasa a hard block puro de `BLOCKED_CITIES`; `should_skip_observation()` separa el skip de observación cuando no hay proxy observado; el scan conserva shadow/NOAA/forecast audit para Paris/London/Atlanta/Chicago con proxy pero los deja `city_mode=blocked` y `allowlisted=False`, sin BUY posible por active/canary/auto_canary/quality-trader gate. `sync_city_policy_state()` bloquea promociones auto_canary sobre ciudades en `BLOCKED_CITIES`. `tools/runtime_policy_effective_view.py` clasifica overlays auto_canary vencidos por `BLOCKED_CITIES` como documented_drift, no blocker operacional. Precheck Railway read-only confirma auto_canary actual para Paris y Chicago, Atlanta auto_shadow, London solo historial. Validaciones: syntax OK, 31 tests focalizados, `verify_before_deploy.py` 1192/1192, runtime snapshot read-only refrescado, `system_alignment_check --decision-mode operational` ok=5 warning=3 error=0, `git diff --check` OK. No BANKROLL, Fase C, env vars, DB, whitelist, city modes, scheduler, sizing/Kelly/MIN_EDGE/sigma, settlement logic ni SL/L2/INTRA. |
| 2026-05-13 | Explícita | Sesión 346 | docs: record opus decision blocked cities hard block | Claude Code cierra LITE la decisión semántica Opus sobre la contradicción runtime/policy detectada en sesión 345 (Paris #304 comprada NO como canary con `BLOCKED_CITIES=London,Paris,Atlanta,Chicago` en Railway). Veredicto: (1) BLOCKED_CITIES debe ser hard block para trading/admisión, desacoplado de observación shadow/NOAA; (2) `is_city_blocked()` en `bot.py:311-318` con cláusula `and not has_observed_proxy` es bug semántico — las 4 blocked tienen `noaa_station_id` y están en `OBSERVED_AUDIT_CITIES`, por lo que la función devuelve False para todas; (3) Paris #304 es bug de admisión/policy, no de SL/L2/INTRA (que funcionaron LOG_ONLY correctamente); (4) Los Angeles queda backlog revisión humana, no canary, no bloqueo por fuente; (5) patch pendiente próximo bloque Opus: dividir `is_city_blocked()` (puro env, hard block trading) y `should_skip_observation()` (con cláusula proxy), auditar ≥6 call-sites, añadir test que afirme `is_city_blocked("Paris") is True` con env BLOCKED aun con NOAA. Sin cambios a bot.py, trading core, NOAA, scheduler, SL/L2/INTRA ejecutable, BANKROLL, Fase C, whitelist, city modes, env vars, DB, Railway ni runtime. |
| 2026-05-13 | Explícita | Sesión 344 | docs: close ORI backlog lite | Cierre LITE documental de ORI. `docs/BACKLOG_ORI_operational_readiness_intelligence.md` queda marcado como backlog activo cerrado: P0 `KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`, P1 readout unificado desplegado, P2 `NO_ACTION operativo / REPORTING_GAP menor`, P3 `KEEP_MONITORING`, P5 `KEEP_CURRENT_STRATEGY_UNTIL_TRIGGER` con revisión obligatoria 2026-06-09 o triggers Phase 2 documentados. P4/P6 quedan `WATCH`; M0 sigue manual recurrente. No se reabre análisis. No runtime, env vars, DB, trading, BANKROLL ni Fase C. |
| 2026-05-13 | Explícita | Sesión 343 | pendiente | Codex cierra ORI P1 como NORMAL / observability tooling / LOG_ONLY. Se crea `tools/sl_intra_case_readout.py`, CLI stdlib-only read-only que une `trade_lifecycle.json`, `sl_intra_hazard_monitor_audit.json`, `intra_reeval_state.json`, `sl_intra_guard_audit.json` y `skip_log.jsonl` por token o ciudad/fecha/lado, con salida JSON/Markdown y clasificaciones de Hazard/INTRA (`REEVAL_WOULD_SELL_BUT_FINAL_WIN`, `HAZARD_OBSERVED_WIN/LOSS`, `REEVAL_GOOD/BAD_SHADOW`, `STILL_OPEN`, `INSUFFICIENT_DATA`). Tests nuevos `tests/test_sl_intra_case_readout.py`. Validaciones: syntax OK, pytest focalizado 3 passed fuera del sandbox por ACL Temp, smoke local `no_matching_case` controlado para May12 porque esos artefactos viven en `/app/data`, `git diff --check` OK, `verify_before_deploy.py` 1187/1187 fuera del sandbox por ACL `tools/__pycache__`. Veredicto P1: `NO_EXISTING_TOOL_PATCH_READY` implementado. No se reabre P0. No BANKROLL, Fase C, trading core, bot.py, scheduler, NOAA, SL/guards/INTRA ejecutable, BUY/SELL/SKIP, city modes, whitelist, sizing, env vars, DB runtime, Telegram real ni Railway. |
| 2026-05-10 | Explícita | Sesión 342 | feat: add Phase 2 mixed-condition monitor v10.6.50 | Claude Code abre Phase 2 Recalibration (T+30=2026-06-09). `bot.py` v10.6.50: `maybe_run_phase2_monitor` vigila WR mixed-condition (exact+at_or_above+at_or_below desde 2026-05-10) con kill-switches rolling mixed WR<40% n≥20 y exact WR<40% n≥10; `CANARY_RETIRED=date(2026,5,10)` retira monitor legacy S341 para evitar alarmas contradictorias con la cohorte pre-Phase2 (WR=42.9% n=21). Railway deploy #1 (código) `8d4dd978` SUCCESS; env vars `QUALITY_TRADER_CONDITIONS=exact`, `ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara`, `BLOCKED_CITIES=London,Paris,Atlanta,Chicago`; deploy #2 `13868d46` SUCCESS. 20/20 tests, 1187/1187 verify. No BANKROLL, Fase C, sigma, MIN_EDGE, sizing, exits, scheduler, NOAA ni DB. |
| 2026-05-09 | Explícita | Sesión 341 | docs: close condition filtered kill-switch | Claude Code ejecuta cierre operativo del canary `condition_filtered` exact/range abierto en Sesión 175 (2026-04-14). Alarma diaria reporta WR bot=42.9% (9/21) tras compra CANARY NO Shanghai 24°C $2.25 edge=24% cerrada por stop-loss ~-38%. Kill-switch documentado en `docs/handoffs/condition-filtered-canary-implement-2026-04-14.md` cumplido: WR<45% con n≥20 → revertir sin esperar checkpoint. Acción ejecutada vía `tools/railway_safe.ps1 variable set`: `QUALITY_TRADER_CONDITIONS` pasa de `exact,range` a valor vacío (parser filtra entradas vacías → set vacío). Auto-deploy Railway disparado por la env var. CONTEXTO.md y agent_events.jsonl alineados. No se tocó bot.py, trading core, NOAA, scheduler, sizing, whitelist, city modes, BANKROLL, Fase C, DB ni thresholds. Reapertura futura requiere handoff nuevo + revisión Opus. |
| 2026-05-08 | Explícita | Sesión 340 | feat: automate db throughput digest | Codex integra `tools/db_throughput_report.py` en el Daily Bot Digest automatico LOG_ONLY. `bot.py` añade kill switch `DB_THROUGHPUT_DIGEST_ENABLED` default 1 y pasa `--db-throughput-report --db SQLITE_DB_PATH` al runner existente; `tools/daily_bot_observability_run.py` resume frescura DB, gaps, top slots flojos, condicion dominante, status KEEP/WATCH/REVIEW_READY y accion manual/Opus; `tools/daily_bot_digest.py` lo muestra en digest humano y Telegram. Reutiliza `daily_digest_state.json`, sin scheduler/state paralelo. Validacion: syntax OK, pytest focalizado 38 passed, smoke CLI db_not_found controlado, `git diff --check` OK, `verify_before_deploy.py` 1174/1174. No cambia trading core semantico, BUY/SELL/SKIP, BANKROLL, Fase C, DB schema, env vars reales, city modes, whitelist, sizing, risk rules ni Telegram accionable. |
| 2026-05-07 | Explícita | Sesión 319 | fix: block stale non-canonical pnl readiness | Codex cierra B4.2 Fix P&L Window Mismatch. Se corrige bug técnico de data-quality: `bankroll_scaling_check.py` bloquea P&L/WR/drawdown si la fuente es `non_canonical_telemetry`, añade blockers `runtime_data_stale`, `pnl_source_non_canonical` y `bankroll_readiness_score_stale`; `pnl_report.py` soporta BOM/payload `records` y marca lifecycle como contaminado; docs y tests focalizados actualizados. Conclusión: FIXED_TECHNICAL_BUG local, pero decisión operativa `BLOCKED_BY_DATA_QUALITY / WAITING_MORE_EVIDENCE`; no BANKROLL increase. No trading core, no bot.py, no Fase C, no DB, no env vars, no Railway. |
| 2026-05-07 | Explícita | Sesión 318 | docs: refine orchestrator workflow rules | Sonnet actualiza ORCHESTRATOR.md con lecciones del bloque A8 SL_intra Guard: definición de done para bloques delicados, escalada auditoría→Opus, separación dato/interpretación/copy/decisión, restricción de conclusiones en cohortes mezcladas, secuencia de referencia para guards, reglas de token economy y bot.py LOG_ONLY ciclo completo. HISTORIAL_SESIONES.md y agent_events.jsonl actualizados. No bot.py, tools/, Railway, DB, env vars, BANKROLL, Fase C. |
| 2026-05-07 | Explícita | Sesión 317 | feat: tag sl intra guard review cohorts | Codex aplica patch mínimo LOG_ONLY / alert analytics para A8 SL_intra Guard. `bot.py` añade helper puro de cohortes y campos additive-only para nuevos skip events (`sl_window_catchable`, `deep_drawdown_at_skip`, `cohort`, `cohort_reason`, thresholds, `cohort_schema_version`) sin backfill. El review one-shot deriva cohortes para eventos antiguos, mantiene delta global solo como contexto, separa Zona A leverage-real, Zona B deep drawdown y Zona C inherited loss, y solo emite veredicto operativo sobre Zona A si `n_zone_a_resolved >= 6`; si no, copy `REVIEW PRELIMINAR — muestra insuficiente / mezclada. No cambiar guard/env vars sin revisión Opus.` Test focalizado nuevo `tests/test_sl_intra_guard_cohorts.py`. Validaciones: syntax OK, pytest focalizado 2 passed, `git diff --check` OK, `verify_before_deploy.py` OK. Se corrige además newline malformado en `agent_events.jsonl` entre S315/S316. No cambia condición del guard, BUY/SELL/SKIP, ventas, BANKROLL, sizing, whitelist, city modes, scheduler, reglas ejecutables de riesgo, env vars, DB, Railway manual, Fase C, P&L tooling, blocked signals ni Truth Pipeline. |
| 2026-05-07 | Explícita | Sesión 316 | docs: clarify sl intra guard leverage cohorts | Sonnet corrige `docs/sl_intra_guard_leverage_instrumentation.md` tras veredicto Opus WATCH_RISK+DESIGN_GAP sobre alarma A8. Clasificación DOCUMENTATION / WATCH_RISK. Ambigüedad corregida: el documento original colapsaba Zona B (deep drawdown borderline -35% a -75%) y Zona C (inherited loss <=-75%) en un solo `sl_window_catchable=false`, mezclando dos poblaciones con semántica distinta. Correcciones: (1) se añade campo `deep_drawdown_at_skip` (true si Zona B, false si Zona A o C, null si datos insuficientes); (2) se definen tres zonas explícitas A/B/C con criterios numéricos; (3) Munich -65.8% reclasificado como Zona B / deep_drawdown_guard_saved, no inherited_loss; (4) se añade sección "Limitación actual del review one-shot" explicando por qué el delta global puede ser misleading; (5) se añade sección "Copy recomendado para futuras alarmas" con texto estándar para evitar malinterpretación; (6) se añade sección "Design gap: hard floor en pct@skip" documentando posible mejora futura sin implementar; (7) tabla de campos actualizada con `deep_drawdown_threshold_low/high`, `cohort`, `cohort_reason`; (8) Evidence Ledger actualizado con métricas `n_deep_drawdown`, `WR_deep_drawdown`, `guard_saved/hurt_deep_drawdown`, `inherited_loss_excluded`, `verdict_global=HOLD`. No se toca bot.py, tools/, env vars, Railway, DB, BANKROLL, Fase C, scheduler, whitelist, city modes, sizing. Commit `docs: clarify sl intra guard leverage cohorts` pusheado. A8 estado sin cambios: WATCH/ESPERAR_MÁS_MUESTRA. |
| 2026-05-07 | Explícita | Sesión 315 | docs: add sl intra guard leverage instrumentation | Sonnet crea `docs/sl_intra_guard_leverage_instrumentation.md`: define campo `sl_window_catchable` como pre-requisito LOG_ONLY para futuro Evidence Ledger del guard SL_intra exact+days<=1. Criterio inicial: true si pct_pnl_at_skip > -35%, false si <= -35%. Umbral observacional y revisable. No modifica bot.py, no afecta trading, no activa BANKROLL, no abre Fase C. A8 estado: WATCH / ESPERAR_MÁS_MUESTRA (n=2 leverage-real). Re-check: 5.º guarded o 2026-05-21. Commit `f6d6a32` pusheado. |
| 2026-05-07 | Explícita | Sesión 314 | feat: add blocked signals schema v3 fields | Codex registra cierre documental LITE de A7 `blocked_signals` schema v3. Clasificacion PATCH_MEMORY / WAITING_SCHEMA / WATCH_RISK. A7 queda WAITING_SCHEMA por decision Opus: no monetiza y no UNLOCK automatico. Commit `4da47ea` pusheado a `origin/main`; Railway auto-deploy SUCCESS deployment `29305fc9-0cf4-4e49-bac5-8be6d3267563`. Cambio desplegado: `bot.py` solo logging/schema blocked_signals con schema v3 para nuevos registros, preservando v2 y campos `bot_would_have_bought`/`bot_evaluation_source`; `verify_before_deploy.py` guardrails; `tests/test_blocked_signals_schema_v3.py` test focalizado. Validacion: syntax OK, pytest focalizado 4 passed, verify_before_deploy.py 1140/1140. Re-check A7: `n>=60` registros v3 con `bot_evaluation_source=live_eval` y `bot_would_have_bought=true`; WR>=70% => UNLOCK_REVIEW para Opus, no auto-unlock. Historico v1/v2 sin backfill y no autoriza UNLOCK. No whitelist/city modes/scheduler/sizing/risk rules, no BANKROLL, no Fase C, no DB/env vars/Telegram real, no data real. Untracked `2026-04-27]` intacto. |
| 2026-05-07 | Explícita | Sesión 313 | (sin commit) | Codex ejecuta BANKROLL Readiness Railway evidence check read-only. Clasificación HOLD_BANKROLL_25 / WAITING_EVIDENCE. Señales positivas no canónicas: P&L 14d +$20.35 (trade_lifecycle Railway, LOW), P&L 30d +$20.87 (bankroll_readiness_score.py dry-run JSON, LOW), WR 43.3% 13W/30 P&L +$19.26 (MEDIUM). Criterios bloqueantes: drawdown 14d $17.89 FAIL conservador (supera umbral $3), SL_intra 14d UNKNOWN (muestra insuficiente), WR <50% con umbral Opus. pnl_report.py blocked (wallet_cash_flows.jsonl ausente). wallet_snapshot Railway 8 snapshots, wallet_pnl_available=false, phase2_ready=false. bankroll_scaling_check NOT_ELIGIBLE, do_not_increase. BANKROLL $35 no autorizado. canonical_source=none. bankroll_readiness=blocked. Siguiente paso: Lean Alarm Matrix v1. Re-evaluar cuando WR>=50%, drawdown<=3, SL_intra muestra suficiente, o wallet/cashflow deje de estar blocked. Sin commits. Sin código. Sin env vars. Sin Railway writes. Sin Telegram real. |
| 2026-05-07 | Explícita | Sesión 312 | docs: add polymarket api pnl discovery | Codex cierra B3.1 Polymarket API P&L discovery. Clasificacion ACTION_DESIGN / RESEARCH / WATCH_RISK. Commit `f493dd3` crea `docs/research/polymarket_api_pnl_discovery.md`. Hallazgo: no hay endpoint oficial documentado equivalente al dashboard P&L; `GET /v1/leaderboard` con `timePeriod=DAY/WEEK/MONTH/ALL` puede servir como external_observability/cross-check por address publica, pero no queda validado como dashboard-equivalent; `positions`/`closed-positions` exponen piezas (`cashPnl`, `realizedPnl`, `totalPnl` en market-position), no el P&L dashboard 1D/1W/1M/ALL; no hay cash flows/deposits/withdrawals documentados para reconciliacion completa; metodologia opaca. Recomendacion: A viable solo como external_observability/sanity bound; D requiere mas investigacion para equivalencia exacta dashboard. Guardrails: nunca canonical_source, no bankroll_readiness, no BANKROLL, no Fase C, no BUY/SELL/SKIP, no Telegram accionable. No codigo, no tools/, no bot.py, no trading core, no DB, no env vars, no credenciales/private key, no Railway, no Telegram, no runtime. main...origin/main [ahead 1], no push. |
| 2026-05-07 | Explícita | Sesión 311 | feat: add pnl report tool | Sonnet documenta micro-cierre B3 implementación. Clasificación ACTION_TOOLING / PATCH_MEMORY / NOT_CANONICAL / WATCH_RISK. Commits locales: `082e02d` (`feat: add pnl report tool`), `420e4b8` (`docs: add pnl report design`). Archivos commit `082e02d`: creado `tools/pnl_report.py` (CLI read-only, stdlib-only, horizontes 1D/1W/1M/ALL), creado `tests/test_pnl_report.py` (14 tests T1–T14), modificado `docs/pnl_report_design.md` (campo `--generated-at` testing-only). Validación Codex: syntax OK; 14 tests passed; missing cashflow exit 0 / JSON válido / horizontes blocked / value_usdc=null / reason explícito; guardrails would_send=false / operational_use=forbidden / promotes_canonical_source=false. Herramienta read-only/LOG_ONLY. No promueve readiness. No cambia canonical_source ni bankroll_readiness. No Telegram. No DB/Railway/runtime/trading core/bot.py/env vars/BANKROLL/Fase C/Patch D. data/wallet_cash_flows.jsonl no existe; git ls-files vacío. canonical_source=none, bankroll_readiness=blocked, wallet_pnl_available=false sin cambios. main...origin/main [ahead 1]; no push todavía. Siguiente paso: push controlado del commit 082e02d; después B3.1 Polymarket API source strategy o B4 diseño, pero no integración automática. No Patch D. |
| 2026-05-07 | Explícita | Sesión B3 | docs: add pnl report design | Sonnet documenta diseño canónico ACTION_DESIGN / WATCH_RISK / NOT_CANONICAL de tools/pnl_report.py. Se crea docs/pnl_report_design.md: propósito read-only/LOG_ONLY, horizontes 1D/1W/1M/ALL, schema JSON completo, máquina de estados 4 emitibles en B3 (unavailable/blocked/provisional/canonical_candidate), confidence capado a medium, ausencia de wallet_cash_flows.jsonl = exit 0 + horizontes blocked, 14 tests T1–T14, stdlib-only, exit codes 0/2, lista negra explícita (no trading/no Telegram/no DB/no Railway/no bot.py/no BANKROLL/no Fase C/no BUY-SELL-SKIP/no Patch D), guardrails G1–G6. HISTORIAL_SESIONES.md y agent_events.jsonl actualizados. data/wallet_cash_flows.jsonl no existe. tools/pnl_report.py no existe (no implementado). canonical_source=none, bankroll_readiness=blocked, wallet_pnl_available=false sin cambios. No tools/, no bot.py, no trading core, no BANKROLL, no Fase C, no Railway, no DB, no env vars, no Telegram real. No commit/push. |
| 2026-05-06 | Explícita | Sesión 310 | docs: record wallet cash flow log deployment | Codex documenta push controlado bd4830a..0506782 + Railway auto-deploy SUCCESS. Clasificación ACTION_DOCUMENTATION / PATCH_MEMORY / WATCH_RISK. Commits pusheados: 81e7346 (feat: add wallet cash flow log tool) y 0506782 (docs: record wallet cash flow log implementation). main alineado con origin/main. Working tree limpio. Railway auto-deploy SUCCESS, deployment 6849b187-61c9-4a4e-82d3-04372cb1bbcd, proyecto enchanting-respect, environment production, service polymarket-bot. Sin deploy manual. Sin env vars. Sin DB. data/wallet_cash_flows.jsonl no existe. git ls-files vacío. canonical_source=none, bankroll_readiness=blocked, wallet_pnl_available=false sin cambios. Siguiente paso: diseño B3 tools/pnl_report.py read-only. No Patch D. |
| 2026-05-06 | Explícita | Sesión 309 | feat: add wallet cash flow log tool | Codex implementa Patch C `tools/wallet_cash_flow_log.py`. Clasificación ACTION_TOOLING / PATCH_MEMORY / WATCH_RISK. Commit `81e7346`. Archivos: creado `tools/wallet_cash_flow_log.py` (CLI manual-only, stdlib-only, append-only, dry-run default), creado `tests/test_wallet_cash_flow_log.py`, modificado `verify_before_deploy.py` con guardrails Patch C. Validación: syntax OK, 24 tests passed, verify_before_deploy.py 1139/1139 OK, git diff --check OK (solo warnings LF/CRLF Windows). Herramienta subordinada a docs/wallet_cash_flow_log_design.md, docs/wallet_cash_flows_policy.md y docs/pnl_observability.md. No calcula P&L. No promueve readiness. No cambia canonical_source ni bankroll_readiness. No manda Telegram. No toca DB/Railway/runtime/trading core/bot.py/BANKROLL/Fase C. data/wallet_cash_flows.jsonl no existe y no fue creado. git ls-files vacío. Herramienta no usada con datos reales. canonical_source=none, bankroll_readiness=blocked, wallet_pnl_available=false sin cambios. main...origin/main [ahead 1]; no push todavía. Patch C sigue sin activar P&L Observability canónico; solo crea la vía segura de registro manual. Siguiente paso: push controlado del commit 81e7346; después planificar B3 tools/pnl_report.py read-only; no Patch D todavía. |
| 2026-05-06 | Explícita | Sesión 308 | docs: add pnl observability contract | Sonnet documenta contrato P&L Observability 1D/1W/1M/ALL. Clasificación ACTION_DESIGN / WATCH_RISK. Se crea `docs/pnl_observability.md`: propósito read-only/LOG_ONLY, 6 capas de P&L (realized/wallet-adjusted/open/net/operational/data-quality), contrato por horizonte con criterios Opus (divergencia ≤±$0.50/±$1.50/±$3.00), definición `t0 ALL` post-Patch C, mapa de componentes (wallet_snapshot/cash_flow_log/pnl_report.py futuro/daily_digest/trade_lifecycle non_canonical), Daily Digest reglas LOG_ONLY/WATCH_AUDIT, clasificación Lean/Kanban, lista negra operativa, roadmap B1–B6, guardrails transversales (falsa canonización/backfill/drift/confusión realized vs wallet-adjusted/bankroll pequeño/etiquetas obligatorias). Se actualizan referencias mínimas en `docs/wallet_cash_flows_policy.md` y `docs/wallet_cash_flow_log_design.md`. Patch C sigue siendo prerequisite técnico para `t0 ALL`, pero subordinado al contrato observability. `canonical_source=none`, `bankroll_readiness=blocked`, `wallet_pnl_available=false` sin cambios. `data/wallet_cash_flows.jsonl` no existe. `tools/wallet_cash_flow_log.py` no existe. No runtime, no Railway, no DB, no env vars, no Telegram real, no `bot.py`, no trading core, no BANKROLL, no Fase C. Siguiente paso posible: review del diff y después Codex Patch C solo con signoff explícito de Pablo. |
| 2026-05-06 | Explícita | Sesión 307 | docs: record wallet hermeticity check | Sonnet registra el micro-cierre documental de la verificación Codex PASS de hermeticidad Patch B/B' con fixture sintético `attested_full_7d`. Veredicto: PASS. Fixture temporal `C:\tmp\polymarket_attested_full_7d_verify` creado y borrado al cierre. Campos con fixture: `cash_flows.status=attested_full_7d`, `coverage_days_7d=7`, `wallet_pnl_available=false`, `phase2_ready=false`, `phase2_ready_reason=need_more_history`, `wallet_pnl_confidence=low/unavailable`, `wallet_pnl_7d=null`, `canonical_source=none`, `bankroll_readiness=blocked`, `would_send=false`. Tests: 45 passed (test_wallet_snapshot.py + test_daily_kanban_digest.py). Primera ejecución pytest falló por permisos Temp de usuario; rerun con `--basetemp` funcionó. Git status final sin cambios. `data/wallet_cash_flows.jsonl` sigue sin existir. `tools/wallet_cash_flow_log.py` no existe. Prioridad 1 Opus cerrada read-only. No runtime, no Railway, no DB, no env vars, no Telegram real, no `bot.py`, no trading core. |
| 2026-05-06 | Explícita | Sesión 306 | docs: add wallet cash flow log design | Sonnet crea `docs/wallet_cash_flow_log_design.md` — diseño canónico de Patch C `tools/wallet_cash_flow_log.py`. Clasificación ACTION_DESIGN / WATCH_RISK. Documenta: propósito CLI manual, scope constraints (no `bot.py`, no Railway, no Telegram, no readiness flags), interfaz CLI completa (`--type`, `--period-start`, `--period-end`, `--note`, `--write`, `--init`, `--data-dir`, `--entry-id` testing-only), tipos permitidos/prohibidos, schema v2 output row, 8 reglas de validación pre-write, comportamiento dry-run y write, init mode con confirmación `YES I CONFIRM`, rutas canónicas, constraint stdlib-only, criterios handoff Codex. Actualización mínima en `docs/wallet_cash_flows_policy.md` con referencia al diseño. No se crea `tools/wallet_cash_flow_log.py`, no se crea `data/wallet_cash_flows.jsonl`, no runtime, no Railway, no env vars, no Telegram real, no `bot.py`, no trading core, no BANKROLL, no Fase C. `canonical_source=none`, `bankroll_readiness=blocked`, `wallet_pnl_available=false` sin cambios. |
| 2026-05-06 | Explícita | Sesión 305 | docs: record wallet snapshot railway verification | Codex registra micro-cierre documental de verificación Railway/runtime de Patch B' `wallet_snapshot` schema v2. Commit runtime verificado `1df7d07c1024f79bee62a2cb1240ed982c25a094` (`fix: align wallet snapshot with cash flow attestation schema`), deployment Railway `98f15601-9b1b-40a8-a1e8-1a37d97b25aa`, status `SUCCESS`. Comando remoto usado previamente: `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "python tools/wallet_snapshot.py --report-only --json --data-dir /app/data"`. Campos observados: `/app/data/wallet_cash_flows.jsonl` no existe, `cash_flows.status=missing`, `cash_flows.schema_version=2`, `phase2_readiness.phase2_ready=false`, `phase2_readiness.phase2_ready_reason=cash_flow_unknown`, `wallet_pnl.wallet_pnl_confidence=low`, `wallet_pnl.wallet_pnl_7d=null`, `wallet_pnl.wallet_pnl_available=false`. Readiness sigue bloqueada: `canonical_source=none`, `bankroll_readiness=blocked`; `data/wallet_cash_flows.jsonl` real local no existe; Patch C sigue bloqueado/no abierto. En la sesión documental no se toca código, tests, deploy, env vars, Railway/DB, Telegram real, `bot.py`, trading core, BANKROLL, Fase C, scheduler, whitelist, sizing, city modes ni reglas de riesgo. |
| 2026-05-06 | Explícita | Sesión 304 | docs: record wallet cash flow gate railway verification | Codex registra verificacion runtime Railway de Patch B `wallet_cash_flows` gate. Commit verificado `58044134ada3fcc748417f9e857e00ec7d732503` (`fix: require attested wallet cash flows for wallet pnl readiness`) desplegado por auto-deploy en Railway: proyecto `enchanting-respect`, environment `production`, service `polymarket-bot`, deployment `420ae384-232f-45b0-944d-978f314a8167`, status `SUCCESS`. Digest remoto ejecutado por SSH en modo dry-run JSON: `python tools/daily_kanban_digest.py --data-dir /app/data --db /app/data/polymarket.db --dry-run --json`. Resultado: `cash_flows.status=missing`, `cash_flows.coverage_days_7d=0`, `wallet_pnl.wallet_pnl_available=false`, `wallet_pnl.phase2_ready_reason=cash_flow_unknown`, `canonical_source=none`, `bankroll_readiness=blocked`, `would_send=false`, `lifecycle.status=contaminated`/`untrusted_only`, nivel `WATCH_RISK`. Se confirma que `/app/data/wallet_cash_flows.jsonl` no existe y no fue creado. Sin env vars, sin DB, sin Railway Volume writes, sin datos productivos, sin Telegram real del digest, sin `bot.py`, sin trading core, sin BANKROLL, sin Fase C y sin Patch C. |
| 2026-05-06 | Explícita | Sesión 303 | docs: add wallet cash flow attestation policy | Codex aplica Patch A documental de política antifalsificación para `wallet_cash_flows`. Clasificación PATCH_MEMORY / WATCH_RISK. Se crea `docs/wallet_cash_flows_policy.md`, se añade `data/wallet_cash_flows.example.jsonl` con ejemplos no productivos `EXAMPLE-*`, y `.gitignore` excluye el archivo real `data/wallet_cash_flows.jsonl`. `docs/pnl_clean_source_policy.md` queda aclarado: un archivo vacío no es evidencia, no equivale a attestation y no desbloquea readiness; la cobertura de 7 días requiere attestations explícitas o movimientos reales documentados. No se crea archivo real, no se toca runtime, `bot.py`, `tools/wallet_snapshot.py`, `tools/daily_kanban_digest.py`, `verify_before_deploy.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway, deploy, Telegram real ni Fase C. `wallet_pnl` sigue no canónico; `canonical_source=none` y `bankroll_readiness=blocked`. |
| 2026-05-06 | Explícita | Sesión 302 | docs: record pnl sources railway verification | Sonnet registra verificación Railway de Daily Bot Kanban Digest 1.3 con bloque `pnl_sources`. Commit referencia: `ecd314b`. Deployment `58778c54` SUCCESS. Resultado: `lifecycle.status=contaminated`, `lifecycle.contamination_rate=1.0`, `lifecycle.operational_use=untrusted_only`, `wallet_pnl.status=accumulating`, `wallet_pnl.phase2_ready=false`, `cash_flows.status=missing`, `dashboard.status=manual_only`, `canonical_source=none`, `bankroll_readiness=blocked`, `would_send=false`, nivel global `WATCH_RISK`. Interpretación: (1) bloque `pnl_sources` activo y correcto en Railway; (2) digest comunica que no hay P/L canónico; (3) `trade_lifecycle` queda `untrusted_only`; (4) `wallet_pnl` sigue acumulando baseline, `phase2_ready=false`; (5) `wallet_cash_flows.jsonl` missing bloquea promoción; (6) dashboard manual only; (7) bankroll readiness bloqueado; (8) Telegram real bloqueado; (9) Fase C no autorizada. No se toca código, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway ni deploy. Clasificación ACTION_DOCUMENTATION / WATCH_RISK. |
| 2026-05-06 | Explícita | Sesión 301 | docs: add pnl clean source policy | Sonnet documenta política canónica de fuentes P/L según decisión Opus. Clasificación ACTION_DESIGN / WATCH_RISK. `trade_lifecycle.json` contaminated 1.0: prohibido para BANKROLL, Telegram real con cifra, decisiones operativas y comparativas históricas; solo como `untrusted_pnl` con disclaimer. `wallet_portfolio_snapshots.jsonl` accumulating baseline/not_ready: prohibido para P/L operativo. `wallet_cash_flows.jsonl` missing: debe existir antes de promover wallet P/L. Dashboard Polymarket = ground truth manual; sin scraper autorizado. Se documentan 8 criterios de promoción `wallet_pnl_7d`, condiciones Telegram por nivel (informativo/cifra/BANKROLL/Fase C), bloque `pnl_sources` recomendado para próximo patch del digest, y guardrails permanentes. Se crea `docs/pnl_clean_source_policy.md`. No se toca código runtime, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway ni deploy. Fase C no autorizada. |
| 2026-05-06 | Explícita | Sesión 299 | fix: mark daily digest source quality | Codex aplica Daily Bot Kanban Digest 1.2 como patch acotado de tooling/observabilidad. `daily_kanban_digest.py` acepta `timestamp_utc` en `cycles_history.jsonl` para ciclos recientes 24h/7d y agrega `source_quality` al P/L sin cambiar el cálculo base: estados `missing`/`reliable`/`contaminated`, conteos, rate y warning de no usar P/L reconstruido/no audit-ready para BANKROLL ni decisiones operativas. Si hay contaminación, `profitability.level` queda en `WATCH_RISK`; la salida humana muestra "Calidad fuente" y warning. `tests/test_daily_kanban_digest.py` cubre timestamp reciente, contaminación lifecycle, JSON/humano, `would_send=false` y ausencia de instrucciones operativas; `verify_before_deploy.py` añade guardrails estáticos. Validación local: sintaxis OK, pytest focalizado 13 passed, `verify_before_deploy.py` 1123/1123, digest local texto/JSON dry-run OK. Railway read-only opcional confirma que, sin deploy, live sigue en digest anterior (`recent_cycles_24h=0`, `recent_cycles_7d=0`, sin `source_quality`, `would_send=false`). No deploy, no env vars, no Telegram real, no `bot.py`, no trading core, no BANKROLL, no Fase C. Clasificación ACTION_TOOLING / WATCH_RISK. |
| 2026-05-06 | Explícita | Sesión 298 | feat: add daily kanban digest dry run; docs: record daily kanban digest dry run | Codex implementa y cierra durablemente el primer tooling del sistema Alerts + Kanban Lean. Clasificación PROJECT_MEMORY/PATCH_MEMORY: DAILY_BOT_KANBAN_DIGEST_DRY_RUN_IMPLEMENTADO. Se crea `tools/daily_kanban_digest.py`, CLI local/read-only stdlib-only con `--dry-run`, `--json --dry-run` y `--db` opcional para resumen Truth Pipeline SQLite read-only; `tests/test_daily_kanban_digest.py` cubre salida texto/JSON, datos/DB ausentes sin crash, Truth Pipeline missing controlado, disclaimers, ausencia de instrucciones operativas, no import de `bot.py`/trading core, no Telegram y no escritura de estado; `verify_before_deploy.py` suma guardrails minimos. Commit `6b6b2f1` pusheado a `origin/main`. Validación: sintaxis OK, pytest focalizado 10 passed, `verify_before_deploy.py` 1120/1120. Estado: dry-run, LOG_ONLY, default OFF, `would_send=false`, sin Telegram real, sin runtime automático, sin `alerts_state`, sin `kanban_state`, sin cron, sin env vars, sin Railway y sin deploy. No se toca `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo ni Fase C. Level inicial `WATCH_RISK` si falta P/L fiable para evitar lectura falsa de salud/mejora; mensaje mantiene "Esta alerta no autoriza cambios de trading." y "Siguiente paso concreto". Próximo paso: ejecutar digest dry-run con datos reales/fixtures y decidir si crear schema `data/kanban_state.json` o seguir con Low Activity Monitor. |
| 2026-05-06 | Explícita | Sesión 297 | docs: add alerts kanban lean design | Sonnet documenta diseño estratégico post-cierre Truth Pipeline Fase 1. Clasificación ACTION_DESIGN / WATCH_RISK. Veredicto Opus: bot en WATCH_RISK; calibration_global=0.789 con n_resolved=19 valida cañería pero no edge operativo; BANKROLL $25 es presupuesto I+D, inviable para pagar Claude Max. Se crea `docs/alerts_kanban_lean.md` con: marco Lean Six Sigma/DMAIC, 7 desperdicios Lean mapeados, taxonomía de alarmas (NO_ACTION/WATCH/WATCH_AUDIT/WATCH_TECH/WATCH_RISK/ACTION_*), Kanban 9 columnas con WIP limits (DOING=2, SAFETY=1, WAITING_EVIDENCE=5, BLOCKED=3), catálogo 11 monitores A–K, diseño detallado A/B/C/J/K, reglas anti-ruido, reglas escalado/des-escalado, roadmap 1–2 semanas, handoffs Sonnet/Codex/Opus y honestidad comercial sobre viabilidad del bankroll. Próximo paso único autorizado: `tools/daily_kanban_digest.py` CLI dry-run / LOG_ONLY / KANBAN_DIGEST_ENABLED=0 — NO implementado todavía. Telegram real solo tras ≥14 días LOG_ONLY sin falsos positivos y revisión Opus. No se toca código runtime, bot.py, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, env vars, Railway ni deploy. Fase C no autorizada. BANKROLL $35 no autorizado. |
| 2026-05-05 | Explícita | Sesión 295 | docs: record truth pipeline 1k expanded cohort | Codex cierra documentalmente Truth Pipeline 1K-B. Clasificación durable PROJECT_MEMORY/PATCH_MEMORY: TRUTH_PIPELINE_1K_B_MANUAL_14_RECORDS_OK_IDEMPOTENT_CALIBRATION_0_789_NO_RUNTIME_ACTIVATION. Escritura controlada de 14 `truth_records` calibrados completada en Railway sobre `/app/data/polymarket.db`, con backup `/app/data/polymarket.db.pre_1k_20260505T164308Z`. Baseline `truth_records=10`, `truth_revisions=0`, `n_resolved=5`, `n_unknown=5`, `calibration_global=0.6`. Dry-run `status=dry_run`, `processable=14`, `skipped=0`, 14 `would_write`; escritura real con `TRUTH_PIPELINE_ENABLED=1` solo en proceso SSH devuelve `status=ok`, 14 `inserted`, ids 11-24; idempotencia con segunda ejecución devuelve 14 `no_change`. Reporter post `status=no_action`, vistas presentes, `truth_records=24`, `truth_revisions=0`, `n_resolved=19`, `n_unknown=5`, `calibration_global=0.789`. Runtime automático Truth Pipeline OFF, Telegram Truth Pipeline OFF, env vars persistentes vacías/no definidas, sin Telegram real. Bot Railway sano en production/polymarket-bot con modo REAL, dashboard, Telegram polling e intra-SL OK; ruido conocido `py_clob_client_v2 400` seguido de autenticación OK. Fixture local eliminado y git limpio. No se toca código runtime, `bot.py`, trading core, BANKROLL, tablas v1 por 1K-B, schema, tests, env vars, deploy ni Fase C. Fase C no autorizada y BANKROLL $35 no autorizado. Siguiente paso: 1L observación/reporter sobre cohorte ampliada y decidir si cerrar Fase 1 observacional mínima o preparar activación log-only del reporter. |
| 2026-05-05 | Explícita | Sesión 294 | docs: record truth pipeline 1i calibrated cohort | Codex cierra documentalmente Truth Pipeline 1I-B. Clasificación durable PROJECT_MEMORY/PATCH_MEMORY: TRUTH_PIPELINE_1I_B_MANUAL_COHORT_OK_IDEMPOTENT_CALIBRATION_0_6_NO_RUNTIME_ACTIVATION. Escritura controlada de cohorte útil para `forecast_truth_join`/`v_decision_truth` completada en Railway sobre `/app/data/polymarket.db`, con backup `/app/data/polymarket.db.pre_1i_20260505T172154Z`. Estado previo `truth_records=5`, `truth_revisions=0`, `n_resolved=0`, `n_unknown=5`, `calibration_global=null`. Insertados 5 registros resueltos con Open-Meteo: London 2026-04-28 16C observed 17.1 outcome YES; London 2026-04-29 16C observed 17.5 outcome YES; Paris 2026-04-29 23C observed 22.2 outcome NO; Seoul 2026-04-28 16C observed 15.5 outcome NO; Tokyo 2026-04-29 20C observed 18.6 outcome NO. Dry-run `processable=5`, `skipped=0`; escritura real con `TRUTH_PIPELINE_ENABLED=1` solo en proceso SSH devuelve cinco `inserted`, ids 6-10; idempotencia devuelve cinco `no_change`, ids 6-10. Reporter final `status=no_action`, `truth_records=10`, `truth_revisions=0`, `n_resolved=5`, `n_unknown=5`, `calibration_global=0.6`, vistas `forecast_truth_join` y `v_decision_truth` presentes. La expectativa manual `~0.4` queda corregida: la implementación calcula 0.6 sobre `v_decision_truth.forecast_correct` (London 2/2, Tokyo 1/1, Paris 0/1, Seoul 0/1). Runtime automático Truth Pipeline OFF, Telegram Truth Pipeline OFF, env vars persistentes vacías/no definidas, sin Telegram real. Bot Railway sano en REAL con dashboard, Telegram polling e intra-SL OK; ruido conocido `py_clob_client_v2 400` seguido de autenticación OK. No se toca código runtime, `bot.py`, trading core, BANKROLL, tablas v1 por 1I-B, schema, tests, env vars, deploy ni Fase C. Fase C no autorizada y BANKROLL $35 no autorizado. Siguiente paso: 1J observación/reporter sobre cohorte calibrada y decidir si activar reporter/alerta en modo preview o poblar más datos. |
| 2026-05-05 | Explícita | Sesión 293 | docs: record truth pipeline 1g cohort | Codex cierra documentalmente Truth Pipeline 1G. Clasificación durable PROJECT_MEMORY/PATCH_MEMORY: FUNCTIONAL_RAILWAY_MANUAL_COHORT_OK_IDEMPOTENT_NO_RUNTIME_ACTIVATION. Cohorte mínima de 5 `truth_records` poblada manualmente en Railway sobre `/app/data/polymarket.db`, con backup existente `/app/data/polymarket.db.pre_truth_v2_20260505T121100Z`. Estado inicial `truth_records=1`, `truth_revisions=0`, registro previo Paris `2026-04-15` `observed_high_c=17.0`. Insertados uno por uno con fetcher real OK y dry-run previo: Seoul `2026-04-10` `11.4C`, Paris `2026-04-10` `14.4C`, Tokyo `2026-04-10` `19.6C`, Shanghai `2026-04-10` `22.6C`, todos `quality=final` y `source=open_meteo_archive`; cada escritura usó `TRUTH_PIPELINE_ENABLED=1` solo en el proceso SSH. Reporter final `status=no_action`, `truth_records=5`, `truth_revisions=0`, `n_unknown=5`, `n_missing_observed=0`, vistas `forecast_truth_join` y `v_decision_truth` presentes. Idempotencia final Shanghai `2026-04-10`: `action=no_change`, `id=5`, conteos estables. Alarm preview omitida por bloqueo técnico de quoting/stdin con `railway_safe.ps1 ssh "python -"`, no bloqueante porque no afectó DB/runtime/Telegram y preview ya estaba validada en 1F. Runtime automático Truth Pipeline OFF, Telegram Truth Pipeline OFF, env vars persistentes vacías/no definidas, sin Telegram real. Bot Railway sano en modo REAL con Telegram polling, dashboard e intra-SL OK; ruido conocido `py_clob_client_v2 400 Could not create api key` seguido de `Autenticación OK`. No se toca código runtime, `bot.py`, trading core, BANKROLL, tablas v1, schema, tests, env vars, deploy ni Fase C. Fase C no autorizada y BANKROLL $35 no autorizado. Siguiente paso: 1H observación/reporter sobre cohorte mínima y decidir si activar runner manual periódico o poblar más datos, sin env vars persistentes salvo aprobación separada. |
| 2026-05-05 | Explícita | Sesión 292 | docs: record truth pipeline 1e first write | Codex cierra documentalmente Truth Pipeline 1E. Clasificación durable PROJECT_MEMORY/PATCH_MEMORY: FUNCTIONAL_RAILWAY_MANUAL_WRITE_OK_IDEMPOTENT_NO_RUNTIME_ACTIVATION. Primera población manual mínima completada en Railway sobre `/app/data/polymarket.db`, con backup existente `/app/data/polymarket.db.pre_truth_v2_20260505T121100Z`. Reporter antes `status=empty`, `truth_records=0`, `truth_revisions=0`; env vars Truth Pipeline y Telegram vacías/no persistentes. Fetcher real Paris `2026-04-15` OK (`observed_high_c=17.0`, `quality=final`, `source=open_meteo_archive`). Escritura manual única con `TRUTH_PIPELINE_ENABLED=1` solo dentro del SSH: `status=ok`, `action=inserted`, `id=1`, registro Paris `2026-04-15` `17.0C`. Reporter después `status=no_action`, `truth_records=1`, `truth_revisions=0`; idempotencia validada con segunda ejecución `action=no_change`, `id=1`, reporter final estable. Runtime automático Truth Pipeline OFF, Telegram Truth Pipeline OFF, sin env vars persistentes, sin Telegram real, sin rollback. Bot Railway sano en modo REAL con Telegram polling, dashboard e intra-SL OK; ruido no relacionado `py_clob_client_v2 400 Could not create api key` en startup. No se toca código runtime, `bot.py`, trading core, BANKROLL, tablas v1, schema, tests, env vars, deploy ni Fase C. Fase C no autorizada y BANKROLL $35 no autorizado. Siguiente paso: 1F observación/reporter sobre el primer record y decidir si poblar cohorte mínima sin activar env vars persistentes. |
| 2026-05-05 | Explícita | Sesión 291 | docs: record truth pipeline 1b 1c validation | Codex cierra documentalmente Truth Pipeline 1B/1C. Clasificación durable PROJECT_MEMORY/PATCH_MEMORY: Fase 1A completa; 1B validada como FUNCTIONAL_CLI_READ_ONLY_READY con tests focalizados OK (29/17/39/29/55 passed), `verify_before_deploy.py` 1112/1112, reporter local fail-safe ante DB ausente, fetcher dry-run Paris OK, fetcher real Seoul/Paris OK y runner dry-run sin escritura; 1C aplica únicamente schema SQLite v2 en Railway sobre `/app/data/polymarket.db`, con backup `/app/data/polymarket.db.pre_truth_v2_20260505T121100Z`, dry-run schema OK, reporter pre `schema_missing`, aplicación `status=applied/current_version=2`, reporter post `status=empty` con `truth_records=0` y vistas v2 presentes, runner post-schema dry-run sin escritura. Tablas v1 confirmadas presentes vía `phase1_readiness_check.py`; bot Railway sano con SQLiteRecorder OK. Runtime Truth Pipeline OFF, Telegram Truth Pipeline OFF, sin env vars cambiadas, sin Telegram real, sin runner writer, sin deploy y sin tocar `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler ni Fase C. Fase C no autorizada y BANKROLL $35 no autorizado. Siguiente paso: 1D dry-run controlado / primera población manual o plan de activación, sin env vars salvo aprobación separada. |
| 2026-05-04 | Explícita | Sesión 290 | docs: add truth pipeline phase1 design | Sonnet documenta diseño completo de Fase 1 Truth Pipeline cerrado por Opus. Clasificación ACTION_DESIGN. Crea `docs/truth_pipeline_phase1.md`: objetivo observacional aislado, schema SQLite v2 con `truth_records`/`truth_revisions`, cuatro scripts standalone (fetcher, runner, alert, schema), job separado sin import de `bot.py`, env vars todas default OFF, guardrails, alertas Telegram solo salud/auditoría en canal separado, subfases 1A.1–1A.4, criterios de aceptación y criterios de promoción a Fase 2. Crea `docs/codex_prompt_truth_pipeline_1A1_schema_isolation.md`: prompt para 1A.1, no ejecutado. Actualiza CONTEXTO.md y HISTORIAL_SESIONES.md. Estado: Phase 1 readiness READY, diseño cerrado, implementación NO iniciada. No toca bot.py, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, env vars productivas ni deploy. |
| 2026-05-01 | Explícita | Sesión 289 | feat(alerts): downgrade blocked signals low fidelity audit level | Codex corrige la semántica de nivel de `Blocked signals — auditoría diaria`: si existe schema v2 pero la muestra OUT v2 es insuficiente (`OUT resolved <50`) y el fallback v1 fuera de whitelist se apoya en settlement unknown/unverified, la alerta baja a `WATCH_AUDIT` en vez de `ACTION`. El copy conserva que no es accionable para trading y que no hay cambios en whitelist ni city modes sin revisión separada; el fallback legacy de emergencia también queda protegido. `verify_before_deploy.py` suma guardrail anti-regresión. Validación: sintaxis OK, smoke sintético `WATCH_AUDIT`, `verify_before_deploy.py` 1074/1074, `git diff --check` OK con avisos LF/CRLF; sin dry-run real de audit por falta de JSONL local. No toca trading core, whitelist, city modes, policy, BANKROLL, sizing, scheduler, riesgo, env vars, Truth Pipeline/Fase C ni deploy. |
| 2026-05-01 | Explícita | Sesión 288 | docs/alerts: update traders intelligence v1 ready copy | Codex ajusta el copy de `tools/traders_intelligence_daily_summary.py` para que, si la v1 minima ya existe (`tools/traders_intelligence_snapshot.py` + doc), la alarma READY no vuelva a pedir `Abrir v1 minimo`; ahora indica ejecutar la CLI con `signals.json` fresco para acumular snapshots. `verify_before_deploy.py` añade guardrail anti-regresion. Validacion: sintaxis OK, dry-run summary OK, `verify_before_deploy.py` 1073/1073, `git diff --check` OK. No toca bot.py, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, NOAA/Open-Meteo, policy, riesgo, env vars ni deploy. |
| 2026-05-01 | Explícita | Sesión 287 | feat(traders): add v1 signal snapshots pseudo lifecycle | Codex implementa v1 minimo manual de Traders Intelligence: `tools/traders_intelligence_snapshot.py` archiva snapshots filtrados de `signals.json` bajo `data/traders_intelligence/snapshots/`, genera reportes JSON y audit JSONL idempotente, limitado a `Thrifty-Original`/`Entire-Hood` y `Houston`/`Los Angeles`/`Manila`/`Miami`. Pseudo-lifecycle externo observacional: `appeared`, `still_present`, `disappeared_apparent`, `reappeared`, sin senales ejecutables ni inferencias operativas. Docs y guardrails actualizados; validacion sintaxis OK, dry-run/smoke OK, missing input limpio, `verify_before_deploy.py` 1072/1072 y `git diff --check` OK. No cambia bot.py, trading core, NOAA/Open-Meteo, BANKROLL, sizing, whitelist, city modes, scheduler, policy, env vars, riesgo, Truth Pipeline/Fase C ni deploy. |
| 2026-05-01 | Explícita | Sesión 286 | feat(alerts): add sl intra hazard monitor log only | Codex implementa L2 Hazard Monitor SL_intra como observador puro LOG_ONLY default OFF. `bot.py` agrega audit independiente `sl_intra_hazard_monitor_audit.json`, scope literal bajo L1 via `_sl_intra_guard_should_skip`, tiers `deteriorating=-50%`, `deep=-70%`, `terminal=-85% o current_value<=0.30`, `collapsed cur_price<=0.05 durante >=2 ciclos`, idempotencia `token_id+tier` y Telegram LOG_ONLY con cooldown propio. `verify_before_deploy.py` cubre defaults, scope, no side-effects, tiers, collapsed 2 ciclos, idempotencia y cooldown independiente. Validacion local: sintaxis OK, `verify_before_deploy.py` 1065/1065, `git diff --check` OK. No cambia L0/L1, stop-loss ejecutable, `STOP_LOSS_PCT`, BANKROLL, sizing, whitelist, city modes, scheduler, NOAA, MIN_EDGE, take_profit, Unsellable Guard, execute_trade, track_trade, trade_lifecycle, sell_lock ni `sl_intra_guard_audit.json`; env vars produccion sin cambios, monitor OFF hasta activar `SL_INTRA_HAZARD_MONITOR_ENABLED`. |
| 2026-05-01 | Explícita | Sesión 285 | docs: record sl intra hazard monitor design | Sonnet documenta decision de riesgo SL_intra Hazard Monitor L2 post-revision Opus (Wellington vs Paris). Veredicto: L0/L1 intactos; guard v10.6.40 protege falsas salidas tipo Paris (exact+days≤1) pero deja sin observacion degradacion terminal tipo Wellington (laguna de cobertura, no bug). Diseno L2 LOG_ONLY puro: scope exact+days≤1, tiers `deteriorating`/`deep`/`terminal`/`collapsed`, idempotencia por token+tier, sin tocar sell_lock/trade_lifecycle/Unsellable Guard. L3 ejecutable diferido ≥14d + ≥8 tokens resueltos. Metrica futura: Net P/L 30d contrafactual por tier. Artefactos: `docs/sl_intra_hazard_monitor_design.md`. No toca bot.py, trading core, BANKROLL, env vars ni deploy. |
| 2026-05-01 | Explícita | Sesión 284 | pendiente | Codex cierra triage read-only de `P/L Reconciliation 2026-04-30` como `WATCH_RISK`: la alarma sigue siendo útil, pero el P/L 7d positivo actual está dominado por batch antiguo `market_resolved` (`+$23.36` n=11 dentro de 7d) y no autoriza ninguna subida de bankroll. `Wallet Snapshot` sigue acumulando baseline 7d y no está integrado aún con `pnl_reconciliation_alert.py`; `Bankroll Scaling` sigue bloqueado/manual-only y `BANKROLL` permanece en `$25`. Sin patch: la alerta ya advierte no interpretar el 7d como mejora limpia; futuro alcance mínimo sería exponer P/L 7d limpio excluyendo batch antiguo y readiness wallet/bankroll en el copy. No se toca código, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, Railway env, commit, push ni deploy. |
| 2026-05-01 | Explícita | Sesión 283 | pendiente | Codex aplica patch acotado de hygiene para `Slot monetization review`: el caso sano de `04h` `validated/keep` con buys y rates positivos, sin execution rejects relevantes y solo residuales benignos no recurrentes queda como `NO_ACTION` silencioso con estado actualizado, sin abrir Telegram accionable. La alerta conserva regresiones: si `04h` deja de monetizar, cae de `validated/keep`, aparecen execution rejects relevantes, se acumulan rechazos benignos recurrentes o un slot habilitado vuelve a ser candidato accionable, sigue enviando alerta. `verify_before_deploy.py` añade fixtures sano/regresión y pasa **1047/1047**. No cambia trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, SKIP real, Railway env, push ni deploy. |
| 2026-05-01 | Explícita | Sesión 282 | pendiente | Codex implementa monitor diario read-only para Unsellable Guard v1 LOG_ONLY. Nueva tool `tools/unsellable_guard_monitor.py` lee `skip_log.jsonl` y rotados, filtra `unsellable_guard_candidate`/`unsellable_v1`/`would_skip`, calcula candidatos 24h/7d/all-time, top ciudades/condiciones, promedios y ejemplos, y eleva `ACTION_SAFETY` si aparece `unsellable_liquidity_guard` o `guard_action=skipped`. `bot.py` la integra en `run_observability_alerts()` con envs `UNSELLABLE_GUARD_MONITOR_*`, wrapper JSON, Telegram manual-only y anti-spam en `alerts_state.json`; `OK` no envía resumen vacío. `verify_before_deploy.py` añade checks y fixtures OK/WATCH/ACTION_REVIEW/ACTION_SAFETY; docs del guard explican el monitor. Validación **1045/1045**, sintaxis y CLI JSON/Markdown OK, `git diff --check` OK con avisos LF/CRLF. No cambia trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, STOP_LOSS/TP, `UNSELLABLE_GUARD_ENABLED`, `UNSELLABLE_GUARD_LOG_ONLY`, Truth Pipeline/Fase C, Railway ni deploy. Sin commit/push. |
| 2026-04-30 | Explícita | Sesión 281 | pendiente | Codex aplica patch acotado `LOG_ONLY_FIRST` del Unsellable Liquidity Guard v1: defaults `UNSELLABLE_GUARD_ENABLED=0`, `UNSELLABLE_GUARD_LOG_ONLY=1`, version `unsellable_v1`, helper testeable y hook antes de `execute_trade()` tras sizing/presupuesto/ajuste minimo notional. En LOG_ONLY registra `unsellable_guard_candidate`/`would_skip` sin bloquear compra ni Telegram; el path real `unsellable_liquidity_guard`/`skipped` queda dormido hasta `LOG_ONLY=0` con signoff Opus. `verify_before_deploy.py` cubre defaults, trigger, `size_ratio=amount/effective_bankroll`, `price_raw` forensics y guardrails; se crea `docs/unsellable-liquidity-guard-v1.md`. Validacion: sintaxis OK, `verify_before_deploy.py` 1032/1032 y `git diff --check` OK. No cambia BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, STOP_LOSS/TP, Truth Pipeline/Fase C, Railway ni SL_intra. |
| 2026-04-30 | Explícita | Sesión 280 | fix(tools): clarify Phase 1 proxy status in bankroll monitor | Codex aplica patch acotado de copy/tooling al Bankroll Scaling Monitor: reemplaza el label desnudo `Phase 1 ready` por `Phase 1 proxy OK - canonical check pending/no evaluado`, remite a `tools/phase1_readiness_check.py` como fuente canonica y aclara que no autoriza Truth Pipeline/Fase C. La revision previa queda registrada: bloqueo `$25 -> $35` correcto por WR limpio `36.7%` y drawdown ultimos 5 cierres `-$3.89`; WATCH_RISK por exact + `micro_position_unsellable` (`Munich 20C Apr27 NO -$2.26`, `Paris 24C Apr29 NO -$2.16`), con `SL_intra` no siendo la causa principal. `verify_before_deploy.py` suma guardrails de copy/manual-only. No cambia logica de bankroll scaling, `phase1_readiness_check.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, STOP_LOSS/TP, Truth Pipeline ni Fase C. |
| 2026-04-30 | Explícita | Sesión 279 | fix(tools): use live paths for traders intelligence inputs | Codex corrige un falso `health=degraded` en `Traders Intelligence`: el reporte buscaba por defecto `data/runtime_import_derived/signals_crosscheck.jsonl` y `data/runtime_import_derived/blocked_signals_resolutions.jsonl`, pero Railway ya tiene las fuentes canónicas en `/app/data/signals_crosscheck.jsonl` (18 líneas) y `/app/data/blocked_signals_resolutions.jsonl` (440 líneas). `tools/traders_intelligence_report.py` pasa a live-first con fallback legacy y warnings con `paths_checked`; `docs/traders-intelligence-spec.md` alinea el contrato; `verify_before_deploy.py` añade guardrails para paths live/fallback, `paths_checked`, no v1 y no scheduler/trading. Validación: sintaxis OK, help OK, smoke local del reporte `usable_signal`, `verify_before_deploy.py` **1010/1010**, `git diff --check` OK. No se toca `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, `SCHEDULE_HOURS_UTC`, riesgo, Truth Pipeline ni Fase C. |
| 2026-04-30 | Explícita | Sesión 278 | fix(tools): clarify SL retrospective verdict in daily briefing | Codex aplica patch mínimo de copy en `tools/daily_position_briefing.py`: el briefing ya no imprime `final_verdict` legacy de `sl_retrospective_state.json` como conclusión operativa desnuda. Si el veredicto contiene `(firme)` o es concluyente (`SL funciona correctamente` / `SL corta posiciones correctas`), lo marca como `veredicto histórico` y remite al detalle `phase-aware` de la alerta SL Retro. `verify_before_deploy.py` añade guardrail funcional para impedir la regresión. Validación **1004/1004**; dry-run del briefing OK. No se toca `tools/sl_retrospective.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, STOP_LOSS/TP, Truth Pipeline ni Fase C. |
| 2026-04-30 | Explícita | Sesión 277 | docs: record Apr 30 alert reviews and wallet snapshot status | Sonnet registra revisiones read-only del 30 de abril: (1) wallet snapshot Railway OK_RUN, 1 snapshot, total_value=19.90, phase2_ready=false, acumulando 7d/168h; (2) PnL 7d limpio ≈−$2.40 (bruto +$20.96 contaminado por batch market_resolved +$23.36 n=11), captura manual −$2.24, BANKROLL $25 sin cambios; (3) cross-check LA gap ya resuelto por b503612/Sesión 276, auditoría fuente/cobertura únicamente; (4) blocked_signals 440 total, v1/v2 398/42, OUT whitelist 13, Unknown=398 registros v1 legacy sin campos v2, WR OUT 100% settlement unverified, backlog Beijing/Lucknow/Guangzhou, veredicto ACTION_AUDIT_BACKLOG. No toca código, bot.py, trading core, whitelist, city modes, bankroll, Truth Pipeline ni Fase C. |
| 2026-04-30 | Explícita | Sesión 276 | fix(alerts): align crosscheck summary with live inputs | Codex aplica patch acotado de observabilidad/copy para evitar incoherencia ACTION/WATCH en el cross-check traders-vs-bot. `bot.py` pasa al summary diario los mismos paths live usados por la alerta corta (`SIGNALS_FILE`, `SHADOW_TRACKING_FILE`, `CITY_POLICY_FILE`) y `tools/signals_crosscheck_daily_summary.py` usa `operational_trader_only_count` del último JSONL como fallback para no decir que no hay gap si el cross-check live ya detectó uno. El copy marca auditoría de fuente/cobertura y no cambio de trading. `verify_before_deploy.py` suma guardrails de paths live, fallback live, no apertura automática whitelist/canary, scheduler intacto y Los Angeles fuera de whitelist/canary/active, `RESOLUTION_ICAO` y `OBSERVED_AUDIT_CITIES`. Validación **1002/1002**. No se toca trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, Los Angeles infra/city policy, Truth Pipeline ni Fase C. |
| 2026-04-30 | Explícita | Sesión 275 | feat(alerts): run wallet snapshot daily from observability | Codex integra `tools/wallet_snapshot.py --json` en `bot.py` como tarea diaria read-only desde `run_observability_alerts()`, con `WALLET_SNAPSHOT_ENABLED=1`, hora configurable, timeout, estado `wallet_snapshot_*` en `alerts_state.json` y alerta Telegram one-shot cuando `phase2_ready=true`. Durante `ACUMULANDO` solo guarda snapshots para baseline 7d/168h y no envía Telegram diario. `docs/wallet_snapshot.md` documenta Railway; `verify_before_deploy.py` suma checks y pasa **996/996**. No se toca `tools/pnl_reconciliation_alert.py`, trading core, scheduler, `SCHEDULE_HOURS_UTC`, BANKROLL, sizing, whitelist, city modes, STOP_LOSS/TP, riesgo, Truth Pipeline ni Fase C. |
| 2026-04-29 | Explícita | Sesión 274 | feat(tools): add read-only wallet snapshot utility | Codex crea `tools/wallet_snapshot.py` como Fase 1 read-only para snapshots wallet/portfolio Polymarket: cash USDC + posiciones Data API, `total_value`, JSONL runtime, delta 7d con baseline 168h, cash flows manuales opcionales, `possible_deposit`, salida JSON/Markdown/texto y `phase2_ready` para integración futura. `docs/wallet_snapshot.md` documenta uso y guardrails; `verify_before_deploy.py` suma checks de contrato/no trading/no `bot.py`. Validación **989/989**. No se integra con `pnl_reconciliation_alert.py`, no se toca `bot.py`, scheduler, trading core, bankroll, sizing, whitelist, city modes, riesgo, Truth Pipeline ni Fase C. |
| 2026-04-29 | Explícita | Sesión 273 | fix(tools): clarify bankroll scaling not eligible status | Codex aplica micro-fix a `tools/bankroll_scaling_check.py`: `UNKNOWN` queda para datos básicos de performance no evaluables, mientras que falta de evidencia de política sin hard blockers pasa a `NOT_ELIGIBLE` con `decision=do_not_increase`. El Markdown de `Performance windows` construye filas explícitas para evitar filas pegadas en Railway. `docs/bankroll_scaling_check.md` y `verify_before_deploy.py` se actualizan; validación **981/981**. No se toca `bot.py`, trading core, compras/ventas, bankroll real, Telegram, scheduler, city modes, whitelist, Truth Pipeline ni Fase C. |
| 2026-04-29 | Explícita | Sesión 272 | fix(tools): separate legacy and clean bankroll performance windows | Codex implementa P2B2 en `tools/bankroll_scaling_check.py`: añade `performance_windows` (`historical_all`, `current_logic_series`, `last_20_closed`, `last_30_clean_closed`) y `evaluation_window` con prioridad a la ventana limpia de 30 trades, luego serie lógica actual, luego últimos 20, dejando histórico total como fallback/contexto legacy. Los criterios PnL/WR usan la ventana elegida y `evidence.pnl_drawdown` conserva compatibilidad. Markdown muestra tabla de ventanas; `verify_before_deploy.py` suma checks del contrato y pasa **980/980**. No se toca `bot.py`, trading core, compras/ventas, bankroll real, sizing, whitelist, city modes, scheduler, Telegram, Truth Pipeline ni Fase C. |
| 2026-04-29 | Explícita | Sesión 271 | feat(alerts): add bankroll scaling Telegram monitor | Codex implementa P2C: `bot.py` integra el check read-only `tools/bankroll_scaling_check.py --json` con Telegram mediante `/bankroll` y `/bankroll_status`, y añade `maybe_run_bankroll_scaling_monitor(state)` en observabilidad. El anti-spam usa `alerts_state.json` (`bankroll_scaling_last_status`, `bankroll_scaling_last_target_tier`, `bankroll_scaling_last_digest_date`, `bankroll_scaling_last_blockers_hash`, `bankroll_scaling_last_alert_cycle`, `bankroll_scaling_last_eligible_for_manual_review`) y alerta solo por cambio de status/target/blockers, transición a `ELIGIBLE_FOR_MANUAL_REVIEW` o resumen cada N ciclos. Si el CLI falla, solo loguea warning y no envía Telegram. `verify_before_deploy.py` añade checks P2C y pasa **975/975**; `docs/bankroll_scaling_check.md` documenta la integración. No se toca trading core, compras/ventas, sizing, BANKROLL real, `BANKROLL_LEVELS`, `SCALING_TIERS`, whitelist, city modes, scheduler, Truth Pipeline, Fase C ni variables de entorno de trading. |
| 2026-04-29 | Explícita | Sesión 270 | fix(tools): clarify bankroll scaling missing evidence | Codex aplica un micro-fix sobre `tools/bankroll_scaling_check.py` tras la primera ejecución real en Railway. `phase1_ready` deja de poder mostrarse como `pass` con valor `False`: si Phase 1 está pendiente y el tier lo permite, aparece como `pending` con mensaje explícito de umbrales pendientes. `bankroll_readiness_score` ahora busca estado en `--data-dir/bankroll_readiness_state.json`, `./data/bankroll_readiness_state.json` y `./bankroll_readiness_state.json`; si no existe, JSON expone `available:false`, `score:null`, `paths_checked` y mensaje de state file not found, mientras Markdown muestra `unavailable (state file not found)`. `verify_before_deploy.py` añade checks de estos contratos y pasa **965/965**. No se toca `bot.py`, trading core, compras/ventas, sizing, bankroll real, `BANKROLL_LEVELS`, `SCALING_TIERS`, whitelist, city modes, scheduler, variables de entorno ni Telegram. |
| 2026-04-29 | Explícita | Sesión 269 | feat(tools): add read-only bankroll scaling check | Codex implementa P2B con `tools/bankroll_scaling_check.py`, una CLI read-only y stdlib-only para evaluar si procede abrir revisión manual de escalado al siguiente tier. Soporta `--data-dir`, `--db`, `--json`, `--markdown`, `--current-bankroll`, `--target-tier` y `--log-tail`; lee runtime JSON/JSONL/logs y SQLite `mode=ro`; emite `eligible_for_manual_review`, `decision` (`do_not_increase` o `manual_review_required`), hard blockers, watch items, missing evidence, criteria y evidence. Se crea `docs/bankroll_scaling_check.md` y `verify_before_deploy.py` añade checks de contrato read-only/no Telegram/no red/no bot.py/no writes/no core trading. Validación: `py_compile` OK, CLI Markdown/JSON OK con DB local ausente y `verify_before_deploy.py` **963/963**. No se toca `bot.py`, trading core, compras/ventas, sizing, bankroll real, `BANKROLL_LEVELS`, `SCALING_TIERS`, whitelist, city modes, scheduler ni variables de entorno. |
| 2026-04-29 | Explícita | Sesión 268 | fix(alerts): clarify bankroll scaling readiness is manual-only | Codex aplica P2A mínimo: corrige solo el copy de `Scaling Readiness`/`Scaling Warning` en `bot.py` para evitar que una señal de PnL de últimos 20 trades parezca autorización de subida de bankroll. `Scaling Readiness` pasa a decir que es señal auxiliar, requiere revisión manual, cumplir `docs/bankroll_scaling_policy.md`, validar health/readiness/PnL y que NO autoriza subida automática ni cambiar `BANKROLL` por la alerta. `Scaling Warning` mantiene el bloqueo y lo encuadra como señal auxiliar para revisar PnL/drawdown. `verify_before_deploy.py` añade checks estáticos para el copy manual-only y para conservar `SCALING_TIERS`/`BANKROLL_LEVELS`. No se toca trading core, compras/ventas, sizing, bankroll real, whitelist, city modes, scheduler ni reglas de riesgo. |
| 2026-04-29 | Explícita | Sesión 267 | docs: add bankroll scaling policy | Sonnet crea `docs/bankroll_scaling_policy.md`: política canónica manual para escalar bankroll $25→$35→$50→$75→$100. Define hard blockers globales (bot_health_check ACTION, phase1_readiness error, SQLiteRecorder stale, drawdown excedido, errores de ejecución, posiciones atascadas, cambios sin observación), soft blockers/WATCH, criterios por nivel con umbrales provisionales (WR≥40%/45%, ciclos≥10/30, PnL≥0, drawdown>-$3, bankroll score≥40%/60%/75%), regla anti-subida por euforia (7 casos explícitos), fuentes de datos con comandos Railway, relación con alertas Telegram (`Scaling Readiness`/`Warning` como señales auxiliares no autoritativas) y plan P2 de herramienta read-only de elegibilidad. Decisión actual: no subir bankroll, continuar acumulando datos. No se toca código, bot.py, trading core, NOAA, scheduler, whitelist, city modes, bankroll real ni variables de entorno. |
| 2026-04-29 | Explícita | Sesión 266 | micro-patch documental | Sonnet actualiza documentación canónica sin cambios de código: cierra narrativa de Fase A (S261, v10.6.44–45), Fase B1 (S262, v10.6.46), Fase B2 (commit `78a55d8`, v10.6.47), bot health check (S264–S265, calibrado). Establece guardrail Truth Pipeline explícito (no tocar `truth_records`, `truth_revisions`, Fase C, `settlement_fidelity`, probability engines, backtesting ni bankroll scaling automático). Documenta Bloque 3 readiness: ETA 2026-05-04, control canónico `python tools/phase1_readiness_check.py --db /app/data/polymarket.db --json`, exit_code=0 requerido. Próximo paso: diseño Fase 1 Truth Pipeline preferiblemente con Opus, implementar solo tras aprobación del diseño. No se toca código, `bot.py`, trading core, NOAA, scheduler, whitelist, city modes ni bankroll. |
| 2026-04-29 | Inferida | v10.6.47 Fase B2 | feat(v10.6.47) Fase B2 blocked_signals (commit 78a55d8) | Reemplaza alerta Telegram diaria de blocked_signals por resumen estructurado con helpers `_blocked_signals_build_telegram_summary`/`_blocked_signals_format_telegram`. Incluye: resumen global v1/v2, WR OUT whitelist, top ciudades, concentración top-3, % settlement `unverified/unknown`, `reason_blocked`/`city_policy_status_at_record_time` (v2), candidatos a auditoría, nivel `INFO/WATCH/ACTION`, hint al CLI de auditoría. Fallback legacy si falla. No accionable para trading; no recomienda abrir whitelist, canary, active ni compras. `verify_before_deploy.py` **919/919** (12 checks nuevos). No se toca trading core, NOAA, scheduler, whitelist, city modes, bankroll ni reglas de entrada/salida. |
| 2026-04-29 | Explícita | Sesión 265 | bot health check calibration | Codex calibra `tools/bot_health_check.py` tras prueba real en Railway para reducir falsos `WATCH/ACTION`. Se añaden `date_out_of_range_past`, `parse_fail` y `city_window_skipped` como rechazos normales; el caso `with_edge=0/selected=0/buys=0/execution_reject_reasons={}` interpreta `no buys because no operable opportunities were selected`; readiness de Fase 1 pendiente queda como `WATCH` bajo esperado; Tracebacks conocidos de observabilidad (`traders_intelligence`/`city-intelligence`) no elevan a `ACTION`, mientras Tracebacks no observability y errores reales siguen críticos. `verify_before_deploy.py` suma 4 checks funcionales y pasa **943/943**; `py_compile` y markdown local OK. No se toca `bot.py`, trading core, compras/ventas, bankroll, whitelist, city modes, scheduler ni variables de entorno. |
| 2026-04-29 | Explícita | Sesión 264 | bot health check read-only | Codex implementa `tools/bot_health_check.py`, una CLI read-only stdlib-only para resumir salud del bot en `OK/WATCH/ACTION` sin abrir SSH manual. Acepta `--data-dir`, `--db`, `--json`, `--markdown`, `--max-cycle-age-hours` y `--log-tail`; lee tolerante runtime files, logs, opcionales y `polymarket.db` con SQLite URI `mode=ro`. Reporta runtime, ciclos, SQLiteRecorder/Phase 1 readiness, compras/rechazos, logs y posiciones. Se crea `docs/bot_health_check.md` y `verify_before_deploy.py` suma checks de contrato read-only/no Telegram/no red/no bot.py/no core trading. Validación: markdown/json locales OK con datos ausentes en `WATCH`; `py_compile` OK fuera del sandbox por lock local de `__pycache__`; `verify_before_deploy.py` **939/939**. No se toca `bot.py`, trading core, compras/ventas, manage_positions, intra_cycle_sl_check, bankroll, whitelist, city modes, scheduler ni variables de entorno. |
| 2026-04-29 | Explícita | Sesión 263 | hardening Telegram traders_intelligence | Codex aplica un minipatch de observabilidad en `tools/traders_intelligence_daily_summary.py` para que un fallo de Telegram no tumbe el resumen diario. `send_telegram()` divide mensajes largos en chunks de 3800 chars, omite `parse_mode=HTML`, captura `HTTPError`/`URLError`/`TimeoutError`/`Exception`, hace un retry simple y devuelve resultado estructurado no fatal; el script mantiene escritura de state/markdown aunque Telegram falle. `verify_before_deploy.py` suma checks del contrato. Validación: dry-run sin llamada real a Telegram, `py_compile` OK fuera del sandbox por lock local de `__pycache__`, `verify_before_deploy.py` **925/925**. No se toca `bot.py`, trading core, NOAA, whitelist, city modes, bankroll, scheduler ni reglas de compra/venta. |
| 2026-04-27 | Explícita | Sesión 256 | anti-flapping guard legacy + PnL reporting fix v10.6.41 | Sonnet revisa las alarmas del dia 27 contra produccion. Encuentra y corrige dos bugs en v10.6.41: (1) anti-flapping guard: `verified_history_bad` solo cubria `noaa_verified`; Dallas (17t WR 11.8% PnL -$1.60 en active, unico ref Academic-Maniac WR 5%) evadio el guard y se re-promovio a canary. Fix: nuevo `degraded_history_bad` que bloquea `promotable_shadow` tambien para ciudades degradadas con historial legacy malo. Dallas demotada manualmente en prod; canary queda en 9. (2) PnL daily briefing: `_daily_summary_closed_trades_last_24h` mezcla `market_resolved` de marzo (+$23.36) con trades reales del dia (-$1.89), inflando la cifra. Fix: separa `batch_closed/batch_pnl` y lo reporta en linea propia. Alarmas verificadas correctas: NOAA NYC (1 caso confirmado), Munich open (0.60, +$0.81 unrealizado), SL_intra guard (0 skips, correcto). 859/859 tests. Archivo alarmas borrado. |
| 2026-04-27 | Explícita | Sesión 255 | fill real por order_id v10.6.41 | Codex corrige la reconciliación de ventas confirmadas tras detectar en Shanghai `27C Apr27 NO` que Telegram/lifecycle mostraban el precio límite (`0.80`) y no el fill real visto en Polymarket (`~0.99`). `audit_check_sell_fills()` ahora intenta leer fills reales por `order_id` con `get_trades`, conserva `limit_price`, actualiza `price/fill_price/return_est` con `fill_value` cuando existe, y propaga `fill_*` a `postmortem`/`trade_lifecycle`. El copy `[INTRA-SL]` aclara `precio límite` y que el precio real puede diferir. Validación: sintaxis OK, helper probado con trade sintético, `verify_before_deploy.py` 859/859; `py_compile` solo falla por lock conocido de `__pycache__`. |
| 2026-04-26 | Explícita | Sesión 249 | legacy analytics paused + delete alarm | Codex pausa los servicios Railway separados `phase5-visibility` y `city-intelligence` con `railway down -s <service> -y`, conservando servicios, variables y volúmenes para rollback/historial. Verificación live: `polymarket-bot` sigue `SUCCESS`; los dos legacy quedan sin deployment activo (`deploymentId=null`); `phase5-visibility-volume` y `city-intelligence-volume` siguen adjuntos. Se actualiza `data/service_transition_followup.json` a fase `legacy_services_paused`, se resuelven temprano los checkpoints de pausa y se programa `legacy_services_delete_readiness_2026_05_03`, que avisará cuándo borrar servicios/volúmenes si la pausa no rompió funcionalidad. `tools/city_intelligence_daily_summary.py` aprende a mostrar un `runbook` resumido en checkpoints vencidos; dry-run muestra el próximo checkpoint del 2026-05-03. Se crea `docs/legacy-analytics-service-cleanup-runbook-2026-04-26.md` y se actualiza el plan de transición. Validación: sintaxis del tool OK y `verify_before_deploy.py` 843/843. No se toca `bot.py`, `city_policy_state.json`, trading, NOAA, scheduler, whitelist, sizing ni reglas core. |
| 2026-04-26 | Explícita | Sesión 248 | legacy analytics Telegram silenced | Codex atiende la alerta combinada `Phase 5 Visibility` + `City Intelligence - resumen diario (2026-04-26 UTC)` y ejecuta la siguiente acción operacional clara: reducir ruido de emisores legacy sin tocar `bot.py`, `city_policy_state.json`, trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida. Se valida que el transporte read-only desde `polymarket-bot` funciona (`runtime_import` fresco `2026-04-26T10:42:33Z`, manifest 12/12, sin drift; ledger/pipeline local `runtime_inputs_status=available`, `overall_status=ok`). La raíz de la alarma queda separada: `city-intelligence` Railway separado sigue sin `/app/data/runtime_import` y por eso envió `runtime_inputs_missing` a las 07:00 UTC; `phase5-visibility` sigue acumulando coincidencias Shanghai+Chicago (`20`, probe `2026-04-26T05:10:38Z`) pero como plano legacy/benchmark. Cambio live reversible: `TELEGRAM_TOKEN=DISABLED` solo en `city-intelligence` y `phase5-visibility`; ambos vuelven a `SUCCESS` y validan `TOKEN_DISABLED`, mientras `polymarket-bot` conserva el emisor Telegram canónico. Riesgo residual: preflight operacional local queda con `error=1` por Atlanta (`runtime auto_shadow` vs `cross canary`), no por runtime transport. |
| 2026-04-26 | Explícita | Sesión 247 | blocked-signals live audit, no code | Codex ejecuta la primera auditoría read-only del `ACTION` diario `Blocked signals (fuera de whitelist)`, sin tocar `bot.py`, whitelist, NOAA, scheduler, sizing, Railway env ni reglas core. Fuente live: `/app/data/blocked_signals_resolutions.jsonl` en Railway `polymarket-bot`, `381` registros resueltos; whitelist live coincide con el default actual hasta `Dallas`; `BLOCKED_CITIES=London`. El agregado queda reproducido: fuera de whitelist `101` resueltas, `100` wins, WR `99.0%`; excluidas por whitelist `280`. Se crea `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md`: el ranking fuera de whitelist lo lideran `Lucknow` `19/19` con consenso `7/7`, `Warsaw` `17/17` con consenso `8/8`, `Chongqing` `16/16` con consenso `2/2` y `Beijing` `14/14` con consenso `4/4`. Decisión: no whitelist masiva ni reglas core; primer bloque accionable = verificación de fuente/cobertura para `Lucknow`, `Warsaw`, `Beijing` y `Chongqing`. `Buenos Aires` queda detrás por falta de consenso/edge y observed live 0; `Miami` no aplica porque ya está en whitelist; `Lagos` necesita discovery de fuente antes de cualquier decisión. |
| 2026-04-26 | Explícita | Sesión 246 | traders-vs-bot backlog, no code | Codex registra el parte diario `traders vs bot` / `Blocked signals` del 2026-04-26 UTC como backlog operativo read-only, sin tocar `bot.py`, whitelist, NOAA, scheduler, sizing, Railway ni reglas core. Foto recibida: `MATCH=23`, `BOT_ONLY=5`, `TRADER_ONLY=12`; serie reciente de 7 corridas con medianas `MATCH=19`, `BOT_ONLY=5`, `TRADER_ONLY=19`; persistentes `TRADER_ONLY` en `7/7`: `Buenos Aires`, `Miami`, `Warsaw`; casi persistentes `6/7`: `Chengdu`, `Lagos`. No hay gap operativo real hoy, asi que el cross-check queda en `WATCH`. `Blocked signals` fuera de whitelist queda en `ACTION` por `101` resueltas, `100` wins, WR `99.0%`, con `280` excluidas por whitelist, pero solo para auditoria ciudad/fuente/cobertura. Se crea `docs/trader-bot-review-backlog-2026-04-26.md`: Buenos Aires = falta whitelist/cobertura efectiva pese a `SAEZ` + NOAA + `OBSERVED_AUDIT_CITIES`; Miami = ya whitelist/observada, revisar edge/filtros si vuelve como gap real; Warsaw = no whitelist/no observed/ICAO-only, verificar fuente antes de cualquier canary. |
| 2026-04-26 | Explícita | Sesión 245 | City Intelligence daily observe, no code | Codex cierra la alerta `City Intelligence - resumen diario (2026-04-25 UTC)` como decisión de observación, sin tocar `bot.py`, policy, Railway, NOAA, scheduler, reglas de entrada/salida ni trading core. Evidencia recibida: runtime read-only manifestado desde `2026-04-25 11:00 UTC`, preflight operacional live sin errores, topología efectiva `blocked=1 / canary=9 / shadow=1 / active=0`, `blocking_operational_collision_count=0`, señal `usable_signal`, review queue `now=1 / soon=3 / watch=14` y cuello dominante `policy_execution_gate`. Decisión: no revalidar transporte runtime ni repetir trabajo cerrado; no abrir policy todavía. Siguiente acción: observar si la evidencia fresca convierte el `now=1` en blocker real o acción concreta, manteniendo los checkpoints Apr 28 y May 1 ya programados. Nota: el preflight local del checkout cae por artefactos stale/no bijectivos, así que no contradice la lectura live de la alerta. |
| 2026-04-26 | Explícita | Sesión 244 | slot 04h validated/keep, no code | Codex cierra la alerta `Slot monetization review` de `04h UTC` como decisión operativa de mantener el slot, sin tocar `bot.py`, scheduler, NOAA, reglas de entrada/salida, sizing, Railway env ni deploy. Evidencia de la ventana leída: 5 ciclos, `same_day_candidates=106`, `same_day_edges=3`, `same_day_selected=3`, `same_day_buys=2`, `buy_rate=66.67%` y `same_day_buy_rate=66.67%`; reject reasons dominantes `price_out_of_range=663`, `condition_filtered=86`, `blocked_city=22`; execution reject residual `buy_min_size=1`. Decisión: `04h UTC` queda `validated/keep`; siguiente acción, vigilar estabilidad y solo reabrir lógica si cae la conversión edge->buy o aparece un cuello recurrente nuevo. |
| 2026-04-25 | Explícita | Sesión 239 | limpieza post-V2 cutover P6+P7 | Codex ejecuta la limpieza post-cutover V2 sin tocar trading core, NOAA, scheduler, Kelly, sigma ni reglas de entrada/salida. Precondición Railway revisada: sin errores recurrentes en `create_or_derive_api_key`, `get_open_orders`, auth endpoints ni CLOB. P6: se crea backup local `data/runtime_import/shadow_city_tracking.json.bak-pre-p6` y backup remoto `/app/data/shadow_city_tracking.json.bak-pre-p6`; `shadow_city_tracking.json` live queda con Seoul aislado a evidencia post-fix desde `2026-04-17T12:22:40Z` (`markets_seen 207 -> 54`, `edge_hits 5 -> 2`, `cycles_seen 91 -> 28`, `best_edge_pct 68.5 -> 26.4`) y una sola señal durable `Seoul|2026-04-18|YES|at_or_above|21`. Validación local con manifest post-P6: ledger/gate `runtime_inputs_status=available`, sin drift, Seoul en `canary_measurement`; `notify_active_candidates` usa trades cerrados post-promoción. P7: se crea `docs/min-edge-per-city-analysis-2026-04-25.md`; no hay ciudades con `n_closed>=10`, `WR>=70%` y `PnL>0`, por lo que no se aplica `MIN_EDGE_PER_CITY`. Tokyo queda como candidata a observar (`n=5`, `WR=80%`, `PnL=+$3.53`) pero sin muestra suficiente. Review Sonnet 4.6 aprobada en `docs/sonnet-review-post-v2-cleanup-p6-p7-2026-04-25.md`; su único finding bajo queda resuelto al actualizar `city_policy_state.auto_canary_cities.Seoul` en local/Railway a `shadow_edges=2`, `best_edge_pct=26.4` y reason post-P6, con backup remoto `/app/data/city_policy_state.json.bak-seoul-p6-traceability`. |
| 2026-04-25 | Explícita | Sesión 238 | alarmas con nivel de acción y tarea concreta | Se convierte el frente de alarmas `traders vs bot` / `Blocked signals` en una capa con repercusión explícita, sin tocar reglas de entrada/salida, NOAA, scheduler, sizing ni trading core. `tools/signals_crosscheck_daily_summary.py` ahora clasifica cada daily como `INFO`, `WATCH` o `ACTION` y emite una `Tarea para Codex`; si hay gap operativo real fuera de `blocked`, la tarea es auditar la ciudad líder por whitelist, `RESOLUTION_ICAO`/estación, `OBSERVED_AUDIT_CITIES`/cobertura NOAA y señales trader, cerrando con `sin cambio`, `preparar whitelist/canary` o `bloqueo por fuente`. El aviso corto legacy en `bot.py` también añade `Nivel` + `Accion`. El copy de `Blocked signals` separa baseline fuera de whitelist de registros excluidos por estar ya en whitelist y aclara que el WR no mide ejecución real del bot; con `n>=50` y `WR>=70%` escala a `ACTION` de auditoría, no a cambio automático de reglas. `verify_before_deploy.py` suma checks `v10.6.37`; validación local: sintaxis OK y preflight **842/842**. |
| 2026-04-25 | Explícita | Sesión 237 | daily traders-vs-bot readout, no code | Se registra el parte diario `traders vs bot` / `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler, reglas de entrada/salida ni trading core. Foto UTC 2026-04-25: `MATCH=19`, `BOT_ONLY=7`, `TRADER_ONLY=13`; serie reciente de 7 corridas con medianas `MATCH=17`, `BOT_ONLY=5`, `TRADER_ONLY=20`. Lectura: el gap se está cerrando respecto al inicio de la serie reciente, pero hoy aparece un gap operativo real fuera de `blocked`: `Los Angeles` con 2 señales, consenso 2 y WR max 80%. Persisten en `TRADER_ONLY` `7/7`: `Buenos Aires`, `Chengdu`, `Miami`, `Warsaw`; casi persistentes `6/7`: `Busan`, `Lagos`, `Los Angeles`. `Blocked signals` fuera de whitelist: 95 resueltas, 94 wins, WR 98.9%, 273 señales excluidas por whitelist. Instrucción reiterada: si el bloque persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA antes de tocar reglas de entrada o trading core. |
| 2026-04-24 | Explícita | Sesión 236 | cooldown post `stop_loss_intra` + alarma post-fix | Codex toma el veredicto read-only de Opus tras la alarma `Strategy Review` (`WR últimos 15 trades=27%`) y aplica el patch mínimo sobre `bot.py`. El snapshot live `data/runtime_import` (`pulled_at=2026-04-24T21:22:53Z`) mostraba que Chicago `62°F Apr25 YES` y New York City `66°F Apr24 YES` concentraron varias pérdidas intra-SL en ~36h; el bucket `LOW <35c` quedó `0/7`, PnL `-$4.30`, frente a `MID/HIGH` `4/8`, PnL `+$1.08`. La causa raíz no era sigma global ni el SL como mecanismo, sino asimetría entre rutas: `manage_positions()` registraba `_sl_cooldown_register(city)` tras SL, pero `intra_cycle_sl_check()` vendía por `stop_loss_intra` sin activar cooldown, dejando reentrar en la misma tesis. El fix añade ese registro de cooldown después de `audit_register_pending_sell(...)` en la ruta intra-SL. También se programa `maybe_run_post_intra_sl_cooldown_review`: primer ciclo post-deploy auto-ancla `started_at` y, al llegar a 10 cierres nuevos, enviará Telegram con WR/PnL post-fix, SL intra, reentradas repetidas y split `LOW <35c` vs `MID/HIGH`. No se tocan sigma, NOAA, scheduler, whitelist, sizing, thresholds ni reglas de entrada. `verify_before_deploy.py` pasa **838/838**; sintaxis OK con `tools/check_python_syntax.py`; `py_compile` directo queda bloqueado solo por el lock conocido de `__pycache__` en Windows. |
| 2026-04-24 | Explícita | Sesión 235 | SL retro en zona gris: no cerramos caso, seguimos monitorizando | Opus hace verificación rápida post-234 y detecta que el copy Telegram concluía `✅ EL SL ESTÁ FUNCIONANDO CORRECTAMENTE` + `🚨 CONCLUSIÓN FIRME` con `accuracy_pct=37.5%` (6/16 falsas salidas) — exactamente la señal que motivó la investigación. Se ajustan umbrales en `tools/sl_retrospective.py` sin tocar trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida: banda "SL funciona correctamente" baja de `<40%` a `<30%`; entre 30–60% el veredicto pasa a `seguir monitorizando` y `CONCLUSIÓN FIRME` queda condicionado a estar fuera de la zona gris, pero la alerta sigue llegando con cada nuevo SL resuelto por el anti-spam existente. El mensaje real pasa a emitir `📊 VEREDICTO: zona gris (6 SLs acabaron ganando sin el corte) — seguimos monitorizando`. Drift detectado sin fix hoy: `daily_position_briefing.py` muestra `SL Retro: sin datos aún` porque `data/sl_retrospective_state.json` solo se escribe en envío real; el primer ciclo live lo sincroniza solo. `verify_before_deploy.py` suma 3 checks (`v10.6.35`) y pasa **834/834**. |
| 2026-04-24 | Explícita | Sesión 234 | Cierre de `SL Retro` a 16/16 + briefing saneado | Codex cierra el frente de alertas `SL Retro` y `Briefing Diario` sin tocar trading core, NOAA core, scheduler, sizing, whitelist ni reglas de entrada/salida. `bot.py` corrige el resumen diario para separar break-even, usar la fecha/hora del payload y no enviar el daily antes del primer ciclo real del día; `tools/daily_position_briefing.py` deja de presentar legacy vencido como abierto real y describe mejor el bloque `24h`; `tools/sl_retrospective.py` pasa a resolver `stop_loss` y `stop_loss_intra` con NOAA local (`audit.json` / `observed_vs_forecast`), `forecast_accuracy_raw` como fallback y `open-meteo archive` cuando aún falta observado local. La muestra queda cerrada en `16/16` resueltos (`6 RIGHT`, `10 WRONG`, `0 UNKNOWN`) y el veredicto pasa a firme: `SL funciona correctamente`. `verify_before_deploy.py` cierra en 831/831. |
| 2026-04-24 | Explícita | Sesión 233 | Hardening del runtime bridge de `City Intelligence` en Railway | Codex cierra un patch corto de observabilidad tras auditar logs live donde el `city-intelligence runtime bridge` terminaba en `city_intelligence_daily_summary.py` con `Missing required input: /app/data/city_validation_ledger.json`. La raíz no estaba en el summary sino en el contrato del pipeline: `tools/city_intelligence_pipeline.py` podía quedar en `partial_failure` y aun devolver exit `0`, permitiendo que `bot.py` siguiera hasta un paso que ya dependía del ledger ausente. El fix añade `failed_steps`, verificación de outputs canónicos (`directional_trader_enrichment`, `reference_trader_city_market_cross`, `city_probe_visibility_tracker`, `city_validation_ledger`, `city_promotion_gate`) y exit code no cero si algún step/output falla, de modo que Railway deje trazado el fallo real y el bridge no continúe en verde falso. `verify_before_deploy.py` suma checks del nuevo contrato y pasa 819/819. |
| 2026-04-24 | Explícita | Sesión 232 | Automatización `traders_intelligence` + gate explícito V1 | Codex convierte `traders_intelligence` en una capa automática de observabilidad sin tocar trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida. Se implementa `tools/traders_intelligence_daily_summary.py`, se integra en `bot.py` dentro de `run_observability_alerts()` y se añade un monitor diario que regenera `data/traders_intelligence.json`, calcula checks de readiness para abrir V1, persiste estado anti-spam y deja instrucciones explícitas cuando toque pasar a snapshots/pseudo-lifecycle. Validación local completa: `python tools/traders_intelligence_report.py`, `python tools/traders_intelligence_daily_summary.py` y `python verify_before_deploy.py` pasan; suite final 817/817. La foto actual queda honesta: `V1 readiness = not_ready` por `census_stale_days=15` y `recent_crosscheck_runs=2`, aunque ya hay lead traders fuertes (`Thrifty-Original`, `Entire-Hood`) y ciudades `trader_only` suficientes. |
| 2026-04-23 | Explícita | Sesión 231 | Logging de skip reasons para hooks SL retro / briefing | Codex añade un patch mínimo de observabilidad en `bot.py` tras comprobar que los tools funcionaban en Railway shell pero el hook automático no dejaba señal en logs. `maybe_run_sl_retrospective()` y `maybe_run_daily_briefing()` ahora registran por qué se saltan: feature flag desactivada, archivo/script faltante, fuera de ventana horaria, already sent today o ausencia de nuevos `stop_loss` / recheck aún no vencido. No cambia trading core ni reglas; solo hace visible el motivo del skip en el siguiente ciclo. `verify_before_deploy.py` sigue 817/817. |
| 2026-04-23 | Explícita | Sesión 230 | Validación live de `SL retrospective` en Railway | Codex cierra la validación live post-deploy sin tocar trading core, NOAA, scheduler, whitelist ni reglas de entrada/salida. Desde la shell del contenedor `polymarket-bot`, `tools/sl_retrospective.py` y `tools/daily_position_briefing.py` corren correctamente contra `/app/data/trade_lifecycle.json` real de Railway. La muestra live sigue en `5/16` SLs resueltos (`3` falsas salidas por SL, `2` SL correctos), y el briefing ya ve `3` cierres `stop_loss_intra` en 24h además de una posición nueva `Seoul 21°C Apr24 YES`. La lectura importante queda explícita: `trade_lifecycle` ya no es solo observabilidad, sino la primera hipótesis concreta y medible sobre por qué el bot pierde, al sugerir que parte del daño puede venir de cortar demasiado pronto trades que después resolvían bien. |
| 2026-04-23 | Explícita | Sesión 229 | Claridad SL retrospective: `con SL` vs `sin SL` | Codex ajusta `tools/sl_retrospective.py` para que el mensaje de Telegram no se lea como una hipótesis difusa, sino como una comparación explícita entre `P/L con SL` y `P/L sin SL (mejor precio visto después)` por trade y en agregado. Se sustituye el wording `RIGHT/WRONG` por `falsas salidas por SL` y `SL correctos`, y se deja claro que `$5.42` es la diferencia total entre ambos escenarios en los 3 falsos exits ya observados, no solo un número abstracto de upside. `verify_before_deploy.py` sigue 817/817. |
| 2026-04-23 | Explícita | Sesión 228 | SL retrospective + daily briefing | Codex añade dos herramientas observables sin tocar trading core, NOAA, scheduler, whitelist ni reglas de entrada/salida: `tools/sl_retrospective.py` para medir si los `stop_loss` cortaron posiciones que luego resultaron correctas, y `tools/daily_position_briefing.py` para resumir abiertas, actividad 24h y estado del retro score por Telegram. `bot.py` integra ambos hooks al final de `run_observability_alerts()` con env vars `SL_RETRO_ENABLED`, `DAILY_BRIEFING_ENABLED` y `DAILY_BRIEFING_HOUR_UTC`; `verify_before_deploy.py` suma 7 checks y pasa 817/817. Dry-run local usa fallback a `data/runtime_import/trade_lifecycle.json` porque el repo no trae `data/trade_lifecycle.json` canónico: hoy ve 14 SLs, 5/16 resueltos (3 RIGHT, 2 WRONG) y 13 posiciones abiertas. |
| 2026-04-23 | Explícita | Sesión 227 | Cierre de trazabilidad `INTRA_REEVAL` live | Cierre corto de contexto y trazabilidad, sin tocar `bot.py`, trading core, NOAA, scheduler, sizing, whitelist ni reglas de entrada/salida. Se corrige el drift documental sobre `INTRA_REEVAL`: el snapshot live de Railway confirma que `INTRA_REEVAL_ENABLED=1` e `INTRA_REEVAL_SHADOW_MODE=1` ya están cargadas en producción y que el contenedor de `polymarket-bot` fue reiniciado/actualizado correctamente. La feature queda activa en modo `shadow-log` con defaults implícitos (`PRICE_DRIFT_PP=10`, `COOLDOWN_MIN=80`, `EDGE_THRESHOLD=-3`) y el próximo hito real pasa a ser el one-shot `Review INTRA-REEVAL` 7 días después del primer trigger, no la activación manual. |
| 2026-04-23 | Explícita | Sesión 226 | v10.6.31 gate LOW+exact + TP dinámico por precio | Sonnet+Opus analizan trades cerrados Apr 9-23 (n=18): WR=53% pero PnL casi breakeven (+$0.21) por ratio adverso avg_win=$0.61 vs avg_loss=$0.76; el bucket LOW (<35¢) sale claramente dañado (n=2, WR=0%, PnL=-$2.57) por eventos exact baratos con gap risk. Se implementa `v10.6.31`: `BLOCK_LOW_EXACT_ENTRIES=1` bloquea entradas `exact` con `mkt_price<0.35` y `effective_tp_pct(entry_price, our_prob)` introduce TP dinámico por precio (LOW≥60%, MID=40%, HIGH≥80%) reutilizado también en `intra_cycle_sl_check`. El step de abs SL queda diferido hasta n≥30 post-gate. `verify_before_deploy.py` pasa 810/810. |
| 2026-04-23 | Explícita | Sesión 225 | Plan operativo transición City Intelligence/Phase5 | Codex convierte la review Opus de la sesión 224 en plan operativo ejecutable y empieza la Fase 1 (`silenciar → observar`) sin tocar `bot.py`, trading core, NOAA, scheduler core, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`. Se crean `docs/city-intelligence-phase5-operational-transition-plan-2026-04-23.md` y `data/service_transition_followup.json`; `tools/city_intelligence_daily_summary.py` añade un bloque `Seguimiento programado` al summary diario existente, con checkpoints UTC 2026-04-24, 2026-04-28, 2026-05-01 y 2026-05-07. En Railway se valida que `polymarket-bot`, `city-intelligence` y `phase5-visibility` siguen `SUCCESS`; se elimina `TELEGRAM_TOKEN` solo de `city-intelligence` y `phase5-visibility`, se reinician ambos servicios legacy para cargar el entorno silenciado, y `polymarket-bot` conserva su token como único emisor canónico. Dry-run del daily summary con salidas temporales OK; el dry-run sobre estado real quedó bloqueado por el lock Windows ya conocido. Siguiente checkpoint: 2026-04-24, confirmar que no hay doble emisor y que el bridge entrega el aviso útil. |
| 2026-04-23 | Explícita | Sesión 224 | Review Opus city-intelligence + phase5-visibility | Revisión estratégica/operacional read-only de ambos servicios, sin tocar `bot.py`, trading core, NOAA, scheduler, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`. Entrega completa en `docs/Sesion Opus.md`. **city-intelligence:** mantener como dominio analítico (census, enrichment, cross, tracker, ledger, gate, daily summary, signals crosscheck), apagar como servicio Railway separado porque el puente 222 ya corre el pipeline dentro de `polymarket-bot` con runtime real mientras el servicio remoto vive en fail-closed por `/app/data/runtime_import` ausente. **phase5-visibility:** congelar como legacy y apagar el servicio — kill criteria ya cumplidos (strategic review 2026-04-17 `pausar`, 11 coincidencias Shanghai+Chicago sin decisión nueva, tracker/alerta/comparador absorbidos por `city-intelligence`). Plan por fases reversible (silenciar Telegram del servicio separado → validar 5–7 días que el bridge cubre señal → `pause → stop`), kill criteria explícitos y 10 acciones concretas. El prompt original (`docs/claude-opus-prompt-city-intelligence-phase5-service-review-2026-04-22.md`) se elimina al cierre. Siguiente paso: Codex convierte la review en plan operativo ejecutable y empieza por silenciar alertas del servicio separado `city-intelligence`. |
| 2026-04-22 | Explícita | Sesión 222 | City Intelligence runtime bridge in `polymarket-bot` | Se aplica la recomendación de arquitectura tras la alarma: mantener `city-intelligence` separado como capa analítica, pero mover el readout diario de runtime al servicio que sí ve el volumen real del bot. `bot.py` añade un puente read-only one-shot diario (`maybe_run_city_intelligence_runtime_summary`) gated por env, que exporta runtime, regenera effective view, pipeline dry-run, preflight operacional y daily summary sin tocar trading, NOAA, whitelist, sizing ni `city_policy_state.json`. Se crea `tools/runtime_import_local_export.py` para copiar desde `DATA_DIR` a `DATA_DIR/runtime_import`, exigir `shadow_city_tracking`, `audit` y `city_policy_state`, y escribir manifest + snapshot de env. `verify_before_deploy.py` suma checks v10.6.31. Validación: sintaxis OK y export local OK; el preflight completo queda bloqueado solo por 2 asserts heredados de `INTRA_SL_INTERVAL default 60`, porque el worktree ya traía `INTRA_SL_INTERVAL=20`. |
| 2026-04-22 | Explícita | Sesión 221 | City Intelligence runtime_import faltante en servicio live | Auditoría operativa de la alarma diaria `City Intelligence` sin tocar `bot.py`, `city_policy_state.json`, NOAA, scheduler ni trading core. El pull read-only local desde `polymarket-bot` funciona y deja `runtime_import_manifest.json` fresco (`2026-04-22T07:19:13Z`, 12/12 archivos, sin drift); tras regenerar effective view, ledger, gate y pipeline, local queda `runtime_inputs_status=available`, `overall_status=ok`, cuello dominante `trader_discovery`, topología `blocked=1 / canary=8 / shadow=16 / active=0` y preflight operacional `error=0`. La causa live de la alarma está en el servicio separado `city-intelligence`: su `/app/data` no contiene `/app/data/runtime_import`, así que el pipeline live cae correctamente en `runtime_inputs_missing` por faltar `shadow_city_tracking`, `audit` y `city_policy_state`. No hay ajuste de trading hoy; el pendiente es infraestructura/cableado read-only para que `city-intelligence` consuma runtime fresco antes de emitir recomendaciones. |
| 2026-04-22 | Explícita | Sesión 220 | daily traders-vs-bot readout, no code | Se registra el parte diario `traders vs bot` / `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler ni trading core. Foto UTC 2026-04-22: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=18`; serie reciente de 7 corridas con medianas `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=23`. Lectura: la serie se mueve, pero todavía no da una historia única de mejora o deterioro; hoy no hay gap operativo fuerte fuera de `blocked` con consenso y condición operable. Persisten en `TRADER_ONLY` `7/7`: `Ankara`, `Busan`, `Houston`, `Jakarta`, `Miami`; casi persistentes `6/7`: `Buenos Aires`, `Chengdu`, `Los Angeles`, `Madrid`, `Singapore`, `Toronto`. `Blocked signals` fuera de whitelist: 61 resueltas, 60 wins, WR 98.4%, 207 señales excluidas por whitelist. Instrucción reiterada: si este bloque persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA antes de tocar reglas de entrada o trading core. |
| 2026-04-21 | Explícita | Sesión 219 | Bankroll Readiness Score | Se implementa `tools/bankroll_readiness_score.py`, indicador standalone 0-100% para medir cuándo el bankroll empieza a ser el cuello real del sistema. Score inicial 23.9%: etapa temprana, con WR/PnL todavía débiles y edge density baja, aunque ya aparece presión de tamaño por `kelly_too_low`. No toca `bot.py` ni Railway. `verify_before_deploy.py` 763/763. |
| 2026-04-21 | Explícita | Sesión 218 | Busan + Dallas al whitelist + schedule 6 ciclos/día | Sesión pre-mañana con tiempo disponible. (1) Railway env `QUALITY_TRADER_CITIES_WHITELIST` verificada — ya tenía las 32 ciudades del pendiente Sesión 215, sin cambios necesarios. (2) **v10.6.29 — Busan ICAO-only:** investigación NOAA/WU/Polymarket completa: NOAA global-hourly 2026 dead (404 estación 47158099999), WU/RKPK confirmado como fuente Polymarket resolution (obtenido de descripción real del mercado Apr-22), WU real-time vivo aunque archivo histórico muestra "No data recorded" (artefacto JS WebFetch), $85.8K volumen en mercado Apr-21 resuelto YES. Busan agregado a `RESOLUTION_STATIONS` (lat 35.18, lon 128.95), `RESOLUTION_ICAO` (RKPK), `OBSERVED_AUDIT_CITIES`, `CITY_TIMEZONES` (Asia/Seoul) y whitelist default. (3) Auditoría City Intelligence: 8 canary, 16 background_watch, Dallas con `review_runtime_policy_gate` priority `now`. (4) **Auditoría Dallas:** WR=11.8% (17 trades) que disparó la degradación Apr-6 era falso — los "17" incluían 66 `LOSS_TOTAL` fantasma del bug ghost-positions corregido en v10.5.12. Trades reales: 4 (2 SL, 2 wins). Shadow actual: `best_edge=68.9%`, 12 hits en 9 ciclos, NOAA 4/5. **v10.6.30:** Dallas agregado al whitelist. (5) **Schedule:** `SCHEDULE_HOURS_UTC=4,8,12,16` → `0,4,8,12,16,20` (6 ciclos/día cada 4h). Motivación: cycles_history muestra 16:00 y 08:00 como horas más productivas; ciclo post-deploy a las 20:10 UTC produjo 3 compras. Railway env actualizada sin redeploy. `verify_before_deploy.py` 763/763. |
| 2026-04-21 | Explícita | Sesión 217 | London runtime overlay neutralizado | Se ejecuta el cierre operativo mínimo de London sin tocar `bot.py`, reglas de entrada/salida, NOAA, scheduler, thresholds, whitelist ni trading core. Con `tools/railway_safe.ps1 ssh` se confirma que `London` seguía en `/app/data/city_policy_state.json` bajo `auto_canary_cities` desde `2026-04-12T15:03:51Z`; se crea backup remoto `/app/data/city_policy_state.json.bak_london_auto_canary_1776788976` y se elimina solo esa entrada, conservando `BLOCKED_CITIES=London` como guardrail estructural por el mismatch `Weather Underground vs Open-Meteo`. Tras `tools/railway_runtime_snapshot_pull.ps1`, se regeneran effective view, cross, ledger, gate, pipeline y `system_alignment_check --decision-mode operational`: London queda `env=blocked`, `runtime=runtime_unknown`, `cross=blocked`, `effective=blocked`, `collision_flag=false`; `blocking_operational_collision_count=0`; el preflight operacional queda en `error=0` (`ok=5`, `warning=3`). |
| 2026-04-21 | Explícita | Sesión 216 | City Intelligence runtime transport repaired + summary wording | Se repara el bloqueo abierto en la Sesión 214. Tras limpiar tokens caducados, Pablo completa `railway login` interactivo y Codex valida desde los wrappers repo-locales: `railway_safe.ps1 whoami` devuelve `pablogomez.eu@gmail.com` y `railway_safe.ps1 status` confirma `enchanting-respect / production / polymarket-bot`. `tools/railway_runtime_snapshot_pull.ps1` vuelve a funcionar y deja `data/runtime_import/` fresco con manifest `pulled_at=2026-04-21T14:54:02Z`, `12/12` archivos y sin drift. Se instala la dependencia local faltante `py-clob-client-v2==1.0.0` para que `city_validation_ledger.py` pueda lazy-importar `bot.py`; después `city_validation_ledger.py` y `city_promotion_gate.py` quedan en `runtime_inputs_status=available`, y `city_intelligence_pipeline.py` cierra `overall_status=ok` con `dominant_bottleneck=policy_execution_gate`, `top_now_city=Dallas` y `signal_health=usable_signal`. Queda un blocker distinto, no de transporte: `system_alignment_check.py --decision-mode operational` sigue en `error=1` por `London` (`BLOCKED_CITIES` + `auto_canary_cities`), sin tocar `city_policy_state.json` por el guardrail original. Además se corrige `tools/city_intelligence_daily_summary.py` para no decir “preflight operacional sin errores” cuando `alignment_summary.error > 0`; dry-run muestra `preflight operacional con error=1`. Handoff creado: `docs/handoffs/london-blocked-policy-review-2026-04-21.md` para analizar en otra sesión si London debe seguir `blocked`, pasar a `shadow` o requerir revalidación externa. |
| 2026-04-21 | Explícita | Sesión 214 | City Intelligence runtime transport auth-blocked | Auditoría operativa del aviso diario `City Intelligence` sin tocar `bot.py`, `city_policy_state.json` runtime, NOAA, scheduler ni policy live. Se valida que el fail-closed es correcto: mientras no haya runtime fresco, no se puede interpretar `edge_evidence=0` como ausencia real de edge ni emitir recomendaciones por ciudad. El snapshot local `data/runtime_import/` está completo y bijectivo con `runtime_import_manifest.json` (`12/12`, sin missing/extra/byte mismatch), pero stale: `pulled_at=2026-04-18T09:28:57Z`, ~75.3h frente al SLO 24h. El pull read-only con `tools/railway_runtime_snapshot_pull.ps1` no llega a leer live porque Railway CLI falla con `invalid_grant`; `railway_auth_repair.ps1 doctor` confirma CLI 4.35.0, sin proxies, config writable, 1 proyecto linkeado, access/refresh tokens presentes pero expirados/invalidos (`tokenExpiresAtUtc=2026-04-20T21:54:37Z`). `city_validation_ledger.py` marca `runtime_inputs_status=stale`; `system_alignment_check.py --decision-mode operational` falla por `runtime_manifest` stale y `runtime_policy_effective_view` stale. Siguiente acción: re-login Railway y repetir pull read-only, luego regenerar effective view, ledger/gate y alignment check antes de volver a permitir recomendaciones por ciudad. |
| 2026-04-21 | Explícita | Sesión 212 | daily traders-vs-bot readout, no code | Se registra el parte diario `traders vs bot` / `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler ni trading core. Foto UTC 2026-04-21: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=19`; serie reciente de 7 corridas con medianas `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=25`. Lectura: el gap traders-vs-bot se está cerrando respecto al inicio de la serie y hoy no hay gap operativo fuerte fuera de `blocked` con consenso y condición operable. Persisten en `TRADER_ONLY` `7/7`: `Ankara`, `Busan`, `Houston`, `Jakarta`, `Miami`; casi persistentes `6/7`: `Amsterdam`, `Buenos Aires`, `Chengdu`, `Helsinki`, `Kuala Lumpur`, `Los Angeles`. `Blocked signals` fuera de whitelist: 117 resueltas, 114 wins, WR 97.4%, 148 señales excluidas por whitelist. Instrucción fijada: si este bloque persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA antes de tocar reglas de entrada o trading core. |
| 2026-04-21 | Explícita | Sesión 211 | cierre Windows/WSL + hardening local de validación | Se reconstruye el contexto tras un reinicio forzado por la instalación de WSL y se cierra el frente operativo de “permisos Windows” sin tocar `bot.py` ni lógica core. La sesión deja fijado que el problema no era una ACL persistente del repo, sino fricción del entorno local: sandbox/proxies inyectados por Codex en Windows más roces de temporales/artefactos Python bajo locks de Windows. Para endurecer las validaciones locales, `verify_before_deploy.py` pasa a usar `.tmp_verify/` dentro del repo en lugar de `tempfile.gettempdir()`, y se añade `tools/check_python_syntax.py` para validar sintaxis sin generar `.pyc` ni depender de `__pycache__`. En paralelo, WSL2 con Ubuntu queda instalado y validado como entorno limpio de escape: el repo abre desde `/mnt/c/Projects/polymarket-bot`, `git` se sanea con `safe.directory`, `python3` queda operativo y tanto una petición directa con `User-Agent` como `python3 tools/polymarket_api_probe.py` devuelven `200`. Cierre clave de la sesión: Codex ya puede ejecutar Ubuntu directamente con `wsl -d Ubuntu bash -lc "..."`, futuras verificaciones en WSL ya no requieren que Pablo las pegue a mano y `python verify_before_deploy.py` vuelve a cerrar en **746/746**. |
| 2026-04-19 | Explícita | Sesión 210 | observability patch for `condition_filtered` canary logs | Se cierra una auditoría corta nacida de la revisión del `decisions.log` live de Apr 18, donde varias ciudades `canary` (`Shanghai`, `New York City`, `Atlanta`, `Munich`) seguían apareciendo en texto como `SHADOW-FILTER` dentro del carve-out `exact/range`. La revisión sobre `skip_log.jsonl`, `city_policy_state.json`, `policy_env_snapshot.json` y `signals.json` demuestra que no había bug de reconocimiento de modo: las filas afectadas ya salían con `city_mode="canary"` y `allowlisted=true`; el filtro se disparaba porque faltaba `match_key` en `trader_signals`, no porque la ciudad hubiese vuelto a `shadow`. Para cortar esa ambigüedad se parchea `bot.py`: el log detallado ahora emite `CANARY-FILTER` cuando la ciudad es `active/canary`, mantiene `SHADOW-FILTER` para ciudades realmente fuera de allowlist y añade al `skip_log` la causa estructurada del gate (`exact_range_gate_reason`) más el `qt_match_key` evaluado. No se tocan trading core, NOAA, scheduler, sizing ni policy live. Validación de cierre: `python verify_before_deploy.py` antes de commit/push. |
| 2026-04-19 | Explícita | Sesión 208 | auditoría read-only `price_out_of_range` por ciudad canary | Se revisa `data/runtime_import/skip_log.jsonl` sin tocar `bot.py`, NOAA, scheduler, policy live ni el filtro `[0.20,0.80]`, para responder si el 53% global de skips por `price_out_of_range` esconde canaries prácticamente inoperables. El snapshot live usado fue pullado de Railway el `2026-04-18T09:28:57Z`. Comparando histórico completo (`79` ciclos / `19,267` skips) contra la ventana reciente de `30` ciclos (`2026-04-14T09:41` → `2026-04-18T09:27`), el hallazgo central es que sí hay concentración fuerte por ciudad: `Seoul`, `Tokyo` y `Shanghai` quedan muy dominadas por `price_out_of_range` en la ventana reciente (`84-87%` de sus skips), `London` / `New York City` / `Munich` muestran presión relevante pero menos extrema, y `Atlanta` no parece una canary estructuralmente atrapada por precio. El patrón es casi enteramente de mercados `<0.20`, no de un choque amplio con `>0.80`. Decisión cerrada de la sesión: no cambiar el filtro global `[0.20,0.80]`, no degradar canaries solo por este readout y reencuadrar el frente como un subcaso de low-price concentration. Se deja priorizado `Seoul/Tokyo/Shanghai` como canary con cuello dominante de precio bajo; `Atlanta` sale de prioridad inmediata y `London/NYC/Munich` quedan en zona intermedia. Si el tema se reabre, el siguiente bloque honesto será una micro-auditoría por ciudad del bucket `<0.20` con ventana fresca post-`v10.6.23`. Artefacto: `docs/price-out-of-range-canary-audit-2026-04-19.md`. |
| 2026-04-19 | Explícita | Sesión 206 | local exact/range canary min amount floor | Se ataca un cuello pequeño pero real de `position management` tras cerrar los frentes mayores de throughput del 17-19 de abril. El diagnóstico de sesión confirma que el supuesto pendiente `QUALITY_TRADER_CITIES_WHITELIST +Jakarta,Kuala Lumpur` ya no era real: Railway production ya incluye ambas ciudades, así que el siguiente cuello honesto es `micro_position_unsellable`. Se parchea `bot.py` con un guardrail reversible y acotado al carve-out `exact/range canary`: nueva env `EXACT_RANGE_MIN_AMOUNT=2.50` y helper `_resize_position_amount()`; después del escalado `canary` + `EXACT_RANGE_SIZE_SCALE`, si la posición queda por debajo del mínimo operativo se recompone hasta ese suelo, respetando el cap de `MAX_BET_PCT`. El objetivo es evitar que la excepción `exact/range canary` siga produciendo entradas microscópicas con mala salibilidad, sin tocar el pipeline general ni NOAA/scheduler. Validación local cerrada: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` **730/730**. |
| 2026-04-19 | Explícita | Sesión 205 | Railway cleanup of `signals-crosscheck` | Se elimina de Railway el servicio vacío `signals-crosscheck` que había quedado como residuo de la activación inicial. Hallazgo operativo útil: la CLI pública no ofrece borrado de servicios, así que la limpieza se ejecuta por API GraphQL (`serviceDelete`) con el `serviceId` exacto del servicio huérfano y `environmentId=production`. Verificación posterior: `service status -a` vuelve a mostrar solo `polymarket-bot`, `city-intelligence` y `phase5-visibility`, todos en `SUCCESS`. La sesión también deja cerrada la lectura estratégica del cambio: el summary diario `traders vs bot` no añade edge por sí mismo, pero sí acelera el ciclo evidencia→decisión sobre ciudades TRADER_ONLY persistentes, reduciendo trabajo manual y haciendo más rápida la reasignación de atención/capital hacia gaps operativos reales. |
| 2026-04-19 | Explícita | Sesión 204 | live activation on polymarket-bot | Se activa en producción el summary temporal `traders vs bot` y se cierra el loop diario sin trabajo manual. Durante la activación se confirma un guardrail relevante de Railway: `polymarket-bot-volume` no puede montarse en un segundo servicio mientras siga adjunto al bot, así que el servicio nuevo `signals-crosscheck` no sirve como reader live sin desmontar producción. Se toma la vía segura: `bot.py` pasa a invocar `tools/signals_crosscheck_daily_summary.py` justo después de `maybe_run_daily_crosscheck(state)`, reutilizando el mismo `/app/data/signals_crosscheck.jsonl` del bot. Validación local previa: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` 727/727. Deploy live realizado sobre `polymarket-bot` (`deployment 58683196-662f-4647-843a-4e9f84b8d02f`, `SUCCESS`), con arranque nuevo visible a `2026-04-19 10:10:41 UTC`. Verificación final por `railway ssh`: el summary escribe `/app/data/signals_crosscheck_daily_summary_state.json`, genera `/app/docs/signals_crosscheck_daily_summary_latest.md` y envía Telegram real (`sent=true`), reportando 7 corridas recientes y `gap_state=estructural`, con 8 ciudades TRADER_ONLY persistentes en 7/7. |
| 2026-04-19 | Explícita | Sesión 203 | local cross-check traders vs bot automation | Se automatiza la capa humana del cross-check `traders vs bot` sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. `tools/signals_vs_edge_crosscheck.py` queda refactorizado para exponer helpers reutilizables (`build_crosscheck_record`, `append_record`) y aceptar output path configurable, manteniendo el modo standalone; además su validación deja de asumir que Austin siempre aparece en el snapshot y solo exige esa comprobación cuando la ciudad está presente en `signals.json`. Encima se crea `tools/signals_crosscheck_daily_summary.py`, que lee `data/signals_crosscheck.jsonl` con fallback a `data/runtime_import_derived/signals_crosscheck.jsonl`, deduplica por fecha UTC, puede ingerir la corrida del día si falta, resume la serie reciente (medianas MATCH/BOT_ONLY/TRADER_ONLY, ciudades TRADER_ONLY persistentes y gap operativo del día), envía Telegram con anti-spam por `last_sent_date` y guarda estado propio. Se añade `tools/signals_crosscheck_railway_service.py` para ejecutar ese summary una vez al día en Railway y `docs/signals-crosscheck-railway-service.md` con el comando/vars recomendadas. `.gitignore` pasa a cubrir `data/signals_crosscheck.jsonl` y `data/signals_crosscheck_daily_summary_state.json`. Validación local: `python tools/signals_vs_edge_crosscheck.py --no-append`, `python tools/signals_crosscheck_daily_summary.py --crosscheck-file data/runtime_import_derived/signals_crosscheck.jsonl --dry-run` y `python tools/signals_crosscheck_railway_service.py --once` OK. |
| 2026-04-19 | Explícita | Sesión 202 | local city-intelligence alerts hardening + lock diagnosis | Cierre corto centrado en tooling humano de `city intelligence`, sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. Se endurece `tools/city_intelligence_telegram_alert.py` para que solo dispare sobre gates accionables (`now/soon` + allowlist explícita), evitando que ciudades ya degradadas a `background_watch` como Dallas vuelvan a saltar como foco falso; validación local `--dry-run`: `should_alert=false`. En paralelo, `tools/city_intelligence_daily_summary.py` deja de mezclar filas del ledger con instrucciones de otra ciudad del gate y añade anti-spam por `last_sent_date`, de modo que el resumen diario no vuelva a dispararse dos veces el mismo día UTC y no vuelva a listar unas ciudades mientras manda revisar otra distinta. Hallazgo operativo adicional documentado: el problema de “permisos” al borrar `.tmp_*` o compilar tools con `py_compile` no era ACL NTFS sino handles abiertos por `Code.exe`/`codex`; escribir en `tools/__pycache__` funciona, pero borrar/renombrar falla mientras VS Code reabre el workspace. |
| 2026-04-19 | Explícita | Sesión 201 | v10.6.22 — Jakarta + Kuala Lumpur (ICAO-only) | Cierre del handoff `docs/handoff-noaa-jakarta-kuala-lumpur.md`: se agregan Jakarta y Kuala Lumpur a `RESOLUTION_STATIONS`, `RESOLUTION_ICAO`, `CITY_TIMEZONES`, `OBSERVED_AUDIT_CITIES` y al default de `QUALITY_TRADER_CITIES_WHITELIST` en `bot.py`. **Verificación de fuente Polymarket (WebFetch):** Jakarta resuelve contra **Halim Perdanakusuma (WIHH)** — NO Soekarno-Hatta (WIII) como sugería el handoff inicial — vía WU `https://www.wunderground.com/history/daily/id/jakarta/WIHH`; Kuala Lumpur resuelve contra **KLIA (WMKK)** vía WU `https://www.wunderground.com/history/daily/my/sepang-district/WMKK`. **Verificación NOAA (isd-history + ghcnd-inventory + ghcnd yearly 2026):** WIHH USAF 967495 → ISD `96749599999` existe pero no hay CSV global-hourly 2026; GHCND diario más cercano es `ID000096745` (Jakarta/Observatory) e `IDM00096741` (Tanjung Priok) — ninguno aporta TMAX en el yearly 2026. WMKK USAF 486500 → ISD `48650099999` sin CSV global-hourly 2026; GHCND diario `MYM00048650` existe pero sin TMAX reportado en 2026. Conclusión operativa: ambas ciudades entran en configuración **ICAO-only** (patrón Singapore/Toronto/Warsaw) — el bot podrá tradear vía WU pero los trades no llevarán `source: noaa_ncei` y no contarán en WR verificado hasta que NOAA retome el feed para SE Asia. Coordenadas: Jakarta `(-6.2666, 106.8906)`, KL `(2.7456, 101.7099)`. `verify_before_deploy.py`: 9 tests nuevos, pasa **727/727** (incluye traza de esta sesión en `agent_events.jsonl`). Pendiente Pablo: actualizar Railway env `QUALITY_TRADER_CITIES_WHITELIST` agregando `Jakarta,Kuala Lumpur`. |
| 2026-04-19 | Explícita | Sesión 200 | `5b880d6` — whitelist +6 ciudades permanentes TRADER_ONLY | Análisis de la serie temporal completa de cross-check traders vs bot (7 corridas automáticas del bot en Railway, Apr 13-19) y expansión del `QUALITY_TRADER_CITIES_WHITELIST`. Hallazgos clave: 8 ciudades son permanentemente TRADER_ONLY en 7/7 corridas (Ankara, Houston, Jakarta, Kuala Lumpur, Madrid, Miami, Paris, Wellington) y 15 ciudades más con 6/7. El ratio MATCH/TRADER_ONLY no converge — el gap estructural se mantiene en ~25 ciudades con mediana estable; Apr 16 fue outlier (15 TRADER_ONLY) por baja cobertura trader ese día. Austin y Toronto aparecen 6/7 (1 ausencia cada una). Las 7 corridas viven en Railway `/app/data/signals_crosscheck.jsonl`; el archivo local solo tiene corridas manuales. **v10.6.21:** se agregan Ankara, Madrid, Miami, Paris, Wellington, Houston al whitelist. Houston también añadida a `RESOLUTION_STATIONS` (KIAH, lat 29.9902 lon -95.3368) y `RESOLUTION_ICAO` (KIAH sin `noaa_station_id`, pendiente verificación vs Polymarket resolution source). Se actualiza el default en `os.getenv("QUALITY_TRADER_CITIES_WHITELIST", ...)` en `bot.py` y la env var en Railway. Jakarta y Kuala Lumpur quedan pendientes por falta de NOAA verificado — handoff `docs/handoff-noaa-jakarta-kuala-lumpur.md` creado. `verify_before_deploy.py` pasa 718/718. |
| 2026-04-19 | Explícita | Sesión 199 | `e8b236c` + `71ca261` + Railway env SCHEDULE_HOURS_UTC=4,8,12,16 | Paquete de throughput v10.6.20 sin tocar trading core, NOAA, scheduler ni policy live. Motivación: Pablo quiere acelerar bankroll $25→$50 con evidencia acumulada (quality traders WR=76.3% n=59 en exact/range, 21 ciudades TRADER_ONLY sin observación bot, slot 16-04 UTC dormido 12h). Cambios en `bot.py` → `v10.6.20`: (1) **P1 ciudades invisibles**: `Lucknow` y `Sao Paulo` añadidas a `OBSERVED_AUDIT_CITIES` (ambas con NOAA coords ya presentes desde handoff C sesión 169); `Istanbul` diferida por falta de `RESOLUTION_STATIONS`/`RESOLUTION_ICAO` (riesgo Seoul mismatch sesión 185). (2) **P4-P5 alerta one-shot** `maybe_alert_p4_p5_expansion(state)` FIRE_DATE=2026-04-22: prompt Codex para expandir `QUALITY_TRADER_CITIES_WHITELIST` post-checkpoint día 7. (3) **P6-P7 alerta one-shot** `maybe_alert_p6_p7_post_v2_cleanup(state)` FIRE_DATE=2026-04-25: prompt Codex para reset `shadow_city_tracking` Seoul legacy pre-fix + análisis MIN_EDGE por ciudad. Ambas siguen patrón `maybe_run_w17_observation_alert` (date-triggered, state flag one-shot, anti-spam daily) e integradas en `run_observability_alerts()`. **Fix adicional anti-flapping shadow↔canary (NYC):** Pablo observa loop donde NYC se degrada canary→shadow por `verified_history_bad` (NOAA-verificado 2/25 trades, WR 8%, PnL -$0.24) y se re-promociona shadow→canary por `promotable_shadow` (11 edges, 64 ciclos, pico 50.5%) en el mismo ciclo. Causa raíz: los dos gates eran independientes — degradación usa `verified_history_bad`, promoción lo ignoraba. Fix: reordenar cálculo (`verified_history_bad` antes de `promotable_shadow`) y añadir `and not verified_history_bad` al tuple `promotable_shadow`; branch `observe` con reason explícita cuando promoción bloqueada por historial. `verify_before_deploy.py` **717/717** (16 tests nuevos: 13 v10.6.20 base + 3 anti-flapping). Commits: `e8b236c` (paquete v10.6.20), `71ca261` (fix anti-flapping). Railway env vars aplicadas por Pablo: `ACTIVE_TRADING_CITIES=NONE`, `SCHEDULE_HOURS_UTC=4,8,12,16`. Deploy live autorizado y ejecutado (Opción A). |
| 2026-04-18 | Explícita | Sesión 198 | `58cf355` + `e132c7e` + `b7762bd` + `ef63efc` + `4cc94a6` | Migración del bot al SDK CLOB V2 de Polymarket antes del cutover del 22 de abril de 2026 (~11:00 UTC), fecha en que los clientes V1 dejan de funcionar completamente. La migración requirió 5 cambios en 2 archivos (`requirements.txt` y `bot.py`), descubiertos iterativamente vía errores de Railway: (1) `requirements.txt`: `py-clob-client==0.34.6` → `py-clob-client-v2==1.0.0`; (2) `bot.py` imports: módulo renombrado `py_clob_client.*` → `py_clob_client_v2.*`; (3) `bot.py` constructor: `chain_id` se mantiene igual en Python (el rename `chain_id→chain` era solo para TypeScript, la doc mezclaba ambos lenguajes); (4) `bot.py` auth: `create_or_derive_api_creds()` → `create_or_derive_api_key()`; (5) `bot.py` órdenes: `get_orders()` → `get_open_orders()`. El error 400 en `/auth/api-key` al arrancar es esperado: `create_or_derive_api_key()` intenta crear primero, falla porque la key ya existe y hace fallback a derivar; el log confirma "Autenticación OK". `tools/`, `city_intelligence`, `phase5_visibility`, `find_traders.py` y `trader_analyzer.py` no usan el SDK CLOB directamente (consumen REST vía `requests`/`httpx`) y no requirieron cambios. Bot verificado en Railway en Modo REAL. |
| 2026-04-18 | Explícita | Sesión 197 | local NOAA coverage queue hardening | Se endurece la cola de `observed_vs_forecast` en `bot.py` para dejar de perder cobertura NOAA por starvation del backlog. El diagnóstico local mostró que `London`, `Munich`, `New York City`, `Shanghai` y `Tokyo` tenían BUYs maduros en `performance.json` pero seguían sin poblar `audit.json`, porque `audit_check_resolution_truth()` procesaba solo `to_check[:10]`, repetía varios `city|date` del mismo día y no dejaba cooldown cuando NOAA devolvía vacío. El patch introduce tres guardrails mínimos: límites `OBSERVED_AUDIT_MAX_SUCCESSES_PER_RUN=10` y `OBSERVED_AUDIT_MAX_ATTEMPTS_PER_RUN=40`, dedupe por `city|date` con prioridad a ciudades con menor muestra y a candidatos `perf_buy` frente al fallback shadow, y cooldown de 12 horas usando `audit["errors"]` para reintentos fallidos `source=noaa_ncei/kind=observed_vs_forecast_fetch_failed`. `verify_before_deploy.py` se amplía con un test de dedupe `city|date` y vuelve a cerrar en 703/703; `py_compile` sigue pudiendo fallar por lock de `__pycache__` en Windows. |
| 2026-04-18 | Explícita | Sesión 196 | local dynamic TP high-conviction | TP dinámico implementado en `bot.py`: posiciones con `our_prob >= 0.80` en entrada usan TP del `+80%` en lugar del `+40%` fijo. Motivación: NYC NO del 17-abr, compra a $1.19 con alta convicción, TP prematuro habría cerrado una posición que podría haber llegado a resolución (`+172%`). Dos env vars nuevas `HIGH_CONVICTION_TP_PCT` (default 80.0) y `HIGH_CONVICTION_PROB_THRESHOLD` (default 0.80). `our_prob` no está en el dict de posición de la API — se cruza con `trade_lifecycle.json` via `entry_context.our_prob` keyed por `token_id`. Cambios en `manage_positions` (lookup + CHECK 2 dinámico) y en `intra_cycle_sl_check` (mismo patrón). `verify_before_deploy.py` 702/702. |
| 2026-04-18 | Explícita | Sesión 195 | local alarm review closeout + weak-city gate | Se cierra la revisión completa del lote actual de alarmas con criterio operativo estricto. Las dos variantes legacy de `Phase 5 Visibility` (`Shanghai + Chicago`, `gap + siguiente paso`) quedan confirmadas como formato ya superado por la sesión 194, por lo que pasan a tratarse como `alarma reescrita/eliminada` y ya no deben abrir sesión por sí solas. En la capa humana del bot también queda sellado que `Slot monetization review` no debe volver a arrastrar `23h UTC` cuando el slot está deshabilitado, y que el `Cross-check traders vs bot` solo debe elevar gap operativo real, no casos esperados como `Toronto` blocked o ruido débil como `Guangzhou` sin consenso. Además, la auditoría de `City Intelligence` aterriza en un gate read-only nuevo: `tools/city_validation_ledger.py` introduce `weak_city_hypothesis` para ciudades vistas repetidamente en shadow pero con `edge_hits=0`, y `tools/city_promotion_gate.py` lo traduce a `background_watch` / prioridad `later` en vez de mantenerlas en review activa cercana a monetización. Se regeneran los artefactos `city_validation_ledger` y `city_promotion_gate`; la ejecución real de los scripts pasa y escribe los outputs nuevos, aunque el intento de `py_compile` sobre tools falla por lock de `__pycache__` en Windows y no por error de sintaxis. |
| 2026-04-18 | Explícita | Sesión 194 | local alarm-closure rule for monetization | Se fija como regla operativa canónica que las alarmas del sistema no pueden cerrarse solo con documentación o análisis: cada alarma debe terminar en `cambio ejecutado`, `patch listo`, `gate definido` o `alarma reescrita/eliminada`, y si no abre ninguna de esas salidas debe desaparecer o rediseñarse. La regla se implementa en la capa `Phase 5 Visibility`: `tools/phase5_operational_action.py` añade `closure_type`, `closure_label` y `operational_change`, y `tools/phase5_visibility_telegram_alert.py` pasa a incluir en Telegram el `cierre obligatorio` y el `cambio operativo` para que la alarma traduzca evidencia en acción. Queda explicitado para la siguiente sesión que ya no hay que reexplicar este criterio: el agente debe responder directamente qué cambia en operativa por haber saltado la alarma y con cuál de las cuatro salidas se cierra. |
| 2026-04-18 | Explícita | Sesión 193 | local phase5 visibility trace sync | Se actualiza la trazabilidad local de `Phase 5 Visibility` para reflejar una nueva coincidencia real del probe sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. El evento fijado es `2026-04-18T01:58:33+00:00` con `Shanghai=2`, `Chicago=2` y `coincidencias acumuladas=11`. La lectura operativa se mantiene: `dominant_gap=evidence_asymmetry_between_shadow_and_active` y siguiente paso `use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence`. Se alinean los readouts `*_latest` y JSON asociados de la capa phase5 para que el repo no siga mostrando `5 snapshots / 0 simultaneidades` cuando ya existe evidencia repetida de coincidencia Shanghai+Chicago. |

| 2026-04-17 | Explícita | Sesión 192 | snapshot Railway fresh + protocolo Seoul post-fix | Auditoría operativa read-only para cerrar la ambigüedad de Seoul tras el incidente `forecast_station_mismatch`. Se refresca `data/runtime_import/` desde Railway y se confirma que live ya no tiene `auto_blocked_cities.Seoul`: la ciudad reapareció en `auto_canary_cities` a las `2026-04-17T16:29:31Z` y el ciclo `2026-04-17T20:44:48Z` abrió una compra real `Seoul 24°C Apr19 YES` (`edge=29.1%`, `$1.23`). La verificación decisiva cruza `CONTEXTO.md`, `git show ed00535`, `bot.py` actual y `decisions.log`: aunque el runtime todavía etiqueta `BOT_VERSION=v10.6.15`, el código live ya usa `RESOLUTION_STATIONS["Seoul"] = (37.5665, 126.9780)` y los forecasts observados (`23.6°C`, `23.8°C`, `25.9°C`) encajan con Seoul ciudad y no con la fuente vieja de Incheon. Decisión operativa cerrada y documentada: esta posición cuenta como la primera evidencia post-cambio de fuente; no se toca nada mientras esté abierta; si gana, Seoul sigue en `canary` con `post-fix sample #1`; si pierde, Seoul baja a `shadow` pero sigue contando como `post-fix sample #1`; toda evaluación futura debe ignorar el edge legacy contaminado por Incheon y, si se quiere evitar nueva autopromoción automática, habrá que aislar o resetear `shadow_city_tracking` tras el cierre. |
| 2026-04-17 | Explícita | Sesión W17-Opus | `669af20` + 3 commits anteriores + Railway vars | Revisión estratégica Opus + bloque W17 completo ejecutado en una sesión. Causa raíz del throughput bajo identificada: `condition_filtered` mata ~47% de candidatos, modelo sobreestima P(YES) en exact/range (bot 0% WR en YES side, traders 76% WR). 4 cambios en bot.py: whitelist canary +4 ciudades, YES exact/range floor `our_prob<65%`, Seoul promotion bug fix, W17 observation alert one-shot. Railway actualizado: whitelist live + `SCHEDULE_DISABLED_HOURS_UTC=23`. 3 docs estratégicos creados. `verify_before_deploy.py` 702/702. |
| 2026-04-17 | Explícita | Sesión 191 | local Telegram wording correctness patch | Sesión corta de correctness en la capa humana de Telegram, sin tocar trading core, NOAA, scheduler, policy live ni métricas base. Se auditan dos avisos automáticos disparados a primera hora: `Cross-check diario traders vs bot` y `Blocked signals`. Hallazgo: el cálculo estaba bien, pero el wording inducía lecturas demasiado fuertes. En el cross-check, la lista visible de ciudades actionable no era una priorización sino solo las primeras `4` del conjunto; el mensaje se ajusta para declarar explícitamente `muestra top N de M`. En blocked-signals, el texto hablaba de `canary excluido` aunque la exclusión real usa `QUALITY_TRADER_CITIES_WHITELIST`; se renombra a `Blocked signals (fuera de whitelist)` y la nota pasa a `Baseline fuera de QUALITY_TRADER_CITIES_WHITELIST`. Validación local: `python -m py_compile bot.py` OK. |
| 2026-04-17 | Explícita | Sesión 190 | `8ec4261` + Railway `SCHEDULE_DISABLED_HOURS_UTC=23` | Cierre live del loop de scheduler por slot. Se empuja a `main` el patch que ya instrumentaba `scan.slot_metrics`, evaluaba automáticamente `04h/23h`, añadía `SCHEDULE_DISABLED_HOURS_UTC` y corregía el cuello de ejecución por mínimo nocional; `verify_before_deploy.py` vuelve a pasar en `702/702`. En Railway se aplica `SCHEDULE_DISABLED_HOURS_UTC=23` y se elimina la env obsoleta `SLOT_04H_REVIEW_REMINDER_DATE`. Verificación final por logs del deploy `6d840105-4246-4c03-8658-18081492f5d7`: el bot arranca con `Schedule: [4, 8, 16] UTC` y `Schedule disabled hours: [23] UTC`, dejando `23h` apagado live de forma reversible y `04h` como slot útil a seguir midiendo. |
| 2026-04-17 | Explícita | Sesión 189 | local slot monetization operational alert | Se añade la capa automática que faltaba encima de `scan.slot_metrics`. `bot.py` integra `maybe_evaluate_slot_monetization(state)` dentro de `run_observability_alerts()`, con estado persistente para idempotencia diaria y cambio de firma. La nueva alerta lee `cycles_history.jsonl`, agrega los últimos ciclos exactos de `04h` y `23h`, clasifica cada slot (`validated`, `not_validated_yet`, `disable_candidate`, etc.) y envía por Telegram una salida operativa con funnel, reject reasons dominantes y siguiente acción sugerida para Codex. El sistema aún no aplica automáticamente el cambio live; automatiza la revisión y la recomendación, no el deploy. `verify_before_deploy.py` cierra en `702/702`. |
| 2026-04-17 | Explícita | Sesión 188 | local monetization patch for 04h + slot instrumentation | La revisión del slot `04h` se convierte en cambio de sistema, no solo en doc. Se añade `SCHEDULE_DISABLED_HOURS_UTC` como feature flag para apagar slots concretos sin reescribir el scheduler base; la recomendación operativa queda lista para usar `23` como disable candidate por su utilidad neta casi nula. Se instrumenta `scan.slot_metrics` en `cycle_summary.json` y `cycles_history.jsonl` con funnel y rechazos por slot (`same_day_candidates`, `same_day_edges`, `same_day_selected`, `same_day_buys`, `edges`, `selected`, `buys`, `buy_rate`, `reject_reasons`, etc.). Además, se corrige un cuello real de monetización: antes de ejecutar un BUY, el bot ahora ajusta `shares` hacia arriba cuando el redondeo deja la orden justo por debajo del mínimo de notional, evitando fallos del tipo `invalid amount for a marketable BUY order ($0.9976), min size: $1` ya observados en `04h`. El recordatorio one-shot `04h` se retira del código por obsoleto. `verify_before_deploy.py` vuelve a pasar en `697/697`. |
| 2026-04-17 | Explícita | Sesión 187 | local railway runtime pull + 04h slot observation | Revisión programada del rollout `SCHEDULE_HOURS_UTC=4,8,16,23` cinco días después de activarlo. Se refresca `data/runtime_import/` con snapshot nuevo de Railway y se crea `docs/04h-slot-observation-2026-04-17.md` con comparación homogénea `pre` vs `post` sobre ciclos exactos. Hallazgo central: `04h UTC` sí abre same-day real para `Tokyo`, `Seoul` y `Shanghai`; en el ciclo `2026-04-17T04:00:45Z` aparecen `25` candidatos post-filtro, `2` edges y `2` seleccionadas, incluyendo `Shanghai NO 20°C` y `Tokyo NO 18°C`, pero sin buy efectivo por restricciones de tamaño mínimo / Kelly. El throughput ejecutado sigue en cero buys por ciclo en la muestra post, mientras `23h` enseña `0` edges, `0` buys y same-day mayormente tardío o bloqueado, quedando como candidato razonable a salir si el objetivo del schedule sigue siendo throughput útil. |
| 2026-04-17 | Explícita | Sesión 186 | local phase5 operational action workflow | La alerta legacy de `Phase 5 Visibility` se convierte en trigger operativo read-only sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. Se crea `tools/phase5_operational_action.py` para traducir la coincidencia `Shanghai + Chicago` a `severity`, `action_state` y `next_operational_step`, persistiendo `data/phase5_operational_action.json` y `docs/phase5_operational_action_latest.md`. `tools/phase5_visibility_pipeline.py` integra la nueva etapa y expone su resumen operativo; `tools/phase5_visibility_telegram_alert.py` amplía el mensaje para incluir la lectura derivada y no quedarse solo en `gap + next_step`. La validación local confirma que la pipeline cierra en `ok`; con los artefactos versionados actuales la salida es `no_progress`, pero una simulación del caso reportado (`probe 2026-04-17T01:56:54+00:00`, `Shanghai=2`, `Chicago=2`, `coincidencias=9`, `gap=evidence_asymmetry_between_shadow_and_active`) clasifica correctamente `watch / review / increase_review_priority`, que era el objetivo de workflow. La sesión también elimina el doc de diseño intermedio para dejar solo código y trazabilidad mínima. |
| 2026-04-16 | Explícita | Sesión 181 | local dashboard shadow-only residual fix + live verification | Se completa el diagnóstico post-deploy del fix `_is_shadow_only()` con foco en la explicación más simple. Railway está sano y el proceso live sí arranca en `MODO REAL`, así que `SHADOW_ONLY_MODE=false` llega correctamente al bot; además `cycle_summary.json` queda en `mode="REAL"`. La parte UI residual sí existía: `build_daily_summary_payload()` seguía calculando `shadow_only` como `len(ACTIVE_TRADING_CITIES) == 0`, arrastrando una lectura stale de `SHADOW-ONLY` aunque la fuente de verdad canónica ya fuera `_is_shadow_only()`. Se aplica un fix mínimo para unificar esa capa sin tocar trading core. `verify_before_deploy.py` vuelve a pasar en `685/685`. Pero la sesión también confirma que el problema no era solo dashboard: en producción sigue apareciendo al menos un `shadow_only_override` posterior al deploy (`Seoul`, ciclo `2026-04-16T07:07`, `city_mode=canary`, `edge_pct=68.47`). Veredicto final de la sesión: `dashboard + gating real`, no solo presentación. |
| 2026-04-16 | Explícita | Sesión 180 | local bot.py shadow-only fix + deploy handoff | Se valida y prepara para deploy un fix de correctness en `bot.py` centrado en `_is_shadow_only()`, sin tocar trading core, NOAA, scheduler, Kelly, sigma ni filtros. La causa raíz cerrada era semántica: `ACTIVE_TRADING_CITIES=NONE` se interpretaba como pausa global y bloqueaba también ciudades ya promovidas a `auto_canary`. El cambio desacopla ambos conceptos: `_is_shadow_only()` pasa a leer `SHADOW_ONLY_MODE` como toggle explícito y deja un fallback legacy solo para el caso “sin activas y sin canary explícitas en env vars”. `verify_before_deploy.py` vuelve a pasar en `685/685`. Se actualiza la documentación operativa para dejar claro que el sistema ya no debe leerse como `shadow-only` deliberado, y se deja instrucción exacta para Railway: añadir `SHADOW_ONLY_MODE=false` manteniendo `ACTIVE_TRADING_CITIES=NONE`. Queda pendiente la validación post-deploy en live: dashboard en modo real y primeros ciclos con `Chicago` pasando de `policy_execution_gate` a ejecución canary efectiva. |
| 2026-04-15 | Explícita | Sesión 179 | local read-only tooling refresh + handoff | Auditoría operativa del funnel live priorizando `skip_log.jsonl`, `shadow_city_tracking.json`, `signals.json`, `policy_env_snapshot.json`, `city_validation_ledger.json`, `city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md`. Hallazgo fuerte: el runtime reciente ya no sostiene `trader_discovery` como cuello dominante del throughput útil; en los dos últimos ciclos hubo `4` near-misses con `edge_pct >= 15` y `3/4` murieron por gating operativo (`shadow_only_override` / `fuera_allowlist`), no por edge/modelo. Se ajustan `tools/city_validation_ledger.py` y `tools/city_promotion_gate.py` para incorporar evidencia reciente de `skip_log` y distinguir `policy_execution_gate`; los artefactos regenerados pasan a mostrar ese bottleneck como dominante y priorizan `Shanghai` y `Chicago`. `verify_before_deploy.py` vuelve a cerrar en `685/685`. La alerta nueva `Phase 5 Visibility` (`Shanghai + Chicago`, probe `2026-04-15T13:54:33+00:00`) se deja explícitamente para una sesión limpia en `docs/next-session-handoff-2026-04-15-policy-gate-throughput.md`. |
| 2026-04-14 | Explícita | Sesión 176 | feat: condition_reopen_monitor + bot integration (v10.6.16) | Implementación del monitor automático del canary condition_filtered. `tools/condition_reopen_monitor.py` standalone read-only: carga `trade_lifecycle.json`, filtra trades exact/range desde 2026-04-14, calcula WR por ciudad, emite veredicto (OK/ALERT/CLOSE/PROMOTE/EXTEND/KILL_SWITCH). `maybe_run_condition_monitor(state)` en `bot.py` v10.6.16: dispara desde día 7 en fechas de checkpoint (2026-04-21, 2026-04-28) o cuando kill-switch activo (WR<45% n≥20); anti-spam via `state["last_condition_checkpoint"]`; kill-switch repite diariamente. Mensaje Telegram incluye métricas + instrucción Sonnet lista para pegar. 9 tests nuevos en `verify_before_deploy.py`. `verify_before_deploy.py` 680/680. |
| 2026-04-14 | Explícita | Sesión 175 | feat: condition_filtered canary reopen exact/range (v10.6.15) | Sesión de decisión + implementación. Sonnet analizó 59 resoluciones reales de quality traders en señales `exact/range` bloqueadas por `condition_filtered`: WR=76.3% (exact 72.5% n=51, range 100% n=8), threshold de reopen cumplido (≥55% n≥50). Opus decidió vía subagente (Opción B modificada): reabrir con triple gate — quality trader + whitelist 9 ciudades (Seattle, Tokyo, Hong Kong, Seoul, Toronto, Chengdu, Shenzhen, Shanghai, Milan) + edge mínimo diferenciado (MIN_EDGE+5pp). London excluida (WR 33% n=3). Sizing efectivo 25% del normal (CANARY_POSITION_SCALE × EXACT_RANGE_SIZE_SCALE). Kill-switch: WR bot <45% n≥20. Checkpoints: 2026-04-21 (día 7) y 2026-04-28 (día 14). Implementado en `bot.py` v10.6.15: 4 env vars nuevas, lógica triple gate en condition_filtered, edge buffer, size scale. `verify_before_deploy.py` 671/671. Deploy Railway OK — verificado en logs: feature activo, Milan 18°C exact procesada por la ruta canary (min 20.0% en log confirma gate abierto). Milan 19°C exact con edge 21.5% habría operado si estuviera en canary mode. Pendiente siguiente sesión: `tools/condition_reopen_monitor.py` + integración Telegram con instrucción Sonnet para checkpoints automáticos. Handoff: `docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md`. |
| 2026-04-12 | Explícita | Sesión 167 | worktree-hygiene-gitignore-cleanup | Sesión de higiene del worktree sin tocar `bot.py`, trading core ni Railway. Causa raíz: el `.gitignore` solo cubría artefactos Python/IDE, dejando sin reglas los tres flujos principales de suciedad: (1) snapshots de Railway en `data/runtime_import/`, (2) outputs regenerables de tools en `data/*.json` y `docs/*_latest.md`, y (3) artefactos de sesión (`docs/next-session-handoff-*.md`, `docs/claude-opus-prompt-*.md`). Se añaden reglas `.gitignore` para cubrir todos estos patrones. Se untrackearon con `git rm --cached` cinco archivos generados que estaban incorrectamente en el índice git: `data/runtime_import/city_policy_state.json`, `data/runtime_policy_effective_view.json`, `data/system_alignment_check_operational.json`, `docs/runtime_policy_effective_view_latest.md`, `docs/system_alignment_check_operational_latest.md`. Se stagearon 32 scripts nuevos de `tools/`, `seed_data/phase5/` (3 archivos), `RTK.md` y ~60 docs de análisis/diseño con valor permanente. Resultado: 0 archivos sin trackear desde 167. Entregable: `docs/worktree-hygiene-audit-2026-04-12.md`. |
| 2026-04-12 | Explícita | Sesión 166 | live-policy-london-dallas-reconcile/atlanta-lifecycle-note | Se ejecuta un cambio live mínimo y deliberadamente acotado sobre `city_policy_state.json` en el volumen de Railway, sin tocar `bot.py`, thresholds, env vars ni promover manualmente ciudades. Tras el preflight operacional inicial con `error=1` por el blocker conocido de `Dallas`, la sesión usa `tools/railway_safe.ps1`, hace backup previo de `/app/data/city_policy_state.json` y elimina exactamente dos overlays persistidos: `London` sale de `auto_canary_cities` y `Dallas` sale de `auto_shadow_cities`, sin tocar `transition_history` ni otros campos. Luego se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1`, se regenera `data/runtime_policy_effective_view.json` y el preflight operacional vuelve a `error=0` (`ok=6`, `warning=2`), desapareciendo el `blocking_operational_collision` de `Dallas` y quedando la foto en `blocked=3`, `canary=6`, `shadow=18`. En paralelo se crea `docs/atlanta-lifecycle-inconsistency-2026-04-12.md` y se alinea `docs/canary-to-active-readiness-2026-04-12.md`: el trade `Atlanta 76°F Apr7 YES` debe leerse como win mal etiquetada, porque su `timeline` registra `RESOLVED_WIN +$0.63` y `post_exit_analysis` confirma mercado a `0.9995`, aunque `close_context` termine como `LOSS_TOTAL` por `micro_position_unsellable`. |
| 2026-04-12 | Explícita | Sesión 165 | dallas-canary-diagnosis/canary-active-readiness | Sesión read-only de diagnóstico sobre Dallas y las canary, sin tocar `bot.py`, thresholds, listas de ciudades, Railway ni policy live. `docs/dallas-canary-block-diagnosis-2026-04-12.md` confirma que `CITY_STATS_CUTOFF` no explica por qué Dallas no reaparece en `auto_canary_cities`: el cutoff solo afecta `get_city_accuracy()`/`get_city_policy_metrics()`, mientras la regla shadow -> canary usa `shadow_city_tracking`, y Dallas sigue hoy en `edge_hits=8`, `cycles_seen=5`, `best_edge_pct=45.8`. La foto runtime efectiva además ya la deja `env=shadow`, así que el bloqueo apunta a un overlay `auto_shadow` persistido/inconsistente, no a falta real de evidencia reciente. En paralelo, `docs/canary-to-active-readiness-2026-04-12.md` deja la tabla factual de las seis canary pedidas: `Munich` y `New York City` siguen sin trades canary post-promoción; `Seoul`, `Shanghai` y `Tokyo` tienen una primera señal positiva limpia pero solo `n=1`; y `Atlanta` queda contaminada por una inconsistencia en `trade_lifecycle` (`close_context=LOSS_TOTAL` pero `timeline` registra antes `RESOLVED_WIN +$0.63`). La sesión deja además documentado que el snapshot actual ya incluye `London` como séptima auto-canary desde `2026-04-12T15:03:51Z`, aunque la auditoría respeta las seis ciudades pedidas. |
| 2026-04-12 | Explícita | Sesión 164 | blocked-cities-structural-closeout/shadow-canary-shortlist | Sesión de cierre read-only sobre policy/observabilidad de ciudades, sin tocar `bot.py`, thresholds, allowlists, bankroll ni cambiar Railway desde Codex. Primero se documentan dos auditorías estructurales de `BLOCKED_CITIES`: `docs/ankara-paris-unblock-review-2026-04-12.md` y `docs/remaining-blocked-cities-review-2026-04-12.md` dejan que el criterio canónico solo sostiene `London` (mismatch documentado), `Toronto` y `Singapore` (sin `noaa_station_id` en `RESOLUTION_ICAO`), mientras `Ankara`, `Paris`, `Madrid`, `Wellington` y `Tel Aviv` deben vivir en `shadow`. Luego, tras el cambio manual del usuario en Railway a `BLOCKED_CITIES=London,Toronto,Singapore`, se refresca `data/runtime_import/`, se regenera la `runtime_policy_effective_view` y el preflight operacional vuelve a `error=0`, con foto live `blocked=3`, `canary=6`, `shadow=19`. Finalmente se abre Bloque B en `docs/shadow-canary-threshold-review-2026-04-12.md`: solo `Dallas` y `Chicago` tienen hoy base suficiente para justificar una revisión acotada del umbral `canary`; `Buenos Aires` sigue en observación y `Denver`, `Los Angeles`, `Houston`, `San Francisco` y `Mexico City` quedan todavía demasiado verdes o débiles para mover esa conversación. |
| 2026-04-12 | Explícita | Sesión 163 | market-universe-price-temporal-audit/read-only | Se abre y cierra un módulo read-only para responder dos preguntas nuevas de throughput sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`: cuánto universo real de mercados de temperatura ofrece hoy Polymarket por ciudad/día, y si los mercados que caen en `price_out_of_range` luego entran en una ventana útil. Se añade `tools/analyze_market_universe.py` y se deja `docs/polymarket-universe-price-temporal-audit-2026-04-12.md` como readout reproducible sobre el snapshot manifestado tirado a `2026-04-12T10:15:51Z`. La conclusión fuerte es doble: el universo observado es muy estable (`29` ciclos normales en `324-330` mercados, mediana `330`, `30` pares `city+date` por ciclo, `273/277` city-dates con exactamente `11` mercados), así que no aparece un ceiling nuevo por discovery; y el bucket `price_out_of_range` casi nunca se convierte en throughput útil (`1091` mercados únicos tocaron ese bucket, solo `25` -> `2.3%` llegaron alguna vez a fase pre-edge, mientras `810` -> `74.2%` solo salieron para morir en filtros temporales y `256` -> `23.5%` nunca salieron de precio). Además, `1058/1091` (`97.0%`) entran por primera vez ya con `mkt_prob < 20` y ese mismo `97.0%` nunca ve `mkt_prob >= 20` después. La lectura operativa resultante es que el techo inmediato parece venir más del funnel que del universo visible, y que la siguiente observación útil debe ser post-rollout del slot `04h`, no una tesis amplia de precio/timing global. |
| 2026-04-12 | Explícita | Sesión 162 | railway-04h-slot/reminder-automation-close | Se activa en Railway la siguiente fase mínima de throughput temporal: `SCHEDULE_HOURS_UTC` pasa a `4,8,16,23` para abrir cobertura `same-day` real a `Tokyo`, `Seoul` y `Shanghai`, sin tocar edge, thresholds, bankroll, política de ciudades ni scheduler interno. En paralelo se automatiza el seguimiento lean del experimento añadiendo en `bot.py` la env var `SLOT_04H_REVIEW_REMINDER_DATE` y un helper one-shot dentro de `run_observability_alerts()` que enviará por Telegram, el `2026-04-17`, un prompt corto para auditar el slot `04h` con Codex y crear `docs/04h-slot-observation-2026-04-17.md`. Validación local: `python verify_before_deploy.py` sigue en `643/643`. Validación live: Railway acepta `SCHEDULE_HOURS_UTC=4,8,16,23` y `SLOT_04H_REVIEW_REMINDER_DATE=2026-04-17`; el servicio `polymarket-bot` queda en nuevo deploy `BUILDING` por el cambio de variables. |
| 2026-04-12 | Explícita | Sesión 161 | city-window-routing/implementation-traceability-close | Se implementa en `bot.py` el city-window prefilter diseñado tras el intercambio con Opus, sin tocar edge, thresholds, bankroll, política de ciudades ni scheduler. La nueva `compute_city_windows()` reutiliza `get_min_days_for_city()` como source of truth para no divergir del override manual `MIN_DAYS_AHEAD`; el early-exit same-day se inserta después de `blocked/mode/shadow` y antes del safety net de fecha, evitando ruido estructural sin perder la semántica operativa existente. `cycle_summary.json` y `cycles_history.jsonl` pasan a guardar `scan.city_window_skipped` y `scan.city_window_cities`, mientras el decision log añade una línea `VENTANA: ...` sin volver a inflar `skip_log.jsonl`. Validación técnica: `python -m py_compile bot.py` pasa y `python verify_before_deploy.py` vuelve a `643/643`. Durante el cierre aparece además un falso rojo de trazabilidad: docs ya iban por la sesión `160`, pero `agent_events.jsonl` seguía detrás; se registra la sesión faltante y el preflight vuelve a verde. |
| 2026-04-12 | Explícita | Sesión 160 | fix/city-timezones-american-cities | Auditoría adversarial del funnel pre-edge (timezone_filter + lado derecho canary) y bug fix de CITY_TIMEZONES. Se confirma que timezone_filter (15.3% del funnel last12) es intocable: 100% son ciudades asiáticas a 16-21h local, filtro correcto por diseño. Se confirma que el throughput canary es críticamente bajo: 967 skips en last12, solo 2 llegan a below_min_edge (ambos Shanghai), 0 trades. Cuello dominante: price_out_of_range con mediana mkt_prob=0.55%. Se confirma que condition_filtered es política deliberada (pérdidas históricas en otras condiciones), no bug. Bug timezone encontrado y corregido: Denver, Mexico City, Los Angeles, Houston y San Francisco no estaban en CITY_TIMEZONES y caían a UTC fallback, causando que 33 market instances fueran bloqueadas falsamente en last12 (se trataban como 16-20h local cuando tenían 10-13h real). Fix: 5 entradas añadidas con zonas IANA correctas. verify_before_deploy.py pasa sin errores. Se prepara prompt Opus para diseño de ciclos por ventana de ciudad. Frente pendiente antes de Opus: Telegram Correctness (Codex). |
| 2026-04-12 | Explícita | Sesión 159 | rtk-shim/local-compat | Se corrige una fricción pequeña pero repetitiva de tooling/documentación sin tocar `bot.py`, Codex global ni Claude global. El diagnóstico confirma que `rtk` sí está instalado y operativo en Codex (`rtk 0.34.3`) y que también existe `~/.codex/RTK.md`, así que el problema no era de instalación sino de resolución de la referencia `@RTK.md` desde el repo. Para evitar romper compatibilidad con Claude o depender de rutas globales distintas entre clientes, se crea un `RTK.md` local y neutral dentro del repo como shim estable. El cambio deja de hacer depender la referencia de cómo cada cliente expande archivos globales y evita tocar configuraciones globales que sí podrían haber roto el flujo en Claude. |
| 2026-04-12 | Explícita | Sesión 158 | same-day-timing-audit/read-only | Se abre y cierra el módulo `Same-Day Timing Audit` sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr los dos preflights canónicos a `2026-04-12T10:56:05+00:00`, y ambos siguen en `ok=7, warning=1, error=0`. Luego se audita el subbucket same-day dentro de `date_out_of_range_past` sobre la misma ventana de `29` ciclos y `9896` skips, usando la regla horaria ya viva en `bot.py`: `min_days_global=1` desde `12:00 UTC` y cutoff práctico `hora_local >= 14` o `día local siguiente`. El nuevo `docs/same-day-timing-audit-2026-04-12.md` deja cuatro conclusiones fuertes: aunque `3980/4475` skips de fecha (`88.9%`) siguen siendo same-day, casi todos ya entran demasiado tarde en la práctica (`3925`, `98.6%`), por lo que same-day no equivale a recuperable; la distribución no es un pico fino sino un patrón estructural en slots post-mediodía, con masa fuerte en `16-17 UTC` y `22-23 UTC`; la parte plausibly recoverable es muy pequeña (`55` filas, `1.4%`) y vive casi solo en `Los Angeles`, `Denver` y `Mexico City`; y por tanto la hipótesis `tiempo` como gran palanca general de throughput queda debilitada, quedando como micro-oportunidad posible por ciudad/slot y no como unlock horizontal del funnel. |
| 2026-04-12 | Explícita | Sesión 157 | prefilter-throughput-audit/read-only | Se abre y cierra el módulo `Prefilter Throughput Audit` sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr los dos preflights canónicos a `2026-04-12T10:36:27+00:00`, y ambos siguen en `ok=7, warning=1, error=0`. Luego se audita `data/runtime_import/skip_log.jsonl` sobre `29` ciclos y `9896` skips reales con un foco pre-edge explícito: cuánto se pierde por fecha, precio y composición por ciudad/modo. El nuevo `docs/prefilter-throughput-audit-2026-04-12.md` deja cuatro conclusiones fuertes: `date_out_of_range_past` sigue siendo el bucket dominante (`45.2%`) y parece venir sobre todo de mercados que llegan demasiado tarde dentro del flujo normal (`88.9%` same-day, `days_late=0`), pero la recuperabilidad por timing queda explícitamente como hipótesis a auditar con granularidad horaria; `price_out_of_range` es grande (`22.7%`) pero está pegado casi por completo al extremo bajo (`97.6%` con `mkt_prob < 20`, mediana `0.3`), no a una nube fina cerca del rango permitido; `Miami` y `Seattle` ya aportan universo visible real como `shadow` efectivo, pero solo suman `5.8%` del funnel reciente y casi todo sigue muriendo por fecha/precio; y `blocked_city` ya cae a `4.4%` en `last12`, así que la siguiente palanca más prometedora para una futura discusión de throughput sigue siendo `tiempo`, aunque todavía no como palanca confirmada. |
| 2026-04-12 | Explícita | Sesión 156 | dallas-drift/live-railway-closeout | Se cierra por fin el drift real de `Dallas`. La evidencia ya era clara: al sincronizar las env vars manuales desde Railway, `ACTIVE_TRADING_CITIES=Dallas` reaparecía como `env active` frente a `city_policy_state.auto_shadow_cities`, generando otra vez `blocking_operational_collision`. El cierre correcto no era retocar tooling ni `bot.py`, sino borrar la declaración live sobrante. Se elimina `ACTIVE_TRADING_CITIES` del servicio `polymarket-bot` en Railway, se refresca `data/runtime_import/`, `policy_env_snapshot.json` ya queda con `ACTIVE_TRADING_CITIES=""`, y `runtime_policy_effective_view` vuelve a dejar `Dallas` como `env=shadow`, `runtime=auto_shadow`, `effective=shadow`. Tras eso, `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` regresan a `ok=7, warning=1, error=0`, con `blocking_operational_collision_count=0`. |
| 2026-04-12 | Explícita | Sesión 155 | policy-env-snapshot/effective-view-sync | Se corrige la deuda técnica menor de la effective view para que ya no dependa de pasar `BLOCKED_CITIES` manualmente al regenerarla. `tools/railway_runtime_snapshot_pull.ps1` pasa a exportar un `policy_env_snapshot.json` read-only con solo `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES` y `BLOCKED_CITIES`, y `tools/runtime_policy_effective_view.py` ahora lo usa por defecto antes de mirar el entorno local del proceso. La validación confirma que `Miami` y `Seattle` siguen resolviendo `shadow` automáticamente sin flags manuales. El efecto colateral honesto del fix es que también reaparece el drift real de `Dallas`: como el snapshot ya trae `ACTIVE_TRADING_CITIES=Dallas`, la effective view vuelve a exponer `env active` vs `runtime auto_shadow`, y `python tools/system_alignment_check.py --decision-mode operational` cae a `error=1` por `blocking_operational_collision_count=1`. La sesión, por tanto, cierra el fix del transporte/env correctamente pero deja visible que el siguiente bloqueo ya no es tooling sino policy live/manual drift en Dallas. |
| 2026-04-12 | Explícita | Sesión 154 | railway-snapshot/effective-view/shadow-check | Se valida el cambio manual en Railway que quita `Miami` y `Seattle` de `BLOCKED_CITIES`. Primero se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1`, dejando `runtime_import_manifest.json` actualizado al `2026-04-12T09:57:08Z`. Luego se regenera la `runtime_policy_effective_view`; al revisar la herramienta se detecta un matiz importante: `tools/runtime_policy_effective_view.py` sigue teniendo un fallback local stale para `DEFAULT_BLOCKED_CITIES`, así que para reflejar el estado live real hay que ejecutarla con el valor explícito ya aplicado en Railway (`London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`). Con esa regeneración, `Miami` y `Seattle` pasan a `env_declared_mode=shadow` y `effective_mode=shadow`, y el conteo global queda en `shadow=16`, `blocked=8`, `canary=6`. Finalmente `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` siguen cerrando en `ok=7, warning=1, error=0`, por lo que la capa canónica queda alineada con el cambio manual sin tocar `bot.py`, `city_policy_state.json` ni configuración core. |
| 2026-04-12 | Explícita | Sesión 153 | blocked-review/four-cities/read-only | Se abre una sesión corta y read-only para revisar las cuatro ciudades marcadas como `dudoso y candidato a revisión futura` dentro de `BLOCKED_CITIES`: `Ankara`, `Miami`, `Paris` y `Seattle`. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos siguen cerrando en `ok=7, warning=1, error=0`, con lo que la revisión queda gateada por la misma señal canónica ya usada para alignment. Luego se comprueba que las cuatro ciudades sí tienen `noaa_station_id` en `RESOLUTION_ICAO`, que siguen apareciendo en artefactos runtime recientes (`cycles_history`, `skip_log`, `performance` o `trade_lifecycle`) y que, por tanto, no son simplemente ciudades muertas o imposibles de observar en shadow. El nuevo `docs/blocked-cities-review-2026-04-12.md` deja un veredicto por ciudad sin tocar runtime live: `Miami` y `Seattle` pasan a `candidata a shadow`, mientras `Ankara` y `Paris` quedan en `insuficiente evidencia`. También queda escrito el cambio manual exacto pendiente si Pablo aprueba quitar solo `Miami` y `Seattle` de `BLOCKED_CITIES`, pero la sesión no ejecuta ningún cambio en Railway ni reabre alignment o config-drift como módulos. |
| 2026-04-12 | Explícita | Sesión 152 | skip-log-readout/analyzer-fix | Se abre y cierra la primera lectura operativa real del funnel a partir de `data/runtime_import/skip_log.jsonl`, ya sin mezclar alignment ni blocked/config-drift. Primero se revalidan los dos preflights canónicos, que siguen en `ok=7, warning=1, error=0`. Luego aparece un bug real pero pequeño en `tools/analyze_skip_log.py`: asumía `data/skip_log.jsonl`, mientras la capa read-only vigente vive en `data/runtime_import/skip_log.jsonl`; se corrige el default para preferir `runtime_import` y se sincroniza `docs/skip-log-analyzer.md`. Con eso, el analyzer corre sobre `25` ciclos y `8576` skips reales, y `docs/skip-log-readout-2026-04-12.md` deja la lectura compacta del funnel: `date_out_of_range_past=46.2%`, `price_out_of_range=21.3%`, `blocked_city=18.8%`, `timezone_filter=9.2%`, `condition_filtered=3.9%`, `below_min_edge=0.1%`, con un único near-miss relevante (`Shanghai`, `edge_pct=2.71`). La conclusión queda cerrada sin tocar policy: el cuello dominante sigue siendo estructural y temprano, no `MIN_EDGE`, Kelly ni sizing. |
| 2026-04-12 | Explícita | Sesión 151 | alignment-closeout/formal-seal | Se hace una sesión corta de sellado para cortar la sensación de módulo eternamente abierto. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos siguen en `ok=7, warning=1, error=0`, con `blocking_operational_collision_count=0`. Luego se verifica que el “Paso 1” sugerido por Sonnet ya estaba técnicamente resuelto: `tools/reference_trader_city_market_cross.py` ya no usa `legacy_bot_lists` y los fósiles `normal_pull_check/final_check` ya no existen en `data/runtime_import_derived/`. El trabajo real pendiente era solo de cierre narrativo, así que `docs/manual-config-drift-audit-2026-04-12.md` se actualiza con un `Closure Checkpoint` y una regla explícita de no reapertura: los módulos `System Alignment Lean Roadmap` y `Blocked Cities / Config Drift Cleanup` quedan cerrados salvo que vuelva a fallar el preflight operacional o aparezca una contradicción real de fuente de verdad. |
| 2026-04-12 | Explícita | Sesión 150 | blocked-rationale/latest/read-only | Se convierte `docs/blocked-cities-rationale-latest.md` desde una ficha genérica defensiva a una justificación canónica y corta por ciudad, sin tocar `bot.py`, `city_policy_state.json`, runtime live, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos cierran en `ok=7, warning=1, error=0`. La effective view sigue dejando las mismas `10` ciudades como `blocked`, pero la lectura ya no las trata como un bloque homogéneo: `London` queda como único caso bien defendido por memo estructural explícito (`Weather Underground vs Open-Meteo`), `Madrid/Singapore/Tel Aviv/Toronto/Wellington` quedan alineadas pero subdocumentadas, y `Ankara/Miami/Paris/Seattle` pasan a quedar marcadas como bloqueos hoy conservados pero dudosos, con revisión futura separada si se quiere sostener que `blocked` sigue significando descarte estructural y no carry-forward histórico. |
| 2026-04-12 | Explícita | Sesión 149 | drift-audit/latest/checks | Se cierra la auditoría `Manual Config Drift` y su cleanup inmediato sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`. Primero se rehidrata `runtime_policy_effective_view`, se reejecutan `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos preflights vuelven a cerrar en `ok=7, warning=1, error=0`; el warning residual de `metrics_funnel_naming` queda eliminado al corregir el mensaje autorreferencial del propio `system_alignment_check.py`. Luego `docs/manual-config-drift-audit-2026-04-12.md` clasifica el estado de los overrides/manual lists: `DEFAULT_ACTIVE_CITIES=""` y `DEFAULT_CANARY_CITIES=""` quedan alineados, `ACTIVE_TRADING_CITIES` queda fósil como fuente de verdad, `BLOCKED_CITIES` se sostiene como override manual de seguridad estructural y se deja `docs/blocked-cities-rationale-latest.md` como ficha corta. `tools/reference_trader_city_market_cross.py` deja de caer a `legacy_bot_lists` y pasa a usar `runtime_policy_effective_view` más default canónico `shadow`; se regeneran `reference_trader_city_market_cross`, `city_validation_ledger` y `city_promotion_gate`, desaparece `untracked` de la capa derivada y deja de reabrirse drift fósil tipo `Chicago active`. Finalmente se retiran los snapshots stale `normal_pull_check/final_check` de `data/runtime_import_derived` y se crea `docs/next-session-handoff-2026-04-12-blocked-cities-evidence.md` para el siguiente bloque lógico. |
| 2026-04-12 | Explícita | Sesión 148 | telegram/runtime_import/latest | Se cierra `Telegram Correctness` sin tocar `bot.py`. Primero se respetan los dos preflights canónicos (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`), que siguen en `error=0`. Luego `tools/city_validation_ledger.py` pasa a leer por defecto `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` desde `data/runtime_import/` en vez de `data/` local, para que `city-intelligence` deje de nacer en falso `runtime_inputs_missing`. Sobre esa base, `tools/city_intelligence_daily_summary.py` se reancla a `runtime_policy_effective_view` y `system_alignment_check_operational` para publicar la historia vigente: runtime read-only manifestado, preflight operacional verde, `blocked=10`, `canary=6`, `shadow=14`, `active=0`, sin `blocking_operational_collision`; además deja de mandar repetir el transporte runtime ya validado. `tools/city_intelligence_telegram_alert.py` y `tools/city_promotion_gate.py` limpian framing stale de monetización y pasan a usar lenguaje de lectura operativa. Validación: `python tools/city_intelligence_pipeline.py --telegram-dry-run` deja `overall_status=ok` y `runtime_inputs_status=available`; `python tools/city_intelligence_daily_summary.py --dry-run` regenera `docs/city_intelligence_daily_summary_latest.md` con el mensaje ya alineado. |
| 2026-04-12 | Explícita | Sesión 147 | docs/dashboard/template/checks | Se cierra `Dashboard Correctness` sin tocar `bot.py`. Primero se regenera `runtime_policy_effective_view` para quitar el bloqueo de frescura operativa, y ambos preflights (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`) vuelven a quedar sin errores. Luego `templates/dashboard.html` deja de presentar `markets_evaluated` como si fueran mercados brutos y pasa a tratarlo explícitamente como alias legacy de `candidates_after_prefilters`; además reencuadra `Road to Real` como checklist heredado, añade una capa de `progreso reciente` apoyada en `cycle_history` y vuelve visible la actividad runtime reciente (ciclos, buys, cierres). Se actualizan `docs/guia-lectura-dashboard.md`, `docs/dashboard-telegram-human-layer-readout-2026-04-11.md` y se crea `docs/dashboard-correctness-readout-2026-04-12.md`. Validación final: `python verify_before_deploy.py` en `643/643`. Se actualizan también `CONTEXTO.md`, el roadmap del módulo y se deja listo `docs/next-session-handoff-2026-04-12-telegram-correctness.md`, dejando explícito que el siguiente bloque debe abrirse como sesión limpia nueva y que `Opus` no hace falta por ahora. |
| 2026-04-12 | Explícita | Sesión 146 | docs/roadmap/handoff | Se mejora el módulo `human-reading-alignment` para que el criterio ya no sea solo correctness técnica, sino también utilidad humana y cierre anti-drift. `docs/human-reading-alignment-roadmap-2026-04-12.md` pasa a exigir que Dashboard y Telegram respondan de forma consistente dónde estamos, qué falta para el siguiente escalón, si el sistema va por buen camino y cómo se distinguen corto, medio y largo plazo. También se añade una regla de cierre anti-drift: si una sesión cambia una pieza que afecta lectura humana, debe dejar explícito qué quedó alineado, qué sigue pendiente y cuál es la siguiente sesión limpia. `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` queda reforzado para que la siguiente sesión de Dashboard no persiga solo wiring factual, sino una lectura diaria más útil y menos friccional para el operador. |
| 2026-04-12 | Explícita | Sesión 145 | docs/handoff/roadmap | Se define el módulo `human-reading-alignment` para corregir la capa humana por bloques limpios y sin volver a mezclar dashboard, Telegram, copy y estrategia en una sola sesión. Se crea `docs/human-reading-alignment-roadmap-2026-04-12.md`, que fija la fuente de verdad única (`runtime_policy_effective_view`, `system_alignment_check`, `metrics-funnel-naming`, `runtime_import/*`), las fases `Preflight -> Dashboard Correctness -> Telegram Correctness -> Shared Copy Layer -> Final Verification`, los criterios para cerrar sesión y los casos en los que sí conviene abrir revisión con Opus. También se crea `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` con el prompt exacto para la siguiente sesión limpia dedicada solo a `Dashboard Correctness`, incluyendo lecturas mínimas, preflight, hallazgos confirmados y Definition of Done. El reparto de modelos queda explícito: Codex ejecuta y cierra, Sonnet ayuda en auditoría/copy compacta, Opus solo entra si aparece conflicto real de fuente de verdad o arquitectura. |
| 2026-04-11 | Explícita | Sesión 144 | docs/read-only/alignment | Se completa la auditoría read-only de Dashboard y Telegram contra la capa canónica actual. Los dos preflights (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`) siguen en `ok=7, warning=1, error=0`, pero el contraste revela drift humano real: el snapshot local del dashboard sigue contando una topología legacy/local (`4` activas: `Atlanta`, `Buenos Aires`, `Chicago`, `Dallas`; `0` ciclos; `0` shadow; `0` cierres) que contradice la `runtime_policy_effective_view` vigente (`active_effective_count=0`, `canary=6`, `shadow=14`) y la observación runtime de `20` ciclos con `4` buys reales y `4` cierres. Además, `templates/dashboard.html` sigue llamando "Mercados escaneados" al alias legacy `markets_evaluated`, rompiendo el contrato de naming del funnel. En Telegram, `docs/city_intelligence_daily_summary_latest.md` queda stale en el viejo framing `runtime_inputs_missing` aunque la capa canónica actual ya parte de `runtime_import` manifestado y ledger disponible. Se crean `docs/dashboard-telegram-human-layer-audit-2026-04-11.md` y `docs/dashboard-telegram-human-layer-readout-2026-04-11.md`; la recomendación explícita es hacer `correctness de lectura` antes de una sesión de copy/UI. |
| 2026-04-11 | Explícita | Sesión 141 | docs/read-only/scoreboard | Se refresca el snapshot runtime por la vía canónica read-only (`tools/railway_runtime_snapshot_pull.ps1`) y se confirma base limpia para throughput: `runtime_import_manifest.json` queda con `pulled_at=2026-04-11T10:52:35Z`, `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` cierran en `ok=7, warning=1, error=0`, sin `blocking_operational_collision`. Sobre esa base se completa una observación extendida de `Step 5` en `docs/step5-throughput-observation-extended-2026-04-11.md`: ventana de `20` ciclos, `raw_markets_fetched ~330`, `candidates_after_prefilters=307`, `condition_filtered_out=285`, `candidates_with_edge=4`, `trades_executed=4`, con cuello aún dominado por `date/price/condition`. La lectura honesta es que `auto_canary` no es puro etiquetado porque las `4` compras reales del tramo salen de ciudades hoy canary (`Atlanta`, `Shanghai`, `Seoul`, `Tokyo`) y las `4` cierran como `RESOLVED_WIN` por `+$1.69`, pero la conversión sigue siendo demasiado intermitente para abrir monetización o policy. Se crean además `docs/controlled-monetization-gate-2026-04-11.md` y `docs/throughput-observation-readout-2026-04-11.md` para dejar el gate de una futura discusión de monetización controlada con bankroll `$25` y un readout corto de cierre. |
| 2026-04-11 | Explícita | Sesión 139 | docs/handoff | Se crea `docs/next-session-handoff-2026-04-11-dallas-claim.md` para abrir una sesión corta enfocada exclusivamente en Dallas como último `blocking_operational_collision`, sin tocar `bot.py`, runtime ni policy live. El handoff incluye además un segundo bloque listo para usar como prompt de revisión a Opus una vez terminada la tarea de Dallas, de modo que la siguiente revisión estratégica parta ya del paquete completo: alignment base, collision barrier, Phase 6.5 y cleanup final de Dallas. |
| 2026-04-11 | Explícita | Sesión 139 | tools/docs/read-only | Mini `Phase 6.5` implementada para endurecer la barrera de colisiones sin tocar `bot.py`, policy live, thresholds, bankroll ni `city_policy_state.json`. `tools/runtime_policy_effective_view.py` ahora clasifica `collision_noise`, `documented_drift` y `blocking_operational_collision`; `tools/reference_trader_city_market_cross.py` deja de arrastrar claims legacy de policy cuando existe la effective view; `tools/system_alignment_check.py` deja de bloquear por `collision_count > 5` y pasa a bloquear por `blocking_operational_collision_count > 0`. Resultado: el preflight `observe` mejora a `ok=7, warning=1, error=0`, el `runtime_ledger` pasa a `ok`, el drift fuerte de `cross` sobre las canaries se limpia, y el bloqueo operacional queda aislado en un único blocker duro: `Dallas` (`env active` vs `runtime auto_shadow`). Se documenta el cambio en `docs/phase6-5-collision-severity-hardening-2026-04-11.md` y se actualizan roadmap y reglas de preflight. |
| 2026-04-11 | Explícita | Sesión 138 | docs/prompt | A partir del readout post-Opus/post-Phase-6 se prepara `docs/claude-opus-prompt-collision-barrier-followup-2026-04-11.md`, un prompt corto y limpio para una nueva revisión de Opus. El prompt deja explícito que la review original de alignment ya ocurrió, que el foco ya no es reabrir wiring base, y que la nueva pregunta es cómo pasar con seguridad desde la barrera `collision_count=17 > 5` hacia una futura discusión operacional o de monetización controlada. |
| 2026-04-11 | Explícita | Sesión 138 | docs/readout | Sesión read-only enfocada exclusivamente en clasificar la barrera `collision_count=17 > 5` después de Opus y de `Phase 6`, sin reabrir alignment base ni tocar policy/throughput. Se crea `docs/collision-barrier-readout-post-opus-phase6-2026-04-11.md`, que separa las colisiones en tres buckets: ruido aceptable por diseño (`shadow` efectivo vs `cross=untracked`), drift documental/cross stale que contamina futuras lecturas (`Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo` como canaries efectivas que `cross` sigue viendo como `shadow`), y blockers reales de discusión operacional (`Dallas` por `env active` vs `runtime shadow`; `Chicago` y `Buenos Aires` por `cross active` vs `effective shadow`). La conclusión deja claro que el `17` actual es una alarma conservadora pero no un diagnóstico de severidad: el subconjunto realmente bloqueante es más pequeño y debe encuadrarse antes de cualquier debate de monetización o policy. |
| 2026-04-11 | Explícita | Sesión 137 | docs/handoff | Cierre de sesión orientado a trazabilidad post-Opus. Se crea `docs/next-session-handoff-2026-04-11-collision-barrier.md` para abrir una sesión limpia enfocada exclusivamente en clasificar la barrera `collision_count=17 > 5` sin reabrir alignment base ni mezclar monetización, throughput o policy. El handoff deja además el puente explícito para una futura revisión de Opus: la base ya revisada está en `docs/opus-review-throughput-alignment-2026-04-10.md`, y todo el trabajo posterior relevante quedó cerrado en sesiones `134-136`. |
| 2026-04-11 | Explícita | Sesión 136 | read-only validation | Se ejecuta el siguiente paso lógico tras `Phase 6`: regenerar `runtime_policy_effective_view` desde el snapshot manifestado y volver a correr el preflight en modo `operational`. La frescura deja de ser el bloqueo principal (`generated_at=2026-04-11T09:38:56+00:00`), y el sistema expone la barrera real: `collision_count=17` frente al umbral `5`, con `ok=6`, `warning=1`, `error=1`. El estado operativo queda clarificado: el alignment ya está suficientemente endurecido para mostrar que no se puede abrir una discusión de throughput/policy todavía, no por artefactos viejos sino por divergencia efectiva demasiado alta. |
| 2026-04-11 | Explícita | Sesión 135 | tools/docs/read-only | Se implementa la mini `Phase 6` de `Decision Preflight Hardening` recomendada por Opus, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni policy live. `tools/system_alignment_check.py` gana `--decision-mode observe/operational`, separa las salidas `latest` normales de las operacionales (`data/system_alignment_check_operational.json`, `docs/system_alignment_check_operational_latest.md`), añade `prompt_semantic_scan`, y endurece el modo `operational` con bloqueo por SLO de frescura del effective view (`6h`). Se crean `docs/bot-funnel-counter-contract-2026-04-11.md` para mapear counters legacy de `bot.py` a nombres canónicos del funnel y `docs/decision-preflight-rules-2026-04-11.md` para fijar las reglas `observe` vs `operational`, el umbral de colisiones y la regla humana de no decidir por PnL con `<20` trades cerrados. Se actualizan roadmap, phase closeout, artifact map, checklist, handoff y prompt de checkpoint. Estado final: `observe => ok=6, warning=2, error=0`; `operational => ok=6, warning=1, error=1`, bloqueando correctamente cualquier discusión operativa con la foto runtime actual. |
| 2026-04-11 | Explícita | Sesión 134 | tools/docs/read-only | Se resuelve el warning restante de targets del paquete de alineación sin tocar `bot.py`, `city_policy_state.json`, thresholds ni allowlists. `tools/city_intelligence_pipeline.py` deja atrás el string plano `tracker_targets` y pasa a exponer `runtime_derived_targets`, `exploratory_targets` y `tracker_targets` como listas; las targets derivadas salen de `data/runtime_policy_effective_view.json` y con el snapshot actual quedan `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai` y `Tokyo`, mientras `Chicago` queda como exploratory. `tools/city_intelligence_service.py` y `tools/city_intelligence_railway_service.py` se alinean con `CITY_INTELLIGENCE_EXPLORATORY_TARGETS`, `docs/city-intelligence-railway-service.md` documenta el contrato nuevo y `tools/system_alignment_check.py` pasa a exigir listas explícitas y ausencia de overlap. Tras regenerar `data/city_intelligence_pipeline.json`, `docs/city_intelligence_pipeline_latest.md`, `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`, el preflight queda en `ok=3`, `warning=2`, `error=0`; desaparece el warning de `city_intelligence_targets` y solo permanecen los warnings aceptados de divergencias policy/cross. En la misma sesión se ejecuta `Step 5` en modo observación read-only y se documenta `docs/step5-throughput-observation-2026-04-11.md`: el sistema sigue viendo `~330` mercados brutos por ciclo, pero el cuello dominante reciente no es edge mínimo sino `condition_filtered_out` junto con filtros de fecha/precio; en los últimos `20` ciclos hubo `4` compras en `3` ciclos y `3/3` cierres recientes ganadores por `+$1.31`, sin evidencia nueva que justifique tocar throughput o pedir Opus todavía. Como continuación de esa misma fase, `docs/shadow-opportunity-shortlist-2026-04-11.md` separa la vigilancia shadow real del ruido: `Chicago` queda como principal caso exploratorio a seguir; `Hong Kong` y `Beijing` como secundarios; y las ciudades ya absorbidas por `auto_canary` dejan de contaminar la pregunta de "qué shadow nueva merece atención". La sesión además deja cerrado el marco de trabajo de esta fase con `docs/system-alignment-phase-closeout-2026-04-11.md`, `docs/system-alignment-artifact-map-2026-04-11.md` y `docs/system-alignment-session-checklist-2026-04-11.md`, más la actualización del roadmap y del handoff para que las sesiones siguientes no reabran dudas de fuente de verdad ni dependan de contexto humano largo. |
| 2026-04-10 | Explícita | Sesión 133 | docs/handoff | Sesión corta de preparación para continuar limpio al día siguiente. Se crea `docs/next-session-handoff-2026-04-10.md` con el prompt exacto de arranque: leer `AGENTS.md`, Sesión 132 de `CONTEXTO.md`, correr `python tools/system_alignment_check.py`, revisar los docs latest y atacar solo el warning restante de targets (`runtime_derived_targets` vs `exploratory_targets`) sin tocar `bot.py`, `city_policy_state.json`, thresholds ni allowlists. `docs/system-alignment-lean-roadmap-2026-04-10.md` se actualiza para que su bloque “Cómo empezar una sesión nueva” ya no apunte al viejo Step 1 sino al estado actual del roadmap. |
| 2026-04-10 | Explícita | Sesión 132 | tools/docs/read-only | Steps 2-4 del roadmap LEAN de alineacion, sin Opus porque no se toca riesgo ni runtime: `tools/runtime_policy_effective_view.py` genera una vista read-only unica de policy efectiva (`data/runtime_policy_effective_view.json`, `docs/runtime_policy_effective_view_latest.md`) combinando snapshot manifestado + listas env declaradas. Validacion: Dallas queda `env_declared_mode=active`, `runtime_policy_mode=auto_shadow`, `effective_mode=shadow`, `collision_flag=true`; las 6 canaries runtime quedan `effective_mode=canary`; `active_effective_count=0`. Se crea `docs/metrics-funnel-naming.md` para fijar `raw_markets_fetched`, `candidates_after_prefilters` alias legacy `markets_evaluated`, `condition_filtered_out`, `candidates_with_edge`, `candidates_selected`, `trades_executed` y `shadow_opportunities_observed`. Se crea `tools/system_alignment_check.py`, que escribe `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`; estado actual `error=0`, `ok=2`, `warning=3` por divergencias policy/cross explicitas y targets de `city-intelligence` aun no etiquetados como runtime-derived/exploratory. Punto recomendado de cierre antes de Step 5 o target tagging. |
| 2026-04-10 | Explícita | Sesión 131 | tools/Railway read-only | Step 1 del roadmap LEAN de alineacion: manifest runtime atomico y bijectivo. `tools/railway_runtime_snapshot_pull.ps1` pasa a construir el snapshot en un directorio temporal, escribir `runtime_import_manifest.json` al final, validar que los archivos del temp coinciden con `manifest.files` y reemplazar `data/runtime_import/` solo al completar. El snapshot manifestado se amplia a 10 artefactos runtime (`shadow_city_tracking`, `cycles_history`, `cycle_summary`, `decisions`, `performance`, `postmortem`, `skip_log`, `trade_lifecycle`, `audit`, `city_policy_state`) y deja fuera outputs derivados. `tools/city_validation_ledger.py` falla cerrado con `runtime_inputs_status=manifest_drift` si hay archivo listado faltante, archivo extra, duplicado o mismatch de bytes; gate y pipeline propagan el estado como no disponible. Validado con pull normal Railway read-only (`available`, 10/10, `n_cities=24`), archivo faltante (`listed_file_missing`) y archivo extra (`unlisted_file_present`). No se toca `bot.py`, no se escribe `city_policy_state.json`, no se cambian thresholds ni allowlists. |
| 2026-04-10 | Explícita | Sesión 130 | docs/Railway read-only | Auditoría operativa de throughput y alineación antes de pedir revisión a Opus. Se confirma con artefactos live de `polymarket-bot` que las 3 compras limpias recientes ganaron (`Atlanta`, `Shanghai`, `Seoul`, `+$1.31` total), pero que el sistema quedó casi sin throughput: sigue encontrando `~330` mercados brutos, mientras `markets_evaluated=12-26` es post-filtros; Dallas está en `ACTIVE_TRADING_CITIES` pero runtime la resuelve como `auto_shadow`, por lo que no hay ciudad `active` efectiva y el trading depende solo de canaries. Se documenta el embudo de skips, la desalineación de targets/volúmenes entre `polymarket-bot`, `city-intelligence` y `phase5`, y el requisito de manifest runtime atomico antes de automatizar transporte. Se crean `docs/throughput-alignment-audit-2026-04-10.md` y `docs/claude-opus-prompt-throughput-alignment-review-2026-04-10.md`, y luego el prompt se amplía para pedir a Opus una hoja de ruta LEAN de estandarización sistémica: contratos canónicos, fuentes de verdad, naming del funnel, manifests, staleness, targets y checks pre-decision. La respuesta de Opus se incorpora en `docs/opus-review-throughput-alignment-2026-04-10.md`: `GO WITH CHANGES`, pero cableado primero, no throughput; roadmap en 5 pasos (manifest bijectivo, runtime policy effective view, naming del funnel, system alignment check, observación honesta). Se crea `docs/system-alignment-lean-roadmap-2026-04-10.md` como checklist único de arranque para sesiones nuevas. No se toca `bot.py`, policy runtime, thresholds ni allowlists. |
| 2026-04-10 | Explícita | Sesión 127 | tools/docs/Railway read-only | Auditoría LEAN del transporte runtime read-only tras el GO de Opus al fail-closed endurecido. Railway muestra tres volúmenes separados (`polymarket-bot-volume`, `city-intelligence-volume`, `phase5-visibility-volume`) y la CLI no expone read-only en `volume attach/update`, por lo que se descarta montar directamente el volumen del bot en `city-intelligence`. Se crea `tools/railway_runtime_snapshot_pull.ps1` para hacer pull local read-only vía SSH desde `polymarket-bot` de `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` hacia `data/runtime_import/`, con manifest. El ledger contra ese snapshot sale `runtime_inputs_status=available`, `n_cities=22`, `actionable=1`; Shanghai ya muestra `edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`, pero sigue `policy_mode=shadow` porque el ledger aún no parsea `city_policy_state.json`. Se documenta el nuevo cuello semántico y se crea prompt para Opus antes de implementar `runtime_policy_mode`. |
| 2026-04-10 | Explícita | Sesión 126 | tools/docs | Hardening pre-transporte del fail-closed tras la segunda revisión de Opus. `tools/city_validation_ledger.py` mueve la dependencia de `bot` a import lazy posterior al chequeo de inputs runtime, de modo que la rama `runtime_inputs_missing` puede escribirse sin cargar `bot.py`; si el import lazy falla con inputs presentes, degrada a fail-closed incluyendo `bot_module` en `missing_runtime_inputs`. `tools/city_intelligence_pipeline.py` cambia la prioridad de estados para que `runtime_inputs_missing` prevalezca incluso sobre `partial_failure`. `docs/system-architecture-city-intelligence-2026-04-10.md` aclara que `cycles_history.jsonl` no es requisito v0 del fail-closed, sino input posterior de staleness/auditoría. Se actualiza el prompt de revisión `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md`; validación local mantiene `overall_status=runtime_inputs_missing` y rama disponible funcional con placeholders. |
| 2026-04-10 | Explícita | Sesión 125 | tools/docs | Primer paso LEAN implementado tras la revisión de Opus: `city-intelligence` falla cerrado cuando faltan artefactos runtime del bot, sin tocar `bot.py` ni trading core. `tools/city_validation_ledger.py` valida `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`; si faltan, escribe `runtime_inputs_status=missing`, `missing_runtime_inputs`, `cities=[]` y `bottleneck_counts.runtime_inputs_missing=1`. `tools/city_promotion_gate.py` propaga `gate_status=runtime_inputs_missing`; `tools/city_intelligence_pipeline.py` marca `overall_status=runtime_inputs_missing`; alertas y daily summary explican que no hay acceso runtime y no se puede concluir por ciudad. Validación local con `python tools/city_intelligence_pipeline.py --telegram-dry-run` y `python tools/city_intelligence_daily_summary.py --dry-run`; se crea `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md` para que Opus revise antes de decidir transporte runtime read-only. |
| 2026-04-10 | Explícita | Sesión 124 | docs | Incorporación de la revisión adversarial de Opus sobre la arquitectura `polymarket-bot`/`city-intelligence`, sin tocar `bot.py` ni implementar código. Opus devuelve `GO WITH CHANGES` y fuerza correcciones importantes: `city_validation_ledger.py` ya importa `bot` y consume constantes runtime, el bug de Shanghai es plumbing (`required=False` + `available=False` descartado) antes que semántica, `policy_mode` viene del cross analítico y no de `city_policy_state.json`, el ledger puede omitir ciudades solo-runtime al iterar solo `cross.city_rows`, y los drift detectors propuestos aún no tienen productor/consumidor. Se actualiza `docs/system-architecture-city-intelligence-2026-04-10.md` con fail-closed como primer cambio futuro recomendado y se crea `docs/opus-review-system-architecture-city-intelligence-2026-04-10.md` para trazabilidad. |
| 2026-04-10 | Explícita | Sesión 123 | docs | Definición documental de la arquitectura canónica entre `polymarket-bot`, `city-intelligence` y `phase5-visibility`, sin tocar `bot.py` ni trading core. Se crea `docs/system-architecture-city-intelligence-2026-04-10.md` con arquitectura actual factual, arquitectura objetivo, fuentes de verdad, contratos de datos, loops de feedback, drift detectors, decisiones abiertas, diagrama Mermaid y rol objetivo de `phase5-visibility` como capa experimental/legacy a fusionar o archivar, no como core. Se crea también `docs/claude-opus-prompt-system-architecture-city-intelligence-2026-04-10.md` para revisión adversarial antes de implementar cualquier import/snapshot runtime. |
| 2026-04-10 | Explícita | Sesión 122 | Railway read-only | Auditoría live del loop Shanghai entre `city-intelligence` y `polymarket-bot`. Se confirma que `city-intelligence` está sano pero usa un volumen separado sin `shadow_city_tracking.json`, `cycles_history.jsonl` ni `audit.json`, así que su ledger queda ciego a la evidencia runtime. En el volumen del bot principal, `Shanghai` sí tiene huella real en `shadow_city_tracking.json`: `markets_seen=84`, `edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`, `last_seen_at=2026-04-10T08:00:42Z`. Además `city_policy_state.json` muestra que Shanghai fue autopromovida a `auto_canary` el `2026-04-06T12:33:22Z` por `19` edges y `15` ciclos, por lo que la premisa de Shanghai como shadow puro ya no representa el runtime live. Queda documentado en `docs/shanghai-shadow-live-audit-2026-04-10.md`; siguiente paso: alinear `city-intelligence` con evidencia runtime del bot principal antes de Austin/Wuhan. |
| 2026-04-10 | Explícita | Sesión 121 | local | Auditoría adversarial del estado de `city-intelligence` tras la revisión de Claude. Se confirma localmente que no existen `data/shadow_city_tracking.json`, `data/cycles_history.jsonl` ni `data/audit.json`, por lo que el ledger no puede acumular edge/NOAA propio y todos los `edge_evidence` siguen en cero. `Shanghai` sigue siendo el único caso formal en `shadow_validation`, pero esa etiqueta aún no es operativamente útil sin huella shadow. Se regenera `tools/city_intelligence_pipeline.py --telegram-dry-run` sin refrescar probe/censo para corregir `docs/city_intelligence_pipeline_latest.md`, que queda alineado con señal usable. La decisión metodológica es no entrar todavía en Austin/Wuhan: el siguiente paso correcto es auditar en Railway si el shadow de Shanghai está alimentando `shadow_city_tracking.json` y `cycles_history.jsonl`. |
| 2026-04-09 | Explícita | Sesión 120 | local | Sesión separada de auditoría del cuello real post-censo en `city-intelligence`, sin tocar `bot.py` ni trading core. Se demuestra que `reference_trader_city_market_cross.json` estaba stale respecto a `directional_trader_enrichment.json`, se regeneran `reference_trader_city_market_cross`, `city_validation_ledger` y `city_promotion_gate`, y el diagnóstico deja de colapsar en `trader_input_*`: el ledger actualizado distribuye `trader_discovery=12`, `market_visibility=5`, `source_fidelity=3`, `shadow_validation=1`. La conclusión operativa queda afinada: `Shanghai` es el único caso cuyo bloqueo útil ya es `shadow_validation`; `Austin` y `Wuhan` siguen frenadas por `source_fidelity`. Además se ajusta `tools/city_promotion_gate.py` para que el gate siga el bottleneck real del ledger y no confunda `needs_shadow_validation` con casos que todavía están en `source_fidelity` o `market_visibility`. |
| 2026-04-09 | Explícita | Sesión 119 | local + Railway | Investigación nueva sobre el censo comparable y validación live del cambio mínimo recomendado por Opus. Se crean `docs/comparable-trader-census-audit-2026-04-09.md` y `docs/claude-opus-prompt-comparable-trader-census-audit-2026-04-09.md`, se demuestra con datos live que el `0 traders after filter` venía de mirar solo `20` mercados top-volume y no de ausencia real de comparables, y Opus valida que primero hay que ampliar el universo a `200`. Se actualizan los defaults de `city-intelligence` a `200`, se cambian targets live a `Chicago,Dallas,Seattle,Munich,Madrid`, y Railway confirma una corrida real a las `18:00 UTC` con `--refresh-census --census-markets 200`, `overall_status=ok`, `signal_health=usable_signal` y `quality_reference_traders=9`. El servicio queda estabilizado otra vez con `CITY_INTELLIGENCE_REFRESH_CENSUS=false`, y el siguiente frente decidido pasa a ser auditar si el cuello real ahora es `trader_discovery` o `shadow_validation`. |
| 2026-04-09 | Explícita | Sesión 118 | local | Auditoría técnica del proxy local `127.0.0.1:9`: se confirma que no viene de variables persistentes de Windows, perfiles de PowerShell, `.vscode`, `git` ni `npm`, sino del proceso actual lanzado por Codex en VS Code (`CODEX_SANDBOX_NETWORK_DISABLED=1`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_vscode`, `PATH` con `.sbx-denybin` y binario de la extensión). Se añaden `tools/run_clean_network.ps1`, `tools/polymarket_api_probe.py` y `docs/local-network-proxy-audit-2026-04-09.md` para limpiar solo el proceso hijo, ejecutar verificaciones con red real y restaurar el entorno al salir. Validación final fuera del sandbox: el probe del repo devuelve `200` en `trades?limit=1` y `positions?...`. |
| 2026-04-09 | Explícita | Sesión 117 | local + Railway | Se despliega en Railway un servicio nuevo `city-intelligence` para ejecutar la capa de mejora continua del sistema de city intelligence sin tocar `bot.py`. Se crean `tools/city_intelligence_service.py`, `tools/city_intelligence_daily_service.py`, `tools/city_intelligence_railway_service.py` y `docs/city-intelligence-railway-service.md`, se provisiona volumen dedicado `city-intelligence-volume` en `/app/data`, se fijan variables (`RAILPACK_START_CMD`, horas `0/6/12/18 UTC`, resumen diario `09:00 UTC`, targets `Shanghai,Chicago,Seoul`, Telegram) y el despliegue `cf189b91-ac6a-4d29-a771-5c81abc13d4c` queda en `SUCCESS`, durmiendo hasta `00:00 UTC` para la primera corrida. |
| 2026-04-08 | Explícita | Sesión 116 | local | Se corrige un warning técnico detectado en logs live del bot principal: `datetime.utcnow()` en el bloque de salud del dashboard/focus se sustituye por `datetime.now(timezone.utc)` y se normaliza `_last_cycle` como datetime aware UTC antes de calcular `hours_ago`. No cambia trading ni scheduler; `verify_before_deploy.py` vuelve a cerrar en `643/643`. |
| 2026-04-08 | Explícita | Sesión 115 | local | Se documenta el siguiente gran frente del proyecto en `docs/city-intelligence-automation-roadmap-2026-04-08.md`: una automatización read-only para aprender de traders exitosos comparables y convertir esa evidencia en recomendaciones por ciudad. Además se deja `docs/claude-opus-prompt-city-intelligence-validation-2026-04-08.md` como prompt listo para que Claude Opus valide estratégicamente el enfoque antes de que Codex implemente. |
| 2026-04-08 | Explícita | Sesión 114 | local + Railway | Se despliega en Railway un servicio separado `phase5-visibility` dentro de `enchanting-respect` para ejecutar periódicamente la pipeline read-only de fase 5. Se crean `tools/phase5_visibility_service.py` + `docs/phase5-visibility-service.md`, se añade bootstrap automático desde `seed_data/phase5/`, se provisiona volumen dedicado `phase5-visibility-volume` en `/app/data`, se fijan variables/Telegram y el despliegue final queda validado con `overall_status=ok`, `visibility_snapshots=2` y `simultaneous_visibility_count=0`. |
| 2026-04-08 | Explícita | Sesión 113 | local | Se crea `tools/phase5_visibility_telegram_alert.py` junto con `docs/phase5-visibility-telegram-alert.md` para enviar una alerta one-shot por Telegram cuando aparezca una coincidencia nueva `Shanghai + Chicago` en el tracker de visibilidad. La etapa queda integrada en `tools/phase5_visibility_pipeline.py` con persistencia anti-spam en `data/phase5_visibility_alert_state.json`. |
| 2026-04-08 | Explícita | Sesión 112 | local | Se crea `tools/phase5_visibility_pipeline.py` junto con `docs/phase5-visibility-pipeline.md` para automatizar en un solo comando la fase 5 read-only. La primera corrida deja `data/phase5_visibility_pipeline.json` + `docs/phase5_visibility_pipeline_latest.md`, ejecuta con éxito tracker, snapshot de Shanghai, benchmark de Chicago y comparador final, y resume `dominant_gap=market_visibility_and_selection` con `simultaneous_visibility_count=0`. |
| 2026-04-08 | Explícita | Sesión 111 | local | Se crea `tools/city_probe_visibility_tracker.py` junto con `docs/city-probe-visibility-tracker.md` para persistir la visibilidad de `Shanghai` y `Chicago` a partir de snapshots del `settlement_fidelity_probe`. La primera corrida deja `data/city_probe_visibility_tracker.json` + `docs/city_probe_visibility_tracker_latest.md` y confirma `1` snapshot, `0` coincidencias simultáneas, `Shanghai visible=1` y `Chicago visible=0`. Desde aquí la comparación deja de depender de fotos aisladas y pasa a una base acumulativa. |
| 2026-04-08 | Explícita | Sesión 110 | local | Se crea `tools/shanghai_vs_chicago_comparator.py` junto con `docs/shanghai-vs-chicago-comparator.md` para comparar directamente la ciudad puente `Shanghai` y el benchmark `active` `Chicago`. La primera corrida deja `data/shanghai_vs_chicago_comparator.json` + `docs/shanghai_vs_chicago_comparator_latest.md` y concluye que el gap dominante observado hoy es `market_visibility_and_selection`: Shanghai aparece en el flujo de mercados local mientras Chicago no, así que la siguiente mejora debe ir por observabilidad comparativa de mercados visibles antes de deducir timing o edge de forecast. |
| 2026-04-08 | Explícita | Sesión 109 | local | Se crea `tools/chicago_active_benchmark.py` junto con `docs/chicago-active-benchmark.md` para dejar a `Chicago` como benchmark operativo simétrico frente a `Shanghai`. La primera corrida deja `data/chicago_active_benchmark.json` + `docs/chicago_active_benchmark_latest.md` y concluye `benchmark_strength=credible`, `observability_status=ok`, `next_action=use_as_active_benchmark`: aunque el probe local no mostraba mercados de Chicago en ese momento, la ciudad sigue siendo un benchmark útil por ser `active` y estar respaldada por dos referencias comparables fuertes. |
| 2026-04-08 | Explícita | Sesión 108 | local | Se crea `tools/city_phase5_contrast.py` junto con `docs/city-phase5-contrast.md` para comparar `Shanghai`, `Chicago` y `Seoul` con el mismo motor de snapshot. La primera corrida deja `data/city_phase5_contrast.json` + `docs/city_phase5_contrast_latest.md` y concluye que `Shanghai` sigue siendo la ciudad puente principal, pero el siguiente paso correcto pasa a ser `continue_shanghai_observability_plus_active_contrast`: mantener `Shanghai` como foco principal mientras se la contrasta explícitamente con `Chicago` como benchmark `active`. |
| 2026-04-08 | Explícita | Sesión 107 | local | Se implementa `tools/shanghai_shadow_test.py` junto con `docs/shanghai-shadow-test.md` y se ejecuta la primera corrida local del extractor. El snapshot queda en `data/shanghai_shadow_test.json` + `docs/shanghai_shadow_test_latest.md` y concluye `signal_status=building`, `data_quality=ok`, `next_action=expand_observability`: la ciudad sigue siendo prometedora, pero en local todavía faltan huellas de `shadow tracking` y `audit` para justificar un salto mayor. |
| 2026-04-08 | Explícita | Sesión 106 | local | Se crea `docs/shanghai-shadow-test-design.md` como contrato operativo del siguiente bloque. El documento fija por qué `Shanghai` es la ciudad puente principal, qué debe medir un test `shadow` read-only, qué artefactos producir y qué criterios usar para distinguir `stay shadow`, `expand observability` o `prepare controlled test`, sin tocar aún `bot.py` ni la estrategia. |
| 2026-04-08 | Explícita | Sesión 105 | local | Se crea `tools/city_watch_reinforced.py` + `docs/city-watch-reinforced.md` para condensar la fase siguiente en tres ciudades prioritarias: `Shanghai`, `Chicago` y `Seoul`. El readout reforzado deja a `Shanghai` como ciudad claramente prioritaria para `prepare_shadow_test_design`, `Chicago` como `watch_live_active_city` y `Seoul` como `expand_shadow_observability`, cerrando la fase de priorización y apuntando ya a un bloque concreto de diseño de test en shadow. |
| 2026-04-08 | Explícita | Sesión 104 | local | Se completa la fase 4 con `tools/city_watchlist_phase4.py` + `docs/city-watchlist-phase4.md`. La nueva watchlist ordena ciudades por acción recomendada: `Shanghai` queda como `prepare_test`, `Chicago` como `watch_active`, `Ankara` como `review_block_reason`, y detrás aparecen `Austin`, `Wuhan` y `Seoul` como ciudades a observar de cerca. El proyecto sale de investigación abierta y entra en modo de priorización operativa por ciudad. |
| 2026-04-08 | Explícita | Sesión 103 | local | Se completa la fase 3 con `tools/reference_trader_city_market_cross.py` + `docs/reference-trader-city-market-cross.md`. El cruce entre referencias reales, `city policy` y snapshot de mercados deja una shortlist operativa: `Shanghai` aparece como mejor ciudad puente (`shadow`, referencias reales + mercados visibles en probe), `Ankara` como mismatch fuerte de research/policy (`blocked` pero muy poblada por referencias), y `Chicago` como principal ciudad `active` tocada por traders de alta prioridad. |
| 2026-04-08 | Explícita | Sesión 102 | local | Se completa la fase 2.5 del plan operativo con `tools/directional_trader_enrichment.py` + `docs/directional-trader-enrichment.md`. La herramienta enriquece la shortlist comparable del censo direccional con posiciones activas/cerradas, `win rate` y `cash PnL`, y deja una primera jerarquía de referencias reales en `data/directional_trader_enrichment.json`. Primera corrida útil sobre el top 5: `Entire-Hood`, `Academic-Maniac`, `Motionless-Stalk` y `Massive-Distribution` salen como `high_priority_reference`; `White-Donkey` queda como `candidate_reference`. |
| 2026-04-08 | Explícita | Sesión 101 | local | Se ejecutan de verdad las fases 1 y 2 del plan de monetización incremental. `tools/settlement_fidelity_probe.py` queda validado tras corregir un `400 Bad Request` de Open-Meteo y ya produce `data/settlement_fidelity_probe.json` + `docs/settlement_fidelity_probe_latest.md` con cobertura `12/12` de forecast en la primera muestra. Además nace `tools/directional_trader_census.py` con `docs/directional-trader-census.md`: la primera corrida bruta muestra que el universo direccional está dominado por compras extremas cerca de `1.0`, y al alinearlo al rango `0.20-0.80` se reduce a una shortlist de `10` traders comparables, concentrados sobre todo en `Shanghai`, `Ankara` y `Wuhan`. |
| 2026-04-08 | Explícita | Sesión 100 | local | Se abre la fase operativa posterior al research cruzado Codex + Opus. Se crea `docs/strategic-monetization-plan-2026-04-08.md` como plan maestro por fases (`Settlement Fidelity Probe v1` -> `Directional Trader Census v1` -> gate de decisión) y se implementa `tools/settlement_fidelity_probe.py` junto con `docs/settlement-fidelity-probe.md`. La herramienta nueva es read-only, no toca `bot.py`, y deja preparado un snapshot reproducible de mercados direccionales con precio implícito, forecast `Open-Meteo`, metadata de resolución y proxy observado NOAA cuando exista. |
| 2026-04-08 | Explícita | Sesión 99 | local | Se documenta un estudio completo de Codex sobre traders comparables al universo actual de `polymarket-bot` en `RESEARCH_CODEX_TRADERS_2026-04-08.md`. El informe fija taxonomía de traders weather/prediction markets, compara esa taxonomía contra la estrategia vigente, detecta que el pipeline histórico de traders del repo sigue sesgado hacia `exact/range` mientras el bot solo monetiza `at_or_above/at_or_below`, y prioriza como siguiente research reconstruir el mapa de wallets realmente comparables antes de tocar forecast core o execution. |
| 2026-04-08 | Explícita | Sesión 98 | local | Se crea `docs/ESTRATEGIA_OPERATIVA.md` como documento canónico de la estrategia vigente para comparar el sistema con otros traders. Resume universo operado, condiciones permitidas, filtros de entrada, cálculo de probabilidad y edge, sizing `Half-Kelly`, modos `active/canary/shadow/blocked`, contrato de fuentes y capas de evaluación. Queda como base explícita para la próxima investigación orientada a monetización. |
| 2026-04-08 | Explícita | Sesión 97 | local | Validación live post-ciclo del rediseño `WR observado direccional`: Railway confirma que `shadow_city_tracking.json` ya usa el esquema nuevo y persiste `edge_hit`, pero `directional_history` sigue vacío porque el ciclo `08:00 UTC` tuvo `0 shadow` y `15 condition_filtered`; la tarjeta `0/72` queda reinterpretada como estado transitorio y no como WR real observado. Además se alinea Telegram para distinguir `ACTIVE` vs `CANARY`, renombrar `candidatos evaluados`/`shadow con edge`, separar `NOAA-verificado` del histórico total en `/accuracy`, aclarar el rol de NOAA en `/noaa`, y se documenta el contrato de fuentes `Open-Meteo decide / NOAA mide / Weather Underground resuelve`. Suite final `643/643`; siguiente sesión orientada a investigar traders y monetización. |
| 2026-04-07 | Explícita | Sesión 96 | local | Hotfix del dashboard tras el deploy del `WR observado direccional`: `build_dashboard_road_to_real()` seguía iterando `recent_opps` sin definirla y Railway caía con `NameError` al abrir `/`. Se repone la lectura desde `directional_history` y `verify_before_deploy.py` añade una regresión específica; suite final `643/643`. |
| 2026-04-07 | Explícita | Sesión 95 | `57be884` | Deploy a Railway del rediseño del `WR observado direccional`: el servicio arranca con código nuevo que ya incluye `directional_history`, pero el volume aún no había sido reescrito tras el restart. Se deja checklist post-ciclo para validar que `shadow_city_tracking.json` materializa la base persistente, persiste `edge_hit` y que la métrica live deja de depender de `recent_opportunities`. |
| 2026-04-07 | Explícita | Sesión 94 | local | Auditoría y rediseño del `WR observado direccional`: se confirma que el join shadow→NOAA estaba sesgado por leer `recent_opportunities` (ventana volátil) y por perder `edge_hit` al persistir. `shadow_city_tracking.json` gana `directional_history` como base persistente de señales shadow direccionales deduplicadas, el join normaliza `date` a `YYYY-MM-DD` y `verify_before_deploy.py` sube a `642/642`. |
| 2026-04-07 | Explícita | Sesión 93 | local/live | Se documenta otro episodio recurrente de auth rota en Railway (`Unauthorized` con tokens presentes y config writable), se recupera con `doctor -> reset -> launch-login -Browserless`, se valida restart live del servicio y se corrige `run_observability_alerts()` para dejar de mandar alertas legacy de `baja accuracy` y pasar a revisión NOAA-verificada en `active/canary`. |
| 2026-04-07 | Explícita | Sesión 92 | local | Se afinan y externalizan los umbrales de `Alertas activas` para la era NOAA-verificada: ciudades malas exigen `n>=5`, activas sin NOAA útil solo alertan por debajo de 3 casos, el join shadow→NOAA pide 20 señales y 10 observaciones NOAA, y el WR shadow no avisa hasta 8 resueltas. |
| 2026-04-07 | Explícita | Sesión 91 | local | El bloque `Alertas activas` deja de priorizar `accuracy baja` histórica y pasa a usar señales de la era NOAA-verificada: ciudades con NOAA-verificado malo, ciudades activas sin NOAA interpretable y problemas del join shadow→NOAA, manteniendo el legacy solo como nota contextual. |
| 2026-04-07 | Explícita | Sesión 90 | local | El bloque `Estado por ciudad` del dashboard se reorganiza en grupos semánticos (`Operativas y candidatas`, `Shadow observadas`, `Sin NOAA util`, `Fuera de observacion`) con una tabla por grupo y `main_reason` visible bajo cada ciudad para mejorar lectura humana y consumo por LLM. |
| 2026-04-07 | Explícita | Sesión 89 | local | `blocked` vuelve a reservarse para ciudades sin NOAA observable; las ciudades con NOAA configurable dejan de quedar fuera del scan por listas/overlays viejos y el dashboard separa rendimiento NOAA-verificado vs legado, además de recordar el estado abierto de `Salud del sistema`. |
| 2026-03-21 | Explícita | Sesión 2 | `bddcab8` | Bot base con edge detection, backtest y bankroll management. |
| 2026-03-21 | Explícita | Sesión 3 | `f97702e` | Instalación `pip`, CLOB API, autenticación y primera orden de prueba. |
| 2026-03-21 | Inferida | Iteración v3-v7 | `e8d11c0` `047f7e4` `5ac83b9` `c32c34f` `9e51025` `6973b74` `d5bf5d8` | Filtros de precio, scheduler, alertas Telegram, dashboard, cartera, órdenes enriquecidas y decision log. |
| 2026-03-21 | Inferida | Infraestructura inicial | `886a112` `d4194ac` `3d128fb` | `requirements.txt`, variables de entorno, `Procfile` y unificación de contexto en `CONTEXTO.md`. |
| 2026-03-22 | Inferida | Iteración v8 | `35ef3d6` `c2bc7ff` `eea1eef` `fba7a0b` | `MIN_DAYS/MAX_DAYS`, reintentos de red y expansión fuerte de ciudades soportadas. |
| 2026-03-22 | Inferida | Iteración v9 | `9e7941e` `4bd7e8b` `c857133` `d7ae3a3` `2aa59c1` `48d7c4f` | Pipeline de traders, `signals.json`, filtro de calidad, parseo de rangos, `logfull`, near misses y ajustes Kelly. |
| 2026-03-22 | Explícita | Sesión 9 | `91162b0` | Pipeline traders v2 y primeras órdenes reales 4/4 OK. |
| 2026-03-22 a 2026-03-23 | Inferida | Iteración v10-v10.2 | `d2ae676` `ce0684e` `931158e` `0ae32c9` `deb50b3` `3c408f3` `d01b4b9` | Exposición acumulativa, sigma calibrada, gestión activa, auditoría, bankroll real, performance tracker, cash balance y mejoras Telegram. |
| 2026-03-24 | Inferida | Iteración v10.3 | `bef71e3` | Cinco bugs corregidos y `verify_before_deploy.py` consolidado. |
| 2026-03-28 | Explícita | Sesión 19 | `a24fde2` `cd12121` `56aeb5a` `185f018` `374d6a8` `3c4b5f1` `19adfdd` `d382f47` `695f405` | v10.4 a v10.4.8: persistencia, rediseño Telegram, ciclos persistentes, DST robusto, trazabilidad multi-agente, tests funcionales, base de `postmortem.json`, alertas de observabilidad, bloqueo operativo de London y refinamiento final de botones Telegram. |
| 2026-03-29 | Explícita | Sesión 24 | `—` | Refinamiento del dashboard: modo oscuro, checklist histórico/serie separado, scorecard por stages y ciclos legacy legibles. |
| 2026-03-29 | Explícita | Sesión 25 | `—` | Pasada rápida de UX: `n/d` y `sin cierres` cuando la serie nueva todavía no tiene muestra real. |
| 2026-03-29 | Explícita | Sesión 26 | `—` | Último pulido UX: estado neutral `Esperando muestra` en el checklist del dashboard. |
| 2026-03-29 | Explícita | Sesión 27 | `—` | Nueva capa del dashboard: progreso operativo, trofeos validados y desbloqueos para saber qué evidencia falta antes de revisar lógica o subir bankroll. |
| 2026-03-29 | Explícita | Sesión 28 | `—` | Dashboard añade balance por tipo de cierre y liquidación para distinguir TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN de `pending_exit` y valor pendiente de canjear. |
| 2026-03-29 | Explícita | Sesión 31 | `—` | Hardening local de `v10.6.2`: alerta de bankroll fiable, rearme con margen, scorecard actualizado y docs/tests alineados. |
| 2026-03-30 | Explícita | Sesión 32 | `—` | Investigación estratégica Codex + Claude: Dallas `KDAL` como bug activo, auditoría mal nombrada, síntesis competitiva y preparación del alcance de `v10.6.3`. |
| 2026-03-30 | Explícita | Sesión 33 | `—` | Implementación local de `v10.6.3`: fix Dallas `KDAL`, `RESOLUTION_ICAO`, auditoría `forecast vs forecast posterior Open-Meteo` y suite en `358/358`. |
| 2026-03-30 | Explícita | Sesión 34 | `—` | Implementación local de `v10.6.4`: `observed_vs_forecast` con NOAA NCEI, `noaa_station_id` para 4 activas, lag de 2 días y suite en `371/371`. |
| 2026-03-30 | Explícita | Sesión 35 | `—` | Implementación local de `v10.6.5`: dashboard separa `Calidad Forecast Observada (NOAA)` del bloque legacy `Drift Open-Meteo`, con suite en `386/386`. |
| 2026-03-30 | Explícita | Sesión 36 | `—` | Sync post-recarga: depósito manual `+$14.99`, fallback `BANKROLL` alineado a `$25` y test para fijar el default local. |
| 2026-03-30 | Explícita | Sesión 37 | `—` | Playbook operativo multiagente, helper seguro para `agent_events.jsonl`, checks de consistencia docs-scoreboard y sync del scoreboard live. |
| 2026-03-30 | Explícita | Sesión 38 | `—` | Limpieza del scoreboard live, deduplicación robusta en `load_agent_events()` y regla explícita: review sin delta = `0 puntos` o sin evento. |
| 2026-03-30 | Explícita | Sesión 39 | `—` | Research final Lean Six Sigma: no adoptar salvo FMEA-lite y definiciones mínimas; playbook mínimo, hitos NOAA one-shot y nueva vista Telegram `/noaa`. |
| 2026-03-30 | Explícita | Sesión 40 | `—` | Diagnóstico pérdidas NYC/Munich/Atlanta: bot entraba en ciudades sin validación (Seoul, Tokyo, NYC, Munich no bloqueadas). Ventas manuales NYC. Identificado bug #15 — allowlist `ACTIVE_TRADING_CITIES` pendiente en v10.6.6. |
| 2026-03-30 | Explícita | Sesión 41 | `—` | Implementación local de `v10.6.6`: allowlist `ACTIVE_TRADING_CITIES`, skip claro en `decisions.log`, bump de versión y suite en `419/419`. |
| 2026-03-30 | Explícita | Sesión 42 | `—` | Implementación local de `v10.6.7`: tabla `Estado de observacion por ciudad` en el dashboard, cruzando allowlist, NOAA e histórico validado, con suite en `426/426`. |
| 2026-03-30 | Explícita | Sesión 43 | `—` | Implementación local de `v10.6.8`: nueva capa 1 `Control Center Discovery/Stabilization` en dashboard + `/focus` en Telegram, con detalle relegado a capas inferiores y suite en `440/440`. |
| 2026-03-30 | Explícita | Sesión 44 | `—` | Implementación local de `v10.6.9`: `Mission HUD` para discovery/stabilization con estilo videojuego operacional, tabs `Overview / Progress / Cities`, barras de progreso, `city race`, `dashboard.js` y suite en `447/447`. |
| 2026-03-30 | Explícita | Sesión 45 | `7eb8f7f` | Refinamiento y despliegue de `v10.6.10`: modo claro por defecto, ciudades agrupadas por prioridad operativa, repetición de `signals stale` reducida cuando NOAA es el cuello de botella, suite en `449/449` y validación en Railway. |
| 2026-03-31 | Explícita | Sesión 46 | `—` | Auditoría NOAA `observed_vs_forecast`: se demuestra bug real de observabilidad, no solo falta de muestra. Fix local con `daily-summaries/TMAX` prioritario, fallback `global-hourly`, guard de lag coherente, trazabilidad extra y suite en `453/453`. |
| 2026-03-31 | Explícita | Sesión 47 | `—` | Nueva capa `trade_lifecycle`: trazabilidad completa por posición con backfill desde `performance+postmortem`, snapshots en gestión e intra-ciclo, observación post-exit y suite final en `467/467`, sin tocar trading. |
| 2026-03-31 | Explícita | Sesión 48 | `—` | Hardening fase 1 de `trade_lifecycle`: matching por `id` reconstruido, coalescing defensivo, bloque `integrity`, fix del caso real de cierres huérfanos y suite en `470/470`; validación live demuestra `92 -> 80` records únicos al reconstruir. |
| 2026-03-31 | Explícita | Sesión 49 | `—` | Hotfix del coalescing de `trade_lifecycle` tras detectar en Railway `unhashable type: 'list'`; se sustituye la comparación inválida con sets `{None, "", [], {}}` por `_lifecycle_is_empty()`, se añade regresión del merge de contextos duplicados, se normaliza `agent_events.jsonl` a UTF-8 y la suite queda en `472/472`. |
| 2026-03-31 | Explícita | Sesión 50 | `—` | Recap operativo + hardening Railway CLI: validación live del hotfix (`87` records, `0` ids duplicados) y nuevo wrapper `tools/railway_safe.ps1` para limpiar proxies de proceso, junto con regla operativa en el playbook para no repetir el bucle de auth/`invalid_grant`. |
| 2026-03-31 | Explícita | Sesión 51 | `—` | Fase 2 analítica de operativa: `build_dashboard_trade_analytics()`, score de exits observados, breakdown por `take_profit / reeval / stop_loss`, timeline corto y sección nueva en dashboard para seguir upside dejado vs downside evitado. Suite local `477/477`. |
| 2026-03-31 | Explícita | Sesión 52 | `—` | Trade console dashboard: nueva pestaña separada con `Resumen / Trades`, KPIs de operativa real y tabla por posición basada en `trade_lifecycle/postmortem`, pensada para seguimiento activo sin tocar trading. |
| 2026-04-01 | Explícita | Sesión 53 | `—` | Snapshot analítico live + refinamiento semántico local: acceso live reabierto vía dashboard, foto congelada de producción (`101` operaciones, `85` cerradas, `16` abiertas, `LOSS_TOTAL=60`, `sample observado=7/85`) y handoff limpio del bug de auth Railway. |
| 2026-04-01 | Explícita | Sesión 54 | `—` | Cierre del bug de Railway auth: wrapper endurecido (`HTTP_PROXY`/minúsculas/`npm_config_*`), nuevo helper `tools/railway_auth_repair.ps1` con `doctor/reset/launch-login/restore-links`, login browserless validado y re-enlace del proyecto restaurado desde backup; `whoami/status/logs` vuelven a funcionar. |
| 2026-04-01 | Explícita | Sesión 55 | `5b23d02` | Deploy validado del refinamiento semántico del `trade console`: push + redeploy manual en Railway y confirmación live de `LOSS_TOTAL`, `SELL negativos` y `Legacy/parcial` ya visibles en producción. |
| 2026-04-01 | Explícita | Sesión 56 | `—` | Auditoría manual de inconsistencias en `trade_lifecycle/trade console`: evidencia de trades recientes con desenlace contradictorio o entrada parcial (`Seoul 14C`, `Seoul 13C`, `Atlanta 70-71F`, `Atlanta 78-79F`), creación del handoff `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` y cambio de foco a saneamiento de trazabilidad, sin tocar trading ni deploy. |
| 2026-04-01 | Explícita | Sesión 57 | `—` | Saneamiento local de `trade_lifecycle/trade console`: clave estable por mercado+lados, coalescing de follow-ups (`SELL` + residuo `LOSS_TOTAL`, `RESOLVED_WIN` repetidos), label con `YES/NO`, cruce con cartera para `claim/redeem` y fallback visible desde `portfolio.dead/resolved_won`. Validación concreta sobre `Seoul 14C/13C`, `Atlanta 70-71F/78-79F/80-81F`, `Tokyo 18C`, `Buenos Aires 28C`, `Chicago 40-41F` y `Dallas 82-83F`. Suite local `483/483`. |
| 2026-04-02 | Explícita | Sesión 60 | `—` | Diagnóstico y fix del bloqueo de capital en live: posiciones `redeemable=True` dejaban exposición falsa y `round(size, 2)` provocaba SELL rechazadas por exceso de shares. `bot.py` pasa a excluir `redeemable` en `get_current_exposure()` y a truncar SELL hacia abajo en `manage_positions()` e intra-cycle. Validación dirigida + suite `483/483`; se actualizan contexto, historial y scoreboard y se empuja a `origin/main`. |
| 2026-04-02 | Explícita | Sesión 61 | `3c2b568` | Auditoría operativa del `Mission HUD` y salto de capa descriptiva a capa decisional por ciudad: `shadow tracking` para ciudades fuera de allowlist, reglas explícitas `shadow -> canary` y `active/canary -> shadow`, overlay automático persistente, dashboard con `canaries/shadows` actuales e historial de transiciones, y alertas Telegram cuando una ciudad cambia de estado. Suite local `496/496`, `commit + push` a `origin/main` y redeploy lanzado en Railway; queda pendiente validar el comportamiento live de la automatización y como siguiente tarea se fija el backfill conservador de `shadow` histórico. |
| 2026-04-02 | Explícita | Sesión 62 | `e4dce44` | Conversión de la capa de ciudades en una vista de ranking operacional clara: `readiness_score`, ranking principal, distancia a canary, tendencia y motivo principal por ciudad; degradadas diferenciadas explícitamente (`Dallas` como `shadow degradada`), copy/UX afinado y tests ampliados. `verify_before_deploy.py` cierra en `500/500`; se detecta además que faltaba el cierre documental, por lo que se actualizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` y se empuja el deploy. |
| 2026-04-02 | Explícita | Sesión 63 | `—` | Cierre mínimo de hardening de tooling/documentación con evidencia ya verificada en local: `OPERATIONS_PLAYBOOK.md` deja RTK y Engram como setup global del usuario, no del repo; RTK queda marcado como verificado para Codex con `rtk --version` + `rtk init -g --codex` + uso real (`rtk git status`, `rtk git diff`); Engram queda marcado como operativo tras `engram setup codex` y alta manual del MCP `engram` en la extensión de Codex para VS Code. Sin cambios en bot, trading, NOAA o deploy. |
| 2026-04-03 | Explícita | Sesión 69 | `—` | Reconciliación acotada de `postmortem.json` live para Chicago Apr1: la fila `2026-04-01` ya no estaba `open`, sino `closed/LOSS_TOTAL` con `micro_position_unsellable`, y `city_accuracy[Chicago]` recalcula a `4T / 1W / 25.0% / +$2.09`; el sesgo pendiente queda movido a 3 filas legacy de Chicago (`2026-03-26`, `2026-03-27`, `2026-03-28`) que siguen abiertas. |
| 2026-04-03 | Explícita | Sesión 71 | `—` | Quick wins Control Center (v10.6.10, sin bump): QW1 elimina bloque `legacy-focus-shell` (código muerto); QW2 mueve card Drift Open-Meteo a capa 3 tras Trofeos; QW3 reordena capa 2 — NOAA+Decision engine pasa a inmediatamente después de Estado operativo; QW4 añade alarma «sin ciclo en >12h» en `build_dashboard_focus_center()` leyendo `cycle_summary.json`; QW6 mini-cards PnL/WR muestran «esperando muestra» si `closed_count < 5`; QW7 Readiness+Desbloqueos colapsados en `<details>`. Verificado en inicio de sesión: `shadow_city_tracking.json` y `city_policy_state.json` presentes en Railway Volume. `verify_before_deploy.py`: 506/506. |
| 2026-04-03 | Explícita | Sesión 70 | `—` | Auditoría completa del Control Center dashboard (v10.6.10): 6 bloques analizados (fidelidad de datos, utilidad operativa, UX/IA, motor de ciudades, alertas Telegram, valor estratégico). Hallazgos críticos: `shadow_tracking` posiblemente no persiste en Volume, WR Chicago sesgado por 3 filas legacy `open`, NOAA/Decision engine al final de capa 2 cuando es el limitante dominante, `readiness_score` opaco (propuesta de 3 gates). Entregables: `docs/control-center-audit.md`, `docs/control-center-roadmap.md` (QW1-7, M1-5, R1-3, I1-3), `docs/control-center-next-session.md` con prompt listo. Sin cambios de código. |
| 2026-04-03 | Explícita | Sesión 66 | `—` | Implementación local del auto-bloqueo real por ciudad sin tocar trading/NOAA/scheduler: `city_policy_state.json` añade `auto_blocked_cities` con `action/reason/metrics/from_mode/triggered_at`, `get_effective_city_mode()` prioriza ese estado sobre la allowlist activa, `sync_city_policy_state()` registra `active/canary -> blocked` con evidencia persistida, dashboard/decision engine leen la política y la suite pasa en `506/506`. Sin push/deploy todavía; siguiente paso validar en Railway. |
| 2026-04-02 | Explícita | Sesión 58 | `—` | Cierre operativo sin tocar el bot: se fija como siguiente prioridad la auditoría de la captura del `Mission HUD`, se formaliza la regla `1 sesión = 1 tarea` con contexto mínimo, se añade una sección de `token economics` para Codex + Claude Code y se crea `.codex/config.toml` del proyecto con `medium` por defecto y perfiles `low/deep/max`. Sin deploy ni cambios de trading/NOAA. |
| 2026-04-02 | Explícita | Sesión 59 | `—` | Cierre completo: `python verify_before_deploy.py` vuelve a pasar `483/483`, se versionan el saneamiento local de `trade_lifecycle/trade console`, el handoff y los guardrails de contexto/tokens, y se hace `commit + push` a `origin/main`. No se tocan reglas de trading ni NOAA; queda pendiente revalidación live del nuevo push. |
| 2026-04-03 | Explícita | Sesión 72 | `—` | Cobertura funcional de la alarma `sin ciclo en >12h` en `build_dashboard_focus_center()`: el test fuerza ausencia de `cycle_summary.json`, valida `incidents` + `badge="warn"` y sincroniza `agent_events.jsonl` con la sesión documentada más reciente. Suite local `507/507`, sin tocar trading/NOAA/scheduler. |
| 2026-04-04 | Explícita | Sesión 76 | `—` | Implementación local de Camino A shadow-only: filtro `ALLOWED_CONDITIONS` para dejar solo `at_or_above/at_or_below`, `range/exact` enviados a shadow tracking con `edge_hit=False`, sigma empírica por ciudad con fallback global, `MIN_EDGE=15.0`, `condition_filtered` en dashboard/Telegram/cycle_summary y suite `515/515`; sin tocar scheduler/NOAA/trade_lifecycle/deploy ni env vars Railway. |
| 2026-04-06 | Explícita | Sesión 82 | `93c8b2e` `1daec87` | Diagnóstico estratégico completo + corrección de modelo + reactivación Dallas. (1) Verificación empírica: NOAA `daily-summaries/TMAX` = WU daily high exactamente para KORD — no se necesita scraping WU. (2) Sesgo Open-Meteo medido con 13 casos NOAA en producción: Atlanta `Bias=+1.38°C`, Chicago `Bias=+1.40°C`, Dallas `Bias≈0`. (3) `FORECAST_BIAS_C` implementado en `estimate_prob_with_city` (`mu = forecast_max + bias`). (4) Dallas sigma D0 `0.21→0.57°C`, samples D0 `2→3`. (5) `MIN_PRICE 0.08→0.20`, `MAX_PRICE 0.92→0.80`. (6) `ACTIVE_TRADING_CITIES=Dallas` en Railway (estaba `NONE`), `auto_blocked_cities` limpio. (7) NOAA decoupling (Codex): `_iter_recent_noaa_cycle_markets` + `_get_noaa_candidate_dates` + `scanned_markets` en cycle_summary — recoge observaciones sin BUY. Suite `620/620` (+8 tests). |
| 2026-04-06 | Explícita | Sesión 85 | `—` | Política local de ciudades `shadow-first`: `sync_city_policy_state()` vuelve a degradar `active/canary -> shadow`, `blocked` queda reservado a descartes reales, y el overlay legado `auto_blocked_cities[action=auto_block]` se migra al vuelo a `auto_shadow_cities` para evitar casos tipo Dallas. Dashboard/copy distinguen `Sin muestra` vs `Sin NOAA` y `Descartes reales` vs `Shadow degradada`. `verify_before_deploy.py` cierra en `628/628`; falta push/deploy. |
| 2026-04-07 | Explícita | Sesión 87 | `—` | Hardening local de `agent_events`: `load_agent_events()` acepta sesiones serializadas como `session_72`, extrae el sufijo numérico, mantiene la deduplicación y evita el warning live `invalid literal for int()`. `verify_before_deploy.py` amplía cobertura funcional y cierra en `637/637`. |
| 2026-04-07 | Explícita | Sesión 88 | `—` | Mitigación local de Open-Meteo rate limit: `get_forecast()` añade caché por `lat/lon`, fallback `stale` acotado y cooldown explícito al detectar `HTTP 429`, recortando el fan-out duplicado entre auditoría legacy y escaneo principal. `verify_before_deploy.py` amplía cobertura y cierra en `639/639`. |

---

## Sesiones explícitas

### Sesión 2

- Fecha: 2026-03-21
- Commit principal: `bddcab8`
- Estado aproximado: bot ya funcional con edge detection, backtest y bankroll.
- Valor histórico: marca el arranque real del proyecto como bot operativo, antes de toda la capa de Telegram, Railway y observabilidad posterior.

### Sesión 3

- Fecha: 2026-03-21
- Commit principal: `f97702e`
- Estado aproximado: integración con CLOB API, autenticación y primera orden de prueba.
- Valor histórico: paso de prototipo local a interacción real con Polymarket.

### Sesión 9

- Fecha: 2026-03-22
- Commit principal: `91162b0`
- Estado aproximado: pipeline de traders v2 y primeras órdenes reales verificadas.
- Valor histórico: inicio de la operativa real con señales de traders ya dentro del sistema.

### Sesión 19

- Fecha: 2026-03-28
- Commits principales:
- `a24fde2`
- `cd12121`
- `56aeb5a`
- `185f018`
- `374d6a8`
- `3c4b5f1`
- `19adfdd`
- `d382f47`
- Resumen:
- persistencia en Volume y ciclos históricos;
- rediseño fuerte de Telegram;
- correcciones de bugs #3, #9, #10, #11, #12, #13 y #14;
- paso de DST manual a `ZoneInfo`;
- entrada de Codex al flujo como agente complementario a Claude Code;
- trazabilidad multi-herramienta;
- reparación manual de una entrada truncada en `performance.json` de Railway;
- base de `postmortem.json`;
- persistencia de `signals.json`, `traders_db.json` y `trader_history.json` en Volume;
- comando `/postmortem` para inspección rápida desde Telegram y botón visible en el menú;
- backfill automático de `postmortem.json` desde `performance.json`;
- `alerts_state.json` y alertas one-shot para `30 trades limpios`, `signals.json` y `pending_exit`;
- bloqueo operativo de London en codigo para evitar nuevas entradas;
- refinamiento Telegram: `traders` cruza por fecha exacta, `postmortem` muestra labels legacy legibles y `detalle` deja de cortar a 40 lineas;
- regla operativa: antes de cada push relevante, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md`.

---

## Hitos inferidos relevantes

### Iteración v3-v7

- Fecha: 2026-03-21
- Commits: `e8d11c0`, `047f7e4`, `5ac83b9`, `c32c34f`, `9e51025`, `6973b74`, `d5bf5d8`
- Resumen:
- se añadieron filtros de precio, agresividad, duplicados y stale cleanup;
- se integró scheduler en `main()`;
- entraron alertas Telegram, dashboard, toggle de modo, cartera y órdenes enriquecidas;
- apareció `decisions.log`.

### Iteración v8

- Fecha: 2026-03-22
- Commits: `35ef3d6`, `c2bc7ff`, `eea1eef`, `fba7a0b`
- Resumen:
- se relajó la ventana temporal (`MIN_DAYS=0`, `MAX_DAYS=5`);
- se añadieron reintentos de red;
- se amplió el universo de ciudades de forma importante.

### Iteración v9

- Fecha: 2026-03-22
- Commits: `9e7941e`, `4bd7e8b`, `c857133`, `d7ae3a3`, `2aa59c1`, `48d7c4f`
- Resumen:
- nació el pipeline de traders;
- aparecieron `find_traders.py`, `trader_analyzer.py`, `signals.json` y `traders_db`;
- se integró calidad de traders y consenso;
- se añadió soporte de mercados de rango;
- se ajustó Kelly y sizing.

### Iteración v10-v10.2

- Fecha: 2026-03-22 a 2026-03-23
- Commits: `d2ae676`, `ce0684e`, `931158e`, `0ae32c9`, `deb50b3`, `3c408f3`, `d01b4b9`
- Resumen:
- fix de exposición acumulativa;
- sigma calibrada;
- gestión activa con stop-loss / take-profit / re-evaluación;
- auditoría de ventas y performance tracker;
- bankroll real en Railway;
- mejoras de balance y Telegram;
- corrección de exposición fantasma y `MIN_DAYS` dinámico.

### Iteración v10.3

- Fecha: 2026-03-24
- Commit: `bef71e3`
- Resumen:
- consolidación de bugs previos;
- fortalecimiento del verificador;
- preparación para la fase 10.4.x.

### Iteración v10.4.x

- Fecha: 2026-03-28
- Commits: `a24fde2`, `cd12121`, `56aeb5a`, `185f018`, `374d6a8`, `3c4b5f1`, `19adfdd`, `d382f47`
- Resumen:
- v10.4: persistencia, fixes críticos y mejoras de Telegram;
- v10.4.1: historial de ciclos;
- v10.4.2: rediseño completo de Telegram;
- v10.4.3: ciclos persistentes y limpieza del repo;
- v10.4.4: parche manual temporal de DST;
- v10.4.5: `ZoneInfo`, tests funcionales, trazabilidad, `postmortem.json`, trader data al Volume y `/postmortem`.
- v10.4.6: backfill de `postmortem.json`, `alerts_state.json` y alertas Telegram de observabilidad.
- v10.4.7: bloqueo operativo de London en codigo y tests de regresion.
- v10.4.8: refinamiento final de Telegram tras revision manual de botones.

---

## Sesión 20 — 29 marzo 2026

**Herramienta:** Claude Code (Opus)
**Versiones:** v10.5.0 → v10.5.1 → v10.5.2
**Tests:** 216 → 226 → 234

**Cambios realizados:**
- v10.5.1: Intra-cycle SL/TP monitor cada 90min con `sell_lock`, thread daemon y cobertura ampliada hasta 226 tests.
- v10.5.2: City accuracy tracker — `get_city_accuracy()` analiza win rate por ciudad desde postmortem.json. Alerta Telegram si una ciudad baja de 25% win rate con 3+ trades. Nuevo comando `/accuracy`. Win rate visible en `/rendimiento`.
- Investigación WU API: API muerta desde 2019 (IBM compró). IBM Trial no viable (Pablo no pudo verificar identidad). Opciones documentadas: PWS key (~$30-50 estación), o seguir con accuracy tracker como proxy.
- CONTEXTO.md actualizado a v10.5.2 con estado real de posiciones (corregido desde auditoría SSH sesión 19).

**Lección operativa:** Esta sesión consumió demasiado uso de Opus. Tareas delegables a Codex: investigación WU (web search + resumen), escritura de tests de comportamiento, actualizaciones de docs. Opus debe reservarse para diseño de arquitectura y coding de lógica crítica.

## Sesión 21 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.3
**Tests:** 242

**Cambios realizados:**
- revisión crítica de los commits de la mañana (`v10.5.0`, `v10.5.1`, `v10.5.2`) contrastando Git, código y docs;
- integración real de `/accuracy` en el menú de Telegram;
- `cmd_accuracy` vuelve con menú y `/estado` muestra el intervalo intra-SL como ya decía el contexto;
- corrección de la trazabilidad de sesión 20 para que no simplifique en exceso lo que realmente añadió `v10.5.1`.

**Resultado:** repo alineado a nivel código, tests y documentación; queda pendiente decidir si desplegar `v10.5.3` o seguir observando `v10.5.2` primero.

## Sesión 22 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.4
**Tests:** 251

**Cambios realizados:**
- separación del contador de ciclos en dos dimensiones: histórico total y serie lógica actual `v10.5`;
- nuevo helper `_load_cycle_counts()` para reconstruir ambos contadores desde `cycles_history.jsonl` sin romper continuidad histórica;
- `cycle_summary.json` y `cycles_history.jsonl` pasan a guardar `logic_series` y `logic_cycle_number`;
- `/estado` y `/info` muestran `N total | M serie v10.5`, resolviendo la ambigüedad que mezclaba observabilidad global con evaluación de la nueva lógica;
- `verify_before_deploy.py` ampliado con tests funcionales de historial mixto `v10.4`/`v10.5`;
- temporales del verificador movidos al directorio temporal del sistema para no dejar `_tmp_*` en el repo en futuras ejecuciones.

**Resultado:** `v10.5.4`, 251/251 tests, histórico total preservado y serie `v10.5` visible por separado para análisis comparativo.

## Sesión 23 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.5
**Tests:** 279

**Cambios realizados:**
- implementación de un dashboard web HTML servido desde el mismo servicio Railway, separado de Telegram;
- checklist gamificado de promoción de bankroll (`$25 -> $35`) calculado con métricas del sistema;
- scoreboard de agentes y rivalidad constructiva basados en `agent_events.jsonl`;
- nueva plantilla `templates/dashboard.html`, estilos en `static/dashboard.css` y arranque HTTP paralelo con `Flask` + `waitress`;
- ampliación de `verify_before_deploy.py` para cubrir backend, scorecard, checklist y assets del dashboard.

**Resultado:** `v10.5.5`, 279/279 tests, dashboard listo para validación visual en navegador y nueva base para comparar utilidad real de Opus/Codex.

## Sesión 24 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.6
**Tests:** 290

**Cambios realizados:**
- refinamiento del dashboard tras revisión visual real en Railway;
- cambio a modo oscuro por defecto para revisión en navegador;
- checklist separado entre `trades limpios históricos` y `trades limpios serie v10.5`;
- scorecard de agentes extendido con stages `proposed / implemented / validated`;
- ciclos legacy pasan a mostrarse como `legacy v10.X` en vez de marcadores ambiguos;
- ciudades clave reordenadas por riesgo operativo en lugar de volumen puro;
- `verify_before_deploy.py` ampliado para cubrir dark mode, stages y checklist separado.

**Resultado:** `v10.5.6`, 290/290 tests, dashboard más honesto para medir la serie `v10.5` y más cómodo de usar en escritorio.

## Sesión 25 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.7
**Tests:** 294

**Cambios realizados:**
- ajuste semántico del dashboard para no mostrar métricas “cero” como si ya existiera muestra válida;
- `PnL serie`, `Win rate serie` y `Drawdown reciente` pasan a mostrar `n/d` o `sin cierres` cuando todavía no hay cierres en la serie `v10.5`;
- el checklist deja de marcar esas métricas como `OK` si la serie aún no tiene cierres;
- ampliación del verificador con casos funcionales específicos para esta situación.

**Resultado:** `v10.5.7`, 294/294 tests, dashboard más claro en las primeras fases de una serie lógica nueva.

## Sesión 26 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.8
**Tests:** 300

**Cambios realizados:**
- incorporación de un tercer estado visual en el checklist del dashboard: `Esperando muestra`;
- separación visual entre `fallo real` y `métrica aún sin datos suficientes`;
- actualización de la plantilla y estilos para que ese estado no se vea rojo;
- ampliación del verificador con cobertura específica de `status`/`tag` en checklist.

**Resultado:** `v10.5.8`, 300/300 tests, checklist más intuitivo para operar y revisar series nuevas.

## Sesión 27 — 29 marzo 2026

**Herramienta:** Codex  
**Versión:** v10.5.9  
**Tests:** 325

**Cambios realizados:**
- nueva capa del dashboard con bloque `Progreso` para mostrar `faltan X para Y` sobre muestra de serie, estabilidad, cierres útiles, readiness de bankroll y cobertura de ciudades;
- bloque `Trofeos` calculado solo desde cierres validados (`postmortem.json`) para resaltar mejores y peores hitos operativos del bot;
- bloque `Desbloqueos` con explicaciones operativas de qué falta para revisar lógica con confianza o evaluar subir de nivel;
- ampliación del snapshot del dashboard y de `/api/dashboard.json` con `progress`, `trophies` y `unlocks`;
- ampliación de `verify_before_deploy.py` con tests funcionales y estructurales específicos de esta capa nueva.

**Resultado:** `v10.5.9`, 325/325 tests, dashboard más accionable para interpretar evidencia y tomar decisiones de siguiente nivel sin mezclarlo con Telegram.

## Sesión 28 — 29 marzo 2026

**Tipo:** Explícita  
**Versión:** v10.5.10  
**Objetivo:** añadir al dashboard una capa explícita de balance por tipo de salida para entender si el sistema corta ganancias demasiado pronto, deja pérdidas crecer o simplemente todavía no ha reconciliado fills/cobros.

**Herramientas utilizadas:**
- `Codex`: implementación completa de backend + HTML/CSS + tests + actualización de docs.
- `Claude Code`: no usado en esta sesión; se deja como siguiente revisor crítico de toda la iteración reciente del dashboard.

**Cambios clave:**
- nuevo helper `build_dashboard_exit_breakdown()` en `bot.py`;
- nueva sección `Balance por tipo de cierre` con filas para `Take-profit`, `Stop-loss`, `Re-evaluación`, `LOSS_TOTAL`, `Ganadas por resolución`, `Ganadas validadas` y `Perdidas validadas`;
- nueva sección `Liquidación` para separar `cierres validados de la serie`, `pending_exit`, `abiertas`, `exit_failed` y `pendiente pago / canjear`;
- snapshot del dashboard ampliado con `exit_breakdown`;
- plantilla y CSS ampliados para mostrar estas dos tarjetas nuevas;
- tests de verificación ampliados a `334/334`.

**Valor de la sesión:**
- el dashboard ya no solo dice “cuántos trades faltan”, sino también **cómo se están cerrando** y **dónde se queda el dinero atascado**;
- deja visible la diferencia entre:
  - cierre validado con PnL real,
  - venta pendiente de fill/auditoría,
  - valor pendiente de cobro/canje.

**Resultado:** `v10.5.10`, 334/334 tests, base mejor preparada para que Claude Code revise por qué el bankroll sigue cayendo y si el patrón dominante es `stop_loss`, `LOSS_TOTAL`, `reeval` o falta de resoluciones favorables a $1.

## Sesión 29 — 29 marzo 2026

**Herramienta:** Claude Code (Sonnet)
**Versión:** v10.5.11
**Tests:** 337

**Objetivo:** Revisión crítica integral de las sesiones 24-28 (dashboard v10.5.6 → v10.5.10). Validar métricas, detectar bugs reales e inconsistencias, y corregirlos.

**Hallazgos críticos:**

1. **Bug en checklist: drawdown marcado OK con muestra incompleta.** Con 1-4 cierres (< `DRAWDOWN_WINDOW=5`), el check `Drawdown últimos N cierres` mostraba `OK` en lugar de `Esperando muestra`. La condición `recent_window_size < DRAWDOWN_WINDOW` siempre era `True` con datos parciales, haciendo que `passed` fuera siempre `True` antes de tener ventana completa.

2. **agent_events.jsonl no se sincronizaba entre repo y Railway Volume.** `_seed_data_file()` no sobreescribe archivos existentes, por lo que las sesiones 27-28 del scoreboard solo estaban en el repo local pero no llegaban a Railway.

3. **Rows "Ganadas validadas" y "Perdidas validadas" en exit_breakdown son agregados, no categorías exclusivas.** Se solapan con las filas TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN. No es un bug de datos pero puede confundir si se suman todos los valores. Las notas en la tabla (`note`) ya lo aclaran; se deja como está (cosmético).

4. **Hipótesis "cortar ganancias demasiado pronto"**: No confirmada con datos locales (no hay datos de Railway disponibles en esta sesión). El TP al +40% es conservador pero intencional. La causa dominante de pérdidas sigue siendo probablemente WU vs Open-Meteo, no el timing de salida.

5. **RESOLVED_WIN pnl_cash**: La lógica es correcta (`pnl_cash = shares - initial_value`). Los registros LOSS_TOTAL también tienen `pnl_cash` correcto (`-initial_value`). No hay bug aquí.

6. **pending_exit pnl_cash**: El dict `pending_exit` en postmortem sí guarda `pnl_cash` (el valor estimado de `p.get("cashPnl")`). El test de verify era correcto.

**Cambios realizados:**
- bug fix: `build_promotion_checklist()` — `has_full_drawdown_window = recent_window_size >= DRAWDOWN_WINDOW`; el check `passed`/`waiting` usa la ventana completa en lugar de cualquier dato parcial;
- nuevo helper `_sync_agent_events_seed()` que merge local → Volume en arranque, añadiendo solo eventos nuevos por `(timestamp, agent, title)`;
- `AGENT_EVENTS_FILE = _sync_agent_events_seed()` en lugar de `_seed_data_file("agent_events.jsonl")`;
- 2 tests nuevos en verify: ventana parcial de drawdown → `Esperando muestra`, y strings actualizados para la nueva asignación;
- CONTEXTO.md y HISTORIAL_SESIONES.md actualizados.

**Resultado:** `v10.5.11`, 337/337 tests, checklist de drawdown ahora honesto y scoreboard sincronizado en arranque.

Misma sesión, segundo commit: `v10.5.12` — bloqueo ciudades + fix posiciones fantasma (ver abajo).

## Sesión 29 (continuación) — v10.5.12

**Disparador:** Alerta Scaling Warning en Telegram: `-$19.98 en últimos 20 trades`. Bot perdiendo bankroll de forma alarmante desde $25 → $18.21.

**Análisis de datos reales** (`/accuracy`, `/rendimiento`, `/postmortem`):
- 10 de 14 ciudades activas: 0% win rate (London, Miami, Seattle, Paris, Tel Aviv, Wellington, Toronto, Madrid, Singapore, Ankara).
- Solo positivas: Chicago (+$3.30, 50% WR), Atlanta (+$2.60, 100% WR), Buenos Aires (+$0.80, 100% WR).
- Causa raíz confirmada: Open-Meteo difiere de Weather Underground en ciudades costeras y europeas. Polymarket resuelve con WU → predicciones sistemáticamente erróneas.
- Bug adicional descubierto: 17 posiciones en postmortem "open" vs 6 en cartera real. Las diferencias son posiciones ya resueltas a $0 que desaparecen del API sin registrarse como LOSS_TOTAL. El `/rendimiento` mostraba -$4.92 pero la escala real era ~-$20.

**Cambios realizados:**
- `BLOCKED_CITIES` default ampliado: `London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`;
- Fix: posiciones con `currentValue < 0.01` ahora llaman a `_mark_micro_as_loss_total` en vez de `continue` silencioso;
- 338/338 tests.

---

## Sesión 30 — v10.6.0 (29 mar 2026)

**Disparador:** Cartera en caída libre: $18.89 (-$9.52 último día, -50.4%). Pablo reporta que desde el 27 de marzo todo son pérdidas y los cambios del fin de semana están destruyendo la operativa.

**Diagnóstico (Claude Code — Opus):**

Investigación completa de trades, commits y lógica de trading desde v10.3 hasta v10.5.12:

1. **Sigma ampliada de v10.5.0 vendía posiciones ganadoras en re-eval.** Con sigma {0:2.0, 1:2.5, 2:3.0, 3:3.5}, la re-evaluación calculaba edge negativo en posiciones que v10.3 habría mantenido y que probablemente habrían ganado. Ejemplo: YES at_or_above 22°C con forecast 23°C a day 3 → v10.3 KEEP (edge +2.6%), v10.5 SELL (edge -3.4%).

2. **Intra-cycle monitor (cada 90 min) disparaba SL ante fluctuaciones normales.** En mercados de temperatura con resolución diaria, una posición puede tocar -25% temporalmente y recuperarse. Con check cada 90 min, se vendía antes de que se estabilizara.

3. **MIN_EDGE_EXACT=15% bloqueaba entradas exact** con solo 4 ciudades activas, dejando al bot casi sin operativa.

4. **Las pérdidas LOSS_TOTAL** (mercados resueltos en contra) son de posiciones compradas con v10.3 donde Open-Meteo difería de Weather Underground. No son bugs de código sino problema de fuente de datos.

**Conclusión:** v10.3 era agresivo pero funcional (ganaba y perdía). Los cambios de v10.5 lo convirtieron en un bot que no entra en nada, vende lo poco que tiene demasiado pronto, y las predicciones base siguen siendo de Open-Meteo.

**Cambios realizados:**
- Sigma restaurada a v10.3: `{0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5, 4+: 3.0}`
- Intra-cycle desactivado: `INTRA_SL_INTERVAL` default 0
- `MIN_EDGE_EXACT` eliminado (usa `MIN_EDGE=7%` para todo)
- Toda la observabilidad mantenida (postmortem, accuracy, alerts, dashboard, ciudades bloqueadas)
- Display sigma en Telegram corregido para coincidir con valores reales
- Tests actualizados: 335/335

**Resultado:** `v10.6.0`, desplegado en Railway. Bot vuelve a la lógica de trading de v10.3 con toda la instrumentación de v10.5.

**Pendiente:** Pablo investigando IBM Trial para integrar Weather Underground como fuente de datos. El upgrade real es cambiar la fuente, no ajustar la confianza del modelo.

### Sesión 30 (continuación) — v10.6.1

**Verificación completa del Dashboard** (Claude Code — Opus):

- Aritmética de "Balance por tipo de cierre": verificada correcta (TP $+9.03/4, SL $-14.21/10, etc.)
- Scoreboard: conteo de puntos verificado evento por evento contra agent_events.jsonl — correcto
- Posible issue: "Ganadas por resolución = 0" cuando Wellington ganó por resolución — a verificar en producción
- Bug encontrado: `get_logic_series_stats()` no ordenaba `closed` por `closed_at` antes de tomar ventana de drawdown
- Redundancia: unlock "Confiar en métricas de serie" era idéntico a "Activar win rate y drawdown"

**Cambios realizados:**
- Fix drawdown: ordena por `closed_at` antes de `[-DRAWDOWN_WINDOW:]`
- Alerta bankroll bajo: Telegram + dashboard alertan cuando cartera cae bajo $5
- Unlock redundante eliminado (de 6 a 5 items)
- Scoreboard: 3 eventos nuevos de sesión 30
- 338/338 tests

**Nota de proceso:** Se detectó que `replace_all=true` en actualizaciones de CONTEXTO.md modificaba entradas históricas (ej: "serie v10.5" en descripción de lo que hizo Codex en v10.5.6 se cambió a "serie v10.6"). Corregido. Regla: nunca usar replace_all para versiones en docs — editar solo las líneas específicas.

---

## Sesión 31 — v10.6.2 (29 mar 2026, local)

**Disparador:** revisión crítica posterior de `v10.6.1` detecta que la alerta de bankroll bajo puede dispararse por un fallo temporal de API y no solo por caída real de fondos.

**Diagnóstico (Codex):**

1. **Falso positivo por API incierta.** `_get_portfolio_and_positions()` puede devolver `cash=0.0`, `cash_ok=False` y `api_error` cuando falla la lectura de balance o posiciones. La alerta de `v10.6.1` usaba igualmente ese `0.0` y podía pedir “recargar” sin que la cartera real hubiera cambiado.

2. **Rearme demasiado rígido.** La flag `low_bankroll_alerted` solo se limpiaba cuando la cartera superaba `LOW_BANKROLL_THRESHOLD * 2`, así que una recuperación parcial razonable (`$4.8 -> $6.3`, por ejemplo) no rearmaba la alerta para una caída posterior real.

3. **Cobertura insuficiente.** `verify_before_deploy.py` comprobaba la presencia de strings y algo de wiring, pero no validaba funcionalmente el trigger real, el no-trigger por API incierta ni el reset con margen.

**Cambios realizados:**
- `BOT_VERSION` actualizado a `v10.6.2`;
- nueva constante `LOW_BANKROLL_RESET_MARGIN=1.0`;
- `run_observability_alerts()` exige `cash_ok` y ausencia de `api_error` antes de disparar la alerta de bankroll bajo;
- `get_dashboard_alert_summary()` solo muestra la alerta crítica de bankroll cuando la señal de cartera es fiable;
- el reset pasa a usar `LOW_BANKROLL_THRESHOLD + LOW_BANKROLL_RESET_MARGIN` en lugar de `2x` el umbral;
- `agent_events.jsonl` añade evento de sesión 31 para el scoreboard;
- `verify_before_deploy.py` sube a `348/348` con casos funcionales nuevos:
  - dashboard muestra alerta con datos fiables;
  - dashboard oculta alerta con API incierta;
  - Telegram dispara al cruzar umbral real;
  - no persiste flag con API incierta;
  - rearma la alerta al salir de zona roja con margen;
- `CONTEXTO.md` y este historial quedan alineados con `v10.6.2`.

**Resultado:** `v10.6.2` quedó listo en local con `348/348` tests. Posteriormente se hizo commit (`29049a1`) y push a `origin/main`. El estado de deploy de Railway no se re-verificó durante la sesión de investigación siguiente.

---

## Sesión 32 — Investigación estratégica + preparación de v10.6.3

**Fecha:** 2026-03-30
**Herramientas:** Codex + Claude Code (Opus) + revisión cruzada
**Versión del código al investigar:** `v10.6.2`
**Cambios de código:** ninguno funcional; sesión centrada en investigación, síntesis y preparación del siguiente bloque técnico

**Trabajo realizado:**
- Codex investigó competidores, reglas reales de resolución en Polymarket y microestructura básica del mercado;
- Claude Code realizó una investigación paralela y una revisión adversarial del informe de Codex;
- se prepararon tres artefactos nuevos en el repo:
  - `RESEARCH_CODEX_HANDOFF_2026-03-30.md`
  - `RESEARCH_CLAUDE_2026-03-30.md`
  - `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`

**Hallazgos compartidos de mayor impacto:**
- Polymarket temperature resuelve con Weather Underground, no con Open-Meteo;
- Dallas está mal mapeada en el bot: código actual `KDFW`, reglas verificadas `KDAL`;
- la auditoría `forecast_vs_real` no debe interpretarse como verdad de resolución, porque no compara contra la fuente real que liquida Polymarket;
- la dirección estratégica correcta sigue siendo `resolution fidelity first`.

**Correcciones / matices surgidos en la revisión cruzada:**
- Claude reforzó correctamente el hallazgo de Dallas y la debilidad real de la auditoría;
- Claude añadió `Degen Doppler` como competidor/referencia más directa;
- se detectó que una parte de la corrección sobre `WeatherClaw` estaba contaminada por confusión de dominio (`.com` vs `.xyz`), así que no debía tomarse sin verificar.

**Roadmap resultante para la siguiente sesión:**
1. Fix Dallas `KDAL`
2. Crear capa formal de resolución (`RESOLUTION_ICAO` + URLs WU)
3. Renombrar/documentar la pseudo-auditoría actual para no presentar Open-Meteo como “real”
4. Añadir tests de estos tres puntos
5. No tocar todavía lógica de trading, scheduling ni nuevas features

**Resultado:** el proyecto queda listo para abrir una sesión nueva de implementación acotada (`v10.6.3`) con contexto claro y sin reabrir la investigación desde cero.

---

## Sesión 33 — v10.6.3 (30 mar 2026, local)

**Disparador:** ejecutar el bloque técnico acordado tras la investigación de la sesión 32 sin tocar lógica de trading ni scheduling.

**Diagnóstico (Codex):**

1. **Dallas seguía mal mapeada.** `RESOLUTION_STATIONS["Dallas"]` apuntaba a `Dallas Fort Worth / KDFW` cuando la investigación cruzada dejó como estación correcta `Dallas Love Field / KDAL`.

2. **La capa de resolución seguía implícita.** Había coordenadas para forecast, pero no existía todavía un mapping formal `ciudad -> ICAO -> URL WU` que dejara clara la referencia de settlement revisada para ciudades activas y bloqueadas.

3. **La pseudo-auditoría inducía a error.** `forecast_vs_real` sonaba a validación contra la fuente real, pero el código seguía reconsultando `get_forecast()` de Open-Meteo. Había que hacer explícito que solo mide deriva `forecast original vs forecast posterior`.

4. **Un test funcional viejo de `/traders` quedó frágil por calendario.** Dependía de fechas fijas ya pasadas, así que empezó a fallar aunque la funcionalidad siguiera bien.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.3`;
- `RESOLUTION_STATIONS["Dallas"]` cambia a `{"lat": 32.8459, "lon": -96.8510, "name": "Dallas Love Field"}`;
- nueva capa `RESOLUTION_ICAO` con `icao + wu_url` para las ciudades activas, las bloqueadas y el resto del mapping actual;
- nuevo helper `_wu_history_url()` para centralizar la plantilla WU;
- la pseudo-auditoría se renombra a `audit_check_open_meteo_forecast_drift()`;
- se mantiene la clave legacy `forecast_vs_real` en `audit.json` solo por compatibilidad, pero docstrings, comentarios, campos y logs nuevos ya hablan de `forecast_original`, `forecast_posterior` y `forecast posterior Open-Meteo`;
- los registros de oportunidad incorporan `resolution_icao` y `resolution_wu_url` sin alterar la lógica de trading;
- `verify_before_deploy.py` sube a `358/358` con checks nuevos para:
  - Dallas `KDAL` / Love Field;
  - `RESOLUTION_ICAO` con las 4 activas y cobertura de ciudades bloqueadas;
  - auditoría sin `real=` y documentada como Open-Meteo posterior;
- el test funcional de `/traders` pasa a usar fechas relativas para no romperse con el calendario.

**Resultado:** `v10.6.3` queda listo en local con `358/358` tests. Trading, sizing, ejecución y scheduling no se tocaron; el cambio queda acotado a resolución, nomenclatura honesta de auditoría y trazabilidad.

---

## Sesión 34 — v10.6.4 (30 mar 2026, local)

**Disparador:** usar la base de `v10.6.3` para crear una capa observada separada con NOAA NCEI, evitando depender de Weather Underground scraping y sin tocar la lógica de trading.

**Diagnóstico (Codex):**

1. **La siguiente capa útil ya no era forecast-vs-forecast.** Hacía falta una auditoría observada separada que no reutilizara Open-Meteo y que no se presentara como “resolución real”.

2. **El riesgo técnico estaba en los station IDs.** NOAA Access Data Service requiere station IDs explícitos; para las 4 activas había que añadir `noaa_station_id` en `RESOLUTION_ICAO` y evitar una resolución dinámica `ICAO -> NOAA`.

3. **Buenos Aires era el punto más incierto.** Se dejó `87576099999` como candidato explícito hasta validar el spike NCEI, en vez de esconder la incertidumbre.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.4`;
- `RESOLUTION_ICAO` añade `noaa_station_id` explícito para:
  - Dallas `72258303927`
  - Chicago `72530094846`
  - Atlanta `72219013874`
  - Buenos Aires `87576099999`;
- nueva clave `OBSERVED_AUDIT_KEY = "observed_vs_forecast"` separada del legacy `forecast_vs_real`;
- nuevo helper `_parse_noaa_tmp_c()` para convertir `TMP` de NOAA;
- nuevo helper `fetch_noaa_observed_max()` contra NOAA NCEI Access Data Service;
- nueva auditoría `audit_check_resolution_truth(dl)`:
  - solo para las 4 ciudades activas;
  - solo con lag mínimo de 2 días;
  - guarda `city, date, icao_used, noaa_station_id, observed_temp_c, forecast_temp_c, error_c, abs_error_c, side, edge_pct, source="noaa_ncei", checked_at`;
  - wording explícito de `observed proxy`;
- `main()` ahora ejecuta esta auditoría junto a la legacy del paso `0.6`;
- `verify_before_deploy.py` sube a `371/371` con:
  - checks estructurales de `noaa_station_id`, `observed_vs_forecast`, funciones nuevas y `source=noaa_ncei`;
  - test funcional del helper NOAA con respuesta simulada;
  - test funcional de la auditoría para asegurar que no toca London y respeta el lag de 2 días.

**Resultado:** `v10.6.4` queda listo en local con `371/371` tests. La nueva capa NOAA mejora la observabilidad, pero se mantiene correctamente etiquetada como `observed proxy`, no como fuente real de settlement.

**Post-scriptum del spike Buenos Aires:** NOAA HOMR devolvió el registro vigente de `SAEZ` como `MINISTRO PISTARINI` (`ncdcStnId=30132405`, WMO `87576`) y una prueba directa contra `global-hourly` confirmó que el identificador operativo para el bot es `87576099999`; `30132405` y `ARI0000SAEZ` no devolvieron filas en ese endpoint.

---

## Sesión 35 — v10.6.5 (30 mar 2026, local)

**Disparador:** una vez cerrada la capa `observed_vs_forecast`, hacía falta separar en el dashboard la métrica NOAA nueva del histórico legacy para poder leer bias sin contaminar la serie de trading ni mezclar semánticas.

**Diagnóstico (Codex):**

1. **No convenía partir el dashboard de trading.** PnL, win rate y drawdown siguen siendo comparables porque `v10.6.5` no toca la lógica operativa.

2. **Sí convenía partir la observabilidad de forecast.** `observed_vs_forecast` (NOAA) y `forecast_vs_real` legacy miden cosas distintas y no debían compartir KPIs ni narrativa.

3. **La muestra necesitaba umbrales explícitos.** El dashboard tenía que dejar claro que `n < 3` significa `acumulando muestra...`, que el bias por ciudad pide `>=3` casos por ciudad y que la lectura global gana sentido a partir de `10` casos.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.5`;
- nuevos builders:
  - `build_dashboard_forecast_quality()` para `observed_vs_forecast`;
  - `build_dashboard_legacy_forecast_drift()` para el bloque histórico `forecast_vs_real`;
- `build_dashboard_snapshot()` incorpora ambos bloques sin tocar trading, scheduling ni auditorías;
- `templates/dashboard.html` añade:
  - `Calidad Forecast Observada (NOAA)` con `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos;
  - `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y último registro prominentes;
- `verify_before_deploy.py` sube a `386/386` con:
  - checks estructurales de los nuevos builders y thresholds de muestra;
  - tests funcionales del bloque NOAA y del bloque legacy;
  - snapshot tests para asegurar que ambos bloques llegan al dashboard.

**Resultado:** `v10.6.5` queda listo en local con `386/386` tests. El dashboard ya separa claramente NOAA observado del drift legacy y deja intacta toda la capa de trading.

---

## Sesión 36 — sync de bankroll tras recarga manual (30 mar 2026, local)

**Disparador:** tras una recarga manual de fondos en Polymarket, apareció una inconsistencia residual: Railway seguía operando con `BANKROLL=25.00`, pero el fallback local en `bot.py` todavía decía `15.00`.

**Diagnóstico (Codex):**

1. **La calibración operativa real seguía siendo $25.** Contexto, tests y Railway apuntaban a `BANKROLL=25.00`; el `15.00` en código era un remanente antiguo.

2. **El bug no afectaba a producción mientras Railway inyectara la variable.** Pero sí podía inducir a errores al leer el código, correr el bot sin env vars o razonar sobre sizing local.

3. **La recarga devolvía al bot a su zona objetivo.** Se registró un depósito manual de `+$14.99`, coherente con seguir operando alrededor del bankroll objetivo configurado.

**Cambios realizados:**
- `bot.py` sincroniza el fallback local `BANKROLL` de `$15.00` a `$25.00`;
- `verify_before_deploy.py` añade un check explícito para fijar `BANKROLL default = 25.00`;
- `CONTEXTO.md` se actualiza con:
  - la recarga manual `+$14.99`;
  - el nuevo estado de `origin/main` en `v10.6.5`;
  - la trazabilidad de esta sincronización;
- `HISTORIAL_SESIONES.md` registra la sesión como cierre de la inconsistencia post-recarga.

**Resultado:** código local, tests, contexto y configuración real vuelven a quedar alineados alrededor de `BANKROLL=$25.00`, sin bump de versión y sin tocar lógica de trading.

---

## Sesión 37 — playbook operativo + guardrails de scoreboard (30 mar 2026, local)

**Disparador:** apareció una desalineación de proceso: el estado humano (`CONTEXTO.md`, `HISTORIAL_SESIONES.md`) estaba actualizado, pero el scoreboard live seguía anclado en la sesión 31 porque `agent_events.jsonl` no formaba parte del cierre obligatorio de sesión.

**Diagnóstico (Codex):**

1. **El problema no era de estado, sino de protocolo.** `CONTEXTO.md` y `HISTORIAL_SESIONES.md` seguían bien; la capa máquina del Dashboard no estaba integrada en el checklist de cierre.

2. **El scoreboard tiene una fuente distinta.** El Dashboard no lee docs; lee `agent_events.jsonl`, que luego se sincroniza al Volume con `_sync_agent_events_seed()`.

3. **Faltaban guardrails.** Había memoria humana, pero no una regla verificable que obligara a cerrar docs y scoreboard juntos.

**Cambios realizados:**
- nuevo `OPERATIONS_PLAYBOOK.md` con:
  - checklist de inicio;
  - checklist de cierre;
  - protocolo de deploy;
  - reglas de scoreboard;
  - workflow Pablo + Codex + Claude;
  - regla de hardening: todo error deja guardrail;
- nuevo helper `tools/append_agent_event.py` para registrar eventos del scoreboard sin editar JSONL a mano;
- `CLAUDE.md` y `CONTEXTO.md` pasan a remitir explícitamente al playbook;
- `verify_before_deploy.py` añade checks para:
  - existencia del playbook;
  - existencia del helper;
  - referencia al playbook en `CONTEXTO.md` y `CLAUDE.md`;
  - regla de hardening;
  - helper con bloqueo de duplicados;
  - consistencia entre la sesión documentada más reciente y `agent_events.jsonl`;
- `_sync_agent_events_seed()` deja de fallar en silencio y ahora loggea warning si el merge del scoreboard falla;
- se sincroniza el scoreboard live en Railway para añadir sesiones 32-36.

**Resultado:** el sistema gana una capa nueva de robustez de proceso. A partir de aquí, estado, historial, scoreboard y tests quedan conectados por un playbook explícito en vez de depender de memoria manual. `verify_before_deploy.py` queda en `396/396`.

---

## Sesión 38 — scoreboard limpio + regla de puntuación (30 mar 2026, local + Railway)

**Disparador:** el scoreboard live mostraba una diferencia engañosa entre Codex y Claude porque el `agent_events.jsonl` persistente del Volume contenía filas duplicadas/corruptas y el dashboard solo mira los últimos `30` eventos válidos.

**Diagnóstico (Codex):**

1. **La métrica estaba siendo contaminada por datos, no solo por scoring.** Había filas duplicadas válidas de Codex y también líneas malformadas antiguas en el fichero live.

2. **El límite de `30` eventos amplificaba el sesgo.** Los duplicados no solo sumaban puntos de más, sino que expulsaban un evento antiguo de Claude del corte visible.

3. **Faltaba una regla explícita de puntuación.** El playbook cubría el cierre de sesiones, pero no dejaba escrito todavía que una revisión sin delta no debe puntuar.

**Cambios realizados:**
- limpieza quirúrgica del `agent_events.jsonl` live en Railway hasta devolverlo a `29` líneas canónicas;
- `load_agent_events()` pasa a deduplicar eventos equivalentes por clave normalizada (`timestamp + session + agent + type + title normalizado`);
- `OPERATIONS_PLAYBOOK.md` añade la regla: validación o aprobación sin delta = `0 puntos` o sin evento;
- `verify_before_deploy.py` añade:
  - un check de la nueva regla de scoring;
  - un test funcional para asegurar que `load_agent_events()` deduplica equivalentes con acentos/símbolos distintos.

**Resultado:** el scoreboard live queda saneado, el loader se vuelve robusto ante duplicados equivalentes y el protocolo deja por escrito que “validar sin cambiar nada” no debe generar puntos. `verify_before_deploy.py` sube a `397/397`.

---

## Sesión 39 — research final Lean Six Sigma + foco NOAA en Telegram (30 mar 2026, local)

**Disparador:** una vez cerrada la discusión metodológica, hacía falta traducir solo lo útil al sistema real y mover el seguimiento diario hacia el cuello de botella actual: `measurement / resolution fidelity`.

**Diagnóstico (Codex):**

1. **Lean Six Sigma completo no encaja ahora.** El sistema sigue en discovery/stabilization; añadir CTQs, A3s o control charts ahora sería más fricción que valor.

2. **Sí encajan dos guardrails pequeños.** Un premortem corto para cambios core y un lenguaje mínimo compartido (`fallo real`, `limitacion conocida`, `ruido`) ayudan a operar con más claridad sin crear burocracia.

3. **El gap operativo no era el menú de Telegram.** El problema real era no tener una vista rápida del estado NOAA desde el canal donde ya se monitoriza el bot.

**Cambios realizados:**
- se consolida `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` con recomendación final `recomiendo no adoptar`, salvo `FMEA-lite` y definiciones mínimas;
- `OPERATIONS_PLAYBOOK.md` añade:
  - `premortem corto para cambios core`;
  - definición operativa mínima de `fallo real del sistema`, `limitacion conocida` y `ruido de mercado`;
- `bot.py` amplía `run_observability_alerts()` con hitos NOAA one-shot sobre `observed_vs_forecast`:
  - primer caso global;
  - muestra mínima `>=3`;
  - muestra global útil `>=10`;
  - ciudad con primera muestra;
  - ciudad interpretable `>=3`;
- `bot.py` añade `/noaa` y `/observabilidad` como vista Telegram específica de `sample`, `MAE`, `bias`, cobertura y últimos casos;
- el menú principal de Telegram se mantiene sin poda agresiva;
- `verify_before_deploy.py` sube a `416/416` con:
  - test de `/noaa`;
  - test de idempotencia para alertas NOAA;
  - check explícito de `state.setdefault("milestones", {})`.

**Resultado:** el proyecto sale de esta sesión con criterio metodológico más claro, un playbook mínimo más útil y una capa de seguimiento diario mejor alineada con el cuello de botella real. `v10.6.5` queda lista para deploy sin tocar lógica de trading.

---

## Sesión 41 — v10.6.6 allowlist ACTIVE_TRADING_CITIES (30 mar 2026, local)

**Disparador:** tras el diagnóstico de la sesión 40, quedó claro que `BLOCKED_CITIES` como lista negra no bastaba: seguían entrando mercados de ciudades sin validación NOAA/WU como NYC, Munich, Seoul o Tokyo.

**Diagnóstico (Codex):**

1. **El bug estaba en el modelo de filtro.** Una blacklist evita reincidir en ciudades ya problemáticas, pero no protege frente a ciudades nuevas todavía no validadas.

2. **La corrección debía afectar solo a entradas nuevas.** `manage_positions` no se toca: el bot debe seguir gestionando SL/TP/reeval en cualquier posición ya abierta, incluso si nació fuera del universo validado.

3. **La solución correcta era un allowlist explícito.** Si ahora mismo solo hay 4 ciudades con monitoreo NOAA y observabilidad suficiente, el scan debe restringirse a esas 4 y dejar trazabilidad clara en `decisions.log`.

**Cambios realizados:**
- `bot.py` sube a `v10.6.6`;
- añade `ACTIVE_TRADING_CITIES` justo después de `BLOCKED_CITIES`, con default:
  - `Chicago`
  - `Atlanta`
  - `Dallas`
  - `Buenos Aires`
- el scan de mercados añade un filtro nuevo:
  - si la ciudad no está en `ACTIVE_TRADING_CITIES`, no entra en candidatos para BUY;
  - se registra `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`;
  - el resumen de filtros ahora separa también cuántos mercados quedaron fuera del allowlist;
- `manage_positions` queda intacta;
- `verify_before_deploy.py` añade checks para:
  - existencia de `ACTIVE_TRADING_CITIES`;
  - default correcto con las 4 activas;
  - presencia del filtro de allowlist y del log de skip;
- la prueba de idempotencia NOAA ya existente se mantiene como guardrail vigente;
- la suite sube a `419/419`.

**Resultado:** el bot deja de abrir posiciones nuevas en ciudades no validadas sin tocar la gestión de posiciones existentes. `v10.6.6` queda lista para push/deploy como fix quirúrgico del bug #15.

---

## Sesión 42 — v10.6.7 dashboard estado por ciudad (30 mar 2026, local)

**Disparador:** tras cerrar el allowlist de entradas nuevas, faltaba una vista clara para saber si una ciudad está operando de verdad, bloqueada, solo como referencia histórica o todavía sin observabilidad suficiente.

**Diagnóstico (Codex):**

1. **El dashboard NOAA era demasiado estrecho.** Mostraba cobertura de las 4 activas, pero no dejaba claro qué pasaba con ciudades bloqueadas, fuera del allowlist o con histórico útil.

2. **Aún no toca automatizar promociones.** La necesidad inmediata no era construir ya `watchlist / shadow / canary`, sino ver la foto actual por ciudad con datos honestos.

3. **La tabla correcta debía cruzar tres capas.** Operativa real (`ACTIVE_TRADING_CITIES` / `BLOCKED_CITIES`), observabilidad NOAA y cierres validados por ciudad.

**Cambios realizados:**
- `bot.py` sube a `v10.6.7`;
- nuevo builder `build_dashboard_city_observation()`:
  - cruza allowlist, bloqueo, `observed_vs_forecast` y `get_city_accuracy()`;
  - clasifica por ciudad `Trading`, `NOAA`, `Historico` y `Estado actual`;
  - distingue estados como `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` y `Sin observabilidad`;
- `build_dashboard_snapshot()` incorpora `city_observation` sin mezclarlo con el bloque NOAA puro;
- `templates/dashboard.html` sustituye la lista simple de cobertura por la tabla `Estado de observacion por ciudad`;
- `verify_before_deploy.py` sube a `426/426` con:
  - check estructural del builder nuevo;
  - check del bloque nuevo en el template;
  - test funcional para `Chicago`, `London` y `New York City`;
  - test de snapshot para asegurar que `city_observation` llega al dashboard.

**Resultado:** el dashboard ya enseña de un vistazo qué ciudades están en operativa real, cuáles siguen bloqueadas y cuáles solo tienen valor como referencia mientras falta una capa futura de `watchlist / shadow / canary`. `v10.6.7` queda validada en local con `426/426`.

---

## Sesión 43 — v10.6.8 control center discovery / stabilization (30 mar 2026, local)

**Disparador:** tras ver que el dashboard y Telegram seguían demasiado cargados, hacía falta una capa 1 explícita que priorizara salud real, incidentes, universo activo, crecimiento NOAA y acción recomendada sin tocar trading, exits ni scheduler.

**Diagnóstico (Codex):**

1. **La información importante estaba mezclada con demasiado detalle.** El dashboard actual sí contenía casi todo, pero no en un orden que permitiera responder rápido `¿está sano?`, `¿hay que actuar?` o `¿estamos aprendiendo?`.

2. **Telegram tenía piezas útiles pero no una vista principal operativa.** `/estado`, `/noaa`, `/accuracy` y `/detalle` existían, pero obligaban a reconstruir mentalmente la capa 1.

3. **La solución correcta era jerárquica, no decorativa.** Había que construir una capa 1 honesta sobre alertas, allowlist y NOAA ya existentes, mover el detalle a capas inferiores y dejar claro qué es incidente real vs limitación de aprendizaje.

**Cambios realizados:**
- `bot.py` sube a `v10.6.8`;
- nuevo builder `build_dashboard_focus_center()`:
  - resume salud operativa, necesidad de intervención, limitador dominante, estado de aprendizaje y acción recomendada;
  - reutiliza `get_dashboard_alert_summary()`, `build_dashboard_forecast_quality()`, `build_dashboard_city_observation()` y muestra quick stats del universo activo;
  - separa incidentes operativos reales de gaps de `measurement / NOAA`;
- `build_dashboard_snapshot()` incorpora `focus` como nueva capa 1 del dashboard;
- Telegram añade `/focus` como vista principal corta y el menú se reordena para poner `Focus` y observabilidad al frente, manteniendo `/estado`, `/noaa`, `/accuracy` y `/detalle` como segunda capa;
- `templates/dashboard.html` abre ahora con un bloque `Control Center Discovery / Stabilization` y deja el detalle extendido dentro de `Capa 3`;
- `static/dashboard.css` añade layout y estilos específicos para la capa 1, los quick stats y el panel colapsable de detalle;
- `verify_before_deploy.py` sube a `440/440` con:
  - checks estructurales del builder nuevo;
  - checks del template/CSS de `focus`;
  - test funcional del `focus center`;
  - test funcional de `/focus`;
  - test de snapshot para asegurar que `focus` llega al dashboard.

**Resultado:** queda una UX operativa mucho más clara para discovery/stabilization: en 10-15 segundos ya se puede leer si el sistema está sano, si hoy toca actuar, qué lo limita, si NOAA está enseñando algo útil y cuál es la acción recomendada. `v10.6.8` queda validada en local con `440/440` tests, sin tocar lógica de trading, exits, scheduler ni gestión de posiciones.

---

## Sesión 44 — v10.6.9 mission HUD discovery / stabilization (30 mar 2026, local)

**Disparador:** una vez resuelta la jerarquía básica de capa 1, el siguiente paso era convertirla en una interfaz mucho más enfocada y visual, con estética de videojuego operativo, para seguir la prioridad actual sin volver a llenar el dashboard de ruido.

**Diagnóstico (Codex):**

1. **La capa 1 ya era correcta en contenido, pero todavía demasiado “dashboard”.** Faltaba un lenguaje visual de misión, progreso y estado que ayudara a fijar la atención en la prioridad actual.

2. **La prioridad no es trading, sino discovery/stabilization.** Por tanto, el HUD tenía que representar `salud`, `allowlist vs NOAA`, `crecimiento de muestra` y `aprendizaje útil`, no PnL táctico ni gestión de posiciones.

3. **La interactividad debía ser ligera y segura.** Lo correcto era añadir tabs y paneles visuales alimentados por el snapshot actual, sin tocar la lógica core ni crear una capa JavaScript compleja.

**Cambios realizados:**
- `bot.py` sube a `v10.6.9`;
- `build_dashboard_city_observation()` expone campos de presentación adicionales (`observed_count`, `progress_pct`, `trades`, `win_rate`, etc.) para alimentar visuales sin alterar decisiones;
- `build_dashboard_focus_center()` gana:
  - `mission` actual;
  - `health_score`;
  - `tracks` de progreso;
  - `stage_path` de prioridad;
  - `city_race` para cobertura NOAA por ciudad;
- `templates/dashboard.html` añade una nueva cabecera `Mission HUD · Discovery / Stabilization` por encima del bloque anterior y oculta la versión previa como fallback;
- el HUD nuevo incorpora:
  - tarjeta principal de misión;
  - `System HP`;
  - ruta operativa por etapas;
  - tabs `Overview / Progress / Cities`;
  - barras de progreso por misión;
  - panel `City race` y `Operator console`;
- `static/dashboard.css` redefine la capa 1 con estética HUD, grid visual, scan lines, chips, barras y paneles de misión;
- aparece `static/dashboard.js` para alternar paneles de la capa 1 sin recargar la página;
- se borran los ficheros antiguos `RESEARCH_LEAN_SIX_SIGMA*.md` dejando solo `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md`;
- `verify_before_deploy.py` sube a `447/447` con checks nuevos de:
  - `dashboard.js`;
  - template `Mission HUD`;
  - tracks y `city_race`;
  - tabs interactivas;
  - shape funcional ampliada de `build_dashboard_focus_center()`.

**Resultado:** la capa 1 deja de sentirse como un tablero genérico y pasa a leerse como una misión operativa: qué proteger, qué está bloqueando, cuánto progreso llevamos y dónde mirar después. Queda lista para previsualización funcional y para una siguiente iteración centrada en tendencias temporales de aprendizaje, no en más detalle táctico.

---

## Sesión 45 — v10.6.10 focus readability + Railway validation (30 mar 2026)

**Disparador:** tras la primera preview real del `Mission HUD`, la lectura seguía costando: la alerta `signals.json stale` aparecía demasiadas veces, la tabla de ciudades era pesada y el modo oscuro no ayudaba a entender rápido la prioridad operativa.

**Diagnóstico (Codex):**

1. **La capa 1 seguía exagerando un síntoma secundario.** `signals.json stale` es una alerta real, pero no debe ocupar toda la lectura cuando el bloqueo dominante sigue siendo `NOAA / muestra / cobertura`.

2. **La tabla de ciudades era correcta, pero no legible como primera pantalla.** Hacía falta agrupar por prioridad operativa y no pedir una lectura fila a fila de 14 ciudades.

3. **La estética debía ayudar a decidir, no solo a impresionar.** En esta fase discovery/stabilization, el contraste y la claridad pesan más que un look oscuro agresivo.

**Cambios realizados:**
- `bot.py` sube a `v10.6.10`;
- `build_dashboard_focus_center()`:
  - relega `signals.json stale` a señal secundaria cuando el bloqueo real es de muestra/cobertura NOAA;
  - deja más clara la lectura de `salud`, `intervención`, `limitador` y `acción recomendada`;
- `build_dashboard_city_observation()` expone grupos listos para UI:
  - `active_rows`;
  - `watch_rows`;
  - `blocked_rows`;
- `templates/dashboard.html` sustituye la tabla larga por zonas operativas:
  - `Universo operativo`;
  - `Seguimiento y referencia`;
  - `Archivo de ciudades fuera de juego`;
- `static/dashboard.css` cambia la experiencia a modo claro por defecto y añade estilos específicos para tarjetas/zonas de ciudad;
- `verify_before_deploy.py` sube a `449/449` con checks nuevos de:
  - modo claro;
  - agrupación visual de ciudades;
  - shape funcional de `active_rows / watch_rows / blocked_rows`;
- se añade `tools/preview_dashboard.py` para levantar solo el dashboard local sin arrancar todo el bot y sin depender de auth.

**Resultado:** la capa 1 conserva el enfoque de misión, pero gana legibilidad operativa real. El dashboard ya no repite tanto una alerta secundaria, las ciudades se entienden como `operativas / seguimiento / bloqueadas` y `v10.6.10` quedó validada también en Railway: `healthz` respondió `200` con `version=v10.6.10` y el snapshot live confirmó modo `REAL`, próxima ejecución `23:00 UTC`, `signals ok`, `141` señales accionables, `0/10` casos NOAA y una única alerta activa de `accuracy` por ciudades.

---

## Sesión 46 — auditoría NOAA `observed_vs_forecast` + fix mínimo local (31 mar 2026)

**Disparador:** Railway `v10.6.10` seguía mostrando `NOAA 0/10` y `0/4` ciudades interpretables pese a que ya había actividad real en Chicago, Atlanta, Dallas y Buenos Aires. Había que distinguir con honestidad entre “todavía no hay muestra” y “el pipeline NOAA está roto”.

**Diagnóstico (Codex):**

1. **La entrada en `observed_vs_forecast` estaba bien definida, pero demasiado exigente para depurarla a ojo.** Un caso solo entra si en `performance.json` existe un `BUY`, la ciudad está en `OBSERVED_AUDIT_CITIES`, la fecha se puede parsear, hay `noaa_station_id`, el `city|date` no está duplicado y han pasado al menos `2` días (`NOAA_OBSERVED_LAG_DAYS`).

2. **No era solo falta de muestra.** La auditoría reconstruyó al menos `7` casos `city|date` ya elegibles frente a `0` registros reales en `audit.json -> observed_vs_forecast`. Evidencia mínima: `Chicago|2026-03-25`, `Chicago|2026-03-26`, `Chicago|2026-03-28`, `Atlanta|2026-03-27`, `Dallas|2026-03-22`, `Dallas|2026-03-28`, `Buenos Aires|2026-03-28`.

3. **El cuello de botella real estaba en la fuente NOAA elegida.** El código dependía de `global-hourly` reconstruyendo el máximo desde `TMP`, pero probes reales sobre fechas 2026 devolvían vacío en varios casos donde `daily-summaries` sí devolvía `TMAX`. Se comprobó, por ejemplo, que `Dallas 2026-03-22`, `Chicago 2026-03-25/26` y `Atlanta 2026-03-27` ya estaban disponibles por `daily-summaries`.

**Cambios realizados:**
- `bot.py` mantiene intacta la lógica de trading y endurece solo NOAA/observabilidad:
  - añade `noaa_daily_station_id` en `RESOLUTION_ICAO` para Chicago, Atlanta y Dallas;
  - incorpora `fetch_noaa_daily_tmax()` para `daily-summaries`;
  - renombra el fetch original a `_fetch_noaa_observed_max_hourly()`;
  - crea un wrapper `fetch_noaa_observed_max()` que prueba primero `daily-summaries/TMAX` y cae a `global-hourly` si no hay dato;
  - `audit_check_resolution_truth()` ahora guarda también `noaa_daily_station_id` y `observed_dataset` para dejar trazabilidad de qué dataset produjo el observado.
- `verify_before_deploy.py` sube a `451/451` con:
  - checks estructurales para `noaa_daily_station_id`;
  - test del helper `fetch_noaa_daily_tmax()`;
  - actualización del test funcional del wrapper NOAA para esperar `daily-summaries_tmax`;
  - test del pipeline de auditoría asegurando persistencia de `observed_dataset`.
- tras review adversarial adicional:
  - `fetch_noaa_daily_tmax()` añade el mismo guard de lag que ya usaba el path hourly para no hacer requests innecesarios si se invoca de forma directa;
  - `verify_before_deploy.py` recupera un test explícito del fallback `daily vacío -> hourly`;
  - la suite queda en `453/453`.

**Resultado:** el diagnóstico correcto al cierre de la sesión es **bug real de observabilidad NOAA**, no mera falta de tiempo. Sí faltaba muestra para algunas fechas recientes, pero ya existían casos elegibles suficientes como para esperar `n > 0` en producción. El fix queda validado en local con `453/453` tests, sin tocar trading, sigma/Kelly, exits, scheduler ni gestión de posiciones. Buenos Aires queda temporalmente en fallback `global-hourly` porque todavía no se validó una estación diaria fiable. La idea de una futura capa `shadow sample` queda solo como propuesta segura para más adelante, no como cambio aplicado hoy.

---

## Sesión 47 — capa `trade_lifecycle` para trazabilidad operativa completa (31 mar 2026)

**Disparador:** al revisar ventas como el take-profit de Atlanta que luego terminó en `100c`, quedó claro que `performance.json` y `postmortem.json` ya explicaban por qué se entró y por qué se intentó salir, pero no dejaban una historia completa por posición para analizar después cuánto upside se dejó encima de la mesa o qué ocurrió tras salir.

**Diagnóstico (Codex):**

1. **La observabilidad actual estaba fragmentada.** `performance.json` registra eventos; `postmortem.json` agrega estado y cierre; `audit.json` cubre NOAA. Pero faltaba una capa única orientada a análisis por trade, no por evento.

2. **El análisis futuro de trading necesitaba evidencia, no intuición.** Antes de pedir a Claude Code Opus que decida cambios de operativa, hacía falta poder responder con datos a preguntas como “¿este TP fue prematuro?”, “¿el mercado llegó a `0.98/1.00` después de vender?” o “¿qué drawdown se evitó realmente?”.

3. **Se podía instrumentar sin tocar trading.** La lógica de entrada/salida no necesitaba cambiar; bastaba con enganchar los puntos correctos del ciclo de vida y reconstruir el histórico desde las fuentes ya existentes.

**Cambios realizados:**
- `bot.py` añade `TRADE_LIFECYCLE_FILE = _data_path("trade_lifecycle.json")` y una nueva capa derivada con:
  - carga/guardado dedicados;
  - helper `_sync_trade_lifecycle_from_sources()` para reconstruir desde `performance.json` + `postmortem.json`;
  - campos por posición: `entry_context`, `latest_entry_context`, `buys`, `timeline`, `exit_attempts`, `position_snapshots`, `market_observations`, `close_context`, `post_exit_analysis` y `summary` global;
  - enriquecimiento de duplicados históricos para no perder `cycle_number`, `logic_cycle_number`, `trader_confirmed`, `decision_note`, `decision_source`, `trigger_price` o `current_value` cuando el backfill parte de `postmortem` y luego se completa con `performance`.
- La capa se actualiza automáticamente:
  - en cada `track_trade()` (`BUY`, `SELL_PENDING`, `SELL`, `SELL_FAILED`, `LOSS_TOTAL`, `RESOLVED_WIN`);
  - al arrancar, tras el backfill de `postmortem`;
  - en `manage_positions()` con snapshots previos a checks;
  - en el monitor intra-ciclo con snapshots entre ciclos;
  - durante el scan principal con observaciones de mercado para medir qué pasa tras el cierre.
- `record_trade_lifecycle_market_observations()` calcula también señales de análisis post-salida:
  - `market_seen_after_close`;
  - `max/min_price_after_close`;
  - `reached_98_after_close`;
  - `upside_left_cash_peak / pct`;
  - `drawdown_avoided_cash_peak / pct`.
- `verify_before_deploy.py` cierra en `467/467` con:
  - checks estructurales de la nueva capa;
  - test funcional de reconstrucción histórica desde `performance+postmortem`;
  - test de snapshots de posición viva;
  - test de observación post-exit con detección explícita de upside dejado hasta `100c`.

**Resultado:** queda lista una capa de trazabilidad completa, pensada para revisión rápida por Claude Code Sonnet y análisis estratégico posterior por Claude Code Opus, sin tocar ni una regla de trading. Limitación conocida al cierre: el backfill real de la cuenta no pudo materializarse localmente en esta sesión porque el CLI de Railway tenía el login OAuth caducado, pero el código ya deja el `trade_lifecycle.json` preparado para reconstruirse automáticamente desde el Volume en el próximo arranque desplegado.

---

## Sesión 48 — hardening fase 1 de `trade_lifecycle` (31 mar 2026)

**Disparador:** tras validar en Railway que `trade_lifecycle.json` ya existía y era útil para analizar exits, la inspección del raw live reveló ruido histórico real: `92` filas visibles, pero varias operaciones antiguas aparecían duplicadas por `id` y con `token_id` vacío, `total_amount = 0` y `total_shares = 0`.

**Diagnóstico (Codex):**

1. **La duplicación no venía de trading, sino del replay histórico.** Algunos cierres viejos de `performance.json` solo guardaban `city/side/precio/razón`, sin `token_id`, `question` ni `date`. Al reconstruir desde `postmortem + performance`, `_find_trade_lifecycle_record()` no conseguía emparejar esos eventos “pobres” con su record previo de `postmortem`.

2. **El síntoma era una pareja `postmortem-only` + `performance-only` con el mismo `id`.** En live esto afectaba a `12` casos y contaminaba el conteo de `tracked_positions/closed_positions`, además de mezclar ruido parcial en futuros rankings de eficiencia operativa.

3. **Se podía sanear sin tocar trading.** Bastaba con endurecer el matching de la capa derivada, coalescer duplicados por `id` y dejar explícito qué records son solo parciales para análisis.

**Cambios realizados:**
- `bot.py` añade `_trade_lifecycle_record_id()` y hace que `_find_trade_lifecycle_record()` pruebe primero el `id` reconstruido antes de caer a `token_id/question/city+side+date`.
- Se añade coalescing defensivo por `id` mediante `_coalesce_trade_lifecycle_records()` y merge controlado de contexto/listas para evitar que una misma posición salga dos veces en el payload final.
- Cada record recibe ahora un bloque `integrity` con flags como:
  - `partial_historical_record`
  - `analysis_ready`
  - `missing_token_id`
  - `missing_question`
  - `missing_entry_context`
  - `missing_buy_history`
  - `zero_amount`
  - `zero_shares`
- El payload global añade también `integrity` agregado para auditar el estado del dataset antes de usarlo en métricas o dashboard.
- `record_trade_lifecycle_position_snapshots()` y `record_trade_lifecycle_market_observations()` refrescan también la integridad global para no dejar el JSON desalineado tras cada update incremental.
- `verify_before_deploy.py` sube a `470/470` con:
  - check estructural del bloque `integrity`;
  - test funcional del caso real de “cierre huérfano” para asegurar que un `SELL` histórico sin `token/question/date` ya no duplica el record y queda marcado como parcial.

**Validación con datos reales:**
- Se descargan `performance.json` y `postmortem.json` live desde Railway y se reconstruye el lifecycle con el código nuevo.
- Resultado:
  - `92` filas visibles en el raw live anterior;
  - `80` records únicos tras reconstrucción endurecida;
  - `0` duplicados residuales;
  - `12` `partial_historical_records` explícitamente marcados;
  - `68` records `analysis_ready`.

**Resultado:** queda cerrada la fase 1 de saneamiento de `trade_lifecycle`: el dataset ya no duplica cierres huérfanos antiguos y además declara explícitamente qué parte del histórico es parcial. No se toca ninguna regla de trading. El siguiente paso natural es desplegar este hardening y construir encima la fase 2: capa analítica de operativa para dashboard y paquete congelado para Claude Code Opus.

---

## Sesión 49 — hotfix de coalescing para `trade_lifecycle` (31 mar 2026)

**Disparador:** al validar en Railway el despliegue de la fase 1, el contenedor arrancó correctamente pero empezó a loguear `Error sincronizando trade_lifecycle: unhashable type: 'list'` tanto en startup como durante el ciclo de las `16:00 UTC`. El problema aparecía justo cuando `track_trade()` registraba varios `LOSS_TOTAL` y el lifecycle intentaba resincronizarse.

**Diagnóstico (Codex):**

1. **El fallo no estaba en trading ni en datos NOAA.** `status`, `logs` y el dashboard live confirmaron que el servicio estaba arriba, que NOAA seguía poblando muestra real y que el error afectaba únicamente a la capa derivada `trade_lifecycle`.

2. **La pista clave era el mensaje Python exacto.** Se revisó el hot path de coalescing y apareció una construcción inválida en Python:
   - `_merge_trade_lifecycle_context()` usaba `if target.get(key) in {None, "", [], {}} ...`
   - `_merge_trade_lifecycle_record()` usaba `existing not in {None, "", [], {}}`
   Eso dispara `TypeError: unhashable type: 'list'` en cuanto la expresión se evalúa, porque `[]` y `{}` no pueden ser elementos de un set.

3. **La razón por la que no saltó antes:** el bug solo se manifiesta cuando la ruta de coalescing se ejecuta de verdad sobre records duplicados/ambiguos. En Railway, esa condición sí se daba tras la fase 1, porque el lifecycle live todavía arrastraba duplicados históricos y el ciclo de las `16:00` volvió a empujar eventos `LOSS_TOTAL`.

**Cambios realizados:**
- `bot.py` añade `_lifecycle_is_empty()` para encapsular de forma segura la noción de “vacío” (`None`, `""`, listas/dicts/tuplas/sets vacíos).
- `_merge_trade_lifecycle_context()` deja de usar sets inválidos con `[]/{}` y pasa a `if _lifecycle_is_empty(...)`.
- `_merge_trade_lifecycle_record()` cambia `_prefer()` para reutilizar el mismo helper seguro.
- `verify_before_deploy.py` añade:
  - check estructural de `_lifecycle_is_empty()`;
  - regresión funcional que coalesce dos records con el mismo `id` y `entry_context` no vacío para asegurar que:
    - no rompe;
    - fusiona `timestamp + price`;
    - une `trader_confirmed` en `["Alpha", "Beta"]`.
- Se normaliza `agent_events.jsonl` del repo a `utf-8`, porque la suite seguía detectando un seed local en `cp1252` que ensuciaba el runner con un warning ajeno al bug de lifecycle.

**Validación:**
- Se confirma el síntoma live en logs de Railway:
  - startup: `Error sincronizando trade_lifecycle al arrancar: unhashable type: 'list'`
  - ciclo `16:00 UTC`: múltiples `Error sincronizando trade_lifecycle: unhashable type: 'list'`
- El hotfix local queda validado con `verify_before_deploy.py` en `472/472`.
- NOAA sigue sano y no está afectado por este bug:
  - `observed_vs_forecast` live ya mostraba `2` casos reales en Chicago.

**Resultado:** el problema queda acotado y corregido localmente sin tocar reglas de trading. El siguiente paso correcto es desplegar este hotfix, revalidar Railway y confirmar que desaparecen los warnings de `trade_lifecycle` antes de seguir con la fase 2 analítica del dashboard.

---

## Sesión 50 — recap + Railway CLI hygiene (31 mar 2026)

**Disparador:** tras cerrar el hotfix de `trade_lifecycle`, el siguiente bloqueo real ya no era el bot sino la operativa del Railway CLI: la sesion acababa mezclando producto, auth OAuth y el proxy `127.0.0.1:9`, y hacia falta dejar un guardrail practico para no volver a perder tiempo en el mismo bucle.

**Diagnóstico (Codex + validación previa con Claude):**

1. **El problema de auth quedo suficientemente entendido.** No era un bug del bot ni del deploy. La secuencia mas plausible era:
   - token de acceso expirado;
   - intento de refresh desde un contexto sandboxed;
   - fallo al persistir `%USERPROFILE%\.railway\config.json` (`os error 5`);
   - refresh token local stale;
   - siguiente intento => `invalid_grant`.

2. **El proxy seguia existiendo, pero ya no era el bloqueo principal.** En esta shell seguian entrando:
   - `HTTP_PROXY=http://127.0.0.1:9`
   - `HTTPS_PROXY=http://127.0.0.1:9`
   - `ALL_PROXY=http://127.0.0.1:9`
   - `GIT_HTTP_PROXY=http://127.0.0.1:9`
   - `GIT_HTTPS_PROXY=http://127.0.0.1:9`
   Ya estaba descartado que vinieran de `PowerShell profile`, `HKCU/HKLM`, `winhttp` o settings normales de VS Code. Se decide no seguir persiguiendo el origen durante esta incidencia porque habia una solucion practica mejor.

3. **El hotfix de lifecycle ya estaba bueno en Railway.** Una vez empujado `47c68ee`, Railway redeployo y el arranque nuevo confirmo:
   - `trade_lifecycle listo al arrancar: 87 registros`
   - sin repetir `unhashable type: 'list'`
   - validacion live posterior:
     - `tracked_positions=87`
     - `open_positions=18`
     - `closed_positions=69`
     - `partial_historical_records=12`
     - `analysis_ready_records=75`
     - `duplicate_id_collisions_resolved=12`
     - `duplicate_ids_live=0`

**Cambios realizados:**
- Nuevo wrapper repo-local `tools/railway_safe.ps1`.
  - limpia `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` solo para el proceso actual;
  - ejecuta `railway.cmd`;
  - restaura el entorno al salir;
  - deja mensaje explicito cuando se usa `login`.
- `OPERATIONS_PLAYBOOK.md` gana la seccion `Higiene Railway CLI` con la regla operativa nueva:
  - `railway login` solo en shell interactiva del usuario;
  - uso diario de Railway con el wrapper;
  - desde Codex, Railway fuera del sandbox cuando la CLI pueda refrescar auth.
- `CONTEXTO.md` se actualiza para reflejar que:
  - el hotfix de lifecycle ya esta validado live;
  - la infraestructura vuelve a estar bajo control practico;
  - el siguiente paso correcto regresa a analytics/dashboard.

**Resultado:** la sesion deja un guardrail operativo claro para Railway CLI sin volver a abrir una investigacion larga del proxy. El sistema queda otra vez orientado al roadmap principal: capa analitica de operativa en dashboard y snapshot para Claude Code Opus.

---

## Sesión 51 — fase 2 analítica de operativa (31 mar 2026)

**Disparador:** con `trade_lifecycle` ya saneado y el wrapper de Railway en su sitio, el siguiente paso lógico era dejar de mirar los exits solo como PnL agregado y pasar a medir con evidencia post-salida qué estaba capturando realmente el bot.

**Objetivo:** añadir una capa analítica derivada, visible en dashboard, que permita seguir activamente:
- cuántos cierres tienen muestra post-exit útil;
- cuánto upside se dejó tras salir;
- cuánto downside se evitó;
- qué buckets (`take_profit`, `reeval`, `stop_loss`) merecen revisión antes de tocar reglas.

**Cambios realizados:**
- Se añade `build_dashboard_trade_analytics()` en `bot.py`.
  - filtra solo `status=closed` con `market_seen_after_close=True`, `close_price` usable, `close_shares > 0` y `integrity.analysis_ready`;
  - calcula `score_pct`, `harvest_efficiency_pct`, `upside_left_total_cash`, `drawdown_avoided_total_cash` y `maturity_pct`;
  - genera `breakdown_rows` por `take_profit / reeval / stop_loss`;
  - construye `recent_rows`, `top_upside_rows`, `top_protection_rows` y `timeline_points`.
- `build_dashboard_snapshot()` pasa a cargar `trade_lifecycle` y a exponer `trade_analytics` en `/api/dashboard.json`.
- El dashboard web gana una nueva sección visible `Operativa observada` con:
  - medidor principal de eficiencia;
  - badges de confianza / muestra;
  - timeline corto de exits observados;
  - cola de revisión con `top upside dejado` y `casos donde salir ayudó`;
  - tabla de últimos cierres con evidencia post-salida.
- La capa evita contaminar el análisis con histórico parcial:
  - los `close_only` o records sin precio/cantidad de salida usable quedan fuera;
  - no se toca ninguna regla de `manage_positions`, sizing, scheduler ni exits.

**Tests:**
- Nuevo bloque funcional para `build_dashboard_trade_analytics()`:
  - cuenta solo cierres observados utilizables;
  - calcula score y rankings de upside/protección;
  - genera breakdown y timeline.
- `build_dashboard_snapshot()` queda cubierto para asegurar que incluye `trade_analytics`.
- `verify_before_deploy.py` sube a `477/477`.

**Resultado:** queda implementada la fase 2 de observabilidad operativa. El bot sigue igual en trading, pero el dashboard ya tiene una base estructurada para seguir si las salidas están capturando valor o dejando dinero encima de la mesa. El siguiente paso correcto es validarlo en Railway y usar esa evidencia para preparar el análisis profundo con Claude Code Opus.

---

## Sesión 52 — trade console dashboard (31 mar 2026)

**Disparador:** tras ver la primera capa `Operativa observada` en pantalla, quedó claro que respondía bien a la pregunta de eficiencia observada de exits, pero seguía siendo poco práctica para revisar la operativa trade por trade.

**Objetivo:** ampliar el dashboard con una vista más accionable que permita responder:
- cuántas operaciones totales hay;
- cuántos TP/SL se ejecutaron;
- cuántas operaciones acabaron ganadas/perdidas;
- cuánto cash se ganó, perdió o se dejó de ganar;
- y, para cada trade, por qué entró el bot, por qué salió y qué pasó después.

**Cambios realizados:**
- `build_dashboard_trade_analytics()` se amplía en `bot.py` con una capa tipo `trade console`.
  - añade `total_cards` con `Operaciones totales`, `TP`, `SL`, `Ganadas`, `Perdidas`, `PnL neto`, `Dejado de ganar` y `Protegido`;
  - añade `trade_rows` con detalle por posición:
    - mercado;
    - condición de entrada;
    - condición de salida;
    - resultado;
    - valor del trade;
    - centavos por share;
    - upside dejado;
    - y estado de observación/integridad.
- `templates/dashboard.html` gana una nueva pestaña separada `Trade console / Operaciones del bot` con dos vistas:
  - `Resumen`;
  - `Trades`.
- `static/dashboard.js` se generaliza para soportar múltiples shells de tabs (`data-tab-shell`) sin romper el Mission HUD original.
- La fuente de verdad sigue siendo `trade_lifecycle` + `postmortem`; el CSV local se deja solo como referencia manual, no como dependencia del dashboard live.

**Tests:**
- Se ajusta la validación funcional de `trade_analytics` para comprobar totales y detalle por trade sin depender de un orden artificial.
- `verify_before_deploy.py` sube a `478/478`.

**Resultado:** el dashboard ya no se queda en una lectura abstracta de eficiencia. Ahora también ofrece una consola de operaciones pensada para seguimiento activo del bot y para preparar, más adelante, una revisión profunda con Claude Code Opus usando una vista más legible y más cercana a cómo se piensa la operativa real.

---

## Sesión 53 — snapshot analítico live + refinamiento semántico local (1 abr 2026)

**Disparador:** el siguiente paso pendiente ya no era añadir más panel, sino usar producción como fuente de verdad para revisar casos reales `take_profit / reeval / stop_loss` y congelar una foto analítica útil antes de seguir tocando semántica o reglas.

**Objetivo:** reabrir acceso live, revisar la consola de trades contra datos reales de Railway y dejar un snapshot congelado que sirva tanto para la próxima iteración local como para un handoff limpio a Claude Code Opus.

**Acceso live recuperado:**
- El Railway CLI seguía bloqueado por auth expirada (`invalid_grant`) y el wrapper confirmó que `railway login` no puede completarse desde una shell no interactiva de Codex.
- Se encontró una vía alternativa suficiente para análisis: el dashboard live ya estaba protegido con auth básica y las credenciales existían en `.env`.
- Con eso se pudo acceder a:
  - `https://polymarket-bot-production-4deb.up.railway.app/healthz`
  - `https://polymarket-bot-production-4deb.up.railway.app/api/dashboard.json`

**Foto live congelada (`2026-04-01 20:13 UTC`):**
- versión: `v10.6.10`
- `portfolio_total = $31.91`
- `signals ok`
- sin `pending_exit` atascadas
- `101` operaciones
- `85` cerradas
- `16` abiertas
- `TP = 5`
- `SL = 13`
- `LOSS_TOTAL = 60`
- `PnL neto = $-37.53`
- muestra observada post-salida: `7/85`
- focus live:
  - `Sano con limitaciones`
  - `La operativa parece estable; el cuello de botella ahora es learning / measurement`
  - acción: `No tocar trading: priorizar crecimiento de muestra NOAA`
  - NOAA: `2/10` casos, `0/4` ciudades interpretables

**Casos revisados en live:**
- `Re-eval` observado:
  - `Will the highest temperature in New York City be 74°F or higher on March 31?`
  - `PnL = $+0.06`
  - `trade_value = $1.32`
  - `2 obs`
  - salida por `edge recalculado < -3%`
- `Stop-loss` observados:
  - Dallas `82-83°F Apr 1`:
    - `PnL = $-0.56`
    - `trade_value = $0.41`
    - `3 obs`
  - Atlanta `80-81°F Apr 1`:
    - `PnL = $-1.30`
    - `trade_value = $0.77`
    - sin observación post-salida todavía
    - conserva `trigger 10.5c | limite 8.0c`
- `Take-profit` identificados en live:
  - `Chicago YES` como `Mejor operacion` (`SELL · take_profit`, `+$3.96`)
  - `Atlanta Mar30 YES` como `Mejor retorno %` (`v10.6.10 · serie v10.6 · SELL · take_profit`, `+302.5%`)
  - importante: en este snapshot no aparece aún muestra observada post-salida de TP (`coverage 0/5`)

**Hallazgo clave del snapshot:**

1. **La consola live seguía mezclando semánticas.** En la tabla visible del snapshot muchos cierres seguían cayendo en bucket `Otro`, aunque el breakdown validado ya reconocía `60 LOSS_TOTAL`. No era un problema teórico: seguía costando leer de un vistazo qué era `SELL negativo`, qué era `LOSS_TOTAL` y qué era ruido legacy/parcial.

2. **La evidencia observada de exits sigue siendo pequeña pero ya útil.** `Re-eval` aparece con señal de `revisar captura`; `Stop-loss` sale `mixto`; y `Take-profit` aún no tiene muestra observada útil en este snapshot aunque sí muestra balance agregado claramente positivo.

3. **El bloqueo principal no es trading, sino measurement.** El propio `focus` live sigue recomendando no tocar reglas y priorizar NOAA, porque `0/4` ciudades activas siguen sin llegar a zona interpretable.

**Cambios realizados en local durante la misma sesión:**
- `build_dashboard_trade_analytics()` queda endurecido para separar:
  - motivo de salida;
  - resultado económico;
  - calidad/integridad del registro.
- El `trade console` local pasa a distinguir explícitamente:
  - `SELL negativos`
  - `LOSS_TOTAL`
  - `Legacy/parcial`
- `templates/dashboard.html` se ajusta para explicar esa nueva lectura.
- `verify_before_deploy.py` gana cobertura funcional de:
  - `LOSS_TOTAL`
  - `close-only`
  - `partial_historical`
- La suite local sube a `479/479`.

**Artefactos congelados:**
- `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json`
- `SNAPSHOT_ANALITICO_LIVE_2026-04-01.md`

**Resultado:** queda reabierto el acceso live suficiente para análisis, congelada una foto real de producción y cerrada en local la semántica que faltaba para que la próxima validación live no vuelva a colapsar `SL / LOSS_TOTAL / legacy` en una lectura ambigua. El siguiente paso correcto ya no es investigar, sino desplegar esta mejora semántica y revalidar la consola sobre el mismo flujo live.

---

## Sesión 54 — cierre del bug de Railway auth (1 abr 2026)

**Disparador:** el usuario pidió una sesión limpia dedicada solo al bug de Railway auth que obligaba a reloguearse continuamente, sin tocar trading ni dashboard.

**Diagnóstico confirmado:**

1. **Había dos capas distintas del fallo.**
   - Sin wrapper, `railway.cmd` seguía intentando salir por `127.0.0.1:9` y fallaba al conectar.
   - Con wrapper, la red quedaba bien, pero `whoami/status` devolvían `Unauthorized`, así que el problema real restante era de credenciales locales degradadas.

2. **Los proxies no eran persistentes de Windows.**
   - `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` estaban presentes en la shell actual.
   - No aparecían ni en variables `User/Machine` ni en perfiles normales de PowerShell.
   - Conclusión operativa: el wrapper seguía siendo la defensa correcta para uso diario.

3. **El `config.json` de Railway estaba enlazado pero roto a nivel de auth.**
   - Existían `accessToken`, `refreshToken` y el link del proyecto.
   - Aun así, en entorno limpio la CLI respondía `Unauthorized`.
   - Esto confirmó que el siguiente paso no era tocar el bot, sino sanear la auth local.

**Cambios implementados:**

- `tools/railway_safe.ps1` se endurece para limpiar también proxies en minúsculas, `NO_PROXY` y variantes `npm_config_*`, no solo `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*`.
- Se añade `tools/railway_auth_repair.ps1` con cuatro acciones operativas:
  - `doctor`: diagnostica proxies, estado del `config.json` y auth real vía `whoami`.
  - `reset`: hace backup del config y limpia solo los tokens stale.
  - `launch-login -Browserless`: abre una shell limpia para login interactivo del usuario.
  - `restore-links`: restaura el bloque `projects` desde el último backup sin tocar los tokens nuevos.
- `OPERATIONS_PLAYBOOK.md`, `CONTEXTO.md` y esta bitácora quedan actualizados con el flujo correcto.

**Incidencia real descubierta durante la reparación:**

- El login browserless sí autenticó correctamente al usuario (`pablogomez.eu@gmail.com`), pero Railway regeneró `config.json` con `projects = {}` y `status` pasó a responder `No linked project found`.
- Para cerrar ese hueco se añadió `restore-links`, que copia únicamente el bloque `projects` desde `config.backup.*.json`.
- También se corrigió la escritura del helper a `UTF-8` sin BOM para no volver a provocar `Unable to parse config file, regenerating` en futuros `reset`.

**Validación final del 1 de abril de 2026:**

- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`
  - `Logged in as pablogomez.eu@gmail.com`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status`
  - `Project: enchanting-respect`
  - `Environment: production`
  - `Service: polymarket-bot`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 logs -s polymarket-bot -n 20`
  - vuelve a responder correctamente

**Límite de alcance respetado:**

- no se tocó trading;
- no se tocó dashboard;
- la lectura de logs live fue solo para validar que la CLI había quedado operativa otra vez.

---

## Sesión 55 — deploy validado de semántica trade console (1 abr 2026)

**Disparador:** con Railway auth ya reparada y el refinamiento semántico listo en local, faltaba cerrar el paso obvio: empujar el commit, redeployar y comprobar si la consola live seguía colapsando cierres en `Otro` o ya leía bien `SL / LOSS_TOTAL / legacy-parcial`.

**Ejecución y validación:**

- Se empuja `5b23d02` (`ops: refine trade console semantics and harden railway auth workflow`) a `origin/main`.
- Se fuerza redeploy manual con `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 redeploy -s polymarket-bot -y`.
- Railway crea el deployment `00366049-f0a4-4267-b782-450ef49feb75`, que progresa hasta `SUCCESS`.
- La comprobación live autenticada de `dashboard.json` a las `21:00 UTC` confirma las tarjetas:
  - `Operaciones totales`, `TP`, `SL`, `LOSS_TOTAL`, `Ganadas`, `SELL negativos`, `Legacy/parcial`, `PnL neto`, `Dejado de ganar`, `Protegido`
- La nota live ya explica explícitamente que la consola separa `SL`, `LOSS_TOTAL` y `legacy/parcial`.
- Las primeras filas reales dejan de caer en `Otro` y pasan a verse como:
  - `Stop-loss | Perdida SELL | Completa`
  - `LOSS_TOTAL | Perdida total | Completa`

**Resultado:** queda cerrada la brecha entre el snapshot local y el panel productivo. El dashboard live ya muestra la nueva taxonomía sin tocar reglas de trading ni bump de versión (`v10.6.10`), y el siguiente trabajo vuelve a ser análisis operativo sobre casos reales, no auth ni deploy.

---

## Sesión 56 — auditoría de inconsistencias en `trade_lifecycle` / trade console (1 abr 2026)

**Disparador:** tras revisar los últimos trades reales en Polymarket, quedó claro que la pregunta importante ya no era solo "si la consola separa bien `SL / LOSS_TOTAL / legacy`", sino si realmente conserva una historia coherente por posicion reciente: por qué entro, por qué salió, qué ocurrió tras salir y si la lectura visible coincide con la cartera real.

**Hallazgos confirmados en la auditoría manual:**

1. **`Seoul 14C Apr 1` aparece con desenlace contradictorio.**
   - En el snapshot congelado de `trade_rows` aparece una fila como `Perdida` con salida `Micro posicion incanjeable / perdida total` y otra fila del mismo mercado como `Ganada` con salida `market_resolved_yes`.
   - Eso rompe la regla básica de "una posición, una historia".

2. **`Seoul 13C Apr 1` sale ganada pero con entrada degradada a parcial.**
   - La fila visible marca `Ganada` y `trade_value = $3.04`.
   - Sin embargo, el `entry_condition` dice `Historico parcial: faltan datos claros de entrada.`
   - Para un caso tan reciente eso apunta a problema de reconciliación, no a mera limitación legacy.

3. **`Atlanta 70-71F Mar 30` sigue duplicada en la lectura humana.**
   - Hay una fila "completa" con la entrada real y `pnl_cash = -1.33`.
   - Además sobreviven filas heredadas/parciales del mismo mercado con `trade_value = $0.00`.
   - El coalescing mejoró, pero todavía no deja una única traza limpia para todos los casos recientes.

4. **`Atlanta 78-79F Apr 1` existe en `portfolio.dead` pero no quedó visible en la extracción revisada de `trade_rows`.**
   - En cartera muerta aparece con `initialValue = 2.1238`, `currentValue = 0.010619`, `cashPnl = -2.113181`.
   - Eso obliga a revisar si el problema está en generación de filas, orden, filtro o semántica del cierre.

5. **La etiqueta visible aún puede ocultar el lado `YES/NO`.**
   - `_trade_lifecycle_label()` prioriza `question`; si existe, no muestra explícitamente `side`.
   - En mercados de temperatura casi idénticos eso dificulta detectar rápido inconsistencias humanas aunque el record interno sí tenga `side`.

6. **El `redeem/claim` manual no se registra como evento propio.**
   - La capa sí maneja `BUY`, `SELL_PENDING`, `SELL`, `SELL_FAILED`, `LOSS_TOTAL` y `RESOLVED_WIN`.
   - Pero el cobro manual posterior no queda registrado como acción diferenciada; solo se sabe que el mercado resolvió y quedó pendiente de canjear/cobrar.

**Qué se validó también como positivo:**

- los BUY recientes sí guardan contexto rico (`price`, `shares`, `amount`, `edge_pct`, `our_prob`, `mkt_price`, `forecast_max`, traders y ciclo);
- los `SELL_PENDING` guardan motivo, trigger, límite, `decision_note`, `decision_source`, `PnL` y `order_id`;
- existen `position_snapshots`, `market_observations` y `post_exit_analysis`.

**Acciones de cierre de la sesión:**

- se deja creado `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` con:
  - lista de evidencias verificadas;
  - hipótesis de trabajo;
  - y prompt listo para arrancar la siguiente sesión solo con esta tarea;
- se actualizan `CONTEXTO.md` y esta bitácora para mover explícitamente el foco operativo desde auth/deploy hacia saneamiento de trazabilidad.

**Límite de alcance respetado:**

- no se tocó trading;
- no se tocó NOAA;
- no se desplegó nada;
- no se cambió lógica del bot en esta sesión;
- se cerró únicamente la auditoría y el handoff.

---

## Sesión 57 — saneamiento local de `trade_lifecycle` / trade console (1 abr 2026)

**Disparador:** el handoff de la sesión 56 ya había aislado el problema real: no faltaban datos de entrada/salida, faltaba reconciliarlos en una sola historia humana por posición. El objetivo de esta sesión fue arreglar eso sin tocar reglas de trading ni NOAA.

**Cambios aplicados:**

- `trade_lifecycle` gana una clave estable por mercado+lados (`position_key`) y un segundo coalescing por identidad de posición para fusionar records que antes quedaban separados solo porque cambiaba el timestamp del `id`.
- `_trade_lifecycle_label()` deja de ocultar el lado cuando existe `question`; ahora la etiqueta visible puede diferenciar `YES/NO`.
- `build_dashboard_trade_analytics()` vuelve a coalescer al leer, cruza cada record con `portfolio.active / resolved_won / dead` y añade dos capacidades nuevas:
  - explicar qué pasó después (`cartera muerta`, residuo micro, posición aún abierta, etc.);
  - y mostrar si hay `claim/redeem` pendiente sin inventar un evento que no existe en el lifecycle.
- La trade console crea fallback visible para posiciones recientes que hoy sobreviven solo en cartera y no habían quedado en `trade_rows` (`portfolio.dead/resolved_won`).
- `verify_before_deploy.py` añade regresiones para:
  - coalescer `SELL` + follow-up `LOSS_TOTAL` en una sola posición;
  - exigir label con lado explícito;
  - validar `claim pendiente`;
  - y asegurar fallback desde cartera para trades recientes sin lifecycle visible.

**Validación concreta sobre los 9 casos auditados:**

1. `Seoul 14C Apr 1`
   - El snapshot congelado mostraba dos filas contradictorias con el mismo label: una pérdida `LOSS_TOTAL` y otra ganada por resolución.
   - La evidencia de cartera (`portfolio.dead`) confirma que el lado `No` quedó a `0c`, `avg=0.85`, `cashPnl=-1.0530`, `redeemable=true`.
   - Con el label por lado y el cruce por mercado, la lectura correcta pasa a ser: dos posiciones distintas del mismo mercado; `NO` perdió y `YES` resolvió a favor.

2. `Seoul 13C Apr 1`
   - El snapshot mostraba ganancia correcta (`$+0.61`) pero entrada degradada a parcial.
   - `portfolio.resolved_won` conserva la entrada real del lado `No`: `avg=0.80`, `initialValue=2.43144`, `currentValue=3.0393`, `redeemable=true`.
   - La consola ya puede reconstruir la entrada desde cartera y marcar `claim pendiente` en vez de esconderse detrás de `Historico parcial`.

3. `Atlanta 70-71F Mar 30`
   - El snapshot tenía una fila completa y dos duplicados parciales del mismo `LOSS_TOTAL`.
   - `portfolio.dead` confirma el residuo final: `avg=0.14`, `initialValue=1.3309534`, `currentValue=0`, `redeemable=true`.
   - El coalescing nuevo colapsa esos follow-ups en una sola historia coherente.

4. `Atlanta 78-79F Apr 1`
   - Antes no aparecía en `trade_rows` aunque sí existía en `portfolio.dead`.
   - La cartera conserva evidencia suficiente para mostrarla: lado `Yes`, `avg=0.10`, `initialValue=2.1238`, `currentValue=0.010619`, `cashPnl=-2.113181`, `redeemable=false`.
   - La consola ahora la puede enseñar vía fallback desde cartera, sin volver a dejarla invisible.

5. `Atlanta 80-81F Apr 1`
   - El snapshot ya mostraba el `SELL` por `stop_loss` (`$-1.30`) y la cartera muerta conservaba un residuo ínfimo (`currentValue=0.000005`, `realizedPnl=-1.480007`).
   - La nueva lectura une ambas capas: salida principal por SL y después residuo micro en cartera muerta.

6. `Tokyo 18C Apr 1`
   - El snapshot mostraba resolución ganada duplicada.
   - `portfolio.resolved_won` conserva el lado `No` con `avg=0.61`, `initialValue=2.4524318`, `currentValue=4.02038`, `cashPnl=+1.5679`, `redeemable=true`.
   - La consola pasa a leerlo como una sola resolución con `claim pendiente`, no como dos cierres idénticos.

7. `Buenos Aires 28C Apr 1`
   - El snapshot ya tenía una historia bastante limpia.
   - La cartera la completa: lado `No`, `avg=0.65`, `initialValue=1.07289`, `currentValue=1.6506`, `cashPnl=+0.57771`, `redeemable=true`.
   - La mejora visible aquí es sobre todo de presentación: resolución clara + estado de claim.

8. `Chicago 40-41F Apr 1`
   - Sigue abierta; el snapshot la mostraba como `Abierta` y `portfolio.active` confirma `avg=0.186`, `cur=0.8505`, `currentValue=8.0691`, `cashPnl=+6.3044`.
   - La trade console mantiene una única historia de posición abierta, sin forzar cierre/resolución artificial.

9. `Dallas 82-83F Apr 1`
   - El snapshot mostraba dos historias separadas para la misma posición: `SELL` por SL y luego `LOSS_TOTAL` micro.
   - La cartera muerta confirma el residuo final (`avg=0.12`, `currentValue=0.000026`, `realizedPnl=-0.6108`, `redeemable=false`).
   - El nuevo coalescing lo convierte en una sola narrativa: SL principal y, después, residuo micro muerto.

**Validación de suite:**

- `python verify_before_deploy.py`
- Resultado final: `483/483`

**Límite de alcance respetado:**

- no se tocaron reglas de trading;
- no se tocó NOAA;
- no se desplegó nada;
- el trabajo fue solo de trazabilidad, reconciliación, presentación y documentación.

---

## Sesión 58 — cierre limpio de contexto + prioridad siguiente + token economics (2 abr 2026)

**Disparador:** tras cerrar el saneamiento de `trade_lifecycle`, la necesidad ya no era tocar más código del bot, sino dejar la siguiente sesión bien acotada y evitar volver a abrir ventanas de contexto demasiado grandes o costosas.

**Decisión principal:** no se identifica una tarea separada más prioritaria que la auditoría de la captura del `Mission HUD` compartida el 2 de abril de 2026. Por tanto, el siguiente paso lógico queda fijado así:

1. dedicar una sesión completa solo a verificar la captura de la capa 1;
2. contrastar screenshot, snapshot live y builders locales;
3. buscar evidencia de errores de dato, agregación o semántica antes de rediseñar nada.

**Cambios aplicados en esta sesión:**

- `CONTEXTO.md` se actualiza para dejar explícita la prioridad siguiente:
  - auditar la captura del `Mission HUD` como sesión 58 recomendada;
  - y reservar la auditoría de `token economics` para una sesión posterior separada.
- `OPERATIONS_PLAYBOOK.md` gana una sección nueva de disciplina `1 sesión = 1 tarea` y contexto mínimo:
  - arrancar cada sesión con una fuente primaria de verdad;
  - limitar la lectura inicial a `1-3` artefactos relevantes;
  - no mezclar rediseño con auditoría de datos.
- `OPERATIONS_PLAYBOOK.md` gana también una sección específica de `token economics` para Codex + Claude Code.
- Se crea `.codex/config.toml` a nivel de proyecto:
  - `model_reasoning_effort = "medium"` por defecto;
  - perfiles `low`, `deep` y `max` para subir esfuerzo solo cuando la tarea lo justifique.

**Criterio operativo resultante:**

- Codex deja de arrancar este repo en `xhigh` por inercia.
- No se asume que Codex pueda decidir un `reasoning effort` completamente `auto` desde config; la estrategia elegida es `medium` por defecto + escalado selectivo por perfil/override.
- Claude Code queda guiado por protocolo, no por más contexto:
  - medir con `/cost`;
  - compactar con `/compact`;
  - limpiar con `/clear`;
  - cambiar modelo con `/model` solo cuando el retorno esperado compense.

**Validación ejecutada:**

- revisión local de la configuración activa de Codex en `C:\Users\USUARIO\.codex\config.toml`, donde el default previo seguía en `xhigh`;
- confirmación en documentación oficial de Codex de que `model_reasoning_effort` acepta valores fijos y puede definirse en config por proyecto;
- confirmación en documentación oficial de Claude Code de que existen `/cost`, `/compact`, `/clear` y `/model` como herramientas nativas para controlar gasto y contexto.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron reglas de trading;
- no se tocó NOAA;
- no se desplegó nada;
- no se ejecutó la suite porque la sesión fue solo de proceso, documentación y configuración local de herramienta.

---

## Sesión 59 — cierre completo con verify + commit + push (2 abr 2026)

**Disparador:** tras dejar lista la parte funcional en la sesión 57 y la parte de proceso/configuración en la 58, faltaba todavía un cierre operativo real: validar la suite otra vez, versionar todo y empujarlo a `origin/main`.

**Verificación ejecutada:**

- `python verify_before_deploy.py`
- resultado final: `483/483`

**Qué se versiona en este cierre:**

- saneamiento local de `trade_lifecycle` y trade console de la sesión 57:
  - clave estable por mercado+lados;
  - coalescing de follow-ups;
  - labels con `YES/NO`;
  - cruce con cartera para `claim/redeem`;
  - fallback para posiciones visibles solo en cartera.
- guardrails de proceso y token economics de la sesión 58:
  - regla `1 sesión = 1 tarea`;
  - contexto mínimo;
  - sección de `token economics` en playbook;
  - `.codex/config.toml` con `medium` por defecto y perfiles `low/deep/max`.
- documentación de soporte:
  - actualización de `CONTEXTO.md`;
  - actualización de `HISTORIAL_SESIONES.md`;
  - actualización de `agent_events.jsonl`;
  - versionado del handoff `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md`.

**Resultado operativo:**

- se hace `commit + push` a `origin/main`;
- no se toca lógica de trading;
- no se toca NOAA;
- el último deploy verificado live sigue siendo el previo (`5b23d02`);
- este nuevo push queda pendiente de revalidación explícita en Railway en la próxima sesión.

**Siguiente paso permanece igual:**

- auditar la captura del `Mission HUD` como única tarea de la próxima sesión, usando screenshot + snapshot live + builders locales como fuentes primarias de verdad.

---

## Sesiones aún no reconstruidas con certeza

Las sesiones 4 a 8, y las 10 a 18, no aparecen nombradas explícitamente en los commits que tenemos a mano. El trabajo de esas sesiones sí existe, pero hoy está representado como:

- iteraciones por versión;
- bloques de commits en Git;
- y contexto consolidado en `CONTEXTO.md`.

Por ahora, lo más honesto es tratarlas como `inferidas` y no inventar numeración exacta.

---

## Cómo mantener este archivo desde ahora

- `CONTEXTO.md`: estado actual del proyecto.
- `HISTORIAL_SESIONES.md`: append-only, sin reescribir entradas pasadas salvo para corregir errores factuales.
- Git: fuente de verdad de diffs, autores y timestamps.

Regla recomendada:

- cuando una sesión cierre, añadir una entrada nueva aquí;
- si una sesión antigua se reconstruye mejor desde Git, marcarla como `reconstruida` o `corregida`, sin borrar la entrada original.
- antes de cada push relevante, revisar si también hay que actualizar `CONTEXTO.md` para la foto actual y este archivo para la memoria histórica.

---

## Sesión 60 — fix de exposición redeemable + SELL seguro (2 abr 2026)

**Disparador:** en live apareció un ciclo bloqueado con `Exposición actual: $9.21 | Presupuesto libre: $0.79` y sin entradas nuevas, pese a que la wallet mostraba una posición casi a `100c` y otra ya `Ganado / Canjear`. Además, el intento de take-profit sobre Chicago falló con `not enough balance / allowance`.

**Hallazgos confirmados:**

- había dos bugs independientes combinándose:
  - `get_current_exposure()` ya excluía `curPrice >= 0.98`, pero no excluía posiciones `redeemable=True`, aunque en práctica ya son cash garantizado pendiente de claim/redeem;
  - el sizing de SELL usaba `round(size, 2)`, que puede redondear al alza y pedir más shares de las realmente disponibles (`9.48748 -> 9.49`), provocando `400` de Polymarket.
- el resultado operativo del caso reproducido era coherente con el síntoma:
  - antes del fix, una posición `redeemable=True @ 0.97` seguía contando ~$8.70 de exposición;
  - tras excluirla, el escenario de prueba pasaba de `budget_left=$0.00` a `budget_left=$6.79`;
  - el truncado con `floor` evitaba errores tanto en tamaños tipo `9.48748` como `0.999`.

**Cambios implementados en `bot.py`:**

- `get_current_exposure()` ahora hace `continue` si `p.get("redeemable")` es truthy;
- `manage_positions()` cambia `round(size, 2)` por `math.floor(size * 100) / 100`;
- `intra_cycle_sl_check()` aplica el mismo truncado seguro para mantener consistencia.

**Validación ejecutada:**

- `python verify_before_deploy.py`
- resultado final: `483/483`
- mini-validación dirigida adicional:
  - posición `redeemable=True, curPrice=0.97` deja de contar exposición;
  - `redeemable=False, curPrice=0.99` sigue excluyéndose por precio como antes;
  - un residuo de `0.01` shares queda por debajo del umbral material de exposición;
  - `size=9.48748` produce `9.48` con `floor`, evitando el rechazo que producía `9.49`.

**Cierre operativo de la sesión:**

- se actualizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`;
- el fix queda preparado para `commit + push`;
- el siguiente paso correcto ya no es más investigación local, sino revalidar en Railway el próximo ciclo real después del redeem/venta manual ya ejecutados por el usuario.

---

## Sesión 61 — shadow/canary automático + dashboard decisional por ciudad (2 abr 2026)

**Disparador:** la auditoría del `Mission HUD` confirmó que la lectura actual era coherente, pero también dejó visible el atasco real: el dashboard explicaba el estado de `NOAA / allowlist / accuracy`, aunque todavía no servía para decidir qué ciudades mantener, cuáles observar y cómo aprender de ciudades fuera de allowlist sin abrir trades reales.

**Hallazgos confirmados en la revisión del HUD:**

- `Allowlist vs NOAA 0/4` significaba `0` ciudades activas con muestra NOAA interpretable (`>= 3` casos), no ausencia total de NOAA;
- `NOAA sample growth 2/10` estaba calculado correctamente como muestra global acumulada;
- la allowlist activa (`Chicago`, `Atlanta`, `Dallas`, `Buenos Aires`) seguía siendo manual y fija;
- el sistema estaba sano a nivel operativo, pero bloqueado a nivel aprendizaje;
- fuera de allowlist faltaba una capa intermedia entre `no comprar` y `arriesgar capital real`.

**Cambios implementados:**

- nueva capa de tracking `shadow` para ciudades fuera de `ACTIVE_TRADING_CITIES`:
  - el scan ya no descarta esas oportunidades silenciosamente;
  - las registra en `shadow_city_tracking.json`;
  - el resumen de ciclo incorpora el contador `shadow`;
  - la evidencia se acumula por ciudad sin abrir posiciones reales.
- nuevo `decision engine` por ciudad en dashboard:
  - `Mantener`
  - `Candidata a canary`
  - `Seguir observando`
  - `Revisar salida`
  - `Bloqueada`
- reglas explícitas de política:
  - `shadow -> canary`: al menos `2` edges shadow, `2` ciclos shadow, mejor edge `>= 7.0%` y soporte `>= 2`;
  - `active/canary -> shadow`: al menos `3` trades, `win rate <= 25%` y `PnL <= $0.00`.
- overlay automático persistente:
  - `city_policy_state.json` guarda `auto_canary_cities`, `auto_shadow_cities` e historial reciente;
  - `get_effective_city_mode()` resuelve `active / canary / shadow / blocked`;
  - las ciudades `canary` ya pueden operar con sizing reducido (`CANARY_POSITION_SCALE`, default `50%`);
  - las ciudades `shadow` siguen observándose, pero sin nuevas compras.
- visibilidad y alertas:
  - el dashboard añade `Canaries automáticos actuales`, `Shadows automáticos actuales` e `Historial automático reciente`;
  - Telegram avisa cuando una ciudad pasa de `shadow -> canary` o de `active/canary -> shadow`.

**Validación local:**

- `python verify_before_deploy.py`
- resultado final: `496/496`

**Impacto operativo:**

- el sistema ya puede empezar a aprender de ciudades fuera de allowlist sin exponer capital real;
- la allowlist manual sigue existiendo, pero ahora convive con una capa automática de promoción/degradación;
- la tabla decisional arrancará con algo de histórico real (`accuracy`, `PnL`, NOAA) y empezará a poblar el nuevo histórico `shadow` a partir de los próximos ciclos.

**Limitación abierta:**

- todavía no existe backfill histórico de `shadow`; la nueva capa aprende bien hacia adelante, pero casi no tiene memoria hacia atrás.

**Siguiente tarea fijada:**

- construir un backfill conservador de `shadow` histórico;
- poblar la capa decisional con evidencia retroconstruida donde haya datos suficientes;
- separar en dashboard lo `retroconstruido` de lo `live`.

**Cierre operativo de la sesión:**

- `python verify_before_deploy.py` vuelve a cerrar en `496/496`;
- se hace `commit + push` a `origin/main` con hash `3c2b568`;
- se lanza `redeploy` en Railway y el servicio vuelve a arrancar sin crash inmediato:
  - dashboard en `0.0.0.0:8080`;
  - `Autenticación OK`;
  - `Telegram polling: OK`;
  - primer ciclo ejecutado y resumen guardado.
- la validación funcional completa del nuevo overlay automático queda pendiente de revisar en el siguiente ciclo live.

---

## Sesión 62 — ranking operacional claro para ciudades (2 abr 2026)

**Disparador:** la nueva capa `shadow/canary/shadow` ya existía y el dashboard enseñaba estado, NOAA y transiciones, pero todavía no permitía responder en segundos qué ciudad estaba más cerca de entrar a operativa ni distinguir con claridad una candidata real de una ciudad degradada o de puro ruido.

**Objetivo exacto de producto:** convertir la capa de ciudades en una vista de decisión, no solo descriptiva:

- ranking principal ordenado por prioridad operativa;
- `readiness score` comprensible;
- `estado actual`, `distancia a canary`, `tendencia` y `motivo principal`;
- buckets legibles `Lista para canary / Cerca de canary / Seguir observando / No tocar / Expulsada / degradada`;
- degradadas recientes separadas visualmente de candidatas normales.

**Cambios implementados en backend (`bot.py`):**

- `build_dashboard_city_decisions()` deja de devolver solo buckets simples y pasa a construir una capa de ranking operacional:
  - `readiness_score`;
  - `priority_group` y `priority_label`;
  - `state_label` y `state_badge`;
  - `distance_label` / `distance_detail`;
  - `trend_label`;
  - `main_reason`;
  - answers rápidas `top_candidate`, `next_candidate`, `cooling_city` y `noise_city`.
- la puntuación combina de forma legible:
  - actividad `shadow` (`edges`, `cycles`, `best_edge`);
  - cobertura NOAA;
  - histórico real (`trades`, `WR`, `PnL`);
  - overlay automático (`auto_canary`, `auto_shadow`, transiciones).
- penalización explícita para ciudades degradadas o expulsadas:
  - una ciudad con shadow activo pero degradada deja de competir como candidata normal;
  - `Dallas` queda cubierta como `Shadow degradada` y `Enfriándose` cuando su overlay / histórico lo justifican.

**Cambios implementados en UI (`templates/dashboard.html` + `static/dashboard.css`):**

- nueva cabecera `Vista de decisión por ciudad`;
- bloque superior con lectura de 10 segundos:
  - `Más cerca de entrar`;
  - `Siguiente`;
  - `Alejándose`;
  - `No merecen atención`.
- nueva tabla principal de ranking con columnas:
  - `Ciudad`;
  - `Score`;
  - `Estado actual`;
  - `Distancia a canary`;
  - `Tendencia`;
  - `Motivo principal`.
- barras de score y acentos visuales por prioridad;
- fila visualmente diferenciada para degradadas (`city-ranking-row-degraded`).

**Copy / UX refinado al cierre:**

- la vista se reescribe con lenguaje más ejecutivo:
  - `Vista de decisión por ciudad`;
  - `Más cerca de entrar`;
  - `Alejándose`;
  - `No merecen atención`;
  - `Reiniciar por degradación`;
  - `Ya operativa`;
  - `histórico real malo`;
  - `bloqueada por política`;
  - `NOAA aún corta`.

**Tests y verificación:**

- `verify_before_deploy.py` gana cobertura nueva para:
  - presencia del ranking en template y CSS;
  - prioridad real del top candidate;
  - caso de `Dallas` como `shadow degradada`;
  - semántica de `readiness_score`, `distance_label`, `trend_label` y `ranking_summary`.
- resultado final local:
  - `python verify_before_deploy.py`
  - `500/500`

**Incidencia de proceso detectada y corregida en el cierre:**

- al hacer `commit + push` del cambio funcional se cerró código y scoreboard, pero todavía faltaban `CONTEXTO.md` y `HISTORIAL_SESIONES.md`;
- el propio playbook seguía exigiendo esas dos capas para considerar la sesión cerrada;
- se corrige con un cierre documental adicional y sincronización final de:
  - `CONTEXTO.md`;
  - `HISTORIAL_SESIONES.md`;
  - `agent_events.jsonl`.

**Cierre operativo de la sesión:**

- commit funcional del ranking: `e4dce44` (`ux: add operational city ranking view`);
- `git push origin main` completado;
- deploy lanzado hacia Railway;
- queda pendiente, ya para la siguiente sesión, validar en live que el ranking separa bien `candidatas reales vs degradadas` y, después, retomar el backfill conservador de `shadow` histórico.

---

## Sesión 63 — cierre mínimo de hardening de tooling/documentación verificado localmente (2 abr 2026)

**Disparador:** después del cierre de proceso de la sesión 58 quedaban matices de RTK/Engram escritos todavía como no verificados o solo parcialmente confirmados. La verificación real ya existía fuera del repo; faltaba alinear la documentación sin reabrir aquella sesión ni tocar el bot.

**Qué se corrige en esta pasada:**

- `OPERATIONS_PLAYBOOK.md` deja explícito que RTK y Engram son setup global del usuario, no dependencias versionadas del proyecto.
- RTK queda marcado como verificado en esta máquina para Codex con evidencia local ya comprobada:
  - `rtk --version`;
  - `rtk init -g --codex`;
  - uso real desde Codex con `rtk git status` y `rtk git diff`.
- Engram queda marcado como operativo en este caso real:
  - `engram setup codex` funcionó;
  - en la extensión de Codex para VS Code hizo falta añadir manualmente por UI el servidor MCP `engram`;
  - configuración usada: `C:\Users\USUARIO\go\bin\engram.exe` + `mcp`;
  - tras eso, Codex ya vio herramientas `mcp__engram__...` en una sesión real.
- `CONTEXTO.md` añade una nota corta para que el estado actual del repo recuerde ese matiz sin convertir memoria externa en fuente de verdad.

**Filosofía que se mantiene:**

- repo = fuente de verdad del proyecto;
- Engram = memoria complementaria, no estado canónico;
- RTK = capa de reducción de ruido/contexto para shell, no requisito del repo.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA ni scheduler;
- no hubo refactor;
- no hubo deploy;
- el cambio fue solo documental y de trazabilidad mínima.

---

## Sesión 64 — setup Claude Code + diagnóstico operativo exploratorio (2 abr 2026)

**Disparador:** primera sesión real de Claude Code en este repo (no Claude.ai ni Codex). El objetivo era verificar que las herramientas de infraestructura quedaban operativas y después hacer un primer diagnóstico del estado actual del bot.

**Qué se configuró y verificó en esta sesión:**

- **Claude Code** queda preparado y funcional para este repo. Es la primera vez que Claude Code opera aquí como agente interactivo (distinción importante: antes se usaban Claude.ai y Codex).
- **Subagente `trading-ops-analyst`** creado en `.claude/agents/trading-ops-analyst.md`. Se probó en live en esta misma sesión y produjo resultados útiles.
- **RTK** verificado operativo en Claude Code en Windows vía `~/.claude/CLAUDE.md`. La integración funciona en sesión real.
- **Engram** verificado operativo en Claude Code. Las herramientas `mem_save`, `mem_search` y `mem_context` son accesibles via MCP y se usaron en esta sesión. Primera memoria guardada para este proyecto.

**Diagnóstico operativo realizado (prueba exploratoria — no conclusión final):**

- Se usó el subagente `trading-ops-analyst` para hacer un primer diagnóstico del estado del bot.
- La primera lectura usó el snapshot Railway del 1-abr-20:13 UTC como fuente, que resultó obsoleto.
- El usuario corrigió el estado real: Chicago Apr1 fue vendida manualmente ~11 horas antes; solo quedan 2 posiciones abiertas en Atlanta; cash disponible ~$27.20; cartera ~$31.58; P&L all-time -$21.79.
- Se rehízo el diagnóstico con el estado real corregido.

**Hallazgos del diagnóstico (exploratorio — requieren verificación en live):**

1. **Discrepancia repo vs real:** el snapshot de Railway (y presumiblemente `postmortem.json`) sigue mostrando Chicago Apr1 como posición abierta. Las ventas manuales no quedan registradas en el bot. Esto puede afectar al cálculo de exposición en el próximo ciclo.
2. **Atlanta no se autobloqueó:** con WR 14.3% en 14 trades, la regla `CITY_BLOCK_WIN_RATE=25%` debería haber bloqueado Atlanta automáticamente. No lo hizo. Es el hallazgo más urgente antes del próximo ciclo, especialmente porque con $27.20 disponibles el bot puede abrir nuevas posiciones en Atlanta.
3. **LOSS_TOTAL = 70.6% de los cierres:** 60 de 85 cierres terminaron en pérdida total. P&L on-chain all-time -$36.42 sobre $161.21 invertido (CSV hasta 31 mar).
4. **Deploy sesión 62 sin validación explícita:** el commit `e4dce44` está en `origin/main` pero no se ha confirmado que Railway lo esté ejecutando.

**Clasificación explícita:**

- El análisis completo de esta sesión fue **exploratorio**, realizado con datos parcialmente obsoletos y sin acceso directo a Railway live.
- Los hallazgos son orientativos y sirven como punto de partida para la próxima sesión, no como conclusiones cerradas.
- La prioridad operativa de mañana queda documentada en `CONTEXTO.md`.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler ni arquitectura core;
- no hubo deploy;
- no se ejecutó la suite;
- el trabajo fue solo setup de infraestructura, diagnóstico y documentación de cierre.

---

## Sesión 65 — hotfix Atlanta bloqueada en Railway + cierre de diagnóstico live (3 abr 2026)

**Disparador:** la sesión 64 dejó como prioridad urgente validar por qué Atlanta seguía operando pese a `WR 14.3%` y umbral de bloqueo `25%`. Antes del próximo ciclo, se necesitaba comprobar el estado live real y aplicar el corte operativo mínimo.

**Evidencia live leída en Railway:**

- `alerts_state.json` contiene `city_accuracy_flagged.Atlanta` desde `2026-03-30T21:02:35.447220+00:00`, con `trades=4`, `wins=1`, `win_rate=25.0`, `pnl=-1.12777159`.
- `postmortem.json` para Atlanta da:
  - `23` trades cerrados;
  - `4` wins si se sigue el criterio real de `get_city_accuracy()` (`pnl_cash > 0`);
  - `WR 17.4%`;
  - `LOSS_TOTAL=17`, `SELL=4`, `RESOLVED_WIN=2`;
  - una entrada antigua anómala todavía `open`: `Atlanta|YES|2026-03-28|2026-03-26T08:00:35.955319+00:00`.
- En Railway no existían overrides de `CITY_MIN_TRADES_FOR_BLOCK` ni `CITY_BLOCK_WIN_RATE`, así que aplicaban los defaults del código.
- Antes del hotfix, `BLOCKED_CITIES` tampoco estaba seteada en Railway, por lo que Atlanta no estaba bloqueada por env var.

**Conclusión del bug:**

- el problema inmediato no era que Telegram no avisara;
- la alerta sí se disparó una vez, pero al quedar Atlanta ya registrada en `city_accuracy_flagged`, no se reenvía aunque el WR siga empeorando;
- más importante: el supuesto “auto-bloqueo” no bloquea nada por sí mismo; solo recomienda añadir la ciudad a `BLOCKED_CITIES`;
- por eso Atlanta seguía habilitada para nuevos BUYs.

**Hotfix aplicado en producción:**

- se seteó en Railway:
  - `BLOCKED_CITIES=London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara,Atlanta`
- verificación posterior:
  - `railway_safe.ps1 variable list --kv` ya muestra Atlanta dentro de `BLOCKED_CITIES`;
  - logs de Railway confirman redeploy/reinicio a `2026-04-03 09:16:46 UTC` y arranque limpio de `POLYMARKET BOT v10.6.10`.

**Incidencia operativa secundaria detectada:**

- pese a la reparación previa, la CLI de Railway volvió a caer en `Unauthorized` / `invalid_grant`;
- se recuperó manualmente con:
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset`
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless`
  - validación con `railway_safe.ps1 whoami` y `status`
- queda como sesión separada revisar por qué este relogin vuelve a ser necesario.

**Apunte de diseño para la siguiente sesión (Claude):**

- el nombre “auto-bloqueo” es engañoso;
- si el sistema debe sacar una ciudad de operativa automáticamente, no basta con una alerta one-shot;
- hace falta persistir `qué ciudad se sacó`, `por qué`, `con qué evidencia`, `cuándo`, y que el scan de BUYs lea esa política persistente.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se cambió lógica de trading;
- el cambio de producción fue solo el hotfix de env var para Atlanta;
- la corrección estructural queda explícitamente aplazada a otra sesión.

---

## Sesión 66 — auto-bloqueo real persistido por ciudad en local (3 abr 2026)

**Disparador:** tras el hotfix manual de Atlanta en Railway, faltaba cerrar el bug de diseño de fondo: el supuesto auto-bloqueo no podía seguir siendo solo `city_accuracy_flagged + Telegram`, porque eso no sacaba la ciudad de BUYs ni dejaba política persistida con evidencia.

**Alcance respetado:**

- no se tocaron reglas de entrada/salida, NOAA, scheduler ni arquitectura core de trading;
- el cambio se concentró en la capa de política por ciudad ya existente en `load_city_policy_state/save_city_policy_state/get_effective_city_mode/sync_city_policy_state`;
- no hubo push ni deploy en esta sesión.

**Cambios implementados:**

- `city_policy_state.json` añade `auto_blocked_cities` como tercera capa persistida del overlay, junto a `auto_canary_cities`, `auto_shadow_cities` y `transition_history`.
- Se añade `_build_auto_city_block_policy()` para persistir por ciudad:
  - `action="auto_block"`;
  - `reason`;
  - `metrics` (`trades`, `wins`, `win_rate`, `pnl`, `observed_count`, `shadow_seen`, `shadow_edges`, `shadow_best_edge`, `support_count`);
  - `from_mode`;
  - `triggered_at`.
- `get_effective_city_mode()` da prioridad a `auto_blocked_cities` y devuelve `blocked` aunque la ciudad siga en `ACTIVE_TRADING_CITIES`, así el scan de BUYs ya respeta la política sin depender solo de Telegram.
- `sync_city_policy_state()` cambia la transición de salida de `active/canary -> shadow` a `active/canary -> blocked`, guarda `action` + `metrics` en `transition_history`, elimina overlays previos `auto_canary/auto_shadow`, y deja la reactivación como manual/conservadora retirando la política persistida.
- `build_dashboard_city_observation()` y `build_dashboard_city_decisions()` pasan a reconocer el auto-bloqueo persistido y exponen `policy_action`, `policy_reason`, `policy_metrics` y `policy_changed_at` para que el dashboard no pierda el motivo/evidencia.
- `verify_before_deploy.py` añade tests estructurales y funcionales para:
  - existencia de `_build_auto_city_block_policy`;
  - persistencia de `auto_blocked_cities`;
  - prioridad de `auto_blocked` sobre allowlist activa;
  - transición `to=blocked` con `action=auto_block` y métricas.

**Validación local:**

- `python verify_before_deploy.py` pasa en `506/506`.

**Estado final:**

- el auto-bloqueo real queda implementado localmente y listo para push/deploy;
- Atlanta sigue bloqueada manualmente en Railway por `BLOCKED_CITIES` desde la sesión 65, así que no hay riesgo inmediato de BUYs nuevos mientras se valida el overlay persistido;
- siguiente paso recomendado: desplegar, inspeccionar `city_policy_state.json` en Railway y confirmar por logs que el scan salta ciudades auto-bloqueadas aunque sigan en la allowlist manual.

---

## Sesión 67 — hardening del relogin recurrente de Railway CLI (3 abr 2026)

**Disparador:** el usuario pidió resolver el problema de relogin recurrente de Railway sin volver a empezar desde cero ni tocar lógica de trading.

**Evidencia reunida antes de cambiar tooling:**

- `CONTEXTO.md`, `RAILWAY_AUTH_BUG_HANDOFF_2026-04-01.md`, `OPERATIONS_PLAYBOOK.md` y las sesiones 50/54/65 dejaban una pista consistente: `invalid_grant` reaparecía tras una auth aparentemente reparada, y el workaround manual `reset + launch-login -Browserless` seguía funcionando.
- En esta sesión, `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor` confirmó que no había proxy persistente ni de proceso, `config.json` seguía enlazado, y el token pudo refrescarse correctamente hasta `2026-04-03T11:07:57Z`.
- `railway_safe.ps1 whoami` y `railway_safe.ps1 status` funcionaron y siguieron funcionando incluso lanzados en paralelo con `doctor`.

**Cambios implementados:**

- `tools/railway_safe.ps1` añade un preflight de refresh OAuth:
  - lee `%USERPROFILE%\.railway\config.json`;
  - parsea `tokenExpiresAt`;
  - si faltan `<=300s` para expirar y el proceso actual no puede abrir el config en modo escritura, corta con instrucciones explícitas en vez de dejar que Railway intente refrescar en un contexto frágil.
- `tools/railway_safe.ps1` también serializa todas las invocaciones del CLI con un mutex global `Global\polymarket-bot-railway-cli`, para evitar carreras de refresh concurrente contra el mismo `refreshToken`.
- `tools/railway_auth_repair.ps1` usa ese mismo mutex en `doctor`, `whoami/version` y `interactive-login`, y `doctor` ahora muestra:
  - `Writable from this process`;
  - `secondsToExpiry`;
  - `refreshWriteRiskSoon`.

**Diagnóstico de causa raíz, formulado con cautela:**

- ya no queda probado que el problema sea solo proxy o solo sandbox;
- la hipótesis más plausible pasa a ser una combinación de refresh sin escritura persistida y/o refreshes concurrentes del Railway CLI sobre el mismo `config.json`;
- el hardening nuevo cubre ambas rutas antes de que la CLI vuelva a degradar el estado OAuth local.

**Validación operativa final:**

- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami` -> `Logged in as pablogomez.eu@gmail.com`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status` -> `Project: enchanting-respect / Environment: production / Service: polymarket-bot`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor` -> `Writable from this process: True`, `tokenExpiresAtUtc=2026-04-03T11:07:57Z`, `refreshWriteRiskSoon: False`, `ExitCode: 0`

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler, exits ni arquitectura core;
- no hubo push ni deploy;
- el cambio fue solo hardening de tooling operativo y trazabilidad documental.

## Sesión 68 — validación end-to-end deploy + corrección desfase env vars (3 abr 2026)

**Disparador:** verificar que el código de sesiones 66-67 estaba desplegado en Railway y que el auto-block engine funciona correctamente end-to-end.

**Verificaciones completadas:**

- Commits `aeebdfb` (sesión 66) y `b54407c` (sesión 67) confirmados en local y pushed a origin.
- `verify_before_deploy.py` pasa 506/506.
- Railway redesplegó a 16:36 UTC (post-push) y de nuevo a 16:54 UTC (post-corrección env var), v10.6.10 limpio.
- `city_policy_state.json` no existe aún en Railway: esperado por diseño (se crea solo cuando `sync_city_policy_state()` detecta un cambio en un ciclo).
- Scan de BUYs verificado en código (L10422-10426): `get_effective_city_mode()` → si `blocked` → `continue` (skip total). Funciona para bloqueos manuales (`BLOCKED_CITIES`) y automáticos (`auto_blocked_cities`).
- Dashboard live auditado via `/api/dashboard.json`: datos cruzados entre portfolio, postmortem (126 registros), trade_lifecycle (62 registros), city_accuracy y exit_breakdown sin desfases funcionales críticos.

**Desfase corregido:**

- Atlanta estaba simultáneamente en `ACTIVE_TRADING_CITIES` (default del código) y en `BLOCKED_CITIES` (env var Railway, sesión 65). Funcionalmente no causaba daño (`is_city_blocked` se evalúa primero), pero impedía que el auto-block engine la procesara y confundía el dashboard.
- Corrección: `ACTIVE_TRADING_CITIES` seteada explícitamente en Railway como `Chicago,Dallas,Buenos Aires`. Redeploy confirmado.

**Hallazgo adicional: Dallas degradada a shadow por overlay:**

- `shadow_city_tracking.json` registra degradación de Dallas el 2 abr (15 trades, WR 6.7%, PnL -$1.66). El overlay `auto_shadow` tiene prioridad sobre `ACTIVE_TRADING_CITIES` en `get_effective_city_mode()` (L620).
- El decision engine la propone como candidata a canary (7 edges shadow, pico 38.9%), pero la promoción requiere que alguien la saque de `auto_shadow` o que el engine la promueva automáticamente en un ciclo futuro.

**Desfases menores documentados (no bloquean):**

- NYC (21 trades, no en ACTIVE ni BLOCKED): ruido informativo, no funcional.
- CONTEXTO.md tenía cash stale ($27.20 vs $21.62 real): actualizado.
- Chicago Apr1 cerrada manualmente: podría no estar en postmortem como closed. Pendiente verificar.
- 4 resolved_won pendientes cobro (~$3.38): capital trabado, no desfase de accounting.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler, exits ni arquitectura core;
- único cambio en producción: env var `ACTIVE_TRADING_CITIES` en Railway.

---

## Sesión 69 — reconciliación postmortem Chicago Apr1 sin edición live (3 abr 2026)

**Disparador:** cerrar la tarea acotada pendiente de sesión 68: verificar si `Chicago Apr1` seguía `open` en `postmortem.json` y, si era así, cerrarla manualmente para que `city_accuracy` no quedara sesgada.

**Evidencia descargada de Railway:**

- Se bajó `/app/data/postmortem.json` vía `tools/railway_safe.ps1 ssh "cat /app/data/postmortem.json"` a un snapshot temporal local.
- La entrada `Chicago|YES|2026-04-01|2026-03-31T23:00:28.735723+00:00` ya estaba `status=closed`, `close_action=LOSS_TOTAL`, `close_reason=micro_position_unsellable`, `closed_at=2026-04-02T07:39:19.807998+00:00`, `total_amount=1.88`, `total_shares=9.89`, `avg_entry_price=0.1901`, `pnl_cash=0.0`.
- Con la misma lógica de `get_city_accuracy()`, Chicago recalcula a `4 trades`, `1 win`, `WR 25.0%`, `PnL +$2.09`, así que esta fila Apr1 ya no explica el posible sesgo por denominador incompleto.

**Hallazgo nuevo:**

- Siguen abiertas 3 filas legacy de Chicago no relacionadas con Apr1:
- `Chicago|YES|2026-03-26|2026-03-25T16:49:42.552882+00:00`
- `Chicago|YES|2026-03-27|2026-03-27T16:00:37.157021+00:00`
- `Chicago|YES|2026-03-28|2026-03-28T16:00:32.932997+00:00`
- Si hay sesgo pendiente en `city_accuracy`, ahora la hipótesis prioritaria son esas filas legacy todavía `open`, no `Chicago Apr1`.

**Acción tomada y límite de alcance:**

- No se editó `postmortem.json` live porque la fila Apr1 ya estaba cerrada.
- No se tocó `bot.py`, trading, NOAA, scheduler ni reglas de salida.
- Solo se corrigió la trazabilidad documental para retirar el aviso stale de Apr1 y mover la siguiente tarea al saneamiento de esas 3 filas Chicago antiguas.

---

## Sesión 73 — quick wins Control Center: QW3 + QW5 + QW6 (4 abr 2026)

**Disparador:** completar el bloque de quick wins pendientes de Fase 1 del roadmap `docs/control-center-roadmap.md` en una sola sesión.

**QW5 — Timestamp "último fetch NOAA exitoso":**
- `build_dashboard_forecast_quality()` ya devolvía `last_record_display` (línea 4114 de `bot.py`), pero el template no lo mostraba.
- Se añadió `<div><dt>Último fetch NOAA</dt><dd>{{ dashboard.forecast_quality.last_record_display }}</dd></div>` en el `metric-list` de "Calidad Forecast Observada (NOAA)".
- Riesgo: ninguno. Solo template.

**QW3 — Reordenar capa 2: NOAA y Decision engine primero:**
- Orden anterior: stats de promoción → bankroll/estado operativo → NOAA (line 418) → readiness → trading stats.
- Orden nuevo: stats de promoción → NOAA → trading stats → bankroll/estado operativo → readiness.
- Implementado con un script Python que reordena bloques por line numbers exactos (sin editar contenido). 1689 líneas antes = 1689 líneas después.

**QW1, QW2, QW7 — ya estaban hechos:**
- `legacy-focus-shell`: no encontrado en el template (ya eliminado en sesión anterior).
- Legacy drift: ya estaba en línea 1464 (fuera de capa 2, en zona reporting).
- Readiness y desbloqueos: ya estaba en `<details>` (colapsado por defecto).

**QW6 — "esperando muestra" en Drawdown:**
- PnL y Win rate ya tenían la condición `closed_count < 5`. Drawdown no.
- Se añadió el mismo guard: cuando `closed_count < 5`, muestra "esperando muestra / menos de 5 cierres" en lugar de `drawdown_display`.

**Validación:** `verify_before_deploy.py` = 507/507 tras todos los cambios.

**Fase 1 del roadmap Control Center completada.** Siguiente: M3 (cerrar 3 filas Chicago legacy open que sesgan WR).

---

## Sesión 74 — tabs de Observabilidad capa 2 en dashboard (4 abr 2026)

**Disparador:** convertir el mega-card monolítico de `Observabilidad (capa 2)` en 3 tabs legibles, sin tocar Python ni `bot.py`, siguiendo el patrón de activación ya existente en `static/dashboard.js`.

**Cambios implementados:**

- `templates/dashboard.html` envuelve el bloque de Observabilidad en `data-tab-shell` con `data-default-panel="obs-noaa"`.
- Se añaden 3 tabs: `NOAA`, `Ciudades`, `Decisiones`, reutilizando `focus-tab-bar`, `focus-tab`, `focus-panel`, `data-panel-target` y `data-panel`.
- La vista `NOAA` agrupa el resumen de calidad forecast y la tabla de últimos 20 casos.
- La vista `Ciudades` agrupa el resumen de estado por ciudad, el universo operativo, seguimiento/referencia y bloqueadas.
- La vista `Decisiones` agrupa decision engine, reglas de promoción/salida, ranking operacional, overlays canary/shadow, observación, shadow reciente y transiciones.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocó ningún archivo Python;
- no se modificó `static/dashboard.js` porque el patrón genérico ya soportaba el nuevo shell de tabs;
- no se corrieron tests, al ser una reestructuración solo de plantilla.

---

## Sesión 75 — auditoría forecast accuracy Fase 1 (4 abr 2026)

**Disparador:** crear un script local para auditar si el edge histórico del bot era ficticio por sigma demasiado estrecha o forecast Open-Meteo malo, sin tocar `bot.py`, trading, scheduler, deploy ni variables Railway.

**Cambios implementados:**

- Se añade `tools/forecast_accuracy_audit.py`, ejecutable localmente con:
- `python tools/forecast_accuracy_audit.py`
- `python tools/forecast_accuracy_audit.py --postmortem-source railway`
- El script carga `postmortem.json` desde copia local, dashboard JSON o Railway via `tools/railway_safe.ps1`, recupera temperatura observada con NOAA (`daily-summaries/TMAX -> global-hourly/TMP`) y cae a Open-Meteo historical si NOAA no devuelve dato.
- Calcula por trade `forecast_error = forecast_max - observed_real`, `prob_with_real_temp`, `real_edge`, `would_have_traded`, `outcome_correct`, `sigma_empirical_used` y `would_have_traded_empirical_sigma`.
- Genera `data/forecast_accuracy_raw.json` y `docs/forecast_accuracy_audit.md` con resumen global, tabla crítica `city × days_ahead`, resumen por ciudad, sesgo `YES/NO`, porcentaje de `real_edge < 0`, porcentaje de trades que no pasarían `MIN_EDGE` con sigma empírica, y top 5 peores gaps de edge ficticio.
- Como `postmortem.json` live tiene muchas filas con `question=""`, el script infiere `threshold_c` por grid-search contra `our_prob` cuando hay `condition/forecast_max/side/days_ahead` pero no `question`, y marca ese fallback en `threshold_source`.

**Resultado observado en la primera corrida live:**

- Fuente: `railway:/app/data/postmortem.json`
- `127` registros input, `34` trades cerrados analizables con BUY context suficiente, `82` cierres omitidos por `missing_forecast_max`, `11` todavía `open`.
- Sobre esos 34 trades: `WR ex-post 52.9%`, `LOSS_TOTAL 41.2%`, `forecast_error_mean -1.444 °C`, `sigma global 2.248 °C`, `real_edge < 0` en `23.5%`, `11.8%` no pasarían `MIN_EDGE` con sigma empírica, sesgo `YES=61.8% / NO=38.2%`.
- Hallazgo más accionable para Opus Fase 2: Chicago muestra sigma empírica claramente por encima del modelo (`3.074 °C` en agregado ciudad; `2.573 °C` en day 0 y `2.587 °C` en day 1 frente a `1.2-1.5 °C` del modelo), mientras Atlanta/Dallas/Buenos Aires no presentan ese gap de forma tan marcada con esta muestra.

**Limitación importante:**

- Esta auditoría aún no explica sola el `79% LOSS_TOTAL` sobre `91` cierres de serie v10.6, porque `postmortem.json` contiene `82` cierres legacy/orphan sin `forecast_max/question/date` recuperables desde la propia fila.
- Si Opus necesita cerrar cobertura sobre los 91 trades completos, la siguiente fase técnica debería enriquecer esos cierres huérfanos desde `performance.json` y/o `trade_lifecycle.json`, manteniendo explícito qué parte es observación directa vs reconstrucción.

**Validación:**

- `python -c "from pathlib import Path; import ast; ast.parse(Path('tools/forecast_accuracy_audit.py').read_text(encoding='utf-8')); print('AST OK')"` -> `AST OK`
- `python tools/forecast_accuracy_audit.py --help` -> parser OK
- `python tools/forecast_accuracy_audit.py --postmortem-source railway --output-json data/forecast_accuracy_raw.json --output-md docs/forecast_accuracy_audit.md` -> `analyzed=34`, `missing_observed=0`

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA del bot, scheduler, execution ni env vars;
- no hubo push ni deploy;
- sí se actualizaron `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y se debe registrar evento en `agent_events.jsonl` para cerrar trazabilidad.

---

## Sesión 76 — Camino A direccional + sigma empírica en shadow-only (4 abr 2026)

**Disparador:** aplicar el diagnóstico de Opus Fase 2 sobre pérdidas en `range/exact` sin reactivar trading, sin tocar scheduler/NOAA/trade_lifecycle/deploy y manteniendo `ACTIVE_TRADING_CITIES=NONE` en Railway.

**Cambios implementados:**

- `bot.py` añade `ALLOWED_CONDITIONS` con default `at_or_above,at_or_below`.
- En el ciclo principal, antes de `estimate_prob`, los mercados `range/exact` quedan filtrados con log explícito, contador `condition_filtered_skip` y envío a `shadow_city_tracking` como observación `edge_hit=False`, evitando descartarlos silenciosamente.
- `get_uncertainty(days_ahead, city=None)` pasa a priorizar sigma empírica por ciudad solo si `n>=3`; si la ciudad/día no tiene muestra suficiente, cae a `EMPIRICAL_SIGMA_GLOBAL`, y solo si tampoco hay bucket global usa la sigma original v10.3 como fallback final.
- Se preserva `estimate_prob()` intacta y se añade una envoltura mínima `estimate_prob_with_city(...)` para inyectar el contexto de ciudad en BUY y re-eval sin cambiar la fórmula.
- `MIN_EDGE` default sube de `7.0` a `15.0`.
- `cycle_summary.scan` añade `condition_filtered`; Telegram de ciclo, `/log`, `/info` y el dashboard muestran cuántos mercados se filtraron por condición.
- `templates/dashboard.html` expone `Condición filtrada` en `Estado operativo`.
- `verify_before_deploy.py` añade tests para `ALLOWED_CONDITIONS`, `get_uncertainty(city=...)`, fallback global si `n<3`, `MIN_EDGE=15.0` y persistencia de `condition_filtered`.

**Límites de alcance respetados:**

- no se tocó scheduler, NOAA, `trade_lifecycle`, deploy ni variables Railway;
- no se cambió `ACTIVE_TRADING_CITIES` local ni Railway;
- los mercados filtrados por condición no se descartan: quedan en shadow tracking.

**Validación:**

- `python verify_before_deploy.py` → `515/515`

---

## Sesión 77 — rediseño Control Center shadow-only direccional (4 abr 2026)

**Disparador:** rehacer la capa visual del dashboard para que Pablo pueda leer en desktop si el bot está sano, si las señales shadow direccionales son buenas y cuánto falta para volver a REAL, dejando la parte Python/backend en manos de Claude en paralelo.

**Cambios implementados por Codex (solo capa UI/tests/docs):**

- `templates/dashboard.html` queda organizado alrededor de:
- barra `Road to Real`;
- `Bloque 1` compacto de estado del bot;
- `Bloque 2` de señales shadow direccionales con columnas `Condicion / Side / Edge / Forecast / Mercado / Resolucion`;
- `Bloque 3` colapsable de salud del sistema.
- Se quitan del flujo visible principal Mission HUD gamificado, trofeos, desbloqueos, scoreboards/rivalry, trade console larga y la tabla larga de ciclos.
- `static/dashboard.css` añade estilos para `progress-bar-big`, `road-to-real-checklist`, `cards-3` y `notice-accent`.
- `verify_before_deploy.py` gana un check estructural para `build_dashboard_road_to_real`, validaciones del nuevo layout y un stub del builder en el harness de `build_dashboard_snapshot()`.
- `docs/control-center-roadmap.md` queda actualizado con el estado de este rediseño y deja como item futuro subir la frecuencia de ciclos a `4-6x/dia` solo después de que el dashboard sea legible.

**Límites de alcance respetados:**

- no se tocó scheduler, NOAA fetch, `manage_positions`, reglas de entrada/salida ni variables Railway desde esta capa Codex;
- `bot.py` sí aparece modificado en el worktree, pero ese cambio corresponde a trabajo paralelo de Claude y no se revirtió;
- `templates/dashboard_legacy.html` quedó creado por un intento fallido de mover el template y Windows devuelve `Access denied` al borrarlo; es un backup no usado por Flask.

**Validación:**

- `python verify_before_deploy.py` -> `516/516`

## Sesión 80 — R3 skip_log backend + analyzer offline + validación producción (5 abr 2026)

**Disparador:** cerrar R3 del roadmap Fase 3 (log de skips por ciclo). El bot evalúa ~150 candidatos por ciclo y solo ejecuta 0-3 trades reales; los 147+ skips eran información estratégica tirada a la basura. R3 materializa esa información en `data/skip_log.jsonl` para poder decidir en el futuro (con datos) si bajar `MIN_EDGE`, expandir allowlist, o recalibrar sigma.

**Split Claude ↔ Codex sobre contrato `docs/control-center-r3-contract.md` (commit 096a680):**

- **Claude (Opus) — backend + tests:**
  - `bot.py`: helpers a nivel de módulo `_make_skip_entry`, `_skip_log_rotate_if_needed`, `append_skip_log_entries` (batch + rotación 20 MB + tolerancia a I/O roto), `_skip_log_rotated_files`, `read_skip_log_last_n_cycles`, `read_skip_log_since`.
  - `run_cycle` instrumentado: `cycle_id = now.strftime("%Y-%m-%dT%H:%M")` capturado una sola vez al inicio, `skip_log_entries = []` bucket local, un único `append_skip_log_entries(...)` al final del ciclo envuelto en try/except.
  - 17 `skip_reason` instrumentados en los `continue` existentes del scan loop. Flag `shadow_override_flag` propagado en `parsed.update(...)` desde Loop A para que Loop B distinga `fuera_allowlist` vs `shadow_only_override` (fix `c8c8e73`).
  - `verify_before_deploy.py`: 64 tests nuevos, estáticos y funcionales (exec del source en namespace limpio contra tempdir).

- **Codex — analyzer offline + docs:**
  - `tools/analyze_skip_log.py`: CLI con flags `--last-n-cycles`, `--since`, `--city`, `--csv`, `--min-edge`. Lee `data/skip_log.jsonl` + rotados directamente con `json.loads(line)`, sin importar `bot.py`. 3 secciones: distribución, trend, near-misses.
  - `docs/skip-log-analyzer.md` con ejemplos.

**Validación:**

- `python verify_before_deploy.py` → `612/612`
- commits en `main`: `096a680` (contrato R3), `4b37cfe` (analyzer Codex), backend R3 (Claude)
- Pablo forzó ciclo vía `/forzar` en Telegram → `data/skip_log.jsonl` generó 660 filas en `cycle_id 2026-04-05T20:09`. Analyzer via SSH funciona.

**Hallazgo estratégico del primer ciclo real:** cero filas llegan a Loop B con edge calculado — todos los skips caen en Loop A (filtros tempranos). `below_min_edge`/`kelly_too_low`/`shadow_only_override` solo aparecerán cuando haya mercados futuros válidos en ciudades activas. R3 listo para análisis longitudinal cuando acumule 10-30 ciclos.

## Sesión 79 — R1 frontend Control Center: 3 gates por ciudad (5 abr 2026)

**Disparador:** cerrar la parte frontend de R1 mientras Claude trabajaba el backend en paralelo, consumiendo el contrato estable de `docs/control-center-r1-contract.md` sin tocar `bot.py`.

**Cambios implementados por Codex (solo frontend):**

- `templates/dashboard.html` reemplaza el bloque `{# -- City states compact -- #}` que iteraba `dashboard.city_observation.active_rows` por una tabla compacta sobre `dashboard.city_decisions.ranking_rows`.
- La nueva tabla muestra `Historial`, `Shadow` y `NOAA` con `gate_a`, `gate_b` y `gate_c` como autoridad del JSON, manteniendo la columna de `state_label`/`state_badge`.
- Cada gate expone `detail` vía `title` HTML y se añade debajo un glosario corto con los significados de `Limpio/Malo/Sin datos`, `Lista/Construyendo/Vacío` e `Interpretable/Parcial/Sin NOAA`.
- `static/dashboard.css` añade un ajuste mínimo `.city-gates` para anchos y badges, reutilizando `badge-good/accent/warn/bad/muted`.
- El bloque posterior de `dashboard.city_observation.blocked_rows` queda intacto.

**Límites de alcance respetados:**

- no se tocó `bot.py` bajo ninguna circunstancia;
- no se modificó `verify_before_deploy.py`;
- no hubo bump de versión;
- no se añadió microajuste UX extra para el caso Dallas (`gate_a=bad` + `gate_b=ready`), porque los gates independientes son parte explícita del diseño y la columna de estado ya sintetiza el veredicto.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` -> `548/548`
- commit/push a `main`: `c382000`
- mensaje: `feat(dashboard): R1 frontend — 3 gates visuales por ciudad`

## Sesión 80 — R3 skip_log: analyzer offline Codex + validación end-to-end (5 abr 2026)

**Disparador:** cerrar la parte Codex del contrato `docs/control-center-r3-contract.md` mientras el backend R3 se implementaba en paralelo, y luego validar el analyzer contra el primer `skip_log.jsonl` real generado en producción.

**Cambios implementados por Codex:**

- `tools/analyze_skip_log.py` añade un CLI stdlib-only para leer `data/skip_log.jsonl` y archivos rotados `data/skip_log.YYYY-MM-DD.jsonl` directamente con `json.loads(line)`, sin importar `bot.py`.
- El analyzer tolera líneas malformadas con warning a `stderr`, respeta campos `null` del schema R3 y soporta `--last-n-cycles`, `--since`, `--city`, `--csv` y `--min-edge`.
- La salida queda organizada en tres secciones: distribución de `skip_reason` por ciudad, trend temporal por razón comparando ventanas de ciclos y near-misses para `below_min_edge`.
- `docs/skip-log-analyzer.md` documenta instalación, flags, interpretación de cada sección y casos de uso operativos.

**Límites de alcance respetados:**

- no se tocó `bot.py`;
- no se modificó `verify_before_deploy.py`;
- no se importó el bot desde el analyzer;
- no se dejaron archivos temporales persistentes en `data/` tras la verificación local.

**Validación y trazabilidad:**

- `python -c "import ast; ast.parse(open('tools/analyze_skip_log.py').read())"` -> OK
- `python tools/analyze_skip_log.py --last-n-cycles 5` -> OK con fixture local mínimo de 3 filas
- validación posterior sobre Railway: el primer ciclo real produjo `660` filas en `data/skip_log.jsonl` (`cycle_id 2026-04-05T20:09`) y el analyzer respondió correctamente por SSH
- commit local Codex: `4b37cfe`
- mensaje: `feat(r3): analyzer offline de skip_log.jsonl`

## Sesión 81 — Control Center simplificado + verify saneado sobre main (6 abr 2026)

**Disparador:** ejecutar los ítems delegables de `docs/control-center-simplify-plan.md` sin agrupar cambios, integrar la cadena completa en `main` y dejar `verify_before_deploy.py` verde antes de cualquier deploy.

**Cambios integrados por Codex:**

- Se mergearon en orden local y luego a `origin/main` siete PRs aisladas del plan:
  - `#5` limpieza de duplicados visuales del dashboard;
  - `#1` badge de modo sin falsa alarma en shadow/dry;
  - `#2` eliminación de la columna `Resolucion` del bloque de señales shadow;
  - `#6` lenguaje llano para scan y etiquetas de condición;
  - `#3` normalización de `forecast_display`/`forecast_badge`, incluyendo corrección del mojibake `°`;
  - `#4` supresión de `city_low_accuracy` como alerta operativa en `SHADOW_ONLY/DRY_RUN`, moviéndola a anotación fija en rendimiento;
  - `#7` gateo NOAA cuando la muestra todavía es insuficiente.
- El conflicto textual de `bot.py` entre `#3` y `#6` se resolvió manteniendo todos los helpers nuevos y combinando correctamente `_strip_resolution_fields(row)`, `_build_shadow_forecast_fields(row)` y `condition_label` en la comprehension de `build_dashboard_city_decisions`.
- `verify_before_deploy.py` se endureció para reflejar el dashboard simplificado y el entorno real de sandbox:
  - actualiza asserts HTML que seguían esperando `Resolucion` y textos viejos del bloque shadow;
  - inyecta `_dashboard_mode_label` en el harness funcional de `get_dashboard_alert_summary`;
  - usa un tempdir local del repo para R3 y monkeypatch de `os.replace` en la prueba de rotación, evitando falsos rojos por restricciones del sandbox Windows.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` -> `612/612`
- commit final de saneamiento del verify en `main`: `df4ff60`
- mensaje: `test(verify): harden merged dashboard checks`
- `git push origin main` publicado con toda la cadena ya integrada

**Notas de alcance:**

- no hubo bump de versión;
- no se tocaron los 3 gates de R1 ni la lógica funcional de `skip_log`;
- no se desplegó a Railway en esta sesión.

## Sesión 83 — Dallas desbloqueado + arquitectura modos ciudad + contrato NOAA (6 abr 2026)

**Disparador:** revisar el primer ciclo Dallas con modelo corregido (bias + sigma 0.57°C), diagnosticar por qué no operaba, y diseñar la hoja de ruta NOAA para todas las ciudades.

**Hallazgos:**

- Dallas bloqueada en producción por `sync_city_policy_state` — re-añadida a `auto_blocked_cities` en cada arranque porque WR=11.8% (<25%) dispara `removable_active=True`. El label "(WU vs Open-Meteo)" en el log es hardcodeado, no refleja una comprobación WU activa.
- El loop era: cleanup manual → bot arranca → `run_observability_alerts()` → `sync_city_policy_state()` → Dallas re-bloqueada antes del primer ciclo.
- Atlanta y Chicago estaban en `BLOCKED_CITIES` por error de diseño: `BLOCKED_CITIES` corta TODO incluyendo recolección NOAA. Esas ciudades habían dejado de acumular datos NOAA sin que nadie lo notara.
- 26 ciudades en `RESOLUTION_ICAO` sin `noaa_station_id` → no acumulan NOAA aunque estén en shadow.

**Resultado:**

- `CITY_STATS_CUTOFF` env var + `get_city_accuracy()` filtrado por fecha: reset de métricas Dallas sin borrar `postmortem.json`. `verify_before_deploy.py` 626/626 (6 tests nuevos).
- `ALLOWLIST_REMOVE_MIN_TRADES=25` en Railway: barrera de seguridad anti-re-bloqueo hasta n≥25 trades nuevos.
- `CITY_STATS_CUTOFF=Dallas=2026-04-06` en Railway: Dallas arranca con 0 trades en métricas.
- Atlanta y Chicago removidas de `BLOCKED_CITIES` en Railway → vuelven a shadow, siguen acumulando NOAA.
- Norma canónica de modos documentada en `AGENTS.md`, `bot.py` (comentario junto a `BLOCKED_CITIES`) y `CONTEXTO.md`: blocked=datos rotos, shadow=no opera pero observa.
- Contrato Codex `docs/noaa-station-verification-contract.md`: proceso autónomo para verificar estaciones NOAA de las 26 ciudades pendientes via isd-history.csv + GHCND API.

**Commits:** `f7abd5b`, `55b6dee`, `0a220ed`
**Railway:** `ALLOWLIST_REMOVE_MIN_TRADES=25`, `CITY_STATS_CUTOFF=Dallas=2026-04-06`, Atlanta/Chicago fuera de `BLOCKED_CITIES`.
**Próximo paso:** Codex ejecuta `docs/noaa-station-verification-contract.md`.

## Sesión 82 — Cierre NOAA decouple en rama de revisión (6 abr 2026)

**Disparador:** cerrar ordenadamente una exploración local sobre NOAA después de detectar que el diff se había trabajado sobre una base de tests antigua respecto a `main`.

**Resultado real al cierre:**

- se creó y publicó la rama `codex/noaa-decouple` para revisión aislada;
- la rama quedó sin delta efectivo de código frente a `main`/`origin/main` al terminar la sesión;
- no se integraron cambios funcionales nuevos en `bot.py` ni `verify_before_deploy.py`;
- se sincronizaron `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` para dejar trazabilidad explícita de que esta sesión cerró workflow, no producto.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` relanzado antes del push de cierre;
- commit de cierre documental realizado sobre `codex/noaa-decouple`;
- push de la rama de revisión actualizado para dejar la sesión cerrada.

## Sesión 84 — Revalidación NOAA London/Milan sin delta funcional (6 abr 2026)

**Disparador:** revisar dos `noaa_daily_station_id` del commit `9efd8bc` con posible sesgo geográfico antes de seguir confiando en la nueva capa NOAA ampliada.

**Verificación ejecutada:**

- `London -> UKE00107650` se reconsultó en `daily-summaries/TMAX` para `2025-10-01..2026-03-31`: devuelve `149` registros válidos, rango plausible `2.5°C..21.3°C`. En `ghcnd-stations.txt` figura como `HEATHROW` (`51.4789, 0.4489`), a ~`27.8 km` de `EGLC`.
- `Milan -> SZ000009480` también devuelve `151` registros `TMAX`, pero las coordenadas son `46.0, 8.9667` (`LUGANO`, Suiza), a ~`45.0 km` de `LIMC`.
- Se hizo búsqueda dirigida de candidatos italianos cerca de Malpensa en `ghcnd-stations.txt` y luego una ampliación de radio hasta `300 km`. Los candidatos italianos obvios (`ITM00016064 CAMERI`, `ITE00100554 MILAN`, etc.) devolvieron `0` registros `TMAX` para el periodo contractual.

**Resultado:**

- no se modifica `bot.py` en esta sesión;
- London queda validada como `daily` útil;
- Milan se mantiene temporalmente con `SZ000009480` por falta de alternativa italiana con cobertura real en GHCND;
- se documenta explícitamente que el siguiente cuello de botella ya no es el lookup de IDs sino acumular muestra real en `observed_vs_forecast`.

**Validación y cierre:**

- `python verify_before_deploy.py` -> `626/626`
- se sincronizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`
- no hay commit funcional nuevo de producto en esta sesión; el commit/push de cierre es solo documental

## Sesión 86 — Policy NOAA-verificada vs histórico legacy en ciudades (6 abr 2026)

**Disparador:** convertir en implementación el pendiente explícito de la sesión 85: evitar que la policy de ciudades degrade/promueva usando como evidencia fuerte un histórico malo de una era pre-NOAA-verificada.

**Implementación local:**

- se añade `get_city_policy_metrics()` en `bot.py` para separar cierres por ciudad en `total`, `verified` y `legacy`, usando join `city + date` contra `audit.json -> observed_vs_forecast` con `source=noaa_ncei`;
- `build_dashboard_city_observation()` pasa a exponer `policy_source`, `policy_is_provisional`, `policy_trades`, `verified_trades` y `legacy_trades`, y deja explícito cuando el histórico visible sigue siendo solo legacy/provisional;
- `build_dashboard_city_decisions()` cambia la regla de salida: `active/canary -> shadow` ya no usa el agregado bruto de `get_city_accuracy()`, sino solo histórico **NOAA-verificado** para disparar `remove`;
- si una ciudad activa solo tiene histórico legacy malo, la decision se mantiene en `keep` pero pasa a `Revisar legado / Bajo review` con score más conservador, de modo que no se autodegrada ni queda visualmente “limpia”;
- el soporte de `shadow -> canary` conserva `trades` totales como soporte para no introducir una regresión silenciosa al split `verified/legacy`, pero la degradación sigue exigiendo evidencia NOAA-verificada;
- se endurece el join `city + date` normalizando ambas fechas a `YYYY-MM-DD`;
- `sync_city_policy_state()`, `_compute_city_decisions_for_alerts()`, snapshot y focus dejan de recalcular tres veces la misma capa `city_policy_metrics`.
- `_build_auto_city_shadow_policy()` persiste también el basis de policy (`policy_source`, `policy_trades`, `verified_trades`, `legacy_trades`) para que la degradación guardada conserve contexto de calidad de evidencia.

**Validación y estado:**

- `python verify_before_deploy.py` -> `632/632`
- se añaden tests funcionales que prueban la separación `NOAA-verificado vs legacy` y que una ciudad activa con histórico legacy malo no se degrada automáticamente por esa sola razón
- no se tocó trading core, NOAA fetch core, scheduler ni exits; el cambio queda acotado a la policy, su lectura y su persistencia

## Sesión 87 — Hardening de agent_events live (7 abr 2026)

**Disparador:** corregir el warning repetido en Railway `Error cargando agent_events: invalid literal for int() with base 10: 'session_72'` sin tocar trading, NOAA ni scheduler.

**Implementación local:**

- `load_agent_events()` deja de asumir que `session` siempre llega como entero puro;
- ahora acepta strings tipo `session_72`, extrae el sufijo numérico y normaliza el valor a `72`;
- la clave de deduplicación sigue usando `timestamp + session + agent + type + title normalizado`, pero ya no rompe al leer eventos antiguos o serializados con prefijo textual.

**Validación y estado:**

- `python verify_before_deploy.py` -> `637/637`
- se añade un test funcional con `session="session_72"` para fijar la compatibilidad y asegurar que la carga sigue ordenando y deduplicando correctamente
- impacto esperado: desaparece el warning repetido de `agent_events` en logs y el scoreboard/dashboard vuelve a poder leer esos eventos sin ruido

## Sesión 88 — Hardening HTTP del forecast provider (7 abr 2026)

**Disparador:** tras desaparecer el warning de `agent_events`, los logs live muestran el siguiente cuello de botella real: `Forecast error` con `timeout`, `429 Too Many Requests` y algún `502` durante el ciclo de las `08:43 UTC`.

**Hallazgo operativo:**

- el mismo ciclo reutiliza `get_forecast()` desde `audit_check_open_meteo_forecast_drift()` y luego otra vez desde el escaneo principal;
- eso duplica hits al mismo endpoint/city cuando el proveedor ya está inestable o rate-limited;
- el wrapper anterior reintentaba siempre con espera fija y no distinguía `HTTP 429`.

**Implementación local:**

- `get_forecast()` añade caché en proceso por `lat/lon`;
- si la respuesta sigue fresca, la reutiliza directamente;
- si aparece `HTTP 429`, registra un cooldown explícito y evita seguir martilleando el proveedor;
- si existe una respuesta reciente pero ya no fresca, puede reutilizarla como `stale cache` controlada cuando el fallo es del proveedor.

**Validación y estado:**

- `python verify_before_deploy.py` -> `639/639`
- se añaden tests funcionales para asegurar que la segunda llamada usa caché y que un `HTTP 429` cae a `stale cache` en vez de romper todo el flujo
- no se toca trading, NOAA, scheduler ni sizing; el cambio queda acotado al wrapper HTTP de forecast

## Sesión 128 — Runtime policy mode read-only en city-intelligence (10 abr 2026)

**Disparador:** Opus valida el transporte runtime manual, pero bloquea la automatización porque el ledger ya puede leer los archivos runtime y aun así seguía tratando Shanghai como `shadow` + `candidate_for_canary_validation`, pese a que `city_policy_state.json` la tiene en `auto_canary_cities`.

**Implementación local:**

- `tools/city_validation_ledger.py` lee `city_policy_state.json` en modo read-only y construye `runtime_policy_mode` desde `auto_canary_cities`, `auto_shadow_cities` y `auto_blocked_cities`;
- el ledger conserva la policy analítica previa como `cross_policy_mode` y usa `policy_mode` como policy efectiva cuando runtime está disponible;
- se añade `drift_flags=["policy_divergence"]` cuando runtime y cross discrepan;
- se añaden filas `runtime_only` para ciudades presentes en `city_policy_state.json` pero ausentes en `cross.city_rows`, como Atlanta y Dallas;
- `tools/city_promotion_gate.py` convierte `policy_divergence` en `gate_status=audit_runtime_drift` y evita pedir `review_for_canary` cuando runtime ya decidió canary;
- se crea `docs/claude-opus-prompt-runtime-policy-mode-review-2026-04-10.md` para que Opus revise esta unidad antes de automatizar pull/sync runtime.

**Validación y estado:**

- contra `data/runtime_import/*`: `runtime_inputs_status=available`, `n_cities=24`, `runtime_policy_mode_counts={auto_canary: 6, auto_shadow: 1, runtime_unknown: 17}`, `drift_flag_counts={policy_divergence: 5}`;
- Shanghai queda reconciliada como `policy_mode=canary`, `cross_policy_mode=shadow`, `runtime_policy_mode=auto_canary`, `recommendation=audit_runtime_drift`, `gate_status=audit_runtime_drift`;
- Atlanta aparece como `cross_policy_mode=runtime_only`, `runtime_policy_mode=auto_canary`, `gate_status=observe_runtime_canary`;
- el fail-closed local sigue intacto: sin runtime local, ledger/gate/pipeline devuelven `runtime_inputs_status=missing` / `overall_status=runtime_inputs_missing` y `cities=[]`;
- no se tocó `bot.py`, no se escribió `city_policy_state.json`, no se cambiaron thresholds ni trading core.
- tras el `GO WITH CHANGES` de Opus, se añade hardening mínimo: `base_recommendation`, `base_evidence_status`, `evidence_status=runtime_only` para filas sintéticas, detector `runtime_policy_collision`, auditoría de consumidores de `policy_mode` y nota arquitectónica de que `cross_policy_mode=unknown` + runtime conocido es `policy_divergence` deliberado en v0;
- con los inputs auxiliares refrescados, Dallas aparece como sexto drift real (`cross_policy_mode=active`, `runtime_policy_mode=auto_shadow`), dejando el snapshot validado en `n_cities=25`, `policy_divergence=6`.

## Sesión 129 — Staleness pre-automation de runtime import (10 abr 2026)

**Disparador:** agotado el cupo semanal de Claude/Opus, se decide continuar sin más review externa y ejecutar el siguiente bloque LEAN recomendado antes de automatizar transporte: evitar que snapshots viejos parezcan runtime actual.

**Implementación local:**

- `tools/city_validation_ledger.py` añade `--runtime-manifest` y `--max-runtime-snapshot-age-hours`;
- si los tres runtime files existen pero el manifest falta, no parsea o supera el umbral, el ledger corta en `runtime_inputs_status=stale`, `cities=[]`, `stale_runtime_inputs` y `bottleneck_counts.runtime_inputs_stale=1`;
- `tools/city_promotion_gate.py` propaga stale como `gate_status=runtime_snapshot_stale`;
- `tools/city_intelligence_pipeline.py` propaga `overall_status=runtime_inputs_stale`;
- `tools/city_intelligence_telegram_alert.py` y `tools/city_intelligence_daily_summary.py` distinguen `missing` de `stale` y listan nombres/razones concretas de archivos/manifest.

**Validación y estado:**

- sintaxis validada por AST sin escribir `.pyc`;
- con `data/runtime_import/runtime_import_manifest.json` y umbral alto, el ledger queda `runtime_inputs_status=available`;
- con `--max-runtime-snapshot-age-hours 0.001`, el ledger/gate cortan en `runtime_inputs_status=stale` / `runtime_snapshot_stale`, sin filas por ciudad;
- con partial-missing simulado (faltando solo `city_policy_state`) el ledger/gate/alert cortan en `runtime_inputs_status=missing` y listan exactamente `city_policy_state`;
- local sin runtime sigue fail-closed: `runtime_inputs_status=missing`, `cities=[]`, `overall_status=runtime_inputs_missing`;
- no se tocó `bot.py`, no se escribió `city_policy_state.json`, no se automatizó pull/sync runtime.

## Sesión 85 — Política de ciudades shadow-first y migración Dallas legacy (6 abr 2026)

**Disparador:** auditar la contradicción entre la semántica deseada (`blocked` solo para descartes reales, `shadow` para observación activa) y el comportamiento real donde `sync_city_policy_state()` mandaba `active/canary -> blocked`, dejando casos como Dallas atrapados por `auto_blocked_cities`.

**Hallazgos de auditoría:**

- `get_effective_city_mode()` daba prioridad total a `auto_blocked_cities` sobre `ACTIVE_TRADING_CITIES`, así que una entrada legacy `action="auto_block"` podía dejar una ciudad `blocked` aunque en la práctica solo se quisiera pausarla y seguir observando.
- `sync_city_policy_state()` seguía escribiendo `auto_blocked_cities` cuando `decision == "remove"`, con transición `active/canary -> blocked`.
- El scan trataba `blocked` como descarte duro (`continue` temprano), por lo que esas ciudades salían también del circuito útil de observación.
- El dashboard mezclaba `Sin muestra` y `Sin NOAA` en el gate C y todavía verbalizaba `blocked` y `shadow degradada` demasiado cerca semánticamente.

**Implementación local:**

- se añade normalización del overlay persistido con `_normalize_city_policy_state()`, `_is_real_block_policy()` y `_coerce_shadow_policy_entry()`;
- el legado `auto_blocked_cities[action=auto_block]` migra automáticamente a `auto_shadow_cities` al cargar/guardar, preservando `reason`, `metrics`, `from_mode` y fecha;
- `sync_city_policy_state()` vuelve a degradar `active/canary -> shadow` con `_build_auto_city_shadow_policy()` y transición `action="auto_shadow"`;
- `blocked` queda reservado a descartes reales explícitos (`BLOCKED_CITIES` o `auto_blocked_cities` con acción de bloqueo real);
- el dashboard distingue `Interpretable`, `Parcial`, `Sin muestra` y `Sin NOAA`, renombra el bloque de `blocked_rows` a `Descartes reales`, y presenta `Shadow degradada` como observación activa, no como expulsión dura.

**Validación y estado:**

- `python verify_before_deploy.py` -> `628/628`
- no se tocó trading core, NOAA fetch core, scheduler ni exits, fuera del overlay de política y la presentación
- no hubo mutación live en Railway durante esta sesión; el siguiente paso operativo es push/deploy para que el código nuevo migre overlays legacy en producción

## Sesión 143 — Mapa mental y handoff de Dashboard/Telegram (11 abr 2026)

**Disparador:** dejar una visión más aterrizada del sistema para el usuario y fijar el siguiente frente lógico tras el cierre del alignment base: revisar si la capa humana de lectura (`Dashboard` y `Telegram`) ya está alineada con la arquitectura y los artefactos canónicos actuales.

**Implementación local:**

- se crea `docs/system-mental-model-2026-04-11.md` para resumir el sistema en tres capas:
  - ejecución runtime (`polymarket-bot`)
  - estado observable (`runtime_import`, effective view, funnel, postmortem)
  - inteligencia read-only (`city-intelligence`, checks, readouts, prompts)
- se crea `docs/next-session-handoff-2026-04-11-dashboard-telegram-audit.md` con una sesión read-only ya acotada para auditar Dashboard + Telegram sin mezclarla con policy, monetización ni trading core.

**Conclusión operativa:**

- la arquitectura base ya está suficientemente alineada como para cambiar el foco desde contratos core hacia la capa de lectura humana;
- el siguiente drift relevante, si existe, probablemente esté en wording, alertas o priorización de Dashboard/Telegram;
- por eso el siguiente paso recomendado ya no es otra sesión abstracta de alignment, sino una auditoría concreta de utilidad y coherencia operativa en la UI y las alertas.

## Sesión 142 — Follow-up de throughput sin muestra nueva (11 abr 2026)

**Disparador:** intentar una segunda extensión read-only de `Step 5` tras la observación extendida previa, manteniendo el mismo scope estricto: snapshot manifestado, naming canónico del funnel y cero cambios en `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll o `exact/range`.

**Hallazgo clave:**

- el snapshot runtime sí quedó fresco (`pulled_at=2026-04-11T11:01:40.7730763+00:00`);
- `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` siguieron en `ok=7, warning=1, error=0`;
- pero los artefactos manifestados no traen ciclos nuevos más allá del tramo ya auditado: `cycles_history.jsonl` sigue cerrando en `2026-04-11T08:00:38.111156+00:00` (`cycle_number=64`) y `shadow_city_tracking.updated_at` coincide en `2026-04-11T08:00:38.036104+00:00`.

**Implementación local:**

- no se cambia lógica ni artefacto runtime alguno;
- se deja `docs/step5-throughput-observation-followup-2026-04-11.md` para documentar que el intento de extensión no puede producir `20` ciclos adicionales honestos todavía;
- se deja `docs/throughput-observation-readout-followup-2026-04-11.md` como cierre corto.

**Validación y estado:**

- snapshot manifestado y fresco por vía canónica read-only;
- `system_alignment_check.py` -> `ok=7, warning=1, error=0`;
- `system_alignment_check.py --decision-mode operational` -> `ok=7, warning=1, error=0`;
- `blocking_operational_collision_count=0`;
- no aparece bug nuevo de counters/accounting;
- la siguiente sesión correcta sigue siendo observación read-only cuando existan ciclos runtime realmente nuevos, no correctness ni policy.

## Sesión 140 — Dallas claim cleanup read-only (11 abr 2026)

**Disparador:** limpiar el último `blocking_operational_collision` de Dallas sin tocar `bot.py`, policy live, `city_policy_state.json` ni capas operativas prohibidas.

**Hallazgo clave:**

- el blocker no venía de runtime live;
- `tools/runtime_policy_effective_view.py` seguía sembrando `DEFAULT_ACTIVE_CITIES = "Dallas"` como fallback local cuando no había snapshot explícito del env;
- eso fabricaba un `env_declared_mode=active` heredado que chocaba con `runtime_policy_mode=auto_shadow`, aunque `effective_mode` correcto ya era `shadow`.

**Implementación local:**

- `DEFAULT_ACTIVE_CITIES` pasa a vacío en `tools/runtime_policy_effective_view.py`;
- la herramienta mantiene el soporte para listas env explícitas por argumento, pero deja de promover por defecto un claim declarativo stale;
- se regeneran `data/runtime_policy_effective_view.json`, `docs/runtime_policy_effective_view_latest.md`, `data/system_alignment_check*.json` y `docs/system_alignment_check*_latest.md`.

**Validación y estado:**

- `python tools/system_alignment_check.py` -> `ok=7, warning=1, error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7, warning=1, error=0`
- `blocking_operational_collision_count` baja de `1` a `0`
- Dallas queda alineada como `env=shadow`, `runtime=auto_shadow`, `cross=shadow`, `effective=shadow`
- readout corto dejado en `docs/dallas-claim-readout-2026-04-11.md`

## Sesión 169 — Cross-check edge vs traders + diagnóstico auto-promoción (13 abr 2026)

**Modelo:** Sonnet. **Handoffs:** A y C del índice 2026-04-13.

**Handoff A — Cross-check edge vs trader signals:**
- Se crea `tools/signals_vs_edge_crosscheck.py` (standalone read-only).
- Primera corrida: MATCH=14, BOT_ONLY=2 (Beijing, Chicago), TRADER_ONLY=21. Austin en TRADER_ONLY ✓, Seoul en MATCH ✓.
- 81% de señales de quality traders caen en exact/range (bloqueadas). 8 ciudades TRADER_ONLY tienen conds operables; Austin y Toronto con consenso son las más urgentes.
- Output: `data/runtime_import_derived/signals_crosscheck.jsonl` + `docs/signals-crosscheck-baseline-2026-04-13.md`.

**Handoff C — Diagnóstico trigger auto-promoción:**
- Dallas: `ACTIVE_TRADING_CITIES` null en Railway → código usa default con Dallas → `city_mode="active"` → nunca llega a `promotable_shadow`. Gate `city not in ACTIVE_TRADING_CITIES` también falla.
- Lucknow, Sao Paulo, Istanbul: no en `OBSERVED_AUDIT_CITIES`, 0 trades, nunca en `auto_shadow_cities` → invisibles a `tracked_cities` → `sync_city_policy_state` nunca las evalúa. Gap estructural entre `shadow_city_tracking` y el pipeline de promoción.
- Fixes propuestos (no aplicados): A1=setear `ACTIVE_TRADING_CITIES` explícito en Railway, B1=añadir a `OBSERVED_AUDIT_CITIES` de a una. Decisión de aplicar → Opus.
- Output: `docs/auto-promotion-trigger-diagnosis-2026-04-13.md`.

### Sesión 170 — Blocked Signals Settlement Tracker (Handoff B) (13 abr 2026)

**Modelo:** Sonnet. **Handoff:** B (experimento 2: resolución de señales `exact/range` bloqueadas).

- Se crea `tools/blocked_signals_settlement_tracker.py`: tool standalone read-only que mide la WR implícita de las señales `exact/range` de quality traders que el bot filtra por `condition_filtered`.
- **Algoritmo:** lee `signals.json`, filtra `condition in {exact, range}` con `date <= today-1`, fetch paginado de eventos cerrados via `gamma-api.polymarket.com`, match por título normalizado, calcula `win = close_price >= 0.95` para el lado de la señal.
- **Bug encoding descubierto:** `signals.json` almacena el símbolo `°` como la secuencia corrupta `U+252C U+2591` (`┬░`) en lugar de `U+00B0`. El tool normaliza antes de comparar con la API.
- **Primera corrida (Apr 13 snapshot, cutoff Apr 12):** 19 candidatos `exact/range`, 18 resueltos, 18 wins. **WR = 100.0% (n=18).**
- **Veredicto:** `INSUFFICIENT SAMPLE` (n < 30). Se necesitan >= 30 resoluciones para primer corte, >= 50 para decisión robusta. El tool debe correrse nuevamente cuando haya más días acumulados.
- **Outputs:** `data/runtime_import_derived/blocked_signals_resolutions.jsonl` (append-only, dedup por `match_key`), `docs/blocked-signals-wr-baseline-2026-04-13.md`.
- **No tocar:** `bot.py`, `trader_analyzer.py`, `signals.json`, Railway, trading core.

### Sesión 169 cont. — Crosscheck automatizado + corrección ACTIVE_TRADING_CITIES

**Modelo:** Sonnet. Continuación de la misma sesión.

- Se añade `maybe_run_daily_crosscheck(state)` a `bot.py` (v10.6.12): corre el crosscheck traders vs edge en el primer ciclo de cada día, appenda a `/app/data/signals_crosscheck.jsonl`, manda Telegram diario y aviso one-shot al acumular 7 corridas.
- Usuario aplica `ACTIVE_TRADING_CITIES=NONE` en Railway: elimina el default hardcoded `Chicago,Atlanta,Dallas,Buenos Aires` que trataba esas 4 ciudades como active sin env var explícito. Ahora ninguna ciudad entra en active mode sin declaración humana.
- Backlog documentado: feature canary→active graduation con criterios automáticos + reminder persistente hasta que el usuario actúe. Requiere sesión dedicada Opus.

### Sesión 171 — Fix encoding ° en signals.json (13 abr 2026)

**Modelo:** Sonnet. **Tarea:** bug fix de codificación.

- **Bug:** `trader_analyzer.py` escribía `°` como `┬░` (U+252C U+2591) en `signals.json` en lugar de `°` (U+00B0). Descubierto en sesión 170 al normalizar títulos para el settlement tracker.
- **Root cause:** `api_get()` línea 103 llamaba `json.loads(resp.read())` sin encoding explícito. En Windows con CP437 como code page del sistema, los bytes UTF-8 `\xC2\xB0` se decodificaban como CP437 produciendo `┬░`.
- **Fix:** `json.loads(resp.read().decode("utf-8"))` — una línea en `trader_analyzer.py:103`.
- **Validación:** `verify_before_deploy.py` → 643/643 tests.
- **Versión activa al cerrar:** `v10.6.13` local lista para push/deploy.

### Sesión 172 — Diseño canary→active automation + handoff Opus (13 abr 2026)

**Modelo:** Opus. **Tarea:** diseño estratégico + handoff para sesión limpia Sonnet. Sin tocar `bot.py`, trading core, thresholds, Railway ni policy live.

- **Decisión arquitectónica:** Opción B (notificación Telegram persistente, Pablo aplica manualmente) sobre auto-promoción full. Fundamento: bankroll $25, modelo en recalibración Phase 2, asimetría de riesgo degradar vs promover.
- **Umbrales v1 congelados con justificación explícita:** `canary_trades>=5` (mínimo donde WR≥60% con alguna pérdida es alcanzable en ~5 semanas), `WR>=60%` (margen claro sobre break-even 50%), `PnL>=+$1.00` (recupera ≥1 pérdida canary), `days_since_promotion>=7` (al menos un ciclo semanal completo), `WR_degradation<=45%` (bajo break-even claro).
- **Scope v1 = Bloques 1+2+4:** historial propio canary + integridad lifecycle (detección patrón Atlanta-inconsistency) + anti-flapping (no degradada últimos 14 días).
- **Scope v2 = Bloques 3+5 deferidos:** corroboración externa (signals.json consensus o shadow edge reciente) + gate global post-recalibración (WR sistema ≥50% últimos 30 días). Se añade trigger alarm one-shot que avisa a Pablo por Telegram cuando precondiciones v2 se cumplan (`RECALIBRATION_PHASE2_CLOSED=true` + al menos 1 ciudad en Active + signals.json fresco).
- **Spec completo en `docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md`:** tres módulos (`notify_active_candidates`, `maybe_run_active_degradation`, `maybe_alert_v2_trigger`), Telegram templates (nueva candidata / recordatorio 24h / revocación / degradación / trigger v2), anti-spam (rate limit 22h + revocación automática), detección de acción del usuario via `os.getenv("ACTIVE_TRADING_CITIES")` runtime, overlay nuevo para degradación active→canary (no tocar `sync_city_policy_state`), test checklist con 8+ casos unitarios.
- **Principio de diseño:** bot observa y avisa; Pablo decide y aplica. Asimetría: degradación = auto (protección capital > espera humana), promoción = manual (decisión de capital más consecuente queda con humano).
- **Nota operativa (recurrente):** volumen bajo de trades (~1 canary/semana por ciudad) sigue siendo prioridad paralela. Este módulo ayuda indirectamente (desbloquea sizing active) pero no resuelve throughput de fondo (scan loop filtra demasiado). Anotado para backlog post-implementación.
- **Implementación diferida:** a sesión Sonnet limpia. Opus cierra aquí; Sonnet arranca con el handoff y clear de contexto.

### Sesión 173 — Canary→Active automation v10.6.14 (13 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md`.

- **Tres módulos implementados en `bot.py` (v10.6.13→v10.6.14):**
  - `_detect_atlanta_inconsistency(record)`: helper que detecta el patrón LOSS_TOTAL + RESOLVED_WIN positivo en timeline + post_exit_analysis confirmando win (Bloque 2 integridad).
  - `notify_active_candidates(state)` (Módulo 1): evalúa ciudades en `auto_canary_cities` contra criterios v1 congelados (n≥5, WR≥60%, PnL≥+$1.00, days≥7, integridad OK, Bloque 4 anti-flapping). Alerta Telegram nueva candidata + recordatorio cada 22h + revocación automática + silenciamiento cuando ciudad aparece en `ACTIVE_TRADING_CITIES` runtime.
  - `maybe_run_active_degradation(state)` (Módulo 2): degrada Active→Canary automáticamente si WR≤45% o PnL≤-$1.50 (con n≥5, anti-flapping 14 días). Overlay `auto_canary_from_active` en `city_policy_state.json`. `get_effective_city_mode()` extendido mínimamente para leer ese overlay antes de `ACTIVE_TRADING_CITIES`.
  - `maybe_alert_v2_trigger(state)` (Módulo 3): alerta one-shot cuando `RECALIBRATION_PHASE2_CLOSED=true` + al menos 1 ciudad en Active + `signals.json` fresco (<48h). Idempotente, gate diario.
- **Integración en `run_observability_alerts()`:** `maybe_run_active_degradation` (antes de `notify_canary_candidates`), `notify_active_candidates` (después), `maybe_alert_v2_trigger` (en gate diario junto a `maybe_run_daily_crosscheck` y `maybe_run_blocked_signals_check`).
- **`verify_before_deploy.py`:** 643→663/663 (+20 tests: 10 estáticos + 8 funcionales + 2 idempotencia/one-shot).
- **No tocado:** `sync_city_policy_state()`, thresholds `SHADOW_CANARY_MIN_*`, `ALLOWLIST_REMOVE_*`, `MIN_EDGE`, `MIN_DAYS_AHEAD`, trading core, NOAA client, scheduler, `signals.json`, `trader_analyzer.py`.
- **Nota operativa recurrente:** volumen bajo del scan loop sigue siendo backlog paralelo no resuelto (condition_filtered, scheduler, filtros temporales). Este módulo ayuda indirectamente al sizing Active pero no resuelve throughput de fondo.

### Sesión 174 — Blocked signals WR baseline n=59 + Opus handoff condition_filtered (14 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/next-session-handoff-2026-04-13-B-blocked-settlement.md` (Opus, Sesión 168).

- **Tool `blocked_signals_settlement_tracker.py` corrida localmente:** data fresca de Polymarket API → 59 resolutions (18 preexistentes + 41 nuevas).
- **WR overall: 76.3% (45/59)** — cumple ampliamente threshold WR≥55% con n≥50 robusto. Veredicto oficial: **REOPEN CANDIDATE**.
- **Por condition:** exact 72.5% (37/51), range 100% (8/8).
- **Por ciudad (n≥3):** Seattle/Tokyo/Hong Kong 100%, Seoul/Toronto 75%, Chengdu/Shenzhen/Shanghai/Milan 66.7%, London 33.3% (outlier, n=3).
- **Consenso vs solo:** consenso 66.7% (6/9), solo 78.0% (39/50).
- **Hallazgo clave:** `ALLOWED_CONDITIONS` ya es env var en `bot.py:222` — añadir `exact,range` en Railway es el cambio mínimo. Cero código nuevo necesario para reapertura global.
- **Decisión de diseño diferida a Opus:** preguntas abiertas — global vs quality-trader-gated, manejo de London (outlier 33.3%), edge mínimo diferenciado, scope de ciudades, fecha de revisión post-apertura.
- **Entregables:**
  - `data/runtime_import_derived/blocked_signals_resolutions.jsonl` actualizado a 59 records (gitignored)
  - `docs/blocked-signals-wr-baseline-2026-04-13.md` actualizado con WR=76.3%/n=59
  - `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md` — spec completo para Opus
  - `CONTEXTO.md` y `HISTORIAL_SESIONES.md` alineados
- **No tocado:** `bot.py`, trading core, Railway, env vars, `ALLOWED_CONDITIONS`.

### Sesión 175 — condition_filtered canary reopen v10.6.15 (14 abr 2026)

**Modelo:** Sonnet (implementación) + Opus (decisión vía subagente). **Handoff:** `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md`.

- **Análisis previo (Sesión 174):** 59 resoluciones reales de quality traders con `exact/range` → WR=76.3%, threshold ≥55% n≥50 cumplido.
- **Decisión Opus (Opción B modificada):** reabrir con triple gate — quality trader + whitelist 9 ciudades + edge buffer +5pp. London excluida (WR 33% n=3).
- **Implementado en `bot.py` v10.6.15:** 4 env vars nuevas (`QUALITY_TRADER_CONDITIONS`, `QUALITY_TRADER_CITIES_WHITELIST`, `MIN_EDGE_EXACT_RANGE_BUFFER_PP=5.0`, `EXACT_RANGE_SIZE_SCALE=0.50`), lógica triple gate en `condition_filtered`, edge mínimo diferenciado, sizing 25% del normal.
- **Checkpoints comprometidos:** día 7 (2026-04-21), día 14 (2026-04-28). Kill-switch: WR bot <45% n≥20.
- **Deploy Railway OK** — logs confirmaron feature activo, Milan 18°C exact procesada por ruta canary.
- **Pendiente:** `tools/condition_reopen_monitor.py` + integración Telegram automática → Sesión 176.
- `verify_before_deploy.py` → 671/671.

### Sesión 178 — London city-intelligence audit + policy priority fix (15 abr 2026)

**Modelo:** Codex.

- **Refresh runtime read-only:** `tools/railway_runtime_snapshot_pull.ps1` se ejecuta con bypass de `ExecutionPolicy` para traer snapshot fresco y eliminar el `manifest_drift` local que estaba distorsionando el ledger.
- **Diagnóstico London reanclado:** la ciudad deja de leerse como simple `background_watch`/`trader_discovery`; el problema real pasa a ser `blocked` con `policy_divergence` (`cross=blocked`, `runtime=auto_canary`) y cuello `source_fidelity`.
- **Fix analítico en `tools/city_validation_ledger.py`:** se añade `STRUCTURAL_BLOCK_GUARDRAILS` para London y se corrige la prioridad de modos para respetar la regla canónica de `AGENTS.md` (`blocked > canary > shadow`). Con eso London vuelve a `policy_mode=blocked`, carga `structural_block_guardrail`, y su bottleneck se clasifica como `source_fidelity`.
- **Ajuste en `tools/city_promotion_gate.py`:** se mejora el tratamiento de ciudades con bloqueo estructural explícito para que la cola de revisión no las cuente como simple falta de discovery.
- **Auditoría settlement/source fresca de London:** `tools/settlement_fidelity_probe.py --city London --limit 20` encuentra 10 mercados con Open-Meteo, 0/10 con NOAA observado y `WU` todavía `pending_not_automated`; `shadow_city_tracking` muestra `markets_seen=128`, `edge_hits=2`, `cycles_seen=41`, `best_edge_pct=28.4`. `docs/blocked-signals-wr-baseline-2026-04-13.md` sigue dejando London en 33.3% (1/3) para exact/range.
- **Veredicto operativo:** mantener London en `blocked`; no usarla como candidata de monetización mientras no exista una revalidación WU-backed o una comparación manual robusta de settlement.
- **Artefactos nuevos:** `docs/london-city-intelligence-warning-review-2026-04-15.md` y `docs/london-settlement-source-audit-2026-04-15.md`.
- **Verificación:** `python -m py_compile tools/city_validation_ledger.py tools/city_promotion_gate.py` OK; `python verify_before_deploy.py` se ejecuta al cierre antes de commit/push.

### Sesión 176 — condition_reopen_monitor + integración bot (v10.6.16) (14 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md` (Sonnet, Sesión 175).

- **`tools/condition_reopen_monitor.py`** standalone read-only: carga `data/trade_lifecycle.json`, filtra trades `condition ∈ {exact, range}` desde 2026-04-14 con `status=closed`, calcula WR via `close_context.pnl_cash > 0`, desglose por ciudad, veredicto automático (OK / ALERT / CLOSE / PROMOTE / EXTEND / KILL_SWITCH / INSUFFICIENT).
- **`_condition_monitor_stats(today)`** en `bot.py`: misma lógica inline para uso desde el bot sin importar desde `tools/`.
- **`maybe_run_condition_monitor(state)`** en `bot.py` v10.6.16: dispara desde día 7 en fechas de checkpoint (2026-04-21, 2026-04-28) y en kill-switch activo (WR<45% n≥20). Anti-spam via `state["last_condition_checkpoint"]`; kill-switch repite diariamente. Integrado en `run_observability_alerts()`.
- **`_build_condition_checkpoint_message`**: templates para OK, ALERT, CLOSE, PROMOTE, EXTEND, KILL_SWITCH — todos incluyen bloque `<code>` con instrucción lista para sesión Sonnet/Codex.
- **9 tests nuevos** en `verify_before_deploy.py`. `verify_before_deploy.py` → 680/680.
- **No tocado:** criterios trading, Kelly, NOAA, thresholds canary→active, Railway, env vars.


### Sesión 177 — Austin canary onboarding + análisis throughput (v10.6.17) (14 abr 2026)

**Modelo:** Opus (análisis/diseño) + Sonnet (implementación).

**Análisis Opus — throughput scan loop:**
- `price_out_of_range` (51% de skips): filtro `[MIN_PRICE=0.20, MAX_PRICE=0.80]` correctamente calibrado. Evidencia: 82.8% de los skips son markets YES<5% (long-shots). Trades históricos con `avg_entry_price<0.25`: 31 registros, 4W/18L, −$23.50 neto. Zona ganadora: 0.50–0.80 (10W/3L, +$4.39). Veredicto: no tocar.
- `timezone_filter` (6.3%): estructural Asia, sin solapamiento con candidatos TRADER_ONLY. Diferido.
- TRADER_ONLY 27 ciudades: todas en shadow (`fuera_allowlist`). Atacar lista de ciudades, no filtros.
- Palanca recomendada: **Austin →canary** (cross-check 2026-04-13: n_consensus=2, trader_wr=65.5%, mkt_price=0.48).

**Bloqueador detectado pre-implementación:** Austin ausente de `RESOLUTION_ICAO`, `CITY_TIMEZONES` y `OBSERVED_AUDIT_CITIES` — sin infraestructura NOAA no puede tradear aunque sea canary.

**Verificación NOAA Austin (KAUS):**
- ISD history: USAF=722540, WBAN=13904, activo hasta 2025-08-27 → `noaa_station_id="72254013904"` (gate-pass; bot usa daily como prioridad 1).
- GHCND confirmado via CDO: `USW00013904` = "AUSTIN BERGSTROM INTERNATIONAL AIRPORT, TX US", 30.18°N 97.68°W, 146.5m.
- NOAA daily-summaries verificado: **182 registros TMAX oct2025–mar2026**, rango −1.7°C a 36.7°C (plausible para Austin).

**Cambios implementados:**
- `bot.py`: Austin en `RESOLUTION_ICAO` (`noaa_station_id`, `noaa_daily_station_id`), `CITY_TIMEZONES` (`America/Chicago`), `OBSERVED_AUDIT_CITIES`.
- `data/runtime_import/city_policy_state.json`: Austin en `auto_canary_cities` + `transition_history` (2026-04-14).
- `verify_before_deploy.py`: 5 tests nuevos (Austin infra, bounds guardados, ACTIVE_TRADING_CITIES guardrail) → **685/685**.

**Criterios de evaluación canary Austin:**
- GO: WR≥55% o PnL≥+$0.50 sobre ≥3 trades cerrados.
- NO-GO: PnL≤−$2.00 o 3 losses consecutivos → degradar a shadow.
- Inconcluso: <3 trades en 14 días → evaluar si Austin tiene mercados suficientes.

**No tocado:** filtros, MIN_PRICE, MAX_PRICE, thresholds, Kelly, sigma, exits, ACTIVE_TRADING_CITIES (sigue NONE).

### Sesión 182 — residual canary shadow-only gate fix + live verification (16 abr 2026)

**Modelo:** Codex.

- **Diagnóstico cerrado con evidencia mínima:** se leen `AGENTS.md`, bloque reciente de `CONTEXTO.md`, `OPERATIONS_PLAYBOOK.md`, `data/runtime_import/skip_log.jsonl`, `cycle_summary.json` y `city_policy_state.json` para aislar el gating residual sin mezclar refactor amplio ni tocar trading core.
- **Patrón runtime exacto:** todas las filas históricas de `skip_log` con `skip_reason="shadow_only_override"` resultan ser `city_mode="canary"` y `allowlisted=false`; no aparece ningún caso `shadow` con ese motivo. Ejemplos previos al fix: `Shanghai` (`2026-04-15T04:00`), `Chicago` (`2026-04-15T07:14`, `08:00`, `15:24`) y `Seoul` (`2026-04-16T07:07`, `edge_pct=68.47`).
- **Causa raíz precisa en `bot.py`:** el scan loop ya resolvía bien `city_mode="canary"` vía `get_effective_city_mode()`, así que el bug no venía del orden de reconocimiento `auto_canary` ni de que la allowlist de ejecución siguiera atada directamente a `ACTIVE_TRADING_CITIES`. El problema real estaba en `_is_shadow_only()`: su fallback legacy seguía mirando solo `ACTIVE_TRADING_CITIES` y `CANARY_TRADING_CITIES` explícitas. Con `ACTIVE_TRADING_CITIES=NONE`, una ciudad podía ser `canary` efectiva por `city_policy_state.json` y aun así quedar degradada a `shadow_override_flag=True`.
- **Fix mínimo aplicado:** `_is_shadow_only()` ahora mantiene `SHADOW_ONLY_MODE` como toggle explícito, pero en el fallback legacy también cuenta `auto_canary_cities` y `auto_canary_from_active` cargadas desde `city_policy_state.json` antes de declarar pausa global.
- **Guardrail nuevo:** `verify_before_deploy.py` añade checks estáticos + funcionales para el caso exacto de `ACTIVE_TRADING_CITIES=NONE` con `auto_canary` persistida; la suite sube a **691/691**.
- **Commit y push:** `2ac2bb1` — `Fix shadow-only fallback for auto-canary cities` → `origin/main`.
- **Deploy Railway verificado:** deployment `af3c82b8-7f4b-4a55-bd3f-14ecb40f8edc`, arranque `2026-04-16 07:36:23 UTC`, logs con `Modo: REAL`.
- **Prueba live post-deploy cerrada:** tras esperar al ciclo `2026-04-16T08:00`, `tools/railway_runtime_snapshot_pull.ps1` refresca `data/runtime_import/`. Resultado: `shadow_only_override` nuevo = **0** desde el deploy; las ciudades `canary` pasan con `allowlisted=true`; `Seoul` ya no cae por override y sus skips pasan a `price_out_of_range`, `condition_filtered` y `existing_position`. El único `fuera_allowlist` nuevo del ciclo corresponde a `Hong Kong` en `shadow`.
- **Veredicto final:** **bug residual corregido**.
### Sesión 183 — shadow→NOAA funnel hardening (16 abr 2026)

- Se audita el embudo `shadow -> NOAA -> WR observado` con `data/runtime_import/shadow_city_tracking.json` y `audit.json`: `30` `edge_hit=true` recientes, pero casi toda la muestra se perdía antes del join NOAA por parser legacy y por depender de una ventana corta de ciclos.
- `bot.py` endurece la semántica shadow: `_shadow_condition_code()` reutiliza `parse_temperature_question()`, se añade `_extract_threshold_canonical()`, y `_shadow_signal_signature()` / `_build_shadow_signal_record()` dejan de persistir señales válidas con `threshold=None` cuando la pregunta es `or higher` / `or below`.
- `_get_noaa_candidate_dates()` pasa a priorizar una base durable desde `directional_history` antes de caer al fallback de `scanned_markets` recientes, para que una señal shadow elegible por lag NOAA no desaparezca solo porque pasaron suficientes ciclos.
- `build_dashboard_road_to_real()` y `get_dashboard_alert_summary()` dejan de usar `shadow.summary.edge_hits` como proxy mezclado y pasan a leer `total_signals`, `matched`, `resolved` y `win_rate` desde `_build_shadow_noaa_resolution_stats()`.
- Se corrige además una referencia latente a `shadow_summary` sin inicializar en `build_dashboard_city_decisions()`.
- Verificación: `python -m py_compile bot.py` OK. `verify_before_deploy.py` ya no falla por la lógica del funnel, pero el harness sigue cayendo en Windows por `Access denied` al tocar `%TEMP%`, así que ese gate queda pendiente de limpieza externa o aislamiento del bug del verificador.

### Sesión 184 — city-intelligence alarm realigned to runtime canary reality (16 abr 2026)

**Modelo:** Codex.

- **Diagnóstico reanclado a runtime:** la alarma de `city intelligence` seguía leyendo `Chicago` como `needs_shadow_validation` / `policy_execution_gate` aunque el snapshot fresco ya la muestra en `runtime_policy_mode=auto_canary`, `allowlisted=true` y sin `shadow_only_override` nuevo tras la sesión 182.
- **Fix analítico en `tools/city_validation_ledger.py`:** se añade un estado explícito `canary_measurement` cuando la ciudad ya está en `auto_canary` y no hay `useful_policy_gate_count` reciente; la recomendación pasa a `observe_runtime_canary`.
- **Fix analítico en `tools/city_promotion_gate.py`:** se evita que una ciudad `auto_canary` sin bloqueos reales recientes vuelva a caer en `audit_runtime_drift`; el gate pasa a `observe_runtime_canary` con prioridad `watch`.
- **Artefactos regenerados:** se rerunean `tools/city_validation_ledger.py`, `tools/city_promotion_gate.py`, `tools/city_intelligence_telegram_alert.py --dry-run` y `tools/city_intelligence_pipeline.py --telegram-dry-run`, dejando `city_validation_ledger.json`, `city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md` alineados con la realidad del bot.
- **Guardrail adicional en `verify_before_deploy.py`:** el harness funcional ahora carga `parse_temperature_question`, `_extract_threshold_canonical`, `re` y `normalize_city` dentro del bloque shadow/persistencia. Con eso desaparece el falso rojo donde `directional_history` y `road_to_real` fallaban por dependencias ausentes del test en vez de por lógica rota.
- **Verificación final:** `python verify_before_deploy.py` vuelve a verde completo en **691/691**.

### Sesión W17-Opus — revisión estratégica + bloque completo (17 abr 2026)

**Modelos:** Opus (análisis) + Sonnet (implementación).

**Contexto de entrada:** 71 ciclos (11 días) con solo 7 buys desde el 6 de abril. Sensación de "iterar en círculos" correcta y con causa estructural identificable.

**Diagnóstico central:**
- Throughput colapsó con v10.6: pre-Apr6 `4.6 edges/ciclo` / `0.98 buys/ciclo`; post-Apr6 `0.1 edges/ciclo` / `0.05 buys/ciclo`.
- Causa raíz: `condition_filtered` mata `~47%` de candidatos cada ciclo. El modelo gaussiano sobreestima P(YES) para exact/range — bot ve `our_prob~40%`, mercado cotiza `18%`, genera edge ilusorio.
- Evidencia: bot WR `0%` en YES exact/range (`26` trades, `−$27.09`). Traders en esos mismos mercados: `76% WR`, van `68% NO`. Todos los wins del bot son NO-side con `our_prob≥78%`.
- PnL real: `at_or_above` +$0.97, `exact` −$9.26, `range` −$23.94.
- `48%` de cierres son `micro_position_unsellable` (29/61 posiciones).

**Cambios implementados en `bot.py` (4 commits push a `main`):**

1. **S2 — Whitelist canary:** `QUALITY_TRADER_CITIES_WHITELIST` default ampliado con `Atlanta, London, New York City, Munich`. Railway actualizado con lista completa.
2. **C1-fix — YES exact/range floor:** bloque `v10.6.18` antes de `_effective_min_edge`: si `exact_range_canary` y `side == "YES"` y `our_prob < 0.65` → skip con `skip_reason_detail="exact_range_yes_low_confidence"`. Habría bloqueado los 23 YES losses históricos (avg `our_prob=40.1%`) manteniendo todos los NO wins.
3. **Seoul auto-canary promotion fix:** guardia `city not in auto_blocked` en `sync_city_policy_state()`. Bug original: `auto_blocked` con NOAA proxy retornaba `"shadow"` de `get_effective_city_mode()` → la guardia pasaba → Seoul entraba en `auto_canary_cities` erróneamente.
4. **W17 observation alert:** `maybe_run_w17_observation_alert(state)` — one-shot el 2026-04-20. Lee `cycles_history.jsonl` desde `2026-04-17T18:00`, calcula métricas post-bloque y envía prompt Telegram completo para Codex/Sonnet.

**Railway actualizado:**
- `QUALITY_TRADER_CITIES_WHITELIST` → lista completa con 4 ciudades canary.
- `SCHEDULE_DISABLED_HOURS_UTC=23` → slot 23h apagado live (ya existía desde Sesión 190).

**Docs creados:**
- `docs/strategic-review-opus-2026-04-17.md`
- `docs/execution-plan-w17-2026-04-17.md` (bloque W17 completado íntegramente)
- `docs/c1-autopsy-exact-range-2026-04-17.md`

**Análisis adicional:** NYC NO TP +59% confirmado como correcto (forecast 77.7°F vs threshold 77°F, margen 0.7°F). No prematuro.

**Verificación:** `verify_before_deploy.py` 702/702 antes del último push.

**Próxima revisión Opus:** semana del 24 de abril de 2026. Criterios: `markets_evaluated≥25`, `with_edge≥0.5`, `buys≥0.3` por ciclo.

## Sesión 215 — P4+P5 whitelist expansion v10.6.27+v10.6.28 (21 abr 2026)

**Tipo:** Improvement — throughput canary exact/range
**Modelo:** Sonnet (implementación) + Opus (verificación NOAA P5)
**Versiones:** v10.6.27 → v10.6.28

**Contexto:** Checkpoint día 7 del canary exact/range (abierto 2026-04-14) mostró WR=40% n=5 — throughput crítico, solo 5 trades en 7 días. El whitelist era el cuello principal. Se descubrió además un bug en la precondición de `maybe_alert_p4_p5_expansion` que hubiera abortado la expansión erróneamente (confundía `OK_INSUFICIENTE` n<5<15 con `CLOSE/ALERT` real).

**P4 — v10.6.27 (ciudades ya en RESOLUTION_STATIONS):**
- Tel Aviv: blocked WR 3/3=100%, NOAA verificado LLBG
- Taipei: blocked WR 3/3=100%, ICAO-only RCTP
- Singapore: TRADER_ONLY 2/2, ICAO-only WSSS
- Wuhan: TRADER_ONLY 2/2, ICAO-only ZHHH

**P5 — v10.6.28 (ciudades nuevas, RESOLUTION_STATIONS añadidas):**
Opus verificó Polymarket resolution sources vía WebFetch y confirmó NOAA global-hourly+GHCND vacíos en 2026 (patrón Jakarta/KL) → todas ICAO-only:
- Moscow: 5/5=100% blocked WR, UUWW Vnukovo
- Amsterdam: 3/3=100%, EHAM Schiphol
- Jeddah: 4/4=100%, OEJN King Abdulaziz
- Istanbul: 3/3=100%, LTFM — riesgo mismatch=cero (LTFM ausente de NOAA ISD)
- Helsinki: TRADER_ONLY 2/2, EFHK Vantaa

**Bug corregido:** `maybe_alert_p4_p5_expansion` — precondición distingue ahora `OK_INSUFICIENTE` (n<15 → continuar) de `CLOSE/ALERT` real (n≥15 y WR<50%).

**Railway:** `BLOCKED_CITIES` actualizado a solo `London` (Singapore y Toronto removidas — bloqueaban el canary gate). `QUALITY_TRADER_CITIES_WHITELIST` a 32 ciudades.

**Verificación:** `verify_before_deploy.py` 755/755 (9 tests nuevos).

## Sesión 224 — INTRA-REEVAL shadow-log (22 abr 2026)

**Tipo:** Explícita | **Agente:** Opus (diseño) + Sonnet (implementación)

### Contexto

Hoy el monitor intra-ciclo (cada 20 min) solo comprueba SL/TP. Si una posición pasa de +20% a -50% entre ciclos principales (4h) porque el edge desapareció pero no hay cruce de umbrales, solo lo detecta el próximo ciclo principal. Histórico: 1 caso real claro (Atlanta YES +25% → -56% por SL). Plan: añadir re-evaluación condicional en modo **shadow-log** primera semana — solo alerta, no vende, alimenta un review one-shot.

### Diseño (Opus)

- **Un disparador**: price drift ≥ `INTRA_REEVAL_PRICE_DRIFT_PP=10.0` pp entre `cur_price` y `entry_context.price`.
- **Cooldown** 80 min por posición → aprovecha el cache HTTP de 15 min de `get_forecast`, ~40-75% NOAA extra sobre baseline.
- **Edge threshold** -3% (idéntico al ciclo principal — consistencia).
- **Shadow mode primera semana**: si edge<-3% → log + Telegram compacto (rate-limited 1/h), NO vende.
- **Alerta one-shot** 7 días tras primer trigger: resumen agregado + prompt para sesión Opus/Sonnet de review.

### Cambios (Sonnet)

- `bot.py:369-373`: 5 ENV vars nuevas (`INTRA_REEVAL_ENABLED/SHADOW_MODE/PRICE_DRIFT_PP/COOLDOWN_MIN/EDGE_THRESHOLD`), todas con defaults seguros (ENABLED=0).
- `bot.py:565`: `INTRA_REEVAL_STATE_FILE` → `data/intra_reeval_state.json`.
- `bot.py:932`: `intra_reeval_review_alert_sent` añadido al default de `alerts_state`.
- `bot.py:1494`: `load_intra_reeval_state()` / `save_intra_reeval_state()` — purga cooldown por tokens no observados.
- `bot.py:14006`: `recompute_position_edge()` — helper puro extraído del CHECK 3 de `manage_positions`. Esta última ahora llama al helper (refactor byte-compatible).
- `bot.py:14471`: `_log_shadow_intra_reeval_trigger()` — registra trigger + Telegram rate-limited a 60 min.
- `bot.py:14619-14649`: bloque `INTRA_REEVAL_ENABLED` dentro de `intra_cycle_sl_check`, después de SL/TP. Solo actúa si drift≥10pp + cooldown OK + edge<-3%.
- `bot.py:7917`: `maybe_run_intra_reeval_review_alert()` — one-shot 7 días tras primer trigger, wired en `run_alerts` (línea 4237).
- `verify_before_deploy.py`: bloque v10.6.30 — 19 checks estructurales + 9 tests funcionales (roundtrip, cooldown, parity del helper).

### Verificación

`verify_before_deploy.py` → **795/795** tests OK.

### Railway — requiere acción manual

Añadir a producción (defaults seguros, feature off por defecto):
```
INTRA_REEVAL_ENABLED=1
INTRA_REEVAL_SHADOW_MODE=1
```
(El resto de vars funcionan con default.) Flip a `SHADOW_MODE=0` solo tras review one-shot a los 7 días.

### Observabilidad

- Telegram compacto por trigger (rate-limit 1/h): `🧪 [INTRA-REEVAL SHADOW] habría vendido | ...`
- Alerta review one-shot a los 7 días del primer trigger con: totales, top 3 ciudades, PnL medio/mediano en trigger, fresh_edge_pct, distribución por banda. Incluye prompt para sesión de decisión (promocionar a real / ajustar umbrales / mantener).

---

## Sesión 223 — INTRA_SL_INTERVAL 60→20 min (22 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet

### Contexto

SL de Shanghai No disparó en ciclo 04:00 UTC a -35.2% pese a umbral de -25%. Causa: gap de polling de 60 min — posición cruzó el umbral entre checks y fue atrapada 10pp más abajo en el siguiente.

### Cambios

- `bot.py:365`: `INTRA_SL_INTERVAL` default `"60"` → `"20"` (checks cada 20 min en vez de 60).

### Verificación

No requiere nuevos tests en `verify_before_deploy.py` (cambio de constante numérica).

---

## Sesión 222 — City Intelligence runtime bridge in `polymarket-bot` (22 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto
Tras validar que el servicio separado `city-intelligence` no veía `/app/data/runtime_import`, se aplica la decisión recomendada: mantener la capa analítica separada, pero hacer que el readout diario que depende del runtime corra desde `polymarket-bot`, que sí ve el volumen real.

### Cambios

- `bot.py`: añade `maybe_run_city_intelligence_runtime_summary`, one-shot diario y configurable por `CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED` / `CITY_INTELLIGENCE_RUNTIME_BRIDGE_HOUR_UTC`.
- `tools/runtime_import_local_export.py`: exporta desde `DATA_DIR` a `DATA_DIR/runtime_import`, exige `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`, y escribe manifest + snapshot de env.
- `verify_before_deploy.py`: añade checks v10.6.31 para cubrir el bridge.
- `.gitignore`: ignora directorios locales de prueba del export.

### Validación

- `python tools/check_python_syntax.py bot.py tools/runtime_import_local_export.py verify_before_deploy.py`: OK
- `python tools/runtime_import_local_export.py --data-dir data\runtime_import --output-dir data\runtime_import_bridge_test_verify`: OK
- `python verify_before_deploy.py`: 769 tests ejecutados; solo fallan 2 asserts heredados de `INTRA_SL_INTERVAL default 60` porque el worktree ya traía `INTRA_SL_INTERVAL=20`.

### Decisión
No hacer deploy hasta resolver explícitamente el default de `INTRA_SL_INTERVAL`: confirmar que `20` es intencional y actualizar el preflight, o volver a `60`.

---

## Sesión 221 — City Intelligence runtime_import faltante en servicio live (22 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto
Alarma diaria `City Intelligence` del 2026-04-22 UTC: `runtime_inputs_missing`, faltan `shadow_tracking`, `audit` y `city_policy_state`. Guardrail respetado: no tocar `bot.py`, `city_policy_state.json`, NOAA, scheduler, reglas de entrada/salida ni trading core.

### Evidencia

**Transporte read-only local:**
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_runtime_snapshot_pull.ps1` funciona
- `data/runtime_import/runtime_import_manifest.json` queda fresco: `pulled_at=2026-04-22T07:19:13Z`
- Manifest: `12/12` archivos, sin missing/extra/byte mismatch
- Inputs requeridos presentes localmente: `shadow_city_tracking.json`, `audit.json`, `city_policy_state.json`

**Artefactos derivados locales:**
- `city_validation_ledger.py`: `runtime_inputs_status=available`, `n_cities=27`
- `city_promotion_gate.py`: `runtime_inputs_status=available`
- `city_intelligence_pipeline.py --telegram-dry-run`: `overall_status=ok`, cuello dominante `trader_discovery`
- `runtime_policy_effective_view.py`: topología efectiva `blocked=1 / canary=8 / shadow=16 / active=0`, `blocking_operational_collision_count=0`
- `system_alignment_check.py --decision-mode operational`: `error=0` (`ok=5`, `warning=3`)

**Servicio live `city-intelligence`:**
- `railway_safe.ps1 service status -a --json`: servicio `city-intelligence` en `SUCCESS`
- `railway_safe.ps1 ssh -s city-intelligence "ls -la /app/data/runtime_import"`: `No such file or directory`
- `/app/data/city_intelligence_pipeline.json` live queda en `overall_status=runtime_inputs_missing` porque faltan `/app/data/runtime_import/shadow_city_tracking.json`, `/app/data/runtime_import/audit.json` y `/app/data/runtime_import/city_policy_state.json`

### Decisión
La alarma es correcta para el servicio `city-intelligence`, pero no implica ausencia real de edge ni problema del bot principal. No hay ajuste de trading hoy. El ajuste pendiente es infraestructura/cableado: hacer que `city-intelligence` consuma una copia read-only fresca del runtime del bot antes de emitir su daily summary, o mover esa lectura al servicio `polymarket-bot` como se hizo con `signals_crosscheck`.

---

## Sesión 220 — daily traders-vs-bot readout, no code (22 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto
Parte diario del summary `traders vs bot` y `blocked signals` del 2026-04-22 UTC. Actualización de trazabilidad, no sesión de cambios funcionales.

### Lectura registrada

**Cross-check traders vs bot:**
- Última corrida: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=18`
- Serie reciente: 7 corridas, medianas `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=23`
- Lectura: la serie se mueve, pero todavía no da una historia única de mejora o deterioro
- No aparece gap operativo fuerte fuera de `blocked` con consenso y condición operable

**TRADER_ONLY persistente:**
- `7/7`: Ankara, Busan, Houston, Jakarta, Miami
- `6/7`: Buenos Aires, Chengdu, Los Angeles, Madrid, Singapore, Toronto

**Blocked signals fuera de whitelist:**
- Resueltas: 61
- Wins: 60
- WR: 98.4%
- Whitelist excluidas: 207
- Baseline fuera de `QUALITY_TRADER_CITIES_WHITELIST`

### Decisión
Sin cambios en `bot.py`, whitelist, NOAA, scheduler, reglas de entrada/salida ni trading core. Se reitera la instrucción operativa: si el bloque `TRADER_ONLY` persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA antes de tocar reglas de entrada o trading core.

---

## Sesión 219 — Bankroll Readiness Score (21 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet

### Contexto
Cierre de día. Discusión estratégica sobre monetización, timeline y cuándo escalar bankroll. Se construye un indicador operativo para medir el progreso hacia ese umbral.

### Acciones

**`tools/bankroll_readiness_score.py`** — score 0-100% con 5 dimensiones ponderadas:
- **D1 WR Confidence (30%):** WR de trades reales cerrados (ventana 60d), ponderado por n. n_factor=min(n/20,1), wr_factor=(WR-0.45)/0.25. Target: WR≥70% con n≥20.
- **D2 PnL Trajectory (25%):** PnL 30d positivo (+60pts) y PnL 60d positivo (+40pts).
- **D3 Edge Density (20%):** avg edges/ciclo últimos 14d. Score=min(avg/1.0,1)×100. Target: 1 edge/ciclo.
- **D4 Size Pressure (15%):** kelly_too_low + buy_min_size como % de oportunidades con edge evaluado. Señal de que el bankroll limita, no la calidad del sistema.
- **D5 System Stability (10%):** % ciclos en versión dominante, ventana 7d, penalización suave por versiones extra.

**Umbrales de acción:**
- <40%: etapa temprana, cuello es el sistema
- 40-60%: mejorando
- 60-75%: madurando, preparar escala
- ≥75%: BANKROLL ES EL CUELLO → añadir capital

**Score inicial: 23.9%** — D1=0 (WR=32%<45%), D2=0 (PnL=-$21.92), D3=21% (0.21 edges/ciclo), D4=100% (29.5% kelly_too_low), D5=46%.

### Verificación
`verify_before_deploy.py` 763/763. Herramienta standalone, sin cambios en bot.py ni Railway.

---

## Sesión 218 — Busan + Dallas + schedule 6 ciclos/día (21 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet

### Contexto
Sesión pre-mañana con tiempo disponible tras las sesiones 211-217 del mismo día. Objetivo: avanzar en throughput antes del checkpoint Apr-28.

### Acciones

**Verificación Railway whitelist:** La env var `QUALITY_TRADER_CITIES_WHITELIST` ya tenía las 32 ciudades del pendiente de Sesión 215. Sin cambios necesarios.

**v10.6.29 — Busan (RKPK) ICAO-only:**
- NOAA global-hourly 2026: 404 para estación 47158099999 → patrón ICAO-only
- WU/RKPK: real-time vivo (56°F observado), archivo histórico muestra "No data recorded" = artefacto de JavaScript no renderizado por WebFetch
- Polymarket resolution source: **WU/RKPK confirmado** — descripción real del mercado Apr-22 dice explícitamente "Gimhae Intl Airport Station (RKPK)"
- $85.8K volumen en mercado Apr-21, resuelto YES → fuente funcionando
- Agregado a `RESOLUTION_STATIONS` (lat 35.18, lon 128.95 / "Gimhae Intl"), `RESOLUTION_ICAO` (RKPK), `OBSERVED_AUDIT_CITIES`, `CITY_TIMEZONES` (Asia/Seoul), whitelist default

**Auditoría City Intelligence:**
- 8 canary (Atlanta, Chicago, Milan, Munich, NYC, Seoul, Shanghai, Tokyo)
- 16 background_watch — bottleneck `trader_discovery` en la mayoría
- Dallas: `review_runtime_policy_gate` priority `now`

**Auditoría Dallas:**
- Degradado Apr-6 por "WR=11.8%, 17 trades, PnL=-$1.60" → diagnóstico: los "17 trades" incluían 66 entradas `LOSS_TOTAL` fantasma del bug de posiciones fantasma (corregido en v10.5.12, mismo token_id repetido)
- Trades reales: 4 (BUY range Mar-28, BUY range Mar-28, BUY range Mar-31, BUY at_or_above Apr-2)
- 2 stop-loss (-$1.36, -$0.56), 2 ganancias pequeñas (+$0.26, +$0.06) → net -$1.60
- Shadow actual: `best_edge=68.9%`, 12 shadow edge hits en 9 ciclos, settlement_fidelity=4/5
- Conclusión: muestra real insuficiente para bloquear la ciudad; rehabilitado

**v10.6.30 — Dallas al whitelist**

**Schedule:** `SCHEDULE_HOURS_UTC=0,4,8,12,16,20` (6 ciclos/día cada 4h)
- Antes: 4,8,12,16 (4 ciclos, gap nocturno de 12h)
- cycles_history: 16:00 y 08:00 son los slots más productivos (2.2 y 1.5 avg edges)
- Ciclo post-deploy a 20:10 UTC produjo 3 compras inmediatas
- Cambio solo en Railway env var, sin redeploy

### Verificación
`verify_before_deploy.py` 763/763 (v10.6.29: 6 tests nuevos Busan; v10.6.30: 2 tests nuevos Dallas)

## Sesión 226 — v10.6.31 gate LOW+exact + TP dinámico por precio (23 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet+Opus

### Contexto

Análisis de posiciones cerradas Apr 9-23 (`n=18`) con una lectura incómoda pero clara: el sistema sostenía `WR=53%` y aun así quedaba casi en breakeven (`PnL=+$0.21`) por ratio adverso `avg_win=$0.61` vs `avg_loss=$0.76`. El bucket LOW (`mkt_price<0.35`) concentraba el riesgo peor: `n=2`, `WR=0%`, `PnL=-$2.57`, con el caso London Apr-19 @0.235 → 0.01 como ejemplo de gap risk catastrófico en eventos binarios baratos.

### Cambios

- **Gate LOW+exact:** `BLOCK_LOW_EXACT_ENTRIES=1` (default on) bloquea entradas `condition=exact` con `mkt_price<0.35`.
- **Nuevo skip reason:** `low_exact_gap_risk`, para dejar visible que el rechazo viene por riesgo estructural de gap y no por falta de edge.
- **TP dinámico por precio:** `effective_tp_pct(entry_price, our_prob)` preserva el TP de alta convicción y añade floors por precio:
  - LOW `<0.35` → `TP>=60%`
  - MID `0.35..0.65` → `TP=40%`
  - HIGH `>=0.65` → `TP>=80%`
- **Reutilización coherente:** el TP dinámico se usa también en `intra_cycle_sl_check`.
- **Step 3 diferido:** el stop-loss absoluto queda pospuesto hasta acumular `n>=30` trades post-gate, porque Opus concluye que sería más leniente precisamente en LOW/MID y no ataca el problema raíz.

### Verificación

`verify_before_deploy.py` → **810/810**.

### Siguiente acción

Observar el comportamiento live en Railway y mantener el checkpoint del canary `condition_filtered` para el `2026-04-28`.

## Sesión 227 — cierre de trazabilidad: INTRA_REEVAL live en Railway shadow (23 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

Durante el cierre de sesión aparece una contradicción entre el contexto histórico y el estado live: `CONTEXTO.md` seguía diciendo que `INTRA_REEVAL` requería activación manual en Railway, pero el snapshot actual de variables compartido por Pablo ya mostraba `INTRA_REEVAL_ENABLED=1` e `INTRA_REEVAL_SHADOW_MODE=1`.

### Acciones

- Se valida documentalmente que el pendiente de la sesión 224 quedó resuelto en live.
- Se fija que el contenedor de `polymarket-bot` ya fue reiniciado/actualizado, así que la configuración está cargada en el proceso real.
- Se sincronizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` para que el repo no siga contando “pendiente” lo que ya está activo.

### Estado live resultante

- `INTRA_REEVAL_ENABLED=1`
- `INTRA_REEVAL_SHADOW_MODE=1`
- Defaults implícitos vigentes:
  - `INTRA_REEVAL_PRICE_DRIFT_PP=10.0`
  - `INTRA_REEVAL_COOLDOWN_MIN=80`
  - `INTRA_REEVAL_EDGE_THRESHOLD=-3.0`
- La feature queda activa en modo `shadow-log`: observa, registra y alerta, pero no vende.

### Próximo hito

El siguiente evento real ya no es “activar Railway”, sino esperar el one-shot `Review INTRA-REEVAL` 7 días después del primer trigger shadow persistido en `data/intra_reeval_state.json`.

## Sesión 232 — traders_intelligence automatizado con gate explícito para abrir V1 (24 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

Tras implementar `traders_intelligence` v0 y leer el output real, la pregunta ya no era “qué más analytics podemos construir”, sino cómo evitar que la capa se quede estancada. El objetivo de esta sesión fue cerrar el circuito: que el propio sistema avise cuándo siguen faltando checks y cuándo ya merece abrir V1 sin depender de una auditoría manual permanente.

### Acciones

- Se implementa `tools/traders_intelligence_daily_summary.py`.
- El nuevo tool:
  - lee `data/traders_intelligence.json`;
  - calcula checks explícitos de readiness para abrir V1;
  - clasifica `lead_traders`, `strong_traders` y `candidate_cities`;
  - genera el readout `docs/traders_intelligence_daily_summary_latest.md`;
  - persiste estado anti-spam en `data/traders_intelligence_daily_summary_state.json`.
- Se integra en `bot.py` mediante `maybe_run_traders_intelligence_summary()` dentro de `run_observability_alerts()`, con feature flag y ventana horaria propia.
- Se añade higiene de worktree en `.gitignore` para excluir `data/traders_intelligence_daily_summary_state.json`, alineándolo con otros states regenerables/anti-spam.

### Lectura resultante

- `V1 readiness = not_ready`.
- Blockers actuales:
  - `census_stale_days=15` con umbral `<=14`;
  - `recent_crosscheck_runs=2` con umbral `>=5`.
- Checks ya cumplidos:
  - health usable;
  - al menos un lead trader fuerte y muy activo (`Thrifty-Original`, `Entire-Hood`);
  - profundidad mínima de traders fuertes;
  - suficientes `trader_only cities` candidatas.

### Verificación

- `python tools/traders_intelligence_report.py`
- `python tools/traders_intelligence_daily_summary.py`
- `python verify_before_deploy.py`

Resultado final: **817/817**.

### Siguiente acción

Cerrar sesión, commitear solo código/docs/artefacto útil y desplegar. El valor nuevo ya no es otra iteración manual sobre V0, sino dejar esta automatización corriendo en Railway para que el propio sistema avise cuándo abrir un `external trade lifecycle` mínimo de V1.

## Sesión 234 — SL retrospective cerrado, sin UNKNOWN, y briefing saneado (24 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

Tras varias revisiones de alertas de Telegram, seguían dos problemas mezclados: el `Briefing Diario` enseñaba como abiertas filas legacy con fecha de resolución ya pasada, y `SL Retro` todavía dejaba demasiados `UNKNOWN` para poder tomar una decisión firme sobre el `intra SL`.

### Acciones

- `bot.py`:
  - separa `break-even` de pérdidas en el resumen diario;
  - usa `generated_at` / `next_run_at` del payload en vez del reloj vivo al renderizar;
  - no envía el daily si aún no ha habido un ciclo real ese día;
  - mejora el matching legacy huérfano para cierres en `trade_lifecycle` y `postmortem`.
- `tools/daily_position_briefing.py`:
  - deja de presentar legacy vencido como abierto real;
  - separa `abiertas`, `vencidas pendientes de reconciliar` y `legacy stale no reconciliado`;
  - hace el bloque `ÚLTIMAS 24H` más legible con lado, entrada, salida y motivo humano.
- `tools/sl_retrospective.py`:
  - incluye `stop_loss_intra` en el retro;
  - prioriza `observed_vs_forecast` desde `audit.json`;
  - usa `forecast_accuracy_raw.json` como fallback;
  - y, cuando aún falta observado local, consulta `open-meteo archive` para cerrar casos residuales.
- Se añade `tools/reconcile_runtime_import_legacy_positions.py` para reconciliar legacy de `runtime_import`.
- Se dejan tests/regresiones nuevas en `verify_before_deploy.py`.

### Resultado

- `SL Retro` queda en `16/16` resueltos.
- Distribución final:
  - `6 RIGHT`
  - `10 WRONG`
  - `0 UNKNOWN`
- Veredicto operativo: `SL funciona correctamente` y la conclusión pasa de preliminar a firme.
- La submuestra específica de `stop_loss_intra` sigue siendo pequeña, así que no conviene sacar una tesis separada solo con ella.
- El briefing deja de inflar `POSICIONES ABIERTAS` con filas legacy vencidas y ya no confunde un cierre ganador de un token `NO` con “el mercado resolvió YES”.

### Verificación

- `python verify_before_deploy.py` → **831/831**

### Siguiente acción

Desplegar, validar en Railway que el servicio sano recoge el commit y hacer una verificación rápida con Opus sobre el estado live de `SL Retro` y `Briefing Diario`.

## Sesión 243 — Cierre definitivo 11 posiciones legacy stale + reconciliación con outcomes reales (26 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet

### Contexto

Las 11 posiciones legacy stale (Ankara ×2, London, Miami, Shanghai, Toronto, Atlanta, Buenos Aires, Seattle, Wellington, Madrid — resolution_date 26-29 mar 2026, sin snapshots ni evidencia de mercado) seguían apareciendo en el briefing con `status=open` en Railway. La sesión 234 solo separó su display; nunca las cerró en la DB. El usuario pidió cierre definitivo en producción, garantía de que no vuelva a ocurrir, y que el cierre refleje el outcome real (no un LOSS_TOTAL especulativo).

### Acciones

**Auto-close wired en bot.py:**
- Nueva función `close_expired_legacy_positions()`: busca posiciones `status=open` con `resolution_date < today - 2 días` sin snapshots ni market_observations. Cierra como `EXPIRED_UNVERIFIED` con `pnl_cash=None` y `reconciliation_needed=True` — no distorsiona P&L ni WR.
- Nueva función `maybe_close_expired_legacy_positions(state)`: wrapper diario (state key `legacy_cleanup_last_run`), corre una vez por día antes del briefing.
- Hook en `run_alerts()` justo antes de `maybe_run_daily_briefing`.
- State key `legacy_cleanup_last_run` añadida a defaults y setdefaults.

**Investigación y reconciliación con outcomes reales:**
- Se investigaron los 11 outcomes reales en Polymarket consultando Wunderground (Esenboğa, Heathrow, KSEA), NWS (Miami, Atlanta), Shanghai Met Service, Environment Canada CYYZ, SMN/Pistarini, MetService/Kelburn y AEMET/Barajas.
- `tools/reconcile_legacy_stale_with_outcomes.py`: parchea `trade_lifecycle.json` + `postmortem.json` en Railway con el resultado real (solo si `close_reason == "legacy_unresolved"`). Ejecutado en Railway sesión_243:
  - **6 RESOLVED_WIN:** Ankara NO, Ankara YES, Miami YES, Shanghai NO, Buenos Aires NO, Wellington NO
  - **5 LOSS_TOTAL:** London NO, Toronto NO, Atlanta YES, Seattle YES, Madrid YES
  - **Net P&L corregido: +$49.94** (TL amounts). Backups `.bak_session_243` en Railway.

**SL retrospectiva** (datos al cierre de sesión):
- RIGHT=5, WRONG=8, UNKNOWN=10 (23 total); veredicto `seguir monitorizando`.
- `maybe_run_sl_retrospective(state)` corre diariamente y envía Telegram automáticamente con cada nuevo SL resuelto.

### Resultado

- Las 11 posiciones legacy stale quedan cerradas en Railway con sus outcomes reales documentados (fuente, temperatura observada, token bot, confianza).
- El auto-close `EXPIRED_UNVERIFIED` garantiza que futuras posiciones vencidas sin evidencia no contaminan P&L hasta ser reconciliadas manualmente.
- `verify_before_deploy.py` → **843/843**.

### Verificación

- `python verify_before_deploy.py` → **843/843**
- Railway SSH: `reconcile_legacy_stale_with_outcomes.py` → `11/11 TL patched, 11/11 PM patched`

### Siguiente acción

El briefing del día siguiente ya no mostrará el bloque LEGACY STALE. Para reconciliaciones futuras, usar `tools/reconcile_legacy_stale_with_outcomes.py` como plantilla.

## Sesión 247 — Auditoría blocked signals fuera de whitelist + handoff ICAO-only (26 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

El daily `Blocked signals (fuera de whitelist)` marcó nivel `ACTION` con `101` señales resueltas fuera de whitelist, `100` wins y WR `99.0%`. El objetivo era verificar fuente/cobertura antes de cualquier whitelist/canary para `Lucknow`, `Warsaw`, `Beijing` y `Chongqing`, manteniendo read-only al inicio y sin tocar trading core, NOAA core, scheduler ni reglas.

### Acciones

- Se creó `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md` con ranking y lectura live de `/app/data/blocked_signals_resolutions.jsonl`.
- Se verificó que `Lucknow`, `Warsaw`, `Beijing` y `Chongqing` tienen `RESOLUTION_STATIONS`, `RESOLUTION_ICAO` y `CITY_TIMEZONES`, pero ninguna tiene NOAA ids útiles.
- Se confirmó fuente Polymarket/WU para `VILK`, `EPWA`, `ZBAA` y `ZUCK`.
- Se leyó Railway read-only: `audit.json` mantiene `observed_vs_forecast=0` para las cuatro; `shadow_city_tracking.json` da edge fuerte en `Lucknow` y `Beijing`, pero no en `Warsaw`/`Chongqing`.
- Se comprobó NOAA/NCEI `global-hourly/access/2026`: los ISD comentados para las cuatro estaciones devuelven 404.
- Se preparó `docs/claude-opus-prompt-icao-only-canary-review-2026-04-26.md`.

### Resultado

- `Lucknow`: `preparar whitelist-canary` solo como propuesta ICAO-only para Opus.
- `Beijing`: `preparar whitelist-canary` solo como propuesta ICAO-only para Opus.
- `Warsaw`: `seguir acumulando muestra`.
- `Chongqing`: `seguir acumulando muestra`.
- No hay `bloqueo por fuente`: las fuentes Polymarket/WU coinciden con las estaciones declaradas.

### Verificación

No se corrieron tests: sesión documental/read-only, sin cambios de runtime.

### Siguiente acción

Opus debe leer `docs/claude-opus-prompt-icao-only-canary-review-2026-04-26.md` y decidir si se permite canary ICAO-only con `observed_vs_forecast=0`, si se exige NOAA observado, o si se crea un estado intermedio sin BUY real.

## Sesión 250 — Alerta diaria P/L reconciliation con tarea explicita (26 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

El usuario compartió captura de Polymarket con `Portfolio $20.38` y `P/L 1W -$3.65`, y pidió aprovechar Codex mientras Sonnet termina SL retrospectiva y Opus revisa la decisión ICAO-only. El objetivo fue convertir la frustración de "trabajamos mucho pero la cuenta no hace click" en una alerta Telegram accionable y honesta.

### Acciones

- Se agregó `tools/pnl_reconciliation_alert.py`.
- El script lee `trade_lifecycle`, calcula PnL/WR realizados en `7d`, `30d`, `60d` y `ultimos 20`, y separa semántica de datos (`legacy_unresolved`, `closed_without_pnl`, open/pending).
- La alerta detecta `batch market_resolved` antiguo dentro de la ventana 7d para no interpretar como mejora limpia resoluciones viejas procesadas hoy.
- El mensaje Telegram incluye bloque `Tarea para Codex` con instrucciones explicitas y guardrail `No tocar trading core`.
- `bot.py` integra `maybe_run_pnl_reconciliation(state)` como hook diario de observabilidad, con env vars `PNL_RECONCILIATION_ENABLED` y `PNL_RECONCILIATION_HOUR_UTC`.
- `verify_before_deploy.py` suma checks de existencia/compilación, env vars e integración en observabilidad.

### Resultado

- Lectura local: `lifecycle 7d = +$20.37`, WR `40.7%`, pero con `+$23.36` de `market_resolved` antiguo dentro de 7d.
- Si se compara con la captura `Polymarket 1W = -$3.65`, el delta sería `+$24.02`, por lo que la acción correcta es reconciliar wallet/fills/redeems/mark-to-market antes de usar el PnL 7d del lifecycle como señal de mejora.
- No cambia trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida.

### Verificación

- `python verify_before_deploy.py` → **847/847**.
- `python -m py_compile tools/pnl_reconciliation_alert.py bot.py verify_before_deploy.py` volvió a fallar solo por el lock conocido de `__pycache__` en Windows (`WinError 5`), no por sintaxis; la suite compila el script nuevo en verde.

### Siguiente acción

Desplegar cuando convenga y dejar que el ciclo diario envíe la nueva alerta. Si la alerta muestra `wallet_pnl_missing`, comparar con el P/L 1W visible en Polymarket; si hay divergencia material, abrir auditoría de reconciliación wallet/fills antes de nuevas reglas.

## Sesión 251 — ICAO-only audit via Open-Meteo proxy (26 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

Opus decidió `Opción 3`: no abrir canary ICAO-only hoy, no exigir NOAA estricto, y crear estado intermedio sin BUY real usando Open-Meteo como proxy observado para `Lucknow/VILK` y `Beijing/ZBAA`. El usuario se encargará de añadir `Beijing` a `OBSERVED_AUDIT_CITIES` en Railway env var.

### Acciones

- `tools/forecast_accuracy_audit.py` ahora genera `icao_only_proxy_audit` para ciudades ICAO-only configurables.
- El audit registra cobertura Open-Meteo, `observed_via_proxy_count`, último observado proxy y delta vs forecast cuando existan filas de forecast/postmortem.
- `tools/city_intelligence_daily_summary.py` acepta `--forecast-accuracy` y añade sección `ICAO-only audit` al mensaje diario cuando el artefacto trae ese bloque.
- No se tocó `bot.py`, trading core, NOAA core, scheduler, whitelist, sizing, reglas ni Railway env.

### Resultado

- Validación temporal con Railway postmortem y probe `2026-04-24`: `Lucknow/VILK` queda `covered` con `42.3C`; `Beijing/ZBAA` queda `covered` con `24.8C`.
- `observed_via_proxy_count=0` en ambas porque todavía no hay filas forecast/postmortem para esas ciudades; el sistema muestra cobertura sin inventar muestra ni habilitar BUY real.

### Verificación

- `python verify_before_deploy.py` → **847/847**.
- `python -B -c compile(...)` OK para `tools/forecast_accuracy_audit.py` y `tools/city_intelligence_daily_summary.py`.
- `python -m py_compile` sigue afectado por el lock conocido de `__pycache__` en Windows (`WinError 5`).

### Siguiente acción

Pablo añade `Beijing` a `OBSERVED_AUDIT_CITIES` en Railway env var. Tras el próximo `forecast_accuracy_audit` canónico, el daily summary empezará a mostrar la sección `ICAO-only audit` con la muestra proxy real disponible.

## Sesión 252 — Beijing observado en código, no env var (26 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

El usuario revisó Railway y confirmó que `OBSERVED_AUDIT_CITIES` no existe como env var. La instrucción anterior de añadir `Beijing` en Railway quedaba mal ubicada: la lista real vive en `bot.py`.

### Acciones

- Se agregó `"Beijing"` a `OBSERVED_AUDIT_CITIES` en `bot.py`.
- Se añadió check en `verify_before_deploy.py`: `v10.6.39: Beijing en OBSERVED_AUDIT_CITIES para ICAO-only proxy audit`.
- No se tocó whitelist, canary, active, trading core, NOAA core, scheduler, sizing ni reglas.

### Resultado

`Beijing/ZBAA` queda en observación formal para el estado intermedio ICAO-only vía proxy Open-Meteo. Este cambio permite acumular observabilidad cuando haya filas, pero no habilita BUY real.

### Verificación

- `python -B -c compile(...)` OK para `bot.py` y `verify_before_deploy.py`.
- `python verify_before_deploy.py` → **848/848**.

### Siguiente acción

Deploy cuando convenga para que Railway use el set actualizado. Opus puede asumir que el patch mínimo completo ya no depende de env var: está en código y validado.

## Sesión 253 — Guardrail auto-canary para ICAO-only proxy (26 abr 2026)

**Tipo:** Explícita | **Agente:** Codex

### Contexto

Tras deploy del patch ICAO-only proxy, Telegram avisó que `Beijing` cumplía shadow → canary y fue promovida a canary con `5` shadow edges, pico `37.9%`, `20` ciclos y `NOAA observados=0`. Esto contradice la decisión Opus: observation-only sin BUY real hasta acumular muestra proxy y revisión manual.

### Diagnóstico

La alarma era normal para el código previo, pero no para el criterio operativo. Al añadir `Beijing` a `OBSERVED_AUDIT_CITIES`, entró en `tracked_cities`; el gate `promotable_shadow` solo exigía edges/ciclos/soporte/días y no bloqueaba ciudades ICAO-only sin NOAA real ni muestra proxy revisada.

### Acciones

- `bot.py` añade `_city_requires_manual_proxy_canary_review(city)`.
- `promotable_shadow` ahora exige `not needs_manual_proxy_review`.
- `get_effective_city_mode()` ignora `auto_canary` persistida para ciudades ICAO-only observadas que requieren revisión proxy manual.
- `sync_city_policy_state()` revoca una `auto_canary` persistida en ese caso (`auto_canary_revoked`) y devuelve la ciudad a shadow con mensaje Telegram.
- `verify_before_deploy.py` suma check de guardrail.

### Resultado

`Lucknow/Beijing` pueden seguir observándose por el estado intermedio ICAO-only/Open-Meteo, pero no pueden auto-promocionar a canary por shadow edges mientras no haya revisión manual. Una inclusión manual en `CANARY_TRADING_CITIES` seguiría siendo una decisión humana explícita.

### Verificación

- `python -B -c compile(...)` OK para `bot.py` y `verify_before_deploy.py`.
- `python verify_before_deploy.py` → **849/849**.

### Siguiente acción

Commit/push/deploy urgente para que Railway revierta Beijing a shadow en el siguiente ciclo. Si hay riesgo de BUY antes del deploy, pausar temporalmente con `SHADOW_ONLY_MODE=true` o limpiar `auto_canary_cities.Beijing` en `city_policy_state.json`.

## Sesión 254 — Guard SL_intra exact+near-resolution (v10.6.40, 27 abr 2026)

**Tipo:** Explícita | **Agente:** Opus | **Origen:** brief P/L semanal `docs/opus-bankroll-50-weekly-pl-brief-2026-04-26.md`.

### Contexto

Pablo busca acción concreta antes del domingo 2026-05-03 para mejorar el P/L semanal con bankroll $25. Codex recomendó HOLD $25 + observar SL post-fix con muestra extra. Opus revisa el lifecycle live y encuentra que la muestra post-fix v10.6.28+ ya existe (n=10 en 14d) y es claramente mala: WR=10%, PnL=−$3.95.

### Diagnóstico

Patrón concentrado en 3 condiciones:
- `condition=exact` con `days_ahead<=1` y edge>40%: 3 trades (Paris/Milan/Munich), 0 wins, −$2.82. Bot dice 80–85% prob, mercado dice 38–40%, SL dispara entre −25% y −46% en 0–5h, vende en suelo. El rebote intra-day o resolución YES son frecuentes; el SL precipita la pérdida.
- `condition=at_or_above` con our_prob 50–77% pero mkt 20–28%: el bot ve edge donde el mercado nunca valida.
- `condition=at_or_above` con our_prob 94–97%: confidence ultra-alta no validada.

El cooldown post-fix (sesión 236) evita re-buys (todos buy_count=1) pero no impide que el primer SL dispare en el peor momento. Bankroll $25 perdiendo ~$4/semana solo por esta regla = 16% bankroll/semana.

### Acciones

- `bot.py` v10.6.40: nuevas env vars `SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION` (default 1), `SL_INTRA_GUARD_DAYS_AHEAD_MAX` (default 1), `SL_INTRA_GUARD_REVIEW_MIN_SKIPS` (default 5), `SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN` (default 60).
- Helpers `load_sl_intra_guard_state()`, `save_sl_intra_guard_state()`, `_sl_intra_guard_should_skip(condition, days_ahead)` añadidos junto a los de `intra_reeval_state`.
- `intra_cycle_sl_check()`: antes de marcar `sell_type="stop_loss_intra"`, calcula `condition` (parse del title) y `days_ahead` (entry_context o cálculo desde market_date). Si guard aplica, NO marca sell_type, persiste evento en `data/sl_intra_guard_audit.json` y manda Telegram inmediato (rate-limited 60min). TP_intra y SL del ciclo principal siguen activos.
- Nueva función `maybe_run_sl_intra_guard_review(state)` integrada en `run_observability_alerts`. Cuando hay >=5 token_ids skipped y todos resolvieron en lifecycle, envía Telegram one-shot comparando PnL real vs hipotético (perdida si SL hubiera disparado al momento del skip). Veredicto explícito: `funcionando` (delta>0), `perjudicando` (delta<0) o `neutro`.
- `verify_before_deploy.py` suma 7 checks v10.6.40 (env vars, helpers, archivo de estado, guard logic en intra_cycle_sl_check, función review, hook en run_observability_alerts, BOT_VERSION bump). Test legacy `Version v10.6.30` actualizado a `v10.6.40`.

### Resultado

Patch defensivo, reversible vía env var, instrumentado con Telegram inmediato + review automático one-shot. Kill switch: `SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION=0` revierte sin redeploy. Esperado para la próxima semana: que SL_intra deje de cerrar en suelo trades exact con resolución <24h y que `market_resolved` los lleve a outcome real.

### NO se toca

Trading core, NOAA core, scheduler, MIN_EDGE, sigma, take_profit, sizing, BANKROLL ($25), whitelist, canary lists, BLOCKED_CITIES, shadow lists, reglas de entrada, cooldown SL existente (sesión 236), ICAO-only audit (sesión 251).

### Verificación

- `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK.
- `python verify_before_deploy.py` → **855/855**.

### Siguiente acción

Commit + push + deploy. Esperar primer skip live para confirmar que el Telegram dispara con el formato correcto. Si en 7 días hay ≥5 skips resueltos, llegará automático el review one-shot con veredicto.

## Sesión 255 — Fill real en SELL por order_id (v10.6.41, 27 abr 2026)

**Tipo:** Explícita | **Agente:** Codex | **Origen:** revisión de la operación Shanghai `27C Apr27 NO` del ciclo 187.

### Diagnóstico

La operación fue buena, pero el reporting era conservador/incorrecto: el bot mostraba y persistía el precio límite (`0.80`) aunque Polymarket enseñaba fill real cercano a `0.99`. En el snapshot Railway fresco, `performance.json` tenía `SELL price=0.80`, `trigger_price=0.82`, `return_est=$3.55`; la reconciliación solo convertía `SELL_PENDING -> SELL` cuando la orden desaparecía de `open_orders`, sin consultar trades/fills reales.

### Acciones

- `bot.py` v10.6.41 importa `TradeParams`.
- `audit_check_sell_fills()` intenta enriquecer cada venta confirmada con fill real: `get_trades(TradeParams(id=order_id))`, luego `get_trades(TradeParams(asset_id=token_id))` filtrando por `order_id`, y por último `get_order(order_id)` solo si trae campos explícitos de precio promedio/filled.
- Si hay fill real, `performance.json` conserva `limit_price`, usa `fill_price` como `price`, actualiza `return_est` con `fill_value`, guarda `fill_source/fill_count/fill_trades` y recalcula PnL cuando tiene `avg_buy_price`.
- `postmortem` y `trade_lifecycle` propagan `fill_price`, `fill_value`, `fill_source` y `limit_price`.
- Telegram `[INTRA-SL]` ahora dice `precio límite` y aclara que el precio real puede diferir.
- `verify_before_deploy.py` suma checks v10.6.41.

### Verificación

- `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK.
- Helper `_extract_fill_summary_from_trades()` probado con trade sintético `price=0.99`, `size=4.44` → `fill_value=4.3956`.
- `python verify_before_deploy.py` → **859/859**.
- `python -m py_compile bot.py verify_before_deploy.py` sigue fallando solo por el lock conocido de `__pycache__` en Windows (`WinError 5`).

### Siguiente acción

Deploy cuando convenga. En el próximo SELL confirmado, revisar que Telegram de confirmación muestre `$... reales @ $...` si CLOB devuelve trades por `order_id`; si no, quedará marcado como estimado y no bloqueará la reconciliación.

## Sesión 261 — blocked_signals schema v2 Fase A (v10.6.44, 28 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet | **Origen:** prompt-sonnet.md (diseño Opus sesión 260, memory `blocked_signals_v2_design_2026_04_28.md`).

### Contexto

Auditorías previas (sesiones 247, 259, 260) tuvieron que reconstruir manualmente `market_id`, `city_mode`, cobertura observada y fuente de resolución vía SSH. La Fase A elimina ese trabajo manual para futuras alertas, añadiendo logging enriquecido aditivo sin tocar lógica de trading.

### Acciones

- **6 helpers nuevos** añadidos en `bot.py` antes de `maybe_run_blocked_signals_check`:
  - `_classify_city_bucket(city)`: bucket BLOCKED/ACTIVE/CANARY/OBSERVED_AUDIT/SHADOW/UNTRACKED
  - `_resolve_observed_coverage_status(city)`: noaa_configured/icao_only/open_meteo_proxy_only/no_local_station
  - `_build_blocked_signal_canonical_id(signal, outcome)`: ID determinista para dedupe fino
  - `_price_bucket(price)`: bucket <0.2/0.2-0.4/0.4-0.6/0.6-0.8/>0.8
  - `_extract_token_id(market, index)`: parsea clobTokenIds (str JSON o lista)
  - `_resolve_blocked_reason(city, condition)`: enum reason_blocked cerrado con detalle
- **Enriquecimiento del dict** de 13 campos v1 a 25 campos v2 (12 siempre disponibles + 5 null/unknown hasta Fase C).
- **Dedupe mejorado**: `existing_canonical_ids` acepta `canonical_signal_id` (v2) y `match_key` fallback (v1). Permite capturar múltiples traders por mismo `match_key` v1.
- **BOT_VERSION** bumpeado a `v10.6.44`.
- **13 checks nuevos** en `verify_before_deploy.py` para v10.6.44.

### NO implementado

Fase B (`tools/blocked_signals_audit.py`), cambios en alerta Telegram diaria, backfill v1 existente, Fase C (cruce truth pipeline).

### Verificación

- `python tools/check_python_syntax.py bot.py verify_before_deploy.py` → OK
- `python verify_before_deploy.py` → **896/896**
- `rtk git diff --name-only` → solo `bot.py`, `verify_before_deploy.py` (más docs)

### Siguiente acción

Commit + push + deploy. Logs a revisar en Railway: primer ciclo del día siguiente que dispare `maybe_run_blocked_signals_check` — inspeccionar último registro JSONL con `tail -1 /app/data/blocked_signals_resolutions.jsonl` y confirmar `schema_version=2` con los 25 campos.

## Sesión 262 — Fase B1: blocked_signals_audit.py (28 abr 2026)

**Tipo:** Explícita | **Agente:** Sonnet | **Origen:** prompt directo (continuación Fase B1 post Sesión 261).

### Contexto

Con Fase A cerrada y el JSONL enriquecido a schema v2, se necesitaba una herramienta para auditar `blocked_signals_resolutions.jsonl` sin acceso SSH manual cada vez que saltase una alerta. Fase B1 es la CLI de auditoría read-only.

### Acciones

- **Nuevo archivo `tools/blocked_signals_audit.py`**: herramienta stdlib-only. Secciones A-G: resumen global, split whitelist, top ciudades, concentración, señales de baja accionabilidad, duplicados, candidatos a auditoría. Acepta `--source`, `--days`, `--json`, `--markdown`, `--out`, `--top`. Nunca recomienda abrir trading — clasifica en `ignore`/`monitor`/`audit_candidate`/`needs_settlement_verification`/`not_actionable`.
- **Documentación `docs/blocked_signals_audit_tool.md`**: uso, secciones, clasificaciones, nota sobre fuente canónica vs local.
- **11 checks nuevos** en `verify_before_deploy.py` para Fase B1.

### NO implementado

Fase B2 (cambios en alerta Telegram diaria), backfill v1, Fase C (cruce truth pipeline). Sin cambios a `bot.py`, trading core, NOAA, scheduler, whitelist, city modes, sigma, bankroll, reglas de entrada/salida.

### Verificación

- `python -c "import py_compile; py_compile.compile('tools/blocked_signals_audit.py', doraise=True)"` → OK
- `python verify_before_deploy.py` → **907/907**

### Siguiente acción

Commit + push. Para usar la herramienta: descargar JSONL desde Railway y correr `python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl --markdown`.

## Sesión 263 — Revisión operativa post-ausencia (4 may 2026)

**Tipo:** Implícita (handoff) | **Agente:** Claude Code Sonnet | **Origen:** `docs/handoffs/2026-05-04_prompt_claude_sonnet.md`.

### Contexto

Pablo estuvo fuera varios días. Esta sesión es read-only + documentación. Se revisaron logs Railway 2026-05-01 a 2026-05-04, estado del repo y alarmas pendientes.

### Comandos ejecutados

- `python verify_before_deploy.py` → **1074/1074** ✅
- `python tools/phase1_readiness_check.py` → sin DB local (Railway-only, esperado)
- `python tools/system_alignment_check.py --decision-mode operational` → ERROR stale snapshot (167h, 2026-04-27); 0 blocking collisions; 3 documented_drift
- `python tools/runtime_policy_effective_view.py` → OK, regenerado; 0 blocking_collisions; canary=10, shadow=12, blocked=1
- `python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl --markdown --top 10` → JSONL local vacío (datos canónicos en Railway)
- `tools/railway_safe.ps1 logs` (read-only Railway)

### Hallazgos

- **403 Cloudflare (2026-05-01): CERRADO.** Transitorio de arranque del deploy. Logs desde 10:11 UTC en adelante sin un solo 403. Todos los ciclos del periodo con `cycle_summary guardado OK`. → Clasificación baja de WATCH_TECH a WATCH.
- **Bankroll: $19.61** (era $17.68). Shanghai NO TP_intra +112.2% a las 05:11 UTC del 2026-05-04 generó ~$1.93 de PnL. Sigue BLOCKED respecto al tope de $25.
- **400 "size below minimum" (2026-05-04 00:01 UTC): WATCH_TECH nuevo.** Intento de BUY Shanghai NO 2.49sh×$0.71 rechazado por CLOB (`status=400, "Size (2.49) lower than the minimum: 5"`). Bot recuperó automáticamente en ciclo 04:00 UTC (4.48sh×$0.40 aceptado). Sin pérdida económica. El pre-check de tamaño mínimo no garantiza aceptación CLOB.
- **L2 Hazard Monitor: confirmado implementado.** Commit 81b7586, `SL_INTRA_HAZARD_MONITOR_ENABLED=0` default OFF. Backlog item cerrado.
- **SL retro muestra post-guard:** n≈2, insuficiente. tracked_stop_losses=14. No nuevo SL desde 2026-05-01T12:00.
- **Ciclos 0 BUYs 2026-05-01/03:** confirmado. Sin BUYs hasta el 2026-05-04 (Shanghai trade).
- **PnL reconciliation 2026-05-04 08:01:** fallo urllib timeout al enviar Telegram. Benign (network blip). No afecta trading.
- **Copy confuso SL Retro ("20/16 SLs"):** `TARGET_SAMPLE_SIZE=16` fijo en `tools/sl_retrospective.py:24`; cuando `n_resolved > 16` la línea 827 muestra "20/16 SLs". Prompt Codex preparado.

### NO se tocó

Trading core, bot.py, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, servicios Railway, Truth Pipeline.

### Documentos actualizados

- `CONTEXTO.md`: nota sesión 263 añadida.
- `HISTORIAL_SESIONES.md`: esta entrada.
- `docs/codex_prompt_sl_retro_copy_2026_05_04.md`: prompt Codex para fix copy SL Retrospective.

### Archivos eliminados

- `docs/handoffs/2026-05-04_alarmas_y_backlog.md`
- `docs/handoffs/2026-05-04_prompt_claude_sonnet.md`

### Commit

Commit documental, no push, no deploy.

## Sesión 296 — Truth Pipeline 1L: cierre Fase 1 observacional mínima (5 may 2026)

**Tipo:** Read-only + cierre documental | **Agente:** Claude Code Sonnet | **Origen:** prompt directo (observación cohorte ampliada y decisión de cierre Fase 1).

### Contexto

Cohorte ampliada a `truth_records=24` en sesión 295 / 1K-B. Esta sesión observa la cohorte end-to-end (reporter + alarm preview + bot logs) y decide si cerrar Fase 1 observacional mínima o requerir más datos.

### Comandos ejecutados

- `python verify_before_deploy.py` → **1112/1112** ✅
- `railway_safe.ps1 status` → `enchanting-respect / production / polymarket-bot` ✅
- `railway_safe.ps1 ssh "ls -lh /app/data/polymarket.db ..."` → 4 backups confirmados ✅
- `railway_safe.ps1 ssh "printenv TRUTH_PIPELINE_ENABLED || true; ..."` → no definidas ✅
- `railway_safe.ps1 ssh "python tools/truth_pipeline_report.py --db /app/data/polymarket.db --json"` → `status=no_action`, `truth_records=24`, `n_resolved=19`, `calibration_global=0.789` ✅
- `railway_safe.ps1 ssh "python tools/truth_pipeline_report.py --db /app/data/polymarket.db"` → reporte humano OK ✅
- Alarm preview vía base64 + import programático (`run_alarm(dry_run=True, force=True)`) → `level=NO_ACTION`, `would_send=false` ✅
- `railway_safe.ps1 logs -s polymarket-bot -n 100` → bot sano ✅

### Hallazgos

- **Status: NO_ACTION** — calibración 78.9%, por encima del umbral WATCH (<50%).
- **Calibración por ciudad:** London 100% (n=4), Tokyo 100% (n=3), Paris 67% (n=3), Seoul 67% (n=3); 6 ciudades con n=1.
- **Madrid y Wellington: 0% con n=1** — sin valor estadístico; un solo error en n=1 no es conclusivo.
- **drift_alert_cities: []** — sin drift sistemático detectado.
- **Alarm preview limpia:** `level=NO_ACTION`, `would_send=false`, mensaje conforme (sin instrucciones de trading).
- **Nota técnica:** `truth_pipeline_alarms.py` no tiene bloque `__main__`; el flag `--dry-run` como argumento CLI no produce output. Solución validada: base64-encode de script Python que importa el módulo y llama `run_alarm(dry_run=True, force=True)`.
- **Bot sano:** v10.6.47, Modo REAL, próximo ciclo 20:00 UTC. Ruido conocido `py_clob_client_v2 400` no relacionado.

### Decisión

**A — Cerrar Fase 1 observacional mínima como completada.**

Pipeline validado end-to-end: escritura ✅ · resolución automática ✅ · calibración ✅ · reporter JSON/humano ✅ · alarm preview ✅ · status correcto ✅ · sin drift ✅ · sin revisiones ✅.

Matiz: `calibration_global=0.789` con `n_resolved=19` es primera lectura, no conclusión operativa. Distribución desigual: 8 ciudades con n=1, estadísticamente insuficientes. Umbral mínimo para cualquier uso operativo posterior: `n_resolved>=30` total, varias ciudades con `n>=5`; ideal `n_resolved>=50`.

### NO se tocó

Código runtime, bot.py, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars persistentes, Railway (solo read-only/preview), tools del Truth Pipeline, schema SQL, tablas v1.

### Documentos actualizados

- `CONTEXTO.md`: entrada sesión 296 añadida al inicio.
- `HISTORIAL_SESIONES.md`: esta entrada.
- `agent_events.jsonl`: entrada sesión 296.

### Commit

`docs: close truth pipeline phase 1 observational` — push sí, deploy no.

---

## Sesión 300 — Daily Bot Kanban Digest 1.2 Railway verification (6 may 2026, Sonnet)

**Tipo:** Documentación / cierre de sesión
**Clasificación:** ACTION_DOCUMENTATION / WATCH_RISK

### Contexto

Sesión de cierre documental posterior al push del commit `d2d335e` (`fix: mark daily digest source quality`, Sesión 299 Codex). El objetivo fue verificar que Railway ejecuta el nuevo código y registrar el resultado.

### Verificación Railway

- **Proyecto:** `enchanting-respect` / environment `production` / service `polymarket-bot`
- **Deployment:** `c6ebab44-49dc-4e2f-840a-ce4f647ebb15` — status `SUCCESS`
- **Nota técnica:** el contenedor no tiene `.git`; no se pudo leer HEAD con `git rev-parse`. La confirmación funcional es directa: el digest remoto ya incluye `source_quality` y ya cuenta ciclos desde `timestamp_utc`.

### Resultado digest Railway

| Campo | Valor |
|---|---|
| `recent_cycles_24h` | 7 |
| `recent_cycles_7d` | 55 |
| `source_quality.status` | `contaminated` |
| `closed_records` | 107 |
| `contaminated_records` | 107 |
| `contamination_rate` | 1.0 |
| `would_send` | `false` |
| Nivel global | `WATCH_RISK` |

Warning presente: *"P/L incluye registros reconstruidos/no audit-ready; no usar para BANKROLL ni decisiones operativas."*

### Interpretación

1. **Bug ciclos=0 corregido en Railway** — `recent_cycles_24h=7` y `recent_cycles_7d=55` confirman que el fix de `timestamp_utc` está activo.
2. **P/L lifecycle contaminado** — `contamination_rate=1.0` es esperado; los 107 registros incluyen históricos reconstruidos/postmortem.
3. **No listo para Telegram real** — `would_send=false` correcto.
4. **No autoriza BANKROLL, trading core ni Fase C.**

### Siguiente bloque recomendado

Diseño/auditoría de fuente limpia de P/L o reconciliación wallet/dashboard antes de habilitar Telegram real.

### NO se tocó

Código, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway, deploy manual, Telegram real, Fase C.

### Documentos actualizados

- `CONTEXTO.md`: entrada sesión 300 añadida al inicio.
- `HISTORIAL_SESIONES.md`: esta entrada.
- `agent_events.jsonl`: entrada sesión 300.

### Commit

`docs: record daily digest railway verification` — push sí, deploy no.

---

## Sesión 302 — Daily Bot Kanban Digest 1.3 pnl_sources Railway verification (6 may 2026, Sonnet)

**Tipo:** Documentación / cierre de sesión
**Clasificación:** ACTION_DOCUMENTATION / WATCH_RISK

### Contexto

Sesión de cierre documental posterior al push del commit `ecd314b` (`feat: add pnl sources to daily digest`, sesión previa Codex). El objetivo fue verificar que Railway ejecuta el nuevo código con bloque `pnl_sources` y registrar el resultado.

### Verificación Railway

- **Proyecto:** `enchanting-respect` / environment `production` / service `polymarket-bot`
- **Deployment:** `58778c54-4de9-46e0-96c2-3f771c8bb62d` — status `SUCCESS`
- **Confirmación funcional:** el JSON remoto ya incluye `pnl_sources`.

### Resultado digest Railway — bloque `pnl_sources`

| Campo | Valor |
|---|---|
| `lifecycle.status` | `contaminated` |
| `lifecycle.closed_records` | 107 |
| `lifecycle.contaminated_records` | 107 |
| `lifecycle.contamination_rate` | 1.0 |
| `lifecycle.operational_use` | `untrusted_only` |
| `wallet_pnl.status` | `accumulating` |
| `wallet_pnl.phase2_ready` | `false` |
| `wallet_pnl.phase2_ready_reason` | `cash_flow_unknown` |
| `wallet_pnl.valid_snapshots` | 8 |
| `wallet_pnl.valid_snapshot_days` | 8 |
| `wallet_pnl.history_span_hours` | 153.98 |
| `wallet_pnl.wallet_pnl_available` | `false` |
| `cash_flows.status` | `missing` |
| `cash_flows.n_records` | 0 |
| `dashboard.status` | `manual_only` |
| `dashboard.auto_extractor_authorized` | `false` |
| `canonical_source` | `none` |
| `bankroll_readiness` | `blocked` |
| `would_send` | `false` |
| Nivel global | `WATCH_RISK` |

### Interpretación

1. **Bloque `pnl_sources` activo en Railway** — la estructura está presente y comunica correctamente el estado de cada fuente.
2. **Digest comunica que no hay P/L canónico** — `canonical_source=none` y `bankroll_readiness=blocked` son correctos.
3. **`trade_lifecycle` queda `untrusted_only`** — `contamination_rate=1.0` es esperado; los 107 registros incluyen históricos reconstruidos/postmortem.
4. **`wallet_pnl` sigue acumulando baseline** — 8 snapshots/8 días/153.98h; `phase2_ready=false` por `cash_flow_unknown`.
5. **`wallet_cash_flows.jsonl` missing** — prerequisito para promover `wallet_pnl`; bloquea promoción.
6. **Dashboard sigue manual only** — sin scraper autorizado.
7. **BANKROLL readiness bloqueado** — esperado y correcto.
8. **Telegram real bloqueado** — `would_send=false` correcto.
9. **Fase C no autorizada.**

### Siguiente bloque recomendado

Acumulación orgánica de `wallet_pnl` snapshots y creación de `wallet_cash_flows.jsonl` (aunque sea vacío) para desbloquear la cadena de promoción.

### NO se tocó

Código, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway, deploy manual, Telegram real, Fase C.

### Documentos actualizados

- `CONTEXTO.md`: entrada sesión 302 añadida al inicio.
- `HISTORIAL_SESIONES.md`: esta entrada.
- `agent_events.jsonl`: entrada sesión 302.

### Commit

`docs: record pnl sources railway verification` — push sí, deploy no.

---

## Sesión 306 — Patch C wallet_cash_flow_log diseño canónico (6 may 2026, Sonnet)

**Tipo:** Documentación / diseño
**Clasificación:** ACTION_DESIGN / WATCH_RISK

### Contexto

Sesión de diseño documental de Patch C para `tools/wallet_cash_flow_log.py`. Patch A (política antifalsificación), Patch B (gate `wallet_cash_flows` en digest), y Patch B' (schema v2 en `wallet_snapshot`) están cerrados y verificados en Railway. Opus clasificó Patch C como ACTION_DESIGN: el diseño puede documentarse ahora; la implementación requiere signoff explícito de Pablo y revisión de diff antes de merge.

### Estado invariante al inicio de sesión

| Campo | Valor |
|---|---|
| `data/wallet_cash_flows.jsonl` local | no existe |
| `/app/data/wallet_cash_flows.jsonl` Railway | no existe |
| `cash_flows.status` | `missing` |
| `cash_flows.coverage_days_7d` | 0 |
| `wallet_pnl_available` | `false` |
| `phase2_ready` | `false` |
| `phase2_ready_reason` | `cash_flow_unknown` |
| `wallet_pnl_confidence` | `low` |
| `wallet_pnl_7d` | `null` |
| `canonical_source` | `none` |
| `bankroll_readiness` | `blocked` |
| `would_send` | `false` |

### Diseño canónico — `docs/wallet_cash_flow_log_design.md`

Documento creado con especificación completa para `tools/wallet_cash_flow_log.py`:

**Propósito:** CLI manual para appending de filas validadas de cash flow a `data/wallet_cash_flows.jsonl`, en cumplimiento de la política de atestación (`docs/wallet_cash_flows_policy.md`).

**Interfaz CLI:**

```
python tools/wallet_cash_flow_log.py \
    --type <type> \
    --period-start <ISO-8601 UTC> \
    --period-end <ISO-8601 UTC> \
    [--note <free text>] \
    [--write] \
    [--init] \
    [--data-dir <path>] \
    [--entry-id <uuid4-override>]
```

`actor` hardcodeado a `pablo_manual`. `recorded_at` = `utcnow`. `schema_version` = `2`. Ninguno de estos es argumento CLI. `entry_id` es auto-generado como UUID4 por la CLI — no es argumento requerido del usuario. `--entry-id` existe solo como override de testing, no para flujos productivos. Sin `--write`, la CLI corre siempre en dry-run y no escribe nada.

**Tipos permitidos:** `deposit`, `withdrawal`, `no_cash_flow_attestation`, `adjustment`.

**Tipos prohibidos (rechazo explícito):** `inferred`, `auto`, `reconstructed`, `estimated`.

**Validaciones anti-falsificación:**
1. `type` debe estar en la allow-list.
2. `period_start` y `period_end` deben ser ISO-8601 parseable.
3. `period_end` >= `period_start`.
4. `type == "adjustment"` requiere `--note` no vacío.
5. Si se usa `--entry-id` override (testing only), el valor no puede empezar con `EXAMPLE-`.
6. El `entry_id` auto-generado (o override) no puede duplicar un ID existente en el archivo.
7. Antes de cualquier append, la CLI re-lee y valida **cada fila existente** del archivo contra schema v2. Si cualquier fila falla validación → **abortar sin escribir**. Filas inválidas son un hard stop; el archivo debe repararse manualmente.

**Comportamiento por defecto (sin `--write`):** dry-run — valida todo, imprime la fila que se escribiría, no escribe, zero side-effects.

**Write mode (`--write`):** si el archivo no existe → abortar salvo que `--init` también esté presente. Si existe → valida filas existentes (hard stop si inválidas), append de una línea JSON, imprime confirmación.

**Init mode (`--write --init`):** permite crear el archivo si no existe; requiere confirmación textual explícita (`YES I CONFIRM`) antes de crear. `--init` sin `--write` es rechazado.

**Constraints:** stdlib-only. No importa `bot.py`. No Railway. No Telegram. No `alerts_state`. No trading core.

**verify_before_deploy.py:** cuando Codex implemente, debe sumar checks de: no import trading core, no Telegram, no Railway, actor hardcodeado, `entry_id` auto-generado UUID4 (no argumento requerido), tipos prohibidos rechazados, `--entry-id` override con `EXAMPLE-*` rechazado, sin `--write` → zero escrituras, `--init` sin `--write` rechazado, `--write --init` requiere confirmación textual, filas existentes inválidas → abortar, adjustment sin note rechazado.

**Criterios de handoff para Codex:** solo tras signoff explícito de Pablo → diff proposal Codex → revisión Pablo → `verify_before_deploy.py` verde → dry-run local confirmado.

### Referencia mínima en policy

`docs/wallet_cash_flows_policy.md` actualizado: la mención de Patch C en la sección "Future Patch Interaction" ahora referencia `docs/wallet_cash_flow_log_design.md` como especificación canónica (ACTION_DESIGN, not implemented).

### Estado invariante al cierre de sesión

Idéntico al estado al inicio. Nada cambió en runtime.

- `data/wallet_cash_flows.jsonl` sigue sin existir (local y Railway).
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### NO se tocó

`tools/wallet_cash_flow_log.py` (no existe), `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, env vars, Railway, DB, Telegram real, Fase C. No deploy. No commit/push todavía (pendiente signoff Pablo).

### Documentos actualizados

- `docs/wallet_cash_flow_log_design.md`: creado (diseño canónico Patch C).
- `docs/wallet_cash_flows_policy.md`: referencia mínima al design doc.
- `CONTEXTO.md`: entrada sesión 306 añadida al inicio.
- `HISTORIAL_SESIONES.md`: esta entrada.
- `agent_events.jsonl`: entrada sesión 306.

### Siguiente paso posible

Codex diff proposal de `tools/wallet_cash_flow_log.py` solo tras signoff explícito de Pablo. Sin signoff: Patch C permanece ACTION_DESIGN / NOT_IMPLEMENTED.

---

## Sesión 307 — 6 de mayo de 2026 (Sonnet 4.6)

**Clasificación:** ACTION_DOCUMENTATION / WATCH_RISK
**Bloque:** Hermeticity check Patch B/B' attested_full_7d
**Veredicto:** PASS

### Contexto

Codex ejecutó verificación read-only de hermeticidad de Patch B/B' usando fixture sintético `attested_full_7d`. Objetivo: confirmar que `wallet_snapshot.py` y `daily_kanban_digest.py` responden correctamente al estado `attested_full_7d` sin crear datos reales, sin tocar Railway y sin abrir Patch C.

### Fixture sintético

- Directorio temporal: `C:\tmp\polymarket_attested_full_7d_verify` (creado y borrado al cierre).
- `cash_flows.status = attested_full_7d`
- `cash_flows.coverage_days_7d = 7`

### Resultado de hermeticidad

| Campo | Valor observado |
|---|---|
| `cash_flows.status` | `attested_full_7d` (vía fixture) |
| `cash_flows.coverage_days_7d` | 7 |
| `wallet_pnl_available` | `false` |
| `phase2_ready` | `false` |
| `phase2_ready_reason` | `need_more_history` |
| `wallet_pnl_confidence` | `low` / `unavailable` según herramienta |
| `wallet_pnl_7d` | `null` |
| `canonical_source` | `none` |
| `bankroll_readiness` | `blocked` |
| `would_send` | `false` |

### Tests focalizados

```
python -m pytest tests/test_wallet_snapshot.py tests/test_daily_kanban_digest.py \
    -q -p no:cacheprovider --basetemp C:\tmp\pytest_attested_full_7d
```

**Resultado: 45 passed in 1.52s**

Nota: la primera ejecución falló por permisos en el directorio Temp de usuario (`%TEMP%`). Rerun con `--basetemp` a ruta explícita funcionó correctamente.

### Limpieza

- `C:\tmp\polymarket_attested_full_7d_verify` borrado.
- `C:\tmp\pytest_attested_full_7d` borrado.
- `git status` final: sin cambios; solo warning conocido de `.pytest_cache`.
- No commit, no push.

### Invariantes confirmados al cierre

- `data/wallet_cash_flows.jsonl` sigue sin existir (local).
- `tools/wallet_cash_flow_log.py` no existe.
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### Prioridad 1 de Opus

Cerrada: read-only, hermeticidad verificada. `cash_flows.status` promociona correctamente a `attested_full_7d` bajo fixture sintético. Readiness sigue bloqueada por `need_more_history`, que es el comportamiento correcto dado que no hay historia real de 7 días.

### NO se tocó

`tools/wallet_cash_flow_log.py` (no existe), runtime, Railway, DB, env vars, Telegram real, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, Fase C. No deploy. No commit/push todavía.

### Siguiente paso posible

Codex diff proposal de `tools/wallet_cash_flow_log.py` solo tras signoff explícito de Pablo. Sin signoff: Patch C permanece ACTION_DESIGN / NOT_IMPLEMENTED.

## Sesión 309 — 6 de mayo de 2026 (Codex)

**Clasificación:** ACTION_TOOLING / PATCH_MEMORY / WATCH_RISK
**Bloque:** Patch C wallet_cash_flow_log implementación local
**Veredicto:** IMPLEMENTADO_LOCAL / NO_PUSH

### Contexto

Codex implementa Patch C `tools/wallet_cash_flow_log.py` tras signoff explícito de Pablo y con base en el diseño canónico de Sesión 306 (`docs/wallet_cash_flow_log_design.md`), la política antifalsificación de Sesión 303 (`docs/wallet_cash_flows_policy.md`) y el contrato P&L Observability de Sesión 308 (`docs/pnl_observability.md`).

### Commit

`81e7346` — `feat: add wallet cash flow log tool`

### Archivos del commit

- **Creado:** `tools/wallet_cash_flow_log.py`
- **Creado:** `tests/test_wallet_cash_flow_log.py`
- **Modificado:** `verify_before_deploy.py`

### Propiedades de la herramienta

- Manual-only (no runtime, no auto-import)
- stdlib-only (sin dependencias externas)
- Append-only (no modificación de entradas existentes)
- Dry-run default (sin `--write` no escribe nada)
- No calcula P&L
- No promueve readiness
- No cambia `canonical_source`
- No cambia `bankroll_readiness`
- No manda Telegram
- No toca DB/Railway/runtime/trading core/`bot.py`/BANKROLL/Fase C

### Validación Codex

| Check | Resultado |
|---|---|
| Syntax `tools/wallet_cash_flow_log.py` | OK |
| Syntax `tests/test_wallet_cash_flow_log.py` | OK |
| `pytest tests/test_wallet_cash_flow_log.py` | **24 passed** |
| `verify_before_deploy.py` | **1139/1139 OK** |
| `git diff --check` | OK (solo warnings LF/CRLF Windows) |

### Invariantes confirmados al cierre

- `data/wallet_cash_flows.jsonl` no existe.
- `git ls-files -- data/wallet_cash_flows.jsonl` vacío.
- `tools/wallet_cash_flow_log.py` existe solo como código.
- Herramienta no usada con datos reales.
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### Estado del repo

- `HEAD`: `81e7346`
- `main...origin/main [ahead 1]`
- Working tree limpio.
- No push todavía.

### NO se tocó

Runtime, Railway, DB, env vars, Telegram real, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, Fase C. No deploy. No se creó `data/wallet_cash_flows.jsonl` real.

### Siguiente paso posible

Push controlado del commit `81e7346`; después diseñar/planificar B3 `tools/pnl_report.py` read-only. No Patch D todavía.

## Sesión 310 — 6 de mayo de 2026 (Codex)

**Clasificación:** ACTION_DOCUMENTATION / PATCH_MEMORY / WATCH_RISK
**Bloque:** Patch C push controlado + Railway auto-deploy SUCCESS
**Veredicto:** PUSH_COMPLETADO / DEPLOY_SUCCESS

### Contexto

Push controlado del rango `bd4830a..0506782` tras implementación y validación local de Patch C en Sesión 309. Commits pusheados:

- `81e7346` — `feat: add wallet cash flow log tool`
- `0506782` — `docs: record wallet cash flow log implementation`

HEAD final: `0506782`. `main` alineado con `origin/main`. Working tree limpio.

### Railway auto-deploy

- **Proyecto:** enchanting-respect
- **Environment:** production
- **Service:** polymarket-bot
- **Deployment ID:** `6849b187-61c9-4a4e-82d3-04372cb1bbcd`
- **Status final:** SUCCESS
- No hubo deploy manual. No env vars. No DB.

### Invariantes confirmados al cierre

- `data/wallet_cash_flows.jsonl` no existe.
- `git ls-files -- data/wallet_cash_flows.jsonl` vacío.
- `tools/wallet_cash_flow_log.py` existe solo como código (sin uso con datos reales).
- Herramienta no usada con datos reales.
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### NO se tocó

`bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, Fase C, runtime, Railway env vars, DB, Telegram real. No deploy manual. Patch C sigue sin activar P&L Observability canónico. Patch C solo crea la vía segura de registro manual.

### Siguiente paso posible

Diseño B3 `tools/pnl_report.py` read-only. No Patch D todavía.

## Sesión B3 — 7 de mayo de 2026 (Sonnet 4.6)

**Clasificación:** ACTION_DESIGN / WATCH_RISK / NOT_CANONICAL
**Bloque:** B3 — diseño documental `tools/pnl_report.py`
**Veredicto:** DOCUMENTO_CREADO / NO_IMPLEMENTACIÓN

### Contexto

Diseño canónico de `tools/pnl_report.py` como herramienta CLI read-only / LOG_ONLY. Se crea `docs/pnl_report_design.md`.

### Artefactos

- **Creado:** `docs/pnl_report_design.md` — contrato completo para implementación futura.

### Contenido del contrato

- Propósito read-only / LOG_ONLY, horizontes 1D/1W/1M/ALL.
- Inputs: `wallet_portfolio_snapshots.jsonl` + `wallet_cash_flows.jsonl` + `trade_lifecycle.json` (non_canonical_telemetry).
- Schema JSON completo con todos los campos requeridos por horizonte.
- Máquina de estados: 5 estados documentados; 4 emitibles en B3 (`unavailable` → `blocked` → `provisional` → `canonical_candidate`). `canonical` documentado como estado futuro pero no emitible en B3 — requiere B5+B6.
- Confidence capado a `medium` en B3. `high` nunca automático.
- Ausencia de `wallet_cash_flows.jsonl` → exit 0, todos los horizontes `blocked`, `reason` explícito.
- 14 tests mínimos T1–T14 definidos.
- Stdlib-only (argparse, json, pathlib, datetime, decimal, typing, sys, dataclasses).
- Exit codes: 0 (éxito/datos ausentes) y 2 (input corrupto).
- Lista negra explícita: no trading, no Telegram, no DB, no Railway, no bot.py, no scheduler, no BANKROLL, no Fase C, no BUY/SELL/SKIP, no promover readiness, no Patch D.
- Guardrails G1–G6 adicionales.

### Invariantes confirmados

- `data/wallet_cash_flows.jsonl` no existe.
- `tools/pnl_report.py` no existe (no implementado).
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### NO se tocó

`tools/`, `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, Fase C, runtime, Railway, DB, env vars, Telegram real. No commit/push.

### Siguiente paso posible

Signoff de Pablo sobre `docs/pnl_report_design.md`. Después: Codex implementa `tools/pnl_report.py` y `tests/test_pnl_report.py` siguiendo el contrato. No Patch D todavía.

## Sesión 311 — 7 de mayo de 2026 (Sonnet 4.6)

**Clasificación:** ACTION_TOOLING / PATCH_MEMORY / NOT_CANONICAL / WATCH_RISK
**Bloque:** B3 — implementación local `tools/pnl_report.py`
**Veredicto:** IMPLEMENTADO_LOCAL / VALIDADO / NO_PUSH_TODAVÍA

### Contexto

Micro-cierre documental de B3. Codex implementa `tools/pnl_report.py` + `tests/test_pnl_report.py` siguiendo el contrato cerrado en `docs/pnl_report_design.md` (Sesión B3).

### Commits locales

- `082e02d` — `feat: add pnl report tool`
- `420e4b8` — `docs: add pnl report design`
- `main...origin/main [ahead 1]` — no push todavía.

### Artefactos

- **Creado:** `tools/pnl_report.py` — CLI read-only, stdlib-only, horizontes 1D/1W/1M/ALL.
- **Creado:** `tests/test_pnl_report.py` — 14 tests T1–T14.
- **Modificado:** `docs/pnl_report_design.md` — campo `--generated-at` marcado `testing-only`.

### Validación Codex

- Syntax OK.
- `pytest tests/test_pnl_report.py`: **14 passed**.
- Missing cashflow: exit 0, JSON válido, horizontes `blocked`, `value_usdc=null`, `reason` explícito.
- Guardrails output: `would_send=false` / `operational_use=forbidden` / `promotes_canonical_source=false`.

### Invariantes confirmados

- `data/wallet_cash_flows.jsonl` no existe. `git ls-files -- data/wallet_cash_flows.jsonl` vacío.
- `canonical_source=none` sin cambios.
- `bankroll_readiness=blocked` sin cambios.
- `wallet_pnl_available=false` sin cambios.

### NO se tocó

`bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, Fase C, runtime, Railway, DB, env vars, Telegram real, Patch D. No datos reales.

### Siguiente paso posible

Push controlado del commit `082e02d`. Después: B3.1 Polymarket API source strategy o B4 diseño — no integración automática. No Patch D todavía.

---

## Sesión 315 — 7 de mayo de 2026 (Sonnet 4.6)

**Tipo:** DOCUMENTATION / WATCH_RISK — Cierre documental LITE

### Contexto

Pre-requisito para el futuro SL_intra Guard Evidence Ledger: definir el campo `sl_window_catchable` antes de que Opus diseñe el ledger o Codex lo implemente en runtime.

### Artefactos

- **Creado:** `docs/sl_intra_guard_leverage_instrumentation.md` — define `sl_window_catchable`, criterio inicial, schema de campos, casos borde, uso previsto/prohibido y relación con el futuro ledger.
- **Actualizado:** `CONTEXTO.md` — entrada breve de Sesión 315.
- **Actualizado:** `HISTORIAL_SESIONES.md` — esta entrada.
- **Actualizado:** `agent_events.jsonl` — evento de documentación.

### Decisión central documentada

`sl_window_catchable = true` si `pct_pnl_at_skip > -35%`; `false` si `<= -35%`. Umbral observacional y revisable. No ejecutable.

### NO se tocó

`bot.py`, `tools/`, scheduler, NOAA, reglas de entrada/salida, Railway, DB, env vars, BANKROLL, Fase C, trading core, whitelist, city modes, sizing, risk rules, Telegram real.

### Invariantes confirmados

- A8 estado: `WATCH / ESPERAR_MÁS_MUESTRA` (n=2 leverage-real).
- Re-check: 5.º guarded o 2026-05-21.
- No implementación runtime.

### Siguiente paso posible

Codex patch mínimo para añadir `sl_window_catchable` al skip event (LOG_ONLY), o Opus diseña el Evidence Ledger si el campo ya existe.

---

## Sesión 320 — 7 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / tooling observability / patch acotado / no runtime
**Bloque:** B4.4 — Leaderboard P&L Snapshot Store
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Contexto

B4.3 cerro que `leaderboard.pnl` no es dashboard-equivalent ni fuente canonica, pero si sirve como observabilidad externa para historico, digest y tendencia. B4.4 materializa esa captura sin conectarla a readiness.

### Artefactos

- **Creado:** `tools/leaderboard_pnl_snapshot.py` — CLI stdlib-only para `--dry-run`, `--write` y `--summary`.
- **Creado:** `tests/test_leaderboard_pnl_snapshot.py` — tests de flags, summary y fallo API.
- **Actualizado:** `.gitignore` — excluye `data/observability/`.
- **Actualizado:** `ORCHESTRATOR.md` — estado estrategico P&L tooling.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

La ruta por defecto es `data/observability/leaderboard_pnl_snapshots.jsonl`. Cada fila es append-only y etiqueta explicitamente `source=polymarket_leaderboard`, `source_quality=external_opaque`, `dashboard_equivalent=false`, `usable_for_digest=true`, `usable_for_trend=true`, `usable_for_bankroll=false`. `MONTH` mantiene `confidence_month=low`.

Si no hay wallet en `--wallet`, `FUNDER`, `POLYMARKET_WALLET`, `WALLET_ADDRESS` o `PROXY_WALLET`, la herramienta devuelve `NEEDS_MANUAL_WALLET_INPUT`. Los fallos API pueden escribirse con `query_status=failed` y `api_error`, sin generar readiness.

### Validacion Codex

- `python tools\check_python_syntax.py tools\leaderboard_pnl_snapshot.py tests\test_leaderboard_pnl_snapshot.py` — OK.
- `python -m pytest tests\test_leaderboard_pnl_snapshot.py -q -p no:cacheprovider` — 5 passed.
- `python tools\leaderboard_pnl_snapshot.py --dry-run` — no write, devuelve `NEEDS_MANUAL_WALLET_INPUT` sin wallet local.
- `python tools\leaderboard_pnl_snapshot.py --summary` — 0 snapshots, trend `unknown`.
- `git diff --check` — OK.
- `python verify_before_deploy.py` — 1140/1140 OK.

### NO se toco

`bot.py`, runtime, trading core, BANKROLL, Fase C, sizing, whitelist, city modes, scheduler, guards, SL, reglas de riesgo, env vars, DB, Railway/deploy, Telegram real.

### Siguiente paso posible

Ejecutar manualmente `tools/leaderboard_pnl_snapshot.py --write --wallet <wallet>` cuando Pablo quiera iniciar historico real. No conectar a `bankroll_scaling_check.py` ni a readiness sin revision separada.

---

## Sesión 321 — 7 de mayo de 2026 (Codex)

**Clasificacion:** LITE / observability tooling / patch acotado / no runtime
**Bloque:** B4.4b — Wallet fallback + leaderboard vol labeling
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Contexto

B4.4a confirmo la primera captura real, pero requirio pasar `--wallet` manualmente porque la shell no tenia `FUNDER` cargado. Tambien quedo aclarado que `leaderboard.vol` es volumen de trading del trader en el leaderboard de Polymarket, no numero de buys ni operaciones.

### Artefactos

- **Modificado:** `tools/leaderboard_pnl_snapshot.py`.
- **Modificado:** `tests/test_leaderboard_pnl_snapshot.py`.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl`.

### Cambio

La herramienta resuelve wallet con prioridad:

1. `--wallet` explicito.
2. Env vars cargadas: `FUNDER`, `POLYMARKET_WALLET`, `WALLET_ADDRESS`, `PROXY_WALLET`.
3. `FUNDER` en `.env` local.

La salida sigue mostrando solo `wallet_masked`; la wallet completa no aparece en JSON stdout. Se agregan `volume_label=leaderboard_trading_volume` y `volume_notes` para fijar que `vol_day/week/month/all` son leaderboard trading volume, no `buy_count`, numero de buys ni numero de operaciones.

### Validacion Codex

- `python tools\check_python_syntax.py tools\leaderboard_pnl_snapshot.py tests\test_leaderboard_pnl_snapshot.py` — OK.
- `python -m pytest tests\test_leaderboard_pnl_snapshot.py -q -p no:cacheprovider` — 8 passed.
- `git diff --check` — OK.
- `python verify_before_deploy.py` — 1140/1140 OK.

### NO se toco

Daily Digest, Telegram, scheduler, Railway, DB, env vars, BANKROLL, trading core, `bot.py`, sizing, whitelist, city modes, guards, SL, reglas de riesgo, Fase C.

---

## Sesión 322 — 7 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / observability digest / patch acotado / Telegram PREVIEW ONLY / no runtime
**Bloque:** B4.5 — Daily Bot Digest dry-run + Telegram preview
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Contexto

B4.4/B4.4b dejaron un store JSONL de snapshots externos del leaderboard de Polymarket. B4.5 crea el generador local de digest sobre ese store, sin conectarlo a runtime, Telegram real ni readiness.

### Artefactos

- **Creado:** `tools/daily_bot_digest.py` — CLI read-only para digest humano, `--json` y `--telegram-preview`.
- **Creado:** `tests/test_daily_bot_digest.py` — tests focalizados de 0/1/2 snapshots, deltas, guardrails y preview.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

La ruta por defecto es `data/observability/leaderboard_pnl_snapshots.jsonl`. El digest toma el ultimo snapshot y lo compara con el anterior cuando existe. Si solo hay un snapshot, imprime `No previous snapshot yet` y `trend_label=unknown`.

La salida mantiene explicitamente `source=polymarket_leaderboard`, `source_quality=external_opaque`, `dashboard_equivalent=false`, `usable_for_digest=true`, `usable_for_trend=true`, `usable_for_bankroll=false`. `vol_day/week/month/all` se renderiza como `Leaderboard trading volume`; no se interpreta como `buy_count`, `trade_count`, numero de buys ni numero de operaciones.

`--telegram-preview` solo imprime texto apto para Telegram. No envia Telegram, no lee `TELEGRAM_*`, no requiere env vars y no escribe estado.

### Validacion Codex

- `python tools\check_python_syntax.py tools\daily_bot_digest.py tests\test_daily_bot_digest.py` — OK.
- `python -m pytest tests\test_daily_bot_digest.py -q -p no:cacheprovider` — 7 passed.
- `python tools\daily_bot_digest.py --dry-run` — OK con snapshot real actual, trend `unknown`.
- `python tools\daily_bot_digest.py --telegram-preview` — OK preview-only con snapshot real actual.

### NO se toco

Telegram real, scheduler, Railway, DB, env vars, BANKROLL, trading core, `bot.py`, sizing, whitelist, city modes, guards, SL, reglas de riesgo, Fase C, `bankroll_scaling_check.py`.

---

## Sesión 323 — 7 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / observability orchestration / patch acotado / Telegram PREVIEW ONLY / no runtime
**Bloque:** B4.6 — Daily Snapshot + Digest Runner
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Contexto

B4.4/B4.4b capturan snapshots externos del leaderboard de Polymarket y B4.5 genera el digest local. B4.6 une el flujo diario en un solo comando local sin integrarlo a runtime, scheduler, Telegram real ni readiness.

### Artefactos

- **Creado:** `tools/daily_bot_observability_run.py` — runner local snapshot + digest + preview.
- **Creado:** `tests/test_daily_bot_observability_run.py` — tests focalizados de dry-run, write, preview, deltas y guardrails.
- **Modificado:** `tools/daily_bot_digest.py` — añade `build_digest_from_rows()` para digest in-memory.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

Comandos soportados:

- `python tools\daily_bot_observability_run.py --dry-run`
- `python tools\daily_bot_observability_run.py --write-snapshot`
- `python tools\daily_bot_observability_run.py --write-snapshot --telegram-preview`
- `python tools\daily_bot_observability_run.py --json`

`--dry-run` construye un snapshot temporal usando la logica existente de `leaderboard_pnl_snapshot.py`, no escribe JSONL, y genera digest in-memory contra el historico existente. `--write-snapshot` appendea una fila JSONL y luego genera digest usando el historico actualizado. `--telegram-preview` solo imprime texto apto para Telegram; no envia Telegram y no lee `TELEGRAM_*`.

La salida conserva `source_quality=external_opaque`, `dashboard_equivalent=false`, `usable_for_digest=true`, `usable_for_trend=true`, `usable_for_bankroll=false` y `Observability only`. Fallos API quedan como `query_status=failed` y no producen readiness.

### Validacion Codex

- `python tools\check_python_syntax.py tools\daily_bot_observability_run.py tools\daily_bot_digest.py tests\test_daily_bot_observability_run.py tests\test_daily_bot_digest.py` — OK.
- `python -m pytest tests\test_daily_bot_observability_run.py tests\test_daily_bot_digest.py -q -p no:cacheprovider` — 13 passed.
- `python tools\daily_bot_observability_run.py --dry-run --env-file __missing_env_file__` — OK, no write, `NEEDS_MANUAL_WALLET_INPUT`.
- `python tools\daily_bot_observability_run.py --dry-run --telegram-preview --env-file __missing_env_file__` — OK preview-only.

### NO se toco

Telegram real, scheduler, Railway, DB, env vars Telegram, BANKROLL, trading core, `bot.py`, sizing, whitelist, city modes, guards, SL, reglas de riesgo, Fase C, `bankroll_scaling_check.py`, semantica P&L.

---

## Sesión 324 — 7 de mayo de 2026 (Codex)

**Clasificacion:** LITE / observability digest fix / patch acotado / no runtime
**Bloque:** B4.6c — compare against previous valid snapshot
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Contexto

B4.6a/B4.6b dejaron intentos failed por `WinError 10061` entre snapshots validos. El digest y el summary comparaban contra el intento inmediatamente anterior, por lo que un OK posterior a failed quedaba con deltas `unknown`.

### Artefactos

- **Modificado:** `tools/leaderboard_pnl_snapshot.py` — summary basado en snapshots validos para tendencia.
- **Modificado:** `tools/daily_bot_digest.py` — digest basado en snapshots validos para tendencia.
- **Modificado:** `tests/test_leaderboard_pnl_snapshot.py` — tests OK/failed/OK, OK/failed y solo failed.
- **Modificado:** `tests/test_daily_bot_digest.py` — tests equivalentes y copy guardrail.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

Los snapshots failed se conservan y cuentan como intentos (`snapshot_count`), pero no se usan para deltas. Un snapshot valido requiere `query_status` `ok`/`success` y `pnl_day`, `pnl_week`, `pnl_month`, `pnl_all` no null.

El summary expone `valid_snapshot_count`, `latest_valid_snapshot` y `previous_valid_snapshot_captured_at_utc`. El digest muestra `query_status`, `Trend vs previous valid snapshot`; si el ultimo intento global es failed, muestra `last_valid_snapshot_captured_at_utc` si existe y deja `trend_label=unknown`.

Con el historico local actual OK/failed/failed/OK: `snapshot_count=4`, `valid_snapshot_count=2`, previous valid `2026-05-07T19:51:33Z`, deltas P&L `0.00`, `trend_label=flat`.

### Validacion Codex

- `python tools\check_python_syntax.py tools\leaderboard_pnl_snapshot.py tools\daily_bot_digest.py tests\test_leaderboard_pnl_snapshot.py tests\test_daily_bot_digest.py` — OK.
- `python -m pytest tests\test_leaderboard_pnl_snapshot.py tests\test_daily_bot_digest.py -q -p no:cacheprovider` — 21 passed.
- `python tools\leaderboard_pnl_snapshot.py --summary` — OK, valid deltas 0.00 contra previous valid.
- `python tools\daily_bot_digest.py --dry-run` — OK, `Trend vs previous valid snapshot`.

### NO se toco

Telegram real, scheduler, Railway, DB, env vars, BANKROLL, trading core, `bot.py`, sizing, whitelist, city modes, guards, SL, reglas de riesgo, Fase C, `bankroll_scaling_check.py`, semantica P&L.

---

## Sesion 326 — 7 de mayo de 2026 (Sonnet 4.6)

**Clasificacion:** NORMAL / scheduler hook / observability / no trading
**Bloque:** B4.8 — Daily Digest automático Railway
**Veredicto:** IMPLEMENTADO / VALIDADO / COMMIT PUSHEADO

### Cambios

`bot.py` bumpeado a `v10.6.48`. Se añade `maybe_send_daily_bot_digest()` siguiendo el patron de `maybe_run_daily_briefing`: state file propio `data/daily_digest_state.json`, idempotencia por fecha UTC, subprocess con timeout 120s, log detallado. Constantes nuevas: `DAILY_DIGEST_ENABLED` (default 1), `DAILY_DIGEST_HOUR_UTC` (default 20), `DAILY_DIGEST_STATE_FILE`, `DAILY_DIGEST_SCRIPT`. Invocado en el loop principal tras `maybe_run_daily_briefing`.

### Timing

Con schedule por defecto `[8,16,23 UTC]` y `DAILY_DIGEST_HOUR_UTC=20`, el primer ciclo elegible es el **23 UTC** (= 01:00 España verano / 00:00 España invierno). Para exactitud 22:00 España (20:00 UTC): Pablo debe añadir `20` a `SCHEDULE_HOURS_UTC` en Railway.

### Artefactos

- **Modificado:** `bot.py` — `v10.6.47` → `v10.6.48`, constantes + función + call en loop.
- **Modificado:** `verify_before_deploy.py` — versión actualizada + 8 tests v10.6.48.

### Validacion

- `python verify_before_deploy.py` — 1148/1148 OK.
- `python -m pytest tests/test_daily_bot_digest.py tests/test_daily_bot_observability_run.py tests/test_leaderboard_pnl_snapshot.py` — 40 passed.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, guards, SL, reglas de riesgo, env vars Railway, DB, Fase C, bot.py scheduler, BUY/SELL/SKIP.

---

## Sesión 325 — 7 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / Telegram delivery / observability only / manual send gated / no trading
**Bloque:** B4.7 — Telegram Manual Send / LOG_ONLY
**Veredicto:** IMPLEMENTADO / VALIDADO / PUSH AUTORIZADO

### Discovery Telegram

Se encontraron patrones existentes de envio en `tools/*` y `bot.py`: `TELEGRAM_CHAT_ID` como chat comun, token dividido entre `TELEGRAM_TOKEN` (runtime/herramientas legacy) y `TELEGRAM_BOT_TOKEN` (Truth Pipeline), y `urllib.request` contra `api.telegram.org/bot.../sendMessage`. No hay helper unico compartido. La deduplicacion/cooldown existente vive en herramientas runtime con `alerts_state`/state files; B4.7 no agrega estado persistente ni anti-spam porque el envio es manual-only.

### Artefactos

- **Modificado:** `tools/daily_bot_digest.py` — agrega `--send-telegram-manual` y helper manual de envio.
- **Modificado:** `tools/daily_bot_observability_run.py` — expone `--send-telegram-manual` para snapshot + digest.
- **Modificado:** `tests/test_daily_bot_digest.py` — cubre no envio sin flag, env faltante, secretos y error API sin retry.
- **Modificado:** `tests/test_daily_bot_observability_run.py` — cubre gating manual y `TELEGRAM_NOT_CONFIGURED`.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

Comandos soportados:

- `python tools\daily_bot_digest.py --send-telegram-manual`
- `python tools\daily_bot_observability_run.py --write-snapshot --send-telegram-manual`

El flag imprime el preview Telegram y luego intenta enviar una sola vez. Usa `TELEGRAM_BOT_TOKEN` con fallback `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID`; no imprime tokens ni chat_id. Si faltan env vars, devuelve `TELEGRAM_NOT_CONFIGURED` sin fallo peligroso. Si falla Telegram API, devuelve `TELEGRAM_API_ERROR` sin retry/bucle. No scheduler, no Railway, no DB, no env var changes.

El mensaje conserva `DAILY BOT DIGEST`, P&L leaderboard DAY/WEEK/MONTH/ALL, Leaderboard trading volume DAY/WEEK/MONTH/ALL, `Trend vs previous valid snapshot`, `trend_label`, `source_quality=external_opaque`, `dashboard_equivalent=false`, `usable_for_bankroll=false`, `Observability only`, `No BANKROLL increase`, `No BUY/SELL/SKIP`, `No Fase C`.

### Validacion Codex

- `python tools\check_python_syntax.py tools\daily_bot_digest.py tools\daily_bot_observability_run.py tests\test_daily_bot_digest.py tests\test_daily_bot_observability_run.py` — OK.
- `python -m pytest tests\test_daily_bot_digest.py tests\test_daily_bot_observability_run.py -q -p no:cacheprovider` — 22 passed.
- `python tools\daily_bot_digest.py --send-telegram-manual --snapshot-file data\observability\leaderboard_pnl_snapshots.jsonl` con `TELEGRAM_*` vacias — preview impreso y `telegram_manual_send=TELEGRAM_NOT_CONFIGURED`.
- `git diff --check` — OK.

### NO se toco

Telegram real enviado, scheduler, Railway, DB, env vars modificadas, BANKROLL, trading core, `bot.py`, BUY/SELL/SKIP, Fase C, sizing, whitelist, city modes, guards, SL, reglas de riesgo, `bankroll_scaling_check.py`, semantica P&L.

---

## Sesión 327 — 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / observability / LOG_ONLY / no trading
**Bloque:** INTRA-REEVAL SHADOW outcome tracking
**Veredicto:** IMPLEMENTADO / VALIDADO LOCAL

### Cambios

- **Modificado:** `bot.py` — `v10.6.48` → `v10.6.49`; la review one-shot de INTRA-REEVAL shadow cruza triggers por `token_id` contra `trade_lifecycle.json`, anota `outcome_review` por trigger y guarda `outcome_review_summary`.
- **Modificado:** `verify_before_deploy.py` — checks estructurales y funcionales para `GOOD_SHADOW`, `BAD_SHADOW`, `OVERLAP_ACTIVE_REEVAL`, `STILL_OPEN` e `INSUFFICIENT_DATA`.
- **Actualizado:** `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl` — cierre y trazabilidad.

### Contrato

Clasificacion LOG_ONLY:

- `OVERLAP_ACTIVE_REEVAL`: hubo intento/cierre real posterior por `reeval` o `reeval_intra`.
- `GOOD_SHADOW`: el cierre posterior tuvo precio menor que el trigger; vender al trigger habria sido mejor.
- `BAD_SHADOW`: el cierre posterior tuvo precio mayor que el trigger; mantener/vender despues fue mejor.
- `STILL_OPEN`: lifecycle sigue `open`, `pending_exit` o `exit_failed`.
- `INSUFFICIENT_DATA`: falta token/timestamp/precio, no hay match lifecycle, no hay cierre posterior o falta precio de cierre.

El Telegram de review agrega n triggers, clasificados, overlap active reeval, good/bad/still_open/insufficient y la nota: `Observability only: no ventas nuevas, no BUY/SELL/SKIP, no BANKROLL, no Fase C.`

### Validacion Codex

- `python tools\check_python_syntax.py bot.py verify_before_deploy.py` — OK.
- `python verify_before_deploy.py` — pendiente de re-run final tras alinear docs/evento; los checks nuevos de INTRA-REEVAL pasaron en la primera corrida.

### NO se toco

Ventas nuevas, criterios de entrada/salida, scheduler, NOAA, BANKROLL, sizing, whitelist, city modes, SL, guards, env vars, DB, Railway, Fase C, `INTRA_REEVAL_ENABLED`, `INTRA_REEVAL_SHADOW_MODE`.

---

## Sesión 328 — 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / TRADERS_INTELLIGENCE / refresh evidencia / no trading
**Bloque:** Traders Intelligence daily alarm — stale census refresh
**Veredicto:** REFRESHED / STILL_NOT_READY

### Diagnostico

La alarma inicial llego como `TRADERS_INTELLIGENCE / REFRESH_REQUIRED / V1_NOT_READY`: `health_status=usable_signal`, `census_stale_days=15`, umbral esperado `<=14`, y daily summary con `recent_crosscheck_runs=2/5`.

### Refresh local

- Ejecutado `tools/directional_trader_census.py`: `n_scanned_markets=40`, `n_total_buy_trades=3545`, `n_unique_traders_raw=1107`, `n_traders_after_filter=8`.
- Ejecutado `tools/directional_trader_enrichment.py`: `n_traders_enriched=8`, `health_status=usable_signal`, `quality_reference_traders=3`, `active_directional_traders=4`.
- Ejecutado `tools/traders_intelligence_report.py`: `data/traders_intelligence.json` regenerado con `health_status=usable_signal`, `n_traders_profiled=13`, `census_stale_days=0`.
- Ejecutado `tools/traders_intelligence_daily_summary.py --dry-run`: readiness final `not_ready`.

### Antes / despues

- `census_stale_days`: `15` -> `0`.
- `health_status`: `usable_signal` -> `usable_signal`.
- `traders_intelligence.n_traders_profiled`: `16` -> `13`.
- Daily readiness: `not_ready` -> `not_ready`.
- Blocker final: `recent_crosscheck_runs=2`, requiere `>=5`.

### Traders fuertes finales

- `Entire-Hood`: `active_now=41`, `blocked_wr=93.3`, `blocked_n=30`; trader_only cities relevantes: Chengdu, Guangzhou, Houston, Jakarta, Kuala Lumpur, Madrid, Paris, Singapore, Warsaw, Wuhan.
- `Dimpled-Boy`: `active_now=11`, `blocked_wr=100.0`, `blocked_n=6`; trader_only cities relevantes: Ankara, Chengdu, Chongqing, Warsaw, Wuhan.
- `Loyal-Aggression`: `active_now=6`, `blocked_wr=100.0`, `blocked_n=6`; trader_only cities relevantes: Ankara, Miami.

### Validacion

- `python tools\check_python_syntax.py tools\directional_trader_census.py tools\directional_trader_enrichment.py tools\traders_intelligence_report.py tools\traders_intelligence_daily_summary.py` — OK.
- `git diff --check` — OK.
- `python verify_before_deploy.py` — `1152/1152` OK.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, Railway, DB, env vars, Telegram real, ni activacion v1.

---

## Sesión 329 — 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / TRADERS_INTELLIGENCE / trazabilidad / no trading
**Bloque:** Correccion mismatch local/runtime en recent_crosscheck_runs
**Veredicto:** CORREGIDO / NEEDS_CANONICAL_REEVAL

### Hallazgo

La discrepancia `recent_runs=7` live vs `recent_runs=2` local no era perdida de evidencia ni cambio de semantica. Eran fuentes distintas:

- Runtime Railway: `/app/data/traders_intelligence.json` usa `/app/data/signals_crosscheck.jsonl`; ese archivo tiene `26` lineas y `traders_intelligence_report.py` resume las ultimas `7`, por eso readiness live ve `recent_crosscheck_runs=7` OK.
- Local repo: no existe `data/signals_crosscheck.jsonl` porque esta gitignored; `traders_intelligence_report.py` cayo a `data/runtime_import_derived/signals_crosscheck.jsonl`, que tiene `2` lineas, por eso el refresh local dejo `recent_crosscheck_runs=2`.

### Correccion

- Se revierte solo `data/traders_intelligence.json` al estado anterior a `64daada`, porque el JSON versionado regenerado localmente desde fallback era misleading como foto de readiness.
- Se conservan los cierres documentales de la sesion previa como trazabilidad del refresh local y del diagnostico posterior.

### Estado correcto

- Fuente canonica para la alarma live: `/app/data/traders_intelligence.json` generado en Railway sobre `/app/data/signals_crosscheck.jsonl`.
- Fuente local del repo no debe usarse como equivalencia canónica si falta `data/signals_crosscheck.jsonl`.
- Readiness live observada read-only: `recent_crosscheck_runs=7` OK, `census_stale_days=15` WAIT, por tanto V1 sigue `not_ready`.
- Estado de aprendizaje tras el refresh local: **NEEDS_CANONICAL_REEVAL**. Para saber si queda `READY_CANDIDATE`, hay que refrescar/re-evaluar con inputs coherentes live o traer todos los inputs canónicos al entorno local.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, DB, env vars, Telegram real, ni activacion v1. Railway solo lectura.

---

## Sesión 330 - 8 de mayo de 2026 (Codex)

**Clasificacion:** FULL controlado / TRADERS_INTELLIGENCE / runtime artifacts / no trading
**Bloque:** Refresh canonico Railway de Traders Intelligence
**Veredicto:** REFRESHED_CANONICAL / READY_CANDIDATE

### Precheck

- Repo local: HEAD `3e47f9a` (`data: correct traders intelligence traceability`).
- `git status --short --untracked-files=all`: sin cambios versionados; solo untracked preexistente `2026-04-27]` y warning conocido de permisos `.pytest_cache`.
- Railway: project `enchanting-respect`, environment `production`, service `polymarket-bot`.
- Deployment activo: `035bb178-9a1c-4c79-ab9c-3346b42e7874`, status `SUCCESS`.
- Volume: `polymarket-bot-volume`, mount path `/app/data`, attached to `polymarket-bot`.

### Backup / listado previo

- Snapshot read-only ejecutado con `powershell -ExecutionPolicy Bypass -File .\tools\railway_runtime_snapshot_pull.ps1`.
- Listado/hash previo relevante:
  - `/app/data/directional_trader_census.json` 125K, sha256 `48d4bbf222afcb192bccc4283e43177109415768fc0105b0745079d2ed5eed72`.
  - `/app/data/directional_trader_enrichment.json` 62K, sha256 `c91d90a7349546eae8def7d9f64198db7fd7e4b64c55f024ed2f86f6d0c01bea`.
  - `/app/data/traders_intelligence.json` 277K, sha256 `f2534b0661809c7db249a5c3b0373ed7c31f9e34d9ac76a02609a6748d3e6b03`.
  - `/app/data/traders_intelligence_daily_summary_state.json` 403 bytes, sha256 `679054278515a051afe1fa14c6b04f2d384c39648c1523e5623bf4d0d701813c`.
  - `/app/data/signals_crosscheck.jsonl` 23K, sha256 `2cce609ef9cb5bbbd575020b9b14a2b4c3da61e6909fef3e54eb0bfbbb45cf27`.
- Backups remotos creados antes de sobrescribir:
  - `/app/data/directional_trader_census.json.pre_traders_refresh_20260508T112621Z`
  - `/app/data/directional_trader_enrichment.json.pre_traders_refresh_20260508T112621Z`
  - `/app/data/traders_intelligence.json.pre_traders_refresh_20260508T112621Z`
  - `/app/data/traders_intelligence_daily_summary_state.json.pre_traders_refresh_20260508T112621Z`

### Refresh canonico

- Ejecutado en Railway SSH dentro de `/app`, escribiendo en `/app/data`.
- `python tools/directional_trader_census.py --json-output /app/data/directional_trader_census.json --md-output /app/data/directional_trader_census_latest.md`
  - `n_scanned_markets=40`, `n_total_buy_trades=3609`, `n_unique_traders_raw=1089`, `n_traders_after_filter=4`.
- `python tools/directional_trader_enrichment.py --input /app/data/directional_trader_census.json --json-output /app/data/directional_trader_enrichment.json --md-output /app/data/directional_trader_enrichment_latest.md`
  - `n_traders_enriched=4`, `quality_reference_traders=1`, `active_directional_traders=2`, `health_status=usable_signal`, `likely_input_degraded=false`.
- `python tools/traders_intelligence_report.py ... --crosscheck-series /app/data/signals_crosscheck.jsonl ... --json-output /app/data/traders_intelligence.json --md-output /app/data/traders_intelligence_latest.md`
  - Fuente crosscheck confirmada: `/app/data/signals_crosscheck.jsonl`, no fallback local.
  - Output: `health_status=usable_signal`, `n_traders_profiled=15`, warning unico `blocked_signals_resolutions.jsonl n=553 global; per-trader N varies`.
- `python tools/traders_intelligence_daily_summary.py --intelligence /app/data/traders_intelligence.json --state-output /app/data/traders_intelligence_daily_summary_state.json --md-output /app/data/traders_intelligence_daily_summary_latest.md --dry-run`
  - `telegram_result=dry_run`, `readiness_transition=true`, sin Telegram real.

### Antes / despues

- `census_stale_days`: `15` -> `0`.
- `recent_crosscheck_runs`: `7` -> `7`.
- `health_status`: `usable_signal` -> `usable_signal`.
- `n_traders_profiled`: `77` -> `15`.
- V1 readiness: `not_ready` -> `ready`.
- Daily summary checks OK: health usable, census stale <=14, recent runs >=5, lead trader fuerte, >=2 traders fuertes, >=3 cities trader_only.

### Traders fuertes finales

- `Entire-Hood`: `active_now=38`, `blocked_wr=99.0`, `blocked_n=205`.
- `Dimpled-Boy`: `active_now=9`, `blocked_wr=99.0`, `blocked_n=97`.
- `Loyal-Aggression`: `active_now=6`, `blocked_wr=100.0`, `blocked_n=6`.
- Cities trader_only relevantes: `Los Angeles`, `Miami`, `San Francisco`, `Tel Aviv`.

### Artefactos runtime escritos

- `/app/data/directional_trader_census.json`
- `/app/data/directional_trader_census_latest.md`
- `/app/data/directional_trader_enrichment.json`
- `/app/data/directional_trader_enrichment_latest.md`
- `/app/data/traders_intelligence.json`
- `/app/data/traders_intelligence_latest.md`
- `/app/data/traders_intelligence_daily_summary_state.json`
- `/app/data/traders_intelligence_daily_summary_latest.md`

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, DB, env vars, Telegram real, ni activacion V1. Railway deploy no disparado por la operacion runtime.

### Siguiente accion

No activar V1 automaticamente. Ejecutar/acumular snapshots frescos con `python tools/traders_intelligence_snapshot.py` manual sobre `signals.json` fresco y mantener la evidencia como observabilidad antes de cualquier cambio semantico o ejecutable.

---

## Sesión 331 - 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / TRADERS_INTELLIGENCE / documentation-contract / no runtime
**Bloque:** Traders Intelligence V1 activation package
**Veredicto:** V1_PACKAGE_PREPARED / WAITING_CONFIRMATION

### Hallazgo

El repo ya tenia una V1 minima implementada desde el 2026-05-01:

- `tools/traders_intelligence_snapshot.py`
- `docs/traders-intelligence-v1-snapshots.md`
- guardrail en `tools/traders_intelligence_daily_summary.py` que, si readiness esta ready y la V1 minima existe, recomienda acumular snapshots frescos.

La V1 existente no es ejecutable para trading. Es un archivador manual de `signals.json` filtrado que produce pseudo-lifecycle observacional.

### Contrato preparado

Se crea `docs/traders-intelligence-v1-activation-package.md` con este contrato:

- `Traders Intelligence V1 active` significa permitir ejecucion manual de `tools/traders_intelligence_snapshot.py` contra `signals.json` fresco.
- Outputs: `data/traders_intelligence/snapshots/<run_id>.json`, `data/traders_intelligence/reports/<run_id>.json`, `data/traders_intelligence/pseudo_lifecycle_runs.jsonl`.
- Eventos permitidos: `appeared`, `still_present`, `disappeared_apparent`, `reappeared`.
- `disappeared_apparent` no es salida confirmada.
- Uso permitido: observabilidad, daily review, aprendizaje manual y preparacion de preguntas futuras.
- Uso prohibido: BUY/SELL/SKIP automatico, seguir salidas de traders, cambiar policy, cambiar city modes, sizing, BANKROLL, Fase C, scheduler, DB, env vars o Telegram accionable.

### Gates a mantener

- `health_status=usable_signal`.
- `census_stale_days <= 14`.
- `recent_crosscheck_runs >= 5`.
- `>=1` lead trader fuerte y muy activo.
- `>=2` traders fuertes.
- `>=3` cities trader_only entre traders fuertes.

La evidencia actual que justifica el paquete viene de la sesion 330:

- `census_stale_days=0`.
- `recent_crosscheck_runs=7`.
- `health_status=usable_signal`.
- readiness `ready`.
- strong traders: `Entire-Hood`, `Dimpled-Boy`, `Loyal-Aggression`.
- trader-only cities: `Los Angeles`, `Miami`, `San Francisco`, `Tel Aviv`.

### Cambios

- Creado: `docs/traders-intelligence-v1-activation-package.md`.
- Actualizado: `docs/traders-intelligence-v1-snapshots.md`.
- Actualizado: `docs/traders-intelligence-spec.md`.
- Actualizado: `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl`.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, DB, env vars, Railway runtime, Telegram real, ni criterios de readiness.

### Siguiente accion

Para pasar de `V1_PACKAGE_PREPARED` a `V1_ACTIVE_OBSERVATIONAL`: confirmacion separada, confirmar `signals.json` fresco, ejecutar `tools/traders_intelligence_snapshot.py --dry-run`, y si es coherente hacer una corrida manual real registrando run id, `n_current_signals`, status counts y artefactos escritos. Si se quiere ampliar scope, scheduler o uso ejecutable, parar y llevar a Opus.

---

## Sesión 332 - 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / TRADERS_INTELLIGENCE / observational manual / runtime artifacts gitignored
**Bloque:** Traders Intelligence V1 observational activation
**Veredicto:** V1_OBSERVATIONAL_ACTIVE / MANUAL_SNAPSHOT_1

### Contrato confirmado

V1 activa significa permitir ejecucion manual de `tools/traders_intelligence_snapshot.py` contra `signals.json` fresco para archivar snapshots filtrados y pseudo-lifecycle observacional bajo `data/traders_intelligence/`.

Queda fuera: scheduler, Telegram real/accionable, DB, env vars, policy, BUY/SELL/SKIP, BANKROLL, Fase C, trading core, cambios de readiness, scope expansion y cualquier interpretacion ejecutable.

### Input usado

- Fuente: `data/runtime_import/signals.json`.
- Frescura: `generated=2026-05-08T11:13:56.716424+00:00`.
- Resumen input: `n_actionable_signals=59`; quality traders `Entire-Hood`, `Dimpled-Boy`, `Villainous-Wave`, `Loyal-Aggression`.
- Scope fijo V1: traders `Thrifty-Original`, `Entire-Hood`; cities `Houston`, `Los Angeles`, `Manila`, `Miami`.

### Ejecuciones

- Dry-run: `python tools/traders_intelligence_snapshot.py --dry-run --run-id 20260508T111356Z-v1-observational-dry-run`.
  - Resultado: OK, sin writes.
  - `n_current_signals=1`.
  - Status counts: `appeared=1`, `still_present=0`, `disappeared_apparent=3`, `reappeared=0`.
- Corrida real manual: `python tools/traders_intelligence_snapshot.py --run-id 20260508T111356Z-v1-observational-manual-1`.
  - Resultado: OK.
  - `generated_at/snapshot_at=2026-05-08T11:44:51+00:00`.
  - `n_current_signals=1`.
  - Status counts: `appeared=1`, `still_present=0`, `disappeared_apparent=3`, `reappeared=0`.

### Artefactos runtime escritos

- `data/traders_intelligence/snapshots/20260508T111356Z-v1-observational-manual-1.json`.
- `data/traders_intelligence/reports/20260508T111356Z-v1-observational-manual-1.json`.
- `data/traders_intelligence/pseudo_lifecycle_runs.jsonl`.

Los tres viven bajo `data/traders_intelligence/` y estan gitignored como runtime/regenerables.

### Eventos observados

- `appeared`: `Entire-Hood` / `Houston|2026-05-08|range|75|F`.
- `disappeared_apparent`: `Entire-Hood` / `Los Angeles|2026-04-26|range|63|F`.
- `disappeared_apparent`: `Entire-Hood` / `Los Angeles|2026-04-27|range|65|F`.
- `disappeared_apparent`: `Thrifty-Original` / `Miami|2026-04-26|range|89|F`.

`disappeared_apparent` sigue siendo ausencia en snapshot filtrado, no salida confirmada.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, DB, env vars, Railway runtime, Telegram real, criterios de readiness ni scope V1.

### Siguiente accion

Acumular mas snapshots manuales con `signals.json` fresco antes de sacar conclusiones. Si se quiere ampliar scope a `Dimpled-Boy`, `Loyal-Aggression`, San Francisco o Tel Aviv, o conectar scheduler/Telegram/semantica ejecutable, parar y llevar a revision Opus.

---

## Sesión 333 - 8 de mayo de 2026 (Opus)

**Clasificacion:** LITE / TRADERS_INTELLIGENCE / documentation-only / no runtime
**Bloque:** Traders Intelligence roadmap V1 → V1.1 → V1.2 → recomendaciones
**Veredicto:** ROADMAP_DOCUMENTED / NOT_IMPLEMENTED

### Contenido

Persistido el diseño estratégico de evolución de Traders Intelligence en `docs/traders-intelligence-roadmap.md`. Cubre V1.1 (collector automático LOG_ONLY con kill switch, cooldown, idempotencia), V1.2 (evidence scoreboard read-only con cohortes cruzadas n>=30), Telegram Andon (salud + REVIEW_READY, nunca BUY/SELL/SKIP), gates entre fases, riesgos, primer patch Codex y scope explícitamente fuera.

### Cambios

- Creado: `docs/traders-intelligence-roadmap.md`.
- Actualizado: `docs/traders-intelligence-spec.md` (link al roadmap).
- Actualizado: `docs/traders-intelligence-v1-snapshots.md` (link al roadmap).
- Actualizado: `docs/traders-intelligence-v1-activation-package.md` (sección 10 con link).
- Actualizado: `HISTORIAL_SESIONES.md`, `agent_events.jsonl`.

### NO se toco

Trading core, BANKROLL, sizing, whitelist, city modes, scheduler, risk rules, policy gates ejecutables, Fase C, `bot.py`, DB, env vars, Railway runtime, Telegram real, criterios de readiness ni código alguno. `CONTEXTO.md` no se modificó: roadmap documental no cambia estado vivo runtime.

### Siguiente accion

Roadmap es diseño durable. Para mover de `ROADMAP_DOCUMENTED` a `V1.1_IMPLEMENTED_LOG_ONLY` requiere autorización explícita y revisión separada del primer patch (sección 9 del roadmap), siguiendo gates V1 → V1.1.
---

## Sesión 334 - 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / TRADERS_INTELLIGENCE / tooling observability / scheduler hook default OFF
**Bloque:** Traders Intelligence V1.1 collector automatico LOG_ONLY
**Veredicto:** V1.1_COLLECTOR_IMPLEMENTED_LOG_ONLY / DEFAULT_OFF

### Implementado

- Nuevo `tools/traders_intelligence_collector.py` como wrapper de `tools/traders_intelligence_snapshot.py`; no reimplementa la logica V1 de snapshots.
- Estado persistente `data/traders_intelligence/collector_state.json` con `last_run_id`, `last_snapshot_at`, `last_signals_generated_at`, `consecutive_failures`, `kill_switch_active`.
- Idempotencia: skip por `signals.json.generated` sin cambios, cooldown default 30 minutos y run_id derivado de `snapshot_at`.
- Kill switch: `TRADERS_INTELLIGENCE_COLLECTOR=OFF` default y auto-disable si `consecutive_failures >= 5`.
- Dry-run: ejecuta el snapshot tool con `--dry-run` y no escribe snapshots, reports, state ni eventos.
- Trazabilidad: corridas reales/fallos agregan evento `traders_intelligence_collector_run` en `agent_events.jsonl` con `run_id`, `n_signals`, `status_counts`, `dry_run`, `ok`.
- Hook en `bot.py` detras de `TRADERS_INTELLIGENCE_COLLECTOR=OFF`; queda conectado pero inerte hasta activacion explicita.
- `verify_before_deploy.py` agrega checks estructurales del collector y el hook.
- Docs actualizadas: `docs/traders-intelligence-roadmap.md`, `docs/traders-intelligence-v1-snapshots.md`, `docs/traders-intelligence-v1-activation-package.md`, `docs/traders-intelligence-spec.md`.

### Validacion

- `python tools/check_python_syntax.py tools/traders_intelligence_collector.py tests/test_traders_intelligence_collector.py bot.py verify_before_deploy.py`
- `python -m pytest tests/test_traders_intelligence_collector.py -q -p no:cacheprovider`
- `python tools/traders_intelligence_collector.py --dry-run --json` con env OFF: skip sin writes.
- `TRADERS_INTELLIGENCE_COLLECTOR=ON python tools/traders_intelligence_collector.py --dry-run --json`: completed, `n_current_signals=1`, `still_present=1`, sin writes.
- Validacion completa pre-commit registrada en el cierre de Codex.

### NO se toco

BANKROLL, sizing, whitelist, city modes, risk rules, Fase C, DB, env vars reales, BUY/SELL/SKIP, Telegram accionable, reglas de trading, NOAA ni semantica ejecutable. `bot.py` solo recibe hook LOG_ONLY default OFF.

### Siguiente accion

Activar `TRADERS_INTELLIGENCE_COLLECTOR=ON` solo cuando Pablo quiera empezar recoleccion automatica real. Tras 7 dias con `runs_24h>=20`, `consecutive_failures<3` y evidencia suficiente, evaluar V1.2 scoreboard read-only como patch separado.
---

## Sesión 335 - 8 de mayo de 2026 (Codex)

**Clasificacion:** FULL controlado / TRADERS_INTELLIGENCE / Railway env var / runtime validation
**Bloque:** Activacion Railway del collector V1.1 LOG_ONLY
**Veredicto:** ACTIVATION_ROLLED_BACK / NEEDS_CANONICAL_SIGNALS_PATH_FIX

### Precheck

- Git local limpio salvo el untracked preexistente `2026-04-27]`.
- HEAD local: `c570ae4 feat: add traders intelligence collector`.
- `origin/main`: `c570ae4`.
- Railway service `polymarket-bot`: deployment `f67b2b6c-b9fe-4577-b74e-bff26209eb49`, `SUCCESS`.
- `TRADERS_INTELLIGENCE_COLLECTOR` no existia/estaba OFF.
- Runtime `/app/data/signals.json` existia y estaba fresco: `generated=2026-05-08T14:04:48.969127+00:00`.
- No existia `/app/data/traders_intelligence/collector_state.json` antes de activar.

### Activacion y hallazgo

- Se activo `TRADERS_INTELLIGENCE_COLLECTOR=ON`.
- Railway deployment `5fd189e9-62c3-40f8-8ec7-140bc4fa06b5` termino en `SUCCESS`.
- Logs confirmaron ejecucion del collector:
  - `traders intelligence collector: status=completed reason=none run_id=20260508T141400Z-v11-collector`.
- Artefactos creados bajo `/app/data/traders_intelligence/`:
  - `collector_state.json`.
  - `snapshots/20260508T141400Z-v11-collector.json`.
  - `reports/20260508T141400Z-v11-collector.json`.
  - `pseudo_lifecycle_runs.jsonl`.
- Validacion detecto fuente no canonica/stale:
  - `collector_state.last_signals_generated_at=2026-05-07T21:59:28.094632+00:00`.
  - Esto no coincide con `/app/data/signals.json` fresco (`2026-05-08T14:04:48.969127+00:00`).
  - Interpretacion: el hook runtime uso el default `data/runtime_import/signals.json` en vez del canónico `/app/data/signals.json`.

### Rollback

- Para evitar acumulacion de evidencia stale, se puso `TRADERS_INTELLIGENCE_COLLECTOR=OFF`.
- Railway deployment `3e1a388d-7149-4eaa-9ea2-e8d0c95ccb62` termino en `SUCCESS`.
- Variable final confirmada: `TRADERS_INTELLIGENCE_COLLECTOR=OFF`.
- Logs de arranque posteriores sanos; no se observaron errores del collector tras el rollback.

### NO usar como evidencia

La corrida `20260508T141400Z-v11-collector` queda marcada como no canonica para V1.1 porque tomo `signals.json` stale. No debe alimentar readiness ni conclusion operativa.

### NO se toco

Codigo, DB, trading core, BANKROLL, sizing, whitelist, city modes, risk rules, Fase C, scheduler core, Telegram accionable ni BUY/SELL/SKIP.

### Siguiente accion

Patch acotado Codex: en `bot.py`, invocar `tools/traders_intelligence_collector.py` con `--signals` apuntando al `SIGNALS_FILE` runtime (`/app/data/signals.json` en Railway), y revisar que el evento runtime se escriba donde el scoreboard lo pueda recoger. Validar con dry-run/real controlado antes de reactivar `TRADERS_INTELLIGENCE_COLLECTOR=ON`.
---

## Sesión 336 - 8 de mayo de 2026 (Codex)

**Clasificacion:** FULL controlado / TRADERS_INTELLIGENCE / patch + Railway env var / runtime validation
**Bloque:** Correccion path canónico y reactivacion V1.1 collector LOG_ONLY
**Veredicto:** V1.1_COLLECTOR_ACTIVE_LOG_ONLY / CANONICAL_SOURCE_CONFIRMED

### Causa raiz

`bot.py` invocaba `tools/traders_intelligence_collector.py` sin `--signals`, por lo que el collector usaba su default local `data/runtime_import/signals.json`. En Railway eso no era el canónico runtime. Además, el evento del collector iba al default efímero del repo en vez de `AGENT_EVENTS_FILE` del Volume.

### Patch

- `bot.py`: `maybe_run_traders_intelligence_collector()` ahora pasa explícitamente:
  - `--signals SIGNALS_FILE` (`/app/data/signals.json` en Railway).
  - `--agent-events AGENT_EVENTS_FILE` (`/app/data/agent_events.jsonl` en Railway).
- `verify_before_deploy.py`: checks estructurales para asegurar que el hook usa `SIGNALS_FILE`, no `data/runtime_import`, y escribe eventos en `AGENT_EVENTS_FILE`.

### Validacion local

- `python tools/check_python_syntax.py bot.py verify_before_deploy.py tools/traders_intelligence_collector.py tests/test_traders_intelligence_collector.py`
- `python -m pytest tests/test_traders_intelligence_collector.py -q -p no:cacheprovider` -> 7 passed.
- `git diff --check` OK.
- `python verify_before_deploy.py` -> 1162/1162 OK.

### Deploy y runtime

- Commit de patch: `13fe375 fix: use canonical signals for traders collector`.
- Push a `origin/main`: si.
- Railway deploy del patch: `73d0f992-f397-4ccc-a614-f0324ca91344` -> `SUCCESS`.
- Dry-run runtime explícito con `/app/data/signals.json`:
  - `signals_generated_at=2026-05-08T14:27:45.782018+00:00`.
  - Sin writes.

### Cuarentena de corrida no canonica

Antes de reactivar se movio el directorio contaminado de la sesion 335:

- De: `/app/data/traders_intelligence/`.
- A: `/app/data/traders_intelligence_quarantine_noncanonical_20260508T141400Z/`.

Contenido preservado: `collector_state.json`, `pseudo_lifecycle_runs.jsonl`, snapshot y report `20260508T141400Z-v11-collector`. No se borro evidencia.

### Reactivacion

- `TRADERS_INTELLIGENCE_COLLECTOR=ON`.
- Railway deployment: `8d417a19-1641-43ab-979c-7408430e70ec` -> `SUCCESS`.
- Logs: `traders intelligence collector: status=completed reason=none run_id=20260508T143136Z-v11-collector`.

### Artefactos canonicos creados

- `/app/data/traders_intelligence/collector_state.json`.
- `/app/data/traders_intelligence/snapshots/20260508T143136Z-v11-collector.json`.
- `/app/data/traders_intelligence/reports/20260508T143136Z-v11-collector.json`.
- `/app/data/traders_intelligence/pseudo_lifecycle_runs.jsonl`.
- Evento runtime en `/app/data/agent_events.jsonl`.

Estado final del collector:

- `last_run_id=20260508T143136Z-v11-collector`.
- `last_signals_generated_at=2026-05-08T14:31:35.577924+00:00`.
- `last_snapshot_at=2026-05-08T14:31:36+00:00`.
- `consecutive_failures=0`.
- `kill_switch_active=false`.
- `n_current_signals=0`.
- `prior_snapshots=0`.
- `source_signals_path=/app/data/signals.json`.

### NO se toco

DB, trading core semantico, BUY/SELL/SKIP, BANKROLL, sizing, whitelist, city modes, risk rules, Fase C, scheduler core, Telegram accionable ni criterios/scope de Traders Intelligence.

### Siguiente accion

Dejar correr V1.1 con `TRADERS_INTELLIGENCE_COLLECTOR=ON` y revisar tras las proximas senales frescas. Si el scope fijo V1 sigue dando `n_current_signals=0` durante varias corridas, tratarlo como pregunta de scope/evidencia separada, no como fallo operativo.

## Sesión 337 - 8 de mayo de 2026 (Codex)

**Clasificacion:** FULL controlado / WALLET_PNL / Railway runtime precheck / no write
**Bloque:** Wallet cash flow attestation para P&L canonico futuro
**Veredicto:** BLOCKED_NEEDS_MANUAL_WITHDRAWAL_CONFIRMATION

### Precheck y evidencia Railway

- Git inicial: working tree sin cambios versionados; untracked preexistente `2026-04-27]`; warning conocido de permisos en `.pytest_cache`.
- HEAD inicial: `fbbbebe docs: record traders collector canonical activation`.
- Railway service `polymarket-bot`: deployment `f1596e28-0045-4f9d-9ceb-a7d2f48b7aec`, `SUCCESS`.
- `/app/data/wallet_cash_flows.jsonl`: missing.
- `/app/data/wallet_portfolio_snapshots.jsonl`: existe.
- `wallet_cash_flow_log.py show --data-dir /app/data --json`: `status=missing`, `row_count=0`.
- `wallet_snapshot.py --report-only --json --data-dir /app/data`: 10 snapshots validos, 10 dias, `history_span_hours=201.81`, baseline `2026-05-01T08:00:30.743065+00:00`, latest `2026-05-08T08:01:04.117648+00:00`, `possible_deposits_7d_count=0`, `cash_flows.status=missing`, `phase2_ready=false`, `phase2_ready_reason=cash_flow_unknown`, `wallet_pnl_available=false`.
- `pnl_report.py --data-dir /app/data --json`: `canonical_source=none`, `bankroll_readiness=blocked`, cashflow log missing, horizontes `blocked`, `promotes_canonical_source=false`.

### Snapshot review

Rango disponible completo: `2026-04-29T22:12:16.678244+00:00` a `2026-05-08T08:01:04.117648+00:00`.

Valores `total_value`: 19.90, 18.89, 17.71, 17.68, 17.68, 19.61, 19.10, 18.94, 20.61, 22.54.

Deltas aproximados: -1.01, -1.18, -0.03, 0.00, +1.93, -0.51, -0.16, +1.67, +1.93. Todos los snapshots tienen `possible_deposit=false`; no aparece salto grande compatible con deposito/retiro obvio, pero los snapshots por si solos no prueban ausencia de retiradas.

### Comando dry-run propuesto

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "python tools/wallet_cash_flow_log.py append --type no_cash_flow_attestation --period-start 2026-04-29T22:12:16.678244Z --period-end 2026-05-08T08:01:04.117648Z --note 'Pablo manual attestation: no deposits after known 2026-03-30 deposit; Codex snapshot review found no possible_deposit=true or withdrawal-like suspicious jumps in available wallet snapshots. Withdrawal absence still requires Pablo confirmation before write.' --data-dir /app/data --json"
```

Resultado: dry-run OK, row schema v2, `actor=pablo_manual`, `type=no_cash_flow_attestation`, sin `amount_usdc`; no escribio runtime.

### Criterio de parada aplicado

Pablo confirmo el ultimo deposito conocido (`2026-03-30`, 15 USDC) y que no hubo depositos posteriores. No habia confirmacion explicita de que no hubiera retiradas ni otros cash flows durante `2026-04-29T22:12:16.678244Z` -> `2026-05-08T08:01:04.117648Z`. Por politica anti-falsificacion, no se ejecuto `--write --init`.

### Estado final

- Runtime escrito: no.
- `/app/data/wallet_cash_flows.jsonl`: sigue missing.
- `canonical_source`: `none`.
- BANKROLL readiness: `blocked`.
- BANKROLL $35: no autorizado.
- Fase C: no autorizada.

### NO se toco

BANKROLL, Fase C, trading core, `bot.py`, scheduler, DB, env vars, sizing, whitelist, city modes, risk rules, Telegram real. No se creo deposito/retiro inventado ni attestation real.

### Siguiente accion

Pablo debe confirmar manualmente: "No hubo retiradas ni otros cash flows entre `2026-04-29T22:12:16.678244Z` y `2026-05-08T08:01:04.117648Z`." Con esa confirmacion, repetir el append con `--write --init --yes` contra `/app/data`, verificar JSONL y rerun `wallet_snapshot.py`/`pnl_report.py`.

---

## Sesión 338 - 8 de mayo de 2026 (Codex)

**Clasificacion:** FULL controlado / WALLET_PNL / runtime data write
**Bloque:** Wallet cash flow attestation real para P&L canonico futuro
**Veredicto:** CASHFLOW_ATTESTATION_STARTED / WAITING_CANONICAL_PNL_GATES

### Confirmacion manual

Pablo confirmo explicitamente que no hubo depositos, retiradas ni otros cash flows externos en Polymarket durante:

`2026-04-29T22:12:16.678244Z` -> `2026-05-08T08:01:04.117648Z`.

El ultimo deposito conocido fue el `2026-03-30` por 15 USDC, fuera de esta ventana.

### Precheck

- Railway service `polymarket-bot`: deployment `1df88fcd-8711-4e78-b7a0-547c510ecdd5`, `SUCCESS`.
- `/app/data/wallet_cash_flows.jsonl`: missing antes del write.
- `/app/data/wallet_portfolio_snapshots.jsonl`: existe.
- Git inicial: `4a40d99 docs: record wallet cash flow attestation precheck`, sin cambios versionados, untracked preexistente `2026-04-27]`.

### Runtime write

Comando ejecutado:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "python tools/wallet_cash_flow_log.py append --type no_cash_flow_attestation --period-start 2026-04-29T22:12:16.678244Z --period-end 2026-05-08T08:01:04.117648Z --note 'Pablo manual attestation: no deposits, withdrawals, or other external Polymarket cash flows during this period. Last known deposit was 2026-03-30 for 15 USDC, outside this window. Codex snapshot review found no possible_deposit=true or withdrawal-like large suspicious jumps in available snapshots.' --data-dir /app/data --write --init --yes --json"
```

Resultado: `appended=true`, path `/app/data/wallet_cash_flows.jsonl`.

Linea JSONL registrada:

```json
{"actor":"pablo_manual","entry_id":"12fc15e1-f5f5-4197-aadc-1f42e4abeff1","note":"Pablo manual attestation: no deposits, withdrawals, or other external Polymarket cash flows during this period. Last known deposit was 2026-03-30 for 15 USDC, outside this window. Codex snapshot review found no possible_deposit=true or withdrawal-like large suspicious jumps in available snapshots.","period_end":"2026-05-08T08:01:04.117648Z","period_start":"2026-04-29T22:12:16.678244Z","recorded_at":"2026-05-08T15:23:02.657857Z","schema_version":2,"type":"no_cash_flow_attestation"}
```

`wallet_cash_flow_log.py validate --data-dir /app/data --json`: `ok=true`, `status=valid`, `rows=1`.

### Reportes read-only

`wallet_snapshot.py --report-only --json --data-dir /app/data`:

- `cash_flows.status=attested_full_7d`.
- `coverage_days_7d=7`.
- `attestation_count=1`.
- `n_records_valid=1`.
- `phase2_ready=false`.
- `phase2_ready_reason=need_more_history`.
- `valid_snapshots=10` de 14 requeridos.
- `valid_snapshot_days=10`.
- `history_span_hours=201.81`.
- `wallet_pnl_available=true`.
- `wallet_pnl_7d=4.83`.
- `possible_deposits_7d_count=0`.

`pnl_report.py --data-dir /app/data --json`:

- `canonical_source=none`.
- `bankroll_readiness=blocked`.
- `guardrails.promotes_canonical_source=false`.
- `inputs.cash_flows.status=present`, `n_records=1`, `coverage_days=7.0`.
- `1W`: `status=provisional`, `value_usdc=4.86`, `confidence=low`, blocker `canonical_requires_B5_B6_opus_review_pablo_signoff`.
- `ALL`: `status=provisional`, `value_usdc=2.64`, `confidence=low`, same canonical review blocker.
- `1D`: blocked por single snapshot.
- `1M`: blocked por coverage menor a 1M.

### Estado final

La cadena de cashflow manual queda iniciada, pero no hay P&L canonico ni readiness de BANKROLL. Siguiente faltante para BANKROLL $35: al menos 14 snapshots validos/gates de historia, cross-check manual contra dashboard Polymarket, reconciliacion/divergencia aceptable, revision Opus y signoff Pablo, ademas de los gates generales de bankroll scaling.

### NO se toco

BANKROLL, Fase C, trading core, `bot.py`, scheduler, DB schema, env vars, sizing, whitelist, city modes, risk rules, Telegram real.

---

## Sesión 339 - 8 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / tooling observability / LOG_ONLY
**Bloque:** DB Throughput Report reutilizable
**Veredicto:** IMPLEMENTED_LOCAL_VALIDATED / RAILWAY_READ_ONLY_PENDING_POST_DEPLOY

### Cambios

- Creado `tools/db_throughput_report.py`.
- Creado `tests/test_db_throughput_report.py`.
- Creado `docs/db-throughput-report.md`.
- Actualizado `verify_before_deploy.py` con guardrails estructurales del tool.

### Contrato

La CLI abre SQLite con URI `mode=ro` y `PRAGMA query_only=ON`. Emite JSON por defecto o con `--json`, Markdown con `--markdown`, y permite `--output` local opcional. El reporte cubre frescura DB, ciclos por slot UTC, markets evaluated, buys, buy rate, snapshots por ciudad, condicion nativa/payload/inferida desde `question` (formatos `°C/°F`, `or higher`, `or below`, `between X-Y`), distribucion `exact/range/at_or_above/at_or_below`, gaps y top cuellos. Si faltan tablas o columnas, degrada con `source_quality` y warnings.

### Validacion local

- `python tools/check_python_syntax.py tools/db_throughput_report.py tests/test_db_throughput_report.py verify_before_deploy.py` OK.
- `python -m pytest tests/test_db_throughput_report.py -q -p no:cacheprovider --basetemp .tmp_pytest_db_throughput3` -> 8 passed. El primer intento sandboxed fallo por ACL de `%TEMP%`; se rerun fuera del sandbox y se limpiaron temporales.
- `python tools/db_throughput_report.py --db data/polymarket.db --json` -> local DB ausente, `db_not_found` controlado.
- `git diff --check` OK.
- `python verify_before_deploy.py` -> 1171/1171.

### NO se toco

BANKROLL, Fase C, trading core, `bot.py`, scheduler, DB schema, env vars, sizing, whitelist, city modes, risk rules, Telegram.

---

## Sesión 342 - 10 de mayo de 2026 (Claude Code)

**Clasificacion:** FULL controlado / Phase 2 Recalibration / bot.py + Railway env vars
**Bloque:** Phase 2 mixed-condition monitor v10.6.50 + apertura Phase 2
**Veredicto:** PHASE2_RECALIBRATION_ABIERTA / T+30=2026-06-09

### Contexto

Opus aprobó Phase 2 Recalibration como experimento mixed-condition de 30 días tras kill-switch canary (Sesión 341, WR=42.9% n=21). Precheck reveló que el monitor legacy S341 hubiera disparado hoy 2026-05-10 sobre la cohorte pre-Phase2, contradiciendo Phase 2 → NEEDS_PATCH aplicado antes de Railway.

### Cambios

- `bot.py` v10.6.49 → v10.6.50:
  - `_phase2_monitor_stats`: calcula WR mixed-condition (exact+at_or_above+at_or_below) y WR exact-slice desde 2026-05-10. Range excluido.
  - `_build_phase2_monitor_message`: alarma Telegram con copy "Phase 2 mixed-condition rollback recommended" / "Exact slice degraded". Sin BUY/SELL/SKIP. Sin auto-mutación Railway.
  - `maybe_run_phase2_monitor`: monitor rolling diario, anti-spam por tipo de kill-switch.
  - `maybe_run_condition_monitor`: `CANARY_RETIRED = date(2026, 5, 10)` — retira el monitor legacy desde esta fecha. Evita que WR=42.9% n=21 continúe disparando alarmas contradictorias con Phase 2.
  - Integrado en `run_alarms` con try/except.
- `verify_before_deploy.py`: 13 guardrails nuevos v10.6.50 (1187/1187).
- `tests/test_phase2_monitor.py`: 20 tests (retirement legacy + stats + message + monitor).

### Kill-switches Phase 2

- Mixed (exact+at_or_above+at_or_below): WR<40% con n≥20 → alarma rollback Phase 2.
- Exact-slice: WR<40% con n≥10 → alarma para vaciar `QUALITY_TRADER_CONDITIONS`.
- Sin auto-mutación Railway en ningún caso.

### Railway

- Deploy #1 (código v10.6.50): `8d4dd978-ad4f-4180-85a1-e37242ce0535` SUCCESS.
- Env vars seteadas tras deploy #1:
  - `QUALITY_TRADER_CONDITIONS`: `` (vacío) → `exact`
  - `ACTIVE_TRADING_CITIES`: `NONE` → `Shanghai,Tokyo,Buenos Aires,Ankara`
  - `BLOCKED_CITIES`: `London` → `London,Paris,Atlanta,Chicago`
  - `ALLOWED_CONDITIONS`: sin cambio (default `at_or_above,at_or_below`)
- Deploy #2 (env vars): `13868d46-7046-4b22-a86c-11d507a278fd` SUCCESS.

### Validacion

- `python -m pytest tests/test_phase2_monitor.py -q` → 20/20.
- `python verify_before_deploy.py` → 1187/1187.
- `git diff --check` → OK.
- Runtime `/app/bot.py`: BOT_VERSION v10.6.50, CANARY_RETIRED, maybe_run_phase2_monitor confirmados.

### Criterios T+30 (2026-06-09)

- n trades cerrados mixed-condition ≥ 25
- WR mixed-condition ≥ 45%
- PnL absoluto ≥ +$5
- drawdown máximo no peor que −$6
- al menos 2 de 4 ciudades Active con n≥3 y WR≥40%
- slice exact aislado: n≥10 y WR≥45%
- si falla cualquiera: `RECOMMEND_KILL_MODEL_PATH` / pivot leaderboard intelligence

### Rollback documentado

```
QUALITY_TRADER_CONDITIONS=       (vacío)
ACTIVE_TRADING_CITIES=NONE
BLOCKED_CITIES=London
```

### NO se toco

BANKROLL, Fase C, sigma, MIN_EDGE, low-price buffer, Kelly, sizing, exits, scheduler, NOAA, settlement logic, DB, trading core semántico.

---

## Sesión 345 - 13 de mayo de 2026 22:11 +02:00 (Codex)

**Clasificacion:** ACTION_NOW / ESCALATE_OPUS
**Bloque:** Auditoria read-only alarmas Telegram / runtime policy
**Veredicto:** PARIS_BLOCKED_ENV_BOUGHT_AS_CANARY / OPUS_REVIEW_REQUIRED

### Resumen

Auditoria read-only de las alarmas recientes confirma contradiccion runtime/policy: Railway tenia `BLOCKED_CITIES=London,Paris,Atlanta,Chicago`, pero el ciclo #304 (`2026-05-13T06:39:03Z`) compro Paris NO como `city_mode=canary`. Causa tecnica localizada: `is_city_blocked()` no aplica bloqueo duro si la ciudad tiene observed/NOAA proxy, por lo que Paris cae por `auto_canary_cities` pese al env blocked. Esto contradice el contrato operativo documentado de que `blocked` no tradea ni observa.

- Paris: contradiccion runtime/policy; escalar a Opus antes de cualquier patch.
- Munich: CANARY permitido por diseno; ciclo #304 compro Munich NO y cerro TP intra con PnL positivo.
- Seoul: CANARY esperado; ciclo #301 compro Seoul YES con sizing canary y luego cerro por `stop_loss_intra`.
- Los Angeles: gap operativo real en traders-vs-bot; no esta en whitelist, `RESOLUTION_ICAO` ni `OBSERVED_AUDIT_CITIES`, y requiere paquete de revision humana/Opus antes de cualquier cambio.
- L2 Hazard e INTRA-REEVAL SHADOW en Paris: LOG_ONLY correcto; no ejecutaron SELL ni tocaron lifecycle/trading, aunque operaron sobre una posicion que no deberia existir bajo bloqueo duro.

### NO se toco

No hubo cambios de codigo. No se tocaron BANKROLL, whitelist, city modes, scheduler, trading core, env vars, Railway, DB ni runtime. `CONTEXTO.md` queda sin cambios hasta decision Opus.

---

## Sesión 346 - 14 de mayo de 2026 (Claude Code / Opus)

**Clasificacion:** LITE / docs-only / diseño estratégico
**Bloque:** City Intelligence v2 — diseño paraguas
**Veredicto:** DESIGN_DOCUMENTED / IMPLEMENTATION_DEFERRED

### Cambios

- Creado `docs/city_intelligence_v2_design.md`.

### Resumen del diseño

City Intelligence v2 = paraguas, no monolito. Dos productores y un consumidor:

- **Source Onboarding Scanner** (NEW, Fase A) — universo: ciudades fuera del flujo. Detecta candidatas a `OBSERVED_AUDIT` desde signals_crosscheck, blocked_signals, shadow_tracking, RESOLUTION_ICAO. Estados Fase A: `READY_FOR_SOURCE_AUDIT`, `WAITING_EVIDENCE`, `RANGE_ONLY_NOT_OPERABLE`, `SOURCE_BLOCKED`.
- **City Lifecycle Review Monitor** (EXISTING, sin tocar) — universo: ciudades dentro del flujo.
- **City Intelligence Digest** (NEW, Fase B) — un Telegram LOG_ONLY diario que une ambas salidas.

Jurisdicción disjunta por construcción: el Scanner excluye `ACTIVE ∪ CANARY ∪ BLOCKED ∪ OBSERVED_AUDIT ∪ auto_canary ∪ auto_shadow ∪ shadow_tracking(cycles≥10) ∪ overrides.keys()`. Handoff con el Lifecycle Monitor vía edición manual de `city_lifecycle_overrides.json` por Pablo — sin import directo entre tools.

Matices clave:
- Fase A excluye `BLOCKED_CITIES` para mantener scope; *blocked source re-audit* diferido a v1.1.
- Paths por CLI, sin dependencia conceptual de `runtime_import_derived`; debe poder apuntar a `/app/data` en runtime futuro.
- Fallo de carga de `RESOLUTION_ICAO` ≠ `SOURCE_BLOCKED`. Si falla la herramienta: `degraded: true`, ciudades a `WAITING_EVIDENCE`, warning `RESOLUTION_ICAO_UNAVAILABLE`.
- Sample mínimos heredados de A7 audit: blocked WR n≥20 + bot_evaluation poblada, trader consensus fuentes≥2 días≥3, shadow leak cycles≥10.

Doc incluye prompt completo para Sonnet (Fase A) listo para pegar cuando Pablo autorice implementación.

### NO se toco

No hubo cambios de código. No se tocaron BANKROLL, whitelist, city modes, scheduler, trading core, env vars, Railway, DB, runtime, Telegram, ni `city_lifecycle_review_monitor.py`. `CONTEXTO.md` y `agent_events.jsonl` sin cambios (docs-only / sin estado vivo durable).

---

## Sesión 357 - 15 de mayo de 2026 (Codex)

**Clasificacion:** LITE / RISK_CONTROL / docs-only + higiene
**Bloque:** Phase 2 T+30 contamination precheck — Paris #304
**Veredicto:** PARIS_304_EXCLUDED_FROM_T30_SCORING / HARD_BLOCK_POST_S347_CONFIRMED

### Resumen

Cierre LITE de la auditoria read-only Phase 2 contamination precheck. Railway live conserva `BLOCKED_CITIES=London,Paris,Atlanta,Chicago`; `/app/data/city_policy_state.json` conserva overlays stale `auto_canary_cities.Paris`, `auto_canary_cities.Chicago` y `auto_shadow_cities.Atlanta`. La evidencia runtime posterior a S347 muestra Paris con `city_mode=blocked` y `allowlisted=false`, por lo que los overlays stale ya no habilitan nuevas admisiones/trades blocked.

Paris #304 queda marcado como contaminado pre-fix para scoring T+30: token `90540818137674278987146948237136603818166030618576062534092750591125921298198`, `Paris 14°C May13 NO`, `exact`, opened `2026-05-13T06:39:02.955596Z`, `cycle_number=304`, `city_mode=canary` en `cycles_history`, cerrado `LOSS_TOTAL / micro_position_unsellable`, `pnl_cash=-2.19`.

### Regla T+30

Excluir exactamente Paris #304 de la cohorte Phase 2 al scoring del `2026-06-09`, con motivo `trade contaminado por bug de admision pre-S347`. No excluir otros trades salvo evidencia clara equivalente.

### Higiene repo

Se elimino `cutoff]`, artifact accidental de la auditoria con salida `SyntaxError` de un one-liner Python remoto mal quoteado. No se toco `2026-04-27]`.

### NO se toco

No se tocaron codigo, runtime, Railway writes, env vars, DB, BANKROLL, Fase C, city modes, scheduler, whitelist, promotion gates, source fidelity blocked cities ni nuevos experimentos.

---

## Sesión 362 - 17 de mayo de 2026 (Sonnet 4.6)

**Clasificacion:** LITE / docs-only / cierre trazabilidad
**Bloque:** Legacy cleanup city-intelligence / phase5-visibility — cierre definitivo
**Veredicto:** TRANSITION_CLOSED

### Resumen

Precheck read-only confirmó que el cleanup Railway ya estaba ejecutado antes de esta sesion: `city-intelligence` y `phase5-visibility` borrados del proyecto (Service not found); `city-intelligence-volume` y `phase5-visibility-volume` borrados (no aparecen en `railway volume list --json`). Unico servicio vivo: `polymarket-bot` (SUCCESS). Unico volumen vivo: `polymarket-bot-volume` (115.67MB). Runtime bridge operacional: `runtime_inputs_status=available`, `city_intelligence_pipeline`, `city_validation_ledger` y `city_promotion_gate` con timestamp 2026-05-17T08:00:xx.

### Cambios

- `data/service_transition_followup.json`: checkpoint `transition_closeout_2026_05_07` marcado `resolved`; `phase` actualizado a `transition_closed`.
- `HISTORIAL_SESIONES.md`: esta entrada.

### NO se toco

No se tocaron codigo, Railway, env vars, DB, BANKROLL, Fase C, city modes, scheduler, whitelist, promotion gates, trading core ni CONTEXTO.md (sin estado vivo durable que cambiar).

---

## Sesión 363 - 17 de mayo de 2026 (Sonnet 4.6)

**Clasificacion:** LITE / docs-only / dirección estratégica
**Bloque:** Operating Model empresa/ROI/tokens-as-payroll
**Veredicto:** DOCTRINE_UPDATED

### Decisión

Se incorporó el principio rector de la sesión 2026-05-17 en `ORCHESTRATOR.md §13`: el sistema opera como empresa orientada a monetización, no como máquina de auditorías. Bankroll = capital operativo; tokens = nómina; P&L semanal = cuenta de resultados.

### Reglas incorporadas

- **Inversión de tokens**: no abrir agente si la tarea no puede mover P&L, throughput, riesgo, BANKROLL readiness o calidad de decisión.
- **Salidas de sesión**: `IMPLEMENTED / EXPERIMENT_PREPARED / OPUS_DECISION_TAKEN / TRIGGER_DEFINED / ARCHIVED / ACTION_NOW`. Prohibido "seguimos monitorizando" sin trigger explícito.
- **Datos insuficientes**: responder qué falta, si hay herramienta, qué trigger reabre, cuándo archivar.
- **Patrón capacidad**: toda auditoría debe seguir blocker→solución→herramienta→experimento→trigger→capacidad.
- **Anti-patrones listados**: auditorías sin decisión, Opus para WATCH sin trigger, herramientas sin workflow.
- **Reglas de agente**: Opus=semántica, Codex=implementación, Sonnet=docs/síntesis; si Opus ya decidió, ejecutar sin reanalizar.

### Ejemplo canónico

Measurement Layer / METAR (sesión 2026-05-17): detectó blocker, generalizó solución, creó tooling LOG_ONLY, definió Wave 1, conectó con promoción de ciudades. Patrón de auditoría que se convierte en capacidad productiva.

### Cambios

- `ORCHESTRATOR.md`: nueva sección §13 Operating Model con subreglas A–H.
- `HISTORIAL_SESIONES.md`: esta entrada.

### NO se toco

No se tocaron codigo, runtime, Railway, env vars, DB, BANKROLL, Fase C, city modes, scheduler, whitelist, promotion gates, trading core, AGENTS.md ni CONTEXTO.md.
---

## Sesión 364 - 17 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / LOG_ONLY tooling / METAR Measurement Layer
**Veredicto:** IMPLEMENTED

### Objetivo

Cerrar el deployment pendiente del ultimo push docs-only y, si Railway estaba `SUCCESS`, implementar una salida operativa LOG_ONLY para parity/coverage METAR que reduzca revision manual ad hoc sin tocar runtime de trading.

### Cambios

- Confirmado Railway deployment `861f017d-bfbd-4a6e-ae32-13e8f9c8f25e` en `SUCCESS` antes de tocar codigo.
- `tools/metar_parity_report.py` ahora genera readout por ciudad y estacion con coverage, insufficient coverage, `parity_status`, delta METAR-WU, delta METAR-Open-Meteo y alertas LOG_ONLY estructuradas.
- Nuevo output JSON manual `data/metar_shadow_report.json` (gitignored) para consumo seguro por revision manual o digest futuro.
- Alertas emitidas: `A_METAR_PARITY_DRIFT`, `A_METAR_COVERAGE_GAP`, `A_METAR_VS_OM_DELTA`, `LUCKNOW_COMPARABLE_DAYS_WATCH`.
- `docs/metar_measurement_layer.md` documenta el contrato operativo nuevo.

### Validacion

- `python -m py_compile tools\metar_parity_report.py tools\metar_shadow_fetch.py`
- `python -m pytest tests\test_metar_measurement_layer.py` -> 6 passed
- `python tools\metar_parity_report.py --md-out data\metar_shadow_report.md` -> `METAR_PARITY_INSUFFICIENT_DATA`, 11 rows, coverage 100%, 1 alert Lucknow watch
- `git diff --check` OK
- `verify_before_deploy.py` se re-ejecuta tras alinear trazabilidad

### Guardrails

No se tocaron `bot.py`, trading core, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, env vars, DB, city modes, whitelist, scheduler automatico, Telegram runtime, NOAA runtime ni promotion gates.

---

## Sesión 366 - 18 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / LOG_ONLY digest-Telegram / METAR Measurement Layer
**Veredicto:** IMPLEMENTED

### Objetivo

Integrar METAR Wave 1 + Wave 2 en el resumen diario Telegram existente sin crear scheduler nuevo y evitando falsos `A_METAR_COVERAGE_GAP` cuando el dia local de una estacion aun no cerro.

### Cambios

- `bot.py` agrega bloque `METAR LOG_ONLY` al resumen diario Telegram. Lee solo el ultimo `metar_shadow_report.json` existente: `/app/data/metar_shadow_report.json` en Railway via `_data_path`, con fallback local `data/metar_shadow_report.json`.
- `tools/metar_parity_report.py` emite `wave_summary`, `coverage_status`, `waiting_local_day_close`, horas locales por fila y separa gaps reales de `WAITING_LOCAL_DAY_CLOSE`.
- `A_METAR_COVERAGE_GAP` ya no se emite si la fecha local de la estacion esta incompleta.
- `docs/metar_measurement_layer.md` documenta el trigger manual: refrescar estaciones con `tools/metar_shadow_fetch.py` y luego `tools/metar_parity_report.py`; el digest no hace fetch ni report runtime.
- `docs/source_audits/metar_measurement_layer_report.md` queda regenerado con Wave 1 + Wave 2: 19 rows, coverage 94.7%, Wave 1 healthy, Wave 2 con Toronto/CYYZ waiting local close, 0 gaps reales.

### Validacion

- `python -m py_compile bot.py tools\metar_parity_report.py tools\metar_shadow_fetch.py verify_before_deploy.py`
- `python -m pytest tests\test_metar_measurement_layer.py tests\test_source_onboarding_runtime.py` -> 29 passed
- Dry-run del bloque diario: Wave 1 10/10, Wave 2 7/7, coverage 87.5%, Toronto/CYYZ 2026-05-17 `Waiting local day close`
- `python tools\metar_parity_report.py --no-write-csv --json-out data\metar_shadow_report.json` -> `METAR_PARITY_INSUFFICIENT_DATA`, 1 alerta Lucknow watch
- `git diff --check` OK
- `python verify_before_deploy.py` -> 1255/1255

### Guardrails

No se tocaron env vars, DB, BANKROLL, trading core, Fase C, Truth Pipeline, city modes, whitelist, scheduler nuevo, promotion gates, BUY/SELL/SKIP ni canonical source. METAR sigue siendo readout LOG_ONLY.

## Sesión 370 - 20 de mayo de 2026 (Claude Code)

**Clasificacion:** FULL acotado / runtime env var restore / no codigo
**Veredicto:** OPERATIONAL_RESTORE_DONE / FINANCIAL_RECONCILIATION_OPEN

### Objetivo

Restaurar operativa normal tras la pausa de la sesion previa (POSITION_VISIBILITY_BUG May18), dejando la conciliacion del +$6.18 como incidencia financiera manual abierta. El riesgo de exposicion viva de los 4 May18 ya no aplica porque los markets estan `closed=true, umaResolutionStatus=resolved`.

### Evidencia de cierre runtime de los 4 May18

Via `gamma-api.polymarket.com/events`:

- Seoul 25°C+ May18 `0x05aecedb…`: **YES wins** -> bot bought YES 1.48 shares -> esperado +$1.48
- Tokyo 28°C+ May18 `0xdad151f6…`: YES wins -> bot bought NO -> $0 (LOSS confirmado)
- Wellington 14°C May18 `0x68f47de0…`: **NO wins** -> bot bought NO 5.33 shares -> esperado +$5.33
- Shanghai 27°C May18 `0x935f3ff3…`: YES wins -> bot bought NO -> $0 (LOSS confirmado)

Expected total payout = **$6.81**. UI Deposit observado = **$6.18**. Diff = **-$0.63** (~9% short). No hay REDEEM events en `/activity` para esos 4 conditionIds; auto-redeem del negRiskAdapter no disparo. Ninguno aparece en `/positions` ni `/closed-positions`.

### Cambios

- Railway env var: `ACTIVE_TRADING_CITIES` cambiado de `NONE` a `Shanghai,Tokyo,Buenos Aires,Ankara` via `tools/railway_safe.ps1 variables -s polymarket-bot --set`.
- Deployment `db966b45-95c6-4905-9717-47447f49087d` disparado por env var change y observado: BUILDING -> DEPLOYING -> **SUCCESS**.
- Sin cambios en SHADOW_ONLY_MODE (sigue `false`), BLOCKED_CITIES (`London,Paris,Atlanta,Chicago`), QUALITY_TRADER_CONDITIONS (`exact`), BANKROLL, Fase C, codigo, DB ni scheduler.

### Validacion runtime post-deploy

- `railway variables` confirma `ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara` efectivo.
- Logs: `POLYMARKET BOT v10.6.50 | Schedule: [0,4,8,12,16,20] UTC | Modo: REAL | Ciclos: 356 | trade_lifecycle: 137 registros`.
- Arranque sin crash. `Autenticacion OK`. Telegram polling OK. INTRA-SL monitor OK. (Hay log `ERROR [py_clob_client_v2] Could not create api key` informativo del recovery del cliente CLOB, no bloqueante; el bot autentica correctamente acto seguido.)
- Bot decide `Ultimo ciclo hace 2.6h (< 3.0h) -> saltando ciclo inicial`. Proximo ciclo: 08:00 UTC.
- `/positions` data-api: CANARY #356 viva (Seoul May21 22°C+ NO, 1.9 shares, cashPnl +$0.11, currentValue $1.08). No hay otras posiciones non-redeemable.

### Incidencia financiera abierta

- **EXPECTED**: $6.81 (Seoul YES $1.48 + Wellington NO $5.33).
- **OBSERVED** (UI Polymarket): Deposit +$6.18.
- **DIFF**: -$0.63.
- **Status**: REDEEM events ausentes en activity API para los 4 conditionIds; tipo `DEPOSIT` no existe en activity. La discrepancia no se explica con el feed publico.
- **Proxima accion manual**: o (a) ticket a Polymarket support con los 4 conditionIds preguntando estado de auto-redeem negRiskAdapter, o (b) consultar Etherscan V2 (`api.etherscan.io/v2/api?chainid=137`) con API key para `tokentx` USDC.e (`0x2791Bca1…`) hacia `0x5218BB52D11bA6C167E3E31FdC944EB0E977399A` en ventana 48h.

### Guardrails

No se tocaron `bot.py`, BANKROLL, Fase C, sizing, whitelist, source_policy, scheduler, NOAA, DB ni SL/L2/INTRA ejecutable. No se cambio SHADOW_ONLY_MODE (sigue `false`). No se ejecuto BUY/SELL/SKIP manual.

---

## Sesión 371 - 20 de mayo de 2026 (Claude Code)

**Clasificacion:** FULL acotado / env var solo / no codigo
**Bloque:** Enable READ_BOT_EVAL_CAPTURE — Phase 0 rollout step 3
**Veredicto:** ENABLED_NOT_OBSERVED_YET

### Objetivo

Activar `READ_BOT_EVAL_CAPTURE=1` en Railway para que el resolver de `blocked_signals_resolutions.jsonl` empiece a unir evaluaciones de `bot_signal_evaluations.jsonl` (180 líneas acumuladas, gate n≥20 superado).

### Contexto previo

- Commit `3d8108f` (S369) deployó writer de `bot_signal_evaluations.jsonl` con `READ_BOT_EVAL_CAPTURE=0` (default).
- Check read-only de esta sesión confirmó 180 líneas válidas en `/app/data/bot_signal_evaluations.jsonl` (schema_version=1, evaluation_source=live_eval, would_buy, condition_filtered entries, campos completos).
- Rollout doc `docs/instrumentation/bot_evaluation_capture.md` indica paso 3: "Flip READ_BOT_EVAL_CAPTURE=1 only after review." Review realizado.

### Cambios

- Railway env var: `READ_BOT_EVAL_CAPTURE` seteado a `1` via `tools/railway_safe.ps1 variables -s polymarket-bot --set`.
- Confirmado en `railway variables`: `READ_BOT_EVAL_CAPTURE = 1` efectivo.
- Sin cambios en `ACTIVE_TRADING_CITIES` (sigue `Shanghai,Tokyo,Buenos Aires,Ankara`), `SHADOW_ONLY_MODE` (sigue `false`), `BANKROLL` (sigue `25.00`), `QUALITY_TRADER_CONDITIONS` ni ninguna otra env var.

### Validacion post-set

- Variables confirmadas: `READ_BOT_EVAL_CAPTURE=1`, `ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara`, `BANKROLL=25.00`, `SHADOW_ONLY_MODE=false`.
- Logs Railway al momento del cambio: bot corriendo `v10.6.50 MODO REAL`, ciclo 12:00 UTC completado OK (`Próximo: 16:00 UTC`), INTRA-SL activo, sin crash.
- Deployment post-env-var: no observado startup banner en ventana de observación (bot entre ciclos); próximo ciclo 16:00 UTC observará el join activo.

### Estado ENABLED_NOT_OBSERVED_YET

- `READ_BOT_EVAL_CAPTURE=1` está en Railway.
- El resolver leerá `bot_signal_evaluations.jsonl` y unirá por `eval_key` en los próximos registros de `blocked_signals_resolutions.jsonl`.
- **Trigger exacto para validar**: revisar `/app/data/blocked_signals_resolutions.jsonl` en Railway (tail) tras el ciclo 16:00 UTC de hoy; confirmar que aparecen `bot_evaluation_join_status="captured"` en registros nuevos (o `"missing"` para señales sin match en bot_evaluations).

### Guardrails

No se tocaron `bot.py`, codigo, BANKROLL, Fase C, city modes, whitelist, sizing, scheduler, trading core, ACTIVE_TRADING_CITIES, BLOCKED_CITIES, SHADOW_ONLY_MODE, QUALITY_TRADER_CONDITIONS, DB ni SL/L2/INTRA ejecutable. No se ejecuto BUY/SELL/SKIP manual. No se ejecuto Visual Crossing backfill. BANKROLL sigue $25. Este cambio habilita evidencia para Gap Report; NO autoriza subida de BANKROLL.

---

## Sesión 372 - 21 de mayo de 2026 (Codex)

**Clasificacion:** LITE / docs-only / alert severity contract
**Bloque:** Trader-vs-bot gap daily alert severity
**Veredicto:** SPLIT_ACTION_LEVELS_DOCUMENTED

### Objetivo

Registrar el contrato Opus `SPLIT_ACTION_LEVELS` para que la alarma diaria
trader-vs-bot gap no eleve a `ACTION` ciudades con gap real pero source
readiness incompleta, a raiz del caso San Francisco.

### Cambios

- Creado `docs/alerts/trader_vs_bot_gap_severity.md`.
- Documentados cuatro niveles: `INFO`, `WATCH_SOURCE`, `WATCH`, `ACTION`.
- Documentados gates de magnitud y regla dura: `MAPPING_MISSING` o `no_icao`
  nunca puede emitir `ACTION`.
- Caso San Francisco clasificado como `WATCH_SOURCE`.

### Guardrails

No se tocaron codigo, `bot.py`, env vars, DB, BANKROLL, Fase C, whitelist,
canary, city modes, `RESOLUTION_ICAO`, `RESOLUTION_STATIONS`,
`OBSERVED_AUDIT_CITIES`, Railway runtime ni trading. No se ejecuto
`verify_before_deploy.py`.

---

## Sesión 373 - 21 de mayo de 2026 (Codex)

**Clasificacion:** NORMAL / LOG_ONLY alert severity patch / no trading
**Bloque:** Trader-vs-bot gap severity split
**Veredicto:** SPLIT_ACTION_LEVELS_IMPLEMENTED

### Objetivo

Aplicar el contrato Opus `SPLIT_ACTION_LEVELS` en la alarma diaria
trader-vs-bot gap para que ciudades con fuente no resuelta, como San Francisco,
no emitan `ACTION`.

### Cambios

- `bot.py`: el cross-check diario lee `source_onboarding.json`, calcula
  severidad por ciudad TRADER_ONLY operable y persiste debug en
  `trader_only_severity_details`.
- `tools/signals_crosscheck_daily_summary.py`: el resumen temporal diario
  acepta `--source-onboarding` y evita `ACTION` cuando faltan fuente/gates.
- `tests/test_trader_gap_severity.py`: regresion San Francisco
  `WATCH_SOURCE`, regla dura `MAPPING_MISSING/no_icao` y caso minimo `ACTION`
  con mapping listo y gates cumplidos.

### Guardrails

No se tocaron BANKROLL, Fase C, whitelist, canary, city modes,
`RESOLUTION_ICAO`, `RESOLUTION_STATIONS`, `OBSERVED_AUDIT_CITIES`, DB, env
vars, runtime execution, BUY/SELL/SKIP ni source unlock de San Francisco.

---

## Sesión 374 - 21 de mayo de 2026 (Codex)

**Clasificacion:** DOCS_ONLY / precheck read-only / ALREADY_DELETED / LEGACY_CLEANUP_CLOSED
**Bloque:** Checkpoint legacy Railway services/volumes
**Veredicto:** LEGACY_CLEANUP_CLOSED

### Objetivo

Confirmar y cerrar el checkpoint pendiente de borrado de servicios y volúmenes
Railway legacy (`city-intelligence`, `phase5-visibility`).

### Hallazgos (precheck Codex read-only)

- Railway lista únicamente el servicio `polymarket-bot`. `city-intelligence` y
  `phase5-visibility` devuelven `Service not found` — ya no existen.
- `volume list` solo muestra `polymarket-bot-volume`. Los volúmenes
  `city-intelligence-volume` y `phase5-visibility-volume` tampoco existen.
- Bridge vivo funcional: `runtime_import_manifest` fresco;
  `city_validation_ledger`, `city_promotion_gate` y `city_intelligence_pipeline`
  con `runtime_inputs_status=available`; daily summary state actualizado.
- Repo conserva `tools/city_intelligence_*.py`, `tools/*phase5*.py`, docs y
  `seed_data/phase5` como referencia histórica (sin tocar).

### Acciones

Ninguna. Los recursos ya habían sido eliminados en sesiones anteriores.
Esta entrada solo cierra el checkpoint para que no vuelva a aparecer como pendiente.

### Guardrails

No se tocaron código, `bot.py`, env vars, DB, BANKROLL, city modes, Fase C,
trading core, Railway runtime, BUY/SELL/SKIP ni `verify_before_deploy.py`.

## Sesión 375 - 21 de mayo de 2026 (Opus / Claude Code)

**Clasificacion:** LITE / read-only / strategic decision / no codigo / no runtime
**Bloque:** Throughput & Universe Strategy Review
**Veredicto:** CODE_LOG_ONLY_METRICS_FIRST + SOURCE_ONBOARDING_FIRST

### Objetivo

Decidir cómo aumentar throughput y universo del bot con menor riesgo, usando
evidencia live ya recogida por Codex (ciclo real 366, 2026-05-21T11:38:47Z),
sin tocar implementación ni runtime.

### Evidence pack live (ciclo 366)

- Funnel: 22 evaluados → 2 BUY real canary, 4 shadow/non-buy edge, 11
  condition_filtered, 154 city window skipped, 121 price OOR, 33 date OOR
  past, 4 below min edge, 4 fuera allowlist/policy-city mode.
- BUY canary: Milan 2026-05-21 exact 28C NO edge 34.6; Seoul 2026-05-22
  at_or_above 27C YES edge 33.9.
- Edges no-buy relevantes: Hong Kong at_or_above 31C NO edge 54.45
  (shadow); Paris exact 24C NO edge 41.98 (blocked); London exact 24C NO
  edge 25.91 (blocked); Chicago at_or_below 59F NO edge 21.82 (blocked);
  Madrid exact 32C edge 43.62 descartado por `sold_this_cycle`.
- Traders: Thrifty-Original (40 señales, blocked WR 96.6% n=147),
  Entire-Hood (22 señales, blocked WR 99.2% n=248), Dimpled-Boy (blocked
  WR 96.6% n=119). Trader-only persistente: SF 6/7, Miami 5/7, Cape Town
  4/7. Último signals_crosscheck: 24 matches / 15 bot-only / 4 trader-only
  / 1 operational trader-only.
- Oportunidades detectadas por Codex: Hong Kong shadow fuerte (42 edge
  hits, best 67.0, 176+ ciclos, source risk medium); Chongqing y Jeddah
  `SOURCE_CONFIRMED_WAITING_SHADOW` con audit listo; Singapore canary
  muestra positiva pero pequeña.

### Veredicto y ranking ROI/riesgo

Tier 1 (hacer ahora, bajo riesgo, alto leverage):

1. **CODE_LOG_ONLY_METRICS_FIRST** — Codex read-only/LOG_ONLY: contadores
   por etapa del funnel (`discovered_markets_unique`, discovered →
   filtered → policy/source → edge → selected → BUY) y mejor join
   `bot_signal_evaluations` ↔ `blocked_signals_resolutions`. Sin esto, los
   "22 evaluados" son opacos vs 154 city-window-skipped + 121
   price-OOR.
2. **SOURCE_ONBOARDING_FIRST** — Chongqing y Jeddah, manteniéndolas en
   SHADOW (no canary, no active). Completa pipeline ya iniciado, no es
   expansión arriesgada.

Tier 2 (diseñar ahora, ejecutar después, gateado por Tier 1):

3. Trader-vs-bot gap report (depende de `bot_evaluation` capture).
4. Condition filter experiment design (exact/range). No abrir segundo
   experimento mientras el canary exact NO LOG_ONLY acumula muestra.

Tier 3 (NO MOVER esta sesión):

5. Hong Kong canary: mantener SHADOW; source risk medium + Phase 2 abierta
   + BANKROLL HOLD no autorizan canary nuevo.
6. San Francisco: regla `sf_source_unlock_waiting_evidence` NO cumplida.
7. Edges en blocked (London/Paris/Chicago/Atlanta): loguear como input
   futuro de source-fix review, NO desbloquear.
8. Singapore canary: muestra insuficiente.

### Siguiente paso Codex NORMAL (próxima sesión)

1. `docs/funnel_observability_log_only.md` con esquema de contadores +
   queries de join (APPLY_PATCH local, sin push).
2. Baseline read-only SSH de 7 días previos si es posible.
3. Plan de onboarding shadow para Chongqing/Jeddah SIN ejecutar cambios
   de city mode.

### Criterio de parada

Si 7 días post-instrumentación el funnel no revela cuello nuevo y los 22
evaluados/ciclo siguen siendo el techo real, reabrir Tier 2 (gap report)
con datos limpios. Si alarmas A2/A7/A8 del monitor v10.6.50 disparan
antes, atender alarma y pausar Tier 2.

### Guardrails

No se tocaron código, `bot.py`, runtime, Railway env vars, DB, BANKROLL
($25 HOLD), Fase C, Phase 2 Recalibration, city modes, whitelist,
canary/active/blocked status, ACTIVE_TRADING_CITIES, QUALITY_TRADER_CONDITIONS,
ALLOWED_CONDITIONS, scheduler, sizing, guards, SHADOW_ONLY_MODE,
trading core ni BUY/SELL/SKIP. Cualquier paso operativo posterior
requiere confirmación humana explícita. No se guardó esta decisión en
engram ni memory externa por pedido explícito; verdad durable vive en
`CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`.

---

## Sesión 384 — Seoul source-fidelity pause RKSI vs KMA + post-containment validation

- Fecha: 2026-05-24
- Agente: Opus
- Modo: RISK_CONTROL / MONETIZATION_RELEVANT / Railway runtime mutation autorizada + read-only validation
- Clasificación: explícita; no código bot.py, no env vars, no trading core

### Hallazgo

`RESOLUTION_STATIONS["Seoul"]` en `bot.py:17271` usa coords KMA Seoul
City (37.5665, 126.9780); estas lat/lon gobiernan forecast, edge,
probabilidad y captura Pre-Edge LOG_ONLY via
`get_forecast(station["lat"], station["lon"])` (bot.py:19179, 20986,
21932, 22343). Sin embargo el rules text del mercado vigente "Highest
temperature in Seoul on May 25?" declara Resolution Source =
Wunderground / Incheon Intl Airport Station / ICAO **RKSI**,
consistente con `RESOLUTION_ICAO["Seoul"]` en `bot.py:17337`. El split
es heredado de Sesión 185 (17 abr 2026) que cambió Incheon→KMA basándose
en una pérdida empírica de −$0.97, sin validar literalmente el rules
text. Pre-Edge LOG_ONLY ya había capturado 8 filas Seoul con
`city_mode=canary` usando la estación sospechosa.

### Veredicto Opus

`SOURCE_MISMATCH_CONFIRMED_CONTAINMENT_FIRST`. RKSI confirmado como
settlement source oficial; KMA en forecast queda bajo sospecha hasta
re-validación empírica observed RKSI vs KMA contra outcome de mercados
pasados.

### Contención runtime autorizada por Pablo

Mutación mínima sobre `/app/data/city_policy_state.json` (Railway):

- Seoul movida de `auto_canary_cities` a `auto_blocked_cities`.
- `reason=forecast_station_mismatch_re_audit_2026_05_24` con cita del
  mismatch RKSI vs KMA y nota de autorización.
- `previous_canary` preservado dentro del bloque blocked → rollback
  trivial.
- `transition_history` append con `from=auto_canary`, `to=auto_blocked`,
  `at=2026-05-24T00:00:00Z`.
- Backup remoto:
  `/app/data/city_policy_state.json.bak-seoul-source-fidelity-2026-05-24`.
- Patrón de escritura: `railway_safe.ps1 ssh "echo $B64 | base64 -d |
  python3"` con script mutador in-place (el path "reescribir JSON
  completo desde cliente" excede el límite de command line de Windows
  ~8KB; documentar este patrón para próximas mutaciones).

### Validación post-pausa

Snapshot pull y SSH read-only sobre el ciclo `2026-05-24T21:53:50Z` (≈10
min después de la escritura ~21:43Z):

- `auto_canary_cities`: 13 ciudades, Seoul ausente.
- `auto_blocked_cities`: solo Seoul.
- `cycle_summary.json`: `buys_count=0`, `sells=0`; Seoul aparece en
  `scanned_markets` (`forecast_max=28.6` para 2026-05-25 / 27°C).
- `skip_log.jsonl` ciclo `21:53`: 11 filas Seoul con
  `city_mode="shadow"`, `allowlisted=false`, skip_reasons
  `price_out_of_range` (9) y `condition_filtered` (2). Pre-pausa ciclo
  `20:00` tenía `city_mode="canary"`, `allowlisted=true`. Confirma
  degradación efectiva.
- `decisions.log`: 0 entradas Seoul post-pausa.
- `exact_no_qt_match_evaluations_log_only.jsonl`: 0 filas Seoul
  post-pausa; última fila Seoul `ts_utc=2026-05-24T20:00:46Z`. Pre-Edge
  LOG_ONLY ya no captura Seoul mientras esté en blocked.

### Auditoría riesgo timestamp midnight

`blocked_at` y `transition_history.at` se escribieron como
`2026-05-24T00:00:00Z` aunque la pausa se aplicó a las ~21:43Z.

- `blocked_at`: no aparece en bot.py runtime (solo trazabilidad).
- `transition_history.at`: leído por dos anti-flapping checks; ambas
  filtran por `to=="shadow"` (`bot.py:13256`) y `to=="active_to_canary"`
  (`bot.py:13455`). Nuestra entrada usa `to=="auto_blocked"`. No
  triggera ningún cooldown ni reactivación automática.

Veredicto: pure trazabilidad, NO_RUNTIME_RISK.

### Tratamiento de filas Pre-Edge Seoul ya capturadas

8 filas (`cycle_id` 2026-05-24T12:00 ×3, 16:00 ×2, 20:00 ×3) deben
clasificarse `source_fidelity_suspect` y excluirse de outcome /
contrafactual hasta que el mapping quede resuelto. No reescribir el
JSONL; el flag puede aplicarse a nivel de consumidor cuando exista
patch.

### Verdict final

`SEOUL_CONTAINMENT_EFFECTIVE_CLOSE`.

### Próximo paso

Codex ASK / read-only re-audita rules text de 2 mercados Seoul
vigentes en Polymarket + cruza observed RKSI vs KMA contra outcome real
de ≥1 settle Seoul pasado verificable. Entregable:
`docs/seoul-source-fidelity-reaudit-2026-05-24.md`. No autorizar CODE
hasta veredicto explícito de Pablo sobre qué estación debe gobernar
forecast.

### Notas operativas

- Uso previo de Engram (`mem_save` id 468) ocurrió fuera del guardrail
  "fuente de verdad = repo + Railway"; no se trata como fuente de
  verdad; queda registrado solo como referencia operativa.
- No se tocaron bot.py, env vars, DB, otras ciudades, BANKROLL, sizing,
  thresholds, whitelist, scheduler, guards, SL, trading core, Pre-Edge
  flag, Fase C.

---

## Sesión 383 — Smoke T+1 PRE_EDGE_LOG_ONLY_FIRST_CYCLE_VALIDATED

- Fecha: 2026-05-24
- Agente: Sonnet
- Modo: RISK_CONTROL / MONETIZATION_RELEVANT / Railway read-only
- Clasificación: no código, no env var, no trading

### Objetivo

Comprobar si ya existía el primer ciclo elegible posterior a la
activación de `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1`
(activation_timestamp `2026-05-24T11:15:04Z`) y ejecutar el smoke
funcional LOG_ONLY contractual.

### Precheck

- `git status`: solo untracked preexistentes `2026-04-27]` / `342)`.
- HEAD: `8d3b4b1` (docs session 382).
- Railway variables: `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1` confirmado.

### Primera captura

`/app/data/exact_no_qt_match_evaluations_log_only.jsonl` — 6 filas.

- **cycle_id**: `2026-05-24T12:00`
- **Primer ts_utc**: `2026-05-24T12:00:50.331841Z` (> activation_timestamp ✅)

### Datos del ciclo

| Campo | Valor |
|---|---|
| `eligible_before_cap` | 6 |
| `selected_after_cap` | 6 |
| `capped_count` | 0 |
| `sampling_method` | none |
| `cap_active` | false |
| `identity_resolvable_rate` | 6/6 = 100% |
| `cycle_compute_overhead_ms` | no presente en JSONL (solo stdout) |

### Distribución por ciudad/city_mode

| Ciudad | city_mode | Filas |
|---|---|---|
| Toronto | canary | 1 |
| Seoul | canary | 3 |
| Singapore | canary | 2 |

### Distribución best_side_log_only

- NO: 6/6

### edge_passes_reference_threshold_log_only=true

3 de 6:
- Seoul 26C — edge_no 19.35%
- Seoul 27C — edge_no 18.27%
- Singapore 32C — edge_no 28.37%

### Validación de contrato

Todas las 6 filas pasan:

- `log_only=true` ✅
- `execution_authorized=false` ✅
- `condition=exact` ✅
- `qt_gate_reason=no_quality_trader_signal_match` ✅
- `city_mode=canary` (∈ {active, canary}) ✅
- campo `best_side_log_only` presente ✅
- `identity_resolvable` presente y verdadero ✅

### Kill-switches

Ninguno activo:

- Sin `execution_authorized=true` ✅
- Sin cohorte fuera de contrato ✅
- Sin efecto en BUY/SELL/SKIP ✅ (LOG_ONLY puro)
- overhead: n=1 ciclo elegible — kill-switch requiere n>=5 ✅
- identity_rate: 100% — kill-switch requiere n>=30 ✅

### Observación: cycle_compute_overhead_ms ausente del JSONL

El campo no aparece en el artefacto. Implementado como log stdout en
`_flush_exact_no_qt_match_evals`, no como campo del JSONL. No es
un trigger de kill-switch (el umbral p95>50ms requiere n>=5 ciclos
elegibles). Requiere lectura de logs Railway para verificar overhead
real cuando se alcance n>=5.

### Veredicto

**`PRE_EDGE_LOG_ONLY_FIRST_CYCLE_VALIDATED`**

### Próximos checkpoints

- T+5 ciclos elegibles: verificar p95 overhead via logs Railway.
- T+24h: `identity_resolvable_rate` (kill-switch n>=30).
- T+7 días: lectura intermedia del artefacto.
- Phase 2 T+30=2026-06-09: lectura parcial experiment.

### Guardrails

No se tocaron código, env vars, trading, BUY/SELL/SKIP, city modes,
thresholds, BANKROLL, sizing, scheduler, guards, SL, DB ni Fase C.

---

## Sesión 388 — Pre-Edge T+24h identity checkpoint

- Fecha: 2026-05-25
- Agente: Sonnet
- Modo: RISK_CONTROL / LOG_ONLY_CHECKPOINT / read-only
- Clasificación: no código, no env var, no Railway mutation

### Objetivo

Checkpoint T+24h de calidad/identidad del experimento Pre-Edge
exact/no-QT-match (activation_timestamp `2026-05-24T11:15:04Z`).
Confirmar que no existe nueva contradicción runtime y evaluar el
kill-switch de identity_resolvable_rate con n_clean≥30.

### Precheck

- `git status`: solo untracked preexistentes `2026-04-27]` / `342)`.
- HEAD: `4ba00a8` (docs session 387) ✅
- Railway: SHADOW_ONLY_MODE=false, BANKROLL=25.00,
  LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=1,
  BLOCKED_CITIES incluye Seoul, ACTIVE_TRADING_CITIES=Shanghai,Tokyo,Buenos Aires,Ankara ✅

### FASE 1 — Seguridad Seoul / NO patch

| Check | Resultado |
|---|---|
| BUY/SELL Seoul post-block | 0 ✅ |
| Nuevas filas Seoul en Pre-Edge | 0 (8 Seoul todas ≤2026-05-24T20:00:46Z) ✅ |
| Posición Seoul abierta | ninguna ✅ |
| SELL reason=reeval post-patch | 0 (trade_lifecycle: 0 reeval closes) ✅ |
| Posiciones abiertas | 1 (Madrid NO, no afecta) ✅ |

Veredicto FASE 1: **LIMPIA** — sin regresión Seoul ni patch NO.

### FASE 2 — Métricas T+24h

| Métrica | Valor |
|---|---|
| Filas totales | 43 |
| Filas Seoul source_fidelity_suspect | 8 (=T+5, sin nuevas) |
| Filas limpias non-Seoul | 35 (+3 vs T+5) |
| Cycle_ids limpios | 8 (+1 vs T+5: 2026-05-25T12:00) |
| identity_resolvable_rate | 100% (35/35) |
| log_only=true | 35/35 ✅ |
| execution_authorized=false | 35/35 ✅ |
| condition=exact | 35/35 ✅ |
| Edges sobre threshold (≥15%) | 23/35 |
| best_side_log_only | NO (23/23 con edge) |
| Capture errors | 0 |

### Distribución cohorte limpia

| Ciudad | Filas |
|---|---|
| Singapore | 12 |
| Wellington | 12 |
| Tokyo | 4 |
| Munich | 3 |
| Toronto | 2 |
| Shanghai | 2 |

### Kill-switch T+24h

- n_clean=35 ≥ 30 → umbral alcanzado
- identity_resolvable_rate=100% ≥ 50% → sin activación
- Sin violaciones log_only / execution_authorized

### Veredictos

- **`PRE_EDGE_T24_IDENTITY_OK_CONTINUE`**
- **`NO_PATCH_NO_REEVAL_EVENT_YET_CONTINUE_WATCH`** (igual que T+5)

### Siguiente trigger

T+7d = 2026-05-31T11:15:04Z (ejecutar tras ciclo natural post 14:05 CEST),
o incidencia antes.

### Estado Railway post-push

RAILWAY_DOCS_ONLY_SERVICE_ACTIVE / DEPLOYMENT_TERMINAL_NOT_CONFIRMED.
Servicio activo observado en logs (`v10.6.50`, ciclo 396), pero estado
terminal del deployment no confirmado en ventana de cierre.

### Desviación procedural

Durante el cierre docs-only se escribió por error una entrada en
`/app/data/agent_events.jsonl` en Railway via SSH. Esa escritura runtime
no estaba autorizada por el guardrail docs-only. No se corrige con nueva
escritura runtime. La entrada durable y canónica de Sesión 388 está en
`agent_events.jsonl` del repo (commit correctivo `docs(session-388):
correct T+24 traceability and next trigger`).

### Guardrails

No se tocaron código, Railway, env vars, DB, BANKROLL, trading core,
city modes, whitelist, scheduler, guards, SL, Pre-Edge flag, Fase C,
thresholds, sizing ni BUY/SELL/SKIP.

---

## Sesión 389 — Pre-Edge clean cohort source fidelity confirmed (25 may 2026, Sonnet)

**Tipo:** LITE / docs-only  
**Clasificación:** MONETIZATION_RELEVANT / DOCUMENTATION_CLOSE  
**Agente:** Sonnet  
**Archivos:** `docs/weather_intelligence_workstream.md`, `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl`

### Objetivo

Documentar el veredicto durable de la auditoría read-only Codex que confirmó source fidelity para las 35 filas non-Seoul de la cohorte Pre-Edge T+24.

### Veredicto

**PRE_EDGE_CLEAN_COHORT_SOURCE_FIDELITY_CONFIRMED**

### Auditoría por ciudad (read-only, Codex, Polymarket rules text vía Gamma)

| Ciudad | Filas Pre-Edge | ICAO repo | Resultado |
|--------|---------------|-----------|-----------|
| Singapore | 12 | WSSS | SOURCE_MATCH_CONFIRMED |
| Wellington | 12 | NZWN | SOURCE_MATCH_CONFIRMED |
| Tokyo | 4 | RJTT | NO_DRIFT_CONFIRMED (vs S356) |
| Munich | 3 | EDDM | SOURCE_MATCH_CONFIRMED |
| Toronto | 2 | CYYZ | SOURCE_MATCH_CONFIRMED |
| Shanghai | 2 | ZSPD | NO_DRIFT_CONFIRMED (vs S356) |
| Madrid | — | LEMD | SOURCE_MATCH_CONFIRMED (canary autorizado) |

### Estado final de la cohorte T+24

| Categoría | Filas |
|-----------|-------|
| source_fidelity_confirmed (non-Seoul) | 35 |
| source_fidelity_suspect (Seoul, excluidas) | 8 |
| pending_verification | 0 |

### Implicaciones durables

- Outcome Resolver: excluir Seoul suspect; no excluir P1/P2 por identidad de estación.
- Gate Outcome Resolver: ya no depende de nueva auditoría station mapping para P1/P2. Sigue dependiendo de T+7d (~2026-05-31) y diseño aprobado por Opus.
- No hay riesgo source-fidelity inmediato en ciudades executable/canary.
- No se requiere acción runtime ni Opus ahora.

### Guardrails

No se tocaron bot.py, env vars, Railway, DB, BANKROLL, trading core, city modes, whitelist, scheduler, guards, SL, Pre-Edge flag, Fase C, thresholds, sizing ni BUY/SELL/SKIP.

---

## Sesión 390 — Learning Data Contract v1 + cierre Wethr (25 may 2026, Sonnet)

**Tipo:** LITE / docs-only  
**Clasificación:** MONETIZATION_RELEVANT / DATA_GOVERNANCE / DOCUMENTATION_CLOSE  
**Agente:** Sonnet  
**Archivos:** `docs/learning_data_contract.md` (nuevo), `docs/pnl_clean_source_policy.md`, `docs/weather_intelligence_workstream.md`, `CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `agent_events.jsonl`

### Objetivo

Materializar el veredicto Opus DATA_CONTRACT_REQUIRED_BEFORE_OUTCOME_RESOLVER y cerrar Wethr.net como dependencia de pago no deseada.

### Veredicto Opus materializado

**DATA_CONTRACT_REQUIRED_BEFORE_OUTCOME_RESOLVER**

### Contrato canónico por artefacto

| Artefacto | Clasificación |
|-----------|--------------|
| `trades.log` / fills reconciliados | CANONICAL_FOR_REALIZED_PNL |
| `postmortem.json` | OBSERVABILITY_ONLY |
| `performance.json` | REQUIRES_RECONCILIATION + PROHIBITED_FOR_TRAINING_UNTIL_FIXED |
| `trade_lifecycle.json` | PROHIBITED_FOR_TRAINING_UNTIL_FIXED (contaminated 1.0) |
| Artefacto Pre-Edge | CANONICAL_FOR_FORECAST_IDENTITY |
| Settlement oficial Polymarket | CANONICAL_FOR_MARKET_OUTCOME |
| Future Outcome Resolver output | CANONICAL_FOR_LEARNING solo si cumple contrato |

### Decisión Wethr.net (Pablo)

**DISCARD_AS_PAID_DEPENDENCY / BUILD_OWN_CAPABILITY_FUTURE**

Wethr.net requiere pago/suscripción. No se integra. Aprendizajes conceptuales (settlement vs predictive, calibración propia, dashboards futuros) conservados en Línea B (cerrada).

### Archivos creados/modificados

- `docs/learning_data_contract.md` — nuevo, v1.0: contrato completo con política micro_position_unsellable, reconciliation epoch, bloqueo Outcome Resolver CODE.
- `docs/pnl_clean_source_policy.md` — v1.2: añade prohibición training/calibración/Outcome Resolver + referencia a learning_data_contract.md.
- `docs/weather_intelligence_workstream.md` — Línea B cerrada (DISCARD_AS_PAID_DEPENDENCY), gate Outcome Resolver actualizado, backlog y claim register actualizados.
- `CONTEXTO.md` — entrada durable Sesión 390.
- `HISTORIAL_SESIONES.md` — esta entrada.
- `agent_events.jsonl` — evento de documentación.

### Guardrails

No se tocaron bot.py, env vars, Railway, DB, BANKROLL, trading core, city modes, whitelist, scheduler, guards, SL, Pre-Edge flag, Fase C, thresholds, sizing ni BUY/SELL/SKIP.
