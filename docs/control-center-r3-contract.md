# R3 — Log de skips por ciclo (contrato Claude ↔ Codex)

**Fecha:** 2026-04-05
**Sesión:** R3 split (Claude backend + tests, Codex analyzer offline en paralelo)
**Objetivo:** registrar, para **cada ciudad en cada ciclo**, la razón exacta por la que NO entró en trade. Hoy el bot evalúa ~150 candidatos por ciclo y solo ejecuta 0-3 trades reales; los 147+ skips son información estratégica tirada a la basura. Saber cuántos caen por `below_min_edge` vs `fuera_allowlist` vs `kelly_too_low` en los últimos 30 ciclos es la base para decidir si bajar `MIN_EDGE`, expandir allowlist, o recalibrar sigma.

Este documento es el contrato estable entre las dos tareas en paralelo. Claude garantiza el **schema de las filas** de `data/skip_log.jsonl`; Codex lo consume desde un script offline sin necesidad de leer `bot.py`.

---

## División de trabajo

| Parte | Responsable | Archivos |
|---|---|---|
| Backend: instrumentar el scan loop + writer + reader + tests | **Claude (Opus)** | `bot.py` (scan loop en `run_cycle`, líneas ~11283-11516), `verify_before_deploy.py` |
| Offline analyzer CLI + docs de uso | **Codex** | `tools/analyze_skip_log.py`, `docs/skip-log-analyzer.md` |

**Cero solapamiento de archivos.** Codex no toca `bot.py`, `verify_before_deploy.py`, ni el writer/reader. Claude no toca `tools/analyze_skip_log.py`.

El archivo de datos `data/skip_log.jsonl` es **generado** por el bot en runtime y consumido por el analyzer. No se versiona (ya está en `.gitignore` vía `data/`).

---

## Contrato JSON (garantizado por Claude)

Cada ciclo emite **N filas** en `data/skip_log.jsonl` (una por skip — un mismo mercado puede aparecer como un único skip). Formato: **JSON Lines UTF-8**, un objeto por línea, append-only.

### Schema de fila

```json
{
  "ts_utc": "2026-04-05T16:00:12.345678+00:00",
  "cycle_id": "2026-04-05T16:00",
  "city": "Tokyo",
  "date_iso": "2026-04-10",
  "side": "YES",
  "skip_reason": "below_min_edge",
  "city_mode": "active",
  "allowlisted": true,
  "days_ahead": 5,
  "edge_pct": 1.8,
  "our_prob": 62.4,
  "mkt_prob": 60.6,
  "min_edge": 3.0,
  "forecast_max": 28.3,
  "threshold": 27.0,
  "threshold_high": null,
  "unit": "C",
  "condition": "above",
  "sigma_used": 2.1,
  "question": "Tokyo temperature above 27C on April 10?",
  "extras": {}
}
```

### Reglas de campos

- **Siempre presentes (nunca omitidos):** `ts_utc`, `cycle_id`, `skip_reason`, `extras`.
- **Nullable** (pueden ser `null` cuando no aplican al punto del loop donde se generó el skip): `city`, `date_iso`, `side`, `city_mode`, `allowlisted`, `days_ahead`, `edge_pct`, `our_prob`, `mkt_prob`, `min_edge`, `forecast_max`, `threshold`, `threshold_high`, `unit`, `condition`, `sigma_used`, `question`.
- **`ts_utc`**: ISO 8601 con tz-aware UTC (`datetime.now(timezone.utc).isoformat()`).
- **`cycle_id`**: string determinista por ciclo, formato `"YYYY-MM-DDTHH:MM"` en UTC (minuto redondeado del arranque del ciclo). Todas las filas de un mismo ciclo comparten `cycle_id` exacto — es la clave de agrupación primaria del analyzer.
- **`edge_pct`**, **`our_prob`**, **`mkt_prob`**: porcentajes (`3.0` = 3%), no fracciones. Consistencia con el resto del código de `bot.py`.
- **`threshold`**: siempre en la unidad original del mercado (`unit`). `threshold_high` solo presente en mercados de rango.
- **`extras`**: diccionario libre, siempre `{}` si no hay nada. Reservado para campos ad-hoc por razón (ej: `{"existing_token_id": "0xabc..."}` para `existing_position`). **Codex debe tolerar claves desconocidas.**

---

## Enum `skip_reason` (17 valores)

Cada valor corresponde a un `continue` o desvío-a-shadow del scan loop. Agrupados por riqueza de datos disponibles en el punto del skip.

