# Wallet Snapshot

`tools/wallet_snapshot.py` crea snapshots read-only del valor wallet/portfolio de Polymarket para dejar de depender de capturas manuales diarias del dashboard.

La herramienta no envia Telegram, no ejecuta ordenes, no cancela ordenes y no se integra todavia con `tools/pnl_reconciliation_alert.py`. Su salida JSON expone `phase2_ready` para que una fase futura pueda avisar cuando ya exista baseline de 7 dias usable.

## Que mide

`total_value` es:

```text
cash_available + active_positions_value + resolved_pending_value
```

- `cash_available`: USDC disponible leido con el cliente CLOB si hay credenciales.
- `active_positions_value`: valor actual de posiciones abiertas con valor material.
- `resolved_pending_value`: posiciones practicamente resueltas o redeemable que aun aparecen en la Data API.

Esto no es el P/L exacto `1W` del dashboard de Polymarket. Es un delta propio por snapshots: compara el valor total actual contra un baseline de hace 7 dias y ajusta depositos/retiros manuales anotados. Es menos dependiente de fills historicos fragiles y sirve tambien para readiness, dashboard futuro, alertas de caja y auditorias de recargas.

## Uso

```bash
python tools/wallet_snapshot.py --dry-run
python tools/wallet_snapshot.py --json
python tools/wallet_snapshot.py --dry-run --markdown
python tools/wallet_snapshot.py --report-only --json
```

Por defecto appendea en `data/wallet_portfolio_snapshots.jsonl`. Con `--dry-run` imprime el snapshot calculado sin escribir. Con `--report-only` no llama a APIs y solo resume el historico existente.

## Cash flows manuales

Si hubo una recarga o retiro manual, se puede anotar en `data/wallet_cash_flows.jsonl`:

```json
{"date": "2026-04-29", "amount": 25.00, "type": "deposit"}
{"date": "2026-04-30", "amount": 10.00, "type": "withdrawal"}
```

Los depositos restan al delta bruto. Los retiros suman al delta bruto. Si el archivo no existe, la herramienta no falla. Las lineas invalidas se ignoran y aparecen como warnings en JSON.

## Estados

`ACUMULANDO`: hay snapshots, pero aun no existe baseline de 7 dias/168h.

`ACTIVO`: existe P/L 7d por snapshot delta.

`phase2_ready`: `true` solo cuando hay baseline valido de 7 dias, P/L disponible y sin posible deposito material sin anotar.

`possible_deposit`: el valor total subio mas que `--deposit-threshold` frente al snapshot valido anterior y no hay cash flow manual que lo explique.

`wallet_pnl_confidence`:

- `high`: baseline 7d sin cash flows ni depositos desconocidos.
- `medium`: baseline 7d con cash flows anotados y ajuste aplicado.
- `low`: posible deposito sin anotar o datos parciales.
- `unavailable`: aun no hay P/L wallet disponible.

## Guardrail

Esta herramienta no autoriza subir capital operativo ni cambiar sizing. Solo produce evidencia read-only para reconciliacion y readiness futura.
