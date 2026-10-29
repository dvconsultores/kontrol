# AFFECTED_PRODUCT_SURFACE_MATRIX — ciclo 07

> Superficies de producto **existentes** (línea Empresarial) que el ciclo 07 toca. El ciclo es `TECHNICAL_FOUNDATION`; estas filas son de
> regresión y UAT del producto existente, no de Gobierno (Gobierno sigue con UAT 0/122). Norma: `docs/governance/product-completeness-and-owner-uat-policy.md`.

## Resumen

- **Cambio visible:** una sola pantalla, «Inventario › Tipos de movimiento». Desaparece el selector «Global (todas las empresas)».
- **Cambio solo por API:** 24 pantallas más. Su backend ahora rechaza ids de **otra** empresa o de otro tenant en relaciones del cuerpo o de la ruta. La UI no puede producir esos ids, porque sus selectores solo ofrecen datos de la empresa activa. Por eso el flujo normal de la pantalla no cambia. Lo que cambia es que una petición manipulada recibe 404 en vez de crear un cruce.
- **Controles retirados:** 1, el selector global, que ya no era válido (§44). Controles muertos nuevos: 0.

## Pantalla con cambio visible

| Campo | Valor |
|---|---|
| SCREEN_ID | `inventario/tipos-movimiento` (`TiposMovimientoPage.tsx`) |
| PROCESS_ID | Configurar tipos de movimiento de inventario (Spec 003) |
| MENU_PATH | Menú principal › Inventario › Tipos de movimiento (`/inventario/tipos-movimiento`) |
| PURPOSE | Dar de alta y consultar los tipos que determinan el efecto de un movimiento sobre las existencias |
| ACTORS | Usuario con `inventario:create` en la empresa activa (alta); con `inventario:view` (consulta) |
| FIELDS | Código (obligatorio), Nombre (obligatorio), Dirección (select). **Retirado:** «Global (todas las empresas)» |
| ACTIONS | Crear; ver la tabla (Código, Nombre, Dirección, Estado) |
| STATES | carga, vacío, éxito («Tipo creado»), error (mensaje del backend); el formulario solo se monta con autoridad (`Autorizado`) |
| PERMISSIONS | backend: `inventario:create` en la empresa del contexto (403 `COMPANY_SCOPE_FORBIDDEN` si es en otra); frontend: proyección |
| ACTIVE_COMPANY / TENANT_CONTEXT | la fila se crea en la empresa activa; nunca con empresa nula desde una petición de empresa |
| BACKEND_AUTHORIZATION | `global_scope=true` → 403 `GLOBAL_SCOPE_FORBIDDEN` (OD-ISO-10); las filas globales existentes se conservan y se miden |
| ERRORS | 403 `GLOBAL_SCOPE_FORBIDDEN` solo alcanzable por API directa; la UI ya no puede pedirlo |
| DIRECT_URL | la URL directa sin autoridad muestra el mensaje de alcance (contrato del 02C) |
| RESPONSIVE / ACCESSIBILITY | axe de `main` a 1280 y 320 px y botón «Crear» visible a 320 px (E2E-TMOV-03) |
| E2E | `e2e/tipos-movimiento.spec.ts`: E2E-TMOV-01 (menú → alta → fila; el cuerpo no lleva `global_scope`), E2E-TMOV-02 (API directa con `global_scope: true` → 403 y sin fila), E2E-TMOV-03 (accesibilidad) |
| ¿Dónde está en el menú? | Inventario › Tipos de movimiento |
| ¿Qué puede hacer el usuario? | Entrar, ver los tipos de su empresa y crear uno nuevo con código, nombre y dirección. Ya no puede crear un tipo «global» que valga en todas las empresas de todos los tenants |
| ¿Está listo para probar el cambio? | Sí, cuando pase la E2E del ciclo (ver la tarjeta) |
| Control retirado (§44) | Era inválido: con OD-ISO-10 toda petición con «Sí» terminaría en 403. Ninguna función queda sin cubrir. El alta de la empresa sigue igual, y la escritura global legítima (de instalación) no existe en el producto |
| Observación LOW | La tabla no distingue las filas globales heredadas de las propias. Es preexistente, no lo introduce el ciclo, y queda como deuda `TIPOS-MOVIMIENTO-SIN-INDICADOR-GLOBAL` (LOW) |
| SCREEN_FORM_COMPLETENESS | PASS una vez verde E2E-TMOV-01..03 |

**Tarjeta de prueba (producto existente).**
- **Entrar en:** Inventario › Tipos de movimiento.
- **Rol:** administrador o usuario con capacidad de inventario en la empresa activa.
- **Pasos:**
  1. Comprueba que el formulario «Nuevo tipo» tiene Código, Nombre y Dirección, y ningún campo «Global».
  2. Crea `PRUEBA_UAT_1`, «Prueba UAT», dirección Entrada.
