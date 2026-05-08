# Traders Intelligence v1 snapshots

Activation contract: see
`docs/traders-intelligence-v1-activation-package.md`.

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
