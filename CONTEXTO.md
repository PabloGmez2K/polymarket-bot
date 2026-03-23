# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 24 de marzo de 2026 (Sesión 11, fin de sesión)

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders de Polymarket, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, Y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Polymarket tiene mercados donde la gente apuesta sobre la temperatura de mañana en distintas ciudades. El bot consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto donde se mide la temperatura oficial), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta. Cada ciclo, antes de buscar nuevas oportunidades, gestiona posiciones existentes: corta pérdidas, asegura ganancias, y re-evalúa con datos frescos.

**Bankroll:** Fase 2 reiniciada con v10.2. $25 USDC como BANKROLL en Railway. Cash disponible ~$35 (beneficios de día 1 + capital original). Posiciones activas: 0. Posiciones muertas: 3 (valor $0.03, no bloquean presupuesto gracias a Fix 1).

**IMPORTANTE — Descubrimiento de Sesión 10:** La fuente de resolución de Polymarket NO es Open-Meteo — es Weather Underground (wunderground.com), con estaciones específicas por ciudad (KLGA para NYC, LFPG para Paris, etc.). Los traders más exitosos ($2M+) usan NOAA/GFS/ECMWF. Pendiente de investigar si podemos mejorar nuestra fuente de datos.

**Modelo de Claude recomendado:** Sesiones de coding puro → Sonnet. Revisiones de arquitectura, estrategia o diseño de sistemas → Opus. **Entre semana (observación):** usar Sonnet para ahorrar uso. Guardar Opus para sesiones de desarrollo del fin de semana.

---

## Qué hace el bot v10.2 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas que no se llenaron.

**0.5 Gestión activa (manage_positions):** Mira cada posición abierta y hace checks en orden:
- ¿curPrice >= 0.98? → SKIP (mercado resuelto, esperando pago automático) ← **NUEVO v10.2**
- ¿Pierde más de -25%? → VENDER (stop-loss, cortar pérdida)
- ¿Gana más de +40%? → VENDER (take-profit, asegurar ganancia)
- Ni uno ni otro → consulta Open-Meteo con datos frescos, recalcula el edge. Si edge ahora es negativo (<-3%) → VENDER (re-evaluación, la previsión cambió)
- Cada venta se registra en performance.json y se trackea en audit.json

**0.6 Auditoría:** Verifica si las ventas del ciclo anterior se llenaron. Para apuestas de días pasados, compara la previsión de Open-Meteo con la temperatura real observada, registrando el error para calibrar el modelo.

**1. MIN_DAYS_AHEAD dinámico:** ← **NUEVO v10.2**
- Ciclos de mañana (< 12:00 UTC): permite mercados de día 0 (temperaturas aún no registradas)
- Ciclos de tarde/noche (≥ 12:00 UTC): solo mercados de día 1+ (muchas ciudades ya tienen dato real)
- Override manual disponible via Railway variable MIN_DAYS_AHEAD (≥0 fuerza ese valor, -1 = automático)

**2-4. Buscar oportunidades:** Escanea ~330 mercados de temperatura en 30 ciudades, consulta previsiones, calcula probabilidad real (distribución normal + redondeo a enteros), detecta cuando el precio del mercado difiere >7% de la realidad, cruza con señales de 9 traders de calidad tracked.

**5. Control de riesgo:** Consulta exposición REAL (currentValue de posiciones, no initialValue), limita al 40% del bankroll efectivo, dimensiona cada apuesta con Half-Kelly. ← **FIX v10.2: ya no cuenta posiciones muertas como exposición**

**6. Ejecución:** Coloca órdenes de compra, registra en performance.json, notifica por Telegram con resumen claro del ciclo.

Todo se almacena en 3 archivos que acumulan datos valiosos:
- `performance.json`: cada BUY/SELL con ciudad, precio, edge, previsión, traders, PnL
- `audit.json`: ventas pendientes de fill + previsión vs temperatura real
- `decisions.log`: razonamiento completo de cada decisión

---

## Progreso hacia el objetivo de $100

**Sistema técnico: ~98% completado.** El bot v10.2 tiene todo lo que necesita: detección de edge, gestión activa, auditoría, tracking, control de riesgo, y ahora los 3 bugs críticos del día 1 corregidos.

