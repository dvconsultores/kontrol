# EVIDENCIA DEL CONTEXTO EN LAS PETICIONES — N6

## 1. Un solo punto

`X-Kontrol-Company` se pone en un único lugar del cliente HTTP. Una prueba de
arquitectura comprueba que no exista una segunda asignación en todo el
frontend: añadir la cabecera a mano en cada servicio garantizaría que alguna se
olvidara, y esa sería exactamente la que operase en la empresa equivocada.

## 2. Se fija al crear la petición

No dentro del `fetch`, ni en el reintento tras renovar la sesión. Leer un valor
mutable más tarde permitiría que una petición nacida en la empresa A saliera con
la cabecera de B porque el usuario cambió mientras la promesa esperaba.

Quien crea la petición puede además fijarla explícitamente, para que una
operación larga —un formulario que se envía, una descarga— termine donde empezó.

## 3. Observado en la red

| Situación | Cabecera |
|---|---|
| Sesión en la empresa A | siempre A |
| Tras cambiar a B | siempre B, ninguna con A |
| Pestaña 1 en A y pestaña 2 en B | cada una la suya |
| Sin empresa resuelta | **ausente** |
| Rutas que no son de empresa | **ausente** |
| Identificador del tenant | **nunca** |

Comprobado interceptando el tráfico real del navegador en Chromium, Firefox y
WebKit, no leyendo el código.

## 4. Cuando no hay empresa

No se envía cadena vacía, ni `undefined`, ni la empresa anterior, ni el tenant.
Sin empresa no hay cabecera, y el servidor responde que hace falta elegir.

El repliegue `empresa ?? tenant` tiene además su propia prueba de arquitectura:
es el defecto de origen de KONTROL escrito en una línea, invisible con una
empresa por tenant y devastador con dos.

## 5. Descargas

Es donde más fácil se pierde el contexto: basta con abrir una URL directa o
poner un `href` y el navegador va sin cabecera y sin token.

Las descargas documentales piden el binario por el cliente central y solo
después lo convierten en un enlace local. Dos pruebas de arquitectura lo fijan:
que todo lo que construye un objeto descargable pase por el cliente, y que no
exista ningún enlace ni redirección que apunte directamente a la API.
