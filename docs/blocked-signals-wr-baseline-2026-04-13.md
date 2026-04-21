# Blocked Signals WR Baseline — 2026-04-13

**Generated:** 2026-04-21 12:51 UTC
**Source:** `data/runtime_import/signals.json` (Apr 13 snapshot)
**Scope:** quality-trader signals with `condition in {exact, range}` and `date <= cutoff-1d`

## Overall

| Metric | Value |
|--------|-------|
| Records in JSONL | 113 |
| Resolved | 113 |
| Wins | 93 |
| **WR** | **82.3%** |

**Verdict:** REOPEN CANDIDATE (WR=82.3% >= 55% on n=113)

## By Condition

| Condition | Wins | Total | WR |
|-----------|------|-------|----|
| `exact` | 78 | 98 | 79.6% |
| `range` | 15 | 15 | 100.0% |

## By City (n >= 3)

| City | Wins | Total | WR |
|------|------|-------|----|
| Chengdu | 5 | 6 | 83.3% |
| Seattle | 5 | 5 | 100.0% |
| Moscow | 5 | 5 | 100.0% |
| Tokyo | 5 | 5 | 100.0% |
| Paris | 2 | 5 | 40.0% |
| Toronto | 3 | 4 | 75.0% |
| Madrid | 3 | 4 | 75.0% |
| Hong Kong | 4 | 4 | 100.0% |
| Seoul | 3 | 4 | 75.0% |
| Shenzhen | 3 | 4 | 75.0% |
| London | 1 | 4 | 25.0% |
| Warsaw | 2 | 4 | 50.0% |
| Jeddah | 4 | 4 | 100.0% |
| Dallas | 3 | 3 | 100.0% |
| Milan | 2 | 3 | 66.7% |
| Wellington | 3 | 3 | 100.0% |
| Taipei | 3 | 3 | 100.0% |
| Shanghai | 2 | 3 | 66.7% |
| Amsterdam | 3 | 3 | 100.0% |
| Istanbul | 3 | 3 | 100.0% |
| Tel Aviv | 3 | 3 | 100.0% |

## Consensus vs Solo

| Type | Wins | Total | WR |
|------|------|-------|----|
| Consensus | 8 | 12 | 66.7% |
| Solo | 85 | 101 | 84.2% |

## Decision Thresholds (from handoff)

| Range | Action |
|-------|--------|
| WR >= 55% (n >= 50) | Reopen filter with canary experiment |
| 50–55% | Gray zone — expand sample before deciding |
| WR < 50% | Filter validated — freeze 3+ months |

*Robust decision threshold: n >= 50. Current: n = 113.*
