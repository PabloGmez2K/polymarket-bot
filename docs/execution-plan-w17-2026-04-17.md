# Plan de Ejecución — Semana 17, 2026-04-17

**Revisión estratégica base:** `docs/strategic-review-opus-2026-04-17.md`  
**Objetivo de la semana:** Completar las 6 tareas del bloque antes del 24 de abril para la próxima revisión Opus.  
**Budget actual:** $9.45

---

## Estado del bloque

| ID | Tarea | Agente | Estado | Sesión |
|---|---|---|---|---|
| S1 | Confirmar quality trader gate activo | Sonnet | ✅ COMPLETADO | Sesión A |
| S2 | Whitelist canary cities fix | Sonnet | ✅ COMPLETADO | Sesión A |
| S4 | Apagar slot 23h (Railway) | Sonnet | ✅ COMPLETADO | Sesión A |
| C1 | Autopsia trades exact/range perdidos | Opus | ✅ COMPLETADO | Sesión A |
| C3 | Benchmark sigma exact vs above/below | Opus | ✅ COMPLETADO | Sesión A (corolario de C1) |
| C1-fix | YES exact/range floor our_prob >= 65% | Opus | ✅ COMPLETADO | Sesión A |
| S3 | Mitigar micro_position_unsellable | Opus | ✅ CERRADO sin cambio | Sesión A |

**Bloque completo ejecutado en Sesión A.** Siguiente paso: observación + revisión Opus el 24 de abril.

---

## Sesión A — Completada (Sonnet, hoy 2026-04-17)

### Qué se hizo

**S1 — Quality trader gate (confirmado activo):**
- El gate ya estaba activo en código. Prueba: Seoul `exact` del 16 de abril pasó por el gate.
- No requirió cambios.

**S2 — Whitelist fix (cambiado en bot.py):**
- Se agregaron Atlanta, London, New York City, Munich al default de `QUALITY_TRADER_CITIES_WHITELIST`.
- Antes: `Seattle, Tokyo, Hong Kong, Seoul, Toronto, Chengdu, Shenzhen, Shanghai, Milan`
- Ahora: + `Atlanta, London, New York City, Munich`
- Impacto: las 4 ciudades canary que no podían operar exact/range ahora pueden hacerlo si hay quality trader signal.

**S4 — Slot 23h (pendiente Railway):**
- El código ya soporta `SCHEDULE_DISABLED_HOURS_UTC` (feature flag implementado).
- Requiere que apliques el env var en Railway (instrucción abajo).

### Qué hacer antes de cerrar esta sesión

1. Aplicar cambio en Railway para S4:
```powershell
.\tools\railway_safe.ps1 variables set SCHEDULE_DISABLED_HOURS_UTC=23
```

2. Hacer deploy del cambio de bot.py:
```powershell
python verify_before_deploy.py
# Si pasa → 
git add bot.py
git commit -m "config: add canary cities to QUALITY_TRADER_CITIES_WHITELIST default"
git push
```

3. Verificar en el próximo ciclo que:
   - Atlanta, London, NYC, Munich aparecen como candidatos en skip_log con `skip_reason != condition_filtered` cuando hay quality trader signal
   - 23h ya no aparece en cycles_history

---

## Sesión B — Autopsia exact/range (Codex)

### Cuándo abrir

Después de que tengamos al menos 3 ciclos con el nuevo whitelist activo (mínimo 12h post-deploy).

### Prompt para Codex

```
Lee AGENTS.md y el bloque reciente de CONTEXTO.md.

Tarea: Autopsia de los trades exact/range perdidos.

Contexto: El bot tiene WR 9-29% en exact/range, pero quality traders tienen 76% WR en esas mismas condiciones.
Queremos entender POR QUÉ el bot pierde en exact/range para decidir si el modelo necesita corrección.

Archivos a analizar:
- data/runtime_import/trade_lifecycle.json (72 trades, foco en exact=20 y range=25)
- data/runtime_import/performance.json (para entry price, forecast_max, our_prob, mkt_prob)
- data/runtime_import/skip_log.jsonl (últimas 2000 entradas)
- data/runtime_import_derived/blocked_signals_resolutions.jsonl (59 resoluciones)
- docs/strategic-review-opus-2026-04-17.md (contexto estratégico)

Preguntas a responder:
1. En los trades exact/range perdidos: ¿our_prob era alta y el mercado le dio la razón o no?
2. ¿Entramos siempre en el lado correcto (YES cuando forecast > threshold, NO cuando forecast < threshold)?
3. ¿Cuál fue el entry price promedio en exact/range vs at_or_above? ¿Compramos con mucha o poca liquidez?
4. En blocked_signals_resolutions: ¿en qué lado entró el trader? ¿Habría entrado el bot al mismo lado?
5. ¿Hay diferencia sistemática entre exact y range en el patrón de pérdida?

Salida esperada:
- Hipótesis principal sobre la causa raíz (modelo de prob / entry price / exit timing / lado equivocado)
- Tablas concretas con los datos que soportan la hipótesis
- Recomendación: ¿qué parámetro o función habría que corregir primero?

No cambiar ningún archivo excepto actualizar CONTEXTO.md si encuentras algo importante.
No tocar bot.py, Kelly, sigma, MIN_EDGE ni trading core.
```

### Qué esperar como salida

Un doc de análisis o respuesta directa con la hipótesis. Si Codex identifica que el problema es sigma para exact, eso alimenta directamente C3.

---

