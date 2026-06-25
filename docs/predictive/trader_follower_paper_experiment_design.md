# Trader Follower Paper Experiment Design

## 1. Estado y decision

Opus ratifico `E3_TRIGGER_PASS` el 2026-06-25 con decision
`APPROVE_CODEX_READONLY_DESIGN_DOC_ONLY`.

Este documento es un contrato de diseno pre-registrado para un experimento
LOG_ONLY/paper. No autoriza runner, canary, live trading, cambios de runtime ni
cambios de policy.

La unica superficie ratificada para paper es:

- cohort: `60-70|trader_NO|no`
- strategy label: `SINGLE_CELL_60_70_TRADER_NO_NO`

Todas las demas celdas quedan demoted o solo disponibles como controles.

## 2. Contexto operativo

El bot esta en Bot Stable v0 / `STANDBY`.

Invariantes operativos vigentes:

- `SHADOW_ONLY_MODE=true`.
- `OPERATIONAL_PHASE=STANDBY`.
- `BANKROLL` en `HOLD $25`.
- Fase C no autorizada.
- BUY real prohibido.
- No live trading esperado.
- Forecast path congelado como predictor salvo trigger E2.
- Paper/log-only no es dinero y no produce P&L canonico.

Este experimento no toca `bot.py`, Railway, env vars, DB, scheduler, city modes,
BUY/SELL/SKIP, sizing, exact/NO ni BANKROLL.

## 3. Reframe del gate

El gate simple:

```text
n>=10 && top1<=50% && edge_ci.lower>0
```

era solo un trigger de rerun, no un gate de promocion.

El gate real de promocion es el de `docs/predictive/trader_following_benchmark_protocol.md`
section 5.4, ejecutado por `tools/trader_benchmark.py`. Incluye, como minimo:

- `n >= 30`.
- `n_traders >= 5`.
- `edge > 0.02`.
- `clustered edge_ci.lower > 0`.
- FDR.
- dominance/top1.
- leave-top-trader-out robustness.
- sign consistency.

La maquinaria demoto 14 de 15 celdas. La unica celda que sobrevive como
candidata de experimento paper es `60-70|trader_NO|no`.

## 4. Celda candidata

La celda candidata ratificada es:

| Campo | Valor |
|---|---:|
| cohort | `60-70|trader_NO|no` |
| verdict | `TRADER_ALPHA_CANDIDATE` |
| n | 99 |
| n_traders | 12 |
| clustered_ci.lower | 0.022 |
| forward_n | 73 |
| forward_ci.lower | 0.057 |
| LTO without top trader | +0.098 |
| p_fdr | 0.0177 |

Por que es candidata:

- Tiene muestra suficiente para un experimento paper acotado.
- Tiene diversidad minima de traders.
- El edge contra `avg_price_entered` es positivo con CI clusterizado por trader
  por encima de cero.
- La muestra forward sigue positiva.
- La robustez sin top trader sigue positiva.
- Pasa FDR bajo la familia de celdas evaluadas.

Por que no autoriza live:

- Es una unica celda y por tanto fragil.
- Depende de la fidelidad de BSR como fuente de resolucion.
- Puede haber leakage en `trader_historical_wr`.
- `sim_unit_pnl` es simulado, no canonico y no dinero.
- Cualquier paso live requiere nueva ratificacion Opus separada.

## 5. Controles

Las celdas demoted se usan solo como controles. No son superficies operables.

`60-70|trader_YES|no` responde si el efecto es especifico del lado NO del trader
o si todo el bucket `60-70` parece positivo.

`<60|trader_YES|no` responde si el supuesto edge aparece tambien en traders de
menor WR historico, lo que debilitaria la interpretacion por calidad de trader.

`70-80|trader_NO|no` y `>=80|trader_NO|no`, si proceden en el reporte paper,
responden si la senal candidata es solo un artefacto de favoritos de mercado,
dominancia de traders o precio alto, en vez de un patron propio del bucket
`60-70|trader_NO|no`.

Estos controles pueden explicar, demote o matar la tesis. No pueden promover una
superficie nueva.

## 6. Precondicion bloqueante: leakage audit

Nombre canonico:

```text
PRECONDITION_A_TRADER_HISTORICAL_WR_NO_OWN_ROW_LEAKAGE
```

Antes de cualquier runner LOG_ONLY debe auditarse, en modo read-only, como se
calcula `trader_historical_wr`.

La auditoria debe responder:

- Si `trader_historical_wr` incluye el outcome de la propia fila.
- Si el WR se calcula con informacion posterior a `avg_price_entered` o al entry.
- Si el bucket `60-70` habria sido observable antes de la decision paper.
- Si la celda candidata cambia cuando el WR historico se recalcula excluyendo la
  propia fila y cualquier informacion posterior al entry.

Archivos/campos a revisar en una auditoria futura:

- `tools/trader_benchmark.py`: consumo de `trader_historical_wr`, bucketing y
  filtros de elegibilidad.
- La fuente BSR row-level que alimenta `data/predictive/trader_benchmark_summary.json`.
- Campos BSR: `trader`, `trader_historical_wr`, `avg_price_entered`,
  `win_for_trader`, `checked_at`, `date`, `resolved`.
- Cualquier builder upstream que escriba `trader_historical_wr` en
  `blocked_signals_resolutions.jsonl`.

Si hay leakage, el experimento queda bloqueado. La unica salida aceptable seria
redefinir la celda con WR historico limpio y volver a Opus antes de runner.

## 7. Precondicion de resolucion: BSR fidelity spot-check

Nombre canonico:

```text
PRECONDITION_B_BSR_RESOLUTION_FIDELITY_SPOT_CHECK
```

