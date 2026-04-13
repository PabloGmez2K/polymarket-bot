# City Probe Visibility Tracker

Tracker persistente y read-only para registrar si ciudades objetivo aparecen o no en cada snapshot del `settlement_fidelity_probe`.

La motivacion principal es dejar de comparar `Shanghai` y `Chicago` con fotos aisladas y empezar a acumular evidencia de:

- cuantas veces aparece cada ciudad;
- cuantas veces aparecen simultaneamente;
- y con cuanta estructura de mercados lo hacen.

---

## Comando base

```powershell
python tools/city_probe_visibility_tracker.py
```

### Variante util

```powershell
python tools/city_probe_visibility_tracker.py --targets Shanghai,Chicago
```

---

## Salidas

- `data/city_probe_visibility_tracker.json`
- `docs/city_probe_visibility_tracker_latest.md`

---

## Uso recomendado

Ejecutarlo cada vez que se regenere `settlement_fidelity_probe.json`.

La señal importante no es solo si una ciudad aparece, sino cuándo `Shanghai` y `Chicago` aparecen en el mismo snapshot. Esa coincidencia es la condición mínima para comparar `market selection` con más rigor.

---

## Guardrails

- no toca `bot.py`
- no consulta red por sí sola
- no reemplaza el probe; solo persiste su visibilidad en el tiempo
