# P&L Observability — Contrato de Métricas 1D / 1W / 1M / ALL

**Status:** ACTION_DESIGN / WATCH_RISK / NOT_CANONICAL  
**Date:** 2026-05-06  
**Session:** 308 (Sonnet 4.6)  
**Classification:** ACTION_DESIGN / WATCH_RISK  

Este documento define la arquitectura read-only de observabilidad P&L del bot. Es documentación durable. No implementa runtime, no promueve `wallet_pnl`, y no autoriza cambios en BANKROLL, Fase C, whitelists, sizing, city modes, scheduler, reglas de riesgo, trading automático, BUY/SELL/SKIP ni Telegram accionable.

---

## A. Propósito

P&L Observability es la capa de medición **read-only / LOG_ONLY** del sistema. Su objetivo es acumular evidencia veraz, trazable y con etiquetas de confianza para:

- medir tendencia real del bot a lo largo del tiempo;
- identificar señales de calidad o degradación del sistema;
- informar **decisiones manuales** de Pablo con datos más confiables;
- alimentar el ciclo de mejora continua sin fabricar señales ejecutables prematuras.

**Lo que no es:**

- No es una señal ejecutable para BUY/SELL/SKIP.
- No desbloquea `BANKROLL`.
- No autoriza Fase C.
- No reemplaza la revisión Opus antes de cualquier uso operativo.
- No es canónico mientras `canonical_source=none`.

**Principio rector:** ninguna herramienta de observabilidad debe promover acciones operativas si la información no está suficientemente validada. La promoción requiere Opus review y Pablo signoff explícito.

---

## B. Capas de P&L

El sistema tiene seis capas conceptuales de P&L. Cada capa debe publicarse **siempre con etiqueta de fuente, calidad y confidence**. Sin esas etiquetas, la cifra no se publica.

### B.1 Realized P&L / closed trades

P&L de posiciones ya cerradas extraído de `trade_lifecycle.json`.

- **Estado actual:** `contaminated` — `contamination_rate=1.0`.
- **Uso permitido:** `non_canonical_telemetry` con disclaimer explícito. Nunca como base de BANKROLL, Telegram real con cifra, o decisión operativa.
- **Etiqueta obligatoria:** `source=trade_lifecycle`, `quality=contaminated`, `confidence=untrusted`.

### B.2 Wallet ΔP&L ajustado por cash flows

Variación de valor de la wallet entre dos snapshots, corregida por depósitos y retiros documentados en `wallet_cash_flows.jsonl`.

- **Estado actual:** `wallet_pnl_available=false`. El cash flow log no existe todavía (`cash_flows.status=missing`).
- **Uso permitido:** solo cuando `cash_flows.status=attested_full_7d` y cobertura ≥7d continua. Hoy bloqueado.
- **Etiqueta obligatoria:** `source=wallet_snapshot+cash_flow_log`, `quality=depends_on_coverage`, `confidence=low_until_attested_full_7d`.

### B.3 Open exposure / unrealized

Valor de posiciones abiertas a precio de mercado actual menos costo de entrada.

- **Estado actual:** visible en snapshots pero no computado de forma estructurada.
- **Uso permitido:** WATCH manual solamente. No combinable con realized P&L hasta que B.1 sea confiable.
- **Etiqueta obligatoria:** `source=wallet_snapshot`, `quality=mark_to_market_only`, `confidence=low`.

### B.4 Net liquidation / wallet value

Valor total de la wallet: cash + posiciones abiertas a precio de mercado.

- **Estado actual:** `total_value` disponible en `wallet_snapshot.py --report-only`.
- **Uso permitido:** WATCH. No usar como base de cálculo P&L hasta que la cobertura de cash flows esté atestiguada.
- **Etiqueta obligatoria:** `source=wallet_snapshot`, `quality=snapshot_only`, `confidence=medium`.

### B.5 Operational P&L observability

