# MIN_EDGE por ciudad - analisis 2026-04-25

## Alcance

Analisis read-only sobre `data/runtime_import/trade_lifecycle.json` tras la limpieza post-V2 cutover.
No se cambia `bot.py`, Railway env vars, Kelly, sigma, filtros ni reglas de entrada/salida.

Precondicion operativa revisada antes del analisis: los logs recientes de Railway no muestran errores recurrentes en `create_or_derive_api_key`, `get_open_orders`, auth endpoints ni CLOB. Solo aparecen warnings auxiliares de resumenes analiticos, no inestabilidad V2 SDK.

## Metodo

- Universo: trades cerrados con `close_context.pnl_cash` disponible.
- `WR`: trades con `pnl_cash > 0` / trades cerrados.
- `PnL`: suma neta de `close_context.pnl_cash`.
- `Avg edge entrada`: media de `entry_context.edge_pct` cuando existe.
- `EV realizado`: `PnL neto / capital de entrada observado`, como ROI realizado aproximado.
- Gate para proponer umbral: `n_closed >= 10`, `WR >= 70%` y `PnL > 0`.
- Regla propuesta si una ciudad cualifica: `MIN_EDGE` justo por encima del mayor `edge_pct` de un trade historico no rentable. Si ese corte elimina tambien ganadores, se marca como no separable.

## Resultado ejecutivo

No hay ninguna ciudad que cumpla hoy `n_closed >= 10`, `WR >= 70%` y `PnL > 0`.

La lectura correcta es no aplicar `MIN_EDGE_PER_CITY` todavia. Tokyo es la ciudad con mejor pinta (`WR=80%`, `PnL=+$3.53`), pero solo tiene `n=5`; mover umbrales con esa muestra seria prematuro.

## Tabla por ciudad

| Ciudad | n cerrados | WR | PnL neto | Avg edge entrada | EV realizado | MIN_EDGE propuesto | Nota |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Ankara | 3 | 33.3% | $-1.58 | 36.4% | -31.6% | n/a | sample<10 |
| Buenos Aires | 4 | 75.0% | $-0.19 | 34.1% | -3.1% | n/a | sample<10 |
| Chicago | 9 | 11.1% | $-7.78 | 24.3% | -47.3% | n/a | sample<10 |
| Dallas | 5 | 20.0% | $-1.10 | 24.9% | -17.1% | n/a | sample<10 |
| London | 5 | 20.0% | $-8.97 | 36.9% | -144.4% | n/a | sample<10 |
| Madrid | 1 | 0.0% | $-1.95 | n/d | n/d | n/a | sample<10 |
| Miami | 3 | 0.0% | $-5.83 | 23.6% | -141.5% | n/a | sample<10 |
| Milan | 1 | 0.0% | $-1.07 | 46.5% | -43.5% | n/a | sample<10 |
| Munich | 2 | 0.0% | $-2.01 | 30.0% | -54.0% | n/a | sample<10 |
| Paris | 2 | 0.0% | $-2.42 | 39.7% | -100.4% | n/a | sample<10 |
| Seattle | 2 | 0.0% | $-2.66 | 14.4% | -140.0% | n/a | sample<10 |
| Shanghai | 4 | 50.0% | $+0.15 | 26.5% | +2.2% | n/a | sample<10 |
| Singapore | 1 | 0.0% | $-0.36 | 25.7% | -25.0% | n/a | sample<10 |
| Tel Aviv | 1 | 0.0% | $-2.46 | n/d | n/d | n/a | sample<10 |
| Tokyo | 5 | 80.0% | $+3.53 | 26.5% | +37.5% | n/a | sample<10 |
| Toronto | 1 | 0.0% | $-1.71 | n/d | n/d | n/a | sample<10 |
| Wellington | 1 | 0.0% | $-2.10 | 35.3% | -84.0% | n/a | sample<10 |
| Atlanta | 10 | 30.0% | $-3.48 | 19.7% | -19.7% | n/a | no cumple gate |
| New York City | 10 | 30.0% | $+0.09 | 33.9% | +0.8% | n/a | no cumple gate |
| Seoul | 10 | 50.0% | $-0.39 | 29.3% | -2.7% | n/a | no cumple gate |

## Propuesta de env var

No aplicar todavia.

Cuando haya al menos una ciudad cualificada, usar formato JSON en Railway:

```text
MIN_EDGE_PER_CITY={"Tokyo":22.5,"Shanghai":24.0}
```

Motivo para preferir JSON sobre CSV: evita ambiguedades con nombres de ciudad con espacios (`New York City`) y permite parseo estricto con fallback al `MIN_EDGE_PCT` global.

## Implementacion sugerida si Opus decide aplicarlo

1. Anadir parser defensivo de `MIN_EDGE_PER_CITY` en `bot.py`:
   - `json.loads(os.getenv("MIN_EDGE_PER_CITY", "{}"))`
   - normalizar claves con `normalize_city`
   - ignorar valores no numericos o negativos
2. Crear helper puro:

```python
def min_edge_for_city(city, default=MIN_EDGE):
    return MIN_EDGE_PER_CITY.get(normalize_city(city), default)
```

3. Sustituir solo el punto donde se calcula `_effective_min_edge` base:

```python
_effective_min_edge = min_edge_for_city(city)
if c.get("exact_range_canary"):
    _effective_min_edge += MIN_EDGE_EXACT_RANGE_BUFFER_PP
```

4. Mantener intactos los buffers ya existentes (`exact/range`, low-price) y registrar en `skip_log` el `min_edge` efectivo usado.
5. Anadir tests de:
   - ciudad sin override usa global
   - ciudad con override usa valor por ciudad
   - nombres con espacios
   - JSON invalido fail-open hacia global

## Decision recomendada

No aplicar P7 en la siguiente sesion salvo que Opus quiera cambiar el criterio estadistico. El siguiente gate razonable es repetir este analisis cuando Tokyo, Shanghai o Seoul alcancen `n_closed >= 10` post-v10.6.30/v10.6.31 con muestra limpia.
