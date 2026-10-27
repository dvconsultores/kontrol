# OpenAPI: reconciliación (Spec 003 · ui-company-aware-authorization)

Comparación de `create_app().openapi()` entre `HEAD` (56f0f5e, extraído con `git archive`) y el árbol del ciclo, con una
`KONTROL_SECRET_KEY` efímera generada solo para construir la aplicación (no sale del equipo).

| Medida | HEAD | Ciclo |
|---|---|---|
| Rutas | 418 | 420 |
| Esquemas de `components` | — | idénticos (0 nuevos, 0 retirados, 0 cambiados) |
| Operaciones existentes con diferencias | — | 1 |

**Rutas nuevas (2), las dos de solo lectura y de proyección (AD-1, AD-2 del delta):**

| Ruta | Alcance | Respuesta |
|---|---|---|
| `GET /api/v1/auth/operations` | GLOBAL (sesión) | `{operations: [{method, path, capabilities, scope}]}`: el catálogo de operaciones y la capacidad que declara cada una. No depende del usuario ni de la empresa |
| `GET /api/v1/authority/company` | COMPANY (`X-Kontrol-Company`) | `{company_id, permissions}`: las capacidades efectivas del usuario en la empresa activa. Pasa por `get_company_context`: empresa inaccesible → 404 `COMPANY_NOT_FOUND` |

**Operación cambiada (1):** `GET /api/v1/auth/me`. Solo cambia la descripción, que documenta el campo nuevo
`tenant_permissions` (las capacidades que valen en todas las empresas del tenant; las usan los catálogos de todo el tenant). La
respuesta no tiene esquema tipado en `components`, así que el campo no altera ningún esquema. Los campos anteriores no cambian.

No cambia ninguna ruta existente, cuerpo, código de respuesta declarado ni esquema. Ninguna ruta expone más datos que los que el
backend ya usa para autorizar: el catálogo es estructural y las capacidades son las del propio usuario.

Guardas de deriva: `resources/backend/tests/test_frontend_fixtures.py` compara la instantánea del frontend
(`src/tests/fixtures/openapi-routes.json` y `operaciones.json`) con la aplicación viva; `qa/fixtures_de_frontend.py` las regenera.

**OPENAPI_UNEXPLAINED_DRIFT = 0**
