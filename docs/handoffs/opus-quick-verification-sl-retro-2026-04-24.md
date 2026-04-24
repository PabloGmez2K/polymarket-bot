# Verificación rápida con Opus — cierre SL Retro / Briefing Diario

## Objetivo

Hacer una comprobación final, corta y operativa, tras el deploy de la sesión 234.

## Qué debe verificar Opus

1. Confirmar que el estado live ya no deja `UNKNOWN` en `SL Retro`.
2. Confirmar que el veredicto agregado sigue siendo:
   - `16/16` resueltos
   - `6 RIGHT`
   - `10 WRONG`
   - `0 UNKNOWN`
   - conclusión firme: `SL funciona correctamente`
3. Confirmar que el `Briefing Diario` ya no muestra como `POSICIONES ABIERTAS` filas legacy con fecha de resolución pasada.
4. Revisar si el bloque `ÚLTIMAS 24H` se entiende sin ambigüedad humana:
   - lado comprado
   - precio de entrada
   - precio de salida si existe
   - motivo de cierre en lenguaje claro
5. Señalar cualquier drift entre:
   - `trade_lifecycle`
   - `sl_retrospective`
   - `daily_position_briefing`
   - y el mensaje real de Telegram

## Comandos sugeridos

```powershell
python tools/sl_retrospective.py --dry-run
python tools/daily_position_briefing.py --dry-run
python verify_before_deploy.py
```

Si Opus necesita leer live en Railway, que priorice comprobaciones read-only y responda con:

- estado confirmado
- discrepancias encontradas
- si hace falta otro patch o si la sesión puede darse por cerrada
