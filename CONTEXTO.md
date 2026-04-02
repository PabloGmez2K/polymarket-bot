# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 2 de abril de 2026 (Sesión 61 — shadow/canary automático + dashboard decisional por ciudad)
**Próxima sesión:** hacer un backfill conservador de `shadow` histórico para poblar la nueva capa de decisiones por ciudad con evidencia retroconstruida, separando claramente lo estimado hacia atrás de lo observado live.

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta.

**Bankroll configurado:** $25.00 en Railway. El 30 mar se depositaron `+$14.99` para volver a la zona objetivo de operación.

**IMPORTANTE — Fuente de resolución:** Polymarket NO usa Open-Meteo — usa Weather Underground (wunderground.com). Esto ha causado pérdidas en London (2 veces). No apostar en London hasta resolver.

---

## Estado financiero (referencia histórica fin sesión 30 — 29 mar 2026)

- **Cartera Polymarket:** ~$18.89 (-$9.52 último día, -50.4%)
- **Disponible para operar:** ~$13.63
- **P&L all-time:** ~-$21.84
- **Causa principal de pérdidas:** Open-Meteo vs Weather Underground discrepancia + sigma ampliada de v10.5 que vendía posiciones ganadoras + intra-cycle monitor que disparaba SL ante fluctuaciones normales
- **Acción tomada:** v10.6.0 revierte lógica de trading a v10.3 (sigma original, sin intra-cycle, sin MIN_EDGE_EXACT)
- **Actualización 30 mar:** depósito manual `+$14.99` para reponer bankroll operativo hacia el objetivo de `$25`.

Para estado exacto: usar `/focus` + `/info` + `/cartera` + `/rendimiento` + `/accuracy` en Telegram.

---

## Qué hace el bot v10.6.10 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas.

**0.5. Gestión activa (manage_positions):** Para cada posición abierta:
- ¿currentValue < $0.10? → LOSS_TOTAL
- ¿curPrice >= 0.98? → SKIP (resuelta, esperando pago)
- ¿redeemable=True? → SKIP (cash garantizado pendiente de claim/redeem; no cuenta como riesgo)
- ¿PnL < -25%? → VENDER (stop-loss)
- ¿PnL > +40%? → VENDER (take-profit)
- Si no: recalcula edge. Si edge < -3% → VENDER (re-evaluación)
- Devuelve `sold_token_ids` para evitar re-entrada en el mismo ciclo

**0.6. Auditoría actual:** Convierte SELL_PENDING → SELL/SELL_FAILED según fills confirmados y mantiene una pseudo-auditoría `forecast_vs_forecast posterior` con Open-Meteo. **No valida contra la fuente real de resolución de Polymarket (Weather Underground).**

**1-5. Buscar oportunidades:** Escanea ~330 mercados, consulta previsiones, calcula edge, cruza con señales de traders, dimensiona con Half-Kelly, respeta exposición máxima 40%.

**6. Ejecución:** Órdenes GTC limit, registra en `performance.json`, sincroniza `postmortem.json` y notifica por Telegram.

**7. Registro de ciclo (v10.4.1+):** Guarda resumen en cycle_summary.json + append en cycles_history.jsonl.

**Al arrancar (v10.4.3+):** Carga ciclos históricos desde `cycles_history.jsonl` (contador total no se reinicia con deploys).

**Contador dual de ciclos (v10.5.4):** Mantiene `cycle_count` como histórico total y añade `cycle_count_series` para la serie lógica actual (`LOGIC_SERIES`). Cada ciclo nuevo guarda `logic_series` y `logic_cycle_number`. `/estado` y `/info` muestran ambos para comparar estrategia nueva sin perder continuidad operativa.

**Bloqueo ciudades perdedoras + fix posiciones fantasma (v10.5.12):** `BLOCKED_CITIES` ampliado a 10 ciudades (London, Miami, Seattle, Paris, Tel Aviv, Wellington, Toronto, Madrid, Singapore, Ankara) tras análisis de accuracy real: todas con 0% WR y pérdidas confirmadas en producción. Solo quedan activas Chicago, Atlanta, Buenos Aires y Dallas. Fix de observabilidad: posiciones con `currentValue < 0.01` ahora se registran también como `LOSS_TOTAL` en vez de ignorarse silenciosamente; antes quedaban en postmortem como "open" para siempre ocultando la pérdida real.

**Fixes dashboard + scorecard (v10.5.11):** Corrección de bug en el checklist del dashboard: el check `Drawdown últimos N cierres` ahora muestra `Esperando muestra` hasta tener `DRAWDOWN_WINDOW` cierres completos (antes mostraba `OK` con solo 1-4 trades, porque `recent_window_size < DRAWDOWN_WINDOW` evaluaba siempre como verdadero). Nuevo helper `_sync_agent_events_seed()` que fusiona la semilla local de `agent_events.jsonl` con el Volume en cada arranque, añadiendo solo los eventos nuevos que no estén ya persistidos; resuelve el problema de que las sesiones 27-28 del scoreboard no aparecían en Railway porque `_seed_data_file()` no sobrescribía un archivo ya existente.

**Dashboard web + scorecard de agentes (v10.5.10):** Levanta un panel HTML separado de Telegram en el mismo servicio Railway, accesible por navegador en `PORT`. Usa modo oscuro, separa checklist histórico vs serie `v10.5`, muestra ciclos legacy con etiquetas legibles, enseña el scoreboard por stages (`proposed / implemented / validated`) a partir de `agent_events.jsonl`, evita mostrar métricas de serie como `0.0%` o `+$0.00` cuando todavía no hay cierres, distingue visualmente entre `fallo real` y `esperando muestra` en el checklist y añade cuatro bloques nuevos: `Progreso`, `Trofeos`, `Desbloqueos` y `Balance por tipo de cierre / liquidación`, para saber no solo qué evidencia falta sino también si el bot está cortando ganancias demasiado pronto, acumulando `stop_loss`, dejando `pending_exit` sin reconciliar o generando valor pendiente de canjear.

**Zona horaria por ciudad (v10.4.5):** Ya no usa offsets manuales; usa zonas IANA reales con `ZoneInfo` para que DST cambie automáticamente sin tocar el código en marzo/octubre.

**Postmortem base (v10.4.5):** Mantiene `postmortem.json` sincronizado con `BUY`, `SELL_PENDING → SELL/SELL_FAILED`, `LOSS_TOTAL` y `RESOLVED_WIN` para poder analizar cierres y resoluciones con datos estructurados.

**Alertas de observabilidad (v10.4.6):** Hace backfill automático de `postmortem.json` desde `performance.json` si aún no existía, guarda estado persistente en `alerts_state.json`, y envía alertas one-shot por Telegram para `30 trades limpios`, `signals.json` con problemas y `pending_exit` atascadas.

**Bloqueo operativo de London (v10.4.7):** London queda excluida del escaneo de oportunidades por discrepancia conocida `Weather Underground vs Open-Meteo`. Ya no depende de disciplina manual; el bot la filtra en código.

**Refinamiento Telegram (v10.4.8):** `/traders` alinea la cartera por `ciudad + lado + fecha exacta`, `/postmortem` deja de mostrar etiquetas legacy tipo `? YES`, y `/detalle` enseña el último ciclo completo del log en vez de cortar a 40 líneas.

**Sigma widening + exact edge filter + smart alerts (v10.5.0):** Recalibración tras -$8.57 en 17 trades cerrados. Sigma ampliada (Día 0: 2.0 → Día 6+: 4.5), filtro MIN_EDGE_EXACT 15% para apuestas exactas, alertas de drawdown/scaling/win rate. **REVERTIDO en v10.6.0** — la sigma ampliada vendía posiciones ganadoras en re-eval y bloqueaba entradas.

**Intra-cycle SL/TP monitor (v10.5.1):** Thread daemon cada 90 minutos revisa posiciones y ejecuta SL/TP sin esperar al ciclo de 8h. Configurable con `INTRA_SL_INTERVAL` (0=desactivar). Lock para evitar conflicto con ciclo principal. **DESACTIVADO en v10.6.0** — disparaba SL ante fluctuaciones normales en mercados diarios.

**Revert trading logic (v10.6.0):** Sigma restaurada a v10.3 (1.2/1.5/2.0/2.5/3.0), intra-cycle desactivado (default 0), MIN_EDGE_EXACT eliminado (usa MIN_EDGE=7% para todo). Se mantiene toda la observabilidad (postmortem, accuracy, alerts, dashboard, ciudades bloqueadas). El problema real es la fuente de datos, no la confianza del modelo.

**Hardening alerta bankroll (v10.6.2):** La alerta de bankroll bajo ahora solo se activa con señal fiable de cartera (`cash_ok` y sin `api_error`) tanto en Telegram como en dashboard, evitando falsos “recargar” cuando falla la API. Añade `LOW_BANKROLL_RESET_MARGIN=1.0` para rearmar la alerta al salir de la zona roja sin exigir recuperar hasta 2x el umbral.

**Investigación estratégica Codex + Claude (30 mar):** La comparación cruzada dejó tres conclusiones de alta prioridad: (1) `resolution fidelity first` sigue siendo la dirección correcta; (2) Dallas está mal mapeada en producción lógica (`KDFW` en código vs `KDAL` en reglas reales de Polymarket); y (3) la auditoría `forecast_vs_real` actual no compara contra la fuente real de resolución y debe renombrarse/documentarse antes de confiar en esa señal. Se añadieron tres artefactos al repo: `RESEARCH_CODEX_HANDOFF_2026-03-30.md`, `RESEARCH_CLAUDE_2026-03-30.md` y `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`.

**Resolution fidelity hardening (v10.6.3):** Corrige Dallas a `Dallas Love Field / KDAL`, añade la capa declarativa `RESOLUTION_ICAO` con ICAO + URL de Weather Underground para ciudades activas/bloqueadas (y el resto de estaciones actuales), y deja explícito en código/logs que la pseudo-auditoría histórica `forecast_vs_real` sigue siendo solo `forecast original vs forecast posterior Open-Meteo`, no una validación de la fuente real de resolución. `verify_before_deploy.py` sube a `358/358` y añade checks específicos de Dallas, `RESOLUTION_ICAO` y nomenclatura honesta de auditoría.

**Observed proxy layer NOAA (v10.6.4):** Añade `noaa_station_id` explícito en `RESOLUTION_ICAO` solo para las 4 ciudades activas y crea una auditoría separada `observed_vs_forecast` con `source="noaa_ncei"`. Esta capa compara forecast original vs observado NOAA NCEI con lag de 2 días y deja intacta la clave legacy `forecast_vs_real`. Importante: es `observed proxy`, no la fuente real de settlement de Polymarket. El spike de Buenos Aires quedó cerrado: `SAEZ` usa `87576099999`, confirmado vía NOAA HOMR + probe real sobre `global-hourly`. `verify_before_deploy.py` sube a `371/371`.

