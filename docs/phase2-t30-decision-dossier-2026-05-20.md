# Phase 2 T+30 Decision Dossier

**Fecha dossier:** 2026-05-20 (T+10 de Phase 2)
**T+30 (cierre previsto):** 2026-06-09
**Elaborado por:** Sonnet — read-only, sin código, sin Railway writes
**Destino:** Opus — revisión estratégica al cierre de Phase 2

> **Nota de alcance:** Este dossier es docs-only/read-only.
> No autoriza cambios de código, env vars, city modes, Railway, BANKROLL,
> Fase C, sizing, whitelist, sigma, MIN_EDGE, Kelly, entries/exits, BUY/SELL/SKIP,
> DB writes ni trading core. No convierte alertas ni Traders Intelligence en señales
> ejecutables. No toca bot.py. No es output de Opus; es input para Opus.

---

## Estado Phase 2 (snapshot 2026-05-20)

| Campo | Valor |
|---|---|
| Estado | ABIERTA |
| Inicio | 2026-05-10 |
| T+30 cierre | 2026-06-09 |
| T+10 (hoy) | 2026-05-20 |
| Días restantes | 20 |
| Ciudades ACTIVE | Shanghai, Tokyo, Buenos Aires, Ankara |
| Ciudades BLOCKED | London, Paris, Atlanta, Chicago |
| Condición | mixed: exact (vía QUALITY_TRADER_CONDITIONS) + at_or_above/at_or_below (ALLOWED_CONDITIONS default) |
| Monitor runtime | `maybe_run_phase2_monitor` v10.6.50 — rolling diario |
| Kill-switch mixed | WR<40% n≥20 → alarma rollback |
| Kill-switch exact | WR<40% n≥10 → vaciar QUALITY_TRADER_CONDITIONS |
| BANKROLL | $25 (firmado) |
| Fase C | no autorizada |

**Exclusión documentada:** Paris #304 (`Paris 14°C May13 NO`, token 9054...198) es trade contaminado pre-S347 y queda excluido de la cohorte T+30 (S357).

**Fuente de datos local:** `data/runtime_import/trade_lifecycle.json` generado `2026-05-13T20:18:21Z` (T+3 de Phase 2 — stale). La fuente canónica de Phase 2 es Railway `/app/data`. No se ejecutó SSH en esta sesión.

---

## 1. Calibration Gap Report

### Contexto del modelo de calibración

- Sigma global por defecto: `EMPIRICAL_SIGMA_GLOBAL = {D0:2.0, D1:1.9, D2:2.5, D3:3.0}` (bot.py:20556)
- Sigma empírica por ciudad activa en `EMPIRICAL_SIGMA`: solo Buenos Aires D0 (1.10, n=3) — umbral mínimo de 3 muestras recién alcanzado
- Corrección de sesgo `FORECAST_BIAS_C`: solo Atlanta(+1.38°C), Chicago(+1.40°C), Dallas(0.0°C) — ninguna ciudad active de Phase 2 tiene entrada
- Definición de forecast_error: `forecast_max − observed_real` (negativo = Open-Meteo subestima)

### 1.1 Shanghai

| Campo | Valor |
|---|---|
| Modo actual | ACTIVE (desde 2026-05-10) |
| Fuente (source fidelity) | SOURCE_MATCH_CONFIRMED — WU/ZSPD (S356) |
| RESOLUTION_ICAO | ZSPD |
| n Phase 2 cerrados (local T+3) | 0 (muestra insuficiente — solo hasta May13) |
| WR Phase 2 | MISSING EVIDENCE (necesita Railway SSH) |
| n total histórico local | 8 cerrados |
| WR histórico (local, todos) | 62.5% (5/8 con pnl no-null) |
| PnL histórico local | +$4.21 (no canónico, stale) |
| Close reasons históricos | stop_loss ×3, take_profit_intra ×2, market_resolved_yes ×2, market_resolved ×1 |
| micro_position_unsellable | 0/8 (0%) |
| sigma D0 activa | 2.0 (GLOBAL — sin empírica) |
| sigma D1 activa | 1.9 (GLOBAL — sin empírica) |
| Bias (FORECAST_BIAS_C) | NONE — no hay entrada para Shanghai |
| MAE/error forecast histórico | MISSING EVIDENCE — Shanghai no aparece en forecast_accuracy_raw.json |
| observed_vs_forecast entries | MISSING — sin observed_audit local post-Phase2 |
| **Hipótesis operativa** | **Muestra insuficiente.** 0 trades Phase 2 en snapshot local. Sin calibración empírica en ningún horizonte. Sin corrección de bias (Open-Meteo vs WU no cuantificado para esta ciudad). El modelo usa sigma global sin evidencia de que sea apropiado para Shanghai. No concluyente — requiere Railway data. |

