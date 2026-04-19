# Auditoría `price_out_of_range` por ciudad canary — 19 abr 2026

## Alcance

- objetivo: leer `skip_log` y responder si hay ciudades `canary` que caen de forma sistemática en `price_out_of_range`
- no se toca `bot.py`, `MIN_EDGE`, el filtro global `[0.20, 0.80]`, scheduler ni policy live
- snapshot usado: `data/runtime_import/skip_log.jsonl` pull de Railway hecho el `2026-04-18T09:28:57Z`

## Fuente y ventana

- histórico del snapshot: `79` ciclos / `19,267` skips
- ventana reciente: últimos `30` ciclos (`2026-04-14T09:41` → `2026-04-18T09:27`)
- canary efectivas en el snapshot: `Atlanta`, `London`, `Munich`, `New York City`, `Seoul`, `Shanghai`, `Tokyo`

## Hallazgo principal

Sí hay **concentración fuerte** de `price_out_of_range` en varias canary, pero la lectura honesta no es "estas ciudades siempre quedan fuera de rango" sino:

1. el problema se concentra sobre todo en `Seoul`, `Tokyo` y `Shanghai`, con saturación reciente muy alta;
2. `London`, `New York City` y `Munich` también muestran peso alto del bucket, pero menos extremo;
3. `Atlanta` no parece una canary estructuralmente atrapada por precio;
4. el filtro está rechazando casi siempre mercados **ultrabaratos `<0.20`**, no una mezcla amplia con mercados caros `>0.80`.

## Resumen cuantitativo

### Todo el snapshot (`79` ciclos)

| Ciudad | Skips totales | `price_out_of_range` | % ciudad |
|------|--------------:|---------------------:|---------:|
| Seoul | 1192 | 772 | 64.8% |
| Shanghai | 724 | 453 | 62.6% |
| New York City | 1011 | 577 | 57.1% |
| London | 1329 | 706 | 53.1% |
| Tokyo | 547 | 276 | 50.5% |
| Atlanta | 571 | 276 | 48.3% |
| Munich | 396 | 158 | 39.9% |

Lectura:

- en histórico completo, `Seoul` y `Shanghai` ya vienen dominadas por precio;
- `NYC` y `London` tienen bucket alto, pero conviven con bastante `date_out_of_range_past` y `condition_filtered`;
- `Atlanta` y `Munich` no se ven "muertas por precio" en el mismo grado.

### Ventana reciente (`30` ciclos)

| Ciudad | Skips totales | `price_out_of_range` | % ciudad | `date_out_of_range_past` | `condition_filtered` |
|------|--------------:|---------------------:|---------:|-------------------------:|---------------------:|
| Seoul | 369 | 320 | 86.7% | 0 | 18 |
| Tokyo | 86 | 74 | 86.0% | 0 | 10 |
| Shanghai | 142 | 120 | 84.5% | 0 | 16 |
| Munich | 88 | 66 | 75.0% | 11 | 11 |
| London | 374 | 253 | 67.6% | 55 | 66 |
| New York City | 417 | 280 | 67.1% | 77 | 55 |
| Atlanta | 110 | 45 | 40.9% | 55 | 10 |

Lectura:

- la saturación reciente sí es muy fuerte en `Seoul`, `Tokyo` y `Shanghai`;
- `Munich` entra en una zona gris: price domina, pero con muestra pequeña (`88` skips);
- `London` y `NYC` están cargadas hacia price, aunque no exclusivamente;
- `Atlanta` queda bastante más balanceada y no encaja con una tesis de "canary inoperable por rango".

## ¿Es un problema por arriba de `0.80` o por debajo de `0.20`?

En la ventana reciente, las filas `price_out_of_range` de canary son casi enteramente mercados por debajo de `0.20`:

