# Handoff Codex — P1 ORI readout unificado lifecycle + Hazard + INTRA-REEVAL

**Fecha:** 2026-05-13
**Agente destino:** Codex
**Modo:** NORMAL · read-only / LOG_ONLY
**Prioridad:** Alta-media
**Origen:** [docs/BACKLOG_ORI_operational_readiness_intelligence.md](BACKLOG_ORI_operational_readiness_intelligence.md) §P1

---

## Por qué este handoff

P0 fue cerrado por Opus el 2026-05-13 (`KEEP_BLOCKED + NEED_MORE_RUNTIME_EVIDENCE`, ver `docs/p0_b5_b6_opus_review_2026_05_13.md`). La siguiente tarea activa del backlog ORI es P1. No duplicar contenido aquí; leer el backlog para detalle, este doc solo encuadra el trabajo.

## Tarea

Diseñar / implementar un report read-only que una la evidencia repartida entre:

- `trade_lifecycle.json`
- `sl_intra_hazard_monitor_audit.json`
- `intra_reeval_state.json`
- `sl_intra_guard_audit.json`
- `skip_log.jsonl`

Campos esperados, casos de prueba (Singapore 32°C May12 NO, Seoul 21°C May12 NO) y veredicto esperado (`NO_EXISTING_TOOL_PATCH_READY` / `EXISTING_TOOL_SUFFICIENT` / `REPORT_DESIGN_ONLY` / `STOP_NEEDS_OPUS`): ver §P1 del backlog ORI.

## Guardrails (no negociables)

- **Read-only / LOG_ONLY.** Ninguna escritura runtime.
- **No DB writes.**
- **No tocar:** BANKROLL, Fase C, trading core, `bot.py` semántico, sizing, whitelist, city modes, scheduler, SL ejecutable, guards, INTRA-REEVAL ejecutable, env vars Railway, reglas BUY/SELL/SKIP.
- **No reabrir P0** ni decisiones de P&L canónico. P0 ya cerró Opus.
- **No Telegram real.**
- **No tocar** `trade_lifecycle.json`, `intra_reeval_state.json`, `sl_intra_guard_audit.json`, `sl_intra_hazard_monitor_audit.json`, `skip_log.jsonl` como writes. Solo lectura.
- **No tocar** el untracked preexistente `2026-04-27]`.
- Antes de push: `python verify_before_deploy.py`.
- Para Railway: `tools/railway_safe.ps1` siempre.
- Si la tarea deriva a decisión semántica de SL/guards/INTRA/riesgo/BANKROLL/whitelist/city modes/Fase C → **parar** y dejar prompt corto para Opus.

## Stop conditions

Parar inmediatamente si aparece:

- Necesidad de cambio en env vars o DB schema.
- Decisión sobre BUY/SELL/SKIP, sizing, whitelist, city modes, scheduler, SL, guards, Fase C.
- Confirmación humana requerida.
- Worktree sucio fuera de scope.
- Necesidad de leer demasiados archivos para acotar el problema.

## Entrega esperada

- Veredicto binario de §P1 del backlog.
- Si `REPORT_DESIGN_ONLY` o `NO_EXISTING_TOOL_PATCH_READY`: diseño/patch acotado en `tools/` (nombre orientativo `tools/sl_intra_case_readout.py`).
- Tests si aplica.
- `git status` final limpio salvo untracked preexistente.
- Validaciones ejecutadas (`verify_before_deploy.py` si hay patch).
- Commit con mensaje claro. Push solo si validaciones pasan y se observa Railway hasta `SUCCESS/FAILED`.

## Siguiente paso opcional

Si P1 cierra limpio y P2 sigue siendo read-only/reporting (verificar `review_alert_sent=false` en INTRA-REEVAL), Codex puede continuar con P2 en la misma sesión. Detalle: §P2 del backlog ORI.
