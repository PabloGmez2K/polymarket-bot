# SL_intra Hazard Monitor L2 — Outcome Evaluation

**Creado:** 2026-05-23 (Sesión 379, Sonnet)
**Fuente live:** Railway `/app/data/sl_intra_hazard_monitor_audit.json` + `/app/data/trade_lifecycle.json`
**Herramienta:** `python3 /app/tools/sl_intra_case_readout.py --data-dir /app/data --json`
**Extracción:** 2026-05-23 ~14:00 UTC
**Veredicto técnico:** `L2_GATE_MET_OUTCOME_TABLE_READY_FOR_OPUS`

---

## 1. Gate de tokens resueltos

| Criterio L3 | Valor | Estado |
|---|---|---|
| Días desde activación (mín 14d) | 19 días (desde 2026-05-04) | **CUMPLIDO** |
| Tokens con trazas L2 en `seen` | 11 | **CUMPLIDO** |
| Tokens resueltos con P&L disponible | 11 / 11 | **CUMPLIDO** |
| Gate ≥ 8 tokens resueltos | 11 ≥ 8 | **CUMPLIDO** |

Todos los 11 tokens del audit están en `trade_lifecycle.json` con `final_status=closed` y P&L real disponible. El gate formal está cumplido.

---

## 2. Tabla por token

| Ciudad | Fecha | Clasificación | Cierre | P&L real | Tiers L2 detectados | Tier máx | CF@deteriorating δ | CF@terminal δ | CF@collapsed δ | Notas |
|---|---|---|---|---|---|---|---|---|---|---|
| Munich | 2026-05-07 | HAZARD_OBSERVED_WIN | RESOLVED_WIN | **+$1.39** | deteriorating | deteriorating | -$4.10 | — | — | WIN; falso positivo L2 |
| Singapore | 2026-05-12 | HAZARD_OBSERVED_WIN | RESOLVED_WIN | **+$1.92** | deep + terminal | terminal | — | -$6.41 | — | WIN; falso positivo L2; no llegó a deteriorating |
| Seoul | 2026-05-12 | REEVAL_GOOD_SHADOW | LOSS_TOTAL | **-$2.34** | deteriorating + deep + terminal | terminal | -$0.58 | -$1.75 | — | LOSS; precio rebotó tras det+term → cierre peor que real |
| Paris | 2026-05-13 | REEVAL_GOOD_SHADOW | LOSS_TOTAL | **-$2.19** | deteriorating + deep + terminal | terminal | +$0.76 | +$0.17 | — | LOSS; venta en deteriorating habría ahorrado $0.76 |
| Singapore (33°C) | 2026-05-14 | REEVAL_GOOD_SHADOW | LOSS_TOTAL | **-$2.08** | deteriorating + deep + terminal | terminal | -$0.72 | -$1.75 | — | LOSS; precio rebotó tras detección → venta temprana peor |
| Singapore (32°C) | 2026-05-14 | HAZARD_OBSERVED_WIN | RESOLVED_WIN | **+$2.97** | deteriorating + deep + terminal | terminal | — | — | — | WIN; **DATA QUALITY**: entry_price=null, total_amount=0; CF no computable |
| Shanghai | 2026-05-14 | REEVAL_GOOD_SHADOW | LOSS_TOTAL | **-$1.77** | deteriorating + terminal + collapsed | collapsed | +$0.39 | -$0.18 | -$0.20 | LOSS; único collapsed; venta en det ok, en term/coll peor |
| Munich | 2026-05-15 | HAZARD_OBSERVED_WIN | RESOLVED_WIN | **+$1.61** | deteriorating + deep | deep | -$4.23 | — | — | WIN; falso positivo L2 |
| Toronto | 2026-05-16 | HAZARD_OBSERVED_LOSS | LOSS_TOTAL | **-$2.48** | deteriorating + deep + terminal | terminal | +$0.79 | +$0.19 | — | LOSS; venta en deteriorating habría ahorrado $0.79 |
| Toronto | 2026-05-21 | HAZARD_OBSERVED_WIN | RESOLVED_WIN | **+$1.02** | deteriorating | deteriorating | -$2.38 | — | — | WIN; falso positivo L2 |
| Singapore | 2026-05-22 | HAZARD_OBSERVED_LOSS | LOSS_TOTAL | **-$2.30** | deteriorating + terminal | terminal | +$0.69 | +$0.04 | — | LOSS; venta en deteriorating habría ahorrado $0.69 |

