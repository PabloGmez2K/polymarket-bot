# OBSERVABILIDAD_Y_APRENDIZAJE.md

## Objetivo

Convertir el bot en un sistema que no solo opere, sino que también genere **memoria útil sobre sí mismo**.

La meta no es que el bot se autoajuste solo en producción, sino que acumule información estructurada y cada vez más valiosa para:

- entender qué hizo y por qué
- medir qué funcionó y qué no
- detectar oportunidades perdidas
- comparar estrategias alternativas
- preparar mejores sesiones de coding con Claude Opus / Sonnet
- mejorar la lógica, la operativa y la observabilidad con evidencia real

La idea central es esta:

**el sistema debe autoobservarse, autodocumentarse y autoresumirse.**

---

## Principios

### 1. No guardar muchos datos por guardar
No queremos ruido. Queremos datos que luego permitan responder preguntas útiles.

### 2. Separar ejecución y aprendizaje
- La capa de trading ejecuta.
- La capa de observabilidad registra.
- La capa de análisis resume y genera postmortems.

### 3. No autooptimizar en producción
El bot no debe cambiar la estrategia por su cuenta.
Debe generar evidencia para que el piloto + Claude decidan cambios.

### 4. Registrar también lo que no hizo
No solo importa qué trades ejecutó.
También importa qué oportunidades dejó pasar y por qué.

### 5. Toda decisión importante debe poder explicarse después
Si no se puede reconstruir:
- qué vio el bot
- qué decidió
- por qué lo decidió
- qué pasó después

entonces falta observabilidad.

---

## Contrato de fuentes del sistema

Para que el bot pueda aprender de sí mismo sin mezclar capas, el proyecto fija este contrato:

- **Open-Meteo decide**
- **NOAA mide**
- **Weather Underground resuelve**

### 1. Open-Meteo decide

Open-Meteo es la fuente de forecast operativo.

Se usa para:

- estimar `forecast_max`
- calcular probabilidad modelo
- calcular `edge`
- dimensionar posición
- decidir si una oportunidad pasa a `BUY`, `CANARY` o `SHADOW`

Esto significa que la ejecución real del bot depende del forecast de Open-Meteo, no de NOAA.

### 2. NOAA mide

NOAA es la capa observada del sistema.

Se usa para:

- poblar `observed_vs_forecast`
- medir `MAE` y `bias`
- contar cobertura por ciudad
- decidir cuándo una ciudad es `interpretable`
- construir señales `NOAA-verificado`
- validar joins tipo `shadow -> observed`

Un **caso NOAA** es una fila `city + date` en `observed_vs_forecast`.

NOAA no decide entradas. NOAA sirve para medir después qué tan bien está aprendiendo el sistema.

### 3. Weather Underground resuelve

Weather Underground es la referencia de settlement final de Polymarket.

Se usa para entender:

- qué fuente manda realmente al resolver mercados
- por qué una capa observada puede ser útil sin ser settlement exacto
- qué discrepancias de fuente pueden seguir generando pérdidas aunque Open-Meteo y NOAA parezcan razonables

### 4. Qué no comparar directamente

Para evitar métricas engañosas:

- no tratar `NOAA` como si fuera la fuente de entrada del bot
- no tratar `NOAA` como si fuera settlement final de Polymarket
- no tratar el histórico total de `postmortem` como equivalente a `NOAA-verificado`
- no mezclar `forecast operativo`, `observed proxy` y `settlement final` en una misma métrica sin etiquetarlo explícitamente

### 5. Regla práctica de lectura

- si la pregunta es **“por qué compró”** → mirar Open-Meteo
- si la pregunta es **“qué tan bien estamos midiendo”** → mirar NOAA
- si la pregunta es **“por qué se resolvió así”** → mirar Weather Underground / settlement real

Este contrato debe mantenerse visible en docs, dashboard y Telegram para que el sistema pueda aprender con semántica estable.

---

## Las tres memorias del sistema

### A. Memoria operativa
Qué hizo realmente el bot:
- ciclos
- órdenes
- fills
- posiciones
- ventas
- resultados

### B. Memoria explicativa
Por qué hizo lo que hizo:
- edge
- forecast
- probabilidad modelo
- probabilidad mercado
- filtros
- Kelly
- presupuesto
- motivo de compra / no compra / venta / mantenimiento

