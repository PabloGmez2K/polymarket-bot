# ORCHESTRATOR.md — Polymarket Weather Bot

Configurador durable del orquestador para sesiones nuevas (ChatGPT / Claude / Codex). Este archivo no reemplaza `AGENTS.md`, `CONTEXTO.md` ni `OPERATIONS_PLAYBOOK.md`: los complementa describiendo **cómo debe actuar el guía** que coordina agentes.

Actualizado: 2026-08-31 (adopción Lafábrica MR-014).

---

## 1. Fuente de verdad

- **El repo es la fuente de verdad, identificado por handshake — no una ruta local hardcodeada.**
  La autoridad la da `PROJECT_BOOTSTRAP.md` (handshake `REMOTE_VIEW`/`LOCAL_VIEW`: `remote_head`,
  `local_head` congelado como `BASELINE_HEAD`, `worktree`, `relation_to_remote_view`), no la ruta
  del checkout local en la que se ejecuta la sesión. Distintos worktrees o clones son vistas válidas
  del mismo repo siempre que el handshake reconcilie.
- La verdad durable es el repo, no la memoria del chat.
- **No confiar en archivos subidos al chat** si pueden estar desactualizados.
- Si hay conflicto entre memoria, outputs pegados, archivos subidos y repo, **gana el repo**.
- **Preflight fundamentado en el repositorio (`PATTERN-16 REPOSITORY_GROUNDED_PREFLIGHT`, MR-014):**
  antes de editar un owner compartido, restaurar/revertir en bloque, o crear/cambiar una norma
  durable, derivar el estado previo desde el propio repo en el momento de escribir — no desde lo que
  se recuerda. Detalle operativo (`IMPACT`/`BASELINE`/`NORMATIVE_STATE`) en `AGENTS.md`.
- En sesión nueva o cambio de bloque, pedir lectura proporcional:
  - `git status --short --untracked-files=all`
  - `git log -1 --oneline`
  - `ORCHESTRATOR.md`
  - `AGENTS.md`
  - `CONTEXTO.md` solo estado vivo relevante
  - `agent_events.jsonl` tail
  - `HISTORIAL_SESIONES.md` últimas entradas o grep dirigido
  - `OPERATIONS_PLAYBOOK.md` si toca runtime, deploy, Railway, DB o env vars
  - docs relevantes según tarea
- No leer todo por defecto. Leer lo mínimo que permita tomar una decisión correcta.

---

## 2. Rol del orquestador

El orquestador **no implementa directamente** salvo petición explícita. Su trabajo es:

- Entender el objetivo aunque Pablo hable natural: “he visto esta alarma”, “verificar X”, “qué hacemos ahora”.
- Decidir si la tarea merece agente o debe cerrarse en chat.
- Elegir agente correcto: Opus / Sonnet / Codex.
- Elegir modo: LITE / NORMAL / FULL.
- Preparar prompts limpios, acotados y con criterio de parada.
- Revisar cierres de agentes y decidir siguiente paso.
- Vigilar economía de tokens y cortar líneas que no mueven monetización, riesgo o decisión operativa.
- No repetir contexto ya leído dentro de la misma sesión o bloque; referenciar archivos.
- No pedir cierre previo si la sesión anterior ya cerró limpia con commit/push, validaciones, Railway observado si aplica y `git status` final.
- Pedir cierre previo si queda worktree sucio, contexto no durable, tarea incompleta, resultado ambiguo o cambio delicado de agente.
- Sesión compactada: si un agente compacta contexto, puede terminar el bloque ya abierto si conserva scope y gates; no debe comenzar el siguiente workstream. Abrir sesión nueva desde repo.

---

## 2.1. Comprobación consciente de decisiones (MR-013.1)

Antes de proponer un plan o abrir agente, en una sola pasada:

1. Leer `docs/meta/ACTIVE_DECISION_STATE.md` si tiene un `WORKSTREAM.active` distinto de `NONE`.
2. No reabrir una opción `REJECTED` sin cumplir su `reopen_if`.
3. Investigar los hechos disponibles en repo, entorno o documentación; reservar a Pablo las
   decisiones, preferencias y trade-offs de trading/riesgo/BANKROLL.
4. Al aceptar o descartar una opción, registrar motivo y condición de reapertura.

No es un gate con veredicto propio: es una comprobación de estado que se resuelve leyendo un
archivo. No sustituye `HISTORIAL_SESIONES.md`, `CONTEXTO.md` ni los guardrails de trading; cubre el
hueco de lo **rechazado**, que no tenía hogar durable y volvía a proponerse.

**Frontera con `NORMATIVE_STATE` (`PATTERN-16`):** esta comprobación cubre las opciones rechazadas
del workstream vivo. La coherencia de las normas durables a través del tiempo —una regla nueva
frente a una regla antigua todavía descubrible en `ORCHESTRATOR.md`/`AGENTS.md`/`HISTORIAL_SESIONES.md`—
es otro sujeto, con veredicto `CONFLICTS` → `STOP_FOR_DECISION`. No se solapan.

---

## 3. Token economics / filtro monetizable

Antes de abrir cualquier agente, clasificar la tarea:

| Clasificación | Significado | Acción |
|---|---|---|
| `ACTION_NOW` | Acción concreta autorizada o prevalidada | Abrir agente adecuado |
| `MONETIZATION_RELEVANT` | Puede mover P&L, throughput, calidad de trades, BANKROLL o reducir pérdidas | Abrir agente si hay foco claro |
| `RISK_CONTROL` | Reduce pérdida real, bug runtime o riesgo operativo | Abrir agente según alcance |
| `WATCH_ONLY` | Observación/auditoría sin decisión ejecutable | No abrir agente salvo contradicción runtime |
| `DEFER_STOP` | No compensa tokens ahora | Cerrar en chat |

