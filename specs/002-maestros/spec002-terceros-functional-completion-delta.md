# Delta 002 · TERCEROS-FUNCTIONAL-COMPLETION

Spec dueña: 002 Maestros. Consumidoras de la regla de pago y de bloqueo: 004 y 005. Árbol de partida `be05f92`.

**Estado: `FUNCTIONAL_PRODUCT_COMPLETE_LOCAL / EXTERNAL_CERTIFICATION_GATES_PENDING`.** Toda la vertical está construida y probada en local. La interfaz y el backend **nunca se han ejecutado juntos en un navegador**: este equipo no tiene PostgreSQL ni navegadores de Playwright.

## Qué puede hacer el usuario

Menú **Maestros → Terceros**.

- **Listado:** búsqueda, filtro de estado y paginación en servidor.
- **Alta** en pantalla completa, con RIF y varios roles. Un duplicado explica el motivo y enlaza al tercero existente.
- **Detalle:** identificación editable, roles, activar, desactivar, eliminar e historial.
- **Direcciones, contactos y cuentas:** agregar, editar, desactivar y verificar cuenta. Nada se borra.
- **Cliente, Proveedor, Transportista y Conductor:** su sección aparece según el rol.
- **Aprobación del proveedor:** aprobar, rechazar con motivo y reenviar.

## Reglas de negocio nuevas

| Regla | Efecto | Error |
|---|---|---|
| Proveedor no aprobado | Sin pagos ni anticipos `OUT`, ni transición del pago a APPROVED o POSTED. Cancelar o rechazar un pago, cobrar (`IN`) y programar siguen permitidos | 409 `SUPPLIER_NOT_APPROVED` |
| Aprobar | Exige tercero activo, RIF y una cuenta vigente verificada | 409 `SUPPLIER_APPROVAL_PRECONDITION` con `details.missing` |
| Tocar una cuenta bancaria | Le quita la verificación, y un proveedor aprobado vuelve a pendiente (control de fraude, CL-002-08) | Auditado |
| Cliente bloqueado | Sin cotizaciones, órdenes ni facturas nuevas; notas y cobros siguen. Bloquear exige motivo | 409 `CUSTOMER_BLOCKED` |
| Documentos activos | Impiden desactivar y se listan en el detalle | 409 `PARTY_HAS_ACTIVE_DOCUMENTS` |
| Edición concurrente | `If-Match` obligatorio; también sube la versión de la fila desplazada al cambiar la marca fiscal o preferida | 428 y 409 `VERSION_CONFLICT` |

**Consecuencia al desplegar:** todo proveedor existente nace `PENDING_APPROVAL`, porque esa es la regla ya aprobada para este ciclo. Sus pagos quedarán bloqueados hasta aprobarlo. Deuda `TERCEROS-PROVEEDORES-HISTORICOS-SIN-APROBAR`.

## Evidencia

| Gate | Resultado |
|---|---|
| Pruebas funcionales de backend | 35 de 35: `test_terceros_funcional` 8, `_datos` 11, `_extensiones` 9, `_puertas` 4, `_auditoria` 3 |
| Backend de módulo y afectados, SQLite | 2045 recogidas, 1 fallo, 1137 saltadas. El fallo era real (`expiry` sin zona), se corrigió en TF-N y su guarda pasa. **No se repitió el conjunto completo tras TF-N**: se repitieron 132 de terceros, maestros, catálogo y guarda, todas verdes |
| Vitest completo | 1738 de 1738 en 150 ficheros, RC 0. La primera corrida dio 3 fallos reales de gates, corregidos en TF-N |
| Ruff · mypy | Limpio · 154 errores, sin aumento sobre la línea base |
| TSC con E2E · ESLint · build | RC 0 |
| OpenAPI | 709 → 738 operaciones, 29 nuevas; instantáneas regeneradas |
| Migración | `0078_terceros_version`, una sola cabeza. **Sin ejecutar sobre PostgreSQL** |
| E2E `e2e/terceros-mantenimiento.spec.ts` | Preparada y compilada. **Sin ejecutar** |
| `test_mc_purchasing_ap_ab` | Fixture ajustado. **Sin ejecutar:** solo corre con PostgreSQL |
| `qa/functional-e2e-*` | Guiones ajustados a la puerta de pago. **Sin ejecutar** |

Mutaciones y regresión global quedan en `FINAL_ENTERPRISE_CERTIFICATION`, por la directiva product-first.

## Defectos que la auditoría evitó que entraran

- Número de cuenta completo devuelto a quien solo tenía `compras:approve`.
- `page=0` en el historial, contra `ge=1` del backend, oculto por un mock con el mismo error.
- `status === "ACTIVO"`, que habría mostrado a todos como inactivos.
- Puerta de pago sobre todos los destinos, que habría impedido cancelar un pago.
- Consulta del historial lanzada sin permiso.

## Tarjeta de prueba de la dueña (lista para cuando se ejecute la E2E)

1. En Maestros → Terceros, pulse «Nuevo tercero» y cree un proveedor con RIF. Debe llevarle al detalle sin pedir confirmación.
2. Intente registrar un pago en Compras → Cuentas por pagar. Debe rechazarlo: «El proveedor no está aprobado para recibir pagos.»
3. Pulse «Aprobar proveedor». Debe decir que falta una cuenta bancaria verificada.
4. Agregue una cuenta, escriba la evidencia, verifíquela y apruebe. El pago ya debe registrarse.
5. Edite la cuenta. El proveedor debe volver a «Pendiente» y el historial debe mostrarlo.

## No absorbido

`PRODUCTO-NUEVO-*`, `CATALOGO-CODIGO-SIN-UNICIDAD`, `ASYNC-COMBOBOX-REABRIR-TRAS-ESCAPE`, `COMPRAS-DEVOLUCION-LINEA-SIN-VALIDAR-PRODUCTO`, `TRASLADOS-REQUIRES-LOT-NO-EXIGIDO`, `ALMACENES-LISTADO-PRIMERA-PAGINA`.

Registro de intentos y contratos: `evidence/terceros-functional-completion/`.