Capa de agregación que combina B.1–B.4 con horizonte temporal (1D/1W/1M/ALL) y produce métricas de tendencia. Requiere `tools/pnl_report.py` (futuro, Roadmap B3).

- **Estado actual:** no implementado. Bloqueado hasta B2 (Patch C), B3 (pnl_report.py) y B4 (integración Daily Digest).
- **Uso permitido:** LOG_ONLY / WATCH_AUDIT cuando esté implementado. No accionable.

### B.6 Data quality / confidence / source status

Metadatos de calidad que deben acompañar cualquier cifra publicada:

| Campo | Valores posibles |
|---|---|
| `source` | `trade_lifecycle`, `wallet_snapshot`, `cash_flow_log`, `dashboard_manual`, `combined` |
| `quality` | `contaminated`, `accumulating`, `attested_partial`, `attested_full_7d`, `missing`, `unreconciled` |
| `confidence` | `untrusted`, `low`, `medium`, `high` (solo tras Opus review) |
| `coverage_gap` | booleano; `true` si hay período sin attestation dentro del horizonte |

**Regla dura:** ninguna capa se publica sin sus tres etiquetas (`source`, `quality`, `confidence`). Una cifra sin etiqueta equivale a dato ausente.

---

## C. Contrato por horizonte

### Criterios Opus aplicados

- **1D:** wallet ΔP&L 24h preferido; realized 24h solo como cross-check; divergencia con dashboard ≤ ±$0.50.
- **1W:** wallet ΔP&L 7d preferido; realized 7d solo como ratio check; divergencia con dashboard ≤ ±$1.50.
- **1M:** wallet ΔP&L 30d preferido; dashboard mensual manual como alternativo; divergencia ≤ ±$3.00.
- **ALL:** wallet acumulado desde t0 + cash_flow_log íntegro.

### Tabla de contratos

| Horizonte | Fuente preferida | Fuente alternativa | Cuándo es canónico | Cuándo es provisional | Cuándo está bloqueado |
|---|---|---|---|---|---|
| **1D** | Wallet ΔP&L 24h (`wallet_snapshot` t-24h vs. t0) | Realized 24h de `trade_lifecycle` (cross-check) | Tras Opus review + `attested_full_7d` + pnl_report.py operativo | `cash_flows.status=attested_partial` y cobertura ≥24h continua | Hoy bloqueado: `cash_flows.status=missing`, `wallet_pnl_available=false` |
| **1W** | Wallet ΔP&L 7d | Realized 7d (ratio check solamente) | Tras Opus review + `attested_full_7d` continua + n_snapshots≥7 | `cash_flows.status=attested_partial` y cobertura ≥5d | Hoy bloqueado: `cash_flows.status=missing` |
| **1M** | Wallet ΔP&L 30d | Dashboard Polymarket mensual manual | Tras Opus review + ≥28d de attestations + n_snapshots≥28 | Primeros 30d post-t0 con cobertura parcial | Hoy bloqueado: cash_flow_log no existe |
| **ALL** | Wallet acumulado desde t0 + cash_flow_log íntegro | N/A | Tras Opus review + cash_flow_log completo post-t0 + reconciliación manual | Mientras sólo exista subconjunto de attestations | Hoy bloqueado: t0 no definido (Patch C no implementado) |

### Confidence esperado por horizonte

| Horizonte | Confidence actual | Confidence objetivo (post-Patch C + B3 + Opus) |
|---|---|---|
| 1D | `untrusted` | `medium` si divergencia ≤ ±$0.50 |
| 1W | `untrusted` | `medium` si divergencia ≤ ±$1.50 y n_snapshots≥7 |
| 1M | `untrusted` | `medium` si divergencia ≤ ±$3.00 y n_snapshots≥28 |
| ALL | `untrusted` | `high` solo tras revisión Opus dedicada |

### Riesgos de interpretación por horizonte

