# REQUIREMENT_TRACEABILITY — fuente → requisito → estado → evidencia

Matriz completa, una fila por requisito con fuente, sección, implementación, evidencia y verificación: `docs/roadmap/enterprise-application-completion/ENTERPRISE_REQUIREMENTS_REBASELINE.csv`.

**Verificación:**

- **M:** medida en el código del HEAD (`b726c1da`/`b3b53046`).
- **R:** evidencia registrada en el repositorio, con su ruta.
- **Sin ejecución nueva:** este puesto no tiene PostgreSQL ni dependencias (ENVIRONMENT_FAILURE, ver ATTEMPT_LOG).

## Cobertura por fuente

| Fuente principal | Requisitos | COMPLETE | PARTIAL | PRODUCT_DEFECT | NOT_BUILT | SPONSOR | Verificados en código (M) |
|---|---|---|---|---|---|---|---|
| V2 | 151 | 9 | 86 | 43 | 12 | 1 | 151 |
| DOCX-IMP | 42 | 39 | 1 | 1 | 0 | 1 | 42 |
| V1 | 25 | 2 | 9 | 12 | 2 | 0 | 25 |
| V3 | 16 | 0 | 13 | 3 | 0 | 0 | 16 |
| V4 | 15 | 1 | 9 | 5 | 0 | 0 | 15 |
| DOCX-PED | 9 | 0 | 6 | 3 | 0 | 0 | 9 |
| SPEC057 | 5 | 0 | 0 | 0 | 5 | 0 | 5 |
| P3 | 4 | 0 | 2 | 2 | 0 | 0 | 3 |
| V5 | 4 | 0 | 3 | 1 | 0 | 0 | 4 |
| V6 | 3 | 0 | 3 | 0 | 0 | 0 | 3 |
| SPEC035 | 3 | 1 | 0 | 0 | 1 | 1 | 3 |

## Requisito → estado

