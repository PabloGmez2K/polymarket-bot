# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 22 de marzo de 2026 (Sesión 9)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, y ejecuta las órdenes automáticamente. Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta. Es arbitraje de información: mejor dato = mejor precio = ganancia.

**Bankroll:** $15 de prueba (objetivo: $100 cuando validemos que el sistema gana).

**Modelo de Claude recomendado:** Sesiones de coding puro → Sonnet. Revisiones de arquitectura, estrategia o diseño de sistemas → Opus.

---

## Progreso: ~99%

- [x] Datos meteorológicos (Open-Meteo, coords de aeropuerto, 30 ciudades)
- [x] Lectura de mercados de Polymarket (Gamma API, tags, parseo regex)
- [x] Parseo de mercados exact, above/below, Y RANGOS "between 62-63°F"
- [x] Alias de ciudades (NYC → New York City, etc.)
- [x] Detección de edge (modelo normal + redondeo)
- [x] Gestión de riesgo (Half-Kelly + presupuesto global)
- [x] Backtest básico (91.4% precisión, 116 mercados)
- [x] Git/GitHub
- [x] Autenticación con Polymarket (Magic wallet, firma EIP-712, credenciales L2)
- [x] Ejecución real de órdenes (DRY_RUN flag, GTC limit orders)
- [x] Filtro de precio 8¢–92¢, agresividad +2¢, check duplicados, limpieza stale
- [x] Despliegue en Railway (bot corriendo 24/7, **EU West Amsterdam**)
- [x] Alertas Telegram (arranque, órdenes, errores)
- [x] Scheduler estratégico (horas UTC fijas: 08, 16, 23)
- [x] Comandos Telegram con botones inline (Estado, Cartera, Órdenes, Log, Detalle, Traders, Forzar, Modo)
- [x] Cartera real desde Data API (posiciones + PnL)
- [x] Toggle DRY_RUN desde Telegram (con doble confirmación)
- [x] Decision log (decisions.log + /log en Telegram + /logfull detallado)
- [x] Near misses en resumen: mercados con edge ≥3% que no entraron + cruce con traders
- [x] known_tokens cache (fix órdenes sin enriquecer)
- [x] Threading (polling Telegram + scheduler en paralelo)
- [x] MODO REAL activado con $15
- [x] Pipeline de inteligencia de traders v2 (find_traders + trader_analyzer + signals.json)
- [x] 9 traders de calidad monitorizados (WR≥50%, PnL positivo)
- [x] Cruce edge×traders en decision log ("🤝 CONFIRMADO por...")
- [x] Descubrimiento semanal automático (lunes 08:00 UTC)
- [x] Análisis diario automático de traders (primer ciclo del día)
- [x] **PRIMERAS ÓRDENES REALES: 4/4 OK** (Paris NO, Dallas YES, Miami YES, London NO)
- [x] Procfile para Railway
- [x] DRY_RUN=false permanente en Railway Variables
- [x] MIN_EDGE, MIN_BET, MAX_BET_PCT configurables desde Railway Variables
- [ ] Fix UX: mensaje "Ejecutando primer ciclo..." tras arranque
- [ ] Validar resultados: observar 2-3 días, analizar decisions.log + PnL
- [ ] Calibrar sigma con datos reales
- [ ] Múltiples fuentes meteorológicas (GFS, ECMWF)
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

### Sesión 4 (21 marzo 2026) — Modelo: Sonnet
- `bot.py` v2: autenticación integrada, ejecución real
- **Primera ejecución real:** 2 órdenes vivas (Shanghai YES 16°C, Wellington YES 18°C)

### Sesión 5 (21 marzo 2026) — Modelo: Opus
- **Revisión estratégica completa** — bot.py v3 con 4 mejoras clave
- Filtro precio, agresividad, duplicados, stale

### Sesión 6 (21 marzo 2026) — Modelo: Sonnet
- requirements.txt, DRY_RUN/BANKROLL como env vars
- Despliegue en Railway, alertas Telegram

### Sesión 7 (21 marzo 2026) — Modelo: Opus
- **bot.py v7** — Reescritura mayor
- Scheduler estratégico, Telegram bidireccional, decision log, known_tokens cache
- **MODO REAL activado** a las 23:09 UTC

