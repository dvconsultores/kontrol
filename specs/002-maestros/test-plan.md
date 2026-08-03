# PLAN DE PRUEBAS — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Responsable | QA Lead |
| Ruta | `specs/002-maestros/test-plan.md` |

## 1. Estrategia

Hereda la infraestructura de pruebas de 001 (Pytest, Vitest/RTL, Playwright, axe). Niveles: unitarias, componentes, contrato, integración, E2E, accesibilidad.

## 2. Unitarias (backend)

| Área | Cobertura |
|---|---|
| Validación RIF / cédula / cuentas | formato, ceros iniciales |
| Duplicidad de tercero | unique por empresa/rol; excepciones |
| Taxonomía | árbol, ámbito, estado, `applies_to` |
| Atributos gobernados | tipos, opciones, buscables, permisos |
| Conversión de unidades | factor, redondeo, vigencia, factor ≤ 0 rechazado |
| Perfiles versionados | vigencia, estado, aprobación |
| Especialización producto/servicio | el servicio no usa lote/serial/almacén |
| Estados | máquinas de estado de maestros |

## 3. Componentes (frontend)

AsyncCombobox (debounce, cancelación, loading, empty, error), formularios de tercero/producto (validación, foco al primer error), DataTable de maestros (sin scroll horizontal, paginación >10, `allowed_actions`), asistente de producto (pasos, borrador).

## 4. Integración

- API/PostgreSQL para terceros, catálogo, perfiles.
- Aislamiento multiempresa (pruebas negativas: empresa A no ve maestros de empresa B).
- Duplicidad de RIF y barcode bajo concurrencia.
- Migraciones `0002` upgrade/downgrade.
- Idempotencia en POST críticos.

## 5. E2E

1. Alta de cliente con RIF; reutilización de RIF en proveedor.
2. Asistente de producto completo (pasos + guardar borrador).
3. Alta de servicio (sin lote/serial/almacén).
4. Búsqueda asíncrona de cliente/producto.
5. Aprobación de proveedor y bloqueo de pago antes de aprobar.
6. Desactivar/activar/eliminar con confirmación.
7. Acceso prohibido a maestro de otra empresa.
8. Concurrencia de edición (409).
9. Responsive y accesibilidad (axe).

## 6. Estado

| Elemento | Estado |
|---|---|
| Plan de pruebas | ✔ |
| Ejecución | Pendiente (implementación, requiere 001 certificada) |
