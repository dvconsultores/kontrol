# DEPENDENCY_MATRIX · cadena presupuestaria (recalculada desde la matriz de completitud, HEAD c93311a)

## Inventario BUD

| BUD_PROCESS_ID | REQUIREMENT_ID | PRIO | WHAT_USER_MUST_DO | CURRENT_STATUS | D_GOV_02_DEPENDENCY | OTHER_DEPENDENCIES | LEGAL_SOURCE | DOMAIN_READY |
|---|---|---|---|---|---|---|---|---|
| BUD-01 | GOV-BUD-001 | P0 | Crear el ejercicio con estado, calendario, moneda funcional, clasificador y versión normativa | BLOCKED | DIRECTA | N07 (C, estadal: no aplica a un municipio), N08 (C), N10 (C) | LOPPM 234-236, 250; N04 (A) | Sí: ORG-01, ente y año calendario |
| BUD-02 | GOV-BUD-002 | P0 | Importar y versionar el clasificador por ejercicio: código, denominación, tipo, nivel y vigencia | BLOCKED | DIRECTA | N10 (C, no custodiado) | LOPPM 239; N04 (A) | Estructura sí; catálogo no |
| BUD-03 | GOV-BUD-003, 004 | P0 | Plan, programa, subprograma, proyecto, acción específica, metas e indicadores; vincular al POA | BLOCKED | DIRECTA | N07, N08 (C); exigencia local de categoría (N37) | LOPPM 233, 239; N30, N31 (A) | Estructura programática sí; metas y POA parcial |
| BUD-04 | GOV-BUD-005 | P0 | Fuentes de financiamiento y restricciones de uso con vigencia | BLOCKED | DIRECTA | N07, N08 (C) | LOPPM 246, 247 | Sí |
| BUD-05 | GOV-BUD-006, 007, 008 | P0 | Formular ingresos y gastos (escenarios, techos); anteproyecto, proyecto y aprobado como versiones inmutables; ordenanza como fuente | BLOCKED | DIRECTA (es el núcleo de la pregunta) | N08 (C), N37 (ordenanza y calendario local) | LOPPM 229, 232-236 | Aprobado + acto: sí. Formulación: falta N08 |
| BUD-06 | GOV-BUD-009, 010 | P0 | Disponibilidad en tiempo real y certificación con saldo antes y después | NOT_STARTED | INDIRECTA (necesita el aprobado) | BUD-02, BUD-05 | LOPPM 242; N03 | Tras BUD-05 aprobado |
| BUD-07 | GOV-BUD-011 | P0 | Precompromiso o reserva «cuando el procedimiento institucional lo utilice» | BLOCKED | INDIRECTA | N37 (si Naguanagua lo usa) | N04 | Parametrizable activar o desactivar |
| BUD-08 | GOV-BUD-012 | P0 | Compromiso con autoridad, soporte y disponibilidad; sin saldo negativo silencioso | NOT_STARTED | INDIRECTA | BUD-06 | LOPPM 242, 248; N03 | Sí: ORG-07 da la autoridad |
| BUD-09 | GOV-BUD-013 | P0 | Causado separado del compromiso y del pago | BLOCKED | INDIRECTA | N36 (C, ONCOP) para el asiento contable | LOPPM 248-249; N06 | El momento presupuestario sí; el asiento no |
| BUD-10 | GOV-BUD-014, 015 | P0 | Modificaciones (traslado o traspaso, crédito adicional, rectificación, insubsistencia) con flujo y nivel de aprobación por ejercicio | BLOCKED | DIRECTA | N09 (C); límites de la ordenanza (N37, como dato) | LOPPM 241, 242, 247 | Sí para los tipos LOPPM |
| BUD-11 | GOV-BUD-016 | P0 | Ledger inmutable: aprobado + modificaciones − compromisos − causados − pagos | NOT_STARTED | INDIRECTA | BUD-05, 08, 09, 10; TRE-04 (pagado) | N03, N04, N06 | Tras la cadena |
| BUD-12 | GOV-BUD-017 | P0 | Cierre y reconducción sin borrar obligaciones | NOT_STARTED | INDIRECTA | BUD-08, BUD-09 | LOPPM 234-236, 248-249 | Sí |
| BUD-13 | GOV-BUD-018 | P1 | Formularios y reportes ONAPRE con plantillas versionadas | BLOCKED | DIRECTA | N07-N10 (C) | — | No |

## Procesos fuera de BUD con dependencia presupuestaria

| Proceso | Prio | Estado | Dependencia |
|---|---|---|---|
| REQ-01 | P0 | BLOCKED | categoría presupuestaria (BUD-03) + N37 |
| REQ-02 | P0 | NOT_STARTED | BUD-06 disponibilidad |
| REQ-05 | P0 | NOT_STARTED | BUD-07 reservas |
| CNT-01 | P0 | NOT_STARTED | BUD-08 compromiso + monto (OBS-PROC08-MONTO-01) |
| CNT-05 | P0 | NOT_STARTED | CNT-01 + BUD-08 |
| TRE-03 | P0 | NOT_STARTED | BUD-09 causado |
| TRE-08 | P0 | BLOCKED | BUD-08/09 + TRE-03/04 + ORG-06 |
| TRE-10 | P0 | NOT_STARTED | BUD-08 + CNT-01 + TRE-04 |
| ACC-05 | P0 | NOT_STARTED | BUD-11 + ACC (D-GOV-04) |
| ORG-05 | P0 | BLOCKED | BUD-03 (programa) entre 8 objetos |
| CTL-08 | P0 | BLOCKED | BUD-02 + proveedores N37 + OQ-CTL08-01 |
| REP-01 | P1 | BLOCKED | D-GOV-02 + BUD-05..11 |
| REP-02 | P1 | BLOCKED | D-GOV-02 + BUD-03 metas |
| REP-05 | P1 | NOT_STARTED | BUD-09 + TRE-03 |
| INT-05 | P1 | BLOCKED | D-GOV-02 + D-GOV-04 |
| DOC-07 | P1 | BLOCKED | BUD-03 entre varios objetos |

**Recuento.** El «11» de los ciclos anteriores se confirma, pero solo como el número de procesos que **citan** D-GOV-02:

- 10 en la columna de bloqueos: BUD-01, 02, 03, 04, 05, 10, 13, INT-05, REP-01 y REP-02;
- más CTL-08, que la cita dentro de su dependencia de dominio.

Eso no equivale a «desbloqueados por D-GOV-02»: ver D_GOV_02_UNLOCK_MATRIX.md.
