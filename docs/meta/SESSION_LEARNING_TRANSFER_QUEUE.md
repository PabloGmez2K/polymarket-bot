# SESSION_LEARNING_TRANSFER_QUEUE.md — polymarket-bot

Cola local de transferencias candidatas hacia `lafabrica-template` y/o `pablo-operating-brain`.

**Política:** Append-only. No eliminar entradas anteriores — cambiar Estado a DISCARDED si no aplica.
**Quién mantiene:** Orquestador al cierre de cada sesión relevante con aprendizaje transferible.
**Cuándo usar:** Solo si la sesión generó aprendizaje metodológico genuinamente transferible.
No en sesiones operativas, patches de trading, auditorías rutinarias o microajustes.

---

## Reglas de privacidad específicas de polymarket-bot

Este repo contiene información sensible. Antes de cualquier transferencia:

- `privacy_level` por defecto: `INTERNAL_ONLY`.
- Solo `PUBLIC_SAFE` si el patrón es 100% abstracto, sin referencia a ningún detalle del bot.
- **Nunca transferir:** estrategia de trading, bankroll, parámetros, thresholds, señales,
  mercados concretos, ciudades/tokens específicos, claves, variables de entorno, Railway,
  DB, snapshots privados, runtime, lógica de ejecución, código core, posiciones operadas,
  P&L concreto, resultados de trades ni infraestructura.
- **Solo transferir:** patrones metodológicos abstractos, principios de gobernanza,
  conceptos de control de riesgo (shadow mode, kill switches), economía de tokens,
  ciclos de vida de proyectos con agentes, STANDBY como estado explícito.
- Revisar dos veces si el candidato menciona riesgo, ejecución, trading o infraestructura.

---

## Formato de entrada

```
### SLT-NNN — TÍTULO

- Fecha: YYYY-MM-DD
- Proyecto: polymarket-bot
- Sesión/bloque: [referencia]
- project_value: [qué valor deja para polymarket-bot — o "No aplica"]
- lafabrica: [qué mejora el sistema operativo — o "No aplica"]
- brain:
  - evidence: [evidencia profesional saneada — o "No aplica"]
  - skills: [capacidad demostrada — o "No aplica"]
  - service_angle: [servicio que podría alimentar — o "No aplica"]
  - content_angle: [post, reflexión o narrativa pública — o "No aplica"]
  - portfolio_asset: [caso, prueba o activo — o "No aplica"]
- future_product: [insight para producto futuro — o "No aplica"]
- no_copy: [qué NO transferir ni publicar — siempre requerido aquí]
- privacy_level: PUBLIC_SAFE / INTERNAL_ONLY / PRIVATE_DO_NOT_EXPORT
- Estado: CANDIDATE / IMPORTED_TO_LAFABRICA / IMPORTED_TO_BRAIN / IMPORTED_TO_BOTH / DISCARDED / NEEDS_REVIEW
- Siguiente acción: [qué debe pasar para avanzar]
```

---

## Estados válidos

| Estado | Significado |
|--------|-------------|
| `CANDIDATE` | Identificado. Pendiente de revisión y absorción. |
| `IMPORTED_TO_LAFABRICA` | Absorbido en lafabrica-template. |
| `IMPORTED_TO_BRAIN` | Absorbido en pablo-operating-brain. |
| `IMPORTED_TO_BOTH` | Absorbido en ambos destinos. |
| `DISCARDED` | Descartado — demasiado específico o privado. |
| `NEEDS_REVIEW` | Requiere revisión de privacidad antes de avanzar. |

---

## Cola de candidatos

---

### SLT-001 — SHADOW_MODE_AND_KILL_SWITCH_DISCIPLINE

- Fecha: 2026-06-20
- Proyecto: polymarket-bot
- Sesión/bloque: SESSION_LEARNING_TRANSFER_AND_STANDBY_FLOW_SYNC
- project_value: Patrón ya implementado en el bot. Documentarlo como transferible lo hace
  explícito y reutilizable en proyectos futuros con riesgo operativo real.
- lafabrica: Shadow primero, ejecución bloqueada por defecto, kill switches explícitos
  en env vars — sin código nuevo para pausar o escalar. Patrón: toda herramienta nueva
  arranca OFF o en modo LOG_ONLY; la activación real es un paso FULL separado con
  autorización explícita. Aplicable a cualquier sistema con consecuencias operativas reales
  (e-commerce con pagos, infraestructura, sistemas con escrituras irreversibles).
