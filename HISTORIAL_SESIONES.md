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
