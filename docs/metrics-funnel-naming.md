# Metrics Funnel Naming

This contract prevents humans, dashboards and LLM reviews from mixing raw market scan volume with post-filter candidate volume.

## Canonical Names

| Canonical name | Legacy/source name | Meaning | Owner | Notes |
| --- | --- | --- | --- | --- |
| `raw_markets_fetched` | `MERCADOS: N encontrados` in `decisions.log` | Raw Polymarket markets fetched before parsing and filters. | `polymarket-bot` runtime logs | This is the top of funnel. It is not `markets_evaluated`. |
| `candidates_after_prefilters` | `markets_evaluated` | Markets that survived parsing, date, timezone, city policy, price and liquidity filters. | `polymarket-bot` cycle summary | Use this name in docs and reviews; keep `markets_evaluated` only as a legacy field alias. |
| `condition_filtered_out` | `condition_filtered` | Markets skipped because their condition is outside `ALLOWED_CONDITIONS`. | `polymarket-bot` cycle summary and skip logs | Do not treat as failed edge; this is strategy scope. |
| `candidates_with_edge` | `with_edge` | Candidates with sufficient modeled edge before final selection. | `polymarket-bot` cycle summary | Compare against `candidates_after_prefilters`, not raw markets. |
| `candidates_selected` | `selected` | Candidates selected for an attempted trade path. | `polymarket-bot` cycle summary | May still produce zero buys if mode, sizing or execution blocks apply. |
| `trades_executed` | `buys_real`, `BUY`, postmortem buys | Real purchases executed. | `polymarket-bot` trading runtime | This is the monetized bottom of funnel. |
| `shadow_opportunities_observed` | shadow rows, `fuera_allowlist`, shadow tracking edge hits | Opportunities observed but not bought because the city/mode was not tradable. | `polymarket-bot` shadow tracking | Use for validation and possible future policy review, not as realized throughput. |
| `blocked_city_count` | `blocked_city` | Markets skipped because city policy is blocked. | `polymarket-bot` skip counters | Blocked means data/source problem, not normal pause. |
| `fuera_allowlist_count` | `fuera_allowlist` | Markets skipped because the city was not in a tradable manual/runtime mode. | `polymarket-bot` skip counters | In English docs, call this `outside_trading_scope_count`. |
| `date_out_of_range_count` | `date_out_of_range_past`, date skip counters | Markets skipped by date window. | `polymarket-bot` skip counters | Keep past/future subreasons when available. |
| `price_out_of_range_count` | `price_out_of_range` | Markets skipped by price bounds. | `polymarket-bot` skip counters | Strategy guard, not discovery failure. |

## Required Wording

When a report uses `markets_evaluated`, it must state:

`markets_evaluated` is a legacy alias for `candidates_after_prefilters`, not raw fetched markets.

When a report compares throughput, use this ordering:

1. `raw_markets_fetched`
2. `candidates_after_prefilters`
3. `condition_filtered_out`
4. `candidates_with_edge`
5. `candidates_selected`
6. `trades_executed`
7. `shadow_opportunities_observed`

## Current Interpretation

The recent low `markets_evaluated` values do not mean the bot only saw a dozen raw markets. Runtime logs still show roughly `330` raw markets fetched per cycle. The small `12-26` number is post-filter candidate throughput.

## Do Not Change Yet

- Do not rename fields inside `bot.py` in this phase.
- Do not change thresholds, allowlists, conditions, bankroll or sizing based on naming cleanup.
- Do not interpret `condition_filtered_out` as a bug without a separate exact/range review.
