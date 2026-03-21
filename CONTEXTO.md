# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 6)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 10%, apuesta en la dirección correcta. Es arbitraje de información: mejor dato = mejor precio = ganancia.

**Bankroll:** $15 de prueba (objetivo: $100 cuando validemos que el sistema gana). Los $15 son para probar integración y validar la estrategia antes de escalar.

**Modelo de Claude recomendado:** Sesiones de coding puro pueden ser Sonnet. Revisiones de arquitectura o estrategia, Opus.

---

## Progreso: ~90%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto, 19 ciudades)
- [x] Lectura de mercados de Polymarket (Gamma API, tags, parseo regex)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Half-Kelly + presupuesto global)
- [x] Backtest básico (91.4% precisión, 116 mercados)
- [x] Git/GitHub
- [x] pip + librerías externas (py-clob-client, web3, eth-account, etc.)
- [x] Autenticación con Polymarket (Magic wallet, firma EIP-712, credenciales L2)
- [x] Ejecución real de órdenes (DRY_RUN flag, GTC limit orders)
- [x] Logging a archivo trades.log con timestamps
- [x] Fix bug clobTokenIds (json.loads)
- [x] Fix bug SELL→BUY para tokens NO
- [x] Filtro mercados del día actual (MIN_DAYS_AHEAD=1)
- [x] Fix MIN_BET=$1.00 (límite real Polymarket)
- [x] Fix mínimo 5 shares por orden (límite real Polymarket)
- [x] Primera orden real ejecutada (2 órdenes vivas en Polymarket)
- [x] Filtro de precio 8¢–92¢ (evitar loterías y near-certainties)
- [x] Agresividad en precio (+2¢ para mejorar llenado)
- [x] Check de órdenes abiertas (no duplicar posiciones)
- [x] Limpieza de órdenes stale (cancelar si > 8 horas)
- [x] Exposición total subida a 40% (más diversificación)
- [x] Logging limpio (nivel INFO, sin ruido HTTP)
- [x] DRY_RUN y BANKROLL leídos de variables de entorno
- [x] requirements.txt creado
- [x] Scheduler integrado (while True + time.sleep, cada 6 horas)
- [x] Despliegue en Railway (bot corriendo 24/7 en la nube)
- [x] Alertas Telegram (arranque, órdenes reales, errores)
- [x] Fix load_dotenv() al inicio del archivo
- [ ] Comandos Telegram interactivos (/estado, /ordenes, etc.)
- [ ] Validación real: correr unos días con $15 y ver resultados
- [ ] Revisión estratégica con Opus (Sesión 7)
- [ ] Activar DRY_RUN=false y operar con los $15 reales
- [ ] Escalar a $100 bankroll (solo si los datos confirman que gana)
- [ ] Mejoras del modelo (múltiples fuentes, calibración)

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
- **Bug encontrado:** `clobTokenIds` viene como string JSON → fix con json.loads()
- **Descubrimiento:** mercados del día actual sin order book

### Sesión 4 (21 marzo 2026) — Modelo: Sonnet
- `bot.py` v2: autenticación integrada, ejecución real, logging, todos los fixes
- **Bugs corregidos:** clobTokenIds, SELL→BUY, MIN_DAYS_AHEAD, MIN_BET, mínimo 5 shares
- **Límites reales de Polymarket descubiertos:** $1 mínimo, 5 shares mínimo
- **Primera ejecución real:** 2 órdenes vivas (Shanghai YES 16°C, Wellington YES 18°C)

### Sesión 5 (21 marzo 2026) — Modelo: Opus
- **Revisión estratégica completa** — análisis de la economía del bankroll
- **bot.py v3** con 4 mejoras clave:
  1. Filtro de precio 8¢–92¢
  2. Agresividad en precio +2¢
  3. Check de duplicados
  4. Limpieza de órdenes stale
- **Exposición total** subida de 30% a 40%
- **Decisión estratégica:** NO escalar a $100 todavía

