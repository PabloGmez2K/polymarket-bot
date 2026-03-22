# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 22 de marzo de 2026 (Sesión 8)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 10%, apuesta en la dirección correcta. Es arbitraje de información: mejor dato = mejor precio = ganancia.

**Bankroll:** $15 de prueba (objetivo: $100 cuando validemos que el sistema gana).

**Modelo de Claude recomendado:** Sesiones de coding puro → Sonnet. Revisiones de arquitectura, estrategia o diseño de sistemas → Opus.

---

## Progreso: ~97%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto, 30 ciudades)
- [x] Lectura de mercados de Polymarket (Gamma API, tags, parseo regex)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Half-Kelly + presupuesto global)
- [x] Backtest básico (91.4% precisión, 116 mercados)
- [x] Git/GitHub
- [x] Autenticación con Polymarket (Magic wallet, firma EIP-712, credenciales L2)
- [x] Ejecución real de órdenes (DRY_RUN flag, GTC limit orders)
- [x] Filtro de precio 8¢–92¢, agresividad +2¢, check duplicados, limpieza stale
- [x] Despliegue en Railway (bot corriendo 24/7)
- [x] Alertas Telegram (arranque, órdenes, errores)
- [x] Scheduler estratégico (horas UTC fijas: 08, 16, 23)
- [x] Comandos Telegram con botones inline (Estado, Cartera, Órdenes, Log, Forzar, Modo)
- [x] Cartera real desde Data API (posiciones + PnL)
- [x] Toggle DRY_RUN desde Telegram (con doble confirmación)
- [x] Decision log (decisions.log + /log en Telegram)
- [x] known_tokens cache (fix órdenes sin enriquecer)
- [x] Threading (polling Telegram + scheduler en paralelo)
- [x] MODO REAL activado con $15
- [x] Procfile para Railway
- [x] DRY_RUN=false permanente en Railway Variables
- [x] bot.py v8: MIN_DAYS=0, MAX_DAYS=5, reintentos de red, +11 ciudades nuevas
- [x] Pipeline de inteligencia de mercado (find_traders + trader_analyzer + traders_db)
- [x] Análisis de 3 traders de referencia (ColdMath, Trader2, Trader3)
- [x] Sistema de histórico acumulativo (trader_history.json)
- [ ] Optimizar find_traders.py para descubrir traders más relevantes
- [ ] Automatizar pipeline de análisis en Railway (ejecución periódica)
- [ ] Validar resultados: correr varios días y analizar decisions.log
- [ ] Parsear mercados de rangos "46-47°F" (+30% mercados)
- [ ] Calibrar sigma con datos reales
- [ ] Escalar a $100 (solo si los datos confirman que gana)

---

## Historial de sesiones

### Sesión 1 (21 marzo 2026)
- Primera llamada a API (Open-Meteo, previsión de Wellington)
- Aprendí: terminal cmd, APIs REST, JSON, por qué no hacer doble clic en .py

### Sesión 2 (21 marzo 2026) — Modelo: Opus
- `weather_forecast.py`, `polymarket_explore.py`, `edge_detector.py` v3
- `backtest.py` (91.4% precisión, 116 mercados), `bankroll.py`, `bot.py` v1
- Git instalado, repo en GitHub
- **Descubrimiento:** coords centro ciudad vs aeropuerto pueden diferir 1-6°C

### Sesión 3 (21 marzo 2026) — Modelo: Opus
- pip, py-clob-client, web3, eth-account, httpx
- Conexión CLOB API, autenticación completa (EIP-712, credenciales L2)
- Primera orden colocada y cancelada (test)
- **Bug:** `clobTokenIds` como string JSON → fix json.loads()

### Sesión 4 (21 marzo 2026) — Modelo: Sonnet
- `bot.py` v2: autenticación integrada, ejecución real, todos los fixes
- **Primera ejecución real:** 2 órdenes vivas (Shanghai YES 16°C, Wellington YES 18°C)

### Sesión 5 (21 marzo 2026) — Modelo: Opus
- **Revisión estratégica completa** — bot.py v3 con 4 mejoras clave
- Filtro precio, agresividad, duplicados, stale
- Exposición total subida de 30% a 40%

### Sesión 6 (21 marzo 2026) — Modelo: Sonnet
- requirements.txt, DRY_RUN/BANKROLL como env vars
- Despliegue en Railway, alertas Telegram

### Sesión 7 (21 marzo 2026) — Modelo: Opus
- **bot.py v7** — Reescritura mayor del bot
- Scheduler estratégico, Telegram bidireccional, decision log, known_tokens cache
- **MODO REAL activado** a las 23:09 UTC