### Sesión 8 (22 marzo 2026) — Modelo: Sonnet
- bot.py v8: MIN_DAYS=0, MAX_DAYS=5, reintentos de red, +11 ciudades
- Pipeline de inteligencia v1 (find_traders, trader_analyzer, traders_db)
- Análisis de 3 traders de referencia

### Sesión 9 (22 marzo 2026) — Modelo: Opus
- **Rediseño completo del pipeline de inteligencia:**
  - `find_traders.py` v2: escanea 120 mercados, 2376 traders, clasifica por estrategia (lottery/mid_range/high_confidence), filtra 32 mid_range relevantes
  - `trader_analyzer.py` v2: genera `signals.json` con señales accionables, filtro de calidad (WR≥50% + PnL positivo), 9 traders calidad de 34 analizados
  - Integración en `bot.py` v9: cruce edge×señales, comando /traders, descubrimiento semanal, análisis diario
- **Fix crítico: Kelly bloqueaba todas las apuestas**
  - MAX_BET_PCT: 5% → 10% (con $15, 5% = $0.75 < $1 mínimo → todo rechazado)
  - MIN_BET: $1.00 → $0.50
  - Min shares: 5 → 1
  - Resultado: 38 oportunidades bloqueadas → 27+ oportunidades viables
- **Geobloqueo resuelto:** Railway US West → EU West (Amsterdam)
- **PRIMERAS ÓRDENES REALES EXITOSAS: 4/4 OK**
  - Paris NO $1.50 (41% edge) 🤝 7 traders confirman
  - Dallas YES $1.50 (31% edge)
  - Miami YES $1.50 (46% edge)
  - London NO $1.50 (37% edge) 🤝 5 traders confirman
  - Total invertido: $6.00 de $15
- **Nuevos comandos Telegram:**
  - 📋 Detalle (/logfull): análisis completo de todos los mercados evaluados
  - 🔍 Traders: señales activas de traders de calidad
- **Near misses en /log:** mercados con edge ≥3% que no entraron, cruzados con traders
- **Feedback mejorado:** "💤 Ciclo completado" siempre se envía, nunca silencio
- **Log sobrevive redeploy:** lee de decisions.log si memoria vacía

**Conceptos aprendidos en sesión 9:**
- Pipeline de inteligencia como sistema completo: descubrimiento → clasificación → filtro de calidad → señales → cruce con edge
- El Kelly criterion con bankroll pequeño puede bloquear todo: los mínimos importan tanto como la fórmula
- Geobloqueo: dónde corre tu servidor importa tanto como el código
- Near misses como herramienta de diagnóstico: sin ellos no habríamos visto que el edge existía

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v9 — scheduler + Telegram + decision log + trader signals |
| `find_traders.py` | v2: descubrimiento inteligente basado en trades (120 mercados) |
| `trader_analyzer.py` | v2: análisis profundo + signals.json con filtro calidad |
| `traders_db.json` | 34 traders registrados (2 core + 32 descubiertos) |
| `signals.json` | 225 señales accionables de 9 traders calidad |
| `trader_history.json` | Histórico acumulativo de análisis |
| `decisions.log` | Log detallado de cada decisión del bot (en Railway) |
| `trades.log` | Registro técnico de operaciones (en Railway) |
| `Procfile` | Indica a Railway cómo arrancar (`web: python bot.py`) |
| `requirements.txt` | Librerías para Railway |
| `.env` | Claves (NO en git) |

### Configuración en bot.py v9:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "0.50"))
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))  # 10% de bankroll
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = 0
MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
SCHEDULE_HOURS_UTC = [8, 16, 23]
```

### Variables de Railway:
```
PK="..."
FUNDER="..."
DRY_RUN="false"
BANKROLL="15.00"
TELEGRAM_TOKEN="..."
TELEGRAM_CHAT_ID="495704420"
# MIN_EDGE, MIN_BET, MAX_BET_PCT: no definidas → usan defaults del código
```

### 30 ciudades cubiertas + aliases:
Seoul, London, Tel Aviv, Shanghai, Tokyo, New York City, Beijing, Hong Kong, Singapore, Toronto, Chicago, Wellington, Munich, Warsaw, Ankara, Atlanta, Shenzhen, Paris, Buenos Aires, Miami, Madrid, Seattle, Dallas, Lucknow, Sao Paulo, Taipei, Milan, Chongqing, Chengdu, Wuhan
Aliases: NYC→New York City, HK→Hong Kong, SP→Sao Paulo, BA→Buenos Aires

### Pipeline de inteligencia de traders:
```
find_traders.py          →    traders_db.json    →    trader_analyzer.py
(120 mercados, 2376       (34 traders, 9 calidad)    (señales + consenso)
 traders, clasifica)                                         ↓
                                                      signals.json
                                                    (225 señales, 51 consenso)
                                                         ↓
                                                      bot.py main()
                                                    (cruce con edge)
