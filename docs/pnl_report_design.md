# pnl_report.py — Contrato de Diseño B3

**Status:** ACTION_DESIGN / WATCH_RISK / NOT_CANONICAL  
**Date:** 2026-05-07  
**Session:** B3 (Sonnet 4.6)  
**Prerequisite:** Patch C (`tools/wallet_cash_flow_log.py`) — implementado y desplegado. `data/wallet_cash_flows.jsonl` — no existe todavía.  
**Clasificación Opus:** ACTION_DESIGN / WATCH_RISK / NOT_CANONICAL  
**Contrato superior:** `docs/pnl_observability.md`

---

## 1. Propósito

`tools/pnl_report.py` es una herramienta CLI **read-only / LOG_ONLY** que produce métricas de P&L para los horizontes 1D / 1W / 1M / ALL.

### Lo que hace

- Lee `data/wallet_portfolio_snapshots.jsonl` y `data/wallet_cash_flows.jsonl`.
- Cruza ambas fuentes para calcular wallet ΔP&L ajustado por cash flows por horizonte.
- Usa `trade_lifecycle.json` únicamente como `non_canonical_telemetry` de cross-check.
- Emite un JSON estructurado con etiquetas obligatorias `source`, `quality`, `confidence` en cada horizonte.
- Sale con exit code 0 cuando los datos están ausentes o insuficientes, reportando el estado con `reason` explícito.

### Lo que NO hace

- **No escribe datos del bot** — no modifica ningún archivo de estado del sistema.
- **No lee APIs en vivo** — solo archivos locales.
- **No envía Telegram** — ni en modo dry-run ni en producción.
- **No emite BUY / SELL / SKIP** — ninguna señal operativa.
- **No toca BANKROLL / Fase C** — no promueve ni evalúa readiness operativa.
- **No promueve `canonical_source`** — el máximo estado alcanzable por esta herramienta en B3 es `canonical_candidate`.
- **No implementa Patch D** — no modifica `wallet_snapshot.py` ni `daily_kanban_digest.py`.
- **No conecta a Railway** — herramienta local únicamente.
- **No usa DB SQLite** — solo JSONL planos.
- **No tiene scheduler / cron** — ejecución manual exclusivamente.
- **No usa `bot.py`** — sin imports del runtime del bot.
- **No modifica env vars** — no requiere variables de entorno del bot.

---

## 2. Inputs

| Input | Path | Rol | Estado actual |
|---|---|---|---|
| Wallet snapshots | `data/wallet_portfolio_snapshots.jsonl` | Fuente primaria para ΔP&L | `accumulating` |
| Cash flows | `data/wallet_cash_flows.jsonl` | Ajuste por depósitos/retiros | `missing` |
| Trade lifecycle | `trade_lifecycle.json` | Cross-check `non_canonical_telemetry` | `contaminated` |
| Tiempo UTC | `datetime.now(timezone.utc)` | Ancla temporal para ventanas | Siempre disponible |

### Reglas de lectura

- `wallet_portfolio_snapshots.jsonl`: JSONL append-only, una snapshot por línea. Si el archivo no existe → horizonte `unavailable`.
- `wallet_cash_flows.jsonl`: JSONL append-only. Si el archivo no existe → `cash_flows.status=missing`, horizontes `blocked` con `reason` explícito. **No es error fatal; exit 0.**
- `trade_lifecycle.json`: JSON único. Si no existe → omitir cross-check; `non_canonical_telemetry.status=missing`. No afecta horizontes primarios.

---

## 3. Schema JSON de salida