### Sesión 8 (22 marzo 2026) — Modelo: Sonnet
- **Análisis de primeros ciclos reales** — bot funcionó pero encontró 0 oportunidades
  - Diagnóstico: MIN_DAYS=1 descartaba 225 mercados de hoy, solo 6 pasaban filtro
  - Error de red en ciclo 23:00 (`Connection reset by peer`) — sin reintentos
- **bot.py v8** con 3 mejoras clave:
  - `MIN_DAYS_AHEAD = 0` — incluye mercados de hoy (sigma=0.8°C, máxima confianza)
  - `MAX_DAYS_AHEAD = 5` — amplía ventana de 3 a 5 días
  - Reintentos automáticos en `api_get` y `get_forecast` (3 intentos, 5s delay)
- **+11 ciudades nuevas** (de 19 a 30): Miami, Madrid, Seattle, Dallas, Lucknow, Sao Paulo, Taipei, Milan, Chongqing, Chengdu, Wuhan
  - Ciudades identificadas analizando traders de referencia
- **Pipeline de inteligencia de mercado** construido desde cero:
  - `coldmath_tracker.py` → análisis de trader individual
  - `trader_analyzer.py` → análisis multi-trader con consenso, edge validation, histórico
  - `find_traders.py` → descubrimiento automático de traders similares vía API
  - `traders_db.json` → registro central persistente de traders
  - `trader_history.json` → histórico acumulativo de análisis
- **Análisis de 3 traders de referencia:**
  - **ColdMath** (0x594e...): $70K bankroll, 87% WR, opera No a $0.95-0.99 → no relevante para nuestra escala
  - **Trader2** (0xd393...): bankroll pequeño, opera Yes a $0.003-0.05, 45% WR → estrategia de lotería masiva, no imitar
  - **Found1** (0x4174...): 75.8% WR, opera en rango medio ($0.10-0.90), London/Ankara → más relevante
