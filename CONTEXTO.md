# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 22 de marzo de 2026 (Sesión 10)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, Y AHORA gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta. Cada ciclo, antes de buscar nuevas oportunidades, gestiona posiciones existentes: corta pérdidas, asegura ganancias, y re-evalúa con datos frescos.

**Bankroll:** $15 de prueba. Cartera actual ~$10.70. PnL histórico: -$7.02 (antes de gestión activa).

**IMPORTANTE — Descubrimiento de Sesión 10:** La fuente de resolución de Polymarket NO es Open-Meteo — es Weather Underground (wunderground.com), con estaciones específicas por ciudad (KLGA para NYC, LFPG para Paris, etc.). Los traders más exitosos ($2M+) usan NOAA/GFS/ECMWF. Pendiente de investigar si podemos mejorar nuestra fuente de datos.

**Modelo de Claude recomendado:** Sesiones de coding puro → Sonnet. Revisiones de arquitectura, estrategia o diseño de sistemas → Opus.

---

## Progreso

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
- [x] Comandos Telegram con botones inline
- [x] Cartera real desde Data API (posiciones + PnL)
- [x] Toggle DRY_RUN desde Telegram (con doble confirmación)
- [x] Decision log (decisions.log + /log en Telegram + /logfull detallado)
- [x] Pipeline de inteligencia de traders v2
- [x] 9 traders de calidad monitorizados
- [x] Cruce edge×traders en decision log
- [x] MODO REAL activado con $15
- [x] **FIX: Exposición acumulativa** (Data API antes de apostar)
- [x] **Sigma recalibrada** (0.8→1.2 día 0, 1.0→1.5 día 1, etc.)
- [x] **Gestión activa de posiciones** (stop-loss -25%, take-profit +40%, re-evaluación con edge<-3%)
- [x] **Performance tracker** (performance.json + comando /rendimiento en Telegram)
- [x] **Investigación de traders** (trader_behavior.py: Entire-Hood 58% gestión activa, 0 pérdidas por resolución)
- [x] **Bankroll dinámico** (consulta valor real de cartera en vez de $15 hardcoded)
- [x] **Sistema de auditoría** (audit.json: verificar fills de ventas + comparar previsión vs temperatura real)
- [x] **Cash balance real** (client.get_balance() para USDC disponible)
- [ ] Calibrar sigma con datos reales (WU vs Open-Meteo)
- [ ] Múltiples fuentes meteorológicas (GFS, ECMWF)
- [ ] Investigar WU como fuente de validación
- [ ] Escalar a $100 (solo si los datos confirman que gana)

---

## Historial de sesiones

### Sesiones 1-9 (21-22 marzo 2026)
Ver archivo de contexto anterior para detalle completo. Resumen: construimos el bot desde cero, lo desplegamos en Railway, primeras 8 órdenes reales, pipeline de traders.

### Sesión 10 (22 marzo 2026) — Modelo: Opus
- **Análisis de pérdidas post-mortem:** 10 posiciones, PnL -$7.02 (-47%)
  - 5 posiciones resueltas: TODAS pérdidas totales (0/5 = 0% WR)
  - 3 en ganancia no realizada: Taipei +67%, Dallas +22%, London +9%
  - 2 en pérdida: Miami -26%, NYC -79%
  - Root cause 1: sigma demasiado baja (sobreconfianza)
  - Root cause 2: exposición no acumulativa entre ciclos (80% vs 40% max)
  - Root cause 3: ZERO gestión activa (buy-and-hold hasta resolución)

- **Fix exposición acumulativa (v10):**
  - `get_current_exposure()`: consulta Data API para saber cuánto hay invertido
  - Presupuesto = (bankroll × 40%) - dinero_ya_invertido
  - Si API falla → asume todo invertido (conservador)

- **Sigma recalibrada (v10):**
  - Día 0: 0.8→1.2 | Día 1: 1.0→1.5 | Día 2: 1.4→2.0 | Día 3: 1.8→2.5

