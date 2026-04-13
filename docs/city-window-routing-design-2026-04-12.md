# City Window Routing — Diseño Arquitectónico

**Fecha:** 2026-04-12
**Autor:** Opus (diseño), Pablo (dirección)
**Estado:** Diseño cerrado (v2 — corregido tras revisión Codex), pendiente implementación
**Revisión v2:** Tres correcciones arquitectónicas sobre v1: (1) `compute_city_windows()` delega a `get_min_days_for_city()` en vez de reimplementar lógica timezone, (2) contadores estructurados en `cycle_data["scan"]` para preservar observabilidad, (3) orden de pipeline fijado explícitamente.

## Problema

El bot corre 3 ciclos diarios (08h, 16h, 23h UTC) y en cada uno escanea **todos** los mercados de temperatura de Polymarket, para **todas** las ciudades. Los filtros per-city (`get_min_days_for_city()`, `timezone_filter`) descartan después lo que ya llega tarde. Esto genera:

- `timezone_filter`: 15.3% del funnel reciente (605 skips en last12) — 100% ciudades asiáticas vistas a 16-21h local en ciclos 08-09h UTC
- `date_out_of_range_past` same-day estructural: 42.5% del funnel, 98.6% ya demasiado tarde según el cutoff 14h local del propio bot
- skip_log de ~350 entradas por ciclo para mercados que **nunca pueden pasar**

El costo real no es de API (PASO 1 es un solo bulk fetch) ni de NOAA (PASO 3 solo consulta ciudades que pasaron filtros). Es:
1. Ruido en skip_log que dificulta diagnóstico operacional
2. Overhead de parsing/filtrado para mercados estructuralmente inviables
3. Imposibilidad de cubrir Asia (ningún slot actual cae antes de 14h local allí)

## Restricciones del diseño

- No tocar lógica de edge, thresholds, bankroll, política de ciudades
- `get_min_days_for_city()` se mantiene como safety net (no se elimina)
- Compatible con Railway cron sin añadir servicios
- Reversible sin pérdida de datos
- No implementar en esta sesión

## Decisión 1: Arquitectura

### Elegido: Filtro dinámico per-city (no regiones estáticas)

**Descartado: regiones estáticas** (4 grupos tipo Asia/Europa/América-E/América-W). Requiere mantener un mapping manual que se desincroniza con `CITY_TIMEZONES`. Pierde precisión en bordes (Denver vs LA son región "América-W" pero tienen 1h de diferencia). Añade una capa de abstracción sin beneficio real.

**Descartado: routing per-city estático** (mapping explícito city→slots en JSON). Más preciso que regiones, pero duplica lo que `CITY_TIMEZONES` + `get_min_days_for_city()` ya computan dinámicamente. No maneja DST sin intervención manual.

**Elegido: pre-cómputo dinámico al inicio de cada ciclo.** Una función `compute_city_windows()` llama a `get_min_days_for_city(city)` una vez por ciudad al inicio del ciclo. Si `min_days >= 1`, la ciudad no tiene hoy viable. No reimplementa la lógica de timezone — la delega.

**Razonamiento:** `get_min_days_for_city()` ya contiene toda la lógica (14h local, date offset, DST via ZoneInfo) **y además respeta el override manual `MIN_DAYS_AHEAD`**. Reimplementar esa lógica en `compute_city_windows()` crearía un segundo source of truth que diverge si Railway fija `MIN_DAYS_AHEAD >= 0`. Delegar garantiza equivalencia total.

### Tabla de cobertura actual (3 slots)

Para referencia, así se ve cada slot con el cutoff 14h local:

| Slot UTC | Asia (UTC+8/+9) | Europa (UTC+0..+2) | América-E (UTC-4/-5) | América-W (UTC-7/-8) |
|----------|-----------------|--------------------|-----------------------|----------------------|
| 08h | 16-17h local ✗ | 08-10h local ✓ | 03-04h local ✓ | 00-01h local ✓ |
| 16h | 00-01h (next day) ✗ | 17-18h local ✗ | 11-12h local ✓ | 08-09h local ✓ |
| 23h | 07-08h (next day) ✗ | 00-01h (next day) ✗ | 18-19h local ✗ | 15-16h local ✗ |

