# City Intelligence v2 — Strategic Design

> **Status**: Design only. No implementation in this commit.
> **Scope**: docs-only. No code, no env vars, no Railway, no BANKROLL, no Phase C, no city_mode changes.
> **Author of design**: Opus (Sesión 346, 2026-05-14).

---

## 1. Objetivo

Unificar bajo un único paraguas conceptual — *City Intelligence v2* — los tres ángulos que hoy o ya están parcialmente cubiertos o faltan:

1. **Descubrimiento**: detectar ciudades aún no observadas que muestran señal externa fuerte (traders, blocked_signals, shadow leak).
2. **Revisión de flujo**: avisar cuándo una ciudad ya observada merece revisión humana (transición de stage).
3. **Promoción / drift**: confirmar que canary → active está justificado y que active no degrada.
4. **Lectura diaria**: un solo Telegram LOG_ONLY que diga a Pablo dónde mirar.

La regla de oro de v2: **no crear un sistema paralelo**. Todo lo nuevo se integra como pieza de City Intelligence v2; nada compite con `city_lifecycle_review_monitor.py` ni con `city_promotion_gate.py`.

---

## 2. Arquitectura — dos productores + un consumidor

```
   ┌─────────────────────────────────┐         ┌──────────────────────────────────┐
   │  SourceOnboardingScanner        │         │  CityLifecycleReviewMonitor      │
   │  (NEW — Fase A)                 │         │  (EXISTING, untouched)           │
   │                                 │         │                                  │
   │  Universe: cities NOT in flow   │         │  Universe: cities IN flow        │
   │  Out: data/source_onboarding.json│        │  Out: data/city_lifecycle_review │
   └────────────────┬────────────────┘         └────────────────┬─────────────────┘
                    │                                            │
                    │       (handoff via override file —         │
                    │        Pablo edits manually)               │
                    │                                            │
                    └──────────────┬─────────────────────────────┘
                                   ▼
                    ┌──────────────────────────────────┐
                    │  CityIntelligenceDigest (NEW Fase B)
                    │  - Merges both JSON reports      │
                    │  - One unified Telegram daily    │
                    │  - One markdown for Pablo        │
                    └──────────────────────────────────┘

   ┌──────────────────────────────────┐
   │  CityPromotionGate (EXISTING)    │   feeds Lifecycle Monitor T2/T3 gates
   └──────────────────────────────────┘   (already wired)
```

Tres binarios físicos (Onboarding, Lifecycle, Digest), pero una sola jurisdicción intelectual: City Intelligence v2.

---

## 3. Diferencia entre Source Onboarding y Lifecycle Monitor

| Eje | Source Onboarding Scanner | Lifecycle Review Monitor |
|---|---|---|
| Universo | Ciudades **fuera** del flujo runtime | Ciudades **dentro** del flujo runtime |
| Pregunta | ¿Vale la pena empezar a observar? | ¿Esta ciudad ya observada cambia de stage? |
| Acción recomendada | Source audit manual → eventual `OBSERVED_AUDIT_CITIES` | Revisión humana → promoción/regresión |
| Entrada al runtime | NO. Solo escribe JSON/MD | NO. Solo escribe JSON/MD + Telegram |
| Riesgo si se equivoca | Pablo ignora la sugerencia | Pablo ignora la sugerencia |

---

## 4. Jurisdicción disjunta — regla canónica

Antes de cualquier scoring, **Source Onboarding excluye** del universo cualquier ciudad presente en:

```
ACTIVE_TRADING_CITIES
∪ CANARY_TRADING_CITIES
∪ OBSERVED_AUDIT_CITIES (overrides)
∪ auto_canary_cities
∪ auto_shadow_cities
∪ shadow_city_tracking.cities con cycles_seen >= MIN_SHADOW_CYCLES
∪ city_lifecycle_overrides.keys()
```

Sobre `BLOCKED_CITIES`:

- **Fase A** (v1.0): también se excluye `BLOCKED_CITIES` para mantener el scope pequeño.
- **Fase v1.1** (diferido): *blocked source re-audit* — re-evaluar si una ciudad blocked por fuente rota merece nueva fuente. Hoy queda fuera; sin esto, no podemos confundir "auditor de fuentes muertas" con "scanner de ciudades nuevas".

