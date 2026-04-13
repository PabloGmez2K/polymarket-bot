# Handoff — Canary → Active Automation (v1)

**Creado:** 2026-04-13 (Sesión 172, Opus)
**Destinatario:** Sesión limpia Sonnet
**Versión objetivo:** v10.6.14
**Scope:** v1 (Bloques 1+2+4) + V2 Trigger Alarm + Auto-degradación active→canary
**Deferido a v2:** Bloques 3 (corroboración externa) + 5 (gate global post-recalibración)

---

## 0. Resumen ejecutivo

Se añaden tres módulos a `bot.py`, siguiendo el patrón ya probado de
`maybe_run_daily_crosscheck` (v10.6.12) y `maybe_run_blocked_signals_check`
(v10.6.13):

1. **`notify_active_candidates(state)`** — evalúa ciudades canary y envía Telegram
   persistente cuando una cumple los criterios para Active. El usuario aplica el
   cambio en Railway manualmente; el bot detecta la acción y silencia la alerta.

2. **`maybe_run_active_degradation(state)`** — auto-degrada ciudades Active a
   Canary cuando su performance cae bajo umbral. Automático, avisa por Telegram,
   no requiere acción del usuario.

3. **`maybe_alert_v2_trigger(state)`** — alarma one-shot que detecta cuando las
   condiciones para habilitar v2 (Bloques 3+5) se cumplen y envía instrucción
   copiable. Pablo no debe recordar cuándo revisitar v2: el bot se lo recuerda.

**Decisión arquitectónica clave:** no se toca `sync_city_policy_state()` para la
promoción canary→active. El gate shadow→canary sigue intacto. La promoción a
Active sigue siendo manual vía env var Railway (`ACTIVE_TRADING_CITIES`). La
automatización opera **solo en la notificación y en la degradación**.

---

## 1. Contexto (para arrancar la sesión Sonnet sin leer todo el repo)

**Estado del bot al cerrar sesión 172:**

- `ACTIVE_TRADING_CITIES=NONE` en Railway desde 2026-04-13 (sesión 169 cont.).
- 7 ciudades en `auto_canary_cities`: Atlanta, London, Munich, NYC, Seoul,
  Shanghai, Tokyo.
- Bot pausado en shadow-only desde 2026-04-04 por colapso de modelo (16.5% WR en
  91 trades). Recalibración Phase 2 (Opus) pendiente.
- Ninguna ciudad tiene todavía evidencia canary suficiente (n=1 en los mejores
  casos). El sistema está diseñado para **esperar evidencia real** antes de
  promover — no para promover pronto.

**Por qué B (notificación) y no auto-promoción:**

- Bankroll real = $25. Una promoción errónea a Active borra semanas de trabajo.
- El modelo está en recalibración; pedirle al modelo que se autopromueva es
  recursión de riesgo.
- Asimetría: degradar = menos exposición = seguro auto; promover = más
  exposición = merece pausa humana.
- La memoria del sistema (checkpoint 2026-04-11) dice textualmente: *"Saltar
  directo a monetización... sería el anti-patrón que el LEAN roadmap vino a
  evitar."*

**Por qué NO dry-run:**

Pablo decidió activar Telegram directo. Esto se acepta porque los criterios
v1 son conservadores (n=5, WR=60%, PnL=+$1) y porque las salvaguardas anti-spam
(rate limit 24h + revocación automática) protegen contra falsas alarmas
repetitivas.

**Nota operativa de volumen (recurrente de Pablo):**

El bot tiene throughput bajo (~1 trade canary/semana por ciudad). Este módulo
ayuda indirectamente: desbloquea promociones a Active cuando hay evidencia, lo
que sube el sizing. Pero el problema de fondo (scan loop filtra demasiado) es
paralelo y no se resuelve aquí. Mencionarlo en el backlog post-sesión.

---

## 2. Criterios v1 (Bloques 1+2+4) — NÚMEROS CONGELADOS

Los cuatro números de abajo están congelados para v1. **No cambiar sin pedirle
a Pablo y documentar nuevo fundamento.** El razonamiento completo vive en la
sesión 172.

### Bloque 1 — Historial propio canary