### 1.2 Tokyo

| Campo | Valor |
|---|---|
| Modo actual | ACTIVE (desde 2026-05-10) |
| Fuente (source fidelity) | SOURCE_MATCH_CONFIRMED — WU/RJTT (S356) |
| RESOLUTION_ICAO | RJTT |
| n Phase 2 cerrados (local T+3) | 1 (Tokyo 25°C May11 NO, at_or_above) |
| WR Phase 2 (local) | 1/1 = 100% — n insuficiente para decisión |
| PnL Phase 2 (local) | +$2.32 (take_profit_intra) |
| n total histórico local | 6 cerrados |
| WR histórico (local, todos) | 100% (4/5 scored, 1 unsellable excluido) |
| PnL histórico local | +$7.00 (no canónico, stale) |
| Close reasons históricos | take_profit ×1, take_profit_intra ×2, market_resolved_yes ×2, micro_position_unsellable ×1 |
| micro_position_unsellable | 1/6 (17%) — Apr5 NO |
| sigma D0 activa | 2.0 (GLOBAL — sin empírica) |
| sigma D1 activa | 1.9 (GLOBAL — sin empírica) |
| Bias (FORECAST_BIAS_C) | NONE — no hay entrada para Tokyo |
| MAE/error forecast histórico | n=1 en forecast_accuracy_raw.json (Apr4): forecast_error=-0.4°C — muestra inútil |
| observed_vs_forecast entries | MISSING — sin observed_audit local post-Phase2 |
| **Hipótesis operativa** | **Muestra insuficiente** (n Phase 2 = 1). WR histórica alta (100%) pero n muy pequeño. Sin calibración empírica ni corrección de sesgo. El único dato de forecast_error (n=1) no es accionable. Candidato observacional positivo (P7: WR=80%, n=5, +$3.53 antes de Phase 2) pero sin evidencia suficiente para calibrar ciudad. No concluyente — requiere Railway data. |

### 1.3 Buenos Aires

| Campo | Valor |
|---|---|
| Modo actual | ACTIVE (desde 2026-05-10) |
| Fuente (source fidelity) | SOURCE_MATCH_CONFIRMED — WU/SAEZ (S356) |
| RESOLUTION_ICAO | SAEZ |
| n Phase 2 cerrados (local T+3) | 0 (muestra insuficiente — stale) |
| WR Phase 2 | MISSING EVIDENCE (necesita Railway SSH) |
| n total histórico local | 5 cerrados |
| WR histórico (local) | 100% (3/4 scored, 1 unsellable excluido) |
| PnL histórico local | +$5.78 (no canónico) |
| Close reasons históricos | market_resolved_yes ×2, take_profit ×1, market_resolved ×1, micro_position_unsellable ×1 |
| micro_position_unsellable | 1/5 (20%) |
| sigma D0 activa | **1.10 (EMPÍRICA — n=3, umbral mínimo justo alcanzado)** |
| sigma D1 activa | 1.9 (GLOBAL — sin empírica) |
| Bias (FORECAST_BIAS_C) | NONE — no hay entrada para Buenos Aires |
| MAE/error forecast histórico | `forecast_error_mean = -2.07°C` (n=3, std=1.097°C) — Open-Meteo subestima temperatura real en ~2°C |
| observed_vs_forecast entries | Parcial (n=3 en forecast_accuracy_raw.json Apr4) — muestra aún insuficiente |
| **Hipótesis operativa** | **Calibración insuficiente con señal de alerta.** `forecast_error_mean=-2.07°C` con n=3 indica sesgo de Open-Meteo hacia frío. Sin corrección en FORECAST_BIAS_C, el modelo estima probabilidades subestimando la temperatura real. Sigma D0=1.10 empírica pero con n exactamente en umbral mínimo (n=3); una observación más podría cambiarla. Este es el gap calibración más concreto de las 4 ciudades activas. |

