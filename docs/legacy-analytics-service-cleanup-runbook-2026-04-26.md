# Legacy Analytics Service Cleanup Runbook - 2026-04-26

Estado: servicios pausados, no borrados.

## Servicios afectados

- `phase5-visibility`
- `city-intelligence`

## Que se conserva

- Scripts del repo: `tools/phase5_*`, `tools/city_intelligence_*`, comparadores y trackers.
- Docs historicos: `docs/phase5-*`, `docs/city-intelligence-*`, arquitectura y planes.
- Seed data versionada: `seed_data/phase5/`.
- Funcionalidad viva: el bridge read-only de `polymarket-bot` que lee runtime real y regenera city-intelligence.

## Que ya no debe vivir como servicio separado

- Scheduler Railway de `phase5-visibility`.
- Scheduler Railway separado de `city-intelligence`.
- Volumenes dedicados que solo contienen estado historico de esos servicios, una vez cumplida la ventana de observacion.

## Criterio para borrar servicios y volumenes

Esperar al checkpoint `2026-05-03` y borrar solo si:

- `polymarket-bot` sigue en `SUCCESS`.
- `city-intelligence` y `phase5-visibility` siguen sin deployment activo.
- El bridge in-bot produjo summaries utiles sin `runtime_inputs_missing` legacy.
- No se echo en falta la alerta Shanghai+Chicago ni el scheduler separado.
- `data/service_transition_followup.json` mantiene el checkpoint `legacy_services_delete_readiness_2026_05_03`.

## Secuencia de borrado segura

1. Verificar estado:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 service status -a --json
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 volume list
```

2. Confirmar que `polymarket-bot` cubre la funcionalidad:

```powershell
python tools\city_intelligence_daily_summary.py --dry-run
python verify_before_deploy.py
```

3. Borrar primero servicios legacy desde Railway Dashboard o API GraphQL `serviceDelete`.

La CLI Railway instalada en esta maquina no expone `service delete`; en la sesion 205 ya se uso GraphQL para borrar un servicio vacio cuando hizo falta.

4. Borrar despues solo estos volumenes:

- `city-intelligence-volume`
- `phase5-visibility-volume`

Comandos CLI para volumenes:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 volume delete -v city-intelligence-volume -y
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 volume delete -v phase5-visibility-volume -y
```

5. No borrar:

- `polymarket-bot`
- `polymarket-bot-volume`
- scripts/docs/seed data versionados en el repo

## Rollback antes de borrar

Antes del borrado definitivo, se puede volver a levantar un servicio pausado con redeploy desde Railway. Despues de borrar servicio o volumen, el rollback deja de ser inmediato y pasa a depender de repo + seed data.
