# Bankroll Readiness Evidence Pack — $25 → $35

**Fecha:** 2026-05-13  
**Agente:** Sonnet 4.6 (read-only)  
**Estado:** BLOCKED — no autoriza subida  
**Fuente de verdad:** herramientas live Railway + docs canónicos  
**Referencia Opus anterior:** `docs/p0_b5_b6_opus_review_2026_05_13.md` → `KEEP_BLOCKED`

---

## 1. Veredicto de sesión

```
BANKROLL $25 → MANTENER
$35 → NO AUTORIZADO
```

Ningún gate duro de Nivel 2 puede cerrarse con fuente canónica hoy. El meta-bloqueador es
`pnl_source_non_canonical`: toda métrica de PnL/WR/drawdown proviene de `trade_lifecycle`
con `contamination_rate=1.0`, que es `non_canonical_telemetry` por diseño (B3). La fuente
canónica no existe hasta B5+B6, cuyo ETA operativo mínimo es **2026-06-08**.

---

## 2. Tabla de gates — Nivel 2 ($25 → $35)

| # | Criterio | Umbral | Estado | Valor actual | Herramienta/Fuente | Siguiente acción | Trigger cuantitativo |
|---|---|---|---|---|---|---|---|
| G1 | `bot_health_check` OK o WATCH esperado ≥5 días consecutivos | OK / WATCH-esperado | **WATCH** | WATCH: rejects no-estándar (condition_filtered=7, sl_city_cooldown=2), errors=11, warnings=8 | `bot_health_check.py` Railway | Verificar que rejects y errores se mantienen sin escalada en próximos ciclos | 5 días consecutivos sin ACTION ni errores nuevos |
| G2 | SQLiteRecorder fresco, sin gaps grandes | Sin gaps >18h | **CLOSED** | 117 ciclos, 16.0d span, 0 gaps, last write hace 6min | `phase1_readiness_check.py` + `db_throughput_report.py` | Ninguna | Mantener frescura |
| G3 | `phase1_readiness_check` exit_code ∈ {0,1} | exit_code=0 o 1 | **CLOSED** | exit_code=0, ready=true, cycle_events=117, days=16, gaps=[] | `phase1_readiness_check.py --json` Railway | Ninguna | Ya cumplido |
| G4 | Trades limpios serie actual ≥30 | ≥30 | **BLOCKED_BY_DATA** | last_30_clean_closed=30 (WR=50%, PnL=+$18.86) pero fuente `non_canonical_telemetry` → no usable para scaling | `bankroll_scaling_check.py` Railway | Esperar fuente canónica (B5+B6) | 30 trades clean con `canonical_source≠none` |
| G5 | Ciclos estables serie actual ≥10 | ≥10 | **CLOSED** | 308 ciclos totales, 117 en SQLite desde 2026-04-27 | `db_throughput_report.py` | Ninguna | Ya superado (30×) |
| G6 | PnL serie actual ≥$0.00 | ≥$0.00 | **BLOCKED_BY_DATA** | current_logic_series PnL=+$0.38 (non-canonical); last_30 PnL=+$18.86 (non-canonical); lifecycle ALL=-$20.47 (contaminated) | `bankroll_scaling_check.py` | Esperar fuente canónica; documentar divergencia lifecycle (ver §5) | PnL `canonical_candidate` 1W ≥$0.00 tras B5+B6 |
| G7 | WR serie actual ≥40% | ≥40% | **BLOCKED_BY_DATA** | current_logic_series WR=39.0% (100 trades, non-canonical); last_30 WR=50% (non-canonical) | `bankroll_scaling_check.py` | Esperar fuente canónica | WR canónico ≥40% en ventana clean |
| G8 | Drawdown últimos 5 cierres >−$3.00 | >−$3.00 | **WATCH** | drawdown_last_5=−$1.28 (pasa el umbral numérico, pero fuente non-canonical) | `bankroll_scaling_check.py` | Mantener observación | >−$3.00 con fuente canónica |
| G9 | Errores de ejecución 0 (order_rejected, auth_failed sin OK) | 0 | **CLOSED** | 0 errores de ejecución de este tipo; critical=0 | `bot_health_check.py` | Ninguna | Mantener |
| G10 | Posiciones atascadas 0 | 0 | **CLOSED** | open_positions=0, pending_exits=0, stale_pending_exits=0 | `bankroll_scaling_check.py` | Ninguna | Mantener |
| G11 | Signals operativas activas | Sí | **BLOCKED_BY_TIME** | S341 (condition_filtered kill-switch) activo; cohorte canary only; Phase 2 abierta hasta 2026-06-09; 26 buys en 117 ciclos (tasa ~1.3%) | `db_throughput_report.py` | Sin acción hasta T+30 (2026-06-09) | Post-Phase2 readout limpio |
| G12 | Bankroll Readiness Score ≥40% | ≥40% (`improving`) | **BLOCKED_BY_TIME** | 38.4% (etapa `early`); D1 WR=0/100 (WR=38.4%<umbral), D2 PnL=100/100, D3=26.5/100 edge density, D4=26.3/100 size pressure, D5=41.9/100 stability | `bankroll_readiness_score.py` Railway | WR improvement vía más buys canary; D3 mejora con más throughput | Score ≥40% en D1 (WR>50% n≥30) |
| G13 | `pnl_reconciliation_alert` sin fallo | Sin fallo | **WATCH** | "Falta P/L wallet para reconciliación completa"; 7d lifecycle +$4.63 WR=57.1%; gap conocido: sin wallet canónico | `pnl_reconciliation_alert.py` Railway | Ver §4 (divergencia) — documentar hipótesis | Wallet ΔP&L canonical disponible (post-B5+B6) |
| G14 | Tiempo desde último cambio core ≥3 días | ≥3d observación estable | **WATCH** | v10.6.50 dominante (46.9% ciclos); 4 versiones en 14d | `bankroll_readiness_score.py` D5 | Dejar bot estabilizar en v10.6.50 | ≥7d sin cambio de versión core |
| G15 | Decisión manual y explícita | Requerida | **PENDING** | Ningún gate duro cerrado con fuente canónica → decisión no procede | — | Esperar cumplimiento de todos los gates | Todos los gates anteriores en CLOSED o WATCH-aceptable |

