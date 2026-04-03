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
| 2026-03-31 | Explícita | Sesión 47 | `—` | Nueva capa `trade_lifecycle`: trazabilidad completa por posición con backfill desde `performance+postmortem`, snapshots en gestión e intra-ciclo, observación post-exit y suite final en `467/467`, sin tocar trading. |
| 2026-03-31 | Explícita | Sesión 48 | `—` | Hardening fase 1 de `trade_lifecycle`: matching por `id` reconstruido, coalescing defensivo, bloque `integrity`, fix del caso real de cierres huérfanos y suite en `470/470`; validación live demuestra `92 -> 80` records únicos al reconstruir. |
| 2026-03-31 | Explícita | Sesión 49 | `—` | Hotfix del coalescing de `trade_lifecycle` tras detectar en Railway `unhashable type: 'list'`; se sustituye la comparación inválida con sets `{None, "", [], {}}` por `_lifecycle_is_empty()`, se añade regresión del merge de contextos duplicados, se normaliza `agent_events.jsonl` a UTF-8 y la suite queda en `472/472`. |
| 2026-03-31 | Explícita | Sesión 50 | `—` | Recap operativo + hardening Railway CLI: validación live del hotfix (`87` records, `0` ids duplicados) y nuevo wrapper `tools/railway_safe.ps1` para limpiar proxies de proceso, junto con regla operativa en el playbook para no repetir el bucle de auth/`invalid_grant`. |
| 2026-03-31 | Explícita | Sesión 51 | `—` | Fase 2 analítica de operativa: `build_dashboard_trade_analytics()`, score de exits observados, breakdown por `take_profit / reeval / stop_loss`, timeline corto y sección nueva en dashboard para seguir upside dejado vs downside evitado. Suite local `477/477`. |
| 2026-03-31 | Explícita | Sesión 52 | `—` | Trade console dashboard: nueva pestaña separada con `Resumen / Trades`, KPIs de operativa real y tabla por posición basada en `trade_lifecycle/postmortem`, pensada para seguimiento activo sin tocar trading. |
| 2026-04-01 | Explícita | Sesión 53 | `—` | Snapshot analítico live + refinamiento semántico local: acceso live reabierto vía dashboard, foto congelada de producción (`101` operaciones, `85` cerradas, `16` abiertas, `LOSS_TOTAL=60`, `sample observado=7/85`) y handoff limpio del bug de auth Railway. |
| 2026-04-01 | Explícita | Sesión 54 | `—` | Cierre del bug de Railway auth: wrapper endurecido (`HTTP_PROXY`/minúsculas/`npm_config_*`), nuevo helper `tools/railway_auth_repair.ps1` con `doctor/reset/launch-login/restore-links`, login browserless validado y re-enlace del proyecto restaurado desde backup; `whoami/status/logs` vuelven a funcionar. |
| 2026-04-01 | Explícita | Sesión 55 | `5b23d02` | Deploy validado del refinamiento semántico del `trade console`: push + redeploy manual en Railway y confirmación live de `LOSS_TOTAL`, `SELL negativos` y `Legacy/parcial` ya visibles en producción. |
| 2026-04-01 | Explícita | Sesión 56 | `—` | Auditoría manual de inconsistencias en `trade_lifecycle/trade console`: evidencia de trades recientes con desenlace contradictorio o entrada parcial (`Seoul 14C`, `Seoul 13C`, `Atlanta 70-71F`, `Atlanta 78-79F`), creación del handoff `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` y cambio de foco a saneamiento de trazabilidad, sin tocar trading ni deploy. |
| 2026-04-01 | Explícita | Sesión 57 | `—` | Saneamiento local de `trade_lifecycle/trade console`: clave estable por mercado+lados, coalescing de follow-ups (`SELL` + residuo `LOSS_TOTAL`, `RESOLVED_WIN` repetidos), label con `YES/NO`, cruce con cartera para `claim/redeem` y fallback visible desde `portfolio.dead/resolved_won`. Validación concreta sobre `Seoul 14C/13C`, `Atlanta 70-71F/78-79F/80-81F`, `Tokyo 18C`, `Buenos Aires 28C`, `Chicago 40-41F` y `Dallas 82-83F`. Suite local `483/483`. |
| 2026-04-02 | Explícita | Sesión 60 | `—` | Diagnóstico y fix del bloqueo de capital en live: posiciones `redeemable=True` dejaban exposición falsa y `round(size, 2)` provocaba SELL rechazadas por exceso de shares. `bot.py` pasa a excluir `redeemable` en `get_current_exposure()` y a truncar SELL hacia abajo en `manage_positions()` e intra-cycle. Validación dirigida + suite `483/483`; se actualizan contexto, historial y scoreboard y se empuja a `origin/main`. |
| 2026-04-02 | Explícita | Sesión 61 | `3c2b568` | Auditoría operativa del `Mission HUD` y salto de capa descriptiva a capa decisional por ciudad: `shadow tracking` para ciudades fuera de allowlist, reglas explícitas `shadow -> canary` y `active/canary -> shadow`, overlay automático persistente, dashboard con `canaries/shadows` actuales e historial de transiciones, y alertas Telegram cuando una ciudad cambia de estado. Suite local `496/496`, `commit + push` a `origin/main` y redeploy lanzado en Railway; queda pendiente validar el comportamiento live de la automatización y como siguiente tarea se fija el backfill conservador de `shadow` histórico. |
| 2026-04-02 | Explícita | Sesión 62 | `e4dce44` | Conversión de la capa de ciudades en una vista de ranking operacional clara: `readiness_score`, ranking principal, distancia a canary, tendencia y motivo principal por ciudad; degradadas diferenciadas explícitamente (`Dallas` como `shadow degradada`), copy/UX afinado y tests ampliados. `verify_before_deploy.py` cierra en `500/500`; se detecta además que faltaba el cierre documental, por lo que se actualizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` y se empuja el deploy. |
| 2026-04-02 | Explícita | Sesión 63 | `—` | Cierre mínimo de hardening de tooling/documentación con evidencia ya verificada en local: `OPERATIONS_PLAYBOOK.md` deja RTK y Engram como setup global del usuario, no del repo; RTK queda marcado como verificado para Codex con `rtk --version` + `rtk init -g --codex` + uso real (`rtk git status`, `rtk git diff`); Engram queda marcado como operativo tras `engram setup codex` y alta manual del MCP `engram` en la extensión de Codex para VS Code. Sin cambios en bot, trading, NOAA o deploy. |
| 2026-04-03 | Explícita | Sesión 69 | `—` | Reconciliación acotada de `postmortem.json` live para Chicago Apr1: la fila `2026-04-01` ya no estaba `open`, sino `closed/LOSS_TOTAL` con `micro_position_unsellable`, y `city_accuracy[Chicago]` recalcula a `4T / 1W / 25.0% / +$2.09`; el sesgo pendiente queda movido a 3 filas legacy de Chicago (`2026-03-26`, `2026-03-27`, `2026-03-28`) que siguen abiertas. |
| 2026-04-03 | Explícita | Sesión 70 | `—` | Auditoría completa del Control Center dashboard (v10.6.10): 6 bloques analizados (fidelidad de datos, utilidad operativa, UX/IA, motor de ciudades, alertas Telegram, valor estratégico). Hallazgos críticos: `shadow_tracking` posiblemente no persiste en Volume, WR Chicago sesgado por 3 filas legacy `open`, NOAA/Decision engine al final de capa 2 cuando es el limitante dominante, `readiness_score` opaco (propuesta de 3 gates). Entregables: `docs/control-center-audit.md`, `docs/control-center-roadmap.md` (QW1-7, M1-5, R1-3, I1-3), `docs/control-center-next-session.md` con prompt listo. Sin cambios de código. |
| 2026-04-03 | Explícita | Sesión 66 | `—` | Implementación local del auto-bloqueo real por ciudad sin tocar trading/NOAA/scheduler: `city_policy_state.json` añade `auto_blocked_cities` con `action/reason/metrics/from_mode/triggered_at`, `get_effective_city_mode()` prioriza ese estado sobre la allowlist activa, `sync_city_policy_state()` registra `active/canary -> blocked` con evidencia persistida, dashboard/decision engine leen la política y la suite pasa en `506/506`. Sin push/deploy todavía; siguiente paso validar en Railway. |
| 2026-04-02 | Explícita | Sesión 58 | `—` | Cierre operativo sin tocar el bot: se fija como siguiente prioridad la auditoría de la captura del `Mission HUD`, se formaliza la regla `1 sesión = 1 tarea` con contexto mínimo, se añade una sección de `token economics` para Codex + Claude Code y se crea `.codex/config.toml` del proyecto con `medium` por defecto y perfiles `low/deep/max`. Sin deploy ni cambios de trading/NOAA. |
| 2026-04-02 | Explícita | Sesión 59 | `—` | Cierre completo: `python verify_before_deploy.py` vuelve a pasar `483/483`, se versionan el saneamiento local de `trade_lifecycle/trade console`, el handoff y los guardrails de contexto/tokens, y se hace `commit + push` a `origin/main`. No se tocan reglas de trading ni NOAA; queda pendiente revalidación live del nuevo push. |

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

## Sesión 47 — capa `trade_lifecycle` para trazabilidad operativa completa (31 mar 2026)

**Disparador:** al revisar ventas como el take-profit de Atlanta que luego terminó en `100c`, quedó claro que `performance.json` y `postmortem.json` ya explicaban por qué se entró y por qué se intentó salir, pero no dejaban una historia completa por posición para analizar después cuánto upside se dejó encima de la mesa o qué ocurrió tras salir.

**Diagnóstico (Codex):**

1. **La observabilidad actual estaba fragmentada.** `performance.json` registra eventos; `postmortem.json` agrega estado y cierre; `audit.json` cubre NOAA. Pero faltaba una capa única orientada a análisis por trade, no por evento.

2. **El análisis futuro de trading necesitaba evidencia, no intuición.** Antes de pedir a Claude Code Opus que decida cambios de operativa, hacía falta poder responder con datos a preguntas como “¿este TP fue prematuro?”, “¿el mercado llegó a `0.98/1.00` después de vender?” o “¿qué drawdown se evitó realmente?”.

3. **Se podía instrumentar sin tocar trading.** La lógica de entrada/salida no necesitaba cambiar; bastaba con enganchar los puntos correctos del ciclo de vida y reconstruir el histórico desde las fuentes ya existentes.

**Cambios realizados:**
- `bot.py` añade `TRADE_LIFECYCLE_FILE = _data_path("trade_lifecycle.json")` y una nueva capa derivada con:
  - carga/guardado dedicados;
  - helper `_sync_trade_lifecycle_from_sources()` para reconstruir desde `performance.json` + `postmortem.json`;
  - campos por posición: `entry_context`, `latest_entry_context`, `buys`, `timeline`, `exit_attempts`, `position_snapshots`, `market_observations`, `close_context`, `post_exit_analysis` y `summary` global;
  - enriquecimiento de duplicados históricos para no perder `cycle_number`, `logic_cycle_number`, `trader_confirmed`, `decision_note`, `decision_source`, `trigger_price` o `current_value` cuando el backfill parte de `postmortem` y luego se completa con `performance`.
- La capa se actualiza automáticamente:
  - en cada `track_trade()` (`BUY`, `SELL_PENDING`, `SELL`, `SELL_FAILED`, `LOSS_TOTAL`, `RESOLVED_WIN`);
  - al arrancar, tras el backfill de `postmortem`;
  - en `manage_positions()` con snapshots previos a checks;
  - en el monitor intra-ciclo con snapshots entre ciclos;
  - durante el scan principal con observaciones de mercado para medir qué pasa tras el cierre.
- `record_trade_lifecycle_market_observations()` calcula también señales de análisis post-salida:
  - `market_seen_after_close`;
  - `max/min_price_after_close`;
  - `reached_98_after_close`;
  - `upside_left_cash_peak / pct`;
  - `drawdown_avoided_cash_peak / pct`.
- `verify_before_deploy.py` cierra en `467/467` con:
  - checks estructurales de la nueva capa;
  - test funcional de reconstrucción histórica desde `performance+postmortem`;
  - test de snapshots de posición viva;
  - test de observación post-exit con detección explícita de upside dejado hasta `100c`.

**Resultado:** queda lista una capa de trazabilidad completa, pensada para revisión rápida por Claude Code Sonnet y análisis estratégico posterior por Claude Code Opus, sin tocar ni una regla de trading. Limitación conocida al cierre: el backfill real de la cuenta no pudo materializarse localmente en esta sesión porque el CLI de Railway tenía el login OAuth caducado, pero el código ya deja el `trade_lifecycle.json` preparado para reconstruirse automáticamente desde el Volume en el próximo arranque desplegado.

---

## Sesión 48 — hardening fase 1 de `trade_lifecycle` (31 mar 2026)

**Disparador:** tras validar en Railway que `trade_lifecycle.json` ya existía y era útil para analizar exits, la inspección del raw live reveló ruido histórico real: `92` filas visibles, pero varias operaciones antiguas aparecían duplicadas por `id` y con `token_id` vacío, `total_amount = 0` y `total_shares = 0`.

**Diagnóstico (Codex):**

1. **La duplicación no venía de trading, sino del replay histórico.** Algunos cierres viejos de `performance.json` solo guardaban `city/side/precio/razón`, sin `token_id`, `question` ni `date`. Al reconstruir desde `postmortem + performance`, `_find_trade_lifecycle_record()` no conseguía emparejar esos eventos “pobres” con su record previo de `postmortem`.

2. **El síntoma era una pareja `postmortem-only` + `performance-only` con el mismo `id`.** En live esto afectaba a `12` casos y contaminaba el conteo de `tracked_positions/closed_positions`, además de mezclar ruido parcial en futuros rankings de eficiencia operativa.

3. **Se podía sanear sin tocar trading.** Bastaba con endurecer el matching de la capa derivada, coalescer duplicados por `id` y dejar explícito qué records son solo parciales para análisis.

**Cambios realizados:**
- `bot.py` añade `_trade_lifecycle_record_id()` y hace que `_find_trade_lifecycle_record()` pruebe primero el `id` reconstruido antes de caer a `token_id/question/city+side+date`.
- Se añade coalescing defensivo por `id` mediante `_coalesce_trade_lifecycle_records()` y merge controlado de contexto/listas para evitar que una misma posición salga dos veces en el payload final.
- Cada record recibe ahora un bloque `integrity` con flags como:
  - `partial_historical_record`
  - `analysis_ready`
  - `missing_token_id`
  - `missing_question`
  - `missing_entry_context`
  - `missing_buy_history`
  - `zero_amount`
  - `zero_shares`
- El payload global añade también `integrity` agregado para auditar el estado del dataset antes de usarlo en métricas o dashboard.
- `record_trade_lifecycle_position_snapshots()` y `record_trade_lifecycle_market_observations()` refrescan también la integridad global para no dejar el JSON desalineado tras cada update incremental.
- `verify_before_deploy.py` sube a `470/470` con:
  - check estructural del bloque `integrity`;
  - test funcional del caso real de “cierre huérfano” para asegurar que un `SELL` histórico sin `token/question/date` ya no duplica el record y queda marcado como parcial.

**Validación con datos reales:**
- Se descargan `performance.json` y `postmortem.json` live desde Railway y se reconstruye el lifecycle con el código nuevo.
- Resultado:
  - `92` filas visibles en el raw live anterior;
  - `80` records únicos tras reconstrucción endurecida;
  - `0` duplicados residuales;
  - `12` `partial_historical_records` explícitamente marcados;
  - `68` records `analysis_ready`.

**Resultado:** queda cerrada la fase 1 de saneamiento de `trade_lifecycle`: el dataset ya no duplica cierres huérfanos antiguos y además declara explícitamente qué parte del histórico es parcial. No se toca ninguna regla de trading. El siguiente paso natural es desplegar este hardening y construir encima la fase 2: capa analítica de operativa para dashboard y paquete congelado para Claude Code Opus.

---

## Sesión 49 — hotfix de coalescing para `trade_lifecycle` (31 mar 2026)

**Disparador:** al validar en Railway el despliegue de la fase 1, el contenedor arrancó correctamente pero empezó a loguear `Error sincronizando trade_lifecycle: unhashable type: 'list'` tanto en startup como durante el ciclo de las `16:00 UTC`. El problema aparecía justo cuando `track_trade()` registraba varios `LOSS_TOTAL` y el lifecycle intentaba resincronizarse.

**Diagnóstico (Codex):**

1. **El fallo no estaba en trading ni en datos NOAA.** `status`, `logs` y el dashboard live confirmaron que el servicio estaba arriba, que NOAA seguía poblando muestra real y que el error afectaba únicamente a la capa derivada `trade_lifecycle`.

2. **La pista clave era el mensaje Python exacto.** Se revisó el hot path de coalescing y apareció una construcción inválida en Python:
   - `_merge_trade_lifecycle_context()` usaba `if target.get(key) in {None, "", [], {}} ...`
   - `_merge_trade_lifecycle_record()` usaba `existing not in {None, "", [], {}}`
   Eso dispara `TypeError: unhashable type: 'list'` en cuanto la expresión se evalúa, porque `[]` y `{}` no pueden ser elementos de un set.

3. **La razón por la que no saltó antes:** el bug solo se manifiesta cuando la ruta de coalescing se ejecuta de verdad sobre records duplicados/ambiguos. En Railway, esa condición sí se daba tras la fase 1, porque el lifecycle live todavía arrastraba duplicados históricos y el ciclo de las `16:00` volvió a empujar eventos `LOSS_TOTAL`.

**Cambios realizados:**
- `bot.py` añade `_lifecycle_is_empty()` para encapsular de forma segura la noción de “vacío” (`None`, `""`, listas/dicts/tuplas/sets vacíos).
- `_merge_trade_lifecycle_context()` deja de usar sets inválidos con `[]/{}` y pasa a `if _lifecycle_is_empty(...)`.
- `_merge_trade_lifecycle_record()` cambia `_prefer()` para reutilizar el mismo helper seguro.
- `verify_before_deploy.py` añade:
  - check estructural de `_lifecycle_is_empty()`;
  - regresión funcional que coalesce dos records con el mismo `id` y `entry_context` no vacío para asegurar que:
    - no rompe;
    - fusiona `timestamp + price`;
    - une `trader_confirmed` en `["Alpha", "Beta"]`.
- Se normaliza `agent_events.jsonl` del repo a `utf-8`, porque la suite seguía detectando un seed local en `cp1252` que ensuciaba el runner con un warning ajeno al bug de lifecycle.

**Validación:**
- Se confirma el síntoma live en logs de Railway:
  - startup: `Error sincronizando trade_lifecycle al arrancar: unhashable type: 'list'`
  - ciclo `16:00 UTC`: múltiples `Error sincronizando trade_lifecycle: unhashable type: 'list'`
- El hotfix local queda validado con `verify_before_deploy.py` en `472/472`.
- NOAA sigue sano y no está afectado por este bug:
  - `observed_vs_forecast` live ya mostraba `2` casos reales en Chicago.

**Resultado:** el problema queda acotado y corregido localmente sin tocar reglas de trading. El siguiente paso correcto es desplegar este hotfix, revalidar Railway y confirmar que desaparecen los warnings de `trade_lifecycle` antes de seguir con la fase 2 analítica del dashboard.

---

## Sesión 50 — recap + Railway CLI hygiene (31 mar 2026)

**Disparador:** tras cerrar el hotfix de `trade_lifecycle`, el siguiente bloqueo real ya no era el bot sino la operativa del Railway CLI: la sesion acababa mezclando producto, auth OAuth y el proxy `127.0.0.1:9`, y hacia falta dejar un guardrail practico para no volver a perder tiempo en el mismo bucle.

**Diagnóstico (Codex + validación previa con Claude):**

1. **El problema de auth quedo suficientemente entendido.** No era un bug del bot ni del deploy. La secuencia mas plausible era:
   - token de acceso expirado;
   - intento de refresh desde un contexto sandboxed;
   - fallo al persistir `%USERPROFILE%\.railway\config.json` (`os error 5`);
   - refresh token local stale;
   - siguiente intento => `invalid_grant`.

2. **El proxy seguia existiendo, pero ya no era el bloqueo principal.** En esta shell seguian entrando:
   - `HTTP_PROXY=http://127.0.0.1:9`
   - `HTTPS_PROXY=http://127.0.0.1:9`
   - `ALL_PROXY=http://127.0.0.1:9`
   - `GIT_HTTP_PROXY=http://127.0.0.1:9`
   - `GIT_HTTPS_PROXY=http://127.0.0.1:9`
   Ya estaba descartado que vinieran de `PowerShell profile`, `HKCU/HKLM`, `winhttp` o settings normales de VS Code. Se decide no seguir persiguiendo el origen durante esta incidencia porque habia una solucion practica mejor.

