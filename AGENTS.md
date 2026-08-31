# AGENTS.md

Capa canonica y corta para Codex en este repo.

## Leer primero

1. `PROJECT_BOOTSTRAP.md` — descubre entrypoints y el handshake (`REMOTE_VIEW`/`LOCAL_VIEW`); no
   sustituye este contrato.
2. `AGENTS.md`
3. bloque relevante de `CONTEXTO.md`
4. `OPERATIONS_PLAYBOOK.md` solo si la tarea toca workflow, cierre, deploy, Railway o scoreboard
5. Si la tarea es un bug, un incidente o una tarea recurrente: consultar
   `docs/meta/AGENT_EXPERIENCE_LEDGER.md` **antes** de cualquier búsqueda amplia del repositorio.
6. El handshake Git que la tarea requiera. Registrar su `local_head` literal como `BASELINE_HEAD` —
   es la baseline aprobada de la sesión y no se recalcula después, ni siquiera tras commitear.

No cargar `CONTEXTO.md` completo ni sesiones antiguas sin necesidad.

## Default

- `model_reasoning_effort = "medium"` por defecto
- subir profundidad solo con perfiles `low`, `deep` o `max`
- preferir trabajo por fases y subproblemas acotados

## Codex Operating Pattern

- Para cambios importantes: primero `ASK` / read-only con mapa, plan, riesgos, archivos candidatos, validación y criterio de parada; luego `CODE` solo si el scope queda claro.
- Tratar prompts como issues/PRs: objetivo, contexto mínimo, rutas, patrón existente, guardrails, validación y entrega.
- `Best-of-N` solo para comparar planes, prompts o alternativas de diseño con coste justificado; no para multiplicar implementaciones, Railway checks ni análisis `WATCH_ONLY`.
- La cola/backlog de Codex requiere trigger, ROI esperado y criterio de cierre; evitar cementerios `WATCH`.
- Codex implementa, testea y valida; no decide semántica de trading/riesgo: BANKROLL, sizing, whitelist, city modes, scheduler, BUY/SELL/SKIP, guards/SL, source promotion y Fase C requieren Opus o confirmación humana según modo.
- `/plan` es apropiado para arquitectura LOG_ONLY o pre-implementation cuando Opus ya fijó semántica; no autoriza CODE. `/goal` solo para implementación iterativa ya autorizada, con objetivo verificable y stop condition; nunca para decisiones de trading/riesgo/BANKROLL/city modes/guards/Fase C/env vars. Para patches runtime concretos ya decididos, usar prompt normal cerrado.

## Preflights fundamentados en el repositorio (`PATTERN-16`, MR-014)

Antes de escribir, derivar el estado previo desde el repositorio en vez de recordarlo. La
recuperación es mecánica; la clasificación y el veredicto son del agente. Un resultado vacío es una
abstención, no una prueba de que no hay nada. No dependen de runtime, comando ni dependencia
concreta.

**Experiencia previa — antes de una búsqueda amplia** (bug, incidente, tarea recurrente). Buscar en
`docs/meta/AGENT_EXPERIENCE_LEDGER.md`, y solo en ese archivo, por los términos de la tarea. Si hay
camino conocido, usarlo y evitar sus callejones. Ver `PATTERN-06` en
`docs/meta/LAFABRICA_ADOPTION.md`.

**`IMPACT` — antes de editar un owner que pueda ser compartido** (`bot.py`, `trader_analyzer.py`,
`ORCHESTRATOR.md`/`AGENTS.md`, contratos de datos). Derivar del repositorio quién depende de ese
owner. El radio de validación **sigue al impacto derivado**. Si el impacto excede el `ASSIGNMENT`
autorizado → `STOP` y reportar el alcance real; no ampliar el scope en silencio.

**`BASELINE` — antes de restaurar, revertir en bloque o recuperar una versión anterior.** La
baseline aprobada es `BASELINE_HEAD` (el `local_head` congelado del handshake de apertura), nunca el
`HEAD` actual. Enumerar qué cambió en esas rutas entre el estado objetivo y `BASELINE_HEAD`. Si
aparece trabajo aprobado que la operación eliminaría → `STOP`: revertir el delta causal, no un
estado de archivo completo.

**`NORMATIVE_STATE` — antes de crear o cambiar una norma durable** (guardrail, invariante, decisión
de trading/riesgo). Recuperar la norma previa desde `ORCHESTRATOR.md`, `AGENTS.md`,
`HISTORIAL_SESIONES.md` y `CONTEXTO.md`, y clasificar: `SAME` (reutilizar) / `EXTENDS` (modificar el
propietario canónico) / `SUPERSEDES` (dejar evidencia de ciclo de vida) / `CONFLICTS` →
**`STOP_FOR_DECISION`**. No elegir en silencio ni asumir que lo más reciente gana.

Prohibido mantener a mano un registro paralelo de owners, consumidores, capacidades aprobadas o
normas: la evidencia del repositorio, la historia de Git y el corpus normativo ya son esa fuente.

---

## Diagnóstico con feedback loop (`MR-013.5`)

