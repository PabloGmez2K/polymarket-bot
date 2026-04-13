# City Intelligence Railway Services

Servicios Railway separados del core del bot para ejecutar la capa de mejora
continua de `city intelligence`.

## Objetivo

- mantener el pipeline de city intelligence corriendo sin depender de sesiones manuales;
- detectar cambios importantes durante el dia;
- enviar un resumen diario a las `07:00 UTC`;
- no tocar `bot.py`, scheduler ni trading core.

## Servicio recomendado

### `city-intelligence`

Servicio principal unificado.

Funcion:

- ejecutar `tools/city_intelligence_pipeline.py`;
- refrescar ledger, gate y alertas;
- mantener foco en el cuello de botella dominante;
- enviar alertas intradia solo cuando cambie algo importante;
- enviar el resumen diario a las `07:00 UTC` usando el mismo volumen/estado.
- bootstrapear el censo automaticamente en la primera corrida si el volumen
  todavia no tiene `data/directional_trader_census.json`.

Comando recomendado:

```text
python -u tools/city_intelligence_railway_service.py
```

Variables recomendadas:

- `RAILPACK_START_CMD=python -u tools/city_intelligence_railway_service.py`
- `CITY_INTELLIGENCE_ALIGN_UTC_HOURS=0,6,12,18`
- `CITY_INTELLIGENCE_DAILY_HOUR_UTC=7`
- `CITY_INTELLIGENCE_PROBE_LIMIT=12`
- `CITY_INTELLIGENCE_CENSUS_MARKETS=200`
- `CITY_INTELLIGENCE_EXPLORATORY_TARGETS=Chicago`
- `CITY_INTELLIGENCE_REFRESH_PROBE=true`
- `CITY_INTELLIGENCE_REFRESH_CENSUS=false`
- `TELEGRAM_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

Las `runtime_derived_targets` salen de `data/runtime_policy_effective_view.json`; la lista exploratoria solo debe contener extras fuera del runtime efectivo.

Notas:

- si quieres discovery mas agresivo, sube `CITY_INTELLIGENCE_REFRESH_CENSUS=true`;
- mientras la señal sea fragil, es mejor mantener `refresh-census` desactivado por default y activarlo manualmente o tras validar coste/ruido.

Notas:

- este modo unificado es el recomendado en Railway porque evita problemas de estado compartido entre servicios;
- el resumen diario lee los artefactos del mismo volumen que actualiza el pipeline intradia.

## Persistencia

El servicio debe montar un volumen dedicado en `/app/data`.

Artefactos clave:

- `data/city_validation_ledger.json`
- `data/city_promotion_gate.json`
- `data/city_intelligence_pipeline.json`
- `data/city_intelligence_alert_state.json`
- `data/city_intelligence_daily_summary_state.json`
- `docs/city_validation_ledger_latest.md`
- `docs/city_promotion_gate_latest.md`
- `docs/city_intelligence_pipeline_latest.md`
- `docs/city_intelligence_daily_summary_latest.md`

## Semantica de outputs

Las alertas y el resumen diario no estan pensados para que tu "revises manualmente",
sino para que puedas abrir una sesion nueva de Codex con la instruccion correcta.

Cada mensaje debe responder:

1. que paso;
2. por que importa;
3. si estamos mas cerca o no de monetizar `bot.py`;
4. cual es el cuello de botella dominante;
5. cual es la `Instruccion para Codex`.

## Uso local rapido

Pipeline una sola vez:

```powershell
python tools/city_intelligence_service.py --once
```

Resumen diario una sola vez:

```powershell
python tools/city_intelligence_daily_service.py --once
```

Modo Railway unificado una sola vez:

```powershell
python tools/city_intelligence_railway_service.py --once
```

## Guardrails

- servicios separados del bot principal;
- sin compras/ventas ni cambios automaticos de policy;
- sin dependencia del scheduler del core;
- con trazabilidad documental para futuras revisiones de Codex y Opus.
