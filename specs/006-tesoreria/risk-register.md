# REGISTRO DE RIESGOS — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/risk-register.md` |

> Escala: P (probabilidad 1-5) × I (impacto 1-5) = R (riesgo). Umbral de acción R ≥ 8.

| ID | Riesgo | P | I | R | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RSK-006-01 | Duplicar la lógica de pagos/cobros de 004/005 | 2 | 4 | 8 | Contrato v1 de integración; consumir `ap_payments` y cobros de 005 | Arquitecto | Vigente |
| RSK-006-02 | Confundir IGTF con IVA adicional | 3 | 4 | 12 | Eventos separados por tipo; reglas versionadas; pruebas específicas | Contador | Vigente |
| RSK-006-03 | Cierre de caja con diferencia no aprobada | 3 | 3 | 9 | FR-006-003: bloquear cierre sin aprobación/justificación | Tesorería | Vigente |
| RSK-006-04 | Emparejamiento incorrecto en conciliación | 3 | 3 | 9 | Reglas de match + resolución manual auditada (FR-006-030) | Contador | Vigente |
| RSK-006-05 | Maestros financieros faltantes retrasan la entrega | 2 | 3 | 6 | Prerequisito en F1 (CL-006-05) | Arquitecto | Vigente |
| RSK-006-06 | Pérdida de trazabilidad por edición de saldos | 2 | 4 | 8 | Saldos calculados desde movimientos/cierres; reversos vinculados (P5) | Arquitecto | Vigente |
| RSK-006-07 | Acoplamiento frágil con 007 (IGTF) | 2 | 2 | 4 | Estructura por regla/evento sin acoplar motor | Arquitecto | Vigente |
| RSK-006-08 | Duplicación de POST sin idempotencia | 2 | 3 | 6 | Idempotency key en ejecución de ingresos/egresos | Arquitecto | Vigente |
