# blocked_signals_audit.py — Fase B1

Read-only CLI para auditar `data/blocked_signals_resolutions.jsonl` sin acceso SSH manual.

## Uso básico

```bash
# Reporte de texto en consola
python tools/blocked_signals_audit.py --source data/blocked_signals_resolutions.jsonl

# Últimos 30 días solamente
python tools/blocked_signals_audit.py --source ... --days 30

# JSON estructurado
python tools/blocked_signals_audit.py --source ... --json

# Markdown a archivo
python tools/blocked_signals_audit.py --source ... --markdown --out docs/blocked_audit_$(date +%F).md

# Top 15 ciudades
python tools/blocked_signals_audit.py --source ... --top 15
```

## Secciones del reporte

| Sección | Contenido |
|---|---|
| **A** | Resumen global: total, v1/v2, resolved, wins, losses, WR, fechas, ciudades, traders |
| **B** | Split whitelist: IN / OUT / unknown con WR por grupo |
| **C** | Top N ciudades: WR, condición, traders, avg_price, price_bucket, schema, fidelity |
| **D** | Concentración: top 3 ciudades, % del total, advertencia si >60% |
| **E** | Señales de baja accionabilidad: fidelity gaps, coverage issues, v1 sin v2, precios extremos |
| **F** | Duplicados por canonical_signal_id y market_id; aviso si hay v1 sin dedupe fino |
| **G** | Candidatos a auditoría (OUT whitelist, n≥10, WR≥70%, precio 0.20–0.90, ≥2 traders) |

## Clasificaciones (solo auditoría operativa)

| Clasificación | Significado |
|---|---|
| `audit_candidate` | OUT whitelist, n≥10, WR≥70%, precio en rango, ≥2 traders — requiere auditoría manual |
| `needs_settlement_verification` | ICAO-only o sin cobertura local + fidelity unknown/unverified |
| `monitor` | WR≥55%, muestra moderada — observar más antes de decidir |
| `not_actionable` | Muestra insuficiente o WR baja |
| `ignore` | n<5 |

> **Ninguna clasificación implica apertura de trading.** La decisión de agregar una ciudad a la whitelist requiere auditoría manual de settlement source, cobertura observada y revisión operativa.

## Fuente canónica

El archivo `data/blocked_signals_resolutions.jsonl` en este repo es para pruebas locales.
La fuente canónica está en Railway: `/app/data/blocked_signals_resolutions.jsonl`.

Para descargar la fuente canónica:
```powershell
.\tools\railway_safe.ps1 ssh "cat /app/data/blocked_signals_resolutions.jsonl" > data/blocked_signals_resolutions.jsonl
```

## Schema v1 vs v2

- Registros sin `schema_version` se tratan como v1 implícito.
- v1 tiene 13 campos; v2 tiene 25 campos (12 siempre disponibles + 5 null/unknown hasta Fase C).
- La herramienta normaliza v1 con defaults para todos los campos ausentes.
- Sección F advierte cuando hay muchos registros v1 (dedupe limitado sin `canonical_signal_id`).

## Restricciones

- Solo lectura por defecto.
- Sin escritura de estado salvo con `--out`.
- Sin llamadas a Polymarket, NOAA, WU, Open-Meteo ni Telegram.
- Sin importación de `bot.py`.
- Solo stdlib Python 3.9+.
