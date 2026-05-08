# Traders Intelligence v1 snapshots

Activation contract: see
`docs/traders-intelligence-v1-activation-package.md`.

Evolution roadmap (V1 → V1.1 collector → V1.2 scoreboard → recomendaciones):
see [`docs/traders-intelligence-roadmap.md`](traders-intelligence-roadmap.md).
V1.1 collector is implemented as LOG_ONLY and default OFF.

`tools/traders_intelligence_snapshot.py` is the minimal v1 archivist for
external trader observation. It does not trade, does not edit `signals.json`,
does not change policy, and does not emit executable signals.

Scope is intentionally fixed:

- Traders: `Thrifty-Original`, `Entire-Hood`
- Cities: `Houston`, `Los Angeles`, `Manila`, `Miami`

Usage:

```powershell
python tools/traders_intelligence_snapshot.py
python tools/traders_intelligence_snapshot.py --dry-run
python tools/traders_intelligence_snapshot.py --run-id 2026-05-01T120000Z
```

Default outputs are runtime/regenerable artifacts under
`data/traders_intelligence/`:

- `snapshots/<run_id>.json`: filtered copy of the current `signals.json`.
- `reports/<run_id>.json`: pseudo-lifecycle report for that run.
- `pseudo_lifecycle_runs.jsonl`: idempotent audit index, one row per `run_id`.

The pseudo-lifecycle is observational only:

- `appeared`: present now and never seen in prior filtered snapshots.
- `still_present`: present now and present in the previous filtered snapshot.
- `disappeared_apparent`: present in the previous filtered snapshot, absent now.
- `reappeared`: present now, absent in the previous filtered snapshot, seen earlier.

`disappeared_apparent` is not a confirmed exit. `signals.json` has no trader
execution event, size, or confirmed close timestamp.

## V1.1 collector LOG_ONLY

`tools/traders_intelligence_collector.py` wraps the V1 snapshot tool without
reimplementing snapshot logic. It adds:

- persistent state in `data/traders_intelligence/collector_state.json`;
- `TRADERS_INTELLIGENCE_COLLECTOR=OFF` default kill switch;
- auto-disable when `consecutive_failures >= 5`;
- 30 minute cooldown by default;
- skip when `signals.json.generated` did not change;
- dry-run mode that does not write snapshots, reports, state, or events;
- trace event rows in `agent_events.jsonl` for completed real runs/failures.

Manual usage:

```powershell
python tools/traders_intelligence_collector.py --json
python tools/traders_intelligence_collector.py --dry-run --json
$env:TRADERS_INTELLIGENCE_COLLECTOR="ON"; python tools/traders_intelligence_collector.py --json
```

The optional `bot.py` hook is present behind the same env var and remains inert
while `TRADERS_INTELLIGENCE_COLLECTOR` is unset or `OFF`. V1.1 still does not
trade, send Telegram, change policy, alter city modes, touch BANKROLL/Fase C, or
emit BUY/SELL/SKIP.
