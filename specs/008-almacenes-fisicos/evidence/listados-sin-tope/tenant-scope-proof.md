# Aislamiento de empresa / tenant

Orden de la consulta en los dos listados (sin cambio en el alcance): contexto validado (`get_company_context`:
cabecera `X-Kontrol-Company` → acceso del usuario, 404 `COMPANY_NOT_FOUND` sin revelar) → filtro de empresa
(`Warehouse.company_id.in_(_alcance(ctx))` / `PickList.company_id == ctx.company_id`) → filtros funcionales → `count`
sobre la consulta filtrada → orden determinista → `offset`/`limit` en SQL. Nunca «traer todo → paginar → filtrar».

| Prueba | Evidencia | Resultado |
|---|---|---|
| Reproducción (antes) | C2 con 50 listas: `total` de D1 = 1 100 | el alcance ya era correcto |
| LT-12/13 | D1 1 100 (`PK-*`) · C2 50 (`PK2-*`) · almacenes C2 = 1 | PASS |
| LT-14 | empresa de otro tenant en la cabecera: 404 `COMPANY_NOT_FOUND`, sin `items` ni `total` en el cuerpo | PASS |
| M-07 (contar todas las empresas) · M-08 (paginar antes de filtrar) | mutantes muertos por LT-12/13 | KILLED |

`TENANT_SCOPE_CHANGE 0` · `CROSS_COMPANY_ITEM_LEAK 0` · `CROSS_COMPANY_TOTAL_LEAK 0`.
