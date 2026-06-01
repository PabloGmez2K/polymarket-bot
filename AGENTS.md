# AGENTS.md

Capa canonica y corta para Codex en este repo.

## Leer primero

1. `AGENTS.md`
2. bloque relevante de `CONTEXTO.md`
3. `OPERATIONS_PLAYBOOK.md` solo si la tarea toca workflow, cierre, deploy, Railway o scoreboard

No cargar `CONTEXTO.md` completo ni sesiones antiguas sin necesidad.

## Default

- `model_reasoning_effort = "medium"` por defecto
- subir profundidad solo con perfiles `low`, `deep` o `max`
- preferir trabajo por fases y subproblemas acotados

## Codex Operating Pattern

- Para cambios importantes: primero `ASK` / read-only con mapa, plan, riesgos, archivos candidatos, validación y criterio de parada; luego `CODE` solo si el scope queda claro.
- Tratar prompts como issues/PRs: objetivo, contexto mínimo, rutas, patrón existente, guardrails, validación y entrega.
- `Best-of-N` solo para comparar planes, prompts o alternativas de diseño con coste justificado; no para multiplicar implementaciones, Railway checks ni análisis `WATCH_ONLY`.
- La cola/backlog de Codex requiere trigger, ROI esperado y criterio de cierre; evitar cementerios `WATCH`.
- Codex implementa, testea y valida; no decide semántica de trading/riesgo: BANKROLL, sizing, whitelist, city modes, scheduler, BUY/SELL/SKIP, guards/SL, source promotion y Fase C requieren Opus o confirmación humana según modo.
- `/plan` es apropiado para arquitectura LOG_ONLY o pre-implementation cuando Opus ya fijó semántica; no autoriza CODE. `/goal` solo para implementación iterativa ya autorizada, con objetivo verificable y stop condition; nunca para decisiones de trading/riesgo/BANKROLL/city modes/guards/Fase C/env vars. Para patches runtime concretos ya decididos, usar prompt normal cerrado.

## Modos de ciudad — regla canónica

Cuatro modos exclusivos y ordenados por prioridad (el primero que aplica gana):

| Modo | Cómo se activa | Tradea | Observa NOAA |
|------|---------------|:------:|:------------:|
| `blocked` | `BLOCKED_CITIES` o `auto_blocked_cities` | ❌ | ❌ |
| `shadow` | **default** (no está en ninguna lista) | ❌ | ✅ |
| `canary` | `CANARY_TRADING_CITIES` o `auto_canary_cities` | ✅ pequeño | ✅ |
| `active` | `ACTIVE_TRADING_CITIES` | ✅ | ✅ |

**Regla de oro:**
- "No quiero operar esta ciudad" → **no la pongas en `ACTIVE_TRADING_CITIES`** (queda shadow).
- "Esta ciudad tiene la fuente de datos rota" → **ponla en `BLOCKED_CITIES`**.
- Nunca usar `BLOCKED_CITIES` como sustituto de "pausa operativa". Shadow es la pausa correcta.

`OBSERVED_AUDIT_CITIES` + `noaa_station_id` en `RESOLUTION_ICAO` son requisitos adicionales
para que una ciudad shadow/active acumule datos en `observed_vs_forecast`.

## Guardrails

- No tocar trading, NOAA, scheduler, reglas de entrada/salida ni arquitectura core salvo pedido explicito.
- Primero evidencia, luego copy o refactor.
- Preferir `rg` y lecturas puntuales.
- Para Railway, usar `tools/railway_safe.ps1`.
- Antes de push/deploy con cambios de codigo, correr `python verify_before_deploy.py`.
- En docs-only/backlog/cierres sin codigo, usar cierre LITE: `git diff --check`, commit/push si procede y Railway check breve si hubo push; no ejecutar verify completo ni session-close-sync completo salvo necesidad real.
- `identity_available` ≠ `joined_evidence` ≠ `temporally_aligned` ≠ `outcome_resolved`. No elevar `CONFIRMED_MISSED_OPPORTUNITY` sin identidad, temporalidad, ejecutabilidad, outcome, fidelity y contrafactual verificados.
- Artefacto nuevo de inteligencia: definir consumer y outcome path desde el diseño, no como afterthought.
- Tooling LOG_ONLY en hot path: aplicar dedup/cap/sampling antes del compute caro (ver COMPUTE_CAP_BUG sesión 381).
- Tests deben medir llamadas reales al compute/hook, no solo filas escritas en el artefacto.
- En sesiones de código: consolidar docs y `agent_events.jsonl` antes del último `verify_before_deploy.py` cuando el contrato del repo lo requiera.
- La memoria externa (Engram) no sustituye la fuente de verdad del repo; toda decisión durable debe quedar en `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`.
- Si se añade entrada a `agent_events.jsonl`, usar timestamp obtenido del sistema en UTC; no inventarlo. En docs-only, no acceder a Railway para registrar eventos.
- Fuente canónica de fills R1 = API CLOB `get_trades(order_id)` cuando existe `order_id`. `trades.log` es log humano sin `order_id`: **prohibido construir parser canónico de fills sobre `trades.log`**. `performance.json`/`postmortem.json`/`trade_lifecycle.json` son contexto/cross-check, no fuente canónica de fill. Ver `docs/learning_data_contract.md` §3.
- Verificar env vars con filtrado selectivo; no listar `railway variables` completo ni pegar secretos en chat, prompts o docs.

## Cierre

Si la sesion cambia estado vivo, workflow o trazabilidad operacional, alinear:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `agent_events.jsonl`

Para docs-only o backlog sin estado vivo durable, no forzar `CONTEXTO.md`,
`HISTORIAL_SESIONES.md` ni `agent_events.jsonl`.

La memoria externa no sustituye la fuente de verdad del repo.
