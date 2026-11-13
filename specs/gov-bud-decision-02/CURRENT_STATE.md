# CURRENT_STATE · D-GOV-02 (HEAD c93311a, 2026-11-13)

## Decisión

```text
D_GOV_02_EXPLICIT_OWNER_DECISION_FOUND=0
DECISION_SOURCE=—   DECISION_DATE=—   DECISION_SCOPE=—
D_GOV_02_STATUS=OPEN
```

Revisé todo el repositorio y la memoria del proyecto:

- `D-GOV-02` aparece en el IR §15, el source register, la start-readiness, el architecture baseline, las matrices de completitud y las matrices de desbloqueo de ciclos anteriores.
- **Todas** la registran como OPEN.
- La única decisión del sponsor registrada (2026-11-07) cierra D-GOV-01 (Naguanagua) y D-GOV-07 (Atenea). No toca D-GOV-02.
- Ninguna implementación parcial, comentario ni inferencia cuenta como decisión.

## Lo que existe en Gobierno y sirve a la cadena presupuestaria

| Pieza | Estado | Relación con BUD |
|---|---|---|
| `ejercicio` (año calendario) en ORG-02, TRE-02 y CTL-05 | Entero, sin entidad propia | LOPPM art. 250 lo confirma. Un BUD-01 debería ser la entidad de ejercicio **sin romper** esos enteros |
| ORG-01 ente, con `TIPOS_DE_ACTO` que incluye ORDENANZA | READY | El ente y sus actos fundacionales |
| ORG-02/03/04/07: estructura, cargos con competencia y límite (`Numeric(18,2)`), ocupación y matriz de autoridad | READY | Autoridad para comprometer, modificar y certificar (N03) |
| DOC-02 actos administrativos (LOPA: DECRETO, RESOLUCION…) | READY | Sirve para traspasos y resoluciones del alcalde. La **ordenanza** del Concejo no es un acto LOPA (ver ARCHITECTURE_CONSEQUENCES) |
| DOC-08 paquete documental y almacenamiento de documentos | READY | Soporte de la ordenanza y de cada modificación; no se crea almacenamiento paralelo |
| CTL-02 bitácora institucional | READY | Única bitácora; no se abre un segundo ledger de auditoría |
| CTL-01/PROC-11 SoD | READY | Separar quien certifica disponibilidad de quien compromete |
| CTL-10 cierres | READY | Patrón de cierre por período |
| TRE-01 cuentas, TRE-02 programación de caja | READY | Caja separada del presupuesto (N05). TRE-02 declara «Presupuesto solo consulta» (OD-TRE02-04) |
| Modelos de presupuesto (ejercicio, clasificador, crédito, compromiso, modificación) | **No existen** | 0 tablas `gov_budget_*` y 0 rutas |
| Catálogo del clasificador ONAPRE (N10) | **No custodiado** | No se puede precargar ningún código |

## Otros bloqueos vigentes, recalculados

- `N37_STATUS=BLOCKED_EXTERNAL_SOURCE`: faltan la ordenanza de presupuesto del ejercicio y el manual presupuestario de Naguanagua.
- `PROC09_STATUS=BLOCKED`: U.T. sin fuente, 3 % frente a 1-5 %, y monto de la oferta (OBS-PROC08-MONTO-01).
- `QA_PGDUMP_ENV_DEBT=OPEN`, `PRODUCT_BLOCKER=0`: no afecta la decisión ni el modelo presupuestario.
