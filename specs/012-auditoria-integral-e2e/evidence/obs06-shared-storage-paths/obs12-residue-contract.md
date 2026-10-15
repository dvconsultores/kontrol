# Contrato de residuos de OBS-12 (`qa/suite_tiempos.py`)
| Registro | Valor |
|---|---|
| `CURRENT_FIXED_STORAGE_FIELD` | `residuos.almacen_fijo_presente` (`ALMACEN_FIJO = "kontrol-test-storage"`), anotado aparte, **no** como residuo |
| `CURRENT_RESIDUE_DEFINITION` | `residuos.efimeros`: directorios del tmp con prefijo `kontrol-test-sqlite-` o `kontrol-test-license-` (`PREFIJOS_EFIMEROS`) |
| Saneado | `<tmp>` sustituye el directorio temporal en el manifiesto |
| Pruebas | O12-09 (almacén fijo no es residuo), O12-10 (efímeros detectados) |
| `EXPECTED_CHANGE_IF_OBS06_CONFIRMED` | la raíz nueva por proceso (`kontrol-test-almacen-…`, o el nombre que fije la implementación) entra en `PREFIJOS_EFIMEROS` (su presencia tras una corrida = residuo); el almacén fijo antiguo pasa a `legado` (`almacen_fijo_legado_presente`), nunca falla la corrida; O12-09/10 se adaptan y O06-18 lo fija |
No se edita hasta el gate material.
