# Settlement Fidelity Probe

Herramienta read-only para medir, por mercado direccional activo, que informacion tenemos hoy sobre:

- precio actual de mercado;
- forecast operativo `Open-Meteo`;
- metadata de resolucion (`icao`, `wu_url`);
- proxy observado NOAA cuando la fecha ya esta resuelta y hay datos.

No modifica `bot.py` ni cambia la logica de trading.

---

## Objetivo

Responder con evidencia a una pregunta previa a cualquier cambio estrategico:

**el gap principal parece venir de `Open-Meteo vs settlement-proxy`, de seleccion de mercados, o de falta de observabilidad?**

Esta herramienta no resuelve todavia el forecast de Weather Underground. Deja esa integracion marcada como pendiente y, mientras tanto, aterriza una base minima repetible para comparar:

- `mercado`
- `Open-Meteo`
- `NOAA observado`
- `metadata de resolucion`

---

## Comando base

```powershell
python tools/settlement_fidelity_probe.py
```

### Variantes utiles

```powershell
python tools/settlement_fidelity_probe.py --limit 10
python tools/settlement_fidelity_probe.py --city Dallas
python tools/settlement_fidelity_probe.py --skip-noaa
python tools/settlement_fidelity_probe.py --skip-openmeteo
```

---

## Salidas

Por defecto genera:

- `data/settlement_fidelity_probe.json`
- `docs/settlement_fidelity_probe_latest.md`

### JSON

Pensado para analisis posterior o para que Claude/Codex lo reutilicen sin reparsear logs.

Campos principales por mercado:

- `city`
- `date_iso`
- `condition`
- `market_prob_yes`
- `openmeteo_forecast_max_c`
- `noaa_observed_max_c`
- `forecast_vs_noaa_gap_c`
- `resolution_icao`
- `resolution_wu_url`
- `probe_readiness`

### Markdown

Pensado para lectura rapida humana:

- resumen de conteos;
- muestra de mercados;
- ciudades top.

---

## Como interpretar los resultados

### Caso 1 - `openmeteo_forecast_max_c` existe y `noaa_observed_max_c` no

Es un mercado futuro o muy reciente. Sirve para validar:

- cobertura de ciudades;
- metadata de resolucion;
- disponibilidad de forecast operativo.

### Caso 2 - ambos existen

Ya podemos medir:

- desvio `Open-Meteo - NOAA observado`;
- si ese gap parece pequeno, estable o problematico por ciudad.

### Caso 3 - falta `resolution_icao` o `wu_url`

La deuda no es de modelo sino de capa de resolucion / observabilidad.

---

## Limitaciones honestas

1. `Weather Underground forecast` no esta automatizado todavia.
2. `NOAA observado` sigue siendo proxy observado, no settlement live scrapeado.
3. El probe no mide profundidad de order book ni spread.
4. El probe no modifica el scheduler ni la frecuencia real del bot.

---

## Siguiente paso despues de este probe

Si la salida confirma que el cuello principal sigue siendo settlement/source gap:

- continuar con una capa mas fuerte de settlement fidelity.

Si la salida es razonablemente estable y el gap no explica mucho:

- pasar a `Directional Trader Census v1`.

---

## Punto de handoff para Claude

Si Claude retoma desde aqui:

1. correr `python tools/settlement_fidelity_probe.py --limit 10`;
2. leer `data/settlement_fidelity_probe.json`;
3. decidir si falta:
   - mejorar la captura de settlement/source,
   - o ya abrir el censo de traders direccionales.
