# Sesion Opus — Review `city-intelligence` y `phase5-visibility`

Fecha: 2026-04-22
Tipo: revision estrategica y operacional de servicios read-only.
Alcance: decidir que seguir manteniendo, fusionar, archivar o apagar — no tocar codigo ni datos operativos.

---

## 1. Veredicto ejecutivo

- `polymarket-bot` es hoy, de facto, la fuente canonica de runtime y la **unica shell que ve el volumen real**. La sesion 222 lo confirmo: el puente `CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED` corre export + pipeline + alignment + daily summary dentro del propio bot. Eso deja al servicio separado `city-intelligence` en Railway como **cascaron sin runtime**, en fail-closed cronico por falta de `/app/data/runtime_import` (sesion 221).
- `city-intelligence` como **dominio analitico** sigue aportando: trader discovery, enrichment, cross con ciudades, ledger, promotion gate y alerta diaria. Esas funciones son las que producen las lecturas de `TRADER_ONLY persistentes` y el summary diario `traders vs bot`, que el strategic review 2026-04-17 no nombro como cuello pero que es la unica palanca viva de ampliacion de universo.
- `city-intelligence` como **servicio Railway separado** dejo de justificar su existencia. Su unico input fresco hoy viene del bridge dentro de `polymarket-bot`; el servicio remoto solo reemite fail-closed. Mantenerlo vivo duplica scheduler, volumen y superficie para que la alarma diaria mienta.
- `phase5-visibility` es legacy confirmado. El strategic review Apr-17 ya lo clasifico `ROI bajo — pausar`. La evidencia repetida (`11 coincidencias acumuladas Shanghai+Chicago`, mismo gap y mismo next step desde la 186) demostro que no produce decisiones nuevas, solo re-envia la misma foto. Las sesiones 194-195 explicitamente reescribieron sus alarmas como `alarma reescrita/eliminada`.
- De `phase5-visibility` sobreviven dos cosas con valor: (a) el **tracker temporal `city_probe_visibility_tracker`** — ya integrado en la pipeline de `city-intelligence`, y (b) el **patron one-shot Telegram** anti-spam — ya replicado en `city_intelligence_telegram_alert` y `city_intelligence_daily_summary` (sesion 202 anti-spam `last_sent_date`).
- Hay **dos planos decisionales compitiendo** hoy solo nominalmente: `phase5-visibility` sigue emitiendo `action_state=review / next_operational_step=increase_review_priority` sobre Shanghai+Chicago, mientras `city-intelligence` ya clasifica Shanghai/Chicago como `canary` runtime observable. No son veredictos contradictorios, pero si son una segunda voz que el humano tiene que ignorar a mano.
- Hay **dos escritores potenciales** del tracker `city_probe_visibility_tracker.json` (el pipeline de `city-intelligence` y el pipeline de `phase5-visibility`). En la arquitectura 2026-04-10 esto estaba marcado como riesgo (`Principio 1: una fuente de verdad por dominio`). En la realidad 2026-04-22, los dos corren en servicios distintos con volumenes distintos, asi que no hay corrupcion, pero si dos estados paralelos con el mismo nombre. Eso es justo el `Detector 6: phase5 duplicate decision plane`.
- Accion recomendada: **convertir el servicio separado `city-intelligence` en codigo-solo** (vive en el repo, lo ejecuta el bridge desde `polymarket-bot`), y **apagar `phase5-visibility` como servicio**, archivando docs y scripts sin borrarlos. Ni uno ni otro requiere tocar trading core, NOAA, scheduler, sizing, whitelist, reglas de entrada/salida ni `city_policy_state.json`.

---

## 2. Tabla por servicio

### 2.1 `city-intelligence`

