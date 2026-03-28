# CONTEXTO DEL PROYECTO — Bot Polymarket

**Última actualización:** 28 de marzo de 2026 (Sesión 19 — v10.4.5)
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

## Qué hace el bot v10.4.5 (paso a paso)

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

**6. Ejecución:** Órdenes GTC limit, registra en `performance.json`, sincroniza `postmortem.json` y notifica por Telegram.

**7. Registro de ciclo (v10.4.1+):** Guarda resumen en cycle_summary.json + append en cycles_history.jsonl.

**Al arrancar (v10.4.3+):** Carga ciclos históricos desde cycles_history.jsonl (contador no se reinicia con deploys).

**Zona horaria por ciudad (v10.4.5):** Ya no usa offsets manuales; usa zonas IANA reales con `ZoneInfo` para que DST cambie automáticamente sin tocar el código en marzo/octubre.

**Postmortem base (v10.4.5):** Mantiene `postmortem.json` sincronizado con `BUY`, `SELL_PENDING → SELL/SELL_FAILED`, `LOSS_TOTAL` y `RESOLVED_WIN` para poder analizar cierres y resoluciones con datos estructurados.

---

## Estado actual del código

**Repositorio:** https://github.com/PabloGmez2K/polymarket-bot (PRIVADO)
**Ubicación local:** `C:\Projects\polymarket-bot`
**Producción:** Railway — Online, EU West Amsterdam, MODO REAL, DRY_RUN=false
**Versión activa:** v10.4.5

### Archivos del proyecto (tras limpieza sesión 19):
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.4.5 |
| `verify_before_deploy.py` | v7 — 146 tests de comportamiento |
| `trader_analyzer.py` | Genera `signals.json` diariamente en Volume |
| `find_traders.py` | Descubrimiento semanal de traders y mantenimiento de `traders_db.json` en Volume |
| `CLAUDE.md` | Instrucciones para Claude Code |
| `CONTEXTO.md` | Estado del proyecto (este archivo) |
| `HISTORIAL_SESIONES.md` | Bitácora append-only de sesiones e hitos reconstruidos desde Git |
| `OBSERVABILIDAD_Y_APRENDIZAJE.md` | Plan de fases futuras |
| `signals.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `traders_db.json` | Copia bootstrap local; producción usa la copia persistente del Volume |
| `requirements.txt` | Dependencias Railway |
| `Procfile` | Arranque Railway |

### Datos persistentes (Railway Volume `/app/data`):
| Archivo | Función |
|---------|---------|
| `performance.json` | 33 trades (BUY/SELL/LOSS_TOTAL desde 25 mar) |
| `postmortem.json` | Postmortems estructurados de apertura/cierre por mercado |
| `signals.json` | Señales de traders activas usadas por el bot en producción |
| `traders_db.json` | Base de datos persistente de traders descubiertos/calificados |
| `trader_history.json` | Historial auxiliar del pipeline de traders |
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

### Configuración en código (defaults bot.py v10.4.5):
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

## Telegram — Comandos disponibles (v10.4.5)

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
| `/postmortem` | Resumen rápido de abiertas/cierres desde `postmortem.json` |
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
| v10.4.4 | 28 mar | Ajuste temporal manual de DST |
| v10.4.5 | 28 mar | `ZoneInfo` + zonas IANA reales + `.claude/` fuera del repo + `postmortem.json` base + trader data al Volume + `/postmortem` |

---

## Trazabilidad por herramienta

**Objetivo:** este proyecto se trabaja con varias herramientas. A partir de ahora, cada sesión debe dejar anotado qué agente hizo qué, qué detectó, y qué corrigió a otro agente si aplica.

### Convención a seguir en futuras sesiones

- **ChatGPT / Claude.ai:** análisis, estrategia, revisión de contexto, ideas y validación conceptual.
- **Codex:** cambios de código en local, revisión crítica del repo, corrección de implementaciones previas, validación técnica y tests.
- **Claude Code:** edición/coding en local cuando se use explícitamente para implementar cambios.

### Regla de documentación

- Cada sesión importante debe añadir una nota breve indicando:
- `Herramienta usada`
- `Qué hizo`
- `Qué problemas detectó`
- `Qué corrigió de trabajo previo`
- `Qué quedó pendiente`

### Plantilla fija — Registro de sesión

Usar esta plantilla al cerrar cada sesión relevante:

```md
### Sesión XX — Registro multi-herramienta

- **Fecha:** YYYY-MM-DD
- **Versión activa al cerrar:** v10.X.X
- **Objetivo de la sesión:** ...