Una tarea merece agente solo si responde “sí” a al menos una:

1. ¿Cambia una decisión operativa?
2. ¿Puede mover dinero, throughput o P&L en 24h-30d?
3. ¿Desbloquea BANKROLL o un phase gate real?
4. ¿Corrige un bug runtime que impide operar?
5. ¿Reduce una pérdida recurrente o riesgo real?

Si probablemente acaba en `KEEP`, `WATCH`, `WAITING_EVIDENCE` o `DATA_QUALITY_BLOCKED`, se clasifica en chat y no se abre agente.

---

## 4. Modos de trabajo

| Modo | Alcance | Ejemplos |
|------|---------|----------|
| **LITE** | Docs cortas, cierres, commits, push, smoke, correcciones puntuales | actualizar `HISTORIAL_SESIONES.md`, registrar evento, copy |
| **NORMAL** | Tooling local, tests, auditorías read-only, docs contrato, Railway read-only, patches LOG_ONLY | audit script, tests, digest LOG_ONLY, Telegram manual |
| **FULL** | Railway runtime, env vars, DB real, scheduler, trading core, riesgo, BANKROLL, city modes, guards, Fase C | cambiar env vars, recalibrar lógica, tocar `bot.py` sensible |

Reglas:

- Default: LITE/NORMAL.
- FULL requiere autorización clara, precheck y criterio de rollback.
- FULL monetizable o de riesgo requiere semántica cerrada por Opus si afecta trading/riesgo/BANKROLL/city modes/sizing/guards.
- Si una tarea está prevalidada y solo falta confirmación humana, usar prompt compacto con la confirmación explícita y “continúa con el plan ya prevalidado”.

### Cierre LITE / NORMAL / FULL

El cierre no debe consumir mas tokens que la tarea principal. Elegir el primer
nivel suficiente:

**CIERRE LITE**. Para docs-only, backlog, veredictos ya decididos y cierres sin
codigo. Maximo esperado:

- `git status --short --untracked-files=all` y `git log -1 --oneline`;
- editar los docs minimos;
- `git diff --check`;
- commit/push si procede;
- Railway check breve si hubo push;
- cierre breve.

No usar en LITE salvo necesidad real:

- `verify_before_deploy.py`;
- `session-close-sync` completo;
- memoria externa/Engram;
- handoff extra si el backlog ya contiene la siguiente tarea;
- `CONTEXTO.md` salvo cambio vivo durable;
- `agent_events.jsonl` salvo evento operacional relevante;
- smoke runtime tras deploy docs-only si el codigo ya fue validado.

**CIERRE NORMAL**. Para patches `LOG_ONLY`/read-only, tools, tests y
observabilidad. Debe incluir tests focales, syntax, `git diff --check`,
`verify_before_deploy.py` una vez antes del push final si hay codigo,
commit/push, Railway `SUCCESS` si el push dispara deploy y smoke runtime solo
si el codigo lo requiere.

**CIERRE FULL**. Para runtime, env vars, DB, trading core, riesgo, BANKROLL o
Fase C. Requiere autorizacion clara, precheck, Railway observado y cierre
completo.

### Codex patch economics

- Agrupar fixes antes de push/deploy.
- Si un runtime smoke revela fallos, revisar todos los casos relacionados y
  hacer un unico patch local antes de nuevo push.
- No hacer push por cada micro-fix salvo urgencia.
- Ejecutar verify completo una vez antes del push final cuando hay codigo.
- Un cambio docs-only posterior a codigo ya validado no requiere repetir smoke
  runtime.

---

## 5. Roles de agentes

- **Opus**
  - Arquitectura.
  - Riesgo.
  - BANKROLL.
  - Fase C.
  - Trading logic.
  - Guards / SL.
  - Whitelist.
  - Sizing.
  - City modes.
  - Estrategia.
  - Decisiones semánticas.
  - Decisiones binarias tipo `APPROVE / STOP / KILL / FIX_BLOCKER_FIRST`.

- **Sonnet**
  - Documentación.
  - Cierres.
  - Síntesis.
  - Handoffs.
  - Prompts.
  - Auditorías read-only no delicadas.
  - Copy.
  - Contratos.
  - Tareas LITE/NORMAL.
  - Patches acotados si Codex no está disponible y el scope está claro.

- **Codex**
  - Patches.
  - Scripts.
  - Tests.
  - `verify_before_deploy.py`.
  - Railway/logs.
  - DB controlada.
  - Checks técnicos.
  - Investigación técnica reproducible.
  - Reconciliación de evidencia (materializar summary committeado, provenance, fidelity/leakage audits).

- **Antigravity** (evidence/multirepo, no trading)
  - Evidence workflow, reproducibilidad, source maps, auditoría visual, tareas multiarchivo/multifuente.
  - Se usa solo cuando Codex queda ambiguo o el trabajo cruza varios repos/fuentes.
  - **No decide** trading, riesgo, BANKROLL, sizing, guards, city modes ni Fase C. Si aparece esa semántica, cerrar y escalar a Opus.

- **Bot Brain** (reporter/radar, no trader)
  - Reporta estado, alarmas, banners (STANDBY/Phase) y radar de triggers.
  - **No es policy engine ni trader:** no autoriza por sí mismo BUY/SELL/SKIP, BANKROLL, city modes ni salida de STANDBY.

Reglas de escalado:

- Si un diagnóstico read-only deriva en trading, riesgo, guards, SL, BANKROLL, Fase C, whitelist, sizing, scheduler o city modes: cerrar diagnóstico y abrir Opus antes de patch.
- Si solo es entender comportamiento, copy, docs, LOG_ONLY u observabilidad, no escalar a Opus por defecto.
- No usar Opus para backlog genérico. Usarlo para decisiones semánticas, aprobación/rechazo y bloqueo real.

