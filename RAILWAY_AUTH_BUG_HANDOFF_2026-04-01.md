# Railway Auth Bug Handoff — 1 abril 2026

## Problema

El Railway CLI pide reloguearse continuamente y comandos como `status` / `whoami` terminan en:

- `Unauthorized. Please run railway login again.`
- `Warning: failed to refresh OAuth token: Token refresh failed: invalid_grant`

## Evidencia local confirmada

### 1. El entorno sigue contaminado por proxies rotos

Variables presentes en la shell:

- `HTTP_PROXY=http://127.0.0.1:9`
- `HTTPS_PROXY=http://127.0.0.1:9`
- `ALL_PROXY=http://127.0.0.1:9`
- `GIT_HTTP_PROXY=http://127.0.0.1:9`
- `GIT_HTTPS_PROXY=http://127.0.0.1:9`

Esto no es teórico: el wrapper `tools/railway_safe.ps1` existe justo para limpiar esas variables antes de invocar Railway.

### 2. El config de Railway existe y está enlazado al proyecto

Ruta:

- `%USERPROFILE%\.railway\config.json`

Estado observado:

- archivo presente
- proyecto `C:\Projects\polymarket-bot` enlazado
- `accessToken` presente
- `refreshToken` presente
- `tokenExpiresAt = 1775077531`
- ese expiry corresponde a `2026-04-01T21:05:31Z`

### 3. Aun con wrapper, Railway falla

El wrapper limpia proxies a nivel de proceso, pero:

- `railway_safe.ps1 status` => `Unauthorized`
- `railway_safe.ps1 whoami` => `invalid_grant`
- `railway_safe.ps1 login` => no se puede completar desde sesión no interactiva

## Hipótesis más probable

La explicación más sólida con la evidencia actual es:

1. El entorno local arrastra proxies muertos (`127.0.0.1:9`).
2. Algún login o refresh anterior ocurrió con ese entorno contaminado o desde un contexto donde la CLI no pudo completar bien el ciclo de auth.
3. El `config.json` quedó con credenciales incoherentes:
   - hay `accessToken` y `refreshToken`,
   - pero Railway rechaza el refresh con `invalid_grant`,
   - así que la CLI entra en bucle de “vuelve a loguearte”.
4. Como `railway login` requiere shell interactiva del usuario, Codex no puede cerrar el ciclo desde esta sesión.

## Importante: qué NO está 100% demostrado todavía

No está demostrada de punta a punta una sola causa única del tipo:

- “es solo el proxy”
- o “es solo un problema de permisos sobre `config.json`”
- o “es solo token caducado”

De hecho, la evidencia actual apunta a una combinación más realista:

- proxy contaminado persistente;
- credenciales ya degradadas;
- necesidad de login interactivo;
- y posible historial previo de refresh incompleto.

## Qué hacer en la sesión dedicada

### Objetivo

No tocar trading ni dashboard. Solo aislar y corregir el bug de auth de Railway.

### Plan sugerido

1. Identificar de dónde salen las variables proxy `127.0.0.1:9`.
2. Validar si reaparecen al abrir una shell nueva.
3. Hacer `railway login` en shell interactiva limpia del usuario.
4. Confirmar que `whoami`, `status`, `logs` y `ssh` funcionan sin wrapper raro adicional.
5. Ver si el wrapper sigue siendo suficiente o si hay que endurecerlo.
6. Documentar causa raíz real y fix permanente en `OPERATIONS_PLAYBOOK.md`.

### Checks concretos para esa sesión

- `Get-ChildItem Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY,Env:GIT_HTTP_PROXY,Env:GIT_HTTPS_PROXY`
- revisar si esas variables vienen de:
  - perfil de PowerShell;
  - variables de usuario/sistema;
  - arranque de VS Code;
  - otra herramienta local
- revisar timestamps y contenido de `%USERPROFILE%\.railway\config.json` antes y después del login
- probar:
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami`
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status`
  - `powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 logs -s polymarket-bot -n 20`

## Estado de contexto ya guardado

La memoria del proyecto ya quedó persistida en:

- `CONTEXTO.md`
- `HISTORIAL_SESIONES.md`
- `SNAPSHOT_ANALITICO_LIVE_2026-04-01.md`

Este archivo existe para que la siguiente sesión pueda arrancar casi “en frío”, enfocada solo en Railway auth.
