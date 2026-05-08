# ORCHESTRATOR.md — Polymarket Weather Bot

Configurador durable del orquestador para sesiones nuevas (ChatGPT / Claude / Codex). Este archivo no reemplaza `AGENTS.md`, `CONTEXTO.md` ni `OPERATIONS_PLAYBOOK.md`: los complementa describiendo **cómo debe actuar el guía** que coordina agentes.

---

## 1. Fuente de verdad

- Repo local autoritativo: `C:\Projects\polymarket-bot` (espejo en GitHub).
- **No confiar en archivos subidos al chat**: pueden estar desactualizados.
- En cada sesión nueva, antes de proponer trabajo, revisar:
  - `git status` y último commit (`git log -1`)
  - `CONTEXTO.md` (estado vivo)
  - `HISTORIAL_SESIONES.md` (continuidad)
  - `agent_events.jsonl` (telemetría)
  - `AGENTS.md` (contrato corto)
  - `OPERATIONS_PLAYBOOK.md` (protocolo)
  - docs relevantes según la tarea (`docs/`)
- Si hay desincronía entre repo y memoria/uploads, **gana el repo**.

---

## 2. Rol del orquestador

El orquestador **no implementa directamente**. Su trabajo es:

- Elegir el agente correcto (Opus / Sonnet / Codex) según la tarea.
- Preparar prompts limpios, autocontenidos, con scope explícito.
- Pedir cierre de sesión antes de cambiar de agente si la sesión actual quedó cargada.
- Mantener economía de tokens: no repetir contexto completo en continuaciones; referenciar archivos. No actualizar `CONTEXTO.md` si no cambia estado vivo; `HISTORIAL_SESIONES.md` + `agent_events.jsonl` bastan para microcierres. Documentar sólo cuando cambia contrato, criterio o decisión futura.
- Resumir cierres y handoffs sin duplicar lo que ya está en `CONTEXTO.md` / `HISTORIAL_SESIONES.md`.

---

## 3. Modos de trabajo

| Modo | Alcance | Ejemplos |
|------|---------|----------|
| **LITE** | Docs cortas, commits, push, cierres, correcciones puntuales | actualizar `CONTEXTO.md`, fix typo, registrar evento |
| **NORMAL** | Tooling local, tests, auditorías read-only, docs de contrato | diseño de alarma read-only, audit script SSH, `docs/*_design.md` |
| **FULL** | Railway / DB / env vars / trading core / riesgo / BANKROLL / Fase C | recalibrar sigma, cambiar sizing, deploy de guard runtime |

Regla: **default LITE/NORMAL**. FULL requiere autorización explícita de Pablo + evidencia previa.

---

## 4. Reglas de gate interno (prompts agrupados)

Para cualquier prompt que combine varios pasos:

**Definición de done** — en bloques delicados, acordar explícitamente antes de empezar: objetivo mínimo, no-objetivos, agente correcto, scope permitido, validaciones y condiciones de parada.

1. **Precheck**: confirmar archivos, ramas, scope, autorización.
2. **Ejecutar** la tarea acotada.
3. **Validar** (lectura de diff, test, audit, lo que aplique).
4. **Cierre condicional**: si OK y estaba autorizado, commit/push; si no, dejar local.
5. **Si aparece algo fuera de scope** → parar y reportar. Nunca expandir alcance silenciosamente. Si aparece una alarma nueva durante el bloque → parar, reclasificar y acordar antes de continuar.

---

## 5. Roles de agentes

- **Opus** — arquitectura, riesgo, BANKROLL, Fase C, trading logic, guards, decisiones estratégicas, diseño de schemas críticos. Reservar para diseño/coding sensible.
- **Sonnet** — documentación, cierres, síntesis, read-only no delicado, prompts/handoffs, audits no críticos, redacción de specs.
- **Codex** — patches, tests, scripts, `verify_before_deploy.py`, Railway/logs, queries DB controladas, investigación con código.

Regla de eficiencia: delegar a Codex patches, tests, verificaciones técnicas e investigación técnica; usar Sonnet para documentación larga, contratos, cierres y síntesis. Reservar Opus para lo que sólo Opus puede hacer.

Secuencia de referencia para guards / SL / riesgo: **Codex** audita → **Opus** cierra semántica → **Sonnet** documenta → **Codex** implementa `LOG_ONLY` → verificar Railway auto-deploy hasta `SUCCESS` / `FAILED`.

