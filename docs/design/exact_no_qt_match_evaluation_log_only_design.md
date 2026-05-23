# Design: Exact / No QT Match — LOG_ONLY Edge Evaluation Experiment

**Status:** `DESIGN_COMPLETE — READY_FOR_OPUS_APPROVAL`
**Date:** 2026-05-23
**Session:** 379 (Sonnet, docs-only + Railway read-only)
**Predecessor verdict:** `DESIGN_PRE_EDGE_LOG_ONLY_LEARNING_EXPERIMENT` (Opus)

---

## 1. Propósito y límites

### Propósito

Existe una cohorte de mercados `condition=exact` que el bot encuentra en ciclos activos y canary, calcula
el forecast (ya cargado), pero nunca llega a calcular probabilidad ni edge porque el QT gate los descarta
antes por `no_quality_trader_signal_match`. No hay evidencia de si estos mercados habrían tenido edge
positivo o negativo: son un **punto ciego de aprendizaje de policy**.

Este experimento captura, en modo **LOG_ONLY**, la probabilidad y edge potencial de esos mercados, sin
autorizar ninguna operación ni cambiar la policy de entrada.

### Límites estrictos

| Lo que hace | Lo que NO hace |
|---|---|
| Llama `estimate_prob_with_city` para cohorte exacta | Compra, vende, ni siquiera se acerca a emitir orden |
| Escribe `exact_no_qt_match_evaluations_log_only.jsonl` | No modifica `ALLOWED_CONDITIONS` |
| Calcula `edge_pct` y `edge_passes_reference_threshold_log_only` | No modifica `QUALITY_TRADER_CONDITIONS` |
| Usa forecast ya cargado en memoria | No agrega ciudades a whitelists |
| Emite métricas de captura por ciclo | No cambia city modes |
| Permite rollback instantáneo por env var | No toca thresholds, BANKROLL, Fase C |

El experimento **no autoriza activación de env var**. La env var `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED`
queda en `0` por defecto hasta aprobación Opus explícita tras revisar este documento.

---

## 2. Evidencia validada y baseline de volumen

### 2.1 Gap Report — live Railway (2026-05-23)

Ejecutado en Railway con `tools/trader_vs_bot_gap_report.py --data-dir /app/data --json`:

| Métrica | Valor |
|---|---|
| Filas con `qt_gate_sub_reason_join_status=MATCHED` | 54 |
| Unique `match_key` entre esas 54 filas | 46 |
| Filas `evaluation_stage_status=POLICY_BLOCKED_BEFORE_EDGE_EVALUATION` | 14 |
| De esas 14, con `qt_join_status=MATCHED` + `no_quality_trader_signal_match` | 9 |
| Unique match_keys entre los 9 POLICY_BLOCKED+MATCHED | 8 |
| Filas POLICY_BLOCKED con `qt_join_status=NOT_APPLICABLE` (Paris blocked) | 5 |

Ciudades en los 54 MATCHED con `no_quality_trader_signal_match`:
Taipei, Shanghai, Seoul, Toronto, Tokyo, Jakarta, Paris, Munich, Madrid, Moscow, Singapore, Shenzhen, Ankara, Milan.

Distribución `city_mode_at_record_time` entre esas 54: `canary=35`, `active=9`, `shadow=10`.

> Nota: Paris aparece tanto como `NOT_APPLICABLE` (ciudad bloqueada, skip antes de QT gate) como
> en cohorte MATCHED de shadow. Los 9 POLICY_BLOCKED+MATCHED corresponden a Madrid, Ankara, Milan
> en ventana 2026-05-21/22.

### 2.2 Skip Log — active/canary baseline (2026-05-23)

Ejecutado en Railway contra `/app/data/skip_log.jsonl`
(`skip_reason=condition_filtered`, `extras.exact_range_gate_reason=no_quality_trader_signal_match`,
`city_mode in {active, canary}`):

