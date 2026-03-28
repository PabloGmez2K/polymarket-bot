# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 28 de marzo de 2026 (Sesiones 14-16 — Observación ciclos 1-9 v10.3)
**Próxima sesión:** Coding con Opus — sábado 28 marzo mañana

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta.

**Bankroll configurado:** $25.00 en Railway.

**IMPORTANTE — Fuente de resolución:** Polymarket NO usa Open-Meteo — usa Weather Underground (wunderground.com). Esto ha causado pérdidas en London (2 veces). Pendiente de investigar e incorporar WU como fuente de validación.

**Modelo de Claude recomendado:** Sesiones de coding → Opus. Observación/análisis → Sonnet.

---

## Estado financiero actual (ciclo 9, 08:00 UTC 28 mar)

- **All-time P&L: -$0.49** (Polymarket, confirmado)
- **Cash disponible: $34.65**
- **Portfolio total: $37.73**

**Posiciones activas (2):**
| Posición | Shares | Entrada | Actual | Valor | PnL |
|----------|--------|---------|--------|-------|-----|
| Dallas YES 58-59°F Mar28 | 15.2 | 16¢ | 9¢ | $1.38 | -43.4% |
| Miami YES 86-87°F Mar28 | 11.9 | 16¢ | 12¢ | $1.43 | -25% |

**Pendientes de canjear (pérdidas confirmadas):**
- Chicago YES 40-41°F Mar27: $0 (-$1.83)
- Toronto NO 0°C Mar27: $0 (-$1.71)

**Próximo ciclo:** 16:00 UTC hoy 28 mar (después de la sesión de coding)

---

## Qué hace el bot v10.3 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas.

**0.5. Gestión activa (manage_positions):** Para cada posición abierta:
- ¿currentValue < $0.10? → LOSS_TOTAL (excluida de gestión)
- ¿curPrice >= 0.98? → SKIP (resuelta, esperando pago)
- ¿PnL < -25%? → VENDER (stop-loss)
- ¿PnL > +40%? → VENDER (take-profit)
- Si no: recalcula edge con Open-Meteo. Si edge < -3% → VENDER (re-evaluación)
- Cada venta se registra como SELL_PENDING → confirmada como SELL por audit

**0.6. Auditoría:** Convierte SELL_PENDING → SELL/SELL_FAILED según fills confirmados.

**1. MIN_DAYS_AHEAD per-city:** Cada ciudad evaluada según su zona horaria local. Si hora_local >= 14 → temperatura ya registrada → min_days=1 para esa ciudad.

**2-4. Buscar oportunidades:** Escanea ~330 mercados, consulta previsiones, calcula edge, cruza con señales de traders de calidad.

**5. Control de riesgo:** Exposición máxima 40% del bankroll efectivo, dimensionado con Half-Kelly.

**6. Ejecución:** Coloca órdenes GTC limit, registra en performance.json, notifica por Telegram.

**NOTA DE DISEÑO — Capital intra-ciclo:** El bot vende en manage_positions() pero calcula presupuesto consultando la Data API. Si el fill de la venta aún no está en la API, el presupuesto del mismo ciclo queda en $0. El capital se libera en el siguiente ciclo. Comportamiento confirmado como latencia de API, no bug permanente.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false
**Versión activa:** v10.3

### Archivos principales:
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.3 (2911 líneas) |
| `verify_before_deploy.py` | v3 — 27+ tests de comportamiento |
| `performance.json` | Historial BUYs, SELLs, LOSS_TOTALs |
| `audit.json` | Ventas pendientes + forecast vs real (actualmente vacío) |
| `decisions.log` | Log detallado por ciclo (50KB) |
| `trades.log` | Log compacto de órdenes (6.1KB) |
| `signals.json` | Señales traders actuales (85KB) |
| `traders_db.json` | 34 traders registrados |

### Configuración en bot.py v10.3:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "0.50"))   # ← código 0.50, Railway tiene 1.00
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))
SCHEDULE_HOURS_UTC = [8, 16, 23]
# Sigma: Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0
```

### Pistas de código (líneas aproximadas en bot.py v10.3):
| Función | Línea aprox. |
|---------|-------------|
| `cmd_estado()` | 592 |
| `get_current_exposure()` | 1346 |
| `get_effective_bankroll()` | 1426 |
| `manage_positions()` | 1513 |
| tracking `SELL_PENDING` | 1795 |
| `main(client)` | 2289 |
| cálculo de presupuesto | 2584 |
| `last_orders_placed` | 2624-2667 |
| primer ciclo al arrancar | 2885 |

### Variables de Railway (estado actual):
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"
MIN_BET="1.00"
```

