# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 28 de marzo de 2026 (Sesiones 17-18 — v10.4 → v10.4.1)
**Próxima sesión:** Coding — rediseño Telegram con Claude Code

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta.

**Bankroll configurado:** $25.00 en Railway.

**IMPORTANTE — Fuente de resolución:** Polymarket NO usa Open-Meteo — usa Weather Underground (wunderground.com). Esto ha causado pérdidas en London (2 veces). Pendiente de investigar e incorporar WU como fuente de validación.

**Modelo de Claude recomendado:** Sesiones de coding → Opus. Observación/análisis → Sonnet.

---

## Estado financiero actual (ciclo 9, 08:00 UTC 28 mar)

- **All-time P&L: -$0.49** (Polymarket, confirmado pre-sesión 17)
- **Cash disponible: $34.65** (pre-sesión 17)
- **Portfolio total: $37.73** (pre-sesión 17)

**Nota:** Estos datos son de antes de la sesión 17. El bot ha ejecutado ciclos 10+ durante la sesión. Consultar Polymarket para datos actuales. A partir de v10.4.1, cycles_history.jsonl registra cada ciclo automáticamente.

**Posiciones activas conocidas (ciclo 9 + compras ciclo 10):**
Dallas YES 58-59°F Mar28, Miami YES 86-87°F Mar28, Tel Aviv NO 24°C Mar28, Paris YES 10°C Mar28, Paris NO 11°C Mar28.

**Pendientes de canjear:** Toronto NO 0°C Mar27, Chicago YES 40-41°F Mar27.

---

## Qué hace el bot v10.4.1 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas.

**0.5. Gestión activa (manage_positions):** Para cada posición abierta:
- ¿currentValue < $0.10? → LOSS_TOTAL (excluida de gestión)
- ¿curPrice >= 0.98? → SKIP (resuelta, esperando pago). v10.4: NO cuenta como "mantenida"
- ¿PnL < -25%? → VENDER (stop-loss)
- ¿PnL > +40%? → VENDER (take-profit)
- Si no: recalcula edge con Open-Meteo. Si edge < -3% → VENDER (re-evaluación)
- Cada venta se registra como SELL_PENDING → confirmada como SELL por audit
- v10.4: devuelve `sold_token_ids` para evitar re-entrada en el mismo ciclo

**0.6. Auditoría:** Convierte SELL_PENDING → SELL/SELL_FAILED según fills confirmados.

**1. MIN_DAYS_AHEAD per-city:** Cada ciudad evaluada según su zona horaria local.

**2-4. Buscar oportunidades:** Escanea ~330 mercados, consulta previsiones, calcula edge, cruza con señales de traders de calidad.
- v10.4: antes de comprar, consulta Data API para posiciones ya llenadas (no solo órdenes)
- v10.4: salta posiciones vendidas este ciclo (sold_this_cycle)

**5. Control de riesgo:** Exposición máxima 40% del bankroll efectivo, dimensionado con Half-Kelly.

**6. Ejecución:** Coloca órdenes GTC limit, registra en performance.json, notifica por Telegram.

**7. Registro de ciclo (v10.4.1):** Guarda resumen en cycle_summary.json + append en cycles_history.jsonl.

