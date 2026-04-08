# SISTEMA_MEJORA_CONTINUA.md

## Propósito del sistema

Este proyecto no debe entenderse solo como "hacer rentable el bot". El objetivo real es construir un **sistema robusto de mejora continua** para operar, observar, explicar, corregir y priorizar con evidencia.

La rentabilidad no se documenta aquí como promesa aislada. Se trata como **consecuencia esperable de un sistema bien instrumentado, trazable, interpretable y prudente con el riesgo**.

Principios de propósito:

- maximizar aprendizaje operativo sin romper trazabilidad;
- distinguir `fallo real del sistema`, `limitación conocida` y `ruido de mercado` antes de tocar lógica;
- registrar qué hizo el bot, por qué lo hizo, qué no hizo y qué pasó después;
- reducir incoherencias entre producción, snapshots, postmortem, lifecycle, dashboard y documentación;
- proteger capital primero; optimizar rentabilidad solo cuando exista evidencia suficiente.

Fuente conceptual ya existente y reutilizada: `OBSERVABILIDAD_Y_APRENDIZAJE.md`, `docs/ESTRATEGIA_OPERATIVA.md`, `CONTEXTO.md`, `OPERATIONS_PLAYBOOK.md`, `HISTORIAL_SESIONES.md` y el contrato operativo de `AGENTS.md` / `CLAUDE.md`.

## Contrato operativo de fuentes

El sistema necesita una semántica estable para aprender sin mezclar señales heterogéneas. El contrato canónico queda así:

- **Open-Meteo decide**
- **NOAA mide**
- **Weather Underground resuelve**

Traducción operativa:

- `Open-Meteo` es la fuente de forecast usada para escaneo, probabilidad, edge y sizing.
- `NOAA` es la capa observada usada para `observed_vs_forecast`, cobertura, `MAE`, `bias`, `NOAA-verificado` y aprendizaje por ciudad.
- `Weather Underground` sigue siendo la referencia de settlement real de Polymarket.

Regla de interpretación:

- si una métrica explica una entrada o una no entrada, pertenece a la capa de decisión;
- si una métrica evalúa cobertura, sesgo o calidad del forecast, pertenece a la capa de medición;
- si una métrica pretende explicar PnL final o resolución, no debe presentar NOAA como settlement real.

Consecuencia práctica: cualquier vista, alerta o investigación futura debe etiquetar explícitamente en qué capa está trabajando para evitar drift semántico entre trading, observabilidad y settlement.

## Estado actual resumido

### Ya validado

| Capa | Estado según repo |
|------|-------------------|
| Persistencia operativa | Railway Volume con `performance.json`, `postmortem.json`, `cycle_summary.json`, `cycles_history.jsonl`, `alerts_state.json`, `audit.json`, `trade_lifecycle.json`, `city_policy_state.json` y `agent_events.jsonl`. |
| Trazabilidad de trades | `postmortem.json` y `trade_lifecycle.json` ya reconstruyen BUY, `SELL_PENDING`, SELL/SELL_FAILED, `LOSS_TOTAL`, `RESOLVED_WIN`, snapshots y observación post-salida, con hardening contra duplicados y cierres huérfanos históricos. |
| Observabilidad ejecutiva | Dashboard con `Mission HUD / Control Center`, `/focus` en Telegram, tabla de estado por ciudad, ranking operacional, capa NOAA separada, scorecard y trade console. |
| Política por ciudad | `ACTIVE_TRADING_CITIES`, `BLOCKED_CITIES`, overlay `shadow/canary`, tracking `shadow_city_tracking.json`, y rediseño local de `auto_blocked_cities` con `action/reason/metrics/from_mode/triggered_at`. |
| Guardrails de proceso | `verify_before_deploy.py`, playbook de inicio/cierre, premortem corto para cambios core, regla "primero evidencia, luego refactor", y wrapper seguro de Railway. |
| Telegram operativo | Comandos `/focus`, `/estado`, `/cartera`, `/rendimiento`, `/accuracy`, `/noaa`, `/observabilidad`, `/postmortem`, `/detalle`, y alertas one-shot ya persistidas para algunos eventos de observabilidad. |
| Tooling multiagente | `.codex/config.toml` fija `medium` por defecto y perfiles `low/deep/max`; `trading-ops-analyst` existe para auditoría operativa y clasifica anomalías sin tocar core. |

