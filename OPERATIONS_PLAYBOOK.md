# OPERATIONS_PLAYBOOK.md

## Objetivo

Protocolo operativo comun para Pablo + Codex + Claude/Claude Code.

Este archivo no describe el estado actual del bot. Describe como trabajar sin
desalinear:

- codigo
- contexto
- historial
- scoreboard
- produccion

Si `CONTEXTO.md` es la foto viva del proyecto, este playbook es la lista de
comprobacion para no romper el proceso.

---

## Fuentes de verdad

- `AGENTS.md`: contrato corto y canonico para Codex en este repo.
- `CONTEXTO.md`: foto actual del proyecto, estado operativo, version local/remota, riesgos y siguientes pasos.
- `HISTORIAL_SESIONES.md`: memoria append-only de sesiones y decisiones.
- `agent_events.jsonl`: eventos estructurados que alimentan el scoreboard del Dashboard.
- `verify_before_deploy.py`: red de seguridad automatizada antes de push/deploy.
- `OPERATIONS_PLAYBOOK.md`: protocolo de trabajo y cierre de sesiones.

Regla: una sesion no esta realmente cerrada si solo se actualiza una de estas capas.

---

## Checklist de inicio

Antes de tocar codigo o producir analisis:

1. Leer `AGENTS.md`.
2. Leer el bloque relevante de `CONTEXTO.md`.
3. Leer las ultimas sesiones relevantes de `HISTORIAL_SESIONES.md` solo si aportan a la tarea.
4. Leer este `OPERATIONS_PLAYBOOK.md` si la tarea toca workflow, cierre, deploy, Railway o scoreboard.
5. Revisar `git status`.
6. Si el trabajo afecta al Dashboard/scoreboard, revisar tambien `agent_events.jsonl`.
7. Si el trabajo afecta a produccion, confirmar version local vs `origin/main` y estado de Railway.

---

## Disciplina de sesion y contexto minimo

Regla principal desde la sesion 58:

- `1 sesion = 1 tarea`.
- Si aparece una segunda tarea importante, se documenta como `siguiente sesion`; no se mezcla en la misma ventana de contexto.
- La sesion debe arrancar identificando una fuente primaria de verdad. Ejemplos:
  - captura de dashboard -> snapshot/json live + builder local;
  - bug de trazabilidad -> handoff + dataset afectado + helper de ensamblado;
  - problema de deploy -> playbook + auth/config + comandos de validacion.
- Antes de abrir archivos largos, decidir que `1-3` artefactos son suficientes para esa tarea concreta.
- No releer `CONTEXTO.md` completo ni sesiones antiguas si no aportan a la tarea actual; leer solo el bloque vigente y las ultimas sesiones directamente relacionadas.
- Si la tarea es de auditoria visual o semantica, primero verificar datos y evidencia; el rediseño o refactor va despues, en otra sesion si hace falta.

Objetivo: reducir ruido, evitar conversaciones demasiado anchas y dejar cierres mas limpios.

---

## Checklist de cierre

Toda sesion relevante debe cerrar estas capas, en este orden:

1. Codigo y tests:
   - implementar el cambio
   - correr `python verify_before_deploy.py`
2. Documentacion humana:
   - actualizar `CONTEXTO.md`
   - actualizar `HISTORIAL_SESIONES.md`
3. Scoreboard:
   - registrar al menos un evento en `agent_events.jsonl`
   - si hubo aportacion multiagente, registrar el valor de cada agente por separado
4. Consistencia:
   - comprobar que la sesion documentada mas reciente tambien existe en `agent_events.jsonl`
5. Deploy:
   - si hay push/deploy, dejar anotado commit y estado esperado de Railway

Regla: no cerrar una sesion con docs sin `agent_events.jsonl`, ni con `agent_events.jsonl` sin docs.

---

## Token economics

Objetivo: reservar el gasto alto de contexto/modelo para tareas con tradeoffs reales y usar defaults mas baratos/compactos en trabajo operativo.

### Codex

- Default del proyecto: `.codex/config.toml` fija `model_reasoning_effort = "medium"`.
- La config del repo tambien fija `approval_policy = "on-request"` y `sandbox_mode = "workspace-write"` para una autonomia predecible sin abrir permisos de mas.
- Perfiles disponibles:
  - `low`: trabajo mecanico, docs, limpieza, snapshots, QA ligero.
  - `deep`: bugs complejos, revisiones de arquitectura, reconciliaciones dificiles.
  - `max`: solo para casos excepcionales donde `deep` no alcance.