### 1.4 Ankara

| Campo | Valor |
|---|---|
| Modo actual | ACTIVE (desde 2026-05-10) |
| Fuente (source fidelity) | SOURCE_MATCH_CONFIRMED — WU/LTAC (S356) |
| RESOLUTION_ICAO | LTAC |
| n Phase 2 cerrados (local T+3) | 0 (último trade Mar29 — muestra muy antigua) |
| WR Phase 2 | MISSING EVIDENCE |
| n total histórico local | 5 cerrados |
| WR histórico (local) | 60% (3/5 scored) |
| PnL histórico local | no canónico |
| Close reasons históricos | stop_loss ×1, take_profit ×1, market_resolved ×2, micro_position_unsellable ×1 |
| micro_position_unsellable | 1/5 (20%) |
| sigma D0 activa | 2.0 (GLOBAL — sin empírica) |
| sigma D1 activa | 1.9 (GLOBAL — sin empírica) |
| Bias (FORECAST_BIAS_C) | NONE — no hay entrada para Ankara |
| MAE/error forecast histórico | `forecast_error_mean = -0.95°C` (n=2, std=0.071°C) — Open-Meteo subestima ~1°C |
| observed_vs_forecast entries | n=2 (insuficiente para acción) |
| **Hipótesis operativa** | **Muestra insuficiente + señal de sesgo incipiente.** n=2 histórico no es accionable. Sin Phase 2 trades en local snapshot; posiblemente sin trades Phase 2 reales también dada la ventana de mercados Ankara. El sesgo de -0.95°C es plausible pero necesita n≥5 para ser concluyente. No concluyente — requiere Railway data. |

### Resumen calibración

| Ciudad | n Phase 2 (local) | sigma activa | Bias corregido | MAE evidencia | Gap principal |
|---|---|---|---|---|---|
| Shanghai | 0 (stale) | Global D0=2.0 | ❌ | MISSING | Muestra insuficiente |
| Tokyo | 1 (n<<25) | Global D0=2.0 | ❌ | n=1 (inútil) | Muestra insuficiente |
| Buenos Aires | 0 (stale) | **Empírica D0=1.10 (n=3)** | ❌ | **-2.07°C n=3** | **Sesgo real sin corregir** |
| Ankara | 0 (stale) | Global D0=2.0 | ❌ | -0.95°C n=2 | Muestra insuficiente |

---

## 2. Execution Gap Report

### 2.1 PRICE_AGGRESSION

- Valor hardcoded: `PRICE_AGGRESSION = 0.02` (bot.py:480)
- No override por env var
- Efecto: `aggressive_price = min(market_price + 0.02, 0.99)` para órdenes limit GTC
- En mercados thin, el bot licita 2pp sobre el mid. No hay evidencia de que este valor sea subóptimo por sí solo, pero tampoco hay tracking de slippage real vs fill price.
- **MISSING EVIDENCE:** No existe tracking de `execution_price` vs `aggressive_price` en los datos locales. `price_raw` está disponible para forensics (Unsellable Guard v1 S281) pero no hay serie histórica de discrepancia.

### 2.2 Modo de orden: GTC vs FOK

- **Configuración actual:** órdenes GTC limit (CONTEXTO.md: "Órdenes GTC limit, registra en performance.json")
- `ORDER_MAX_AGE_HOURS = 8` — las órdenes no llenadas en 8h se cancelan en el siguiente ciclo de mantenimiento
- **Implicación en thin liquidity:**
  - GTC: la orden queda abierta hasta fill o cancelación. En mercados thin, puede resultar en fill a precio stale si la orderbook se mueve.
  - FOK (Fill-or-Kill): llena completo o cancela inmediatamente. Elimina stale exposure pero puede aumentar la tasa de no-fill en mercados thin.
- **Trade-off abierto (no recomendación ejecutable):** ¿Vale la pena implementar un modo FOK para mercados donde la orderbook depth ≤ `desired_size`? Esto requeriría orderbook precheck antes de emitir la orden.
- **MISSING EVIDENCE:** No hay datos de orderbook depth en el momento del BUY en trade_lifecycle.json.

### 2.3 micro_position_unsellable

