# Source Parity Framework

**Mode:** LOG_ONLY measurement layer tooling  
**Authority:** No operational action. No BUY/SELL/SKIP. No whitelist, canary,
active, scheduler, env var, DB, BANKROLL, Fase C, or Truth Pipeline change.

## Purpose

The measurement layer verifies whether the bot's observation source matches the
source Polymarket uses to settle a weather market. This is separate from trader
quality, edge calculation, city mode, and bankroll policy.

For exact temperature markets, a small measurement mismatch can flip the edge:
the bot may price against an Open-Meteo proxy while Polymarket settles against
Weather Underground for a specific ICAO station. Beijing showed this structural
blocker clearly: Polymarket/Gamma settlement source was WU/ZBAA, while the bot
measurement was Open-Meteo proxy, with Gamma-derived settlement parity failing.

## Sources

- **Settlement source:** the source named by Polymarket/Gamma, normally a
  Weather Underground daily history URL with an ICAO/station code.
- **Bot observation source:** the dataset used by the bot for measurement or
  audit, such as Open-Meteo proxy or NOAA observed data.
- **Gamma-derived exact settlement:** read-only inference from resolved exact
  markets. It is useful triage when WU scraping/fetching is unavailable, but it
  does not replace a formal WU dataset.

## Tool

Generic CLI:

```powershell
python tools/source_parity_audit.py --city Beijing --icao ZBAA --lat 40.0799 --lon 116.6031 --tz Asia/Shanghai --days 60 --blocked-jsonl data/runtime_import_derived/blocked_signals_resolutions.jsonl --settlement-from-gamma --gamma-neighbor-radius 3 --out-md docs/source_audits/beijing_open_meteo_vs_wu_parity.md --no-write-json
```

Inputs:

- `--city`, `--icao`, `--lat`, `--lon`, `--tz`
- `--days`, or explicit `--start` / `--end`
- `--wu-csv` for manual WU daily highs when available
- `--blocked-jsonl` for resolved blocked signal evidence
- `--settlement-from-gamma` and `--gamma-neighbor-radius` for exact-market
  settlement inference
- `--out-md` for the versioned dossier

The tool is standalone and does not import `bot.py`.

## Verdicts

| Verdict | Meaning |
|---|---|
| `WU_FETCHER_MISSING` | No reliable WU fetcher or WU CSV was provided. |
| `PARITY_PASS_WU` | WU daily highs pass all parity criteria. |
| `SETTLEMENT_GAMMA_PARITY_PASS` | Gamma-derived exact settlement passes all parity criteria. |
| `SETTLEMENT_GAMMA_PARITY_FAIL` | Gamma-derived exact settlement shows a material mismatch. |
| `INSUFFICIENT_DATA` | Evidence is too thin or unreliable to pass or fail. |

## PASS Criteria

PASS requires all of:

- WU real data: `n >= 30`, or Gamma-derived unique exact dates: `n >= 20`
- median `|delta| <= 0.5C`
- percent of `|delta| >= 1C <= 10%`
- max `|delta| <= 2C`
- if blocked-signal outcomes are comparable against real WU data:
  at least `10/11` bot-derived outcomes match settlement outcomes

Small Gamma samples can still expose a clear blocker when the mismatch is
large and repeated, but they must not be used to approve parity.

## Promotion Gate

Exact markets in ICAO/WU cities require a source parity PASS before any Opus
promotion review can treat the measurement layer as cleared. A source-text
match alone is not enough: Gamma can confirm `WU/<ICAO>` while Open-Meteo still
disagrees with that station's settled high.

This framework is a prerequisite evidence layer only. It does not authorize
trading, city modes, whitelist changes, scheduler changes, env vars, or any
runtime writes.

