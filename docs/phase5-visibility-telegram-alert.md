# Phase 5 Visibility Telegram Alert

Alerta one-shot para la fase 5.

Su objetivo es avisar por Telegram cuando aparezca una coincidencia nueva `Shanghai + Chicago` en el tracker de visibilidad.

---

## Condicion de disparo

Solo avisa cuando:

- el `city_probe_visibility_tracker` detecta `simultaneous_visibility=true`
- y esa coincidencia corresponde a un `probe_generated_at` que aun no fue notificado

---

## Anti-spam

Usa estado persistente en:

- `data/phase5_visibility_alert_state.json`

Con eso evita repetir la misma alerta en cada corrida.

---

## Comando base

```powershell
python tools/phase5_visibility_telegram_alert.py
```

### Variante segura

```powershell
python tools/phase5_visibility_telegram_alert.py --dry-run
```

---

## Requisitos

Variables de entorno ya usadas por el repo:

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## Salidas

- `data/phase5_visibility_alert_state.json`
- `docs/phase5_visibility_alert_latest.md`

---

## Guardrails

- no toca `bot.py`
- no toca trading
- solo envia una alerta cuando hay evidencia nueva y util
