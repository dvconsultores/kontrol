# CRITERIOS DE ACEPTACIÓN — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/acceptance-criteria.md` |

## Criterios globales

| ID | Criterio | Verificación |
|---|---|---|
| AC-005-001 | La OV recorre DRAFT → … → CLOSED con crédito, margen y reserva separados | Test de máquina de estados |
| AC-005-002 | La cotización NO reserva inventario; la reserva ocurre al aprobar (vía 003) | Test de integración |
| AC-005-003 | El despacho se bloquea si falta documento/venció/no coincide; la salida usa 003 | Test de bloqueo/integración |
| AC-005-004 | La factura de venta es inmutable, con líneas mixtas, base fiscal VES y tasa snapshot | Test de estados/snapshot |
| AC-005-005 | El saldo de CxC se calcula desde documentos y aplicaciones; nunca se edita | Test de saldo |
| AC-005-006 | Ninguna aplicación excede el saldo de origen ni destino; operación atómica | Test de aplicación/concurrencia |
| AC-005-007 | Los cobros son idempotentes y multimoneda | Test de idempotencia |
| AC-005-008 | La retención sufrida se registra y aplica por regla versionada | Test de retención |
| AC-005-009 | 006 puede consumir cobros/aplicaciones para conciliación | Contract test |
| AC-005-010 | CxC reutiliza el motor de 004 (RECEIVABLE) sin duplicar lógica | Revisión de código |
| AC-005-011 | Aislamiento multiempresa probado con pruebas negativas | Pytest negativo |
| AC-005-012 | No se hardcodean límites de crédito ni reglas de aprobación | Revisión de código |

## Criterios por historia (US)

| Historia | Criterio |
|---|---|
| US-005-001 | La cotización se emite sin reservar inventario |
| US-005-002 | El pedido se recibe y se validan los datos del cliente |
| US-005-003 | El análisis de crédito separa crédito, margen y precios |
| US-005-004 | La OV aprobada reserva inventario (disponible baja, físico sin cambio) |
| US-005-005 | El picking se genera y prepara con ubicación/lote/serial |
| US-005-006 | La validación de traslado/permisos se registra antes de la salida |
| US-005-007 | La salida mueve inventario a tránsito o entregado-no-facturado con costo |
| US-005-008 | La factura de venta muestra base fiscal VES y tasa snapshot |
| US-005-009 | La CxC se crea y se registran cobros/anticipos/retenciones sufridas |
| US-005-010 | Notas y diferencias cambiarias se aplican al saldo sin excederlo |
| US-005-011 | El aging de CxC y la gestión de cobranza funcionan |
| US-005-012 | El ciclo se concilia y cierra con trazabilidad |

## Criterios de la fase documental

| ID | Criterio | Estado |
|---|---|---|
| AC-005-DOC-001 | Spec 005 completa | ✔ |
| AC-005-DOC-002 | Ambigüedades resueltas o bloqueadas | ✔ (pendientes registrados) |
| AC-005-DOC-003 | Plan pasa la Constitución | ✔ |
| AC-005-DOC-004 | Modelo de datos documentado | ✔ |