Esto garantiza que las dos herramientas no chocan: cada ciudad cae en una y solo una jurisdicción.

Defensa adicional: si el scanner detecta que una ciudad debería estar excluida pero llega al output (bug), debe emitir warning `JURISDICTION_LEAK` y excluirla del review queue. No crashea.

---

## 5. Inputs (read-only, todos por CLI)

El scanner **no asume** ninguna ruta concreta. Todas las rutas se aceptan por CLI con defaults locales (`data/runtime_import_derived/...`, `data/runtime_import/...`), pero conceptualmente debe ser capaz de apuntar a `/app/data` en runtime futuro sin cambios de código.

| Input | Path local default | Uso |
|---|---|---|
| signals crosscheck | `data/runtime_import_derived/signals_crosscheck.jsonl` | universo trader |
| blocked signals resolutions | `data/runtime_import_derived/blocked_signals_resolutions.jsonl` | WR/n por ciudad (gate de calidad) |
| shadow tracking | `data/runtime_import/shadow_city_tracking.json` | exclusión + shadow edge leak |
| policy env snapshot | `data/runtime_import/policy_env_snapshot.json` | ACTIVE / BLOCKED / CANARY / OBSERVED_AUDIT_CITIES |
| city policy state | `data/runtime_import/city_policy_state.json` | auto_canary / auto_shadow |
| lifecycle overrides | `data/city_lifecycle_overrides.json` | exclusión |
| RESOLUTION_ICAO | módulo Python (import) | feasibility de fuente NOAA |

`trade_lifecycle` y `observed_vs_forecast` se reservan para v1.1+ (no son necesarios para Fase A).

---

## 6. Estados v1 (Fase A)

Cuatro estados activos; el resto se difiere.

| Estado | Significado | Acción humana sugerida |
|---|---|---|
| `READY_FOR_SOURCE_AUDIT` | Señal trader/blocked fuerte + ICAO disponible + sin source risk evidente | Revisar fuente, lanzar source audit manual |
| `WAITING_EVIDENCE` | Aparece en señales pero muestra insuficiente o WR insuficiente | Re-check semanal |
| `RANGE_ONLY_NOT_OPERABLE` | Toda la señal está en condition=range → no operable bajo Phase 2 | Archivar |
| `SOURCE_BLOCKED` | RESOLUTION_ICAO no tiene station para la ciudad / proxy notoriamente roto | Archivar o pedir investigación |

Estados **no** emitidos en Fase A (reservados para v1.1+): `READY_FOR_OBSERVED_AUDIT_REVIEW`, `SOURCE_UNVERIFIED`, `ALREADY_OBSERVED` (este último solo como warning de leak), `BLOCKED_SOURCE_RE_AUDIT`.

### Matiz importante — degraded vs SOURCE_BLOCKED

`SOURCE_BLOCKED` significa **"la fuente para esta ciudad está rota o no existe"** (information about the city). Si lo que falla es la **carga del módulo RESOLUTION_ICAO** (information about the scanner itself), el scanner NO debe marcar todas las ciudades como `SOURCE_BLOCKED` — eso confundiría un fallo de herramienta con un fallo de fuente.

Política correcta cuando falla la carga de `RESOLUTION_ICAO`:

- emitir warning crítico `RESOLUTION_ICAO_UNAVAILABLE`;
- marcar payload con `degraded: true` y `source_feasibility: "unknown"`;
- cada ciudad evaluable cae a `WAITING_EVIDENCE` (no `SOURCE_BLOCKED`);
- el report queda inutilizable para acciones, pero no miente sobre fuentes.

---

## 7. Scoring y priorización

Un solo `priority_score` numérico decide el orden de la review queue:

