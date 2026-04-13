# System Mental Model - 2026-04-11

## Para Que Sirve Este Documento

Bajar a tierra que sistema estamos construyendo, que parte ya esta alineada, que parte sigue abierta y cual es el siguiente paso logico sin mezclar observacion, policy y monetizacion.

## La Idea En Una Frase

Estamos construyendo un sistema de trading meteorologico con una capa operativa que ejecuta de verdad y una capa de inteligencia read-only que observa, audita y evita que tomemos decisiones con una foto falsa del sistema.

## Las 3 Capas Del Sistema

### 1. Capa de ejecucion

Fuente de verdad: `polymarket-bot`

Esta capa:

- escanea mercados
- filtra por fecha, precio, ciudad, condicion y liquidez
- calcula edge
- selecciona oportunidades
- ejecuta buys reales
- cierra posiciones
- escribe los artefactos runtime

Pregunta que responde:

- que hizo realmente el bot

## 2. Capa de estado observable

Fuentes principales:

- `data/runtime_import/runtime_import_manifest.json`
- `data/runtime_policy_effective_view.json`
- `data/runtime_import/cycles_history.jsonl`
- `data/runtime_import/skip_log.jsonl`
- `data/runtime_import/postmortem.json`
- `data/runtime_import/shadow_city_tracking.json`

Esta capa:

- congela una foto read-only de runtime
- dice que snapshot es valido
- dice que ciudad esta en que modo efectivo
- deja ver por donde se estrecha el funnel
- deja ver que trades cerraron y como

Pregunta que responde:

- que evidencia real tenemos hoy para interpretar el sistema

## 3. Capa de inteligencia y decision

Fuentes principales:

- `tools/system_alignment_check.py`
- `docs/runtime_policy_effective_view_latest.md`
- `docs/system_alignment_check_latest.md`
- `docs/system_alignment_check_operational_latest.md`
- `docs/step5-throughput-observation-2026-04-11.md`
- `docs/step5-throughput-observation-extended-2026-04-11.md`
- `docs/shadow-opportunity-shortlist-2026-04-11.md`

Esta capa:

- audita si el sistema esta alineado
- traduce artefactos tecnicos a lectura humana
- separa ruido documental de blockers reales
- ayuda a decidir si toca observar, corregir o escalar

Pregunta que responde:

- podemos confiar en la lectura actual y cual es el siguiente paso correcto

## Regla Madre De Fuente De Verdad

- `polymarket-bot` ejecuta y manda sobre runtime
- `city-intelligence` recomienda y audita, pero no actua
- docs y prompts deben reflejar esa verdad, no inventarla

## Que Ya Esta Cerrado O Bastante Cerrado

- snapshot runtime atomico y manifestado
- effective view por ciudad
- preflight `observe` y `operational`
- naming canonico del funnel
- separacion entre `runtime_derived_targets` y `exploratory_targets`
- limpieza del claim de `Dallas` como blocker declarativo falso

En lenguaje simple:

ya no estamos pilotando a ciegas ni mezclando varias verdades sobre la misma ciudad o la misma metrica.

## Que Todavia No Esta Cerrado

- demostrar throughput repetible con muestra mas grande
- decidir si el siguiente problema es observacion o correctness
- validar que Dashboard y Telegram cuentan la misma historia que los artefactos canonicos
- abrir una conversacion honesta de monetizacion con evidencia menos fragil

## Lo Que Hemos Demostrado Hasta Ahora

- el sistema puede producir trades reales
- `auto_canary` no es solo decoracion: ya produjo trades reales
- el preflight operacional ya no esta bloqueado por colisiones falsas
- el cuello principal observado sigue siendo estructural antes de edge y seleccion

## Lo Que Todavia No Hemos Demostrado

- que el throughput actual sea suficientemente repetible
- que ya toque cambiar policy
- que ya sea honesto hablar de monetizacion controlada
- que Dashboard y Telegram esten totalmente alineados con la arquitectura nueva

## Que Significa "Subir Un Escalon"

No significa aun subir bankroll ni forzar mas trades.

El siguiente escalon real seria demostrar esto:

- preflight `operational` sigue verde
- hay mas ciclos nuevos de verdad
- varias `auto_canary` convierten de forma menos intermitente
- aumenta el numero de cierres recientes sin tocar policy
- no aparece bug nuevo de accounting/counters

Si eso se sostiene, entonces el siguiente debate deja de ser "esta alineado?" y pasa a ser "seguimos observando o ya existe base para una discusion operativa superior?".

## Donde Encajan Dashboard Y Telegram

Dashboard y Telegram ya no son una capa decorativa.

Su trabajo correcto ahora es:

- contar la misma historia que los artefactos canonicos
- priorizar lo que cambia la decision de hoy
- no arrastrar wording viejo o ambiguedades de fases anteriores
- no sonar mas seguros que la evidencia real disponible

Por eso, si alignment base ya esta razonablemente cerrado, el siguiente frente logico es una auditoria read-only de Dashboard y Telegram.

## Siguiente Paso Logico Recomendado

Sesion dedicada y acotada a:

- revisar Dashboard y Telegram
- contrastarlos contra `runtime_policy_effective_view`, `system_alignment_check`, `metrics-funnel-naming` y los readouts actuales
- detectar drift semantico, mensajes stale o bloques que ya no ayuden a decidir
- dejar un readout corto de que esta alineado, que confunde y que conviene corregir despues

## Cuando Tiene Sentido Llamar A Opus Otra Vez

No por inercia.

La siguiente review de Opus tiene sentido cuando ocurra una de estas dos cosas:

1. hay evidencia nueva material:
   - otra ventana real de ciclos frescos
   - mas cierres
   - mejor lectura de si `auto_canary` se sostiene

2. aparece una contradiccion seria:
   - bug real de correctness
   - Dashboard/Telegram contradicen la capa canonica
   - una pieza vuelve a producir drift operativo

## Veredicto Aterrizado

- si: la arquitectura base ya esta bastante alineada
- no: todavia no estamos en punto de monetizacion honesta
- si: el trabajo hecho ya es rentable como infraestructura de decision
- siguiente escalon: pasar de sistema alineado a sistema operativamente repetible
- siguiente sesion recomendada: auditoria read-only de Dashboard y Telegram
