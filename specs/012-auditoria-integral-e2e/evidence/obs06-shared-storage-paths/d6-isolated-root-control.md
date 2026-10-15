# D6 · Control con raíz aislada (conftest temporal de la carpeta de sondas: `mkdtemp("kontrol-test-almacen-")` + `storage/` + `backups/` en `pytest_configure`, `cache_clear`, `rmtree` en `pytest_unconfigure`)
| Registro | Valor |
|---|---|
| A y B a la vez, rc | 0, 0 |
| `A_STORAGE != B_STORAGE` · `A_BACKUP != B_BACKUP` | **YES** · **YES** (`<tmp>/kontrol-test-almacen-<aleatorio>/storage`) |
| Ninguna es la fija | sí |
| El hijo no hereda la raíz del padre | sí (aunque viaje en el entorno) |
| Misma raíz dentro del proceso | sí: `Settings.storage_path` = entorno; proveedor documental y exportaciones bajo esa raíz; `Settings.backup_path` = entorno |
| Marcadores al empezar | `[]` en A y en B (nadie ve nada de nadie) |
| Raíces eliminadas al terminar | **YES** |
