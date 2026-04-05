# R1 — Motor de ciudades: 3 gates (contrato Claude ↔ Codex)

**Fecha:** 2026-04-05
**Sesión:** R1 split (Claude backend, Codex frontend en paralelo)
**Objetivo:** reemplazar `readiness_score` 0-99 como display primario por 3 gates semafóricos (A historial / B shadow / C NOAA) para que el ranking de ciudades sea interpretable de un vistazo.

Este documento es el contrato estable entre las dos tareas en paralelo. Claude garantiza estos campos en el JSON de `city_decisions.ranking_rows`; Codex los consume desde el template sin ambigüedad.

---

## División de trabajo

| Parte | Responsable | Archivos |
|---|---|---|
| Backend: emitir `gate_a`, `gate_b`, `gate_c` en `ranking_rows` + tests | **Claude (Opus)** | `bot.py` (`build_dashboard_city_decisions`), `verify_before_deploy.py` |
| Frontend: renderizar los 3 gates en `templates/dashboard.html` + estilos + glosario | **Codex** | `templates/dashboard.html`, `static/dashboard.css` |

**Cero solapamiento de archivos.** Codex no toca `bot.py`; Claude no toca el template ni el CSS.

---

## Contrato JSON (garantizado por Claude)

Cada fila de `dashboard.city_decisions.ranking_rows` va a incluir estos 3 nuevos campos además de los existentes (que siguen intactos):

```json
{
  "city": "Tokyo",
  "...": "campos existentes (readiness_score, decision, state_label, etc.) sin cambios",
  "gate_a": {
    "state": "clean",
    "label": "Limpio",
    "badge": "good",
    "detail": "12 trades, WR 58.3%, PnL +$2.10"
  },
  "gate_b": {
    "state": "ready",
    "label": "Lista",
    "badge": "good",
    "detail": "4 edges, 2 ciclos, pico 28.3%"
  },
  "gate_c": {
    "state": "partial",
    "label": "Parcial",
    "badge": "warn",
    "detail": "3/5 casos NOAA"
  },
  "gates_summary": "A clean · B ready · C partial"
}
```

### Valores posibles por gate

**`gate_a` — historial real (trades cerrados de v10.6)**

| `state` | `label` | `badge` | Cuándo dispara |
|---|---|---|---|
| `clean` | `Limpio` | `good` | `trades > 0` y no flagged como malo/degradado/bloqueado |
| `bad` | `Malo` | `bad` | `history_bad` ∨ `degraded` ∨ `blocked` ∨ `removable_active` |
| `no_data` | `Sin datos` | `muted` | `trades == 0` |

**`gate_b` — shadow signal (direccional)**

| `state` | `label` | `badge` | Cuándo dispara |
|---|---|---|---|
| `ready` | `Lista` | `good` | `promotable_shadow` (cumple los 4 criterios canary) |
| `building` | `Construyendo` | `accent` | `shadow_seen > 0` ∨ `shadow_edges > 0` ∨ `shadow_cycles > 0`, pero no `ready` |
| `empty` | `Vacío` | `muted` | sin actividad shadow |

**`gate_c` — NOAA observed proxy**

| `state` | `label` | `badge` | Cuándo dispara |
|---|---|---|---|
| `interpretable` | `Interpretable` | `good` | `observed_count >= OBSERVED_FORECAST_MIN_SAMPLE` y configurado |
| `partial` | `Parcial` | `warn` | `noaa_configured` y `observed_count > 0`, pero sin muestra suficiente |
| `none` | `Sin NOAA` | `muted` | no configurado o `observed_count == 0` |

### `gates_summary` (string de conveniencia)

Un string one-liner con el formato exacto:
```
"A {gate_a.state} · B {gate_b.state} · C {gate_c.state}"
```
Útil para logs, tooltips y glosarios inline. Codex lo puede ignorar si usa los tres objetos directamente.

### `detail` por gate (string human-readable con números)

Siempre presente, nunca `null`. Ejemplos exactos que Codex puede asumir:

- `gate_a.detail`:
  - `clean`: `"12 trades, WR 58.3%, PnL +$2.10"`
  - `bad`: razón real (`"regla de salida disparada: 24 trades, WR 8.3% y PnL -$0.24"` o similar)
  - `no_data`: `"sin trades reales"`
- `gate_b.detail`:
  - `ready`: `"4 edges, 2 ciclos, pico 28.3%"`
  - `building`: `"2 edges, 1 ciclo, pico 18.0%"` (solo valores no-cero; faltan X para canary)
  - `empty`: `"sin actividad shadow"`
- `gate_c.detail`:
  - `interpretable`: `"12 casos NOAA"`
  - `partial`: `"3/5 casos NOAA"`
  - `none`: `"sin NOAA configurado"` o `"NOAA sin muestra"`

Codex puede renderizar `detail` como tooltip o como texto secundario bajo el chip, lo que quede mejor en el layout.

---

## Qué NO cambia (garantía de backwards compat)

- Todos los campos existentes de `ranking_rows` se mantienen: `readiness_score`, `decision`, `decision_label`, `badge`, `state_label`, `priority_group`, `priority_label`, `trend_label`, `distance_label`, `main_reason`, `trades`, `win_rate`, `pnl`, `shadow_edges`, etc.
- El orden de las filas (`_sort`) no cambia — sigue usando `priority_group` y `readiness_score` como clave primaria.
- `readiness_score` pasa a ser un campo **auxiliar** (se usa para ordenar), no se muestra como display primario.
- `build_dashboard_city_observation` no se toca.

---

## Frontend (responsabilidad de Codex)

### Dónde renderizar

**En `templates/dashboard.html`, dentro de Bloque 3 (`Salud del sistema`, `<details>` colapsable).**

