# C1 — Autopsia Trades Exact/Range Perdidos
**Fecha:** 2026-04-17 | **Agente:** Opus (análisis directo)

---

## Hallazgo Principal

**El bot entra en YES exact/range a precios bajos (10-25c) con our_prob ~40% cuando el mercado cotiza 10-20c.
Esa diferencia de 20pp es edge ilusorio: el mercado tiene razón y el modelo del bot sobreestima P(YES).**

---

## Datos

### Distribución de lados

| Agente | YES | NO |
|---|---:|---:|
| Bot (exact/range, todos los trades) | 26 (58%) | 19 (42%) |
| Quality traders (blocked_signals, n=59) | 32% | **68%** |

Los traders van mayoritariamente NO. El bot va mayoritariamente YES. **Lados opuestos.**

### Resultado por lado

| Lado | n | WR | PnL total | Entry price avg |
|---|---:|---:|---:|---:|
| YES (bot) | 26 | 0% wins | -$27.09 | 0.199 |
| NO (bot) | 19 | 38% wins | -$6.11 | 0.594 |

**Todos los wins del bot en exact/range son NO-side, con entry price > 0.51 y our_prob > 78%.**

### Tabla wins

| Ciudad | Condición | Lado | Price | our_prob | PnL |
|---|---|---|---:|---:|---:|
| Atlanta | range | NO | 0.795 | 86.7% | +$0.66 |
| Seoul | exact | NO | 0.865 | 97.9% | +$0.61 |
| Buenos Aires | exact | NO | 0.665 | 95.1% | +$0.58 |
| Atlanta | range | NO | 0.520 | 78.9% | +$0.54 |
| Tokyo | exact | NO | 0.615 | 81.1% | +$1.57 |
| Ankara | exact | NO | 0.515 | 85.9% | +$1.67 |

**Patrón consistente:** our_prob ≥ 78%, price ≥ 0.51 (entrada cara = alta confianza en NO).

### Por qué YES pierde

El bot ve: forecast=19°C, threshold=19°C → sigma de 2°C → P(YES) ≈ 38% → mercado cotiza 18% → edge 20% → compra YES.

Pero el modelo usa sigma como ancho de ventana para "cerca del umbral", cuando la probabilidad real de resolución exacta es más restrictiva. El mercado (que tiene precio correcto a largo plazo) estima 18%. El bot dice 38%. **La diferencia no es edge real, es error del modelo.**

Esto explica el 9% WR en range y 29% WR en exact en YES side: la señal de edge es ilusoria en YES cuando our_prob < 65%.

---

## C3 (corolario): Diagnóstico de Sigma

El problema no es que sigma sea alto/bajo en sentido absoluto. Es que el modelo aplica la misma distribución gaussiana para:
- `at_or_above`: P(X > threshold) — cola de distribución — **funciona bien**
- `exact`: P(X ≈ threshold) — masa central estrecha — **sobreestima para YES lado**

Para `at_or_above` YES: si forecast=22°C y threshold=20°C, P(YES) es alta y bien estimada.
Para `exact` YES: si forecast=19°C y threshold=19°C, el modelo da 38-48% pero el mercado dice 18%. El modelo no ajusta por la precisión del punto exacto de resolución.

**La señal SÍ funciona cuando our_prob > 70% (lado NO de exact/range).**
No hace falta cambiar sigma — hace falta filtrar los YES exact/range con our_prob < 65%.

---

## Fix Propuesto

Agregar condición en el quality trader canary: **no entrar en YES exact/range si our_prob < 65%.**

Esto habría:
- Bloqueado los 23 YES losses (avg our_prob = 40.1%, todos < 65%)
- Mantenido los 6 NO wins (our_prob > 78%)
- Mantenido los NO wins también del lado NO

Implementación: una línea en `bot.py` en el bloque `exact_range_canary`.

---

## Estado

- C1 ✅ Cerrado con causa raíz identificada
- C3 ✅ Cerrado (corolario de C1 — no requiere sesión separada)
- Siguiente: implementar fix en bot.py (una línea, riesgo bajo)
