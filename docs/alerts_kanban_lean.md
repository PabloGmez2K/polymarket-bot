# Alerts & Kanban Lean — Diseño Estratégico

**Versión:** 1.0  
**Fecha:** 2026-05-06  
**Autor:** Sonnet 4.6 (documentación) / Revisión estratégica: Opus  
**Estado:** DISEÑO — sin implementación activa  

---

## DISCLAIMER OBLIGATORIO

> **Las alertas descritas en este documento NO son señales de trading.**
>
> - Telegram NO autoriza BUY / SELL / SKIP.
> - Telegram NO autoriza cambios de BANKROLL.
> - Telegram NO autoriza activación de Fase C.
> - Todo cambio de riesgo requiere revisión separada y aprobación explícita.
> - `calibration_global=0.789` con `n_resolved=19` valida la cañería del Truth Pipeline, **no el bot como sistema rentable**.
> - Ningún monitor en este documento puede modificar parámetros de trading, sizing, whitelist, city modes, scheduler, STOP_LOSS_PCT, take_profit ni environment variables productivas.
> - Todo monitor nuevo empieza **LOG_ONLY / default OFF** y requiere revisión antes de activación Telegram real.

---

## 1. Veredicto Ejecutivo (Opus — mayo 2026)

**Clasificación de estado:** `WATCH_RISK`

El bot lleva operaciones reales desde aproximadamente 2026-03-28. A la fecha del cierre de Truth Pipeline Fase 1 observacional mínima (2026-05-05), el diagnóstico honesto es:

| Dimensión | Estado |
|-----------|--------|
| Win Rate histórico | ~36–40% sobre serie limpia, insuficiente para rentabilidad sostenida |
| P/L 7d limpio | Aproximadamente plano/negativo una vez descontado batch antiguo |
| Calibración Truth Pipeline | 78.9% con n=19 — valida la cañería, no el edge |
| BANKROLL | $25 — matemáticamente inviable para "pagar Claude Max" |
| Fase C | No autorizada |
| Escalado de bankroll | Bloqueado; no hay evidencia suficiente de edge sostenible |

**Conclusión operativa:** El bot debe tratarse como **I+D**, no como sistema de ingresos. El objetivo inmediato es validar si existe edge sostenible, no aumentar operaciones ni buscar rentabilidad a corto plazo.

**Próximo enfoque recomendado:** Sistema de alarmas Telegram + Kanban Lean para observar el sistema con disciplina, sin intervenciones prematuras.

---

## 2. Marco Lean Six Sigma / DMAIC aplicado al bot

El marco DMAIC (Define → Measure → Analyze → Improve → Control) se aplica al ciclo de mejora del bot:

| Fase DMAIC | Traducción al bot | Estado actual |
|------------|-------------------|---------------|
| **Define** | Definir qué es "edge sostenible": WR ≥55% con n≥50 en serie limpia, P/L 30d positivo, calibration_global ≥0.80 con n_resolved≥30 | Definido en documentos de política |
| **Measure** | Truth Pipeline (calibración), P/L Reconciliation, trade_lifecycle, SL Retrospective, Blocked Signals | Instrumentación básica activa |
| **Analyze** | Taxonomía de alarmas, Kanban de evidencias, auditorías read-only | **Fase actual** |
| **Improve** | Cambios solo cuando la evidencia supera umbrales predefinidos y Opus aprueba | Diferido hasta evidencia suficiente |
| **Control** | Guardrails en `verify_before_deploy.py`, confirmación Opus/revisión separada antes de cada cambio de riesgo | En vigor |

La trampas habituales de Six Sigma que el bot debe evitar:

- **Mejorar antes de medir:** ya ocurrió en fases tempranas; ahora se mide primero.
- **Confundir varianza con señal:** n=19 en Truth Pipeline no es evidencia operativa.
- **Sobre-ajustar:** cambios de lógica de trading cada semana destruyen la capacidad de medir.

---

## 3. Los 7 desperdicios Lean mapeados al sistema

| Desperdicio Lean | Manifestación en el bot | Mitigación |
|-----------------|------------------------|------------|
| **Sobreproducción** | Implementar features antes de validar edge | Checklist "evidencia antes de código" |
| **Espera** | Truth Pipeline esperando n_resolved≥30 sin vigilancia | Monitor C (Truth Pipeline Organic Growth) |
| **Transporte** | Datos en múltiples JSONLs sin fuente canónica | Paths live-first ya implementados |
| **Sobreprocessamiento** | Alertas que nadie lee porque hay demasiadas | Anti-spam: hash dedupe, cooldown, digest |
| **Inventario** | Trades open no reconciliados, estados zombie | Monitor D (P/L Reconciliation) |
| **Movimiento** | Revisar Railway manualmente sin protocolo | Daily Bot Kanban Digest (Monitor K) |
| **Defectos** | Bugs descubiertos post-deploy | `verify_before_deploy.py` como net de seguridad |