Para bugs no triviales, antes de construir una teoría hay que tener una señal ejecutable que se
ponga en rojo con **este** bug:

1. Establecer un comando, reproducción, test o loop ejecutable que atraviese el camino del defecto y
   afirme el síntoma real, no "no ha petado".
2. Ejecutarlo al menos una vez. Conservar la invocación, el resultado causal y el entorno.
3. Solo entonces formular hipótesis falsables — cada una con su predicción — y probar la más barata
   primero.

Leer código para construir una teoría antes de que exista esa señal es el fallo que esta regla
evita. Si no puede construirse el loop, decirlo explícitamente con lo que se intentó y pedir acceso,
artefacto capturado o instrumentación; no seguir hacia la hipótesis sin señal. No sustituye `ASK →
CODE` ni los guardrails de trading; no aplica a correcciones documentales ni cambios mecánicos.

---

## Governance de evidencia (artifact-first, lección E3)

- **Artifact-first:** ninguna estrategia, design doc, ratificación ni runner avanza si la evidencia base no está committeada en el repo o runtime-citada con ruta exacta y reproducible. Si no, `BLOCKED_NEEDS_ARTIFACT`.
- **Temp quarantine:** outputs en `%TEMP%`/chat = solo diagnóstico; nunca ratifican. Materializar summary committeado o citar ruta antes de cerrar estrategia. Producción = `/app/data`, no `data/runtime_import` local.
- **One truth lane:** un solo agente reconcilia una verdad de datos a la vez. Contradicción dato↔doc → reconciliación primero (Codex/Antigravity), no estrategia Opus.
- **Roles extendidos:** Antigravity = evidence workflow/multirepo/visual audit/source maps cuando Codex queda ambiguo; no decide trading/riesgo. Bot Brain = reporter/radar; no autoriza BUY/SELL/SKIP, BANKROLL, city modes ni salida de STANDBY.
- Detalle completo en `ORCHESTRATOR.md §16`.

## Modos de ciudad — regla canónica

Cuatro modos exclusivos y ordenados por prioridad (el primero que aplica gana):

| Modo | Cómo se activa | Tradea | Observa NOAA |
|------|---------------|:------:|:------------:|
| `blocked` | `BLOCKED_CITIES` o `auto_blocked_cities` | ❌ | ❌ |
| `shadow` | **default** (no está en ninguna lista) | ❌ | ✅ |
| `canary` | `CANARY_TRADING_CITIES` o `auto_canary_cities` | ✅ pequeño | ✅ |
| `active` | `ACTIVE_TRADING_CITIES` | ✅ | ✅ |

**Regla de oro:**
- "No quiero operar esta ciudad" → **no la pongas en `ACTIVE_TRADING_CITIES`** (queda shadow).
- "Esta ciudad tiene la fuente de datos rota" → **ponla en `BLOCKED_CITIES`**.
- Nunca usar `BLOCKED_CITIES` como sustituto de "pausa operativa". Shadow es la pausa correcta.

`OBSERVED_AUDIT_CITIES` + `noaa_station_id` en `RESOLUTION_ICAO` son requisitos adicionales
para que una ciudad shadow/active acumule datos en `observed_vs_forecast`.

## Guardrails

