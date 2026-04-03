---
name: session-close-sync
description: Usa esta skill al cerrar una sesion relevante para alinear docs, scoreboard y trazabilidad del repo sin dejar drift.
---

# Session Close Sync

1. Confirmar si la sesion cambio estado, workflow, datos, arquitectura o trazabilidad.
2. Si si, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md`.
3. Si hubo aportacion relevante, registrar evento con `python tools/append_agent_event.py ...`.
4. Verificar que docs y `agent_events.jsonl` cuentan la misma sesion.

- No editar `agent_events.jsonl` a mano salvo emergencia.
- Mantener `HISTORIAL_SESIONES.md` append-only.
- Si no hubo cambio de estado real, no inflar docs ni scoreboard.
