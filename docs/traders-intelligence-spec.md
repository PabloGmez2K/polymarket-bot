# `traders_intelligence` — Spec de diseño (v0)

> Documento de diseño para la tool `traders_intelligence`. Read-only, no toca
> trading core, NOAA, scheduler ni policy. Esta spec es la fuente de verdad para
> la implementación inicial (v0). v1 y v2 quedan pospuestos hasta que exista una
> pregunta operativa concreta que los justifique.

---

## 1. Resumen ejecutivo

La tool construye una capa analítica sobre los 6 artefactos ya existentes de
traders (`signals.json`, `directional_trader_census.json`,
`directional_trader_enrichment.json`, `reference_trader_city_market_cross.json`,
`signals_crosscheck.jsonl`, `blocked_signals_resolutions.jsonl`) más el propio
`trade_lifecycle.json` como contexto.

**Hallazgo central**: hoy NO tenemos un "lifecycle externo" al mismo nivel que
el propio. Lo que tenemos son snapshots puntuales + settlements post-facto.
Cualquier inferencia sobre SL/TP/escalado de un trader es derivada indirectamente
de diferencias entre snapshots y settlement — no de datos de ejecución.

La recomendación es lanzar **v0 puro-compute** sobre artefactos existentes y
posponer v1 hasta que haya una decisión operativa concreta que lo requiera.
Casi todo el valor de inteligencia-sobre-traders vive en v0 si la
interpretación es honesta. v1 y v2 son valiosos pero caros y fáciles de
sobre-construir.

---

## 2. Hallazgos y premisas (verificados contra la data actual)

**Hecho A — Los artefactos NO son simétricos con `trade_lifecycle.json`:**
- Nuestro lifecycle: `buys[]`, `exit_attempts[]`, `position_snapshots[]`,
  `close_context`, timestamps en cada evento.
- `signals.json` trader-side: `avg_price` (cost basis actual), `cur_price`
  (mark), `cash_pnl`, `pct_pnl`, `trader_win_rate`. **No size, no entry
  timestamp, no exit event.**
- `directional_trader_census.json`: per-trade price + size en `sample_positions`.
- `directional_trader_enrichment.json`: sólo summaries agregados
  (wins/losses/n_closed), sin granularidad por posición excepto 4 ejemplos.

**Hecho B — El census es un one-shot, no una serie:**
`directional_trader_census.json` fue generado 2026-04-08. El enrichment,
2026-04-22. No hay cadencia. Cualquier "evolución del trader" requeriría
snapshots periódicos nuevos → v1.

**Hecho C — Hay dos series temporales ya existentes que subutilizamos:**
- `signals_crosscheck.jsonl` (cadencia baja pero existente).
- `blocked_signals_resolutions.jsonl` (~113 líneas al momento del diseño;
  settlements post-resolution con `avg_price_entered`, `close_price`,
  `win_for_trader`, por `match_key`).
- Estas dos son la columna vertebral de v0 honesto: permiten construir
  `apparent_outcome_by_trader` por match_key sin inventar eventos intermedios.

**Hecho D — `signals.json` como serie de snapshots NO se archiva hoy:**
El archivo se sobrescribe cada cycle. Si queremos detectar apariciones y
desapariciones de `match_key` por trader necesitamos un archivador → v1.

**Hecho E — Sí hay margen útil en v0:**
- Composición por trader: dominant_city, conditions, outcomes (YES/NO),
  price_style, win rate cerrado.
- Multi-strike: contar posiciones por (trader, city, date) en `signals.json`.
- Cross bot/trader: `signals_crosscheck.jsonl` ya tiene bucket MATCH / BOT_ONLY
  / TRADER_ONLY por ciudad.
- Settlement realizado vs entrada: `blocked_signals_resolutions.jsonl` tiene
  `avg_price_entered` y `close_price` → permite medir edge-at-entry real.

---

## 3. Objetivo de la tool

`traders_intelligence` produce un perfil comparativo, por trader y agregado, de
estilo operativo inferido desde los artefactos existentes, con el menor
overreach posible. Responde: "¿cómo operan estos wallets, en qué difieren de
nosotros, y qué señal de ellos es realmente útil?"

No es un backtester. No es un oráculo. No toca trading core. No modifica policy.

---

## 4. Preguntas que SÍ debe responder / que NO debe

### 4.1 Sí responde (con data actual)

