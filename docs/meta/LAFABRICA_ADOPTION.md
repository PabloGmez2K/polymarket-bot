# LAFABRICA_ADOPTION.md — polymarket-bot

Declaración de adopción metodológica de este proyecto hijo frente a lafabrica.

**Copiar a:** `docs/meta/LAFABRICA_ADOPTION.md` del proyecto hijo.
**Fuente del protocolo:** `lafabrica/docs/orchestrator/LAFABRICA_RELEASE_PROTOCOL.md` (verificado en
`7c1c8bb133f50caa0772b5f5d813c9e01764234f`, `main`).
**Modelo operativo:** `lafabrica/docs/orchestrator/CHILD_PROJECT_ADOPTION_MODEL.md` (`AUDIT -> PLAN -> APPLY`).
**Política:** este archivo es la **única fuente de verdad** de qué release y patrones metodológicos tiene adoptados este proyecto. El operador no recuerda el estado de cada repo — lo lee aquí.
**Quién mantiene:** Orquestador, al adoptar una release y al reactivar el proyecto. Modelo **pull**: lafabrica nunca empuja; este proyecto adopta cuando le toca.

---

## Estado de adopción (bloque legible por máquina)

> Mantener estas claves exactas. Un futuro Brain Console las parsea para calcular el estado del ecosistema sin intervención humana.

```
project: polymarket-bot
domain: trading — prediction-market bot (weather-based markets en Polymarket)
lafabrica_release_base: MR-014
lafabrica_release_current_seen: MR-014
pending_critical: none
pending_recommended: none
project_state: STANDBY
last_reviewed: 2026-08-31
next_review_recommended: on-reactivation
privacy_level: INTERNAL_ONLY
```

`lafabrica_release_base` y `lafabrica_release_current_seen` avanzan a `MR-014` porque la cobertura
del Change Index MR-001..MR-014 es completa (65/65 `change_id`, ver §2.1). `pending_critical: none`
es correcto en este eje: **release-adoption** — todo `CRITICAL` de MR-001..MR-014 tiene una
disposición metodológica terminal (`PATTERN-01` en §3, `PATTERN-14` en §3 con
`DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION`). Ningún `CRITICAL` queda sin adoptar a nivel de release.

Esto es un eje distinto de la **verificación operacional** de `PATTERN-14`, que sigue sin resolver y
no se oculta: ver §4 (`PATTERN-14` — gate operacional, `runtime_verification: pending`) y
`docs/meta/ACTIVE_CONTEXT_PACK.md` (`NEXT_REAL_ORDER_WRITE = BLOCKED`). Un `change_id` puede tener
disposición terminal de adopción y, a la vez, un gate operacional propio sin resolver — son sujetos
distintos (`METHODOLOGICAL_RELEASE` vs. `PATTERN_14_OPERATIONAL_GATE` vs. `ACTIVE_OPERATION`).

---

## 1 — Identidad

- **Proyecto:** polymarket-bot
- **Dominio:** trading — prediction-market bot (weather-based markets en Polymarket)
- **Estado del proyecto:** STANDBY (Bot Stable v0; `SHADOW_ONLY_MODE=true` en Railway)
- **Fecha de última revisión de adopción:** 2026-08-31

---

## 2 — Release base adoptada

- **Release base de lafabrica adoptada:** MR-014
- **Release actual de lafabrica vista en esta revisión:** MR-014 (Release Ledger, `LAFABRICA_RELEASE_PROTOCOL.md`, verificado `7c1c8bb133f5...`)
- **Gap:** ninguno — cobertura completa MR-001..MR-014

---

## 2.1 — Fidelidad canónica de `change_id` (obligatoria, MR-014.3)

El **Change Index** de `LAFABRICA_RELEASE_PROTOCOL.md` es la autoridad de identidad. Este archivo lo
consume; nunca lo reinterpreta. Los 65 `change_id` de §3/§4/§6/§7 se copiaron literalmente del
Change Index verificado en el commit remoto citado arriba — ninguno se reteclea de memoria ni desde
un output pegado.

**Cobertura verificada:** 65 `change_id` canónicos MR-001..MR-014 → 65 filas de disposición en este
archivo. Sin IDs inventados, duplicados ni faltantes (ver FINAL OUTPUT de la sesión de migración
2026-08-31 para el detalle expected/actual/missing/duplicate/unknown).

