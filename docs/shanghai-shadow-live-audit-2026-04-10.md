# Shanghai Shadow Live Audit

**Fecha:** 2026-04-10
**Alcance:** Railway live, read-only
**Servicios revisados:** `city-intelligence` y `polymarket-bot`

## Decision

El loop shadow de Shanghai **si esta generando huella en el bot principal**, pero `city-intelligence` **no la esta consumiendo**.

La lectura anterior de que Shanghai tenia `edge_evidence=0` era correcta solo dentro del volumen del servicio `city-intelligence`. No representa el runtime real del bot principal.

## Evidencia

### Servicio `city-intelligence`

- Estado Railway: `SUCCESS`
- Deployment: `80e70e0a-e64e-4ddf-b0fb-7d9c6db1c683`
- Ultimas corridas observadas:
  - `2026-04-10T00:00Z`
  - `2026-04-10T06:00Z`
  - resumen diario `2026-04-10T07:00Z`
- El volumen de `city-intelligence` contiene artefactos propios:
  - `city_intelligence_pipeline.json`
  - `city_validation_ledger.json`
  - `city_promotion_gate.json`
  - `city_probe_visibility_tracker.json`
  - `directional_trader_enrichment.json`
  - `reference_trader_city_market_cross.json`
  - `settlement_fidelity_probe.json`
- El volumen de `city-intelligence` **no contiene**:
  - `shadow_city_tracking.json`
  - `cycles_history.jsonl`
  - `audit.json`
- El ledger live apunta a esas rutas como inputs:
  - `/app/data/shadow_city_tracking.json`
  - `/app/data/audit.json`
- Como esos archivos no existen en ese volumen, `city_validation_ledger.py` cae a inputs opcionales vacios y todos los `edge_evidence` quedan a cero.
- En el ledger live de `city-intelligence` generado a `2026-04-10T06:00:38Z`, `Shanghai` ni siquiera aparece en `cities`.

### Servicio `polymarket-bot`

- Estado Railway: `SUCCESS`
- Deployment: `7c39c95e-a263-4a87-8774-f25fc66f9780`
- El volumen del bot principal si contiene:
  - `/app/data/shadow_city_tracking.json`
  - `/app/data/cycles_history.jsonl`
  - `/app/data/audit.json`
- Los tres estaban actualizados en la corrida de `2026-04-10T08:00Z`.

En `/app/data/shadow_city_tracking.json`, Shanghai tiene:

- `first_seen_at`: `2026-04-02T23:00:25.955698+00:00`
- `last_seen_at`: `2026-04-10T08:00:42.750952+00:00`
- `markets_seen`: `84`
- `edge_hits`: `19`
- `cycles_seen`: `30`
- `best_edge_pct`: `38.7`
- `best_ev`: `2.27`

En `/app/data/cycles_history.jsonl`, Shanghai aparece escaneada repetidamente. La corrida mas reciente revisada (`cycle_number=61`, `2026-04-10T08:00:42Z`) incluye Shanghai en `scanned_markets`, pero con:

- `with_edge=0`
- `selected=0`
- `shadow=0`
- `condition_filtered=25`

En `city_policy_state.json`, Shanghai figura en `auto_canary_cities`:

- `promoted_at`: `2026-04-06T12:33:22.569142+00:00`
- `reason`: `regla canary disparada: 19 edges shadow, 15 ciclos y pico 38.7%`
- `best_edge_pct`: `38.7`
- `shadow_edges`: `19`

## Hallazgo Critico

Shanghai no es un caso shadow puro en el runtime live del bot principal. El bot la autopromovio a `canary` el `2026-04-06T12:33Z`.

Por tanto hay dos realidades divergentes:

1. `city-intelligence` ve Shanghai como ausente o sin edge propio porque no tiene el volumen runtime del bot.
2. `polymarket-bot` si tiene huella acumulada de Shanghai y la policy live la trato como `canary`.

## Matiz Importante

Aunque los agregados por ciudad muestran `edge_hits=19`, el campo `directional_history` en `shadow_city_tracking.json` esta vacio.

Esto significa:

- hay huella operativa de edges y ciclos por ciudad;
- pero la capa persistente pensada para resolver señales direccionales contra NOAA no esta acumulando historial resoluble;
- por tanto `resolved_directional_count` seguiria siendo cero aunque `city-intelligence` leyera el archivo correcto, salvo que el ledger use los agregados por ciudad.

## Conclusion

El problema inmediato no es Austin, ni source fidelity, ni falta de discovery.

El problema real es de integracion/observabilidad entre servicios:

- `polymarket-bot` tiene datos runtime relevantes de Shanghai;
- `city-intelligence` genera decisiones estrategicas sin leer esos datos;
- ademas, el runtime live ya autopromovio Shanghai a `canary`, lo que contradice el marco analitico que la sigue tratando como `shadow`.

## Siguiente Paso Recomendado

No tocar `bot.py` ni trading core todavia.

El siguiente paso correcto es crear una mini-capa read-only de importacion/auditoria que compare:

- `city-intelligence` ledger/gate;
- `polymarket-bot` `shadow_city_tracking.json`;
- `polymarket-bot` `city_policy_state.json`;
- `polymarket-bot` `cycles_history.jsonl`.

Objetivo: que el proximo ledger no pueda decir que Shanghai tiene `edge_evidence=0` si el bot principal tiene `edge_hits=19`, `cycles_seen=30` y policy `auto_canary`.

## Instruccion Para Codex

Codex debe alinear `city-intelligence` con la evidencia runtime del bot principal antes de abrir Austin/Wuhan o cualquier onboarding nuevo.
