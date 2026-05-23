# Design: Exact / No QT Match — LOG_ONLY Edge Evaluation Experiment

**Status:** `DESIGN_CORRECTED — READY_FOR_OPUS_APPROVAL`
**Date:** 2026-05-23
**Session:** 379 (Sonnet, docs-only + Railway read-only) — corrección S379b
**Predecessor verdict:** `DESIGN_PRE_EDGE_LOG_ONLY_LEARNING_EXPERIMENT` (Opus)

---

## 1. Propósito y límites

### Propósito

Existe una cohorte de mercados `condition=exact` que el bot encuentra en ciclos activos y canary, tiene
el forecast cargado en memoria, pero nunca llega a calcular probabilidad ni edge porque el QT gate los
descarta antes por `no_quality_trader_signal_match`. No hay evidencia de si estos mercados habrían
tenido edge positivo o negativo, ni en qué lado: son un **punto ciego de aprendizaje de policy**.

Este experimento captura, en modo **LOG_ONLY**, la probabilidad y edge potencial (en ambos lados YES/NO)
de esos mercados, sin autorizar ninguna operación ni cambiar la policy de entrada.

### Límites estrictos

| Lo que hace | Lo que NO hace |
|---|---|
| Llama `estimate_prob_with_city` para cohorte exacta | Compra, vende, ni se acerca a emitir orden |
| Registra edge en ambos lados YES y NO | No modifica `ALLOWED_CONDITIONS` |
| Identifica `best_side_log_only` sin ejecutarlo | No modifica `QUALITY_TRADER_CONDITIONS` |
| Usa forecast ya disponible en memoria | No agrega ciudades a whitelists ni city modes |
| Emite métricas de captura por ciclo (overhead a validar) | No toca thresholds, BANKROLL, Fase C |
| Permite rollback instantáneo por env var | No escribe en artefactos de trading ni en DB |

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
`no_quality_trader_signal_match` dispara, el bot ya tiene `forecast_max` disponible en `forecast_cache`,
cargada al inicio del ciclo. No hay fetch adicional de red para la llamada de probabilidad.

El coste **esperado** (basado en inspección de código — pendiente de validar con métrica
`cycle_compute_overhead_ms` antes de activar la env var en producción):
- Una llamada a `estimate_prob_with_city` por row capturado (CPU puro, sin red).
- Una escritura append al artefacto por row deduplicado.
- Con deduplicación por `cycle_id + eval_key`, volumen efectivo en las últimas 24h: ≤19 escrituras
  en 7 ciclos (~2-3 únicas por ciclo). Máximo observado sin dedup: 12/ciclo.

**Cap de seguridad:** 20 por ciclo (cubre el máximo observado con margen). No se activa sin
validación de overhead real (ver §6).

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

## 4. Decisión arquitectónica pendiente para Opus

Antes de fijar el artefacto de salida, Opus debe decidir entre dos opciones. Ambas se describen a
continuación con sus implicaciones. Se incluye una **recomendación razonada** al final.

### Opción A: Extender `bot_signal_evaluations.jsonl`

Añadir las nuevas filas al artefacto existente `bot_signal_evaluations.jsonl` con campos
discriminadores:

```jsonc
{
  "evaluation_source": "exact_no_qt_match_log_only",  // distingue de "live_eval"
  "log_only": true,
  "execution_authorized": false,
  // + campos YES/NO del §5
}
```

**Ventajas:**
- Un único artefacto de evaluaciones; sin nueva isla de datos.
- El Gap Report ya lee `bot_signal_evaluations.jsonl`; el enriquecimiento es inmediato.
- Menos superficie de mantenimiento (un writer, un schema versionado).

**Riesgos:**
- El artefacto `bot_signal_evaluations.jsonl` mezcla semánticamente evaluaciones ejecutables
  (`live_eval`) con evaluaciones LOG_ONLY contrafactuales; requiere disciplina de filtrado en
  todos los consumers.
- Un consumer futuro que olvide filtrar por `execution_authorized=false` puede leer filas
  LOG_ONLY como si fueran evaluaciones reales.

### Opción B: Artefacto separado `exact_no_qt_match_evaluations_log_only.jsonl`

