# Handoff — London blocked policy review (2026-04-21)

## Prompt para Codex

Lee `AGENTS.md`, el bloque reciente de `CONTEXTO.md`, `docs/london-settlement-source-audit-2026-04-15.md`, `data/runtime_policy_effective_view.json`, `docs/runtime_policy_effective_view_latest.md`, `data/runtime_import/city_policy_state.json`, `data/runtime_import/policy_env_snapshot.json`, `data/city_validation_ledger.json`, `data/city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md`.

Objetivo: evaluar por qué `London` sigue siendo la única ciudad en `BLOCKED_CITIES` y si ese bloqueo todavía está justificado. No empieces tocando `bot.py`, reglas de entrada/salida, NOAA core, scheduler, thresholds, whitelist ni trading core. Primero evidencia, luego decisión.

Preguntas obligatorias:

1. ¿Cuál fue la razón original de bloquear London y sigue estando respaldada por evidencia reciente?
2. ¿La colisión actual `BLOCKED_CITIES=London` + `city_policy_state.auto_canary_cities.London` es solo deuda de overlay runtime, o indica que la evidencia shadow posterior contradice el bloqueo?
3. ¿Qué datos frescos hay de London en `shadow_city_tracking`, `audit`, `performance`, `trade_lifecycle`, `skip_log` y señales de quality traders?
4. ¿London debe quedarse `blocked`, pasar a `shadow`, o requiere una revalidación externa de settlement/source antes de tocar policy?
5. Si el veredicto es mantener `blocked`, ¿conviene neutralizar solo el overlay runtime `auto_canary` de London para que `system_alignment_check.py --decision-mode operational` vuelva a verde?
6. Si el veredicto es desbloquear, ¿cuál es el cambio mínimo y reversible: quitar de `BLOCKED_CITIES`, mover a `shadow`, o otra vía?

Salida esperada:

- Diagnóstico corto con evidencia concreta y fechas.
- Veredicto: `mantener_blocked`, `desbloquear_a_shadow`, o `revalidacion_externa_primero`.
- Acción mínima propuesta, separando claramente cambios read-only, cambios Railway env y cambios sobre `city_policy_state.json`.
- Checklist de validación: refrescar runtime read-only, regenerar `runtime_policy_effective_view`, `city_validation_ledger`, `city_promotion_gate`, correr `python tools/system_alignment_check.py --decision-mode operational`.

Guardrail: no usar `BLOCKED_CITIES` como pausa operativa. Si London está bloqueada, debe ser por fuente/settlement rota o riesgo estructural, no por throughput bajo ni por “no quiero operar ahora”.

## Contexto de arranque

- El transporte runtime ya fue reparado en Sesión 216: manifest fresco `2026-04-21T14:54:02Z`, `runtime_inputs_status=available`, pipeline `overall_status=ok`.
- El único error operacional restante es London: `BLOCKED_CITIES=London` en Railway y `auto_canary_cities.London` en `city_policy_state.json`.
- La effective view mantiene `effective_mode=blocked` porque `blocked` tiene prioridad sobre `auto_canary`.
- La sesión original pidió no tocar `city_policy_state.json`, así que el overlay London quedó intacto a propósito.