- **Investigación de traders exitosos (trader_behavior.py):**
  - Entire-Hood (WR=84%, +$4,153): 58% gestión activa, **0 PÉRDIDAS POR RESOLUCIÓN**
    - Take-profit promedio +17%, stop-loss promedio -10%
    - 29 holds = 29 wins (100% cuando aguanta)
  - Thrifty-Original (WR=75%, +$48): 50% gestión activa
    - 5 pérdidas por resolución = -$141 (las que no gestionó)
    - Stop-loss menos disciplinado (-23% vs -10%)
  - Conclusión: gestión activa NO es opcional. Es la diferencia entre ganar y perder.

- **Investigación web — descubrimientos clave:**
  - **Fuente de resolución:** Polymarket resuelve con Weather Underground, NO con Open-Meteo
    - NYC: wunderground.com → LaGuardia (KLGA)
    - Paris: wunderground.com → CDG (LFPG)
    - London: wunderground.com → London City Airport (EGLC)
  - **Bots exitosos documentados:**
    - gopfan2 (+$2M): reglas simples de precio (YES < $0.15, NO > $0.45)
    - Hans323 (+$80K weather): arbitraje latencia entre modelo y precios
    - Bots con $24K profit: ENTRY_THRESHOLD=15%, EXIT_THRESHOLD=45¢
  - **Estrategias de los que ganan:**
    - Venden ANTES de resolución cuando el precio sube (no esperan a $1)
    - Reciclan capital (mismo $15 puede hacer 20+ trades/semana vs nuestros 4)
    - Re-evalúan con cada actualización del modelo meteorológico (cada 6-12h)

- **Gestión activa de posiciones (v10.1):**
  - `manage_positions()` se ejecuta al inicio de cada ciclo, ANTES de buscar oportunidades
  - 3 checks por posición, en orden:
    1. **Stop-loss:** PnL% < -25% → vender (configurable: STOP_LOSS_PCT)
    2. **Take-profit:** PnL% > +40% → vender (configurable: TAKE_PROFIT_PCT)
    3. **Re-evaluación:** consulta previsión fresca, recalcula edge. Si edge < -3% → vender
  - Ventas con SELL_AGGRESSION = -2¢ (debajo del mercado para asegurar fill)
  - Notificaciones Telegram: 🔻 Stop-loss / 💰 Take-profit / 🔄 Re-evaluación

- **Performance tracker (v10.1):**
  - `performance.json`: registra cada BUY y SELL con todos los datos
  - Datos: ciudad, lado, precio, edge, previsión, traders confirmados, razón de venta, PnL
  - Comando /rendimiento: ROI, ventas por tipo, comparación trader vs solo, ciudades
  - Esto permite análisis futuro de qué funciona y qué no

- **Primer ciclo con gestión activa — RESULTADOS:**
  - 💰 Taipei YES take-profit: +93.2% (+$1.44) — PRIMERA GANANCIA REALIZADA
  - 🔻 Dallas YES stop-loss: -32.3% (-$0.95) — cortada a tiempo
  - 🔻 NYC YES stop-loss: -87.8% (-$1.26) — demasiado tarde (herencia v9)
  - 🔻 Paris NO stop-loss: -98.5% (-$1.02) — demasiado tarde (herencia v9)
  - ✓ London YES mantenida: +4.2%, edge +13.1% — re-evaluación correcta
  - 23 oportunidades con edge pero 0 seleccionadas (presupuesto agotado)

- **Fixes menores:**
  - /detalle con fallback a decisions.log + manejo de errores
  - Mensaje "Ejecutando primer ciclo..." al arrancar
  - trader_behavior.py: fix bug timestamp (int vs string)

- **Bankroll dinámico (v10.1 final):**
  - `get_effective_bankroll()`: consulta valor real de cartera (cash + posiciones)
  - BANKROLL de Railway = tope máximo, no valor real
  - Con $10.70 de cartera: presupuesto = $10.70 × 40% = $4.28 (antes: $15 × 40% = $6)
  - Si la API falla → usa BANKROLL estático como fallback

