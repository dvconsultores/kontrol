# SPEC 012 — FRONTEND

## Qué se construyó

| Pantalla | Ruta |
|---|---|
| Listas de precios · versiones · ítems | `/comercial/listas-precio` |
| Condiciones de pago | `/comercial/condiciones-pago` |

Páginas completas con ruta propia, no modales: `P18` y `ADR-015`.

## Regresión

| Comprobación | Resultado |
|---|---|
| Vitest | **282 / 282** (eran 278) |
| `tsc -b` | limpio |
| ESLint `--max-warnings 0` | limpio |
| `npm run build` | limpio |

Las cuatro pruebas nuevas no se escribieron: las descubrió
`audit-completeness.test.ts`, que recorre las rutas registradas y exige que cada
una exista y sea alcanzable. Añadir dos páginas añadió sus comprobaciones.

## El aislamiento por empresa no se implementó aquí

Y esa es la noticia. `queryKeyHashFn` antepone la empresa activa a toda clave de
consulta cuya raíz no esté exenta, y `comercial` no lo está. Las claves
`["comercial", "listas-precio"]` y `["comercial", "items", …]` quedaron separadas
por empresa **sin escribir una línea para ello**.

Es lo que N6 compró al resolverlo en la función de hash en vez de consulta por
consulta: la clave que nadie recordó actualizar queda protegida igual.

Contaminación entre empresas: **0**. Entre pestañas: **0**.

## La empresa fijada al abrir el formulario

El formulario de ítems escribe con `companyId` explícito, tomado de la empresa
activa cuando se abrió la versión, y con los identificadores de la lista y de la
versión guardados en el estado.

Cambiar el selector de empresa con el formulario abierto **no** convierte la
escritura en la otra empresa: la petición sale con la que tenía, y si esa
empresa ya no corresponde al padre, el backend responde `404`. La autoridad
sigue siendo del servidor; el frontend solo evita mandar una petición ambigua.

## Estados

Carga, error, vacío y sin empresa activa, en las dos pantallas.

El vacío dice algo útil en vez de disculparse: «el catálogo nace vacío: ningún
precio viene de fábrica» y «"contado" y "30 días" son datos de esta empresa».
Es la diferencia entre una pantalla que parece rota y una que explica el
diseño.

Una versión publicada no muestra el formulario de ítems: muestra por qué no lo
muestra —«para modificar precios, cree una versión nueva»—, que es donde la
interfaz enseña la regla en vez de esconderla.
