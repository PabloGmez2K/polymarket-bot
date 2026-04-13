# Signals vs Edge Cross-check — Baseline 2026-04-13

**Sesión:** 169 (Sonnet)
**Handoff origen:** A (Experimento 1 — Cross-check bot edge vs trader consensus)
**Datos:** `signals.json` generado `2026-04-13T04:00:58 UTC`, `shadow_city_tracking.json` actualizado `2026-04-13T08:00:37 UTC`
**Tool:** `tools/signals_vs_edge_crosscheck.py`
**JSONL:** `data/runtime_import_derived/signals_crosscheck.jsonl` (primer registro)

---

## Resultado general

| Bucket | Ciudades | Con consenso | Con conds permitidas |
|--------|----------|--------------|----------------------|
| MATCH | 14 | 5 | 6 |
| BOT_ONLY | 2 | — | — |
| TRADER_ONLY | 21 | 3 | 8 |

De 104 señales activas de 8 quality traders, el universo efectivo se reparte entre **14 ciudades donde bot y traders se solapan** y **21 ciudades donde solo tienen señal los traders** (sin edge bot visible). Solo 2 ciudades tienen edge bot sin ningún trader cubriendo la misma fecha.

---

## Validación de ejemplos canónicos

- **Austin** → TRADER_ONLY ✓ — 2 señales `at_or_above 84°F`, ambas en consenso (WR 65.5%), `edge_hits=0`. El caso canónico del gap: traders ven oportunidad, bot no registra edge.
- **Seoul** → MATCH ✓ — 10 señales, 7 en consenso, `edge_hits=2`, ciudad canary activa. El caso canónico de alineación.

---

## Hallazgo 1: El bot y los traders son mayoritariamente DIVERGENTES por ciudad

14 MATCH vs 21 TRADER_ONLY vs 2 BOT_ONLY. Los traders cubren **2.5× más ciudades** sin solapamiento con el bot que con él. Interpretaciones posibles:

1. El bot tiene un universo shadow mucho más restringido que el mercado que los traders exploran.
2. Los traders siguen activamente ciudades donde el bot no llega porque `edge_hits=0` (no hay forecast accuracy suficiente, o condición filtrada, o ciudad no vista en skips).
3. El universo de shadow es incompleto — muchas de las 21 ciudades TRADER_ONLY **no aparecen en `shadow_city_tracking` en absoluto**, no solo con `edge_hits=0`. Ejemplos: Austin, Helsinki, Milan, Toronto, Taipei... El bot nunca las analizó en serio.

**Implicación:** el gap principal no es "el bot ve edge y no entra" sino "el bot **no observa** estas ciudades en absoluto".

---

## Hallazgo 2: Las conds `exact/range` dominan casi todo

De las 104 señales: `exact`=76 (73%), `range`=8 (8%), `at_or_above`=19 (18%), `at_or_below`=1 (1%). Solo **20 señales** (19%) caen en condiciones que el bot puede operar.

Desglosado por bucket:
- **MATCH con conds permitidas**: 6 ciudades (Dallas, London, Munich, Seoul, Shanghai, Tokyo). El bot SÍ podría operar aligned con traders en estas ciudades.
- **TRADER_ONLY con conds permitidas**: 8 ciudades. El bot podría en teoría cubrir estas señales si las ciudades entraran en shadow y acumularan edge.

La decisión previa de bloquear `exact/range` resulta confirmada como cuello estructural: el 81% de las señales de quality traders caen en condiciones que el bot nunca ejecuta (→ ver Handoff B para medir WR real de ese bloque).

---

## Hallazgo 3: BOT_ONLY es casi vacío (2 ciudades)

Solo **Beijing** (edge_hits=3) y **Chicago** (edge_hits=1) tienen edge bot sin señales trader para fechas actuales. Esto es importante:

- No sugiere que el bot tenga alpha independiente significativo en muchos mercados.
- Puede ser un artefacto de que los traders no cubren estas ciudades hoy, no que el bot sea más agudo.
- Beijing y Chicago merecen seguimiento: si el bot acierta con edge_hits sin confirmación trader, es evidencia de alpha genuinamente propio.

---