### C. Memoria contrafactual
Qué habría pasado con otra lógica:
- TP fijo
- hold to resolution
- venta parcial
- trailing stop
- monitor de salidas más frecuente
- otras reglas de gestión

Sin estas tres memorias, no hay retroalimentación inteligente.

---

## Qué debe registrar el sistema

## 1. Registro de ciclo

Cada ciclo debe quedar guardado como una unidad completa.

### Campos mínimos
- `cycle_id`
- `timestamp_utc`
- `bot_version`
- `strategy_version`
- `mode` (real / paper)
- `bankroll_cap`
- `cash_start`
- `active_positions_start`
- `resolved_waiting_claim_start`
- `signals_loaded`
- `markets_evaluated`
- `markets_accepted`
- `near_misses`
- `orders_submitted`
- `orders_filled`
- `sales_executed`
- `cities_forecasted`
- `forecast_source`
- `traders_snapshot`
- `notes`

### Objetivo
Poder reconstruir:
- qué veía el bot al inicio del ciclo
- cuánto capital tenía realmente
- qué cambió durante el ciclo
- si una anomalía fue de mercado, de datos o de lógica

---

## 2. Evaluación completa de mercados

El bot debe registrar **todos los mercados evaluados**, no solo los que termina comprando.

### Campos mínimos
- `cycle_id`
- `market_id`
- `market_name`
- `city`
- `target_date`
- `side`
- `market_price`
- `forecast_value`
- `model_probability`
- `market_probability`
- `edge`
- `ev`
- `kelly_fraction`
- `suggested_size`
- `liquidity_ok`
- `trader_confirmation`
- `filter_result`
- `final_decision`
- `decision_reason`

### Valores posibles de `final_decision`
- `filtered_out`
- `near_miss`
- `accepted`
- `selected`
- `bought`
- `skipped_capital`
- `skipped_kelly`
- `skipped_duplicate`
- `skipped_other`

### Objetivo
Poder responder:
- qué oportunidades había realmente
- cuáles eran buenas y no entraron
- qué filtros están bloqueando demasiado
- qué edge funciona mejor con el tiempo

---

## 3. Motivo de cada decisión

No basta con guardar el resultado.
Hay que guardar el motivo.

### Ejemplos
- `edge_high_and_kelly_ok`
- `capital_insufficient`
- `kelly_below_minimum`
- `duplicate_market`
- `take_profit_hit`
- `stop_loss_hit`
- `revaluation_sell`
- `hold_edge_still_positive`
- `hold_no_exit_trigger`
- `skip_bad_price`
- `skip_out_of_date`

### Objetivo
Tener trazabilidad humana y técnica.

---

## 4. Órdenes y fills separados

Es obligatorio separar:
- trade
- orden
- fill
- posición

Ya hemos visto que mezclar estas capas crea mucha confusión.

### 4.1 Registro de orden

#### Campos mínimos
- `order_id`
- `trade_id`
- `cycle_id`
- `market_id`
- `submitted_at`
- `side`
- `price_limit`
- `size_requested`
- `notional_requested`
- `status_initial`
- `status_final`
- `submission_channel`
- `notes`

#### Estados posibles
- `submitted`
- `live`
- `delayed`
- `matched`
- `partially_filled`
- `cancelled`
- `failed`

### 4.2 Registro de fill

#### Campos mínimos
- `fill_id`
- `order_id`
- `trade_id`
- `timestamp`
- `price_fill`
- `size_fill`
- `notional_fill`

### Objetivo
Poder explicar bien:
- qué intentó hacer el bot
- qué se llenó realmente
- si hubo fills parciales
- por qué Railway, Telegram y Polymarket no siempre coinciden

---

## 5. Vida completa de cada trade

Cada trade debe tener un expediente propio desde la apertura hasta la resolución final.

### Campos mínimos
- `trade_id`
- `market_id`
- `market_name`
- `opened_at`
- `opened_cycle_id`
- `entry_reason`
- `entry_limit_price`
- `entry_fill_price_avg`
- `entry_size`
- `entry_cost`
- `forecast_at_entry`
- `model_probability_at_entry`
- `market_probability_at_entry`
- `edge_at_entry`
- `ev_at_entry`
- `trader_confirmation_at_entry`
- `max_price_seen`
- `min_price_seen`
- `max_pnl_seen`
- `min_pnl_seen`
- `closed_at`
- `closed_cycle_id`
- `exit_reason`
- `exit_fill_price_avg`
- `pnl_realized`
- `outcome_final`
- `duration_minutes`