- **ChatGPT / Claude.ai:**
  Análisis / estrategia / contexto aportado:
  ...

- **Claude Code:**
  Cambios implementados:
  ...

- **Codex:**
  Revisión crítica / cambios / validaciones:
  ...

- **Problemas detectados en trabajo previo:**
  ...

- **Correcciones aplicadas en esta sesión:**
  ...

- **Tests / verificaciones ejecutadas:**
  ...

- **Pendientes para la próxima sesión:**
  ...

- **Estado final:**
  versión ..., tests ..., deploy sí/no, observaciones ...
```

### Regla práctica de uso

- Si solo participa una herramienta, se rellena solo su bloque y se dejan las demás como `No usado en esta sesión`.
- Si una herramienta corrige o valida trabajo de otra, dejarlo explícito en `Problemas detectados en trabajo previo` y `Correcciones aplicadas en esta sesión`.
- Si hay cambios en Railway, Volume, Telegram o datos históricos, anotarlo también en el bloque `Estado final`.
- Antes de cada push relevante, actualizar `CONTEXTO.md` y `HISTORIAL_SESIONES.md` si la sesión cambió estado, arquitectura, datos persistentes, comandos Telegram, workflow o trazabilidad multi-agente.

### Sesión 19 — Registro multi-herramienta

- **Claude Code:** implementó v10.4.2, v10.4.3 y v10.4.4; rediseño Telegram, paginación, `/info`, persistencia de ciclos, limpieza del repo y un fix manual de DST basado en offsets estáticos.
- **Codex:** revisó críticamente esa secuencia y detectó dos deudas importantes: el fix de DST seguía siendo frágil por usar offsets manuales, y `.claude/settings.local.json` había quedado versionado por error.
- **Codex:** corrigió el enfoque de DST en `bot.py` migrando a `ZoneInfo` + `CITY_TIMEZONES` con zonas IANA reales (`v10.4.5`), actualizó `verify_before_deploy.py`, sacó `.claude/settings.local.json` del control de versiones sin borrar la copia local, reparó manualmente una entrada truncada en `performance.json` de Railway, implementó la capa base de `postmortem.json`, movió `signals.json` / `traders_db.json` / `trader_history.json` al flujo persistente de Volume con bootstrap automático y añadió `/postmortem` para inspección rápida desde Telegram.
- **Estado final de la sesión 19:** versión activa `v10.4.5`, tests `146/146`, repo listo para deploy, DST robusto para futuros cambios de horario, observabilidad base de postmortem lista para crecer y pipeline de traders persistente en Volume.

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
- Bugs #3-#14 corregidos, 146 tests ✅
- Claude Code instalado y funcional ✅

### Fase 1.5 — ✅ Implementada (sesión 19):
- Rediseño completo Telegram (7 botones + /info) ✅
- Bug #13 paginación ✅
- Ciclos persistentes entre deploys ✅
- Limpieza del repo (17 archivos eliminados) ✅
- performance.json fusionado con historial completo (33 trades) ✅
- DST robusto con `ZoneInfo` y zonas IANA reales ✅
- `postmortem.json` base implementado ✅
- `signals.json`, `traders_db.json` y `trader_history.json` persistidos en Volume ✅
- `/postmortem` disponible para inspección rápida desde Telegram ✅

### Fase 2 — Cuando haya 30+ trades limpios:
- Monitor ligero intra-ciclo: revisar posiciones cada 2-4h
- Ampliar `postmortem.json` con análisis más rico al resolver cada mercado

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

### Trabajo multi-agente:
- `CONTEXTO.md` debe mantenerse como foto actual compartida entre ChatGPT, Codex, Claude.ai y Claude Code.
- `HISTORIAL_SESIONES.md` debe usarse como memoria histórica append-only para no perder qué sesiones ya existieron y qué se corrigió en cada etapa.
- Antes de cada push relevante, actualizar ambos archivos si cambió algo material del sistema.
- Antes de cerrar una sesión relevante, anotar qué herramienta hizo los cambios finales y qué corrigió de sesiones previas.

### Workflow de deploy:
```bash
python verify_before_deploy.py   # 146/146 deben pasar
# actualizar CONTEXTO.md si cambió el estado actual
# actualizar HISTORIAL_SESIONES.md si hubo una sesión/hito nuevo
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
3. **Dashboard web:** Fase 3 cuando haya 30+ trades
4. **Enriquecer `/postmortem`:** filtros por ciudad/estado/últimos N cierres
5. **Ampliar `postmortem.json`** con más campos de forecast y comparación resolución vs decisión
6. **Aumentar frecuencia ciclos:** [8,16,23] → [6,10,14,18,22]