- No tocar trading, NOAA, scheduler, reglas de entrada/salida ni arquitectura core salvo pedido explicito.
- Primero evidencia, luego copy o refactor.
- **Autonomía A0-A3** (`ORCHESTRATOR.md §7.a`): A0 `READ_ONLY`, A1 `PATCH_PROPOSAL`, A2 `APPLY_LOCAL`, A3 `CONTROLLED_EXTERNAL_WRITE`. A0/A1 no escriben repo ni estado externo salvo autorización explícita. Al activar `STOP_LOSS`, devolver el control inmediatamente sin abrir otro cuestionario.
- **PERSIST_BEFORE_DELEGATE (`MR-009.1`):** antes de aceptar una delegación basada en un bloque previamente cerrado, comprobar que el artefacto durable citado existe y es verificable. Si solo existe un cierre declarado en chat (`CLOSED_CHAT_ONLY`, sin artefacto durable), parar con `FIX_BLOCKER_FIRST`.
- **Idempotencia:** antes de repetir una operación de escritura solicitada, comprobar si el estado objetivo ya existe. Si ya existe exactamente, no repetirla y devolver `ALREADY_APPLIED`/`ALREADY_COMMITTED` con evidencia.
- **Test de alcance a nivel de línea:** cada hunk o línea modificada debe ser necesaria para el `OUTCOME` y pertenecer al scope autorizado. Si una modificación no supera esa prueba, retirarla.
- **DOMAIN_PRODUCT_MODELING_GATE (`PATTERN-10`):** en tareas de UI/dashboard (`templates/`, `static/`) con vocabulario ambiguo de dominio, separar valor interno, label visible y valor externo/API antes de CODE. Tras 2+ microfixes de dominio seguidos, parar y replantear antes de seguir parcheando.
- Preferir `rg` y lecturas puntuales.
- Para Railway, usar `tools/railway_safe.ps1`.
- Antes de push/deploy con cambios de codigo, correr `python verify_before_deploy.py`.
- En docs-only/backlog/cierres sin codigo, usar cierre LITE: `git diff --check`, commit/push si procede y Railway check breve si hubo push; no ejecutar verify completo ni session-close-sync completo salvo necesidad real.
- `identity_available` ≠ `joined_evidence` ≠ `temporally_aligned` ≠ `outcome_resolved`. No elevar `CONFIRMED_MISSED_OPPORTUNITY` sin identidad, temporalidad, ejecutabilidad, outcome, fidelity y contrafactual verificados.
- Artefacto nuevo de inteligencia: definir consumer y outcome path desde el diseño, no como afterthought.
- Tooling LOG_ONLY en hot path: aplicar dedup/cap/sampling antes del compute caro (ver COMPUTE_CAP_BUG sesión 381).
- Tests deben medir llamadas reales al compute/hook, no solo filas escritas en el artefacto.
- En sesiones de código: consolidar docs y `agent_events.jsonl` antes del último `verify_before_deploy.py` cuando el contrato del repo lo requiera.
- La memoria externa (Engram) no sustituye la fuente de verdad del repo; toda decisión durable debe quedar en `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`.
- Si se añade entrada a `agent_events.jsonl`, usar timestamp obtenido del sistema en UTC; no inventarlo. En docs-only, no acceder a Railway para registrar eventos.
- Fuente canónica de fills R1 = API CLOB `get_trades(order_id)` cuando existe `order_id`. `trades.log` es log humano sin `order_id`: **prohibido construir parser canónico de fills sobre `trades.log`**. `performance.json`/`postmortem.json`/`trade_lifecycle.json` son contexto/cross-check, no fuente canónica de fill. Ver `docs/learning_data_contract.md` §3.
- Verificar env vars con filtrado selectivo; no listar `railway variables` completo ni pegar secretos en chat, prompts o docs.

## Cierre

Si la sesion cambia estado vivo, workflow o trazabilidad operacional, alinear:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `agent_events.jsonl`

Para docs-only o backlog sin estado vivo durable, no forzar `CONTEXTO.md`,
`HISTORIAL_SESIONES.md` ni `agent_events.jsonl`.

La memoria externa no sustituye la fuente de verdad del repo.

**Cosecha proporcional al ledger (`PATTERN-06`/`MR-014.1`):** si la tarea es repetible y hubo camino
ganador claro, callejones relevantes o mejora real de autonomía, crear o actualizar su entrada en
`docs/meta/AGENT_EXPERIENCE_LEDGER.md`, con sus `Disparadores`. Omitir en one-off y microajustes
triviales. `agent_events.jsonl` sigue siendo log, no reemplaza esta cosecha.

**`docs/meta/ACTIVE_DECISION_STATE.md` (`MR-013.1`):** si el workstream tuvo una decisión rechazada
que podría reproponerse, registrarla con motivo y `reopen_if` antes de cerrar. Si el workstream
cierra por completo, limpiar el archivo o reanclarlo al siguiente.

### SESSION_LEARNING_TRANSFER (opcional, proporcional)

Bloque de cierre para capturar aprendizajes metodológicos transferibles al ecosistema
(lafabrica-template, pablo-operating-brain). Solo cuando hay aprendizaje real no obvio.
No usar en microajustes, patches operativos rutinarios o sesiones sin aprendizaje nuevo.

**Reglas específicas de polymarket-bot:**

- `privacy_level` por defecto `INTERNAL_ONLY`; solo `PUBLIC_SAFE` si el patrón es 100% abstracto.
- No transferir: estrategia de trading, bankroll, parámetros, thresholds, señales, mercados,
  ciudades/tokens, claves, env vars, Railway, DB, snapshots, runtime, lógica de ejecución,
  código core, posiciones ni nombres de mercados operados.
- Transferible solo: patrones de gobernanza, kill switches como concepto, shadow mode como
  concepto, gates de promoción, economía de tokens, documentación de cierres, observabilidad
  accionable, STANDBY como estado explícito.
- Este bloque no autoriza reactivar el bot, cambiar city modes, env vars ni runtime.
- Cola local: `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md`.

```
SESSION_LEARNING_TRANSFER:
  project_value:    [valor para polymarket-bot — o "No aplica"]
  lafabrica:        [patrón/workflow/criterio/guardrail transferible — o "No aplica"]
  brain:
    evidence:       [evidencia profesional saneada — o "No aplica"]
    skills:         [capacidad demostrada — o "No aplica"]
    service_angle:  [servicio que podría alimentar — o "No aplica"]
    content_angle:  [narrativa o post publicable — o "No aplica"]
    portfolio_asset: [caso o activo de portfolio — o "No aplica"]
  future_product:   [insight para producto futuro — o "No aplica"]
  no_copy:          [qué NO transferir ni publicar — obligatorio si hay riesgo]
  privacy_level:    [PUBLIC_SAFE / INTERNAL_ONLY / PRIVATE_DO_NOT_EXPORT]
```
