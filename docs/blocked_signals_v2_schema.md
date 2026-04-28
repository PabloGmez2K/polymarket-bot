# blocked_signals_resolutions.jsonl — Schema v2

Implemented in v10.6.44 (Fase A). Append-only JSONL; one record per signal+outcome+trader combination resolved.

## Backward compatibility

Records without `schema_version` are treated as v1 implicitly. All v1 fields are present unchanged in v2. The dedup index accepts both `canonical_signal_id` (v2) and `match_key` (v1 fallback), so v1 and v2 records coexist.

## Fields

| Field | Type | v1 | v2 | Notes |
|---|---|---|---|---|
| `schema_version` | int | absent | 2 | absent = v1 implícito |
| `canonical_signal_id` | str | absent | always | deterministic dedupe key |
| `checked_at` | str (ISO) | ✓ | ✓ | |
| `match_key` | str | ✓ | ✓ | |
| `city` | str | ✓ | ✓ | |
| `date` | str (ISO date) | ✓ | ✓ | |
| `condition` | str | ✓ | ✓ | |
| `trader` | str | ✓ | ✓ | |
| `trader_historical_wr` | float | ✓ | ✓ | |
| `outcome` | str | ✓ | ✓ | "Yes" or "No" |
| `avg_price_entered` | float | ✓ | ✓ | |
| `close_price` | float | ✓ | ✓ | price for trader's outcome side |
| `resolved` | bool | ✓ | ✓ | yes_p>=0.95 or no_p>=0.95 |
| `win_for_trader` | bool | ✓ | ✓ | |
| `has_consensus` | bool | ✓ | ✓ | |
| `market_id` | str\|null | — | always | Polymarket market ID |
| `condition_id` | str\|null | — | always | |
| `token_id_yes` | str\|null | — | always | clobTokenIds[0] |
| `token_id_no` | str\|null | — | always | clobTokenIds[1] |
| `market_slug` | str\|null | — | always | |
| `city_mode_at_record_time` | str | — | always | active/canary/shadow/blocked/unknown |
| `whitelist_status_at_record_time` | str | — | always | "in" or "out" |
| `city_policy_status_at_record_time` | str | — | always | see _classify_city_bucket |
| `reason_blocked` | str | — | always | see enum below |
| `block_reason_detail` | str | — | always | free-text detail |
| `resolution_source` | str | — | always | "polymarket_market_price" |
| `observed_coverage_status` | str | — | always | see enum below |
| `price_bucket` | str | — | always | see enum below |
| `settlement_source` | str | — | null/unknown | "unknown" until Fase C |
| `settlement_fidelity_status` | str | — | null/unknown | "unverified" until Fase C |
| `bot_edge_pct_at_signal` | float\|null | — | null | None until Fase C |
| `bot_would_have_bought` | bool\|null | — | null | None until Fase C |
| `bot_evaluation_source` | str | — | null/unknown | "unknown" until Fase C |

## Enums

**reason_blocked:** `out_of_whitelist` | `blocked_city` | `shadow_only_mode` | `condition_filtered` | `settlement_risk` | `mixed` | `unknown`

**observed_coverage_status:** `noaa_configured` | `icao_only` | `open_meteo_proxy_only` | `no_local_station` | `unknown`

**city_policy_status_at_record_time:** `BLOCKED` | `ACTIVE` | `CANARY` | `OBSERVED_AUDIT` | `SHADOW` | `UNTRACKED` | `unknown`

**price_bucket:** `<0.2` | `0.2-0.4` | `0.4-0.6` | `0.6-0.8` | `>0.8` | `unknown`

## Phases

- **Fase A (v10.6.44):** logging enriquecido aditivo. Settlement/edge fields are null/unknown.
- **Fase B:** `tools/blocked_signals_audit.py` para análisis automatizado.
- **Fase C:** cruce con truth pipeline (requiere SQLite recorder Fase 1 live). Populates settlement_source, settlement_fidelity_status, bot_edge_pct_at_signal, bot_would_have_bought.
