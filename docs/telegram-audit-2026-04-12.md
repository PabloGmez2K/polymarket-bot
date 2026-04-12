# Telegram Audit — 2026-04-12

**Estado previo al audit:** preflight operational sin errores (ok=6, warning=2 — ambos no bloqueantes).
**Topología efectiva:** blocked=3, canary=6, shadow=18, active=0. `_is_shadow_only()=True`.

---

## Paso 1 — Inventario completo

### Botones del menú principal (MENU_KEYBOARD)

| # | Botón | Función | Trigger | Contenido |
|---|-------|---------|---------|-----------|
| 1 | 🎯 Focus | `cmd_focus` | tap | Vista operativa principal: headline de estado, respuestas a 4 preguntas clave, acción recomendada, quick_stats, incidentes |
| 2 | 📊 Estado | `cmd_estado` | tap | Versión, modo DRY/REAL, bankroll, edge, SL/TP, schedule, ciclos, resumen último ciclo |
| 3 | 🛰 Observabilidad | `cmd_noaa` | tap | NOAA proxy: MAE global, bias, cobertura, últimos casos por ciudad |
| 4 | 💰 Cartera | `cmd_cartera` | tap | Cash + posiciones activas/resueltas/muertas (live API) |
| 5 | ✦ Accuracy | `cmd_accuracy` | tap | Win rate y PnL por ciudad, separado en "operables hoy" vs "histórico total postmortem" |
| 6 | 📚 Postmortem | `cmd_postmortem` | tap | Open/pending/failed/closed trades, últimos cierres, posiciones abiertas |
| 7 | 📓 Log | `cmd_log` | tap | Resumen último ciclo desde `cycle_summary.json` (gestión, escaneo, compras, exposición) |
| 8 | 📋 Detalle | `cmd_logfull` | tap | Log full del último ciclo: aceptados, near misses, shadow con edge, condición filtrada, duplicados |
| 9 | ✦ Traders | `cmd_traders` | tap | Señales de traders: calidad, señales accionables, cruce con posiciones activas |
| 10 | 📈 Rendimiento | `cmd_rendimiento` | tap | Portfolio live + estadísticas históricas de performance.json |
| 11 | 🗒 Órdenes | `cmd_ordenes` | tap | Órdenes CLOB pendientes con etiqueta ciudad+temp+fecha |
| 12 | ℹ Info | `cmd_info` | tap | Bloque completo para pegar en ChatGPT/Claude: parámetros, ciclos, arquitectura |
| 13 | 🚀 Forzar ciclo | `cmd_forzar` | tap | Dispara ciclo inmediato vía `force_event` |
| 14 | ⚡ Modo | `cmd_modo` | tap | Toggle DRY_RUN/REAL, muestra teclado de confirmación inline |

### Botones secundarios (teclado inline de cmd_modo)

| Botón | Callback | Acción |
|-------|----------|--------|
| ✅ Activar REAL | `confirmar_real` | Pone `DRY_RUN=False` en memoria; avisa sobre restart Railway |
| 🟡 Volver a DRY RUN | `confirmar_dry` | Pone `DRY_RUN=True` en memoria |
| ✕ Cancelar | `cancelar_modo` | Sin cambios, muestra modo actual |

### Mensajes proactivos/automáticos

| ID | Función | Trigger | Contenido |
|----|---------|---------|-----------|
| A | Startup | Bot arranca | Versión, modo, bankroll, schedule, SL/TP, intra-SL, traders |
| B | Skip first cycle | Ciclo reciente detectado al arrancar | Último ciclo hace Xh, esperando próximo |
| C | First cycle | Primer ciclo del deploy | "Ejecutando primer ciclo..." |
| D | Cycle end summary | Fin de cada ciclo main() | Candidatos, con edge, shadow con edge, buys, exposición |
| E | Buy notification | BUY real ejecutado | Ciudad, lado, amount, edge, modo |
| F | Sell notification | SL/TP/Reeval ejecutado | Tipo, ciudad/lado, shares, precio límite, PnL estimado |
| G | **Daily summary** | `sorted(SCHEDULE_HOURS_UTC)[0]` → ahora 04h UTC | Ciclos 24h, resoluciones 24h, NOAA 24h, próximo ciclo |
| H | 04h slot review reminder | One-shot en fecha objetivo (17 abr) | Recordatorio de auditar impacto del slot 04h |
| I | Review trigger | N trades limpios cerrados alcanzados | Milestone para sesión de análisis |
| J | Signals health | Cambio de estado signals.json | missing/stale/empty/error/resuelto |
| K | NOAA milestones | One-shot por umbral | Proxy activo / muestra mínima / muestra global |
| L | NOAA por ciudad | One-shot primera muestra/interpretable | "NOAA nueva ciudad con muestra" / "ciudad interpretable" |
| M | Pending exits stuck | Órdenes > threshold horas sin fill | Lista de órdenes atascadas |
| N | Drawdown alert | PnL ventana reciente <= umbral | Alerta con PnL neto de últimos N trades |
| O | Scaling readiness/warning | PnL positivo/negativo en ventana | Subir/no subir bankroll |
| P | Win rate alert | WR < umbral bajo o >= umbral alto | Alerta / señal de estrategia |
| Q | City accuracy alert | Ciudad operable con WR bajo (postmortem) | Sugerir BLOCKED_CITIES |
| R | City NOAA-verified review | Ciudad canary/active con WR bajo verificado | Revisar allowlist/canary |
| S | Low bankroll alert | Cash total <= umbral | Urgente: recargar USDC |
| T | Canary candidate | Ciudad shadow alcanza criterio de promoción | One-shot pre-promote |
| U | City promoted/demoted | `sync_city_policy_state` ejecuta transición | Ciudad → canary / → shadow |
| V | Auth error | `setup_client()` falla al arrancar | Error autenticación |
| W | Trader discovery | Semanal (lunes) | "Descubrimiento iniciado/completado/error" |