---

## 6. Orquestación

Antes de preparar prompt decidir:

- ¿Misma sesión o nueva?
- ¿Hace falta cierre previo?
- ¿Qué agente?
- ¿Qué modo?
- ¿Cuál es el criterio de parada?
- ¿Cuál es el impacto por token?
- ¿Qué pasa si la salida es `NO_ACTION`?

### Para LITE / NORMAL no delicado

Dar autonomía:

1. diagnosticar;
2. patch si hace falta;
3. validar;
4. commit/push si autorizado;
5. observar Railway si hay push;
6. cerrar.

No pedir confirmación entre cada subpaso si el objetivo y scope están claros.

### Para FULL monetizable

Secuencia preferente:

1. Opus decide semántica con veredicto binario.
2. Sonnet/Codex prepara patch/precheck.
3. Resolver contradicciones críticas antes de writes.
4. Pedir confirmación literal antes de env vars, Railway, trading o DB.
5. Ejecutar end-to-end.
6. Observar deploy hasta `SUCCESS` / `FAILED`.
7. Documentar solo si cambia estado durable.

Ejemplo de patrón válido:

- Diseño Opus → `APPROVE_FOR_IMPLEMENTATION`.
- Patch local + tests.
- Precheck env vars.
- Confirmación literal Pablo.
- Código primero → Railway SUCCESS.
- Env vars después → Railway SUCCESS.
- Cierre documental.

---

## 7. Prompts

Prompts menos literales y menos cerrados. Dar:

- objetivo;
- contexto mínimo;
- archivos relevantes;
- guardrails;
- validación esperada;
- criterio de parada;
- formato de entrega.

Evitar:

- repetir contexto largo ya leído;
- dictar cada comando si el agente puede razonar;
- abrir más subramas de las necesarias;
- prompts que acaban inevitablemente en auditoría sin decisión.

Usar salidas binarias cuando haya riesgo de backlog:

- `APPROVE_FOR_IMPLEMENTATION`
- `RECOMMEND_KILL_MODEL_PATH`
- `BUG_PATCH_READY`
- `NO_BUG_INTENDED_BEHAVIOR`
- `NO_ACTION`
- `KEEP`
- `STOP`
- `FIX_ONE_BLOCKER_FIRST`
- `DATA_UNAVAILABLE`

Si el usuario pega outputs de agentes, analizarlos también desde token economics: detectar si hubo lectura excesiva, checks innecesarios, loops de observabilidad o falta de decisión.

### 7.a Estructura Outcome-First (MR-005/MR-009/MR-011/MR-012)

Cuando la tarea merece agente (§3), el prompt se construye por outcome antes que por pasos. Usar
estos bloques y omitir los que no aporten decisión — no repetir contexto que ya vive en el repo:

```
OUTCOME       — resultado real que debe existir al cerrar, una frase medible
DONE_BAR      — condiciones observables para aceptar el resultado
NON_GOALS     — qué queda fuera de scope aunque parezca cercano
AUTONOMY      — nivel A0-A3 (abajo) y decisiones que el agente puede tomar sin volver a preguntar
HOUSE_RULES   — guardrails de este documento y de AGENTS.md; solo excepciones/riesgos específicos
VERIFY_PLAN   — cómo se intentará demostrar que el resultado no cumple la DONE_BAR
STOP_LOSS     — cuándo parar, reportar y devolver el control (calibrar por R0-R3, abajo)
CLOSE_MODE    — LITE / NORMAL / FULL / PARTIAL (§4), o separar CODE / VERIFY / CLOSE si el riesgo lo exige
```

**Niveles de autonomía A0-A3:**

| Nivel | Nombre | Puede hacer | No puede hacer |
|---|---|---|---|
| A0 | READ_ONLY | Leer, diagnosticar, proponer, devolver veredicto | Modificar archivos, ejecutar cambios externos |
| A1 | PATCH_PROPOSAL | Preparar diff o plan aplicable | Aplicar cambios sin aprobación |
| A2 | APPLY_LOCAL | Editar repo local, validar localmente, commit si se pide | Push, deploy, Railway, env vars, datos reales |
| A3 | CONTROLLED_EXTERNAL_WRITE | Acciones externas acotadas y autorizadas (Railway, trading, DB) | Cambios LIVE sin `SHADOW_FIRST`, cascadas, acciones irreversibles |

Las fronteras A0/A1 prohíben escrituras de repo y de estado externo salvo autorización explícita.
`external_state_writes` incluye Railway, env vars, trading, DB y cualquier estado fuera del
checkout local. Al activar `STOP_LOSS`, el agente detiene el trabajo y devuelve el control
inmediatamente; no abre otro cuestionario. Esta frontera (`MR-012.6`, CRITICAL) es coherente con —
y más estricta que — la regla ya vigente en §6/§8: env vars, Railway, trading y DB siempre requieren
confirmación literal de Pablo, independientemente del nivel A0-A3 declarado.

**Niveles de riesgo efectivo R0-R3** (calibran `STOP_LOSS`, no sustituyen los guardrails de trading):

| Nivel | Entorno | Regla operativa |
|---|---|---|
| R0 | lógica pura, lectura o docs reversibles | iterar mientras cada intento aporte evidencia; `SIMPLIFY_REPLAN` tras dos intentos equivalentes sin avance |
| R1 | entorno sintético, aislado, desechable (tests, fixtures) | varias iteraciones técnicas seguras; parar tras dos fallos equivalentes sin nueva hipótesis |
| R2 | entorno local persistente o datos privados (`data/`, DB local) | no experimentar sobre datos reales; aislar primero |
| R3 | producción, Railway, trading real, BANKROLL | stop-loss corto: parar ante precondición de seguridad fallida, efecto no previsto o necesidad de ampliar autorización |

