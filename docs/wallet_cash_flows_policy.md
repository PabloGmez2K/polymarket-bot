# Wallet Cash Flows Attestation Policy

**Status:** POLICY / MANUAL_ONLY / NOT_CANONICAL  
**Date:** 2026-05-06  
**Scope:** `wallet_cash_flows.jsonl` future manual attestation for wallet P/L readiness  

This policy documents the anti-falsification rules for wallet cash flow evidence. It is documentation only. It does not implement runtime behavior, does not promote wallet P/L, and does not authorize BANKROLL changes, Telegram real P/L, dashboard scraping, or Phase C.

## Purpose

`wallet_cash_flows.jsonl` is the future manual ledger for deposits, withdrawals, explicit no-cash-flow attestations, and reviewed adjustments that affect wallet P/L calculations.

The file exists to answer one narrow question before `wallet_pnl_7d` can ever be promoted: did cash enter or leave the wallet during the evaluation window, and is that fact explicitly documented by Pablo?

## File Existence Policy

- Do not create a real `data/wallet_cash_flows.jsonl` file silently.
- Do not create an empty real `data/wallet_cash_flows.jsonl` file.
- A real file may exist only as a manual runtime artifact when Pablo explicitly decides to start the formal counter.
- Future Railway canonical path: `/app/data/wallet_cash_flows.jsonl`.
- Local default state: absent.
- Railway default state: absent until explicit manual action by Pablo.
- Git must not version real cash flow rows.
- Git may version this policy, `data/wallet_cash_flows.example.jsonl`, and a `.gitignore` rule that excludes the real file.

## Proposed Schema v2

Every productive row must be JSONL with these required fields:

- `schema_version`: always `2`
- `entry_id`: stable unique id; productive ids must not start with `EXAMPLE-`
- `recorded_at`: ISO-8601 UTC timestamp
- `actor`: `pablo_manual`
- `type`: one of the allowed types below
- `period_start`: ISO-8601 UTC timestamp or date boundary for the covered period
- `period_end`: ISO-8601 UTC timestamp or date boundary for the covered period

Allowed `type` values:

- `deposit`
- `withdrawal`
- `no_cash_flow_attestation`
- `adjustment`

Forbidden `type` values:

- `inferred`
- `auto`
- `reconstructed`
- `estimated`

## No-Cash-Flow Periods

"No deposits or withdrawals happened" must be recorded with an explicit `no_cash_flow_attestation` row.

An empty file is not an attestation. It is not proof. It must not unlock readiness.

## Anti-Falsification Rules

- Empty file means `empty_unattested`, not `present`.
- A future valid readiness status must be `attested_full_7d`, not merely `present`.
- `actor` must be `pablo_manual`.
- Any productive `entry_id` starting with `EXAMPLE-` must be rejected.
- Coverage must be contiguous for the full 7-day readiness window.
- `possible_deposit` without a documented explanation blocks readiness.
- `adjustment` requires human review before it can support readiness.
- Promotion of `canonical_source` requires Opus review and Pablo signoff.
- `wallet_pnl_7d` is not promoted by this policy.
- `canonical_source` remains `none`.
- `bankroll_readiness` remains `blocked`.

## What Not To Do

- Do not create real `data/wallet_cash_flows.jsonl`.
- Do not use example rows as productive data.
- Do not unlock wallet P/L readiness.
- Do not touch BANKROLL.
- Do not send Telegram real messages with P/L.
- Do not implement a dashboard scraper or extractor.
- Do not treat file existence as evidence.

## Future Patch Interaction

Patch B, if approved separately, should update `tools/wallet_snapshot.py` to read schema v2 and should update `tools/daily_kanban_digest.py` to distinguish:

- `missing`
- `empty_unattested`
- `attested_partial`
- `attested_full_7d`
- `unreconciled`

Patch B should gate readiness on `attested_full_7d`, not `present`.

Patch C, if approved separately, may introduce a manual CLI such as `tools/wallet_cash_flow_log.py` to append validated rows. That CLI must remain manual-only and reject examples, inferred rows, auto rows, reconstructed rows, and estimated rows.