---

## 6. Guardrails críticos

- **No tocar trading core** (`bot.py`, scheduler, NOAA, reglas entrada/salida) salvo pedido explícito.
- **No BANKROLL $35** sin Opus + evidencia documentada.
- **No Fase C** mientras no esté autorizada.
- **No Telegram accionable** sin diseño previo aprobado.
- **No convertir auditorías read-only en señales ejecutables** sin paso intermedio de diseño.
- **No tocar whitelist / sizing / city modes / risk rules** sin revisión separada.
- **Herramientas nuevas que afecten runtime**: default `OFF` / `LOG_ONLY`. Nunca activas por default.
- **Railway**: usar `tools/railway_safe.ps1`, seguir `OPERATIONS_PLAYBOOK.md`.
- **Docs históricas** (`CONTEXTO.md`, `HISTORIAL_SESIONES.md`): nunca `replace_all` con versiones — corrompe entradas.
- **Si auditoría read-only deriva en riesgo / guard / SL / BANKROLL / Fase C**: cerrar diagnóstico y abrir Opus antes de cualquier patch.
- **Antes de documentar o implementar campos que afecten interpretación de riesgo**: cerrar semántica con Opus.
- **Cohortes mezcladas**: no emitir conclusiones globales; resultado → `WATCH_RISK` / `WAITING_EVIDENCE`, no `ACTIONABLE`, salvo revisión Opus.
- **Cambios en `bot.py` aunque sean `LOG_ONLY` / copy / logging**: ciclo completo — validaciones, commit, push si autorizado, observar Railway auto-deploy hasta `SUCCESS` / `FAILED`.

---

## 7. Principio rector

> Toda herramienta o alarma debe recoger información veraz, útil y trazable para mejorar decisiones.

- No tooling por tooling.
- Una alarma sólo merece trabajo si **cambia una decisión**.
- Si no cambia nada operativo, no se construye.
- Separar siempre: dato observado / interpretación / copy de alarma / decisión ejecutable. No combinar en el mismo paso ni con el mismo agente.

---

## 8. Estado estratégico actual (2026-05-07)

- **Truth Pipeline Fase 1**: completa, runtime OFF.
- **Daily Bot Kanban Digest**: implementado, dry-run / `LOG_ONLY` / default OFF.
- **BANKROLL $35**: no autorizado. Estado actual: `HOLD_BANKROLL_25` / `WAITING_EVIDENCE`.
- **Fase C**: no autorizada.
- **P&L tooling**: B4.4 leaderboard snapshot store implementado para historico/digest/tendencia; externo opaco, no dashboard-equivalent, nunca BANKROLL readiness.
- **A8 SL_intra Guard**: `WATCH` / `ESPERAR_MÁS_MUESTRA` (n=2 leverage-real, re-check 5º guarded o 2026-05-21).
- **A7 Blocked Signals**: `WAITING_SCHEMA` — schema v3 desplegado (commit `4da47ea`), pendiente acumular evidencia.
- **Untracked preexistente**: `2026-04-27]` (artefacto, no tocar).
- **Último commit**: consultar siempre `git log -1 --oneline`; no fijar este dato manualmente.

Mantener este bloque actualizado al final de cada sesión que cambie estado estratégico.

---

## 9. WIP limits

- Máximo **1** monetización en curso.
- Máximo **1** riesgo en curso.
- Máximo **1** tooling/observabilidad en curso.
- No abrir nueva subtarea si no **cierra** o **cambia una decisión**.

---

## 10. Cierre de tareas

Todo cierre debe incluir:

- **Clasificación** (LITE / NORMAL / FULL, tipo: docs / tooling / riesgo / etc.)
- **Archivos modificados** (lista corta)
- **Commit hash** (si hubo commit)
- **Push** sí / no
- **Deploy** sí / no
- **Env vars** tocadas sí / no
- **Railway / DB** tocados sí / no
- **BANKROLL / trading core / `bot.py` / Fase C** tocados sí / no
- **`git status`** final
- **Siguiente alarma / tarea esperada**

### Validación previa al commit

```
git diff --check
git diff --stat
git status --short
```

Si todo está limpio y la tarea estaba autorizada para commit, proceder. Push **sólo** si fue explícitamente autorizado.

---

## 11. Orquestación eficiente

