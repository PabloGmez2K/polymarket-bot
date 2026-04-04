# Forecast Accuracy Audit

## Resumen ejecutivo

- Generado: `2026-04-04T09:28:13+00:00`
- Fuente postmortem: `railway:/app/data/postmortem.json`
- Trades analizados con observado: `34` / normalizados `34` / input `127`
- Win rate observado ex-post: `52.9%`
- LOSS_TOTAL: `41.2%`
- Error forecast medio `forecast_max - observed_real`: `-1.444 °C`
- Sigma forecast error global: `2.248 °C`
- Trades con `real_edge < 0`: `23.5%`
- Trades que no pasarían `MIN_EDGE` usando sigma empírica: `11.8%`
- Sesgo por lado: `YES=21 (61.8%)` | `NO=13 (38.2%)`
- Trades sin observado recuperado: `0`

## Sigma empírica por ciudad y days_ahead

| Ciudad | days_ahead | trades | WR | forecast_error_mean | sigma_empirica | sigma_modelo | PnL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ankara | 0 | 1 | 0.0% | -0.900 | n/d | 1.20 | -1.35$ |
| Ankara | 1 | 1 | 100.0% | -1.000 | n/d | 1.50 | 1.67$ |
| Atlanta | 0 | 5 | 40.0% | -0.400 | 0.784 | 1.20 | -5.17$ |
| Atlanta | 1 | 1 | 0.0% | -3.500 | n/d | 1.50 | -1.30$ |
| Buenos Aires | 0 | 3 | 66.7% | -2.067 | 1.097 | 1.20 | -4.22$ |
| Chicago | 0 | 4 | 25.0% | 0.200 | 2.573 | 1.20 | -6.87$ |
| Chicago | 1 | 3 | 0.0% | -3.500 | 2.587 | 1.50 | -4.94$ |
| Dallas | 0 | 2 | 100.0% | 0.350 | 0.212 | 1.20 | -1.30$ |
| Dallas | 1 | 1 | 0.0% | -1.300 | n/d | 1.50 | -0.56$ |
| London | 1 | 1 | 100.0% | 0.300 | n/d | 1.50 | -2.31$ |
| Miami | 0 | 2 | 100.0% | -0.450 | 1.061 | 1.20 | -3.69$ |
| Munich | 0 | 1 | 0.0% | -0.300 | n/d | 1.20 | -1.26$ |
| New York City | 0 | 2 | 50.0% | -2.000 | 0.283 | 1.20 | 0.31$ |
| New York City | 2 | 1 | 100.0% | -5.700 | n/d | 2.00 | 0.06$ |
| Paris | 0 | 1 | 100.0% | 0.400 | n/d | 1.20 | -1.84$ |
| Seattle | 0 | 1 | 0.0% | -7.400 | n/d | 1.20 | -1.32$ |
| Seoul | 2 | 1 | 100.0% | -5.900 | n/d | 2.00 | -1.05$ |
| Singapore | 1 | 1 | 100.0% | -0.700 | n/d | 1.50 | -0.36$ |
| Tokyo | 2 | 1 | 100.0% | -0.400 | n/d | 2.00 | 1.57$ |
| Wellington | 1 | 1 | 100.0% | -0.600 | n/d | 1.50 | -2.10$ |

## Resumen por ciudad

| Ciudad | trades | WR | forecast_error_mean | sigma_empirica | PnL | LOSS_TOTAL |
| --- | --- | --- | --- | --- | --- | --- |
| Ankara | 2 | 50.0% | -0.950 | 0.071 | 0.32$ | 0 |
| Atlanta | 6 | 33.3% | -0.917 | 1.447 | -6.47$ | 3 |
| Buenos Aires | 3 | 66.7% | -2.067 | 1.097 | -4.22$ | 2 |
| Chicago | 7 | 14.3% | -1.386 | 3.074 | -11.81$ | 4 |
| Dallas | 3 | 66.7% | -0.200 | 0.964 | -1.86$ | 0 |
| London | 1 | 100.0% | 0.300 | n/d | -2.31$ | 1 |
| Miami | 2 | 100.0% | -0.450 | 1.061 | -3.69$ | 1 |
| Munich | 1 | 0.0% | -0.300 | n/d | -1.26$ | 1 |
| New York City | 3 | 66.7% | -3.233 | 2.146 | 0.37$ | 1 |
| Paris | 1 | 100.0% | 0.400 | n/d | -1.84$ | 0 |
| Seattle | 1 | 0.0% | -7.400 | n/d | -1.32$ | 0 |
| Seoul | 1 | 100.0% | -5.900 | n/d | -1.05$ | 1 |
| Singapore | 1 | 100.0% | -0.700 | n/d | -0.36$ | 0 |
| Tokyo | 1 | 100.0% | -0.400 | n/d | 1.57$ | 0 |
| Wellington | 1 | 100.0% | -0.600 | n/d | -2.10$ | 0 |

## Top 5 peores trades por edge ficticio

| Ciudad | Fecha | Side | Forecast | Obs | Edge original | Real edge | Gap ficticio | Close | PnL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Chicago | 2026-04-04 | YES | 13.6C | 16.6C | 27.6% | -35.4% | 63.0% | SELL | -0.06$ |
| Chicago | 2026-03-27 | YES | 4.4C | 7.8C | 29.3% | -16.5% | 45.8% | LOSS_TOTAL | -2.50$ |
| New York City | 2026-04-03 | YES | 17.8C | 20.0C | 20.7% | -15.3% | 36.0% | SELL | 0.51$ |
| Chicago | 2026-03-26 | YES | 15.9C | 22.2C | 23.2% | -7.5% | 30.7% | LOSS_TOTAL | -4.88$ |
| Chicago | 2026-03-29 | YES | 19.4C | 17.2C | 20.1% | -8.8% | 28.9% | SELL | -0.66$ |

## Notas de interpretación

- `forecast_error = forecast_max - observed_real`; positivo significa que Open-Meteo sobreestimó la máxima.
- `real_edge` se calcula contra la probabilidad del lado comprado usando la temperatura observada como media de la normal y la sigma del modelo v10.3.
- `sigma_empirica` es el desvío estándar muestral del error en cada bucket; si `n < 2`, se usa bucket ciudad o sigma del modelo para el recálculo.
- La referencia por trade es `first_buy` si existe; si no, se usa snapshot `latest_*`.
- Si `question` venía vacío en postmortem, el umbral se infiere por grid-search contra `our_prob` y queda marcado como `threshold_source=inferred_from_prob` en el JSON.

## Registros omitidos o degradados

```json
{
  "missing_forecast_max": 82,
  "ok": 34,
  "not_closed": 11
}
```
