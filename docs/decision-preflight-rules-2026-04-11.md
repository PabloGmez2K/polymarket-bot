# Decision Preflight Rules - 2026-04-11

## Objetivo

Convertir el preflight de alignment en una frontera clara entre:

- sesiones de `observe` read-only;
- y sesiones `operational` donde se esta evaluando un cambio real de throughput, policy o correctness.

## Modos

### `observe`

- sirve para auditoria, lectura y checkpoints;
- permite warnings aceptados mientras no haya errores;
- no autoriza cambios operacionales por si mismo.

### `operational`

- se usa cuando la sesion quiere decidir o proponer un cambio real;
- endurece el preflight;
- debe bloquear la decision si la frescura o las colisiones hacen que la foto no sea confiable.

## Reglas Operativas

1. Ningun cambio operacional debe evaluarse con `runtime_policy_effective_view` fuera del SLO de frescura.
   Regla inicial: effective view con mas de `6` horas bloquea modo `operational`.

2. Ningun cambio operacional debe evaluarse con `blocking_operational_collision > 0`.
   La meta no es eliminar drift documental perfecto; la meta es no tomar decisiones cuando siga viva una contradiccion fuerte sobre tradabilidad o modo efectivo.

3. `collision_count` total no debe leerse como severidad por si solo.
   Debe separarse en:
   - `collision_noise`
   - `documented_drift`
   - `blocking_operational_collision`

4. `documented_drift` puede ser tolerable en sesiones de observacion o lectura, pero debe quedar visible.
   Ejemplo tipico: canaries efectivas cuya capa `cross` sigue en `shadow`.

5. Ninguna decision basada en PnL reciente debe ejecutarse con `< 20` trades cerrados comparables.
   Con muestras menores, el PnL reciente se trata como observacion, no como autorizacion.

6. `ACTIVE_TRADING_CITIES` no autoriza lectura operativa por si solo.
   La verdad operativa debe pasar por `effective_mode` en `runtime_policy_effective_view`.

7. `markets_evaluated` no autoriza interpretacion del funnel por si solo.
   Debe leerse como alias legacy de `candidates_after_prefilters`.

## Lo Que Hoy Se Enforcea

En `python tools/system_alignment_check.py`:

- la sesion puede declarar `--decision-mode observe` o `--decision-mode operational`;
- en modo `operational`, el check bloquea si el effective view supera el SLO de frescura;
- en modo `operational`, el check bloquea si `blocking_operational_collision_count > 0`;
- en modo `operational`, `collision_noise` y `documented_drift` siguen visibles en la salida aunque no impliquen bloqueo por si solos;
- el escaneo semantico revisa prompts y docs canonicos para evitar drift sobre `effective_mode` y funnel naming.

## Lo Que Aun Es Regla Humana

Todavia no se bloquea automaticamente por:

- `< 20` trades cerrados;
- decisiones basadas en PnL reciente con muestra chica.

Esa regla queda explicita aqui para que no se cuele en reviews o prompts.

## No Toca

- `bot.py`
- `city_policy_state.json`
- thresholds
- allowlists
- bankroll
- `exact/range`