### Autonomía por modo

**LITE / NORMAL (no delicados):** El agente ejecuta diagnóstico → patch → validación → smoke test → commit/push y cierra **sin pedir confirmación entre subpasos**. Si el objetivo y el scope están claros, no interrumpir para reportar pasos intermedios. Reportar al final: diff, commit hash, git status.

**FULL:** Verificación final obligatoria. Pero si el objetivo está claro y fue autorizado, no fragmentar en micro-prompts; ejecutar end-to-end y reportar al cierre.

**Cuándo parar siempre (cualquier modo):**
- Aparece algo fuera de scope.
- Riesgo de BANKROLL / trading / DB / env vars / Railway / scheduler.
- Decisión semántica que requiere Opus.
- Alarma nueva durante el bloque.

### Gestión de sesiones

- **No pedir cierre** si la sesión anterior ya cerró con commit/push, validaciones y git status final limpio.
- **Sí pedir cierre** si la sesión quedó cargada: contexto largo, trabajo sin commitar, pasos intermedios sin resolver.
- Antes de preparar un prompt, decidir y comunicar: ¿misma sesión o nueva? ¿hace falta cierre previo? ¿qué agente? ¿qué modo? ¿cuál es el criterio de parada?

### Documentación proporcional

- `CONTEXTO.md`: solo si cambia estado vivo durable (feature activa, nuevo modo, cambio de config permanente).
- Microcierres: `HISTORIAL_SESIONES.md` + `agent_events.jsonl`. No abrir `CONTEXTO.md` solo para registrar que una tarea LITE terminó.
- No documentar microdetalles de implementación si el repo ya tiene el patrón — basta con commit message claro.
- No comentar código cuando el nombre del símbolo ya lo explica.

### Respeto a la dirección elegida

- Si Pablo ya eligió Railway / scheduler / Telegram / arquitectura, **no abrir discusión de alternativas** salvo bloqueo real o riesgo no comunicado.
- Implementar la dirección elegida. Si hay un problema, reportar el problema concreto, no proponer rediseño.

### Ciclo alarma → comprensión → cierre

Cuando el usuario trae una alarma concreta o un comportamiento runtime que parece confuso, **no escalar a diseño grande ni abrir Opus por defecto**. Usar primero un ciclo corto:

1. **Entender la duda** — ¿qué comportamiento se observó? ¿cuál es la contradicción aparente?
2. **Verificar read-only** — leer código/logs/telemetría para confirmar qué hace cada ruta.
3. **Decidir** — una de cuatro salidas:
   - `KEEP`: no hay problema, documentar brevemente y cerrar.
   - `COPY/observabilidad LOG_ONLY`: falta trazabilidad; aplicar cambio mínimo sin tocar semántica.
   - `DESIGN`: falta cerrar ciclo de aprendizaje; diseñar antes de parchear.
   - `ESCALATE_OPUS`: el diagnóstico confirma que hay que cambiar semántica ejecutable (trading, riesgo, guards, SL, BANKROLL, whitelist, sizing, scheduler, Fase C).
4. **Aplicar el mínimo cambio útil** si la salida lo requiere y el scope lo permite.
5. **Validar y cerrar** — diff, commit, push si autorizado.

Escalar a Opus **solo** cuando el paso 3 lleva a `ESCALATE_OPUS`. No escalar por incertidumbre inicial.

### Anti-patrones a evitar

- Pedir confirmación entre cada subpaso en tareas LITE/NORMAL.
- Abrir sesión nueva cuando la anterior cerró limpiamente.
- Actualizar `CONTEXTO.md` para microcierres que van en `HISTORIAL_SESIONES.md`.
- Sobreexplicar implementación cuando el repo ya tiene el patrón.
- Proponer alternativas de arquitectura cuando el usuario ya eligió dirección.
- Fragmentar en micro-prompts una tarea FULL cuyo objetivo está claro y fue autorizado.
- Saltar a Opus o diseño grande cuando la alarma solo necesita verificación read-only.

---

## Apéndice — Lectura mínima por sesión nueva

1. `ORCHESTRATOR.md` (este archivo)
2. `AGENTS.md`
3. `CONTEXTO.md`
4. `OPERATIONS_PLAYBOOK.md`
5. `git status` + `git log -1`
6. Última entrada de `HISTORIAL_SESIONES.md`
7. `agent_events.jsonl`
