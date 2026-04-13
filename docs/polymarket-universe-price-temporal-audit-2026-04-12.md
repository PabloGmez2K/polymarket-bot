# Polymarket Universe And Price Temporal Audit - 2026-04-12

## Objetivo

Responder con evidencia runtime a dos preguntas nuevas para throughput, sin tocar `bot.py`,
`city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`:

1. cual es el universo real observado de mercados de temperatura de Polymarket por ciudad y dia
2. si los mercados que hoy caen en `price_out_of_range` alguna vez entran en rango util mas adelante

## Preflight y Fuente

- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=6`, `warning=2`, `error=0`
- snapshot base: `data/runtime_import/`, `pulled_at=2026-04-12T10:15:51.3083432+00:00`
- analisis reproducible: `python tools/analyze_market_universe.py`
- ventana leida: `29` ciclos normales entre `2026-04-05T20:09:48+00:00` y `2026-04-12T09:45:48+00:00`

## Resumen Ejecutivo

- el techo inmediato parece venir mas de Polymarket que del bot: el universo observado es muy estable, no una masa creciente que el bot este dejando escapar
- por ciclo, el bot sigue viendo practicamente siempre el mismo orden de magnitud: `324-330` mercados y `30` pares `city + date`
- la estructura interna tambien es muy rigida: `273` de `277` combinaciones `city + date` observadas tienen exactamente `11` mercados
- el bucket `price_out_of_range` casi nunca se convierte en throughput util despues:
  - `1091` mercados unicos tocaron `price_out_of_range`
  - solo `25` (`2.3%`) llegaron despues a una fase pre-edge
  - `810` (`74.2%`) salieron del bucket de precio solo para morir en filtros temporales
  - `256` (`23.5%`) nunca salieron del bucket de precio
- conclusion operativa: cambiar el timing puede mover una fraccion pequena de algunos mercados, pero no hay evidencia de que el bucket de precio esconda una bolsa grande de candidatos recuperables

## 1. Universo Real Observado de Polymarket

### 1.1 Estabilidad por ciclo

- `29/29` ciclos normales quedan entre `324` y `330` mercados observados
- mediana por ciclo: `330`
- `19` de `29` ciclos ya clavan exactamente `330`
- los `30` pares `city + date` por ciclo tambien son estables en toda la ventana

Lectura:

- no aparece una expansion del universo bruto dentro de esta muestra
- el problema no parece ser "el bot escanea poco"
- la foto mas honesta hoy es: Polymarket ofrece un universo bastante fijo y el embudo se estrecha despues

### 1.2 Estructura por ciudad y dia

Histograma de mercados por `city + date` observado en la ventana:

- `11` mercados: `273` city-dates
- `9` mercados: `1`
- `8` mercados: `1`
- `7` mercados: `2`

Los unicos outliers con menos de `11` fueron:

- `Moscow 2026-04-09` -> `9`
- `Moscow 2026-04-10` -> `7`
- `Moscow 2026-04-11` -> `8`
- `Toronto 2026-04-07` -> `7`

Lectura:

- el universo observado no solo es estable en volumen total, tambien es muy regular dentro de cada ciudad/dia
- eso debilita la idea de que falten muchos mercados ocultos por discovery o que el ceiling inmediato venga de una mala cobertura del bot
- para subir trades/dia, la palanca no parece ser "descubrir mas mercados"; parece ser convertir mejor el universo ya visible

### 1.3 Nota sobre crecimiento

La suma por `date_iso` crece en dias centrales de la ventana porque acumula varias fechas de mercado coexistiendo en distintos ciclos, no porque cada ciclo traiga una explosion nueva de universo. La lectura valida para ceiling es la per-cycle: ahi el universo luce esencialmente plano.

## 2. Auditoria Temporal de `price_out_of_range`

### 2.1 Cuantos mercados vuelven a rango

Sobre `1091` mercados unicos que tocaron `price_out_of_range`:

- `810` (`74.2%`) salen del bucket de precio solo para caer luego en `date_out_of_range_past`, `date_out_of_range_future` o `timezone_filter`
- `256` (`23.5%`) se quedan siempre en `price_out_of_range`
- `25` (`2.3%`) llegan alguna vez a fase pre-edge (`condition_filtered`, `below_min_edge`, `kelly_too_low`, etc.)

Lectura:

- si, existen ventanas donde algunos mercados dejan de estar demasiado baratos
- pero casi siempre eso ocurre demasiado tarde para throughput util
- la historia dominante no es "los baratos luego suben y se vuelven candidates"; es "los baratos dejan de ser baratos cuando ya pasan a morir por tiempo"

### 2.2 Forma real del bucket

- `1058` de `1091` (`97.0%`) ya entran por primera vez con `mkt_prob < 20`
- el mismo `97.0%` nunca llega a ver un precio `>= 20` en ninguna observacion posterior

Lectura:

- el bucket sigue siendo extremadamente extremo, no marginal
- no hay evidencia de una nube grande oscilando justo alrededor del bound de precio

### 2.3 Tiempo hasta cambiar de estado

- cuando un mercado logra llegar a fase pre-edge, tarda entre `0.57h` y `17.00h`, con mediana `8.01h`
- cuando solo cambia para morir por fecha/zona, tarda entre `3.46h` y `41.00h`, con mediana `10.55h`

Lectura:

- incluso los pocos casos que mejoran lo hacen con una espera no trivial
- eso vuelve poco convincente la idea de que un simple "otro slot general" vaya a rescatar una parte grande del bucket de precio

## 3. Ciudades Donde el Bucket de Precio Parece Menos Muerto

Top por volumen de mercados que tocaron `price_out_of_range`:

- `Shanghai`: `74`, de los cuales `2` (`2.7%`) llegaron a pre-edge
- `Chicago`: `74`, de los cuales `2` (`2.7%`) llegaron a pre-edge
- `Seoul`: `73`, de los cuales `9` (`12.3%`) llegaron a pre-edge
- `London`: `70`, de los cuales `3` (`4.3%`) llegaron a pre-edge
- `Miami`: `48`, de los cuales `3` (`6.2%`) llegaron a pre-edge

Lectura:

- `Seoul` destaca como la ciudad menos estanca dentro de un cuadro general aun muy flojo
- `Miami` y `London` muestran algo de movilidad, pero con volumen util todavia pequeno
- `Shanghai` y `Chicago` tienen mucho ruido de precio pero casi nada llega a volverse util

## 4. Implicacion Para Throughput

### Lo que esta bastante claro

- el universo observado de Polymarket luce estable; no hay señal de crecimiento rapido dentro de esta muestra
- el bucket `price_out_of_range` no parece esconder un reservorio grande de trades recuperables por esperar un poco
- por tanto, el techo actual de throughput no parece ser principalmente "el bot no ve suficiente universo"

### Lo que aun no debemos concluir

- no significa que nunca haya valor en el slot `04h`; este snapshot fue tirado a `2026-04-12T10:15:51+00:00` y todavia no contiene una ventana limpia post-rollout suficiente para juzgar ese experimento
- tampoco significa que el timing ya no importe nada; significa que `price_out_of_range` no justifica por si solo una tesis de timing amplio

## Veredicto Corto

La respuesta corta a la propuesta de Opus es:

1. el universo real observado de Polymarket parece hoy estable y muy regular: `~330` mercados por ciclo, `30` city-dates, casi siempre `11` mercados por city-date
2. los mercados baratos rara vez se convierten despues en throughput util: solo `2.3%` llegan a fase pre-edge, mientras `97.0%` nunca llegan siquiera a tocar `>=20`

## Siguiente Sesion Logica

Si queremos seguir empujando trades/dia con evidencia y sin abrir refactor core, lo mas prometedor ya no parece ser un cambio global de precio o discovery, sino una de estas dos vias:

- observar con muestra nueva el impacto real del slot `04h` sobre `Seoul`, `Shanghai` y `Tokyo`
- hacer una micro-auditoria por ciudad/slot para los pocos sitios donde el bucket de precio muestra algo de movilidad real (`Seoul` primero, luego `Miami`/`London` si sigue habiendo muestra)
