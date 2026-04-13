# Worktree Hygiene Audit — 2026-04-12

**Fecha:** 2026-04-12  
**Estado al inicio:** 7 archivos modificados, ~167 archivos sin trackear  
**Ejecutado por:** Claude Code Sonnet 4.6

---

## 1. Resumen ejecutivo

El worktree acumuló suciedad porque el `.gitignore` solo cubre artefactos Python y de IDE, ignorando completamente los tres flujos que generan archivos nuevos en cada sesión de trabajo: (1) snapshots de Railway, (2) outputs de herramientas de análisis y (3) documentación de sesión. Ninguno de estos archivos debería versionarse, pero ninguno estaba excluido. El resultado es un `git status` de ~167 archivos sin trackear que se reinicia a 0 con las reglas mínimas descritas aquí.

Adicionalmente, cinco archivos generados por herramientas fueron commiteados en sesiones previas y están perpetuamente `Modified` en cada ejecución. Necesitan ser untrackeados.

---

## 2. Mapa de fuentes de suciedad

### 2.1 `data/runtime_import/` — **Causa raíz #1 (mayor volumen)**

| Archivo | Fuente | Regenerable |
|---------|--------|-------------|
| `audit.json` | `tools/railway_runtime_snapshot_pull.ps1` | ✅ Siempre |
| `cycle_summary.json` | ídem | ✅ Siempre |
| `cycles_history.jsonl` | ídem | ✅ Siempre |
| `performance.json` | ídem | ✅ Siempre |
| `policy_env_snapshot.json` | ídem | ✅ Siempre |
| `postmortem.json` | ídem | ✅ Siempre |
| `runtime_import_manifest.json` | ídem | ✅ Siempre |
| `shadow_city_tracking.json` | ídem | ✅ Siempre |
| `skip_log.jsonl` | ídem | ✅ Siempre |
| `trade_lifecycle.json` | ídem | ✅ Siempre |
| `city_policy_state.json` | ídem (⚠️ estaba trackeado) | ✅ Siempre |
| `decisions.log` | ídem | ✅ Siempre |

**Diagnóstico:** Estos archivos son siempre una foto de Railway. La fuente de verdad canónica vive en el volumen de Railway (`/app/data/`). El repo no es el lugar correcto para versionar snapshots de producción.

**Error previo:** `city_policy_state.json` fue commiteado en algún momento como si fuera un archivo de configuración del repo. Pero su contenido cambia en cada ciclo del bot (promociones de ciudad, `updated_at`, etc.) y siempre es sobreescrito por el pull. Debe ser untrackeado.

### 2.2 `data/runtime_import_derived/` — **Causa raíz #2**

Directorio creado por `tools/city_validation_ledger.py` y `tools/city_promotion_gate.py` como espacio de trabajo de validación cruzada. Sus archivos son siempre derivados de `runtime_import/` y nunca son fuente de verdad.

### 2.3 `data/*.json` outputs de tools — **Causa raíz #3**

| Patrón | Script generador | Tipo |
|--------|-----------------|------|
| `data/system_alignment_check.json` | `tools/system_alignment_check.py` | Snapshot regenerable |
| `data/system_alignment_check_operational.json` | ídem (⚠️ trackeado) | Snapshot regenerable |
| `data/runtime_policy_effective_view.json` | `tools/runtime_policy_effective_view.py` (⚠️ trackeado) | Snapshot regenerable |
| `data/city_intelligence_pipeline.json` | `tools/city_intelligence_pipeline.py` | Snapshot regenerable |
| `data/city_intelligence_alert_state.json` | `tools/city_intelligence_*` | Estado de servicio |
| `data/city_intelligence_daily_summary_state.json` | ídem | Estado de servicio |
| `data/city_validation_ledger.json` | `tools/city_validation_ledger.py` | Análisis regenerable |
| `data/city_promotion_gate.json` | `tools/city_promotion_gate.py` | Análisis regenerable |
| `data/city_watchlist_phase4.json` | `tools/city_watchlist_phase4.py` | Análisis regenerable |
| `data/city_watch_reinforced.json` | `tools/city_watch_reinforced.py` | Análisis regenerable |
| `data/city_phase5_contrast.json` | `tools/city_phase5_contrast.py` | Análisis regenerable |
| `data/city_probe_visibility_tracker.json` | `tools/city_probe_visibility_tracker.py` | Análisis regenerable |
| `data/phase5_visibility_pipeline.json` | `tools/phase5_visibility_pipeline.py` | Análisis regenerable |
| `data/phase5_visibility_alert_state.json` | ídem | Análisis regenerable |
| `data/directional_trader_census.json` | `tools/directional_trader_census.py` | Análisis regenerable |
| `data/directional_trader_enrichment.json` | `tools/directional_trader_enrichment.py` | Análisis regenerable |
| `data/reference_trader_city_market_cross.json` | `tools/reference_trader_city_market_cross.py` | Análisis regenerable |
| `data/settlement_fidelity_probe.json` | `tools/settlement_fidelity_probe.py` | Análisis regenerable |
| `data/shanghai_shadow_test.json` | `tools/shanghai_shadow_test.py` | Análisis regenerable |
| `data/shanghai_vs_chicago_comparator.json` | `tools/shanghai_vs_chicago_comparator.py` | Análisis regenerable |
| `data/chicago_active_benchmark.json` | `tools/chicago_active_benchmark.py` | Análisis regenerable |

