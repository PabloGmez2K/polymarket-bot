# Skip Log Analyzer

`tools/analyze_skip_log.py` es un analizador offline para `data/runtime_import/skip_log.jsonl` y sus rotaciones, con fallback a `data/skip_log.jsonl` si no existe snapshot runtime importado. Lee JSON Lines directo con `json.loads(line)`, no importa `bot.py`, tolera filas malformadas con warning a `stderr` y no escribe nada salvo que se use `--csv`.

## Instalación

No requiere instalación extra: es un script Python puro con librería estándar.

```bash
python tools/analyze_skip_log.py
```

Si no existe `skip_log.jsonl` ni en `data/runtime_import/` ni en `data/`, el script termina con exit code `1`. Si el archivo existe pero todavía no tiene filas válidas, imprime:

```text
skip_log vacío — aún no corrió ningún ciclo con R3
```

## Flags y ejemplos

`--last-n-cycles N`

```bash
python tools/analyze_skip_log.py --last-n-cycles 30
```

Usa los últimos `N` `cycle_id` distintos. Default: `30`.

`--since YYYY-MM-DD`

```bash
python tools/analyze_skip_log.py --since 2026-04-01
```

Filtra filas con `ts_utc >= YYYY-MM-DDT00:00:00Z`.

`--city CITY`

```bash
python tools/analyze_skip_log.py --city Tokyo
```

Restringe el análisis a una ciudad exacta, case-insensitive.

`--csv OUT.csv`

```bash
python tools/analyze_skip_log.py --last-n-cycles 60 --csv out/skip_log_filtered.csv
```

Exporta a CSV las filas filtradas que el analyzer usó para las 3 secciones.

`--min-edge FLOAT`

```bash
python tools/analyze_skip_log.py --min-edge 3.0
```

Override del umbral usado para la sección de near-misses. El default operativo del analyzer es `3.0`.

Combinando flags:

```bash
python tools/analyze_skip_log.py --since 2026-04-01 --city Chicago --last-n-cycles 20 --min-edge 3.0
```

## Cómo leer la salida

### 1. Distribución de skip_reason por ciudad

La primera sección lista una tabla `City | Total | Skip Reason | Count | % City`.

- `Total` es el número total de skips de esa ciudad dentro de los filtros aplicados.
- `% City` es el peso de esa razón sobre el total de skips de esa ciudad.
- Las ciudades salen ordenadas por mayor volumen de skips, para detectar rápido dónde concentrar el análisis.

Lectura práctica:

- Si una ciudad tiene `liquidity_low` arriba de `40-50%`, el cuello de botella no es el modelo sino el mercado.
- Si domina `below_min_edge`, el problema suele ser calibración, threshold o calidad del forecast.
- Si aparece mucho `shadow_only_override`, la ciudad sí genera edges pero está frenada por policy state.

### 2. Trend temporal

La segunda sección compara, para cada `skip_reason`, las últimas `N/2` ventanas de ciclo contra las `N/2` anteriores.

- `Prev Xc` y `Last Xc` son los conteos en cada mitad.
- `Delta` es el cambio absoluto de filas.
- `Delta %` es el cambio relativo contra la ventana anterior.
- `Mark` muestra `↑` o `↓` cuando el cambio supera `20%`.

Lectura práctica:

- `below_min_edge ↑` sugiere que el edge reciente empeoró frente a la ventana previa.
- `forecast_missing ↓` suele confirmar mejora del pipeline de forecast.
- `shadow_only_override ↑` puede ser una señal sana si una ciudad volvió a generar edge, aunque siga en shadow.

### 3. Near-misses

La tercera sección toma filas con `skip_reason == "below_min_edge"` y `edge_pct` en `[MIN_EDGE-3, MIN_EDGE)`, ordenadas por `edge_pct` descendente. Muestra top 20 con:

- `city`
- `date_iso`
- `side`
- `edge_pct`
- `our_prob`
- `mkt_prob`
- `forecast_max`

Lectura práctica:

- Son los candidatos más cercanos a convertirse en trades reales.
- Si el top 20 está lleno y repetido por pocas ciudades, suele haber margen para revisar sigma o threshold.
- Si casi no hay near-misses, bajar `MIN_EDGE` probablemente no mueva demasiado el throughput.

## Casos de uso reales

### A. Detectar que `MIN_EDGE` está demasiado alto

Corré:

```bash
python tools/analyze_skip_log.py --last-n-cycles 30 --min-edge 3.0
```

Señales a buscar:

- En distribución, `below_min_edge` domina varias ciudades.
- En trend, `below_min_edge` no cae y hasta sube.
- En near-misses aparecen muchas filas con `edge_pct` muy cerca del corte, por ejemplo `2.7-2.9`.

Interpretación: el bot está encontrando señales, pero las deja afuera por un margen fino. Eso no obliga a bajar `MIN_EDGE`, pero sí justifica revisar si el umbral está demasiado agresivo para la sigma actual.

### B. Detectar que una ciudad concentra skips por `liquidity_low`

Corré:

```bash
python tools/analyze_skip_log.py --city Buenos_Aires --last-n-cycles 30
```

o bien sin filtro de ciudad para ver el ranking global.

Señales a buscar:

- La tabla de distribución muestra `liquidity_low` como razón dominante de una ciudad.
- El trend confirma que no es un pico aislado, sino un patrón sostenido.

Interpretación: bajar `MIN_EDGE` no resolvería casi nada ahí. El bloqueo está en profundidad de mercado, no en calibración del modelo.

### C. Detectar que `shadow_only_override` es el bloqueador dominante

Corré:

```bash
python tools/analyze_skip_log.py --last-n-cycles 30
python tools/analyze_skip_log.py --city Tokyo --last-n-cycles 30
```

Señales a buscar:

- `shadow_only_override` pesa fuerte en la distribución, especialmente en ciudades `active/canary`.
- En trend aparece estable o en subida.
- Los near-misses no explican el bloqueo principal porque esas filas ya tienen edge calculado y no fallan por threshold.

Interpretación: esa ciudad ya produce señales con edge, pero la policy todavía la retiene. Cuando `shadow_only_override` se vuelve el skip dominante y las otras razones no son críticas, hay evidencia para evaluar si corresponde desactivar shadow-only o promover la ciudad.
