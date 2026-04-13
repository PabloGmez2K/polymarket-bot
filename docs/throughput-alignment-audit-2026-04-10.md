# Throughput Alignment Audit - 2026-04-10

## Scope

Auditoria operativa y de cableado para entender por que el bot gano las ultimas compras limpias pero casi no abre nuevas posiciones, y para preparar una decision LEAN de aumento controlado de throughput.

No se cambia trading core, `bot.py`, thresholds, allowlists, Railway volumes, `city_policy_state.json` ni phase5.

## Evidence Window

- Servicio auditado: `polymarket-bot` en Railway, read-only.
- Ultimo ciclo disponible durante la auditoria: `2026-04-10T08:00:42Z`.
- Hora local al auditar: `2026-04-10T17:32:27+02:00`, es decir antes del ciclo `16:00 UTC`.
- Artefactos runtime leidos desde `/app/data`: `cycle_summary.json`, `cycles_history.jsonl`, `performance.json`, `postmortem.json`, `trade_lifecycle.json`, `decisions.log`, `skip_log.jsonl`, `audit.json`, `shadow_city_tracking.json`, `city_policy_state.json`.
- Variables Railway relevantes de `polymarket-bot`: `DRY_RUN=false`, `BANKROLL=25.00`, `MIN_DAYS_AHEAD=-1`, `MIN_BET=1.00`, `ACTIVE_TRADING_CITIES=Dallas`, `BLOCKED_CITIES=London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`, `ALLOWLIST_REMOVE_MIN_TRADES=25`, `CITY_STATS_CUTOFF=Dallas=2026-04-06`.

## Executive Finding

El sistema no esta roto: sigue encontrando aproximadamente `330` mercados brutos por ciclo y las ultimas 3 compras limpias fueron ganadoras. Pero el sistema esta casi en modo observacion: no hay ninguna ciudad `active` efectiva porque Dallas esta manualmente en `ACTIVE_TRADING_CITIES` pero runtime la tiene en `auto_shadow_cities`, que tiene prioridad. Las compras nuevas dependen de 6 canaries con sizing reducido.

La falta de throughput viene de un embudo demasiado estrecho, no de un fallo de scan:

- muchisimos mercados quedan fuera por fecha/zona horaria;
- muchos quedan fuera por precio;
- `exact` y `range` se filtran por `ALLOWED_CONDITIONS=at_or_above,at_or_below`;
- `MIN_EDGE=15%` elimina casi todos los direccionales restantes;
- las ciudades con senal reciente no necesariamente estan operables.

## Recent Trading Result

Postmortem limpio desde `2026-04-07`:

| City | Market | Opened | Closed | Side | Amount | PnL |
| --- | --- | --- | --- | --- | ---: | ---: |
| Atlanta | 76F or higher Apr 7 | 2026-04-07 08:47 UTC | 2026-04-07 23:00 UTC | YES | 1.15 | +0.63 |
| Shanghai | 30C or higher Apr 9 | 2026-04-08 08:00 UTC | 2026-04-09 16:00 UTC | NO | 1.18 | +0.40 |
| Seoul | 15C or higher Apr 9 | 2026-04-08 08:00 UTC | 2026-04-09 08:00 UTC | NO | 1.18 | +0.28 |

Resumen: `3/3`, `+$1.31` postmortem PnL limpio desde Apr 7. Es buena senal direccional reciente, pero muestra pequena.

## Cycle Throughput Since Apr 8

| Cycle UTC | Candidates evaluated | With edge | Selected | Condition filtered | Buys |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-04-08 08:00 | 17 | 2 | 2 | 15 | 2 |
| 2026-04-08 14:14 | 17 | 0 | 0 | 16 | 0 |
| 2026-04-08 14:16 | 17 | 0 | 0 | 16 | 0 |
| 2026-04-08 16:00 | 18 | 0 | 0 | 16 | 0 |
| 2026-04-08 23:00 | 14 | 0 | 0 | 12 | 0 |
| 2026-04-09 08:00 | 12 | 0 | 0 | 12 | 0 |
| 2026-04-09 16:00 | 13 | 0 | 0 | 13 | 0 |
| 2026-04-09 23:01 | 19 | 0 | 0 | 17 | 0 |
| 2026-04-10 08:00 | 26 | 0 | 0 | 25 | 0 |

Important interpretation: `markets_evaluated` is the legacy alias for `candidates_after_prefilters`, not raw Polymarket universe. `decisions.log` still reports `MERCADOS: 330 encontrados` in the cycles inspected. The low `12-26` number is post-filter candidate throughput.

## Skip Funnel Since Apr 8

Skip counts from `skip_log.jsonl` since `2026-04-08`:

| Skip reason | Count |
| --- | ---: |
| `date_out_of_range_past` | 1461 |
| `price_out_of_range` | 873 |
| `timezone_filter` | 330 |
| `blocked_city` | 143 |
| `condition_filtered` | 142 |
| `parse_fail` | 10 |
| `below_min_edge` | 8 |
| `fuera_allowlist` | 1 |

By mode:

| Mode | Main skips |
| --- | --- |
| `canary` | price/date/timezone/condition, plus 4 below-min-edge |
| `shadow` | date/price/timezone/condition, plus 1 strong fuera_allowlist |
| `blocked` | blocked_city |

This means the biggest throughput limit is before selection, not order execution.

## Effective Policy Alignment

