# Plan de simplificación del Control Center

Sesión 81 — Diagnóstico de `templates/dashboard.html` + funciones `build_dashboard_*` en `bot.py`, contrastado con `docs/guia-lectura-dashboard.md`.

**Objetivo operativo de Pablo** (las 3 preguntas del chequeo de 60 s):

1. ¿El bot está sano?
2. ¿Está aprendiendo algo?
3. ¿Hay que decidir algo hoy?

**Criterio de clasificación**:

- `[OK]` — responde una de las 3 preguntas sin depender de la guía.
- `[Ambiguo]` — con guía es interpretable; sin guía es opaco. Necesita cambio mínimo.
- `[Ruido]` — técnicamente correcto pero no aporta a las 3 preguntas del chequeo diario.

Respuestas del operador que entran como insumo:

- B2 tabla shadow: **inspecciona filas**, no solo contador → la tabla se queda visible.
- B1 Cash/Posiciones: **chequea igual en shadow** → no se oculta.
- B3 Estado operativo: **eliminar bloque entero** → Intra-SL/Signals viajan a otro lado o se retiran.
- B3 Rendimiento por ciudad: **memoria histórica útil** → se mantiene aun en shadow.

---

## 1. Tabla de clasificación por bloque

| # | Bloque / Campo | Clasificación | Pregunta que responde | Comentario |
|---|---|---|---|---|
| 1 | Header: título + `generated_at` | OK | Q1 | Directo |
| 2 | Header: badge `Modo` con `badge-warn` cuando `!= REAL` | **Ambiguo** | Q1 | Amarillo en estado esperado (SHADOW/DRY) contradice la regla de colores de la guía (`warn = revisar hoy`) — induce falsa alarma |
| 3 | Header: badge `version` | OK | Q1 | |
| 4 | Aviso de autenticación desactivada | OK | Q3 | Condicional; solo aparece en alarma real |
| 5 | Road to Real: progress bar + `passed/total` + `pct` | OK | Q2 | El número agregado sí sirve como pulso semanal |
| 6 | Road to Real: checklist de 7 ítems (texto completo de cada check) | **Ambiguo** | Q2 | Varias labels opacas sin guía: `WR observado direccional ≥45%` con `n=0`, `readiness ≥60`, `sigma empírica (n≥5)`. Hoy la mayoría están en `Pendiente` y no se mueven — la señal útil está enterrada |
| 7 | Bloque 1 > `status_label` badge | OK | Q1 | Core |
| 8 | Bloque 1 > `Modo` (fila del metric-list) | **Ruido** | — | Duplica exactamente el badge del header |
| 9 | Bloque 1 > `Cash` + `Posiciones abiertas` + valor activo | OK | Q1 | Operador lo chequea aun en shadow (confirmado) |
| 10 | Bloque 1 > `Ultimo ciclo` | OK | Q1 | Core |
| 11 | Bloque 1 > `Proximo ciclo` | OK | Q1 | Core |
| 12 | Bloque 1 > `Mercados escaneados: X total, Y direccionales, Z filtrados (range/exact)` | **Ambiguo** | Q1/Q2 | "filtrados (range/exact)" es jerga; requiere glosario para leer |
| 13 | Bloque 1 > `Version` (fila del metric-list) | **Ruido** | — | Duplica el badge del header |
| 14 | Bloque 1 > `incidents` alert-stack | OK | Q3 | Condicional |
| 15 | Bloque 1 > Acción (título + detalle) | OK | Q3 | Literal: qué hacer hoy |
| 16 | Bloque 1 > PnL / WR / Cierres (gated ≥5) | OK | Q2 | Ya está gated por cierre mínimo |
| 17 | Bloque 2 > Header badge `N recientes (M históricas)` | OK | Q2 | Pulso de aprendizaje |
| 18 | Bloque 2 > Tabla 8 columnas completa | **Ambiguo** | Q2 | El operador la usa (no es ruido) pero `Condicion = at_or_above/at_or_below` requiere glosario. La tabla se queda, el campo condition necesita castellano |
| 19 | Bloque 2 > Notice footer con totales | **Ruido** | — | Repite el badge de arriba con otro formato |
| 20 | Bloque 3 > NOAA: `n=X` badge + `Muestra NOAA` + `Ultimo fetch` | OK | Q2 | Core del aprendizaje |
| 21 | Bloque 3 > NOAA: `MAE` / `Bias` / `Cobertura` cuando muestra insuficiente | **Ambiguo** | Q2 | Mostrar "acumulando" tres veces seguidas es ruido cognitivo; debería aparecer solo cuando hay muestra legible |
| 22 | Bloque 3 > NOAA: tabla `Últimos 20 casos` | OK | — | Ya es investigación, vive dentro de `<details>` colapsado |
| 23 | Bloque 3 > Rendimiento por ciudad (Trades/WR/PnL/Estado histórico) | OK | Q2 | Memoria histórica (confirmado) — se mantiene |
| 24 | Bloque 3 > Estado por ciudad (3 gates A/B/C + estado) | OK | Q2/Q3 | Core — es el R1 que acabamos de entregar |
| 25 | Bloque 3 > Glosario inline de gates (notice-muted) | OK | — | Reduce dependencia de la guía dentro del dashboard mismo |
| 26 | Bloque 3 > Ciudades bloqueadas | OK | Q3 | Condicional |
| 27 | Bloque 3 > Alertas activas | OK | Q3 | Core |
| 28 | Bloque 3 > **Estado operativo** (Version, Serie, Próximo, Último, Intra-SL, Signals) | **Ruido** | — | 4 de 6 campos duplican Bloque 1 + header. Intra-SL e Signals pueden mudarse (confirmado: eliminar el bloque entero) |

