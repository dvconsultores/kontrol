# READ-PERMISSION ENFORCEMENT · OpenAPI (2026-10-27)

**Método.** Herramienta de Claude, fuera del árbol (`scratchpad/tools/openapi_diff.py`):
- Vuelca `create_app().openapi()` de `HEAD` (`fb8ead1`, extraído con `git archive`) y del árbol del ciclo.
- Cada volcado usa una clave de firma efímera, generada al vuelo. No se guarda ni sale del equipo.
- Compara las rutas, los esquemas y cada operación.

| Medida | Resultado |
|---|---|
| Rutas | 420 → 420 |
| Rutas nuevas / retiradas | ninguna / ninguna |
| Esquemas nuevos / retirados / cambiados | ninguno / ninguno / ninguno |
| Operaciones cambiadas (parámetros, respuestas, `security`, descripción) | **0** |

**Por qué no hay deriva** (AD-10 del delta):
- `require_permission` depende de `get_current_user`, así que la seguridad publicada (`BearerAccessToken`) ya era la misma.
- La capacidad declarada no añade parámetros.
- El tablero sigue siendo un `dict` sin esquema tipado. Que omita indicadores no cambia ningún esquema publicado.

**OPENAPI_UNEXPLAINED_DRIFT = 0** · OPENAPI_DRIFT = 0.
