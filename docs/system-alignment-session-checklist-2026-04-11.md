# System Alignment Session Checklist - 2026-04-11

## Inicio Minimo

1. Leer `AGENTS.md`.
2. Leer el bloque vigente de `CONTEXTO.md`.
3. Correr `python tools/system_alignment_check.py`.
4. Revisar `docs/system_alignment_check_latest.md`.
5. Abrir solo el artefacto que responda la pregunta de la sesion.

## Preguntas Tipo

Si la sesion pregunta:

- "que esta roto en el cableado" -> `docs/system_alignment_check_latest.md`
- "que modo efectivo tiene una ciudad" -> `docs/runtime_policy_effective_view_latest.md`
- "que significa una metrica del funnel" -> `docs/metrics-funnel-naming.md`
- "por que el throughput esta estrecho" -> `docs/step5-throughput-observation-2026-04-11.md`
- "que ciudad shadow vigilar" -> `docs/shadow-opportunity-shortlist-2026-04-11.md`
- "que archivo es fuente de verdad de cada cosa" -> `docs/system-alignment-artifact-map-2026-04-11.md`
- "si ya podemos discutir un cambio real" -> `docs/decision-preflight-rules-2026-04-11.md`

## Regla De Trabajo

- No tocar `bot.py`.
- No escribir `city_policy_state.json`.
- No cambiar thresholds, allowlists, bankroll ni policy live.
- Primero evidencia, luego interpretacion.
- Si editas docs que mencionan metricas del funnel, vuelve a correr `python tools/system_alignment_check.py` antes de dar por cerrado el readout.
- Si la sesion va a proponer un cambio real, corre tambien `python tools/system_alignment_check.py --decision-mode operational`.

## Cuando Parar

Parar y cerrar la sesion si se cumple cualquiera de estas:

1. la pregunta de la sesion ya tiene respuesta explicita en un doc o artefacto canonico;
2. el siguiente paso implicaria tocar throughput o policy;
3. aparece una contradiccion nueva que ya no es de lectura sino de arquitectura/correctness;
4. la sesion se esta convirtiendo en mezcla de varias tareas.

## Cuando Abrir Sesion Limpia

Abrir sesion limpia cuando:

1. terminaste una auditoria/readout y el siguiente paso ya es una decision nueva;
2. vas a pedir Opus;
3. vas a pasar de alignment a throughput/policy/correctness;
4. haria falta releer demasiados artefactos para seguir sin ruido.

## Cuando Conviene Opus

Pedir revision de Opus solo si:

1. vas a proponer un cambio real de throughput o policy;
2. aparece una contradiccion nueva de arquitectura;
3. sospechas un bug de correctness y quieres validar si el siguiente paso correcto es fix tecnico o decision operacional.

## Exit Criteria De Esta Fase

Podemos considerar cerrada la fase de alignment cuando:

1. `system_alignment_check.py` siga sin errores;
2. los warnings restantes sean conocidos y aceptados, no drift nuevo;
3. las sesiones nuevas ya puedan trabajar con el mapa de artefactos y el checklist sin reabrir dudas de fuente de verdad;
4. cualquier trabajo nuevo ya sea claramente de throughput, policy o correctness, no de cableado basico.