Mantener un archivo dedicado, pero con las siguientes exigencias de integración:

1. **Join contractual inmediato** al Market Evidence Ledger por `eval_key` / identidad primaria.
2. **Consumer definido** antes de activar: al menos el Gap Report o un derivado debe leerlo.
3. **Learning Review Queue future hook** documentado (ver §8).
4. **Joins de identidad y outcome** explícitos y cubiertos por tests (ver §5 y §10).

**Ventajas:**
- Aislamiento semántico total: las filas LOG_ONLY no pueden mezclarse accidentalmente con
  evaluaciones ejecutables.
- Schema puede evolucionar sin afectar el schema de `bot_signal_evaluations.jsonl`.
- Más fácil de rotar/limpiar de forma independiente.

**Riesgos:**
- Nueva isla de datos si no se establecen los joins contractuales antes de activar.
- Dos artefactos de evaluaciones con lifecycle de mantenimiento distinto.

### Recomendación

**Opción B con exigencias contractuales cumplidas antes de activar la env var.**

Razón principal: `bot_signal_evaluations.jsonl` contiene evaluaciones que informan decisiones
operativas (el Gap Report ya las une con BSR para calcular `bot_edge_pct_at_signal`). Mezclar
filas `log_only=true` en ese artefacto introduce riesgo de contaminación semántica en consumers
que hoy no filtran por `execution_authorized`. El aislamiento de Opción B es más robusto dado el
tamaño del codebase y los consumers actuales.

El riesgo de isla se mitiga exigiendo, antes de activar, que:
- El Gap Report (o un consumer derivado documentado) lea el artefacto separado.
- Se definan los joins de outcome de §7 con tests de §10.

Opus puede invertir esta recomendación si prefiere la reducción de superficie de Opción A, siempre
que se añada filtrado obligatorio `execution_authorized=true` a todos los consumers de
`bot_signal_evaluations.jsonl`.

---

## 5. Schema del artefacto LOG_ONLY (v1)

Schema aplicable a **Opción B** (artefacto separado). Si Opus elige Opción A, los campos
`evaluation_source`, `log_only` y `execution_authorized` se añaden al schema existente de
`bot_signal_evaluations.jsonl`, y los campos de identidad/edge se alinean con ese schema.

```jsonc
{
  "schema_version": 1,
  "ts_utc": "2026-05-23T16:01:04.370228+00:00",
  "cycle_id": "2026-05-23T16:00",
  "eval_key": "Shanghai|2026-05-24|exact|25|C",   // qt_match_key; clave de dedup
  "capture_id": "<uuid4>",                          // ID único para joins futuros

  // Identidad primaria — se debe capturar al menos uno de los tres;
  // sin al menos condition_id o market_id, la fila no puede resolverse con outcome futuro.
  // Si el contexto del ciclo no provee ninguno, registrar como null y marcar
  // identity_resolvable=false (ver nota de §7).
  "market_id": null,
  "condition_id": null,
  "token_id_yes": null,
  "token_id_no": null,
  "identity_resolvable": false,    // false si todos los ids anteriores son null

  // Contexto de mercado
  "city": "Shanghai",
  "city_mode": "active",
  "date_iso": "2026-05-24",
  "days_ahead": 1,
  "condition": "exact",
  "threshold": 25,
  "threshold_high": null,
  "unit": "C",

  // Gate
  "qt_gate_reason": "no_quality_trader_signal_match",

  // Evaluación LOG_ONLY — ambos lados
  "our_prob_yes": 0.12,             // estimate_prob_with_city(forecast_max, threshold, ...)
  "our_prob_no": 0.88,              // 1.0 - our_prob_yes
  "mkt_prob_yes": 0.08,             // mkt_prob_yes del contexto de ciclo
  "mkt_prob_no": 0.92,              // mkt_prob_no del contexto de ciclo
  "edge_yes_pct": 4.0,              // (our_prob_yes - mkt_prob_yes) * 100
  "edge_no_pct": -4.0,              // (our_prob_no - mkt_prob_no) * 100
  "best_side_log_only": "YES",      // lado con mayor edge positivo; null si ningún lado > 0
  "best_edge_pct_log_only": 4.0,    // edge del mejor lado; null si ambos ≤ 0
  "min_edge_reference": 25.0,       // MIN_EDGE vigente en el ciclo
  "edge_passes_reference_threshold_log_only": false, // true si best_edge_pct >= min_edge_reference

  // Contexto de forecast
  "forecast_max": 23.8,
  "sigma_used": 1.9,

  // Fidelidad de fuente
  "source_fidelity_status": "unknown",  // si disponible en ciclo; "unknown" si no

  // Flags de intención — inmutables, no cambiar en versiones futuras
  "log_only": true,
  "execution_authorized": false,

  // Provenance para joins
  "skip_log_eval_key": "Shanghai|2026-05-24|exact|25|C",
  "capture_meta": {
    "sampled": false,       // true si se aplicó sampling por cap
    "cap_active": false     // true si el ciclo alcanzó el cap antes de esta fila
  }
}
```

