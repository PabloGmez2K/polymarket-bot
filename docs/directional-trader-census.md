# Directional Trader Census

Herramienta read-only para descubrir y perfilar wallets que compran en mercados de temperatura direccionales:

- `at_or_above`
- `at_or_below`

Se crea separada del pipeline viejo para no mezclarlo con traders de `exact/range`.

---

## Objetivo

Responder una pregunta que ahora mismo el repo no puede contestar bien:

**quienes son los traders realmente comparables a la estrategia vigente del bot?**

El pipeline historico (`find_traders.py` + `trader_analyzer.py`) estaba sesgado hacia `exact/range`. Esta herramienta reconstruye el mapa desde el universo direccional.

Por defecto, ademas filtra BUYs al rango `0.20-0.80` para acercarse al universo operativo actual del bot.

---

## Comando base

```powershell
python tools/directional_trader_census.py
```

### Variantes utiles

```powershell
python tools/directional_trader_census.py --markets 20
python tools/directional_trader_census.py --city Dallas
python tools/directional_trader_census.py --min-trades 3 --min-markets 2
python tools/directional_trader_census.py --min-price 0.20 --max-price 0.80
```

---

## Salidas

Por defecto genera:

- `data/directional_trader_census.json`
- `docs/directional_trader_census_latest.md`

---

## Que perfila por trader

- `address`
- `pseudonym`
- `n_buy_trades`
- `n_markets`
- `total_notional`
- `avg_price`
- `price_style`
- `dominant_city`
- `top_cities`
- `conditions`
- `outcomes`
- `type_hint`
- `sample_positions`

---

## Como interpretar `type_hint`

Es un hint inicial, no una clasificacion definitiva.

- `directional_forecast_candidate`
  - perfil direccional generico comparable al bot.
- `city_specialist_candidate`
  - concentracion fuerte en una sola ciudad.
- `extreme_pricing_candidate`
  - compra muy cerca de extremos de precio; puede ser perfil de conviccion, estructura o timing.

---

## Limites honestos

1. No calcula PnL historico completo del trader.
2. No clasifica aun maker vs taker de forma fuerte.
3. No detecta multi-leg entre strikes.
4. No sustituye todavia al pipeline viejo; convive aparte para research.

---

## Siguiente uso recomendado

1. Ejecutar el censo.
2. Identificar una shortlist de wallets direccionales reales.
3. Decidir si merece la pena:
   - enriquecerlas con posiciones cerradas/PnL,
   - o cruzarlas con nuestras ciudades/mercados primero.