**Dashboard NOAA observado (v10.6.5):** Añade un bloque nuevo `Calidad Forecast Observada (NOAA)` separado de performance/trading. Lee `audit.json -> observed_vs_forecast`, muestra `n total`, `MAE`, `bias`, cobertura por ciudad activa y los últimos 20 casos. Mantiene visible un bloque legacy `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y `ultimo registro` prominentes, sin mezclar ambas series. `verify_before_deploy.py` sube a `386/386`.

**Foco fidelity + Telegram NOAA (30 mar, sin bump):** El research final `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` concluye `recomiendo no adoptar`, salvo `FMEA-lite` en playbook y una definición mínima de `fallo real / limitacion conocida / ruido`. `OPERATIONS_PLAYBOOK.md` añade ese premortem corto para cambios core, y `run_observability_alerts()` pasa a enviar hitos NOAA one-shot (`primer caso`, `n>=3`, `n>=10`, `ciudad con muestra`, `ciudad interpretable`). Además aparece `/noaa` y `/observabilidad` en Telegram como vista rápida de `sample`, `MAE`, `bias`, cobertura por ciudad y últimos casos, sin tocar el menú principal. `verify_before_deploy.py` sube a `416/416`.

**Allowlist de ciudades activas (v10.6.6):** Añade `ACTIVE_TRADING_CITIES` como allowlist explícita para entradas nuevas, con default `Chicago,Atlanta,Dallas,Buenos Aires`. El scan de mercados ya no depende solo de `BLOCKED_CITIES`: si una ciudad no está en el allowlist, se salta con log `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`. Importante: esto solo afecta BUYs nuevos; `manage_positions` sigue gestionando SL/TP/reeval en posiciones ya abiertas de cualquier ciudad. `verify_before_deploy.py` sube a `419/419`.

**Dashboard estado por ciudad (v10.6.7):** El dashboard añade una tabla nueva `Estado de observacion por ciudad` que cruza `ACTIVE_TRADING_CITIES`, `BLOCKED_CITIES`, muestra NOAA y cierres validados por ciudad. La tabla distingue entre `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` y `Sin observabilidad`. Importante: es una capa descriptiva para seguimiento, no una promocion automatica de ciudades.

**Control Center Discovery/Stabilization (v10.6.8):** Nueva capa 1 operativa tanto en dashboard como en Telegram. El dashboard abre ahora con un `Control Center` que responde explícitamente `¿está sano el sistema?`, `¿hay que intervenir hoy?`, `¿qué limita ahora?`, `¿estamos aprendiendo o solo operando?` y `¿cuál es la acción recomendada hoy?`. Añade `build_dashboard_focus_center()`, prioriza incidentes reales, allowlist y crecimiento NOAA por encima del resto, mueve el detalle pesado a capas inferiores y crea `/focus` en Telegram como vista principal corta, manteniendo `/estado`, `/noaa`, `/accuracy` y `/detalle` como segunda capa.

**Mission HUD operativo (v10.6.9):** La capa 1 del dashboard da un paso mas y se convierte en un HUD tipo videojuego, pero con semantica operativa real. La cabecera pasa a mostrar la mision actual, `System HP`, progreso de `allowlist vs NOAA`, crecimiento de muestra NOAA y ruta operativa por etapas. Añade tabs interactivos `Overview / Progress / Cities`, barras de progreso, `city race` por cobertura NOAA y un `Operator Console` para conservar el detalle fuera del primer golpe de vista. Se mantiene la misma prioridad: discovery / stabilization, sin tocar trading, exits, scheduler ni gestion de posiciones.

**Focus readability pass (v10.6.10):** Refinamiento de la capa 1 tras la primera previsualizacion real. El dashboard pasa a modo claro por defecto para lectura prolongada, agrupa las ciudades en `universo operativo`, `seguimiento/referencia` y `archivo bloqueado`, y deja de repetir la alerta `signals.json stale` como bloqueo principal cuando el cuello de botella real es `NOAA / muestra / cobertura`. La prioridad operativa no cambia: sigue siendo discovery / stabilization, pero con menos ruido y lectura mas directa. `verify_before_deploy.py` sube a `449/449`.

**Auditoría NOAA + hardening local (31 mar, sin bump):** La revisión operativa sobre Railway `v10.6.10` confirmó que `NOAA 0/10` no era solo “falta de tiempo”. El pipeline que llena `audit.json -> observed_vs_forecast` sí tenía casos elegibles, pero el fetch NOAA quedaba ciego porque dependía de `global-hourly`, que devolvía vacío para varios casos 2026 donde `daily-summaries` sí ofrecía `TMAX`. Se añaden `noaa_daily_station_id` para Chicago/Atlanta/Dallas, un helper `fetch_noaa_daily_tmax()`, un wrapper que prioriza `daily-summaries/TMAX` y luego cae a `global-hourly`, y trazabilidad extra (`noaa_daily_station_id`, `observed_dataset`) en cada caso guardado. Tras review adversarial adicional se endurece también el guard de lag en el helper diario y se recupera un test explícito del fallback `daily vacío -> hourly`. Evidencia mínima reconstruida: al menos `7` casos `city|date` elegibles ya existían frente a `0` guardados en producción. `verify_before_deploy.py` sube a `453/453`.

**Trade lifecycle observability layer (31 mar, sin bump):** Se añade una nueva capa derivada `trade_lifecycle.json` para convertir cada posición en una traza completa y legible: `entry_context`, `latest_entry_context`, lista de `buys`, `timeline`, `exit_attempts`, `position_snapshots`, `market_observations`, `close_context`, `post_exit_analysis` y un `summary` agregado con `top_upside_left`. La capa se reconstruye desde `performance.json` + `postmortem.json`, se actualiza automáticamente en cada `BUY/SELL_PENDING/SELL/SELL_FAILED/LOSS_TOTAL/RESOLVED_WIN`, captura snapshots tanto en `manage_positions()` como en el monitor intra-ciclo y registra qué hizo el mercado tras la salida para medir upside perdido o drawdown evitado. No toca ninguna regla de trading. Tras una pasada de higiene se elimina un bloque duplicado de checks y el runner queda limpio; `verify_before_deploy.py` cierra en `467/467`.

**Trade lifecycle hardening fase 1 (31 mar, sin bump):** La primera revisión del raw live de `trade_lifecycle.json` reveló ruido histórico real: `92` filas en producción, de las que `12` eran duplicados por `id` y correspondían a cierres huérfanos reconstruidos dos veces (par `postmortem` + `performance`) cuando el evento histórico no tenía `token_id/question/date`. Se endurece la capa derivada con matching por `id` reconstruido, coalescing defensivo por `id`, bloque explícito `integrity` tanto global como por record (`partial_historical_record`, `analysis_ready`, faltas de token/question/entry/buys, etc.) y test funcional del caso real de “cierre huérfano” para evitar regresiones. Validación con datos live descargados de Railway: reconstruyendo desde `performance.json + postmortem.json`, el lifecycle queda en `80` records únicos, `0` duplicados residuales y `12` `partial_historical_records`. La suite local sube a `470/470`.

**Hotfix `trade_lifecycle` + normalización `agent_events` (31 mar, sin bump):** Al validar en Railway el despliegue de la fase 1 apareció un bug real en live: `trade_lifecycle` empezó a loguear `Error sincronizando trade_lifecycle: unhashable type: 'list'` tanto en startup como durante el ciclo de las `16:00 UTC`. La causa raíz no era un dato extraño sino una comparación inválida en Python dentro de `_merge_trade_lifecycle_context()` y `_merge_trade_lifecycle_record()`, que usaba sets literales del tipo `{None, "", [], {}}`; eso explota en cuanto la ruta de coalescing se ejecuta sobre records duplicados. El hotfix introduce `_lifecycle_is_empty()` para hacer esas comprobaciones de forma segura, añade una regresión funcional que coalesce dos records con el mismo `id` y `entry_context` no vacío, y normaliza `agent_events.jsonl` del repo a `utf-8` para eliminar el warning de seed corrupta en la suite. `verify_before_deploy.py` sube a `472/472`. Importante: NOAA sigue bien (`observed_vs_forecast` ya mostraba 2 casos reales en Chicago); lo roto es solo el sync incremental del lifecycle en Railway hasta desplegar este hotfix.

**Railway CLI hygiene wrapper (31 mar, sin bump):** Tras el recap operativo se deja un guardrail practico para no repetir el bucle `proxy contaminado -> auth rota -> invalid_grant`. Se añade `tools/railway_safe.ps1`, que limpia `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/GIT_*` solo para el proceso actual, ejecuta `railway.cmd` y restaura el entorno al salir. El playbook queda actualizado con una regla explicita: `railway login` solo en shell interactiva del usuario; uso diario de Railway con el wrapper; y desde Codex, Railway fuera del sandbox cuando la CLI pueda refrescar/escribir `%USERPROFILE%\.railway\config.json`.

**Railway auth repair cerrado (1 abr, sin bump):** La sesión dedicada confirmó que los proxies `127.0.0.1:9` no venían de variables persistentes de Windows ni de perfiles de PowerShell; estaban inyectados solo en el proceso actual. El wrapper seguía siendo correcto para red, pero la auth local estaba degradada: `whoami/status` devolvían `Unauthorized` incluso en entorno limpio. Se endurece `tools/railway_safe.ps1` para limpiar también variantes en minúsculas y `npm_config_*`, se añade `tools/railway_auth_repair.ps1` con `doctor`, `reset`, `launch-login` y `restore-links`, y se documenta el flujo de recuperación. Caso real observado el 1 de abril de 2026: tras `reset + login --browserless`, Railway regeneró `config.json` con `projects = {}` aunque `whoami` ya funcionaba; `restore-links` recuperó el enlace desde el backup sin tocar los tokens nuevos. Estado final validado: `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`, `status` y `logs -s polymarket-bot -n 20` vuelven a funcionar.

**Trade analytics dashboard phase 2 (31 mar, sin bump):** Sobre la base ya saneada de `trade_lifecycle`, se añade una capa analítica nueva `build_dashboard_trade_analytics()` que solo cuenta cierres con `market_seen_after_close` y `close_price * close_shares` utilizables. La nueva vista resume: `sample observado`, `score` de eficiencia observada, `harvest efficiency`, `upside_left_total_cash`, `drawdown_avoided_total_cash`, breakdown por `take_profit / reeval / stop_loss`, timeline corto de exits observados y dos colas de revisión (`top_upside_rows`, `top_protection_rows`). El dashboard gana una sección visible para seguir activamente qué está capturando el bot, qué upside deja y qué downside evita, sin tocar ninguna regla de trading. `verify_before_deploy.py` sube a `477/477`.

**Trade console dashboard (31 mar, sin bump):** La primera capa analítica de exits resultó demasiado estrecha para uso diario: respondía bien a `¿estamos capturando bien los exits observados?`, pero no a `¿qué hizo exactamente el bot en cada operación?`. Sobre la misma base de `trade_lifecycle`, el dashboard añade ahora una pestaña separada tipo consola con dos vistas: `Resumen` y `Trades`. Esta nueva capa expone `Operaciones totales`, `TP`, `SL`, `Ganadas`, `Perdidas`, `PnL neto`, `Dejado de ganar` y `Protegido`, además de una tabla por trade con: mercado, condición de entrada del bot, condición de salida, resultado, valor, centavos por share y evidencia observada post-salida. Importante: no depende del CSV local; usa exclusivamente `trade_lifecycle`/`postmortem` para que la misma lectura exista también en Railway. `verify_before_deploy.py` sube a `478/478`.

**Fix exposición redeemable + truncado seguro en SELL (2 abr, sin bump):** Se corrigen dos bugs operativos que podían bloquear capital aunque la wallet ya tuviera dinero prácticamente liberado. En `get_current_exposure()` las posiciones con `redeemable=True` dejan de contar como exposición aunque `curPrice` aún no haya subido a `0.98+`; esto cubre mercados ya resueltos/canjeables que la API sigue mostrando con valor pero que en práctica son cash garantizado. En paralelo, la construcción de órdenes SELL en `manage_positions()` y en el monitor intra-ciclo deja de usar `round(size, 2)` y pasa a truncar hacia abajo con `math.floor(size * 100) / 100`, evitando rechazos `400 not enough balance / allowance` por pedir más shares de las realmente disponibles. Validación dirigida: el caso real tipo `redeemable=True @ 0.97` deja de consumir exposición, el presupuesto libre sube de `0` a zona operativa en el escenario reproducido, y tamaños como `9.48748` se convierten en `9.48` en vez de `9.49`. `verify_before_deploy.py` se mantiene en verde (`483/483`).

**City accuracy tracker (v10.5.2):** Calcula win rate por ciudad desde postmortem. Alerta por Telegram si una ciudad baja de 25% win rate con 3+ trades. Nuevo comando `/accuracy`. Win rate visible en `/rendimiento`.

**Integración `/accuracy` + revisión crítica (v10.5.3):** `/accuracy` queda visible en el menú, responde siempre con menú, `/estado` muestra explícitamente el intervalo intra-SL y la trazabilidad de sesión 20 queda corregida para reflejar mejor lo que realmente introdujeron los commits de la mañana.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción (último deploy verificado):** Railway — EU West Amsterdam, MODO REAL, DRY_RUN=false (`v10.6.10`, refinamiento semántico del `trade console` validado live el 1 abr 2026 a las `21:00 UTC`). Tras la sesión 61 el repo queda listo para empujar una nueva capa de decisiones por ciudad; la validación live de esta automatización sigue pendiente hasta revisar el siguiente ciclo en Railway.
**Estado actual tras sesión 61:** el repo añade una capa nueva de aprendizaje operacional para ciudades fuera de allowlist sin tocar todavía la estrategia base. `bot.py` ya registra oportunidades `shadow`, construye un `decision engine` por ciudad, expone reglas explícitas `shadow -> canary` y `active/canary -> shadow`, sincroniza un overlay automático persistente (`city_policy_state.json`), muestra `canaries/shadows` automáticos en dashboard y envía alertas Telegram cuando una ciudad cambia de estado. La suite local vuelve a quedar limpia en `496/496`.
**Versión local / remoto GitHub:** la rama local incorpora ya el fix operativo de la sesión 60 y la nueva capa de política automática por ciudad de la sesión 61. Hasta validar Railway, el último deploy confirmado live sigue siendo `5b23d02`; el siguiente push/deploy debe comprobar tanto la salud del ciclo como la nueva observabilidad `shadow/canary`.
**Siguiente paso prioritario (sesión 62 recomendada):** backfill conservador de `shadow` histórico. Objetivo: reconstruir oportunidades pasadas con suficiente trazabilidad para que la tabla decisional no arranque casi vacía, marcando siempre qué evidencia es retroconstruida y cuál viene de ciclos live.
**Bloque posterior recomendado, en sesión separada:** revalidación live del nuevo overlay automático en Railway tras al menos `1-2` ciclos reales y auditoría de `token economics`/disciplina de contexto mínimo solo después de que la capa `shadow/canary` tenga muestra útil.

### Archivos del proyecto:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.6.10 con NOAA hardening, `trade_lifecycle` saneado y nueva capa `shadow/canary` automática para decisiones por ciudad |
| `verify_before_deploy.py` | Suite local de `496` tests de comportamiento |
| `trader_analyzer.py` | Genera `signals.json` diariamente en Volume |
| `find_traders.py` | Descubrimiento semanal de traders y mantenimiento de `traders_db.json` en Volume |
| `CLAUDE.md` | Instrucciones para Claude Code |
| `.codex/config.toml` | Config por proyecto para Codex: `medium` por defecto y perfiles `low/deep/max` para ajustar reasoning effort sin tocar la configuración global |
| `CONTEXTO.md` | Estado del proyecto (este archivo) |
| `OPERATIONS_PLAYBOOK.md` | Protocolo operativo multiagente y checklist de inicio/cierre |
| `HISTORIAL_SESIONES.md` | Bitácora append-only de sesiones e hitos reconstruidos desde Git |
| `OBSERVABILIDAD_Y_APRENDIZAJE.md` | Plan de fases futuras |
| `RESEARCH_CODEX_HANDOFF_2026-03-30.md` | Informe de investigación de Codex para revisión cruzada |
| `RESEARCH_CLAUDE_2026-03-30.md` | Informe de investigación de Claude Code (Opus) |
| `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md` | Síntesis combinada de ambos informes + roadmap |
| `RAILWAY_AUTH_BUG_HANDOFF_2026-04-01.md` | Handoff específico del bug de relogin continuo de Railway; conserva el diagnóstico previo a la reparación cerrada en la sesión 54 |
| `TRADE_LIFECYCLE_INCONSISTENCY_HANDOFF_2026-04-01.md` | Handoff específico de la auditoría de inconsistencias en `trade_lifecycle` y la trade console; lista evidencias verificadas y prompt para la siguiente sesión |
| `SNAPSHOT_ANALITICO_LIVE_2026-04-01.md` | Snapshot humano de la revisión live: salud, exits, casos TP/reeval/SL y anomalías semánticas |
| `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json` | Dump congelado del `/api/dashboard.json` live usado como evidencia del snapshot |
| `templates/dashboard.html` | Plantilla principal del dashboard web |
| `static/dashboard.css` | Estilos del dashboard web |
| `static/dashboard.js` | Interaccion ligera para tabs del Mission HUD |
| `agent_events.jsonl` | Eventos semilla para el scoreboard de agentes |
| `trade_lifecycle.json` | Nueva capa derivada por posición: entrada, snapshots, salida y observación post-exit (se genera automáticamente donde exista histórico) |
| `tools/railway_safe.ps1` | Wrapper Railway que limpia proxies de proceso antes de ejecutar la CLI |
| `tools/railway_auth_repair.ps1` | Helper operativo para `doctor / reset / launch-login / restore-links` de auth Railway |
| `tools/append_agent_event.py` | Helper seguro para añadir eventos al scoreboard sin editar JSONL a mano |
| `signals.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `traders_db.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `requirements.txt` | Dependencias Railway |
| `Procfile` | Arranque Railway |

### Datos persistentes (Railway Volume `/app/data`):
| Archivo | Función |
|---------|---------|
| `performance.json` | 38+ trades (BUY/SELL/LOSS_TOTAL desde 25 mar) |
| `postmortem.json` | Postmortems estructurados de apertura/cierre por mercado |
| `alerts_state.json` | Estado persistente de alertas para evitar avisos duplicados |
| `agent_events.jsonl` | Eventos persistentes del scoreboard de agentes (si existe en Volume) |
| `signals.json` | Señales de traders activas usadas por el bot en producción |
| `traders_db.json` | Base de datos persistente de traders descubiertos/calificados |
| `trader_history.json` | Historial auxiliar del pipeline de traders |
| `cycle_summary.json` | Último ciclo (se sobreescribe) |
| `cycles_history.jsonl` | Historial acumulativo de todos los ciclos |
| `audit.json` | Ventas pendientes + auditoría legacy `forecast vs forecast posterior` + `observed_vs_forecast` NOAA |
| `trade_lifecycle.json` | Trazabilidad completa derivada por posición: buys, exit_attempts, snapshots, mercado post-salida y summary agregado |
| `decisions.log` | Log detallado por ciclo |
| `trades.log` | Log compacto de órdenes |

### Configuración en Railway (variables de entorno):
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"
MIN_BET="1.00"
DATA_DIR="/app/data"
```