**No usar `would_buy`.** Esta ruta nunca autoriza operación; el campo sería semánticamente
incorrecto y podría confundir revisiones futuras.

**Nota sobre identidad:** Si `market_id`, `condition_id`, `token_id_yes` y `token_id_no` son
todos `null` en el contexto del ciclo para una fila, registrar `identity_resolvable=false`.
Las filas con `identity_resolvable=false` no podrán unirse a outcome por identidad primaria
(solo por `eval_key`/`match_key`). Si más del 20% de las filas capturadas tienen
`identity_resolvable=false`, escalar a Opus antes de continuar.

---

## 6. Pseudocódigo de inserción futura

El punto exacto de inserción en `bot.py` sería **antes del `continue` en la línea ~21864**,
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
                min_edge=MIN_EDGE,
            )
        except Exception:
            pass  # fail-open: error en captura nunca bloquea el ciclo

    continue  # ← NUNCA se mueve ni se elimina este continue
    # === FIN INSERCIÓN ===
```

### Garantías de la inserción futura

1. **Fail-open**: cualquier excepción en `_capture_exact_no_qt_match_eval_log_only` es silenciada.
   El ciclo principal continúa sin alterar.
2. **`continue` intacto**: la decisión de no ejecutar NO cambia. El `continue` permanece en su
   posición original.
3. **No alter execution**: ningún campo del objeto `c` se modifica; ningún `skip_log_entries`
   extra; ningún `edge_analysis` extra.
4. **Solo `no_quality_trader_signal_match`**: otros sub-reasons quedan excluidos por condición.

---

## 7. Kill-switch y control de coste

### Variable de control

```
LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=0   # por defecto; NO activar sin aprobación Opus
```

El experimento **no está activo** hasta que:
1. Opus revise y apruebe este documento (incluyendo decisión arquitectónica §4).
2. Pablo autorice la activación explícita.
3. Se implemente el patch en `bot.py` (sesión Codex separada).
4. Se pasen los tests de la §10.
5. Se valide `cycle_compute_overhead_ms` con un smoke ciclo antes de activar en producción.

### Deduplicación por ciclo

Dentro de cada ciclo, deduplicar por `cycle_id + eval_key`. Si la misma `eval_key` aparece
múltiples veces en un ciclo (múltiples tokens del mismo mercado), capturar solo la primera
aparición y registrar `deduplicated_count` en métricas del ciclo.

### Cap por ciclo

```
EXACT_NO_QT_MATCH_CAP_PER_CYCLE=20  # control de seguridad; cubre máximo observado (12)
```

Si el ciclo supera el cap, aplicar **sampling por hash determinista**: usar
`hash(eval_key + cycle_id) % cap_per_cycle` para seleccionar qué filas incluir, preservando
representación proporcional de ciudades. No usar orden lexicográfico por `eval_key` porque puede
sesgar la muestra hacia ciudades cuyo nombre comienza con letras más tempranas en el alfabeto.

Si el volumen sube de forma sostenida por encima del cap, considerar **estratificación por
ciudad/city_mode** antes de aumentar el cap.

### Contadores de ciclo

El writer emite en el log del ciclo (no en Telegram):
```
[exact_no_qt_eval] captured=N deduplicated=M capped=K failed=J overhead_ms=T
```

### Monitor de coste/latencia

Medir tiempo de ejecución del writer completo por ciclo. El coste es **esperado bajo** según
inspección de código (CPU puro, forecast ya cargado), pero **debe validarse** con
`cycle_compute_overhead_ms` antes de activar la env var en producción. Si supera 50ms/ciclo
de forma consistente, reducir el cap o escalar a Opus.

### Rollback

Apagar `LOG_ONLY_EXACT_NO_QT_MATCH_EVAL_ENABLED=0` en Railway es suficiente. No se necesita
revertir código. El archivo capturado queda intacto para análisis offline.

---

## 8. Outcome join y aprendizaje posterior

La cohorte runtime puede incluir mercados que ningún trader monitorizado opere posteriormente.
Por eso se definen **dos vías de resolución de outcome**, con requisitos de identidad distintos:

### Vía 1: Outcome trader-related vía BSR

Para mercados que aparecen en `blocked_signals_resolutions.jsonl`:

- Join por `eval_key` ↔ `match_key` en BSR.
- Cuando `resolved=true` en BSR, usar `outcome`, `win_for_trader`, `close_price`.
- Permite calcular `counterfactual_win_rate_no_qt_match` comparando con la cohorte
  `quality_trader_signal_match` del mismo periodo.
- **Limitación**: solo cubre mercados donde al menos un trader monitorizado tiene posición;
  puede ser una fracción menor de la cohorte capturada.

### Vía 2: Outcome por identidad primaria

Para todos los mercados, independientemente de si hay trader:

- Join por `condition_id` o `market_id` ↔ fuente de resolución Polymarket/Gamma.
- Requiere que al menos uno de `condition_id`, `market_id` sea no-null en la fila capturada.
- Permite calcular `counterfactual_win_rate_no_qt_match` con source fidelity verificable.
- **Requisito de identidad:** si `identity_resolvable=false` para una fila, esa fila
  no puede resolverse por esta vía (ver nota en §5).

**Dato de identidad obligatorio para que el experimento genere aprendizaje útil:**
Al menos `condition_id` o `market_id` debe estar disponible en el contexto del ciclo.
Si la implementación confirma que esos campos no están disponibles en `bot.py` en el punto
de inserción, el patch debe priorizar capturarlos o la utilidad del experimento se limita
a la Vía 1 (solo mercados con traders monitorizados).

### 8.1 Market Evidence Ledger

Cada fila capturada puede enriquecerse con outcome por cualquiera de las dos vías y alimentar
el Ledger como `evaluation_source=exact_no_qt_match_log_only`.

### 8.2 Trader vs Bot Gap Report

El Gap Report puede leer `exact_no_qt_match_evaluations_log_only.jsonl` (futuro, §11) y añadir:
- `unique_match_keys_captured_log_only`
- `n_best_edge_above_threshold_log_only`
- breakdown por ciudad/city_mode

### 8.3 Learning Review Queue (propuesta)

> **Estado: `READY_FOR_DESIGN` — no registrar como artefacto durable todavía.**

Una Learning Review Queue consolidaría periódicamente filas capturadas con
`edge_passes_reference_threshold_log_only=true`, outcomes resueltos por cualquiera de las
dos vías, y source fidelity verificada, emitiendo recomendaciones de revisión Opus cuando
la muestra supere umbrales mínimos.

Se deja como hipótesis `READY_FOR_DESIGN` hasta tener suficiente muestra capturada.

### Aclaraciones

- **Edge capturado sin outcome fiable no autoriza ninguna conclusión.** Es señal de aprendizaje.
- **Source fidelity debe resolverse** antes de cualquier recomendación de cambio de policy QT gate.
- **Settlement fidelity** continúa pendiente para la mayoría de ciudades de la cohorte.

---

## 9. Métricas de éxito del experimento

| Métrica | Descripción |
|---|---|
| `n_unique_eval_keys_captured` | Unique `eval_key` capturadas desde inicio |
| `n_best_edge_above_threshold_log_only` | Filas con `edge_passes_reference_threshold_log_only=true` |
| `edge_yes_pct_distribution` | Distribución de `edge_yes_pct`: p10, p25, p50, p75, p90 |
| `edge_no_pct_distribution` | Distribución de `edge_no_pct` |
| `best_side_distribution` | Frecuencia de `best_side_log_only` en {YES, NO, null} |
| `comparable_qt_match_best_edge_distribution` | Edge del lado ganador en la cohorte `quality_trader_signal_match` del mismo periodo (si hay evidencia compatible en BSR) |
| `identity_resolvable_rate` | Fracción de filas con `identity_resolvable=true` |
| `resolved_outcomes_via_bsr` | Filas con outcome de BSR unido (Vía 1) |
| `resolved_outcomes_via_identity` | Filas con outcome por identidad primaria (Vía 2) |
| `source_fidelity_verified_rate` | Fracción de filas con `source_fidelity_status != "unknown"` |
| `counterfactual_win_rate_no_qt_match` | WR usando lado `best_side_log_only` y outcome resuelto (N≥10 resueltos) |
| `cycle_compute_overhead_ms` | ms adicionales por ciclo (validar antes de activar) |
| `capture_error_rate` | `failed / (captured + failed)` |

---

## 10. Checkpoints y gates de decisión posterior

### Checkpoint Phase 2 (preexistente)

- **Phase 2 T+30 = 2026-06-09** (abierta 2026-05-10; checkpoint oficial ya establecido).
- El experimento LOG_ONLY aquí diseñado no altera Phase 2 ni su checkpoint.
- Si Phase 2 produce un rollback de `QUALITY_TRADER_CONDITIONS` antes de que el experimento
  se active, Opus debe revisar si la cohorte de captura sigue siendo válida.

### Checkpoints propios del experimento (pendiente de aprobación Opus)

| Gate | Condición | Acción propuesta |
|---|---|---|
| Smoke pre-activación | `cycle_compute_overhead_ms` validado en primer ciclo real | Continuar o reducir cap antes de activar completamente |
| Revisión anticipada | ≥20 unique eval_keys resueltos con outcome (cualquiera de las dos vías) + edge LOG_ONLY | Solicitar revisión Opus antes de T+N |
| Revisión obligatoria | Activation_timestamp + 30 días | Revisión Opus independientemente de muestra |
| Bloqueo estratégico | `source_fidelity_status="unknown"` para >50% de la muestra al momento de revisión | No recomendar cambio de policy QT gate |
| Sin auto-activación | Ningún resultado del experimento autoriza trading automático | Requiere aprobación Opus + Pablo explícitos |

> El checkpoint T+N del experimento se calcula desde `activation_timestamp`, que es desconocido
> hasta que Opus/Pablo aprueben la activación. No se usa una fecha absoluta como referencia.
> Si el experimento se activa después de 2026-06-09, Opus debe confirmar si los checkpoints
> del experimento deben coordinarse con los de Phase 2 o correr en paralelo.

---

## 11. Test spec futuro para implementación

Si Opus aprueba este diseño y autoriza el patch en `bot.py`, Codex/Sonnet deberá cubrir los
siguientes tests **antes de activar la env var**:

```python
# T1: env var OFF → no captura, ciclo continúa normalmente
def test_no_capture_when_disabled(): ...

