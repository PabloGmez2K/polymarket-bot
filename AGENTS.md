# AGENTS.md

Capa canonica y corta para Codex en este repo.

## Leer primero

1. `AGENTS.md`
2. bloque relevante de `CONTEXTO.md`
3. `OPERATIONS_PLAYBOOK.md` solo si la tarea toca workflow, cierre, deploy, Railway o scoreboard

No cargar `CONTEXTO.md` completo ni sesiones antiguas sin necesidad.

## Default

- `model_reasoning_effort = "medium"` por defecto
- subir profundidad solo con perfiles `low`, `deep` o `max`
- preferir trabajo por fases y subproblemas acotados

## Guardrails

- No tocar trading, NOAA, scheduler, reglas de entrada/salida ni arquitectura core salvo pedido explicito.
- Primero evidencia, luego copy o refactor.
- Preferir `rg` y lecturas puntuales.
- Para Railway, usar `tools/railway_safe.ps1`.
- Antes de push/deploy, correr `python verify_before_deploy.py`.

## Cierre

Si la sesion cambia estado, workflow o trazabilidad, alinear:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `agent_events.jsonl`

La memoria externa no sustituye la fuente de verdad del repo.