- brain:
  - evidence: Diseño y operación de un sistema con kill switches y shadow mode en
    producción real durante meses, con múltiples incidentes manejados sin pérdida
    de control gracias a estos mecanismos.
  - skills: Diseño de sistemas defensivos por defecto; separación entre observar y actuar;
    protocolos de autorización explícita para acciones irreversibles.
  - service_angle: Consultoría en diseño de sistemas operativos seguros para proyectos
    con IA y agentes autónomos (cualquier vertical con riesgo de ejecución real).
  - content_angle: "Por qué todo sistema con IA debería tener shadow mode y kill switches
    desde el día 1" — caso real, abstracto y publicable.
  - portfolio_asset: Evidencia de diseño defensivo en producción real. Caso de estudio
    abstracto sobre gestión de riesgo operativo con agentes.
- future_product: Patrón base para Cauvera (marketplace con transacciones reales) o
  cualquier SaaS con operaciones de escritura críticas.
- no_copy: No mencionar parámetros de trading, bankroll, thresholds, ciudades, señales,
  mercados Polymarket, P&L real ni ningún detalle del bot. Solo el concepto.
- privacy_level: PUBLIC_SAFE
- Estado: IMPORTED_TO_BOTH
- Traza Brain: 2026-06-20 → pablo-operating-brain EVID-005 ext., POST_IDEAS, OFFER-07 creado (Sesión 5 Brain); 2026-06-29 → confirmado, status actualizado.
- Traza Lafabrica: PATTERN-01 en ECOSYSTEM_LEARNING_PATTERNS.md (SHADOW_FIRST).
- Siguiente acción: Ninguna.

---

### SLT-002 — LONG_RUNNING_AGENT_PROJECT_GOVERNANCE

- Fecha: 2026-06-20
- Proyecto: polymarket-bot
- Sesión/bloque: SESSION_LEARNING_TRANSFER_AND_STANDBY_FLOW_SYNC
- project_value: La estructura de gobernanza de polymarket-bot (cierres de sesión,
  CONTEXTO.md, HISTORIAL_SESIONES.md, ORCHESTRATOR.md, AGENTS.md, agent_events.jsonl,
  economía de tokens) es el modelo que luego se generalizó en lafabrica. Documentarlo
  cierra el origen histórico.
- lafabrica: Patrón reutilizable de gobernanza para proyectos largos con agentes:
  (1) "1 sesión = 1 tarea" como regla de disciplina de contexto.
  (2) Fuentes de verdad separadas: foto viva (CONTEXTO), protocolo de trabajo
  (OPERATIONS_PLAYBOOK), historial append-only (HISTORIAL_SESIONES), eventos máquina
  (agent_events.jsonl).
  (3) Cierre proporcional: LITE/NORMAL/FULL según el alcance real.
  (4) Economía de tokens: medir antes de optimizar, modelo default barato, escalar solo
  cuando la tarea lo justifica.
  (5) Roles de agentes separados: orquestador / implementador / revisor.
- brain:
  - evidence: Operación de un proyecto con >400 sesiones documentadas con cierres
    controlados, sin pérdida de trazabilidad operativa en más de 6 meses.
  - skills: Diseño de flujos de trabajo con agentes para proyectos largos; control de
    contexto y economía de tokens en producción real.
  - service_angle: Consultoría en implementación de flujos operativos con IA para equipos
    pequeños (solopreneur, pyme, agencias). Methodología probada en producción real.
  - content_angle: "Cómo gestionar cientos de sesiones con IA sin perder el hilo" —
    extracto del flujo real, abstracto y publicable.
  - portfolio_asset: Caso de estudio de gobernanza de proyecto largo con agentes,
    completamente abstracto (sin datos de trading).
- future_product: Sistema operativo base para cualquier proyecto con agentes autónomos
  y consecuencias reales (Cauvera, SaaS, laboratorio operativo).
- no_copy: No mencionar trading, señales, bankroll, Polymarket, ciudades, P&L ni
  ningún detalle operativo del bot. Solo el framework de gobernanza.
- privacy_level: PUBLIC_SAFE
- Estado: IMPORTED_TO_BOTH
- Traza Brain: 2026-06-20 → pablo-operating-brain EVID-005 ext. (>400 sesiones, gobernanza), POST_IDEAS (Sesión 5 Brain); 2026-06-29 → confirmado, status actualizado.
- Traza Lafabrica: PATTERN-02 en ECOSYSTEM_LEARNING_PATTERNS.md (LONG_RUNNING_PROJECT_GOVERNANCE).
- Siguiente acción: Ninguna.

---

### SLT-003 — STANDBY_AS_FIRST_CLASS_PROJECT_STATE

