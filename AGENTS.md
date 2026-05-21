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

## Cierre

Si la sesion cambia estado vivo, workflow o trazabilidad operacional, alinear:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `agent_events.jsonl`

Para docs-only o backlog sin estado vivo durable, no forzar `CONTEXTO.md`,
`HISTORIAL_SESIONES.md` ni `agent_events.jsonl`.

La memoria externa no sustituye la fuente de verdad del repo.
