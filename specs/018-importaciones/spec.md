# Spec 018 · Importaciones

**Fuente rectora:** `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, §1. Correlacionada con Volumen 2 (§6 compras, §8 recepción), Volumen 3 (§8, §13) y Volumen 4. Ningún volumen define máquina de estados ni wireframe propios de importación: se derivan aquí y se registran en `clarifications.md`.

**Estado:** en construcción. `SPEC018_END_TO_END_FLOW_COMPLETE = 0`.

## Resultado para el usuario

Compras abre un **expediente de importación** por menú y lo lleva desde la negociación con el proveedor hasta la mercancía liberada en almacén, viendo en todo momento en qué estado está, qué falta y cuál es la siguiente acción válida.

## Las 12 etapas del sponsor

| N.º | Etapa (DOCX §1) | Dueño | Estado |
|---|---|---|---|
| IMP-01 | Detectar necesidad de reposición o compra | Compras | Parcial: sin detección por rotación |
| IMP-02 | Revisar inventario, rotación y demanda | Inventario, Reportes | Parcial: existencias sí; rotación y proyección no |
| IMP-03 | Generar solicitud de compra | `/compras/requisiciones` | Existe; se reutiliza |
| IMP-04 | Aprobar según autoridad | Spec 045 | Existe; se reutiliza |
| IMP-05 | Seleccionar y confirmar proveedor | Terceros, cotizaciones | Existe; aprobación de proveedor hecha |
| IMP-06 | Negociar precio, cantidad, tiempos, INCOTERM, pago, entrega | **018** | **Ciclo 1** |
| IMP-07 | Emitir orden de compra | `/compras/ordenes`, vínculo en 018 | **Ciclo 1**: vínculo |
| IMP-08 | Recibir y validar proforma, packing list, embarque, certificados | **018**, Spec 046 | **Ciclo 1** |
| IMP-09 | Anticipo o pago al proveedor | CxP, puerta de proveedor | Ciclo 2: enlace desde el expediente |
| IMP-10 | Seguimiento del embarque internacional | **018** | Ciclo 2 |
| IMP-11 | Confirmar documentación completa y mercancía despachada | **018** | Documentación en ciclo 1; despacho en ciclo 2 |
| IMP-12 | Gestionar faltantes o correcciones con proveedor o agente | **018** | Observación en ciclo 1; gestión con agente en ciclo 2 |

Recepción, confirmación de inventario y ubicación (DOCX §2, §3 y §4) ya existen en las Specs 019 a 022. La Spec 018 las **enlaza**, no las duplica: ciclo 3.

## Requisitos

- **FR-018-001** Expediente con código único por empresa, proveedor, moneda y estado. El proveedor debe tener rol PROVEEDOR y estar activo.
- **FR-018-002** Negociación: INCOTERM, lugar, condiciones de pago y de entrega, fechas previstas. Precio y cantidad viven en la orden de compra, una sola fuente de verdad.
- **FR-018-003** Vincular una orden aprobada del mismo proveedor, empresa y moneda; una orden solo pertenece a un expediente activo.
- **FR-018-004** Lista documental con proforma, packing list y documento de embarque obligatorios; certificados o soportes añadibles.
- **FR-018-005** Cada documento pasa por recibido (con referencia), validado (con adjunto) u observado (con motivo). Los archivos usan la Spec 046.
- **FR-018-006** Confirmar la documentación exige todos los obligatorios validados; si no, se responde qué falta.
- **FR-018-007** Cancelar exige motivo y solo antes de confirmar la documentación.
- **FR-018-008** Todo cambio se audita y el detalle muestra su historial.
- **FR-018-009** El backend calcula acciones permitidas y siguiente acción; la interfaz las refleja.
- **FR-018-010** Aislamiento por empresa y permisos `compras:*`.

## Pantallas

| Ruta | Pantalla | Ciclo |
|---|---|---|
| `/compras/importaciones` | Listado con búsqueda, estado y paginación | 1 |
| `/compras/importaciones/nueva` | Nueva importación | 1 |
| `/compras/importaciones/:id` | Expediente: estado, siguiente acción, negociación, orden, documentos, historial | 1 |
| Expediente, sección Embarque | Seguimiento, agente, despacho | 2 |
| Expediente, sección Recepción | Enlace a recepciones, diferencias y ubicación | 3 |
| Expediente, sección Costos | Gastos de importación (Spec 026) | 4 |

## Fuera de este ciclo

Seguimiento, agente, pagos desde el expediente, recepción y costos. La Spec no se declara completa hasta cubrirlos.
