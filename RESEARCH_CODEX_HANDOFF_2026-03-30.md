# Research Handoff for Claude Review

Date: 2026-03-30
Author: Codex
Purpose: give Claude a concrete, auditable summary of Codex's investigation so Claude can review it critically after finishing its own research.

## Recommended Review Mode

Please do not just summarize this document. Review it adversarially.

For each major claim below:
- confirm it with stronger evidence if you agree
- challenge it if you disagree
- mark whether it is verified, inferred, or still uncertain
- say whether it changes the roadmap priority for the bot

## Executive Summary

Codex's current thesis is:

The next strategic step for this bot should be `resolution fidelity first`, not `forecast sophistication first`.

Reason:
- the bot currently relies mainly on Open-Meteo for both forecast and historical observed comparisons
- Polymarket weather markets that were checked resolve using Weather Underground
- at least one active city, Dallas, appears to be mapped to the wrong airport station in the bot
- this means the system may currently be optimizing against the wrong source, and in one case possibly the wrong station as well

The highest-conviction recommendation from Codex is:

Build a formal resolution layer:

`market -> station -> source_url -> timezone -> unit -> finalization rule`

before adding more model complexity.

## Scope of Codex Research

Codex focused on four areas:

1. Current bot baseline from the local repo
2. Real Polymarket market rules for temperature market resolution
3. Public competitors, tools, and trader profiles in the same ecosystem
4. Timing and microstructure signals around weather data releases

This is intended as a strategic research memo, not a code change proposal.

## Repo Baseline Confirmed

From the local repo:

- Forecast source is Open-Meteo in `bot.py`
- Historical observed audit also uses Open-Meteo in `bot.py`
- Station mappings are hardcoded in `RESOLUTION_STATIONS`
- Current active cities are Chicago, Atlanta, Buenos Aires, Dallas
- London and other cities are blocked due to poor live results / source mismatch concerns
- Trading logic is currently:
  - `MIN_EDGE = 7%`
  - `Half-Kelly`
  - `STOP_LOSS = -25%`
  - `TAKE_PROFIT = +40%`
  - re-evaluate and sell if edge `< -3%`
- Current schedule is `08:00, 16:00, 23:00 UTC`

Relevant local references:
- `bot.py:2853` for `RESOLUTION_STATIONS`
- `bot.py:4037` for Open-Meteo forecast
- `bot.py:4954` for Open-Meteo observed/historical logic
- `CONTEXTO.md:34` for schedule
- `CONTEXTO.md:58` for currently active vs blocked cities

## Verified Findings from Polymarket Rules

### High confidence

Codex verified multiple Polymarket event pages where the market rules explicitly say the resolution source is Weather Underground.

Examples checked:

- Dallas:
  - Polymarket uses Dallas Love Field Station
  - Weather Underground URL ends with `KDAL`
  - example checked:
    - `https://polymarket.com/event/highest-temperature-in-dallas-on-february-23-2026/highest-temperature-in-dallas-on-february-23-2026-70-71f`

- Atlanta:
  - Polymarket uses Hartsfield-Jackson
  - Weather Underground URL ends with `KATL`
  - example checked:
    - `https://polymarket.com/event/highest-temperature-in-atlanta-on-december-27/highest-temperature-in-atlanta-on-december-27-62-63f`

- Buenos Aires:
  - Polymarket uses Minister Pistarini / Ezeiza
  - Weather Underground URL ends with `SAEZ`
  - example checked:
    - `https://polymarket.com/es/event/highest-temperature-in-buenos-aires-on-february-13-2026/highest-temperature-in-buenos-aires-on-february-13-2026-29c`

- London:
  - Polymarket uses London City
  - Weather Underground URL ends with `EGLC`
  - example checked:
    - `https://polymarket.com/event/highest-temperature-in-london-on-may-27`

- Madrid:
  - Polymarket uses Barajas
  - Weather Underground URL ends with `LEMD`
  - example checked:
    - `https://polymarket.com/pt/event/highest-temperature-in-madrid-on-march-18-2026/highest-temperature-in-madrid-on-march-18-2026-19c`

- Toronto:
  - Polymarket uses Pearson
  - Weather Underground URL ends with `CYYZ`
  - example checked:
    - `https://polymarket.com/event/highest-temperature-in-toronto-on-february-9-2026/highest-temperature-in-toronto-on-february-9-2026-neg-9c`