# T2: env var ON + no_qt_match + active → captura LOG_ONLY con ambos lados YES/NO
def test_captures_both_sides_when_enabled_active():
    # city_mode=active, exact_range_gate_reason=no_quality_trader_signal_match
    # → our_prob_yes, our_prob_no, mkt_prob_yes, mkt_prob_no, edge_yes_pct, edge_no_pct presentes
    # → log_only=true, execution_authorized=false

# T3: env var ON + no_qt_match + canary → misma cobertura que T2
def test_captures_when_enabled_canary(): ...

# T4: blocked/shadow → no captura
def test_no_capture_blocked_shadow(): ...

# T5: otro sub-reason → no captura
def test_no_capture_other_sub_reason():
    # condition_not_in_quality_trader_gate → no captura
    # city_not_in_quality_trader_whitelist → no captura

# T6: la decisión original NO se modifica; continue preservado
def test_continue_is_preserved():
    # _qt_canary sigue False; ningún BUY emitido; skip_log inalterado

# T7: error en writer → fail-open, ciclo continúa
def test_writer_error_is_fail_open(monkeypatch): ...

# T8: deduplicación dentro del ciclo
def test_dedup_by_eval_key_same_cycle():
    # misma eval_key dos veces en el ciclo → solo un registro escrito

# T9: cap + hash sampling
def test_cap_per_cycle_hash_sampling():
    # 25 rows con cap=20 → 20 escritas con distribución no-lexicográfica,
    # sampled=true, cap_active=true en capture_meta; 5 omitidas

