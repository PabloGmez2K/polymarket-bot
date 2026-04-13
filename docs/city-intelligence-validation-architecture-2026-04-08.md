# City Intelligence Validation Architecture

## Objetivo

Esta arquitectura convierte la automatizacion de traders en un sistema util
para ampliar universo con evidencia y seguimiento continuo.

La idea no es:

- copiar wallets;
- decidir edge operativo solo por actividad externa;
- tocar el core del bot sin validacion.

La idea si es:

- detectar ciudades candidatas;
- medir cual es el cuello de botella real por ciudad;
- empujar esas ciudades a una cola de validacion shadow;
- avisar por Telegram cuando haya algo que debas reenviar a Codex.

## Cuello de botella que resuelve

Hoy el cuello no es discovery puro.

Ya sabemos encontrar traders y ciudades interesantes.
Lo que falta es convertir esa senal externa en una prueba suficiente de edge
operativo para nuestro sistema.

Por eso la nueva arquitectura se centra en este puente:

`trader discovery -> city validation ledger -> promotion gate -> review`

## Scripts conectados

### 1. `tools/directional_trader_census.py`

Funcion:

- escanea mercados direccionales comparables;
- detecta wallets compradoras activas;
- deja una shortlist comparable.

Salida:

- `data/directional_trader_census.json`
- `docs/directional_trader_census_latest.md`

### 2. `tools/directional_trader_enrichment.py`

Funcion:

- enriquece la shortlist con WR, PnL y posiciones cerradas/activas;
- separa referencias fuertes de candidatos flojos.

Salida:

- `data/directional_trader_enrichment.json`
- `docs/directional_trader_enrichment_latest.md`

### 3. `tools/reference_trader_city_market_cross.py`

Funcion:

- cruza traders comparables con policy de ciudades y snapshot actual;
- convierte wallet intelligence en discovery por ciudad.

Salida:

- `data/reference_trader_city_market_cross.json`
- `docs/reference_trader_city_market_cross_latest.md`

### 4. `tools/city_validation_ledger.py`

Funcion nueva:

- toma discovery externo y lo combina con observabilidad propia;
- separa `visibility_evidence` de `edge_evidence`;
- calcula `settlement_fidelity`;
- identifica el cuello de botella dominante de cada ciudad.

Salida:

- `data/city_validation_ledger.json`
- `docs/city_validation_ledger_latest.md`

### 5. `tools/city_promotion_gate.py`

Funcion nueva:

- convierte el ledger en una cola operativa de revision;
- deja claro que ciudades merecen revision manual en Codex;
- no toca policy ni trading, solo recomienda.

Salida:

- `data/city_promotion_gate.json`
- `docs/city_promotion_gate_latest.md`

### 6. `tools/city_intelligence_telegram_alert.py`

Funcion nueva:

- envia alerta one-shot por Telegram cuando una ciudad entra en review queue;
- evita spam con estado persistido;
- explica que paso, por que importa y deja una `Instruccion para Codex`
  lista para pegar en una sesion nueva.

Salida:

- `data/city_intelligence_alert_state.json`
- `docs/city_intelligence_alert_latest.md`

### 7. `tools/city_intelligence_daily_summary.py`

Funcion nueva:

- genera el resumen diario para las `07:00 UTC`;
- resume si estamos mas cerca, estancados o sin senal util;
- deja la mejor `Instruccion para Codex` del dia;
- sirve como checkpoint diario del bucle de mejora continua.

Salida:

- `data/city_intelligence_daily_summary_state.json`
- `docs/city_intelligence_daily_summary_latest.md`

### 8. `tools/city_intelligence_pipeline.py`

Funcion nueva:

- orquesta toda la cadena;
- opcionalmente refresca `settlement_fidelity_probe` y `directional_trader_census`;
- regenera ledger, gate y alertas;
- deja un resumen final corto con el cuello dominante del sistema.

Salida:

- `data/city_intelligence_pipeline.json`
- `docs/city_intelligence_pipeline_latest.md`

## Flujo operativo real

1. `city_intelligence_pipeline.py` corre por cron o manualmente.
2. Si hay datos nuevos, actualiza traders comparables.
3. Cruza traders con ciudades relevantes.
4. Calcula para cada ciudad:
   - discovery externo;
   - evidencia shadow propia;
   - source/settlement fidelity;
   - cuello de botella dominante.
5. Genera una cola de revision clara.
6. Si aparece algo nuevo e importante, Telegram avisa con
   `Instruccion para Codex`.
7. Cada dia a las `07:00 UTC`, el resumen diario dice si estamos mas cerca o
   no de monetizar expansion del universo.
8. La revision fina se hace en Codex antes de tocar policy o canary.

## Que informacion util te da

No solo "que ciudad sale arriba", sino:

- por que sale;
- que le falta para ser candidata de verdad;
- si el problema es discovery, visibilidad, source fidelity o validacion shadow;
- si merece shadow reforzado, benchmark, revision de bloqueo o posible canary;
- si estamos mas cerca o no de monetizar `bot.py`;
- que mensaje breve debes enviar a Codex para seguir iterando.

## Como usarlo

Modo seguro con datos ya existentes:

```powershell
python tools/city_intelligence_pipeline.py --telegram-dry-run
```

Modo con refresh completo:

```powershell
python tools/city_intelligence_pipeline.py --refresh-probe --refresh-census
```

Resumen diario:

```powershell
python tools/city_intelligence_daily_summary.py --dry-run
```

## Workflow humano correcto

El sistema esta pensado para este bucle:

1. Railway ejecuta el pipeline periodico.
2. Telegram te envia:
   - alertas intradia cuando algo cambia de verdad;
   - resumen diario a las `07:00 UTC`.
3. Tu lees el output como operador.
4. Si hay accion, copias la `Instruccion para Codex` en una sesion nueva.
5. Codex trabaja el cuello de botella actual.
6. Los cambios relevantes quedan documentados.
7. Periodicamente Opus revisa direccion, sesgos y oportunidades de mejora.

Eso convierte la automatizacion en un sistema de mejora continua, no en una
coleccion de scripts sueltos.

## Interpretacion correcta

Esta arquitectura no demuestra edge operativo por si sola.

Lo que hace es alimentar el cuello de botella correcto:

- selecciona mejores candidatas;
- las empuja a una validacion propia mas rica;
- y te dice con claridad cuando toca revisar.

Si una ciudad pasa bien por este embudo, entonces ya tiene sentido llevarla a
una validacion shadow mas agresiva o a un canary pequeno.