- **Resultado esperado:** aviso «Tipo creado» y fila nueva en la tabla.
- **Prueba negativa:** no se puede hacer desde la pantalla, porque el control no existe; la automática la cubre por API (E2E-TMOV-02).
- **Limpieza:** desactivar el tipo si la pantalla lo permite. Si no, dejarlo, porque es inocuo.

## Pantallas con cambio solo por API (ids ajenos)

Las tres preguntas valen para todas igual:
- **¿Dónde está en el menú?** Ver la columna «Menú».
- **¿Qué puede hacer el usuario?** Lo mismo que antes: el flujo normal no cambia.
- **¿Está listo para probar el cambio?** El cambio no es observable desde la pantalla. Se prueba con las pruebas hostiles de backend y, donde existe, con la E2E canónica del flujo, que verifica que la pantalla no ha regresado.

| Menú | Pantalla | Qué cambia en el backend | GAP | E2E canónica del flujo |
|---|---|---|---|---|
| Inventario › Valorización | `ValorizacionPage` | perfil de costeo con producto de la empresa; `global_scope=true` → 403 (la pantalla ya envía `false`) | G-INV-03 | — (solo pruebas de backend) |
| Inventario › Transferencias | `TransferenciasPage` | producto, lote y serie de la línea de la empresa | G-INV-01 | recorrido responsive |
| Inventario › Conteos | `ConteosPage` | producto, lote y ubicación de la línea de conteo | G-INV-02 | — |
| Inventario › Confirmación | `ConfirmacionPage` | la incidencia pertenece a la recepción | G-COM-05 | `inventory-confirmation.spec.ts` |
| Inventario › Existencias | `ExistenciasPage` | saldo de cuenta solo de la empresa | G-TES-03 | `read-permission`, `strict-api-input`, `accessibility` |
| Maestros › Productos / Servicios / Catálogos | `ProductoNuevoPage`, `ProductosPage`, `ServiciosPage`, `CatalogosPage` | categoría, unidad base, perfiles, unidad de facturación y padre de taxonomía de la empresa o globales | G-MD-01/02 | `uom-conversion`, `isolation`, `order-confirmation`, `billing` |
| Maestros › Presentaciones | `PresentacionesPage` | unidad y unidad de factor de la empresa | G-MD-03 | `uom-conversion.spec.ts` |
| Documentos › Tipos documentales | `TiposDocumentalesPage` | categoría de la empresa | G-DOC-01 | `documents`, `documents-a11y`, `audit-catalog` |
| Compras › Requisiciones / Cotizaciones / Órdenes / Facturas | `RequisicionesPage`, `CotizacionesComprasPage`, `OrdenesComprasPage`, `FacturasProveedorPage` | líneas con producto, unidad, orden y recepción de la empresa | G-COM-01..04 | recorrido responsive; `accessibility` |
| Ventas › Facturación / Confirmación de pedido / Devoluciones | `FacturasVentasPage`, `ConfirmacionPedidoPage`, `DevolucionesVentasPage` | artículo, líneas extra, lote y serie de la empresa | G-VEN-01..03 | `billing`, `order-confirmation`, `returns` |
| Ventas › Estado de cuenta · Tesorería › Reembolsos | `EstadoDeCuentaPage`, `ReembolsosPage` | cliente de la empresa en saldo, estado de cuenta y créditos | G-VEN-04 | `receivables`, `treasury` |
| Tesorería › Cajas / Conciliación | `CajasPage`, `ConciliacionPage` | instrumento, pago y transacción bancaria de la empresa; idempotencia por empresa | G-TES-01/02 | `treasury.spec.ts` |
| Seguridad › Roles | `RolesPage` | roles filtrados por tenant; un rol nuevo lleva el tenant | G-ROL-01 | `delegation-ceiling`, `roles-alta` |
| Seguridad › Sesiones | `SesionesPage` | revocar una sesión ajena → 404 (antes 403) | G-SES-01 | — (backend ISO-SES) |
| Notificaciones › Reglas | `ReglasPage` | rol de escalado del tenant y la empresa | G-NOT-01 | — (backend ISO-NOT-01) |
| Organización › Ubicaciones | estructura de almacén | nodo de otra empresa → 404 `<NIVEL>_NOT_FOUND` (antes 422) | G-WH-01 | `warehouse-structure`, `warehouse-a11y` |
| Reportes › Exportaciones | `ExportacionesPage` | escritura exclusiva de la exportación | G-STO-01 | `report-download.spec.ts` |

**AFFECTED_PRODUCT_SURFACES = 25 · AFFECTED_SCREENS_REVIEWED = 25 · AFFECTED_FORMS_REVIEWED = 1 (el único formulario cambiado) · DEAD_CONTROLS = 0.**
`AFFECTED_SCREEN_FORM_COMPLETENESS_GATE` = PASS cuando la E2E canónica (que incluye `tipos-movimiento.spec.ts`) quede verde.
