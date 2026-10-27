# OpenAPI: reconciliación (Spec 003 · company-scope-authorization)

Comparación de `create_app().openapi()` entre `HEAD` (021c1c6, extraído con `git archive`) y el árbol del ciclo.

| Medida | HEAD | Ciclo |
|---|---|---|
| Rutas | 418 | 418 |
| Esquemas de `components` | — | idénticos |
| Operaciones con diferencias | — | 480 |

Las 480 diferencias son la misma: la descripción de la cabecera `X-Kontrol-Company`, en el parámetro y en su `schema`. No cambia ningún tipo, `anyOf` ni `title`. La descripción añade:

> Si el usuario accede a la empresa pero no tiene en ella la autoridad que pide la operación, responde `403 COMPANY_SCOPE_FORBIDDEN`.

No cambian rutas, cuerpos, respuestas declaradas ni esquemas. Las 11 rutas de catálogos de todo el tenant cambian solo su dependencia de autorización, que no se expone en OpenAPI.

**OPENAPI_UNEXPLAINED_DRIFT = 0**
