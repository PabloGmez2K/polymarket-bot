# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 7)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 10%, apuesta en la dirección correcta. Es arbitraje de información: mejor dato = mejor precio = ganancia.

**Bankroll:** $15 de prueba (objetivo: $100 cuando validemos que el sistema gana).

**Modelo de Claude recomendado:** Sesiones de coding puro pueden ser Sonnet. Revisiones de arquitectura o estrategia, Opus.

---

## Progreso: ~95%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto, 19 ciudades)
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
- [ ] Validar resultados: correr varios días y analizar decisions.log
- [ ] Optimizar estrategia basándose en datos reales
- [ ] Escalar a $100 (solo si los datos confirman que gana)
- [ ] Mejoras del modelo (múltiples fuentes, calibración sigma)

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
- **Scheduler estratégico:** de "cada 6h" a horas UTC fijas (08, 16, 23)
  - Open-Meteo actualiza modelos cada 6h (00, 06, 12, 18 UTC)
  - Bot ejecuta después de cada actualización + cuando EEUU tiene liquidez
- **Telegram bidireccional:** threading + polling + botones inline
  - 📊 Estado: modo, bankroll, próxima ejecución, último ciclo
  - 💰 Cartera: posiciones reales con PnL (Data API)
  - 📋 Órdenes: pendientes enriquecidas con pregunta del mercado
  - 📓 Log: resumen del último ciclo de decisiones
  - 🚀 Forzar: ejecuta ciclo inmediato
  - ⚡ Modo: toggle DRY_RUN↔REAL con doble confirmación
- **Decision log:** archivo decisions.log con análisis completo de cada ciclo
  - Qué mercados encontró y cuántos filtró (y por qué)
  - Edge calculado para cada mercado con previsión vs precio
  - Por qué descartó cada oportunidad (edge bajo, duplicado, Kelly insuficiente)
  - Qué órdenes colocó y resultado