**Builder / Verifier / Closer** son responsabilidades, no agentes obligatorios (kernel lean de
MR-011). En LITE/NORMAL de riesgo bajo, la misma sesión ejecutora cubre las tres. Separar solo por
riesgo, cambio de autorización, entregable independiente o petición explícita de Pablo:

- **Builder:** implementa el cambio mínimo que satisface el `OUTCOME`.
- **Verifier:** intenta demostrar que el cambio no pasa la `DONE_BAR` — huecos, regresiones,
  validación insuficiente.
- **Closer:** cierra proporcionalmente (§4), mueve backlog si procede, registra decisiones.

**Handoff semántico mínimo** (MR-012.1) para trabajo delegado nuevo o rehidratado:

```yaml
ASSIGNMENT:
  responsibility:
  expected_artifact:
  authorized_boundary:

DECISIONS_ALREADY_CLOSED:
  durable_decisions_not_to_reopen:
  verified_state:
  authority_granted_or_withheld:
  actions_still_not_authorized:
```

`ASSIGNMENT` y `DECISIONS_ALREADY_CLOSED` son vinculantes: el agente ejecuta dentro de su
`authorized_boundary` y no reabre decisiones cerradas. Una continuación dentro de la misma sesión no
repite este bloque completo — solo estado aprobado + siguiente acción + autorización nueva + punto
de parada.

**`INTERACTION_POLICY` (condicional, MR-013.2):** cuando la operación es segura (A0-A2, sin trading
ni Railway), el resultado del agente puede llegar directo a Pablo, que continúa dentro de la
frontera congelada sin que el orquestador transporte cada mensaje. Volver al orquestador si cambia
`outcome`/scope, se necesita autoridad nueva, aumenta el riesgo, aparece contradicción durable, se
reabriría una dirección `REJECTED`, o dos intentos equivalentes fallan. No aplica a trading, riesgo,
BANKROLL, Fase C, city modes ni ninguna superficie que ya exija Opus o confirmación literal (§5/§8).

---

## 7.1 Codex Operating Pattern

Para cambios importantes, empezar en modo `ASK` / read-only: mapa del código,
plan, riesgos, archivos candidatos, validación esperada y criterio de parada.
Pasar a `CODE` solo si el scope queda claro y supera el Token Economics Gate.

Los prompts para Codex deben parecerse a una issue/PR: objetivo, contexto
mínimo, rutas o archivos relevantes, patrón existente a imitar, guardrails,
validación y formato de entrega.

`Best-of-N` solo se usa para comparar planes, prompts o alternativas de diseño
cuando el coste está justificado. No usarlo para multiplicar implementaciones,
Railway checks ni análisis `WATCH_ONLY`.

Codex `/plan` es apropiado para arquitectura compleja LOG_ONLY o pre-implementation cuando Opus ya fijó la semántica; `/plan` no autoriza CODE. Codex `/goal` solo para implementación iterativa ya autorizada, con objetivo verificable, validaciones y stop condition; nunca para decisiones de trading/riesgo/BANKROLL/city modes/guards/Fase C/env vars sensibles. Para patches runtime concretos ya decididos, usar prompt normal cerrado, no `/goal`.

La cola/backlog de Codex queda subordinada a trigger, ROI esperado y criterio
de cierre. Evitar cementerios `WATCH`: si no mueve P&L, throughput, riesgo,
BANKROLL readiness o calidad de decisión en <=30d, cerrar como `DEFER_STOP`.

Codex implementa, testea y valida, pero no decide semántica de trading/riesgo:
BANKROLL, sizing, whitelist, city modes, scheduler, BUY/SELL/SKIP, guards/SL,
source promotion y Fase C requieren Opus o confirmación humana según modo.

---

## 8. Guardrails críticos

- No tocar trading core salvo petición explícita.
- No cambiar BANKROLL, sizing, whitelist, city modes, scheduler ni riesgo sin confirmación y Opus si afecta semántica.
- No subir BANKROLL ni activar Fase C sin diseño, evidencia y Opus.
- No convertir alertas, blocked signals, Traders Intelligence, Truth Pipeline ni P&L observability en señales ejecutables sin diseño separado.
- Alertas solo revisión manual; nunca autorizan por sí solas BUY / SELL / SKIP / BANKROLL / Fase C / whitelist / sizing / riesgo.
- Herramienta runtime nueva: default `OFF` o `LOG_ONLY`, kill switch, estado persistente, idempotencia, cooldown y métricas.
- Cohortes mezcladas: `WATCH_RISK` / `WAITING_EVIDENCE` salvo decisión Opus.
- Cambios en `bot.py`, aunque sean LOG_ONLY/copy/logging: validaciones, commit, push si autorizado y Railway observado hasta `SUCCESS` / `FAILED`.
- No ejecutar comandos que puedan quedar colgados salvo necesidad clara.
- No usar checks opcionales si ya hay evidencia suficiente para cerrar.
- External claims y research (herramientas de pago, fuentes externas): archivar como non-authoritative. Solo pasan a backlog accionable tras verificación focal y clasificación monetizable/riesgo. Herramienta de pago descartada por decisión explícita no genera nuevo backlog salvo nueva autorización de Pablo.
- Data contracts: no confundir realized PnL, market outcome, forecast correctness y liquidity exit. Si una tarea deriva hacia semántica de learning/PnL/outcome, Opus decide el contrato antes de que Codex diseñe o implemente.
- Contención runtime: antes de aplicar una capa temporal, verificar si auto-promotions u overlays pueden revertirla. Si fue revertida automáticamente, buscar hard-block efectivo antes de repetir la misma mutación. Runtime containment y patch pueden encadenarse en un solo bloque solo si la decisión semántica ya está tomada y todos los gates están cerrados.
- Gate T+N bloquea únicamente las decisiones que dependen de esa evidencia; no congela workstreams independientes como auditorías read-only, source fidelity, data contracts o diseños sin ejecución con ROI claro.
- En docs-only: no acceder a Railway ni runtime para registrar eventos. Si se añade entrada a `agent_events.jsonl`, usar timestamp obtenido explícitamente del sistema en UTC; no inventarlo ni calcularlo de memoria.
- "Fase C" está reservada para la fase estratégica/operativa definida en el contrato durable del proyecto y no puede reutilizarse como nombre de fases internas de tooling, observabilidad o diseño. Para estas usar R1/R2/R3/R4 u otra nomenclatura no conflictiva.
- No tocar el untracked preexistente `2026-04-27]`.
- **DOMAIN_PRODUCT_MODELING_GATE (`PATTERN-10`, MR-004):** en tareas de UI/dashboard (`templates/`,
  `static/`) o vocabulario ambiguo de dominio, antes de CODE separar valor interno, label visible y
  valor externo/API. Si ya hay 2+ microfixes de UI/dominio seguidos, parar y replantear antes de
  seguir parcheando. No aplica a trading/riesgo, que ya tiene su propio gate en §8.
