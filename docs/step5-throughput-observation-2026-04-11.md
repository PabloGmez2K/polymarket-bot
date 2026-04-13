# Step 5 Throughput Observation - 2026-04-11

## Objetivo

Observar el throughput con los contratos ya alineados, sin tocar `bot.py`, policy live, thresholds, allowlists ni bankroll.

## Preflight

- `python tools/system_alignment_check.py`
- Estado en `observe`: `ok=6`, `warning=2`, `error=0`
- Los warnings restantes siguen siendo los aceptados:
  - `runtime_policy_effective_view`: colisiones/divergencias explicitadas.
  - `runtime_ledger`: `policy_divergence=6` explicitado.

## Lectura Del Funnel Reciente

Ventana observada: ultimos `20` ciclos de `data/runtime_import/cycles_history.jsonl`.

- `raw_markets_fetched`: sigue en torno a `330` por ciclo en `data/runtime_import/decisions.log`.
- `candidates_after_prefilters` legacy `markets_evaluated`: `286` total, media `14.3` por ciclo.
- `candidates_with_edge`: `4` total.
- `candidates_selected`: `4` total.
- `trades_executed`: `4` compras en `3` ciclos.
- `shadow_opportunities_observed`: `1` ciclo reciente con `shadow=1`.
- `condition_filtered_out`: `267` total en `20` ciclos.

Lectura:

- El sistema no esta viendo pocos mercados brutos.
- El cuello principal del throughput reciente no es descubrimiento bruto.
- El estrechamiento dominante ocurre antes de la seleccion final, sobre todo por `condition_filtered_out`.

## Distribucion De Skips Recientes

Agregado reciente sobre `skip_log.jsonl`:

- `date_out_of_range_past`: `910`
- `price_out_of_range`: `648`
- `timezone_filter`: `220`
- `condition_filtered`: `111`
- `blocked_city`: `88`
- `below_min_edge`: `7`
- `kelly_too_low`: `1`
- `fuera_allowlist`: `1`

Lectura:

- El techo reciente no esta dominado por `below_min_edge`.
- El bot pierde mucho mas flujo por fecha, precio y condicion permitida que por edge insuficiente.
- Esto es consistente con la lectura de Opus: no conviene enmarcar el problema principal como "falta throughput por edge demasiado estricto".

## Casos Operables Recientes

Trades abiertos desde `2026-04-07` con `buy_count > 0` en `postmortem.json`:

- `4` trades recientes
- `3` ya cerrados
- `3/3` cerrados ganadores
- `PnL cerrado = +$1.31`
- Ciudades: `Atlanta`, `Shanghai`, `Seoul`, `Tokyo`

Lectura:

- El pipeline sigue siendo capaz de producir operaciones validas.
- La muestra sigue siendo demasiado chica para justificar cambios operacionales.
- La señal correcta no es "abramos throughput", sino "no romper el pipeline mientras seguimos midiendo".

## Chicago Y Shadow Accounting

Hallazgos actuales:

- `shadow_city_tracking.json` sigue mostrando a `Chicago` con evidencia real (`edge_hits=1`, `best_edge_pct=35.1`, `cycles_seen=7`).
- En el ciclo `2026-04-09T23:00`, `cycles_history` registra `shadow=1`.
- En el ciclo `2026-04-10T08:00`, Chicago ya no aparece como oportunidad con edge suficiente; aparece un caso `below_min_edge=6.5%`.
- En el ciclo `2026-04-10T16:00`, Chicago cae por `condition_filtered` en mercados `range`.

Lectura:

- No aparece una contradiccion nueva que obligue a tocar policy o a pedir Opus ya.
- Chicago sigue siendo un caso a vigilar, pero con esta evidencia no hay base para promocion manual.
- Tampoco hay aqui una prueba nueva de bug de accounting; por ahora la historia encaja con "hubo una oportunidad shadow aislada y luego no se repitio de forma operable".

## Conclusion Operativa

La observacion honesta de `Step 5` refuerza tres ideas:

1. `raw_markets_fetched` sigue sano; el problema no es discovery bruto.
2. El throughput reciente se estrecha principalmente por `condition_filtered_out`, junto con `price_out_of_range` y `date/time gating`.
3. No hay evidencia nueva suficiente para tocar throughput, policy o canaries manuales.

## Siguiente Paso Recomendado

Seguir en modo read-only y completar una observacion algo mas larga antes de cualquier cambio operacional:

- mantener `system_alignment_check.py` como preflight obligatorio;
- seguir leyendo funnel con nombres canonicos;
- vigilar si Chicago u otra ciudad vuelve a producir `shadow_opportunities_observed` repetidas y consistentes;
- solo pedir revision de Opus antes de proponer un cambio de throughput/policy o si aparece una contradiccion nueva de arquitectura/correctness.