---

## 4. Taxonomía de alarmas

Todas las alarmas del sistema siguen esta jerarquía. Los monitores solo pueden emitir niveles dentro de su scope autorizado.

### Niveles NO_ACTION / WATCH

| Nivel | Significado | Acción requerida |
|-------|-------------|-----------------|
| `NO_ACTION` | Sistema sano, sin anomalía | Ninguna |
| `WATCH` | Anomalía observable, sin urgencia | Anotar; revisar si persiste |
| `WATCH_AUDIT` | Anomalía en datos o cobertura, no en trading | Auditoría de datos; sin cambios de trading |
| `WATCH_TECH` | Anomalía técnica (DB, red, parsing) | Revisar logs; sin cambios de trading |
| `WATCH_RISK` | Señal de riesgo sistémico o de bankroll | Revisión manual separada antes de cualquier cambio |

### Niveles ACTION

| Nivel | Significado | Acción requerida |
|-------|-------------|-----------------|
| `ACTION_ANALYSIS` | Requiere análisis manual | Revisar evidencias; no implementar hasta concluir análisis |
| `ACTION_DESIGN` | Requiere diseño de solución | Documentar antes de implementar |
| `ACTION_COPY` | Solo cambio de texto/copy | Puede implementar Sonnet + review |
| `ACTION_TOOLING` | Requiere nueva herramienta de observabilidad | Implementar LOG_ONLY; Opus revisa antes de activar |
| `ACTION_LOGIC_CANDIDATE` | Candidato a cambio de lógica de trading | NUNCA implementar sin: revisión Opus + evidencia n≥30 + aprobación explícita |
| `ACTION_SAFETY` | Anomalía de seguridad o riesgo inmediato | DETENER operación relacionada; escalar a Opus inmediatamente |

---

## 5. Kanban propuesto

### Columnas y WIP limits

| Columna | Descripción | WIP limit |
|---------|-------------|-----------|
| `BACKLOG` | Tareas identificadas, no priorizadas | Sin límite |
| `READY` | Tarea priorizada con evidencia suficiente para iniciar | Sin límite |
| `DOING` | En implementación activa | **2** |
| `WAITING_EVIDENCE` | Implementado, esperando evidencia de campo | **5** |
| `BLOCKED` | Impedimento externo o falta de evidencia | **3** |
| `WATCH` | Observación activa, no requiere acción | Sin límite |
| `DONE` | Completado y validado | Sin límite |
| `DEFERRED` | Pospuesto explícitamente | Sin límite |
| `SAFETY` | Relacionado con ACTION_SAFETY; prioridad máxima | **1** |

### Reglas de flujo

- Una tarjeta en `DOING` solo avanza a `DONE` si `verify_before_deploy.py` pasa y hay commit documentado.
- Una tarjeta en `WAITING_EVIDENCE` avanza a `DONE` si la evidencia supera el umbral definido al crear la tarjeta.
- Una tarjeta puede retroceder de `WAITING_EVIDENCE` a `BLOCKED` si la evidencia muestra que el cambio fue contraproducente.
- `SAFETY` tiene prioridad sobre todo; bloquea nuevas entradas en `DOING` hasta resolverse.
- Cualquier `ACTION_LOGIC_CANDIDATE` requiere aprobación Opus antes de entrar en `READY`.

---

## 6. Catálogo de monitores

### Resumen

| ID | Nombre | Nivel máx. | Estado | Prioridad |
|----|--------|-----------|--------|-----------|
| A | Profitability Monitor | `WATCH_RISK` | Diseño | Alta |
| B | Low Activity Monitor | `WATCH` | Diseño | Alta |
| C | Truth Pipeline Organic Growth | `WATCH_AUDIT` | Diseño | Alta |
| D | P/L Reconciliation Monitor | `ACTION_ANALYSIS` | Parcialmente implementado | Media |
| E | Bankroll Scaling Blocker | `WATCH_RISK` | Implementado (bot.py) | Media |
| F | SL/Guard Risk Monitor | `ACTION_SAFETY` | Implementado (LOG_ONLY) | Alta |
| G | Shadow Edge Monitor | `WATCH` | Diseño | Baja |
| H | Trader Cross-check Monitor | `WATCH_AUDIT` | Implementado (bot.py) | Media |
| I | Technical Health Monitor | `WATCH_TECH` | Parcialmente (Railway logs) | Media |
| J | Telegram Hygiene Monitor | `NO_ACTION` | Diseño | Alta |
| K | Daily Bot Kanban Digest | `NO_ACTION` | **Próximo paso** | **Máxima** |

