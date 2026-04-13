# Human Reading Alignment Roadmap - 2026-04-12

## Objetivo

Alinear `Dashboard` y `Telegram` con la capa canónica actual sin tocar trading core ni mezclar este bloque con policy, monetización o throughput nuevo.

La meta no es "mejorar copy" todavía.

La meta es que la capa humana:

- lea la misma verdad que `runtime_policy_effective_view`
- respete `system_alignment_check`
- use el funnel canónico correcto
- no arrastre mensajes stale de fases anteriores
- te permita entender el sistema sin fricción
- te deje ver si vamos por buen camino hacia monetización sin vender una promesa prematura
- te ayude a aprender qué falta para el siguiente escalón

## Criterio Rector

Este módulo no se considera bien hecho si solo queda "técnicamente correcto".

También tiene que quedar:

- útil para lectura humana diaria
- claro para alguien no metido en el detalle técnico del wiring
- consistente entre superficies
- orientado a progreso, no solo a diagnóstico

La capa humana debe servir para contestar rápido:

1. `Dónde estamos ahora`
2. `Si el sistema está sano o no`
3. `Cuál es el bloqueo real`
4. `Qué falta para subir el siguiente escalón`
5. `Si seguimos avanzando hacia monetización o todavía estamos en observación/correctness`
6. `Qué cambió desde la lectura anterior`

## Principios De Diseño Del Módulo

### 1. Correctness primero

Ninguna superficie humana puede contar una historia distinta de la capa canónica.

### 2. Utilidad humana explícita

Dashboard y Telegram no son solo salidas de estado. Tienen que reducir fricción y ayudarte a decidir sin reconstruir el proyecto en la cabeza cada vez.

### 3. Progreso visible

Cada superficie debe hacer visible:

- punto actual
- siguiente objetivo
- qué falta para alcanzarlo
- si el sistema mejora, se estanca o retrocede

### 4. Horizontes claros

La lectura humana debe distinguir:

- `corto plazo`: qué corregir o verificar ahora
- `medio plazo`: qué evidencia falta para validar repetibilidad
- `largo plazo`: qué tendría que pasar para una conversación honesta de monetización

### 5. Anti-drift

Si una sesión cambia una pieza importante, el resto del circuito humano no puede quedar desactualizado sin que eso se considere un fallo de cierre.

## Fuente De Verdad Del Módulo

Usar siempre esta base, en este orden:

1. `docs/runtime_policy_effective_view_latest.md`
2. `docs/system_alignment_check_latest.md`
3. `docs/system_alignment_check_operational_latest.md`
4. `docs/metrics-funnel-naming.md`
5. `data/runtime_import/*`
6. readouts vigentes de throughput y alineación humana

## Veredicto De Entrada

Estado al cerrar la auditoría previa:

- `Dashboard`: no alineado por correctness de lectura
- `Telegram`: no alineado por staleness y framing desfasado
- siguiente paso correcto: `correctness de lectura`
- no hace falta Opus todavía salvo que aparezca conflicto de arquitectura o de fuente de verdad

## Estado Del Módulo

- `Phase 1 - Dashboard Audit`: cerrada
- `Phase 2 - Dashboard Correctness`: cerrada en sesión `147`
- `Phase 3 - Telegram Correctness`: siguiente bloque limpio
- `Phase 4 - Shared Copy Layer`: pendiente
- `Phase 5 - Final Verification`: pendiente

## Contrato De Utilidad Humana

Al terminar este módulo, tanto `Dashboard` como `Telegram` deberían contar de forma consistente estas cuatro capas:

### Estado actual

- qué está pasando hoy
- qué está sano
- qué está degradado

### Siguiente escalón

- cuál es el siguiente punto real del sistema
- qué condición concreta falta para alcanzarlo

### Horizonte

- corto plazo
- medio plazo
- largo plazo

### Alineación

- si Dashboard, Telegram, runtime y docs siguen contando la misma historia
- si el sistema avanza o si una mejora dejó desalineado el resto

## Fases LEAN

### Phase 0 - Preflight Obligatorio

Objetivo:

No trabajar sobre una base rota o desactualizada.

Comandos:

- `python tools/system_alignment_check.py`
- `python tools/system_alignment_check.py --decision-mode operational`

Regla:

- si `operational` tiene errores, parar y documentar

Definition of Done:

- ambos checks sin errores

## Phase 1 - Dashboard Audit

Objetivo:

Dejar evidencia concreta de qué parte del Dashboard ya no cuenta la misma historia que la capa canónica.

Estado:

- cerrado en sesión anterior

Salida ya existente:

- `docs/dashboard-telegram-human-layer-audit-2026-04-11.md`
- `docs/dashboard-telegram-human-layer-readout-2026-04-11.md`

## Phase 2 - Dashboard Correctness

Objetivo:

Reanclar el Dashboard a la capa canónica antes de tocar copy o UI.

Alcance:

- modos por ciudad a `effective_mode`
- throughput visible a `runtime_import/*`
- wording del funnel que hoy mezcla `markets_evaluated` con mercados escaneados
- bloques stale tipo `sin ciclo`, `0 cierres`, `activas` o similares si contradicen la foto canónica
- dejar visible para lectura humana:
  - dónde estamos
  - qué falta para el siguiente escalón
  - si vamos por buen camino
  - qué es corto/medio/largo plazo

No hacer aún:

- rediseño visual
- copy fino
- Telegram
- Opus

Definition of Done:

- el Dashboard deja de contradecir `runtime_policy_effective_view`
- el Dashboard deja de contradecir los readouts runtime manifestados
- no quedan contradicciones duras sobre modos, throughput o funnel
- el Dashboard ya te deja leer sin fricción:
  - estado actual
  - siguiente objetivo
  - bloqueo principal
  - progreso hacia el siguiente punto

Estado:

- cerrada en sesión `147`

Salida de cierre:

- `docs/dashboard-correctness-readout-2026-04-12.md`

## Phase 3 - Telegram Correctness

Objetivo:

Hacer que `city_intelligence_alert` y `city_intelligence_daily_summary` cuenten el estado canónico actual, no una fase anterior.

Alcance:

- revisar qué inputs usan realmente
- quitar framing stale como `runtime_inputs_missing` cuando ya no sea la historia operativa vigente
- alinear recomendaciones con el estado actual
- evitar que Telegram mande repetir trabajo ya cerrado
- compactar la misma narrativa útil del Dashboard en formato corto:
  - estado
  - bloqueo principal
  - siguiente objetivo
  - progreso hacia el siguiente escalón
  - alineación del sistema

Definition of Done:

- Telegram cuenta la misma historia operativa que la capa canónica
- no quedan instrucciones stale
- Telegram sirve como lectura corta útil, no solo como log de estado

## Phase 4 - Shared Copy Layer

Objetivo:

Una vez corregido el wiring, limpiar lenguaje legacy y dejar Dashboard y Telegram usando el mismo vocabulario.

Alcance:

- labels ambiguos del funnel
- marcos viejos como `Road to Real` si hoy confunden más de lo que ayudan
- wording compartido entre Dashboard y Telegram
- lenguaje de progreso comprensible para humano no técnico
- misma forma de expresar:
  - punto actual
  - siguiente punto
  - qué falta
  - si vamos por buen camino

Definition of Done:

- misma semántica en ambas superficies
- ninguna frase empuja policy/monetización fuera de tiempo
- ambas superficies ayudan a aprender el sistema, no solo a observarlo

## Phase 5 - Final Verification

Objetivo:

Cerrar el módulo con verificación factual, no solo con sensación de limpieza.

Checklist:

- `python tools/system_alignment_check.py` sin errores
- `python tools/system_alignment_check.py --decision-mode operational` sin errores
- Dashboard y Telegram cuentan la misma historia
- no quedan claims humanos que contradigan `effective_mode`
- no queda mezcla entre `raw_markets_fetched` y `candidates_after_prefilters`
- ambas superficies dejan claro:
  - dónde estamos
  - qué falta
  - qué cambió
  - si seguimos avanzando hacia el siguiente escalón

Definition of Done:

- módulo cerrado y trazado
- circuito humano útil y alineado

## Cuándo Cerrar Sesión

Cerrar y pasar a sesión limpia cuando ocurra cualquiera de estas:

