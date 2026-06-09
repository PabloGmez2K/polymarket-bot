# STANDBY_ALARM_HYGIENE_V0 — Higiene de alertas post Phase 2

**Fecha:** 2026-06-09 (Sesión 423, Fable)
**Estado:** IMPLEMENTED (alert routing/text only)
**Contexto:** Phase 2 cerrada el 2026-06-09 como `STOP_CURRENT_LINE / PHASE2_CLOSED_FAIL_B6_ZERO_THROUGHPUT_TAIL`
(ver `docs/phase2-t30-decision-dossier-2026-05-20.md`, addendum T+30). El sistema queda en
fase **STANDBY** (Bot Stable v0): sin live trading esperado, accrual de datos trader/BSR
activo, próximo trigger accionable = E3 trader-following check **2026-06-23**.

> Este cambio NO toca BUY/SELL/SKIP, BANKROLL, Fase C, city modes, exact/NO, sizing,
> scheduler de trading, guards/SL ni collectors. Solo routing y texto de alertas/digest.

---

## 1. Concepto: `OPERATIONAL_PHASE`

- Constante en `bot.py` (junto al resto de config env): `OPERATIONAL_PHASE = os.getenv("OPERATIONAL_PHASE", "STANDBY")`.
- **El default en código es `STANDBY`** porque ese ES el estado verdadero del sistema tras el cierre de Phase 2.
  No requiere env var nueva en Railway.
- Salir de STANDBY (p. ej. a un futuro estado ARMED del follower E3) = setear la env var
  `OPERATIONAL_PHASE` en Railway → **cambio FULL** que requiere autorización explícita de Pablo
  y semántica Opus si afecta trading.
- `tools/daily_bot_digest.py` lee la misma env var con el mismo default (proceso separado).

### Por qué NO se usó el mecanismo existente `RECALIBRATION_PHASE2_CLOSED`

El concepto preexistente de "Phase 2 cerrada" (`RECALIBRATION_PHASE2_CLOSED=true` o
`data/recalibration_phase2_status.json` con `status=closed`, bot.py `maybe_alert_v2_trigger`)
está cableado a una **sugerencia de expansión** ("añadir Bloques 3+5") — exactamente el tipo de
ruido que STANDBY debe evitar. Marcarlo habría disparado esa alerta con 4 ciudades aún en
`ACTIVE_TRADING_CITIES`. Footgun documentado y desactivado en STANDBY (ver §3).

---

## 2. Taxonomía de alertas en STANDBY

| Clase | Componente | Comportamiento en STANDBY |
|---|---|---|
| `RISK_KEEP` | signals.json health (missing/stale/error) | Sin cambio — collector crítico para accrual E3 |
| `RISK_KEEP` | recorder health alert | Sin cambio |
| `RISK_KEEP` | low bankroll alert | Sin cambio — gasto inesperado debe alertar |
| `RISK_KEEP` | city accuracy / NOAA-verified review / active degradation | Sin cambio — mudas con flujo=0; si suena una, hay trading inesperado |
| `RISK_KEEP` | notify_canary_candidates / notify_active_candidates / sync_city_policy_state | Sin cambio — revelan cambios de modo; silenciarlas repetiría el incidente de visibilidad 2026-05-20 |
| `RISK_KEEP` | bankroll scaling: transición de elegibilidad o cambio de estado | Sin cambio |
| `MUTED_IN_STANDBY` | `maybe_run_phase2_monitor` (rollback Phase 2) | **Early return** — fase muerta no alerta |
| `MUTED_IN_STANDBY` | `maybe_alert_v2_trigger` (sugerencia expansión v2) | **Early return** — footgun desactivado |
| `MUTED_IN_STANDBY` | bankroll scaling: resumen periódico cada N ciclos | **Suprimido** (solo el resumen; transiciones siguen vivas) |
| `DIGEST_ONLY` | funnel `with_edge=0` / `condition_filtered` / BUY=0 | Sin cambio de routing (ya vivían solo en digest); ahora con banner STANDBY que los contextualiza como esperados |
| `DIGEST_ONLY` | resumen diario 08:00, digest 20:00, P&L/briefing | Sin cambio de routing |
| `TRIGGER_WATCH` | crosscheck diario, traders intelligence summaries, blocked signals check | Sin cambio — son el accrual E3; no tocar |
| Ya muertas (sin acción) | W17, P4/P5, P6/P7, Busan, TP/SL steps (one-shot ya disparadas), condition_monitor (auto-retirado) | Estado en `alerts_state` las mantiene apagadas |

### Banner en digest diario

`tools/daily_bot_digest.py` antepone en Telegram y render humano:

```
⏸ Bot state: STANDBY
Phase 2 closed (2026-06-09). No live trading expected.
Next actionable trigger: E3 trader-following check 2026-06-23.
```

---

## 3. Cambios de código (S423)

| Archivo | Cambio |
|---|---|
| `bot.py` | Constante `OPERATIONAL_PHASE` (default `STANDBY`); early return en `maybe_run_phase2_monitor`; early return en `maybe_alert_v2_trigger` (getenv inline por el namespace aislado de verify); supresión de `cycle_summary_due` en `maybe_run_bankroll_scaling_monitor` |
| `tools/daily_bot_digest.py` | `operational_phase()` + `standby_banner_lines()` + banner en `render_telegram_digest` (ambas ramas) y `render_human_digest` |
| `tests/test_phase2_monitor.py` | Fixture autouse non-standby para los tests históricos + test nuevo: STANDBY silencia incluso con kill-switch |
| `verify_before_deploy.py` | Fixtures v2-trigger con `OPERATIONAL_PHASE=PHASE2` + caso funcional nuevo: default STANDBY no alerta ni muta state |

## 4. No-goals explícitos de v0

- **Sin alarma nueva "BSR no acumula"** ni "E3 trigger candidate": serían observabilidad nueva;
  la cobertura es el check manual del 2026-06-23 (Codex read-only, `tools/trader_benchmark.py`).
- Sin tocar `maybe_send_daily_summary_telegram` (resumen 08:00): ya es digest por naturaleza.
- Sin borrar herramientas ni desactivar collectors.
- Sin env vars nuevas en Railway (el default en código es el estado verdadero).

## 5. Cómo salir de STANDBY

1. Trigger E3 (celda forward `n>=10 && top1<=50%` + `edge_ci.lower>0`) → Opus ratifica diseño follower.
2. `OPERATIONAL_PHASE` se setea en Railway con autorización explícita (cambio FULL).
3. Los gates de este doc se reactivan solos (leen la fase); el banner del digest desaparece.
