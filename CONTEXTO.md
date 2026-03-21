# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 5)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 10%, apuesta en la dirección correcta. Es arbitraje de información: mejor dato = mejor precio = ganancia.

**Bankroll:** $15 de prueba (objetivo: $100 cuando validemos que el sistema gana). Los $15 son para probar integración y validar la estrategia antes de escalar.

**Modelo de Claude recomendado:** Sesiones de coding puro pueden ser Sonnet. Revisiones de arquitectura o estrategia, Opus.

---

## Progreso: ~70%

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
- [x] DRY_RUN=True por defecto (seguridad)
- [ ] Validación real: correr unos días con $15 y ver resultados
- [ ] Ejecución programada (scheduler cada X horas)
- [ ] Despliegue en Railway (nube 24/7)
- [ ] Alertas (Telegram/email)
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
  1. Filtro de precio 8¢–92¢ (42 mercados filtrados en primera corrida)
  2. Agresividad en precio +2¢ (para mejorar llenado de órdenes)
  3. Check de duplicados (consulta órdenes abiertas, no repite)
  4. Limpieza de órdenes stale (cancela si > 8 horas)
- **Exposición total** subida de 30% a 40% (más diversificación = menos riesgo)
- **Logging** cambiado de DEBUG a INFO (eliminado ruido HTTP ilegible)
- **DRY_RUN=True** por defecto (seguridad — yo lo cambio cuando quiero operar)
- **Bug encontrado y corregido:** `created_at` de Polymarket es Unix timestamp (int), no string ISO. Fix: isinstance() para detectar el tipo.
- **Decisión estratégica:** NO escalar a $100 todavía. Mantener $15 hasta validar que el sistema gana dinero real. Pablo propuso esto y es la decisión correcta.
- **Primera corrida v3:** 0 operaciones recomendadas (correcto — no había edge suficiente en ese momento). 330 mercados analizados, 42 filtrados por precio, 15 candidatos evaluados.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Ejecución principal:** `python bot.py` desde cmd en la carpeta del proyecto.

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v3 — análisis + ejecución con filtros inteligentes |
| `edge_detector.py` | Detección de edge (versión standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `polymarket_explore.py` | Explorador de mercados por tags |
| `weather_forecast.py` | Previsión multi-ciudad |
| `wellington_forecast.py` | Script original Sesión 1 |
| `test_connection.py` | Tests de conexión CLOB (puede borrarse) |
| `test_order.py` | Test de orden + cancelación (puede borrarse) |
| `.env` | Claves privadas — PK y FUNDER (NO en git) |
| `.gitignore` | Protege `.env` y otros archivos sensibles |
| `trades.log` | Registro de todas las ejecuciones con timestamps |

### Configuración actual en bot.py v3:
```python
DRY_RUN = True           # True por defecto — cambiar a False para órdenes reales
BANKROLL = 15.00         # Bankroll de prueba (objetivo: $100 cuando validemos)
MIN_EDGE = 10.0
MIN_BET = 1.00           # Límite real Polymarket
MAX_BET_PCT = 0.05       # 5% por operación
MAX_EXPOSURE_PCT = 0.40  # 40% total (subido desde 30% en v3)
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
MIN_DAYS_AHEAD = 1

# Nuevos en v3:
MIN_PRICE = 0.08         # Ignorar mercados < 8¢
MAX_PRICE = 0.92         # Ignorar mercados > 92¢
PRICE_AGGRESSION = 0.02  # Pagar +2¢ para mejorar llenado
ORDER_MAX_AGE_HOURS = 8  # Cancelar órdenes stale
```

### Arquitectura v3:
```
0. Limpiar órdenes stale (> 8 horas) → liberar presupuesto
1. Polymarket (Gamma API, tag_id=103040) → mercados activos
2. Filtro precio (8¢–92¢) + parseo regex + token IDs (json.loads fix)
3. Open-Meteo (coords aeropuerto) → previsión temp_max
4. Modelo probabilidad (normal + redondeo) → edge vs precio mercado
5. Check duplicados (consultar órdenes abiertas, no repetir)
6. Kelly (half-kelly + 5% max + 40% total) + mínimo $1 + mínimo 5 shares
7. CLOB API (BUY siempre, precio mercado + 2¢ agresividad)
8. Verificación + logging a trades.log
```

### Estaciones de resolución mapeadas (19 ciudades):
Seoul (RKSI), London (EGLC), Tel Aviv (LLBG), Shanghai (ZSPD), Tokyo (RJTT), NYC (KLGA), Beijing (ZBAA), Hong Kong (VHHH), Singapore (WSSS), Toronto (CYYZ), Chicago (KORD), Wellington (NZWN), Munich (EDDM), Warsaw (EPWA), Ankara (LTAC), Atlanta (KATL), Shenzhen (ZGSZ), Paris (LFPG), Buenos Aires (SAEZ).

---

## Problemas conocidos / pendientes para Sesión 6

### Prioritarios:
1. **Validar con datos reales** — Correr el bot varias veces con DRY_RUN=True y luego con órdenes reales. Ver si las órdenes se llenan con la agresividad de +2¢. Ver si las predicciones aciertan.
2. **2 órdenes vivas de sesión 4** — Shanghai YES 16°C y Wellington YES 18°C para March 22. Revisar si se llenaron y si el resultado fue correcto.
3. **Scheduler** — Ejecutar bot cada X horas automáticamente (probablemente cada 4-6 horas).
4. **Railway deployment** — Bot 24/7 en la nube.

### Secundarios:
5. **Alertas** — Telegram o email cuando se ejecuta una orden o hay un error.
6. **Escalar a $100** — Solo cuando tengamos datos de que el sistema gana.
7. **Mejoras del modelo** — Múltiples fuentes meteorológicas, calibración más fina.

### Bugs conocidos resueltos:
- `created_at` como int (Unix timestamp) — resuelto con isinstance() en v3
- `clobTokenIds` como string JSON — resuelto con json.loads() en v2
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
- **Python:** urllib, json, re, math, datetime, dotenv, logging, py-clob-client, isinstance().
- **Git:** Flujo básico consolidado.
- **Crypto/Blockchain:** Básico funcional. Polygon, signature_type=1, EIP-712, token IDs.
- **Polymarket:** Comprende shares, órdenes límite GTC, resolución binaria, order book, llenado.
- **Estrategia:** Entiende Kelly, edge, agresividad en precio, por qué no escalar antes de validar.
- **Pendiente:** VS Code avanzado, Railway, scheduler, estrategias avanzadas de llenado.
- **Workflow de sesiones:** No edita código manualmente — Claude siempre entrega archivos completos. Revisa DRY_RUN antes de ejecutar (buena práctica aprendida en sesión 5).