Regla práctica aplicada: **se copiaron los identificadores del Change Index, no se retecleraron.**

---

## 3 — Patrones adoptados

Patrones y cambios no-patrón del catálogo que este proyecto **ya aplica** (documentalmente, cuando
`DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION`).

| `change_id` | Patrón / cambio | Tipo | Adoptado en | Nota |
|---|---|---|---|---|
| `PATTERN-01` | SHADOW_FIRST | CRITICAL | sesión 424, 2026-06-10 | `SHADOW_ONLY_MODE=true` en Railway; kill switch global activo; BUY real bloqueado. **DONE**. |
| `PATTERN-14` | CONTROLLED_EXTERNAL_WRITE_FOUNDATION | CRITICAL | 2026-08-31 | Adoptado documentalmente: whitelist, revalidación fresca, preview/confirm, semántica de fallos, event log y refresh del mirror son foundation conceptual conocido y referenciado. Disposición de **release** terminal — no queda `CRITICAL` sin adoptar en MR-001..MR-014. La verificación **operacional** (runtime) es un eje distinto, sin resolver: ver §4 (gate operacional dedicado, no cuenta como `pending_critical`). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `PATTERN-02` | LONG_RUNNING_PROJECT_GOVERNANCE | RECOMMENDED | vigente (>400 sesiones) | Sin `BACKLOG.md`/`DECISIONS.md` discretos; equivalente vía `ORCHESTRATOR.md`, `CONTEXTO.md`, `HISTORIAL_SESIONES.md`. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `PATTERN-03` | STANDBY_AS_FIRST_CLASS_STATE | RECOMMENDED | sesión 423, 2026-06-09 | `OPERATIONAL_PHASE=STANDBY` en código; Bot Stable v0. **DONE**. |
| `PATTERN-04` | SLT_MIGRATION_IN_ACTIVE_REPOS | RECOMMENDED | sesión SLTSSF, 2026-06-20 | `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` instalado. **DONE**. |
| `PATTERN-05` | AI_FIRST_LAYERED_DOCUMENTATION | RECOMMENDED | 2026-08-31 | L0 `docs/meta/ACTIVE_CONTEXT_PACK.md` creado esta sesión (trigger `HISTORIAL_SESIONES.md` >50KB cumplido con margen — 640KB). L1 cubierto por `.codex/skills/context-bootstrap/SKILL.md` en vez de un `READING_RECIPES.md` separado; sin `STATUS.md` por módulo (fuera de `EXACT_SCOPE`). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `PATTERN-06` | AGENT_EXPERIENCE_LEDGER | RECOMMENDED | 2026-08-31 | `docs/meta/AGENT_EXPERIENCE_LEDGER.md` creado vacío. Reconciliación: la adopción anterior (2026-06-26) clasificaba mal `agent_events.jsonl` como el ledger — corregido; `agent_events.jsonl` es log, no experience ledger. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `PATTERN-07` | STOP_AND_REPLAN_MICROPATCH_PROTOCOL | RECOMMENDED | 2026-08-31 | `SIMPLIFY_REPLAN` incorporado vía wiring MR-009/MR-011 en `ORCHESTRATOR.md`; ya existían elementos análogos en AGENTS §Codex Operating Pattern. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-003.1` | Protocolo de releases metodológicas | RECOMMENDED | 2026-06-26 | Este archivo sigue el protocolo. **DONE**. |
| `MR-003.2` | Plantilla `LAFABRICA_ADOPTION.md` | RECOMMENDED | 2026-08-31 | Actualizado a la plantilla vigente con granularidad `change_id` (antes solo agrupaba por `PATTERN-NN`). **DONE**. |
| `MR-003.3` | Clasificación de `PATTERN-01..09` por tipo de cambio | (reclasificación) | 2026-06-26 | Reflejada en esta tabla. **DONE**. |
| `PATTERN-10` | DOMAIN_PRODUCT_MODELING_GATE | RECOMMENDED | 2026-08-31 | Guardrail añadido a `AGENTS.md`, adaptado al dashboard/templates del bot; sin documento local dedicado (ver §6, `MR-004.2`). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-004.3` | Guardrail en `ORCHESTRATOR.md` / `AGENTS.md` | RECOMMENDED | 2026-08-31 | Añadido junto con `PATTERN-10`. **DONE**. |
| `MR-005.1` | OUTCOME_FIRST_PROMPTING | RECOMMENDED | 2026-08-31 | Estructura `OUTCOME/DONE_BAR/NON_GOALS/AUTONOMY/VERIFY_PLAN/STOP_LOSS/CLOSE_MODE` incorporada en `ORCHESTRATOR.md §7`, adaptada sobre el token economics existente sin sustituirlo. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-005.2` | Separación Builder / Verifier / Closer | RECOMMENDED | 2026-08-31 | Responsabilidades, no agentes obligatorios — igual que el kernel lean de MR-011. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-005.3` | Cierre proporcional | RECOMMENDED | 2026-08-31 | Ya existía LITE/NORMAL/FULL; se añade `PARTIAL` para bloques con validación visual/manual pendiente. **DONE**. |
| `MR-006.1` | CHILD_PROJECT_ADOPTION_MODEL | RECOMMENDED | 2026-08-31 | Esta sesión ejecuta `APPLY` tras `AUDIT -> PLAN` realizado por el orquestador. **DONE**. |
| `MR-006.3` | MANAGED_BLOCKS_GUIDE | RECOMMENDED | 2026-08-31 | Bloque gestionado `UPDATE_NOTIFICATION_CHECK` instalado con la sintaxis `LAFABRICA:BEGIN/END` de esta guía. **DONE**. |
| `MR-006.4` | Política manual-first antes de automatizar adopciones | RECOMMENDED | 2026-08-31 | Esta adopción es manual/docs-only, sin CLI ni script. **DONE**. |
| `MR-008.1` | Update Notification Protocol V1 canónico | RECOMMENDED | 2026-08-31 | **DONE**. |
| `MR-008.2` | Fuente durable única de adopción + `methodology_source` | RECOMMENDED | 2026-08-31 | `methodology_source` ya en `PROJECT_BOOTSTRAP.md`; este archivo es la fuente durable. **DONE**. |
| `MR-008.3` | Tracking/delta efímeros y semántica CRITICAL de tres ejes | RECOMMENDED | 2026-08-31 | Aplicada a `PATTERN-14` en §4 (`risk_live`/`activation_prerequisite`/`blocking_scope`). **DONE**. |
| `MR-008.4` | Change Index estable y append-only | RECOMMENDED | 2026-08-31 | Consumido, no reinterpretado (§2.1). **DONE**. |
| `MR-008.5` | Wiring read-only de `CHECK` en el orquestador | RECOMMENDED | 2026-08-31 | Bloque gestionado instalado en `ORCHESTRATOR.md`. **DONE**. |
| `MR-009.1` | `PERSIST_BEFORE_DELEGATE`, idempotencia, alcance por línea, limpieza huérfana directa | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-009.2` | `DOCS_LITE` y handoff remoto mínimo | RECOMMENDED | 2026-08-31 | Ya existía cierre LITE; se añade el formato de handoff remoto mínimo. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-009.3` | Ciclo compacto de mensajes y prohibiciones con causa | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-009.4` | Progreso estable y `SIMPLIFY_REPLAN` | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-009.5` | Stop-loss R0-R3 e incidencias dentro del bloque | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-009.6` | Presupuesto de contexto/tiempo hasta valor | RECOMMENDED | 2026-08-31 | Ya cubierto en espíritu por §12/§13 (token economics/tokens-as-payroll). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-011.1` | Sesión ejecutora y propietario por defecto; Builder/Verifier/Closer como responsabilidades | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-011.2` | Separación solo por riesgo, autorización, entregable independiente o petición explícita | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-011.3` | Evidencia proporcional a la DONE_BAR | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-011.4` | Contexto completo una vez y cambio de método tras dos fallos equivalentes | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-011.5` | Git read-only independiente de commit/push; memoria asistiva sin autoridad | RECOMMENDED | 2026-08-31 | Ya existía `rtk KEEP_WITH_RULES` / `engram USE_AFTER_REPO`; se explicita la semántica read-only. **DONE**. |
| `MR-011.6` | Actualizar solo trackers cuyo estado cambió; cierre y publicación coherentes | RECOMMENDED | 2026-08-31 | Ya existía "actualizar solo trackers cuyo estado cambió". **DONE**. |
| `MR-012.1` | Handoff semántico mínimo: `ASSIGNMENT` + `DECISIONS_ALREADY_CLOSED` | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-012.2` | Solución suficiente y cierre al pasar DONE_BAR | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-012.3` | No microfix recursivo; incidencias dentro del bloque | RECOMMENDED | 2026-08-31 | Ya cubierto por "Codex patch economics" en `ORCHESTRATOR.md §4`. **DONE**. |
| `MR-012.4` | Bucle técnico autónomo dentro de la autoridad concedida | RECOMMENDED | 2026-08-31 | Acotado: FULL sigue requiriendo Opus/confirmación literal — sin ampliar autonomía de trading. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-012.5` | Context delta only en continuaciones vivas | RECOMMENDED | 2026-08-31 | Ya existía "no repetir contexto ya leído". **DONE**. |
| `MR-012.6` | Frontera de escritura externa A0/A1 y retorno inmediato tras STOP_LOSS | CRITICAL | 2026-08-31 | Ya cubierto, más estricto que el genérico, por "confirmación literal antes de env vars/Railway/trading/DB"; ahora explícito con vocabulario A0-A3. Sin superficie nueva expuesta. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-012.7` | Validación de patch proposals sobre la frontera causal | RECOMMENDED | 2026-08-31 | **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-013.1` | Estado decisorio activo y preservación de rechazos | RECOMMENDED | 2026-08-31 | `docs/meta/ACTIVE_DECISION_STATE.md` creado (vacío, `WORKSTREAM.active: NONE`). **DONE**. |
| `MR-013.2` | Interacción directa persona-agente con escalado condicional | RECOMMENDED | 2026-08-31 | `INTERACTION_POLICY` incorporado como bloque condicional en `ORCHESTRATOR.md`. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-013.3` | Grilling proporcional y separación hechos/decisiones | RECOMMENDED | 2026-08-31 | Incorporado como principio ligero; sin ledger `CONFIRMED/REJECTED/HYPOTHESIS/OPEN` dedicado (remite a `PATTERN-15` si aparece situación). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-013.5` | Feedback loop ejecutable antes de teorizar sobre bugs no triviales | RECOMMENDED | 2026-08-31 | Sección "Diagnóstico con feedback loop" añadida a `AGENTS.md`. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-013.6` | Deliberación barata, transmisión cara | RECOMMENDED | 2026-08-31 | Referencia añadida junto al token economics existente (§7/§13 `ORCHESTRATOR.md`). **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-013.7` | Disciplina de poda y sedimento en el protocolo de release | RECOMMENDED | 2026-08-31 | Esta misma migración aplica poda: `PATTERN-06` reconciliado; propuesta de Project Instructions anterior marcada `SUPERSEDED` en `docs/meta/orchestrator_optimization_after_e3_2026-06-25.md`. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-014.1` | `RETRIEVABLE_EXPERIENCE` | RECOMMENDED | 2026-08-31 | Ledger creado; consulta previa a búsqueda amplia cableada en `AGENTS.md`. **DONE**. |
| `PATTERN-16` | `REPOSITORY_GROUNDED_PREFLIGHT` | RECOMMENDED | 2026-08-31 | `IMPACT`/`BASELINE`/`NORMATIVE_STATE` cableados en `AGENTS.md`; `BASELINE_HEAD` explícito en el handshake. **DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION**. |
| `MR-014.3` | `CANONICAL_CHANGE_ID_FIDELITY` | RECOMMENDED | 2026-08-31 | Aplicada en esta misma reconciliación (§2.1). **DONE**. |