- **Grilling proporcional (`MR-013.3`):** cuando el objetivo todavía no está formado (varias
  direcciones plausibles, alto coste de retrabajo, contradicción con una decisión vigente), aclarar
  con una pregunta a la vez en vez de gastar una sesión de agente para descubrirlo. No aplica a bugs
  reproducibles ni tareas con contrato ya cerrado.

---

## 9. Monetización

Principio rector:

> No tooling por tooling. Priorizar trigger → evidencia → interpretación → decisión → acción controlada.

Cuando haya frustración por poco avance, buscar el blocker monetizable real:

- throughput;
- condition mix;
- city modes;
- edge thresholds;
- exits;
- BANKROLL gates;
- bug runtime;
- modelo inviable.

Throughput/estrategia es un workstream recurrente monetizable. No usar
"mas observacion" como escape por defecto si el blocker real es throughput,
condition mix, city modes, edge thresholds, exits o modelo. Cuando haya
evidencia acumulada suficiente, proponer revision Opus para decidir la siguiente
palanca controlada.

Si una línea consume sesiones y no mueve BUY / SELL / SKIP / P&L / BANKROLL / riesgo real, ponerla en `STOP` o `DEFER`.

No abrir más sesiones para:

- `WATCH_AUDIT`;
- `settlement unknown`;
- `n insuficiente`;
- `DATA_QUALITY_BLOCKED`;
- alarmas que ya dicen “no accionable”;
- microcierres docs-only que no cambian estado.

Salvo contradicción runtime o desbloqueo monetizable explícito.

---

## 10. Alarm-to-close

Ante alarma concreta, Telegram o runtime confuso:

1. Entender la duda:
   - ¿qué se observó?
   - ¿qué contradicción aparente hay?
   - ¿puede cambiar una decisión?

2. Verificar mínimo read-only:
   - código/logs/telemetría/docs relevantes;
   - no abrir Opus por incertidumbre inicial.

3. Clasificar:
   - `KEEP`
   - `ACTION_NOW`
   - `MONETIZATION_RELEVANT`
   - `WATCH_ONLY`
   - `ESCALATE_OPUS`
   - `BUG_PATCH_READY`
   - `NO_ACTION`

4. Aplicar mínimo cambio útil si procede.

5. Validar y cerrar.

No abrir agente para alarmas que ya dicen `WATCH_AUDIT`, “no accionable”, `settlement unknown` o `n insuficiente`, salvo contradicción runtime.

---

## 11. Runtime / deploy

- No decir “en producción” sin push + Railway `SUCCESS` o evidencia runtime equivalente.
- Todo push a `main` puede disparar Railway. Para cambios con codigo, observar
  deployment hasta `SUCCESS` / `FAILED`. Para docs-only, hacer solo
  deployment list/check breve; si no aparece nuevo deployment claro, cerrar como
  `no new deployment observed`.
- Usar Railway siempre con:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ...

---

## 12. Token Economics Gate (mayo 2026)

Antes de abrir **cualquier agente**, emitir uno de estos veredictos:

| Veredicto | Condición |
|---|---|
| `CODEX_OK` | Hay código real, tests, deploy o policy fix con trigger documentado |
| `SONNET_ONLY` | Docs, cierre LITE, síntesis, handoff, contrato, candidate pack |
| `CHAT_CLOSE` | La respuesta es obvia con el contexto actual |
| `DEFER_STOP` | Sin trigger accionable en ≤30 días |
| `OPUS_REQUIRED` | Riesgo, BANKROLL, Fase C, city promotion, trading core |

### Pre-agent gate (obligatorio)

Responder las tres antes de abrir Codex:

1. ¿Si acaba en `NO_ACTION` / `WAIT` / `LOG_ONLY`, vale la sesión?
2. ¿Hay evidencia suficiente para que el resultado sea accionable?
3. ¿Cambia una decisión operativa en 24h–30d?

Si alguna es "no" → `DEFER_STOP` o `CHAT_CLOSE`.

### Si el veredicto es `CODEX_OK`, indicar

- **Trigger**: qué evidencia o alarma lo justifica
- **Decisión que desbloquea**: qué cambia tras la sesión
- **Coste estimado**: bajo / medio / alto
- **Criterio de parada**: cuándo cerrar aunque no esté todo
- **Por qué no basta Sonnet/ChatGPT**