| Condición | Umbral | Fundamento corto |
|---|---|---|
| `canary_trades_post_promotion >= N` | **5** | Mínimo donde WR≥60% es alcanzable con ≥1 pérdida; alcanzable en ~5 semanas al ritmo actual. |
| `win_rate >= X%` | **60.0** | Margen claro sobre break-even (~50%); protege contra modelos con edge débil. |
| `pnl_acumulado >= Y USD` | **+1.00** | Recupera ≥1 pérdida completa canary neta. |
| `days_since_promotion >= Z` | **7** | Al menos un ciclo semanal completo y varios regímenes meteorológicos. |

Trades contados: solo `trade_lifecycle` records con `opened_at >= promoted_at`
de la ciudad (mismo criterio que ya usa
`docs/canary-to-active-readiness-2026-04-12.md`).

### Bloque 2 — Integridad de datos (gate de seguridad)

Todas deben ser true para TODOS los trades canary contados:

- `integrity.analysis_ready == True`
- No inconsistencia tipo Atlanta: si `close_context.close_action == "LOSS_TOTAL"`
  pero el `timeline` del mismo record contiene `RESOLVED_WIN` con `pnl_cash > 0`
  y `post_exit_analysis.market_seen_after_close == True` con precio ≥ 0.95,
  marcar la ciudad como `integrity_inconsistent` y **NO alertar**.
- Patrón de detección exacto documentado en
  `docs/atlanta-lifecycle-inconsistency-2026-04-12.md`.

Si Bloque 2 falla, incluir la ciudad en el log interno de `integrity_blocked`
pero no mandar Telegram. Evita que Pablo reciba una alerta sobre una ciudad
cuyo WR es no-confiable.

### Bloque 4 — Anti-flapping

- Ciudad NO debe tener entrada en `transition_history` con `to == "shadow"`
  dentro de los últimos 14 días (revisar `city_policy_state.transition_history`).
- Ciudad NO debe estar en `auto_blocked_cities`.

### Bloques 3 y 5 — DEFERIDOS A V2

No implementar en esta sesión. Están documentados en §6 para cuando v2 arranque.

---

## 3. Módulo 1 — `notify_active_candidates(state)`

### 3.1 Patrón a copiar

Este módulo sigue **exactamente** el mismo patrón que
`notify_canary_candidates(state)` en `bot.py` (búscalo — ya existe). Sigue las
mismas convenciones: idempotencia vía `alerts_state[...]`, retorna `True` si
mutó el state, función aparte para computar candidatos.

### 3.2 Contrato

```python
def notify_active_candidates(state: dict) -> bool:
    """
    Evalúa ciudades en auto_canary_cities y detecta cuáles cumplen los criterios
    v1 para ser promovidas manualmente a Active.

    Envía Telegram cuando:
    - Nueva candidata detectada (primera vez que cumple criterios).
    - Candidata sigue cumpliendo y han pasado >= 24h desde último aviso
      (recordatorio persistente).

    Revoca (envía aviso de revocación + borra entry) cuando:
    - Candidata ya no cumple criterios.

    Silencia cuando:
    - Pablo aplicó el cambio: la ciudad aparece en el env var
      ACTIVE_TRADING_CITIES leído con os.getenv() en runtime.

    Returns True si mutó state (caller persiste).
    """
```

### 3.3 State shape

```python
state.setdefault("active_candidate_notified", {})
# Estructura por ciudad:
{
    "Tokyo": {
        "first_notified_at": "2026-04-20T10:00:00+00:00",
        "last_notified_at": "2026-04-21T10:00:00+00:00",
        "trades": 7,
        "win_rate": 71.4,
        "pnl": 2.34,
        "days_since_promotion": 12
    }
}
```

### 3.4 Fuentes de datos

- `load_city_policy_state()` → `auto_canary_cities` + `transition_history` (ya existentes).
- `load_audit_data()` y/o `trade_lifecycle.json` → trades canary post-promoción.
- `os.getenv("ACTIVE_TRADING_CITIES", "")` parseado a set → detección de acción del usuario.

### 3.5 Telegram — mensaje nueva candidata

```
🚀 <b>Ciudad lista para Active</b>
{city} cumple todos los criterios canary → active.

Evidencia canary (desde {promoted_at_date}):
• Trades: {trades} ({wins}W / {losses}L) — WR {win_rate:.1f}%
• PnL acumulado: ${pnl:+.2f}
• Mejor edge: {best_edge:.1f}%
• Días en canary: {days}
• Integridad de datos: OK ✓

Para activar en Railway aplicar exactamente:
<code>ACTIVE_TRADING_CITIES={current_cities}{,if_any},{city}</code>

Mientras no apliques el cambio, este aviso se repetirá cada 24h.
Si los criterios dejan de cumplirse, te llegará aviso de revocación.
```

