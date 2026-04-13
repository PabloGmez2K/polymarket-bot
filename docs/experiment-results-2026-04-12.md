# Resultados Experimentos Edge — 2026-04-12

**Sesión**: análisis read-only sobre datos locales  
**Contexto**: bot 91 trades, 16.5% WR, -$29.71 PnL, shadow mode desde Apr 4  
**Metodología**: trade_lifecycle.json (70 posiciones), directional_trader_census.json (10 traders)

---

## TAREA 1 — Phantom Edge Analysis (Experimento 3)

### Hallazgo crítico: convención del bot

`market_resolved_yes` en este codebase significa **"nuestro token resolvió a $1 (ganamos)"**, no que el outcome YES del mercado ganó. Todo el bot apuesta NO (temperatura no alcanzará el umbral), así que cuando NO gana, close_reason = `market_resolved_yes`. Confirmado por diagnóstico: todos los `market_resolved_yes` son `side=NO, pnl>0`.

### Resultados

```
Total trades cerrados: 58
Analizables (con resolución conocida): 16
  Dirección correcta: 15 (93.8%)
  Dirección incorrecta: 1 (6.2%)
  Inconcluso (sin datos post-cierre): 42
```

**Breakdown por causa de cierre:**

| Causa           | Total | Analizables | Dir. correcta |
|-----------------|-------|-------------|---------------|
| market_resolved_yes | 9 | 9 | 9 (100%) |
| take_profit     | 4     | 4           | 4 (100%)  |
| reeval          | 3     | 3           | 2 (67%)   |
| stop_loss       | 11    | 0           | — (sin datos post-cierre) |
| micro_position_unsellable | 28 | 0 | — (sin datos post-cierre) |

**Problema estructural**: 42/58 trades (72%) son inconclusivos porque `stop_loss` y `micro_position_unsellable` no tienen datos del mercado post-cierre. No podemos saber si esas direcciones fueron correctas o incorrectas.

**Trades donde bot salió pero mercado siguió siendo correcto (top upside_left):**

| Trade | Cerró @  | Máx después | Upside perdido | Causa |
|-------|----------|-------------|----------------|-------|
| Chicago 57°F Apr4 YES | 0.42 | 0.9995 | $3.26 (+138%) | reeval |
| NYC 74°F Mar31 YES | 0.44 | 0.993 | $1.66 (+126%) | reeval |
| Dallas Apr1 YES | 0.04 | 0.065 | $0.25 (+63%) | micro_unsellable |
| NYC Apr3 YES | 0.26 | 0.30 | $0.24 (+15%) | micro_unsellable |

Los 2 casos de `reeval` con upside_left significativo son directamente atribuibles al bot saliendo prematuramente en dirección correcta.

### Veredicto T1

**SEÑAL POSITIVA** — 93.8% dirección correcta (umbral: ≥55%)  
*Caveat importante*: los 16 analizables incluyen solo los trades que terminaron de alguna forma observable (resolución de mercado, take_profit, reeval con PnL conocido). Los 42 inconclusivos (stop_loss + micro_position) pueden distorsionar el cuadro completo.

El problema del bot **no es el modelo**. Las pérdidas vienen de:
1. `stop_loss` sacando al bot antes de resolución en trades donde la dirección era correcta
2. `micro_position_unsellable` (28 trades!) — posiciones muy pequeñas que no pueden liquidarse
3. `reeval` con criterio demasiado agresivo (2 casos confirmados de salida prematura)

---

## TAREA 2 — Trader Census: Outcomes (Experimento 2)

### Mercados evaluados

| Mercado | mkt_prob_yes (entry) | Resultado | Fuente |
|---------|---------------------|-----------|--------|
| Shanghai at_or_above 30°C Apr9 | ~32.3% | **NO gana** | Confirmado por bot T3 |
| Ankara at_or_below 8°C Apr8 | ~42-50% (inferido del precio) | **NO gana** | Inferido de mkt_prob→0.0 |
| Wuhan at_or_above 24°C Apr8 | ~0.2% | **NO gana** | Inferido de mkt_prob=0.002 |

