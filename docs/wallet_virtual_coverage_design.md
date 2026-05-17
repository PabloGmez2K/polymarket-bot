# Wallet Virtual Coverage Design

**Status:** ACTION_DESIGN / LOG_ONLY / NOT_CANONICAL
**Date:** 2026-05-17
**Scope:** Prototype design for B5/B6 wallet virtual coverage

This document designs a LOG_ONLY prototype. It does not implement runtime behavior,
does not modify existing tools, does not write wallet data, and does not promote
wallet P/L to canonical.

## 1. Design Goal

The current manual-only attestation model is anti-falsification friendly, but it
does not scale if Pablo must add a new `no_cash_flow_attestation` row every day
only to say that nothing happened.

The goal is to preserve the anti-falsification guarantees while allowing a
derived LOG_ONLY coverage state:

- Manual cash-flow rows remain the only canonical evidence.
- Daily automatic no-cash-flow rows are not written to
  `wallet_cash_flows.jsonl`.
- A virtual coverage window may be derived from a mandatory manual base anchor
  plus detector evidence that found no credible cash-flow anomaly.
- Any detector failure, missing data, timeout, discrepancy, or suspicious wallet
  movement fails closed to `unreconciled`.

Pablo's operational rule is valid as direction:

> If Pablo does not report a deposit or withdrawal, the system assumes no
> cash-flow.

For this design that rule is not canonical evidence. It only supports a separate
derived state, `attested_virtual`, which B5/B6 may accept or reject explicitly.

## 2. Proposed States

### `missing`

No usable cash-flow evidence is available for the requested window. This includes
the absence of a manual base anchor, absent snapshot history, or no detector
run. Downstream consumers must treat this as not covered.

### `base_anchored`

A required manual base exists at `base_t0`, but the requested window is not yet
covered by enough detector runs to claim virtual continuity. This is an
intermediate LOG_ONLY state, not readiness.

### `attested_virtual`

The requested window is covered by:

- a valid manual `base_t0`;
- no manual override indicating deposit or withdrawal inside the virtual window;
- all required detectors having run successfully;
- no anomaly flags that require review;
- no dashboard/manual discrepancy if Pablo supplied a dashboard reading.

`attested_virtual` is derived coverage only. It is not equivalent to
`attested_full_7d`, does not write rows into `wallet_cash_flows.jsonl`, and does
not become canonical by repetition.

### `unreconciled`

The system cannot safely say that the window has no external cash-flow. This
state is used for detected anomalies and for detector failures. It is the default
fail-closed target.

### `attested_full_7d`

The existing strict state where the full 7-day window is covered by explicit
manual rows in `wallet_cash_flows.jsonl`, following the wallet cash-flow policy.
This remains the stronger, canonical-eligible evidence class.

B5/B6 must declare which states they accept. For example, B5 may accept
`attested_virtual` for LOG_ONLY comparison while B6 may still require
`attested_full_7d` for any promotion review.

## 3. Minimum Detectors

All detector results are LOG_ONLY inputs. They may support `attested_virtual`
only if they run successfully and produce no blocking flags.

Initial thresholds are conservative defaults for prototype review, not executable
policy.

### `possible_deposit`

Inputs:

- wallet portfolio snapshots;
- cash balance when available;
- active positions value;
- resolved pending value;
- manual cash-flow rows, if any.

Initial threshold:

- positive unexplained equity delta greater than `max(1.50 USDC, 5% of base_t0
  total_value)`.

Fail-closed behavior:

- if the jump cannot be explained by closed market P/L, mark `unreconciled`;
- if required inputs are missing, mark `unreconciled`.

### `possible_withdrawal`

Inputs:

- wallet portfolio snapshots;
- cash balance when available;
- position inventory deltas;
- manual withdrawal rows, if any.

Initial threshold:

- negative unexplained equity delta greater than `max(1.50 USDC, 5% of base_t0
  total_value)`.

Fail-closed behavior:

- if the drop cannot be explained by market losses, buys, fees, or settlement
  timing, mark `unreconciled`;
- if the detector cannot separate withdrawal from trading loss, mark
  `unreconciled`.

### `equity_jump`

Inputs:

- total wallet value per snapshot;
- closed/resolved position events where available;
- latest known open exposure.

Initial threshold:

- single-snapshot absolute equity movement greater than `2.00 USDC` or `7.5%`
  of prior total value, whichever is larger.

Fail-closed behavior:

- if the movement is not explained by observed market settlement or mark-to-
  market change, mark `unreconciled`.

### `withdrawal_like_drop`

Inputs:

- cash balance;
- total value;
- open positions;
- redeemable/resolved pending value.

Initial threshold:

- cash or total-value drop greater than `2.00 USDC` with no matching buy,
  negative P/L event, or position-value migration.

Fail-closed behavior:

- if the drop could be a withdrawal and cannot be disproved, mark
  `unreconciled`.

### `adjustment_pending`

Inputs:

- manual `adjustment` rows;
- any future reviewed correction queue;
- detector notes that require human explanation.

Initial threshold:

- any pending or unreviewed adjustment is blocking.

Fail-closed behavior:

- mark `unreconciled` until Pablo review resolves it.

### Detector Timeout / No Run / Missing Data

Inputs:

- detector run metadata;
- expected daily schedule;
- snapshot availability;
- parse status for all input files.

Initial threshold:

- no successful detector run for a calendar day inside the evaluated virtual
  window;
- detector run older than 36 hours for a daily coverage claim;
- corrupt, missing, or partial input needed by any detector.

Fail-closed behavior:

- mark `unreconciled` with `fail_closed_reason` such as `detector_timeout`,
  `detector_no_run`, `missing_snapshot`, or `input_parse_error`.

### Dashboard / Manual Discrepancy

Inputs:

- Pablo's manual dashboard reading, if supplied;
- LOG_ONLY computed wallet P/L or equity delta for the same labeled horizon;
- notes about dashboard horizon and capture time.

Initial threshold:

- discrepancy greater than `0.50 USDC` for short windows;
- discrepancy greater than `1.50 USDC` for 7-day style review;
- any mismatch in horizon definition that cannot be normalized.

Fail-closed behavior:

- mark `unreconciled` until the discrepancy is explained;
- do not assume the dashboard is API canonical, because the dashboard method is
  opaque and manual-only in this design.

## 4. `base_t0` Rule

Virtual coverage requires a manual base anchor.

Required fields for `base_t0`:

- timestamp;
- actor, normally `pablo_manual`;
- wallet total value reading or enough wallet components to reconstruct it;
- statement that known deposits/withdrawals up to that timestamp have been
  reviewed;
- source note, for example manual dashboard reading, wallet snapshot, or both.

Expiration and re-anchor:

- initial prototype default: `base_t0` expires after 14 calendar days;
- Opus/Pablo may choose a shorter `N` if detector quality is weak;
- after expiry, status cannot remain `attested_virtual`; it falls back to
  `base_anchored` or `missing` until a new base is supplied.

Manual override:

- if Pablo reports a deposit, withdrawal, or correction, that override wins over
  virtual continuity;
- the override splits the virtual window;
- coverage before and after the override must be evaluated as separate windows;
- the post-override segment needs a new `base_t0` or an explicit reviewed anchor.

## 5. Output Contract for B5/B6

Proposed LOG_ONLY output fields:

```json
{
  "status": "attested_virtual",
  "coverage_days_explicit": 0,
  "coverage_days_virtual": 7,
  "base_t0": {
    "timestamp": "2026-05-10T08:00:00Z",
    "total_value_usdc": "35.00",
    "source": "pablo_manual_dashboard_plus_snapshot"
  },
  "actor": "derived_log_only",
  "anomaly_flags": [],
  "review_required": false,
  "fail_closed_reason": null,
  "last_detector_run_at": "2026-05-17T08:05:00Z",
  "dashboard_reconciliation_status": "not_supplied",
  "canonical_eligible": false
}
```

Field meanings:

- `status`: one of `missing`, `base_anchored`, `attested_virtual`,
  `unreconciled`, `attested_full_7d`.
- `coverage_days_explicit`: days covered by manual canonical rows.
- `coverage_days_virtual`: days covered only by derived LOG_ONLY continuity.
- `base_t0`: manual anchor used for virtual derivation.
- `actor`: `pablo_manual` for explicit manual rows; `derived_log_only` for
  virtual state.
- `anomaly_flags`: detector flags such as `possible_deposit` or
  `withdrawal_like_drop`.