- Paris:
  - Polymarket uses Charles de Gaulle
  - Weather Underground URL ends with `LFPG`
  - example checked:
    - `https://polymarket.com/pt/event/highest-temperature-in-paris-on-march-22-2026/highest-temperature-in-paris-on-march-22-2026-16c`

- Miami:
  - Polymarket uses Miami Intl
  - Weather Underground URL ends with `KMIA`
  - example checked:
    - `https://polymarket.com/event/highest-temperature-in-miami-on-february-21-2026/highest-temperature-in-miami-on-february-21-2026-74-75f`

### Highest-impact mismatch found

Dallas appears to be wrong in the current bot:

- bot mapping: Dallas Fort Worth / `KDFW`
- Polymarket rule checked: Dallas Love Field / `KDAL`

Codex view:
- Chicago, Atlanta, Buenos Aires look like `source mismatch`
- Dallas looks like `source mismatch + station mismatch`

## Competitor / Ecosystem Map

### Public trader profiles / leaderboard signals

Polymarket weather leaderboard checked:
- `gopfan2`
- `aenews2`
- `gopfan`
- `ColdMath`
- `automatedAItradingbot`
- `WeatherTraderBot`

Important nuance:
- leaderboard "weather" includes both `daily temperature` and broader `weather/climate` markets
- many largest public wins come from macro climate markets, not necessarily the exact same sub-game as this bot

Example:
- `gopfan2` and `aenews2` public biggest wins include climate-style markets like monthly or yearly heat records

Codex conclusion:
- top weather leaderboard traders are useful references
- but not all of them are direct analogs for daily airport temperature bucket trading

### Directly relevant public products / tools

#### WeatherClaw

What looked real:
- specific claims about `122 ensemble forecast models`
- `quarter-Kelly`
- `circuit breaker`
- `30-minute scans`
- CLOB execution
- dashboard / paper-to-live workflow

What concerned Codex:
- site copy says settlement is fetched from Iowa State Mesonet
- Dallas is presented as `DFW / KDFW`
- this may not align with Polymarket Dallas settlement, which Codex verified as `KDAL / Wunderground`

Codex conclusion:
- WeatherClaw looks technically serious
- but it may still be solving a slightly different settlement problem than Polymarket's actual rules

#### OpenClaw / polymarket-weather-trader

What it appears to be:
- a public template for a weather bot
- NOAA via Simmer API
- execution plumbing plus safeguards
- explicitly positioned as "gopfan2-style"

Codex conclusion:
- useful reference for what is now becoming commodity infrastructure
- not evidence of unique edge by itself

#### PolyWeatherBot / PolyTraderBot

Claims observed:
- `10-model ensemble`
- `82 probabilistic members`
- `YES ladder`
- `NO-outlier`
- `conflict filter`
- Docker deployment

Codex conclusion:
- plausible as a working product
- but much less verifiable than public wallets or products that expose clearer methodology

#### Wethr

What Codex found useful:
- education on `DSM`, `OMO`, `6 Hour Bot`, `240`, `1-Up`
- timing / order-book awareness
- city release schedules

What Codex did not trust as truth source:
- Wethr city/resources pages still frame `CLI` as the official resolution source for temperature markets
- checked Polymarket pages instead pointed to `Wunderground`

Codex conclusion:
- use Wethr for timing intuition and microstructure ideas
- do not use it as the final source of truth for settlement rules

## Timing / Microstructure Findings

Codex found enough primary evidence to believe timing matters materially.

Official weather-data evidence:
- ASOS updates continuously and observations are very frequent
- internal high/low tracking is more precise than simplified public 5-minute outputs
- one-minute and phone/audio interfaces exist in the ASOS ecosystem
- daily summaries and transmitted reports occur on schedules that can cause repricing moments

Official sources reviewed:
- `https://www.weather.gov/asos`
- `https://www.weather.gov/about/observation-equipment`
- `https://www.weather.gov/psr/HiResASOS`
- `https://www.weather.gov/lox/asostemperature`
- `https://www.weather.gov/asos/InformationReporting.html`
- `https://www.weather.gov/asos/METAR.html`

