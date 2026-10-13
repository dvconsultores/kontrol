# Rendimiento DESPUÉS (W37) · mismo guion y mismo dataset que ANTES (1 100 listas, 300 almacenes en D1; 50 y 1 en C2)

## SQLite en memoria
```
motor=sqlite · empresa D1: 1100 listas, 300 almacenes · empresa C2: 50 listas, 1 almacén
/sales/pick-lists                                       → 200 items=   20 total=1100 page=1 page_size=20 limit=None bytes=    3748     13.0 ms
/sales/pick-lists?page=1&page_size=20                   → 200 items=   20 total=1100 page=1 page_size=20 limit=None bytes=    3748     11.7 ms
/sales/pick-lists?page=2&page_size=100                  → 200 items=  100 total=1100 page=2 page_size=100 limit=None bytes=   18549     11.6 ms
/sales/pick-lists?page_size=101                         → 422 items=    - total=None page=None page_size=None limit=None bytes=     214      7.4 ms code=VALIDATION_ERROR
/sales/pick-lists?page=0                                → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      6.5 ms code=VALIDATION_ERROR
/sales/pick-lists?page=abc                              → 422 items=    - total=None page=None page_size=None limit=None bytes=     237      6.0 ms code=VALIDATION_ERROR
/organization/warehouses                                → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     21.1 ms
/organization/warehouses?limit=1                        → 200 items=    1 total=300 page=None page_size=None limit=1 bytes=     626     10.1 ms
/organization/warehouses?limit=50                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     12.9 ms
/organization/warehouses?limit=100                      → 200 items=  100 total=300 page=None page_size=None limit=100 bytes=   58336     16.7 ms
/organization/warehouses?limit=101                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      6.3 ms code=VALIDATION_ERROR
/organization/warehouses?limit=100000                   → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      5.5 ms code=VALIDATION_ERROR
/organization/warehouses?limit=0                        → 422 items=    - total=None page=None page_size=None limit=None bytes=     211      5.9 ms code=VALIDATION_ERROR
/organization/warehouses?limit=-1                       → 422 items=    - total=None page=None page_size=None limit=None bytes=     211      5.9 ms code=VALIDATION_ERROR
/organization/warehouses?limit=abc                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     238      5.5 ms code=VALIDATION_ERROR
/organization/warehouses?offset=0                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     11.7 ms
/organization/warehouses?offset=100000                  → 200 items=    0 total=300 page=None page_size=None limit=50 bytes=      51      7.4 ms
/organization/warehouses?offset=-1                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     212      5.6 ms code=VALIDATION_ERROR
```

## PostgreSQL
```
motor=postgresql · empresa D1: 1100 listas, 300 almacenes · empresa C2: 50 listas, 1 almacén
/sales/pick-lists                                       → 200 items=   20 total=1100 page=1 page_size=20 limit=None bytes=    3748     17.4 ms
/sales/pick-lists?page=1&page_size=20                   → 200 items=   20 total=1100 page=1 page_size=20 limit=None bytes=    3748     11.3 ms
/sales/pick-lists?page=2&page_size=100                  → 200 items=  100 total=1100 page=2 page_size=100 limit=None bytes=   18549     12.3 ms
/sales/pick-lists?page_size=101                         → 422 items=    - total=None page=None page_size=None limit=None bytes=     214      7.3 ms code=VALIDATION_ERROR
/sales/pick-lists?page=0                                → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      7.5 ms code=VALIDATION_ERROR
/sales/pick-lists?page=abc                              → 422 items=    - total=None page=None page_size=None limit=None bytes=     237      7.7 ms code=VALIDATION_ERROR
/organization/warehouses                                → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     28.8 ms
/organization/warehouses?limit=1                        → 200 items=    1 total=300 page=None page_size=None limit=1 bytes=     626     12.4 ms
/organization/warehouses?limit=50                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     18.1 ms
/organization/warehouses?limit=100                      → 200 items=  100 total=300 page=None page_size=None limit=100 bytes=   58336     23.2 ms
/organization/warehouses?limit=101                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      8.7 ms code=VALIDATION_ERROR
/organization/warehouses?limit=100000                   → 422 items=    - total=None page=None page_size=None limit=None bytes=     210      7.7 ms code=VALIDATION_ERROR
/organization/warehouses?limit=0                        → 422 items=    - total=None page=None page_size=None limit=None bytes=     211      8.4 ms code=VALIDATION_ERROR
/organization/warehouses?limit=-1                       → 422 items=    - total=None page=None page_size=None limit=None bytes=     211      7.8 ms code=VALIDATION_ERROR
/organization/warehouses?limit=abc                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     238      8.0 ms code=VALIDATION_ERROR
/organization/warehouses?offset=0                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     14.6 ms
/organization/warehouses?offset=100000                  → 200 items=    0 total=300 page=None page_size=None limit=50 bytes=      51     11.4 ms
/organization/warehouses?offset=-1                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     212      7.5 ms code=VALIDATION_ERROR
```

## Comparación

| Petición | ANTES | DESPUÉS |
|---|---|---|
| `GET /sales/pick-lists` (sin parámetros) | 200 · **1 100 items** · 203 550 B · ≈ 25 ms | 200 · **20 items** · **3 748 B** (−98 %) · ≈ 12 ms; `total` 1 100 |
| `GET /sales/pick-lists?page=2&page_size=100` | ignorado: 1 100 items | 100 items · 18 549 B · `page` 2 |
| `page_size=101` · `page=0` · `page=abc` | 200 con todo | **422 `VALIDATION_ERROR`** |
| `GET /organization/warehouses?limit=100000` | 200 · **300 items** · 175 139 B · ≈ 30 ms | **422** · 210 B · ≈ 6 ms |
| `limit=101` · `limit=0` · `limit=-1` · `offset=-1` | 200 (101 / 0 / 300 items) · PostgreSQL **500** en los negativos | **422** en los dos motores |
| `limit=100` (máximo) | 100 items · 58 336 B | igual |
| sin parámetros · `offset=100000` | 50 items · página vacía con `total` | igual (contrato WHL intacto) |

Sin SLO inventado: la medida demuestra que la respuesta deja de crecer con la colección (una página de 20 pesa 3,7 KB
frente a 203 KB) y que los valores fuera de contrato se rechazan en vez de servir la empresa entera o reventar.