Runtime policy priority in `bot.py`: blocked/auto_blocked, auto_shadow, manual active, auto_canary/manual canary, default shadow.

Effective matrix from live variables + runtime state:

| City | Manual active | Manual blocked | Auto canary | Auto shadow | Effective mode |
| --- | --- | --- | --- | --- | --- |
| Dallas | yes | no | no | yes | `shadow(auto)` |
| Atlanta | no | no | yes | no | `canary(auto)` |
| Munich | no | no | yes | no | `canary(auto)` |
| New York City | no | no | yes | no | `canary(auto)` |
| Seoul | no | no | yes | no | `canary(auto)` |
| Shanghai | no | no | yes | no | `canary(auto)` |
| Tokyo | no | no | yes | no | `canary(auto)` |
| Chicago | no | no | no | no | `shadow(default)` |
| Buenos Aires | no | no | no | no | `shadow(default)` |

Critical finding: `ACTIVE_TRADING_CITIES=Dallas` does not currently create active throughput because `auto_shadow_cities.Dallas` wins. Operationally, there is no active city.

## City-Intelligence Alignment

`city-intelligence` is now safer than before, but still not automated:

- Local default pipeline emits `runtime_inputs_missing` when not passed runtime paths.
- Manual runtime import through `data/runtime_import/*` can produce a reconciled ledger/gate.
- The live `city-intelligence` service still has a separate Railway volume and does not yet consume `polymarket-bot` runtime automatically.
- Live `city-intelligence` targets are `Chicago,Dallas,Seattle,Munich,Madrid`, which are not the same as runtime canaries `Atlanta,Munich,New York City,Seoul,Shanghai,Tokyo`.

This is acceptable as analysis infrastructure, but not yet a reliable autonomous decision layer. It must remain read-only and advisory.

## Runtime Import Manifest Alignment

The official runtime import manifest currently represents only the 3-file snapshot:

- `shadow_city_tracking.json`
- `audit.json`
- `city_policy_state.json`

For this audit, additional files were pulled manually into `data/runtime_import` for diagnosis. That means the manifest is not a complete provenance record for all local `runtime_import` files after the audit.

Required before automation: runtime transport must be atomic and manifest-driven. Every imported file should be listed with source path, pull timestamp, byte count, and preferably checksum. Downstream tools should not silently mix files from different pulls.

## Phase5 Alignment

`phase5-visibility` remains a separate experimental visibility service:

- targets: `Shanghai,Chicago`
- interval: `180` minutes
- own Railway volume

It is not a policy source and should not be used to make runtime trading changes. Its useful role is comparative/visibility evidence until folded into `city-intelligence` or archived.

## High-Signal Opportunities Observed

One notable shadow opportunity was recorded:

- `Chicago`, Apr 10, `NO` on `56F or higher`, `edge_pct=35.09`, virtual amount `$2.43`, virtual EV `+$1.99`.
- It was skipped as `fuera_allowlist` because Chicago is `shadow(default)`.

This is not enough to activate Chicago blindly, but it is the cleanest candidate for a LEAN canary discussion because it is a directional market, has observed infrastructure, and produced a strong virtual edge.

## Monetization Interpretation

Positive:

- Last 3 clean trades won.
- Recent canary sizing avoided overexposure.
- Auto-shadow prevented Dallas from continuing as active after poor results.
- Fail-closed city-intelligence prevents false confidence from missing runtime.

Negative:

- No active city means very low expected trade count.
- `ALLOWED_CONDITIONS` excludes most available markets.
- `MIN_EDGE=15` plus `MIN_BET=1` leaves few trades at 25 bankroll.
- Runtime/cross/pipeline/service targets are not yet fully aligned.
- Operational telemetry still needs clearer raw-vs-filtered funnel wording.

## Minimal Change Candidates For Opus Review

These are candidates for review, not recommendations to execute immediately:

1. Add a single new canary, probably Chicago, without making it active.
2. Keep `ALLOWED_CONDITIONS` restricted to directional markets.
3. Keep `MIN_EDGE=15` until a larger canary sample exists.
4. Fix observability copy/metrics so raw markets, candidates, condition-filtered markets, shadow opportunities and selected buys are distinct.
5. Automate runtime snapshot transport before letting `city-intelligence` produce normal-looking gates in production.
6. Align city-intelligence targets with runtime canary/watchlist intent, or explicitly label them as independent analysis targets.

## Recommended Next LEAN Step

Before changing trading behavior:

1. Automate read-only runtime snapshot import with a complete manifest and staleness guard.
2. Regenerate city-intelligence ledger/gate from that snapshot.
3. Produce one reconciled daily "throughput funnel" report:
   - raw markets found,
   - candidate markets after date/price/liquidity,
   - directional allowed markets,
   - below-min-edge,
   - shadow opportunities,
   - canary/active selected,
   - buys executed,
   - resulting postmortem.
4. Then ask Opus whether one controlled canary addition is justified.

## Do Not Implement Yet

- Do not raise bankroll above `25`.
- Do not lower `MIN_EDGE`.
- Do not enable `exact` or `range`.
- Do not force Dallas back to active.
- Do not promote Chicago directly to active.
- Do not let city-intelligence write runtime policy.
- Do not write `city_policy_state.json` from analysis services.
- Do not turn phase5 into a second decision source.
- Do not add broad drift detectors before runtime transport is reliable.
