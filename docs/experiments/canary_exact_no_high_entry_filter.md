# Experimento: `canary_exact_no_high_entry_filter`

- **Estado:** DISEÑO (no implementado)
- **Modo:** LOG_ONLY
- **Origen:** veredicto Opus 2026-05-17 (`CANARY_EXACT_NO_RISK_FILTER`).
- **Autor del diseño:** Sonnet 2026-05-17.
- **Implementación futura:** Codex (hook LOG_ONLY, commit local sin push, patrón `unsellable_liquidity_guard_v1`).

## 1. Hipótesis

En el segmento canary, las entradas `exact + NO + entry_price >= 0.60` tienden a perder dinero a pesar del edge nominal porque:

- el precio alto implica que el mercado ya descuenta el evento (poco margen residual),
- en `exact` (rango cerrado del forecast), una desviación pequeña del observado tira la posición a 0,
- los `winners` recientes (Munich, Milan) operan en su mayoría en franja `entry_price < 0.60`,
- los `losers` repetidos (Seoul, Singapore, Shanghai en `exact`) suelen aparecer con precio alto y `days_ahead` cortos.

Si la hipótesis es cierta, marcar esta cohorte permitirá decidir, en una iteración futura, bloquearla sin bloquear los winners actuales.

## 2. Trigger exacto

Se marca la operación en el momento de la decisión de entry si y solo si **todas** las condiciones se cumplen:

| Condición | Valor |
|-----------|-------|
| `condition` | `exact` |
| `side` | `NO` |
| `entry_price` | `>= 0.60` |
| `city_mode` | `canary` (no `active`, no `shadow`, no `blocked`) |

Cualquier otra combinación queda fuera del flag.

## 3. Qué hace LOG_ONLY

- Emite un registro en el log/lifecycle con el flag `experiment_flags.canary_exact_no_high_entry = true`.
- Conserva el trazo del trigger (precio, ciudad, edge, days_ahead, cycle_number, version).
- Permite cosechar la cohorte luego sin reinterpretar logs.

## 4. Qué NO hace LOG_ONLY

- **No bloquea** la entrada.
- **No** modifica `BUY/SELL/SKIP`.
- **No** altera sizing, bankroll, edge, ni cierre.
- **No** toca el scheduler ni el bot core.
- **No** afecta SL_intra, Truth Pipeline, Fase C, ni city modes.
- **No** modifica env vars de trading.
- **No** escribe en DB de trading; sólo añade un campo en el lifecycle / skip_log existente.

## 5. Cohortes

### 5.1 Cohorte marcada (treatment)

Operaciones que en el momento de la decisión cumplen el trigger.

### 5.2 Cohorte control

Operaciones canary + `NO` + `exact` con `entry_price < 0.60` cerradas en la misma ventana. No requiere flag; se reconstruye desde lifecycle.

## 6. Métricas

Para cada cohorte se reporta:

- `n` (operaciones cerradas dentro de la ventana)
- `WR` (% con `pnl_cash > 0`)
- `PnL total` y `PnL medio`
- **Micro residual / unsellable**: cantidad de operaciones con shares > 0 al cierre o con liquidez insuficiente (cruce con `unsellable_liquidity_guard` o `close_subtype` indicativo de residual)
- **City breakdown**: `n`, `WR`, `PnL` por ciudad
- Distribución de `entry_price` y `days_ahead` dentro de la cohorte marcada

## 7. Criterios de decisión

| Resultado | Condición |
|-----------|-----------|
| **Éxito** (cohorte sangra de verdad) | `marked.WR <= 35%` **y** `marked.PnL <= -$0.50` **y** `marked.n >= 10` **y** `control.WR > 50%` |
| **Fracaso** (no hay señal) | `marked.WR >= 50%` **o** `marked.n < 5` al cierre de la ventana |
| **Inconcluso** | `n` entre 5 y 9, o `WR` entre 35% y 50% con `n >= 10` → **no se extiende automáticamente**; requiere nueva decisión humana |

## 8. Ventana de observación

- **Inicio:** 2026-05-18
- **Cierre:** 2026-06-14 (4 semanas)
- **Cierre anticipado:** si `marked.n >= 10` antes de 2026-06-14, se cierra y se aplican los criterios de §7.
- **Si al cierre `marked.n < 5`:** **fracaso por muestra insuficiente** → archivar el experimento sin conclusiones.
- **Si al cierre `marked.n` entre 5 y 9:** **inconcluso**; **no** se extiende automáticamente — requiere nueva decisión humana para prorrogar, archivar, o re-diseñar el trigger.
- **Si al cierre `marked.n >= 10`:** aplicar los criterios de éxito/fracaso definidos en §7.

## 9. Criterios de parada / abort

- Si Opus reclasifica la palanca semana siguiente (ej. cambia a `BANKROLL` o `Fase C`), el experimento se pausa pero no se elimina.
- Si se detecta que el flag está mutando el sizing o el trading core (regresión), **abort inmediato** y rollback del hook.
- Si la cohorte control colapsa (`control.WR <= 35%`), invalidar el experimento: el problema no es entry_price sino el segmento entero.
- Si en cualquier momento se descubre un bug en cómo se calcula `entry_price` (snapshot vs realizado) que afecta a >20% de la cohorte, abort.

