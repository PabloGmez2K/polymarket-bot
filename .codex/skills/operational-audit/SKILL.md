---
name: operational-audit
description: Usa esta skill para auditorias operativas del bot, dashboard, logs, Railway o estado live/local sin cambiar la logica core.
---

# Operational Audit

1. Confirmar si la auditoria es local, live o ambas.
2. Reunir evidencia minima: log, snapshot, JSON live, diff o builder local.
3. Priorizar sintomas verificables, riesgos y siguiente accion concreta.

- Para Railway, usar `tools/railway_safe.ps1`.
- Para buscar, preferir `rg`.
- Si RTK esta instalado, preferirlo para listados, busquedas y git read-only.
- No reinterpretar performance o forecast sin evidencia.
- No mezclar auditoria con refactor amplio en la misma sesion.
- No tocar trading, NOAA, scheduler o exits salvo pedido explicito.