## Hallazgo 4: TRADER_ONLY actionable — 8 ciudades con señales operables

Las ciudades donde traders tienen señales `at_or_above`/`at_or_below` pero el bot no registra edge:

| Ciudad | Signals | Consenso | Max WR | Condición |
|--------|---------|----------|--------|-----------|
| Austin | 2 | 2 (consensus) | 66% | at_or_above |
| Toronto | 1 | 2 (via exact) | 76% | at_or_below |
| Helsinki | 1 | 0 | 68% | at_or_above |
| Houston | 2 | 0 | 66% | at_or_above |
| Mexico City | 1 | 0 | 54% | at_or_above |
| Milan | 2 | 0 | 95% | at_or_above |
| Panama City | 1 | 0 | 54% | at_or_above |
| Tel Aviv | 1 | 0 | 54% | at_or_above |

**Austin** es el caso más urgente: 2 señales consensus en condición operable. El bot no está en shadow de Austin — si Austin tuviera datos históricos de forecast vs resolución, podría evaluarse si merece incorporación.

**Toronto** tiene 2 consensus pero la señal operable es `at_or_below` sobre fecha Apr12 (posiblemente ya resuelta). Igual interesante como candidato.

---

## Hallazgo 5: MATCH con conds permitidas — confirmación bot+trader en 6 canary/shadow

| Ciudad | edge_hits | best_edge | Allowed sigs | Consenso | Canary |
|--------|-----------|-----------|--------------|----------|--------|
| Dallas | 8 | 45.8% | 2 | 2 | No (shadow bloqueado) |
| London | 2 | 28.4% | 1 | 6 | Sí |
| Munich | 3 | 24.3% | 1 | 0 | Sí |
| Seoul | 2 | 15.0% | 3 | 7 | Sí |
| Shanghai | 19 | 38.7% | 1 | 2 | Sí |
| Tokyo | 4 | 28.3% | 1 | 2 | Sí |

**Dallas** es el más llamativo: 8 edge_hits, 45.8% best edge, 2 señales consensus en `at_or_above` — todo indicaría promoción, pero sigue en shadow sin promover (→ ver Handoff C).

---

## Recomendaciones accionables

**Acción inmediata:**
1. **Correr esta tool diariamente** durante 7-10 días para construir la serie temporal. Un solo snapshot no permite distinguir señal de ruido de fecha.
2. **Dallas + Handoff C**: la combinación de 8 edge_hits y 2 señales consensus accionables hoy es el argumento más fuerte para desbloquear la auto-promoción (diagnóstico en esta misma sesión).

**A mediano plazo (1-2 semanas de datos):**
3. **Evaluar si Austin y Houston merecen entrar en shadow**: no hay edge registrado, pero los quality traders los cubren con condiciones operables. Primera pregunta: ¿`shadow_city_tracking` los tiene con `edge_hits=0` o directamente **no los ve en absoluto**? (Austin no aparece en el archivo — es el segundo caso, más grave: nunca fue analizado.)
4. **Handoff B**: la WR implícita de exact/range sobre resolutions reales determinará si el 81% de señales bloqueadas merece reabrir, congelar o ignorar.

**No hacer ahora:**
- Añadir Austin/Houston a shadow sin primero validar cobertura NOAA/Polymarket para esas ciudades.
- Cambiar `allowed_conditions` hasta tener WR de Handoff B.
- Promover Dallas manualmente — el diagnóstico correcto es Handoff C.

---

## Apéndice — Metodología

El crosscheck opera por ciudad, no por market individual:
- **MATCH**: ciudad con `edge_hits ≥ 1` en `shadow_city_tracking` Y ≥1 señal activa de quality trader.
- **BOT_ONLY**: ciudad con `edge_hits ≥ 1` sin señales.
- **TRADER_ONLY**: ciudad con señales de quality trader, `edge_hits=0` o ausente en `shadow_city_tracking`.

El matching por `match_key` exacto (city|date|condition|temp|unit) no se aplica en esta versión baseline porque `shadow_city_tracking` no preserva market-level detail por fecha. La granularidad actual (por ciudad) es suficiente para las preguntas estratégicas planteadas.
