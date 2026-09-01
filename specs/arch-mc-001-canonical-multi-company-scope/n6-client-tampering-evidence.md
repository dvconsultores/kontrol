# MANIPULACIÓN DEL CLIENTE — N6

Ninguno de estos valores concede acceso. Todos son selectores de contexto; el
servidor vuelve a validar.

| Manipulación | Resultado |
|---|---|
| Empresa inventada en `sessionStorage` | no se adopta; las peticiones siguen con la autorizada |
| Empresa inventada en `localStorage` | no se restaura; se descarta la preferencia |
| Empresa de otro usuario en la pestaña | no se hereda: lleva el id de quien la eligió |
| Cabecera forzada a una empresa ajena del mismo tenant | **404** |
| Cabecera forzada a una empresa de otro tenant | **404** |
| Empresa ajena declarada en el cuerpo | **rechazada** |
| Cabecera con el identificador del tenant | nunca se envía; el servidor la rechazaría |

## Cómo se probó, y por qué importa

Las pruebas que comprueban la autoridad del servidor piden un token por el mismo
endpoint que usa la aplicación y **fuerzan la cabecera a mano**, que es
exactamente lo que haría alguien con las herramientas del navegador.

La primera versión de estas pruebas lanzaba `fetch` desde la página. Como el
token de acceso vive en memoria del módulo y no en una cookie, esas peticiones
salían sin autenticar: su 401 no decía nada sobre el control de empresa, y las
tres habrían pasado por el motivo equivocado.

Se incluye la prueba positiva —el contexto propio sí funciona y devuelve el
tercero sembrado en esa empresa— sin la cual los bloqueos podrían deberse a que
la ruta rechaza cualquier cosa.

## Un defecto real encontrado por el camino

`GET /organization/companies` devolvía **todas** las empresas del tenant,
ignorando `UserScope`. Es el endpoint que el selector usa como autoridad.

No concedía acceso: cada petición se seguía rechazando. Pero ofrecía al usuario
empresas en las que no puede operar y convertía el selector en una fuente de
errores inexplicables. Ahora resuelve con `accessible_company_ids`, la misma
autoridad que valida cada petición, para que la lista y el permiso no puedan
divergir.

La prueba se verificó en rojo contra el comportamiento anterior antes de darla
por buena.
