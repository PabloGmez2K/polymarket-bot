# Revisión Estratégica Opus — 2026-04-17

**Tipo:** Revisión estratégica quincenal  
**Modelo:** Claude Opus 4.6  
**Fecha:** 2026-04-17  
**Budget al momento:** $9.45 | Exposición: $0.01

---

## Diagnóstico Ejecutivo

### Situación

El sistema no está monetizando de forma repetible. 71 ciclos (11 días) con 7 buys totales desde el 6 de abril. La sensación de "iterar en círculos" es correcta y tiene causa estructural identificable.

### Principal error de enfoque

Las semanas recientes se invirtieron en observabilidad (city intelligence, phase5, slot metrics, slot 04h), que son trabajo correcto pero atacan el **tercer y cuarto cuello de botella**. El primero y segundo no se han tocado.

### ¿Estamos más cerca de monetizar?

**No**, en términos de buys/ciclo. Sí en términos de diagnóstico: esta revisión identifica la causa raíz por primera vez con datos concretos.

---

## Evidencia Central

### Colapso de throughput con v10.6

| Período | Ciclos | Edges/ciclo | Buys/ciclo | Total buys |
|---|---:|---:|---:|---:|
| Pre-Apr6 (v10.4-10.5) | 41 | **4.6** | **0.98** | 40 |
| Apr6-12 (v10.6 canary) | 33 | 0.2 | 0.15 | 5 |
| Apr13+ (v10.6 +04h) | 38 | 0.1 | 0.05 | 2 |

### PnL real por condición (trade_lifecycle, 72 trades)

| Condición | Trades | WR | PnL |
|---|---:|---:|---:|
| `at_or_above` | 11 | **60%** | **+$0.97** |
| `at_or_below` | 4 | 0% | -$0.06 |
| `exact` | 20 | 29% | **-$9.26** |
| `range` | 25 | 9% | **-$23.94** |

### Funnel actual: condition_filtered mata ~47% de mercados

Cada ciclo: ~26 candidatos totales → ~12 muertos por `condition_filtered` (exact/range) → ~14 llegan a edge → 0-1 tienen edge → 0-1 compras.

### Blocked signals: traders aciertan 76% en exact/range (n=59)

La señal existe en esos mercados. El problema no es el tipo de condición sino el modelo del bot para calcular edge en esas condiciones.

### Position management: 48% de cierres son micro_position_unsellable

29 de 61 posiciones cerradas murieron sin poder venderse. 4 de 61 (7%) cerraron con take_profit. El bot también corta winners demasiado pronto: $7+ dejados en mesa en solo 3 casos.

---

## Mapa de Cuellos de Botella

| # | Cuello | Severidad | Estado |
|---|---|---|---|
| 1 | Modelo de probabilidad exact/range roto | CRÍTICO | No atacado |
| 2 | Position management (micro_pos, exit timing) | ALTO | No atacado |
| 3 | Universo canary estrecho | MEDIO | Derivado del #1 |
| 4 | Whitelist canary cities incompleta | MEDIO | Fix en esta sesión |
| 5 | 23h slot sin valor neto | BAJO | Fix en esta sesión |
| — | City intelligence expansión | ROI bajo | Pausar |
| — | Phase5 visibility | ROI bajo | Pausar |

---

## Decisiones de esta revisión

### Ejecutar ya (Semana del 17 de abril)

- **S1**: Confirmar quality trader gate activo (ya estaba activo — Seoul exact Apr16 lo prueba)
- **S2**: Agregar Atlanta, London, NYC, Munich a `QUALITY_TRADER_CITIES_WHITELIST` ← **ejecutado**
- **S4**: Apagar slot 23h (`SCHEDULE_DISABLED_HOURS_UTC=23` en Railway)

### Ejecutar esta semana (Codex + Sonnet)

- **C1**: Autopsia de 45 trades exact/range perdidos → identificar causa raíz del modelo
- **C3**: Benchmark sigma exact vs above/below → ¿es un problema de calibración de probabilidad?
- **S3**: Investigar y mitigar micro_position_unsellable

### Parar / no continuar

- Expansión city intelligence pipeline (17/26 ciudades "insufficient")
- Más refinamiento slot_metrics
- Phase5 visibility refinement
- Observación pasiva extendida 23h

---

## Criterios de Éxito (para próxima revisión Opus)

| Gate | Métrica | Target | Kill |
|---|---|---|---|
| 1 | markets_evaluated / ciclo | ≥25 | — |
| 2 | with_edge / ciclo | ≥0.5 | — |
| 3 | buys / ciclo | ≥0.3 | — |
| 4 | WR exact/range canary | ≥40% | <25% n≥10 |
| 5 | Ciudad promocionable | ≥1 ciudad con n≥15 y WR≥45% | — |

**Próxima revisión Opus:** Semana del 24 de abril de 2026.  
El objetivo no es que todo esté resuelto, sino que tengamos datos de al menos 5-7 días con el quality trader gate activo para medir si el cuello #1 se movió.
