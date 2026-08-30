# PANTALLAS — SPEC 012

Cinco pantallas. Todas completas, ninguna en modal (`P18`, `ADR-015`).

## 1. `/comercial/listas-precio` — Listas

`DataTable`: código · nombre · moneda · segmento · canal · versión vigente ·
vigencia · estado. Filtros: texto, moneda, canal, estado, «vigentes hoy».

Acciones según `allowed_actions` del backend, nunca según el rol adivinado en el
cliente.

## 2. `/comercial/listas-precio/:id` — Detalle

Cabecera con la lista. Debajo, **historial de versiones** con su vigencia y
estado — acumulativo, sin control de edición sobre las ya activas, igual que el
historial de versiones de la Spec 046.

Al abrir una versión: tabla de ítems con producto o categoría, presentación,
rango de volumen y precio. Los precios se editan **solo** en versiones `DRAFT`.

Si una versión está referenciada por documentos, se muestra **cuántos** y se
ofrece archivar, no eliminar.

## 3. `/comercial/condiciones-pago`

Formulario en página completa: código, nombre, tipo, y según el tipo, los campos
que correspondan —días, cuotas, anticipo—. El formulario **cambia con el tipo**;
no se muestran doce campos de los que diez sobran.

Estado vacío honesto: «No hay condiciones de pago. Cree las que use su empresa;
KONTROL no impone ninguna.»

## 4. `/comercial/zonas` y `/comercial/canales`

Tabla y alta. La zona admite jerarquía y vendedor asignado.

En la cabecera de zonas, una nota que evita el error de bulto:
«Territorio de ventas. No es la zona física del almacén.»

## 5. `/comercial/politicas` — Descuento y crédito

Dos pestañas. En descuento: ámbito, a qué aplica, máximo, umbral de aprobación,
acumulable, incompatibilidades.

El campo de máximo **nace vacío**, con ayuda: «Sin valor, no hay límite y ningún
descuento pedirá aprobación.» Es una decisión de la empresa, y decirlo evita que
alguien suponga que hay un límite oculto.

## 6. Dónde se ve el resultado

En la cotización (Spec 029, **no** en esta) el precio llegará resuelto y con su
origen visible: «Lista Mayoristas v3, vigente desde 01/07/2026». Esta Spec
entrega el dato para que esa pantalla pueda decirlo.

## 7. Responsive y accesibilidad

- 320 a 1440 sin desbordamiento horizontal; las tablas anchas desplazan **dentro
  de su contenedor**.
- Sin violaciones serias de WCAG 2.2 AA.
- Operable con teclado.
- Importes alineados a la derecha y con la moneda visible: un número sin moneda
  no es un precio.
