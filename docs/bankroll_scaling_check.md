# Bankroll Scaling Check

`tools/bankroll_scaling_check.py` is a read-only assistant for the manual bankroll scaling policy in `docs/bankroll_scaling_policy.md`.

It answers one narrow question: is there enough evidence to open a manual review for the next bankroll tier?

It never authorizes an automatic increase.

## How to run

Local defaults:

```powershell
python tools/bankroll_scaling_check.py --markdown
python tools/bankroll_scaling_check.py --json
```

Production-style paths:

```powershell
python tools/bankroll_scaling_check.py --data-dir /app/data --db /app/data/polymarket.db --markdown
python tools/bankroll_scaling_check.py --data-dir /app/data --db /app/data/polymarket.db --json
```

Optional tier override:

```powershell
python tools/bankroll_scaling_check.py --current-bankroll 25 --target-tier 35 --log-tail 200 --markdown
```

Defaults:

- `--data-dir data`
- `--db data/polymarket.db`
- `--current-bankroll auto`, falling back to `25`
- `--target-tier auto`, using the next tier from `25,35,50,75,100`
- `--log-tail 200`

## What It Reads

If present, the tool reads:

- `cycle_summary.json`
- `cycles_history.jsonl`
- `trade_lifecycle.json`
- `postmortem.json`
- `performance.json`
- `bankroll_readiness_state.json`
- `polymarket.db` with SQLite URI `mode=ro`
- `decisions.log`
- `trades.log`

It also checks `data/runtime_import/` as a fallback for runtime files when the direct path under `--data-dir` is missing.

For `bankroll_readiness_state.json`, it checks these locations:

- `--data-dir/bankroll_readiness_state.json`
- `./data/bankroll_readiness_state.json`
- `./bankroll_readiness_state.json`

If none exists, the score is reported as unavailable with `paths_checked`. That is not treated as a script bug; it means the readiness score tool has not produced persistent state in that environment. Because the scaling policy requires a score threshold, missing score evidence still blocks eligibility.

## What It Does Not Do

The tool does not:

- increase bankroll;
- change environment variables;
- write files;
- modify SQLite;
- send Telegram;
- make external network calls;
- backfill data;
- touch `bot.py`;
- touch trading core, purchases, sales, sizing, city modes, scheduler, NOAA, whitelist, or risk rules.

## Status Meaning

- `ELIGIBLE_FOR_MANUAL_REVIEW`: no hard blockers were detected and important evidence is present. The decision is still manual.
- `NOT_ELIGIBLE`: evaluated evidence is insufficient for manual review.
- `BLOCKED`: one or more hard blockers were detected.
- `UNKNOWN`: important evidence is missing or unreadable, so the tool refuses to mark the system eligible.

## Policy Relationship

The tool implements a conservative read-only interpretation of `docs/bankroll_scaling_policy.md`.

For `$25 -> $35`, it checks at least:

- stable cycles threshold;
- SQLiteRecorder freshness and large gaps;
- Phase 1 readiness as a conservative gate. Pending Phase 1 is shown as `pending`, not `pass`, until readiness is actually true;
- PnL non-negative;
- win rate threshold;
- drawdown over the last five closes above `-$3`;
- bankroll readiness score threshold;
- absence of critical execution errors and stuck pending exits.

For `$35 -> $50` and above, Phase 1 readiness must be ready. Higher tiers add conservative checks for Truth Pipeline, settlement fidelity, and replay/shadow evidence where applicable.

When evidence cannot be evaluated, the tool adds it to `missing_evidence` instead of inventing a pass.

## Manual-Only Rule

`eligible_for_manual_review: true` means only that a human may open a review.

It does not mean "increase bankroll now". The only possible positive decision is `manual_review_required`; the tool never emits an automatic scaling authorization.

## Telegram Observability

`bot.py` can now surface the same read-only check from Telegram:

- manual commands: `/bankroll` and `/bankroll_status`;
- automatic monitor: `maybe_run_bankroll_scaling_monitor(state)` inside observability;
- anti-spam state: `alerts_state.json` keys prefixed with `bankroll_scaling_last_*`.

The monitor sends Telegram only when status, target tier, or hard blockers change; when the result first becomes `ELIGIBLE_FOR_MANUAL_REVIEW`; or after `BANKROLL_SCALING_MONITOR_EVERY_CYCLES` cycles as a compact digest. If the CLI fails, the bot logs a warning and sends no alert.

The Telegram copy is intentionally manual-only: it can say `BLOCKED`, `NOT_ELIGIBLE`, `eligible for manual review`, or `no subir bankroll`. It also states that the alert does not authorize automatic scaling or changing `BANKROLL`.