---

## Paso 2 — Clasificación

### VIGENTE (refleja estado y objetivos actuales)

- **2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13** — todos leen datos vivos y muestran información directamente útil para observar el sistema en modo canary.
- **Botones secundarios de modo** — correctos; el aviso sobre Railway restart es preciso.
- **A, B, C, D, E, F, H, I, J, M, N, O, P, Q, R, S, T, U, V** — todos gateados correctamente; los que dependen de condiciones (N-R) son dormantes con throughput bajo pero no generan ruido, solo disparan si la condición se cumple.
- **K, L** — one-shots ya probablemente disparados y gateados; no volverán a aparecer.

### STALE — hallazgos con drift semántico

**S1 · cmd_focus "Universo activo" con active_count que incluye canary** (`build_dashboard_focus_center`, líneas 7393–7394, 7339, 7481–7482)

`active_count` se calcula como `active OR canary` en `build_dashboard_city_observation` (línea 4920). Con la topología actual (active=0, canary=6), `active_count=6`. El widget quick_stats muestra:
```
• Universo activo: 6 activas | 3 bloqueadas
```
Y el action_detail:
```
Universo activo 6 | NOAA interpretable X/Y | muestra global ...
```
El usuario sabe que active=0 y canary=6. Ver "6 activas" puede confundirse con "6 active cities". El label correcto sería "operable" o "canary/activo".

**Impacto:** bajo a medio — no bloquea decisiones, pero confunde la lectura de la topología.
**Corrección propuesta:** renombrar `"Universo activo"` → `"Universo operable"` y `"N activas"` → `"N operables"` en los tres puntos de display. Cambio de 5 strings en `build_dashboard_focus_center`, sin tocar lógica.

---

**S2 · Daily summary se disparó al horario 04h UTC al añadir el slot 04h** (`maybe_send_daily_summary_telegram`, línea 6592)

```python
target_hour = sorted(SCHEDULE_HOURS_UTC)[0] if SCHEDULE_HOURS_UTC else 8
```

Antes de activar el slot 04h, `SCHEDULE_HOURS_UTC=[8,16,23]` → daily a las 08h.
Con `SCHEDULE_HOURS_UTC=[4,8,16,23]` → daily a las **04h UTC**.

Este es un cambio de comportamiento silencioso: el resumen diario ahora llega a las 04h, no 08h. La lógica es coherente internamente pero puede sorprender.

**Impacto:** bajo — el resumen sigue siendo correcto, solo cambia la hora.
**Corrección propuesta (no aplicada — requiere decisión del usuario):** hardcodear `target_hour = 8` o añadir una variable de entorno `DAILY_SUMMARY_HOUR_UTC`. No se aplica en esta sesión porque toca scheduler/env.

---

**S3 · cmd_info arquitectura con "~330 mercados temp" estático** (línea 10937)

```python
"~330 mercados temp | forecast operativo: Open-Meteo | modelo normal(μ,σ)\n"
```

Número aproximado heredado. Con prefilter de city_window y otros filtros, el número real de candidatos evaluados varía. No es operacionalmente crítico (es un bloque descriptivo para AI assistants).

**Impacto:** mínimo.
**Corrección propuesta:** ninguna en esta sesión — es texto de descripción estática, no data viva.

---

### RUIDO — nada identificado

Ninguna superficie se dispara con frecuencia excesiva ni aporta ruido real en el estado actual:
- Las alertas de escala (O), win rate (P), drawdown (N) son dormantes con throughput bajo.
- El daily summary (G) es one-shot/día.
- Los milestones NOAA (K, L) están gateados.

### FALTA — gaps identificados

**F1 · No hay superficie compacta de topología de ciudades**

