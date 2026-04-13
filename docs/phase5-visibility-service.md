# Phase 5 Visibility Service

Servicio periodico separado del core del bot para ejecutar la pipeline read-only
de visibilidad de fase 5 en Railway.

## Objetivo

- acumular snapshots temporales sin depender de ejecuciones manuales;
- detectar coincidencias nuevas `Shanghai + Chicago`;
- disparar alerta Telegram one-shot cuando aparezca una coincidencia nueva;
- no tocar `bot.py`, scheduler ni trading core.

## Flujo

El servicio ejecuta en bucle:

1. `tools/phase5_visibility_pipeline.py`
2. esa pipeline refresca el probe si se pide
3. actualiza tracker, snapshot de Shanghai, benchmark de Chicago y comparador
4. ejecuta `tools/phase5_visibility_telegram_alert.py`

## Comando local

```powershell
python tools/phase5_visibility_service.py --once
```

## Servicio periodico local

```powershell
python tools/phase5_visibility_service.py --interval-minutes 180
```

## Variables esperadas

- `PHASE5_INTERVAL_MINUTES`
- `PHASE5_PROBE_LIMIT`
- `PHASE5_REFRESH_PROBE`
- `PHASE5_TARGETS`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

## Variables recomendadas en Railway

- `NIXPACKS_START_CMD=python -u tools/phase5_visibility_service.py`
- `PHASE5_INTERVAL_MINUTES=180`
- `PHASE5_PROBE_LIMIT=20`
- `PHASE5_REFRESH_PROBE=true`
- `PHASE5_TARGETS=Shanghai,Chicago`

## Persistencia

Para conservar evidencia y anti-spam entre reinicios, el servicio debe montar el
mismo volumen del proyecto en `/app/data`.

Artefactos clave:

- `data/city_probe_visibility_tracker.json`
- `data/phase5_visibility_pipeline.json`
- `data/phase5_visibility_alert_state.json`
- `docs/phase5_visibility_pipeline_latest.md`
- `docs/phase5_visibility_alert_latest.md`

## Guardrails

- servicio independiente del bot principal;
- sin compras/ventas ni cambios de policy;
- sin dependencia del scheduler del core;
- trazabilidad en `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`.
