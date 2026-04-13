# City Phase 5 Contrast

Comparador read-only para las ciudades prioritarias del siguiente bloque.

Usa el mismo motor de snapshot del test de `Shanghai`, pero lo aplica a varias ciudades a la vez para evitar que la decision estrategica dependa de una sola ciudad puente.

---

## Objetivo

Contrastar:

- una ciudad `shadow` puente como `Shanghai`,
- una ciudad `active` benchmark como `Chicago`,
- y una `shadow` secundaria como `Seoul`,

para decidir si el siguiente paso debe centrarse en:

- seguir reforzando `Shanghai`,
- usar `Chicago` como benchmark activo,
- o ampliar observabilidad cruzada antes de escalar.

---

## Comando base

```powershell
python tools/city_phase5_contrast.py
```

### Variante util

```powershell
python tools/city_phase5_contrast.py --cities Shanghai,Chicago,Seoul
```

---

## Salidas

- `data/city_phase5_contrast.json`
- `docs/city_phase5_contrast_latest.md`

---

## Lectura recomendada

1. `recommendation.recommended_next_step`
2. tabla de ranking
3. racional por ciudad

---

## Guardrails

- no toca `bot.py`
- no cambia policy de ciudades
- no promociona ciudades
- no reemplaza los snapshots individuales; los complementa