**Diagnóstico:** El patrón consistente de todos los scripts en `tools/` es `DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "<nombre>.json"`. El directorio `data/` recibe todos los outputs automáticamente. No hay separación entre datos canónicos (`data/forecast_accuracy_raw.json`) y snapshots regenerables.

### 2.4 `docs/*_latest.md` — **Causa raíz #4**

Cada script de análisis también escribe un readout en Markdown bajo `docs/<nombre>_latest.md`. Patrón: `DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "<nombre>_latest.md"`. Cinco de estos archivos estaban trackeados (error):
- `docs/runtime_policy_effective_view_latest.md` ← **trackeado, siempre Modified**
- `docs/system_alignment_check_operational_latest.md` ← **trackeado, siempre Modified**

### 2.5 `docs/next-session-handoff-*.md` — **Causa raíz #5**

Patrón de sesión: al cerrar cada sesión se crea `docs/next-session-handoff-YYYY-MM-DD-<tema>.md`. Estos archivos son señales de traspaso entre sesiones de Claude, no documentación permanente del sistema. Acumulan uno o varios por sesión de trabajo.

### 2.6 `docs/claude-opus-prompt-*.md` y `docs/codex-prompt-*.md` — **Causa raíz #6**

Archivos de preparación de prompts para modelos. Son artefactos de sesión de IA, no documentación del sistema. No aportan valor versionado porque su contenido es de un solo uso.

### 2.7 `tools/*.py` / `tools/*.ps1` nuevos — **Causa raíz #7 (inversa)**

Todos los scripts nuevos en `tools/` están sin trackear. Son código real y deberían estar versionados. El repo tiene 9 scripts trackeados en `tools/` y ~25 sin trackear. Esta es la única categoría donde el problema es de *menos* tracking, no más.

### 2.8 Root-level artifacts — **Causa raíz #8**

- `RESEARCH_CODEX_TRADERS_2026-04-08.md`, `RESEARCH_OPUS_TRADERS_2026-04-08.md` — documentos de investigación creados en la raíz, deberían estar en `docs/` o gitignoreados.
- `RTK.md` — shim intencional (Sesión 159), merece ser trackeado.

---

## 3. Clasificación de cada patrón

| Categoría | Patrón | Acción |
|-----------|--------|--------|
| **Fuente de verdad canónica** | `data/forecast_accuracy_raw.json`, `seed_data/**` | Mantener trackeado |
| **Código (scripts de tools)** | `tools/*.py`, `tools/*.ps1` nuevos | Agregar a git |
| **Docs permanentes de sistema** | `docs/metrics-funnel-naming.md`, `docs/decision-preflight-rules-*.md`, `docs/system-mental-model-*.md`, `docs/bot-funnel-counter-contract-*.md`, `docs/system-alignment-*.md`, `docs/controlled-monetization-gate-*.md`, `docs/phase6-5-*.md`, `docs/city-window-routing-design-*.md`, `docs/experiment-results-*.md` | Agregar a git |
| **Snapshot Railway** | `data/runtime_import/` | Gitignore + untrack `city_policy_state.json` |
| **Análisis derivado** | `data/runtime_import_derived/` | Gitignore |
| **Outputs regenerables** | `data/*.json` generados por tools | Gitignore + untrack 2 archivos |
| **Readouts regenerables** | `docs/*_latest.md` | Gitignore + untrack 2 archivos |
| **Handoffs de sesión** | `docs/next-session-handoff-*.md` | Gitignore |
| **Prompts de modelo** | `docs/claude-opus-prompt-*.md`, `docs/codex-prompt-*.md` | Gitignore |
| **Research raíz** | `RESEARCH_*.md` en root | Gitignore (mover a docs/ si se quieren conservar) |
| **RTK shim** | `RTK.md` | Agregar a git |
| **seed_data untracked** | `seed_data/phase5/*.json` | Agregar a git |

---

## 4. Cambios implementados

### 4.1 `.gitignore` — reglas añadidas

