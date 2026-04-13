# Blocked Signals WR Baseline — 2026-04-13

**Generated:** 2026-04-13 15:11 UTC
**Source:** `data/runtime_import/signals.json` (Apr 13 snapshot)
**Scope:** quality-trader signals with `condition in {exact, range}` and `date <= cutoff-1d`

## Overall

| Metric | Value |
|--------|-------|
| Records in JSONL | 18 |
| Resolved | 18 |
| Wins | 18 |
| **WR** | **100.0%** |

**Verdict:** INSUFFICIENT SAMPLE (n=18 < 30) -- accumulate more resolutions

## By Condition

| Condition | Wins | Total | WR |
|-----------|------|-------|----|
| `exact` | 10 | 10 | 100.0% |
| `range` | 8 | 8 | 100.0% |

## By City (n >= 3)

| City | Wins | Total | WR |
|------|------|-------|----|
| Seattle | 3 | 3 | 100.0% |

## Consensus vs Solo

| Type | Wins | Total | WR |
|------|------|-------|----|
| Consensus | 1 | 1 | 100.0% |
| Solo | 17 | 17 | 100.0% |

## Decision Thresholds (from handoff)

| Range | Action |
|-------|--------|
| WR >= 55% (n >= 50) | Reopen filter with canary experiment |
| 50–55% | Gray zone — expand sample before deciding |
| WR < 50% | Filter validated — freeze 3+ months |

*Robust decision threshold: n >= 50. Current: n = 18.*