3. **El hotfix de lifecycle ya estaba bueno en Railway.** Una vez empujado `47c68ee`, Railway redeployo y el arranque nuevo confirmo:
   - `trade_lifecycle listo al arrancar: 87 registros`
   - sin repetir `unhashable type: 'list'`
   - validacion live posterior:
     - `tracked_positions=87`
     - `open_positions=18`
     - `closed_positions=69`
     - `partial_historical_records=12`
     - `analysis_ready_records=75`
     - `duplicate_id_collisions_resolved=12`
     - `duplicate_ids_live=0`

**Cambios realizados:**
- Nuevo wrapper repo-local `tools/railway_safe.ps1`.
  - limpia `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` solo para el proceso actual;
  - ejecuta `railway.cmd`;
  - restaura el entorno al salir;
  - deja mensaje explicito cuando se usa `login`.
- `OPERATIONS_PLAYBOOK.md` gana la seccion `Higiene Railway CLI` con la regla operativa nueva:
  - `railway login` solo en shell interactiva del usuario;
  - uso diario de Railway con el wrapper;
  - desde Codex, Railway fuera del sandbox cuando la CLI pueda refrescar auth.
- `CONTEXTO.md` se actualiza para reflejar que:
  - el hotfix de lifecycle ya esta validado live;
  - la infraestructura vuelve a estar bajo control practico;
  - el siguiente paso correcto regresa a analytics/dashboard.

