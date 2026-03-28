# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 28 de marzo de 2026 (Sesión 19 — v10.4.3)
**Próxima sesión:** Análisis / Coding según necesidad

---

## Qué estamos construyendo

Un bot automatizado de arbitraje meteorológico en Polymarket. El bot detecta mercados donde las previsiones meteorológicas profesionales difieren de lo que creen los traders, calcula cuánto apostar usando gestión de riesgo matemática, ejecuta las órdenes automáticamente, y gestiona activamente las posiciones (stop-loss, take-profit, re-evaluación). Objetivo: que funcione 24/7 en la nube sin intervención humana.

**Cómo gana dinero:** Consulta la previsión meteorológica profesional (Open-Meteo, coordenadas exactas del aeropuerto), calcula la probabilidad real con un modelo matemático (distribución normal + redondeo a °C enteros), y cuando detecta que el precio del mercado está equivocado por más de 7%, apuesta en la dirección correcta.

**Bankroll configurado:** $25.00 en Railway.

**IMPORTANTE — Fuente de resolución:** Polymarket NO usa Open-Meteo — usa Weather Underground (wunderground.com). Esto ha causado pérdidas en London (2 veces). No apostar en London hasta resolver.

---

## Estado financiero (fin sesión 19, ~18:00 UTC 28 mar)

- **Posiciones activas:** Dallas YES, Chicago YES, Miami YES (~$6.37 valor actual)
- **Cash disponible:** ~$25.65
- **Portfolio total:** ~$32.03
- **All-time P&L:** ~-$0.49 (estimado, referencia: dashboard Polymarket)

Para estado exacto: usar `/info` + `/cartera` + `/rendimiento` en Telegram al inicio de cada sesión.

**Historial de trades completo (33 entradas) en Railway Volume `/app/data/performance.json`.**
Fusionado en sesión 19: backup local (ciclos 1-9) + Volume (ciclos 10-11).

---

## Qué hace el bot v10.4.3 (paso a paso)

Cada 8 horas (08:00, 16:00, 23:00 UTC) ejecuta un ciclo completo:

**0. Limpieza:** Cancela órdenes pendientes de más de 8 horas.

**0.5. Gestión activa (manage_positions):** Para cada posición abierta:
- ¿currentValue < $0.10? → LOSS_TOTAL
- ¿curPrice >= 0.98? → SKIP (resuelta, esperando pago)
- ¿PnL < -25%? → VENDER (stop-loss)
- ¿PnL > +40%? → VENDER (take-profit)
- Si no: recalcula edge. Si edge < -3% → VENDER (re-evaluación)
- Devuelve `sold_token_ids` para evitar re-entrada en el mismo ciclo

**0.6. Auditoría:** Convierte SELL_PENDING → SELL/SELL_FAILED según fills confirmados.

**1-5. Buscar oportunidades:** Escanea ~330 mercados, consulta previsiones, calcula edge, cruza con señales de traders, dimensiona con Half-Kelly, respeta exposición máxima 40%.

**6. Ejecución:** Órdenes GTC limit, registra en performance.json, notifica por Telegram.

**7. Registro de ciclo (v10.4.1+):** Guarda resumen en cycle_summary.json + append en cycles_history.jsonl.

**Al arrancar (v10.4.3):** Carga ciclos históricos desde cycles_history.jsonl (contador no se reinicia con deploys).

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false
**Versión activa:** v10.4.3

### Archivos del proyecto (tras limpieza sesión 19):
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.4.3 |
| `verify_before_deploy.py` | v5 — 99 tests de comportamiento |
| `trader_analyzer.py` | Genera signals.json diariamente |
| `find_traders.py` | Descubrimiento semanal de traders |
| `CLAUDE.md` | Instrucciones para Claude Code |
| `CONTEXTO.md` | Estado del proyecto (este archivo) |
| `OBSERVABILIDAD_Y_APRENDIZAJE.md` | Plan de fases futuras |
| `signals.json` | Señales traders actuales (cache local) |
| `traders_db.json` | Base de datos de traders (cache local) |
| `requirements.txt` | Dependencias Railway |
| `Procfile` | Arranque Railway |

### Datos persistentes (Railway Volume `/app/data`):
| Archivo | Función |
|---------|---------|
| `performance.json` | 33 trades (BUY/SELL/LOSS_TOTAL desde 25 mar) |
| `cycle_summary.json` | Último ciclo (se sobreescribe) |
| `cycles_history.jsonl` | Historial acumulativo de todos los ciclos |
| `audit.json` | Ventas pendientes + forecast vs real |
| `decisions.log` | Log detallado por ciclo |
| `trades.log` | Log compacto de órdenes |