```
# ─── Runtime imports (Railway snapshot, never canonical) ─────────────────────
data/runtime_import/
data/runtime_import_derived/

# ─── Tool-generated output snapshots (regenerable) ───────────────────────────
data/system_alignment_check.json
data/system_alignment_check_operational.json
data/runtime_policy_effective_view.json
data/city_intelligence_pipeline.json
data/city_intelligence_alert_state.json
data/city_intelligence_daily_summary_state.json
data/city_phase5_contrast.json
data/city_probe_visibility_tracker.json
data/city_promotion_gate.json
data/city_validation_ledger.json
data/city_watch_reinforced.json
data/city_watchlist_phase4.json
data/phase5_visibility_alert_state.json
data/phase5_visibility_pipeline.json
data/directional_trader_census.json
data/directional_trader_enrichment.json
data/reference_trader_city_market_cross.json
data/settlement_fidelity_probe.json
data/shanghai_shadow_test.json
data/shanghai_vs_chicago_comparator.json
data/chicago_active_benchmark.json

# ─── Docs: regenerable readouts (scripts write these automatically) ───────────
docs/*_latest.md

# ─── Docs: session-ephemeral artifacts ───────────────────────────────────────
docs/next-session-handoff-*.md
docs/claude-opus-prompt-*.md
docs/codex-prompt-*.md

# ─── Root: research / session artifacts ──────────────────────────────────────
RESEARCH_*.md
```

### 4.2 Archivos untrackeados con `git rm --cached`

Los siguientes archivos estaban trackeados pero son regenerables; deben salir del índice sin eliminarse del disco:

- `data/runtime_import/city_policy_state.json`
- `data/runtime_policy_effective_view.json`
- `data/system_alignment_check_operational.json`
- `docs/runtime_policy_effective_view_latest.md`
- `docs/system_alignment_check_operational_latest.md`

### 4.3 Archivos agregados a tracking

**tools/ (código nuevo):**  
Todos los scripts `tools/*.py` y `tools/*.ps1` sin trackear.

**seed_data/:**  
`seed_data/phase5/*.json`

**Docs permanentes:**  
Documentos de diseño, contratos y resultados de experimentos con valor permanente.

**Root:**  
`RTK.md`

---

## 5. Política de versioning

### Regla simple: ¿Para qué existe el archivo?

| Si el archivo es... | ¿Se versiona? | Ubicación correcta |
|--------------------|:-------------:|--------------------|
| Código (scripts) | ✅ Sí | `tools/` |
| Datos canónicos de entrada | ✅ Sí | `data/` o `seed_data/` |
| Diseño, contrato, roadmap, decisión | ✅ Sí | `docs/` |
| Snapshot de producción (Railway pull) | ❌ No | `data/runtime_import/` (gitignored) |
| Output regenerable de un script | ❌ No | `data/*.json` (gitignored) |
| Readout regenerable de un script | ❌ No | `docs/*_latest.md` (gitignored) |
| Handoff de sesión | ❌ No | `docs/next-session-handoff-*.md` (gitignored) |
| Prompt preparado para modelo | ❌ No | `docs/claude-opus-prompt-*.md` (gitignored) |

### Cuándo generar artefactos y cuándo no

- **Siempre está bien correr** `railway_runtime_snapshot_pull.ps1` — refresha `data/runtime_import/`, gitignored.
- **Siempre está bien correr** `system_alignment_check.py` — genera `data/system_alignment_check*.json` y `docs/*_latest.md`, ambos gitignored.
- **Herramientas de análisis** (`city_validation_ledger.py`, `city_promotion_gate.py`, etc.) — sus outputs en `data/` y `docs/` son gitignored.
- **Docs de sesión con valor permanente** deben crearse bajo un nombre sin `_latest` y sin `next-session-handoff-` para ser elegibles para commiting.

### Convención de nombres para docs permanentes

```
docs/<tema>-<YYYY-MM-DD>.md          # análisis con fecha
docs/<tema>.md                        # referencia permanente sin fecha
```

No usar:
- `docs/<nombre>_latest.md` — reservado para readouts automáticos (gitignored)
- `docs/next-session-handoff-*.md` — reservado para handoffs (gitignored)

---

## 6. Prevención a futuro

El problema reaparecerá si:

1. **Se commitean outputs de tools** — Si alguien hace `git add docs/` o `git add data/` con wildcard, el `.gitignore` ahora bloquea los archivos de sesión.

2. **Se añaden nuevos scripts sin añadir sus outputs al `.gitignore`** — Al crear un nuevo script en `tools/` que escribe a `data/<nuevo>.json` y `docs/<nuevo>_latest.md`, hay que añadir esos paths al `.gitignore`. El patrón es predecible: `DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "<nombre>.json"`.

3. **Se crean nuevas sesiones de análisis** — Los docs de sesión deben usar nombres con fecha (no `_latest`) y los handoffs no deben acumularse.

### Checklist de nueva herramienta (al crear un script en `tools/`)

```
[ ] git add tools/<nuevo_script>.py
[ ] Si el script escribe data/<nombre>.json   → añadir al .gitignore
[ ] Si el script escribe docs/<nombre>_latest.md → ya cubierto por docs/*_latest.md
[ ] Si hay seed data de entrada → git add seed_data/<archivo>
```