---

## 2. Detalle: qué cambio mínimo cierra cada `[Ambiguo]`

### #2 — Badge de `Modo` en header con color equivocado

- **Cambio**: en `templates/dashboard.html:18`, reemplazar `badge-warn` por `badge-accent` (o `badge-muted`) cuando `dashboard.mode != 'REAL'` en fase shadow-only. Alternativa más limpia: backend expone `dashboard.mode_badge` ya resuelto (good/accent/warn) considerando que en shadow-only el estado esperado **no** es `REAL`.
- **Efecto**: desaparece el amarillo falso que contradice la regla de colores que la propia guía enseñó en "Cómo usar esta guía".

### #6 — Road to Real: 7 checks visibles siempre

- **Cambio**: el backend (`build_dashboard_road_to_real`, `bot.py:5766`) ya tiene `passed/total/pct/checks[]`. Añadir un campo `bottleneck_check` que identifique el primer check con mayor impacto pendiente (heurística sugerida: primer check con `done=False` y `badge != muted`, con fallback al primero con `done=False`). Frontend muestra:
  - Barra de progreso + `passed/total/pct` (como hoy).
  - Línea destacada: **"Hoy el cuello de botella es: `{bottleneck_check.label}` ({bottleneck_check.display})"**.
  - El resto de los 7 checks queda dentro de `<details>` "Ver los 7 requisitos".
- **Efecto**: la pregunta "¿qué está frenando el avance?" se lee sin abrir la guía ni contar colores.

### #12 — `Mercados escaneados` con jerga `range/exact`

- **Cambio**: `templates/dashboard.html:115-121`. Reemplazar el string por:
  `"{direccionales} direccionales de {total} mercados escaneados"`
  y mover el desglose de `filtrados (range/exact)` a un `title=` (tooltip) sobre el valor, o a Bloque 3 "detalle del scan". No se oculta el dato — se oculta la jerga.
- **Efecto**: elimina dependencia del glosario para el bloque más mirado.

### #18 — Columna `Condicion` de Bloque 2 en jerga

- **Cambio**: backend (`build_dashboard_city_decisions`, `bot.py:4865`) ya tiene `condition_label` como fallback. Asegurar que `condition_label` siempre traduzca `at_or_above → "≥ umbral"` y `at_or_below → "≤ umbral"`. Frontend ya usa `row.condition_label|default(...)` en `templates/dashboard.html:207` — solo hay que garantizar que nunca caiga al default.
- **Efecto**: la tabla se lee sin ir al glosario.

### #21 — NOAA MAE/Bias/Cobertura en `acumulando` crónico

- **Cambio**: en `build_dashboard_forecast_quality` (`bot.py:4243`), cuando `sample_size < N_MIN` (sugerencia: `N_MIN=10`, igual que el umbral del road to real), los campos `mae_display`, `bias_display`, `coverage_display` no se exponen (o se exponen bajo una clave separada `forecast_quality.insufficient_sample = True`). Frontend oculta las tres filas y muestra en su lugar una sola línea:
  `"Muestra insuficiente todavía — {sample_size}/{N_MIN}. MAE/Bias se habilitan al alcanzar el umbral."`
