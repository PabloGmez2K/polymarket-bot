# Sonnet review - post-V2 cleanup P6+P7

Fecha: 2026-04-25
Autor del paquete: Codex
Scope: revision read-only antes de seguir

## Instruccion para Sonnet

Lee `AGENTS.md`, el bloque superior reciente de `CONTEXTO.md`, esta nota y `docs/min-edge-per-city-analysis-2026-04-25.md`.

Revisa la limpieza post-V2 cutover P6+P7 ejecutada por Codex:

1. Validar que la precondicion V2 fue suficiente: logs recientes de Railway sin errores recurrentes en `create_or_derive_api_key`, `get_open_orders`, auth endpoints ni CLOB.
2. Auditar P6: Seoul en `shadow_city_tracking.json` fue reducido a evidencia post-fix de estacion, con backup local y remoto.
3. Auditar P7: el analisis `MIN_EDGE` por ciudad concluye que no hay ciudad elegible para `MIN_EDGE_PER_CITY` porque ninguna cumple `n_closed>=10`, `WR>=70%` y `PnL>0`.
4. Confirmar si hay algun riesgo, omision o follow-up antes de continuar.

No modificar `bot.py`, trading core, NOAA, scheduler, Kelly, sigma, sizing, filtros ni Railway env vars.

## Evidencia que debe revisar

- `CONTEXTO.md` sesion 239.
- `HISTORIAL_SESIONES.md` sesion 239.
- `agent_events.jsonl` evento sesion 239.
- `docs/min-edge-per-city-analysis-2026-04-25.md`.
- Si necesita comprobar datos locales:
  - `data/runtime_import/shadow_city_tracking.json`
  - `data/runtime_import/shadow_city_tracking.json.bak-pre-p6`
  - `data/runtime_import/trade_lifecycle.json`
  - `data/runtime_import/skip_log.jsonl`
  - `data/runtime_import/city_policy_state.json`

## Resultado P6 a validar

Seoul antes del reset:

- `markets_seen=207`
- `edge_hits=5`
- `cycles_seen=91`
- `best_edge_pct=68.5`

Seoul despues del reset:

- `first_seen_at=2026-04-17T12:22:40.235413+00:00`
- `markets_seen=54`
- `edge_hits=2`
- `cycles_seen=28`
- `best_edge_pct=26.4`

La unica senal direccional durable restante para Seoul debe ser:

- `Seoul|2026-04-18|YES|at_or_above|21`
- `times_seen=2`
- `first_seen_at=2026-04-17T12:22:40.235413+00:00`
- `last_seen_at=2026-04-17T16:00:40.495025+00:00`

Backup esperado:

- Local: `data/runtime_import/shadow_city_tracking.json.bak-pre-p6`
- Railway: `/app/data/shadow_city_tracking.json.bak-pre-p6`

## Resultado P7 a validar

El analisis concluye:

- No aplicar `MIN_EDGE_PER_CITY` todavia.
- Ninguna ciudad cumple simultaneamente:
  - `n_closed >= 10`
  - `WR >= 70%`
  - `PnL > 0`
- Tokyo es solo candidata observacional: `n=5`, `WR=80%`, `PnL=+$3.53`.
- La propuesta futura de env var debe quedar como diseno, no accion:
  - `MIN_EDGE_PER_CITY={"Tokyo":22.5,"Shanghai":24.0}`

## Preguntas concretas para Sonnet

1. Esta bien elegido el corte P6 en `2026-04-17T12:00Z` / primera evidencia `2026-04-17T12:22:40Z`, o deberia haberse usado otro punto post-fix?
2. El reset P6 deja algun riesgo por conservar `city_policy_state.auto_canary_cities.Seoul.reason` con texto legacy (`5 edges`, `65 ciclos`, `68.5%`) aunque el tracker ya este limpio?
3. La metodologia P7 para proponer `MIN_EDGE` por ciudad es suficientemente conservadora?
4. Hay alguna accion necesaria antes de seguir, o basta con observar hasta nueva muestra?

## Formato esperado de respuesta

Responder con:

- `Aprobado` o `Bloqueado`.
- Findings ordenados por severidad, con archivo/dato afectado.
- Recomendacion final:
  - seguir sin cambios,
  - ajustar docs/trazabilidad,
  - repetir P6 con otro corte,
  - o escalar a Opus.

No implementar cambios salvo que Pablo lo pida despues.
