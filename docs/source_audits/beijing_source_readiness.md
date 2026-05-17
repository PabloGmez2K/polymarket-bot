# Beijing — Source Readiness Dossier

**Generated:** 2026-05-17  
**Mode:** Sonnet read-only / docs-only  
**Authority:** No operational action. No code patch. No env/whitelist/policy change.  
**Source data:** Blocked Signals audit 2026-05-17 (Railway live); `data/runtime_import/shadow_city_tracking.json`; `data/runtime_import_derived/blocked_signals_resolutions.jsonl`; `bot.py` RESOLUTION_ICAO + OBSERVED_AUDIT_CITIES (v10.6.40); `tools/forecast_accuracy_audit.py` ICAO_ONLY_PROXY_AUDIT_CITIES.  
**Verdict:** **BLOCKED_BY_MEASUREMENT_LAYER** — source text is confirmed WU/ZBAA, but source parity fails. The general parity dossier
`docs/source_audits/beijing_open_meteo_vs_wu_parity.md` reproduces
`SETTLEMENT_GAMMA_PARITY_FAIL` with median `|delta|=1.05C`, max `|delta|=3.0C`,
and `58.3%` of Gamma-derived exact settlement dates at `|delta| >= 1C`.
Exact-market promotion review is gated until source parity passes.

---

## 1. Estado Actual de Beijing

| Campo | Valor |
|---|---|
| city_mode | shadow (auto-canary revocado 2026-04-26) |
| city_policy | OBSERVED_AUDIT |
| shadow_cycles | 42 (snapshot 2026-05-13) |
| edge_hits | 5 |
| best_edge_pct | 37.9% |
| best_ev | 2.99 |
| first_seen_at | 2026-04-02 |
| last_seen_at | 2026-05-13 |
| markets_seen | 90 |
| blocked_signals OUT whitelist (Railway 2026-05-17) | **n=11, WR=100%** |
| blocked_signals local (data/runtime_import_derived/) | n=2 (subset local, no completo) |
| condition types | **exact only** |
| traders dominantes | Entire-Hood, Thrifty-Original, Dimpled-Boy |
| avg_price_entered (muestra local) | 0.42–0.47 |
| settlement_source | **WU ZBAA** — `https://www.wunderground.com/history/daily/cn/beijing/ZBAA` (Gamma audit 2026-05-17) |
| fidelity | **SOURCE_TEXT_CONFIRMED_WU_ZBAA** — Gamma description explicit, Celsius entero, mapping match |
| observed_coverage | icao_only (open-meteo proxy) |
| whitelist (QUALITY_TRADER_CITIES_WHITELIST) | **Ausente** |
| active trading | No — cero BUY real |
| ICAO_ONLY_PROXY_AUDIT_CITIES | Sí — `("Lucknow", "Beijing")` en `forecast_accuracy_audit.py:32` |

**Historial de modo:**
- 2026-04-26T16:48: auto-promoted shadow → canary (5 edges, 20 ciclos, pico 37.9%)
- 2026-04-26T17:30: auto_canary_revocado → shadow ("ICAO-only observation via proxy: auto-canary blocked until manual review")
- Estado actual: shadow, bloqueado de auto-canary por `_city_requires_manual_proxy_canary_review()`

**Nota sobre n=11 Railway vs n=2 local:**  
Los 2 registros locales en `blocked_signals_resolutions.jsonl` son los únicos sincronizados al snapshot local (ambos 2026-04-18, ambos Entire-Hood, WR=100%). El dato n=11 WR=100% proviene del Blocked Signals audit 2026-05-17 sobre Railway live — es la fuente autorizada.

---

## 2. Source / Settlement