```json
{
  "schema_version": "1.0",
  "generated_at": "<ISO-8601 UTC>",
  "canonical_source": "none",
  "bankroll_readiness": "blocked",
  "inputs": {
    "snapshots": {
      "path": "data/wallet_portfolio_snapshots.jsonl",
      "status": "present | missing",
      "n_records": 0
    },
    "cash_flows": {
      "path": "data/wallet_cash_flows.jsonl",
      "status": "present | missing",
      "n_records": 0,
      "coverage_days": 0
    },
    "trade_lifecycle": {
      "path": "trade_lifecycle.json",
      "status": "present | missing | contaminated",
      "contamination_rate": null
    }
  },
  "horizons": {
    "1D": {
      "status": "unavailable | blocked | provisional | canonical_candidate",  // canonical no emitible en B3
      "value_usdc": null,
      "source": "wallet_snapshot+cash_flow_log | trade_lifecycle | none",
      "quality": "missing | contaminated | accumulating | attested_partial | attested_full_7d | unreconciled",
      "confidence": "untrusted | low | medium",
      "coverage_gap": true,
      "window": {
        "start": null,
        "end": null,
        "hours": null
      },
      "n_snapshots": 0,
      "snapshots_used": [],
      "cash_flow_adjustment_usdc": null,
      "lifecycle_cross_check_usdc": null,
      "divergence_threshold_usdc": 0.50,
      "divergence_actual_usdc": null,
      "reason": "<descripción explícita del estado>",
      "promotion_blocked_by": ["cash_flows.status=missing"]
    },
    "1W": {
      "status": "...",
      "value_usdc": null,
      "source": "...",
      "quality": "...",
      "confidence": "...",
      "coverage_gap": true,
      "window": {
        "start": null,
        "end": null,
        "hours": null
      },
      "n_snapshots": 0,
      "snapshots_used": [],
      "cash_flow_adjustment_usdc": null,
      "lifecycle_cross_check_usdc": null,
      "divergence_threshold_usdc": 1.50,
      "divergence_actual_usdc": null,
      "reason": "...",
      "promotion_blocked_by": []
    },
    "1M": {
      "status": "...",
      "value_usdc": null,
      "source": "...",
      "quality": "...",
      "confidence": "...",
      "coverage_gap": true,
      "window": {
        "start": null,
        "end": null,
        "hours": null
      },
      "n_snapshots": 0,
      "snapshots_used": [],
      "cash_flow_adjustment_usdc": null,
      "lifecycle_cross_check_usdc": null,
      "divergence_threshold_usdc": 3.00,
      "divergence_actual_usdc": null,
      "reason": "...",
      "promotion_blocked_by": []
    },
    "ALL": {
      "status": "...",
      "value_usdc": null,
      "source": "...",
      "quality": "...",
      "confidence": "...",
      "coverage_gap": true,
      "window": {
        "start": null,
        "end": null,
        "hours": null
      },
      "n_snapshots": 0,
      "snapshots_used": [],
      "cash_flow_adjustment_usdc": null,
      "lifecycle_cross_check_usdc": null,
      "divergence_threshold_usdc": null,
      "divergence_actual_usdc": null,
      "reason": "...",
      "promotion_blocked_by": []
    }
  },
  "non_canonical_telemetry": {
    "trade_lifecycle": {
      "status": "missing | contaminated | partial",
      "contamination_rate": null,
      "realized_pnl_usdc": null,
      "n_closed_trades": 0,
      "disclaimer": "non_canonical_telemetry — no usar para BANKROLL, Telegram real, o decisiones operativas."
    }
  },
  "guardrails": {
    "max_confidence_b3": "medium",
    "canonical_requires": "B5_B6_opus_review_pablo_signoff",
    "tool_scope": "read_only_log_only",
    "no_operational_use": true
  }
}
```

### Notas de schema

- `schema_version` es string fijo `"1.0"` en B3. Cambios requieren nueva sesión de diseño.
- `canonical_source` siempre `"none"` en la salida de B3; nunca lo modifica la herramienta.
- `bankroll_readiness` siempre `"blocked"` en la salida de B3; nunca lo modifica la herramienta.
- `value_usdc` es `null` cuando el horizonte no puede calcularse. Nunca `0` a menos que el ΔP&L real sea cero con datos válidos.
- `snapshots_used` lista solo los IDs/timestamps de las snapshots efectivamente usadas para el cálculo, no todas las disponibles.
- `divergence_threshold_usdc` sigue los umbrales de `docs/pnl_observability.md` sección C.

---

## 4. Máquina de estados por horizonte

Cada horizonte transita independientemente. Hay **5 estados documentados**; solo **4 son emitibles automáticamente en B3** (`unavailable`, `blocked`, `provisional`, `canonical_candidate`). El quinto estado (`canonical`) está documentado como estado futuro pero **no puede ser emitido por esta herramienta en B3** — requiere B5 + B6.