| Pregunta | Fuente | Confianza |
|---|---|---|
| ¿En qué ciudades opera principalmente? | census.top_cities, enrichment.closed_weather_conditions | alta |
| ¿Qué condition prefiere (exact/range/at_or_above/at_or_below)? | census.conditions, enrichment.closed_weather_conditions | alta |
| ¿Sesgo YES vs NO en BUYs? | census.outcomes | alta |
| ¿Rango de precios de entrada (deep-value vs mid vs favorito)? | census.avg_price, census.price_style, blocked_resolutions.avg_price_entered | alta |
| ¿WR realizado cerrado? | enrichment.closed_summary.win_rate | media (cohort sesgado) |
| ¿PnL realizado cerrado? | enrichment.total_closed_pnl | media |
| ¿Cubre múltiples strikes de la misma ciudad/fecha? | signals.json agrupado por (trader, city, date) | alta |
| ¿Solapa con nosotros en la grilla? | signals_crosscheck.jsonl | alta |
| ¿Qué pasó con sus señales cuando las bloqueamos? | blocked_signals_resolutions.jsonl | alta |
| ¿El trader entra cerca de mercado extremo (<0.2 o >0.8)? | census.sample_positions.price, blocked_resolutions.avg_price_entered | alta |

### 4.2 NO responde honestamente hoy

| Pregunta | Por qué no | Qué haría falta |
|---|---|---|
| ¿Usa SL? | `signals.json` no archiva series; no hay exit events. | v1: archivador de snapshots + heurística `apparent_stop_loss` con confidence. |
| ¿Usa TP? | igual | igual, con umbral contrario. |
| ¿Cuánto tiempo sostiene posiciones? | No hay entry ni exit timestamp. | v1: diff entre primera y última aparición del match_key. |
| ¿Escala entradas o salidas? | `signals.json` tiene `avg_price`. Un delta indica compra adicional, pero sin volumen. | v1: serie de avg_price por (trader, match_key). |
| ¿Reacciona a updates de forecast? | No tenemos timestamp de su acción. | v1 + alineación con `forecast_accuracy_raw`. |
| ¿PnL realizado real por operación? | Enrichment agrega métrica Polymarket no weather-only. | Data API histórica por wallet. |
| ¿Es "convicción" vs "timing" vs "estructura"? | Taxonomía inferida, no observable. | Ver §7 — sólo como tag con evidencia. |

**Guardrail fundamental**: cada respuesta de la tool debe venir con un campo
`confidence` ∈ {`high`, `medium`, `low`, `insufficient_data`} y un campo
`evidence` enumerando los archivos y N que la sustentan. Si no alcanza la data,
el valor es `null` y `confidence: insufficient_data`.

---

## 5. Inferencias legítimas vs overreach

### Legítimas (observacional directo)
- "El trader X tuvo 74% WR sobre 100 posiciones cerradas la última ventana." — enrichment.
- "El trader X entra mayoritariamente en `exact` en Shanghai." — census.
- "El trader X, en los 23 match_keys bloqueados que resolvieron, ganó en 17." — blocked_resolutions.
- "En la grilla actual, el trader X ofrece 5 strikes adyacentes en la misma ciudad/fecha." — signals.json filtrado.

### Overreach (rechazar explícitamente)
- "Este trader usa SL en -30%." — prohibido hasta tener serie de snapshots. Máximo expresable: `apparent_exit_while_negative` con confidence baja.
- "Este trader tiene edge sobre NOAA." — requiere backtest, no sólo WR histórico.
- "Este trader es mejor forecaster que nosotros." — sesgo de selección por supervivencia.
- "Este trader escaló entradas." — necesita serie de avg_price.
- "Reaccionó al forecast update." — necesita alineación temporal fina.

**Regla interna**: cada tag binario (`uses_apparent_sl`, `is_specialist`, etc.)
requiere `evidence_count >= threshold_min` y `confidence` explícito. Si no, el
tag no se emite.

---

## 6. Arquitectura por fases

### v0 — compute-only sobre artefactos existentes (ESTA IMPLEMENTACIÓN)

**Objetivo**: extraer el 80% del valor interpretativo sin recolectar data nueva.