| Dimensión | Estado | Detalle |
|---|---|---|
| ICAO | **ZBAA** (Beijing Capital) — confirmado | `bot.py:16353` RESOLUTION_STATIONS; `bot.py:16419` RESOLUTION_ICAO |
| WU URL | **Definida** — `_wu_history_url("ZBAA")` | `bot.py:16419`: `{"icao": "ZBAA", "wu_url": _wu_history_url("ZBAA")}` |
| noaa_station_id | **Ausente** | `bot.py:16419` — no tiene `noaa_station_id` ni `noaa_daily_station_id` |
| noaa ISD | ISD 54511099999 confirmado (GHCND sin TMAX 2025-10→2026-03) | Comentario `bot.py:16461` — mismo patrón que Toronto/HK/Singapore |
| Open-Meteo proxy | **Activo** — lat 40.0799, lon 116.6031, "Beijing Capital" | `bot.py:16353` coords; `forecast_accuracy_audit.py:32` ICAO_ONLY_PROXY_AUDIT_CITIES |
| source_texts (mercados) | **WU ZBAA confirmado** | Gamma audit 2026-05-17: `resolutionSource=https://www.wunderground.com/history/daily/cn/beijing/ZBAA`; description explícita: "Beijing Capital International Airport Station", Celsius entero; sin "unknown", sin "polymarket_market_price" |
| settlement_source | **WU ZBAA** | Confirmado vía Gamma — dos mercados auditados (market_id 1996577, 1996578), idéntica fuente |
| fidelity | **SOURCE_TEXT_CONFIRMED_WU_ZBAA** | Gamma URL == bot.py `_wu_history_url("ZBAA")` — match exacto |
| Riesgo de mismatch | **Bajo** | Source confirmada y alineada con mapping interno; riesgo estructural resuelto |

**Situación vs Jeddah:**  
Jeddah tiene `OEJN` en RESOLUTION_STATIONS con WU URL definida, y el scanner v0.2 confirmó `source_texts=["polymarket_market_price"]`. Beijing tiene `ZBAA` con WU URL también definida — y el **Gamma audit directo 2026-05-17** confirmó `resolutionSource=https://www.wunderground.com/history/daily/cn/beijing/ZBAA` en dos mercados resueltos. A diferencia de Jeddah (que obtuvo source via scanner sobre blocked_signals), Beijing obtuvo su confirmación via Gamma API directa (el scanner la excluía como `observed_audit`). El resultado es equivalente: source WU/ICAO confirmada, sin "unknown". **La brecha con Jeddah ya no es de source — ambas ciudades esperan decisión Opus sobre el path WU/ICAO.**

**¿Por qué no es inmediatamente accionable?**  
El camino WU-ZBAA existe estructuralmente en `bot.py`, pero `bot.py:5497` exige `interpretable = noaa_configured AND observed >= MIN_SAMPLE`. Sin `noaa_station_id`, `noaa_configured=False`. La única vía habilitada actualmente es ICAO-only via open-meteo proxy — modo de *observación*, no de *trading*.

---

## 3. Gamma Audit 2026-05-17

**Método:** Gamma API directa — `GET gamma-api.polymarket.com/markets/slug/{slug}`. Read-only. Sin código nuevo. Sin cambios a bot.py, tools, env, ni datos operativos.  
**Autoridad:** Informativo / docs-only. No autoriza trading, whitelist, city mode change, BANKROLL, ni Fase C.

### Mercados auditados

| Campo | Mercado 1 | Mercado 2 |
|---|---|---|
| **Pregunta** | Will the highest temperature in Beijing be 27°C on April 18? | Will the highest temperature in Beijing be 26°C on April 18? |
| **slug** | `highest-temperature-in-beijing-on-april-18-2026-27c` | `highest-temperature-in-beijing-on-april-18-2026-26c` |
| **market_id** | 1996578 | 1996577 |
| **conditionId** | `0xa08019...e452e8eb` | `0x5b656a...6c3d3ed` |
| **endDate** | 2026-04-18T12:00:00Z | 2026-04-18T12:00:00Z |
| **condition (blocked)** | exact | exact |
| **trader (blocked)** | Entire-Hood | Entire-Hood |
| **outcome** | Yes — win_for_trader=true | No — win_for_trader=true |
| **resolutionSource** | `https://www.wunderground.com/history/daily/cn/beijing/ZBAA` | `https://www.wunderground.com/history/daily/cn/beijing/ZBAA` |