### En observación

| Tema | Qué significa |
|------|---------------|
| `auto_blocked_cities` | Implementado localmente, pero `origin/main` y Railway aún no reflejan sesiones 66-67 según `CONTEXTO.md`; falta validar en live que el scan salta ciudades auto-bloqueadas aunque sigan en allowlist manual. |
| Ranking decisional por ciudad | El ranking y `readiness_score` ya existen, pero sigue pendiente validar en Railway que separan bien candidatas reales vs degradadas y que el overlay automático se interpreta como se espera en operación real. |
| NOAA observado | La capa `observed_vs_forecast` está separada y el fix `daily-summaries/TMAX -> global-hourly` está implementado, pero falta cerrar la validación live completa y Buenos Aires aún queda en fallback temporal. |
| Railway CLI | El hardening con mutex + preflight reduce el riesgo de `invalid_grant`, pero la causa raíz exacta sigue tratándose como inferencia, no como hecho cerrado. |
| Estado real vs snapshots | Hay evidencia explícita de drift: snapshot Railway del `2026-04-01 20:13 UTC` quedó obsoleto frente a ventas manuales no registradas por el bot. |

### Frágil o incompleto

| Zona | Fragilidad pendiente |
|------|----------------------|
| Fuente real de resolución | NOAA mejora la observabilidad, pero sigue siendo `observed proxy`; la fuente real de settlement sigue siendo Weather Underground y aún no está automatizada. |
| Backfill `shadow` | La capa `shadow` aprende hacia adelante, pero todavía no tiene backfill histórico conservador ni separación explícita entre retroconstruido y live. |
| Reconciliación manual | Las ventas manuales externas al bot pueden dejar postmortem/snapshot desalineados con el estado real y afectar interpretación de exposición o lifecycle. |
| Evento explícito de `REDEEM` | La consola ya habla honestamente de `claim pendiente / no confirmado`, pero no existe un evento de lifecycle dedicado para canje/redención. |
| Auditoría legacy | `forecast_vs_real` sigue existiendo como clave histórica, pero semánticamente no es "real" sino forecast posterior Open-Meteo; requiere disciplina constante para no sobreinterpretarlo. |
| Consistencia documental | `AGENTS.md` referencia `@RTK.md`, pero ese archivo no existe en el árbol local actual; es una señal pequeña de posible drift documental. |

## Próximos niveles del sistema

Esto no es un roadmap temporal. Es un **roadmap lógico de madurez**: cada nivel solo tiene sentido si el anterior ya genera evidencia suficiente y estable.

### Nivel 1 — Fidelidad de datos y estado real

Objetivo: que producción, snapshots, postmortem, lifecycle, cartera real y dashboard cuenten la misma historia o, si no, que la discrepancia sea explícita.

Incluye:

- verificación sistemática de drift `estado real vs repo/snapshot`;
- reconciliation explícita de operaciones manuales y estados `redeemable/claim`;
- nomenclatura honesta entre auditoría legacy, NOAA proxy y fuente real de resolución.

### Nivel 2 — Coherencia de lifecycle y accounting

Objetivo: que cada trade tenga una narrativa única, completa y auditable desde entrada hasta cierre/canje, sin duplicados, parciales ambiguos ni estados imposibles.

Incluye:

- fortalecer `trade_lifecycle.json` como capa canónica derivada de lectura operativa;
- cerrar huecos alrededor de `SELL_PENDING`, `REDEEM/claim`, micro-residuos y reconciliación con cartera;
- generar indicadores de integridad que bloqueen conclusiones analíticas cuando falte evidencia.