- Fecha: 2026-06-20
- Proyecto: polymarket-bot
- Sesión/bloque: SESSION_LEARNING_TRANSFER_AND_STANDBY_FLOW_SYNC
- project_value: La decisión de documentar STANDBY como estado explícito (no como
  abandono silencioso) protege el proyecto: el repo queda gobernable, transferible
  y seguro para retomarlo con criterio claro. La alternativa — parar sin documentar —
  habría dejado ambigüedad sobre si el sistema estaba roto o pausado intencionalmente.
- lafabrica: Patrón reutilizable: STANDBY es un estado operativo de primera clase,
  con definición explícita, criterios de entrada/salida documentados y restricciones
  claras de qué se puede/no se puede hacer en ese estado.
  Aplica a: proyectos pausados por estrategia, proyectos en espera de evidencia,
  proyectos con riesgo alto que requieren gate antes de reactivar.
  Elementos del patrón: (1) criterio de entrada a STANDBY documentado; (2) qué se
  permite hacer en STANDBY (docs, auditorías, mantenimiento); (3) qué no se permite
  (cambios de runtime, reactivación sin decisión); (4) trigger explícito para salir
  (fecha, métrica, evidencia); (5) canal de salida definido (quién autoriza, qué sesión).
- brain:
  - evidence: Gestión de una transición controlada de sistema activo a STANDBY sin
    pérdida de gobernanza ni datos, con criterios de reactivación documentados.
  - skills: Diseño de estados de ciclo de vida para proyectos técnicos complejos;
    documentación de invariantes de estado.
  - service_angle: Consultoría en gestión de proyectos con IA: cómo pausar
    responsablemente un sistema sin generar deuda técnica ni confusión futura.
  - content_angle: "Por qué 'pausar un proyecto de IA' necesita un protocolo" —
    caso de STANDBY como decisión activa vs. abandono pasivo.
  - portfolio_asset: Caso de estudio de gestión de ciclo de vida de proyecto técnico
    con IA, abstracto y publicable.
- future_product: Patrón aplicable a cualquier producto con fases de go/no-go:
  sistemas de recomendación, bots de automatización, pipelines de datos.
- no_copy: No mencionar por qué el bot entró en STANDBY (trading, resultados,
  estrategia, P&L). Solo el patrón de gestión del estado.
- privacy_level: PUBLIC_SAFE
- Estado: IMPORTED_TO_BOTH
- Traza Brain: 2026-06-20 → pablo-operating-brain EVID-005 ext. (STANDBY explícito), POST_IDEAS (Sesión 5 Brain); 2026-06-29 → confirmado, status actualizado.
- Traza Lafabrica: PATTERN-03 en ECOSYSTEM_LEARNING_PATTERNS.md (STANDBY_AS_FIRST_CLASS_STATE).
- Siguiente acción: Ninguna.

---

### SLT-004 — CANDIDATE_CHILD_LOCAL: outcome-scoped worktree execution

- Fecha: 2026-08-31
- Proyecto: polymarket-bot
- Sesión/bloque: migración de sistema operativo documental Lafábrica MR-003 → MR-014
- project_value: Ejecutar cada outcome discreto en un worktree aislado del mismo repo evita
  contaminar el checkout principal con estado a medio terminar y hace explícito qué cambios
  pertenecen a qué tarea.
- lafabrica: Patrón candidato — no confirmado como estándar todavía. Concepto abstracto: cuando una
  tarea tiene un outcome acotado y verificable, ejecutarla en un espacio de trabajo aislado
  (worktree o equivalente) por outcome, en vez de por agente o por sesión de chat, reduce el riesgo
  de mezclar cambios no relacionados y facilita el handshake `BASELINE_HEAD` (`PATTERN-16`). Sin
  evidencia todavía de un segundo proyecto independiente que lo valide.
- brain:
  - evidence: No aplica.
  - skills: No aplica.
  - service_angle: No aplica.
  - content_angle: No aplica.
  - portfolio_asset: No aplica.
- future_product: No aplica.
- no_copy: No mencionar rutas locales, nombres de agentes, herramientas de orquestación concretas ni
  ningún dato de trading. Solo el concepto abstracto de aislamiento por outcome.
- privacy_level: PUBLIC_SAFE
- Estado: `CANDIDATE`
- Siguiente acción: Pablo revisa. No se declara estándar de Lafábrica ni regla del hijo hasta
  validarse en un segundo proyecto independiente — ver `LAFABRICA_RELEASE_PROTOCOL.md §7` (regla del
  segundo proyecto).

---

## Historial de revisiones

| Fecha | Cambio |
|-------|--------|
| 2026-06-20 | Documento creado. Candidatos iniciales: SLT-001, SLT-002, SLT-003. |
| 2026-08-31 | SLT-004 añadido (candidato abstracto y saneado: outcome-scoped worktree execution). Parte de la migración Lafábrica MR-014. |