**Al arrancar (v10.4):** Comprueba timestamp del último ciclo. Si < 3h → espera scheduler (Bug #11 fix).

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false
**Versión activa:** v10.4.1

### Archivos principales:
| Archivo | Ubicación | Función |
|---------|-----------|---------|
| `bot.py` | /app (código) | Script principal v10.4.1 (3054 líneas) |
| `verify_before_deploy.py` | /app (código) | v4 — 56 tests de comportamiento |
| `CLAUDE.md` | repo local | Instrucciones para Claude Code |
| `performance.json` | /app/data (Volume) | Historial BUYs, SELLs, LOSS_TOTALs |
| `cycle_summary.json` | /app/data (Volume) | Último ciclo (se sobreescribe) |
| `cycles_history.jsonl` | /app/data (Volume) | Historial acumulativo de TODOS los ciclos |
| `audit.json` | /app/data (Volume) | Ventas pendientes + forecast vs real |
| `decisions.log` | /app/data (Volume) | Log detallado por ciclo |
| `trades.log` | /app/data (Volume) | Log compacto de órdenes |
| `signals.json` | /app (se regenera) | Señales traders actuales |
| `traders_db.json` | /app (se regenera) | 34 traders registrados |

### Configuración en bot.py v10.4.1:
```python
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BANKROLL = float(os.getenv("BANKROLL", "15.00"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "7.0"))
MIN_BET = float(os.getenv("MIN_BET", "1.00"))   # v10.4: default alineado con Railway
MAX_BET_PCT = float(os.getenv("MAX_BET_PCT", "0.10"))
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.40"))
MIN_DAYS_AHEAD = int(os.getenv("MIN_DAYS_AHEAD", "-1"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-25.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "40.0"))
SCHEDULE_HOURS_UTC = [8, 16, 23]
DATA_DIR = os.getenv("DATA_DIR", "")  # v10.4: Railway Volume
# Sigma: Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0
```

### Variables de Railway (estado actual):
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"
MIN_BET="1.00"
DATA_DIR="/app/data"
```

---

## Historial completo de trades (v10.3+, desde 25 marzo)

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

---

## Ciclos ejecutados (v10.3 → v10.4.1)

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
| 10 | 28 mar ~11:01 | Miami YES (legít.) | — | Deploy v10.4 — Bug #3 bloqueó duplicados ✅ |
| 11+ | 28 mar 16:00+ | — | — | v10.4.1 — cycles_history.jsonl registra |

**A partir del ciclo 11+, cada ciclo queda registrado automáticamente en cycles_history.jsonl.**

---

## BUGS — Estado completo

### Bugs corregidos en v10.4 (sesión 17):
- **Bug #3** ✅ Duplicados por posición abierta → `existing_position_tokens` consulta Data API. Confirmado: decisions.log mostró "YA HAY POSICIÓN ABIERTA" para Dallas, Paris×2, Tel Aviv en ciclo 10
- **Bug #9** ✅ Re-entrada tras stop-loss → `sold_token_ids` devuelto por manage_positions(), usado como `sold_this_cycle` en main()
- **Bug #11** ✅ Ciclo extra al arrancar → comprueba timestamp último trade, skip si < 3h
- **Bug #10** ✅ MIN_BET default 0.50 → 1.00
- **Bug #12** ✅ Resueltas no cuentan como "mantenidas" → excluidas de `keeping`
- **Bug #14** ✅ Telegram clarifica "precio límite" vs fill real

### Bugs corregidos en v10.3:
- **Bug #4** ✅ Resueltas contaban como exposición → excluidas con curPrice >= 0.98
- **Bug #5** ✅ Zona horaria asiática → CITY_UTC_OFFSETS per-city. Costó ~$5.16
- **Bug #6** ✅ signals.json vacío → freshness 12h→26h
- **Bug #7** ✅ Stop-loss sin confirmar fill → SELL_PENDING → SELL en audit
- **Bug #8** ✅ Posiciones micro no vendibles → LOSS_TOTAL

### Bugs pendientes:

**Bug #13 — /log intermitente por límite caracteres Telegram (BAJA)**
- Observado: HTTP Error 400 el 26 mar 16:06. Actualmente funciona
- Causa probable: cuando decisions.log supera 4096 caracteres
- Fix: paginar o truncar el mensaje

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

**Conclusión provisional:** Con 6 casos no hay suficiente evidencia estadística para cambiar la lógica de salida. La solución correcta es un **monitor ligero intra-ciclo** que recalcule el edge cada 2-4 horas para posiciones vivas. Cuando Ankara llegó a 53¢, el edge del modelo era negativo. El monitor lo habría detectado y habría vendido por re-evaluación.

**Cuándo implementar:** Fase 2, después de validar con 30+ trades limpios.

### Problema estructural Open-Meteo vs Weather Underground
London ha producido dos pérdidas seguidas (-$2.25 y el NO 9°C de sesiones anteriores) porque Open-Meteo predice una temperatura y Weather Underground (fuente real de Polymarket) resuelve con otra. Pendiente de investigar. No apostar en London hasta resolver.

---

## Infraestructura

### Railway:
- **Región:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403)
- **Volume:** Montado en `/app/data` — archivos persisten entre deploys
- **Variable DATA_DIR:** `/app/data` — todos los archivos de datos usan _data_path()

### Acceso SSH:
```
# Node.js instalado (v11.11.0), Railway CLI (v4.35.0), login hecho
railway ssh
# Directorio trabajo: /app (código) | /app/data (datos persistentes)
```

### Claude Code:
- Instalado via `irm https://claude.ai/install.ps1 | iex`
- PATH: `$env:PATH += ";$env:USERPROFILE\.local\bin"`
- Funciona en VS Code terminal integrada. Versión 2.1.86
- Para Windows: `$env:PYTHONIOENCODING="utf-8"` antes de ejecutar tests

### Persistencia — qué sobrevive deploys:
| Archivo | Ubicación | ¿Persiste? |
|---------|-----------|------------|
| performance.json | /app/data | ✅ Sí (Volume) |
| cycles_history.jsonl | /app/data | ✅ Sí (Volume) |
| cycle_summary.json | /app/data | ✅ Sí (Volume) |
| audit.json | /app/data | ✅ Sí (Volume) |
| decisions.log | /app/data | ✅ Sí (Volume) |
| trades.log | /app/data | ✅ Sí (Volume) |
| signals.json | /app | ❌ Se regenera (OK) |
| traders_db.json | /app | ❌ Se regenera (OK) |

---

## Versionado — sistema establecido

### Reglas:
- **v10.4.X** = misma lógica de trading, mejoras de observabilidad/UI/Telegram
- **v10.5** = cambio en cómo el bot decide comprar/vender (lógica de trading)
- El historial de datos (cycles_history.jsonl, performance.json) es continuo y acumulativo
- Cada registro incluye la versión del bot que lo generó
- Los datos NUNCA se borran con un cambio de versión

### Historial de versiones:
| Versión | Fecha | Cambios principales |
|---------|-------|-------------------|
| v10.3 | 25 mar | Bugs #4-#8, zona horaria per-city, SELL_PENDING |
| v10.4 | 28 mar | Bugs #3,#9,#10,#11,#12,#14 + persistencia Volume |
| v10.4.1 | 28 mar | cycles_history.jsonl + cycle_summary.json |

---

## Arquitectura de observabilidad — fases

### Fase 1 — ✅ Implementada (sesiones 17-18):
- **Persistencia:** Railway Volume → archivos sobreviven deploys ✅
- **cycles_history.jsonl:** historial acumulativo de cada ciclo ✅
- **cycle_summary.json:** último ciclo para consulta rápida ✅
- **Bug fixes:** 6 bugs corregidos, todos verificados con 56 tests ✅
- **Claude Code:** instalado y funcional ✅

### Fase 1.5 — Próxima sesión (con Claude Code):
- **Rediseño Telegram:** 7 botones rediseñados + botón /info
  - /estado: Portfolio real + posiciones con % + timing
  - /cartera: Ciudad+temp+fecha, precios en centavos
  - /log: Resumen legible desde cycle_data
  - /detalle: Dump técnico por categoría
  - /rendimiento: Portfolio real + breakdown
  - /ordenes: Ciudad+temp+fecha legibles
  - /traders: Coincidencias con posiciones + consenso
  - /info (NUEVO): Bloque markdown para ChatGPT/Claude
- **Helpers:** _parse_position_label, _get_portfolio_and_positions

### Fase 2 — Cuando haya 30+ trades limpios:
- **Monitor ligero intra-ciclo:** cada 2-4h revisar posiciones vivas, recalcular edge
- **postmortem.json:** análisis automático al resolver cada mercado

### Fase 3 — Cuando escale:
- **Dashboard web** (Python + Streamlit o HTML estático en GitHub Pages)
- Telegram queda para alertas rápidas; dashboard para análisis completo

---

## Recordatorios importantes

**⚠️ Deploy seguro:** Bug #11 evita ciclo extra si último ciclo < 3h. Pero mejor no hacer deploy justo cuando toca un ciclo programado.

**Git paso a paso:**
```
cd C:\Projects\polymarket-bot
python verify_before_deploy.py
git add .
git commit -m "descripción"
git push
```

**Después de push:** Railway → Variables → verificar que todo sigue igual (DATA_DIR, MIN_BET, etc.).

**Región Railway:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403).

**Repo PRIVADO:** No compartir código, umbrales, ni traders tracked.

**Para activar órdenes reales:** railway.app → Variables → DRY_RUN="false".

**Verificar estado tras deploy:**
```
railway ssh
ls -la /app/data/
cat /app/data/cycle_summary.json
wc -l /app/data/cycles_history.jsonl
```

---

## Ideas pendientes (no implementar hasta validar)

1. **Monitor ligero intra-ciclo:** cada 2-4h revisar posiciones vivas y recalcular edge
2. **Aumentar frecuencia ciclos:** SCHEDULE_HOURS_UTC [8,16,23] → [6,10,14,18,22] en Railway
3. **Detectar ventas manuales:** posición que existía y ya no existe → registrar
4. **Horario de verano (DST):** CITY_UTC_OFFSETS usa offsets fijos. Impacto desde abril
5. **Weather Underground:** sustituir o complementar Open-Meteo para ciudades activas
6. **Dashboard completo:** Python + Streamlit o HTML. Fase 3 cuando haya 30+ trades
7. **Migrar signals.json y traders_db.json al Volume** (no usan _data_path, se regeneran solos — baja prioridad)
