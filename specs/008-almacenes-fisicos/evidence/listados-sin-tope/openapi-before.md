# OpenAPI ANTES (W16)

Generado en proceso con `create_app().openapi()` (guion de medición).

```
operaciones 544 · protegidas 533 · públicas 11 · esquemas de seguridad ['BearerAccessToken']
GET /api/v1/organization/warehouses: parámetros q, branch_id, status, company_id, limit (integer, default 50, SIN máximo ni mínimo), offset (integer, default 0, SIN mínimo), X-Kontrol-Company; security BearerAccessToken; 200 schema {}
GET /api/v1/sales/pick-lists: parámetros order_id, X-Kontrol-Company (SIN page ni page_size); security BearerAccessToken; 200 schema {}
```

`X-Kontrol-Company` sigue siendo selector de contexto (su descripción lo dice), no autenticación. Documento completo guardado fuera del repositorio para la comparación DESPUÉS.
