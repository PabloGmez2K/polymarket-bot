# DB Throughput Report

`tools/db_throughput_report.py` is a read-only LOG_ONLY CLI for quickly auditing the SQLite recorder funnel by UTC slot, city, and market condition.

It measures:

- DB state, schema presence, row counts, and cycle freshness.
- Cycles by UTC slot, markets evaluated, buys, and buy rates.
- Market snapshots by city.
- Condition distribution from a native column when present, otherwise from `payload_json`, otherwise inferred from `question`.
- Large cycle gaps and top throughput bottlenecks.

It does not authorize:

- BANKROLL changes.
- Fase C.
- Trading core changes.
- DB schema writes.
- Env var changes.
- Scheduler, city mode, whitelist, sizing, risk rule, or Telegram changes.
- Executable trading instructions.

Examples:

```bash
python tools/db_throughput_report.py --db data/polymarket.db --json
python tools/db_throughput_report.py --db data/polymarket.db --markdown
python tools/db_throughput_report.py --db data/polymarket.db --markdown --output data/observability/db_throughput_report.md
```

Railway read-only example:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "python tools/db_throughput_report.py --db /app/data/polymarket.db --markdown"
```

The tool opens SQLite using URI `mode=ro` and enables `PRAGMA query_only=ON`. If expected tables or columns are missing, it returns a degraded report with warnings instead of failing.