Lectura: **ningún slot existente cubre Asia para same-day.** Europa solo tiene 08h. Las Américas tienen 08h y 16h. El 23h no cubre nada para same-day.

## Decisión 2: Definición de "ventana válida"

### Elegido: misma regla 14h local, sin redefinir

La ventana válida para same-day markets es exactamente: `hora_local < 14` (ya codificada en `get_min_days_for_city()`). No conviene cambiar el umbral porque:

- El razonamiento original (Bug #5, Chongqing) sigue siendo correcto: la temperatura máxima diaria se registra ~14-16h local
- Cambiar el umbral para el routing pero no para el filtro crearía inconsistencia
- El filtro existente ya usa ZoneInfo con zonas IANA (maneja DST)

La función `compute_city_windows()` delega a `get_min_days_for_city()` y retorna un dict para uso en el ciclo. Si `MIN_DAYS_AHEAD` se fija manualmente en Railway, ambas capas se comportan igual.

## Decisión 3: Mercados de mañana (days_ahead ≥ 1)

### Elegido: siempre procesar, sin restricción de ventana

El city-window filter solo aplica a mercados same-day (`days_ahead == 0` relativo al `min_days` de la ciudad). Mercados para mañana o después pasan sin restricción de ventana.

**Razonamiento:** un mercado para "mañana en Tokyo" es igual de válido a las 08h UTC que a las 16h UTC. No hay degradación informacional. Restringirlo a un solo slot reduciría la frecuencia de monitoreo sin beneficio.

**Implicación para shadow data:** las ciudades seguirán acumulando shadow data de mercados futuros en todos los ciclos. La restricción a un solo slot por ciudad NO ocurre. Solo se evita el procesamiento (y logging) de mercados same-day que ya nacen muertos.

## Decisión 4: Dónde vive el cambio

### Elegido: filtro de entrada en PASO 2 de `main()`, dentro de `bot.py`

El cambio vive como pre-cómputo + early-exit dentro del loop de PASO 2.

### Orden exacto del pipeline dentro del loop (v2 — fijado explícitamente)

El pipeline actual en `bot.py:13055-13138` sigue este orden:

```
1. parse_temperature_question(question)   → parsed, city
2. date_text_to_iso(...)                  → date_iso, days_ahead
3. get_effective_city_mode(city)           → city_mode
4. blocked_city check                     → skip + skip_log entry
5. allowlist/shadow logic                 → allowlisted flag (NO skip, continúa)
6. get_min_days_for_city(city)            → min_days
7. days_ahead < min_days check            → timezone_filter / date_out_of_range_past skip
8. days_ahead > MAX_DAYS_AHEAD check      → date_out_of_range_future skip
9. price check                            → price_out_of_range skip
10. liquidity check                       → liquidity_low skip
```

**El city-window pre-filter entra entre paso 5 y paso 6** — después de blocked/mode/shadow, antes de `get_min_days_for_city()`:

```
1-5: [sin cambios — blocked/mode/shadow se resuelven primero]
5.5: city-window pre-filter (NUEVO)
     if days_ahead == 0 and city_windows[city]["min_days"] >= 1:
         structural_skip_count += 1
         structural_skip_cities.add(city)
         continue
6-10: [sin cambios — safety net sigue para lo que pase el pre-filter]
```

**Justificación del orden:** blocked/mode/shadow deben resolverse primero porque:
- `blocked_city` genera su propio skip_log entry y atribución operativa
- La señal humana de shadow/allowlist afecta qué se loguea en Loop B
- El city-window filter es una optimización de ruido, no una decisión de política

Si el pre-filter entrara antes de `blocked_city`, dejaríamos de ver cuántos mercados de ciudades bloqueadas caen en el ciclo. Eso rompería la atribución operativa del funnel.

Después del loop, resumen en decision log:

```python
if structural_skip_count > 0:
    dl.append(f"VENTANA: {structural_skip_count} same-day fuera de ventana ({', '.join(sorted(structural_skip_cities))})")
```

**Descartado: parámetro de Railway por slot.** Requeriría múltiples cron entries con diferentes env vars (`ELIGIBLE_CITIES_08=...`). Frágil, no maneja DST, requiere sync manual cada vez que se añade una ciudad.

**Descartado: lógica en el scheduler.** El scheduler solo calcula cuándo despertar, no qué procesar. Mezclar selección de ciudades en `get_next_run_time()` rompe separación de responsabilidades.

**Descartado: skip_log entry per-market.** El objetivo es reducir ruido, no crear ruido diferente. Los skips estructurales se resumen, no se detallan.

### Detalle: observabilidad (v2 — contadores estructurados)

Los mercados same-day filtrados por city-window **no generan entries per-market en skip_log.jsonl**. Pero los contadores se persisten en la capa estructurada del ciclo:

**En `cycle_data["scan"]`** (se escribe a `cycle_summary.json` y `cycles_history.jsonl`):

```python
"scan": {
    "markets_evaluated": len(candidates),
    "with_edge": len(trades),
    "selected": len(selected),
    "shadow": len(shadow_trades),
    "condition_filtered": condition_filtered_skip,
    "city_window_skipped": structural_skip_count,           # NUEVO
    "city_window_cities": sorted(structural_skip_cities),   # NUEVO
},
```

Esto preserva trazabilidad histórica: cualquier auditoría futura puede reconstruir cuántos mercados se filtraron por city-window en cada ciclo, qué ciudades, y la tendencia en el tiempo. Sin per-market entries en skip_log pero con contadores por ciclo en la capa estructurada.

`get_min_days_for_city()` sigue ejecutándose para todo lo que pase el city-window filter, como safety net. Si por algún bug el pre-filtro deja pasar algo, el filtro existente lo atrapa. El skip_log sigue registrando: `timezone_filter` (para lo que escape), `date_out_of_range_past` (para mercados legítimamente tarde, no estructurales), `price_out_of_range`, `blocked_city`, etc.

Impacto estimado en skip_log: de ~350 entries/ciclo a ~150-180 (eliminando los ~170 skips estructurales same-day que hoy se loguean individualmente).

## Decisión 5: Excepciones al routing

### Casos donde NO se restringe

1. **Mercados futuros (days_ahead ≥ 1):** siempre pasan, como se diseñó arriba.

2. **Ciudades sin entry en CITY_TIMEZONES:** fallback a `today_viable=True` (permisivo). Razón: si una ciudad no tiene timezone mapping, es más seguro procesarla y dejar que `get_min_days_for_city()` la filtre con su fallback UTC que silenciarla preemptivamente.

3. **Ciclos forzados (`/run`):** el city-window filter aplica igual. No hay razón para bypassearlo en forzados — un mercado same-day que ya es tarde sigue siendo tarde aunque lo forces.

4. **Ciudades con posiciones abiertas:** `manage_positions()` corre en PASO 0.4, antes de PASO 2. No se ve afectado. El bot sigue monitoreando y vendiendo posiciones independientemente del city-window.

5. **Blocked cities:** se filtran antes del city-window check (el `blocked_city` check viene primero en el pipeline actual y se mantiene).

## Decisión 6: Slot adicional para Asia (propuesta separada)

### Hallazgo: ningún slot actual cubre Asia para same-day

Con los slots 08/16/23 UTC, las ciudades asiáticas (UTC+8/+9) nunca tienen un ciclo donde `hora_local < 14`. Esto NO se resuelve con city-window routing — el routing solo evita el ruido, no crea oportunidades nuevas.

### Propuesta (separada de este diseño): añadir 04h UTC a SCHEDULE_HOURS_UTC

Cambiar `SCHEDULE_HOURS_UTC` de `"8,16,23"` a `"4,8,16,23"`. Esto:

- No requiere nuevo servicio Railway (el scheduler interno de `bot.py` maneja N horas)
- A las 04h UTC, Asia está a 12-13h local → hoy viable
- Cubriría same-day markets para Tokyo, Seoul, Shanghai, etc.

**Esta propuesta es independiente del city-window routing.** El routing reduce ruido con los slots actuales. El slot adicional abre throughput real para Asia. Son complementarias pero no dependientes.

**Trade-off:** un ciclo adicional = una llamada más a la API de Polymarket + más forecast calls. Con ~30 ciudades y pocas passing, el costo es bajo. Pero requiere monitoreo de rate limits.

**Decisión: no incluir en esta implementación.** Documentar como opción futura. Si las ciudades asiáticas pasan a canary/active, el ROI justifica el slot. Mientras sean shadow, el beneficio es solo acumular más shadow data — útil pero no urgente.

## Invariantes que el diseño debe respetar

1. `get_min_days_for_city()` no se modifica ni se remueve — sigue como safety net
2. Mercados con `days_ahead ≥ 1` nunca se filtran por city-window
3. `manage_positions()` no se ve afectado (corre antes)
4. Shadow/canary/blocked modes no cambian
5. `SCHEDULE_HOURS_UTC` no cambia (mismos 3 slots)
6. `skip_log.jsonl` sigue registrando skips reales — solo los estructurales se resumen (pero `city_window_skipped` y `city_window_cities` se persisten en `cycle_data["scan"]`)
7. `compute_city_windows()` delega a `get_min_days_for_city()` — respeta `MIN_DAYS_AHEAD` override
8. Si se elimina el pre-filtro, el comportamiento vuelve al actual sin pérdida de datos
9. `force_event` / `/run` no bypasea el city-window (es un filtro informacional, no operacional)
10. Ciudad sin entry en `CITY_TIMEZONES` → permisiva (no silenciada)

## Especificación funcional

### Nueva funci��n: `compute_city_windows()`

```python
def compute_city_windows():
    """Pre-computa viabilidad same-day por ciudad para el ciclo actual.
    
    Delega a get_min_days_for_city() para cada ciudad en CITY_TIMEZONES.
    Esto garantiza equivalencia con el override manual MIN_DAYS_AHEAD.
    
    Retorna dict {city: {"min_days": int, "today_viable": bool}}
    donde:
      - min_days: resultado de get_min_days_for_city(city) (0 o 1)
      - today_viable: True si min_days == 0 (same-day markets son procesables)
    """
    result = {}
    for city in CITY_TIMEZONES:
        min_days = get_min_days_for_city(city)
        result[city] = {
            "min_days": min_days,
            "today_viable": min_days == 0,
        }
    return result
```

**Nota:** la función es deliberadamente simple. Toda la lógica (14h local, date offset, DST, `MIN_DAYS_AHEAD` override) vive en `get_min_days_for_city()`. Si esa función cambia, `compute_city_windows()` hereda el cambio automáticamente.

### Cambios en `main()`, PASO 2

Antes del loop:

```python
city_windows = compute_city_windows()
structural_skip_count = 0
structural_skip_cities = set()
```

Dentro del loop, **después de blocked/mode/shadow (paso 5) y antes de `get_min_days_for_city()` (paso 6)**:

```python
# City-window pre-filter (paso 5.5): skip same-day markets para ciudades fuera de ventana
cw = city_windows.get(city)
if cw and not cw["today_viable"] and days_ahead == 0:
    structural_skip_count += 1
    structural_skip_cities.add(city)
    continue
```

Después del loop, en el resumen de decision log:

```python
if structural_skip_count > 0:
    dl.append(f"VENTANA: {structural_skip_count} same-day fuera de ventana ({', '.join(sorted(structural_skip_cities))})")
```

En `cycle_data["scan"]` (PASO final — persistencia estructurada):

```python
"scan": {
    "markets_evaluated": ...,
    "with_edge": ...,
    "selected": ...,
    "shadow": ...,
    "condition_filtered": ...,
    "city_window_skipped": structural_skip_count,
    "city_window_cities": sorted(structural_skip_cities),
},
```

### Qué NO cambia

- PASO 1 (fetch markets): igual, sigue siendo bulk
- PASO 3 (forecasts): igual, solo para candidates
- PASO 4 (edge): igual
- Scheduler: igual
- Railway config: igual
- `skip_log.jsonl` format: igual (solo menos entries)
- `cycles_history.jsonl` format: compatible (nuevos campos en `scan`, no rompe lectores existentes)
- Dashboard: igual (podría mostrar city-window info en futuro)

## Lo que queda para implementación (Codex)

1. **Añadir `compute_city_windows()`** — función pura, delega a `get_min_days_for_city()`, ~10 líneas
2. **Insertar pre-filtro en PASO 2, entre paso 5 (shadow) y paso 6 (`get_min_days_for_city`)** — 5 líneas de early-exit + 2 contadores
3. **Añadir línea de resumen en decision log** — 2 líneas post-loop
4. **Añadir `city_window_skipped` y `city_window_cities` a `cycle_data["scan"]`** — 2 líneas en el bloque de persistencia (~`bot.py:13738`)
5. **Verificar con `verify_before_deploy.py`** — debe pasar sin errores
6. **Test manual**: comparar skip_log de un ciclo antes vs después; verificar que `cycle_summary.json` contiene los nuevos campos
7. **NO tocar**: `get_min_days_for_city()`, `SCHEDULE_HOURS_UTC`, Railway config, skip_log schema, pipeline order de blocked/mode/shadow

Estimación de complejidad: baja. El cambio es ~20 líneas de código nuevo, ninguna lógica de trading afectada. El punto de inserción exacto en el pipeline está fijado (entre paso 5 y paso 6 del loop de PASO 2).

## Conflictos identificados y resueltos en v2

### 1. Divergencia con MIN_DAYS_AHEAD override (resuelto)

**Hallazgo Codex:** v1 de `compute_city_windows()` reimplementaba la lógica timezone sin respetar `MIN_DAYS_AHEAD >= 0` (override manual desde Railway). Si Railway fija `MIN_DAYS_AHEAD=1`, el pre-filter seguía usando la lógica de 14h local.

**Resolución:** `compute_city_windows()` ahora delega a `get_min_days_for_city(city)`. Un solo source of truth.

### 2. Pérdida de observabilidad (resuelto)

**Hallazgo Codex:** v1 solo guardaba los skips estructurales en una línea de `dl` (decision log humano). Las auditorías de funnel salen de `skip_log.jsonl` y `cycles_history.jsonl`, no de decision log.

**Resolución:** contadores `city_window_skipped` y `city_window_cities` se persisten en `cycle_data["scan"]`, que se escribe a `cycle_summary.json` y `cycles_history.jsonl`. La evidencia sobrevive para auditorías futuras.

### 3. Orden de pipeline ambiguo (resuelto)

**Hallazgo Codex:** v1 decía "después de parsear city pero ANTES de `get_min_days_for_city()`", pero no fijaba si eso es antes o después de blocked/mode/shadow. Si entraba antes de `blocked_city`, se perdería atribución operativa.

**Resolución:** orden fijado explícitamente como paso 5.5: después de blocked/mode/shadow (pasos 3-5), antes de `get_min_days_for_city()` (paso 6).

### Edge case timezone (ya resuelto por diseño)

Los edge cases de `local_date_offset` (ciudad en ayer/mañana) se resuelven automáticamente porque `compute_city_windows()` delega a `get_min_days_for_city()`, que ya los maneja con comparación de `local_now.date()` vs `datetime.now(timezone.utc).date()`.