| ID | Módulo | Fuente | Requisito | Estado | UAT | Evidencia principal |
|---|---|---|---|---|---|---|
| INI-01 | Inicio | V2 §1 Inicio | Dashboard ejecutivo con indicadores configurables por rol | PARTIAL | NO | resources/backend/app/modules/reporting/service.py |
| INI-02 | Inicio | V4 WF01 | Dashboard: moneda y período explícitos en los indicadores | PRODUCT_DEFECT | NO | resources/backend/app/modules/reporting/service.py |
| INI-03 | Inicio | V2 §1 Inicio | Mis tareas: bandeja personal de tareas asignadas | COMPLETE | NO | resources/backend/app/modules/notifications/api.py |
| INI-04 | Inicio | V2 §1 Inicio | Mis aprobaciones: bandeja de aprobaciones pendientes del usuario | COMPLETE | NO | resources/frontend/src/modules/aprobaciones/bandeja/BandejaPage.tsx |
| INI-05 | Inicio | V2+V4 §1 / WF01 | Alertas accionables (no solo informativas) con origen y estado | PARTIAL | NO | resources/frontend/src/modules/notificaciones/alertas/AlertasPage.tsx |
| INI-06 | Inicio | V2+V1 §1 / V1§4 | Vencimientos: vista consolidada de vencimientos (documentos, permisos, crédito, obligaciones) | PARTIAL | NO | resources/backend/app/modules/reporting/service.py |
| ORG-01 | Maestros/Organización | V2+V3 §3 / V3§2 | Empresa: entidad legal, RIF, razón social, actividad, domicilio, moneda funcional, medio fiscal, perfiles y documentos | PARTIAL | NO | resources/backend/app/modules/organization/api.py |
| ORG-02 | Maestros/Organización | V2 §3 | Sucursal: unidad administrativa/comercial con responsables, centros de costo y horarios | PARTIAL | NO | resources/backend/app/modules/organization/api.py |
| ORG-03 | Maestros/Organización | V2 §3 | Establecimiento: lugar de emisión con series, correlativos, lotes de control y dirección fiscal | PARTIAL | NO | resources/backend/app/modules/organization/api.py |
| ORG-04 | Maestros/Organización | V2 §3 | Almacén: custodia, tipo, políticas, estados permitidos | PARTIAL | NO | resources/backend/app/modules/organization/warehouse_api.py |
| ORG-05 | Maestros/Organización | V2 §3 | Ubicación: pasillo, estante, zona, capacidad, restricciones y picking | PARTIAL | NO | resources/backend/app/modules/organization/warehouse_api.py |
| ORG-06 | Maestros/Organización | V2 §3 | Centro de costo: clasificación analítica versionada | NOT_BUILT | NO | resources/backend/app/modules/identity_access/models.py:133 |
| ORG-07 | Maestros/Organización | V2 §3 | Unidad de negocio: segmentación operativa y de permisos | NOT_BUILT | NO | resources/backend/app/modules/government/models.py:135 |
| ORG-08 | Maestros/Organización | V2 §3 | Período: apertura, cierre, bloqueo y reapertura aprobada | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| ORG-09 | Maestros/Organización | V4 WF06 | Maestro de empresa separa empresa, sucursal y establecimiento; medio fiscal y perfiles versionados | PARTIAL | NO | resources/backend/app/modules/organization/models.py |
| ORG-10 | Maestros/Organización | V2 §13 | Flujo de incorporación por empresa (empresa→estructura→monedas/períodos→rubros→plantillas→precios→fiscal→usuarios→carga→ | PARTIAL | NO | resources/backend/app/modules/setup/api.py |
| TER-01 | Maestros/Terceros | V2+V3 §4 / V3§3 | Tercero común con extensiones por rol; sin duplicidad de RIF, direcciones, contactos y cuentas | PARTIAL | NO | resources/backend/app/modules/master_data/party_service.py |
| TER-02 | Maestros/Terceros | V3 §12 RIF | RIF: validación de formato y duplicidad controlada por empresa/tenant y rol | PRODUCT_DEFECT | NO | resources/backend/app/modules/master_data/service.py |
| TER-03 | Maestros/Terceros | V2+V3 §4 | Cliente: lista de precios, vendedor, zona, condición, días y límite de crédito, bloqueo, direcciones de entrega, perfil  | PRODUCT_DEFECT | NO | resources/frontend/src/modules/maestros/terceros/TerceroExtensiones.tsx |
| TER-04 | Maestros/Terceros | V2+V3 §4 | Proveedor: categoría, comprador, condición de pago, perfil fiscal, retenciones, cuentas bancarias verificadas y aprobaci | PARTIAL | NO | resources/backend/app/modules/master_data/party_extensions.py |
| TER-05 | Maestros/Terceros | V4 WF08 | Aprobación bancaria/fiscal del proveedor antes de pagar | COMPLETE | NO | resources/backend/app/modules/master_data/party_extensions.py |
| TER-06 | Maestros/Terceros | V2 §4 | Vendedor: usuario, zonas, metas, comisiones y vigencia | PARTIAL | NO | resources/backend/app/modules/commercial/models.py |
| TER-07 | Maestros/Terceros | V2 §4 | Transportista: registro, seguros, vehículos, permisos y contratos | PARTIAL | NO | resources/backend/app/modules/master_data/models.py |
| TER-08 | Maestros/Terceros | V2 §4 | Conductor: identificación, licencia, vigencias, vehículos y restricciones | PARTIAL | NO | resources/backend/app/modules/master_data/models.py:152 |
| TER-09 | Maestros/Terceros | V2 §4 | Beneficiario: datos para pagos y validación bancaria | PARTIAL | NO | resources/backend/app/modules/master_data/party_children.py |
| TER-10 | Maestros/Terceros | V2+V3 §4 | Contactos del tercero con rol, teléfono, email, preferido y vigencia | COMPLETE | NO | resources/backend/app/modules/master_data/party_children.py |
| TER-11 | Maestros/Terceros | V2+V3 §4 | Direcciones fiscal/entrega con vigencia | PARTIAL | NO | resources/backend/app/modules/master_data/party_children.py |
| TER-12 | Maestros/Terceros | V4 WF07 | Maestro de cliente: crédito y perfil fiscal histórico; alertas de riesgo visibles | PARTIAL | NO | resources/frontend/src/modules/maestros/terceros/TerceroHistorial.tsx |
| PRD-01 | Maestros/Productos | V2+V3 §5 / V3§4 | Producto: ítem comercial PRODUCT con perfiles de inventario, trazabilidad, regulatorio, fabricante, origen | PARTIAL | NO | resources/backend/app/modules/master_data/api.py |
| PRD-02 | Maestros/Productos | V1+V3 §8 / V3§4 | Servicio: modalidad, unidad de facturación, duración, recurrencia, contrato y evidencia, perfil fiscal | PARTIAL | NO | resources/frontend/src/modules/maestros/servicios/ServiciosPage.tsx |
| PRD-03 | Maestros/Productos | V4 WF05 | Servicio no muestra lote/serial/almacén; concepto ISLR como referencia a regla | PRODUCT_DEFECT | NO | resources/frontend/src/modules/maestros/productos/ProductosPage.tsx |
| PRD-04 | Maestros/Productos | V2 §5 | Sector, rubro, categoría, familia, línea y tipo como taxonomía configurable por empresa | PARTIAL | NO | resources/backend/app/modules/master_data/api.py |
| PRD-05 | Maestros/Productos | V2+V3 §5 / V3§4 | Plantillas de producto/servicio: globales activables, copiables o propias (comportamientos lote, serial, vencimiento, va | PARTIAL | NO | resources/backend/app/modules/master_data/models.py:281 |
| PRD-06 | Maestros/Productos | V2+V3 §5 | Atributos configurables: tipo, unidad, obligatoriedad, opciones, validación, búsqueda, permisos, orden y aplicabilidad | PARTIAL | NO | resources/backend/app/modules/master_data/api.py |
| PRD-07 | Maestros/Productos | V2 §1 | Marcas | NOT_BUILT | NO | resources/backend/app/modules/master_data/models.py:321 |
| PRD-08 | Maestros/Productos | V2 §1 | Modelos | NOT_BUILT | NO | resources/backend/app/modules/master_data/models.py |
| PRD-09 | Maestros/Productos | V2+V3 §1 / V3§4 | Presentaciones con unidad, contenido, código de barras y flags compra/venta/almacenaje | PARTIAL | NO | resources/frontend/src/modules/maestros/presentaciones/PresentacionesPage.tsx |
| PRD-10 | Maestros/Productos | V2+V3 §1 / V3§4 | Unidades de medida y conversiones con factor, redondeo y vigencia | PRODUCT_DEFECT | NO | resources/frontend/src/modules/maestros/catalogos/CatalogosPage.tsx |
| PRD-11 | Maestros/Productos | V2 §5 | Perfiles de inventario, trazabilidad, fiscal y regulatorio versionados y reutilizables | PRODUCT_DEFECT | NO | resources/backend/app/modules/master_data/service.py |
| PRD-12 | Maestros/Productos | V3 §4 | Códigos de barras por producto/presentación y variantes de producto | PARTIAL | NO | resources/backend/app/modules/master_data/models.py:422 |
| PRD-13 | Maestros/Productos | V1 §8 | Crear un rubro ordinario sin migración; inventario/impuestos/lotes/seriales no en JSON libre | PARTIAL | NO | resources/backend/app/modules/master_data/api.py |
| PRD-14 | Maestros/Productos | V4 WF03 | Asistente de producto: campos por plantilla/perfil, guardar borrador y reanudar, sin condiciones por nombre de rubro | PARTIAL | NO | resources/frontend/src/modules/maestros/productos/ProductoNuevoPage.tsx |
| PRD-15 | Maestros/Productos | V4 WF04 | Detalle de producto con resumen inventario/fiscal/regulatorio e historial/auditoría | PRODUCT_DEFECT | NO | resources/frontend/src/modules/maestros/productos/ProductosPage.tsx |
| COM-01 | Maestros/Comercial | V2+V3 §1 / V3§6 | Listas de precios por moneda, alcance y vigencia; ítems por presentación y cantidad mínima | PRODUCT_DEFECT | NO | resources/backend/app/modules/commercial/service.py |
| COM-02 | Maestros/Comercial | V3 §6 | Reglas de precios con prioridad, condiciones, fórmula, piso/margen y aprobación requerida | PARTIAL | NO | resources/backend/app/modules/commercial/service.py |
| COM-03 | Maestros/Comercial | V2+V3 §1 / V3§6 | Condiciones de pago: cuotas, días, descuentos y estado | PARTIAL | NO | resources/backend/app/modules/commercial/api.py |
| COM-04 | Maestros/Comercial | V2 §1 | Maestro de crédito: políticas y límites de crédito configurables | PARTIAL | NO | resources/backend/app/modules/commercial/models.py |
| COM-05 | Maestros/Comercial | V2 §1 | Zonas comerciales | PARTIAL | NO | resources/backend/app/modules/commercial/models.py |
| COM-06 | Maestros/Comercial | V2 §1 | Rutas comerciales/de reparto | PARTIAL | NO | resources/backend/app/modules/commercial/models.py |
| COM-07 | Maestros/Comercial | V2 §1 | Comisiones de vendedores | NOT_BUILT | NO | resources/backend/app/modules/commercial/models.py |
| COM-08 | Maestros/Comercial | V2 §1 | Descuentos configurables con aprobación | PRODUCT_DEFECT | NO | resources/backend/app/modules/commercial/service.py |
| FIN-01 | Maestros/Financiero | V2+V3 §1 / V3§6 | Monedas ISO con decimales y estado | PARTIAL | NO | resources/backend/app/modules/treasury/models.py |
| FIN-02 | Maestros/Financiero | V3 §6 | Tasas de cambio por tipo y fuente, con valid_at, captured_at, hash de documento y estado | PARTIAL | NO | resources/backend/app/modules/treasury/rates.py |
| FIN-03 | Maestros/Financiero | V2 §1 | Bancos | PARTIAL | NO | resources/backend/app/modules/treasury/service.py |
| FIN-04 | Maestros/Financiero | V2 §1 | Cuentas bancarias de la empresa por moneda | PARTIAL | NO | resources/backend/app/modules/treasury/models.py |
| FIN-05 | Maestros/Financiero | V2 §1 | Cajas | PARTIAL | NO | resources/backend/app/modules/treasury/service.py |
| FIN-06 | Maestros/Financiero | V2+V3 §1 / V3§6 | Métodos e instrumentos de pago con monedas y comportamiento IGTF | PARTIAL | NO | resources/backend/app/modules/treasury/models.py |
| FMA-01 | Maestros/Fiscal | V2+V3 §1 / V3§10 | Perfiles fiscales por empresa/tercero/ítem con clasificaciones y vigencia | PRODUCT_DEFECT | NO | resources/backend/app/modules/master_data/service.py |
| FMA-02 | Maestros/Fiscal | V1+V3 §9 / V3§10 | IVA: gravado, exento, exonerado, no sujeto; alícuotas y vigencias versionadas con fuente legal | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FMA-03 | Maestros/Fiscal | V1 §9 | Retención IVA: agente, proveedor, documento, 75/100 u otra regla versionada | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FMA-04 | Maestros/Fiscal | V1+V4 §9 / WF18 | Conceptos y reglas ISLR versionadas por concepto, beneficiario, residencia, base, tarifa, mínimo, sustraendo y vigencia | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/models.py |
| FMA-05 | Maestros/Fiscal | V1 §9 | IGTF: hecho imponible, sujeto, moneda/cripto, medio, percepción y exenciones | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py |
| FMA-06 | Maestros/Fiscal | V2+V3 §1 / V3§7 | Series y correlativos por empresa/establecimiento/tipo con lock de versión y vigencia | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FMA-07 | Maestros/Fiscal | V2+V3 §1 / V3§7 | Lotes de números de control por imprenta, rango y estados AVAILABLE/RESERVED/USED/VOID/LOST/DAMAGED | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FMA-08 | Maestros/Fiscal | V2 §1 | Imprentas autorizadas | NOT_BUILT | NO | resources/backend/app/modules/fiscal/models.py |
| FMA-09 | Maestros/Fiscal | V2 §1 | Plantillas fiscales | NOT_BUILT | NO | specs/007-nucleo-fiscal/evidence/test-results.md |
| FMA-10 | Maestros/Fiscal | V3 §10 / §12 | Fuente legal (LegalSource) y TaxRuleVersion sin solape de vigencias, con aprobación | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| REGM-01 | Maestros/Regulatorio | V2+V3 §1 / V3§11 | Organismos (SENIAT, SUNAGRO, INSAI, SACS u otros) | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:91 |
| REGM-02 | Maestros/Regulatorio | V2+V3 §1 / V3§11 | Tipos de permiso por organismo con alcance y método de validación | PARTIAL | NO | resources/backend/app/modules/regulatory/models.py:44 |
| REGM-03 | Maestros/Regulatorio | V2+V3 §1 / V3§11 | Registros oficiales de empresa/tercero/sitio/vehículo/persona con archivo y estado | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:113 |
| REGM-04 | Maestros/Regulatorio | V2+V3 §1 / V3§11 | Perfiles regulatorios por rubro/producto/operación/origen/destino con documentos requeridos | PRODUCT_DEFECT | NO | resources/backend/app/modules/regulatory/service.py:235 |
| REGM-05 | Maestros/Regulatorio | V2 §1 | Vehículos | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:140 |
| REGM-06 | Maestros/Regulatorio | V2 §1 | Certificados | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:212 |
| CMP-01 | Compras | V2 §6.1 | Identificar necesidad y crear requisición (con centro de costo y fecha requerida) | PARTIAL | NO | resources/frontend/src/modules/compras/requisiciones/RequisicionNuevaPage.tsx |
| CMP-02 | Compras | V2 §6.2 | Aplicar presupuesto y aprobación a la requisición | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:438-472 |
| CMP-03 | Compras | V2 §6.3 | Solicitar cotizaciones a proveedores | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:478-487 |
| CMP-04 | Compras | V2+V3 §6.4 | Registrar ofertas con vigencia, moneda, condiciones y anexos | PARTIAL | NO | resources/frontend/src/modules/compras/cotizaciones/CotizacionesComprasPage.tsx:78 |
| CMP-05 | Compras | V2 §6.5 | Comparar precio, impuesto, disponibilidad, plazo y calidad | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:237-283 |
| CMP-06 | Compras | V2 §6.6 | Seleccionar proveedor y emitir orden de compra | COMPLETE | YES | resources/backend/app/modules/purchasing/service.py:286-363 |
| CMP-07 | Compras | V2+V3 §6.7 / §13 | Aprobar OC según monto, categoría y excepción; máquina DRAFT→SUBMITTED→APPROVED→PARTIALLY_RECEIVED→RECEIVED→CLOSED; CANC | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:131-141 |
| CMP-08 | Compras | V4 WF09 | OC con aprobación y totales por moneda; no sustituye recepción ni factura | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2493-2512 |
| CMP-09 | Compras | V2+V3 §6.8 / §13 | Recepción parcial o total con lotes, seriales, vencimientos y calidad; DRAFT→CONFIRMED→QUALITY_PENDING→ACCEPTED/PARTIALL | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:147-156 |
| CMP-10 | Compras | V2 §12 | Segregación recepción: almacén crea, calidad revisa, supervisor aprueba | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:1327-1370 |
| CMP-11 | Compras | V2 menú | Incidencias de recepción registradas con evidencia | PARTIAL | NO | resources/frontend/src/modules/compras/incidencias/IncidenciasPage.tsx |
| CMP-12 | Compras | V2+V3 §6.9 / §12 | Registrar factura de proveedor validando duplicidad (proveedor, número, control) y requisitos | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2036-2066 |
| CMP-13 | Compras | V3 §13 | Máquina de factura de proveedor DRAFT→VALIDATED→MATCHED/EXCEPTION→APPROVED→POSTED→PARTIALLY_PAID→PAID; REVERSED | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:158-170 |
| CMP-14 | Compras | V2+V4 §6.10 / WF10 | Conciliar orden, recepción y factura con diferencias explícitas y resolución auditada | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2112-2142 |
| CMP-15 | Compras | V2 §6.11 | Calcular retenciones IVA/ISLR en pago o abono en cuenta | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py:451-465 |
| CMP-16 | Compras | V2 §6.14 | Devolución al proveedor y nota del proveedor | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2185-2230 |
| CMP-17 | Compras | V6 §6 E2E | requisición → ofertas → orden → recepción parcial → factura → triple match → retenciones → pago | PARTIAL | NO | resources/frontend/e2e/cotizaciones-adjudicacion.spec.ts |
| IMP-01 | Importaciones | DOCX-IMP / Spec 018 IMP-01 Detectar necesidad de reposición o compra | IMP-01 Detectar necesidad de reposición o compra | COMPLETE | NO | resources/backend/app/modules/planning |
| IMP-02 | Importaciones | DOCX-IMP / Spec 018 IMP-02 Revisar inventario disponible | IMP-02 Revisar inventario disponible | COMPLETE | NO | resources/backend/app/modules/planning |
| IMP-03 | Importaciones | DOCX-IMP / Spec 018 IMP-02 Rotación y proyección de demanda | IMP-02 Rotación y proyección de demanda | COMPLETE | NO | resources/backend/app/modules/planning |
| IMP-04 | Importaciones | DOCX-IMP / Spec 018 IMP-03 Solicitud de compra | IMP-03 Solicitud de compra | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:404-462 |
| IMP-05 | Importaciones | DOCX-IMP / Spec 018 IMP-04 Aprobar según autoridad | IMP-04 Aprobar según autoridad | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:665-686 |
| IMP-06 | Importaciones | DOCX-IMP / Spec 018 IMP-05 Seleccionar y confirmar proveedor | IMP-05 Seleccionar y confirmar proveedor | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:237-363 |
| IMP-07 | Importaciones | DOCX-IMP / Spec 018 IMP-06 Negociar condiciones | IMP-06 Negociar condiciones | COMPLETE | NO | resources/backend/app/modules/imports/models.py:36-39 |
| IMP-08 | Importaciones | DOCX-IMP / Spec 018 IMP-07 Emitir orden de compra | IMP-07 Emitir orden de compra | COMPLETE | NO | resources/backend/app/modules/imports/api.py:252 |
| IMP-09 | Importaciones | DOCX-IMP / Spec 018 IMP-08 Recibir y validar documentación | IMP-08 Recibir y validar documentación | COMPLETE | NO | resources/backend/app/modules/imports/api.py:512-626 |
| IMP-10 | Importaciones | DOCX-IMP / Spec 018 IMP-09 Anticipo o pago | IMP-09 Anticipo o pago | COMPLETE | NO | resources/backend/app/modules/imports/service.py:565-600 |
| IMP-11 | Importaciones | DOCX-IMP / Spec 018 IMP-10 Seguimiento del embarque | IMP-10 Seguimiento del embarque | COMPLETE | NO | resources/backend/app/modules/imports/api.py:273 |
| IMP-12 | Importaciones | DOCX-IMP / Spec 018 IMP-11 Confirmar documentación y despacho | IMP-11 Confirmar documentación y despacho | COMPLETE | NO | resources/backend/app/modules/imports/api.py:493 |
| IMP-13 | Importaciones | DOCX-IMP / Spec 018 IMP-12 Faltantes y correcciones | IMP-12 Faltantes y correcciones | COMPLETE | NO | resources/backend/app/modules/imports/api.py:411 |
| IMP-14 | Importaciones | DOCX-IMP / Spec 018 Gastos de importación | Gastos de importación | COMPLETE | NO | resources/backend/app/modules/imports/costs.py |
| IMP-15 | Importaciones | DOCX-IMP / Spec 018 Distribución y preview de landed cost | Distribución y preview de landed cost | COMPLETE | NO | resources/backend/app/modules/imports/landed_cost.py |
| IMP-16 | Importaciones | DOCX-IMP / Spec 018 Aplicación de landed cost a la capa | Aplicación de landed cost a la capa | COMPLETE | NO | resources/backend/app/modules/imports/landed_cost.py |
| IMP-17 | Importaciones | DOCX-IMP / Spec 018 Moneda de la capa de costo | Moneda de la capa de costo | COMPLETE | NO | resources/backend/app/modules/imports/costs.py |
| IMP-18 | Importaciones | DOCX-IMP / Spec 018 §2 Confirmar arribo | §2 Confirmar arribo | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:739-766 |
| IMP-19 | Importaciones | DOCX-IMP / Spec 018 §2 Programar descarga | §2 Programar descarga | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:768-795 |
| IMP-20 | Importaciones | DOCX-IMP / Spec 018 §2 Recibir, comparar e inspeccionar | §2 Recibir, comparar e inspeccionar | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1019-1190 |
| IMP-21 | Importaciones | DOCX-IMP / Spec 018 §2 Registrar diferencias, evidencia y escalar | §2 Registrar diferencias, evidencia y escalar | PARTIAL | NO | resources/frontend/src/modules/compras/incidencias/IncidenciasPage.tsx |
| IMP-22 | Importaciones | DOCX-IMP / Spec 018 §2 Acta o registro de recepción | §2 Acta o registro de recepción | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1300-1325 |
| IMP-23 | Importaciones | DOCX-IMP / Spec 018 §2 Zona temporal de recepción o validación | §2 Zona temporal de recepción o validación | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:797-908 |
| IMP-24 | Importaciones | DOCX-IMP / Spec 018 §3 Conteo y comparación por SKU | §3 Conteo y comparación por SKU | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1760-1870 |
| IMP-25 | Importaciones | DOCX-IMP / Spec 018 §3 Estados recibido, disponible, pendiente, bloqueado | §3 Estados recibido, disponible, pendiente, bloqueado | COMPLETE | NO | resources/backend/app/modules/purchasing/process_condition.py |
| IMP-26 | Importaciones | DOCX-IMP / Spec 018 §3 Reporte formal de diferencias | §3 Reporte formal de diferencias | COMPLETE | NO | resources/backend/app/modules/imports/difference_report.py |
| IMP-27 | Importaciones | DOCX-IMP / Spec 018 §3 Tratamiento: ajuste, reclamo, investigación, cuarentena | §3 Tratamiento: ajuste, reclamo, investigación, cuarentena | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1543-1610 |
| IMP-28 | Importaciones | DOCX-IMP / Spec 018 §3 Confirmar y liberar a almacenamiento | §3 Confirmar y liberar a almacenamiento | PRODUCT_DEFECT | NO | resources/backend/app/modules/imports/service.py:1182-1235 |
| IMP-29 | Importaciones | DOCX-IMP / Spec 018 §4 Determinar zona de almacenamiento | §4 Determinar zona de almacenamiento | COMPLETE | NO | resources/backend/app/modules/storage |
| IMP-30 | Importaciones | DOCX-IMP / Spec 018 §4 Clasificación por tipo y familia | §4 Clasificación por tipo y familia | COMPLETE | NO | resources/backend/app/modules/storage |
| IMP-31 | Importaciones | DOCX-IMP / Spec 018 §4 Clasificación por tamaño, peso, rotación y volumen | §4 Clasificación por tamaño, peso, rotación y volumen | COMPLETE | NO | resources/backend/app/modules/storage |
| IMP-32 | Importaciones | DOCX-IMP / Spec 018 §4 Condiciones especiales | §4 Condiciones especiales | COMPLETE | NO | resources/backend/app/modules/storage |
| IMP-33 | Importaciones | DOCX-IMP / Spec 018 §4 Ubicación: zona, pasillo, rack, nivel, posición | §4 Ubicación: zona, pasillo, rack, nivel, posición | COMPLETE | NO | resources/backend/app/modules/organization |
| IMP-34 | Importaciones | DOCX-IMP / Spec 018 §4 Zonas A a E | §4 Zonas A a E | SPONSOR_VALIDATION_REQUIRED | NO | specs/018-importaciones/IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.md |
| IMP-35 | Importaciones | DOCX-IMP / Spec 018 §4 Etiquetar o identificar | §4 Etiquetar o identificar | COMPLETE | NO | resources/backend/app/modules/imports/storage_flow.py |
| IMP-36 | Importaciones | DOCX-IMP / Spec 018 §4 Trasladar, colocar y registrar ubicación | §4 Trasladar, colocar y registrar ubicación | COMPLETE | NO | resources/backend/app/modules/imports/storage_flow.py |
| IMP-37 | Importaciones | DOCX-IMP / Spec 018 §4 Validar ubicación física contra registrada | §4 Validar ubicación física contra registrada | COMPLETE | NO | resources/backend/app/modules/imports/physical_locations.py |
| IMP-38 | Importaciones | DOCX-IMP / Spec 018 §4 Reubicar por error | §4 Reubicar por error | COMPLETE | NO | resources/backend/app/modules/imports/physical_locations.py |
| IMP-39 | Importaciones | DOCX-IMP / Spec 018 §4 Liberar para preparación y despacho | §4 Liberar para preparación y despacho | COMPLETE | NO | resources/frontend/e2e/importaciones.spec.ts |
| IMP-40 | Importaciones | DOCX-IMP / Spec 018 Trazabilidad importación a ubicación final | Trazabilidad importación a ubicación final | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:910-1017 |
| IMP-41 | Importaciones | DOCX-IMP / Spec 018 Conteo independiente | Conteo independiente | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1724-1790 |
| IMP-42 | Importaciones | DOCX-IMP / Spec 018 Autorización de ajustes | Autorización de ajustes | COMPLETE | NO | resources/backend/app/modules/purchasing/service.py:1543-1610 |
| VEN-01 | Ventas | V2 §7.1 | Crear o seleccionar cliente en el flujo de venta | PARTIAL | NO | resources/frontend/src/modules/ventas/ordenes/OrdenesVentasPage.tsx:290 |
| VEN-02 | Ventas | V2 §7.2 | Emitir cotización sin reservar inventario | PARTIAL | NO | resources/backend/app/modules/sales/service.py:78 |
| VEN-03 | Ventas | V2 §7.3 | Recibir pedido y validar datos | PARTIAL | NO | resources/backend/app/modules/sales/service.py:538 |
| VEN-04 | Ventas | V2+V4 §7.4 / WF11 | Analizar crédito, margen, precios y excepciones; crédito, margen y reserva separados | PARTIAL | NO | resources/backend/app/modules/sales/service.py:742-756 |
| VEN-05 | Ventas | V2 menú | Ventas → Crédito: bandeja de decisiones de crédito sobre pedidos | PARTIAL | NO | resources/frontend/src/layout/Sidebar.tsx:281-293 |
| VEN-06 | Ventas | V2+V3 §7.5 / §13 | Aprobar orden y reservar inventario; DRAFT→SUBMITTED→CREDIT_PENDING→APPROVED→RESERVED→PREPARING→SHIPPED→CLOSED | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:99-131 |
| VEN-07 | Ventas | V2 §7.6 | Generar picking y preparación | PARTIAL | NO | resources/frontend/src/modules/ventas/preparacion/PreparacionPage.tsx:359,413 |
| VEN-08 | Ventas | V2+V4 §7.7 / WF12 | Validar documentos de traslado, lotes/seriales y permisos regulatorios antes de la salida | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2370-2447 |
| VEN-09 | Ventas | V2 §7.8 | Confirmar salida y mover inventario a tránsito o entregado-no-facturado | SPONSOR_VALIDATION_REQUIRED | NO | resources/backend/app/modules/sales/service.py:2449-2526 |
| VEN-10 | Ventas | V2+V3 §7.9 / §13 | Emitir factura; DRAFT→VALIDATED→APPROVED→EMITTED→DELIVERED→PARTIALLY_PAID→PAID | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2133-2190 |
| VEN-11 | Ventas | V4+V1 WF13 / §8 | Factura mixta producto+servicio con snapshot por línea, base fiscal en VES y tasa snapshot; servicio no mueve inventario | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2056-2131 |
| VEN-12 | Ventas | V2 §7.10 | Crear CxC a partir de la factura | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2642-2665 |
| VEN-13 | Ventas | V2 §7.11 | Registrar cobros, retenciones sufridas y anticipos | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2295-2390 |
| VEN-14 | Ventas | V2 §7.12 | Aplicar notas, devoluciones y diferencias cambiarias | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:3760-3910 |
| VEN-15 | Ventas | V2+V1 menú / §5 | Devolución de venta; la devolución física no sustituye la nota de crédito | PARTIAL | NO | resources/frontend/src/modules/ventas/devoluciones/DevolucionesVentasPage.tsx:256-277 |
| VEN-16 | Ventas | V6 §6 E2E | cotización → pedido → crédito → orden → reserva → picking → despacho → factura → cobro | PARTIAL | NO | resources/frontend/e2e/dispatch.spec.ts |
| PED-01 | Ventas | DOCX-PED Proceso 1 | Consultar disponibilidad, validar condiciones comerciales, registrar y emitir pedido; decidir si reserva al emitir (no c | PARTIAL | NO | resources/backend/app/modules/sales/service.py:682-756 |
| PED-02 | Ventas | DOCX-PED Proceso 2 | Cola de preparación con orden de proceso y detalle de productos, SKU, cantidades y ubicaciones | PARTIAL | NO | resources/backend/app/modules/sales/service.py:1033-1061 |
| PED-03 | Ventas | DOCX-PED Proceso 3 | Picking por ruta de ubicación (zona→pasillo→rack→ubicación) ordenado | PARTIAL | NO | resources/backend/app/modules/sales/service.py:1150-1173 |
| PED-04 | Ventas | DOCX-PED Proceso 4 | Marcar línea preparada; registrar diferencias con evidencia (no localizado, insuficiente, ubicación incorrecta, sistema≠ | PARTIAL | NO | resources/backend/app/modules/sales/service.py:1500-1577 |
| PED-05 | Ventas | DOCX-PED Proceso 5 | Consolidar pedido identificado y separado, trasladado a confirmación | PARTIAL | NO | resources/backend/app/modules/sales/service.py:1579-1640 |
| PED-06 | Ventas | DOCX-PED Proceso 6 | Segundo control físico independiente producto por producto; no conforme → incidencia → regresa a corrección → vuelve a c | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:1832-1929 |
| PED-07 | Ventas | DOCX-PED Proceso 7 | Confirmación autoriza facturar; almacén prepara, confirmación verifica, facturación factura (segregación) | PARTIAL | NO | resources/backend/app/modules/sales/service.py:2018-2042 |
| PED-08 | Ventas | DOCX-PED Proceso 8 | Factura sobre pedido confirmado, asociada al pedido | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2056-2190 |
| PED-09 | Ventas | DOCX-PED Proceso 9 | Despacho valida pedido preparado + confirmado + factura emitida; registra salida y entrega | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2320-2526 |
| INV-01 | Inventario | V2+V3 §1 / V3§5 | Existencias por producto, almacén, ubicación, lote, serial y estado; saldo proyectado y reconstruible | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/api.py |
| INV-02 | Inventario | V2 §1 | Kardex por producto/almacén con movimientos y costo | PARTIAL | NO | resources/backend/app/modules/inventory/api.py:262 |
| INV-03 | Inventario | V2+V5 §8 / V5§6 | Reserva reduce disponible sin cambiar físico; lock por producto/almacén/lote; sin sobre-reserva salvo política | COMPLETE | NO | resources/backend/app/modules/inventory/service.py:1333 |
| INV-04 | Inventario | V2 §8 | Picking: lista → confirmación de ubicación/lote/serial → preparación | PARTIAL | NO | resources/backend/app/modules/sales/service.py:1500 |
| INV-05 | Inventario | V2+V3 §8 / §13 | Transferencia solicitud→aprobación→reserva→salida→tránsito→recepción→diferencias (máquina de estados) | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/service.py:1593-1650 |
| INV-06 | Inventario | V2 §1 | Cargos y descargos de inventario por tipo de movimiento | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/service.py:533 |
| INV-07 | Inventario | V2 §8 | Ajuste con motivo, evidencia, costo, aprobación y movimiento; nunca edición directa de saldo | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/service.py:159,1725-1788 |
| INV-08 | Inventario | V2+V3 §8 / §5 | Conteo: plan → congelamiento/lectura → conteo → diferencias → aprobación → ajuste | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/service.py:91-100,1655-1722 |
| INV-09 | Inventario | V3 §5 | Capas de costo con cantidad restante, costo unitario, moneda, tasa fiscal y landed cost | PARTIAL | NO | resources/backend/app/modules/inventory/service.py:571-790 |
| INV-10 | Inventario | V3 §5 | Lotes con fabricación, vencimiento, proveedor y recepción; unicidad por política | PARTIAL | NO | resources/backend/app/modules/inventory/service.py:793-856 |
| INV-11 | Inventario | V3 §5 / §12 | Seriales/IMEI con unicidad e historial completo | PARTIAL | NO | resources/backend/app/modules/inventory/service.py:819-870 |
| INV-12 | Inventario | V2 §8 | Devolución con inspección y destino disponible, cuarentena, reparación, rechazo o desecho | PARTIAL | NO | resources/backend/app/modules/sales/service.py:3610 |
| INV-13 | Inventario | P3 §17 coherencia | Coherencia entre físico, disponible, reservado, recibido no confirmado, suministro abierto y valor | PARTIAL | NO | resources/backend/app/modules/inventory/service.py:235-316 |
| INV-14 | Inventario | SPEC035 DCR | El despacho consume capas de costo (landed incluido) y lo despachado sale de la valoración | COMPLETE | NO | specs/005-ventas-cuentas-por-cobrar/spec035-dispatch-cost-relief-delta.md |
| INV-15 | Inventario | SPEC035 DCR-10 | Despachos anteriores a DCR con costo aliviado (backfill autorizado) | SPONSOR_VALIDATION_REQUIRED | NO | specs/005-ventas-cuentas-por-cobrar/spec035-dispatch-cost-relief-delta.md (DCR-10) |
| INV-16 | Inventario | SPEC035 DCR-08 | Valoración de lo reingresado a RECHAZADO por devolución | NOT_BUILT | NO | resources/backend/app/modules/sales/service.py:3641-3646 |
| INV-17 | Inventario | V3 §12 | Movimiento balanceado, quantity≠0; sin eliminación física de movimientos | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/service.py:395-566 |
| INV-18 | Inventario | V2 §12 | Ajuste: almacén crea, costos/auditor revisa, aprobador aprueba | PARTIAL | NO | resources/backend/app/modules/inventory/service.py:1741-1770 |
| CXC-01 | CxC | V2+V3 §9 / V3§9 | Documentos por cobrar (OpenItem) con saldo = documentos + débitos − cobros − retenciones − créditos; no editable | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2800-2866 |
| CXC-02 | CxC | V2 §9 | Cobros parciales y múltiples | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2248-2390 |
| CXC-03 | CxC | V2 §9 | Anticipos sin aplicación inicial y aplicación posterior | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2404-2415 |
| CXC-04 | CxC | V2+V3 §9 / §12 | Aplicación con origen, destino, moneda, tasa, monto nominal y fiscal; sin exceder saldos; atómica | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py:2728-2797 |
| CXC-05 | CxC | V2 §1 | Aging por cliente y tramo | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2441-2466 |
| CXC-06 | CxC | V2+V1 §1 / V1§6 | Gestión de cobranza: promesas, seguimiento | NOT_BUILT | NO | resources/backend/app/modules/sales/api.py:1262-1446 |
| CXC-07 | CxC | P3 §18 estado de cuenta | Estado de cuenta del cliente | PARTIAL | NO | resources/backend/app/modules/sales/service.py:2935-2989 |
| CXC-08 | CxC | V1 §4 | Retenciones sufridas registradas y aplicadas al documento | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2315-2350 |
| CXC-09 | CxC | V2 §9 | Reversos sin eliminar: evento inverso y reapertura controlada | PARTIAL | NO | resources/backend/app/modules/sales/service.py:2991-3041 |
| CXC-10 | CxC | V2 §9 | Diferencias cambiarias al aplicar o valorar, sin alterar el IVA original | PARTIAL | NO | resources/backend/app/modules/treasury/service.py:954-1010 |
| CXP-01 | CxP | V2 §9 | Documentos por pagar con saldo = facturas + débitos − pagos − retenciones − créditos | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2233-2246 |
| CXP-02 | CxP | V2 §1 | Programación de pagos; evita pago duplicado | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2470-2481 |
| CXP-03 | CxP | V2 §1 | Pagos a proveedores | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2248-2292 |
| CXP-04 | CxP | V2 §1 | Anticipos a proveedores y aplicación posterior | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2404-2415 |
| CXP-05 | CxP | V2 §9 | Aplicaciones de pagos/créditos/retenciones a documentos | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2353-2401 |
| CXP-06 | CxP | V2 §1 | Aging de proveedores | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:2441-2467 |
| CXP-07 | CxP | V4+V2 WF15 / §12 | Retenciones y neto conciliados; aprobación del pago separada (CxP crea, tesorería revisa, aprobador aprueba) | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2277-2292 |
| TES-01 | Tesorería | V2 §10 | Caja: apertura, movimientos, arqueo, pre-cierre, cierre y diferencias | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py:394-534 |
| TES-02 | Tesorería | V2 §10 | Bancos y cuentas con moneda, fecha valor, referencia y comisiones | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py:536-551,1037-1051 |
| TES-03 | Tesorería | V2 §1 | Ingresos y egresos de tesorería | PARTIAL | NO | resources/backend/app/modules/treasury/service.py:584-666 |
| TES-04 | Tesorería | V2 §1 | Transferencias entre cuentas/cajas | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py:669-720 |
| TES-05 | Tesorería | V2 §1 | Depósitos de caja a banco | PARTIAL | NO | resources/backend/app/modules/treasury/service.py:669-720 |
| TES-06 | Tesorería | V2 §10 | Conciliación bancaria asistida con reglas y resolución manual auditada | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py:745-885 |
| TES-07 | Tesorería | V2+V4 §10 / WF14 | Varios medios y monedas por transacción; varias transacciones por documento; aplicación independiente | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:2248-2274 |
| TES-08 | Tesorería | V2 §10 | IGTF evaluado por regla y evento (no como IVA adicional) | PRODUCT_DEFECT | NO | resources/backend/app/modules/treasury/service.py:888-935 |
| TES-09 | Tesorería | V1 §4 | Comisiones bancarias y diferencias cambiarias en tesorería | PARTIAL | NO | resources/backend/app/modules/treasury/service.py:536-551,954-1035 |
| FIS-01 | Fiscal | V2+V5 §11 / V5§6 | Emisión fiscal consume correlativo y número de control en transacción atómica, sin duplicados bajo concurrencia | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-02 | Fiscal | V2+V3 §11 / §7 | Impresión y reimpresión registradas con copia, motivo y usuario | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-03 | Fiscal | V2+V3 §11 / §12 | Notas de crédito/débito referencian factura y se limitan al saldo ajustable (cantidades, base, IVA) | PRODUCT_DEFECT | NO | resources/backend/app/modules/sales/service.py |
| FIS-04 | Fiscal | V2+V3 §11 / §13 | Retenciones con estados calculada→aprobada→practicada→comprobante→declarada→pagada→conciliada; reversada | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py |
| FIS-05 | Fiscal | V4 WF17 | Comprobante de retención emitido no editable | PARTIAL | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-06 | Fiscal | V2 §11 | Libros de compra y venta generados desde documentos y eventos, con equivalentes en bolívares y tasas | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-07 | Fiscal | V3 §10 | Período fiscal con plazos, abierto/cerrado/reabierto con aprobaciones | PARTIAL | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-08 | Fiscal | V1 §9 | Contingencia fiscal: procedimiento aprobado, plantillas, sincronización posterior y auditoría | NOT_BUILT | NO | resources/backend/app/modules/regulatory/service.py |
| FIS-09 | Fiscal | V2+V3 §1 / §10 | Exportaciones y lotes de declaración (TaxReturnBatch) con archivos y totales | PARTIAL | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-10 | Fiscal | V4 WF16 | Inventario fiscal de números de control con estados inalterables | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py |
| FIS-11 | Fiscal | V1+V6 §9 / V6§8 | Versión fiscal identificada, eventos, integridad, sin declarar homologación sin acto formal | PARTIAL | NO | resources/backend/app/modules/homologation/service.py |
| FIS-12 | Fiscal | V1 §5 | Cero documentos fiscales emitidos editables o eliminables; corrección solo por documento de ajuste | PARTIAL | NO | resources/backend/app/modules/sales/service.py |
| FIS-13 | Fiscal | V1 §9 | Medio autorizado: forma libre, máquina fiscal o modalidad digital versionada | PARTIAL | NO | resources/backend/app/modules/fiscal/service.py |
| REG-01 | Regulación | V2 §1 | Guías (SICA, SACS, etc.) registradas y vinculadas al movimiento | PRODUCT_DEFECT | NO | resources/backend/app/modules/regulatory/service.py:273 |
| REG-02 | Regulación | V2+V3 §1 / §13 | Permisos DRAFT→REGISTERED→VERIFIED→APPROVED_FOR_USE→USED→EXPIRED; REJECTED/CANCELLED | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:48 |
| REG-03 | Regulación | V2+V1 §11 / V1§10 | Evaluación regulatoria por línea de despacho y consolidación de requisitos del movimiento | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:256 |
| REG-04 | Regulación | V1+V4 §10 / WF19 | Bloqueo del despacho si falta, vence o no coincide (producto, lote, cantidad, origen, destino, vehículo, conductor) | PRODUCT_DEFECT | NO | resources/backend/app/modules/regulatory/service.py:270 |
| REG-05 | Regulación | V2 §1 | Recepciones reguladas | NOT_BUILT | NO | resources/backend/app/modules/purchasing/service.py |
| REG-06 | Regulación | V2 §1 | Vencimientos de permisos, registros y certificados | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:278 |
| REG-07 | Regulación | V1 §10 | Documento con número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría | PRODUCT_DEFECT | NO | resources/backend/app/modules/regulatory/service.py:212 |
| REG-08 | Regulación | V1 §10 | Contingencias regulatorias solo mediante regla oficial versionada | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:315 |
| REG-09 | Regulación | V2 §12 | Permiso: logística crea, responsable regulatorio revisa, aprobador de salida aprueba | PARTIAL | NO | resources/backend/app/modules/regulatory/api.py:289 |
| RPT-01 | Reportes | V2+V1 §1 / §4 | Reportes ejecutivos, operativos, financieros, fiscales y regulatorios | PARTIAL | NO | resources/backend/app/modules/reporting/service.py:154 |
| RPT-02 | Reportes | V1 §4 | Reportes personalizados | NOT_BUILT | NO | resources/backend/app/modules/reporting/service.py:142 |
| RPT-03 | Reportes | V5 §7 | Reportes asíncronos para volumen con snapshot de parámetros y archivo descargable | PRODUCT_DEFECT | NO | resources/backend/app/modules/reporting/service.py:346 |
| RPT-04 | Reportes | V4 WF22 | Reporte de ventas con filtros, moneda, tasa y totales conciliables | PARTIAL | NO | resources/backend/app/modules/reporting/service.py:185 |
| RPT-05 | Reportes | V2 §1 | Reportes de auditoría | PARTIAL | NO | resources/backend/app/modules/reporting/service.py:369 |
| APR-01 | Aprobaciones | V2 §1 | Bandejas de aprobación | PARTIAL | NO | resources/backend/app/modules/approvals/service.py:923 |
| APR-02 | Aprobaciones | V2 §1 | Excepciones con aprobación | PARTIAL | NO | resources/backend/app/modules/approvals/integration.py:24 |
| APR-03 | Aprobaciones | V2 §1 | Delegaciones de autoridad con vigencia y tope | PARTIAL | NO | resources/backend/app/modules/approvals/models.py:188 |
| APR-04 | Aprobaciones | V1 §4 | Aprobaciones de crédito, descuentos, compras, pagos, ajustes y notas por regla y umbral | PARTIAL | NO | resources/backend/app/modules/commercial/service.py:458 |
| APR-05 | Aprobaciones | V1+V5 §5 / V5§4 | Un usuario no crea y aprueba su propia excepción crítica (SoD y maker-checker) | PRODUCT_DEFECT | NO | resources/backend/app/modules/approvals/service.py:600 |
| APR-06 | Aprobaciones | V3 §13 | Aprobación PENDING→IN_REVIEW→APPROVED/REJECTED/EXPIRED/CANCELLED con historial | PARTIAL | NO | resources/backend/app/modules/approvals/service.py:43 |
| APR-07 | Aprobaciones | V4 WF23 | Bandeja priorizada por riesgo, monto y vencimiento | PARTIAL | NO | resources/backend/app/modules/approvals/service.py:927 |
| SEG-01 | Seguridad | V2 §1 | Usuarios | PARTIAL | NO | resources/backend/app/modules/identity_access/api.py:479 |
| SEG-02 | Seguridad | V2+V4 §1 / WF20 | Roles y permisos con acciones más allá de CRUD | PARTIAL | NO | resources/backend/app/modules/identity_access/api.py:573 |
| SEG-03 | Seguridad | V2+V3 §1 / §2 | Alcances por empresa, sucursal, establecimiento, almacén y centro de costo con vigencia | PARTIAL | NO | resources/backend/app/core/company_context.py:54 |
| SEG-04 | Seguridad | V2+V5 §1 / §4 | Sesiones visibles y revocables; rotación | PARTIAL | NO | resources/backend/app/modules/identity_access/api.py:282 |
| SEG-05 | Seguridad | V2+V5 §1 / §4 | MFA configurable; recuperación segura, bloqueo | COMPLETE | NO | resources/backend/app/modules/identity_access/mfa_service.py |
| SEG-06 | Seguridad | V5 §5 | Aislamiento por tenant y empresa con pruebas negativas de acceso cruzado | PARTIAL | NO | resources/backend/app/modules/identity_access/service.py:643 |
| SEG-07 | Seguridad | V1+V5 §3 / §4 | Backend como autoridad: deny by default, permisos en ruta, API y dominio | COMPLETE | NO | resources/backend/app/core/dependencies.py |
| AUD-01 | Auditoría | V2+V4 §1 / WF21 | Timeline de eventos de extremo a extremo con Request ID y evidencia | COMPLETE | NO | resources/backend/app/shared/audit.py:38 |
| AUD-02 | Auditoría | V2+V3 §1 / §11 | Cambios de datos con antes/después | PARTIAL | NO | resources/backend/app/modules/regulatory/service.py:91 |
| AUD-03 | Auditoría | V2 §1 | Accesos | COMPLETE | NO | resources/backend/app/shared/audit_catalog_entries.py:333 |
| AUD-04 | Auditoría | V2 §1 | Impresiones | PARTIAL | NO | resources/backend/app/shared/audit_catalog_entries.py:137 |
| AUD-05 | Auditoría | V2 §1 | Exportaciones auditadas | PARTIAL | NO | resources/backend/app/modules/reporting/service.py:288 |
| AUD-06 | Auditoría | V2+V5 §1 / §4 | Incidentes: detección, triage, contención, evidencia, recuperación | NOT_BUILT | NO | resources/frontend/e2e/incidents.spec.ts |
| AUD-07 | Auditoría | V1 §5 | Eventos de auditoría no eliminables | COMPLETE | NO | resources/backend/alembic/versions/0061_spec001_audit_immutability.py |
| DOC-01 | Documentos | V5 §2 / §4 | Biblioteca documental con tipos | PARTIAL | NO | resources/backend/app/modules/documents/api.py:244 |
| DOC-02 | Documentos | P3 §25 versiones | Versiones de documentos | PRODUCT_DEFECT | NO | docs/roadmap/technical-debt-roadmap.md |
| DOC-03 | Documentos | V5 §4 | Antivirus, MIME real, hash, URLs firmadas y autorización por objeto | PARTIAL | NO | resources/backend/app/modules/documents/service.py:176 |
| DOC-04 | Documentos | V3 §14 | Archivos referenciados por ID desde las entidades (adjuntos/evidencia) | PARTIAL | NO | resources/backend/app/modules/documents/resources.py:38 |
| CFG-01 | Configuración | V2 §1 | Correo | NOT_BUILT | NO | resources/backend/app/modules/notifications/delivery.py:6 |
| CFG-02 | Configuración | V2 §1 | Impresión | PARTIAL | NO | resources/backend/app/modules/fiscal/api.py:94 |
| CFG-03 | Configuración | V2+V5 §1 / §2 | Integraciones (BCV, bancos, correo, interfaces oficiales) | NOT_BUILT | NO | resources/backend/app/modules/treasury/service.py:380 |
| CFG-04 | Configuración | V2 §1 | Almacenamiento | PARTIAL | NO | resources/backend/app/modules/documents/storage.py |
| CFG-05 | Configuración | V2 §1 | Notificaciones | PARTIAL | NO | resources/backend/app/modules/notifications/service.py |
| CFG-06 | Configuración | V2+V5 §1 / §12 | Monitoreo y observabilidad | PARTIAL | NO | resources/backend/app/modules/system/api.py:36 |
| CFG-07 | Configuración | V2+V5 §1 / §11 | Respaldos con RPO ≤15 min y restauración probada | PARTIAL | NO | specs/001-fundacion/spec001-backup-rpo-delta.md |
| CFG-08 | Configuración | V4 WF24 | Configuración técnica fuera de Maestros | PARTIAL | NO | resources/frontend/src/layout/Sidebar.tsx:390 |
| TRV-01 | Transversal | V1+V3 §3 / §14 | POST críticos con Idempotency-Key; reintentos no duplican facturas, pagos, movimientos, comprobantes | PRODUCT_DEFECT | NO | resources/backend/app/core/idempotency.py |
| TRV-02 | Transversal | V3 §14 | PATCH con control de versión/ETag | PARTIAL | NO | resources/backend/app/modules/organization/warehouse_api.py:394 |
| TRV-03 | Transversal | V3 §14 | Respuestas con allowed_actions calculadas en backend | PARTIAL | NO | resources/backend/app/modules/purchasing/service.py:379 |
| TRV-04 | Transversal | V3 §1 / §15 | Outbox/eventos de dominio para integraciones y tareas | PARTIAL | NO | resources/backend/app/modules/system/models.py:79 |
| TRV-05 | Transversal | V1 §3 | Decimal exacto para montos, tasas y cantidades | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py:458 |
| TRV-06 | Transversal | V2+V4 §2 / §2 | Estándar de pantalla: URL propia, breadcrumb, estados Loading/Empty/Forbidden/NotFound/Error, paginación | PARTIAL | NO | resources/frontend/src/components/PageHeader.tsx:17 |
| TRV-07 | Transversal | V1+V4 §11 / §28 | WCAG 2.2 AA y responsive (escritorio, tablet, móvil, zoom 150 %) | PARTIAL | NO | resources/frontend/e2e/accessibility.spec.ts |
| TRV-08 | Transversal | V1 §12 | Saldos, libros e inventario reconstruibles desde eventos y documentos | PRODUCT_DEFECT | NO | resources/backend/app/modules/inventory/api.py:254 |
| TRV-09 | Transversal | V1 §3 | Cada documento conserva snapshot de cliente, producto, impuestos, tasa y regla | PRODUCT_DEFECT | NO | resources/backend/app/modules/fiscal/service.py:354 |
| TRV-10 | Transversal | V6 §6 | 13 casos E2E mínimos del Volumen 6 §6 | PARTIAL | NO | resources/frontend/e2e/returns.spec.ts |
| TRV-11 | Transversal | P3 §27 hard-code | Cero hard-code institucional (clientes, zonas, tasas, bancos, roles por nombre, umbrales) | PRODUCT_DEFECT | NO | resources/backend/app/modules/purchasing/service.py:1536 |
| AF-01 | Activos fijos | SPEC057 §4–§9 | Maestros y políticas, alta, capitalización, componentización, ubicación, custodia, etiquetado y estados | NOT_BUILT | NO | docs/roadmap/enterprise-baseline/ENTERPRISE_WORK_MATRIX_CURRENT.md:23 |
| AF-02 | Activos fijos | SPEC057 §10–§13 | Libros de valoración, depreciación, mejoras, revaluación y deterioro | NOT_BUILT | NO | docs/roadmap/enterprise-baseline/ENTERPRISE_WORK_MATRIX_CURRENT.md:23 |
| AF-03 | Activos fijos | SPEC057 §14–§16 | Transferencias, inventario físico de activos y desincorporación | NOT_BUILT | NO | docs/roadmap/enterprise-baseline/ENTERPRISE_WORK_MATRIX_CURRENT.md:23 |
| AF-04 | Activos fijos | SPEC057 §17–§20 | Documentos, garantías, seguros, mantenimiento, integración financiera y cierre de períodos | NOT_BUILT | NO | docs/roadmap/enterprise-baseline/ENTERPRISE_WORK_MATRIX_CURRENT.md:23 |
| AF-05 | Activos fijos | SPEC057 §21–§24 | Seguridad, SoD, multiempresa, auditoría, reportes y dashboard | NOT_BUILT | NO | docs/roadmap/enterprise-baseline/ENTERPRISE_WORK_MATRIX_CURRENT.md:23 |

`REQUIREMENT_LEVEL_MATRIX_CREATED=YES` · `MENU_ONLY_GAPS_ELIMINATED=YES`. Además de las 92 opciones del menú, la matriz cubre:

- reglas no negociables;
- máquinas de estado;
- integridad;
- segregación;
- concurrencia;
- idempotencia;
- costeo;
- procesos de los DOCX;
- los 13 E2E mínimos;
- activos fijos.