**Gates CLOSED:** G2, G3, G5, G9, G10 (5/15)  
**Gates WATCH (pasan numéricamente, sin riesgo inmediato):** G1, G8, G13, G14  
**Gates BLOCKED_BY_DATA:** G4, G6, G7 (meta-bloqueador: `pnl_source_non_canonical`)  
**Gates BLOCKED_BY_TIME:** G11, G12  
**Gates PENDING:** G15

---

## 3. ¿Qué gates siguen bloqueados por tiempo?

### G11 — Signals operativas (BLOCKED_BY_TIME hasta 2026-06-09)

Phase 2 está diseñada para observar la cohorte canary sin contaminación. S341 (condition_filtered kill-switch, commit 47ee558) está activo por diseño. La cohorte activa no puede expandirse sin contaminar Phase 2.

- Throughput actual: 26 buys en 117 ciclos (~0.22 buys/ciclo)
- Tasa de conversión evaluado→buy: ~1.3% (2005 mercados evaluados)
- Slots muertos (0 buys en muchos ciclos): 12h, 09h, 15h, 19h, 21h, 23h
- Sin acción posible antes de T+30

### G12 — Bankroll Readiness Score (BLOCKED_BY_TIME, estimado ~2026-05-30)

Score actual 38.4%, umbral 40%. La dimensión crítica es D1 (WR Confidence = 0/100 porque WR=38.4% está debajo del umbral interno). D2 es 100/100 pero refleja lifecycle no-canónico. La mejora de D1 requiere que WR suba a ≥50% en n≥20, lo cual requiere más buys y cierres limpios en la cohorte canary.

---

## 4. ¿Qué gaps son técnicos y se pueden trabajar ya?

### GAP-A — Cash flow attestation desactualizada (ACTION_NOW — Pablo)

**Problema:** La última attestation cubre hasta **2026-05-11T08:00:53Z**. Hoy es 2026-05-13. Hay un gap de ~2 días sin attestation. `pnl_report.py` muestra `cash_flows.coverage_days=5.0` (no 7d) y el horizonte 1D queda bloqueado por `cash_flow_coverage_below_1D`.

**Acción concreta:** Pablo ejecuta:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh `
  "python tools/wallet_cash_flow_log.py --write --actor pablo_manual `
   --note 'No deposits or withdrawals 2026-05-11 to 2026-05-13' `
   --period-start 2026-05-11T08:00:53Z --period-end 2026-05-13T20:00:00Z 2>&1"
```

**Impacto:** Cierra la brecha de attestation. `pnl_report.py` 1W podría pasar de `blocked` a `provisional` con coverage >7d. No promueve a `canonical` ni desbloquea BANKROLL — solo mejora la calidad de observabilidad.

**Trigger:** Ejecutar cada 2-3 días mientras Phase 2 esté activa.

