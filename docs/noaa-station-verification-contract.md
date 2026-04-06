# NOAA Station Verification Contract — Sesión 83

**Fecha:** 2026-04-06
**Ejecutor:** Codex (autónomo)
**Revisor:** Claude / Pablo
**Archivos que toca:** `bot.py` (solo `RESOLUTION_ICAO` y `OBSERVED_AUDIT_CITIES`), `CONTEXTO.md` (sección de resultados al final)

---

## Contexto y objetivo

El bot acumula datos NOAA en `observed_vs_forecast` comparando la temperatura real
(NOAA) con el forecast de Open-Meteo. Esto es la base del bias correction por ciudad
(`FORECAST_BIAS_C`) y del sigma empírico. Sin NOAA, una ciudad nunca puede ser promovida
a trading con confianza estadística.

Actualmente **26 ciudades en `RESOLUTION_ICAO` carecen de `noaa_station_id`** y por tanto
nunca acumulan datos, aunque estén en shadow mode observando mercados.

Este contrato define cómo verificar y añadir las estaciones correctas.

---

## Dos IDs por ciudad — roles distintos

| Campo | Dataset NOAA | Formato ejemplo | Rol |
|-------|-------------|-----------------|-----|
| `noaa_station_id` | ISD Global Hourly | `72258303927` | **GATE obligatorio.** Si falta, la ciudad queda fuera del pipeline NOAA completamente. Formato: USAF (6 dígitos) + WBAN (5 dígitos) concatenados. WBAN=99999 para estaciones sin WBAN (internacionales). |
| `noaa_daily_station_id` | GHCND Daily Summaries | `USW00013960` | Fuente preferida para TMAX. Si existe, se usa antes que el hourly. Si no existe, el bot hace fallback a hourly. |

---

## Fuentes de lookup — usar en este orden

### 1. ISD History CSV (para `noaa_station_id`)
```
https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv
```
Columnas clave: `USAF`, `WBAN`, `ICAO`, `BEGIN`, `END`, `CTRY`

Algoritmo:
```python
# Descargar una vez, luego filtrar
rows = [r for r in csv if r['ICAO'] == target_icao and r['END'] >= '20240101']
# noaa_station_id = r['USAF'] + r['WBAN'].zfill(5)
# Si hay múltiples, tomar la más reciente (END mayor)
```

### 2. GHCND Stations list (para `noaa_daily_station_id`)
```
https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt
```
Formato de columnas (fixed-width):
- ID: columnas 1–11
- LAT: 13–20, LON: 22–30, ELEV: 32–37, NAME: 42–71

Para cruzar ISD → GHCND:
- Estaciones US: WBAN del ISD → `USW00` + WBAN (5 dígitos con ceros). Ejemplo: WBAN=14732 → `USW00014732`
- Estaciones internacionales: buscar por cercanía geográfica a las coordenadas del ISD encontrado

### 3. Verificación de datos — OBLIGATORIA para cada estación
```
GET https://www.ncei.noaa.gov/access/services/data/v1
  ?dataset=daily-summaries
  &stations=<noaa_daily_station_id>
  &dataTypes=TMAX
  &startdate=2025-10-01
  &enddate=2026-03-31
  &format=json
  &units=metric
```

**Criterio de aprobación:**
- Devuelve ≥ 30 registros con `TMAX` no nulo en ese periodo
- El valor de TMAX es plausible para la ciudad (entre -30 y +55 °C)
- Si falla o devuelve <30 registros: marcar como `NO_NOAA` (ver abajo)

Para `noaa_station_id` (hourly fallback), verificar con:
```
GET https://www.ncei.noaa.gov/access/services/data/v1
  ?dataset=global-hourly
  &stations=<noaa_station_id>
  &dataTypes=TMP
  &startdate=2026-01-01
  &enddate=2026-03-31
  &format=json
```
Criterio: devuelve al menos 1 registro con TMP válido.

---

## Lista de ciudades a verificar (26)

Ordenadas por prioridad de impacto operativo. Candidatos marcados como [PROBABLE] son estimaciones con alta confianza; [BUSCAR] requieren lookup en isd-history.csv.

### Prioridad 1 — US (NOAA cobertura casi garantizada)

| Ciudad | ICAO actual | Candidato `noaa_daily_station_id` | Candidato `noaa_station_id` |
|--------|-------------|-----------------------------------|-----------------------------|
| New York City | KLGA | `USW00014732` [PROBABLE] | BUSCAR por ICAO=KLGA en isd-history |
| Miami | KMIA | `USW00012839` [PROBABLE] | BUSCAR por ICAO=KMIA |
| Seattle | KSEA | `USW00024233` [PROBABLE] | BUSCAR por ICAO=KSEA |

### Prioridad 2 — Canadá / Europa Occidental