### `unavailable`

Sin datos suficientes para iniciar el cálculo. No es error.

**Condiciones de entrada:**
- `wallet_portfolio_snapshots.jsonl` no existe.
- 0 snapshots en el período del horizonte.
- `t0 ALL` no definido (primera entrada válida de `cash_flow_log`).

**Salida:** `value_usdc=null`, `reason` explícito.

### `blocked`

Datos presentes pero falta un prerequisite estructural para el cálculo.

**Condiciones de entrada:**
- `cash_flows.status=missing` (archivo no existe).
- Cobertura de attestation insuficiente para el horizonte.
- Depósito `possible_deposit` no reconciliado en el período.
- 1 sola snapshot (imposible calcular delta).

**Salida:** `value_usdc=null`, `promotion_blocked_by` lista los bloqueadores explícitos.

### `provisional`

Cálculo posible con datos parciales. Confianza baja.

**Condiciones de entrada:**
- `cash_flows.status=attested_partial` y cobertura mínima del horizonte cubierta.
- No hay gaps invalidantes según tabla de `docs/pnl_observability.md` sección C.

**Confidence máximo:** `low`.

**Salida:** `value_usdc` presente pero con advertencia explícita en `reason`.

### `canonical_candidate`

Cálculo con attestation completa para el horizonte. Confidence máximo `medium`.

**Condiciones de entrada:**
- `cash_flows.status=attested_full_7d` y cobertura ≥ mínimo del horizonte.
- Sin gaps invalidantes.
- Sin depósitos `possible_deposit` sin reconciliar.
- `n_snapshots` ≥ mínimo del horizonte.

**Confidence máximo en B3:** `medium`. Nunca `high` automático.

**Promoción a `canonical`:** bloqueada en B3. Requiere B5 + B6 (Opus review + Pablo signoff explícito).

### `canonical` (BLOQUEADO EN B3)

**La herramienta `tools/pnl_report.py` no puede emitir `status=canonical` por sí sola en B3.**

Canonical requiere:
- B5: criterios de promoción formales documentados.
- B6: Opus review del sistema completo.
- Pablo signoff explícito con documento de promoción.

Si por bug o error la herramienta emitiera `canonical`, debe considerarse un defecto crítico de implementación.

---

## 5. Confidence y data quality

### Niveles de confidence

| Nivel | Descripción | Condiciones |
|---|---|---|
| `untrusted` | Dato no verificado. Solo para auditoría interna. | Sin attestation, `trade_lifecycle` contaminated |
| `low` | Attestation parcial o incompleta para el horizonte. | `attested_partial`, cobertura mínima pero con gaps menores |
| `medium` | Attestation completa para el horizonte, sin gaps invalidantes, divergencia dentro de umbral. | `attested_full_7d` para 1D/1W; ≥28d para 1M; cobertura íntegra para ALL |
| `high` | **Nunca automático en B3.** Solo post-Opus review. | Requiere B6 |

### Regla dura: confidence capado a `medium` en B3

La herramienta **nunca puede emitir `confidence=high`** sin revisión Opus explícita. Si la implementación generara `high`, es un bug.

### Tabla de quality → confidence máximo

| quality | confidence máximo |
|---|---|
| `missing` | `untrusted` |
| `contaminated` | `untrusted` |
| `accumulating` | `untrusted` |
| `attested_partial` | `low` |
| `attested_full_7d` | `medium` |
| `unreconciled` | `untrusted` |

---

## 6. Ausencia de `wallet_cash_flows.jsonl`

La ausencia del archivo cash flow **no es un error fatal**.

### Comportamiento

- Exit code: **0**
- `inputs.cash_flows.status = "missing"`
- `inputs.cash_flows.n_records = 0`
- `inputs.cash_flows.coverage_days = 0`
- Todos los horizontes: `status = "blocked"`, `value_usdc = null`
- `reason` explícito en cada horizonte: `"cash_flow_log missing — no es posible ajustar ΔP&L por cash flows"`
- `promotion_blocked_by`: `["cash_flows.status=missing"]`
- `non_canonical_telemetry.trade_lifecycle` se reporta igual (si existe)
- `guardrails` se incluye con valores normales