### Objetivo
Convertir cada trade en una historia completa y auditable.

---

## 6. Revisión periódica de posiciones

Cada vez que el bot revise posiciones vivas, debe guardar el estado de cada una.

### Campos mínimos
- `review_id`
- `timestamp`
- `cycle_id` o `review_cycle_type`
- `trade_id`
- `market_id`
- `current_price`
- `current_pnl`
- `forecast_current`
- `model_probability_current`
- `market_probability_current`
- `edge_current`
- `time_to_resolution_minutes`
- `decision`
- `decision_reason`

### Valores posibles de `decision`
- `hold`
- `sell_take_profit`
- `sell_stop_loss`
- `sell_revaluation`
- `sell_resolution`
- `ignore_micro_position`

### Objetivo
Responder después:
- por qué mantuvo Seattle
- por qué vendió Atlanta
- por qué no salió antes de una reversión
- por qué una posición siguió viva aun perdiendo

---

## 7. Tracking intradía de posiciones vivas

Esto es crítico para casos como:
- Ankara +500% → 0
- Seattle +49% → stop-loss
- Chicago gran subida → win enorme

### Frecuencia sugerida
Ligera, solo para posiciones vivas.
No hace falta cada segundo.

### Campos mínimos
- `timestamp`
- `trade_id`
- `market_id`
- `current_price`
- `midpoint`
- `current_pnl`
- `max_price_seen_so_far`
- `min_price_seen_so_far`
- `max_pnl_seen_so_far`
- `min_pnl_seen_so_far`

### Métricas derivadas útiles
- tiempo por encima de +40%
- tiempo por encima de +100%
- tiempo por debajo de -30%
- hora del máximo
- hora del mínimo
- número de cruces de umbral

### Objetivo
Poder reconstruir:
- cuándo estuvo una posición en gran beneficio
- cuánto duró
- si una revisión más frecuente habría cambiado el resultado

---

## 8. Oportunidades perdidas

No basta con registrar lo que hizo el bot.
También debe registrar lo que dejó pasar.

### Tipos de oportunidades perdidas
- edge alto no comprado
- mercado aceptado no seleccionado
- mercado no comprado por falta de capital
- mercado no comprado por Kelly bajo
- posición que tocó gran beneficio y no se vendió
- posición vendida que luego siguió subiendo mucho
- posición mantenida que luego revirtió
- capital liberado no reutilizado en el mismo ciclo
- exposición duplicada que no debería haberse añadido

### Campos mínimos
- `timestamp`
- `cycle_id`
- `market_id` o `trade_id`
- `opportunity_type`
- `estimated_cost_of_miss`
- `reason_not_taken`
- `evidence_snapshot`
- `notes`

### Objetivo
Medir el coste real de la lógica actual.

---

## 9. Postmortem al resolver un mercado

Cuando un mercado resuelve, debe generarse un análisis estructurado del trade.

### Campos mínimos
- `trade_id`
- `market_id`
- `resolved_at`
- `market_result`
- `trade_result`
- `pnl_realized`
- `max_unrealized_pnl`
- `min_unrealized_pnl`
- `best_seen_price`
- `worst_seen_price`
- `would_tp40_help`
- `would_tp100_help`
- `would_trailing_help`
- `would_4h_monitor_help`
- `would_15m_monitor_help`
- `hold_to_resolution_vs_actual`
- `notes`

### Objetivo
No quedarnos en “ganó o perdió”, sino entender:
- si la lógica fue buena
- si la ejecución fue mala
- si una estrategia alternativa habría mejorado el resultado

---

## 10. Calidad de forecast y calidad de fuente

Para un bot meteorológico, hay que medir también si el problema viene de:
- la estrategia
- la ejecución
- o la fuente del dato meteorológico

### Campos mínimos
- `city`
- `target_date`
- `forecast_source`
- `forecast_at_entry`
- `forecast_last`
- `actual_result`
- `absolute_error`
- `error_bucket`
- `model_vs_market_gap`

