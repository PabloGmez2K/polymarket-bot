# City Universe Audit

> LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.

- Generated: `2026-05-20T20:58:18.723694+00:00`
- Window: `14` days
- Confidence banner: `LOW_CONFIDENCE_WINDOW`
- Effective window days: `14`
- READ_BOT_EVAL_CAPTURE: `enabled`
- Shadow-only mode: `False`
- Action semantics: `review_candidates_only_not_operational_decisions`
- Cities ranked: `51`
- Top canary candidates: `0`
- Bottom active review rows: `4`

> LOW_CONFIDENCE_WINDOW - active-city actions are throughput watches/review candidates, not demotions.
> Reasons: effective_window_days_lt_21

## Ranking

| Rank | City | Mode | Evals/day | WouldBuy Shadow | Edge+ | Score | Data | Risk Flags | Action |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | Paris | blocked | 1.07 | 0 | 0 | 7/16 | medium | structural_block | source_blocked |
| 2 | Taipei | shadow | 0.57 | 0 | 0 | 7/16 | medium | - | observe_more |
| 3 | Amsterdam | shadow | 0.29 | 0 | 0 | 6/16 | low | - | observe_more |
| 4 | Beijing | shadow | 0.50 | 0 | 0 | 6/16 | medium | - | observe_more |
| 5 | Guangzhou | shadow | 0.57 | 0 | 0 | 6/16 | medium | source_critical | source_blocked |
| 6 | Los Angeles | shadow | 0.93 | 0 | 0 | 6/16 | medium | - | observe_more |
| 7 | Madrid | canary | 0.64 | 0 | 0 | 6/16 | medium | drift_warning | observe_more |
| 8 | Moscow | shadow | 0.14 | 0 | 0 | 6/16 | low | - | observe_more |
| 9 | Seoul | canary | 1.50 | 0 | 0 | 6/16 | high | - | observe_more |
| 10 | Shanghai | active | 0.29 | 0 | 0 | 6/16 | low | - | active_throughput_watch |
| 11 | Singapore | canary | 0.29 | 0 | 0 | 6/16 | low | drift_warning | observe_more |
| 12 | Tel Aviv | shadow | 0.14 | 0 | 0 | 6/16 | low | - | observe_more |
| 13 | Wellington | canary | 0.93 | 0 | 0 | 6/16 | medium | - | observe_more |
| 14 | Wuhan | shadow | 0.21 | 0 | 0 | 6/16 | low | - | observe_more |
| 15 | Atlanta | blocked | 0.71 | 0 | 0 | 5/16 | medium | structural_block | source_blocked |
| 16 | Busan | shadow | 0.36 | 0 | 0 | 5/16 | low | - | observe_more |
| 17 | Dallas | canary | 0.64 | 0 | 0 | 5/16 | medium | - | observe_more |
| 18 | Hong Kong | shadow | 1.29 | 0 | 0 | 5/16 | medium | - | observe_more |
| 19 | Jakarta | shadow | 0.57 | 0 | 0 | 5/16 | medium | - | observe_more |
| 20 | London | blocked | 2.14 | 0 | 0 | 5/16 | high | structural_block | source_blocked |
| 21 | Milan | canary | 0.36 | 0 | 0 | 5/16 | low | - | observe_more |
| 22 | Munich | canary | 0.36 | 0 | 0 | 5/16 | low | - | observe_more |
| 23 | Qingdao | shadow | 0.07 | 0 | 0 | 5/16 | low | - | observe_more |
| 24 | San Francisco | shadow | 0.21 | 0 | 0 | 5/16 | low | source_critical | source_blocked |
| 25 | Shenzhen | shadow | 0.29 | 0 | 0 | 5/16 | low | - | observe_more |
| 26 | Austin | canary | 0.36 | 0 | 0 | 4/16 | low | - | observe_more |
| 27 | Chicago | blocked | 0.07 | 0 | 0 | 4/16 | low | structural_block | source_blocked |
| 28 | Denver | shadow | 0.07 | 0 | 0 | 4/16 | low | - | observe_more |
| 29 | Kuala Lumpur | shadow | 0.43 | 0 | 0 | 4/16 | low | - | observe_more |
| 30 | Mexico City | shadow | 0.14 | 0 | 0 | 4/16 | low | source_critical, drift_unknown | source_blocked |
| 31 | New York City | shadow | 0.14 | 0 | 0 | 4/16 | low | - | observe_more |
| 32 | Ankara | active | 0.00 | 0 | 0 | 2/16 | none | drift_warning, insufficient_data | active_throughput_watch |
| 33 | Tokyo | active | 0.00 | 0 | 0 | 2/16 | none | insufficient_data | active_throughput_watch |
| 34 | Buenos Aires | active | 0.00 | 0 | 0 | 0/16 | none | insufficient_data | active_throughput_watch |

## Top 5 Candidatas A Canary

No clear promote_to_canary_candidate rows in this window.

## Bottom Active Cities

### Shanghai - Score: 6/16 - Action: active_throughput_watch

- Mode actual: active
- Evals/day: 0.29 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_WOULD_BUY_TRUE']
- Recommendation: active_throughput_watch

### Ankara - Score: 2/16 - Action: active_throughput_watch

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'DRIFT_WARNING']
- Recommendation: active_throughput_watch

### Tokyo - Score: 2/16 - Action: active_throughput_watch

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE']
- Recommendation: active_throughput_watch

### Buenos Aires - Score: 0/16 - Action: active_throughput_watch

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL']
- Recommendation: active_throughput_watch


## Reason Codes

| City | Reason Codes | Recommended Action |
| --- | --- | --- |
| Paris | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | source_blocked |
| Taipei | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Amsterdam | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Beijing | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Guangzhou | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_CRITICAL | source_blocked |
| Los Angeles | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Madrid | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Moscow | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Seoul | NO_POSITIVE_EDGE | observe_more |
| Shanghai | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | active_throughput_watch |
| Singapore | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Tel Aviv | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Wellington | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Wuhan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Atlanta | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Busan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Dallas | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Hong Kong | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Jakarta | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| London | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Milan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Munich | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Qingdao | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| San Francisco | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_CRITICAL | source_blocked |
| Shenzhen | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Austin | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Chicago | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Denver | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Kuala Lumpur | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Mexico City | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL, DRIFT_UNKNOWN | source_blocked |
| New York City | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Chongqing | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Ankara | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | active_throughput_watch |
| Istanbul | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Jeddah | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Tokyo | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | active_throughput_watch |
| Chengdu | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Helsinki | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Houston | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Warsaw | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Buenos Aires | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | active_throughput_watch |
| Cape Town | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Karachi | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL, DRIFT_UNKNOWN | source_blocked |
| Lagos | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Lucknow | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Manila | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_UNKNOWN | observe_more |
| Miami | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Panama City | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL, DRIFT_UNKNOWN | source_blocked |
| Sao Paulo | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Seattle | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Toronto | NO_EVALS_IN_WINDOW, NO_DATA_FOR_CONDITION_COMPAT, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |

---

*LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.*