**Tasa histórica global:** 48% de cierres (29/61) eran `micro_position_unsellable` en la era pre-Phase2 (HISTORIAL S161-era). Este número incluía la disfunción mayor (exact/range) que fue corregida con S341/kill-switch.

**Tasa por ciudad active (local snapshot, todos los tiempos):**

| Ciudad | micro_position_unsellable | Total cerrados |
|---|---|---|
| Shanghai | 0/8 (0%) | 8 |
| Tokyo | 1/6 (17%) | 6 |
| Buenos Aires | 1/5 (20%) | 5 |
| Ankara | 1/5 (20%) | 5 |

**Unsellable Guard v1 (S281, S282):**
- `UNSELLABLE_GUARD_ENABLED = 0` (dormido por defecto)
- `UNSELLABLE_GUARD_LOG_ONLY = 1`
- Trigger: `condition in {exact, range}`, `days_ahead==0`, `price 0.10–0.65`, `size_ratio≥0.15`
- Estado actual: LOG_ONLY capturando candidatos, pero sin enforcement
- Veredicto previo (Opus S281): `APPROVE_WITH_ADJUSTMENTS / Fase 1 LOG_ONLY`

**Paris #304 (May13, excluded):** micro_position_unsellable, pnl=-$2.19 — confirma que el problema persiste en conditions de thin-market.

### 2.4 buy_min_notional / buy_min_size

- `ORDER_MIN_NOTIONAL = float(os.getenv("ORDER_MIN_NOTIONAL", "1.00"))` — mínimo de exposición por trade
- S207 implementó retry logic (`v10.6.23`) para el error Polymarket `"Size lower than minimum: 5"` — riesgo de buy_min_size reducido post-fix
- `EXACT_RANGE_MIN_AMOUNT = 2.50` — suelo para exact/range canary (S206) para evitar posiciones microscópicas
- **Residual no-crítico:** `buy_min_notional` y `buy_min_size` aún aparecen en alerts state como benignos no-recurrentes (S283 confirmó que no disparan alerta en condiciones normales de slot 04h)

### 2.5 Slippage y bid-ask spread

- **MISSING EVIDENCE:** No hay tracking de bid-ask spread ni datos de orderbook depth en los artefactos locales.
- Los `market_observations` en trade_lifecycle.json incluyen `liquidity` y `volume_24h` por market, pero no capturan la granularidad del orderbook en el momento del BUY.
- Ejemplo de data disponible: Shanghai 24°C May9 tenía `liquidity: 569–39088 USDC` en distintos snapshots — varianza alta indica mercado thin en ciertas ventanas.

### Resumen ejecución

| Gap | Estado | Evidencia disponible | Severidad |
|---|---|---|---|
| PRICE_AGGRESSION=0.02 | Hardcoded, sin override | Sin tracking fill vs price | WATCH — no accionable sin datos |
| GTC vs FOK | GTC activo | Sin orderbook depth data | DESIGN_PENDING — trade-off no evaluado |
| micro_position_unsellable | Guard dormido (LOG_ONLY) | 0–20% por active city | WATCHABLE — Opus decide enforcement |
| buy_min_size | Fixed en v10.6.23 | Benignos no-recurrentes (S283) | OK |
| Slippage/spread | Sin tracking | Sin evidencia local | MISSING EVIDENCE |

---

## 3. Decision Questions for Opus T+30

Preguntas binarias para revisión Opus el 2026-06-09 (o antes si se activa kill-switch):

**A. Modelo / Calibración**
1. ¿Mantener sigma global ({D0:2.0, D1:1.9}) para Shanghai, Tokyo, Ankara, o iniciar calibración empírica por ciudad vía colección de observed_vs_forecast?
2. ¿Agregar Buenos Aires a `FORECAST_BIAS_C` con valor provisional (-2.07°C, n=3) antes de T+30, o esperar n≥5?
3. ¿Agregar Ankara a `FORECAST_BIAS_C` con valor provisional (-0.95°C, n=2), o esperar n≥5?
4. ¿Subir MIN_EDGE por ciudad para compensar sesgo no corregido en Buenos Aires/Ankara, o no actuar hasta calibración completa?

**B. Resultado Phase 2**
5. ¿Phase 2 alcanzó n≥25 mixed-condition cerrados al T+30? (Si no → `RECOMMEND_KILL_MODEL_PATH`)
6. ¿Al menos 2 de 4 ciudades tienen n≥3 y WR≥40%? (Criterio Opus S342)
7. ¿El slice exact aislado alcanzó n≥10 y WR≥45%? (Criterio Opus S342)

