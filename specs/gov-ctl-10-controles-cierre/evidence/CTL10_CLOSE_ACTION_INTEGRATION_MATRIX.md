# GOV-CTL-10 · CTL10_CLOSE_ACTION_INTEGRATION_MATRIX

Inventario de acciones de «cierre» existentes en Gobierno al 2026-11-06 (CURRENT_CLOSE_ACTION_INVENTORY_COMPLETE = 1). INITIAL_INTEGRATED_CLOSE_ACTIONS = 2.

## Cierres de proceso integrados

| Proceso | Objeto | Acción | Estado origen | Estado destino | Servicio | Actor (permiso) | MFA | SoD | Auditoría | Integración |
|---|---|---|---|---|---|---|---|---|---|---|
| ORG-02 | `GovernmentStructure` (ejercicio) | Cerrar estructura del ejercicio (ORG02_CERRAR_ESTRUCTURA) | VIGENTE | CERRADA | `service_estructura.cerrar` | `gobierno_estructura:close` | sí (SENSITIVE) | no aplica: ORG-02 no está en el catálogo SoD (CTL-10 no lo añade) | GOV_STRUCTURE_CLOSED | SÍ (OD-CTL10-02). Guarda tras estado y comprobación de ejercicio terminado, fila bloqueada, antes de la mutación. `ejercicio` = año de la estructura; código de objeto derivado `EST-<ejercicio>` |
| TRE-02 | `GovernmentCashProgram` | Cerrar programa (TRE02_CERRAR_PROGRAMA) | VIGENTE (sin borrador) | CERRADO | `service_caja.cerrar` | `gobierno_caja:activate` | sí (SENSITIVE) | sí, `TRE02_CERRAR` vía `evaluar_antes_de_actuar` | GOV_CASH_PROGRAM_CLOSED | SÍ (OD-CTL10-02). Guarda después del estado, de borrador abierto y de SoD, antes de la mutación. `ejercicio` = `programa.ejercicio`; código = `programa.codigo` |

Orden común: autenticación → permiso → ámbito → estado → SoD (si existe) → CTL-10 → mutación → auditoría.

## Acciones de cierre no integradas

| Proceso | Objeto | Acción | Servicio | ¿Cierre de proceso? | Integración | Razón |
|---|---|---|---|---|---|---|
| TRE-01 | `GovernmentBankAccount` | Cerrar cuenta (TRE01_CERRAR), VIGENTE o INACTIVA → CERRADA, MFA, SoD sí | `service_cuentas.cerrar` | Sí | NO | OD-CTL10-02: TRE-01 no se integra |
| CTL-01 | `GovernmentSoDRule` | Cerrar regla SoD, VIGENTE → CERRADA, `gobierno_sod:activate` | `service_sod.cerrar` | No: es retiro de una regla | NO | La regla SoD no es un cierre de proceso (fuera de alcance) |
| CTL-06 | `GovernmentFinding` | Verificar y cerrar hallazgo (CTL06_VERIFICAR) → CERRADO | `service_hallazgos.verificar` | No: es el hecho que el control cuenta | NO | Verificar hallazgo no es cierre de proceso; integrarlo sería circular con HALLAZGOS_ABIERTOS |
| ORG-03 | competencia de cargo | Retirar competencia | `service_cargos.retirar_competencia` | No | NO | No es un cierre |
| CTL-10 | `GovernmentClosurePolicy` | Retirar política | `service_cierres.retirar` | No | NO | Es la propia política; con SoD CTL10_RETIRAR |

Las acciones del catálogo de CTL-10 son exactamente dos: ORG02_CERRAR_ESTRUCTURA y TRE02_CERRAR_PROGRAMA. TRE-08 sigue BLOCKED y no entra.

## Contrato de integración (qué cambia en los dos servicios)

Una sola línea de llamada a `service_cierres.evaluar_cierre(db, ctx, accion, objeto_tipo, objeto_id, objeto_codigo, ejercicio)` en cada servicio, sin modificar la lógica previa; la regresión de ORG-02 y TRE-02 prueba que los contratos existentes no cambian.
