# SYSTEM_LEARNING_TRANSFER_FROM_LAFABRICA_AND_BRAIN — 2026-06-25

**Sesión:** POLYMARKET_SYSTEM_UPGRADE_FROM_LAFABRICA_AND_OPERATING_BRAIN (S426)
**Modelo:** Claude Opus 4.8 · READ_ONLY / ARCHITECTURE_TRANSFER / DOCS_PATCH_IF_SAFE
**Estado del bot durante la sesión:** STANDBY · `SHADOW_ONLY_MODE=true` · BANKROLL HOLD $25 · Fase C no autorizada · camino vivo = ratificación E3 trader-following.

> Este documento es **docs-only / meta**. No toca trading, runtime, env vars, Railway, DB, scheduler,
> city modes, exact/NO, guards, SL, BUY/SELL/SKIP, BANKROLL ni Fase C. **No autoriza salir de STANDBY.**
> Es la contraparte **entrante** (qué absorbe polymarket-bot del ecosistema) de la cola **saliente**
> `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` (qué exporta polymarket-bot al ecosistema).

---

## 0. TL;DR — la premisa estaba invertida

La sesión se abrió asumiendo que polymarket-bot tiene "una estructura más vieja" y debe **absorber**
mejoras de LaFábrica Template y Pablo Operating Brain. La evidencia dice lo contrario:

> **Polymarket-bot es el repo de origen del sistema operativo del ecosistema, no el rezagado.**

Tres pruebas independientes:

1. **LaFábrica README:** *"El proyecto nace con la forma probada en 361 sesiones de un proyecto previo
   (Polymarket Bot)."* LaFábrica fue construida **desde** los patrones de este repo.
2. **Brain `docs/imports/SESSION_LEARNING_TRANSFER_ABSORB_LOG.md` (2026-06-20):** los candidatos
   `SLT-001/002/003` de polymarket-bot (SHADOW_MODE, LONG_RUNNING_GOVERNANCE, STANDBY_AS_FIRST_CLASS)
   fueron **absorbidos al Brain** (EVID-005) y recomendados a LaFábrica (`REC-LF-001/002/003`).
3. **LaFábrica `docs/orchestrator/ECOSYSTEM_LEARNING_PATTERNS.md`:** PATTERN-01 (SHADOW_FIRST),
   PATTERN-02 (LONG_RUNNING_PROJECT_GOVERNANCE), PATTERN-03 (STANDBY) son literalmente
   derivados de polymarket-bot.

Conclusión: el loop de transferencia **ya está cableado y mayormente saliente**. El último commit del
repo (`590d41a docs(meta): install session learning transfer and standby flow`) ya instaló el flujo de
learning-transfer y STANDBY en ORCHESTRATOR/AGENTS + creó la cola. **Lo entrante que queda es pequeño y,
en su mayoría, NO conviene ejecutarlo mientras volvemos a E3** (sería migración, no saneamiento).

---

## A. SOURCES_READ

**Polymarket-bot (primario):**
- `git status --short --untracked-files=all` (limpio salvo untracked preexistentes `2026-04-27]`, `342)`), `git log -1` (`590d41a`).
- `ORCHESTRATOR.md` (completo, act. 2026-05-13) · `AGENTS.md` (completo).
- `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` (cola saliente, SLT-001/002/003).
- `docs/standby_alarm_hygiene_v0.md` · `docs/predictive/trader_following_benchmark_protocol.md` (E3 design-only).
- `agent_events.jsonl` tail (S419→S424) · `HISTORIAL_SESIONES.md` tail (cierra en S418).
- Índice `docs/*.md` (428 archivos) y raíz `*.md` (sin BACKLOG/DECISIONS/TOKEN_ECONOMICS/PROJECT_BRIEF discretos).

**LaFábrica Template (proporcional):**
- `README.md` · `ORCHESTRATOR.md` · `TOKEN_ECONOMICS.md` · `docs/orchestrator/lifecycle.md`.
- Índice `docs/orchestrator/**` (confirmado: `ECOSYSTEM_LEARNING_PATTERNS.md`, `CHILD_PROJECT_TRANSFER_PROTOCOL.md`, `discovery_intake_pack/`, `company_brain_pack/`).