### Configuración en código (defaults bot.py v10.6.10):
```python
MIN_EDGE = 7.0%
STOP_LOSS_PCT = -25.0%
TAKE_PROFIT_PCT = +40.0%
MAX_EXPOSURE_PCT = 40%
MIN_BET = $1.00
BLOCKED_CITIES = ["London","Miami","Seattle","Paris","Tel Aviv","Wellington","Toronto","Madrid","Singapore","Ankara"]
BANKROLL_LEVELS = [25, 35, 50, 75, 100]
DASHBOARD_PORT = $PORT
DASHBOARD_REFRESH_SEC = 60
PROMOTION_CITY_COVERAGE_TARGET = 3
INTRA_SL_INTERVAL = 0           # v10.6.0: desactivado (v10.5 usaba 90)
CITY_MIN_TRADES_FOR_BLOCK = 3
CITY_BLOCK_WIN_RATE = 25.0%
LOW_BANKROLL_THRESHOLD = $5.00
LOW_BANKROLL_RESET_MARGIN = $1.00
Sigma: Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0  # v10.6.x: restaurada de v10.3
Schedule: 08:00, 16:00, 23:00 UTC
```

---

## Telegram — Comandos disponibles (v10.6.10)

| Comando | Qué muestra |
|---------|-------------|
| `/focus` | Vista principal de capa 1: salud real, intervención hoy, limitador actual, estado de aprendizaje NOAA y acción recomendada |
| `/estado` | Versión, modo, bankroll, SL/TP, intervalo intra-SL, próximo ciclo, último ciclo y contadores `total`/`serie v10.6` |
| `/cartera` | Cash, posiciones vivas (ciudad+temp+fecha, precios en ¢), resueltas, muertas |
| `/log` | Resumen del último ciclo desde cycle_summary.json |
| `/detalle` | Último ciclo completo del `decisions.log`, paginado y sin corte fijo de 40 líneas |
| `/rendimiento` | Portfolio real + historial trades (TP/SL/reeval, por ciudad con win rate) |
| `/ordenes` | Órdenes GTC pendientes con etiquetas legibles |
| `/traders` | Señales activas + coincidencias filtradas por ciudad, lado y fecha exacta del mercado |
| `/info` | Bloque resumen completo para pegar en Claude/ChatGPT, incluyendo contadores `total`/`serie v10.6` |
| `/postmortem` | Resumen rápido de abiertas/cierres desde `postmortem.json` |
| `/accuracy` | Win rate por ciudad desde postmortem, con iconos de bloqueada/flaggeada y botón visible en el menú |
| `/noaa` / `/observabilidad` | Muestra `sample`, `MAE`, `bias`, cobertura por ciudad activa y últimos casos de `observed_vs_forecast` |
| `/forzar` | Ejecuta ciclo inmediatamente |
| `/modo` | Cambia DRY RUN ↔ REAL |

**Para iniciar una sesión de análisis en claude.ai:** pegar `/info` + `/cartera` + `/rendimiento`.

## Dashboard web (v10.6.10)

- **Ruta principal:** `/`
- **Healthcheck:** `/healthz`
- **API JSON:** `/api/dashboard.json`
- **Autenticación:** básica opcional con `DASHBOARD_USER` y `DASHBOARD_PASSWORD`
- **Objetivo:** separar monitorización visual de Telegram para revisar el sistema en navegador