```
priority_score =
    1.5 * trader_consensus_strength      # 0..1 (fracción de fuentes que coinciden)
  + 1.0 * blocked_signals_wr_excess      # max(0, WR - 0.55) * 2, capped 1
  + 1.0 * shadow_edge_leak               # 1 si shadow_tracking muestra edge_hit cond_filtered
  + 0.5 * trader_only_persistence        # n días seguidos solo en señal trader, capped 1
  - 0.8 * range_only_fraction            # penaliza cuando >RANGE_ONLY_THRESHOLD señales son range
  - 1.0 * source_risk_flag               # ICAO ausente / proxy notoriamente sospechoso
  - 0.5 * no_local_station               # station_id ausente en RESOLUTION_ICAO
```

### Umbrales v1 (constantes top-level, ajustables sin redeploy)

| Constante | Valor v1 | Significado |
|---|---:|---|
| `SCORE_READY` | 1.5 | ≥ → `READY_FOR_SOURCE_AUDIT` |
| `SCORE_WAITING` | 0.5 | ≥ → `WAITING_EVIDENCE` (debajo: queda fuera del review queue) |
| `MIN_BLOCKED_N` | 20 | Mínimo n para que blocked_signals cuente |
| `MIN_TRADER_SOURCES` | 2 | Mínimo fuentes para que consenso cuente |
| `MIN_TRADER_DAYS` | 3 | Mínimo días seguidos para persistencia |
| `MIN_SHADOW_CYCLES` | 10 | Mínimo cycles_seen para shadow leak |
| `RANGE_ONLY_THRESHOLD` | 0.7 | Fracción ≥ → flag `RANGE_ONLY_NOT_OPERABLE` |

### Sample mínimo (anti-ruido)

- Blocked signals WR solo cuenta si `n >= MIN_BLOCKED_N` y `bot_evaluation` está poblada — lección de A7 audit (2026-05-07).
- Trader consensus solo cuenta si `fuentes >= MIN_TRADER_SOURCES` y `días >= MIN_TRADER_DAYS`.
- Shadow leak solo cuenta si `cycles_seen >= MIN_SHADOW_CYCLES`.

Si un componente no cumple su sample mínimo, su contribución al score es 0 — no rompe los demás componentes.

---

## 8. Conexión con Lifecycle Review Monitor

Handoff vía archivo, no vía import:

1. Scanner escribe `data/source_onboarding.json` y `docs/source_onboarding_latest.md`.
2. Pablo decide manualmente; si aprueba, añade entrada a `data/city_lifecycle_overrides.json` y/o a `OBSERVED_AUDIT_CITIES`.
3. En el siguiente run, **Lifecycle Monitor** recoge la ciudad automáticamente (su universo incluye `overrides.keys()`).
4. Scanner deja de listarla porque pasa al set de exclusión.

Las dos herramientas no se importan ni se invocan mutuamente. Acoplamiento mínimo, reversible.

---

## 9. Telegram diario (formato propuesto para Fase B)

```
🏙 City Intelligence Digest — YYYY-MM-DD (LOG_ONLY)

▶ Review Queue (action recommended)
  • Los Angeles — manual_review_pending (override active, n=12, WR=72%)
  • Houston — canary_review (T2 pass, gate=observe_runtime_canary)

▶ Onboarding Candidates (NEW — no action authorized)
  • Lucknow — READY_FOR_SOURCE_AUDIT (score=2.1, ICAO=VILK, traders=3/4, blocked WR=64% n=22)
  • Karachi — WAITING_EVIDENCE (score=0.8, n=14 insufficient)

▶ Quiet
  3 cities WAITING_EVIDENCE, 7 cities below score floor

⚠ Nothing here authorizes trading, env changes, or policy edits.
```

Cooldown: si una ciudad apareció ayer con estado idéntico, no repetir alerta. Mismo patrón que el Lifecycle Monitor.

---

## 10. Prohibiciones explícitas

City Intelligence v2 — y en particular Source Onboarding — **nunca** debe:

- ❌ Emitir BUY / SELL / SKIP
- ❌ Modificar env vars
- ❌ Cambiar city modes (active / canary / shadow / blocked)
- ❌ Escribir en `auto_canary_cities`, `auto_shadow_cities`, whitelist
- ❌ Tocar BANKROLL o Fase C
- ❌ Aplicar Phase 2 / range gating real (solo *informa* si una señal es range-only)
- ❌ Llamar a Railway, DB o `/app/data` en producción
- ❌ Convertir blocked_signals o trader signals en algo ejecutable
- ❌ Auto-promover ciudades a `OBSERVED_AUDIT_CITIES` (siempre vía edición manual de Pablo)
- ❌ Bypass del Lifecycle Monitor — si una ciudad ya está en su jurisdicción, Scanner la ignora
- ❌ Crear sistema paralelo: todo binario nuevo se documenta como pieza de City Intelligence v2

