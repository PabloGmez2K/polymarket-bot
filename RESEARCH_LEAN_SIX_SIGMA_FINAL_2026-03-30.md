# Research Estratégico Final — Lean Six Sigma y gates de madurez del bot

**Fecha:** 2026-03-30  
**Autor:** Codex  
**Estado:** versión final consolidada tras revisión crítica iterativa con Claude.  
**Alcance:** research estratégico; sin cambios de código, tests, dashboard ni deploy.

## 1. Conclusión final

**Recomendación final:** `recomiendo no adoptar`

### Excepción única sí recomendada ahora

Integrar un **FMEA-lite / premortem corto** dentro de `OPERATIONS_PLAYBOOK.md` antes de tocar cambios core en:

- `sigma`
- `sizing / Kelly`
- `MIN_EDGE`
- `MAX_EXPOSURE`
- lógica principal de exits
- `settlement mapping`
- `execution`
- `accounting`

### Acción operativa adicional sí recomendada ahora

Añadir en el playbook una definición corta de:

- `fallo real del sistema`
- `limitación conocida`
- `ruido de mercado`

con 2-3 ejemplos concretos del historial reciente.

---

## 2. Tesis final

El bot **sí tiene estructura**:

- playbook
- verify gate
- dashboard
- postmortem
- audit
- historial

Pero **todavía no tiene suficiente control validado** como para entrar en una fase de optimización metodológica.

La pregunta correcta no es:

- "¿qué partes de Lean Six Sigma adoptamos ya?"

La pregunta correcta es:

- "¿qué tendría que demostrarse para poder afirmar que el sistema salió de discovery/stabilization y ya merece una fase de optimization?"

Mi respuesta final es:

- hoy el sistema sigue en **`Discovery activo`, con primeros signos de `Stabilization`**;
- por tanto, añadir una capa Lean Six Sigma ahora sería más proceso que valor;
- lo correcto es usar **gates de madurez** para decidir más adelante cuándo reabrir la conversación.

---

## 3. Qué diría Lean Six Sigma en este punto

### Lectura aplicada

Lean Six Sigma no pediría primero:

- más plantillas;
- más taxonomías;
- más CTQs;
- más control charts.

Pediría primero:

1. **Measurement validity**
2. **Operational definitions**
3. **Process stability**
4. **Baseline con tiempo suficiente**
5. **Resultados sostenidos antes de estandarizar más**

### Traducción al bot

Antes de optimizar la lógica core debería estar razonablemente claro:

- qué miden realmente `forecast_vs_real` legacy y `observed_vs_forecast`;
- qué cuenta como fallo evitable del sistema;
- qué cuenta como limitación conocida de fuente;
- qué cuenta como ruido de mercado;
- si la lógica core ha operado tiempo suficiente sin rollback ni nuevos defectos estructurales.

---

## 4. Diagnóstico actual del sistema

### Estado correcto

**Discovery activo, con primeros signos de Stabilization.**

### Por qué

Hechos del repo:

- el proyecto tiene muy pocos días de vida operativa;
- Dallas `KDFW -> KDAL` se corrigió el 30 de marzo;
- NOAA `observed_vs_forecast` se añadió el 30 de marzo;
- la semántica honesta de la auditoría legacy también se fijó el 30 de marzo;
- la fuente real de settlement de Polymarket sigue sin automatizarse;
- la v10.5 fue revertida por problemas de fondo, no por microajustes.

### Implicación

Esto significa que el cuello de botella actual no es:

- falta de metodología;

sino:

- `measurement fidelity`
- `muestra`
- `estabilidad temporal`
- `ausencia de nuevos defectos estructurales`

---

## 5. Respuesta final sobre Weather Underground

### Pregunta

¿Hace falta acceso directo a Weather Underground para salir de discovery/stabilization?

### Respuesta

**No como requisito duro obligatorio.**

### Sí hace falta, en cambio

1. Que la opacidad de WU deje de producir nuevas clases de defectos source/mapping.
2. Que NOAA siga tratándose honestamente como `observed proxy`, no como settlement truth.
3. Que el bot capture y use correctamente los **outcomes finales resueltos por Polymarket**.
4. Que las pérdidas recientes ya no necesiten reinterpretarse a posteriori como “seguramente era un problema de fuente”.