1. ya se resolvió un bloque factual completo
2. aparece un conflicto nuevo que cambia el plan
3. habría que tocar arquitectura o `bot.py`
4. la sesión empieza a mezclar Dashboard, Telegram, copy y estrategia a la vez
5. ya existe un siguiente subproblema más limpio que conviene tratar aparte
6. ya quedó resuelta la parte factual pero el siguiente trabajo es otra capa del circuito humano

## Regla De Cierre Anti-Drift

Si una sesión cambia una pieza que afecta lectura humana, antes de cerrarla debe quedar explícito:

1. qué cambió en la verdad canónica
2. qué superficie humana ya quedó alineada
3. qué superficie humana sigue pendiente
4. cuál es la siguiente sesión limpia

Si no se puede cerrar ese circuito, la sesión debe declararse parcial, no cerrada del todo.

## Regla Operativa Permanente

Esto ya no depende de que el usuario lo recuerde en cada turno.

Cada sesión que cierre un bloque del módulo debe dejar por escrito:

1. qué cambió en `CONTEXTO.md`
2. qué cambió en el roadmap si cambió el estado de fases
3. cuál es el siguiente bloque recomendado
4. si conviene:
   - seguir en la misma sesión
   - abrir una sesión limpia nueva
   - usar `Sonnet`
   - o escalar a `Opus`

Regla por defecto:

- si ya se cerró un bloque factual completo, el siguiente bloque va en **sesión nueva**
- `Sonnet` se usa solo para auditoría rápida o copy compacto
- `Opus` se usa solo si aparece conflicto real de arquitectura o de fuente de verdad

## Cuándo Abrir Revisión Con Opus

Sí usar Opus si aparece alguna de estas:

1. hay dos fuentes de verdad incompatibles y no está claro cuál debe mandar
2. arreglar Dashboard o Telegram exige tocar arquitectura o contratos upstream
3. aparece una contradicción seria entre runtime, effective view y consumers humanos
4. queremos una validación estratégica final del módulo completo antes de abrir otro frente grande

No usar Opus para:

- fixes locales de wiring ya acotados
- copy/UI
- findings evidentes de lectura humana

## Reparto De Modelos

### Codex

Para:

- implementación
- verificación local
- wiring
- docs de sesión
- cierre y trazabilidad

### Sonnet

Para:

- auditorías rápidas
- contraste semántico
- revisión de copy
- preparar findings compactos antes o después de una sesión Codex

### Opus

Para:

- checkpoints estratégicos
- conflictos de arquitectura
- cierre de módulo si hay duda real de diseño

## Regla De Consumo

- `1 sesión = 1 bloque`
- `Codex` ejecuta
- `Sonnet` audita o compacta
- `Opus` solo entra en bifurcaciones importantes

No mezclar en una misma sesión:

- `Dashboard Correctness`
- `Telegram Correctness`
- `Shared Copy Layer`
- estrategia / Opus

## Patrón De Trabajo Recomendado

### Antes de Codex

Usar `Sonnet` si conviene para:

- resumir findings
- detectar wording confuso
- comparar Dashboard/Telegram/docs rápidamente

### Sesión principal

Usar `Codex` para:

- corregir wiring
- verificar outputs
- dejar readout y trazabilidad

### Después

Usar `Sonnet` para una revisión corta de claridad humana si hace falta.

### Solo si se atasca

Escalar a `Opus` si ya no estamos ante un problema de presentación sino de arquitectura o de fuentes de verdad.

## Orden Recomendado

1. `Phase 3 - Telegram Correctness`
2. `Phase 4 - Shared Copy Layer`
3. `Phase 5 - Final Verification`

## Próxima Sesión Recomendada

Abrir una sesión limpia dedicada solo a:

- `Phase 3 - Telegram Correctness`

Modelo recomendado:

- `Codex` para ejecutar `Telegram Correctness`
- `Sonnet` opcional antes o después si hace falta compactar findings o revisar claridad humana
- `Opus` no hace falta por ahora

Si durante esa sesión aparece conflicto de fuente de verdad o necesidad de tocar arquitectura, parar, documentar y recién entonces decidir si conviene una revisión de Opus.
