# B3.1 Polymarket API P&L Discovery

Fecha: 2026-05-07

## Alcance

Investigacion read-only para decidir si una futura fuente `polymarket_api_pnl` puede servir como `external_observability` para contrastar el P&L mostrado por Polymarket en horizontes 1D, 1W, 1M y ALL.

No se ejecutaron llamadas autenticadas, no se usaron credenciales, no se tocaron `tools/`, `bot.py`, trading core, DB, env vars, Telegram, Railway, BANKROLL, Fase C ni `tools/pnl_report.py`.

## Fuentes consultadas

- Polymarket docs index: https://docs.polymarket.com/llms.txt
- API overview: https://docs.polymarket.com/api-reference/introduction
- Authentication: https://docs.polymarket.com/api-reference/authentication
- Rate limits: https://docs.polymarket.com/api-reference/rate-limits
- Current positions: https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user
- Closed positions: https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user
- Market positions: https://docs.polymarket.com/api-reference/core/get-positions-for-a-market
- User activity: https://docs.polymarket.com/api-reference/core/get-user-activity
- User position value: https://docs.polymarket.com/api-reference/core/get-total-value-of-a-users-positions
- Trader leaderboard: https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings
- Accounting snapshot: https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs
- Official Python SDK: https://docs.polymarket.com/api-reference/clients-sdks and https://github.com/Polymarket/py-clob-client-v2
- Data OpenAPI spec: https://docs.polymarket.com/api-spec/data-openapi.yaml

## Endpoints encontrados

### `GET https://data-api.polymarket.com/v1/leaderboard`

Endpoint publico documentado para ranking de traders. Permite `user=<address>`, `orderBy=PNL`, `category=OVERALL` y `timePeriod=DAY|WEEK|MONTH|ALL`.

Campos relevantes:

- `proxyWallet`
- `vol`
- `pnl`
- `rank`
- `userName`

Lectura: es el unico endpoint oficial encontrado que devuelve un P&L agregado por horizontes equivalentes a 1D/1W/1M/ALL. La documentacion no afirma que sea exactamente el mismo calculo del dashboard de portfolio, ni explica la metodologia.

### `GET https://data-api.polymarket.com/positions`

Endpoint publico de posiciones actuales por `user`.

Campos relevantes:

- `initialValue`
- `currentValue`
- `cashPnl`
- `percentPnl`
- `totalBought`
- `realizedPnl`
- `percentRealizedPnl`
- `curPrice`
- `redeemable`
- `mergeable`

Lectura: sirve para P&L por posicion abierta/current, no para un P&L agregado por 1D/1W/1M/ALL.

### `GET https://data-api.polymarket.com/closed-positions`

Endpoint publico de posiciones cerradas por `user`.

Campos relevantes:

- `totalBought`
- `realizedPnl`
- `timestamp`
- `curPrice`

Lectura: sirve para realized P&L por posicion cerrada, paginado y filtrable, pero no devuelve directamente horizontes dashboard.

### `GET https://data-api.polymarket.com/v1/market-positions`

Endpoint publico por mercado, con filtro opcional `user`.

Campos relevantes:

- `currentValue`
- `cashPnl`
- `realizedPnl`
- `totalPnl`
- `totalBought`

Lectura: aporta `totalPnl = cash_pnl + realized_pnl` segun la propia descripcion del sort, pero en contexto de un mercado; no es endpoint de portfolio dashboard por horizonte.

### `GET https://data-api.polymarket.com/value`

Endpoint publico de valor total de posiciones por `user`.

Campos relevantes:

- `value`

Lectura: valor de posiciones, no P&L.

### `GET https://data-api.polymarket.com/activity`

Endpoint publico de actividad por `user`, con filtros `start`, `end`, `type`, `side`.

Tipos documentados:

- `TRADE`
- `SPLIT`
- `MERGE`
- `REDEEM`
- `REWARD`
- `CONVERSION`
- `MAKER_REBATE`
- `REFERRAL_REWARD`

Lectura: util para auditoria/reconstruccion parcial. No documenta deposits/withdrawals como cash flows completos de wallet.

### `GET https://data-api.polymarket.com/v1/accounting/snapshot`

Endpoint publico por `user` que devuelve un ZIP con `positions.csv` y `equity.csv`.

Lectura: puede ser relevante para contabilidad externa, pero la documentacion no especifica columnas, metodologia, frecuencia, ni equivalencia con 1D/1W/1M/ALL.

## Auth requerida

- Data API: publica, sin autenticacion documentada.
- Gamma API: publica, sin autenticacion documentada.
- CLOB read endpoints: publicos para orderbook/precios/spreads.
- CLOB trading/account endpoints: requieren L1/L2 auth. L1 usa firma EIP-712 con private key para crear/derivar API credentials. L2 usa `apiKey`, `secret`, `passphrase` y headers `POLY_*`.
- Para esta investigacion no hace falta private key si se limita a Data API publica por address.

## Rate limits documentados

- Data API general: 1,000 req / 10s.
- Data API `/trades`: 200 req / 10s.
- Data API `/positions`: 150 req / 10s.
- Data API `/closed-positions`: 150 req / 10s.
- Rate limits tambien mencionan `User PNL API`: 200 req / 10s, pero no encontre una pagina ni ruta publica correspondiente en `llms.txt` ni en el OpenAPI consultado.

## SDK Python oficial

Polymarket documenta SDKs oficiales TypeScript, Python y Rust para CLOB. El paquete Python actual documentado es `py-clob-client-v2` / `py_clob_client_v2`.

Cobertura documentada:

- market data CLOB,
- order management,
- authentication,
- order creation/posting/cancellation,
- account/trading data CLOB autenticada.

No encontre cobertura oficial del SDK Python para Data API portfolio/P&L, ni un wrapper oficial para `/positions`, `/closed-positions`, `/activity`, `/value` o `/v1/leaderboard`.

## Respuestas directas

- Endpoint publico o autenticado que sirve el P&L del dashboard: no encontre un endpoint oficial documentado como "dashboard portfolio P&L". El candidato mas cercano es `GET /v1/leaderboard?user=<address>&timePeriod=DAY|WEEK|MONTH|ALL&orderBy=PNL`, publico, pero documentado como leaderboard, no como dashboard.
- Devuelve P&L por timeframes 1D/1W/1M/ALL: `GET /v1/leaderboard` devuelve `pnl` por `DAY`, `WEEK`, `MONTH`, `ALL`. Otros endpoints no devuelven horizontes agregados.
- Devuelve realized P&L: si, `/closed-positions` y `/positions` incluyen `realizedPnl`; `/v1/market-positions` tambien.
- Devuelve unrealized P&L: si, `/positions` incluye `cashPnl`; `/v1/market-positions` documenta `cashPnl` como unrealized cash PnL en el sort.
- Devuelve total P&L: si, `/v1/market-positions` incluye `totalPnl`; `/v1/leaderboard` incluye `pnl` agregado por periodo, metodologia no explicada.
- Devuelve cash flows / deposits / withdrawals: no encontre un endpoint oficial de cash flows completos. `/activity` cubre trades, splits, merges, redemptions, rewards, conversions and rebates; Bridge docs cubren operaciones bridge, pero no una serie historica completa de deposits/withdrawals para P&L.
- Permite consultar por address publica sin private key: si para los endpoints Data API anteriores.
- Requiere autenticacion: no para Data API. Si se usa CLOB autenticado, requiere L1/L2 segun docs, con private key para derivar credenciales.
- Rate limits: si, documentados como arriba.
- SDK Python oficial: si para CLOB; no encontre SDK oficial Python para Data API/P&L.
- Metodologia de calculo: opaca para `leaderboard.pnl`, `positions.cashPnl`, `realizedPnl` y el posible dashboard P&L. La documentacion lista campos, pero no especifica formula completa, tratamiento de fees, redemptions pendientes, resolved/redeemable, cash flows, deposits/withdrawals, cambios de proxy wallet, o reconciliacion temporal.

## Limitaciones

- `DAY/WEEK/MONTH/ALL` en leaderboard son equivalentes de naming a 1D/1W/1M/ALL, pero no estan documentados como el mismo widget del dashboard.
- `leaderboard.pnl` puede ser suficiente para sanity check externo, pero no descompone realized vs unrealized ni cash flows.
- Posiciones current/closed permiten reconstrucciones parciales, pero la metodologia y edge cases quedan fuera de contrato oficial.
- `User PNL API` aparece en rate limits, pero no se encontro ruta documentada en el indice ni en OpenAPI; tratar como pista no integrable hasta encontrar documento oficial o especificacion estable.
- El ZIP contable puede ser prometedor, pero sin schema de columnas documentado no debe asumirse como canonical ni como match del dashboard.

## Riesgos

- Falsa canonizacion: confundir `leaderboard.pnl` con P&L operacional validado.
- Drift metodologico: Polymarket puede cambiar calculos de dashboard/leaderboard sin versionado visible.
- Resolved/redeemable: posiciones resueltas no redimidas pueden distorsionar `currentValue`/`cashPnl`.
- Cash flow blindness: sin deposits/withdrawals confiables, no sustituye `wallet_cash_flows`.
- Timeframe ambiguity: `DAY/WEEK/MONTH/ALL` no define zona horaria, ventanas exactas ni corte temporal.
- Auth creep: usar CLOB autenticado para esta fuente aumentaria riesgo sin aportar un endpoint dashboard P&L claro.

## Recomendacion

**Resultado principal: A) viable integrar como `external_observability`, con alcance muy limitado.**

**Resultado condicionado: D) requiere mas investigacion solo si se exige equivalencia exacta con el dashboard P&L.**

Fuente propuesta solo para futuro:

- `polymarket_api_pnl.leaderboard_day_week_month_all`
- Data API publica,
- sin private key,
- sin L1/L2,
- sin credenciales,
- sin firma wallet,
- solo `user=<proxyWallet/address>` + `timePeriod=DAY|WEEK|MONTH|ALL`.

Uso permitido:

- cross-check,
- sanity bound,
- comparacion humana contra `tools/pnl_report.py`,
- etiqueta obligatoria `source=polymarket_api_pnl`,
- `quality=external_opaque`,
- `confidence<=low` hasta que se valide contra dashboard manual.

Uso no permitido:

- canonical source,
- bankroll readiness,
- BANKROLL $35,
- Fase C,
- BUY/SELL/SKIP,
- sizing,
- whitelist,
- scheduler,
- Telegram accionable.

Si el requisito estricto es "endpoint oficial que replica exactamente el dashboard portfolio P&L 1D/1W/1M/ALL con metodologia documentada", la respuesta actual baja a **D) requiere mas investigacion**, porque el endpoint no aparece documentado como tal.

## Guardrails

- Polymarket API P&L nunca debe ser `canonical_source` por si sola.
- No desbloquea `bankroll_readiness`.
- No autoriza BANKROLL $35.
- No Fase C.
- No BUY/SELL/SKIP.
- No Telegram accionable.
- Solo cross-check / sanity bound.
