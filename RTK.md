# RTK

Shim local y neutral para la referencia `@RTK.md` usada en este repo.

Objetivo:

- evitar que la referencia dependa de cómo cada cliente resuelve archivos globales;
- mantener compatibilidad entre Codex y Claude;
- no sustituir la instalación global real de `rtk`.

## Regla de uso

Si `rtk` está disponible en la máquina, preferirlo para comandos de shell repetitivos o ruidosos.

Ejemplos:

```bash
rtk git status
rtk git diff
rtk rg "pattern" .
rtk pytest -q
```

Si un comando no está claramente soportado por `rtk`, usar el comando nativo normal.

## Verificación

```bash
rtk --version
rtk gain
```

## Nota de compatibilidad

La instalación global real puede vivir fuera del repo, por ejemplo en `~/.codex/RTK.md`.
Este archivo local existe solo como punto de resolución estable para `@RTK.md`.