| Ciudad | Price skips | `<0.20` | `>0.80` |
|------|------------:|---------:|---------:|
| Atlanta | 45 | 100.0% | 0.0% |
| London | 253 | 100.0% | 0.0% |
| Munich | 66 | 100.0% | 0.0% |
| New York City | 280 | 99.3% | 0.7% |
| Seoul | 320 | 98.8% | 1.2% |
| Shanghai | 120 | 98.3% | 1.7% |
| Tokyo | 74 | 97.3% | 2.7% |

Conclusión:

- no hay evidencia de una ciudad canary chocando mucho con el techo `>0.80`;
- el bucket viene casi por completo de mercados que Polymarket ya lista demasiado baratos para la policy actual.

## ¿Estas canary quedan "operables en teoría, pero nunca operables en práctica"?

No en sentido literal.

En los últimos `30` ciclos:

- `Seoul` aparece en `28` ciclos y tiene `23` ciclos donde al menos una fila sale del puro bucket de precio y llega más adentro del funnel; además tiene `2` BUYs después de la promoción actual del `2026-04-17T16:29:31Z`
- `Shanghai` aparece en `11` ciclos y alcanza etapas posteriores al filtro de precio en `4`; tiene `1` BUY posterior a su promoción actual
- `Tokyo` aparece en `6` ciclos y alcanza etapas posteriores en `2`; tiene `1` BUY posterior a su promoción actual
- `New York City` aparece en `28` ciclos y alcanza etapas posteriores en `5`; tiene `1` BUY reciente desde `2026-04-14`
- `London` y `Munich` no muestran progreso post-price en esta ventana, pero sí tienen BUYs posteriores a su promoción actual en el snapshot completo (`1` cada una)
- `Atlanta` no convierte recientemente, pero su cuello dominante reciente es más mixto (`date` + `price`) que puramente precio

Por tanto:

- **no** veo una canary que pueda describirse honestamente como "siempre fuera de rango, nunca puede operar"
- **sí** veo canary donde el precio es ya el filtro dominante y muy probablemente está reduciendo mucho la oportunidad práctica, sobre todo `Seoul`, `Tokyo` y `Shanghai`

## Matices importantes

- `Seoul` arrastra en esta ventana `22` filas `kelly_too_low` relacionadas con el mismatch Seoul/Incheon ya documentado y corregido después; ese ruido afecta la lectura del funnel, aunque no cambia el hecho de que `price_out_of_range` sigue siendo su bucket dominante
- esta auditoría usa un snapshot tirado el `2026-04-18`; no incluye lo que haya pasado después de ese pull
- la pregunta aquí es de readout operativo, no de si conviene relajar el filtro global

## Veredicto corto

- el `53%` global de skips por `price_out_of_range` **sí** esconde concentración por ciudad
- las canary más afectadas hoy son `Seoul`, `Tokyo` y `Shanghai`
- `London`, `New York City` y quizá `Munich` muestran presión relevante pero no una imposibilidad total
- `Atlanta` no parece candidata a una tesis de "fuera de rango sistemático"
- el patrón es casi totalmente de mercados `<0.20`, así que si más adelante se quisiera reabrir este frente, el follow-up honesto sería **por ciudad y por tramo de precio bajo**, no una discusión abstracta sobre todo el rango `[0.20, 0.80]`

## Decisión operativa

- **no cambiar** el filtro global `[0.20, 0.80]` con esta evidencia
- **no degradar** ni sacar de `canary` a `Seoul`, `Tokyo` o `Shanghai` solo por este readout
- **no abrir** una discusión abstracta de recalibración global del precio; la evidencia no apunta a un problema simétrico del rango, sino a un subcaso concentrado en precios `<0.20`

## Acción cerrada en esta sesión

- se clasifica a `Seoul`, `Tokyo` y `Shanghai` como canary con **cuello dominante de precio bajo**
- se deja fuera de prioridad inmediata a `Atlanta`, y en zona intermedia a `London`, `New York City` y `Munich`
- si este frente se reabre más adelante, el siguiente bloque honesto ya no será "¿cambiamos el filtro global?", sino una **micro-auditoría por ciudad del bucket `<0.20`** usando una ventana fresca posterior a `v10.6.23`
