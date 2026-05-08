# Traders Intelligence V1 activation package

**Status:** `V1_PACKAGE_PREPARED / WAITING_CONFIRMATION`
**Prepared:** 2026-05-08
**Basis:** canonical Railway refresh session 330, commit `fd1db9a`

This package defines what "Traders Intelligence V1 active" means after the
canonical refresh reached `READY_CANDIDATE`. It does not activate trading,
scheduler, env vars, Telegram real delivery, policy, DB writes, or any
BUY/SELL/SKIP behavior.

## 1. Definition

`Traders Intelligence V1 active` means:

- the minimal V1 archivist `tools/traders_intelligence_snapshot.py` is allowed
  to run manually against a fresh `signals.json`;
- each run archives a filtered snapshot and pseudo-lifecycle report under
  `data/traders_intelligence/`;
- outputs are used only for observability, daily review, and manual learning;
- the system may discuss `appeared`, `still_present`,
  `disappeared_apparent`, and `reappeared` events, always with caveats;
- V1 remains non-executable and cannot alter bot policy.

V1 active does **not** mean the bot follows traders, copies exits, changes
city modes, changes sizing, changes risk rules, sends actionable Telegram, or
promotes BANKROLL/Fase C readiness.

## 2. Inputs

V1 uses these inputs:

- fresh `signals.json`, canonical in Railway as `/app/data/signals.json` or
  local runtime snapshot as `data/runtime_import/signals.json`;
- the V0 report `/app/data/traders_intelligence.json`, or local equivalent,
  only as readiness context;
- `signals_crosscheck.jsonl` as evidence that trader/bot gaps are deep enough;
- existing V1 snapshot history under `data/traders_intelligence/`, if any.

The canonical readiness evidence from session 330 used:

- `crosscheck_series=/app/data/signals_crosscheck.jsonl`;
- `census_stale_days=0`;
- `recent_crosscheck_runs=7`;
- `health_status=usable_signal`;
- `V1 readiness=ready`;
- strong traders: `Entire-Hood`, `Dimpled-Boy`, `Loyal-Aggression`;
- trader-only cities: `Los Angeles`, `Miami`, `San Francisco`, `Tel Aviv`.

## 3. Outputs

The current V1 tool writes only runtime/regenerable artifacts:

- `data/traders_intelligence/snapshots/<run_id>.json`;
- `data/traders_intelligence/reports/<run_id>.json`;
- `data/traders_intelligence/pseudo_lifecycle_runs.jsonl`.

Each report is observational and carries guardrails:

- `does_not_modify_signals_json=true`;
- `does_not_trade=true`;
- `does_not_change_policy=true`;
- `not_a_trading_signal=true`.

## 4. Scope

The minimal V1 scope is intentionally narrow and inherited from
`tools/traders_intelligence_snapshot.py`:

- traders: `Thrifty-Original`, `Entire-Hood`;
- cities: `Houston`, `Los Angeles`, `Manila`, `Miami`.

The broader READY evidence from session 330 includes additional strong traders
and cities. Expanding the V1 snapshot scope to include `Dimpled-Boy`,
`Loyal-Aggression`, `San Francisco`, or `Tel Aviv` is a separate design/code
change and is not part of this activation package.

## 5. Gates To Maintain

V1 may remain active only while the V0 readiness gates remain healthy:

| Gate | Threshold |
| --- | --- |
| Health | `health_status=usable_signal` |
| Census freshness | `census_stale_days <= 14` |
| Crosscheck depth | `recent_crosscheck_runs >= 5` |
| Lead trader | `>=1` lead trader strong and very active |
| Strong trader depth | `>=2` strong traders |
| Candidate city gap | `>=3` trader-only cities among strong traders |

The current default thresholds live in
`tools/traders_intelligence_daily_summary.py`. This package does not change
them.

## 6. What V1 Enables

V1 enables:

- manual snapshot accumulation;
- pseudo-lifecycle event review for the fixed V1 scope;
- evidence for future questions such as "did a tracked trader disappear before
  resolution?";
- better daily-summary language when the system has fresh snapshots;
- manual review of whether trader-only cities keep recurring.

V1 can support a future design discussion. It cannot by itself justify
execution.

## 7. What Stays Out

Explicitly out of V1:

- automatic BUY/SELL/SKIP;
- following trader exits;
- changing `ACTIVE_TRADING_CITIES`, canary/shadow/block modes, whitelist, or
  sizing;
- changing BANKROLL readiness;
- Fase C;
- scheduler integration;
- Telegram actionable recommendations;
- DB writes;
- inference of confirmed stop loss, take profit, or hold duration.

`disappeared_apparent` is not a confirmed exit. It is only the absence of a
previously seen trader signal in a later filtered snapshot.

## 8. Degradation Back To WATCH

Move the package back to `WATCH` or `WAITING_EVIDENCE` if any of these occur:

- `health_status != usable_signal`;
- `census_stale_days > 14`;
- `recent_crosscheck_runs < 5`;
- fewer than two strong traders;
- fewer than three strong-trader trader-only cities;
- `signals.json` is stale or missing when a snapshot is attempted;
- V1 snapshot reports repeatedly produce `n_current_signals=0` because the
  fixed V1 scope no longer matches the READY evidence;
- pseudo-lifecycle reports are interpreted as confirmed exits or trading
  actions.

If the desired next step requires changing snapshot scope, adding a scheduler,
sending real Telegram, or deriving risk/trading semantics, stop and route the
decision to Opus before any patch.

## 9. Activation Checklist

To move from `V1_PACKAGE_PREPARED` to `V1_ACTIVE_OBSERVATIONAL`, perform a
separate confirmation step:

1. Confirm Railway is healthy and `/app/data/signals.json` is fresh.
2. Confirm V0 readiness still passes using canonical `/app/data` inputs.
3. Run one V1 snapshot in dry-run mode.
4. Run one real V1 snapshot manually if dry-run is coherent.
5. Record the run id, `n_current_signals`, status counts, and paths written.
6. Keep outputs observational-only and document the close.

No step in this checklist authorizes trading or policy changes.
