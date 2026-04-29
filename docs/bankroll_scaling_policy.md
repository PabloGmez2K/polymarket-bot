# Bankroll Scaling Policy

**Versión:** 1.0  
**Fecha:** 2026-04-29  
**Sesión:** 267  
**Estado:** vigente

---

## 1. Propósito

Este documento define la política canónica para decidir cuándo y cómo subir el bankroll del bot de trading meteorológico. El objetivo no es maximizar apuestas lo más rápido posible, sino aumentar capital solo cuando hay evidencia operativa suficiente de que el sistema es estable, los datos son trazables, y el bot ha demostrado consistencia real.

El bankroll solo es el cuello de botella cuando el sistema ya está funcionando bien. Subirlo antes de eso solo amplifica errores.

---

## 2. Principio central

**El bankroll solo se sube cuando se cumplen todas estas condiciones simultáneamente:**

- El bot está estable sin errores críticos recientes.
- Los datos son trazables y el SQLiteRecorder está activo y fresco.
- Las pérdidas recientes están dentro del umbral aceptable.
- No hay posiciones atascadas ni errores de ejecución.
- Hay evidencia estadística suficiente (n de trades y ciclos).
- La decisión es **manual y explícita**, nunca automática.

---

## 3. Estado actual

| Parámetro | Valor |
|-----------|-------|
| Bankroll experimental actual | $25 |
| Escalones futuros | $35 → $50 → $75 → $100 |
| Bankroll Readiness Score | 23.9% (etapa `early`, 2026-04-21) |
| SQLiteRecorder | Activo desde 2026-04-27 (`SQLITE_RECORDER_ENABLED=1`) |
| Fase 1 Truth Pipeline | En espera — ETA exit_code=0 aprox. 2026-05-04 |
| Fase C blocked_signals | No implementada |
| Settlement fidelity real | No implementada |

**El sistema está en fase de acumulación de datos.** No hay evidencia suficiente para subir bankroll todavía.

---

## 4. Hard blockers globales

Cualquiera de estos bloquea **toda subida de bankroll**, independientemente del nivel:

### Operativos críticos
- `tools/bot_health_check.py` reporta `ACTION` (no solo `WATCH`).
- Órdenes rechazadas por `order rejected`, `insufficient funds` o `auth failed` sin "Autenticación OK" posterior.
- `SQLiteRecorder error` repetido en logs.
- Cycle crash (excepción no controlada que interrumpe el ciclo principal).
- Pending exits atascadas (posiciones abiertas sin cierre esperado).

### Datos y trazabilidad
- `tools/phase1_readiness_check.py` con exit_code ≠ 0 cuando el nivel requiere Fase 1 activa.
- SQLiteRecorder stale (sin escritura en más de 24–48h).
- Gaps grandes en `cycles_history.jsonl` o `polymarket.db`.
- `tools/pnl_reconciliation_alert.py` reporta fallo o discrepancia no explicada.

### Pérdidas y riesgo
- Drawdown de los últimos 5 cierres por debajo de `DRAWDOWN_THRESHOLD = -$3.00`.
- Pérdida grave reciente sin postmortem documentado.
- PnL de la serie lógica actual negativo.

### Cambios de código
- Cambio reciente en trading core, NOAA, Kelly, sigma, sizing, o reglas de entrada/salida sin período de observación posterior de al menos 3–5 días de ciclos estables.

### Truth Pipeline (para niveles 3+)
- Fase 1 Truth Pipeline no diseñada ni implementada cuando el salto supera $35.
- `settlement_fidelity_status` no verificable para las ciudades activas/canary principales.

---

## 5. Soft blockers / WATCH

Estas condiciones no bloquean por sí solas, pero **requieren revisión explícita antes de subir**:

- `tools/bot_health_check.py` reporta `WATCH` por motivos no esperados (los `WATCH` esperados son: Fase 1 readiness pendiente, Tracebacks de observabilidad conocidos de `traders_intelligence_daily_summary.py` / `city-intelligence`).
- Warnings de observabilidad en Telegram (blocked_signals `WATCH`, scaling warning).
- City-intelligence con divergencias no explicadas.
- Forecast 502 aislado en un ciclo que sí completó el resto.
- `phase1_readiness_check.py` con exit_code=1 (esperando más datos) cuando aún es ETA lógico.
- `bankroll_readiness_score.py` por debajo del umbral del siguiente nivel.
- Ciudades flaggeadas críticas en el dashboard de promoción.

---

