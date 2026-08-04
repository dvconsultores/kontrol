# CONVERGENCIA — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Ruta | `specs/006-tesoreria/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-006-01 | Cálculo completo de IGTF/retenciones (declaración, libros) | Spec 007 (núcleo fiscal) | Fiscal | Pendiente (007) |
| CVG-006-02 | Reglas de match de conciliación configurables por banco (tolerancias) | Decisión (CL-006-09) | Contador | Pendiente |
| CVG-006-03 | Política de cierres de caja (horarios, responsable de diferencias) | Decisión (CL-006-10) | Tesorería | Pendiente |
| CVG-006-04 | Conciliación de ingresos de 005 integrada al estado de cuenta | Trabajo de integración | Tesorería | Pendiente |
| CVG-006-05 | Flujo de anticipos por proveedor/cliente en UI de tesorería | Frontend de anticipos | Tesorería | Pendiente |

## 3. Implementado (006)

| Elemento | Estado |
|---|---|
| Maestros financieros (bancos, cuentas, cajas, métodos e instrumentos, monedas y tasas) | ✔ |
| Cajas: sesiones (apertura → movimientos → arqueo → pre-cierre → cierre/rechazo) con diferencias aprobadas | ✔ |
| Bancos: `BankTransaction` (fecha valor, referencia, comisión, snapshot de tasa) | ✔ |
| Ingresos/egresos: ejecución de pagos de 004 y cobros de 005 contra caja/banco, idempotente, marca POSTED | ✔ |
| Transferencias y depósitos entre cajas/cuentas | ✔ |
| Conciliación asistida con reglas (match score) + resolución manual auditada + aprobación | ✔ |
| IGTF por regla y evento (reglas versionadas; no confundir con IVA) | ✔ |
| Migración Alembic `0006_tesoreria` (head) | ✔ |
| API `/treasury/*` (27 endpoints) | ✔ |
| Frontend: cajas/arqueo, ingresos-egresos, transferencias, conciliación, IGTF, maestros | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 109/109 (85 previos + 24 de tesorería) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 72 archivos, 0 issues |
| Alembic | ✔ head `0006_tesoreria` (cadena 0001→0006; ALTER de 0004 requiere PostgreSQL, igual que CI) |
| OpenAPI | ✔ 27 endpoints `/treasury/*` (150 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/004/005 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 007/008/009) | Pendiente — depende de 001 certificada y de Specs 007/008/009 |
