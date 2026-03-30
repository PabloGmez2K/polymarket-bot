# Research Synthesis: Codex + Claude

Date: 2026-03-30
Purpose: consolidate the overlap, corrections, and final roadmap after cross-reviewing Codex research with Claude research.

## Final High-Confidence Conclusions

1. `Resolution fidelity first` remains the correct strategic priority.
2. Dallas is an active, high-impact bug:
   - bot maps Dallas to `KDFW`
   - Polymarket Dallas markets checked resolve with `KDAL`
3. The current audit layer does **not** validate against Polymarket's real settlement source.
4. The current audit implementation is weaker than Codex originally framed:
   - it calls `get_forecast()` from the Open-Meteo forecast endpoint
   - it does not use Weather Underground
   - it does not use a formal observed-source pipeline
5. Chicago looks **more likely solved than uncertain**:
   - multiple Polymarket Chicago pages checked use `KORD`
   - current bot mapping also uses O'Hare / `KORD`
6. Wethr should be treated as:
   - useful for timing / microstructure intuition
   - not the final source of truth for Polymarket settlement rules
7. Degen Doppler is a real, relevant competitor/reference that Codex missed.

## Corrections to Codex

### Correction A: audit weakness is worse than initially described

Codex was directionally right that the audit depends on Open-Meteo rather than Polymarket's resolution source.

After Claude's review and local code verification, the stronger statement is:

- the audit path calls `get_forecast()`
- `get_forecast()` hits Open-Meteo's forecast endpoint
- the code does not implement a true WU-based observed reconciliation path

This means the audit cannot be trusted as a settlement-accuracy validator.

### Correction B: Degen Doppler should be included in the competitive map

It is a directly relevant public reference:
- Polymarket weather edge finder
- multi-model ensemble
- observed-high awareness
- confidence tiers

It is a much more relevant comparator than several generic weather/climate leaderboard references.

### Correction C: WeatherClaw was not a clean correction from Claude

Claude reported that WeatherClaw does not exist, but that check appears to have used `weatherclaw.com`.

Codex had referenced `weatherclaw.xyz`, which is active and publicly presents a weather trading product.

Therefore the right synthesis is:
- Claude was right to challenge this aggressively
- but the claim "WeatherClaw does not exist" is not supported after checking `weatherclaw.xyz`
- the real caution is still that public marketing copy may not reflect actual settlement fidelity

## Points Where Claude Strengthened the Picture

### Dallas

Claude materially strengthened the Dallas finding by:
- confirming `KDAL`
- emphasizing the likely practical impact of airport mismatch
- reframing it as an urgent production bug, not just a research curiosity

### Audit / observability

Claude strengthened the case that:
- current "forecast_vs_real" is not a robust truth layer
- historical accuracy metrics may be partially misleading

### METAR / aviationweather nuance

Claude added an important operational nuance:
- aviationweather.gov can be a useful validation feed
- but it should not be treated as identical to Polymarket's final resolution source
- for Polymarket, Weather Underground still matters more

## Points Where Codex Stands Up Well

1. Core thesis:
   - source/station correctness before model complexity
2. Dallas station mismatch:
   - found correctly
3. WU vs Open-Meteo:
   - found correctly
4. Commodity vs real edge:
   - found correctly
5. Wethr positioning:
   - useful for timing, not trusted as settlement truth

## Points Still Open / Not Fully Settled

1. Buenos Aires:
   - current evidence points to `SAEZ`
   - continue monitoring for possible variant rules, but not top priority

2. Timing-aware execution ordering:
   - Codex favored timing after source/station fixes
   - Claude prefers trying low-effort ensemble upgrades earlier
   - this is a genuine sequencing disagreement, not a factual contradiction

3. Favourite-longshot bias / bond strategy:
   - interesting leads from Claude
   - not yet critical enough to reorder the roadmap without more direct verification

## Final Roadmap Ordering

### Priority 1 — Do immediately

- Fix Dallas mapping from `KDFW` to `KDAL`
- Audit the city-to-station mapping for the active cities
- Make the current audit path explicit about what it is and is not validating

### Priority 2 — Build the truth layer

- Introduce a formal resolution layer:
  `city/market -> ICAO -> WU URL -> timezone -> unit -> finalization semantics`
- Add a WU-oriented or resolution-oriented validation path for post-market checks

### Priority 3 — Improve forecasting only after alignment

- Evaluate a low-effort ensemble upgrade, especially if Open-Meteo can expose richer model options
- But do it only after station/source correctness is fixed for active cities

### Priority 4 — Timing and execution

- Add release-aware execution or no-trade windows
- Use Wethr and official weather-data docs as timing references, not settlement truth

### Priority 5 — Secondary strategy research

- favourite-longshot bias
- bond-style high-probability plays
- more advanced maker/taker execution behavior

## Single Strategic Direction

If forced to choose one direction only:

`align the bot with Polymarket's actual resolution reality before adding more model complexity`

Everything else should follow from that.