**Validación: ~5%.** Día 1 (23 marzo) fue rentable neto (+$3.36), pero descubrimos 3 bugs que invalidaron los datos como test limpio del sistema. El push de v10.2 reinicia los archivos de datos. Necesitamos 30+ trades limpios con v10.2.

**Tiempo estimado hasta $100:**
- Si todo va bien: 6-8 semanas (validación + escalado gradual)
- Si hay que ajustar: 2-3 meses (repetir fases con ajustes)
- Si el sistema no funciona: parar y rediseñar (posible, hay que ser honesto)

**Mentalidad clave:** Los $25 de ahora son para APRENDER, no para ganar. Si al final de la semana tienes $24, es un resultado excelente — significa que el sistema no pierde dinero y podemos escalar. No buscar +50% en una semana. Buscar +1%.

### Metas concretas

**Corto plazo (semana 1-2):** Validar con $25 usando v10.2. Pasar los 6 checks. Acumular 30+ trades cerrados. Demostrar que el sistema no pierde dinero. Calibrar sigma si audit.json muestra error >2°C.

**Medio plazo (semana 3-6):** Escalar gradualmente $25→$35→$50→$75→$100. Cada salto requiere 7 días rentables. Optimizar parámetros (stop-loss, take-profit, ciudades) con datos reales.

**Largo plazo (mes 2-3):** Con $100 estable y 50+ días de datos: calibrar sigma con datos reales, investigar Weather Underground como segunda fuente, excluir ciudades que pierden, ponderar más señales de traders, posiblemente añadir mercados de precipitación. Objetivo: 10-20% ROI mensual sostenible.

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
- [x] Fix: filtro valor mínimo en ventas (no vender posiciones <$0.10)
- [x] **FIX v10.2: Exposición fantasma** — get_current_exposure() usa currentValue (no initialValue)
- [x] **FIX v10.2: MIN_DAYS_AHEAD dinámico** — get_min_days_ahead() ajusta por hora UTC
- [x] **FIX v10.2: Skip mercados resueltos** — curPrice >= 0.98 → no intentar vender
- [x] **v10.2: Telegram mejorado** — cartera separa activas/muertas/resueltas, resumen de ciclo claro
- [x] **v10.2: verify_before_deploy.py v2** — 18 tests, detecta los 3 bugs que nos costaron dinero
- [ ] Calibrar sigma con datos reales de audit.json (error previsión vs real)
- [ ] Investigar Weather Underground como fuente de validación
- [ ] Fase 2: Validar sistema v10.2 (7-14 días, 30+ trades)
- [ ] Fase 3: Escalar gradualmente $25→$35→$50→$75→$100

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

- **Construido en sesión 10:**
  - Fix exposición acumulativa (v10)
  - Sigma recalibrada
  - Investigación de traders exitosos (trader_behavior.py)
  - Gestión activa de posiciones (v10.1)
  - Performance tracker
  - Bankroll dinámico
  - Sistema de auditoría

- **Descubrimientos clave:**
  - Fuente de resolución: Weather Underground, NO Open-Meteo
  - Bots exitosos: gopfan2 (+$2M), Hans323 (+$80K weather)
  - Entire-Hood (+$4,153): 58% gestión activa, 0 pérdidas por resolución

### Sesión 10b (23 marzo 2026) — Deploy Fase 2 + primer día
- Deploy de v10.1 con $25 BANKROLL
- **Día 1 resultados:**
  - Mañana: Tokyo +$8.67, Dallas +$1.12, London +$2.25, Chongqing +$5.24 = **+$17.28**
  - Tarde: Paris NO, London NO, Chongqing NO = **-$7.50** (compras contra info conocida)
  - Neto: +$3.36 | Cartera: $36.21
- **Bug crítico descubierto:** A las 16:00-23:00 UTC, las temperaturas de Europa/Asia ya se habían registrado. El bot apostaba contra información conocida.
- **Fix temporal:** MIN_DAYS_AHEAD=1 en Railway Variables
- **Repo cambiado a PRIVADO**

### Sesión 11 (24 marzo 2026, noche) — Modelo: Opus
**Motivo:** 3 bugs detectados durante observación del día 1 que invalidan los datos de Fase 2.
Decisión: corregir ahora en vez de esperar, reiniciar Fase 2 con código limpio.

