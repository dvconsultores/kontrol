# N6 — CHECKPOINT DE FRONTEND MULTIEMPRESA

PostgreSQL 18.6 en UTC · **96 pruebas** nuevas o ampliadas · tres navegadores

## 1. El principio

El frontend **selecciona**; el backend **autoriza**. Nada de lo que se añadió
concede acceso: `localStorage`, `sessionStorage`, la cabecera, el estado de
React — todos son selectores de contexto que el servidor vuelve a validar.

Si esta capa se equivocara, el peor resultado sería un error, nunca un dato de
otra empresa. Las pruebas de manipulación lo comprueban desde el navegador.

## 2. Lo que había, y por qué no bastaba

El contexto anterior guardaba la empresa entera en `localStorage`, que se
comparte entre todas las pestañas del mismo origen. Con una empresa por tenant
daba igual. Con dos, cambiar de empresa en una pestaña cambia la otra por
debajo, con un formulario a medio llenar dentro.

Y la cabecera de empresa **no se enviaba en absoluto**: N1 la definió y N2
convirtió 234 puntos del backend a usarla, pero ninguna petición del frontend la
llevaba. Con una sola empresa el servidor la resolvía solo; con dos, cada
petición habría recibido `COMPANY_CONTEXT_REQUIRED`.

## 3. Cuatro cosas que estaban en una

| Qué | Dónde | Alcance |
|---|---|---|
| Preferencia del usuario | `localStorage`, bajo su id | navegador |
| Contexto operativo | `sessionStorage`, bajo su id | pestaña |
| Empresas autorizadas | backend | sesión |
| Estado de resolución | memoria | explícito, no booleanos |

Los estados son `AUTH_LOADING`, `COMPANY_LOADING`, `COMPANY_SELECTION_REQUIRED`,
`NO_COMPANIES`, `READY` y `ERROR`. Sin empresa resuelta no se pinta ninguna
pantalla de negocio: hacerlo dispararía peticiones de empresa sin saber cuál.

## 4. Defectos encontrados

| Dónde | Qué pasaba | Lo descubrió |
|---|---|---|
| `GET /organization/companies` | Devolvía todas las empresas del tenant, ignorando `UserScope` | Revisión de la autoridad del selector |
| `CompanyContext` | Borraba el contexto de la pestaña en cualquier parpadeo de autenticación | La prueba multi-pestaña |
| `CompanySelector` | `role="listbox"` con elementos de lista intercalados | La prueba de accesibilidad |

El primero es el más relevante y merece detalle. No concedía acceso —cada
petición se seguía rechazando— pero ofrecía empresas ajenas en el selector y
convertía cada intento en un error inexplicable. Es el endpoint que el frontend
usa como autoridad, así que un selector construido sobre él habría heredado el
defecto entero. Ahora resuelve con `accessible_company_ids`, la misma autoridad
que valida cada petición, para que la lista y el permiso no puedan divergir.

Se verificó en rojo contra el comportamiento anterior antes de darlo por bueno.

## 5. La caché

Separada en el único punto donde no se puede olvidar: la función que convierte
una clave de consulta en su identidad. Con 271 consultas repartidas por la
aplicación, confiar en que cada una recuerde añadir la empresa sería confiar en
que ninguna se olvide.

Invalidar no sustituye a esto. Invalidar marca lo viejo como caducado; separar
hace que lo de A y lo de B nunca hayan sido la misma entrada.

## 6. Pruebas propias que estaban mal

Tres pruebas E2E pedían datos con `fetch` desde la página. Como el token de
acceso vive en memoria del módulo y no en una cookie, esas peticiones salían sin
autenticar: su 401 no decía nada sobre el control de empresa, y las tres habrían
pasado por el motivo equivocado.

Las que comprueban la autoridad del servidor piden ahora un token por el mismo
endpoint que usa la aplicación y fuerzan la cabecera a mano, que es exactamente
lo que haría alguien con las herramientas del navegador.

La contaminación de caché se prueba con un tercero sembrado en cada empresa: sin
datos distintos, dos listas vacías tampoco se contaminan.

Los identificadores se leen del arranque en lugar de codificarlos, porque
sembrar de nuevo genera otros y una prueba con ids fijos empezaría a pasar
porque el id ya no existe.

## 7. Estado

| | |
|---|---|
| Vitest | 278/278 |
| tsc · eslint · build | limpios |
| E2E multiempresa | 39 (13 × 3 navegadores) |
| E2E accesibilidad y tamaños | 12 |
| Route crawl | 79 rutas sin 404 |
| OpenAPI | 294 rutas, sin cambios |
| Arquitectura backend | 3 EXPECTED_RED (N7/N8) · 0 inesperadas |

## 8. Lo que N6 no hizo

No se rediseñó el `CompanyContext` del backend. No se sustituyó ninguna
validación del servidor por lógica de cliente. No se tocó `REM-046-001`, ni los
tipos de recurso pendientes, ni la reconvergencia de 046.

La cabecera sigue sin declararse en OpenAPI —la dependencia la lee del
`Request`—; eso es trabajo de N8 y quedó anotado en N5.

## 9. Veredicto

**`ARCH-MC-001 — N6 COMPLETE`**

`SPEC 012 APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001`
`REM-046-001 BLOCKED_BY_ARCH_MC_001`

N7 a N10 quedan pendientes y no se inician.