- `review_required`: true whenever human explanation is required.
- `fail_closed_reason`: machine-readable reason for `unreconciled`.
- `last_detector_run_at`: timestamp of the latest successful detector run.
- `dashboard_reconciliation_status`: `not_supplied`, `matched`,
  `discrepant`, `horizon_mismatch`, or `manual_review_pending`.
- `canonical_eligible`: false by default for this prototype.

## 6. Shadow LOG_ONLY Plan: At Least 14 Days

Run the prototype in shadow for at least 14 days before asking Opus to consider
any further promotion.

Daily calculation:

- load the current manual base anchor;
- load wallet snapshots and any existing manual cash-flow rows;
- run all minimum detectors;
- compute candidate status for 1-day, 7-day, and since-`base_t0` windows;
- reconcile against Pablo's manual dashboard reading only when he supplies one;
- emit a LOG_ONLY record without changing canonical files.

Daily log fields:

- generated timestamp;
- evaluated window;
- status;
- explicit and virtual coverage days;
- detector run status per detector;
- anomaly flags;
- fail-closed reason;
- dashboard reconciliation status;
- whether B5 would accept the state;
- whether B6 would accept the state;
- `canonical_eligible=false`.

Safety metrics:

- days with all detectors successful;
- days failed closed;
- count and type of anomaly flags;
- count of Pablo manual overrides;
- dashboard discrepancy distribution when readings exist;
- number of times virtual coverage would have disagreed with manual evidence;
- stale or missing detector runs.

Criteria to return to Opus:

- at least 14 consecutive days of LOG_ONLY logs;
- zero unexplained detector failures, or every failure correctly marked
  `unreconciled`;
- no case where virtual state contradicted Pablo's manual report;
- dashboard discrepancies explained or explicitly classified as opaque/manual;
- B5/B6 acceptance matrix drafted with explicit state handling;
- no writes to `wallet_cash_flows.jsonl` except manual rows separately approved
  by Pablo.

## 7. Manual Reconciliation Plan: `$20.52` vs `$0.32`

This section is read-only design for explaining the observed gap. It does not
declare either number canonical.

Questions to answer:

- which closed outcomes compose the `+$20.52`;
- which of those entered the window because `closed_at` fell inside the window
  even though the underlying market belonged to an earlier date;
- what remains if the same set is filtered by market date or resolution date;
- how the result compares to dashboard 1M without treating dashboard display as
  an API-canonical source.

Manual/read-only procedure:

1. Export or inspect the closed records that sum to `+$20.52`, preserving
   market id, question/title, city if available, market date, resolution date,
   `closed_at`, realized P/L, and source quality.
2. Group the records by inclusion reason:
   `closed_at_inside_window`, `market_date_inside_window`,
   `resolution_date_inside_window`, and `unknown_date_basis`.
3. Identify records where `closed_at` is inside the window but the market date
   or resolution date is older than the dashboard-like 1M period.
4. Recompute three read-only totals:
   `total_by_closed_at`, `total_by_market_date`, and
   `total_by_resolution_date`.
5. Compare each total with Pablo's dashboard 1M reading of `$0.32`, using the
   dashboard as manual opaque reference only.
6. Classify the gap as one or more of:
   delayed close ingestion, settlement timing, dashboard horizon mismatch,
   open-position mark-to-market difference, cash-flow mismatch, contaminated
   lifecycle source, or unexplained.

The expected output is a reconciliation note, not a data mutation. If any
component cannot be explained, B5/B6 should keep the related state
`unreconciled`.

## 8. What This Design Does Not Do

This design explicitly does not:

- authorize BANKROLL `$35`;
- activate Fase C;
- activate Truth Pipeline;
- write rows into `wallet_cash_flows.jsonl`;
- backfill daily no-cash-flow attestations;
- scrape the Polymarket dashboard;
- change trading behavior;
- change city modes;
- change scheduler behavior;
- change `pnl_report.py`;
- change `wallet_snapshot.py`;
- change `bankroll_readiness_score.py`;
- change env vars;
- write to DB;
- use Railway;
- promote Telegram actionable P/L;
- convert `attested_virtual` into canonical evidence;
- convert `attested_virtual` into `attested_full_7d`.

`attested_virtual` is a LOG_ONLY review state. It can inform B5/B6 design
discussion, but canonical promotion remains blocked unless separately approved
by Opus and Pablo under the stricter policy.
