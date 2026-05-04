# Truth Pipeline — Diseño Fase 1

**Estado:** DISEÑO CERRADO — Implementación NO iniciada  
**Clasificación Opus:** ACTION_DESIGN  
**Fecha de diseño:** 2026-05-04  
**Autor del diseño:** Opus  
**Documentado por:** Sonnet (Sesión 290)

---

## 1. Objetivo de Fase 1

Construir una capa de observabilidad pasiva que cruce el forecast del bot con los resultados reales de Polymarket, sin tocar el trading core ni generar señales ejecutables.

El propósito concreto es:
- Medir qué tan bien calibrado está el forecast del bot vs. la resolución real del mercado.
- Detectar degradación sistemática de señales antes de que se vea en el P/L.
- Producir datos de entrada para decisiones futuras de política (bankroll scaling, city whitelist, SL retrospective).

Fase 1 es **solo observación**. No actúa, no vende, no compra, no salta nada.

---

## 2. Qué incluye Fase 1

### 2.1 Schema SQLite (subfase 1A.1)

Dos tablas nuevas en `polymarket.db`, aditivas sobre el schema v1:

**`truth_records`** — una fila por mercado+ciudad resuelto:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | — |
| `city` | TEXT NOT NULL | ciudad |
| `date_iso` | TEXT NOT NULL | fecha del mercado |
| `condition` | TEXT | `exact`, `range`, etc. |
| `threshold_c` | REAL | umbral de temperatura |
| `question` | TEXT | texto del mercado |
| `market_id` | TEXT | ID Polymarket |
| `token_id_yes` | TEXT | token YES |
| `token_id_no` | TEXT | token NO |
| `forecast_high_c` | REAL | forecast del bot al momento del snapshot |
| `forecast_source` | TEXT | `open_meteo`, `noaa`, etc. |
| `observed_high_c` | REAL | temperatura real observada (puede ser NULL) |
| `observed_source` | TEXT | fuente de observación |
| `resolution_outcome` | TEXT | `YES`, `NO`, `VOID`, `UNKNOWN` |
| `resolution_ts_utc` | TEXT | timestamp de resolución Polymarket |
| `resolution_method` | TEXT | cómo se determinó la resolución |
| `bot_had_position` | INTEGER | 1 si el bot tenía posición, 0 si no |
| `bot_side` | TEXT | `YES` o `NO` si tenía posición |
| `snapshot_ts_utc` | TEXT NOT NULL | cuándo se grabó esta fila |
| `payload_json` | TEXT NOT NULL | payload completo para replay |

**`truth_revisions`** — log de correcciones:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | — |
| `truth_record_id` | INTEGER FK | FK a `truth_records.id` |
| `field_changed` | TEXT NOT NULL | campo corregido |
| `old_value` | TEXT | valor anterior |
| `new_value` | TEXT | valor nuevo |
| `revision_ts_utc` | TEXT NOT NULL | timestamp de la corrección |
| `reason` | TEXT | por qué se corrigió |

Índices mínimos:
```sql
CREATE INDEX IF NOT EXISTS idx_truth_city ON truth_records (city, date_iso);
CREATE INDEX IF NOT EXISTS idx_truth_outcome ON truth_records (resolution_outcome);
CREATE INDEX IF NOT EXISTS idx_truth_revisions_rec ON truth_revisions (truth_record_id);
```

### 2.2 Fetcher de resoluciones (subfase 1A.2)

Script standalone `tools/truth_pipeline_fetcher.py`:
- Lee `polymarket.db` en modo read-only URI.
- Consulta Polymarket Data API para mercados resueltos relevantes.
- NO importa `bot.py`.
- NO escribe en tablas de trading ni en runtime del bot.
- Produce un JSON intermedio `data/truth_pipeline_fetch.json` con los registros crudos.
- Logea cada run en `data/truth_pipeline_fetch_runs.jsonl`.
- Activado por `TRUTH_PIPELINE_ENABLED=1` (default 0).

### 2.3 Runner / writer (subfase 1A.3)

