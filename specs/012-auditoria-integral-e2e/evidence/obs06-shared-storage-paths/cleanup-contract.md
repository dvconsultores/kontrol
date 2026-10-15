# Contrato de limpieza actual
| Registro | Valor |
|---|---|
| `CREATOR` | el **producto** (`_exports_dir()` hace `mkdir(parents=True)`; `FilesystemStorageProvider` crea `documents/AAAA/MM/DD`) sobre la ruta que el conftest fija; `kontrol-test-backups` nunca se crea |
| `CLEANER` | **nadie**: ni conftest, ni fixture, ni `pytest_unconfigure`, ni `qa/suite_tiempos.py` (solo lo inventaría) |
| `CLEANUP_BOUNDARY` | ninguna |
| `CURRENT_PERSISTENCE_INTENTIONAL` | **NO**: ningún comentario, prueba ni spec exige que exportaciones o documentos sobrevivan a la sesión; la persistencia es un efecto de fijar la ruta por máquina (contraste: el volumen de instalación, en el mismo fichero, se elimina en `pytest_unconfigure`) |
`UNKNOWN = 0`.