### Lo que NO ocurre

- No se lanza excepción Python no capturada.
- No se imprime stack trace al usuario.
- No se emite un valor `value_usdc` estimado o aproximado.
- No se usa `trade_lifecycle` como sustituto del cash flow log.

---

## 7. Ausencia de historia suficiente

### 0 snapshots

- Horizonte: `unavailable`
- `reason`: `"no wallet snapshots found for this horizon"`
- `n_snapshots: 0`, `value_usdc: null`

### 1 snapshot

- Horizonte: `blocked`
- `reason`: `"single snapshot — delta requires at least 2 snapshots"`
- `n_snapshots: 1`, `value_usdc: null`

### Ventana parcial (menos snapshots que el mínimo del horizonte)

- Horizonte: `provisional` si hay attestation, `blocked` si no hay cash flow log.
- `coverage_gap: true`
- `reason`: describe la cobertura real vs. la requerida.

### t0 ALL ausente

- Horizonte ALL: `unavailable`
- `reason`: `"t0 not defined — no valid cash_flow_log entry with type=no_cash_flow_attestation or type=deposit found"`
- t0 ALL = primera entrada válida del cash flow log con `--write --init` (Patch C).

### `attested_partial` insuficiente

- Si la attestation parcial no cubre el mínimo del horizonte (ej. solo 3 días para 1W):
  - `status: blocked`
  - `reason`: `"attested_partial coverage (3d) below minimum required for 1W (5d)"`

---

## 8. Daily Digest futuro (B4)

### Qué puede mostrarse (LOG_ONLY / WATCH_AUDIT)

Cuando B3 esté implementado y B4 integre `pnl_report.py` en el Digest:

- Estado de cada horizonte (`status`, `quality`, `confidence`), sin valor numérico si confidence < `medium`.
- `cash_flows.status` y `coverage_days`.
- `promotion_blocked_by` como lista de bloqueadores.
- `non_canonical_telemetry` con disclaimer explícito.

### Qué NO debe mostrarse

- `value_usdc` de ningún horizonte mientras `canonical_source=none`.
- Cifras de `trade_lifecycle` sin disclaimer `non_canonical_telemetry`.
- `confidence=high` (bloqueado en B3).
- Cualquier métrica que pueda interpretarse como señal operativa.

### Regla de `would_send`

- `would_send=false` mientras `canonical_source=none`, sin excepción.
- `trade_lifecycle` siempre etiquetado `non_canonical_telemetry` en el Digest.
- No mostrar `value_usdc` numérico hasta B5 + B6.

---

## 9. Tests mínimos T1–T14

Los siguientes tests deben existir antes de considerar la implementación de `tools/pnl_report.py` como completa. Todos en `tests/test_pnl_report.py`.

| ID | Nombre | Descripción |
|---|---|---|
| **T1** | `test_missing_cash_flow_log` | Sin `wallet_cash_flows.jsonl`: exit 0, todos los horizontes `blocked`, `value_usdc=null`, `reason` explícito en cada uno. |
| **T2** | `test_zero_snapshots` | `wallet_portfolio_snapshots.jsonl` vacío: todos los horizontes `unavailable`, exit 0. |
| **T3** | `test_single_snapshot` | Solo 1 snapshot en JSONL: horizonte correspondiente `blocked` con reason `single snapshot`. |
| **T4** | `test_7d_attestation_provisional` | `cash_flows.status=attested_partial` con 5d cobertura: 1W → `provisional`, confidence=`low`. |
| **T5** | `test_28d_attestation_canonical_candidate` | `attested_full_7d` + ≥28 snapshots: 1M → `canonical_candidate`, confidence=`medium`. |
| **T6** | `test_gap_invalidates_horizon` | Gap de >2h sin snapshot en ventana 1D: `coverage_gap=true`, status → `blocked`. |
| **T7** | `test_deposit_unreconciled_blocks` | Entrada `possible_deposit` sin reconciliar en el período: horizonte → `blocked`, `promotion_blocked_by` contiene `possible_deposit_unreconciled`. |
| **T8** | `test_lifecycle_always_non_canonical` | Siempre que `trade_lifecycle.json` existe: `non_canonical_telemetry.trade_lifecycle` presente con `disclaimer` explícito. Nunca eleva confidence del horizonte. |
| **T9** | `test_divergence_alert` | ΔP&L wallet vs lifecycle cross-check supera umbral del horizonte: `divergence_actual_usdc` > `divergence_threshold_usdc`, horizonte queda en `provisional` máximo. |
| **T10** | `test_opus_attested_no_promotion` | Aunque todos los datos estén perfectos y `attested_full_7d`: `status` queda en `canonical_candidate`, nunca `canonical`. Confidence nunca `high`. |
| **T11** | `test_jsonl_corrupted` | Línea JSONL inválida en snapshots o cash flows: exit 2, mensaje de error claro, no crash silencioso. |
| **T12** | `test_determinism` | Mismos inputs → mismo output JSON en dos ejecuciones consecutivas. Sin efectos de tiempo no controlados. |
| **T13** | `test_read_only_chmod` | Directorio `data/` con chmod -w (read-only): herramienta funciona sin error (no escribe). |
| **T14** | `test_write_report_no_init_dir` | Flag futuro `--write-report` sin directorio de destino existente: falla limpia con mensaje, exit distinto de 0, sin crash. |

