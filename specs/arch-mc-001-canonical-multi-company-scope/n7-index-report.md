# ÍNDICES — N7

## 1. Ninguno añadido, y esa es la conclusión

PostgreSQL no crea un índice al declarar una clave foránea, así que las 85
claves nuevas podrían haber pedido 85 índices. No los piden.

| Medida | Valor |
|---|---:|
| Columnas `company_id` | 107 |
| Con índice que las cubre | **102** |
| Índices totales en el esquema | 498 |
| Índices añadidos por N7 | **0** |

## 2. Las cinco sin índice por empresa

`document_versions`, `idempotency_records`, `outbox_events`, `user_roles`,
`user_scopes`.

Ninguna se consulta por empresa: las versiones se piden por documento, los
registros de idempotencia por clave, los eventos por orden de publicación, y los
roles y alcances por usuario. La empresa es un filtro secundario, no el criterio
de búsqueda.

## 3. Medido, no supuesto

`EXPLAIN` sobre consultas representativas:

| Consulta | Plan |
|---|---|
| Listado de terceros por empresa | índice |
| Órdenes de compra por empresa | índice |
| Documentos fiscales por empresa | índice |
| Versiones de un documento | índice |
| Alcances de un usuario | índice |

Las cinco usan índice. Añadir alguno más sería optimización sin evidencia, y un
índice de más cuesta en cada escritura para no ahorrar nada en ninguna lectura.