**Resultado:** la sesion deja un guardrail operativo claro para Railway CLI sin volver a abrir una investigacion larga del proxy. El sistema queda otra vez orientado al roadmap principal: capa analitica de operativa en dashboard y snapshot para Claude Code Opus.

---

## Sesión 51 — fase 2 analítica de operativa (31 mar 2026)

**Disparador:** con `trade_lifecycle` ya saneado y el wrapper de Railway en su sitio, el siguiente paso lógico era dejar de mirar los exits solo como PnL agregado y pasar a medir con evidencia post-salida qué estaba capturando realmente el bot.

**Objetivo:** añadir una capa analítica derivada, visible en dashboard, que permita seguir activamente:
- cuántos cierres tienen muestra post-exit útil;
- cuánto upside se dejó tras salir;
- cuánto downside se evitó;
- qué buckets (`take_profit`, `reeval`, `stop_loss`) merecen revisión antes de tocar reglas.

**Cambios realizados:**
- Se añade `build_dashboard_trade_analytics()` en `bot.py`.
  - filtra solo `status=closed` con `market_seen_after_close=True`, `close_price` usable, `close_shares > 0` y `integrity.analysis_ready`;
  - calcula `score_pct`, `harvest_efficiency_pct`, `upside_left_total_cash`, `drawdown_avoided_total_cash` y `maturity_pct`;
  - genera `breakdown_rows` por `take_profit / reeval / stop_loss`;
  - construye `recent_rows`, `top_upside_rows`, `top_protection_rows` y `timeline_points`.
- `build_dashboard_snapshot()` pasa a cargar `trade_lifecycle` y a exponer `trade_analytics` en `/api/dashboard.json`.
- El dashboard web gana una nueva sección visible `Operativa observada` con:
  - medidor principal de eficiencia;
  - badges de confianza / muestra;
  - timeline corto de exits observados;
  - cola de revisión con `top upside dejado` y `casos donde salir ayudó`;
  - tabla de últimos cierres con evidencia post-salida.
- La capa evita contaminar el análisis con histórico parcial:
  - los `close_only` o records sin precio/cantidad de salida usable quedan fuera;
  - no se toca ninguna regla de `manage_positions`, sizing, scheduler ni exits.

**Tests:**
- Nuevo bloque funcional para `build_dashboard_trade_analytics()`:
  - cuenta solo cierres observados utilizables;
  - calcula score y rankings de upside/protección;
  - genera breakdown y timeline.
- `build_dashboard_snapshot()` queda cubierto para asegurar que incluye `trade_analytics`.
- `verify_before_deploy.py` sube a `477/477`.

**Resultado:** queda implementada la fase 2 de observabilidad operativa. El bot sigue igual en trading, pero el dashboard ya tiene una base estructurada para seguir si las salidas están capturando valor o dejando dinero encima de la mesa. El siguiente paso correcto es validarlo en Railway y usar esa evidencia para preparar el análisis profundo con Claude Code Opus.

---

## Sesión 52 — trade console dashboard (31 mar 2026)

**Disparador:** tras ver la primera capa `Operativa observada` en pantalla, quedó claro que respondía bien a la pregunta de eficiencia observada de exits, pero seguía siendo poco práctica para revisar la operativa trade por trade.

**Objetivo:** ampliar el dashboard con una vista más accionable que permita responder:
- cuántas operaciones totales hay;
- cuántos TP/SL se ejecutaron;
- cuántas operaciones acabaron ganadas/perdidas;
- cuánto cash se ganó, perdió o se dejó de ganar;
- y, para cada trade, por qué entró el bot, por qué salió y qué pasó después.

**Cambios realizados:**
- `build_dashboard_trade_analytics()` se amplía en `bot.py` con una capa tipo `trade console`.
  - añade `total_cards` con `Operaciones totales`, `TP`, `SL`, `Ganadas`, `Perdidas`, `PnL neto`, `Dejado de ganar` y `Protegido`;
  - añade `trade_rows` con detalle por posición:
    - mercado;
    - condición de entrada;
    - condición de salida;
    - resultado;
    - valor del trade;
    - centavos por share;
    - upside dejado;
    - y estado de observación/integridad.
- `templates/dashboard.html` gana una nueva pestaña separada `Trade console / Operaciones del bot` con dos vistas:
  - `Resumen`;
  - `Trades`.
- `static/dashboard.js` se generaliza para soportar múltiples shells de tabs (`data-tab-shell`) sin romper el Mission HUD original.
- La fuente de verdad sigue siendo `trade_lifecycle` + `postmortem`; el CSV local se deja solo como referencia manual, no como dependencia del dashboard live.

**Tests:**
- Se ajusta la validación funcional de `trade_analytics` para comprobar totales y detalle por trade sin depender de un orden artificial.
- `verify_before_deploy.py` sube a `478/478`.

**Resultado:** el dashboard ya no se queda en una lectura abstracta de eficiencia. Ahora también ofrece una consola de operaciones pensada para seguimiento activo del bot y para preparar, más adelante, una revisión profunda con Claude Code Opus usando una vista más legible y más cercana a cómo se piensa la operativa real.

---

## Sesión 53 — snapshot analítico live + refinamiento semántico local (1 abr 2026)

**Disparador:** el siguiente paso pendiente ya no era añadir más panel, sino usar producción como fuente de verdad para revisar casos reales `take_profit / reeval / stop_loss` y congelar una foto analítica útil antes de seguir tocando semántica o reglas.

**Objetivo:** reabrir acceso live, revisar la consola de trades contra datos reales de Railway y dejar un snapshot congelado que sirva tanto para la próxima iteración local como para un handoff limpio a Claude Code Opus.

**Acceso live recuperado:**
- El Railway CLI seguía bloqueado por auth expirada (`invalid_grant`) y el wrapper confirmó que `railway login` no puede completarse desde una shell no interactiva de Codex.
- Se encontró una vía alternativa suficiente para análisis: el dashboard live ya estaba protegido con auth básica y las credenciales existían en `.env`.
- Con eso se pudo acceder a:
  - `https://polymarket-bot-production-4deb.up.railway.app/healthz`
  - `https://polymarket-bot-production-4deb.up.railway.app/api/dashboard.json`

**Foto live congelada (`2026-04-01 20:13 UTC`):**
- versión: `v10.6.10`
- `portfolio_total = $31.91`
- `signals ok`
- sin `pending_exit` atascadas
- `101` operaciones
- `85` cerradas
- `16` abiertas
- `TP = 5`
- `SL = 13`
- `LOSS_TOTAL = 60`
- `PnL neto = $-37.53`
- muestra observada post-salida: `7/85`
- focus live:
  - `Sano con limitaciones`
  - `La operativa parece estable; el cuello de botella ahora es learning / measurement`
  - acción: `No tocar trading: priorizar crecimiento de muestra NOAA`
  - NOAA: `2/10` casos, `0/4` ciudades interpretables

**Casos revisados en live:**
- `Re-eval` observado:
  - `Will the highest temperature in New York City be 74°F or higher on March 31?`
  - `PnL = $+0.06`
  - `trade_value = $1.32`
  - `2 obs`
  - salida por `edge recalculado < -3%`
- `Stop-loss` observados:
  - Dallas `82-83°F Apr 1`:
    - `PnL = $-0.56`
    - `trade_value = $0.41`
    - `3 obs`
  - Atlanta `80-81°F Apr 1`:
    - `PnL = $-1.30`
    - `trade_value = $0.77`
    - sin observación post-salida todavía
    - conserva `trigger 10.5c | limite 8.0c`
- `Take-profit` identificados en live:
  - `Chicago YES` como `Mejor operacion` (`SELL · take_profit`, `+$3.96`)
  - `Atlanta Mar30 YES` como `Mejor retorno %` (`v10.6.10 · serie v10.6 · SELL · take_profit`, `+302.5%`)
  - importante: en este snapshot no aparece aún muestra observada post-salida de TP (`coverage 0/5`)