### Qué muestra
- capa 1 `Mission HUD / Discovery-Stabilization` con mision actual, `System HP`, accion recomendada y respuestas explicitas a salud, intervencion, limitador y aprendizaje
- tabs interactivos `Overview / Progress / Cities` para alternar entre lectura rapida, barras de progreso y carrera NOAA por ciudad sin abandonar la capa 1
- quick stats de universo activo, NOAA interpretable, muestra NOAA y próximo ciclo
- incidents rail con solo alertas activas relevantes
- layering operativa clara: `capa 1` visible primero, `capa 2` como seguimiento/explicación y `capa 3` colapsada para detalle extendido
- nivel actual y siguiente bankroll objetivo
- checklist de promoción `$25 -> $35` separando histórico vs serie `v10.6`
- salud operativa del sistema
- métricas de la serie `v10.6`
- últimos ciclos y posiciones abiertas
- scoreboard de agentes y rivalidad constructiva por stages (`proposed / implemented / validated`)
- modo claro por defecto para lectura y seguimiento prolongado en navegador
- cuando la serie aún no tiene cierres, muestra `n/d` / `sin cierres` en lugar de métricas aparentes
- el checklist distingue visualmente entre `Pendiente` y `Esperando muestra`
- alerta crítica de bankroll bajo cuando la cartera cae bajo `$5`, pero solo con señal fiable (`cash_ok` y sin `api_error`)
- bloque `Progreso` con `faltan X para Y` sobre muestra, estabilidad, cierres útiles, readiness de nivel y cobertura de ciudades
- bloque `Trofeos` con hitos del bot calculados solo desde cierres validados (`mejor operación`, `mayor edge ejecutado`, `ciudad más rentable`, etc.)
- bloque `Desbloqueos` con evidencias/confirmaciones pendientes antes de revisar lógica o evaluar subir bankroll
- bloque `Calidad Forecast Observada (NOAA)` separado del PnL/trading, con `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos de `observed_vs_forecast`
- tabla `Estado de observacion por ciudad`, que cruza allowlist actual, bloqueo, muestra NOAA e histórico validado para distinguir operativa real vs referencia historica vs falta de observabilidad
- bloque legacy `Drift Open-Meteo (historico - no comparable con NOAA)` con `n=` y fecha del último registro para no mezclar la serie nueva con la auditoría vieja

## Hoja de ruta UX operativa

**Fase 1 — Mission HUD (consolidada en v10.6.10):**
- una sola pantalla para decidir si hoy toca actuar o solo seguir recogiendo evidencia;
- capa 1 limitada a salud real, bloqueo dominante, allowlist, NOAA y accion recomendada;
- interaccion ligera con tabs, sin mover el detalle fuera del dashboard.

**Fase 2 — Tendencias de aprendizaje (siguiente iteracion recomendada):**
- series temporales cortas para `sample NOAA por dia`, `coverage activa por ciudad` y `eventos/incidentes por jornada`;
- comparativas visuales para distinguir si estamos aprendiendo mas rapido o solo operando mas;
- mantener esto en `Progress` o capa 2, nunca mezclado con la decision principal.

**Fase 3 — Drill-down operativo:**
- filtros por ciudad/estado (`activa`, `bloqueada`, `solo observacion`, `interpretable`);
- detalle interactivo por ciudad con ultimo caso NOAA, historico validado y razon de estado;
- timeline de checkpoints diarios para sesiones de seguimiento mientras se acumulan datos.

**Regla de diseño:** cualquier nueva visual entra en capa 1 solo si cambia la decision de hoy; si solo explica, vive en capa 2 o capa 3.

---

## BUGS — Estado completo

### Corregidos (v10.3 → v10.4.3):
- **#3** ✅ Duplicados: consulta Data API antes de comprar
- **#4** ✅ Resueltas contaban como exposición
- **#5** ✅ Zona horaria asiática (CITY_UTC_OFFSETS per-city)
- **#6** ✅ signals.json freshness 12h → 26h
- **#7** ✅ SELL_PENDING → SELL en audit
- **#8** ✅ Posiciones micro → LOSS_TOTAL
- **#9** ✅ Re-entrada tras stop-loss mismo ciclo
- **#10** ✅ MIN_BET default 0.50 → 1.00
- **#11** ✅ Ciclo extra al arrancar
- **#12** ✅ Doble conteo resueltas en Telegram
- **#13** ✅ Paginación automática >3800 chars (send_telegram_paged)
- **#14** ✅ Precio límite vs fill clarificado en Telegram

### Pendientes:
- **#15** ✅ **Corregido en v10.6.6:** `ACTIVE_TRADING_CITIES` añade allowlist explícita para entradas nuevas y restringe BUYs a Chicago, Atlanta, Dallas y Buenos Aires. El bug original venía de depender solo de `BLOCKED_CITIES`, lo que dejaba pasar ciudades sin validación NOAA/WU como Seoul, Tokyo, NYC y Munich. La gestión de posiciones existentes (`manage_positions`) no se toca.
- **Observed proxy NOAA / bug de observabilidad detectado:** la auditoría de `31 mar 2026` encontró al menos `7` casos `city|date` elegibles para NOAA en las 4 activas, mientras Railway seguía mostrando `observed_vs_forecast = 0`. No era solo falta de muestra. Causa raíz: `global-hourly` devolvía vacío en varios casos 2026 que sí estaban en `daily-summaries`. Fix local listo: priorizar `daily-summaries/TMAX` para Chicago/Atlanta/Dallas, guardar `observed_dataset`, añadir guard de lag al helper diario y cubrir el fallback `daily -> hourly`; falta desplegar y validar en Railway.
- **Nueva trazabilidad operativa lista para análisis, aún sin poblar localmente con live data:** `trade_lifecycle.json` ya está implementado y validado con tests; medirá contexto de entrada, intentos de salida, snapshots de posición y comportamiento del mercado tras el cierre. El backfill real de la cuenta se generará en el próximo arranque desplegado. No se pudo materializar localmente desde Railway en esta sesión porque el login OAuth del CLI estaba caducado.
- **Saneamiento local de `trade_lifecycle` / trade console (sesión 57, 1 abr 2026):** la auditoría abierta en la sesión 56 ya quedó convertida en cambios concretos de reconciliación/presentación. `build_dashboard_trade_analytics()` vuelve a coalescer records al leer, une duplicados del mismo mercado+lados cuando uno es un follow-up sin BUY (`LOSS_TOTAL`/`RESOLVED_WIN` repetidos), cruza la historia con `portfolio.active/resolved_won/dead`, y crea fallback visible para posiciones recientes presentes solo en cartera. Resultado esperado sobre los casos auditados: `Seoul 14C` deja de verse como historia contradictoria al explicitar el lado; `Seoul 13C` ya no depende de `entry_condition` parcial si la cartera conserva `avgPrice`; `Atlanta 70-71F` y `Dallas 82-83F` condensan `SELL` + residuo micro en una sola narrativa; `Atlanta 78-79F` entra en la tabla aunque solo exista en `portfolio.dead`; `Tokyo 18C` y `Buenos Aires 28C` muestran resolución con `claim` pendiente; `Chicago 40-41F` sigue abierta con lectura coherente de cartera. Sigue sin existir un evento explícito de `REDEEM`, así que la consola habla con honestidad de “claim pendiente / no confirmado” en vez de inventar un cobro.
- **Prioridad siguiente sesión (2 abr 2026):** auditar la captura del `Mission HUD` como fuente de verdad visual de la capa 1. La revisión debe contrastar screenshot, snapshot/dashboard JSON y builders locales para comprobar que las métricas y textos prioritarios no estén arrastrando errores de agregación, buckets equivocados o semántica desalineada.
- **Auditoría de token economics pendiente, en sesión separada:** revisar consumo de contexto/tokens de Codex y Claude Code con reglas explícitas de `1 sesión = 1 tarea`, contexto mínimo y escalado selectivo de reasoning/modelo. No mezclar esta auditoría con la revisión del HUD.
- **Seguimiento de ciudades aún descriptivo:** `v10.6.7` ya muestra por dashboard qué ciudades están activas, bloqueadas, fuera del allowlist o sin observabilidad, pero todavía no existe promoción automática tipo `watchlist / shadow / canary`.
- **Buenos Aires NOAA spike cerrado:** `SAEZ` usa `87576099999`, confirmado con NOAA HOMR y una consulta real al endpoint `global-hourly`.
- **Buenos Aires daily station aún no validada:** el fix local resuelve el cuello de botella principal en US con `daily-summaries`, pero Buenos Aires sigue temporalmente en fallback `global-hourly` hasta encontrar y validar un `daily_station_id` fiable.
- **Fuente real de resolución sigue sin automatizarse:** NOAA mejora mucho la observabilidad, pero sigue siendo `observed proxy`, no la fuente real de settlement de Polymarket.
- **Auditoría legacy sigue limitada aunque honesta:** `forecast_vs_real` sigue existiendo como nombre legacy en `audit.json`, pero los logs/código ya dejan claro que compara `forecast original vs forecast posterior Open-Meteo`, no “real” ni Weather Underground.
- **Weather Underground vs Open-Meteo:** Polymarket resuelve con WU, no Open-Meteo. London sigue bloqueada en código desde `v10.4.7`. IBM Trial no accesible; la vía correcta a corto plazo es alinear resolución, no esperar una API oficial.

---

## Versionado — sistema establecido

- **v10.4.X** = misma lógica de trading, mejoras UI/Telegram/observabilidad
- **v10.5.0** = recalibración de lógica de entrada (sigma, exact filter) — REVERTIDO en v10.6.0
- **v10.5.X** (X>0) = mejoras operativas sin cambiar lógica de entrada
- **v10.6.0** = revert trading logic a v10.3 + toda la observabilidad de v10.5.X
- Ciclos y datos son continuos y acumulativos entre versiones; desde `v10.5.4` se muestra además contador por serie lógica actual
- Cada registro incluye la versión del bot que lo generó

### Historial de versiones:
| Versión | Fecha | Cambios principales |
|---------|-------|-------------------|
| v10.3 | 25 mar | Bugs #4-#8, zona horaria per-city, SELL_PENDING |
| v10.4 | 28 mar | Bugs #3,#9,#10,#11,#12,#14 + persistencia Volume |
| v10.4.1 | 28 mar | cycles_history.jsonl + cycle_summary.json |
| v10.4.2 | 28 mar | Rediseño Telegram + Bug #13 + helpers + /info |
| v10.4.3 | 28 mar | Ciclos persistentes + fixes post-deploy + limpieza repo |
| v10.4.4 | 28 mar | Ajuste temporal manual de DST |
| v10.4.5 | 28 mar | `ZoneInfo` + zonas IANA reales + `.claude/` fuera del repo + `postmortem.json` base + trader data al Volume + `/postmortem` |
| v10.4.6 | 28 mar | backfill automático de `postmortem.json` + `alerts_state.json` + alertas Telegram de observabilidad |
| v10.4.7 | 28 mar | bloqueo operativo de London en código + tests para evitar regresión |
| v10.4.8 | 28 mar | refinamiento Telegram: `traders` por fecha exacta, `postmortem` legacy legible y `detalle` sin corte fijo |
| v10.5.0 | 29 mar | sigma widening (2.0→4.5), MIN_EDGE_EXACT 15%, smart alerts (drawdown/scaling/win rate), 216 tests |
| v10.5.1 | 29 mar | intra-cycle SL/TP monitor cada 90min, threading.Lock, 226 tests |
| v10.5.2 | 29 mar | city accuracy tracker, `/accuracy`, win rate en `/rendimiento`, alertas por ciudad, 234 tests |
| v10.5.3 | 29 mar | `/accuracy` integrado en menú + menú persistente + `/estado` muestra intra-SL + trazabilidad corregida, 242 tests |
| v10.5.4 | 29 mar | contador dual de ciclos (histórico total + serie lógica), `logic_series`/`logic_cycle_number` en historial, `/estado` y `/info` separan total vs serie, 251 tests |
| v10.5.5 | 29 mar | dashboard web HTML separado de Telegram + checklist de bankroll + scoreboard de agentes + `agent_events.jsonl`, 279 tests |
| v10.5.6 | 29 mar | dashboard oscuro + checklist histórico/serie separado + scorecard por stages + ciclos legacy legibles, 290 tests |
| v10.5.7 | 29 mar | dashboard evita métricas falsas sin muestra (`n/d` / `sin cierres`) en serie nueva, 294 tests |
| v10.5.8 | 29 mar | checklist con estado visual neutral `Esperando muestra` para serie sin datos, 300 tests |
| v10.5.9 | 29 mar | dashboard añade `Progreso`, `Trofeos` y `Desbloqueos`, más cobertura de tests funcionales de snapshot y readiness, 325 tests |
| v10.5.10 | 29 mar | dashboard añade `Balance por tipo de cierre` y `Liquidación`, separando TP/SL/Reeval/LOSS_TOTAL/RESOLVED_WIN de `pending_exit` y `pendiente pago`, 334 tests |
| v10.5.11 | 29 mar | fix drawdown checklist + sync agent_events Railway, 337 tests |
| v10.5.12 | 29 mar | bloqueo 10 ciudades 0% WR + fix posiciones fantasma, 338 tests |
| **v10.6.0** | **29 mar** | **revert sigma a v10.3, intra-cycle off, MIN_EDGE_EXACT eliminado. Mantiene toda observabilidad. 335 tests** |
| v10.6.1 | 29 mar | fix drawdown sort, alerta bankroll bajo ($5), unlock redundante eliminado, scoreboard sesión 30. 338 tests |
| v10.6.2 | 29 mar | hardening alerta bankroll: exige `cash_ok` y ausencia de `api_error`, añade `LOW_BANKROLL_RESET_MARGIN`, tests funcionales dashboard/Telegram/reset. 348 tests |
| v10.6.3 | 30 mar | fix Dallas `KDAL`, añade `RESOLUTION_ICAO` con URLs WU, renombra/documenta la pseudo-auditoría como `forecast vs forecast posterior Open-Meteo`, y sube a 358 tests |
| v10.6.4 | 30 mar | añade `observed_vs_forecast` con NOAA NCEI, `noaa_station_id` explícito para las 4 activas, lag de 2 días, tests funcionales NOAA y 371 tests |
| v10.6.5 | 30 mar | dashboard añade bloque `Calidad Forecast Observada (NOAA)` + bloque legacy `Drift Open-Meteo`, separados de performance/trading, y sube a 386 tests |
| **v10.6.6** | **30 mar** | **allowlist `ACTIVE_TRADING_CITIES` — entradas nuevas solo en Chicago/Atlanta/Dallas/Buenos Aires; gestión de posiciones existentes no afectada; suite en 419 tests** |
| **v10.6.7** | **30 mar** | **dashboard añade tabla `Estado de observacion por ciudad`, cruzando allowlist, bloqueo, NOAA e histórico validado para distinguir operativa real vs referencia; suite en 426 tests** |

---

## Trazabilidad por herramienta

**Objetivo:** este proyecto se trabaja con varias herramientas. A partir de ahora, cada sesión debe dejar anotado qué agente hizo qué, qué detectó, y qué corrigió a otro agente si aplica.

### Convención a seguir en futuras sesiones

- **Lectura obligatoria al abrir sesión:** `CONTEXTO.md` + `OPERATIONS_PLAYBOOK.md`
- **ChatGPT / Claude.ai:** análisis, estrategia, revisión de contexto, ideas y validación conceptual.
- **Codex:** cambios de código en local, revisión crítica del repo, corrección de implementaciones previas, validación técnica y tests.
- **Claude Code:** edición/coding en local cuando se use explícitamente para implementar cambios.

### Regla de documentación

- Cada sesión importante debe añadir una nota breve indicando:
- `Herramienta usada`
- `Qué hizo`
- `Qué problemas detectó`
- `Qué corrigió de trabajo previo`
- `Qué quedó pendiente`

### Plantilla fija — Registro de sesión

Usar esta plantilla al cerrar cada sesión relevante:

```md
### Sesión XX — Registro multi-herramienta

