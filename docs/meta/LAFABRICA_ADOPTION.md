# LAFABRICA_ADOPTION.md — polymarket-bot

Declaración de adopción metodológica de este proyecto hijo frente a lafabrica.

**Copiar a:** `docs/meta/LAFABRICA_ADOPTION.md` del proyecto hijo.
**Fuente del protocolo:** `lafabrica-template/docs/orchestrator/LAFABRICA_RELEASE_PROTOCOL.md`.
**Política:** este archivo es la **única fuente de verdad** de qué release y patrones metodológicos tiene adoptados este proyecto. El operador no recuerda el estado de cada repo — lo lee aquí.
**Quién mantiene:** Orquestador, al adoptar una release y al reactivar el proyecto. Modelo **pull**: lafabrica nunca empuja; este proyecto adopta cuando le toca.

---

## Estado de adopción (bloque legible por máquina)

```
project: polymarket-bot
domain: trading — prediction-market bot
lafabrica_release_base: MR-003
lafabrica_release_current_seen: MR-003
pending_critical: none
pending_recommended: [ PATTERN-05, PATTERN-07 ]
project_state: STANDBY
last_reviewed: 2026-06-26
next_review_recommended: on-reactivation
privacy_level: INTERNAL_ONLY
```

---

## 1 — Identidad

- **Proyecto:** polymarket-bot
- **Dominio:** trading — prediction-market bot (weather-based markets en Polymarket)
- **Estado del proyecto:** STANDBY (Bot Stable v0; SHADOW_ONLY_MODE=true en Railway)
- **Fecha de última revisión de adopción:** 2026-06-26

---

## 2 — Release base adoptada

- **Release base de lafabrica adoptada:** MR-003
- **Release actual de lafabrica vista en esta revisión:** MR-003 (del Release Ledger en `LAFABRICA_RELEASE_PROTOCOL.md`)
- **Gap:** ninguno

---

## 3 — Patrones adoptados

| Patrón | Tipo de cambio | Adoptado en | Nota |
|--------|----------------|-------------|------|
| PATTERN-01 SHADOW_FIRST | CRITICAL | sesión 424, 2026-06-10 | SHADOW_ONLY_MODE=true seteado en Railway; kill switch global activo; BUY real bloqueado |
| PATTERN-02 LONG_RUNNING_PROJECT_GOVERNANCE | RECOMMENDED | vigente (>400 sesiones) | ORCHESTRATOR.md, CONTEXTO.md, HISTORIAL_SESIONES.md, AGENTS.md, OPERATIONS_PLAYBOOK.md presentes; estructura de gobernanza madura |
| PATTERN-03 STANDBY_AS_FIRST_CLASS_STATE | RECOMMENDED | sesión 423, 2026-06-09 | OPERATIONAL_PHASE=STANDBY default en código; Bot Stable v0 declarado; alarmas silenciadas en STANDBY |
| PATTERN-04 SLT_MIGRATION_IN_ACTIVE_REPOS | RECOMMENDED | sesión SLTSSF, 2026-06-20 | `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` instalado; bloque SLT en AGENTS.md; reglas de privacidad específicas documentadas |
| PATTERN-06 AGENT_EXPERIENCE_LEDGER | RECOMMENDED | vigente | `agent_events.jsonl` presente en la raíz del repo; parte del contrato en AGENTS.md §Cierre |

---

## 4 — Cambios críticos pendientes (CRITICAL)

| Cambio | Release | ¿Riesgo vivo aquí? | Acción | Estado |
|--------|---------|--------------------|--------|--------|
| — | — | — | — | none |

No hay CRITICAL pendientes. PATTERN-01 SHADOW_FIRST está adoptado; SHADOW_ONLY_MODE=true activo en Railway desde 2026-06-10.

---

## 5 — Cambios recomendados pendientes (RECOMMENDED)

