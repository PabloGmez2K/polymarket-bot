# Auditoría del Control Center — Polymarket Bot

**Fecha:** 3 de abril de 2026  
**Versión analizada:** v10.6.10  
**Fase del sistema:** Discovery / Stabilization  
**Fuentes:** `templates/dashboard.html`, `bot.py:4367-5200`, `CONTEXTO.md`, `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json`

---

## Índice

1. [Estructura actual del dashboard](#1-estructura-actual)
2. [Fidelidad de datos](#2-fidelidad-de-datos)
3. [Utilidad operativa real](#3-utilidad-operativa-real)
4. [UX y arquitectura de información](#4-ux-y-arquitectura-de-información)
5. [Motor de ciudades y scoring](#5-motor-de-ciudades-y-scoring)
6. [Alertas de Telegram](#6-alertas-de-telegram)
7. [Dashboard como herramienta estratégica](#7-dashboard-como-herramienta-estratégica)
8. [Mapa de fuentes y confianza](#8-mapa-de-fuentes-y-confianza)

---

## 1. Estructura actual

El dashboard tiene 3 capas:

### Capa 1 — Mission HUD
- Hero header (modo, versión, serie, timestamp)
- Mission card: System HP + 2 tracks + acción recomendada
- Pipeline de prioridad (stage_path)
- Tabs: **Overview** (5 Q&A cards + incidentes + drivers) | **Progress** (tracks con barras) | **Cities** (city race NOAA + operator console)

### Capa 2 — Seguimiento y explicación _(cajón de sastre)_
1. Stats bar: Nivel / Siguiente nivel / Ciclos / Trades limpios
2. Checklist subida de bankroll + Estado operativo + Portfolio + Alertas
3. Readiness operativo + Desbloqueos
4. Mini-cards: PnL serie / Win rate / Cierres / Drawdown
5. Eficiencia de exits (trade_analytics)
6. Trade console (tabs: Resumen / Trades)
7. **Mega-card de Observabilidad** (NOAA + ciudad observation + decision engine + ranking + canary/shadow + shadow table + transiciones + universo operativo + bloqueadas + últimos 20 casos NOAA)

### Capa 3 — Detalle extendido `<details>` colapsado
- Balance por tipo de cierre
- Trofeos + Scoreboard de agentes
- Ciclos + Posiciones abiertas

---

## 2. Fidelidad de datos

### Desfases activos confirmados

**Desfase 1 — Doble capa de bloqueo que puede diverger (CRÍTICO)**  
`BLOCKED_CITIES` env de Railway y `auto_blocked_cities` en `city_policy_state.json` son independientes. Si Railway se reinicia y el Volume no persiste la política, el bloqueo auto desaparece sin alarma.

**Desfase 2 — 3 filas Chicago legacy `open` sesgan WR (ALTO)**  
Confirmado en CONTEXTO.md sesión 69. Las filas `2026-03-26`, `2026-03-27`, `2026-03-28` siguen con `status=open`. El WR 25% de Chicago que muestra el dashboard puede ser incorrecto.

**Desfase 3 — Shadow tracking puede resetearse en deploys (CRÍTICO)**  
`shadow_tracking` no aparece en la lista de datos persistentes del Volume de Railway en CONTEXTO.md. Si no persiste, el ranking de ciudades y las decisiones de autopromoción a canary se reconstruyen desde cero en cada deploy. **La autopromoción a canary nunca se dispara si esto es así.**

**Desfase 4 — Dallas inconsistente entre Railway y bot**  
`ACTIVE_TRADING_CITIES` en Railway incluye Dallas, pero CONTEXTO.md sesión 69 dice "Dallas degradada a shadow por overlay". El dashboard puede mostrarla como activa mientras el motor la resuelve como shadow.

### Métricas que pueden inducir a error

| Métrica | Problema |
|---|---|
| `readiness_score` 0-99 | Mezcla shadow (prospectivo), NOAA (observacional), trading real (histórico) y city_mode (+24 por estar activa). Opaco e inestable. |
| `health_score` 0-100 | Heurística: -45 bankroll + -35 signals = score 20 aunque el sistema opere bien. |
| Win rate / PnL por ciudad | Sesgado por filas legacy `open` (Chicago confirmado). |
| Eficiencia de exits | Se calcula aunque `market_seen_after_close` sean solo 2-3 casos. Score parece preciso con muestra mínima. |
| Mini-cards PnL/WR serie | Con n < 5 cierres limpios son ruido estadístico presentado como señal. |
| `trend_label` "Subiendo" | Puede dispararse con 1 solo edge shadow. |

### Checks y alarmas que faltan

- **"Sin ciclo en >12h"** como incidente en Mission HUD — el bot puede estar caído sin que el dashboard lo detecte
- **"Shadow tracking: ¿persistido?"** — check de integridad del motor de ciudades
- **"Filas legacy open en postmortem"** — aviso visible cuando hay posiciones `open` con fecha > 7 días
- **"Último fetch NOAA exitoso"** timestamp visible — el pipeline puede fallar silenciosamente

### Instrumentación adicional recomendada

**A 1 mes:**
- Timestamp del último ciclo exitoso + tiempo transcurrido
- Confirmar que `shadow_tracking` y `city_policy_state.json` están en la lista de archivos persistentes del Volume
- Flag de integridad de postmortem: cuántas filas tienen `status=open` con fecha > 7 días

**A 3 meses:**
- Log de "skip": ciudad + razón + edge calculado cuando el bot decide no entrar
- `market_seen_after_close` cubierto sistemáticamente (hoy es fortuito)
- Calibración real del readiness_score: ¿qué scores tenían ciudades que resultaron exitosas vs fallidas?
- Correlación NOAA MAE × WR por ciudad

---

## 3. Utilidad operativa real

### La capa 1 está conceptualmente bien — con un problema estructural

Las 5 preguntas del Mission HUD son correctas para la fase actual. Pero el código está **hardcoded** para discovery/stabilization. Si el sistema entra en fase learning, la capa 1 no cambia automáticamente su foco.

### Qué sobra hoy (carga cognitiva sin valor)

- `legacy-focus-shell` en el HTML — ya está `hidden`, es código muerto
- Legacy drift Open-Meteo — mezclado con NOAA activo, debería estar en capa 3
- Readiness operativo (capa 2) — duplica el tab Progress de la capa 1
- Desbloqueos (capa 2) — parcialmente duplica los Drivers del Mission HUD
- Mini-cards PnL/WR cuando n < 5 — más ruido que señal
- Trofeos y Scoreboard de agentes — motivacional, no operativo

### Qué falta para lectura inmediata de acción

| Decisión operativa | Estado actual | Gap |
|---|---|---|
| ¿Tocar trading hoy? | En Mission HUD (acción recomendada) | Falta: "¿hubo oportunidades en el último ciclo?" |
| ¿Priorizar NOAA? | En Drivers y Progress (duplicado) | No queda claro si ya se tomó acción |
| ¿Revisar exits? | En Eficiencia de exits | Sin señal clara de cuándo revisar vs solo observar |
| ¿Revisar ranking ciudades? | En Decision engine (final de capa 2) | Un auto-block nuevo no sube a capa 1 |
| ¿El bot está corriendo? | No hay indicador explícito | Falta alarma de "sin ciclo en >12h" |

### El problema de orden más importante

En la fase actual, **NOAA/coverage es el cuello de botella dominante** según el propio Mission HUD. Sin embargo, el bloque de Observabilidad/NOAA/Decision engine está al final de la capa 2, después de 7 secciones de datos de trading. El orden actual es:

```
1. Stats nivel/ciclos
2. Checklist bankroll
3. Estado operativo
4. Readiness + Desbloqueos  ← redundante
5. PnL/WR/drawdown mini-cards
6. Eficiencia de exits
7. Trade console
8. NOAA + Decision engine  ← DEBERÍA ESTAR AQUÍ ARRIBA
```

### Clasificación de la información actual

| Nivel | Elementos |
|---|---|
| **Acción ahora** | System HP degradado, Incidentes, Acción recomendada, Ciudad auto-bloqueada recientemente |
| **Vigilar** | NOAA progress, candidatas a canary, pending exits, flagged cities |
| **Solo referencia** | PnL/WR con muestra pequeña, Trofeos, Scoreboard agentes, último ciclo |
| **No tocar hoy** | Exit efficiency con confidence=muted, Legacy drift, Historial de ciclos |

---

## 4. UX y arquitectura de información

### Densidad: muy alta

Más de 25 secciones distintas antes de llegar a la capa 3. El mayor problema es el **mega-card de Observabilidad**: un solo `<article>` que contiene al menos 7 dimensiones distintas (NOAA quality, city observation, decision engine, ranking, overlay activo, shadow reciente, historial de transiciones). Imposible de leer de un vistazo.

### Redundancias confirmadas

| Par redundante | Impacto |
|---|---|
| City race (capa 1) ↔ Universo operativo (capa 2) | Mismas ciudades + NOAA progress en dos formatos |
| Progress tab ↔ Readiness operativo | Mismos checks en dos lugares |
| Incidentes (capa 1) ↔ Alertas activas (capa 2) | Potencial duplicación |
| Trade analytics quick_stats ↔ Trade console total_cards | Contenido muy similar |
| Drivers (capa 1) ↔ Desbloqueos (capa 2) | Ambos responden "¿qué limita ahora?" |

### Etiquetas confusas

- **"Readiness operativo"** (checklist de trading) vs **"Readiness score"** (de ciudades) — mismo nombre, dos conceptos
- **"Seguir observando"** — no especifica qué tipo de observación (shadow, NOAA, histórico)
- **"Shadow degradada"** vs **"Bloqueada"** — ambas tienen badge rojo; diferencia semántica no obvia sin glosario
- **"Dejado de ganar"** — sin nota de que solo existe cuando hay `market_seen_after_close`
- **"Canary"** — sin glosario; significado no autoevidente

### Estado real de las capas

| Capa | Definición formal | Realidad |
|---|---|---|
| Capa 1 | "¿Sano?, ¿intervenir?" | Bien definida y limpia |
| Capa 2 | "Información secundaria para entender capa 1" | Cajón de sastre con 9 bloques heterogéneos |
| Capa 3 | "Detalle extendido" | Bien: colapsada en `<details>` |

Lo que hay realmente en capa 2: finanzas + trading metrics + readiness + NOAA learning + city management + decision engine. Las dos últimas son prioritarias en esta fase pero están al final.

### Propuesta de orden recomendado (fase actual)

```
[CAPA 1] Mission HUD — MANTENER
[CAPA 2]
  1. Estado operativo compacto (1 barra: versión, ciclos, próx. ciclo, signals)
  2. NOAA calidad + Decision engine / Ranking de ciudades   ← MOVER AQUÍ
  3. Stats de trading (con aviso "muestra pequeña" si n < 10)
  4. Checklist subida de bankroll
  5. Eficiencia de exits (colapsada si confidence=muted)
  6. Trade console (colapsada por defecto)
[CAPA 3] — MANTENER, añadir Legacy drift
```

### Patrón de navegación recomendado

- **Mantener tabs** del Mission HUD
- **Dividir mega-card de Observabilidad** en 3 tabs: `NOAA | Ciudades | Decisiones`
- **Colapsar en `<details>`**: Readiness, Desbloqueos, Eficiencia de exits cuando confidence=muted, Trade console
- **Eliminar**: `legacy-focus-shell` (código muerto)
- **Accordion** para lista de 11 ciudades bloqueadas

---

## 5. Motor de ciudades y scoring

### Mapa de estados actual

| Estado | Definición | Efecto en trading |
|---|---|---|
| `active` | En `ACTIVE_TRADING_CITIES` y no bloqueada | BUYs normales |
| `canary` | En `auto_canary_cities` de `city_policy_state.json` | BUYs con sizing reducido |
| `shadow` | No activa; bot observa sin comprar | Registra edge_hits, cycles_seen, best_edge_pct |
| `blocked` | En `BLOCKED_CITIES` ENV o `auto_blocked_cities` | Sin BUYs; manage_positions sigue activo |
| `shadow degradada` | Fue active/canary, degradada por mal historial | Igual que shadow |
| `reference` | Tiene trades históricos sin NOAA ni shadow | Solo informativa |

### Problemas del readiness_score actual

```python
# Fórmula actual (simplificada)
score += min(30, shadow_edges * 12)      # hasta 30 pts
score += min(18, shadow_cycles * 8)      # hasta 18 pts
score += min(12, best_edge/min_best * 12) # hasta 12 pts
score += 6 if noaa_configured
score += min(16, observed/goal * 16)     # hasta 16 pts
score += 6 if interpretable
if history_bad: score -= 28
elif pnl>0 or wr>=50: score += 10
if active: score += 24                   # ← PROBLEMA PRINCIPAL
elif canary: score += 18
if promotable_shadow: score = max(score, 82)
if blocked: score = min(score, 8)
...
```

**Problema 1 — Bonus +24 por `city_mode="active"` es dominante.**  
Una ciudad active con 0 trades, 0 NOAA, 0 shadow edges → score 24. Mide "está operando" más que "merece operar".

**Problema 2 — `support_count = max(observed_count, trades, shadow_cycles)` no tiene coherencia.**  
10 observaciones NOAA, 10 trades ejecutados y 10 ciclos shadow no son equivalentes.

**Problema 3 — El score no distingue calidad de shadow edges.**  
1 edge a 25% y 1 edge a 8.1% (justo sobre el mínimo) pesan igual.

**Problema 4 — Shadow tracking puede no persistir.**  
Si `shadow_tracking` no está en Railway Volume, `shadow_edges` y `shadow_cycles` se resetean en cada deploy. La autopromoción a canary nunca se dispara.

**Problema 5 — Contradicción promotable + history_bad.**  
`if promotable_shadow: score = max(score, 82)` se aplica después de `score -= 28` por history_bad. Una ciudad con mal historial pero buenos shadow edges puede rescatar su score a 82 automáticamente si no está bloqueada/degradada.

### Evaluación del score actual

| Criterio | Veredicto |
|---|---|
| Interpretable | No — ver "67" no dice qué mejorar |
| Estable | Parcialmente — depende de shadow_tracking |
| Accionable | Solo los "gaps de canary" son accionables; el número no |
| Resistente a muestra pequeña | No — con 1-2 edges fluctúa fuertemente |

### Propuesta: 3 gates en lugar de score único

```
GATE A — Historial real
  LIMPIO   → n_trades < threshold  ó  (WR > 25% Y PnL > $0)
  ZONA ROJA → removable_active = True

GATE B — Shadow readiness
  LISTA      → promotable_shadow = True
  ACUMULANDO → shadow_seen > 0, no cumple todo
  VACÍO      → shadow_seen = 0

GATE C — NOAA coverage
  INTERPRETABLE → observed_count >= min_sample
  EN PROGRESO  → configurada pero < min_sample
  SIN DATOS   → no configurada

DECISIÓN = aplicar gates en orden → 1 línea de texto
```

Mantener `readiness_score` como campo de **ordenación** de tabla, pero no mostrarlo como número primario.

### Contradicciones detectadas con ciudades actuales

| Ciudad | Contradicción |
|---|---|
| Chicago | WR 25% pero PnL +$2.09 → el motor no saca porque PnL positivo. Correcto por diseño, pero no está explicado en el dashboard. |
| Dallas | En `ACTIVE_TRADING_CITIES` Railway pero con overlay shadow. El display puede inducir a creer que está activa. |
| Buenos Aires | Activa sin NOAA configurado → operamos sin ninguna validación observada. El +24 por `active` compensa la ausencia de NOAA en el score. |

### Display recomendado por ciudad

```
Chicago         [ACTIVA]
  Historial: ✓  4 trades | WR 25% | PnL +$2.09
  Shadow:    —  No aplica (ya activa)
  NOAA:      ◐  0/10 casos | configurada
  Decisión: MANTENER — "PnL positivo; NOAA en progreso"

Dallas          [SHADOW overlay]
  Historial: ✓  sin historial malo
  Shadow:    ◐  X edges | Y ciclos
  NOAA:      ⚫  no configurada
  Decisión: OBSERVAR — "shadow por overlay manual"

Atlanta         [BLOQUEADA AUTO]
  Historial: ✗  23 trades | WR 17.4% | PnL negativo
  Decisión: BLOQUEADA — "auto-bloqueada 2026-04-03"
```

---

## 6. Alertas de Telegram

### Alertas que deberían existir

| Alerta | Tipo | Urgencia |
|---|---|---|
| Bot sin ciclo >12h | Tiempo real | CRÍTICA |
| Bankroll crítico | Tiempo real | CRÍTICA (ya existe) |
| Ciudad auto-bloqueada | Tiempo real | ALTA (parcialmente existe) |
| Pending exit > umbral | Tiempo real | ALTA (ya existe) |
| Ciudad candidata a canary | Tiempo real | MEDIA |
| Resumen operativo diario | 08:00 UTC agrupado | ÚTIL |
| NOAA bias fuera de rango | Diario/semanal | MEDIA |

### Alertas que son spam

- "Ciclo ejecutado" sin cambios relevantes
- "Signals.json stale" cuando el limitante real es NOAA (fase actual)
- Hitos NOAA n=1/2/3 — reducir a n=5/10/20
- "Ciudad bajo review" si ya está auto-bloqueada (duplicado)

### Payload recomendado para alertas críticas

```
[NIVEL] Título
Ciudad/Sistema: nombre
Qué pasó: descripción concisa
Métricas: evidencia mínima (n, WR, PnL)
Cambio vs anterior: diff explícito
Confianza: alta/media/baja (n=X)
Urgencia: crítica/alta/media
Acción: /focus · /accuracy · /noaa
```

### Automatismos seguros vs requieren revisión humana

| Automático seguro | Requiere revisión humana |
|---|---|
| Auto-block por accuracy (ya implementado) | Promoción a canary → alerta primero, BUY después de confirmación |
| Alertas de hitos NOAA | Cambios a `ACTIVE_TRADING_CITIES` Railway |
| `manage_positions` SL/TP | Reversión de bloqueos |

---

## 7. Dashboard como herramienta estratégica

### Datos que sí sirven para aprender hoy

- `postmortem.json`: WR y PnL por ciudad — base real de análisis
- `audit.json → observed_vs_forecast`: con 20+ casos por ciudad, MAE y bias por ciudad son muy valiosos
- `trade_lifecycle.json`: entry_context + exit_condition — con más trades, permite correlacionar condiciones de entrada con resultados
- `cycles_history.jsonl`: cuándo no hay oportunidades — patrón de activación del modelo

### Datos que faltan para aprender de verdad

| Gap | Impacto | Complejidad |
|---|---|---|
| Log de "skip": ciudad + razón + edge calculado | Muy alto — no se aprende del no-trade | Media |
| Settlement real (Weather Underground) | Muy alto — NOAA sigue siendo proxy | Alta |
| Edge stability: edge inicial vs ciclos posteriores | Alto — mide robustez del modelo | Media |
| Correlación NOAA MAE × WR por ciudad | Muy alto — valida que NOAA mejora decisiones | Media cuando n >= 10 |
| Contexto de mercado en entrada: liquidez, días abierto | Medio | Baja |

### Métricas estratégicas que faltan

- **Calibración por ciudad**: cuando el modelo da P=70%, ¿gana el mercado el 70% de las veces? (requiere n >= 10)
- **Edge stability**: ¿el edge al entrar se mantiene o fluctúa hasta el cierre?
- **Tiempo en posición vs resultado**: ¿trades cortos (1-2 días) tienen mejor resultado?

---

## 8. Mapa de fuentes y confianza

| Métrica/Bloque | Fuente | Confianza | Riesgo principal | Recomendación |
|---|---|---|---|---|
| System HP | alerts_state + portfolio API | Media | API falla → HP incorrecto | Mostrar "API error" explícito si portfolio=None |
| Mission acción | Lógica hardcoded | Media | Hardcoded para discovery phase | Revisitar cuando cambie la fase |
| NOAA progress | audit.json → observed_vs_forecast | Alta (cuando hay datos) | Pipeline puede fallar silenciosamente | Añadir timestamp "último fetch NOAA" |
| City ranking / readiness_score | shadow_tracking + postmortem + city_policy_state | Media-Baja | shadow_tracking puede perderse en deploys | **Verificar persistencia en Volume URGENTE** |
| WR / PnL por ciudad | postmortem.json | Media | 3 filas Chicago legacy open sesgan WR | Cerrar filas legacy (next step sesión 69) |
| Exit efficiency | trade_lifecycle.json | Baja (muestra pequeña) | Solo cuando hay market_seen_after_close | Mostrar n_observados/n_total siempre |
| Estado operativo / ciclos | cycle_summary.json + bot vars | Alta | Bot caído → last_cycle stale sin alarma | Añadir alarma "sin ciclo en >12h" |
| Portfolio live | API Polymarket | Alta cuando responde | Guard ya existe | Mantener |
| Alertas activas | alerts_state.json | Alta | One-shot → no se repite si condición persiste | Revisar alertas persistentes |
| Legacy drift | audit.json → forecast_vs_real | Muy baja (no real) | No compara vs Weather Underground | Mover a capa 3 |
| Scoreboard agentes | agent_events.jsonl | Media | Seed local puede diferir de Volume | Mantener como histórico |
