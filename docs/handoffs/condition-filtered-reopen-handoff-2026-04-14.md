# Handoff — Reapertura condition_filtered: diseño guardrails

**Creado:** 2026-04-14 por Sonnet (Sesión 174)
**Target model:** Opus
**Prioridad:** 1 — mayor ROI disponible ahora mismo (bloquea 81% de señales quality traders)
**Depende de:** análisis Sesión 174 completado — datos ya están, solo falta diseño

---

## Contexto y decisión previa

`condition_filtered` fue cerrado en Sesión 160 como política deliberada: el bot solo opera
`at_or_above` y `at_or_below`. Fundamento original: "pérdidas propias en exact/range".
Gate para reabrir: "datos nuevos con WR≥55% en n≥30".

## Datos actuales (Sesión 174 — 2026-04-14)

Tool `tools/blocked_signals_settlement_tracker.py` corrida con Polymarket API fresca:

| Métrica | Valor |
|---------|-------|
| N total | 59 |
| WR overall | **76.3%** |
| exact (n=51) | 72.5% |
| range (n=8) | 100.0% |
| Consenso (n=9) | 66.7% |
| Solo (n=50) | 78.0% |

Ciudades con n≥3 y WR:
- Seattle / Tokyo / Hong Kong: 100%
- Seoul / Toronto: 75%
- Chengdu / Shenzhen / Shanghai / Milan: 66.7%
- **London: 33.3% (1/3) — outlier**

Threshold oficial: WR≥55%, n≥50 robusto. **Cumplido: 76.3% en n=59.**

Full data en `data/runtime_import_derived/blocked_signals_resolutions.jsonl` (gitignored).

## Lo que YA existe en el código

`ALLOWED_CONDITIONS` es un env var en `bot.py:222`:

```python
ALLOWED_CONDITIONS = {
    condition.strip().lower()
    for condition in os.getenv("ALLOWED_CONDITIONS", "at_or_above,at_or_below").split(",")
    if condition.strip()
}
```

El filtro se aplica en `bot.py:14328`. El cambio mínimo es agregar `exact,range` a esa env var
en Railway — **una línea, cero código nuevo**. Pero antes de hacerlo Opus debe decidir:

## Preguntas de diseño que Opus debe resolver

### 1. ¿Global vs quality-trader-only?

**Opción A — Global:** `ALLOWED_CONDITIONS=at_or_above,at_or_below,exact,range`. El bot opera
cualquier señal exact/range si el edge y el precio pasan los filtros normales.

**Opción B — Quality-trader-gated:** solo opera exact/range si el signal viene de un quality
trader (ya presente en `signals.json`). Requiere ~10 líneas nuevas en el scan loop para
cruzar condition + trader antes del filtro. Más complejo, más conservador.

**Datos para decidir:** el sample de 59 es de quality traders. No tenemos datos del bot propio
en exact/range (las "pérdidas originales" que cerraron el filtro). Si el bot puede generar
señales exact/range sin que un quality trader las confirme, ¿son confiables?

### 2. ¿Qué hacer con London?

London tiene WR=33.3% (1 win, 2 losses) en el sample. Las pérdidas son:
- `London|2026-04-13|exact|13|C` — outcome No, close 0.0
- `London|2026-04-13|exact|15|C` — outcome Yes, close 0.0

¿Excluir London de condition_filtered_reopen hasta n≥10? ¿O confiar en WR global y dejar
que el edge mínimo proteja?

### 3. ¿Edge mínimo diferenciado para exact/range?

Los filtros actuales son `MIN_EDGE` (global) y el Kelly sizing normal. Exact/range son
condiciones más precisas — el mercado puede tener baja liquidez y alta volatilidad de precio
cerca de la resolución. ¿Debe aplicarse un `MIN_EDGE_EXACT_RANGE` más alto? ¿O suficiente
con el `MIN_EDGE` normal más el filtro de calidad del trader?

### 4. ¿Qué ciudades primero?

El handoff B original decía "1 ciudad canary, experimento mínimo". Pero con 10 ciudades
mostrando WR>66% y el sistema ya en modo canary global (all trading es canary sizing),
¿justifica abrir para todas las canary? ¿O restringir a las ciudades con n≥3 y WR≥70%?

### 5. ¿Cuándo revisar?

Proponer una fecha de revisión (ej. 7 días post-apertura) para analizar si el WR del bot
en exact/range confirma el WR de los quality traders, o si hay divergencia.

## Guardrails ya en producción (no rediseñar)

- Canary sizing: `CANARY_POSITION_SCALE=0.50` — las posiciones son 50% del tamaño normal
- `MIN_EDGE` global protege contra señales de bajo margen
- `price_out_of_range` filtra mercados ilíquidos (mkt_prob < threshold)
- `condition_filtered` está en `skip_log.jsonl` — si se abre el filtro, los skips desaparecen
  y la señal entra en el pipeline normal (edge → Kelly → order)

## Entregable esperado de Opus

Un diseño de 1-2 páginas con:
1. Decisión: Opción A (global) vs B (quality-trader-gated) con justificación
2. Respuesta a cada pregunta de diseño (London, edge mínimo, ciudades, fecha revisión)
3. La línea exacta de cambio en Railway (env var) + cualquier código nuevo si Opción B
4. Test checklist para `verify_before_deploy.py`
5. Nota sobre `CONTEXTO.md`: qué escribir cuando se implemente

## No hacer en la sesión Opus

- No implementar el cambio (diferir a Sonnet limpia tras el diseño)
- No tocar `MIN_EDGE`, `CANARY_POSITION_SCALE`, Kelly, NOAA, scheduler
- No rediseñar `sync_city_policy_state()` ni thresholds canary→active
- No correr el tracker tool de nuevo (ya tiene n=59, suficiente para la decisión)

## Archivos relevantes

- `bot.py:222` — `ALLOWED_CONDITIONS` env var
- `bot.py:14327-14361` — filtro condition_filtered en scan loop
- `data/runtime_import_derived/blocked_signals_resolutions.jsonl` — 59 registros (gitignored, leer via Railway SSH si necesario)
- `docs/blocked-signals-wr-baseline-2026-04-13.md` — baseline WR actualizado
- `docs/next-session-handoff-2026-04-13-B-blocked-settlement.md` — handoff original Opus (contexto histórico)