**Pablo Operating Brain (proporcional):**
- `docs/imports/SESSION_LEARNING_TRANSFER_ABSORB_LOG.md` · `docs/imports/polymarket-bot/SUMMARY.md`.

**Missing / no leído por token-economics (deliberado):**
- `CONTEXTO.md` cuerpo (2741 líneas; lectura falló por tamaño). Estado vivo establecido vía ORCHESTRATOR §15
  + standby doc + agent_events + contexto del prompt; suficiente para un análisis meta. No se forzó.
- `OPERATIONS_PLAYBOOK.md` (no toca runtime/deploy esta sesión).
- LaFábrica: `AGENTS.md`, `OPERATIONS_PLAYBOOK.md`, design docs, `discovery_intake_pack/*`, `company_brain_pack/*`,
  cuerpos de `templates/orchestrator/*` y `ECOSYSTEM_LEARNING_PATTERNS.md` (solo confirmada su existencia).
- Brain: `ORCHESTRATOR.md`, `TOKEN_ECONOMICS.md`, profile/knowledge/strategy docs.
- Los 428 `docs/*.md` de polymarket (solo se leyó el índice).

---

## B. DIAGNOSIS

### Qué está VIEJO en polymarket-bot (fricción real, no falta de gobernanza)
1. **Doc sprawl: 428 archivos en `docs/` + ~12 dated en raíz** (`RESEARCH_*`, `*_HANDOFF_*`, `SNAPSHOT_*`,
   `claude-opus-prompt-*`, `*-readout-*`, `next-session-handoff-*`). Es el costo de 6 meses **sin** archivos
   discretos `BACKLOG.md`/`DECISIONS.md` desde el día 1 — exactamente el arranque caótico que LaFábrica nació
   para cortar. **El sprawl es histórico; el fix NO es borrado masivo** (prohibido + riesgoso), sino disciplina
   forward + un índice.
2. **Token-economics triplicado en ORCHESTRATOR.md** (§3 "Token economics", §12 "Token Economics Gate",
   §13 "tokens-as-payroll"): tres secciones solapadas que accretaron. LaFábrica lo tiene en un `TOKEN_ECONOMICS.md`
   único. (Consolidar = edición mayor del archivo joya; no ahora.)
3. **Drift de fuentes de cierre:** `HISTORIAL_SESIONES.md` cierra en **S418**; `agent_events.jsonl` llega a
   **S424**. Las narrativas humanas de S419–S425 viven solo en el log máquina. Parcialmente **by-design**
   (los cierres LITE docs-only legítimamente saltan HISTORIAL), pero HISTORIAL deja de ser narrativa completa.

### Qué está BIEN y debe CONSERVARSE (no diluir con genéricos)
- **Guardrails de trading más estrictos que el template.** ORCHESTRATOR §8/§9/§11, AGENTS guardrails y la
  separación dura `realized PnL ≠ outcome ≠ forecast ≠ liquidity exit` son **superiores** a los genéricos de
  LaFábrica. No reemplazar lenguaje de riesgo específico por versiones genéricas.
- **Token economics tokens-as-payroll (§13), Connected Learning Loop (§14), STANDBY flow (§15).** Más maduros
  que cualquier cosa del ecosistema. Son el origen de los patrones absorbidos.
- **Provenance de decisiones de trading** en HISTORIAL + agent_events + dossiers fechados. Bifurcar esto a un
  `DECISIONS.md` paralelo mid-flight es **riesgo**, no mejora.

### Fricción que venimos repitiendo
- Cada avance genera dated docs nuevos en vez de mover ítems en archivos discretos vivos → el sprawl crece.
- Tres lugares para "lo mismo" (token economics) cuestan relectura.
- "Próximos pasos / triggers" viven dispersos (CONTEXTO + memoria + handoff docs), sin un único `BACKLOG.md`.

### Mejoras externas que SÍ aplican (pequeñas, entrantes) → ver tabla C, todas DEFER
`BACKLOG.md` discreto · plantillas de prompt reutilizables · §17 Workstream Anchor · §16 AI-First como lista.