Donde `{current_cities}` se construye leyendo `os.getenv("ACTIVE_TRADING_CITIES", "")`
y filtrando "NONE" (si el env dice "NONE", empezar desde vacío).

### 3.6 Telegram — mensaje recordatorio (24h después)

```
🔔 <b>Recordatorio — {city} sigue lista para Active</b>
Han pasado 24h desde el primer aviso y los criterios siguen cumpliéndose.

Evidencia actualizada:
• Trades: {trades} — WR {win_rate:.1f}% — PnL ${pnl:+.2f}

Env var para aplicar:
<code>ACTIVE_TRADING_CITIES={current_cities}{,if_any},{city}</code>
```

### 3.7 Telegram — mensaje revocación

```
🚫 <b>{city} ya no cumple criterios para Active</b>
Razón: {reason}
(WR cayó a {win_rate:.1f}% / PnL ${pnl:+.2f} / n={trades})

La candidatura queda revocada. Si vuelve a cumplir, recibirás nueva alerta.
```

### 3.8 Detección de acción del usuario (silenciamiento)

Cada invocación:
```python
active_env = {c.strip() for c in os.getenv("ACTIVE_TRADING_CITIES", "").split(",") if c.strip() and c.strip() != "NONE"}
for city in list(notified.keys()):
    if city in active_env:
        # Usuario aplicó el cambio — limpiar silenciosamente sin aviso adicional.
        notified.pop(city, None)
        changed = True
```

### 3.9 Anti-spam — rate limit duro

Nunca enviar más de una alerta (tipo nueva/recordatorio/revocación) por ciudad
por periodo de 22h (margen para no colisionar con jitter del scheduler). Usar
`last_notified_at` + comparación con `datetime.now(timezone.utc)`.

### 3.10 Integración en el loop principal

Llamar una vez por ciclo desde el mismo sitio donde se llama
`notify_canary_candidates(state)`. Respetar el mismo patrón de persistencia.

---

## 4. Módulo 2 — `maybe_run_active_degradation(state)`

### 4.1 Intención

Si una ciudad en `ACTIVE_TRADING_CITIES` tiene performance pobre, **degradarla
automáticamente a canary** (no shadow). Menos agresivo que el
`ALLOWLIST_REMOVE` existente que pasa directo a shadow.

### 4.2 Criterios

Evaluar por ciudad en `ACTIVE_TRADING_CITIES` (env var real, no overlay):

- `active_trades_post_activation >= 5`
- `win_rate <= 45%` **O** `pnl <= -1.50`
- No degradada a canary en últimos 14 días (anti-flapping)

### 4.3 Acción

No podemos editar el env var de Railway desde el bot. La degradación se
implementa igual que `auto_shadow_cities`: un overlay persistente. Propuesta:

- Añadir overlay `auto_canary_from_active` en `city_policy_state.json` (o
  extender `auto_canary_cities` con un campo `source: "degraded_from_active"`).
- Modificar `get_effective_city_mode()` para que una ciudad con overlay
  `auto_canary_from_active` se trate como `canary` aunque esté en
  `ACTIVE_TRADING_CITIES`.

**Decisión de implementación (Sonnet resuelve):** optar por la solución que
requiera el menor cambio en `get_effective_city_mode()` y más reutilice la
infraestructura existente. Lo importante es que:
1. La ciudad deje de operar en modo Active.
2. Pablo reciba Telegram con la evidencia de la degradación + instrucción
   copiable para remover la ciudad del env var.
3. `transition_history` registre el cambio.

### 4.4 Telegram

```
⚠️ <b>Ciudad degradada Active → Canary</b>
{city} ha sido degradada automáticamente por performance pobre.

Evidencia (desde activación):
• Trades: {trades} — WR {win_rate:.1f}% — PnL ${pnl:+.2f}
• Razón: {reason_short}

El bot ya operaba {city} con sizing active. A partir de este ciclo vuelve a
sizing canary (posición pequeña).

Para limpiar el env var en Railway:
<code>ACTIVE_TRADING_CITIES={new_cities_sin_la_ciudad}</code>
(opcional — el overlay runtime ya la excluye).
```