### Source text (description Gamma — idéntico en ambos mercados)

> "The resolution source for this market will be information from Wunderground, specifically the highest temperature recorded for all times on this day by the **Beijing Capital International Airport Station** once information is finalized, available here: `https://www.wunderground.com/history/daily/cn/beijing/ZBAA`."
>
> "The resolution source for this market measures temperatures to **whole degrees Celsius**."

### Comparación con mapping interno

| Dimensión | Gamma (real) | bot.py interno |
|---|---|---|
| Fuente | Weather Underground | `_wu_history_url("ZBAA")` |
| URL | `https://www.wunderground.com/history/daily/cn/beijing/ZBAA` | idéntica |
| Estación | Beijing Capital International Airport Station | ZBAA |
| Unidad | Celsius entero | Celsius |
| "unknown" presente | No | — |
| "polymarket_market_price" | No | — |
| **Veredicto** | **SOURCE_TEXT_CONFIRMED_WU_ZBAA** | **MATCH EXACTO** |

---

## 4. Señal Trader

| Dimensión | Valor | Interpretación |
|---|---|---|
| blocked_signals WR (Railway) | **100%** n=11 | Muy fuerte — source confirmada WU/ZBAA |
| blocked_signals WR (local n=2) | 100% | Consistent; muestra insuficiente localmente |
| condition | **exact only** | No hay range ni at_or_below en la muestra de blocked |
| traders | Entire-Hood (hist_wr=80%), Thrifty-Original (hist_wr=80.5%), Dimpled-Boy (hist_wr=81.0%) | Tres traders de alta WR histórica, todos presentes en otras ciudades activas |
| shadow edge_hits | 5 en 42 ciclos | edge_hits/cycles = 0.12 — baja densidad de hits vs shadow ciclos altos |
| best_edge_pct | 37.9% | Señal decente cuando aparece |
| best_ev | 2.99 | EV positivo confirmado en shadow |
| avg_price_entered (local) | 0.42–0.47 | No trivial — mercados competitivos, no fáciles |
| consensus (local sample) | `has_consensus=False` en ambos registros locales | Sin consenso entre múltiples traders en los 2 casos visibles |
| signals_crosscheck directo | **0 señales Beijing** | No hay señales directas — toda la evidencia viene vía blocked_signals_resolutions |

**¿Early/edge o late/market-informed?**  
La muestra local (n=2) muestra avg_price 0.42–0.47 — rango de mercado activo, no de early entry barato. Dado que los mercados de exact temperature en Beijing típicamente tienen 2–3 opciones simultáneas (34°C, 35°C, 36°C), los precios observados en shadow (market_price=56–75%) son coherentes con mercados maduros, no con alpha pre-information. Esto no descarta el alpha del trader, pero sugiere que no es un simple trade de precio obvio.

**¿Basta para justificar Opus review?**  
**Sí.** WR=100% n=11, tres traders de calidad, shadow activo con edge real (best 37.9%), source confirmada WU/ZBAA — la señal es suficiente para solicitar Opus review sobre el path WU/ICAO. No autoriza trading ni whitelist.

---

## 5. Comparación con Jeddah