### Mejoras externas que NO aplican
- Maquinaria greenfield de creación de proyectos: SEED, `lafabrica new/continue/open`, Discovery Intake Pack,
  Company Brain/RAG, `--agent-surface`/Antigravity. Polymarket **ya existe**; es la plantilla **fuente**, no un
  consumidor del launcher.
- Cualquier cosa que diluya guardrails de trading o reabra superficie operativa.

---

## C. TRANSFERABLE_LESSONS

| # | Aprendizaje | Fuente | ¿Aplica? | Cómo aplicarlo | Riesgo | ¿Patch ahora? |
|---|---|---|---|---|---|---|
| L1 | `BACKLOG.md` discreto NOW/NEXT/LATER/BLOCKED | LaFábrica/Brain | Sí, parcial | Un archivo nuevo que centralice triggers/próximos pasos (E3, exact/NO, Outcome Resolver) | Bajo, pero es migración + duplica CONTEXTO si no se sincroniza | **DEFER** (trigger D1) |
| L2 | Plantillas de prompt reutilizables (`SESSION_CLOSE`, `SESSION_CONTINUE`, `HANDOFF`, `PROJECT_START`, agent_prompts) | LaFábrica `templates/orchestrator/` | Sí | Reemplazan los dated `next-session-handoff-*` / `claude-opus-prompt-*` one-off | Bajo | **DEFER** (trigger D2) |
| L3 | §17 Workstream Anchor (`PROJECT/SUBSYSTEM/BLOCK`) | LaFábrica ORCHESTRATOR §17 | Sí | Nombrar el workstream al abrir sesión; evita mezclar líneas (E3 vs Phase 2) | Muy bajo | **DEFER** (trigger D3) — candidato más barato |
| L4 | §16 AI-First como lista de 7 principios nombrada | LaFábrica ORCHESTRATOR §16 | Parcial | Ya están dispersos en guardrails; nombrarlos es cosmético | Muy bajo | **NO** (ya cubierto en sustancia) |
| L5 | `TOKEN_ECONOMICS.md` como archivo único | LaFábrica/Brain | Sí, conceptual | Consolidar ORCHESTRATOR §3/§12/§13 redundantes | Medio (edita archivo joya; riesgo de perder matices) | **DEFER** (trigger D4) |
| L6 | `DECISIONS.md` discreto | LaFábrica/Brain | **No para trading** | — | Alto: bifurca provenance de decisiones de riesgo ya canónica | **NO** |
| L7 | `docs/orchestrator/lifecycle.md` (diagrama de ciclo) | LaFábrica | Marginal | Ya implícito en ORCHESTRATOR §6/§10/§15 | Bajo | **NO** |
| L8 | Higiene anti-sprawl: índice de `docs/` + mover, no acumular | Inferencia (LaFábrica corta el arranque caótico) | Sí | Forward: un `docs/INDEX.md` y disciplina de mover ítems; **sin borrar** histórico | Bajo si solo-añadir | **DEFER** (trigger D5) |

**Regla dura de esta tabla:** ninguna fila ejecuta ahora. Todas son `TRIGGER_DEFINED`. El default es
**no hacer nada** hasta resolver E3; revisar una fila **solo** si su trigger concreto dispara.

---

## D. POLYMARKET_OPERATING_SYSTEM_VNEXT (recomendación, no ejecución)

El "vNext" de polymarket **no es un sistema nuevo**: es el actual + 3 ajustes baratos cuando toque, sin migración:

- **Arranque de sesión:** mantener ORCHESTRATOR §1 (lectura proporcional). Añadir, cuando se adopte L3, el
  ancla `PROJECT / SUBSYSTEM / BLOCK` en una línea al abrir (evita mezclar E3 con Phase 2 / exact/NO).
- **Token economics:** mantener §13 como canon. Si algún día molesta la triplicación (§3/§12/§13), consolidar
  en un `TOKEN_ECONOMICS.md` (L5) — **no antes** de que cause fricción real medible.
