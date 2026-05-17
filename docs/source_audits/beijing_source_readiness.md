# Beijing — Source Readiness Dossier

**Generated:** 2026-05-17  
**Mode:** Sonnet read-only / docs-only  
**Authority:** No operational action. No code patch. No env/whitelist/policy change.  
**Source data:** Blocked Signals audit 2026-05-17 (Railway live); `data/runtime_import/shadow_city_tracking.json`; `data/runtime_import_derived/blocked_signals_resolutions.jsonl`; `bot.py` RESOLUTION_ICAO + OBSERVED_AUDIT_CITIES (v10.6.40); `tools/forecast_accuracy_audit.py` ICAO_ONLY_PROXY_AUDIT_CITIES.  
**Verdict:** **SOURCE_AUDIT_NEEDED** — trader signal strong; source/settlement path unresolved; no promotion step authorized.

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
| settlement_source | **unknown** |
| fidelity | **unverified** |
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
| source_texts (mercados) | **unknown** | Campo no confirmado vía Gamma para Beijing — no existe source_text conocido en scanner local |
| settlement_source | **unknown** | No registrado en blocked_signals schema (campo ausente, no null) |
| fidelity | **unverified** | Sin audit Gamma/WU comparativo realizado |
| Riesgo de mismatch | **Alto** | Beijing tiene WU ZBAA definida, pero no se sabe si Polymarket usa WU/ZBAA, otra fuente, o precio interno como settlement reference |

**Situación vs Jeddah:**  
Jeddah tiene `OEJN` en RESOLUTION_STATIONS **con** WU URL definida, y el scanner v0.2 confirmó `source_texts=["polymarket_market_price"]` (solo, sin "unknown"). Beijing tiene `ZBAA` con WU URL también definida — la diferencia es que **no se ha corrido el scanner v0.2 sobre Beijing** (fue excluida como `observed_audit` en el run 2026-05-15 que analizó Jeddah/Chongqing/Amsterdam). El riesgo de mismatch es desconocido hasta que Gamma audit confirme qué usa Polymarket como settlement reference para los mercados de Beijing.

**¿Por qué no es inmediatamente accionable?**  
El camino WU-ZBAA existe estructuralmente en `bot.py`, pero `bot.py:5497` exige `interpretable = noaa_configured AND observed >= MIN_SAMPLE`. Sin `noaa_station_id`, `noaa_configured=False`. La única vía habilitada actualmente es ICAO-only via open-meteo proxy — modo de *observación*, no de *trading*.

---

## 3. Señal Trader

| Dimensión | Valor | Interpretación |
|---|---|---|
| blocked_signals WR (Railway) | **100%** n=11 | Muy fuerte — pero source unverified |
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

**¿Basta para justificar source audit?**  
**Sí.** WR=100% n=11, tres traders de calidad, shadow activo con edge real (best 37.9%) — la señal es suficiente para justificar que alguien resuelva el blocker de source/settlement. No basta para autorizar trading ni whitelist.

---

## 4. Comparación con Jeddah

| Dimensión | Jeddah (dossier 2026-05-17) | Beijing (este dossier) |
|---|---|---|
| Veredicto | **NOT_READY_WAIT_SHADOW** | **SOURCE_AUDIT_NEEDED** |
| Blocker primario | shadow_cycles < 10 (ciclos = 6–7) | settlement_source = unknown; source_texts sin confirmar |
| Blocker secundario | Opus path decision (ICAO-only/WU aceptable?) | noaa_station_id ausente (mismo patrón) |
| ICAO | OEJN — en RESOLUTION_STATIONS + WU URL | ZBAA — en RESOLUTION_STATIONS + WU URL |
| WU URL | Definida | Definida |
| noaa_station_id | Ausente (mismo problema) | Ausente (mismo problema) |
| Scanner v0.2 corrido | **Sí** — run 2026-05-15 | **No** — excluida como observed_audit |
| source_texts confirmado | `["polymarket_market_price"]` — single, limpio | **Desconocido** — no auditado vía Gamma |
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
- **Beijing:** resolver `settlement_source` y `source_texts` vía Gamma audit + Opus confirmar si WU ZBAA es el settlement reference real. Shadow está sobrado (42 ciclos), pero la fuente sigue oscura.

Beijing no está esperando maduración de shadow — ya maduró. Está esperando **resolución de fuente**.

---

## 5. Criterios para SOURCE_AUDIT_READY

Para pasar de `WATCH_AUDIT / SOURCE_AUDIT_NEEDED` a una revisión Opus accionable:

| # | Criterio | Estado actual | Notas |
|---|---|---|---|
| C1 | Source text identificada (Gamma audit) | **PENDIENTE** | Correr scanner v0.2 sobre Beijing O audit manual de Gamma para un mercado Beijing reciente |
| C2 | settlement_source verificable | **PENDIENTE** | Confirmar si Polymarket usa WU ZBAA, otra fuente, o precio interno |
| C3 | Mapping reproducible (ICAO ZBAA → WU URL → dato verificado) | **PARCIAL** | Estructura bot.py existe (ZBAA + WU URL); falta validación end-to-end contra un dato resuelto real |
| C4 | source_texts sin "unknown" | **DESCONOCIDO** | Amsterdam tiene "unknown" y es un blocker — Beijing podría tener el mismo problema |
| C5 | Shadow/blocked signal suficiente | **MET** | shadow_cycles=42, edge_hits=5, best_edge=37.9%, blocked n=11 WR=100% |
| C6 | noaa_station_id resuelto (para path NOAA) | **BLOQUEADO** | ISD 54511099999 existe pero GHCND sin TMAX 2025-10→2026-03. Bloquea el path NOAA. No bloquea path WU/ICAO si Opus lo acepta |
| C7 | Sin drift reciente | **DESCONOCIDO** | No monitoreado activamente; shadow filtra (last_side=FILTERED en ciclos recientes) |
| C8 | Sin policy conflict | **MET** | No en whitelist, no en canary/active — clean slate |
| C9 | No risk blocker | **MET** | LOG_ONLY / shadow, sin exposición real |
| C10 | Opus confirma si WU ZBAA es path aceptable para promotion review | **PENDIENTE** | Mismo decision point que Jeddah C10 |
| C11 | Opus review antes de cualquier promotion | **PENDIENTE** | Requerida una vez C1–C4 resueltos |

**Gate de source audit:** C1, C2, C3, C4 son los bloqueadores activos. C5, C8, C9 ya están met. C6 bloquea solo el path NOAA, no el path WU/ICAO. Shadow es suficiente — el trabajo pendiente es enteramente de fuente, no de señal.

---

## 6. Veredicto Actual

**SOURCE_AUDIT_NEEDED.**

Rationale (en orden de peso):

1. `settlement_source=unknown` — blocker estructural primario. Sin saber qué usa Polymarket para resolver los mercados de Beijing, no se puede validar que el alpha del trader sea explotable con la fuente que tiene el bot.

2. `source_texts` sin confirmar — el scanner v0.2 no corrió sobre Beijing (fue excluida como `observed_audit`). No se sabe si hay "unknown" en source_texts (como Amsterdam) o si está limpio (como Jeddah). Esto es un paso previo a cualquier Opus review.

3. `noaa_station_id` ausente — bloquea el path estándar NOAA/observed-audit. No es un blocker absoluto si Opus acepta el path WU/ZBAA, pero requiere decisión explícita.

**¿Por qué no WATCH_AUDIT?**  
Shadow está sobrado: 42 ciclos, 5 edge_hits, best 37.9%. Seguir esperando más shadow no desbloquea nada — el problema es la fuente. El estado correcto es SOURCE_AUDIT_NEEDED, no espera pasiva.

**¿Por qué no READY_FOR_OPUS_SOURCE_REVIEW?**  
Falta el Gamma audit (C1, C2, C4). Pedir review Opus sin saber si source_texts contiene "unknown" sería prematuro — es el mismo pattern que llevó a Amsterdam a un blocker de resolución tardía.

**¿Por qué no SOURCE_BLOCKED?**  
La estructura técnica existe: ZBAA está mapeado, WU URL definida, open-meteo proxy activo. El blocker no es falta de fuente — es falta de *verificación* de fuente. Es remediable con trabajo humano de bajo costo (Gamma audit de 1-2 mercados).

---

## 7. Next Trigger

> **Reabrir cuando:** se complete un audit Gamma de al menos 1–2 mercados Beijing resueltos recientes, confirmando (a) qué aparece en `source_texts` para Beijing, y (b) si el settlement reference coincide con WU ZBAA o usa otra fuente.  
> Una vez C1–C4 resueltos, solicitar Opus review específicamente para: (1) confirmar si el path WU/ZBAA es aceptable para promotion review (análogo a C10 de Jeddah), y (2) decidir próximo paso operativo (scanner v0.2 run, whitelist candidacy, o espera adicional).  
> **Escalación inmediata si:** `source_texts` confirma "unknown" para Beijing → no proceder sin Opus.  
> **No reabrir solo por:** más shadow ciclos, más blocked signals, o cambios en otros mercados. La señal ya es suficiente.

---

## Validaciones

- Dossier read-only. Sin cambios a `bot.py`, `tools/`, tests, env vars, DB, whitelist, policy, scheduler, BANKROLL, Fase C, observed_vs_forecast, Telegram, source mappings, ni city modes.
- `git diff --check`: verificar a continuación antes de commit.
- Fuentes: `data/runtime_import/shadow_city_tracking.json` (Beijing snapshot 2026-05-13); `data/runtime_import_derived/blocked_signals_resolutions.jsonl` (local n=2); Blocked Signals audit 2026-05-17 (Railway live n=11); `bot.py` v10.6.40 RESOLUTION_STATIONS/RESOLUTION_ICAO/OBSERVED_AUDIT_CITIES; `tools/forecast_accuracy_audit.py:32` ICAO_ONLY_PROXY_AUDIT_CITIES; `docs/source_audits/jeddah_promotion_readiness.md` (comparación); `docs/source_audits/candidate_source_onboarding_audit.md`.
