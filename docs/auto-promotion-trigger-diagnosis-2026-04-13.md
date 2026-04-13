# Auto-promotion trigger diagnosis — 2026-04-13

**Sesión:** 169 (Sonnet)
**Handoff origen:** C — Diagnóstico trigger auto-promoción shadow→canary
**Tipo:** Read-only. Cero cambios en código.
**Ciudades analizadas:** Dallas, Lucknow, Sao Paulo, Istanbul

---

## 1. ¿Cuándo y cómo dispara `promotable_shadow`?

El trigger vive en `bot.py:5586-5591` dentro de `build_dashboard_city_decisions()`:

```python
promotable_shadow = (
    shadow_edges >= SHADOW_CANARY_MIN_EDGE_HITS          # default 2
    and shadow_cycles >= SHADOW_CANARY_MIN_CYCLES        # default 2
    and shadow_best_edge >= SHADOW_CANARY_MIN_BEST_EDGE  # default MIN_EDGE = 15.0
    and support_count >= SHADOW_CANARY_MIN_SUPPORT       # default 2
)
```

Donde `support_count = max(observed_count, trades, shadow_cycles)` (línea 5585).

Si `promotable_shadow = True`, la ciudad recibe `decision = "promote"` en el pipeline de decisiones (línea 5680), **pero solo si** no está bloqueada, no es activa, y no es removable_active.

La función `sync_city_policy_state()` (línea 6120) llama a `build_dashboard_city_decisions()` cada ciclo y ejecuta el cambio real. La promoción efectiva está en línea **6154**:

```python
if decision == "promote"
    and current_mode == "shadow"
    and city not in ACTIVE_TRADING_CITIES
    and city.lower() not in (globals().get("BLOCKED_CITIES") or set()):
```

Todas las condiciones deben ser verdaderas para que la ciudad entre en `auto_canary_cities`.

`sync_city_policy_state` es llamada desde `run_observability_alerts()` (línea 3872) en cada ciclo del bot.

---

## 2. Campos/archivos/flags que gatillan la lógica

En orden de precedencia:

| Campo | Fuente | Impacto |
|-------|--------|---------|
| `ACTIVE_TRADING_CITIES` | env var Railway | Si la ciudad está aquí → `city_mode = "active"` → nunca llega a `promotable_shadow` |
| `auto_shadow_cities` | `city_policy_state.json` | Fuerza `city_mode = "shadow"` PERO también bloquea `city not in ACTIVE_TRADING_CITIES` si la ciudad está en ambos |
| `tracked_cities` | calculada en `build_dashboard_city_observation` | Si la ciudad NO aparece aquí, es invisible para todo el pipeline |
| `shadow_city_tracking.cities[city]` | `shadow_city_tracking.json` en Railway volume | Provee `edge_hits, cycles_seen, best_edge_pct` para el cálculo de `promotable_shadow` |
| `OBSERVED_AUDIT_CITIES` | hardcoded en `bot.py:9832` | Vía secundaria para que ciudades entren en `tracked_cities` si no tienen trades |

---

## 3. Diagnóstico por ciudad

### Dallas — Causa raíz: `ACTIVE_TRADING_CITIES` null en Railway

**Estado:** `edge_hits=8, cycles=5, best_edge=45.8%` → pasa todos los thresholds de `promotable_shadow`.

**Por qué no promueve:**

El env var `ACTIVE_TRADING_CITIES` está en `null` en Railway (confirmado en `policy_env_snapshot.json` `pulled_at: 2026-04-13T10:42:31 UTC`). Cuando Railway no setea la variable, el código usa el default hardcoded en `bot.py:204`:

```python
ACTIVE_TRADING_CITIES = {
    city.strip()
    for city in os.getenv(
        "ACTIVE_TRADING_CITIES",
        "Chicago,Atlanta,Dallas,Buenos Aires"  # ← Dallas está aquí
    ).split(",")
    if city.strip()
}
```

Esto tiene dos efectos bloqueantes:

**Efecto 1 (post Session 166):** `get_effective_city_mode("Dallas")` devuelve `"active"` (línea 1070-1071: `if city in ACTIVE_TRADING_CITIES: return "active"`). En `build_dashboard_city_decisions`, `active = True` → el branch `elif active:` asigna `decision = "keep"` → nunca llega a `elif promotable_shadow:`.

**Efecto 2 (pre Session 166, con Dallas en auto_shadow):** aunque `get_effective_city_mode("Dallas")` devolvía `"shadow"` (porque `auto_shadow` se chequea antes que `ACTIVE_TRADING_CITIES` en la línea 1068), el gate de `sync_city_policy_state` (línea 6154) tiene `city not in ACTIVE_TRADING_CITIES` → `"Dallas" not in {"Chicago","Atlanta","Dallas","Buenos Aires"}` → **False** → no promovía.

En ambos casos, la presencia de Dallas en el default de `ACTIVE_TRADING_CITIES` es el bloqueante real. Session 166 limpió `auto_shadow_cities` pero el bloqueo original en el gate de promoción nunca fue el `auto_shadow` — siempre fue `ACTIVE_TRADING_CITIES`.

### Lucknow — Causa raíz: ciudad invisible a `tracked_cities`

**Estado:** `edge_hits=8, cycles=4, best_edge=47.4%` → pasa todos los thresholds de `promotable_shadow`.

**Por qué no promueve:**

Lucknow nunca entra en `tracked_cities` (calculado en `build_dashboard_city_observation:4904-4912`). Para aparecer en `tracked_cities`, una ciudad necesita estar en al menos uno de:

- `ACTIVE_TRADING_CITIES` → No
- `CANARY_TRADING_CITIES` → No
- `auto_canary_cities` → No
- `auto_shadow_cities` → No (vacío post Session 166; además nunca fue promovida/degradada)
- `auto_blocked_cities` → No
- `OBSERVED_AUDIT_CITIES` → **No** (Lucknow no está en esta lista hardcoded)
- `city_accuracy.keys()` → No (0 trades como ciudad shadow pura)
- Ciudades bloqueadas en `RESOLUTION_ICAO` → No

**Resultado:** Lucknow está completamente invisible para `sync_city_policy_state`. Aunque `shadow_city_tracking.json` acumula su historial correctamente, el pipeline de promoción nunca la ve.

**Causa raíz estructural:** `shadow_city_tracking` y `tracked_cities` son conjuntos desconectados. El tracking de shadow acumula datos de cualquier ciudad que el scan loop evalúe, pero el pipeline de promoción solo opera sobre ciudades que ya están formalmente "en el sistema" (en alguno de los sets/dicts anteriores).

### Sao Paulo — misma causa raíz que Lucknow

**Estado:** `edge_hits=4, cycles=8, best_edge=52.8%`.

Sao Paulo tampoco está en `OBSERVED_AUDIT_CITIES`, no tiene trades, no está en ningún auto_* dict. Es invisible a `tracked_cities`. Misma causa raíz que Lucknow: ciudad shadow pura que nunca fue formalizada.

### Istanbul — misma causa raíz que Lucknow

**Estado:** `edge_hits=5, cycles=4, best_edge=37.9%`.

Istanbul tampoco está en `OBSERVED_AUDIT_CITIES`, no tiene trades, no está en ningún auto_* dict. Invisible a `tracked_cities`. Misma causa raíz que Lucknow y Sao Paulo.

---

## 4. Hipótesis más probable

Hay dos bugs distintos, no uno:

**Bug A (Dallas):** `ACTIVE_TRADING_CITIES` env var null en Railway → código usa default "Chicago,Atlanta,Dallas,Buenos Aires" → Dallas jamás puede ser auto-promovida por la lógica shadow→canary porque el gate de promoción la excluye explícitamente (`city not in ACTIVE_TRADING_CITIES`) Y porque su `city_mode` resulta "active" (no "shadow").