**Inputs**:
- `data/runtime_import/signals.json`
- `data/directional_trader_census.json`
- `data/directional_trader_enrichment.json`
- `data/reference_trader_city_market_cross.json`
- `data/signals_crosscheck.jsonl` (fuente live canónica; fallback legacy:
  `data/runtime_import_derived/signals_crosscheck.jsonl`)
- `data/blocked_signals_resolutions.jsonl` (fuente live canónica; fallback
  legacy: `data/runtime_import_derived/blocked_signals_resolutions.jsonl`)
- `data/runtime_import/trade_lifecycle.json` (contexto comparativo agregado; no se
  cruza a nivel match_key en v0)

**Outputs**:
- `data/traders_intelligence.json`
- `docs/traders_intelligence_latest.md`

**Alcance de v0**:
- Perfil por trader con métricas §9.
- Agregados por ciudad (qué trader "manda" ahí).
- Cross matrix con `signals_crosscheck.jsonl`.
- Blocked-signals outcome por trader.
- Composición actual de la grilla (multi-strike flags).
- No inventa pseudo-lifecycle. Cualquier pregunta de SL/TP/hold time devuelve
  `confidence: insufficient_data` con mensaje claro.

### v1 — snapshots periódicos + pseudo-lifecycle (MINIMO ACTIVADO 2026-05-01)

Nota 2026-05-01: se activa solo el minimo observacional via
`tools/traders_intelligence_snapshot.py`, sin scheduler ni integracion con
trading. El alcance queda limitado a `Thrifty-Original` y `Entire-Hood` en
`Houston`, `Los Angeles`, `Manila` y `Miami`. La salida vive bajo
`data/traders_intelligence/` como artefacto runtime/regenerable.

