# Post-Phase2 Strategy Experiments — Matriz design-only

**Fecha:** 2026-05-13
**Autor:** Opus (design-only)
**Estado:** DESIGN_ONLY — no autoriza cambios

---

## Scope y restricciones

- **DESIGN_ONLY.** Este documento describe palancas candidatas para evaluar throughput/monetización después de que Phase 2 cierre.
- **No autoriza cambios antes de T+30.** T+30 = cierre de Phase 2 = **2026-06-09**. Ninguna palanca aquí se ejecuta antes de esa fecha.
- **No reabre BANKROLL.** Bankroll $25 sigue firmado. Subir cap requiere proceso separado, fuera de este doc.
- **No es Fase C.** Esto no extiende ni redefine el roadmap Phase 2 / Phase 3. Es input para una futura revisión Opus post-Phase2.
- **No toca:** city modes, whitelist, scheduler, SL/intra guard, trading core, entry rules, gates, kill-switches, `ACTIVE_TRADING_CITIES`, condition filters, runtime de producción.
- **Uso previsto:** input estructurado para una revisión Opus post-cierre Phase 2 que decida qué experimentos (si alguno) priorizar.

---

## Premisas de estado actual (2026-05-13)

- Phase 2 abierta hasta **2026-06-09**.
- DB throughput con slots flojos (cohorte real activa subdimensionada por diseño).
- `condition=exact` dominante en cohorte canary.
- Cross-check traders disponible como señal observada, no como filtro de entry.
- Traders Intelligence y SL/intra readout pendientes de readout limpio post-cierre.
- Gate v1 canary→active congelado (n≥5, WR≥60%, PnL≥+$1, days≥7). No se relaja.
- S341 (`condition_filtered` kill-switch, commit 47ee558) activo.
- A8 (SL_intra guard v10.6.40) en estado ESPERAR_MÁS_MUESTRA.

---

## Palancas candidatas

### L1 — Activar 1 ciudad real vía gate v1 (Tokyo/Shanghai/Seoul)

- **Impacto esperado:** desbloquear throughput real (>0 trades Active/semana). Pasa de WR=100% n=1 a evidencia accionable con muestra real.
- **Riesgo:** drawdown sobre bankroll firmado si la cohorte canary no era representativa. Single-city = varianza alta.
- **GO/NO-GO:** gate v1 existente (n≥5, WR≥60%, PnL≥+$1, days≥7 medidos post-Phase2). No se modifica el umbral.
- **Contamina Phase 2:** sí, si se activa antes del 2026-06-09. Esperar cierre + readout limpio.
- **Dependencias:** `maybe_alert_v2_trigger` ya implementado (handoff 2026-04-13).

### L2 — Relajar S341 (condition_filtered) con whitelist estrecha

- **Impacto esperado:** condition exact deja de monopolizar la cohorte. Reabre signals hoy filtradas, sube throughput sin tocar entry rules.
- **Riesgo:** S341 fue killed por razón concreta (commit 47ee558). Reactivar sin diferenciar subcohortes reimporta el WR malo previo.
- **GO/NO-GO:** readout post-Phase2 muestra subcohorte `condition_filtered` con WR≥55% n≥30 en ventana shadow Phase 2. Sin n suficiente → NO-GO automático.
- **Contamina Phase 2:** no si se diseña ahora y se aplica después. Sí si se toca el switch durante la ventana.

### L3 — Cross-check traders como filtro de confirmación (no entry)

- **Impacto esperado:** mejora WR marginal del top tail de cohorte exact sin reducir throughput. Convierte Traders Intelligence en señal de "size up" o veto, no en gate.
- **Riesgo:** sobreajuste a histórico de traders observados; lookahead bias si la fuente tiene lag variable; latencia operativa añadida.
- **GO/NO-GO:** A/B shadow post-Phase2 — cohorte con cross-check vs sin, WR uplift ≥5pp con n≥30 cada brazo.
- **Contamina Phase 2:** no si se loggea passive (no afecta decisión) durante Phase 2. Sí si filtra entries.

### L4 — Reabrir SL_intra con guard refinado (A8 readout)

- **Impacto esperado:** recupera signals SL_intra hoy skipeadas por v10.6.40 guard, condicional a leverage-real. n=2 actual (+$1.12) no decide.
- **Riesgo:** A8 marcado ESPERAR_MÁS_MUESTRA. Reabrir prematuro = regreso al sangrado de -$3.95 n=10.
- **GO/NO-GO:** ≥5 SL_intra guarded con WR≥60% y PnL acumulado positivo. Re-check natural 2026-05-21 o al 5º guarded.
- **Contamina Phase 2:** no si el guard no cambia. Sí si se afloja durante la ventana.

### L5 — Multi-city Active staggered (post-L1 validado)

- **Impacto esperado:** diversifica varianza. Pasa de 1 ciudad a 2–3 ciudades Active con cap por ciudad.
- **Riesgo:** correlación entre ciudades (cohortes simultáneas, mismo régimen meteo) puede no diversificar tanto como sugiere el conteo nominal.
- **GO/NO-GO:** L1 con ≥4 semanas Active, WR≥55% n≥10, drawdown máximo <30% bankroll firmado. Cap por ciudad sobre bankroll vigente al momento de la decisión.
- **Contamina Phase 2:** no, ocurre mucho después.

---

## Regla común — qué contaminaría Phase 2

Cualquier intervención que durante la ventana hasta 2026-06-09 modifique:

- entry rules, gates, kill-switches;
- `ACTIVE_TRADING_CITIES`, whitelist, condition filters;
- SL_intra guard;
- bankroll efectivo en producción;
- la composición de la cohorte medida.

**No contaminan:** análisis, diseño, audits read-only, dashboards passive, memorias, este documento.

---

## Orden recomendado para después de T+30 (post 2026-06-09)

1. **Readout Phase 2 limpio** — cohorte cerrada, descontar drift documentado. Decisión hold/release del gate v1.
2. **L1 (1 ciudad Active)** vía gate v1 existente. Sin tocar nada más. Ventana mínima 4 semanas.
3. **L3 (cross-check passive logging)** en paralelo a L1 — acumular n para decisión futura sin afectar entries.
4. **L4 (SL_intra re-evaluación)** según calendario A8 (independiente de L1/L3).
5. **L2 (S341 relax)** solo si readout muestra subcohorte recuperable. Más arriesgado, más tarde.
6. **L5 (multi-city)** solo después de L1 firmado con n≥10 y bankroll subido por proceso separado.

Principio: validar antes de diversificar; passive antes de active; refinar guards antes de aflojar kill-switches.

---

## Próximo paso

Revisión Opus post-Phase2 (post 2026-06-09) toma este documento como input, lo confronta con el readout real de cierre, y decide qué palancas (si alguna) pasan a diseño detallado. Este doc no se ejecuta solo.
