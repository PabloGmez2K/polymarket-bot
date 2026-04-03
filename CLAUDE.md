# CLAUDE.md - Polymarket Weather Bot

## Lectura minima obligatoria

- `AGENTS.md`
- `CONTEXTO.md`
- `OPERATIONS_PLAYBOOK.md`

Usar `AGENTS.md` como contrato corto, `CONTEXTO.md` como estado vivo y `OPERATIONS_PLAYBOOK.md` como protocolo de trabajo/cierre.

## Rol de este archivo

Este archivo ya no intenta duplicar estado, versionado ni inventarios largos.
Solo recuerda el marco estable para Claude Code:

- repo de bot meteorologico en Polymarket;
- codigo principal en Python;
- produccion en Railway;
- `verify_before_deploy.py` es la red de seguridad antes de push/deploy.

## Guardrails

- No tocar trading, NOAA, scheduler, reglas de entrada/salida ni arquitectura core salvo pedido explicito.
- Si cambia estado o workflow, alinear `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`.
- Para Railway, seguir `OPERATIONS_PLAYBOOK.md` y usar `tools/railway_safe.ps1`.

## Nota de drift

La informacion viva del proyecto debe mantenerse en `CONTEXTO.md` y `OPERATIONS_PLAYBOOK.md`, no aqui.
