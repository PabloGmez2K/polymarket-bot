# SL_intra Guard Leverage Instrumentation

**Documento:** `docs/sl_intra_guard_leverage_instrumentation.md`
**Fecha:** 2026-05-07
**Clasificación:** DOCUMENTATION / WATCH_RISK
**Estado:** PRE-REQUISITO LOG_ONLY — no implementado en runtime

---

## 1. Objetivo

Este documento define los campos `sl_window_catchable` y `deep_drawdown_at_skip` y sus campos relacionados, para usarlos en futuras auditorías y en el futuro `SL_intra Guard Evidence Ledger` (LOG_ONLY). Los campos ayudan a separar skip events del guard SL_intra exact+days≤1 en tres cohortes distintas, evitando que el veredicto de performance del guard se contamine con casos donde la pérdida ya era estructuralmente heredada al momento del skip.

---

## 2. Problema que resuelve

Sin `sl_window_catchable` y `deep_drawdown_at_skip`, el análisis de la alarma A8 mezcla tres poblaciones distintas:

1. **Zona A — Leverage-real limpio:** el guard skipea una venta cuando el trade aún puede recuperarse — o empeorar — de forma atribuible al guard. El resultado final es evidencia válida para medir si el guard ayudó o perjudicó.

2. **Zona B — Deep drawdown borderline:** el skip ocurre cuando el deterioro es profundo (-35% a -75%) pero no definitivo. El guard pudo tener leverage real, pero la incertidumbre es mayor. No cuenta en `WR_leverage_real` principal; se analiza por separado.

3. **Zona C — Inherited loss claro:** el skip ocurre cuando el trade ya está tan deteriorado (≤-75%) que ninguna decisión razonable del guard hubiera cambiado el resultado de forma limpia. Incluir estos casos en el delta global distorsiona `WR_leverage_real` y puede llevar a conclusiones incorrectas.

**Observación de la alarma A8 (2026-05-07):** los tres casos Munich (-94.1%), Paris (-93.1%) y Wellington (-92.0%) son Zona C pura. Al incluirlos en el delta global, el mensaje "el guard está perjudicando: $-2.13" es potencialmente misleading — el guard no causó esas pérdidas, simplemente no impidió el hold-to-expiry de posiciones ya muertas.

---

## 3. Definición de los campos

### 3.1 `sl_window_catchable`

| Atributo | Valor |
|----------|-------|
| **Nombre** | `sl_window_catchable` |
| **Tipo** | `boolean` (o `null` si datos insuficientes) |
| **Contexto** | Skip event del guard SL_intra con `condition=exact` y `days_ahead≤1` |

**Semántica:**

- **`true`**: el skip ocurrió dentro de una ventana donde el SL todavía habría podido actuar de forma razonablemente comparable. El resultado final de este trade puede usarse como evidencia para `WR_leverage_real`. Corresponde a **Zona A**.
- **`false`**: el skip ocurrió cuando el deterioro ya era demasiado profundo al momento del skip. No debe contribuir a `WR_leverage_real`. Corresponde a **Zona B** o **Zona C**.
- **`null`**: datos insuficientes (ver Sección 8, Casos borde).

### 3.2 `deep_drawdown_at_skip`

| Atributo | Valor |
|----------|-------|
| **Nombre** | `deep_drawdown_at_skip` |
| **Tipo** | `boolean` (o `null` si datos insuficientes) |
| **Contexto** | Skip event con `sl_window_catchable=false` y `pct_pnl_at_skip` disponible |

**Semántica:**

- **`true`**: el skip ocurrió en Zona B (deep drawdown borderline). El guard puede haber tenido leverage real, pero el caso tiene mayor incertidumbre. No cuenta en `WR_leverage_real` principal. Sí debe conservarse en métricas separadas (`WR_deep_drawdown`, `deep_drawdown_guard_saved`, `deep_drawdown_guard_hurt`).
- **`false`**: si `sl_window_catchable=true`, este campo no aplica. Si `sl_window_catchable=false` y `pct_pnl_at_skip <= -75%`, es Zona C (inherited loss claro).
- **`null`**: `pct_pnl_at_skip` faltante o fuera de rango calculable.