| Ventana | Filas | Unique `qt_match_key` | Ciclos | Máx/ciclo | Avg/ciclo |
|---|---|---|---|---|---|
| Todo el tiempo (desde 2026-05-01) | 781 | 290 | 132 | 14 | 5.9 |
| Últimas 72h | 161 | 57 | 23 | 12 | 7.0 |
| Últimas 24h | 44 | 19 | 7 | 12 | 6.3 |

Ciudades últimas 72h: Seoul, Tokyo, Shanghai, Singapore, Wellington, Madrid, Ankara, Munich, Milan, Toronto.

Ciudades últimas 24h: Tokyo, Shanghai, Seoul, Singapore.

**Muestra de `qt_match_key` últimas 24h (deduplicados):**
```
Seoul|2026-05-23|exact|21|C      Shanghai|2026-05-23|exact|27|C
Seoul|2026-05-23|exact|22|C      Shanghai|2026-05-23|exact|28|C
Seoul|2026-05-23|exact|23|C      Shanghai|2026-05-23|exact|29|C
Tokyo|2026-05-23|exact|23|C      Shanghai|2026-05-23|exact|30|C
Tokyo|2026-05-23|exact|24|C      Shanghai|2026-05-23|exact|31|C
...                               (19 unique)
```

### 2.3 Análisis de coste de cómputo

El QT gate (`bot.py:21823`) está antes de `estimate_prob_with_city` (`bot.py:21868`). Cuando
`no_quality_trader_signal_match` dispara, el bot ya tiene `forecast_max` cargado en memoria
(desde `forecast_cache`, poblada al inicio del ciclo). No hay fetch adicional de red.

El coste incremental de captura es únicamente:
- Una llamada a `estimate_prob_with_city` por row (CPU puro, sin red, ~microsegundos).
- Una escritura append a `exact_no_qt_match_evaluations_log_only.jsonl` por row deduplicado.

Con deduplicación por `cycle_id + eval_key`, el volumen real en las últimas 24h sería
≤19 escrituras en 7 ciclos (~2-3 por ciclo). El máximo observado es 12 filas/ciclo (sin
deduplicación); con deduplicación por `qt_match_key`, el máximo efectivo probablemente
sea ≤10 escrituras/ciclo.

**Cap recomendado:** 20 por ciclo (cubre el máximo observado con margen).
Si el volumen excede el cap, aplicar sampling determinista (ver §5).

---

## 3. Cohorte exacta del experimento

La captura LOG_ONLY se activa **solo** cuando se cumplen las tres condiciones simultáneamente:

```
condition == "exact"
AND extras["exact_range_gate_reason"] == "no_quality_trader_signal_match"
AND city_mode in {"active", "canary"}
```

### Incluye

- Mercados `exact` activos y canary sin señal trader en el ciclo actual.
- Pueden incluir mercados que nunca aparecerán en el Gap Report ni en `blocked_signals_resolutions`.
  Esta es una **cohorte de aprendizaje de policy**, no una copia de la cohorte de traders.

### Excluye explícitamente

| Excluido | Motivo |
|---|---|
| `city_mode=shadow` | No es cohorte operativa activa; shadow ya está protegido |
| `city_mode=blocked` | Hard-block por `BLOCKED_CITIES`; `is_city_blocked()` ya impide llegar aquí |
| `exact_range_gate_reason=condition_not_in_quality_trader_gate` | Diferente categoría de filtro |
| `exact_range_gate_reason=city_not_in_quality_trader_whitelist` | Ciudad fuera de whitelist; datos no operativos |
| `condition=range` | Fuera del alcance de este experimento |
| Cualquier ruta `_qt_canary=True` | Esas rutas ya llegan a `estimate_prob_with_city` normalmente |

---

## 4. Artefacto LOG_ONLY

### Nombre del archivo

```
data/exact_no_qt_match_evaluations_log_only.jsonl
```

