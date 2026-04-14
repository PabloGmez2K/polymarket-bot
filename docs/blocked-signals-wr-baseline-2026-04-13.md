# Blocked Signals WR Baseline — 2026-04-13

**Generated:** 2026-04-14 08:21 UTC
**Source:** `data/runtime_import/signals.json` (Apr 13 snapshot)
**Scope:** quality-trader signals with `condition in {exact, range}` and `date <= cutoff-1d`

## Overall

| Metric | Value |
|--------|-------|
| Records in JSONL | 59 |
| Resolved | 59 |
| Wins | 45 |
| **WR** | **76.3%** |

**Verdict:** REOPEN CANDIDATE (WR=76.3% >= 55% on n=59)

## By Condition

| Condition | Wins | Total | WR |
|-----------|------|-------|----|
| `exact` | 37 | 51 | 72.5% |
| `range` | 8 | 8 | 100.0% |

## By City (n >= 3)

| City | Wins | Total | WR |
|------|------|-------|----|
| Toronto | 3 | 4 | 75.0% |
| Seoul | 3 | 4 | 75.0% |
| Seattle | 3 | 3 | 100.0% |
| Tokyo | 3 | 3 | 100.0% |
| Hong Kong | 3 | 3 | 100.0% |
| Milan | 2 | 3 | 66.7% |
| Shenzhen | 2 | 3 | 66.7% |
| London | 1 | 3 | 33.3% |
| Chengdu | 2 | 3 | 66.7% |
| Shanghai | 2 | 3 | 66.7% |

## Consensus vs Solo

| Type | Wins | Total | WR |
|------|------|-------|----|
| Consensus | 6 | 9 | 66.7% |
| Solo | 39 | 50 | 78.0% |

## Decision Thresholds (from handoff)

| Range | Action |
|-------|--------|
| WR >= 55% (n >= 50) | Reopen filter with canary experiment |
| 50–55% | Gray zone — expand sample before deciding |
| WR < 50% | Filter validated — freeze 3+ months |

*Robust decision threshold: n >= 50. Current: n = 59.*
