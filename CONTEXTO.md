# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 4)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Bankroll objetivo:** $100 para empezar, con estrategia de bola de nieve si funciona. Los $15 actuales son solo para pruebas de integración.

**Modelo de Claude recomendado:** Sesión 5 debe ser con Opus — hay que revisar arquitectura, estrategia y parámetros completos para $100 de bankroll. Las sesiones de coding puro pueden ser Sonnet.

---

## Progreso: ~65%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto)
- [x] Lectura de mercados de Polymarket (Gamma API, tags)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Kelly + presupuesto global)
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
- [x] Primera orden real ejecutada ✅ (2 órdenes vivas en Polymarket)
- [ ] Revisión completa de estrategia y parámetros para $100 bankroll
- [ ] Gestión de órdenes abiertas (no duplicar si el bot corre 2 veces)
- [ ] Ejecución programada (scheduler cada X horas)
- [ ] Despliegue en Railway (nube 24/7)
- [ ] Alertas (Telegram/email)
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
- **Bugs corregidos:**
  - `clobTokenIds` string → json.loads()
  - SELL→BUY para tokens NO (comprar NO = BUY token_id_no)
  - Filtro MIN_DAYS_AHEAD=1 (excluir mercados de hoy)
  - MIN_BET=$0.50→$1.00 (límite real Polymarket)
  - Mínimo 5 shares por orden (límite real Polymarket)
- **Límites reales de Polymarket descubiertos:**
  - Importe mínimo por orden: $1.00
  - Shares mínimas por orden: 5
  - "Marketable BUY" (orden que se llenaría instantáneamente): mínimo $1
- **Primera ejecución real:** 2 órdenes vivas (6 intentadas, 4 fallaron por límites)
  - ✅ Shanghai YES 16°C March 22 — $0.67 — 17 shares a 4¢ — ID: `0x7d1e...`
  - ✅ Wellington YES 18°C March 22 — $0.70 — 14 shares a 5¢ — ID: `0x7139...`
- **Aprendizajes sobre Polymarket:**
  - Un share = billete que vale $1 si aciertas, $0 si fallas
  - "0/17" = 0 shares llenadas de 17 pedidas (orden límite esperando contraparte)
  - No hay SL/TP clásico — los mercados resuelven binariamente a $1 o $0
  - La alternativa al SL es cancelar órdenes abiertas si cambia la previsión

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Ejecución principal:** `python bot.py` desde cmd en la carpeta del proyecto.

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v2 — análisis + ejecución real con DRY_RUN flag |
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

### Configuración actual en bot.py:
```python
DRY_RUN = False          # False = órdenes reales activas
BANKROLL = 15.00         # Bankroll de prueba (objetivo: $100)
MIN_EDGE = 10.0
MIN_BET = 1.00           # Límite real Polymarket
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.30
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
MIN_DAYS_AHEAD = 1
```

### Lógica de shares mínimas en calculate_position():
```python
# Si Kelly calcula menos de 5 shares, escalar el importe
if shares < 5.0:
    amount_for_5_shares = round(5.0 * market_price, 2)
    if amount_for_5_shares > bankroll * MAX_BET_PCT:
        return None  # No se puede llegar a 5 shares sin superar tope
    if amount_for_5_shares < MIN_BET:
        return None
    amount = amount_for_5_shares
    shares = 5.0
```

### Arquitectura:
```
Polymarket (Gamma API, tag_id=103040)
    ↓ mercados activos Daily Temperature (días futuros únicamente)
Parseo (regex) + extracción de token IDs (json.loads fix)
    ↓ ciudad, temperatura, condición, fecha, token_id_yes, token_id_no
Open-Meteo (coords de aeropuerto)
    ↓ previsión temp_max para esa fecha
Modelo de probabilidad (normal + redondeo a °C enteros)
    ↓ probabilidad estimada vs precio de mercado
Kelly (medio kelly + tope 5% + presupuesto global 30%)
    + validación mínimo $1 y mínimo 5 shares
    ↓ cantidad a apostar
CLOB API (autenticado, signature_type=1, BUY siempre)
    ↓ órdenes límite GTC
Verificación + logging a trades.log
```

### Estaciones de resolución mapeadas (19 ciudades):
Seoul (RKSI), London (EGLC), Tel Aviv (LLBG), Shanghai (ZSPD), Tokyo (RJTT), NYC (KLGA), Beijing (ZBAA), Hong Kong (VHHH), Singapore (WSSS), Toronto (CYYZ), Chicago (KORD), Wellington (NZWN), Munich (EDDM), Warsaw (EPWA), Ankara (LTAC), Atlanta (KATL), Shenzhen (ZGSZ), Paris (LFPG), Buenos Aires (SAEZ).

---

## Problemas conocidos / pendientes para Sesión 5

### Estratégicos (revisar con Opus):
1. **Parámetros para $100 bankroll** — Con $100, MIN_BET=$1, MAX_BET_PCT=5% → $5 por operación. ¿Es suficiente? ¿Cómo afecta el mínimo de 5 shares a la estrategia?
2. **Mercados YES muy baratos (2-5¢)** — Requieren muchas shares, alto riesgo de que no se llenen. ¿Vale la pena operarlos?
3. **Órdenes que no se llenan** — Las órdenes límite pueden quedarse esperando indefinidamente. ¿Cuándo cancelar? ¿Poner precio ligeramente por encima del mercado para asegurar llenado?
4. **Sin gestión de órdenes abiertas** — Si el bot corre dos veces, puede duplicar órdenes en el mismo mercado.
5. **SL/TP conceptual** — No es SL/TP clásico, pero sí hay que decidir si cancelar órdenes cuando la previsión cambia significativamente.
6. **Backtest optimista** — Validado con datos reales, no con previsiones históricas. La precisión real puede ser menor.

### Técnicos (para implementar):
7. **Función check_open_orders()** — Consultar órdenes activas y no duplicar posiciones.
8. **Scheduler** — Ejecutar bot cada X horas automáticamente.
9. **Railway deployment** — Bot 24/7 en la nube.
10. **Alertas** — Telegram o email cuando se ejecuta una orden o hay un error.

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación real: diferencias 0.5-2°C incluso con coords de aeropuerto.
2. Modelo simplificado: sigma fija por días, no considera microclima.
3. Backtest optimista: usa datos reales, no previsiones históricas.
4. 58 preguntas no parseables: regex no cubre rangos como "46-47°F".
5. Sin precios históricos de Polymarket: backtest solo mide dirección.

---

## Mi nivel técnico

- **Programación:** Principiante avanzado. Funciones, regex, distribuciones, APIs, OOP básica.
- **Terminal:** Cómodo con cmd, Git básico (add → commit → push).
- **Python:** urllib, json, re, math, datetime, dotenv, logging, py-clob-client.
- **Git:** Flujo básico consolidado.
- **Crypto/Blockchain:** Básico funcional. Polygon, signature_type=1, EIP-712, token IDs.
- **Polymarket:** Comprende shares, órdenes límite GTC, resolución binaria, order book.
- **Pendiente:** VS Code avanzado, Railway, estrategias de llenado de órdenes.
- **Workflow de sesiones:** No edita código manualmente — Claude siempre entrega archivos completos.