### Nivel 3 — Guardrails automáticos con evidencia persistida

Objetivo: pasar de alertas descriptivas a política operativa explícita y persistida, sin convertir cada aviso en automatización prematura.

Incluye:

- consolidar `auto_blocked_cities` y sus criterios de salida manual/conservadora;
- distinguir alertar, degradar, shadowear, canariar y bloquear como acciones separadas con evidencia estructurada;
- evitar que una ciudad siga comprando solo porque Telegram ya avisó una vez.

### Nivel 4 — Observabilidad live accionable

Objetivo: que dashboard y Telegram prioricen lo que cambia la decisión de hoy, y releguen lo explicativo a capas secundarias sin esconder evidencia.

Incluye:

- mantener capa 1 centrada en salud, intervención, limitador dominante, aprendizaje y siguiente acción;
- series cortas de tendencia para saber si el sistema está aprendiendo o solo operando;
- alertas Telegram basadas en discrepancias materiales, no en ruido.

### Nivel 5 — Aprendizaje por ciudad y por fuente

Objetivo: que las decisiones por ciudad no dependan de intuición ni de un único agregado global, sino de evidencia local suficiente y comparable.

Incluye:

- backfill conservador de `shadow` histórico;
- separación clara entre `retroconstruido` y `live`;
- lectura por ciudad combinando histórico real, NOAA, policy overlay, support count y coste de reabrir riesgo.

### Nivel 6 — Automatización segura y reversible

Objetivo: automatizar solo lo que ya está suficientemente observado, tiene criterio estable, test de regresión y rollback claro.

Incluye:

- hardening de procesos repetitivos como Railway, snapshots y validación predeploy;
- automatización que reduzca riesgo operativo, no que oculte incertidumbre;
- ninguna autooptimización de estrategia core sin revisión humana y evidencia previa.

## Implementaciones candidatas

No son tareas a ejecutar ya. Son **bloques futuros razonables** que solo deberían abrirse si la evidencia previa existe.

