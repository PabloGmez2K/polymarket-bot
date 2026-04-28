# Auditoría Blocked Signals fuera de whitelist — 2026-04-28

**Sesión:** 259  
**Fecha:** 28 de abril de 2026  
**Modelo:** Sonnet  
**Tipo:** Read-only / documentación. No se modificó código, whitelist, city modes ni trading core.

---

## Alerta recibida

```
📊 Blocked signals (fuera de whitelist) - WR diaria
Baseline fuera de whitelist: 105 resueltas | Wins: 104 | WR: 99.0%
Excluidas del cálculo por estar ya en whitelist: 293
Nivel: ACTION
```

---

## Fuente de datos

Archivo en Railway: `/app/data/blocked_signals_resolutions.jsonl`  
Descargado vía SSH (`MSYS_NO_PATHCONV=1 railway ssh --service polymarket-bot -- cat /app/data/blocked_signals_resolutions.jsonl`).

**Total registros:** 398 — todos con `resolved=True`.

---

## Schema real del archivo

Campos presentes:
```
checked_at, match_key, city, date, condition, trader,
trader_historical_wr, outcome, avg_price_entered,
close_price, resolved, win_for_trader, has_consensus
```

**Campos ausentes** (requeridos para análisis completo):
- `resolution_source` — no existe en el schema
- `settlement_source` — no existe en el schema
- `market_id` — no existe (sin deduplicación por mercado)
- `edge_pct` — no existe (sin filtro de edge del bot)
- `city_mode_at_record_time` — no existe

Nota: en análisis anteriores aparecían como "UNKNOWN" — no son null, es que el campo no existe. Es un gap de logging, no un error de datos.

---

## Split whitelist — resultado correcto

La lógica `bot.py:8441-8442` funciona correctamente.

| Grupo | n | wins | losses | WR |
|---|---|---|---|---|
| IN whitelist | 293 | 281 | 12 | 95.9% |
| **OUT whitelist** | **105** | **104** | **1** | **99.0%** |

El split está bien implementado. Las ciudades ya en `QUALITY_TRADER_CITIES_WHITELIST` (32 ciudades) se excluyen correctamente del cálculo de la alerta.

---

## Ciudades fuera de whitelist (16 ciudades)

| Ciudad | n | wins | losses | WR | avg_price | cond | notas |
|---|---|---|---|---|---|---|---|
| **Lucknow** | 19 | 19 | 0 | 100% | 0.774 | exact | Sin infraestructura settlement local |
| **Warsaw** | 17 | 17 | 0 | 100% | 0.677 | exact | Aparece en `stable_trader_only`; EPWA conocido |
| **Beijing** | 17 | 17 | 0 | 100% | 0.640 | exact | ICAO-only audit activo (ZBAA) |
| **Chongqing** | 17 | 17 | 0 | 100% | 0.653 | exact | Sin infraestructura; ZUCK no verificado |
| Lagos | 7 | 7 | 0 | 100% | 0.727 | exact | Sin estructuras base en bot.py |
| Buenos Aires | 7 | 7 | 0 | 100% | 0.408 | exact | Trader Illustrious-Church WR 0% en closed |
| Guangzhou | 6 | 6 | 0 | 100% | 0.613 | exact | Sin infraestructura |
| Karachi | 4 | 4 | 0 | 100% | 0.775 | exact | Sin infraestructura |
| Cape Town | 3 | 3 | 0 | 100% | 0.403 | exact | n pequeño |
| Los Angeles | 2 | 2 | 0 | 100% | 0.870 | range | n muy pequeño |
| **Mexico City** | 1 | 0 | **1** | 0% | 0.107 | exact | **Única pérdida** — apuesta especulativa muy barata |
| Panama City | 1 | 1 | 0 | 100% | 0.749 | exact | n=1 |
| Austin | 1 | 1 | 0 | 100% | 0.824 | range | n=1 |
| San Francisco | 1 | 1 | 0 | 100% | 0.826 | range | n=1 |
| Sao Paulo | 1 | 1 | 0 | 100% | 0.573 | exact | n=1 |
| Manila | 1 | 1 | 0 | 100% | 0.761 | exact | n=1 |

**Las 4 primeras ciudades explican 70/105 señales = 66.7% del total out-wl.**

La única pérdida: `Mexico City|2026-04-13|exact|24°C` — Trader Thrifty-Original compró YES a 0.107 (10.7¢), mercado resolvió NO. Apuesta especulativa de bajo precio fallida.

