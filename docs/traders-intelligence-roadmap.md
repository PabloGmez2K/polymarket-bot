# Traders Intelligence — Roadmap V1 → V1.1 → V1.2 → recomendaciones

**Status:** `ROADMAP_DOCUMENTED / NOT_IMPLEMENTED`
**Prepared:** 2026-05-08 (Opus design)
**Basis:** `docs/traders-intelligence-spec.md` (v0), `docs/traders-intelligence-v1-snapshots.md`, `docs/traders-intelligence-v1-activation-package.md`, commit `0b262e1` (V1 observational active).

Documento durable que persiste el diseño estratégico de evolución de Traders
Intelligence desde la V1 manual observacional actual hacia una herramienta
automatizada de aprendizaje operativo. **No autoriza implementación.** Cada
fase requiere gates explícitos y, donde corresponde, revisión Opus separada.

Principio rector: `data → evidencia → interpretación → recomendación →
decisión controlada`. Sin saltos.

---

## 1. Marco general

| Versión | Función | Telegram | Toca runtime |
|---|---|---|---|
| V1 (hoy) | Snapshot manual filtrado, lifecycle pseudo | Daily summary read-only | No |
| V1.1 | Collector automático, cooldown, kill switch, métricas | Andon de cadencia/salud | No |
| V1.2 | Evidence scoreboard por trader/city, cruce con outcomes | Andon `WAITING_EVIDENCE → REVIEW_READY` | No |
| V1.3 (futuro) | Recomendaciones humanas (priorizar ciudades, revisión manual) | Andon `REVIEW_READY` accionable manual | No |
| V2 (no diseñar aún) | Posible input a gates/sizing | Requiere Opus + revisión separada | Sí (fuera de scope) |

Cada versión sólo abre cuando los gates de la anterior están cerrados con
evidencia trazable.

---

## 2. V1.1 — Collector automático (LOG_ONLY)

### 2.1 Forma
Wrapper sobre `tools/traders_intelligence_snapshot.py` actual. **No** reescribir
el snapshot tool; reutilizar.

### 2.2 Cuándo corre
- Cadencia: cada 60 minutos vía scheduler **existente** del bot. No scheduler
  nuevo. Ventana operativa: 24/7 mientras `signals.json` se refresque.
- Trigger manual: `--run-id` ya existe.
- Cooldown: mínimo 30 min entre runs.

### 2.3 Inputs
- `data/runtime_import/signals.json` (existente).
- Estado persistente: `data/traders_intelligence/collector_state.json`
  (`last_run_id`, `last_snapshot_at`, `last_signals_generated_at`,
  `consecutive_failures`, `kill_switch_active`).

### 2.4 Outputs
Sin cambios de schema vs V1:
- `data/traders_intelligence/snapshots/<run_id>.json`
- `data/traders_intelligence/reports/<run_id>.json`
- `data/traders_intelligence/pseudo_lifecycle_runs.jsonl` (append idempotente).

Adicional V1.1:
- `data/traders_intelligence/collector_state.json`.
- `agent_events.jsonl` event tipo `traders_intelligence_collector_run` con
  `{run_id, n_signals, status_counts, dry_run, ok}`.

### 2.5 Idempotencia
- Skip si `signals.json.generated == last_signals_generated_at` (no hubo refresh).
- Skip si `now - last_snapshot_at < cooldown`.
- `run_id` derivado de `snapshot_at` (ya implementado).

### 2.6 Kill switch
- Env var `TRADERS_INTELLIGENCE_COLLECTOR=OFF` → no ejecuta.
- Default **OFF** hasta gate V1→V1.1 cerrado.
- Auto-disable: si `consecutive_failures >= 5` el collector marca
  `kill_switch_active=true` en state, deja de correr y emite Andon.

### 2.7 Métricas mínimas
- `runs_24h`, `signals_seen_24h`, `traders_seen_24h`, `cities_seen_24h`.
- `appeared_24h`, `disappeared_apparent_24h`, `still_present_24h`,
  `reappeared_24h`.
- `last_run_age_minutes`, `signals_freshness_minutes`.
- `consecutive_failures`, `kill_switch_active`.

### 2.8 Lo que **no** hace V1.1
- No cruza con outcomes ni con `trade_lifecycle`.
- No agrega por trader/city más allá del lifecycle pseudo actual.
- No emite recomendaciones.
- No toca BUY/SELL/SKIP, `blocked_signals`, ni `promotion_gate`.

---

## 3. V1.2 — Evidence Scoreboard

### 3.1 Forma
Tool read-only nuevo (`tools/traders_intelligence_scoreboard.py`) que **lee**
snapshots de V1.1 + `bot_outcomes.csv` (canónico) y produce agregados.