---

## 4. Tres zonas de cohorte

| Zona | Nombre | Criterio `pct_pnl_at_skip` | `sl_window_catchable` | `deep_drawdown_at_skip` | Uso en métricas |
|------|--------|---------------------------|----------------------|------------------------|-----------------|
| **A** | Leverage-real limpio | `> -35%` | `true` | `false` | Cuenta en `WR_leverage_real` |
| **B** | Deep drawdown borderline | `<= -35%` y `> -75%` | `false` | `true` | Solo en `WR_deep_drawdown` / métricas separadas |
| **C** | Inherited loss claro | `<= -75%` | `false` | `false` | Excluido del veredicto de performance del guard |

### Casos ejemplo de la alarma A8 (2026-05-07)

| Caso | `pct@skip` | Zona | `sl_window_catchable` | `deep_drawdown_at_skip` | Real | Hipotético |
|------|-----------|------|----------------------|------------------------|------|------------|
| Munich No | -94.1% | **C** | false | false | -$2.26 | -$0.12 |
| Paris No | -93.1% | **C** | false | false | -$2.16 | -$0.14 |
| Wellington No | -92.0% | **C** | false | false | -$1.89 | -$0.14 |
| Munich No | -65.8% | **B** | false | true | +$1.39 | -$0.46 |
| Paris No | -29.6% | **A** | true | false | +$1.55 | -$0.38 |

**Nota sobre Munich -65.8%:** este caso no debe describirse como inherited_loss puro. Es **deep_drawdown_guard_saved / Zona B**: el guard skipea con deterioro profundo pero borderline, y el trade revierte a +67.98%. Debe conservarse como evidencia separada en métricas `WR_deep_drawdown` y `deep_drawdown_guard_saved`, no descartarse ni mezclarse con Zona C.

---

## 5. Criterio inicial (observacional)

```
sl_window_catchable = true            si pct_pnl_at_skip > -35%
sl_window_catchable = false           si pct_pnl_at_skip <= -35%

deep_drawdown_at_skip = false         si sl_window_catchable = true
deep_drawdown_at_skip = true          si sl_window_catchable = false y pct_pnl_at_skip > -75%
deep_drawdown_at_skip = false         si sl_window_catchable = false y pct_pnl_at_skip <= -75%
deep_drawdown_at_skip = null          si pct_pnl_at_skip es null o faltante
```

> **Importante:** estos umbrales (`-35%`, `-75%`) son observacionales y revisables. No cambian ejecución. No venden. No bloquean. No alteran el guard SL_intra ni ningún otro componente del bot. Son exclusivamente herramientas de análisis post-hoc.

Los umbrales pueden ajustarse en futuras auditorías A8. Cuando se ajusten, debe registrarse la versión anterior y el razonamiento en el ledger (ver Sección 10).

---

## 6. Campos del schema

Cada skip event que se registre en el futuro Evidence Ledger debe incluir estos campos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `token_id` | string | Identificador del mercado/token |
| `ts_skip` | ISO 8601 string | Timestamp del skip event |
| `pct_pnl_at_skip` | float | P&L porcentual en el momento del skip respecto a entry_price |
| `price_at_skip` | float | Precio del token al momento del skip |
| `entry_price` | float | Precio de entrada del trade |
| `condition` | string | Condición del mercado (`exact`, `range`, etc.) |
| `days_ahead` | int | Días al cierre del mercado en el momento del skip |
| `guard_version` | string | Versión del guard SL_intra activo |
| `skip_reason` | string | Razón del skip (ej. `sl_intra_exact_days_le_1`) |
| `sl_window_catchable` | boolean / null | `true` si Zona A; `false` si Zona B o C; `null` si datos insuficientes |
| `sl_window_catchable_reason` | string | Explicación textual de la clasificación |
| `sl_window_catchable_threshold` | float | Umbral Zona A usado para la clasificación (ej. `-0.35`) |
| `deep_drawdown_at_skip` | boolean / null | `true` si Zona B; `false` si Zona A o C; `null` si pct_pnl_at_skip ausente |
| `deep_drawdown_threshold_low` | float | Umbral inferior de Zona B (ej. `-0.75`) |
| `deep_drawdown_threshold_high` | float | Umbral superior de Zona B (ej. `-0.35`) |
| `cohort` | string | `zone_a` / `zone_b` / `zone_c` / `unknown` |
| `cohort_reason` | string | Explicación textual de la asignación de cohorte |
| `schema_version` | string | Versión del schema del ledger |

