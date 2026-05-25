# Política Canónica de Fuentes P/L

**Versión:** 1.0  
**Fecha:** 2026-05-06  
**Sesión:** 301 (Sonnet 4.6)  
**Clasificación:** ACTION_DESIGN / WATCH_RISK  
**Decidido por:** Opus (revisión solicitada por Pablo)

---

## 1. Estado actual de fuentes (2026-05-06)

| Fuente | Estado | Uso autorizado | Uso prohibido |
|--------|--------|---------------|---------------|
| `trade_lifecycle.json` | contaminated 1.0 | `untrusted_pnl` con disclaimer / auditoría interna | BANKROLL readiness, Telegram real con cifra P/L, decisiones operativas, comparativas históricas |
| `wallet_portfolio_snapshots.jsonl` | accumulating baseline / not_ready | base futura cuando `phase2_ready=true` y cash flows ajustados | P/L operativo mientras `not_ready` o sin cash flows reconciliados |
| `wallet_cash_flows.jsonl` | missing | — | cualquier uso; debe tener cobertura manual atestiguada antes de promover wallet P/L. Un archivo vacío no es evidencia |
| Dashboard Polymarket | manual only | ground truth de comparación manual | scraper/extractor automático (no autorizado) |

---

## 2. Jerarquía canónica

1. **Dashboard Polymarket (manual)** — ground truth de referencia. Sin extractor automático autorizado.
2. **`wallet_pnl_7d` vía `wallet_portfolio_snapshots`** — puede ser canónica operativa solo tras cumplir todos los criterios de promoción (ver §4).
3. **`trade_lifecycle`** — telemetría interna no operativa. Siempre con disclaimer `untrusted_pnl`.

---

## 3. Bloque `pnl_sources` recomendado en el digest

Próximo patch del Daily Bot Kanban Digest debe incluir este bloque (JSON y formato humano):

```json
{
  "pnl_sources": {
    "lifecycle":          "contaminated — no operativo",
    "wallet_pnl":         "accumulating baseline",
    "cash_flows":         "missing",
    "dashboard":          "manual only / unavailable",
    "canonical_source":   null,
    "bankroll_readiness": "blocked"
  }
}
```

---

## 4. Criterios de promoción `wallet_pnl_7d` (todos obligatorios)

1. `phase2_ready=true` desde `wallet_snapshot.py`
2. ≥ 168 h de historia continua de snapshots
3. ≥ 14 snapshots válidos
4. ≥ 7 días distintos con al menos un snapshot
5. `wallet_cash_flows.jsonl` cubre últimos 7 días con attestations explícitas o movimientos reales documentados. Un archivo vacío no es evidencia y no desbloquea readiness
6. `possible_deposits_7d=0` o todos los movimientos reconciliados
7. Divergencia ≤ ±$1.50 vs. dashboard Polymarket 1W en comparación manual
8. Revisión Opus explícita

---

## 5. Condiciones Telegram

| Nivel | Requisito mínimo |
|-------|-----------------|
| Telegram informativo (sin cifra P/L) | ≥ 14 días LOG_ONLY/dry-run sin falsos positivos + disclaimer + `source_quality` + revisión Opus |
| Telegram con cifra P/L | Lo anterior + `wallet_pnl` promovido a canónico (§4) |
| BANKROLL readiness | Todo lo anterior + WR limpio + drawdown aceptable + signoff Pablo + Opus |
| Fase C | Decisión independiente — no autorizada por esta política |

---

## 6. Qué mostrar ahora en el digest

```
P/L no canónico:
  - Lifecycle:      contaminated — no operativo
  - Wallet 7d:      accumulating baseline
  - Cash flows:     missing
  - Dashboard 1W/1M/ALL: manual only / unavailable
  - BANKROLL ready: blocked
```

---

## 7. Guardrails permanentes

- `trade_lifecycle` nunca se promueve a canónico aunque se reprocese, por contaminación estructural confirmada.
- No hay scraper/extractor automático del dashboard Polymarket autorizado.
- Ninguna fuente `not_ready` se usa en Telegram real, BANKROLL ni decisiones de sizing.
- Toda cifra P/L en comunicaciones debe incluir `source_quality` y estado de canon.
- `data/wallet_cash_flows.jsonl` real no debe versionarse ni crearse antes de Patch B/Patch C y aprobación manual explícita de Pablo.
- La ausencia sigue siendo el estado correcto hasta que exista attestation manual; `canonical_source=none` y `bankroll_readiness=blocked` permanecen.
- Esta política no autoriza cambios en trading core, bot.py, scheduler, whitelist, city modes, sizing, reglas de riesgo, BANKROLL ni Fase C.
- **Prohibición training/calibración/Outcome Resolver:** `trade_lifecycle.json` (contaminated 1.0) y `performance.json` no reconciliado están **PROHIBITED_FOR_TRAINING_UNTIL_FIXED**. No pueden ser input del Outcome Resolver, calibración meteorológica ni etiquetado de `forecast_correctness`. Ver contrato completo en [`docs/learning_data_contract.md`](learning_data_contract.md).
- **Fuente canónica para PnL realizado:** `trades.log` / fills reconciliados por `order_id + fill_value`. Ver §Contrato en [`docs/learning_data_contract.md`](learning_data_contract.md).

---

## 8. Historial de cambios

| Versión | Fecha | Autor | Cambio |
|---------|-------|-------|--------|
| 1.2 | 2026-05-25 | Sonnet (Sesión 390) | Añade prohibición training/calibración/Outcome Resolver + referencia a learning_data_contract.md |
| 1.1 | 2026-05-06 | Codex (Sesión 303) | Aclara que un archivo vacío no es attestation y no desbloquea readiness |
| 1.0 | 2026-05-06 | Opus + Sonnet 4.6 (Sesión 301) | Creación inicial |
