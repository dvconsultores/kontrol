# Causa raíz
ROOT_CAUSE = `UNSCOPED_BODY_REFERENCE` · ROOT_CAUSE_PROVEN = 1 · UNKNOWN = 0.
`create_warehouse_full` copia `body.branch_id` a la fila y `patch_warehouse` hace `setattr` de cualquier campo enviado, sin
comprobar a qué empresa pertenece la sucursal. La única barrera es la FK simple `warehouses.branch_id → branches.id`, que
prueba que la sucursal existe, no que sea de la empresa activa. El aislamiento de la Spec 008 vive en el router
(`_alcance`, `_get_warehouse`), y este campo no pasaba por él.
CONTROL: `create_establishment` (organización) comprueba `sucursal.company_id != ctx.company_id → 404 BRANCH_NOT_FOUND`
y `test_n10_cross_company_writes.py::test_no_se_abre_un_establecimiento_en_la_sucursal_de_otra_empresa` lo fija. Con
la misma sonda, el establecimiento cruzado se rechaza y el almacén no.
PREDICCIÓN: con la misma comprobación en el alta y en el PATCH, D1-D3 dan 404 `BRANCH_NOT_FOUND` sin escribir, y D0 sigue
en 200. Una sucursal inexistente también da 404, sin distinguir «no existe» de «es ajena» (sin oráculo de enumeración).