---

## 7. Uso previsto

Este campo se consume en los siguientes contextos, todos **read-only / LOG_ONLY**:

- **Auditoría A8** (`WATCH / ESPERAR_MÁS_MUESTRA`): filtrar la cohorte para calcular `WR_leverage_real` solo sobre Zona A; calcular `WR_deep_drawdown` sobre Zona B; excluir Zona C del veredicto principal.
- **Re-check A8 del 2026-05-21** (o al alcanzar el 5.º guarded event): usar `cohort` para separar poblaciones antes de emitir veredicto.
- **Futuro SL_intra Guard Evidence Ledger** (`docs/sl_intra_guard_evidence_ledger_design.md`): consume estos campos para calcular las métricas de la Sección 10.

---

## 8. Casos borde

| Situación | Comportamiento esperado |
|-----------|------------------------|
| `pct_pnl_at_skip` faltante o nulo | `sl_window_catchable = null`, `deep_drawdown_at_skip = null`, `cohort = "unknown"` |
| Skip duplicado (mismo token_id + ts_skip) | Idempotencia: no insertar segundo registro; mantener el primero |
| Trade no resuelto al calcular métricas | No calcular `verdict` final; marcar `outcome = pending` |
| Fuente de datos incompleta | No fallar — marcar `sl_window_catchable = null`, `cohort_reason = "incomplete_source"` |
| Umbral revisado entre versiones | Registrar ambas clasificaciones con `sl_window_catchable_threshold` y `deep_drawdown_threshold_*` explícitos |

---

## 9. Limitación actual del review one-shot

Hasta que `sl_window_catchable` y `deep_drawdown_at_skip` estén implementados en runtime, el review automático de la alarma A8 mezcla las tres cohortes.

El texto "el guard está perjudicando: $X" calculado sobre el delta global es **potencialmente misleading** cuando la muestra incluye casos Zona C. El delta global suma los tres tipos:

- Zona C (inherited loss): casos donde el guard no causó la pérdida — simplemente no pudo evitar el hold-to-expiry de posiciones ya muertas. El delta es grande y negativo, pero no atribuible al guard.
- Zona B (deep drawdown): casos borderline con incertidumbre mayor.
- Zona A (leverage-real): la única cohorte donde el delta es atribuible directamente al guard.

**El veredicto operativo debe emitirse solo sobre Zona A.** El estado actual recomendado es `WATCH_RISK`, no acción ejecutable. No cambiar guard ni env vars sin separar cohortes y revisar con Opus.

---

## 10. Copy recomendado para futuras alarmas de review

El siguiente copy conceptual debe aparecer en alarmas de review cuando la muestra incluya casos Zona B o C mezclados:

```
REVIEW PRELIMINAR — muestra mezclada.
Separar leverage-real (Zona A), deep-drawdown (Zona B) e inherited-loss (Zona C)
antes de decidir.
No cambiar guard/env vars sin revisión Opus.
```

**Este copy es solo documental.** No implementar en `bot.py`. Sirve como referencia para redactar alarmas futuras de forma que el operador no malinterprete el delta global.

---

## 11. Design gap identificado: hard floor en pct@skip

El guard actualmente puede actuar incluso cuando `pct_pnl_at_skip` está por debajo de `-75%` (Zona C). Esos casos representan posiciones casi muertas donde el guard sólo prolonga hold-to-expiry sin posibilidad razonable de recuperación.

**Posible futuro diseño:** introducir un hard floor tipo `pct_pnl_at_skip > -75%` (o `-80%`) como condición previa para que el guard pueda actuar. Si `pct_pnl_at_skip <= umbral_floor`, el guard podría permitir la venta en lugar de skipear, reduciendo la exposición a inherited loss.