---

## Historial completo de trades (v10.3, desde 25 marzo)

Datos extraídos de performance.json via SSH más resoluciones observadas:

| # | Ciudad | Mercado | Lado | Coste | Fill real | Resultado | PnL | Motivo cierre | Fecha |
|---|--------|---------|------|-------|-----------|-----------|-----|---------------|-------|
| 1 | Chicago | 62-63°F Mar26 | YES | $2.38* | 10.5¢ | $7.72 | +$3.96* | Take-profit +85% | 25 mar |
| 2 | Ankara | 11°C Mar26 | YES | $2.50 | 10.5¢ | $0 | -$1.90 | LOSS_TOTAL | 26 mar |
| 3 | Atlanta | 66-67°F Mar28 | YES | $4.04** | 13-13.5¢ | $6.71** | +$2.60 | Take-profit +63% | 27 mar |
| 4 | London | 10°C Mar26 | NO | $2.50 | 41.5¢ | ~$0.22 | -$2.25 | Pérdida (WU vs OMA) | 26 mar |
| 5 | Ankara | 13°C Mar26 | NO | $2.50 | 59¢ | $4.24 | +$1.74 | WIN resolución | 26 mar |
| 6 | Chicago | 66-67°F Mar26 | YES | $1.61 | 13.9¢ | $11.59 | +$9.98 | WIN resolución +619% | 26 mar |
| 7 | Miami | 84-85°F Mar26 | YES | $2.20 | 19.5¢ | $0 | -$2.14 | LOSS_TOTAL | 26 mar |
| 8 | Shanghai | 17°C Mar26 | NO | $2.48 | 53¢ | $4.67 | +$2.19 | WIN resolución | 26 mar |
| 9 | Shanghai | 15°C Mar27 | NO | $1.43 | 56.5¢ | $2.52 | +$1.09 | WIN resolución | 27 mar |
| 10 | Seattle | ≤51°F Mar28 | YES | $2.38 | 10.5¢ | $0.96 | -$0.42 | Stop-loss (fill real 4¢) | 28 mar |
| 11 | Wellington | 21°C Mar28 | NO | $2.24 | 50¢ | $4.48 | +$2.24 | WIN resolución | 28 mar |
| 12 | Toronto | 0°C Mar27 | NO | $1.71 | 29.5¢ | $0 | -$1.70 | Pérdida total | 27 mar |
| 13 | Chicago | 40-41°F Mar27 | YES | $1.83 | 19.5¢ | $0 | -$1.83 | Pérdida total | 27 mar |
| 14 | Madrid | ≤11°C Mar29 | YES | $4.82*** | 13-16¢ | $2.50 | -$1.95*** | Stop-loss (bug #3) | 28 mar |
| 15 | Buenos Aires | ≥27°C Mar28 | NO | $1.54 | 31.5¢ | $2.21 | +$0.80 | Take-profit +52% | 28 mar |

*Chicago #1: posición doble por bug #11 deploy. Normal serían ~22 shares.
**Atlanta: dos entradas separadas en ciclos 3 y 4, vendidas juntas.
***Madrid: posición ampliada por bug #3 en ciclo 8. Sin bug, pérdida habría sido ~$1.65.

**Trades abiertos actualmente:** Dallas YES ($1.38, -43.4%), Miami YES ($1.43, -25%)

---

## Ciclos ejecutados (v10.3)

| Ciclo | Hora UTC | Compras | Ventas | Nota |
|-------|----------|---------|--------|------|
| Extra | 25 mar 16:49 | Chicago YES 22.67sh | — | Bug #11 — deploy entre ciclos |
| 2 | 25 mar 23:00 | — | Chicago YES TP +85% | Capital $0 intra-ciclo (latencia API) |
| 3 | 26 mar 08:00 | Ankara YES/NO, London NO, Atlanta YES | — | OK |
| 4 | 26 mar 16:00 | Chicago YES 66-67°F, Atlanta YES, Miami YES, Shanghai NO | — | OK |
| 5 | 26 mar 23:00 | Seattle YES, Buenos Aires NO | — | OK |
| 6 | 27 mar 08:00 | — | Atlanta YES TP +63% | OK |
| 7 | 27 mar 16:00 | Madrid YES, Chicago YES 40-41°F, Toronto NO | — | OK |
| 8 | 27 mar 23:00 | Madrid YES (BUG #3), Wellington NO | Seattle YES SL | Madrid amplificada |
| 9 | 28 mar 08:00 | Dallas YES, Miami YES | Madrid YES SL, Buenos Aires TP | OK |

---

## BUGS — Estado completo

### Bugs corregidos en v10.3:
- **Bug #4** ✅ Resueltas contaban como exposición → excluidas con curPrice >= 0.98
- **Bug #5** ✅ Zona horaria asiática → CITY_UTC_OFFSETS per-city. Costó ~$5.16
- **Bug #6** ✅ signals.json vacío → freshness 12h→26h
- **Bug #7** ✅ Stop-loss sin confirmar fill → SELL_PENDING → SELL en audit
- **Bug #8** ✅ Posiciones micro no vendibles → LOSS_TOTAL

### Bugs pendientes — orden de prioridad para el sábado:

**Bug #3 — Duplicados por posición abierta (PRIORIDAD 1)**
- Impacto económico confirmado: Madrid amplificada por bug, pérdida extra ~$0.30
- El check de duplicados mira órdenes abiertas, no posiciones ya llenadas
- En ciclo 7 se compró Madrid YES. En ciclo 8 el bot dijo "MANTENER" y luego la volvió a comprar
- Fix: antes de comprar, verificar posiciones abiertas en Data API (no solo órdenes)

**Bug #9 — Re-entrada tras stop-loss mismo ciclo (PRIORIDAD 2)**
- NYC YES vendido por SL en ciclo 4 y recomprado en el mismo ciclo
- Fix: set `sold_this_cycle` en manage_positions() → saltarlos en búsqueda de oportunidades

**Bug #11 — Ciclo extra al arrancar (PRIORIDAD 3)**
- El bot siempre ejecuta un primer ciclo al arrancar sin comprobar si el último fue reciente
- Causó doble posición en Chicago al añadir MIN_BET en Railway
- Fix: al arrancar, comprobar timestamp del último ciclo. Si fue hace menos de X horas → esperar

**Bug #10 — Default MIN_BET desalineado (PRIORIDAD 4)**
- bot.py dice 0.50, Railway tiene 1.00. Si se pierde la variable Railway → órdenes de $0.50-$0.99 fallarán
- Fix: cambiar default en bot.py de 0.50 a 1.00

**Bug #12 — Doble conteo de resueltas en resumen Telegram (PRIORIDAD 5)**
- manage_positions() añade resueltas a `keeping` Y incrementa `n_resolved`
- Una posición resuelta aparece como "🏁 resuelta" Y "✓ mantenida"
- Fix: excluir resueltas del contador `keeping`

**Bug #13 — /log intermitente por límite caracteres Telegram**
- Observado: HTTP Error 400 el 26 mar 16:06. Actualmente funciona
- Causa probable: cuando decisions.log supera 4096 caracteres
- Fix: paginar o truncar el mensaje

**Bug #14 — Telegram muestra precio límite, no fill real (PRIORIDAD 6)**
- Seattle: Telegram reportó 2¢ (precio límite), Polymarket confirmó fill a 4¢
- El PnL en /rendimiento usa precio límite → puede ser incorrecto en ambas direcciones
- Fix: usar fill_price real del order_id en lugar del precio límite enviado

---

## Observaciones estratégicas acumuladas

### Tensión de lógica de salida — casos reales

| Trade | Comportamiento bot | Resultado | ¿Fue correcto? |
|-------|-------------------|-----------|----------------|
| Ankara YES 11°C | Mantuvo hasta resolución | Subió a ~53¢, terminó en 0 | No — edge se volvió negativo a 53¢ |
| Chicago YES 66-67°F | Mantuvo hasta resolución | +619% | Sí — edge positivo hasta el final |
| Atlanta YES | Take-profit +63% | Capturó valor | Sí — aunque el mercado siguió algo más |
| Seattle YES | Mantuvo con edge alto | Reversión → stop-loss -17% | Parcial — edge era alto pero el precio cayó |
| Buenos Aires NO | Take-profit +52% | Capturó valor | Sí |
| Madrid YES | Ampliada (bug) → stop-loss | -$1.95 | No aplica — distorsionada por bug |

**Conclusión provisional:** Con 6 casos no hay suficiente evidencia estadística para cambiar la lógica de salida. Ankara y Chicago se contradicen directamente con el mismo comportamiento del bot. La solución correcta es un **monitor ligero intra-ciclo** que recalcule el edge cada 2-4 horas para posiciones vivas — no aumentar el TP ni añadir trailing. Cuando Ankara llegó a 53¢, el edge del modelo era negativo (mercado 53%, modelo 20%). El monitor lo habría detectado y habría vendido por re-evaluación sin cambiar el TP.

**Cuándo implementar:** Fase 2, después de validar con 30+ trades limpios.

### Problema estructural Open-Meteo vs Weather Underground
London ha producido dos pérdidas seguidas (-$2.25 y el NO 9°C de sesiones anteriores) porque Open-Meteo predice una temperatura y Weather Underground (fuente real de Polymarket) resuelve con otra. Pendiente de investigar. No apostar en London hasta resolver.

---

## Infraestructura Railway — aprendido esta sesión

### Acceso SSH (instalado en Windows de Pablo):
```
# Node.js ya instalado (v11.11.0)
# Railway CLI ya instalado (v4.35.0)
# Login ya hecho

# Para entrar al contenedor:
railway ssh

# IDs del proyecto:
# Project: d2338269-f031-4cb4-939f-5b910b4a4d47
# Environment: production
# Service: polymarket-bot
# Directorio trabajo: /app
```

### Archivos confirmados en Railway (/app):
| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| performance.json | 7.2KB | Todos los trades estructurados ✅ |
| audit.json | 67B | Vacío — forecast_vs_real=[] |
| decisions.log | 50KB | Log detallado por ciclo |
| trades.log | 6.1KB | Log compacto de órdenes |
| signals.json | 85KB | Señales traders |
| traders_db.json | 27KB | Base datos traders |

### PROBLEMA CRÍTICO: Todos los archivos se borran con cada deploy.
El contador de /rendimiento se reinicia porque performance.json desaparece. Solución: Railway Volume (Attach volume) — implementar el sábado como primera tarea.

---

## Observabilidad — problemas detectados

1. **"Órdenes" en /estado cuenta solo BUYs exitosas**, no ventas. Un ciclo con venta muestra "Órdenes: 0". Confunde al operador.
2. **"Exposición" y "Disp" en resumen de ciclo** — "Exposición" es la exposición inicial antes de compras, "Disp" es presupuesto sobrante tras seleccionar. No es el estado final de la cartera.
3. **Telegram vs Polymarket vs Railway** — Polymarket es la fuente de verdad del fill. Telegram es resumen útil, no referencia absoluta. Railway tiene el estado interno.
4. **Fill real vs precio límite** — Bug #14. Telegram muestra el precio límite de la orden, no el fill real ejecutado.
5. **Estado "delayed"** — Wellington y Miami entraron como "delayed". Se llenaron finalmente pero no hay trazabilidad de cuándo ni a qué precio exacto.

---

## Arquitectura de observabilidad — fases planificadas

### Fase 1 — Sábado (implementar):
- **Persistencia:** Railway Volume → archivos sobreviven deploys
- **trade_log.json:** expediente completo de cada trade con price_history, max/min visto, fill real, postmortem básico
- **missed_opportunities.json:** mercados con edge no comprados y motivo

### Fase 2 — Siguiente sesión coding:
- **Monitor ligero intra-ciclo:** cada 2-4h revisar posiciones vivas, recalcular edge, vender si negativo
- **postmortem.json:** análisis automático al resolver cada mercado

### Fase 3 — Cuando escale:
- **Dashboard web** (Python + Streamlit o HTML estático en GitHub Pages)
- Pantallas: resumen general, ciclos, trades, posiciones vivas, oportunidades perdidas, exportación para IA
- Telegram queda para alertas rápidas; dashboard para análisis completo

### Principios de diseño establecidos:
- El bot no se automodifica — solo se autoobserva y autodocumenta
- Cada decisión técnica debe ser compatible con el dashboard futuro
- No añadir complejidad sin evidencia de que resuelve un problema real

---

## Plan detallado sesión coding sábado

### ANTES de tocar código (15 min):
Entrar por SSH y descargar estado actual completo:
```
railway ssh
cat performance.json   → guardar en archivo local
cat decisions.log      → guardar en archivo local
cat trades.log         → guardar en archivo local
exit
```
Esto es la foto del sistema antes del sábado. Si algo falla, tenemos el estado anterior.

### Paso 1 — Instalar Claude Code (20 min):
```
npm install -g @anthropic-ai/claude-code
```
Conectar al repo polymarket-bot. Prueba simple de lectura de bot.py.

### Paso 2 — Railway Volume para persistencia (30 min):
Railway → proyecto → clic derecho → Attach volume → montar en `/app/data`.
Modificar bot.py para guardar JSONs en `/app/data/` en lugar de `/app/`.
A partir de ahí los datos sobreviven deploys.

### Paso 3 — trade_log.json estructura base (30 min):
Usar los datos reales de performance.json para poblar la estructura desde el inicio.
Campos mínimos: trade_id, market, entry (precio, shares, coste, edge, forecast, traders), price_history (precio en cada revisión), max_price_seen, min_price_seen, exit (motivo, fill_real, PnL), postmortem.

### Paso 4 — Bug #3 (45 min) — PRIORIDAD 1:
Antes de comprar, consultar posiciones abiertas en Data API.
Si ya existe posición abierta para ese match_key → no comprar, registrar como "duplicado_posición".

### Paso 5 — Bug #9 (30 min):
Set `sold_this_cycle` con match_keys vendidos en manage_positions().
Saltarlos en la búsqueda de oportunidades del mismo ciclo.

### Paso 6 — Bug #11 (20 min):
Al arrancar, leer timestamp del último ciclo en performance.json.
Si fue hace menos de (intervalo mínimo entre ciclos) horas → no ejecutar, esperar el siguiente scheduled.

### Paso 7 — Bug #10 (5 min):
Cambiar default MIN_BET de 0.50 a 1.00 en bot.py.

### Paso 8 — Bug #12 (15 min):
Excluir resueltas del contador `keeping` en manage_positions().

### Paso 9 — Bug #14 (20 min):
Usar fill_price real del order confirmado en lugar del precio límite enviado en reportes de Telegram.

### Paso 10 — Mejoras Telegram (30 min):
- Renombrar "Órdenes" → separar "Compras: X | Ventas: Y" en /estado
- Nuevo comando /info con bloque estructurado para análisis ChatGPT/Claude
- Aclarar "Exposición inicial" y "Presupuesto sobrante" en resumen de ciclo

### Paso 11 — verify_before_deploy.py v4 (30 min):
Tests para todos los fixes nuevos. Especialmente para Bug #3.

### Paso 12 — UN solo deploy al final:
```
python verify_before_deploy.py   ← todos los tests deben pasar
git add .
git commit -m "v10.4: persistencia + bugs #3 #9 #11 #10 #12 #14 + mejoras Telegram"
git push
```
Verificar en Railway que arranca correctamente y que NO ejecuta ciclo extra inmediato (fix Bug #11).

---

## Nuevo workflow con Claude Code (implementar el sábado)

**Workflow actual:**
```
Capturas Telegram/Polymarket
→ ChatGPT produce informe markdown
→ Pegas en claude.ai + CONTEXTO.md
→ Claude reescribe CONTEXTO.md entero
→ Descargas, sobrescribes en local, actualizas Proyecto Claude y GPT ChatGPT
```

**Workflow nuevo:**
```
Capturas Telegram/Polymarket
→ ChatGPT produce informe markdown
→ Abres terminal: claude
→ Pegas el informe
→ Claude Code lee CONTEXTO.md y archivos del repo directamente
→ Edita solo los párrafos que cambian
→ git push
→ Listo
```

Claude.ai sigue siendo el canal para charlas, análisis rápidos y sesiones sin código.

---

## Recordatorios importantes

**⚠️ NO hacer Deploy en Railway entre ciclos** — causa ciclo extra inesperado (Bug #11).

**Git paso a paso:**
```
cd C:\Projects\polymarket-bot
python verify_before_deploy.py
git add .
git commit -m "descripción"
git push
```

**Después de push:** Railway → Variables → verificar MIN_DAYS_AHEAD="-1" y MIN_BET="1.00".

**Región Railway:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403).

**Repo PRIVADO:** No compartir código, umbrales, ni traders tracked.

**Para activar órdenes reales:** railway.app → Variables → DRY_RUN="false".

---

## Ideas pendientes (no implementar hasta validar Fase 2)

1. **Monitor ligero intra-ciclo:** cada 2-4h revisar posiciones vivas y recalcular edge
2. **Aumentar frecuencia ciclos:** SCHEDULE_HOURS_UTC [8,16,23] → [6,10,14,18,22] en Railway
3. **Detectar ventas manuales:** posición que existía y ya no existe → registrar
4. **Horario de verano (DST):** CITY_UTC_OFFSETS usa offsets fijos. Impacto desde abril
5. **Weather Underground:** sustituir o complementar Open-Meteo para ciudades activas
6. **Dashboard completo:** Python + Streamlit o HTML. Fase 3 cuando haya 30+ trades
