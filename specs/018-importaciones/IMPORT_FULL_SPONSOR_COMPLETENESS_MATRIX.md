# Importaciones: matriz completa contra el sponsor

**IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.** Comparada el 2026-11-09 con `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx` (§1 a §4, zonas y controles críticos, leído completo), el Roadmap B-031 y B-032, y el código en `bcf4d1f`.

**Resultado: `SPEC018_END_TO_END_FLOW_COMPLETE = 0`.** El flujo central funciona en Chrome sobre PostgreSQL, pero el documento pide más de lo construido.

`BROWSER_VERIFIED = POSTGRESQL_BROWSER_VERIFIED` significa que la E2E canónica lo recorre sobre PostgreSQL migrado. `EXISTS_NOT_REVALIDATED` significa que hay código y pruebas propias, pero no se revalidó sobre PostgreSQL en este bloque: **no es prueba de que funcione**.

## Resumen

| Estado | Requisitos |
|---|---|
| COMPLETE | 17 |
| PARTIAL | 8 |
| EXISTS_NOT_REVALIDATED | 7 |
| NOT_BUILT | 9 |
| SPONSOR_VALIDATION_REQUIRED | 1 |
| **Total** | **42** |

La proporción no mide el avance real: las filas no pesan igual. Las brechas de mayor peso son landed cost, clasificación con reubicación y el reporte formal.

## Orden propuesto de las brechas

1. **Ciclo 4B:** distribución, preview y aplicación de landed cost. Decisiones ya resueltas.
2. **Reporte formal de diferencias:** los datos existen; falta el documento.
3. **Reubicar por error** y validación física de la ubicación.
4. **Clasificación, zona y etiquetado:** exige atributos nuevos en el maestro y que el sponsor valide las zonas A a E.
5. **Rotación y proyección** (IMP-02): pertenece a la Spec 015, no a la 018.

## Matriz