### GAP-B — Divergencia 1W wallet vs lifecycle sin documento (ACTION_NOW — Sonnet docs-only)

**Problema:** El P0 Opus (2026-05-13) indica que la promoción a `canonical_candidate` requiere un documento corto que narrative la divergencia. Wallet ALL provisional=+$2.93, lifecycle=-$20.47, divergencia=23.4 USDC (16× el umbral de 1W=1.5).

**Hipótesis documentada:** El lifecycle tiene `contamination_rate=1.0` porque incluye:
1. Batch `market_resolved` de posiciones históricas pre-2026-04-27 (antes de SQLiteRecorder), donde los precios de entrada/salida no se capturaron correctamente.
2. 4 trades `legacy_unresolved` (excluidos por `pnl_reconciliation_alert`).
3. Settlement gap: mercados que se resolvieron via batch en lugar de vía cierre normal, produciendo PnL negativo aparente.

La wallet ΔP&L (+$2.93 en 11.4d desde t0=2026-04-29) es más confiable porque refleja cambios reales de balance, ajustados por las 2 attestaciones de Pablo sin depósitos/retiros en ese período.

**Este gap no requiere Opus ahora.** Sonnet puede redactar el documento de reconciliación narrativa (ver trigger en §8 acción concreta).

### GAP-C — pnl_report 1D siempre blocked por snapshot_gap_gt_2h (NEEDS_DESIGN)

**Problema:** El horizonte 1D está bloqueado porque la cadencia de snapshots (~cada 24h) crea gaps >2h dentro de la ventana de 24h. El contrato B3 requiere ≥2 snapshots en 24h sin gap >2h.

**No es bug.** La cadencia actual de `wallet_snapshot.py` no genera snapshots sub-horarios. El 1D canónico es inalcanzable con la arquitectura actual sin aumentar frecuencia de snapshots.

**Impacto sobre BANKROLL:** bajo. El gate BANKROLL no requiere 1D canonical explícitamente — usa 1W. No bloquea $35 por sí solo, pero sí marca `coverage_gap=true` permanentemente.

**Propuesta futura (no implementar ahora):** evaluar si `wallet_snapshot.py` puede ejecutarse con mayor frecuencia en Railway sin afectar throughput del bot. Requiere diseño separado post-Phase2.

---

## 5. ¿Qué divergencia wallet vs lifecycle existe?

| Horizonte | Wallet ΔP&L (provisional) | Lifecycle PnL (non_canonical) | Divergencia | Umbral | Factor |
|---|---|---|---|---|---|
| 1W | TBD (blocked por coverage gap) | −$20.47 (toda la historia) | — | $1.50 | — |
| ALL | **+$2.93** (11.4d desde t0=2026-04-29) | −$20.47 | **$23.40** | N/A | ~16× |

**Hipótesis de trabajo (sin Opus, provisional):**

La cifra wallet +$2.93 sobre $25 inicial representa un resultado modestamente positivo en los últimos 11.4d (equivalente a ~+0.26 USDC/día). Esto es consistente con un sistema que: (a) gana algunos trades en cohorte canary, (b) tiene stops y micro-posiciones unsellable que producen pérdidas pequeñas, y (c) no ha tenido depósitos/retiros en el período.

La cifra lifecycle −$20.47 (122 trades cerrados) incluye:
- Trades de **antes de 2026-04-27** (pre-SQLiteRecorder), muchos con precios de entrada reconstruidos imprecisamente.
- 1 batch `market_resolved` antiguo (+$1.55 en 7d según pnl_reconciliation_alert).
- 4 trades `legacy_unresolved` (excluidos en reconciliation pero presentes en lifecycle).
- Trades SL_intra del período de sangrado (n=10, -$3.95) antes del guard v10.6.40.

La reconciliación completa requiere B5 (criterios formales) + B6 (Opus review) + Pablo signoff. Hasta entonces, la wallet ΔP&L es la fuente más confiable pero sigue siendo `provisional` / `non_canonical`.

---

## 6. ¿Qué evidencia de Phase 2 hay?