- **known_tokens cache:** fix para que /ordenes muestre la pregunta del mercado
- **Data API:** cartera real desde data-api.polymarket.com/positions
- **MODO REAL activado** desde Telegram a las 22:52 UTC
- **Conceptos nuevos aprendidos:** threading, threading.Event, inline keyboard Telegram, long polling, daemon threads

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, MODO REAL, schedule 08/16/23 UTC

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v7 — scheduler + Telegram + decision log |
| `requirements.txt` | Librerías para Railway |
| `decisions.log` | **NUEVO** — Log detallado de cada decisión del bot |
| `trades.log` | Registro técnico de operaciones |
| `edge_detector.py` | Detección de edge (standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `polymarket_explore.py` | Explorador de mercados |
| `weather_forecast.py` | Previsión multi-ciudad |
| `.env` | Claves (NO en git) |

### Variables de entorno (Railway + .env):
```
PK=...
FUNDER=...
DRY_RUN=true              # Actualmente overrideado a false desde Telegram
BANKROLL=15.00
SCHEDULE_HOURS_UTC=8,16,23
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=495704420
```

### Configuración en bot.py v7:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"  # Mutable desde Telegram
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = 10.0
MIN_BET = 1.00
MAX_BET_PCT = 0.05        # 5% max por operación
MAX_EXPOSURE_PCT = 0.40   # 40% exposición total
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
MIN_DAYS_AHEAD = 1
MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
SCHEDULE_HOURS_UTC = [8, 16, 23]
```

### Arquitectura v7:
```
HILO 1: TELEGRAM POLLING (24/7)
  ↓ Escucha botones/comandos
  ↓ Lee bot_state para responder
  ↓ force_event.set() si /forzar

HILO 2: SCHEDULER (horas UTC fijas)
  ↓
  0. Limpiar stale (>8h)
  1. Gamma API → mercados activos
  2. Parseo + filtros (precio, fecha, liquidez)
  3. Open-Meteo → previsiones
  4. Modelo probabilidad → edge vs mercado
  5. Kelly + presupuesto → selección
  6. CLOB API → órdenes + Telegram alert
  7. Decision log → decisions.log + bot_state
  ↓
  Esperar próxima hora UTC (interruptible por /forzar)
```

### APIs utilizadas:
| API | URL | Función |
|-----|-----|---------|
| Gamma API | gamma-api.polymarket.com | Mercados, preguntas, precios |
| Data API | data-api.polymarket.com | Posiciones del usuario, PnL |
| CLOB API | clob.polymarket.com | Órdenes, autenticación |
| Open-Meteo | api.open-meteo.com | Previsiones meteorológicas |
| Telegram | api.telegram.org | Dashboard + alertas |

---

## Estado de las primeras operaciones

### Posición activa:
- **Shanghai YES 16°C** (March 22): 16.9 shares @ $0.04, valor actual ~$0.54, PnL: -$0.13 (-20%)

### Orden pendiente:
- **Wellington YES 18°C** (March 22): Buy @ $0.05, 14 shares, ~5h esperando llenado

### Balance Polymarket:
- Cartera total: ~$14.91
- Disponible: ~$14.32
- PnL total: -$0.41

**Nota:** Las primeras órdenes fueron de la sesión 4 (pre-optimización). El bot v7 es significativamente mejor — el resultado de estas órdenes iniciales no es representativo.

---

## Plan para Sesión 8 — Análisis de datos + Optimización

### Objetivo: Aprender de los datos reales y mejorar la estrategia

### Paso 1: Revisar decisions.log
- Leer el log de la noche (ciclos 23:00 y 08:00)
- ¿Cuántas oportunidades encontró? ¿Colocó órdenes?
- ¿Los edges eran reales o el modelo está mal calibrado?

### Paso 2: Revisar resultados en Polymarket
- ¿Se llenaron las órdenes?
- ¿Los mercados que apostamos se resolvieron correctamente?
- Comparar temperatura real vs previsión del bot

### Paso 3: Mejoras potenciales (priorizar según datos)
1. **Calibración de sigma** — ¿La incertidumbre de 1.0°C para 1 día es correcta?
2. **Múltiples fuentes** — Comparar Open-Meteo con otra fuente
3. **Historial de edges** — ¿Los edges que detectamos son consistentes?
4. **Fill rate** — ¿Cuántas órdenes se llenan vs cuántas expiran?
5. **Ajuste de agresividad** — ¿+2¢ es suficiente para llenarse?
6. **Parseo de rangos** — Capturar mercados "46-47°F" que ahora se pierden

### Workflow continuo:
```
1. Bot corre 24/7 → genera decisions.log
2. Pablo revisa datos → identifica patrones
3. Sesión con Claude → implementa mejoras
4. Push → Railway redeploy → más datos
5. Repetir hasta que el bot sea consistentemente rentable
```

---

## Problemas conocidos / pendientes

### Observados:
1. **DRY_RUN desde Telegram es temporal** — Si Railway reinicia, vuelve al valor de la variable. Para permanente: cambiar en Railway → Variables.
2. **85 mercados no parseables** — regex no cubre rangos "46-47°F"
3. **131 fuera de fecha** — muchos mercados son para hoy (MIN_DAYS_AHEAD=1 los excluye)
4. **Shanghai -20%** — primera operación, pre-optimización, no representativa

### Resueltos en v7:
- Órdenes sin enriquecer → known_tokens cache
- Cartera 404 → Data API correcta
- Scheduler fijo cada 6h → horas UTC estratégicas
- Bot solo envía → Telegram bidireccional con botones

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación real: diferencias 0.5-2°C incluso con coords de aeropuerto.
2. Modelo simplificado: sigma fija por días, no considera microclima.
3. Backtest optimista: usa datos reales, no previsiones históricas.
4. 85 preguntas no parseables: regex no cubre rangos como "46-47°F".
5. Sin precios históricos de Polymarket: backtest solo mide dirección.

---

## Mi nivel técnico

- **Programación:** Intermedio. Funciones, regex, distribuciones, APIs, OOP básica, sets, threading, eventos.
- **Terminal:** Cómodo con cmd, Git básico.
- **Python:** urllib, json, re, math, datetime, dotenv, logging, threading, py-clob-client, time.sleep.
- **Conceptos nuevos (Sesión 7):** threading, threading.Event, daemon threads, long polling, inline keyboard, callback_query, múltiples loggers.
- **Git:** Flujo básico consolidado.
- **Polymarket:** Comprende shares, órdenes GTC, resolución, order book, Data API, Gamma API, CLOB API.
- **Railway:** Despliegue, variables de entorno, logs.
- **Telegram:** Bot bidireccional con botones inline y polling.
- **Estrategia:** Kelly, edge, agresividad, por qué validar antes de escalar.
- **Workflow:** Claude entrega archivos completos, Pablo hace push.

---

## Recordatorios importantes

**Activar órdenes reales (permanente):**
Railway → Variables → `DRY_RUN` = `false`

**Activar órdenes reales (temporal):**
Telegram → ⚡ Modo → Activar REAL

**Push a GitHub:**
```
cd C:\Projects\polymarket-bot
git add .
git commit -m "descripción"
git push
```

**Ver qué hizo el bot:**
Telegram → 📓 Log (resumen) o Railway → Logs (completo)