### Monitores A, B, C — Diseño detallado

#### Monitor A — Profitability Monitor

**Objetivo:** Detectar degradación sostenida de rentabilidad antes de que cause daño irreversible al bankroll.

**Fuentes de datos:**
- `data/trade_lifecycle.json`
- `data/pnl_reconciliation_state.json`
- `data/wallet_portfolio_snapshots.jsonl`

**Umbrales:**
| Métrica | `NO_ACTION` | `WATCH` | `WATCH_RISK` |
|---------|------------|---------|-------------|
| WR últimos 20 trades cerrados | ≥45% | 35–45% | <35% |
| P/L 7d limpio | ≥$0 | −$3 a $0 | <−$3 |
| Drawdown últimos 5 cierres | <−$5 | −$5 a −$8 | <−$8 |

**Anti-spam:** Transición de nivel, no repetición. Hash del estado previo. Cooldown 24h entre emisiones del mismo nivel.

**Salida:** Resumen diario solo si nivel ≥ `WATCH`. Incluye: "Esta alerta no autoriza cambios de trading ni de bankroll."

**Implementación:** LOG_ONLY primero. Telegram real solo tras revisión.

---

#### Monitor B — Low Activity Monitor

**Objetivo:** Alertar cuando el bot lleva muchos ciclos sin comprar, lo que puede indicar que el mercado se agotó o que los filtros son demasiado restrictivos.

**Fuentes de datos:**
- `data/agent_events.jsonl` (ciclos recientes)
- `data/trade_lifecycle.json` (último trade)

**Umbrales:**
| Período sin BUY | Nivel |
|----------------|-------|
| < 3 días | `NO_ACTION` |
| 3–7 días | `WATCH` |
| > 7 días | `WATCH_AUDIT` (posible cambio de condiciones de mercado) |

**Anti-spam:** Una alerta por transición de umbral, no diaria.

**Nota:** Baja actividad puede ser correcto (mercado sin oportunidades). No se interpreta como "bug" sin evidencia adicional.

**Implementación:** LOG_ONLY primero. Telegram real solo tras revisión.

---

#### Monitor C — Truth Pipeline Organic Growth

**Objetivo:** Notificar cuando el Truth Pipeline acumula suficientes registros resueltos para habilitar revisiones operativas.

**Fuentes de datos:**
- Reporter Truth Pipeline (`truth_pipeline_reporter.py`)
- DB Railway: `truth_records`, `n_resolved`, `calibration_global`

**Hitos y notificaciones:**
| Hito | Nivel | Acción |
|------|-------|--------|
| `n_resolved` alcanza 30 | `WATCH_AUDIT` | Abrir revisión operativa de calibración |
| `n_resolved` alcanza 50 | `ACTION_ANALYSIS` | Evaluar promoción a Fase 2 del pipeline |
| `calibration_global` baja de 0.65 con n≥10 | `WATCH_RISK` | Revisar fetcher y cobertura |
| Ciudad específica baja de 0.50 con n≥5 | `WATCH_AUDIT` | Auditoría de ciudad |

**Anti-spam:** Cada hito se notifica una sola vez. El drift de calibración tiene cooldown 72h.

**Implementación:** LOG_ONLY primero. No activa Truth Pipeline runtime.

---

### Monitor J — Telegram Hygiene Monitor

**Objetivo:** Detectar si el bot está enviando demasiados mensajes Telegram, o si hay silencio inesperado (posible crash), sin crear un loop de alertas-sobre-alertas.

**Fuentes de datos:**
- `data/alerts_state.json` (timestamps de última alerta por tipo)
- Logs Railway (conteo de "TELEGRAM" en últimas 24h, estimado)

**Umbrales:**
| Situación | Nivel |
|-----------|-------|
| Tasa normal (1–5 mensajes Telegram/día) | `NO_ACTION` |
| Alta tasa (>10 mensajes/día) | `WATCH` (posible loop de alertas) |
| Silencio >48h en bot activo con posiciones open | `WATCH_TECH` |

**Anti-spam:** Este monitor no envía mensajes Telegram (paradoja anti-spam). Solo loguea a `data/telegram_hygiene_log.jsonl`. El digest K lo incluye como sección.

**Implementación:** LOG_ONLY puro. Sin Telegram propio nunca.

---

### Monitor K — Daily Bot Kanban Digest

