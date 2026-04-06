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
- Antes de push/deploy, correr `python verify_before_deploy.py`.

## Cierre

Si la sesion cambia estado, workflow o trazabilidad, alinear:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `agent_events.jsonl`

La memoria externa no sustituye la fuente de verdad del repo.