| Dimensión | Jeddah (dossier 2026-05-17) | Beijing (este dossier) |
|---|---|---|
| Veredicto | **NOT_READY_WAIT_SHADOW** | **READY_FOR_OPUS_SOURCE_REVIEW** |
| Blocker primario | shadow_cycles < 10 (ciclos = 6–7) | Opus review C10/C11 pendiente |
| Blocker secundario | Opus path decision (ICAO-only/WU aceptable?) | noaa_station_id ausente (mismo patrón; no bloquea WU path) |
| ICAO | OEJN — en RESOLUTION_STATIONS + WU URL | ZBAA — en RESOLUTION_STATIONS + WU URL |
| WU URL | Definida | Definida |
| noaa_station_id | Ausente (mismo problema) | Ausente (mismo problema) |
| Scanner v0.2 corrido | **Sí** — run 2026-05-15 | **No** — excluida como observed_audit; compensado con Gamma API directo |
| source_texts confirmado | `["polymarket_market_price"]` — single, limpio | **WU ZBAA** — Gamma audit 2026-05-17 (market_id 1996577, 1996578) |
| Whitelist | Sí — en QUALITY_TRADER_CITIES_WHITELIST | **No** — ausente |
| shadow_cycles | 6–7 | **42** — muy maduro |
| edge_hits | 4–5 | 5 |
| edge_hits / cycles ratio | ~0.67 — alta densidad | ~0.12 — baja densidad en shadow |
| blocked_signals WR | n=8 WR=87.5% | **n=11 WR=100%** |
| city_mode | shadow | shadow (auto-canary revocado) |
| Observed audit coverage | ICAO-only proxy | ICAO-only proxy (open-meteo) |
| Traders dominantes | General traders | Entire-Hood, Thrifty-Original, Dimpled-Boy |

**Lo que desbloquea a cada una:**

- **Jeddah:** acumular shadow_cycles (necesita ~3–4 más hasta n≥10) + Opus decidir si ICAO-only/WU es path aceptable. Source ya parcialmente conocida.  
- **Beijing:** Gamma audit completo (2026-05-17). Source confirmada WU ZBAA. Espera **Opus review** sobre path WU/ICAO y decisión de siguiente paso operativo.

Beijing no está esperando ni shadow ni source audit — ambos están met. Está esperando **decisión Opus**.

---

## 6. Criterios para READY_FOR_OPUS_SOURCE_REVIEW

Para pasar de `SOURCE_AUDIT_NEEDED` a revisión Opus accionable — estado actualizado post Gamma audit 2026-05-17:

| # | Criterio | Estado | Notas |
|---|---|---|---|
| C1 | Source text identificada (Gamma audit) | **MET** | Gamma audit 2026-05-17: `resolutionSource=WU ZBAA` en market_id 1996577 y 1996578 |
| C2 | settlement_source verificable | **MET** | WU ZBAA confirmado — sin ambigüedad, sin "unknown", sin precio interno |
| C3 | Mapping reproducible (ICAO ZBAA → WU URL → dato resuelto) | **MET** | URL Gamma == `_wu_history_url("ZBAA")` en bot.py — match exacto sobre mercados resueltos reales |
| C4 | source_texts sin "unknown" | **MET** | No aparece "unknown" ni "polymarket_market_price" en Gamma description |
| C5 | Shadow/blocked signal suficiente | **MET** | shadow_cycles=42, edge_hits=5, best_edge=37.9%, blocked n=11 WR=100% |
| C6 | noaa_station_id resuelto (para path NOAA) | **BLOQUEADO** | ISD 54511099999 existe pero GHCND sin TMAX 2025-10→2026-03. Bloquea path NOAA. **No bloquea path WU/ICAO** — Opus decide |
| C7 | Sin drift reciente | **DESCONOCIDO** | No monitoreado activamente; shadow filtra (last_side=FILTERED en ciclos recientes) |
| C8 | Sin policy conflict | **MET** | No en whitelist, no en canary/active — clean slate |
| C9 | No risk blocker | **MET** | LOG_ONLY / shadow, sin exposición real |
| C10 | Opus confirma si WU ZBAA es path aceptable para promotion review | **PENDIENTE** | Mismo decision point que Jeddah C10 — base técnica ya disponible |
| C11 | Opus review antes de cualquier promotion | **PENDIENTE** | **Gate activo** — nada procede sin review Opus explícita |

**Gate actual:** C1–C5, C8, C9 met. C6 bloquea solo el path NOAA, no el path WU/ICAO. Los únicos bloqueadores son C10 y C11 — ambos son decisión Opus, no trabajo técnico pendiente.

---

## 7. Veredicto Actual

**READY_FOR_OPUS_SOURCE_REVIEW.**  
*(Actualizado 2026-05-17 post Gamma audit — anterior: SOURCE_AUDIT_NEEDED)*

