# System Alignment Phase Closeout - 2026-04-11

## Objetivo De Esta Fase

Cerrar la estandarizacion del sistema antes de tocar throughput o policy.

La meta de esta fase no era abrir mas trades ya. La meta era dejar a `polymarket-bot`, `city-intelligence`, docs y checks diciendo la misma verdad operativa para que cualquier cambio futuro no deje capas desalineadas.

## Lo Que Queda Cerrado

1. `runtime_import` es atomico y bijectivo con su manifest.
2. `runtime_policy_effective_view` resuelve la policy efectiva en una sola vista read-only.
3. El funnel tiene nombres canonicos y alias legacy explicitados.
4. `system_alignment_check.py` valida los contratos principales en un solo comando.
5. `city-intelligence` ya separa `runtime_derived_targets` de `exploratory_targets`.
6. Ya existe una primera lectura honesta de throughput reciente.
7. Ya existe una shortlist separada de vigilancia shadow real.

## Estado Operativo Actual

- `python tools/system_alignment_check.py`
- Resultado actual en `observe`: `ok=6`, `warning=2`, `error=0`
- Resultado actual en `operational`: `ok=6`, `warning=1`, `error=1` por `collision_count=17 > 5`

Warnings aceptados por ahora:

- `runtime_policy_effective_view`: colisiones/divergencias explicitadas.
- `runtime_ledger`: `policy_divergence=6` explicitado.

Lectura:

- no queda un contrato roto bloqueando trabajo;
- lo que queda abierto es interpretacion operativa futura, no cableado basico roto.
- antes de cualquier cambio operacional conviene pasar por la mini `Phase 6` de hardening del preflight, para cubrir drift semantico y frescura de decision.

## Preguntas Que Esta Fase Ya Responde Bien

- Que snapshot runtime es valido.
- Que ciudad esta en que modo efectivo.
- Que significa `markets_evaluated` como alias legacy de `candidates_after_prefilters` frente a `raw_markets_fetched`.
- Si los targets de `city-intelligence` son runtime-derived o exploratorios.
- Si una sesion nueva esta partiendo de contratos alineados o no.

## Lo Que Esta Fase Deliberadamente No Resuelve Todavia

- si conviene abrir throughput;
- si hay que tocar `exact/range`;
- si Chicago merece promocion manual;
- si Dallas debe volver a `active`;
- cambios en `bot.py`, bankroll, thresholds, allowlists o policy live.

## Phase 6 Mini

El siguiente trabajo safe despues del cierre base es:

- endurecer `system_alignment_check.py` con `decision_mode`;
- escanear prompts/docs canonicos para detectar drift semantico;
- fijar un contrato explicito `bot.py` counters -> funnel canonico;
- fijar reglas de preflight para sesiones `operational`.

## Criterio Practico De Cierre

Podemos considerar esta fase suficientemente cerrada cuando aceptemos esta regla:

- cualquier trabajo nuevo sobre throughput, policy o correctness parte de `system_alignment_check.py` y usa los artefactos canonicos ya definidos, sin reabrir discusiones de fuente de verdad basica.

## Cuando Reabrir Esta Fase

Solo reabrir esta fase si aparece una contradiccion nueva en alguno de estos contratos:

- manifest runtime;
- effective policy view;
- naming del funnel;
- tagging de targets;
- checklist de preflight.