- **Auditoría de huecos (descubierta y ARREGLADA al final de sesión 10):**
  - ~~BANKROLL hardcoded~~ → ARREGLADO con bankroll dinámico (cash + posiciones)
  - ~~No verificamos si órdenes de venta se llenaron~~ → ARREGLADO con audit_check_sell_fills()
  - ~~No registramos temperatura REAL tras resolución~~ → ARREGLADO con audit_check_forecasts()
  - ~~No consultamos cash libre real~~ → ARREGLADO con client.get_balance()

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.1 — gestión activa + performance tracker |
| `find_traders.py` | v2: descubrimiento inteligente de traders |
| `trader_analyzer.py` | v2: genera signals.json con señales accionables |
| `trader_behavior.py` | Investigación: cómo operan los traders exitosos |
| `traders_db.json` | 34 traders registrados (9 calidad) |
| `signals.json` | Señales accionables de traders calidad |
| `performance.json` | **NUEVO** — Historial de BUYs y SELLs con datos completos |
| `audit.json` | **NUEVO** — Ventas pendientes de fill + previsión vs temperatura real |
| `trader_history.json` | Histórico acumulativo de análisis |
| `decisions.log` | Log detallado de cada decisión del bot |
| `trades.log` | Registro técnico de operaciones |
| `Procfile` | `web: python bot.py` |
| `requirements.txt` | Librerías para Railway |
| `.env` | Claves (NO en git) |

### Configuración en bot.py v10.1:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))  # TOPE máximo
# effective_bankroll = get_effective_bankroll()  ← consulta valor real cada ciclo
MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "0.50"))
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))  # 10% de bankroll
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))
SELL_AGGRESSION = 0.02
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
MIN_DAYS_AHEAD = 0
MIN_PRICE = 0.08
MAX_PRICE = 0.92
PRICE_AGGRESSION = 0.02
ORDER_MAX_AGE_HOURS = 8
SCHEDULE_HOURS_UTC = [8, 16, 23]

# Sigma (incertidumbre del modelo):
# Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0
```

### Variables de Railway:
```
PK="..."
FUNDER="..."
DRY_RUN="false"
BANKROLL="15.00"
TELEGRAM_TOKEN="..."
TELEGRAM_CHAT_ID="495704420"
# Otros parámetros: usan defaults del código si no están definidos
```

### Flujo de cada ciclo:
```
0.   Limpiar órdenes stale (>8h)
0.5  manage_positions()           ← Gestión activa
     - Stop-loss (PnL < -25%)
     - Take-profit (PnL > +40%)
     - Re-evaluación (edge < -3%)
     - → track_trade("SELL") + audit_register_pending_sell()
0.6  Auditoría
     - audit_check_sell_fills(): ¿ventas anteriores se llenaron?
     - audit_check_forecasts(): previsión vs temperatura real (calibra sigma)
