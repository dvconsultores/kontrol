# CONTRATO DE `X-Kontrol-Company` — N8

## 1. Existía sin estar escrito

La cabecera funciona desde N1, la usan 112 pruebas y el frontend la envía en
cada petición de empresa desde N6. Pero la dependencia la leía del `Request` en
lugar de declararla como parámetro, así que FastAPI no podía publicarla.

Quien leyera el contrato no sabría que existe. Un cliente escrito contra ese
contrato habría recibido `400 COMPANY_CONTEXT_REQUIRED` sin nada que le
explicara por qué.

## 2. Cómo se declara

Como parámetro de cabecera **opcional**, con una descripción escrita una sola
vez y compartida por todas las operaciones. Repetirla en cada ruta garantizaría
que alguna acabara diciendo algo distinto de lo que el servidor hace.

## 3. Por qué opcional y no obligatoria

Porque el servidor la resuelve solo cuando el usuario puede operar en una sola
empresa. Esa auto-resolución es una decisión de diseño de N1, no un descuido:
con una única empresa, exigir que se declare cuál sería pedirle al usuario que
conteste una pregunta que solo tiene una respuesta.

Declararla obligatoria describiría un sistema distinto, y quien leyera el
contrato enviaría siempre una cabecera que a veces sobra.

## 4. Semántica publicada

| Situación | Respuesta |
|---|---|
| Una sola empresa accesible, sin cabecera | Se resuelve sola |
| Varias, sin cabecera | `400 COMPANY_CONTEXT_REQUIRED` |
| Empresa a la que no se tiene acceso | `404 COMPANY_NOT_FOUND` |
| Empresa de otro tenant | `404`, sin revelar que existe |
| Empresa inactiva | `409 COMPANY_INACTIVE` |

La descripción publicada termina diciendo lo más importante: **la cabecera
selecciona, no concede**. El servidor valida el acceso en cada petición, y eso
es lo que hace que manipularla desde el navegador no sirva de nada.

## 5. Dónde aparece, y dónde no

| | |
|---|---:|
| Operaciones que la declaran | **332** |
| Operaciones que no | 72 |
| Rutas totales | 294, sin cambios |

Las 72 son autenticación, la propia lista de empresas —que es lo que se pide
*antes* de tener contexto—, instalación, licencia, salud y diagnóstico.
Declararla en todas partes sería tan falso como no declararla en ninguna.

## 6. Una sola lectura

El valor viene del parámetro declarado. Una prueba comprueba que nadie lo saque
además de `request.headers`: dos lecturas del mismo dato serían dos autoridades
sobre la misma decisión, y tarde o temprano una de las dos se quedaría atrás.

## 7. Comprobado por comportamiento

Además del contrato, se verifica lo que el servidor hace: un usuario con una
empresa opera sin cabecera, uno con dos recibe el error definido, y una ruta que
no es de empresa funciona sin ella.