### Objetivo
Poder ver:
- qué ciudades fallan más
- qué fuentes fallan más
- dónde el mercado supo algo antes
- dónde el modelo tenía razón y el mercado no

---

## 11. Registro de cambios del sistema

Si cambiamos lógica y no registramos cuándo, luego no sabremos qué mejoró o empeoró.

### Campos mínimos
- `bot_version`
- `strategy_version`
- `deployed_at`
- `min_edge`
- `tp_rule`
- `sl_rule`
- `sizing_rule`
- `forecast_source`
- `position_monitor_enabled`
- `notes`

### Objetivo
Poder atribuir resultados a cambios concretos.

---

## Qué debe producir el sistema automáticamente

## 1. Resumen diario
- pnl realizado
- pnl no realizado
- trades abiertos
- trades cerrados
- mejores trades
- peores trades
- oportunidades perdidas destacadas
- errores de observabilidad
- anomalías del día

## 2. Resumen semanal
- win rate
- profit factor
- average edge at entry
- average edge at exit
- realized vs unrealized max
- utilidad del TP
- utilidad del SL
- eficacia por ciudad
- eficacia por setup
- cambios entre versiones

## 3. Postmortems prioritarios
Lista automática de:
- trades más caros
- mayores oportunidades perdidas
- mejores capturas
- peores reversions
- trades afectados por bugs de duplicación o reporting

## 4. Paquete para Claude / Opus
Export automático en markdown o JSON con:
- resumen ejecutivo
- anomalías
- top trades
- oportunidades perdidas
- hipótesis técnicas
- dudas abiertas del piloto
- decisiones pendientes

---

## Preguntas que el sistema debería poder responder dentro de unas semanas

- ¿Qué setups ganan más?
- ¿Qué ciudades fallan más?
- ¿El TP40 ayuda o perjudica?
- ¿Cuánto dinero deja el bot sin capturar por revisar tarde?
- ¿Qué oportunidades se pierden por Kelly o por capital?
- ¿Qué versiones mejoraron el sistema y cuáles no?
- ¿Qué diferencia habría con hold-to-resolution?
- ¿Qué diferencia habría con ventas parciales?
- ¿Qué diferencia habría con un monitor cada 15 minutos?
- ¿Qué parte del problema viene de forecasting y qué parte de ejecución?

Si el sistema no puede responder estas preguntas, todavía no se está retroalimentando bien.

---

## Priorización por fases

## Fase 1 — Imprescindible
Implementar ya:
- `trade_id`
- registro completo de mercados evaluados
- órdenes y fills separados
- expediente de cada trade
- revisión de posiciones
- postmortem básico
- changelog de estrategia / versión

## Fase 2 — Muy importante
Añadir:
- tracking intradía de posiciones vivas
- registro de oportunidades perdidas
- métricas diarias y semanales
- export markdown para Claude

## Fase 3 — Potencia real
Añadir:
- contrafactuales automáticos
- comparativa entre estrategias sombra
- dashboard operativo
- export completo de análisis para sesiones de coding

---

## Estructura sugerida de archivos

### Eventos append-only
- `cycles.jsonl`
- `market_evaluations.jsonl`
- `orders.jsonl`
- `fills.jsonl`
- `trades.jsonl`
- `position_reviews.jsonl`
- `missed_opportunities.jsonl`
- `trade_postmortems.jsonl`

### Resúmenes
- `daily_metrics.json`
- `weekly_review.json`

### Export para IA
- `reports/last_cycle.md`
- `reports/daily_summary.md`
- `reports/weekly_summary.md`
- `reports/claude_packet.md`

---

## Regla principal

**El bot no debe auto-modificarse solo; debe auto-documentarse muy bien.**

Ese es el punto exacto donde el sistema gana valor con el tiempo sin poner en riesgo la operativa.

---

## Objetivo final

Pasar de un bot que solo ejecuta trades a un sistema:

- instrumentado
- explicable
- auditable
- acumulativo
- útil para sesiones de mejora con Claude Opus / Sonnet

Cuantas más sesiones y más tiempo de operación tenga, más memoria útil debe generar sobre:
- decisiones
- errores
- oportunidades perdidas
- ventajas
- lógica
- estrategia
- contrafactuales

Ese es el tipo de retroalimentación inteligente que realmente mejora un proyecto como este.