### Fixtures sintéticos

- Todos los tests usan fixtures sintéticos en `tmp_path` (pytest).
- **Ningún test debe leer datos reales** de `data/` sin fixture explícito.
- Los fixtures deben cubrir los casos de borde documentados en secciones 6 y 7.
- Si algún test requiere datos reales de `wallet_cash_flows.jsonl`, requiere decisión explícita de Pablo antes de implementar.

### Hook determinista de testing

- `--generated-at` existe solo como testing hook para fixtures deterministas.
- Acepta ISO-8601 UTC.
- No cambia source data, status, confidence, `canonical_source`, `bankroll_readiness` ni `operational_use`.
- No permite emitir `canonical` ni simular promocion canonica.
- No debe usarse para simular rendimiento real.

---

## 10. Imports permitidos

`tools/pnl_report.py` usa **solo stdlib Python**. No instala dependencias externas.

Lista propuesta:

```python
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
```

`dataclasses` es opcional según el diseño de implementación. Si el código puede ser igualmente claro sin él, se omite.

**Prohibido en B3:**

- `requests`, `httpx`, `aiohttp` — sin llamadas HTTP.
- `sqlite3` — sin DB.
- `bot`, `scheduler`, cualquier módulo del runtime del bot.
- Cualquier paquete de terceros no stdlib.

---

## 11. Exit codes

| Código | Condición |
|---|---|
| **0** | Reporte generado correctamente, aunque métricas estén `unavailable` o `blocked`. Incluye el caso de cash flow log ausente. |
| **2** | Input corrupto: JSONL inválido (línea no parseable), inconsistencia estructural (campo requerido ausente en snapshot), o error de integridad detectado. |

Otros exit codes solo si están justificados por un caso específico documentado en una futura revisión de este diseño.

**Exit 1 (error genérico Python)** no debe ocurrir en condiciones normales. Toda excepción debe capturarse y convertirse en exit 2 con mensaje claro.

---

## 12. Lo que la herramienta NO hace

Lista negra explícita. Si alguna funcionalidad de las siguientes aparece en el código de `tools/pnl_report.py`, es un defecto de implementación:

- **Trading**: ninguna señal BUY/SELL/SKIP.
- **Telegram**: ningún envío, ni en modo dry-run.
- **DB**: ningún acceso a SQLite.
- **Railway**: ninguna conexión remota.
- **Env vars del bot**: no lee `BANKROLL`, `ACTIVE_TRADING_CITIES`, `MIN_EDGE`, ni variables operativas.
- **`bot.py`**: no importa ni llama ningún símbolo de `bot.py`.
- **Scheduler**: no registra tareas, no configura cron.
- **BANKROLL**: no evalúa, no modifica, no reporta readiness de BANKROLL.
- **Fase C**: no evalúa, no desbloquea, no referencia Fase C como decisión.
- **Promueve readiness**: no cambia `canonical_source` de `none` a ningún valor.
- **Promueve canonical_source**: no escribe en ningún archivo de estado del bot.
- **Patch D**: no modifica `wallet_snapshot.py`, `daily_kanban_digest.py` ni ningún componente existente.
- **Escritura de datos del bot**: no modifica `wallet_portfolio_snapshots.jsonl`, `wallet_cash_flows.jsonl`, `trade_lifecycle.json` ni ningún archivo de `data/`.
- **Escritura de estado operativo**: no crea archivos de estado nuevos salvo un eventual `--write-report` a un directorio de reportes separado, explícitamente fuera de `data/`.

