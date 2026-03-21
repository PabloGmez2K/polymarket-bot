# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 21 de marzo de 2026 (Sesión 2)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Modelo de Claude recomendado:** Sonnet es suficiente para la mayoría de sesiones (coding, debugging, configuración). Usar Opus solo si la sesión requiere investigación compleja, diseño de arquitectura nueva, o razonamiento avanzado sobre probabilidades/modelos. La Sesión 2 se hizo entera con Opus y consumió ~90% del límite — habría funcionado igual con Sonnet.

---

## Progreso: ~40%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto)
- [x] Lectura de mercados de Polymarket (Gamma API, tags)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Kelly + presupuesto global)
- [x] Backtest básico (91.4% precisión, 116 mercados)
- [x] Git/GitHub
- [ ] Autenticación con Polymarket (wallet crypto, firma)
- [ ] Ejecución de órdenes (CLOB API)
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

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Ejecución principal:** `python bot.py` desde cmd en la carpeta del proyecto.

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal — genera plan de operaciones |
| `edge_detector.py` | Detección de edge (versión standalone) |
| `backtest.py` | Validación con mercados resueltos |
| `bankroll.py` | Gestión de riesgo + demo Kelly |
| `polymarket_explore.py` | Explorador de mercados por tags |
| `weather_forecast.py` | Previsión multi-ciudad |
| `wellington_forecast.py` | Script original Sesión 1 |

### Configuración actual en bot.py:
```python
BANKROLL = 100.00
MIN_EDGE = 10.0
MIN_BET = 0.50
MAX_BET_PCT = 0.05
MAX_EXPOSURE_PCT = 0.30
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 3
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
Plan de operaciones
    ↓ lista ordenada por EV con cantidades en $
```

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

---

## Mi nivel técnico

- **Programación:** Principiante avanzado. Funciones, regex, distribuciones, APIs. Primer proyecto real.
- **Terminal:** Cómodo con cmd, Git básico.
- **Python:** urllib, json, re, math, datetime. Sin pip ni librerías externas aún.
- **Git:** Flujo básico add → commit → push.
- **Pendiente aprender:** VS Code, pip, wallet crypto, Railway.

---

## Siguiente paso

**Sesión 3 — Autenticación y ejecución de órdenes en Polymarket:**
1. Crear wallet (Polygon/USDC)
2. Conectar con CLOB API (firma criptográfica)
3. Primera orden de prueba (mínima, dinero real)
4. Integrar ejecución en bot.py
