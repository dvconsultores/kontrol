# EVIDENCIA MULTI-PESTAÑA — N6

## 1. El problema

`localStorage` se comparte entre todas las pestañas del mismo origen. El
contexto anterior guardaba ahí la empresa activa, así que cambiar de empresa en
una pestaña cambiaba la otra por debajo — con un formulario a medio llenar
dentro, apuntando ya a otra empresa.

## 2. La separación

| Dónde | Qué guarda | Alcance |
|---|---|---|
| `localStorage` | última empresa elegida, bajo el id del usuario | navegador |
| `sessionStorage` | empresa de **esta** pestaña, bajo el id del usuario | pestaña |

Se verificó empíricamente que `sessionStorage` es realmente por pestaña en el
navegador de pruebas antes de apoyarse en ello, en vez de darlo por supuesto.

## 3. Comprobado

| Escenario | Resultado |
|---|---|
| Pestaña 1 en A, pestaña 2 en B | independientes |
| Cambiar en la 2 | la 1 no se mueve |
| Recargar la 1 | sigue en A |
| Recargar la 2 | sigue en B |
| Peticiones de cada una | cada una con su empresa |
| Cambios rápidos A↔B | sin mezcla |
| Nueva pestaña | arranca con la preferencia, luego independiente |

## 4. Un defecto propio que esta prueba destapó

La primera versión borraba el contexto de la pestaña en **cualquier** transición
a no autenticado. Una sesión puede quedarse sin autenticar un instante mientras
se renueva el token —y el token de renovación es de un solo uso, así que con
varias pestañas eso ocurre—; al volver, la pestaña se resolvía desde la
preferencia global, y bastaba con que otra pestaña hubiera cambiado de empresa
para arrastrarla.

Ahora lo guardado sobrevive a esos parpadeos. No concede nada: se revalida
siempre contra la lista autorizada, y lleva el identificador de quien lo eligió,
así que otro usuario que reutilice la misma pestaña tampoco lo hereda.

## 5. Lo que no se sincroniza entre pestañas

El cierre de sesión sí puede propagarse, según el diseño de autenticación
vigente. La empresa activa **no**: son dos cosas distintas y confundirlas
devolvería el problema de partida.