- **Fecha:** YYYY-MM-DD
- **Versión activa al cerrar:** v10.X.X
- **Objetivo de la sesión:** ...

- **ChatGPT / Claude.ai:**
  Análisis / estrategia / contexto aportado:
  ...

- **Claude Code:**
  Cambios implementados:
  ...

- **Codex:**
  Revisión crítica / cambios / validaciones:
  ...

- **Problemas detectados en trabajo previo:**
  ...

- **Correcciones aplicadas en esta sesión:**
  ...

- **Tests / verificaciones ejecutadas:**
  ...

- **Pendientes para la próxima sesión:**
  ...

- **Estado final:**
  versión ..., tests ..., deploy sí/no, observaciones ...
```

### Regla práctica de uso

- `CONTEXTO.md` define el estado actual; `OPERATIONS_PLAYBOOK.md` define el protocolo para no desalinear código, docs y scoreboard.
- Si solo participa una herramienta, se rellena solo su bloque y se dejan las demás como `No usado en esta sesión`.
- Si una herramienta corrige o valida trabajo de otra, dejarlo explícito en `Problemas detectados en trabajo previo` y `Correcciones aplicadas en esta sesión`.
- Si hay cambios en Railway, Volume, Telegram o datos históricos, anotarlo también en el bloque `Estado final`.
- Antes de cada push relevante, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md` si la sesión cambió estado, arquitectura, datos persistentes, comandos Telegram, workflow o trazabilidad multi-agente.
- Antes de cerrar una sesión relevante, actualizar también `agent_events.jsonl` usando `tools/append_agent_event.py` o un método equivalente seguro.

### Sesión 20 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.2
- **Objetivo de la sesión:** Completar v10.5.1 (intra-cycle SL) + implementar city accuracy tracker (v10.5.2) + investigar WU API

- **Claude Code (Opus):**
  - Implementó y cerró v10.5.1: intra-cycle SL/TP monitor cada 90min con `sell_lock`, thread daemon y cobertura ampliada hasta 226/226
  - Investigó Weather Underground API: API muerta desde 2019, IBM Trial no viable para Pablo (verificación fallida), opciones: PWS key o accuracy tracker
  - Diseñó e implementó v10.5.2: city accuracy tracker con `get_city_accuracy()`, alertas automáticas por ciudad, comando `/accuracy`, win rate en `/rendimiento` → 234/234 tests
  - Actualizó CONTEXTO.md y HISTORIAL_SESIONES.md

- **Codex:** No usado en esta sesión.
- **ChatGPT / Claude.ai:** No usado en esta sesión.

- **Problemas detectados en trabajo previo:**
  - CONTEXTO.md seguía diciendo v10.4.8, posiciones incorrectas (Dallas/Miami como activas cuando ya habían sido vendidas SL)

- **Lección de gestión de uso:**
  - Sesión consumió mucho uso de Opus. Tareas como investigación WU, escritura de tests, y actualizaciones de docs podrían haberse delegado a Codex para preservar el budget de Opus para decisiones de diseño y coding crítico.

- **Estado final:**
  v10.5.2, 234/234 tests, deploy hecho, v10.5.0+v10.5.1+v10.5.2 en producción, CONTEXTO.md actualizado

### Sesión 21 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.3
- **Objetivo de la sesión:** Revisar críticamente los cambios de la mañana, cerrar huecos de Telegram y corregir la trazabilidad del proyecto

- **Claude Code (Opus):**
  - No usado directamente en esta sesión de revisión

- **Codex:**
  - Revisó commits `v10.5.0`, `v10.5.1` y `v10.5.2` contra Git y código real
  - Detectó que `/accuracy` existía como comando pero no estaba integrado en el menú de Telegram y tampoco volvía con menú
  - Detectó que `/estado` no mostraba el intervalo intra-SL aunque el contexto sí lo documentaba
  - Señaló que la narrativa de sesión 20 decía “solo tests” para `v10.5.1`, pero el commit real había introducido bastante código en `bot.py`
  - Integró `/accuracy` en `MENU_KEYBOARD`, añadió menú persistente y visibilidad del intervalo intra-SL en `/estado`
  - Amplió `verify_before_deploy.py` hasta `242/242` para cubrir estas integraciones
  - Actualizó `CONTEXTO.md` e `HISTORIAL_SESIONES.md` para mantener la memoria del proyecto alineada con Git

- **Problemas detectados en trabajo previo:**
  - `/accuracy` incompleto a nivel UX
  - ligera desalineación docs-código en `/estado`
  - trazabilidad de sesión 20 demasiado simplificada

- **Estado final:**
  v10.5.3, 242/242 tests, repo alineado a nivel código/tests/docs, listo para decidir si hacer deploy

### Sesión 22 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.4
- **Objetivo de la sesión:** Separar el contador histórico de ciclos del contador específico de la nueva lógica `v10.5`

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que `Ciclos: 4` seguía mezclando histórico total con evaluación de la serie `v10.5`
  - Implementó `_load_cycle_counts()` para cargar `total` y `serie lógica` desde `cycles_history.jsonl`
  - Mantuvo `cycle_count` como histórico total para no romper continuidad operativa
  - Añadió `cycle_count_series`, `logic_series` y `logic_cycle_number`
  - Actualizó `/estado` y `/info` para mostrar `total | serie v10.5`
  - Amplió `verify_before_deploy.py` con tests estructurales y funcionales del recuento mixto `v10.4`/`v10.5`
  - Movió los temporales del verificador al directorio temporal del sistema para no ensuciar el repo

- **Problemas detectados en trabajo previo:**
  - El contador acumulativo total era correcto operativamente, pero confuso para analizar la lógica nueva
  - La suite de tests dejaba temporales `_tmp_*` en el workspace de Windows

- **Estado final:**
  v10.5.4, 251/251 tests, histórico total preservado y serie `v10.5` visible por separado en Telegram

### Sesión 23 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.5
- **Objetivo de la sesión:** Crear un dashboard web separado de Telegram para visualizar el sistema, el checklist de bankroll y la rivalidad de agentes

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Diseñó e implementó un dashboard web HTML servido desde el mismo servicio Railway
  - Añadió checklist de promoción de bankroll (`$25 -> $35`) calculado desde métricas reales del sistema
  - Añadió scoreboard de agentes y rivalidad constructiva a partir de `agent_events.jsonl`
  - Creó `templates/dashboard.html` y `static/dashboard.css`
  - Añadió configuración de dashboard (`DASHBOARD_*`, `BANKROLL_LEVELS`) y arranque HTTP en paralelo al bot
  - Amplió `verify_before_deploy.py` hasta `279/279` para cubrir backend, checklist, scorecard y archivos del dashboard

- **Problemas detectados en trabajo previo:**
  - La observabilidad seguía demasiado concentrada en Telegram para revisar sistema, niveles y progreso
  - No existía una métrica estructurada para comparar aportaciones de Opus vs Codex

- **Estado final:**
  v10.5.5, 279/279 tests, dashboard web listo para abrir en navegador, Telegram queda separado de la capa visual principal

### Sesión 24 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.6
- **Objetivo de la sesión:** Refinar el dashboard tras la primera revisión visual para que el checklist mida mejor la serie `v10.5`, el scorecard sea más legible y el panel quede en modo oscuro

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que el checklist del dashboard mezclaba `trades limpios` históricos con métricas de la serie `v10.5`, lo que hacía menos fiable la decisión de subir bankroll
  - Cambió el checklist para separar explícitamente `histórico` vs `serie v10.5`
  - Añadió `get_logic_series_clean_closed_trade_stats()` para medir cierres limpios de la serie lógica actual
  - Refinó el scoreboard de agentes para mostrar estados `proposed / implemented / validated`
  - Hizo que los ciclos legacy se muestren como `legacy v10.X` en vez de `#?`
  - Reordenó las ciudades clave por riesgo operativo en vez de solo por número de trades
  - Rediseñó `static/dashboard.css` a modo oscuro y actualizó la plantilla HTML para reflejar mejor los nuevos estados
  - Amplió `verify_before_deploy.py` hasta `290/290` con checks de dark mode, stages y checklist separado