| Aspecto | Lectura |
|---|---|
| Estado recomendado | **Fusionar plano de ejecucion en `polymarket-bot`, conservar el dominio analitico**. El servicio Railway separado se apaga; sus scripts siguen en `tools/` y los invoca el bridge. |
| Razon | El runtime solo existe en `polymarket-bot`. El bridge 222 ya demuestra que se puede correr el pipeline completo (export → effective view → pipeline → alignment → daily summary) una vez al dia desde el propio bot con inputs reales. Un segundo servicio agrega scheduler redundante, volumen divergente, y fail-closed cronico que obliga a leer alarmas falsas. |
| Funciones que sobreviven | `directional_trader_census`, `directional_trader_enrichment`, `reference_trader_city_market_cross`, `city_probe_visibility_tracker`, `city_validation_ledger`, `city_promotion_gate`, `city_intelligence_telegram_alert`, `city_intelligence_daily_summary`, `signals_vs_edge_crosscheck` + summary diario. |
| Funciones a retirar | El `city_intelligence_railway_service.py` como daemon en Railway; el scheduler propio; la copia de `/app/data/runtime_import` en el volumen separado. Tambien el uso de `city_validation_ledger.py` como escritor de artefactos publicos en un volumen que no es el del bot. |
| Riesgo principal | Perder el **aislamiento de scheduler**: si el pipeline tarda o falla dentro de `polymarket-bot`, tiene que degradarse limpio (ya lo hace: el bridge es best-effort antes de `blocked_signals`) y no bloquear el ciclo de trading. El guardrail actual — exception handling + anti-spam diario — es suficiente si se mantiene. |

### 2.2 `phase5-visibility`

| Aspecto | Lectura |
|---|---|
| Estado recomendado | **Congelar como legacy y apagar el servicio Railway**. Mantener docs y artefactos por trazabilidad; no ejecutar como scheduler vivo. |
| Razon | La arquitectura canonica 2026-04-10 ya lo nombra `experimental/legacy anterior a city-intelligence`. El strategic review 2026-04-17 lo puso explicitamente en `pausar`. Las sesiones 186+193+194+195 cerraron que la alerta `Shanghai + Chicago` no produce decisiones nuevas, solo repeticion (11 coincidencias, mismo gap, mismo next step). Toda funcion generica (tracker, alerta one-shot, comparador) ya esta absorbida o es absorbible por `city-intelligence`. |
| Funciones que sobreviven | Como **documentacion/trazabilidad**: `docs/phase5-*`, `data/phase5_visibility_*.json`, `seed_data/phase5/*`. Como **concepto metodologico**: la idea de comparar ciudad candidata vs benchmark active (hoy la cumple el ledger). |
| Funciones a retirar | `phase5_visibility_service.py` como daemon, `phase5_visibility_pipeline.py` como scheduler, `phase5_visibility_telegram_alert.py` como emisor, `phase5_operational_action.py` como workflow. Tambien los escritores especificos `shanghai_shadow_test.py`, `chicago_active_benchmark.py` y `shanghai_vs_chicago_comparator.py` en modo programado. |
| Riesgo principal | Perder el one-shot `Shanghai + Chicago` — ya sin valor decisional tras 11 repeticiones —; dejar seed data huerfana si se borra sin archivar; y **dejar un scheduler legacy encendido creyendo que se apago**. Mitigacion: primero apagar el servicio en Railway y confirmar `Stopped`, luego archivar docs, y solo despues — opcional — retirar los scripts del hot path. |

---

## 3. Plan minimo por fases

### Fase 0 — no tocar
- `bot.py`, trading core, NOAA core, scheduler del bot, sizing, whitelist, reglas de entrada/salida, `city_policy_state.json`, arquitectura core.
- El puente `CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED` recien activado en 222. Dejar estabilizar ≥5 dias con datos reales antes de retirar nada remoto.
- Los artefactos `data/city_validation_ledger.json`, `data/city_promotion_gate.json`, `data/city_intelligence_pipeline.json` como producidos por el bridge desde `polymarket-bot`: son la nueva fuente canonica. No sobreescribirlos desde otro proceso.

