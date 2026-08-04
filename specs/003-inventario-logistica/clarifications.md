# CLARIFICACIONES — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/003-inventario-logistica/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-003-01 | Alcance de 003 vs. 004/005 | ¿003 incluye recepción de compra y despacho de venta completos? | **No.** 003 es el **motor de inventario** (existencias, movimientos, lotes, seriales, reservas, transferencias, conteos, ajustes, costos, kardex) y expone la API que 004/005 invocarán (recibir, reservar, liberar, salida). Los documentos completos (orden, factura, conciliación, despacho regulatorio) son de 004/005 | Producto | Resuelto |
| CL-003-02 | Almacenes y ubicaciones | Los maestros Almacén/Ubicación (DOC-02 §3) no se implementaron en 001/002. ¿Dónde viven? | Se incluyen en **003** como prerequisito de custodia (pertenecen al dominio de inventario). La migración `0003` los crea. Si 001 ya tiene estructura de organización, se extiende sin duplicar | Arquitecto | Resuelto |
| CL-003-03 | Método de valoración | ¿Promedio ponderado o FIFO? | Ambos, **según perfil versionado** del producto/empresa (P8). Default: promedio ponderado. La política global por empresa queda pendiente (CL-003-11) | Costos | Resuelto |
| CL-003-04 | Reservas | ¿Automáticas o manuales? | Automáticas al aprobar una orden de venta (005) vía servicio de 003; la liberación es automática al despachar o cancelar. 003 no crea la orden, solo la reserva | Ventas | Resuelto |
| CL-003-05 | Vencidos | ¿Se bloquea la salida de lotes vencidos? | Sí, cuando el perfil lo exige; además FEFO prioriza el más próximo a vencer. El bloqueo anticipado (días) queda pendiente (CL-003-12) | Almacén | Resuelto |
| CL-003-06 | Diferencias de conteo | ¿El conteo ajusta automáticamente? | **No.** Las diferencias generan un ajuste que requiere revisión de Costos/auditor y aprobación (segregación DOC-02 §12) | Costos | Resuelto |
| CL-003-07 | Almacén multiempresa | ¿Un almacén puede servir a varias empresas? | No. Un almacén/ubicación pertenece a una empresa/sucursal/establecimiento; los movimientos confirman la misma empresa (DOC-03 §12) | Arquitecto de datos | Resuelto |
| CL-003-08 | Devoluciones | ¿Qué destinos tienen las devoluciones? | Destinos de inventario por estado: disponible, cuarentena, reparación, rechazo o desecho (DOC-02 §8). El flujo de devolución con documentos es de 004/005 | Almacén | Resuelto |
| CL-003-09 | Balance vs. kardex | ¿`InventoryBalance` es la fuente de verdad? | No. La fuente es el **movimiento**; `InventoryBalance` es una **proyección/cache reconstruible** (DOC-03 §5). El kardex se genera desde movimientos | Arquitecto de datos | Resuelto |
| CL-003-10 | Dependencia con 002 | ¿Se implementa 003 sin 002? | La implementación requiere **001 certificada** y **002 implementado** (productos con perfiles de inventario/trazabilidad son entrada de 003) y autorización expresa. La fase documental no requiere nada de eso | Producto | Resuelto |
| CL-003-13 | Negativos | ¿Se permiten existencias negativas? | Solo si la política del almacén lo permite y con aprobación; por defecto **no** (movimiento balanceado, reservas ≤ disponible) | Arquitecto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-003-01 | Valoración default por promedio ponderado, configurable por perfil versionado | Método de costeo distinto por empresa | Perfil de costeo versionado; migrar sin reescribir capas históricas |
| SU-003-02 | 004/005 crean los movimientos de recepción/despacho invocando servicios de 003; 003 no emite documentos fiscales | Acoplamiento entre módulos | Contrato de API versionado (v1) y pruebas de integración |
| SU-003-03 | El congelamiento de conteo es por política (por producto/almacén), no global siempre | Bloqueo operativo en conteos | Política de congelamiento configurable por plan |
| SU-003-04 | IMEI/serial únicos por tenant/producto según definición del perfil (no siempre global) | Colisión de seriales entre empresas | Regla de unicidad versionada por perfil |
| SU-003-05 | El `InventoryBalance` se reconstruye bajo demanda o por evento (outbox), no se recalcula en cada lectura | Costo de reconstrucción | Reconstrucción incremental + job; movimientos como fuente |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-003-11 | Política de costeo por defecto a nivel de empresa (método y moneda de valoración) | Valoración inicial | No la fase documental |
| CL-003-12 | Política de vencidos: días de bloqueo anticipado y destino automático | Salidas FEFO | No la fase documental |
| CL-003-14 | Política de ubicaciones: ¿pickeo por ubicación obligatoria o libre cuando el almacén no usa ubicaciones? | Configuración de picking | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