### 3.2 Outputs
- `data/traders_intelligence/scoreboard.json` — schema
  `traders_intelligence_scoreboard_v1`:
  - **Por trader:** `n_signals_total`, `n_unique_lifecycle_keys`,
    `mean_persistence_runs`, `pct_disappeared_apparent`,
    `appearance_rate_per_day`, `cities_active`, `freshness_score`.
  - **Por ciudad:** mismas + `n_traders_observed`, `signal_density`,
    `overlap_with_bot_signals` (correlación, sin causalidad).
  - **Cohorte cruzada con outcomes:** sólo si `lifecycle_key` matchea exact
    con un trade real cerrado. Métricas: `n_matched_trades`,
    `bot_wr_when_trader_present`, `bot_wr_when_trader_absent`, `n` por celda.
    `cohort_size_warning=true` si `n<30`.
- `docs/traders_intelligence_scoreboard_latest.md` (humano).

### 3.3 Persistencia / reaparición
Definiciones explícitas:
- `persistence_runs`: consecutivos `still_present` antes de
  `disappeared_apparent`.
- `reappearance_gap`: runs entre `disappeared_apparent` y siguiente
  `reappeared`.
- `flicker`: `appeared` y `disappeared_apparent` en runs adyacentes; señal
  débil o ruido.

### 3.4 Relación con módulos existentes (sólo lectura, no flujo)
| Módulo | Relación V1.2 | Acción |
|---|---|---|
| `blocked_signals` | Cruzar `lifecycle_key` con `match_key` de bloqueos | Métrica `pct_blocked_overlap` |
| `city_validation` | Comparar cohortes trader vs validación ciudad | Solo display |
| `promotion_gate` | **No** alimentar gates. Log paralelo para futura comparación | Anotar `promotion_gate_state_at_run` |
| `trade_lifecycle` | Match exact por `match_key` para outcomes reales | Cohorte cruzada con `n` mínimo |

### 3.5 Lo que no hace V1.2
- No modifica gates, sizing, whitelist, city modes.
- No envía Telegram accionable.
- No genera recomendaciones automáticas.

---

## 4. Telegram Andon — propuestas

**Regla:** ningún mensaje contiene BUY/SELL/SKIP. Solo evidencia/salud/readiness.

### 4.1 V1.1 — Salud del collector (1 mensaje/día máximo)

```
[TI Collector] OK — 24/24 runs, freshness 12m
appeared=4 still=12 disappeared_apparent=2 reappeared=1
cities: Houston(8) Miami(5) LA(3) Manila(0)
```

```
[TI Collector] WARN — 18/24 runs, last_run 92m ago
consecutive_failures=2 kill_switch=OFF
```

```
[TI Collector] KILL — kill_switch_active=true (5 fallos consecutivos)
acción: revisar logs, flag manual para reactivar
```

Thresholds iniciales:
- OK: `runs_24h >= 20` y `last_run_age_minutes <= 90`.
- WARN: `runs_24h in [12,19]` o `last_run_age_minutes in (90,180]`.
- KILL: `kill_switch_active=true` o `runs_24h < 12`.

### 4.2 V1.2 — Evidence Andon (semanal, sólo cambio de estado)

```
[TI Evidence] Houston — REVIEW_READY
trader=Thrifty-Original n_signals=42 persistence_mean=6.2 runs
overlap_blocked=18% overlap_bot=64%
cohort_outcomes n=31 wr_present=68% wr_absent=52%
clasificación: REVIEW_READY (humano)
```

Clasificaciones:
- `KEEP` — evidencia estable, sin cambio.
- `WATCH` — métricas moviéndose pero sin masa crítica.
- `WAITING_EVIDENCE` — `n<30` o `freshness_score<0.5`.
- `REVIEW_READY` — `n>=30`, `freshness>=0.5`,
  `pct_disappeared_apparent<40%`, gap clara `wr_present vs wr_absent` ≥10pp.
  Disparador para revisión humana, **no** patch.

### 4.3 Anti-spam
- Una alerta por `(trader, city, clasificación)` por semana máximo.
- Sólo emitir cuando hay cambio de estado, no como heartbeat.
- Heartbeat solo via daily_summary existente.

---

## 5. Cómo ayuda a mejorar (sin tocar runtime)

| Decisión humana | Cómo TI alimenta | Cuándo |
|---|---|---|
| Priorizar ciudades para revisión manual | `signal_density` + `freshness_score` | Semanal |
| Detectar señales `trader_only` útiles | `appeared` con `overlap_bot=0` y persistence>=3 runs | V1.2 |
| Alert hygiene | `flicker` rate alto → ajustar TARGET_TRADERS | Mensual |
| Decidir nuevos traders a observar | `n_unique_traders_seen` en signals sin filtrar | V1.2+ |
| Cambiar city modes | **No automático.** Solo input a discusión Opus separada | V2 (fuera scope) |

---

## 6. Gates entre fases

### Gate V1 → V1.1
- ≥3 snapshots manuales registrados con lifecycle no vacío.
- Schema validado.
- `verify_before_deploy.py` cubre el tool.
- `docs/traders-intelligence-v1-snapshots.md` actualizada.
- Decisión explícita: scheduler hook + env var.