### Configuración en Railway (variables de entorno):
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"
MIN_BET="1.00"
DATA_DIR="/app/data"
```

### Configuración en código (defaults bot.py v10.4.3):
```python
MIN_EDGE = 7.0%
STOP_LOSS_PCT = -25.0%
TAKE_PROFIT_PCT = +40.0%
MAX_EXPOSURE_PCT = 40%
MIN_BET = $1.00
Sigma: Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0
Schedule: 08:00, 16:00, 23:00 UTC
```

---

## Telegram — Comandos disponibles (v10.4.3)

| Comando | Qué muestra |
|---------|-------------|
| `/estado` | Versión, modo, bankroll, SL/TP, próximo ciclo, último ciclo |
| `/cartera` | Cash, posiciones vivas (ciudad+temp+fecha, precios en ¢), resueltas, muertas |
| `/log` | Resumen del último ciclo desde cycle_summary.json |
| `/detalle` | Todos los mercados evaluados, near misses, aceptados |
| `/rendimiento` | Portfolio real + historial trades (TP/SL/reeval, por ciudad) |
| `/ordenes` | Órdenes GTC pendientes con etiquetas legibles |
| `/traders` | Señales activas + coincidencias filtradas con cartera actual |
| `/info` | Bloque resumen completo para pegar en Claude/ChatGPT |
| `/forzar` | Ejecuta ciclo inmediatamente |
| `/modo` | Cambia DRY RUN ↔ REAL |

**Para iniciar una sesión de análisis en claude.ai:** pegar `/info` + `/cartera` + `/rendimiento`.

---

## BUGS — Estado completo

### Corregidos (v10.3 → v10.4.3):
- **#3** ✅ Duplicados: consulta Data API antes de comprar
- **#4** ✅ Resueltas contaban como exposición
- **#5** ✅ Zona horaria asiática (CITY_UTC_OFFSETS per-city)
- **#6** ✅ signals.json freshness 12h → 26h
- **#7** ✅ SELL_PENDING → SELL en audit
- **#8** ✅ Posiciones micro → LOSS_TOTAL
- **#9** ✅ Re-entrada tras stop-loss mismo ciclo
- **#10** ✅ MIN_BET default 0.50 → 1.00
- **#11** ✅ Ciclo extra al arrancar
- **#12** ✅ Doble conteo resueltas en Telegram
- **#13** ✅ Paginación automática >3800 chars (send_telegram_paged)
- **#14** ✅ Precio límite vs fill clarificado en Telegram

### Pendientes:
- **Weather Underground vs Open-Meteo:** Polymarket resuelve con WU, no Open-Meteo. Ha causado pérdidas en London. No apostar en London hasta investigar.

---

## Versionado — sistema establecido

- **v10.4.X** = misma lógica de trading, mejoras UI/Telegram/observabilidad
- **v10.5** = cambio en cómo el bot decide comprar/vender (lógica de trading)
- Ciclos y datos son continuos y acumulativos entre versiones 10.4.X
- Cada registro incluye la versión del bot que lo generó

### Historial de versiones:
| Versión | Fecha | Cambios principales |
|---------|-------|-------------------|
| v10.3 | 25 mar | Bugs #4-#8, zona horaria per-city, SELL_PENDING |
| v10.4 | 28 mar | Bugs #3,#9,#10,#11,#12,#14 + persistencia Volume |
| v10.4.1 | 28 mar | cycles_history.jsonl + cycle_summary.json |
| v10.4.2 | 28 mar | Rediseño Telegram + Bug #13 + helpers + /info |
| v10.4.3 | 28 mar | Ciclos persistentes + fixes post-deploy + limpieza repo |

---

## Historial de trades (33 entradas en performance.json)

| # | Ciudad | Lado | Coste | Resultado | PnL | Motivo | Fecha |
|---|--------|------|-------|-----------|-----|--------|-------|
| 1 | Chicago | YES | $2.38 | $7.72 | +$3.96 | Take-profit +85% | 25 mar |
| 2 | Ankara | YES | $2.50 | $0 | -$1.90 | LOSS_TOTAL | 26 mar |
| 3 | Atlanta | YES | $4.04 | $6.71 | +$2.60 | Take-profit +63% | 27 mar |
| 4 | London | NO | $2.50 | ~$0.22 | -$2.25 | Pérdida (WU vs OMA) | 26 mar |
| 5 | Ankara | NO | $2.50 | $4.24 | +$1.74 | WIN resolución | 26 mar |
| 6 | Chicago | YES | $2.50 | $11.59 | +$9.98 | WIN resolución +619% | 26 mar |
| 7 | Miami | YES | $2.20 | $0 | -$2.14 | LOSS_TOTAL | 26 mar |
| 8 | Shanghai | NO | $1.43 | $2.52 | +$1.09 | WIN resolución | 27 mar |
| 9 | Seattle | YES | $2.50 | $0.96 | -$0.42 | Stop-loss | 28 mar |
| 10 | Wellington | NO | $2.26 | $4.48 | +$2.24 | WIN resolución | 28 mar |
| 11 | Toronto | NO | $1.68 | $0 | -$1.71 | LOSS_TOTAL | 27 mar |
| 12 | Madrid | YES | $4.89 | $2.36 | -$1.95 | Stop-loss (bug #3) | 28 mar |
| 13 | Buenos Aires | NO | $1.62 | $2.21 | +$0.80 | Take-profit +52% | 28 mar |
| 14 | Dallas | YES | $2.50 | $2.44 | +$0.26 | Re-evaluación | 28 mar |
| — | Tel Aviv | NO | $2.46 | $0 | -$2.46 | LOSS_TOTAL | 28 mar |
| — | Paris | NO | $0.58 | $0 | -$0.58 | LOSS_TOTAL | 28 mar |
| — | Miami | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Chicago | YES | $2.50 | abierta | — | En cartera | 28 mar |
| — | Dallas | YES | $2.50 | abierta | — | En cartera | 28 mar |

---

## Ciclos ejecutados

| Ciclo | Hora UTC | Compras | Ventas | Nota |
|-------|----------|---------|--------|------|
| Extra | 25 mar 16:49 | Chicago YES | — | Bug #11 — deploy entre ciclos |
| 2 | 25 mar 23:00 | — | Chicago YES TP +85% | OK |
| 3 | 26 mar 08:00 | Ankara YES/NO, London NO, Atlanta YES | — | OK |
| 4 | 26 mar 16:00 | Chicago YES, Atlanta YES, Miami YES, Shanghai NO | — | OK |
| 5 | 26 mar 23:00 | Seattle YES, Buenos Aires NO | — | OK |
| 6 | 27 mar 08:00 | — | Atlanta YES TP +63% | OK |
| 7 | 27 mar 16:00 | Madrid YES, Chicago YES 40-41°F, Toronto NO | — | OK |
| 8 | 27 mar 23:00 | Madrid YES (BUG #3), Wellington NO | Seattle YES SL | Madrid amplificada |
| 9 | 28 mar 08:00 | Dallas YES, Miami YES | Madrid YES SL, Buenos Aires TP | OK |
| 10 | 28 mar ~11:01 | Miami YES | — | Deploy v10.4 — Bug #3 bloqueó duplicados ✅ |
| 11 | 28 mar 16:00 | Chicago YES, Dallas YES | Dallas reeval, Tel Aviv/Paris LOSS_TOTAL | v10.4.2 |
| 12+ | 28 mar 23:00+ | — | — | v10.4.3 activo, cycles_history.jsonl acumula |

---

## Observaciones estratégicas

### Open-Meteo vs Weather Underground
London ha producido pérdidas seguidas porque Open-Meteo predice una temperatura y Weather Underground (fuente real de Polymarket) resuelve con otra. **No apostar en London hasta resolver.**

### Lógica de salida — casos reales
Con ~15 trades cerrados no hay suficiente evidencia estadística para cambiar la lógica. La solución correcta es un monitor ligero intra-ciclo (Fase 2, cuando haya 30+ trades limpios).

---

## Arquitectura de observabilidad — fases

### Fase 1 — ✅ Implementada:
- Persistencia Railway Volume, cycles_history.jsonl, cycle_summary.json ✅
- Bugs #3-#14 corregidos, 99 tests ✅
- Claude Code instalado y funcional ✅

### Fase 1.5 — ✅ Implementada (sesión 19):
- Rediseño completo Telegram (7 botones + /info) ✅
- Bug #13 paginación ✅
- Ciclos persistentes entre deploys ✅
- Limpieza del repo (17 archivos eliminados) ✅
- performance.json fusionado con historial completo (33 trades) ✅

### Fase 2 — Cuando haya 30+ trades limpios:
- Monitor ligero intra-ciclo: revisar posiciones cada 2-4h
- postmortem.json: análisis automático al resolver cada mercado

### Fase 3 — Cuando escale:
- Dashboard web (Streamlit o HTML estático)

---

## Infraestructura

### Railway:
- **Región:** EU West (Amsterdam) — NO cambiar a US (geobloqueo 403)
- **Volume:** Montado en `/app/data` — archivos persisten entre deploys
- **Variable DATA_DIR:** `/app/data`

### Acceso SSH:
```bash
railway ssh                          # shell interactivo
railway ssh "comando"                # comando directo
railway ssh "ls /app/data/"         # ver archivos del volume
```

### Claude Code:
- Instalado en `C:\Projects\polymarket-bot`
- Para tests: `$env:PYTHONIOENCODING="utf-8"` antes de ejecutar

### Workflow de deploy:
```bash
python verify_before_deploy.py   # 99/99 deben pasar
git add .
git commit -m "v10.X.X: descripción"
git push
# Railway despliega automáticamente
# Verificar variables: DATA_DIR, MIN_BET, DRY_RUN
```

---

## Ideas pendientes (no implementar hasta validar)

1. **Monitor ligero intra-ciclo:** cada 2-4h revisar posiciones vivas
2. **Weather Underground:** sustituir o complementar Open-Meteo
3. **Horario de verano (DST):** CITY_UTC_OFFSETS usa offsets fijos — impacta desde abril
4. **Dashboard web:** Fase 3 cuando haya 30+ trades
5. **Migrar signals.json y traders_db.json al Volume**
6. **Aumentar frecuencia ciclos:** [8,16,23] → [6,10,14,18,22]
