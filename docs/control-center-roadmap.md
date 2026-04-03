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

## Quick wins

Cambios sin riesgo de regresión. No tocan la lógica de trading ni el deploy.

---

### QW1 — Eliminar `legacy-focus-shell`

| Campo | Valor |
|---|---|
| **Objetivo** | Limpiar código HTML muerto que contamina el template |
| **Impacto** | Legibilidad del template; sin efecto visible en el dashboard |
| **Dificultad** | Mínima |
| **Riesgo** | Ninguno (ya está `hidden`) |
| **Prioridad** | Alta |
| **Archivos** | `templates/dashboard.html` |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

---

### QW2 — Mover Legacy drift a capa 3

| Campo | Valor |
|---|---|
| **Objetivo** | Sacar el bloque "Drift Open-Meteo" de la zona de Observabilidad activa |
| **Impacto** | Reduce ruido en capa 2; Legacy drift no es comparable con NOAA activo |
| **Dificultad** | Mínima |
| **Riesgo** | Ninguno |
| **Prioridad** | Alta |
| **Archivos** | `templates/dashboard.html` |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

---

### QW3 — Reordenar capa 2: NOAA y Decision engine primero

| Campo | Valor |
|---|---|
| **Objetivo** | Reflejar la prioridad real de la fase actual: NOAA/coverage es el cuello de botella, pero aparece al final de capa 2 |
| **Impacto** | Alto: la información más relevante pasa a estar visible sin bajar 7 secciones |
| **Dificultad** | Baja |
| **Riesgo** | Ninguno |
| **Prioridad** | Alta |
| **Archivos** | `templates/dashboard.html` |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

**Orden objetivo:**
```
[Capa 2]
  1. Estado operativo compacto
  2. NOAA calidad + Decision engine / Ranking   ← subir aquí
  3. Stats de trading
  4. Checklist bankroll
  5. Eficiencia de exits (colapsada si muted)
  6. Trade console
```

---

### QW4 — Alarma "sin ciclo en >12h" en Mission HUD

| Campo | Valor |
|---|---|
| **Objetivo** | Detectar bot caído antes del próximo ciclo de 8h |
| **Impacto** | Crítico operativamente — hoy no hay forma de saber desde el dashboard si el bot está corriendo |
| **Dificultad** | Baja |
| **Riesgo** | Bajo — solo añade lógica de lectura en `build_dashboard_focus_center()` |
| **Prioridad** | Crítica |
| **Archivos** | `bot.py` (función `build_dashboard_focus_center`), `templates/dashboard.html` |
| **Dependencias** | Requiere leer `cycle_summary.json` para obtener el timestamp del último ciclo |
| **Sesión aparte** | No, pero toca Python |

---

### QW5 — Timestamp "último fetch NOAA exitoso"

| Campo | Valor |
|---|---|
| **Objetivo** | Hacer visible cuándo fue el último caso NOAA guardado exitosamente |
| **Impacto** | Detecta pipeline NOAA roto sin necesidad de revisar logs de Railway |
| **Dificultad** | Baja |
| **Riesgo** | Ninguno |
| **Prioridad** | Alta |
| **Archivos** | `bot.py` (`build_dashboard_forecast_quality`), `templates/dashboard.html` |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

---

### QW6 — Mini-cards: "esperando muestra" cuando n < 5

| Campo | Valor |
|---|---|
| **Objetivo** | Evitar que PnL serie, Win rate y Drawdown se lean como señal cuando la muestra es insuficiente |
| **Impacto** | Medio — elimina lectura ruidosa de métricas con n < 5 trades limpios |
| **Dificultad** | Mínima |
| **Riesgo** | Ninguno |
| **Prioridad** | Media |
| **Archivos** | `templates/dashboard.html` (condición Jinja existente, ampliar umbral) |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

---

### QW7 — Colapsar Readiness y Desbloqueos

| Campo | Valor |
|---|---|
| **Objetivo** | Reducir redundancia con los tracks de Progress en capa 1 |
| **Impacto** | Medio — elimina secciones que duplican información ya visible en capa 1 |
| **Dificultad** | Mínima |
| **Riesgo** | Ninguno |
| **Prioridad** | Media |
| **Archivos** | `templates/dashboard.html` |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No |

---

## Mejoras medianas

Requieren más trabajo pero no cambian la arquitectura core.

---

### M1 — Mega-card Observabilidad → 3 tabs

| Campo | Valor |
|---|---|
| **Objetivo** | Dividir el mega-card de Observabilidad en 3 tabs: `NOAA \| Ciudades \| Decisiones` |
| **Impacto** | Alto — es el bloque más denso del dashboard; imposible de leer de un vistazo |
| **Dificultad** | Media |
| **Riesgo** | Bajo — solo reorganización de HTML, mismos datos y variables Jinja |
| **Prioridad** | Alta |
| **Archivos** | `templates/dashboard.html`, `static/dashboard.js` (activar tabs nuevos) |
| **Dependencias** | QW3 (para no confundir con el reordenamiento previo) |
| **Sesión aparte** | Sí — dedicar una sesión específica |

