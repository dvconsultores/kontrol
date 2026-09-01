# SEGURIDAD DE FORMULARIOS ANTE UN CAMBIO DE EMPRESA — N6

## 1. El caso que se evita

Alguien abre un formulario en la empresa A, cambia a B en otra parte de la
pantalla, vuelve y pulsa Guardar. Sin protección, el registro se crearía en B
con datos pensados para A —clientes, almacenes y precios de otra empresa— y todo
respondería 200.

## 2. Cómo

La empresa se fija **al abrir**, no al enviar. Cuál sea la activa al pulsar el
botón es justamente el dato que no se puede usar.

`useCompanyScope` congela la empresa en la primera renderización de la pantalla
y expone `ejecutar`, que rechaza la operación si la empresa activa ya no es la de
apertura y, cuando la deja pasar, la envía explícitamente.

## 3. Estado

| Aspecto | Mecanismo | Resultado |
|---|---|---|
| Empresa de apertura capturada | `useRef`, congelada | PASS |
| Envío con empresa distinta | `CompanyMismatchError` | BLOQUEADO |
| Empresa enviada explícitamente | `companyId` de la petición | PASS |
| Sucursal seleccionada | se reinicia al remontar | PASS |
| Almacén seleccionado | se reinicia al remontar | PASS |
| Cuenta bancaria seleccionada | se reinicia al remontar | PASS |
| Filas marcadas en tablas | se reinician al remontar | PASS |
| Detalle de A en pantalla tras cambiar | se remonta | PASS |

## 4. Por qué el remontado resuelve la mayoría

Al cambiar de empresa, el contenido se remonta. Eso reinicia de una vez todo el
estado local de las pantallas: identificadores relacionados, filtros con
entidades de empresa, filas marcadas y formularios a medias.

Es deliberadamente contundente. La alternativa —limpiar a mano cada
identificador dependiente en cada pantalla— tendría la misma forma que el
problema que N6 corrige: funcionaría hasta que alguien añadiera una pantalla y
olvidara un campo.

## 5. Lo que esto no es

No es seguridad. El backend valida cada petición igual, y las regresiones de N5
lo demuestran desde el propio navegador: forzar la cabecera a una empresa ajena
devuelve 404, y declarar otra empresa en el cuerpo no la impone.

Es lo que impide que un descuido se convierta en un asiento en la empresa
equivocada, que es un daño distinto y no menor.