**Hallazgo clave del snapshot:**

1. **La consola live seguía mezclando semánticas.** En la tabla visible del snapshot muchos cierres seguían cayendo en bucket `Otro`, aunque el breakdown validado ya reconocía `60 LOSS_TOTAL`. No era un problema teórico: seguía costando leer de un vistazo qué era `SELL negativo`, qué era `LOSS_TOTAL` y qué era ruido legacy/parcial.

2. **La evidencia observada de exits sigue siendo pequeña pero ya útil.** `Re-eval` aparece con señal de `revisar captura`; `Stop-loss` sale `mixto`; y `Take-profit` aún no tiene muestra observada útil en este snapshot aunque sí muestra balance agregado claramente positivo.

3. **El bloqueo principal no es trading, sino measurement.** El propio `focus` live sigue recomendando no tocar reglas y priorizar NOAA, porque `0/4` ciudades activas siguen sin llegar a zona interpretable.

**Cambios realizados en local durante la misma sesión:**
- `build_dashboard_trade_analytics()` queda endurecido para separar:
  - motivo de salida;
  - resultado económico;
  - calidad/integridad del registro.
- El `trade console` local pasa a distinguir explícitamente:
  - `SELL negativos`
  - `LOSS_TOTAL`
  - `Legacy/parcial`
- `templates/dashboard.html` se ajusta para explicar esa nueva lectura.
- `verify_before_deploy.py` gana cobertura funcional de:
  - `LOSS_TOTAL`
  - `close-only`
  - `partial_historical`
- La suite local sube a `479/479`.

**Artefactos congelados:**
- `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json`
- `SNAPSHOT_ANALITICO_LIVE_2026-04-01.md`

**Resultado:** queda reabierto el acceso live suficiente para análisis, congelada una foto real de producción y cerrada en local la semántica que faltaba para que la próxima validación live no vuelva a colapsar `SL / LOSS_TOTAL / legacy` en una lectura ambigua. El siguiente paso correcto ya no es investigar, sino desplegar esta mejora semántica y revalidar la consola sobre el mismo flujo live.

---

## Sesión 54 — cierre del bug de Railway auth (1 abr 2026)

**Disparador:** el usuario pidió una sesión limpia dedicada solo al bug de Railway auth que obligaba a reloguearse continuamente, sin tocar trading ni dashboard.

**Diagnóstico confirmado:**

1. **Había dos capas distintas del fallo.**
   - Sin wrapper, `railway.cmd` seguía intentando salir por `127.0.0.1:9` y fallaba al conectar.
   - Con wrapper, la red quedaba bien, pero `whoami/status` devolvían `Unauthorized`, así que el problema real restante era de credenciales locales degradadas.

2. **Los proxies no eran persistentes de Windows.**
   - `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` estaban presentes en la shell actual.
   - No aparecían ni en variables `User/Machine` ni en perfiles normales de PowerShell.
   - Conclusión operativa: el wrapper seguía siendo la defensa correcta para uso diario.

3. **El `config.json` de Railway estaba enlazado pero roto a nivel de auth.**
   - Existían `accessToken`, `refreshToken` y el link del proyecto.
   - Aun así, en entorno limpio la CLI respondía `Unauthorized`.
   - Esto confirmó que el siguiente paso no era tocar el bot, sino sanear la auth local.

**Cambios implementados:**

- `tools/railway_safe.ps1` se endurece para limpiar también proxies en minúsculas, `NO_PROXY` y variantes `npm_config_*`, no solo `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*`.
- Se añade `tools/railway_auth_repair.ps1` con cuatro acciones operativas:
  - `doctor`: diagnostica proxies, estado del `config.json` y auth real vía `whoami`.
  - `reset`: hace backup del config y limpia solo los tokens stale.
  - `launch-login -Browserless`: abre una shell limpia para login interactivo del usuario.
  - `restore-links`: restaura el bloque `projects` desde el último backup sin tocar los tokens nuevos.
- `OPERATIONS_PLAYBOOK.md`, `CONTEXTO.md` y esta bitácora quedan actualizados con el flujo correcto.

**Incidencia real descubierta durante la reparación:**

- El login browserless sí autenticó correctamente al usuario (`pablogomez.eu@gmail.com`), pero Railway regeneró `config.json` con `projects = {}` y `status` pasó a responder `No linked project found`.
- Para cerrar ese hueco se añadió `restore-links`, que copia únicamente el bloque `projects` desde `config.backup.*.json`.
- También se corrigió la escritura del helper a `UTF-8` sin BOM para no volver a provocar `Unable to parse config file, regenerating` en futuros `reset`.

**Validación final del 1 de abril de 2026:**

- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`
  - `Logged in as pablogomez.eu@gmail.com`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status`
  - `Project: enchanting-respect`
  - `Environment: production`
  - `Service: polymarket-bot`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 logs -s polymarket-bot -n 20`
  - vuelve a responder correctamente

**Límite de alcance respetado:**

- no se tocó trading;
- no se tocó dashboard;
- la lectura de logs live fue solo para validar que la CLI había quedado operativa otra vez.

---

## Sesión 55 — deploy validado de semántica trade console (1 abr 2026)

**Disparador:** con Railway auth ya reparada y el refinamiento semántico listo en local, faltaba cerrar el paso obvio: empujar el commit, redeployar y comprobar si la consola live seguía colapsando cierres en `Otro` o ya leía bien `SL / LOSS_TOTAL / legacy-parcial`.

**Ejecución y validación:**

- Se empuja `5b23d02` (`ops: refine trade console semantics and harden railway auth workflow`) a `origin/main`.
- Se fuerza redeploy manual con `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 redeploy -s polymarket-bot -y`.
- Railway crea el deployment `00366049-f0a4-4267-b782-450ef49feb75`, que progresa hasta `SUCCESS`.
- La comprobación live autenticada de `dashboard.json` a las `21:00 UTC` confirma las tarjetas:
  - `Operaciones totales`, `TP`, `SL`, `LOSS_TOTAL`, `Ganadas`, `SELL negativos`, `Legacy/parcial`, `PnL neto`, `Dejado de ganar`, `Protegido`
- La nota live ya explica explícitamente que la consola separa `SL`, `LOSS_TOTAL` y `legacy/parcial`.
- Las primeras filas reales dejan de caer en `Otro` y pasan a verse como:
  - `Stop-loss | Perdida SELL | Completa`
  - `LOSS_TOTAL | Perdida total | Completa`

**Resultado:** queda cerrada la brecha entre el snapshot local y el panel productivo. El dashboard live ya muestra la nueva taxonomía sin tocar reglas de trading ni bump de versión (`v10.6.10`), y el siguiente trabajo vuelve a ser análisis operativo sobre casos reales, no auth ni deploy.

---

## Sesión 56 — auditoría de inconsistencias en `trade_lifecycle` / trade console (1 abr 2026)

**Disparador:** tras revisar los últimos trades reales en Polymarket, quedó claro que la pregunta importante ya no era solo "si la consola separa bien `SL / LOSS_TOTAL / legacy`", sino si realmente conserva una historia coherente por posicion reciente: por qué entro, por qué salió, qué ocurrió tras salir y si la lectura visible coincide con la cartera real.

**Hallazgos confirmados en la auditoría manual:**

1. **`Seoul 14C Apr 1` aparece con desenlace contradictorio.**
   - En el snapshot congelado de `trade_rows` aparece una fila como `Perdida` con salida `Micro posicion incanjeable / perdida total` y otra fila del mismo mercado como `Ganada` con salida `market_resolved_yes`.
   - Eso rompe la regla básica de "una posición, una historia".

2. **`Seoul 13C Apr 1` sale ganada pero con entrada degradada a parcial.**
   - La fila visible marca `Ganada` y `trade_value = $3.04`.
   - Sin embargo, el `entry_condition` dice `Historico parcial: faltan datos claros de entrada.`
   - Para un caso tan reciente eso apunta a problema de reconciliación, no a mera limitación legacy.

3. **`Atlanta 70-71F Mar 30` sigue duplicada en la lectura humana.**
   - Hay una fila "completa" con la entrada real y `pnl_cash = -1.33`.
   - Además sobreviven filas heredadas/parciales del mismo mercado con `trade_value = $0.00`.
   - El coalescing mejoró, pero todavía no deja una única traza limpia para todos los casos recientes.

4. **`Atlanta 78-79F Apr 1` existe en `portfolio.dead` pero no quedó visible en la extracción revisada de `trade_rows`.**
   - En cartera muerta aparece con `initialValue = 2.1238`, `currentValue = 0.010619`, `cashPnl = -2.113181`.
   - Eso obliga a revisar si el problema está en generación de filas, orden, filtro o semántica del cierre.

5. **La etiqueta visible aún puede ocultar el lado `YES/NO`.**
   - `_trade_lifecycle_label()` prioriza `question`; si existe, no muestra explícitamente `side`.
   - En mercados de temperatura casi idénticos eso dificulta detectar rápido inconsistencias humanas aunque el record interno sí tenga `side`.

6. **El `redeem/claim` manual no se registra como evento propio.**
   - La capa sí maneja `BUY`, `SELL_PENDING`, `SELL`, `SELL_FAILED`, `LOSS_TOTAL` y `RESOLVED_WIN`.
   - Pero el cobro manual posterior no queda registrado como acción diferenciada; solo se sabe que el mercado resolvió y quedó pendiente de canjear/cobrar.

**Qué se validó también como positivo:**

- los BUY recientes sí guardan contexto rico (`price`, `shares`, `amount`, `edge_pct`, `our_prob`, `mkt_price`, `forecast_max`, traders y ciclo);
- los `SELL_PENDING` guardan motivo, trigger, límite, `decision_note`, `decision_source`, `PnL` y `order_id`;
- existen `position_snapshots`, `market_observations` y `post_exit_analysis`.

**Acciones de cierre de la sesión:**

- se deja creado `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` con:
  - lista de evidencias verificadas;
  - hipótesis de trabajo;
  - y prompt listo para arrancar la siguiente sesión solo con esta tarea;
- se actualizan `CONTEXTO.md` y esta bitácora para mover explícitamente el foco operativo desde auth/deploy hacia saneamiento de trazabilidad.

**Límite de alcance respetado:**

- no se tocó trading;
- no se tocó NOAA;
- no se desplegó nada;
- no se cambió lógica del bot en esta sesión;
- se cerró únicamente la auditoría y el handoff.

---

## Sesión 57 — saneamiento local de `trade_lifecycle` / trade console (1 abr 2026)

**Disparador:** el handoff de la sesión 56 ya había aislado el problema real: no faltaban datos de entrada/salida, faltaba reconciliarlos en una sola historia humana por posición. El objetivo de esta sesión fue arreglar eso sin tocar reglas de trading ni NOAA.

**Cambios aplicados:**

- `trade_lifecycle` gana una clave estable por mercado+lados (`position_key`) y un segundo coalescing por identidad de posición para fusionar records que antes quedaban separados solo porque cambiaba el timestamp del `id`.
- `_trade_lifecycle_label()` deja de ocultar el lado cuando existe `question`; ahora la etiqueta visible puede diferenciar `YES/NO`.
- `build_dashboard_trade_analytics()` vuelve a coalescer al leer, cruza cada record con `portfolio.active / resolved_won / dead` y añade dos capacidades nuevas:
  - explicar qué pasó después (`cartera muerta`, residuo micro, posición aún abierta, etc.);
  - y mostrar si hay `claim/redeem` pendiente sin inventar un evento que no existe en el lifecycle.
- La trade console crea fallback visible para posiciones recientes que hoy sobreviven solo en cartera y no habían quedado en `trade_rows` (`portfolio.dead/resolved_won`).
- `verify_before_deploy.py` añade regresiones para:
  - coalescer `SELL` + follow-up `LOSS_TOTAL` en una sola posición;
  - exigir label con lado explícito;
  - validar `claim pendiente`;
  - y asegurar fallback desde cartera para trades recientes sin lifecycle visible.

**Validación concreta sobre los 9 casos auditados:**

1. `Seoul 14C Apr 1`
   - El snapshot congelado mostraba dos filas contradictorias con el mismo label: una pérdida `LOSS_TOTAL` y otra ganada por resolución.
   - La evidencia de cartera (`portfolio.dead`) confirma que el lado `No` quedó a `0c`, `avg=0.85`, `cashPnl=-1.0530`, `redeemable=true`.
   - Con el label por lado y el cruce por mercado, la lectura correcta pasa a ser: dos posiciones distintas del mismo mercado; `NO` perdió y `YES` resolvió a favor.

2. `Seoul 13C Apr 1`
   - El snapshot mostraba ganancia correcta (`$+0.61`) pero entrada degradada a parcial.
   - `portfolio.resolved_won` conserva la entrada real del lado `No`: `avg=0.80`, `initialValue=2.43144`, `currentValue=3.0393`, `redeemable=true`.
   - La consola ya puede reconstruir la entrada desde cartera y marcar `claim pendiente` en vez de esconderse detrás de `Historico parcial`.

3. `Atlanta 70-71F Mar 30`
   - El snapshot tenía una fila completa y dos duplicados parciales del mismo `LOSS_TOTAL`.
   - `portfolio.dead` confirma el residuo final: `avg=0.14`, `initialValue=1.3309534`, `currentValue=0`, `redeemable=true`.
   - El coalescing nuevo colapsa esos follow-ups en una sola historia coherente.

4. `Atlanta 78-79F Apr 1`
   - Antes no aparecía en `trade_rows` aunque sí existía en `portfolio.dead`.
   - La cartera conserva evidencia suficiente para mostrarla: lado `Yes`, `avg=0.10`, `initialValue=2.1238`, `currentValue=0.010619`, `cashPnl=-2.113181`, `redeemable=false`.
   - La consola ahora la puede enseñar vía fallback desde cartera, sin volver a dejarla invisible.

5. `Atlanta 80-81F Apr 1`
   - El snapshot ya mostraba el `SELL` por `stop_loss` (`$-1.30`) y la cartera muerta conservaba un residuo ínfimo (`currentValue=0.000005`, `realizedPnl=-1.480007`).
   - La nueva lectura une ambas capas: salida principal por SL y después residuo micro en cartera muerta.

6. `Tokyo 18C Apr 1`
   - El snapshot mostraba resolución ganada duplicada.
   - `portfolio.resolved_won` conserva el lado `No` con `avg=0.61`, `initialValue=2.4524318`, `currentValue=4.02038`, `cashPnl=+1.5679`, `redeemable=true`.
   - La consola pasa a leerlo como una sola resolución con `claim pendiente`, no como dos cierres idénticos.

7. `Buenos Aires 28C Apr 1`
   - El snapshot ya tenía una historia bastante limpia.
   - La cartera la completa: lado `No`, `avg=0.65`, `initialValue=1.07289`, `currentValue=1.6506`, `cashPnl=+0.57771`, `redeemable=true`.
   - La mejora visible aquí es sobre todo de presentación: resolución clara + estado de claim.

8. `Chicago 40-41F Apr 1`
   - Sigue abierta; el snapshot la mostraba como `Abierta` y `portfolio.active` confirma `avg=0.186`, `cur=0.8505`, `currentValue=8.0691`, `cashPnl=+6.3044`.
   - La trade console mantiene una única historia de posición abierta, sin forzar cierre/resolución artificial.

9. `Dallas 82-83F Apr 1`
   - El snapshot mostraba dos historias separadas para la misma posición: `SELL` por SL y luego `LOSS_TOTAL` micro.
   - La cartera muerta confirma el residuo final (`avg=0.12`, `currentValue=0.000026`, `realizedPnl=-0.6108`, `redeemable=false`).
   - El nuevo coalescing lo convierte en una sola narrativa: SL principal y, después, residuo micro muerto.

**Validación de suite:**

- `python verify_before_deploy.py`
- Resultado final: `483/483`

**Límite de alcance respetado:**

- no se tocaron reglas de trading;
- no se tocó NOAA;
- no se desplegó nada;
- el trabajo fue solo de trazabilidad, reconciliación, presentación y documentación.

---

## Sesión 58 — cierre limpio de contexto + prioridad siguiente + token economics (2 abr 2026)

**Disparador:** tras cerrar el saneamiento de `trade_lifecycle`, la necesidad ya no era tocar más código del bot, sino dejar la siguiente sesión bien acotada y evitar volver a abrir ventanas de contexto demasiado grandes o costosas.

**Decisión principal:** no se identifica una tarea separada más prioritaria que la auditoría de la captura del `Mission HUD` compartida el 2 de abril de 2026. Por tanto, el siguiente paso lógico queda fijado así:

1. dedicar una sesión completa solo a verificar la captura de la capa 1;
2. contrastar screenshot, snapshot live y builders locales;
3. buscar evidencia de errores de dato, agregación o semántica antes de rediseñar nada.

**Cambios aplicados en esta sesión:**

- `CONTEXTO.md` se actualiza para dejar explícita la prioridad siguiente:
  - auditar la captura del `Mission HUD` como sesión 58 recomendada;
  - y reservar la auditoría de `token economics` para una sesión posterior separada.
- `OPERATIONS_PLAYBOOK.md` gana una sección nueva de disciplina `1 sesión = 1 tarea` y contexto mínimo:
  - arrancar cada sesión con una fuente primaria de verdad;
  - limitar la lectura inicial a `1-3` artefactos relevantes;
  - no mezclar rediseño con auditoría de datos.
- `OPERATIONS_PLAYBOOK.md` gana también una sección específica de `token economics` para Codex + Claude Code.
- Se crea `.codex/config.toml` a nivel de proyecto:
  - `model_reasoning_effort = "medium"` por defecto;
  - perfiles `low`, `deep` y `max` para subir esfuerzo solo cuando la tarea lo justifique.

**Criterio operativo resultante:**

- Codex deja de arrancar este repo en `xhigh` por inercia.
- No se asume que Codex pueda decidir un `reasoning effort` completamente `auto` desde config; la estrategia elegida es `medium` por defecto + escalado selectivo por perfil/override.
- Claude Code queda guiado por protocolo, no por más contexto:
  - medir con `/cost`;
  - compactar con `/compact`;
  - limpiar con `/clear`;
  - cambiar modelo con `/model` solo cuando el retorno esperado compense.

**Validación ejecutada:**

- revisión local de la configuración activa de Codex en `C:\Users\USUARIO\.codex\config.toml`, donde el default previo seguía en `xhigh`;
- confirmación en documentación oficial de Codex de que `model_reasoning_effort` acepta valores fijos y puede definirse en config por proyecto;
- confirmación en documentación oficial de Claude Code de que existen `/cost`, `/compact`, `/clear` y `/model` como herramientas nativas para controlar gasto y contexto.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron reglas de trading;
- no se tocó NOAA;
- no se desplegó nada;
- no se ejecutó la suite porque la sesión fue solo de proceso, documentación y configuración local de herramienta.

---

## Sesión 59 — cierre completo con verify + commit + push (2 abr 2026)

**Disparador:** tras dejar lista la parte funcional en la sesión 57 y la parte de proceso/configuración en la 58, faltaba todavía un cierre operativo real: validar la suite otra vez, versionar todo y empujarlo a `origin/main`.

**Verificación ejecutada:**

- `python verify_before_deploy.py`
- resultado final: `483/483`

**Qué se versiona en este cierre:**

- saneamiento local de `trade_lifecycle` y trade console de la sesión 57:
  - clave estable por mercado+lados;
  - coalescing de follow-ups;
  - labels con `YES/NO`;
  - cruce con cartera para `claim/redeem`;
  - fallback para posiciones visibles solo en cartera.
- guardrails de proceso y token economics de la sesión 58:
  - regla `1 sesión = 1 tarea`;
  - contexto mínimo;
  - sección de `token economics` en playbook;
  - `.codex/config.toml` con `medium` por defecto y perfiles `low/deep/max`.
- documentación de soporte:
  - actualización de `CONTEXTO.md`;
  - actualización de `HISTORIAL_SESIONES.md`;
  - actualización de `agent_events.jsonl`;
  - versionado del handoff `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md`.

**Resultado operativo:**

- se hace `commit + push` a `origin/main`;
- no se toca lógica de trading;
- no se toca NOAA;
- el último deploy verificado live sigue siendo el previo (`5b23d02`);
- este nuevo push queda pendiente de revalidación explícita en Railway en la próxima sesión.

**Siguiente paso permanece igual:**

- auditar la captura del `Mission HUD` como única tarea de la próxima sesión, usando screenshot + snapshot live + builders locales como fuentes primarias de verdad.

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

---

## Sesión 60 — fix de exposición redeemable + SELL seguro (2 abr 2026)

**Disparador:** en live apareció un ciclo bloqueado con `Exposición actual: $9.21 | Presupuesto libre: $0.79` y sin entradas nuevas, pese a que la wallet mostraba una posición casi a `100c` y otra ya `Ganado / Canjear`. Además, el intento de take-profit sobre Chicago falló con `not enough balance / allowance`.

**Hallazgos confirmados:**

- había dos bugs independientes combinándose:
  - `get_current_exposure()` ya excluía `curPrice >= 0.98`, pero no excluía posiciones `redeemable=True`, aunque en práctica ya son cash garantizado pendiente de claim/redeem;
  - el sizing de SELL usaba `round(size, 2)`, que puede redondear al alza y pedir más shares de las realmente disponibles (`9.48748 -> 9.49`), provocando `400` de Polymarket.
- el resultado operativo del caso reproducido era coherente con el síntoma:
  - antes del fix, una posición `redeemable=True @ 0.97` seguía contando ~$8.70 de exposición;
  - tras excluirla, el escenario de prueba pasaba de `budget_left=$0.00` a `budget_left=$6.79`;
  - el truncado con `floor` evitaba errores tanto en tamaños tipo `9.48748` como `0.999`.

**Cambios implementados en `bot.py`:**

- `get_current_exposure()` ahora hace `continue` si `p.get("redeemable")` es truthy;
- `manage_positions()` cambia `round(size, 2)` por `math.floor(size * 100) / 100`;
- `intra_cycle_sl_check()` aplica el mismo truncado seguro para mantener consistencia.

**Validación ejecutada:**

- `python verify_before_deploy.py`
- resultado final: `483/483`
- mini-validación dirigida adicional:
  - posición `redeemable=True, curPrice=0.97` deja de contar exposición;
  - `redeemable=False, curPrice=0.99` sigue excluyéndose por precio como antes;
  - un residuo de `0.01` shares queda por debajo del umbral material de exposición;
  - `size=9.48748` produce `9.48` con `floor`, evitando el rechazo que producía `9.49`.

**Cierre operativo de la sesión:**

- se actualizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`;
- el fix queda preparado para `commit + push`;
- el siguiente paso correcto ya no es más investigación local, sino revalidar en Railway el próximo ciclo real después del redeem/venta manual ya ejecutados por el usuario.

