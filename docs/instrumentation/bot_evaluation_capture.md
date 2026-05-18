# Bot Evaluation Capture

Status: Phase 0 LOG_ONLY. This patch captures what the bot evaluated; it does not change trading behavior.

## Objective

Blocked trader signals can show trader WR, but they do not show whether the bot would have passed its own gates at the same moment. `bot_signal_evaluations.jsonl` fills that gap so a future Trader vs Bot Gap Report can estimate opportunity lost, avoided loss, and true trader-vs-bot divergence.

## JSON Contract

Artifact: `data/bot_signal_evaluations.jsonl`

Each line is append-only JSON with:

- `schema_version`
- `ts_utc`
- `cycle_id`
- `eval_key`
- `city`
- `date_iso`
- `condition`
- `threshold`
- `threshold_high`
- `unit`
- `would_buy`
- `bot_edge_pct_at_signal`
- `evaluation_source` = `live_eval`
- `skip_or_block_reason`
- `decision_gate`
- `decision_confidence`
- `our_prob`
- `mkt_prob`
- `forecast_max`
- `sigma_used`
- `days_ahead`

`eval_key` matches the existing trader signal key shape:
`city|date_iso|condition|threshold[-threshold_high]|unit`.

## Guardrails

- LOG_ONLY append-only telemetry.
- No BUY/SELL/SKIP changes.
- No filter, edge, sizing, bankroll, scheduler, DB, Telegram, NOAA, source policy, whitelist, or city mode changes.
- Capture is best-effort and no-throw; I/O errors are swallowed.
- No secrets are written.
- Historical `unknown` behavior remains unchanged unless the read gate is explicitly enabled.

## Env Vars

- `DISABLE_BOT_EVAL_CAPTURE=1`: disables the writer.
- `READ_BOT_EVAL_CAPTURE=1`: enables resolver joins into `blocked_signals_resolutions.jsonl`.
- Default read behavior is off: `READ_BOT_EVAL_CAPTURE=0`.

## Rollout

1. Deploy with writer enabled and read gate off.
2. Let `data/bot_signal_evaluations.jsonl` accumulate live rows.
3. Flip `READ_BOT_EVAL_CAPTURE=1` only after review.
4. Confirm new blocked signal resolutions show `bot_evaluation_join_status="captured"` for matching `eval_key` rows.

## Phase 1 Gap Report

The next report should join trader signal outcomes, blocked resolutions, and bot evaluation rows by `eval_key`. It should segment:

- trader won and bot would have bought: confirmed missed opportunity
- trader won and bot would not have bought: avoided by bot filters or non-executable trader edge
- trader lost and bot would have bought: avoided loss if blocked, bot-risk if unblocked
- trader lost and bot would not have bought: filter-confirming evidence

## Opus Criteria

Success:

- Rows accumulate with `evaluation_source="live_eval"`.
- Resolver remains `unknown` by default.
- With read gate enabled, matching signals become `live_eval/captured`.
- No runtime decisions change.

Stop:

- Any evidence that capture affects control flow.
- JSONL write failures surfacing into cycle execution.
- Join rate too low to support gap analysis without an `eval_key` review.
