# PROJECT_BOOTSTRAP.md — polymarket-bot

```yaml
bootstrap_version: canonical-project-bootstrap-v1
project_name: "polymarket-bot"
repository_url: "https://github.com/PabloGmez2K/polymarket-bot"

methodology_source:
  repository_url: "https://github.com/PabloGmez2K/lafabrica"
  branch: "main"
  bootstrap_path: "PROJECT_BOOTSTRAP.md"

entrypoints:
  orchestrator: ORCHESTRATOR.md
  builder: AGENTS.md
  adoption: docs/meta/LAFABRICA_ADOPTION.md

DEFAULT_ROUTING:
  CONTROL_PLANE: CHILD_PROJECT
  KNOWLEDGE_DESTINATION: CHILD_ONLY

handshake:
  remote_view_required_for_continuous_orchestration: true
  local_view_required_before_local_execution: true
```

Este archivo es un manifiesto de descubrimiento. No contiene metodología, cierre, routing de modelos, instrucciones de implementación, decisiones de dominio ni roadmap.

Orden de carga: `PROJECT_BOOTSTRAP.md` → `ORCHESTRATOR.md` → `AGENTS.md` → documentos locales referenciados por la tarea (`CONTEXTO.md`, `HISTORIAL_SESIONES.md`, `OPERATIONS_PLAYBOOK.md` solo cuando la tarea lo exige, según ya indican `ORCHESTRATOR.md` §1 y `AGENTS.md` §Leer primero).

`CONTROL_PLANE` y `KNOWLEDGE_DESTINATION` enrutan la sesión; nunca conceden autonomía ni permisos de escritura. Para trabajo operativo se requiere el contrato de sesión definido en `ORCHESTRATOR.md`. Las consultas generales y `CHAT_CLOSE` pueden resolverse sin contrato completo si no cambian estado ni autorizan ejecución.

Handshake mínimo:

```yaml
REMOTE_VIEW:
  status: VERIFIED | PARTIAL | UNAVAILABLE
  remote_head: <hash verificado o UNKNOWN>

LOCAL_VIEW:
  local_head: <hash>            # congelar como BASELINE_HEAD de la sesión
  worktree: CLEAN | DIRTY
  upstream_tracking_head: <hash o UNKNOWN>
  relation_to_remote_view: SAME | LOCAL_AHEAD | LOCAL_BEHIND | DIVERGED | UNKNOWN
```

La referencia upstream es evidencia local y no prueba el remoto actual. Sin `remote_head` verificado, la relación es `UNKNOWN`. El protocolo de origen es `CANONICAL_PROJECT_BOOTSTRAP.md` de Lafabrica; este manifiesto adoptado es autosuficiente para descubrir los contratos del hijo.

`local_head` se congela como `BASELINE_HEAD`: la baseline aprobada de la sesión. **Nunca es el `HEAD` actual**, que avanza con cada commit propio y ocultaría el trabajo aprobado que hay que preservar.

`methodology_source` distingue dos identidades distintas:

* `repository_url` identifica el repositorio hijo (polymarket-bot);
* `methodology_source.repository_url` identifica Lafabrica, el repositorio metodológico;
* `methodology_source.branch` indica la rama remota de Lafabrica a verificar;
* `bootstrap_path` se resuelve dentro de Lafabrica, no dentro del hijo;
* ningún path relativo declarado por Lafabrica se interpreta como path del hijo;
* el bootstrap hijo no contiene estado durable de adopción; esa fuente es `docs/meta/LAFABRICA_ADOPTION.md`.

`methodology_source` solo descubre. No concede permisos, no ejecuta fetch/pull y no modifica el hijo.