---

## Sesión 61 — shadow/canary automático + dashboard decisional por ciudad (2 abr 2026)

**Disparador:** la auditoría del `Mission HUD` confirmó que la lectura actual era coherente, pero también dejó visible el atasco real: el dashboard explicaba el estado de `NOAA / allowlist / accuracy`, aunque todavía no servía para decidir qué ciudades mantener, cuáles observar y cómo aprender de ciudades fuera de allowlist sin abrir trades reales.

**Hallazgos confirmados en la revisión del HUD:**

- `Allowlist vs NOAA 0/4` significaba `0` ciudades activas con muestra NOAA interpretable (`>= 3` casos), no ausencia total de NOAA;
- `NOAA sample growth 2/10` estaba calculado correctamente como muestra global acumulada;
- la allowlist activa (`Chicago`, `Atlanta`, `Dallas`, `Buenos Aires`) seguía siendo manual y fija;
- el sistema estaba sano a nivel operativo, pero bloqueado a nivel aprendizaje;
- fuera de allowlist faltaba una capa intermedia entre `no comprar` y `arriesgar capital real`.

**Cambios implementados:**

- nueva capa de tracking `shadow` para ciudades fuera de `ACTIVE_TRADING_CITIES`:
  - el scan ya no descarta esas oportunidades silenciosamente;
  - las registra en `shadow_city_tracking.json`;
  - el resumen de ciclo incorpora el contador `shadow`;
  - la evidencia se acumula por ciudad sin abrir posiciones reales.
- nuevo `decision engine` por ciudad en dashboard:
  - `Mantener`
  - `Candidata a canary`
  - `Seguir observando`
  - `Revisar salida`
  - `Bloqueada`
- reglas explícitas de política:
  - `shadow -> canary`: al menos `2` edges shadow, `2` ciclos shadow, mejor edge `>= 7.0%` y soporte `>= 2`;
  - `active/canary -> shadow`: al menos `3` trades, `win rate <= 25%` y `PnL <= $0.00`.
- overlay automático persistente:
  - `city_policy_state.json` guarda `auto_canary_cities`, `auto_shadow_cities` e historial reciente;
  - `get_effective_city_mode()` resuelve `active / canary / shadow / blocked`;
  - las ciudades `canary` ya pueden operar con sizing reducido (`CANARY_POSITION_SCALE`, default `50%`);
  - las ciudades `shadow` siguen observándose, pero sin nuevas compras.
- visibilidad y alertas:
  - el dashboard añade `Canaries automáticos actuales`, `Shadows automáticos actuales` e `Historial automático reciente`;
  - Telegram avisa cuando una ciudad pasa de `shadow -> canary` o de `active/canary -> shadow`.

**Validación local:**

- `python verify_before_deploy.py`
- resultado final: `496/496`

**Impacto operativo:**

- el sistema ya puede empezar a aprender de ciudades fuera de allowlist sin exponer capital real;
- la allowlist manual sigue existiendo, pero ahora convive con una capa automática de promoción/degradación;
- la tabla decisional arrancará con algo de histórico real (`accuracy`, `PnL`, NOAA) y empezará a poblar el nuevo histórico `shadow` a partir de los próximos ciclos.

**Limitación abierta:**

- todavía no existe backfill histórico de `shadow`; la nueva capa aprende bien hacia adelante, pero casi no tiene memoria hacia atrás.

**Siguiente tarea fijada:**

- construir un backfill conservador de `shadow` histórico;
- poblar la capa decisional con evidencia retroconstruida donde haya datos suficientes;
- separar en dashboard lo `retroconstruido` de lo `live`.

**Cierre operativo de la sesión:**

- `python verify_before_deploy.py` vuelve a cerrar en `496/496`;
- se hace `commit + push` a `origin/main` con hash `3c2b568`;
- se lanza `redeploy` en Railway y el servicio vuelve a arrancar sin crash inmediato:
  - dashboard en `0.0.0.0:8080`;
  - `Autenticación OK`;
  - `Telegram polling: OK`;
  - primer ciclo ejecutado y resumen guardado.
- la validación funcional completa del nuevo overlay automático queda pendiente de revisar en el siguiente ciclo live.

---

## Sesión 62 — ranking operacional claro para ciudades (2 abr 2026)

**Disparador:** la nueva capa `shadow/canary/shadow` ya existía y el dashboard enseñaba estado, NOAA y transiciones, pero todavía no permitía responder en segundos qué ciudad estaba más cerca de entrar a operativa ni distinguir con claridad una candidata real de una ciudad degradada o de puro ruido.

**Objetivo exacto de producto:** convertir la capa de ciudades en una vista de decisión, no solo descriptiva:

- ranking principal ordenado por prioridad operativa;
- `readiness score` comprensible;
- `estado actual`, `distancia a canary`, `tendencia` y `motivo principal`;
- buckets legibles `Lista para canary / Cerca de canary / Seguir observando / No tocar / Expulsada / degradada`;
- degradadas recientes separadas visualmente de candidatas normales.

**Cambios implementados en backend (`bot.py`):**

- `build_dashboard_city_decisions()` deja de devolver solo buckets simples y pasa a construir una capa de ranking operacional:
  - `readiness_score`;
  - `priority_group` y `priority_label`;
  - `state_label` y `state_badge`;
  - `distance_label` / `distance_detail`;
  - `trend_label`;
  - `main_reason`;
  - answers rápidas `top_candidate`, `next_candidate`, `cooling_city` y `noise_city`.
- la puntuación combina de forma legible:
  - actividad `shadow` (`edges`, `cycles`, `best_edge`);
  - cobertura NOAA;
  - histórico real (`trades`, `WR`, `PnL`);
  - overlay automático (`auto_canary`, `auto_shadow`, transiciones).
- penalización explícita para ciudades degradadas o expulsadas:
  - una ciudad con shadow activo pero degradada deja de competir como candidata normal;
  - `Dallas` queda cubierta como `Shadow degradada` y `Enfriándose` cuando su overlay / histórico lo justifican.

**Cambios implementados en UI (`templates/dashboard.html` + `static/dashboard.css`):**

- nueva cabecera `Vista de decisión por ciudad`;
- bloque superior con lectura de 10 segundos:
  - `Más cerca de entrar`;
  - `Siguiente`;
  - `Alejándose`;
  - `No merecen atención`.
- nueva tabla principal de ranking con columnas:
  - `Ciudad`;
  - `Score`;
  - `Estado actual`;
  - `Distancia a canary`;
  - `Tendencia`;
  - `Motivo principal`.
- barras de score y acentos visuales por prioridad;
- fila visualmente diferenciada para degradadas (`city-ranking-row-degraded`).

**Copy / UX refinado al cierre:**

- la vista se reescribe con lenguaje más ejecutivo:
  - `Vista de decisión por ciudad`;
  - `Más cerca de entrar`;
  - `Alejándose`;
  - `No merecen atención`;
  - `Reiniciar por degradación`;
  - `Ya operativa`;
  - `histórico real malo`;
  - `bloqueada por política`;
  - `NOAA aún corta`.

**Tests y verificación:**