| Ciudad | ICAO actual | Candidato `noaa_daily_station_id` | Candidato `noaa_station_id` |
|--------|-------------|-----------------------------------|-----------------------------|
| Toronto | CYYZ | BUSCAR (formato CA...) | BUSCAR por ICAO=CYYZ |
| London | EGLC | BUSCAR (EGLC=London City; considerar también EGLL=Heathrow si EGLC falla) | BUSCAR |
| Paris | LFPG | BUSCAR | BUSCAR por ICAO=LFPG |
| Munich | EDDM | BUSCAR | BUSCAR por ICAO=EDDM |
| Warsaw | EPWA | BUSCAR | BUSCAR por ICAO=EPWA |
| Madrid | LEMD | BUSCAR | BUSCAR por ICAO=LEMD |
| Milan | LIMC | BUSCAR | BUSCAR por ICAO=LIMC |
| Tel Aviv | LLBG | BUSCAR | BUSCAR por ICAO=LLBG |
| Ankara | LTAC | BUSCAR | BUSCAR por ICAO=LTAC |
| Wellington | NZWN | BUSCAR | BUSCAR por ICAO=NZWN |

### Prioridad 3 — Asia / Resto

| Ciudad | ICAO actual | Notas |
|--------|-------------|-------|
| Tokyo | RJTT | BUSCAR. JMA/NOAA suele tener cobertura. |
| Seoul | RKSI | BUSCAR. KMA/NOAA. |
| Singapore | WSSS | BUSCAR. |
| Hong Kong | VHHH | BUSCAR. |
| Taipei | RCTP | BUSCAR. |
| Shanghai | ZSPD | BUSCAR. Cobertura NOAA para China es irregular. |
| Beijing | ZBAA | BUSCAR. Ídem. |
| Shenzhen | ZGSZ | BUSCAR. Ídem. |
| Chongqing | ZUCK | BUSCAR. Ídem. |
| Chengdu | ZUUU | BUSCAR. Ídem. |
| Wuhan | ZHHH | BUSCAR. Ídem. |
| Lucknow | VILK | BUSCAR. India, cobertura parcial. |
| Sao Paulo | SBGR | BUSCAR. Brasil, cobertura parcial. |

---

## Output esperado en `bot.py`

Para cada ciudad verificada con éxito, actualizar su entrada en `RESOLUTION_ICAO`:

```python
# ANTES
"New York City": {"icao": "KLGA", "wu_url": _wu_history_url("KLGA")},

# DESPUÉS
"New York City": {
    "icao": "KLGA",
    "wu_url": _wu_history_url("KLGA"),
    "noaa_station_id": "<ISD_ID_VERIFICADO>",
    "noaa_daily_station_id": "<GHCND_ID_VERIFICADO>",
},
```

Si solo se encuentra `noaa_station_id` pero no `noaa_daily_station_id` (daily no tiene cobertura suficiente pero hourly sí):
```python
"noaa_station_id": "<ISD_ID_VERIFICADO>",
# noaa_daily_station_id omitido — bot usará fallback hourly
```

Actualizar `OBSERVED_AUDIT_CITIES` añadiendo cada ciudad verificada:
```python
OBSERVED_AUDIT_CITIES = {"Chicago", "Atlanta", "Buenos Aires", "Dallas", "New York City", ...}
```

---

## Ciudades sin cobertura NOAA — protocolo

Si una ciudad no tiene estación verificable (API devuelve <30 registros de TMAX en 6 meses):

1. NO añadir `noaa_station_id` a `RESOLUTION_ICAO`
2. Añadir al bloque `NO_NOAA_CITIES` al final de `RESOLUTION_ICAO` como comentario:
```python
# Ciudades sin cobertura NOAA verificada (2026-04-06) — pendiente alternativa
# Shenzhen: ZGSZ — ISD encontrado pero TMAX <30 registros
# Wuhan: ZHHH — sin entrada en ISD history
```
3. Documentar en `CONTEXTO.md` bajo `## Ciudades sin NOAA` con fecha y motivo

---

## Constraints obligatorios

- **No tocar** lógica de trading, sigma, Kelly, FORECAST_BIAS_C, manage_positions, ni ninguna otra función
- **Solo editar** en `bot.py`: el dict `RESOLUTION_ICAO` y el set `OBSERVED_AUDIT_CITIES`
- **Solo editar** en `CONTEXTO.md`: añadir sección de resultados al final
- Antes de hacer commit: `python verify_before_deploy.py` debe pasar **626/626**
- Si verify falla por algún test de NOAA, reportar el error sin forzar el commit

---

## Entregable final

Un solo commit con:
```
feat(noaa): verificación de estaciones NOAA para N ciudades

Añade noaa_station_id + noaa_daily_station_id a N ciudades en RESOLUTION_ICAO.
Verificadas via ISD history + GHCND daily-summaries API (≥30 TMAX en oct-mar 2025/26).

Ciudades verificadas: NYC, Miami, Seattle, ...
Ciudades sin cobertura: Shenzhen, ...
verify_before_deploy: 626/626.

Co-Authored-By: Codex <noreply@openai.com>
```
