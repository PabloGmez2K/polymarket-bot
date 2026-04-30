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