**Objetivo:** Consolidar el estado diario del bot en un único mensaje Telegram estructurado, reemplazando la dispersión de alertas individuales para el ciclo de revisión humana de fin de jornada.

**Estructura del digest:**
```
🤖 Bot Kanban Digest — YYYY-MM-DD HH:MM UTC

📊 ESTADO GENERAL: [NO_ACTION / WATCH / WATCH_RISK]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 BANKROLL & P/L
  • Bankroll: $XX.XX
  • P/L 7d limpio: ±$X.XX
  • WR últimos 20: XX%
  • Drawdown últimos 5: ±$X.XX

📈 ACTIVIDAD
  • Trades cerrados (7d): N
  • Posiciones open: N
  • Último BUY: hace N días
  • Ciclos sin BUY: N

🔬 TRUTH PIPELINE
  • n_resolved: N / umbral 30
  • calibration_global: X.XXX
  • Estado: [observación orgánica / umbral alcanzado]

⚠️ ALERTAS ACTIVAS
  • [lista de alertas ≥ WATCH en últimas 24h, o "Ninguna"]

📋 KANBAN
  DOING: [item] | [item]
  WAITING_EVIDENCE: N items
  BLOCKED: [item si aplica]
  SAFETY: [item si aplica, o "OK"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Este digest no autoriza cambios de trading, BANKROLL ni Fase C.
```

**Frecuencia:** Una vez por día, hora configurable (default: misma hora que P/L Reconciliation).

**Anti-spam:** Solo una emisión por día. Si hay `ACTION_SAFETY` activo, el digest incluye aviso prominente pero no bloquea el envío.

**Implementación — Próximo paso (LOG_ONLY / default OFF):**
- `tools/daily_kanban_digest.py`: CLI stdlib-only que lee múltiples fuentes y genera el texto del digest en JSON.
- `bot.py`: integración en `run_observability_alerts()` con `KANBAN_DIGEST_ENABLED=0` default.
- Dry-run local primero. Telegram real solo tras revisión separada.
- No lee ni modifica bot.py, trading core, BANKROLL, whitelist, city modes ni scheduler.

---

## 7. Reglas anti-ruido

El problema más destructivo de un sistema de alertas es el ruido: si hay demasiadas alertas, se ignoran todas.

### Reglas obligatorias para todo monitor nuevo

1. **Transición, no repetición:** Un monitor solo alerta cuando el estado *cambia* (de `NO_ACTION` a `WATCH`, etc.), no en cada ciclo.

2. **Hash dedupe:** Antes de enviar, calcular hash del contenido. Si el hash coincide con el último enviado, suprimir.

3. **Cooldown:** Mínimo 24h entre dos alertas del mismo monitor al mismo nivel (excepto `ACTION_SAFETY`).

4. **Daily digest primero:** Para nivel `WATCH` o inferior, acumular en el digest K en vez de enviar alerta individual.

5. **Quiet hours:** No enviar alertas entre 23:00 y 07:00 UTC (excepto `ACTION_SAFETY`).

6. **Siguiente paso concreto:** Toda alerta debe incluir una acción específica ("Revisar `data/trade_lifecycle.json` para los últimos 5 cierres") en vez de mensajes genéricos ("algo está mal").

7. **No alerts about no alerts:** El Monitor J nunca usa Telegram. El digest K puede incluir "sin alertas hoy" pero no envía un mensaje extra para decirlo.

---

## 8. Reglas de escalado y des-escalado

### Escalado (nivel sube)

Un monitor puede subir de nivel si:
- La métrica supera el umbral durante **3 ciclos consecutivos** (no un pico aislado).
- Una segunda métrica independiente confirma la anomalía.
- El nivel anterior fue `WATCH` durante más de 7 días sin resolución.

### Des-escalado (nivel baja)

Un monitor baja de nivel si:
- La métrica vuelve a rango normal durante **2 ciclos consecutivos**.
- La condición original fue resuelta y hay commit documentado.
- Opus aprueba explícitamente el des-escalado en sesión de revisión.

### Promoción de monitor (LOG_ONLY → Telegram real)

Un monitor puede pasar de LOG_ONLY a Telegram real si:
1. Ha corrido en LOG_ONLY durante **≥14 días**.
2. Los logs muestran **0 falsos positivos** en ese período.
3. El formato del mensaje fue revisado y aprobado por el usuario.
4. Opus revisa el riesgo de la activación.

---

## 9. Roadmap 1–2 semanas

### Semana 1 (diseño y dry-run)