Script standalone `tools/truth_pipeline_runner.py`:
- Lee `data/truth_pipeline_fetch.json`.
- Cruza con `market_snapshots` y `forecast_snapshots` en `polymarket.db`.
- Escribe en `truth_records` y `truth_revisions` (WAL, transaccional).
- NO importa `bot.py`.
- NO toca `cycle_events`, `market_snapshots`, `forecast_snapshots` (read-only sobre ellas).
- Idempotente: no duplica filas ya existentes.

### 2.4 Alertas Telegram (subfase 1A.4)

Script standalone `tools/truth_pipeline_alert.py`:
- Lee `truth_records` en modo read-only.
- Calcula: n_resolved, calibración por ciudad (forecast_ok/total), drift acumulado, cobertura.
- Envía resumen a `TRUTH_PIPELINE_TG_CHAT_ID` (canal separado del operativo).
- Activado por `TRUTH_PIPELINE_TELEGRAM_ENABLED=1` (default 0).
- Telegram es salud/auditoría únicamente — no señal operativa.
- **Nunca recomienda BUY/SELL/SKIP** en su salida.

### 2.5 Job separado

Los cuatro scripts de Fase 1 se ejecutan como job standalone en Railway (servicio separado o cron separado), **nunca como import desde `bot.py`**. El bot no depende del Truth Pipeline; el Truth Pipeline depende del volumen de datos del bot (read-only sobre `polymarket.db`).

---

## 3. Qué NO incluye Fase 1

- **No toca `bot.py`** bajo ninguna circunstancia.
- **No toca trading core**: execute_trade, manage_positions, intra_cycle_sl_check, cooldown, sizing, MIN_EDGE, sigma.
- **No toca BANKROLL ni sizing.**
- **No toca whitelist, CANARY_TRADING_CITIES, ACTIVE_TRADING_CITIES, BLOCKED_CITIES.**
- **No toca city modes ni scheduler.**
- **No toca reglas de entrada/salida ni reglas de riesgo.**
- **No toca env vars productivas** (solo añade las propias del Truth Pipeline, todas default OFF).
- **No activa Fase C** de blocked_signals (cruce truth pipeline con señales bloqueadas).
- **No crea señales ejecutables** de ningún tipo.
- **No autoriza subida de BANKROLL** ($25 → $35 ni ningún otro nivel).
- **No hace backtesting.**
- **No implementa probability engines.**
- **No activa bankroll scaling automático.**
- **No es fuente autoritativa** de ninguna decisión operativa en esta fase.
- **El canal Telegram del Truth Pipeline es separado** del canal operativo; no reemplaza ni duplica las alertas operativas.

---

## 4. Artefactos propuestos

| Artefacto | Ruta | Tipo |
|-----------|------|------|
| Schema SQL v2 | `sql/002_truth_pipeline.sql` | Migración aditiva |
| Fetcher | `tools/truth_pipeline_fetcher.py` | Script standalone |
| Runner/writer | `tools/truth_pipeline_runner.py` | Script standalone |
| Alerta Telegram | `tools/truth_pipeline_alert.py` | Script standalone |
| Estado de runs | `data/truth_pipeline_fetch_runs.jsonl` | Runtime (gitignored) |
| Fetch intermedio | `data/truth_pipeline_fetch.json` | Runtime (gitignored) |
| Audit log | `data/truth_pipeline_audit.json` | Runtime (gitignored) |

Todos los artefactos de runtime van en `.gitignore`. Los scripts y el SQL van en el repo.

---

## 5. Integración con sistemas existentes

### 5.1 P/L Reconciliation

Truth Pipeline provee `forecast_ok_rate` por ciudad, que enriquece el contexto de `tools/pnl_reconciliation_alert.py` en sesiones futuras. En Fase 1 no hay integración automática: el enriquecimiento es manual.

### 5.2 Blocked Signals v2

Fase 1 no activa Fase C (el cruce truth pipeline × blocked_signals). Los campos `settlement_fidelity_status`, `bot_would_have_bought`, `bot_evaluation_source` que están null/unknown en schema v2 pueden llenarse en Fase 2, una vez que `truth_records` tenga muestra suficiente.