| Bloque candidato | Qué problema resuelve | Por qué importa | Evidencia necesaria antes | Riesgo si se implementa demasiado pronto |
|------------------|-----------------------|-----------------|---------------------------|------------------------------------------|
| Validador de drift `estado real vs snapshot/postmortem/lifecycle` | Detectar ventas manuales, posiciones obsoletas o divergencias entre cartera real y archivos persistidos. | Evita decisiones sobre una foto falsa y reduce errores de exposición o diagnóstico. | Casos concretos reproducidos de drift, patrón de campos afectados y regla clara de qué fuente manda en cada conflicto. | Falsos positivos o reconciliaciones mal hechas que sobreescriban evidencia útil o tapen una anomalía real. |
| Evento explícito `REDEEM/CLAIM` en lifecycle | Cerrar la narrativa de posiciones ganadas/canjeables y distinguir "cerrada económicamente" de "canje registrado". | Mejora accounting, lectura de capital liberado y calidad de postmortems. | Casos live suficientes donde `redeemable=true` y claim pendiente estén trazados y entendidos. | Inventar estados que la API no confirma o duplicar cierres si no se define bien la relación con `RESOLVED_WIN`. |
| Backfill conservador de `shadow` histórico | Dar memoria inicial a ciudades fuera de allowlist y acelerar aprendizaje sin abrir capital real. | Hace útil el ranking por ciudad antes de acumular demasiados ciclos nuevos. | Dataset histórico suficiente, criterio de reconstrucción conservador y separación visual entre `retroconstruido` y `live`. | Contaminar decisiones futuras con pseudo-histórico mal reconstruido o mezclar evidencia débil con datos live. |
| Validación live formal de `auto_blocked_cities` | Confirmar que el bloqueo automático persistido corta BUYs en producción y conserva motivo/evidencia en dashboard. | Cierra el bug de diseño detectado en Atlanta y reduce pérdidas evitables por ciudades degradadas. | Deploy activo, inspección de `city_policy_state.json`, logs de `SKIP` por ciudad bloqueada y lectura correcta en dashboard/Telegram. | Confiar en una política que solo está verde en local y descubrir tarde que el scan o la UI no leen el estado real. |
| Tendencias cortas de aprendizaje NOAA / ciudades / incidentes | Saber si la muestra y la cobertura avanzan o si el sistema solo repite ciclos sin aumentar interpretabilidad. | Prioriza trabajo según cuello de botella real, no según intuición o estética del dashboard. | Métricas base estables y semántica ya validada para `sample`, `coverage`, `interpretable`, incidentes y buckets. | Meter gráficos que parezcan precisión pero amplifiquen ruido por muestra baja o definiciones aún inestables. |
| Score de integridad analítica por trade/ciudad | Marcar cuándo una conclusión no es interpretable porque faltan `entry_context`, `buys`, `close_context`, `observed_after_close` o reconciliación de cartera. | Evita actuar sobre tablas bonitas pero incompletas y fuerza disciplina de evidencia. | Catálogo de casos `analysis_ready=false`, campos mínimos obligatorios y reglas de degradación visual claras. | Bloquear demasiados casos válidos por criterios excesivos o, al revés, dar una falsa sensación de completitud. |
| Paquete automático de sesión para Claude/Codex | Generar un resumen operativo estructurado con estado, anomalías, top riesgos y preguntas abiertas. | Reduce coste de contexto y mejora continuidad entre sesiones sin convertir memoria externa en fuente canónica. | Acordar qué campos salen de repo/live, qué se excluye por ruido y cómo enlazar con `CONTEXTO.md`/`HISTORIAL_SESIONES.md`. | Duplicar documentación, crear drift o producir resúmenes automáticos que suenen coherentes pero oculten incertidumbre. |
| Alertas Telegram de discrepancia material | Elevar incidentes reales como lifecycle roto, capital incoherente, deploy no validado o ciudad que debería estar bloqueada. | Permite intervenir rápido sin mirar todo el dashboard y sin esperar a una revisión manual completa. | Reglas estables, umbrales con pocos falsos positivos, persistencia anti-spam y evidencia de ejemplos reales. | Fatiga de alertas, ruido operacional y decisiones reactivas si se alerta por síntomas no clasificados. |

## Telegram / alertas

Las alertas por Telegram no deben activarse "porque sí". Solo tienen sentido si hay **criterio estable, evidencia suficiente, persistencia anti-duplicados y una acción operativa clara**.

Regla base: una alerta debe responder al menos estas preguntas:

- qué condición exacta se detectó;
- qué fuente o archivo la sustenta;
- por qué no es ruido normal;
- qué revisión o intervención se espera;
- cómo se evita realertar sin nueva evidencia.

Tipos de alertas que sí tendrían sentido en una fase posterior:

| Tipo de alerta | Condición documental esperada | Criterio de uso |
|----------------|-------------------------------|-----------------|
| Drift estado real vs snapshot/repo | Una posición o venta manual aparece en cartera real pero no en `postmortem/trade_lifecycle`, o al revés. | Alertar solo si la discrepancia afecta exposición, cierre, política por ciudad o lectura ejecutiva. |
| Ciudad que debería bloquearse y no se bloquea | `WR/PnL/trades` cruzan umbral de salida y no existe política efectiva `blocked` o `auto_blocked`. | Exigir evidencia estructurada en `city_policy_state.json` y mostrar motivo + métricas. |
| Capital/exposición inconsistente | `cash`, `currentValue`, `redeemable` o presupuesto libre no cuadran con reglas documentadas. | Priorizar casos que puedan bloquear entradas o inducir sobreexposición real. |
| `SELL_PENDING` o lifecycle roto | `SELL_PENDING` estancado, cierre huérfano, duplicado por `id`, o `analysis_ready=false` en casos recientes materiales. | Alertar solo cuando el estado impacte una posición viva, una salida reciente o una métrica usada para decidir. |
| Deploy o versión activa no validada | `origin/main`, docs y runtime Railway no están alineados o hay commit relevante sin validación funcional explícita. | Útil después de push/deploy, no como alerta recurrente sin acción. |
| Evidencia suficiente para escalar incidencia real | Patrón reproducible que encaja en `fallo real del sistema`, no en `limitación conocida` ni `ruido de mercado`. | Debe incluir fuente, caso mínimo reproducible y por qué merece intervención ahora. |
| Hitos de muestra interpretables | `n` NOAA o cierres por ciudad cruzan umbral mínimo de interpretación. | Usar como one-shot informativo para abrir análisis, no como señal de trading automática. |

Lo que no debería hacerse con Telegram:

- usar alertas como sustituto de política persistida;
- reabrir el mismo aviso en bucle sin nueva evidencia;
- mezclar en el mismo mensaje incidentes reales, limitaciones conocidas y ruido;
- activar automatización solo porque un umbral se cruzó una vez con muestra baja.

## Guardrails de evolución

- No implementar automatización antes de tener evidencia persistida, ejemplos reales y criterio de reversión.
- No confundir pérdidas por ruido de mercado con fallo interno de ejecución, datos o accounting.
- No tocar `bot.py`, trading, NOAA, scheduler, execution, exits o arquitectura core sin trazabilidad suficiente y premortem previo.
- No añadir complejidad analítica si antes faltan integridad de lifecycle, reconciliación de estado o semántica honesta.
- No usar métricas de muestra baja como prueba de mejora estructural.
- No promover/degradar ciudades sin distinguir `live`, `shadow`, `canary`, `blocked`, histórico retroconstruido y evidencia NOAA interpretable.
- No considerar cerrada una sesión si docs, historial y scoreboard quedan desalineados cuando el estado del sistema cambió.
- No tratar memoria externa como fuente de verdad por encima del repo y del estado live verificado.

## Criterio de priorización

Priorizar primero lo que:

- reduce riesgo real de pérdida evitable o bloqueo operativo;
- mejora interpretación de estado y evita conclusiones falsas;
- cierra incoherencias entre cartera, lifecycle, postmortem, dashboard y política por ciudad;
- protege capital y exposición antes de optimizar rentabilidad;
- crea guardrails reutilizables: test, alerta, regla de playbook, snapshot, o evidencia estructurada.

No priorizar primero lo que:

- añade UI vistosa sin cambiar una decisión operativa;
- amplía automatización con criterios aún no validados;
- mete refactors de arquitectura sin una anomalía observable clara;
- persigue features nuevas cuando la semántica de datos actuales sigue incompleta.

Regla práctica de decisión:

1. Si hay discrepancia de estado o riesgo de exposición mal medida, va antes.
2. Si una ciudad degradada puede seguir comprando por fallo de policy, va antes.
3. Si la capa analítica muestra una conclusión sin integridad suficiente, se corrige la trazabilidad antes de discutir estrategia.
4. Si el problema es una limitación conocida documentada y sin impacto operativo inmediato, no debe desplazar un fallo real.

## Qué no hacer todavía

- No reabrir cambios de sigma, Kelly, edge, scheduler o exits solo porque el PnL histórico siga negativo.
- No automatizar promoción a canary o desbloqueo desde `blocked` con criterios agresivos antes de validar `shadow` y backfill.
- No presentar NOAA como fuente real de settlement de Polymarket.
- No implementar alertas Telegram adicionales sin diseñar antes condición, fuente, deduplicación y acción esperada.
- No construir un backlog enorme desconectado de evidencia live; cada bloque futuro debe nacer de una incoherencia o una limitación concreta ya observada.