| SPONSOR_REQUIREMENT | SOURCE | BUSINESS_PROCESS | SCREEN | BACKEND | DATABASE | API | ROLE_PERMISSION | INTEGRATION | FUNCTIONAL_TEST | BROWSER_VERIFIED | OWNER_UAT_READY | STATUS | GAP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IMP-01 Detectar necesidad de reposición o compra | DOCX §1 | Importación | /inventario/existencias, /compras/requisiciones | Parcial | SI | /inventory, /purchasing | compras, inventario | Inventario | Sin prueba de este paso | NO | NO | PARTIAL | Sin detección: la necesidad la identifica una persona |
| IMP-02 Revisar inventario disponible | DOCX §1 | Importación | /inventario/existencias | SI | SI | /inventory | inventario | Inventario | Fuera de la E2E | NO | NO | PARTIAL | Existencias se consultan; rotación y proyección abajo |
| IMP-02 Rotación y proyección de demanda | DOCX §1; B-031 | Importación | Ninguna | NO | NO | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | No existe cálculo ni pantalla. Dueño en backlog: Spec 015 |
| IMP-03 Solicitud de compra | DOCX §1 | Importación | /compras/requisiciones | SI | SI | /purchasing | compras | Compras | Otras suites; fuera de la E2E de importación | NO | NO | EXISTS_NOT_REVALIDATED | Existe; no se revalidó en este bloque |
| IMP-04 Aprobar según autoridad | DOCX §1 | Importación | Aprobaciones | SI | SI | /approvals | aprobaciones | Spec 045 | Otras suites | NO | NO | EXISTS_NOT_REVALIDATED | La E2E parte de una orden aprobada |
| IMP-05 Seleccionar y confirmar proveedor | DOCX §1 | Importación | Maestros → Terceros | SI | SI | /parties | maestros | Terceros | E2E crea proveedor por API | NO | NO | EXISTS_NOT_REVALIDATED | Comparación de ofertas sin construir |
| IMP-06 Negociar condiciones | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones | compras | — | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | Precio y cantidad viven en la orden |
| IMP-07 Emitir orden de compra | DOCX §1 | Importación | /compras/ordenes; /compras/importaciones/{id} | SI | SI | /importaciones/{id}/order | compras | Compras | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | La orden se emite en Compras y se vincula |
| IMP-08 Recibir y validar documentación | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/documents | compras | Spec 046 | E2E con analizador + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| IMP-09 Anticipo o pago | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/payments | compras | CxP | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | Corregido created_by en este bloque |
| IMP-10 Seguimiento del embarque | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/tracking | compras | — | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| IMP-11 Confirmar documentación y despacho | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/confirm-dispatch | compras | — | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| IMP-12 Faltantes y correcciones | DOCX §1 | Importación | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/corrections | compras | Documentos | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| Gastos de importación | B-032; orden de la dueña | Costos | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/expenses, /costs | compras | Tesorería, Documentos | E2E + pytest PG | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | Documento de soporte y factura vinculada: cubiertos por API, no en navegador |
| Distribución y preview de landed cost | B-032; decisiones de la dueña | Costos | Ninguna | NO | NO | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | Ciclo 4B |
| Aplicación de landed cost a la capa | B-032; decisiones de la dueña | Costos | Ninguna | NO | Columna sin uso | Ninguna | — | Motor de costos | Ninguna | NO | NO | NOT_BUILT | Ciclo 4B. `_consume_cost` y `valuation` no leen `landed_cost` |
| Moneda de la capa de costo | Documento Maestro | Costos | /compras/importaciones/{id} | SI | SI | /importaciones/{id}/costs | compras | Inventario | E2E: capa USD | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §2 Confirmar arribo | DOCX §2 | Recepción | /compras/importaciones/{id} | SI | SI | /purchasing/receipts/{id}/arrival | compras | Spec 019 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §2 Programar descarga | DOCX §2 | Recepción | /compras/recepciones | SI | SI | /purchasing/receipts | compras | Spec 019 | Fuera de la E2E | NO | NO | PARTIAL | El formulario del expediente no lo pide; está en Recepciones |
| §2 Recibir, comparar e inspeccionar | DOCX §2 | Recepción | /compras/recepciones | SI | SI | /purchasing/receipts | compras | Spec 019 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §2 Registrar diferencias, evidencia y escalar | DOCX §2 | Recepción | /compras/incidencias | SI | SI | /purchasing/incidents | compras | Spec 020 | E2E: registrar, escalar y resolver | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | Adjuntar evidencia no se recorre en la E2E |
| §2 Acta o registro de recepción | DOCX §2 | Recepción | /compras/recepciones | SI | SI | /purchasing/receipts | compras | Spec 019 | Otras suites; no afirmada en esta E2E | NO | NO | EXISTS_NOT_REVALIDATED |  |
| §2 Zona temporal de recepción o validación | DOCX §2 | Recepción | Parcial | Parcial | SI | /inventory | inventario | Spec 022 | Fuera de la E2E | NO | NO | PARTIAL | Hay estado de inventario; no se designa una zona física |
| §3 Conteo y comparación por SKU | DOCX §3 | Confirmación | /inventario/confirmacion | SI | SI | /purchasing/receipts/{id}/conciliacion | inventario | Spec 021 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE | La columna Producto muestra un id recortado (IMP-CONFIRM-UUID-01) |
| §3 Estados recibido, disponible, pendiente, bloqueado | DOCX §3 | Confirmación | /inventario/existencias | SI | SI | /inventory | inventario | Spec 021 | Otras suites | NO | NO | EXISTS_NOT_REVALIDATED |  |
| §3 Reporte formal de diferencias | DOCX §3 | Confirmación | Ninguna | NO | Datos sí; documento no | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | Los datos existen en incidencias y conciliación; no hay documento emitible |
| §3 Tratamiento: ajuste, reclamo, investigación, cuarentena | DOCX §3 | Confirmación | /compras/incidencias | SI | SI | /purchasing/incidents | compras | Spec 020 | E2E recorre un tratamiento | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §3 Confirmar y liberar a almacenamiento | DOCX §3 | Confirmación | /inventario/confirmacion | SI | SI | /purchasing/receipts | inventario | Spec 021 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §4 Determinar zona de almacenamiento | DOCX §4 | Ubicación | Ninguna guiada | NO | Catálogo de zonas sí | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | El usuario elige ubicación; nada propone ni determina la zona |
| §4 Clasificación por tipo y familia | DOCX §4 | Ubicación | Taxonomía de productos | Parcial | `category_id` | /master-data | maestros | Spec 022 | Ninguna | NO | NO | PARTIAL | Hay categoría; no interviene en la ubicación |
| §4 Clasificación por tamaño, peso, rotación y volumen | DOCX §4 | Ubicación | Ninguna | NO | NO | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | El maestro no guarda esos atributos. Ya bloquea peso y volumen en DM-IMP-COST-01 |
| §4 Condiciones especiales | DOCX §4 | Ubicación | Ninguna | NO | NO | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT |  |
| §4 Ubicación: zona, pasillo, rack, nivel, posición | DOCX §4 | Ubicación | /organizacion/ubicaciones; /compras/importaciones/{id} | SI | SI | /inventory/putaway | inventario | Spec 022 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §4 Zonas A a E | DOCX §4: «conviene validar» | Ubicación | Catálogo de zonas configurable | SI | SI | /organization | organization | — | Ninguna | NO | NO | SPONSOR_VALIDATION_REQUIRED | El sistema admite crearlas; la fuente pide validarlas para HJ y no hay reglas de rotación que las alimenten |
| §4 Etiquetar o identificar | DOCX §4 | Ubicación | Ninguna | NO | NO | Ninguna | — | — | Ninguna | NO | NO | NOT_BUILT | «Cuando corresponda»: falta definir cuándo |
| §4 Trasladar, colocar y registrar ubicación | DOCX §4 | Ubicación | /compras/importaciones/{id} | SI | SI | /inventory/putaway | inventario | Spec 022 | E2E: «Recibida y ubicada» | POSTGRESQL_BROWSER_VERIFIED | YES | COMPLETE |  |
| §4 Validar ubicación física contra registrada | DOCX §4 | Ubicación | Parcial | Parcial | SI | /inventory/putaway | inventario | Spec 022 | Fuera de la E2E | NO | NO | PARTIAL | «Confirmar ubicación» registra; no hay validación física independiente |
| §4 Reubicar por error | DOCX §4 | Ubicación | Ninguna identificada | NO confirmado | Movimientos con origen | /inventory/transfers no cubre el caso comprobado | inventario | — | Ninguna | NO | NO | NOT_BUILT | No hay función de reubicar dentro del almacén; las transferencias son el único candidato y no se verificaron para esto |
| §4 Liberar para preparación y despacho | DOCX §4 | Ubicación | /compras/importaciones/{id} | SI | SI | /inventory/putaway | inventario | Ventas | E2E llega a ubicada; no recorre el despacho posterior | NO | NO | PARTIAL | Disponibilidad no verificada en un pedido |
| Trazabilidad importación a ubicación final | DOCX, controles | Control | /compras/importaciones/{id} | SI | SI | /importaciones/{id} | compras | Specs 019 a 022 | E2E | POSTGRESQL_BROWSER_VERIFIED | YES | PARTIAL | IMPORT-PUTAWAY-ATRIBUCION: lo ubicado desde Inventario sin referencia no se atribuye al expediente |
| Conteo independiente | DOCX, controles | Control | /inventario/confirmacion | Parcial | SI | /purchasing/receipts | inventario | Spec 021 | Otras suites | NO | NO | EXISTS_NOT_REVALIDATED | `confirmation_same_user_allowed` existe; no revalidado aquí |
| Autorización de ajustes | DOCX, controles | Control | /compras/incidencias | SI | SI | /purchasing/incidents | compras | Spec 045 | Otras suites | NO | NO | EXISTS_NOT_REVALIDATED |  |
