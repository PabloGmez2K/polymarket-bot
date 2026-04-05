# Guía de lectura del Control Center

## Cómo usar esta guía

Abrí el dashboard y recorré primero el [chequeo de 60 segundos](#chequeo-de-60-segundos). Si algo no cierra, bajá al bloque correspondiente y usá la tabla para entender qué significa y qué acción tomar.

Regla rápida de colores: `good` = sano/listo, `accent` = en progreso o foco del día, `warn` = revisar hoy, `bad` = intervenir, `muted` = sin muestra o no aplica todavía.

## Chequeo de 60 segundos

1. Mirá el badge de modo arriba a la derecha. Hoy lo esperable es `DRY RUN` o `SHADOW-ONLY`, no `REAL`. Si aparece `REAL`, frená y confirmá si hubo un cambio deliberado de modo.
2. Mirá el bloque `Estado del bot`. Lo sano hoy es `Sano`, `Sano con alertas` o `Sano con limitaciones`. Si ves `Intervención requerida`, no sigas leyendo el resto como si fuera rutina: primero resolvé la incidencia.
3. Mirá la tarjeta `Acción`. Hoy lo normal en shadow-only es una acción tipo “priorizar crecimiento de muestra NOAA” o “seguir monitorizando”. Si la acción pide reparar señales, reconciliar pending exits o recargar bankroll, esa es la prioridad del día.
4. Mirá `Road to Real`. Hoy es normal que no esté completo. Lo importante es que no haya una regresión rara y que el check `Sin alertas críticas activas` siga en `OK`. Si ese check está en rojo, revisá alertas antes de cualquier otra cosa.
5. Mirá `Señales shadow direccionales`. Puede haber pocas o ninguna según el día. Lo anormal no es “0 ahora”, sino “0 todo el día” o muchos ciclos sin actividad cuando sí hubo mercados escaneados; en ese caso revisá si el scan está viendo mercados direccionales o si todo está siendo filtrado.

## Bloque por bloque

### Aviso de autenticación

- **Qué pregunta responde**
  ¿El dashboard está protegido con usuario y contraseña?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `Autenticacion desactivada` | El dashboard está expuesto sin login | No debería aparecer en producción | Configurar `DASHBOARD_USER` y `DASHBOARD_PASSWORD` en Railway |

- **Señales de alarma**
  - El aviso aparece en el dashboard live
  - Se usa el dashboard desde una URL pública sin autenticación

### Road to Real

- **Qué pregunta responde**
  ¿Qué tan lejos estamos de volver a operar con dinero real y cuál es el cuello de botella hoy?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `status_label` | Etapa general del camino a real | Hoy puede ser `Fase temprana` o `En progreso` | Si retrocede respecto de días anteriores, revisar qué check cayó |
| `passed/total` | Cuántos requisitos están cumplidos | Que no retroceda sin explicación | Mirar cuál check cambió de color |
| `>= 30 señales shadow direccionales` | Cantidad de oportunidades shadow útiles para aprender | Subir con el tiempo; no hace falta que sea alto hoy | Si queda clavado muchos días, revisar Bloque 2 y filtros |
| `>= 10 observaciones NOAA` | Muestra global observada para empezar a leer sesgo | Debe crecer con los días | Si no sube, revisar bloque NOAA y pipeline observed |
| `WR observado direccional >= 45%` | Win rate simulado de señales shadow ya resueltas con NOAA | Puede estar vacío al principio | Si hay muchas señales pero `n=0`, revisar join city+date |
| `>= 2 ciudades con sigma empírica (n>=5)` | Ciudades con suficiente muestra para calibrar incertidumbre | Normalmente bajo al principio | Si nunca avanza, revisar cierres por ciudad |
| `>= 2 ciudades con readiness >= 60` | Ciudades cerca de una promoción real | Puede estar en 0 hoy | Si baja después de haber subido, revisar ranking de ciudades |
| `Sin alertas críticas activas` | Confirmación de que no hay un problema operativo grave ahora mismo | `OK` | Si aparece en rojo, mirar `Alertas activas` antes de todo lo demás |

- **Señales de alarma**
  - El check `Sin alertas críticas activas` deja de estar en `OK`
  - `passed/total` baja de un día a otro
  - Hay señales shadow, pero el check de WR sigue mucho tiempo en `n=0`
  - NOAA no suma casos durante varios días seguidos

### Bloque 1: Estado del bot

- **Qué pregunta responde**
  ¿El bot está sano hoy, cuándo corrió por última vez y cuál es la acción operativa más importante?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `status_label` | Estado sintético del sistema | `Sano`, `Sano con alertas` o `Sano con limitaciones` | Si pasa a `Intervención requerida`, actuar antes de seguir |
| `Modo` | Si el bot está en real, dry run o shadow-only | Hoy: no `REAL` | Si muestra `REAL`, validar que fue intencional |
| `Cash` y `Posiciones abiertas` | Caja disponible y cuántas posiciones vivas hay | Caja no crítica y sin sorpresas | Si la cartera cae cerca del umbral o hay posiciones inesperadas, revisar cartera |
| `Ultimo ciclo` | Última ejecución registrada | Reciente | Si dice `Sin ciclos aún` o está muy viejo en live, revisar que el bot siga corriendo |
| `Proximo ciclo` | Próxima ejecución esperada | Una hora futura razonable | Si dice `No programado`, revisar scheduler o contexto local |
| `Mercados escaneados` | Cuántos mercados vio el bot, cuántos fueron direccionales y cuántos se filtraron por `range/exact` | Que existan direccionales cuando hay mercado | Si todo termina en filtrados, revisar si el universo del día es puro `range/exact` |
| `Version` | Versión y serie lógica del bot | Coherente con la versión desplegada | Si no coincide con lo esperado, revisar deploy |
| `Acción` | Prioridad operativa del día | Algo tipo “seguir monitorizando” o “ganar muestra NOAA” | Si pide reparar señales, pending exits o bankroll, hacer eso primero |
| `PnL serie / Win rate / Cierres` | KPIs de la serie actual | Solo son útiles con muestra | Si hay menos de 5 cierres, tratarlos como orientación débil |

- **Señales de alarma**
  - `Intervención requerida`
  - `Ultimo ciclo` muy antiguo o sin registro en el dashboard live
  - La acción del día pide reparar `signals`, `pending exits` o `bankroll`
  - El scan muestra muchos mercados totales pero casi nada direccional durante demasiado tiempo

### Bloque 2: Señales shadow direccionales

- **Qué pregunta responde**
  ¿El bot está encontrando oportunidades shadow útiles para aprender aunque todavía no compre en real?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `recientes` | Cantidad de filas visibles en la tabla | Puede ser baja o 0 según el día | Si pasa días entero en 0, revisar scan y filtros |
| `historicas` | Total acumulado de edges shadow válidos | Debe crecer con el tiempo | Si no crece nunca, revisar si el bot solo está filtrando |
| `Ciudad` | Ciudad de la señal | La ciudad debe tener sentido con el universo seguido | Si aparece una ciudad rara, revisar policy/allowlist |
| `Fecha` | Fecha del mercado | Debe ser una fecha futura válida cuando se generó la señal | Si ves fechas incoherentes, revisar parsing |
| `Condicion` | Tipo de condición direccional (`at_or_above` / `at_or_below`) | Una de esas dos | Si aparecen otras, revisar porque esta tabla debería ser direccional |
| `Side` | Lado que habría tomado el bot (`YES` o `NO`) | Uno de esos dos | Si falta, revisar la fila origen |
| `Edge%` | Ventaja estimada del bot frente al mercado | Positivo; cuanto más alto, más fuerte la señal | Si todas las filas están muy al límite, tomarlo como construcción, no como lista |
| `Forecast` | Temperatura prevista o umbral que explica la lectura | Debe ser legible | Si sale `n/d` muchas veces, revisar datos de forecast |
| `Mercado` | Pregunta exacta del mercado | Debe corresponder con la ciudad/fecha | Si no coincide, revisar parsing o fuente |
| `Resolucion` | Si la señal ya tiene resolución observada | `pendiente` es normal al principio | Si nunca resuelve, revisar NOAA observed |

- **Señales de alarma**
  - Muchos ciclos sin ninguna señal direccional y sin explicación visible
  - Filas con `Condicion` distinta de direccional
  - La tabla queda vacía mientras `Mercados escaneados` sigue alto todos los días
  - Se acumulan señales, pero nunca aparecen resoluciones observadas

### Bloque 3: Salud del sistema

- **Qué pregunta responde**
  ¿Quiero bajar a detalle para entender observabilidad, ciudades, alertas y estado técnico?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `Salud del sistema` | Contenedor del detalle operativo | Cerrado por defecto; se abre para investigar | Si el chequeo de 60 segundos dio bien, no hace falta abrir todo |
| `Forecast accuracy, sigma, ciudades, alertas` | Resume qué temas viven dentro | Coherente con lo que querés investigar | Si un problema no encaja en ningún bloque, documentarlo aparte |

- **Señales de alarma**
  - Necesitás abrir este bloque todos los días para entender si el bot está vivo: eso indica que la capa superior todavía no alcanza
  - Encontrás un dato crítico solo acá y no en el Bloque 1

### Salud del sistema: Calidad NOAA observada

- **Qué pregunta responde**
  ¿Estamos midiendo el forecast contra observado de una forma suficiente para aprender algo útil?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `n=...` | Tamaño de muestra NOAA | Debe crecer con el tiempo | Si queda en 0 o no sube, revisar pipeline NOAA |
| `Muestra NOAA` | Cantidad de mercados con observado cargado | Hoy puede estar por debajo del objetivo | Si no crece en varios días, revisar fetch y auditoría |
| `MAE NOAA` | Error medio absoluto del forecast | Solo es legible con muestra mínima | Si sigue en “acumulando” es falta de muestra, no un bug |
| `Bias NOAA` | Sesgo promedio del forecast | Igual que MAE: requiere muestra | Si aparece muy corrido cuando ya hay muestra, revisar ciudad por ciudad |
| `Cobertura` | Cuántas ciudades tienen muestra NOAA | Debe avanzar hacia el universo activo | Si las activas no tienen cobertura, la prioridad del día sigue siendo observabilidad |
| `Ultimo fetch NOAA` | Último caso observado cargado | Reciente para el ritmo normal del bot | Si queda viejo, revisar fetch o fuente NOAA |
| `Ultimos 20 casos` | Muestra concreta de forecast vs observado | Útil para diagnóstico, no para la lectura rápida | Si ves muchos errores rojos seguidos, abrir investigación |

- **Señales de alarma**
  - `n=0` durante días en producción
  - `Ultimo fetch NOAA` viejo
  - Muchas filas recientes con error rojo
  - Las ciudades activas siguen sin llegar a muestra interpretable

### Salud del sistema: Rendimiento por ciudad

- **Qué pregunta responde**
  ¿Qué ciudades son operables, cuáles vienen mal y cuáles solo están acumulando evidencia?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `Trades / WR / PnL` | Histórico real por ciudad | Útil solo cuando hay muestra | Si una ciudad activa cae a histórico malo, revisar salida o bloqueo |
| `Estado` en tabla superior | Riesgo agregado de esa ciudad | Verde o amarillo en ciudades sanas | Si se pone crítico, revisar esa ciudad antes de ampliar universo |
| `Historial` | Gate A: salud del histórico real | `Limpio`, `Malo` o `Sin datos` | Si está `Malo`, no promover esa ciudad |
| `Shadow` | Gate B: evidencia shadow | `Vacío`, `Construyendo` o `Lista` | Si está `Lista`, revisar candidata a canary |
| `NOAA` | Gate C: evidencia observada | `Sin NOAA`, `Parcial` o `Interpretable` | Si está `Sin NOAA`, todavía falta observabilidad |
| `Estado` en ranking | Modo real de esa ciudad (`Activa`, `Shadow`, `Bloqueada`, etc.) | Coherente con la policy actual | Si una activa aparece bloqueada o degradada, revisar transición |
| `Bloqueadas` | Ciudades explícitamente fuera de juego | Puede haber algunas | Si aparece una ciudad importante sin que lo esperes, revisar motivo de bloqueo |

- **Señales de alarma**
  - Una ciudad con `Historial = Malo`
  - Una ciudad que parecía avanzar y ahora aparece `Bloqueada` o degradada
  - Varias ciudades activas sin `NOAA` interpretable
  - El ranking muestra muchas filas de `Sin datos` y nada de progreso en shadow o NOAA

### Salud del sistema: Alertas activas

- **Qué pregunta responde**
  ¿Hay un problema operativo que justifique intervención hoy?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `Señales de traders` | Estado de `signals.json` | `ok`, o como mucho `stale` sin impacto grave | Si está `missing` o `error`, reparar antes del próximo ciclo |
| `Pending exits atascadas` | Órdenes de salida pendientes por más de 12h | 0 | Si aparece, auditar y reconciliar manualmente |
| `Ciudades con accuracy baja` | Ciudades con muestra suficiente y WR demasiado bajo | Pocas o ninguna | Si aparece una activa, no ampliar riesgo ahí |
| `Bankroll bajo` | Cartera por debajo del umbral operativo | No debería aparecer | Si aparece, recargar antes de esperar aprendizaje útil |

- **Señales de alarma**
  - Cualquier alerta roja
  - `signals.json missing` o `error`
  - Pending exits atascadas
  - Bankroll bajo

### Salud del sistema: Estado operativo

- **Qué pregunta responde**
  ¿Los datos técnicos básicos del dashboard siguen coherentes con la operación?

- **Qué significa cada campo visible**

| Campo | Significado en castellano claro | Valor esperado | Qué hacer si se desvía |
|---|---|---|---|
| `Version` | Versión desplegada | La versión que esperabas ver | Si no coincide, revisar deploy |
| `Serie logica` | Serie de reglas con la que se están leyendo los datos | La serie vigente | Si cambia sin contexto, revisar release |
| `Proximo ciclo` | Próxima corrida | Futuro razonable | Si no existe, revisar scheduler |
| `Ultimo ciclo` | Última corrida | Reciente | Si está viejo, revisar bot caído |
| `Intra-SL` | Estado del monitor intra-ciclo | Coherente con la configuración actual | Si cambia inesperadamente, revisar config |
| `Signals` | Estado resumido de `signals.json` | Preferible `ok` | Si está `stale`, `missing` o `error`, cruzarlo con alertas |

- **Señales de alarma**
  - `Ultimo ciclo` viejo
  - `Signals` en `missing` o `error`
  - Versión distinta de la que creías desplegada

## Glosario

### `edge`
Ventaja estimada del bot frente al precio del mercado. Si el bot cree que una respuesta vale bastante más que lo que paga el mercado, hay `edge`.

No significa “trade seguro”. Solo dice que, según el modelo, hay valor esperado positivo.

### `shadow`
Modo de observación: el bot analiza y registra oportunidades, pero no compra en real. Sirve para aprender sin arriesgar dinero.

Cuando el dashboard habla de señales shadow, habla de oportunidades vistas, no de operaciones ejecutadas.

### `canary`
Etapa intermedia entre observar y operar normal. Una ciudad en canary opera con riesgo reducido para validar que la evidencia también aguanta en real.

Es una prueba controlada, no una promoción completa.

### `promote`
Pasar una ciudad a una etapa superior, normalmente de shadow a canary. En el ranking aparece cuando una ciudad ya juntó evidencia suficiente.

Promover no es automático en esta guía: primero se revisa la evidencia.

### `observed`
Dato observado de temperatura real ya ocurrida. Es lo que permite comparar forecast contra realidad.

Sin `observed`, no hay forma seria de medir si el modelo estuvo bien.

### `NOAA`
Fuente del proxy observado que usa el dashboard para medir forecast vs realidad. No es el settlement final del mercado, pero sí una referencia útil para aprendizaje.

En el dashboard, `NOAA` quiere decir cobertura observacional, no trading.

### `gate_a / gate_b / gate_c`
Son tres semáforos por ciudad. `gate_a` mira el histórico real, `gate_b` la evidencia shadow y `gate_c` la muestra NOAA.

La idea es evitar resumir una ciudad en un solo número opaco.

### `readiness_score`
Puntaje auxiliar de 0 a 99 usado sobre todo para ordenar ciudades. No es el display principal.

Si dos ciudades tienen scores parecidos, mirá antes los tres gates y el estado textual.

### `road to real`
Barra de progreso que resume cuánto falta para volver a operar en real. No decide trading por sí sola.

Su valor real es mostrar qué requisito está frenando el avance hoy.

### `liquidez`
Facilidad para entrar o salir de una posición sin castigar mucho el precio. Un mercado poco líquido puede verse atractivo en teoría pero ser malo en práctica.

Si falta liquidez, el bot puede descartar la oportunidad.

### `kelly`
Regla para calcular tamaño de apuesta según edge y riesgo. Si el resultado es demasiado bajo, el bot puede decidir no entrar.

No es una alerta de fallo: suele indicar que la ventaja era insuficiente para justificar tamaño.

### `sigma`
Medida de incertidumbre del forecast. Cuanto más alta, más “ancho” es el rango de error que el bot asume.

En el dashboard aparece ligada a calibración y a evidencia suficiente por ciudad.

### `condition_filtered`
Mercado descartado por no ser una condición direccional útil para esta fase, por ejemplo `range` o `exact`.

No es necesariamente un problema: hoy el sistema prioriza condiciones direccionales.

## Qué NO mirar todavía

Si Pablo recién empieza, puede ignorar sin perder nada crítico:

- La tabla `Ultimos 20 casos` de NOAA. Sirve para investigar, no para el chequeo rápido.
- Los números finos de `PnL serie`, `Win rate` y `Cierres` cuando la muestra es chica. Son contexto, no volante de mando.
- El detalle exacto del `readiness_score`. El ranking importa menos que leer los tres gates y el `Estado`.
- La lista larga de ciudades bloqueadas, salvo que una ciudad que te importe aparezca ahí.
- Cualquier interpretación fuerte de MAE o Bias con poca muestra. Si el bloque dice “acumulando”, tomalo literalmente.

## Flujos de decisión

### Veo una ciudad con `gate_a = Malo`

Eso significa que el histórico real de esa ciudad ya tiene evidencia mala o una regla de salida disparada. No la promociones aunque `gate_b` venga bien.

Abrí el ranking, confirmá si además está `Bloqueada`, `Shadow degradada` o `Revisar salida`. Si sigue activa, la acción correcta es revisar por qué todavía no salió de carrera.

### `Road to Real` no avanza en 3 días

Primero mirá qué check está clavado. Si es NOAA, el problema es observabilidad; si es shadow, el problema es falta de señales útiles; si es alertas críticas, el problema es operativo.

No saques conclusiones globales por el porcentaje total. El valor del bloque está en identificar cuál requisito dejó de moverse y bajar a ese bloque.

### `shadow` tiene 0 edges todo el día

Puede ser normal en un día flojo, pero no si además hubo muchos mercados direccionales escaneados. Mirá `Mercados escaneados` y cuántos fueron `direccionales`.

Si hubo scan pero no hubo edges en todo el día, revisá si el mercado ofrecía edge real, si todo quedó en `condition_filtered` o si hay un problema de señales.

### Veo `signals.json stale`

Si el Bloque 1 sigue en `Sano con limitaciones` y no hay alertas rojas, no significa parar el bot de inmediato. Sí significa revisar hoy el pipeline de señales.

Si `signals` pasa a `missing` o `error`, deja de ser una revisión tranquila y pasa a ser intervención antes del próximo ciclo.
