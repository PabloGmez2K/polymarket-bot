# Sonnet review result - post-V2 cleanup P6+P7

Fecha: 2026-04-25
Revisor: Sonnet 4.6
Veredicto: APROBADO

## Findings

### Bajo - trazabilidad, no bloqueante

`city_policy_state.json` conserva metricas legacy para Seoul:

- `auto_canary_cities.Seoul.reason`: `5 edges shadow, 65 ciclos y pico 68.5%`
- `best_edge_pct=68.5`
- `shadow_edges=5`

Esos valores pertenecen al periodo pre-fix contaminado por la fuente Incheon. El reset P6 de `shadow_city_tracking.json` es correcto, pero `city_policy_state` conserva la base historica con la que se tomo la promocion a canary.

Impacto operativo: ninguno inmediato. Seoul sigue en canary y el sizing usa edge de mercado en vivo, no esos campos. El riesgo es de auditoria futura: si alguien usa `city_policy_state` para razonar sobre elegibilidad a active, puede ver `68.5%` inflado.

Recomendacion original: actualizar `city_policy_state.Seoul` reason + metricas en una proxima limpieza de trazabilidad. No bloqueaba continuar.

Estado: resuelto en la misma sesion de cierre. `auto_canary_cities.Seoul` queda alineado con la muestra post-P6:

- `reason`: `post-P6 traceability cleanup: Seoul canary retenida; shadow evidence aislada a datos post-fix Seoul City KMA desde 2026-04-17T12:22Z: 2 edges shadow, 28 ciclos y pico 26.4%`
- `best_edge_pct=26.4`
- `shadow_edges=2`

Backup Railway: `/app/data/city_policy_state.json.bak-seoul-p6-traceability`.

### Informativo

El backup remoto `/app/data/shadow_city_tracking.json.bak-pre-p6` no fue verificado por Sonnet por ser una revision read-only sin SSH. El backup local `data/runtime_import/shadow_city_tracking.json.bak-pre-p6` si queda confirmado.

## Validacion P6

Sonnet confirma que el corte elegido es correcto:

- `first_seen_at=2026-04-17T12:22:40.235413+00:00`
- `markets_seen=54`
- `edge_hits=2`
- `cycles_seen=28`
- `best_edge_pct=26.4`
- unica senal durable: `Seoul|2026-04-18|YES|at_or_above|21`
- `times_seen=2`
- `last_seen_at=2026-04-17T16:00:40.495025+00:00`

Conclusion: ningun dato Incheon queda en el tracker de Seoul.

## Validacion P7

Sonnet aprueba la metodologia conservadora:

- `n_closed>=10`
- `WR>=70%`
- `PnL>0`

Con la muestra actual no hay ciudad elegible para `MIN_EDGE_PER_CITY`. La propuesta de env var queda correctamente como diseno futuro, no como accion.

## Recomendacion final

Seguir sin cambios de codigo ni Railway.

El unico follow-up es una correccion menor de trazabilidad en `city_policy_state.json` para Seoul, a ejecutar cuando convenga en una sesion de limpieza documental/datos.
