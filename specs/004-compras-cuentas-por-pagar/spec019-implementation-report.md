# SPEC 019 — RECEPCIÓN FÍSICA · INFORME DE IMPLEMENTACIÓN

| Campo | Valor |
|---|---|
| Ciclo | `SPEC 019 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-03) |
| Base | `01987ff` |
| Migración | `0044_spec019_receipt` (revisa `0043_spec030_reservation`) |
| Fuente del proceso | `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx`, §2 |

## 1. Lo primero que se corrigió fue la cuenta

Cuatro artefactos de hoja de ruta repetían «Recepción física: 10 etapas, 3 cubiertas» y la matriz de
procesos listaba nueve filas. Leído el DOCX que todos citan, **son doce etapas**, y solo ocho son de
esta Spec: tres son de la 020 y una de la 022. La cifra se había copiado entre documentos sin volver
a la fuente. Este ciclo la corrige en los cinco artefactos afectados.

| # | Etapa | Owner | Antes | Ahora |
|---:|---|---|---|---|
| 1 | Confirmar arribo | 019 | ✖ | ✔ `arrival_at`, `arrival_confirmed_by`, ruta `/arrival` |
| 2 | Programar descarga | 019 | ✖ | ✔ `unloading_scheduled_at` al crear |
| 3 | Recibir físicamente | 019 | ◐ | ✔ con unidad, presentación, factor congelado y cantidad base |
| 4 | Comparar contra *packing list*, factura, orden y documentación | 019 | ◐ solo orden | ✔ cuatro referencias y cuatro resultados |
| 5 | Inspección visual inicial | 019 | ◐ binaria | ✔ `inspected_at`, `inspected_by`, `inspection_notes`, ruta `/inspection` |
| 6 | Validar bultos, estado, daños, identificación y referencias | 019 | ✖ | ✔ bultos declarados y contados; observación por línea |
| 7 | Determinar si es conforme | 019 | ◐ implícita | ✔ declarada en `quality_status`, sostenida por la inspección |
| 8 | Registrar diferencias | 020 | ✖ | pendiente de 020; el **hecho** ya se captura aquí |
| 9 | Evidencia de la incidencia | 020 · 046 | ✖ | pendiente de 020 |
| 10 | Escalar a Compras | 020 · 047 | ✖ | pendiente de 020 |
| 11 | Acta de recepción | 019 | ◐ | ✔ `record_issued_at`, `record_issued_by` al aceptar |
| 12 | Zona temporal de recepción | 022 | ✖ | pendiente de 022; el invariante «almacén conocido, ubicación nula» ya lo sostiene |

**019 pasa de 3 parciales a 8 de 8.**

## 2. El defecto de raíz, que no estaba donde parecía

El checkpoint operativo había localizado el síntoma: la línea de recepción no capturaba presentación
ni unidad, y el asiento tomaba la cantidad tecleada. Al implementar apareció la causa, un nivel más
abajo:

`record_movement` **sí** calculaba y guardaba la cantidad base en el movimiento, y a continuación
actualizaba el saldo con la cantidad **tecleada**:

```python
balance.qty_on_hand = _dec(balance.qty_on_hand) + _dec(signed)   # antes
balance.qty_on_hand = _dec(balance.qty_on_hand) + _dec(base_signed)  # ahora
```

De modo que el movimiento decía «24 unidades base» y el saldo sumaba 2. Y no era un riesgo futuro
de la recepción: la API de movimientos ya aceptaba `presentation_id`, así que **cualquier** entrada
con presentación estaba corrompiendo el saldo desde antes de esta Spec.

Es capacidad de la Spec 023 y la autorización pedía no absorber su motor. Pero IMP-019-014 —«el
movimiento usa la cantidad base, no la tecleada»— no puede cumplirse sin esta línea, y §7 admite
la corrección mínima en ese caso. Se hizo una línea, no un motor: sin presentación el factor es 1 y
las dos cantidades coinciden, así que ningún llamante anterior cambia de comportamiento.

## 3. Lo que se implementó

| Área | Cambio |
|---|---|
| Modelo | `GoodsReceipt` gana 16 columnas de proceso físico; `GoodsReceiptLine` gana 6 de observación y sobrante |
| Servicio | `confirmar_arribo`, `registrar_inspeccion`; `add_receipt_line` captura unidad, presentación, factor, tres cantidades base, observación física y sobrante; `accept_receipt` pasa la presentación al motor, acumula en base y emite el acta |
| Motor de inventario | el saldo se acumula en cantidad base (corrección mínima descrita arriba) |
| API | `GET /receipts/{id}` (no existía), `POST /receipts/{id}/arrival`, `POST /receipts/{id}/inspection`; la creación y la línea admiten los datos nuevos; listado y detalle los devuelven |
| Frontend | la página pasa de listar cinco columnas a capturar la recepción entera: arribo, bultos, comparación documental, inspección, presentación, estado físico, daño, lote, vencimiento y seriales, con el detalle de líneas y su cantidad base |
| Migración | `0044`, solo columnas y restricciones; ningún dato inventado |

## 4. Defectos preexistentes corregidos de paso

| Hallazgo | Por qué importaba |
|---|---|
| El saldo se acumulaba con la cantidad tecleada | Descrito en §2. Afectaba a toda entrada con presentación, no solo a la recepción |
| Los seriales viajaban como lista a una columna de texto, y la aceptación esperaba una cadena separada por comas | Los dos extremos no hablaban el mismo idioma: el serial se capturaba y no se materializaba |
| `add_receipt_line` no comprobaba que la línea de orden fuera de la orden de la recepción | Se podía recibir contra la línea de otra orden pasando su identificador por el cuerpo |
| `add_receipt_line` no comprobaba el estado de la recepción | Se podían añadir líneas a una recepción ya aceptada, que nunca entrarían al inventario |
| Aceptado más rechazado podía superar lo recibido | La suma no cuadraba y nadie lo impedía |
| La acumulación en la línea de orden era lectura-modificación-escritura sin bloqueo | Dos recepciones simultáneas contra la misma línea perdían una acumulación |
| La acumulación se hacía en cantidad tecleada | Comparar cajas contra unidades daría por recibida una orden que no lo está |

## 5. Lo que deliberadamente no se hizo

- **No se añadió un segundo veredicto de conformidad.** `quality_status` ya responde «¿la recepción
  es conforme?». Lo que faltaba no era el veredicto sino la inspección que lo sostiene.
- **No se asigna ubicación.** Recibir no es ubicar: el invariante «almacén conocido, ubicación nula»
  se preserva y se prueba. La ubicación es de la Spec 022.
- **No se crea el flujo de incidencias.** La observación física se captura; clasificarla, adjuntar su
  evidencia, escalarla y resolverla es de la Spec 020.
- **No se toca el momento de la disponibilidad.** El saldo sigue entrando en `DISPONIBLE`: cambiarlo
  es de la Spec 021 con capacidad de la 023, y así lo previó `ADR-D0-010`.
- **No se implementa el expediente de importación** (Spec 018) ni se crean motores paralelos de
  inventario, unidad, presentación o aprobaciones.
