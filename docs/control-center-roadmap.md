# Roadmap del Control Center — Polymarket Bot

**Fecha:** 3 de abril de 2026  
**Basado en:** `docs/control-center-audit.md`  
**Criterio de prioridad:** utilidad operativa real > estética > refactor

---

## Índice

1. [Quick wins](#quick-wins)
2. [Mejoras medianas](#mejoras-medianas)
3. [Cambios estructurales](#cambios-estructurales)
4. [Instrumentación nueva](#instrumentación-nueva)
5. [Orden recomendado de ejecución](#orden-recomendado-de-ejecución)

---

## Estado al 4 de abril de 2026 (post-rediseño)

### Completado (sesiones 71-77)

| ID | Tarea | Sesión | Estado |
|----|-------|--------|--------|
| QW1 | Eliminar `legacy-focus-shell` | 77 | Obsoleto — template reescrito de 1716→460 líneas |
| QW2 | Mover Legacy drift a capa 3 | 77 | Obsoleto — eliminado en rediseño |
| QW3 | Reordenar capa 2 | 73 | Hecho |
| QW4 | Alarma "sin ciclo en >12h" | 71 | Hecho |
| QW5 | Timestamp NOAA | 73 | Hecho |
| QW6 | Mini-cards "esperando muestra" | 73 | Hecho |
| QW7 | Colapsar Readiness/Desbloqueos | 77 | Obsoleto — eliminados trofeos/unlocks |
| M1 | Mega-card 3 tabs | 74 | Hecho (absorbido en Bloque 3) |
| M2 | Verificar persistencia shadow/policy en Volume | 78 | Hecho (5 abr, SSH Railway) |
| M3 | Cerrar filas Chicago legacy | 74 | Hecho (auditado) |
| M4 | Resumen diario Telegram (08:00 UTC) | 78 | Hecho (v10.6.11) |
| M5 | Alerta ciudad candidata a canary | 78 | Hecho (v10.6.11) |

### Rediseño global (sesión 77)
- Dashboard: Road to Real progress bar + Bloque 1 (Estado bot) + Bloque 2 (Señales shadow direccionales) + Bloque 3 (Salud del sistema en `<details>`)
- Eliminado: Mission HUD, trofeos, desbloqueos, scoreboards, trade console larga, tabla ciclos
- `build_dashboard_road_to_real()` con 6 checks (R1-R6) para reactivar trading real
- `_is_shadow_only()`, `_dashboard_mode_label()`, `_build_recent_shadow_rows()` en bot.py
- `verify_before_deploy.py` cubre nueva estructura: 516/516

---

## Tareas pendientes post-rediseño

### Mejoras medianas

### M2 — Verificar persistencia de shadow_city_tracking y city_policy_state en Volume ✅

**Estado:** Hecho (5 abr 2026, sesión 78).

**Verificación (via `railway_safe.ps1 ssh`):**
```
shadow_city_tracking.json   45650 B   Apr 4 23:00
city_policy_state.json       5449 B   Apr 4 16:00
```

Ambos archivos persisten en `/app/data/` entre deploys. Evidencia adicional: backups de `agent_events.jsonl` de Mar 29/30 y `postmortem.json.bak_session72_chicago` del 3 abr siguen presentes en el mismo Volume. El nombre real del archivo shadow es `shadow_city_tracking.json` (no `shadow_tracking.json` como figuraba originalmente en el roadmap). Tabla de `Datos persistentes` en `CONTEXTO.md` actualizada con la nueva fila.

**Desbloquea:** M5 (alerta canary en Telegram) y R1 (motor 3 gates).

---

### M3 — Cerrar 3 filas Chicago legacy open en postmortem.json

| Campo | Valor |
|---|---|
| **Objetivo** | Corregir el sesgo de WR de Chicago causado por filas `2026-03-26/27/28` con `status=open` |
| **Impacto** | Alto — WR 25% de Chicago puede ser incorrecto; afecta también la regla de salida automática |
| **Dificultad** | Media |
| **Riesgo** | Medio — modificar postmortem.json en producción requiere cuidado |
| **Prioridad** | Alta (ya estaba en next steps de CONTEXTO.md sesión 69) |
| **Archivos** | `postmortem.json` (Railway Volume), `bot.py` si se necesita lógica de backfill |
| **Dependencias** | Ninguna |
| **Sesión aparte** | Sí — ya planeado en sesión 70 según CONTEXTO.md |

---

### M4 — Resumen diario Telegram (08:00 UTC) ✅

**Estado:** Hecho v10.6.11 (sesión 78).

**Implementación:**
- `build_daily_summary_payload(now)` + `format_daily_summary_text(payload)` + `maybe_send_daily_summary_telegram(state, now)` en `bot.py`.
- Gate: `now.hour == sorted(SCHEDULE_HOURS_UTC)[0]` (08 UTC por defecto) y `state["daily_summary_last_sent"] != today_utc` → one-shot idempotente por fecha UTC.
- Invocado desde `run_observability_alerts()` al final, envuelto en try/except.
- Helpers internos de agregación 24h: `_daily_summary_cycles_last_24h` (cycles_history.jsonl), `_daily_summary_closed_trades_last_24h` (postmortem), `_daily_summary_noaa_last_24h` (audit.observed_vs_forecast por `checked_at`).

**Contenido:** ciclos 24h (ejecutados, mercados, edges, selected/shadow/buys_real), resoluciones 24h (cerrados, wins/losses, PnL), NOAA nuevos por ciudad + acumulado, versión, modo (SHADOW-ONLY / N activas), próximo ciclo.

---

### M5 — Alerta "ciudad candidata a canary" en Telegram ✅

**Estado:** Hecho v10.6.11 (sesión 78).

**Implementación:**
- `notify_canary_candidates(state)` en `bot.py`, self-contained: reconstruye `city_decisions` vía `_compute_city_decisions_for_alerts()` con los mismos helpers que usa `sync_city_policy_state`.
- Fires one-shot cuando `row.decision == "promote"`. Registra en `state["canary_candidate_notified"]` con evidencia (shadow_edges, best_edge).
- Limpia la entrada cuando la ciudad deja de ser candidata → permite re-disparo futuro si la evidencia regresa tras una regresión.
- Invocado desde `run_observability_alerts()` justo antes de `sync_city_policy_state`, envuelto en try/except. NO modifica la lógica de auto-promote: es observabilidad paralela con un mensaje rico en evidencia para review humano.

---

## Cambios estructurales

Requieren sesión propia y tienen impacto en lógica Python.

---

### R1 — Motor de ciudades: 3 gates visuales en lugar de score único

| Campo | Valor |
|---|---|
| **Objetivo** | Reemplazar `readiness_score` como display primario por 3 gates (Gate A historial, Gate B shadow, Gate C NOAA) |
| **Impacto** | Alto — hace el ranking de ciudades interpretable; hoy un número 0-99 es opaco |
| **Dificultad** | Alta |
| **Riesgo** | Medio — afecta `build_dashboard_city_decisions()` y el template |
| **Prioridad** | Media |
| **Archivos** | `bot.py` (`build_dashboard_city_decisions`), `templates/dashboard.html`, `static/dashboard.css` |
| **Dependencias** | M2 (verificar persistencia), M3 (corregir WR Chicago) |
| **Sesión aparte** | Sí |

**Diseño del cambio:**
- Añadir campos `gate_a`, `gate_b`, `gate_c` por fila de ranking (valores: `clean/bad/no_data`, `ready/building/empty`, `interpretable/partial/none`)
- Mostrar como 3 semáforos visuales antes del `state_label`
- Mantener `readiness_score` solo para ordenar la tabla (campo auxiliar, no display primario)
- Añadir glosario corto de estados debajo de la tabla

---

### R2 — Dashboard multi-fase: capa 1 adaptativa

| Campo | Valor |
|---|---|
| **Objetivo** | Que la capa 1 cambie automáticamente su foco según la fase del sistema (discovery → learning → optimization) |
| **Impacto** | Muy alto a largo plazo |
| **Dificultad** | Alta |
| **Riesgo** | Alto — requiere definir y detectar la transición entre fases |
| **Prioridad** | Baja — no hacer hasta tener NOAA con >= 20 casos/ciudad |
| **Archivos** | `bot.py` (`build_dashboard_focus_center`), `templates/dashboard.html` |
| **Dependencias** | R1, instrumentación I4 |
| **Sesión aparte** | Sí — sesión de diseño separada antes de implementar |

---

### R3 — Log de skips: por qué no entró en cada ciudad por ciclo

| Campo | Valor |
|---|---|
| **Objetivo** | Registrar para cada ciclo: ciudad escaneada + razón de no entrada + edge calculado |
| **Impacto** | Muy alto estratégicamente — imposible aprender del no-trade sin este log |
| **Dificultad** | Media |
| **Riesgo** | Bajo — no toca reglas de trading, solo añade instrumentación al scan |
| **Prioridad** | Media |
| **Archivos** | `bot.py` (loop de scan en ciclo principal), nuevo archivo `skip_log.jsonl` en Volume |
| **Dependencias** | Ninguna |
| **Sesión aparte** | Sí |

---

## Instrumentación nueva

Datos que hoy no se recogen y que habilitarán aprendizaje estratégico.

---

### I1 — NOAA MAE del día del trade en trade_lifecycle

| Campo | Valor |
|---|---|
| **Objetivo** | Enriquecer cada trade con el valor observado NOAA del día del mercado, si existe |
| **Impacto** | Alto — permite correlacionar calidad del forecast con resultado del trade |
| **Dificultad** | Media |
| **Riesgo** | Bajo |
| **Prioridad** | Media |
| **Archivos** | `bot.py` (`_merge_trade_lifecycle_context()`), `trade_lifecycle.json` |
| **Dependencias** | NOAA con suficiente cobertura (>= 10 casos) |
| **Sesión aparte** | No |

---

### I2 — Edge stability tracker

| Campo | Valor |
|---|---|
| **Objetivo** | Registrar el edge calculado en cada ciclo posterior a la entrada (no solo al abrir) para medir estabilidad del modelo |
| **Impacto** | Alto — un edge inestable sugiere ruido; uno estable sugiere señal real |
| **Dificultad** | Media |
| **Riesgo** | Bajo |
| **Prioridad** | Baja (requiere primero suficiente muestra de trades) |
| **Archivos** | `bot.py` (`manage_positions()`, `trade_lifecycle.json`) |
| **Dependencias** | I1 |
| **Sesión aparte** | Sí |

---

### I3 — Correlación NOAA MAE × WR por ciudad en el dashboard

| Campo | Valor |
|---|---|
| **Objetivo** | Mostrar en el dashboard si el MAE de NOAA correlaciona con el WR de los trades de esa ciudad |
| **Impacto** | Muy alto — es la validación fundamental de que NOAA mejora las decisiones |
| **Dificultad** | Media |
| **Riesgo** | Bajo |
| **Prioridad** | Baja ahora, alta cuando n >= 10 por ciudad |
| **Archivos** | `bot.py` (`build_dashboard_city_observation()`), `templates/dashboard.html` |
| **Dependencias** | NOAA con >= 10 casos por ciudad, I1 |
| **Sesión aparte** | Sí |

---

## Orden recomendado de ejecución (post-rediseño)

### Fase 2 — Operativa (próximas sesiones)

```
M2 ✅ shadow_city_tracking + city_policy_state persisten (sesión 78)
M4 ✅ resumen diario Telegram 08 UTC (sesión 78, v10.6.11)
M5 ✅ alerta ciudad candidata a canary (sesión 78, v10.6.11)
```

### Fase 3 — Refactors con impacto

```
R1 → motor de ciudades con 3 gates          (después de M2)
R3 → log de skips por ciclo                 (sesión propia)
```

### Fase 4 — Instrumentación y aprendizaje

```
I1 → NOAA MAE en trade_lifecycle
I3 → correlación NOAA × WR
I2 + R2 → edge stability + capa 1 adaptativa   (largo plazo)
```

### Reglas de corte

- No empezar R1 sin tener M2 (persistencia confirmada)
- No empezar R2 (capa adaptativa) sin >= 20 casos NOAA por ciudad
- M5 (alerta canary) solo tiene valor si M2 confirma que shadow_tracking persiste
- I3 solo tiene valor cuando hay >= 10 casos NOAA por ciudad
- Evaluar subir ciclos de 3x/dia a 4-6x/dia solo después de validar que la muestra shadow crece bien
