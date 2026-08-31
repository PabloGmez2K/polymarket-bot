# ACTIVE_DECISION_STATE — polymarket-bot

Estado decisorio **activo** del workstream en curso. Lo lee el orquestador antes de proponer un plan
o abrir agente (`ORCHESTRATOR.md`, comprobación consciente de decisiones).

No es un historial. No sustituye a `HISTORIAL_SESIONES.md`, `CONTEXTO.md` ni los contratos de
dominio (`ORCHESTRATOR.md`, `AGENTS.md`, `OPERATIONS_PLAYBOOK.md`): cubre el hueco de lo
**rechazado**, que no tenía hogar durable y volvía a proponerse.

- Una opción en `REJECTED` no se vuelve a proponer sin cumplir su `reopen_if`.
- Al cerrar el workstream, las decisiones durables se trasladan a `HISTORIAL_SESIONES.md`/
  `CONTEXTO.md` u otra fuente existente, y este archivo se limpia o se reancla al workstream
  siguiente.
- No almacena transcripts, logs, razonamiento interno ni evidencia cruda: solo la decisión, su
  motivo y su condición de reapertura.
- Si una entrada solo describe trabajo pendiente, pertenece a `CONTEXTO.md` o al trigger vivo
  correspondiente, no aquí.

La coherencia de las **normas durables a través del tiempo** no vive aquí: es el sujeto
`NORMATIVE_STATE` de `PATTERN-16 REPOSITORY_GROUNDED_PREFLIGHT`, con `HISTORIAL_SESIONES.md`,
`CONTEXTO.md` y los contratos operativos como corpus.

## Estado

Sin workstream activo. Al abrir el primero, rellenar este bloque; no acumular aquí el estado de
workstreams cerrados.

```yaml
WORKSTREAM:
  active: NONE
  excluded: NONE

ACCEPTED: []

REJECTED: []

UNRESOLVED: []
```

---

## Historial de cambios

| Fecha | Cambio | Quién |
|-------|--------|-------|
| 2026-08-31 | Creado vacío como parte de la adopción MR-013.1 / MR-014. | Claude Sonnet 5 |