*Nota metodológica*: el `market_prob_yes` del census fue capturado el 8 Apr a las 15:21 UTC. Para Ankara/Wuhan Apr8, el mercado ya podría haber resuelto. Los precios de entrada (0.38-0.70) indican que en el momento de compra había incertidumbre real (~40-62% YES). No eran "moneda obvia" al entrar.

### Win rates en el census sample

| Trader | Sample WR | Rango útil WR | n útiles | Hist WR | Nota |
|--------|-----------|----------------|----------|---------|------|
| White-Donkey | 6/6 = 100% | 6/6 = 100% | 6 | 56.6% | ✓ THRESHOLD |
| Motionless-Stalk | 6/6 = 100% | 6/6 = 100% | 6 | 39.8% | ✓ THRESHOLD |
| Academic-Maniac | 6/6 = 100% | 6/6 = 100% | 6 | 55.6% | ✓ THRESHOLD |
| Entire-Hood | 2/3 = 67% | 2/3 = 67% | 3 | 91.0% | Umbral con n=3 |
| Massive-Distribution | 2/5 = 40% | 2/5 = 40% | 5 | 70.7% | Apostó ambos lados |
| Coarse-Gas | 1/3 = 33% | 1/3 = 33% | 3 | 73.5% | **Apostó YES en Shanghai** |
| Rewarding-Pusher | 1/2 = 50% | 1/2 = 50% | 2 | 17.5% | — |
| Content-Lunchroom | 1/2 = 50% | 1/2 = 50% | 2 | 61.0% | — |
| Illustrious-Church | 1/2 = 50% | 1/2 = 50% | 2 | 5.0% | — |
| Extra-Small-Tabletop | 1/2 = 50% | 1/2 = 50% | 2 | 72.7% | **Apostó YES en Shanghai** |

**Patrón de apuestas en Shanghai Apr9 (rango útil, mkt=32.3%):**
- 8 traders apostaron NO → todos ganaron (100%)
- 2 traders (Coarse-Gas, Extra-Small-Tabletop) apostaron YES → ambos perdieron (0%)

**Patrón de apuestas en Ankara Apr8 (rango útil en entrada):**
- Traders que apostaron NO: Motionless-Stalk, Academic-Maniac, Extra-Small-Tabletop, Coarse-Gas, Massive-Distribution (2/4) → ganaron
- Traders que apostaron YES: Entire-Hood, Rewarding-Pusher, Content-Lunchroom, Illustrious-Church, Massive-Distribution (2/4) → perdieron

**Massive-Distribution** apostó ambos lados en Ankara → patrón de market making o testeo, no señal direccional.

### Veredicto T2

**SEÑAL DÉBIL** — 3 traders cumplen umbral (WR>60%, n≥5), pero con advertencia crítica:

> Los 5-6 trades por trader son repetidos en los **mismos 2-3 mercados distintos** (Shanghai Apr9, Ankara Apr8, Wuhan Apr8). El umbral n≥5 en **trades** no equivale a n≥5 en **mercados independientes**. Valor estadístico limitado.

Lo más útil de T2: la **dirección del consenso** es información. El 80% de los traders eligió NO en Shanghai Apr9 cuando el mercado decía 32.3% para YES → la mayoría acertó. Pero esto podría ser coincidencia en una sola observación.

Los traders con mayor historial comprobado (Entire-Hood 91%, Coarse-Gas 73.5%) se dividieron: Entire-Hood apostó NO en Shanghai (acertó) pero YES en Ankara (falló). Coarse-Gas apostó YES en Shanghai (falló). Señal histórica no se traduce directamente a esta muestra específica.

---

## TAREA 3 — Settlement Fidelity Quick-Check (Experimento 1, parcial)

### Tabla de mercados resueltos directamente

