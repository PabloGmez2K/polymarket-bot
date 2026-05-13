# Auto-Attestation Feasibility Audit - A3

**Fecha:** 2026-05-13
**Modo:** NORMAL / read-only audit / docs-only
**Estado:** No implementa codigo, no runtime, no env vars, no DB writes, no BANKROLL.

## Resumen

Un sistema automatico de continuidad de wallet es viable solo si nace como ledger separado y debil: `data/wallet_continuity_checks.jsonl`, con `actor=system_auto`, `type=no_external_flow_inferred` y `confidence=weak_provisional`.

No es viable automatizar escrituras en `wallet_cash_flows.jsonl`. Ese archivo ya tiene semantica de atestacion manual fuerte (`actor=pablo_manual`) y sus consumidores lo usan como evidencia para cobertura de cash flows. Mezclar inferencias automaticas ahi contaminaria PnL, readiness y la futura discusion B5/B6.

Veredicto principal: **REMINDER_ONLY** ahora. La ruta futura **FEASIBLE_WITH_SEPARATE_LEDGER** es razonable, pero solo despues de un contrato nuevo que garantice que `coverage_weak_provisional` nunca suma a `cash_flows.coverage_days`, nunca cambia `cash_flows.status`, nunca promueve `canonical_source`, y nunca desbloquea BANKROLL.

## Mapa de consumidores

| Consumidor | Lee / escribe | Uso actual de `wallet_cash_flows.jsonl` | Riesgo si se automatiza el ledger actual |
|---|---|---|---|
| `tools/wallet_cash_flow_log.py` | Escribe manualmente y valida | CLI append-only manual; schema v2; `ACTOR="pablo_manual"`; tipos permitidos: `deposit`, `withdrawal`, `no_cash_flow_attestation`, `adjustment`; rechaza `inferred`, `auto`, `reconstructed`, `estimated` | Alto: romperia la garantia humana y el contrato explicitamente anti-inferencia |
| `tools/wallet_snapshot.py` | Lee | Calcula `cash_flows.status`, `coverage_days_7d`, `attestation_count`, `last_attestation_at`, ajustes 7d y `phase2_readiness` | Alto: podria convertir inferencias debiles en `attested_full_7d` |
| `tools/pnl_report.py` | Lee | Calcula horizontes 1D/1W/1M/ALL desde `wallet_portfolio_snapshots.jsonl` + `wallet_cash_flows.jsonl`; emite `inputs.cash_flows.coverage_days`; mantiene `canonical_source="none"` y `bankroll_readiness="blocked"` | Muy alto: `coverage_days` alimenta bloqueos/promociones provisionales y podria crear falsa cobertura B3/B5 |
| `tools/daily_kanban_digest.py` | Lee | Resume `cash_flows.status`, `coverage_days_7d`, rechazos y attestations para el digest | Medio: riesgo de copy ambiguo si presenta inferencia como cobertura real |
| `bot.py` via `maybe_run_wallet_snapshot` | Indirecto | Ejecuta `wallet_snapshot.py` diario; alerta one-shot si `phase2_ready` | Alto si la cobertura automatica cambiara `phase2_ready` |
| `bot.py` via `maybe_run_pnl_reconciliation` | Indirecto / paralelo | No lee cash flows directamente; reporta falta de P/L wallet o divergencia lifecycle vs wallet | Bajo directo, pero buen canal de visibilidad manual |
| `bot.py` via `maybe_run_bankroll_scaling_monitor` | No lee cash flows directo | Bloquea scaling si PnL es non-canonical; consume performance/lifecycle/score/DB | Bajo directo, pero cualquier cambio a `canonical_source` lo afectaria semanticamente |
| Tests y `verify_before_deploy.py` | Validan contrato | Fijan que el ledger real local no exista versionado, que el tool sea manual, stdlib-only, sin BANKROLL/readiness/trading | Alto: habria que anadir guardrails si se crea ledger nuevo |

## Que asumirian ante `wallet_continuity_checks.jsonl`

Si se anade el archivo sin tocar consumidores, no pasa nada: las herramientas actuales lo ignoran.

