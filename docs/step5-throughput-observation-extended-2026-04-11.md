# Step 5 Throughput Observation Extended - 2026-04-11

## Objetivo

Extender la observacion read-only de `Step 5` sobre una base limpia:

- snapshot runtime manifestado y fresco;
- `python tools/system_alignment_check.py` en verde;
- `python tools/system_alignment_check.py --decision-mode operational` en verde;
- sin tocar `bot.py`, policy live, thresholds, allowlists, bankroll ni `exact/range`.

## Preflight Y Frescura

- Snapshot refrescado por via canonica: `powershell -ExecutionPolicy Bypass -File .\tools\railway_runtime_snapshot_pull.ps1`
- `runtime_import_manifest.json` queda con `pulled_at=2026-04-11T10:52:35.9056147+00:00`
- Ventana operativamente razonable al interpretar esta observacion: `~1 min` entre pull y preflight
- `python tools/system_alignment_check.py`:
  - `ok=7`, `warning=1`, `error=0`
- `python tools/system_alignment_check.py --decision-mode operational`:
  - `ok=7`, `warning=1`, `error=0`
- `blocking_operational_collision_count=0`

La warning restante sigue siendo la ya aceptada: `runtime_policy_effective_view` lista de forma explicita `documented_drift=1` y `collision_noise=2`, sin blocker duro.

## Ventana Observada

- Fuente: solo archivos manifestados bajo `data/runtime_import/`
- Ventana: ultimos `20` ciclos de `data/runtime_import/cycles_history.jsonl`
- Rango: `2026-04-06T16:01:14.997875+00:00` -> `2026-04-11T08:00:38.111156+00:00`

## Funnel Canonico Del Tramo

- `raw_markets_fetched`: `330` por ciclo en los logs recientes
- `candidates_after_prefilters`:
  - total `307`
  - media `15.35` por ciclo
- `condition_filtered_out`: `285`
- `candidates_with_edge`: `4`
- `candidates_selected`: `4`
- `trades_executed`: `4`
- `shadow_opportunities_observed`: `2` ciclos con `shadow > 0`
- ciclos con buys reales: `3/20`

Lectura:

- el top del funnel sigue sano;
- el estrechamiento principal sigue ocurriendo mucho antes de edge/seleccion;
- el cuello dominante del tramo no es falta de mercados brutos ni falta general de edge, sino filtrado estructural.

## Distribucion De Skips En La Ventana

Top agregados de `skip_log.jsonl` sobre los mismos `20` ciclos:

- `date_out_of_range_past`: `2643`
- `price_out_of_range`: `1355`
- `blocked_city`: `553`
- `timezone_filter`: `462`
- `condition_filtered`: `230`
- `parse_fail`: `20`
- `below_min_edge`: `10`
- `existing_position`: `2`
- `kelly_too_low`: `1`
- `fuera_allowlist`: `1`

Lectura:

- el throughput reciente sigue perdiendo mucho mas por fecha, precio, bloqueo y condicion que por edge insuficiente;
- no aparece evidencia nueva que justifique reencuadrar el problema como uno de thresholds o bankroll;
- tampoco aparece un bug nuevo de accounting/counters en esta lectura.

## Auto-Canary: Senal Operativa O Solo Clasificacion

Ciudades `auto_canary` efectivas hoy:

- `Atlanta`
- `Munich`
- `New York City`
- `Seoul`
- `Shanghai`
- `Tokyo`

Resultado del tramo observado:

- las `4` compras reales del tramo salen de ciudades hoy `auto_canary`:
  - `Atlanta`
  - `Shanghai`
  - `Seoul`
  - `Tokyo`
- las `4` ya aparecen cerradas en `postmortem.json`
- las `4` cerraron como `RESOLVED_WIN`
- `PnL cerrado del tramo = +$1.69`

Esto es importante porque evita la lectura falsa de que `auto_canary` sea puro etiquetado sin impacto runtime.

## Pero El Comportamiento Sigue Siendo Discontinuo

La misma ventana muestra que `auto_canary` todavia no equivale a throughput consistente:

- `New York City` aparece en `15` ciclos, con `26` `condition_filtered`, `0` buys
- `Munich` aparece en `2` ciclos, `2` `condition_filtered`, `0` buys
- `Seoul` aparece en `20` ciclos, `38` `condition_filtered`, `1` buy
- `Shanghai` aparece en `17` ciclos, `26` `condition_filtered`, `5` `below_min_edge`, `1` buy
- `Atlanta` aparece en `10` ciclos, `14` `condition_filtered`, `1` buy
- `Tokyo` aparece en `6` ciclos, `8` `condition_filtered`, `1` buy

Lectura honesta:

- `auto_canary` si esta generando valor operativo real;
- pero ese valor sigue siendo esporadico y dominado por filtros estructurales antes de convertirse en throughput repetible;
- la evidencia actual no sostiene la tesis de que el sistema ya este en una fase de expansion natural del throughput.

## Shadow Y Casos Exploratorios

En esta ventana:

- solo hay `2` ciclos con `shadow_opportunities_observed`
- `Chicago` sigue sin repetir como caso operable:
  - `cycles_seen=5`
  - `condition_filtered=7`
  - `below_min_edge=1`
  - `0` buys
- `Hong Kong` queda en zona gris:
  - `condition_filtered=2`
  - `below_min_edge=2`
- `Beijing` sigue apareciendo mas como caso filtrado que como oportunidad operable:
  - `condition_filtered=10`
  - `0` buys

Lectura:

- no hay base nueva para manual canary de `Chicago`;
- tampoco hay evidencia nueva de que el shortlist shadow actual esconda una ciudad claramente perdida por policy;
- el seguimiento correcto sigue siendo observacion, no promocion.

## Conclusiones

1. `auto_canary` no es solo clasificacion: en esta ventana explica todo el throughput real ejecutado.
2. Aun asi, la muestra sigue siendo chica y la conversion sigue siendo intermitente.
3. El cuello dominante sigue siendo estructural (`date`, `price`, `condition`) y no un problema obvio de edge, sizing o bankroll.
4. No aparece un bug nuevo de correctness/accounting que obligue a parar esta linea y abrir una sesion de fixes.

## Implicacion Operativa

La conclusion correcta no es "abrir throughput" ni "hablar ya de monetizacion".

La conclusion correcta es mas estrecha:

- el sistema ya muestra que `auto_canary` puede convertir señal en trades reales;
- pero todavia no muestra suficiente repeticion ni volumen como para presentar eso como una base monetizable robusta;
- el siguiente uso honesto de esta evidencia es endurecer observacion comparativa, no mover policy.