```

### 9 Traders de calidad:
| Nombre | WR | PnL | Señales | Especialidad |
|--------|---|---|---|---|
| Entire-Hood | 84% | +$4,153 | 32 | Tokyo, Chicago, Shenzhen |
| Thrifty-Original | 75% | +$48 | 21 | New York, Tokyo, London |
| Dimpled-Boy | 78% | +$275 | 8 | Tel Aviv, London, Tokyo |
| Auto_007 | 61% | +$163 | 21 | New York, London, Taipei |
| Auto_003 | 59% | +$115 | 47 | Milan, Wuhan, Tel Aviv |
| Small-Retirement | 59% | +$395 | 48 | Shanghai, Singapore, Hong Kong |
| Unwieldy-Counsel | 56% | +$121 | 1 | Seattle |
| Rubbery-Worshiper | 62% | +$35 | 45 | New York, Wellington, Munich |
| Unaware-Engine | 100% | +$0.45 | 1 | Beijing (datos mínimos) |

### APIs utilizadas:
| API | URL | Función |
|-----|-----|---------|
| Gamma API | gamma-api.polymarket.com | Mercados, preguntas, precios |
| Data API | data-api.polymarket.com | Posiciones, trades, PnL |
| CLOB API | clob.polymarket.com | Órdenes, autenticación |
| Open-Meteo | api.open-meteo.com | Previsiones meteorológicas |
| Telegram | api.telegram.org | Dashboard + alertas |

---

## Lo que hay que hacer en la próxima sesión

### Prioridad 1: Observar y validar (no tocar código)
- El bot tiene órdenes vivas desde 13:16 UTC del 22 de marzo
- **Revisar cartera:** ¿se llenaron las órdenes? ¿cuál es el PnL?
- **Revisar decisions.log:** ¿qué hicieron los ciclos de 16:00 y 23:00 UTC?
- **Comparar con traders:** ¿las órdenes confirmadas por traders fueron mejores?
- Solo con 2-3 días de datos podemos decidir si escalar a $100

### Prioridad 2: Fix UX del arranque
- Problema: tras redeploy, bot ejecuta primer ciclo silenciosamente
- El usuario ve "Bot arrancado" → espera → pulsa Forzar → "Ya en ejecución"
- Fix: enviar "🔄 Ejecutando primer ciclo..." antes de llamar a main()

### Prioridad 3: Análisis de rendimiento
- ¿Fill rate? (¿cuántas limit orders se llenan vs expiran?)
- ¿Los mercados de rango (between X-Y°F) dan mejor/peor edge?
- ¿Las órdenes confirmadas por traders tienen mejor PnL que las solitarias?

### Prioridad 4: Calibración
- Sigma fija vs sigma dinámica por ciudad
- Múltiples fuentes meteorológicas para reducir error
- Si los datos confirman rentabilidad → escalar a $100

### Archivos que Pablo adjuntará:
- `bot.py` (v9)
- `find_traders.py` (v2)
- `trader_analyzer.py` (v2)
- `traders_db.json`
- Capturas de Telegram con resultados de los días de observación
- Railway deploy logs si hay errores

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación real: diferencias 0.5-2°C incluso con coords de aeropuerto
2. Modelo simplificado: sigma fija por días, no considera microclima
3. Backtest optimista: usa datos reales, no previsiones históricas
4. Sin precios históricos de Polymarket: backtest solo mide dirección
5. Bankroll pequeño ($15): limita diversificación, cada orden es $1.50

---

## Recordatorios importantes

**Ver qué hizo el bot:** Telegram → 📓 Log (resumen) o 📋 Detalle (completo) o Railway → Logs

**Ajustar parámetros sin push:** Railway → Variables → añadir MIN_EDGE=5.0 (o MIN_BET, MAX_BET_PCT)

**Push a GitHub:**
```
cd C:\Projects\polymarket-bot
git add .
git commit -m "descripción"
git push
```

**Región Railway:** EU West (Amsterdam) — NO cambiar a US, da geobloqueo 403