---

## 13. Criterios de aceptación para Codex

El diseño B3 está listo para implementación cuando se cumplan **todos** los siguientes criterios:

### Criterios de implementación

- [ ] Este documento (`docs/pnl_report_design.md`) está completo y revisado.
- [ ] Tests T1–T14 están definidos en este documento y son implementables sin ambigüedad.
- [ ] No hay implementación prematura — ningún código de `tools/pnl_report.py` existe antes del signoff.
- [ ] Fixtures sintéticos diseñados o aprobados (no datos reales por accidente).

### Criterios de validación post-implementación

- [ ] `python -m pytest tests/test_pnl_report.py -q` — todos los tests pasan.
- [ ] `python verify_before_deploy.py` — número total de checks OK sin regresión.
- [ ] `git diff --check` — sin errores de whitespace.
- [ ] `python tools/pnl_report.py --help` — funciona sin error.
- [ ] Ejecución con `data/wallet_cash_flows.jsonl` ausente → exit 0, JSON válido, todos los horizontes `blocked`.
- [ ] Herramienta no importa `bot.py` ni módulos del runtime (verificable con `grep -r "import bot" tools/pnl_report.py`).
- [ ] No escribe a `data/` (verificable con strace o revisión de código).

### Criterios de signoff

- [ ] Pablo revisa el diff antes de merge.
- [ ] No push a Railway hasta signoff explícito de Pablo.
- [ ] Opus review de B3 antes de cualquier uso operativo de las métricas.

---

## 14. Dependencias del roadmap

```
B1  docs/pnl_observability.md          COMPLETADO
B2  tools/wallet_cash_flow_log.py      COMPLETADO (Patch C, sesiones 306–310)
B3  tools/pnl_report.py                ESTE DOCUMENTO — diseño completado, implementación pendiente signoff
B4  Integración Daily Digest            PENDIENTE — requiere B3 completo
B5  Criterios de promoción canónica     PENDIENTE — requiere B4 + datos reales
B6  Revisión Opus completa             OBLIGATORIO antes de cualquier uso operativo
```

**B3 no desbloquea B4 automáticamente.** La integración en Daily Digest requiere decisión explícita separada.

---

## 15. Guardrails transversales

Estos guardrails son adicionales a los de `docs/pnl_observability.md` sección J, específicos para la implementación de B3:

### G1: Confidence capado

Ninguna ruta de código en `pnl_report.py` puede producir `confidence=high` sin flag explícito `--opus-attested` y validación manual. Incluso con ese flag, `confidence=high` requiere revisión del resultado antes de su uso.

### G2: No datos reales en tests

Todos los fixtures de tests son sintéticos o copias controladas. Ningún test lee `data/wallet_cash_flows.jsonl` real, `data/wallet_portfolio_snapshots.jsonl` real, ni `trade_lifecycle.json` real sin fixture explícito.

### G3: Exit 0 en ausencia de datos

La herramienta nunca falla con exit distinto de 0 por datos ausentes o insuficientes. Solo falla (exit 2) ante corrupción de inputs.

### G4: `value_usdc` nunca estimado

Si no hay datos suficientes para calcular el ΔP&L con precisión, `value_usdc=null`. Nunca se aproxima, interpola, ni extrapola un valor.

### G5: No backfill

La herramienta no intenta reconstruir períodos sin snapshots. Los gaps se reportan como gaps, no como ceros ni como continuidades interpoladas.

### G6: `promotion_blocked_by` siempre lista

El campo `promotion_blocked_by` siempre es una lista (puede estar vacía). Nunca `null`. Para horizontes `blocked` o `unavailable`, debe contener al menos un elemento explicativo.
