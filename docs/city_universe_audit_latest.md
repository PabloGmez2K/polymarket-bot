# City Universe Audit

> LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.

- Generated: `2026-05-20T17:11:48.529181+00:00`
- Window: `14` days
- Cities ranked: `50`
- Top canary candidates: `0`
- Bottom active cities: `4`

## Ranking

| Rank | City | Mode | Evals/day | WouldBuy Shadow | Edge+ | Score | Data | Risk Flags | Action |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | Ankara | active | 0.00 | 0 | 0 | 2/16 | none | drift_warning, insufficient_data | demote_to_watch_candidate |
| 2 | Buenos Aires | active | 0.00 | 0 | 0 | 2/16 | none | insufficient_data | demote_to_watch_candidate |
| 3 | Shanghai | active | 0.00 | 0 | 0 | 2/16 | none | drift_warning, insufficient_data | demote_to_watch_candidate |
| 4 | Tokyo | active | 0.00 | 0 | 0 | 2/16 | none | drift_warning, insufficient_data | demote_to_watch_candidate |

## Top 5 Candidatas A Canary

No clear promote_to_canary_candidate rows in this window.

## Bottom Active Cities

### Ankara - Score: 2/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate

### Buenos Aires - Score: 2/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL']
- Recommendation: demote_to_watch_candidate

### Shanghai - Score: 2/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate

### Tokyo - Score: 2/16 - Action: demote_to_watch_candidate

- Mode actual: active
- Evals/day: 0.00 (DEAD)
- Would_buy_true: 0
- Main blockers: ['NO_EVALS_IN_WINDOW', 'NO_WOULD_BUY_TRUE', 'NO_TRADER_SIGNAL', 'DRIFT_WARNING']
- Recommendation: demote_to_watch_candidate


## Reason Codes

| City | Reason Codes | Recommended Action |
| --- | --- | --- |
| Amsterdam | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Chongqing | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Houston | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Jeddah | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Wuhan | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_AMBIGUOUS | observe_more |
| Ankara | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | demote_to_watch_candidate |
| Atlanta | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Austin | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Beijing | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Buenos Aires | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | demote_to_watch_candidate |
| Busan | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Cape Town | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Chengdu | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Chicago | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | source_blocked |
| Dallas | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Denver | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Guangzhou | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Helsinki | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Hong Kong | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Istanbul | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Jakarta | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Karachi | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Kuala Lumpur | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Lagos | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| London | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | source_blocked |
| Los Angeles | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Lucknow | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Madrid | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Mexico City | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Miami | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Milan | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Moscow | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Munich | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| New York City | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Panama City | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Paris | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | source_blocked |
| Qingdao | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| San Francisco | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, SOURCE_CRITICAL | source_blocked |
| Sao Paulo | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Seattle | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Seoul | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Shanghai | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | demote_to_watch_candidate |
| Shenzhen | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Singapore | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Taipei | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Tel Aviv | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Tokyo | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | demote_to_watch_candidate |
| Toronto | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |
| Warsaw | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL | observe_more |
| Wellington | NO_EVALS_IN_WINDOW, NO_WOULD_BUY_TRUE, NO_POSITIVE_EDGE, NO_TRADER_SIGNAL, DRIFT_WARNING | observe_more |

## Input Warnings

- bot_signal_evaluations missing: C:\Projects\polymarket-bot\data\runtime_import_derived\bot_signal_evaluations.jsonl
- trade_lifecycle missing: C:\Projects\polymarket-bot\data\runtime_import_derived\trade_lifecycle.json
- skip_log missing: C:\Projects\polymarket-bot\data\runtime_import_derived\skip_log.jsonl
- city_policy_state missing: C:\Projects\polymarket-bot\data\runtime_import_derived\city_policy_state.json

---

*LOG_ONLY - observational report only. No BUY, SELL, SKIP, env var, BANKROLL, Phase C, city-mode, scheduler, source_policy, sizing, DB, or runtime changes.*