## 6. Criterios por nivel

### Nivel 1 — Mantener $25 (estado actual)

**Objetivo:** estabilizar operación, acumular datos, validar que todos los sistemas registran correctamente.

Condiciones para permanecer aquí:
- Sistema en fase experimental / acumulación de datos.
- SQLiteRecorder recién activado, ETA Fase 1 no alcanzado.
- Bankroll Readiness Score en etapa `early` o `improving`.
- Ninguna evidencia estadística suficiente para saltar.

---

### Nivel 2 — $25 → $35

**Requisitos mínimos** (todos deben cumplirse):

| Criterio | Umbral |
|----------|--------|
| `bot_health_check.py` | `OK` o `WATCH` esperado durante ≥ 5 días consecutivos |
| SQLiteRecorder | fresco, sin gaps grandes |
| `phase1_readiness_check.py` | exit_code ∈ {0, 1} — si exit_code=1, justificar que el salto no eleva riesgo más allá de prueba mínima |
| Trades limpios serie actual | ≥ 30 |
| Ciclos estables serie actual | ≥ 10 |
| PnL serie actual | ≥ $0.00 |
| Win rate serie actual | ≥ 40% |
| Drawdown últimos 5 cierres | > -$3.00 |
| Errores de ejecución recientes | 0 (`order rejected`, `insufficient funds`, `auth failed` sin OK) |
| Posiciones atascadas | 0 |
| Signals operativas | sí |
| Bankroll Readiness Score | ≥ 40% (`improving`) |
| `pnl_reconciliation_alert.py` | sin fallo |
| Tiempo desde último cambio a trading core | ≥ 3 días de observación estable |
| Decisión | manual y explícita |

**Restricción adicional:** no subir tras una sola operación ganadora, ni tras un día positivo aislado. Ver Sección 7.

---

### Nivel 3 — $35 → $50

**Más exigente que Nivel 2.** Todos los criterios del Nivel 2, más:

| Criterio | Umbral |
|----------|--------|
| `phase1_readiness_check.py` | exit_code=0 (Fase 1 activa y completa) |
| Trades limpios históricos | ≥ 30 |
| Trades limpios serie actual | ≥ 30 |
| Ciclos estables serie actual | ≥ 30 |
| PnL serie actual | ≥ $0.00 sostenido (no solo por batch `market_resolved`) |
| Win rate serie actual | ≥ 45% (provisional) |
| Drawdown últimos 5 cierres | > -$3.00 |
| Incidentes Sev1/Sev2 recientes | 0 |
| Fase 1 Truth Pipeline | diseñada o implementada parcialmente |
| Postmortems de pérdidas > $1 | documentados |
| Bankroll Readiness Score | ≥ 60% (`getting_close`) |
| Ventana de observación | ≥ 7 días sin cambios a core |

---

### Nivel 4 — $50 → $75

**Requiere madurez del Truth Pipeline.** Todos los criterios del Nivel 3, más:

| Criterio | Umbral |
|----------|--------|
| Fase 1 Truth Pipeline | operativo y produciendo datos |
| `settlement_fidelity_status` | verificable para ciudades activas/canary principales |
| PnL real (no phantom) | evidencia de edge positivo sostenido ≥ 30 días |
| Win rate verificado (NOAA) | no depender solo de WR de traders externos |
| Control de exposición | sin concentración excesiva en una sola ciudad |
| Bankroll Readiness Score | ≥ 75% (`add_capital`) |
| Ventana de observación | ≥ 14 días sin cambios a core |

---

### Nivel 5 — $75 → $100

**Solo si el sistema ha demostrado consistencia operativa y estadística robusta.** Todos los criterios del Nivel 4, más:

| Criterio | Umbral |
|----------|--------|
| Consistencia operativa | ≥ 60 días con bot estable en producción |
| Evidencia estadística | n de trades cerrados verificados ≥ 60 (provisional) |
| Drawdown máximo histórico | dentro de límites aceptables documentados |
| Replay / shadow comparison | disponible como evidencia adicional |
| Reporting y alertas | maduros — sin alertas no accionables recurrentes |
| Decisión final | revisión manual con postmortem del ciclo completo |

---

## 7. Regla anti-subida por euforia

**No subir bankroll en ninguno de estos casos:**