### 5.3 SL Retrospective

`truth_records.bot_had_position` + `truth_records.resolution_outcome` permiten construir una cohorte de posiciones con ground truth. En Fase 1 se acumulan los datos; el análisis phase-aware de `tools/sl_retrospective.py` puede leerlos en Fase 2 para métricas de SL sobre resolución real vs SL trigger.

### 5.4 Low-exact-gap risk

`truth_records.condition` + calibración permite cuantificar el riesgo de señales `exact` con gaps de temperatura cercanos al umbral. En Fase 1 se acumulan los registros; análisis en Fase 2.

### 5.5 City Intelligence

`truth_records` es la fuente futura para `settlement_fidelity_probe` con datos reales (vs proxy Open-Meteo). En Fase 1, el probe sigue usando Open-Meteo; en Fase 2, puede leer `truth_records` directamente.

### 5.6 Bankroll Scaling Policy

`tools/bankroll_scaling_check.py` ya tiene el placeholder `truth_pipeline_status_unknown` como evidencia faltante. Cuando Fase 1 tenga ≥30 registros resueltos, provee la evidencia `truth_pipeline_calibration` que desbloquea la revisión manual. **No autoriza escalado automático.**

---

## 6. Guardrails de implementación

1. **`TRUTH_PIPELINE_ENABLED=0`** por defecto. Activación requiere aprobación explícita.
2. **`TRUTH_PIPELINE_TELEGRAM_ENABLED=0`** por defecto.
3. **`TRUTH_PIPELINE_TG_CHAT_ID`** debe ser un chat separado del canal operativo (`TELEGRAM_CHAT_ID`).
4. Los scripts no importan `bot.py` ni ningún módulo del trading core.
5. Toda lectura de `polymarket.db` usa URI `?mode=ro` (read-only).
6. Toda escritura en `truth_records`/`truth_revisions` es WAL + transaccional.
7. `verify_before_deploy.py` debe cubrir: defaults OFF, no import bot.py, no trading core, URI read-only sobre tablas Fase 0, idempotencia.
8. Antes de deploy, `python verify_before_deploy.py` debe pasar en verde.
9. No deploy hasta que el diseño de 1A.1 esté aprobado explícitamente por el usuario.

---

## 7. Diseño de alertas Telegram (1A.4)

El mensaje de Telegram del Truth Pipeline tiene esta estructura:

```
📊 Truth Pipeline — Resumen diario
Fecha: 2026-MM-DD UTC

Resueltos total: N
Con forecast: M (K%)
Calibración global: X% (forecast_ok / resueltos_con_forecast)

Por ciudad:
  Paris        n=5  calibración=60%
  Seoul        n=3  calibración=100%
  ...

Cobertura: [ciudad_sin_datos si corresponde]

Estado: OK | WATCH | ACTION_AUDIT
[WATCH si calibración < 50% con n>=10]
[ACTION_AUDIT si drift sistemático en ciudad >= 3 consecutivos]

Nota: Observabilidad pura. No accionable para trading.
```

Niveles:
- `OK`: calibración global ≥50% o muestra insuficiente (n<10).
- `WATCH`: calibración global <50% con n>=10, o una ciudad con degradación reciente.
- `ACTION_AUDIT`: drift sistemático ≥3 consecutivos en misma ciudad/condición. Requiere revisión Opus; no implica acción de trading.

---

## 8. Subfases

### 1A.1 — Schema + tests de aislamiento

- Crear `sql/002_truth_pipeline.sql` con `truth_records` y `truth_revisions`.
- Tests de aislamiento: verificar que la migración no rompe tablas Fase 0.
- Tests de idempotencia del schema (doble aplicación segura).
- `verify_before_deploy.py` verde.
- **Sin fetcher, sin runner, sin Telegram, sin bot.py, sin trading core.**

### 1A.2 — Fetcher

