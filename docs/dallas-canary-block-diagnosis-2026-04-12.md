# Dallas no se auto-promovió a canary

Fecha de auditoría: 2026-04-12

Fuentes usadas:
- `data/runtime_import/shadow_city_tracking.json`
- `data/runtime_import/city_policy_state.json`
- `data/runtime_policy_effective_view.json`
- `data/runtime_import/cycles_history.jsonl`
- `bot.py`

## Respuesta corta

No está bloqueada por falta real de evidencia reciente.

Tampoco la explica `CITY_STATS_CUTOFF`.

Con el snapshot actual, Dallas sigue teniendo evidencia shadow suficiente para canary (`edge_hits=8`, `cycles_seen=5`, `best_edge_pct=45.8`, `support_count >= 5`) y `CITY_STATS_CUTOFF` no participa en la regla de promoción `shadow -> canary` de `build_dashboard_city_decisions()`.

El bloqueo real es otro: Dallas sigue persistida en `auto_shadow_cities` desde la degradación del `2026-04-06T07:21:54Z`, y el estado runtime actual no refleja una re-promoción posterior aunque la evidencia shadow ya volvió a cumplir la regla. Eso apunta a un problema de estado/overlay o de re-evaluación efectiva, no a una falta de edges recientes.

## 1. Valores reales de Dallas en `shadow_city_tracking.json`

Snapshot actual (`data/runtime_import/shadow_city_tracking.json`):

| Campo | Valor |
|------|------:|
| `markets_seen` | 9 |
| `edge_hits` | 8 |
| `cycles_seen` | 5 |
| `best_edge_pct` | 45.8 |
| `first_seen_at` | `2026-04-02T10:59:19Z` |
| `last_seen_at` | `2026-04-08T08:00:36Z` |
| `last_date` | `2026-04-08` |
| `last_side` | `FILTERED` |

Detalle útil:
- Los edges direccionales fuertes están concentrados en `2026-04-02` a `2026-04-04`.
- El último registro (`2026-04-08`) no es un edge nuevo; es una observación `FILTERED`.

## 2. Cómo usa `bot.py` el cutoff en esta decisión

Hallazgos de código:

1. `CITY_STATS_CUTOFF` se parsea desde env en `bot.py:143-152`.
2. El cutoff solo se usa en:
   - `get_city_accuracy()` (`bot.py:3353-3381`)
   - `get_city_policy_metrics()` (`bot.py:3384-3438`)
3. En ambos casos, el efecto es excluir trades cerrados antes del cutoff de las métricas por ciudad.

Eso alimenta métricas de histórico y auto-shadow, pero no recorta directamente el shadow tracker.

La regla de promoción en `build_dashboard_city_decisions()` (`bot.py:5456-6112`) usa:
- `shadow_edges` desde `shadow_city_tracking`
- `shadow_cycles` desde `shadow_city_tracking`
- `shadow_best_edge` desde `shadow_city_tracking`
- `support_count = max(observed_count, trades, shadow_cycles)` (`bot.py:5580`)

La condición exacta es (`bot.py:5581-5585`):
- `shadow_edges >= SHADOW_CANARY_MIN_EDGE_HITS`
- `shadow_cycles >= SHADOW_CANARY_MIN_CYCLES`
- `shadow_best_edge >= SHADOW_CANARY_MIN_BEST_EDGE`
- `support_count >= SHADOW_CANARY_MIN_SUPPORT`

Con los thresholds actuales:

| Threshold | Valor |
|------|------:|
| `SHADOW_CANARY_MIN_EDGE_HITS` | 2 |
| `SHADOW_CANARY_MIN_CYCLES` | 2 |
| `SHADOW_CANARY_MIN_BEST_EDGE` | 15.0 |
| `SHADOW_CANARY_MIN_SUPPORT` | 2 |

Dallas pasa todos, incluso si `CITY_STATS_CUTOFF` dejara `trades=0`, porque `support_count` seguiría siendo al menos `shadow_cycles=5`.

## 3. Qué explica de verdad el bloqueo

`city_policy_state.json` muestra esta secuencia:

- `2026-04-06T07:20:18Z`: Dallas pasa de `shadow` a `canary`
- `2026-04-06T07:21:54Z`: Dallas pasa de `active` a `shadow` por auto-shadow

La metadata persistida actual sigue siendo:

| Overlay actual | Valor |
|------|------|
| `auto_shadow_cities.Dallas.action` | `auto_shadow` |
| `from_mode` | `active` |
| `reason` | `regla de salida disparada: 17 trades, WR 11.8% y PnL $-1.60` |
| `shadow_best_edge` | 45.8 |
| `shadow_edges` | 8 |
| `support_count` | 17 |

Y la vista efectiva runtime actual deja a Dallas en:

| Campo | Valor |
|------|------|
| `env_declared_mode` | `shadow` |
| `runtime_policy_mode` | `auto_shadow` |
| `effective_mode` | `shadow` |
| `source_of_truth` | `city_policy_state.auto_shadow_cities` |

Eso descarta dos hipótesis:

1. No está frenada por seguir en `ACTIVE_TRADING_CITIES`.
   `data/runtime_policy_effective_view.json` ya la deja como `env=shadow`.

2. No está frenada por falta de edges recientes bajo cutoff.
   El shadow tracker vigente ya contiene suficiente evidencia para re-promoverla.

La inferencia más fuerte desde fuente + estado actual es esta:

- Dallas quedó degradada a `auto_shadow` por histórico malo.
- Después volvió a acumular evidencia shadow suficiente.
- Pero el overlay persistido no terminó reflejando una re-promoción posterior.

Eso es compatible con bug o inconsistencia de state-sync/overlay, no con “todavía no reunió evidencia post-cutoff”.

## 4. Corrección mínima

## Lo que no arregla el problema de raíz

- Quitar `CITY_STATS_CUTOFF=Dallas=2026-04-06` no explica ni corrige este caso.
- Esperar edges nuevos post-cutoff tampoco parece la respuesta correcta, porque Dallas ya cumple hoy la regla shadow -> canary con evidencia posterior visible en `shadow_city_tracking`.

## Corrección mínima más plausible

La corrección mínima conceptual no es tocar el cutoff, sino revisar por qué Dallas permanece en `auto_shadow_cities` pese a cumplir la regla de promoción y con `env_declared_mode=shadow`.

Traducido a diagnóstico:
- el problema está en la transición/overlay persistido;
- no en los thresholds;
- no en la evidencia shadow reciente;
- no en `CITY_STATS_CUTOFF`.

## Veredicto final

Dallas no está bloqueada por falta real de evidencia reciente.

Está bloqueada por un estado persistido inconsistente con la evidencia shadow actual: sigue en `auto_shadow` aunque el snapshot vigente ya la muestra como promotable bajo la regla actual.

`CITY_STATS_CUTOFF=Dallas=2026-04-06` no explica el bloqueo actual.
