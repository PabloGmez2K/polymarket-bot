# Plan Operativo: `city-intelligence` Y `phase5-visibility`

Fecha de arranque: 2026-04-23

## Objetivo

Convertir la review de Opus en una transicion operativa reversible:

- `city-intelligence` deja de ser un servicio Railway separado y queda como dominio analitico ejecutado desde `polymarket-bot` mediante el bridge runtime.
- `phase5-visibility` deja de ser un servicio vivo y queda absorbido como metodologia de visibilidad/benchmark dentro de `city-intelligence`.
- Los avisos de seguimiento salen por el resumen diario de City Intelligence, sin crear otro scheduler.

No se toca trading core, NOAA core, scheduler core, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`.

## Transformacion Objetivo

| Antes | Despues | Utilidad operativa |
| --- | --- | --- |
| Servicio Railway `city-intelligence` con volumen separado | Dominio `city-intelligence` in-bot, ejecutado por bridge read-only | Una sola verdad runtime; ledger/gate/daily summary accionables sin `runtime_inputs_missing` falso |
| Servicio Railway `phase5-visibility` legacy | Modulo/metodologia `visibility benchmark` archivada y absorbida | Comparar visibilidad de ciudad candidata vs benchmark sin segunda voz decisional |

## Fases

### Fase 0 - Arranque y plan

Estado: en curso desde 2026-04-23.

Acciones:

- Registrar esta transicion como plan operativo.
- Programar avisos/checkpoints en `data/service_transition_followup.json`.
- Hacer auditoria live de servicios Railway antes de cambiar variables.

Salida esperada:

- Plan versionado.
- Avisos diarios integrados en `city_intelligence_daily_summary`.
- Evidencia de estado actual de `city-intelligence` y `phase5-visibility`.

### Fase 1 - Silenciar y observar

Ventana recomendada: 2026-04-23 a 2026-04-28.

Estado: iniciada el 2026-04-23T08:05Z.

Acciones:

- Silenciar Telegram en los servicios separados `city-intelligence` y `phase5-visibility`, preferiblemente quitando `TELEGRAM_TOKEN` solo en esos servicios.
- Mantener scripts, docs, volumenes y servicios vivos para reversibilidad.
- Confirmar que el bridge diario desde `polymarket-bot` produce `runtime_inputs_status=available`, `overall_status=ok` y un unico daily summary.

Evidencia inicial:

- Railway `service status -a --json`: `polymarket-bot`, `city-intelligence` y `phase5-visibility` siguen en `SUCCESS`.
- `TELEGRAM_TOKEN` eliminado solo de `city-intelligence` y `phase5-visibility`.
- `polymarket-bot` conserva `TELEGRAM_TOKEN`, por lo que el bridge/daily summary canonico puede seguir enviando Telegram.
- Ambos servicios legacy fueron reiniciados para cargar el entorno ya silenciado.
- `city-intelligence` alcanzo a enviar el summary legacy de las 07:00 UTC antes del silencio; el primer dia realmente limpio sera 2026-04-24.

Salida esperada:

- Cero alertas duplicadas desde servicios separados.
- El humano sigue recibiendo el summary util desde `polymarket-bot`.
- No se pierde evidencia de ledger/gate/tracker.

### Fase 2 - Pausar servicios separados

Ventana recomendada: 2026-04-28 a 2026-05-01.

Estado 2026-04-26: ejecutada antes del checkpoint previsto.

Evidencia de pausa:

- `phase5-visibility` queda sin deployment activo mediante `railway down -s phase5-visibility -y`.
- `city-intelligence` queda sin deployment activo mediante `railway down -s city-intelligence -y`.
- Los volumenes `phase5-visibility-volume` y `city-intelligence-volume` siguen adjuntos para rollback/historial.
- `polymarket-bot` sigue en `SUCCESS` y conserva el runtime/emisor canonico.

Acciones:

- Pausar `phase5-visibility` si no se echo en falta durante la ventana de silencio.
- Pausar `city-intelligence` si el bridge acumulo al menos 5 ejecuciones diarias validas.
- Confirmar que solo `polymarket-bot` escribe los artefactos canonicos consumidos por humanos.

Salida esperada:

- `phase5-visibility` deja de ser scheduler vivo.
- `city-intelligence` separado deja de competir con el bridge.
- Queda una sola voz operativa: `polymarket-bot` + bridge + docs/artefactos.

### Fase 3 - Borrado controlado

Ventana recomendada: desde 2026-05-03 si la pausa no rompe nada.

Alarma programada: `legacy_services_delete_readiness_2026_05_03` en `data/service_transition_followup.json`.

Condiciones:

- `polymarket-bot` sigue en `SUCCESS`.
- El bridge in-bot cubre runtime import, ledger, gate, pipeline y daily summary con `runtime_inputs_status=available`.
- No reaparecen avisos legacy `runtime_inputs_missing`.
- Nadie echo en falta la alerta Shanghai+Chicago ni el scheduler separado.
- Los artefactos utiles quedan preservados como scripts/docs/seed data versionados.

Runbook: `docs/legacy-analytics-service-cleanup-runbook-2026-04-26.md`.

### Fase 4 - Archivo y cambio de foco

Ventana recomendada: 2026-05-01 a 2026-05-07.

Acciones:

- Anadir nota de legacy a `docs/phase5-visibility-service.md`, `docs/phase5-visibility-pipeline.md` y `docs/phase5-visibility-telegram-alert.md`.
- Conservar `seed_data/phase5/` y `data/phase5_visibility_*.json` como trazabilidad historica.
- Actualizar `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` cuando el apagado/pausa este ejecutado.
- Redirigir atencion operativa a los cuellos de Opus 2026-04-17: exact/range y position management.

Salida esperada:

- Phase5 queda archivado, no borrado.
- City Intelligence queda como dominio vivo y util, no como servicio separado.
- Menos ruido humano y mas foco en decisiones que mueven bankroll.

## Checkpoints Programados

| Fecha UTC | Aviso | Decision esperada |
| --- | --- | --- |
| 2026-04-24 | Confirmar que el summary del bridge salio y no hubo doble emisor | Mantener silencio o revertir si falta aviso real |
| 2026-04-28 | Checkpoint 5 dias de bridge | Pausar `phase5-visibility` si no aporto nada unico |
| 2026-05-01 | Checkpoint 72h post-pausa phase5 | Pausar `city-intelligence` separado si el bridge sigue ok |
| 2026-05-03 | Readiness de borrado legacy | Borrar servicios/volumenes legacy solo si la pausa no rompio funcionalidad |
| 2026-05-07 | Cierre de transformacion | Archivar docs phase5 y cerrar trazabilidad |

## Validacion

Antes de cualquier cambio live:

- `tools/railway_safe.ps1 status`
- `tools/railway_safe.ps1 service status -a --json`
- revisar variables por servicio antes de quitar `TELEGRAM_TOKEN`

Despues de cualquier cambio live:

- confirmar estado Railway;
- confirmar que Telegram sigue llegando desde el bridge;
- confirmar que no llegan alertas legacy;
- si hay cambio de repo, correr al menos sintaxis de los tools tocados;
- antes de push/deploy, correr `python verify_before_deploy.py`.