### 4.5 Integración

Llamar desde `run_observability_alerts()` antes de
`notify_active_candidates(state)`. Si el mismo ciclo degrada Tokyo y detecta
que Seoul cumple, ambos se procesan correctamente porque operan sobre state
separados.

---

## 5. Módulo 3 — `maybe_alert_v2_trigger(state)`

### 5.1 Intención

Pablo no debe recordar cuándo revisitar v2 (Bloques 3+5). El bot vigila las
precondiciones y, cuando se cumplen, manda Telegram one-shot con instrucción
copiable para arrancar la sesión Opus de v2.

### 5.2 Precondiciones para v2

Todas deben cumplirse:

1. **Recalibración Phase 2 cerrada.** Detección:
   - Env var `RECALIBRATION_PHASE2_CLOSED=true` en Railway, **O**
   - Archivo `data/recalibration_phase2_status.json` con `{"status": "closed"}`.
   - (Crear la env var vacía/false ahora; Pablo la setea a `true` cuando cierra Phase 2.)

2. **Al menos una ciudad promovida manualmente a Active vía v1.** Detección:
   `os.getenv("ACTIVE_TRADING_CITIES")` contiene al menos una ciudad (distinta
   de "NONE").

3. **Datos de traders disponibles localmente.** Detección: existencia de
   `data/runtime_import/signals.json` con `updated_at` de los últimos 48h.
   (Esto depende de que `railway_runtime_snapshot_pull.ps1` incluya signals.json
   — ya está en el backlog de Opus session 168.)

### 5.3 Alerta one-shot

Se envía una sola vez. Idempotencia vía `state["v2_trigger_notified"] = {"at": iso}`.

```
🎯 <b>Condiciones para v2 cumplidas</b>

Canary→Active v1 ha estado corriendo con {n_cities_active} ciudad(es) en Active
y la recalibración Phase 2 está cerrada. Es momento de añadir los Bloques 3+5
(corroboración externa + gate global post-recalibración) al gate de promoción.

Para arrancar la sesión limpia con Opus, copiar exactamente:

<code>Leer docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md §6 (Bloques 3+5 v2). Extender notify_active_candidates con: (Bloque 3) corroboración trader_signals o shadow_edge reciente, (Bloque 5) gate global WR sistema >= 50% últimos 30 días. No tocar criterios v1 ya en producción. Verificar con verify_before_deploy.py. Cierre: commit + push + deploy Railway.</code>

Este aviso es one-shot. No se repetirá.
```

### 5.4 Integración

Llamar una vez por día desde el mismo gate diario que usa
`maybe_run_daily_crosscheck` y `maybe_run_blocked_signals_check`.

---

## 6. Spec v2 (Bloques 3 + 5) — NO implementar ahora

Documentado aquí solo para que la sesión futura Opus (trigger: §5) sepa qué
construir.

### 6.1 Bloque 3 — Corroboración externa

Añadir al gate de `notify_active_candidates`:

- **Al menos UNA** de las siguientes debe cumplirse para la ciudad:
  - En `signals.json` (quality traders), `consensus >= 2` para la ciudad en
    últimos 7 días.
  - En `shadow_city_tracking.json`, la ciudad tiene `edge_hits >= 2` en últimos
    7 ciclos con `best_edge_pct >= MIN_EDGE`.

### 6.2 Bloque 5 — Gate global del sistema

**Antes** de evaluar ciudades individuales en `notify_active_candidates`,
chequear:

- WR global del bot en últimos 30 días >= 50% (calcular desde `audit_data` o
  `trade_lifecycle`, usando `RECALIBRATION_PHASE2_CLOSED_AT` como cutoff mínimo).
- Si no se cumple, **saltar toda la evaluación** y loggear `gate5_failed` a
  `alerts_state["active_candidate_gate5_log"]`. No alertar a Pablo por este
  chequeo — el v2 Trigger Alarm ya le avisó de arrancar esta sesión.

---

## 7. Archivos que SÍ tocar

- `bot.py` — añadir los 3 módulos, incrementar versión a `v10.6.14`, añadir
  entries a `BOT_VERSION_HISTORY` si aplica.
- (Si se elige overlay nuevo para §4.3) — `city_policy_state` shape.

## 8. Archivos que NO tocar

