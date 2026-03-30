# CLAUDE.md — Polymarket Weather Bot

## Protocolo obligatorio antes de trabajar

Leer también:

- `CONTEXTO.md`
- `OPERATIONS_PLAYBOOK.md`

`CONTEXTO.md` da el estado actual.
`OPERATIONS_PLAYBOOK.md` define el checklist de inicio/cierre, reglas de scoreboard y workflow multiagente.

## Qué es este proyecto
Bot automatizado de arbitraje meteorológico en Polymarket. Detecta mercados donde las previsiones meteorológicas profesionales (Open-Meteo) difieren de los precios del mercado, calcula apuestas con Half-Kelly, y ejecuta órdenes automáticamente.

## Stack
- **Lenguaje:** Python 3 (un solo archivo: bot.py ~3000 líneas)
- **Producción:** Railway (EU West Amsterdam), DRY_RUN=false
- **Mercados:** Polymarket CLOB API (py_clob_client)
- **Previsiones:** Open-Meteo API (coordenadas de aeropuertos)
- **Notificaciones:** Telegram bot (polling + inline keyboard)
- **Repo:** GitHub privado, deploy automático al push

## Arquitectura
El bot ejecuta ciclos cada 8h (08:00, 16:00, 23:00 UTC). Cada ciclo:
1. Limpia órdenes stale (>8h)
2. Gestiona posiciones activas (stop-loss -25%, take-profit +40%, re-evaluación)
3. Audita ventas pendientes (SELL_PENDING → SELL confirmado)
4. Escanea ~330 mercados de temperatura
5. Calcula edge con modelo probabilístico (distribución normal + sigma por días ahead)
6. Cruza con señales de traders de calidad
7. Dimensiona con Half-Kelly, respeta exposición máxima 40%
8. Ejecuta órdenes GTC limit

## Archivos principales
| Archivo | Función |
|---------|---------|
| `bot.py` | Script principal v10.4 (~3010 líneas) |
| `verify_before_deploy.py` | v4 — 51 tests de comportamiento |
| `trader_analyzer.py` | Genera signals.json diariamente |
| `find_traders.py` | Descubrimiento semanal de traders |
| `CONTEXTO.md` | Estado completo del proyecto (para claude.ai) |
| `OBSERVABILIDAD_Y_APRENDIZAJE.md` | Plan de instrumentación futura |

## Datos persistentes (Railway Volume en /app/data)
| Archivo | Función |
|---------|---------|
| `performance.json` | Historial de trades (BUY, SELL, SELL_PENDING, LOSS_TOTAL) |
| `audit.json` | Ventas pendientes + forecast vs real |
| `decisions.log` | Log detallado por ciclo |
| `trades.log` | Log compacto de órdenes |
| `signals.json` | Señales de traders actuales |
| `traders_db.json` | Base de datos de traders |

## Variables de entorno (Railway)
```
DRY_RUN="false"
BANKROLL="25.00"
MIN_DAYS_AHEAD="-1"      # -1 = automático por zona horaria
MIN_BET="1.00"
DATA_DIR="/app/data"      # Railway Volume mount
PK, FUNDER               # Credenciales Polymarket (secretas)
TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
```

## Configuración en código (defaults)
```python
MIN_EDGE = 7.0%           # Edge mínimo para entrar
STOP_LOSS_PCT = -25.0%    # Cortar pérdida
TAKE_PROFIT_PCT = +40.0%  # Asegurar ganancia
MAX_EXPOSURE_PCT = 40%    # Máximo del bankroll en posiciones
SELL_AGGRESSION = 0.02    # Bajar precio para fill rápido
Sigma: Día 0: 1.2 | Día 1: 1.5 | Día 2: 2.0 | Día 3: 2.5 | Día 4-5: 3.0
```

## Bugs corregidos (v10.3-v10.4)
- **#3** ✅ Duplicados: ahora consulta posiciones de Data API, no solo órdenes
- **#4** ✅ Resueltas contaban como exposición
- **#5** ✅ Zona horaria asiática (CITY_UTC_OFFSETS per-city)
- **#6** ✅ signals.json freshness 12h→26h
- **#7** ✅ SELL_PENDING → SELL en audit
- **#8** ✅ Posiciones micro → LOSS_TOTAL
- **#9** ✅ Re-entrada tras stop-loss mismo ciclo (sold_token_ids)
- **#10** ✅ MIN_BET default alineado con Railway
- **#11** ✅ Ciclo extra al arrancar (check timestamp último ciclo)
- **#12** ✅ Doble conteo resueltas en Telegram
- **#14** ✅ Precio límite vs fill en Telegram

## Bugs pendientes
- **#13** Telegram /log intermitente por límite 4096 caracteres
- **Weather Underground vs Open-Meteo:** Polymarket usa WU para resolver, no Open-Meteo. Ha causado pérdidas en London.

## Convenciones de código
- Archivo completo siempre, nunca parches parciales
- Tests en verify_before_deploy.py — TODOS deben pasar antes de push
- Un solo deploy al final de cada sesión
- Comentarios en español, código en inglés
- `_data_path()` para cualquier archivo persistente
- `track_trade()` para registrar BUY/SELL/LOSS_TOTAL en performance.json

## Pistas de código (líneas aproximadas en bot.py v10.4)
| Función | Línea aprox. |
|---------|-------------|
| `_data_path()` | 156 |
| `track_trade()` | 230 |
| `cmd_estado()` | 605 |
| `get_current_exposure()` | 1360 |
| `get_effective_bankroll()` | 1440 |
| `manage_positions()` | 1530 |
| `main(client)` | 2340 |
| scheduler / `__main__` | 2910 |

## Workflow de deploy
```bash
python verify_before_deploy.py   # 51/51 deben pasar
git add .
git commit -m "v10.X: descripción"
git push
# Verificar en Railway que arranca OK
# Verificar en Railway → Variables que MIN_DAYS_AHEAD="-1" y MIN_BET="1.00"
```

## Contexto del operador
- Pablo es principiante en programación. Explicar el porqué, no solo el cómo.
- Bankroll real: $25. All-time P&L: ~-$0.49
- El bot NO se automodifica — se autoobserva y autodocumenta
- Próximas fases: monitor intra-ciclo, postmortems, dashboard web
