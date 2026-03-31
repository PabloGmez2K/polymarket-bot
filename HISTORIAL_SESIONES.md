# HISTORIAL DE SESIONES

Bitácora legible del proyecto reconstruida desde:

- `git log`
- `CONTEXTO.md`
- mensajes de commit

Objetivo:

- saber qué sesiones ya existieron;
- evitar repetir trabajo ya hecho;
- distinguir entre cambios explícitamente documentados y reconstrucciones inferidas;
- complementar a Git con una memoria humana del proyecto.

Reglas de lectura:

- `Explícita`: la sesión aparece nombrada tal cual en Git o en el contexto.
- `Inferida`: no aparece como sesión formal, pero se puede reconstruir con bastante confianza por la secuencia de commits.
- Este archivo no sustituye al historial real de Git; lo resume.

Comandos útiles:

- `git log --follow --oneline -- CONTEXTO.md`
- `git log --oneline --reverse`
- `git show <commit>`

---

## Línea temporal resumida

| Fecha | Tipo | Referencia | Commits clave | Resumen |
|------|------|------------|---------------|---------|
| 2026-03-21 | Explícita | Sesión 2 | `bddcab8` | Bot base con edge detection, backtest y bankroll management. |
| 2026-03-21 | Explícita | Sesión 3 | `f97702e` | Instalación `pip`, CLOB API, autenticación y primera orden de prueba. |
| 2026-03-21 | Inferida | Iteración v3-v7 | `e8d11c0` `047f7e4` `5ac83b9` `c32c34f` `9e51025` `6973b74` `d5bf5d8` | Filtros de precio, scheduler, alertas Telegram, dashboard, cartera, órdenes enriquecidas y decision log. |
| 2026-03-21 | Inferida | Infraestructura inicial | `886a112` `d4194ac` `3d128fb` | `requirements.txt`, variables de entorno, `Procfile` y unificación de contexto en `CONTEXTO.md`. |
| 2026-03-22 | Inferida | Iteración v8 | `35ef3d6` `c2bc7ff` `eea1eef` `fba7a0b` | `MIN_DAYS/MAX_DAYS`, reintentos de red y expansión fuerte de ciudades soportadas. |
| 2026-03-22 | Inferida | Iteración v9 | `9e7941e` `4bd7e8b` `c857133` `d7ae3a3` `2aa59c1` `48d7c4f` | Pipeline de traders, `signals.json`, filtro de calidad, parseo de rangos, `logfull`, near misses y ajustes Kelly. |
| 2026-03-22 | Explícita | Sesión 9 | `91162b0` | Pipeline traders v2 y primeras órdenes reales 4/4 OK. |
| 2026-03-22 a 2026-03-23 | Inferida | Iteración v10-v10.2 | `d2ae676` `ce0684e` `931158e` `0ae32c9` `deb50b3` `3c408f3` `d01b4b9` | Exposición acumulativa, sigma calibrada, gestión activa, auditoría, bankroll real, performance tracker, cash balance y mejoras Telegram. |
| 2026-03-24 | Inferida | Iteración v10.3 | `bef71e3` | Cinco bugs corregidos y `verify_before_deploy.py` consolidado. |
| 2026-03-28 | Explícita | Sesión 19 | `a24fde2` `cd12121` `56aeb5a` `185f018` `374d6a8` `3c4b5f1` `19adfdd` `d382f47` `695f405` | v10.4 a v10.4.8: persistencia, rediseño Telegram, ciclos persistentes, DST robusto, trazabilidad multi-agente, tests funcionales, base de `postmortem.json`, alertas de observabilidad, bloqueo operativo de London y refinamiento final de botones Telegram. |
| 2026-03-29 | Explícita | Sesión 24 | `—` | Refinamiento del dashboard: modo oscuro, checklist histórico/serie separado, scorecard por stages y ciclos legacy legibles. |
| 2026-03-29 | Explícita | Sesión 25 | `—` | Pasada rápida de UX: `n/d` y `sin cierres` cuando la serie nueva todavía no tiene muestra real. |
| 2026-03-29 | Explícita | Sesión 26 | `—` | Último pulido UX: estado neutral `Esperando muestra` en el checklist del dashboard. |
| 2026-03-29 | Explícita | Sesión 27 | `—` | Nueva capa del dashboard: progreso operativo, trofeos validados y desbloqueos para saber qué evidencia falta antes de revisar lógica o subir bankroll. |
| 2026-03-29 | Explícita | Sesión 28 | `—` | Dashboard añade balance por tipo de cierre y liquidación para distinguir TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN de `pending_exit` y valor pendiente de canjear. |
| 2026-03-29 | Explícita | Sesión 31 | `—` | Hardening local de `v10.6.2`: alerta de bankroll fiable, rearme con margen, scorecard actualizado y docs/tests alineados. |
| 2026-03-30 | Explícita | Sesión 32 | `—` | Investigación estratégica Codex + Claude: Dallas `KDAL` como bug activo, auditoría mal nombrada, síntesis competitiva y preparación del alcance de `v10.6.3`. |
| 2026-03-30 | Explícita | Sesión 33 | `—` | Implementación local de `v10.6.3`: fix Dallas `KDAL`, `RESOLUTION_ICAO`, auditoría `forecast vs forecast posterior Open-Meteo` y suite en `358/358`. |
| 2026-03-30 | Explícita | Sesión 34 | `—` | Implementación local de `v10.6.4`: `observed_vs_forecast` con NOAA NCEI, `noaa_station_id` para 4 activas, lag de 2 días y suite en `371/371`. |
| 2026-03-30 | Explícita | Sesión 35 | `—` | Implementación local de `v10.6.5`: dashboard separa `Calidad Forecast Observada (NOAA)` del bloque legacy `Drift Open-Meteo`, con suite en `386/386`. |
| 2026-03-30 | Explícita | Sesión 36 | `—` | Sync post-recarga: depósito manual `+$14.99`, fallback `BANKROLL` alineado a `$25` y test para fijar el default local. |
| 2026-03-30 | Explícita | Sesión 37 | `—` | Playbook operativo multiagente, helper seguro para `agent_events.jsonl`, checks de consistencia docs-scoreboard y sync del scoreboard live. |
| 2026-03-30 | Explícita | Sesión 38 | `—` | Limpieza del scoreboard live, deduplicación robusta en `load_agent_events()` y regla explícita: review sin delta = `0 puntos` o sin evento. |
| 2026-03-30 | Explícita | Sesión 39 | `—` | Research final Lean Six Sigma: no adoptar salvo FMEA-lite y definiciones mínimas; playbook mínimo, hitos NOAA one-shot y nueva vista Telegram `/noaa`. |
| 2026-03-30 | Explícita | Sesión 40 | `—` | Diagnóstico pérdidas NYC/Munich/Atlanta: bot entraba en ciudades sin validación (Seoul, Tokyo, NYC, Munich no bloqueadas). Ventas manuales NYC. Identificado bug #15 — allowlist `ACTIVE_TRADING_CITIES` pendiente en v10.6.6. |
| 2026-03-30 | Explícita | Sesión 41 | `—` | Implementación local de `v10.6.6`: allowlist `ACTIVE_TRADING_CITIES`, skip claro en `decisions.log`, bump de versión y suite en `419/419`. |
| 2026-03-30 | Explícita | Sesión 42 | `—` | Implementación local de `v10.6.7`: tabla `Estado de observacion por ciudad` en el dashboard, cruzando allowlist, NOAA e histórico validado, con suite en `426/426`. |
| 2026-03-30 | Explícita | Sesión 43 | `—` | Implementación local de `v10.6.8`: nueva capa 1 `Control Center Discovery/Stabilization` en dashboard + `/focus` en Telegram, con detalle relegado a capas inferiores y suite en `440/440`. |
| 2026-03-30 | Explícita | Sesión 44 | `—` | Implementación local de `v10.6.9`: `Mission HUD` para discovery/stabilization con estilo videojuego operacional, tabs `Overview / Progress / Cities`, barras de progreso, `city race`, `dashboard.js` y suite en `447/447`. |
| 2026-03-30 | Explícita | Sesión 45 | `7eb8f7f` | Refinamiento y despliegue de `v10.6.10`: modo claro por defecto, ciudades agrupadas por prioridad operativa, repetición de `signals stale` reducida cuando NOAA es el cuello de botella, suite en `449/449` y validación en Railway. |
| 2026-03-31 | Explícita | Sesión 46 | `—` | Auditoría NOAA `observed_vs_forecast`: se demuestra bug real de observabilidad, no solo falta de muestra. Fix local con `daily-summaries/TMAX` prioritario, fallback `global-hourly`, guard de lag coherente, trazabilidad extra y suite en `453/453`. |

