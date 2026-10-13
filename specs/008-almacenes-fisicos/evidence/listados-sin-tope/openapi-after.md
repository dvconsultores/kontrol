# OpenAPI DESPUÉS (W35)

```
OPENAPI DESPUÉS: operaciones 544 protegidas 533 públicas 11 esquemas ['BearerAccessToken']
operaciones con cambio: [('GET', '/api/v1/organization/warehouses'), ('GET', '/api/v1/sales/pick-lists')]
públicas antes/después iguales: True
/api/v1/organization/warehouses [('limit', {'type': 'integer', 'maximum': 100, 'minimum': 1, 'default': 50}), ('offset', {'type': 'integer', 'minimum': 0, 'default': 0})] security: [{'BearerAccessToken': []}] 422: True
/api/v1/sales/pick-lists [('page', {'type': 'integer', 'minimum': 1, 'default': 1}), ('page_size', {'type': 'integer', 'maximum': 100, 'minimum': 1, 'default': 20})] security: [{'BearerAccessToken': []}] 422: True
```

| Registro | Antes | Después |
|---|---|---|
| Operaciones | 544 | **544** |
| Protegidas / públicas | 533 / 11 | **533 / 11** (el mismo conjunto de públicas) |
| Esquema de seguridad | BearerAccessToken | BearerAccessToken |
| Operaciones cuyo documento cambia | — | exactamente 2: `GET /organization/warehouses` (`limit` 1..100 defecto 50; `offset` ≥ 0; 422 declarado) y `GET /sales/pick-lists` (`page` ≥ 1 defecto 1; `page_size` 1..100 defecto 20; 422 declarado) |
| `X-Kontrol-Company` | selector de contexto | sin cambio |
