# Handoff — condition_reopen_monitor: checkpoint automático + Telegram

**Creado:** 2026-04-14 por Sonnet (Sesión 175)
**Target model:** Sonnet
**Prioridad:** 1 — deadline día 7 (2026-04-21)
**Depende de:** v10.6.15 ya en producción (condition_filtered canary activo)
**Tipo:** Implementación nueva + integración bot

---

## Contexto

El canary de exact/range lleva operando desde 2026-04-14. Hay dos checkpoints comprometidos:
- **Día 7 — 2026-04-21**: si WR bot < 50% con n ≥ 15 → cerrar canary
- **Día 14 — 2026-04-28**: decisión final (promover / extender / cerrar)

Sin un monitor automático, estos checkpoints son ciegos. Este handoff crea el monitor
y lo integra en el ciclo del bot para que dispare Telegram automáticamente con una
instrucción lista para pegar a Sonnet/Codex.

---

## Patrón de trabajo requerido (IMPORTANTE)

Pablo trabaja en sesiones discretas. El aviso de Telegram debe incluir:
1. Métricas claras (WR, n, por ciudad)
2. Veredicto automático (continuar / alerta / kill-switch)
3. Bloque de texto listo para iniciar una sesión Sonnet/Codex sin contexto adicional

Ejemplo de mensaje Telegram esperado:
```
📊 Checkpoint condition_filtered — Día 7

WR: 8/12 = 66.7% | Estado: ✅ OK
Ciudades: Seoul 3/4, Tokyo 2/2, Milan 1/3...
Kill-switch: NO (necesita n≥20, actual n=12)

▶️ Próximo checkpoint: 2026-04-28

Para sesión Sonnet:
Leer docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md.
WR actual exact/range = 66.7% (n=12). Checkpoint día 7 OK.
Acción: continuar canary sin cambios. Actualizar CONTEXTO.md con métricas.
```

O si requiere acción:
```
⚠️ ALERTA condition_filtered — Día 7

WR: 5/15 = 33.3% | Estado: ⚠️ BAJO THRESHOLD

Para sesión Sonnet:
Leer docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md y
docs/handoffs/condition-filtered-canary-implement-2026-04-14.md.
WR exact/range = 33.3% (n=15) < 50% threshold día 7.
Acción requerida: cerrar canary. Revertir QUALITY_TRADER_CONDITIONS a vacío
en Railway y actualizar CONTEXTO.md.
```

---

## Qué construir

### 1. `tools/condition_reopen_monitor.py` (standalone, read-only)

Script que puede correr tanto manualmente como invocado por el bot.

**Inputs:**
- `data/trade_lifecycle.jsonl` o `data/postmortem.jsonl` — para trades reales del bot
- Filtro: trades con `condition in {exact, range}` y fecha ≥ 2026-04-14

**Outputs (stdout + retorno estructurado):**
```
WR: X/N = Y%
Por ciudad: Seoul X/N (Y%), Tokyo X/N (Y%), ...
Kill-switch: SÍ/NO (threshold: WR<45% n≥20)
Veredicto día 7: OK / ALERTA / KILL-SWITCH
```

**Criterios de decisión (del handoff Opus):**
| Checkpoint | Umbral | Acción |
|------------|--------|--------|
| Día 7 (2026-04-21) | WR < 50% con n ≥ 15 | Cerrar canary |
| Día 7 | WR 50-70% | Continuar con alerta |
| Día 7 | WR ≥ 70% | Continuar sin cambios |
| Día 14 (2026-04-28) | WR ≥ 55% con n ≥ 30 | Promover (quitar EXACT_RANGE_SIZE_SCALE) |
| Día 14 | WR 50-55% | Extender 14 días más |
| Día 14 | WR < 50% | Cerrar canary |
| Kill-switch (cualquier día) | WR < 45% con n ≥ 20 rolling | Cerrar inmediatamente |

### 2. Integración en `bot.py` — `maybe_run_condition_monitor(state)`

Función nueva a añadir al ciclo del bot. Patrón: igual a `maybe_alert_v2_trigger` o `notify_active_candidates`.

**Cuándo dispara:**
- Una vez al día (primer ciclo del día), desde el día 7 del canary en adelante
- Siempre que kill-switch se active (WR < 45% con n ≥ 20)
- Fechas de checkpoint exactas: 2026-04-21 y 2026-04-28