**Bug B (Lucknow, Sao Paulo, Istanbul):** El pipeline de auto-promoción solo opera sobre `tracked_cities`, pero `tracked_cities` no incluye automáticamente ciudades que acumularon shadow evidence. La única forma en que una ciudad entra a `tracked_cities` sin trades ni env vars es via `OBSERVED_AUDIT_CITIES` (hardcoded) o via `auto_shadow_cities` (que solo se setea cuando una ciudad es degradada desde active/canary). Ciudades shadow puras que nunca fueron activas o canary son permanentemente invisibles.

**Hipótesis falseable:** Si se setea `ACTIVE_TRADING_CITIES=NONE` en Railway (o cualquier valor que no incluya "Dallas"), Dallas debería aparecer con `decision = "promote"` y ser promovida en el ciclo siguiente. Si no lo hace, hay un tercer bloqueante no identificado.

---

## 5. Fixes propuestos (sin aplicar — solo análisis)

### Fix A1 — Para Dallas: setear `ACTIVE_TRADING_CITIES` en Railway (cambio de política)

**Tipo:** Cambio env var Railway (no requiere código).

**Acción:** Setear `ACTIVE_TRADING_CITIES=NONE` (o vacío) para que Dallas deje de estar en la lista default. Esto hace que Dallas pase de `city_mode="active"` a `city_mode="shadow"` y que el gate de promoción no la excluya.

**Riesgo:** Dallas sería promovida automáticamente a canary en el siguiente ciclo que evalúe `sync_city_policy_state`. Esto es precisamente lo que se quiere, pero hay que tener claro que entonces el bot **operará en Dallas** (canary = opera pequeño). El historial previo (17 trades, WR 11.8%) ya estaba limpio del overlay `auto_shadow`; lo que queda en `city_policy_state.transition_history` mostrará el ciclo completo (shadow→canary→shadow→canary) pero no debería impedir la nueva operación. El riesgo real es si la exit rule de performance (ALLOWLIST_REMOVE) dispara de nuevo. Pero esos 17 trades son pre-shadow y el cutoff ya existe; con trades=0 NOAA-verificados, la exit rule no tiene base suficiente para disparar.

**Riesgo residual:** Si `ACTIVE_TRADING_CITIES` nulo está siendo usado intencionalmente como "shadow-only override" para las 4 ciudades del default (Chicago, Atlanta, Dallas, Buenos Aires), este cambio las afecta a todas. Verificar que Chicago y Atlanta están correctamente en `auto_canary` antes de tocar el env var.

### Fix B1 — Para Lucknow/Sao Paulo/Istanbul: añadirlas a `OBSERVED_AUDIT_CITIES` (cambio en código)

**Tipo:** Cambio mínimo en `bot.py:9832`.

**Acción:** Añadir "Lucknow", "Sao Paulo", "Istanbul" a `OBSERVED_AUDIT_CITIES`. Esto las agrega a `tracked_cities` en cada ciclo, lo que hace que `build_dashboard_city_decisions` las evalúe y `sync_city_policy_state` pueda promoverlas.

**Riesgo bajo:** `OBSERVED_AUDIT_CITIES` solo afecta qué ciudades se incluyen en el dashboard y el pipeline de observación. No activa trading directamente. La ciudad entraría en `tracked_cities`, `promotable_shadow` sería True para las tres (todas pasan thresholds), y serían promovidas a canary en el siguiente ciclo.

**Riesgo real:** Tres ciudades en canary simultáneamente → más throughput pero más riesgo si hay bugs de forecast no detectados. Recomendar agregarlas de a una o con un check previo de calidad de datos NOAA/forecast para cada ciudad.

### Fix B2 — Alternativa estructural: incluir `shadow_city_tracking.cities` en `tracked_cities`

**Tipo:** Cambio en `build_dashboard_city_observation` (línea 4904-4912).

**Acción:** Añadir al cálculo de `tracked_cities`:
```python
| set(shadow_cities.keys())   # shadow_cities viene de load_shadow_city_tracking()
```