### Grupo A — datos ricos (edge ya calculado)

Estos son los que más valor tienen para recalibración. `our_prob`, `mkt_prob`, `edge_pct`, `forecast_max`, `sigma_used`, `threshold`, `city`, `date_iso`, `side`, `days_ahead` **siempre presentes y no-null**.

| `skip_reason` | Línea bot.py | Cuándo dispara |
|---|---|---|
| `no_edge` | ~11472 | `edge_yes<=0` y `edge_no<=0` simultáneamente |
| `below_min_edge` | ~11478 | `edge_pct < MIN_EDGE` (hoy 3.0) |
| `kelly_too_low` | ~11483 | `calculate_position()` devuelve `None` (bet < $1 mínimo) |
| `shadow_only_override` | ~11498 | `_is_shadow_only()` apagó ejecución para city originalmente `active`/`canary`. Edge **sí** calculado, ejecución **no**. Este es el caso crítico del fix `c8c8e73`. |
| `existing_order` | ~11503 | `token_id in open_token_ids` |
| `sold_this_cycle` | ~11509 | `token_id in sold_this_cycle` (v10.4 Fix Bug #9) |
| `existing_position` | ~11515 | `token_id in existing_position_tokens` (v10.4 Fix Bug #3) |

### Grupo B — datos parciales (antes de edge eval)

Estos skips ocurren en Loop A (filtrado de candidatos). `city`, `date_iso`, `days_ahead`, `city_mode`, `allowlisted` presentes cuando ya se parsearon. `edge_pct`/`our_prob`/`mkt_prob`/`forecast_max`/`sigma_used` = `null`.

| `skip_reason` | Línea bot.py | Cuándo dispara |
|---|---|---|
| `blocked_city` | ~11303 | `city_mode == "blocked"` |
| `fuera_allowlist` | ~11315 | `city_mode` ∉ {`active`, `canary`} y **NO** es shadow-override (city realmente fuera de allowlist). Excluye el caso shadow-override que va al Grupo A. |
| `timezone_filter` | ~11327 | `min_days > min_days_global` y `days_ahead < min_days` (v10.3 Bug #5 fix) |
| `date_out_of_range_past` | ~11330 | `days_ahead < min_days_global` |
| `date_out_of_range_future` | ~11334 | `days_ahead > MAX_DAYS_AHEAD` |
| `price_out_of_range` | ~11357 | `mkt_prob` fuera de `[MIN_PRICE, MAX_PRICE]` en ambos lados |
| `liquidity_low` | ~11362 | `liquidity < MIN_LIQUIDITY` |
| `condition_filtered` | ~11427 | `condition_name not in ALLOWED_CONDITIONS` (va también a shadow tracking) |
| `forecast_missing` | ~11411 | `city not in forecast_cache` o fecha faltante en el cache |

### Grupo C — datos mínimos (parse fail)

| `skip_reason` | Línea bot.py | Cuándo dispara |
|---|---|---|
| `parse_fail` | ~11286, 11292, 11298, 11341, 11343, 11348, 11350 | Mercado mal parseado: pregunta ilegible, fecha no convertible, JSON malformado, clob_ids insuficientes. `city`, `date_iso`, `days_ahead`, etc. = `null`. `question` presente (string raw) si se logró leer. |

### Importante: `shadow_only_override` NO se loguea en Loop A

Cuando una ciudad `active`/`canary` es apagada por shadow-only, el scan loop NO la filtra en Loop A — la sigue procesando con `allowlisted=False` y llega a Loop B:11486 donde tiene edge calculado. Ahí es donde se emite el `skip_log` entry con **datos ricos**. Loop A solo emite `fuera_allowlist` para ciudades realmente fuera de allowlist (no shadow-override). Distinguir estos dos caminos es clave para el analyzer.

---

## Ubicación, formato, rotación

- **Archivo:** `data/skip_log.jsonl`
- **Formato:** JSON Lines, una fila por línea, UTF-8, terminada en `\n`.
- **Append-only.** Nunca se reescriben filas existentes.
- **Rotación:** al principio de cada ciclo, si `data/skip_log.jsonl` excede **20 MB**, se rota a `data/skip_log.YYYY-MM-DD.jsonl` y se crea uno nuevo. El reader debe tolerar la existencia de archivos rotados (ver API abajo). 20 MB ≈ ~60k filas ≈ ~400 ciclos a ritmo actual — suficiente para análisis de 2 semanas.
- **`.gitignore`:** ya cubierto por `data/` existente, no hay que tocar.

---

## API writer/reader (en `bot.py`, exportada al módulo)

Claude implementa estas 3 funciones puras, con side effects mínimos. Deben estar **al nivel de módulo**, no dentro de `run_cycle`, para testear aisladas.

### `append_skip_log_entries(entries: list[dict]) -> None`

- Recibe una lista de dicts ya formateados según el schema.
- Valida que cada dict tenga `ts_utc`, `cycle_id`, `skip_reason`, `extras` (fail-fast si falta alguno).
- Abre `data/skip_log.jsonl` en modo append, hace **una sola** llamada a `write()` con todas las líneas concatenadas por `\n`, cierra.
- Chequea rotación **antes** de escribir (si `os.path.getsize()` > 20 MB, rotar).
- **Nunca lanza excepciones hacia el scan loop.** Cualquier error se loggea con `log.warning(...)` y se descarta — el trading no se cae por un log roto.

### `read_skip_log_last_n_cycles(n: int) -> list[dict]`

- Lee `data/skip_log.jsonl` desde el final hacia atrás, acumula filas hasta reunir `n` valores únicos de `cycle_id`, devuelve todas las filas de esos `n` ciclos.
- Si el archivo actual no alcanza, continúa en los archivos rotados (`data/skip_log.YYYY-MM-DD.jsonl`) ordenados por fecha descendente.
- Devuelve lista plana (no agrupada por ciclo). El analyzer agrupa.
- Skip silencioso de líneas malformadas (JSON decode error) con `log.warning`.

### `read_skip_log_since(ts_utc_iso: str) -> list[dict]`

- Lee todas las filas con `ts_utc >= ts_utc_iso`.
- Igual tolerancia a archivos rotados y líneas malformadas.

**Codex NO usa estas funciones** — el analyzer lee los archivos JSONL directamente con `json.loads(line)`. Esto permite que Codex trabaje sin importar `bot.py`.

---

## Hot path constraints (crítico)

El scan loop corre en un thread que compite con ejecución de trades. Cualquier regresión de performance acá **frena BUYs reales** y es leak directo de dinero.

Reglas obligatorias para la instrumentación:

1. **No I/O dentro del for de candidatos.** Acumular entries en una lista local `skip_log_entries = []` y hacer **un único** `append_skip_log_entries(skip_log_entries)` al final del scan loop, después de `PASO 6: Ejecución`.
2. **Si el writer falla, el ciclo no se cae.** Try/except alrededor del write único, warning log, continuar.
3. **Construcción de dicts barata.** Helpers locales tipo `_make_skip_entry(reason, c=None, side=None, **kwargs)` que devuelvan el dict con defaults `null`. Evitar copiar `candidates` enteros.
4. **Cero cambio en el control flow existente.** Cada `continue` actual queda donde está; solo se añade `skip_log_entries.append(_make_skip_entry(...))` inmediatamente antes.
5. **Rotación solo al principio del ciclo.** No chequear tamaño en cada write.
6. **`cycle_id` capturado una vez** al arrancar `run_cycle()` y reutilizado en toda la función.

---

## Qué NO cambia (garantía de backwards compat)

- Todos los `continue` del scan loop se mantienen en la misma línea con la misma condición. Solo se **añade** un `append` justo antes.
- El log humano-legible actual (`dl.append(f"...")` y `edge_analysis.append(...)`) se mantiene intacto. El `skip_log.jsonl` es **adicional**, no reemplazo.
- Los contadores existentes (`parse_fail`, `date_fail`, `blocked_city_skip`, etc.) se mantienen — se usan para el resumen humano de `FILTROS: ...`.
- `bot_state`, `build_dashboard_*`, `ranking_rows`, `city_decisions`: ninguno se toca.
- No hay cambio en schedule, ejecución de trades, ni comportamiento de `_is_shadow_only()`.
- R1 (3 gates) queda intocado.

---

## Verificación al cierre

### Claude (backend)

- `python -c "import ast; ast.parse(open('bot.py', encoding='utf-8').read())"` → syntax OK
- `python verify_before_deploy.py` → pasa en verde con al menos **548 tests** (target: 556+ tras añadir tests de skip_log)
- Tests nuevos obligatorios en `verify_before_deploy.py`:
  1. `append_skip_log_entries([])` es no-op y no crea archivo vacío.
  2. `append_skip_log_entries([entry])` crea archivo con exactamente 1 línea JSON parseable.
  3. Entry con campos faltantes obligatorios hace fail-fast (no silencia).
  4. Cada uno de los 17 `skip_reason` dispara en un fixture de ciclo (fake markets + fake forecasts), aparece en `data/skip_log.jsonl` con el valor correcto y con los campos obligatorios del grupo correspondiente (A/B/C).
  5. `shadow_only_override` aparece con `edge_pct != null` y `our_prob != null` (confirma que va por Loop B, no Loop A).
  6. `fuera_allowlist` aparece con `edge_pct == null` (confirma que va por Loop A).
  7. `read_skip_log_last_n_cycles(2)` devuelve exactamente las filas de los 2 últimos `cycle_id` distintos.
  8. `read_skip_log_since(ts)` filtra correctamente.
  9. Writer tolera archivo inexistente (primer run) — lo crea.
  10. Writer tolera fallo de disco (mock) — loggea warning y no lanza.
  11. Rotación dispara cuando el archivo supera 20 MB (simulado con threshold override en el test).
  12. Reader lee correctamente desde archivos rotados.
- Checkpoint manual post-deploy: después del primer ciclo real con R3, `cat data/skip_log.jsonl | wc -l` > 0 y `jq '.skip_reason' data/skip_log.jsonl | sort | uniq -c` muestra distribución sana.

### Codex (analyzer)

Expectativa de `tools/analyze_skip_log.py` (Codex puede iterar en detalle):

- CLI con flags:
  - `--last-n-cycles N` (default 30)
  - `--since YYYY-MM-DD`
  - `--city CITY` (filtro opcional)
  - `--csv OUT.csv` (export opcional)
- Output a stdout con al menos 3 secciones:
  1. **Distribución de `skip_reason`** por ciudad — tabla con % de cada razón sobre total de skips de esa ciudad.
  2. **Trend temporal** — para cada `skip_reason`, ¿aumenta o baja en los últimos N ciclos vs los N anteriores? Reportar delta absoluto y %.
  3. **Near-misses** — filas con `skip_reason == "below_min_edge"` y `edge_pct ∈ [MIN_EDGE-3, MIN_EDGE)`, ordenadas por edge descendente. Estos son candidatos directos para sigma recalibration.
- **Cero escritura** a `data/skip_log.jsonl` ni a otros archivos salvo el CSV opcional.
- **Cero import de `bot.py`.** Lee `data/skip_log.jsonl` + archivos rotados con `json.loads(line)` directo.
- `docs/skip-log-analyzer.md` con: instalación, ejemplos de CLI, interpretación de cada sección, 2-3 casos de uso reales (ej: "cómo detectar que un ajuste de sigma es necesario").

### Verificación conjunta

- Claude commitea backend primero (analyzer aún no existe, pero el archivo ya se genera en runtime).
- Codex hace `git pull`, y corre `python tools/analyze_skip_log.py --last-n-cycles 5` contra un `data/skip_log.jsonl` generado por Claude en local con fixtures (o contra Railway via `railway_safe.ps1 ssh cat`).
- Ambos en verde antes de push final a Railway.

---

## Merge order

1. **Claude** commitea backend (`bot.py` + `verify_before_deploy.py`) primero. En ese momento Railway ya empieza a generar `skip_log.jsonl` en el siguiente ciclo.
2. **Codex** hace `git pull`, implementa analyzer, commitea `tools/analyze_skip_log.py` + `docs/skip-log-analyzer.md`.
3. Verificación conjunta en local contra un skip_log real.
4. Push a Railway solo si ambas partes pasan verify (548+ tests) y un ciclo real genera skip_log sin errores.

Si Codex termina primero contra un fixture sintético: el analyzer se commitea igual, y el test de integración contra datos reales se valida cuando Claude termine backend.

---

## Out of scope para R3

- **No** cambiar `MIN_EDGE`, `MIN_LIQUIDITY`, `MIN_PRICE`, `MAX_PRICE`, `MAX_DAYS_AHEAD`, ni thresholds de allowlist. R3 **solo instrumenta**, no decide; el analyzer **sugiere**, no ejecuta.
- **No** tocar la lógica de `_is_shadow_only()` ni el fix `c8c8e73`.
- **No** tocar R1 (3 gates en `ranking_rows`).
- **No** agregar skip_log al dashboard web (es consumo offline por ahora; si más adelante se quiere surface en el Control Center, será R4 o posterior).
- **No** bump de versión (v10.6.11 se mantiene hasta que haya feature user-facing).
- **No** backfillear skips de ciclos anteriores — skip_log arranca desde el deploy de R3.