### Fase 1 — migrar / absorber
1. **Confirmar cobertura funcional del bridge**. Validar, durante al menos 5 ejecuciones diarias consecutivas del bridge desde `polymarket-bot`, que los artefactos locales (`runtime_import`, `city_validation_ledger`, `city_promotion_gate`, `city_intelligence_pipeline`, `system_alignment_check_operational`, `city_intelligence_daily_summary_state`) quedan `runtime_inputs_status=available`, `overall_status=ok` y la alerta Telegram no dispara falsos `runtime_inputs_missing`.
2. **Silenciar el servicio remoto `city-intelligence` sin borrarlo**. Primer paso reversible: apagar el env var `TELEGRAM_TOKEN` del servicio separado (o equivalente `--dry-run` forzado), para que sus daily summaries dejen de ruido humano mientras el bridge ya cubre la alerta real. Esto no toca policy live.
3. **Migrar — si todavia no esta — cualquier funcion unica de `phase5-visibility`** al pipeline de `city-intelligence`. Revisar: el one-shot anti-spam, el tracker (ya en `city_intelligence_pipeline`), y el comparador ciudad vs benchmark active (cubierto por `reference_trader_city_market_cross` + ledger). No crear codigo nuevo si ya existe equivalente.

### Fase 2 — archivar / apagar
4. **Apagar el servicio Railway `phase5-visibility`**. Reversible: primero `pause` del servicio, verificar 48h que no hay input critico perdido, luego confirmar `Stopped`. Scripts y docs quedan en el repo como material historico.
5. **Apagar el servicio Railway `city-intelligence`**. Mismo patron: primero silenciar alertas, luego `pause`, luego `Stopped`. La ejecucion queda cien por cien dentro de `polymarket-bot` via bridge. Las env vars del servicio (census, probe refresh) se transfieren al bot si hace falta; la mayoria ya son defaults.
6. **Unificar escritor de `city_probe_visibility_tracker.json`**. Confirmar que el unico proceso que escribe ese artefacto es el pipeline dentro de `polymarket-bot`. Dejar trazabilidad en `CONTEXTO.md` y en un handoff corto.
7. **Docs y seed data**. `docs/phase5-*` y `seed_data/phase5/*` se conservan sin cambios. Anadir una nota al principio de cada doc phase5 que diga `legacy archivado el YYYY-MM-DD, reemplazado por city-intelligence` con enlace al doc de arquitectura 2026-04-10.

### Validacion requerida (para cada paso)
- `python verify_before_deploy.py` — verde antes y despues de cada cambio.
- Pull fresco de runtime: `railway_runtime_snapshot_pull.ps1` sigue funcionando y el manifest no pierde archivos.
- Un ciclo completo del bridge produce `runtime_inputs_status=available`, `overall_status=ok` y `system_alignment_check.py --decision-mode operational` cierra con `error=0`.
- Telegram recibe la alerta diaria esperada y **no** recibe doble disparo (un solo emisor vivo).
- Durante 3 dias consecutivos post-apagado remoto: no hay perdida de evidencia operativa — ledger + gate + summary coherentes con la foto del bot.

---

## 4. Kill criteria

### 4.1 Para **mantener** `city-intelligence` como dominio (no servicio)
Se mantiene **si y solo si** cumple todos:
- El bridge en `polymarket-bot` produce `runtime_inputs_status=available` ≥ 80% de dias habiles en una ventana rolling de 7 dias.
- El summary diario genera al menos una **instruccion accionable por semana** que encaje en una de las cuatro salidas operativas (sesion 194): `cambio ejecutado`, `patch listo`, `gate definido` o `alarma reescrita/eliminada`.
- El cruce `signals vs bot` revela al menos una ciudad nueva al mes que valga la pena evaluar para whitelist (tendencia ya vista: Busan sesion 218, Dallas sesion 218; Jakarta/Kuala Lumpur sesion 201; lote P4+P5 sesion 215).

Se **apaga el dominio completo** (no solo el servicio) si:
- En una ventana de 30 dias el summary no produjo ninguna accion operativa real.
- O el tiempo humano dedicado a leer ledger/gate/summary supera al tiempo invertido en cuellos #1 (modelo exact/range) y #2 (position management) del strategic review.
- O la tasa de alarmas falsas/ruido supera ~40% de los envios.