- **Problemas detectados en trabajo previo:**
  - El dashboard v10.5.5 mezclaba progreso histórico y progreso de la serie nueva en una misma vista de promoción
  - El scorecard seguía siendo útil pero no mostraba todavía la madurez de cada contribución
  - Los ciclos anteriores a `v10.5` se veían ambiguos en la tabla (`#?`)

- **Estado final:**
  v10.5.6, 290/290 tests, dashboard oscuro y más honesto para evaluar la serie `v10.5` sin perder contexto histórico

### Sesión 25 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.7
- **Objetivo de la sesión:** Hacer una pasada rápida de UX para que el dashboard no muestre métricas engañosas cuando la serie `v10.5` aún no tiene cierres

- **Claude Code (Opus):**
  - No usado directamente en esta sesión

- **Codex:**
  - Detectó que `PnL serie`, `Win rate serie` y `Drawdown reciente` seguían mostrándose como `+$0.00` / `0.0%` con `0` cierres, lo que parecía un dato real cuando en realidad faltaba muestra
  - Ajustó el checklist para que `PnL`, `Win rate` y `Drawdown` queden en `sin cierres` hasta que exista información válida
  - Cambió los cards del dashboard para mostrar `n/d` y subtítulos como `Sin cierres todavía` o `Esperando muestra`
  - Amplió `verify_before_deploy.py` con casos funcionales para asegurar que estas métricas no vuelvan a mostrarse como si fueran reales sin haber cierres

- **Problemas detectados en trabajo previo:**
  - El panel era ya coherente en estructura, pero todavía podía inducir a interpretar como “OK” una serie sin muestra

- **Estado final:**
  v10.5.7, 294/294 tests, dashboard semánticamente más claro para analizar una serie nueva sin sobreinterpretar ceros iniciales

### Sesión 26 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.8
- **Objetivo de la sesión:** Último pulido visual del checklist para distinguir entre una condición fallida y una métrica que todavía está esperando muestra

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión

- **Codex:**
  - Añadió un tercer estado al checklist del dashboard: `Esperando muestra`
  - Mantuvo intacta la lógica de promoción, pero separó visualmente `fallo` vs `todavía sin datos`
  - Ajustó la plantilla y los estilos para que ese estado se vea neutro y no rojo
  - Amplió `verify_before_deploy.py` para cubrir `status` y `tag` de los checks cuando no hay cierres en la serie
  - Dejó contexto e historial actualizados para que la siguiente revisión con Claude Code Sonnet tenga trazabilidad clara

- **Problemas detectados en trabajo previo:**
  - Aunque `v10.5.7` ya evitaba métricas engañosas, el checklist seguía pintando esos casos como `Pendiente` rojo, lo que mezclaba falta de muestra con fallo real

- **Estado final:**
  v10.5.8, 300/300 tests, dashboard visualmente más fino y más fácil de interpretar en fases tempranas de una serie nueva

### Sesión 27 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.9
- **Objetivo de la sesión:** Añadir al dashboard una capa más operativa de progreso, trofeos e hitos desbloqueables para saber qué evidencia falta antes de revisar la estrategia o subir bankroll

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión

- **Codex:**
  - Implementó un bloque `Progreso` con muestra pendiente para revisar la serie `v10.5`, estabilidad por ciclos, cierres útiles para activar win rate/drawdown, readiness de subida a `$35` y cobertura de ciudades con muestra suficiente
  - Añadió un bloque `Trofeos` calculado solo desde cierres validados para destacar mejor operación, mejor retorno, mayor edge ejecutado, primera victoria validada, peor operación y ciudades extremas
  - Añadió un bloque `Desbloqueos` para expresar de forma explícita qué confirmaciones faltan antes de confiar en métricas de serie o evaluar decisiones de bankroll
  - Reutilizó `postmortem.json`, `performance.json`, `cycles_history.jsonl` y `alerts_state.json` sin tocar la lógica de trading
  - Amplió `verify_before_deploy.py` hasta `325/325` con tests estructurales y funcionales de snapshot, progreso, trofeos y desbloqueos

- **Problemas detectados en trabajo previo:**
  - El dashboard era ya consistente, pero todavía faltaba una capa más práctica de “faltan X para poder hacer Y”
  - El panel tenía scorecard y checklist, pero no convertía bien la evidencia acumulada en hitos operativos fáciles de interpretar

- **Estado final:**
  v10.5.9, 325/325 tests, dashboard más útil para readiness operativa y más preparado para una revisión global con Claude Code Sonnet

### Sesión 28 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.5.10
- **Objetivo de la sesión:** Hacer medible en el dashboard si el bot corta ganancias demasiado pronto frente a pérdidas demasiado grandes, separando cierres validados, salidas pendientes y cobros pendientes

- **Claude Code (Opus / Sonnet):**
  - No usado directamente en esta sesión; queda como siguiente revisor de toda la iteración reciente del dashboard

- **Codex:**
  - Añadió `build_dashboard_exit_breakdown()` al backend para resumir balance por tipo de cierre usando solo datos ya existentes (`postmortem.json`, serie lógica actual y cartera viva)
  - Separó explícitamente `Take-profit`, `Stop-loss`, `Re-evaluación`, `LOSS_TOTAL`, `Ganadas por resolución`, `Ganadas validadas` y `Perdidas validadas`
  - Añadió una tarjeta de `Liquidación` para distinguir `cierres validados`, `pending_exit`, `abiertas`, `exit_failed` y `pendiente pago / canjear`
  - Dejó claro en el dashboard cuándo el balance ya es validado y cuándo sigue siendo solo estimado por fill pendiente
  - Amplió `verify_before_deploy.py` hasta `334/334` con tests estructurales y funcionales del bloque nuevo, incluyendo `pending_exit` y `canjear`

- **Problemas detectados en trabajo previo:**
  - El dashboard ya explicaba progreso y readiness, pero seguía faltando una vista directa del balance por tipo de salida para responder si el sistema está cortando beneficios antes de tiempo
  - La diferencia entre `vendido en mercado`, `cerrado y auditado` y `pendiente de canjear` no estaba suficientemente visible para interpretación operativa

- **Estado final:**
  v10.5.10, 334/334 tests, dashboard más útil para diagnosticar por qué baja el bankroll y para diferenciar cierres validados de fills/cobros aún pendientes

### Sesión 19 — Registro multi-herramienta

- **Claude Code:** implementó v10.4.2, v10.4.3 y v10.4.4; rediseño Telegram, paginación, `/info`, persistencia de ciclos, limpieza del repo y un fix manual de DST basado en offsets estáticos.
- **Codex:** revisó críticamente esa secuencia y detectó dos deudas importantes: el fix de DST seguía siendo frágil por usar offsets manuales, y `.claude/settings.local.json` había quedado versionado por error.
- **Codex:** corrigió el enfoque de DST en `bot.py` migrando a `ZoneInfo` + `CITY_TIMEZONES` con zonas IANA reales (`v10.4.5`), actualizó `verify_before_deploy.py`, sacó `.claude/settings.local.json` del control de versiones sin borrar la copia local, reparó manualmente una entrada truncada en `performance.json` de Railway, implementó la capa base de `postmortem.json`, movió `signals.json` / `traders_db.json` / `trader_history.json` al flujo persistente de Volume con bootstrap automático, añadió `/postmortem` para inspección rápida desde Telegram, preparó `v10.4.6` con backfill automático de postmortem y alertas de observabilidad persistentes, cerró `v10.4.7` bloqueando London en código para que no vuelva a comprarse por error, y remató `v10.4.8` afinando Telegram para que `traders` cruce por fecha exacta, `postmortem` no degrade etiquetas legacy y `detalle` muestre el último ciclo completo.
- **Estado final de la sesión 19:** versión activa `v10.4.8`, tests `182/182`, repo listo para deploy, DST robusto para futuros cambios de horario, observabilidad base de postmortem lista para crecer, pipeline de traders persistente en Volume, botón visible de `/postmortem`, alertas automáticas listas para avisar cuando haya suficiente muestra para revisar la lógica, London bloqueada operativamente en código y botones de Telegram principales ya refinados tras revisión manual.

### Sesión 31 — Registro multi-herramienta

- **Fecha:** 2026-03-29
- **Versión activa al cerrar:** v10.6.2 (local, pendiente de deploy)
- **Objetivo de la sesión:** Blindar la alerta de bankroll bajo introducida en `v10.6.1`, evitar falsos positivos por fallo de API y dejar código/tests/docs alineados

- **Claude Code (Opus):**
  - No usado directamente en esta sesión
  - El cambio parte de una revisión crítica del trabajo previo firmado con Claude en `v10.6.1`

- **Codex:**
  - Revisó `v10.6.1` y detectó que la alerta de bankroll podía dispararse con `cash=0` por fallo de API aunque la cartera real no hubiera caído
  - Endureció `run_observability_alerts()` y `get_dashboard_alert_summary()` para exigir `cash_ok` y ausencia de `api_error`
  - Añadió `LOW_BANKROLL_RESET_MARGIN = $1.00` para rearmar la alerta al salir de la zona roja sin exigir recuperar hasta `2x` el umbral
  - Amplió `verify_before_deploy.py` hasta `348/348` con casos funcionales de trigger real, no-trigger por API incierta, reset con margen y visibilidad correcta en dashboard
  - Actualizó `agent_events.jsonl`, `CONTEXTO.md` e `HISTORIAL_SESIONES.md` para empaquetar el cambio como `v10.6.2`

- **Problemas detectados en trabajo previo:**
  - La alerta de bankroll bajo de `v10.6.1` mezclaba caída real de fondos con fallos temporales de API
  - El reset de la alerta solo ocurría al superar `LOW_BANKROLL_THRESHOLD * 2`, dejando la alerta demasiado “pegada” y sin rearmarse en recuperaciones parciales razonables

- **Estado final:**
  v10.6.2 local, 348/348 tests, alerta de bankroll más fiable en Telegram/dashboard y repo listo para push/deploy

### Sesión 32 — Investigación estratégica + preparación de v10.6.3

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** v10.6.2 (local + `origin/main`), sin cambio funcional todavía
- **Objetivo de la sesión:** investigar competidores/estrategia, contrastar Codex vs Claude y cerrar el siguiente bloque técnico antes de tocar producción

- **Codex:**
  - Investigó wallets, bots y tooling del ecosistema weather de Polymarket
  - Detectó y documentó que Polymarket usa Weather Underground en múltiples mercados de temperatura
  - Identificó el bug Dallas `KDAL vs KDFW`
  - Preparó `RESEARCH_CODEX_HANDOFF_2026-03-30.md` y la plantilla de comparación con Claude
  - Contrastó después el informe de Claude y creó `RESEARCH_SYNTHESIS_CODEX_CLAUDE_2026-03-30.md`

- **Claude Code (Opus):**
  - Reforzó el hallazgo de Dallas con evidencia adicional
  - Señaló correctamente que la auditoría `forecast_vs_real` actual no valida contra la fuente real de resolución
  - Añadió `Degen Doppler` al mapa competitivo como referencia más directa

- **Conclusión compartida:**
  - `resolution fidelity first`
  - El siguiente bloque correcto no es “más modelo” ni “más ciudades”, sino `v10.6.3`: fix Dallas, capa formal de resolución y honestidad explícita en la auditoría actual

- **Estado final:**
  Repo documentado para arrancar una sesión nueva de implementación con contexto limpio y alcance acotado (`v10.6.3` sin tocar la lógica de trading).