---

## 11. Fase A — implementable por Sonnet (alcance v1.0)

1. `tools/source_onboarding_scanner.py` — read-only, mismo patrón I/O que `city_lifecycle_review_monitor.py`.
2. Inputs por CLI (con defaults locales). Sin dependencia conceptual de `runtime_import_derived` — los paths se inyectan.
3. Filtro de jurisdicción **antes** del scoring (incluye BLOCKED en Fase A — re-audit diferido a v1.1).
4. Solo cuatro estados activos: `READY_FOR_SOURCE_AUDIT`, `WAITING_EVIDENCE`, `RANGE_ONLY_NOT_OPERABLE`, `SOURCE_BLOCKED`.
5. Scoring con constantes top-level (ver §7).
6. Si falla la carga de RESOLUTION_ICAO: warning `degraded`, ciudades a `WAITING_EVIDENCE`, NUNCA a `SOURCE_BLOCKED`.
7. Outputs: `data/source_onboarding.json` + `docs/source_onboarding_latest.md`.
8. Tests focales (3–5): jurisdicción no se solapa, range-only excluido, ciudad sin ICAO → `SOURCE_BLOCKED`, fallo de RESOLUTION_ICAO → `degraded` (no `SOURCE_BLOCKED`), sample mínimo respetado.
9. NO modificar `city_lifecycle_review_monitor.py`.
10. NO añadir al scheduler ni a Railway en Fase A — correr manualmente durante varias semanas antes de automatizar.

---

## 12. Fase B — Digest unificado

1. `tools/city_intelligence_digest.py` (~100 LOC).
2. Lee `city_lifecycle_review.json` + `source_onboarding.json`.
3. Aplica cooldown (reusa lógica del Lifecycle Monitor).
4. Emite **un** Telegram LOG_ONLY diario con ambas secciones.
5. Escribe **un** markdown `docs/city_intelligence_digest_latest.md`.

Sin Fase B, ambos productores quedan como reportes manuales sin Telegram unificado — funcional, pero sin la lectura diaria que pidió Pablo. Fase B es desbloqueable después de validar Fase A.

---

## 13. Diferido a v1.1+ (no implementar en Fase A)

- `READY_FOR_OBSERVED_AUDIT_REVIEW` y `SOURCE_UNVERIFIED` (requieren ingest de un repo de "source audits ya realizados").
- `BLOCKED_SOURCE_RE_AUDIT` — re-evaluar fuentes rotas.
- Tuning de pesos del score basado en datos reales.
- Integración con scheduler Railway.
- Lectura de `trade_lifecycle` / `observed_vs_forecast` para enriquecer scoring.

---

## 14. Prompt de implementación para Sonnet (Fase A)

> Pegar este prompt tal cual cuando Pablo autorice la implementación.

