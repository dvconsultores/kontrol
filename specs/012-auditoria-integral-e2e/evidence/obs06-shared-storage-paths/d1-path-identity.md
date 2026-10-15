# D1 · Identidad de rutas entre procesos (arnés de `7a15f2e`, sin cambios; sondas temporales en procesos `pytest` hijos)
| Registro | Valor |
|---|---|
| Procesos | A y B consecutivos; A y B **a la vez** (pids distintos); los cuatro rc 0 |
| `PROCESS_A_STORAGE` / `PROCESS_B_STORAGE` | `<tmp>/kontrol-test-storage` / `<tmp>/kontrol-test-storage` |
| `PROCESS_A_BACKUP` / `PROCESS_B_BACKUP` | `<tmp>/kontrol-test-backups` / `<tmp>/kontrol-test-backups` |
| `STORAGE_PATH_EQUAL` · `BACKUP_PATH_EQUAL` | **YES** · **YES** (en los cuatro procesos) |
| `Settings` = entorno | sí en todos; proveedor documental `<tmp>/kontrol-test-storage/documents`; exportaciones `<tmp>/kontrol-test-storage/exports` |
| ¿Es el almacén fijo histórico? | sí: el mismo directorio que acumula ficheros desde el 2026-10-13 |
Fuente: `<scratch>/o6/diagnostico.txt` (D1).