**Leyenda δ (delta_vs_real):** positivo = venta temprana habría sido mejor que la realidad; negativo = venta temprana habría sido peor.

---

## 3. Tabla agregada por tier

### 3.1 Cobertura

| Tier | n tokens que alcanzaron ese tier | n WINs | n LOSSes |
|---|---|---|---|
| deteriorating | 10 (excl. Singapore May12) | 4 ¹ | 6 |
| deep | 5 | 2 | 3 |
| terminal | 8 ² | 2 | 6 |
| collapsed | 1 | 0 | 1 |

¹ Singapore May14 (32°C) llegó a deteriorating pero tiene data quality issue (no total_amount).
² Incluye Singapore May14 (32°C) con data quality.

### 3.2 P&L real agregado

| Subconjunto | n | P&L real total |
|---|---|---|
| Todos los casos L2 (11) | 11 | -$4.25 (+$8.91 wins / -$13.16 losses) |
| Solo WINS (5) | 5 | +$8.91 |
| Solo LOSSES (6) | 6 | -$13.16 |

### 3.3 Contrafactual agregado por tier (bruto, sin fees/slippage)

**Nota: `fee_slippage_not_modeled`** — los deltas son brutos. No existe fórmula aprobada para fees/slippage intraday en el contrato. El neto real podría ser peor (fees de venta).

#### Si L3 hubiera actuado a `deteriorating` (n=9 con CF computable; Singapore May14 32°C excluida por data quality)

| | Valor |
|---|---|
| P&L real para esos 9 | -$7.14 |
| CF@deteriorating para esos 9 | -$16.52 |
| **Delta bruto acumulado** | **-$9.38** |
| Interpretación | L3 en deteriorating habría costado $9.38 adicionales |
| Si se incluye Singapore May14 32°C (WIN +$2.97 perdido) | aprox. **-$12.35** adicionales |

Desglose:
- WINs (4 casos con CF): Munich May7 -$4.10, Munich May15 -$4.23, Toronto May21 -$2.38 = **-$10.71** de costo por falsos positivos
- LOSSes (5 casos con CF): Paris +$0.76, Singapore May22 +$0.69, Toronto May16 +$0.79, Shanghai +$0.39, Seoul -$0.58, Singapore May14 33°C -$0.72 = **+$1.33** neto en pérdidas

Ratio: el costo de los falsos positivos (+$10.71) supera ampliamente el beneficio en pérdidas (+$1.33).

#### Si L3 hubiera actuado a `terminal` (n=7 con CF computable)

| | Valor |
|---|---|
| P&L real para esos 7 | -$9.19 |
| CF@terminal para esos 7 | -$18.88 |
| **Delta bruto acumulado** | **-$9.69** |
| Interpretación | L3 en terminal habría costado $9.69 adicionales |
| Nota | Singapore May12 (WIN +$1.92, delta -$6.41) domina el resultado |

#### Si L3 hubiera actuado a `collapsed` (n=1)

| | Valor |
|---|---|
| Único caso | Shanghai May14 (LOSS_TOTAL -$1.77) |
| CF@collapsed | -$1.97 |
| Delta bruto | -$0.20 |
| Muestra | Insuficiente para conclusión |

---

## 4. Hallazgos técnicos clave

### 4.1 Tasa de falsos positivos

5 de 11 posiciones con trazas L2 resolvieron como WIN (45%). Para tres de ellas (Munich May7, Munich May15, Toronto May21), el L2 detectó tiers `deteriorating` o `deep` durante caídas intraday transitorias, y el mercado resolvió favorablemente. El costo de haberse salido en esos momentos habría sido entre -$2.38 y -$4.23 por posición.

### 4.2 Rebote de precio tras detección (ruido de tier)

En Seoul May12 y Singapore May14 (33°C), el L2 detectó `deep` o `terminal` durante una caída real, pero el precio **rebotó** antes del vencimiento. El cierre final fue `LOSS_TOTAL / micro_position_unsellable`, pero la magnitud de la pérdida fue menor que el contrafactual de venta en el tier detectado. Esto sugiere que la señal de tier contiene ruido temporal significativo: el precio puede caer a `terminal` y recuperarse parcialmente antes de colapsar.

El patrón específico de Seoul May12:
- `deep` detectado a las 04:59 UTC (pct_pnl=-80%)
- `terminal` detectado a las 05:39 UTC (pct_pnl=-86%)
- `deteriorating` detectado a las 06:19 UTC (pct_pnl=-61%) — **precio rebotó**
- Resolución final: LOSS_TOTAL pero con P&L real de -$2.34 (no el -100% de micro_position_unsellable canónico)