| Horizonte | Riesgos principales |
|---|---|
| 1D | Confundir ΔP&L diario con P&L realizado del día; ruido intra-día por mark-to-market de posiciones abiertas |
| 1W | Batches de resolución agrupados distorsionan la semana; unrealized contamina el delta si hay posiciones grandes abiertas |
| 1M | Depósitos o retiros no atestiguados invalidan el horizonte completo; sesgo de supervivencia si el mes coincide con un batch de liquidaciones |
| ALL | Pre-observability history no es comparable con post-t0; backfill no autorizado como canónico |

### Datos mínimos y gap invalidante

| Horizonte | Datos mínimos | Gap invalidante |
|---|---|---|
| 1D | 2 snapshots (t-24h y t0) + attestation continua 24h | Cualquier período >2h sin snapshot o sin attestation |
| 1W | 7 snapshots diarios + attestation continua 7d | Cualquier día sin snapshot o con `possible_deposit` no explicado |
| 1M | 28 snapshots diarios + attestation continua 28d | Cualquier brecha >1d o `adjustment` sin human review |
| ALL | cash_flow_log completo desde t0 sin brechas | Cualquier período sin attestation explícita post-t0 |

---

## D. Definición de t0 ALL

- **t0 ALL** = primera entrada válida del `cash_flow_log` post-Patch C con `type=no_cash_flow_attestation` o `type=deposit`/`type=withdrawal`, creada manualmente por Pablo con `--write --init`.
- **Histórico previo a t0** = `pre_observability`. Toda evidencia anterior a t0 queda bajo la etiqueta `pre_observability` y no puede usarse como base canónica del horizonte ALL.
- **No backfill retroactivo canónico.** Si alguna vez se requiere reconstruir evidencia anterior a t0, ese diseño requiere una sesión Opus separada con Pablo signoff explícito antes de cualquier intento.
- **ALL canónico no reescribe historia anterior.** El horizonte ALL mide desde t0 hacia adelante; no es un intento de reconciliar toda la actividad del bot desde su origen.

---

## E. Mapa de componentes

Los siguientes componentes forman el pipeline de P&L Observability:

### E.1 Componentes existentes