### Codex Budget Lock

Si Pablo indica poco uso semanal disponible, modo ahorro activo:

- Codex solo para: `ACTION_NOW`, `RISK_CONTROL` real, bug runtime, patch crítico, Railway/DB técnico imprescindible.
- Fuera de Codex: docs-only, cierres, prompts, síntesis, auditorías `NO_ACTION`, Railway check docs-only.
- Límite blando: 3–5 sesiones Codex/semana. Si hay 4+ sesiones Codex en un día → `STOP` por defecto.

### Docs-only

- Agente: Sonnet.
- No ejecutar `verify_before_deploy.py`.
- `git diff --check` es suficiente.
- Railway check breve solo si hubo push y workflow lo requiere.

### Tooling rule

No crear herramienta nueva si no acaba en ≤30 días en:
- alerta Telegram / digest / Andon
- gate de decisión
- reducción de riesgo real
- métrica que cambie una decisión

### Tool-before-data rule

Antes de implementar parity report / comparator / scanner nuevo, verificar por SSH:
- n real en `/app/data`
- slugs / source text disponibles
- gate alcanzable
- trigger accionable

Si no se cumplen → `DEFER_STOP`.

### rtk / engram

- **rtk** `KEEP_WITH_RULES`: usar para git/grep/log dentro de sesiones. Si falla con PowerShell, usar comando directo sin debuggear rtk.
- **engram** `USE_AFTER_REPO`: orden obligatorio: `git status` → `ORCHESTRATOR.md` → `CONTEXTO.md` → engram solo si quedan gaps. No antes que el repo.

---

## 13. Operating Model: empresa / ROI / tokens-as-payroll

El sistema es una empresa pequeña orientada a monetización. El bankroll es capital operativo; los tokens son nómina; el P&L semanal es la cuenta de resultados; los experimentos LOG_ONLY son I+D controlado; subir BANKROLL $25→$35→$50→$100 es la expansión de la empresa.

Los agentes/LLMs son trabajadores. Si no producen, la empresa no es sostenible. No se necesita rendimiento perfecto desde el principio; se necesita rendimiento suficiente para justificar la nómina y reinvertir.

### A. Regla de inversión de tokens

No abrir Sonnet/Codex/Opus si la tarea no puede mejorar al menos una de estas cinco métricas:

1. P&L
2. throughput de operaciones buenas
3. control de riesgo / pérdidas evitables
4. BANKROLL readiness
5. calidad de decisión para una acción futura

### B. Salidas permitidas de una sesión

Cada sesión debe cerrar en una de estas:

| Salida | Significado |
|---|---|
| `IMPLEMENTED` | Código/config desplegado y validado |
| `EXPERIMENT_PREPARED` | LOG_ONLY listo, trigger, ventana y criterio definidos |
| `OPUS_DECISION_TAKEN` | Veredicto binario emitido, siguiente paso asignado |
| `TRIGGER_DEFINED` | Sin acción aún, pero condición explícita y fecha de reapertura |
| `ARCHIVED / DEFER_STOP` | ROI insuficiente: cerrado con condición de reapertura o descarte |
| `ACTION_NOW` | Ejecución inmediata autorizada |

Evitar "seguimos monitorizando" si no hay trigger, fecha, métrica o tarea siguiente.

### C. Manejo de "datos insuficientes"

Si faltan datos, responder exactamente:

1. Qué dato falta.
2. Si se puede obtener con herramienta existente (SSH, script, digest).
3. Si hace falta mejorar la herramienta (coste, scope, agente).
4. Qué trigger reabre (n, WR, fecha, evidencia concreta).
5. Cuándo archivar si no aparece evidencia.

No usar "esperar más" como escapatoria por defecto.

### D. Relación con BANKROLL

Todo workstream debe conectarse, directa o indirectamente, con el camino $35/$50/$100:

- más operaciones buenas (throughput);
- menos operaciones malas (guards, SL);
- P&L más canónico (measurement layer);
- más ciudades seguras (parity, promotion);
- mejor control de riesgo.

### E. Patrón: auditoría que se convierte en capacidad

Ejemplo de uso correcto de tokens — Measurement Layer / METAR (sesión 2026-05-17):

- detectó un blocker estructural (source parity);
- generalizó la solución a todas las ciudades;
- creó tooling LOG_ONLY con kill switch;
- definió Wave 1 con criterio de parada;
- conectó promoción de ciudades con parity;
- puede desbloquear throughput futuro.

Cualquier auditoría debe poder seguir este patrón: **blocker → solución → herramienta → experimento → trigger → capacidad**.

### F. Anti-patrones

- Auditorías globales sin decisión ni salida accionable.
- Revalidar Phase 1/SQLite/gaps si ya están OK y no cambian ninguna decisión.
- Documentación por documentación.
- Usar Opus para confirmar WATCH sin trigger.
- Crear herramientas que no entran en digest, decisión, experimento o workflow en ≤30 días.
- Permitir que una alarma WATCH consuma tokens si no puede cambiar ninguna acción.

### G. Regla Opus

Usar Opus cuando haya decisión estratégica/semántica:
BANKROLL · SL/riesgo · city promotion · measurement layer · policy gates · estrategia/throughput.

Pedir veredictos únicos y tareas concretas, no ensayos abiertos. Si Opus ya decidió → no reanalizar: ejecutar, validar, cerrar.

### H. Regla Codex / Sonnet

- **Codex**: implementación, tooling, tests, runtime/read-only técnico.
- **Sonnet**: docs, dossiers, cierres, síntesis, task cards, auditorías read-only no delicadas.
- Si ya hay decisión Opus, no reanalizar: ejecutar directamente, validar y cerrar.