### Gate V1.1 → V1.2
- ≥7 días continuos con `runs_24h>=20` y `consecutive_failures<3`.
- ≥3 ciudades target con `n_signals>=20`.
- Kill switch testeado al menos una vez (forzado).
- Sin incidentes de overlap con bot runtime.

### Gate V1.2 → recomendaciones
- ≥1 cohorte cruzada con `n>=30` outcomes reales.
- ≥1 ciclo completo (4 semanas) de scoreboard estable.
- Validación humana de al menos 3 clasificaciones `REVIEW_READY`
  con resultado documentado.
- Opus revisa metodología de cohorte (evita cohorts mezcladas).

### Gate recomendaciones → cambios operativos
- **Fuera de scope ahora.** Requiere Opus + autorización Pablo + revisión
  separada de BANKROLL/Fase C.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobreinterpretar muestras pequeñas | `cohort_size_warning` si `n<30`. Prohibir `REVIEW_READY` con `n<30`. |
| Confundir presencia trader con causalidad | Reportar siempre `wr_present` + `wr_absent` + `n` ambos lados. |
| Cohortes mezcladas | Segmentar por `(trader, city, condition)`. Si se mezcla → `WATCH_RISK`, no `REVIEW_READY`. |
| P&L no canónico | Solo `bot_outcomes.csv` u origen canónico. Nunca derivar P&L desde `signals.json`. |
| Telegram spam | Estado-cambio only + 1/semana max por `(trader,city)`. |
| Observabilidad → trading prematuro | Gate explícito V1.2→recomendaciones y Opus. TI nunca escribe a `bot_evaluation`, `gates`, `whitelist`, `sizing`. |
| Drift de TARGET_TRADERS hardcoded | V1.2 mover a `config/traders_intelligence.json` con review humano antes de cada cambio. |

---

## 8. Eventos / artefactos a guardar

- `agent_events.jsonl`: `traders_intelligence_collector_run`,
  `traders_intelligence_kill_switch`, `traders_intelligence_scoreboard_run`,
  `traders_intelligence_review_ready`.
- `data/traders_intelligence/collector_state.json` (V1.1).
- `data/traders_intelligence/scoreboard.json` (V1.2).
- `data/traders_intelligence/scoreboard_history/<date>.json` (V1.2,
  snapshot diario para trend).
- Snapshots y reports actuales se mantienen sin cambio.

---

## 9. Primer patch para Codex (V1.1, LOG_ONLY)

Scope mínimo, autorizable después de revisión:

1. Crear `tools/traders_intelligence_collector.py` que invoque el snapshot
   tool actual con:
   - Lectura de `collector_state.json`.
   - Cooldown + kill switch via env var.
   - Skip si `signals.json.generated` no cambió.
   - Append a `agent_events.jsonl`.
2. Hook al scheduler **existente** del bot — bloque opt-in tras env var.
   Default OFF.
3. Tests: dry-run, cooldown, kill switch, env OFF.
4. Doc en `docs/traders-intelligence-v1-snapshots.md` (sección V1.1).
5. `verify_before_deploy.py`: smoke del nuevo tool.

No incluye en este patch:
- Telegram Andon (segundo patch separado, tras 7 días estables).
- Scoreboard (V1.2, distinto patch).
- Cambios al snapshot tool actual.

---

## 10. Explícitamente fuera hasta revisión posterior

- Cambios a city modes, whitelist, sizing, gates, scheduler core.
- Telegram con BUY/SELL/SKIP o sugerencias accionables.
- Cohortes que mezclen `condition`/`days_ahead`/`trader` sin segmentar.
- Cualquier flujo donde TI escriba a campos consumidos por trading
  (`bot_evaluation`, `promotion_gate`, `whitelist`).
- BANKROLL $35.
- Fase C.
- Auto-modificación de `TARGET_TRADERS` / `TARGET_CITIES`.

---

## 11. Resumen ejecutivo (1 línea)

V1.1 = collector automático LOG_ONLY con kill switch + Andon de salud;
V1.2 = evidence scoreboard agregado por trader/city + cohortes cruzadas con
`n>=30`; entre fases, gates duros con evidencia operativa; entre V1.2 y
cualquier cambio runtime, **revisión Opus separada**.

---

## Referencias

- `docs/traders-intelligence-spec.md` — spec v0 puro-compute.
- `docs/traders-intelligence-v1-snapshots.md` — V1 archivist tool.
- `docs/traders-intelligence-v1-activation-package.md` — contrato V1 active.
- `tools/traders_intelligence_snapshot.py` — V1 minimal archivist (reutilizado por V1.1).
- `tools/traders_intelligence_daily_summary.py` — daily review heartbeat.
- `ORCHESTRATOR.md` — modos LITE/NORMAL/FULL, gates internos, anti-patrones.