# T10: schema completo con campos YES/NO
def test_schema_required_fields():
    # nuestro_prob_yes, our_prob_no, mkt_prob_yes, mkt_prob_no,
    # edge_yes_pct, edge_no_pct, best_side_log_only, best_edge_pct_log_only,
    # edge_passes_reference_threshold_log_only, log_only=true, execution_authorized=false

# T11: identity_resolvable cuando ids son null
def test_identity_resolvable_false_when_ids_null():
    # market_id=None, condition_id=None, token_id_yes=None → identity_resolvable=False

# T12: join con skip_log por eval_key
def test_eval_key_joinable_with_skip_log():
    # eval_key == qt_match_key del skip_log para el mismo mercado

# T13: best_side_log_only correcto
def test_best_side_logic():
    # edge_yes > 0 y > edge_no → best_side=YES, best_edge_pct=edge_yes
    # edge_no > 0 y > edge_yes → best_side=NO, best_edge_pct=edge_no
    # ambos ≤ 0 → best_side=null, best_edge_pct=null
```

---

## 12. Ajuste futuro del Gap Report

Documentado como parte del futuro patch de implementación — **no implementar ahora**.

Cuando se implemente el patch de `bot.py`, `tools/trader_vs_bot_gap_report.py` deberá leer
opcionalmente el artefacto LOG_ONLY y añadir al summary (Opción B) o leer desde
`bot_signal_evaluations.jsonl` filtrando por `evaluation_source` (Opción A):

```python
# En summary del gap report (futuro, no implementar ahora)
"exact_no_qt_match_eval_log_only": {
    "unique_match_keys_captured": N,
    "unique_match_keys_best_edge_above_threshold": K,
    "n_unique_match_keys_also_in_bsr": J,   # intersección con BSR
    "city_breakdown": {...},
    "city_mode_breakdown": {"active": ..., "canary": ...},
    "identity_resolvable_rate": 0.0,        # fracción con al menos un id no-null
}
```

La clasificación automática del Gap Report no cambia: `POLICY_BLOCKED_BEFORE_EDGE_EVALUATION`
sigue siendo `POLICY_BLOCKED_BEFORE_EDGE_EVALUATION`.

---

## 13. Veredicto

| Veredicto | Condición |
|---|---|
| `PRE_EDGE_LOG_ONLY_DESIGN_CORRECTED_READY_FOR_OPUS_APPROVAL` | Diseño corregido con baseline real, schema YES/NO, decisión arquitectónica pendiente, checkpoints alineados con Phase 2 ✓ |
| `PRE_EDGE_LOG_ONLY_DESIGN_BLOCKED_BY_VOLUME_OR_COST` | Si validación de overhead revela coste inaceptable |
| `PRE_EDGE_LOG_ONLY_DESIGN_BLOCKED_BY_DATA_GAP` | Si confirmación de implementación revela que `condition_id`/`market_id` no están disponibles en el punto de inserción |

**Estado actual:** `PRE_EDGE_LOG_ONLY_DESIGN_CORRECTED_READY_FOR_OPUS_APPROVAL`

Pendiente de resolución por Opus antes de implementar:
1. Decisión arquitectónica §4: Opción A (extender `bot_signal_evaluations`) o Opción B (artefacto separado).
2. Aprobación de los checkpoints propios del experimento (§10).
3. Confirmación de que `condition_id`/`market_id` son accesibles en el punto de inserción.

---

*Corrección aplicada en sesión 379b (Sonnet, docs-only). No se modificó `bot.py`, no se activó env var,
no se ejecutó trading, no se tocaron BANKROLL, Fase C, city modes, whitelists, thresholds, scheduler,
guards, SL ni ningún path de BUY/SELL/SKIP.*