### Sesión 33 — Implementación local de v10.6.3

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.3` local (`origin/main` sigue en `v10.6.2`)
- **Objetivo de la sesión:** ejecutar el bloque técnico acordado tras la investigación: Dallas `KDAL`, capa formal de resolución, honestidad explícita en la pseudo-auditoría y tests.

- **Codex:**
  - Corrigió `RESOLUTION_STATIONS["Dallas"]` de `KDFW`/Fort Worth a `KDAL`/Love Field
  - Añadió `RESOLUTION_ICAO` con `icao + wu_url` para las ciudades activas, las bloqueadas y el resto del mapping actual
  - Renombró la función de auditoría a `audit_check_open_meteo_forecast_drift()` y dejó explícito en docstrings/logs que compara forecast original vs forecast posterior de Open-Meteo
  - Mantuvo la clave legacy `forecast_vs_real` en `audit.json` por compatibilidad, pero dejó de registrar campos/mensajes como si fueran “real”
  - Amplió `verify_before_deploy.py` con checks específicos de Dallas, `RESOLUTION_ICAO`, y mensajes de auditoría sin `real=`
  - Aprovechó para hacer estable un test funcional viejo de `/traders` que dependía de fechas fijas ya pasadas

- **Problemas detectados en trabajo previo:**
  - Dallas seguía apuntando a la estación equivocada para una de las 4 ciudades activas
  - La nomenclatura `forecast_vs_real` inducía a interpretar como observación real algo que seguía viniendo del forecast endpoint de Open-Meteo
  - Faltaba una base declarativa mínima para empezar a alinear resolución sin tocar todavía la lógica de trading

- **Estado final:**
  `v10.6.3` local, `358/358` tests, trading/scheduling intactos y base de resolución más explícita para la siguiente iteración de truth layer.

### Sesión 34 — Implementación local de v10.6.4

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.4` local (`origin/main` sigue en `v10.6.3`)
- **Objetivo de la sesión:** convertir la capa declarativa de resolución en una auditoría observada separada usando NOAA NCEI, sin tocar trading ni scheduling.

- **Codex:**
  - Añadió `noaa_station_id` explícito en `RESOLUTION_ICAO` solo para Chicago, Atlanta, Buenos Aires y Dallas
  - Implementó `fetch_noaa_observed_max()` contra NOAA NCEI Access Data Service usando station IDs ya resueltos, no ICAO dinámico
  - Implementó `audit_check_resolution_truth(dl)` con clave nueva `observed_vs_forecast`
  - Dejó el framing explícito de `observed proxy` con `source="noaa_ncei"` y mantuvo `forecast_vs_real` solo como auditoría legacy Open-Meteo
  - Limitó la auditoría NOAA a las 4 ciudades activas y a fechas con lag mínimo de 2 días
  - Amplió `verify_before_deploy.py` con checks estructurales nuevos y tests funcionales de NOAA

- **Problemas detectados / matices:**
  - NOAA mejora mucho la observabilidad, pero no debe confundirse con la fuente real de settlement de Polymarket
  - Buenos Aires quedó confirmado con `87576099999` tras consultar NOAA HOMR y probar el endpoint `global-hourly`

- **Estado final:**
  `v10.6.4` local, `371/371` tests, observabilidad NOAA añadida como capa separada y trading/scheduling intactos.

### Sesión 35 — Implementación local de v10.6.5

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local (`origin/main` sigue en `v10.6.4`)
- **Objetivo de la sesión:** separar en el dashboard la nueva serie NOAA observada del bloque legacy para poder analizar el forecast sin mezclar fuentes ni romper la continuidad de trading.

- **Codex:**
  - Añadió `build_dashboard_forecast_quality()` para leer `audit.json -> observed_vs_forecast` y exponer `n`, `MAE`, `bias`, cobertura por ciudad activa y últimos 20 casos
  - Añadió `build_dashboard_legacy_forecast_drift()` para mantener visible `forecast_vs_real` como bloque histórico no comparable
  - Integró ambos bloques en `build_dashboard_snapshot()` sin tocar trading, scheduling ni auditorías
  - Actualizó `templates/dashboard.html` para renderizar `Calidad Forecast Observada (NOAA)` y `Drift Open-Meteo (historico - no comparable con NOAA)`
  - Amplió `verify_before_deploy.py` con checks estructurales, thresholds de muestra y tests funcionales del snapshot

- **Problemas detectados / matices:**
  - `observed_vs_forecast` necesita todavía 2+ días de lag y acumulación real para empezar a leer sesgo con muestra útil
  - El bloque legacy sigue siendo útil como histórico, pero queda marcado explícitamente como no comparable con NOAA

- **Estado final:**
  `v10.6.5` local, `386/386` tests, dashboard preparado para observar NOAA vs legacy sin tocar la lógica de trading.

### Sesión 36 — Sync de bankroll tras recarga manual

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local y `origin/main` en `v10.6.5`
- **Objetivo de la sesión:** alinear el fallback local de bankroll con la configuración real de Railway después de una recarga manual de fondos.

- **Codex:**
  - Confirmó que Railway sigue usando `BANKROLL=25.00`
  - Actualizó el fallback de `bot.py` de `$15.00` a `$25.00` para que el entorno local no vuelva a desalinearse de producción
  - Añadió un test en `verify_before_deploy.py` para fijar `BANKROLL default = 25.00`
  - Actualizó `CONTEXTO.md` e `HISTORIAL_SESIONES.md` con la recarga manual `+$14.99` y el sync posterior

- **Problemas detectados / matices:**
  - La inconsistencia no afectaba a producción mientras Railway siguiera inyectando `BANKROLL=25.00`, pero sí podía inducir a errores de lectura o pruebas locales
  - La recarga manual devuelve al bot a la zona de operación prevista para `MIN_BET=$1` y `MAX_EXPOSURE_PCT=40%`

- **Estado final:**
  `v10.6.5` sigue sin bump de versión, pero queda alineado entre código local, tests, contexto y configuración operativa real de Railway.

### Sesión 37 — Playbook operativo + guardrails de scoreboard

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local y `origin/main` en `v10.6.5`
- **Objetivo de la sesión:** convertir el error de desalineación entre docs y scoreboard en una mejora estructural del proceso.

- **Codex:**
  - Creó `OPERATIONS_PLAYBOOK.md` como protocolo específico separado del estado vivo del proyecto
  - Añadió `tools/append_agent_event.py` para registrar eventos del scoreboard sin editar `agent_events.jsonl` a mano
  - Endureció `verify_before_deploy.py` con checks de playbook, helper y consistencia entre la sesión documentada más reciente y `agent_events.jsonl`
  - Dejó `_sync_agent_events_seed()` con warning explícito si falla el merge del scoreboard en arranque
  - Sincronizó el scoreboard live para que sesiones 32-36 queden reflejadas también en Railway

- **Problema detectado:**
  - `CONTEXTO.md` e `HISTORIAL_SESIONES.md` estaban bien, pero el Dashboard seguía leyendo un `agent_events.jsonl` desfasado porque el proceso de cierre de sesión no obligaba a actualizar la capa máquina del scoreboard

- **Guardrails nuevos:**
  - protocolo escrito de inicio/cierre multiagente
  - helper seguro para eventos del scoreboard
  - test que falla si la sesión más reciente en docs no existe también en `agent_events.jsonl`

- **Estado final:**
  el sistema ya no depende solo de memoria manual: estado, historial, scoreboard y tests quedan unidos por un protocolo explícito. `verify_before_deploy.py` queda en `396/396`.

### Sesión 38 — Scoreboard limpio + regla de puntuacion

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local por encima de `origin/main` con hardening adicional del scoreboard
- **Objetivo de la sesión:** corregir la diferencia engañosa del scoreboard y fijar una regla explícita para que revisar sin delta no genere puntos.

- **Codex:**
  - Detectó que el scoreboard live estaba inflado por filas duplicadas y corruptas en `agent_events.jsonl` del Volume
  - Limpió el fichero live en Railway hasta dejarlo otra vez en `29` líneas canónicas
  - Endureció `load_agent_events()` para deduplicar eventos equivalentes por clave normalizada y no volver a inflar el ranking por acentos, símbolos o duplicados manuales
  - Añadió al `OPERATIONS_PLAYBOOK.md` la regla `validacion o aprobacion sin delta = 0 puntos o sin evento`
  - Amplió `verify_before_deploy.py` con un check de esa regla y un test funcional de deduplicación

- **Problema detectado:**
  - El scoreboard no dependía solo del scoring manual; también dependía de la higiene del `agent_events.jsonl` persistente del Volume
  - La vista live usa los últimos `30` eventos válidos; con duplicados de Codex y el límite activo, el panel expulsaba además un evento antiguo de Claude y exageraba la diferencia

- **Estado final:**
  el scoreboard live vuelve a una base limpia, el loader queda robusto frente a duplicados equivalentes y el protocolo ya deja claro que validar sin cambiar nada no debe generar puntos. `verify_before_deploy.py` sube a `397/397`.

### Sesión 39 — Research final Lean Six Sigma + foco NOAA en Telegram

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.5` local lista para deploy, sin bump de versión
- **Objetivo de la sesión:** cerrar la investigación metodológica, traducir solo lo útil al playbook y mover el foco operativo diario hacia `measurement / resolution fidelity`.

- **Codex:**
  - consolidó el research en `RESEARCH_LEAN_SIX_SIGMA_FINAL_2026-03-30.md` con conclusión explícita: `recomiendo no adoptar`, salvo `FMEA-lite` y definiciones operativas mínimas;
  - actualizó `OPERATIONS_PLAYBOOK.md` con:
    - `premortem corto para cambios core`;
    - definición mínima de `fallo real del sistema`, `limitacion conocida` y `ruido de mercado`;
  - amplió `run_observability_alerts()` para enviar hitos NOAA one-shot sobre `observed_vs_forecast`:
    - primer caso global;
    - muestra mínima `>=3`;
    - muestra global útil `>=10`;
    - ciudad con primera muestra;
    - ciudad interpretable `>=3`;
  - añadió `/noaa` y `/observabilidad` en Telegram para leer `sample`, `MAE`, `bias`, cobertura y últimos casos sin abrir el dashboard;
  - mantuvo el menú principal sin poda agresiva tras revisar que el gap real era la falta de una vista específica, no el exceso de botones;
  - endureció `verify_before_deploy.py` con:
    - test de `/noaa`;
    - test de idempotencia de alertas NOAA;
    - check explícito de `state.setdefault("milestones", {})`.

- **Decisión operativa importante:**
  - el cuello de botella actual no es la lógica de trading, sino `measurement / resolution fidelity`;
  - por eso no se tocó `sigma`, `Kelly`, `MIN_EDGE`, exits ni menú principal;
  - el objetivo inmediato pasa a ser observar si NOAA se puebla de verdad en Railway y distinguir mejor `fallo real` vs `limitacion conocida`.

- **Estado final de la sesión:**
  `v10.6.5` queda lista para deploy con foco explícito en fidelity, Telegram ya tiene vista dedicada `/noaa` y la suite sube a `416/416`.

### Sesión 41 — v10.6.6 allowlist ACTIVE_TRADING_CITIES

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.6` local lista para push/deploy
- **Objetivo de la sesión:** corregir el bug #15 para que el bot no vuelva a abrir posiciones nuevas en ciudades sin validación NOAA/WU, manteniendo intacta la gestión de posiciones ya abiertas.

- **Codex:**
  - añadió `ACTIVE_TRADING_CITIES` con default `Chicago,Atlanta,Dallas,Buenos Aires`;
  - insertó un filtro adicional en el scan: si la ciudad no está en el allowlist, no entra en candidatos para BUY;
  - dejó trazabilidad explícita en `decisions.log` con `SKIP {city}: fuera de ACTIVE_TRADING_CITIES`;
  - mantuvo `manage_positions` sin cambios, para no tocar SL/TP/reeval de posiciones ya abiertas;
  - actualizó `verify_before_deploy.py` con checks estructurales del allowlist y alineó el bump de versión a `v10.6.6`;
  - conservó la prueba de idempotencia NOAA ya existente como guardrail activo.

