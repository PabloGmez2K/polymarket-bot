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
| 2026-04-21 | Explícita | Sesión 214 | City Intelligence runtime transport auth-blocked | Auditoría operativa del aviso diario `City Intelligence` sin tocar `bot.py`, `city_policy_state.json` runtime, NOAA, scheduler ni policy live. Se valida que el fail-closed es correcto: mientras no haya runtime fresco, no se puede interpretar `edge_evidence=0` como ausencia real de edge ni emitir recomendaciones por ciudad. El snapshot local `data/runtime_import/` está completo y bijectivo con `runtime_import_manifest.json` (`12/12`, sin missing/extra/byte mismatch), pero stale: `pulled_at=2026-04-18T09:28:57Z`, ~75.3h frente al SLO 24h. El pull read-only con `tools/railway_runtime_snapshot_pull.ps1` no llega a leer live porque Railway CLI falla con `invalid_grant`; `railway_auth_repair.ps1 doctor` confirma CLI 4.35.0, sin proxies, config writable, 1 proyecto linkeado, access/refresh tokens presentes pero expirados/invalidos (`tokenExpiresAtUtc=2026-04-20T21:54:37Z`). `city_validation_ledger.py` marca `runtime_inputs_status=stale`; `system_alignment_check.py --decision-mode operational` falla por `runtime_manifest` stale y `runtime_policy_effective_view` stale. Siguiente acción: re-login Railway y repetir pull read-only, luego regenerar effective view, ledger/gate y alignment check antes de volver a permitir recomendaciones por ciudad. |
| 2026-04-21 | Explícita | Sesión 212 | daily traders-vs-bot readout, no code | Se registra el parte diario `traders vs bot` / `blocked signals` como actualización de trazabilidad, sin tocar `bot.py`, whitelist, NOAA, scheduler ni trading core. Foto UTC 2026-04-21: `MATCH=16`, `BOT_ONLY=5`, `TRADER_ONLY=19`; serie reciente de 7 corridas con medianas `MATCH=16`, `BOT_ONLY=3`, `TRADER_ONLY=25`. Lectura: el gap traders-vs-bot se está cerrando respecto al inicio de la serie y hoy no hay gap operativo fuerte fuera de `blocked` con consenso y condición operable. Persisten en `TRADER_ONLY` `7/7`: `Ankara`, `Busan`, `Houston`, `Jakarta`, `Miami`; casi persistentes `6/7`: `Amsterdam`, `Buenos Aires`, `Chengdu`, `Helsinki`, `Kuala Lumpur`, `Los Angeles`. `Blocked signals` fuera de whitelist: 117 resueltas, 114 wins, WR 97.4%, 148 señales excluidas por whitelist. Instrucción fijada: si este bloque persistente sigue estable varios días, revisar primero `QUALITY_TRADER_CITIES_WHITELIST` y cobertura observada/NOAA antes de tocar reglas de entrada o trading core. |
| 2026-04-21 | Explícita | Sesión 211 | cierre Windows/WSL + hardening local de validación | Se reconstruye el contexto tras un reinicio forzado por la instalación de WSL y se cierra el frente operativo de “permisos Windows” sin tocar `bot.py` ni lógica core. La sesión deja fijado que el problema no era una ACL persistente del repo, sino fricción del entorno local: sandbox/proxies inyectados por Codex en Windows más roces de temporales/artefactos Python bajo locks de Windows. Para endurecer las validaciones locales, `verify_before_deploy.py` pasa a usar `.tmp_verify/` dentro del repo en lugar de `tempfile.gettempdir()`, y se añade `tools/check_python_syntax.py` para validar sintaxis sin generar `.pyc` ni depender de `__pycache__`. En paralelo, WSL2 con Ubuntu queda instalado y validado como entorno limpio de escape: el repo abre desde `/mnt/c/Projects/polymarket-bot`, `git` se sanea con `safe.directory`, `python3` queda operativo y tanto una petición directa con `User-Agent` como `python3 tools/polymarket_api_probe.py` devuelven `200`. Cierre clave de la sesión: Codex ya puede ejecutar Ubuntu directamente con `wsl -d Ubuntu bash -lc "..."`, futuras verificaciones en WSL ya no requieren que Pablo las pegue a mano y `python verify_before_deploy.py` vuelve a cerrar en **746/746**. |
| 2026-04-19 | Explícita | Sesión 210 | observability patch for `condition_filtered` canary logs | Se cierra una auditoría corta nacida de la revisión del `decisions.log` live de Apr 18, donde varias ciudades `canary` (`Shanghai`, `New York City`, `Atlanta`, `Munich`) seguían apareciendo en texto como `SHADOW-FILTER` dentro del carve-out `exact/range`. La revisión sobre `skip_log.jsonl`, `city_policy_state.json`, `policy_env_snapshot.json` y `signals.json` demuestra que no había bug de reconocimiento de modo: las filas afectadas ya salían con `city_mode="canary"` y `allowlisted=true`; el filtro se disparaba porque faltaba `match_key` en `trader_signals`, no porque la ciudad hubiese vuelto a `shadow`. Para cortar esa ambigüedad se parchea `bot.py`: el log detallado ahora emite `CANARY-FILTER` cuando la ciudad es `active/canary`, mantiene `SHADOW-FILTER` para ciudades realmente fuera de allowlist y añade al `skip_log` la causa estructurada del gate (`exact_range_gate_reason`) más el `qt_match_key` evaluado. No se tocan trading core, NOAA, scheduler, sizing ni policy live. Validación de cierre: `python verify_before_deploy.py` antes de commit/push. |
| 2026-04-19 | Explícita | Sesión 208 | auditoría read-only `price_out_of_range` por ciudad canary | Se revisa `data/runtime_import/skip_log.jsonl` sin tocar `bot.py`, NOAA, scheduler, policy live ni el filtro `[0.20,0.80]`, para responder si el 53% global de skips por `price_out_of_range` esconde canaries prácticamente inoperables. El snapshot live usado fue pullado de Railway el `2026-04-18T09:28:57Z`. Comparando histórico completo (`79` ciclos / `19,267` skips) contra la ventana reciente de `30` ciclos (`2026-04-14T09:41` → `2026-04-18T09:27`), el hallazgo central es que sí hay concentración fuerte por ciudad: `Seoul`, `Tokyo` y `Shanghai` quedan muy dominadas por `price_out_of_range` en la ventana reciente (`84-87%` de sus skips), `London` / `New York City` / `Munich` muestran presión relevante pero menos extrema, y `Atlanta` no parece una canary estructuralmente atrapada por precio. El patrón es casi enteramente de mercados `<0.20`, no de un choque amplio con `>0.80`. Decisión cerrada de la sesión: no cambiar el filtro global `[0.20,0.80]`, no degradar canaries solo por este readout y reencuadrar el frente como un subcaso de low-price concentration. Se deja priorizado `Seoul/Tokyo/Shanghai` como canary con cuello dominante de precio bajo; `Atlanta` sale de prioridad inmediata y `London/NYC/Munich` quedan en zona intermedia. Si el tema se reabre, el siguiente bloque honesto será una micro-auditoría por ciudad del bucket `<0.20` con ventana fresca post-`v10.6.23`. Artefacto: `docs/price-out-of-range-canary-audit-2026-04-19.md`. |
| 2026-04-19 | Explícita | Sesión 206 | local exact/range canary min amount floor | Se ataca un cuello pequeño pero real de `position management` tras cerrar los frentes mayores de throughput del 17-19 de abril. El diagnóstico de sesión confirma que el supuesto pendiente `QUALITY_TRADER_CITIES_WHITELIST +Jakarta,Kuala Lumpur` ya no era real: Railway production ya incluye ambas ciudades, así que el siguiente cuello honesto es `micro_position_unsellable`. Se parchea `bot.py` con un guardrail reversible y acotado al carve-out `exact/range canary`: nueva env `EXACT_RANGE_MIN_AMOUNT=2.50` y helper `_resize_position_amount()`; después del escalado `canary` + `EXACT_RANGE_SIZE_SCALE`, si la posición queda por debajo del mínimo operativo se recompone hasta ese suelo, respetando el cap de `MAX_BET_PCT`. El objetivo es evitar que la excepción `exact/range canary` siga produciendo entradas microscópicas con mala salibilidad, sin tocar el pipeline general ni NOAA/scheduler. Validación local cerrada: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` **730/730**. |
| 2026-04-19 | Explícita | Sesión 205 | Railway cleanup of `signals-crosscheck` | Se elimina de Railway el servicio vacío `signals-crosscheck` que había quedado como residuo de la activación inicial. Hallazgo operativo útil: la CLI pública no ofrece borrado de servicios, así que la limpieza se ejecuta por API GraphQL (`serviceDelete`) con el `serviceId` exacto del servicio huérfano y `environmentId=production`. Verificación posterior: `service status -a` vuelve a mostrar solo `polymarket-bot`, `city-intelligence` y `phase5-visibility`, todos en `SUCCESS`. La sesión también deja cerrada la lectura estratégica del cambio: el summary diario `traders vs bot` no añade edge por sí mismo, pero sí acelera el ciclo evidencia→decisión sobre ciudades TRADER_ONLY persistentes, reduciendo trabajo manual y haciendo más rápida la reasignación de atención/capital hacia gaps operativos reales. |
| 2026-04-19 | Explícita | Sesión 204 | live activation on polymarket-bot | Se activa en producción el summary temporal `traders vs bot` y se cierra el loop diario sin trabajo manual. Durante la activación se confirma un guardrail relevante de Railway: `polymarket-bot-volume` no puede montarse en un segundo servicio mientras siga adjunto al bot, así que el servicio nuevo `signals-crosscheck` no sirve como reader live sin desmontar producción. Se toma la vía segura: `bot.py` pasa a invocar `tools/signals_crosscheck_daily_summary.py` justo después de `maybe_run_daily_crosscheck(state)`, reutilizando el mismo `/app/data/signals_crosscheck.jsonl` del bot. Validación local previa: `python -m py_compile bot.py` OK y `python verify_before_deploy.py` 727/727. Deploy live realizado sobre `polymarket-bot` (`deployment 58683196-662f-4647-843a-4e9f84b8d02f`, `SUCCESS`), con arranque nuevo visible a `2026-04-19 10:10:41 UTC`. Verificación final por `railway ssh`: el summary escribe `/app/data/signals_crosscheck_daily_summary_state.json`, genera `/app/docs/signals_crosscheck_daily_summary_latest.md` y envía Telegram real (`sent=true`), reportando 7 corridas recientes y `gap_state=estructural`, con 8 ciudades TRADER_ONLY persistentes en 7/7. |
| 2026-04-19 | Explícita | Sesión 203 | local cross-check traders vs bot automation | Se automatiza la capa humana del cross-check `traders vs bot` sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. `tools/signals_vs_edge_crosscheck.py` queda refactorizado para exponer helpers reutilizables (`build_crosscheck_record`, `append_record`) y aceptar output path configurable, manteniendo el modo standalone; además su validación deja de asumir que Austin siempre aparece en el snapshot y solo exige esa comprobación cuando la ciudad está presente en `signals.json`. Encima se crea `tools/signals_crosscheck_daily_summary.py`, que lee `data/signals_crosscheck.jsonl` con fallback a `data/runtime_import_derived/signals_crosscheck.jsonl`, deduplica por fecha UTC, puede ingerir la corrida del día si falta, resume la serie reciente (medianas MATCH/BOT_ONLY/TRADER_ONLY, ciudades TRADER_ONLY persistentes y gap operativo del día), envía Telegram con anti-spam por `last_sent_date` y guarda estado propio. Se añade `tools/signals_crosscheck_railway_service.py` para ejecutar ese summary una vez al día en Railway y `docs/signals-crosscheck-railway-service.md` con el comando/vars recomendadas. `.gitignore` pasa a cubrir `data/signals_crosscheck.jsonl` y `data/signals_crosscheck_daily_summary_state.json`. Validación local: `python tools/signals_vs_edge_crosscheck.py --no-append`, `python tools/signals_crosscheck_daily_summary.py --crosscheck-file data/runtime_import_derived/signals_crosscheck.jsonl --dry-run` y `python tools/signals_crosscheck_railway_service.py --once` OK. |
| 2026-04-19 | Explícita | Sesión 202 | local city-intelligence alerts hardening + lock diagnosis | Cierre corto centrado en tooling humano de `city intelligence`, sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. Se endurece `tools/city_intelligence_telegram_alert.py` para que solo dispare sobre gates accionables (`now/soon` + allowlist explícita), evitando que ciudades ya degradadas a `background_watch` como Dallas vuelvan a saltar como foco falso; validación local `--dry-run`: `should_alert=false`. En paralelo, `tools/city_intelligence_daily_summary.py` deja de mezclar filas del ledger con instrucciones de otra ciudad del gate y añade anti-spam por `last_sent_date`, de modo que el resumen diario no vuelva a dispararse dos veces el mismo día UTC y no vuelva a listar unas ciudades mientras manda revisar otra distinta. Hallazgo operativo adicional documentado: el problema de “permisos” al borrar `.tmp_*` o compilar tools con `py_compile` no era ACL NTFS sino handles abiertos por `Code.exe`/`codex`; escribir en `tools/__pycache__` funciona, pero borrar/renombrar falla mientras VS Code reabre el workspace. |
| 2026-04-19 | Explícita | Sesión 201 | v10.6.22 — Jakarta + Kuala Lumpur (ICAO-only) | Cierre del handoff `docs/handoff-noaa-jakarta-kuala-lumpur.md`: se agregan Jakarta y Kuala Lumpur a `RESOLUTION_STATIONS`, `RESOLUTION_ICAO`, `CITY_TIMEZONES`, `OBSERVED_AUDIT_CITIES` y al default de `QUALITY_TRADER_CITIES_WHITELIST` en `bot.py`. **Verificación de fuente Polymarket (WebFetch):** Jakarta resuelve contra **Halim Perdanakusuma (WIHH)** — NO Soekarno-Hatta (WIII) como sugería el handoff inicial — vía WU `https://www.wunderground.com/history/daily/id/jakarta/WIHH`; Kuala Lumpur resuelve contra **KLIA (WMKK)** vía WU `https://www.wunderground.com/history/daily/my/sepang-district/WMKK`. **Verificación NOAA (isd-history + ghcnd-inventory + ghcnd yearly 2026):** WIHH USAF 967495 → ISD `96749599999` existe pero no hay CSV global-hourly 2026; GHCND diario más cercano es `ID000096745` (Jakarta/Observatory) e `IDM00096741` (Tanjung Priok) — ninguno aporta TMAX en el yearly 2026. WMKK USAF 486500 → ISD `48650099999` sin CSV global-hourly 2026; GHCND diario `MYM00048650` existe pero sin TMAX reportado en 2026. Conclusión operativa: ambas ciudades entran en configuración **ICAO-only** (patrón Singapore/Toronto/Warsaw) — el bot podrá tradear vía WU pero los trades no llevarán `source: noaa_ncei` y no contarán en WR verificado hasta que NOAA retome el feed para SE Asia. Coordenadas: Jakarta `(-6.2666, 106.8906)`, KL `(2.7456, 101.7099)`. `verify_before_deploy.py`: 9 tests nuevos, pasa **727/727** (incluye traza de esta sesión en `agent_events.jsonl`). Pendiente Pablo: actualizar Railway env `QUALITY_TRADER_CITIES_WHITELIST` agregando `Jakarta,Kuala Lumpur`. |
| 2026-04-19 | Explícita | Sesión 200 | `5b880d6` — whitelist +6 ciudades permanentes TRADER_ONLY | Análisis de la serie temporal completa de cross-check traders vs bot (7 corridas automáticas del bot en Railway, Apr 13-19) y expansión del `QUALITY_TRADER_CITIES_WHITELIST`. Hallazgos clave: 8 ciudades son permanentemente TRADER_ONLY en 7/7 corridas (Ankara, Houston, Jakarta, Kuala Lumpur, Madrid, Miami, Paris, Wellington) y 15 ciudades más con 6/7. El ratio MATCH/TRADER_ONLY no converge — el gap estructural se mantiene en ~25 ciudades con mediana estable; Apr 16 fue outlier (15 TRADER_ONLY) por baja cobertura trader ese día. Austin y Toronto aparecen 6/7 (1 ausencia cada una). Las 7 corridas viven en Railway `/app/data/signals_crosscheck.jsonl`; el archivo local solo tiene corridas manuales. **v10.6.21:** se agregan Ankara, Madrid, Miami, Paris, Wellington, Houston al whitelist. Houston también añadida a `RESOLUTION_STATIONS` (KIAH, lat 29.9902 lon -95.3368) y `RESOLUTION_ICAO` (KIAH sin `noaa_station_id`, pendiente verificación vs Polymarket resolution source). Se actualiza el default en `os.getenv("QUALITY_TRADER_CITIES_WHITELIST", ...)` en `bot.py` y la env var en Railway. Jakarta y Kuala Lumpur quedan pendientes por falta de NOAA verificado — handoff `docs/handoff-noaa-jakarta-kuala-lumpur.md` creado. `verify_before_deploy.py` pasa 718/718. |
| 2026-04-19 | Explícita | Sesión 199 | `e8b236c` + `71ca261` + Railway env SCHEDULE_HOURS_UTC=4,8,12,16 | Paquete de throughput v10.6.20 sin tocar trading core, NOAA, scheduler ni policy live. Motivación: Pablo quiere acelerar bankroll $25→$50 con evidencia acumulada (quality traders WR=76.3% n=59 en exact/range, 21 ciudades TRADER_ONLY sin observación bot, slot 16-04 UTC dormido 12h). Cambios en `bot.py` → `v10.6.20`: (1) **P1 ciudades invisibles**: `Lucknow` y `Sao Paulo` añadidas a `OBSERVED_AUDIT_CITIES` (ambas con NOAA coords ya presentes desde handoff C sesión 169); `Istanbul` diferida por falta de `RESOLUTION_STATIONS`/`RESOLUTION_ICAO` (riesgo Seoul mismatch sesión 185). (2) **P4-P5 alerta one-shot** `maybe_alert_p4_p5_expansion(state)` FIRE_DATE=2026-04-22: prompt Codex para expandir `QUALITY_TRADER_CITIES_WHITELIST` post-checkpoint día 7. (3) **P6-P7 alerta one-shot** `maybe_alert_p6_p7_post_v2_cleanup(state)` FIRE_DATE=2026-04-25: prompt Codex para reset `shadow_city_tracking` Seoul legacy pre-fix + análisis MIN_EDGE por ciudad. Ambas siguen patrón `maybe_run_w17_observation_alert` (date-triggered, state flag one-shot, anti-spam daily) e integradas en `run_observability_alerts()`. **Fix adicional anti-flapping shadow↔canary (NYC):** Pablo observa loop donde NYC se degrada canary→shadow por `verified_history_bad` (NOAA-verificado 2/25 trades, WR 8%, PnL -$0.24) y se re-promociona shadow→canary por `promotable_shadow` (11 edges, 64 ciclos, pico 50.5%) en el mismo ciclo. Causa raíz: los dos gates eran independientes — degradación usa `verified_history_bad`, promoción lo ignoraba. Fix: reordenar cálculo (`verified_history_bad` antes de `promotable_shadow`) y añadir `and not verified_history_bad` al tuple `promotable_shadow`; branch `observe` con reason explícita cuando promoción bloqueada por historial. `verify_before_deploy.py` **717/717** (16 tests nuevos: 13 v10.6.20 base + 3 anti-flapping). Commits: `e8b236c` (paquete v10.6.20), `71ca261` (fix anti-flapping). Railway env vars aplicadas por Pablo: `ACTIVE_TRADING_CITIES=NONE`, `SCHEDULE_HOURS_UTC=4,8,12,16`. Deploy live autorizado y ejecutado (Opción A). |
| 2026-04-18 | Explícita | Sesión 198 | `58cf355` + `e132c7e` + `b7762bd` + `ef63efc` + `4cc94a6` | Migración del bot al SDK CLOB V2 de Polymarket antes del cutover del 22 de abril de 2026 (~11:00 UTC), fecha en que los clientes V1 dejan de funcionar completamente. La migración requirió 5 cambios en 2 archivos (`requirements.txt` y `bot.py`), descubiertos iterativamente vía errores de Railway: (1) `requirements.txt`: `py-clob-client==0.34.6` → `py-clob-client-v2==1.0.0`; (2) `bot.py` imports: módulo renombrado `py_clob_client.*` → `py_clob_client_v2.*`; (3) `bot.py` constructor: `chain_id` se mantiene igual en Python (el rename `chain_id→chain` era solo para TypeScript, la doc mezclaba ambos lenguajes); (4) `bot.py` auth: `create_or_derive_api_creds()` → `create_or_derive_api_key()`; (5) `bot.py` órdenes: `get_orders()` → `get_open_orders()`. El error 400 en `/auth/api-key` al arrancar es esperado: `create_or_derive_api_key()` intenta crear primero, falla porque la key ya existe y hace fallback a derivar; el log confirma "Autenticación OK". `tools/`, `city_intelligence`, `phase5_visibility`, `find_traders.py` y `trader_analyzer.py` no usan el SDK CLOB directamente (consumen REST vía `requests`/`httpx`) y no requirieron cambios. Bot verificado en Railway en Modo REAL. |
| 2026-04-18 | Explícita | Sesión 197 | local NOAA coverage queue hardening | Se endurece la cola de `observed_vs_forecast` en `bot.py` para dejar de perder cobertura NOAA por starvation del backlog. El diagnóstico local mostró que `London`, `Munich`, `New York City`, `Shanghai` y `Tokyo` tenían BUYs maduros en `performance.json` pero seguían sin poblar `audit.json`, porque `audit_check_resolution_truth()` procesaba solo `to_check[:10]`, repetía varios `city|date` del mismo día y no dejaba cooldown cuando NOAA devolvía vacío. El patch introduce tres guardrails mínimos: límites `OBSERVED_AUDIT_MAX_SUCCESSES_PER_RUN=10` y `OBSERVED_AUDIT_MAX_ATTEMPTS_PER_RUN=40`, dedupe por `city|date` con prioridad a ciudades con menor muestra y a candidatos `perf_buy` frente al fallback shadow, y cooldown de 12 horas usando `audit["errors"]` para reintentos fallidos `source=noaa_ncei/kind=observed_vs_forecast_fetch_failed`. `verify_before_deploy.py` se amplía con un test de dedupe `city|date` y vuelve a cerrar en 703/703; `py_compile` sigue pudiendo fallar por lock de `__pycache__` en Windows. |
| 2026-04-18 | Explícita | Sesión 196 | local dynamic TP high-conviction | TP dinámico implementado en `bot.py`: posiciones con `our_prob >= 0.80` en entrada usan TP del `+80%` en lugar del `+40%` fijo. Motivación: NYC NO del 17-abr, compra a $1.19 con alta convicción, TP prematuro habría cerrado una posición que podría haber llegado a resolución (`+172%`). Dos env vars nuevas `HIGH_CONVICTION_TP_PCT` (default 80.0) y `HIGH_CONVICTION_PROB_THRESHOLD` (default 0.80). `our_prob` no está en el dict de posición de la API — se cruza con `trade_lifecycle.json` via `entry_context.our_prob` keyed por `token_id`. Cambios en `manage_positions` (lookup + CHECK 2 dinámico) y en `intra_cycle_sl_check` (mismo patrón). `verify_before_deploy.py` 702/702. |
| 2026-04-18 | Explícita | Sesión 195 | local alarm review closeout + weak-city gate | Se cierra la revisión completa del lote actual de alarmas con criterio operativo estricto. Las dos variantes legacy de `Phase 5 Visibility` (`Shanghai + Chicago`, `gap + siguiente paso`) quedan confirmadas como formato ya superado por la sesión 194, por lo que pasan a tratarse como `alarma reescrita/eliminada` y ya no deben abrir sesión por sí solas. En la capa humana del bot también queda sellado que `Slot monetization review` no debe volver a arrastrar `23h UTC` cuando el slot está deshabilitado, y que el `Cross-check traders vs bot` solo debe elevar gap operativo real, no casos esperados como `Toronto` blocked o ruido débil como `Guangzhou` sin consenso. Además, la auditoría de `City Intelligence` aterriza en un gate read-only nuevo: `tools/city_validation_ledger.py` introduce `weak_city_hypothesis` para ciudades vistas repetidamente en shadow pero con `edge_hits=0`, y `tools/city_promotion_gate.py` lo traduce a `background_watch` / prioridad `later` en vez de mantenerlas en review activa cercana a monetización. Se regeneran los artefactos `city_validation_ledger` y `city_promotion_gate`; la ejecución real de los scripts pasa y escribe los outputs nuevos, aunque el intento de `py_compile` sobre tools falla por lock de `__pycache__` en Windows y no por error de sintaxis. |
| 2026-04-18 | Explícita | Sesión 194 | local alarm-closure rule for monetization | Se fija como regla operativa canónica que las alarmas del sistema no pueden cerrarse solo con documentación o análisis: cada alarma debe terminar en `cambio ejecutado`, `patch listo`, `gate definido` o `alarma reescrita/eliminada`, y si no abre ninguna de esas salidas debe desaparecer o rediseñarse. La regla se implementa en la capa `Phase 5 Visibility`: `tools/phase5_operational_action.py` añade `closure_type`, `closure_label` y `operational_change`, y `tools/phase5_visibility_telegram_alert.py` pasa a incluir en Telegram el `cierre obligatorio` y el `cambio operativo` para que la alarma traduzca evidencia en acción. Queda explicitado para la siguiente sesión que ya no hay que reexplicar este criterio: el agente debe responder directamente qué cambia en operativa por haber saltado la alarma y con cuál de las cuatro salidas se cierra. |
| 2026-04-18 | Explícita | Sesión 193 | local phase5 visibility trace sync | Se actualiza la trazabilidad local de `Phase 5 Visibility` para reflejar una nueva coincidencia real del probe sin tocar `bot.py`, trading core, NOAA core, scheduler ni policy live. El evento fijado es `2026-04-18T01:58:33+00:00` con `Shanghai=2`, `Chicago=2` y `coincidencias acumuladas=11`. La lectura operativa se mantiene: `dominant_gap=evidence_asymmetry_between_shadow_and_active` y siguiente paso `use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence`. Se alinean los readouts `*_latest` y JSON asociados de la capa phase5 para que el repo no siga mostrando `5 snapshots / 0 simultaneidades` cuando ya existe evidencia repetida de coincidencia Shanghai+Chicago. |

