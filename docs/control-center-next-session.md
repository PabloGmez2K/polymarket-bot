# Próxima sesión recomendada — Control Center

**Fecha de planificación:** 3 de abril de 2026  
**Basado en:** `docs/control-center-roadmap.md` (Fase 1)

---

## Sesión: Quick wins HTML + Alarma sin ciclo + Verificación shadow_tracking

### Objetivo

Aplicar las correcciones de mayor impacto y menor riesgo derivadas de la auditoría del Control Center:

1. Verificar que `shadow_tracking` persiste en Railway Volume (crítico para el motor de ciudades)
2. Añadir alarma "sin ciclo en >12h" en Mission HUD (crítico para detectar bot caído)
3. Aplicar 5 quick wins de HTML que mejoran la legibilidad sin tocar Python ni el deploy

---

### Alcance cerrado

**Incluido en esta sesión:**
- [ ] Verificación de `shadow_tracking` y `city_policy_state.json` en Railway Volume
- [ ] `QW4` — añadir check "sin ciclo en >12h" en `build_dashboard_focus_center()`
- [ ] `QW1` — eliminar bloque `legacy-focus-shell` del HTML (código muerto)
- [ ] `QW2` — mover bloque Legacy drift Open-Meteo al interior del `<details>` de capa 3
- [ ] `QW3` — reordenar capa 2: NOAA + Decision engine antes de stats de trading
- [ ] `QW6` — mini-cards PnL/WR: mostrar "esperando muestra" cuando `series_stats.closed_count < 5`
- [ ] `QW7` — colapsar Readiness operativo y Desbloqueos en `<details>`
- [ ] Ejecutar `python verify_before_deploy.py` y confirmar que pasa en verde

**Excluido explícitamente de esta sesión:**
- No cerrar filas Chicago legacy open (sesión M3, ya planeada en sesión 70)
- No tocar lógica de trading, NOAA, exits, scheduler, ni gestión de posiciones
- No implementar resumen diario Telegram (sesión M4)
- No refactorizar el motor de ciudades (sesión R1)

---

### Archivos a revisar antes de empezar

| Archivo | Para qué |
|---|---|
| `templates/dashboard.html` | Identificar exactamente el bloque `legacy-focus-shell` a eliminar, la ubicación de Legacy drift y el orden actual de secciones en capa 2 |
| `bot.py` línea ~4925 | `build_dashboard_focus_center()` para añadir el check de ciclo |
| `static/dashboard.css` | Verificar que no hay estilos acoplados a los bloques que se mueven |
| `static/dashboard.js` | Verificar que no hay lógica JS acoplada a `legacy-focus-shell` |
| `bot.py` línea ~6948 | `build_dashboard_snapshot()` para confirmar qué datos se pasan al template |

---

### Checklist de validación al cierre

**Antes de commit:**
- [ ] `python verify_before_deploy.py` pasa en verde (mantener el conteo actual, no reducirlo)
- [ ] El bloque `legacy-focus-shell` ya no aparece en el HTML (ni hidden ni visible)
- [ ] El bloque Legacy drift está dentro del `<details>` de capa 3
- [ ] En la capa 2, el bloque de Observabilidad/NOAA aparece antes de las mini-cards de PnL/WR
- [ ] Las mini-cards de PnL serie y Win rate serie muestran "esperando muestra" cuando `series_stats.closed_count < 5`
- [ ] Readiness operativo y Desbloqueos están dentro de `<details>` con summary descriptivo
- [ ] El Mission HUD muestra un incidente "sin ciclo en >Xh" si `last_cycle` tiene más de 12h de antigüedad
- [ ] El dashboard se renderiza correctamente en local con `tools/preview_dashboard.py` (si aplica)

**Verificación Railway (inicio de sesión):**
```bash
# ¿shadow_tracking persiste en Volume?
rtk railway run -- ls /app/data/ | grep shadow

# ¿city_policy_state.json persiste en Volume?
rtk railway run -- ls /app/data/ | grep city_policy
```

Si `shadow_tracking` NO aparece → anotar como deuda crítica en CONTEXTO.md antes de continuar con el resto de la sesión. No bloquea los quick wins de HTML pero sí bloquea M5 y R1.

---

### Notas de contexto para arrancar

- La versión actual es `v10.6.10`; no se hace bump de versión en esta sesión (solo HTML y una pequeña adición en `build_dashboard_focus_center`)
- `verify_before_deploy.py` está en `506/506` al inicio de esta sesión
- Dallas tiene overlay shadow activo aunque aparezca en `ACTIVE_TRADING_CITIES` Railway; no cambiar eso en esta sesión
- Las 3 filas Chicago legacy open quedan pendientes para la sesión siguiente (M3)

---

### Prompt exacto para arrancar esta sesión en Claude Code

```
Contexto: estoy en la sesión de quick wins del Control Center del bot Polymarket (v10.6.10).
Antes de tocar código, ejecuta: rtk railway run -- ls /app/data/ | grep -E "shadow|city_policy"
y dime si shadow_tracking y city_policy_state.json aparecen en el Volume de Railway.

Después, implementa estos cambios en orden:

1. En bot.py, función build_dashboard_focus_center() (~línea 4925):
   añade un check de "sin ciclo en >12h". Lee el timestamp del último ciclo
   desde cycle_summary.json (campo timestamp_utc o equivalente), compara con
   datetime.utcnow(), y si han pasado más de 12h añade un incidente con
   badge="bad" y mensaje "sin ciclo en X horas — verificar que el bot sigue corriendo".
   Si no existe cycle_summary.json o el timestamp es None, añade un incidente con
   badge="warn" y mensaje "sin ciclo registrado todavía".

2. En templates/dashboard.html:
   a) Elimina el bloque completo que tiene el atributo hidden y la clase legacy-focus-shell
      (busca: <section class="layer-block legacy-focus-shell" hidden>).
      Es código muerto, ya no se usa.
   b) Mueve el card de "Drift Open-Meteo" al interior del bloque <details> de capa 3,
      después del bloque de Trofeos. Está en la grid layout-main con el card de
      "Calidad Forecast Observada (NOAA)".
   c) Reordena capa 2: el bloque de Observabilidad/NOAA (la grid layout-main que contiene
      "Calidad Forecast Observada" y "Decision engine") debe aparecer inmediatamente
      después del bloque de Estado operativo, antes de las mini-cards de PnL/WR/drawdown.
   d) En las mini-cards de PnL serie y Win rate serie, añade condición Jinja:
      si series_stats.closed_count < 5, mostrar "esperando muestra" en lugar del valor.
      El campo has_closed_count ya existe en el contexto.
   e) Envuelve las secciones de "Readiness operativo" y "Desbloqueos" (la grid layout-main
      con esos dos cards) en un <details> con summary="Readiness y desbloqueos (detalle)".

3. Ejecuta: python verify_before_deploy.py
   Debe pasar en verde con el mismo número de tests que antes (506).
   Si algún test falla, corrígelo antes de continuar.

Guardrails:
- No tocar lógica de trading, NOAA, exits, scheduler ni gestión de posiciones
- No hacer bump de versión
- No cerrar las filas legacy open de Chicago (eso es la siguiente sesión)
- No modificar static/dashboard.css ni static/dashboard.js salvo que sea imprescindible
```
