# Orden determinista

| Registro | Valor |
|---|---|
| Orden de negocio actual (pick-lists) | `created_at desc` (sin cambio) |
| Desempate | `id asc`, el precedente ratificado del listado de empresas (`order_by(Company.created_at, Company.id)`) |
| Dónde | en SQL (`ORDER BY … LIMIT … OFFSET …`), comprobado con el capturador de sentencias (LT-SQL) |
| Prueba | LT-11: 1 100 listas, cinco grupos de diez con el mismo `created_at`; el orden completo coincide con la ordenación calculada en Python fuera de SQL; repetible entre peticiones; dentro de cada grupo, por `id` |
| Mutación | M-06 (sin desempate) muere |
| Almacenes | `code` asc, sin cambio (contrato WHL); LT-03b: tres páginas de 3 sin solape |

`ORDERING_CONTRACT = PROVEN` · `UNSTABLE_ORDER 0`.
