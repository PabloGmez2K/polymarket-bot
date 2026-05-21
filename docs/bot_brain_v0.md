# Bot Brain v0

**Status:** IMPLEMENTED / LOG_ONLY / read-only.

Bot Brain v0 is a small local query tool for connecting existing bot artifacts. It answers "what does the system already know about X?" without manually reopening every JSONL, doc, and session trace.

It is not a source of truth. It does not create trading signals. It does not authorize BANKROLL, BUY/SELL/SKIP, city modes, scheduler changes, env vars, DB writes, Railway work, Telegram alerts, guards, stop-loss, Fase C, or Truth Pipeline changes.

## Tool

```powershell
python tools/bot_brain.py --scope overview --window 7d
python tools/bot_brain.py --scope city:Shanghai --window 14d
python tools/bot_brain.py --scope cycle:367
python tools/bot_brain.py --scope eval_key:<key>
python tools/bot_brain.py --scope match_key:<key> --format md
```

JSON is the default output. Use `--format md` for a short Markdown readout.

## Inputs

Bot Brain v0 reads existing local artifacts if present:

- `data/cycles_history.jsonl`
- `data/funnel_observability_log_only.jsonl`
- `data/funnel_observability_latest.json`
- `data/bot_signal_evaluations.jsonl`
- `data/blocked_signals_resolutions.jsonl`
- `data/trade_lifecycle.json`
- `agent_events.jsonl`
- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`

`CONTEXTO.md` and `HISTORIAL_SESIONES.md` are searched lightly as text. They are not parsed as canonical structured state.

## Connections

The v0 linkage is intentionally small:

- `bot_signal_evaluations.eval_key == blocked_signals_resolutions.match_key`
- cycles linked with Funnel records by `cycle_number` / `logic_cycle_number`
- city mentions across cycles, Funnel records, evaluations, blocked resolutions, and light text search
- artifact inventory with present/missing status
- orphan detection for evals without resolutions, resolutions without evals, and cycles without Funnel records

If data is missing, undersampled, or unmatched, the tool returns `missing_artifacts`, `undersampled`, or `no_match`. It must not infer or invent missing knowledge.

## Guardrails

- LOG_ONLY / `NO_ACTION`.
- Read-only local files only.
- No backfill.
- No daemon.
- No Telegram.
- No scheduler.
- No DB writes.
- No runtime/env var/Railway work.
- No trading semantics.
- No BANKROLL, BUY/SELL/SKIP, sizing, whitelist, city mode, guard, stop-loss, Fase C, or Truth Pipeline change.