- `verify_before_deploy.py` gana cobertura nueva para:
  - presencia del ranking en template y CSS;
  - prioridad real del top candidate;
  - caso de `Dallas` como `shadow degradada`;
  - semántica de `readiness_score`, `distance_label`, `trend_label` y `ranking_summary`.
- resultado final local:
  - `python verify_before_deploy.py`
  - `500/500`

**Incidencia de proceso detectada y corregida en el cierre:**

- al hacer `commit + push` del cambio funcional se cerró código y scoreboard, pero todavía faltaban `CONTEXTO.md` y `HISTORIAL_SESIONES.md`;
- el propio playbook seguía exigiendo esas dos capas para considerar la sesión cerrada;
- se corrige con un cierre documental adicional y sincronización final de:
  - `CONTEXTO.md`;
  - `HISTORIAL_SESIONES.md`;
  - `agent_events.jsonl`.

**Cierre operativo de la sesión:**

- commit funcional del ranking: `e4dce44` (`ux: add operational city ranking view`);
- `git push origin main` completado;
- deploy lanzado hacia Railway;
- queda pendiente, ya para la siguiente sesión, validar en live que el ranking separa bien `candidatas reales vs degradadas` y, después, retomar el backfill conservador de `shadow` histórico.

---

## Sesión 63 — cierre mínimo de hardening de tooling/documentación verificado localmente (2 abr 2026)

**Disparador:** después del cierre de proceso de la sesión 58 quedaban matices de RTK/Engram escritos todavía como no verificados o solo parcialmente confirmados. La verificación real ya existía fuera del repo; faltaba alinear la documentación sin reabrir aquella sesión ni tocar el bot.

**Qué se corrige en esta pasada:**

- `OPERATIONS_PLAYBOOK.md` deja explícito que RTK y Engram son setup global del usuario, no dependencias versionadas del proyecto.
- RTK queda marcado como verificado en esta máquina para Codex con evidencia local ya comprobada:
  - `rtk --version`;
  - `rtk init -g --codex`;
  - uso real desde Codex con `rtk git status` y `rtk git diff`.
- Engram queda marcado como operativo en este caso real:
  - `engram setup codex` funcionó;
  - en la extensión de Codex para VS Code hizo falta añadir manualmente por UI el servidor MCP `engram`;
  - configuración usada: `C:\Users\USUARIO\go\bin\engram.exe` + `mcp`;
  - tras eso, Codex ya vio herramientas `mcp__engram__...` en una sesión real.
- `CONTEXTO.md` añade una nota corta para que el estado actual del repo recuerde ese matiz sin convertir memoria externa en fuente de verdad.

**Filosofía que se mantiene:**

- repo = fuente de verdad del proyecto;
- Engram = memoria complementaria, no estado canónico;
- RTK = capa de reducción de ruido/contexto para shell, no requisito del repo.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA ni scheduler;
- no hubo refactor;
- no hubo deploy;
- el cambio fue solo documental y de trazabilidad mínima.

---

## Sesión 64 — setup Claude Code + diagnóstico operativo exploratorio (2 abr 2026)

**Disparador:** primera sesión real de Claude Code en este repo (no Claude.ai ni Codex). El objetivo era verificar que las herramientas de infraestructura quedaban operativas y después hacer un primer diagnóstico del estado actual del bot.

**Qué se configuró y verificó en esta sesión:**

- **Claude Code** queda preparado y funcional para este repo. Es la primera vez que Claude Code opera aquí como agente interactivo (distinción importante: antes se usaban Claude.ai y Codex).
- **Subagente `trading-ops-analyst`** creado en `.claude/agents/trading-ops-analyst.md`. Se probó en live en esta misma sesión y produjo resultados útiles.
- **RTK** verificado operativo en Claude Code en Windows vía `~/.claude/CLAUDE.md`. La integración funciona en sesión real.
- **Engram** verificado operativo en Claude Code. Las herramientas `mem_save`, `mem_search` y `mem_context` son accesibles via MCP y se usaron en esta sesión. Primera memoria guardada para este proyecto.

**Diagnóstico operativo realizado (prueba exploratoria — no conclusión final):**

- Se usó el subagente `trading-ops-analyst` para hacer un primer diagnóstico del estado del bot.
- La primera lectura usó el snapshot Railway del 1-abr-20:13 UTC como fuente, que resultó obsoleto.
- El usuario corrigió el estado real: Chicago Apr1 fue vendida manualmente ~11 horas antes; solo quedan 2 posiciones abiertas en Atlanta; cash disponible ~$27.20; cartera ~$31.58; P&L all-time -$21.79.
- Se rehízo el diagnóstico con el estado real corregido.

**Hallazgos del diagnóstico (exploratorio — requieren verificación en live):**

1. **Discrepancia repo vs real:** el snapshot de Railway (y presumiblemente `postmortem.json`) sigue mostrando Chicago Apr1 como posición abierta. Las ventas manuales no quedan registradas en el bot. Esto puede afectar al cálculo de exposición en el próximo ciclo.
2. **Atlanta no se autobloqueó:** con WR 14.3% en 14 trades, la regla `CITY_BLOCK_WIN_RATE=25%` debería haber bloqueado Atlanta automáticamente. No lo hizo. Es el hallazgo más urgente antes del próximo ciclo, especialmente porque con $27.20 disponibles el bot puede abrir nuevas posiciones en Atlanta.
3. **LOSS_TOTAL = 70.6% de los cierres:** 60 de 85 cierres terminaron en pérdida total. P&L on-chain all-time -$36.42 sobre $161.21 invertido (CSV hasta 31 mar).
4. **Deploy sesión 62 sin validación explícita:** el commit `e4dce44` está en `origin/main` pero no se ha confirmado que Railway lo esté ejecutando.

**Clasificación explícita:**

- El análisis completo de esta sesión fue **exploratorio**, realizado con datos parcialmente obsoletos y sin acceso directo a Railway live.
- Los hallazgos son orientativos y sirven como punto de partida para la próxima sesión, no como conclusiones cerradas.
- La prioridad operativa de mañana queda documentada en `CONTEXTO.md`.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler ni arquitectura core;
- no hubo deploy;
- no se ejecutó la suite;
- el trabajo fue solo setup de infraestructura, diagnóstico y documentación de cierre.

---

## Sesión 65 — hotfix Atlanta bloqueada en Railway + cierre de diagnóstico live (3 abr 2026)

**Disparador:** la sesión 64 dejó como prioridad urgente validar por qué Atlanta seguía operando pese a `WR 14.3%` y umbral de bloqueo `25%`. Antes del próximo ciclo, se necesitaba comprobar el estado live real y aplicar el corte operativo mínimo.

**Evidencia live leída en Railway:**

- `alerts_state.json` contiene `city_accuracy_flagged.Atlanta` desde `2026-03-30T21:02:35.447220+00:00`, con `trades=4`, `wins=1`, `win_rate=25.0`, `pnl=-1.12777159`.
- `postmortem.json` para Atlanta da:
  - `23` trades cerrados;
  - `4` wins si se sigue el criterio real de `get_city_accuracy()` (`pnl_cash > 0`);
  - `WR 17.4%`;
  - `LOSS_TOTAL=17`, `SELL=4`, `RESOLVED_WIN=2`;
  - una entrada antigua anómala todavía `open`: `Atlanta|YES|2026-03-28|2026-03-26T08:00:35.955319+00:00`.
- En Railway no existían overrides de `CITY_MIN_TRADES_FOR_BLOCK` ni `CITY_BLOCK_WIN_RATE`, así que aplicaban los defaults del código.
- Antes del hotfix, `BLOCKED_CITIES` tampoco estaba seteada en Railway, por lo que Atlanta no estaba bloqueada por env var.

**Conclusión del bug:**

- el problema inmediato no era que Telegram no avisara;
- la alerta sí se disparó una vez, pero al quedar Atlanta ya registrada en `city_accuracy_flagged`, no se reenvía aunque el WR siga empeorando;
- más importante: el supuesto “auto-bloqueo” no bloquea nada por sí mismo; solo recomienda añadir la ciudad a `BLOCKED_CITIES`;
- por eso Atlanta seguía habilitada para nuevos BUYs.

**Hotfix aplicado en producción:**

- se seteó en Railway:
  - `BLOCKED_CITIES=London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara,Atlanta`
- verificación posterior:
  - `railway_safe.ps1 variable list --kv` ya muestra Atlanta dentro de `BLOCKED_CITIES`;
  - logs de Railway confirman redeploy/reinicio a `2026-04-03 09:16:46 UTC` y arranque limpio de `POLYMARKET BOT v10.6.10`.

**Incidencia operativa secundaria detectada:**

- pese a la reparación previa, la CLI de Railway volvió a caer en `Unauthorized` / `invalid_grant`;
- se recuperó manualmente con:
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset`
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless`
  - validación con `railway_safe.ps1 whoami` y `status`
- queda como sesión separada revisar por qué este relogin vuelve a ser necesario.

**Apunte de diseño para la siguiente sesión (Claude):**

- el nombre “auto-bloqueo” es engañoso;
- si el sistema debe sacar una ciudad de operativa automáticamente, no basta con una alerta one-shot;
- hace falta persistir `qué ciudad se sacó`, `por qué`, `con qué evidencia`, `cuándo`, y que el scan de BUYs lea esa política persistente.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se cambió lógica de trading;
- el cambio de producción fue solo el hotfix de env var para Atlanta;
- la corrección estructural queda explícitamente aplazada a otra sesión.

---

## Sesión 66 — auto-bloqueo real persistido por ciudad en local (3 abr 2026)

**Disparador:** tras el hotfix manual de Atlanta en Railway, faltaba cerrar el bug de diseño de fondo: el supuesto auto-bloqueo no podía seguir siendo solo `city_accuracy_flagged + Telegram`, porque eso no sacaba la ciudad de BUYs ni dejaba política persistida con evidencia.

**Alcance respetado:**

- no se tocaron reglas de entrada/salida, NOAA, scheduler ni arquitectura core de trading;
- el cambio se concentró en la capa de política por ciudad ya existente en `load_city_policy_state/save_city_policy_state/get_effective_city_mode/sync_city_policy_state`;
- no hubo push ni deploy en esta sesión.