**Estado actual:** no implementar. Requiere:
1. Diseño Opus explícito.
2. Evidencia adicional (mínimo n Zona C = 10 resueltos).
3. Revisión del impacto sobre Zona B antes de fijar el umbral.

No tocar `bot.py`, env vars, ni guard runtime hasta que este diseño esté aprobado.

---

## 12. Uso prohibido

Este campo y cualquier métrica derivada de él **no deben usarse para:**

- Ejecutar BUY, SELL o SKIP automático
- Modificar el guard SL_intra en runtime
- Ajustar BANKROLL
- Cambiar sizing, whitelist o city modes
- Modificar el scheduler
- Activar Fase C
- Cualquier cambio de riesgo ejecutable

El campo es exclusivamente documental y analítico.

---

## 13. Relación con el futuro Evidence Ledger

El documento `docs/sl_intra_guard_evidence_ledger_design.md` (pendiente de diseño Opus) consumirá estos campos para calcular las siguientes métricas agregadas:

| Métrica | Descripción |
|---------|-------------|
| `n_leverage_real` | Skip events con `cohort=zone_a` y outcome resuelto |
| `n_deep_drawdown` | Skip events con `cohort=zone_b` y outcome resuelto |
| `n_inherited` | Skip events con `cohort=zone_c` (excluidos del veredicto principal) |
| `WR_leverage_real` | Win rate sobre Zona A únicamente |
| `WR_deep_drawdown` | Win rate sobre Zona B (análisis separado) |
| `guard_saved_deep_drawdown` | Casos Zona B donde el guard evitó pérdida (outcome > hipotético) |
| `guard_hurt_deep_drawdown` | Casos Zona B donde el guard aumentó pérdida (outcome < hipotético) |
| `inherited_loss_excluded` | Casos Zona C excluidos del veredicto de performance |
| `guard_delta_zone_a` | Diferencia de outcome entre Zona A real vs hipotético |
| `verdict_global` | `GUARD_HELPS` / `GUARD_HURTS` / `INCONCLUSIVE` / `INSUFFICIENT_SAMPLE` — emitido solo sobre Zona A con n suficiente |

**Regla de veredicto:** `verdict_global = HOLD` si `n_leverage_real < umbral_minimo` (umbral a definir en diseño Opus). El ledger calculará estas métricas en modo LOG_ONLY y solo informará a auditorías humanas.

---

## 14. Guardrails de implementación futura

Cuando Codex implemente estos campos en el skip event runtime:

- **No tocar** `bot.py` más allá del campo de logging
- **No tocar** `tools/`
- **No tocar** scheduler, NOAA, reglas de entrada/salida
- **No tocar** Railway ni env vars
- **No tocar** DB directamente (solo escribir vía logger existente)
- **No tocar** BANKROLL ni Fase C
- Los campos deben ser **additive-only**: no pueden reemplazar ni modificar campos existentes del skip event
- Los campos deben estar gated tras `LOG_ONLY` / feature flag, nunca activos por defecto en ejecución

---

## 15. Estado actual

- `sl_window_catchable`: **documentado, no implementado en runtime**
- `deep_drawdown_at_skip`: **documentado, no implementado en runtime**
- `SL_intra Guard Evidence Ledger`: **no diseñado** (requiere Opus)
- A8 estado: `WATCH / ESPERAR_MÁS_MUESTRA` (n=2 leverage-real; re-check 5.º guarded o 2026-05-21)
- Próximo paso: Codex patch mínimo para añadir estos campos al skip event runtime (LOG_ONLY), o Opus diseña el ledger si los campos ya existen

---

*Documento creado en Sesión 315 (2026-05-07, Sonnet 4.6). Corregido en Sesión 316 (2026-05-07, Sonnet 4.6) para separar correctamente Zona A/B/C y añadir `deep_drawdown_at_skip`. Pre-requisito del futuro `docs/sl_intra_guard_evidence_ledger_design.md`.*
