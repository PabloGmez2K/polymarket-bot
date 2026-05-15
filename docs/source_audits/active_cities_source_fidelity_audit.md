# Active Cities Source Fidelity Audit

Generated: `2026-05-15T06:27:41+00:00`

Status: `NORMAL / LOG_ONLY`

> Human review package only. This audit does not authorize trading actions,
> policy edits, city-mode changes, automation, bankroll changes, promotion
> gates, observed-audit inclusion, or Phase C.

## Scope

This package applies `tools/source_fidelity_resolver.py` to the current active
city set:

- Shanghai
- Tokyo
- Buenos Aires
- Ankara

The resolver used local blocked-resolution evidence where available and queried
Polymarket Gamma read-only for five active/recent slugs per city. No runtime
data, mappings, city modes, env vars, trading rules, scheduler, whitelist,
promotion gates, or Telegram wiring were changed.

WRH/weather.gov and NOAA NCEI remain separate datasets and are not treated as
equivalent. These four active-city samples resolved to Weather Underground
source text, not WRH.

## Summary

| City | Internal mapping | External Polymarket source/rules summary | Verdict | Confidence | Evidence count | Human review required | Operational action |
|---|---|---|---|---|---:|---|---|
| Shanghai | `ZSPD`; WU template; NOAA NCEI proxy IDs `58321199999` / `CHM00058362` | Gamma source text cites Weather Underground daily history for `cn/shanghai/ZSPD`; five parsed markets all reported `wunderground`; no WRH site. | `SOURCE_MATCH_CONFIRMED` | High for WU source identity; observed proxy remains separate | 5 Gamma markets + 3 local rows | yes | `NO_ACTION / LOG_ONLY` |
| Tokyo | `RJTT`; WU template; NOAA NCEI proxy IDs `47671099999` / `JA000047670` | Gamma source text cites Weather Underground daily history for `jp/tokyo/RJTT`; five parsed markets all reported `wunderground`; no WRH site. | `SOURCE_MATCH_CONFIRMED` | High for WU source identity; observed proxy remains separate | 5 Gamma markets + 5 local rows | yes | `NO_ACTION / LOG_ONLY` |
| Buenos Aires | `SAEZ`; WU template; NOAA NCEI proxy IDs `87576099999` / `ARM00087576` | Gamma source text cites Weather Underground daily history for `ar/ezeiza/SAEZ`; five parsed markets all reported `wunderground`; no WRH site. | `SOURCE_MATCH_CONFIRMED` | High for WU source identity; observed proxy remains separate | 5 Gamma markets + 2 local rows | yes | `NO_ACTION / LOG_ONLY` |
| Ankara | `LTAC`; WU template; NOAA NCEI proxy IDs `17128099999` / `TUM00017130` | Gamma source text cites Weather Underground daily history for `tr/cubuk/LTAC` (URL-encoded in Gamma payload); five parsed markets all reported `wunderground`; no WRH site. | `SOURCE_MATCH_CONFIRMED` | High for WU source identity; observed proxy remains separate | 5 Gamma markets + 1 local row | yes | `NO_ACTION / LOG_ONLY` |

## Verdict

Baseline LOG_ONLY source-fidelity result:

- `Shanghai`: `SOURCE_MATCH_CONFIRMED`
- `Tokyo`: `SOURCE_MATCH_CONFIRMED`
- `Buenos Aires`: `SOURCE_MATCH_CONFIRMED`
- `Ankara`: `SOURCE_MATCH_CONFIRMED`

No `SOURCE_MISMATCH` was found.

No final `SOURCE_AMBIGUOUS` result remains after Gamma lookup. The first local
pass was ambiguous for all four cities because the local fallback ledger had no
slugs, market IDs, condition IDs, or source text for these active-city samples.
Gamma read-only lookup supplied the source/rules text.

## Per-City Reports

- `docs/source_audits/shanghai_source_fidelity_resolver.md`
- `docs/source_audits/tokyo_source_fidelity_resolver.md`
- `docs/source_audits/buenos_aires_source_fidelity_resolver.md`
- `docs/source_audits/ankara_source_fidelity_resolver.md`

JSON payloads were written under `data/source_audits/`, which is gitignored.

## Limitations

- Source parsing is heuristic and remains a human-review package.
- Gamma samples are recent active markets, not a complete historical proof.
- NOAA NCEI IDs in the internal mapping are treated as observed proxies and do
  not make NCEI equivalent to the Weather Underground settlement source.
- This audit does not update runtime rows, source mappings, city modes, active
  status, promotion gates, or trading behavior.

## Recommended Next Step

Close this as a baseline LOG_ONLY audit for the current active-city source
identity. If a future city returns `SOURCE_MISMATCH` or a serious
`SOURCE_AMBIGUOUS` result, stop and prepare an Opus RISK_CONTROL review before
any operational change.