**Riesgo medio-alto:** `shadow_city_tracking` puede tener docenas de ciudades con `edge_hits=0` y `cycles_seen=1`. Agregarlas todas a `tracked_cities` infla el dashboard y podría evaluar ciudades con datos incompletos o ruidosos. Requiere validar que `promotable_shadow` tenga thresholds adecuados para esas ciudades (actualmente edge_hits>=2, cycles>=2, best_edge>=15% → es un filtro razonable pero no idéntico al que se usó para las ciudades que ya están en sistema).

**Ventaja:** Fix estructural permanente; evita la necesidad de mantener `OBSERVED_AUDIT_CITIES` como lista manual.

---

## 6. Ranking de fixes por (impacto / riesgo)

| Fix | Ciudades | Impacto | Riesgo | Recomendación |
|-----|----------|---------|--------|---------------|
| A1 — Setear `ACTIVE_TRADING_CITIES` Railway | Dallas | Alto | Bajo-medio | Hacer primero, es solo env var |
| B1 — Añadir a `OBSERVED_AUDIT_CITIES` | Lucknow, Istanbul (primero) | Alto | Bajo | Segundo paso, una por una |
| B1 — Añadir a `OBSERVED_AUDIT_CITIES` | Sao Paulo | Medio | Bajo | Tercero, tras ver las dos primeras |
| B2 — Incluir shadow_tracking en tracked_cities | Todas shadow | Alto | Medio | Pendiente de decisión Opus |

**Orden recomendado para el fix Opus:** A1 primero (inmediato, solo env var, Dallas es el caso más urgente según el crosscheck). Luego B1 para Lucknow e Istanbul (similar edge_hits, cycles, best_edge). Sao Paulo con más cautela: solo 4 edge_hits pero best_edge muy alto (52.8%).

---

## TODOs residuales (detectados durante el diagnóstico, no aplicados)

1. **TODO**: Verificar si Chicago está en `auto_canary_cities` o `ACTIVE_TRADING_CITIES` antes de tocar el env var `ACTIVE_TRADING_CITIES`. Si Chicago está en el default y se setea a NONE, Chicago quedaría en shadow pura hasta acumular edge suficiente via auto-promoción.
2. **TODO**: Confirmar si `city_accuracy` incluye o no a Lucknow/Istanbul/Sao Paulo para entender si alguna ruta alternativa las traería a `tracked_cities` eventualmente.
3. **TODO**: Auditar si hay más ciudades en `shadow_city_tracking` con edge_hits >= 2 y cycles >= 2 que también estén invisibles al pipeline por la misma causa raíz de Bug B.

---

## Apéndice — Datos de soporte

**`policy_env_snapshot.json` (pulled_at: 2026-04-13T10:42:31 UTC):**
```
ACTIVE_TRADING_CITIES: null
CANARY_TRADING_CITIES: null
BLOCKED_CITIES: London,Toronto,Singapore
```

**Code default (bot.py:203-205):**
```python
ACTIVE_TRADING_CITIES = {city.strip() for city in os.getenv("ACTIVE_TRADING_CITIES","Chicago,Atlanta,Dallas,Buenos Aires").split(",") ...}
```

**`shadow_city_tracking.json` updated_at: 2026-04-13T08:00:37 UTC:**
- Dallas: edge_hits=8, cycles=5, best_edge=45.8%
- Lucknow: edge_hits=8, cycles=4, best_edge=47.4%
- Istanbul: edge_hits=5, cycles=4, best_edge=37.9%
- Sao Paulo: edge_hits=4, cycles=8, best_edge=52.8%

**`city_policy_state.json` updated_at: 2026-04-12T17:50:54 UTC:**
- `auto_shadow_cities`: `{}` (vacío — Session 166 limpió Dallas de aquí)
- `auto_canary_cities`: Atlanta, London, Munich, New York City, Seoul, Shanghai, Tokyo
