# Phase 6.5 - Collision Severity Hardening - 2026-04-11

## Objetivo

Introducir una segunda capa de guardrails para que el preflight `operational`
no bloquee por un contador ciego de colisiones, sino por contradicciones
operativas realmente severas.

Scope de esta mini fase:

- no tocar `bot.py`
- no tocar policy live
- no escribir `city_policy_state.json`
- no cambiar thresholds, allowlists, bankroll ni `exact/range`

## Cambios aplicados

1. `runtime_policy_effective_view` ahora clasifica colisiones en:
   - `collision_noise`
   - `documented_drift`
   - `blocking_operational_collision`

2. `reference_trader_city_market_cross.py` deja de publicar claims legacy de
   policy cuando existe `data/runtime_policy_effective_view.json`.
   Su `policy_mode` pasa a alinearse con `effective_mode` y conserva
   `policy_source` para dejar explícito el origen.

3. `system_alignment_check.py` deja de usar `collision_count > 5` como
   bloqueo operacional principal y pasa a bloquear por:
   - `blocking_operational_collision_count > 0`

4. `docs/decision-preflight-rules-2026-04-11.md` se actualiza para reflejar
   la nueva taxonomía y distinguir ruido/documented drift de blockers reales.

## Resultado observado

Antes de Phase 6.5:

- `observe`: `ok=6`, `warning=2`, `error=0`
- `operational`: `ok=6`, `warning=1`, `error=1`
- bloqueo: `collision_count=17 > 5`

Despues de Phase 6.5:

- `observe`: `ok=7`, `warning=1`, `error=0`
- `operational`: `ok=7`, `warning=0`, `error=1`
- bloqueo: `blocking_operational_collision_count=1`
- `runtime_ledger`: pasa de warning a `ok`

Foto actual de colisiones en `runtime_policy_effective_view`:

- `collision_count=4`
- `collision_category_counts`:
  - `blocking_operational_collision=1`
  - `documented_drift=1`
  - `collision_noise=2`

## Lectura operativa

El preflight ya no esta bloqueado por un agregado ciego.

La barrera real queda reducida a:

- `Dallas` como `blocking_operational_collision`

Y quedan visibles pero no bloqueantes por si solos:

- `Atlanta` como `documented_drift`
- `lucknow`
- `sao paulo`
  ambas como `collision_noise`

## Que se limpio de facto

- el bloque canary `Munich / New York City / Seoul / Shanghai / Tokyo`
  deja de aparecer como drift cross/runtime fuerte porque `cross` ya no
  insiste en `shadow` cuando la `effective view` dice `canary`.
- `Chicago` y `Buenos Aires` dejan de arrastrar claims `active` legacy dentro
  de `cross`.
- el ledger runtime deja de emitir `policy_divergence=6` y pasa a
  `drift_flag_counts={}`.

## Que sigue pendiente

No queda autorizado abrir monetizacion, throughput o policy.

El siguiente blocker real ya esta aislado:

- `Dallas`: `env_declared_mode=active` vs `runtime_policy_mode=auto_shadow`

La siguiente sesion correcta puede enfocarse solo en el claim superviviente
de Dallas y en decidir si conviene alinear la fuente declarativa que sigue
diciendo `active`, sin tocar runtime ni policy live.