### 4.2 Para **apagar o congelar** `phase5-visibility`
Se apaga ya (kill criteria ya cumplidos):
- ≥2 sesiones consecutivas (193, 195) con `alarma legacy / ya superada` como conclusion.
- 11 coincidencias `Shanghai+Chicago` sin generar decision nueva.
- Strategic review 2026-04-17 lo pone explicitamente en `pausar`.
- Toda funcion generica esta absorbida por `city-intelligence` (tracker, alerta one-shot, comparador).
- No hay PnL, no hay trade, no hay policy que dependa de este servicio.

Se **reconsidera** (se reabre) solo si:
- Aparece una ciudad candidata que el ledger de `city-intelligence` no sabe comparar contra benchmark `active` y el comparador phase5 si sabe.
- O aparece evidencia concreta de que `city-intelligence` perdio la capacidad de detectar asimetria shadow-vs-active para una ciudad nueva.

---

## 5. Recomendacion final accionable

1. **Dejar el bridge 222 estabilizar 5 dias**. No tocar `CITY_INTELLIGENCE_RUNTIME_BRIDGE_ENABLED`, no cambiar hora, no mover scripts. Solo observar que el summary diario Telegram salga coherente desde `polymarket-bot`.
2. **Silenciar — no apagar — el servicio Railway `city-intelligence`**. Quitar `TELEGRAM_TOKEN` de su env (o forzar `--dry-run` en su pipeline) para que deje de emitir la alarma `runtime_inputs_missing` en paralelo. Revertible en segundos.
3. **Silenciar — no apagar — el servicio Railway `phase5-visibility`**. Mismo patron: quitar `TELEGRAM_TOKEN`. Confirmar que no queda nadie esperando la alerta `Shanghai + Chicago`.
4. **Revisar que el unico escritor vivo del tracker `city_probe_visibility_tracker.json`** sea el pipeline invocado desde `polymarket-bot`. Si el servicio phase5 aun escribe a un volumen propio, esa copia queda huerfana y no se consume — aceptable durante fase de silencio.
5. **Durante la ventana de silencio (≈7 dias), medir**: cuantas alarmas reales nuevas aparecen desde el bridge, cuantas instrucciones accionables genera, y si el humano sigue dependiendo del servicio separado para algo concreto. Si nadie lo extrana, se confirma el kill.
6. **Apagar el servicio `phase5-visibility` en Railway** (`pause` → confirmar sin impacto → `stop`). Anadir nota de archivo en `docs/phase5-visibility-service.md` con fecha y razon; dejar scripts en el repo. No borrar data ni seed.
7. **Apagar el servicio `city-intelligence` en Railway** (mismo patron reversible). Migrar al bot las env vars que sobrevivan (revisar `census_markets`, `refresh_probe`, hora de corrida). Confirmar que `polymarket-bot` queda como el unico servicio con volumen activo.
8. **Unificar daily summary en un solo emisor**. El bridge ya manda via `city_intelligence_daily_summary` desde el bot; asegurar que no quede ningun otro emisor esperando el mismo trigger (`last_sent_date` ya activo desde sesion 202 evita doble disparo).
9. **Actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md`** con una sola entrada: `city-intelligence pasa a dominio en-bot via bridge, phase5-visibility apagado como servicio, ambos conservan docs y scripts`. No tocar `AGENTS.md` ni `CLAUDE.md`.
10. **Congelar cualquier expansion de observabilidad** durante 2-3 semanas mas. Las palancas reales siguen siendo las del strategic review 2026-04-17: modelo de probabilidad exact/range (C1, C3) y position management (S3). Este apagado libera atencion humana para ir a esos cuellos sin perder evidencia.

---

## Nota metodologica

Esta review no recomienda borrar codigo, no recomienda tocar volumenes en Railway ni mover env vars de policy. El patron es `silenciar → observar → pausar → apagar`, cada paso reversible en minutos. El objetivo no es simplificar por estetica, es **dejar una sola voz operativa viva** (`polymarket-bot` + bridge) y liberar cabeza humana para los cuellos que si mueven bankroll.