Si se integra en el futuro, los consumidores deben asumir:

- Es evidencia **debil y provisional**, no attestation.
- No prueba ausencia de depositos/retiros; solo infiere que no hay senales visibles de flujo externo.
- No sustituye a `wallet_cash_flows.jsonl`.
- No puede explicar `possible_deposit=true` por si solo.
- No puede aportar `amount_usdc`.
- No puede definir `t0` para ALL.
- No puede cambiar `cash_flows.status` ni sumar a `cash_flows.coverage_days`.
- Solo puede alimentar campos paralelos, por ejemplo `continuity_checks.coverage_weak_provisional_days`.

## Donde se calcula coverage

`cash_flows.coverage_days` se calcula en `tools/pnl_report.py` dentro de `build_report`: toma la ultima snapshot valida, abre una ventana de 7 dias hacia atras y llama a `merged_coverage_days(cash_flows, start, latest_snapshot_at)`. Ese valor sale en `inputs.cash_flows.coverage_days`.

Ademas hay calculos relacionados:

- `tools/pnl_report.py` usa `merged_coverage_days` dentro de cada horizonte para decidir `blocked`, `provisional` o `canonical_candidate`.
- `tools/wallet_snapshot.py` calcula `cash_flows.coverage_days_7d` en `cash_flows_summary`, con ventana fija de 168 horas y solo filas `type=no_cash_flow_attestation`.
- `tools/daily_kanban_digest.py` tiene logica similar para `coverage_days_7d` del digest.

Conclusion: cualquier `coverage_weak_provisional` debe implementarse como metrica nueva y separada, no como input a esas funciones de cobertura fuerte.

## Cambios potenciales

| Cambio futuro | Archivos probables | Utilidad | Guardrail requerido | Recomendacion |
|---|---|---|---|---|
| Nuevo schema `wallet_continuity_checks.jsonl` | Nuevo doc + tool nuevo | Registrar checks automaticos sin tocar cash flow manual | `actor=system_auto`, `type=no_external_flow_inferred`, `confidence=weak_provisional`, no `amount_usdc` | Viable con diseno separado |
| Parser read-only de continuidad | Tool nuevo o helper en `pnl_report.py` | Calcular `coverage_weak_provisional_days` | Campo bajo `inputs.continuity_checks`, nunca bajo `inputs.cash_flows` | Viable |
| Mostrar en digest | `daily_bot_digest` o `daily_kanban_digest` | Recordar a Pablo que falta attestation manual | Copy: "manual assist"; no PnL canonico; no BANKROLL | Mejor puente |
| Reminder A3 diario/2-3 dias | Daily digest o alerta existente | Evitar gaps de attestation | Anti-spam, una vez/dia maximo, mensaje manual-only | GO como puente |
| Usar en `wallet_snapshot.py` | `tools/wallet_snapshot.py` | Exponer continuidad debil junto a status fuerte | No alterar `phase2_ready`, `cash_flows.status`, `wallet_pnl_available` | Posible, pero no primera opcion |
| Usar en `pnl_report.py` | `tools/pnl_report.py` | Diagnostico de por que falta cobertura fuerte | No alterar horizontes ni promotion blockers | Solo despues de tests |
| Usar en `bankroll_scaling_check.py` | `tools/bankroll_scaling_check.py` | Mostrar evidencia auxiliar | Debe seguir bloqueando por `pnl_source_non_canonical` | Evitar salvo readout muy claro |
| Escribir en `wallet_cash_flows.jsonl` | `tools/wallet_cash_flow_log.py` | Ninguna aceptable | Rompe contrato manual | NO-GO |

## Reminder/manual assist

Mejor puente: **daily digest**.

Motivo: A3 es una tarea recurrente, de baja urgencia y manual. Encaja mejor en un digest que en una alarma de salud o scaling. El mensaje deberia decir algo como:

```text
A3 cash-flow attestation: falta cobertura manual desde <timestamp>.
Sugerencia: si Pablo confirma que no hubo depositos, retiros ni otros cash flows externos, ejecutar wallet_cash_flow_log.py append manual.
Esto no desbloquea BANKROLL ni canonical_source.
```

