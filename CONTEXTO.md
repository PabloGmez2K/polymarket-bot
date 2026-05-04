# CONTEXTO DEL PROYECTO — Bot Polymarket


**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 289 - Blocked signals low-fidelity audit level, Codex)
**Sesion 289 (1 may 2026, Codex):** Patch pequeno de semantica/copy para `Blocked signals — auditoria diaria`. Diagnostico: con `has_v2=true` pero muestra v2 OUT insuficiente (`OUT resolved <50`), el builder podia caer al fallback v1 fuera de whitelist y emitir `Nivel: ACTION` aunque el soporte fuese legacy con `settlement_fidelity_status` unknown/unverified y sin accion real de trading/policy. Cambio: en ese caso el nivel baja a `WATCH_AUDIT`, el mensaje conserva `No accionable para trading. Auditoría de datos — sin cambios en whitelist ni city modes sin revisión separada.`, y el fallback legacy de emergencia tampoco eleva a `ACTION` si detecta v2 de baja muestra/baja fidelidad. `verify_before_deploy.py` suma guardrail anti-regresion. Validacion: `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; smoke sintetico del helper devuelve `WATCH_AUDIT`; `python verify_before_deploy.py` pasa **1074/1074**; `git diff --check` OK con avisos LF/CRLF de Windows; `tools/blocked_signals_audit.py --help` OK, sin dry-run real por no existir `data/blocked_signals_resolutions.jsonl` local. No se toca trading core, whitelist, city modes, policy, BANKROLL, sizing, scheduler, SL, Unsellable Guard, reglas de riesgo, env vars, Truth Pipeline/Fase C ni deploy.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 288 - Traders Intelligence READY copy post-v1, Codex)
**Sesion 288 (1 may 2026, Codex):** Patch pequeno de observabilidad/copy para evitar ruido repetido en la alarma `Traders Intelligence` cuando los checks de v1 ya estan READY. Diagnostico: `tools/traders_intelligence_daily_summary.py` seguia emitiendo la instruccion `Abrir v1 minimo...` aunque la v1 minima ya existe desde `bb7586d` (`tools/traders_intelligence_snapshot.py` + `docs/traders-intelligence-v1-snapshots.md`). Cambio: el summary detecta la existencia de tool+doc y, si readiness esta listo, cambia el copy a `V1 minima implementada. Siguiente paso: ejecutar python tools/traders_intelligence_snapshot.py con signals.json fresco para acumular snapshots`; el fallback para repo sin v1 ya no usa el literal `Abrir v1 minimo`. `verify_before_deploy.py` suma guardrail para impedir la regresion. Validacion: `python tools/check_python_syntax.py tools/traders_intelligence_daily_summary.py verify_before_deploy.py` OK; dry-run del summary OK; `python verify_before_deploy.py` pasa **1073/1073**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, NOAA/Open-Meteo, policy, reglas de riesgo, env vars ni automatizacion. Deploy manual: NO.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 287 - Traders Intelligence v1 snapshots pseudo-lifecycle, Codex)
**Sesion 287 (1 may 2026, Codex):** Patch acotado de tooling/observabilidad para abrir v1 minimo de Traders Intelligence tras readiness `usable_signal`: se crea `tools/traders_intelligence_snapshot.py`, CLI manual stdlib-only que lee `data/runtime_import/signals.json`, filtra solo `Thrifty-Original` y `Entire-Hood` en `Houston`, `Los Angeles`, `Manila` y `Miami`, archiva snapshots filtrados bajo `data/traders_intelligence/snapshots/<run_id>.json`, escribe reportes `data/traders_intelligence/reports/<run_id>.json` y mantiene audit idempotente `data/traders_intelligence/pseudo_lifecycle_runs.jsonl`. El pseudo-lifecycle externo emite solo `appeared`, `still_present`, `disappeared_apparent` y `reappeared`, con caveat explicito de que desaparicion aparente no es salida confirmada. Se documenta uso en `docs/traders-intelligence-v1-snapshots.md`, se actualiza `docs/traders-intelligence-spec.md`, `.gitignore` ignora la ruta runtime y `verify_before_deploy.py` suma guardrails de scope/manual-only/no trading/policy. Validacion: `python tools/check_python_syntax.py tools/traders_intelligence_snapshot.py verify_before_deploy.py` OK; `python tools/traders_intelligence_snapshot.py --dry-run --run-id validation-dry-run` OK (`n_current_signals=3`, `appeared=3`); smoke real con `validation-v1-smoke` OK y segunda corrida `validation-v1-smoke-2` marca `still_present=3`; input faltante falla limpio con mensaje claro; `python verify_before_deploy.py` pasa **1072/1072**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca `bot.py`, trading core, NOAA/Open-Meteo, BANKROLL, sizing, whitelist, city modes, scheduler, policy, reglas de riesgo, env vars, Truth Pipeline/Fase C ni automatizacion de trading. Deploy manual: NO.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 286 - SL_intra Hazard Monitor L2 LOG_ONLY, Codex)
**Sesion 286 (1 may 2026, Codex):** Implementacion acotada de L2 Hazard Monitor SL_intra como observador puro LOG_ONLY y default OFF. `bot.py` agrega env vars seguras `SL_INTRA_HAZARD_MONITOR_ENABLED=0`, `SL_INTRA_HAZARD_MONITOR_LOG_ONLY=1`, thresholds `deteriorating=-50%`, `deep=-70%`, `terminal=-85% o current_value<=0.30`, `collapsed cur_price<=0.05 durante >=2 ciclos`, audit independiente `data/sl_intra_hazard_monitor_audit.json`, idempotencia por `token_id+tier`, Telegram LOG_ONLY con cooldown propio y scope literal bajo L1 via `_sl_intra_guard_should_skip(condition, days_ahead)`. Con ENABLED=0 no hace load/save/Telegram/audit. `verify_before_deploy.py` suma checks de defaults, scope L1, tiers, collapsed 2 ciclos, idempotencia, Telegram/cooldown independiente y ausencia de side-effects ejecutables. Validacion: `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; `python verify_before_deploy.py` **1065/1065**; `git diff --check` OK. No se cambia L0/L1, `_sl_intra_guard_should_skip`, STOP_LOSS_PCT, BANKROLL, sizing, whitelist, city modes, scheduler, NOAA, MIN_EDGE, take_profit, Unsellable Guard, execute_trade, track_trade, trade_lifecycle, sell_lock ni `sl_intra_guard_audit.json`. Env vars cambiadas en produccion: NO; queda OFF hasta activar `SL_INTRA_HAZARD_MONITOR_ENABLED`.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 285 - SL_intra Hazard Monitor L2 design, Sonnet)
**Sesion 285 (1 may 2026, Sonnet):** Documentacion de decision de riesgo SL_intra post-revision Opus (caso Wellington vs Paris). Veredicto L0/L1: intocables. Wellington no es bug del guard v10.6.40: es laguna de cobertura — el guard protege falsas salidas tipo Paris (exact+days<=1) pero deja sin observacion la degradacion terminal tipo Wellington. Decision durable: L2 Hazard Monitor LOG_ONLY puro, scope posiciones bajo guard exact+days<=1, tiers `deteriorating`/`deep`/`terminal`/`collapsed`, idempotencia por token+tier, auditoria independiente sin tocar sell_lock/trade_lifecycle/Unsellable Guard. L3/reality-check ejecutable diferido hasta >=14 dias + >=8 tokens resueltos con trazas L2. Metrica decisiva futura: Net P/L 30d contrafactual por tier. Artefactos: `docs/sl_intra_hazard_monitor_design.md`, entrada HISTORIAL S285, entrada agent_events.jsonl. No se toca bot.py, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, env vars, STOP_LOSS/TP, Unsellable Guard, sell_lock ni trade_lifecycle. No deploy.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 284 - P/L Reconciliation WATCH_RISK, Codex)
**Sesion 284 (1 may 2026, Codex):** Triage read-only de `P/L Reconciliation 2026-04-30`. Clasificacion final: `WATCH_RISK`. La alarma sigue siendo util, pero el P/L 7d positivo actual no debe leerse como mejora limpia ni autoriza subir bankroll: el dry-run local marca lifecycle 7d `+$23.32`, con `+$23.36` n=11 de batch antiguo `market_resolved` dentro de la ventana; descontado ese batch, el P/L reciente queda aprox. plano/negativo. `Wallet Snapshot` sigue acumulando baseline 7d y no alimenta aun `pnl_reconciliation_alert.py`; `Bankroll Scaling` sigue bloqueado/manual-only y `BANKROLL` permanece en `$25`. No se implementa patch ahora porque la alerta ya avisa que no se interprete el 7d como mejora limpia, pero queda como posible ajuste futuro mostrar `pnl_7d_clean_excluding_old_resolution_batch` y estado Wallet Snapshot/readiness dentro del mensaje. No se toca codigo, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, riesgo, Railway env, commit, push ni deploy.

**Ultima actualizacion:** 1 de mayo de 2026 (Sesion 283 - Slot Monetization Review NO_ACTION 04h, Codex)
**Sesion 283 (1 may 2026, Codex):** Patch acotado de alert hygiene para `Slot monetization review`. `maybe_evaluate_slot_monetization()` mantiene la evaluacion diaria y actualiza `alerts_state`, pero suprime Telegram accionable cuando `04h` esta `validated/keep`, tiene `same_day_buys>0`, `buy_rate` y `same_day_buy_rate` positivos, sin execution rejects relevantes y solo con residuales benignos `buy_min_size`/`buy_min_notional` no recurrentes. Sigue alertando si `04h` baja de sano, deja de convertir, aparece un execution reject relevante, hay exceso de rechazos benignos recurrentes o un slot habilitado como `23h` vuelve a ser candidato accionable. `verify_before_deploy.py` suma fixtures para el caso sano silencioso y para regresion con `clob_reject`. Validacion: `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; `python verify_before_deploy.py` pasa **1047/1047**. No se cambia trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, SKIP real, Railway env, push ni deploy.

**Última actualización:** 1 de mayo de 2026 (Sesión 282 - Unsellable Guard Monitor diario, Codex)
**Sesión 282 (1 may 2026, Codex):** Patch acotado de observabilidad read-only para el Unsellable Guard v1 LOG_ONLY. Se crea `tools/unsellable_guard_monitor.py`, stdlib-only, que lee `data/skip_log.jsonl` y rotados `skip_log.YYYY-MM-DD.jsonl`, filtra candidatos `skip_reason="unsellable_guard_candidate"` + `guard_version="unsellable_v1"` + `guard_action="would_skip"`, calcula totales 24h/7d/all-time, top ciudades/condiciones, promedios de `size_ratio`/`price_at_guard`, ejemplos y detecta `ACTION_SAFETY` si aparece `unsellable_liquidity_guard` o `guard_action="skipped"`. `bot.py` integra el monitor en `run_observability_alerts()` con `UNSELLABLE_GUARD_MONITOR_ENABLED=1`, hora default `PNL_RECONCILIATION_HOUR_UTC`, timeout 30s, wrapper JSON fail-safe, formatter Telegram y anti-spam en `alerts_state.json` (`unsellable_guard_*`); no envía Telegram en `OK`, sí en `WATCH`/`ACTION_REVIEW`/`ACTION_SAFETY`, siempre con copy manual-only: revisión manual/Opus antes de promoción y no activar SKIP automáticamente. `verify_before_deploy.py` suma checks de tool/env/wrapper/hook/state, fixtures `OK`/`WATCH`/`ACTION_REVIEW`/`ACTION_SAFETY` y guardrails de defaults dormidos. `docs/unsellable-liquidity-guard-v1.md` documenta el monitor diario. Validación: `python tools/check_python_syntax.py bot.py verify_before_deploy.py tools/unsellable_guard_monitor.py` OK; `python tools/unsellable_guard_monitor.py --data-dir data --json` OK (`OK`, 0 candidates en checkout local sin skip_log); `python tools/unsellable_guard_monitor.py --data-dir data --markdown` OK; `python verify_before_deploy.py` pasa **1045/1045**; `git diff --check` OK con avisos LF/CRLF de Windows. No se cambia trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, STOP_LOSS/TP, `UNSELLABLE_GUARD_ENABLED`, `UNSELLABLE_GUARD_LOG_ONLY`, Truth Pipeline/Fase C, Railway ni deploy. Sin commit ni push.

**Última actualización:** 30 de abril de 2026 (Sesión 281 - Unsellable Liquidity Guard v1 LOG_ONLY, Codex)
**Sesión 281 (30 abr 2026, Codex):** Patch acotado `LOG_ONLY_FIRST` del Unsellable Liquidity Guard v1 aprobado por Opus. `bot.py` añade defaults dormidos `UNSELLABLE_GUARD_ENABLED=0`, `UNSELLABLE_GUARD_LOG_ONLY=1`, `UNSELLABLE_GUARD_VERSION="unsellable_v1"`, helpers puros y hook en `main()` justo antes de `execute_trade()`, despues de sizing/presupuesto/ajuste minimo notional. Trigger: `condition in {"exact","range"}`, `days_ahead==0`, `0.10<=price_at_guard<=0.65`, `size_ratio=amount/effective_bankroll>=0.15`; `price_raw` es solo forensics None-safe. En LOG_ONLY registra `skip_reason="unsellable_guard_candidate"` + `guard_action="would_skip"` sin bloquear compra ni enviar Telegram por candidato; el path real `skip_reason="unsellable_liquidity_guard"` + `guard_action="skipped"` queda dormido hasta `LOG_ONLY=0` con signoff Opus. `verify_before_deploy.py` suma checks funcionales/defaults/guardrails y se crea `docs/unsellable-liquidity-guard-v1.md`. Validacion: `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; `python verify_before_deploy.py` pasa **1032/1032**; `git diff --check` OK con avisos LF/CRLF de Windows. No se cambia BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, STOP_LOSS/TP, Truth Pipeline/Fase C, Railway ni `SL_INTRA_GUARD_*`. Sin push ni deploy manual.

**Última actualización:** 30 de abril de 2026 (Sesión 280 - Bankroll Monitor Phase 1 proxy copy, Codex)
**Sesión 280 (30 abr 2026, Codex):** Patch acotado de copy/tooling tras revision read-only de `Drawdown Alert` + `Bankroll Scaling Monitor`. Se confirma que el bloqueo `$25 -> $35` es correcto: WR limpio `36.7%` y drawdown ultimos 5 cierres `-$3.89`; la ventana es reciente y limpia, sin batch antiguo, pending exits ni contaminacion legacy. Patron WATCH_RISK: dos exact con `micro_position_unsellable` explican el drawdown principal (`Munich 20C Apr27 NO -$2.26`, `Paris 24C Apr29 NO -$2.16`); `SL_intra` no explica el dano principal. Backlog especifico: exact condition -> micro_position_unsellable; el guard v10.6.40 cubre `SL_intra exact+days<=1`, no `micro_position_unsellable`. Cambio aplicado: el Bankroll Scaling Monitor deja de mostrar `Phase 1 ready` desnudo y ahora distingue `Phase 1 proxy OK - canonical check pending/no evaluado`, remitiendo a `tools/phase1_readiness_check.py` como fuente canonica y aclarando que no autoriza Truth Pipeline/Fase C. `verify_before_deploy.py` suma guardrails para impedir la regresion del copy y conservar el mensaje manual-only. No se cambia la logica de bankroll scaling, `phase1_readiness_check.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, STOP_LOSS/TP, Truth Pipeline ni Fase C. No deploy manual.

**Última actualización:** 30 de abril de 2026 (Sesión 279 - traders_intelligence live paths fallback, Codex)
**Sesión 279 (30 abr 2026, Codex):** Patch acotado de tooling/observabilidad para corregir falso `health=degraded` en `Traders Intelligence`. Diagnóstico live: `/app/data/traders_intelligence.json` se generaba con `missing_inputs=["crosscheck_series","blocked_resolutions"]`, warnings contra `/app/data/runtime_import_derived/*.jsonl` y `recent_crosscheck.recent_runs=0`, aunque las fuentes canónicas existían en Railway (`/app/data/signals_crosscheck.jsonl` con 18 líneas y `/app/data/blocked_signals_resolutions.jsonl` con 440 líneas). Cambio: `tools/traders_intelligence_report.py` ahora prefiere `data/signals_crosscheck.jsonl` y `data/blocked_signals_resolutions.jsonl`, mantiene fallback legacy a `data/runtime_import_derived/*`, y cuando faltan inputs reporta `paths_checked` para evitar diagnósticos opacos. `verify_before_deploy.py` añade guardrails para live paths, fallback legacy, `paths_checked`, no abrir v1 y no tocar scheduler/trading. `docs/traders-intelligence-spec.md` documenta el contrato live-first/fallback. Validación: `python tools/check_python_syntax.py tools/traders_intelligence_report.py tools/traders_intelligence_daily_summary.py verify_before_deploy.py` OK; `python tools/traders_intelligence_report.py --help` OK; smoke local con salidas temporales OK (`health_status=usable_signal`); `python verify_before_deploy.py` pasa **1010/1010**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca `bot.py`, trading core, BANKROLL, sizing, whitelist, city modes, scheduler, `SCHEDULE_HOURS_UTC`, reglas de riesgo, Truth Pipeline ni Fase C. No deploy manual.

**Última actualización:** 30 de abril de 2026 (Sesión 278 - SL Retro briefing histórico phase-aware, Codex)
**Sesión 278 (30 abr 2026, Codex):** Patch mínimo de copy para alinear `Briefing Diario` con el `SL Retrospective` phase-aware. Diagnóstico: `tools/daily_position_briefing.py` imprimía directamente `final_verdict` desde `sl_retrospective_state.json`, por lo que podía mostrar `SL funciona correctamente (firme)` como conclusión operativa actual aunque `tools/sl_retrospective.py` ya separara histórico total vs config actual post-guard. Cambio: `build_sl_retro_line()` conserva `n_resolved/TARGET_SAMPLE_SIZE`, pero si el veredicto es concluyente o contiene `(firme)` lo muestra como `veredicto histórico` y remite al detalle `phase-aware`; no se toca `tools/sl_retrospective.py` ni la lógica de SL. `verify_before_deploy.py` añade checks para impedir que el briefing vuelva a emitir el copy legacy desnudo. Validación: `python tools/check_python_syntax.py tools/daily_position_briefing.py verify_before_deploy.py` OK; `python tools/daily_position_briefing.py --dry-run` OK; `python verify_before_deploy.py` pasa **1004/1004**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca trading core, BANKROLL, sizing, whitelist, city modes, scheduler, reglas de riesgo, STOP_LOSS/TP, Truth Pipeline ni Fase C. No deploy manual.

**Última actualización:** 30 de abril de 2026 (Sesión 277 - cierre documental auditorías read-only Apr 30, Sonnet)
**Sesión 277 (30 abr 2026, Sonnet):** Cierre documental de revisiones read-only del 30 de abril. (1) Wallet snapshot Railway: OK_RUN, 1 snapshot en `/app/data/wallet_portfolio_snapshots.jsonl`, `api_ok=true`, `total_value=19.90`, `phase2_ready=false`, `reason=need_more_history`, `valid_snapshot_days=1`; acumulando baseline 7d/168h; sin Telegram diario durante ACUMULANDO. (2) P/L reconciliación: 7d bruto +$20.96 contaminado por batch `market_resolved` antiguo +$23.36 (n=11); 7d limpio aprox. −$2.40; captura manual Polymarket 1W 08:00 = −$2.24. Lectura limpia válida; bruto no refleja mejora. BANKROLL $25 sin cambios. (3) Cross-check traders vs bot Los Angeles: contradicción ACTION/WATCH ya resuelta por commit `b503612` (Sesión 276); Los Angeles queda como auditoría de fuente/cobertura, no trading; sin cambios a whitelist/canary/active/RESOLUTION_ICAO/OBSERVED_AUDIT_CITIES. (4) Blocked signals daily audit 30-04: lectura read-only de `/app/data/blocked_signals_resolutions.jsonl`; total 440, v1/v2 398/42, OUT whitelist 13, IN 29, Unknown 398, WR OUT 100%, settlement unverified/unknown 100%; Unknown=398 son registros v1 legacy sin campos v2; backlog fuente/cobertura: Beijing, Lucknow, Guangzhou; veredicto ACTION_AUDIT_BACKLOG, no trading. No autoriza whitelist/canary/active/sizing/BANKROLL ni Fase C. No se toca código, bot.py, trading core, NOAA, scheduler, whitelist, city modes, bankroll, reglas de riesgo, Truth Pipeline ni Fase C.

**Última actualización:** 30 de abril de 2026 (Sesión 276 - crosscheck summary live-input alignment, Codex)
**Sesión 276 (30 abr 2026, Codex):** Patch acotado de observabilidad/copy para alinear la alerta corta `maybe_run_daily_crosscheck()` con el resumen diario `tools/signals_crosscheck_daily_summary.py`. Diagnóstico previo: el aviso corto del 2026-04-30 UTC vio `ACTION` por Los Angeles como gap operativo real, mientras el resumen diario emitió `WATCH` porque reconstruía el detalle operativo desde defaults/snapshots `runtime_import` potencialmente desfasados aunque la serie usara `/app/data/signals_crosscheck.jsonl`. Solución A: `bot.py` ahora invoca el summary pasando explícitamente los paths live del bot (`--signals SIGNALS_FILE`, `--shadow SHADOW_TRACKING_FILE`, `--policy CITY_POLICY_FILE`) además de `--crosscheck-file`. El summary añade fallback desde `operational_trader_only_count` del último registro live para no decir "sin gap operativo" si el JSONL ya detectó gap pero no puede reconstruir detalle. Copy nuevo: cuando hay detalle, muestra `Hoy aparece gap operativo real: ... Accion: auditoria de fuente/cobertura; no cambio de trading`; si no hay detalle, avisa que el gap fue detectado por cross-check live pero no reconstruible con snapshots. `verify_before_deploy.py` suma guardrails para paths live, fallback live, no recomendación automática de whitelist/canary, `SCHEDULE_HOURS_UTC` intacto y Los Angeles fuera de whitelist/canary/active, `RESOLUTION_ICAO` y `OBSERVED_AUDIT_CITIES`. Validación: `python tools/check_python_syntax.py bot.py tools/signals_crosscheck_daily_summary.py verify_before_deploy.py` OK; `python verify_before_deploy.py` pasa **1002/1002**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca trading core, BANKROLL, sizing, whitelist, city modes, scheduler, `SCHEDULE_HOURS_UTC`, reglas de riesgo, Los Angeles infra/city policy, Truth Pipeline ni Fase C. No deploy manual.

**Última actualización:** 30 de abril de 2026 (Sesión 275 - wallet snapshot observability daily, Codex)
**Sesión 275 (30 abr 2026, Codex):** Integración acotada de `tools/wallet_snapshot.py` como tarea diaria read-only de observabilidad en `bot.py`. Se añade `WALLET_SNAPSHOT_SCRIPT`, kill switch `WALLET_SNAPSHOT_ENABLED=1`, `WALLET_SNAPSHOT_HOUR_UTC` con default a `PNL_RECONCILIATION_HOUR_UTC`, timeout `WALLET_SNAPSHOT_TIMEOUT_SECONDS=45`, helper `run_wallet_snapshot_json()` vía `subprocess.run(... --json ...)` y `maybe_run_wallet_snapshot(state)` dentro de `run_observability_alerts()`. La tarea corre como máximo una vez al día en el mismo contenedor Railway, guarda snapshots reales para acumular baseline 7d/168h, no envía Telegram durante `ACUMULANDO` y emite una alerta one-shot cuando `phase2_ready=true`, dejando claro que solo abre integración manual con `pnl_reconciliation_alert.py` y que no autoriza cambiar BANKROLL ni sizing. `alerts_state.json` suma claves `wallet_snapshot_*` para anti-spam/readiness/error. `verify_before_deploy.py` añade checks estáticos de env vars, helper JSON, estado, one-shot, no scheduler y no integración PnL. `docs/wallet_snapshot.md` documenta la automatización diaria. Validación local: `python -m py_compile bot.py tools/wallet_snapshot.py verify_before_deploy.py` bloqueado por lock local conocido de `__pycache__`; fallback `python tools/check_python_syntax.py bot.py tools/wallet_snapshot.py verify_before_deploy.py` OK; `python tools/wallet_snapshot.py --dry-run --json` OK; `python verify_before_deploy.py` pasa **996/996**; `git diff --check` OK con avisos LF/CRLF de Windows. No se toca `tools/pnl_reconciliation_alert.py`, trading core, scheduler de trading, `SCHEDULE_HOURS_UTC`, BANKROLL, sizing, whitelist, city modes, STOP_LOSS/TP, reglas de riesgo, Truth Pipeline ni Fase C. No se ejecuta deploy manual.

**Última actualización:** 29 de abril de 2026 (Sesión 274 - wallet snapshot read-only Fase 1, Codex)
**Sesión 274 (29 abr 2026, Codex):** Implementación acotada de `tools/wallet_snapshot.py` como Fase 1 read-only para snapshots diarios de wallet/portfolio Polymarket. La herramienta lee `FUNDER`, intenta cash USDC vía CLOB y posiciones vía Data API, calcula `total_value = cash_available + active_positions_value + resolved_pending_value`, soporta `--dry-run`, `--json`, `--markdown`, `--report-only`, appendea en runtime `data/wallet_portfolio_snapshots.jsonl` y tolera fallos API/auth con `api_ok=false` sin crash. Añade delta 7d cuando exista baseline 168h, ajuste opcional por `data/wallet_cash_flows.jsonl`, detección de `possible_deposit` y contrato `phase2_ready` para futura integración. Se crea `docs/wallet_snapshot.md` y `verify_before_deploy.py` suma checks estáticos de no `bot.py`, no órdenes, no trading core y contrato JSON. Validación local: `py_compile tools/wallet_snapshot.py` OK fuera del sandbox por lock local de `__pycache__`; CLI `--dry-run`, `--dry-run --json`, `--dry-run --markdown`, `--report-only --json` OK sin `FUNDER` marcando unavailable; `python verify_before_deploy.py` pasa **989/989**; `git diff --check` sin errores, solo aviso LF/CRLF de Windows en `verify_before_deploy.py`. No se integra aún con `tools/pnl_reconciliation_alert.py`; no se toca `bot.py`, scheduler, trading core, BANKROLL, sizing, whitelist, city modes, reglas de riesgo, Truth Pipeline ni Fase C. Primeros días queda `ACUMULANDO` hasta baseline 7d/168h y no autoriza subir bankroll.

**Última actualización:** 29 de abril de 2026 (Sesión 273 - micro-fix bankroll scaling status/markdown, Codex)
**Sesión 273 (29 abr 2026, Codex):** Micro-fix acotado de `tools/bankroll_scaling_check.py`: el estado `UNKNOWN` queda reservado para ausencia/error de datos básicos de performance (`closed_trades`, PnL, WR o drawdown no evaluables). Si no hay hard blockers pero faltan evidencias de política para abrir revisión manual, por ejemplo `bankroll_readiness_score_unavailable`, `truth_pipeline_status_unknown` o `recent_core_change_observation_unknown`, el status pasa a `NOT_ELIGIBLE` con `decision=do_not_increase`. También se endurece el render Markdown de `Performance windows` construyendo filas explícitas antes de `lines.extend(window_rows)` para evitar que `current_logic_series` y `last_20_closed` se peguen en Railway. `docs/bankroll_scaling_check.md` aclara la semántica y `verify_before_deploy.py` añade checks. Validación local: `py_compile` OK; CLI markdown/json OK; `python verify_before_deploy.py` pasa **981/981**. No se toca `bot.py`, trading core, compras/ventas, bankroll real, Telegram, scheduler, city modes, whitelist, Truth Pipeline ni Fase C.

**Última actualización:** 29 de abril de 2026 (Sesión 272 - P2B2 bankroll scaling performance windows, Codex)
**Sesión 272 (29 abr 2026, Codex):** P2B2 micro-patch read-only de `tools/bankroll_scaling_check.py`: el WR/PnL ya no se evalúa solo sobre todo `trade_lifecycle.json` mezclado. La tool añade `performance_windows` con `historical_all`, `current_logic_series`, `last_20_closed` y `last_30_clean_closed`; cada ventana reporta `closed`, `wins`, `losses`, `win_rate_pct`, `pnl_total`, `drawdown_last_5` y `sample_ok`. `evaluation_window` prioriza `last_30_clean_closed` si n>=30, luego `current_logic_series`, luego `last_20_closed`, y deja `historical_all` solo como fallback conservador; si hay ventana limpia suficiente, añade watch `historical_all_legacy_context`. `evidence.pnl_drawdown` mantiene compatibilidad y apunta a la ventana usada. Markdown añade tabla `Performance windows`; docs y verify cubren el contrato. Validación local: `py_compile` OK; CLI markdown/json OK; `python verify_before_deploy.py` pasa **980/980**. No se toca `bot.py`, trading core, compras/ventas, bankroll real, `BANKROLL_LEVELS`, `SCALING_TIERS`, sizing, whitelist, city modes, scheduler, variables de entorno, Telegram, Truth Pipeline ni Fase C; la herramienta sigue sin escribir archivos, sin DB writes y sin llamadas externas.

**Última actualización:** 29 de abril de 2026 (Sesión 271 - P2C bankroll scaling Telegram monitor, Codex)
**Sesión 271 (29 abr 2026, Codex):** P2C implementa integración acotada de observabilidad para el Bankroll Scaling Check. `bot.py` añade `run_bankroll_scaling_check_json()` con `subprocess.run(..., timeout=...)` contra `tools/bankroll_scaling_check.py --json`, formato Telegram manual-only y comando `/bankroll`/`/bankroll_status`. `maybe_run_bankroll_scaling_monitor(state)` se integra en `run_observability_alerts()` y usa `alerts_state.json` con claves `bankroll_scaling_last_status`, `bankroll_scaling_last_target_tier`, `bankroll_scaling_last_digest_date`, `bankroll_scaling_last_blockers_hash`, `bankroll_scaling_last_alert_cycle` y `bankroll_scaling_last_eligible_for_manual_review`; alerta solo por cambio de status/target/blockers, transición a `ELIGIBLE_FOR_MANUAL_REVIEW` o resumen cada `BANKROLL_SCALING_MONITOR_EVERY_CYCLES` ciclos. Si el check falla, solo loguea warning y no envía Telegram ni rompe ciclo. `verify_before_deploy.py` suma checks P2C y `docs/bankroll_scaling_check.md` documenta Telegram. Validación local: `python -m py_compile bot.py verify_before_deploy.py` OK; `python verify_before_deploy.py` pasa **975/975**. No se toca trading core, compras/ventas, `manage_positions`, `intra_cycle_sl_check`, BANKROLL real, `BANKROLL_LEVELS`, `SCALING_TIERS`, sizing, whitelist, city modes, scheduler, Truth Pipeline, Fase C ni variables de entorno de trading; integración read-only de observabilidad.

**Última actualización:** 29 de abril de 2026 (Sesión 270 - P2B micro-fix scaling check evidence clarity, Codex)
**Sesión 270 (29 abr 2026, Codex):** Micro-fix acotado de `tools/bankroll_scaling_check.py` tras ejecución real en Railway. Se corrige la semántica visual de `phase1_ready`: solo sale `pass` cuando `ready=true`; si `exit_code=1` permitido para `$25→$35`, ahora sale `pending` con nota `Phase 1 readiness pending; expected until thresholds are met`, evitando `pass | False`. Se mejora la evidencia de `bankroll_readiness_score` cuando no existe `bankroll_readiness_state.json`: busca en `--data-dir/bankroll_readiness_state.json`, `./data/bankroll_readiness_state.json` y `./bankroll_readiness_state.json`, expone `paths_checked`, `score:null`, `available:false` y copy claro de state file not found; Markdown muestra `unavailable (state file not found)` en vez de `None stage=None`. `verify_before_deploy.py` suma checks de estos contratos y pasa **965/965**. Validación local: `py_compile` OK, CLI `--markdown`/`--json` OK. No se toca `bot.py`, trading core, compras/ventas, sizing, bankroll real, `BANKROLL_LEVELS`, `SCALING_TIERS`, whitelist, city modes, scheduler, env vars ni Telegram; herramienta sigue read-only.

**Última actualización:** 29 de abril de 2026 (Sesión 269 - P2B bankroll scaling check read-only, Codex)
**Sesión 269 (29 abr 2026, Codex):** P2B implementado como herramienta acotada y read-only `tools/bankroll_scaling_check.py`. Evalúa si el sistema está `eligible_for_manual_review` para el siguiente tier manual `$25→$35→$50→$75→$100`, siguiendo `docs/bankroll_scaling_policy.md`; salida JSON/Markdown con `decision` limitada a `do_not_increase` o `manual_review_required`, hard blockers, watch items, missing evidence, criteria y evidence. Lee defensivamente runtime JSON/JSONL/logs y SQLite en URI `mode=ro`, sin importar `bot.py`, sin llamadas externas, sin Telegram, sin escribir archivos ni modificar DB. Documentación en `docs/bankroll_scaling_check.md`. `verify_before_deploy.py` suma checks de contrato read-only/no Telegram/no red/no bot.py/no writes/no core trading y pasa **963/963**. Validación local: `py_compile` OK, CLI `--markdown`/`--json` OK con DB local ausente y status `BLOCKED` conservador. No se toca `bot.py`, trading core, compras/ventas, sizing, bankroll real, `BANKROLL_LEVELS`, `SCALING_TIERS`, whitelist, city modes, scheduler ni variables de entorno.

**Última actualización:** 29 de abril de 2026 (Sesión 268 - P2A copy scaling manual-only, Codex)
**Sesión 268 (29 abr 2026, Codex):** P2A mínimo de observabilidad: se corrige únicamente el copy de las alertas Telegram `Scaling Readiness` y `Scaling Warning` en `bot.py` para alinearlas con `docs/bankroll_scaling_policy.md`. `Scaling Readiness` deja de decir "Considerar subir bankroll" y ahora se declara señal auxiliar, exige revisión manual, aclara que NO autoriza subida automática ni cambiar `BANKROLL` solo por esa alerta, y pide validar health/readiness/PnL antes de decidir. `Scaling Warning` conserva el bloqueo y añade lectura de señal auxiliar con revisión de PnL/drawdown. `verify_before_deploy.py` suma checks de contrato para este copy y para conservar `SCALING_TIERS`/`BANKROLL_LEVELS`. No se cambia lógica de trigger, trading core, compras/ventas, sizing, bankroll real, whitelist, city modes, scheduler ni reglas de riesgo.

**Última actualización:** 29 de abril de 2026 (Sesión 267 - política canónica de escalado de bankroll, Sonnet)
**Sesión 267 (29 abr 2026, Sonnet):** Documentación-only. Creado `docs/bankroll_scaling_policy.md`: política canónica manual para escalar bankroll $25→$35→$50→$75→$100. Define hard blockers globales, soft blockers/WATCH, criterios por nivel (incluyendo phase1_readiness, bot_health_check, SQLiteRecorder, PnL, WR, drawdown, ciclos estables), regla anti-subida por euforia, fuentes de datos, relación con alertas Telegram actuales (`Scaling Readiness`/`Scaling Warning` como señales auxiliares no autoritativas) y próximo paso P2 (herramienta read-only de elegibilidad). Decisión actual: no subir bankroll — continuar acumulando datos hasta phase1_readiness exit_code=0 o Bankroll Readiness Score ≥ 40% con PnL no negativo. No se toca código, bot.py, trading core, NOAA, scheduler, whitelist, city modes, bankroll real ni variables de entorno.

**Última actualización:** 29 de abril de 2026 (Sesión 266 - micro-patch documental Fase B2 + Bloque 3 readiness, Sonnet)
**Sesión 266 (29 abr 2026, Sonnet):** Micro-patch documental — sin cambios de código. Cierra el estado narrativo de Fase B2, bot health check y Bloque 3 readiness; establece el guardrail explícito del Truth Pipeline.
- **Fase A cerrada (v10.6.44–45, Sesión 261):** `blocked_signals_resolutions.jsonl` schema v2 implementado y generando registros reales en Railway. Confirmado `schema_version=2` en `/app/data/blocked_signals_resolutions.jsonl`. Ver Sesión 261 para campos y compatibilidad v1/v2.
- **Fase B1 cerrada (v10.6.46, Sesión 262):** `tools/blocked_signals_audit.py` implementado y probado. CLI read-only 7-secciones, stdlib-only, clasificación `audit_candidate/needs_settlement_verification/monitor/not_actionable/ignore`. Comando: `python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl --markdown`. Ver Sesión 262.
- **Fase B2 cerrada (v10.6.47, commit `78a55d8`):** alerta Telegram diaria de `blocked_signals` reemplazada por resumen estructurado con helpers `_blocked_signals_build_telegram_summary`/`_blocked_signals_format_telegram`. Incluye: resumen global v1/v2, WR OUT whitelist, top ciudades, concentración top-3, % settlement `unverified/unknown`, `reason_blocked`/`city_policy_status_at_record_time` cuando hay registros v2, candidatos a auditoría, nivel `INFO/WATCH/ACTION` y hint al CLI. Fallback al copy legacy si los helpers fallan. No es accionable para trading: no recomienda abrir whitelist, canary, active, bankroll ni compras. `verify_before_deploy.py` 12 checks nuevos → **919/919**. No se toca trading core, NOAA, scheduler, whitelist, city modes, bankroll, `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES` ni reglas de entrada/salida.
- **Bot health check cerrado (`tools/bot_health_check.py`, Sesiones 264–265):** CLI read-only stdlib-only `OK/WATCH/ACTION`. Calibrado: rechazos normales (`date_out_of_range_past`, `parse_fail`, `city_window_skipped`) no elevan estado; Tracebacks de observabilidad conocidos (`traders_intelligence_daily_summary.py`, `city-intelligence`) son `WATCH` y no `ACTION`; readiness Fase 1 pendiente queda como `WATCH` bajo esperado. `verify_before_deploy.py` **943/943**.
- **Bloque 3 — Fase 1 readiness (en espera):** recorder activo desde 2026-04-27. Control canónico: `python tools/phase1_readiness_check.py --db /app/data/polymarket.db --json` → exit_code=0 para avanzar. Criterios: ≥7 días, ≥21 ciclos, `market_snapshots>0`, `forecast_snapshots>0`, `recorder_fresh`, `no_large_gaps`. Último estado conocido aprox.: ~11/21 ciclos, ~1.5/7 días. ETA 2026-05-04 si el recorder sigue sin gaps.
- **Guardrail Truth Pipeline — NO tocar todavía:** `truth_records`, `truth_revisions` y tablas SQLite de Fase 1; Fase C blocked_signals (cruce truth pipeline); `settlement_fidelity_status` real; probability engines; backtesting; bankroll scaling automático.
- **Próximo paso cuando exit_code=0:** pedir diseño Fase 1 Truth Pipeline preferiblemente con Opus. No implementar antes de readiness confirmada. Codex/Sonnet solo implementan después de que el diseño esté aprobado.

**Sesión 265 (29 abr 2026, Codex):** Micro-fix de calibración en `tools/bot_health_check.py` tras prueba real en Railway. Se amplía la lista de reject reasons normales (`date_out_of_range_past`, `parse_fail`, `city_window_skipped`) y el caso `with_edge=0/selected=0/buys=0/execution_reject_reasons={}` pasa a interpretar `no buys because no operable opportunities were selected` sin elevar por rechazos normales. La readiness pendiente de Fase 1 mantiene `WATCH` bajo con copy explícito de umbral esperado. Los `Traceback` conocidos de observabilidad (`traders_intelligence_daily_summary.py`, `traders intelligence summary`, `city-intelligence`) pasan a `WATCH` y no `ACTION`; los Traceback no relacionados con observabilidad, `order rejected`, `insufficient funds`, `auth failed` sin OK posterior, `SQLiteRecorder error` repetido y `cycle crash` siguen siendo críticos. `verify_before_deploy.py` suma 4 checks funcionales para estos contratos y pasa **943/943**. Validación: `python -m py_compile tools/bot_health_check.py verify_before_deploy.py` OK; `python tools/bot_health_check.py --data-dir data --db data/polymarket.db --markdown` OK. No se toca `bot.py`, trading core, compras/ventas, bankroll, whitelist, city modes, scheduler ni variables de entorno.

**Sesión 264 (29 abr 2026, Codex):** Implementada herramienta read-only `tools/bot_health_check.py` para resumir salud del bot en una sola salida `OK/WATCH/ACTION` sin SSH manual. CLI stdlib-only con `--data-dir`, `--db`, `--json`, `--markdown`, `--max-cycle-age-hours` y `--log-tail`; lee tolerante `cycle_summary.json`, `cycles_history.jsonl`, logs, `trade_lifecycle.json`/`postmortem.json`/`signals.json` opcionales y `polymarket.db` en SQLite URI `mode=ro`. Reporta runtime, ciclos, recorder/Phase 1 readiness, actividad de compras/rechazos, logs, posiciones y veredicto. Documentación en `docs/bot_health_check.md`. `verify_before_deploy.py` suma checks de contrato read-only/no Telegram/no red/no bot.py/no core trading. Validación: `python tools/bot_health_check.py --data-dir data --db data/polymarket.db --markdown` y `--json` OK con datos locales ausentes (WATCH sin crash); `python -m py_compile tools/bot_health_check.py verify_before_deploy.py` OK fuera del sandbox por lock local conocido de `__pycache__`; `python verify_before_deploy.py` pasa **939/939**. No se toca `bot.py`, trading core, compras/ventas, manage_positions, intra_cycle_sl_check, bankroll, whitelist, city modes, scheduler ni variables de entorno.

**Sesión 263 (29 abr 2026, Codex):** Minipatch de observabilidad para `tools/traders_intelligence_daily_summary.py` tras warning live en `send_telegram()`. El summary diario de traders_intelligence ahora trata Telegram como canal no fatal: divide mensajes largos en chunks seguros de 3800 caracteres, omite `parse_mode=HTML` para evitar fallos por tags/datos dinámicos, captura `HTTPError`, `URLError`, `TimeoutError` y `Exception`, hace un retry simple y devuelve `telegram_result` estructurado sin lanzar excepción. El script sigue escribiendo state/markdown aunque Telegram falle. `verify_before_deploy.py` suma checks de hardening de este tool. Validación: dry-run local sin llamada real a Telegram OK; `python -m py_compile tools\traders_intelligence_daily_summary.py verify_before_deploy.py` OK al ejecutarlo fuera del sandbox por lock local de `__pycache__`; `python verify_before_deploy.py` pasa **925/925**. No se toca `bot.py`, trading core, NOAA, whitelist, city modes, bankroll, scheduler, compras/ventas ni gestión de riesgo.

**Última actualización:** 28 de abril de 2026 (Sesión 262 - Fase B1 blocked_signals_audit.py, Sonnet)
**Sesión 262 (28 abr 2026, Sonnet):** Implementación Fase B1: `tools/blocked_signals_audit.py`. Herramienta read-only stdlib-only para auditar `blocked_signals_resolutions.jsonl` (v1 y v2) sin acceso SSH manual. Acepta `--source`, `--days`, `--json`, `--markdown`, `--out`, `--top`. Reporta 7 secciones: A) resumen global, B) split whitelist, C) top ciudades, D) concentración, E) señales baja accionabilidad, F) duplicados, G) candidatos a auditoría. Clasificaciones: `audit_candidate` / `needs_settlement_verification` / `monitor` / `not_actionable` / `ignore` — nunca recomienda abrir trading. 11 checks nuevos en `verify_before_deploy.py`. Total: **907/907**. Documentación en `docs/blocked_signals_audit_tool.md`. No se toca `bot.py`, trading core, NOAA, scheduler, whitelist, city modes, sigma, bankroll, ACTIVE_TRADING_CITIES, CANARY_TRADING_CITIES, ni reglas de entrada/salida. No se implementó Fase B2 ni Fase C.
- **Comando local rápido:** `python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl --markdown`
- **Con datos Railway:** descargar JSONL vía `railway_safe.ps1 ssh "cat /app/data/blocked_signals_resolutions.jsonl"` y pasar con `--source`.

**Última actualización:** 28 de abril de 2026 (Sesión 261 - blocked_signals schema v2 Fase A v10.6.45, Sonnet)
**Sesión 261 (28 abr 2026, Sonnet):** Implementación Fase A del schema v2 para `data/blocked_signals_resolutions.jsonl`. Cambios aditivos en `bot.py`: 6 helpers nuevos (`_classify_city_bucket`, `_resolve_observed_coverage_status`, `_build_blocked_signal_canonical_id`, `_price_bucket`, `_extract_token_id`, `_resolve_blocked_reason`) + enriquecimiento del dict appendeado al JSONL de 13 campos v1 a 33 campos v2 + dedupe por `canonical_signal_id` más granular (acepta `match_key` como fallback para registros v1). 13 checks nuevos en `verify_before_deploy.py`. Bump patch v10.6.44 → v10.6.45 (micro-fix doc post-review Opus). Total: **896/896**. No se toca trading core, NOAA, scheduler, MIN_EDGE, sigma, sizing, BANKROLL, whitelist, city modes, ACTIVE_TRADING_CITIES, CANARY_TRADING_CITIES, ni reglas de entrada/salida.
- **Campos nuevos siempre disponibles (15):** `schema_version`, `canonical_signal_id`, `market_id`, `condition_id`, `token_id_yes`, `token_id_no`, `market_slug`, `city_mode_at_record_time`, `whitelist_status_at_record_time`, `city_policy_status_at_record_time`, `reason_blocked`, `block_reason_detail`, `resolution_source`, `observed_coverage_status`, `price_bucket`
- **Campos null/unknown hasta Fase C (5):** `settlement_source`, `settlement_fidelity_status`, `bot_edge_pct_at_signal`, `bot_would_have_bought`, `bot_evaluation_source`
- **Compatibilidad v1/v2:** registros v1 antiguos (398 canónicos) se leen sin cambio; `schema_version` ausente = v1 implícito. Dedupe acepta ambos formatos.
- **NO implementado en esta sesión:** backfill v1, Fase C (cruce truth pipeline). Fase B1 implementada en Sesión 262 (v10.6.46); Fase B2 en v10.6.47 (commit `78a55d8`).

**Última actualización:** 28 de abril de 2026 (Sesión 259 - Auditoría blocked signals fuera de whitelist, Sonnet)
**Sesión 259 (28 abr 2026, Sonnet):** auditoría read-only de la alerta `Blocked signals fuera de whitelist — 105 resueltas | 104 wins | WR 99.0%`. Sin cambios a bot.py, whitelist, city modes, bankroll, trading core ni reglas de entrada/salida. Fuente: `/app/data/blocked_signals_resolutions.jsonl` en Railway (398 registros, todos `resolved=True`), descargado vía SSH y analizado localmente con Python.
- **Split confirmado correcto:** `bot.py:8441-8442` separa bien IN whitelist (293 señales, 281 wins, WR 95.9%) vs OUT whitelist (105 señales, 104 wins, 1 loss, WR 99.0%).
- **4 ciudades dominantes** explican 70/105 señales (66.7%): Lucknow 19, Warsaw 17, Beijing 17, Chongqing 17. Todas WR 100%.
- **6 traders en out-wl:** Entire-Hood (n=31, hist_wr=84%), Jubilant-Spending (28, 64.9%), Thrifty-Original (20, 80.5%), Dimpled-Boy (19, 81.0%), Kind-Flour (5), Pricey-Score (2). Son distintos a los del ledger de referencia.
- **Schema tiene gaps:** `resolution_source`, `settlement_source`, `market_id`, `edge_pct` no existen en el schema actual. Las apariciones de "UNKNOWN" en análisis previos eran campos ausentes, no nulls.
- **Dato no accionable todavía:** avg_price 0.64-0.77 (no trivial) pero sin settlement source verificado para las 4 ciudades dominantes. London WR 100% con n=21 y está bloqueada — refuerza que WR alta ≠ tradeable.
- **Warsaw:** candidata prioritaria a auditoría futura (no trading): n=17, 100%, avg_price 0.677, aparece en `stable_trader_only`, ICAO EPWA conocido. Pendiente confirmar settlement fidelity en ledger.
- **Mejora diferida:** enriquecer schema de `blocked_signals_resolutions.jsonl` con `market_id`, `edge_pct`, `resolution_source`, `settlement_source`, `city_mode_at_record_time`.
- **Readout:** `docs/blocked_signals_whitelist_audit_2026_04_28.md`. verify_before_deploy.py: sin cambios de código, no aplica re-run.

**Última actualización:** 27 de abril de 2026 (Sesión 258 - Fase 0.5/0.6 readiness check + Telegram health alerts v10.6.43, Sonnet)
**Sesión 258 (27 abr 2026, Sonnet):** Cierre de Fase 0/0.5/0.6. Merge y deploy de `feature/sqlite-recorder-phase-0` a `main`. Primer ciclo real con `SQLITE_RECORDER_ENABLED=1` grabado correctamente: 1 ciclo REAL, 5 ciudades (Dallas, London, Lucknow, Paris, Seoul), exit_code=1 (esperando más datos, ETA 2026-05-04). Implementado `tools/phase1_readiness_check.py` (Fase 0.5): script stdlib-only, exit codes 0/1/2/3, 6 criterios de readiness, output JSON. Implementado `maybe_run_recorder_health_alert()` (Fase 0.6): alerta Telegram Tipo A (readiness one-shot via `milestones["sqlite_recorder_phase1_ready"]`) + Tipo B (stale 1/día via `recorder_stale_last_alert_date`). Nueva variable `RECORDER_HEALTH_ALERTS_ENABLED=0` (default off). Constante `PHASE1_READINESS_SCRIPT` apunta a `tools/phase1_readiness_check.py`. Hook en `run_observability_alerts()` protegido por try/except. 8 nuevos checks en `verify_before_deploy.py`. Total: **883/883**. No se toca trading core, NOAA, city modes, sigma, bankroll ni lógica de compra/venta.
- **Variables Railway activas:** `SQLITE_RECORDER_ENABLED=1`, `SQLITE_DB_PATH=/app/data/polymarket.db`, `RECORDER_HEALTH_ALERTS_ENABLED=1`
- **ETA Fase 1 (Truth Pipeline):** 2026-05-04 si el recorder sigue activo y sin gaps
- **Criterio go/no-go Fase 1:** `python tools/phase1_readiness_check.py --db /app/data/polymarket.db` → exit_code=0

**Última actualización:** 27 de abril de 2026 (Sesión 257 - SQLite Recorder Fase 0 v10.6.42, Sonnet)
**Sesión 257 (27 abr 2026, Sonnet):** implementación de SQLite Recorder pasivo (Fase 0, arquitectura). Nuevo archivo `sqlite_recorder.py` en la raiz del repo: WAL mode, 3 tablas (`cycle_events`, `market_snapshots`, `forecast_snapshots`), rollback en caso de error, solo libreria estandar. Hook en `main()` al final del ciclo tras guardar `cycle_summary.json`, protegido por `SQLITE_RECORDER_ENABLED=0` (default off — no activo en Railway todavia). Si el recorder lanza cualquier excepcion, el ciclo continua sin interrupcion (fail-safe). `SQLITE_DB_PATH` usa `_data_path("polymarket.db")` para compatibilidad con el volumen Railway. `.gitignore` actualizado con `*.db`, `*.sqlite`, `*.sqlite3`. `sql/001_init.sql` como referencia canonica del schema. 10 checks nuevos en `verify_before_deploy.py` (v10.6.42). Pasa **869/869**. No se toca trading core, NOAA, scheduler, whitelist, sizing, reglas de entrada/salida ni city modes. Tambien se actualiza el check de version de v10.6.41 a v10.6.42 en `verify_before_deploy.py` y se añaden entradas de sesiones 256 y 257 a `agent_events.jsonl`.
- **Rama:** `feature/sqlite-recorder-phase-0`
- **Activacion Railway:** añadir `SQLITE_RECORDER_ENABLED=1` cuando se quiera empezar a acumular datos. El recorder crea `data/polymarket.db` automaticamente la primera vez.
- **Siguiente paso (Fase 1):** `truth_records` y `truth_revisions` en SQLite una vez confirmado que el recorder funciona en Railway sin impacto en latencia de ciclo.

**Ultima actualizacion:** 27 de abril de 2026 (Sesion 256 - revision alarmas dia 27 + anti-flapping guard legacy + PnL reporting fix, Sonnet)
**Sesion 256 (27 abr 2026, Sonnet):** revision sistematica de las alarmas del dia 27 — todas verificadas contra produccion via Railway SSH. Dos bugs reales encontrados y corregidos en v10.6.41:
- **Bug anti-flapping guard (Dallas):** `verified_history_bad` solo disparaba para `policy_source="noaa_verified"`. Dallas (17 trades, WR 11.8%, PnL -$1.60 cuando fue activa) tenia `policy_source="legacy"`, evadio el guard y se re-promovio a canary el 27 abr a las 08:00 UTC pese a historial malo y unico trader de referencia (Academic-Maniac WR 5%, PnL -$322). Fix: nuevo campo `degraded_history_bad` en `build_dashboard_city_decisions` — si la ciudad esta degradada (`auto_shadow_meta` presente) Y tiene `policy_trades >= 3`, `win_rate <= 25%`, `pnl <= 0`, bloquea `promotable_shadow` igual que `verified_history_bad`. Dallas demotada manualmente a shadow en produccion; canary activas quedan en 9 (sin Dallas).
- **Bug PnL reporting (daily briefing):** `_daily_summary_closed_trades_last_24h` incluia resoluciones `market_resolved` de marzo (11 trades, +$23.36) como si fueran del dia, inflando el "PnL neto 24h" de -$1.89 real a +$21.47. Fix: la funcion separa `batch_reasons = {"market_resolved", "market_resolved_yes"}` en campos propios `batch_closed/batch_pnl`; el mensaje Telegram muestra el PnL neto real en la linea principal y el batch en una linea separada "Batch market_resolved: N trades ($X) — resoluciones de mercados antiguos".
- **Alarmas verificadas correctas:** NOAA New York City (NYC 2026-04-22, observado 04:00 UTC, acumulado 25); Munich abierta (entry 0.465, precio 0.60 +$0.81 unrealizado, resuelve hoy); SL_intra guard (activo desde 05:56 UTC, 0 skips correcto — Seoul/Paris SL_intra son pre-guard).
- **Validacion:** `python -c "import py_compile; py_compile.compile('bot.py', doraise=True)"` OK; `verify_before_deploy.py` pasa **859/859**. El archivo `docs/revision alarmas dia 27.md` se borra en este commit segun instruccion del propio archivo.

**Ultima actualizacion:** 27 de abril de 2026 (Sesion 255 - fill real en SELL por order_id v10.6.41)
**Sesion 255 (27 abr 2026, Codex):** tras la operacion `Shanghai 27C Apr27 NO` del ciclo 187, se confirma con snapshot Railway fresco (`pulled_at=2026-04-27T09:03:22Z`) que el bot estaba mostrando y persistiendo el precio limite de salida, no el fill real: `performance.json` guardaba `SELL price=0.80`, `trigger_price=0.82`, `return_est=$3.55`, mientras Polymarket mostro fill real cercano a `99c` (`+$4.39`). La causa era de reporting/reconciliacion, no de trading: `audit_check_sell_fills()` solo verificaba que la orden ya no estuviera en `open_orders` y convertia `SELL_PENDING -> SELL` conservando el limite.
- **Patch v10.6.41 (Codex):** `bot.py` importa `TradeParams` y, al confirmar una venta, intenta enriquecer el pending sell con fill real por `order_id`: primero `client.get_trades(TradeParams(id=order_id))`, luego `client.get_trades(TradeParams(asset_id=token_id))` filtrando por `order_id`, y finalmente `client.get_order(order_id)` solo si trae campos explicitos de precio promedio/filled. Si hay fill real, `performance.json` conserva `limit_price`, reemplaza `price` por `fill_price`, actualiza `return_est` con `fill_value`, recalcula `pnl_cash/pnl_pct` cuando hay `avg_buy_price`, y propaga `fill_price/fill_value/fill_source` a `postmortem` y `trade_lifecycle`.
- **Copy Telegram:** el mensaje `[INTRA-SL]` ahora dice `precio limite` y aclara que el precio real puede diferir, igual que el path de ventas del ciclo principal.
- **Validacion:** `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; `python verify_before_deploy.py` pasa **859/859**. `python -m py_compile bot.py verify_before_deploy.py` sigue fallando solo por el lock conocido de `__pycache__` en Windows (`WinError 5`).

**Ultima actualizacion:** 27 de abril de 2026 (Sesion 254 - guard SL_intra exact+near-resolution v10.6.40)
**Sesion 254 (27 abr 2026, Opus):** se aplica el patch del clic identificado en el brief P/L semanal. Evidencia: en `data/runtime_import/trade_lifecycle.json`, los SL_intra post-fix v10.6.28+ acumulan en 14d `n=10`, `WR=10%`, PnL `-$3.95`, con patron concentrado en `condition=exact` + `days_ahead<=1` + edge>40%: Paris (43.1%/-$1.00/0h), Milan (46.5%/-$1.07/5.5h), Munich (42.8%/-$0.75/1.5h). El cooldown post-fix evita re-buys (todos buy_count=1) pero no impide que el SL dispare en el peor momento. Bot $25 perdiendo ~$4/semana solo por esta regla = 16% bankroll/semana.
- **Patch v10.6.40 (Opus):** `bot.py` agrega guard SL_intra para `condition=exact` con `days_ahead<=SL_INTRA_GUARD_DAYS_AHEAD_MAX` (default 1). Cuando el guard aplica, `intra_cycle_sl_check()` NO marca `sell_type="stop_loss_intra"`, deja que el mercado resuelva. TP_intra y SL del ciclo principal siguen activos. Cada skip se persiste en `data/sl_intra_guard_audit.json` con timestamp, token_id, city, outcome, condition, days_ahead, pct_pnl_at_skip, entry_price, cur_price, current_value, shares y bot_version. Telegram inmediato rate-limited (default 60min) por skip.
- **Alerta automatica de validacion:** `maybe_run_sl_intra_guard_review(state)` integrado en `run_observability_alerts`. Cuando hay >=`SL_INTRA_GUARD_REVIEW_MIN_SKIPS=5` token_ids skipped y todos resolvieron en lifecycle, envia Telegram one-shot comparando PnL real vs hipotetico (si SL hubiera disparado al momento del skip). Veredicto explicito: `funcionando` (delta>0), `perjudicando` (delta<0) o `neutro`. Idempotencia en `alerts_state["sl_intra_guard_review"]` y mirror en `sl_intra_guard_audit.json`.
- **Env vars Railway (default activo):** `SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION=1`, `SL_INTRA_GUARD_DAYS_AHEAD_MAX=1`, `SL_INTRA_GUARD_REVIEW_MIN_SKIPS=5`, `SL_INTRA_GUARD_TELEGRAM_COOLDOWN_MIN=60`. Kill switch: `SL_INTRA_GUARD_EXACT_NEAR_RESOLUTION=0` revierte a comportamiento previo sin redeploy.
- **NO se toca:** trading core, NOAA core, scheduler, MIN_EDGE, sigma, take_profit, sizing, BANKROLL ($25), whitelist, canary lists, BLOCKED_CITIES (London sigue), shadow lists (Atlanta/Dallas siguen), reglas de entrada, cooldown SL existente, ICAO-only audit (Lucknow/Beijing observados sin BUY).
- **Guardrails verify:** `verify_before_deploy.py` suma 7 checks v10.6.40 (env vars, helpers, archivo de estado, integracion en intra_cycle_sl_check, review function, hook en run_observability_alerts, BOT_VERSION). Pasa **855/855**. `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 253 - guardrail auto-canary ICAO-only)
**Sesion 253 (26 abr 2026, Codex):** tras deploy del patch ICAO-only proxy, Telegram emitio `Ciudad candidata a canary` y `Ciudad promovida a canary` para `Beijing` (`5` shadow edges, pico `37.9%`, `20` ciclos, `NOAA observados=0`). Diagnostico: no era normal segun la decision Opus; era un efecto colateral esperado por el codigo viejo. Al agregar Beijing a `OBSERVED_AUDIT_CITIES`, entro en `tracked_cities`; `promotable_shadow` solo exigia edges/ciclos/soporte/dias y no exigia muestra observada/interpretable ni revision manual para ICAO-only.
- **Fix:** `bot.py` agrega `_city_requires_manual_proxy_canary_review(city)` para ciudades en `OBSERVED_AUDIT_CITIES` sin `noaa_station_id`/`noaa_daily_station_id`. Esas ciudades quedan observables, pero no pueden auto-promocionar por shadow edges (`promotable_shadow` exige `not needs_manual_proxy_review`).
- **Estado persistido live:** como Beijing ya pudo quedar en `auto_canary_cities`, `get_effective_city_mode()` ignora `auto_canary` persistida para ciudades que requieren revision proxy manual, y `sync_city_policy_state()` la revoca (`auto_canary_revoked`) devolviendo la ciudad a shadow con Telegram explicito. Una configuracion manual en `CANARY_TRADING_CITIES` seguiria siendo una decision humana explicita.
- **Guardrail:** `verify_before_deploy.py` suma check `v10.6.39: ICAO-only proxy bloquea auto-canary sin revision manual`.
- **Validacion:** `python -B -c compile(...)` OK para `bot.py` y `verify_before_deploy.py`; `python verify_before_deploy.py` pasa **849/849**. Recomendacion operativa: commit/push/deploy urgente para revertir Beijing a shadow en el siguiente ciclo; si hay riesgo de BUY antes del deploy, pausar con `SHADOW_ONLY_MODE=true` o limpiar `auto_canary_cities.Beijing` en `city_policy_state.json`.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 252 - Beijing observado en codigo, no env var)
**Sesion 252 (26 abr 2026, Codex):** se corrige el ultimo supuesto operativo: Railway no tiene env var `OBSERVED_AUDIT_CITIES`; la lista vive hardcoded en `bot.py`. Se agrega `Beijing` a `OBSERVED_AUDIT_CITIES` para completar el estado intermedio decidido por Opus (`ICAO-only audit` via Open-Meteo proxy), sin agregarla a `QUALITY_TRADER_CITIES_WHITELIST`, `CANARY_TRADING_CITIES`, `ACTIVE_TRADING_CITIES` ni tocar reglas/sizing/scheduler/NOAA core.
- **Cambio de codigo:** `bot.py` incluye `"Beijing"` en el set `OBSERVED_AUDIT_CITIES`, junto a sus estructuras ya existentes `RESOLUTION_STATIONS`, `RESOLUTION_ICAO=ZBAA` y timezone `Asia/Shanghai`.
- **Guardrail:** `verify_before_deploy.py` suma check `v10.6.39: Beijing en OBSERVED_AUDIT_CITIES para ICAO-only proxy audit`, para fijar que la observacion formal no dependa de una env var inexistente.
- **Validacion:** `python -B -c compile(...)` OK para `bot.py` y `verify_before_deploy.py`; `python verify_before_deploy.py` pasa **848/848**. Resultado: Beijing puede acumular observabilidad/proxy cuando haya filas, pero no queda habilitada para BUY real por este cambio.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 251 - ICAO-only audit via Open-Meteo proxy)
**Sesion 251 (26 abr 2026, Codex):** se aplica la parte de codigo del patch minimo aprobado tras la decision Opus `Opcion 3` para ciudades ICAO-only: estado intermedio sin BUY real, usando Open-Meteo como proxy observado. No se toca `bot.py`, trading core, NOAA core, scheduler, whitelist, sizing, reglas ni Railway env.
- **Forecast accuracy audit:** `tools/forecast_accuracy_audit.py` agrega `icao_only_proxy_audit` para `Lucknow/VILK` y `Beijing/ZBAA`, configurable via `--icao-only-proxy-cities` y `--icao-only-proxy-date`. El bloque registra `coverage_status`, `observed_via_proxy_count`, ultimo observado proxy y delta vs forecast cuando existan filas de postmortem; si no hay filas, mantiene probe de cobertura sin inventar muestra.
- **Daily summary:** `tools/city_intelligence_daily_summary.py` lee `data/forecast_accuracy_raw.json` via `--forecast-accuracy` y agrega seccion `ICAO-only audit` al mensaje cuando el artefacto contiene `icao_only_proxy_audit`. La seccion muestra proxy rows, ultimo dato, delta vs forecast y cobertura por ciudad; es observabilidad pura.
- **Validacion live temporal:** con Railway postmortem y probe `2026-04-24`, Open-Meteo devuelve cobertura `covered` para `Lucknow/VILK` (`42.3C`) y `Beijing/ZBAA` (`24.8C`). `observed_via_proxy_count=0` en ambas porque todavia no hay filas forecast/postmortem para esas ciudades; esto confirma el estado intermedio sin BUY real.
- **Validacion repo:** `python verify_before_deploy.py` pasa **847/847**. `python -B -c compile(...)` OK para los dos scripts. `python -m py_compile` sigue pudiendo fallar por el lock conocido de `__pycache__` en Windows.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 250 - alerta P/L reconciliation)
**Sesion 250 (26 abr 2026, Codex):** se implementa una alerta diaria de reconciliacion P/L para separar la lectura wallet de Polymarket de la lectura explicativa del bot, sin tocar trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida. Nuevo script `tools/pnl_reconciliation_alert.py`: lee `trade_lifecycle`, calcula PnL/WR realizados en 7d/30d/60d/ultimos 20, marca semantica (`legacy_unresolved`, `closed_without_pnl`, open/pending), detecta `batch market_resolved` antiguo procesado dentro de 7d y genera mensaje Telegram con bloque `Tarea para Codex`.
- **Hook diario:** `bot.py` suma `PNL_RECONCILIATION_ENABLED=1` y `PNL_RECONCILIATION_HOUR_UTC` (default igual a `DAILY_BRIEFING_HOUR_UTC`), `PNL_RECONCILIATION_SCRIPT`, `PNL_RECONCILIATION_STATE_FILE` y `maybe_run_pnl_reconciliation(state)` integrado en `run_observability_alerts` despues de SL retro y antes del briefing. El hook es observabilidad/alerta, no actuador.
- **Lectura local de la captura:** sobre `data/runtime_import/trade_lifecycle.json` fresco, el lifecycle 7d marca `+$20.37` con WR `40.7%`, pero incluye `+$23.36` de `market_resolved` antiguo dentro de 7d; con el P/L Polymarket 1W de la captura (`-$3.65`) el delta seria `+$24.02`, por lo que la instruccion correcta es reconciliar wallet/fills/redeems/mark-to-market antes de usar el 7d del lifecycle como senal de mejora.
- **Validacion:** `python verify_before_deploy.py` pasa **847/847**. `python -m py_compile tools/pnl_reconciliation_alert.py bot.py verify_before_deploy.py` vuelve a topar con el lock conocido de `__pycache__` en Windows (`WinError 5`), pero la suite compila el script nuevo en verde. Readout regenerable local: `docs/pnl-reconciliation-readout-latest.md` (gitignored).

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 249 - servicios legacy pausados y alarma de borrado)
**Sesion 249 (26 abr 2026, Codex):** se ejecuta la limpieza operacional pedida tras validar que los servicios separados ya no deben emitir ni competir: `phase5-visibility` y `city-intelligence` se pausan en Railway con `railway down -s <service> -y`, conservando servicios, variables y volumenes para rollback/historial. Estado live posterior: `polymarket-bot` sigue `SUCCESS`; `phase5-visibility` y `city-intelligence` quedan sin deployment activo (`deploymentId=null`); `phase5-visibility-volume` y `city-intelligence-volume` siguen adjuntos y no se borran.
- **Alarma de borrado programada:** `data/service_transition_followup.json` pasa a fase `legacy_services_paused`, marca como resueltos los checkpoints de pausa (`phase5_pause_gate_2026_04_28`, `city_intelligence_pause_gate_2026_05_01`) y crea `legacy_services_delete_readiness_2026_05_03`. El daily summary canonico mostrara ese checkpoint y, cuando llegue la fecha, incluira runbook resumido para borrar servicios/volumenes sin perder funcionalidad.
- **Runbook permanente:** se crea `docs/legacy-analytics-service-cleanup-runbook-2026-04-26.md` y se actualiza `docs/city-intelligence-phase5-operational-transition-plan-2026-04-23.md`. Lo que queda vivo: scripts/docs/seed data en repo y el bridge de `polymarket-bot`; lo que puede borrarse tras observacion: servicios Railway legacy y volumenes `city-intelligence-volume` / `phase5-visibility-volume`, nunca `polymarket-bot` ni `polymarket-bot-volume`.
- **Validacion:** `tools/city_intelligence_daily_summary.py` soporta `runbook` en checkpoints pendientes; dry-run muestra proximo checkpoint `2026-05-03`; `python tools/check_python_syntax.py tools/city_intelligence_daily_summary.py` OK; `python verify_before_deploy.py` pasa **843/843**. No se toca `bot.py`, `city_policy_state.json`, trading, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 248 - servicios analiticos legacy silenciados)
**Sesion 248 (26 abr 2026, Codex):** se atiende la alerta combinada `Phase 5 Visibility` + `City Intelligence - resumen diario (2026-04-26 UTC)` siguiendo la accion clara posterior a la auditoria: eliminar ruido de emisores legacy sin tocar `bot.py`, `city_policy_state.json`, trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida. Primero se valida que el transporte read-only desde `polymarket-bot` funciona: `tools/railway_runtime_snapshot_pull.ps1` refresca `data/runtime_import/` con manifest fresco `pulled_at=2026-04-26T10:42:33Z`, `12/12` archivos, sin missing/extra/byte mismatch; ledger/pipeline local quedan `runtime_inputs_status=available` y `overall_status=ok`.
- **Raiz de la alarma:** el servicio Railway separado `city-intelligence` seguia sin `/app/data/runtime_import` y por eso su daily de `2026-04-26T07:00:00Z` envio `runtime_inputs_missing`. `phase5-visibility` seguia vivo y emitio la coincidencia Shanghai+Chicago del probe `2026-04-26T05:10:38Z` (`2+2` mercados, `20` coincidencias acumuladas), pero la lectura sigue siendo legacy/benchmark y no una decision de policy.
- **Cambio live reversible:** se sobrescribe `TELEGRAM_TOKEN=DISABLED` solo en los servicios separados `city-intelligence` y `phase5-visibility`, que vuelven a `SUCCESS` y validan dentro del contenedor `TOKEN_DISABLED`. `polymarket-bot` conserva su Telegram real como unico emisor canonico. No se apagan servicios todavia; el checkpoint `2026-04-28` queda orientado a pausar `phase5-visibility` si no aporta nada unico y el puente in-bot sigue cubriendo la senal.
- **Riesgo residual:** `system_alignment_check --decision-mode operational` queda con `error=1` por una colision operacional concreta en Atlanta (`runtime auto_shadow` vs `cross canary`), ya no por transporte runtime. No abrir policy hasta revisar esa divergencia con evidencia.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 247 - auditoria live blocked signals fuera de whitelist)
**Sesion 247 (26 abr 2026, Codex):** se ejecuta la primera auditoria read-only del `ACTION` diario `Blocked signals (fuera de whitelist)`, sin tocar `bot.py`, whitelist, NOAA, scheduler, sizing, Railway env ni reglas core. Fuente live: `/app/data/blocked_signals_resolutions.jsonl` en Railway `polymarket-bot`, `381` registros resueltos; whitelist live coincide con el default actual hasta `Dallas`; `BLOCKED_CITIES=London`. El agregado del Telegram queda reproducido: fuera de whitelist `101` resueltas, `100` wins, WR `99.0%`; excluidas por whitelist `280`.
- **Readout creado:** `docs/blocked-signals-outside-whitelist-audit-2026-04-26.md`. Ranking fuera de whitelist: `Lucknow` `19/19` WR 100%, consenso `7/7`, `VILK`, observado configurado pero sin NOAA ids ni `observed_vs_forecast`; `Warsaw` `17/17`, consenso `8/8`, `EPWA`, no observed, edge bot `0` pero vista live Apr 26; `Chongqing` `16/16`, consenso `2/2`, `ZUCK`, no observed, edge bot `1`; `Beijing` `14/14`, consenso `4/4`, `ZBAA`, no observed, edge bot `5`; `Buenos Aires` `7/7` pero sin consenso/edge y observed live `0`; `Lagos` `7/7` pero sin estructuras base en `bot.py`.
- **Decision operativa:** no abrir whitelist masiva ni tocar reglas core. El primer bloque accionable no es `Buenos Aires/Miami/Warsaw` como WATCH, sino verificacion de fuente/cobertura para `Lucknow`, `Warsaw`, `Beijing` y `Chongqing`, en ese orden aproximado. `Buenos Aires` queda para revisar starvation/cobertura NOAA si vuelve como gap real; `Miami` no aplica al baseline fuera de whitelist porque ya esta en whitelist; `Lagos` requiere discovery de fuente antes de cualquier decision. Delegar a Sonnet solo para segunda lectura del ranking/gate; delegar a Opus si aparece decision de criterio sobre aceptar nuevas ICAO-only o ampliar whitelist con `observed_vs_forecast=0`.
- **Continuacion fuente/cobertura:** Codex confirma fuente Polymarket/WU para `Lucknow/VILK`, `Warsaw/EPWA`, `Beijing/ZBAA` y `Chongqing/ZUCK`; live `audit.json` sigue con `observed_vs_forecast=0` para las cuatro; NOAA/NCEI global-hourly 2026 devuelve 404 para los ISD comentados (`42369099999`, `12375099999`, `54511099999`, `57516099999`). Cierres: `Lucknow` y `Beijing` quedan como `preparar whitelist-canary` solo si Opus acepta criterio ICAO-only; `Warsaw` y `Chongqing` quedan en `seguir acumulando muestra`. Prompt preparado: `docs/claude-opus-prompt-icao-only-canary-review-2026-04-26.md`. No deploy: cierre documental/read-only.

**Ultima actualizacion:** 26 de abril de 2026 (Sesion 246 - backlog traders-vs-bot 2026-04-26, no code)
**Sesion 246 (26 abr 2026, Codex):** se registra el parte diario `traders vs bot` / `Blocked signals` del `2026-04-26 UTC` como backlog operativo read-only, sin tocar `bot.py`, whitelist, NOAA, scheduler, sizing, Railway ni reglas core. Foto recibida: `MATCH=23`, `BOT_ONLY=5`, `TRADER_ONLY=12`; serie reciente de 7 corridas con medianas `MATCH=19`, `BOT_ONLY=5`, `TRADER_ONLY=19`. Persisten en `TRADER_ONLY` `7/7`: `Buenos Aires`, `Miami`, `Warsaw`; casi persistentes `6/7`: `Chengdu`, `Lagos`. No hay gap operativo real hoy, asi que el nivel queda `WATCH` para cross-check. En paralelo, `Blocked signals` fuera de `QUALITY_TRADER_CITIES_WHITELIST` marca `101` resueltas, `100` wins, WR `99.0%`, con `280` excluidas por whitelist, nivel `ACTION` solo para auditoria por ciudad/fuente/cobertura antes de tocar reglas core.
- **Backlog creado:** `docs/trader-bot-review-backlog-2026-04-26.md` fija el gate de ejecucion: no actuar por persistencia sola; ejecutar solo cuando una ciudad tambien sea gap operativo real fuera de blocked, con consenso/condicion operable o evidencia `exact/range` suficiente y fuente de resolucion verificable. Lectura por ciudad: `Buenos Aires` no esta en whitelist pero si tiene `SAEZ` + NOAA ids y esta en `OBSERVED_AUDIT_CITIES` (local `observed_vs_forecast=0`, revisar starvation/cobertura live antes de whitelist); `Miami` ya esta en whitelist y observada (`KMIA`, NOAA ids, local n=3), por lo que su persistencia apunta mas a falta de edge que a permiso; `Warsaw` no esta en whitelist ni en `OBSERVED_AUDIT_CITIES` y sigue `ICAO-only` (`EPWA`), asi que requiere verificacion de fuente/cobertura antes de cualquier canary.
- **Cola ACTION blocked signals:** el agregado `101/100` no autoriza cambios automaticos. La siguiente auditoria debe rankear el JSONL live por ciudades fuera de whitelist con mas muestra, confirmar `RESOLUTION_ICAO`, `OBSERVED_AUDIT_CITIES`, `observed_vs_forecast` y fuente Polymarket/WU/NOAA, y solo preparar whitelist/canary si esa ciudad tambien aparece como gap operativo real.

**Última actualización:** 26 de abril de 2026 (Sesión 245 — City Intelligence daily: observar, sin blocker nuevo)
**Sesión 245 (26 abr 2026, Codex):** se cierra la alerta `City Intelligence - resumen diario (2026-04-25 UTC)` como decisión de observación, sin cambio de código, policy, Railway ni trading core. Evidencia recibida: runtime read-only manifestado desde `2026-04-25 11:00 UTC`, preflight operacional live sin errores, topología efectiva `blocked=1 / canary=9 / shadow=1 / active=0`, `blocking_operational_collision_count=0`, señal `usable_signal`, review queue `now=1 / soon=3 / watch=14` y cuello dominante `policy_execution_gate`. Decisión: no revalidar transporte runtime ni repetir trabajo cerrado; no abrir policy todavía. Siguiente acción: observar si la evidencia fresca convierte el `now=1` en blocker real o en acción concreta; mantener los checkpoints existentes de transición (`Apr 28` phase5-visibility y `May 1` bridge con ≥5 ejecuciones válidas). Nota local: `system_alignment_check --decision-mode operational` en este checkout cae por artefactos locales stale/no bijectivos (`runtime_import` con backup extra y effective view viejo), por lo que no debe usarse para contradecir la lectura live de esta alerta.

**Última actualización:** 26 de abril de 2026 (Sesión 244 — cierre operativo slot 04h validated/keep)
**Sesión 244 (26 abr 2026, Codex):** se cierra la alerta `Slot monetization review` recibida para `04h UTC` como decisión operativa, no como cambio de lógica. Evidencia de la ventana leída: `5 ciclos`, `same_day_candidates=106`, `same_day_edges=3`, `same_day_selected=3`, `same_day_buys=2`, `buy_rate=66.67%` y `same_day_buy_rate=66.67%`; reject reasons dominantes `price_out_of_range=663`, `condition_filtered=86`, `blocked_city=22`; execution reject residual `buy_min_size=1`. Decisión: `04h UTC` queda `validated/keep`; no se toca `bot.py`, scheduler, NOAA, reglas de entrada/salida, sizing, Railway env ni deploy. Siguiente acción: vigilar estabilidad del slot en las próximas alertas y solo reabrir lógica si cae la conversión edge->buy o reaparece un cuello recurrente distinto de `buy_min_size` aislado.

**Última actualización:** 25 de abril de 2026 (Sesión 241 — fix bridge city intelligence: bootstrap settlement_fidelity_probe)
**Sesión 241 (25 abr 2026, Sonnet):** diagnóstico y fix del bridge de City Intelligence en Railway. La alarma de `runtime_inputs_missing` que llegaba diariamente provenía del servicio separado `city-intelligence` (que reporta `missing_telegram_env` y escribe `last_sent_date` igual que si hubiera enviado) y del bridge de `polymarket-bot` fallando silenciosamente por `partial_failure` en el pipeline. Causa raíz: `settlement_fidelity_probe.json` no existía en el volumen de `polymarket-bot`; esto causaba cascade de fallos en `reference_trader_city_market_cross`, `city_probe_visibility_tracker`, `city_validation_ledger`, `city_promotion_gate` y `city_intelligence_telegram_alert`. Fix: se agrega bootstrap `--refresh-probe` al bridge cuando el archivo falta, idéntico al bootstrap existente para `directional_trader_census.json` (`bot.py` línea 7557). `verify_before_deploy.py` suma check v10.6.31 para el nuevo bootstrap y queda en verde: **843/843**. Commit `dfc9235`, push a main. Tras el próximo redeploy de Railway, el primer ciclo post-07 UTC bajará el probe y el bridge podrá completar el pipeline exitosamente por primera vez.
- **Estado del checkpoint Apr 24:** `bridge_single_emitter_2026_04_24` resuelto con fix. `city-intelligence` ya no tiene `TELEGRAM_TOKEN` activo (confirmed). `phase5-visibility` sigue silenciado. El bridge producirá la primera daily summary real del bridge en el próximo ciclo post-redeploy.
- **Próximo checkpoint:** Apr 28 — gate para pausar `phase5-visibility` si no se echó en falta y el bridge acumula ≥1 ejecución válida post-fix.
- **Ejecución #1 confirmada (Apr 25 11:00 UTC):** el bridge completó los 5 pasos exitosamente. `settlement_fidelity_probe.json` generado via `--refresh-probe` (14KB). `last_progress_state=mejorando`, `bottleneck=policy_execution_gate`, `actionable_cities=0`, `building=5`. Gate de May 1 (≥5 ejecuciones): 1/5 cumplido.

**Última actualización:** 25 de abril de 2026 (Sesión 240 — encoding fix alert slot monetization)
**Sesión 240 (25 abr 2026, Sonnet):** fix de un byte en `maybe_evaluate_slot_monetization` en `bot.py`: la línea recortada para cuando `SCHEDULE_DISABLED_HOURS_UTC=23` tenía `leÃ­da` en vez de `leída`, produciendo texto corrupto en Telegram. Un carácter, 842/842. La revisión del alert confirmó que el slot `04h` cruzó a `validated/keep` (`same_day_buys=2` en ventana de 5 ciclos), no requería cambio de lógica. Acción: push + redeploy Railway.

**Última actualización:** 25 de abril de 2026 (Sesión 239 — limpieza post-V2 cutover P6+P7)
**Sesión 239 (25 abr 2026, Codex):** se ejecuta la limpieza post-cutover V2 disparada por la alerta P6+P7, respetando el guardrail de no tocar trading core, NOAA, scheduler, Kelly, sigma ni reglas de entrada/salida. Precondición revisada en Railway: logs recientes de `polymarket-bot` sin errores recurrentes en `create_or_derive_api_key`, `get_open_orders`, auth endpoints ni CLOB; solo persisten warnings auxiliares de summaries analíticos, no inestabilidad V2 SDK.
- **P6 — Seoul shadow legacy reset:** se crea backup local `data/runtime_import/shadow_city_tracking.json.bak-pre-p6` y backup remoto `/app/data/shadow_city_tracking.json.bak-pre-p6`. `shadow_city_tracking.json` en Railway queda con Seoul aislado a evidencia post-fix desde `2026-04-17T12:22:40Z`: `markets_seen 207 -> 54`, `edge_hits 5 -> 2`, `cycles_seen 91 -> 28`, `best_edge_pct 68.5 -> 26.4`. La única señal direccional durable de Seoul queda `Seoul|2026-04-18|YES|at_or_above|21`, `times_seen=2`, `first_seen_at=2026-04-17T12:22:40Z`, sin arrastrar la muestra contaminada Incheon previa al fix de estación.
- **Validación P6:** `city_validation_ledger.py` + `city_promotion_gate.py` se validan contra una copia manifestada post-P6 con `runtime_inputs_status=available`, `manifest_drift_inputs=[]`, `gate_status_counts` sin drift y Seoul en `canary_measurement` con `edge_evidence.shadow_edge_hits=2`, `shadow_cycles_seen=28`, `shadow_best_edge_pct=26.4`. `notify_active_candidates` para Seoul se apoya en trades cerrados post-promoción (`promoted_at=2026-04-17T16:29:31Z`), no en la muestra shadow contaminada; queda como caveat que `city_policy_state.auto_canary_cities.Seoul.reason` conserva texto histórico legacy, pero no cambia modo ni criterios de selección.
- **P7 — MIN_EDGE por ciudad:** se crea `docs/min-edge-per-city-analysis-2026-04-25.md`. Sobre `trade_lifecycle.json` fresco no hay ninguna ciudad que cumpla `n_closed>=10`, `WR>=70%` y `PnL>0`, así que la recomendación es **no aplicar** `MIN_EDGE_PER_CITY` todavía. Tokyo es la mejor candidata observacional (`n=5`, `WR=80%`, `PnL=+$3.53`) pero sigue bajo muestra mínima. El doc deja propuesta futura de env var JSON (`MIN_EDGE_PER_CITY={...}`) e implementación sugerida, sin aplicarla.
- **Review Sonnet 4.6:** `docs/sonnet-review-post-v2-cleanup-p6-p7-2026-04-25.md` aprueba P6+P7. Findings: solo trazabilidad baja/no bloqueante porque `city_policy_state.auto_canary_cities.Seoul` conserva reason/metrics legacy (`5 edges`, `65 ciclos`, `68.5%`) aunque el tracker ya está limpio. Recomendación: seguir sin cambios; limpiar ese texto/métricas en una futura sesión de cleanup documental/datos.
- **Follow-up Sonnet resuelto:** se actualiza `city_policy_state.auto_canary_cities.Seoul` en Railway y local para reflejar la muestra post-P6 (`shadow_edges=2`, `best_edge_pct=26.4`, reason con corte `2026-04-17T12:22Z`). Backup remoto: `/app/data/city_policy_state.json.bak-seoul-p6-traceability`. No cambia modo, sizing, reglas ni env vars.

**Última actualización:** 25 de abril de 2026 (Sesión 238 — alarmas con nivel de acción y tarea concreta)
**Sesión 238 (25 abr 2026, Codex):** se convierte el frente de alarmas `traders vs bot` / `Blocked signals` en una capa con repercusión explícita, sin tocar reglas de entrada/salida, NOAA, scheduler, sizing ni trading core. `tools/signals_crosscheck_daily_summary.py` ahora clasifica cada daily como `INFO`, `WATCH` o `ACTION` y reemplaza la instrucción genérica por una `Tarea para Codex`: si hay gap operativo real fuera de `blocked`, auditar primero la ciudad líder (whitelist, `RESOLUTION_ICAO`/estación, `OBSERVED_AUDIT_CITIES`/cobertura NOAA y señales trader), cerrando con `sin cambio`, `preparar whitelist/canary` o `bloqueo por fuente`. El mensaje legacy de `maybe_run_daily_crosscheck()` en `bot.py` también añade `Nivel` + `Accion`, para que incluso el aviso corto tenga salida operativa.
- **Blocked signals aclarado:** el Telegram ya separa `Baseline fuera de whitelist: N resueltas / wins / WR` de `Excluidas del cálculo por estar ya en whitelist: M`, y añade `Nivel` + tarea. Con `n>=50` y `WR>=70%` pasa a `ACTION`, pero la acción es auditoría de ciudades/fuente/cobertura antes de tocar core; el copy explicita que ese WR no mide ejecución real del bot.
- **Guardrail fijado:** `verify_before_deploy.py` suma checks `v10.6.37` para impedir que se pierdan `Nivel de accion`, `Tarea para Codex`, separación baseline/excluidas y la tarea de auditoría previa a reglas core. Validación local: `python tools/check_python_syntax.py bot.py tools/signals_crosscheck_daily_summary.py verify_before_deploy.py` OK y `python verify_before_deploy.py` pasa **842/842**.

**Última actualización:** 25 de abril de 2026 (Sesión 237 — lectura diaria traders-vs-bot con gap operativo en Los Angeles)
**Sesión 237 (25 abr 2026, Codex):** se registra el parte diario del summary `traders vs bot` y `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler, reglas de entrada/salida ni trading core. Foto UTC del `2026-04-25`: `MATCH=19`, `BOT_ONLY=7`, `TRADER_ONLY=13`; frente a la serie reciente de 7 corridas, las medianas quedan en `MATCH=17`, `BOT_ONLY=5`, `TRADER_ONLY=20`. La lectura operativa es que el gap se está cerrando respecto al inicio de la serie reciente, pero hoy sí aparece un gap operativo real fuera de `blocked`: `Los Angeles` con `2` señales, consenso `2` y `WR max 80%`.
- **TRADER_ONLY persistente:** en `7/7` corridas siguen `Buenos Aires`, `Chengdu`, `Miami` y `Warsaw`; casi persistentes `6/7`: `Busan`, `Lagos` y `Los Angeles`.
- **Blocked signals fuera de whitelist:** resueltas `95`, wins `94`, WR `98.9%`, con `273` señales excluidas por whitelist. Lectura: el baseline fuera de `QUALITY_TRADER_CITIES_WHITELIST` sigue muy alto y refuerza seguimiento, pero no autoriza por sí solo tocar reglas core.
- **Instrucción operativa vigente:** si el bloque `TRADER_ONLY` persistente se mantiene estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA de esas ciudades antes de tocar reglas de entrada o trading core. Para el siguiente bloque, `Los Angeles` queda como primera ciudad a verificar por gap operativo real con consenso.

**Última actualización:** 24 de abril de 2026 (Sesión 236 — cooldown post `stop_loss_intra` para cortar reentradas)
**Sesión 236 (24 abr 2026, Codex + Opus):** tras la alarma `Strategy Review` (`WR últimos 15 trades = 27%`) se refresca snapshot live de Railway (`data/runtime_import`, `pulled_at=2026-04-24T21:22:53Z`) y se confirma que el problema reciente no apunta a sigma global ni a retirar el SL, sino a reentradas tras `stop_loss_intra`. Evidencia clave: Chicago `62°F Apr25 YES` y New York City `66°F Apr24 YES` concentraron varios cierres intra-SL en ~36h; el bucket `LOW <35c` queda `0/7`, PnL `-$4.30`, mientras `MID/HIGH` queda `4/8`, PnL `+$1.08`. Opus revisa el caso read-only y señala el bug operativo: `manage_positions()` registraba `_sl_cooldown_register(city)` para `stop_loss`/`stop_loss_intra`, pero `intra_cycle_sl_check()` vendía por `stop_loss_intra` sin activar cooldown, permitiendo recomprar en el ciclo siguiente la misma tesis invalidada. Patch mínimo en `bot.py`: después de `audit_register_pending_sell(...)` en `intra_cycle_sl_check()`, si `sell_type in ("stop_loss", "stop_loss_intra")` y hay `city`, se registra `_sl_cooldown_register(city)` y se loggea el cooldown. Además se añade `maybe_run_post_intra_sl_cooldown_review(state)`: el primer ciclo post-deploy auto-ancla `started_at` en `alerts_state` y, cuando haya `POST_INTRA_SL_COOLDOWN_REVIEW_MIN_CLOSED=10` cierres nuevos, envía Telegram con WR/PnL post-fix, recuento de SL intra, reentradas repetidas y split `LOW <35c` vs `MID/HIGH`. No se toca sigma, NOAA, scheduler, whitelist, sizing, thresholds de SL/TP ni reglas de entrada. `verify_before_deploy.py` suma checks `v10.6.36` para cooldown + alarma post-fix y queda en verde: **838/838**. `python tools/check_python_syntax.py bot.py verify_before_deploy.py` OK; `python -m py_compile bot.py verify_before_deploy.py` volvió a fallar solo por el lock conocido de `__pycache__` en Windows (`WinError 5`), no por sintaxis.

**Última actualización:** 24 de abril de 2026 (Sesión 235 — SL retro en zona gris: no cerramos caso, seguimos monitorizando)
**Sesión 235 (24 abr 2026, Opus):** verificación rápida post-sesión 234 detecta que, aunque técnicamente el retro llega a `16/16` resueltos sin UNKNOWN, el mensaje Telegram concluía `✅ EL SL ESTÁ FUNCIONANDO CORRECTAMENTE` + `🚨 CONCLUSIÓN FIRME — tomar acción` con `accuracy_pct=37.5%` (6 falsas salidas de 16). Eso es exactamente la señal que motivó la investigación (SLs que acaban ganando), así que el copy cerraba el caso donde Pablo quería seguir recogiendo muestra. Se ajustan umbrales en `tools/sl_retrospective.py` sin tocar trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida: la banda "SL funciona correctamente" baja de `<40%` a `<30%`; entre 30–60% el veredicto pasa a `seguir monitorizando` y el bloque `CONCLUSIÓN FIRME` queda condicionado a estar fuera de la zona gris, pero la alerta sigue llegando con cada nuevo SL resuelto. El mensaje real ahora emite `📊 VEREDICTO: zona gris (6 SLs acabaron ganando sin el corte) — seguimos monitorizando` + `🔁 Muestra completa pero señal aún no concluyente — alerta seguirá llegando con cada nuevo SL`. `verify_before_deploy.py` suma 3 checks nuevos (`v10.6.35`) y queda en verde: **834/834**.
- **Drift detectado sin fix hoy:** `daily_position_briefing.py` muestra `🔍 SL Retro: sin datos aún` porque `data/sl_retrospective_state.json` solo se escribe en envío real, no en dry-run; el primer ciclo live en Railway sincroniza solo.
- **Intención operativa alineada:** el sistema ya no presenta el SL como caso cerrado. La banda 30–60% fuerza "seguimos monitorizando" y el re-envío por `new_resolved_data` sigue activo, así que cada nuevo SL resuelto dispara alerta.
- **Deploy:** push a `main` + redeploy Railway (sesión 235).

**Última actualización:** 24 de abril de 2026 (Sesión 234 — SL retrospective cerrado, sin UNKNOWN, y briefing saneado)
**Sesión 234 (24 abr 2026, Codex):** se cierra el frente de alertas `SL Retro` + `Briefing Diario` sin tocar trading core, NOAA core, scheduler, sizing, whitelist ni reglas de entrada/salida. La sesión corrige tres capas a la vez: (1) `bot.py` deja de presentar como pérdidas los break-even del resumen diario, usa la fecha/hora del payload en vez del reloj vivo y evita enviar el daily si aún no hubo un ciclo real ese día; (2) `tools/daily_position_briefing.py` ya no llama “posiciones abiertas” a filas legacy vencidas sin reconciliar y describe mejor las salidas de las últimas 24h; (3) `tools/sl_retrospective.py` pasa a resolver `stop_loss` y `stop_loss_intra` contra evidencia local NOAA (`audit.json` / `observed_vs_forecast`), `forecast_accuracy_raw` como fallback y, si aún falta observado local, `open-meteo archive`, hasta cerrar la muestra completa.
- **Lectura operativa final:** el retro de SL queda ya en `16/16` resueltos, `6 RIGHT`, `10 WRONG`, `0 UNKNOWN`. La conclusión deja de ser preliminar y pasa a **firme**: el `SL` agregado hoy **funciona correctamente**. La submuestra pura de `stop_loss_intra` sigue siendo pequeña, así que no da una tesis fuerte por sí sola, pero tampoco sostiene retirar el mecanismo.
- **Correctness del briefing:** las posiciones legacy con fecha de resolución pasada ya no contaminan `POSICIONES ABIERTAS`; el briefing separa abiertas reales, vencidas con contexto pendiente de reconciliación y `legacy stale no reconciliado`. Además, el bloque `ÚLTIMAS 24H` ya explica lado, entrada y motivo humano del cierre.
- **Cobertura nueva validada:** se backfillean/consumen observados para los casos que faltaban (`Madrid`, `London`, `Shanghai`, `Seoul`) y desaparecen los `UNKNOWN` del retro local. `verify_before_deploy.py` queda en verde con **831/831**.

**Última actualización:** 24 de abril de 2026 (Sesión 233 — hardening del runtime bridge de City Intelligence en Railway)
**Sesión 233 (24 abr 2026, Codex):** cierre corto de hardening operacional tras leer logs live de Railway donde el `city-intelligence runtime bridge` acababa fallando en `city_intelligence_daily_summary.py` por `Missing required input: /app/data/city_validation_ledger.json`. No se toca trading core, NOAA, scheduler, whitelist, sizing ni reglas de entrada/salida; el ajuste va al contrato del pipeline. `tools/city_intelligence_pipeline.py` ahora expone `failed_steps`, verifica outputs canónicos (`directional_trader_enrichment`, `reference_trader_city_market_cross`, `city_probe_visibility_tracker`, `city_validation_ledger`, `city_promotion_gate`) y devuelve exit code no cero cuando queda en `partial_failure`, para que el bridge se detenga en el paso real que falló y no llegue al summary con artefactos ausentes.
- **Raíz operativa validada:** el bridge no estaba fallando “en el summary” como causa primaria, sino porque `city_intelligence_pipeline.py` podía quedar en parcial y aun salir con código `0`; entonces `bot.py` seguía adelante y el primer síntoma visible era el ledger faltante.
- **Guardrail nuevo:** el stdout del pipeline ahora deja `failed_steps` / `missing_outputs` explícitos para Railway, y `verify_before_deploy.py` suma checks de contrato para impedir futuros verdes falsos antes de push/deploy. Validación local: `python tools/city_intelligence_pipeline.py --telegram-dry-run` y `python verify_before_deploy.py` en verde: **819/819**.

**Última actualización:** 24 de abril de 2026 (Sesión 232 — traders_intelligence automatizado con gate explícito para abrir V1)
**Sesión 232 (24 abr 2026, Codex):** se cierra la primera automatización útil de `traders_intelligence` sin tocar trading core, NOAA, scheduler, whitelist, sizing, reglas de entrada/salida ni arquitectura core. A partir de la spec `docs/traders-intelligence-spec.md`, se implementa `tools/traders_intelligence_daily_summary.py` y se integra en `bot.py` dentro de `run_observability_alerts()` como un builder/readout diario más. El flujo ahora regenera `data/traders_intelligence.json`, calcula checks explícitos de readiness para V1, persiste estado anti-spam en `data/traders_intelligence_daily_summary_state.json` (gitignored) y produce `docs/traders_intelligence_daily_summary_latest.md`. Validación local completa: `python tools/traders_intelligence_report.py`, `python tools/traders_intelligence_daily_summary.py` y `python verify_before_deploy.py` en verde: **817/817**.
- **Qué quedó automatizado:** el sistema ya no depende de una lectura manual para decidir si merece abrir `V1`; ahora distingue `ready / not_ready`, enumera blockers y deja instrucción explícita de siguiente acción cuando toque.
- **Foto actual del gate:** `V1 readiness = not_ready`. Los blockers reales hoy son `census_stale_days=15` (umbral `<=14`) y `recent_crosscheck_runs=2` (umbral `>=5`). Los checks fuertes sí pasan: hay al menos un lead trader muy activo (`Thrifty-Original`, `Entire-Hood`), profundidad de traders fuertes y varias `trader_only cities` candidatas.
- **Lectura estratégica nueva:** el siguiente paso correcto ya no es “inventar V1 por intuición”, sino desplegar esta automatización y dejar que el propio sistema avise cuando la base esté suficientemente fresca/profunda para archivar snapshots y abrir un `external trade lifecycle` mínimo con alcance acotado.

**Última actualización:** 23 de abril de 2026 (Sesión 231 — logging de skip reasons para SL retrospective / daily briefing)
**Sesión 231 (23 abr 2026, Codex):** patch mínimo de observabilidad sobre `bot.py` tras ver que el ciclo de las `20:00 UTC` ejecutó `run_observability_alerts()` pero no dejó rastro de `sl retrospective: OK`. Sin tocar trading core, NOAA, scheduler, whitelist ni reglas de entrada/salida, `maybe_run_sl_retrospective()` y `maybe_run_daily_briefing()` ahora loggean explícitamente por qué se saltan (`feature flag off`, archivo faltante, fuera de ventana horaria, ya enviado hoy, o ausencia de nuevos `stop_loss` / recheck no vencido). `python tools/check_python_syntax.py bot.py` y `python verify_before_deploy.py` siguen en verde: **817/817**.
- **Objetivo del patch:** cerrar el gap entre “el script funciona manualmente en Railway shell” y “el hook automático no deja huella en logs”.
- **Próxima lectura esperada en Railway:** el siguiente ciclo ya no debería ser silencioso; debería dejar un `sl retrospective: OK` o un `sl retrospective: skip (...)` con causa concreta.

**Última actualización:** 23 de abril de 2026 (Sesión 230 — validación live de SL retrospective en Railway)
**Sesión 230 (23 abr 2026, Codex):** cierre corto de validación live tras deploy manual de Pablo. Sin tocar trading core, NOAA, scheduler, whitelist ni reglas de entrada/salida, se confirma en shell del contenedor `polymarket-bot` que `tools/sl_retrospective.py` y `tools/daily_position_briefing.py` funcionan contra `/app/data/trade_lifecycle.json` real de Railway. El dry-run live ya no depende del fallback local y muestra datos más frescos que el checkout local: `SL Retro` sigue en `5/16` resueltos (`3` falsas salidas por SL, `2` SL correctos), mientras el briefing ya ve `3` cierres `stop_loss_intra` en las últimas 24h y una posición nueva `Seoul 21°C Apr24 YES`.
- **Validación live cerrada:** el deploy quedó bien; los scripts leen el volume real, formatean bien el mensaje y están listos para dispararse por ciclo sin esperar cambios de código.
- **Lectura estratégica nueva:** `trade_lifecycle` deja de ser solo observabilidad y pasa a ser la hipótesis más concreta y medible sobre el problema de PnL de las últimas semanas: el bot no solo puede estar entrando mal, también puede estar cortando demasiado pronto posiciones que luego sí resolvían bien.
- **Siguiente checkpoint operativo:** esperar el próximo ciclo natural de observabilidad para ver en logs el hook real (`sl retrospective: OK`) y, después, acumular muestra hasta `n>=8` SLs resueltos para sacar un veredicto preliminar con suficiente señal.

**Última actualización:** 23 de abril de 2026 (Sesión 229 — SL retrospective más claro: con SL vs sin SL)
**Sesión 229 (23 abr 2026, Codex):** ajuste corto sobre `tools/sl_retrospective.py` para que el mensaje deje de ser ambiguo. Sin tocar trading core, NOAA, scheduler, whitelist ni reglas de entrada/salida, el retrospective pasa de hablar en términos `RIGHT/WRONG` a mostrar explícitamente `con SL` vs `sin SL (mejor precio visto después)` por trade y en agregado. `verify_before_deploy.py` sigue pasando **817/817**.
- **Lectura humana nueva:** `falsas salidas por SL` y `SL correctos`, en vez de “tesis correcta / SL correcto”.
- **Métrica aclarada:** `upside_left_cash_peak` ya no se presenta como si fuese beneficio total; ahora el tool calcula `P/L con SL`, `P/L sin SL` y la diferencia atribuible al stop.
- **Foto actual de la muestra:** en los `3` SLs ya clasificados como falsas salidas, el total real fue `-0.96$ con SL` frente a `+4.46$ sin SL` al mejor precio visto después; diferencia `+5.42$`. En los `2` SLs correctos, el total fue `-3.56$ con SL` frente a `-4.39$ sin SL`; el stop evitó `0.83$` adicionales de pérdida.

**Última actualización:** 23 de abril de 2026 (Sesión 228 — SL retrospective + daily briefing)
**Sesión 228 (23 abr 2026, Codex):** se añaden dos capas observables nuevas sin tocar la lógica core de trading, NOAA, scheduler, whitelist ni reglas de entrada/salida: `tools/sl_retrospective.py` y `tools/daily_position_briefing.py`. `bot.py` integra ambos hooks al final de `run_observability_alerts()` con env vars nuevas `SL_RETRO_ENABLED`, `DAILY_BRIEFING_ENABLED` y `DAILY_BRIEFING_HOUR_UTC`. `verify_before_deploy.py` suma 7 checks nuevos; el preflight completo queda en **817/817**.
- **SL retrospective:** lee `trade_lifecycle`, clasifica cada `stop_loss` en `RIGHT/WRONG/UNKNOWN`, calcula muestra resuelta, accuracy y dinero dejado sobre la mesa, persiste estado en `data/sl_retrospective_state.json` y evita spam salvo nuevos datos, recordatorio diario o primer cruce del umbral preliminar (`n>=8`).
- **Daily briefing:** resume posiciones abiertas, cierres de las últimas 24h, score actual de `SL Retro` y recordatorio del checkpoint `Apr 28`, con anti-spam diario en `data/daily_briefing_state.json`.
- **Validación local:** `python tools/check_python_syntax.py tools/sl_retrospective.py tools/daily_position_briefing.py bot.py` OK; `python tools/sl_retrospective.py --dry-run` usa fallback local `data/runtime_import/trade_lifecycle.json` y hoy ve `14` SLs (`5/16` resueltos: `3 RIGHT`, `2 WRONG`, `9 UNKNOWN`, `$5.42` upside dejado); `python tools/daily_position_briefing.py --dry-run` muestra `13` posiciones abiertas; `python verify_before_deploy.py` pasa `817/817`.

**Última actualización:** 23 de abril de 2026 (Sesión 227 — cierre de trazabilidad: INTRA_REEVAL live en Railway shadow)
**Sesión 227 (23 abr 2026, Codex):** cierre corto de trazabilidad y contexto, sin tocar `bot.py`, trading core, NOAA, scheduler, sizing, whitelist, reglas de entrada/salida ni arquitectura core. Se valida contra snapshot live de Railway aportado por Pablo que `INTRA_REEVAL_ENABLED=1` y `INTRA_REEVAL_SHADOW_MODE=1` ya estaban cargadas en producción; el contenedor de `polymarket-bot` quedó reiniciado/actualizado correctamente, así que el bloque `INTRA_REEVAL` de la sesión 224 deja de estar pendiente y pasa a estado **live en modo shadow-log**.
- **Estado live corregido:** `INTRA_REEVAL` ya no requiere activación manual. El bot corre con `INTRA_REEVAL_ENABLED=1`, `INTRA_REEVAL_SHADOW_MODE=1` y defaults implícitos `PRICE_DRIFT_PP=10`, `COOLDOWN_MIN=80`, `EDGE_THRESHOLD=-3`. La feature observa/loggea y alerta, pero no vende.
- **Próximo hito real:** el one-shot `Review INTRA-REEVAL` queda armado para disparar 7 días después del primer trigger shadow registrado en `data/intra_reeval_state.json`. Hasta entonces no hace falta más trabajo sobre este frente salvo observación.
- **Nota de contexto:** la mención “Railway pendiente” de la sesión 224 queda como foto histórica de aquel momento, no como estado actual del sistema.

**Última actualización:** 23 de abril de 2026 (Sesión 226 — v10.6.31 gate LOW+exact + TP dinámico por precio)
**Sesión 226 (23 abr 2026, Sonnet+Opus):** análisis de posiciones cerradas (Apr 9-23, n=18) reveló WR=53% pero PnL=+$0.21 (breakeven) por ratio adverso avg_win=$0.61 vs avg_loss=$0.76. Bucket LOW (<35¢): n=2 WR=0% PnL=-$2.57 — London Apr19 @0.235 cayó a 1¢ (-95.7%, -$2.26 solo). Opus consultado: recomendó gate LOW+exact como palanca prioritaria; Step 3 (abs SL) diferido por ser más leniente en LOW/MID sin atacar el gap risk real. Implementado en **v10.6.31** — commit `da...` — `verify_before_deploy.py` pasa **810/810**.
- **Gate LOW+exact:** `BLOCK_LOW_EXACT_ENTRIES=1` (default on) bloquea entradas con `condition=exact` y `mkt_price<0.35`. Nuevo skip reason `low_exact_gap_risk`. Elimina la fuente del gap risk catastrófico en binary events sin afectar buckets productivos (MID/HIGH tienen WR=40% y 83%).
- **TP dinámico por precio:** función `effective_tp_pct(entry_price, our_prob)` combina HIGH_CONVICTION existente con floors por precio — LOW(<0.35): TP≥60%, HIGH(≥0.65): TP≥80%, MID: sin cambio. Nuevo cache `_lc_by_token_price` en `manage_positions`. Reemplaza inline también en `intra_cycle_sl_check`.
- **Step 3 (abs SL) diferido:** reevaluar cuando n≥30 trades post-gate. Opus identificó que abs SL es MÁS leniente para LOW/MID (amplifica pérdidas tipo gap) y no resuelve el problema raíz.
- **Siguiente acción:** observar comportamiento en Railway next cycles; checkpoint canary condition_filtered Apr 28.

**Última actualización:** 23 de abril de 2026 (Sesión 225 — plan operativo y Fase 1 de transición City Intelligence/Phase5)
**Sesión 225 (23 abr 2026, Codex):** se convierte la review de Opus de la sesión 224 en un plan operativo ejecutable y se inicia la Fase 1 (`silenciar → observar`) sin tocar `bot.py`, trading core, NOAA, scheduler core, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`. Se crea `docs/city-intelligence-phase5-operational-transition-plan-2026-04-23.md` y `data/service_transition_followup.json`; `tools/city_intelligence_daily_summary.py` pasa a leer ese plan y añadir un bloque `Seguimiento programado` al summary diario ya existente, de modo que los avisos/checkpoints usan el bridge de `polymarket-bot` y no crean un scheduler nuevo.
- **Avisos programados:** checkpoints UTC `2026-04-24` (confirmar bridge como único emisor útil), `2026-04-28` (gate para pausar `phase5-visibility`), `2026-05-01` (gate para pausar `city-intelligence` separado) y `2026-05-07` (cierre/archivo). Dry-run validado con salidas temporales: el summary muestra `Próximo checkpoint 2026-04-24`.
- **Cambio live reversible:** Railway confirma `polymarket-bot`, `city-intelligence` y `phase5-visibility` en `SUCCESS`. Se elimina `TELEGRAM_TOKEN` solo de los servicios separados `city-intelligence` y `phase5-visibility`, y se reinician ambos para que carguen el entorno sin token. `polymarket-bot` conserva su `TELEGRAM_TOKEN`, por lo que el emisor canónico del bridge sigue habilitado.
- **Evidencia post-cambio:** las variables de `city-intelligence` y `phase5-visibility` ya no incluyen `TELEGRAM_TOKEN`; `phase5-visibility` corre su pipeline post-restart en `overall_status=ok` pero queda mudo para Telegram; `city-intelligence` alcanzó a enviar el summary legacy de las 07:00 UTC antes del silencio, así que el primer día realmente limpio será el `2026-04-24`. Siguiente acción: observar que llegue solo el summary útil del bridge y no haya doble emisor.

**Última actualización:** 23 de abril de 2026 (Sesión 224 — review Opus city-intelligence + phase5-visibility, plan operativo para Codex)
**Sesión 224 (23 abr 2026, Opus):** revisión estratégica/operacional read-only de los dos servicios analíticos vivos del sistema, sin tocar `bot.py`, trading core, NOAA, scheduler, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`. Prompt ejecutado tal cual llegó en `docs/claude-opus-prompt-city-intelligence-phase5-service-review-2026-04-22.md` (ya eliminado al cierre). Entrega completa escrita en `docs/Sesion Opus.md`, con veredicto ejecutivo, tabla por servicio, plan por fases, kill criteria y 10 acciones concretas reversibles.
- **Veredicto city-intelligence:** mantener como **dominio analítico** (census, enrichment, cross, tracker, ledger, gate, daily summary, signals crosscheck), pero **apagar como servicio Railway separado**. Motivo: el puente 222 ya corre el pipeline completo desde `polymarket-bot` con runtime real, mientras el servicio remoto vive en fail-closed crónico por `/app/data/runtime_import` ausente (sesión 221). Una segunda shell solo agrega scheduler redundante y alarmas `runtime_inputs_missing` paralelas.
- **Veredicto phase5-visibility:** **congelar como legacy y apagar el servicio**. Kill criteria ya cumplidos antes de esta review: strategic review 2026-04-17 lo puso en `pausar`, 11 coincidencias `Shanghai + Chicago` sin producir decisión nueva (sesiones 186/193/195), tracker + alerta one-shot + comparador ya absorbidos por `city-intelligence`. Docs, seed data y scripts quedan en el repo como material histórico.
- **Plan operativo por fases (reversible):** Fase 0 no tocar bridge ni policy live; Fase 1 silenciar Telegram de los dos servicios Railway separados y validar 5–7 días que el bridge cubre toda la señal; Fase 2 `pause → stop` ambos servicios Railway, conservar código y docs, unificar escritor del tracker en el proceso del bot.
- **Siguiente paso:** la review pasa ahora a Codex para convertirla en plan operativo ejecutable y empezar a aplicarla — arrancando por silenciar alertas del servicio separado `city-intelligence` sin tocar trading ni policy runtime.

**Última actualización:** 22 de abril de 2026 (Sesión 222 — puente runtime read-only para City Intelligence en polymarket-bot)
**Sesión 222 (22 abr 2026, Codex):** se aplica la recomendación posterior a la alarma `City Intelligence`: mantener `city-intelligence` como servicio/capa separada para análisis, enriquecimiento, ledger/gate y revisión humana, pero mover la lectura diaria del runtime al único proceso que ve el volumen real del bot: `polymarket-bot`. No se cambian reglas de entrada/salida, NOAA, sizing, whitelist, policy runtime ni `city_policy_state.json`; el cambio queda limitado a observabilidad read-only.
- **Puente en el bot:** `bot.py` añade `maybe_run_city_intelligence_runtime_summary`, gated por `CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED` y `CITY_INTELLIGENCE_RUNTIME_BRIDGE_HOUR_UTC` (`07 UTC` default). Una vez por día, antes de `blocked_signals`, exporta el runtime, regenera `runtime_policy_effective_view`, corre `city_intelligence_pipeline.py --telegram-dry-run`, ejecuta `system_alignment_check.py --decision-mode operational` y finalmente dispara `city_intelligence_daily_summary.py`.
- **Export local read-only:** se crea `tools/runtime_import_local_export.py`, que copia desde `DATA_DIR` hacia `DATA_DIR/runtime_import` los artefactos observables del bot (`shadow_city_tracking`, `audit`, `city_policy_state`, etc.), exige los tres runtime inputs canónicos y escribe `runtime_import_manifest.json` + `policy_env_snapshot.json`. El export solo copia/deriva; no escribe policy live.
- **Bootstrap robusto:** si falta `data/directional_trader_census.json`, el bridge fuerza `--refresh-census` para que la primera corrida diaria no muera por falta de censo. `verify_before_deploy.py` queda ampliado con checks específicos v10.6.31 del bridge.
- **Validación:** `python tools/check_python_syntax.py bot.py tools/runtime_import_local_export.py verify_before_deploy.py` pasa; `python tools/runtime_import_local_export.py --data-dir data\runtime_import --output-dir data\runtime_import_bridge_test_verify` exporta manifest correctamente. `python verify_before_deploy.py` ejecuta 769 tests y solo falla 2 asserts heredados por el cambio preexistente de `INTRA_SL_INTERVAL` default `60` -> `20`; los 6 checks nuevos v10.6.31 pasan. No hacer deploy hasta decidir si ese default `20` es intencional y actualizar preflight o revertirlo.

**Última actualización:** 22 de abril de 2026 (Sesión 221 — City Intelligence runtime_import faltante en servicio live)
**Sesión 221 (22 abr 2026, Codex):** se atiende la alarma diaria `City Intelligence` que vuelve a declarar `runtime_inputs_missing`, respetando el guardrail: no tocar `bot.py`, `city_policy_state.json`, NOAA, scheduler, reglas de entrada/salida ni trading core. La validación separa dos planos: (1) el transporte read-only desde Codex/local hacia `polymarket-bot` funciona; (2) el servicio Railway separado `city-intelligence` sigue sin tener `/app/data/runtime_import`, por lo que su pipeline live cae correctamente en fail-closed.
- **Transporte read-only validado:** `powershell -ExecutionPolicy Bypass -File .\tools\railway_runtime_snapshot_pull.ps1` refresca `data/runtime_import/` desde `polymarket-bot` y deja `runtime_import_manifest.json` con `pulled_at=2026-04-22T07:19:13Z`, `12/12` archivos, sin missing/extra/byte mismatch. Artefactos requeridos presentes: `shadow_city_tracking.json`, `audit.json`, `city_policy_state.json`.
- **Lectura local corregida:** tras regenerar `runtime_policy_effective_view`, `city_validation_ledger`, `city_promotion_gate` y `city_intelligence_pipeline`, el estado local queda `runtime_inputs_status=available`, `overall_status=ok`, cuello dominante `trader_discovery`, topología efectiva `blocked=1 / canary=8 / shadow=16 / active=0`; `system_alignment_check.py --decision-mode operational` cierra en `error=0` (`ok=5`, `warning=3`).
- **Raíz live de la alarma:** `railway_safe.ps1 ssh -s city-intelligence "ls -la /app/data/runtime_import"` confirma `No such file or directory`; el `city_intelligence_pipeline.json` live de `city-intelligence` muestra `overall_status=runtime_inputs_missing` porque faltan `/app/data/runtime_import/shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`. No es ausencia real de edge ni fallo del bot principal.
- **Acción resultante:** no hay ajuste de trading hoy. El ajuste pendiente es de infraestructura/cableado: hacer que `city-intelligence` consuma una copia read-only fresca del runtime del bot antes de emitir su daily summary, o mover esa lectura al servicio `polymarket-bot` como se hizo con `signals_crosscheck`. Hasta entonces, sus recomendaciones por ciudad deben seguir fail-closed.

**Última actualización:** 22 de abril de 2026 (Sesión 220 — lectura diaria traders-vs-bot sin gap operativo real)
**Sesión 220 (22 abr 2026, Codex):** se registra el parte diario del summary `traders vs bot` y `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler, reglas de entrada/salida ni trading core. Foto UTC del 2026-04-22: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=18`; frente a la serie reciente de 7 corridas, las medianas quedan en `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=23`. La lectura operativa sigue prudente: la serie se mueve, pero todavía no da una historia única de mejora o deterioro. No aparece hoy un gap operativo fuerte fuera de `blocked` con consenso y condición operable; por tanto no se abre cambio inmediato de reglas.
- **TRADER_ONLY persistente:** en `7/7` corridas siguen `Ankara`, `Busan`, `Houston`, `Jakarta` y `Miami`; casi persistentes `6/7`: `Buenos Aires`, `Chengdu`, `Los Angeles`, `Madrid`, `Singapore` y `Toronto`.
- **Blocked signals fuera de whitelist:** resueltas `61`, wins `60`, WR `98.4%`, con `207` señales excluidas por whitelist. Lectura: baseline fuera de `QUALITY_TRADER_CITIES_WHITELIST` sigue extremadamente alto, pero el resumen diario no marca gap operativo real accionable hoy.
- **Instrucción operativa reiterada:** si el bloque `TRADER_ONLY` persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA de esas ciudades antes de tocar reglas de entrada o trading core.

**Última actualización:** 21 de abril de 2026 (Sesión 219 — Bankroll Readiness Score)
**Sesión 219 (21 abr 2026, Sonnet):** se implementa `tools/bankroll_readiness_score.py`, un indicador 0-100% que mide cuán cerca está el sistema de que el bankroll sea el cuello de botella real (en vez del sistema). 5 dimensiones ponderadas: D1 WR Confidence (30%, WR live con peso estadístico n≥20), D2 PnL Trajectory (25%, PnL 30d+60d positivo), D3 Edge Density (20%, edges/ciclo últimos 14d, target 1.0), D4 Size Pressure (15%, kelly_too_low como señal de bankroll limitante), D5 System Stability (10%, consistencia de versión en 7d). Score >75% = bankroll es el cuello → considera añadir capital. Score actual: **23.9%** (etapa temprana — D1=0 por WR=32%, D2=0 por PnL 30d=-$21.92, D3=21% por 0.21 edges/ciclo, D4=100% por kelly_too_low en 29.5% de oportunidades). El tool guarda historial en `data/bankroll_readiness_state.json` para seguimiento de tendencia. `verify_before_deploy.py` 763/763 sin cambios.

**Última actualización:** 21 de abril de 2026 (Sesión 218 — Busan + Dallas + schedule 6 ciclos/día)
**Sesión 218 — cierre (21 abr 2026, Sonnet):** activados 6 ciclos/día `SCHEDULE_HOURS_UTC=0,4,8,12,16,20` (antes 4,8,12,16). Motivación: cycles_history muestra 16:00 y 08:00 como horas más productivas; bloque 20:00-00:00 tenía actividad real en el schedule anterior (23:00, 21 ciclos, 1.3 edges/ciclo). El ciclo de las 20:10 UTC post-deploy produjo 3 compras (Shanghai NO, New York City YES, Seoul NO). Cambio solo en Railway env var, sin tocar bot.py.

**Última actualización:** 21 de abril de 2026 (Sesión 218 — Busan + Dallas al whitelist v10.6.29+v10.6.30)
**Sesión 218 — parte 2 (21 abr 2026, Sonnet):** tras incorporar Busan (v10.6.29), auditoría de Dallas reveló que la degradación del Apr-6 (WR=11.8%, "17 trades") era falsa: los 17 conteos incluían 66 entradas `LOSS_TOTAL` fantasma del bug de posiciones fantasma corregido en v10.5.12. Los trades reales de Dallas fueron 4 (2 SL, 2 pequeñas ganancias), muestra insuficiente para bloquear la ciudad. Shadow evidence actual: `best_edge=68.9%`, 12 shadow edge hits en 9 ciclos, NOAA 4/5 riesgo bajo. **v10.6.30:** Dallas agregado a `QUALITY_TRADER_CITIES_WHITELIST` (ahora 32 ciudades). Railway env actualizada. `verify_before_deploy.py` pasa **763/763**.

**Última actualización:** 21 de abril de 2026 (Sesión 218 — Busan (RKPK) incorporado como ICAO-only v10.6.29)
**Sesión 218 (21 abr 2026, Sonnet):** incorporación de Busan al bot tras verificación completa. Busan era TRADER_ONLY en 7/7 corridas del cross-check. Investigación confirmó: resolución Polymarket vía WU/RKPK (Gimhae Intl Airport Station) — fuente verificada en descripción real del mercado Apr-22; NOAA global-hourly 2026 dead (404 para estación 47158099999); WU histórico muestra "No data recorded" pero es artefacto de JavaScript no renderizado — WU real-time sí funciona ($85.8K volumen en mercado Apr-21, resuelto YES). Sin mismatch de fuente (diferencia con London). **v10.6.29:** Busan agregado a `RESOLUTION_STATIONS` (RKPK, lat 35.18, lon 128.95), `RESOLUTION_ICAO` (RKPK, ICAO-only), `OBSERVED_AUDIT_CITIES`, `CITY_TIMEZONES` (Asia/Seoul) y `QUALITY_TRADER_CITIES_WHITELIST` default (31 ciudades). Railway env var actualizada. `verify_before_deploy.py` pasa **761/761** (6 tests nuevos v10.6.29).

**Última actualización:** 21 de abril de 2026 (Sesión 217 — London overlay neutralizado, bloqueo estructural conservado)
**Sesión 217 (21 abr 2026, Codex):** se ejecuta la acción mínima y reversible definida tras la auditoría de London: mantener `BLOCKED_CITIES=London` como guardrail estructural por el mismatch documentado `Weather Underground vs Open-Meteo`, pero quitar la contradicción runtime que la mantenía también en `city_policy_state.auto_canary_cities`. No se toca `bot.py`, reglas de entrada/salida, NOAA core, scheduler, thresholds, whitelist ni trading core. Antes del cambio, `tools/railway_safe.ps1 ssh` confirma en live que `London` seguía en `auto_canary_cities` con `promoted_at=2026-04-12T15:03:51Z`, `best_edge_pct=28.4`, `shadow_edges=2`.
- **Cambio live en Railway:** se crea backup remoto `/app/data/city_policy_state.json.bak_london_auto_canary_1776788976` y se elimina solo `auto_canary_cities.London`; `updated_at` queda en `2026-04-21T16:29:36Z`. La reversión consiste en restaurar ese backup o reinsertar la entrada eliminada.
- **Validación post-cambio:** `tools/railway_runtime_snapshot_pull.ps1` deja snapshot fresco `pulled_at=2026-04-21T16:29:48Z`; se regeneran `runtime_policy_effective_view`, `reference_trader_city_market_cross`, `city_validation_ledger`, `city_promotion_gate`, `city_intelligence_pipeline` y `system_alignment_check --decision-mode operational`. Resultado: `blocking_operational_collision_count=0`, `collision_count=2` solo `documented_drift`, `system_alignment_check` pasa a `error=0` (`ok=5`, `warning=3`).
- **Estado London nuevo:** `runtime_policy_effective_view` lee `London => env=blocked, runtime=runtime_unknown, cross=blocked, effective=blocked, collision_flag=false`; `city_promotion_gate` la muestra como `blocked_with_signal`, `review_priority=soon`, `bottleneck=source_fidelity`, con `structural_block_guardrail=weather_underground_openmeteo_mismatch`. El siguiente paso honesto sigue siendo revalidación externa WU/manual antes de considerar mover London a `shadow`.

**Última actualización:** 21 de abril de 2026 (Sesión 216 — City Intelligence runtime transport reparado + wording de preflight)
**Sesión 216 (21 abr 2026, Codex):** se repara el bloqueo operativo abierto en la Sesión 214. Pablo completa `railway login` interactivo tras limpiar tokens caducados, y Codex valida desde el wrapper repo-local: `railway_safe.ps1 whoami` devuelve `pablogomez.eu@gmail.com` y `railway_safe.ps1 status` confirma `Project: enchanting-respect`, `Environment: production`, `Service: polymarket-bot`. Luego se ejecuta `tools/railway_runtime_snapshot_pull.ps1` con éxito: snapshot runtime read-only fresco en `data/runtime_import/` y `runtime_import_manifest.json` con `pulled_at=2026-04-21T14:54:02Z`, `12/12` archivos, sin drift de manifest.
- **Regeneración City Intelligence:** tras instalar la dependencia local faltante `py-clob-client-v2==1.0.0` desde `requirements.txt`, `city_validation_ledger.py` pasa a `runtime_inputs_status=available`, `n_cities=25`, sin missing/stale/manifest drift; `city_promotion_gate.py` pasa a `runtime_inputs_status=available`; `city_intelligence_pipeline.py` cierra `overall_status=ok`, `dominant_bottleneck=policy_execution_gate`, `top_now_city=Dallas`, `signal_health=usable_signal`.
- **Estado pendiente real:** `system_alignment_check.py --decision-mode operational` ya no falla por transporte, pero sigue en `error=1` por `blocking_operational_collision_count=1`: `London` está en `BLOCKED_CITIES` y a la vez en `city_policy_state.auto_canary_cities`. Como la instrucción original prohibía tocar `city_policy_state.json`, se deja sin borrar el overlay runtime. El transporte queda arreglado; el bloqueo restante es policy/live drift de London.
- **Patch de capa humana:** se corrige `tools/city_intelligence_daily_summary.py` para que el resumen no diga “preflight operacional sin errores” cuando `alignment_summary.error > 0`; ahora muestra `preflight operacional con error=N`. Dry-run validado: el mensaje ya declara `runtime_inputs_missing` cerrado, runtime snapshot fresco y `preflight operacional con error=1`. Sintaxis OK con `python tools/check_python_syntax.py tools/city_intelligence_daily_summary.py`.
- **Handoff siguiente sesión:** queda creado `docs/handoffs/london-blocked-policy-review-2026-04-21.md` con un prompt específico para analizar por qué `London` sigue siendo la única ciudad bloqueada y si corresponde mantener `blocked`, desbloquear a `shadow` o revalidar settlement/source antes de tocar policy.

**Última actualización:** 21 de abril de 2026 (Sesión 215 — P4+P5 whitelist expansion v10.6.27+v10.6.28: +9 ciudades al canary exact/range)
**Sesión 215 (21 abr 2026, Sonnet+Opus):** expansión masiva del canary exact/range para resolver throughput crítico (n=5 en 7 días). El checkpoint día 7 (WR=40% n=5) es `OK_INSUFICIENTE` — n<15, no cumple close trigger (WR<50% con n≥15). **P4 — v10.6.27** (ciudades ya en RESOLUTION_STATIONS): Tel Aviv (3/3=100% blocked WR, NOAA LLBG), Taipei (3/3=100%, ICAO-only RCTP), Singapore (TRADER_ONLY 2/2, ICAO-only WSSS), Wuhan (TRADER_ONLY 2/2, ICAO-only ZHHH). **P5 — v10.6.28** (ciudades nuevas, RESOLUTION_STATIONS añadidas): Opus verificó Polymarket resolution sources vía WebFetch y confirmó NOAA global-hourly+GHCND vacíos para las 5 en 2026 (patrón Jakarta/KL sesion 201) → todas ICAO-only: Moscow (5/5=100%, UUWW Vnukovo), Amsterdam (3/3=100%, EHAM Schiphol), Jeddah (4/4=100%, OEJN King Abdulaziz), Istanbul (3/3=100%, LTFM — riesgo mismatch=cero porque LTFM no está en NOAA ISD), Helsinki (TRADER_ONLY 2/2, EFHK Vantaa). También se corrigió bug en `maybe_alert_p4_p5_expansion`: precondición abortaría con WR<50% y n<15, confundiendo `OK_INSUFICIENTE` con `CLOSE/ALERT` real. `verify_before_deploy.py` pasa **755/755** (9 tests nuevos). El whitelist default pasa de 23 a 32 ciudades. **Pendiente Railway**: reemplazar env var `QUALITY_TRADER_CITIES_WHITELIST` con el valor completo: `Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan,Atlanta,London,New York City,Munich,Ankara,Madrid,Miami,Paris,Wellington,Houston,Jakarta,Kuala Lumpur,Tel Aviv,Taipei,Singapore,Wuhan,Moscow,Amsterdam,Jeddah,Istanbul,Helsinki`.

**Última actualización:** 21 de abril de 2026 (Sesión 214 — City Intelligence runtime transport bloqueado por auth Railway)
**Sesión 214 (21 abr 2026, Codex):** se atiende la alerta diaria de `City Intelligence` que declara `runtime_inputs_missing` y pide validar transporte read-only + manifest, con guardrail explícito de no tocar `bot.py` ni `city_policy_state.json` runtime. La auditoría confirma que el fail-closed es correcto: no se deben interpretar `edge_evidence=0` ni emitir recomendaciones por ciudad mientras no haya runtime fresco. En local, `data/runtime_import/` conserva un snapshot completo y bijectivo con manifest (`12/12` archivos, sin missing/extra/byte mismatch), pero está obsoleto: `runtime_import_manifest.json` tiene `pulled_at=2026-04-18T09:28:57Z` y el check operacional lo marca `runtime snapshot is stale` (~75.3h, SLO 24h). El pull read-only con `tools/railway_runtime_snapshot_pull.ps1` no llega a leer runtime live porque Railway CLI falla antes con `invalid_grant`.
- **Causa raíz validada:** `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor` confirma CLI `railway 4.35.0`, sin proxies en proceso ni persistentes, config writable y 1 proyecto linkeado, pero token expirado (`tokenExpiresAtUtc=2026-04-20T21:54:37Z`) y refresh token inválido. La recuperación requiere re-login Railway (`reset` + `launch-login -Browserless` o login interactivo) antes de reintentar el transporte.
- **Checks ejecutados:** `city_validation_ledger.py` sobre snapshot actual devuelve `runtime_inputs_status=stale`, `missing_runtime_inputs=[]`, `manifest_drift_inputs=[]`; `system_alignment_check.py --decision-mode operational` falla con `error=2` por `runtime_manifest` stale y `runtime_policy_effective_view` stale. No se tocó lógica del bot ni policy live.
- **Siguiente acción concreta:** renovar auth Railway y repetir `powershell -ExecutionPolicy Bypass -File .\tools\railway_runtime_snapshot_pull.ps1`; después regenerar `runtime_policy_effective_view`, `city_validation_ledger`, `city_promotion_gate` y `system_alignment_check --decision-mode operational`. Hasta entonces, City Intelligence debe seguir fail-closed sin recomendaciones por ciudad.

**Última actualización:** 21 de abril de 2026 (Sesión 213 — checkpoint condition_filtered día 7, WR=40% n=5, OK)
**Sesión 213 (21 abr 2026, Sonnet):** checkpoint programado día 7 del canary `condition_filtered` exact/range (abierto 2026-04-14). Métricas al 2026-04-21: **WR bot = 40.0% (2/5)**. Por ciudad: Seoul 1/2 (50%), Tokyo 1/1 (100%), London 0/1 (0%), Shanghai 0/1 (0%). Estado: **✅ OK** — el umbral de cierre es WR < 50% con n ≥ 15; con n=5 no se cumple la condición de muestra mínima, por lo que el canary continúa sin cambios. No se activa kill-switch (requiere WR < 45% con n ≥ 20 rolling). Sin cambios en Railway, bot.py, trading core ni policy live. Próximo checkpoint: **2026-04-28** (día 14 — decisión final: promover si WR ≥ 55% n ≥ 30, extender si WR 50-55%, cerrar si WR < 50%).

**Última actualización:** 21 de abril de 2026 (Sesión 212 — lectura diaria traders-vs-bot sin gap operativo real)
**Sesión 212 (21 abr 2026, Codex):** se registra el parte diario del summary `traders vs bot` y `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler, reglas de entrada/salida ni trading core. Foto UTC del 2026-04-21: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=19`; frente a la serie reciente de 7 corridas, las medianas quedan en `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=25`, y la lectura operativa es que el gap traders-vs-bot se está cerrando respecto al inicio de la serie. No aparece hoy un gap operativo fuerte fuera de `blocked` con consenso y condición operable; por tanto no se abre cambio inmediato de reglas.
- **TRADER_ONLY persistente:** en `7/7` corridas siguen `Ankara`, `Busan`, `Houston`, `Jakarta` y `Miami`; casi persistentes `6/7`: `Amsterdam`, `Buenos Aires`, `Chengdu`, `Helsinki`, `Kuala Lumpur` y `Los Angeles`.
- **Blocked signals fuera de whitelist:** resueltas `117`, wins `114`, WR `97.4%`, con `148` señales excluidas por whitelist. La lectura sigue reforzando que el frente `condition_filtered`/quality traders merece seguimiento, pero no autoriza por sí solo tocar reglas core en esta sesión.
- **Instrucción operativa fijada:** si el bloque `TRADER_ONLY` persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA de esas ciudades antes de tocar reglas de entrada o trading core.

**Última actualización:** 21 de abril de 2026 (Sesión 211 — cierre del frente Windows/WSL y takeover directo desde Codex)
**Sesión 211 (21 abr 2026, Codex):** se reconstruye la sesión tras un reinicio forzado por la instalación de WSL y se cierra con una lectura operativa ya estabilizada del frente “permisos Windows”. El problema base no era una ACL persistente rota del repo, sino una mezcla de fricción del runtime local de Windows: en sesiones anteriores ya se había probado que Codex/VS Code podía inyectar proxies `127.0.0.1:9` y PATH sandboxed en el proceso actual, y además seguían apareciendo dos roces concretos al validar tooling local: temporales fuera del repo y escritura/borrado de artefactos Python bajo locks de Windows. Para endurecer ese frente sin tocar `bot.py`, `verify_before_deploy.py` deja de depender de `tempfile.gettempdir()` y pasa a usar `.tmp_verify/` dentro del repo para sus ficheros temporales, mientras `tools/check_python_syntax.py` añade una validación de sintaxis sin generar `.pyc` ni depender de `__pycache__`.
- **WSL queda confirmado como vía de escape operativa, no como requisito del proyecto:** se instala Ubuntu en WSL2, se completa la creación del usuario Unix y se valida que el repo abre bien desde `/mnt/c/Projects/polymarket-bot`, con `git` saneado mediante `safe.directory` y `python3 3.12.3` disponible. La instalación no se hizo porque el bot necesitara Linux para correr, sino para disponer de una shell limpia fuera del sandbox problemático y separar fallos del entorno Windows/Codex de fallos reales del repo.
- **Verificación definitiva de red y takeover real por parte de Codex:** primero se comprueba manualmente en WSL que `https://data-api.polymarket.com/trades?limit=1` responde `200` cuando la petición lleva `User-Agent`, y que `python3 tools/polymarket_api_probe.py` devuelve `200` en `trades` y `positions`. Después se valida el paso clave para sesiones futuras: Codex ya puede invocar Ubuntu directamente con `wsl -d Ubuntu bash -lc "..."` y ejecutar él mismo el probe del repo con resultado `200/200`, sin depender de que Pablo pegue comandos manualmente. La conclusión operativa queda cerrada: WSL sí resuelve el frente de entorno para verificaciones y tooling manual/directo, mientras que los wrappers repo-locales (`tools/run_clean_network.ps1`, `tools/railway_safe.ps1`) siguen siendo la vía correcta en Windows cuando toque trabajar fuera de WSL.
- **Cierre de validación local:** `python tools/check_python_syntax.py verify_before_deploy.py tools/check_python_syntax.py tools/append_agent_event.py` pasa en verde y `python verify_before_deploy.py` vuelve a cerrar completo en **746/746**, con lo que el harness deja de depender del `%TEMP%` problemático que había quedado documentado en la sesión W17.

**Última actualización:** 19 de abril de 2026 (Sesión 210 — intra-SL reactivado + MIN_EDGE low-price buffer + alarma Steps 2+3)
**Sesión 210 (19 abr 2026, Sonnet+Opus):** análisis de la operación London NO@23¢→46¢→SL@1¢ y corrección de dos problemas estructurales. **Problema 1 — ventana de ciclo:** el intra-cycle SL/TP monitor (`INTRA_SL_INTERVAL`) fue desactivado en v10.6.0 como revert conservador, pero la causa real del problema de v10.5 era la sigma ampliada + re-eval, no el monitor; `intra_cycle_sl_check` solo hace SL+TP por PnL%, nunca re-evaluación. **Fix v10.6.24:** `INTRA_SL_INTERVAL` default reactivado a 60 min, thread `IntraSL` corre en paralelo al ciclo principal (8/16/23 UTC). **Problema 2 — asimetría TP/SL por precio:** Opus analizó que el edge en % no ajusta al nivel de precio; a 20¢ un error ±10pp en `our_prob` puede convertir EV+ en EV−. El SL en % también puede dispararse por ruido en posiciones baratas. **Fix v10.6.25:** `MIN_EDGE_LOW_PRICE_BUFFER_PP=5.0` + `LOW_PRICE_THRESHOLD=0.35` — posiciones con `mkt_price<0.35` requieren 5pp extra de edge en el path de compra. Solo afecta entradas, no TP/SL. **Plan pendiente Steps 2+3:** TP escalonado por precio de entrada (60%/40%/80%) y SL absoluto en centavos; guardados en engram + alarma one-shot `maybe_alert_tp_sl_price_steps` con `FIRE_DATE=2026-05-10` para revisarlos tras 3 semanas de datos. Precondición antes de implementar: analizar WR+PnL por bucket de precio [0.20-0.35]/[0.35-0.65]/[0.65-0.80]; si bucket bajo tiene WR≥50% y PnL≥0, cerrar plan sin implementar. `verify_before_deploy.py` pasa **743/743**. Deploy pendiente.

**Última actualización:** 19 de abril de 2026 (Sesión 210 — observabilidad condition_filtered exact/range por ciudad canary)
**Sesión 210 (19 abr 2026, Codex):** patch corto de observabilidad en `bot.py`, disparado tras revisar el `decisions.log` live del `2026-04-18` y detectar que varias ciudades `canary` (`Shanghai`, `New York City`, `Atlanta`, `Munich`) seguían apareciendo en texto como `SHADOW-FILTER` aunque el `skip_log` ya mostraba `city_mode="canary"` y `allowlisted=true`. La auditoría cerró que no había bug de reconocimiento de modo: el carve-out `exact/range` sí reconoce correctamente a la ciudad como `canary`, pero el gate además exige `match_key` en `signals.json`; cuando ese cruce falta, el evento caía a `condition_filtered` con copy engañosa. Cambio aplicado: el log detallado pasa a emitir `CANARY-FILTER` para ciudades `active/canary` y conserva `SHADOW-FILTER` para ciudades realmente fuera de allowlist; además `skip_log.jsonl` guarda `extras.filter_label`, `extras.exact_range_gate_reason` y `extras.qt_match_key` para distinguir causas como `no_quality_trader_signal_match` o `city_not_in_quality_trader_whitelist` sin tener que reabrir auditorías manuales sobre texto ambiguo. No se toca trading core, NOAA, scheduler, sizing ni policy live. Validación local cerrada con `python verify_before_deploy.py`.

**Última actualización:** 19 de abril de 2026 (Sesión 209 — auditoría blocked_signals post-Apr-18, confirmación checkpoint día 7)
**Sesión 209 (19 abr 2026, Sonnet):** auditoría read-only de `data/blocked_signals_resolutions.jsonl` desde Railway con datos frescos hasta Apr 18. Objetivo: verificar si WR de quality traders en señales `exact/range` se mantiene ≥55% para confirmar la decisión del checkpoint día 7 (2026-04-21). Resultado: **WR=97.0% (223/230)**, vs baseline Apr-13 de WR=76.3% (n=59). Post-Apr-13 exclusivamente: **n=155, WR=97.4%** — la tendencia no bajó, subió. Por condición: `exact` 96.7% (203/210), `range` 100% (20/20). Total 7 pérdidas con `close_price=0.0`: 5 de `Pricey-Score`, 1 de `Thrifty-Original`, 1 de `Shy-Advertising`; **Loyal-Aggression: cero pérdidas**. No se tocó `bot.py` ni Railway. **Veredicto: checkpoint día 7 confirmado con máxima confianza — ninguna señal para revertir `condition_filtered` antes del Apr 21.** El monitor automático `maybe_run_condition_monitor(state)` en `run_observability_alerts()` disparará el Apr 21 y evaluará los trades reales del bot en exact/range desde Apr 14.

**Última actualización:** 19 de abril de 2026 (Sesión 208 — auditoría skip_log `price_out_of_range` por ciudad canary)
**Sesión 208 (19 abr 2026, Codex):** auditoría operativa read-only sobre `data/runtime_import/skip_log.jsonl` para responder si el bucket `price_out_of_range` esconde ciudades `canary` prácticamente inoperables por quedar siempre fuera del rango `[0.20, 0.80]`. Se trabaja con el snapshot live pullado de Railway el `2026-04-18T09:28:57Z`, comparando histórico completo (`79` ciclos / `19,267` skips) contra ventana reciente de `30` ciclos (`2026-04-14T09:41` → `2026-04-18T09:27`), sin tocar `bot.py`, policy live ni thresholds. Hallazgo central: sí hay concentración fuerte por ciudad, especialmente en `Seoul`, `Tokyo` y `Shanghai`, donde `price_out_of_range` domina `84-87%` de los skips recientes; `London`, `New York City` y `Munich` también muestran presión relevante, mientras `Atlanta` queda bastante más balanceada. El patrón no viene de mercados caros `>0.80`, sino casi por completo de precios ultrabajos `<0.20` en todas las canary del snapshot. **Decisión operativa cerrada:** no cambiar el filtro global `[0.20,0.80]`, no degradar canaries solo por este readout y reencuadrar el frente como un subcaso de precios bajos, no como fallo general del guardrail. Se deja marcado que `Seoul/Tokyo/Shanghai` son hoy las canary donde `price_out_of_range` más probablemente estrangula la oportunidad práctica; `Atlanta` sale de prioridad inmediata y `London/NYC/Munich` quedan en zona intermedia. Si el tema se reabre, el siguiente bloque honesto será una micro-auditoría por ciudad del bucket `<0.20` con ventana fresca post-`v10.6.23`. Artefacto nuevo: `docs/price-out-of-range-canary-audit-2026-04-19.md`.

**Última actualización:** 19 de abril de 2026 (Sesión 207 — auditoría execution layer + fix buy_min_size v10.6.23)
**Sesión 207 (19 abr 2026, Sonnet):** auditoría completa del cuello de ejecución ("25 candidatos → 2 edges → 0 buys") y fix del bug residual `buy_min_size`. Hallazgos de la auditoría: (1) el ciclo Apr 17 04h murió por `buy_min_notional` (ya corregido en Sesión 188); el Apr 18 04h mejoró a 1/2 buys pero Tokyo NO 22°C falló por `"Size (2) lower than the minimum: 5"` — Polymarket impone mínimos de shares por mercado, y el `CANARY_POSITION_SCALE=0.50` puede reducir shares por debajo de ese mínimo (sin escalar: 5.02 shares; con escala: 2.51 → 2 shares → fallo). (2) Los 26 `kelly_too_low` Apr14-17 eran 100% Seoul/Incheon mismatch (`our_prob=99%` activando el guard `>=0.99` en `kelly_fraction`), completamente resueltos tras el fix de Sesión 185. (3) La pérdida 25→2 edges no es un bug: `price_out_of_range` (116 same-day) y `condition_filtered` (21) filtran correctamente; el 220 de `fuera ACTIVE_TRADING_CITIES` (shadow) es el mayor supresor y requiere onboarding de ciudades canary con proceso validado. **Fix implementado en v10.6.23:** `_parse_min_shares_from_error(msg)` extrae el mínimo de shares del mensaje de error de Polymarket; en el loop de ejecución, tras un fallo `buy_min_size`, se intenta retry con `min_shares` si `min_shares × price ≤ MAX_BET_PCT × effective_bankroll` (hard cap Kelly nunca superado); si excede, se loguea `SKIP RETRY MIN SHARES` y no se ejecuta. El hard cap mantiene el tope absoluto de $2.50 (10% de $25). Para el caso Tokyo confirmado: 5 shares × $0.49 = $2.45 ≤ $2.46 → habría pasado. `verify_before_deploy.py` pasa **735/735** (5 tests nuevos v10.6.23). Deploy autorizado y pusheado a Railway.

**Última actualización:** 19 de abril de 2026 (Sesión 206 — exact/range canary min amount + cierre de pendiente stale)
**Sesión 206 (19 abr 2026, Codex):** se ejecuta un patch corto orientado a throughput/calidad de ejecución sobre el cuello de `position management`, sin tocar NOAA core, scheduler ni reglas base de edge. El contexto reciente ya había cerrado los frentes más obvios (`condition_filtered` YES-side, slot `23h`, expansión de whitelist y summary diario `traders vs bot`), así que la sesión se centra en el siguiente cuello abierto por Opus: el exceso de cierres `micro_position_unsellable`. Ajuste aplicado en `bot.py`: nuevo guardrail `EXACT_RANGE_MIN_AMOUNT` (default `2.50`) solo para `exact/range canary`; tras el escalado canary y el `EXACT_RANGE_SIZE_SCALE`, si la posición queda por debajo de ese suelo se recompone con `_resize_position_amount()` hasta el mínimo operativo permitido por el cap actual (`MAX_BET_PCT`). La intención no es “apostar más” globalmente, sino evitar que el carve-out `exact/range canary` siga naciendo en tamaños demasiado microscópicos para una salida útil. Validación local cerrada: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` **730/730**. Hallazgo adicional de contexto: el supuesto pendiente de Railway para `QUALITY_TRADER_CITIES_WHITELIST +Jakarta,Kuala Lumpur` ya estaba resuelto live; se confirma que la env de producción ya incluye ambas ciudades, así que deja de ser una tarea abierta real para futuras sesiones.

**Última actualización:** 19 de abril de 2026 (Sesión 205 — cleanup Railway + lectura de impacto bankroll)
**Sesión 205 (19 abr 2026, Codex):** se cierra la cola operativa que había quedado tras la activación del summary `traders vs bot`. El servicio vacío `signals-crosscheck`, creado durante la prueba inicial de despliegue separado, se elimina de Railway para no dejar ruido ni superficies muertas en el proyecto; la limpieza se hace por API GraphQL (`serviceDelete`) porque la CLI pública de Railway sigue sin exponer borrado de servicios, y se verifica después que en `production` solo quedan `polymarket-bot`, `city-intelligence` y `phase5-visibility`, todos en `SUCCESS`. Lectura estratégica cerrada para sesiones futuras: esta actualización no aumenta bankroll por sí sola, pero sí mejora el feedback loop de asignación de capital, porque convierte un análisis manual discontinuo en una señal diaria automática sobre dónde los quality traders ven oportunidades que el bot todavía no monetiza. Eso reduce tiempo muerto humano, acorta el tiempo entre evidencia y decisión de whitelist/canary/observación, y evita seguir creciendo el bankroll a ciegas con gaps estructurales sin revisar.

**Última actualización:** 19 de abril de 2026 (Sesión 204 — activación live del summary traders vs bot)
**Sesión 204 (19 abr 2026, Codex):** se activa en producción el feedback loop diario `traders vs bot` sin introducir un servicio que compita con el bot principal. Hallazgo operativo clave durante la activación: Railway no permite montar `polymarket-bot-volume` en un segundo servicio a la vez, así que el servicio nuevo `signals-crosscheck` no sirve como reader del runtime live sin desmontar el bot; se decide no tocar ese volumen y se redirige la activación al camino más seguro. Ajuste mínimo en `bot.py`: tras `maybe_run_daily_crosscheck(state)` el bot invoca `tools/signals_crosscheck_daily_summary.py` vía subprocess apuntando al mismo `SIGNALS_CROSSCHECK_FILE` live (`/app/data/signals_crosscheck.jsonl`), con lo que la serie temporal y el summary comparten exactamente la misma fuente de verdad. Validación local previa: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` pasa **727/727**. Deploy live realizado en Railway sobre `polymarket-bot` (`deployment 58683196-662f-4647-843a-4e9f84b8d02f`, estado `SUCCESS`); arranque nuevo visible a `2026-04-19 10:10:41 UTC`. Verificación live cerrada por SSH dentro del contenedor: `python tools/signals_crosscheck_daily_summary.py --crosscheck-file /app/data/signals_crosscheck.jsonl` escribe `signals_crosscheck_daily_summary_state.json`, genera `docs/signals_crosscheck_daily_summary_latest.md` y envía Telegram real (`telegram_result.sent=true`). La lectura enviada hoy usa **7 corridas** y confirma `gap_state=estructural`, con 8 ciudades `TRADER_ONLY` persistentes en `7/7` (`Ankara, Houston, Jakarta, Kuala Lumpur, Madrid, Miami, Paris, Wellington`). Queda activado para futuras corridas automáticas del bot sin trabajo manual adicional.

**Última actualización:** 19 de abril de 2026 (Sesión 203 — cross-check traders vs bot automatizado en Railway)
**Sesión 203 (19 abr 2026, Codex):** se automatiza la capa humana del cross-check `traders vs bot` sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. Cambio 1: `tools/signals_vs_edge_crosscheck.py` se refactoriza para que su lógica sea reutilizable y configurable por path, manteniendo el modo standalone pero dejando `build_crosscheck_record()` + `append_record()` listos para otros servicios; además la validación deja de romper si `Austin` no aparece en el snapshot actual y solo exige ese check cuando la ciudad está presente en `signals.json`. Cambio 2: se crea `tools/signals_crosscheck_daily_summary.py`, que lee `data/signals_crosscheck.jsonl` (o fallback local `data/runtime_import_derived/signals_crosscheck.jsonl`), deduplica por día UTC, opcionalmente ingiere la corrida de hoy si falta, resume la serie reciente (medianas MATCH/BOT_ONLY/TRADER_ONLY, ciudades TRADER_ONLY persistentes, gap operativo del día), envía Telegram con anti-spam diario y guarda estado en `data/signals_crosscheck_daily_summary_state.json`. Cambio 3: se añade `tools/signals_crosscheck_railway_service.py` como loop Railway diario y `docs/signals-crosscheck-railway-service.md` con comando/vars recomendadas; `.gitignore` ahora cubre `data/signals_crosscheck.jsonl` y el state del summary para no ensuciar el worktree. Validación local: `python tools/signals_vs_edge_crosscheck.py --no-append` OK, `python tools/signals_crosscheck_daily_summary.py --crosscheck-file data/runtime_import_derived/signals_crosscheck.jsonl --dry-run` OK, `python tools/signals_crosscheck_railway_service.py --once` OK (sin Telegram real por env ausente).

**Última actualización:** 19 de abril de 2026 (Sesión 202 — city intelligence alerts hardening + Windows lock diagnosis)
**Sesión 202 (19 abr 2026, Codex):** cierre corto de hardening en la capa `city intelligence`, sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Se corrigen dos problemas de alertas humanas: (1) `tools/city_intelligence_telegram_alert.py` ahora solo dispara sobre `gate_status` realmente accionables (`now/soon` + allowlist explícita), con lo que ciudades ya degradadas a `background_watch` como `Dallas` dejan de reabrirse como foco falso; validación local con `--dry-run` sobre el gate actual: `should_alert=false`, `new_rows_count=0`. (2) `tools/city_intelligence_daily_summary.py` deja de mezclar filas del ledger con instrucciones de otra ciudad del gate: el bloque “Lectura del sistema” y la “Instrucción para Codex” pasan a salir de la misma selección coherente, y además se añade anti-spam diario vía `last_sent_date` para evitar el doble disparo del mismo resumen cuando lo ejecutan más de un servicio; validación local: segunda invocación el mismo día devuelve `telegram_result.reason=already_sent_today`. Hallazgo operativo adicional documentado para no reabrir la investigación: los fallos de borrado/rename en `.tmp_*` y `tools/__pycache__`, y los `py_compile` fallidos sobre tools, no son un problema de ACL NTFS sino de handles abiertos por `Code.exe`/`codex`; escribir en `__pycache__` sí funciona, pero borrar/renombrar falla mientras VS Code vuelve a abrir el workspace. Quedan fuera del commit los `.tmp_*` de validación. Próxima sesión: si se quiere limpiar ese frente, cerrar VS Code antes de validar o aceptar que `py_compile` en tools puede seguir fallando por lock aun con fuente correcta.

**Última actualización:** 19 de abril de 2026 (Sesión 201 — Jakarta + Kuala Lumpur ICAO-only v10.6.22)
**Sesión 201 (19 abr 2026, Opus):** cierre del handoff `docs/handoff-noaa-jakarta-kuala-lumpur.md`. Se agregan Jakarta y Kuala Lumpur a `RESOLUTION_STATIONS`, `RESOLUTION_ICAO`, `CITY_TIMEZONES`, `OBSERVED_AUDIT_CITIES` y al default de `QUALITY_TRADER_CITIES_WHITELIST` en `bot.py`. **Verificación de fuente Polymarket (WebFetch):** Jakarta resuelve contra **Halim Perdanakusuma (WIHH)** — NO Soekarno-Hatta (WIII) como sugería el handoff inicial — vía Wunderground `https://www.wunderground.com/history/daily/id/jakarta/WIHH`; Kuala Lumpur resuelve contra **KLIA (WMKK)** vía WU `https://www.wunderground.com/history/daily/my/sepang-district/WMKK`. **Verificación NOAA:** `isd-history.csv` confirma WIHH USAF `967495` → ISD `96749599999` y WMKK USAF `486500` → ISD `48650099999`, pero los CSV `global-hourly/access/2026/*.csv` devuelven 404 para ambos (feed SE Asia parado ~fin-agosto 2025); el `ghcnd-inventory.txt` marca TMAX hasta 2025 para `ID000096745` (Jakarta/Observatory), `IDM00096741` (Tanjung Priok), `IDM00096749` (Soekarno-Hatta) y `MYM00048650` (KLIA), pero el `ghcnd/by_year/2026.csv.gz` NO contiene ni una fila TMAX para ninguna estación indonesia/malaya (contraste: Tokyo/NYC/Atlanta tienen datos hasta Apr 16 2026). Conclusión: ambas ciudades entran en **configuración ICAO-only** (mismo patrón que Singapore, Toronto, Warsaw) — el bot podrá tradear vía WU pero los trades no llevarán `source: noaa_ncei` y no contarán en WR verificado hasta que NOAA retome el feed. Coords: Jakarta `(-6.2666, 106.8906)`, KL `(2.7456, 101.7099)`. `verify_before_deploy.py`: 9 tests nuevos (Jakarta/KL en cada estructura + whitelist default), pasa **727/727** (incluye traza de esta sesión). Pendiente Pablo: actualizar Railway env `QUALITY_TRADER_CITIES_WHITELIST` agregando `,Jakarta,Kuala Lumpur` al final.

**Última actualización:** 19 de abril de 2026 (Sesión 200 — análisis 7 corridas cross-check + whitelist +6 ciudades v10.6.21)
**Sesión 200 (19 abr 2026, Sonnet):** análisis de la serie temporal completa de cross-check traders vs bot (7 corridas automáticas del bot en Railway, Apr 13-19) y expansión del `QUALITY_TRADER_CITIES_WHITELIST`. Hallazgos clave: 8 ciudades son permanentemente TRADER_ONLY en 7/7 corridas (Ankara, Houston, Jakarta, Kuala Lumpur, Madrid, Miami, Paris, Wellington) y 15 ciudades más con 6/7. El ratio MATCH/TRADER_ONLY no converge — el gap estructural se mantiene en ~25 ciudades con mediana estable; Apr 16 fue outlier (15 TRADER_ONLY) por baja cobertura trader ese día. Austin y Toronto aparecen 6/7 (1 ausencia cada una). Las 7 corridas viven en Railway `/app/data/signals_crosscheck.jsonl` — el archivo local solo tiene corridas manuales. **v10.6.21:** se agregan Ankara, Madrid, Miami, Paris, Wellington, Houston al whitelist. Houston también añadida a `RESOLUTION_STATIONS` (KIAH, lat 29.9902 lon -95.3368) y `RESOLUTION_ICAO` (KIAH sin `noaa_station_id`, pendiente verificación vs Polymarket resolution source). Se actualiza el default en `os.getenv("QUALITY_TRADER_CITIES_WHITELIST", ...)` en `bot.py` y la env var en Railway. Jakarta y Kuala Lumpur quedan pendientes por falta de NOAA verificado — ver `docs/handoff-noaa-jakarta-kuala-lumpur.md`. `verify_before_deploy.py` pasa **718/718**.

**Última actualización:** 18 de abril de 2026 (Sesión 199 — P1 fix + alertas P4-P7 v10.6.20 + anti-flapping NYC)
**Sesión 199 (18 abr 2026, Opus):** paquete de throughput sin tocar trading core, NOAA core, scheduler ni policy live. Motivación: Pablo pide acelerar bankroll $25→$50 con evidencia acumulada (quality traders WR=76.3% n=59 en exact/range, 21 ciudades TRADER_ONLY sin observación bot, slot 16-04 UTC dormido 12h). Cambios en `bot.py` elevando versión a `v10.6.20`: (1) **P1 — ciudades invisibles al pipeline**: se añaden `Lucknow` y `Sao Paulo` a `OBSERVED_AUDIT_CITIES`, ambas con `RESOLUTION_STATIONS`/`RESOLUTION_ICAO`/`CITY_TIMEZONES` ya presentes (handoff C sesión 169); `Istanbul` queda diferida porque carece de coords NOAA y añadirla replicaría el riesgo Seoul mismatch (sesión 185). (2) **P4-P5 alerta one-shot** `maybe_alert_p4_p5_expansion(state)` con `FIRE_DATE=2026-04-22` (día posterior al checkpoint condition_filtered día 7): entrega prompt explícito para Codex sobre expandir `QUALITY_TRADER_CITIES_WHITELIST` (si checkpoint cerró OK/PROMOTE) y añadir 3-5 ciudades TRADER_ONLY con NOAA verificado al universo. (3) **P6-P7 alerta one-shot** `maybe_alert_p6_p7_post_v2_cleanup(state)` con `FIRE_DATE=2026-04-25` (3 días tras cutover V2): prompt para reset `shadow_city_tracking` Seoul legacy pre-fix + análisis MIN_EDGE por ciudad (sin aplicar). Ambas alertas siguen el patrón `maybe_run_w17_observation_alert` (date-triggered, state flag one-shot, anti-spam daily). Se integran en `run_observability_alerts()` tras w17 y antes de slot monetization. **Fix adicional cierre de sesión — anti-flapping shadow↔canary (New York City):** Pablo observa en Telegram un loop donde NYC se degrada canary→shadow por `verified_history_bad` (NOAA-verificado 2/25 trades, WR 8.0%, PnL $-0.24) y se re-promociona shadow→canary inmediatamente en el mismo o siguiente ciclo por `promotable_shadow` (11 edges, 64 ciclos, pico 50.5%). Causa raíz: en `bot.py` líneas 5786-5799, `promotable_shadow` evaluaba solo métricas shadow y era independiente de `verified_history_bad`; la degradación (`removable_active`) sí usa el segundo, pero la promoción ignoraba el primero, de modo que una ciudad con histórico NOAA-verificado malo podía re-promocionarse infinitamente por evidencia shadow acumulada vieja. Fix mínimo: se reordena el cálculo (`verified_history_bad` ahora se computa antes que `promotable_shadow`) y se añade `and not verified_history_bad` al tuple de `promotable_shadow`. Se actualiza el branch `observe` con reason explícita (`"historial NOAA-verificado malo (...); promoción a canary bloqueada hasta reunir evidencia nueva mejor"`) para que Telegram/dashboard no muestre "falta decidir si merece canary" cuando en realidad la promoción está bloqueada por historial. Tareas pendientes para Pablo (Railway env vars, no código): **P1 env** — ya hecho (`ACTIVE_TRADING_CITIES=NONE`); **P2** — ya hecho (`SCHEDULE_HOURS_UTC=4,8,12,16`); **P3** — actuar sobre alertas de `notify_active_candidates` cuando las reciba. `verify_before_deploy.py` pasa **717/717** (16 tests nuevos: 13 v10.6.20 base + 3 anti-flapping). Deploy autorizado por Pablo (Opción A).

**Última actualización:** 18 de abril de 2026 (Sesión 198 — migración CLOB V2 SDK)
**Sesión 198 (18 abr 2026, Sonnet):** se migra el bot al SDK CLOB V2 de Polymarket antes del cutover del 22 de abril de 2026 (~11:00 UTC), fecha en que los clientes V1 dejan de funcionar completamente. La migración requirió 5 cambios en 2 archivos (`requirements.txt` y `bot.py`), descubiertos iterativamente via errores de Railway: (1) `requirements.txt`: `py-clob-client==0.34.6` → `py-clob-client-v2==1.0.0`; (2) `bot.py` imports: módulo renombrado `py_clob_client.*` → `py_clob_client_v2.*`; (3) `bot.py` constructor: `chain_id` se mantiene igual en Python (el rename `chain_id→chain` es solo para TypeScript, la doc mezclaba ambos lenguajes); (4) `bot.py` auth: `create_or_derive_api_creds()` → `create_or_derive_api_key()`; (5) `bot.py` órdenes: `get_orders()` → `get_open_orders()`. El error 400 en `/auth/api-key` al arrancar es esperado: `create_or_derive_api_key()` intenta crear primero, falla porque la key ya existe y hace fallback a derivar; el log confirma "Autenticación OK". `tools/`, `city_intelligence`, `phase5_visibility`, `find_traders.py` y `trader_analyzer.py` no usan el SDK CLOB directamente (consumen REST vía `requests`/`httpx`) y no requirieron cambios. Commits: `58cf355`, `e132c7e`, `b7762bd`, `ef63efc`, `4cc94a6`. Bot verificado en Railway en Modo REAL.

**Última actualización:** 18 de abril de 2026 (Sesión 197 — NOAA coverage queue hardening)
**Sesión 197 (18 abr 2026, Codex):** se endurece el embudo `observed_vs_forecast` para dejar de perder cobertura NOAA en ciudades canary/observadas por starvation de cola, sin tocar trading core, scheduler, NOAA fetcher base ni policy live. Diagnóstico de partida: el snapshot local mostraba muestra NOAA solo para `Atlanta`, mientras `London`, `Munich`, `New York City`, `Shanghai` y `Tokyo` sí tenían BUYs maduros en `performance.json` pero seguían sin entrar en `audit.json`; la causa raíz quedó aislada en `audit_check_resolution_truth()`, que procesaba solo `to_check[:10]`, repetía varios `city|date` del mismo día y no dejaba cooldown cuando NOAA devolvía vacío, de modo que el backlog fallido podía ocupar siempre los primeros slots. Patch aplicado en `bot.py`: nuevos límites `OBSERVED_AUDIT_MAX_SUCCESSES_PER_RUN=10`, `OBSERVED_AUDIT_MAX_ATTEMPTS_PER_RUN=40` y `OBSERVED_AUDIT_FAIL_COOLDOWN_HOURS=12`; dedupe por `city|date`; prioridad a ciudades con menor muestra acumulada y a candidatos `perf_buy` frente al fallback shadow; y trazabilidad de fallos NOAA en `audit["errors"]` con `source=noaa_ncei` / `kind=observed_vs_forecast_fetch_failed` para evitar reintentos ciegos cada ciclo. También se amplía `verify_before_deploy.py` con un test de dedupe `city|date`. Validación local: `python verify_before_deploy.py` vuelve a cerrar en **703/703**; `py_compile` sigue pudiendo fallar por lock de `__pycache__` en Windows, pero la suite funcional quedó verde. Resultado esperado compartido para próximas sesiones: la cobertura NOAA debería empezar a poblar antes en `London`, `Munich`, `NYC`, `Shanghai` y `Tokyo`, y recién con esa muestra nueva reevaluar posibles station mismatches.

**Última actualización:** 18 de abril de 2026 (Sesión 196 — TP dinámico alta convicción)
**Sesión 196 (18 abr 2026, Sonnet):** se implementa TP dinámico en `bot.py` sin tocar trading core, NOAA, scheduler ni policy live. Motivación: el NYC NO del 17-abr compró a $1.19 con `our_prob=85%`; el TP fijo `+40%` habría cerrado prematuramente una posición que con el forecast ≥3°C del umbral podría haber llegado a resolución (+172%). Cambios: dos env vars nuevas `HIGH_CONVICTION_TP_PCT` (default 80%) y `HIGH_CONVICTION_PROB_THRESHOLD` (default 0.80); en `manage_positions` se construye un dict `_lc_by_token` cruzando `trade_lifecycle.json` via `entry_context.our_prob` keyed por `token_id`, y el CHECK 2 pasa a usar `effective_tp` dinámico con tag `[conv=XX%]` en el mensaje; la misma lógica se replica en `intra_cycle_sl_check`. Gotcha clave: `our_prob` no está en el dict de posición de la API de Polymarket, hay que cruzar con lifecycle. `verify_before_deploy.py` cierra en **702/702**.

**Última actualización:** 18 de abril de 2026 (Sesión 195 — cierre de revisión total de alarmas)
**Sesión 195 (18 abr 2026, Codex):** se cierra la revisión completa del lote actual de alarmas con criterio operativo estricto, sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Primero se auditan una a una las alarmas activas y se fuerza su cierre útil: las dos lecturas legacy de `Phase 5 Visibility` (`gap + siguiente paso` sobre `Shanghai + Chicago`) quedan explícitamente tratadas como formato ya superado por la sesión 194 y, por tanto, pasan a considerarse `alarma reescrita/eliminada` sin volver a abrir sesión por sí solas; la alarma de `Slot monetization review` deja de arrastrar `23h UTC` cuando ese slot ya está deshabilitado por `SCHEDULE_DISABLED_HOURS_UTC=23`; y la alarma diaria `Cross-check traders vs bot` deja de elevar como oportunidades casos estructurales o débiles (`Toronto` blocked conocido, `Guangzhou` sin consenso) porque la capa humana ya se reescribió para mostrar solo gap operativo real. Segundo, la revisión de `City Intelligence` aterriza en un cambio read-only concreto: se introduce en `tools/city_validation_ledger.py` el bottleneck `weak_city_hypothesis` para ciudades con observación shadow repetida pero sin edge propio útil (`edge_hits=0`, `cycles_seen>=5`, `markets_seen>=8`), y `tools/city_promotion_gate.py` lo traduce a `background_watch` con prioridad `later` en vez de seguir tratándolo como review activa cercana a monetización. Se regeneran `data/city_validation_ledger.json`, `docs/city_validation_ledger_latest.md`, `data/city_promotion_gate.json` y `docs/city_promotion_gate_latest.md`; la foto nueva reduce ruido de revisión y deja el queue centrado en canaries runtime reales (`Shanghai`, `Seoul`, `Tokyo`, `NYC`, `Atlanta`, `Munich`) y en source fidelity genuino (`Wuhan`, `Hong Kong`). La compilación de los tools no se pudo cerrar por un lock de `__pycache__` en Windows, pero la ejecución real de ambos scripts pasó y escribió artefactos nuevos, así que la salida operativa de la sesión queda cerrada como `gate definido + alarmas legacy eliminadas/reescritas`.

**Última actualización:** 18 de abril de 2026 (Sesión 194 — alarmas deben cerrar en salida operativa)
**Sesión 194 (18 abr 2026, Codex):** se convierte en regla operativa explícita que las alarmas del sistema ya no pueden cerrarse solo con documentación o análisis. Criterio nuevo para sesiones futuras: toda alarma debe terminar en una de cuatro salidas útiles para monetización: `cambio ejecutado`, `patch listo`, `gate definido` o `alarma reescrita/eliminada`; si no provoca ninguna de esas salidas, debe desaparecer o rediseñarse. Se implementa esta regla en la capa `Phase 5 Visibility`: `tools/phase5_operational_action.py` pasa a emitir `closure_type`, `closure_label` y `operational_change`, y `tools/phase5_visibility_telegram_alert.py` incluye en el mensaje el `cierre obligatorio` y el `cambio operativo` para que la alarma deje de ser un FYI y pase a abrir una acción concreta. La decisión compartida para la siguiente sesión queda fijada así: no volver a discutir “qué significa” una alarma; discutir solo qué cambia en operativa por haber saltado y con cuál de las cuatro salidas se cierra. Esta sesión no toca `bot.py`, trading core, NOAA core, scheduler ni policy live; cambia workflow y contrato de cierre de alarmas.

**Última actualización:** 18 de abril de 2026 (Sesión 193 — Phase 5 visibility coincidence rises to 11)
**Sesión 193 (18 abr 2026, Codex):** se alinea la trazabilidad local de `Phase 5 Visibility` con una nueva coincidencia real reportada por el probe, sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. El evento nuevo queda fijado en `probe=2026-04-18T01:58:33+00:00`: `Shanghai=2 mercados`, `Chicago=2 mercados`, `coincidencias acumuladas=11`. La lectura operativa no cambia de tesis, pero sí sube en persistencia: el `dominant_gap` sigue siendo `evidence_asymmetry_between_shadow_and_active` y el siguiente paso sano sigue siendo `use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence`. Para evitar drift entre repo y lectura compartida, se actualizan los artefactos `docs/city_probe_visibility_tracker_latest.md`, `docs/shanghai_vs_chicago_comparator_latest.md`, `docs/phase5_operational_action_latest.md`, `docs/phase5_visibility_pipeline_latest.md` y sus JSON asociados para reflejar esta nueva foto. Decisión metodológica explícita: no se reabre diseño ni se interpreta esta coincidencia como promoción de ciudad; se documenta como refuerzo de visibilidad repetida dentro de una capa legacy/read-only que sigue subordinada a la arquitectura principal.

**Última actualización:** 17 de abril de 2026 (Sesión 192 — Seoul source verification + post-fix evidence protocol)
**Sesión 192 (17 abr 2026, Codex):** se cierra una auditoría operativa centrada en aclarar el estado real de Seoul tras el incidente `forecast_station_mismatch`, sin tocar `bot.py`, Railway ni policy live. Se arranca leyendo `AGENTS.md`, el bloque reciente de `CONTEXTO.md`, `bot.py`, `audit.json`, `city_policy_state.json` y `docs/strategic-review-opus-2026-04-17.md`; la primera lectura local sugería que Seoul seguía `blocked`, pero un pull fresco de `data/runtime_import/` desde Railway confirma que el estado live ya cambió: `auto_blocked_cities` está vacío, Seoul reapareció en `auto_canary_cities` a las `2026-04-17T16:29:31Z`, y el ciclo live `2026-04-17T20:44:48Z` abrió una compra real `Seoul 24°C Apr19 YES` (`edge=29.1%`, `$1.23`) con `city_mode="canary"`. La comprobación decisiva es que la compra sí parece usar la fuente nueva: aunque el runtime siga reportando `BOT_VERSION="v10.6.15"`, tanto el repo actual como el commit `ed00535` mantienen `RESOLUTION_STATIONS["Seoul"] = {"lat": 37.5665, "lon": 126.9780, "name": "Seoul City (KMA)"}`, y los logs live ya muestran forecasts plausibles de Seoul ciudad (`23.6°C` para `Apr18`, `23.8°C` horas después y `25.9°C` para `Apr19`), muy lejos del patrón roto de Incheon (`13.1°C` cuando Seoul real estaba en `19-21°C`). Decisión operativa cerrada para no reabrir el mismo debate: **la posición `Will the highest temperature in Seoul be 24°C or higher on April 19? / Yes 55¢ / 2.2 shares / $1.17` cuenta como la primera evidencia post-cambio de fuente**. Mientras siga abierta no se toca `city_policy_state.json` ni `shadow_city_tracking.json`. Cuando resuelva, el siguiente agente debe aplicar este protocolo exacto: 1) si gana, Seoul se mantiene en `canary` y esta posición pasa a ser `post-fix sample #1`; 2) si pierde, Seoul se degrada a `shadow` y aun así esta posición cuenta como `post-fix sample #1`; 3) en ambos casos, la evaluación futura de Seoul debe usar solo evidencia posterior al cambio de fuente, no el edge histórico contaminado por Incheon; 4) si tras la resolución se decide bajar a `shadow limpia` o evitar autopromoción inmediata, habrá que aislar o resetear el `shadow_city_tracking` legacy para que la promotion logic no vuelva a mezclar los `65 ciclos / 68.5% best edge` de la fuente vieja con la muestra post-fix. La sesión deja por escrito que el bot debe poder actuar solo con que el usuario pegue el estado final de esta posición al cierre.

**Última actualización:** 17 de abril de 2026 (Sesión 191 — telegram wording correctness for crosscheck/blocked signals)
**Sesión 191 (17 abr 2026, Codex):** se cierra una sesión corta de correctness en la capa humana de Telegram, sin tocar trading core, NOAA, scheduler, policy live ni métricas base. Se revisan dos avisos automáticos disparados a primera hora (`Cross-check diario traders vs bot` y `Blocked signals`) y se confirma que el cálculo era correcto pero el wording inducía dos lecturas demasiado fuertes: en el cross-check, la lista mostrada de ciudades actionable no era una priorización sino solo las primeras `4` visibles; en blocked-signals, el texto hablaba de `canary excluido` aunque la exclusión real se hace contra `QUALITY_TRADER_CITIES_WHITELIST`, lo que podía mezclar ciudades hoy ya `blocked` o con estado canónico distinto. Se aplica un patch mínimo en `bot.py`: el primer mensaje ahora declara explícitamente que muestra una `muestra top N de M`, y el segundo pasa a leerse como `Blocked signals (fuera de whitelist)` con nota `Baseline fuera de QUALITY_TRADER_CITIES_WHITELIST`. Validación local: `python -m py_compile bot.py` OK. Estado final: mejora de claridad/correctness en Telegram, sin cambiar contadores, filtros ni decisiones operativas.

**Última actualización:** 17 de abril de 2026 (Sesión 190 — slot scheduler live closure)
**Sesión 190 (17 abr 2026, Codex):** se cierra en live el loop operativo del scheduler por slot. Primero se confirma que Railway seguía con `SCHEDULE_HOURS_UTC=4,8,16,23`, sin `SCHEDULE_DISABLED_HOURS_UTC`, y todavía cargando la env obsoleta `SLOT_04H_REVIEW_REMINDER_DATE`; después se actualiza el handoff `docs/next-session-handoff-2026-04-15-policy-gate-throughput.md` para reflejar que esta línea ya no es una auditoría abierta de `policy_execution_gate`, sino una decisión de monetización sobre slots. Se hace push a `main` del patch ya preparado (`commit 8ec4261`) con `SCHEDULE_DISABLED_HOURS_UTC`, `scan.slot_metrics`, evaluación automática `maybe_evaluate_slot_monetization(state)` y el fix de ejecución por mínimo nocional; `python verify_before_deploy.py` vuelve a cerrar en **702/702**. A continuación se aplica en Railway `SCHEDULE_DISABLED_HOURS_UTC=23` y se elimina `SLOT_04H_REVIEW_REMINDER_DATE`; verificación live cerrada: el deploy `6d840105-4246-4c03-8658-18081492f5d7` arranca en `MODO REAL` mostrando `Schedule: [4, 8, 16] UTC` y `Schedule disabled hours: [23] UTC`, confirmando que el slot `23h` ya quedó apagado de forma reversible. Estado final: `04h` sigue `keep`, `23h` queda desactivado live por feature flag, el aviso manual viejo desaparece también de config y la revisión futura pasa a entrar por alerta operativa automática en vez de por recordatorio ad hoc.

**Última actualización:** 17 de abril de 2026 (Sesión 189 — slot monetization operational alert)
**Sesión 189 (17 abr 2026, Codex):** se cierra el loop que faltaba tras instrumentar `slot_metrics`: el sistema ya no solo mide `04h` y `23h`, sino que además los **evalúa automáticamente** y envía una alerta operativa accionable por Telegram pensada para abrir sesión Codex con salida de decisión. Se añade `maybe_evaluate_slot_monetization(state)` a `run_observability_alerts()`, con memoria en `alerts_state` (`slot_monetization_last_date`, `slot_monetization_last_signature`) para evitar ruido e idempotencia diaria. La nueva lógica lee `cycles_history.jsonl`, agrega `scan.slot_metrics` de los últimos ciclos exactos por slot, clasifica `04h` y `23h` (`validated`, `not_validated_yet`, `disable_candidate`, etc.) y manda un mensaje que ya incluye funnel reciente, reject reasons dominantes y siguiente acción sugerida para Codex; por ejemplo, mantener `04h` si sigue generando same-day con edge y marcar `23h` como candidato a apagado reversible si continúa en `0` edge / `0` buys. Importante: el sistema **todavía no aplica automáticamente** el cambio live; esta capa automatiza la revisión y la recomendación operativa, no el deploy ni la mutación de Railway. `verify_before_deploy.py` sube y vuelve a pasar en **702/702** con tests nuevos para el evaluador e idempotencia de la alerta.

**Última actualización:** 17 de abril de 2026 (Sesión 188 — 04h monetization patch + slot instrumentation)
**Sesión 188 (17 abr 2026, Codex):** la revisión del slot `04h` deja de cerrarse solo como auditoría y se convierte en decisión de sistema orientada a monetización. Sin tocar NOAA core, edge model, Kelly ni policy live, se parchea `bot.py` en tres frentes. 1) **Scheduler configurable por flag:** se añade `SCHEDULE_DISABLED_HOURS_UTC` para apagar slots concretos sin reescribir `SCHEDULE_HOURS_UTC`; la recomendación operativa queda lista para usar `23` como disable candidate porque el readout post-rollout lo deja en `0` edges, `0` buys y sesgo tardío. 2) **Conversión edge -> buy:** se corrige un cuello real de `04h` detectado en el ciclo `2026-04-17T04:00:45Z`: compras ya seleccionadas podían fallar por quedar apenas por debajo del mínimo de notional al redondear la orden (`invalid amount for a marketable BUY order ($0.9976), min size: $1`), así que antes de ejecutar el BUY el bot ahora normaliza `shares` al mínimo que cumple `ORDER_MIN_NOTIONAL`, dejando trazabilidad explícita en `decisions.log`. 3) **Instrumentación por slot:** `cycle_summary.json` y `cycles_history.jsonl` pasan a persistir `scan.slot_metrics` con `slot_hour_utc`, `same_day_candidates`, `same_day_edges`, `same_day_selected`, `same_day_buys`, `edges`, `selected`, `buys`, `buy_rate`, `same_day_buy_rate`, `reject_reasons`, `same_day_reject_reasons` y `execution_reject_reasons`, para que futuras revisiones no dependan de reconstrucción manual desde `skip_log`. Además, se retira del código el recordatorio one-shot `maybe_send_04h_slot_review_reminder()` y la env var `SLOT_04H_REVIEW_REMINDER_DATE`, ya cumplidos y obsoletos para la operativa actual. `verify_before_deploy.py` sube y vuelve a pasar en **697/697** con tests nuevos para schedule flag, normalización de mínimo notional y slot metrics. El readout `docs/04h-slot-observation-2026-04-17.md` queda actualizado con la decisión de sistema: `04h=keep`, `23h=feature flag`, `alert=remove`.

**Última actualización:** 17 de abril de 2026 (Sesión 187 — 04h slot post-rollout observation)
**Sesión 187 (17 abr 2026, Codex):** se ejecuta la revisión programada a cinco días del rollout `SCHEDULE_HOURS_UTC=4,8,16,23` usando un pull fresco de `data/runtime_import/` desde Railway y sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Se crea `docs/04h-slot-observation-2026-04-17.md` con un corte homogéneo `pre` vs `post` sobre ciclos exactos. Hallazgo central: `04h UTC` **sí abrió same-day real para Asia**; en la ventana post-rollout `Tokyo`, `Seoul` y `Shanghai` solo aparecen con `days_ahead=0` en ciclos exactos `04h`, nunca en `08h/16h/23h`. El mejor caso visible es el ciclo `2026-04-17T04:00:45Z`, que llega a `25` candidatos post-filtro, `2` edges y `2` seleccionadas, incluyendo `Shanghai NO 20°C` (`edge=25.4%`) y `Tokyo NO 18°C` (`edge=24.6%`), pero sin buy efectivo por restricciones operativas de tamaño mínimo/Kelly. Comparación resumida: `markets_evaluated/ciclo` queda casi plano (`16.5 -> 16.94`), `with_edge/ciclo` mejora levemente (`0.08 -> 0.17`) y `buys/ciclo` sigue en `0.00` en la muestra post; `city_window_skipped` pasa a `118.56/ciclo` por el city-window filter ya activo. Veredicto operativo: `04h` queda justificado como slot de discovery same-day real, mientras `23h` muestra señal débil (`0` edges, `0` buys, same-day mayormente `date_out_of_range_past`/`blocked_city`) y pasa a ser candidato razonable a salir si el objetivo principal del schedule sigue siendo throughput útil.

**Última actualización:** 17 de abril de 2026 (Sesión 186 — phase5 visibility alarm upgraded into operational action workflow)
**Sesión 186 (17 abr 2026, Codex):** se convierte la alerta de `Phase 5 Visibility` en un trigger operativo read-only sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Cambio central: la coincidencia `Shanghai + Chicago` deja de quedarse en aviso informativo y pasa a producir una lectura explícita hacia monetización. Se crea `tools/phase5_operational_action.py`, que consume `city_probe_visibility_tracker`, `shanghai_vs_chicago_comparator`, `shanghai_shadow_test` y `chicago_active_benchmark` para clasificar cada caso en `severity`, `action_state` y `next_operational_step`, persistiendo `data/phase5_operational_action.json` y `docs/phase5_operational_action_latest.md`. `tools/phase5_visibility_pipeline.py` integra esta nueva etapa y su resumen pasa a exponer severidad/estado/next-step operativos; `tools/phase5_visibility_telegram_alert.py` se amplía para enviar también esa lectura derivada en Telegram. Validación local: la pipeline completa cierra en `ok`; con los artefactos versionados actuales la salida queda en `no_progress` porque el snapshot local no contiene la coincidencia nueva reportada, pero una simulación controlada del caso real `probe=2026-04-17T01:56:54+00:00`, `Shanghai=2`, `Chicago=2`, `coincidencias=9`, `gap=evidence_asymmetry_between_shadow_and_active` clasifica correctamente `severity=watch`, `action_state=review`, `next_operational_step=increase_review_priority`, que era el objetivo de workflow. La sesión también limpia el doc de diseño intermedio para no dejar residuos y mantiene el handoff operativo ya actualizado. `verify_before_deploy.py` marca durante el cierre un único rojo transitorio de trazabilidad (`docs=186 / events=185`) que se resuelve al registrar esta sesión en `agent_events.jsonl`.

**Última actualización:** 17 de abril de 2026 (Sesión 185 — Seoul station-mismatch postmortem + v10.6.17)
**Sesión 185 (17 abr 2026, Sonnet):** postmortem del trade fallido de Seoul (NO edge=68%, pérdida -$0.97) e implementación de 3 mejoras de seguridad en `bot.py` v10.6.17. **Causa raíz:** `RESOLUTION_STATIONS["Seoul"]` apuntaba a Incheon airport (RKSI, lat=37.46, lon=126.44) — 40km al oeste de Seoul ciudad, en isla, 6-8°C más frío en primavera por brisas marinas. Polymarket resuelve vs ciudad. Forecast daba 13.1°C cuando Seoul real llegó a 19-21°C → edge=68% NO fantasma, matemáticamente coherente con datos erróneos. Agravante: bot vendió por SL y re-compró inmediatamente porque `sold_this_cycle` es token-level, no city-level. Shadow gate también falló: Seoul pasó con solo 2 edges mínimos (15%) en mercados 14-15°C de abril temprano donde Incheon era accidentalmente correcta. **Fix 1 (coords):** `RESOLUTION_STATIONS["Seoul"]` → KMA Seoul City (37.5665, 126.9780). **Fix 2 (SL cooldown):** tras `stop_loss`/`stop_loss_intra`, ciudad bloqueada 48h en `data/sl_city_cooldown.json`; funciones `_sl_cooldown_register` / `_sl_cooldown_check`; skip reason `sl_city_cooldown` en Loop B. **Fix 3 (shadow gate):** edge_hits 2→5, cycles 2→10, support 2→5; nuevo `SHADOW_CANARY_MIN_DAYS=14` (días mínimos en shadow antes de promoción, calculado desde `first_seen_at`). **Policy state Railway:** Seoul movida a `auto_blocked_cities` con razón `forecast_station_mismatch`; restaurado desde backup `.bak-20260412-1730` (el comando pipe previo había vaciado el archivo). **Incidente operativo:** un pipe de 3 Railway CLIs en cascada del contexto anterior corrompió `city_policy_state.json` (0 bytes) y mantuvo el mutex global 30 min. Solución: matar PID 9804, restaurar desde backup, escribir JSON correcto vía base64. **`verify_before_deploy.py`:** 691/691. Commit `ed00535`, desplegado en Railway.

**Última actualización:** 16 de abril de 2026 (Sesión 184 — city-intelligence alarm realigned to runtime canary reality)
**Sesión 184 (16 abr 2026, Codex):** se corrige la capa analítica de `city intelligence` para que deje de contar una historia vieja sobre Chicago y ciudades equivalentes, sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Hallazgo de partida: la alarma seguía leyendo `Chicago` como `needs_shadow_validation` / `policy_execution_gate` pese a que el runtime fresco ya la trata como `auto_canary`, con `allowlisted=true` y sin `shadow_only_override` nuevo tras el fix live de la sesión 182. Se ajustan `tools/city_validation_ledger.py` y `tools/city_promotion_gate.py` para que una ciudad con `runtime_policy_mode=auto_canary`, sin `useful_policy_gate_count` reciente y sin colisión runtime, pase a `bottleneck=canary_measurement`, `recommendation=observe_runtime_canary` y `gate_status=observe_runtime_canary` en vez de arrastrar `audit_runtime_drift` o `needs_shadow_validation`. Se regeneran los artefactos read-only (`city_validation_ledger`, `city_promotion_gate`, alerta dry-run y `docs/city_intelligence_pipeline_latest.md`) y la lectura queda reanclada a la realidad actual del bot: Chicago ya no es un caso de discovery pendiente, sino un canary activo que debe demostrar valor medible. Como guardrail adicional, `verify_before_deploy.py` se endurece para cargar `parse_temperature_question`, `_extract_threshold_canonical`, `re` y `normalize_city` dentro del harness shadow/persistencia, eliminando el falso rojo que hacía fallar `directional_history` / `road_to_real` por dependencias ausentes del test y no por la lógica real. Cierre técnico: `python verify_before_deploy.py` vuelve a pasar en **691/691**.
**Última actualización:** 16 de abril de 2026 (Sesión 182 — residual canary shadow-only gate fix + live verification)
**Sesión 182 (16 abr 2026, Codex):** se diagnostica y corrige el bug residual que seguía generando `shadow_only_override` en ciudades `canary` pese a que Railway ya arrancaba en `MODO REAL`. Evidencia previa cerrada: en `data/runtime_import/skip_log.jsonl` todas las entradas históricas con `skip_reason="shadow_only_override"` eran `city_mode="canary"` y `allowlisted=false`; no aparecía ningún caso `shadow` con ese motivo. Causa raíz precisa: el scan loop sí resolvía bien `city_mode="canary"` vía `get_effective_city_mode()`, pero `_is_shadow_only()` conservaba un fallback legacy que solo miraba `ACTIVE_TRADING_CITIES` + `CANARY_TRADING_CITIES` explícitas y **no** las canary persistidas en `city_policy_state.json` (`auto_canary_cities` / `auto_canary_from_active`). Con `ACTIVE_TRADING_CITIES=NONE`, una ciudad podía ser canary efectiva y aun así caer en `shadow_override_flag=True`. Se aplica el fix mínimo en `bot.py`: el fallback de `_is_shadow_only()` ahora también cuenta canary persistidas antes de declarar pausa global; `verify_before_deploy.py` sube a **691/691** con tests nuevos para `auto_canary` y `auto_canary_from_active`. Deploy live confirmado en Railway (`commit 2ac2bb1`, deployment `af3c82b8-7f4b-4a55-bd3f-14ecb40f8edc`, arranque `2026-04-16 07:36:23 UTC`). Verificación read-only post-deploy cerrada: el siguiente ciclo (`2026-04-16T08:00`, `cycle_summary.timestamp_utc=2026-04-16T08:01:17.784600+00:00`) ya no muestra ningún `shadow_only_override` nuevo (`count=0` desde el deploy) y las ciudades `canary` pasan con `allowlisted=true`; los bloqueos observados pasan a ser legítimos (`price_out_of_range`, `condition_filtered`, `date_out_of_range_past`, `existing_position` en Seoul) mientras el único `fuera_allowlist` nuevo corresponde a `Hong Kong` en `shadow`. Veredicto final: **bug residual corregido**.
**Última actualización:** 16 de abril de 2026 (Sesión 181 — dashboard shadow-only residual fix + verificación post-deploy)
**Sesión 181 (16 abr 2026, Codex):** se cierra el diagnóstico simple post-deploy del fix `_is_shadow_only()` sin tocar trading core, NOAA core, scheduler, Kelly, sigma ni filtros. Hallazgo 1: el servicio live quedó desplegado sano en Railway (`deployment b140bb87-0d40-4d26-8705-20907e9f47b0`, logs en `Modo: REAL` y `cycle_summary.mode=\"REAL\"`), así que el toggle explícito `SHADOW_ONLY_MODE=false` sí está llegando al proceso y el problema no era un env var perdido. Hallazgo 2: quedaba un residuo de presentación en `bot.py`: `build_daily_summary_payload()` seguía marcando `shadow_only` con `len(ACTIVE_TRADING_CITIES) == 0` en vez de reutilizar `_is_shadow_only()`. Se aplica un fix mínimo para unificar esa capa con la fuente de verdad canónica y `verify_before_deploy.py` vuelve a cerrar en `685/685`. Hallazgo 3: la sesión confirma que el problema no era solo UI/dashboard; sigue existiendo gating real post-deploy en runtime, con al menos una entrada `skip_reason=\"shadow_only_override\"` posterior al deploy (`Seoul`, ciclo `2026-04-16T07:07`, `city_mode=\"canary\"`, `edge_pct=68.47`). Veredicto limpio: **`dashboard + gating real`**. El estado compartido ya no debe leerse como “shadow-only deliberado”, pero queda abierto un bug residual en el scan loop / allowlist path que todavía puede degradar ciudades `canary` a `shadow_only_override` pese a arrancar en `MODO REAL`.
**Última actualización:** 16 de abril de 2026 (Sesión 180 — shadow-only toggle desacoplado de ACTIVE_TRADING_CITIES)
**Sesión 180 (16 abr 2026, Codex):** se valida y prepara para deploy el fix de correctness en `bot.py` sobre `_is_shadow_only()` sin tocar trading core, NOAA core, scheduler, Kelly, sigma ni filtros. Causa raíz cerrada: `ACTIVE_TRADING_CITIES=NONE` se estaba usando como proxy de pausa global y eso bloqueaba también ciudades ya promovidas a `auto_canary`. El fix desacopla ambos conceptos: `_is_shadow_only()` ahora prioriza `SHADOW_ONLY_MODE` como toggle explícito, y solo usa fallback legacy cuando no hay activas ni canary explícitas en env vars. `verify_before_deploy.py` vuelve a cerrar en `685/685`. Se deja el sistema listo para que Railway use `SHADOW_ONLY_MODE=false`, preservando `ACTIVE_TRADING_CITIES=NONE` como “ninguna ciudad ganó active aún” y permitiendo que las ciudades en `auto_canary_cities` ejecuten trades canary reales. Handoff operativo asociado: `docs/next-session-handoff-2026-04-16-active-none-canary-gate.md`. Verificación post-deploy pendiente: confirmar que el dashboard salga de lectura shadow-only deliberada, muestre modo REAL y que `Chicago` empiece a convertir `policy_execution_gate` en ejecución canary real.
**Última actualización:** 15 de abril de 2026 (Sesión 179 — throughput live funnel audit + policy gate reprioritized)
**Sesión 179 (15 abr 2026, Codex):** auditoría operativa del funnel live del bot priorizando evidencia fresca de `data/runtime_import/` y sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Se cruza `skip_log.jsonl`, `shadow_city_tracking.json`, `signals.json`, `policy_env_snapshot.json`, `city_validation_ledger.json`, `city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md`. Hallazgo clave: el runtime reciente ya no justifica leer `trader_discovery` como cuello dominante del throughput útil; en los dos últimos ciclos (`2026-04-15T04:00` y `2026-04-15T07:14`) hubo `4` near-misses con `edge_pct >= 15`, y `3/4` murieron por gating operativo (`shadow_only_override` / `fuera_allowlist`) mientras solo `1/4` cayó por `kelly_too_low`. Se implementa una mejora read-only en `tools/city_validation_ledger.py` y `tools/city_promotion_gate.py` para incorporar evidencia reciente de `skip_log` al ledger/gate y distinguir `policy_execution_gate` de `trader_discovery`; tras regenerar artefactos, `city_intelligence_pipeline_latest.md` pasa a mostrar `dominant_bottleneck=policy_execution_gate`, con `Shanghai` y `Chicago` como casos prioritarios por edge útil reciente bloqueado por policy. `verify_before_deploy.py` cierra en `685/685`. Durante el cierre entra una nueva alerta `Phase 5 Visibility` (`2026-04-15T13:54:33+00:00`) con coincidencia acumulada `Shanghai + Chicago = 6`, gap `evidence_asymmetry_between_shadow_and_active` y siguiente paso sugerido `use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence`; se decide no mezclar ese bloque en esta sesión y dejarlo como handoff limpio para la siguiente. Seguimiento posterior: el probe `2026-04-17T01:56:54+00:00` vuelve a detectar `Shanghai=2 mercados` y `Chicago=2 mercados`, eleva las coincidencias acumuladas a `9` y mantiene sin cambios el gap dominante (`evidence_asymmetry_between_shadow_and_active`) y la recomendación operativa (`use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence`). Artefacto nuevo: `docs/next-session-handoff-2026-04-15-policy-gate-throughput.md`.
**Última actualización:** 15 de abril de 2026 (Sesión 178 — London city-intelligence audit + policy priority fix)
**Sesión 178 (15 abr 2026, Codex):** sesión read-only de auditoría operativa/analítica sobre London dentro de `city intelligence`, sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. Se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1` y se elimina el `manifest_drift` local del snapshot. Hallazgo clave: London no estaba “casi lista para monetizar”, sino mal contada por la capa analítica y además en colisión de policy (`cross=blocked`, `runtime=auto_canary`). Se corrige `tools/city_validation_ledger.py` para respetar la prioridad canónica de modos de ciudad (`blocked` gana sobre `auto_canary`) y para cargar un `structural_block_guardrail` explícito para London (`weather_underground_openmeteo_mismatch`); con eso London pasa a `policy_mode=blocked`, `bottleneck=source_fidelity` y deja de degradarse a `trader_discovery`. `tools/city_promotion_gate.py` se ajusta para reflejar mejor casos de bloqueo estructural en revisión. Auditoría fresca: `settlement_fidelity_probe.py --city London` encuentra 10 mercados con Open-Meteo pero 0/10 con NOAA observado y `WU` sigue `pending_not_automated`; `shadow_city_tracking` muestra `edge_hits=2`, `cycles_seen=41`, `best_edge_pct=28.4`; `blocked-signals` mantiene London en 33.3% (1/3) para exact/range. Veredicto: **mantener London en blocked** y tratar su situación como `blocked with runtime drift`, no como candidata de monetización. Artefactos nuevos: `docs/london-city-intelligence-warning-review-2026-04-15.md` y `docs/london-settlement-source-audit-2026-04-15.md`. `verify_before_deploy.py` ejecutado OK antes de cierre.

**Última actualización:** 14 de abril de 2026 (Sesión 177 — Austin canary onboarding v10.6.17)
**Sesión 177 (14 abr 2026, Opus+Sonnet):** sesión de análisis de throughput del scan loop + implementación de palanca recomendada. **Análisis Opus (diseño):** diagnóstico de `price_out_of_range` (51% de skips): filtro `[MIN_PRICE=0.20, MAX_PRICE=0.80]` correctamente calibrado — trades históricos con `avg_entry_price<0.25` acumulan −$23.50 en 31 registros (WR=18%); zona ganadora está en 0.50–0.80 (+$4.39 en 18 trades). Veredicto: no tocar filtro de precio. **Palanca única recomendada:** Austin →canary por consensus trader (n_consensus=2, trader_wr=65.5%, mkt_price=0.48 dentro del filtro). **Implementación Sonnet (opción A):** NOAA Austin verificado — KAUS/USW00013904: 182 registros TMAX oct2025–mar2026 plausibles. ISD 72254013904 (USAF=722540) confirmado históricamente en isd-history.csv (activo hasta 2025-08-27; bot usa daily path prioritario). Tres cambios en `bot.py`: (1) Austin en `RESOLUTION_ICAO` con `noaa_station_id="72254013904"` + `noaa_daily_station_id="USW00013904"`; (2) `"Austin": "America/Chicago"` en `CITY_TIMEZONES`; (3) Austin en `OBSERVED_AUDIT_CITIES`. `city_policy_state.json`: Austin agregado a `auto_canary_cities` con timestamp 2026-04-14. 5 tests nuevos en `verify_before_deploy.py` → **685/685**. Criterios de evaluación: ≥3 trades cerrados o 14 días; GO si WR≥55% o PnL≥+$0.50; NO-GO si PnL≤−$2.00 o 3 losses consecutivos; Inconcluso si <3 trades en 14 días. Sin tocar: filtros, thresholds, Kelly, sigma, exits, ACTIVE_TRADING_CITIES (sigue NONE).

**Última actualización:** 14 de abril de 2026 (Sesión 176 — condition_reopen_monitor v10.6.16)
**Sesión 176 (14 abr 2026, Sonnet):** monitor automático del canary condition_filtered exact/range. `tools/condition_reopen_monitor.py`: standalone read-only, carga `data/trade_lifecycle.json`, filtra trades `condition ∈ {exact, range}` con `opened_at >= 2026-04-14` y `status=closed`, calcula WR via `close_context.pnl_cash > 0`, desglose por ciudad, veredicto (OK / ALERT / CLOSE / PROMOTE / EXTEND / KILL_SWITCH / INSUFFICIENT). `maybe_run_condition_monitor(state)` en `bot.py` v10.6.16 integrado en `run_observability_alerts()`: dispara desde día 7 en fechas de checkpoint (2026-04-21, 2026-04-28) y diariamente si kill-switch activo (WR<45% n≥20). Anti-spam via `state["last_condition_checkpoint"]`. Mensaje Telegram incluye métricas + bloque `<code>` con instrucción Sonnet/Codex lista para pegar. 9 tests nuevos en `verify_before_deploy.py` → 680/680. Sin cambios en Railway, trading core, env vars.

**Última actualización:** 14 de abril de 2026 (Sesión 175 — condition_filtered canary reopen v10.6.15)
**Sesión 175 (14 abr 2026, Opus+Sonnet):** decisión operativa de Opus + implementación Sonnet. Opus analizó 59 resoluciones reales de quality traders en señales `exact/range` (WR=76.3%, threshold cumplido ≥55% n≥50). **Decisión: reabrir `condition_filtered` con triple gate (Opción B modificada)**. Implementado en `bot.py` v10.6.15: (1) 4 env vars nuevas (`QUALITY_TRADER_CONDITIONS`, `QUALITY_TRADER_CITIES_WHITELIST`, `MIN_EDGE_EXACT_RANGE_BUFFER_PP=5.0`, `EXACT_RANGE_SIZE_SCALE=0.50`); (2) lógica de tres vías en el filtro: condition en ALLOWED_CONDITIONS → normal, condition en QUALITY_TRADER_CONDITIONS + trader quality + ciudad whitelist → pipeline con flag `exact_range_canary`, otherwise → skip; (3) edge mínimo diferenciado (`MIN_EDGE + 5pp`) para exact/range canary; (4) sizing 25% del normal (`CANARY_POSITION_SCALE × EXACT_RANGE_SIZE_SCALE`). **Whitelist 9 ciudades**: Seattle, Tokyo, Hong Kong, Seoul, Toronto, Chengdu, Shenzhen, Shanghai, Milan. **London excluida** (WR 33% n=3). Checkpoints: día 7 (2026-04-21) y día 14 (2026-04-28). Kill-switch: WR bot <45% n≥20 → revertir. `verify_before_deploy.py` → 671/671. Decisión archivada en engram + `docs/handoffs/condition-filtered-canary-implement-2026-04-14.md`.

**Última actualización:** 14 de abril de 2026 (Sesión 174 — blocked signals WR baseline n=59 + Opus handoff condition_filtered)
**Sesión 174 (14 abr 2026, Sonnet):** análisis empírico de señales `exact/range` bloqueadas por `condition_filtered`. Tool `tools/blocked_signals_settlement_tracker.py` corrida localmente con data fresca de Polymarket API: 59 resolutions, **WR=76.3%** (exact=72.5% n=51, range=100% n=8). Threshold de decisión cumplido ampliamente (WR≥55%, n≥50 robusto). Ciudades con n≥3: Toronto/Seoul 75%, Seattle/Tokyo/Hong Kong 100%, London 33.3% (outlier). Consenso 66.7% vs Solo 78.0%. Veredicto: **REOPEN CANDIDATE**. Implementación diferida a sesión Opus: `ALLOWED_CONDITIONS` ya es env var en Railway (default `at_or_above,at_or_below`), añadir `exact,range` es un cambio de una línea de Railway, pero Opus decide guardrails (¿global vs quality-trader-only? ¿edge mínimo diferenciado? ¿qué ciudades primero?). Handoff: `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md`. JSONL local actualizado a 59 records en `data/runtime_import_derived/` (gitignored). Baseline doc actualizado: `docs/blocked-signals-wr-baseline-2026-04-13.md`. Sin tocar `bot.py`, trading core, Railway ni env vars.

**Última actualización:** 13 de abril de 2026 (Sesión 173 — canary→active automation v10.6.14)
**Sesión 173 (13 abr 2026, Sonnet):** implementación del handoff de sesión 172 (Opus). Se añaden tres módulos a `bot.py` elevando versión a `v10.6.14`: (1) `notify_active_candidates(state)` — alerta Telegram persistente cada 24h cuando una ciudad canary cumple criterios v1 (n≥5, WR≥60%, PnL≥+$1.00, days≥7, integridad OK, anti-flapping), revocación automática si criterios dejan de cumplirse, silenciamiento cuando la ciudad aparece en `ACTIVE_TRADING_CITIES` en runtime; (2) `maybe_run_active_degradation(state)` — degrada Active→Canary automáticamente (WR≤45% o PnL≤-$1.50, con n≥5 y anti-flapping 14 días) usando overlay `auto_canary_from_active` en `city_policy_state.json`; `get_effective_city_mode()` extendido para leer ese overlay antes de `ACTIVE_TRADING_CITIES`; (3) `maybe_alert_v2_trigger(state)` — alerta one-shot cuando `RECALIBRATION_PHASE2_CLOSED=true`, al menos 1 ciudad en Active y `signals.json` fresco (<48h). Helper `_detect_atlanta_inconsistency()` añadido. `verify_before_deploy.py` pasa a 663/663 (+20 tests nuevos). Nota operativa: volumen bajo del scan loop sigue siendo backlog paralelo no resuelto aquí.

**Última actualización:** 13 de abril de 2026 (Sesión 172 — diseño canary→active automation + handoff Opus)
**Sesión 172 (13 abr 2026, Opus):** sesión de diseño estratégico. No se toca `bot.py`, trading core, thresholds ni Railway. Se decide arquitectura de automatización canary→active con opción B (notificación Telegram persistente, Pablo aplica manualmente) tras descartar auto-promoción full. Fundamento: bankroll $25 no absorbe error de auto-promoción, modelo en recalibración, asimetría de riesgo (degradar=auto-seguro, promover=decisión humana). Umbrales v1 congelados con justificación explícita: `canary_trades>=5`, `WR>=60%`, `PnL>=+$1.00`, `days_since_promotion>=7`, `WR_degradation<=45%`. Scope v1 = Bloques 1+2+4 (historial propio canary + integridad lifecycle + anti-flapping). Scope v2 = Bloques 3+5 (corroboración externa signals.json + gate global post-recalibración), deferidos con trigger alarm automático que avisa a Pablo cuando precondiciones v2 se cumplan. Entregable único: `docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md` con spec completo de tres módulos (`notify_active_candidates`, `maybe_run_active_degradation`, `maybe_alert_v2_trigger`), Telegram templates, anti-spam (rate limit 24h + revocación), detección de acción del usuario vía env var runtime, test checklist. Implementación diferida a sesión Sonnet limpia. Nota operativa registrada: volumen bajo de trades sigue siendo prioridad paralela (scan loop filtra demasiado); este módulo ayuda indirectamente al sizing pero no resuelve throughput de fondo.

**Última actualización:** 13 de abril de 2026 (Sesión 171 — fix encoding ° en signals.json)
**Sesión 171 (13 abr 2026, Sonnet):** bug fix de codificación descubierto en sesión 170. `trader_analyzer.py api_get()` llamaba `json.loads(resp.read())` sin encoding explícito; en Windows con CP437 los bytes UTF-8 `\xC2\xB0` del símbolo `°` se decodificaban como CP437 produciendo `┬░` (U+252C U+2591) en `signals.json`. Fix: `json.loads(resp.read().decode("utf-8"))` una línea en `trader_analyzer.py:103`. `verify_before_deploy.py` → 643/643.

**Última actualización:** 13 de abril de 2026 (Sesión 170 — blocked signals settlement tracker)
**Sesión 170 (13 abr 2026, Sonnet):** se crea `tools/blocked_signals_settlement_tracker.py` (Handoff B). Tool read-only que mide WR implícita de señales `exact/range` de quality traders bloqueadas por `condition_filtered`. Primera corrida: 18/18 = 100% WR (n=18, insufficient para decisión — necesita >= 30). Bug encoding documentado: `signals.json` almacena `°` como `U+252C U+2591`; el tool normaliza antes de matching. Outputs: `data/runtime_import_derived/blocked_signals_resolutions.jsonl` + `docs/blocked-signals-wr-baseline-2026-04-13.md`. No se toca bot.py ni trading core.

**Última actualización:** 13 de abril de 2026 (Sesión 169 cont. — crosscheck automatizado + corrección ACTIVE_TRADING_CITIES)
**Sesión 169 continuación (13 abr 2026, Sonnet):** dos cambios adicionales al cierre de la sesión. (1) Se añade `maybe_run_daily_crosscheck(state)` a `bot.py` (v10.6.12): corre el cross-check señales traders vs edge bot una vez por día en el primer ciclo, appenda a `SIGNALS_CROSSCHECK_FILE` (`/app/data/signals_crosscheck.jsonl`), manda Telegram diario con resumen MATCH/BOT_ONLY/TRADER_ONLY, y cuando acumula `SIGNALS_CROSSCHECK_NOTIFY_THRESHOLD=7` corridas manda aviso one-shot para iniciar análisis. (2) Usuario aplica `ACTIVE_TRADING_CITIES=NONE` en Railway — elimina el default hardcoded "Chicago,Atlanta,Dallas,Buenos Aires" que trataba a esas ciudades como active sin env var explícito. Ahora ninguna ciudad entra en active mode sin declaración explícita; todo el trading real pasa por `auto_canary_cities`. (3) Feature nueva documentada en backlog: graduación canary→active con criterios automáticos y reminder persistente hasta que el usuario actúe — requiere sesión dedicada Opus.

**Última actualización:** 13 de abril de 2026 (Sesión 169 — cross-check edge vs traders + diagnóstico auto-promoción)
**Sesión 169 (13 abr 2026, Sonnet):** dos handoffs de Opus (A y C) ejecutados en una sesión. Sin tocar `bot.py`, trading core, thresholds, Railway ni policy live.
- **Handoff A — Experimento 1 (Cross-check edge vs traders):** se crea `tools/signals_vs_edge_crosscheck.py`, tool standalone read-only que compara `shadow_city_tracking.json` (edge bot) vs `signals.json` (señales de quality traders). Primera corrida sobre snapshot `2026-04-13T04:00:58 UTC`: 104 señales de 8 quality traders, 14 ciudades MATCH (bot y traders solapados), 2 BOT_ONLY (Beijing, Chicago — bot tiene edge sin cobertura trader), 21 TRADER_ONLY (bot sin edge pero traders tienen señal). Austin confirmada en TRADER_ONLY (consensus x2, at_or_above, edge_hits=0 — gap canónico). Seoul confirmada en MATCH (canary activa, edge_hits=2). Hallazgo clave: 81% de señales de quality traders caen en `exact/range` (condiciones bloqueadas por el bot). De los 21 TRADER_ONLY, 8 tienen señales con condiciones operables (`at_or_above`/`at_or_below`) — Austin y Toronto con consenso. Output: `data/runtime_import_derived/signals_crosscheck.jsonl` (primer registro) y readout `docs/signals-crosscheck-baseline-2026-04-13.md`. Tool se debe correr manualmente ~1 vez por día hasta acumular 7-10 corridas para serie temporal.
- **Handoff C — Diagnóstico trigger auto-promoción shadow→canary:** análisis read-only de por qué Dallas, Lucknow, Sao Paulo e Istanbul no se auto-promueven pese a cumplir los thresholds. Dos bugs distintos identificados con citas de código: (1) Dallas — `ACTIVE_TRADING_CITIES` env var es `null` en Railway, el código usa default "Chicago,Atlanta,Dallas,Buenos Aires", lo que hace que Dallas sea tratada como `city_mode="active"` (nunca llega al branch `promotable_shadow`) Y que el gate de promoción en `sync_city_policy_state:6154` (`city not in ACTIVE_TRADING_CITIES`) falle; (2) Lucknow, Sao Paulo, Istanbul — no están en `OBSERVED_AUDIT_CITIES` (hardcoded `bot.py:9832`), tienen 0 trades (no aparecen en `city_accuracy`), y nunca fueron degradadas de active/canary (no están en `auto_shadow_cities`), por lo que son **invisibles a `tracked_cities`** y `sync_city_policy_state` nunca las evalúa. Gap estructural: `shadow_city_tracking` acumula datos de cualquier ciudad del scan loop, pero el pipeline de promoción solo ve ciudades formalmente registradas. Fixes propuestos (no aplicados, decisión Opus): A1=setear `ACTIVE_TRADING_CITIES` explícitamente en Railway (env var, no código), B1=añadir Lucknow/Istanbul/Sao Paulo a `OBSERVED_AUDIT_CITIES` de a una. Readout: `docs/auto-promotion-trigger-diagnosis-2026-04-13.md`.

**Última actualización:** 12 de abril de 2026 (Sesión 167 — higiene de worktree: gitignore, untrack y stage de artefactos)
**Sesión 167 (12 abr 2026, Sonnet):** sesión de higiene del worktree. Sin tocar `bot.py`, trading core, thresholds ni Railway. Diagnóstico de causa raíz: el `.gitignore` no cubría los tres flujos principales de artefactos (snapshots de Railway, outputs de tools, docs de sesión), lo que causó ~167 archivos sin trackear acumulados desde sesiones anteriores. Se crean reglas `.gitignore` para `data/runtime_import/`, `data/runtime_import_derived/`, outputs generados en `data/*.json`, readouts en `docs/*_latest.md` y `docs/*-latest.md`, handoffs de sesión `docs/next-session-handoff-*.md`, prompts de modelo `docs/claude-opus-prompt-*.md`/`docs/codex-prompt-*.md`, y artefactos de research en raíz `RESEARCH_*.md`. Se untrackearon con `git rm --cached` cinco archivos generados que estaban incorrectamente en el índice: `data/runtime_import/city_policy_state.json`, `data/runtime_policy_effective_view.json`, `data/system_alignment_check_operational.json`, `docs/runtime_policy_effective_view_latest.md` y `docs/system_alignment_check_operational_latest.md`. Se stagearon todos los scripts nuevos de `tools/` (32), `seed_data/phase5/*.json` (3), `RTK.md` y ~60 docs de análisis/diseño con valor permanente. El preflight final es `0 archivos sin trackear`. Entregable: `docs/worktree-hygiene-audit-2026-04-12.md`.

**Última actualización:** 12 de abril de 2026 (Sesión 166 — policy live London/Dallas reconciliada + Atlanta lifecycle aclarada)
**Sesión 166 (12 abr 2026, Codex):** se aplica un cambio live mínimo y acotado sobre `city_policy_state.json` en el volumen de Railway, sin tocar `bot.py`, thresholds, env vars ni promover manualmente ciudades. La sesión parte del preflight operacional canónico, edita solo los dos overlays pedidos, refresca `data/runtime_import/`, regenera `runtime_policy_effective_view` y deja además documentada la inconsistencia de `Atlanta` en `trade_lifecycle`.
- **Cambio live exacto en policy persistida:** usando `tools/railway_safe.ps1`, backup previo del archivo en `/app/data/` y edición remota acotada por líneas, se elimina `London` de `auto_canary_cities` y `Dallas` de `auto_shadow_cities` en `city_policy_state.json`. No se toca ningún otro campo de la policy ni se modifica `transition_history`.
- **Estado runtime ya reanclado:** tras `tools/railway_runtime_snapshot_pull.ps1`, `data/runtime_import/city_policy_state.json` vuelve a mostrar solo `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai` y `Tokyo` en `auto_canary_cities`, mientras `auto_shadow_cities` queda vacío. `python tools/runtime_policy_effective_view.py` deja la foto nueva en `blocked=3`, `canary=6`, `shadow=18`.
- **Preflight operacional vuelve a barrera sana:** `python tools/system_alignment_check.py --decision-mode operational` cierra en `ok=6`, `warning=2`, `error=0`. Desaparece el `blocking_operational_collision` de `Dallas`; queda solo ruido de `documented_drift` más el warning documental ya conocido de `markets_evaluated`.
- **Atlanta queda leída correctamente para humanos:** se crea `docs/atlanta-lifecycle-inconsistency-2026-04-12.md` y se alinea `docs/canary-to-active-readiness-2026-04-12.md`. La lectura correcta del trade `Atlanta 76°F Apr7 YES` es win mal etiquetada: la `timeline` registra `RESOLVED_WIN` con `pnl_cash=+0.63` y `post_exit_analysis` confirma `0.9995`, aunque `close_context` terminara en `LOSS_TOTAL` por `micro_position_unsellable`.

**Última actualización:** 12 de abril de 2026 (Sesión 165 — diagnóstico Dallas canary + readiness canary→active)
**Sesión 165 (12 abr 2026, Codex):** se cierra un bloque read-only de diagnóstico sobre `Dallas` y las ciudades `canary`, sin tocar `bot.py`, thresholds, listas de ciudades, Railway ni policy live. La sesión parte del preflight operacional canónico, confirma que el snapshot runtime está fresco y separa dos preguntas: por qué `Dallas` no reaparece en `auto_canary_cities` pese a cumplir hoy la regla shadow -> canary, y qué evidencia canary real existe para las seis ciudades pedidas antes de cualquier conversación manual sobre `Active`.
- **Dallas no está frenada por `CITY_STATS_CUTOFF`:** se crea `docs/dallas-canary-block-diagnosis-2026-04-12.md`. La lectura de `bot.py` confirma que `CITY_STATS_CUTOFF` solo recorta `get_city_accuracy()` y `get_city_policy_metrics()`; no entra en la condición `promotable_shadow` de `build_dashboard_city_decisions()`, que se alimenta de `shadow_city_tracking`. Con el snapshot actual, Dallas sigue en `edge_hits=8`, `cycles_seen=5`, `best_edge_pct=45.8`, así que pasa todos los thresholds incluso si el cutoff dejara `trades=0`. El bloqueo actual apunta a un estado persistido inconsistente (`auto_shadow_cities`) y no a falta real de evidencia reciente.
- **Matiz fuerte de estado runtime:** `data/runtime_policy_effective_view.json` deja hoy a `Dallas` como `env_declared_mode=shadow`, `runtime_policy_mode=auto_shadow`, `effective_mode=shadow`, así que tampoco queda frenada por seguir en `ACTIVE_TRADING_CITIES`. La explicación más fuerte ya no es “esperar más edges post-cutoff”, sino que el overlay `auto_shadow` no refleja una re-promoción posterior aunque la evidencia shadow vigente sí volvería a justificarla.
- **Readiness factual de las canary pedidas:** se crea `docs/canary-to-active-readiness-2026-04-12.md` usando `trade_lifecycle.json`, `cycles_history.jsonl` y `city_policy_state.json`. La tabla deja un cuadro sobrio: `Munich` y `New York City` siguen sin trades canary post-promoción; `Seoul`, `Shanghai` y `Tokyo` tienen una primera señal positiva limpia pero solo `n=1`; `Atlanta` queda contaminada por una inconsistencia interna en `trade_lifecycle` (`close_context=LOSS_TOTAL` pero `timeline` registra antes `RESOLVED_WIN +$0.63` y `post_exit_analysis` ve el mercado a `0.9995`).
- **Discrepancia de snapshot documentada:** aunque el pedido hablaba de seis canary actuales (`Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`), el snapshot runtime ya muestra además `London` en `auto_canary_cities` con `promoted_at=2026-04-12T15:03:51Z`. La auditoría respeta las seis ciudades solicitadas, pero deja esa diferencia fechada para no arrastrar una lectura stale del estado live.

**Última actualización:** 12 de abril de 2026 (Sesión 164 — cierre de blocked cities y shortlist shadow para canary review)
**Sesión 164 (12 abr 2026, Codex):** se cierra un bloque read-only de policy/observabilidad sobre ciudades `blocked` y `shadow`, sin tocar `bot.py`, thresholds, allowlists, bankroll ni Railway desde Codex. La sesión une dos auditorías estructurales de `BLOCKED_CITIES`, valida el estado live post-cambio manual del usuario con snapshot fresco, y deja el primer filtro honesto de ciudades `shadow` que sí merecen debatir una revisión del umbral `canary`.
- **Blocked cities reducidas a criterio canónico puro:** se crean `docs/ankara-paris-unblock-review-2026-04-12.md` y `docs/remaining-blocked-cities-review-2026-04-12.md`. El veredicto combinado deja como estructuralmente justificadas solo `London`, `Toronto` y `Singapore`; `Ankara`, `Paris`, `Madrid`, `Wellington` y `Tel Aviv` quedan recomendadas para `shadow` por no mostrar mismatch forecast/settlement documentado, ausencia de `noaa_station_id` o mecanismo de resolución roto/no validado.
- **Estado live reanclado tras el cambio manual del usuario:** después de que el usuario aplicara en Railway `BLOCKED_CITIES=London,Toronto,Singapore`, se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1`, se regenera `runtime_policy_effective_view` y el preflight operacional vuelve a `error=0` (`ok=6`, `warning=2`). La foto operativa nueva queda en `blocked=3`, `canary=6`, `shadow=19`; el único choque residual es `London` como colisión operacional conocida y ya documentada.
- **Bloque B acotado sin sobreprometer:** se crea `docs/shadow-canary-threshold-review-2026-04-12.md` para separar ciudades `shadow` con base real para revisar umbral `canary` de las que siguen verdes. Con la evidencia actual, solo `Dallas` y `Chicago` ameritan abrir esa conversación; `Buenos Aires` queda en observación y `Denver`, `Los Angeles`, `Houston`, `San Francisco` y `Mexico City` siguen demasiado recientes o débiles. Las cinco ciudades recién movidas de `blocked` a `shadow` quedan explícitamente fuera de cualquier decisión inmediata y en observación pura.

**Última actualización:** 12 de abril de 2026 (Sesión 163 — auditoría del universo Polymarket y temporalidad de precio)
**Sesión 163 (12 abr 2026, Codex):** se auditan dos hipótesis nuevas de throughput usando solo evidencia read-only de `data/runtime_import/`: si el techo actual viene del universo real de Polymarket o del embudo del bot, y si los mercados que hoy caen en `price_out_of_range` llegan luego a ventanas útiles.
- **Universo observado muy estable y muy regular:** se añade `tools/analyze_market_universe.py` y se documenta `docs/polymarket-universe-price-temporal-audit-2026-04-12.md`. Sobre `29` ciclos normales del snapshot manifestado (`2026-04-05T20:09:48+00:00` a `2026-04-12T09:45:48+00:00`), el bot sigue viendo `324-330` mercados por ciclo con mediana `330`, y `30` pares `city + date` por ciclo sin deriva material. Ademas, `273` de `277` combinaciones `city + date` observadas tienen exactamente `11` mercados. La lectura corta es que no aparece crecimiento visible del universo bruto dentro de esta muestra; el ceiling inmediato parece vivir mas en el funnel que en discovery.
- **`price_out_of_range` casi nunca se convierte en throughput util:** `1091` mercados unicos tocaron ese bucket; solo `25` (`2.3%`) llegaron luego a una fase pre-edge, mientras `810` (`74.2%`) solo salieron del bucket de precio para morir en filtros temporales y `256` (`23.5%`) nunca salieron de `price_out_of_range`. La señal extrema previa se mantiene: `1058/1091` (`97.0%`) entran por primera vez con `mkt_prob < 20` y ese mismo `97.0%` nunca llega siquiera a ver `mkt_prob >= 20` en observaciones posteriores.
- **Implicacion operativa nueva:** la propuesta de Opus queda respondida en negativo parcial. No hay evidencia en esta muestra de que el bot este limitado por no ver suficientes mercados, ni de que el bucket de precio esconda una reserva amplia de trades recuperables con un timing un poco mejor. Si se quiere seguir empujando throughput sin tocar core, el siguiente modulo mas honesto pasa a ser observacion post-rollout del slot `04h` y, en paralelo o despues, micro-auditoria por ciudad/slot en las pocas plazas donde el bucket de precio muestra alguna movilidad real (`Seoul` primero).
- **Matiz importante de fechas:** esta auditoria usa el snapshot `runtime_import` tirado a `2026-04-12T10:15:51+00:00`, o sea antes de poder juzgar con muestra limpia el efecto del rollout live `SCHEDULE_HOURS_UTC=4,8,16,23` activado mas tarde el mismo `2026-04-12`. Sirve como baseline fuerte para la comparacion posterior, no como veredicto del slot `04h`.

**Última actualización:** 12 de abril de 2026 (Sesión 162 — slot 04h activado + recordatorio Telegram programado)
**Sesión 162 (12 abr 2026, Codex):** se activa en Railway la siguiente fase mínima de throughput temporal sin tocar lógica core de trading: `SCHEDULE_HOURS_UTC` pasa a `4,8,16,23` para abrir una ventana `same-day` real a las canary asiáticas, y además se deja automatizado un recordatorio one-shot por Telegram para revisar el impacto del cambio cinco días después.
- **Cambio live mínimo y reversible:** el ajuste de scheduler no vive en código ni en un servicio nuevo, sino en Railway. `SCHEDULE_HOURS_UTC=4,8,16,23` queda aplicado en `polymarket-bot`, manteniendo intactos edge, thresholds, bankroll, política de ciudades, `get_min_days_for_city()` y el city-window prefilter recién implementado. El objetivo no es rediseñar el sistema temporal, sino probar la palanca de menor riesgo que sí puede abrir throughput asiático real.
- **Automatización lean del seguimiento:** en `bot.py` se añade `SLOT_04H_REVIEW_REMINDER_DATE`, más un helper `maybe_send_04h_slot_review_reminder()` integrado en `run_observability_alerts()`. Cuando llegue la fecha objetivo, el bot enviará por Telegram un prompt corto y accionable para abrir una sesión Codex de auditoría del slot `04h`, sin depender de que el usuario recuerde revisar docs o calendarizarlo a mano.
- **Fecha ya configurada en producción:** Railway queda con `SLOT_04H_REVIEW_REMINDER_DATE=2026-04-17`, así que el recordatorio one-shot queda programado para el viernes tras cinco días de observación. El mensaje pide explícitamente revisar `data/runtime_import/`, crear `docs/04h-slot-observation-2026-04-17.md`, comparar pre vs post y decidir si `23h UTC` sigue aportando valor.
- **Validación de cierre:** `python verify_before_deploy.py` sigue en `643/643` tras añadir la automatización. Railway acepta ambas env vars (`SCHEDULE_HOURS_UTC=4,8,16,23` y `SLOT_04H_REVIEW_REMINDER_DATE=2026-04-17`) y el servicio entra en nuevo deploy (`BUILDING`) por el cambio de variables.

**Última actualización:** 12 de abril de 2026 (Sesión 161 — city-window prefilter implementado + cierre de trazabilidad)
**Sesión 161 (12 abr 2026, Codex):** se implementa en `bot.py` el diseño de city-window routing acordado tras la revisión con Opus, sin tocar edge, thresholds, bankroll, política de ciudades ni scheduler, y se cierra además el drift de trazabilidad que volvía a dejar `agent_events.jsonl` por detrás de docs.
- **Prefilter same-day ya vivo en el scan loop:** se añade `compute_city_windows()` reutilizando `get_min_days_for_city()` como source of truth, de forma que el prefilter respeta también cualquier override manual de `MIN_DAYS_AHEAD` y no duplica lógica de timezone. El early-exit se inserta después de `blocked/mode/shadow` y antes del safety net de fecha, exactamente como pedía el diseño v2.
- **Observabilidad estructurada preservada:** los skips estructurales por ventana dejan de inflar `skip_log.jsonl`, pero ya no se pierden para futuras auditorías; `cycle_data["scan"]` ahora persiste `city_window_skipped` y `city_window_cities` en `cycle_summary.json` y `cycles_history.jsonl`. La lista de ciudades queda ordenada para que la diff y la lectura histórica sean estables.
- **Semántica operativa sin drift:** las ciudades fuera de `CITY_TIMEZONES` siguen siendo permisivas en el prefilter porque `compute_city_windows()` solo precalcula para ciudades con timezone declarada, y `get_min_days_for_city()` se mantiene intacto como safety net real del paso 2. El decision log añade una línea humana `VENTANA: ...` sin reintroducir ruido per-market en `skip_log`.
- **Verificación técnica cerrada:** `python -m py_compile bot.py` pasa, y `python verify_before_deploy.py` vuelve a cerrar en `643/643`. El único falso rojo intermedio no era del código nuevo sino de la secuencia de cierre: `agent_events.jsonl` seguía en la sesión `159`/`160` mientras `CONTEXTO.md` y `HISTORIAL_SESIONES.md` ya iban por delante. Se registra la sesión faltante y el preflight vuelve a verde.
- **Siguiente estado real del módulo:** el diseño ya no está solo documentado; queda implementado y trazado. El siguiente paso lógico ya no es arquitectura sino validación observacional del primer ciclo con city-window activo para medir cuánto baja el ruido estructural de `skip_log` y cómo se refleja el nuevo contador en `cycle_summary`/`cycles_history`.

**Última actualización:** 12 de abril de 2026 (Sesión 160 — auditoría timezone_filter + canary funnel + bug fix CITY_TIMEZONES)
**Sesión 160 (12 abr 2026, Sonnet):** auditoría adversarial del funnel pre-edge completando los dos frentes no auditados (timezone_filter y lado derecho canary), bug fix de timezone, y preparación del módulo de diseño para Opus.
- **timezone_filter cerrado como intocable:** 100% de los 605 skips en last12 son ciudades asiáticas/Wellington a 16-21h local en ciclos 08-09h UTC. El filtro opera exactamente como fue diseñado para evitar el Bug #5 (Chongqing UTC fallback). No hay nada recuperable aquí.
- **Canary throughput críticamente bajo:** 967 skips en last12 para las 6 ciudades canary (Seoul, Shanghai, Munich, NYC, Atlanta, Tokyo), solo 2 llegaron a `below_min_edge` (ambos Shanghai). Cuello dominante: `price_out_of_range` con mediana `mkt_prob=0.55%` — universo de mercados extremadamente baratos, no margen fino.
- **condition_filtered confirmado como política deliberada:** todos los 94 casos canary bloqueados por `allowed_conditions=['at_or_above','at_or_below']`. Fue auditado previamente con evidencia de pérdidas en otras condiciones. No reabrir sin datos nuevos.
- **Bug timezone confirmado y corregido:** Denver, Mexico City, Los Angeles, Houston, San Francisco no estaban en `CITY_TIMEZONES` y caían al fallback UTC, causando que `get_min_days_for_city()` los tratara como 16-20h local cuando tenían 10-13h real. 33 market instances falsamente bloqueadas en last12. Fix: 5 entradas añadidas a `CITY_TIMEZONES` con zonas IANA correctas. `verify_before_deploy.py` pasa sin errores. Commit: `fix: add missing American cities to CITY_TIMEZONES`.
- **Scheduler actual documentado:** 3 slots dominantes (08h, 16h, 23h UTC, 7 ciclos cada uno). 08h = asiáticas a 16-17h local (todo timezone_filter); 16h = americanas en mañana (buen timing); 23h = americanas a 18-19h (tarde). Esta foto es el punto de partida para el diseño Opus.
- **Frente pendiente antes de Opus:** Telegram Correctness — handoff en `docs/next-session-handoff-2026-04-12-telegram-correctness.md`, sin readout de cierre. Asignar a Codex.
- **Prompt Opus preparado:** diseño de ciclos por ventana de ciudad (asignar qué ciudades procesa cada slot existente según su hora local, sin crear nuevos ciclos en Railway).

**Última actualización:** 12 de abril de 2026 (Sesión 158 — auditoría horaria de same-day timing)
**Sesión 158 (12 abr 2026, Codex):** se audita el subbucket same-day dentro de `date_out_of_range_past` con granularidad horaria usando solo evidencia read-only de `data/runtime_import/`, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight limpio respetado otra vez:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` se vuelven a correr a `2026-04-12T10:56:05+00:00` y ambos siguen en `ok=7`, `warning=1`, `error=0`, así que la auditoría parte de la misma base canónica alineada.
- **Readout nuevo del módulo:** se crea `docs/same-day-timing-audit-2026-04-12.md` sobre la misma ventana de `29` ciclos y `9896` skips, enfocándose solo en `date_out_of_range_past` y usando la regla horaria ya viva en `bot.py`: `min_days_global=1` desde `12:00 UTC` y cutoff práctico `hora_local >= 14` o `día local siguiente`.
- **Hallazgo central que cambia la lectura:** aunque el same-day sigue pesando `3980` de `4475` skips de fecha (`88.9%`), casi nunca llega dentro de una ventana aún operable; `3925` de `3980` filas (`98.6%`) ya caen `too late in practice`, mientras solo `55` (`1.4%`) quedan como `late but plausibly recoverable`.
- **La concentración no es un pico fino sino un patrón estructural post-mediodía:** el same-day aparece en casi todos los slots reales posteriores a `12:00 UTC`, con mayor masa en `16-17 UTC` (`1415`) y `22-23 UTC` (`1355`). En `last12` la señal sigue viva y concentrada en los dos slots recientes reales (`16 UTC` y `23 UTC`), así que el problema no parece una rareza puntual de un solo borde horario.
- **La parte recuperable es pequeña y geográficamente acotada:** el subbucket plausibly recoverable vive casi solo en `Los Angeles` (`22`), `Denver` (`22`) y `Mexico City` (`11`); no aparece una bolsa grande distribuida por Asia o Europa.
- **Veredicto corto y siguiente lectura:** la hipótesis `tiempo` como gran palanca general de throughput queda debilitada. Si se reabre timing, debería ser como micro-oportunidad acotada por ciudad/slot; esta auditoría ya no permite seguir leyendo `same-day` como sinónimo de `recuperable`.

**Última actualización:** 12 de abril de 2026 (Sesión 159 — shim local para RTK.md)
**Sesión 159 (12 abr 2026, Codex):** se corrige una pequeña fricción de tooling/documentación creando `RTK.md` dentro del repo como shim neutral para la referencia `@RTK.md`, sin tocar `bot.py`, configuración global de Codex, configuración de Claude ni instalación alguna del binario `rtk`.
- **Diagnóstico corto:** `rtk` sí estaba instalado y operativo en Codex (`rtk 0.34.3`) y también existía `~/.codex/RTK.md`, así que el problema no era de instalación sino de resolución de referencia desde el repo.
- **Cambio mínimo y conservador:** se añade `RTK.md` local con instrucciones breves y neutrales para que `@RTK.md` resuelva igual en Codex y Claude, sin forzar rutas específicas como `~/.codex/RTK.md` que pudieran romper compatibilidad cruzada.
- **Lectura de riesgo:** el cambio reduce dependencia de cómo cada cliente expande archivos globales y es el parche menos invasivo; no sustituye la instalación global real de `rtk`, solo da un destino estable a la referencia documental del repo.

**Última actualización:** 12 de abril de 2026 (Sesión 157 — auditoría de throughput prefilter antes de edge)
**Sesión 157 (12 abr 2026, Codex):** se audita el cuello real de throughput antes de edge usando solo evidencia read-only de `data/runtime_import/`, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight limpio obligatorio:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` se vuelven a ejecutar a `2026-04-12T10:36:27+00:00` y ambos cierran en `ok=7`, `warning=1`, `error=0`, así que la auditoría parte de una base canónica alineada.
- **Readout nuevo del módulo:** se crea `docs/prefilter-throughput-audit-2026-04-12.md` sobre `29` ciclos y `9896` skips reales de `data/runtime_import/skip_log.jsonl`, con foco exclusivo en prefiltros (`fecha`, `precio`, `composición por ciudad/modo`) y sin mezclar el problema con `MIN_EDGE`, sigma ni monetización.
- **Cuello dominante real:** `date_out_of_range_past` sigue siendo el bucket principal (`4475`, `45.2%`) y además parece mayoritariamente “late within normal flow”, no universo muerto: `3980` de `4475` (`88.9%`) caen el mismo día del mercado (`days_late=0`), mientras solo `495` (`11.1%`) llegan con un día de retraso.
- **Lectura de precio afinada:** `price_out_of_range` sigue siendo el segundo gran filtro (`2249`, `22.7%`), pero no aparece como una nube repartida cerca del bound; está concentrado casi por completo en extremos bajos: `2194` (`97.6%`) tienen `mkt_prob < 20`, con mediana `0.3` y `83.0%` del bucket en `0-5`.
- **Miami y Seattle ya cuentan como visibilidad real, pero no mueven el funnel:** ambas aparecen ya como `shadow` efectivo en la capa canónica y en `last12` suman `231` filas (`5.8%` del funnel reciente), presentes en `10` de `12` ciclos. Añaden universo visible real, pero casi todo sigue muriendo por `date_out_of_range_past` y `price_out_of_range`, así que todavía no cambian materialmente el throughput.
- **Veredicto corto y siguiente palanca:** el prefiltro que domina de verdad el throughput hoy es `date_out_of_range_past`; la palanca más prometedora para la siguiente sesión es `tiempo` (`88.9%` del bucket same-day), pero la recuperabilidad real no está confirmada hasta auditar ese módulo con granularidad horaria.
**Última actualización:** 12 de abril de 2026 (Sesión 156 — drift de Dallas cerrado en Railway)
**Sesión 156 (12 abr 2026, Codex):** se cierra el drift real de `Dallas` sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`, actuando sobre la declaración manual live que seguía contradiciendo la policy runtime efectiva.
- **Cambio live mínimo y correcto:** se elimina `ACTIVE_TRADING_CITIES` del servicio `polymarket-bot` en Railway, porque hoy solo sembraba el claim declarativo `Dallas=active` mientras `city_policy_state.json` la sigue resolviendo como `auto_shadow`.
- **Snapshot y effective view revalidados después del cambio:** `tools/railway_runtime_snapshot_pull.ps1` vuelve a refrescar `data/runtime_import/`, `policy_env_snapshot.json` ya muestra `ACTIVE_TRADING_CITIES=""`, y `data/runtime_policy_effective_view.json` deja `Dallas` alineada como `env=shadow`, `runtime=auto_shadow`, `effective=shadow`, sin `blocking_operational_collision`.
- **Preflight operacional vuelve a verde:** tras regenerar la effective view, `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a cerrar en `ok=7`, `warning=1`, `error=0`; el conteo queda en `shadow=16`, `blocked=8`, `canary=6`, con `blocking_operational_collision_count=0`.
- **Lectura final del cierre:** el drift de Dallas ya no vive ni en tooling ni en Railway. Lo que queda visible en la capa canónica son solo `documented_drift=4`, no blockers duros.

**Última actualización:** 12 de abril de 2026 (Sesión 155 — snapshot de policy env automatizado)
**Sesión 155 (12 abr 2026, Codex):** se corrige la deuda menor de `tools/runtime_policy_effective_view.py` para que deje de depender de pasar `BLOCKED_CITIES` a mano y pueda leer automáticamente las listas manuales desde un snapshot read-only de Railway, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.
- **Fix puntual en el transporte read-only:** `tools/railway_runtime_snapshot_pull.ps1` ahora guarda `data/runtime_import/policy_env_snapshot.json` con solo `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES` y `BLOCKED_CITIES`, evitando traer secretos innecesarios. `tools/runtime_policy_effective_view.py` pasa a leer ese snapshot por defecto antes de caer al entorno local del proceso.
- **La sincronización de `BLOCKED_CITIES` ya funciona sola:** tras refrescar snapshot y regenerar la effective view sin flags manuales, `miami` y `seattle` siguen saliendo como `env=shadow`, `effective=shadow`, con conteo total `shadow=16`, `blocked=8`, `canary=6`.
- **Hallazgo sano que reaparece al sincronizar también `ACTIVE_TRADING_CITIES`:** al traer las listas manuales reales de Railway, vuelve a hacerse visible `ACTIVE_TRADING_CITIES=Dallas` frente a `city_policy_state.auto_shadow_cities`, así que `python tools/system_alignment_check.py --decision-mode operational` vuelve a caer en `error=1` por `blocking_operational_collision_count=1`. El collision real es `Dallas` (`env active` vs `runtime auto_shadow`); no lo introduce el fix, solo lo deja visible otra vez.
- **Estado de cierre honesto:** el fix técnico del snapshot/env queda correcto y verificable; el siguiente paso, si se quiere volver a `operational error=0`, ya no es tocar este script sino decidir qué hacer con el drift real de `Dallas`.

**Última actualización:** 12 de abril de 2026 (Sesión 154 — shadow efectivo tras cambio manual en Railway)
**Sesión 154 (12 abr 2026, Codex):** se valida el cambio manual de Railway donde `BLOCKED_CITIES` deja de incluir `Miami` y `Seattle`, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.
- **Snapshot runtime live refrescado:** el pull canónico `tools/railway_runtime_snapshot_pull.ps1` se ejecuta con éxito y deja `data/runtime_import/runtime_import_manifest.json` con `pulled_at=2026-04-12T09:57:08.6678143+00:00`, así que la sesión ya trabaja sobre una foto live nueva y no sobre el snapshot anterior del `2026-04-11`.
- **Effective view ya muestra el cambio esperado:** `data/runtime_policy_effective_view.json` y `docs/runtime_policy_effective_view_latest.md` se regeneran y ahora dejan `Miami` y `Seattle` con `env_declared_mode=shadow`, `effective_mode=shadow`; el conteo total pasa a `shadow=16`, `blocked=8`, `canary=6`.
- **Matiz importante de fuente de verdad:** para reflejar el cambio live real hubo que regenerar `tools/runtime_policy_effective_view.py` con `--blocked-cities "London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara"`, porque el script conserva un fallback local stale que todavía incluía `Miami` y `Seattle`. No se tocó `bot.py`; solo se alineó la generación read-only con el valor manual ya aplicado en Railway.
- **Preflight vuelve a cerrar en verde:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a terminar en `ok=7`, `warning=1`, `error=0`, con `blocking_operational_collision_count=0`, así que el cambio no rompe alignment.

**Última actualización:** 12 de abril de 2026 (Sesión 153 — revisión read-only de blocked dudosas)
**Sesión 153 (12 abr 2026, Codex):** se ejecuta la revisión read-only pedida para las cuatro ciudades `dudoso y candidato a revisión futura` dentro de `BLOCKED_CITIES` (`Ankara`, `Miami`, `Paris`, `Seattle`), sin tocar `bot.py`, `city_policy_state.json`, runtime live, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight respetado como gate real:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a cerrar en `ok=7`, `warning=1`, `error=0`, así que la revisión se hace sobre una base alineada y sin reabrir módulos ya cerrados.
- **Mercados visibles + NOAA sí existen en las cuatro:** la revisión confirma que `RESOLUTION_ICAO` ya contiene `noaa_station_id` para `Ankara`, `Miami`, `Paris` y `Seattle`, y que las cuatro reaparecen en artefactos runtime recientes (`cycles_history`, `skip_log`, `performance` o `trade_lifecycle`), así que no son ciudades muertas ni inobservables por falta de estación.
- **Veredicto por ciudad sin cambio live:** `docs/blocked-cities-review-2026-04-12.md` deja `Miami` y `Seattle` como `candidata a shadow`, porque hoy ya no aparece una razón estructural fuerte para mantener hard block y ambas siguen teniendo visibilidad de mercado útil; `Ankara` y `Paris` quedan en `insuficiente evidencia`, porque aunque tienen NOAA y algo de visibilidad, el ledger sigue leyéndolas como casos en construcción con cuello en `market_visibility`.
- **Cambio manual ya explicitado pero no ejecutado:** el doc deja escrito el ajuste exacto pendiente si Pablo aprueba mover solo las candidatas actuales a `shadow`: pasar `BLOCKED_CITIES` de `London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara` a `London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`, sin tocar Railway en esta sesión.

**Última actualización:** 12 de abril de 2026 (Sesión 152 — primera lectura operativa real del funnel)
**Sesión 152 (12 abr 2026, Codex):** se abre y cierra el siguiente módulo lógico tras `alignment`: la primera lectura operativa real del funnel usando `skip_log.jsonl` de producción, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight mantenido como gate real:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a cerrar en `ok=7`, `warning=1`, `error=0`, así que el readout se hace sobre una base alineada.
- **Bugfix mínimo en el analyzer, no en trading core:** `tools/analyze_skip_log.py` pasa a preferir `data/runtime_import/skip_log.jsonl` en vez de asumir `data/skip_log.jsonl`, reflejando la capa read-only canonica del repo. También se alinea `docs/skip-log-analyzer.md`.
- **Lectura del funnel por fin anclada a datos reales:** `python tools/analyze_skip_log.py --last-n-cycles 30` lee `25` ciclos y `8576` skips reales. El cuello dominante queda explicitado: `date_out_of_range_past=46.2%`, `price_out_of_range=21.3%`, `blocked_city=18.8%`, `timezone_filter=9.2%`, `condition_filtered=3.9%`; `below_min_edge` queda en solo `0.1%` con un único near-miss relevante (`Shanghai`, `edge_pct=2.71`).
- **Conclusión operacional cerrable:** el funnel no se está estrechando por `MIN_EDGE` ni por Kelly; se estrecha casi por completo antes de llegar a edge (`Grupo B = 99.4%`). `docs/skip-log-readout-2026-04-12.md` deja la primera lectura compacta y confirma, con más nitidez, la historia ya insinuada por `Step 5`: hoy no hay base para tocar policy o thresholds a partir de esta muestra.

**Última actualización:** 12 de abril de 2026 (Sesión 151 — cierre formal de alignment y blocked/config-drift)
**Sesión 151 (12 abr 2026, Codex):** se ejecuta una sesión corta de sellado para dejar explícitamente cerrados `System Alignment Lean Roadmap` y `Blocked Cities / Config Drift Cleanup`, sin tocar `bot.py`, `city_policy_state.json`, runtime live, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight sigue dando la señal correcta de cierre:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a cerrar en `ok=7`, `warning=1`, `error=0`, con `blocking_operational_collision_count=0`. Se adopta esta señal como criterio real de cierre del módulo de alignment.
- **El “Paso 1” de limpieza ya estaba hecho:** se confirma que `tools/reference_trader_city_market_cross.py` ya no usa `legacy_bot_lists` y que los fósiles `normal_pull_check/final_check` ya no existen en `data/runtime_import_derived/`. Lo pendiente no era técnico sino de narrativa/cierre.
- **Cierre formal y regla anti-reapertura:** `docs/manual-config-drift-audit-2026-04-12.md` pasa a marcar explícitamente que sus dos deudas técnicas principales quedaron resueltas y que el módulo no debe reabrirse por hallazgos puntuales de ciudad ni por deuda documental menor. A partir de aquí, hallazgos nuevos entran en backlog salvo que vuelva a romperse el preflight o aparezca una contradicción real de fuente de verdad.

**Última actualización:** 12 de abril de 2026 (Sesión 150 — racional canónico de blocked cities)
**Sesión 150 (12 abr 2026, Codex):** se convierte `docs/blocked-cities-rationale-latest.md` desde ficha defensiva genérica a justificación canónica y corta por ciudad, manteniendo el trabajo 100% read-only y sin tocar `bot.py`, `city_policy_state.json`, runtime live, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight respetado antes de documentar:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a correrse primero y ambos cierran en `ok=7`, `warning=1`, `error=0`, así que la auditoría parte de una base operacional válida.
- **Inventario de `BLOCKED_CITIES` ya clasificado por ciudad:** el artefacto nuevo mantiene las 10 ciudades actuales como `blocked` en la effective view, pero deja una taxonomía honesta: `London` queda como único caso `alineado y bien defendido`; `Madrid`, `Singapore`, `Tel Aviv`, `Toronto` y `Wellington` quedan `alineado pero subdocumentado`; `Ankara`, `Miami`, `Paris` y `Seattle` quedan `dudoso y candidato a revisión futura`.
- **Lectura canónica más precisa sin tocar policy:** la conclusión ya no es “todas las bloqueadas están igualmente bien justificadas”, sino “la lista sigue siendo operativamente coherente hoy, pero solo una ciudad tiene memo estructural explícito vigente y cuatro merecen revisión separada si queremos que `blocked` siga significando descarte por fuente/resolución”.

**Última actualización:** 12 de abril de 2026 (Sesión 149 — cierre manual-config-drift y cleanup de artefactos derivados)
**Sesión 149 (12 abr 2026, Codex):** se cierra la auditoría `Manual Config Drift` y su cleanup inmediato sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`, y se deja el siguiente bloque lógico ya empaquetado como handoff limpio.
- **Preflight canónico revalidado:** tras regenerar `runtime_policy_effective_view` y rerunear `python tools/system_alignment_check.py` + `python tools/system_alignment_check.py --decision-mode operational`, ambos checks vuelven a quedar en `ok=7`, `warning=1`, `error=0`. El único warning vivo pasa a ser el esperado de colisiones explícitas en la effective view; desaparece el warning residual de `metrics_funnel_naming`.
- **Drift manual clasificado con evidencia:** `docs/manual-config-drift-audit-2026-04-12.md` deja inventario corto de overrides/manual lists vivas. Quedan `DEFAULT_ACTIVE_CITIES=""` y `DEFAULT_CANARY_CITIES=""` como alineadas; `ACTIVE_TRADING_CITIES` queda fósil como fuente de verdad; `BLOCKED_CITIES` se sostiene como override manual de seguridad estructural; el fallback `legacy_bot_lists` en `reference_trader_city_market_cross.py` se clasifica como deuda dudosa a migrar.
- **Capa derivada reanclada a semántica canónica:** `tools/reference_trader_city_market_cross.py` deja de caer a `legacy_bot_lists` y usa `runtime_policy_effective_view` + default canónico `shadow`. Se regeneran `docs/reference_trader_city_market_cross_latest.md`, `docs/city_validation_ledger_latest.md` y `docs/city_promotion_gate_latest.md`; desaparecen modos `untracked` y deja de reabrirse drift fósil tipo `Chicago active`.
- **Artefactos fósiles retirados y trazabilidad nueva:** se crea `docs/blocked-cities-rationale-latest.md` como ficha corta de `BLOCKED_CITIES`, y se eliminan snapshots stale `normal_pull_check/final_check` de `data/runtime_import_derived` para que no compitan con la capa canónica vigente. También queda listo `docs/next-session-handoff-2026-04-12-blocked-cities-evidence.md` con prompt exacto del siguiente bloque.

**Última actualización:** 12 de abril de 2026 (Sesión 148 — Telegram Correctness reanclado a runtime_import)
**Sesión 148 (12 abr 2026, Codex):** se cierra `Telegram Correctness` sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`, reanclando la capa Telegram a la foto canónica actual en vez de seguir describiendo una fase `runtime_inputs_missing` ya superada.
- **Preflight respetado:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` se corren antes de tocar Telegram y ambos siguen sin errores (`error=0`), así que la sesión no trabaja sobre una base operacional rota.
- **Runtime import pasa a ser la base por defecto del ledger:** `tools/city_validation_ledger.py` deja de buscar `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` en `data/` local y pasa a leer por defecto desde `data/runtime_import/`, alineando `city-intelligence` con el transporte read-only ya manifestado.
- **Telegram deja de repetir trabajo cerrado:** `tools/city_intelligence_daily_summary.py` deja de depender de un pipeline stale para concluir `runtime_inputs_missing` y pasa a combinar `city_intelligence_pipeline`, `runtime_policy_effective_view` y `system_alignment_check_operational` para contar la historia vigente: runtime read-only manifestado, preflight operacional verde, `blocked=10`, `canary=6`, `shadow=14`, `active=0`, sin `blocking_operational_collision`.
- **Framing humano actualizado también en alertas/prompts:** `tools/city_intelligence_telegram_alert.py` y `tools/city_promotion_gate.py` eliminan framing stale de monetización prematura y reencuadran el mensaje hacia lectura operativa, bloqueo actual y siguiente paso real sin mandar repetir transporte runtime ni abrir policy antes de tiempo.
- **Artefactos regenerados:** `python tools/city_intelligence_pipeline.py --telegram-dry-run` deja `overall_status=ok`, `runtime_inputs_status=available` y review queue sin blockers `now`; `python tools/city_intelligence_daily_summary.py --dry-run` regenera `docs/city_intelligence_daily_summary_latest.md` con la narrativa correcta; `docs/city_intelligence_alert_latest.md` queda actualizado al framing nuevo.

**Última actualización:** 12 de abril de 2026 (Sesión 147 — Dashboard Correctness cerrado y siguiente bloque explicitado)
**Sesión 147 (12 abr 2026, Codex):** se cierra `Dashboard Correctness` sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`, y se deja trazabilidad explícita del siguiente bloque para no depender de recordatorios manuales.
- **Preflight desbloqueado y cierre factual:** se regenera `data/runtime_policy_effective_view.json` + `docs/runtime_policy_effective_view_latest.md`, con lo que `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a quedar sin errores (`error=0`). El bloqueo previo de frescura operativa queda resuelto sin tocar runtime live ni policy.
- **Dashboard reanclado a la capa canónica visible:** `templates/dashboard.html` deja de presentar `markets_evaluated` como si fueran mercados brutos y pasa a leerlo explícitamente como alias legacy de `candidates_after_prefilters`. El bloque superior reencuadra `Road to Real` como checklist heredado y no como verdad operativa principal, y reaparece una capa de `progreso reciente` basada en `cycle_history` para mostrar ciclos visibles, ciclos con buys, cierres visibles y tabla corta de actividad runtime.
- **Surface humana sincronizada:** `docs/guia-lectura-dashboard.md` y `docs/dashboard-telegram-human-layer-readout-2026-04-11.md` se actualizan para alinear naming del funnel y framing humano con la lectura canónica actual. Se crea `docs/dashboard-correctness-readout-2026-04-12.md` como cierre corto de la fase.
- **Validación y siguiente paso:** `python verify_before_deploy.py` vuelve a cerrar en `643/643`. El siguiente bloque recomendado pasa a ser `Telegram Correctness`, y queda explícito que debe abrirse como **sesión limpia nueva** (`1 sesión = 1 bloque`). `Sonnet` solo sería útil como auditoría/copy compacta antes o después; `Opus` no hace falta mientras no aparezca conflicto real de fuente de verdad o arquitectura.

**Última actualización:** 12 de abril de 2026 (Sesión 146 — roadmap reforzado con utilidad humana y anti-drift)
**Sesión 146 (12 abr 2026, Codex):** se refuerza el módulo `human-reading-alignment` para que no persiga solo correctness técnica, sino también utilidad humana, visibilidad de progreso y cierre anti-drift entre superficies.
- **Roadmap reforzado:** `docs/human-reading-alignment-roadmap-2026-04-12.md` ahora deja explícito que `Dashboard` y `Telegram` deben responder no solo "qué estado tenemos", sino también "dónde estamos", "qué falta para el siguiente escalón", "si vamos por buen camino hacia monetización" y "qué cambió desde la lectura anterior". Se añaden principios de `utilidad humana`, `horizontes corto/medio/largo` y una `regla de cierre anti-drift` para que ningún cambio deje desactualizado el resto del circuito humano.
- **Handoff de Dashboard mejorado:** `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` se actualiza para exigir que `Dashboard Correctness` no solo reanude la verdad factual, sino que también deje el dashboard más útil para lectura diaria: punto actual, bloqueo principal, siguiente escalón y señal de si el sistema sigue avanzando o no.
- **Criterio nuevo de cierre:** queda escrito que una sesión no se considera realmente bien cerrada si resuelve wiring pero sigue dejando fricción humana alta o deja otras superficies desalineadas sin declararlo como pendiente explícita.

**Última actualización:** 12 de abril de 2026 (Sesión 145 — roadmap del módulo human-reading-alignment)
**Sesión 145 (12 abr 2026, Codex):** se deja definido el módulo completo para corregir la capa humana por fases limpias, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Roadmap del módulo:** se crea `docs/human-reading-alignment-roadmap-2026-04-12.md`, que fija el bloque `human-reading-alignment` con fases explícitas (`Preflight`, `Dashboard Audit`, `Dashboard Correctness`, `Telegram Correctness`, `Shared Copy Layer`, `Final Verification`), regla `1 sesión = 1 bloque`, criterios de corte y cuándo sí/no pedir revisión de Opus.
- **Siguiente sesión ya aterrizada:** se crea `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` para arrancar una sesión limpia dedicada solo a `Dashboard Correctness`, con lecturas mínimas, preflight obligatorio, hallazgos de partida ya confirmados, Definition of Done y regla explícita de parar si arreglar Dashboard exige tocar arquitectura o `bot.py`.
- **Reparto de modelos explicitado:** el roadmap deja escrito cómo compaginar `Codex`, `Sonnet` y `Opus`: Codex para ejecutar y cerrar, Sonnet para auditoría/copy compacta, Opus solo para conflictos de fuente de verdad o arquitectura. La intención es evitar volver a gastar contexto mezclando bloques heterogéneos en una sola sesión.

**Última actualización:** 11 de abril de 2026 (Sesión 144 — auditoría de alineación Dashboard/Telegram)
**Sesión 144 (11 abr 2026, Codex):** se ejecuta la auditoría read-only de la capa humana pedida en el handoff anterior, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Preflight sigue verde:** `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` vuelven a cerrar en `ok=7`, `warning=1`, `error=0`; no reaparece `blocking_operational_collision`.
- **Dashboard no cuenta hoy la historia canónica:** el snapshot local del builder sigue leyendo una topología legacy/local (`4` activas: `Atlanta`, `Buenos Aires`, `Chicago`, `Dallas`; `0` ciclos; `0` shadow; `0` cierres) que contradice la capa canónica actual (`active_effective_count=0`, `canary=6`, `shadow=14`, ventana runtime ya observada con `20` ciclos, `4` buys y `4` cierres). Además, `templates/dashboard.html` sigue llamando "Mercados escaneados" al alias legacy `markets_evaluated`, rompiendo el contrato de `metrics-funnel-naming.md`.
- **Telegram queda una fase atrás:** `docs/city_intelligence_daily_summary_latest.md` sigue anclado a `runtime_inputs_missing` y a "validar el transporte read-only del runtime", pero la capa canónica usada hoy ya parte de `runtime_import` manifestado, `runtime_ledger` disponible y preflight verde. `docs/city_intelligence_alert_latest.md` no dispara una alerta falsa, pero tampoco aporta una lectura útil del estado actual.
- **Conclusión y siguiente paso:** se crean `docs/dashboard-telegram-human-layer-audit-2026-04-11.md` y `docs/dashboard-telegram-human-layer-readout-2026-04-11.md`. El veredicto es que la capa humana **no** está alineada hoy con la capa canónica; el siguiente paso recomendado es `correctness de lectura` primero y solo después una sesión corta de copy/UI para limpiar wording stale como `Road to Real` y la lectura ambigua del funnel.

**Última actualización:** 11 de abril de 2026 (Sesión 143 — mapa mental y siguiente frente Dashboard/Telegram)
**Sesión 143 (11 abr 2026, Codex):** se deja un documento corto para aterrizar el sistema en lenguaje humano y fijar el siguiente frente lógico tras cerrar alignment base: auditar Dashboard y Telegram como capa de lectura humana, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Mapa mental explícito:** se crea `docs/system-mental-model-2026-04-11.md`, que resume el sistema en tres capas (`polymarket-bot` como ejecución, artefactos runtime como estado observable y `city-intelligence`/checks/docs como inteligencia read-only), explicita qué parte ya está cerrada, qué sigue abierta y qué significa realmente "subir un escalón" sin confundirlo con monetización prematura.
- **Siguiente sesión propuesta:** se crea `docs/next-session-handoff-2026-04-11-dashboard-telegram-audit.md` para abrir una auditoría read-only del Dashboard y Telegram contra la capa canónica actual (`runtime_policy_effective_view`, `system_alignment_check`, naming del funnel y readouts recientes). La hipótesis operativa nueva es que la arquitectura base ya está suficientemente alineada como para que el siguiente drift relevante, si existe, viva más en la capa humana de lectura/alerta que en los contratos core ya cerrados.

**Última actualización:** 11 de abril de 2026 (Sesión 142 — follow-up de throughput sin muestra nueva)
**Sesión 142 (11 abr 2026, Codex):** se intenta extender otra vez la observación read-only de `Step 5` con snapshot runtime fresco y preflight `observe/operational` limpio, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Base limpia sigue en pie:** se refresca `data/runtime_import/` por la vía canónica read-only, dejando `runtime_import_manifest.json` con `pulled_at=2026-04-11T11:01:40.7730763+00:00`. Ambos checks vuelven a quedar verdes: `python tools/system_alignment_check.py => ok=7, warning=1, error=0`; `python tools/system_alignment_check.py --decision-mode operational => ok=7, warning=1, error=0`, sin `blocking_operational_collision`.
- **No hay muestra incremental real:** aunque el manifest está fresco, `cycles_history.jsonl` sigue cerrando en `2026-04-11T08:00:38.111156+00:00` (`cycle_number=64`) y `shadow_city_tracking.updated_at` queda en `2026-04-11T08:00:38.036104+00:00`. La ventana de los últimos `20` ciclos es exactamente la misma ya usada en `docs/step5-throughput-observation-extended-2026-04-11.md`, así que no existe todavía una segunda tanda honesta de `20` ciclos nuevos para medir.
- **Conclusión operativa honesta:** no reaparece ningún blocker operacional ni ningún bug nuevo de accounting/counters que fuerce una sesión de correctness, pero tampoco hay evidencia nueva para afirmar que `auto_canary` se sostenga más o menos que en la lectura previa. El siguiente paso sigue siendo observación read-only cuando exista una ventana material de ciclos frescos. Artefactos nuevos: `docs/step5-throughput-observation-followup-2026-04-11.md` y `docs/throughput-observation-readout-followup-2026-04-11.md`.

**Última actualización:** 11 de abril de 2026 (Sesión 141 — throughput extendido sobre base limpia)
**Sesión 141 (11 abr 2026, Codex):** se ejecuta una observación extendida de `Step 5` sobre snapshot runtime fresco y preflight `observe/operational` en verde, sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`.
- **Base limpia confirmada:** se refresca `data/runtime_import/` por la vía canónica read-only (`tools/railway_runtime_snapshot_pull.ps1`), dejando `runtime_import_manifest.json` con `pulled_at=2026-04-11T10:52:35.9056147+00:00`. Ambos checks quedan verdes: `python tools/system_alignment_check.py => ok=7, warning=1, error=0`; `python tools/system_alignment_check.py --decision-mode operational => ok=7, warning=1, error=0`, sin `blocking_operational_collision`.
- **Throughput extendido observado:** se crea `docs/step5-throughput-observation-extended-2026-04-11.md` con una lectura de los últimos `20` ciclos manifestados (`2026-04-06T16:01Z` a `2026-04-11T08:00Z`). El funnel canónico queda en `raw_markets_fetched ~330` por ciclo, `candidates_after_prefilters=307`, `condition_filtered_out=285`, `candidates_with_edge=4`, `candidates_selected=4`, `trades_executed=4`, `shadow_opportunities_observed=2`. El cuello dominante sigue siendo estructural (`date`, `price`, `condition`), no edge/thresholds/bankroll.
- **Lectura honesta de auto-canary:** la sesión confirma que `auto_canary` no es solo clasificación: las `4` compras reales del tramo salen de ciudades hoy `auto_canary` (`Atlanta`, `Shanghai`, `Seoul`, `Tokyo`) y las `4` cierran como `RESOLVED_WIN` por `+$1.69`. Aun así, la conversión sigue siendo intermitente y no repetible en todas las canaries (`New York City` y `Munich` no convierten en esta ventana), así que la evidencia todavía no habilita una conversación honesta de monetización o policy.
- **Gate escrito y cierre corto:** se crean `docs/controlled-monetization-gate-2026-04-11.md` y `docs/throughput-observation-readout-2026-04-11.md`. El gate fija que la siguiente discusión de monetización controlada con bankroll `$25` solo sería honesta tras otra ventana read-only con preflight verde y una muestra claramente mayor (por ejemplo `>=10` cierres recientes bajo la política efectiva actual). `Chicago` sigue sin base para manual canary y no se detecta bug nuevo de accounting/counters que obligue a abrir correctness.

**Última actualización:** 11 de abril de 2026 (Sesión 137 — closeout y handoff limpio post-Opus)
**Sesión 137 (11 abr 2026, Codex):** se cierra la sesión dejando trazabilidad explícita del tramo posterior a Opus y un handoff limpio para abrir una sesión específica sobre la barrera de colisiones, en vez de mezclarla con alignment base o monetización.
- **Handoff limpio nuevo:** se crea `docs/next-session-handoff-2026-04-11-collision-barrier.md` para arrancar una sesión enfocada solo en `collision_count=17 > 5`, con orden de lectura mínimo, preflight `observe/operational` y regla explícita de no reabrir alignment base ni tocar throughput/policy todavía.
- **Puente claro para futuro Opus:** queda documentado que cualquier nueva revisión de Opus debe partir de `docs/opus-review-throughput-alignment-2026-04-10.md` más el trabajo posterior ya cerrado en sesiones `134-136` (target tagging, Step 5, Phase 6 y validación de la barrera de colisiones), de modo que Opus no reevalúe desde cero el paquete de alignment ya resuelto.

**Última actualización:** 11 de abril de 2026 (Sesión 136 — operational preflight hits collision barrier)
**Sesión 136 (11 abr 2026, Codex):** se ejecuta el siguiente paso lógico tras `Phase 6`: refrescar la `runtime_policy_effective_view` desde el snapshot manifestado y volver a correr el preflight en modo `operational`.
- **Frescura ya no bloquea:** tras regenerar `data/runtime_policy_effective_view.json` y `docs/runtime_policy_effective_view_latest.md`, la vista efectiva queda fresca (`generated_at=2026-04-11T09:38:56+00:00`) y desaparece el bloqueo por SLO de `6h`.
- **Barrera real expuesta:** `python tools/system_alignment_check.py --decision-mode operational` pasa a bloquear por `collision_count exceeds operational threshold`: `collision_count=17`, umbral `5`, `ok=6`, `warning=1`, `error=1`. Es la primera confirmación explícita de que la siguiente frontera ya no es alignment base ni frescura de artefactos, sino divergencia policy/runtime/cross todavía demasiado alta para una discusión operacional segura.
- **Lectura operativa nueva:** el siguiente paso ya no es seguir endureciendo preflight, sino decidir si conviene abrir una sesión específica de reducción/encuadre de colisiones o si la discusión futura debe asumir explícitamente que no se puede pasar a throughput/policy mientras esa barrera siga activa.

**Última actualización:** 11 de abril de 2026 (Sesión 135 — phase 6 decision preflight hardening)
**Sesión 135 (11 abr 2026, Codex):** se implementa la mini `Phase 6` recomendada por Opus para endurecer el preflight antes de cualquier discusión operativa, manteniendo todo read-only respecto a `polymarket-bot`.
- **Preflight con modos explícitos:** `tools/system_alignment_check.py` ahora distingue `--decision-mode observe` y `--decision-mode operational`. En `observe` el estado actual queda en `error=0`, `ok=6`, `warning=2`; en `operational` se escriben artefactos separados (`data/system_alignment_check_operational.json`, `docs/system_alignment_check_operational_latest.md`) y el check bloquea hoy por `effective view` fuera del SLO de `6h`.
- **Drift semántico cubierto:** se añade `prompt_semantic_scan` sobre prompts/docs canónicos para detectar citas ambiguas de `ACTIVE_TRADING_CITIES` y `markets_evaluated`. Se corrige el prompt histórico de throughput para remitir explícitamente a `effective_mode` y el scan queda en `ok`.
- **Contratos read-only nuevos:** se crean `docs/bot-funnel-counter-contract-2026-04-11.md` para mapear counters legacy de `bot.py` (`markets_evaluated`, `with_edge`, `selected`, `buys_real`, `condition_filtered`, etc.) a nombres canónicos del funnel, y `docs/decision-preflight-rules-2026-04-11.md` para fijar reglas de sesión `observe` vs `operational`, SLO de frescura, umbral de `collision_count` y la regla humana de no decidir por PnL con `<20` cerrados.
- **Roadmap y artefactos alineados:** `docs/system-alignment-lean-roadmap-2026-04-10.md`, `docs/system-alignment-phase-closeout-2026-04-11.md`, `docs/system-alignment-artifact-map-2026-04-11.md`, `docs/system-alignment-session-checklist-2026-04-11.md` y `docs/next-session-handoff-2026-04-10.md` quedan actualizados para reflejar que la fase base de alignment ya no solo está cerrada, sino endurecida para decisiones futuras sin drift silencioso.

**Última actualización:** 11 de abril de 2026 (Sesión 134 — target tagging city-intelligence)
**Sesión 134 (11 abr 2026, Codex):** se resuelve el warning restante de targets en el paquete de alineacion, manteniendo todo read-only respecto a `polymarket-bot` y sin tocar `bot.py`, `city_policy_state.json`, thresholds ni allowlists.
- **Contrato de targets separado:** `tools/city_intelligence_pipeline.py` deja de emitir `tracker_targets` como string plano y pasa a exponer `runtime_derived_targets`, `exploratory_targets` y `tracker_targets` como listas. Los `runtime_derived_targets` se derivan de `data/runtime_policy_effective_view.json` (ciudades con `effective_mode in {canary, active}`) y la lista exploratoria queda separada; con el snapshot actual: runtime-derived `Atlanta/Munich/New York City/Seoul/Shanghai/Tokyo`, exploratory `Chicago`.
- **Wrappers y docs alineados:** `tools/city_intelligence_service.py` y `tools/city_intelligence_railway_service.py` pasan a usar `CITY_INTELLIGENCE_EXPLORATORY_TARGETS` como superficie explicita, conservando compatibilidad minima con el flag legacy. `docs/city-intelligence-railway-service.md` documenta que las targets derivadas salen de `runtime_policy_effective_view.json` y que la lista exploratoria solo agrega extras fuera del runtime efectivo.
- **Checks y latest regenerados:** `tools/system_alignment_check.py` ahora exige listas explicitas para targets y detecta overlaps entre runtime-derived/exploratory. Tras regenerar `data/city_intelligence_pipeline.json`, `docs/city_intelligence_pipeline_latest.md`, `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`, el estado queda en `error=0`, `ok=3`, `warning=2`; los unicos warnings restantes siguen siendo los ya aceptados de `runtime_policy_effective_view` y `runtime_ledger`.
- **Step 5 observado sin tocar policy:** se completa una primera lectura honesta del throughput reciente en `docs/step5-throughput-observation-2026-04-11.md`. Ventana: ultimos `20` ciclos runtime con `raw_markets_fetched~330` por ciclo, `markets_evaluated` medio `14.3`, `condition_filtered=267`, `with_edge=4`, `selected=4`, `4` compras en `3` ciclos y `3/3` cierres recientes ganadores por `+$1.31`. El cuello dominante observado sigue siendo estructural (`condition_filtered_out`, fecha y precio), no `below_min_edge`; Chicago mantiene valor de observacion, pero sin evidencia nueva para promocion manual ni para pedir Opus todavia.
- **Shortlist shadow separada:** se crea `docs/shadow-opportunity-shortlist-2026-04-11.md` para distinguir señal shadow repetida de casos ya absorbidos por runtime canary o frenados por restricciones estructurales. Con la foto actual, `Chicago` queda como principal caso exploratorio a vigilar; `Hong Kong` y `Beijing` como secundarios; `Shanghai`, `Atlanta`, `New York City`, `Munich`, `Tokyo` y `Seoul` ya no son pregunta de "promocion shadow" porque su señal historica ya fue absorbida por `auto_canary`.
- **Cierre estructural de fase:** se crean `docs/system-alignment-phase-closeout-2026-04-11.md`, `docs/system-alignment-artifact-map-2026-04-11.md` y `docs/system-alignment-session-checklist-2026-04-11.md` para cerrar la fase de alignment como sistema operativo y no solo como lista de cambios. Queda explicitado que esta fase ya cerró manifest/effective view/funnel/checks/targets, qué pregunta responde cada artefacto, cuándo parar una sesión, cuándo abrir una limpia y cuándo escalar a Opus. `docs/system-alignment-lean-roadmap-2026-04-10.md` y `docs/next-session-handoff-2026-04-10.md` se actualizan para reflejar el estado nuevo: alignment base cerrado, Step 5 ya observado y siguiente trabajo orientado por checklist/mapa en vez de reabrir cableado.

**Última actualización:** 10 de abril de 2026 (Sesión 133 — handoff corto para continuar limpio)
**Sesión 133 (10 abr 2026, Codex):** se deja preparado un arranque corto para la siguiente sesion limpia, sin abrir bloque nuevo de implementacion.
- **Handoff actualizado:** se crea `docs/next-session-handoff-2026-04-10.md` con prompt exacto de arranque, orden de chequeos y foco exclusivo en el warning restante de targets (`runtime_derived_targets` vs `exploratory_targets`) antes de Step 5.
- **Roadmap refrescado:** `docs/system-alignment-lean-roadmap-2026-04-10.md` deja de apuntar al viejo Step 1 como mensaje sugerido y pasa a arrancar con `python tools/system_alignment_check.py`, revision de `system_alignment_check_latest.md`, `runtime_policy_effective_view_latest.md` y `metrics-funnel-naming.md`.
- **Cierre recomendado:** buen punto para cortar y retomar mañana. No hace falta Opus todavia; el siguiente checkpoint estrategico sigue siendo antes de tocar throughput/policy o si aparece una contradiccion nueva de arquitectura.

**Última actualización:** 10 de abril de 2026 (Sesión 132 — effective view, funnel naming y alignment check)
**Sesión 132 (10 abr 2026, Codex):** se avanzan Steps 2-4 del roadmap LEAN de alineacion sin pedir Opus, porque siguen siendo cambios read-only de contratos/observabilidad y no tocan riesgo, trading, thresholds, allowlists ni `bot.py`.
- **Step 2 effective view:** se crea `tools/runtime_policy_effective_view.py`, que genera `data/runtime_policy_effective_view.json` y `docs/runtime_policy_effective_view_latest.md` desde el snapshot manifestado + listas env declaradas. Validacion actual: Dallas `env_declared_mode=active`, `runtime_policy_mode=auto_shadow`, `effective_mode=shadow`, `collision_flag=true`; Atlanta/Munich/New York City/Seoul/Shanghai/Tokyo quedan `effective_mode=canary`; `active_effective_count=0`.
- **Step 3 naming funnel:** se crea `docs/metrics-funnel-naming.md` con nombres canonicos: `raw_markets_fetched`, `candidates_after_prefilters` (alias legacy `markets_evaluated`), `condition_filtered_out`, `candidates_with_edge`, `candidates_selected`, `trades_executed`, `shadow_opportunities_observed` y subrazones. Se ajustan docs activas para que `markets_evaluated` no quede ambiguo.
- **Step 4 alignment check:** se crea `tools/system_alignment_check.py`, que escribe `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`. Resultado actual: `error=0`, `ok=2`, `warning=3`. Warnings aceptados: divergencias policy efectivas listadas, `policy_divergence=6` en ledger runtime, y targets de `city-intelligence` todavia como string plano (`Shanghai,Chicago,Seoul`) sin etiquetas runtime-derived/exploratory.
- **Corte recomendado:** tras Steps 1-4, conviene cerrar sesion antes de Step 5/targets/throughput para arrancar limpio con `system_alignment_check.py` como preflight. Opus no es necesario aun; siguiente punto estrategico de Opus seria antes de tocar throughput/policy o despues de resolver target tagging si se quiere revisar el paquete de alineacion completo.

**Última actualización:** 10 de abril de 2026 (Sesión 131 — manifest runtime atomico/bijectivo)
**Sesión 131 (10 abr 2026, Codex):** se implementa Step 1 del roadmap LEAN de alineacion: manifest runtime atomico y completo, sin tocar `bot.py`, sin escribir `city_policy_state.json`, sin cambiar thresholds ni allowlists.
- **Pull atomico:** `tools/railway_runtime_snapshot_pull.ps1` ahora trae un snapshot ampliado de artefactos runtime (`shadow_city_tracking`, `cycles_history`, `cycle_summary`, `decisions`, `performance`, `postmortem`, `skip_log`, `trade_lifecycle`, `audit`, `city_policy_state`) hacia un directorio temporal, escribe manifest al final, valida bijeccion temporal y solo entonces reemplaza `data/runtime_import/`.
- **Manifest drift fail-closed:** `tools/city_validation_ledger.py` compara `runtime_import_manifest.json` contra los archivos reales del directorio; si falta un archivo listado, sobra un archivo no listado, hay duplicados o mismatch de bytes, emite `runtime_inputs_status=manifest_drift`, `cities=[]`, `manifest_drift_inputs` y `bottleneck_counts.runtime_inputs_manifest_drift=1`. `city_promotion_gate.py` y `city_intelligence_pipeline.py` propagan el estado como no disponible.
- **Validacion:** pull normal Railway read-only aprobado y ejecutado; `data/runtime_import/` queda limpio con 10 archivos manifestados + manifest, sin outputs derivados. Ledger normal: `runtime_inputs_status=available`, `manifest_file_count=10`, `disk_file_count=10`, `n_cities=24`. Casos simulados en copias temporales: archivo listado faltante => `manifest_drift/listed_file_missing`; archivo extra => `manifest_drift/unlisted_file_present`. Compilacion en memoria OK; `py_compile` sigue no usable por `__pycache__` bloqueado de Windows.

**Última actualización:** 10 de abril de 2026 (Sesión 130 — throughput/alignment audit pre-Opus)
**Sesión 130 (10 abr 2026, Codex):** se ejecuta una auditoria operativa read-only del throughput reciente y del cableado `polymarket-bot`/`city-intelligence`/`phase5`, sin tocar `bot.py`, sin escribir `city_policy_state.json`, sin cambiar thresholds ni allowlists.
- **Resultado reciente:** las 3 compras limpias desde el 7-8 abr cerraron ganadoras (`Atlanta +$0.63`, `Shanghai +$0.40`, `Seoul +$0.28`, total `3/3` y `+$1.31` en postmortem), pero la muestra es pequena y no justifica subir riesgo global.
- **Throughput real:** `decisions.log` sigue mostrando `MERCADOS: 330 encontrados`; el aparente scan bajo (`12-26`) es `markets_evaluated` post-filtros. Desde el 8 abr el embudo principal fue fecha/zona horaria, precio, `condition_filtered` por `ALLOWED_CONDITIONS=at_or_above,at_or_below` y `MIN_EDGE=15`.
- **Policy efectiva:** `ACTIVE_TRADING_CITIES=Dallas` no produce active real porque runtime tiene `Dallas` en `auto_shadow_cities`, que tiene prioridad. En la practica no hay ninguna ciudad `active`; el trading nuevo depende de canaries auto (`Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`) con sizing reducido.
- **Cableado pendiente:** `city-intelligence` live sigue en volumen separado, targets `Chicago,Dallas,Seattle,Munich,Madrid` y sin transporte runtime automatizado; el pipeline local default falla cerrado con `runtime_inputs_missing`, correcto como guardrail. El manifest de `runtime_import` debe volverse completo/atomico antes de automatizar, porque las lecturas manuales ampliadas pueden dejar archivos locales no representados por el manifest.
- **Artefactos:** se crean `docs/throughput-alignment-audit-2026-04-10.md` y `docs/claude-opus-prompt-throughput-alignment-review-2026-04-10.md`. Siguiente decision recomendada: que Opus revise si el proximo paso LEAN es automatizar transporte runtime primero, mejorar observabilidad del funnel o considerar una unica canary controlada (Chicago), sin tocar Dallas ni relajar filtros globales.
- **Handoff Opus ampliado:** el prompt de throughput se refuerza para pedir tambien revision del problema estructural de desalineacion entre capas: contratos canonicos `polymarket-bot`/`city-intelligence`, fuente de verdad por artefacto, manifest atomico, staleness, naming del funnel, targets, rol de phase5 y un roadmap LEAN de estandarizacion antes de crecer complejidad.
- **Respuesta Opus incorporada:** Opus devuelve `GO WITH CHANGES`, pero reencuadra el problema: no tocar throughput todavia; primero corregir estado confiable. Orden canonico propuesto: (1) manifest atomico/completo y directorio `runtime_import` bijectivo, (2) `runtime_policy_effective_view` read-only para matar ambiguedad env/runtime, (3) contrato de nombres del funnel, (4) `system_alignment_check.py` como pre-flight obligatorio, (5) observar throughput con datos manifestados antes de policy changes. Quedan explicitamente vetados por ahora: Chicago manual canary, Dallas active, exact/range, subir bankroll, automatizar sync roto, tocar `bot.py` o escribir `city_policy_state.json`. Artefacto: `docs/opus-review-throughput-alignment-2026-04-10.md`.
- **Roadmap operativo unico:** se crea `docs/system-alignment-lean-roadmap-2026-04-10.md` como checklist de arranque para sesiones nuevas. Primer paso obligatorio: Step 1 `manifest runtime atomico y completo`; no avanzar a throughput hasta tener manifest bijectivo, vista efectiva de policy, naming canonico del funnel y `system_alignment_check.py`.

**Última actualización:** 10 de abril de 2026 (Sesión 129 — staleness pre-automation de runtime import)
**Sesión 129 (10 abr 2026, Codex):** agotado temporalmente el cupo semanal de Claude/Opus, se deja anotada su ultima review (`GO WITH CHANGES` sobre `runtime_policy_mode`) y se avanza sin Opus al siguiente bloque LEAN recomendado: seguridad previa a automatizar transporte runtime.
- **Checkpoint Opus:** la ultima revision pidio auditar consumidores de `policy_mode`, marcar `runtime_only`, preservar `base_recommendation`, detectar colisiones runtime y documentar `cross_policy_mode=unknown` + runtime conocido como `policy_divergence` v0. Todo quedo aplicado en la sesion 128; no hace falta reabrir ese bloque salvo blocker real.
- **Staleness de snapshot:** `tools/city_validation_ledger.py` añade `--runtime-manifest` y `--max-runtime-snapshot-age-hours`. Si los tres runtime files existen pero el manifest falta, no parsea o supera el umbral, el ledger emite `runtime_inputs_status=stale`, `cities=[]`, `stale_runtime_inputs` y `bottleneck_counts.runtime_inputs_stale=1`.
- **Propagacion aguas abajo:** `tools/city_promotion_gate.py` convierte stale en `gate_status=runtime_snapshot_stale`; `tools/city_intelligence_pipeline.py` propaga `overall_status=runtime_inputs_stale`; Telegram alert y daily summary distinguen `missing` de `stale` y muestran nombres/razones concretas (`runtime_manifest:snapshot_stale`, `missing_manifest`, etc.).
- **Validaciones:** con `data/runtime_import/runtime_import_manifest.json` y umbral alto, el ledger queda `runtime_inputs_status=available`; con umbral `0.001h`, corta en `runtime_inputs_status=stale` y no emite filas; con partial-missing simulado (falta solo `city_policy_state`) corta en `runtime_inputs_status=missing` y la alerta lista exactamente `city_policy_state`; en local sin runtime sigue `runtime_inputs_status=missing`, `cities=[]`, `overall_status=runtime_inputs_missing`. No se toco `bot.py`, no se escribio `city_policy_state.json`, no se automatizo pull/sync.

**Última actualización:** 10 de abril de 2026 (Sesión 128 — runtime_policy_mode read-only en city-intelligence)
**Sesión 128 (10 abr 2026, Codex):** se implementa el siguiente paso LEAN validado por Opus antes de automatizar transporte runtime: reconciliar semanticamente `city_policy_state.json` dentro de `city-intelligence`, sin tocar `bot.py` ni escribir runtime.
- **Lectura read-only de policy runtime:** `tools/city_validation_ledger.py` ahora parsea `city_policy_state.json` y expone `runtime_policy_mode` (`auto_canary`, `auto_shadow`, `auto_blocked`, `runtime_unknown`) separado de `cross_policy_mode` procedente de `reference_trader_city_market_cross.json`. `policy_mode` pasa a ser la policy efectiva usada por el ledger cuando runtime esta disponible.
- **Drift explícito:** el ledger emite `drift_flags=["policy_divergence"]` cuando runtime y cross discrepan, e incluye filas `runtime_only` para ciudades presentes en `city_policy_state.json` pero ausentes en `cross.city_rows`.
- **Gate reconciliado:** `tools/city_promotion_gate.py` convierte `policy_divergence` en `gate_status=audit_runtime_drift`, de modo que Shanghai/Seoul/Tokyo/Munich/New York City ya no piden `review_for_canary` si runtime ya las tiene en `auto_canary_cities`.
- **Validación con snapshot real:** contra `data/runtime_import/*`, el ledger queda en `runtime_inputs_status=available`, `n_cities=24`, `auto_canary=6`, `auto_shadow=1`, `policy_divergence=5`; Shanghai queda `policy_mode=canary`, `cross_policy_mode=shadow`, `runtime_policy_mode=auto_canary`, `recommendation=audit_runtime_drift`, `gate_status=audit_runtime_drift`. Atlanta aparece como `runtime_only` + `observe_runtime_canary`.
- **Fail-closed intacto:** en local sin runtime, `city_validation_ledger.py`, `city_promotion_gate.py` y `city_intelligence_pipeline.py` siguen devolviendo `runtime_inputs_status=missing` / `overall_status=runtime_inputs_missing` con `cities=[]`. Se crea `docs/claude-opus-prompt-runtime-policy-mode-review-2026-04-10.md` como punto exacto para revisión de Opus antes de automatizar pull/sync runtime.
- **Hardening post-review Opus:** tras un nuevo `GO WITH CHANGES`, se preserva `base_recommendation`, se fuerza `evidence_status=runtime_only` en filas sintéticas, se detecta `runtime_policy_collision` y se auditan consumidores de `policy_mode`. Al refrescar inputs auxiliares, Dallas pasa a ser un sexto `policy_divergence` (`cross=active`, `runtime=auto_shadow`), quedando `n_cities=25`.

**Última actualización:** 10 de abril de 2026 (Sesión 127 — auditoría LEAN del transporte runtime read-only)
**Sesión 127 (10 abr 2026, Codex):** tras el `GO` de Opus al fail-closed endurecido, se audita el siguiente paso LEAN de transporte runtime sin tocar `bot.py`, sin cambiar volúmenes Railway y sin escribir en servicios live.
- **Evidencia Railway:** `volume list` confirma tres volúmenes separados: `polymarket-bot-volume` -> `polymarket-bot`, `city-intelligence-volume` -> `city-intelligence`, `phase5-visibility-volume` -> `phase5-visibility`, todos en `/app/data`. La ayuda de `volume attach/update` no muestra opción read-only; por tanto se descarta intentar montar el volumen del bot en `city-intelligence` como paso seguro.
- **Pull local read-only:** se crea `tools/railway_runtime_snapshot_pull.ps1`, que usa `tools/railway_safe.ps1 ssh -s polymarket-bot` para leer con `cat` `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` desde `/app/data` y copiarlos localmente a `data/runtime_import/` con manifest. No escribe en Railway ni toca el bot.
- **Validación de consumo runtime:** `city_validation_ledger.py` se ajusta a `utf-8-sig` porque las copias de PowerShell traen BOM. Ejecutando el ledger contra `data/runtime_import/*` se obtiene `runtime_inputs_status=available`, `n_cities=22`, `actionable=1`; Shanghai aparece con `shadow_edge_hits=19`, `shadow_cycles_seen=30`, `best_edge_pct=38.7`, `resolved_directional_count=0`, `noaa_rows=0`.
- **Nuevo cuello semántico:** aunque `city_policy_state.json` se importa, el ledger todavía no lo parsea; Shanghai sigue saliendo `policy_mode=shadow` y `candidate_for_canary_validation`, pese a que runtime live la tiene en `auto_canary`. El siguiente paso LEAN recomendado es leer `city_policy_state.json` read-only y separar `cross_policy_mode` de `runtime_policy_mode`/`policy_drift`, antes de automatizar sync en Railway.
- **Artefactos:** se crean `docs/city-intelligence-runtime-transport-audit-2026-04-10.md`, `docs/claude-opus-prompt-runtime-transport-review-2026-04-10.md`, `data/runtime_import/runtime_import_manifest.json`, `data/runtime_import/city_validation_ledger.runtime_import.json`, `data/runtime_import/city_promotion_gate.runtime_import.json`, `docs/city_validation_ledger_runtime_import.md` y `docs/city_promotion_gate_runtime_import.md`.

**Última actualización:** 10 de abril de 2026 (Sesión 126 — hardening pre-transporte del fail-closed city-intelligence)
**Sesión 126 (10 abr 2026, Codex):** se aplican las dos correcciones bloqueantes marcadas por Opus antes de avanzar a transporte runtime read-only, sin tocar `bot.py`.
- **Lazy import de `bot`:** `tools/city_validation_ledger.py` ya no importa `bot` al cargar el modulo. Primero evalua los inputs runtime obligatorios; si faltan, escribe el fail-closed sin cargar runtime. Solo si los inputs existen hace import lazy de `bot`; si ese import falla, tambien degrada a fail-closed incluyendo `bot_module` en `missing_runtime_inputs`.
- **Prioridad del estado runtime:** `tools/city_intelligence_pipeline.py` ahora deja que `runtime_inputs_missing` prevalezca incluso si algun paso externo previo causara `partial_failure`, evitando que un fallo de red en enrichment/probe esconda la señal principal de runtime ausente.
- **Docs alineadas:** `docs/system-architecture-city-intelligence-2026-04-10.md` aclara que el fail-closed v0 exige tres artefactos (`shadow_city_tracking.json`, `audit.json`, `city_policy_state.json`) y deja `cycles_history.jsonl` como input posterior de staleness/auditoria, no requisito v0. El prompt `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md` queda actualizado para indicar que las correcciones de Opus ya fueron aplicadas.
- **Validación:** sintaxis validada con `compile(...)`; `python tools/city_intelligence_pipeline.py --telegram-dry-run` sigue cerrando en `overall_status=runtime_inputs_missing`; se valido la rama disponible con paths placeholder y se regenero `docs/city_intelligence_alert_latest.md` usando estado temporal para mostrar el mensaje honesto sin alterar el anti-spam real. Se limpio el temporal con elevacion por bloqueo de Windows.

**Última actualización:** 10 de abril de 2026 (Sesión 125 — fail-closed runtime missing en city-intelligence)
**Sesión 125 (10 abr 2026, Codex):** se implementa el primer paso LEAN recomendado por Opus: `city-intelligence` falla cerrado cuando no tiene acceso a artefactos runtime del bot, sin tocar `bot.py` ni trading core.
- **Cambio en ledger:** `tools/city_validation_ledger.py` añade `--city-policy-state` y valida como inputs runtime obligatorios `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`. Si falta cualquiera, escribe `summary.runtime_inputs_status=missing`, lista `missing_runtime_inputs`, `cities=[]` y `bottleneck_counts.runtime_inputs_missing=1`; deja de convertir ausencia de runtime en `edge_evidence=0`.
- **Cambio en gate/pipeline/alertas:** `tools/city_promotion_gate.py` propaga el bloqueo como `gate_status=runtime_inputs_missing` con fila sintética `city=runtime`; `tools/city_intelligence_pipeline.py` marca `overall_status=runtime_inputs_missing`; Telegram alert y daily summary explican que no se puede concluir nada fiable por ciudad hasta conectar runtime read-only.
- **Validación local:** en el repo local faltan `data/shadow_city_tracking.json`, `data/audit.json` y `data/city_policy_state.json`; `python tools/city_intelligence_pipeline.py --telegram-dry-run` termina con `overall_status=runtime_inputs_missing`, `dominant_bottleneck=runtime_inputs_missing`, `review_queue_size=1`, `actionable/building/insufficient=0`; `python tools/city_intelligence_daily_summary.py --dry-run` emite mensaje honesto de runtime faltante. Sintaxis validada con `compile(...)` sin escribir `.pyc` porque `py_compile` encontro `__pycache__` bloqueado por Windows.
- **Artefactos:** se regeneran `data/city_validation_ledger.json`, `data/city_promotion_gate.json`, `data/city_intelligence_pipeline.json`, estados de alert/daily y docs latest correspondientes con el nuevo estado fail-closed. Se crea `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md`; el siguiente punto de revisión de Opus es ahora, antes de decidir transporte runtime.

**Última actualización:** 10 de abril de 2026 (Sesión 124 — revisión Opus incorporada a la arquitectura city-intelligence)
**Sesión 124 (10 abr 2026, Codex):** se incorpora la revisión adversarial de Opus sobre `docs/system-architecture-city-intelligence-2026-04-10.md`, sin implementar código ni tocar `bot.py`.
- **Veredicto Opus:** `GO WITH CHANGES`. La dirección general es correcta, pero el documento no podía quedar como canon operativo cerrado porque el código actual ya contradice varios supuestos.
- **Deuda explicitada:** `tools/city_validation_ledger.py` hace `import bot` y usa constantes runtime (`OBSERVED_AUDIT_KEY`, `RESOLUTION_ICAO`, thresholds de shadow/canary), así que `city-intelligence` no está desacoplado en el plano de imports. Se documenta como deuda arquitectónica.
- **Bug real redefinido:** el problema de Shanghai no es solo drift semántico; es plumbing: inputs runtime ausentes + `required=False` + `available=False` descartado terminan en ceros mudos. La arquitectura corregida exige fail-closed con `runtime_inputs_status=missing` antes de emitir gates/alertas normales.
- **Contratos corregidos:** se aclara que `policy_mode` actual viene de `reference_trader_city_market_cross.json`, no de `city_policy_state.json`; que el ledger hoy itera solo `cross.city_rows`; que `runtime_policy_mode`, `analytics_policy_mode`, `drift_flags` y estados como `audit_runtime_drift` son objetivo futuro, no comportamiento vivo.
- **Shanghai y Phase 5:** Shanghai queda definido como auditoría posterior a `auto_canary`, no como candidata pendiente de promoción; `edge_hits=19` justifica exploración canary barata pero no WR observado. `phase5-visibility` queda congelable como legacy solo tras migrar la alerta one-shot y verificar que queda un único escritor del tracker.
- **Artefactos:** se actualiza `docs/system-architecture-city-intelligence-2026-04-10.md` y se crea `docs/opus-review-system-architecture-city-intelligence-2026-04-10.md` como resumen trazable de la revisión.

**Última actualización:** 10 de abril de 2026 (Sesión 123 — arquitectura canónica polymarket-bot/city-intelligence)
**Sesión 123 (10 abr 2026, Codex):** se define la arquitectura canónica documental entre `polymarket-bot`, `city-intelligence` y la capa experimental `phase5-visibility`, sin tocar `bot.py` ni trading core.
- **Arquitectura actual factual:** `polymarket-bot` queda fijado como fuente de verdad runtime para trading, policy viva y artefactos `/app/data` (`shadow_city_tracking.json`, `cycles_history.jsonl`, `audit.json`, `city_policy_state.json`); `city-intelligence` queda como capa analítica read-only que hoy corre en volumen separado y por eso puede producir ledgers/gates divergentes si no importa runtime.
- **Arquitectura objetivo:** `city-intelligence` debe consumir un snapshot runtime explícito o montaje read-only antes de emitir ledger/gate; si faltan inputs runtime debe marcar `runtime_inputs_missing`, no inferir `edge_evidence=0`. Los gates son cola de revisión humana/Codex/Opus, no actuadores de policy.
- **Shanghai como caso guía:** el documento separa `runtime_policy_mode=canary`/`auto_canary` y agregados (`edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`) de la falta de `directional_history` resoluble contra NOAA.
- **Phase 5:** se evalúa `phase5-visibility` como experimento/legacy anterior a `city-intelligence`; conserva valor en visibilidad temporal, comparador Shanghai/Chicago y patrón one-shot de alerta, pero su rol objetivo es fusión funcional en `city-intelligence` + archivo documental, no segundo plano decisional.
- **Artefactos:** se crean `docs/system-architecture-city-intelligence-2026-04-10.md` y `docs/claude-opus-prompt-system-architecture-city-intelligence-2026-04-10.md` para revisión adversarial de Opus antes de implementar cualquier integración.

**Última actualización:** 10 de abril de 2026 (Sesión 122 — auditoría live del loop Shanghai entre bot principal y city-intelligence)
**Sesión 122 (10 abr 2026, Codex):** se ejecuta la siguiente auditoría lógica en Railway, read-only, comparando el servicio auxiliar `city-intelligence` con el runtime real de `polymarket-bot`.
- **Hallazgo central:** `city-intelligence` corre sano pero en un volumen separado que no contiene `shadow_city_tracking.json`, `cycles_history.jsonl` ni `audit.json`; su ledger apunta a esas rutas en `/app/data`, pero al no existir en ese volumen cae a inputs vacíos. Por eso `edge_evidence=0` en el ledger auxiliar no prueba ausencia de shadow real.
- **Shanghai sí tiene huella live en el bot principal:** el volumen de `polymarket-bot` sí contiene los archivos runtime y `shadow_city_tracking.json` muestra para `Shanghai`: `markets_seen=84`, `edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`, `last_seen_at=2026-04-10T08:00:42Z`.
- **Policy live divergente:** `city_policy_state.json` del bot principal muestra `Shanghai` en `auto_canary_cities`, autopromovida el `2026-04-06T12:33:22Z` por `19` edges shadow y `15` ciclos. Por tanto `Shanghai` no es shadow puro en el runtime live aunque `city-intelligence` la trate como caso analítico shadow/ausente.
- **Riesgo restante:** `directional_history` en `shadow_city_tracking.json` sigue vacío, así que hay agregados de edge/ciclos por ciudad pero no una base persistente resoluble contra NOAA. El siguiente paso no es Austin/Wuhan: es alinear `city-intelligence` con la evidencia runtime del bot principal antes de producir gates de promoción.
- **Artefacto:** se crea `docs/shanghai-shadow-live-audit-2026-04-10.md` con evidencia, conclusión e instrucción para la próxima sesión.

**Última actualización:** 10 de abril de 2026 (Sesión 121 — auditoría adversarial del loop shadow de Shanghai)
**Sesión 121 (10 abr 2026, Codex):** se revisa la lectura estratégica de Claude sobre `city-intelligence` y se audita localmente el loop `shadow -> shadow_city_tracking -> edge_evidence` sin tocar `bot.py` ni trading core.
- **Diagnóstico confirmado:** en local no existen `data/shadow_city_tracking.json`, `data/cycles_history.jsonl` ni `data/audit.json`, por lo que el ledger no puede tener evidencia shadow/NOAA propia; `Shanghai` sigue siendo el único caso formal en `shadow_validation`, pero con `edge_score=0`, `shadow_edge_hits=0`, `shadow_cycles_seen=0` y `noaa_rows=0`.
- **Austin no es siguiente foco:** tras regenerar la pipeline local, `Austin` cae incluso a `trader_discovery` por tener solo `2` refs en la foto actual y `settlement_fidelity.score=0`; auditarla ahora seria onboarding/plumbing, no evidencia de monetizacion. `Wuhan` queda como `source_fidelity` con metadata parcial.
- **Pipeline stale corregido:** se regenera `tools/city_intelligence_pipeline.py --telegram-dry-run` sin refresh de probe/censo. `docs/city_intelligence_pipeline_latest.md` deja de contradecir el ledger y queda en `overall_status=ok`, `signal_health=usable_signal`, `dominant_bottleneck=trader_discovery`, `quality_reference_traders=7`.
- **Siguiente paso correcto:** no profundizar en Austin/Wuhan todavia; auditar en Railway si `/app/data/shadow_city_tracking.json` y `/app/data/cycles_history.jsonl` contienen huella real de `Shanghai`, o si el shadow de Shanghai no esta generando datos pese a estar en policy `shadow`.

**Última actualización:** 9 de abril de 2026 (Sesión 120 — auditoría del cuello real post-censo y alineación del promotion gate)
**Sesión 120 (9 abr 2026, Codex):** se cierra la sesión separada de auditoría sobre el cuello real de `city-intelligence` después del fix del censo comparable, sin tocar `bot.py` ni el trading core.
- **Artefacto stale aislado y regenerado:** se confirma que `data/reference_trader_city_market_cross.json` seguía congelado en una corrida vieja con `low_signal`, aunque `data/directional_trader_enrichment.json` ya estaba sano. Se regeneran `reference_trader_city_market_cross`, `city_validation_ledger` y `city_promotion_gate`, y la foto resultante deja de hablar de `trader_input_degraded/trader_input_quality`.
- **Diagnóstico real del sistema tras refresh completo:** el ledger actualizado pasa a `21` ciudades y distribuye cuellos reales en vez de un falso cuello único: `trader_discovery=12`, `market_visibility=5`, `source_fidelity=3`, `shadow_validation=1`. El gate vuelve a tener `dominant_bottleneck=trader_discovery`, pero solo `Shanghai` queda realmente como caso de `shadow_validation`.
- **Prometedoras separadas por cuello útil:** `Shanghai` queda como única ciudad cuyo siguiente bloqueo útil ya es `shadow_validation`; `Austin` y `Wuhan` dejan de caer erróneamente en `needs_shadow_validation` y pasan a estar frenadas por `source_fidelity`; `Ankara`, `Madrid`, `Hong Kong`, `Milan` y `New York City` quedan clasificadas por `market_visibility`.
- **Gate alineado con el ledger:** `tools/city_promotion_gate.py` se ajusta para que el gate siga el bottleneck real del ledger y no tape `source_fidelity`/`market_visibility` bajo la etiqueta genérica `needs_shadow_validation`. El estado final queda resumido en `data/city_promotion_gate.json`: `needs_shadow_validation=1`, `watch_closely=5`, `observe_with_source_caution=3`, `background_watch=12`.

**Última actualización:** 9 de abril de 2026 (Sesión 119 — validación live del censo comparable en city-intelligence)
**Sesión 119 (9 abr 2026, Codex):** se cierra la investigación nueva sobre el censo comparable y se valida en Railway el cambio mínimo recomendado por Opus: ampliar el universo de `city-intelligence` a `200` mercados antes de rediseñar el censo.
- **Investigación separada y validación metodológica:** se crea `docs/comparable-trader-census-audit-2026-04-09.md` y `docs/claude-opus-prompt-comparable-trader-census-audit-2026-04-09.md`. La auditoría live demuestra que el `0 traders after filter` no probaba ausencia de comparables, sino un slice demasiado estrecho (`20` mercados top-volume) más un prefilter temprano por precio. Claude Opus valida el diagnóstico y prioriza ampliar el universo a `200` antes de tocar la arquitectura del censo.
- **Cambio mínimo aplicado y validado:** `tools/city_intelligence_service.py`, `tools/city_intelligence_railway_service.py` y `tools/city_intelligence_pipeline.py` pasan a default `--census-markets 200`; `docs/city-intelligence-railway-service.md` queda alineado. En Railway se valida una corrida real a las `18:00 UTC` con `--refresh-census --census-markets 200`, `overall_status=ok`, `signal_health=usable_signal` y `quality_reference_traders=9`.
- **Configuración live estabilizada:** `city-intelligence` queda finalmente con `CITY_INTELLIGENCE_CENSUS_MARKETS=200`, `CITY_INTELLIGENCE_REFRESH_CENSUS=false`, `CITY_INTELLIGENCE_REFRESH_PROBE=true` y `CITY_INTELLIGENCE_TARGETS=Chicago,Dallas,Seattle,Munich,Madrid`. Se abandona la shortlist histórica `Shanghai,Chicago,Seoul` para el tracker del servicio principal y se deja pendiente una revisión separada de `phase5-visibility`, sin mezclar ambos frentes.
- **Nuevo frente explicitado:** el primer aviso útil post-cambio ya no habla de “0 traders comparables”, sino de `dominant_bottleneck=trader_discovery` con ciudades prometedoras como `Moscow`, `Toronto`, `Austin` y `Houston` cayendo en `needs_shadow_validation`. Queda decidido que la siguiente sesión correcta debe auditar si el cuello real es `trader_discovery` o `shadow_validation`, sin tocar `bot.py` ni el trading core.

**Sesión 118 (9 abr 2026, Codex):** se cierra una sesión técnica dedicada exclusivamente al proxy local `127.0.0.1:9`, separando definitivamente el problema de red del runtime de Codex del resto del entorno Windows y dejando un wrapper seguro para verificaciones futuras.
- **Causa raíz atribuida con evidencia:** los proxies `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_* = http://127.0.0.1:9` no salen de variables persistentes de Windows, perfiles de PowerShell, `.vscode`, `git` ni `npm`. Aparecen solo en el proceso actual lanzado por la extensión de Codex en VS Code, acompañado de `CODEX_SANDBOX_NETWORK_DISABLED=1`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_vscode` y segmentos sandbox en `PATH` (`.sbx-denybin`, `.codex\\tmp\\arg0\\...`, binario de la extensión OpenAI).
- **Mitigación estable en el repo:** se añaden `tools/run_clean_network.ps1` y `tools/polymarket_api_probe.py`, junto con `docs/local-network-proxy-audit-2026-04-09.md`. El wrapper limpia proxies y variables `CODEX_*` solo para el proceso hijo, elimina rutas sandbox del `PATH`, ejecuta el comando real y restaura el entorno al salir.
- **Validación end-to-end:** ejecutado fuera del sandbox con el wrapper, `python tools/polymarket_api_probe.py` devuelve `200` en `https://data-api.polymarket.com/trades?limit=1` y `https://data-api.polymarket.com/positions?...`. Queda fijado que un `403` previo dentro de pruebas inline ya no era síntoma de proxy roto sino respuesta real del API a la forma de la petición; con `User-Agent` explícito y wrapper limpio la conectividad queda confirmada.

**Sesión 117 (9 abr 2026, Codex):** se deja operativo en Railway un servicio nuevo `city-intelligence` para ejecutar la capa de mejora continua del sistema de traders/ciudades sin tocar el core de `bot.py`.
- **Servicio Railway unificado:** se crea `city-intelligence` dentro del proyecto `enchanting-respect`, con volumen dedicado `city-intelligence-volume` montado en `/app/data`, `RAILPACK_START_CMD=python -u tools/city_intelligence_railway_service.py` y variables propias (`CITY_INTELLIGENCE_ALIGN_UTC_HOURS=0,6,12,18`, `CITY_INTELLIGENCE_DAILY_HOUR_UTC=7`, `CITY_INTELLIGENCE_PROBE_LIMIT=12`, `CITY_INTELLIGENCE_CENSUS_MARKETS=20`, `CITY_INTELLIGENCE_TARGETS=Shanghai,Chicago,Seoul`, `CITY_INTELLIGENCE_REFRESH_PROBE=true`, `CITY_INTELLIGENCE_REFRESH_CENSUS=false`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`).
- **Loop live confirmado:** el despliegue `cf189b91-ac6a-4d29-a771-5c81abc13d4c` queda en `SUCCESS` y los logs muestran el runner durmiendo hasta `2026-04-09T00:00:00+00:00` para la primera corrida del pipeline intradía.
- **Arquitectura y wrappers nuevos:** se añaden `tools/city_intelligence_service.py`, `tools/city_intelligence_daily_service.py`, `tools/city_intelligence_railway_service.py` y `docs/city-intelligence-railway-service.md`. El diseño recomendado en Railway queda simplificado a un solo servicio que combina pipeline cada `6h` + resumen diario `07:00 UTC` usando el mismo volumen/estado.

**Sesión 116 (8 abr 2026, Codex):** se cierra una esquina técnica detectada en logs live del bot principal: el warning de deprecación por `datetime.utcnow()` en el bloque de salud del dashboard/focus, sin tocar trading core ni comportamiento operativo.
- **Fix puntual y seguro:** en `bot.py` se sustituye el cálculo naive `datetime.utcnow()` por `datetime.now(timezone.utc)` y se normaliza `_last_cycle` como datetime aware en UTC antes de medir horas desde el último ciclo.
- **Motivación:** los logs live mostraban `DeprecationWarning` en `bot.py:7301` durante el incidente colateral del servicio auxiliar. No afectaba a trading, pero sí dejaba ruido técnico innecesario y una incompatibilidad futura con Python.
- **Validación:** `python verify_before_deploy.py` vuelve a cerrar en `643/643`.

**Sesión 115 (8 abr 2026, Codex):** se deja documentado el siguiente gran frente del proyecto: una automatización read-only orientada a aprender de traders exitosos comparables a nuestro universo y transformar esa evidencia en recomendaciones por ciudad, con validación estratégica previa por Claude Opus antes de implementar.
- **Roadmap canónico del nuevo sistema:** se crea `docs/city-intelligence-automation-roadmap-2026-04-08.md`. El documento fija objetivo, no-objetivos, flujo completo (`comparable trader universe -> trader-city linker -> city evidence ledger -> city ranking engine -> alerts/review triggers`), arquitectura propuesta, artefactos previstos, métricas, riesgos y hoja de ruta por fases.
- **Handoff explícito a Claude Opus:** se crea `docs/claude-opus-prompt-city-intelligence-validation-2026-04-08.md` con un prompt listo para que Opus actúe como revisor estratégico y emita un `GO`, `GO WITH CHANGES` o `NO-GO` antes de que Codex implemente.
- **Contrato de continuidad:** queda decidido que la siguiente implementación no empieza por intuición, sino solo después de la revisión de Opus. La primera pieza prevista tras validación es `Trader-City Linker v1`, seguida por `City Evidence Ledger v1` y `City Ranking Engine v1`, siempre en modo read-only y sin tocar el core del bot.

**Sesión 114 (8 abr 2026, Codex):** se despliega en Railway un servicio separado `phase5-visibility` para ejecutar periodicamente la pipeline read-only de la fase 5 y avisar por Telegram cuando aparezca una coincidencia nueva `Shanghai + Chicago`, sin tocar el core del bot principal.
- **Servicio separado en Railway:** se crea el servicio `phase5-visibility` dentro del proyecto `enchanting-respect`, con volumen dedicado `phase5-visibility-volume` montado en `/app/data`, variables propias (`RAILPACK_START_CMD`, `PHASE5_INTERVAL_MINUTES=180`, `PHASE5_PROBE_LIMIT=20`, `PHASE5_REFRESH_PROBE=true`, `PHASE5_TARGETS=Shanghai,Chicago`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`) y despliegue validado en production.
- **Bootstrap automatico del volumen:** se crea `tools/phase5_visibility_service.py` junto con `docs/phase5-visibility-service.md` y un `seed_data/phase5/` versionado con los artefactos base necesarios (`city_watch_reinforced.json`, `reference_trader_city_market_cross.json`, `directional_trader_enrichment.json`). El servicio siembra esos inputs al arrancar si el volumen esta vacio y luego ejecuta `tools/phase5_visibility_pipeline.py`.
- **Estado live validado:** el despliegue final `7710189e-d820-47ed-b5f9-3715382287b0` arranca correctamente el runner de fase 5, deja `overall_status=ok`, incrementa `visibility_snapshots` a `2`, mantiene `simultaneous_visibility_count=0` y entra en reposo de `10800s` entre corridas. La alerta sigue correctamente en `no_simultaneous_visibility`.

**Sesión 113 (8 abr 2026, Codex):** se añade la alerta one-shot por Telegram a la fase 5 para que Railway pueda avisar automaticamente cuando aparezca una coincidencia nueva `Shanghai + Chicago`, sin tocar el core del bot.
- **Nueva capa de alerta separada del core:** se crea `tools/phase5_visibility_telegram_alert.py` con `docs/phase5-visibility-telegram-alert.md`. La herramienta lee el tracker y el comparador, usa `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` y persiste anti-spam en `data/phase5_visibility_alert_state.json`.
- **Pipeline ampliado:** `tools/phase5_visibility_pipeline.py` pasa a incluir la nueva etapa `phase5_visibility_telegram_alert`, manteniendo la tuberia completa en modo read-only.
- **Validacion inicial:** hoy la alerta no dispara (`decision_reason=no_simultaneous_visibility`), lo cual es correcto: todavia no existe una coincidencia simultanea entre `Shanghai` y `Chicago`. Queda listo para Railway como job periodico sin riesgo de spam hasta que aparezca evidencia nueva.

**Sesión 112 (8 abr 2026, Codex):** se automatiza la fase 5 completa en un solo comando read-only, pasando de piezas sueltas a una tubería reproducible que regenera snapshots, benchmark y comparador sobre la evidencia visible más reciente.
- **Nuevo pipeline orquestado:** se crea `tools/phase5_visibility_pipeline.py` con `docs/phase5-visibility-pipeline.md`. La tubería encadena `city_probe_visibility_tracker`, `shanghai_shadow_test`, `chicago_active_benchmark` y `shanghai_vs_chicago_comparator`, con opcion de refrescar primero `settlement_fidelity_probe.py`.
- **Artefactos generados:** la primera corrida deja `data/phase5_visibility_pipeline.json` + `docs/phase5_visibility_pipeline_latest.md`.
- **Estado operativo consolidado:** la ejecucion cierra `overall_status=ok` y resume de forma consistente el estado actual: `visibility_snapshots=1`, `simultaneous_visibility_count=0`, `Shanghai -> expand_observability`, `Chicago -> use_as_active_benchmark`, `dominant_gap=market_visibility_and_selection`.

**Sesión 111 (8 abr 2026, Codex):** se implementa la capa persistente de visibilidad del `settlement probe` para dejar de comparar `Shanghai` y `Chicago` con snapshots aislados y empezar a acumular evidencia de coincidencia real.
- **Nuevo tracker de visibilidad:** se crea `tools/city_probe_visibility_tracker.py` con `docs/city-probe-visibility-tracker.md`. La herramienta toma `data/settlement_fidelity_probe.json`, registra si las ciudades objetivo aparecen o no, cuántos mercados muestran y si existe visibilidad simultánea.
- **Artefactos generados:** la primera corrida deja `data/city_probe_visibility_tracker.json` + `docs/city_probe_visibility_tracker_latest.md`.
- **Lectura operativa nueva:** la base arranca con `1` snapshot, `0` coincidencias simultáneas, `Shanghai visible en 1` y `Chicago visible en 0`. Esto convierte la hipótesis previa en evidencia persistida: el cuello inmediato para comparar ambas ciudades no es todavía forecast, sino disponibilidad/visibilidad conjunta en el flujo de mercados.

**Sesión 110 (8 abr 2026, Codex):** se cierra el comparador directo entre `Shanghai` y `Chicago` para identificar el gap operativo dominante entre la ciudad puente `shadow` y el benchmark `active`.
- **Nuevo comparador directo:** se crea `tools/shanghai_vs_chicago_comparator.py` con `docs/shanghai-vs-chicago-comparator.md`. Consume los snapshots ya generados de `Shanghai` y `Chicago` y devuelve una lectura compacta por dimension junto con un `dominant_gap`.
- **Artefactos generados:** la primera corrida deja `data/shanghai_vs_chicago_comparator.json` + `docs/shanghai_vs_chicago_comparator_latest.md`.
- **Decision estrategica nueva:** el comparador concluye que el gap dominante observado hoy es `market_visibility_and_selection`, no forecast puro. `Shanghai` gana en visibilidad actual de mercado y profundidad de referencias; `Chicago` gana en rol operativo actual (`active`). La recomendacion resultante es `track_chicago_visibility_and_compare_when_probe_catches_it`, o sea reforzar observabilidad comparativa de mercados visibles antes de inferir timing o edge de modelo.

**Sesión 109 (8 abr 2026, Codex):** se crea el benchmark operativo especifico de `Chicago` para emparejar la observabilidad de `Shanghai` con una ciudad `active` real, manteniendo la investigacion en modo read-only.
- **Nuevo artefacto espejo de Chicago:** se crea `tools/chicago_active_benchmark.py` con `docs/chicago-active-benchmark.md`. La herramienta reutiliza el snapshot base por ciudad y añade una lectura propia de `benchmark_strength`, `observability_status` y `next_action` para evaluar si Chicago sirve como referencia operativa creible.
- **Artefactos generados:** la primera corrida deja `data/chicago_active_benchmark.json` + `docs/chicago_active_benchmark_latest.md`.
- **Lectura operativa nueva:** `Chicago` sale como `benchmark_strength=credible`, `observability_status=ok` y `next_action=use_as_active_benchmark`. No habia mercados visibles en el probe local actual, pero la ciudad sigue siendo valiosa como benchmark porque ya es `active` y aparece tocada por `2` referencias comparables fuertes (`Academic-Maniac`, `Motionless-Stalk`).

**Sesión 108 (8 abr 2026, Codex):** se construye el contraste multi-ciudad posterior al primer snapshot de `Shanghai`, para evitar que la siguiente decision estrategica dependa de una sola ciudad puente y anclarla contra una ciudad `active` real.
- **Nuevo comparador de fase siguiente:** se crea `tools/city_phase5_contrast.py` con `docs/city-phase5-contrast.md`. La herramienta reutiliza el motor de snapshot del test de `Shanghai` y compara `Shanghai`, `Chicago` y `Seoul` en una sola salida.
- **Artefactos generados:** la primera corrida deja `data/city_phase5_contrast.json` + `docs/city_phase5_contrast_latest.md`, con ranking, racional por ciudad y una recomendacion unificada de continuidad.
- **Lectura estrategica nueva:** `Shanghai` sigue primera, `Seoul` segunda y `Chicago` tercera en este contraste local. La recomendacion resultante ya no es solo “seguir mirando Shanghai”, sino `continue_shanghai_observability_plus_active_contrast`: es decir, mantener a `Shanghai` como ciudad puente principal pero contrastandola explicitamente contra `Chicago` como benchmark activo para evitar sobreajuste narrativo.

**Sesión 107 (8 abr 2026, Codex):** se implementa el extractor read-only especifico para `Shanghai` y se deja la primera corrida local del `shadow test`, ya con artefactos generados y una recomendacion operativa intermedia.
- **Nueva herramienta ejecutable:** se crea `tools/shanghai_shadow_test.py` junto con `docs/shanghai-shadow-test.md`. Consume el readout reforzado, el cruce por ciudad, el enrichment de traders y el settlement probe, y ademas tolera la ausencia de `data/shadow_city_tracking.json` y `data/audit.json` en local para no romper el flujo offline.
- **Artefactos generados:** la primera ejecucion deja `data/shanghai_shadow_test.json` + `docs/shanghai_shadow_test_latest.md`. El snapshot resume baseline, contexto de ciudad, referencias comparables, mercados visibles en probe, estado de `shadow tracking`, estado de `audit` y una `assessment` final.
- **Lectura inicial del test:** la salida clasifica `Shanghai` como `signal_status=building`, `data_quality=ok` y `next_action=expand_observability`. La racional actual es clara: hay `4` referencias comparables y `2` mercados visibles en el probe, pero todavia no existe en local evidencia adicional de `shadow tracking` o `NOAA audit` para justificar un salto a `prepare_controlled_test`.

**Sesión 106 (8 abr 2026, Codex):** se cierra la fase de priorización y se deja documentado el contrato del siguiente bloque operativo: un `shadow test` especifico para `Shanghai`, diseñado para producir evidencia nueva sin tocar todavia el core del bot.
- **Contrato operativo nuevo:** se crea `docs/shanghai-shadow-test-design.md` como documento fuente del siguiente experimento. El texto fija por que `Shanghai` es la ciudad puente principal, que preguntas debe responder el test, que metricas deben medirse, que artefactos nuevos se recomiendan y que criterios separan `stay shadow`, `expand observability` y `prepare controlled test`.
- **Guardrails explicitados:** el diseño deja claro que esta fase sigue siendo `read-only`: no mueve `Shanghai` a `canary/active`, no cambia `MIN_EDGE`, no toca `bot.py`, no abre `exact/range` y no reinterpreta la investigacion previa como permiso para cambiar la estrategia.
- **Siguiente implementacion ya acotada:** queda aprobado como proximo paso crear un extractor dedicado tipo `tools/shanghai_shadow_test.py` con salidas separadas (`data/shanghai_shadow_test.json` + `docs/shanghai_shadow_test_latest.md`) para medir senal shadow propia, calidad observacional y comparabilidad contra traders de referencia.

**Sesión 105 (8 abr 2026, Codex):** se ejecuta la fase siguiente a la watchlist general y se deja una `city watch` reforzada focalizada en `Shanghai`, `Chicago` y `Seoul`, con siguiente paso recomendado explícito por ciudad.
- **Nuevo readout focalizado por ciudad:** se crea `tools/city_watch_reinforced.py` con `docs/city-watch-reinforced.md`. La salida `data/city_watch_reinforced.json` + `docs/city_watch_reinforced_latest.md` resume policy, referencias reales, mercados visibles y `next_step` para las ciudades más importantes del siguiente bloque.
- **Jerarquía ya resuelta:** `Shanghai` queda claramente primera (`prepare_shadow_test_design`), `Chicago` segunda (`watch_live_active_city`) y `Seoul` tercera (`expand_shadow_observability`). Esto reduce la ambigüedad estratégica: el proyecto ya no necesita otra ronda de exploración general, sino una mini-fase concreta centrada en `Shanghai`.
- **Decisión de continuidad implícita:** si seguimos por orden y sin tocar todavía el core, el siguiente bloque correcto es diseñar un `shadow test` bien delimitado para `Shanghai`, usando la evidencia de referencias reales y el snapshot actual de mercado como base.

**Sesión 104 (8 abr 2026, Codex):** fase 4 completada: la investigación ya desemboca en una `watchlist` operativa por ciudad, con acción recomendada explícita y orden de prioridad para el siguiente bloque sin tocar aún la lógica core del bot.
- **Nueva salida operativa de alto nivel:** se crea `tools/city_watchlist_phase4.py` con `docs/city-watchlist-phase4.md`. La herramienta convierte las fases previas en una watchlist con acciones `prepare_test`, `watch_active`, `review_block_reason`, `observe_closely` y `background_watch`.
- **Orden recomendado ya fijado:** la primera ejecución deja `Shanghai` como mejor ciudad para `prepare_test` (`shadow`, referencias fuertes y mercados visibles en el probe), `Chicago` como `watch_active` principal dentro del universo ya operable, y `Ankara` como `review_block_reason` por la fuerza de las referencias pese a seguir `blocked`. Detrás aparecen `Austin`, `Wuhan` y `Seoul` como ciudades a observar de cerca.
- **Estado estratégico del proyecto tras fase 4:** ya no estamos en investigación abierta, sino en un punto donde el siguiente paso lógico puede ser un bloque muy concreto de observabilidad reforzada por ciudad. La mejor secuencia ya no es “buscar más ideas”, sino decidir si abrimos una mini-fase de `city watch` sobre `Shanghai + Chicago (+Seoul)` o una revisión de bloqueo para `Ankara`.

**Sesión 103 (8 abr 2026, Codex):** fase 3 completada: las referencias reales de traders ya están cruzadas contra la `city policy` del bot y contra el snapshot actual de mercados, dejando una shortlist operativa de ciudades puente y traders prioritarios sin tocar todavía el core.
- **Nueva herramienta de cruce operativo:** se crea `tools/reference_trader_city_market_cross.py` con `docs/reference-trader-city-market-cross.md`. Lee `directional_trader_enrichment.json`, `settlement_fidelity_probe.json` y la policy local (`ACTIVE/CANARY/BLOCKED/OBSERVED`) para ordenar ciudades y traders por relevancia práctica.
- **Ciudad puente más fuerte encontrada:** `Shanghai` emerge como la mejor ciudad de continuidad entre research y operativa: `policy=shadow`, `priority_score=14`, `4` referencias reales (`Academic-Maniac`, `Entire-Hood`, `Motionless-Stalk`, `White-Donkey`) y además `2` mercados visibles en el probe actual. Es la mejor candidata para observabilidad reforzada o futuros tests controlados sin saltar todavía al core.
- **Mismatch estratégico explicitado:** `Ankara` sale muy alto (`priority_score=12`, `4` high-priority references) pero sigue `blocked`, lo que obliga a tratarla como caso de research/policy y no como candidata inmediata de trading. `Chicago` aparece como la única ciudad `active` tocada por referencias fuertes (`Academic-Maniac`, `Motionless-Stalk`), aunque no estuvo en el snapshot actual del probe; esto la convierte en la principal ciudad activa a vigilar en el siguiente bloque. También emergen ciudades `untracked` con señal repetida (`Austin`, `Wuhan`) que hoy no forman parte explícita del marco operativo del bot.

**Sesión 102 (8 abr 2026, Codex):** fase 2.5 del plan operativo completada: la shortlist comparable del censo direccional ya está enriquecida con `closed positions`, `win rate` y `cash PnL`, de modo que dejamos de tener solo actividad observable y pasamos a una primera capa de referencias reales.
- **Nueva herramienta de enrichment separada del pipeline legacy:** se crea `tools/directional_trader_enrichment.py` con `docs/directional-trader-enrichment.md`. Toma `data/directional_trader_census.json` como input, consulta posiciones activas/cerradas vía endpoints públicos y produce `data/directional_trader_enrichment.json` + `docs/directional_trader_enrichment_latest.md`.
- **Primera shortlist priorizada ya disponible:** la primera corrida útil sobre `top 5` traders comparables clasifica `4` como `high_priority_reference` y `1` como `candidate_reference`. Ranking inicial: `Entire-Hood` (`WR 81.0`, `PnL 615.88`, `8` cierres direccionales), `Academic-Maniac` (`76.0`, `326.68`, `22`), `Motionless-Stalk` (`66.3`, `53.35`, `14`), `Massive-Distribution` (`79.0`, `41.3`, `11`) y `White-Donkey` como candidato (`52.5`, `195.21`, `19`).
- **Hallazgo estratégico nuevo:** la shortlist comparable ya no es solo “quién está activo”; ahora tenemos evidencia de que varios de esos traders también ganan dinero históricamente en weather/direccional. Además, sus focos dominantes siguen apareciendo más en `Shanghai / Ankara / Wuhan` que en el núcleo operativo actual del bot, mientras que en posiciones activas sí emergen ciudades como `Chicago`, `Austin`, `Denver` o `Wuhan`. Esto empuja la siguiente fase hacia cruce de referencias con ciudades/markets y no todavía hacia cambios directos en el core.

**Sesión 101 (8 abr 2026, Codex):** ejecución real de las dos primeras fases del plan de monetización incremental: `Settlement Fidelity Probe v1` corregido y `Directional Trader Census v1` ya con una primera shortlist comparable al rango operativo del bot.
- **Settlement probe ya produce snapshot útil:** `tools/settlement_fidelity_probe.py` se ejecuta con red real y genera `data/settlement_fidelity_probe.json` + `docs/settlement_fidelity_probe_latest.md`. Se detecta y corrige un bug del request a Open-Meteo (`forecast_days` provocaba `400 Bad Request`); tras el fix, la cobertura de forecast pasa a `12/12`. La primera muestra cae en mercados del día y por eso `NOAA observado` sigue `0/12`, pero la herramienta queda validada como base de observabilidad de fase 1.
- **Directional census separado del pipeline legacy:** se crea `tools/directional_trader_census.py` y `docs/directional-trader-census.md` para perfilar solo wallets activas en `at_or_above/at_or_below`, sin mezclar `exact/range`. La primera corrida bruta (`20` mercados, `1605` BUYs, `719` wallets, `79` traders filtrados) queda dominada por compras a precio extremo cerca de `1.0`, lo que revela que el universo direccional bruto no es comparable al bot.
- **Shortlist comparable ya visible tras alinear el precio al bot:** se corrige el cálculo de `avg_price` y se filtra el censo al rango `0.20-0.80`. El universo comparable se reduce a `10` traders (`1642` BUYs brutos, `747` wallets crudas), casi todos con precio medio `0.30-0.60` y patrón `directional_forecast_candidate`. Los nombres más repetidos son `White-Donkey`, `Entire-Hood`, `Motionless-Stalk` y `Academic-Maniac`. Hallazgo importante: esta shortlist se concentra sobre todo en `Shanghai`, `Ankara` y `Wuhan`, no en las ciudades hoy más centrales para nuestra policy operativa local.

**Sesión 100 (8 abr 2026, Codex):** arranque de la fase operativa posterior al cruce Codex + Opus, dejando un plan ejecutable por fases y la primera herramienta read-only para medir settlement fidelity sin tocar el core del bot.
- **Plan maestro persistido en el repo:** se crea `docs/strategic-monetization-plan-2026-04-08.md` para fijar el orden de trabajo: (1) `Settlement Fidelity Probe v1`, (2) `Directional Trader Census v1`, (3) gate de decisión antes de cualquier cambio funcional. El documento deja handoff explícito para que Claude pueda retomar la fase pendiente sin reinterpretar el objetivo.
- **Fase 1 implementada como herramienta independiente:** se añade `tools/settlement_fidelity_probe.py`, un scanner read-only de mercados direccionales activos que junta precio implícito, forecast `Open-Meteo`, metadata de resolución (`RESOLUTION_ICAO` / `wu_url`) y proxy observado NOAA cuando la fecha ya está resuelta. Las salidas previstas quedan separadas del runtime del bot: `data/settlement_fidelity_probe.json` y `docs/settlement_fidelity_probe_latest.md`.
- **Runbook de uso y límites explícitos:** se crea `docs/settlement-fidelity-probe.md` para documentar objetivo, comandos, interpretación y limitaciones honestas. Queda fijado que esta v1 todavía no automatiza `Weather Underground forecast`; su función es medir cobertura, gaps `Open-Meteo vs NOAA observado` y huecos de observabilidad antes de decidir si la siguiente mejora debe ir por settlement/source gap o por censo de traders direccionales.

**Sesión 99 (8 abr 2026, Codex):** estudio estratégico completo sobre traders comparables al universo de `polymarket-bot`, dejando una base explícita para futura investigación paralela con Opus y cruce posterior de conclusiones.
- **Nuevo artefacto de research auditable:** se crea `RESEARCH_CODEX_TRADERS_2026-04-08.md` con una taxonomía de traders relevantes para weather/prediction markets, comparación explícita contra la estrategia vigente del bot, hipótesis priorizadas de mejora y propuesta de siguiente experimento.
- **Hallazgo interno clave:** el pipeline histórico de traders del repo (`find_traders.py` + `trader_analyzer.py` + `signals.json`) sigue observando sobre todo mercados `exact` y `range`, mientras que la estrategia vigente solo monetiza `at_or_above` y `at_or_below`; por tanto, la base actual de “traders seguidos” no representa todavía bien el universo operable del bot.
- **Dirección estratégica resultante:** antes de tocar forecast core o execution, la siguiente línea de research recomendada es reconstruir el mapa de traders realmente comparables al bot actual y separar mejor selección de mercados, estructura multi-strike, microestructura y wallet-intelligence.

**Sesión 98 (8 abr 2026, Codex):** consolidación documental de la operativa vigente para preparar la investigación comparativa de traders y estrategias ganadoras.
- **Nueva fuente única para comparar estrategia:** se crea `docs/ESTRATEGIA_OPERATIVA.md` como documento canónico y compacto de la operativa actual. Resume qué mercados operamos, qué condiciones permitimos, qué filtros pasan antes de comprar, cómo calculamos probabilidad/edge, cómo dimensionamos con `Half-Kelly`, qué significan `active/canary/shadow/blocked`, y cómo se separan `Open-Meteo`, `NOAA` y `Weather Underground`.
- **Objetivo del documento:** dejar una base explícita y comparable para futuras sesiones de research sobre otros traders, evitando reconstruir la estrategia desde `bot.py`, `CONTEXTO.md` y notas dispersas.
- **Semántica alineada con el repo:** el documento no cambia la lógica; solo fija en lenguaje humano la estrategia real vigente en código y enlaza mejor la capa operativa con la capa de aprendizaje/observabilidad.

**Sesión 97 (8 abr 2026, Codex):** validación live post-ciclo del rediseño `WR observado direccional`, alineación semántica de Telegram y contrato explícito de fuentes del sistema.
- **Validación live cerrada con evidencia:** tras los ciclos `2026-04-07 23:00 UTC` y `2026-04-08 08:00 UTC`, Railway confirmó que `shadow_city_tracking.json` ya usa el esquema nuevo (`directional_history` existe y `recent_opportunities` persiste `edge_hit`), pero la base persistente sigue vacía en live (`directional_history=[]`). El ciclo `08:00 UTC` reescribió el volume, abrió BUYs reales en `Shanghai` y `Seoul`, y aun así mantuvo `scan.shadow=0`; por tanto el `0/72` del dashboard no representa un WR real observado, sino un estado transitorio donde el agregado histórico de `edge_hits` todavía no se materializó como señales persistidas/resolubles.
- **Causa operativa aclarada:** el ciclo `08:00 UTC` tuvo `17` candidatos, `2` con edge, `2` BUYs reales, `0` shadow y `15` `condition_filtered`; no hubo señales shadow direccionales nuevas que pudieran poblar `directional_history`. La tarjeta `Road to Real` ya lee la base correcta, pero hoy sigue midiendo una capa aún vacía en datos live.
- **Telegram alineado a la operativa real:** `bot.py` pasa a distinguir `ACTIVE` vs `CANARY` en compras, renombra `Mercados escaneados` a `Candidatos evaluados`, aclara `Shadow con edge`, arregla el resumen diario para reflejar `active + canary` en vez de solo la allowlist manual, y corrige `/detalle` para separar `condition_filtered`, `shadow con edge` y `duplicados/protecciones`. `/accuracy` prioriza una vista `NOAA-verificado / policy` para ciudades operables y deja el histórico total como contexto separado.
- **Contrato de fuentes explicitado en docs y copy:** queda fijado el esquema canónico del sistema: **Open-Meteo decide**, **NOAA mide**, **Weather Underground resuelve**. `cmd_info`, `OBSERVABILIDAD_Y_APRENDIZAJE.md` y `docs/SISTEMA_MEJORA_CONTINUA.md` ya dejan explícito qué usa cada capa (forecast operativo, observabilidad observada y settlement final) para reducir deriva semántica al iterar sobre learning loops, métricas y futuras investigaciones de traders.
- **Validación local previa al cierre:** `python verify_before_deploy.py` vuelve a cerrar en **643/643** tras los cambios de Telegram/docs.

**Sesión 96 (7 abr 2026, Codex):** hotfix del crash live del dashboard tras el deploy del `WR observado direccional`.
- **Incidente confirmado en Railway:** el endpoint `/` caía con `NameError: name 'recent_opps' is not defined` dentro de `build_dashboard_road_to_real()` al renderizar la tarjeta `Road to Real`.
- **Causa raíz:** el refactor hacia base persistente dejó `Road to Real` iterando `recent_opps` sin volver a inicializar esa variable dentro de la función. El resto de la lógica y los datos persistentes seguían correctos; el fallo era un remanente local del builder del dashboard.
- **Hotfix aplicado:** `build_dashboard_road_to_real()` vuelve a leer `shadow_tracking["directional_history"]` antes del join shadow→NOAA, con lo que recupera el cálculo del `WR observado direccional` y deja de romper la home del dashboard.
- **Regresión añadida:** `verify_before_deploy.py` incorpora un test funcional específico para garantizar que `build_dashboard_road_to_real()` consume `directional_history` sin lanzar `NameError`.
- **Validación local:** `python verify_before_deploy.py` cierra en **643/643**.

**Sesión 95 (7 abr 2026, Codex):** deploy a Railway del rediseño del `WR observado direccional` y registro explícito del seguimiento post-ciclo para no perder el hilo al cerrar sesión.
- **Deploy completado:** el commit `57be884` (`ops: persist shadow observed win-rate basis`) quedó en `origin/main` y Railway arrancó una instancia nueva a `2026-04-07 10:56:26 UTC`.
- **Código live confirmado:** `/app/bot.py` ya contiene `directional_history`, así que la lógica nueva de base persistente para señales shadow resolubles está desplegada.
- **Estado live aún transitorio:** `/app/data/shadow_city_tracking.json` seguía con esquema viejo justo tras el deploy porque todavía no había corrido un ciclo nuevo que reescribiera el volume con la versión nueva.
- **Checklist post-ciclo pendiente:** en la próxima revisión live, validar que `shadow_city_tracking.json` ya incluya `directional_history`, que `recent_opportunities` persista `edge_hit`, y que el dashboard/estado derivado deje de depender de una base reciente volátil para el `WR observado direccional`.
- **Lectura operativa recomendada:** hasta que pase ese ciclo, el deploy debe considerarse correcto pero pendiente de validación de datos escritos; la siguiente comprobación útil es post-ciclo, no inmediatamente tras el restart.

**Sesión 94 (7 abr 2026, Codex):** auditoría y rediseño del `WR observado direccional` para dejar de depender de una ventana shadow volátil.
- **Causa raíz confirmada con evidencia de código:** el check `WR observado direccional >= 45%` y la alerta asociada leían `shadow_tracking.recent_opportunities`, una lista recortada/perecedera pensada para UI reciente, no para resolución tardía con NOAA. Además `record_shadow_city_opportunities()` persistía esas filas sin `edge_hit`, de modo que `save_shadow_city_tracking()` las re-clasificaba como no direccionales al guardar y el join quedaba sesgado hacia `0/N`.
- **Base persistente nueva para shadow observado:** `shadow_city_tracking.json` gana `directional_history`, un registro estable de señales shadow direccionales deduplicadas por firma (`city|date|side|condition|threshold`). Esta capa conserva `first_seen_at/last_seen_at/times_seen`, mantiene `recent_opportunities` solo como ventana de UI, y permite resolver señales cuando NOAA llegue con lag sin tocar trading core.
- **Join endurecido:** el cálculo del dashboard y de alertas ya no depende de la lista reciente volátil; usa `directional_history` y normaliza `date` a `YYYY-MM-DD` tanto del lado shadow como del lado `observed_vs_forecast`, tolerando datetimes ISO del audit.
- **Legibilidad operativa mantenida:** la métrica sigue leyendo `WR observado direccional`, pero ahora representa señales shadow persistidas y resolubles, no solo las todavía visibles en la cola reciente. `verify_before_deploy.py` añade regresiones para `edge_hit` persistido, `directional_history` y join NOAA con fecha datetime.
- **Validación local:** `python verify_before_deploy.py` cierra en **642/642**.

**Sesión 93 (7 abr 2026, Codex):** cierre operativo de deploy con Railway relogin, restart live y limpieza de alertas legacy en observabilidad.
- **Incidente Railway confirmado como recurrente:** `tools/railway_auth_repair.ps1 doctor` volvió a mostrar el patrón de siempre: `accessToken` y `refreshToken` presentes, `Writable from this process=True`, `secondsToExpiry>0`, sin proxies persistentes ni de proceso, pero `Auth check via clean env` devolviendo `Unauthorized`. El recovery `reset + launch-login -Browserless` restauró `whoami/status`.
- **Estado live validado:** tras `git push origin main` del commit `bb208fb`, la comprobación live inicial no mostraba arranque nuevo. Se forzó `restart --yes`, el CLI quedó colgado con mutex ocupado, se detectaron procesos `railway/node` atascados y se limpiaron. La evidencia final en logs muestra un nuevo arranque del servicio `polymarket-bot` a `2026-04-07 10:10:07 UTC`.
- **Alerta legacy retirada de observabilidad:** `run_observability_alerts()` deja de disparar `Ciudad con baja accuracy` basada en histórico agregado/legacy y pasa a emitir solo revisión `NOAA-verificado` para ciudades `active/canary` con suficiente muestra verificada. Se evita así recomendar `BLOCKED_CITIES` por métricas pre-NOAA.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639**.

**Sesión 92 (7 abr 2026, Codex):** afinado final de umbrales del dashboard para reducir ruido en la fase NOAA-verificada temprana, sin tocar trading core, NOAA fetch core ni scheduler.
- **Umbrales explícitos de alertas:** `bot.py` añade `ALERT_VERIFIED_BAD_MIN_TRADES`, `ALERT_VERIFIED_BAD_MAX_WIN_RATE`, `ALERT_ACTIVE_NOAA_MIN_CASES`, `ALERT_SHADOW_JOIN_MIN_SIGNALS`, `ALERT_SHADOW_JOIN_MIN_NOAA_SAMPLE`, `ALERT_SHADOW_WR_MIN_RESOLVED` y `ALERT_SHADOW_WR_TARGET` para que `Alertas activas` ya no dependa de números mágicos enterrados en `get_dashboard_alert_summary()`.
- **Defaults más prudentes para esta fase:** por defecto una ciudad `NOAA-verificado malo` exige `n>=5`; la alerta de activas sin NOAA interpretable solo aparece si la ciudad sigue por debajo de `3` casos observados; `Shadow sin join NOAA útil` exige `>=20` señales shadow y `>=10` observaciones NOAA globales; y el `WR shadow observado` no se alerta hasta `n>=8` resueltas.
- **Objetivo operativo:** mantener visibilidad sobre cuellos de botella reales de la era NOAA-verificada sin sobrerreaccionar a muestras todavía pequeñas o transitorias.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639**.

**Sesión 91 (7 abr 2026, Codex):** actualización de alertas del dashboard hacia métricas NOAA-verificadas y cuellos de botella reales, sin tocar trading core, NOAA fetch core ni scheduler.
- **Alertas activas reinterpretadas:** `get_dashboard_alert_summary()` deja de usar `Ciudades con accuracy baja` como señal operativa principal y pasa a priorizar `Ciudades con NOAA-verificado malo`, `Ciudades activas sin NOAA interpretable`, `Shadow sin join NOAA util` o `WR shadow observado por debajo de objetivo`, además de las alertas ya existentes de `signals`, `pending exits` y `bankroll`.
- **Legacy separado del presente:** la antigua capa de ciudades con WR histórico malo sigue disponible como `legacy_flagged_cities` y `flagged_history_note`, pero ya no manda sobre `active_items`. El histórico legacy queda como contexto congelado, no como alarma operativa de primer nivel.
- **Focus center alineado:** `build_dashboard_focus_center()` cambia el lenguaje de `accuracy baja` a `NOAA-verificado` cuando usa `flagged_cities` para explicar el limitador dominante o la acción del día.
- **Compatibilidad con el harness:** `get_dashboard_alert_summary()` añade fallbacks cuando los tests funcionales ejecutan el builder en un namespace parcial sin ciertos helpers/constantes cargados.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639**.

**Sesión 90 (7 abr 2026, Codex):** pasada de legibilidad del dashboard para lectura humana + LLM, sin tocar trading core, NOAA fetch core ni scheduler.
- **Estado por ciudad agrupado:** `build_dashboard_city_decisions()` expone ahora `grouped_sections` con cuatro zonas explícitas: `Operativas y candidatas`, `Shadow observadas`, `Sin NOAA util` y `Fuera de observacion`.
- **HTML más escaneable:** `templates/dashboard.html` deja de mostrar una tabla monolítica única para `Estado por ciudad` y renderiza una tabla por grupo, cada una con conteo y nota corta. Cada fila añade además `main_reason` visible bajo el nombre de la ciudad para que un operador o un LLM pueda leer la causa principal sin inferirla.
- **CSS de soporte:** `static/dashboard.css` añade `city-groups`, `city-group-card`, `city-group-head` y `city-group-note` para que el bloque siga siendo legible sin romper el look actual.
- **Objetivo cumplido:** el dashboard ya separa mejor contexto operativo, observación activa, ciudades sin NOAA útil y bloqueos reales, reduciendo mezcla semántica en una sola tabla.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639**.

**Sesión 89 (7 abr 2026, Codex):** limpieza final de semántica `blocked` + separación actual/histórico en dashboard, sin tocar trading core, NOAA fetch core ni scheduler.
- **Blocked vuelve a significar “no observar”:** `is_city_blocked()` solo bloquea operativamente si la ciudad está en `BLOCKED_CITIES` **y** no tiene NOAA utilizable (`noaa_station_id`/`noaa_daily_station_id` o entrada explícita en `OBSERVED_AUDIT_CITIES`). Ciudades con NOAA configurable pero descartadas en listas viejas dejan de quedar fuera del scan/observación y vuelven a `shadow`.
- **Overlays legacy neutralizados:** `get_effective_city_mode()` ya no trata `auto_blocked_cities` como bloqueo duro cuando la ciudad sí puede observarse con NOAA; en esos casos la resuelve como `shadow`. El bloqueo efectivo queda reservado a casos sin observabilidad NOAA.
- **Dashboard alineado con la nueva semántica:** `build_dashboard_city_observation()` deja de presentar como “bloqueadas” ciudades con NOAA configurado, actualiza el detalle textual de bloqueo a “sin NOAA configurado”, y `build_dashboard_city_decisions()` filtra `auto_state.blocked_rows` por bloqueo efectivo real.
- **Lectura actual vs legado visible:** el bloque `Rendimiento por ciudad` ya separa `Rendimiento NOAA-verificado` de `Legado pre-NOAA`, para que la operativa nueva no quede mezclada con la era previa.
- **UX:** el Bloque 3 (`Salud del sistema`) recuerda su estado abierto/cerrado entre auto-refreshes del dashboard.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639**.

**Sesión 88 (7 abr 2026, Codex):** mitigación operativa del proveedor forecast, sin tocar trading core, NOAA fetch core ni scheduler.
- **Hallazgo live:** los ciclos estaban sufriendo `timeout`, `429 Too Many Requests` y `502` al consultar Open-Meteo; además el mismo ciclo reutilizaba `get_forecast()` desde auditoría legacy y luego desde el escaneo principal, amplificando los hits al proveedor.
- **Hardening HTTP:** `get_forecast()` ahora comparte caché en proceso por `lat/lon`, reutiliza respuestas frescas con TTL, respeta un cooldown explícito al detectar `HTTP 429` y puede caer a cache `stale` acotada cuando el proveedor rate-limita o falla.
- **Impacto esperado:** menos fan-out duplicado dentro del ciclo, menos martilleo tras un `429`, y más probabilidad de que audit + scan sigan operando con una única respuesta reciente en vez de reconsultar la misma ciudad varias veces.
- **Validación local:** `python verify_before_deploy.py` cierra en **639/639** con tests nuevos para cachear la segunda llamada y reutilizar `stale cache` cuando aparece `HTTP 429`.

**Sesión 87 (7 abr 2026, Codex):** hardening puntual del scoreboard live, sin tocar trading core, NOAA fetch core ni scheduler.
- **Fix de compatibilidad live:** `load_agent_events()` ya no falla al leer sesiones serializadas como texto tipo `session_72`; ahora extrae el sufijo numérico, lo normaliza a entero y mantiene la deduplicación por clave estable.
- **Impacto operativo:** desaparece el warning repetido `invalid literal for int() with base 10: 'session_72'` que estaba ensuciando logs y podía dejar cojo el bloque de eventos/agentes del dashboard.
- **Cobertura nueva:** `verify_before_deploy.py` añade un caso funcional con `session="session_72"` y verifica tanto la normalización a `72` como la deduplicación/ordenación de eventos.
- **Validación local:** `python verify_before_deploy.py` cierra en **637/637**.

**Sesión 86 (6 abr 2026, Codex):** reinterpretación del histórico para la policy de ciudades, sin tocar trading core, NOAA fetch core ni scheduler.
- **Nueva capa de policy:** `get_city_policy_metrics()` separa cierres por ciudad en `verified` (join `city+date` contra `observed_vs_forecast` con `source=noaa_ncei`) y `legacy` (sin NOAA-verificado).
- **Degradación más robusta:** `build_dashboard_city_decisions()` ya no degrada `active/canary -> shadow` usando histórico agregado bruto. La regla `remove` ahora exige trades **NOAA-verificados**; si solo hay histórico legacy malo, la policy queda `provisional` y la ciudad se mantiene/observa en vez de oscilar por una era observacional antigua.
- **Promoción/lectura alineadas:** `build_dashboard_city_observation()` expone `policy_source`, `policy_is_provisional`, `verified_trades` y `legacy_trades`; el soporte para `shadow -> canary` vuelve a usar `trades` totales como soporte para no penalizar ciudades con trayectoria previa, pero la degradación sigue exigiendo evidencia NOAA-verificada.
- **Review manual visible:** las ciudades activas con histórico legacy muy malo pero aún sin base NOAA suficiente ya no quedan “operando limpias”; pasan a `Revisar legado / Bajo review`, con score más conservador y sin autodegradación.
- **Hardening técnico:** el join `city+date` normaliza fechas a `YYYY-MM-DD` y `sync_city_policy_state()`, alertas canary, snapshot y focus reutilizan `city_policy_metrics` para evitar recálculo triple.
- **Persistencia de evidencia:** `_build_auto_city_shadow_policy()` guarda también el basis de policy (`policy_source`, `policy_trades`, `verified_trades`, `legacy_trades`) cuando una ciudad sí se degrada a shadow.
- **Validación local:** `python verify_before_deploy.py` cierra en **632/632** con tests nuevos para separar NOAA-verificado vs legacy, normalizar fechas y evitar degradación automática por histórico legacy malo.

**Sesión 85 (6 abr 2026, Codex):** limpieza semántica de la política `blocked/shadow/canary/active`, sin tocar trading core, NOAA fetch core ni scheduler.
- **Cambio canónico local:** `sync_city_policy_state()` ya no degrada `active/canary -> blocked`; ahora degrada `active/canary -> shadow` con evidencia persistida en `auto_shadow_cities`. `blocked` queda reservado a descartes reales.
- **Migración de legado:** `load_city_policy_state()/save_city_policy_state()/get_effective_city_mode()` normalizan overlays viejos `auto_blocked_cities[action=auto_block]` a `auto_shadow_cities`. Caso principal cubierto: Dallas deja de quedar atrapada como `blocked` por overlay legacy aunque siga en `ACTIVE_TRADING_CITIES`.
- **Dashboard/copy alineado:** Gate NOAA distingue `Interpretable`, `Parcial`, `Sin muestra` y `Sin NOAA`; `blocked` se verbaliza como descarte real; `shadow` y `shadow degradada` quedan como observación activa.
- **Validación local:** `python verify_before_deploy.py` cierra en **628/628**.
- **Importante:** esta sesión no muta Railway por sí sola; si en live sigue existiendo `city_policy_state.json` viejo, el código nuevo lo migrará a shadow al cargar/guardar la política.

**Sesión 82 (6 abr 2026, Claude + Codex en paralelo):** diagnóstico estratégico completo, validación empírica WU≈NOAA, corrección de sesgo del modelo y reactivación del bot.
- **Hallazgo clave — WU = NOAA:** verificación manual de 3 fechas en Chicago (KORD): NOAA `daily-summaries/TMAX` es idéntico al daily high de Weather Underground (diferencia ≤1°F por redondeo). No se necesita scraping de WU. La capa NOAA ya existente es la fuente correcta de validación.
- **Sesgo Open-Meteo confirmado con NOAA:** `observed_vs_forecast` (13 casos en producción): Atlanta `MAE=1.38°C, Bias=+1.38°C`; Chicago `MAE=2.48°C, Bias=+1.40°C`; Dallas `MAE=0.57°C, Bias≈0°C`. Open-Meteo subestima sistemáticamente en Atlanta/Chicago; Dallas está bien calibrado.
- **Corrección de modelo implementada (`FORECAST_BIAS_C`):** nuevo dict en `bot.py` con `Atlanta: +1.38, Chicago: +1.40, Dallas: 0.0`. Aplicado en `estimate_prob_with_city` como `mu = forecast_max + bias` antes del cálculo de probabilidad. Dallas `EMPIRICAL_SIGMA D0` actualizado `0.21→0.57°C`, `samples D0` `2→3` (desbloquea sigma empírica NOAA). Commits `93c8b2e` + `1daec87`. `verify_before_deploy.py` cierra en **620/620** (8 tests nuevos de bias + sigma).
- **Filtros de precio endurecidos:** `MIN_PRICE 0.08→0.20`, `MAX_PRICE 0.92→0.80`. Evita entradas en mercados de probabilidad extrema donde el modelo tiene baja resolución y el sesgo relativo es mayor.
- **Bot reactivado en Railway:** `ACTIVE_TRADING_CITIES=Dallas` (estaba en `NONE` desde shadow mode). `auto_blocked_cities` limpio (Chicago/Dallas/NYC estaban bloqueadas). Bankroll disponible: `$9.21`.
- **NOAA decoupling (Codex):** `_iter_recent_noaa_cycle_markets()` + `_get_noaa_candidate_dates()` añadidos. El audit NOAA ahora recoge observaciones para mercados escaneados aunque no haya `BUY` asociado, usando `scanned_markets` guardado en `cycle_summary`/`cycles_history`. Acelera la acumulación de muestra ~3-4x sin depender de trades. Los cambios de Codex viajaron junto al commit `1daec87` al estar en el worktree compartido.
- **Próximo hito:** con `n≥10` Dallas en `observed_vs_forecast`, recalcular bias/sigma y evaluar si Buenos Aires puede ser la segunda ciudad activa.

**Sesión 81 (6 abr 2026, Codex):** simplificación operativa del Control Center integrada y publicada en `main`, sin bump de versión.
- Se mergearon en cadena 7 PRs aisladas del plan `docs/control-center-simplify-plan.md`: badge de modo sin falsa alarma en shadow/dry, eliminación de la columna `Resolucion` en señales shadow, normalización de `forecast_display` con fallback semántico, supresión de la alerta operativa `city_low_accuracy` en `SHADOW_ONLY/DRY_RUN` moviéndola a nota fija de rendimiento, limpieza de duplicados en dashboard, lenguaje llano en scan/condición y gateo NOAA con mensaje de muestra insuficiente.
- `bot.py` resolvió el conflicto textual entre PRs manteniendo ambos helpers (`_shadow_condition_label`, `_extract_threshold_display_from_question`) y combinando correctamente `_strip_resolution_fields(...)`, `_build_shadow_forecast_fields(...)` y `condition_label` en `build_dashboard_city_decisions`.
- `verify_before_deploy.py` quedó saneado para el estado actual de `main`: actualiza asserts del dashboard simplificado, inyecta `_dashboard_mode_label` en el harness funcional y hace la prueba R3 de rotación robusta al sandbox Windows usando tempdir local del repo y monkeypatch de `os.replace`.
- Validación final sobre `main`: `python verify_before_deploy.py` cerró en **612/612**. Push realizado a `origin/main` en commit `df4ff60` (`test(verify): harden merged dashboard checks`).

**Sesión 80 (5 abr 2026, Claude + Codex en paralelo):** R3 (log de skips por ciclo) implementado, testeado y validado end-to-end.
- Claude (Opus): `bot.py` añade `_make_skip_entry`, `append_skip_log_entries` (batch al final del ciclo + rotación 20 MB), `read_skip_log_last_n_cycles`, `read_skip_log_since`. Scan loop (`run_cycle`) instrumentado con `skip_log_entries = []` como bucket local y 17 `skip_reason` distintos: `parse_fail`, `blocked_city`, `fuera_allowlist`, `shadow_only_override`, `timezone_filter`, `date_out_of_range_past`, `date_out_of_range_future`, `price_out_of_range`, `liquidity_low`, `forecast_missing`, `condition_filtered`, `no_edge`, `below_min_edge`, `kelly_too_low`, `existing_order`, `sold_this_cycle`, `existing_position`. `shadow_override_flag` propagado desde Loop A para distinguir `fuera_allowlist` vs `shadow_only_override` en Loop B. `cycle_id` determinista `YYYY-MM-DDTHH:MM` UTC capturado una sola vez.
- Codex: `tools/analyze_skip_log.py` analyzer offline con flags `--last-n-cycles`, `--since`, `--city`, `--csv`, `--min-edge`. Lee `data/skip_log.jsonl` + rotados directo con `json.loads(line)`, sin importar `bot.py`. Renderiza 3 secciones: distribución por ciudad, trend temporal, near-misses. `docs/skip-log-analyzer.md` con guía de uso.
- `verify_before_deploy.py` cierra en `612/612` (64 tests R3 nuevos: estáticos + funcionales con `exec` en namespace limpio cubriendo `_make_skip_entry`, writer, readers, fail-fast, rotación, tolerancia a líneas malformadas, tolerancia a I/O roto).
- Commits pusheados a `main`: `096a680` (contrato), `4b37cfe` (analyzer Codex), backend R3 (Claude).
- Validación producción: Pablo forzó ciclo vía `/forzar` en Telegram tras deploy automático Railway. `data/skip_log.jsonl` generó **660 filas** en el primer ciclo real (`cycle_id 2026-04-05T20:09`). Analyzer corrido por SSH contra Railway funciona.
- **Hallazgo estratégico del primer ciclo:** cero filas llegan a Loop B con edge calculado — todos los skips son Loop A. Significa que `below_min_edge`/`kelly_too_low`/`shadow_only_override` (casos ricos para sigma recalibration) solo aparecerán cuando haya mercados futuros válidos en ciudades activas. R3 listo para análisis longitudinal cuando entren nuevos mercados.
- Distribución primer ciclo: `blocked_city` 100% para London/Chicago/Dallas/Paris/Madrid/NYC/Miami/Seattle/Toronto/Tel Aviv/Ankara/Atlanta; `date_out_of_range_past` 100% para Amsterdam/Austin/BuenosAires/Chongqing/HongKong/LA/Milan/Moscow/Munich/SaoPaulo/Shenzhen/Warsaw; Shanghai/Chengdu/Seoul con mix `price_out_of_range` + `condition_filtered`.

**Sesión 79 (5 abr 2026, Codex):** R1 frontend del Control Center cerrado sobre contrato estable con backend paralelo de Claude.
- `templates/dashboard.html` reemplaza el bloque compacto que iteraba `dashboard.city_observation.active_rows` por una tabla de `dashboard.city_decisions.ranking_rows` con 3 gates visibles por ciudad: `Historial`, `Shadow` y `NOAA`, usando `gate_a`, `gate_b` y `gate_c` como autoridad del JSON.
- Debajo de la tabla se añade un glosario corto de estados y `static/dashboard.css` gana una clase mínima `.city-gates` para ajustar el layout, reutilizando `badge-good/accent/warn/bad/muted` existentes.
- Se mantiene intacto el bloque posterior de `blocked_rows`; no se toca `bot.py`, `verify_before_deploy.py` ni se hace bump de versión.
- Validación local: `python verify_before_deploy.py` cierra en `548/548`. Commit/push realizado a `main`: `c382000` (`feat(dashboard): R1 frontend — 3 gates visuales por ciudad`).
**Sesión 78 (5 abr 2026, Claude):** M2, M4 y M5 del control-center roadmap completados en una sesión.
- M2: verificado por SSH Railway que `shadow_city_tracking.json` y `city_policy_state.json` persisten en el Volume `/app/data` entre deploys. Nombre real del archivo shadow corregido en roadmap y añadido a la tabla de "Datos persistentes".
- M4: `build_daily_summary_payload()`, `format_daily_summary_text()`, `maybe_send_daily_summary_telegram(state)` en `bot.py`. Hook desde `run_observability_alerts()` (try/except). One-shot idempotente por fecha UTC, disparado en la ventana `sorted(SCHEDULE_HOURS_UTC)[0]` (08 UTC por defecto). Contenido: ciclos 24h, resoluciones 24h (wins/losses/PnL), NOAA 24h por ciudad + acumulado, versión, modo y próximo ciclo.
- M5: `notify_canary_candidates(state)` en `bot.py`. Self-contained, se invoca desde `run_observability_alerts()` antes de `sync_city_policy_state` (try/except). Fires one-shot por ciudad cuando `row.decision == "promote"` usando `state["canary_candidate_notified"]`; limpia la entrada cuando la ciudad deja de ser candidata para permitir re-disparo tras regresión. NO toca la lógica de auto-promote — es observabilidad paralela con evidencia rica (shadow_edges, best_edge, soporte, NOAA count).
- Versión bumpeada a **v10.6.11**. `verify_before_deploy.py` cierra en `534/534` (21 tests nuevos cubriendo M4 + M5: gating, idempotencia, agregaciones 24h y lifecycle del flag canary candidate).
- Pendiente operativo: push + deploy Railway (el usuario decide cuándo); validar en live que el resumen diario cae el primer ciclo 08 UTC y que la alerta canary candidate no se dispara accidentalmente por la shadow tracking actual.
**M3 COMPLETADA (sesión 72, auditada sesión 74):** Las 3 filas legacy Chicago `2026-03-26/27/28` ya están `closed/LOSS_TOTAL/legacy_unresolved` en producción. Chicago accuracy real: `trades=8, wins=1, WR=12.5%, PnL=-$7.85`. Hay una fila sin fecha (take_profit, la única win) — dato menor.
**M1 COMPLETADA (sesión 74, Codex):** Mega-card Observabilidad dividida en 3 tabs: `NOAA | Ciudades | Decisiones` en `templates/dashboard.html`. Usa patrón existente `data-tab-shell`. DOM order: NOAA → Ciudades → Decisiones. 507/507 OK.
**ALERTA ESTRATÉGICA — próxima sesión con Opus:** WR últimos 15 trades pasó de 53% (16:00 UTC 3 abr) a 27% (23:00 UTC 3 abr) en 7 horas. Revisar trades del ciclo 23:00 UTC, lógica de entrada y sigma. M4 y R1 quedan desbloqueados para Fase 2 CC.
**Fase 1 forecast accuracy audit (sesión 75, Codex):** se añade `tools/forecast_accuracy_audit.py`, `docs/forecast_accuracy_audit.md` y `data/forecast_accuracy_raw.json` sin tocar `bot.py` ni variables Railway. Resultado crítico para Opus: sobre `34` cierres con BUY context recuperable, `real_edge < 0` en `23.5%`, `11.8%` no pasarían `MIN_EDGE` con sigma empírica, sesgo de lado `YES=61.8% / NO=38.2%`, y Chicago muestra `sigma_empirica` muy por encima del modelo (`3.074 °C` global ciudad; `2.573-2.587 °C` en days_ahead 0-1 vs `1.2-1.5`). Limitación explícita: `82` cierres legacy/orphan de `postmortem.json` no traen `forecast_max/question/date` y quedan omitidos, así que esta tabla no representa aún los `91` cierres de serie v10.6 completos.
**Camino A implementado localmente (sesión 76, Codex):** `bot.py` pasa a operar solo condiciones direccionales por default (`ALLOWED_CONDITIONS=at_or_above,at_or_below`), filtra `range/exact` antes de `estimate_prob`, las registra en `shadow_city_tracking` con `edge_hit=False` y expone `condition_filtered` en `cycle_summary`, Telegram `/log`/`/info` y dashboard. `get_uncertainty(days_ahead, city=None)` ahora usa sigma empírica por ciudad solo si `n>=3`, cae a `EMPIRICAL_SIGMA_GLOBAL` si la muestra es insuficiente y deja la sigma original v10.3 como fallback final; `MIN_EDGE` default sube a `15.0`. `ACTIVE_TRADING_CITIES` Railway no se toca y `verify_before_deploy.py` cierra en `515/515`.
**Rediseño Control Center shadow-only (sesión 77, Codex UI):** `templates/dashboard.html` pasa a una lectura de 3 bloques con barra `Road to Real`, bloque compacto `Estado del bot`, tabla `Señales shadow direccionales` y `<details>` de `Salud del sistema`. Se saca del flujo visible principal Mission HUD, trofeos, desbloqueos, scoreboards, trade console larga y tabla larga de ciclos; el JSON de `/api/dashboard.json` sigue intacto. `static/dashboard.css` añade estilos para `road-to-real`, `cards-3` y `notice-accent`, y `verify_before_deploy.py` incorpora checks de la nueva estructura + stub de `build_dashboard_road_to_real()`. Validación local: `516/516`.
**Workflow CC con Codex:** Codex puede hacer tareas HTML/JS puras (M1, QW7) sin fricción. Evitar darle tareas que requieran Railway o contexto de producción.

**Estado real de la cuenta a cierre de sesión 68 (3 abr 2026, ~17:00 UTC):**
- Cash disponible: $21.62
- Posiciones abiertas: 2 (NYC Apr3 YES x2, PnL neto ~$0.00)
- Pendiente cobro (resolved_won): 4 posiciones, ~$3.38
- Ciudades activas Railway: Chicago, Buenos Aires (Dallas degradada a shadow por overlay, Atlanta bloqueada)
- `ACTIVE_TRADING_CITIES` Railway: `Chicago,Dallas,Buenos Aires` (Atlanta retirada sesión 68)
- `BLOCKED_CITIES` Railway: incluye Atlanta (añadida sesión 65)
- **Postmortem Chicago Apr1 reconciliado:** la fila `Chicago|YES|2026-04-01|2026-03-31T23:00:28.735723+00:00` ya aparece `status=closed`, `close_action=LOSS_TOTAL`, `close_reason=micro_position_unsellable`, `closed_at=2026-04-02T07:39:19.807998+00:00`, `pnl_cash=0.0`. Con la lógica actual del bot, `city_accuracy[Chicago] = 4 trades, 1 win, WR 25.0%, PnL +$2.09`; el sesgo pendiente no viene de Apr1 sino de 3 filas Chicago antiguas todavía `open`.

**Hotfix operativo sesión 65 (3 abr 2026):**
- `BLOCKED_CITIES` en Railway quedó actualizado con `Atlanta` añadida.
- `alerts_state.json` live confirma que la alerta de baja accuracy de Atlanta sí se envió una vez el `2026-03-30T21:02:35.447220+00:00`, cuando llevaba `1/4`, `WR 25.0%`, `PnL -1.13`.
- `postmortem.json` live para Atlanta da `23` cierres, `4` wins por `pnl_cash > 0`, `WR 17.4%`, con `SELL=4`, `RESOLVED_WIN=2`, `LOSS_TOTAL=17`, más una entrada antigua abierta `Atlanta|YES|2026-03-28|2026-03-26T08:00:35.955319+00:00`.
- Diagnóstico operativo: el nombre “auto-bloqueo” es engañoso en la implementación actual; la regla solo manda Telegram y añade `city_accuracy_flagged`, pero no modifica `BLOCKED_CITIES`.
- Redeploy confirmado por logs Railway a `2026-04-03 09:16:46 UTC` con `POLYMARKET BOT v10.6.10` arrancando limpio.

**Implementación local sesión 66 (3 abr 2026):**
- El rediseño del auto-bloqueo queda hecho en `city_policy_state.json`: `auto_blocked_cities[city]` persiste `action="auto_block"`, `reason`, `metrics` (`trades`, `wins`, `win_rate`, `pnl`, `observed_count`, `shadow_seen`, `shadow_edges`, `shadow_best_edge`, `support_count`), `from_mode` y `triggered_at`.
- `get_effective_city_mode()` ahora da prioridad a `auto_blocked_cities`, así que una ciudad auto-bloqueada queda en `blocked` aunque siga en `ACTIVE_TRADING_CITIES`; el scan de BUYs ya respeta ese modo sin depender solo de Telegram.
- `sync_city_policy_state()` pasa de degradar `active/canary -> shadow` a registrar `active/canary -> blocked` con evidencia estructurada y sin reactivación automática agresiva; la salida de esa política queda deliberadamente manual/conservadora retirando la entrada persistida.
- `build_dashboard_city_observation()` y `build_dashboard_city_decisions()` ya leen el bloqueo automático persistido y exponen `policy_action`, `policy_reason`, `policy_metrics` y `policy_changed_at`.
- Validación local: `python verify_before_deploy.py` sube a `507/507` tras cubrir en test la alarma de `build_dashboard_focus_center()` cuando falta `cycle_summary.json`.

**Hardening del relogin Railway CLI — sesión 67 (3 abr 2026):**
- Evidencia base de recurrencia: el 3 abr `tools/railway_auth_repair.ps1 doctor` llegó a ver `accessToken present=True`, `refreshToken present=True`, `tokenExpiresAtUtc=2026-04-03T10:03:11Z`, sin proxies persistentes ni de proceso, pero `Auth check via clean env` seguía devolviendo `Unauthorized`; el workaround manual `reset + launch-login -Browserless + railway_safe.ps1 whoami/status` volvió a recuperar la CLI.
- Nueva evidencia de esta sesión: `doctor`, `whoami` y `status` funcionan localmente y el config se refresca a `tokenExpiresAtUtc=2026-04-03T11:07:57Z`; `doctor` además expone `Writable from this process`, `secondsToExpiry` y `refreshWriteRiskSoon`.
- Mitigación implementada en tooling, sin tocar `bot.py`: `tools/railway_safe.ps1` ahora hace preflight del expiry OAuth y corta si el token está a <=5 min de vencer y el proceso no puede abrir `%USERPROFILE%\.railway\config.json` en modo escritura; además serializa todas las invocaciones Railway con un mutex global para evitar carreras de refresh concurrente contra el mismo `refreshToken`. `tools/railway_auth_repair.ps1 doctor/login` usa el mismo mutex y expone la nueva telemetría.
- Causa raíz exacta aún no queda demostrada al 100%: la hipótesis más plausible pasa a ser una mezcla de refresh sin escritura persistida y/o refreshes concurrentes del CLI sobre el mismo config; el mutex + preflight están pensados para cortar ambas rutas antes de volver a caer en `invalid_grant`.

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado direccional está equivocado por más de 15%, apuesta en la dirección correcta.

**Bankroll configurado:** $25.00 en Railway. El 30 mar se depositaron `+$14.99` para volver a la zona objetivo de operación.

**IMPORTANTE — Fuente de resolución:** Polymarket NO usa Open-Meteo — usa Weather Underground (wunderground.com). Esto ha causado pérdidas en London (2 veces). No apostar en London hasta resolver.

---

## Estado financiero (referencia histórica fin sesión 30 — 29 mar 2026)

- **Cartera Polymarket:** ~$18.89 (-$9.52 último día, -50.4%)
- **Disponible para operar:** ~$13.63
- **P&L all-time:** ~-$21.84
- **Causa principal de pérdidas:** Open-Meteo vs Weather Underground discrepancia + sigma ampliada de v10.5 que vendía posiciones ganadoras + intra-cycle monitor que disparaba SL ante fluctuaciones normales
- **Acción tomada:** v10.6.0 revierte lógica de trading a v10.3 (sigma original, sin intra-cycle, sin MIN_EDGE_EXACT)
- **Actualización 30 mar:** depósito manual `+$14.99` para reponer bankroll operativo hacia el objetivo de `$25`.

Para estado exacto: usar `/focus` + `/info` + `/cartera` + `/rendimiento` + `/accuracy` en Telegram.

---

## Qué hace el bot v10.6.10 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas.

**0.5. Gestión activa (manage_positions):** Para cada posición abierta:
- ¿currentValue < $0.10? → LOSS_TOTAL
- ¿curPrice >= 0.98? → SKIP (resuelta, esperando pago)
- ¿redeemable=True? → SKIP (cash garantizado pendiente de claim/redeem; no cuenta como riesgo)
- ¿PnL < -25%? → VENDER (stop-loss)
- ¿PnL > +40%? → VENDER (take-profit)
- Si no: recalcula edge. Si edge < -3% → VENDER (re-evaluación)
- Devuelve `sold_token_ids` para evitar re-entrada en el mismo ciclo

**0.6. Auditoría actual:** Convierte SELL_PENDING → SELL/SELL_FAILED según fills confirmados y mantiene una pseudo-auditoría `forecast_vs_forecast posterior` con Open-Meteo. **No valida contra la fuente real de resolución de Polymarket (Weather Underground).**

**1-5. Buscar oportunidades:** Escanea ~330 mercados, consulta previsiones, calcula edge, cruza con señales de traders, dimensiona con Half-Kelly, respeta exposición máxima 40%.

**6. Ejecución:** Órdenes GTC limit, registra en `performance.json`, sincroniza `postmortem.json` y notifica por Telegram.

**7. Registro de ciclo (v10.4.1+):** Guarda resumen en cycle_summary.json + append en cycles_history.jsonl.

**Al arrancar (v10.4.3+):** Carga ciclos históricos desde `cycles_history.jsonl` (contador total no se reinicia con deploys).

**Contador dual de ciclos (v10.5.4):** Mantiene `cycle_count` como histórico total y añade `cycle_count_series` para la serie lógica actual (`LOGIC_SERIES`). Cada ciclo nuevo guarda `logic_series` y `logic_cycle_number`. `/estado` y `/info` muestran ambos para comparar estrategia nueva sin perder continuidad operativa.

**Bloqueo ciudades perdedoras + fix posiciones fantasma (v10.5.12):** `BLOCKED_CITIES` ampliado a 10 ciudades (London, Miami, Seattle, Paris, Tel Aviv, Wellington, Toronto, Madrid, Singapore, Ankara) tras análisis de accuracy real: todas con 0% WR y pérdidas confirmadas en producción. Solo quedan activas Chicago, Atlanta, Buenos Aires y Dallas. Fix de observabilidad: posiciones con `currentValue < 0.01` ahora se registran también como `LOSS_TOTAL` en vez de ignorarse silenciosamente; antes quedaban en postmortem como "open" para siempre ocultando la pérdida real.

**Fixes dashboard + scorecard (v10.5.11):** Corrección de bug en el checklist del dashboard: el check `Drawdown últimos N cierres` ahora muestra `Esperando muestra` hasta tener `DRAWDOWN_WINDOW` cierres completos (antes mostraba `OK` con solo 1-4 trades, porque `recent_window_size < DRAWDOWN_WINDOW` evaluaba siempre como verdadero). Nuevo helper `_sync_agent_events_seed()` que fusiona la semilla local de `agent_events.jsonl` con el Volume en cada arranque, añadiendo solo los eventos nuevos que no estén ya persistidos; resuelve el problema de que las sesiones 27-28 del scoreboard no aparecían en Railway porque `_seed_data_file()` no sobrescribía un archivo ya existente.

**Dashboard web + scorecard de agentes (v10.5.10):** Levanta un panel HTML separado de Telegram en el mismo servicio Railway, accesible por navegador en `PORT`. Usa modo oscuro, separa checklist histórico vs serie `v10.5`, muestra ciclos legacy con etiquetas legibles, enseña el scoreboard por stages (`proposed / implemented / validated`) a partir de `agent_events.jsonl`, evita mostrar métricas de serie como `0.0%` o `+$0.00` cuando todavía no hay cierres, distingue visualmente entre `fallo real` y `esperando muestra` en el checklist y añade cuatro bloques nuevos: `Progreso`, `Trofeos`, `Desbloqueos` y `Balance por tipo de cierre / liquidación`, para saber no solo qué evidencia falta sino también si el bot está cortando ganancias demasiado pronto, acumulando `stop_loss`, dejando `pending_exit` sin reconciliar o generando valor pendiente de canjear.

**Zona horaria por ciudad (v10.4.5):** Ya no usa offsets manuales; usa zonas IANA reales con `ZoneInfo` para que DST cambie automáticamente sin tocar el código en marzo/octubre.

**Postmortem base (v10.4.5):** Mantiene `postmortem.json` sincronizado con `BUY`, `SELL_PENDING → SELL/SELL_FAILED`, `LOSS_TOTAL` y `RESOLVED_WIN` para poder analizar cierres y resoluciones con datos estructurados.

**Alertas de observabilidad (v10.4.6):** Hace backfill automático de `postmortem.json` desde `performance.json` si aún no existía, guarda estado persistente en `alerts_state.json`, y envía alertas one-shot por Telegram para `30 trades limpios`, `signals.json` con problemas y `pending_exit` atascadas.

**Bloqueo operativo de London (v10.4.7):** London queda excluida del escaneo de oportunidades por discrepancia conocida `Weather Underground vs Open-Meteo`. Ya no depende de disciplina manual; el bot la filtra en código.

**Refinamiento Telegram (v10.4.8):** `/traders` alinea la cartera por `ciudad + lado + fecha exacta`, `/postmortem` deja de mostrar etiquetas legacy tipo `? YES`, y `/detalle` enseña el último ciclo completo del log en vez de cortar a 40 líneas.

**Sigma widening + exact edge filter + smart alerts (v10.5.0):** Recalibración tras -$8.57 en 17 trades cerrados. Sigma ampliada (Día 0: 2.0 → Día 6+: 4.5), filtro MIN_EDGE_EXACT 15% para apuestas exactas, alertas de drawdown/scaling/win rate. **REVERTIDO en v10.6.0** — la sigma ampliada vendía posiciones ganadoras en re-eval y bloqueaba entradas.

**Intra-cycle SL/TP monitor (v10.5.1):** Thread daemon cada 90 minutos revisa posiciones y ejecuta SL/TP sin esperar al ciclo de 8h. Configurable con `INTRA_SL_INTERVAL` (0=desactivar). Lock para evitar conflicto con ciclo principal. **DESACTIVADO en v10.6.0** — disparaba SL ante fluctuaciones normales en mercados diarios.

**Revert trading logic (v10.6.0):** Sigma restaurada a v10.3 (1.2/1.5/2.0/2.5/3.0), intra-cycle desactivado (default 0), MIN_EDGE_EXACT eliminado (usa MIN_EDGE=7% para todo). Se mantiene toda la observabilidad (postmortem, accuracy, alerts, dashboard, ciudades bloqueadas). El problema real es la fuente de datos, no la confianza del modelo.

**Hardening alerta bankroll (v10.6.2):** La alerta de bankroll bajo ahora solo se activa con señal fiable de cartera (`cash_ok` y sin `api_error`) tanto en Telegram como en dashboard, evitando falsos “recargar” cuando falla la API. Añade `LOW_BANKROLL_RESET_MARGIN=1.0` para rearmar la alerta al salir de la zona roja sin exigir recuperar hasta 2x el umbral.

**Investigación estratégica Codex + Claude (30 mar):** La comparación cruzada dejó tres conclusiones de alta prioridad: (1) `resolution fidelity first` sigue siendo la dirección correcta; (2) Dallas está mal mapeada en producción lógica (`KDFW` en código vs `KDAL` en reglas reales de Polymarket); y (3) la auditoría `forecast_vs_real` actual no compara contra la fuente real de resolución y debe renombrarse/documentarse antes de confiar en esa señal. Se añadieron tres artefactos al repo: `RESEARCH_CODEX_HANDOFF_2026-03-30.md`, `RESEARCH_CLAUDE_2026-03-30.md` y `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`.

**Resolution fidelity hardening (v10.6.3):** Corrige Dallas a `Dallas Love Field / KDAL`, añade la capa declarativa `RESOLUTION_ICAO` con ICAO + URL de Weather Underground para ciudades activas/bloqueadas (y el resto de estaciones actuales), y deja explícito en código/logs que la pseudo-auditoría histórica `forecast_vs_real` sigue siendo solo `forecast original vs forecast posterior Open-Meteo`, no una validación de la fuente real de resolución. `verify_before_deploy.py` sube a `358/358` y añade checks específicos de Dallas, `RESOLUTION_ICAO` y nomenclatura honesta de auditoría.

**Observed proxy layer NOAA (v10.6.4):** Añade `noaa_station_id` explícito en `RESOLUTION_ICAO` solo para las 4 ciudades activas y crea una auditoría separada `observed_vs_forecast` con `source="noaa_ncei"`. Esta capa compara forecast original vs observado NOAA NCEI con lag de 2 días y deja intacta la clave legacy `forecast_vs_real`. Importante: es `observed proxy`, no la fuente real de settlement de Polymarket. El spike de Buenos Aires quedó cerrado: `SAEZ` usa `87576099999`, confirmado vía NOAA HOMR + probe real sobre `global-hourly`. `verify_before_deploy.py` sube a `371/371`.

**Dashboard NOAA observado (v10.6.5):** Añade un bloque nuevo `Calidad Forecast Observada (NOAA)` separado de performance/trading. Lee `audit.json -> observed_vs_forecast`, muestra `n total`, `MAE`, `bias`, cobertura por ciudad activa y los últimos 20 casos. Mantiene visible un bloque legacy `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y `ultimo registro` prominentes, sin mezclar ambas series. `verify_before_deploy.py` sube a `386/386`.

**Foco fidelity + Telegram NOAA (30 mar, sin bump):** El research final `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` concluye `recomiendo no adoptar`, salvo `FMEA-lite` en playbook y una definición mínima de `fallo real / limitacion conocida / ruido`. `OPERATIONS_PLAYBOOK.md` añade ese premortem corto para cambios core, y `run_observability_alerts()` pasa a enviar hitos NOAA one-shot (`primer caso`, `n>=3`, `n>=10`, `ciudad con muestra`, `ciudad interpretable`). Además aparece `/noaa` y `/observabilidad` en Telegram como vista rápida de `sample`, `MAE`, `bias`, cobertura por ciudad y últimos casos, sin tocar el menú principal. `verify_before_deploy.py` sube a `416/416`.

**Allowlist de ciudades activas (v10.6.6):** Añade `ACTIVE_TRADING_CITIES` como allowlist explícita para entradas nuevas, con default `Chicago,Atlanta,Dallas,Buenos Aires`. El scan de mercados ya no depende solo de `BLOCKED_CITIES`: si una ciudad no está en el allowlist, se salta con log `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`. Importante: esto solo afecta BUYs nuevos; `manage_positions` sigue gestionando SL/TP/reeval en posiciones ya abiertas de cualquier ciudad. `verify_before_deploy.py` sube a `419/419`.

**Dashboard estado por ciudad (v10.6.7):** El dashboard añade una tabla nueva `Estado de observacion por ciudad` que cruza `ACTIVE_TRADING_CITIES`, `BLOCKED_CITIES`, muestra NOAA y cierres validados por ciudad. La tabla distingue entre `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` y `Sin observabilidad`. Importante: es una capa descriptiva para seguimiento, no una promocion automatica de ciudades.

**Control Center Discovery/Stabilization (v10.6.8):** Nueva capa 1 operativa tanto en dashboard como en Telegram. El dashboard abre ahora con un `Control Center` que responde explícitamente `¿está sano el sistema?`, `¿hay que intervenir hoy?`, `¿qué limita ahora?`, `¿estamos aprendiendo o solo operando?` y `¿cuál es la acción recomendada hoy?`. Añade `build_dashboard_focus_center()`, prioriza incidentes reales, allowlist y crecimiento NOAA por encima del resto, mueve el detalle pesado a capas inferiores y crea `/focus` en Telegram como vista principal corta, manteniendo `/estado`, `/noaa`, `/accuracy` y `/detalle` como segunda capa.

**Mission HUD operativo (v10.6.9):** La capa 1 del dashboard da un paso mas y se convierte en un HUD tipo videojuego, pero con semantica operativa real. La cabecera pasa a mostrar la mision actual, `System HP`, progreso de `allowlist vs NOAA`, crecimiento de muestra NOAA y ruta operativa por etapas. Añade tabs interactivos `Overview / Progress / Cities`, barras de progreso, `city race` por cobertura NOAA y un `Operator Console` para conservar el detalle fuera del primer golpe de vista. Se mantiene la misma prioridad: discovery / stabilization, sin tocar trading, exits, scheduler ni gestion de posiciones.

**Focus readability pass (v10.6.10):** Refinamiento de la capa 1 tras la primera previsualizacion real. El dashboard pasa a modo claro por defecto para lectura prolongada, agrupa las ciudades en `universo operativo`, `seguimiento/referencia` y `archivo bloqueado`, y deja de repetir la alerta `signals.json stale` como bloqueo principal cuando el cuello de botella real es `NOAA / muestra / cobertura`. La prioridad operativa no cambia: sigue siendo discovery / stabilization, pero con menos ruido y lectura mas directa. `verify_before_deploy.py` sube a `449/449`.

**Observabilidad capa 2 en tabs (4 abr, sin bump):** El mega-card monolítico de `templates/dashboard.html` se divide en 3 pestañas reutilizando el patrón genérico de `static/dashboard.js`: `NOAA` (calidad forecast + últimos 20 casos), `Ciudades` (estado por ciudad, universo operativo, seguimiento y bloqueadas) y `Decisiones` (decision engine, ranking operacional, canary/shadow, shadow reciente y transiciones). No se toca `bot.py` ni backend Python; el cambio es solo estructural en plantilla.

**Auditoría NOAA + hardening local (31 mar, sin bump):** La revisión operativa sobre Railway `v10.6.10` confirmó que `NOAA 0/10` no era solo “falta de tiempo”. El pipeline que llena `audit.json -> observed_vs_forecast` sí tenía casos elegibles, pero el fetch NOAA quedaba ciego porque dependía de `global-hourly`, que devolvía vacío para varios casos 2026 donde `daily-summaries` sí ofrecía `TMAX`. Se añaden `noaa_daily_station_id` para Chicago/Atlanta/Dallas, un helper `fetch_noaa_daily_tmax()`, un wrapper que prioriza `daily-summaries/TMAX` y luego cae a `global-hourly`, y trazabilidad extra (`noaa_daily_station_id`, `observed_dataset`) en cada caso guardado. Tras review adversarial adicional se endurece también el guard de lag en el helper diario y se recupera un test explícito del fallback `daily vacío -> hourly`. Evidencia mínima reconstruida: al menos `7` casos `city|date` elegibles ya existían frente a `0` guardados en producción. `verify_before_deploy.py` sube a `453/453`.

**Trade lifecycle observability layer (31 mar, sin bump):** Se añade una nueva capa derivada `trade_lifecycle.json` para convertir cada posición en una traza completa y legible: `entry_context`, `latest_entry_context`, lista de `buys`, `timeline`, `exit_attempts`, `position_snapshots`, `market_observations`, `close_context`, `post_exit_analysis` y un `summary` agregado con `top_upside_left`. La capa se reconstruye desde `performance.json` + `postmortem.json`, se actualiza automáticamente en cada `BUY/SELL_PENDING/SELL/SELL_FAILED/LOSS_TOTAL/RESOLVED_WIN`, captura snapshots tanto en `manage_positions()` como en el monitor intra-ciclo y registra qué hizo el mercado tras la salida para medir upside perdido o drawdown evitado. No toca ninguna regla de trading. Tras una pasada de higiene se elimina un bloque duplicado de checks y el runner queda limpio; `verify_before_deploy.py` cierra en `467/467`.

**Trade lifecycle hardening fase 1 (31 mar, sin bump):** La primera revisión del raw live de `trade_lifecycle.json` reveló ruido histórico real: `92` filas en producción, de las que `12` eran duplicados por `id` y correspondían a cierres huérfanos reconstruidos dos veces (par `postmortem` + `performance`) cuando el evento histórico no tenía `token_id/question/date`. Se endurece la capa derivada con matching por `id` reconstruido, coalescing defensivo por `id`, bloque explícito `integrity` tanto global como por record (`partial_historical_record`, `analysis_ready`, faltas de token/question/entry/buys, etc.) y test funcional del caso real de “cierre huérfano” para evitar regresiones. Validación con datos live descargados de Railway: reconstruyendo desde `performance.json + postmortem.json`, el lifecycle queda en `80` records únicos, `0` duplicados residuales y `12` `partial_historical_records`. La suite local sube a `470/470`.

**Hotfix `trade_lifecycle` + normalización `agent_events` (31 mar, sin bump):** Al validar en Railway el despliegue de la fase 1 apareció un bug real en live: `trade_lifecycle` empezó a loguear `Error sincronizando trade_lifecycle: unhashable type: 'list'` tanto en startup como durante el ciclo de las `16:00 UTC`. La causa raíz no era un dato extraño sino una comparación inválida en Python dentro de `_merge_trade_lifecycle_context()` y `_merge_trade_lifecycle_record()`, que usaba sets literales del tipo `{None, "", [], {}}`; eso explota en cuanto la ruta de coalescing se ejecuta sobre records duplicados. El hotfix introduce `_lifecycle_is_empty()` para hacer esas comprobaciones de forma segura, añade una regresión funcional que coalesce dos records con el mismo `id` y `entry_context` no vacío, y normaliza `agent_events.jsonl` del repo a `utf-8` para eliminar el warning de seed corrupta en la suite. `verify_before_deploy.py` sube a `472/472`. Importante: NOAA sigue bien (`observed_vs_forecast` ya mostraba 2 casos reales en Chicago); lo roto es solo el sync incremental del lifecycle en Railway hasta desplegar este hotfix.

**Railway CLI hygiene wrapper (31 mar, sin bump):** Tras el recap operativo se deja un guardrail practico para no repetir el bucle `proxy contaminado -> auth rota -> invalid_grant`. Se añade `tools/railway_safe.ps1`, que limpia `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` solo para el proceso actual, ejecuta `railway.cmd` y restaura el entorno al salir. El playbook queda actualizado con una regla explicita: `railway login` solo en shell interactiva del usuario; uso diario de Railway con el wrapper; y desde Codex, Railway fuera del sandbox cuando la CLI pueda refrescar/escribir `%USERPROFILE%\.railway\config.json`.

**Railway auth repair cerrado (1 abr, sin bump):** La sesión dedicada confirmó que los proxies `127.0.0.1:9` no venían de variables persistentes de Windows ni de perfiles de PowerShell; estaban inyectados solo en el proceso actual. El wrapper seguía siendo correcto para red, pero la auth local estaba degradada: `whoami/status` devolvían `Unauthorized` incluso en entorno limpio. Se endurece `tools/railway_safe.ps1` para limpiar también variantes en minúsculas y `npm_config_*`, se añade `tools/railway_auth_repair.ps1` con `doctor`, `reset`, `launch-login` y `restore-links`, y se documenta el flujo de recuperación. Caso real observado el 1 de abril de 2026: tras `reset + login --browserless`, Railway regeneró `config.json` con `projects = {}` aunque `whoami` ya funcionaba; `restore-links` recuperó el enlace desde el backup sin tocar los tokens nuevos. Estado final validado: `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`, `status` y `logs -s polymarket-bot -n 20` vuelven a funcionar.

**Railway relogin hardening (3 abr, sin bump):** Sobre la reparación de la sesión 54 se añade una capa preventiva para evitar que `invalid_grant` reaparezca por contexto de refresh frágil. `tools/railway_safe.ps1` lee `tokenExpiresAt`, aplica una ventana de seguridad de `300s`, verifica si el proceso actual puede abrir `%USERPROFILE%\.railway\config.json` en modo escritura y, si no, corta con instrucciones accionables antes de invocar Railway. También introduce un mutex global `Global\polymarket-bot-railway-cli` para serializar comandos y evitar refreshes OAuth concurrentes. `tools/railway_auth_repair.ps1 doctor` ahora muestra `Writable from this process`, `secondsToExpiry`, `refreshWriteRiskSoon` y usa el mismo mutex en `whoami/version/login`. Evidencia local final: `whoami`, `status` y `doctor` pasan incluso lanzados en paralelo y el expiry queda extendido a `2026-04-03T11:07:57Z`. La causa raíz exacta sigue tratándose como inferencia, no como hecho cerrado, pero el hardening cubre las dos rutas más plausibles.

**Trade analytics dashboard phase 2 (31 mar, sin bump):** Sobre la base ya saneada de `trade_lifecycle`, se añade una capa analítica nueva `build_dashboard_trade_analytics()` que solo cuenta cierres con `market_seen_after_close` y `close_price * close_shares` utilizables. La nueva vista resume: `sample observado`, `score` de eficiencia observada, `harvest efficiency`, `upside_left_total_cash`, `drawdown_avoided_total_cash`, breakdown por `take_profit / reeval / stop_loss`, timeline corto de exits observados y dos colas de revisión (`top_upside_rows`, `top_protection_rows`). El dashboard gana una sección visible para seguir activamente qué está capturando el bot, qué upside deja y qué downside evita, sin tocar ninguna regla de trading. `verify_before_deploy.py` sube a `477/477`.

**Trade console dashboard (31 mar, sin bump):** La primera capa analítica de exits resultó demasiado estrecha para uso diario: respondía bien a `¿estamos capturando bien los exits observados?`, pero no a `¿qué hizo exactamente el bot en cada operación?`. Sobre la misma base de `trade_lifecycle`, el dashboard añade ahora una pestaña separada tipo consola con dos vistas: `Resumen` y `Trades`. Esta nueva capa expone `Operaciones totales`, `TP`, `SL`, `Ganadas`, `Perdidas`, `PnL neto`, `Dejado de ganar` y `Protegido`, además de una tabla por trade con: mercado, condición de entrada del bot, condición de salida, resultado, valor, centavos por share y evidencia observada post-salida. Importante: no depende del CSV local; usa exclusivamente `trade_lifecycle`/`postmortem` para que la misma lectura exista también en Railway. `verify_before_deploy.py` sube a `478/478`.

**Fix exposición redeemable + truncado seguro en SELL (2 abr, sin bump):** Se corrigen dos bugs operativos que podían bloquear capital aunque la wallet ya tuviera dinero prácticamente liberado. En `get_current_exposure()` las posiciones con `redeemable=True` dejan de contar como exposición aunque `curPrice` aún no haya subido a `0.98+`; esto cubre mercados ya resueltos/canjeables que la API sigue mostrando con valor pero que en práctica son cash garantizado. En paralelo, la construcción de órdenes SELL en `manage_positions()` y en el monitor intra-ciclo deja de usar `round(size, 2)` y pasa a truncar hacia abajo con `math.floor(size * 100) / 100`, evitando rechazos `400 not enough balance / allowance` por pedir más shares de las realmente disponibles. Validación dirigida: el caso real tipo `redeemable=True @ 0.97` deja de consumir exposición, el presupuesto libre sube de `0` a zona operativa en el escenario reproducido, y tamaños como `9.48748` se convierten en `9.48` en vez de `9.49`. `verify_before_deploy.py` se mantiene en verde (`483/483`).

**City accuracy tracker (v10.5.2):** Calcula win rate por ciudad desde postmortem. Alerta por Telegram si una ciudad baja de 25% win rate con 3+ trades. Nuevo comando `/accuracy`. Win rate visible en `/rendimiento`.

**Hotfix Atlanta manual (3 abr, sin bump):** La auditoría live confirmó que Atlanta seguía operativa no porque faltara alerta, sino porque `run_observability_alerts()` solo emite una alerta one-shot y deja `city_accuracy_flagged[Atlanta]` persistido; no cambia la política de entrada. Se añade `Atlanta` a `BLOCKED_CITIES` en Railway para cortar BUYs nuevos de inmediato y se documenta el bug de diseño para rediseñarlo en la siguiente sesión.

**Auto-bloqueo persistido por ciudad (3 abr, sin bump):** Se cierra el bug de diseño sin duplicar mecanismo: `load_city_policy_state/save_city_policy_state/get_effective_city_mode/sync_city_policy_state` pasan a manejar `auto_blocked_cities` dentro de `city_policy_state.json`. Cuando una ciudad activa/canary dispara la regla de salida por mala accuracy, se persisten `action`, `reason`, `metrics`, `from_mode` y `triggered_at`, `get_effective_city_mode()` la resuelve como `blocked`, y el scan de BUYs la salta aunque permanezca en la allowlist manual. No hay reactivación automática agresiva desde `blocked`; la reversión queda manual o muy conservadora editando la política persistida. `verify_before_deploy.py` sube a `506/506`.

**Cobertura alarma sin ciclo + sync docs/scoreboard (3 abr, sin bump):** Se confirma que el bloque `sin ciclo en >12h` de `build_dashboard_focus_center()` no tenía una prueba funcional real porque el harness no inyectaba `os/datetime/CYCLE_SUMMARY_FILE/load_cycle_summary_data` y el `try/except` del builder tragaba esa ruta. `verify_before_deploy.py` añade un test que fuerza `cycle_summary.json` inexistente y comprueba que el builder devuelve un `dict` con clave `incidents` y al menos un incidente `badge="warn"`. Además se registra la sesión nueva en `agent_events.jsonl` para corregir el drift docs-scoreboard. Suite local final: `507/507`.

**Integración `/accuracy` + revisión crítica (v10.5.3):** `/accuracy` queda visible en el menú, responde siempre con menú, `/estado` muestra explícitamente el intervalo intra-SL y la trazabilidad de sesión 20 queda corregida para reflejar mejor lo que realmente introdujeron los commits de la mañana.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción (último deploy lanzado):** Railway — EU West Amsterdam, MODO REAL, DRY_RUN=false. Tras la sesión 62, `origin/main` ya incluye tanto el overlay `shadow/canary` como la nueva vista de ranking operacional por ciudad, y el deploy quedó lanzado desde el push del commit `e4dce44`. La validación funcional explícita del deploy sigue pendiente hasta revisar el siguiente ciclo live.
**Estado actual tras sesión 67:** el dashboard ya no se queda en una capa descriptiva por ciudad. `bot.py` calcula un `readiness_score` y una prioridad operativa por ciudad combinando histórico real, evidencia NOAA, actividad shadow y overlay de política, y además el overlay persistente ya soporta `auto_blocked_cities` con evidencia estructurada para cortar BUYs de ciudades perdedoras sin depender solo de Telegram. En paralelo, el tooling de Railway queda más protegido contra relogin recurrente por refresh frágil: mutex global, preflight de escritura del config y telemetría extra en `doctor`. La salida desde `blocked` queda manual/conservadora, no automática agresiva.
**Validación local:** `python verify_before_deploy.py` cierra en `507/507` tras añadir cobertura para la alarma de `cycle_summary.json` ausente en `build_dashboard_focus_center()` y sincronizar `agent_events.jsonl` con la sesión documentada más reciente.
**Versión local / remoto GitHub:** `origin/main` aún no incluye las sesiones 66-67; el siguiente paso operativo es hacer push/deploy, validar en Railway que `city_policy_state.json` registra el auto-bloqueo, confirmar que el scan de BUYs respeta `blocked` aunque la ciudad siga listada como activa, y observar si Railway CLI aguanta el siguiente refresh OAuth sin pedir relogin.
**Tooling local verificado (2 abr, sin bump):** RTK ya quedó operativo como tooling global del usuario para Codex (`rtk --version`, `rtk init -g --codex`, `rtk git status`, `rtk git diff` verificados en uso real), mientras que Engram también quedó operativo como memoria complementaria tras `engram setup codex` y el alta manual por UI del servidor MCP `engram` en la extensión de Codex para VS Code (`C:\Users\USUARIO\go\bin\engram.exe`, `mcp`). Nada de esto sustituye `CONTEXTO.md`/`HISTORIAL_SESIONES.md`/`agent_events.jsonl` como fuente de verdad del repo.
**Siguiente paso prioritario:** validar en live que el ranking operacional refleja bien `degradadas vs candidatas reales` tras el deploy.
**Bloque posterior recomendado, en sesión separada:** una vez confirmada la semántica live, retomar el backfill conservador de `shadow` histórico para enriquecer la capa con evidencia retroconstruida.

### Archivos del proyecto:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.6.10 con NOAA hardening, `trade_lifecycle` saneado y overlay persistente `canary/shadow/blocked` por ciudad |
| `verify_before_deploy.py` | Suite local de `506` tests de comportamiento |
| `trader_analyzer.py` | Genera `signals.json` diariamente en Volume |
| `find_traders.py` | Descubrimiento semanal de traders y mantenimiento de `traders_db.json` en Volume |
| `AGENTS.md` | Contrato corto, canónico y operativo para Codex en la raíz del repo |
| `CLAUDE.md` | Puente corto para Claude Code; remite a `AGENTS.md`, `CONTEXTO.md` y `OPERATIONS_PLAYBOOK.md` |
| `.codex/config.toml` | Config por proyecto para Codex: `medium` por defecto, perfiles `low/deep/max` y permisos operativos predecibles |
| `.codex/skills/` | Skills mínimas del repo para arranque de contexto, auditoría operativa y cierre de sesión sin drift |
| `CONTEXTO.md` | Estado del proyecto (este archivo) |
| `OPERATIONS_PLAYBOOK.md` | Protocolo operativo multiagente y checklist de inicio/cierre |
| `HISTORIAL_SESIONES.md` | Bitácora append-only de sesiones e hitos reconstruidos desde Git |
| `OBSERVABILIDAD_Y_APRENDIZAJE.md` | Plan de fases futuras |
| `RESEARCH_CODEX_HANDOFF_2026-03-30.md` | Informe de investigación de Codex para revisión cruzada |
| `RESEARCH_CLAUDE_2026-03-30.md` | Informe de investigación de Claude Code (Opus) |
| `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md` | Síntesis combinada de ambos informes + roadmap |
| `RAILWAY_AUTH_BUG_HANDOFF_2026-04-01.md` | Handoff específico del bug de relogin continuo de Railway; conserva el diagnóstico previo a la reparación cerrada en la sesión 54 |
| `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` | Handoff específico de la auditoría de inconsistencias en `trade_lifecycle` y la trade console; lista evidencias verificadas y prompt para la siguiente sesión |
| `SNAPSHOT_ANALITICO_LIVE_2026-04-01.md` | Snapshot humano de la revisión live: salud, exits, casos TP/reeval/SL y anomalías semánticas |
| `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json` | Dump congelado del `/api/dashboard.json` live usado como evidencia del snapshot |
| `templates/dashboard.html` | Plantilla principal del dashboard web |
| `static/dashboard.css` | Estilos del dashboard web |
| `static/dashboard.js` | Interaccion ligera para tabs del Mission HUD |
| `agent_events.jsonl` | Eventos semilla para el scoreboard de agentes |
| `trade_lifecycle.json` | Nueva capa derivada por posición: entrada, snapshots, salida y observación post-exit (se genera automáticamente donde exista histórico) |
| `tools/railway_safe.ps1` | Wrapper Railway que limpia proxies, serializa comandos con mutex global y hace preflight de escritura del config antes de refresh OAuth |
| `tools/railway_auth_repair.ps1` | Helper operativo para `doctor / reset / launch-login / restore-links`; `doctor` expone writability, segundos a expiry y riesgo de refresh próximo |
| `tools/append_agent_event.py` | Helper seguro para añadir eventos al scoreboard sin editar JSONL a mano |
| `signals.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `traders_db.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `requirements.txt` | Dependencias Railway |
| `Procfile` | Arranque Railway |

### Datos persistentes (Railway Volume `/app/data`):
| Archivo | Función |
|---------|---------|
| `performance.json` | 38+ trades (BUY/SELL/LOSS_TOTAL desde 25 mar) |
| `postmortem.json` | Postmortems estructurados de apertura/cierre por mercado |
| `alerts_state.json` | Estado persistente de alertas para evitar avisos duplicados |
| `city_policy_state.json` | Overlay persistente por ciudad: `auto_canary_cities`, `auto_shadow_cities`, `auto_blocked_cities` y `transition_history` |
| `shadow_city_tracking.json` | Tracking shadow acumulativo por ciudad (señales detectadas, edges, hit-rate) — input de la autopromoción a canary |
| `agent_events.jsonl` | Eventos persistentes del scoreboard de agentes (si existe en Volume) |
| `signals.json` | Señales de traders activas usadas por el bot en producción |
| `traders_db.json` | Base de datos persistente de traders descubiertos/calificados |
| `trader_history.json` | Historial auxiliar del pipeline de traders |
| `cycle_summary.json` | Último ciclo (se sobreescribe) |
| `cycles_history.jsonl` | Historial acumulativo de todos los ciclos |
| `audit.json` | Ventas pendientes + auditoría legacy `forecast vs forecast posterior` + `observed_vs_forecast` NOAA |
| `trade_lifecycle.json` | Trazabilidad completa derivada por posición: buys, exit_attempts, snapshots, mercado post-salida y summary agregado |
| `decisions.log` | Log detallado por ciclo |
| `trades.log` | Log compacto de órdenes |

### Modos de ciudad — regla canónica (sesión 83)

| Modo | Cómo se activa | Tradea | Observa NOAA |
|------|---------------|:------:|:------------:|
| `blocked` | `BLOCKED_CITIES` o `auto_blocked_cities` | ❌ | ❌ |
| `shadow` | **default** (no está en ninguna lista) | ❌ | ✅ |
| `canary` | `CANARY_TRADING_CITIES` o `auto_canary_cities` | ✅ pequeño | ✅ |
| `active` | `ACTIVE_TRADING_CITIES` | ✅ | ✅ |

**Regla de oro:** `BLOCKED_CITIES` = fuente de datos rota. Para "no operar pero sí acumular NOAA" → dejar en shadow (no añadir a `ACTIVE_TRADING_CITIES`, no añadir a `BLOCKED_CITIES`).

**Nota sesión 85:** el overlay persistido solo debe usar `auto_blocked_cities` para descartes reales. Los legados `action="auto_block"` de mala performance se migran a `auto_shadow_cities`.

### Configuración en Railway (variables de entorno):
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"
MIN_BET="1.00"
DATA_DIR="/app/data"
ACTIVE_TRADING_CITIES="Dallas"
BLOCKED_CITIES="London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara"
ALLOWLIST_REMOVE_MIN_TRADES="25"
CITY_STATS_CUTOFF="Dallas=2026-04-06"
```
Atlanta y Chicago: shadow (fuera de BLOCKED_CITIES, fuera de ACTIVE_TRADING_CITIES) — acumulan NOAA sin operar.

### Configuración en código (defaults bot.py v10.6.11, sesión 82-83):
```python
MIN_EDGE = 15.0%
MIN_PRICE = 0.20      # sesión 82: subido desde 0.08 — evita mercados extremos
MAX_PRICE = 0.80      # sesión 82: bajado desde 0.92 — simétrico con MIN_PRICE
ALLOWED_CONDITIONS = at_or_above,at_or_below
STOP_LOSS_PCT = -25.0%
TAKE_PROFIT_PCT = +40.0%
HIGH_CONVICTION_TP_PCT = +80.0%          # sesión 196: TP elevado si our_prob >= 0.80 en entrada
HIGH_CONVICTION_PROB_THRESHOLD = 0.80    # sesión 196: umbral para activar TP dinámico
MAX_EXPOSURE_PCT = 40%
MIN_BET = $1.00
BLOCKED_CITIES = ["London","Miami","Seattle","Paris","Tel Aviv","Wellington","Toronto","Madrid","Singapore","Ankara"]
BANKROLL_LEVELS = [25, 35, 50, 75, 100]
DASHBOARD_PORT = $PORT
DASHBOARD_REFRESH_SEC = 60
PROMOTION_CITY_COVERAGE_TARGET = 3
INTRA_SL_INTERVAL = 0           # v10.6.0: desactivado (v10.5 usaba 90)
CITY_MIN_TRADES_FOR_BLOCK = 3
CITY_BLOCK_WIN_RATE = 25.0%
LOW_BANKROLL_THRESHOLD = $5.00
LOW_BANKROLL_RESET_MARGIN = $1.00
Sigma: empírica por ciudad si n>=3; fallback global D0=2.0 D1=1.9 D2=2.5 D3=3.0; fallback final v10.3 D0=1.2 D1=1.5 D2=2.0 D3=2.5 D4-5=3.0
FORECAST_BIAS_C: Atlanta=+1.38°C, Chicago=+1.40°C, Dallas=0.0 (sesión 82, NOAA n=5/5/3)
EMPIRICAL_SIGMA Dallas D0: 0.57°C (n=3, NOAA sesión 82)
Schedule: 08:00, 16:00, 23:00 UTC
```

---

## Telegram — Comandos disponibles (v10.6.10)

| Comando | Qué muestra |
|---------|-------------|
| `/focus` | Vista principal de capa 1: salud real, intervención hoy, limitador actual, estado de aprendizaje NOAA y acción recomendada |
| `/estado` | Versión, modo, bankroll, SL/TP, intervalo intra-SL, próximo ciclo, último ciclo y contadores `total`/`serie v10.6` |
| `/cartera` | Cash, posiciones vivas (ciudad+temp+fecha, precios en ¢), resueltas, muertas |
| `/log` | Resumen del último ciclo desde cycle_summary.json |
| `/detalle` | Último ciclo completo del `decisions.log`, paginado y sin corte fijo de 40 líneas |
| `/rendimiento` | Portfolio real + historial trades (TP/SL/reeval, por ciudad con win rate) |
| `/ordenes` | Órdenes GTC pendientes con etiquetas legibles |
| `/traders` | Señales activas + coincidencias filtradas por ciudad, lado y fecha exacta del mercado |
| `/info` | Bloque resumen completo para pegar en Claude/ChatGPT, incluyendo contadores `total`/`serie v10.6` |
| `/postmortem` | Resumen rápido de abiertas/cierres desde `postmortem.json` |
| `/accuracy` | Win rate por ciudad desde postmortem, con iconos de bloqueada/flaggeada y botón visible en el menú |
| `/noaa` / `/observabilidad` | Muestra `sample`, `MAE`, `bias`, cobertura por ciudad activa y últimos casos de `observed_vs_forecast` |
| `/forzar` | Ejecuta ciclo inmediatamente |
| `/modo` | Cambia DRY RUN ↔ REAL |

**Para iniciar una sesión de análisis en claude.ai:** pegar `/info` + `/cartera` + `/rendimiento`.

## Dashboard web (v10.6.10)

- **Ruta principal:** `/`
- **Healthcheck:** `/healthz`
- **API JSON:** `/api/dashboard.json`
- **Autenticación:** básica opcional con `DASHBOARD_USER` y `DASHBOARD_PASSWORD`
- **Objetivo:** separar monitorización visual de Telegram para revisar el sistema en navegador

### Qué muestra
- capa 1 `Mission HUD / Discovery-Stabilization` con mision actual, `System HP`, accion recomendada y respuestas explicitas a salud, intervencion, limitador y aprendizaje
- tabs interactivos `Overview / Progress / Cities` para alternar entre lectura rapida, barras de progreso y carrera NOAA por ciudad sin abandonar la capa 1
- quick stats de universo activo, NOAA interpretable, muestra NOAA y próximo ciclo
- incidents rail con solo alertas activas relevantes
- layering operativa clara: `capa 1` visible primero, `capa 2` como seguimiento/explicación y `capa 3` colapsada para detalle extendido
- nivel actual y siguiente bankroll objetivo
- checklist de promoción `$25 -> $35` separando histórico vs serie `v10.6`
- salud operativa del sistema
- métricas de la serie `v10.6`
- últimos ciclos y posiciones abiertas
- scoreboard de agentes y rivalidad constructiva por stages (`proposed / implemented / validated`)
- modo claro por defecto para lectura y seguimiento prolongado en navegador
- cuando la serie aún no tiene cierres, muestra `n/d` / `sin cierres` en lugar de métricas aparentes
- el checklist distingue visualmente entre `Pendiente` y `Esperando muestra`
- alerta crítica de bankroll bajo cuando la cartera cae bajo `$5`, pero solo con señal fiable (`cash_ok` y sin `api_error`)
- bloque `Progreso` con `faltan X para Y` sobre muestra, estabilidad, cierres útiles, readiness de nivel y cobertura de ciudades
- bloque `Trofeos` con hitos del bot calculados solo desde cierres validados (`mejor operación`, `mayor edge ejecutado`, `ciudad más rentable`, etc.)
- bloque `Desbloqueos` con evidencias/confirmaciones pendientes antes de revisar lógica o evaluar subir bankroll
- bloque `Calidad Forecast Observada (NOAA)` separado del PnL/trading, con `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos de `observed_vs_forecast`
- tabla `Estado de observacion por ciudad`, que cruza allowlist actual, bloqueo, muestra NOAA e histórico validado para distinguir operativa real vs referencia historica vs falta de observabilidad
- bloque legacy `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y fecha del último registro para no mezclar la serie nueva con la auditoría vieja

## Hoja de ruta UX operativa

**Fase 1 — Mission HUD (consolidada en v10.6.10):**
- una sola pantalla para decidir si hoy toca actuar o solo seguir recogiendo evidencia;
- capa 1 limitada a salud real, bloqueo dominante, allowlist, NOAA y accion recomendada;
- interaccion ligera con tabs, sin mover el detalle fuera del dashboard.

**Fase 2 — Tendencias de aprendizaje (siguiente iteracion recomendada):**
- series temporales cortas para `sample NOAA por dia`, `coverage activa por ciudad` y `eventos/incidentes por jornada`;
- comparativas visuales para distinguir si estamos aprendiendo mas rapido o solo operando mas;
- mantener esto en `Progress` o capa 2, nunca mezclado con la decision principal.

**Fase 3 — Drill-down operativo:**
- filtros por ciudad/estado (`activa`, `bloqueada`, `solo observacion`, `interpretable`);
- detalle interactivo por ciudad con ultimo caso NOAA, historico validado y razon de estado;
- timeline de checkpoints diarios para sesiones de seguimiento mientras se acumulan datos.

**Regla de diseño:** cualquier nueva visual entra en capa 1 solo si cambia la decision de hoy; si solo explica, vive en capa 2 o capa 3.

---

## BUGS — Estado completo

### Corregidos (v10.3 → v10.4.3):
- **#3** ✅ Duplicados: consulta Data API antes de comprar
- **#4** ✅ Resueltas contaban como exposición
- **#5** ✅ Zona horaria asiática (CITY_UTC_OFFSETS per-city)
- **#6** ✅ signals.json freshness 12h → 26h
- **#7** ✅ SELL_PENDING → SELL en audit
- **#8** ✅ Posiciones micro → LOSS_TOTAL
- **#9** ✅ Re-entrada tras stop-loss mismo ciclo
- **#10** ✅ MIN_BET default 0.50 → 1.00
- **#11** ✅ Ciclo extra al arrancar
- **#12** ✅ Doble conteo resueltas en Telegram
- **#13** ✅ Paginación automática >3800 chars (send_telegram_paged)
- **#14** ✅ Precio límite vs fill clarificado en Telegram

### Pendientes:
- **#15** ✅ **Corregido en v10.6.6:** `ACTIVE_TRADING_CITIES` añade allowlist explícita para entradas nuevas y restringe BUYs a Chicago, Atlanta, Dallas y Buenos Aires. El bug original venía de depender solo de `BLOCKED_CITIES`, lo que dejaba pasar ciudades sin validación NOAA/WU como Seoul, Tokyo, NYC y Munich. La gestión de posiciones existentes (`manage_positions`) no se toca.
- **Observed proxy NOAA / bug de observabilidad detectado:** la auditoría de `31 mar 2026` encontró al menos `7` casos `city|date` elegibles para NOAA en las 4 activas, mientras Railway seguía mostrando `observed_vs_forecast = 0`. No era solo falta de muestra. Causa raíz: `global-hourly` devolvía vacío en varios casos 2026 que sí estaban en `daily-summaries`. Fix local listo: priorizar `daily-summaries/TMAX` para Chicago/Atlanta/Dallas, guardar `observed_dataset`, añadir guard de lag al helper diario y cubrir el fallback `daily -> hourly`; falta desplegar y validar en Railway.
- **Nueva trazabilidad operativa lista para análisis, aún sin poblar localmente con live data:** `trade_lifecycle.json` ya está implementado y validado con tests; medirá contexto de entrada, intentos de salida, snapshots de posición y comportamiento del mercado tras el cierre. El backfill real de la cuenta se generará en el próximo arranque desplegado. No se pudo materializar localmente desde Railway en esta sesión porque el login OAuth del CLI estaba caducado.
- **Saneamiento local de `trade_lifecycle` / trade console (sesión 57, 1 abr 2026):** la auditoría abierta en la sesión 56 ya quedó convertida en cambios concretos de reconciliación/presentación. `build_dashboard_trade_analytics()` vuelve a coalescer records al leer, une duplicados del mismo mercado+lados cuando uno es un follow-up sin BUY (`LOSS_TOTAL`/`RESOLVED_WIN` repetidos), cruza la historia con `portfolio.active/resolved_won/dead`, y crea fallback visible para posiciones recientes presentes solo en cartera. Resultado esperado sobre los casos auditados: `Seoul 14C` deja de verse como historia contradictoria al explicitar el lado; `Seoul 13C` ya no depende de `entry_condition` parcial si la cartera conserva `avgPrice`; `Atlanta 70-71F` y `Dallas 82-83F` condensan `SELL` + residuo micro en una sola narrativa; `Atlanta 78-79F` entra en la tabla aunque solo exista en `portfolio.dead`; `Tokyo 18C` y `Buenos Aires 28C` muestran resolución con `claim` pendiente; `Chicago 40-41F` sigue abierta con lectura coherente de cartera. Sigue sin existir un evento explícito de `REDEEM`, así que la consola habla con honestidad de “claim pendiente / no confirmado” en vez de inventar un cobro.
- **Prioridad siguiente sesión (2 abr 2026):** auditar la captura del `Mission HUD` como fuente de verdad visual de la capa 1. La revisión debe contrastar screenshot, snapshot/dashboard JSON y builders locales para comprobar que las métricas y textos prioritarios no estén arrastrando errores de agregación, buckets equivocados o semántica desalineada.
- **Auditoría de token economics pendiente, en sesión separada:** revisar consumo de contexto/tokens de Codex y Claude Code con reglas explícitas de `1 sesión = 1 tarea`, contexto mínimo y escalado selectivo de reasoning/modelo. No mezclar esta auditoría con la revisión del HUD.
- **Seguimiento de ciudades aún descriptivo:** `v10.6.7` ya muestra por dashboard qué ciudades están activas, bloqueadas, fuera del allowlist o sin observabilidad, pero todavía no existe promoción automática tipo `watchlist / shadow / canary`.
- **Buenos Aires NOAA spike cerrado:** `SAEZ` usa `87576099999`, confirmado con NOAA HOMR y una consulta real al endpoint `global-hourly`.
- **Buenos Aires daily station aún no validada:** el fix local resuelve el cuello de botella principal en US con `daily-summaries`, pero Buenos Aires sigue temporalmente en fallback `global-hourly` hasta encontrar y validar un `daily_station_id` fiable.
- **Fuente real de resolución sigue sin automatizarse:** NOAA mejora mucho la observabilidad, pero sigue siendo `observed proxy`, no la fuente real de settlement de Polymarket.
- **Auditoría legacy sigue limitada aunque honesta:** `forecast_vs_real` sigue existiendo como nombre legacy en `audit.json`, pero los logs/código ya dejan claro que compara `forecast original vs forecast posterior Open-Meteo`, no “real” ni Weather Underground.
- **Weather Underground vs Open-Meteo:** Polymarket resuelve con WU, no Open-Meteo. London sigue bloqueada en código desde `v10.4.7`. IBM Trial no accesible; la vía correcta a corto plazo es alinear resolución, no esperar una API oficial.

---

## Versionado — sistema establecido

- **v10.4.X** = misma lógica de trading, mejoras UI/Telegram/observabilidad
- **v10.5.0** = recalibración de lógica de entrada (sigma, exact filter) — REVERTIDO en v10.6.0
- **v10.5.X** (X>0) = mejoras operativas sin cambiar lógica de entrada
- **v10.6.0** = revert trading logic a v10.3 + toda la observabilidad de v10.5.X
- Ciclos y datos son continuos y acumulativos entre versiones; desde `v10.5.4` se muestra además contador por serie lógica actual
- Cada registro incluye la versión del bot que lo generó

### Historial de versiones:
| Versión | Fecha | Cambios principales |
|---------|-------|-------------------|
| v10.3 | 25 mar | Bugs #4-#8, zona horaria per-city, SELL_PENDING |
| v10.4 | 28 mar | Bugs #3,#9,#10,#11,#12,#14 + persistencia Volume |
| v10.4.1 | 28 mar | cycles_history.jsonl + cycle_summary.json |
| v10.4.2 | 28 mar | Rediseño Telegram + Bug #13 + helpers + /info |
| v10.4.3 | 28 mar | Ciclos persistentes + fixes post-deploy + limpieza repo |
| v10.4.4 | 28 mar | Ajuste temporal manual de DST |
| v10.4.5 | 28 mar | `ZoneInfo` + zonas IANA reales + `.claude/` fuera del repo + `postmortem.json` base + trader data al Volume + `/postmortem` |
| v10.4.6 | 28 mar | backfill automático de `postmortem.json` + `alerts_state.json` + alertas Telegram de observabilidad |
| v10.4.7 | 28 mar | bloqueo operativo de London en código + tests para evitar regresión |
| v10.4.8 | 28 mar | refinamiento Telegram: `traders` por fecha exacta, `postmortem` legacy legible y `detalle` sin corte fijo |
| v10.5.0 | 29 mar | sigma widening (2.0→4.5), MIN_EDGE_EXACT 15%, smart alerts (drawdown/scaling/win rate), 216 tests |
| v10.5.1 | 29 mar | intra-cycle SL/TP monitor cada 90min, threading.Lock, 226 tests |
| v10.5.2 | 29 mar | city accuracy tracker, `/accuracy`, win rate en `/rendimiento`, alertas por ciudad, 234 tests |
| v10.5.3 | 29 mar | `/accuracy` integrado en menú + menú persistente + `/estado` muestra intra-SL + trazabilidad corregida, 242 tests |
| v10.5.4 | 29 mar | contador dual de ciclos (histórico total + serie lógica), `logic_series`/`logic_cycle_number` en historial, `/estado` y `/info` separan total vs serie, 251 tests |
| v10.5.5 | 29 mar | dashboard web HTML separado de Telegram + checklist de bankroll + scoreboard de agentes + `agent_events.jsonl`, 279 tests |
| v10.5.6 | 29 mar | dashboard oscuro + checklist histórico/serie separado + scorecard por stages + ciclos legacy legibles, 290 tests |
| v10.5.7 | 29 mar | dashboard evita métricas falsas sin muestra (`n/d` / `sin cierres`) en serie nueva, 294 tests |
| v10.5.8 | 29 mar | checklist con estado visual neutral `Esperando muestra` para serie sin datos, 300 tests |
| v10.5.9 | 29 mar | dashboard añade `Progreso`, `Trofeos` y `Desbloqueos`, más cobertura de tests funcionales de snapshot y readiness, 325 tests |
| v10.5.10 | 29 mar | dashboard añade `Balance por tipo de cierre` y `Liquidación`, separando TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN de `pending_exit` y `pendiente pago`, 334 tests |
| v10.5.11 | 29 mar | fix drawdown checklist + sync agent_events Railway, 337 tests |
| v10.5.12 | 29 mar | bloqueo 10 ciudades 0% WR + fix posiciones fantasma, 338 tests |
| **v10.6.0** | **29 mar** | **revert sigma a v10.3, intra-cycle off, MIN_EDGE_EXACT eliminado. Mantiene toda observabilidad. 335 tests** |
| v10.6.1 | 29 mar | fix drawdown sort, alerta bankroll bajo ($5), unlock redundante eliminado, scoreboard sesión 30. 338 tests |
| v10.6.2 | 29 mar | hardening alerta bankroll: exige `cash_ok` y ausencia de `api_error`, añade `LOW_BANKROLL_RESET_MARGIN`, tests funcionales dashboard/Telegram/reset. 348 tests |
| v10.6.3 | 30 mar | fix Dallas `KDAL`, añade `RESOLUTION_ICAO` con URLs WU, renombra/documenta la pseudo-auditoría como `forecast vs forecast posterior Open-Meteo`, y sube a 358 tests |
| v10.6.4 | 30 mar | añade `observed_vs_forecast` con NOAA NCEI, `noaa_station_id` explícito para las 4 activas, lag de 2 días, tests funcionales NOAA y 371 tests |
| v10.6.5 | 30 mar | dashboard añade bloque `Calidad Forecast Observada (NOAA)` + bloque legacy `Drift Open-Meteo`, separados de performance/trading, y sube a 386 tests |
| **v10.6.6** | **30 mar** | **allowlist `ACTIVE_TRADING_CITIES` — entradas nuevas solo en Chicago/Atlanta/Dallas/Buenos Aires; gestión de posiciones existentes no afectada; suite en 419 tests** |
| **v10.6.7** | **30 mar** | **dashboard añade tabla `Estado de observacion por ciudad`, cruzando allowlist, bloqueo, NOAA e histórico validado para distinguir operativa real vs referencia; suite en 426 tests** |

---

## Trazabilidad por herramienta

**Objetivo:** este proyecto se trabaja con varias herramientas. A partir de ahora, cada sesión debe dejar anotado qué agente hizo qué, qué detectó, y qué corrigió a otro agente si aplica.

### Convención a seguir en futuras sesiones

- **Lectura obligatoria al abrir sesión:** `AGENTS.md` + bloque relevante de `CONTEXTO.md` + `OPERATIONS_PLAYBOOK.md` si la tarea toca workflow/deploy/cierre
- **ChatGPT / Claude.ai:** análisis, estrategia, revisión de contexto, ideas y validación conceptual.
- **Codex:** cambios de código en local, revisión crítica del repo, corrección de implementaciones previas, validación técnica y tests.
- **Claude Code:** edición/coding en local cuando se use explícitamente para implementar cambios.

### Regla de documentación

- Cada sesión importante debe añadir una nota breve indicando:
- `Herramienta usada`
- `Qué hizo`
- `Qué problemas detectó`
- `Qué corrigió de trabajo previo`
- `Qué quedó pendiente`

### Plantilla fija — Registro de sesión

Usar esta plantilla al cerrar cada sesión relevante:

```md
### Sesión XX — Registro multi-herramienta

- **Fecha:** YYYY-MM-DD
- **Versión activa al cerrar:** v10.X.X
- **Objetivo de la sesión:** ...

- **ChatGPT / Claude.ai:**
  Análisis / estrategia / contexto aportado:
  ...

- **Claude Code:**
  Cambios implementados:
  ...

- **Codex:**
  Revisión crítica / cambios / validaciones:
  ...

- **Problemas detectados en trabajo previo:**
  ...

- **Correcciones aplicadas en esta sesión:**
  ...

- **Tests / verificaciones ejecutadas:**
  ...

- **Pendientes para la próxima sesión:**
  ...

- **Estado final:**
  versión ..., tests ..., deploy sí/no, observaciones ...
```

### Regla práctica de uso

- `AGENTS.md` define la capa corta y canónica para Codex; `CONTEXTO.md` define el estado actual; `OPERATIONS_PLAYBOOK.md` define el protocolo para no desalinear código, docs y scoreboard.
- Si solo participa una herramienta, se rellena solo su bloque y se dejan las demás como `No usado en esta sesión`.
- Si una herramienta corrige o valida trabajo de otra, dejarlo explícito en `Problemas detectados en trabajo previo` y `Correcciones aplicadas en esta sesión`.
- Si hay cambios en Railway, Volume, Telegram o datos históricos, anotarlo también en el bloque `Estado final`.
- Antes de cada push relevante, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md` si la sesión cambió estado, arquitectura, datos persistentes, comandos Telegram, workflow o trazabilidad multi-agente.
- Antes de cerrar una sesión relevante, actualizar también `agent_events.jsonl` usando `tools/append_agent_event.py` o un método equivalente seguro.

### Sesión 20 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.2
- **Objetivo de la sesión:** Completar v10.5.1 (intra-cycle SL) + implementar city accuracy tracker (v10.5.2) + investigar WU API

- **Claude Code (Opus):**
  - Implementó y cerró v10.5.1: intra-cycle SL/TP monitor cada 90min con `sell_lock`, thread daemon y cobertura ampliada hasta 226/226
  - Investigó Weather Underground API: API muerta desde 2019, IBM Trial no viable para Pablo (verificación fallida), opciones: PWS key o accuracy tracker
  - Diseñó e implementó v10.5.2: city accuracy tracker con `get_city_accuracy()`, alertas automáticas por ciudad, comando `/accuracy`, win rate en `/rendimiento` → 234/234 tests
  - Actualizó CONTEXTO.md y HISTORIAL_SESIONES.md

- **Codex:** No usado en esta sesión.
- **ChatGPT / Claude.ai:** No usado en esta sesión.

- **Problemas detectados en trabajo previo:**
  - CONTEXTO.md seguía diciendo v10.4.8, posiciones incorrectas (Dallas/Miami como activas cuando ya habían sido vendidas SL)

- **Lección de gestión de uso:**
  - Sesión consumió mucho uso de Opus. Tareas como investigación WU, escritura de tests, y actualizaciones de docs podrían haberse delegado a Codex para preservar el budget de Opus para decisiones de diseño y coding crítico.

- **Estado final:**
  v10.5.2, 234/234 tests, deploy hecho, v10.5.0+v10.5.1+v10.5.2 en producción, CONTEXTO.md actualizado

### Sesión 21 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.3
- **Objetivo de la sesión:** Revisar críticamente los cambios de la mañana, cerrar huecos de Telegram y corregir la trazabilidad del proyecto

- **Claude Code (Opus):**
  - No usado directamente en esta sesión de revisión

- **Codex:**
  - Revisó commits `v10.5.0`, `v10.5.1` y `v10.5.2` contra Git y código real
  - Detectó que `/accuracy` existía como comando pero no estaba integrado en el menú de Telegram y tampoco volvía con menú
  - Detectó que `/estado` no mostraba el intervalo intra-SL aunque el contexto sí lo documentaba
  - Señaló que la narrativa de sesión 20 decía “solo tests” para `v10.5.1`, pero el commit real había introducido bastante código en `bot.py`
  - Integró `/accuracy` en `MENU_KEYBOARD`, añadió menú persistente y visibilidad del intervalo intra-SL en `/estado`
  - Amplió `verify_before_deploy.py` hasta `242/242` para cubrir estas integraciones
  - Actualizó `CONTEXTO.md` e `HISTORIAL_SESIONES.md` para mantener la memoria del proyecto alineada con Git

- **Problemas detectados en trabajo previo:**
  - `/accuracy` incompleto a nivel UX
  - ligera desalineación docs-código en `/estado`
  - trazabilidad de sesión 20 demasiado simplificada

- **Estado final:**
  v10.5.3, 242/242 tests, repo alineado a nivel código/tests/docs, listo para decidir si hacer deploy

### Sesión 22 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.4
- **Objetivo de la sesión:** Separar el contador histórico de ciclos del contador específico de la nueva lógica `v10.5`

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que `Ciclos: 4` seguía mezclando histórico total con evaluación de la serie `v10.5`
  - Implementó `_load_cycle_counts()` para cargar `total` y `serie lógica` desde `cycles_history.jsonl`
  - Mantuvo `cycle_count` como histórico total para no romper continuidad operativa
  - Añadió `cycle_count_series`, `logic_series` y `logic_cycle_number`
  - Actualizó `/estado` y `/info` para mostrar `total | serie v10.5`
  - Amplió `verify_before_deploy.py` con tests estructurales y funcionales del recuento mixto `v10.4`/`v10.5`
  - Movió los temporales del verificador al directorio temporal del sistema para no ensuciar el repo

- **Problemas detectados en trabajo previo:**
  - El contador acumulativo total era correcto operativamente, pero confuso para analizar la lógica nueva
  - La suite de tests dejaba temporales `_tmp_*` en el workspace de Windows

- **Estado final:**
  v10.5.4, 251/251 tests, histórico total preservado y serie `v10.5` visible por separado en Telegram

### Sesión 23 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.5
- **Objetivo de la sesión:** Crear un dashboard web separado de Telegram para visualizar el sistema, el checklist de bankroll y la rivalidad de agentes

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Diseñó e implementó un dashboard web HTML servido desde el mismo servicio Railway
  - Añadió checklist de promoción de bankroll (`$25 -> $35`) calculado desde métricas reales del sistema
  - Añadió scoreboard de agentes y rivalidad constructiva a partir de `agent_events.jsonl`
  - Creó `templates/dashboard.html` y `static/dashboard.css`
  - Añadió configuración de dashboard (`DASHBOARD_*`, `BANKROLL_LEVELS`) y arranque HTTP en paralelo al bot
  - Amplió `verify_before_deploy.py` hasta `279/279` para cubrir backend, checklist, scorecard y archivos del dashboard

- **Problemas detectados en trabajo previo:**
  - La observabilidad seguía demasiado concentrada en Telegram para revisar sistema, niveles y progreso
  - No existía una métrica estructurada para comparar aportaciones de Opus vs Codex

- **Estado final:**
  v10.5.5, 279/279 tests, dashboard web listo para abrir en navegador, Telegram queda separado de la capa visual principal

### Sesión 24 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.6
- **Objetivo de la sesión:** Refinar el dashboard tras la primera revisión visual para que el checklist mida mejor la serie `v10.5`, el scorecard sea más legible y el panel quede en modo oscuro

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que el checklist del dashboard mezclaba `trades limpios` históricos con métricas de la serie `v10.5`, lo que hacía menos fiable la decisión de subir bankroll
  - Cambió el checklist para separar explícitamente `histórico` vs `serie v10.5`
  - Añadió `get_logic_series_clean_closed_trade_stats()` para medir cierres limpios de la serie lógica actual
  - Refinó el scoreboard de agentes para mostrar estados `proposed / implemented / validated`
  - Hizo que los ciclos legacy se muestren como `legacy v10.X` en vez de `#?`
  - Reordenó las ciudades clave por riesgo operativo en vez de solo por número de trades
  - Rediseñó `static/dashboard.css` a modo oscuro y actualizó la plantilla HTML para reflejar mejor los nuevos estados
  - Amplió `verify_before_deploy.py` hasta `290/290` con checks de dark mode, stages y checklist separado

- **Problemas detectados en trabajo previo:**
  - El dashboard v10.5.5 mezclaba progreso histórico y progreso de la serie nueva en una misma vista de promoción
  - El scorecard seguía siendo útil pero no mostraba todavía la madurez de cada contribución
  - Los ciclos anteriores a `v10.5` se veían ambiguos en la tabla (`#?`)

- **Estado final:**
  v10.5.6, 290/290 tests, dashboard oscuro y más honesto para evaluar la serie `v10.5` sin perder contexto histórico

### Sesión 25 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.7
- **Objetivo de la sesión:** Hacer una pasada rápida de UX para que el dashboard no muestre métricas engañosas cuando la serie `v10.5` aún no tiene cierres

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que `PnL serie`, `Win rate serie` y `Drawdown reciente` seguían mostrándose como `+$0.00` / `0.0%` con `0` cierres, lo que parecía un dato real cuando en realidad faltaba muestra
  - Ajustó el checklist para que `PnL`, `Win rate` y `Drawdown` queden en `sin cierres` hasta que exista información válida
  - Cambió los cards del dashboard para mostrar `n/d` y subtítulos como `Sin cierres todavía` o `Esperando muestra`
  - Amplió `verify_before_deploy.py` con casos funcionales para asegurar que estas métricas no vuelvan a mostrarse como si fueran reales sin haber cierres

- **Problemas detectados en trabajo previo:**
  - El panel era ya coherente en estructura, pero todavía podía inducir a interpretar como “OK” una serie sin muestra

- **Estado final:**
  v10.5.7, 294/294 tests, dashboard semánticamente más claro para analizar una serie nueva sin sobreinterpretar ceros iniciales

### Sesión 26 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.8
- **Objetivo de la sesión:** Último pulido visual del checklist para distinguir entre una condición fallida y una métrica que todavía está esperando muestra

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión

- **Codex:**
  - Añadió un tercer estado al checklist del dashboard: `Esperando muestra`
  - Mantuvo intacta la lógica de promoción, pero separó visualmente `fallo` vs `todavía sin datos`
  - Ajustó la plantilla y los estilos para que ese estado se vea neutro y no rojo
  - Amplió `verify_before_deploy.py` para cubrir `status` y `tag` de los checks cuando no hay cierres en la serie
  - Dejó contexto e historial actualizados para que la siguiente revisión con Claude Code Sonnet tenga trazabilidad clara

- **Problemas detectados en trabajo previo:**
  - Aunque `v10.5.7` ya evitaba métricas engañosas, el checklist seguía pintando esos casos como `Pendiente` rojo, lo que mezclaba falta de muestra con fallo real

- **Estado final:**
  v10.5.8, 300/300 tests, dashboard visualmente más fino y más fácil de interpretar en fases tempranas de una serie nueva

### Sesión 27 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.9
- **Objetivo de la sesión:** Añadir al dashboard una capa más operativa de progreso, trofeos e hitos desbloqueables para saber qué evidencia falta antes de revisar la estrategia o subir bankroll

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión

- **Codex:**
  - Implementó un bloque `Progreso` con muestra pendiente para revisar la serie `v10.5`, estabilidad por ciclos, cierres útiles para activar win rate/drawdown, readiness de subida a `$35` y cobertura de ciudades con muestra suficiente
  - Añadió un bloque `Trofeos` calculado solo desde cierres validados para destacar mejor operación, mejor retorno, mayor edge ejecutado, primera victoria validada, peor operación y ciudades extremas
  - Añadió un bloque `Desbloqueos` para expresar de forma explícita qué confirmaciones faltan antes de confiar en métricas de serie o evaluar decisiones de bankroll
  - Reutilizó `postmortem.json`, `performance.json`, `cycles_history.jsonl` y `alerts_state.json` sin tocar la lógica de trading
  - Amplió `verify_before_deploy.py` hasta `325/325` con tests estructurales y funcionales de snapshot, progreso, trofeos y desbloqueos

- **Problemas detectados en trabajo previo:**
  - El dashboard era ya consistente, pero todavía faltaba una capa más práctica de “faltan X para poder hacer Y”
  - El panel tenía scorecard y checklist, pero no convertía bien la evidencia acumulada en hitos operativos fáciles de interpretar

- **Estado final:**
  v10.5.9, 325/325 tests, dashboard más útil para readiness operativa y más preparado para una revisión global con Claude Code Sonnet

### Sesión 28 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.10
- **Objetivo de la sesión:** Hacer medible en el dashboard si el bot corta ganancias demasiado pronto frente a pérdidas demasiado grandes, separando cierres validados, salidas pendientes y cobros pendientes

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión; queda como siguiente revisor de toda la iteración reciente del dashboard

- **Codex:**
  - Añadió `build_dashboard_exit_breakdown()` al backend para resumir balance por tipo de cierre usando solo datos ya existentes (`postmortem.json`, serie lógica actual y cartera viva)
  - Separó explícitamente `Take-profit`, `Stop-loss`, `Re-evaluación`, `LOSS_TOTAL`, `Ganadas por resolución`, `Ganadas validadas` y `Perdidas validadas`
  - Añadió una tarjeta de `Liquidación` para distinguir `cierres validados`, `pending_exit`, `abiertas`, `exit_failed` y `pendiente pago / canjear`
  - Dejó claro en el dashboard cuándo el balance ya es validado y cuándo sigue siendo solo estimado por fill pendiente
  - Amplió `verify_before_deploy.py` hasta `334/334` con tests estructurales y funcionales del bloque nuevo, incluyendo `pending_exit` y `canjear`

- **Problemas detectados en trabajo previo:**
  - El dashboard ya explicaba progreso y readiness, pero seguía faltando una vista directa del balance por tipo de salida para responder si el sistema está cortando beneficios antes de tiempo
  - La diferencia entre `vendido en mercado`, `cerrado y auditado` y `pendiente de canjear` no estaba suficientemente visible para interpretación operativa

- **Estado final:**
  v10.5.10, 334/334 tests, dashboard más útil para diagnosticar por qué baja el bankroll y para diferenciar cierres validados de fills/cobros aún pendientes

### Sesión 19 — Registro multi-herramienta

- **Claude Code:** implementó v10.4.2, v10.4.3 y v10.4.4; rediseño Telegram, paginación, `/info`, persistencia de ciclos, limpieza del repo y un fix manual de DST basado en offsets estáticos.
- **Codex:** revisó críticamente esa secuencia y detectó dos deudas importantes: el fix de DST seguía siendo frágil por usar offsets manuales, y `.claude/settings.local.json` había quedado versionado por error.
- **Codex:** corrigió el enfoque de DST en `bot.py` migrando a `ZoneInfo` + `CITY_TIMEZONES` con zonas IANA reales (`v10.4.5`), actualizó `verify_before_deploy.py`, sacó `.claude/settings.local.json` del control de versiones sin borrar la copia local, reparó manualmente una entrada truncada en `performance.json` de Railway, implementó la capa base de `postmortem.json`, movió `signals.json` / `traders_db.json` / `trader_history.json` al flujo persistente de Volume con bootstrap automático, añadió `/postmortem` para inspección rápida desde Telegram, preparó `v10.4.6` con backfill automático de postmortem y alertas de observabilidad persistentes, cerró `v10.4.7` bloqueando London en código para que no vuelva a comprarse por error, y remató `v10.4.8` afinando Telegram para que `traders` cruce por fecha exacta, `postmortem` no degrade etiquetas legacy y `detalle` muestre el último ciclo completo.
- **Estado final de la sesión 19:** versión activa `v10.4.8`, tests `182/182`, repo listo para deploy, DST robusto para futuros cambios de horario, observabilidad base de postmortem lista para crecer, pipeline de traders persistente en Volume, botón visible de `/postmortem`, alertas automáticas listas para avisar cuando haya suficiente muestra para revisar la lógica, London bloqueada operativamente en código y botones de Telegram principales ya refinados tras revisión manual.

### Sesión 31 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.6.2 (local, pendiente de deploy)
- **Objetivo de la sesión:** Blindar la alerta de bankroll bajo introducida en `v10.6.1`, evitar falsos positivos por fallo de API y dejar código/tests/docs alineados

- **Claude Code (Opus):**
  - No usado directamente en esta sesión
  - El cambio parte de una revisión crítica del trabajo previo firmado con Claude en `v10.6.1`

- **Codex:**
  - Revisó `v10.6.1` y detectó que la alerta de bankroll podía dispararse con `cash=0` por fallo de API aunque la cartera real no hubiera caído
  - Endureció `run_observability_alerts()` y `get_dashboard_alert_summary()` para exigir `cash_ok` y ausencia de `api_error`
  - Añadió `LOW_BANKROLL_RESET_MARGIN = $1.00` para rearmar la alerta al salir de la zona roja sin exigir recuperar hasta `2x` el umbral
  - Amplió `verify_before_deploy.py` hasta `348/348` con casos funcionales de trigger real, no-trigger por API incierta, reset con margen y visibilidad correcta en dashboard
  - Actualizó `agent_events.jsonl`, `CONTEXTO.md` e `HISTORIAL_SESIONES.md` para empaquetar el cambio como `v10.6.2`

- **Problemas detectados en trabajo previo:**
  - La alerta de bankroll bajo de `v10.6.1` mezclaba caída real de fondos con fallos temporales de API
  - El reset de la alerta solo ocurría al superar `LOW_BANKROLL_THRESHOLD * 2`, dejando la alerta demasiado “pegada” y sin rearmarse en recuperaciones parciales razonables

- **Estado final:**
  v10.6.2 local, 348/348 tests, alerta de bankroll más fiable en Telegram/dashboard y repo listo para push/deploy

### Sesión 32 — Investigación estratégica + preparación de v10.6.3

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** v10.6.2 (local + `origin/main`), sin cambio funcional todavía
- **Objetivo de la sesión:** investigar competidores/estrategia, contrastar Codex vs Claude y cerrar el siguiente bloque técnico antes de tocar producción

- **Codex:**
  - Investigó wallets, bots y tooling del ecosistema weather de Polymarket
  - Detectó y documentó que Polymarket usa Weather Underground en múltiples mercados de temperatura
  - Identificó el bug Dallas `KDAL vs KDFW`
  - Preparó `RESEARCH_CODEX_HANDOFF_2026-03-30.md` y la plantilla de comparación con Claude
  - Contrastó después el informe de Claude y creó `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`

- **Claude Code (Opus):**
  - Reforzó el hallazgo de Dallas con evidencia adicional
  - Señaló correctamente que la auditoría `forecast_vs_real` actual no valida contra la fuente real de resolución
  - Añadió `Degen Doppler` al mapa competitivo como referencia más directa

- **Conclusión compartida:**
  - `resolution fidelity first`
  - El siguiente bloque correcto no es “más modelo” ni “más ciudades”, sino `v10.6.3`: fix Dallas, capa formal de resolución y honestidad explícita en la auditoría actual

- **Estado final:**
  Repo documentado para arrancar una sesión nueva de implementación con contexto limpio y alcance acotado (`v10.6.3` sin tocar la lógica de trading).

### Sesión 33 — Implementación local de v10.6.3

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.3` local (`origin/main` sigue en `v10.6.2`)
- **Objetivo de la sesión:** ejecutar el bloque técnico acordado tras la investigación: Dallas `KDAL`, capa formal de resolución, honestidad explícita en la pseudo-auditoría y tests.

- **Codex:**
  - Corrigió `RESOLUTION_STATIONS["Dallas"]` de `KDFW`/Fort Worth a `KDAL`/Love Field
  - Añadió `RESOLUTION_ICAO` con `icao + wu_url` para las ciudades activas, las bloqueadas y el resto del mapping actual
  - Renombró la función de auditoría a `audit_check_open_meteo_forecast_drift()` y dejó explícito en docstrings/logs que compara forecast original vs forecast posterior de Open-Meteo
  - Mantuvo la clave legacy `forecast_vs_real` en `audit.json` por compatibilidad, pero dejó de registrar campos/mensajes como si fueran “real”
  - Amplió `verify_before_deploy.py` con checks específicos de Dallas, `RESOLUTION_ICAO`, y mensajes de auditoría sin `real=`
  - Aprovechó para hacer estable un test funcional viejo de `/traders` que dependía de fechas fijas ya pasadas

- **Problemas detectados en trabajo previo:**
  - Dallas seguía apuntando a la estación equivocada para una de las 4 ciudades activas
  - La nomenclatura `forecast_vs_real` inducía a interpretar como observación real algo que seguía viniendo del forecast endpoint de Open-Meteo
  - Faltaba una base declarativa mínima para empezar a alinear resolución sin tocar todavía la lógica de trading

- **Estado final:**
  `v10.6.3` local, `358/358` tests, trading/scheduling intactos y base de resolución más explícita para la siguiente iteración de truth layer.

### Sesión 34 — Implementación local de v10.6.4

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.4` local (`origin/main` sigue en `v10.6.3`)
- **Objetivo de la sesión:** convertir la capa declarativa de resolución en una auditoría observada separada usando NOAA NCEI, sin tocar trading ni scheduling.

- **Codex:**
  - Añadió `noaa_station_id` explícito en `RESOLUTION_ICAO` solo para Chicago, Atlanta, Buenos Aires y Dallas
  - Implementó `fetch_noaa_observed_max()` contra NOAA NCEI Access Data Service usando station IDs ya resueltos, no ICAO dinámico
  - Implementó `audit_check_resolution_truth(dl)` con clave nueva `observed_vs_forecast`
  - Dejó el framing explícito de `observed proxy` con `source="noaa_ncei"` y mantuvo `forecast_vs_real` solo como auditoría legacy Open-Meteo
  - Limitó la auditoría NOAA a las 4 ciudades activas y a fechas con lag mínimo de 2 días
  - Amplió `verify_before_deploy.py` con checks estructurales nuevos y tests funcionales de NOAA

- **Problemas detectados / matices:**
  - NOAA mejora mucho la observabilidad, pero no debe confundirse con la fuente real de settlement de Polymarket
  - Buenos Aires quedó confirmado con `87576099999` tras consultar NOAA HOMR y probar el endpoint `global-hourly`

- **Estado final:**
  `v10.6.4` local, `371/371` tests, observabilidad NOAA añadida como capa separada y trading/scheduling intactos.

### Sesión 35 — Implementación local de v10.6.5

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local (`origin/main` sigue en `v10.6.4`)
- **Objetivo de la sesión:** separar en el dashboard la nueva serie NOAA observada del bloque legacy para poder analizar el forecast sin mezclar fuentes ni romper la continuidad de trading.

- **Codex:**
  - Añadió `build_dashboard_forecast_quality()` para leer `audit.json -> observed_vs_forecast` y exponer `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos
  - Añadió `build_dashboard_legacy_forecast_drift()` para mantener visible `forecast_vs_real` como bloque histórico no comparable
  - Integró ambos bloques en `build_dashboard_snapshot()` sin tocar trading, scheduling ni auditorías
  - Actualizó `templates/dashboard.html` para renderizar `Calidad Forecast Observada (NOAA)` y `Drift Open-Meteo (historico - no comparable con NOAA)`
  - Amplió `verify_before_deploy.py` con checks estructurales, thresholds de muestra y tests funcionales del snapshot

- **Problemas detectados / matices:**
  - `observed_vs_forecast` necesita todavía 2+ días de lag y acumulación real para empezar a leer sesgo con muestra útil
  - El bloque legacy sigue siendo útil como histórico, pero queda marcado explícitamente como no comparable con NOAA

- **Estado final:**
  `v10.6.5` local, `386/386` tests, dashboard preparado para observar NOAA vs legacy sin tocar la lógica de trading.

### Sesión 36 — Sync de bankroll tras recarga manual

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local y `origin/main` en `v10.6.5`
- **Objetivo de la sesión:** alinear el fallback local de bankroll con la configuración real de Railway después de una recarga manual de fondos.

- **Codex:**
  - Confirmó que Railway sigue usando `BANKROLL=25.00`
  - Actualizó el fallback de `bot.py` de `$15.00` a `$25.00` para que el entorno local no vuelva a desalinearse de producción
  - Añadió un test en `verify_before_deploy.py` para fijar `BANKROLL default = 25.00`
  - Actualizó `CONTEXTO.md` e `HISTORIAL_SESIONES.md` con la recarga manual `+$14.99` y el sync posterior

- **Problemas detectados / matices:**
  - La inconsistencia no afectaba a producción mientras Railway siguiera inyectando `BANKROLL=25.00`, pero sí podía inducir a errores de lectura o pruebas locales
  - La recarga manual devuelve al bot a la zona de operación prevista para `MIN_BET=$1` y `MAX_EXPOSURE_PCT=40%`

- **Estado final:**
  `v10.6.5` sigue sin bump de versión, pero queda alineado entre código local, tests, contexto y configuración operativa real de Railway.

### Sesión 37 — Playbook operativo + guardrails de scoreboard

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local y `origin/main` en `v10.6.5`
- **Objetivo de la sesión:** convertir el error de desalineación entre docs y scoreboard en una mejora estructural del proceso.

- **Codex:**
  - Creó `OPERATIONS_PLAYBOOK.md` como protocolo específico separado del estado vivo del proyecto
  - Añadió `tools/append_agent_event.py` para registrar eventos del scoreboard sin editar `agent_events.jsonl` a mano
  - Endureció `verify_before_deploy.py` con checks de playbook, helper y consistencia entre la sesión documentada más reciente y `agent_events.jsonl`
  - Dejó `_sync_agent_events_seed()` con warning explícito si falla el merge del scoreboard en arranque
  - Sincronizó el scoreboard live para que sesiones 32-36 queden reflejadas también en Railway

- **Problema detectado:**
  - `CONTEXTO.md` e `HISTORIAL_SESIONES.md` estaban bien, pero el Dashboard seguía leyendo un `agent_events.jsonl` desfasado porque el proceso de cierre de sesión no obligaba a actualizar la capa máquina del scoreboard

- **Guardrails nuevos:**
  - protocolo escrito de inicio/cierre multiagente
  - helper seguro para eventos del scoreboard
  - test que falla si la sesión más reciente en docs no existe también en `agent_events.jsonl`

- **Estado final:**
  el sistema ya no depende solo de memoria manual: estado, historial, scoreboard y tests quedan unidos por un protocolo explícito. `verify_before_deploy.py` queda en `396/396`.

### Sesión 38 — Scoreboard limpio + regla de puntuacion

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local por encima de `origin/main` con hardening adicional del scoreboard
- **Objetivo de la sesión:** corregir la diferencia engañosa del scoreboard y fijar una regla explícita para que revisar sin delta no genere puntos.

- **Codex:**
  - Detectó que el scoreboard live estaba inflado por filas duplicadas y corruptas en `agent_events.jsonl` del Volume
  - Limpió el fichero live en Railway hasta dejarlo otra vez en `29` líneas canónicas
  - Endureció `load_agent_events()` para deduplicar eventos equivalentes por clave normalizada y no volver a inflar el ranking por acentos, símbolos o duplicados manuales
  - Añadió al `OPERATIONS_PLAYBOOK.md` la regla `validacion o aprobacion sin delta = 0 puntos o sin evento`
  - Amplió `verify_before_deploy.py` con un check de esa regla y un test funcional de deduplicación

- **Problema detectado:**
  - El scoreboard no dependía solo del scoring manual; también dependía de la higiene del `agent_events.jsonl` persistente del Volume
  - La vista live usa los últimos `30` eventos válidos; con duplicados de Codex y el límite activo, el panel expulsaba además un evento antiguo de Claude y exageraba la diferencia

- **Estado final:**
  el scoreboard live vuelve a una base limpia, el loader queda robusto frente a duplicados equivalentes y el protocolo ya deja claro que validar sin cambiar nada no debe generar puntos. `verify_before_deploy.py` sube a `397/397`.

### Sesión 39 — Research final Lean Six Sigma + foco NOAA en Telegram

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local lista para deploy, sin bump de versión
- **Objetivo de la sesión:** cerrar la investigación metodológica, traducir solo lo útil al playbook y mover el foco operativo diario hacia `measurement / resolution fidelity`.

- **Codex:**
  - consolidó el research en `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` con conclusión explícita: `recomiendo no adoptar`, salvo `FMEA-lite` y definiciones operativas mínimas;
  - actualizó `OPERATIONS_PLAYBOOK.md` con:
    - `premortem corto para cambios core`;
    - definición mínima de `fallo real del sistema`, `limitacion conocida` y `ruido de mercado`;
  - amplió `run_observability_alerts()` para enviar hitos NOAA one-shot sobre `observed_vs_forecast`:
    - primer caso global;
    - muestra mínima `>=3`;
    - muestra global útil `>=10`;
    - ciudad con primera muestra;
    - ciudad interpretable `>=3`;
  - añadió `/noaa` y `/observabilidad` en Telegram para leer `sample`, `MAE`, `bias`, cobertura y últimos casos sin abrir el dashboard;
  - mantuvo el menú principal sin poda agresiva tras revisar que el gap real era la falta de una vista específica, no el exceso de botones;
  - endureció `verify_before_deploy.py` con:
    - test de `/noaa`;
    - test de idempotencia de alertas NOAA;
    - check explícito de `state.setdefault("milestones", {})`.

- **Decisión operativa importante:**
  - el cuello de botella actual no es la lógica de trading, sino `measurement / resolution fidelity`;
  - por eso no se tocó `sigma`, `Kelly`, `MIN_EDGE`, exits ni menú principal;
  - el objetivo inmediato pasa a ser observar si NOAA se puebla de verdad en Railway y distinguir mejor `fallo real` vs `limitacion conocida`.

- **Estado final de la sesión:**
  `v10.6.5` queda lista para deploy con foco explícito en fidelity, Telegram ya tiene vista dedicada `/noaa` y la suite sube a `416/416`.

### Sesión 41 — v10.6.6 allowlist ACTIVE_TRADING_CITIES

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.6` local lista para push/deploy
- **Objetivo de la sesión:** corregir el bug #15 para que el bot no vuelva a abrir posiciones nuevas en ciudades sin validación NOAA/WU, manteniendo intacta la gestión de posiciones ya abiertas.

- **Codex:**
  - añadió `ACTIVE_TRADING_CITIES` con default `Chicago,Atlanta,Dallas,Buenos Aires`;
  - insertó un filtro adicional en el scan: si la ciudad no está en el allowlist, no entra en candidatos para BUY;
  - dejó trazabilidad explícita en `decisions.log` con `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`;
  - mantuvo `manage_positions` sin cambios, para no tocar SL/TP/reeval de posiciones ya abiertas;
  - actualizó `verify_before_deploy.py` con checks estructurales del allowlist y alineó el bump de versión a `v10.6.6`;
  - conservó la prueba de idempotencia NOAA ya existente como guardrail activo.

- **Resultado operativo:**
  - el universo de entradas nuevas queda restringido a las 4 ciudades con monitoreo NOAA;
  - el bug de NYC/Munich/Seoul/Tokyo por blacklist incompleta queda corregido;
  - la suite sube a `419/419`.

### Sesión 42 — v10.6.7 dashboard estado por ciudad

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.7` local validada, pendiente de push/deploy
- **Objetivo de la sesión:** hacer visible en el dashboard, sin tocar la lógica de trading, en qué estado está cada ciudad desde el punto de vista de operativa real, cobertura NOAA y evidencia histórica.

- **Codex:**
  - añadió `build_dashboard_city_observation()` para cruzar `ACTIVE_TRADING_CITIES`, `BLOCKED_CITIES`, `observed_vs_forecast` y `get_city_accuracy()`;
  - incorporó el bloque nuevo al snapshot del dashboard sin mezclarlo con el builder NOAA puro;
  - sustituyó la lista simple de cobertura por una tabla `Estado de observacion por ciudad` con columnas de `Trading`, `NOAA`, `Historico` y `Estado actual`;
  - dejó la tabla deliberadamente descriptiva: muestra `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` o `Sin observabilidad`, pero no promociona ciudades automáticamente;
  - endureció `verify_before_deploy.py` con:
    - check estructural del builder nuevo;
    - check del bloque nuevo en `dashboard.html`;
    - test funcional de la tabla para `Chicago`, `London` y `New York City`;
    - test de snapshot para asegurar que `city_observation` llega al dashboard;
  - subió la versión a `v10.6.7`.

- **Resultado operativo:**
  - el dashboard ya permite ver de un vistazo qué ciudades están realmente operando, cuáles siguen bloqueadas, cuáles solo tienen valor histórico y cuáles siguen sin observabilidad;
  - esto no desbloquea ciudades ni cambia BUY/SELL, pero prepara mejor la decisión futura sobre `watchlist / shadow / canary`;
  - la suite sube a `426/426`.

---

## Historial de trades (33 entradas en performance.json)

| # | Ciudad | Lado | Coste | Resultado | PnL | Motivo | Fecha |
|---|--------|------|-------|-----------|-----|--------|-------|
| 1 | Chicago | YES | $2.38 | $7.72 | +$3.96 | Take-profit +85% | 25 mar |
| 2 | Ankara | YES | $2.50 | $0 | -$1.90 | LOSS_TOTAL | 26 mar |
| 3 | Atlanta | YES | $4.04 | $6.71 | +$2.60 | Take-profit +63% | 27 mar |
| 4 | London | NO | $2.50 | ~$0.22 | -$2.25 | Pérdida (WU vs OMA) | 26 mar |
| 5 | Ankara | NO | $2.50 | $4.24 | +$1.74 | WIN resolución | 26 mar |
| 6 | Chicago | YES | $2.50 | $11.59 | +$9.98 | WIN resolución +619% | 26 mar |
| 7 | Miami | YES | $2.20 | $0 | -$2.14 | LOSS_TOTAL | 26 mar |
| 8 | Shanghai | NO | $1.43 | $2.52 | +$1.09 | WIN resolución | 27 mar |
| 9 | Seattle | YES | $2.50 | $0.96 | -$0.42 | Stop-loss | 28 mar |
| 10 | Wellington | NO | $2.26 | $4.48 | +$2.24 | WIN resolución | 28 mar |
| 11 | Toronto | NO | $1.68 | $0 | -$1.71 | LOSS_TOTAL | 27 mar |
| 12 | Madrid | YES | $4.89 | $2.36 | -$1.95 | Stop-loss (bug #3) | 28 mar |
| 13 | Buenos Aires | NO | $1.62 | $2.21 | +$0.80 | Take-profit +52% | 28 mar |
| 14 | Dallas | YES | $2.50 | $2.44 | +$0.26 | Re-evaluación | 28 mar |
| — | Tel Aviv | NO | $2.46 | $0 | -$2.46 | LOSS_TOTAL | 28 mar |
| — | Paris | NO | $0.58 | $0 | -$0.58 | LOSS_TOTAL | 28 mar |
| — | Miami | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Chicago | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Dallas | YES | $2.50 | abierta | — | En cartera | 28 mar |

---

## Ciclos ejecutados

| Ciclo | Hora UTC | Compras | Ventas | Nota |
|-------|----------|---------|--------|------|
| Extra | 25 mar 16:49 | Chicago YES | — | Bug #11 — deploy entre ciclos |
| 2 | 25 mar 23:00 | — | Chicago YES TP +85% | OK |
| 3 | 26 mar 08:00 | Ankara YES/NO, London NO, Atlanta YES | — | OK |
| 4 | 26 mar 16:00 | Chicago YES, Atlanta YES, Miami YES, Shanghai NO | — | OK |
| 5 | 26 mar 23:00 | Seattle YES, Buenos Aires NO | — | OK |
| 6 | 27 mar 08:00 | — | Atlanta YES TP +63% | OK |
| 7 | 27 mar 16:00 | Madrid YES, Chicago YES 40-41°F, Toronto NO | — | OK |
| 8 | 27 mar 23:00 | Madrid YES (BUG #3), Wellington NO | Seattle YES SL | Madrid amplificada |
| 9 | 28 mar 08:00 | Dallas YES, Miami YES | Madrid YES SL, Buenos Aires TP | OK |
| 10 | 28 mar ~11:01 | Miami YES | — | Deploy v10.4 — Bug #3 bloqueó duplicados ✅ |
| 11 | 28 mar 16:00 | Chicago YES, Dallas YES | Dallas reeval, Tel Aviv/Paris LOSS_TOTAL | v10.4.2 |
| 12+ | 28 mar 23:00+ | — | — | v10.4.3 activo, cycles_history.jsonl acumula |

---

## Observaciones estratégicas

### Open-Meteo vs Weather Underground
London ha producido pérdidas seguidas porque Open-Meteo predice una temperatura y Weather Underground (fuente real de Polymarket) resuelve con otra. **No apostar en London hasta resolver.** Desde `v10.4.7`, London está bloqueada en el código del bot.

### Lógica de salida — casos reales
Con ~15 trades cerrados no hay suficiente evidencia estadística para cambiar la lógica. La solución correcta es un monitor ligero intra-ciclo (Fase 2, cuando haya 30+ trades limpios). Desde `v10.4.6`, Telegram avisará automáticamente cuando se alcance ese umbral para abrir una sesión de análisis/coding con Opus.

---

## Arquitectura de observabilidad — fases

### Fase 1 — ✅ Implementada:
- Persistencia Railway Volume, cycles_history.jsonl, cycle_summary.json ✅
- Bugs #3-#14 corregidos, 173 tests ✅
- Claude Code instalado y funcional ✅

### Fase 1.5 — ✅ Implementada (sesión 19):
- Rediseño completo Telegram (7 botones + /info) ✅
- Bug #13 paginación ✅
- Ciclos persistentes entre deploys ✅
- Limpieza del repo (17 archivos eliminados) ✅
- performance.json fusionado con historial completo (33 trades) ✅
- DST robusto con `ZoneInfo` y zonas IANA reales ✅
- `postmortem.json` base implementado ✅
- `signals.json`, `traders_db.json` y `trader_history.json` persistidos en Volume ✅
- `/postmortem` disponible para inspección rápida desde Telegram ✅
- backfill automático de `postmortem.json` desde `performance.json` ✅
- `alerts_state.json` + alertas Telegram de observabilidad ✅
- London bloqueada operativamente en código ✅
- Refinamiento Telegram tras revisión manual de botones (`/traders`, `/postmortem`, `/detalle`) ✅

### Fase 2 — ✅ Implementada (sesión 20):
- Monitor intra-ciclo SL/TP cada 90min (v10.5.1) ✅
- City accuracy tracker con alertas automáticas (v10.5.2) ✅
- Sigma recalibrada tras análisis de 17 trades cerrados (v10.5.0) ✅
- Smart alerts: drawdown, scaling readiness, win rate (v10.5.0) ✅

### Fase 2.5 — Próxima:
- Resolver acceso a Weather Underground API (IBM Trial falló, buscar alternativas)
- Ampliar `postmortem.json` con análisis más rico al resolver cada mercado

### Fase 3 — Cuando escale:
- Dashboard web (Streamlit o HTML estático)

---

## Infraestructura

### Railway:
- **Región:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403)
- **Volume:** Montado en `/app/data` — archivos persisten entre deploys
- **Variable DATA_DIR:** `/app/data`

### Acceso SSH:
```bash
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "comando"
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "ls -l /app/data"
```

### Higiene Railway CLI:
- Usar `tools/railway_safe.ps1` para `status`, `logs`, `ssh`, `domain` y lecturas del Volume.
- Si Railway entra en bucle de relogin o pierde el enlace del proyecto, usar `tools/railway_auth_repair.ps1 doctor`, luego `reset`, después `launch-login -Browserless` y, si el login deja `projects = {}`, rematar con `restore-links`.
- Hacer `railway login` solo en una shell interactiva del usuario.
- Validación mínima del 1 de abril de 2026: `whoami`, `status` y `logs -s polymarket-bot -n 20` ya responden otra vez vía wrapper.
- Si Codex necesita ejecutar Railway despues del login y la CLI puede refrescar auth, usar permisos fuera del sandbox para que pueda tocar `%USERPROFILE%\.railway\config.json`.

### Claude Code:
- Instalado en `C:\Projects\polymarket-bot`
- Para tests: `$env:PYTHONIOENCODING="utf-8"` antes de ejecutar

### Trabajo multi-agente:
- `CONTEXTO.md` debe mantenerse como foto actual compartida entre ChatGPT, Codex, Claude.ai y Claude Code.
- `HISTORIAL_SESIONES.md` debe usarse como memoria histórica append-only para no perder qué sesiones ya existieron y qué se corrigió en cada etapa.
- Antes de cada push relevante, actualizar ambos archivos si cambió algo material del sistema.
- Antes de cerrar una sesión relevante, anotar qué herramienta hizo los cambios finales y qué corrigió de sesiones previas.

### Workflow de deploy:
```bash
python verify_before_deploy.py   # todos los tests deben pasar
# actualizar CONTEXTO.md si cambió el estado actual
# actualizar HISTORIAL_SESIONES.md si hubo una sesión/hito nuevo
git add .
git commit -m "v10.X.X: descripción"
git push
# Railway despliega automáticamente
# Verificar variables: DATA_DIR, MIN_BET, DRY_RUN
```

---

## Ideas pendientes (no implementar hasta validar)

1. ~~**Monitor ligero intra-ciclo:**~~ ✅ Implementado en v10.5.1
2. **Weather Underground:** IBM Trial no accesible. Opciones: PWS key ($30-50 estación), scraping (frágil), o seguir con accuracy tracker
3. **Dashboard web:** Fase 3 cuando haya 50+ trades
4. **Enriquecer `/postmortem`:** filtros por ciudad/estado/últimos N cierres
5. **Ampliar `postmortem.json`** con más campos de forecast y comparación resolución vs decisión
6. **Aumentar frecuencia ciclos:** [8,16,23] → [6,10,14,18,22]

---

## Resultados NOAA station verification (sesión 83, 6 abr 2026)

- **Contrato ejecutado:** `docs/noaa-station-verification-contract.md`
- **Archivos tocados:** `bot.py` (`RESOLUTION_ICAO`, `OBSERVED_AUDIT_CITIES`) y esta sección al final de `CONTEXTO.md`
- **Validación usada:**
  - `isd-history.csv` para resolver `noaa_station_id` por ICAO
  - `ghcnd-stations.txt` + `daily-summaries/TMAX` para `noaa_daily_station_id`
  - criterio de aprobación daily: `>=30` TMAX entre `2025-10-01` y `2026-03-31`

### Ciudades añadidas a NOAA observado

- `New York City` → `72503014732` + `USW00014732`
- `Miami` → `72202012839` + `USW00012839`
- `Seattle` → `72793024233` + `USW00024233`
- `London` → `03768399999` + `UKE00107650` (fallback daily en Heathrow; `EGLC` no devolvió TMAX útil)
- `Paris` → `07157099999` + `FRM00007149` (fallback daily en Orly)
- `Munich` → `10866099999` + `GMM00010870`
- `Madrid` → `08221099999` + `SPE00120278`
- `Milan` → `16066099999` + `SZ000009480`
- `Tel Aviv` → `40180099999` + `ISE00105694`
- `Ankara` → `17128099999` + `TUM00017130`
- `Wellington` → `93436000488` + `NZM00093439`
- `Tokyo` → `47671099999` + `JA000047670`
- `Seoul` → `47113199999` + `KS000047112`
- `Shanghai` → `58321199999` + `CHM00058362`
- `Chengdu` → `56294099999` + `CHM00056187`

### Ciudades sin NOAA daily verificada

- `Toronto`, `Beijing`, `Hong Kong`, `Singapore`, `Warsaw`, `Taipei`, `Shenzhen`, `Chongqing`, `Wuhan`, `Lucknow`, `Sao Paulo`
- Motivo común: `isd-history.csv` sí resolvió el ICAO, pero el candidato GHCND local/regional no devolvió `>=30` registros `TMAX` en `2025-10-01..2026-03-31`

### Nota operativa

- El endpoint `global-hourly` devolvió datos reales para `2025-01-01..2025-03-31` en las estaciones ISD verificadas, pero devolvió vacío para `2026-01-01..2026-03-31` incluso en estaciones ya buenas como `KORD` y `KLGA`, así que la promoción en esta sesión se apoyó en `isd-history.csv` + `daily-summaries`.
- Para mantener compatibilidad con la suite actual, `bot.py` conserva una ancla literal legacy de `OBSERVED_AUDIT_CITIES` aunque el set real ya incluye las 19 ciudades con NOAA observado activo.

### Seguimiento London/Milan (sesión 84, 6 abr 2026)

- `London -> UKE00107650` revalidada contra `daily-summaries`: `149` registros `TMAX` entre `2025-10-01` y `2026-03-31`, rango `2.5°C..21.3°C`, coordenadas `51.4789, 0.4489` (`HEATHROW`), a ~`27.8 km` de `EGLC`.
- `Milan -> SZ000009480` revalidada: `151` registros `TMAX`, rango `3.8°C..21.9°C`, pero corresponde a `LUGANO` (`46.0, 8.9667`), Suiza, a ~`45.0 km` de `LIMC`.
- Se buscaron candidatos italianos en `ghcnd-stations.txt` cerca de `LIMC` (`ITM00016064 CAMERI`, `ITE00100554 MILAN` y radio ampliado hasta `300 km`), pero ninguno devolvió `TMAX` útil en ese periodo.
- Decisión: no cambiar `bot.py` en esta sesión; London queda confirmada y Milan se mantiene como mejor daily disponible hasta encontrar una estación italiana con cobertura real.
- Siguiente paso lógico: observar en dashboard/API que las 19 ciudades configuradas empiecen a poblar `observed_vs_forecast`; el valor operativo ahora viene de acumular muestra, no de seguir resolviendo IDs.
**Última actualización:** 11 de abril de 2026 (Sesión 138 — clasificación operativa de collision barrier)
**Sesión 138 (11 abr 2026, Codex):** se resuelve la pregunta abierta del handoff post-Opus/post-Phase-6 sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds ni throughput: qué parte del `collision_count=17` bloquea de verdad una futura discusión operacional.
- **Readout escrito nuevo:** se crea `docs/collision-barrier-readout-post-opus-phase6-2026-04-11.md`, que descompone las `17` colisiones en tres buckets: ruido aceptable por diseño (`shadow` efectivo vs `cross=untracked`), drift documental/cross stale que contamina lectura futura (las `5` canaries efectivas que `cross` sigue viendo como `shadow`) y colisiones que sí deben considerarse blockers reales antes de una decisión (`Dallas` por `env active` vs `runtime shadow`, más `Chicago` y `Buenos Aires` por `cross active` vs `effective shadow`).
- **Conclusión operativa nueva:** el bloqueo real ya no es “hay 17 colisiones” en abstracto, sino un subconjunto mucho más pequeño donde siguen existiendo claims incompatibles sobre tradabilidad real o sobre ciudades que probablemente entren en la próxima discusión de policy/throughput. El bucket grande `shadow` vs `untracked` queda explicitado como drift analítico visible, no como bloqueo operativo por sí solo.
- **Insight de guardrail:** el readout deja documentado que `collision_count` funciona hoy como alarma conservadora, pero no como diagnóstico suficiente de severidad; incluso `Atlanta` muestra que puede haber relevancia operativa (`effective_mode=canary`, `cross=unknown`) que no suma colisión. El siguiente paso seguro ya no es tocar monetización, sino decidir si conviene una mini capa read-only para distinguir `blocking_operational_collision` de ruido documental antes de cualquier discusión futura.
- **Última actualización:** 11 de abril de 2026 (Sesión 139 — Phase 6.5 collision severity hardening)
**Sesión 139 (11 abr 2026, Codex):** se implementa la mini `Phase 6.5` recomendada por la review adversarial post-Opus para endurecer la barrera de colisiones sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, bankroll ni `exact/range`.
- **Segunda capa de severidad:** `tools/runtime_policy_effective_view.py` deja de tratar todas las colisiones como equivalentes y pasa a clasificarlas en `collision_noise`, `documented_drift` y `blocking_operational_collision`. La `effective view` resultante ya no deja el preflight rehén de un contador ciego.
- **Cross alineado con effective view:** `tools/reference_trader_city_market_cross.py` deja de arrastrar claims legacy de policy cuando existe `data/runtime_policy_effective_view.json`; su `policy_mode` se deriva de `effective_mode` y conserva `policy_source`. Con eso desaparece el drift fuerte del bloque canary y los claims `active` legacy de `Chicago` / `Buenos Aires`.
- **Preflight operational endurecido pero más preciso:** `tools/system_alignment_check.py` deja de bloquear por `collision_count > 5` y pasa a bloquear por `blocking_operational_collision_count > 0`. Tras regenerar `reference_trader_city_market_cross`, `runtime_policy_effective_view`, `city_validation_ledger.runtime_import` y los `latest`, el estado queda en `observe => ok=7, warning=1, error=0` y `operational => ok=7, warning=0, error=1`. El `runtime_ledger` pasa a `ok` con `drift_flag_counts={}`.
- **Blocker real aislado:** la barrera operacional queda reducida a un único blocker duro: `Dallas` (`env_declared_mode=active` vs `runtime_policy_mode=auto_shadow`). El resto queda clasificado como drift visible no bloqueante por sí solo. Se documenta el cambio en `docs/phase6-5-collision-severity-hardening-2026-04-11.md` y se actualizan `docs/decision-preflight-rules-2026-04-11.md` y `docs/system-alignment-lean-roadmap-2026-04-10.md`.
**Última actualización:** 11 de abril de 2026 (Sesión 140 — Dallas claim cleanup)
**Sesión 140 (11 abr 2026, Codex):** se limpia el ultimo claim declarativo que mantenía a `Dallas` como `blocking_operational_collision` sin tocar `bot.py`, policy live, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`.
- **Raíz real del blocker:** el choque no venía de runtime live sino de la capa read-only `tools/runtime_policy_effective_view.py`, que seguía inyectando `DEFAULT_ACTIVE_CITIES = "Dallas"` como fallback local cuando no había snapshot explícito del env. Eso fabricaba `env_declared_mode=active` aunque la verdad operativa ya fuera `shadow`.
- **Corrección mínima aplicada:** `DEFAULT_ACTIVE_CITIES` pasa a vacío para que la herramienta no convierta un claim auditado heredado en verdad declarativa por defecto. Si una sesión quiere evaluar listas env explícitas, todavía puede pasarlas como argumentos.
- **Estado nuevo tras regenerar artefactos:** `data/runtime_policy_effective_view.json` y `docs/runtime_policy_effective_view_latest.md` quedan con `Dallas => env=shadow, runtime=auto_shadow, cross=shadow, effective=shadow`. `collision_count` baja `4 -> 3`, desaparece `blocking_operational_collision`, y el preflight queda en `observe => ok=7, warning=1, error=0` y `operational => ok=7, warning=1, error=0`.
- **Readout corto nuevo:** se crea `docs/dallas-claim-readout-2026-04-11.md` para dejar explícito qué se limpió, por qué el blocker no era runtime real y qué ruido visible sigue quedando (`Atlanta` como `documented_drift`; `lucknow` y `sao paulo` como `collision_noise`).
**Última actualización:** 13 de abril de 2026 (Sesión 171 — fix encoding ° en signals.json)
**Sesión 171 (13 abr 2026, Sonnet):** bug fix de codificación de una línea en `trader_analyzer.py`.
- **Bug:** `api_get()` llamaba `json.loads(resp.read())` sin encoding explícito. En Windows con CP437, los bytes UTF-8 `\xC2\xB0` del símbolo `°` se decodificaban como CP437, produciendo `┬░` (U+252C U+2591) en `signals.json`.
- **Fix:** `json.loads(resp.read().decode("utf-8"))` en `trader_analyzer.py:103`.
- **Validación:** `verify_before_deploy.py` → 643/643.

**Última actualización:** 16 de abril de 2026 (Sesión 183 — shadow→NOAA funnel hardening)
**Sesión 183 (16 abr 2026, Codex):** se endurece el embudo `shadow -> NOAA -> WR observado` para dejar de perder evidencia antes de poder usarla para monetización, sin tocar trading core, scheduler, Kelly, exits ni policy live.
- **Auditoría del embudo con evidencia live importada:** sobre `data/runtime_import/shadow_city_tracking.json` y `audit.json`, había `30` `edge_hit=true` recientes, pero `28` caían como `otro` por el parser legacy, `directional_history` retenía solo `2`, y `0` señales llegaban a resolverse con NOAA. El cuello no estaba solo en el join final, sino antes: parser incompleto + fuente NOAA no durable para señales shadow.
- **Parser shadow endurecido:** `_shadow_condition_code()` pasa a reutilizar `parse_temperature_question()` cuando puede, cubriendo correctamente `or higher` / `or below`. Además se añade `_extract_threshold_canonical()` para normalizar umbrales a Celsius con tolerancia a encoding raro del símbolo `°`, de modo que preguntas como `19°C or higher`, `13°C or below` o `74°F or higher` ya no quedan con `threshold=None`.
- **Persistencia shadow alineada:** `_shadow_signal_signature()` y `_build_shadow_signal_record()` pasan a usar el umbral canónico, así que `directional_history` deja de firmar o persistir señales válidas con umbral nulo por culpa del parser legacy.
- **NOAA para shadow deja de depender solo de 12 ciclos recientes:** `_get_noaa_candidate_dates()` ya no usa únicamente `_iter_recent_noaa_cycle_markets(limit_cycles=12)`. Primero intenta reconstruir candidatos durables desde `load_shadow_city_tracking().directional_history` y solo cae al fallback de `scanned_markets` recientes si no encuentra nada. Con eso, una señal shadow elegible por lag NOAA deja de desaparecer del radar solo porque pasaron suficientes ciclos.
- **Dashboard y alertas alineados con base resoluble real:** `_build_shadow_noaa_resolution_stats()` expone también `matched`, y tanto `build_dashboard_road_to_real()` como `get_dashboard_alert_summary()` pasan a derivar `directional_signals`, `resolved` y `win_rate` desde esa capa en vez de usar `shadow.summary.edge_hits` como proxy mezclado. Se elimina así la lectura engañosa donde el numerador y el denominador del `WR observado direccional` salían de bases distintas.
- **Higiene adicional detectada durante la implementación:** `build_dashboard_city_decisions()` tenía una referencia latente a `shadow_summary` sin inicializar; se corrige para no dejar un `NameError` oculto en contextos aislados.

**Última actualización:** 22 de abril de 2026 (Sesión 223 — INTRA_SL_INTERVAL 60→20 min)

**Sesión W17-Opus (17 abr 2026, Opus + Sonnet):** revisión estratégica quincenal + ejecución completa del bloque W17 en una sola sesión. Causa raíz del throughput bajo identificada por primera vez con datos concretos. Bloque ejecutado sin pasos manuales para el usuario.

### Diagnóstico ejecutivo (Opus)

- **Colapso de throughput con v10.6:** pre-Apr6 `4.6 edges/ciclo` y `0.98 buys/ciclo`; post-Apr6 con canary gate `0.1 edges/ciclo` y `0.05 buys/ciclo`. `71` ciclos (`11` días) con solo `7` buys desde el 6 de abril.
- **Causa raíz del colapso:** `condition_filtered` mata `~47%` de candidatos cada ciclo (exact/range bloqueados). El modelo gaussiano sobreestima P(YES) para exact/range: bot ve `our_prob~40%`, mercado cotiza `18%` → edge ilusorio → bot pierde. WR real del bot en exact YES: `0%` (`26` trades). Traders en esos mismos mercados: `76% WR`, van `68% NO`.
- **PnL real por condición:** `at_or_above` +$0.97 (60% WR); `exact` -$9.26 (29% WR); `range` -$23.94 (9% WR).
- **48% de cierres son `micro_position_unsellable`:** `29/61` posiciones sin poder venderse.
- **Mapa de cuellos:** (1) modelo exact/range roto [CRÍTICO], (2) position management [ALTO], (3) whitelist canary estrecha [MEDIO], (4) slot 23h sin valor [BAJO].

### Cambios implementados (bot.py)

- **S2 — Whitelist canary ampliada:** `QUALITY_TRADER_CITIES_WHITELIST` default + `Atlanta, London, New York City, Munich`. Railway también actualizado con la lista completa.
- **C1-fix — YES exact/range floor:** bloque nuevo antes de `_effective_min_edge`: si `exact_range_canary` y `side == "YES"` y `our_prob < 0.65` → skip con `skip_reason_detail="exact_range_yes_low_confidence"`. Habría bloqueado los `23` YES losses históricos (avg `our_prob=40.1%`) manteniendo los `6` NO wins (`our_prob≥78%`).
- **Seoul auto-canary promotion bug fix:** guardia `city not in auto_blocked` añadida en `sync_city_policy_state()` línea `6334`. Bug: ciudades en `auto_blocked` con NOAA proxy devuelven `"shadow"` desde `get_effective_city_mode()` → la guardia de promoción pasaba → Seoul entraba incorrectamente en `auto_canary_cities`.
- **W17 observation alert (`maybe_run_w17_observation_alert`):** one-shot que dispara el `2026-04-20` o después. Lee `cycles_history.jsonl` desde `2026-04-17T18:00`, calcula métricas post-bloque (`markets_evaluated`, `with_edge`, `buys`) y envía Telegram con prompt completo listo para pegar en Codex/Sonnet.

### Railway actualizado

- `QUALITY_TRADER_CITIES_WHITELIST` → lista completa con 4 ciudades canary añadidas.
- `SCHEDULE_DISABLED_HOURS_UTC=23` → slot 23h apagado live.

### Docs creados

- `docs/strategic-review-opus-2026-04-17.md` — revisión estratégica completa.
- `docs/execution-plan-w17-2026-04-17.md` — plan de ejecución W17, bloque completo marcado como completado.
- `docs/c1-autopsy-exact-range-2026-04-17.md` — autopsia exact/range con causa raíz + fix propuesto.

### Estado del sistema post-sesión W17

- `bot.py` versión `v10.6.19` (aproximado; 4 commits push al `main`).
- `verify_before_deploy.py` pasando en `702/702` antes del último push.
- Observación activa: criterios de éxito a medir entre 17-24 de abril → `markets_evaluated≥25`, `with_edge≥0.5`, `buys≥0.3` por ciclo.
- Próxima revisión Opus: semana del 24 de abril de 2026.

**Sesión 223 (22 abr 2026, Sonnet):** reducción del intervalo intra-SL de 60 a 20 minutos.
- **Contexto:** SL de Shanghai No disparó en ciclo 04:00 UTC a -35.2% pese a que el umbral es -25%. Gap de polling: la posición estaba por encima de -25% en el check anterior y cayó ~10pp adicionales en los 60 min siguientes.
- **Fix:** `INTRA_SL_INTERVAL` default `"60"` → `"20"` en `bot.py:365`. Con checks cada 20 min el slippage máximo vs. el umbral baja de ~35pp a ~10pp.
- **Sin cambio en `STOP_LOSS_PCT`** (-25% sigue siendo el umbral correcto).
- `verify_before_deploy.py` no requiere nuevos tests (cambio de constante numérica sin lógica nueva).
- **Validación local:** `python -m py_compile bot.py` OK. `verify_before_deploy.py` deja de fallar por la lógica del funnel, pero el harness aún cae en Windows por `Access denied` al tocar un directorio temporal (`[WinError 5]` sobre `%TEMP%`), así que queda pendiente una pasada limpia del verificador o aislar ese bug del harness antes de usarlo como gate final de deploy.

**Última actualización:** 22 de abril de 2026 (Sesión 224 — INTRA-REEVAL shadow-log)

**Sesión 224 (22 abr 2026, Opus diseño + Sonnet implementación):** re-evaluación condicional en el monitor intra-ciclo, en modo shadow-log (no vende, solo alerta) para alimentar con evidencia propia la próxima decisión.
- **Problema atacado:** hoy el monitor intra (cada 20 min) solo mira SL/TP. Una posición puede pasar de +20% a -50% entre ciclos principales (4h) sin que el edge justifique mantenerla. Histórico: 1 caso real claro (Atlanta YES +25% → -56% por SL).
- **Diseño (Opus):** A-only + shadow-log. Un único disparador (drift ≥10pp entre `cur_price` y `entry_context.price`) + cooldown 80 min por posición + edge threshold -3% (idéntico al ciclo principal). En shadow, si edge<-3% → Telegram breve (rate-limit 1/h) + estado persistente en `data/intra_reeval_state.json`, NO vende. A los 7 días del primer trigger, alerta one-shot con resumen para decidir promoción.
- **Cambios (Sonnet):** 5 ENV vars nuevas (`INTRA_REEVAL_ENABLED/SHADOW_MODE/PRICE_DRIFT_PP/COOLDOWN_MIN/EDGE_THRESHOLD`), helper puro `recompute_position_edge` extraído del CHECK 3 de `manage_positions` (byte-compatible), integración opt-in en `intra_cycle_sl_check` después del bloque SL/TP, alerta one-shot `maybe_run_intra_reeval_review_alert` wired en `run_alerts`.
- **Verificación:** `verify_before_deploy.py` → 795/795 (19 checks estructurales + 9 funcionales nuevos).
- **Railway pendiente (acción usuario):** añadir `INTRA_REEVAL_ENABLED=1` y `INTRA_REEVAL_SHADOW_MODE=1` (el resto usa defaults). Flip a `SHADOW_MODE=0` solo tras review one-shot a los 7 días.
- **Próximo hito auto-disparado:** en 7 días desde el primer trigger shadow llegará un Telegram de "Review INTRA-REEVAL" con datos agregados y prompt listo para la siguiente sesión.

**Última actualización:** 26 de abril de 2026 (Sesión 242 — cierre operativo slot 04h validated/keep)
**Sesión 242 (26 abr 2026, Codex):** se cierra la alerta `Slot monetization review` recibida para `04h UTC` como decisión operativa, no como cambio de lógica. Evidencia: `5 ciclos`, `same_day_candidates=106`, `same_day_edges=3`, `same_day_selected=3`, `same_day_buys=2`, `buy_rate=66.67%`; reject reasons dominantes `price_out_of_range=663`, `condition_filtered=86`, `blocked_city=22`; execution reject residual `buy_min_size=1`. Decisión: `04h UTC` queda `validated/keep`; no se toca bot.py, scheduler, NOAA, reglas de entrada/salida.

**Última actualización:** 26 de abril de 2026 (Sesión 243 — cierre definitivo 11 posiciones legacy stale + SL retro split por tipo)
**Sesión 243 (26 abr 2026, Sonnet):** cierre definitivo de 11 posiciones legacy stale (Ankara ×2, London, Miami, Shanghai, Toronto, Atlanta, Buenos Aires, Seattle, Wellington, Madrid — resolution_date 26-29 mar 2026, sin snapshots ni evidencia) con investigación previa de outcomes reales en Polymarket.
- **Auto-close wired:** `bot.py` añade `close_expired_legacy_positions()` + `maybe_close_expired_legacy_positions(state)` (hook antes del briefing diario). Clave: usa `EXPIRED_UNVERIFIED` con `pnl_cash=None` (no distorsiona P&L ni WR) y `reconciliation_needed=True`; no LOSS_TOTAL especulativo.
- **Reconciliación con outcomes reales:** `tools/reconcile_legacy_stale_with_outcomes.py` investiga los 11 outcomes reales en Polymarket (Wunderground, NWS, MetService, AEMET, SMN) y parchea `trade_lifecycle.json` + `postmortem.json` en Railway con el resultado real: 6 RESOLVED_WIN, 5 LOSS_TOTAL. Ejecutado en Railway (11/11 TL + 11/11 PM con backups `.bak_session_243`).
- **SL retrospectiva:** RIGHT=5, WRONG=8, UNKNOWN=10 (23 total). WRONG dobla a RIGHT; veredicto `seguir monitorizando`. `maybe_run_sl_retrospective(state)` corre diariamente y envía Telegram automáticamente.
- **SL retro split por tipo:** `tools/sl_retrospective.py` añade `_summarize_type()` y muestra en el Telegram el desglose separado entre `stop_loss` (ciclo principal) y `stop_loss_intra` (intra-ciclo), para poder evaluar cada mecanismo de forma independiente.
- `verify_before_deploy.py` → **847/847**.

**Última actualización:** 28 de abril de 2026 (Sesión 259/260 — auditoría blocked signals + Warsaw observación pasiva)
**Sesión 259 (28 abr 2026, Sonnet):** auditoría read-only de alerta ACTION `blocked signals fuera de whitelist` (105 resueltas, 104W, WR 99%). Top 4 fuera de whitelist: Lucknow 19, Warsaw 17, Beijing 17, Chongqing 17. Confirmado split correcto `bot.py:8441-8442`. Warsaw flaggeada como candidata prioritaria para observación.
**Sesión 260 (28 abr 2026, Sonnet):** Warsaw confirmada con SSH a Railway. Añadida a `OBSERVED_AUDIT_CITIES`.
- **Warsaw Railway confirmado:** n=17, WR=100%, 5 traders (Dimpled-Boy×6, Thrifty-Original×4, Entire-Hood×3, Jubilant-Spending×2, Pricey-Score×2), 8/17 has_consensus, exact×17, avg_price=0.677, fechas 2026-04-13..2026-04-21 repartidas.
- **Cambio:** `Warsaw` añadida a `OBSERVED_AUDIT_CITIES` en `bot.py`. Efecto: observación pasiva de mercados Warsaw en cada ciclo (scanned_markets ledger). Sin compras, sin whitelist, sin canary/active, sin cambio de trading core.
- **Guardrail anti-auto-canary:** `_city_requires_manual_proxy_canary_review()` retorna True para Warsaw (ICAO-only, sin noaa_station_id) → bloquea auto-promoción.
- **Guardrail documental (OBJETIVO B):** advertencia añadida al docstring de `tools/blocked_signals_settlement_tracker.py` explicando que su output local es parcial y NO equivale al archivo Railway canónico. Causa de la contradicción: el archivo local y Railway capturan subconjuntos distintos de señales (distintas temperaturas por ciclo operativo vs. snapshot local).
- **Bloqueadores pendientes Warsaw:** no en whitelist, no en canary/active, falta settlement fidelity formal, falta city_validation_ledger, falta city_promotion_gate, faltan campos schema (market_id, edge_pct, resolution_source, settlement_source, city_mode_at_record_time).

**Última actualización:** 4 de mayo de 2026 (Sesión 263 — revisión operativa post-ausencia 2026-05-01/04)
**Sesión 263 (4 may 2026, Claude Code Sonnet):** revisión read-only post-ausencia. Sin cambios de código.
- **Bankroll:** $19.61 (subió desde $17.68 por Shanghai NO `take_profit_intra` +112.2% a las 05:11 UTC del 2026-05-04). Sigue BLOCKED respecto a $25 tope.
- **403 Cloudflare (2026-05-01):** cerrado. El error fue transitorio de arranque del deploy. Desde 10:11 UTC en adelante, cero 403. Todos los ciclos 2026-05-01 → 2026-05-04 con `cycle_summary guardado OK`.
- **WATCH_TECH nuevo — 400 size below min (2026-05-04 00:01 UTC):** intento de BUY Shanghai NO 2.49sh×$0.71 rechazado por CLOB con `status=400 "Size (2.49) lower than the minimum: 5"`. Bot recuperó en ciclo 04:00 UTC (4.48sh×$0.40 aceptado, TP a las 05:11). No hubo pérdida económica. El pre-check de tamaño no garantiza aceptación CLOB en todos los casos.
- **L2 Hazard Monitor:** confirmado implementado en `bot.py` (commit 81b7586), default OFF (`SL_INTRA_HAZARD_MONITOR_ENABLED=0`).
- **SL retro:** 14 stop_losses tracked, no nuevo SL desde 2026-05-01T12:00. Muestra post-guard n≈2, insuficiente.
- **Ciclos 2026-05-01/03:** 0 BUYs confirmado. Patrón roto el 2026-05-04 con Shanghai trade.
- **PnL reconciliation 2026-05-04 08:01:** fallo urllib timeout al enviar Telegram (benign, network blip).
- **verify_before_deploy.py:** 1074/1074. runtime_policy_effective_view regenerado con 0 blocking_collisions.
- **Copy fix pendiente (ACTION_COPY):** `tools/sl_retrospective.py` línea 827 muestra "20/16 SLs" cuando `n_resolved > TARGET_SAMPLE_SIZE=16`. Prompt Codex preparado en `docs/codex_prompt_sl_retro_copy_2026_05_04.md`.