### Regla final

- **WU directo no es gate duro.**
- **La ausencia sostenida de nuevos defects source/mapping sí es gate duro.**
- **La muestra de outcomes finales resueltos por Polymarket sí es gate duro.**

---

## 6. Acciones inmediatas que sí tienen sentido ahora

Estas acciones no significan “adoptar Lean Six Sigma”. Son solo mejoras de disciplina compatibles con el momento real del sistema.

## A1. FMEA-lite en el playbook

Antes de cambios core, responder:

1. ¿Qué podría salir mal?
2. ¿Cuál sería el daño máximo?
3. ¿Cómo lo detectaríamos rápido?
4. ¿Qué guardrail/test lo cubre?
5. ¿Qué rollback simple existe?
6. ¿Qué supuesto crítico depende de una fuente externa no validada?

### Trigger de decisión para la pregunta 6

Si la respuesta a la pregunta 6 es `sí`, entonces debe pasar al menos una de estas tres cosas:

- se añade un guardrail/test específico;
- se documenta explícitamente el riesgo aceptado;
- se aplaza el cambio hasta tener evidencia mejor.

Sin una de esas tres consecuencias, la pregunta 6 no cuenta como cerrada.

## A2. Definición operativa `fallo real / limitación conocida / ruido`

Esta acción debe hacerse ahora porque además hace operable `G6`.

### Propuesta mínima

- `fallo real del sistema`: defecto evitable interno que distorsiona decisiones, datos, ejecución o lectura del resultado.
- `limitación conocida`: restricción real del sistema ya identificada y tratada honestamente, pero aún no resuelta del todo.
- `ruido de mercado`: pérdida o variación que ocurre sin evidencia de defecto interno relevante.

### Ejemplos del historial

- `London loss por WU vs Open-Meteo`:
  si en ese momento la fuente estaba mal alineada y el bot no lo trataba bien, cuenta como `fallo real de fuente/medición`.

- `v10.5 revertida en v10.6.0`:
  cuenta como `fallo real de decisión/proceso`, no ruido.

- `trade perdido con source/mapping correcto, settlement entendible y sin anomalías operativas`:
  cuenta como `ruido de mercado` o error de estrategia/forecast, no necesariamente fallo sistémico.

### Cómo conecta con G6

Hasta que esta definición no exista, `G6` no puede declararse pasado con rigor.

---

## 7. Gates de salida de discovery/stabilization

**Importante:** estos gates son una propuesta adaptada al proyecto. No son thresholds canónicos de ASQ.

## G1 — Medición estructuralmente estable

### Debe ser verdad

- no hay defects abiertos en ciudades activas relacionados con:
  - source/mapping;
  - estación de resolución;
  - nomenclatura engañosa;
  - confusión entre proxy observado y truth final.

### Además

- **no aparece ninguna nueva clase de defecto estructural de medición/source/mapping durante 3+ semanas consecutivas**.

### Nota

Correcciones cosméticas de docs o copy no deberían romper este gate.  
Sí lo rompe cualquier corrección que cambie:

- la interpretación de una métrica crítica;
- la lectura de una ciudad activa;
- la atribución de una pérdida o una resolución.

## G2 — NOAA deja de ser anecdótico

### Debe ser verdad

`observed_vs_forecast` ya tiene muestra y cobertura suficientes como para ser señal útil de calidad forecast, aunque no sea settlement truth.

### Criterios propuestos

- `20-30` registros observados útiles totales;
- al menos `3` ciudades activas con varios registros útiles;
- `>= 60%` de cobertura de días elegibles en cada una de esas 3 ciudades;
- ninguna ciudad activa crítica con cobertura persistentemente marginal sin explicación clara.

## G3 — Congelación temporal de lógica core

### Qué captura este gate

`G3` mide **disciplina de cambio**: que el equipo no siga moviendo los parámetros core mientras todavía intenta leer el sistema.

### Debe ser verdad

- `4+ semanas` de calendario;
- sin cambios core en:
  - `sigma`
  - `Kelly / sizing`
  - `MIN_EDGE`
  - `MAX_EXPOSURE`
  - lógica principal de exits
- sin rollback estratégico.