- **Descubrimiento clave de API:** `/trades?market=conditionId` funciona; `/positions?market=` da 400 error
- **Conceptos aprendidos:** pipeline de datos, JSON como base de datos simple, endpoint discovery por debug, estrategias de trading comparadas

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, MODO REAL, DRY_RUN=false permanente, schedule 08/16/23 UTC

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v8 — scheduler + Telegram + decision log |
| `Procfile` | Indica a Railway cómo arrancar (`web: python bot.py`) |
| `requirements.txt` | Librerías para Railway |
| `trader_analyzer.py` | Análisis multi-trader: consenso, edge, histórico |
| `find_traders.py` | Descubrimiento automático de traders similares |
| `traders_db.json` | Registro central de traders (NO en git si contiene datos sensibles) |
| `trader_history.json` | Histórico de análisis acumulativo |
| `decisions.log` | Log detallado de cada decisión del bot (en Railway) |
| `trades.log` | Registro técnico de operaciones (en Railway) |
| `edge_detector.py` | Detección de edge (standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `.env` | Claves (NO en git) |

### Configuración en bot.py v8:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = 10.0
MIN_BET = 1.00
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.40
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5        # v8: ampliado de 3
MIN_DAYS_AHEAD = 0        # v8: incluye hoy
MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
SCHEDULE_HOURS_UTC = [8, 16, 23]
```

### 30 ciudades cubiertas (RESOLUTION_STATIONS):
Seoul, London, Tel Aviv, Shanghai, Tokyo, New York City, Beijing, Hong Kong, Singapore, Toronto, Chicago, Wellington, Munich, Warsaw, Ankara, Atlanta, Shenzhen, Paris, Buenos Aires, Miami, Madrid, Seattle, Dallas, Lucknow, Sao Paulo, Taipei, Milan, Chongqing, Chengdu, Wuhan

### Pipeline de análisis de traders:
```
find_traders.py          →    traders_db.json    →    trader_analyzer.py
(descubre via /trades)        (registro central)       (analiza todos)
                                                              ↓
                                                    trader_history.json
                                                    (acumulación histórica)
```

**Endpoint que funciona para traders de un mercado:**
```
GET https://data-api.polymarket.com/trades?market={conditionId}&limit=100
```
Campos útiles: `proxyWallet`, `side`, `price`, `size`, `timestamp`, `outcome`, `pseudonym`

**Endpoints que NO funcionan:**
- `/positions?market=conditionId` → 400 Bad Request
- `/positions?asset_id=tokenId` → 400 Bad Request
- `/markets/{tokenId}/top-holders` → 404

### APIs utilizadas:
| API | URL | Función |
|-----|-----|---------|
| Gamma API | gamma-api.polymarket.com | Mercados, preguntas, precios |
| Data API | data-api.polymarket.com | Posiciones del usuario, trades, PnL |
| CLOB API | clob.polymarket.com | Órdenes, autenticación |
| Open-Meteo | api.open-meteo.com | Previsiones meteorológicas |
| Telegram | api.telegram.org | Dashboard + alertas |

---

## Traders de referencia analizados

| Nombre | Address | Bankroll | WR | Estrategia | Relevancia |
|--------|---------|---------|----|-----------|-|
| ColdMath | 0x594e... | ~$70K | 87% | No a $0.95-0.99 | Baja — escala diferente |
| Trader2 | 0xd393... | Pequeño | 45% | Yes a $0.003 masivo | Baja — lotería pura |
| Trader3 | 0x09f4... | Pequeño | 97%* | Yes a $0.002 masivo | Muy baja — WR engañoso |
| Found1 | 0x4174... | ~$221 | 75.8% | Mix mid-range | Media — seguir observando |

*97% WR engañoso: compra cientos de mercados imposibles a $0.002, alguno acierta.

**Patrones aprendidos de los traders:**
- ColdMath opera 08:00-09:07 UTC (justo después de actualización Open-Meteo)
- Los tres operan en la ventana 08:00-10:00 UTC — nuestro schedule es correcto
- Condición "exact" es la más apostada (más edge cuando el mercado está equivocado)
- London, Warsaw, Chicago, Lucknow, Paris son las ciudades con más actividad agregada

---

## Lo que hay que hacer en la próxima sesión de Opus

### Objetivo principal: Rediseñar find_traders.py y automatizar el pipeline

### Problema actual de find_traders.py:
1. **Criterio de selección débil** — aparecer en 2 de 40 mercados escaneados es muy ruidoso. Traders relevantes pueden no estar en esos mercados concretos.
2. **Bankroll calculado imprecisamente** — `initialValue` de posiciones activas ≠ balance real de wallet.
3. **Win rate poco fiable** — endpoint `closed=true` no está documentado, puede cambiar.
4. **Sin usar `pseudonym`** — el campo está disponible en `/trades` y permite identificar traders con nombre público.
5. **Descubrimiento reactivo** — escanea mercados aleatorios en vez de partir de fuentes de alta calidad (leaderboard, mercados de mayor volumen por ciudad).

### Lo que Opus debe diseñar:
1. **Estrategia de descubrimiento más inteligente:** partir del leaderboard de temperatura si existe, o escanear todos los mercados de temperatura (no solo 40) agrupando por ciudad, y rankear traders por frecuencia real en el universo completo.
2. **Clasificador de traders:** categorizar automáticamente por estrategia (lotería, mid-range, high-confidence) basándose en distribución de precios histórica, no solo snapshot actual.
3. **Automatización en Railway:** cron semanal para `find_traders`, diario para `trader_analyzer`, con resultados accesibles vía Telegram (`/traders` comando nuevo).
4. **Integración con bot.py:** cuando `trader_analyzer` detecte consenso entre traders mid-range en un mercado que el bot no tiene, registrarlo en el decision log como señal adicional.

### Archivos que Pablo adjuntará:
- `bot.py` (v8)
- `find_traders.py`
- `trader_analyzer.py`
- `traders_db.json`
- `trader_history.json` (con las entradas acumuladas hasta entonces)

---

## Hoja de ruta de mejoras

### Fase 1 — Validar y reparar (en curso)
- [ ] Confirmar que v8 encuentra oportunidades (ciclo 16:00 UTC del 22 marzo)
- [ ] Parsear mercados de rangos "46-47°F" (+30% mercados)
- [ ] Medir fill rate (¿cuántas órdenes se llenan vs expiran?)
- [ ] Calibrar sigma con datos reales

### Fase 2 — Pipeline de inteligencia (próxima sesión Opus)
- [ ] Rediseñar find_traders.py con criterios más sólidos
- [ ] Automatizar pipeline en Railway
- [ ] Integrar señales de consenso en decision log del bot
- [ ] Comando /traders en Telegram

### Fase 3 — Más inteligencia meteorológica
- [ ] Múltiples fuentes meteorológicas (GFS, ECMWF)
- [ ] Sigma dinámica por ciudad y patrón meteorológico
- [ ] Backtest con previsiones históricas

### Fase 4 — Escalar
- [ ] Subir bankroll a $100 cuando datos confirmen rentabilidad

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación real: diferencias 0.5-2°C incluso con coords de aeropuerto.
2. Modelo simplificado: sigma fija por días, no considera microclima.
3. Backtest optimista: usa datos reales, no previsiones históricas.
4. Regex no cubre rangos como "46-47°F" — esos mercados se pierden.
5. Sin precios históricos de Polymarket: backtest solo mide dirección.

---

## Recordatorios importantes

**Ver qué hizo el bot:** Telegram → 📓 Log (resumen) o Railway → Logs (completo)

**Activar modo real permanente:** railway.app → proyecto → Variables → `DRY_RUN=false`

**Push a GitHub:**
```
cd C:\Projects\polymarket-bot
git add .
git commit -m "descripción"
git push
```