**Lógica de disparo:**
```python
CANARY_OPEN_DATE = date(2026, 4, 14)
days_since = (date.today() - CANARY_OPEN_DATE).days

if days_since < 7:
    return  # demasiado pronto

# Checkpoints forzados
is_checkpoint = date.today() in [date(2026, 4, 21), date(2026, 4, 28)]

# Kill-switch siempre activo
stats = run_condition_monitor()
kill = stats["wr"] < 0.45 and stats["n"] >= 20

if not (is_checkpoint or kill):
    return  # no es día de checkpoint ni kill-switch

# Enviar Telegram con métricas + instrucción Sonnet
send_telegram(build_checkpoint_message(stats, is_checkpoint, kill))
```

**Anti-spam:** un solo envío por fecha de checkpoint (guardar en `bot_state["last_condition_checkpoint"]`).

### 3. Mensaje Telegram — `build_checkpoint_message(stats, is_checkpoint, kill)`

El mensaje debe incluir SIEMPRE el bloque de instrucción para Sonnet/Codex.

**Templates:**

Kill-switch activo:
```
🚨 KILL-SWITCH condition_filtered

WR bot exact/range: {wr_pct}% ({wins}/{n})
Threshold: <45% con n≥20 → CUMPLIDO

Para sesión Sonnet/Codex:
Leer docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md
WR={wr_pct}% n={n} → kill-switch activado.
Acción urgente: setear QUALITY_TRADER_CONDITIONS="" en Railway
y actualizar CONTEXTO.md sección "Condition filtered reopen".
```

Checkpoint OK (continuar):
```
✅ Checkpoint condition_filtered — Día {days}

WR bot exact/range: {wr_pct}% ({wins}/{n})
Ciudades: {city_breakdown}
Estado: {status_text}

Próximo checkpoint: {next_date}

Para sesión Sonnet (no urgente):
Leer docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md
WR={wr_pct}% n={n} en día {days}. Estado: {status}.
Acción: actualizar CONTEXTO.md con métricas actuales. Sin cambios en Railway.
```

Checkpoint con alerta (acción requerida):
```
⚠️ Checkpoint condition_filtered — Día {days}

WR bot exact/range: {wr_pct}% ({wins}/{n})
Estado: {status_text}

Para sesión Sonnet:
Leer docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md y
docs/handoffs/condition-filtered-canary-implement-2026-04-14.md
WR={wr_pct}% n={n} → {accion_requerida}.
Acción: {instruccion_exacta_railway}
```

---

## Cómo identificar trades exact/range del bot

Buscar en `trade_lifecycle.jsonl` o `postmortem.jsonl`:
```python
# Filtro: trades reales (no shadow) con condition exact o range desde apertura canary
trades = [
    t for t in all_trades
    if t.get("condition") in {"exact", "range"}
    and t.get("date", "") >= "2026-04-14"
    and t.get("mode") != "shadow"  # ajustar según schema real
]
```

**Antes de implementar: verificar el schema real** leyendo 5-10 registros de
`data/postmortem.jsonl` y `data/trade_lifecycle.jsonl` para confirmar qué campo
contiene `condition`, `result`, y cómo distinguir trades reales de shadow.

---

## Archivos a leer antes de implementar

1. `docs/handoffs/condition-filtered-canary-implement-2026-04-14.md` — criterios completos Opus
2. `data/postmortem.jsonl` — schema de trades resueltos (5-10 líneas)
3. `data/trade_lifecycle.jsonl` — schema de trades (5-10 líneas)
4. `bot.py` — función `maybe_alert_v2_trigger` y `notify_active_candidates` como patrón
5. `tools/blocked_signals_settlement_tracker.py` — patrón de script standalone

---

## No hacer

- No modificar criterios de trading, Kelly, NOAA, thresholds canary→active
- No tocar `ALLOWED_CONDITIONS` ni la lógica de condición que ya está en v10.6.15
- No cerrar el canary automáticamente — solo notificar. Pablo decide y ejecuta en Railway.
- No eliminar la instrucción Sonnet del mensaje Telegram — es el patrón requerido

---

## Criterios de éxito

1. `python tools/condition_reopen_monitor.py` corre sin args y muestra WR actual
2. Bot integra `maybe_run_condition_monitor(state)` y lo llama en el ciclo diario
3. Test en `verify_before_deploy.py`: función definida + lógica de checkpoint presente
4. `CONTEXTO.md` actualizado con: fecha apertura canary, próximos checkpoints, referencia al monitor
5. `HISTORIAL_SESIONES.md` actualizado con sesión 175 (pendiente de esta sesión también)
