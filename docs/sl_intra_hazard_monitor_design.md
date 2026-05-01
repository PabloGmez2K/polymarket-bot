# SL_intra Hazard Monitor — Diseño L2 (decisión 2026-05-01)

## Contexto de la decisión

Opus revisó el caso Wellington vs Paris tras Sesión 254 (guard SL_intra v10.6.40).

- **Paris:** posición exact+days≤1 que habría sido cortada por SL_intra; el guard la protegió correctamente y el mercado resolvió favorable. Patrón cubierto por L1 (guard activo).
- **Wellington:** posición que pasó el guard (no exact/days>1 o no en zona de riesgo del guard), pero se deterioró terminalmente sin señal visible antes del vencimiento. El guard no la cubría.

## Veredicto L0/L1 — sin cambios

- **L0 (stop-loss ejecutable):** intocable. No se modifica el mecanismo ni los umbrales.
- **L1 (guard v10.6.40):** intocable. `SL_INTRA_GUARD_DAYS_AHEAD_MAX`, `SL_INTRA_GUARD_ENABLED` y la lógica de skip quedan exactamente como están.
- Wellington no es un bug del guard: es una laguna de cobertura. El guard hace lo que prometió.

## Diagnóstico del gap

El guard actual (L1) protege contra falsas salidas tipo Paris cuando `condition=exact` y `days_ahead<=1`. Sin embargo, deja sin observación posiciones que se deterioran gradualmente sin alcanzar el trigger del SL_intra: el mercado puede pasar de precios normales a zona de pérdida terminal en horas, sin que ningún mecanismo lo note antes del vencimiento.

## Diseño L2 — Hazard Monitor (LOG_ONLY puro)

### Principio

L2 es un observador puro. No vende, no modifica lifecycle, no toca `sell_lock`, no interactúa con Unsellable Guard. Solo cataloga posiciones en tiers de riesgo creciente y deja trazas auditables.

### Scope

Posiciones bajo guard exact+days≤1 (las mismas que L1 protege de SL_intra).

### Tiers de riesgo

| Tier | Descripción |
|------|-------------|
| `deteriorating` | Precio cayendo pero sin señal de crisis inminente |
| `deep` | Pérdida significativa acumulada, posición bajo agua |
| `terminal` | Precio cerca de cero, resolución inminente desfavorable |
| `collapsed` | Precio efectivamente en cero o valor residual mínimo |

### Propiedades de diseño

- **Idempotencia:** cada entrada en el log es `(token_id, tier)`. No se duplican eventos para la misma posición en el mismo tier.
- **LOG_ONLY:** no hay acción ejecutable. El tier no desencadena ventas ni ordenes.
- **Auditoría independiente:** el monitor no requiere acceso a `bot.py` ni a los mecanismos de trading para funcionar.
- **Sin interferencia:** no toca `sell_lock`, `trade_lifecycle`, `sl_intra_guard_audit.json` ni Unsellable Guard.

### Datos a registrar por evento

```json
{
  "timestamp": "ISO-8601",
  "token_id": "...",
  "city": "...",
  "tier": "deteriorating|deep|terminal|collapsed",
  "condition": "exact|range",
  "days_ahead": 0,
  "entry_price": 0.0,
  "cur_price": 0.0,
  "pct_pnl": 0.0,
  "current_value": 0.0,
  "shares": 0,
  "bot_version": "v10.x.x"
}
```

## L3 — Reality-check ejecutable (DIFERIDO)

L3 añadiría una acción real (salida parcial o total) cuando L2 detecta `terminal` o `collapsed`. Está explícitamente diferido hasta que se cumplan ambas condiciones:

1. **14 días de observación** desde el deploy de L2.
2. **Mínimo 8 tokens resueltos** con trazas L2 en `trade_lifecycle`.

Sin ese mínimo, no hay base empírica para calibrar los umbrales de acción.

## Métrica decisiva futura

**Net P/L 30d contrafactual por tier:** comparar el P/L real de posiciones detectadas en cada tier contra el P/L hipotético si L3 hubiera actuado en el momento de la detección. Esto mide si L2/L3 añaden valor neto antes de activar cualquier acción ejecutable.

## Relación con L0/L1 (no modificados)

```
L0  stop-loss ejecutable (ciclo principal)        — intocable
L1  guard SL_intra exact+days≤1 (v10.6.40)        — intocable
L2  Hazard Monitor LOG_ONLY (este diseño)          — pendiente de implementar
L3  Reality-check ejecutable                       — diferido ≥14d + ≥8 tokens L2
```

## Estado

- **Decisión aprobada:** 2026-05-01 (Opus, Sesión 285)
- **Implementación L2:** pendiente, próxima sesión de coding
- **L3:** diferido, criterio explícito arriba
- **Variables de entorno cambiadas en esta sesión:** NINGUNA
- **Código cambiado en esta sesión:** NINGUNO
- **Deploy:** NO