- **Bug 1 — Exposición fantasma (CRÍTICO, bloqueaba el bot):**
  - `get_current_exposure()` sumaba `initialValue` ($2.50 por posición) en vez de `currentValue` ($0.01)
  - 7 posiciones muertas contaban como $9.23 de exposición cuando valían $0.11
  - Con BANKROLL=25 y max 40% = $10, solo quedaba $0.77 de presupuesto
  - El bot no podía apostar en nada → Toronto cancelado por presupuesto insuficiente
  - **Fix:** `get_current_exposure()` ahora suma `currentValue` (lo que vale, no lo que pagamos)

- **Bug 2 — Compra día-0 por la tarde (CRÍTICO, -$7.50):**
  - MIN_DAYS_AHEAD era 0 fijo (o 1 por parche en Railway)
  - A las 16:00+ UTC, temperaturas de Europa/Asia ya registradas
  - El bot apostaba usando previsión contra información ya conocida
  - **Fix:** `get_min_days_ahead()` función dinámica:
    - < 12:00 UTC → min_days=0 (temperaturas no registradas)
    - ≥ 12:00 UTC → min_days=1 (muchas ciudades ya tienen dato)
    - Railway override: MIN_DAYS_AHEAD=-1 para modo automático

- **Bug 3 — Venta de mercados resueltos (ruido en logs):**
  - Si curPrice >= 0.98, el mercado ya se resolvió a YES
  - Intentar vender daba error "orderbook does not exist"
  - **Fix:** skip en manage_positions, marca como "🏁 RESUELTO, esperando pago"

- **Mejora: Telegram rediseñado:**
  - `/cartera` ahora separa: cash, posiciones activas, resueltas (esperando pago), muertas (solo resumen)
  - Resumen de ciclo: un solo mensaje que dice qué vendió (y por qué), qué compró, qué mantuvo, exposición y presupuesto

- **Mejora: verify_before_deploy.py v2:**
  - De 13 tests (con huecos) a 18 tests limpios
  - Tests nuevos que habrían detectado los 3 bugs:
    - Inspecciona código de `get_current_exposure()` buscando `currentValue` vs `initialValue`
    - Verifica que `get_min_days_ahead()` tiene lógica por hora UTC
    - Verifica skip `curPrice >= 0.98` en manage_positions
    - Test de API Open-Meteo (antes no se verificaba)
    - Test de Telegram (verifica que el token es válido)
  - 22/22 passed, 0 warnings, 0 errors

- **Estado post-sesión 11:**
  - Cartera: ~$35 cash, 0 posiciones activas, 3 muertas ($0.03)
  - Bot: v10.2 desplegado, DRY_RUN=false, BANKROLL=25, MIN_DAYS_AHEAD=-1
  - Fase 2 reiniciada con código limpio — datos de v10.1 descartados (tenían bugs)
  - Push borra performance.json/audit.json/decisions.log (correcto: datos limpios desde v10.2)

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO — no compartir)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false

### Archivos:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.2 — 3 bugfixes + Telegram mejorado |
| `verify_before_deploy.py` | **v2** — 18 tests pre-deploy, detecta bugs conocidos |
| `find_traders.py` | v2: descubrimiento inteligente de traders |
| `trader_analyzer.py` | v2: genera signals.json con señales accionables |
| `trader_behavior.py` | Investigación: cómo operan los traders exitosos |
| `traders_db.json` | 34 traders registrados (9 calidad) |
| `signals.json` | Señales accionables de traders calidad |
| `performance.json` | Historial de BUYs y SELLs con datos completos |
| `audit.json` | Ventas pendientes de fill + previsión vs temperatura real |
| `trader_history.json` | Histórico acumulativo de análisis |
| `decisions.log` | Log detallado de cada decisión del bot |
| `trades.log` | Registro técnico de operaciones |
| `Procfile` | `web: python bot.py` |
| `requirements.txt` | Librerías para Railway |
| `.env` | Claves (NO en git) |