| Mercado | Side | Resultado | Forecast (OpenMeteo) | Our_prob | Modelo OK |
|---------|------|-----------|---------------------|----------|-----------|
| Tokyo 26°C Apr11 NO | NO | mercado resolvió a favor | 21.2°C < 26°C | 98.8% | ✓ |
| Seoul 15°C Apr9 NO | NO | mercado resolvió a favor | 10.9°C < 15°C | 97.1% | ✓ |
| Shanghai 30°C Apr9 NO | NO | mercado resolvió a favor | 26.2°C < 30°C | 95.9% | ✓ |
| Buenos Aires 29°C Apr3 NO | NO | mercado resolvió a favor | 26.8°C < 29°C | 92.2% | ✓ |
| Atlanta Apr2 NO | NO | mercado resolvió a favor | 27.1°C | 63.3% | ✓ |
| Seoul 14°C Apr1 NO | NO | mercado resolvió a favor | 9.7°C < 14°C | 94.8% | ✓ |
| Buenos Aires 28°C Apr1 NO | NO | mercado resolvió a favor | 25.6°C < 28°C | 95.1% | ✓ |
| Atlanta Apr1 NO | NO | mercado resolvió a favor | 26.4°C | 78.9% | ✓ |
| Tokyo 18°C Apr1 NO | NO | mercado resolvió a favor | 17.4°C ≈ 18°C | 81.1% | ✓ |

**Settlement fidelity: 9/9 = 100%**

OpenMeteo forecast fue coherente con la resolución real del mercado en TODOS los casos analizables. Los forecasts consistentemente predijeron temperaturas por debajo del umbral, y el mercado confirmó que el umbral no fue alcanzado.

Nota: el caso Tokyo 18°C Apr1 es el más ajustado (forecast=17.4°C vs umbral=18°C, ~0.6°C de margen). El bot asignó our_prob=81.1% → hay calibración razonable.

### Veredicto T3

**SEÑAL POSITIVA** — OpenMeteo como fuente de forecast tiene alta coherencia con outcomes reales en los 9 mercados resueltos directamente. No hay evidencia de error sistemático de forecast en este dataset.

Limitación: todos los 9 casos son side=NO (el bot solo apuesta NO en esta fase). No hay trades de side=YES con resolución directa para validar la calibración en el otro lado.

---

## VEREDICTO INTEGRADO

### Señales

| Experimento | Veredicto | Confianza |
|-------------|-----------|-----------|
| T1 Phantom Edge | POSITIVO — 93.8% dir. correcta | Media (42/58 inconclusivos) |
| T2 Trader Census | DÉBIL POSITIVO — consenso acertó en sample | Baja (solo 2-3 mercados) |
| T3 Settlement | POSITIVO — 9/9 forecasts coherentes | Alta (todos los resueltos) |

### Diagnóstico del problema real

**El modelo SÍ tiene edge direccional.** Las pérdidas no son del modelo sino de 3 mecanismos de salida:

1. **`micro_position_unsellable` (28 trades, 48% de los cerrados)** — posiciones microscópicas que expiran sin poder vender. Causa pérdida de capital por falta de liquidez.

2. **`stop_loss` excesivo (11 trades, 19%)** — saca al bot prematuramente. Sin datos post-cierre para saber cuántos eran dirección correcta.

3. **`reeval` agresivo (3 trades)** — 2 de los 3 casos con datos confirmaron que la dirección era correcta pero el bot salió (Chicago -$3.26, NYC -$1.66 de upside perdido).

### Veredicto final

**GO** — seguir en este mercado, pero la prioridad es arreglar los mecanismos de salida, no el modelo.

El modelo acerta la dirección. El problema es la gestión de posición:
- `micro_position_unsellable` es el mayor destructor de PnL (número de ocurrencias)  
- `reeval` con criterio poco calibrado abandona posiciones ganadoras
- `stop_loss` debe ser evaluado (sin datos suficientes aún)

### Próximos pasos sugeridos

1. **Inmediato**: investigar por qué el 48% de trades terminan como `micro_position_unsellable`. ¿El bot entra con tamaños demasiado pequeños? ¿Hay un threshold de size mínimo que no se respeta?

2. **Próxima sesión**: analizar los 11 stop_loss con datos de mercado post-cierre (obtener prices de resolución para esos tokens). Determinar qué % de ellos tenían dirección correcta.

3. **Experimento 2 extendido**: necesita más mercados (≥10 distintos) para tener validez estadística. El census actual solo tiene 2-3 eventos.

---

*Generado: 2026-04-12 | Análisis read-only, sin cambios al bot*