**Gatillo**: sólo si una pregunta operativa concreta lo justifica (ej. "¿copiamos
la señal de salida de X?"). Si no hay esa pregunta, no se construye.

Componentes previstos cuando se active:
1. `traders_intelligence_snapshot.py` archivando `signals.json` recortado a
   `data/traders_intelligence/snapshots/<run_id>.json`.
2. Builder de pseudo-lifecycle por `(trader, match_key)` con `first_seen_at`,
   `last_seen_at`, `avg_price_trajectory`, `cur_price_trajectory`,
   `disappeared_before_resolution`, `apparent_exit_label`.
3. Heurísticas documentadas (no mágicas):
   - `apparent_stop_loss`: `last_cur_price <= avg_price * 0.70` AND
     `disappeared_before_resolution` → confidence=`medium`.
   - `apparent_take_profit`: `last_cur_price >= 0.90` AND
     `disappeared_before_resolution` → confidence=`medium`.
   - `held_to_resolution`: `last_seen_at` a <2h de resolución y match_key en
     blocked_resolutions → confidence=`high`.
   - Ambiguos → `unknown`. No forzar etiqueta.

### v2 — comparativa trader vs bot usando `trade_lifecycle.json` (POSPUESTO)

**Gatillo**: v1 estable Y ≥30 match_keys solapados.

Qué agrega:
- Para cada `(trader, match_key)` que también sea posición nuestra: alinear
  timelines.
- Métricas cruzadas: `entry_gap_minutes`, `exit_gap_minutes`, `same_outcome`,
  `both_right`, `both_wrong`, `trader_right_bot_wrong`.
- Si N de solapamiento <30, reporta "insufficient" en vez de métricas.

---

## 7. Output — esquema propuesto

### 7.1 `data/traders_intelligence.json` (v0)

```json
{
  "schema_version": "v0",
  "generated_at": "2026-04-24T...",
  "inputs": {
    "signals": "data/runtime_import/signals.json",
    "census": "data/directional_trader_census.json",
    "enrichment": "data/directional_trader_enrichment.json",
    "city_cross": "data/reference_trader_city_market_cross.json",
    "crosscheck_series": "data/signals_crosscheck.jsonl",
    "blocked_resolutions": "data/blocked_signals_resolutions.jsonl"
  },
  "integrity": {
    "signals_generated_at": "...",
    "census_generated_at": "...",
    "census_stale_days": 16,
    "enrichment_generated_at": "...",
    "n_traders_profiled": 10,
    "n_traders_dropped_insufficient_data": 2,
    "likely_input_degraded": false
  },
  "traders": [
    {
      "pseudonym": "Entire-Hood",
      "address": "0xb40e...",
      "reference_quality": "high_priority_reference",
      "activity": {
        "n_active_signals_now": 8,
        "n_distinct_cities_active_now": 6,
        "n_closed_positions_recent": 100,
        "closed_weather_conditions": {"exact": 47, "range": 6, "at_or_above": 4},
        "confidence": "high",
        "evidence": ["signals.json", "enrichment.json"]
      },
      "style": {
        "dominant_city": "Wuhan",
        "top_cities": {"Wuhan": 1, "Shanghai": 1, "Ankara": 1},
        "condition_preference": "exact",
        "outcome_bias_pct": {"Yes": 33.3, "No": 66.7},
        "price_style": "mid_range",
        "entry_price_band": {"p25": 0.48, "p50": 0.58, "p75": 0.65, "n": 3},
        "confidence": "medium",
        "evidence": ["census.sample_positions n=3"]
      },
      "grid_structure": {
        "multi_strike_signals": [
          {"city": "London", "date": "2026-04-21", "n_strikes": 2, "strikes": [13, 14], "condition": "exact"}
        ],
        "any_consensus_with_others": true,
        "n_consensus_match_keys": 3,
        "confidence": "high",
        "evidence": ["signals.json"]
      },
      "realized_performance": {
        "closed_win_rate_pct": 74.0,
        "closed_pnl_cash": 667.59,
        "closed_n": 100,
        "confidence": "medium",
        "caveat": "Polymarket enrichment cohort, no necesariamente weather-only",
        "evidence": ["enrichment.closed_summary"]
      },
      "blocked_signal_performance": {
        "n_resolved": 17,
        "n_wins": 14,
        "wr_pct": 82.4,
        "avg_entry_price": 0.63,
        "avg_close_price": 0.85,
        "confidence": "high",
        "evidence": ["blocked_signals_resolutions.jsonl"]
      },
      "vs_bot": {
        "n_match_keys_overlap_recent": 4,
        "n_cities_bot_only": 2,
        "n_cities_trader_only": 8,
        "confidence": "high",
        "evidence": ["signals_crosscheck.jsonl"]
      },
      "exit_behaviour": {
        "answerable": false,
        "reason": "v0 no archiva serie de signals.json; sin snapshots periódicos no se puede inferir SL/TP.",
        "confidence": "insufficient_data"
      },
      "hold_duration": {
        "answerable": false,
        "reason": "mismo motivo",
        "confidence": "insufficient_data"
      },
      "scaling_behaviour": {
        "answerable": false,
        "reason": "mismo motivo",
        "confidence": "insufficient_data"
      },
      "profile_tags": [
        "specialist_exact",
        "no_bias",
        "high_blocked_wr",
        "multi_strike_issuer"
      ]
    }
  ],
  "city_rollup": [
    {
      "city": "Shanghai",
      "policy_mode": "canary",
      "n_reference_traders_active": 2,
      "dominant_trader_now": "Entire-Hood",
      "any_consensus_now": true,
      "bot_overlap_recent": true
    }
  ],
  "aggregate": {
    "n_traders_profiled": 10,
    "n_high_priority": 3,
    "n_low_signal": 1,
    "n_active_but_unproven": 6,
    "top_blocked_wr": [
      {"trader": "Loyal-Aggression", "wr_pct": 95.0, "n": 6}
    ]
  },
  "warnings": [
    "census.generated_at is 16 days old; top_cities/conditions may be stale",
    "blocked_signals_resolutions.jsonl n=113 global; per-trader N varies"
  ]
}
```

### 7.2 `docs/traders_intelligence_latest.md` (v0)

Estructura fija y corta:
- **Header**: generated_at, health_status, n_traders_profiled.
- **Tabla por trader**: pseudonym, quality, dominant_city, condition_pref,
  outcome_bias, closed_wr, blocked_wr, n_active_now, tags.
- **Sección "no responde honestamente hoy"**: lista literal de preguntas con
  `insufficient_data`.
- **Anexo**: top mismatches bot vs trader en últimos ciclos del crosscheck.
- Máximo ~2 pantallas de texto.

### 7.3 Scores y tags

Tags sólo si hay evidencia suficiente:
- `specialist_<city>` si `top_cities[city]/total >= 0.6` y n≥5.
- `specialist_<condition>` análogo.
- `yes_biased` / `no_biased` si desviación >30%.
- `high_blocked_wr` si `blocked.wr_pct >= 70` y `n>=10`.
- `multi_strike_issuer` si hay al menos un (trader, city, date) con ≥2 strikes
  distintos en grilla actual.
- `consensus_hub` si aparece en `consensus_with` de ≥3 traders en ventana.
- `deep_value_entrant` si `avg_price_entered <= 0.3` y n≥5.
- `favorite_entrant` si `avg_price_entered >= 0.7` y n≥5.

**Sin score compuesto en v0.** Un score único es vanity. La tool devuelve tags
discretos; el operador interpreta.

---

## 8. Taxonomía útil de perfiles

Cuatro arquetipos. Cada uno se emite como `candidate_profile` con `evidence` y
`confidence`, nunca como etiqueta definitiva.

1. **Directional forecaster** — bias por `condition=exact` o `at_or_above`,
   entradas mid-range, WR cerrado ≥65%, múltiples ciudades, sin multi-strike.
   Hipótesis: predice el número con su propio modelo meteo.
2. **Multi-strike structurer** — cobertura de varios strikes adyacentes mismo
   día/ciudad, entradas mid, bias mixto YES/NO. Hipótesis: arbitra estructura
   de grilla o hedging.
3. **Favorite chaser** — `avg_price_entered ≥ 0.75` consistente, WR aparente
   alto pero EV dudoso. Hipótesis: captura kopecks en mercados casi resueltos.
4. **Deep-value taker** — `avg_price_entered ≤ 0.3`, n bajo, hits aislados de
   PnL alto. Hipótesis: busca mispricing extremo.

No confundir convicción vs timing vs estructura en v0. Sin serie temporal,
"timing" no es observable. Sólo expresable como `apparent_timing_candidate` en
v1.

---

## 9. Métricas concretas recomendadas

### Por trader (v0)
- `n_active_signals_now` (signals.json)
- `n_closed_positions_recent` (enrichment)
- `dominant_city`, `top_cities_share` (census)
- `condition_preference`, `condition_shares` (census + enrichment)
- `outcome_bias_pct`
- `entry_price_band` (p25/p50/p75) con n explícito
- `closed_win_rate_pct` + caveat
- `blocked_signal_wr_pct` + n  ← la métrica más honesta disponible hoy
- `n_multi_strike_groups_now`
- `n_consensus_with_others_now`
- `bot_overlap_recent` (boolean)

### Por ciudad (`city_rollup`)
- `n_reference_traders_active`, `any_consensus_now`, `bot_overlap_recent`,
  `dominant_trader_now`, `policy_mode`.

### Agregado
- Distribución por `reference_quality`.
- Top por `blocked_signal_wr_pct`.
- Lista de `traders_profile_incomplete`.

**Explícitamente fuera de v0**: `hold_duration`, `scale_in_rate`,
`apparent_sl_rate`, `apparent_tp_rate`, `reaction_time_to_forecast_update` —
todo con `"answerable": false` hasta v1.

---

## 10. Riesgos de interpretación / falsos positivos

1. **Stale census** — `directional_trader_census.json` puede estar desactualizado.
   Mitigación: `integrity.census_stale_days`, flag si >14 días.
2. **Cohort sesgado en `closed_win_rate`** — enrichment trae los 100 últimos
   cerrados del wallet, NO los weather-only (`n_closed_weather` < 100).
   Mitigación: preferir `blocked_signal_wr_pct`.
3. **Selection bias** — seguimos a estos traders porque ganaban; su WR no
   generaliza. La tool no debe decir "traders en general ganan".
4. **Consensus ≠ señal independiente** — pueden estar copiándose entre sí.
5. **`blocked_signal_wr` sobre-indexa mercados fáciles** (cur_price≈0.99 al
   momento del bloqueo). Mitigación: reportar también `avg_entry_price`.
6. **Multi-strike ≠ scalping** — podría ser cobertura. No inferir causalidad.
7. **`apparent_exit_*` (v1) confundirá ruido con señal** — documentar que
   `apparent_*` ≠ `confirmed_*`.
8. **Settlement fidelity** — si Polymarket reporta con delay, `checked_at` puede
   adelantar fake wins/losses. Mitigación: re-check si
   `close_price ∈ (0.01, 0.99)`.

---

## 11. Cómo comparar con nuestra operativa sin caer en vanity

Regla base: **mismo match_key, misma ventana, mismo cohort**.

Comparaciones válidas (v2 mínimo):
- Sobre `(trader, bot)` en el MISMO `match_key`: quién entró primero, quién
  salió primero, mismo outcome, quién ganó.
- Agregado sobre N≥30 solapamientos.

Comparaciones prohibidas:
- "WR global del trader" vs "WR global del bot" — cohorts distintos.
- "PnL del trader" vs "PnL nuestro" — sizing distinto; nuestra cuenta es $25.
- "Ellos usan SL, nosotros también" — sin serie temporal no se afirma en v0.

La tool debe emitir `comparison_mode: "matched_subset"` con `n_overlap`; si
n<30, `comparison_mode: "insufficient"` y no devuelve números.

---

## 12. Recomendación final

**Construir v0 ahora. Posponer v1 y v2 hasta que exista una decisión operativa
concreta que lo requiera.**

Razones:
1. v0 extrae el grueso del valor con riesgo cero: no toca trading, no escribe
   state nuevo, no agrega cadencias ni jobs.
2. Las preguntas sin respuesta honesta hoy quedan explícitamente marcadas como
   `insufficient_data`. Eso por sí solo aclara dónde invertir después.
3. v1 agrega costo: jobs adicionales, archivador, un nuevo
   `data/traders_signals_archive/` creciente, heurísticas ambiguas propensas a
   falsos positivos. Sin una pregunta operativa concreta, v1 no se justifica.
4. v2 sólo tiene sentido cuando v1 esté estable y haya ≥30 match_keys
   solapados. Prematuro hoy.

**Criterio de activación de v1**: que una decisión de roadmap (ej. "seguir
salidas de traders en canary cities") requiera saber si salen antes. Hasta ese
momento, v0 cubre "auditable + útil".

---

## 13. Spec ejecutable para Codex

### Entregables concretos
1. `tools/traders_intelligence_report.py` — script read-only, sin side-effects
   salvo escribir sus dos outputs.
2. `data/traders_intelligence.json` — output JSON (v0 schema).
3. `docs/traders_intelligence_latest.md` — output markdown.

### Contrato del script (v0)
- CLI: `python tools/traders_intelligence_report.py [--json-output PATH] [--md-output PATH] [--min-evidence N]`.
- Lee sólo los 7 artefactos listados en §6.
- Si un input falta: NO falla; emite `warnings` y continúa con lo disponible.
  `health_status` ∈ {`usable_signal`, `degraded`, `unusable`}.
- Nunca escribe fuera de `data/traders_intelligence.json` y
  `docs/traders_intelligence_latest.md`.
- Nunca llama a APIs externas en v0.
- Formato de timestamps y `generated_at` consistente con los otros artefactos
  (ISO con `+00:00`).
- Honra la convención `integrity` del enrichment (`likely_input_degraded`,
  contadores).

### Convenciones de código del repo (respetar)
- `REPO_ROOT = Path(__file__).resolve().parents[1]`.
- Paths default:
  `DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "traders_intelligence.json"`,
  `DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "traders_intelligence_latest.md"`.
- `argparse` con estilo de `tools/directional_trader_census.py` y
  `tools/reference_trader_city_market_cross.py`.
- No usar `replace_all` sobre documentos históricos.

### Tests mínimos esperables
- Smoke test: el script corre sin inputs → output con `health_status: unusable`
  y warnings poblados.
- Con los inputs actuales de la rama: output válido, `n_traders_profiled >= 1`,
  ningún tag emitido sin evidencia mínima.
- Campos `confidence` presentes en cada bloque.

### Explícitamente fuera de alcance para Codex en esta iteración
- Nada de archivar `signals.json` (eso es v1).
- Nada de tocar `tools/signals_crosscheck_railway_service.py`.
- Nada de emitir alertas Telegram ni modificar policy.
- Nada de comparar contra `trade_lifecycle.json` a nivel match_key (eso es v2).
- Nada de cambios en `bot.py`, scheduler, NOAA, sizing, reglas de
  entrada/salida ni arquitectura core.
- No modificar `CONTEXTO.md`, `HISTORIAL_SESIONES.md` ni `agent_events.jsonl`
  sin pedido explícito del operador; si el operador lo pide después del merge,
  alinear según `OPERATIONS_PLAYBOOK.md`.

### Checkpoint previo al push
- `verify_before_deploy.py` debe pasar sin regresiones antes de commit.
- Sanity check manual del JSON y del MD generados con los inputs actuales.
