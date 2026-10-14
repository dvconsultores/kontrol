# Inventario de fallos atribuidos a `ENTORNO-SIN-CLAMSCAN` (`failures-sqlite-tbline.txt`, `failures-pg-tbline.txt`)

Corridas dirigidas con `--tb=line` (una línea de origen por fallo) de `test_documents.py`, `test_documents_security.py`,
`test_documents_legacy_import.py` (+ `test_n9_integrity.py` en PostgreSQL): SQLite **42 failed · 25 passed · 3 skipped**;
PostgreSQL **37 failed · 33 passed · 3 skipped**. Mismo conjunto que las suites completas.

| Grupo | Firma | SQLite | PostgreSQL | Pruebas | Origen | Clasificación |
|---|---|---|---|---|---|---|
| S1 | `assert 422 == 200` / `{"code":"SCAN_FAILED",…}` en una subida | 17 | 17 | `test_documents.py` ×4, `test_documents_security.py` ×13 (incl. las 6 carreras ×8 nodos) | la aserción sobre `_upload`/`_post_version` | SCANNER_ABSENT_UPLOAD (la subida con `scan_required` se rechaza con 422 antes de todo lo demás) |
| S2 | consecuencia de una subida rechazada sin aserción inmediata: `KeyError: 'sha256'/'version_number'/'file'`, `AttributeError: 'NoneType'… stored_file_id` (ayudante `_stored_of`), `IndexError`, `assert 0 == 1`, `assert 200 == 409`, `{"deleted":true}` | 18 | 18 | `test_documents.py` ×6, `test_documents_security.py` ×12 | líneas posteriores a una subida que devolvió 422 (comprobado: cada una sube antes de la línea de fallo; `_stored_of` recibe una versión inexistente) | SCANNER_ABSENT_UPLOAD (secundaria) |
| S3 | `FILE_NOT_SCANNED` al descargar / `assert 409 == 500` | — | 2 | `test_n9_integrity.py` (PostgreSQL-only; fixture con `scan_required: False`: la subida entra, el archivo queda `SCAN_FAILED` y no se entrega) | fixture `_documento_con_archivo` | SCANNER_ABSENT_DELIVERY (el contrato exige `CLEAN` para entregar) |
| S4 | `StaleDataError: UPDATE statement on table 'legacy_document_references' expected to update 1 row(s); 0 were matched` | **7** | **0** | `test_documents_legacy_import.py` (7 de 8) | `service.import_legacy_reference` → `db.flush()`; `_reference()` deja la fila pendiente en la sesión de la prueba y `_company_id()` hace una petición HTTP en medio (`_CLIENT.get(/organization/companies)`): sobre la conexión pysqlite compartida de `make_engine()` el `commit`/`rollback` de la petición se lleva la fila de la prueba y el UPDATE no encuentra nada. PostgreSQL (conexión por sesión) pasa 8/8 **con el mismo analizador ausente** | **NO es del analizador**: HARNESS_SHARED_CONNECTION (misma familia que OBS-02 y que `test_el_historico…` de UoM). NEW_INDEPENDENT_DEBT, registrada (OBS-10), no absorbida |
| S5 | `libmagic no clasifica el SVG…` | skip | skip | `test_amz_02…` (SVG) | `pytest.skip` | entorno (libmagic), preexistente, no es del analizador |

Totales: SQLite 42 = 35 del analizador (S1+S2) + **7 que no lo son (S4)**; PostgreSQL 37 = 35 (S1+S2) + 2 (S3). `UNKNOWN = 0`.
La fila del roadmap decía «42 en SQLite (más `test_documents_legacy_import`)» atribuyéndolos al analizador: se corrige.
