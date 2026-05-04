# Codex Prompt — Fix copy confuso "20/16 SLs" en SL Retrospective

**Fecha:** 2026-05-04  
**Clasificación:** ACTION_COPY  
**Archivo permitido:** `tools/sl_retrospective.py`

---

## Problema

`TARGET_SAMPLE_SIZE = 16` (línea 24). Cuando `n_resolved` excede ese valor, la línea 827 genera:

```
📊 Resueltos: 20/16 SLs
```

El denominador 16 es menor que el numerador 20. Esto parece un error de formato y puede inducir lecturas erróneas (¿resolvimos más de los posibles? ¿hay datos corruptos?).

---

## Fix esperado

**Solo tocar `tools/sl_retrospective.py`.** No cambiar lógica, no cambiar `TARGET_SAMPLE_SIZE`, no tocar bot.py, alertas, trading ni ningún otro archivo.

### Cambio en línea 827

**Actual:**
```python
f"📊 Resueltos: {n_resolved}/{TARGET_SAMPLE_SIZE} SLs",
```

**Propuesta:**
```python
(
    f"📊 Resueltos: {n_resolved}/{TARGET_SAMPLE_SIZE} SLs"
    if n_resolved <= TARGET_SAMPLE_SIZE
    else f"📊 Resueltos: {n_resolved} SLs (objetivo {TARGET_SAMPLE_SIZE} superado)"
),
```

---

## Validación mínima

1. Ejecutar `python -c "import py_compile; py_compile.compile('tools/sl_retrospective.py', doraise=True)"` → OK.
2. Si `verify_before_deploy.py` tiene tests para el copy de SL retro (buscar con `grep -n "Resueltos\|20/16\|TARGET_SAMPLE" verify_before_deploy.py`), actualizarlos si alguno valida literalmente el string antiguo.
3. `python verify_before_deploy.py` → debe pasar todos los checks existentes.

---

## Guardrails

- No tocar `TARGET_SAMPLE_SIZE`, `PRELIMINARY_THRESHOLD`, `FINAL_THRESHOLD`.
- No cambiar lógica de `_summarize_type()`, `_build_summary()` ni ningún cálculo de WR/PnL.
- No tocar `bot.py`, alertas Telegram en `bot.py`, trading core, scheduler, sizing, bankroll ni env vars.
- No hacer push ni deploy. Solo commit local con mensaje tipo `fix(alerts): sl retro resolved display when n exceeds target`.
