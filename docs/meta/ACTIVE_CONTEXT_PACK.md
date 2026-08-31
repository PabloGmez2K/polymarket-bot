# ACTIVE_CONTEXT_PACK.md — polymarket-bot

L0. Arranque rápido — objetivo de lectura: **menos de 2 minutos**. No sustituye a `CONTEXTO.md`
(estado vivo detallado, append-only) ni a `HISTORIAL_SESIONES.md` (bitácora). Es la cápsula que
evita releerlos completos en cada sesión. Patrón de origen: `PATTERN-05 AI_FIRST_LAYERED_DOCUMENTATION`
(`docs/meta/LAFABRICA_ADOPTION.md`).

---

## Fase

**STANDBY.** Bot Stable v0. Trading real bloqueado globalmente vía `SHADOW_ONLY_MODE=true` en
Railway (verificado 2026-06-10, Sesión 424). Phase 2 cerrada `STOP_CURRENT_LINE` (2026-06-09,
Sesión 422). El bot observa, acumula y alerta; no emite BUY reales.

## Owners principales

- **Pablo** — autoridad exclusiva sobre BANKROLL, city modes, sizing, guards/SL, salida de STANDBY,
  env vars de Railway y cualquier acción FULL. Ninguna sesión autoriza estas superficies por sí sola.
- **Repo** (`ORCHESTRATOR.md`, `AGENTS.md`, `OPERATIONS_PLAYBOOK.md`) — fuente de verdad operativa.
  El chat y la memoria asistiva no tienen autoridad.
- **`docs/meta/LAFABRICA_ADOPTION.md`** — única fuente durable del estado de adopción metodológica.

## Prohibiciones operacionales vivas

- No trading real, no BUY/SELL/SKIP ejecutable, no BANKROLL, no Fase C sin autorización literal de
  Pablo y cambio FULL en Railway.
- No tocar trading core, NOAA, scheduler, reglas de entrada/salida ni arquitectura core sin pedido
  explícito.
- No cambiar env vars, DB, city modes ni runtime sin confirmación literal.
- Detalle completo: `ORCHESTRATOR.md §8` (guardrails) y `§15` (flujo STANDBY).

## Blocker operacional — PATTERN-14

```
NEXT_REAL_ORDER_WRITE = BLOCKED
```

`PATTERN-14 CONTROLLED_EXTERNAL_WRITE_FOUNDATION` (MR-007, CRITICAL, PROVISIONAL) está adoptado
**documentalmente** pero su verificación runtime sigue sin resolver: `risk_live: unknown`,
`activation_prerequisite: true`, `blocking_scope: NEXT_REAL_ORDER_WRITE`. No se investiga en
sesiones docs-only; requiere una sesión futura autorizada y con semántica Opus si aplica. Ver
`docs/meta/LAFABRICA_ADOPTION.md §4`.

## Trigger / siguiente observación vigente

- **BSR_POST_PROVENANCE_ROWS_CHECK** — revisar filas `blocked_signals_resolutions.jsonl` con
  provenance de `trader_win_rate` una vez existan filas nuevas post-deploy (`c7955fd`).
- Triggers E3 y de rotación de ciudades: ver `ORCHESTRATOR.md §15` y
  `HISTORIAL_SESIONES.md` (últimas entradas) para el estado exacto.

## Punteros a lectura más profunda

| Necesitas | Ir a |
|---|---|
| Estado vivo completo, experimento activo | `CONTEXTO.md` (bloque más reciente, no el archivo entero) |
| Bitácora de sesiones | `HISTORIAL_SESIONES.md` (entradas recientes) |
| Protocolo de workflow, deploy, Railway | `OPERATIONS_PLAYBOOK.md` |
| Contrato del orquestador | `ORCHESTRATOR.md` |
| Contrato de agentes de implementación | `AGENTS.md` |
| Estado de adopción metodológica Lafábrica | `docs/meta/LAFABRICA_ADOPTION.md` |
| Decisiones rechazadas vivas del workstream actual | `docs/meta/ACTIVE_DECISION_STATE.md` |
| Caminos conocidos por tipo de tarea recurrente | `docs/meta/AGENT_EXPERIENCE_LEDGER.md` |

---

## Historial de cambios

| Fecha | Cambio | Quién |
|-------|--------|-------|
| 2026-08-31 | Creado como parte de la migración de sistema operativo documental Lafábrica MR-003 → MR-014 (docs-only). | Claude Sonnet 5 |