Este nombre refleja con precisión la cohorte (exact, no QT match), el modo (LOG_ONLY), y la
naturaleza incremental del artefacto. No es "shadow" (captura active+canary) ni necesariamente
"edge positivo" (puede incluir edge bajo o negativo, que también son señal de aprendizaje).

El archivo debe estar en `.gitignore` (datos de producción Railway, no código).

### Schema mínimo (v1)

```jsonc
{
  "schema_version": 1,                         // versión del schema de este artefacto
  "ts_utc": "2026-05-23T16:01:04.370228+00:00",
  "cycle_id": "2026-05-23T16:00",
  "eval_key": "Shanghai|2026-05-24|exact|25|C", // qt_match_key del skip_log; clave de dedup
  "capture_id": "<uuid4>",                      // ID único de esta captura para joins futuros

  // Identidad primaria (si disponible en el momento de captura)
  "market_id": null,                            // puede ser null si no está en el contexto de ciclo
  "condition_id": null,
  "token_id": null,

  // Contexto de mercado
  "city": "Shanghai",
  "city_mode": "active",
  "date_iso": "2026-05-24",
  "days_ahead": 1,
  "condition": "exact",
  "threshold": 25,
  "threshold_high": null,
  "unit": "C",
  "side": null,                                 // null porque no hay decisión de lado

  // Gate
  "qt_gate_reason": "no_quality_trader_signal_match",

  // Evaluación LOG_ONLY
  "our_prob": 0.12,                             // resultado de estimate_prob_with_city
  "mkt_prob": 0.08,                             // mkt_prob_yes o mkt_prob_no según side
  "edge_pct": 4.0,                              // (our_prob - mkt_prob) * 100
  "min_edge_reference": 25.0,                   // MIN_EDGE vigente en el ciclo
  "edge_passes_reference_threshold_log_only": false, // true si edge_pct >= min_edge_reference

  // Contexto de forecast
  "forecast_max": 23.8,
  "sigma_used": 1.9,

  // Fidelidad de fuente (si disponible en el contexto del ciclo, o "unknown")
  "source_fidelity_status": "unknown",

  // Flags de intención
  "log_only": true,
  "execution_authorized": false,

  // Provenance para joins posteriores
  "skip_log_cycle_id": "2026-05-23T16:00",      // mismo que cycle_id, para join con skip_log
  "skip_log_eval_key": "Shanghai|2026-05-24|exact|25|C",  // para join con ledger/outcomes
  "capture_meta": {
    "sampled": false,                            // true si se aplicó sampling por cap
    "cap_active": false                          // true si ciclo alcanzó el cap
  }
}
```

**No usar `would_buy` como campo semántico.** Esta ruta nunca autoriza operación; el campo sería
semánticamente incorrecto y podría confundir revisiones futuras.

---

## 5. Pseudocódigo de inserción futura

El punto exacto de inserción en `bot.py` sería **antes del `continue` en la línea 21864**,
dentro del bloque `if not _qt_canary:`, solo para `no_quality_trader_signal_match`.

```python
# bot.py — línea ~21864 (referencia, NO implementar aún)
if not _qt_canary:
    # ... (logging existente, skip_log_entries.append, etc.)

    # === INSERCIÓN LOG_ONLY (solo cuando env var habilitada) ===
    if (
        os.getenv("LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED", "0") == "1"
        and _qt_gate_reason == "no_quality_trader_signal_match"
        and c.get("city_mode") in {"active", "canary"}
    ):
        try:
            _capture_exact_no_qt_match_eval_log_only(
                cycle_id=cycle_id,
                eval_key=_early_key,
                c=c,
                forecast_max=forecast_max,
                threshold_c=threshold_c,
                threshold_high_c=threshold_high_c,
                sigma_used=sigma_used_val,
                # writer y state pasados como argumento o accedidos por closure
            )
        except Exception:
            pass  # fail-open: error en captura nunca bloquea el ciclo

    continue  # ← NUNCA se mueve ni se elimina este continue
    # === FIN INSERCIÓN ===
```

