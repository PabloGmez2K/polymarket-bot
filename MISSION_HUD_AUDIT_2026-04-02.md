# Auditoria Mission HUD — 2 abr 2026

## Alcance

Sesion dedicada a la prioridad fijada en contexto:

- auditar la captura del `Mission HUD` como fuente de verdad visual de la capa 1;
- contrastar `snapshot` live, builders locales y screenshot;
- comprobar que metricas y textos prioritarios no arrastren errores de agregacion, buckets o semantica.

## Fuentes revisadas

- `SNAPSHOT_DASHBOARD_LIVE_2026-04-01T2013Z.json`
- `bot.py`
- `templates/dashboard.html`
- `verify_before_deploy.py`
- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`

## Estado de la auditoria

### 1. Contraste builder -> snapshot

La semantica principal del HUD queda alineada entre codigo y payload congelado:

- `focus.status_label = "Sano con limitaciones"`
- `focus.health_score = 85`
- mision activa: `Primary Quest`
- accion recomendada: `No tocar trading: priorizar crecimiento de muestra NOAA`
- resumen operativo: `NOAA 2/10 casos | 0/4 ciudades interpretables`

No aparecen incoherencias duras de agregacion en:

- titulo de mision;
- accion principal;
- contadores de cobertura;
- barras `tracks`;
- `stage_path`;
- quick stats del HUD.

### 2. Semantica que puede parecer confusa, pero es intencional

El snapshot mezcla dos conceptos cercanos pero distintos:

- `0/4 ciudades interpretables`
- `1 / 4 ciudades con muestra`

Esto **no parece un bug**. Los tests existentes en `verify_before_deploy.py` lo validan explicitamente: una ciudad puede tener casos NOAA acumulados sin haber alcanzado aun el umbral de interpretabilidad (`>= 3`).

Lectura correcta del snapshot auditado:

- solo `Chicago` tiene muestra (`2 casos`);
- ninguna ciudad activa es todavia `interpretable`;
- por eso `coverage_display` puede ser `1 / 4 ciudades con muestra` y a la vez `observed_ready_count = 0`.

### 3. Riesgos de lectura detectados

No veo error de datos, pero si dos puntos de friccion visual/semantica:

1. El HUD usa a la vez:
   - `ciudades con muestra`
   - `ciudades interpretables`
   Esto es correcto tecnicamente, pero sin screenshot no puedo confirmar si visualmente se distinguen bien.

2. El panel puede transmitir a la vez:
   - estado general `Sano con limitaciones` (`accent`);
   - `System health` en `85/100`;
   - track `health` con badge `good`.
   No parece inconsistencia logica, pero si un punto a revisar en la captura para asegurar que no se lea como mensaje contradictorio.

## Lo que falta para cerrar la auditoria

No hay screenshot/captura del `Mission HUD` en el workspace. Sin esa tercera fuente no puede cerrarse la parte visual final:

- orden real de lectura;
- prominencia de `Primary Quest` vs `System HP`;
- claridad entre `muestra` e `interpretable`;
- posible confusion entre badges `accent / good / warn` en el primer pliegue.

## Veredicto parcial

Con las fuentes disponibles, **no hay evidencia de bug de agregacion o semantica rota en el builder del Mission HUD**. La prioridad NOAA/coverage del snapshot live esta bien reflejada por el codigo y por los tests.

El unico cierre pendiente de esta auditoria es el contraste directo con la captura visual compartida el 2 de abril de 2026.