| Dimensión | Valor | Fuente |
|---|---|---|
| Ventana Phase 2 | Abierta hasta **2026-06-09** (T+30) | `post-phase2-strategy-experiments-2026-05-13.md` |
| Modo ciudades | Canary-only (ninguna ciudad Active) | `AGENTS.md` + env var `ACTIVE_TRADING_CITIES=NONE` |
| Kill-switch S341 | Activo (`condition_filtered` kill-switch, commit 47ee558) | `db_throughput_report` + `cycle_summary` |
| Ciclos Phase 2 | 117 en SQLite (desde 2026-04-27), 308 totales | `phase1_readiness_check` / `db_throughput_report` |
| Buys totales | ~26 en 117 ciclos (0.22 buys/ciclo) | `db_throughput_report` funnel |
| Ciudades observadas | London=133 snaps, Seoul=98, NYC=72, Shanghai=56, Paris=52, Madrid=33, Seattle=32 | `db_throughput_report` Snapshots By City |
| Condición dominante | `exact`=512 (71%), `range`=186 (26%) | `db_throughput_report` Conditions |
| Tasa buy/evaluado | ~1.3% overall; 0% en slots 09h, 12h, 15h, 19h, 21h, 23h | `db_throughput_report` Funnel |
| Posibles contaminaciones | Ninguna identificada (S341 no tocado, city modes no tocados) | Guardrails del equipo |

**Lectura Phase 2:** El sistema está acumulando datos de cohorte canary de forma limpia. El throughput bajo es esperado (diseñado así). Los datos post-Phase2 serán el input para el readout limpio del 2026-06-09.

---

## 7. ¿Qué dice throughput sobre capacidad de escalar?

| Métrica | Valor | Lectura |
|---|---|---|
| Buys totales en 117 ciclos | ~26 | Muy bajo para escalar con confianza estadística |
| Tasa buy/eval | ~1.3% (26/2005 mercados evaluados) | Throughput limitado por: price_out_of_range=56, condition_filtered=7, sl_city_cooldown=2 |
| Edge density (D3 readiness) | 0.27 edges/ciclo (26 edges en 98 ciclos, 14d) | Score 26.5/100 → dimensión más débil junto con D4 |
| Conversion seleccionado→buy | 85-100% en la mayoría de slots | No es el cuello de botella — el problema es que pocas oportunidades llegan a "selected" |
| Slots muertos | 09h, 12h, 15h, 19h, 21h, 23h (0 buys en múltiples ciclos) | No se tocan hasta post-Phase2 (L1/L2/S341 relax) |
| Proyección de trades limpios | A tasa actual: ~0.22 buys/ciclo × (2026-06-09 − hoy) ≈ 38 ciclos más ≈ 8-9 buys más hasta T+30 | Masa muestral final al cierre de Phase 2: ~34 trades canary |

**Conclusión throughput:** La capacidad de escalar en términos de volumen de señales **no mejora antes de T+30** sin contaminar Phase 2. Post-T+30, las palancas L1 (1 ciudad Active), L2 (S341 relax), L3 (cross-check passive) están diseñadas y priorizadas. La limitación es deliberada, no un bug.

---

## 8. ¿Qué evidencia SL_intra afecta el riesgo de subir BANKROLL?

| Indicador SL_intra | Valor | Riesgo sobre BANKROLL |
|---|---|---|
| Guard v10.6.40 | Activo desde 2026-04-27 — skipea exact+days≤1 | **Reduce** riesgo de sangrado SL_intra vs pre-guard |
| A8 veredicto (memoria) | ESPERAR_MÁS_MUESTRA — n=2 leverage-real (+$1.12) | No concluye aún; no bloquea BANKROLL por sí solo |
| Hazard monitor | 4 markets vistos en estados deteriorating/deep/terminal (London, Seoul…) | Telemetría interna; no autoriza acción operativa |
| Peor bucket 7d | micro_position_unsellable: −$4.53 n=2 WR=0% | Riesgo puntual de posiciones bloqueadas; ya documentado |
| Re-check A8 | 5º trade guarded o 2026-05-21 (el que llegue primero) | Sin acción hasta cumplirse |
| Impacto sobre bankroll $35 | Subir bankroll amplifica pérdidas SL_intra si guard falla | **WATCH RISK**: no subir bankroll mientras A8 sea ESPERAR_MÁS_MUESTRA |

**Lectura SL_intra:** El guard reduce el riesgo activamente. A8 tiene n insuficiente para veredicto. Subir BANKROLL antes de un veredicto A8 positivo amplifica la exposición al patrón SL_intra que produjo −$3.95 en n=10 pre-guard. Este no es el bloqueador principal (el bloqueador es pnl_source_non_canonical), pero es un riesgo adicional que refuerza el KEEP_BLOCKED.

---

## 9. Acciones concretas antes de 2026-06-09 sin contaminar Phase 2