- **Cuándo Opus:** decisión semántica/estratégica de trading/riesgo (BANKROLL, SL, city promotion, gates,
  ratificación E3). Sin cambios — ya correcto.
- **Cuándo Codex:** patches/tools/tests/Railway técnico con trigger. Sin cambios.
- **Cuándo Sonnet:** docs, cierres, síntesis, handoffs, auditorías read-only no delicadas. Sin cambios.
- **Cuándo modelos caros:** solo decisión binaria o diseño con riesgo; no para confirmar WATCH ni backlog genérico.
- **Cierre:** proporcional LITE/NORMAL/FULL (ya canon). **Reducir el drift HISTORIAL↔agent_events**: si un cierre
  LITE salta HISTORIAL, dejar **un puntero de una línea** en HISTORIAL apuntando al evento, para que la narrativa
  no se rompa. No backfill masivo.
- **Registrar aprendizajes:** salientes → cola SLT; entrantes → este doc. No duplicar en memoria externa.
- **Evitar tooling-por-tooling:** ORCHESTRATOR §9/§13.F ya lo cubre. Mantener.
- **STANDBY:** ORCHESTRATOR §15 es canon. Este doc no lo altera.
- **Triggers tipo E3:** un trigger no congela workstreams independientes (ORCHESTRATOR §8). Volver a E3 es el
  camino vivo; este doc no es un desvío.
- **Runtime/Railway/env vars:** intocables esta sesión. Salir de STANDBY sigue siendo cambio FULL con
  autorización literal de Pablo.
- **Patches vs diseño:** este doc es diseño/registro; cualquier ejecución de L1–L8 es sesión futura separada.
- **Impedir que cada avance genere 3 tareas:** las 8 lecciones quedan **parqueadas con trigger**, no abiertas.
  El default es cero acción.

### Triggers de reapertura (para no perder los candidatos sin abrir backlog amplio)
- **D1 (BACKLOG.md):** si en ≥2 sesiones futuras se vuelve a perder un "próximo paso" por estar disperso.
- **D2 (plantillas prompt):** la próxima vez que se cree un handoff/prompt one-off reutilizable → hacerlo plantilla.
- **D3 (Workstream Anchor):** si una sesión mezcla E3 con otra línea sin querer → adoptar el ancla.
- **D4/L5 (TOKEN_ECONOMICS.md):** si la triplicación §3/§12/§13 causa una contradicción real.
- **D5 (índice docs):** si una búsqueda en `docs/` falla por sprawl en una sesión operativa.

Si ningún trigger dispara, **no se toca nada**: el sistema actual es suficiente.

---

## E. PATCH_DECISION

**`DOC_PATCH_SAFE_NOW`** (mínimo):
1. Este documento (`docs/meta/system_learning_transfer_from_lafabrica_2026-06-25.md`) — nuevo, durable.
2. Un puntero de una línea en `ORCHESTRATOR.md §15` para descubrir este doc entrante junto a la cola saliente.
3. Cierre proporcional: una entrada en `HISTORIAL_SESIONES.md` (S426) + una línea en `agent_events.jsonl`.
4. **No** se toca `CONTEXTO.md` (no hay cambio operativo vivo: sigue STANDBY/E3). **No** `verify_before_deploy.py`
   (docs-only). **No** runtime/Railway/env vars. **No** se borra nada. **No** se ejecuta ninguna fila C.

---

## F. NEXT_STEP_AFTER_THIS

- Tras esta sesión vuelve la **ratificación estratégica E3 trader-following** (gate pasó en check oficial tardío:
  celda `60-70|trader_NO|no`, forward_n=73, top1 28.77%, edge_ci.lower 0.0571, WR 86.3%, sim_unit_pnl_mean 0.1257).
- Prompt recomendado: **`E3_TRIGGER_PASS_RATIFICATION_FOLLOWER_EXPERIMENT`** (ya preparado) para decidir si
  diseñar el experimento follower **LOG_ONLY/paper**.
- Esta sesión **no abre backlog**: las 8 lecciones quedan DEFER con trigger. El foco regresa a E3 sin reabrir
  Phase 2 ni tocar trading.
