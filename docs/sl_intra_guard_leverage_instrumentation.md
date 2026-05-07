# SL_intra Guard Leverage Instrumentation

**Documento:** `docs/sl_intra_guard_leverage_instrumentation.md`
**Fecha:** 2026-05-07
**Clasificación:** DOCUMENTATION / WATCH_RISK
**Estado:** PRE-REQUISITO LOG_ONLY — no implementado en runtime

---

## 1. Objetivo

Este documento define el campo `sl_window_catchable` y sus campos relacionados, para usarlos en futuras auditorías y en el futuro `SL_intra Guard Evidence Ledger` (LOG_ONLY). El campo ayuda a separar skip events del guard SL_intra exact+days≤1 donde el guard tenía **leverage real** de casos donde la pérdida ya era **heredada** y no es justo usarlos para medir el mérito o daño del guard.

---

## 2. Problema que resuelve

Sin `sl_window_catchable`, el análisis de la alarma A8 mezcla dos poblaciones distintas:

1. **Leverage-real:** el guard skipea una venta cuando el trade aún puede recuperarse — o empeorar — de forma atribuible al guard. El resultado final es evidencia válida para medir si el guard ayudó o perjudicó.

2. **Inherited loss:** el skip ocurre cuando el trade ya está tan deteriorado que ninguna decisión razonable del guard hubiera cambiado el resultado. Incluir estos casos distorsiona `WR_leverage_real` y puede llevar a conclusiones incorrectas.

Ejemplos observados:

- **Munich (leverage-real):** Entry ≈ $0.60 → cae a $0.20 (−65.8%) → guard skip (condition=exact, days_ahead=0) → recupera a +67.98%. *Caso borderline: deterioro profundo pero resultado positivo. Clasificación puede ser `sl_window_catchable=false` por umbral o `true` si el análisis futuro revisa el umbral.*
- **Caso heredado:** el skip ocurre sobre un trade cuya pérdida acumulada ya supera −35% al momento del skip. El outcome final no es evidencia limpia del guard.

---

## 3. Definición del campo

| Atributo | Valor |
|----------|-------|
| **Nombre** | `sl_window_catchable` |
| **Tipo** | `boolean` (o `null` si datos insuficientes) |
| **Contexto** | Skip event del guard SL_intra con `condition=exact` y `days_ahead≤1` |

### Semántica

- **`true`**: el skip ocurrió dentro de una ventana donde el SL todavía habría podido actuar de forma razonablemente comparable. El resultado final de este trade puede usarse como evidencia para `WR_leverage_real`.
- **`false`**: el skip ocurrió cuando el deterioro ya era demasiado profundo al momento del skip. Debe clasificarse como `inherited_loss`. **No debe contribuir a `WR_leverage_real`.**
- **`null`**: datos insuficientes (ver Sección 7, Casos borde).

---

## 4. Criterio inicial (observacional)

```
sl_window_catchable = true   si pct_pnl_at_skip > -35%
sl_window_catchable = false  si pct_pnl_at_skip <= -35%
```

> **Importante:** este umbral (`-35%`) es observacional y revisable. No cambia ejecución. No vende. No bloquea. No altera el guard SL_intra ni ningún otro componente del bot. Es exclusivamente una herramienta de análisis post-hoc.

El umbral puede ajustarse en futuras auditorías A8. Cuando se ajuste, debe registrarse la versión anterior y el razonamiento en el ledger (ver Sección 9).

---

## 5. Campos del schema

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
| `sl_window_catchable` | boolean / null | Campo definido en este documento |
| `sl_window_catchable_reason` | string | Explicación textual de la clasificación |
| `sl_window_catchable_threshold` | float | Umbral usado para la clasificación (ej. `-0.35`) |
| `schema_version` | string | Versión del schema del ledger |

---

## 6. Uso previsto

Este campo se consume en los siguientes contextos, todos **read-only / LOG_ONLY**:

- **Auditoría A8** (`WATCH / ESPERAR_MÁS_MUESTRA`): filtrar la cohorte para calcular `WR_leverage_real` excluyendo `inherited_loss`.
- **Re-check A8 del 2026-05-21** (o al alcanzar el 5.º guarded event): usar `sl_window_catchable` para separar poblaciones antes de emitir veredicto.
- **Futuro SL_intra Guard Evidence Ledger** (`docs/sl_intra_guard_evidence_ledger_design.md`): consume este campo para calcular las métricas de la Sección 9.

---

## 7. Casos borde

| Situación | Comportamiento esperado |
|-----------|------------------------|
| `pct_pnl_at_skip` faltante o nulo | `sl_window_catchable = null`, `sl_window_catchable_reason = "pct_pnl_at_skip_missing"` |
| Skip duplicado (mismo token_id + ts_skip) | Idempotencia: no insertar segundo registro; mantener el primero |
| Trade no resuelto al calcular métricas | No calcular `verdict` final; marcar `outcome = pending` |
| Fuente de datos incompleta | No fallar — marcar `sl_window_catchable = null`, `sl_window_catchable_reason = "incomplete_source"` |
| Umbral revisado entre versiones | Registrar ambas clasificaciones con `sl_window_catchable_threshold` explícito |

---

## 8. Uso prohibido

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

## 9. Relación con el futuro Evidence Ledger

El documento `docs/sl_intra_guard_evidence_ledger_design.md` (pendiente de diseño Opus) consumirá `sl_window_catchable` para calcular las siguientes métricas agregadas:

| Métrica | Descripción |
|---------|-------------|
| `n_leverage_real` | Número de skip events con `sl_window_catchable=true` y outcome resuelto |
| `n_inherited` | Número de skip events con `sl_window_catchable=false` (excluidos de WR) |
| `WR_leverage_real` | Win rate sobre la cohorte leverage-real únicamente |
| `guard_delta` | Diferencia de outcome entre cohorte leverage-real y baseline sin guard |
| `verdict_global` | Veredicto consolidado A8 (`GUARD_HELPS` / `GUARD_HURTS` / `INCONCLUSIVE` / `INSUFFICIENT_SAMPLE`) |

El ledger calculará estas métricas en modo LOG_ONLY y solo informará a auditorías humanas. No modificará el comportamiento del bot.

---

## 10. Guardrails de implementación futura

Cuando Codex implemente el campo en el skip event runtime:

- **No tocar** `bot.py` más allá del campo de logging
- **No tocar** `tools/`
- **No tocar** scheduler, NOAA, reglas de entrada/salida
- **No tocar** Railway ni env vars
- **No tocar** DB directamente (solo escribir vía logger existente)
- **No tocar** BANKROLL ni Fase C
- El campo debe ser **additive-only**: no puede reemplazar ni modificar campos existentes del skip event
- El campo debe estar gated tras `LOG_ONLY` / feature flag, nunca activo por defecto en ejecución

---

## 11. Estado actual

- `sl_window_catchable`: **documentado, no implementado en runtime**
- `SL_intra Guard Evidence Ledger`: **no diseñado** (requiere Opus)
- A8 estado: `WATCH / ESPERAR_MÁS_MUESTRA` (n=2 leverage-real; re-check 5.º guarded o 2026-05-21)
- Próximo paso: Codex patch mínimo para añadir `sl_window_catchable` al skip event runtime (LOG_ONLY), o Opus diseña el ledger si el campo ya existe

---

*Documento creado en Sesión 315 (2026-05-07, Sonnet 4.6). Pre-requisito del futuro `docs/sl_intra_guard_evidence_ledger_design.md`.*
