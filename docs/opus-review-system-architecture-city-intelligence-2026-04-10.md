# Opus Review: System Architecture city-intelligence

**Fecha:** 2026-04-10  
**Veredicto:** `GO WITH CHANGES`  
**Documento revisado:** `docs/system-architecture-city-intelligence-2026-04-10.md`

## Resumen

Opus valida la direccion general:

- `polymarket-bot` debe ser la fuente de verdad runtime;
- `city-intelligence` debe recomendar, no actuar;
- no hay que tocar `bot.py` ni trading core para corregir el mapa.

Pero rechaza congelar el documento como canonico operativo sin cambios, porque encontro deuda concreta en el codigo actual.

## Hallazgos Criticos

1. `city-intelligence` no esta desacoplado de `bot.py`.
   `tools/city_validation_ledger.py` hace `import bot` y consume constantes runtime. Eso convierte cambios futuros en `bot.py` en cambios implicitos del ledger.

2. El bug de Shanghai es plumbing antes que semantica.
   Cuando faltan `shadow_city_tracking.json` o `audit.json`, el ledger usa `required=False`, recibe `None`, transforma la ausencia en ceros y descarta `available=False`.

3. `policy_mode` no viene de runtime.
   El ledger hereda `policy_mode` desde `reference_trader_city_market_cross.json`; no lee `city_policy_state.json`.

4. Shanghai puede no aparecer en el ledger.
   El ledger itera solo `cross.city_rows`; ciudades que existan solo en runtime pueden omitirse en silencio.

5. Los drift detectors propuestos no estan cableados.
   `runtime_inputs_status`, `drift_flags`, `audit_runtime_drift` y estados relacionados son especificacion futura, no comportamiento actual.

## Correcciones Arquitectonicas A Incorporar

- Declarar `import bot` como deuda arquitectonica.
- Exigir fail-closed cuando falten inputs runtime.
- Propagar `runtime_inputs_status=missing` al ledger, gate y alertas.
- Separar `cross_policy_mode`, `analytics_policy_mode` y `runtime_policy_mode`.
- Decidir si el ledger iterara `cross ∪ runtime`; recomendacion: si, pero no como primer cambio.
- Tratar Shanghai como auditoria posterior a canary, no como candidata pendiente de promocion.
- Reconocer que `edge_hits=19` justifica exploracion canary barata, pero no validacion observada.
- Considerar backfill analitico desde `cycles_history.jsonl` + `audit.observed_vs_forecast` como unica ruta a historial resoluble sin tocar `bot.py`.

## Recomendacion De Primer Cambio

Sin tocar `bot.py`, hacer que `city_validation_ledger.py` falle cerrado cuando falten artefactos runtime:

- detectar ausencia de `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`;
- emitir `summary.runtime_inputs_status=missing`;
- evitar filas con ceros mudos;
- hacer que `city_promotion_gate.py` emita `gate_status=runtime_inputs_missing`;
- hacer que alertas digan que `city-intelligence` no puede concluir sobre runtime.

Despues de eso, decidir transporte runtime. Opus recomienda volumen compartido read-only entre `polymarket-bot` y `city-intelligence` si Railway lo permite.

## Phase5

Mantener por ahora:

- `city_probe_visibility_tracker.py`;
- patron one-shot anti-spam de `phase5_visibility_telegram_alert.py`;
- docs y artefactos historicos `phase5-*`;
- `seed_data/phase5/*`.

Marcar como legacy/no periodico:

- `shanghai_shadow_test.py`;
- `chicago_active_benchmark.py`;
- `shanghai_vs_chicago_comparator.py`.

No apagar `phase5-visibility` hasta verificar que queda un solo escritor vivo del tracker y que `city-intelligence` reproduce la alerta one-shot `Shanghai + Chicago`.

## No Implementar Todavia

- No tocar `bot.py`.
- No escribir `city_policy_state.json` desde `city-intelligence`.
- No crear exporter en `polymarket-bot` antes de confirmar volumen compartido.
- No implementar todos los drift detectors antes de `runtime_inputs_status`.
- No apagar `phase5-visibility` todavia.
- No generalizar comparadores Shanghai/Chicago todavia.
- No integrar Weather Underground como feed automatico.