### Configuración en bot.py v10.2:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
# effective_bankroll = get_effective_bankroll()  ← consulta valor real cada ciclo
MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "0.50"))
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))  # 10% de bankroll
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))  # -1 = automático
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))
SELL_AGGRESSION = 0.02
MIN_LIQUIDITY = 100
MAX_DAYS_AHEAD = 5
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
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"   ← NUEVO v10.2: modo automático
TELEGRAM_TOKEN="..."
TELEGRAM_CHAT_ID="495704420"
# Otros parámetros: usan defaults del código si no están definidos
```

### Flujo de cada ciclo:
```
0.   Limpiar órdenes stale (>8h)
0.5  manage_positions()
     - Skip resueltos (curPrice >= 0.98) ← NUEVO v10.2
     - Stop-loss (PnL < -25%)
     - Take-profit (PnL > +40%)
     - Re-evaluación (edge < -3%)
     - → track_trade("SELL") + audit_register_pending_sell()
0.6  Auditoría
     - audit_check_sell_fills(): ¿ventas anteriores se llenaron?
     - audit_check_forecasts(): previsión vs temperatura real
1.   MIN_DAYS_AHEAD dinámico (0 mañana, 1 tarde) ← NUEVO v10.2
2.   Escanear mercados de temperatura
3.   Parseo + filtro
4.   Previsiones (Open-Meteo)
5.   Calcular edge + cruzar con traders
6.   Presupuesto (exposición = currentValue, no initialValue) ← FIX v10.2
7.   Ejecutar órdenes → track_trade("BUY")
8.   Resumen de ciclo por Telegram ← NUEVO v10.2
```

### Comandos Telegram:
📊 Estado | 💰 Cartera (rediseñada v10.2) | 📓 Log | 📋 Detalle | 🔍 Traders | 📈 Rendimiento | 📋 Órdenes | 🚀 Forzar ciclo | ⚡ Modo

---

## Roadmap: De prueba a producción

### Situación actual (post sesión 11)
- v10.2 desplegada con 3 bugfixes + Telegram mejorado
- Fase 2 reiniciada con datos limpios
- Cash: ~$35 | Posiciones activas: 0 | BANKROLL=25
- verify_before_deploy.py v2: 22/22 passed

### Fase 2: Validación ($25 de capital) — 🟢 REINICIADA con v10.2
**Inicio real: 24 marzo 2026 (post-deploy v10.2)**

**¿Por qué reiniciar?** Los datos del día 1 (23 marzo) tenían 3 bugs activos: exposición fantasma bloqueando presupuesto, compras contra info conocida (-$7.50), y errores de mercados resueltos. Los +$3.36 de beneficio son reales pero los datos no sirven para validar el sistema.

**Checks de validación (mínimo 7 días, 30+ trades cerrados):**
1. Win rate > 55% en trades cerrados (no en posiciones abiertas)
2. ROI positivo después de fees
3. Error medio de previsión < 2°C (audit.json lo mide)
4. Stop-loss activándose ANTES de -50% (no a -99% como en v9)
5. Al menos 3 take-profits realizados
6. Fill rate de órdenes > 60%

**Si FALLA cualquier check:** PARAR. Analizar. Ajustar. Repetir Fase 2 (sin añadir dinero).

### Fase 3: Escalado gradual (solo si Fase 2 pasa TODOS los checks)
```
$25 → 7 días rentables → +$10 = $35
$35 → 7 días rentables → +$15 = $50
$50 → 7 días rentables → +$25 = $75
$75 → 7 días rentables → +$25 = $100
```
**Regla de oro:** Si en cualquier fase el PnL cae por debajo de -15% del bankroll actual → PARAR. Analizar. No añadir dinero. Nunca más del doble de golpe.

### Variables de mejora continua (el bot las mide automáticamente)
| Variable | Archivo | Qué nos dice | Acción si falla |
|----------|---------|-------------|-----------------|
| Error previsión | audit.json forecast_vs_real | Precisión del modelo | Ajustar sigma |
| Fill rate | audit.json pending_sells | ¿Se ejecutan las órdenes? | Ajustar SELL_AGGRESSION |
| ROI por ciudad | performance.json | ¿Qué ciudades ganan? | Excluir las que pierden |
| Trader confirmation | performance.json | ¿Traders mejoran ROI? | Ponderar más si sí |
| Stop-loss timing | performance.json | ¿Cortamos a tiempo? | Ajustar STOP_LOSS_PCT |
| Take-profit timing | performance.json | ¿Vendemos bien? | Ajustar TAKE_PROFIT_PCT |

### Lo que hay que hacer en la próxima sesión

1. **Revisar datos acumulados de la semana (usar Sonnet, no Opus):**
   - /rendimiento: ¿ROI positivo o negativo?
   - /log: ¿cuántos trades se ejecutaron? ¿gestión activa funcionó?
   - /cartera: valor actual vs $25 depositados
   - ¿Los mensajes de Telegram v10.2 son claros?
2. **Analizar performance.json y audit.json** (capturas de Telegram o Railway logs)
   - Error medio de previsión (forecast vs real)
   - Fill rate de ventas
   - ROI por ciudad
3. **Evaluar checks de Fase 2:**
   - Win rate > 55%? ROI positivo? Error < 2°C? Stop-loss a tiempo?
4. **Decidir:** ¿seguir Fase 2? ¿ajustar parámetros? ¿escalar a $35?

### Archivos que Pablo adjuntará:
- Capturas de Telegram: cartera (nueva), log, rendimiento, resúmenes de ciclo
- Railway logs si hay errores

### ⚠️ REGLA CRÍTICA DE LA SEMANA
**NO hacer git push hasta la próxima sesión.** Cada push borra performance.json, audit.json y decisions.log del container Railway. Los datos acumulados durante la semana son los que necesitamos para evaluar el sistema.

### Monitoreo diario (5 minutos)
- Mirar Telegram una vez al día: ¿hay 3 ciclos (08:00, 16:00, 23:00 UTC)?
- 💰 Take-profit o 🔻 Stop-loss → bien, gestión activa funciona
- 🛒 Compra → verificar que no sea día-0 por la tarde (ya corregido, pero vigilar)
- ❌ Error repetido → hacer captura para próxima sesión
- **No cambiar variables, no forzar ciclos, no depositar más dinero**

### Señales de alarma (contactar Claude con Sonnet)
- 24h sin mensajes del bot → puede haberse caído
- Mismo error repetido en cada ciclo → bug activo
- Cartera cae por debajo de $20 en un solo día → algo va mal

---

## Errores conocidos y lecciones

### Errores del modelo (histórico)
1. **Sigma v9 demasiado baja:** 0.8°C para día 0. Decía "93% seguro" cuando debía decir "70% seguro". 5/5 pérdidas por resolución. Fix sesión 10: ahora 1.2°C.
2. **Exposición no acumulativa v9:** Cada ciclo creía tener $6 frescos. 2 ciclos = $12 de $15 (80%). Fix sesión 10: consulta Data API.
3. **Sin gestión activa v9:** 100% buy-and-hold. 5 posiciones a $0. Fix sesión 10: manage_positions con 3 checks.
4. **Open-Meteo vs Weather Underground:** No estamos usando la fuente de resolución. Error de 1-3°C posible.
5. **BANKROLL hardcoded v10:** Bot calculaba presupuesto sobre $15 cuando solo quedaban $10.70. Fix sesión 10: bankroll dinámico.
6. **Cash balance API v10.1:** `client.get_balance()` no funciona con Magic wallet. Fix sesión 10: fallback a BANKROLL.
7. **Push sin verificar (lección proceso):** Se dijo "listo para push" múltiples veces con bugs activos. Lección: SIEMPRE ejecutar verify_before_deploy.py.
8. **Exposición fantasma v10.1 (sesión 11):** `get_current_exposure()` sumaba `initialValue` → posiciones muertas de $0.01 contaban como $9.23. Fix v10.2: usa `currentValue`.
9. **Compra día-0 por la tarde v10.1 (sesión 11):** A las 16:00-23:00 UTC, temperaturas ya registradas. -$7.50 en un ciclo. Fix v10.2: `get_min_days_ahead()` dinámico.
10. **Venta mercado resuelto v10.1 (sesión 11):** curPrice=1.00 → error "orderbook does not exist". Fix v10.2: skip si curPrice >= 0.98.

### Lecciones de la investigación de traders
1. **Entire-Hood (el mejor, +$4,153):** 0 pérdidas por resolución. Corta a -10%, toma a +17%. Solo aguanta lo que va a ganar seguro.
2. **Thrifty-Original (+$48):** Menos disciplinado. 5 pérdidas por resolución = -$141. Stop-loss tardío (-23%).
3. **Los bots exitosos ($24K+):** Venden a 45¢ (no esperan $1). Reciclan capital constantemente.

### Lección meta de sesión 11
**Cuando detectas un bug crítico durante observación, corregirlo inmediatamente.** No esperar al fin de semana. Una semana de datos con un bug activo es una semana perdida. Es mejor gastar 1h de Opus y reiniciar con código limpio que acumular 7 días de datos inválidos.

---

## Evaluación honesta del proyecto (fin sesión 11)

### ¿Hay oportunidad real?
SÍ. Datos públicos verificables: bots con +$24K (London weather), traders con +$78K (ColdMath), +$2M (gopfan2). Weather markets son pura física/matemáticas, no opinión. La ventaja informativa (previsión profesional vs crowd) es real y medible.

### ¿Estamos listos para $100?
NO. Track record actual: v10.1 tuvo un día rentable (+$3.36) pero con 3 bugs activos. v10.2 tiene 0 trades — es un sistema nuevo sin validar. Necesitamos mínimo 30 trades cerrados limpios.

### ¿Qué nos da confianza?
- El día 1 fue rentable PESE a los bugs (-$7.50 de compras imposibles aún dejó +$3.36 neto)
- Entire-Hood (+$4,153) usa la misma estrategia que replicamos
- Los 3 bugs encontrados y corregidos eran todos de implementación, no de estrategia
- El verificador v2 ahora detectaría esos bugs antes de deploy
- Weather markets son repetibles: nuevos mercados cada día, misma mecánica

### ¿Qué nos preocupa?
- Competencia creciente: más bots cada mes → edges más pequeños
- Bankroll pequeño: $25 no permite diversificación real (4-5 posiciones)
- Open-Meteo no es la fuente de resolución (Weather Underground lo es)
- v10.2 tiene 0 trades: todo es teoría hasta que tengamos datos

### Probabilidad estimada de éxito
- Con sistema v9 (sin gestión): ~15% (lo que vimos: -88%)
- Con sistema v10.2 (gestión activa + bugfixes): ~50-60%
- Para subir a 65%+: necesitamos calibrar sigma con datos reales y posiblemente mejorar fuente de datos

---

## Limitaciones conocidas del modelo

1. Open-Meteo vs estación WU: previsión vs dato real medido → error 0.5-2°C
2. Sigma estimada, no calibrada con datos reales (audit.json la calibrará)
3. Sin precios históricos de Polymarket: no sabemos si el edge fue real
4. Bankroll pequeño: limita diversificación (4-5 posiciones max)
5. Órdenes de venta son GTC limit → pueden no llenarse inmediatamente

---

## Ideas de mejora pendientes (no implementar hasta validar Fase 2)

1. **Reciclaje agresivo de capital:** Si manage_positions cierra una posición, buscar oportunidades inmediatamente en el mismo ciclo en vez de esperar al siguiente. Los bots de $24K+ reciclan constantemente.
2. **Aumentar frecuencia de gestión:** Cambiar de cada 8h a cada 3-4h.
   Solo requiere cambiar SCHEDULE_HOURS_UTC en Railway.
   Implementar después de validar que las decisiones son correctas.

~~3. Mejorar output de Telegram~~ → **HECHO en v10.2**
~~4. Detectar mercados resueltos~~ → **HECHO en v10.2**
~~5. MIN_DAYS_AHEAD dinámico~~ → **HECHO en v10.2**

---

## Recordatorios importantes

**Push a GitHub:**
```
cd C:\Projects\polymarket-bot
python verify_before_deploy.py   ← SIEMPRE antes de push (v2: 18 tests)
git add .
git commit -m "descripción"
git push
```

**Después de push:** Railway → Variables → verificar que MIN_DAYS_AHEAD="-1" (modo automático).

**Ajustar parámetros sin push:** Railway → Variables → añadir variable (ej: STOP_LOSS_PCT=-15). El bot lo leerá en la siguiente ejecución sin necesidad de push.

**Región Railway:** EU West (Amsterdam) — NO cambiar a US, da geobloqueo 403

**Ver rendimiento:** Telegram → 📈 Rendimiento

**Ver qué hizo el bot:** Telegram → 📓 Log (resumen) o 📋 Detalle (completo)

**Repo PRIVADO:** No compartir código, umbrales, ni traders tracked. Cada copia del bot compite contra nosotros por los mismos edges.