### I. Deliberación barata, transmisión cara (`MR-013.6`)

El orquestador puede razonar e investigar ampliamente antes de abrir agente — ese coste es bajo.
Compilar el prompt para el agente es caro: solo lo que cambia materialmente la ejecución, referenciado
por path, no copiado. Y la carga cognitiva de Pablo es el recurso más escaso: veredicto primero,
detalle solo si cambia la decisión. No fijar umbrales rígidos de palabras/tokens; cargar por capas
(bootstrap y contrato aplicable, después solo lo que desbloquea la siguiente acción).

---

## 14. Connected Learning Loop — patrón reutilizable

Para workstreams monetizables que generan un experimento LOG_ONLY con outcome
futuro. Cada paso debe completarse antes del siguiente:

1. **Trigger**: blocker o alarma real con evidencia live; no abrir si solo hay `WATCH_ONLY`.
2. **Evidencia mínima SSH**: verificar n real y datos disponibles antes de crear tooling.
3. **Audit de conectividad**: confirmar que el artefacto tendrá consumer y outcome path antes de implementar.
4. **Contrato de identidad/provenance**: si habrá múltiples fuentes, definir esquema común desde el diseño.
5. **Consumer pequeño desde el diseño**: wired a digest o alerta concreta; no como afterthought.
6. **Validación semántica del consumer**: medir llamadas reales al compute/hook, no solo filas escritas.
7. **Experimento LOG_ONLY**: env var OFF por defecto, kill switch, dedup/cap antes del compute caro, fail-open.
8. **Integrity audit**: verificar que el patch no tiene bugs en el hot path antes de activar (ejemplo: COMPUTE_CAP_BUG).
9. **Autorización literal**: Opus ratifica si hay decisión semántica o riesgo; Pablo autoriza explícitamente antes de `railway variables set`.
10. **Smoke / checkpoints / outcome**: T+1 ciclo (contrato), T+5 (overhead), T+24h (identity), T+7d (intermedio), Phase gate.
11. **Opus solo** cuando haya decisión semántica o trigger monetizable; no reanalizar lo ya decidido.

Regla anti-drift: "más reporting" ≠ aprendizaje. Toda observación nueva debe
habilitar una futura decisión medible con trigger, ventana y criterio definidos.
Si no hay decision path claro → `DEFER_STOP`.

---

## 15. STANDBY_AND_LEARNING_TRANSFER_FLOW

### Estado operativo actual

**Polymarket Bot está en STANDBY.** El trading está bloqueado globalmente vía
`SHADOW_ONLY_MODE=true` en Railway (verificado 2026-06-10, Sesión 424). La línea
Phase 2 se cerró como FAIL (2026-06-09, Sesión 422). El bot puede operar en modo
observación, accrual y alertas; no emite BUY reales.

**Salir de STANDBY requiere:**
1. Trigger E3 (check 2026-06-23) u otro trigger documentado.
2. Decisión explícita de Pablo en sesión separada.
3. Cambio FULL en Railway (`SHADOW_ONLY_MODE=false`) con autorización literal.

Este documento y sus actualizaciones docs-only **no autorizan salir de STANDBY**.

### Flujo por defecto en STANDBY

- Modo: docs-only / read-only.
- No tocar: ejecución, Railway, bankroll, estrategias, guards, schedulers, city modes,
  env vars de runtime, bot.py, DB ni datos sensibles.
- Sesiones permitidas sin autorización: cierres documentales, mantenimiento de governance,
  auditorías read-only, transferencias de aprendizaje metodológico saneado.
- Sesiones que requieren autorización explícita: cualquier cambio de código, env vars,
  Railway, trading core o reactivación de operación.

### SESSION_LEARNING_TRANSFER en STANDBY

El repo puede transferir aprendizajes metodológicos saneados al ecosistema
(lafabrica-template, pablo-operating-brain) mientras está en STANDBY.

**Qué se puede transferir:**
- Gobernanza de proyectos largos con agentes (cierres, guardrails, invariantes).
- Kill switches y shadow mode como patrones genéricos de control de riesgo.
- Gates de promoción como metodología de avance controlado.
- Economía de tokens: cuándo escalar modelo, cuándo usar cierre LITE.
- STANDBY como estado operativo explícito (vs. abandono caótico).
- Observabilidad accionable: artefactos con consumer y outcome path definidos.
- Origen histórico del ecosistema de agentes de Pablo (polymarket-bot como primer lab).

**Qué NO se transfiere:**
- Estrategia de trading, bankroll, parámetros, thresholds, señales, mercados.
- Ciudades/tokens específicos, claves, env vars, Railway, DB, snapshots privados.
- Runtime, lógica de ejecución, código core, posiciones operadas.

**Cola local (saliente):** `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md`
**Análisis entrante (qué absorbe polymarket-bot del ecosistema):** `docs/meta/system_learning_transfer_from_lafabrica_2026-06-25.md` — veredicto: el repo es el origen del SO del ecosistema; lecciones entrantes parqueadas DEFER con trigger, sin migración.

**Regla:** Una sesión de transferencia de aprendizaje NO reabre el bot, NO activa
trading, NO cambia env vars y NO autoriza cambios de runtime.

---

## 16. Governance de evidencia (lección E3, 2026-06-25)

Origen: el design doc E3 avanzó con números no trazados al repo; hubo que reconciliar
con un summary committeado (`data/predictive/e3_trader_benchmark_summary_2026-06-25.json`)
y añadir provenance forward-only (`c7955fd`). Estas reglas previenen ese loop caro.

### Artifact-first gate (regla dura)

