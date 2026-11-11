# CTL05_POSTCLOSE_RECONCILIATION · 2026-11-11

Entrada: HEAD = origin/develop = `ec358b6`; Alembic `0100_gov_ctl05_rendicion` (una cabeza); P2 no publicó después.

```text
CTL05_PRODUCT_STATUS=OWNER_UAT_READY
CTL05_OWNER_UAT_READY=YES
CTL05_OWNER_ACCEPTED=NO

PROCESS_DEVIATION_GLOBAL_DEEPSEEK_CALLS=1
DEEPSEEK_HARD_CAP_FUTURE=8

MIGRATION_AUTHORSHIP_CLASSIFICATION=A (mecánico permitido)

P2_BASELINE_HEAD=6e778a4
P1_CTL05_HEAD=ec358b6

P2_BASELINE_VITEST_PASS=1911   (Node 22.23.4)
P2_BASELINE_VITEST_FAIL=0
P1_HEAD_VITEST_PASS=1922       (Node 22.23.4)
P1_HEAD_VITEST_FAIL=0

PREEXISTING_FRONTEND_FAILURES_CONFIRMED=0
NEW_FRONTEND_FAILURES=0

CTL05_REOPEN_REQUIRED=0
```

## OBS-CTL05-ORCH-01: volumen de llamadas a DeepSeek

CTL-05 usó 33 llamadas: 3 antes del incidente del puente y 30 después. Ningún subproblema pasó de 2 reintentos, pero el volumen global incumple el objetivo de orquestación, así que `PROCESS_DEVIATION_CONFIRMED = 1`. CTL-05 no se reabre por esto.

Política actualizada en `docs/governance/ai-orchestration-policy.md` §6:
- **Regla A:** 2 reintentos por subproblema.
- **Regla B:** tope global de **8 llamadas por ciclo**, con un objetivo de 2 a 4.
- Al llegar a 8 se hace un alto semántico; superarlo exige decisión de la dueña.

## OBS-CTL05-MIG-01: autoría de la migración

**Caso A, mecánico permitido.** `MIGRATION_AUTHORSHIP_VIOLATION = 0`.

**Lo que escribió DeepSeek (evidencia en las respuestas guardadas en `herramientas/ctl05`):**
- **C4R:** cambió `down_revision` de `0097_fusion_gov_replenishment` a `0098_dispatch_cost_relief` y `revision` de `0098_gov_ctl05_rendicion` a `0099_gov_ctl05_rendicion`. Incluyó la línea `RENAME 0098_gov_ctl05_rendicion.py -> 0099_gov_ctl05_rendicion.py`.
- **C32:** cambió `down_revision` a `0099_quote_award` y `revision` a `0100_gov_ctl05_rendicion`. Incluyó la línea `RENAME … -> 0100_gov_ctl05_rendicion.py`.
- **C1, C16 y C23:** escribió el contenido: tablas, CHECK, disparadores con `::text`, `server_default` y BigInteger.

**Lo que hizo Claude:**
- `mv` del fichero, ejecutando literalmente las dos líneas RENAME de DeepSeek (nombre físico, sin tocar el contenido);
- `ruff --fix --select I001` sobre la migración: reordenó `import sqlalchemy as sa` / `from alembic import op`. Es formato puro, sin cambio semántico, y ya estaba declarado en el CIERRE.

Claude no modificó `revision`, `down_revision`, upgrade, downgrade, SQL, esquema, constraints ni índices. La regla sigue: **DeepSeek escribe y modifica las migraciones**.

## OBS-CTL05-VITEST-01: contradicción del baseline

**Caso C, diferencia de entorno.**

**Entorno común a todas las ejecuciones:**
- **Comando:** `node node_modules/vitest/vitest.mjs run` desde `resources/frontend`, en worktrees temporales exactos de `6e778a4` y `ec358b6`.
- **Dependencias:** el mismo `node_modules`, enlazado desde el repositorio principal.
- **Herramientas:** npm 11.19.0. `package.json` exige `node >= 20` y no fija versión.

| Head | Node 24.21.0 | Node 22.23.4 |
|---|---|---|
| `6e778a4` (P2) | 1888 PASS / 23 FAIL (4 ficheros) | **1911/1911 PASS** |
| `ec358b6` (CTL-05) | 1899 PASS / 23 FAIL (los mismos 4 ficheros) | **1922/1922 PASS** |

**Detalle de los fallos con Node 24:**
- **Pruebas afectadas:** las mismas 23 en los dos heads: `compras/importaciones` (9), `compras/requisiciones` (8), `compras/planificacion/necesidades` (5) y `maestros/terceros/tercerosMantenimiento` (1).
- **Causa:** común a todas, `TypeError: RequestInit: Expected signal ("AbortSignal {}") to be an instance of AbortSignal`. Es una incompatibilidad del `fetch` nativo de Node 24 con el `AbortSignal` de jsdom, no un defecto de código.

**Por qué los informes discrepaban:**
- P2 midió con un Node donde no ocurre (coincide con el resultado de 22.23.4).
- En el cierre de CTL-05 P1 midió con Node 24 y atribuyó los fallos a «preexistentes de origin». Era cierto para el entorno, pero la atribución estaba incompleta: no comparó entornos.

**Normalización (comando canónico de Vitest completo en esta estación):** `~/.nvm/versions/node/v22.23.4/bin/node node_modules/vitest/vitest.mjs run`.

**Conclusión:** CTL-05 no tiene fallos de frontend; los 23 son un artefacto de entorno.