### 4.3 Correlación tier → resultado

| Tier máximo alcanzado | n | Outcomes |
|---|---|---|
| deteriorating (solo) | 2 | 2 WINS (Munich May7, Toronto May21) |
| deep (máximo) | 1 | 1 WIN (Munich May15) |
| terminal (máximo) | 7 | 2 WINS + 5 LOSSES |
| collapsed (máximo) | 1 | 1 LOSS (Shanghai May14) |

El tier máximo `terminal` tiene 5/7 (71%) de ratio de pérdida. Pero el tamaño de muestra es demasiado pequeño para calibrar con significancia estadística.

### 4.4 Data quality

Singapore May14 (32°C, 95026..., +$2.97 WIN):
- `avg_entry_price=null`, `total_amount=0.0` en trade_lifecycle
- CF bruto no computable para ningún tier
- El P&L real fue +$2.97
- Este caso tiene trazas L2 en los tres tiers deteriorating+deep+terminal
- No se puede incluir en el delta agregado; marcado como DATA_QUALITY

---

## 5. Limitaciones

1. **n=11, n_loss=6**: muestra pequeña. Los deltas agregados están dominados por pocos casos de alto impacto (Singapore May12 WIN +$1.92 con CF@terminal -$6.41).
2. **fee_slippage_not_modeled**: deltas son brutos. En mercados near-resolution con poca liquidez, la venta real podría tener spread/slippage significativo que empeoraría el CF aún más.
3. **micro_position_unsellable en losses**: algunos tokens son económicamente invendibles antes de resolución. La hipótesis de venta en tier puede ser parcialmente no ejecutable (L3 no podría ejecutar la salida incluso si lo intentara).
4. **Ventana temporal corta**: 19 días, condición=exact+days_ahead≤0 exclusivamente. No hay datos range ni days_ahead>0.
5. **Singapore May14 95026 DATA_QUALITY**: excluida del agregado. Su inclusión como WIN aumentaría el costo de falsos positivos.
6. **Mercados bloqueados**: algunos losses son posiciones de mercados bloqueados (Paris, ex-Phase 1). Esto puede sesgar la muestra de LOSSes hacia calidad de señal peor.

---

## 6. Veredicto técnico para Opus

**Veredicto:** `L2_GATE_MET_OUTCOME_TABLE_READY_FOR_OPUS`

Los datos son suficientes para una decisión Opus sobre L3. Resumen ejecutivo:

| Pregunta | Respuesta técnica |
|---|---|
| ¿Gate cumplido? | Sí: 11/11 resueltos, 19d desde activación |
| ¿L2 aportó señal preventiva neta positiva? | **No** en ningún tier. Delta agregado negativo en todos los tiers (-$9.38 a -$9.69) |
| ¿Habría valido la pena activar L3 en algún tier? | No con esta muestra. Las pérdidas evitadas en loss cases son ampliamente superadas por el costo de falsos positivos (WINs vendidos prematuramente) |
| ¿El monitor L2 detecta ruido? | Sí. Seoul y Singapore May14 33°C muestran detección en caídas temporales que luego rebotaron parcialmente |
| ¿Es la señal `terminal` más precisa que `deteriorating`? | Marginalmente: 71% ratio de pérdida en `terminal`, pero n=7 insuficiente |
| ¿Hay valor en seguir L2 sin L3? | Sí: acumulación de datos LOG_ONLY sin costo, y el monitor ya es funcional |
| ¿Próximo checkpoint sugerido? | A criterio de Opus; dato mínimo recomendado: n_loss ≥ 15 con trazas L2 para calibrar tiers |

**Lo que Opus debe decidir:**
- ¿Mantener L2 sin cambios y seguir acumulando?
- ¿Rediseñar tiers para reducir ruido temporal (e.g., confirmación multi-ciclo antes de activar tier)?
- ¿Descartar L3 ejecutable por incompatibilidad estructural con `micro_position_unsellable` (si la posición es invendible, L3 no puede ejecutar)?
- ¿Revisar el criterio de scope (actualmente exact+days_ahead≤0 solamente)?

**Nota:** este documento no propone ningún cambio ejecutable. La decisión de L3, modificación de umbrales, cambio de scope o cierre del monitor corresponde exclusivamente a Opus.