---

## Traders en señales fuera de whitelist

| Trader | n | wins | WR observado | hist_wr |
|---|---|---|---|---|
| Entire-Hood | 31 | 31 | 100% | 84.0% |
| Jubilant-Spending | 28 | 28 | 100% | 64.9% |
| Thrifty-Original | 20 | 19 | 95.0% | 80.5% |
| Dimpled-Boy | 19 | 19 | 100% | 81.0% |
| Kind-Flour | 5 | 5 | 100% | 59.0% |
| Pricey-Score | 2 | 2 | 100% | 52.3% |

Estos 6 traders son distintos a los del whitelist reference (Coarse-Gas, Academic-Maniac, Content-Lunchroom, White-Donkey, etc.). Son quality traders con hist_wr 52-84%, pero no tienen posiciones cruzadas con las ciudades del ledger principal.

`trader_historical_wr` promedio en out-wl: **75.9%** (min 50.8%, max 93.0%).

---

## Sesgos del WR 99%

El WR no es trivial (avg_price 0.64-0.77 = no son apuestas near-certain), pero tampoco es accionable:

1. **Concentración en 4 ciudades** (66.7%) sin diversificación real de la muestra.
2. **No hay settlement source** en el schema. `close_price=1.0` significa que el mercado pagó, no que hay fuente verificable de temperatura real.
3. **Sin ICAO/NOAA local** para Lucknow, Chongqing, Lagos, Buenos Aires, Guangzhou, Karachi. Sin infraestructura de verificación.
4. **has_consensus=True** solo en 21/105 (20%) de señales out-wl.
5. **market_id ausente** → no se puede descartar que el mismo mercado aparezca varias veces (con distintos traders).
6. **Refuerzo de London**: 21 señales, WR 100%, pero está bloqueada por mismatch WU/OpenMeteo. WR alta ≠ ciudad tradeable.

---

## Ciudades dentro de whitelist (top 10, para referencia)

| Ciudad | n | wins | WR |
|---|---|---|---|
| London | 21 | 21 | 100% |
| Shanghai | 21 | 20 | 95.2% |
| Moscow | 18 | 14 | 77.8% |
| Paris | 17 | 16 | 94.1% |
| Istanbul | 15 | 15 | 100% |
| Wuhan | 15 | 15 | 100% |
| Chengdu | 14 | 14 | 100% |
| Tokyo | 13 | 13 | 100% |
| Jakarta | 13 | 13 | 100% |
| Ankara | 11 | 11 | 100% |

---

## Decisión

**No se toca:**
- Trading core
- Whitelist
- City modes
- Bankroll / MIN_EDGE / sigma / sizing
- Reglas de entrada/salida

**Warsaw** queda como candidata prioritaria para auditoría futura (no trading):
- n=17, WR 100%, avg_price 0.677
- Aparece en `signals_crosscheck_daily_summary_state.json` como `last_stable_trader_only`
- ICAO EPWA conocido — requiere confirmar settlement fidelity en ledger local
- No abrir a canary/active sin ese paso

**Lucknow, Beijing, Chongqing:** muestra sólida (17-19 señales) pero sin settlement local verificado. Beijing ya está en ICAO-only audit (`OBSERVED_AUDIT_CITIES`). Lucknow también. Chongqing sin infraestructura.

---

## Mejora de logging diferida (no implementar ahora)

El schema de `blocked_signals_resolutions.jsonl` necesita estos campos para hacer el análisis sin auditoría manual:

- `market_id` — deduplicación
- `edge_pct` — saber si el bot hubiera tenido edge suficiente
- `resolution_source` — fuente de verificación
- `settlement_source` — fuente de liquidación
- `city_mode_at_record_time` — modo del bot al momento del registro

Esta mejora es para proponer en próxima sesión de diseño con Opus, no para implementar en esta sesión.

---

## Archivos relevantes

- `bot.py:258-265` — definición de `QUALITY_TRADER_CITIES_WHITELIST`
- `bot.py:8441-8442` — split in_wl/out_wl en el chequeo diario
- `bot.py:8450-8466` — lógica de nivel ACTION/WATCH/INFO y envío Telegram
- `data/signals_crosscheck_daily_summary_state.json` — lista de `stable_trader_only` (incluye Warsaw)
- `data/city_validation_ledger.json` — evidencia de settlement fidelity por ciudad
- `/app/data/blocked_signals_resolutions.jsonl` — Railway (398 registros, solo lectura)