Rationale (en orden de peso):

1. **Source confirmada WU ZBAA** — Gamma audit sobre 2 mercados resueltos (market_id 1996577, 1996578) confirmó `resolutionSource=https://www.wunderground.com/history/daily/cn/beijing/ZBAA`. Description explícita: "Beijing Capital International Airport Station", Wunderground, Celsius entero. Sin "unknown", sin "polymarket_market_price". Blocker C1/C2/C4 resueltos.

2. **Mapping interno match exacto** — `_wu_history_url("ZBAA")` en bot.py genera la misma URL que Gamma usa como `resolutionSource`. C3 resuelto.

3. **Señal trader madura** — shadow_cycles=42, edge_hits=5, best_edge=37.9%, blocked n=11 WR=100%. C5 met desde antes.

4. `noaa_station_id` ausente — sigue bloqueando el path NOAA/observed-audit (C6). **No bloquea el path WU/ICAO.** Opus decide si ese path es aceptable para promotion review.

**¿Por qué no SOURCE_TEXT_CONFIRMED directamente accionable?**  
C10 y C11 son gates explícitos. Toda promotion (canary, whitelist, active) requiere Opus review explícita sobre (1) si path WU/ZBAA es aceptable y (2) cuál es el siguiente paso operativo. No hay auto-promoción.

**¿Por qué no SOURCE_BLOCKED?**  
La fuente existe, está mapeada y fue confirmada vía Gamma. No hay mismatch ni "unknown". El único trabajo pendiente es decisión Opus.

---

## 8. Next Trigger

> **Trigger activo:** Solicitar Opus review para C10 y C11 — confirmar si el path WU/ZBAA es aceptable para promotion review (análogo a C10 de Jeddah) y decidir siguiente paso operativo.  
> La base técnica está completa: source confirmada, mapping match, señal madura. El único trabajo pendiente es decisión Opus.
>
> **Opus debe decidir:**  
> (1) ¿Es WU/ZBAA un path aceptable para promotion review sin `noaa_station_id`? (mismo decision point que Jeddah C10)  
> (2) ¿Cuál es el siguiente paso operativo? — opciones: whitelist candidacy, canary limitado, scanner v0.2 run (eliminando exclusión observed_audit), o espera adicional.
>
> **Guardrails hasta Opus review:**  
> No BUY/SELL/SKIP. No whitelist. No city mode change. No BANKROLL. No Fase C. No env vars. No promotion de ningún tipo.
>
> **No reabrir solo por:** más shadow ciclos, más blocked signals, o cambios en otros mercados. La señal ya es suficiente y la fuente está confirmada.

---

## Validaciones

- Dossier docs-only. Sin cambios a `bot.py`, `tools/`, tests, env vars, DB, whitelist, policy, scheduler, BANKROLL, Fase C, observed_vs_forecast, Telegram, source mappings, ni city modes.
- Gamma audit: read-only, queries a `gamma-api.polymarket.com/markets/slug/` (GET, sin autenticación, sin side effects).
- Fuentes originales: `data/runtime_import/shadow_city_tracking.json` (Beijing snapshot 2026-05-13); `data/runtime_import_derived/blocked_signals_resolutions.jsonl` (local n=2); Blocked Signals audit 2026-05-17 (Railway live n=11); `bot.py` v10.6.40 RESOLUTION_STATIONS/RESOLUTION_ICAO/OBSERVED_AUDIT_CITIES; `tools/forecast_accuracy_audit.py:32` ICAO_ONLY_PROXY_AUDIT_CITIES; `docs/source_audits/jeddah_promotion_readiness.md` (comparación); `docs/source_audits/candidate_source_onboarding_audit.md`.
- Fuente Gamma audit 2026-05-17: slugs `highest-temperature-in-beijing-on-april-18-2026-27c` (market_id 1996578) y `highest-temperature-in-beijing-on-april-18-2026-26c` (market_id 1996577); campo `resolutionSource` y `description` del payload Gamma.