## Sesión C — Benchmark sigma (Codex)

### Cuándo abrir

Después de tener la hipótesis de C1. Si C1 dice "el problema es sigma", C3 va primero. Si dice "el problema es exit timing", C3 puede esperar.

### Prompt para Codex

```
Lee AGENTS.md y el bloque reciente de CONTEXTO.md.

Tarea: Benchmark del modelo de probabilidad para exact vs at_or_above/at_or_below.

Contexto: El bot tiene 60% WR en at_or_above pero 9-29% WR en exact/range.
Queremos saber si estimate_prob_with_city() produce probabilidades calibradas para cada tipo de condición.

Archivos a analizar:
- bot.py (función estimate_prob_with_city y get_uncertainty — sin modificar)
- data/runtime_import/trade_lifecycle.json (entry_context.our_prob vs resultados reales)
- data/runtime_import/audit.json (observed_vs_forecast si tiene datos)
- docs/strategic-review-opus-2026-04-17.md (contexto)
- Resultado de Sesión B (hipótesis sobre causa raíz)

Preguntas a responder:
1. Para condición exact: ¿qué sigma se usa? ¿Es razonable para un rango de ±0.5°C?
2. Para at_or_above/at_or_below: ¿qué sigma se usa? ¿Produce probabilidades más confiables?
3. ¿Hay evidencia de que our_prob es sistemáticamente demasiado alta en exact (lo que generaría edge ilusorio)?
4. ¿La función trata igual exact vs above/below en términos de distribución?

Salida esperada:
- Diagnóstico concreto: ¿sigma está bien calibrado para exact?
- Si no: ¿qué ajuste mínimo corregiría el problema?
- Propuesta de cambio (borrador de código si aplica) — sin tocar bot.py todavía

No implementar nada. Solo diagnóstico y propuesta.
```

---

## Sesión D — Mitigar micro_position_unsellable (Sonnet)

### Cuándo abrir

Después de completar C1 y C3. Necesitamos saber si el problema de exit es secundario o relacionado con el modelo.

### Objetivo

48% de posiciones cierran como `micro_position_unsellable`. Esto destruye el PnL realizado.

### Contexto para Sonnet

```
Lee AGENTS.md y el bloque reciente de CONTEXTO.md.

Tarea: Investigar y proponer fix para micro_position_unsellable.

Evidencia: 29 de 61 posiciones cerradas (48%) terminaron como micro_position_unsellable.
Esto significa que el bot compró y no pudo vender — la posición se volvió tan pequeña que la orden de venta falló.

Archivos a analizar:
- bot.py (buscar "micro_position_unsellable" — sin modificar todavía)
- data/runtime_import/trade_lifecycle.json (records con close_reason=micro_position_unsellable)
- data/runtime_import/performance.json (entradas con action=LOSS_TOTAL)
- docs/strategic-review-opus-2026-04-17.md (contexto)
- Resultados de sesiones B y C

Preguntas:
1. ¿Cuándo ocurre micro_position_unsellable? ¿Es por shares < umbral de venta? ¿Por precio < umbral?
2. ¿Las posiciones que mueren así tenían entry_price muy bajo (< 0.05)?
3. ¿Qué condición activa el label micro_position_unsellable en bot.py?
4. ¿Qué cambio mínimo en sizing o en la condición de venta lo resolvería?

Salida esperada:
- Diagnóstico de la causa exacta
- Propuesta de fix concreto (qué cambiar en bot.py, con diff)
- Estimación de impacto: ¿cuántas posiciones se hubieran salvado?

Si el fix requiere tocar bot.py, presentar el diff antes de implementar.
```

---

## Sesión de Cierre de Bloque (Sonnet)

### Cuándo abrir

Cuando S1, S2, S4, C1, C3 estén completos y S3 esté al menos diagnosticada.

### Qué hacer

1. Actualizar `CONTEXTO.md` con el estado post-bloque
2. Actualizar `HISTORIAL_SESIONES.md` con resumen de la semana
3. Añadir evento a `agent_events.jsonl`
4. Pull fresco de Railway para `data/runtime_import/`
5. Preparar prompt para la revisión Opus del 24 de abril

---

## Criterios de Éxito del Bloque

Para considerar el bloque completo y válido para la revisión Opus:

| Criterio | Qué medir |
|---|---|
| markets_evaluated / ciclo | ≥25 (vs 14-17 previo) |
| with_edge / ciclo | ≥0.5 (vs 0.1 previo) |
| buys / ciclo | ≥0.3 (vs 0.05 previo) |
| Hipótesis exact/range documentada | C1 completado con conclusión |
| Sigma diagnóstico cerrado | C3 completado con veredicto |

Si los primeros 3 criterios no se cumplen después de 5 días con el nuevo whitelist, el diagnóstico es que el quality trader signal no aparece con suficiente frecuencia → entonces C1 y C3 pasan a ser urgentes para recalibrar.

---

## Notas de Workflow

- **Siempre arrancar sesión nueva** con: leer AGENTS.md + bloque reciente CONTEXTO.md + el handoff de la sesión anterior
- **Siempre cerrar sesión** actualizando CONTEXTO.md si cambió algo de estado
- **Codex**: tareas de análisis read-only o refactors acotados, sin tocar arquitectura core
- **Sonnet**: implementación de cambios, fixes puntuales, Railway, deploy
- **Opus**: solo revisión estratégica — no para tareas de implementación
- **verify_before_deploy.py**: obligatorio antes de cualquier push que toque bot.py