---

## 4 — Cambios críticos pendientes de adopción de release (CRITICAL)

Cambios CRITICAL de releases posteriores a la base que **aún no** tienen disposición terminal de
adopción a nivel de release.

**Ninguno.** Todo `CRITICAL` de MR-001..MR-014 (`PATTERN-01`, `PATTERN-14`) tiene disposición
terminal en §3. `pending_critical: none` en el bloque legible por máquina es correcto en este eje.

### `PATTERN-14` — gate operacional (MR-007, no es `pending_critical` de release)

`PATTERN-14 CONTROLLED_EXTERNAL_WRITE_FOUNDATION` está **adoptado** a nivel de release (§3,
`DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION`). Por separado, su **gate operacional** — si el pathway
real de escritura de órdenes de polymarket-bot cumple los invariantes del foundation — sigue sin
verificarse. Este eje es independiente de la adopción de release y no cuenta como `pending_critical`:

| `risk_live` | `activation_prerequisite` | `blocking_scope` | `runtime_verification` |
|--------------|----------------------------|-------------------|--------------------------|
| `unknown` | `true` | `NEXT_REAL_ORDER_WRITE` | `pending` |

No se investiga en sesiones docs-only (ver `DECISIONS_ALREADY_CLOSED` de la sesión de migración
2026-08-31). Requiere una sesión futura autorizada, con semántica Opus si la superficie de riesgo
real lo exige.

