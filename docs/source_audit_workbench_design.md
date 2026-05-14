# Source Audit Workbench v1.0

> Piece of City Intelligence v2. It sits between Source Onboarding Scanner and a human OBSERVED_AUDIT review.

## Purpose

`tools/source_audit_workbench.py` turns one Source Onboarding candidate into a small, reviewable source-audit package.
It answers one question: does this city have enough verifiable source/proxy metadata to send to Opus for OBSERVED_AUDIT-only review?

The tool is read-only and LOG_ONLY. It does not edit `bot.py`, city modes, policy files, Railway, Telegram, DB, or runtime data.

## Inputs

All inputs are CLI paths:

| Flag | Default |
|---|---|
| `--city` | required |
| `--candidate-source` | `data/source_onboarding.json` |
| `--signals-crosscheck` | `data/runtime_import_derived/signals_crosscheck.jsonl` |
| `--blocked-resolutions` | `data/runtime_import_derived/blocked_signals_resolutions.jsonl` |
| `--policy-env` | `data/runtime_import/policy_env_snapshot.json` |
| `--policy-state` | `data/runtime_import/city_policy_state.json` |
| `--output-json` | `data/source_audits/<city_slug>_source_audit.json` |
| `--output-md` | `docs/source_audits/<city_slug>_source_audit.md` |

Optional human-supplied source fields:

- `--icao`
- `--noaa-daily-station-id`
- `--noaa-station-id`
- `--polymarket-source-url`
- `--wu-url`

The workbench parses selected constants from `bot.py` via AST without importing or executing the bot.

## Outputs

JSON includes:

- `city`
- `status`
- `source_candidate`
- `evidence`
- `risk`
- `recommendation`
- `proposed_next_step`

Markdown includes:

- verdict
- evidence
- candidate source
- mismatch risk
- recommendation
- LOG_ONLY disclaimer

Generated JSON under `data/source_audits/` is ignored. Markdown source-audit packages under `docs/source_audits/` are not ignored by default, so a human can decide to version the useful packages.

## Statuses

| Status | Meaning |
|---|---|
| `SOURCE_AUDIT_PASS` | Source fields validate structurally, but evidence is not clean enough for direct review-ready wording. |
| `SOURCE_AUDIT_FAIL` | Supplied source fields fail structural validation. |
| `NEEDS_MANUAL_SOURCE_LOOKUP` | Candidate lacks enough public source metadata. |
| `READY_FOR_OBSERVED_AUDIT_REVIEW` | Candidate has ICAO plus NOAA daily/hourly metadata and is suitable for Opus review. |
| `ALREADY_OBSERVED` | City is already in observed-audit scope. |
| `OUT_OF_SCOPE` | City is already active/canary/auto-canary or otherwise outside this workbench path. |

## Example

```powershell
python tools/source_audit_workbench.py `
  --city "San Francisco" `
  --candidate-source data/source_onboarding.json `
  --no-network
```

With no supplied source IDs, the expected clean degradation is `NEEDS_MANUAL_SOURCE_LOOKUP`.

```powershell
python tools/source_audit_workbench.py `
  --city "San Francisco" `
  --icao KSFO `
  --noaa-daily-station-id USW00023234 `
  --noaa-station-id 72494023234 `
  --wu-url "https://www.wunderground.com/history/daily/KSFO/date/{date}" `
  --no-network
```

With structurally valid IDs, the package can move to source-audit pass or OBSERVED_AUDIT review, depending on range-only risk and evidence mix.

## Flow

1. Source Onboarding Scanner finds a city outside the current runtime flow.
2. Source Audit Workbench gathers evidence and source metadata into a human review package.
3. Opus reviews whether OBSERVED_AUDIT-only is appropriate.
4. If a human later edits observed-audit config, City Lifecycle Review Monitor watches the city under its own jurisdiction.
