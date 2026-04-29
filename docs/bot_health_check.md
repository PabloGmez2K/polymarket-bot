# Bot Health Check

`tools/bot_health_check.py` es una CLI read-only para responder rapido si el bot
parece sano o si requiere atencion antes de revisar Railway por SSH.

## Comandos

```bash
python tools/bot_health_check.py --data-dir data --db data/polymarket.db --markdown
python tools/bot_health_check.py --data-dir /app/data --db /app/data/polymarket.db --markdown
python tools/bot_health_check.py --data-dir /app/data --db /app/data/polymarket.db --json
```

Defaults:

- `--data-dir data`
- `--db data/polymarket.db`
- `--max-cycle-age-hours 6`
- `--log-tail 200`

## Significado

- `OK`: ultimo ciclo reciente, recorder fresco, sin gaps grandes ni errores criticos.
- `WATCH`: avisos no criticos, datos insuficientes para Fase 1, errores transitorios o archivos opcionales ausentes.
- `ACTION`: ciclo stale, DB stale mayor a 30h, errores criticos de logs, rejects de ejecucion relevantes o DB ilegible.

## Cuando usarlo

Usalo antes de abrir una revision manual por SSH, despues de un deploy, o cuando
un resumen Telegram parezca ambiguo. En Railway puede correr contra `/app/data`.

## Que lee

- `cycle_summary.json`
- `cycles_history.jsonl`
- `decisions.log`
- `trades.log`
- `trade_lifecycle.json` si existe
- `postmortem.json` si existe
- `polymarket.db` si existe
- `signals.json` si existe

## Que no hace

- No envia Telegram.
- No hace llamadas externas.
- No importa `bot.py`.
- No modifica variables de entorno.
- No compra, vende ni cambia reglas de trading.
- No implementa Truth Pipeline.
- No cambia runtime del bot.

La conexion SQLite se abre en modo URI `mode=ro`; si la DB no existe o no se
puede leer, el informe lo marca como `WATCH` o `ACTION` sin crear archivos.