### Garantías de la inserción futura

1. **Fail-open**: cualquier excepción en `_capture_exact_no_qt_match_eval_log_only` es silenciada
   con `except Exception: pass`. El ciclo principal continúa sin alterar.
2. **`continue` intacto**: la decisión de no ejecutar NO cambia. El `continue` permanece en su
   posición original.
3. **No alter execution**: ningún campo del objeto `c` se modifica, ningún `skip_log_entries`
   extra, ningún `edge_analysis` extra más allá de lo que ya existe.
4. **Solo `no_quality_trader_signal_match`**: otros sub-reasons (`condition_not_in_quality_trader_gate`,
   `city_not_in_quality_trader_whitelist`) quedan excluidos por condición explícita.

---

## 6. Kill-switch y control de coste

### Variable de control

```
LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=0   # por defecto; NO activar sin aprobación Opus
```

El experimento **no está activo** hasta que:
1. Opus revise y apruebe este documento.
2. Pablo autorice la activación explícita.
3. Se implemente el patch en `bot.py` (requiere sesión Codex separada).
4. Se pasen los tests de la §9.

### Deduplicación por ciclo

Dentro de cada ciclo, deduplicar por `cycle_id + eval_key`. Si la misma `eval_key` aparece
múltiples veces en un ciclo (múltiples tokens del mismo mercado), capturar solo la primera
aparición y registrar `deduplicated_count` en métricas del ciclo.

### Cap por ciclo

```
EXACT_NO_QT_MATCH_CAP_PER_CYCLE=20  # cubre el máximo observado (12) con margen
```

Si el ciclo supera el cap, aplicar **sampling determinista**: ordenar por `eval_key` (orden
lexicográfico determinista), tomar los primeros `CAP_PER_CYCLE`, marcar `sampled=true` y
`cap_active=true` en `capture_meta` de las filas incluidas.

### Contadores de ciclo

El writer debe emitir en el log del ciclo (no en Telegram):
```
[exact_no_qt_eval] captured=N deduplicated=M capped=K failed=J
```

Donde:
- `captured`: filas efectivamente escritas en el artefacto
- `deduplicated`: filas omitidas por dedup `cycle_id + eval_key`
- `capped`: filas omitidas por cap del ciclo
- `failed`: excepciones silenciadas

### Monitor de coste/latencia

Medir tiempo de ejecución de `_capture_exact_no_qt_match_eval_log_only` por ciclo. Si la
latencia media supera 50ms por ciclo, escalar `cap_per_cycle` hacia abajo en la siguiente
revisión operativa.

### Rollback

Apagar `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=0` en Railway Railway es suficiente. No se
necesita revertir código. El archivo `exact_no_qt_match_evaluations_log_only.jsonl` existente
queda intacto para análisis offline.

---

## 7. Outcome join y aprendizaje posterior

La captura de este experimento alimenta tres capas:

### 7.1 Market Evidence Ledger

Cada fila capturada puede enriquecerse con outcome cuando el mercado resuelve:
- Join por `eval_key` / `match_key` con `blocked_signals_resolutions.jsonl`.
- Cuando `resolved=true` en BSR para la misma `match_key`, se puede calcular
  `counterfactual_win_rate_no_qt_match` offline.

### 7.2 Trader vs Bot Gap Report

El Gap Report puede incorporar un nuevo consumer derivado que lea
`exact_no_qt_match_evaluations_log_only.jsonl` y añada (ver §10 para diseño futuro):
- `unique_match_keys_captured_log_only`
- `n_edge_above_threshold_log_only`
- breakdown por ciudad/city_mode

Esto complementa el `POLICY_BLOCKED_BEFORE_EDGE_EVALUATION` existente con datos de edge reales.

### 7.3 Learning Review Queue (propuesta)

> **Estado: `READY_FOR_DESIGN` — no implementar todavía.**