Ranking de herramientas existentes:

| Opcion | Veredicto | Por que |
|---|---|---|
| Daily digest | Mejor | Canal anti-spam, manual-only, ya agrega observabilidad y throughput; evita crear alarma nueva |
| `pnl_reconciliation_alert` | Segunda | Ya habla de P/L wallet vs lifecycle; util si el recordatorio se vincula a "falta wallet P/L completo" |
| `bot_health_check` | No ideal | Su foco es salud runtime/DB/logs; A3 no es health failure |
| `bankroll_scaling_check` | No ideal | Esta demasiado cerca de BANKROLL; podria inducir a pensar que continuidad debil desbloquea scaling |

## A4 y B5

A4 esta parcialmente cubierto por alarmas/readouts existentes. `bot.py` ya tiene `maybe_run_sl_intra_guard_review`, que observa skips del guard SL_intra y envia un review cuando hay muestra minima resuelta. La documentacion actual fija el re-check A8/A4 para 2026-05-21 o al 5o guarded event. Falta visibilidad si Pablo quiere un recordatorio calendario antes de que el umbral automatico se cumpla; eso tambien deberia ir al digest, no a BANKROLL.

B5 no esta cubierto como decision. Hay readouts que muestran blockers (`pnl_report.py`, `bankroll_scaling_check.py`, `pnl_reconciliation_alert.py`, docs de evidencia), pero B5 requiere spec formal y Opus review despues de cobertura suficiente. La visibilidad operativa existe; falta el workflow de promocion formal, que no debe automatizarse desde A3.

## Riesgos

- **Contaminacion semantica:** que una inferencia automatica parezca atestacion manual.
- **Falso negativo:** no detectar deposito/retiro pequeno o externo y marcar continuidad debil como "sin flujo".
- **Promotion creep:** que `coverage_weak_provisional` acabe sumando a `cash_flows.coverage_days`.
- **Copy peligroso:** que Telegram/digest sugiera "ready" o "coverage ok" sin confirmacion humana.
- **Acoplamiento indirecto a BANKROLL:** `bankroll_scaling_check.py` no lee cash flows directamente, pero cualquier futuro `canonical_source` podria afectarlo.
- **Duplicidad de fuentes:** dos ledgers con ventanas superpuestas pueden confundir auditorias si no hay nombres y estados muy claros.
- **Anti-spam:** A3 cada 2-3 dias puede volverse ruido si no se agrupa en digest.
- **B5 premature:** usar la cobertura debil como atajo antes de los 28 dias y Opus signoff romperia el contrato de readiness.

## Recomendacion GO/NO-GO

| Opcion | Veredicto |
|---|---|
| Auto-escribir `wallet_cash_flows.jsonl` | **DO_NOT_AUTOMATE** |
| Cambiar `actor=pablo_manual` o aceptar `system_auto` en ese ledger | **DO_NOT_AUTOMATE** |
| Usar `type=no_cash_flow_attestation` para inferencias | **DO_NOT_AUTOMATE** |
| Crear ledger separado de continuidad debil | **FEASIBLE_WITH_SEPARATE_LEDGER**, pero no ahora como patch |
| Integrar `coverage_weak_provisional` en PnL/BANKROLL | **DO_NOT_AUTOMATE** si afecta gates; solo readout paralelo |
| Puente actual de A3 | **REMINDER_ONLY** |

## Veredicto

**REMINDER_ONLY** para la accion inmediata.

**FEASIBLE_WITH_SEPARATE_LEDGER** como diseno futuro, siempre que el contrato sea estricto:

- `wallet_cash_flows.jsonl` sigue siendo manual y fuerte.
- `wallet_continuity_checks.jsonl` es automatico, debil y paralelo.
- `coverage_weak_provisional` no contamina `cash_flows.coverage_days`.
- `canonical_source` permanece `none`.
- `bankroll_readiness` permanece `blocked`.
- BANKROLL, Fase C, trading core, city modes, scheduler, env vars y DB runtime quedan fuera de alcance.