**C. Ejecución**
8. ¿Pasar UNSELLABLE_GUARD de LOG_ONLY a enforcement (`UNSELLABLE_GUARD_ENABLED=1`)? Prerequisito: readout de candidatos acumulados post-Phase2.
9. ¿Diseñar orderbook depth precheck antes de BUY para mercados thin? ¿Con qué umbral de liquidez mínima?
10. ¿Evaluar FOK como alternativa a GTC para mercados con `liquidity < threshold`?

**D. Estrategia general**
11. ¿Mantener las 4 ciudades ACTIVE o reducir a 2 ciudades con mayor throughput para acumular n más rápido?
12. ¿Kill/pivot de todo el path modelo si T+30 no alcanza ningún gate?

---

## 4. Stop Criteria — Qué falta para decidir al T+30

| Evidencia faltante | Por qué no está disponible ahora | Trigger para obtenerla |
|---|---|---|
| Phase 2 WR/n por ciudad (Railway) | Local snapshot stale (T+3) | Railway SSH `cat /app/data/trade_lifecycle.json` antes de 2026-06-09 |
| Phase 2 exact slice WR | Ídem | Ídem |
| bot_signal_evaluations.jsonl efectivo | Activado hoy (S371 READ_BOT_EVAL_CAPTURE=1); no observado aún | Verificar `tail /app/data/blocked_signals_resolutions.jsonl` post-ciclo 16:00 UTC |
| Unsellable Guard candidatos acumulados | Guard dormido LOG_ONLY; datos en `/app/data/skip_log.jsonl` Railway | SSH + `tools/unsellable_guard_monitor.py` |
| MAE/forecast_error Shanghai | No en forecast_accuracy_raw.json; sin observed_audit NOAA para Shanghai | Requires n≥3 observed_vs_forecast entries para Shanghai post-T+10 |
| MAE/forecast_error Tokyo (n útil) | n=1 actual — inútil | Requiere n≥3 |
| Confirmación Buenos Aires bias (n≥5) | n=3 actual en el umbral mínimo | 2+ trades cerrados adicionales con MAE medido |
| Evidencia Ankara bias (n≥5) | n=2 actual | 3+ trades cerrados con MAE medido |
| Kill-switch Phase 2 activado o no | Desconocido sin Railway | Railway SSH `/app/data/alerts_state.json` o Telegram alerts |

**Trigger mínimo para que Opus decida al T+30:** Railway SSH para obtener (1) trade_lifecycle.json actualizado a T+30, (2) unsellable_guard skip_log candidatos, y (3) estado del Phase2 monitor. Sin eso, la decisión es `INSUFFICIENT_EVIDENCE`.

---

## 5. Cierre

**Clasificación de sesión:** DOCS_ONLY / READ_ONLY / DOSSIER_PHASE2_T30

**Archivos leídos:**
- `CONTEXTO.md` (grep puntual — Phase 2, sigma, PRICE_AGGRESSION, unsellable, active cities)
- `AGENTS.md`
- `bot.py` (grep: EMPIRICAL_SIGMA, FORECAST_BIAS_C, PRICE_AGGRESSION, UNSELLABLE_GUARD)
- `data/runtime_import/trade_lifecycle.json` (generado 2026-05-13 — stale)
- `data/forecast_accuracy_raw.json` (generado 2026-04-04 — muy stale)
- `docs/post-phase2-strategy-experiments-2026-05-13.md`
- `docs/source_audits/active_cities_source_fidelity_audit.md`

**Archivos creados:**
- `docs/phase2-t30-decision-dossier-2026-05-20.md` (este archivo)

**Archivos modificados:** ninguno

**Commit/push:** no — docs-only, sin estado vivo. Aplicar cierre LITE si se decide committing.

**Confirmaciones explícitas:**
- ✅ No se tocó código
- ✅ No se tocó DB
- ✅ No se ejecutó Railway (ni writes ni SSH)
- ✅ No se modificaron env vars
- ✅ No se tocó BANKROLL
- ✅ No se tocó bot.py
- ✅ No se tocó trading core
- ✅ No se tocó Fase C
- ✅ No se tocó sigma, MIN_EDGE, Kelly, sizing, exits, scheduler, NOAA, whitelist, city modes
- ✅ No se activaron señales de Traders Intelligence como ejecutables

