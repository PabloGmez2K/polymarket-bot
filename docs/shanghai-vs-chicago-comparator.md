# Shanghai vs Chicago Comparator

Comparador directo entre:

- `Shanghai` como ciudad puente en `shadow`
- `Chicago` como benchmark operativo `active`

Su objetivo es responder de forma compacta donde esta hoy el gap dominante.

---

## Preguntas que responde

1. Quien gana por rol operativo actual.
2. Quien tiene mas profundidad de referencias.
3. Si el gap actual parece de:
   - market visibility / selection
   - asimetria de evidencia
   - o falta de datos live
4. Cual es el siguiente paso recomendable.

---

## Comando base

```powershell
python tools/shanghai_vs_chicago_comparator.py
```

---

## Salidas

- `data/shanghai_vs_chicago_comparator.json`
- `docs/shanghai_vs_chicago_comparator_latest.md`

---

## Guardrails

- no toca `bot.py`
- no mueve ciudades de modo
- no reemplaza los snapshots individuales
- solo sintetiza el gap operativo entre ambas
