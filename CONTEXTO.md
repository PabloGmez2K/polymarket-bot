# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 3)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Modelo de Claude recomendado:** Sonnet es suficiente para la mayoría de sesiones (coding, debugging, configuración, integración). Usar Opus solo si la sesión requiere diseño de arquitectura nueva, razonamiento avanzado sobre probabilidades/modelos, o investigación compleja. Las Sesiones 2 y 3 se hicieron con Opus — la 3 habría funcionado igual con Sonnet (fue todo configuración e instalación).

---

## Progreso: ~55%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto)
- [x] Lectura de mercados de Polymarket (Gamma API, tags)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Kelly + presupuesto global)
- [x] Backtest básico (91.4% precisión, 116 mercados)
- [x] Git/GitHub
- [x] pip + librerías externas (py-clob-client, web3, eth-account, etc.)
- [x] Autenticación con Polymarket (Magic wallet, firma EIP-712, credenciales L2)
- [x] Primera orden de prueba (colocar + verificar + cancelar — ciclo completo)
- [ ] Primera orden real ejecutada (compra que se llene)
- [ ] Integrar ejecución en bot.py (que el plan se ejecute automáticamente)
- [ ] Ejecución programada (scheduler cada X horas)
- [ ] Despliegue en Railway (nube 24/7)
- [ ] Alertas (Telegram/email)
- [ ] Mejoras del modelo (múltiples fuentes, calibración)

---

## Historial de sesiones

### Sesión 1 (21 marzo 2026)
- Primera llamada a API (Open-Meteo, previsión de Wellington)
- Aprendí: terminal cmd, APIs REST, JSON, por qué no hacer doble clic en .py

### Sesión 2 (21 marzo 2026) — Modelo usado: Opus
- `weather_forecast.py` — Multi-ciudad, funciones, más variables
- `polymarket_explore.py` — Explorador con tags verificados
- `edge_detector.py` v3 — Coords de aeropuerto, modelo normal, redondeo
- `backtest.py` — Validación: 91.4% precisión sobre 116 mercados
- `bankroll.py` — Criterio de Kelly, simulación
- `bot.py` — Sistema completo con presupuesto global (30%)
- Git instalado, repo en GitHub
- **Descubrimiento clave:** coordenadas centro de ciudad vs aeropuerto pueden diferir 1-6°C (Seoul, Shanghai). Habríamos perdido dinero sin la corrección.