Community microstructure source reviewed:
- `https://wethr.net/edu/market-bots`

Codex interpretation:
- bots reacting to `DSM`, `6-hour`, `OMO`, or minute-level observation channels are plausible
- even if community labels are imperfect, the underlying timing edge appears real
- leaving exposed orders near certain data release windows is probably dangerous

## Commodity vs Real Edge

Codex view of what is already becoming commodity:
- basic forecast-vs-market scanning
- Kelly sizing
- dashboards
- paper/live execution plumbing
- "gopfan2-style" templates
- generic NOAA / ensemble marketing

Codex view of what may still be real edge:
- exact mapping of market to airport station
- exact mapping of market to final resolution source
- knowing when a city's intuitive station is wrong
- timing-aware execution around data release windows
- city specialization instead of broad shallow scanning

## Main Strategic Thesis

Codex thesis:

Do not prioritize "more models" until settlement is aligned.

Why:
- if the forecast is evaluated against the wrong source or wrong station, better modeling does not solve the core problem
- it may simply make the bot more confidently wrong

## Roadmap Proposed by Codex

### Priority 1

Build a resolution layer:

`market -> station -> source_url -> timezone -> unit -> finalization semantics`

### Priority 2

Fix known station mismatch:
- Dallas should be audited first

### Priority 3

Add shadow monitoring:
- compare bot source vs real resolution source for active cities
- store divergence data over time

### Priority 4

Add timing-aware execution:
- no-trade or reduced-risk windows around major release times
- especially near DSM / 6-hour / finalization-sensitive periods

### Priority 5

Only then evaluate:
- NOAA / NWS point forecasts
- multi-model ensemble upgrades
- more frequent scans
- more advanced execution

## Concrete Experiments Suggested by Codex

1. Dallas audit:
- compare `KDFW` vs `KDAL` for a meaningful sample

2. Source divergence monitor:
- compare Open-Meteo vs actual Polymarket settlement source for Chicago, Atlanta, Buenos Aires, Dallas

3. Historical relabeling:
- classify losses/wins as:
  - source mismatch
  - station mismatch
  - timing-sensitive
  - forecast miss despite proper source

4. Release-window simulation:
- estimate whether vulnerable orders around DSM / 6-hour windows would have harmed fills or exits

5. Paper mode after settlement fix:
- test a resolution-aware system before expanding model complexity

## What is Verified vs Inferred vs Uncertain

### Verified

- Current bot uses Open-Meteo in core forecast and historical observed logic
- Current bot station list includes Dallas as Fort Worth
- Checked Polymarket market rules point to Weather Underground in several temperature markets
- Checked Dallas market rule points to `KDAL`, not `KDFW`
- Public tools and profiles listed in this memo exist and make the cited claims

### Inferred

- Resolution fidelity is a higher-value next step than forecast sophistication
- Some competitors may be operating with good forecast stacks but imperfect settlement alignment
- Timing-aware bots likely have a meaningful edge against slower systems

### Uncertain / Needs Claude Pressure Test

- Whether Wunderground is consistently the settlement source across all current and future temperature markets
- Whether Dallas station usage is universal across all Dallas market variants or changed over time
- Whether WeatherClaw internally handles settlement better than its public marketing copy suggests
- How much of top leaderboard weather PnL comes specifically from daily temperature bucket trading
- The actual magnitude of economic advantage from microstructure timing versus plain settlement correctness

## Questions for Claude to Answer Explicitly

1. Do you agree that `resolution fidelity first` should outrank `ensemble/model expansion`?
2. Can you confirm or refute the Dallas `KDAL vs KDFW` finding with stronger evidence?
3. Do you see any other city with a station mismatch risk comparable to Dallas?
4. Do you agree Wethr should be treated as microstructure/timing aid rather than settlement truth?
5. Which competitor or public stack seems most dangerous specifically for daily temperature markets?
6. Are there stronger primary sources than the ones Codex found for final market-resolution behavior?
7. If you disagree with Codex's roadmap ordering, what would you change first and why?

## Final Codex Position

If Codex had to choose one single strategic direction for the next sessions, it would be:

`make the bot play the exact same settlement game that Polymarket is actually liquidating`

before investing heavily in more prediction sophistication.