- **Efecto**: pasa de 3 filas con "acumulando" a 1 frase con expectativa clara.

---

## 3. Detalle: qué hacer con cada `[Ruido]`

### #8 — Fila `Modo` en Bloque 1 metric-list

- **Acción**: **eliminar** `templates/dashboard.html:91-94`. El badge del header es autoritativo y ya está a 10 cm de distancia.

### #13 — Fila `Version` en Bloque 1 metric-list

- **Acción**: **eliminar** `templates/dashboard.html:123-126`. Mismo argumento: badge del header + eventual detalle en Estado operativo (que también se elimina — ver #28). La serie lógica (`v{{ logic_series }}`) sí puede quedar escondida como `title=` del badge de versión del header, para no perder el dato.

### #19 — Notice footer de Bloque 2 con totales

- **Acción**: **eliminar** `templates/dashboard.html:226-230`. El header del bloque ya dice `N recientes (M históricas)`; repetirlo tres líneas abajo es redundante.

### #28 — Bloque "Estado operativo" entero (Bloque 3)

- **Acción**: **eliminar** `templates/dashboard.html:433-450`. Destino de los dos campos no duplicados:
  - `Intra-SL`: mover a `Alertas activas` como alerta condicional (solo aparece si no coincide con el modo esperado). Si no se quiere tocar backend de alertas, mover como fila de metric-list dentro de Bloque 1 junto a `Modo`-badge-header.
  - `Signals` status: ya vive en `Alertas activas` (`dashboard.alerts.signals`). No hace falta re-exponerlo.
- **Efecto**: se eliminan 4 filas duplicadas sin perder ningún dato operativo.

---

## 4. Top 5 simplificaciones priorizadas

Criterio de priorización: impacto sobre la capacidad de leer el dashboard en 60 s sin abrir la guía, sobre costo de implementación.

| # | Cambio | Impacto | Costo | Delegación |
|---|---|---|---|---|
| 1 | **Badge de Modo con color correcto** (#2) | Alto — el primer elemento que mira el operador deja de dar falsa alarma | Mínimo (1 condicional en template, o 1 campo en backend) | **Codex** — cambio visual, test visual en smoke del dashboard |
| 2 | **"Cuello de botella de hoy" en Road to Real** (#6) | Alto — convierte un bloque denso de 7 filas en una frase accionable | Medio — requiere nueva lógica en `build_dashboard_road_to_real` + rediseño del layout de la sección | **Opus** — backend (heurística + campo nuevo) y frontend entrelazados; decisión de qué cuenta como "bottleneck" no es trivial |
| 3 | **Limpieza de duplicados**: eliminar fila `Modo` (#8), fila `Version` (#13), notice footer B2 (#19), bloque `Estado operativo` entero (#28), reubicar `Intra-SL` | Medio-alto — reduce ~30 líneas de template y elimina 4-5 duplicados que diluyen la atención | Bajo — solo borra y mueve; no hay lógica nueva salvo decidir dónde vive `Intra-SL` | **Codex** — task plana de template, con una sola decisión menor sobre `Intra-SL` |
| 4 | **NOAA: ocultar MAE/Bias/Cobertura bajo umbral** (#21) | Medio — corta 3 líneas que repiten "acumulando" y pone expectativa clara | Bajo-medio — condicional en backend (`forecast_quality.insufficient_sample`) + guardas en template | **Codex** — patrón ya usado en PnL/WR gated por `closed_count >= 5` |
| 5 | **Lenguaje llano en scan + condition labels** (#12 + #18) | Medio — elimina dos dependencias del glosario en los dos bloques más leídos | Bajo — cambio de strings, verificación de que `condition_label` siempre esté poblado | **Codex** — grep-and-replace + asegurar fallback en `build_dashboard_city_decisions` |

---

## 5. Resumen ejecutivo de delegación

- **Codex-delegable** (4 de 5): #1, #3, #4, #5. Son cambios de template + pequeñas garantías de campo en backend, todos con patrón análogo ya presente.
- **Requiere Opus** (1 de 5): #2 (cuello de botella en Road to Real). La decisión de qué heurística usar para identificar el check que frena el avance hoy es de diseño, y además entrelaza backend (`build_dashboard_road_to_real`) con un rediseño frontend de la sección.

**Recomendación de orden de ejecución**:

1. Codex arranca con el paquete #1 + #3 + #5 en una sola PR (todos son template/strings, bajo riesgo). Permite medir antes/después con el dashboard live.
2. Codex sigue con #4 (NOAA gated) en PR separada — tiene condicional backend y conviene aislarla para revisar el umbral.
3. Opus entra con #2 cuando los 4 anteriores estén verdes, porque #2 modifica la sección que más cambia de percepción visual y conviene que el resto del ruido ya esté sacado para poder juzgar su impacto real.

---

## 6. Addendum — 3 hallazgos nuevos surgidos del operador (post-revisión)

Después de escribir las secciones 1-5, el operador reportó 3 confusiones concretas leyendo el dashboard live. Codex respondió explicando el comportamiento actual y ofreció **ampliar la guía**. Rechazamos esa oferta: las 3 confusiones son síntomas del dashboard, no gaps de guía. Se integran al plan como items nuevos.

### #29 — Columna `Forecast` en Bloque 2 muestra `n/d` crónico

- **Síntoma observado**: todas las filas visibles (`Lucknow`, `New York City`, ...) traen `Forecast = n/d`.
- **Causa identificada** (según diagnóstico de Codex): `build_dashboard_city_decisions` (`bot.py:4865`) construye `recent_shadow_rows` pero muchas filas no traen poblados `forecast_display` ni `forecast_max`. El template (`templates/dashboard.html:210-218`) cae al default `n/d`.
- **Clasificación**: **Ambiguo con bug**. El operador confirmó que usa la tabla fila-a-fila (sección 1 #18), pero 2 de las columnas que necesitaría para inspeccionarla están rotas. Eso invalida parcialmente la decisión de mantener la tabla visible: hoy es un mock.
- **Fix propuesto**:
  - Paso 1 (diagnóstico): identificar en qué path del builder se pierden `forecast_display`/`forecast_max`. Probable que el fallback con `recent_edges` no llame al mismo populado que la rama `recent_opportunities`.
  - Paso 2 (fix): poblar el campo en ambas ramas. Fórmula esperada: `"{forecast_max:.1f}°C"` (o `°F` según mercado) y `forecast_display` como texto listo-para-render.
  - Paso 3 (salvaguarda): si tras el fix sigue habiendo filas con forecast ausente, marcarlas con `badge-muted` explícito en lugar de string `n/d` pelado, para que el operador sepa "dato faltante en origen" vs. "pipeline roto".
- **Delegación**: diagnóstico (paso 1) = Opus, porque la causa exacta puede estar en varios paths. Fix (paso 2) = Codex una vez identificado el path.

### #30 — Columna `Resolucion` en Bloque 2 siempre dice `pendiente`

- **Síntoma observado**: `72 históricas | 16 ciclos con shadow`, pero el operador no puede ver "cómo resolvió" ninguna señal shadow: la columna siempre cae a `pendiente`.
- **Causa identificada**: `resolution_label`/`resolution_badge` rara vez vienen poblados en las filas; el template (`templates/dashboard.html:220`) fuerza `pendiente` por default.
- **Clasificación**: **Ruido con feature incompleta**. La columna promete un dato ("¿cómo resolvió esta señal shadow?") que hoy no cumple. Para el operador es peor que no tenerla, porque genera la expectativa de que el bot ya está aprendiendo por ciclo cerrado cuando no lo está mostrando.
- **Fix propuesto** (dos alternativas):
  - **Alternativa A (ambiciosa)**: hacer el join en `build_dashboard_city_decisions` contra NOAA observed (mismo pipeline que alimenta el check "WR observado direccional ≥45%" del Road to Real). Para cada fila shadow con `(city, date)` en el pasado, buscar si existe observado y calcular `HIT` / `MISS` / `PENDING`. Esto además cerraría el loop que el operador pidió: `shadow → resolución → WR observado`.
  - **Alternativa B (conservadora)**: **eliminar la columna** hasta que la alternativa A esté lista. Mejor no tener columna que tener una que miente.
- **Recomendación**: empezar con Alternativa B (eliminar ahora, cae en el paquete Codex de limpieza de duplicados) y agendar Alternativa A como feature aparte cuando haya capacidad Opus. Razón: la A implica decidir semántica (¿qué es un `HIT` para un `at_or_below`? ¿qué margen tolera?) y no conviene colarla en este plan de simplificación.
- **Delegación**: Alternativa B = Codex (borra una columna del template + los dos campos relacionados del builder). Alternativa A = Opus, sesión futura.

### #31 — Alerta "Ciudades con accuracy baja" ruidosa en shadow-only

- **Síntoma observado**: la alerta aparece **siempre** con las mismas 4 ciudades (`London 0.0%, Miami 0.0%, New York City 8.0%, Dallas 11.8%`), todos los días. El operador ya no la puede leer como alerta.
- **Causa identificada**: la regla (`CITY_MIN_TRADES_FOR_BLOCK=3`, `CITY_BLOCK_WIN_RATE=25`) dispara sobre el **histórico congelado** de cuando el bot operaba en REAL. Como en shadow-only ese histórico no se mueve, la alerta es por construcción permanente hasta que vuelva a operar.
- **Clasificación**: **Ruido en contexto shadow** — sería señal útil si el operador pudiese reaccionar (no promover, no ampliar universo), pero en shadow-only esa reacción ya es la política global. La alerta no cambia ninguna decisión.
- **Desalineación adicional**: el texto de Acción dice "6 ciudades siguen bajo review" pero la alerta lista 4. Números incoherentes entre dos elementos del mismo dashboard.
- **Fix propuesto**:
  - En `build_dashboard_focus_center` / pipeline de alertas, cuando `mode in ('SHADOW_ONLY', 'DRY_RUN')`, **suprimir** la alerta `city_low_accuracy` del stack activo y moverla al bloque 3 "Rendimiento por ciudad" como **anotación fija** del tipo: `"Histórico congelado desde {fecha_ultimo_trade_real}. Estas ciudades no serán promovidas sin evidencia nueva: {lista}."`. Así la información no se pierde, pero deja de contar como "alerta del día".
  - Alinear el texto de Acción con el mismo número de ciudades que lista la alerta (bug de coherencia independiente: investigar de dónde sale el `6` vs. el `4`).
- **Delegación**: Codex. Cambio aislado en una condición de modo + reubicación de texto. El bug del `6 vs 4` requiere un grep adicional para localizar la fuente de cada número.

---

## 7. Priorización revisada con hallazgos nuevos

Integrando #29, #30, #31 con las 5 simplificaciones originales, el orden queda:

| Rango | Item | Por qué en este lugar |
|---|---|---|
| 1 | **#2 Badge Modo** (original top 1) | Sigue siendo el elemento más visible; arreglo trivial |
| 2 | **#30 Alt. B: eliminar columna Resolucion** | La columna miente; eliminar es mejor que tener una columna que da falsa sensación de "ya aprende" |
| 3 | **#29 Forecast n/d bug** | El operador usa la tabla fila-a-fila; sin Forecast poblado la tabla es inútil |
| 4 | **#31 Alerta city_low_accuracy suprimida en shadow** | Alta relación ruido-señal; cambio pequeño; elimina el "aparece siempre" |
| 5 | #3 Limpieza de duplicados (original top 3) | Bajo riesgo, gran limpieza visual |
| 6 | #5 Lenguaje llano scan + condition (original top 5) | Saca dependencias de glosario |
| 7 | #4 NOAA MAE/Bias gated (original top 4) | Cierra el "acumulando" crónico |
| 8 | **#2 Road to Real "cuello de botella"** (original top 2) | Opus, el más pesado; conviene último para juzgar impacto sobre fondo limpio |
| Backlog | #30 Alt. A: join NOAA observed para resolución real | Opus, sesión futura; no se mezcla en este plan |

**Reglas que siguen firmes**: sin implementación en esta sesión, sin bump de versión, no tocar 3 gates (R1) ni skip_log (R3). No ampliar la guía de lectura — cada ampliación de la guía es un parche sobre un dashboard roto.

---

## 8. Alcance explícitamente NO tocado en este plan

- No se tocan `bot.py` ni `templates/*` en esta sesión. Solo diagnóstico.
- No se propone cambiar los 3 gates de ciudad (R1 recién entregado).
- No se propone cambiar el skip_log de R3 (recién entregado en sesión 80).
- No se propone cambio de versión ni deploy.
- No se elimina ningún dato que el operador confirmó que usa (Cash/Posiciones, tabla B2 fila-a-fila, Rendimiento histórico por ciudad).