## G4 — Muestra mínima de outcomes finales resueltos por Polymarket

### Qué captura este gate

`G4` mide **si ya existe suficiente verdad de negocio cerrada** para revisar outcomes finales, no solo ventas o snapshots intermedios.

### Debe ser verdad

- al menos `15` outcomes finales resueltos por Polymarket como mínimo duro;
- `20` outcomes resueltos sería mejor;
- no cuentan solo `SELL`, TP o cierres anticipados;
- deben poder revisarse contra outcome final del mercado.

### Estimación temporal realista

Con:

- solo `4` ciudades activas;
- frecuencia de ciclos de `3/día`;
- selectividad actual del bot;
- y el lag natural de resolución de mercados meteorológicos,

mi estimación es:

- **escenario optimista:** `4-6 semanas` para acercarse a `15` outcomes finales útiles;
- **escenario conservador:** `6-8+ semanas`.

Conclusión:

- `G4` probablemente será un **co-cuello de botella** junto con `G3` y `G7`, no un gate trivial.

## G5 — Especificaciones internas mínimas sostenidas

### Debe ser verdad

Existe un conjunto pequeño de especificaciones internas que el sistema cumple y sostiene.

### Sub-criterios

1. mappings activos correctos y cubiertos por verify;
2. nomenclatura honesta entre dashboard, logs y audit;
3. reconciliación básica de `pending_exit` dentro de ventana esperada;
4. cero falsas alertas críticas por señales manifiestamente inválidas;
5. consistencia entre docs, scoreboard y artefactos al cerrar sesiones relevantes.

### Definición operativa de “ventana esperada” para `pending_exit`

Tomando como referencia:

- ciclos cada `8h`;
- alerta actual a partir de `12h` (`PENDING_EXIT_ALERT_HOURS=12.0`);

propongo esta definición:

- `>12h` = anomalía operativa a vigilar;
- `>24h` o `>3 ciclos` sin reconciliación = incumplimiento del sub-criterio para gates de madurez, salvo justificación explícita.

### Estado actual resumido

- `1` parcial
- `2` parcial
- `3` parcial
- `4` mejorado pero no consolidado en tiempo
- `5` mejorado pero reciente

## G6 — Resultados recientes no dominados por defectos evitables

### Qué captura este gate

`G6` mide **si las pérdidas recientes siguen viniendo sobre todo de fallos internos básicos**, o si ya pertenecen más al terreno de forecast/mercado/estrategia.

### Debe ser verdad

Evaluando una ventana de `15` outcomes finales resueltos por Polymarket:

- falla si `2` o más outcomes están **materialmente contaminados** por defectos evitables de sistema;
- falla si aparece `1` defecto evitable grave nuevo en las `10` resoluciones más recientes;
- pasa solo si las pérdidas residuales son explicables mayoritariamente por mercado/forecast/estrategia y no por fallos internos básicos.

### Qué significa “materialmente contaminado”

Cuenta como materialmente contaminado si el resultado estuvo afectado por un:

- error evitable de mapping;
- error evitable de source/interpretación;
- error evitable de semántica crítica;
- error evitable de ejecución o accounting;
- cambio de lógica core que luego se revela claramente prematuro o mal controlado.

No cuenta automáticamente como materialmente contaminado una:

- limitación conocida y ya tratada honestamente, si no distorsiona la interpretación del resultado;
- pérdida atribuible a forecast/mercado sin señal clara de defecto interno.

### Importante

La clasificación anterior depende de `A2`.  
Sin `A2`, `G6` no debería declararse pasado.

## G7 — Tiempo mínimo sin nuevas regresiones core

### Qué captura este gate

`G7` mide **robustez descubierta en el tiempo**: aunque no cambies los parámetros, ¿aparecen igualmente regresiones estructurales nuevas?

### Diferencia con G3

- `G3` = el equipo deja de mover la lógica core.
- `G7` = el sistema demuestra que, aun dejando de moverla, no siguen emergiendo fallos core nuevos.

### Debe ser verdad

- `4+ semanas` de calendario;
- sin:
  - nuevo fallo de source/mapping activo;
  - rollback estratégico tipo `v10.5 -> v10.6.0`;
  - redefinición fuerte de semántica de una métrica crítica;
  - corrección tardía de una ciudad activa por error estructural.

