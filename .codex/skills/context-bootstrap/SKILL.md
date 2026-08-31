---
name: context-bootstrap
description: Usa esta skill al arrancar trabajo en este repo para abrir el minimo contexto util, elegir 1-3 artefactos fuente y evitar releer documentos largos sin necesidad.
---

# Context Bootstrap

1. Leer `PROJECT_BOOTSTRAP.md` (entrypoints, handshake — manifiesto de descubrimiento, no contrato).
2. Leer `docs/meta/ACTIVE_CONTEXT_PACK.md` (L0, <2 min: fase, owners, prohibiciones vivas, blocker
   `NEXT_REAL_ORDER_WRITE`, trigger vigente, punteros).
3. Leer `AGENTS.md` (contrato corto) y solo el bloque relevante de `CONTEXTO.md`.
4. Abrir `OPERATIONS_PLAYBOOK.md` solo si la tarea toca workflow, cierre, deploy, Railway o scoreboard.
5. Owners causales necesarios: si la tarea es bug/incidente/recurrente, `docs/meta/AGENT_EXPERIENCE_LEDGER.md`
   antes de cualquier búsqueda amplia; como mucho un artefacto extra más (handoff, snapshot, log o
   archivo objetivo).

- No abrir `CONTEXTO.md` completo por defecto.
- No leer sesiones antiguas salvo relacion directa.
- Esta receta no crea un segundo sistema de reading recipes: es el orden de lectura de
  `PROJECT_BOOTSTRAP.md`/`AGENTS.md`, no una lista paralela de artefactos por tipo de tarea.