| 2026-04-17 | Explícita | Sesión 192 | snapshot Railway fresh + protocolo Seoul post-fix | Auditoría operativa read-only para cerrar la ambigüedad de Seoul tras el incidente `forecast_station_mismatch`. Se refresca `data/runtime_import/` desde Railway y se confirma que live ya no tiene `auto_blocked_cities.Seoul`: la ciudad reapareció en `auto_canary_cities` a las `2026-04-17T16:29:31Z` y el ciclo `2026-04-17T20:44:48Z` abrió una compra real `Seoul 24°C Apr19 YES` (`edge=29.1%`, `$1.23`). La verificación decisiva cruza `CONTEXTO.md`, `git show ed00535`, `bot.py` actual y `decisions.log`: aunque el runtime todavía etiqueta `BOT_VERSION=v10.6.15`, el código live ya usa `RESOLUTION_STATIONS["Seoul"] = (37.5665, 126.9780)` y los forecasts observados (`23.6°C`, `23.8°C`, `25.9°C`) encajan con Seoul ciudad y no con la fuente vieja de Incheon. Decisión operativa cerrada y documentada: esta posición cuenta como la primera evidencia post-cambio de fuente; no se toca nada mientras esté abierta; si gana, Seoul sigue en `canary` con `post-fix sample #1`; si pierde, Seoul baja a `shadow` pero sigue contando como `post-fix sample #1`; toda evaluación futura debe ignorar el edge legacy contaminado por Incheon y, si se quiere evitar nueva autopromoción automática, habrá que aislar o resetear `shadow_city_tracking` tras el cierre. |
| 2026-04-17 | Explícita | Sesión W17-Opus | `669af20` + 3 commits anteriores + Railway vars | Revisión estratégica Opus + bloque W17 completo ejecutado en una sesión. Causa raíz del throughput bajo identificada: `condition_filtered` mata ~47% de candidatos, modelo sobreestima P(YES) en exact/range (bot 0% WR en YES side, traders 76% WR). 4 cambios en bot.py: whitelist canary +4 ciudades, YES exact/range floor `our_prob<65%`, Seoul promotion bug fix, W17 observation alert one-shot. Railway actualizado: whitelist live + `SCHEDULE_DISABLED_HOURS_UTC=23`. 3 docs estratégicos creados. `verify_before_deploy.py` 702/702. |
| 2026-04-17 | Explícita | Sesión 191 | local Telegram wording correctness patch | Sesión corta de correctness en la capa humana de Telegram, sin tocar trading core, NOAA, scheduler, policy live ni métricas base. Se auditan dos avisos automáticos disparados a primera hora: `Cross-check diario traders vs bot` y `Blocked signals`. Hallazgo: el cálculo estaba bien, pero el wording inducía lecturas demasiado fuertes. En el cross-check, la lista visible de ciudades actionable no era una priorización sino solo las primeras `4` del conjunto; el mensaje se ajusta para declarar explícitamente `muestra top N de M`. En blocked-signals, el texto hablaba de `canary excluido` aunque la exclusión real usa `QUALITY_TRADER_CITIES_WHITELIST`; se renombra a `Blocked signals (fuera de whitelist)` y la nota pasa a `Baseline fuera de QUALITY_TRADER_CITIES_WHITELIST`. Validación local: `python -m py_compile bot.py` OK. |
| 2026-04-17 | Explícita | Sesión 190 | `8ec4261` + Railway `SCHEDULE_DISABLED_HOURS_UTC=23` | Cierre live del loop de scheduler por slot. Se empuja a `main` el patch que ya instrumentaba `scan.slot_metrics`, evaluaba automáticamente `04h/23h`, añadía `SCHEDULE_DISABLED_HOURS_UTC` y corregía el cuello de ejecución por mínimo nocional; `verify_before_deploy.py` vuelve a pasar en `702/702`. En Railway se aplica `SCHEDULE_DISABLED_HOURS_UTC=23` y se elimina la env obsoleta `SLOT_04H_REVIEW_REMINDER_DATE`. Verificación final por logs del deploy `6d840105-4246-4c03-8658-18081492f5d7`: el bot arranca con `Schedule: [4, 8, 16] UTC` y `Schedule disabled hours: [23] UTC`, dejando `23h` apagado live de forma reversible y `04h` como slot útil a seguir midiendo. |
| 2026-04-17 | Explícita | Sesión 189 | local slot monetization operational alert | Se añade la capa automática que faltaba encima de `scan.slot_metrics`. `bot.py` integra `maybe_evaluate_slot_monetization(state)` dentro de `run_observability_alerts()`, con estado persistente para idempotencia diaria y cambio de firma. La nueva alerta lee `cycles_history.jsonl`, agrega los últimos ciclos exactos de `04h` y `23h`, clasifica cada slot (`validated`, `not_validated_yet`, `disable_candidate`, etc.) y envía por Telegram una salida operativa con funnel, reject reasons dominantes y siguiente acción sugerida para Codex. El sistema aún no aplica automáticamente el cambio live; automatiza la revisión y la recomendación, no el deploy. `verify_before_deploy.py` cierra en `702/702`. |
| 2026-04-17 | Explícita | Sesión 188 | local monetization patch for 04h + slot instrumentation | La revisión del slot `04h` se convierte en cambio de sistema, no solo en doc. Se añade `SCHEDULE_DISABLED_HOURS_UTC` como feature flag para apagar slots concretos sin reescribir el scheduler base; la recomendación operativa queda lista para usar `23` como disable candidate por su utilidad neta casi nula. Se instrumenta `scan.slot_metrics` en `cycle_summary.json` y `cycles_history.jsonl` con funnel y rechazos por slot (`same_day_candidates`, `same_day_edges`, `same_day_selected`, `same_day_buys`, `edges`, `selected`, `buys`, `buy_rate`, `reject_reasons`, etc.). Además, se corrige un cuello real de monetización: antes de ejecutar un BUY, el bot ahora ajusta `shares` hacia arriba cuando el redondeo deja la orden justo por debajo del mínimo de notional, evitando fallos del tipo `invalid amount for a marketable BUY order ($0.9976), min size: $1` ya observados en `04h`. El recordatorio one-shot `04h` se retira del código por obsoleto. `verify_before_deploy.py` vuelve a pasar en `697/697`. |
| 2026-04-17 | Explícita | Sesión 187 | local railway runtime pull + 04h slot observation | Revisión programada del rollout `SCHEDULE_HOURS_UTC=4,8,16,23` cinco días después de activarlo. Se refresca `data/runtime_import/` con snapshot nuevo de Railway y se crea `docs/04h-slot-observation-2026-04-17.md` con comparación homogénea `pre` vs `post` sobre ciclos exactos. Hallazgo central: `04h UTC` sí abre same-day real para `Tokyo`, `Seoul` y `Shanghai`; en el ciclo `2026-04-17T04:00:45Z` aparecen `25` candidatos post-filtro, `2` edges y `2` seleccionadas, incluyendo `Shanghai NO 20°C` y `Tokyo NO 18°C`, pero sin buy efectivo por restricciones de tamaño mínimo / Kelly. El throughput ejecutado sigue en cero buys por ciclo en la muestra post, mientras `23h` enseña `0` edges, `0` buys y same-day mayormente tardío o bloqueado, quedando como candidato razonable a salir si el objetivo del schedule sigue siendo throughput útil. |
| 2026-04-17 | Explícita | Sesión 186 | local phase5 operational action workflow | La alerta legacy de `Phase 5 Visibility` se convierte en trigger operativo read-only sin tocar `bot.py`, trading core, NOAA, scheduler ni policy live. Se crea `tools/phase5_operational_action.py` para traducir la coincidencia `Shanghai + Chicago` a `severity`, `action_state` y `next_operational_step`, persistiendo `data/phase5_operational_action.json` y `docs/phase5_operational_action_latest.md`. `tools/phase5_visibility_pipeline.py` integra la nueva etapa y expone su resumen operativo; `tools/phase5_visibility_telegram_alert.py` amplía el mensaje para incluir la lectura derivada y no quedarse solo en `gap + next_step`. La validación local confirma que la pipeline cierra en `ok`; con los artefactos versionados actuales la salida es `no_progress`, pero una simulación del caso reportado (`probe 2026-04-17T01:56:54+00:00`, `Shanghai=2`, `Chicago=2`, `coincidencias=9`, `gap=evidence_asymmetry_between_shadow_and_active`) clasifica correctamente `watch / review / increase_review_priority`, que era el objetivo de workflow. La sesión también elimina el doc de diseño intermedio para dejar solo código y trazabilidad mínima. |
| 2026-04-16 | Explícita | Sesión 181 | local dashboard shadow-only residual fix + live verification | Se completa el diagnóstico post-deploy del fix `_is_shadow_only()` con foco en la explicación más simple. Railway está sano y el proceso live sí arranca en `MODO REAL`, así que `SHADOW_ONLY_MODE=false` llega correctamente al bot; además `cycle_summary.json` queda en `mode="REAL"`. La parte UI residual sí existía: `build_daily_summary_payload()` seguía calculando `shadow_only` como `len(ACTIVE_TRADING_CITIES) == 0`, arrastrando una lectura stale de `SHADOW-ONLY` aunque la fuente de verdad canónica ya fuera `_is_shadow_only()`. Se aplica un fix mínimo para unificar esa capa sin tocar trading core. `verify_before_deploy.py` vuelve a pasar en `685/685`. Pero la sesión también confirma que el problema no era solo dashboard: en producción sigue apareciendo al menos un `shadow_only_override` posterior al deploy (`Seoul`, ciclo `2026-04-16T07:07`, `city_mode=canary`, `edge_pct=68.47`). Veredicto final de la sesión: `dashboard + gating real`, no solo presentación. |
| 2026-04-16 | Explícita | Sesión 180 | local bot.py shadow-only fix + deploy handoff | Se valida y prepara para deploy un fix de correctness en `bot.py` centrado en `_is_shadow_only()`, sin tocar trading core, NOAA, scheduler, Kelly, sigma ni filtros. La causa raíz cerrada era semántica: `ACTIVE_TRADING_CITIES=NONE` se interpretaba como pausa global y bloqueaba también ciudades ya promovidas a `auto_canary`. El cambio desacopla ambos conceptos: `_is_shadow_only()` pasa a leer `SHADOW_ONLY_MODE` como toggle explícito y deja un fallback legacy solo para el caso “sin activas y sin canary explícitas en env vars”. `verify_before_deploy.py` vuelve a pasar en `685/685`. Se actualiza la documentación operativa para dejar claro que el sistema ya no debe leerse como `shadow-only` deliberado, y se deja instrucción exacta para Railway: añadir `SHADOW_ONLY_MODE=false` manteniendo `ACTIVE_TRADING_CITIES=NONE`. Queda pendiente la validación post-deploy en live: dashboard en modo real y primeros ciclos con `Chicago` pasando de `policy_execution_gate` a ejecución canary efectiva. |
| 2026-04-15 | Explícita | Sesión 179 | local read-only tooling refresh + handoff | Auditoría operativa del funnel live priorizando `skip_log.jsonl`, `shadow_city_tracking.json`, `signals.json`, `policy_env_snapshot.json`, `city_validation_ledger.json`, `city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md`. Hallazgo fuerte: el runtime reciente ya no sostiene `trader_discovery` como cuello dominante del throughput útil; en los dos últimos ciclos hubo `4` near-misses con `edge_pct >= 15` y `3/4` murieron por gating operativo (`shadow_only_override` / `fuera_allowlist`), no por edge/modelo. Se ajustan `tools/city_validation_ledger.py` y `tools/city_promotion_gate.py` para incorporar evidencia reciente de `skip_log` y distinguir `policy_execution_gate`; los artefactos regenerados pasan a mostrar ese bottleneck como dominante y priorizan `Shanghai` y `Chicago`. `verify_before_deploy.py` vuelve a cerrar en `685/685`. La alerta nueva `Phase 5 Visibility` (`Shanghai + Chicago`, probe `2026-04-15T13:54:33+00:00`) se deja explícitamente para una sesión limpia en `docs/next-session-handoff-2026-04-15-policy-gate-throughput.md`. |
| 2026-04-14 | Explícita | Sesión 176 | feat: condition_reopen_monitor + bot integration (v10.6.16) | Implementación del monitor automático del canary condition_filtered. `tools/condition_reopen_monitor.py` standalone read-only: carga `trade_lifecycle.json`, filtra trades exact/range desde 2026-04-14, calcula WR por ciudad, emite veredicto (OK/ALERT/CLOSE/PROMOTE/EXTEND/KILL_SWITCH). `maybe_run_condition_monitor(state)` en `bot.py` v10.6.16: dispara desde día 7 en fechas de checkpoint (2026-04-21, 2026-04-28) o cuando kill-switch activo (WR<45% n≥20); anti-spam via `state["last_condition_checkpoint"]`; kill-switch repite diariamente. Mensaje Telegram incluye métricas + instrucción Sonnet lista para pegar. 9 tests nuevos en `verify_before_deploy.py`. `verify_before_deploy.py` 680/680. |
| 2026-04-14 | Explícita | Sesión 175 | feat: condition_filtered canary reopen exact/range (v10.6.15) | Sesión de decisión + implementación. Sonnet analizó 59 resoluciones reales de quality traders en señales `exact/range` bloqueadas por `condition_filtered`: WR=76.3% (exact 72.5% n=51, range 100% n=8), threshold de reopen cumplido (≥55% n≥50). Opus decidió vía subagente (Opción B modificada): reabrir con triple gate — quality trader + whitelist 9 ciudades (Seattle, Tokyo, Hong Kong, Seoul, Toronto, Chengdu, Shenzhen, Shanghai, Milan) + edge mínimo diferenciado (MIN_EDGE+5pp). London excluida (WR 33% n=3). Sizing efectivo 25% del normal (CANARY_POSITION_SCALE × EXACT_RANGE_SIZE_SCALE). Kill-switch: WR bot <45% n≥20. Checkpoints: 2026-04-21 (día 7) y 2026-04-28 (día 14). Implementado en `bot.py` v10.6.15: 4 env vars nuevas, lógica triple gate en condition_filtered, edge buffer, size scale. `verify_before_deploy.py` 671/671. Deploy Railway OK — verificado en logs: feature activo, Milan 18°C exact procesada por la ruta canary (min 20.0% en log confirma gate abierto). Milan 19°C exact con edge 21.5% habría operado si estuviera en canary mode. Pendiente siguiente sesión: `tools/condition_reopen_monitor.py` + integración Telegram con instrucción Sonnet para checkpoints automáticos. Handoff: `docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md`. |
| 2026-04-12 | Explícita | Sesión 167 | worktree-hygiene-gitignore-cleanup | Sesión de higiene del worktree sin tocar `bot.py`, trading core ni Railway. Causa raíz: el `.gitignore` solo cubría artefactos Python/IDE, dejando sin reglas los tres flujos principales de suciedad: (1) snapshots de Railway en `data/runtime_import/`, (2) outputs regenerables de tools en `data/*.json` y `docs/*_latest.md`, y (3) artefactos de sesión (`docs/next-session-handoff-*.md`, `docs/claude-opus-prompt-*.md`). Se añaden reglas `.gitignore` para cubrir todos estos patrones. Se untrackearon con `git rm --cached` cinco archivos generados que estaban incorrectamente en el índice git: `data/runtime_import/city_policy_state.json`, `data/runtime_policy_effective_view.json`, `data/system_alignment_check_operational.json`, `docs/runtime_policy_effective_view_latest.md`, `docs/system_alignment_check_operational_latest.md`. Se stagearon 32 scripts nuevos de `tools/`, `seed_data/phase5/` (3 archivos), `RTK.md` y ~60 docs de análisis/diseño con valor permanente. Resultado: 0 archivos sin trackear desde 167. Entregable: `docs/worktree-hygiene-audit-2026-04-12.md`. |
| 2026-04-12 | Explícita | Sesión 166 | live-policy-london-dallas-reconcile/atlanta-lifecycle-note | Se ejecuta un cambio live mínimo y deliberadamente acotado sobre `city_policy_state.json` en el volumen de Railway, sin tocar `bot.py`, thresholds, env vars ni promover manualmente ciudades. Tras el preflight operacional inicial con `error=1` por el blocker conocido de `Dallas`, la sesión usa `tools/railway_safe.ps1`, hace backup previo de `/app/data/city_policy_state.json` y elimina exactamente dos overlays persistidos: `London` sale de `auto_canary_cities` y `Dallas` sale de `auto_shadow_cities`, sin tocar `transition_history` ni otros campos. Luego se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1`, se regenera `data/runtime_policy_effective_view.json` y el preflight operacional vuelve a `error=0` (`ok=6`, `warning=2`), desapareciendo el `blocking_operational_collision` de `Dallas` y quedando la foto en `blocked=3`, `canary=6`, `shadow=18`. En paralelo se crea `docs/atlanta-lifecycle-inconsistency-2026-04-12.md` y se alinea `docs/canary-to-active-readiness-2026-04-12.md`: el trade `Atlanta 76°F Apr7 YES` debe leerse como win mal etiquetada, porque su `timeline` registra `RESOLVED_WIN +$0.63` y `post_exit_analysis` confirma mercado a `0.9995`, aunque `close_context` termine como `LOSS_TOTAL` por `micro_position_unsellable`. |
| 2026-04-12 | Explícita | Sesión 165 | dallas-canary-diagnosis/canary-active-readiness | Sesión read-only de diagnóstico sobre Dallas y las canary, sin tocar `bot.py`, thresholds, listas de ciudades, Railway ni policy live. `docs/dallas-canary-block-diagnosis-2026-04-12.md` confirma que `CITY_STATS_CUTOFF` no explica por qué Dallas no reaparece en `auto_canary_cities`: el cutoff solo afecta `get_city_accuracy()`/`get_city_policy_metrics()`, mientras la regla shadow -> canary usa `shadow_city_tracking`, y Dallas sigue hoy en `edge_hits=8`, `cycles_seen=5`, `best_edge_pct=45.8`. La foto runtime efectiva además ya la deja `env=shadow`, así que el bloqueo apunta a un overlay `auto_shadow` persistido/inconsistente, no a falta real de evidencia reciente. En paralelo, `docs/canary-to-active-readiness-2026-04-12.md` deja la tabla factual de las seis canary pedidas: `Munich` y `New York City` siguen sin trades canary post-promoción; `Seoul`, `Shanghai` y `Tokyo` tienen una primera señal positiva limpia pero solo `n=1`; y `Atlanta` queda contaminada por una inconsistencia en `trade_lifecycle` (`close_context=LOSS_TOTAL` pero `timeline` registra antes `RESOLVED_WIN +$0.63`). La sesión deja además documentado que el snapshot actual ya incluye `London` como séptima auto-canary desde `2026-04-12T15:03:51Z`, aunque la auditoría respeta las seis ciudades pedidas. |
| 2026-04-12 | Explícita | Sesión 164 | blocked-cities-structural-closeout/shadow-canary-shortlist | Sesión de cierre read-only sobre policy/observabilidad de ciudades, sin tocar `bot.py`, thresholds, allowlists, bankroll ni cambiar Railway desde Codex. Primero se documentan dos auditorías estructurales de `BLOCKED_CITIES`: `docs/ankara-paris-unblock-review-2026-04-12.md` y `docs/remaining-blocked-cities-review-2026-04-12.md` dejan que el criterio canónico solo sostiene `London` (mismatch documentado), `Toronto` y `Singapore` (sin `noaa_station_id` en `RESOLUTION_ICAO`), mientras `Ankara`, `Paris`, `Madrid`, `Wellington` y `Tel Aviv` deben vivir en `shadow`. Luego, tras el cambio manual del usuario en Railway a `BLOCKED_CITIES=London,Toronto,Singapore`, se refresca `data/runtime_import/`, se regenera la `runtime_policy_effective_view` y el preflight operacional vuelve a `error=0`, con foto live `blocked=3`, `canary=6`, `shadow=19`. Finalmente se abre Bloque B en `docs/shadow-canary-threshold-review-2026-04-12.md`: solo `Dallas` y `Chicago` tienen hoy base suficiente para justificar una revisión acotada del umbral `canary`; `Buenos Aires` sigue en observación y `Denver`, `Los Angeles`, `Houston`, `San Francisco` y `Mexico City` quedan todavía demasiado verdes o débiles para mover esa conversación. |
| 2026-04-12 | Explícita | Sesión 163 | market-universe-price-temporal-audit/read-only | Se abre y cierra un módulo read-only para responder dos preguntas nuevas de throughput sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`: cuánto universo real de mercados de temperatura ofrece hoy Polymarket por ciudad/día, y si los mercados que caen en `price_out_of_range` luego entran en una ventana útil. Se añade `tools/analyze_market_universe.py` y se deja `docs/polymarket-universe-price-temporal-audit-2026-04-12.md` como readout reproducible sobre el snapshot manifestado tirado a `2026-04-12T10:15:51Z`. La conclusión fuerte es doble: el universo observado es muy estable (`29` ciclos normales en `324-330` mercados, mediana `330`, `30` pares `city+date` por ciclo, `273/277` city-dates con exactamente `11` mercados), así que no aparece un ceiling nuevo por discovery; y el bucket `price_out_of_range` casi nunca se convierte en throughput útil (`1091` mercados únicos tocaron ese bucket, solo `25` -> `2.3%` llegaron alguna vez a fase pre-edge, mientras `810` -> `74.2%` solo salieron para morir en filtros temporales y `256` -> `23.5%` nunca salieron de precio). Además, `1058/1091` (`97.0%`) entran por primera vez ya con `mkt_prob < 20` y ese mismo `97.0%` nunca ve `mkt_prob >= 20` después. La lectura operativa resultante es que el techo inmediato parece venir más del funnel que del universo visible, y que la siguiente observación útil debe ser post-rollout del slot `04h`, no una tesis amplia de precio/timing global. |
| 2026-04-12 | Explícita | Sesión 162 | railway-04h-slot/reminder-automation-close | Se activa en Railway la siguiente fase mínima de throughput temporal: `SCHEDULE_HOURS_UTC` pasa a `4,8,16,23` para abrir cobertura `same-day` real a `Tokyo`, `Seoul` y `Shanghai`, sin tocar edge, thresholds, bankroll, política de ciudades ni scheduler interno. En paralelo se automatiza el seguimiento lean del experimento añadiendo en `bot.py` la env var `SLOT_04H_REVIEW_REMINDER_DATE` y un helper one-shot dentro de `run_observability_alerts()` que enviará por Telegram, el `2026-04-17`, un prompt corto para auditar el slot `04h` con Codex y crear `docs/04h-slot-observation-2026-04-17.md`. Validación local: `python verify_before_deploy.py` sigue en `643/643`. Validación live: Railway acepta `SCHEDULE_HOURS_UTC=4,8,16,23` y `SLOT_04H_REVIEW_REMINDER_DATE=2026-04-17`; el servicio `polymarket-bot` queda en nuevo deploy `BUILDING` por el cambio de variables. |
| 2026-04-12 | Explícita | Sesión 161 | city-window-routing/implementation-traceability-close | Se implementa en `bot.py` el city-window prefilter diseñado tras el intercambio con Opus, sin tocar edge, thresholds, bankroll, política de ciudades ni scheduler. La nueva `compute_city_windows()` reutiliza `get_min_days_for_city()` como source of truth para no divergir del override manual `MIN_DAYS_AHEAD`; el early-exit same-day se inserta después de `blocked/mode/shadow` y antes del safety net de fecha, evitando ruido estructural sin perder la semántica operativa existente. `cycle_summary.json` y `cycles_history.jsonl` pasan a guardar `scan.city_window_skipped` y `scan.city_window_cities`, mientras el decision log añade una línea `VENTANA: ...` sin volver a inflar `skip_log.jsonl`. Validación técnica: `python -m py_compile bot.py` pasa y `python verify_before_deploy.py` vuelve a `643/643`. Durante el cierre aparece además un falso rojo de trazabilidad: docs ya iban por la sesión `160`, pero `agent_events.jsonl` seguía detrás; se registra la sesión faltante y el preflight vuelve a verde. |
| 2026-04-12 | Explícita | Sesión 160 | fix/city-timezones-american-cities | Auditoría adversarial del funnel pre-edge (timezone_filter + lado derecho canary) y bug fix de CITY_TIMEZONES. Se confirma que timezone_filter (15.3% del funnel last12) es intocable: 100% son ciudades asiáticas a 16-21h local, filtro correcto por diseño. Se confirma que el throughput canary es críticamente bajo: 967 skips en last12, solo 2 llegan a below_min_edge (ambos Shanghai), 0 trades. Cuello dominante: price_out_of_range con mediana mkt_prob=0.55%. Se confirma que condition_filtered es política deliberada (pérdidas históricas en otras condiciones), no bug. Bug timezone encontrado y corregido: Denver, Mexico City, Los Angeles, Houston y San Francisco no estaban en CITY_TIMEZONES y caían a UTC fallback, causando que 33 market instances fueran bloqueadas falsamente en last12 (se trataban como 16-20h local cuando tenían 10-13h real). Fix: 5 entradas añadidas con zonas IANA correctas. verify_before_deploy.py pasa sin errores. Se prepara prompt Opus para diseño de ciclos por ventana de ciudad. Frente pendiente antes de Opus: Telegram Correctness (Codex). |
| 2026-04-12 | Explícita | Sesión 159 | rtk-shim/local-compat | Se corrige una fricción pequeña pero repetitiva de tooling/documentación sin tocar `bot.py`, Codex global ni Claude global. El diagnóstico confirma que `rtk` sí está instalado y operativo en Codex (`rtk 0.34.3`) y que también existe `~/.codex/RTK.md`, así que el problema no era de instalación sino de resolución de la referencia `@RTK.md` desde el repo. Para evitar romper compatibilidad con Claude o depender de rutas globales distintas entre clientes, se crea un `RTK.md` local y neutral dentro del repo como shim estable. El cambio deja de hacer depender la referencia de cómo cada cliente expande archivos globales y evita tocar configuraciones globales que sí podrían haber roto el flujo en Claude. |
| 2026-04-12 | Explícita | Sesión 158 | same-day-timing-audit/read-only | Se abre y cierra el módulo `Same-Day Timing Audit` sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr los dos preflights canónicos a `2026-04-12T10:56:05+00:00`, y ambos siguen en `ok=7, warning=1, error=0`. Luego se audita el subbucket same-day dentro de `date_out_of_range_past` sobre la misma ventana de `29` ciclos y `9896` skips, usando la regla horaria ya viva en `bot.py`: `min_days_global=1` desde `12:00 UTC` y cutoff práctico `hora_local >= 14` o `día local siguiente`. El nuevo `docs/same-day-timing-audit-2026-04-12.md` deja cuatro conclusiones fuertes: aunque `3980/4475` skips de fecha (`88.9%`) siguen siendo same-day, casi todos ya entran demasiado tarde en la práctica (`3925`, `98.6%`), por lo que same-day no equivale a recuperable; la distribución no es un pico fino sino un patrón estructural en slots post-mediodía, con masa fuerte en `16-17 UTC` y `22-23 UTC`; la parte plausibly recoverable es muy pequeña (`55` filas, `1.4%`) y vive casi solo en `Los Angeles`, `Denver` y `Mexico City`; y por tanto la hipótesis `tiempo` como gran palanca general de throughput queda debilitada, quedando como micro-oportunidad posible por ciudad/slot y no como unlock horizontal del funnel. |
| 2026-04-12 | Explícita | Sesión 157 | prefilter-throughput-audit/read-only | Se abre y cierra el módulo `Prefilter Throughput Audit` sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr los dos preflights canónicos a `2026-04-12T10:36:27+00:00`, y ambos siguen en `ok=7, warning=1, error=0`. Luego se audita `data/runtime_import/skip_log.jsonl` sobre `29` ciclos y `9896` skips reales con un foco pre-edge explícito: cuánto se pierde por fecha, precio y composición por ciudad/modo. El nuevo `docs/prefilter-throughput-audit-2026-04-12.md` deja cuatro conclusiones fuertes: `date_out_of_range_past` sigue siendo el bucket dominante (`45.2%`) y parece venir sobre todo de mercados que llegan demasiado tarde dentro del flujo normal (`88.9%` same-day, `days_late=0`), pero la recuperabilidad por timing queda explícitamente como hipótesis a auditar con granularidad horaria; `price_out_of_range` es grande (`22.7%`) pero está pegado casi por completo al extremo bajo (`97.6%` con `mkt_prob < 20`, mediana `0.3`), no a una nube fina cerca del rango permitido; `Miami` y `Seattle` ya aportan universo visible real como `shadow` efectivo, pero solo suman `5.8%` del funnel reciente y casi todo sigue muriendo por fecha/precio; y `blocked_city` ya cae a `4.4%` en `last12`, así que la siguiente palanca más prometedora para una futura discusión de throughput sigue siendo `tiempo`, aunque todavía no como palanca confirmada. |
| 2026-04-12 | Explícita | Sesión 156 | dallas-drift/live-railway-closeout | Se cierra por fin el drift real de `Dallas`. La evidencia ya era clara: al sincronizar las env vars manuales desde Railway, `ACTIVE_TRADING_CITIES=Dallas` reaparecía como `env active` frente a `city_policy_state.auto_shadow_cities`, generando otra vez `blocking_operational_collision`. El cierre correcto no era retocar tooling ni `bot.py`, sino borrar la declaración live sobrante. Se elimina `ACTIVE_TRADING_CITIES` del servicio `polymarket-bot` en Railway, se refresca `data/runtime_import/`, `policy_env_snapshot.json` ya queda con `ACTIVE_TRADING_CITIES=""`, y `runtime_policy_effective_view` vuelve a dejar `Dallas` como `env=shadow`, `runtime=auto_shadow`, `effective=shadow`. Tras eso, `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` regresan a `ok=7, warning=1, error=0`, con `blocking_operational_collision_count=0`. |
| 2026-04-12 | Explícita | Sesión 155 | policy-env-snapshot/effective-view-sync | Se corrige la deuda técnica menor de la effective view para que ya no dependa de pasar `BLOCKED_CITIES` manualmente al regenerarla. `tools/railway_runtime_snapshot_pull.ps1` pasa a exportar un `policy_env_snapshot.json` read-only con solo `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES` y `BLOCKED_CITIES`, y `tools/runtime_policy_effective_view.py` ahora lo usa por defecto antes de mirar el entorno local del proceso. La validación confirma que `Miami` y `Seattle` siguen resolviendo `shadow` automáticamente sin flags manuales. El efecto colateral honesto del fix es que también reaparece el drift real de `Dallas`: como el snapshot ya trae `ACTIVE_TRADING_CITIES=Dallas`, la effective view vuelve a exponer `env active` vs `runtime auto_shadow`, y `python tools/system_alignment_check.py --decision-mode operational` cae a `error=1` por `blocking_operational_collision_count=1`. La sesión, por tanto, cierra el fix del transporte/env correctamente pero deja visible que el siguiente bloqueo ya no es tooling sino policy live/manual drift en Dallas. |
| 2026-04-12 | Explícita | Sesión 154 | railway-snapshot/effective-view/shadow-check | Se valida el cambio manual en Railway que quita `Miami` y `Seattle` de `BLOCKED_CITIES`. Primero se refresca `data/runtime_import/` con `tools/railway_runtime_snapshot_pull.ps1`, dejando `runtime_import_manifest.json` actualizado al `2026-04-12T09:57:08Z`. Luego se regenera la `runtime_policy_effective_view`; al revisar la herramienta se detecta un matiz importante: `tools/runtime_policy_effective_view.py` sigue teniendo un fallback local stale para `DEFAULT_BLOCKED_CITIES`, así que para reflejar el estado live real hay que ejecutarla con el valor explícito ya aplicado en Railway (`London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`). Con esa regeneración, `Miami` y `Seattle` pasan a `env_declared_mode=shadow` y `effective_mode=shadow`, y el conteo global queda en `shadow=16`, `blocked=8`, `canary=6`. Finalmente `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` siguen cerrando en `ok=7, warning=1, error=0`, por lo que la capa canónica queda alineada con el cambio manual sin tocar `bot.py`, `city_policy_state.json` ni configuración core. |
| 2026-04-12 | Explícita | Sesión 153 | blocked-review/four-cities/read-only | Se abre una sesión corta y read-only para revisar las cuatro ciudades marcadas como `dudoso y candidato a revisión futura` dentro de `BLOCKED_CITIES`: `Ankara`, `Miami`, `Paris` y `Seattle`. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos siguen cerrando en `ok=7, warning=1, error=0`, con lo que la revisión queda gateada por la misma señal canónica ya usada para alignment. Luego se comprueba que las cuatro ciudades sí tienen `noaa_station_id` en `RESOLUTION_ICAO`, que siguen apareciendo en artefactos runtime recientes (`cycles_history`, `skip_log`, `performance` o `trade_lifecycle`) y que, por tanto, no son simplemente ciudades muertas o imposibles de observar en shadow. El nuevo `docs/blocked-cities-review-2026-04-12.md` deja un veredicto por ciudad sin tocar runtime live: `Miami` y `Seattle` pasan a `candidata a shadow`, mientras `Ankara` y `Paris` quedan en `insuficiente evidencia`. También queda escrito el cambio manual exacto pendiente si Pablo aprueba quitar solo `Miami` y `Seattle` de `BLOCKED_CITIES`, pero la sesión no ejecuta ningún cambio en Railway ni reabre alignment o config-drift como módulos. |
| 2026-04-12 | Explícita | Sesión 152 | skip-log-readout/analyzer-fix | Se abre y cierra la primera lectura operativa real del funnel a partir de `data/runtime_import/skip_log.jsonl`, ya sin mezclar alignment ni blocked/config-drift. Primero se revalidan los dos preflights canónicos, que siguen en `ok=7, warning=1, error=0`. Luego aparece un bug real pero pequeño en `tools/analyze_skip_log.py`: asumía `data/skip_log.jsonl`, mientras la capa read-only vigente vive en `data/runtime_import/skip_log.jsonl`; se corrige el default para preferir `runtime_import` y se sincroniza `docs/skip-log-analyzer.md`. Con eso, el analyzer corre sobre `25` ciclos y `8576` skips reales, y `docs/skip-log-readout-2026-04-12.md` deja la lectura compacta del funnel: `date_out_of_range_past=46.2%`, `price_out_of_range=21.3%`, `blocked_city=18.8%`, `timezone_filter=9.2%`, `condition_filtered=3.9%`, `below_min_edge=0.1%`, con un único near-miss relevante (`Shanghai`, `edge_pct=2.71`). La conclusión queda cerrada sin tocar policy: el cuello dominante sigue siendo estructural y temprano, no `MIN_EDGE`, Kelly ni sizing. |
| 2026-04-12 | Explícita | Sesión 151 | alignment-closeout/formal-seal | Se hace una sesión corta de sellado para cortar la sensación de módulo eternamente abierto. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos siguen en `ok=7, warning=1, error=0`, con `blocking_operational_collision_count=0`. Luego se verifica que el “Paso 1” sugerido por Sonnet ya estaba técnicamente resuelto: `tools/reference_trader_city_market_cross.py` ya no usa `legacy_bot_lists` y los fósiles `normal_pull_check/final_check` ya no existen en `data/runtime_import_derived/`. El trabajo real pendiente era solo de cierre narrativo, así que `docs/manual-config-drift-audit-2026-04-12.md` se actualiza con un `Closure Checkpoint` y una regla explícita de no reapertura: los módulos `System Alignment Lean Roadmap` y `Blocked Cities / Config Drift Cleanup` quedan cerrados salvo que vuelva a fallar el preflight operacional o aparezca una contradicción real de fuente de verdad. |
| 2026-04-12 | Explícita | Sesión 150 | blocked-rationale/latest/read-only | Se convierte `docs/blocked-cities-rationale-latest.md` desde una ficha genérica defensiva a una justificación canónica y corta por ciudad, sin tocar `bot.py`, `city_policy_state.json`, runtime live, thresholds, allowlists, bankroll ni `exact/range`. Primero se vuelven a correr `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos cierran en `ok=7, warning=1, error=0`. La effective view sigue dejando las mismas `10` ciudades como `blocked`, pero la lectura ya no las trata como un bloque homogéneo: `London` queda como único caso bien defendido por memo estructural explícito (`Weather Underground vs Open-Meteo`), `Madrid/Singapore/Tel Aviv/Toronto/Wellington` quedan alineadas pero subdocumentadas, y `Ankara/Miami/Paris/Seattle` pasan a quedar marcadas como bloqueos hoy conservados pero dudosos, con revisión futura separada si se quiere sostener que `blocked` sigue significando descarte estructural y no carry-forward histórico. |
| 2026-04-12 | Explícita | Sesión 149 | drift-audit/latest/checks | Se cierra la auditoría `Manual Config Drift` y su cleanup inmediato sin tocar `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll ni `exact/range`. Primero se rehidrata `runtime_policy_effective_view`, se reejecutan `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`, y ambos preflights vuelven a cerrar en `ok=7, warning=1, error=0`; el warning residual de `metrics_funnel_naming` queda eliminado al corregir el mensaje autorreferencial del propio `system_alignment_check.py`. Luego `docs/manual-config-drift-audit-2026-04-12.md` clasifica el estado de los overrides/manual lists: `DEFAULT_ACTIVE_CITIES=""` y `DEFAULT_CANARY_CITIES=""` quedan alineados, `ACTIVE_TRADING_CITIES` queda fósil como fuente de verdad, `BLOCKED_CITIES` se sostiene como override manual de seguridad estructural y se deja `docs/blocked-cities-rationale-latest.md` como ficha corta. `tools/reference_trader_city_market_cross.py` deja de caer a `legacy_bot_lists` y pasa a usar `runtime_policy_effective_view` más default canónico `shadow`; se regeneran `reference_trader_city_market_cross`, `city_validation_ledger` y `city_promotion_gate`, desaparece `untracked` de la capa derivada y deja de reabrirse drift fósil tipo `Chicago active`. Finalmente se retiran los snapshots stale `normal_pull_check/final_check` de `data/runtime_import_derived` y se crea `docs/next-session-handoff-2026-04-12-blocked-cities-evidence.md` para el siguiente bloque lógico. |
| 2026-04-12 | Explícita | Sesión 148 | telegram/runtime_import/latest | Se cierra `Telegram Correctness` sin tocar `bot.py`. Primero se respetan los dos preflights canónicos (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`), que siguen en `error=0`. Luego `tools/city_validation_ledger.py` pasa a leer por defecto `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` desde `data/runtime_import/` en vez de `data/` local, para que `city-intelligence` deje de nacer en falso `runtime_inputs_missing`. Sobre esa base, `tools/city_intelligence_daily_summary.py` se reancla a `runtime_policy_effective_view` y `system_alignment_check_operational` para publicar la historia vigente: runtime read-only manifestado, preflight operacional verde, `blocked=10`, `canary=6`, `shadow=14`, `active=0`, sin `blocking_operational_collision`; además deja de mandar repetir el transporte runtime ya validado. `tools/city_intelligence_telegram_alert.py` y `tools/city_promotion_gate.py` limpian framing stale de monetización y pasan a usar lenguaje de lectura operativa. Validación: `python tools/city_intelligence_pipeline.py --telegram-dry-run` deja `overall_status=ok` y `runtime_inputs_status=available`; `python tools/city_intelligence_daily_summary.py --dry-run` regenera `docs/city_intelligence_daily_summary_latest.md` con el mensaje ya alineado. |
| 2026-04-12 | Explícita | Sesión 147 | docs/dashboard/template/checks | Se cierra `Dashboard Correctness` sin tocar `bot.py`. Primero se regenera `runtime_policy_effective_view` para quitar el bloqueo de frescura operativa, y ambos preflights (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`) vuelven a quedar sin errores. Luego `templates/dashboard.html` deja de presentar `markets_evaluated` como si fueran mercados brutos y pasa a tratarlo explícitamente como alias legacy de `candidates_after_prefilters`; además reencuadra `Road to Real` como checklist heredado, añade una capa de `progreso reciente` apoyada en `cycle_history` y vuelve visible la actividad runtime reciente (ciclos, buys, cierres). Se actualizan `docs/guia-lectura-dashboard.md`, `docs/dashboard-telegram-human-layer-readout-2026-04-11.md` y se crea `docs/dashboard-correctness-readout-2026-04-12.md`. Validación final: `python verify_before_deploy.py` en `643/643`. Se actualizan también `CONTEXTO.md`, el roadmap del módulo y se deja listo `docs/next-session-handoff-2026-04-12-telegram-correctness.md`, dejando explícito que el siguiente bloque debe abrirse como sesión limpia nueva y que `Opus` no hace falta por ahora. |
| 2026-04-12 | Explícita | Sesión 146 | docs/roadmap/handoff | Se mejora el módulo `human-reading-alignment` para que el criterio ya no sea solo correctness técnica, sino también utilidad humana y cierre anti-drift. `docs/human-reading-alignment-roadmap-2026-04-12.md` pasa a exigir que Dashboard y Telegram respondan de forma consistente dónde estamos, qué falta para el siguiente escalón, si el sistema va por buen camino y cómo se distinguen corto, medio y largo plazo. También se añade una regla de cierre anti-drift: si una sesión cambia una pieza que afecta lectura humana, debe dejar explícito qué quedó alineado, qué sigue pendiente y cuál es la siguiente sesión limpia. `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` queda reforzado para que la siguiente sesión de Dashboard no persiga solo wiring factual, sino una lectura diaria más útil y menos friccional para el operador. |
| 2026-04-12 | Explícita | Sesión 145 | docs/handoff/roadmap | Se define el módulo `human-reading-alignment` para corregir la capa humana por bloques limpios y sin volver a mezclar dashboard, Telegram, copy y estrategia en una sola sesión. Se crea `docs/human-reading-alignment-roadmap-2026-04-12.md`, que fija la fuente de verdad única (`runtime_policy_effective_view`, `system_alignment_check`, `metrics-funnel-naming`, `runtime_import/*`), las fases `Preflight -> Dashboard Correctness -> Telegram Correctness -> Shared Copy Layer -> Final Verification`, los criterios para cerrar sesión y los casos en los que sí conviene abrir revisión con Opus. También se crea `docs/next-session-handoff-2026-04-12-dashboard-correctness.md` con el prompt exacto para la siguiente sesión limpia dedicada solo a `Dashboard Correctness`, incluyendo lecturas mínimas, preflight, hallazgos confirmados y Definition of Done. El reparto de modelos queda explícito: Codex ejecuta y cierra, Sonnet ayuda en auditoría/copy compacta, Opus solo entra si aparece conflicto real de fuente de verdad o arquitectura. |
| 2026-04-11 | Explícita | Sesión 144 | docs/read-only/alignment | Se completa la auditoría read-only de Dashboard y Telegram contra la capa canónica actual. Los dos preflights (`python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational`) siguen en `ok=7, warning=1, error=0`, pero el contraste revela drift humano real: el snapshot local del dashboard sigue contando una topología legacy/local (`4` activas: `Atlanta`, `Buenos Aires`, `Chicago`, `Dallas`; `0` ciclos; `0` shadow; `0` cierres) que contradice la `runtime_policy_effective_view` vigente (`active_effective_count=0`, `canary=6`, `shadow=14`) y la observación runtime de `20` ciclos con `4` buys reales y `4` cierres. Además, `templates/dashboard.html` sigue llamando "Mercados escaneados" al alias legacy `markets_evaluated`, rompiendo el contrato de naming del funnel. En Telegram, `docs/city_intelligence_daily_summary_latest.md` queda stale en el viejo framing `runtime_inputs_missing` aunque la capa canónica actual ya parte de `runtime_import` manifestado y ledger disponible. Se crean `docs/dashboard-telegram-human-layer-audit-2026-04-11.md` y `docs/dashboard-telegram-human-layer-readout-2026-04-11.md`; la recomendación explícita es hacer `correctness de lectura` antes de una sesión de copy/UI. |
| 2026-04-11 | Explícita | Sesión 141 | docs/read-only/scoreboard | Se refresca el snapshot runtime por la vía canónica read-only (`tools/railway_runtime_snapshot_pull.ps1`) y se confirma base limpia para throughput: `runtime_import_manifest.json` queda con `pulled_at=2026-04-11T10:52:35Z`, `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` cierran en `ok=7, warning=1, error=0`, sin `blocking_operational_collision`. Sobre esa base se completa una observación extendida de `Step 5` en `docs/step5-throughput-observation-extended-2026-04-11.md`: ventana de `20` ciclos, `raw_markets_fetched ~330`, `candidates_after_prefilters=307`, `condition_filtered_out=285`, `candidates_with_edge=4`, `trades_executed=4`, con cuello aún dominado por `date/price/condition`. La lectura honesta es que `auto_canary` no es puro etiquetado porque las `4` compras reales del tramo salen de ciudades hoy canary (`Atlanta`, `Shanghai`, `Seoul`, `Tokyo`) y las `4` cierran como `RESOLVED_WIN` por `+$1.69`, pero la conversión sigue siendo demasiado intermitente para abrir monetización o policy. Se crean además `docs/controlled-monetization-gate-2026-04-11.md` y `docs/throughput-observation-readout-2026-04-11.md` para dejar el gate de una futura discusión de monetización controlada con bankroll `$25` y un readout corto de cierre. |
| 2026-04-11 | Explícita | Sesión 139 | docs/handoff | Se crea `docs/next-session-handoff-2026-04-11-dallas-claim.md` para abrir una sesión corta enfocada exclusivamente en Dallas como último `blocking_operational_collision`, sin tocar `bot.py`, runtime ni policy live. El handoff incluye además un segundo bloque listo para usar como prompt de revisión a Opus una vez terminada la tarea de Dallas, de modo que la siguiente revisión estratégica parta ya del paquete completo: alignment base, collision barrier, Phase 6.5 y cleanup final de Dallas. |
| 2026-04-11 | Explícita | Sesión 139 | tools/docs/read-only | Mini `Phase 6.5` implementada para endurecer la barrera de colisiones sin tocar `bot.py`, policy live, thresholds, bankroll ni `city_policy_state.json`. `tools/runtime_policy_effective_view.py` ahora clasifica `collision_noise`, `documented_drift` y `blocking_operational_collision`; `tools/reference_trader_city_market_cross.py` deja de arrastrar claims legacy de policy cuando existe la effective view; `tools/system_alignment_check.py` deja de bloquear por `collision_count > 5` y pasa a bloquear por `blocking_operational_collision_count > 0`. Resultado: el preflight `observe` mejora a `ok=7, warning=1, error=0`, el `runtime_ledger` pasa a `ok`, el drift fuerte de `cross` sobre las canaries se limpia, y el bloqueo operacional queda aislado en un único blocker duro: `Dallas` (`env active` vs `runtime auto_shadow`). Se documenta el cambio en `docs/phase6-5-collision-severity-hardening-2026-04-11.md` y se actualizan roadmap y reglas de preflight. |
| 2026-04-11 | Explícita | Sesión 138 | docs/prompt | A partir del readout post-Opus/post-Phase-6 se prepara `docs/claude-opus-prompt-collision-barrier-followup-2026-04-11.md`, un prompt corto y limpio para una nueva revisión de Opus. El prompt deja explícito que la review original de alignment ya ocurrió, que el foco ya no es reabrir wiring base, y que la nueva pregunta es cómo pasar con seguridad desde la barrera `collision_count=17 > 5` hacia una futura discusión operacional o de monetización controlada. |
| 2026-04-11 | Explícita | Sesión 138 | docs/readout | Sesión read-only enfocada exclusivamente en clasificar la barrera `collision_count=17 > 5` después de Opus y de `Phase 6`, sin reabrir alignment base ni tocar policy/throughput. Se crea `docs/collision-barrier-readout-post-opus-phase6-2026-04-11.md`, que separa las colisiones en tres buckets: ruido aceptable por diseño (`shadow` efectivo vs `cross=untracked`), drift documental/cross stale que contamina futuras lecturas (`Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo` como canaries efectivas que `cross` sigue viendo como `shadow`), y blockers reales de discusión operacional (`Dallas` por `env active` vs `runtime shadow`; `Chicago` y `Buenos Aires` por `cross active` vs `effective shadow`). La conclusión deja claro que el `17` actual es una alarma conservadora pero no un diagnóstico de severidad: el subconjunto realmente bloqueante es más pequeño y debe encuadrarse antes de cualquier debate de monetización o policy. |
| 2026-04-11 | Explícita | Sesión 137 | docs/handoff | Cierre de sesión orientado a trazabilidad post-Opus. Se crea `docs/next-session-handoff-2026-04-11-collision-barrier.md` para abrir una sesión limpia enfocada exclusivamente en clasificar la barrera `collision_count=17 > 5` sin reabrir alignment base ni mezclar monetización, throughput o policy. El handoff deja además el puente explícito para una futura revisión de Opus: la base ya revisada está en `docs/opus-review-throughput-alignment-2026-04-10.md`, y todo el trabajo posterior relevante quedó cerrado en sesiones `134-136`. |
| 2026-04-11 | Explícita | Sesión 136 | read-only validation | Se ejecuta el siguiente paso lógico tras `Phase 6`: regenerar `runtime_policy_effective_view` desde el snapshot manifestado y volver a correr el preflight en modo `operational`. La frescura deja de ser el bloqueo principal (`generated_at=2026-04-11T09:38:56+00:00`), y el sistema expone la barrera real: `collision_count=17` frente al umbral `5`, con `ok=6`, `warning=1`, `error=1`. El estado operativo queda clarificado: el alignment ya está suficientemente endurecido para mostrar que no se puede abrir una discusión de throughput/policy todavía, no por artefactos viejos sino por divergencia efectiva demasiado alta. |
| 2026-04-11 | Explícita | Sesión 135 | tools/docs/read-only | Se implementa la mini `Phase 6` de `Decision Preflight Hardening` recomendada por Opus, sin tocar `bot.py`, `city_policy_state.json`, thresholds, allowlists, bankroll ni policy live. `tools/system_alignment_check.py` gana `--decision-mode observe/operational`, separa las salidas `latest` normales de las operacionales (`data/system_alignment_check_operational.json`, `docs/system_alignment_check_operational_latest.md`), añade `prompt_semantic_scan`, y endurece el modo `operational` con bloqueo por SLO de frescura del effective view (`6h`). Se crean `docs/bot-funnel-counter-contract-2026-04-11.md` para mapear counters legacy de `bot.py` a nombres canónicos del funnel y `docs/decision-preflight-rules-2026-04-11.md` para fijar las reglas `observe` vs `operational`, el umbral de colisiones y la regla humana de no decidir por PnL con `<20` trades cerrados. Se actualizan roadmap, phase closeout, artifact map, checklist, handoff y prompt de checkpoint. Estado final: `observe => ok=6, warning=2, error=0`; `operational => ok=6, warning=1, error=1`, bloqueando correctamente cualquier discusión operativa con la foto runtime actual. |
| 2026-04-11 | Explícita | Sesión 134 | tools/docs/read-only | Se resuelve el warning restante de targets del paquete de alineación sin tocar `bot.py`, `city_policy_state.json`, thresholds ni allowlists. `tools/city_intelligence_pipeline.py` deja atrás el string plano `tracker_targets` y pasa a exponer `runtime_derived_targets`, `exploratory_targets` y `tracker_targets` como listas; las targets derivadas salen de `data/runtime_policy_effective_view.json` y con el snapshot actual quedan `Atlanta`, `Munich`, `New York City`, `Seoul`, `Shanghai` y `Tokyo`, mientras `Chicago` queda como exploratory. `tools/city_intelligence_service.py` y `tools/city_intelligence_railway_service.py` se alinean con `CITY_INTELLIGENCE_EXPLORATORY_TARGETS`, `docs/city-intelligence-railway-service.md` documenta el contrato nuevo y `tools/system_alignment_check.py` pasa a exigir listas explícitas y ausencia de overlap. Tras regenerar `data/city_intelligence_pipeline.json`, `docs/city_intelligence_pipeline_latest.md`, `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`, el preflight queda en `ok=3`, `warning=2`, `error=0`; desaparece el warning de `city_intelligence_targets` y solo permanecen los warnings aceptados de divergencias policy/cross. En la misma sesión se ejecuta `Step 5` en modo observación read-only y se documenta `docs/step5-throughput-observation-2026-04-11.md`: el sistema sigue viendo `~330` mercados brutos por ciclo, pero el cuello dominante reciente no es edge mínimo sino `condition_filtered_out` junto con filtros de fecha/precio; en los últimos `20` ciclos hubo `4` compras en `3` ciclos y `3/3` cierres recientes ganadores por `+$1.31`, sin evidencia nueva que justifique tocar throughput o pedir Opus todavía. Como continuación de esa misma fase, `docs/shadow-opportunity-shortlist-2026-04-11.md` separa la vigilancia shadow real del ruido: `Chicago` queda como principal caso exploratorio a seguir; `Hong Kong` y `Beijing` como secundarios; y las ciudades ya absorbidas por `auto_canary` dejan de contaminar la pregunta de "qué shadow nueva merece atención". La sesión además deja cerrado el marco de trabajo de esta fase con `docs/system-alignment-phase-closeout-2026-04-11.md`, `docs/system-alignment-artifact-map-2026-04-11.md` y `docs/system-alignment-session-checklist-2026-04-11.md`, más la actualización del roadmap y del handoff para que las sesiones siguientes no reabran dudas de fuente de verdad ni dependan de contexto humano largo. |
| 2026-04-10 | Explícita | Sesión 133 | docs/handoff | Sesión corta de preparación para continuar limpio al día siguiente. Se crea `docs/next-session-handoff-2026-04-10.md` con el prompt exacto de arranque: leer `AGENTS.md`, Sesión 132 de `CONTEXTO.md`, correr `python tools/system_alignment_check.py`, revisar los docs latest y atacar solo el warning restante de targets (`runtime_derived_targets` vs `exploratory_targets`) sin tocar `bot.py`, `city_policy_state.json`, thresholds ni allowlists. `docs/system-alignment-lean-roadmap-2026-04-10.md` se actualiza para que su bloque “Cómo empezar una sesión nueva” ya no apunte al viejo Step 1 sino al estado actual del roadmap. |
| 2026-04-10 | Explícita | Sesión 132 | tools/docs/read-only | Steps 2-4 del roadmap LEAN de alineacion, sin Opus porque no se toca riesgo ni runtime: `tools/runtime_policy_effective_view.py` genera una vista read-only unica de policy efectiva (`data/runtime_policy_effective_view.json`, `docs/runtime_policy_effective_view_latest.md`) combinando snapshot manifestado + listas env declaradas. Validacion: Dallas queda `env_declared_mode=active`, `runtime_policy_mode=auto_shadow`, `effective_mode=shadow`, `collision_flag=true`; las 6 canaries runtime quedan `effective_mode=canary`; `active_effective_count=0`. Se crea `docs/metrics-funnel-naming.md` para fijar `raw_markets_fetched`, `candidates_after_prefilters` alias legacy `markets_evaluated`, `condition_filtered_out`, `candidates_with_edge`, `candidates_selected`, `trades_executed` y `shadow_opportunities_observed`. Se crea `tools/system_alignment_check.py`, que escribe `data/system_alignment_check.json` y `docs/system_alignment_check_latest.md`; estado actual `error=0`, `ok=2`, `warning=3` por divergencias policy/cross explicitas y targets de `city-intelligence` aun no etiquetados como runtime-derived/exploratory. Punto recomendado de cierre antes de Step 5 o target tagging. |
| 2026-04-10 | Explícita | Sesión 131 | tools/Railway read-only | Step 1 del roadmap LEAN de alineacion: manifest runtime atomico y bijectivo. `tools/railway_runtime_snapshot_pull.ps1` pasa a construir el snapshot en un directorio temporal, escribir `runtime_import_manifest.json` al final, validar que los archivos del temp coinciden con `manifest.files` y reemplazar `data/runtime_import/` solo al completar. El snapshot manifestado se amplia a 10 artefactos runtime (`shadow_city_tracking`, `cycles_history`, `cycle_summary`, `decisions`, `performance`, `postmortem`, `skip_log`, `trade_lifecycle`, `audit`, `city_policy_state`) y deja fuera outputs derivados. `tools/city_validation_ledger.py` falla cerrado con `runtime_inputs_status=manifest_drift` si hay archivo listado faltante, archivo extra, duplicado o mismatch de bytes; gate y pipeline propagan el estado como no disponible. Validado con pull normal Railway read-only (`available`, 10/10, `n_cities=24`), archivo faltante (`listed_file_missing`) y archivo extra (`unlisted_file_present`). No se toca `bot.py`, no se escribe `city_policy_state.json`, no se cambian thresholds ni allowlists. |
| 2026-04-10 | Explícita | Sesión 130 | docs/Railway read-only | Auditoría operativa de throughput y alineación antes de pedir revisión a Opus. Se confirma con artefactos live de `polymarket-bot` que las 3 compras limpias recientes ganaron (`Atlanta`, `Shanghai`, `Seoul`, `+$1.31` total), pero que el sistema quedó casi sin throughput: sigue encontrando `~330` mercados brutos, mientras `markets_evaluated=12-26` es post-filtros; Dallas está en `ACTIVE_TRADING_CITIES` pero runtime la resuelve como `auto_shadow`, por lo que no hay ciudad `active` efectiva y el trading depende solo de canaries. Se documenta el embudo de skips, la desalineación de targets/volúmenes entre `polymarket-bot`, `city-intelligence` y `phase5`, y el requisito de manifest runtime atomico antes de automatizar transporte. Se crean `docs/throughput-alignment-audit-2026-04-10.md` y `docs/claude-opus-prompt-throughput-alignment-review-2026-04-10.md`, y luego el prompt se amplía para pedir a Opus una hoja de ruta LEAN de estandarización sistémica: contratos canónicos, fuentes de verdad, naming del funnel, manifests, staleness, targets y checks pre-decision. La respuesta de Opus se incorpora en `docs/opus-review-throughput-alignment-2026-04-10.md`: `GO WITH CHANGES`, pero cableado primero, no throughput; roadmap en 5 pasos (manifest bijectivo, runtime policy effective view, naming del funnel, system alignment check, observación honesta). Se crea `docs/system-alignment-lean-roadmap-2026-04-10.md` como checklist único de arranque para sesiones nuevas. No se toca `bot.py`, policy runtime, thresholds ni allowlists. |
| 2026-04-10 | Explícita | Sesión 127 | tools/docs/Railway read-only | Auditoría LEAN del transporte runtime read-only tras el GO de Opus al fail-closed endurecido. Railway muestra tres volúmenes separados (`polymarket-bot-volume`, `city-intelligence-volume`, `phase5-visibility-volume`) y la CLI no expone read-only en `volume attach/update`, por lo que se descarta montar directamente el volumen del bot en `city-intelligence`. Se crea `tools/railway_runtime_snapshot_pull.ps1` para hacer pull local read-only vía SSH desde `polymarket-bot` de `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json` hacia `data/runtime_import/`, con manifest. El ledger contra ese snapshot sale `runtime_inputs_status=available`, `n_cities=22`, `actionable=1`; Shanghai ya muestra `edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`, pero sigue `policy_mode=shadow` porque el ledger aún no parsea `city_policy_state.json`. Se documenta el nuevo cuello semántico y se crea prompt para Opus antes de implementar `runtime_policy_mode`. |
| 2026-04-10 | Explícita | Sesión 126 | tools/docs | Hardening pre-transporte del fail-closed tras la segunda revisión de Opus. `tools/city_validation_ledger.py` mueve la dependencia de `bot` a import lazy posterior al chequeo de inputs runtime, de modo que la rama `runtime_inputs_missing` puede escribirse sin cargar `bot.py`; si el import lazy falla con inputs presentes, degrada a fail-closed incluyendo `bot_module` en `missing_runtime_inputs`. `tools/city_intelligence_pipeline.py` cambia la prioridad de estados para que `runtime_inputs_missing` prevalezca incluso sobre `partial_failure`. `docs/system-architecture-city-intelligence-2026-04-10.md` aclara que `cycles_history.jsonl` no es requisito v0 del fail-closed, sino input posterior de staleness/auditoría. Se actualiza el prompt de revisión `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md`; validación local mantiene `overall_status=runtime_inputs_missing` y rama disponible funcional con placeholders. |
| 2026-04-10 | Explícita | Sesión 125 | tools/docs | Primer paso LEAN implementado tras la revisión de Opus: `city-intelligence` falla cerrado cuando faltan artefactos runtime del bot, sin tocar `bot.py` ni trading core. `tools/city_validation_ledger.py` valida `shadow_city_tracking.json`, `audit.json` y `city_policy_state.json`; si faltan, escribe `runtime_inputs_status=missing`, `missing_runtime_inputs`, `cities=[]` y `bottleneck_counts.runtime_inputs_missing=1`. `tools/city_promotion_gate.py` propaga `gate_status=runtime_inputs_missing`; `tools/city_intelligence_pipeline.py` marca `overall_status=runtime_inputs_missing`; alertas y daily summary explican que no hay acceso runtime y no se puede concluir por ciudad. Validación local con `python tools/city_intelligence_pipeline.py --telegram-dry-run` y `python tools/city_intelligence_daily_summary.py --dry-run`; se crea `docs/claude-opus-prompt-city-intelligence-fail-closed-review-2026-04-10.md` para que Opus revise antes de decidir transporte runtime read-only. |
| 2026-04-10 | Explícita | Sesión 124 | docs | Incorporación de la revisión adversarial de Opus sobre la arquitectura `polymarket-bot`/`city-intelligence`, sin tocar `bot.py` ni implementar código. Opus devuelve `GO WITH CHANGES` y fuerza correcciones importantes: `city_validation_ledger.py` ya importa `bot` y consume constantes runtime, el bug de Shanghai es plumbing (`required=False` + `available=False` descartado) antes que semántica, `policy_mode` viene del cross analítico y no de `city_policy_state.json`, el ledger puede omitir ciudades solo-runtime al iterar solo `cross.city_rows`, y los drift detectors propuestos aún no tienen productor/consumidor. Se actualiza `docs/system-architecture-city-intelligence-2026-04-10.md` con fail-closed como primer cambio futuro recomendado y se crea `docs/opus-review-system-architecture-city-intelligence-2026-04-10.md` para trazabilidad. |
| 2026-04-10 | Explícita | Sesión 123 | docs | Definición documental de la arquitectura canónica entre `polymarket-bot`, `city-intelligence` y `phase5-visibility`, sin tocar `bot.py` ni trading core. Se crea `docs/system-architecture-city-intelligence-2026-04-10.md` con arquitectura actual factual, arquitectura objetivo, fuentes de verdad, contratos de datos, loops de feedback, drift detectors, decisiones abiertas, diagrama Mermaid y rol objetivo de `phase5-visibility` como capa experimental/legacy a fusionar o archivar, no como core. Se crea también `docs/claude-opus-prompt-system-architecture-city-intelligence-2026-04-10.md` para revisión adversarial antes de implementar cualquier import/snapshot runtime. |
| 2026-04-10 | Explícita | Sesión 122 | Railway read-only | Auditoría live del loop Shanghai entre `city-intelligence` y `polymarket-bot`. Se confirma que `city-intelligence` está sano pero usa un volumen separado sin `shadow_city_tracking.json`, `cycles_history.jsonl` ni `audit.json`, así que su ledger queda ciego a la evidencia runtime. En el volumen del bot principal, `Shanghai` sí tiene huella real en `shadow_city_tracking.json`: `markets_seen=84`, `edge_hits=19`, `cycles_seen=30`, `best_edge_pct=38.7`, `last_seen_at=2026-04-10T08:00:42Z`. Además `city_policy_state.json` muestra que Shanghai fue autopromovida a `auto_canary` el `2026-04-06T12:33:22Z` por `19` edges y `15` ciclos, por lo que la premisa de Shanghai como shadow puro ya no representa el runtime live. Queda documentado en `docs/shanghai-shadow-live-audit-2026-04-10.md`; siguiente paso: alinear `city-intelligence` con evidencia runtime del bot principal antes de Austin/Wuhan. |
| 2026-04-10 | Explícita | Sesión 121 | local | Auditoría adversarial del estado de `city-intelligence` tras la revisión de Claude. Se confirma localmente que no existen `data/shadow_city_tracking.json`, `data/cycles_history.jsonl` ni `data/audit.json`, por lo que el ledger no puede acumular edge/NOAA propio y todos los `edge_evidence` siguen en cero. `Shanghai` sigue siendo el único caso formal en `shadow_validation`, pero esa etiqueta aún no es operativamente útil sin huella shadow. Se regenera `tools/city_intelligence_pipeline.py --telegram-dry-run` sin refrescar probe/censo para corregir `docs/city_intelligence_pipeline_latest.md`, que queda alineado con señal usable. La decisión metodológica es no entrar todavía en Austin/Wuhan: el siguiente paso correcto es auditar en Railway si el shadow de Shanghai está alimentando `shadow_city_tracking.json` y `cycles_history.jsonl`. |
| 2026-04-09 | Explícita | Sesión 120 | local | Sesión separada de auditoría del cuello real post-censo en `city-intelligence`, sin tocar `bot.py` ni trading core. Se demuestra que `reference_trader_city_market_cross.json` estaba stale respecto a `directional_trader_enrichment.json`, se regeneran `reference_trader_city_market_cross`, `city_validation_ledger` y `city_promotion_gate`, y el diagnóstico deja de colapsar en `trader_input_*`: el ledger actualizado distribuye `trader_discovery=12`, `market_visibility=5`, `source_fidelity=3`, `shadow_validation=1`. La conclusión operativa queda afinada: `Shanghai` es el único caso cuyo bloqueo útil ya es `shadow_validation`; `Austin` y `Wuhan` siguen frenadas por `source_fidelity`. Además se ajusta `tools/city_promotion_gate.py` para que el gate siga el bottleneck real del ledger y no confunda `needs_shadow_validation` con casos que todavía están en `source_fidelity` o `market_visibility`. |
| 2026-04-09 | Explícita | Sesión 119 | local + Railway | Investigación nueva sobre el censo comparable y validación live del cambio mínimo recomendado por Opus. Se crean `docs/comparable-trader-census-audit-2026-04-09.md` y `docs/claude-opus-prompt-comparable-trader-census-audit-2026-04-09.md`, se demuestra con datos live que el `0 traders after filter` venía de mirar solo `20` mercados top-volume y no de ausencia real de comparables, y Opus valida que primero hay que ampliar el universo a `200`. Se actualizan los defaults de `city-intelligence` a `200`, se cambian targets live a `Chicago,Dallas,Seattle,Munich,Madrid`, y Railway confirma una corrida real a las `18:00 UTC` con `--refresh-census --census-markets 200`, `overall_status=ok`, `signal_health=usable_signal` y `quality_reference_traders=9`. El servicio queda estabilizado otra vez con `CITY_INTELLIGENCE_REFRESH_CENSUS=false`, y el siguiente frente decidido pasa a ser auditar si el cuello real ahora es `trader_discovery` o `shadow_validation`. |
| 2026-04-09 | Explícita | Sesión 118 | local | Auditoría técnica del proxy local `127.0.0.1:9`: se confirma que no viene de variables persistentes de Windows, perfiles de PowerShell, `.vscode`, `git` ni `npm`, sino del proceso actual lanzado por Codex en VS Code (`CODEX_SANDBOX_NETWORK_DISABLED=1`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_vscode`, `PATH` con `.sbx-denybin` y binario de la extensión). Se añaden `tools/run_clean_network.ps1`, `tools/polymarket_api_probe.py` y `docs/local-network-proxy-audit-2026-04-09.md` para limpiar solo el proceso hijo, ejecutar verificaciones con red real y restaurar el entorno al salir. Validación final fuera del sandbox: el probe del repo devuelve `200` en `trades?limit=1` y `positions?...`. |
| 2026-04-09 | Explícita | Sesión 117 | local + Railway | Se despliega en Railway un servicio nuevo `city-intelligence` para ejecutar la capa de mejora continua del sistema de city intelligence sin tocar `bot.py`. Se crean `tools/city_intelligence_service.py`, `tools/city_intelligence_daily_service.py`, `tools/city_intelligence_railway_service.py` y `docs/city-intelligence-railway-service.md`, se provisiona volumen dedicado `city-intelligence-volume` en `/app/data`, se fijan variables (`RAILPACK_START_CMD`, horas `0/6/12/18 UTC`, resumen diario `09:00 UTC`, targets `Shanghai,Chicago,Seoul`, Telegram) y el despliegue `cf189b91-ac6a-4d29-a771-5c81abc13d4c` queda en `SUCCESS`, durmiendo hasta `00:00 UTC` para la primera corrida. |
| 2026-04-08 | Explícita | Sesión 116 | local | Se corrige un warning técnico detectado en logs live del bot principal: `datetime.utcnow()` en el bloque de salud del dashboard/focus se sustituye por `datetime.now(timezone.utc)` y se normaliza `_last_cycle` como datetime aware UTC antes de calcular `hours_ago`. No cambia trading ni scheduler; `verify_before_deploy.py` vuelve a cerrar en `643/643`. |
| 2026-04-08 | Explícita | Sesión 115 | local | Se documenta el siguiente gran frente del proyecto en `docs/city-intelligence-automation-roadmap-2026-04-08.md`: una automatización read-only para aprender de traders exitosos comparables y convertir esa evidencia en recomendaciones por ciudad. Además se deja `docs/claude-opus-prompt-city-intelligence-validation-2026-04-08.md` como prompt listo para que Claude Opus valide estratégicamente el enfoque antes de que Codex implemente. |
| 2026-04-08 | Explícita | Sesión 114 | local + Railway | Se despliega en Railway un servicio separado `phase5-visibility` dentro de `enchanting-respect` para ejecutar periódicamente la pipeline read-only de fase 5. Se crean `tools/phase5_visibility_service.py` + `docs/phase5-visibility-service.md`, se añade bootstrap automático desde `seed_data/phase5/`, se provisiona volumen dedicado `phase5-visibility-volume` en `/app/data`, se fijan variables/Telegram y el despliegue final queda validado con `overall_status=ok`, `visibility_snapshots=2` y `simultaneous_visibility_count=0`. |
| 2026-04-08 | Explícita | Sesión 113 | local | Se crea `tools/phase5_visibility_telegram_alert.py` junto con `docs/phase5-visibility-telegram-alert.md` para enviar una alerta one-shot por Telegram cuando aparezca una coincidencia nueva `Shanghai + Chicago` en el tracker de visibilidad. La etapa queda integrada en `tools/phase5_visibility_pipeline.py` con persistencia anti-spam en `data/phase5_visibility_alert_state.json`. |
| 2026-04-08 | Explícita | Sesión 112 | local | Se crea `tools/phase5_visibility_pipeline.py` junto con `docs/phase5-visibility-pipeline.md` para automatizar en un solo comando la fase 5 read-only. La primera corrida deja `data/phase5_visibility_pipeline.json` + `docs/phase5_visibility_pipeline_latest.md`, ejecuta con éxito tracker, snapshot de Shanghai, benchmark de Chicago y comparador final, y resume `dominant_gap=market_visibility_and_selection` con `simultaneous_visibility_count=0`. |
| 2026-04-08 | Explícita | Sesión 111 | local | Se crea `tools/city_probe_visibility_tracker.py` junto con `docs/city-probe-visibility-tracker.md` para persistir la visibilidad de `Shanghai` y `Chicago` a partir de snapshots del `settlement_fidelity_probe`. La primera corrida deja `data/city_probe_visibility_tracker.json` + `docs/city_probe_visibility_tracker_latest.md` y confirma `1` snapshot, `0` coincidencias simultáneas, `Shanghai visible=1` y `Chicago visible=0`. Desde aquí la comparación deja de depender de fotos aisladas y pasa a una base acumulativa. |
| 2026-04-08 | Explícita | Sesión 110 | local | Se crea `tools/shanghai_vs_chicago_comparator.py` junto con `docs/shanghai-vs-chicago-comparator.md` para comparar directamente la ciudad puente `Shanghai` y el benchmark `active` `Chicago`. La primera corrida deja `data/shanghai_vs_chicago_comparator.json` + `docs/shanghai_vs_chicago_comparator_latest.md` y concluye que el gap dominante observado hoy es `market_visibility_and_selection`: Shanghai aparece en el flujo de mercados local mientras Chicago no, así que la siguiente mejora debe ir por observabilidad comparativa de mercados visibles antes de deducir timing o edge de forecast. |
| 2026-04-08 | Explícita | Sesión 109 | local | Se crea `tools/chicago_active_benchmark.py` junto con `docs/chicago-active-benchmark.md` para dejar a `Chicago` como benchmark operativo simétrico frente a `Shanghai`. La primera corrida deja `data/chicago_active_benchmark.json` + `docs/chicago_active_benchmark_latest.md` y concluye `benchmark_strength=credible`, `observability_status=ok`, `next_action=use_as_active_benchmark`: aunque el probe local no mostraba mercados de Chicago en ese momento, la ciudad sigue siendo un benchmark útil por ser `active` y estar respaldada por dos referencias comparables fuertes. |
| 2026-04-08 | Explícita | Sesión 108 | local | Se crea `tools/city_phase5_contrast.py` junto con `docs/city-phase5-contrast.md` para comparar `Shanghai`, `Chicago` y `Seoul` con el mismo motor de snapshot. La primera corrida deja `data/city_phase5_contrast.json` + `docs/city_phase5_contrast_latest.md` y concluye que `Shanghai` sigue siendo la ciudad puente principal, pero el siguiente paso correcto pasa a ser `continue_shanghai_observability_plus_active_contrast`: mantener `Shanghai` como foco principal mientras se la contrasta explícitamente con `Chicago` como benchmark `active`. |
| 2026-04-08 | Explícita | Sesión 107 | local | Se implementa `tools/shanghai_shadow_test.py` junto con `docs/shanghai-shadow-test.md` y se ejecuta la primera corrida local del extractor. El snapshot queda en `data/shanghai_shadow_test.json` + `docs/shanghai_shadow_test_latest.md` y concluye `signal_status=building`, `data_quality=ok`, `next_action=expand_observability`: la ciudad sigue siendo prometedora, pero en local todavía faltan huellas de `shadow tracking` y `audit` para justificar un salto mayor. |
| 2026-04-08 | Explícita | Sesión 106 | local | Se crea `docs/shanghai-shadow-test-design.md` como contrato operativo del siguiente bloque. El documento fija por qué `Shanghai` es la ciudad puente principal, qué debe medir un test `shadow` read-only, qué artefactos producir y qué criterios usar para distinguir `stay shadow`, `expand observability` o `prepare controlled test`, sin tocar aún `bot.py` ni la estrategia. |
| 2026-04-08 | Explícita | Sesión 105 | local | Se crea `tools/city_watch_reinforced.py` + `docs/city-watch-reinforced.md` para condensar la fase siguiente en tres ciudades prioritarias: `Shanghai`, `Chicago` y `Seoul`. El readout reforzado deja a `Shanghai` como ciudad claramente prioritaria para `prepare_shadow_test_design`, `Chicago` como `watch_live_active_city` y `Seoul` como `expand_shadow_observability`, cerrando la fase de priorización y apuntando ya a un bloque concreto de diseño de test en shadow. |
| 2026-04-08 | Explícita | Sesión 104 | local | Se completa la fase 4 con `tools/city_watchlist_phase4.py` + `docs/city-watchlist-phase4.md`. La nueva watchlist ordena ciudades por acción recomendada: `Shanghai` queda como `prepare_test`, `Chicago` como `watch_active`, `Ankara` como `review_block_reason`, y detrás aparecen `Austin`, `Wuhan` y `Seoul` como ciudades a observar de cerca. El proyecto sale de investigación abierta y entra en modo de priorización operativa por ciudad. |
| 2026-04-08 | Explícita | Sesión 103 | local | Se completa la fase 3 con `tools/reference_trader_city_market_cross.py` + `docs/reference-trader-city-market-cross.md`. El cruce entre referencias reales, `city policy` y snapshot de mercados deja una shortlist operativa: `Shanghai` aparece como mejor ciudad puente (`shadow`, referencias reales + mercados visibles en probe), `Ankara` como mismatch fuerte de research/policy (`blocked` pero muy poblada por referencias), y `Chicago` como principal ciudad `active` tocada por traders de alta prioridad. |
| 2026-04-08 | Explícita | Sesión 102 | local | Se completa la fase 2.5 del plan operativo con `tools/directional_trader_enrichment.py` + `docs/directional-trader-enrichment.md`. La herramienta enriquece la shortlist comparable del censo direccional con posiciones activas/cerradas, `win rate` y `cash PnL`, y deja una primera jerarquía de referencias reales en `data/directional_trader_enrichment.json`. Primera corrida útil sobre el top 5: `Entire-Hood`, `Academic-Maniac`, `Motionless-Stalk` y `Massive-Distribution` salen como `high_priority_reference`; `White-Donkey` queda como `candidate_reference`. |
| 2026-04-08 | Explícita | Sesión 101 | local | Se ejecutan de verdad las fases 1 y 2 del plan de monetización incremental. `tools/settlement_fidelity_probe.py` queda validado tras corregir un `400 Bad Request` de Open-Meteo y ya produce `data/settlement_fidelity_probe.json` + `docs/settlement_fidelity_probe_latest.md` con cobertura `12/12` de forecast en la primera muestra. Además nace `tools/directional_trader_census.py` con `docs/directional-trader-census.md`: la primera corrida bruta muestra que el universo direccional está dominado por compras extremas cerca de `1.0`, y al alinearlo al rango `0.20-0.80` se reduce a una shortlist de `10` traders comparables, concentrados sobre todo en `Shanghai`, `Ankara` y `Wuhan`. |
| 2026-04-08 | Explícita | Sesión 100 | local | Se abre la fase operativa posterior al research cruzado Codex + Opus. Se crea `docs/strategic-monetization-plan-2026-04-08.md` como plan maestro por fases (`Settlement Fidelity Probe v1` -> `Directional Trader Census v1` -> gate de decisión) y se implementa `tools/settlement_fidelity_probe.py` junto con `docs/settlement-fidelity-probe.md`. La herramienta nueva es read-only, no toca `bot.py`, y deja preparado un snapshot reproducible de mercados direccionales con precio implícito, forecast `Open-Meteo`, metadata de resolución y proxy observado NOAA cuando exista. |
| 2026-04-08 | Explícita | Sesión 99 | local | Se documenta un estudio completo de Codex sobre traders comparables al universo actual de `polymarket-bot` en `RESEARCH_CODEX_TRADERS_2026-04-08.md`. El informe fija taxonomía de traders weather/prediction markets, compara esa taxonomía contra la estrategia vigente, detecta que el pipeline histórico de traders del repo sigue sesgado hacia `exact/range` mientras el bot solo monetiza `at_or_above/at_or_below`, y prioriza como siguiente research reconstruir el mapa de wallets realmente comparables antes de tocar forecast core o execution. |
| 2026-04-08 | Explícita | Sesión 98 | local | Se crea `docs/ESTRATEGIA_OPERATIVA.md` como documento canónico de la estrategia vigente para comparar el sistema con otros traders. Resume universo operado, condiciones permitidas, filtros de entrada, cálculo de probabilidad y edge, sizing `Half-Kelly`, modos `active/canary/shadow/blocked`, contrato de fuentes y capas de evaluación. Queda como base explícita para la próxima investigación orientada a monetización. |
| 2026-04-08 | Explícita | Sesión 97 | local | Validación live post-ciclo del rediseño `WR observado direccional`: Railway confirma que `shadow_city_tracking.json` ya usa el esquema nuevo y persiste `edge_hit`, pero `directional_history` sigue vacío porque el ciclo `08:00 UTC` tuvo `0 shadow` y `15 condition_filtered`; la tarjeta `0/72` queda reinterpretada como estado transitorio y no como WR real observado. Además se alinea Telegram para distinguir `ACTIVE` vs `CANARY`, renombrar `candidatos evaluados`/`shadow con edge`, separar `NOAA-verificado` del histórico total en `/accuracy`, aclarar el rol de NOAA en `/noaa`, y se documenta el contrato de fuentes `Open-Meteo decide / NOAA mide / Weather Underground resuelve`. Suite final `643/643`; siguiente sesión orientada a investigar traders y monetización. |
| 2026-04-07 | Explícita | Sesión 96 | local | Hotfix del dashboard tras el deploy del `WR observado direccional`: `build_dashboard_road_to_real()` seguía iterando `recent_opps` sin definirla y Railway caía con `NameError` al abrir `/`. Se repone la lectura desde `directional_history` y `verify_before_deploy.py` añade una regresión específica; suite final `643/643`. |
| 2026-04-07 | Explícita | Sesión 95 | `57be884` | Deploy a Railway del rediseño del `WR observado direccional`: el servicio arranca con código nuevo que ya incluye `directional_history`, pero el volume aún no había sido reescrito tras el restart. Se deja checklist post-ciclo para validar que `shadow_city_tracking.json` materializa la base persistente, persiste `edge_hit` y que la métrica live deja de depender de `recent_opportunities`. |
| 2026-04-07 | Explícita | Sesión 94 | local | Auditoría y rediseño del `WR observado direccional`: se confirma que el join shadow→NOAA estaba sesgado por leer `recent_opportunities` (ventana volátil) y por perder `edge_hit` al persistir. `shadow_city_tracking.json` gana `directional_history` como base persistente de señales shadow direccionales deduplicadas, el join normaliza `date` a `YYYY-MM-DD` y `verify_before_deploy.py` sube a `642/642`. |
| 2026-04-07 | Explícita | Sesión 93 | local/live | Se documenta otro episodio recurrente de auth rota en Railway (`Unauthorized` con tokens presentes y config writable), se recupera con `doctor -> reset -> launch-login -Browserless`, se valida restart live del servicio y se corrige `run_observability_alerts()` para dejar de mandar alertas legacy de `baja accuracy` y pasar a revisión NOAA-verificada en `active/canary`. |
| 2026-04-07 | Explícita | Sesión 92 | local | Se afinan y externalizan los umbrales de `Alertas activas` para la era NOAA-verificada: ciudades malas exigen `n>=5`, activas sin NOAA útil solo alertan por debajo de 3 casos, el join shadow→NOAA pide 20 señales y 10 observaciones NOAA, y el WR shadow no avisa hasta 8 resueltas. |
| 2026-04-07 | Explícita | Sesión 91 | local | El bloque `Alertas activas` deja de priorizar `accuracy baja` histórica y pasa a usar señales de la era NOAA-verificada: ciudades con NOAA-verificado malo, ciudades activas sin NOAA interpretable y problemas del join shadow→NOAA, manteniendo el legacy solo como nota contextual. |
| 2026-04-07 | Explícita | Sesión 90 | local | El bloque `Estado por ciudad` del dashboard se reorganiza en grupos semánticos (`Operativas y candidatas`, `Shadow observadas`, `Sin NOAA util`, `Fuera de observacion`) con una tabla por grupo y `main_reason` visible bajo cada ciudad para mejorar lectura humana y consumo por LLM. |
| 2026-04-07 | Explícita | Sesión 89 | local | `blocked` vuelve a reservarse para ciudades sin NOAA observable; las ciudades con NOAA configurable dejan de quedar fuera del scan por listas/overlays viejos y el dashboard separa rendimiento NOAA-verificado vs legado, además de recordar el estado abierto de `Salud del sistema`. |
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
| 2026-04-03 | Explícita | Sesión 71 | `—` | Quick wins Control Center (v10.6.10, sin bump): QW1 elimina bloque `legacy-focus-shell` (código muerto); QW2 mueve card Drift Open-Meteo a capa 3 tras Trofeos; QW3 reordena capa 2 — NOAA+Decision engine pasa a inmediatamente después de Estado operativo; QW4 añade alarma «sin ciclo en >12h» en `build_dashboard_focus_center()` leyendo `cycle_summary.json`; QW6 mini-cards PnL/WR muestran «esperando muestra» si `closed_count < 5`; QW7 Readiness+Desbloqueos colapsados en `<details>`. Verificado en inicio de sesión: `shadow_city_tracking.json` y `city_policy_state.json` presentes en Railway Volume. `verify_before_deploy.py`: 506/506. |
| 2026-04-03 | Explícita | Sesión 70 | `—` | Auditoría completa del Control Center dashboard (v10.6.10): 6 bloques analizados (fidelidad de datos, utilidad operativa, UX/IA, motor de ciudades, alertas Telegram, valor estratégico). Hallazgos críticos: `shadow_tracking` posiblemente no persiste en Volume, WR Chicago sesgado por 3 filas legacy `open`, NOAA/Decision engine al final de capa 2 cuando es el limitante dominante, `readiness_score` opaco (propuesta de 3 gates). Entregables: `docs/control-center-audit.md`, `docs/control-center-roadmap.md` (QW1-7, M1-5, R1-3, I1-3), `docs/control-center-next-session.md` con prompt listo. Sin cambios de código. |
| 2026-04-03 | Explícita | Sesión 66 | `—` | Implementación local del auto-bloqueo real por ciudad sin tocar trading/NOAA/scheduler: `city_policy_state.json` añade `auto_blocked_cities` con `action/reason/metrics/from_mode/triggered_at`, `get_effective_city_mode()` prioriza ese estado sobre la allowlist activa, `sync_city_policy_state()` registra `active/canary -> blocked` con evidencia persistida, dashboard/decision engine leen la política y la suite pasa en `506/506`. Sin push/deploy todavía; siguiente paso validar en Railway. |
| 2026-04-02 | Explícita | Sesión 58 | `—` | Cierre operativo sin tocar el bot: se fija como siguiente prioridad la auditoría de la captura del `Mission HUD`, se formaliza la regla `1 sesión = 1 tarea` con contexto mínimo, se añade una sección de `token economics` para Codex + Claude Code y se crea `.codex/config.toml` del proyecto con `medium` por defecto y perfiles `low/deep/max`. Sin deploy ni cambios de trading/NOAA. |
| 2026-04-02 | Explícita | Sesión 59 | `—` | Cierre completo: `python verify_before_deploy.py` vuelve a pasar `483/483`, se versionan el saneamiento local de `trade_lifecycle/trade console`, el handoff y los guardrails de contexto/tokens, y se hace `commit + push` a `origin/main`. No se tocan reglas de trading ni NOAA; queda pendiente revalidación live del nuevo push. |
| 2026-04-03 | Explícita | Sesión 72 | `—` | Cobertura funcional de la alarma `sin ciclo en >12h` en `build_dashboard_focus_center()`: el test fuerza ausencia de `cycle_summary.json`, valida `incidents` + `badge="warn"` y sincroniza `agent_events.jsonl` con la sesión documentada más reciente. Suite local `507/507`, sin tocar trading/NOAA/scheduler. |
| 2026-04-04 | Explícita | Sesión 76 | `—` | Implementación local de Camino A shadow-only: filtro `ALLOWED_CONDITIONS` para dejar solo `at_or_above/at_or_below`, `range/exact` enviados a shadow tracking con `edge_hit=False`, sigma empírica por ciudad con fallback global, `MIN_EDGE=15.0`, `condition_filtered` en dashboard/Telegram/cycle_summary y suite `515/515`; sin tocar scheduler/NOAA/trade_lifecycle/deploy ni env vars Railway. |
| 2026-04-06 | Explícita | Sesión 82 | `93c8b2e` `1daec87` | Diagnóstico estratégico completo + corrección de modelo + reactivación Dallas. (1) Verificación empírica: NOAA `daily-summaries/TMAX` = WU daily high exactamente para KORD — no se necesita scraping WU. (2) Sesgo Open-Meteo medido con 13 casos NOAA en producción: Atlanta `Bias=+1.38°C`, Chicago `Bias=+1.40°C`, Dallas `Bias≈0`. (3) `FORECAST_BIAS_C` implementado en `estimate_prob_with_city` (`mu = forecast_max + bias`). (4) Dallas sigma D0 `0.21→0.57°C`, samples D0 `2→3`. (5) `MIN_PRICE 0.08→0.20`, `MAX_PRICE 0.92→0.80`. (6) `ACTIVE_TRADING_CITIES=Dallas` en Railway (estaba `NONE`), `auto_blocked_cities` limpio. (7) NOAA decoupling (Codex): `_iter_recent_noaa_cycle_markets` + `_get_noaa_candidate_dates` + `scanned_markets` en cycle_summary — recoge observaciones sin BUY. Suite `620/620` (+8 tests). |
| 2026-04-06 | Explícita | Sesión 85 | `—` | Política local de ciudades `shadow-first`: `sync_city_policy_state()` vuelve a degradar `active/canary -> shadow`, `blocked` queda reservado a descartes reales, y el overlay legado `auto_blocked_cities[action=auto_block]` se migra al vuelo a `auto_shadow_cities` para evitar casos tipo Dallas. Dashboard/copy distinguen `Sin muestra` vs `Sin NOAA` y `Descartes reales` vs `Shadow degradada`. `verify_before_deploy.py` cierra en `628/628`; falta push/deploy. |
| 2026-04-07 | Explícita | Sesión 87 | `—` | Hardening local de `agent_events`: `load_agent_events()` acepta sesiones serializadas como `session_72`, extrae el sufijo numérico, mantiene la deduplicación y evita el warning live `invalid literal for int()`. `verify_before_deploy.py` amplía cobertura funcional y cierra en `637/637`. |
| 2026-04-07 | Explícita | Sesión 88 | `—` | Mitigación local de Open-Meteo rate limit: `get_forecast()` añade caché por `lat/lon`, fallback `stale` acotado y cooldown explícito al detectar `HTTP 429`, recortando el fan-out duplicado entre auditoría legacy y escaneo principal. `verify_before_deploy.py` amplía cobertura y cierra en `639/639`. |

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

---

## Sesión 73 — quick wins Control Center: QW3 + QW5 + QW6 (4 abr 2026)

**Disparador:** completar el bloque de quick wins pendientes de Fase 1 del roadmap `docs/control-center-roadmap.md` en una sola sesión.

**QW5 — Timestamp "último fetch NOAA exitoso":**
- `build_dashboard_forecast_quality()` ya devolvía `last_record_display` (línea 4114 de `bot.py`), pero el template no lo mostraba.
- Se añadió `<div><dt>Último fetch NOAA</dt><dd>{{ dashboard.forecast_quality.last_record_display }}</dd></div>` en el `metric-list` de "Calidad Forecast Observada (NOAA)".
- Riesgo: ninguno. Solo template.

**QW3 — Reordenar capa 2: NOAA y Decision engine primero:**
- Orden anterior: stats de promoción → bankroll/estado operativo → NOAA (line 418) → readiness → trading stats.
- Orden nuevo: stats de promoción → NOAA → trading stats → bankroll/estado operativo → readiness.
- Implementado con un script Python que reordena bloques por line numbers exactos (sin editar contenido). 1689 líneas antes = 1689 líneas después.

**QW1, QW2, QW7 — ya estaban hechos:**
- `legacy-focus-shell`: no encontrado en el template (ya eliminado en sesión anterior).
- Legacy drift: ya estaba en línea 1464 (fuera de capa 2, en zona reporting).
- Readiness y desbloqueos: ya estaba en `<details>` (colapsado por defecto).

**QW6 — "esperando muestra" en Drawdown:**
- PnL y Win rate ya tenían la condición `closed_count < 5`. Drawdown no.
- Se añadió el mismo guard: cuando `closed_count < 5`, muestra "esperando muestra / menos de 5 cierres" en lugar de `drawdown_display`.

**Validación:** `verify_before_deploy.py` = 507/507 tras todos los cambios.

**Fase 1 del roadmap Control Center completada.** Siguiente: M3 (cerrar 3 filas Chicago legacy open que sesgan WR).

---

## Sesión 74 — tabs de Observabilidad capa 2 en dashboard (4 abr 2026)

**Disparador:** convertir el mega-card monolítico de `Observabilidad (capa 2)` en 3 tabs legibles, sin tocar Python ni `bot.py`, siguiendo el patrón de activación ya existente en `static/dashboard.js`.

**Cambios implementados:**

- `templates/dashboard.html` envuelve el bloque de Observabilidad en `data-tab-shell` con `data-default-panel="obs-noaa"`.
- Se añaden 3 tabs: `NOAA`, `Ciudades`, `Decisiones`, reutilizando `focus-tab-bar`, `focus-tab`, `focus-panel`, `data-panel-target` y `data-panel`.
- La vista `NOAA` agrupa el resumen de calidad forecast y la tabla de últimos 20 casos.
- La vista `Ciudades` agrupa el resumen de estado por ciudad, el universo operativo, seguimiento/referencia y bloqueadas.
- La vista `Decisiones` agrupa decision engine, reglas de promoción/salida, ranking operacional, overlays canary/shadow, observación, shadow reciente y transiciones.

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocó ningún archivo Python;
- no se modificó `static/dashboard.js` porque el patrón genérico ya soportaba el nuevo shell de tabs;
- no se corrieron tests, al ser una reestructuración solo de plantilla.

---

## Sesión 75 — auditoría forecast accuracy Fase 1 (4 abr 2026)

**Disparador:** crear un script local para auditar si el edge histórico del bot era ficticio por sigma demasiado estrecha o forecast Open-Meteo malo, sin tocar `bot.py`, trading, scheduler, deploy ni variables Railway.

**Cambios implementados:**

- Se añade `tools/forecast_accuracy_audit.py`, ejecutable localmente con:
- `python tools/forecast_accuracy_audit.py`
- `python tools/forecast_accuracy_audit.py --postmortem-source railway`
- El script carga `postmortem.json` desde copia local, dashboard JSON o Railway via `tools/railway_safe.ps1`, recupera temperatura observada con NOAA (`daily-summaries/TMAX -> global-hourly/TMP`) y cae a Open-Meteo historical si NOAA no devuelve dato.
- Calcula por trade `forecast_error = forecast_max - observed_real`, `prob_with_real_temp`, `real_edge`, `would_have_traded`, `outcome_correct`, `sigma_empirical_used` y `would_have_traded_empirical_sigma`.
- Genera `data/forecast_accuracy_raw.json` y `docs/forecast_accuracy_audit.md` con resumen global, tabla crítica `city × days_ahead`, resumen por ciudad, sesgo `YES/NO`, porcentaje de `real_edge < 0`, porcentaje de trades que no pasarían `MIN_EDGE` con sigma empírica, y top 5 peores gaps de edge ficticio.
- Como `postmortem.json` live tiene muchas filas con `question=""`, el script infiere `threshold_c` por grid-search contra `our_prob` cuando hay `condition/forecast_max/side/days_ahead` pero no `question`, y marca ese fallback en `threshold_source`.

**Resultado observado en la primera corrida live:**

- Fuente: `railway:/app/data/postmortem.json`
- `127` registros input, `34` trades cerrados analizables con BUY context suficiente, `82` cierres omitidos por `missing_forecast_max`, `11` todavía `open`.
- Sobre esos 34 trades: `WR ex-post 52.9%`, `LOSS_TOTAL 41.2%`, `forecast_error_mean -1.444 °C`, `sigma global 2.248 °C`, `real_edge < 0` en `23.5%`, `11.8%` no pasarían `MIN_EDGE` con sigma empírica, sesgo `YES=61.8% / NO=38.2%`.
- Hallazgo más accionable para Opus Fase 2: Chicago muestra sigma empírica claramente por encima del modelo (`3.074 °C` en agregado ciudad; `2.573 °C` en day 0 y `2.587 °C` en day 1 frente a `1.2-1.5 °C` del modelo), mientras Atlanta/Dallas/Buenos Aires no presentan ese gap de forma tan marcada con esta muestra.

**Limitación importante:**

- Esta auditoría aún no explica sola el `79% LOSS_TOTAL` sobre `91` cierres de serie v10.6, porque `postmortem.json` contiene `82` cierres legacy/orphan sin `forecast_max/question/date` recuperables desde la propia fila.
- Si Opus necesita cerrar cobertura sobre los 91 trades completos, la siguiente fase técnica debería enriquecer esos cierres huérfanos desde `performance.json` y/o `trade_lifecycle.json`, manteniendo explícito qué parte es observación directa vs reconstrucción.

**Validación:**

- `python -c "from pathlib import Path; import ast; ast.parse(Path('tools/forecast_accuracy_audit.py').read_text(encoding='utf-8')); print('AST OK')"` -> `AST OK`
- `python tools/forecast_accuracy_audit.py --help` -> parser OK
- `python tools/forecast_accuracy_audit.py --postmortem-source railway --output-json data/forecast_accuracy_raw.json --output-md docs/forecast_accuracy_audit.md` -> `analyzed=34`, `missing_observed=0`

**Límite de alcance respetado:**

- no se tocó `bot.py`;
- no se tocaron trading, NOAA del bot, scheduler, execution ni env vars;
- no hubo push ni deploy;
- sí se actualizaron `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y se debe registrar evento en `agent_events.jsonl` para cerrar trazabilidad.

---

## Sesión 76 — Camino A direccional + sigma empírica en shadow-only (4 abr 2026)

**Disparador:** aplicar el diagnóstico de Opus Fase 2 sobre pérdidas en `range/exact` sin reactivar trading, sin tocar scheduler/NOAA/trade_lifecycle/deploy y manteniendo `ACTIVE_TRADING_CITIES=NONE` en Railway.

**Cambios implementados:**

- `bot.py` añade `ALLOWED_CONDITIONS` con default `at_or_above,at_or_below`.
- En el ciclo principal, antes de `estimate_prob`, los mercados `range/exact` quedan filtrados con log explícito, contador `condition_filtered_skip` y envío a `shadow_city_tracking` como observación `edge_hit=False`, evitando descartarlos silenciosamente.
- `get_uncertainty(days_ahead, city=None)` pasa a priorizar sigma empírica por ciudad solo si `n>=3`; si la ciudad/día no tiene muestra suficiente, cae a `EMPIRICAL_SIGMA_GLOBAL`, y solo si tampoco hay bucket global usa la sigma original v10.3 como fallback final.
- Se preserva `estimate_prob()` intacta y se añade una envoltura mínima `estimate_prob_with_city(...)` para inyectar el contexto de ciudad en BUY y re-eval sin cambiar la fórmula.
- `MIN_EDGE` default sube de `7.0` a `15.0`.
- `cycle_summary.scan` añade `condition_filtered`; Telegram de ciclo, `/log`, `/info` y el dashboard muestran cuántos mercados se filtraron por condición.
- `templates/dashboard.html` expone `Condición filtrada` en `Estado operativo`.
- `verify_before_deploy.py` añade tests para `ALLOWED_CONDITIONS`, `get_uncertainty(city=...)`, fallback global si `n<3`, `MIN_EDGE=15.0` y persistencia de `condition_filtered`.

**Límites de alcance respetados:**

- no se tocó scheduler, NOAA, `trade_lifecycle`, deploy ni variables Railway;
- no se cambió `ACTIVE_TRADING_CITIES` local ni Railway;
- los mercados filtrados por condición no se descartan: quedan en shadow tracking.

**Validación:**

- `python verify_before_deploy.py` → `515/515`

---

## Sesión 77 — rediseño Control Center shadow-only direccional (4 abr 2026)

**Disparador:** rehacer la capa visual del dashboard para que Pablo pueda leer en desktop si el bot está sano, si las señales shadow direccionales son buenas y cuánto falta para volver a REAL, dejando la parte Python/backend en manos de Claude en paralelo.

**Cambios implementados por Codex (solo capa UI/tests/docs):**

- `templates/dashboard.html` queda organizado alrededor de:
- barra `Road to Real`;
- `Bloque 1` compacto de estado del bot;
- `Bloque 2` de señales shadow direccionales con columnas `Condicion / Side / Edge / Forecast / Mercado / Resolucion`;
- `Bloque 3` colapsable de salud del sistema.
- Se quitan del flujo visible principal Mission HUD gamificado, trofeos, desbloqueos, scoreboards/rivalry, trade console larga y la tabla larga de ciclos.
- `static/dashboard.css` añade estilos para `progress-bar-big`, `road-to-real-checklist`, `cards-3` y `notice-accent`.
- `verify_before_deploy.py` gana un check estructural para `build_dashboard_road_to_real`, validaciones del nuevo layout y un stub del builder en el harness de `build_dashboard_snapshot()`.
- `docs/control-center-roadmap.md` queda actualizado con el estado de este rediseño y deja como item futuro subir la frecuencia de ciclos a `4-6x/dia` solo después de que el dashboard sea legible.

**Límites de alcance respetados:**

- no se tocó scheduler, NOAA fetch, `manage_positions`, reglas de entrada/salida ni variables Railway desde esta capa Codex;
- `bot.py` sí aparece modificado en el worktree, pero ese cambio corresponde a trabajo paralelo de Claude y no se revirtió;
- `templates/dashboard_legacy.html` quedó creado por un intento fallido de mover el template y Windows devuelve `Access denied` al borrarlo; es un backup no usado por Flask.

**Validación:**

- `python verify_before_deploy.py` -> `516/516`

## Sesión 80 — R3 skip_log backend + analyzer offline + validación producción (5 abr 2026)

**Disparador:** cerrar R3 del roadmap Fase 3 (log de skips por ciclo). El bot evalúa ~150 candidatos por ciclo y solo ejecuta 0-3 trades reales; los 147+ skips eran información estratégica tirada a la basura. R3 materializa esa información en `data/skip_log.jsonl` para poder decidir en el futuro (con datos) si bajar `MIN_EDGE`, expandir allowlist, o recalibrar sigma.

**Split Claude ↔ Codex sobre contrato `docs/control-center-r3-contract.md` (commit 096a680):**

- **Claude (Opus) — backend + tests:**
  - `bot.py`: helpers a nivel de módulo `_make_skip_entry`, `_skip_log_rotate_if_needed`, `append_skip_log_entries` (batch + rotación 20 MB + tolerancia a I/O roto), `_skip_log_rotated_files`, `read_skip_log_last_n_cycles`, `read_skip_log_since`.
  - `run_cycle` instrumentado: `cycle_id = now.strftime("%Y-%m-%dT%H:%M")` capturado una sola vez al inicio, `skip_log_entries = []` bucket local, un único `append_skip_log_entries(...)` al final del ciclo envuelto en try/except.
  - 17 `skip_reason` instrumentados en los `continue` existentes del scan loop. Flag `shadow_override_flag` propagado en `parsed.update(...)` desde Loop A para que Loop B distinga `fuera_allowlist` vs `shadow_only_override` (fix `c8c8e73`).
  - `verify_before_deploy.py`: 64 tests nuevos, estáticos y funcionales (exec del source en namespace limpio contra tempdir).

- **Codex — analyzer offline + docs:**
  - `tools/analyze_skip_log.py`: CLI con flags `--last-n-cycles`, `--since`, `--city`, `--csv`, `--min-edge`. Lee `data/skip_log.jsonl` + rotados directamente con `json.loads(line)`, sin importar `bot.py`. 3 secciones: distribución, trend, near-misses.
  - `docs/skip-log-analyzer.md` con ejemplos.

**Validación:**

- `python verify_before_deploy.py` → `612/612`
- commits en `main`: `096a680` (contrato R3), `4b37cfe` (analyzer Codex), backend R3 (Claude)
- Pablo forzó ciclo vía `/forzar` en Telegram → `data/skip_log.jsonl` generó 660 filas en `cycle_id 2026-04-05T20:09`. Analyzer via SSH funciona.

**Hallazgo estratégico del primer ciclo real:** cero filas llegan a Loop B con edge calculado — todos los skips caen en Loop A (filtros tempranos). `below_min_edge`/`kelly_too_low`/`shadow_only_override` solo aparecerán cuando haya mercados futuros válidos en ciudades activas. R3 listo para análisis longitudinal cuando acumule 10-30 ciclos.

## Sesión 79 — R1 frontend Control Center: 3 gates por ciudad (5 abr 2026)

**Disparador:** cerrar la parte frontend de R1 mientras Claude trabajaba el backend en paralelo, consumiendo el contrato estable de `docs/control-center-r1-contract.md` sin tocar `bot.py`.

**Cambios implementados por Codex (solo frontend):**

- `templates/dashboard.html` reemplaza el bloque `{# -- City states compact -- #}` que iteraba `dashboard.city_observation.active_rows` por una tabla compacta sobre `dashboard.city_decisions.ranking_rows`.
- La nueva tabla muestra `Historial`, `Shadow` y `NOAA` con `gate_a`, `gate_b` y `gate_c` como autoridad del JSON, manteniendo la columna de `state_label`/`state_badge`.
- Cada gate expone `detail` vía `title` HTML y se añade debajo un glosario corto con los significados de `Limpio/Malo/Sin datos`, `Lista/Construyendo/Vacío` e `Interpretable/Parcial/Sin NOAA`.
- `static/dashboard.css` añade un ajuste mínimo `.city-gates` para anchos y badges, reutilizando `badge-good/accent/warn/bad/muted`.
- El bloque posterior de `dashboard.city_observation.blocked_rows` queda intacto.

**Límites de alcance respetados:**

- no se tocó `bot.py` bajo ninguna circunstancia;
- no se modificó `verify_before_deploy.py`;
- no hubo bump de versión;
- no se añadió microajuste UX extra para el caso Dallas (`gate_a=bad` + `gate_b=ready`), porque los gates independientes son parte explícita del diseño y la columna de estado ya sintetiza el veredicto.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` -> `548/548`
- commit/push a `main`: `c382000`
- mensaje: `feat(dashboard): R1 frontend — 3 gates visuales por ciudad`

## Sesión 80 — R3 skip_log: analyzer offline Codex + validación end-to-end (5 abr 2026)

**Disparador:** cerrar la parte Codex del contrato `docs/control-center-r3-contract.md` mientras el backend R3 se implementaba en paralelo, y luego validar el analyzer contra el primer `skip_log.jsonl` real generado en producción.

**Cambios implementados por Codex:**

- `tools/analyze_skip_log.py` añade un CLI stdlib-only para leer `data/skip_log.jsonl` y archivos rotados `data/skip_log.YYYY-MM-DD.jsonl` directamente con `json.loads(line)`, sin importar `bot.py`.
- El analyzer tolera líneas malformadas con warning a `stderr`, respeta campos `null` del schema R3 y soporta `--last-n-cycles`, `--since`, `--city`, `--csv` y `--min-edge`.
- La salida queda organizada en tres secciones: distribución de `skip_reason` por ciudad, trend temporal por razón comparando ventanas de ciclos y near-misses para `below_min_edge`.
- `docs/skip-log-analyzer.md` documenta instalación, flags, interpretación de cada sección y casos de uso operativos.

**Límites de alcance respetados:**

- no se tocó `bot.py`;
- no se modificó `verify_before_deploy.py`;
- no se importó el bot desde el analyzer;
- no se dejaron archivos temporales persistentes en `data/` tras la verificación local.

**Validación y trazabilidad:**

- `python -c "import ast; ast.parse(open('tools/analyze_skip_log.py').read())"` -> OK
- `python tools/analyze_skip_log.py --last-n-cycles 5` -> OK con fixture local mínimo de 3 filas
- validación posterior sobre Railway: el primer ciclo real produjo `660` filas en `data/skip_log.jsonl` (`cycle_id 2026-04-05T20:09`) y el analyzer respondió correctamente por SSH
- commit local Codex: `4b37cfe`
- mensaje: `feat(r3): analyzer offline de skip_log.jsonl`

## Sesión 81 — Control Center simplificado + verify saneado sobre main (6 abr 2026)

**Disparador:** ejecutar los ítems delegables de `docs/control-center-simplify-plan.md` sin agrupar cambios, integrar la cadena completa en `main` y dejar `verify_before_deploy.py` verde antes de cualquier deploy.

**Cambios integrados por Codex:**

- Se mergearon en orden local y luego a `origin/main` siete PRs aisladas del plan:
  - `#5` limpieza de duplicados visuales del dashboard;
  - `#1` badge de modo sin falsa alarma en shadow/dry;
  - `#2` eliminación de la columna `Resolucion` del bloque de señales shadow;
  - `#6` lenguaje llano para scan y etiquetas de condición;
  - `#3` normalización de `forecast_display`/`forecast_badge`, incluyendo corrección del mojibake `°`;
  - `#4` supresión de `city_low_accuracy` como alerta operativa en `SHADOW_ONLY/DRY_RUN`, moviéndola a anotación fija en rendimiento;
  - `#7` gateo NOAA cuando la muestra todavía es insuficiente.
- El conflicto textual de `bot.py` entre `#3` y `#6` se resolvió manteniendo todos los helpers nuevos y combinando correctamente `_strip_resolution_fields(row)`, `_build_shadow_forecast_fields(row)` y `condition_label` en la comprehension de `build_dashboard_city_decisions`.
- `verify_before_deploy.py` se endureció para reflejar el dashboard simplificado y el entorno real de sandbox:
  - actualiza asserts HTML que seguían esperando `Resolucion` y textos viejos del bloque shadow;
  - inyecta `_dashboard_mode_label` en el harness funcional de `get_dashboard_alert_summary`;
  - usa un tempdir local del repo para R3 y monkeypatch de `os.replace` en la prueba de rotación, evitando falsos rojos por restricciones del sandbox Windows.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` -> `612/612`
- commit final de saneamiento del verify en `main`: `df4ff60`
- mensaje: `test(verify): harden merged dashboard checks`
- `git push origin main` publicado con toda la cadena ya integrada

**Notas de alcance:**

- no hubo bump de versión;
- no se tocaron los 3 gates de R1 ni la lógica funcional de `skip_log`;
- no se desplegó a Railway en esta sesión.

## Sesión 83 — Dallas desbloqueado + arquitectura modos ciudad + contrato NOAA (6 abr 2026)

**Disparador:** revisar el primer ciclo Dallas con modelo corregido (bias + sigma 0.57°C), diagnosticar por qué no operaba, y diseñar la hoja de ruta NOAA para todas las ciudades.

**Hallazgos:**

- Dallas bloqueada en producción por `sync_city_policy_state` — re-añadida a `auto_blocked_cities` en cada arranque porque WR=11.8% (<25%) dispara `removable_active=True`. El label "(WU vs Open-Meteo)" en el log es hardcodeado, no refleja una comprobación WU activa.
- El loop era: cleanup manual → bot arranca → `run_observability_alerts()` → `sync_city_policy_state()` → Dallas re-bloqueada antes del primer ciclo.
- Atlanta y Chicago estaban en `BLOCKED_CITIES` por error de diseño: `BLOCKED_CITIES` corta TODO incluyendo recolección NOAA. Esas ciudades habían dejado de acumular datos NOAA sin que nadie lo notara.
- 26 ciudades en `RESOLUTION_ICAO` sin `noaa_station_id` → no acumulan NOAA aunque estén en shadow.

**Resultado:**

- `CITY_STATS_CUTOFF` env var + `get_city_accuracy()` filtrado por fecha: reset de métricas Dallas sin borrar `postmortem.json`. `verify_before_deploy.py` 626/626 (6 tests nuevos).
- `ALLOWLIST_REMOVE_MIN_TRADES=25` en Railway: barrera de seguridad anti-re-bloqueo hasta n≥25 trades nuevos.
- `CITY_STATS_CUTOFF=Dallas=2026-04-06` en Railway: Dallas arranca con 0 trades en métricas.
- Atlanta y Chicago removidas de `BLOCKED_CITIES` en Railway → vuelven a shadow, siguen acumulando NOAA.
- Norma canónica de modos documentada en `AGENTS.md`, `bot.py` (comentario junto a `BLOCKED_CITIES`) y `CONTEXTO.md`: blocked=datos rotos, shadow=no opera pero observa.
- Contrato Codex `docs/noaa-station-verification-contract.md`: proceso autónomo para verificar estaciones NOAA de las 26 ciudades pendientes via isd-history.csv + GHCND API.

**Commits:** `f7abd5b`, `55b6dee`, `0a220ed`
**Railway:** `ALLOWLIST_REMOVE_MIN_TRADES=25`, `CITY_STATS_CUTOFF=Dallas=2026-04-06`, Atlanta/Chicago fuera de `BLOCKED_CITIES`.
**Próximo paso:** Codex ejecuta `docs/noaa-station-verification-contract.md`.

## Sesión 82 — Cierre NOAA decouple en rama de revisión (6 abr 2026)

**Disparador:** cerrar ordenadamente una exploración local sobre NOAA después de detectar que el diff se había trabajado sobre una base de tests antigua respecto a `main`.

**Resultado real al cierre:**

- se creó y publicó la rama `codex/noaa-decouple` para revisión aislada;
- la rama quedó sin delta efectivo de código frente a `main`/`origin/main` al terminar la sesión;
- no se integraron cambios funcionales nuevos en `bot.py` ni `verify_before_deploy.py`;
- se sincronizaron `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl` para dejar trazabilidad explícita de que esta sesión cerró workflow, no producto.

**Validación y trazabilidad:**

- `python verify_before_deploy.py` relanzado antes del push de cierre;
- commit de cierre documental realizado sobre `codex/noaa-decouple`;
- push de la rama de revisión actualizado para dejar la sesión cerrada.

## Sesión 84 — Revalidación NOAA London/Milan sin delta funcional (6 abr 2026)

**Disparador:** revisar dos `noaa_daily_station_id` del commit `9efd8bc` con posible sesgo geográfico antes de seguir confiando en la nueva capa NOAA ampliada.

**Verificación ejecutada:**

- `London -> UKE00107650` se reconsultó en `daily-summaries/TMAX` para `2025-10-01..2026-03-31`: devuelve `149` registros válidos, rango plausible `2.5°C..21.3°C`. En `ghcnd-stations.txt` figura como `HEATHROW` (`51.4789, 0.4489`), a ~`27.8 km` de `EGLC`.
- `Milan -> SZ000009480` también devuelve `151` registros `TMAX`, pero las coordenadas son `46.0, 8.9667` (`LUGANO`, Suiza), a ~`45.0 km` de `LIMC`.
- Se hizo búsqueda dirigida de candidatos italianos cerca de Malpensa en `ghcnd-stations.txt` y luego una ampliación de radio hasta `300 km`. Los candidatos italianos obvios (`ITM00016064 CAMERI`, `ITE00100554 MILAN`, etc.) devolvieron `0` registros `TMAX` para el periodo contractual.

**Resultado:**

- no se modifica `bot.py` en esta sesión;
- London queda validada como `daily` útil;
- Milan se mantiene temporalmente con `SZ000009480` por falta de alternativa italiana con cobertura real en GHCND;
- se documenta explícitamente que el siguiente cuello de botella ya no es el lookup de IDs sino acumular muestra real en `observed_vs_forecast`.

**Validación y cierre:**

- `python verify_before_deploy.py` -> `626/626`
- se sincronizan `CONTEXTO.md`, `HISTORIAL_SESIONES.md` y `agent_events.jsonl`
- no hay commit funcional nuevo de producto en esta sesión; el commit/push de cierre es solo documental

## Sesión 86 — Policy NOAA-verificada vs histórico legacy en ciudades (6 abr 2026)

**Disparador:** convertir en implementación el pendiente explícito de la sesión 85: evitar que la policy de ciudades degrade/promueva usando como evidencia fuerte un histórico malo de una era pre-NOAA-verificada.

**Implementación local:**

- se añade `get_city_policy_metrics()` en `bot.py` para separar cierres por ciudad en `total`, `verified` y `legacy`, usando join `city + date` contra `audit.json -> observed_vs_forecast` con `source=noaa_ncei`;
- `build_dashboard_city_observation()` pasa a exponer `policy_source`, `policy_is_provisional`, `policy_trades`, `verified_trades` y `legacy_trades`, y deja explícito cuando el histórico visible sigue siendo solo legacy/provisional;
- `build_dashboard_city_decisions()` cambia la regla de salida: `active/canary -> shadow` ya no usa el agregado bruto de `get_city_accuracy()`, sino solo histórico **NOAA-verificado** para disparar `remove`;
- si una ciudad activa solo tiene histórico legacy malo, la decision se mantiene en `keep` pero pasa a `Revisar legado / Bajo review` con score más conservador, de modo que no se autodegrada ni queda visualmente “limpia”;
- el soporte de `shadow -> canary` conserva `trades` totales como soporte para no introducir una regresión silenciosa al split `verified/legacy`, pero la degradación sigue exigiendo evidencia NOAA-verificada;
- se endurece el join `city + date` normalizando ambas fechas a `YYYY-MM-DD`;
- `sync_city_policy_state()`, `_compute_city_decisions_for_alerts()`, snapshot y focus dejan de recalcular tres veces la misma capa `city_policy_metrics`.
- `_build_auto_city_shadow_policy()` persiste también el basis de policy (`policy_source`, `policy_trades`, `verified_trades`, `legacy_trades`) para que la degradación guardada conserve contexto de calidad de evidencia.

**Validación y estado:**

- `python verify_before_deploy.py` -> `632/632`
- se añaden tests funcionales que prueban la separación `NOAA-verificado vs legacy` y que una ciudad activa con histórico legacy malo no se degrada automáticamente por esa sola razón
- no se tocó trading core, NOAA fetch core, scheduler ni exits; el cambio queda acotado a la policy, su lectura y su persistencia

## Sesión 87 — Hardening de agent_events live (7 abr 2026)

**Disparador:** corregir el warning repetido en Railway `Error cargando agent_events: invalid literal for int() with base 10: 'session_72'` sin tocar trading, NOAA ni scheduler.

**Implementación local:**

- `load_agent_events()` deja de asumir que `session` siempre llega como entero puro;
- ahora acepta strings tipo `session_72`, extrae el sufijo numérico y normaliza el valor a `72`;
- la clave de deduplicación sigue usando `timestamp + session + agent + type + title normalizado`, pero ya no rompe al leer eventos antiguos o serializados con prefijo textual.

**Validación y estado:**

- `python verify_before_deploy.py` -> `637/637`
- se añade un test funcional con `session="session_72"` para fijar la compatibilidad y asegurar que la carga sigue ordenando y deduplicando correctamente
- impacto esperado: desaparece el warning repetido de `agent_events` en logs y el scoreboard/dashboard vuelve a poder leer esos eventos sin ruido

## Sesión 88 — Hardening HTTP del forecast provider (7 abr 2026)

**Disparador:** tras desaparecer el warning de `agent_events`, los logs live muestran el siguiente cuello de botella real: `Forecast error` con `timeout`, `429 Too Many Requests` y algún `502` durante el ciclo de las `08:43 UTC`.

**Hallazgo operativo:**

- el mismo ciclo reutiliza `get_forecast()` desde `audit_check_open_meteo_forecast_drift()` y luego otra vez desde el escaneo principal;
- eso duplica hits al mismo endpoint/city cuando el proveedor ya está inestable o rate-limited;
- el wrapper anterior reintentaba siempre con espera fija y no distinguía `HTTP 429`.

**Implementación local:**

- `get_forecast()` añade caché en proceso por `lat/lon`;
- si la respuesta sigue fresca, la reutiliza directamente;
- si aparece `HTTP 429`, registra un cooldown explícito y evita seguir martilleando el proveedor;
- si existe una respuesta reciente pero ya no fresca, puede reutilizarla como `stale cache` controlada cuando el fallo es del proveedor.

**Validación y estado:**

- `python verify_before_deploy.py` -> `639/639`
- se añaden tests funcionales para asegurar que la segunda llamada usa caché y que un `HTTP 429` cae a `stale cache` en vez de romper todo el flujo
- no se toca trading, NOAA, scheduler ni sizing; el cambio queda acotado al wrapper HTTP de forecast

## Sesión 128 — Runtime policy mode read-only en city-intelligence (10 abr 2026)

**Disparador:** Opus valida el transporte runtime manual, pero bloquea la automatización porque el ledger ya puede leer los archivos runtime y aun así seguía tratando Shanghai como `shadow` + `candidate_for_canary_validation`, pese a que `city_policy_state.json` la tiene en `auto_canary_cities`.

**Implementación local:**

- `tools/city_validation_ledger.py` lee `city_policy_state.json` en modo read-only y construye `runtime_policy_mode` desde `auto_canary_cities`, `auto_shadow_cities` y `auto_blocked_cities`;
- el ledger conserva la policy analítica previa como `cross_policy_mode` y usa `policy_mode` como policy efectiva cuando runtime está disponible;
- se añade `drift_flags=["policy_divergence"]` cuando runtime y cross discrepan;
- se añaden filas `runtime_only` para ciudades presentes en `city_policy_state.json` pero ausentes en `cross.city_rows`, como Atlanta y Dallas;
- `tools/city_promotion_gate.py` convierte `policy_divergence` en `gate_status=audit_runtime_drift` y evita pedir `review_for_canary` cuando runtime ya decidió canary;
- se crea `docs/claude-opus-prompt-runtime-policy-mode-review-2026-04-10.md` para que Opus revise esta unidad antes de automatizar pull/sync runtime.

**Validación y estado:**

- contra `data/runtime_import/*`: `runtime_inputs_status=available`, `n_cities=24`, `runtime_policy_mode_counts={auto_canary: 6, auto_shadow: 1, runtime_unknown: 17}`, `drift_flag_counts={policy_divergence: 5}`;
- Shanghai queda reconciliada como `policy_mode=canary`, `cross_policy_mode=shadow`, `runtime_policy_mode=auto_canary`, `recommendation=audit_runtime_drift`, `gate_status=audit_runtime_drift`;
- Atlanta aparece como `cross_policy_mode=runtime_only`, `runtime_policy_mode=auto_canary`, `gate_status=observe_runtime_canary`;
- el fail-closed local sigue intacto: sin runtime local, ledger/gate/pipeline devuelven `runtime_inputs_status=missing` / `overall_status=runtime_inputs_missing` y `cities=[]`;
- no se tocó `bot.py`, no se escribió `city_policy_state.json`, no se cambiaron thresholds ni trading core.
- tras el `GO WITH CHANGES` de Opus, se añade hardening mínimo: `base_recommendation`, `base_evidence_status`, `evidence_status=runtime_only` para filas sintéticas, detector `runtime_policy_collision`, auditoría de consumidores de `policy_mode` y nota arquitectónica de que `cross_policy_mode=unknown` + runtime conocido es `policy_divergence` deliberado en v0;
- con los inputs auxiliares refrescados, Dallas aparece como sexto drift real (`cross_policy_mode=active`, `runtime_policy_mode=auto_shadow`), dejando el snapshot validado en `n_cities=25`, `policy_divergence=6`.

## Sesión 129 — Staleness pre-automation de runtime import (10 abr 2026)

**Disparador:** agotado el cupo semanal de Claude/Opus, se decide continuar sin más review externa y ejecutar el siguiente bloque LEAN recomendado antes de automatizar transporte: evitar que snapshots viejos parezcan runtime actual.

**Implementación local:**

- `tools/city_validation_ledger.py` añade `--runtime-manifest` y `--max-runtime-snapshot-age-hours`;
- si los tres runtime files existen pero el manifest falta, no parsea o supera el umbral, el ledger corta en `runtime_inputs_status=stale`, `cities=[]`, `stale_runtime_inputs` y `bottleneck_counts.runtime_inputs_stale=1`;
- `tools/city_promotion_gate.py` propaga stale como `gate_status=runtime_snapshot_stale`;
- `tools/city_intelligence_pipeline.py` propaga `overall_status=runtime_inputs_stale`;
- `tools/city_intelligence_telegram_alert.py` y `tools/city_intelligence_daily_summary.py` distinguen `missing` de `stale` y listan nombres/razones concretas de archivos/manifest.

**Validación y estado:**

- sintaxis validada por AST sin escribir `.pyc`;
- con `data/runtime_import/runtime_import_manifest.json` y umbral alto, el ledger queda `runtime_inputs_status=available`;
- con `--max-runtime-snapshot-age-hours 0.001`, el ledger/gate cortan en `runtime_inputs_status=stale` / `runtime_snapshot_stale`, sin filas por ciudad;
- con partial-missing simulado (faltando solo `city_policy_state`) el ledger/gate/alert cortan en `runtime_inputs_status=missing` y listan exactamente `city_policy_state`;
- local sin runtime sigue fail-closed: `runtime_inputs_status=missing`, `cities=[]`, `overall_status=runtime_inputs_missing`;
- no se tocó `bot.py`, no se escribió `city_policy_state.json`, no se automatizó pull/sync runtime.

## Sesión 85 — Política de ciudades shadow-first y migración Dallas legacy (6 abr 2026)

**Disparador:** auditar la contradicción entre la semántica deseada (`blocked` solo para descartes reales, `shadow` para observación activa) y el comportamiento real donde `sync_city_policy_state()` mandaba `active/canary -> blocked`, dejando casos como Dallas atrapados por `auto_blocked_cities`.

**Hallazgos de auditoría:**

- `get_effective_city_mode()` daba prioridad total a `auto_blocked_cities` sobre `ACTIVE_TRADING_CITIES`, así que una entrada legacy `action="auto_block"` podía dejar una ciudad `blocked` aunque en la práctica solo se quisiera pausarla y seguir observando.
- `sync_city_policy_state()` seguía escribiendo `auto_blocked_cities` cuando `decision == "remove"`, con transición `active/canary -> blocked`.
- El scan trataba `blocked` como descarte duro (`continue` temprano), por lo que esas ciudades salían también del circuito útil de observación.
- El dashboard mezclaba `Sin muestra` y `Sin NOAA` en el gate C y todavía verbalizaba `blocked` y `shadow degradada` demasiado cerca semánticamente.

**Implementación local:**

- se añade normalización del overlay persistido con `_normalize_city_policy_state()`, `_is_real_block_policy()` y `_coerce_shadow_policy_entry()`;
- el legado `auto_blocked_cities[action=auto_block]` migra automáticamente a `auto_shadow_cities` al cargar/guardar, preservando `reason`, `metrics`, `from_mode` y fecha;
- `sync_city_policy_state()` vuelve a degradar `active/canary -> shadow` con `_build_auto_city_shadow_policy()` y transición `action="auto_shadow"`;
- `blocked` queda reservado a descartes reales explícitos (`BLOCKED_CITIES` o `auto_blocked_cities` con acción de bloqueo real);
- el dashboard distingue `Interpretable`, `Parcial`, `Sin muestra` y `Sin NOAA`, renombra el bloque de `blocked_rows` a `Descartes reales`, y presenta `Shadow degradada` como observación activa, no como expulsión dura.

**Validación y estado:**

- `python verify_before_deploy.py` -> `628/628`
- no se tocó trading core, NOAA fetch core, scheduler ni exits, fuera del overlay de política y la presentación
- no hubo mutación live en Railway durante esta sesión; el siguiente paso operativo es push/deploy para que el código nuevo migre overlays legacy en producción

## Sesión 143 — Mapa mental y handoff de Dashboard/Telegram (11 abr 2026)

**Disparador:** dejar una visión más aterrizada del sistema para el usuario y fijar el siguiente frente lógico tras el cierre del alignment base: revisar si la capa humana de lectura (`Dashboard` y `Telegram`) ya está alineada con la arquitectura y los artefactos canónicos actuales.

**Implementación local:**

- se crea `docs/system-mental-model-2026-04-11.md` para resumir el sistema en tres capas:
  - ejecución runtime (`polymarket-bot`)
  - estado observable (`runtime_import`, effective view, funnel, postmortem)
  - inteligencia read-only (`city-intelligence`, checks, readouts, prompts)
- se crea `docs/next-session-handoff-2026-04-11-dashboard-telegram-audit.md` con una sesión read-only ya acotada para auditar Dashboard + Telegram sin mezclarla con policy, monetización ni trading core.

**Conclusión operativa:**

- la arquitectura base ya está suficientemente alineada como para cambiar el foco desde contratos core hacia la capa de lectura humana;
- el siguiente drift relevante, si existe, probablemente esté en wording, alertas o priorización de Dashboard/Telegram;
- por eso el siguiente paso recomendado ya no es otra sesión abstracta de alignment, sino una auditoría concreta de utilidad y coherencia operativa en la UI y las alertas.

## Sesión 142 — Follow-up de throughput sin muestra nueva (11 abr 2026)

**Disparador:** intentar una segunda extensión read-only de `Step 5` tras la observación extendida previa, manteniendo el mismo scope estricto: snapshot manifestado, naming canónico del funnel y cero cambios en `bot.py`, `city_policy_state.json`, policy live, thresholds, allowlists, bankroll o `exact/range`.

**Hallazgo clave:**

- el snapshot runtime sí quedó fresco (`pulled_at=2026-04-11T11:01:40.7730763+00:00`);
- `python tools/system_alignment_check.py` y `python tools/system_alignment_check.py --decision-mode operational` siguieron en `ok=7, warning=1, error=0`;
- pero los artefactos manifestados no traen ciclos nuevos más allá del tramo ya auditado: `cycles_history.jsonl` sigue cerrando en `2026-04-11T08:00:38.111156+00:00` (`cycle_number=64`) y `shadow_city_tracking.updated_at` coincide en `2026-04-11T08:00:38.036104+00:00`.

**Implementación local:**

- no se cambia lógica ni artefacto runtime alguno;
- se deja `docs/step5-throughput-observation-followup-2026-04-11.md` para documentar que el intento de extensión no puede producir `20` ciclos adicionales honestos todavía;
- se deja `docs/throughput-observation-readout-followup-2026-04-11.md` como cierre corto.

**Validación y estado:**

- snapshot manifestado y fresco por vía canónica read-only;
- `system_alignment_check.py` -> `ok=7, warning=1, error=0`;
- `system_alignment_check.py --decision-mode operational` -> `ok=7, warning=1, error=0`;
- `blocking_operational_collision_count=0`;
- no aparece bug nuevo de counters/accounting;
- la siguiente sesión correcta sigue siendo observación read-only cuando existan ciclos runtime realmente nuevos, no correctness ni policy.

## Sesión 140 — Dallas claim cleanup read-only (11 abr 2026)

**Disparador:** limpiar el último `blocking_operational_collision` de Dallas sin tocar `bot.py`, policy live, `city_policy_state.json` ni capas operativas prohibidas.

**Hallazgo clave:**

- el blocker no venía de runtime live;
- `tools/runtime_policy_effective_view.py` seguía sembrando `DEFAULT_ACTIVE_CITIES = "Dallas"` como fallback local cuando no había snapshot explícito del env;
- eso fabricaba un `env_declared_mode=active` heredado que chocaba con `runtime_policy_mode=auto_shadow`, aunque `effective_mode` correcto ya era `shadow`.

**Implementación local:**

- `DEFAULT_ACTIVE_CITIES` pasa a vacío en `tools/runtime_policy_effective_view.py`;
- la herramienta mantiene el soporte para listas env explícitas por argumento, pero deja de promover por defecto un claim declarativo stale;
- se regeneran `data/runtime_policy_effective_view.json`, `docs/runtime_policy_effective_view_latest.md`, `data/system_alignment_check*.json` y `docs/system_alignment_check*_latest.md`.

**Validación y estado:**

- `python tools/system_alignment_check.py` -> `ok=7, warning=1, error=0`
- `python tools/system_alignment_check.py --decision-mode operational` -> `ok=7, warning=1, error=0`
- `blocking_operational_collision_count` baja de `1` a `0`
- Dallas queda alineada como `env=shadow`, `runtime=auto_shadow`, `cross=shadow`, `effective=shadow`
- readout corto dejado en `docs/dallas-claim-readout-2026-04-11.md`

## Sesión 169 — Cross-check edge vs traders + diagnóstico auto-promoción (13 abr 2026)

**Modelo:** Sonnet. **Handoffs:** A y C del índice 2026-04-13.

**Handoff A — Cross-check edge vs trader signals:**
- Se crea `tools/signals_vs_edge_crosscheck.py` (standalone read-only).
- Primera corrida: MATCH=14, BOT_ONLY=2 (Beijing, Chicago), TRADER_ONLY=21. Austin en TRADER_ONLY ✓, Seoul en MATCH ✓.
- 81% de señales de quality traders caen en exact/range (bloqueadas). 8 ciudades TRADER_ONLY tienen conds operables; Austin y Toronto con consenso son las más urgentes.
- Output: `data/runtime_import_derived/signals_crosscheck.jsonl` + `docs/signals-crosscheck-baseline-2026-04-13.md`.

**Handoff C — Diagnóstico trigger auto-promoción:**
- Dallas: `ACTIVE_TRADING_CITIES` null en Railway → código usa default con Dallas → `city_mode="active"` → nunca llega a `promotable_shadow`. Gate `city not in ACTIVE_TRADING_CITIES` también falla.
- Lucknow, Sao Paulo, Istanbul: no en `OBSERVED_AUDIT_CITIES`, 0 trades, nunca en `auto_shadow_cities` → invisibles a `tracked_cities` → `sync_city_policy_state` nunca las evalúa. Gap estructural entre `shadow_city_tracking` y el pipeline de promoción.
- Fixes propuestos (no aplicados): A1=setear `ACTIVE_TRADING_CITIES` explícito en Railway, B1=añadir a `OBSERVED_AUDIT_CITIES` de a una. Decisión de aplicar → Opus.
- Output: `docs/auto-promotion-trigger-diagnosis-2026-04-13.md`.

### Sesión 170 — Blocked Signals Settlement Tracker (Handoff B) (13 abr 2026)

**Modelo:** Sonnet. **Handoff:** B (experimento 2: resolución de señales `exact/range` bloqueadas).

- Se crea `tools/blocked_signals_settlement_tracker.py`: tool standalone read-only que mide la WR implícita de las señales `exact/range` de quality traders que el bot filtra por `condition_filtered`.
- **Algoritmo:** lee `signals.json`, filtra `condition in {exact, range}` con `date <= today-1`, fetch paginado de eventos cerrados via `gamma-api.polymarket.com`, match por título normalizado, calcula `win = close_price >= 0.95` para el lado de la señal.
- **Bug encoding descubierto:** `signals.json` almacena el símbolo `°` como la secuencia corrupta `U+252C U+2591` (`┬░`) en lugar de `U+00B0`. El tool normaliza antes de comparar con la API.
- **Primera corrida (Apr 13 snapshot, cutoff Apr 12):** 19 candidatos `exact/range`, 18 resueltos, 18 wins. **WR = 100.0% (n=18).**
- **Veredicto:** `INSUFFICIENT SAMPLE` (n < 30). Se necesitan >= 30 resoluciones para primer corte, >= 50 para decisión robusta. El tool debe correrse nuevamente cuando haya más días acumulados.
- **Outputs:** `data/runtime_import_derived/blocked_signals_resolutions.jsonl` (append-only, dedup por `match_key`), `docs/blocked-signals-wr-baseline-2026-04-13.md`.
- **No tocar:** `bot.py`, `trader_analyzer.py`, `signals.json`, Railway, trading core.

### Sesión 169 cont. — Crosscheck automatizado + corrección ACTIVE_TRADING_CITIES

**Modelo:** Sonnet. Continuación de la misma sesión.

- Se añade `maybe_run_daily_crosscheck(state)` a `bot.py` (v10.6.12): corre el crosscheck traders vs edge en el primer ciclo de cada día, appenda a `/app/data/signals_crosscheck.jsonl`, manda Telegram diario y aviso one-shot al acumular 7 corridas.
- Usuario aplica `ACTIVE_TRADING_CITIES=NONE` en Railway: elimina el default hardcoded `Chicago,Atlanta,Dallas,Buenos Aires` que trataba esas 4 ciudades como active sin env var explícito. Ahora ninguna ciudad entra en active mode sin declaración humana.
- Backlog documentado: feature canary→active graduation con criterios automáticos + reminder persistente hasta que el usuario actúe. Requiere sesión dedicada Opus.

### Sesión 171 — Fix encoding ° en signals.json (13 abr 2026)

**Modelo:** Sonnet. **Tarea:** bug fix de codificación.

- **Bug:** `trader_analyzer.py` escribía `°` como `┬░` (U+252C U+2591) en `signals.json` en lugar de `°` (U+00B0). Descubierto en sesión 170 al normalizar títulos para el settlement tracker.
- **Root cause:** `api_get()` línea 103 llamaba `json.loads(resp.read())` sin encoding explícito. En Windows con CP437 como code page del sistema, los bytes UTF-8 `\xC2\xB0` se decodificaban como CP437 produciendo `┬░`.
- **Fix:** `json.loads(resp.read().decode("utf-8"))` — una línea en `trader_analyzer.py:103`.
- **Validación:** `verify_before_deploy.py` → 643/643 tests.
- **Versión activa al cerrar:** `v10.6.13` local lista para push/deploy.

### Sesión 172 — Diseño canary→active automation + handoff Opus (13 abr 2026)

**Modelo:** Opus. **Tarea:** diseño estratégico + handoff para sesión limpia Sonnet. Sin tocar `bot.py`, trading core, thresholds, Railway ni policy live.

- **Decisión arquitectónica:** Opción B (notificación Telegram persistente, Pablo aplica manualmente) sobre auto-promoción full. Fundamento: bankroll $25, modelo en recalibración Phase 2, asimetría de riesgo degradar vs promover.
- **Umbrales v1 congelados con justificación explícita:** `canary_trades>=5` (mínimo donde WR≥60% con alguna pérdida es alcanzable en ~5 semanas), `WR>=60%` (margen claro sobre break-even 50%), `PnL>=+$1.00` (recupera ≥1 pérdida canary), `days_since_promotion>=7` (al menos un ciclo semanal completo), `WR_degradation<=45%` (bajo break-even claro).
- **Scope v1 = Bloques 1+2+4:** historial propio canary + integridad lifecycle (detección patrón Atlanta-inconsistency) + anti-flapping (no degradada últimos 14 días).
- **Scope v2 = Bloques 3+5 deferidos:** corroboración externa (signals.json consensus o shadow edge reciente) + gate global post-recalibración (WR sistema ≥50% últimos 30 días). Se añade trigger alarm one-shot que avisa a Pablo por Telegram cuando precondiciones v2 se cumplan (`RECALIBRATION_PHASE2_CLOSED=true` + al menos 1 ciudad en Active + signals.json fresco).
- **Spec completo en `docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md`:** tres módulos (`notify_active_candidates`, `maybe_run_active_degradation`, `maybe_alert_v2_trigger`), Telegram templates (nueva candidata / recordatorio 24h / revocación / degradación / trigger v2), anti-spam (rate limit 22h + revocación automática), detección de acción del usuario via `os.getenv("ACTIVE_TRADING_CITIES")` runtime, overlay nuevo para degradación active→canary (no tocar `sync_city_policy_state`), test checklist con 8+ casos unitarios.
- **Principio de diseño:** bot observa y avisa; Pablo decide y aplica. Asimetría: degradación = auto (protección capital > espera humana), promoción = manual (decisión de capital más consecuente queda con humano).
- **Nota operativa (recurrente):** volumen bajo de trades (~1 canary/semana por ciudad) sigue siendo prioridad paralela. Este módulo ayuda indirectamente (desbloquea sizing active) pero no resuelve throughput de fondo (scan loop filtra demasiado). Anotado para backlog post-implementación.
- **Implementación diferida:** a sesión Sonnet limpia. Opus cierra aquí; Sonnet arranca con el handoff y clear de contexto.

### Sesión 173 — Canary→Active automation v10.6.14 (13 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/handoffs/canary-to-active-automation-handoff-2026-04-13.md`.

- **Tres módulos implementados en `bot.py` (v10.6.13→v10.6.14):**
  - `_detect_atlanta_inconsistency(record)`: helper que detecta el patrón LOSS_TOTAL + RESOLVED_WIN positivo en timeline + post_exit_analysis confirmando win (Bloque 2 integridad).
  - `notify_active_candidates(state)` (Módulo 1): evalúa ciudades en `auto_canary_cities` contra criterios v1 congelados (n≥5, WR≥60%, PnL≥+$1.00, days≥7, integridad OK, Bloque 4 anti-flapping). Alerta Telegram nueva candidata + recordatorio cada 22h + revocación automática + silenciamiento cuando ciudad aparece en `ACTIVE_TRADING_CITIES` runtime.
  - `maybe_run_active_degradation(state)` (Módulo 2): degrada Active→Canary automáticamente si WR≤45% o PnL≤-$1.50 (con n≥5, anti-flapping 14 días). Overlay `auto_canary_from_active` en `city_policy_state.json`. `get_effective_city_mode()` extendido mínimamente para leer ese overlay antes de `ACTIVE_TRADING_CITIES`.
  - `maybe_alert_v2_trigger(state)` (Módulo 3): alerta one-shot cuando `RECALIBRATION_PHASE2_CLOSED=true` + al menos 1 ciudad en Active + `signals.json` fresco (<48h). Idempotente, gate diario.
- **Integración en `run_observability_alerts()`:** `maybe_run_active_degradation` (antes de `notify_canary_candidates`), `notify_active_candidates` (después), `maybe_alert_v2_trigger` (en gate diario junto a `maybe_run_daily_crosscheck` y `maybe_run_blocked_signals_check`).
- **`verify_before_deploy.py`:** 643→663/663 (+20 tests: 10 estáticos + 8 funcionales + 2 idempotencia/one-shot).
- **No tocado:** `sync_city_policy_state()`, thresholds `SHADOW_CANARY_MIN_*`, `ALLOWLIST_REMOVE_*`, `MIN_EDGE`, `MIN_DAYS_AHEAD`, trading core, NOAA client, scheduler, `signals.json`, `trader_analyzer.py`.
- **Nota operativa recurrente:** volumen bajo del scan loop sigue siendo backlog paralelo no resuelto (condition_filtered, scheduler, filtros temporales). Este módulo ayuda indirectamente al sizing Active pero no resuelve throughput de fondo.

### Sesión 174 — Blocked signals WR baseline n=59 + Opus handoff condition_filtered (14 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/next-session-handoff-2026-04-13-B-blocked-settlement.md` (Opus, Sesión 168).

- **Tool `blocked_signals_settlement_tracker.py` corrida localmente:** data fresca de Polymarket API → 59 resolutions (18 preexistentes + 41 nuevas).
- **WR overall: 76.3% (45/59)** — cumple ampliamente threshold WR≥55% con n≥50 robusto. Veredicto oficial: **REOPEN CANDIDATE**.
- **Por condition:** exact 72.5% (37/51), range 100% (8/8).
- **Por ciudad (n≥3):** Seattle/Tokyo/Hong Kong 100%, Seoul/Toronto 75%, Chengdu/Shenzhen/Shanghai/Milan 66.7%, London 33.3% (outlier, n=3).
- **Consenso vs solo:** consenso 66.7% (6/9), solo 78.0% (39/50).
- **Hallazgo clave:** `ALLOWED_CONDITIONS` ya es env var en `bot.py:222` — añadir `exact,range` en Railway es el cambio mínimo. Cero código nuevo necesario para reapertura global.
- **Decisión de diseño diferida a Opus:** preguntas abiertas — global vs quality-trader-gated, manejo de London (outlier 33.3%), edge mínimo diferenciado, scope de ciudades, fecha de revisión post-apertura.
- **Entregables:**
  - `data/runtime_import_derived/blocked_signals_resolutions.jsonl` actualizado a 59 records (gitignored)
  - `docs/blocked-signals-wr-baseline-2026-04-13.md` actualizado con WR=76.3%/n=59
  - `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md` — spec completo para Opus
  - `CONTEXTO.md` y `HISTORIAL_SESIONES.md` alineados
- **No tocado:** `bot.py`, trading core, Railway, env vars, `ALLOWED_CONDITIONS`.

### Sesión 175 — condition_filtered canary reopen v10.6.15 (14 abr 2026)

**Modelo:** Sonnet (implementación) + Opus (decisión vía subagente). **Handoff:** `docs/handoffs/condition-filtered-reopen-handoff-2026-04-14.md`.

- **Análisis previo (Sesión 174):** 59 resoluciones reales de quality traders con `exact/range` → WR=76.3%, threshold ≥55% n≥50 cumplido.
- **Decisión Opus (Opción B modificada):** reabrir con triple gate — quality trader + whitelist 9 ciudades + edge buffer +5pp. London excluida (WR 33% n=3).
- **Implementado en `bot.py` v10.6.15:** 4 env vars nuevas (`QUALITY_TRADER_CONDITIONS`, `QUALITY_TRADER_CITIES_WHITELIST`, `MIN_EDGE_EXACT_RANGE_BUFFER_PP=5.0`, `EXACT_RANGE_SIZE_SCALE=0.50`), lógica triple gate en `condition_filtered`, edge mínimo diferenciado, sizing 25% del normal.
- **Checkpoints comprometidos:** día 7 (2026-04-21), día 14 (2026-04-28). Kill-switch: WR bot <45% n≥20.
- **Deploy Railway OK** — logs confirmaron feature activo, Milan 18°C exact procesada por ruta canary.
- **Pendiente:** `tools/condition_reopen_monitor.py` + integración Telegram automática → Sesión 176.
- `verify_before_deploy.py` → 671/671.

### Sesión 178 — London city-intelligence audit + policy priority fix (15 abr 2026)

**Modelo:** Codex.

- **Refresh runtime read-only:** `tools/railway_runtime_snapshot_pull.ps1` se ejecuta con bypass de `ExecutionPolicy` para traer snapshot fresco y eliminar el `manifest_drift` local que estaba distorsionando el ledger.
- **Diagnóstico London reanclado:** la ciudad deja de leerse como simple `background_watch`/`trader_discovery`; el problema real pasa a ser `blocked` con `policy_divergence` (`cross=blocked`, `runtime=auto_canary`) y cuello `source_fidelity`.
- **Fix analítico en `tools/city_validation_ledger.py`:** se añade `STRUCTURAL_BLOCK_GUARDRAILS` para London y se corrige la prioridad de modos para respetar la regla canónica de `AGENTS.md` (`blocked > canary > shadow`). Con eso London vuelve a `policy_mode=blocked`, carga `structural_block_guardrail`, y su bottleneck se clasifica como `source_fidelity`.
- **Ajuste en `tools/city_promotion_gate.py`:** se mejora el tratamiento de ciudades con bloqueo estructural explícito para que la cola de revisión no las cuente como simple falta de discovery.
- **Auditoría settlement/source fresca de London:** `tools/settlement_fidelity_probe.py --city London --limit 20` encuentra 10 mercados con Open-Meteo, 0/10 con NOAA observado y `WU` todavía `pending_not_automated`; `shadow_city_tracking` muestra `markets_seen=128`, `edge_hits=2`, `cycles_seen=41`, `best_edge_pct=28.4`. `docs/blocked-signals-wr-baseline-2026-04-13.md` sigue dejando London en 33.3% (1/3) para exact/range.
- **Veredicto operativo:** mantener London en `blocked`; no usarla como candidata de monetización mientras no exista una revalidación WU-backed o una comparación manual robusta de settlement.
- **Artefactos nuevos:** `docs/london-city-intelligence-warning-review-2026-04-15.md` y `docs/london-settlement-source-audit-2026-04-15.md`.
- **Verificación:** `python -m py_compile tools/city_validation_ledger.py tools/city_promotion_gate.py` OK; `python verify_before_deploy.py` se ejecuta al cierre antes de commit/push.

### Sesión 176 — condition_reopen_monitor + integración bot (v10.6.16) (14 abr 2026)

**Modelo:** Sonnet. **Handoff:** `docs/handoffs/condition-filtered-monitor-handoff-2026-04-14.md` (Sonnet, Sesión 175).

- **`tools/condition_reopen_monitor.py`** standalone read-only: carga `data/trade_lifecycle.json`, filtra trades `condition ∈ {exact, range}` desde 2026-04-14 con `status=closed`, calcula WR via `close_context.pnl_cash > 0`, desglose por ciudad, veredicto automático (OK / ALERT / CLOSE / PROMOTE / EXTEND / KILL_SWITCH / INSUFFICIENT).
- **`_condition_monitor_stats(today)`** en `bot.py`: misma lógica inline para uso desde el bot sin importar desde `tools/`.
- **`maybe_run_condition_monitor(state)`** en `bot.py` v10.6.16: dispara desde día 7 en fechas de checkpoint (2026-04-21, 2026-04-28) y en kill-switch activo (WR<45% n≥20). Anti-spam via `state["last_condition_checkpoint"]`; kill-switch repite diariamente. Integrado en `run_observability_alerts()`.
- **`_build_condition_checkpoint_message`**: templates para OK, ALERT, CLOSE, PROMOTE, EXTEND, KILL_SWITCH — todos incluyen bloque `<code>` con instrucción lista para sesión Sonnet/Codex.
- **9 tests nuevos** en `verify_before_deploy.py`. `verify_before_deploy.py` → 680/680.
- **No tocado:** criterios trading, Kelly, NOAA, thresholds canary→active, Railway, env vars.


### Sesión 177 — Austin canary onboarding + análisis throughput (v10.6.17) (14 abr 2026)

**Modelo:** Opus (análisis/diseño) + Sonnet (implementación).

**Análisis Opus — throughput scan loop:**
- `price_out_of_range` (51% de skips): filtro `[MIN_PRICE=0.20, MAX_PRICE=0.80]` correctamente calibrado. Evidencia: 82.8% de los skips son markets YES<5% (long-shots). Trades históricos con `avg_entry_price<0.25`: 31 registros, 4W/18L, −$23.50 neto. Zona ganadora: 0.50–0.80 (10W/3L, +$4.39). Veredicto: no tocar.
- `timezone_filter` (6.3%): estructural Asia, sin solapamiento con candidatos TRADER_ONLY. Diferido.
- TRADER_ONLY 27 ciudades: todas en shadow (`fuera_allowlist`). Atacar lista de ciudades, no filtros.
- Palanca recomendada: **Austin →canary** (cross-check 2026-04-13: n_consensus=2, trader_wr=65.5%, mkt_price=0.48).

**Bloqueador detectado pre-implementación:** Austin ausente de `RESOLUTION_ICAO`, `CITY_TIMEZONES` y `OBSERVED_AUDIT_CITIES` — sin infraestructura NOAA no puede tradear aunque sea canary.

**Verificación NOAA Austin (KAUS):**
- ISD history: USAF=722540, WBAN=13904, activo hasta 2025-08-27 → `noaa_station_id="72254013904"` (gate-pass; bot usa daily como prioridad 1).
- GHCND confirmado via CDO: `USW00013904` = "AUSTIN BERGSTROM INTERNATIONAL AIRPORT, TX US", 30.18°N 97.68°W, 146.5m.
- NOAA daily-summaries verificado: **182 registros TMAX oct2025–mar2026**, rango −1.7°C a 36.7°C (plausible para Austin).

**Cambios implementados:**
- `bot.py`: Austin en `RESOLUTION_ICAO` (`noaa_station_id`, `noaa_daily_station_id`), `CITY_TIMEZONES` (`America/Chicago`), `OBSERVED_AUDIT_CITIES`.
- `data/runtime_import/city_policy_state.json`: Austin en `auto_canary_cities` + `transition_history` (2026-04-14).
- `verify_before_deploy.py`: 5 tests nuevos (Austin infra, bounds guardados, ACTIVE_TRADING_CITIES guardrail) → **685/685**.

**Criterios de evaluación canary Austin:**
- GO: WR≥55% o PnL≥+$0.50 sobre ≥3 trades cerrados.
- NO-GO: PnL≤−$2.00 o 3 losses consecutivos → degradar a shadow.
- Inconcluso: <3 trades en 14 días → evaluar si Austin tiene mercados suficientes.

**No tocado:** filtros, MIN_PRICE, MAX_PRICE, thresholds, Kelly, sigma, exits, ACTIVE_TRADING_CITIES (sigue NONE).

### Sesión 182 — residual canary shadow-only gate fix + live verification (16 abr 2026)

**Modelo:** Codex.

- **Diagnóstico cerrado con evidencia mínima:** se leen `AGENTS.md`, bloque reciente de `CONTEXTO.md`, `OPERATIONS_PLAYBOOK.md`, `data/runtime_import/skip_log.jsonl`, `cycle_summary.json` y `city_policy_state.json` para aislar el gating residual sin mezclar refactor amplio ni tocar trading core.
- **Patrón runtime exacto:** todas las filas históricas de `skip_log` con `skip_reason="shadow_only_override"` resultan ser `city_mode="canary"` y `allowlisted=false`; no aparece ningún caso `shadow` con ese motivo. Ejemplos previos al fix: `Shanghai` (`2026-04-15T04:00`), `Chicago` (`2026-04-15T07:14`, `08:00`, `15:24`) y `Seoul` (`2026-04-16T07:07`, `edge_pct=68.47`).
- **Causa raíz precisa en `bot.py`:** el scan loop ya resolvía bien `city_mode="canary"` vía `get_effective_city_mode()`, así que el bug no venía del orden de reconocimiento `auto_canary` ni de que la allowlist de ejecución siguiera atada directamente a `ACTIVE_TRADING_CITIES`. El problema real estaba en `_is_shadow_only()`: su fallback legacy seguía mirando solo `ACTIVE_TRADING_CITIES` y `CANARY_TRADING_CITIES` explícitas. Con `ACTIVE_TRADING_CITIES=NONE`, una ciudad podía ser `canary` efectiva por `city_policy_state.json` y aun así quedar degradada a `shadow_override_flag=True`.
- **Fix mínimo aplicado:** `_is_shadow_only()` ahora mantiene `SHADOW_ONLY_MODE` como toggle explícito, pero en el fallback legacy también cuenta `auto_canary_cities` y `auto_canary_from_active` cargadas desde `city_policy_state.json` antes de declarar pausa global.
- **Guardrail nuevo:** `verify_before_deploy.py` añade checks estáticos + funcionales para el caso exacto de `ACTIVE_TRADING_CITIES=NONE` con `auto_canary` persistida; la suite sube a **691/691**.
- **Commit y push:** `2ac2bb1` — `Fix shadow-only fallback for auto-canary cities` → `origin/main`.
- **Deploy Railway verificado:** deployment `af3c82b8-7f4b-4a55-bd3f-14ecb40f8edc`, arranque `2026-04-16 07:36:23 UTC`, logs con `Modo: REAL`.
- **Prueba live post-deploy cerrada:** tras esperar al ciclo `2026-04-16T08:00`, `tools/railway_runtime_snapshot_pull.ps1` refresca `data/runtime_import/`. Resultado: `shadow_only_override` nuevo = **0** desde el deploy; las ciudades `canary` pasan con `allowlisted=true`; `Seoul` ya no cae por override y sus skips pasan a `price_out_of_range`, `condition_filtered` y `existing_position`. El único `fuera_allowlist` nuevo del ciclo corresponde a `Hong Kong` en `shadow`.
- **Veredicto final:** **bug residual corregido**.
### Sesión 183 — shadow→NOAA funnel hardening (16 abr 2026)

- Se audita el embudo `shadow -> NOAA -> WR observado` con `data/runtime_import/shadow_city_tracking.json` y `audit.json`: `30` `edge_hit=true` recientes, pero casi toda la muestra se perdía antes del join NOAA por parser legacy y por depender de una ventana corta de ciclos.
- `bot.py` endurece la semántica shadow: `_shadow_condition_code()` reutiliza `parse_temperature_question()`, se añade `_extract_threshold_canonical()`, y `_shadow_signal_signature()` / `_build_shadow_signal_record()` dejan de persistir señales válidas con `threshold=None` cuando la pregunta es `or higher` / `or below`.
- `_get_noaa_candidate_dates()` pasa a priorizar una base durable desde `directional_history` antes de caer al fallback de `scanned_markets` recientes, para que una señal shadow elegible por lag NOAA no desaparezca solo porque pasaron suficientes ciclos.
- `build_dashboard_road_to_real()` y `get_dashboard_alert_summary()` dejan de usar `shadow.summary.edge_hits` como proxy mezclado y pasan a leer `total_signals`, `matched`, `resolved` y `win_rate` desde `_build_shadow_noaa_resolution_stats()`.
- Se corrige además una referencia latente a `shadow_summary` sin inicializar en `build_dashboard_city_decisions()`.
- Verificación: `python -m py_compile bot.py` OK. `verify_before_deploy.py` ya no falla por la lógica del funnel, pero el harness sigue cayendo en Windows por `Access denied` al tocar `%TEMP%`, así que ese gate queda pendiente de limpieza externa o aislamiento del bug del verificador.

### Sesión 184 — city-intelligence alarm realigned to runtime canary reality (16 abr 2026)

**Modelo:** Codex.

- **Diagnóstico reanclado a runtime:** la alarma de `city intelligence` seguía leyendo `Chicago` como `needs_shadow_validation` / `policy_execution_gate` aunque el snapshot fresco ya la muestra en `runtime_policy_mode=auto_canary`, `allowlisted=true` y sin `shadow_only_override` nuevo tras la sesión 182.
- **Fix analítico en `tools/city_validation_ledger.py`:** se añade un estado explícito `canary_measurement` cuando la ciudad ya está en `auto_canary` y no hay `useful_policy_gate_count` reciente; la recomendación pasa a `observe_runtime_canary`.
- **Fix analítico en `tools/city_promotion_gate.py`:** se evita que una ciudad `auto_canary` sin bloqueos reales recientes vuelva a caer en `audit_runtime_drift`; el gate pasa a `observe_runtime_canary` con prioridad `watch`.
- **Artefactos regenerados:** se rerunean `tools/city_validation_ledger.py`, `tools/city_promotion_gate.py`, `tools/city_intelligence_telegram_alert.py --dry-run` y `tools/city_intelligence_pipeline.py --telegram-dry-run`, dejando `city_validation_ledger.json`, `city_promotion_gate.json` y `docs/city_intelligence_pipeline_latest.md` alineados con la realidad del bot.
- **Guardrail adicional en `verify_before_deploy.py`:** el harness funcional ahora carga `parse_temperature_question`, `_extract_threshold_canonical`, `re` y `normalize_city` dentro del bloque shadow/persistencia. Con eso desaparece el falso rojo donde `directional_history` y `road_to_real` fallaban por dependencias ausentes del test en vez de por lógica rota.
- **Verificación final:** `python verify_before_deploy.py` vuelve a verde completo en **691/691**.

### Sesión W17-Opus — revisión estratégica + bloque completo (17 abr 2026)

**Modelos:** Opus (análisis) + Sonnet (implementación).

**Contexto de entrada:** 71 ciclos (11 días) con solo 7 buys desde el 6 de abril. Sensación de "iterar en círculos" correcta y con causa estructural identificable.

**Diagnóstico central:**
- Throughput colapsó con v10.6: pre-Apr6 `4.6 edges/ciclo` / `0.98 buys/ciclo`; post-Apr6 `0.1 edges/ciclo` / `0.05 buys/ciclo`.
- Causa raíz: `condition_filtered` mata `~47%` de candidatos cada ciclo. El modelo gaussiano sobreestima P(YES) para exact/range — bot ve `our_prob~40%`, mercado cotiza `18%`, genera edge ilusorio.
- Evidencia: bot WR `0%` en YES exact/range (`26` trades, `−$27.09`). Traders en esos mismos mercados: `76% WR`, van `68% NO`. Todos los wins del bot son NO-side con `our_prob≥78%`.
- PnL real: `at_or_above` +$0.97, `exact` −$9.26, `range` −$23.94.
- `48%` de cierres son `micro_position_unsellable` (29/61 posiciones).

**Cambios implementados en `bot.py` (4 commits push a `main`):**

1. **S2 — Whitelist canary:** `QUALITY_TRADER_CITIES_WHITELIST` default ampliado con `Atlanta, London, New York City, Munich`. Railway actualizado con lista completa.
2. **C1-fix — YES exact/range floor:** bloque `v10.6.18` antes de `_effective_min_edge`: si `exact_range_canary` y `side == "YES"` y `our_prob < 0.65` → skip con `skip_reason_detail="exact_range_yes_low_confidence"`. Habría bloqueado los 23 YES losses históricos (avg `our_prob=40.1%`) manteniendo todos los NO wins.
3. **Seoul auto-canary promotion fix:** guardia `city not in auto_blocked` en `sync_city_policy_state()`. Bug original: `auto_blocked` con NOAA proxy retornaba `"shadow"` de `get_effective_city_mode()` → la guardia pasaba → Seoul entraba en `auto_canary_cities` erróneamente.
4. **W17 observation alert:** `maybe_run_w17_observation_alert(state)` — one-shot el 2026-04-20. Lee `cycles_history.jsonl` desde `2026-04-17T18:00`, calcula métricas post-bloque y envía prompt Telegram completo para Codex/Sonnet.

**Railway actualizado:**
- `QUALITY_TRADER_CITIES_WHITELIST` → lista completa con 4 ciudades canary.
- `SCHEDULE_DISABLED_HOURS_UTC=23` → slot 23h apagado live (ya existía desde Sesión 190).

**Docs creados:**
- `docs/strategic-review-opus-2026-04-17.md`
- `docs/execution-plan-w17-2026-04-17.md` (bloque W17 completado íntegramente)
- `docs/c1-autopsy-exact-range-2026-04-17.md`

**Análisis adicional:** NYC NO TP +59% confirmado como correcto (forecast 77.7°F vs threshold 77°F, margen 0.7°F). No prematuro.

**Verificación:** `verify_before_deploy.py` 702/702 antes del último push.

**Próxima revisión Opus:** semana del 24 de abril de 2026. Criterios: `markets_evaluated≥25`, `with_edge≥0.5`, `buys≥0.3` por ciclo.

## Sesión 215 — P4+P5 whitelist expansion v10.6.27+v10.6.28 (21 abr 2026)

**Tipo:** Improvement — throughput canary exact/range
**Modelo:** Sonnet (implementación) + Opus (verificación NOAA P5)
**Versiones:** v10.6.27 → v10.6.28

**Contexto:** Checkpoint día 7 del canary exact/range (abierto 2026-04-14) mostró WR=40% n=5 — throughput crítico, solo 5 trades en 7 días. El whitelist era el cuello principal. Se descubrió además un bug en la precondición de `maybe_alert_p4_p5_expansion` que hubiera abortado la expansión erróneamente (confundía `OK_INSUFICIENTE` n<5<15 con `CLOSE/ALERT` real).

**P4 — v10.6.27 (ciudades ya en RESOLUTION_STATIONS):**
- Tel Aviv: blocked WR 3/3=100%, NOAA verificado LLBG
- Taipei: blocked WR 3/3=100%, ICAO-only RCTP
- Singapore: TRADER_ONLY 2/2, ICAO-only WSSS
- Wuhan: TRADER_ONLY 2/2, ICAO-only ZHHH

**P5 — v10.6.28 (ciudades nuevas, RESOLUTION_STATIONS añadidas):**
Opus verificó Polymarket resolution sources vía WebFetch y confirmó NOAA global-hourly+GHCND vacíos en 2026 (patrón Jakarta/KL) → todas ICAO-only:
- Moscow: 5/5=100% blocked WR, UUWW Vnukovo
- Amsterdam: 3/3=100%, EHAM Schiphol
- Jeddah: 4/4=100%, OEJN King Abdulaziz
- Istanbul: 3/3=100%, LTFM — riesgo mismatch=cero (LTFM ausente de NOAA ISD)
- Helsinki: TRADER_ONLY 2/2, EFHK Vantaa

**Bug corregido:** `maybe_alert_p4_p5_expansion` — precondición distingue ahora `OK_INSUFICIENTE` (n<15 → continuar) de `CLOSE/ALERT` real (n≥15 y WR<50%).

**Railway:** `BLOCKED_CITIES` actualizado a solo `London` (Singapore y Toronto removidas — bloqueaban el canary gate). `QUALITY_TRADER_CITIES_WHITELIST` a 32 ciudades.

**Verificación:** `verify_before_deploy.py` 755/755 (9 tests nuevos).