---

## Sesiones explícitas

### Sesión 2

- Fecha: 2026-03-21
- Commit principal: `bddcab8`
- Estado aproximado: bot ya funcional con edge detection, backtest y bankroll.
- Valor histórico: marca el arranque real del proyecto como bot operativo, antes de toda la capa de Telegram, Railway y observabilidad posterior.

### Sesión 3

- Fecha: 2026-03-21
- Commit principal: `f97702e`
- Estado aproximado: integración con CLOB API, autenticación y primera orden de prueba.
- Valor histórico: paso de prototipo local a interacción real con Polymarket.

### Sesión 9

- Fecha: 2026-03-22
- Commit principal: `91162b0`
- Estado aproximado: pipeline de traders v2 y primeras órdenes reales verificadas.
- Valor histórico: inicio de la operativa real con señales de traders ya dentro del sistema.

### Sesión 19

- Fecha: 2026-03-28
- Commits principales:
- `a24fde2`
- `cd12121`
- `56aeb5a`
- `185f018`
- `374d6a8`
- `3c4b5f1`
- `19adfdd`
- `d382f47`
- Resumen:
- persistencia en Volume y ciclos históricos;
- rediseño fuerte de Telegram;
- correcciones de bugs #3, #9, #10, #11, #12, #13 y #14;
- paso de DST manual a `ZoneInfo`;
- entrada de Codex al flujo como agente complementario a Claude Code;
- trazabilidad multi-herramienta;
- reparación manual de una entrada truncada en `performance.json` de Railway;
- base de `postmortem.json`;
- persistencia de `signals.json`, `traders_db.json` y `trader_history.json` en Volume;
- comando `/postmortem` para inspección rápida desde Telegram y botón visible en el menú;
- backfill automático de `postmortem.json` desde `performance.json`;
- `alerts_state.json` y alertas one-shot para `30 trades limpios`, `signals.json` y `pending_exit`;
- bloqueo operativo de London en codigo para evitar nuevas entradas;
- refinamiento Telegram: `traders` cruza por fecha exacta, `postmortem` muestra labels legacy legibles y `detalle` deja de cortar a 40 lineas;
- regla operativa: antes de cada push relevante, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md`.

---

## Hitos inferidos relevantes

### Iteración v3-v7

- Fecha: 2026-03-21
- Commits: `e8d11c0`, `047f7e4`, `5ac83b9`, `c32c34f`, `9e51025`, `6973b74`, `d5bf5d8`
- Resumen:
- se añadieron filtros de precio, agresividad, duplicados y stale cleanup;
- se integró scheduler en `main()`;
- entraron alertas Telegram, dashboard, toggle de modo, cartera y órdenes enriquecidas;
- apareció `decisions.log`.

### Iteración v8

- Fecha: 2026-03-22
- Commits: `35ef3d6`, `c2bc7ff`, `eea1eef`, `fba7a0b`
- Resumen:
- se relajó la ventana temporal (`MIN_DAYS=0`, `MAX_DAYS=5`);
- se añadieron reintentos de red;
- se amplió el universo de ciudades de forma importante.

### Iteración v9

- Fecha: 2026-03-22
- Commits: `9e7941e`, `4bd7e8b`, `c857133`, `d7ae3a3`, `2aa59c1`, `48d7c4f`
- Resumen:
- nació el pipeline de traders;
- aparecieron `find_traders.py`, `trader_analyzer.py`, `signals.json` y `traders_db`;
- se integró calidad de traders y consenso;
- se añadió soporte de mercados de rango;
- se ajustó Kelly y sizing.

### Iteración v10-v10.2

- Fecha: 2026-03-22 a 2026-03-23
- Commits: `d2ae676`, `ce0684e`, `931158e`, `0ae32c9`, `deb50b3`, `3c408f3`, `d01b4b9`
- Resumen:
- fix de exposición acumulativa;
- sigma calibrada;
- gestión activa con stop-loss / take-profit / re-evaluación;
- auditoría de ventas y performance tracker;
- bankroll real en Railway;
- mejoras de balance y Telegram;
- corrección de exposición fantasma y `MIN_DAYS` dinámico.

### Iteración v10.3

- Fecha: 2026-03-24
- Commit: `bef71e3`
- Resumen:
- consolidación de bugs previos;
- fortalecimiento del verificador;
- preparación para la fase 10.4.x.

### Iteración v10.4.x

- Fecha: 2026-03-28
- Commits: `a24fde2`, `cd12121`, `56aeb5a`, `185f018`, `374d6a8`, `3c4b5f1`, `19adfdd`, `d382f47`
- Resumen:
- v10.4: persistencia, fixes críticos y mejoras de Telegram;
- v10.4.1: historial de ciclos;
- v10.4.2: rediseño completo de Telegram;
- v10.4.3: ciclos persistentes y limpieza del repo;
- v10.4.4: parche manual temporal de DST;
- v10.4.5: `ZoneInfo`, tests funcionales, trazabilidad, `postmortem.json`, trader data al Volume y `/postmortem`.
- v10.4.6: backfill de `postmortem.json`, `alerts_state.json` y alertas Telegram de observabilidad.
- v10.4.7: bloqueo operativo de London en codigo y tests de regresion.
- v10.4.8: refinamiento final de Telegram tras revision manual de botones.

---

## Sesión 20 — 29 marzo 2026

**Herramienta:** Claude Code (Opus)
**Versiones:** v10.5.0 → v10.5.1 → v10.5.2
**Tests:** 216 → 226 → 234

**Cambios realizados:**
- v10.5.1: Intra-cycle SL/TP monitor cada 90min con `sell_lock`, thread daemon y cobertura ampliada hasta 226 tests.
- v10.5.2: City accuracy tracker — `get_city_accuracy()` analiza win rate por ciudad desde postmortem.json. Alerta Telegram si una ciudad baja de 25% win rate con 3+ trades. Nuevo comando `/accuracy`. Win rate visible en `/rendimiento`.
- Investigación WU API: API muerta desde 2019 (IBM compró). IBM Trial no viable (Pablo no pudo verificar identidad). Opciones documentadas: PWS key (~$30-50 estación), o seguir con accuracy tracker como proxy.
- CONTEXTO.md actualizado a v10.5.2 con estado real de posiciones (corregido desde auditoría SSH sesión 19).

**Lección operativa:** Esta sesión consumió demasiado uso de Opus. Tareas delegables a Codex: investigación WU (web search + resumen), escritura de tests de comportamiento, actualizaciones de docs. Opus debe reservarse para diseño de arquitectura y coding de lógica crítica.

## Sesión 21 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.3
**Tests:** 242

**Cambios realizados:**
- revisión crítica de los commits de la mañana (`v10.5.0`, `v10.5.1`, `v10.5.2`) contrastando Git, código y docs;
- integración real de `/accuracy` en el menú de Telegram;
- `cmd_accuracy` vuelve con menú y `/estado` muestra el intervalo intra-SL como ya decía el contexto;
- corrección de la trazabilidad de sesión 20 para que no simplifique en exceso lo que realmente añadió `v10.5.1`.

**Resultado:** repo alineado a nivel código, tests y documentación; queda pendiente decidir si desplegar `v10.5.3` o seguir observando `v10.5.2` primero.

## Sesión 22 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.4
**Tests:** 251

**Cambios realizados:**
- separación del contador de ciclos en dos dimensiones: histórico total y serie lógica actual `v10.5`;
- nuevo helper `_load_cycle_counts()` para reconstruir ambos contadores desde `cycles_history.jsonl` sin romper continuidad histórica;
- `cycle_summary.json` y `cycles_history.jsonl` pasan a guardar `logic_series` y `logic_cycle_number`;
- `/estado` y `/info` muestran `N total | M serie v10.5`, resolviendo la ambigüedad que mezclaba observabilidad global con evaluación de la nueva lógica;
- `verify_before_deploy.py` ampliado con tests funcionales de historial mixto `v10.4`/`v10.5`;
- temporales del verificador movidos al directorio temporal del sistema para no dejar `_tmp_*` en el repo en futuras ejecuciones.

**Resultado:** `v10.5.4`, 251/251 tests, histórico total preservado y serie `v10.5` visible por separado para análisis comparativo.

## Sesión 23 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.5
**Tests:** 279

**Cambios realizados:**
- implementación de un dashboard web HTML servido desde el mismo servicio Railway, separado de Telegram;
- checklist gamificado de promoción de bankroll (`$25 -> $35`) calculado con métricas del sistema;
- scoreboard de agentes y rivalidad constructiva basados en `agent_events.jsonl`;
- nueva plantilla `templates/dashboard.html`, estilos en `static/dashboard.css` y arranque HTTP paralelo con `Flask` + `waitress`;
- ampliación de `verify_before_deploy.py` para cubrir backend, scorecard, checklist y assets del dashboard.

**Resultado:** `v10.5.5`, 279/279 tests, dashboard listo para validación visual en navegador y nueva base para comparar utilidad real de Opus/Codex.

## Sesión 24 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.6
**Tests:** 290

**Cambios realizados:**
- refinamiento del dashboard tras revisión visual real en Railway;
- cambio a modo oscuro por defecto para revisión en navegador;
- checklist separado entre `trades limpios históricos` y `trades limpios serie v10.5`;
- scorecard de agentes extendido con stages `proposed / implemented / validated`;
- ciclos legacy pasan a mostrarse como `legacy v10.X` en vez de marcadores ambiguos;
- ciudades clave reordenadas por riesgo operativo en lugar de volumen puro;
- `verify_before_deploy.py` ampliado para cubrir dark mode, stages y checklist separado.

**Resultado:** `v10.5.6`, 290/290 tests, dashboard más honesto para medir la serie `v10.5` y más cómodo de usar en escritorio.

## Sesión 25 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.7
**Tests:** 294

**Cambios realizados:**
- ajuste semántico del dashboard para no mostrar métricas “cero” como si ya existiera muestra válida;
- `PnL serie`, `Win rate serie` y `Drawdown reciente` pasan a mostrar `n/d` o `sin cierres` cuando todavía no hay cierres en la serie `v10.5`;
- el checklist deja de marcar esas métricas como `OK` si la serie aún no tiene cierres;
- ampliación del verificador con casos funcionales específicos para esta situación.

**Resultado:** `v10.5.7`, 294/294 tests, dashboard más claro en las primeras fases de una serie lógica nueva.

## Sesión 26 — 29 marzo 2026

**Herramienta:** Codex
**Versión:** v10.5.8
**Tests:** 300

**Cambios realizados:**
- incorporación de un tercer estado visual en el checklist del dashboard: `Esperando muestra`;
- separación visual entre `fallo real` y `métrica aún sin datos suficientes`;
- actualización de la plantilla y estilos para que ese estado no se vea rojo;
- ampliación del verificador con cobertura específica de `status`/`tag` en checklist.

**Resultado:** `v10.5.8`, 300/300 tests, checklist más intuitivo para operar y revisar series nuevas.

## Sesión 27 — 29 marzo 2026

**Herramienta:** Codex  
**Versión:** v10.5.9  
**Tests:** 325

**Cambios realizados:**
- nueva capa del dashboard con bloque `Progreso` para mostrar `faltan X para Y` sobre muestra de serie, estabilidad, cierres útiles, readiness de bankroll y cobertura de ciudades;
- bloque `Trofeos` calculado solo desde cierres validados (`postmortem.json`) para resaltar mejores y peores hitos operativos del bot;
- bloque `Desbloqueos` con explicaciones operativas de qué falta para revisar lógica con confianza o evaluar subir de nivel;
- ampliación del snapshot del dashboard y de `/api/dashboard.json` con `progress`, `trophies` y `unlocks`;
- ampliación de `verify_before_deploy.py` con tests funcionales y estructurales específicos de esta capa nueva.

**Resultado:** `v10.5.9`, 325/325 tests, dashboard más accionable para interpretar evidencia y tomar decisiones de siguiente nivel sin mezclarlo con Telegram.

## Sesión 28 — 29 marzo 2026

**Tipo:** Explícita  
**Versión:** v10.5.10  
**Objetivo:** añadir al dashboard una capa explícita de balance por tipo de salida para entender si el sistema corta ganancias demasiado pronto, deja pérdidas crecer o simplemente todavía no ha reconciliado fills/cobros.

**Herramientas utilizadas:**
- `Codex`: implementación completa de backend + HTML/CSS + tests + actualización de docs.
- `Claude Code`: no usado en esta sesión; se deja como siguiente revisor crítico de toda la iteración reciente del dashboard.

**Cambios clave:**
- nuevo helper `build_dashboard_exit_breakdown()` en `bot.py`;
- nueva sección `Balance por tipo de cierre` con filas para `Take-profit`, `Stop-loss`, `Re-evaluación`, `LOSS_TOTAL`, `Ganadas por resolución`, `Ganadas validadas` y `Perdidas validadas`;
- nueva sección `Liquidación` para separar `cierres validados de la serie`, `pending_exit`, `abiertas`, `exit_failed` y `pendiente pago / canjear`;
- snapshot del dashboard ampliado con `exit_breakdown`;
- plantilla y CSS ampliados para mostrar estas dos tarjetas nuevas;
- tests de verificación ampliados a `334/334`.

**Valor de la sesión:**
- el dashboard ya no solo dice “cuántos trades faltan”, sino también **cómo se están cerrando** y **dónde se queda el dinero atascado**;
- deja visible la diferencia entre:
  - cierre validado con PnL real,
  - venta pendiente de fill/auditoría,
  - valor pendiente de cobro/canje.

**Resultado:** `v10.5.10`, 334/334 tests, base mejor preparada para que Claude Code revise por qué el bankroll sigue cayendo y si el patrón dominante es `stop_loss`, `LOSS_TOTAL`, `reeval` o falta de resoluciones favorables a $1.

## Sesión 29 — 29 marzo 2026

**Herramienta:** Claude Code (Sonnet)
**Versión:** v10.5.11
**Tests:** 337

**Objetivo:** Revisión crítica integral de las sesiones 24-28 (dashboard v10.5.6 → v10.5.10). Validar métricas, detectar bugs reales e inconsistencias, y corregirlos.

**Hallazgos críticos:**

1. **Bug en checklist: drawdown marcado OK con muestra incompleta.** Con 1-4 cierres (< `DRAWDOWN_WINDOW=5`), el check `Drawdown últimos N cierres` mostraba `OK` en lugar de `Esperando muestra`. La condición `recent_window_size < DRAWDOWN_WINDOW` siempre era `True` con datos parciales, haciendo que `passed` fuera siempre `True` antes de tener ventana completa.

2. **agent_events.jsonl no se sincronizaba entre repo y Railway Volume.** `_seed_data_file()` no sobreescribe archivos existentes, por lo que las sesiones 27-28 del scoreboard solo estaban en el repo local pero no llegaban a Railway.

3. **Rows "Ganadas validadas" y "Perdidas validadas" en exit_breakdown son agregados, no categorías exclusivas.** Se solapan con las filas TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN. No es un bug de datos pero puede confundir si se suman todos los valores. Las notas en la tabla (`note`) ya lo aclaran; se deja como está (cosmético).

4. **Hipótesis "cortar ganancias demasiado pronto"**: No confirmada con datos locales (no hay datos de Railway disponibles en esta sesión). El TP al +40% es conservador pero intencional. La causa dominante de pérdidas sigue siendo probablemente WU vs Open-Meteo, no el timing de salida.

5. **RESOLVED_WIN pnl_cash**: La lógica es correcta (`pnl_cash = shares - initial_value`). Los registros LOSS_TOTAL también tienen `pnl_cash` correcto (`-initial_value`). No hay bug aquí.

6. **pending_exit pnl_cash**: El dict `pending_exit` en postmortem sí guarda `pnl_cash` (el valor estimado de `p.get("cashPnl")`). El test de verify era correcto.

**Cambios realizados:**
- bug fix: `build_promotion_checklist()` — `has_full_drawdown_window = recent_window_size >= DRAWDOWN_WINDOW`; el check `passed`/`waiting` usa la ventana completa en lugar de cualquier dato parcial;
- nuevo helper `_sync_agent_events_seed()` que merge local → Volume en arranque, añadiendo solo eventos nuevos por `(timestamp, agent, title)`;
- `AGENT_EVENTS_FILE = _sync_agent_events_seed()` en lugar de `_seed_data_file("agent_events.jsonl")`;
- 2 tests nuevos en verify: ventana parcial de drawdown → `Esperando muestra`, y strings actualizados para la nueva asignación;
- CONTEXTO.md y HISTORIAL_SESIONES.md actualizados.

**Resultado:** `v10.5.11`, 337/337 tests, checklist de drawdown ahora honesto y scoreboard sincronizado en arranque.

Misma sesión, segundo commit: `v10.5.12` — bloqueo ciudades + fix posiciones fantasma (ver abajo).

## Sesión 29 (continuación) — v10.5.12

**Disparador:** Alerta Scaling Warning en Telegram: `-$19.98 en últimos 20 trades`. Bot perdiendo bankroll de forma alarmante desde $25 → $18.21.

**Análisis de datos reales** (`/accuracy`, `/rendimiento`, `/postmortem`):
- 10 de 14 ciudades activas: 0% win rate (London, Miami, Seattle, Paris, Tel Aviv, Wellington, Toronto, Madrid, Singapore, Ankara).
- Solo positivas: Chicago (+$3.30, 50% WR), Atlanta (+$2.60, 100% WR), Buenos Aires (+$0.80, 100% WR).
- Causa raíz confirmada: Open-Meteo difiere de Weather Underground en ciudades costeras y europeas. Polymarket resuelve con WU → predicciones sistemáticamente erróneas.
- Bug adicional descubierto: 17 posiciones en postmortem "open" vs 6 en cartera real. Las diferencias son posiciones ya resueltas a $0 que desaparecen del API sin registrarse como LOSS_TOTAL. El `/rendimiento` mostraba -$4.92 pero la escala real era ~-$20.

**Cambios realizados:**
- `BLOCKED_CITIES` default ampliado: `London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`;
- Fix: posiciones con `currentValue < 0.01` ahora llaman a `_mark_micro_as_loss_total` en vez de `continue` silencioso;
- 338/338 tests.

---

## Sesión 30 — v10.6.0 (29 mar 2026)

**Disparador:** Cartera en caída libre: $18.89 (-$9.52 último día, -50.4%). Pablo reporta que desde el 27 de marzo todo son pérdidas y los cambios del fin de semana están destruyendo la operativa.

**Diagnóstico (Claude Code — Opus):**

Investigación completa de trades, commits y lógica de trading desde v10.3 hasta v10.5.12:

1. **Sigma ampliada de v10.5.0 vendía posiciones ganadoras en re-eval.** Con sigma {0:2.0, 1:2.5, 2:3.0, 3:3.5}, la re-evaluación calculaba edge negativo en posiciones que v10.3 habría mantenido y que probablemente habrían ganado. Ejemplo: YES at_or_above 22°C con forecast 23°C a day 3 → v10.3 KEEP (edge +2.6%), v10.5 SELL (edge -3.4%).

2. **Intra-cycle monitor (cada 90 min) disparaba SL ante fluctuaciones normales.** En mercados de temperatura con resolución diaria, una posición puede tocar -25% temporalmente y recuperarse. Con check cada 90 min, se vendía antes de que se estabilizara.

3. **MIN_EDGE_EXACT=15% bloqueaba entradas exact** con solo 4 ciudades activas, dejando al bot casi sin operativa.

4. **Las pérdidas LOSS_TOTAL** (mercados resueltos en contra) son de posiciones compradas con v10.3 donde Open-Meteo difería de Weather Underground. No son bugs de código sino problema de fuente de datos.

**Conclusión:** v10.3 era agresivo pero funcional (ganaba y perdía). Los cambios de v10.5 lo convirtieron en un bot que no entra en nada, vende lo poco que tiene demasiado pronto, y las predicciones base siguen siendo de Open-Meteo.

**Cambios realizados:**
- Sigma restaurada a v10.3: `{0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5, 4+: 3.0}`
- Intra-cycle desactivado: `INTRA_SL_INTERVAL` default 0
- `MIN_EDGE_EXACT` eliminado (usa `MIN_EDGE=7%` para todo)
- Toda la observabilidad mantenida (postmortem, accuracy, alerts, dashboard, ciudades bloqueadas)
- Display sigma en Telegram corregido para coincidir con valores reales
- Tests actualizados: 335/335

**Resultado:** `v10.6.0`, desplegado en Railway. Bot vuelve a la lógica de trading de v10.3 con toda la instrumentación de v10.5.

**Pendiente:** Pablo investigando IBM Trial para integrar Weather Underground como fuente de datos. El upgrade real es cambiar la fuente, no ajustar la confianza del modelo.

### Sesión 30 (continuación) — v10.6.1

**Verificación completa del Dashboard** (Claude Code — Opus):

- Aritmética de "Balance por tipo de cierre": verificada correcta (TP $+9.03/4, SL $-14.21/10, etc.)
- Scoreboard: conteo de puntos verificado evento por evento contra agent_events.jsonl — correcto
- Posible issue: "Ganadas por resolución = 0" cuando Wellington ganó por resolución — a verificar en producción
- Bug encontrado: `get_logic_series_stats()` no ordenaba `closed` por `closed_at` antes de tomar ventana de drawdown
- Redundancia: unlock "Confiar en métricas de serie" era idéntico a "Activar win rate y drawdown"

**Cambios realizados:**
- Fix drawdown: ordena por `closed_at` antes de `[-DRAWDOWN_WINDOW:]`
- Alerta bankroll bajo: Telegram + dashboard alertan cuando cartera cae bajo $5
- Unlock redundante eliminado (de 6 a 5 items)
- Scoreboard: 3 eventos nuevos de sesión 30
- 338/338 tests

**Nota de proceso:** Se detectó que `replace_all=true` en actualizaciones de CONTEXTO.md modificaba entradas históricas (ej: "serie v10.5" en descripción de lo que hizo Codex en v10.5.6 se cambió a "serie v10.6"). Corregido. Regla: nunca usar replace_all para versiones en docs — editar solo las líneas específicas.

---

## Sesión 31 — v10.6.2 (29 mar 2026, local)

**Disparador:** revisión crítica posterior de `v10.6.1` detecta que la alerta de bankroll bajo puede dispararse por un fallo temporal de API y no solo por caída real de fondos.

**Diagnóstico (Codex):**

1. **Falso positivo por API incierta.** `_get_portfolio_and_positions()` puede devolver `cash=0.0`, `cash_ok=False` y `api_error` cuando falla la lectura de balance o posiciones. La alerta de `v10.6.1` usaba igualmente ese `0.0` y podía pedir “recargar” sin que la cartera real hubiera cambiado.

2. **Rearme demasiado rígido.** La flag `low_bankroll_alerted` solo se limpiaba cuando la cartera superaba `LOW_BANKROLL_THRESHOLD * 2`, así que una recuperación parcial razonable (`$4.8 -> $6.3`, por ejemplo) no rearmaba la alerta para una caída posterior real.

3. **Cobertura insuficiente.** `verify_before_deploy.py` comprobaba la presencia de strings y algo de wiring, pero no validaba funcionalmente el trigger real, el no-trigger por API incierta ni el reset con margen.

**Cambios realizados:**
- `BOT_VERSION` actualizado a `v10.6.2`;
- nueva constante `LOW_BANKROLL_RESET_MARGIN=1.0`;
- `run_observability_alerts()` exige `cash_ok` y ausencia de `api_error` antes de disparar la alerta de bankroll bajo;
- `get_dashboard_alert_summary()` solo muestra la alerta crítica de bankroll cuando la señal de cartera es fiable;
- el reset pasa a usar `LOW_BANKROLL_THRESHOLD + LOW_BANKROLL_RESET_MARGIN` en lugar de `2x` el umbral;
- `agent_events.jsonl` añade evento de sesión 31 para el scoreboard;
- `verify_before_deploy.py` sube a `348/348` con casos funcionales nuevos:
  - dashboard muestra alerta con datos fiables;
  - dashboard oculta alerta con API incierta;
  - Telegram dispara al cruzar umbral real;
  - no persiste flag con API incierta;
  - rearma la alerta al salir de zona roja con margen;
- `CONTEXTO.md` y este historial quedan alineados con `v10.6.2`.

**Resultado:** `v10.6.2` quedó listo en local con `348/348` tests. Posteriormente se hizo commit (`29049a1`) y push a `origin/main`. El estado de deploy de Railway no se re-verificó durante la sesión de investigación siguiente.

---

## Sesión 32 — Investigación estratégica + preparación de v10.6.3

**Fecha:** 2026-03-30
**Herramientas:** Codex + Claude Code (Opus) + revisión cruzada
**Versión del código al investigar:** `v10.6.2`
**Cambios de código:** ninguno funcional; sesión centrada en investigación, síntesis y preparación del siguiente bloque técnico

**Trabajo realizado:**
- Codex investigó competidores, reglas reales de resolución en Polymarket y microestructura básica del mercado;
- Claude Code realizó una investigación paralela y una revisión adversarial del informe de Codex;
- se prepararon tres artefactos nuevos en el repo:
  - `RESEARCH_CODEX_HANDOFF_2026-03-30.md`
  - `RESEARCH_CLAUDE_2026-03-30.md`
  - `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`

**Hallazgos compartidos de mayor impacto:**
- Polymarket temperature resuelve con Weather Underground, no con Open-Meteo;
- Dallas está mal mapeada en el bot: código actual `KDFW`, reglas verificadas `KDAL`;
- la auditoría `forecast_vs_real` no debe interpretarse como verdad de resolución, porque no compara contra la fuente real que liquida Polymarket;
- la dirección estratégica correcta sigue siendo `resolution fidelity first`.

**Correcciones / matices surgidos en la revisión cruzada:**
- Claude reforzó correctamente el hallazgo de Dallas y la debilidad real de la auditoría;
- Claude añadió `Degen Doppler` como competidor/referencia más directa;
- se detectó que una parte de la corrección sobre `WeatherClaw` estaba contaminada por confusión de dominio (`.com` vs `.xyz`), así que no debía tomarse sin verificar.

**Roadmap resultante para la siguiente sesión:**
1. Fix Dallas `KDAL`
2. Crear capa formal de resolución (`RESOLUTION_ICAO` + URLs WU)
3. Renombrar/documentar la pseudo-auditoría actual para no presentar Open-Meteo como “real”
4. Añadir tests de estos tres puntos
5. No tocar todavía lógica de trading, scheduling ni nuevas features

**Resultado:** el proyecto queda listo para abrir una sesión nueva de implementación acotada (`v10.6.3`) con contexto claro y sin reabrir la investigación desde cero.

---

## Sesión 33 — v10.6.3 (30 mar 2026, local)

**Disparador:** ejecutar el bloque técnico acordado tras la investigación de la sesión 32 sin tocar lógica de trading ni scheduling.

**Diagnóstico (Codex):**

1. **Dallas seguía mal mapeada.** `RESOLUTION_STATIONS["Dallas"]` apuntaba a `Dallas Fort Worth / KDFW` cuando la investigación cruzada dejó como estación correcta `Dallas Love Field / KDAL`.

2. **La capa de resolución seguía implícita.** Había coordenadas para forecast, pero no existía todavía un mapping formal `ciudad -> ICAO -> URL WU` que dejara clara la referencia de settlement revisada para ciudades activas y bloqueadas.

3. **La pseudo-auditoría inducía a error.** `forecast_vs_real` sonaba a validación contra la fuente real, pero el código seguía reconsultando `get_forecast()` de Open-Meteo. Había que hacer explícito que solo mide deriva `forecast original vs forecast posterior`.

4. **Un test funcional viejo de `/traders` quedó frágil por calendario.** Dependía de fechas fijas ya pasadas, así que empezó a fallar aunque la funcionalidad siguiera bien.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.3`;
- `RESOLUTION_STATIONS["Dallas"]` cambia a `{"lat": 32.8459, "lon": -96.8510, "name": "Dallas Love Field"}`;
- nueva capa `RESOLUTION_ICAO` con `icao + wu_url` para las ciudades activas, las bloqueadas y el resto del mapping actual;
- nuevo helper `_wu_history_url()` para centralizar la plantilla WU;
- la pseudo-auditoría se renombra a `audit_check_open_meteo_forecast_drift()`;
- se mantiene la clave legacy `forecast_vs_real` en `audit.json` solo por compatibilidad, pero docstrings, comentarios, campos y logs nuevos ya hablan de `forecast_original`, `forecast_posterior` y `forecast posterior Open-Meteo`;
- los registros de oportunidad incorporan `resolution_icao` y `resolution_wu_url` sin alterar la lógica de trading;
- `verify_before_deploy.py` sube a `358/358` con checks nuevos para:
  - Dallas `KDAL` / Love Field;
  - `RESOLUTION_ICAO` con las 4 activas y cobertura de ciudades bloqueadas;
  - auditoría sin `real=` y documentada como Open-Meteo posterior;
