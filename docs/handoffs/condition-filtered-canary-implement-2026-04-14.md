# Handoff — Implementación canary condition_filtered (trader-gate + edge buffer + kill-switch)

**Creado:** 2026-04-14 por Opus (Sesión 175)
**Target model:** Sonnet
**Prioridad:** 1
**Depende de:** Decisión ya tomada — solo ejecución
**Tipo:** Implementación + deploy

---

## Contexto

Opus decidió reabrir `condition_filtered` para `exact` y `range` con un canary acotado.
Datos base: 59 resoluciones reales de quality traders → WR=76.3% (umbral era ≥55% en n≥50).

Handoff de diseño original: `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md`
Baseline WR: `docs/blocked-signals-wr-baseline-2026-04-13.md`

---

## Decisión de Opus: Opción B modificada

Reabrir `exact` y `range` **NO globalmente**, sino con triple gate:
1. Trader ∈ quality_traders (presentes en signals.json)
2. Ciudad ∈ whitelist canary (9 ciudades)
3. Edge ≥ MIN_EDGE + 5pp

Sizing efectivo: `CANARY_POSITION_SCALE × EXACT_RANGE_SIZE_SCALE = 0.5 × 0.5 = 25%` del normal.

---

## Cambios a implementar

### 1. bot.py — 3 nuevas env vars

```python
# Junto a ALLOWED_CONDITIONS (línea ~222)
QUALITY_TRADER_CONDITIONS = {
    c.strip().lower()
    for c in os.getenv("QUALITY_TRADER_CONDITIONS", "exact,range").split(",")
    if c.strip()
}
QUALITY_TRADER_CITIES_WHITELIST = {
    c.strip()
    for c in os.getenv(
        "QUALITY_TRADER_CITIES_WHITELIST",
        "Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan"
    ).split(",")
    if c.strip()
}
MIN_EDGE_EXACT_RANGE_BUFFER_PP = float(os.getenv("MIN_EDGE_EXACT_RANGE_BUFFER_PP", "5.0"))
EXACT_RANGE_SIZE_SCALE = float(os.getenv("EXACT_RANGE_SIZE_SCALE", "0.50"))
```

### 2. bot.py — lógica condition gate (línea ~14328)

Reemplazar el skip binario actual por lógica de tres vías:

```python
# ANTES (skip binario):
if signal.condition not in ALLOWED_CONDITIONS:
    skip(reason="condition_filtered")
    continue

# DESPUÉS (tres vías):
if signal.condition in ALLOWED_CONDITIONS:
    pass  # normal pipeline
elif (
    signal.condition in QUALITY_TRADER_CONDITIONS
    and signal.trader in quality_traders
    and signal.city in QUALITY_TRADER_CITIES_WHITELIST
):
    # pasa con flag para edge buffer + size scale aguas abajo
    signal._exact_range_canary = True
else:
    skip(reason="condition_filtered")
    continue
```

### 3. bot.py — edge mínimo diferenciado

Donde se calcula el edge mínimo para el filtro de entrada:

```python
effective_min_edge = MIN_EDGE
if getattr(signal, "_exact_range_canary", False):
    effective_min_edge = MIN_EDGE + MIN_EDGE_EXACT_RANGE_BUFFER_PP / 100
```

### 4. bot.py — sizing diferenciado

Donde se calcula `position_size`:

```python
if getattr(signal, "_exact_range_canary", False):
    position_size *= EXACT_RANGE_SIZE_SCALE
```

### 5. tools/condition_reopen_monitor.py (nuevo, read-only)

Script standalone que lee `trade_log.jsonl` (o equivalente), filtra trades con
condition ∈ {exact, range}, calcula WR rolling y emite alerta si WR < 45% con n ≥ 20.
Correr manualmente los días de checkpoint.

### 6. verify_before_deploy.py — 4 aserciones nuevas

```python
# 1. exact/range se salta cuando trader NO es quality
assert bot skips signal(condition="exact", trader="Unknown-Trader", city="Seoul")

# 2. exact/range pasa cuando trader ES quality y ciudad EN whitelist
assert bot processes signal(condition="exact", trader="Entire-Hood", city="Seoul")

# 3. London sigue bloqueado aunque trader sea quality
assert bot skips signal(condition="exact", trader="Entire-Hood", city="London")

# 4. Sizing = base × CANARY_POSITION_SCALE × EXACT_RANGE_SIZE_SCALE para exact/range
assert position_size(condition="exact") == base_size * 0.5 * 0.5
```

### 7. CONTEXTO.md — sección nueva