```
Modo: implementación read-only LOG_ONLY. Sin runtime, sin Railway, sin BANKROLL.

Tarea:
Implementar `tools/source_onboarding_scanner.py` v1.0 siguiendo el diseño en
docs/city_intelligence_v2_design.md (§11 Fase A).

Patrón de referencia obligatorio: `tools/city_lifecycle_review_monitor.py`.
Reusar la misma estructura: parse_args, _load_json_optional, load_inputs (con
warnings/critical), build_records, render_markdown, main.

Inputs (todos por CLI, sin asumir paths fijos):
  --signals-crosscheck   default: data/runtime_import_derived/signals_crosscheck.jsonl
  --blocked-resolutions  default: data/runtime_import_derived/blocked_signals_resolutions.jsonl
  --shadow-tracking      default: data/runtime_import/shadow_city_tracking.json
  --policy-env           default: data/runtime_import/policy_env_snapshot.json
  --policy-state         default: data/runtime_import/city_policy_state.json
  --overrides            default: data/city_lifecycle_overrides.json
  --json-output          default: data/source_onboarding.json
  --md-output            default: docs/source_onboarding_latest.md

Reglas no negociables:
1. LOG_ONLY disclaimer en JSON y MD, idéntico estilo a Lifecycle Monitor.
2. Filtro de jurisdicción ANTES de scoring: excluir ACTIVE / CANARY / BLOCKED /
   OBSERVED_AUDIT (override) / auto_canary / auto_shadow / shadow_tracking con
   cycles_seen >= MIN_SHADOW_CYCLES / overrides.keys(). Las excluidas no
   aparecen en el reporte. Si por bug aparecen, warning `JURISDICTION_LEAK`.
3. Constantes top-level: MIN_BLOCKED_N=20, MIN_TRADER_SOURCES=2,
   MIN_TRADER_DAYS=3, MIN_SHADOW_CYCLES=10, SCORE_READY=1.5,
   SCORE_WAITING=0.5, RANGE_ONLY_THRESHOLD=0.7.
4. Estados Fase A: READY_FOR_SOURCE_AUDIT, WAITING_EVIDENCE,
   RANGE_ONLY_NOT_OPERABLE, SOURCE_BLOCKED. No emitir otros.
5. RESOLUTION_ICAO: import desde el módulo Python existente (grep para
   localizarlo). Si import o lookup falla a nivel módulo: warning
   `RESOLUTION_ICAO_UNAVAILABLE`, payload con `degraded: true`,
   `source_feasibility: "unknown"`, ciudades evaluables caen a
   WAITING_EVIDENCE — NUNCA a SOURCE_BLOCKED por fallo de herramienta.
6. SOURCE_BLOCKED solo cuando la ciudad concreta no tiene station/ICAO en
   un RESOLUTION_ICAO que sí cargó correctamente.
7. Sample mínimo aplicado por componente del score: si no cumple, ese
   componente vale 0, no rompe el resto.
8. Tests focales en tests/ siguiendo patrón existente:
   - jurisdicción no se solapa con Lifecycle Monitor
   - range-only se clasifica como RANGE_ONLY_NOT_OPERABLE
   - ciudad sin ICAO en RESOLUTION_ICAO cargado → SOURCE_BLOCKED
   - fallo de carga RESOLUTION_ICAO → degraded + WAITING_EVIDENCE (no SOURCE_BLOCKED)
   - sample mínimo blocked respetado (n<20 no aporta al score)

Prohibido:
- import requests / urllib / cualquier red.
- import del módulo de trading, scheduler, telegram, bankroll.
- Lectura de /app/data o Railway.
- Auto-emisión de Telegram (eso es Fase B).
- BUY / SELL / SKIP, env vars, policy mutations.
- Crear sistema paralelo: el tool se documenta como pieza de City Intelligence v2.

Entrega:
- tools/source_onboarding_scanner.py
- tests/test_source_onboarding_scanner.py (3-5 tests focales)
- docs/source_onboarding_design.md (≤ 1 página, link a city_intelligence_v2_design.md)
- NO modificar city_lifecycle_review_monitor.py.
- NO añadir al scheduler ni a Railway.

Cierre LITE.
```

---

## 15. Resumen

- City Intelligence v2 = paraguas, no monolito. Dos productores (Onboarding + Lifecycle), un consumidor (Digest).
- Jurisdicción disjunta por construcción evita el riesgo principal: dos sistemas peleando por la misma ciudad.
- Handoff vía archivo de override, no vía import. Desacoplado y reversible.
- Source Onboarding solo escala a OBSERVED_AUDIT, jamás a canary directo (lección LA).
- Sample mínimos (n≥20, fuentes≥2, cycles≥10) heredados de A7 audit para evitar falsos positivos.
- Fallo de tooling (RESOLUTION_ICAO no carga) ≠ fallo de fuente — distinción crítica.
- Fase A es ~250 LOC, implementable por Sonnet en una sesión sin tocar nada vivo.
- BLOCKED re-audit diferido a v1.1 para mantener Fase A pequeña.
