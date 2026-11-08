# Secuencia del proceso según el sponsor

**Fuente única de los pasos:** `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, §1. Citas literales. El DOCX no define estados, campos de embarque ni el rol de agente; todo lo que no esté citado aquí es una decisión de ingeniería y figura en `plan.md`.

| SPONSOR_STEP | SOURCE (literal) | USER_ACTION | INPUT | OUTPUT | PRECONDITION | NEXT_STEP | SYSTEM_STATE_REQUIRED | NOTES |
|---|---|---|---|---|---|---|---|---|
| IMP-01 | «Detectar necesidad de reposición o compra.» | Identificar la necesidad | Existencias | Necesidad | — | IMP-02 | Ninguno | Sin detección automática |
| IMP-02 | «Revisar inventario disponible, rotación y proyección de demanda.» | Revisar | Existencias, ventas | Decisión | IMP-01 | IMP-03 | Ninguno | Rotación y proyección sin construir |
| IMP-03 | «Generar solicitud de compra o reposición.» | Crear requisición | Necesidad | Requisición | IMP-02 | IMP-04 | Compras | Existe |
| IMP-04 | «Validar y aprobar la compra según niveles de autoridad establecidos.» | Aprobar | Requisición | Aprobación | IMP-03 | IMP-05 | Spec 045 | Existe |
| IMP-05 | «Seleccionar y confirmar proveedor.» | Elegir proveedor | Ofertas | Proveedor | IMP-04 | IMP-06 | Terceros | Existe |
| IMP-06 | «Negociar condiciones: precio; cantidad; tiempos; INCOTERM; forma de pago; condiciones de entrega.» | Registrar condiciones | Proveedor | Condiciones | IMP-05 | IMP-07 | NEGOTIATING | Precio y cantidad, en la orden |
| IMP-07 | «Emitir orden de compra.» | Vincular orden | Condiciones | Orden | IMP-06 | IMP-08 | ORDERED | Orden en Compras |
| IMP-08 | «Recibir y validar documentación: factura proforma; packing list; documentos de embarque; certificados o soportes requeridos.» | Recibir y validar | Archivos | Documentos | IMP-07 | IMP-09 | ORDERED | — |
| IMP-09 | «Ejecutar anticipo o pago al proveedor según condiciones acordadas.» | Pagar | Condiciones | Pago o anticipo | IMP-07 | IMP-10 | ORDERED o posterior | El dinero vive en CxP |
| IMP-10 | «Realizar seguimiento al embarque internacional.» | Registrar seguimiento | Embarque | Hitos | IMP-07 | IMP-11 | ORDERED o posterior | Sin lista de campos en la fuente |
| IMP-11 | «Confirmar que la documentación esté completa y que la mercancía haya sido despachada.» | Confirmar los dos hechos | Documentos y embarque | Confirmación | IMP-08, IMP-10 | IMP-12 y §2 | DOCUMENTS_COMPLETE → DISPATCHED | Dos hechos; el orden interno es derivado |
| IMP-12 | «Gestionar cualquier faltante o corrección documental con proveedor, agente o responsable de importación.» | Gestionar | Hallazgo | Corrección | Cualquier momento desde IMP-07 | §2 Recepción | ORDERED o posterior | «Cualquier»: no se limita a un estado |

**Control crítico citado:** «Control documental de importación». **Sigue en la fuente:** §2 Recepción de la importación, §3 Confirmación del inventario, §4 Clasificación y ubicación.

## Lo que la fuente no dice

- No fija un orden obligatorio entre documentación, pago y seguimiento más allá de su enumeración. Un documento de embarque suele existir solo tras embarcar, así que exigir la documentación completa antes de seguir el embarque sería una imposición de ingeniería.
- No define «agente» como rol. Solo lo nombra como contraparte en IMP-12.
- No indica que una corrección abierta bloquee el despacho físico de la mercancía.

## Después del despacho: DOCX §2, §3 y §4

Citas literales del documento. Todas son `SOURCE_BACKED_PROCESS_STEP`. La columna «Dónde» y las etapas de abajo son `DERIVED_IMPLEMENTATION_DECISION`.

| Sección | Paso del sponsor | Spec dueña | Capacidad | Dónde lo hace el usuario |
|---|---|---|---|---|
| §2 | «Confirmar arribo de la mercancía.» | 019 | `POST /purchasing/receipts/{id}/arrival` | Expediente → Arribo |
| §2 | «Programar descarga y recepción.» | 019 | `unloading_scheduled_at` | API del expediente y pantalla Recepciones; el formulario del expediente no lo pide |
| §2 | «Recibir físicamente.» Comparación, inspección, bultos, conformidad | 019 | Líneas, inspección, calidad y aceptación | Expediente → Abrir recepción |
| §2 | «Si existen diferencias, registrar», «Escalar la novedad a Compras» | 020 | `ReceiptIncident` | Expediente → Gestionar incidencias |
| §3 | «Realizar conteo detallado por SKU o código» a «confirmar inventario» | 021 | Conteo y confirmación | Expediente → Confirmar inventario |
| §4 | «Asignar ubicación física específica», «Registrar la ubicación definitiva» | 022 | `POST /inventory/putaway` | Expediente → Ubicación |

**No cubierto por este tramo:** el reporte formal de diferencias como documento, la clasificación por tipo, familia, tamaño, peso, rotación y volumen, las zonas A a E (la fuente pide validarlas), el etiquetado interno y la validación física de coincidencia. El expediente tampoco lleva el flujo de reubicación.

## Etapa logística

Es un cálculo sobre datos de sus dueñas, no un estado guardado: `NO_RECEIPT → AWAITING_ARRIVAL → RECEIVING → INCIDENTS_OPEN → PENDING_CONFIRMATION → PENDING_PUTAWAY → PUT_AWAY`. El estado del expediente permanece en `DISPATCHED`. Decisión derivada: añadir un estado guardado duplicaría lo que ya dicen la recepción y los saldos.

Lo ubicado se atribuye a la recepción por `document_ref` igual a su código. Un put-away hecho desde el menú de Inventario sin esa referencia no cuenta para el expediente.