Reemplazar el bloque actual `{# -- City states compact -- #}` (líneas ~337-354, el que itera `dashboard.city_observation.active_rows`) por una tabla compacta que itere `dashboard.city_decisions.ranking_rows` con las 3 columnas de gates. Razón: la nueva tabla es superset — `gate_c` cubre lo que hoy muestra el bloque viejo (NOAA readiness), y además añade historial y shadow.

**Mantener** el bloque de `blocked_rows` posterior (líneas ~356-373): sigue siendo útil para ver ciudades expulsadas.

### Estructura sugerida de la nueva tabla

```html
<div class="card-head">
  <div>
    <p class="section-kicker">Ciudades</p>
    <h2>Ranking de ciudades</h2>
  </div>
  <span class="badge badge-accent">{{ dashboard.city_decisions.ranking_rows|length }} seguidas</span>
</div>

<div class="table-wrap">
  <table class="city-gates">
    <thead>
      <tr>
        <th>Ciudad</th>
        <th>Historial</th>
        <th>Shadow</th>
        <th>NOAA</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      {% for row in dashboard.city_decisions.ranking_rows %}
      <tr>
        <td><strong>{{ row.city }}</strong></td>
        <td>
          <span class="badge badge-{{ row.gate_a.badge }}" title="{{ row.gate_a.detail }}">
            {{ row.gate_a.label }}
          </span>
        </td>
        <td>
          <span class="badge badge-{{ row.gate_b.badge }}" title="{{ row.gate_b.detail }}">
            {{ row.gate_b.label }}
          </span>
        </td>
        <td>
          <span class="badge badge-{{ row.gate_c.badge }}" title="{{ row.gate_c.detail }}">
            {{ row.gate_c.label }}
          </span>
        </td>
        <td><span class="badge badge-{{ row.state_badge }}">{{ row.state_label }}</span></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

Esto es una **sugerencia estructural**, no un mandato literal. Codex puede reorganizar si tiene mejor criterio UX, mientras cumpla estas condiciones:
- Usa `ranking_rows` (ya viene ordenado correctamente).
- Muestra los 3 gates con sus `label` y `badge` correspondientes.
- El `detail` está disponible como tooltip o subtexto.
- Conserva la columna de `state_label` con su `state_badge` actual.

### Glosario (obligatorio)

Debajo de la tabla, un bloque `notice notice-muted` con el glosario corto de los estados. Texto sugerido:

```
Historial: Limpio (trades sanos) · Malo (WR/PnL bajos) · Sin datos (sin cierres).
Shadow: Lista (cumple regla canary) · Construyendo (acumulando señales) · Vacío (sin actividad).
NOAA: Interpretable (muestra suficiente) · Parcial (en acumulación) · Sin NOAA (no configurado o vacío).
```

### CSS

Reutilizar las clases `badge badge-good|accent|warn|bad|muted` existentes en `static/dashboard.css`. Si hace falta una clase nueva para el layout de la tabla (`.city-gates`, por ejemplo para ajustar anchos de columna), añadirla al final del CSS. Nada de tocar clases existentes.

---

## Verificación al cierre (ambas tareas)

**Claude (backend):**
- `python -c "import ast; ast.parse(open('bot.py', encoding='utf-8').read())"` → syntax OK
- `python verify_before_deploy.py` → pasa en verde con al menos 534 tests (target: 540+ tras añadir tests de los 3 gates)
- Tests nuevos obligatorios en `verify_before_deploy.py`:
  1. `gate_a == "clean"` para ciudad con `trades>0` y `pnl>=0` y sin flags
  2. `gate_a == "bad"` para ciudad con `history_bad=True`
  3. `gate_a == "no_data"` para ciudad con `trades==0`
  4. `gate_b == "ready"` para ciudad con `promotable_shadow=True`
  5. `gate_b == "building"` para ciudad con `shadow_edges>0` pero no ready
  6. `gate_b == "empty"` para ciudad sin actividad shadow
  7. `gate_c == "interpretable"` para ciudad con `interpretable=True`
  8. `gate_c == "partial"` para ciudad con NOAA configurado pero `observed_count<goal`
  9. `gate_c == "none"` para ciudad sin NOAA

**Codex (frontend):**
- El template renderiza sin error con `tools/preview_dashboard.py` (si aplica) o con un mock de `dashboard.city_decisions.ranking_rows`
- Las 3 columnas de gates aparecen con badges de color correctos
- Tooltips (`title` HTML) exponen el `detail`
- El glosario aparece debajo de la tabla
- El bloque viejo `city_observation.active_rows` queda eliminado (y su CSS si tiene selectores huérfanos)
- `verify_before_deploy.py` sigue en verde (los tests del template si existen)

---

## Merge order

1. Claude commitea y pushea backend primero (aunque el frontend aún no use los campos, el JSON ya los expone y no rompe nada).
2. Codex hace `git pull`, commitea y pushea frontend.
3. Verificación conjunta en preview local antes del deploy a Railway.

Si Codex termina primero: el frontend puede commitearse contra un stub manual (ejemplo de fila `ranking_rows` con los campos nuevos inyectados en el preview) y hacer merge después del backend sin conflicto.

---

## Out of scope para R1

- No tocar la lógica de `readiness_score` (sigue calculándose y sigue ordenando).
- No tocar `build_dashboard_city_observation` ni las `active_rows` que consumen otros bloques del template.
- No cambiar thresholds de `SHADOW_CANARY_MIN_*` ni `ALLOWLIST_REMOVE_MIN_*`.
- No tocar la regla `_is_shadow_only` ni el override del ciclo 16:00 UTC (eso es c8c8e73 del mismo día, sesión paralela).
- No hacer bump de versión (v10.6.11 se mantiene hasta que haya feature user-facing que lo amerite).