Semántica de los tres ejes de riesgo (`LAFABRICA_RELEASE_PROTOCOL.md §9`):

* `risk_live: unknown` — no se ha verificado si existe superficie vulnerable en producción ahora
  mismo. `SHADOW_ONLY_MODE=true` bloquea el trading real global, lo que sugiere riesgo no vivo, pero
  esta declaración no sustituye la verificación runtime pendiente.
* `activation_prerequisite: true` — si se confirma `risk_live: false`, este gate operacional es
  bloqueante de reactivación: se verifica como primera tarea al reactivar el proyecto, no de
  inmediato.
* `blocking_scope: NEXT_REAL_ORDER_WRITE` — la superficie concreta bloqueada: ninguna escritura de
  orden real puede considerarse segura hasta verificar los invariantes de `PATTERN-14` contra el
  pathway real del bot.

Ningún eje bloquea `CHAT_CLOSE` ni trabajo no relacionado. `NEXT_REAL_ORDER_WRITE = BLOCKED` es la
representación visible de este gate en `docs/meta/ACTIVE_CONTEXT_PACK.md` (`ACTIVE_OPERATION`).

---

## 5 — Cambios recomendados pendientes (RECOMMENDED)

Ninguno. Cobertura completa: todo `RECOMMENDED` aplicable de MR-001..MR-014 tiene disposición `DONE`
o `DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION` en §3, o `NOT_YET_NEEDED` en §6 si su trigger
situacional no se ha cumplido.