```
## Condition filtered reopen (canary activo desde 2026-04-14)
- Condiciones: exact, range (solo quality traders + whitelist ciudades)
- Ciudades whitelist: Seattle, Tokyo, Hong Kong, Seoul, Toronto, Chengdu, Shenzhen, Shanghai, Milan
- Ciudades excluidas: London (WR 33% n=3, revisar tras n≥10)
- Traders elegibles: Entire-Hood, Thrifty-Original, Dimpled-Boy, Loyal-Aggression, Pricey-Score
- Edge buffer: MIN_EDGE + 5pp para exact/range
- Sizing: 25% del normal (canary 0.5 × exact_range 0.5)
- Kill-switch: WR < 45% con n≥20 → revertir a bloqueo total
- Checkpoint día 7: 2026-04-21
- Checkpoint día 14: 2026-04-28
- Decisión tomada por: Opus sesión 175, datos analizados por Sonnet sesión 174-175
```

---

## Variables Railway a setear en el deploy

```
QUALITY_TRADER_CONDITIONS=exact,range
QUALITY_TRADER_CITIES_WHITELIST=Seattle,Tokyo,Hong Kong,Seoul,Toronto,Chengdu,Shenzhen,Shanghai,Milan
MIN_EDGE_EXACT_RANGE_BUFFER_PP=5.0
EXACT_RANGE_SIZE_SCALE=0.50
```

**NO modificar**: `ALLOWED_CONDITIONS`, `MIN_EDGE`, `CANARY_POSITION_SCALE`, Kelly, NOAA, scheduler.

---

## Whitelist ciudades y racional

| Ciudad | WR observado | n | Estado |
|--------|-------------|---|--------|
| Seattle | 100% | 3 | ✓ whitelist |
| Tokyo | 100% | 3 | ✓ whitelist |
| Hong Kong | 100% | 3 | ✓ whitelist |
| Seoul | 75% | 4 | ✓ whitelist |
| Toronto | 75% | 4 | ✓ whitelist |
| Chengdu | 66.7% | 3 | ✓ whitelist |
| Shenzhen | 66.7% | 3 | ✓ whitelist |
| Shanghai | 66.7% | 3 | ✓ whitelist |
| Milan | 66.7% | 3 | ✓ whitelist (vigilar: riesgo estación única Europa) |
| **London** | **33.3%** | **3** | **✗ excluida — revisar tras n≥10** |

---

## Checkpoints

### Día 7 — 2026-04-21
Correr `tools/condition_reopen_monitor.py`:
- WR ≥ 70% (n ≥ 15): continuar sin cambios
- WR 50–70%: continuar con alerta, no aumentar sizing
- WR < 50% (n ≥ 15): **cerrar canary — revertir ALLOWED_CONDITIONS**

### Día 14 — 2026-04-28
Decisión final:
- WR ≥ 55% (n ≥ 30): promover — quitar `EXACT_RANGE_SIZE_SCALE`, mantener trader-gate y edge buffer
- WR 50–55%: extender canary 14 días más, no aumentar sizing
- WR < 50%: cerrar — congelar exact/range 3+ meses

### Kill-switch automático
Si en cualquier momento WR < 45% con n ≥ 20 en ventana rolling → revertir sin esperar checkpoint.

---

## Caveats registrados por Opus (para análisis futuro)

1. **Concentración temporal**: 69% de señales de un solo día (2026-04-13). Posible régimen favorable, no skill persistente.
2. **Range n=8 WR 100%**: muestra insuficiente. Si se quiere mayor conservadurismo, usar +7pp para `range` en vez de +5pp.
3. **Gap bot vs traders**: si WR-bot < WR-traders por más de 20pp → investigar exit timing, resolución, slippage antes de promover.
4. **Milan**: vigilar como ciudad europea de estación única (mismo riesgo que London en principio).
5. **Sesgo look-ahead**: las 59 resoluciones son señales ya resueltas. WR podría estar inflado por selección.

---

## No hacer

- No abrir London hasta n ≥ 10 (requiere handoff separado)
- No abrir condiciones fuera de exact/range
- No quitar CANARY_POSITION_SCALE global mientras el canary esté activo
- No extrapolar a quality traders no observados en el sample exact/range

---

## Criterios de éxito de esta sesión de implementación

1. `verify_before_deploy.py` pasa sin errores (incluyendo las 4 aserciones nuevas)
2. Las 3 env vars nuevas están seteadas en Railway
3. Bot corriendo en Railway con logs mostrando señales exact/range procesadas (no skipeadas) para ciudades whitelist
4. `CONTEXTO.md` actualizado con la sección canary
5. Commit con mensaje descriptivo referenciando la decisión de Opus