- `tools/truth_pipeline_fetcher.py` standalone.
- Lee `polymarket.db` URI read-only.
- Consulta Polymarket Data API para mercados resueltos.
- Produce `data/truth_pipeline_fetch.json`.
- Tests: dry-run sin DB real, manejo de API unavailable.
- `verify_before_deploy.py` verde.
- **Sin runner, sin Telegram.**

### 1A.3 — Runner / writer

- `tools/truth_pipeline_runner.py` standalone.
- Cruza fetch con snapshots, escribe `truth_records`.
- Idempotente por `(city, date_iso, condition, threshold_c)`.
- Tests: fixture con registros duplicados, manejo de snapshots ausentes.
- `verify_before_deploy.py` verde.
- **Sin Telegram.**

### 1A.4 — Alerta Telegram

- `tools/truth_pipeline_alert.py` standalone.
- Lee `truth_records` URI read-only.
- Envía a `TRUTH_PIPELINE_TG_CHAT_ID`.
- Anti-spam: máximo 1 alerta por día.
- Tests: fixture sin registros, fixture con ACTION_AUDIT.
- `verify_before_deploy.py` verde.

---

## 9. Criterios de aceptación de Fase 1

Una subfase está aceptada cuando:
1. Script corre en local sin errores con `--dry-run` o fixture local.
2. `python tools/check_python_syntax.py <script>` OK.
3. `python verify_before_deploy.py` pasa en verde (sin regresión).
4. `git diff --check` OK.
5. No hay imports de `bot.py` ni de trading core.
6. No hay efectos sobre `BANKROLL`, `execute_trade`, `manage_positions`.
7. `TRUTH_PIPELINE_ENABLED` y `TRUTH_PIPELINE_TELEGRAM_ENABLED` siguen `=0` en Railway hasta activación explícita.

---

## 10. Criterios de promoción a Fase 2

Fase 2 (cruce truth pipeline × blocked_signals, settlement_fidelity_status real, probability engines) se puede iniciar cuando:

1. `truth_records` acumula **≥30 registros** con `resolution_outcome != UNKNOWN`.
2. La calibración global es **evaluable** (no hay error sistemático en el fetcher).
3. Al menos **2 ciudades** tienen n≥5 registros cada una.
4. `verify_before_deploy.py` de Fase 1 sigue verde.
5. Revisión explícita de Opus antes de iniciar Fase 2.
6. No hay degradación activa de P/L que requiera priorizar otro frente.

---

## 11. Qué NO autoriza este diseño

Este documento cierra el diseño de Fase 1. Explícitamente **NO autoriza**:

- Subir BANKROLL de $25 a $35 ni a ningún otro nivel.
- Activar Fase C de blocked_signals.
- Implementar Fase 2 (backtesting, probability engines, settlement fidelity real).
- Cualquier cambio a `bot.py`.
- Cualquier cambio a trading core, scheduler, sizing, whitelist, city modes.
- Cualquier cambio a env vars productivas en Railway (fuera de las propias del Truth Pipeline, que quedan OFF).
- Deploy automático.
- Señales ejecutables de ningún tipo.
- BUY, SELL o SKIP reales basados en datos del Truth Pipeline.

---

## 12. Env vars del Truth Pipeline

Todas default OFF, nunca activas en Railway sin aprobación explícita:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TRUTH_PIPELINE_ENABLED` | `0` | Master kill switch |
| `TRUTH_PIPELINE_TELEGRAM_ENABLED` | `0` | Habilita alertas Telegram |
| `TRUTH_PIPELINE_TG_CHAT_ID` | (vacío) | Chat separado del operativo |
| `TRUTH_PIPELINE_DB_PATH` | `$SQLITE_DB_PATH` | Path a polymarket.db |
| `TRUTH_PIPELINE_FETCH_OUTPUT` | `data/truth_pipeline_fetch.json` | Output del fetcher |
| `TRUTH_PIPELINE_ALERT_HOUR_UTC` | `8` | Hora UTC para alerta diaria |

---

*Este documento es la referencia canónica del diseño de Fase 1. La implementación comienza únicamente con aprobación explícita para 1A.1.*