Una Learning Review Queue durable consolidaría periodicamente:
- Filas de `exact_no_qt_match_evaluations_log_only.jsonl` con `edge_passes_reference_threshold_log_only=true`.
- Outcomes resueltos joined desde BSR.
- Source fidelity verificada.
- Recomendaciones de revisión Opus cuando la muestra supere umbrales mínimos.

Esta hipótesis se deja como `READY_FOR_DESIGN` hasta tener suficiente muestra capturada
(ver §8, gate T+30).

### Aclaraciones importantes

- **Edge capturado sin outcome fiable no autoriza ninguna conclusión.** El edge LOG_ONLY es
  una señal de aprendizaje, no una señal de trading.
- **Source fidelity debe resolverse** antes de cualquier recomendación estratégica de modificar
  la policy QT gate.
- **Settlement fidelity** continúa pendiente de verificación para la mayoría de las ciudades en
  la cohorte (ver `docs/source_audits/`). Sin settlement fidelity verificado, la tasa de acierto
  contrafactual no es fiable.

---

## 8. Métricas de éxito del experimento

| Métrica | Descripción |
|---|---|
| `n_unique_eval_keys_captured` | Unique `eval_key` capturadas desde inicio del experimento |
| `n_edge_above_threshold_log_only` | Filas con `edge_passes_reference_threshold_log_only=true` |
| `edge_pct_distribution_no_qt_match` | Distribución de `edge_pct`: p10, p25, p50, p75, p90 |
| `comparable_quality_trader_match_edge_distribution` | Edge de la cohorte complementaria (si hay evidencia compatible en BSR) |
| `resolved_outcomes_joined` | Filas con outcome de BSR unido post-resolución |
| `source_fidelity_verified_rate` | Fracción de filas con `source_fidelity_status != "unknown"` |
| `counterfactual_win_rate_no_qt_match` | WR hipotético usando outcome resuelto de BSR (requiere N≥10 resueltos) |
| `cycle_compute_overhead_ms` | ms adicionales por ciclo atribuibles a la captura |
| `capture_error_rate` | `failed / (captured + failed)` |

---

## 9. Gates de decisión posterior

Estos gates son **propuestas para revisión Opus** — no están aprobados:

| Gate | Condición | Acción propuesta |
|---|---|---|
| Revisión anticipada | ≥20 unique eval_keys resueltos con outcome + edge LOG_ONLY | Solicitar revisión Opus antes de T+30 |
| Revisión obligatoria | T+30 = **2026-06-22** | Revisión Opus independientemente de muestra |
| Bloqueo estratégico | `source_fidelity_status="unknown"` para >50% de la muestra | No recomendar cambio de policy QT gate |
| Sin auto-activación | Ningún resultado del experimento autoriza trading automático | Requiere aprobación Opus + Pablo explícitos |

> Nota: T+30 se calcula desde la activación del experimento, no desde la fecha de diseño.
> La fecha 2026-06-22 es referencial basada en activación inmediata hipotética.

---

## 10. Test spec futuro para implementación

Si Opus aprueba este diseño y se autoriza el patch en `bot.py`, Codex/Sonnet deberá cubrir
los siguientes tests **antes de activar la env var**:

### Tests obligatorios

