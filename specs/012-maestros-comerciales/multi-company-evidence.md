# SPEC 012 — EVIDENCIA MULTIEMPRESA

Arnés: `T1 → A, B` · `T2 → C`. Usuarios `ua`, `ub`, `uab`, `uc`.

## Aislamiento

| Comprobación | Resultado |
|---|---|
| Los seis catálogos nacen vacíos en A | **PASS** |
| El mismo código existe en A y en B | **PASS** |
| El mismo código repetido dentro de A | **409** |
| A no versiona una lista de B | **404** |
| T1 no versiona una lista de T2 | **404** |
| `uab` en contexto A sobre una lista de B | **404** |
| `uab` en contexto B sobre una lista de B | **PASS** |
| Versión de otra lista, con lista propia válida | **404** |
| A no lee los ítems de una versión de B | **404** |
| A no usa una moneda de B | **404** |
| A no cotiza un artículo de B | **404** |
| Una lista de B no participa en una resolución de A | **PASS** |
| La política de descuento de A no alcanza a B | **PASS** |
| La precedencia de A no se filtra a B | **PASS** |

Fuga entre empresas: **0**. Entre tenants: **0**. Mezcla de datos: **0**.

## La prueba que va en las dos direcciones

`test_la_lista_de_b_no_participa_en_una_resolucion_de_a` crea el **mismo código
de artículo** en A y en B, pone precio solo en B, y resuelve en A. El resultado
correcto no es un error: es `resolved: false`.

Si la resolución cruzara la frontera, A vería el precio de B sin que nada
fallara, y ninguna prueba de bloqueo lo habría notado.

## La unidad de plataforma

`units_of_measure.company_id` admite nulo, y ese nulo es una unidad de la
plataforma que ven todas las empresas.

`test_una_unidad_de_plataforma_si_se_puede_usar` comprueba que la Spec 012 la
**acepta**. Es una prueba de que algo funciona, no de que algo se bloquea, y por
eso hace falta: una comprobación por igualdad estricta la habría rechazado, y
habría sido un rechazo invisible —la unidad existe y es legítima—.
