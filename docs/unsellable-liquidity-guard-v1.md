# Unsellable Liquidity Guard v1

Fecha: 2026-04-30
Estado: Fase 1 LOG_ONLY

## Objetivo

Registrar candidatos con riesgo de terminar como `micro_position_unsellable` antes de la compra, sin bloquear ejecuciones en la primera fase.

## Defaults

- `UNSELLABLE_GUARD_ENABLED=0`
- `UNSELLABLE_GUARD_LOG_ONLY=1`
- `UNSELLABLE_GUARD_VERSION=unsellable_v1`

Con los defaults actuales el guard queda apagado. Si se activa con `LOG_ONLY=1`, escribe `skip_log` con `guard_action="would_skip"` y `skip_reason="unsellable_guard_candidate"`, pero no hace `continue` ni bloquea la compra.

## Trigger

El candidato se marca solo si se cumplen todas estas condiciones:

- `condition in {"exact", "range"}`
- `days_ahead == 0`
- `0.10 <= price_at_guard <= 0.65`
- `size_ratio >= 0.15`

`size_ratio = amount / effective_bankroll`. Es ratio, no porcentaje: `0.15` equivale al 15% del bankroll efectivo.

## Forensics

`price_at_guard` es la fuente exclusiva del trigger. `price_raw` se guarda solo como forensics desde `trade.get("position", {}).get("market_price")` y puede ser `None`.

Extras registrados en `skip_log`:

- `guard_version`
- `guard_action`
- `trigger_reason`
- `match_zone_bucket`
- `price_at_guard`
- `price_raw`
- `amount`
- `effective_bankroll`
- `size_ratio`
- `edge_pct`
- `city_mode`
- `label`
- `question`
- `side`
- `counterfactual_resolved`

## Promocion Futura

El path de SKIP queda dormido. Solo puede hacer `continue` si:

- `UNSELLABLE_GUARD_ENABLED=1`
- `UNSELLABLE_GUARD_LOG_ONLY=0`
- el trigger se cumple

Promocionar de LOG_ONLY a SKIP requiere signoff explicito de Opus.

## Monitor diario

`tools/unsellable_guard_monitor.py` es una herramienta read-only para resumir el
guard sin revisar manualmente `skip_log`.

Lee `data/skip_log.jsonl` y rotados `skip_log.YYYY-MM-DD.jsonl` si existen. Para
candidatos LOG_ONLY exige:

- `skip_reason == "unsellable_guard_candidate"`
- `extras.guard_version == "unsellable_v1"`
- `extras.guard_action == "would_skip"`

Tambien vigila el caso de seguridad: cualquier `skip_reason ==
"unsellable_liquidity_guard"` o `extras.guard_action == "skipped"` se marca como
SKIP real inesperado mientras `LOG_ONLY=1`.

Niveles:

- `OK`: 0 candidatos en 24h y 0 skips reales.
- `WATCH`: 1-2 candidatos en 24h.
- `ACTION_REVIEW`: >=3 candidatos en 24h o >=5 acumulados en `skip_log`.
- `ACTION_SAFETY`: aparece algun skip real inesperado.

`ACTION_REVIEW` significa que hay evidencia suficiente para abrir revision
manual. No autoriza cambiar `UNSELLABLE_GUARD_LOG_ONLY`, ni activar SKIP, ni
tocar sizing/BANKROLL/reglas de riesgo.

La promocion de LOG_ONLY a SKIP sigue requiriendo revision manual / Opus. El
monitor solo envia Telegram para `WATCH`, `ACTION_REVIEW` o `ACTION_SAFETY`, con
anti-spam diario en `alerts_state.json`.