---

## 6 — Patrones pendientes opcionales / situacionales (OPTIONAL / on-situation)

`NOT_YET_NEEDED` es un estado completo y válido: no es deuda.

| Cambio | Release | Situación que lo activa | Estado |
|--------|---------|--------------------------|--------|
| `MR-004.2` DOMAIN_PRODUCT_MODELING_GATE — documento local | MR-004 | Tarea real de UI/producto con ambigüedad; crear `docs/patterns/DOMAIN_PRODUCT_MODELING_GATE.md` local | `NOT_YET_NEEDED` |
| `MR-005.4` PACK_INHERITANCE_MODEL | MR-005 | Herencia por bloques gestionados entre múltiples proyectos hijo | `NOT_YET_NEEDED` |
| `MR-005.5` LAFABRICA_PROJECT_METADATA | MR-005 | Necesidad de metadata estructurada de proyecto para tooling externo | `NOT_YET_NEEDED` |
| `MR-006.2` CHILD_PROJECT_REGISTRY | MR-006 | Más de un proyecto hijo a trackear manualmente | `NOT_YET_NEEDED` |
| `PATTERN-13` APPROVED_BASE_DELTA_PATCHING | MR-008 | Ciclo de iteración visual con múltiples agentes y aprobaciones parciales del dashboard | `NOT_YET_NEEDED` |
| `PATTERN-15` PRODUCT_TARGET_CONTRACT_DISCOVERY | MR-010 | Módulo nuevo o rediseño transversal ambiguo dentro del proyecto vivo | `NOT_YET_NEEDED` |
| `MR-010.2` Wiring pre-CODE de PATTERN-15 | MR-010 | Mismo trigger que `PATTERN-15` | `NOT_YET_NEEDED` |
| `MR-013.4` Prototipo visual desechable | MR-013 | Redisño de UI/producto visual con validación previa a implementación costosa | `NOT_YET_NEEDED` |

