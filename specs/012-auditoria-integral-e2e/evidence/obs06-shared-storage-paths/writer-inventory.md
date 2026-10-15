# Escritores en la raíz compartida (inventario de solo lectura; estado del almacén fijo al empezar el ciclo)
| Fichero / prueba | Ruta | Objeto | Patrón de nombre | Limpieza | Persistencia esperada | Clase de colisión |
|---|---|---|---|---|---|---|
| `tests/test_reporting.py` (exportaciones CSV y PDF) | `<storage>/exports/` | `report-executive_ventas-<AAAAMMDDhhmmss>.csv/.pdf` | **marca de tiempo (1 s)** | ninguna | ninguna requerida (la prueba descarga en la misma sesión) | **timestamp**: dos procesos (o dos exportaciones del mismo informe en el mismo segundo) producen el **mismo nombre** |
| `tests/test_n9_integrity.py` (subidas por el proveedor por defecto) | `<storage>/documents/AAAA/MM/DD/` | binarios sintéticos | token opaco de 32 caracteres | ninguna | ninguna requerida | UUID/token: sin colisión práctica |
| `tests/test_documents.py`, `test_documents_security.py`, `test_documents_legacy_import.py` | `tmp_path_factory.mktemp("kontrol-docs…")` | — | — | pytest (basetemp) | — | no escriben en la raíz compartida |
Estado observado (solo lectura): 121 ficheros / 484 KB en `<tmp>/kontrol-test-storage`; `documents/2026/10/{13,14,15}`
55 ficheros (8 + 31 + 16 por día) y `exports/` 66 ficheros (3 por corrida completa: 2 CSV + 1 PDF), del 13 al 15 de
octubre. `kontrol-test-backups` no existe: ningún consumidor lo crea.
