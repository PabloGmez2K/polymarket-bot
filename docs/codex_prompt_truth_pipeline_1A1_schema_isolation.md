# Prompt de implementación — Truth Pipeline 1A.1: Schema + tests de aislamiento

**ESTADO:** PROMPT PREPARADO — NO EJECUTAR sin aprobación explícita del usuario  
**Subfase:** 1A.1 de Fase 1 Truth Pipeline  
**Para:** Codex  
**Fecha de preparación:** 2026-05-04

---

## Contexto obligatorio antes de ejecutar

1. Leer `docs/truth_pipeline_phase1.md` completo (diseño canónico cerrado por Opus).
2. Leer `sql/001_init.sql` (schema v1 actual — tablas Fase 0).
3. Leer `sqlite_recorder.py` (recorder activo en Railway).
4. Leer el bloque `## Guardrails` de `AGENTS.md`.
5. Verificar que `python verify_before_deploy.py` pasa antes de empezar.

---

## Tarea

Implementar **solo** subfase 1A.1: schema SQLite v2 + tests de aislamiento.

**No implementar:** fetcher, runner, Telegram, bot.py, trading core.

---

## Cambios autorizados

### 1. Nuevo archivo `sql/002_truth_pipeline.sql`

Migración aditiva que añade dos tablas y sus índices a `polymarket.db`.

Tablas a crear:

**`truth_records`:**
```sql
CREATE TABLE IF NOT EXISTS truth_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    city                TEXT NOT NULL,
    date_iso            TEXT NOT NULL,
    condition           TEXT,
    threshold_c         REAL,
    question            TEXT,
    market_id           TEXT,
    token_id_yes        TEXT,
    token_id_no         TEXT,
    forecast_high_c     REAL,
    forecast_source     TEXT,
    observed_high_c     REAL,
    observed_source     TEXT,
    resolution_outcome  TEXT,
    resolution_ts_utc   TEXT,
    resolution_method   TEXT,
    bot_had_position    INTEGER DEFAULT 0,
    bot_side            TEXT,
    snapshot_ts_utc     TEXT NOT NULL,
    payload_json        TEXT NOT NULL
);
```

**`truth_revisions`:**
```sql
CREATE TABLE IF NOT EXISTS truth_revisions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    truth_record_id   INTEGER NOT NULL,
    field_changed     TEXT NOT NULL,
    old_value         TEXT,
    new_value         TEXT,
    revision_ts_utc   TEXT NOT NULL,
    reason            TEXT,
    FOREIGN KEY (truth_record_id) REFERENCES truth_records(id)
);
```

Índices:
```sql
CREATE INDEX IF NOT EXISTS idx_truth_city     ON truth_records (city, date_iso);
CREATE INDEX IF NOT EXISTS idx_truth_outcome  ON truth_records (resolution_outcome);
CREATE INDEX IF NOT EXISTS idx_truth_rev_rec  ON truth_revisions (truth_record_id);
```

El archivo debe empezar con:
```sql
-- sql/002_truth_pipeline.sql — Schema v2 (Fase 1: Truth Pipeline)
-- Migración aditiva. No modifica tablas v1 (cycle_events, market_snapshots, forecast_snapshots).
-- Ejecutar solo sobre DB existente con schema_version=1 aplicado.
```

Y terminar con:
```sql
INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (2, datetime('now'));
```

### 2. Nuevo archivo `tools/truth_pipeline_schema.py`

Script standalone stdlib-only que aplica la migración:

```
python tools/truth_pipeline_schema.py --db data/polymarket.db [--dry-run]
```

Comportamiento:
- Lee `sql/002_truth_pipeline.sql` desde la ruta relativa al script.
- Verifica que `schema_version=1` existe antes de aplicar.
- Aplica en una transacción, con rollback en error.
- Con `--dry-run`: imprime el SQL pero no ejecuta.
- Salida: `{"status": "applied"|"already_applied"|"dry_run"|"error", "version": 2}`.
- **No importa `bot.py`.**
- **No toca tablas v1.**
- **No hace llamadas externas.**

### 3. Actualizar `verify_before_deploy.py`

Añadir checks para esta subfase. Los checks deben verificar:

1. `sql/002_truth_pipeline.sql` existe en el repo.
2. `tools/truth_pipeline_schema.py` existe en el repo.
3. `truth_pipeline_schema.py` no importa `bot.py`.
4. `truth_pipeline_schema.py` no importa módulos externos (solo stdlib).
5. `sql/002_truth_pipeline.sql` contiene `truth_records` y `truth_revisions`.
6. `sql/002_truth_pipeline.sql` contiene `schema_version` insert con versión 2.
7. `truth_pipeline_schema.py` contiene `--dry-run`.
8. `truth_pipeline_schema.py` no contiene `execute_trade`, `manage_positions`, `intra_cycle_sl_check`.
9. `sql/002_truth_pipeline.sql` no contiene `DROP TABLE` ni `ALTER TABLE` sobre tablas v1.
10. `TRUTH_PIPELINE_ENABLED` no está hardcodeado como `1` en ningún archivo Python del repo.

---

## Tests de aislamiento requeridos

Además de los checks de `verify_before_deploy.py`, el script `tools/truth_pipeline_schema.py` debe poder ejecutar:

```bash
python tools/truth_pipeline_schema.py --db :memory: --dry-run
```
→ Sin error, salida JSON con `status=dry_run`.

```bash
python tools/truth_pipeline_schema.py --db /tmp/test_truth.db
```
→ Sin error, crea las tablas, inserta `schema_version=2`.

Idempotencia:
```bash
python tools/truth_pipeline_schema.py --db /tmp/test_truth.db
python tools/truth_pipeline_schema.py --db /tmp/test_truth.db
```
→ Segunda corrida sale con `status=already_applied` sin error.

---

## Cambios prohibidos en esta subfase

- **No tocar `bot.py`** bajo ninguna circunstancia.
- **No tocar `sqlite_recorder.py`.**
- **No crear fetcher, runner ni alert.**
- **No añadir env vars a Railway.**
- **No hacer deploy.**
- **No añadir importaciones de `requests`, `httpx` ni ninguna librería externa.**
- **No tocar tablas v1** (`cycle_events`, `market_snapshots`, `forecast_snapshots`).
- **No tocar trading core, BANKROLL, sizing, whitelist, city modes, scheduler.**

---

## Validación requerida antes de cerrar

1. `python tools/check_python_syntax.py tools/truth_pipeline_schema.py verify_before_deploy.py` → OK.
2. `python verify_before_deploy.py` pasa en verde sin regresión.
3. `git diff --check` → OK (solo avisos LF/CRLF de Windows son aceptables).
4. `python tools/truth_pipeline_schema.py --db :memory: --dry-run` → OK.
5. Test de idempotencia manual en DB temporal → `already_applied` en segunda corrida.

---

## Entrega esperada

- `sql/002_truth_pipeline.sql` creado.
- `tools/truth_pipeline_schema.py` creado.
- `verify_before_deploy.py` actualizado con los 10 checks nuevos.
- Hash de commit (sin push — Pablo revisa antes).
- Confirmación de que no se tocó `bot.py`, trading core, ni se cambió ninguna env var.
- `verify_before_deploy.py` pasa en verde.

---

*No ejecutar este prompt sin aprobación explícita del usuario. Ver `docs/truth_pipeline_phase1.md` para contexto completo.*
