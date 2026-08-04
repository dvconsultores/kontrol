# CRITERIOS DE ACEPTACIÓN — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/acceptance-criteria.md` |

## Criterios globales

| ID | Criterio | Verificación |
|---|---|---|
| AC-003-001 | Los movimientos son balanceados e inmutables; toda corrección mediante reverso vinculado (no edición ni borrado) | Test de movimientos + auditoría |
| AC-003-002 | El balance es reconstruible desde movimientos; `disponible = físico − reservas` | Test de reconstrucción |
| AC-003-003 | Lote y serial/IMEI cumplen la unicidad según política y conservan historial completo | Test de unicidad |
| AC-003-004 | FEFO y bloqueo de vencidos se aplican cuando el perfil lo exige | Test FEFO |
| AC-003-005 | Las reservas no superan el disponible; las salidas simultáneas no sobreadjudican | Test de concurrencia |
| AC-003-006 | Un ajuste o conteo nunca edita el saldo: genera movimientos con motivo, evidencia y aprobación | Test de ajuste/segregación |
| AC-003-007 | La valoración usa capas de costo según método versionado (promedio/FIFO); el costo de salida se calcula desde capas | Test de capas/valoración |
| AC-003-008 | 004/005 pueden invocar la API de integración v1 sin duplicar lógica de saldos | Contract test |
| AC-003-009 | Aislamiento multiempresa probado con pruebas negativas | Pytest negativo |
| AC-003-010 | Frontend respeta el estándar (pantallas completas, sin scroll horizontal, búsqueda asíncrona, `allowed_actions`) | E2E + axe |
| AC-003-011 | Cada requisito tiene identificador, fuente, dueño, criterio y prueba | Trazabilidad |
| AC-003-012 | No se hardcodean tipos de movimiento, métodos de costeo, FEFO ni estados | Revisión de código |

## Criterios por historia (US)

| Historia | Criterio |
|---|---|
| US-003-001 | La consulta de existencias filtra por producto/almacén/ubicación/lote/serial/estado y pagina |
| US-003-002 | El kardex muestra el historial de movimientos con saldos acumulados reconstruidos |
| US-003-003 | Un lote se registra con fabricación/vencimiento y se consume por FEFO cuando aplica |
| US-003-004 | Un serial/IMEI se registra una sola vez según política y conserva historial de movimientos |
| US-003-005 | Una orden aprobada reserva inventario: baja el disponible sin cambiar la existencia física |
| US-003-006 | Una transferencia recorre la máquina de estados y registra diferencias con destino definido |
| US-003-007 | Un conteo congela, registra líneas/diferencias y deriva en ajuste aprobado |
| US-003-008 | Un ajuste exige motivo, evidencia, costo y aprobación; genera movimiento, no edita saldo |
| US-003-009 | Las capas de costo valoran el inventario y calculan el costo de salida según el método del perfil |
| US-003-010 | El picking confirma ubicación/lote/serial y la salida mueve a tránsito o entregado-no-facturado |
| US-003-011 | Ningún movimiento se borra o edita; el reverso vinculado queda auditado |
| US-003-012 | Lotes/seriales transitan por estados explícitos con transiciones autorizadas |
| US-003-013 | La auditoría registra quién, cuándo y qué cambió en movimientos, lotes, seriales, reservas, conteos y ajustes |

## Criterios de la fase documental

| ID | Criterio | Estado |
|---|---|---|
| AC-003-DOC-001 | Spec 003 completa | ✔ |
| AC-003-DOC-002 | Ambigüedades resueltas o bloqueadas | ✔ (pendientes registrados) |
| AC-003-DOC-003 | Plan pasa la Constitución | ✔ |
| AC-003-DOC-004 | Modelo de datos documentado | ✔ |
