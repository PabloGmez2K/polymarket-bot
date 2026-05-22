# Traders Activity Profile

`tools/traders_activity_profile.py` is a read-only, `LOG_ONLY` profiler for wallets already followed by this repo. It queries the Polymarket Data API Activity endpoint separately for BUY and SELL fills, summarizes raw behavior, and emits provisional descriptive labels for calibration.

It does not discover new wallets, does not write `traders_intelligence.json`, and does not import trading/runtime modules.

## CLI Contract

```powershell
python tools/traders_activity_profile.py `
  --external-report C:\Users\USUARIO\Downloads\traders_intelligence_external_observability.json `
  --window-hours 168 `
  --format md
```

Arguments:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--external-report <path>` | omitted | JSON produced by `tools/traders_intelligence_report.py --external-observability`. When present, it is the primary cohort and source for alias, display name, wallet, profile URL, WEATHER ALL P/L, and volume. |
| `--cohort external-report\|local-registry\|union` | `external-report` when `--external-report` is provided, otherwise `local-registry` | Selects the cohort before `--wallets` filtering. `external-report` analyzes only wallets resolved from the report; `local-registry` uses local JSON registries; `union` is the broad exploratory union. |
| `--wallets <csv\|@file>` | omitted | Optional extra filter over the already-followed cohort. |
| `--window-hours N` | `168` | Activity lookback window. |
| `--burst-window-sec N` | `120` | Max seconds for burst detection. |
| `--burst-min-fills N` | `4` | Min BUY fills inside the burst window. |
| `--high-price-threshold P` | `0.95` | BUY fill price threshold for high-price activity. |
| `--rotation-window-min N` | `60` | Max BUY to SELL lag for rotation detection. |
| `--max-wallets N` | `30` | Hard cap on profiled wallets. |
| `--max-fills-per-wallet N` | `1000` | Total cap per wallet. MVP splits it conservatively: BUY cap `floor(max/2)`, SELL cap remaining. |
| `--rate-limit-ms N` | `250` | Sleep between paginated/API calls. |
| `--format md\|json` | `md` | Output to stdout. |
| `--snapshot` | off | Opt-in append-only JSON snapshot. |
| `--snapshot-dir <path>` | `data/traders_intelligence/activity_snapshots/` | Snapshot directory. Manual validation should use a temp path, not the default data path. |
| `--traders-db <path>` | `traders_db.json` | Local followed-trader catalog. |
| `--traders-intelligence <path>` | `data/traders_intelligence.json` | Additional local style source only. |

## Cohort Resolution

When `--external-report` is provided, its traders are the primary cohort. The tool then completes/validates against `traders_db.json` and may add local style rows from `data/traders_intelligence.json`. Wallets are deduplicated by lower-case proxy wallet/address. Without `--external-report`, fields that would have come from external observability are emitted as `"not_loaded"`.

The output includes cohort transparency fields:

- `cohort_mode`
- `cohort_description`
- `cohort_warning`
- `n_external_report_wallets`
- `n_external_report_rows`
- `n_external_report_missing_wallets`
- `n_local_registry_added`
- `n_deduplicated`
- `n_wallets_before_wallet_filter`
- `n_wallets_after_wallet_filter`
- `n_wallets_analyzed`
- `max_wallets_truncated`
- `max_wallets_truncated_count`
- `max_wallets_truncated_examples`
- per-trader `cohort_source`: `external_report`, `traders_db`, `both`, or `local_intelligence_only`

No new wallets are discovered.

`--cohort external-report` requires `--external-report`. In `local-registry` and `union` modes, the tool emits `cohort_warning` because `traders_db.json` can contain discovered or historical registry wallets; these files alone do not prove every wallet is actively followed now.

## JSON Schema

The JSON output has `schema_version: "activity-profile-v0"`:

```json
{
  "schema_version": "activity-profile-v0",
  "generated_at": "ISO-8601 UTC",
  "disclaimer": "LOG_ONLY provisional...",
  "window": {"hours": 168, "start_ts": "ISO", "end_ts": "ISO"},
  "parameters": {
    "burst_window_sec": 120,
    "burst_min_fills": 4,
    "high_price_threshold": 0.95,
    "rotation_window_min": 60,
    "max_wallets": 30,
    "max_fills_per_wallet": 1000,
    "max_fills_buy": 500,
    "max_fills_sell": 500,
    "activity_query_cap_policy": "split total cap per wallet into BUY cap=floor(max/2), SELL cap=remaining",
    "rate_limit_ms": 250,
    "external_report": "path-or-null"
  },
  "cohort": {
    "cohort_mode": "external-report",
    "cohort_description": "Only wallets resolved from --external-report.",
    "cohort_warning": null,
    "n_external_report_rows": 0,
    "n_external_report_wallets": 0,
    "n_external_report_missing_wallets": 0,
    "n_local_registry_added": 0,
    "n_deduplicated": 0,
    "n_wallets_before_wallet_filter": 0,
    "n_wallets_after_wallet_filter": 0,
    "n_wallets_analyzed": 0,
    "n_wallets_available_after_filter": 0,
    "max_wallets_truncated": false,
    "max_wallets_truncated_count": 0,
    "max_wallets_truncated_examples": [],
    "cohort_source_counts": {}
  },
  "summary": {
    "n_wallets": 0,
    "fills_per_wallet": {"p25": null, "p50": null, "p75": null},
    "entry_price_band_p50": {"p25": null, "p50": null, "p75": null},
    "burst_count": {},
    "high_price_ratio": {"p25": null, "p50": null, "p75": null},
    "rotation_signals_count": {},
    "conditions_mix": {},
    "lane_counts": {},
    "query_status_counts": {},
    "capped_wallets": 0
  },
  "traders": []
}
```