### Sesión 3 (21 marzo 2026) — Modelo usado: Opus
- Primer uso de pip — instalado `py-clob-client` v0.34.6 (45 dependencias, incluye web3, eth-account, httpx)
- Conexión al CLOB API sin autenticación — lectura de order books reales
- **Bug encontrado y resuelto:** `clobTokenIds` viene como string JSON desde la Gamma API, no como lista Python. `tokens[0]` devolvía el carácter `[` en vez del token ID. Fix: `json.loads()` si es string.
- Archivo `.env` con `PK` y `FUNDER` — protegido en `.gitignore`
- Autenticación completa: firma EIP-712, credenciales L2 (API key + secret + passphrase)
- Primera orden colocada y cancelada con éxito: BUY 10 shares a $0.01 en mercado de Londres, status LIVE, cancelación limpia.
- **Descubrimiento clave:** Los mercados del día actual (ej: March 21) no tienen order book activo porque ya están a punto de resolver. El bot necesita filtrar mercados futuros.
- Cuenta Polymarket: email pablogomez.eu@gmail.com, Magic wallet (signature_type=1), $14.99 USDC depositados desde Binance via BSC.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Ejecución principal:** `python bot.py` desde cmd en la carpeta del proyecto.

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal — genera plan de operaciones (solo análisis, aún no ejecuta) |
| `edge_detector.py` | Detección de edge (versión standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `polymarket_explore.py` | Explorador de mercados por tags |
| `weather_forecast.py` | Previsión multi-ciudad |
| `wellington_forecast.py` | Script original Sesión 1 |
| `test_connection.py` | Tests de conexión CLOB (diagnóstico, puede borrarse) |
| `test_order.py` | Test de orden + cancelación (diagnóstico, puede borrarse) |
| `.env` | Claves privadas — PK y FUNDER (NO en git) |
| `.gitignore` | Protege `.env` y otros archivos sensibles |

### Configuración actual en bot.py:
```python
BANKROLL = 100.00      # Nota: bankroll real actual es ~$15 USDC
MIN_EDGE = 10.0
MIN_BET = 0.50
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.30
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
```

### Configuración de autenticación (para integrar en bot.py):
```python
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

load_dotenv()
client = ClobClient(
    "https://clob.polymarket.com",
    key=os.getenv("PK"),
    chain_id=137,              # Polygon
    signature_type=1,          # Magic wallet (email)
    funder=os.getenv("FUNDER")
)
client.set_api_creds(client.create_or_derive_api_creds())
```

### Tipos de orden disponibles:
```python
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Orden límite (GTC = Good Till Cancelled)
order = OrderArgs(token_id="...", price=0.50, size=10.0, side=BUY)
signed = client.create_order(order)
resp = client.post_order(signed, OrderType.GTC)

# Cancelar
client.cancel(order_id)
```

### Arquitectura:
```
Polymarket (Gamma API, tag_id=103040)
    ↓ mercados activos de Daily Temperature
Parseo (regex)
    ↓ ciudad, temperatura, condición, fecha
Open-Meteo (coords de aeropuerto)
    ↓ previsión temp_max para esa fecha
Modelo de probabilidad (normal + redondeo a °C enteros)
    ↓ probabilidad estimada vs precio de mercado
Kelly (medio kelly + tope 5% + presupuesto global 30%)
    ↓ cantidad a apostar
CLOB API (autenticado, signature_type=1)     ← NUEVO
    ↓ colocar órdenes límite
Verificación + logging
    ↓ confirmar ejecución
```

### Bug conocido pendiente de corregir en bot.py:
`clobTokenIds` de la Gamma API viene como string JSON. Hay que hacer `json.loads()` antes de usar. Actualmente bot.py probablemente tiene este bug (no usa clobTokenIds aún, pero lo necesitará cuando integre ejecución).

### Estaciones de resolución mapeadas (19 ciudades):
Seoul (RKSI), London (EGLC), Tel Aviv (LLBG), Shanghai (ZSPD), Tokyo (RJTT), NYC (KLGA), Beijing (ZBAA), Hong Kong (VHHH), Singapore (WSSS), Toronto (CYYZ), Chicago (KORD), Wellington (NZWN), Munich (EDDM), Warsaw (EPWA), Ankara (LTAC), Atlanta (KATL), Shenzhen (ZGSZ), Paris (LFPG), Buenos Aires (SAEZ).

### Tags de Polymarket verificados:
Daily Temperature (103040), Weather (84), Climate & Weather (1474), Precipitation (103041), Hurricanes (85), Global Temp (832), Natural Disasters (496).

---

## Limitaciones conocidas

1. **Open-Meteo vs estación real:** Diferencias de 0.5-2°C incluso con coords de aeropuerto.
2. **Modelo simplificado:** Sigma fija por días. No considera microclima.
3. **Backtest optimista:** Usa datos reales, no previsiones históricas.
4. **58 preguntas no parseables:** Regex no cubre rangos como "46-47°F".
5. **Sin precios históricos de Polymarket:** Backtest solo mide dirección, no rentabilidad.
6. **Mercados del día actual sin order book:** Los mercados que van a resolver hoy no tienen order book activo — el bot debe filtrarlos.

---

## Mi nivel técnico

- **Programación:** Principiante avanzado. Funciones, regex, distribuciones, APIs. Primer proyecto real.
- **Terminal:** Cómodo con cmd, Git básico.
- **Python:** urllib, json, re, math, datetime + ahora pip, dotenv, py-clob-client.
- **Git:** Flujo básico add → commit → push.
- **Crypto/Blockchain:** Básico. Sabe que Polygon = chain_id 137, que signature_type=1 es Magic wallet, que hay que firmar con clave privada. No necesita entender los detalles de EIP-712.
- **Pendiente aprender:** VS Code, Railway, estrategias de ejecución (market vs limit orders, slippage).

---

## Siguiente paso

**Sesión 4 — Primera orden real + integración en bot.py:**
1. Ejecutar una orden real pequeña ($0.50-$1) que se llene — para ver el flujo de compra completo
2. Integrar la autenticación y ejecución de órdenes en bot.py — que el plan de operaciones se ejecute automáticamente
3. Añadir logging (registro de operaciones ejecutadas)
4. Corregir bug de clobTokenIds en bot.py
5. Hacer commit de todo al repo