- No existe hoy un valor `auto` documentado para `model_reasoning_effort` en config; por eso la estrategia es `medium` por defecto + subida selectiva por perfil o override.
- Si hace falta subir esfuerzo puntualmente, usar una de estas vias:
  - `codex -c profile=\"deep\"`
  - `codex -c profile=\"max\"`
  - `codex -c model_reasoning_effort=\"high\"`
- Regla practica: no usar `xhigh` por defecto en este repo.
- Pendiente futuro: evaluar un launcher o wrapper de proyecto que clasifique la tarea y arranque Codex con `low/deep/max` automaticamente. No esta implementado; hoy solo existen `medium` por defecto y perfiles manuales.
- Rentabilidad esperada de esa automatizacion: media-alta si seguimos trabajando con muchas sesiones cortas y heterogeneas, porque evitaria pagar `high/xhigh` en tareas operativas y reduciria decisiones manuales. Si la mayoria de tareas reales siguen resolviendose bien en `medium`, el retorno seria mas de comodidad que de ahorro fuerte.
- No metemos aqui claves de roles/subagentes no verificadas en el CLI actual; la preparacion practica para profundidad selectiva queda en perfiles + skills + delegacion puntual.

### Claude Code

- Medir antes de optimizar a ciegas:
  - usar `/cost` para ver consumo de la sesion;
  - usar `/compact` cuando la conversacion ya resolvio una subparte;
  - usar `/clear` al cambiar de tarea.
- Cambiar modelo con `/model` solo cuando la tarea lo justifique; no dejar modelos caros por inercia.
- Si una tarea se vuelve amplia, dividirla en dos sesiones en vez de arrastrar contexto largo.
- Guardar en `CLAUDE.md` y `CONTEXTO.md` solo memoria estable; no convertirlos en transcript de razonamiento.

### Regla de uso

- `medium/default`: docs, UX copy, validaciones, wiring, snapshots, higiene operativa.
- `high/deep`: bugs no obvios, reconciliaciones complejas, revisiones criticas.
- modelo premium o esfuerzo maximo: solo para decisiones de trading, arquitectura o auditorias estrategicas donde el coste adicional tenga retorno claro.

### Skills minimas del repo

- `context-bootstrap`: abrir contexto minimo y elegir `1-3` artefactos fuente.
- `operational-audit`: auditorias de dashboard/logs/Railway sin tocar logica core.
- `session-close-sync`: cierre de sesion sin drift entre docs y scoreboard.

Regla: skills cortas, sin duplicar estado vivo ni inventar memoria.

---

## Capa canonica para Codex

Orden recomendado de lectura/uso en este repo:

1. `AGENTS.md`
2. bloque relevante de `CONTEXTO.md`
3. seccion necesaria de `OPERATIONS_PLAYBOOK.md`
4. solo despues: handoff, log, snapshot o archivo de codigo objetivo

Objetivo: menos gasto de contexto, menos drift y menos releer historia no util.

---

## Integracion RTK

Objetivo: reducir ruido de shell cuando Codex trabaja mucho con git, busquedas y listados.

### Que vive en el repo

- En `AGENTS.md`: preferir lecturas puntuales, `rg` y evidencia minima.
- En este playbook: reglas de uso, limites y el recordatorio de que RTK es tooling global del usuario, no dependencia versionada del proyecto.

### Comandos a preferir cuando RTK exista

- `rtk git status`
- `rtk git diff`
- `rtk git log -n 10`
- `rtk grep`
- `rtk find`
- `rtk ls`
- `rtk gain`

Regla: si un comando no esta claramente soportado por RTK, usar el comando nativo normal.

### Pasos manuales de Pablo fuera del repo

1. Instalar `rtk`.
2. Confirmar la sintaxis real con `rtk --version` y `rtk init --help`.
3. Inicializarlo para Codex desde el entorno global del usuario.
4. Reiniciar Codex.
5. Validar con `rtk gain` tras una o dos sesiones reales.

Estado verificado en esta maquina el 2 de abril de 2026: `rtk` ya esta instalado, `rtk --version` funciona, `rtk init -g --codex` funciona en la instalacion real del usuario y Codex ya lo uso en una tarea real con `rtk git status` y `rtk git diff`.

Referencia externa de apoyo: la web publica de RTK que revise documenta `rtk init --global` como comando oficial de activacion del hook.

Matiz importante: para este caso real queda verificado `rtk init -g --codex` como setup valido de Codex en la maquina del usuario. Aun asi, el repo no debe asumir que esa variante exista igual en cualquier otra instalacion.

---

## Integracion Engram

Objetivo: usar memoria persistente para continuidad de sesiones sin convertirla en fuente de verdad del repo.

### Fuente de verdad que debe quedarse en el repo