Each trader row includes identity/external fields, query statuses, metrics, top-N examples, `style_labels`, `lane_suggestion`, `confidence`, `reason`, and `manual_review_required`. Raw fills are not emitted.

Per-trader query fields:

- `query_status`: `ok_complete`, `ok_capped`, `partial`, or `failed`.
- `buy_query_status` / `sell_query_status`: `ok_complete`, `ok_capped`, or `failed`.
- `buy_capped` / `sell_capped`: true when that side reached its cap.
- `max_fills_buy` / `max_fills_sell`: caps used for that wallet.
- `coverage_note`: reminds that high activity count is not complete coverage when capped.

Status meanings:

| Status | Meaning |
| --- | --- |
| `ok_complete` | Both BUY and SELL returned below cap and parsing was not critically insufficient. |
| `ok_capped` | BUY or SELL reached its side cap. More Activity rows may exist. |
| `partial` | One side failed or parsing was critically insufficient. |
| `failed` | Neither side could be consulted. |

`manual_review_required=true` when a wallet is capped, partial, failed, or has high parse unknown ratio. `confidence=high` means many fills were observed; it is not a reliability or coverage guarantee.

Reserved field: `nearest_bot_cycle_lag_sec_p50` is always `null` in this MVP. The tool does not read `cycles_history.jsonl`.

## Labels

| Label | Definition |
| --- | --- |
| `SINGLE_OUTCOME_DIRECTIONAL` | At least 70% of markets have one observed outcome/strike. |
| `MULTI_OUTCOME_BASKET` | At least 30% of parsed city/date weather event groups have two or more distinct condition/strike/outcome legs. The grouping key is reconstructed from title/slug as `city|event_date`, intentionally ignoring the strike so related event legs group together. |
| `BASKET_BURST` | `MULTI_OUTCOME_BASKET` plus at least one burst that itself contains multiple related legs in the same city/date group. A burst of repeated fills in one leg does not count as basket by itself. |
| `POSITION_BUILDING` | At least one market has three or more BUY fills on the same outcome within 30 minutes at distinct prices. |
| `HIGH_PRICE_ACTIVITY` | At least 10% of BUY fills are at or above `--high-price-threshold`. |
| `NEAR_RESOLUTION_PROVISIONAL` | `HIGH_PRICE_ACTIVITY` plus p50 lead time to resolution <= 6h, only when endpoint data exposes resolution/end time. |
| `BUY_SELL_PRESENT` | At least one SELL fill is present. Informative only. |
| `FREQUENT_BUY_SELL_ROTATION` | At least three BUY to SELL pairs in the same market/outcome inside `--rotation-window-min`. |
| `RANGE_DOMINANT` | `range` condition is more than 50% of parsed markets. |
| `UNKNOWN_STYLE` | Fewer than three fills in the selected window. |

All thresholds are provisional. The first real run is for distribution calibration, not for concluding comparability.

## Lane Rules

| Rule | `lane_suggestion` |
| --- | --- |
| `UNKNOWN_STYLE` | `WAITING_EVIDENCE` |
| `SINGLE_OUTCOME_DIRECTIONAL` mixed with `MULTI_OUTCOME_BASKET`, `BASKET_BURST`, `HIGH_PRICE_ACTIVITY`, or `POSITION_BUILDING` | `REVIEW_REQUIRED` with `lane_reason=mixed_style_evidence` |
| `BASKET_BURST` or `HIGH_PRICE_ACTIVITY` or `FREQUENT_BUY_SELL_ROTATION` or `RANGE_DOMINANT` | `LEARNING_REFERENCE_CANDIDATE` |
| City overlap with `{Shanghai, Tokyo, Buenos Aires, Ankara}` and at least 70% of markets in `{exact, at_or_above, at_or_below}`, with no disqualifying label above | `COMPARABLE_CANDIDATE` |
| Everything else | `REVIEW_REQUIRED` |

`BUY_SELL_PRESENT` is informational. It does not degrade comparability by itself; only `FREQUENT_BUY_SELL_ROTATION` can contribute to `LEARNING_REFERENCE_CANDIDATE`.

`manual_review_required` is true when the lane is `REVIEW_REQUIRED`, query status is `partial`/`failed`, either side is capped, parse unknown ratio exceeds 20%, or potentially incompatible patterns appear, such as `SINGLE_OUTCOME_DIRECTIONAL` with `BASKET_BURST`.

Confidence is based on fill count: `high` at 20+, `medium` at 5+, `low` at 3+, otherwise `insufficient_data`.

## Safety Notes

`lane_suggestion` is not a definitive state, does not authorize copy-trading, and does not change the bot. Any promotion to a definitive status requires a separate Opus/human decision.

The tool is intentionally not coupled to runtime:

- It does not import `bot.py`.
- It does not import scheduler/runtime modules.
- It does not import from `src/`.
- It does not import trading modules.
- It does not touch Telegram, DB, env vars, BANKROLL, trading core, whitelist, sizing, city modes, guards, or Phase C.