- Una sola compra ganadora, por alta que sea la rentabilidad.
- Una alerta de WR alto en los últimos N trades.
- Un día o semana positiva aislada.
- Para "recuperar" pérdidas recientes — esa lógica amplifica el daño.
- Inmediatamente después de un cambio de código, aunque haya pasado `verify_before_deploy.py`.
- Porque la alerta `Scaling Readiness` de Telegram lo sugiera (ver Sección 9).
- Por presión de tiempo, calendario, o ganas de acelerar el experimento.

La regla básica: **la evidencia debe ser aburrida** — ciclos consecutivos estables, sin incidentes, con una tendencia positiva lenta y sostenida.

---

## 8. Fuentes de datos para evaluar escalado

Antes de considerar cualquier subida, consultar todas estas fuentes:

| Herramienta / Archivo | Qué mide |
|-----------------------|---------|
| `tools/bot_health_check.py --data-dir data --db data/polymarket.db --markdown` | Salud general del bot: OK / WATCH / ACTION |
| `tools/phase1_readiness_check.py --db /app/data/polymarket.db --json` | Readiness Fase 1 Truth Pipeline (exit_code 0/1/2/3) |
| `tools/bankroll_readiness_score.py --data-dir data/runtime_import` | Score 0–100%, dimensiones D1–D5 |
| `tools/pnl_reconciliation_alert.py` | Reconciliación P/L bot vs wallet |
| `data/trade_lifecycle.json` | Trades abiertos/cerrados, fill prices reales |
| `data/postmortem.json` | Detalle de pérdidas relevantes |
| `data/performance.json` | PnL por trade, fill prices |
| `data/cycle_summary.json` | Último ciclo ejecutado |
| `data/cycles_history.jsonl` | Histórico de ciclos, versiones, edges por ciclo |
| `data/polymarket.db` | SQLite — ciclos, snapshots de mercado y forecast |
| `data/alerts_state.json` | Estado de alertas, flags one-shot ya disparados |

**Comandos Railway (via `tools/railway_safe.ps1`):**

```powershell
# Salud del bot en producción
railway_safe.ps1 ssh "python tools/bot_health_check.py --data-dir /app/data --db /app/data/polymarket.db --markdown"

# Phase 1 readiness
railway_safe.ps1 ssh "python tools/phase1_readiness_check.py --db /app/data/polymarket.db"

# Bankroll readiness score
railway_safe.ps1 ssh "python tools/bankroll_readiness_score.py --data-dir /app/data/runtime_import"
```

---

## 9. Relación con las alertas Telegram actuales

### `📈 Scaling Readiness`
Dispara cuando el PnL acumulado de los últimos 20 trades es positivo y `BANKROLL + scaling_pnl >= next_tier`. **No es autorización para subir bankroll.** Es una señal auxiliar que indica que la tendencia reciente es positiva. Debe interpretarse bajo todos los criterios de esta política.

### `⚠ Scaling Warning`
Dispara cuando el PnL acumulado de los últimos 20 trades es negativo. **Bloqueo informativo.** Refuerza que no se suba en ese momento.

Ambas alertas son **señales de observabilidad**, no gatillos de acción. La decisión de escalar siempre es manual.

---

## 10. Próximo paso P2 (tooling futuro)

En una sesión futura se creará una herramienta read-only `tools/bankroll_scaling_eligibility.py` que:

- Evalúa automáticamente todos los criterios de esta política para el nivel siguiente.
- Emite un output `eligible_for_manual_review: true/false` con justificación por criterio.
- Tiene anti-spam por tier (no repite la alerta si ya se emitió para ese tier).
- **Nunca sube el bankroll automáticamente.**
- No toca `bot.py`, trading core, ni variables de entorno de producción.

Esta herramienta es solo un asistente de decisión. La subida siempre requiere confirmación manual.

---

## 11. Decisión actual

Con el estado del sistema a 2026-04-29:

- **No subir bankroll.**
- SQLiteRecorder activo desde 2026-04-27, acumulando datos. ETA Fase 1: 2026-05-04 si no hay gaps.
- Bankroll Readiness Score: 23.9% (etapa `early`). PnL 30/60d negativo. WR en window 32% (debajo del umbral mínimo).
- `bot_health_check.py` operativo pero en `WATCH` esperado (Fase 1 pendiente).
- Próxima revisión cuando `phase1_readiness_check.py` retorne exit_code=0, o cuando Bankroll Readiness Score alcance ≥ 40% con PnL no negativo.

**Acción concreta:** continuar acumulando datos. Vigilar via `bot_health_check.py`. Revisitar esta política cuando la Fase 1 esté lista.

---

*Política manual. No implementa automatización. No toca código de trading.*