- `AGENTS.md`: contrato operativo corto.
- `CONTEXTO.md`: estado actual y siguiente paso.
- `OPERATIONS_PLAYBOOK.md`: protocolo de trabajo.
- `HISTORIAL_SESIONES.md`: memoria append-only humana.
- `agent_events.jsonl`: capa maquina del scoreboard.

### Lo que si puede ir a memoria persistente

- resumenes de sesion y punto de reentrada;
- descubrimientos no obvios del repo;
- patrones recurrentes de incidentes;
- preferencias operativas del operador que no sustituyen docs;
- pistas para retomar investigacion o auditorias futuras.

### Lo que no debe delegarse a Engram

- estado canonico del deploy;
- inventario oficial del repo;
- decisiones core no reflejadas en docs;
- configuracion operativa que deba viajar con el repositorio.

### Pasos manuales de Pablo fuera del repo

1. Instalar el binario `engram`.
2. Ejecutar `engram setup codex`.
3. Reiniciar Codex.
4. Verificar que aparecen herramientas tipo `mem_save` y `mem_search`.

Estado verificado en esta maquina el 2 de abril de 2026: Engram ya esta instalado y funcionando; `engram setup codex` funciono; y en la extension de Codex para VS Code hizo falta completar la conexion MCP manualmente por UI con `command = C:\Users\USUARIO\go\bin\engram.exe` y `args = mcp`. Tras eso, Codex ya ve herramientas `mcp__engram__...` en una sesion real.

Nota de verificacion externa: a 2 de abril de 2026, la guia publica de Engram para Codex indica que `engram setup codex` registra `[mcp_servers.engram]` y escribe instrucciones/prompt de compaction en el config global del usuario, no en este repo. En este caso real, la extension de VS Code no quedo operativa solo con ese setup y requirio el alta manual del servidor MCP por UI. Sigue siendo integracion global del usuario, no parte del arbol versionado.

---

## Checklist de deploy

Antes de `git push`:

1. `python verify_before_deploy.py`
2. `git status` limpio salvo cambios intencionales
3. `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` alineados
4. Si aplica, registrar evento nuevo con `tools/append_agent_event.py`
5. Si el cambio toca logica core (`sigma`, `Kelly`, `MIN_EDGE`, `MAX_EXPOSURE`, exits, settlement mapping, execution o accounting), pasar antes el premortem corto de este playbook

Despues de `git push`:

1. confirmar commit enviado
2. confirmar servicio Railway correcto
3. si el cambio afecta al scoreboard, recordar que el live se actualiza al reiniciar/desplegar el servicio porque `_sync_agent_events_seed()` mergea repo -> Volume al arranque

---

## Higiene Railway CLI

Regla operativa: el problema reciente de auth no fue solo Railway. Se mezclaron:

- proxies de proceso contaminados (`127.0.0.1:9`) inyectados en la shell actual
- refresh de OAuth que necesita escribir en `%USERPROFILE%\.railway\config.json`

Guardrail minimo desde ahora:

1. Para uso manual, ejecutar Railway con:
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 logs -s polymarket-bot -n 80`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "ls -l /app/data"`
2. `tools/railway_safe.ps1` limpia proxies en mayusculas/minusculas y tambien variantes `npm_config_*`, para que Railway no herede un proxy roto aunque la shell venga contaminada.
3. `railway login` se hace solo en una terminal interactiva del usuario.
4. Si `whoami` o `status` vuelven a pedir login de forma persistente, usar primero:
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless`
   El reset hace backup del `config.json`, limpia solo los tokens stale y preserva el enlace del proyecto.
5. Tras el login limpio, validar con:
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status`
   - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 logs -s polymarket-bot -n 20`
6. Si Codex necesita usar Railway despues del login, hacerlo fuera del sandbox cuando pueda tocar auth o refrescar tokens.
7. No perseguir el origen del proxy durante una incidencia si el wrapper ya desbloquea la operativa. El origen del proxy es deuda tecnica secundaria mientras no vuelva a bloquear.

Si Railway vuelve a responder `invalid_grant`:

1. ejecutar `tools/railway_auth_repair.ps1 doctor`
2. hacer `reset` para eliminar tokens incoherentes, no el enlace del proyecto
3. relanzar login limpio con `launch-login -Browserless`
4. reintentar con `tools/railway_safe.ps1`
5. no asumir que el problema es del bot ni del deploy

---

## Scoreboard

### Como se actualiza

- El Dashboard no lee `CONTEXTO.md` ni `HISTORIAL_SESIONES.md`.
- El scoreboard sale de `agent_events.jsonl`.
- En arranque, `_sync_agent_events_seed()` fusiona la semilla local del repo con el archivo persistente del Volume.
- Por eso:
  - actualizar docs no actualiza el scoreboard
  - actualizar `agent_events.jsonl` local tampoco actualiza el live hasta deploy/restart o sync manual

### Regla de eventos

Registrar eventos cuando ocurra una de estas cosas:

- `bug_detected`
- `fix_implemented`
- `review_correction`
- `feature_shipped`
- `validated_improvement`

Campos minimos:

- `timestamp`
- `session`
- `agent`
- `type`
- `stage`
- `title`
- `description`
- `points`
- `impact`
- `validated`

Si un agente corrige o valida trabajo de otro, usar `target_agent`.

### Regla de puntos

- `review_correction` solo puntua si cambia una decision, detecta un riesgo no obvio, evita un bug real o reencuadra la direccion de trabajo.
- Validacion o aprobacion sin delta no merece puntos: usar `0 puntos` o no registrar evento.
- En research multiagente, separar el credito por:
  - descubrimiento del problema;
  - revision adversarial que cambia framing o fuente;
  - sintesis ejecutable;
  - implementacion posterior.
- No duplicar credito por el mismo delta: si una revision solo confirma algo ya asentado sin mover la decision, no puntuarla aparte.

### Herramienta recomendada

Usar:

```bash
python tools/append_agent_event.py --session 37 --agent Codex --type fix_implemented --stage validated --title "..." --description "..." --points 3 --impact high
```

No editar `agent_events.jsonl` a mano salvo emergencia.

---

## Workflow Pablo + Codex + Claude

### Pablo

- revisar dashboard
- aportar contexto de negocio o capturas
- decidir recargas, tolerancia al riesgo y prioridades

### Codex

- operativa diaria
- lectura de logs / Railway / dashboard
- fixes directos
- tests
- deploys
- actualizacion de docs
- actualizacion del scoreboard

### Claude / Claude Code

- decisiones estrategicas
- cambios de forecast / sigma / Kelly / edge
- reinterpretacion del observed proxy cuando haya muestra suficiente
- revisiones de alto nivel cuando haya tradeoffs no obvios

Regla: Claude no debe ser cuello de botella para operacion, mantenimiento, observabilidad o trazabilidad.

---

## Premortem corto para cambios core

Aplicar solo cuando el cambio toque:

- `sigma`
- `Kelly`
- `MIN_EDGE`
- `MAX_EXPOSURE`
- logica principal de exits
- settlement mapping
- execution
- accounting

Responder antes de implementar o desplegar:

1. Que podria salir mal?
2. Cual seria el dano maximo?
3. Como lo detectariamos rapido?
4. Que guardrail o test lo cubre?
5. Que rollback simple existe?
6. Que supuesto critico depende de una fuente externa no validada?

Si la respuesta a la pregunta 6 es `si`, debe ocurrir al menos una de estas tres cosas:

- se anade un guardrail o test especifico;
- se documenta explicitamente el riesgo aceptado;
- se aplaza el cambio hasta tener evidencia mejor.

---

## Regla de hardening

Todo error detectado debe dejar al menos uno de estos guardrails:

- un fix
- un test
- una mejora de observabilidad
- una regla nueva en este playbook
- una automatizacion nueva

Si un error no deja guardrail, el sistema no aprendio.

---

## Protocolo de incidentes

Cuando aparezca un error:

1. describir el sintoma
2. identificar si fue bug de codigo, bug de proceso o bug de datos
3. corregir el problema inmediato
4. anotar que guardrail nuevo se añade para que no vuelva
5. reflejarlo en:
   - codigo
   - tests
   - docs
   - scoreboard si fue una aportacion relevante

---

## Definicion operativa minima

- `fallo real del sistema`: defecto evitable interno que distorsiona decisiones, datos, ejecucion o lectura del resultado.
- `limitacion conocida`: restriccion real del sistema ya identificada y tratada honestamente, pero aun no resuelta del todo.
- `ruido de mercado`: perdida o variacion sin evidencia clara de defecto interno relevante.

Ejemplos:

- `London loss por WU vs Open-Meteo` = fallo de fuente/medicion, no ruido.
- `v10.5 revertida en v10.6.0` = fallo evitable de decision/proceso.
- `trade perdido con source/mapping correcto y sin anomalias operativas` = ruido de mercado o error de forecast/estrategia, no necesariamente fallo del sistema.

---

## Nota de consistencia

`CONTEXTO.md` sigue siendo el archivo principal de estado compartido.

Este playbook existe porque, al crecer el sistema, el estado y el protocolo ya
no caben bien en el mismo documento. La regla es:

- `CONTEXTO.md` = que esta pasando
- `OPERATIONS_PLAYBOOK.md` = como trabajamos sin desalinearnos
