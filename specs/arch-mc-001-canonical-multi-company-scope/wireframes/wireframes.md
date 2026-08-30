# PANTALLAS — ARCH-MC-001

La remediación es sobre todo de servidor. En la interfaz toca tres cosas.

## 1. Selector de empresa

En la barra superior, siempre visible: **la empresa activa se ve sin desplegar
nada**. Un usuario que no sabe en qué empresa está no debería poder facturar.

- Con una sola empresa autorizada: se muestra el nombre, sin control de cambio.
  No se pide elegir entre una opción.
- Con varias: control desplegable con **solo las empresas autorizadas**.
- Operable con teclado; el cambio se anuncia a los lectores de pantalla.
- A 320 px se conserva visible, abreviando el nombre y manteniendo el código.

## 2. Cambio de empresa

Al cambiar:

1. Se invalidan **todas** las consultas de alcance de empresa.
2. Se muestra estado de carga: nunca datos de A bajo el rótulo de B.
3. Se conserva la ruta si tiene sentido en la empresa nueva; si no, se vuelve al
   listado del módulo.
4. **No** se cierra la sesión.

> Ver por un instante datos de la empresa anterior bajo el nombre de la nueva es
> el fallo más peligroso de esta pantalla, porque no parece un error.

## 3. Lo que **no** se hace

- **No** se añade un campo «empresa» a cada formulario. La empresa viene del
  contexto (`FR-MC-023`). Un formulario que la pregunta invita a equivocarse.
- **No** se muestran empresas a las que el usuario no accede, ni siquiera en gris.
- **No** se mezclan listas de dos empresas con una columna «empresa». Si hiciera
  falta una vista consolidada, sería una capacidad futura y explícita.

## 4. Estado tras cerrar sesión

Se limpian contexto, pista de empresa y cachés. La empresa del usuario anterior
no reaparece para el siguiente (`FR-MC-017`).

## 5. Manipulación

Cambiar a mano el valor guardado en el navegador **no** da acceso: el servidor
valida en cada petición. Hay prueba explícita de ello (`FR-MC-012`).