| Acción | Tipo | Quién | Urgencia | Impacto sobre BANKROLL |
|---|---|---|---|---|
| **A1** — Actualizar cash flow attestation (hasta 2026-05-13) | Railway ssh, no-code, read-only JSONL append | Pablo | Esta semana | Cierra gap 1D/1W `blocked→provisional`; mejora calidad observabilidad pero NO desbloquea BANKROLL |
| **A2** — Documentar hipótesis divergencia lifecycle (reconciliación narrativa) | Sonnet docs-only | Sonnet/Pablo | Esta sesión o próxima | Es prerequisito para B5; no requiere Opus; output: `docs/lifecycle-divergence-narrative-2026-05.md` |
| **A3** — Renovar attestation cada 2-3 días | Operación rutinaria Pablo | Pablo | Continua | Acumula cobertura para llegar a ≥28d en ~2026-06-08 |
| **A4** — Observar A8 SL_intra re-check (2026-05-21 o 5º guarded) | Read-only audit | Sonnet | 2026-05-21 | Si resultado positivo, reduce uno de los riesgos adicionales a BANKROLL $35 |
| **A5** — Readout Phase 2 preparatorio (post 2026-06-09) | Codex audit read-only | Codex | Post T+30 | Input directo para gate v1 (L1) y decisión de escalar |
| **A6** — Verificar si `bankroll_readiness_score` cruza 40% | Watch pasiva | Sonnet | Continua | Score 38.4% → 40% requiere WR subir a ~41%+ en D1 con n≥20 |

**Lo que NO se toca antes de 2026-06-09:**
- BANKROLL (confirmado: no autorizado)
- City modes (ninguna ciudad a Active)
- S341 kill-switch
- SL_intra guard v10.6.40
- Entry rules, gates, sizing
- Fase C
- B5/B6 formal (Opus P0 dice: no abrir patch todavía)

---

## 10. Cronograma de desbloques estimados

| Fecha estimada | Evento | Gate desbloqueado |
|---|---|---|
| 2026-05-13 (hoy) | Attestation actualizada → coverage 7d | G6/G7 mejora observabilidad (no canonical aún) |
| 2026-05-21 | Re-check A8 SL_intra | Riesgo adicional SL_intra resuelto (si positivo) |
| 2026-06-01 | Bankroll Readiness Score puede cruzar 40% | G12 |
| 2026-06-08 | ≥28d cash flow coverage desde t0=2026-04-29 | ETA mínimo para B5+B6 (prerequisito G4/G6/G7) |
| 2026-06-09 | Cierre Phase 2 (T+30) | G11 (signals operativas activas vía L1 gate) |
| Post 2026-06-09 | Readout Phase 2 + Opus B5/B6 + Pablo signoff | G15 (decisión manual) |

**Ventana realista para revisión BANKROLL:** **no antes de 2026-06-09**, más tiempo de Opus B5/B6 (~1 semana). Fecha operativa más temprana plausible: **~2026-06-16**.

---

## 11. Estado snapshot (2026-05-13T19:13 UTC)

| Componente | Estado | Valor |
|---|---|---|
| bot_health_check | WATCH | v10.6.50, cycle #308, 2 min ago |
| phase1_readiness | exit_code=0 | ready=true, 117 cycles, 16d |
| SQLiteRecorder | Fresco | last write 6min, 0 gaps |
| bankroll_readiness_score | 38.4% (early) | WR D1=0, PnL D2=100, Edge D3=26.5, Size D4=26.3, Stability D5=41.9 |
| pnl_report 1W | provisional (non-canonical) | coverage 5d, divergence 24.36 (umbral 1.5) |
| pnl_report ALL | provisional, value=+$2.93 | coverage 11.4d, divergence 23.4 |
| pnl_report 1M | blocked | coverage 11.4d < 28d required |
| pnl_report 1D | blocked | snapshot_gap_gt_2h + cash_flow_coverage_below_1D |
| trade_lifecycle | contaminated | 122 trades, realized=-$20.47, contamination_rate=1.0 |
| wallet total | $22.83 | cash=$16.91, active_positions=$5.92 |
| cash_flows | 2 records, 5.0d coverage | gap desde 2026-05-11 → ACTION_NOW |
| bankroll_scaling_check | BLOCKED | hard blocker: pnl_source_non_canonical |
| SL_intra guard | Activo v10.6.40 | A8: ESPERAR_MÁS_MUESTRA (n=2) |
| Phase 2 | Abierta | T+30 = 2026-06-09 |
| BANKROLL | $25 | No autorizado $35 hasta post-2026-06-09 mínimo |

---

*Documento read-only. No implementa cambios. No promueve canonical_source. No autoriza BANKROLL ni Fase C.*  
*Fuente de verdad: herramientas Railway + docs canónicos del repo.*
