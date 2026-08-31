# AGENT_EXPERIENCE_LEDGER — polymarket-bot

Índice de **caminos conocidos por tipo de tarea recurrente**. Antes de ejecutar una tarea de un
tipo ya registrado, se consulta su entrada; al cerrar una tarea con aprendizaje real, se crea o se
actualiza.

**Quién mantiene:** el agente al cerrar, según las reglas de cierre de `AGENTS.md`.
**Patrón de origen:** `ECOSYSTEM_LEARNING_PATTERNS.md` PATTERN-06 (catálogo de lafabrica), extendido
por `MR-014.1 RETRIEVABLE_EXPERIENCE`.

Este archivo nace vacío. Que esté vacío es un estado correcto, no deuda.

---

## Qué NO es (no duplicar)

| Documento | Qué guarda | Por qué no es el ledger |
|-----------|-----------|--------------------------|
| `agent_events.jsonl` | Log resumido, una línea por tarea | Es registro, no aprendizaje legible para reuso. |
| `HISTORIAL_SESIONES.md` | Narrativa append-only por sesión | Es histórico cronológico, no índice por tarea. |
| `CONTEXTO.md` | Estado vivo del proyecto | Es fase actual, no camino de ejecución. |
| `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md` | Candidatos a transferir a lafabrica o al Brain | Es transferencia externa, no aprendizaje interno. |

`agent_events.jsonl` **no es** este ledger — es el corrección explícita de la clasificación previa
de `PATTERN-06` en este proyecto (ver `docs/meta/LAFABRICA_ADOPTION.md §8`).

---

## Cómo se consulta

Para bug, incidente o tarea recurrente, buscar **en este archivo y solo en este archivo** por los
términos de la tarea, **antes** de cualquier búsqueda amplia del repositorio. No abrir el ledger
entero. La semántica no depende de ningún runtime, comando ni dependencia: sirve un `grep`, la
búsqueda del editor o la búsqueda nativa del agente.

Si no hay entrada, se ejecuta normal y, si procede, se cosecha al cerrar.

---

## Cuándo añadir o actualizar (proporcionalidad)

Solo si la tarea es **repetible** y se cumple al menos uno:

- Hubo un camino ganador claro que conviene fijar.
- Hubo errores o callejones relevantes que no merece la pena repetir.
- Conocer el camino mejora el acierto al primer pase o la autonomía útil.

**Omitir** en one-off, microajustes triviales y cierres sin aprendizaje nuevo.

---

## Formato de entrada

```markdown
## <TASK_TYPE_KEY>
- Aplica a: <descripción corta de la tarea recurrente>
- Disparadores: <términos concretos con los que se formula naturalmente esta tarea>
- Camino conocido (known good): <pasos mínimos que funcionan>
- Callejones sin salida (evitar): <qué falló y por qué>
- Pitfalls: <trampas no obvias>
- Cadena/agente recomendado: <herramienta/modelo por paso>
- Ref ganadora: <doc, commit o lección que funcionó>
- Historia: <Sxxx N intentos → Syyy OK> (1 línea)
- Estado: PROVISIONAL | CONFIRMED_BY_REUSE
- Actualizado: <fecha — sesión>
```

`Disparadores` es obligatorio: una entrada que no se recupera con la formulación natural de su
propia tarea no evita nada. Escribir los términos que aparecerían en el enunciado del problema.

`PROVISIONAL` = capturado una vez, aún no reusado.
`CONFIRMED_BY_REUSE` = la entrada existente **se recuperó**, su camino **se reutilizó** y la tarea
**terminó con éxito**. Capturarla, copiarla o releerla no cuenta como reuso.

---

## Guardrails de contenido

Sin secretos, credenciales, tokens, PII ni datos reales de trading (ciudades, thresholds, señales,
mercados, P&L, posiciones). Nombres genéricos de archivo o módulo sí; datos operativos no. Mismas
reglas de privacidad que `docs/meta/SESSION_LEARNING_TRANSFER_QUEUE.md`.

---

## Entradas

<!-- Sin entradas todavía. La primera se añade al cerrar una tarea repetible con aprendizaje real. -->

---

## Historial de cambios

| Fecha | Cambio | Quién |
|-------|--------|-------|
| 2026-08-31 | Creado vacío como parte de la adopción MR-014 (PATTERN-06 / MR-014.1). Reconciliación explícita: `agent_events.jsonl` no es este ledger. | Claude Sonnet 5 |
