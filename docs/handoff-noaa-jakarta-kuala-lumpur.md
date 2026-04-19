# Handoff: NOAA research — Jakarta y Kuala Lumpur

**Para**: sesión limpia con Opus  
**Fecha creación**: 2026-04-19  
**Prioridad**: media (estas 2 ciudades son las únicas de las 8 permanentes TRADER_ONLY sin configuración NOAA)

---

## Contexto

El bot tiene un `QUALITY_TRADER_CITIES_WHITELIST` que permite trades canary en mercados `exact/range` cuando un quality trader tiene señal. Las otras 6 ciudades permanentemente TRADER_ONLY (Ankara, Madrid, Miami, Paris, Wellington, Houston) ya fueron agregadas al whitelist en v10.6.21.

Jakarta y Kuala Lumpur aparecen en **6/7** corridas del cross-check como TRADER_ONLY, lo que indica demanda trader consistente. No tienen ninguna configuración NOAA en el bot.

---

## Qué hace falta para cada ciudad

El bot necesita dos entradas por ciudad:

### 1. `RESOLUTION_STATIONS` (en `bot.py`)
```python
"CityName": {"lat": XX.XXXX, "lon": YY.YYYY, "name": "Airport Name"},
```

### 2. `RESOLUTION_ICAO` (en `bot.py`)
```python
"CityName": {"icao": "XXXX", "wu_url": _wu_history_url("XXXX"),
             "noaa_station_id": "...", "noaa_daily_station_id": "..."},
```
Los `noaa_station_id` y `noaa_daily_station_id` son opcionales si no se encuentran (ver Toronto/Warsaw que solo tienen ICAO).

### 3. `CITY_TIMEZONES` (en `bot.py`)
Jakarta y Kuala Lumpur están **ausentes** de CITY_TIMEZONES — necesitan ser agregadas.

---

## Aeropuertos candidatos

### Jakarta
- **Soekarno-Hatta International Airport** — el más probable para Polymarket
  - ICAO: `WIII`
  - Coords aprox: lat -6.1256, lon 106.6559
  - Timezone: `Asia/Jakarta` (WIB, UTC+7)
  - NOAA ISD: por verificar

### Kuala Lumpur
- **Kuala Lumpur International Airport (KLIA)** — el más probable
  - ICAO: `WMKK`
  - Coords aprox: lat 2.7456, lon 101.7099
  - Timezone: `Asia/Kuala_Lumpur` (MYT, UTC+8)
  - NOAA ISD: por verificar

---

## Pasos de la sesión Opus

1. **Verificar qué aeropuerto usa Polymarket para cada ciudad**  
   Buscar en Polymarket mercados activos de Jakarta/KL y ver el texto de resolución. Generalmente indica el aeropuerto.

2. **Buscar NOAA ISD station**  
   URL: `https://www.ncei.noaa.gov/cdo-web/datatools/findstation`  
   Filtrar por país/coords, tipo "Global Surface Summary", verificar registros TMAX en el rango oct-2025/abr-2026.

3. **Buscar GHCND daily station**  
   Mismo portal, tipo "Daily Summaries". Verificar TMAX disponible.

4. **Agregar a bot.py**:
   - `RESOLUTION_STATIONS`
   - `RESOLUTION_ICAO`
   - `CITY_TIMEZONES`

5. **Agregar al whitelist**:
   - Modificar el default en `os.getenv("QUALITY_TRADER_CITIES_WHITELIST", ...)` en bot.py
   - Actualizar Railway env var `QUALITY_TRADER_CITIES_WHITELIST`

6. **Correr `verify_before_deploy.py`** y hacer deploy.

---

## Precedentes de ciudades con NOAA no verificado

Si no se encuentran NOAA IDs válidos con TMAX reciente, se puede agregar igual con solo ICAO (como Toronto/Warsaw/Singapore). El bot podrá tradear pero los trades no tendrán `source: noaa_ncei` — no contarán en WR verificado. Documentar explícitamente en un comentario en `RESOLUTION_ICAO`.

---

## Nota adicional

`OBSERVED_AUDIT_CITIES` también debería incluir Jakarta y KL una vez confirmadas, para auditoría de resolución diaria.