---

## Addendum T+30 — Cierre Phase 2 (2026-06-09, Sesión 422)

**Fecha de cierre:** 2026-06-09
**Adjudicado por:** Fable (lectura Railway SSH read-only: trade_lifecycle.json, cycles_history.jsonl tail, funnel_observability_log_only.jsonl tail)
**Veredicto:** `STOP_CURRENT_LINE / PHASE2_CLOSED_FAIL_B6_ZERO_THROUGHPUT_TAIL`

### Readout ventana 2026-05-10 → 2026-06-09

| Campo | Valor |
|---|---|
| Filas trade_lifecycle | 37 (36 con PnL) |
| B5 (n >= 25) | **PASS** — n=36 |
| WR global | 47.2% (17W / 19L) |
| P&L no canónico bruto | +$2.11 |
| Outlier Wellington | +$19.05 |
| P&L ex-outlier | **-$16.94** |
| B6 (≥2 ciudades n>=3 WR>=40%) | **FAIL** |
| Tokyo Phase 2 | n=3, WR>=40% (único PASS) |
| Shanghai Phase 2 | n=0/3 WR>=40% (FAIL) |
| Buenos Aires Phase 2 | n=0 (FAIL) |
| Ankara Phase 2 | n=0 (FAIL) |
| Trades de ciudades ACTIVE | 6/37 (16%) |
| Fuente real del flujo | canary/auto-canary (Munich, Singapore, Seoul, Wellington) |
| Trades exact/NO | ~62% — bloqueados por SHADOW_EXACT_NO_GLOBAL |
| micro_position_unsellable | 11 cierres = -$22.77 (~60% pérdidas brutas) |
| Trades desde 2026-05-26 | 0 |

### Funnel diagnóstico (ciclos 497-499, 2026-06-09)

| Paso | Valor |
|---|---|
| discovered | 330 |
| city_window | ~250 |
| price_out_of_range | 50-86 |
| condition_filtered | mata 100% de los evaluados |
| with_edge | **0** |

**Diagnóstico estructural:** la superficie operable de la policy actual está vacía. El catálogo weather actual es casi todo exact/range; directional apenas existe; exact requiere QT match; exact/NO está bloqueado por SHADOW_EXACT_NO_GLOBAL.

### Decisión

`STOP_CURRENT_LINE`. No rediseñar policy para forzar throughput sobre un modelo con evidencia congelada negativa.

**Descartado explícitamente (mientras flujo=0):**
- Recalibración sigma/bias
- Rotación ciudades
- FOK/orderbook depth
- Unsellable Guard enforcement
- Camino B Forecast Autopsy
- Más observabilidad

**Deferrido (cosmético, sin efecto P&L):**
- Cleanup BA/Ankara de ACTIVE — requiere env var/FULL + confirmación Pablo

### Invariantes confirmados

| Invariante | Estado |
|---|---|
| BANKROLL | HOLD $25 |
| $35 | No autorizado |
| Fase C | No autorizada |
| BUY/SELL/SKIP | Sin cambio |
| City modes | Sin cambio |
| Env vars / Railway | Sin cambio |
| bot.py | No tocado |

### Triggers de reapertura

| Trigger | Condición | Check |
|---|---|---|
| A — Trader-following | Celda forward n>=10 **y** top1<=50% en `tools/trader_benchmark.py` sobre BSR fresco | 2026-06-23 (natural); celda cercana: `>=80\|trader_NO\|no` forward n=47 WR=100% top1=55.3% |
| B — Forecast path | E2 L1 `forward_holdout n>=30` en alguna cohorte | Sin fecha fija |
| C — exact/NO | Criterio S418: n_closed_calibration_unique>=10, wr>=0.60, calibration_gap<=0.10, pnl_sim_unit>0 | Sin fecha fija |

### Siguiente acción

Ninguna hasta 2026-06-23. Si `tools/trader_benchmark.py` (rerun sobre BSR fresco) encuentra alguna celda con `n>=10 && top1<=50%`, abrir sesión Opus para diseñar experimento trader-following LOG_ONLY. Si no, siguiente check +14d sin sesión intermedia.