| Componente | Rol | Estado |
|---|---|---|
| `tools/wallet_snapshot.py` | Captura snapshots de wallet y evalúa readiness de `wallet_pnl`. Lee `wallet_cash_flows.jsonl` para calcular `cash_flows.status`. | Implementado (Patch B') |
| `tools/daily_kanban_digest.py` | Agrega señales de calidad del sistema (incluyendo `pnl_sources`) en un resumen LOG_ONLY. | Implementado (Sesiones 298–302) |
| `data/wallet_portfolio_snapshots.jsonl` | Ledger de snapshots de wallet en Railway. Estado actual: `accumulating`, `phase2_ready=false`. | En acumulación |
| `trade_lifecycle.json` | Historial de trades cerrados. Estado actual: `contaminated`, `contamination_rate=1.0`. | `non_canonical_telemetry` |

### E.2 Componentes futuros (requieren signoff explícito)

| Componente | Rol | Prerequisito |
|---|---|---|
| `data/wallet_cash_flows.jsonl` (Patch C) | Ledger manual de cash flows atestiguados por Pablo. t0 del horizonte ALL. | Pablo signoff + `--write --init` manual |
| `tools/wallet_cash_flow_log.py` (Patch C) | CLI manual para registrar cash flows validados en `wallet_cash_flows.jsonl`. Diseño: `docs/wallet_cash_flow_log_design.md`. | Codex diff + Pablo review antes de merge |
| `tools/pnl_report.py` (Patch D — B3 del roadmap) | Herramienta read-only que produce métricas 1D/1W/1M/ALL con etiquetas de confidence. Nunca accionable. | Patch C operativo + Opus review del diseño |
| Patch D `missing → partial/available` | Mejora de `wallet_snapshot.py` para transicionar `cash_flows.status` más granular. | Patch C completado + test coverage |
| Fuente futura opcional `polymarket_api_pnl` | `external_observability` / sanity bound vía Data API pública (`/v1/leaderboard?user=…&timePeriod=DAY\|WEEK\|MONTH\|ALL`). Cross-check humano contra dashboard. **No** sustituye wallet ΔP&L ajustado, **no** es `canonical_source`, **no** desbloquea `bankroll_readiness`, BANKROLL $35, Fase C, BUY/SELL/SKIP ni Telegram accionable. Equivalencia con dashboard sin confirmar. Discovery: [`docs/research/polymarket_api_pnl_discovery.md`](research/polymarket_api_pnl_discovery.md). | Bloque futuro B3.1/B3.2 separado con diseño Opus + signoff Pablo antes de cualquier integración. Fuera del alcance de B3. |

### E.3 Trade lifecycle como non_canonical_telemetry

`trade_lifecycle.json` sigue siendo útil para:

- auditoría individual de trades;
- detección de anomalías puntuales;
- análisis de patrones de entrada/salida bajo etiqueta explícita.

No es útil para:

- P&L acumulado canónico;
- comparaciones de rendimiento entre períodos;
- BANKROLL o decisiones operativas.

Toda referencia a cifras de `trade_lifecycle` en el Daily Digest o en reportes debe ir marcada con `non_canonical_telemetry`.

---

## F. Daily Bot Kanban Digest

### F.1 Métricas ya visibles (LOG_ONLY / WATCH / WATCH_RISK)

| Métrica | Clasificación actual | Condición |
|---|---|---|
| `lifecycle.status` | WATCH_RISK | `contaminated` → nunca operativo |
| `lifecycle.contamination_rate` | WATCH_RISK | 1.0 → 100% de trades contaminados |
| `lifecycle.operational_use` | WATCH_AUDIT | `untrusted_only` |
| `wallet_pnl.status` | WATCH | `accumulating` |
| `wallet_pnl.phase2_ready` | WATCH | `false` |
| `cash_flows.status` | WATCH_RISK | `missing` → bloquea promoción |
| `bankroll_readiness` | WATCH_RISK | `blocked` |
| `canonical_source` | WATCH | `none` |
| `would_send` | LOG_ONLY | `false` mientras `canonical_source=none` |

### F.2 Métricas futuras (post-Patch C + pnl_report.py)

Estas métricas solo aparecen en el Digest cuando Patch C esté operativo, `pnl_report.py` esté implementado, y haya cobertura suficiente:

- P&L 1D / 1W / 1M / ALL con etiquetas de source/quality/confidence.
- `cash_flows.coverage_days_7d` ≥ 7.
- `wallet_pnl_7d` con confidence ≥ `medium`.

### F.3 Métricas bloqueadas (sin confianza suficiente)

Las siguientes cifras **no se muestran** en el Digest hasta que tengan source/quality/confidence válidos:

- Cualquier cifra P&L numérica de `trade_lifecycle` sin disclaimer explícito.
- `wallet_pnl_7d` mientras `wallet_pnl_available=false`.
- Delta de wallet sin attestation de cash flows.

### F.4 Métricas solo WATCH_AUDIT

- `lifecycle.pnl_*` de `trade_lifecycle` → únicamente para auditorías individuales, nunca como resumen de rendimiento.
- `wallet_portfolio_snapshots.jsonl` valor de wallet → WATCH acumulación, no P&L operativo.

### F.5 Reglas operativas del Digest

- **No mostrar cifras P&L canónicas mientras `canonical_source=none`.**
- **`would_send=false` mientras `canonical_source=none`** si existe cualquier riesgo de interpretación como señal operativa.
- **`trade_lifecycle` P&L → siempre `non_canonical_telemetry`** con disclaimer en el copy.
- Cualquier divergencia entre `wallet_pnl` y `lifecycle_pnl` superior a los umbrales del horizonte correspondiente debe elevar el nivel del Digest a `WATCH_RISK`.

---

## G. Clasificación Lean/Kanban

Los bloques del sistema de P&L Observability se clasifican según la siguiente taxonomía:

| Clasificación | Criterio |
|---|---|
| `NO_ACTION` | Estado sano, ninguna señal relevante. No enviar nada. |
| `WATCH` | Dato disponible, sin anomalía. LOG_ONLY silencioso. |
| `WATCH_AUDIT` | Métrica disponible pero con fidelidad baja o sin validación completa. Solo para revisión manual. |
| `WATCH_RISK` | Condición que puede implicar riesgo si se ignora. Requiere atención manual sin acción automática. |
| `ACTION_ANALYSIS` | Nueva evidencia que requiere análisis antes de decidir cualquier acción. |
| `ACTION_DESIGN` | Se ha tomado la decisión de diseñar una solución; implementación no comenzada. |
| `ACTION_TOOLING` | Implementación de herramienta nueva aprobada y en progreso. |
| `ACTION_LOGIC_CANDIDATE` | Candidato a cambio de lógica operativa. Requiere revisión Opus antes de proceder. |
| `ACTION_SAFETY` | Problema de seguridad/integridad detectado. Bloqueo inmediato hasta resolver. |

**P&L Observability completa** se clasifica hoy como **ACTION_DESIGN / WATCH_RISK**:
- `ACTION_DESIGN` porque el contrato está documentado pero los componentes clave (Patch C, pnl_report.py) no están implementados.
- `WATCH_RISK` porque las métricas actuales son insuficientes para informar decisiones operativas sin riesgo de interpretación errónea.

---

## H. Lista negra operativa

Las siguientes métricas P&L **no pueden usarse** para ninguna de las acciones listadas hasta que sean promovidas canónicamente con Opus review y Pablo signoff:

| Métrica | Usos prohibidos |
|---|---|
| Cualquier cifra P&L actual (`trade_lifecycle`, `wallet_pnl`) | BANKROLL, Fase C, whitelist, sizing, city modes, scheduler, reglas de riesgo, BUY/SELL/SKIP, Telegram accionable |
| `wallet_pnl_7d` mientras `wallet_pnl_available=false` | Todos los usos operativos |
| `lifecycle_pnl_*` de `trade_lifecycle` | Todos los usos operativos; solo auditoría individual con disclaimer |
| Horizonte ALL pre-Patch C | Cualquier uso como base de cálculo canónico |
| Delta wallet sin attestation | Todos los usos operativos |

**Regla general:** si una métrica no tiene `canonical_source` confirmado, `quality≠contaminated` y `confidence≥medium`, no puede usarse para ninguna decisión que afecte el comportamiento del bot o el capital de Pablo.

---

## I. Roadmap B1–B6

| Paso | Artefacto | Estado | Descripción |
|---|---|---|---|
| **B1** | `docs/pnl_observability.md` | **COMPLETADO** (esta sesión) | Contrato de P&L Observability 1D/1W/1M/ALL documentado. |
| **B2** | `tools/wallet_cash_flow_log.py` (Patch C) | DISEÑADO / NO IMPLEMENTADO | CLI manual para registrar cash flows. Diseño en `docs/wallet_cash_flow_log_design.md`. Requiere signoff Pablo → diff Codex → review → merge. |
| **B3** | `tools/pnl_report.py` | PENDIENTE | Herramienta read-only que produce métricas 1D/1W/1M/ALL con etiquetas de confidence. Requiere Patch C operativo + diseño Opus separado. |
| **B4** | Integración Daily Digest | PENDIENTE | `daily_kanban_digest.py` incorpora métricas P&L de `pnl_report.py` como LOG_ONLY / WATCH_AUDIT. Requiere B3 completado. |
| **B5** | Criterios de promoción canónica | PENDIENTE | Definición formal de cuándo `wallet_pnl_7d` puede pasar de `provisional` a `canonical`. Requiere ≥28 snapshots, ≥28d attestations, y revisión Opus. |
| **B6** | Revisión Opus | OBLIGATORIO antes de cualquier uso operativo | Revisión Opus del sistema completo antes de usar cualquier métrica P&L para BANKROLL, sizing, whitelist, Fase C, Telegram accionable u otras decisiones operativas. |

**Orden de dependencias:** B1 → B2 → B3 → B4 → B5 → B6 → uso operativo.

**Nota sobre Patch C como prerequisite técnico:** Patch C (B2) es condición necesaria para que exista `t0 ALL` y para que `cash_flows.status` pueda progresar más allá de `missing`. Sin embargo, la implementación de Patch C no promueve automáticamente ninguna métrica. La promoción requiere cobertura suficiente de attestations más revisión Opus (B6).

---

## J. Guardrails transversales

Los siguientes riesgos sistémicos deben evitarse activamente en todas las etapas del roadmap:

### J.1 Falsa canonización temprana

**Riesgo:** declarar una métrica como canónica antes de tener cobertura suficiente, attestation completa o Opus review.

**Guardrail:** ninguna métrica P&L cambia `canonical_source` de `none` a cualquier valor sin un documento de promoción explícito aprobado por Opus + Pablo signoff. Un número que "parece correcto" no es suficiente.

### J.2 Backfill silencioso

**Riesgo:** añadir attestations retroactivas para cubrir períodos pasados sin evidencia real, inflando artificialmente la cobertura.

**Guardrail:** `actor` debe ser siempre `pablo_manual`. El CLI rechaza `actor` inferred, auto, reconstructed o estimated. Cualquier intento de backfill retroactivo como canónico requiere diseño Opus separado con señalización explícita en el documento de solicitud.

### J.3 Drift snapshot/cash_flow

**Riesgo:** desincronización entre la frecuencia de snapshots de wallet y la cobertura del cash_flow_log, creando ventanas temporales donde el ΔP&L no es confiable.

**Guardrail:** `wallet_snapshot.py` debe verificar que la cobertura de `wallet_cash_flows.jsonl` es continua para el horizonte evaluado. Si hay una brecha, el status debe ser `attested_partial` o `unreconciled`, nunca `attested_full_7d`.

### J.4 Confusión realized vs. wallet-adjusted

**Riesgo:** usar P&L realizado de `trade_lifecycle` y wallet ΔP&L como si fueran equivalentes o intercambiables.

**Guardrail:** las dos métricas son distintas por diseño. El Daily Digest siempre las etiqueta separadamente. Una nunca se usa como proxy de la otra. La divergencia entre las dos, si supera los umbrales del horizonte, es en sí misma una señal de alerta.

### J.5 Bankroll pequeño y umbrales absolutos

**Riesgo:** con bankroll de ~$25, diferencias de $1–$3 representan el 4–12% del capital. Los umbrales de divergencia definidos en este contrato (±$0.50/±$1.50/±$3.00) son significativos a esta escala.

**Guardrail:** los umbrales de divergencia son conservadores por diseño. No deben relajarse sin Opus review. Si el bankroll crece, los umbrales deben revisarse proporcionalmente.

### J.6 Ninguna cifra sin source/confidence/data quality

**Riesgo:** publicar una cifra P&L en el Daily Digest sin sus etiquetas, llevando a Pablo a interpretar como confiable algo que no lo es.

**Guardrail:** cualquier bloque P&L en el Digest que no incluya `source`, `quality` y `confidence` debe ser rechazado por `verify_before_deploy.py`. Si las etiquetas no están disponibles, el bloque no se publica (`would_send=false` o la sección queda como `N/A — datos no disponibles todavía`).
