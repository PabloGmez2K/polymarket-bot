# System Alignment Check

- Generated: `2026-04-12T17:38:34+00:00`
- Decision mode: `operational`
- Summary: `{'ok': 6, 'warning': 2, 'error': 0}`

## Checks

| Check | Status | Message |
| --- | --- | --- |
| runtime_manifest | ok | runtime manifest is bijective and fresh |
| runtime_policy_effective_view | warning | policy collisions/divergences are explicitly listed |
| runtime_ledger | ok | runtime-import ledger is available |
| metrics_funnel_naming | warning | legacy markets_evaluated mentions remain without canonical alias candidates_after_prefilters |
| city_intelligence_targets | ok | city-intelligence targets are explicitly tagged |
| prompt_semantic_scan | ok | canonical prompts/docs respect effective-mode and funnel wording contracts |
| bot_funnel_counter_contract | ok | bot funnel counter contract is documented |
| decision_preflight_rules | ok | decision preflight guardrails are documented |

## Warnings

- `runtime_policy_effective_view`: policy collisions/divergences are explicitly listed `{'generated_at': '2026-04-12T17:38:34+00:00', 'age_hours': 0.0, 'decision_mode': 'operational', 'operational_age_slo_hours': 6.0, 'operational_max_collision_count': 5, 'operational_max_blocking_collision_count': 0, 'operational_max_documented_drift_count': 999, 'n_cities': 27, 'effective_mode_counts': {'shadow': 18, 'canary': 6, 'blocked': 3}, 'collision_count': 7, 'collision_category_counts': {'documented_drift': 7}, 'blocking_operational_collision_count': 0, 'active_effective_count': 0, 'missing_fields': []}`
- `metrics_funnel_naming`: legacy markets_evaluated mentions remain without canonical alias candidates_after_prefilters `{'ambiguous_docs': ['docs\\city-window-routing-design-2026-04-12.md'], 'ambiguous_docs_count': 1}`