---

## 8. Cuándo reabrir la conversación Lean Six Sigma

### Nivel 1 — Conversación exploratoria limitada

Puede reabrirse una conversación **solo exploratoria**, sin cambiar aún la lógica core, cuando estén razonablemente bien:

- `G1`
- `G2`
- `G3`

Objetivo:

- revisar si empieza a tener sentido hablar de CTQs o de una capa ligera de control, pero todavía sin tocar parámetros estratégicos.

### Nivel 2 — Optimization real de la lógica core

Para entrar realmente en una fase de optimization, deberían pasar **todos** estos bloques:

- `G1 + G2`
- `G3 + G7`
- `G4`
- `G5 + G6`

Es decir:

- **los 7 gates son obligatorios** para abrir optimización real de la lógica core.

---

## 9. Quién revisa los gates y cuándo

### Dueños propuestos

- **Codex**:
  recopila evidencia del estado de los gates y prepara el snapshot operativo.

- **Pablo**:
  decide si quiere abrir una sesión de revisión estratégica o seguir acumulando muestra.

- **Claude**:
  revisa de forma crítica el estado de los gates antes de cualquier cambio estratégico de lógica core.

### Momento de revisión

No hace falta revisar gates en cada deploy normal.

Sí hace falta revisarlos:

- antes de proponer cambios estratégicos en `sigma`, `Kelly`, `MIN_EDGE`, `MAX_EXPOSURE` o exits;
- antes de reabrir una sesión de optimization de la lógica core;
- o cuando se crea que el sistema ya puede haber salido de discovery/stabilization.

### Integración recomendada en flujo real

La regla operativa que mejor encajaría en el playbook sería una frase simple como:

- “Antes de cualquier cambio estratégico de lógica core, revisar si los gates de madurez de discovery/stabilization están realmente validados.”

---

## 10. Qué no recomendaría todavía

- `CTQ_OPERATIVOS.md` nuevo;
- `A3_INCIDENTE.md` nuevo;
- check sheets nuevos;
- run charts formales ahora mismo;
- capability/SPC sobre outcomes de trading;
- jerarquías o rituales nuevos de metodología;
- añadir más capas documentales si antes no se consolida lo ya existente.

### Motivo

Hoy el mayor riesgo no es la falta de proceso. Es:

- formalizar demasiado pronto;
- multiplicar superficies documentales;
- confundir estructura con control validado.

---

## 11. Cierre

La conclusión final ya es estable:

- el sistema **tiene estructura**;
- pero sigue en **Discovery activo**;
- por tanto, **no conviene adoptar Lean Six Sigma ahora**;
- lo correcto es usar estos gates para saber cuándo esa conversación deja de ser prematura.

### Frase final

**`recomiendo no adoptar`**, con la única excepción de `FMEA-lite` en el playbook y la acción inmediata de definir `fallo real del sistema / limitación conocida / ruido de mercado` con ejemplos concretos del historial reciente.

---

## Fuentes locales del repo

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `OPERATIONS_PLAYBOOK.md`
- `verify_before_deploy.py`
- `OBSERVABILIDAD_Y_APRENDIZAJE.md`
- `templates/dashboard.html`
- `agent_events.jsonl`

## Fuentes externas

- ASQ, `DMAIC`: https://asq.org/quality-resources/dmaic
- ASQ, `Measurement System Analysis (MSA)`: https://asq.org/training/measurement-system-analysis--msa--msaasq
- ASQ, `Process Capability`: https://asq.org/quality-resources/process-capability
- ASQ, `Statistical Process Control`: https://asq.org/quality-resources/statistical-process-control
- ASQ, `A3 Report`: https://asq.org/quality-resources/a3-report
- Lean Enterprise Institute, `Standardized Work`: https://www.lean.org/lexicon-terms/standardized-work/
- Lean Enterprise Institute, `Standardized Work is a Goal To Work Toward, Not a Tool to Implement`: https://www.lean.org/the-lean-post/articles/standardized-work-is-a-goal-to-work-toward-not-a-tool-to-implement/
- ASQ, `FMEA / Failure mode effects analysis`: https://asq.org/learn-about-quality/process-analysis-tools/overview/fmea.html