- **Resultado operativo:**
  - el universo de entradas nuevas queda restringido a las 4 ciudades con monitoreo NOAA;
  - el bug de NYC/Munich/Seoul/Tokyo por blacklist incompleta queda corregido;
  - la suite sube a `419/419`.

### Sesión 42 — v10.6.7 dashboard estado por ciudad

- **Fecha:** 2026-03-30
- **Versión activa al cerrar:** `v10.6.7` local validada, pendiente de push/deploy
- **Objetivo de la sesión:** hacer visible en el dashboard, sin tocar la lógica de trading, en qué estado está cada ciudad desde el punto de vista de operativa real, cobertura NOAA y evidencia histórica.

- **Codex:**
  - añadió `build_dashboard_city_observation()` para cruzar `ACTIVE_TRADING_CITIES`, `BLOCKED_CITIES`, `observed_vs_forecast` y `get_city_accuracy()`;
  - incorporó el bloque nuevo al snapshot del dashboard sin mezclarlo con el builder NOAA puro;
  - sustituyó la lista simple de cobertura por una tabla `Estado de observacion por ciudad` con columnas de `Trading`, `NOAA`, `Historico` y `Estado actual`;
  - dejó la tabla deliberadamente descriptiva: muestra `Activa`, `Bloqueada`, `Fuera allowlist`, `Operando con observabilidad`, `Referencia historica` o `Sin observabilidad`, pero no promociona ciudades automáticamente;
  - endureció `verify_before_deploy.py` con:
    - check estructural del builder nuevo;
    - check del bloque nuevo en `dashboard.html`;
    - test funcional de la tabla para `Chicago`, `London` y `New York City`;
    - test de snapshot para asegurar que `city_observation` llega al dashboard;
  - subió la versión a `v10.6.7`.

- **Resultado operativo:**
  - el dashboard ya permite ver de un vistazo qué ciudades están realmente operando, cuáles siguen bloqueadas, cuáles solo tienen valor histórico y cuáles siguen sin observabilidad;
  - esto no desbloquea ciudades ni cambia BUY/SELL, pero prepara mejor la decisión futura sobre `watchlist / shadow / canary`;
  - la suite sube a `426/426`.

---

## Historial de trades (33 entradas en performance.json)

| # | Ciudad | Lado | Coste | Resultado | PnL | Motivo | Fecha |
|---|--------|------|-------|-----------|-----|--------|-------|
| 1 | Chicago | YES | $2.38 | $7.72 | +$3.96 | Take-profit +85% | 25 mar |
| 2 | Ankara | YES | $2.50 | $0 | -$1.90 | LOSS_TOTAL | 26 mar |
| 3 | Atlanta | YES | $4.04 | $6.71 | +$2.60 | Take-profit +63% | 27 mar |
| 4 | London | NO | $2.50 | ~$0.22 | -$2.25 | Pérdida (WU vs OMA) | 26 mar |
| 5 | Ankara | NO | $2.50 | $4.24 | +$1.74 | WIN resolución | 26 mar |
| 6 | Chicago | YES | $2.50 | $11.59 | +$9.98 | WIN resolución +619% | 26 mar |
| 7 | Miami | YES | $2.20 | $0 | -$2.14 | LOSS_TOTAL | 26 mar |
| 8 | Shanghai | NO | $1.43 | $2.52 | +$1.09 | WIN resolución | 27 mar |
| 9 | Seattle | YES | $2.50 | $0.96 | -$0.42 | Stop-loss | 28 mar |
| 10 | Wellington | NO | $2.26 | $4.48 | +$2.24 | WIN resolución | 28 mar |
| 11 | Toronto | NO | $1.68 | $0 | -$1.71 | LOSS_TOTAL | 27 mar |
| 12 | Madrid | YES | $4.89 | $2.36 | -$1.95 | Stop-loss (bug #3) | 28 mar |
| 13 | Buenos Aires | NO | $1.62 | $2.21 | +$0.80 | Take-profit +52% | 28 mar |
| 14 | Dallas | YES | $2.50 | $2.44 | +$0.26 | Re-evaluación | 28 mar |
| — | Tel Aviv | NO | $2.46 | $0 | -$2.46 | LOSS_TOTAL | 28 mar |
| — | Paris | NO | $0.58 | $0 | -$0.58 | LOSS_TOTAL | 28 mar |
| — | Miami | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Chicago | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Dallas | YES | $2.50 | abierta | — | En cartera | 28 mar |

---

## Ciclos ejecutados

| Ciclo | Hora UTC | Compras | Ventas | Nota |
|-------|----------|---------|--------|------|
| Extra | 25 mar 16:49 | Chicago YES | — | Bug #11 — deploy entre ciclos |
| 2 | 25 mar 23:00 | — | Chicago YES TP +85% | OK |
| 3 | 26 mar 08:00 | Ankara YES/NO, London NO, Atlanta YES | — | OK |
| 4 | 26 mar 16:00 | Chicago YES, Atlanta YES, Miami YES, Shanghai NO | — | OK |
| 5 | 26 mar 23:00 | Seattle YES, Buenos Aires NO | — | OK |
| 6 | 27 mar 08:00 | — | Atlanta YES TP +63% | OK |
| 7 | 27 mar 16:00 | Madrid YES, Chicago YES 40-41°F, Toronto NO | — | OK |
| 8 | 27 mar 23:00 | Madrid YES (BUG #3), Wellington NO | Seattle YES SL | Madrid amplificada |
| 9 | 28 mar 08:00 | Dallas YES, Miami YES | Madrid YES SL, Buenos Aires TP | OK |
| 10 | 28 mar ~11:01 | Miami YES | — | Deploy v10.4 — Bug #3 bloqueó duplicados ✅ |
| 11 | 28 mar 16:00 | Chicago YES, Dallas YES | Dallas reeval, Tel Aviv/Paris LOSS_TOTAL | v10.4.2 |
| 12+ | 28 mar 23:00+ | — | — | v10.4.3 activo, cycles_history.jsonl acumula |

---

## Observaciones estratégicas

### Open-Meteo vs Weather Underground
London ha producido pérdidas seguidas porque Open-Meteo predice una temperatura y Weather Underground (fuente real de Polymarket) resuelve con otra. **No apostar en London hasta resolver.** Desde `v10.4.7`, London está bloqueada en el código del bot.

### Lógica de salida — casos reales
Con ~15 trades cerrados no hay suficiente evidencia estadística para cambiar la lógica. La solución correcta es un monitor ligero intra-ciclo (Fase 2, cuando haya 30+ trades limpios). Desde `v10.4.6`, Telegram avisará automáticamente cuando se alcance ese umbral para abrir una sesión de análisis/coding con Opus.

---

## Arquitectura de observabilidad — fases

### Fase 1 — ✅ Implementada:
- Persistencia Railway Volume, cycles_history.jsonl, cycle_summary.json ✅
- Bugs #3-#14 corregidos, 173 tests ✅
- Claude Code instalado y funcional ✅

### Fase 1.5 — ✅ Implementada (sesión 19):
- Rediseño completo Telegram (7 botones + /info) ✅
- Bug #13 paginación ✅
- Ciclos persistentes entre deploys ✅
- Limpieza del repo (17 archivos eliminados) ✅
- performance.json fusionado con historial completo (33 trades) ✅
- DST robusto con `ZoneInfo` y zonas IANA reales ✅
- `postmortem.json` base implementado ✅
- `signals.json`, `traders_db.json` y `trader_history.json` persistidos en Volume ✅
- `/postmortem` disponible para inspección rápida desde Telegram ✅
- backfill automático de `postmortem.json` desde `performance.json` ✅
- `alerts_state.json` + alertas Telegram de observabilidad ✅
- London bloqueada operativamente en código ✅
- Refinamiento Telegram tras revisión manual de botones (`/traders`, `/postmortem`, `/detalle`) ✅

### Fase 2 — ✅ Implementada (sesión 20):
- Monitor intra-ciclo SL/TP cada 90min (v10.5.1) ✅
- City accuracy tracker con alertas automáticas (v10.5.2) ✅
- Sigma recalibrada tras análisis de 17 trades cerrados (v10.5.0) ✅
- Smart alerts: drawdown, scaling readiness, win rate (v10.5.0) ✅

### Fase 2.5 — Próxima:
- Resolver acceso a Weather Underground API (IBM Trial falló, buscar alternativas)
- Ampliar `postmortem.json` con análisis más rico al resolver cada mercado

### Fase 3 — Cuando escale:
- Dashboard web (Streamlit o HTML estático)

---

## Infraestructura

### Railway:
- **Región:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403)
- **Volume:** Montado en `/app/data` — archivos persisten entre deploys
- **Variable DATA_DIR:** `/app/data`

### Acceso SSH:
```bash
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "comando"
powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 ssh "ls -l /app/data"
```

### Higiene Railway CLI:
- Usar `tools/railway_safe.ps1` para `status`, `logs`, `ssh`, `domain` y lecturas del Volume.
- Si Railway entra en bucle de relogin o pierde el enlace del proyecto, usar `tools/railway_auth_repair.ps1 doctor`, luego `reset`, después `launch-login -Browserless` y, si el login deja `projects = {}`, rematar con `restore-links`.
- Hacer `railway login` solo en una shell interactiva del usuario.
- Validación mínima del 1 de abril de 2026: `whoami`, `status` y `logs -s polymarket-bot -n 20` ya responden otra vez vía wrapper.
- Si Codex necesita ejecutar Railway despues del login y la CLI puede refrescar auth, usar permisos fuera del sandbox para que pueda tocar `%USERPROFILE%\.railway\config.json`.

### Claude Code:
- Instalado en `C:\Projects\polymarket-bot`
- Para tests: `$env:PYTHONIOENCODING="utf-8"` antes de ejecutar

### Trabajo multi-agente:
- `CONTEXTO.md` debe mantenerse como foto actual compartida entre ChatGPT, Codex, Claude.ai y Claude Code.
- `HISTORIAL_SESIONES.md` debe usarse como memoria histórica append-only para no perder qué sesiones ya existieron y qué se corrigió en cada etapa.
- Antes de cada push relevante, actualizar ambos archivos si cambió algo material del sistema.
- Antes de cerrar una sesión relevante, anotar qué herramienta hizo los cambios finales y qué corrigió de sesiones previas.

### Workflow de deploy:
```bash
python verify_before_deploy.py   # todos los tests deben pasar
# actualizar CONTEXTO.md si cambió el estado actual
# actualizar HISTORIAL_SESIONES.md si hubo una sesión/hito nuevo
git add .
git commit -m "v10.X.X: descripción"
git push
# Railway despliega automáticamente
# Verificar variables: DATA_DIR, MIN_BET, DRY_RUN
```

---

## Ideas pendientes (no implementar hasta validar)

1. ~~**Monitor ligero intra-ciclo:**~~ ✅ Implementado en v10.5.1
2. **Weather Underground:** IBM Trial no accesible. Opciones: PWS key ($30-50 estación), scraping (frágil), o seguir con accuracy tracker
3. **Dashboard web:** Fase 3 cuando haya 50+ trades
4. **Enriquecer `/postmortem`:** filtros por ciudad/estado/últimos N cierres
5. **Ampliar `postmortem.json`** con más campos de forecast y comparación resolución vs decisión
6. **Aumentar frecuencia ciclos:** [8,16,23] → [6,10,14,18,22]