- el test funcional de `/traders` pasa a usar fechas relativas para no romperse con el calendario.

**Resultado:** `v10.6.3` queda listo en local con `358/358` tests. Trading, sizing, ejecución y scheduling no se tocaron; el cambio queda acotado a resolución, nomenclatura honesta de auditoría y trazabilidad.

---

## Sesión 34 — v10.6.4 (30 mar 2026, local)

**Disparador:** usar la base de `v10.6.3` para crear una capa observada separada con NOAA NCEI, evitando depender de Weather Underground scraping y sin tocar la lógica de trading.

**Diagnóstico (Codex):**

1. **La siguiente capa útil ya no era forecast-vs-forecast.** Hacía falta una auditoría observada separada que no reutilizara Open-Meteo y que no se presentara como “resolución real”.

2. **El riesgo técnico estaba en los station IDs.** NOAA Access Data Service requiere station IDs explícitos; para las 4 activas había que añadir `noaa_station_id` en `RESOLUTION_ICAO` y evitar una resolución dinámica `ICAO -> NOAA`.

3. **Buenos Aires era el punto más incierto.** Se dejó `87576099999` como candidato explícito hasta validar el spike NCEI, en vez de esconder la incertidumbre.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.4`;
- `RESOLUTION_ICAO` añade `noaa_station_id` explícito para:
  - Dallas `72258303927`
  - Chicago `72530094846`
  - Atlanta `72219013874`
  - Buenos Aires `87576099999`;
- nueva clave `OBSERVED_AUDIT_KEY = "observed_vs_forecast"` separada del legacy `forecast_vs_real`;
- nuevo helper `_parse_noaa_tmp_c()` para convertir `TMP` de NOAA;
- nuevo helper `fetch_noaa_observed_max()` contra NOAA NCEI Access Data Service;
- nueva auditoría `audit_check_resolution_truth(dl)`:
  - solo para las 4 ciudades activas;
  - solo con lag mínimo de 2 días;
  - guarda `city, date, icao_used, noaa_station_id, observed_temp_c, forecast_temp_c, error_c, abs_error_c, side, edge_pct, source="noaa_ncei", checked_at`;
  - wording explícito de `observed proxy`;
- `main()` ahora ejecuta esta auditoría junto a la legacy del paso `0.6`;
- `verify_before_deploy.py` sube a `371/371` con:
  - checks estructurales de `noaa_station_id`, `observed_vs_forecast`, funciones nuevas y `source=noaa_ncei`;
  - test funcional del helper NOAA con respuesta simulada;
  - test funcional de la auditoría para asegurar que no toca London y respeta el lag de 2 días.

**Resultado:** `v10.6.4` queda listo en local con `371/371` tests. La nueva capa NOAA mejora la observabilidad, pero se mantiene correctamente etiquetada como `observed proxy`, no como fuente real de settlement.

**Post-scriptum del spike Buenos Aires:** NOAA HOMR devolvió el registro vigente de `SAEZ` como `MINISTRO PISTARINI` (`ncdcStnId=30132405`, WMO `87576`) y una prueba directa contra `global-hourly` confirmó que el identificador operativo para el bot es `87576099999`; `30132405` y `ARI0000SAEZ` no devolvieron filas en ese endpoint.

---

## Sesión 35 — v10.6.5 (30 mar 2026, local)

**Disparador:** una vez cerrada la capa `observed_vs_forecast`, hacía falta separar en el dashboard la métrica NOAA nueva del histórico legacy para poder leer bias sin contaminar la serie de trading ni mezclar semánticas.

**Diagnóstico (Codex):**

1. **No convenía partir el dashboard de trading.** PnL, win rate y drawdown siguen siendo comparables porque `v10.6.5` no toca la lógica operativa.

2. **Sí convenía partir la observabilidad de forecast.** `observed_vs_forecast` (NOAA) y `forecast_vs_real` legacy miden cosas distintas y no debían compartir KPIs ni narrativa.

3. **La muestra necesitaba umbrales explícitos.** El dashboard tenía que dejar claro que `n < 3` significa `acumulando muestra...`, que el bias por ciudad pide `>=3` casos por ciudad y que la lectura global gana sentido a partir de `10` casos.

**Cambios realizados:**
- `BOT_VERSION` sube a `v10.6.5`;
- nuevos builders:
  - `build_dashboard_forecast_quality()` para `observed_vs_forecast`;
  - `build_dashboard_legacy_forecast_drift()` para el bloque histórico `forecast_vs_real`;
- `build_dashboard_snapshot()` incorpora ambos bloques sin tocar trading, scheduling ni auditorías;
- `templates/dashboard.html` añade:
  - `Calidad Forecast Observada (NOAA)` con `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos;
  - `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y último registro prominentes;
- `verify_before_deploy.py` sube a `386/386` con:
  - checks estructurales de los nuevos builders y thresholds de muestra;
  - tests funcionales del bloque NOAA y del bloque legacy;
  - snapshot tests para asegurar que ambos bloques llegan al dashboard.

**Resultado:** `v10.6.5` queda listo en local con `386/386` tests. El dashboard ya separa claramente NOAA observado del drift legacy y deja intacta toda la capa de trading.

---

## Sesión 36 — sync de bankroll tras recarga manual (30 mar 2026, local)

**Disparador:** tras una recarga manual de fondos en Polymarket, apareció una inconsistencia residual: Railway seguía operando con `BANKROLL=25.00`, pero el fallback local en `bot.py` todavía decía `15.00`.

**Diagnóstico (Codex):**

1. **La calibración operativa real seguía siendo $25.** Contexto, tests y Railway apuntaban a `BANKROLL=25.00`; el `15.00` en código era un remanente antiguo.

2. **El bug no afectaba a producción mientras Railway inyectara la variable.** Pero sí podía inducir a errores al leer el código, correr el bot sin env vars o razonar sobre sizing local.

3. **La recarga devolvía al bot a su zona objetivo.** Se registró un depósito manual de `+$14.99`, coherente con seguir operando alrededor del bankroll objetivo configurado.

**Cambios realizados:**
- `bot.py` sincroniza el fallback local `BANKROLL` de `$15.00` a `$25.00`;
- `verify_before_deploy.py` añade un check explícito para fijar `BANKROLL default = 25.00`;
- `CONTEXTO.md` se actualiza con:
  - la recarga manual `+$14.99`;
  - el nuevo estado de `origin/main` en `v10.6.5`;
  - la trazabilidad de esta sincronización;
- `HISTORIAL_SESIONES.md` registra la sesión como cierre de la inconsistencia post-recarga.

**Resultado:** código local, tests, contexto y configuración real vuelven a quedar alineados alrededor de `BANKROLL=$25.00`, sin bump de versión y sin tocar lógica de trading.

---

## Sesión 37 — playbook operativo + guardrails de scoreboard (30 mar 2026, local)

**Disparador:** apareció una desalineación de proceso: el estado humano (`CONTEXTO.md`, `HISTORIAL_SESIONES.md`) estaba actualizado, pero el scoreboard live seguía anclado en la sesión 31 porque `agent_events.jsonl` no formaba parte del cierre obligatorio de sesión.

**Diagnóstico (Codex):**

1. **El problema no era de estado, sino de protocolo.** `CONTEXTO.md` y `HISTORIAL_SESIONES.md` seguían bien; la capa máquina del Dashboard no estaba integrada en el checklist de cierre.

2. **El scoreboard tiene una fuente distinta.** El Dashboard no lee docs; lee `agent_events.jsonl`, que luego se sincroniza al Volume con `_sync_agent_events_seed()`.

3. **Faltaban guardrails.** Había memoria humana, pero no una regla verificable que obligara a cerrar docs y scoreboard juntos.

**Cambios realizados:**
- nuevo `OPERATIONS_PLAYBOOK.md` con:
  - checklist de inicio;
  - checklist de cierre;
  - protocolo de deploy;
  - reglas de scoreboard;
  - workflow Pablo + Codex + Claude;
  - regla de hardening: todo error deja guardrail;
- nuevo helper `tools/append_agent_event.py` para registrar eventos del scoreboard sin editar JSONL a mano;
- `CLAUDE.md` y `CONTEXTO.md` pasan a remitir explícitamente al playbook;
- `verify_before_deploy.py` añade checks para:
  - existencia del playbook;
  - existencia del helper;
  - referencia al playbook en `CONTEXTO.md` y `CLAUDE.md`;
  - regla de hardening;
  - helper con bloqueo de duplicados;
  - consistencia entre la sesión documentada más reciente y `agent_events.jsonl`;
- `_sync_agent_events_seed()` deja de fallar en silencio y ahora loggea warning si el merge del scoreboard falla;
- se sincroniza el scoreboard live en Railway para añadir sesiones 32-36.

**Resultado:** el sistema gana una capa nueva de robustez de proceso. A partir de aquí, estado, historial, scoreboard y tests quedan conectados por un playbook explícito en vez de depender de memoria manual. `verify_before_deploy.py` queda en `396/396`.

---

## Sesión 38 — scoreboard limpio + regla de puntuación (30 mar 2026, local + Railway)

**Disparador:** el scoreboard live mostraba una diferencia engañosa entre Codex y Claude porque el `agent_events.jsonl` persistente del Volume contenía filas duplicadas/corruptas y el dashboard solo mira los últimos `30` eventos válidos.

**Diagnóstico (Codex):**

1. **La métrica estaba siendo contaminada por datos, no solo por scoring.** Había filas duplicadas válidas de Codex y también líneas malformadas antiguas en el fichero live.

2. **El límite de `30` eventos amplificaba el sesgo.** Los duplicados no solo sumaban puntos de más, sino que expulsaban un evento antiguo de Claude del corte visible.

3. **Faltaba una regla explícita de puntuación.** El playbook cubría el cierre de sesiones, pero no dejaba escrito todavía que una revisión sin delta no debe puntuar.

**Cambios realizados:**
- limpieza quirúrgica del `agent_events.jsonl` live en Railway hasta devolverlo a `29` líneas canónicas;
- `load_agent_events()` pasa a deduplicar eventos equivalentes por clave normalizada (`timestamp + session + agent + type + title normalizado`);
- `OPERATIONS_PLAYBOOK.md` añade la regla: validación o aprobación sin delta = `0 puntos` o sin evento;
- `verify_before_deploy.py` añade:
  - un check de la nueva regla de scoring;
  - un test funcional para asegurar que `load_agent_events()` deduplica equivalentes con acentos/símbolos distintos.

**Resultado:** el scoreboard live queda saneado, el loader se vuelve robusto ante duplicados equivalentes y el protocolo deja por escrito que “validar sin cambiar nada” no debe generar puntos. `verify_before_deploy.py` sube a `397/397`.

---

## Sesión 39 — research final Lean Six Sigma + foco NOAA en Telegram (30 mar 2026, local)

**Disparador:** una vez cerrada la discusión metodológica, hacía falta traducir solo lo útil al sistema real y mover el seguimiento diario hacia el cuello de botella actual: `measurement / resolution fidelity`.

**Diagnóstico (Codex):**

1. **Lean Six Sigma completo no encaja ahora.** El sistema sigue en discovery/stabilization; añadir CTQs, A3s o control charts ahora sería más fricción que valor.

2. **Sí encajan dos guardrails pequeños.** Un premortem corto para cambios core y un lenguaje mínimo compartido (`fallo real`, `limitacion conocida`, `ruido`) ayudan a operar con más claridad sin crear burocracia.

3. **El gap operativo no era el menú de Telegram.** El problema real era no tener una vista rápida del estado NOAA desde el canal donde ya se monitoriza el bot.

**Cambios realizados:**
- se consolida `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` con recomendación final `recomiendo no adoptar`, salvo `FMEA-lite` y definiciones mínimas;
- `OPERATIONS_PLAYBOOK.md` añade:
  - `premortem corto para cambios core`;
  - definición operativa mínima de `fallo real del sistema`, `limitacion conocida` y `ruido de mercado`;
- `bot.py` amplía `run_observability_alerts()` con hitos NOAA one-shot sobre `observed_vs_forecast`:
  - primer caso global;
  - muestra mínima `>=3`;
  - muestra global útil `>=10`;
  - ciudad con primera muestra;
  - ciudad interpretable `>=3`;
- `bot.py` añade `/noaa` y `/observabilidad` como vista Telegram específica de `sample`, `MAE`, `bias`, cobertura y últimos casos;
- el menú principal de Telegram se mantiene sin poda agresiva;
- `verify_before_deploy.py` sube a `416/416` con:
  - test de `/noaa`;
  - test de idempotencia para alertas NOAA;
  - check explícito de `state.setdefault("milestones", {})`.

**Resultado:** el proyecto sale de esta sesión con criterio metodológico más claro, un playbook mínimo más útil y una capa de seguimiento diario mejor alineada con el cuello de botella real. `v10.6.5` queda lista para deploy sin tocar lógica de trading.

---

## Sesión 41 — v10.6.6 allowlist ACTIVE_TRADING_CITIES (30 mar 2026, local)

**Disparador:** tras el diagnóstico de la sesión 40, quedó claro que `BLOCKED_CITIES` como lista negra no bastaba: seguían entrando mercados de ciudades sin validación NOAA/WU como NYC, Munich, Seoul o Tokyo.

**Diagnóstico (Codex):**

1. **El bug estaba en el modelo de filtro.** Una blacklist evita reincidir en ciudades ya problemáticas, pero no protege frente a ciudades nuevas todavía no validadas.

2. **La corrección debía afectar solo a entradas nuevas.** `manage_positions` no se toca: el bot debe seguir gestionando SL/TP/reeval en cualquier posición ya abierta, incluso si nació fuera del universo validado.

3. **La solución correcta era un allowlist explícito.** Si ahora mismo solo hay 4 ciudades con monitoreo NOAA y observabilidad suficiente, el scan debe restringirse a esas 4 y dejar trazabilidad clara en `decisions.log`.

**Cambios realizados:**
- `bot.py` sube a `v10.6.6`;
- añade `ACTIVE_TRADING_CITIES` justo después de `BLOCKED_CITIES`, con default:
  - `Chicago`
  - `Atlanta`
  - `Dallas`
  - `Buenos Aires`
- el scan de mercados añade un filtro nuevo:
  - si la ciudad no está en `ACTIVE_TRADING_CITIES`, no entra en candidatos para BUY;
  - se registra `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`;
  - el resumen de filtros ahora separa también cuántos mercados quedaron fuera del allowlist;
- `manage_positions` queda intacta;
- `verify_before_deploy.py` añade checks para:
  - existencia de `ACTIVE_TRADING_CITIES`;
  - default correcto con las 4 activas;
  - presencia del filtro de allowlist y del log de skip;
- la prueba de idempotencia NOAA ya existente se mantiene como guardrail vigente;
- la suite sube a `419/419`.

**Resultado:** el bot deja de abrir posiciones nuevas en ciudades no validadas sin tocar la gestión de posiciones existentes. `v10.6.6` queda lista para push/deploy como fix quirúrgico del bug #15.

---

## Sesión 42 — v10.6.7 dashboard estado por ciudad (30 mar 2026, local)

**Disparador:** tras cerrar el allowlist de entradas nuevas, faltaba una vista clara para saber si una ciudad está operando de verdad, bloqueada, solo como referencia histórica o todavía sin observabilidad suficiente.

**Diagnóstico (Codex):**

1. **El dashboard NOAA era demasiado estrecho.** Mostraba cobertura de las 4 activas, pero no dejaba claro qué pasaba con ciudades bloqueadas, fuera del allowlist o con histórico útil.

2. **Aún no toca automatizar promociones.** La necesidad inmediata no era construir ya `watchlist / shadow / canary`, sino ver la foto actual por ciudad con datos honestos.

3. **La tabla correcta debía cruzar tres capas.** Operativa real (`ACTIVE_TRADING_CITIES` / `BLOCKED_CITIES`), observabilidad NOAA y cierres validados por ciudad.

**Cambios realizados:**
- `bot.py` sube a `v10.6.7`;
- nuevo builder `build_dashboard_city_observation()`:
  - cruza allowlist, bloqueo, `observed_vs_forecast` y `get_city_accuracy()`;
  - clasifica por ciudad `Trading`, `NOAA`, `Historico` y `Estado actual`;
  - distingue estados como `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` y `Sin observabilidad`;
- `build_dashboard_snapshot()` incorpora `city_observation` sin mezclarlo con el bloque NOAA puro;
- `templates/dashboard.html` sustituye la lista simple de cobertura por la tabla `Estado de observacion por ciudad`;
- `verify_before_deploy.py` sube a `426/426` con:
  - check estructural del builder nuevo;
  - check del bloque nuevo en el template;
  - test funcional para `Chicago`, `London` y `New York City`;
  - test de snapshot para asegurar que `city_observation` llega al dashboard.

**Resultado:** el dashboard ya enseña de un vistazo qué ciudades están en operativa real, cuáles siguen bloqueadas y cuáles solo tienen valor como referencia mientras falta una capa futura de `watchlist / shadow / canary`. `v10.6.7` queda validada en local con `426/426`.

---

## Sesión 43 — v10.6.8 control center discovery / stabilization (30 mar 2026, local)

**Disparador:** tras ver que el dashboard y Telegram seguían demasiado cargados, hacía falta una capa 1 explícita que priorizara salud real, incidentes, universo activo, crecimiento NOAA y acción recomendada sin tocar trading, exits ni scheduler.

**Diagnóstico (Codex):**

1. **La información importante estaba mezclada con demasiado detalle.** El dashboard actual sí contenía casi todo, pero no en un orden que permitiera responder rápido `¿está sano?`, `¿hay que actuar?` o `¿estamos aprendiendo?`.

2. **Telegram tenía piezas útiles pero no una vista principal operativa.** `/estado`, `/noaa`, `/accuracy` y `/detalle` existían, pero obligaban a reconstruir mentalmente la capa 1.

3. **La solución correcta era jerárquica, no decorativa.** Había que construir una capa 1 honesta sobre alertas, allowlist y NOAA ya existentes, mover el detalle a capas inferiores y dejar claro qué es incidente real vs limitación de aprendizaje.

**Cambios realizados:**
- `bot.py` sube a `v10.6.8`;
- nuevo builder `build_dashboard_focus_center()`:
  - resume salud operativa, necesidad de intervención, limitador dominante, estado de aprendizaje y acción recomendada;
  - reutiliza `get_dashboard_alert_summary()`, `build_dashboard_forecast_quality()`, `build_dashboard_city_observation()` y muestra quick stats del universo activo;
  - separa incidentes operativos reales de gaps de `measurement / NOAA`;
- `build_dashboard_snapshot()` incorpora `focus` como nueva capa 1 del dashboard;
- Telegram añade `/focus` como vista principal corta y el menú se reordena para poner `Focus` y observabilidad al frente, manteniendo `/estado`, `/noaa`, `/accuracy` y `/detalle` como segunda capa;
- `templates/dashboard.html` abre ahora con un bloque `Control Center Discovery / Stabilization` y deja el detalle extendido dentro de `Capa 3`;
- `static/dashboard.css` añade layout y estilos específicos para la capa 1, los quick stats y el panel colapsable de detalle;
- `verify_before_deploy.py` sube a `440/440` con:
  - checks estructurales del builder nuevo;
  - checks del template/CSS de `focus`;
  - test funcional del `focus center`;
  - test funcional de `/focus`;
  - test de snapshot para asegurar que `focus` llega al dashboard.

**Resultado:** queda una UX operativa mucho más clara para discovery/stabilization: en 10-15 segundos ya se puede leer si el sistema está sano, si hoy toca actuar, qué lo limita, si NOAA está enseñando algo útil y cuál es la acción recomendada. `v10.6.8` queda validada en local con `440/440` tests, sin tocar lógica de trading, exits, scheduler ni gestión de posiciones.

---

## Sesión 44 — v10.6.9 mission HUD discovery / stabilization (30 mar 2026, local)

**Disparador:** una vez resuelta la jerarquía básica de capa 1, el siguiente paso era convertirla en una interfaz mucho más enfocada y visual, con estética de videojuego operativo, para seguir la prioridad actual sin volver a llenar el dashboard de ruido.

**Diagnóstico (Codex):**

1. **La capa 1 ya era correcta en contenido, pero todavía demasiado “dashboard”.** Faltaba un lenguaje visual de misión, progreso y estado que ayudara a fijar la atención en la prioridad actual.

2. **La prioridad no es trading, sino discovery/stabilization.** Por tanto, el HUD tenía que representar `salud`, `allowlist vs NOAA`, `crecimiento de muestra` y `aprendizaje útil`, no PnL táctico ni gestión de posiciones.

3. **La interactividad debía ser ligera y segura.** Lo correcto era añadir tabs y paneles visuales alimentados por el snapshot actual, sin tocar la lógica core ni crear una capa JavaScript compleja.

**Cambios realizados:**
- `bot.py` sube a `v10.6.9`;
- `build_dashboard_city_observation()` expone campos de presentación adicionales (`observed_count`, `progress_pct`, `trades`, `win_rate`, etc.) para alimentar visuales sin alterar decisiones;
- `build_dashboard_focus_center()` gana:
  - `mission` actual;
  - `health_score`;
  - `tracks` de progreso;
  - `stage_path` de prioridad;
  - `city_race` para cobertura NOAA por ciudad;
- `templates/dashboard.html` añade una nueva cabecera `Mission HUD · Discovery / Stabilization` por encima del bloque anterior y oculta la versión previa como fallback;
- el HUD nuevo incorpora:
  - tarjeta principal de misión;
  - `System HP`;
  - ruta operativa por etapas;
  - tabs `Overview / Progress / Cities`;
  - barras de progreso por misión;
  - panel `City race` y `Operator console`;
- `static/dashboard.css` redefine la capa 1 con estética HUD, grid visual, scan lines, chips, barras y paneles de misión;
- aparece `static/dashboard.js` para alternar paneles de la capa 1 sin recargar la página;
- se borran los ficheros antiguos `RESEARCH_LEAN_SIX_SIGMA*.md` dejando solo `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md`;
- `verify_before_deploy.py` sube a `447/447` con checks nuevos de:
  - `dashboard.js`;
  - template `Mission HUD`;
  - tracks y `city_race`;
  - tabs interactivas;
  - shape funcional ampliada de `build_dashboard_focus_center()`.

**Resultado:** la capa 1 deja de sentirse como un tablero genérico y pasa a leerse como una misión operativa: qué proteger, qué está bloqueando, cuánto progreso llevamos y dónde mirar después. Queda lista para previsualización funcional y para una siguiente iteración centrada en tendencias temporales de aprendizaje, no en más detalle táctico.

---

## Sesión 45 — v10.6.10 focus readability + Railway validation (30 mar 2026)

**Disparador:** tras la primera preview real del `Mission HUD`, la lectura seguía costando: la alerta `signals.json stale` aparecía demasiadas veces, la tabla de ciudades era pesada y el modo oscuro no ayudaba a entender rápido la prioridad operativa.

**Diagnóstico (Codex):**

1. **La capa 1 seguía exagerando un síntoma secundario.** `signals.json stale` es una alerta real, pero no debe ocupar toda la lectura cuando el bloqueo dominante sigue siendo `NOAA / muestra / cobertura`.

2. **La tabla de ciudades era correcta, pero no legible como primera pantalla.** Hacía falta agrupar por prioridad operativa y no pedir una lectura fila a fila de 14 ciudades.

3. **La estética debía ayudar a decidir, no solo a impresionar.** En esta fase discovery/stabilization, el contraste y la claridad pesan más que un look oscuro agresivo.

**Cambios realizados:**
- `bot.py` sube a `v10.6.10`;
- `build_dashboard_focus_center()`:
  - relega `signals.json stale` a señal secundaria cuando el bloqueo real es de muestra/cobertura NOAA;
  - deja más clara la lectura de `salud`, `intervención`, `limitador` y `acción recomendada`;
- `build_dashboard_city_observation()` expone grupos listos para UI:
  - `active_rows`;
  - `watch_rows`;
  - `blocked_rows`;
- `templates/dashboard.html` sustituye la tabla larga por zonas operativas:
  - `Universo operativo`;
  - `Seguimiento y referencia`;
  - `Archivo de ciudades fuera de juego`;
- `static/dashboard.css` cambia la experiencia a modo claro por defecto y añade estilos específicos para tarjetas/zonas de ciudad;
- `verify_before_deploy.py` sube a `449/449` con checks nuevos de:
  - modo claro;
  - agrupación visual de ciudades;
  - shape funcional de `active_rows / watch_rows / blocked_rows`;
- se añade `tools/preview_dashboard.py` para levantar solo el dashboard local sin arrancar todo el bot y sin depender de auth.

**Resultado:** la capa 1 conserva el enfoque de misión, pero gana legibilidad operativa real. El dashboard ya no repite tanto una alerta secundaria, las ciudades se entienden como `operativas / seguimiento / bloqueadas` y `v10.6.10` quedó validada también en Railway: `healthz` respondió `200` con `version=v10.6.10` y el snapshot live confirmó modo `REAL`, próxima ejecución `23:00 UTC`, `signals ok`, `141` señales accionables, `0/10` casos NOAA y una única alerta activa de `accuracy` por ciudades.

---

## Sesión 46 — auditoría NOAA `observed_vs_forecast` + fix mínimo local (31 mar 2026)

**Disparador:** Railway `v10.6.10` seguía mostrando `NOAA 0/10` y `0/4` ciudades interpretables pese a que ya había actividad real en Chicago, Atlanta, Dallas y Buenos Aires. Había que distinguir con honestidad entre “todavía no hay muestra” y “el pipeline NOAA está roto”.

**Diagnóstico (Codex):**

1. **La entrada en `observed_vs_forecast` estaba bien definida, pero demasiado exigente para depurarla a ojo.** Un caso solo entra si en `performance.json` existe un `BUY`, la ciudad está en `OBSERVED_AUDIT_CITIES`, la fecha se puede parsear, hay `noaa_station_id`, el `city|date` no está duplicado y han pasado al menos `2` días (`NOAA_OBSERVED_LAG_DAYS`).

2. **No era solo falta de muestra.** La auditoría reconstruyó al menos `7` casos `city|date` ya elegibles frente a `0` registros reales en `audit.json -> observed_vs_forecast`. Evidencia mínima: `Chicago|2026-03-25`, `Chicago|2026-03-26`, `Chicago|2026-03-28`, `Atlanta|2026-03-27`, `Dallas|2026-03-22`, `Dallas|2026-03-28`, `Buenos Aires|2026-03-28`.

3. **El cuello de botella real estaba en la fuente NOAA elegida.** El código dependía de `global-hourly` reconstruyendo el máximo desde `TMP`, pero probes reales sobre fechas 2026 devolvían vacío en varios casos donde `daily-summaries` sí devolvía `TMAX`. Se comprobó, por ejemplo, que `Dallas 2026-03-22`, `Chicago 2026-03-25/26` y `Atlanta 2026-03-27` ya estaban disponibles por `daily-summaries`.

**Cambios realizados:**
- `bot.py` mantiene intacta la lógica de trading y endurece solo NOAA/observabilidad:
  - añade `noaa_daily_station_id` en `RESOLUTION_ICAO` para Chicago, Atlanta y Dallas;
  - incorpora `fetch_noaa_daily_tmax()` para `daily-summaries`;
  - renombra el fetch original a `_fetch_noaa_observed_max_hourly()`;
  - crea un wrapper `fetch_noaa_observed_max()` que prueba primero `daily-summaries/TMAX` y cae a `global-hourly` si no hay dato;
  - `audit_check_resolution_truth()` ahora guarda también `noaa_daily_station_id` y `observed_dataset` para dejar trazabilidad de qué dataset produjo el observado.
- `verify_before_deploy.py` sube a `451/451` con:
  - checks estructurales para `noaa_daily_station_id`;
  - test del helper `fetch_noaa_daily_tmax()`;
  - actualización del test funcional del wrapper NOAA para esperar `daily-summaries_tmax`;
  - test del pipeline de auditoría asegurando persistencia de `observed_dataset`.
- tras review adversarial adicional:
  - `fetch_noaa_daily_tmax()` añade el mismo guard de lag que ya usaba el path hourly para no hacer requests innecesarios si se invoca de forma directa;
  - `verify_before_deploy.py` recupera un test explícito del fallback `daily vacío -> hourly`;
  - la suite queda en `453/453`.

**Resultado:** el diagnóstico correcto al cierre de la sesión es **bug real de observabilidad NOAA**, no mera falta de tiempo. Sí faltaba muestra para algunas fechas recientes, pero ya existían casos elegibles suficientes como para esperar `n > 0` en producción. El fix queda validado en local con `453/453` tests, sin tocar trading, sigma/Kelly, exits, scheduler ni gestión de posiciones. Buenos Aires queda temporalmente en fallback `global-hourly` porque todavía no se validó una estación diaria fiable. La idea de una futura capa `shadow sample` queda solo como propuesta segura para más adelante, no como cambio aplicado hoy.

---

## Sesiones aún no reconstruidas con certeza

Las sesiones 4 a 8, y las 10 a 18, no aparecen nombradas explícitamente en los commits que tenemos a mano. El trabajo de esas sesiones sí existe, pero hoy está representado como:

- iteraciones por versión;
- bloques de commits en Git;
- y contexto consolidado en `CONTEXTO.md`.

Por ahora, lo más honesto es tratarlas como `inferidas` y no inventar numeración exacta.

---

## Cómo mantener este archivo desde ahora

- `CONTEXTO.md`: estado actual del proyecto.
- `HISTORIAL_SESIONES.md`: append-only, sin reescribir entradas pasadas salvo para corregir errores factuales.
- Git: fuente de verdad de diffs, autores y timestamps.

Regla recomendada:

- cuando una sesión cierre, añadir una entrada nueva aquí;
- si una sesión antigua se reconstruye mejor desde Git, marcarla como `reconstruida` o `corregida`, sin borrar la entrada original.
- antes de cada push relevante, revisar si también hay que actualizar `CONTEXTO.md` para la foto actual y este archivo para la memoria histórica.