| Día | Tarea | Agente | Criterio de completado |
|-----|-------|--------|----------------------|
| 1–2 | Documentar diseño Monitor K (este doc) | Sonnet | Commit en main |
| 3–4 | Implementar `tools/daily_kanban_digest.py` CLI | Codex | Dry-run local OK, sin Telegram |
| 5–7 | Integrar en `bot.py` con `KANBAN_DIGEST_ENABLED=0` | Codex | `verify_before_deploy.py` pasa, LOG_ONLY confirmado |

### Semana 2 (observación y revisión)

| Día | Tarea | Agente | Criterio de completado |
|-----|-------|--------|----------------------|
| 1–3 | Observar logs del digest en Railway (sin Telegram) | Pablo | 3 días de logs limpios |
| 4–5 | Revisar formato y contenido del digest | Pablo + Sonnet | Aprobación explícita del formato |
| 6–7 | Activar Telegram real si aprobado | Opus revisa | Cooldown 24h post-activación sin falsos positivos |

---

## 10. Qué hacer primero

**Único próximo paso autorizado:**

> Implementar `tools/daily_kanban_digest.py` como CLI dry-run / LOG_ONLY / `KANBAN_DIGEST_ENABLED=0` por defecto.

**Criterios de "listo para iniciar":**
- Este documento está commiteado.
- No hay `ACTION_SAFETY` activo.
- No hay tarjeta en `DOING` relacionada con trading core.

**Agente responsable:** Codex implementa la CLI y la integración `bot.py`. Sonnet revisa el diseño si hay ambigüedad. Opus revisa antes de activar Telegram real.

---

## 11. Qué NO hacer

- **No activar Telegram real** sin haber corrido LOG_ONLY ≥14 días sin falsos positivos.
- **No subir BANKROLL** hasta que Truth Pipeline tenga n_resolved≥30 con calibration_global≥0.80 Y Opus apruebe.
- **No activar Fase C** (automatización de sizing/whitelist) hasta evidencia mucho más robusta.
- **No implementar ACTION_LOGIC_CANDIDATE** sin: evidencia n≥50, análisis Opus, aprobación explícita.
- **No interpretar calibration_global=0.789 como validación del bot**: es validación de la cañería del pipeline.
- **No interpretar P/L 7d bruto positivo como señal de mejora**: el batch antiguo contamina la lectura.
- **No crear nuevos monitores ejecutables** sin diseño documentado y aprobación.
- **No hacer replace_all en CONTEXTO.md o HISTORIAL_SESIONES.md**: siempre insertar al inicio, nunca reemplazar.

---

## 12. Honestidad comercial

### La meta "pagar Claude Max con $25" es matemáticamente inviable

Con BANKROLL $25 y un fee/spread mínimo de ~2% por trade, necesitaríamos:
- Costo mensual Claude Max: ~$20
- ROI mensual requerido: **80%** sobre el capital total
- En ningún mercado financiero competitivo existe un edge sostenible del 80% mensual

**Conclusión:** El bot debe tratarse como **proyecto de I+D**. El objetivo no es pagar Claude Max; es aprender si existe un edge estadísticamente significativo en mercados de predicción meteorológica en Polymarket. Si se demuestra edge (WR≥55%, n≥50, P/L positivo 30d, calibration≥0.80), se puede escalar responsablemente. Hasta entonces, el BANKROLL es presupuesto de investigación.

---

## 13. Handoffs entre agentes

| Tarea | Agente | Condiciones |
|-------|--------|------------|
| Documentación y diseño de monitores | Sonnet | Sin restricciones; este archivo |
| Implementación de tools CLI (LOG_ONLY) | Codex | Solo implementa lo que Sonnet diseña y el usuario aprueba |
| Revisión de riesgo y promoción de nivel | Opus | Antes de ACTION_LOGIC_CANDIDATE, activación Telegram real, escalado BANKROLL, o ACTION_SAFETY |
| Revisión diaria operativa | Pablo | Leer digest K; escalar si ve algo inusual |

**Protocolo de handoff Sonnet → Codex:**
1. El diseño está documentado con inputs, outputs, umbrales y anti-spam claros.
2. El documento especifica qué archivos toca y qué NO toca.
3. `verify_before_deploy.py` debe pasar tras la implementación.
4. Commit local sin push; Pablo revisa antes.

**Protocolo de handoff Codex → Opus (revisión de riesgo):**
1. Han pasado ≥14 días de LOG_ONLY sin falsos positivos.
2. Existe un log de las últimas emisiones del monitor.
3. El usuario solicita explícitamente la revisión.
4. Opus puede decir "no" y devolver la tarjeta a `WAITING_EVIDENCE` con criterios más altos.

---

*Este documento es un diseño estratégico. No contiene código ejecutable. No autoriza cambios en el sistema de trading.*