| Cambio | Release | Adoptar cuándo | Estado |
|--------|---------|----------------|--------|
| PATTERN-05 AI_FIRST_LAYERED_DOCUMENTATION | MR-002 | on-reactivation | PENDING — trigger historial >50KB cumplido; estructura de lectura mínima presente en CLAUDE.md pero adopción completa no verificada |
| PATTERN-07 STOP_AND_REPLAN_MICROPATCH_PROTOCOL | MR-002 | on-reactivation | PENDING — elementos análogos presentes en AGENTS.md §Codex Operating Pattern pero protocolo formal no verificado |

---

## 6 — Patrones pendientes opcionales / situacionales (OPTIONAL)

No hay patrones OPTIONAL en MR-001..MR-003.

---

## 7 — Cambios no aplicables (NOT_APPLICABLE)

| Cambio | Release | Dominio del cambio | Por qué no aplica aquí |
|--------|---------|--------------------|------------------------|
| PATTERN-08 TRANSACTIONAL_EMAIL_PRODUCTION_GATE | MR-002 | e-commerce/CMS con email transaccional | polymarket-bot es un bot de trading en mercados de predicción; no hay email transaccional |
| PATTERN-09 ECOMMERCE_HOOK_STATE_GUARD | MR-002 | e-commerce/CMS | polymarket-bot es un bot de trading; no hay hooks de e-commerce |

---

## 8 — Notas de adopción

- PATTERN-02: polymarket-bot no tiene `BACKLOG.md` ni `DECISIONS.md` con esos nombres exactos; la gobernanza equivalente existe a través de ORCHESTRATOR.md, HISTORIAL_SESIONES.md, `docs/ESTRATEGIA_OPERATIVA.md`, `docs/SISTEMA_MEJORA_CONTINUA.md` y el historial de decisiones embebido en CONTEXTO.md (>400 sesiones). El patrón está adoptado en espíritu.
- PATTERN-05: la primera tarea de la reactivación debe verificar si la estructura documental actual cumple la definición completa de AI_FIRST_LAYERED_DOCUMENTATION según `ECOSYSTEM_LEARNING_PATTERNS.md`.
- PATTERN-07: verificar en reactivación si el protocolo STOP_AND_REPLAN_MICROPATCH está documentado en ORCHESTRATOR.md §16 o equivalente, más allá del ASK/CODE pattern de AGENTS.md.
- Esta adopción se hizo en STANDBY: solo declaración documental. No se absorbieron patrones nuevos ni se abrieron tareas de mejora.

---

## 9 — Siguiente revisión recomendada

- **Cuándo:** `on-reactivation`
- **Disparador:** salir de STANDBY (requiere cambio de `SHADOW_ONLY_MODE` en Railway con autorización explícita de Pablo) / nueva release de lafabrica detectada
- **Primera tarea de esa revisión:** diffear `lafabrica_release_base` (MR-003) contra la release actual del Release Ledger; adoptar CRITICAL si aplica + PATTERN-05 + PATTERN-07 antes de retomar features

---

## 10 — Checklist de privacidad y no-cascada

```
[x] Este archivo no contiene credenciales, PII, datos de clientes/pedidos/precios ni rutas reales
[x] Las notas de adopción describen metodología, no lógica de negocio sensible
[x] privacy_level marcado correctamente (INTERNAL_ONLY)
[x] La adopción se hizo por PULL: lafabrica no empujó cambios a este repo
[ ] Si hubo migración, fue explícita, autorizada por el operador y registrada en DECISIONS.md de este proyecto
    (no aplica: no hubo migración, solo declaración documental)
[x] DOMAIN_SPECIFIC fuera de dominio están marcados NOT_APPLICABLE, no copiados
[x] No se adoptó nada estando en STANDBY salvo CRITICAL con riesgo vivo (no había CRITICAL pendiente)
```

---

## Historial de adopción

| Fecha | Release adoptada | Cambio | Quién |
|-------|------------------|--------|-------|
| 2026-06-26 | MR-003 | Primera declaración de adopción: MR-001..MR-003 revisadas; PATTERN-01..07 evaluados; PATTERN-08/09 descartados (NOT_APPLICABLE) | Claude Code / Sonnet (DOCS_ONLY) |
