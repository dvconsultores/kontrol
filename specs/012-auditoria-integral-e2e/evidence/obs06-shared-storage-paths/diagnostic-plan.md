# Plan de diagnóstico (etapa 1; sondas **temporales** bajo `tests/sondas_almacen/` que se eliminan al terminar; marcadores sintéticos; nunca se borra ni se escribe en el almacén fijo histórico salvo los marcadores de las sondas, que se retiran)
Las sondas corren en procesos `pytest` hijos (patrón `tests/test_volumen_de_instalacion.py`) y cuentan por JSON saneado:
`storage` y `backup` del entorno, `get_settings().storage_path/backup_path`, la raíz real de `documents.get_storage()`, la de
`reporting._exports_dir()`, los marcadores que ven y los que escriben.
| Sonda | Qué prueba | Determinación |
|---|---|---|
| D1 | dos procesos hijos consecutivos y dos a la vez con el arnés actual | `STORAGE_PATH_EQUAL`, `BACKUP_PATH_EQUAL` |
| D2 | A escribe `marcador-<pid>` en `<storage>/sonda/` y en `<backup>/sonda/`; B lista; luego al revés | `A_SEES_B`, `B_SEES_A` |
| D3 | dos procesos exportan con la **fórmula real** de nombre (`report-<clave>-<AAAAMMDDhhmmss>`) forzando el mismo segundo (marca inyectada) | colisión / sobrescritura |
| D4 | A termina normalmente; B nuevo lista | `CROSS_RUN_PERSISTENCE` |
| D5 | inventario saneado del almacén fijo antes y después de un grupo representativo (`test_reporting.py`, `test_n9_integrity.py`) | residuo por corrida |
| D6 | control: cada hijo con raíz única inyectada en `pytest_configure` por un `conftest` **temporal** de la carpeta de sondas | A≠B, sin visibilidad, misma raíz en settings/documentos/exports dentro del proceso |
| D7 | control: el hijo elimina solo su raíz al cerrar; la del otro sigue | limpieza propia |
| D8 | control: con la inyección en `pytest_configure`, `app.main`/`create_app()`/`TestClient` y los consumidores ven la raíz inyectada | orden de captura |
Clases: SHARED_PATH_LEAK · STALE_STATE_ACROSS_RUNS · CROSS_PROCESS_COLLISION · HARNESS_CLEANUP_DEFECT ·
SETTINGS_CAPTURE_DEFECT · NO_EFFECT · NOT_REPRODUCED · PRODUCT_PATH_CONTRACT · OTHER. UNKNOWN = 0 al converger.