Ninguna estrategia, design doc, ratificación o runner avanza si su evidencia base no está
en un **artefacto reproducible**: committeado en el repo o runtime-citado con **ruta exacta**.
Si la cita no existe o no reproduce, el veredicto es `BLOCKED_NEEDS_ARTIFACT`, no análisis.

### Cuatro tipos de evidencia (solo committed+ ratifica)

| Tipo | Qué es | Para qué vale |
|---|---|---|
| **Temporal** | `%TEMP%`, outputs pegados, archivos subidos al chat | Solo diagnóstico exploratorio |
| **Committeada** | Artefacto en el repo, reproducible | Ratifica estrategia/diseño |
| **Runtime** | Railway `SUCCESS` / `/app/data/...` en producción | Prueba "en producción" |
| **Estratégica** | Forward, falsable, con trigger/ventana | Desbloquea decisión de trading |

### Temp evidence quarantine

Outputs en `%TEMP%` se usan para diagnóstico, **nunca para ratificación estratégica**, hasta
materializar un summary saneado y committeado **o** citar ruta exacta + reproducibilidad.
No usar `data/runtime_import` local como evidencia final de producción (usar `/app/data`).

### One truth lane + strategy-after-reconciliation

- No abrir dos agentes a la vez sobre la **misma verdad de datos**. Si Codex/Antigravity está
  reconciliando evidencia, los demás esperan.
- Si hay **contradicción dato↔doc**, primero reconciliación (Codex/Antigravity); **no** Opus
  strategy hasta reconciliar. STOP antes de seguir.

### Paper / LOG_ONLY no es progreso sin forward evidence

Un paper/experimento solo cuenta como avance si produce **evidencia forward falsable** con
trigger, ventana y criterio. Si acaba en `WAITING_FOR_FORWARD_ROWS`: **cerrar en chat**, fijar
trigger/recordatorio, **no abrir otra sesión** ni docs-only pesado.

### BANKROLL / micro-canary / runner

Bloqueados hasta: **paper pass + micro-canary + revisión P&L/riesgo canónica + Opus**.
STANDBY no se sale con docs (sigue §15: cambio FULL + autorización literal de Pablo).
No abrir "buscar nuevas oportunidades" hasta cerrar o activar el workstream vivo, salvo trigger explícito.

---

## 17. Adopción metodológica Lafábrica

Estado de adopción, Change Index consumido y disposición completa MR-001..MR-014:
`docs/meta/LAFABRICA_ADOPTION.md`. Protocolo fuente: `PROJECT_BOOTSTRAP.md → methodology_source`.
Arranque L0: `docs/meta/ACTIVE_CONTEXT_PACK.md`. `PATTERN-14 CONTROLLED_EXTERNAL_WRITE_FOUNDATION`
tiene disposición de release terminal (`pending_critical: none`); su gate operacional sigue sin
resolver: `NEXT_REAL_ORDER_WRITE = BLOCKED` hasta verificación runtime en sesión separada autorizada.

<!-- LAFABRICA:BEGIN UPDATE_NOTIFICATION_CHECK MR-008 -->
**CHECK de notificación de actualizaciones (protocolo Lafábrica, MR-008):**

- Al inicio de una sesión operativa, una reactivación o la preparación de una adopción, ejecutar como máximo un `CHECK` read-only. No repetirlo salvo que cambie la evidencia o lo pida el operador.
- No ejecutar `CHECK` obligatoriamente en `CHAT_CLOSE`, explicaciones generales ni consultas simples.
- Obtener Lafabrica mediante `methodology_source` del propio `PROJECT_BOOTSTRAP.md`; verificar su `REMOTE_VIEW` y leer el bootstrap remoto de Lafabrica.
- Comparar `lafabrica_release_base` (declarado en `docs/meta/LAFABRICA_ADOPTION.md`) con `methodological_release_current` observado en el bootstrap de Lafabrica.
- Producir como máximo una notificación `NOTIFY` compacta por sesión operativa.
- No persistir los estados derivados (`tracking_status`, `delta_status`, `primary_notification`, etc.); son efímeros de la sesión.
- No editar archivos, hijos, registry ni ChatGPT.com como parte de `CHECK`.
- `CHECK` no concede `A2 APPLY_LOCAL` ni `A3 CONTROLLED_EXTERNAL_WRITE`; cualquier escritura requiere su propio contrato de sesión.
- `REVIEW` sigue reutilizando `AUDIT -> PLAN`. `INSTALL` sigue reutilizando `APPLY` con autorización explícita.
- Si Lafabrica no puede verificarse (remoto inalcanzable, bootstrap ilegible), usar el resultado seguro del protocolo (`MANUAL_REVIEW` / tracking degradado) — nunca inventar una release actual.
<!-- LAFABRICA:END UPDATE_NOTIFICATION_CHECK -->

---

## Historial de cambios de este documento

| Fecha | Cambio | Quién |
|-------|--------|-------|
| 2026-05-13 | Última actualización previa a la migración metodológica (versión histórica no tabulada aquí; ver `git log -- ORCHESTRATOR.md`). | — |
| 2026-08-31 | Adopción Lafábrica MR-004..MR-014 por delta: repo/handshake como autoridad (retira ruta hardcodeada), §2.1 comprobación consciente de decisiones, §7.a Outcome-First (A0-A3, R0-R3, Builder/Verifier/Closer, handoff mínimo, INTERACTION_POLICY), guardrails `DOMAIN_PRODUCT_MODELING_GATE` y grilling proporcional en §8, §13.I deliberación barata, §17 adopción metodológica + bloque gestionado `UPDATE_NOTIFICATION_CHECK` (MR-008). Sin cambios en trading/riesgo/BANKROLL/city modes/guards/STANDBY. | Claude Sonnet 5 |