No existe un comando/botón que muestre directamente `blocked=3, canary=6, shadow=18, active=0`. El usuario necesita combinar `cmd_accuracy` (canary visible), `cmd_focus` (blocked_count en quick_stats) y SSH para ver shadow count. Dado que el bot opera en modo observación, esta información es el punto de partida de cualquier análisis.

**Severidad:** media. No impide operar, pero obliga a triangular tres surfaces distintas.
**Nota:** implementar una vista de topología compacta iría en una sesión separada de Telegram (tocaría cmd_estado o un nuevo comando `/topologia`). Fuera de scope de esta sesión.

---

## Paso 3 — Auditoría de botones inline

| Botón | Callback | Relevante ahora | Nota |
|-------|----------|----------------|------|
| 🎯 Focus | `focus` | ✅ | Principal entry point operativo |
| 📊 Estado | `estado` | ✅ | Schedule, ciclos, último ciclo |
| 🛰 Observabilidad | `noaa` | ✅ | NOAA proxy, cobertura |
| 💰 Cartera | `cartera` | ✅ | Posiciones reales o DRY |
| ✦ Accuracy | `accuracy` | ✅ | Canary cities con stats |
| 📚 Postmortem | `postmortem` | ✅ | Cierres históricos |
| 📓 Log | `log` | ✅ | Último ciclo |
| 📋 Detalle | `logfull` | ✅ | Diagnóstico del último ciclo |
| ✦ Traders | `traders` | ✅ | Intel de señales |
| 📈 Rendimiento | `rendimiento` | ✅ | Estadísticas + portfolio |
| 🗒 Órdenes | `ordenes` | ✅ (raramente útil) | Devuelve "ninguna" si no hay órdenes; no molesta |
| ℹ Info | `info` | ✅ | Bloque para AI — útil para sesiones de análisis |
| 🚀 Forzar ciclo | `forzar` | ✅ | Útil para provocar observación bajo demanda |
| ⚡ Modo | `modo` | ✅ (dormante) | DRY/REAL toggle; con active=0 el REAL mode no ejecutaría trades aunque se activara |
| ✅ Activar REAL | `confirmar_real` | ✅ | Aviso de Railway correcto |
| 🟡 Volver a DRY RUN | `confirmar_dry` | ✅ | Clean |
| ✕ Cancelar | `cancelar_modo` | ✅ | Clean |

**Orphaned callbacks:** ninguno. Todos los `callback_data` del MENU_KEYBOARD y los teclados inline custom tienen handler en `COMMANDS`.

**Observación sobre ⚡ Modo:** Con `_is_shadow_only()=True` (ACTIVE_TRADING_CITIES vacío), activar REAL mode desde Telegram **no habilitaría trades canary**, porque el shadow-only override se aplica antes de la check de DRY_RUN. El botón es correcto pero el usuario debe saber que activar REAL tampoco activa trades hasta que se ponga una ciudad en ACTIVE_TRADING_CITIES. El aviso actual en `cmd_confirmar_real` menciona Railway pero no esto. No se cambia en esta sesión (tocaría lógica de trading para la explicación).

---

## Cambios propuestos

### Cambio 1 (APLICADO): Label "Universo activo" → "Universo operable" en cmd_focus

**Justificación:** `active_count` en `build_dashboard_focus_center` = active+canary. Con active=0 y canary=6, mostrar "6 activas" confunde al usuario que sabe que active=0. "Operable" es el término canónico para active+canary (usado en `cmd_accuracy`: "Operables hoy", y en `cmd_noaa`: "Ciudades operables / seguidas").

**Archivos tocados:** `bot.py` (5 strings en `build_dashboard_focus_center`, sin tocar lógica).
**Líneas:** 7339, 7393, 7394, 7481, 7482.

### Cambio 2 (NO APLICADO — decisión pendiente): Daily summary a 08h fijo

**Justificación:** El slot 04h activado recientemente movió el daily summary de 08h a 04h silenciosamente. `target_hour = sorted(SCHEDULE_HOURS_UTC)[0]` devuelve 4 con el schedule actual.

**Opción A:** Hardcodear `target_hour = 8` en `maybe_send_daily_summary_telegram`.
**Opción B:** Añadir variable de entorno `DAILY_SUMMARY_HOUR_UTC=8` en Railway.
**Opción C:** Dejar como está (daily a 04h es coherente con el primer ciclo del día).

Requiere decisión explícita del usuario sobre qué hora prefiere para el daily.

---

## Definition of Done — estado

1. ✅ `docs/telegram-audit-2026-04-12.md` creado con inventario completo.
2. ✅ Cambio 1 listado y aplicado. Cambio 2 listado y pendiente de decisión.
3. ✅ `python verify_before_deploy.py` ejecutado tras aplicar Cambio 1.
4. N/A — no se cerró en no-op; hubo 1 fix menor aplicado.
