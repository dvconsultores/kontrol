# OpenAPI tras el cambio

`create_app().openapi()`: **544 operaciones · 533 protegidas · 11 públicas · esquemas `['BearerAccessToken']`**, igual que
la referencia. `POST /api/v1/auth/refresh`: respuestas declaradas `200`, `422`; sin `security` (pública por contrato: la
cookie HttpOnly no es un esquema OpenAPI), sin cambio. `tests/test_openapi_security.py` (OAS-01…15) verde en SQLite y
PostgreSQL dentro de las corridas dirigidas. No hay cambio de forma de respuesta ni de códigos: el 401 `SESSION_REVOKED`
del perdedor ya existía.
