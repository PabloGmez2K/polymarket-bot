# City Universe Audit

> LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.

- Generated: `2026-05-20T20:09:50.282544+00:00`
- Window: `14` days
- Cities ranked: `51`
- Top canary candidates: `0`
- Bottom active cities: `4`

## Ranking

| Rank | City | Mode | Evals/day | WouldBuy Shadow | Edge+ | Score | Data | Risk Flags | Action |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | Paris | blocked | 1.07 | 0 | 0 | 7/16 | medium | structural_block, drift_warning | source_blocked |
| 2 | Taipei | shadow | 0.57 | 0 | 0 | 7/16 | medium | - | observe_more |
| 3 | Amsterdam | shadow | 0.29 | 0 | 0 | 6/16 | low | - | observe_more |
| 4 | Beijing | shadow | 0.50 | 0 | 0 | 6/16 | medium | - | observe_more |
| 5 | Guangzhou | shadow | 0.57 | 0 | 0 | 6/16 | medium | source_critical | source_blocked |
| 6 | Los Angeles | shadow | 0.93 | 0 | 0 | 6/16 | medium | - | observe_more |
| 7 | Madrid | canary | 0.64 | 0 | 0 | 6/16 | medium | drift_warning | observe_more |
| 8 | Moscow | shadow | 0.14 | 0 | 0 | 6/16 | low | - | observe_more |
| 9 | Seoul | canary | 1.50 | 0 | 0 | 6/16 | high | drift_warning | observe_more |
| 10 | Shanghai | active | 0.29 | 0 | 0 | 6/16 | low | drift_warning | demote_to_watch_candidate |
| 11 | Singapore | canary | 0.29 | 0 | 0 | 6/16 | low | drift_warning | observe_more |
| 12 | Tel Aviv | shadow | 0.14 | 0 | 0 | 6/16 | low | - | observe_more |
| 13 | Wellington | canary | 0.93 | 0 | 0 | 6/16 | medium | drift_warning | observe_more |
| 14 | Wuhan | shadow | 0.21 | 0 | 0 | 6/16 | low | - | observe_more |
| 15 | Atlanta | blocked | 0.71 | 0 | 0 | 5/16 | medium | structural_block | source_blocked |
| 16 | Busan | shadow | 0.36 | 0 | 0 | 5/16 | low | - | observe_more |
| 17 | Dallas | canary | 0.64 | 0 | 0 | 5/16 | medium | drift_warning | observe_more |
| 18 | Hong Kong | shadow | 1.29 | 0 | 0 | 5/16 | medium | - | observe_more |
| 19 | Jakarta | shadow | 0.57 | 0 | 0 | 5/16 | medium | - | observe_more |
| 20 | London | blocked | 2.14 | 0 | 0 | 5/16 | high | structural_block | source_blocked |
| 21 | Milan | canary | 0.36 | 0 | 0 | 5/16 | low | drift_warning | observe_more |
| 22 | Munich | canary | 0.36 | 0 | 0 | 5/16 | low | drift_warning | observe_more |
| 23 | Qingdao | shadow | 0.07 | 0 | 0 | 5/16 | low | - | observe_more |
| 24 | San Francisco | shadow | 0.21 | 0 | 0 | 5/16 | low | source_critical | source_blocked |
| 25 | Shenzhen | shadow | 0.29 | 0 | 0 | 5/16 | low | - | observe_more |
| 26 | Ankara | active | 0.00 | 0 | 0 | 4/16 | none | drift_warning, insufficient_data | demote_to_watch_candidate |
| 27 | Austin | canary | 0.36 | 0 | 0 | 4/16 | low | - | observe_more |
| 28 | Chicago | blocked | 0.07 | 0 | 0 | 4/16 | low | structural_block, drift_warning | source_blocked |
| 29 | Denver | shadow | 0.07 | 0 | 0 | 4/16 | low | - | observe_more |
| 30 | Kuala Lumpur | shadow | 0.36 | 0 | 0 | 4/16 | low | - | observe_more |
| 31 | Mexico City | shadow | 0.14 | 0 | 0 | 4/16 | low | source_critical | source_blocked |
| 32 | New York City | shadow | 0.14 | 0 | 0 | 4/16 | low | - | observe_more |
| 33 | Tokyo | active | 0.00 | 0 | 0 | 4/16 | none | drift_warning, insufficient_data | demote_to_watch_candidate |
| 34 | Buenos Aires | active | 0.00 | 0 | 0 | 2/16 | none | insufficient_data | demote_to_watch_candidate |

## Top 5 Candidatas A Canary

No clear promote_to_canary_candidate rows in this window.

## Bottom Active Cities

### Shanghai - Score: 6/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.29 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_WOULD_BUY_TRUE', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate

### Ankara - Score: 4/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate

### Tokyo - Score: 4/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate

### Buenos Aires - Score: 2/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL']
- Recommendation: demote_to_watch_candidate


## Reason Codes

| City | Reason Codes | Recommended Action |
| --- | --- | --- |
| Paris | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | source_blocked |
| Taipei | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Amsterdam | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Beijing | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Guangzhou | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_CRITICAL | source_blocked |
| Los Angeles | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Madrid | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Moscow | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Seoul | NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Shanghai | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | demote_to_watch_candidate |
| Singapore | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Tel Aviv | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Wellington | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Wuhan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Atlanta | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Busan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Chongqing | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Dallas | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Hong Kong | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Jakarta | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| London | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Milan | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Munich | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | observe_more |
| Qingdao | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| San Francisco | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_CRITICAL | source_blocked |
| Shenzhen | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Ankara | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | demote_to_watch_candidate |
| Austin | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Chicago | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | source_blocked |
| Denver | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Istanbul | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Jeddah | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, SOURCE_AMBIGUOUS | observe_more |
| Kuala Lumpur | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Mexico City | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| New York City | NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Tokyo | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, DRIFT_WARNING | demote_to_watch_candidate |
| Chengdu | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Helsinki | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Houston | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Warsaw | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE | observe_more |
| Buenos Aires | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | demote_to_watch_candidate |
| Cape Town | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Karachi | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Lagos | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Lucknow | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Manila | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Miami | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Panama City | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Sao Paulo | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Seattle | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Toronto | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |

## Input Warnings

- bot_signal_evaluations line 1 invalid JSON, skipped
- blocked_signals_resolutions line 1 invalid JSON, skipped
- skip_log line 1 invalid JSON, skipped

---

*LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.*
