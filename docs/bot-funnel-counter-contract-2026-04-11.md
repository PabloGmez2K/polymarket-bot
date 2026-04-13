# Bot Funnel Counter Contract - 2026-04-11

## Objetivo

Fijar un contrato read-only entre los counters legacy de `bot.py` y los nombres canonicos del funnel.

Este doc existe para que dashboards, docs, prompts y checks no dependan de copy informal.

No cambia `bot.py`. Solo documenta como debe leerse hoy.

## Regla De Uso

- Cuando un doc use nombres canonicos, debe remitir a esta tabla si necesita citar el counter legacy real.
- Cuando un doc use nombres legacy de `bot.py`, debe aclarar el nombre canonico correspondiente.
- Este contrato no autoriza renombrar counters internos en `bot.py`.

## Mapeo Canonico

| Capa | Legacy en `bot.py` / runtime | Nombre canonico | Lectura |
| --- | --- | --- | --- |
| decisions log | `MERCADOS: N encontrados` | `raw_markets_fetched` | Mercados brutos descargados antes de filtros. |
| cycle summary | `markets_evaluated` | `candidates_after_prefilters` | Candidatos tras parseo, fecha, timezone, policy, precio y liquidez. |
| cycle summary | `with_edge` | `candidates_with_edge` | Candidatos con edge suficiente antes de seleccion final. |
| cycle summary | `selected` | `candidates_selected` | Candidatos elegidos para el camino de compra. |
| cycle summary / postmortem | `buys_real` | `trades_executed` | Compras reales ejecutadas. |
| cycle summary / shadow tracking | `shadow` | `shadow_opportunities_observed` | Oportunidades con edge vistas pero no operables por modo/scope. |
| cycle summary / skip log | `condition_filtered` | `condition_filtered_out` | Mercados fuera de `ALLOWED_CONDITIONS`; hoy tipicamente `range/exact`. |
| skip log | `blocked_city` | `blocked_city_count` | Markets descartados porque la ciudad esta en modo `blocked`. |
| skip log | `fuera_allowlist` | `fuera_allowlist_count` | Markets descartados por quedar fuera del scope tradable efectivo. |
| skip log | `timezone_filter` | `date_out_of_range_count` | Subrazon de gating temporal por timezone/min-days local. |
| skip log | `date_out_of_range_past` | `date_out_of_range_count` | Subrazon de ventana temporal por fecha pasada. |
| skip log | `date_out_of_range_future` | `date_out_of_range_count` | Subrazon de ventana temporal por fecha demasiado futura. |
| skip log | `price_out_of_range` | `price_out_of_range_count` | Markets descartados por bounds de precio. |

## Notas De Interpretacion

- `markets_evaluated` no significa universo bruto; es alias legacy de `candidates_after_prefilters`.
- `condition_filtered` no significa edge insuficiente; es scope de estrategia.
- `shadow` no significa compras virtuales equivalentes a `buys_real`; es observacion read-only.
- `timezone_filter`, `date_out_of_range_past` y `date_out_of_range_future` son subrazones temporales; el agregado canonico es `date_out_of_range_count`.

## No Toca

- `bot.py`
- thresholds
- allowlists
- policy live
- bankroll
