# REGISTRO DE RIESGOS — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/risk-register.md` |

> Convención: `RSK-010-XXX`. Probabilidad/Impacto: B(aja)/M(edia)/A(lta).

| ID | Riesgo | Prob | Imp | Mitigación | Dueño | Estado |
|---|---|---|---|---|---|---|
| RSK-010-001 | Sin servidor central real, el cliente no se puede probar en producción | M | A | Cliente configurable + fake server en tests (SU-010-01) | Arquitecto | Activo |
| RSK-010-002 | Manipulación del reloj local durante la gracia offline | M | A | `last_reliable_date` + verificación remota periódica | Arquitecto | Activo |
| RSK-010-003 | Matriz de entitlements desactualizada | M | M | Snapshots versionados + reintento de sincronización | Producto | Activo |
| RSK-010-004 | Regresión en el módulo licensing de 001 al extenderlo | M | A | Pruebas existentes + nuevas; no redefinir entidades | Arquitecto | Activo |
| RSK-010-005 | Bloqueo de escrituras insuficiente en READ_ONLY/SECURITY_SUSPENSION | M | A | Refuerzo con `ensure_write_allowed` y pruebas | Arquitecto | Activo |
| RSK-010-006 | Duplicación/colisión en sincronización (idempotencia) | B | M | Clave de idempotencia + registro por ejecución | Arquitecto | Activo |