1.   Escanear mercados de temperatura
2.   Parseo + filtro
3.   Previsiones (Open-Meteo)
4.   Calcular edge + cruzar con traders
5.   Presupuesto (bankroll real: cash + posiciones)
6.   Ejecutar órdenes → track_trade("BUY")
7.   Guardar decision log + notificar Telegram
```

### Comandos Telegram:
📊 Estado | 💰 Cartera | 📓 Log | 📋 Detalle | 🔍 Traders | 📈 Rendimiento (NUEVO) | 📋 Órdenes | 🚀 Forzar ciclo | ⚡ Modo

---

## Lo que hay que hacer en la próxima sesión

### Prioridad 1: Revisar datos de auditoría
- ¿audit.json tiene datos de forecast_vs_real? → error medio del modelo
- ¿Las ventas pendientes se llenaron? → fill rate
- ¿performance.json registra correctamente BUYs y SELLs?
- Si error medio > 2°C → sigma todavía demasiado baja

### Prioridad 2: Analizar rendimiento con datos reales
- /rendimiento en Telegram: ROI, ventas por tipo
- ¿Posiciones con traders confirmados ganan más que las solitarias?
- ¿Qué ciudades dan mejores resultados?
- ¿El stop-loss a -25% es correcto o habría que ajustar?

### Prioridad 3: Optimizar según datos
- Si audit muestra error medio de X°C → ajustar sigma a X
- Si take-profit se activa demasiado pronto → subir umbral
- Si stop-loss se activa demasiado tarde → bajar umbral
- Si ventas no se llenan → ajustar SELL_AGGRESSION

### Prioridad 4: Optimizar reciclaje de capital
- Ahora con gestión activa, el capital rota más rápido
- ¿Deberíamos subir MAX_EXPOSURE_PCT de 40% a 60%?
- ¿O bajar el TAKE_PROFIT_PCT para vender más rápido y reciclar?
- Los bots exitosos usan EXIT_THRESHOLD=45¢ — ¿equivale a nuestro take-profit?

### Prioridad 5: Escalar
- Solo si 3+ días de datos muestran rentabilidad positiva
- Primero $25, luego $50, luego $100
- Cada paso requiere datos que confirmen que el sistema gana

### Archivos que Pablo adjuntará:
- `bot.py` (v10.1)
- Capturas de Telegram con resultados
- performance.json (si tiene datos)
- Railway logs

---

## Errores conocidos y lecciones

### Errores del modelo
1. **Sigma v9 demasiado baja:** 0.8°C para día 0. Decía "93% seguro" cuando debía decir "70% seguro". 5/5 pérdidas por resolución. Ahora 1.2°C.
2. **Exposición no acumulativa v9:** Cada ciclo creía tener $6 frescos. 2 ciclos = $12 de $15 (80%). Fix: consulta Data API.
3. **Sin gestión activa v9:** 100% buy-and-hold. 5 posiciones a $0. Traders exitosos gestionan 50-58% activamente.
4. **Open-Meteo vs Weather Underground:** No estamos usando la fuente de resolución. Error de 1-3°C posible.
5. **BANKROLL hardcoded v10:** Bot calculaba presupuesto sobre $15 cuando solo quedaban $10.70. Fix: bankroll dinámico.

### Lecciones de la investigación de traders
1. **Entire-Hood (el mejor, +$4,153):** 0 pérdidas por resolución. Corta a -10%, toma a +17%. Solo aguanta lo que va a ganar seguro.
2. **Thrifty-Original (+$48):** Menos disciplinado. 5 pérdidas por resolución = -$141. Stop-loss tardío (-23%).
3. **Diferencia:** La disciplina en el stop-loss explica la diferencia entre +$4,153 y +$48.
4. **Los bots exitosos ($24K+):** Venden a 45¢ (no esperan $1). Reciclan capital constantemente.

### Decisiones buenas del bot
- Taipei take-profit a +93%: primera ganancia realizada
- London YES mantenida con re-evaluación positiva: edge +13.1%
- Dallas stop-loss a -32%: habría ido a peor sin corte

### Decisiones que llegaron tarde
- NYC, Paris, London NO: stop-loss ejecutado pero ya valían $0.01 (herencia de v9 sin gestión)

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación WU: previsión vs dato real medido → error 0.5-2°C
2. Sigma estimada, no calibrada con datos reales
3. Sin precios históricos de Polymarket: no sabemos si el edge fue real
4. Bankroll pequeño ($10.70 actual): limita diversificación
5. Órdenes de venta son GTC limit → pueden no llenarse inmediatamente

---

## Recordatorios importantes

**Push a GitHub:**
```
cd C:\Projects\polymarket-bot
git add .
git commit -m "descripción"
git push
```

**Ajustar parámetros sin push:** Railway → Variables → añadir variable (ej: STOP_LOSS_PCT=-15)

**Región Railway:** EU West (Amsterdam) — NO cambiar a US, da geobloqueo 403

**Ver rendimiento:** Telegram → 📈 Rendimiento

**Ver qué hizo el bot:** Telegram → 📓 Log (resumen) o 📋 Detalle (completo)