**Cambios implementados:**

- `city_policy_state.json` añade `auto_blocked_cities` como tercera capa persistida del overlay, junto a `auto_canary_cities`, `auto_shadow_cities` y `transition_history`.
- Se añade `_build_auto_city_block_policy()` para persistir por ciudad:
  - `action="auto_block"`;
  - `reason`;
  - `metrics` (`trades`, `wins`, `win_rate`, `pnl`, `observed_count`, `shadow_seen`, `shadow_edges`, `shadow_best_edge`, `support_count`);
  - `from_mode`;
  - `triggered_at`.
- `get_effective_city_mode()` da prioridad a `auto_blocked_cities` y devuelve `blocked` aunque la ciudad siga en `ACTIVE_TRADING_CITIES`, así el scan de BUYs ya respeta la política sin depender solo de Telegram.
- `sync_city_policy_state()` cambia la transición de salida de `active/canary -> shadow` a `active/canary -> blocked`, guarda `action` + `metrics` en `transition_history`, elimina overlays previos `auto_canary/auto_shadow`, y deja la reactivación como manual/conservadora retirando la política persistida.
- `build_dashboard_city_observation()` y `build_dashboard_city_decisions()` pasan a reconocer el auto-bloqueo persistido y exponen `policy_action`, `policy_reason`, `policy_metrics` y `policy_changed_at` para que el dashboard no pierda el motivo/evidencia.
- `verify_before_deploy.py` añade tests estructurales y funcionales para:
  - existencia de `_build_auto_city_block_policy`;
  - persistencia de `auto_blocked_cities`;
  - prioridad de `auto_blocked` sobre allowlist activa;
  - transición `to=blocked` con `action=auto_block` y métricas.

**Validación local:**

- `python verify_before_deploy.py` pasa en `506/506`.

**Estado final:**

- el auto-bloqueo real queda implementado localmente y listo para push/deploy;
- Atlanta sigue bloqueada manualmente en Railway por `BLOCKED_CITIES` desde la sesión 65, así que no hay riesgo inmediato de BUYs nuevos mientras se valida el overlay persistido;
- siguiente paso recomendado: desplegar, inspeccionar `city_policy_state.json` en Railway y confirmar por logs que el scan salta ciudades auto-bloqueadas aunque sigan en la allowlist manual.

---

## Sesión 67 — hardening del relogin recurrente de Railway CLI (3 abr 2026)

**Disparador:** el usuario pidió resolver el problema de relogin recurrente de Railway sin volver a empezar desde cero ni tocar lógica de trading.

**Evidencia reunida antes de cambiar tooling:**

- `CONTEXTO.md`, `RAILWAY_AUTH_BUG_HANDOFF_2026-04-01.md`, `OPERATIONS_PLAYBOOK.md` y las sesiones 50/54/65 dejaban una pista consistente: `invalid_grant` reaparecía tras una auth aparentemente reparada, y el workaround manual `reset + launch-login -Browserless` seguía funcionando.
- En esta sesión, `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor` confirmó que no había proxy persistente ni de proceso, `config.json` seguía enlazado, y el token pudo refrescarse correctamente hasta `2026-04-03T11:07:57Z`.
- `railway_safe.ps1 whoami` y `railway_safe.ps1 status` funcionaron y siguieron funcionando incluso lanzados en paralelo con `doctor`.

**Cambios implementados:**

- `tools/railway_safe.ps1` añade un preflight de refresh OAuth:
  - lee `%USERPROFILE%\.railway\config.json`;
  - parsea `tokenExpiresAt`;
  - si faltan `<=300s` para expirar y el proceso actual no puede abrir el config en modo escritura, corta con instrucciones explícitas en vez de dejar que Railway intente refrescar en un contexto frágil.
- `tools/railway_safe.ps1` también serializa todas las invocaciones del CLI con un mutex global `Global\polymarket-bot-railway-cli`, para evitar carreras de refresh concurrente contra el mismo `refreshToken`.
- `tools/railway_auth_repair.ps1` usa ese mismo mutex en `doctor`, `whoami/version` y `interactive-login`, y `doctor` ahora muestra:
  - `Writable from this process`;
  - `secondsToExpiry`;
  - `refreshWriteRiskSoon`.

**Diagnóstico de causa raíz, formulado con cautela:**

- ya no queda probado que el problema sea solo proxy o solo sandbox;
- la hipótesis más plausible pasa a ser una combinación de refresh sin escritura persistida y/o refreshes concurrentes del Railway CLI sobre el mismo `config.json`;
- el hardening nuevo cubre ambas rutas antes de que la CLI vuelva a degradar el estado OAuth local.

**Validación operativa final:**

- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami` -> `Logged in as pablogomez.eu@gmail.com`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status` -> `Project: enchanting-respect / Environment: production / Service: polymarket-bot`
- `powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor` -> `Writable from this process: True`, `tokenExpiresAtUtc=2026-04-03T11:07:57Z`, `refreshWriteRiskSoon: False`, `ExitCode: 0`

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler, exits ni arquitectura core;
- no hubo push ni deploy;
- el cambio fue solo hardening de tooling operativo y trazabilidad documental.

## Sesión 68 — validación end-to-end deploy + corrección desfase env vars (3 abr 2026)

**Disparador:** verificar que el código de sesiones 66-67 estaba desplegado en Railway y que el auto-block engine funciona correctamente end-to-end.

**Verificaciones completadas:**

- Commits `aeebdfb` (sesión 66) y `b54407c` (sesión 67) confirmados en local y pushed a origin.
- `verify_before_deploy.py` pasa 506/506.
- Railway redesplegó a 16:36 UTC (post-push) y de nuevo a 16:54 UTC (post-corrección env var), v10.6.10 limpio.
- `city_policy_state.json` no existe aún en Railway: esperado por diseño (se crea solo cuando `sync_city_policy_state()` detecta un cambio en un ciclo).
- Scan de BUYs verificado en código (L10422-10426): `get_effective_city_mode()` → si `blocked` → `continue` (skip total). Funciona para bloqueos manuales (`BLOCKED_CITIES`) y automáticos (`auto_blocked_cities`).
- Dashboard live auditado via `/api/dashboard.json`: datos cruzados entre portfolio, postmortem (126 registros), trade_lifecycle (62 registros), city_accuracy y exit_breakdown sin desfases funcionales críticos.

**Desfase corregido:**

- Atlanta estaba simultáneamente en `ACTIVE_TRADING_CITIES` (default del código) y en `BLOCKED_CITIES` (env var Railway, sesión 65). Funcionalmente no causaba daño (`is_city_blocked` se evalúa primero), pero impedía que el auto-block engine la procesara y confundía el dashboard.
- Corrección: `ACTIVE_TRADING_CITIES` seteada explícitamente en Railway como `Chicago,Dallas,Buenos Aires`. Redeploy confirmado.

**Hallazgo adicional: Dallas degradada a shadow por overlay:**

- `shadow_city_tracking.json` registra degradación de Dallas el 2 abr (15 trades, WR 6.7%, PnL -$1.66). El overlay `auto_shadow` tiene prioridad sobre `ACTIVE_TRADING_CITIES` en `get_effective_city_mode()` (L620).
- El decision engine la propone como candidata a canary (7 edges shadow, pico 38.9%), pero la promoción requiere que alguien la saque de `auto_shadow` o que el engine la promueva automáticamente en un ciclo futuro.

**Desfases menores documentados (no bloquean):**

- NYC (21 trades, no en ACTIVE ni BLOCKED): ruido informativo, no funcional.
- CONTEXTO.md tenía cash stale ($27.20 vs $21.62 real): actualizado.
- Chicago Apr1 cerrada manualmente: podría no estar en postmortem como closed. Pendiente verificar.
- 4 resolved_won pendientes cobro (~$3.38): capital trabado, no desfase de accounting.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA, scheduler, exits ni arquitectura core;
- único cambio en producción: env var `ACTIVE_TRADING_CITIES` en Railway.

---

## Sesión 69 — reconciliación postmortem Chicago Apr1 sin edición live (3 abr 2026)

**Disparador:** cerrar la tarea acotada pendiente de sesión 68: verificar si `Chicago Apr1` seguía `open` en `postmortem.json` y, si era así, cerrarla manualmente para que `city_accuracy` no quedara sesgada.

**Evidencia descargada de Railway:**

- Se bajó `/app/data/postmortem.json` vía `tools/railway_safe.ps1 ssh "cat /app/data/postmortem.json"` a un snapshot temporal local.
- La entrada `Chicago|YES|2026-04-01|2026-03-31T23:00:28.735723+00:00` ya estaba `status=closed`, `close_action=LOSS_TOTAL`, `close_reason=micro_position_unsellable`, `closed_at=2026-04-02T07:39:19.807998+00:00`, `total_amount=1.88`, `total_shares=9.89`, `avg_entry_price=0.1901`, `pnl_cash=0.0`.
- Con la misma lógica de `get_city_accuracy()`, Chicago recalcula a `4 trades`, `1 win`, `WR 25.0%`, `PnL +$2.09`, así que esta fila Apr1 ya no explica el posible sesgo por denominador incompleto.

**Hallazgo nuevo:**

- Siguen abiertas 3 filas legacy de Chicago no relacionadas con Apr1:
- `Chicago|YES|2026-03-26|2026-03-25T16:49:42.552882+00:00`
- `Chicago|YES|2026-03-27|2026-03-27T16:00:37.157021+00:00`
- `Chicago|YES|2026-03-28|2026-03-28T16:00:32.932997+00:00`
- Si hay sesgo pendiente en `city_accuracy`, ahora la hipótesis prioritaria son esas filas legacy todavía `open`, no `Chicago Apr1`.

**Acción tomada y límite de alcance:**

- No se editó `postmortem.json` live porque la fila Apr1 ya estaba cerrada.
- No se tocó `bot.py`, trading, NOAA, scheduler ni reglas de salida.
- Solo se corrigió la trazabilidad documental para retirar el aviso stale de Apr1 y mover la siguiente tarea al saneamiento de esas 3 filas Chicago antiguas.