---

## 7 — Cambios no aplicables (NOT_APPLICABLE)

DOMAIN_SPECIFIC fuera del dominio de este proyecto, o mecanismo histórico que este proyecto nunca
adoptó. **No son deuda, son correctamente descartados.**

| Cambio | Release | Dominio del cambio | Por qué no aplica aquí |
|--------|---------|--------------------|------------------------|
| `PATTERN-08` TRANSACTIONAL_EMAIL_PRODUCTION_GATE | MR-002 | e-commerce/CMS con email transaccional | polymarket-bot es un bot de trading; no hay email transaccional |
| `PATTERN-09` ECOMMERCE_HOOK_STATE_GUARD | MR-002 | e-commerce/CMS | no hay hooks de e-commerce |
| `PATTERN-11` GSC_API_READONLY_CONNECTOR | MR-008 | seo / observability (Google Search Console) | no hay superficie SEO ni conector GSC |
| `PATTERN-12` B2B_RETAIL_FALLBACK_DETECTION | MR-008 | e-commerce / B2B | no hay superficie de retail/B2B |
| `MR-011.7` Cierre histórico de CROSS_AGENT_CONTEXT_ENGINEERING | MR-011 | mecanismo histórico interno de lafabrica | polymarket-bot nunca adoptó esa capa metodológica separada; no hay nada que cerrar aquí |

---

## 8 — Notas de adopción

- **PATTERN-06 reconciliado (2026-08-31):** la adopción anterior (2026-06-26) clasificaba
  `agent_events.jsonl` como implementación de `PATTERN-06 AGENT_EXPERIENCE_LEDGER`. Es incorrecto:
  `agent_events.jsonl` es un log máquina resumido, no un índice de caminos conocidos por tipo de
  tarea. Se creó `docs/meta/AGENT_EXPERIENCE_LEDGER.md` vacío como implementación correcta.
- **PATTERN-02:** polymarket-bot no tiene `BACKLOG.md` ni `DECISIONS.md` con esos nombres exactos;
  la gobernanza equivalente existe a través de `ORCHESTRATOR.md`, `HISTORIAL_SESIONES.md` y el
  historial de decisiones embebido en `CONTEXTO.md` (>400 sesiones). El patrón está adoptado en
  espíritu — ver `DECISIONS_ALREADY_CLOSED` de la migración 2026-08-31: `BACKLOG.md` y
  `DECISIONS.md` explícitamente no se crean.
- **PATTERN-05:** L0 (`ACTIVE_CONTEXT_PACK.md`) y parte de L1 (`.codex/skills/context-bootstrap/SKILL.md`
  como router) están en su lugar; L2 (`STATUS.md` por módulo) no se creó — fuera de `EXACT_SCOPE` de
  la migración 2026-08-31. Reabrir si el coste de arranque por módulo se vuelve un blocker medible.
- **Orca worktree-per-outcome:** candidato metodológico abstracto registrado en
  `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` (SLT-004). `CANDIDATE_CHILD_LOCAL`, no estándar de
  lafabrica todavía.
- Esta migración se hizo en STANDBY: adopción documental de MR-004..MR-014, incluidos los CRITICAL
  aplicables (`PATTERN-14` documentalmente; `MR-012.6` ya cubierto de forma más estricta). No se
  absorbieron cambios que requirieran tocar runtime, tests, dependencias o Railway.

---

## 9 — Siguiente revisión recomendada

- **Cuándo:** `on-reactivation`
- **Disparador:** salir de STANDBY (requiere cambio de `SHADOW_ONLY_MODE` en Railway con
  autorización explícita de Pablo) / nueva release de lafabrica detectada / resolución de
  `PATTERN-14` mediante sesión autorizada separada
- **Primera tarea de esa revisión:** (1) resolver `PATTERN-14` — verificar runtime el pathway real
  de escritura de órdenes contra los invariantes del foundation; (2) diffear `lafabrica_release_base`
  (MR-014) contra la release actual del Release Ledger; adoptar `CRITICAL` si aplica antes de
  retomar features.

---