### Sesión 6 (21 marzo 2026) — Modelo: Sonnet
- **requirements.txt** creado (5 librerías clave)
- **DRY_RUN y BANKROLL** movidos a variables de entorno (Railway-friendly)
- **bot.py v4:** función main() + scheduler while True (Railway no crashea)
- **Despliegue en Railway:** bot corriendo 24/7, estado Online
- **Bot de Telegram creado:** @polymarket_pablo_bot
- **bot.py v5:** alertas Telegram integradas
  - 🤖 Alerta de arranque (siempre)
  - ✅/❌ Alerta por orden ejecutada (solo modo real)
  - 📊 Resumen de ciclo (solo modo real)
  - ❌ Alerta de error grave
- **Bug encontrado y corregido:** load_dotenv() estaba dentro de setup_client(), las variables de Telegram se leían antes — fix: mover load_dotenv() al inicio del archivo
- **Telegram verificado:** mensaje de prueba recibido en móvil OK
- **Push final:** Railway actualizado con v5

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Ejecución principal:** `python bot.py` desde cmd en la carpeta del proyecto.
**Producción:** Railway (enchanting-respect) — Online, ciclo cada 6h

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v5 — scheduler + Telegram + todas las mejoras |
| `requirements.txt` | Librerías para Railway (5 líneas) |
| `edge_detector.py` | Detección de edge (versión standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `polymarket_explore.py` | Explorador de mercados por tags |
| `weather_forecast.py` | Previsión multi-ciudad |
| `wellington_forecast.py` | Script original Sesión 1 |
| `.env` | Claves privadas — PK, FUNDER, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (NO en git) |
| `.gitignore` | Protege `.env` y otros archivos sensibles |
| `trades.log` | Registro de todas las ejecuciones con timestamps |

### Variables de entorno (Railway + .env local):
```
PK=...                    # Clave privada wallet
FUNDER=...                # Dirección funder
DRY_RUN=true              # true = sin órdenes reales / false = modo real
BANKROLL=15.00            # Bankroll activo
INTERVALO_HORAS=6         # Horas entre ejecuciones (opcional, default 6)
TELEGRAM_TOKEN=...        # Token del bot @polymarket_pablo_bot
TELEGRAM_CHAT_ID=495704420
```

### Configuración actual en bot.py v5:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = 10.0
MIN_BET = 1.00
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.40
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
MIN_DAYS_AHEAD = 1
MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
INTERVALO_HORAS = float(os.getenv("INTERVALO_HORAS", "6"))
```

### Arquitectura v5:
```
SCHEDULER (while True, cada 6h)
  ↓
0. Limpiar órdenes stale (> 8 horas)
1. Polymarket (Gamma API, tag_id=103040) → mercados activos
2. Filtro precio (8¢–92¢) + parseo regex + token IDs
3. Open-Meteo (coords aeropuerto) → previsión temp_max
4. Modelo probabilidad (normal + redondeo) → edge vs precio mercado
5. Check duplicados + Kelly (half-kelly + 5% max + 40% total)
6. CLOB API (BUY, precio mercado + 2¢ agresividad)
7. Verificación + logging + alerta Telegram
  ↓
Dormir INTERVALO_HORAS → repetir
```

### Alertas Telegram implementadas:
- 🤖 **Arranque:** cada vez que el proceso arranca (Railway redeploy, reinicio)
- ✅/❌ **Orden ejecutada:** detalle completo de cada orden (solo modo real)
- 📊 **Ciclo completado:** resumen cuando hay órdenes (solo modo real)
- ❌ **Error grave:** si main() lanza una excepción no controlada

### Estaciones de resolución mapeadas (19 ciudades):
Seoul (RKSI), London (EGLC), Tel Aviv (LLBG), Shanghai (ZSPD), Tokyo (RJTT), NYC (KLGA), Beijing (ZBAA), Hong Kong (VHHH), Singapore (WSSS), Toronto (CYYZ), Chicago (KORD), Wellington (NZWN), Munich (EDDM), Warsaw (EPWA), Ankara (LTAC), Atlanta (KATL), Shenzhen (ZGSZ), Paris (LFPG), Buenos Aires (SAEZ).

---

## Plan para Sesión 7 — Revisión con Opus + Activar $15 reales

### Objetivo principal:
Revisar el bot completo con Opus, identificar mejoras, y dejarlo operativo en modo real antes de dormir.

### Agenda propuesta:
1. **Revisar órdenes de sesión 4** — Shanghai YES 16°C y Wellington YES 18°C (March 22). ¿Se llenaron? ¿Acertaron?
2. **Revisión estratégica con Opus** — leer bot.py v5 completo y proponer mejoras
3. **Comandos Telegram interactivos** — `/estado`, `/ordenes`, `/siguiente` para consultar el bot desde el móvil sin entrar a Railway
4. **Activar DRY_RUN=false** — cambiar en Railway y dejar corriendo con los $15 reales

### Comandos Telegram planificados:
| Comando | Respuesta del bot |
|---------|-------------------|
| `/estado` | Bankroll, modo, próxima ejecución, órdenes abiertas |
| `/ordenes` | Lista de órdenes abiertas con ciudad, lado, precio |
| `/siguiente` | Cuánto tiempo falta para el próximo ciclo |
| `/forzar` | Ejecuta un ciclo ahora sin esperar |

---

## Problemas conocidos / pendientes

### Prioritarios:
1. **Validar con $15 reales** — activar DRY_RUN=false en Railway
2. **Comandos Telegram** — el bot solo envía, no recibe comandos todavía
3. **Revisar órdenes vivas** — Shanghai y Wellington del 22 de marzo

### Secundarios:
4. **Escalar a $100** — solo cuando tengamos datos de que el sistema gana
5. **Mejoras del modelo** — múltiples fuentes meteorológicas, calibración

### Bugs conocidos resueltos:
- `load_dotenv()` debe estar al inicio del archivo (antes de os.getenv)
- `created_at` como int (Unix timestamp) — resuelto con isinstance()
- `clobTokenIds` como string JSON — resuelto con json.loads()
- SELL vs BUY para tokens NO — resuelto en v2

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación real: diferencias 0.5-2°C incluso con coords de aeropuerto.
2. Modelo simplificado: sigma fija por días, no considera microclima.
3. Backtest optimista: usa datos reales, no previsiones históricas.
4. 58 preguntas no parseables: regex no cubre rangos como "46-47°F".
5. Sin precios históricos de Polymarket: backtest solo mide dirección.

---

## Mi nivel técnico

- **Programación:** Principiante avanzado. Funciones, regex, distribuciones, APIs, OOP básica, sets.
- **Terminal:** Cómodo con cmd, Git básico (add → commit → push).
- **Python:** urllib, json, re, math, datetime, dotenv, logging, py-clob-client, isinstance(), time.sleep, while True, variables de entorno.
- **Git:** Flujo básico consolidado.
- **Crypto/Blockchain:** Básico funcional. Polygon, signature_type=1, EIP-712, token IDs.
- **Polymarket:** Comprende shares, órdenes límite GTC, resolución binaria, order book, llenado.
- **Railway:** Sabe desplegar desde GitHub, configurar variables de entorno, leer logs.
- **Telegram Bot API:** Sabe crear bots con BotFather, obtener chat_id, enviar mensajes via HTTP.
- **Estrategia:** Entiende Kelly, edge, agresividad en precio, por qué no escalar antes de validar.
- **Pendiente:** Comandos Telegram bidireccionales (polling), estrategias avanzadas de llenado.
- **Workflow de sesiones:** No edita código manualmente — Claude siempre entrega archivos completos.

---

## Recordatorios importantes

**Activar órdenes reales en Railway:**
railway.app → proyecto polymarket-bot → Variables → cambiar `DRY_RUN` de `true` a `false`. Sin push, sin tocar código.

**Push a GitHub (después de cambios en local):**
```
cd C:\Projects\polymarket-bot
git add .
git commit -m "descripción del cambio"
git push
```