## 10. Calibración retroactiva (read-only, ventana 4 semanas)

**Fuente:** `data/runtime_import/trade_lifecycle.json` + `data/runtime_import/postmortem.json` + `data/runtime_import/city_policy_state.json` (snapshot 2026-05-13).

**Ventana:** trades cerrados con `opened_at >= 2026-04-15` (≈ 4 semanas previas a la decisión).

**Definición operativa de `city_mode = canary`:** la ciudad estaba en `auto_canary_cities` al momento de `opened_at`. Si no se conserva history granular, se usa la mejor aproximación (`promoted_at <= opened_at`).

**Resultados de calibración (4 semanas, 2026-04-15 → 2026-05-13):**

| Cohorte | n | WR | PnL total | Top ciudades |
|---------|---|----|-----------|--------------|
| canary + NO + exact (universo) | 25 | 52% | -$0.78 | Munich(5), Shanghai(5), Paris(4), Seoul(3) |
| **MARKED** (entry_price ≥ 0.60) | **7** | **57.1%** | **-$2.08** | Seoul(3), Shanghai(2), Munich(1), Tokyo(1) |
| **CONTROL** (entry_price < 0.60) | 17 | 47.1% | +$0.13 | Paris(4), Munich(4), Shanghai(4), Singapore(2), Wellington(1), Milan(1), Tokyo(1) |

**Lectura:**

- **n esperado en 2 semanas: ~3-4** (proyección lineal). Insuficiente para `n >= 10`.
- WR de la cohorte marcada (57.1%) **no** cumple el criterio de éxito (≤35%), pero su PnL **sí** apunta en la dirección de la hipótesis (-$2.08 vs control +$0.13, gap ≈ $2.20 en 4 semanas).
- Seoul (3 de 7 marcados) domina la cohorte marcada y es la ciudad con peor balance ($0.32 − $2.34 − $2.41 = -$4.43).
- La cohorte control no muestra colapso (WR 47%, PnL ligeramente positivo), lo que mantiene el experimento válido.

**Sesgo conocido:** la calibración asume que las ciudades canary actuales lo eran al momento del trade, lo cual es razonable para promociones `<= 2026-04-15` pero podría sobre-incluir trades anteriores a su promoción para `Austin`, `Madrid`, `Singapore`, `Toronto` (promoted ≥ 2026-05-05). El impacto cuantitativo es bajo (estas 4 ciudades aportan 2 de 25 trades en el universo).

## 11. Recomendación de ventana

**4 semanas (2026-05-18 → 2026-06-14) desde el inicio.**

Razones:

1. La calibración retroactiva muestra que `n` proyectado a 2 semanas es ~3-4, por debajo del umbral `n >= 5` para evitar "fracaso por baja muestra".
2. A 4 semanas la proyección es ~7, cerca pero aún por debajo de `n >= 10`. Mejor declarar la ventana completa desde el inicio que arrancar a 2 semanas y forzar prórroga.
3. El criterio `n >= 10` se mantiene como gate de éxito; si llega antes (acumulación de exact+NO en Seoul/Shanghai), el experimento puede cerrar antes.
4. Si al cierre la muestra es 5-9 (inconcluso), **no se extiende automáticamente**: requiere decisión humana explícita.

## 12. Guardrails

- LOG_ONLY: no toca trading, sizing, edge, bankroll, ni SL.
- No env vars de trading.
- No DB writes fuera del registro lifecycle/skip_log existente.
- No cambia city modes.
- No cambia scheduler.
- Compatible con: shadow mode, auto-canary, SL_intra v10.6.40 guard, unsellable liquidity guard v1.
- No depende de Fase C ni Truth Pipeline.

## 13. Tarea futura para Codex (no en este turno)

1. Implementar hook LOG_ONLY: `experiment_flags.canary_exact_no_high_entry` poblado en `entry_context` (o equivalente) cuando se cumple el trigger.
2. Patch local commit, **sin push**. Patrón de revisión: Pablo aprueba antes de push (ver `unsellable_liquidity_guard_v1_design`).
3. Asegurar que el flag se persiste en `trade_lifecycle.json` para reconciliación posterior.
4. Añadir test ligero que verifique:
   - el flag se setea solo cuando se cumplen las 4 condiciones,
   - el flag **no** bloquea entries (assert que el código sigue al path BUY).
5. No tocar SL, sizing, ni post-exit pipelines.

## 14. Referencias

- Decisión Opus 2026-05-17: `decision_canary_exact_no_filter_2026_05_17`
- Patrón de patch local sin push: `unsellable_liquidity_guard_v1_design`
- SL_intra guard activo: `session_254_sl_intra_guard_v10_6_40`, `a8_sl_intra_verdict_2026_05_07`
- Matriz lean: `lean_alarm_matrix_v1_design_2026_05_07`
