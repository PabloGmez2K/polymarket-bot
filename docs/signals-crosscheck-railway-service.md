# Signals Crosscheck Railway Service

Servicio ligero para automatizar el loop diario de `traders vs bot` sin tocar
`bot.py`, scheduler ni trading core.

## Que hace

- lee la serie temporal de `signals_crosscheck.jsonl`;
- si hoy todavia no existe corrida, ingiere una desde `signals.json` +
  `shadow_city_tracking.json`;
- arma un resumen temporal corto para Telegram;
- guarda estado anti-spam en `data/signals_crosscheck_daily_summary_state.json`;
- escribe el ultimo readout en `docs/signals_crosscheck_daily_summary_latest.md`.

## Comando Railway recomendado

```text
python -u tools/signals_crosscheck_railway_service.py
```

## Variables recomendadas

- `RAILPACK_START_CMD=python -u tools/signals_crosscheck_railway_service.py`
- `SIGNALS_CROSSCHECK_DAILY_HOUR_UTC=9`
- `SIGNALS_CROSSCHECK_SUMMARY_WINDOW_RUNS=7`
- `SIGNALS_CROSSCHECK_SUMMARY_MIN_RUNS=5`
- `TELEGRAM_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

## Notas

- el script prefiere `data/signals_crosscheck.jsonl` cuando existe (caso live del
  bot) y hace fallback a `data/runtime_import_derived/signals_crosscheck.jsonl`
  para trabajo local;
- la ingestión diaria es idempotente por fecha UTC;
- el resumen no cambia whitelist ni policy: solo deja feedback loop diario y una
  instruccion corta para Codex.
