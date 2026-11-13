# OWNER_DECISION · D-GOV-02 Profundidad presupuestaria

```text
STATUS=PENDING_OWNER_DECISION
DECIDED_BY=—
DECISION_DATE=—
```

Hay que responder 4 preguntas. Las opciones completas están en OPTIONS.md; la recomendación de Claude, en RECOMMENDATION.md.

| Id | Pregunta | Opciones | Recomendación de Claude |
|---|---|---|---|
| D02-A | ¿Qué profundidad presupuestaria cubre v1.0? | **A** aprobado + ejecución completa, formulación después · **B** formulación completa + ejecución · **C** control mínimo de disponibilidad | **A** |
| D02-B | ¿De dónde sale el catálogo del clasificador ONAPRE de cada ejercicio? | **1** lo registra o importa el ente, con procedencia (edición, fecha y documento), sin precarga · **2** se espera la copia oficial custodiada antes de cargar el aprobado | **1** |
| D02-C | ¿Los niveles de la estructura programática (sector, programa, subprograma, proyecto, acción o actividad) son fijos o configurables por ente? | **1** configurables por ente y ejercicio («categorías equivalentes», LOPPM 239) · **2** fijos | **1** |
| D02-D | ¿El precompromiso o reserva (GOV-BUD-011) se usa en v1.0? | **1** activable por ente, apagado por defecto hasta tener el manual local (N37) · **2** siempre activo · **3** fuera de v1.0 | **1** |

## Lo que cambia según la respuesta

- **Con A, 1, 1, 1:** `D_GOV_02_STATUS=CLOSED`. Siguiente ciclo: BUD-01 + BUD-02 «Ejercicio presupuestario y su clasificador versionado», producto completo con menú, UAT y E2E.
- **Con B:** el mismo primer ciclo. BUD-05 completo queda bloqueado por N08 y N37 hasta tener esas fuentes en custodia.
- **Con C:** se registra la divergencia con LOPPM 239 y con GOV-BUD-014..017 P0 como riesgo aceptado por la dueña.

**Esta decisión la toma la dueña.** Claude no la marcará como cerrada sin una instrucción explícita.