BSR no debe usarse ciegamente como verdad absoluta. Antes de adjudicar paper win,
debe ejecutarse un spot-check independiente de resolucion sobre al menos 10% de
las filas paper.

Reglas:

- Priorizar filas nuevas post-freeze.
- Verificar de forma independiente que el outcome BSR coincide con la resolucion
  del mercado.
- Registrar conteo revisado, tasa de discrepancia y ejemplos saneados.
- Si aparece sesgo sistematico de resolucion, aplicar `KILL` y escalar resolver.
- Si hay errores aislados sin sesgo, corregir lectura paper o excluir filas
  afectadas antes de evaluar criterios de win.

## 8. Freeze y ventana paper

Freeze date: `2026-06-25`.

El experimento paper usa solo filas nuevas posteriores al freeze. La ventana
discovery existente no cuenta como paper win.

Duracion minima:

- 4 semanas posteriores al freeze, o
- hasta que la celda candidata acumule `fresh_forward_n >= 30` y `>=5` traders
  post-freeze,
- lo que ocurra mas tarde.

Si la muestra no madura, el resultado correcto es `NEEDS_MORE_DATA`, no
promocion.

## 9. Input y outputs

Inputs permitidos:

- BSR read-only.
- Candidate membership rule congelada: `60-70|trader_NO|no`.
- `avg_price_entered` como precio observado de entrada paper.
- Outcomes heredados de BSR, sujetos al spot-check de fidelidad.

Inputs prohibidos:

- `bot.py`.
- `trades.log`.
- wallets como superficie de promocion.
- env vars.
- Railway writes.
- DB writes.
- cualquier senal live.

Outputs futuros si Opus autoriza runner en otra sesion:

- paper positions non-canonical.
- `sim_unit_pnl` non-canonical / not money.
- report JSON/MD agregado.

Este documento no implementa esos outputs.

## 10. Paper prediction

Para cada fila BSR nueva post-freeze que cumpla `60-70|trader_NO|no`, el paper
predice seguir el lado NO del trader al `avg_price_entered` observado.

La unidad de resultado es:

```text
sim_unit_pnl = win_for_trader - avg_price_entered
```

No se ejecuta orden. No se envia senal live. No se toca `SHADOW_ONLY_MODE`.

## 11. Paper win criteria

Para declarar paper win deben cumplirse todos los criterios:

- `fresh_forward_n >= 30`.
- `n_traders >= 5`.
- `WR - mean_price > 0.02`.
- `clustered edge_ci.lower > 0`.
- Sign-consistent con discovery cell.
- `dominance/top1 <= 50%`.
- Spot-check de resolucion >=10% sin sesgo sistematico.
- `sim_unit_pnl_mean > 0`.
- Drawdown aceptable: la peor caida acumulada de `sim_unit_pnl`, ordenada por
  `checked_at` o entry paper, no debe borrar mas del 50% del edge acumulado
  maximo previo una vez `fresh_forward_n >= 30`.

Si el drawdown no puede medirse por falta de timestamp fiable, no hay paper win;
el estado queda `NEEDS_TIMESTAMP_FIDELITY`.

## 12. Kill / demotion criteria

Kill y demotion estan pre-registrados:

- `fresh-forward edge_ci.upper < 0` con `n>=30` => `KILL`.
- Sign flip vs discovery => `KILL`.
- Spot-check de resolucion revela sesgo sistematico => `KILL` y escalar resolver.
- `top1 > 50%` en fresh window => `DEMOTE`.
- `n_traders < 5` despues de la ventana minima => `NEEDS_MORE_DATA` o `DEMOTE`,
  segun evidencia y concentracion.
- Stale-signal lag invalida `avg_price_entered` => `DEMOTE`.
- Leakage confirmado en `trader_historical_wr` => `BLOCKED` hasta redefinir con
  WR historico limpio y nueva ratificacion Opus.

## 13. Metricas obligatorias

Todo reporte paper futuro debe incluir:

- `forward_n`.
- WR.
- `mean_price`.
- `sim_unit_pnl_mean`.
- edge vs price.
- clustered CI.
- p/FDR si aplica.
- dominance/top1/top2.
- trader diversity.
- LTO robustness.
- drawdown.
- stale signal lag.
- liquidity/exit realism.
- resolution spot-check status.
- fresh vs discovery split.

La salida debe etiquetar siempre `sim_unit_pnl` como simulated,
non-canonical y not money.

## 14. Safety / invariants

Invariantes explicitos:

- `BANKROLL $25 HOLD`.
- `SHADOW_ONLY_MODE=true`.
- `OPERATIONAL_PHASE=STANDBY`.
- Fase C no autorizada.
- BUY real prohibido.
- Paper/log-only no autoriza trading.
- Forecast no veta ni autoriza esta celda.
- exact/NO live sigue bloqueado.
- Ninguna salida paper autoriza runner sin nueva ratificacion Opus.
- Ninguna salida paper autoriza canary, live trading, city modes, sizing,
  scheduler, env vars, Railway writes ni cambios de `bot.py`.

## 15. Proxima decision

Despues de este design doc, el siguiente paso es volver a Opus para ratificar:

- el diseno paper,
- `PRECONDITION_A_TRADER_HISTORICAL_WR_NO_OWN_ROW_LEAKAGE`,
- `PRECONDITION_B_BSR_RESOLUTION_FIDELITY_SPOT_CHECK`,
- y el criterio de drawdown.

Solo si Opus aprueba, una sesion futura separada podria autorizar un runner
LOG_ONLY.

La decision futura tendria que ser explicita, por ejemplo:

```text
APPROVE_CODEX_LOG_ONLY_RUNNER
```

Hasta entonces, este documento es solo diseno read-only.