```python
# T1: env var OFF → no captura, ciclo continúa normalmente
def test_no_capture_when_disabled():
    os.environ["LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED"] = "0"
    # simular ciclo con no_qt_match → archivo NO se crea/actualiza

# T2: env var ON + no_qt_match + active → captura LOG_ONLY
def test_captures_when_enabled_active():
    os.environ["LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED"] = "1"
    # city_mode=active, exact_range_gate_reason=no_quality_trader_signal_match
    # → archivo se escribe, log_only=true, execution_authorized=false

# T3: env var ON + no_qt_match + canary → captura LOG_ONLY
def test_captures_when_enabled_canary():
    # city_mode=canary → mismo comportamiento que T2

# T4: blocked/shadow → no captura
def test_no_capture_blocked_shadow():
    # city_mode=blocked → no captura
    # city_mode=shadow → no captura

# T5: otro sub-reason → no captura
def test_no_capture_other_sub_reason():
    # exact_range_gate_reason=condition_not_in_quality_trader_gate → no captura
    # exact_range_gate_reason=city_not_in_quality_trader_whitelist → no captura

# T6: la decisión original NO se modifica
def test_continue_is_preserved():
    # Verificar que la captura LOG_ONLY nunca altera _qt_canary ni emite BUY

# T7: error en writer → fail-open, ciclo continúa
def test_writer_error_is_fail_open(monkeypatch):
    # monkeypatch writer para lanzar IOError → ciclo no lanza, no corrompe estado

# T8: deduplicación dentro del ciclo
def test_dedup_by_eval_key_same_cycle():
    # misma eval_key dos veces en el ciclo → solo un registro escrito

# T9: cap por ciclo
def test_cap_per_cycle_sampling():
    # 25 rows en ciclo con cap=20 → solo 20 escritas, sampled=true en extra, capped=5

# T10: schema completo
def test_schema_required_fields():
    # verificar que todas las claves del schema §4 están presentes

# T11: compatibilidad de join con Ledger
def test_eval_key_joinable_with_skip_log():
    # eval_key del artefacto == qt_match_key del skip_log para el mismo mercado
```

---

## 11. Ajuste futuro del Gap Report

Este ajuste se documenta como parte del **futuro patch de implementación** — no implementar ahora.

Cuando se implemente el patch de `bot.py`, `tools/trader_vs_bot_gap_report.py` deberá leer
opcionalmente `exact_no_qt_match_evaluations_log_only.jsonl` y añadir al summary:

```python
# En summary del gap report (futuro, no implementar ahora)
"exact_no_qt_match_eval_log_only": {
    "unique_match_keys_captured": N,
    "unique_match_keys_with_edge_above_threshold": K,
    "n_unique_match_keys_in_gap_report_also": J,  # intersección con BSR
    "city_breakdown": {...},
    "city_mode_breakdown": {"active": ..., "canary": ...},
}
```

La **clasificación automática** del Gap Report no cambia: `POLICY_BLOCKED_BEFORE_EDGE_EVALUATION`
sigue siendo `POLICY_BLOCKED_BEFORE_EDGE_EVALUATION`. El nuevo campo es informativo adicional,
no reemplaza la clasificación existente.

---

## 12. Veredicto del experimento (post validación)

Una vez aprobado e implementado, el veredicto final se emitirá como uno de:

| Veredicto | Condición |
|---|---|
| `PRE_EDGE_LOG_ONLY_DESIGN_READY_FOR_OPUS_APPROVAL` | Este documento está completo y baseline de volumen/coste está disponible ✓ |
| `PRE_EDGE_LOG_ONLY_DESIGN_BLOCKED_BY_VOLUME_OR_COST` | Si el análisis de coste revelara overhead inaceptable |
| `PRE_EDGE_LOG_ONLY_DESIGN_BLOCKED_BY_DATA_GAP` | Si faltaran campos críticos del schema en el contexto del ciclo |

**Estado actual:** `PRE_EDGE_LOG_ONLY_DESIGN_READY_FOR_OPUS_APPROVAL`

El baseline de volumen confirma que el experimento es viable:
- ~7 filas/ciclo en active/canary (máximo observado: 12)
- ~19 unique eval_keys por día
- Coste de cómputo: CPU puro, sin fetch de red, forecast ya cargado
- Cap de 20/ciclo cubre el máximo histórico con margen
- Rollback instantáneo por env var

---

*Documento generado en sesión 379 (Sonnet, docs-only). No se modificó `bot.py`, no se activó env var,
no se ejecutó trading, no se tocaron BANKROLL, Fase C, city modes, whitelists, thresholds, scheduler,
guards, SL ni ningún path de BUY/SELL/SKIP.*