- `sync_city_policy_state()` — la promoción shadow→canary sigue intacta.
- Thresholds: `SHADOW_CANARY_MIN_*`, `ALLOWLIST_REMOVE_*`, `MIN_EDGE`, `MIN_DAYS_AHEAD`.
- Trading core, NOAA client, scheduler.
- `verify_before_deploy.py` (salvo añadir nuevos tests).
- `signals.json`, `trader_analyzer.py`.
- `ACTIVE_TRADING_CITIES` en Railway (debe seguir en NONE hasta que v1 dispare la primera alerta real).

## 9. Tests / verificación

1. `python verify_before_deploy.py` → debe quedar en `643/643+` (los tests
   nuevos deben pasar).
2. Añadir al menos estos casos unitarios (o smoke tests):
   - `notify_active_candidates`: ciudad con 4 trades NO alerta.
   - `notify_active_candidates`: ciudad con 5 trades, WR 60%, PnL +$1.50, días=8,
     integridad OK, sin degradación reciente → alerta.
   - `notify_active_candidates`: misma ciudad, re-invocación 1h después → NO alerta (rate limit).
   - `notify_active_candidates`: misma ciudad, re-invocación 25h después → recordatorio.
   - `notify_active_candidates`: ciudad con record Atlanta-inconsistency → NO alerta.
   - `notify_active_candidates`: ciudad ya en `ACTIVE_TRADING_CITIES` → silencio, limpiar state.
   - `maybe_run_active_degradation`: ciudad active con 5 trades, WR 30% → degrada + alerta.
   - `maybe_alert_v2_trigger`: precondiciones parciales → NO alerta. Todas cumplidas → alerta una sola vez. Segunda invocación → NO alerta (idempotente).
3. Manual smoke test contra datos reales: correr en dry-mode local con
   `data/runtime_import/city_policy_state.json` y `trade_lifecycle.json` actuales.
   Con el estado actual (todos con n≤1) **ninguna ciudad debe alertar**.

## 10. Checklist cierre de sesión

- [ ] Commit mensaje: `feat: canary→active notification + active→canary auto-degradation (v10.6.14)`
- [ ] `python verify_before_deploy.py` → verde
- [ ] Push a main
- [ ] Deploy Railway vía `tools/railway_safe.ps1`
- [ ] Actualizar `CONTEXTO.md` + `HISTORIAL_SESIONES.md` + `agent_events.jsonl`
- [ ] Crear env var `RECALIBRATION_PHASE2_CLOSED=false` en Railway (para que el trigger §5 tenga algo que vigilar)
- [ ] Post-deploy: verificar en logs Railway que las 3 funciones se invocan sin excepción en el primer ciclo.

---

## 11. Referencia cruzada de sesiones (para contexto)

- Sesión 169 cont. — ACTIVE_TRADING_CITIES=NONE aplicado + `maybe_run_daily_crosscheck` (patrón a copiar).
- Sesión 170 — `maybe_run_blocked_signals_check` (patrón a copiar para Telegram one-shot + recordatorio).
- `docs/canary-to-active-readiness-2026-04-12.md` — evidencia canary actual que justifica los umbrales.
- `docs/atlanta-lifecycle-inconsistency-2026-04-12.md` — patrón de inconsistencia a detectar en Bloque 2.
- `docs/auto-promotion-trigger-diagnosis-2026-04-13.md` — cómo funciona `sync_city_policy_state` hoy (no tocar).

---

## 12. Notas de diseño (para consulta)

**Por qué `notify_active_candidates` no muta `city_policy_state` directamente:**
Preservar la asimetría de responsabilidad. El bot **observa y avisa**; Pablo
**decide y aplica**. Esto mantiene la red de seguridad humana en la decisión de
capital más consecuente.

**Por qué `maybe_run_active_degradation` SÍ muta overlay:**
La degradación es una acción de protección de capital. Demorarla esperando
decisión humana viola la asimetría de riesgo: esperar a degradar = más pérdida.

**Por qué el trigger alarm v2 es one-shot:**
El recordatorio persistente es apropiado para "Pablo tiene que hacer algo ya"
(aplicar env var). El trigger v2 es "Pablo debería considerar empezar una
sesión Opus pronto" — no urgente, no persistente. Si Pablo lo ignora, puede
revisitarlo manualmente; no hay riesgo de capital.

---

*Fin de handoff. Esta sesión (172, Opus) lo creó; la sesión siguiente (Sonnet)
lo implementa.*