**Estructura objetivo:**
```
Tab NOAA:       calidad forecast + últimos 20 casos
Tab Ciudades:   estado por ciudad + universo operativo + bloqueadas
Tab Decisiones: decision engine + ranking + canary/shadow + transiciones
```

---

### M2 — Verificar persistencia de shadow_tracking y city_policy_state en Volume

| Campo | Valor |
|---|---|
| **Objetivo** | Confirmar que los dos archivos críticos para el motor de ciudades persisten entre deploys |
| **Impacto** | Crítico — si `shadow_tracking` no persiste, la autopromoción a canary nunca se dispara |
| **Dificultad** | Baja (solo verificación + documentar) |
| **Riesgo** | Ninguno |
| **Prioridad** | Crítica — hacer antes de confiar en ninguna autopromoción |
| **Archivos** | Railway Volume `/app/data/`, `CONTEXTO.md` (actualizar tabla de datos persistentes) |
| **Dependencias** | Ninguna |
| **Sesión aparte** | No — puede hacerse en 15 minutos desde Railway |

**Verificación:**
```bash
rtk railway run -- ls /app/data/ | grep -E "shadow|city_policy"
```

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

### M4 — Resumen diario Telegram (08:00 UTC)

| Campo | Valor |
|---|---|
| **Objetivo** | Reemplazar múltiples alertas de estado con un único resumen diario agrupado |
| **Impacto** | Alto — reduce dependencia del dashboard para seguimiento operativo diario |
| **Dificultad** | Media |
| **Riesgo** | Bajo — no toca trading, solo observabilidad |
| **Prioridad** | Alta |
| **Archivos** | `bot.py` (nueva función `send_daily_summary_telegram()`), `alerts_state.json` (flag de envío) |
| **Dependencias** | M3 (para que el WR de Chicago no distorsione el resumen) |
| **Sesión aparte** | Sí |

**Contenido del resumen:**
1. Ciclos ejecutados en las últimas 24h + oportunidades detectadas/tomadas
2. Resoluciones del día (ganadas/perdidas + importes)
3. NOAA nuevos casos por ciudad + acumulado
4. Estado del sistema: HP, versión, próximo ciclo estimado

---

### M5 — Alerta "ciudad candidata a canary" en Telegram

| Campo | Valor |
|---|---|
| **Objetivo** | Notificar cuando una ciudad shadow cumple la regla de promoción, antes de ejecutar automáticamente |
| **Impacto** | Alto — añade gate de revisión humana antes de que el bot empiece a hacer BUYs en una ciudad nueva |
| **Dificultad** | Baja |
| **Riesgo** | Ninguno — es observabilidad, no acción |
| **Prioridad** | Alta |
| **Archivos** | `bot.py` (`sync_city_policy_state()`), `alerts_state.json` |
| **Dependencias** | M2 (verificar que shadow_tracking persiste) |
| **Sesión aparte** | No — puede hacerse junto con M4 |

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

## Orden recomendado de ejecución

### Fase 1 — Corrección y quick wins (sin deploy de riesgo)

```
M2 → verificar shadow_tracking en Volume    (15 min, Railway)
QW4 → alarma "sin ciclo en >12h"            (toca Python, riesgo bajo)
M3 → cerrar 3 filas Chicago legacy open     (sesión 70 ya planificada)
QW1 + QW2 + QW3 + QW6 + QW7 → HTML puro    (sesión rápida, cero riesgo)
QW5 → timestamp NOAA                        (junto con QW4)
```

### Fase 2 — Mejoras de experiencia (después de Fase 1)

```
M1 → mega-card en 3 tabs                    (sesión propia, solo HTML)
M4 + M5 → resumen diario + alerta canary    (sesión propia, Python)
```

### Fase 3 — Refactors con impacto

```
R1 → motor de ciudades con 3 gates          (después de M2 + M3)
R3 → log de skips                           (sesión propia)
```

### Fase 4 — Instrumentación y aprendizaje

```
I1 → NOAA MAE en trade_lifecycle
I3 → correlación NOAA × WR
I2 + R2 → edge stability + capa 1 adaptativa   (largo plazo)
```

### Reglas de corte

- No empezar R1 (refactor motor) sin tener M2 (persistencia confirmada) y M3 (WR Chicago corregido)
- No empezar R2 (capa adaptativa) sin >= 20 casos NOAA por ciudad
- M5 (alerta canary) solo tiene valor si M2 confirma que shadow_tracking persiste
- I3 solo tiene valor cuando hay >= 10 casos NOAA por ciudad