## 10 — Checklist de privacidad y no-cascada

```
[x] Este archivo no contiene credenciales, PII, datos de clientes/pedidos/precios ni rutas reales
[x] Las notas de adopción describen metodología, no lógica de negocio sensible
[x] privacy_level marcado correctamente (INTERNAL_ONLY)
[x] La adopción se hizo por PULL: lafabrica no empujó cambios a este repo
[x] Si hubo APPLY, fue tras PLAN aprobado (orquestador), un solo hijo por sesión y sin push automático
[ ] Si hubo migración, fue explícita, autorizada por el operador y registrada en DECISIONS.md de este proyecto
    (no aplica: polymarket-bot no tiene DECISIONS.md discreto — ver nota PATTERN-02 en §8;
    la autorización queda en el handshake/ASSIGNMENT de la sesión, HISTORIAL_SESIONES.md y agent_events.jsonl)
[x] DOMAIN_SPECIFIC fuera de dominio están marcados NOT_APPLICABLE, no copiados
[x] No se adoptó nada estando en STANDBY salvo CRITICAL con riesgo vivo o no vivo pero documentado (PATTERN-14, MR-012.6)
[x] Los bloques gestionados, si existen, tienen BEGIN/END únicos y balanceados (UPDATE_NOTIFICATION_CHECK MR-008)
```

---

## Ejemplo de uso por dominio (orientativo — heredado de la plantilla)

Cómo cuatro proyectos distintos rellenarían la sección 7 frente a MR-002 (que trae `PATTERN-08` y
`PATTERN-09`, ambos DOMAIN_SPECIFIC[e-commerce/CMS]): polymarket-bot es el proyecto **trading**, que
marca ambos `NOT_APPLICABLE` — resultado completo y correcto, no deuda. Ver
`LAFABRICA_RELEASE_PROTOCOL.md` para la tabla completa de ejemplo.

---

## Historial de adopción

| Fecha | Release adoptada | Cambio | Quién |
|-------|------------------|--------|-------|
| 2026-06-26 | MR-003 | Primera declaración de adopción: MR-001..MR-003 revisadas; PATTERN-01..07 evaluados; PATTERN-08/09 descartados (NOT_APPLICABLE) | Claude Code / Sonnet (DOCS_ONLY) |
| 2026-08-31 | MR-014 | Migración de sistema operativo documental MR-003 → MR-014. Cobertura completa 65/65 `change_id`. `PATTERN-06` reconciliado (agent_events.jsonl ≠ ledger). `PATTERN-14` con disposición de release terminal (`DONE_WITH_PROJECT_SPECIFIC_IMPLEMENTATION`, §3) — `pending_critical: none` correcto; su gate operacional (`risk_live`/`activation_prerequisite`/`blocking_scope`/`runtime_verification: pending`) queda representado aparte en §4, sin contar como deuda de adopción de release, y `NEXT_REAL_ORDER_WRITE = BLOCKED` sigue explícito. Creados `docs/meta/ACTIVE_CONTEXT_PACK.md`, `docs/meta/AGENT_EXPERIENCE_LEDGER.md`, `docs/meta/ACTIVE_DECISION_STATE.md`, `docs/orchestrator_chatgpt_project_instructions.md`. `ORCHESTRATOR.md`/`AGENTS.md` actualizados por delta. STANDBY sin cambio; sin runtime/Railway/env vars/trading. | Claude Sonnet 5 (DOCS_ONLY, A2 APPLY_LOCAL) |
| 2026-08-31 | MR-014 | `FIX_BLOCKER_FIRST`: corregida la representación de `pending_critical` (era `[ PATTERN-14 ]`, incompatible con `lafabrica_release_base: MR-014` — un `change_id` con disposición terminal de release no puede figurar como pendiente de adopción). Restaurado `pending_critical: none`; `PATTERN-14` movido a §3 con disposición terminal; §4 reframeado como gate operacional dedicado (no release-pending), preservando íntegros `risk_live: unknown`, `activation_prerequisite: true`, `blocking_scope: NEXT_REAL_ORDER_WRITE`. Sin cambios en la cobertura 65/65 ni en el resto de disposiciones. | Claude Sonnet 5 (DOCS_ONLY, A2 APPLY_LOCAL) |
