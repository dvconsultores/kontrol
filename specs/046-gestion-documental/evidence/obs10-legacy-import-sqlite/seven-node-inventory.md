# Inventario exacto de los siete nodos (`tests/test_documents_legacy_import.py`; 8 pruebas, 7 rojas en SQLite, 0 en PostgreSQL)

| Prueba | Invariante (Spec 046) | Firma actual | Setup directo | HTTP | Hilos | Sesiones | Commit antes del HTTP | Sesión cerrada antes del HTTP | HTTP esperado | Estado final | PostgreSQL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `test_binario_localizable_y_verificable_se_importa` | FR-046-112: binario localizable se importa con hash verificado, `PENDING_SCAN`, fuente intacta | `StaleDataError` en `import_legacy_reference` | `DocumentType` + `LegacyDocumentReference` en la sesión de la prueba (flush, sin commit) | sí, **dentro** del setup: `_company_id()` ×2 (login + companies) y `_actor()` (sesión auxiliar) | no | S-prueba + S-API por petición + S-actor | no | no | — (los HTTP son de los ayudantes) | referencia `VALID_MANAGED_FILE`, documento y `StoredFile` creados | PASS |
| `test_lo_importado_no_se_entrega_hasta_verificarse` | lo importado no se entrega sin `CLEAN` | ídem | ídem | ídem + `GET /descargar` **tras** `db.close()` | no | ídem | sí (antes del GET) | sí | 409 `FILE_NOT_SCANNED` | ídem | PASS |
| `test_una_url_externa_no_se_importa_como_archivo_propio` | FR-046-113: URL externa no se importa | ídem | ídem | ayudantes | no | ídem | — | — | — | `MISSING_FILE`, `raw_value` intacto | PASS |
| `test_un_archivo_que_no_esta_se_reporta_no_se_inventa` | FR-046-113: no se inventa | ídem | ídem | ayudantes | no | ídem | — | — | — | `MISSING_FILE` + nota | PASS |
| `test_una_huella_que_no_coincide_detiene_la_importacion` | FR-046-112: hash distinto → `LEGACY_HASH_MISMATCH`, `MIGRATION_BLOCKER` | ídem | ídem | ayudantes | no | ídem | — | — | — | `MIGRATION_BLOCKER`, fuente intacta | PASS |
| `test_un_hash_suelto_sigue_sin_ser_un_documento` | hash sin binario no es documento | ídem | ídem | ayudantes | no | ídem | — | — | — | sin documento | PASS |
| `test_una_ruta_heredada_no_autoriza_a_salir_del_volumen` | contención: `../../etc/passwd` no sale de la raíz | ídem | ídem | ayudantes | no | ídem | — | — | — | `MISSING_FILE` | PASS |
| `test_ninguna_importacion_borra_la_fuente` (8.ª, verde) | §144: nada se borra | — | no | no | no | 0 | — | — | — | fuente intacta | PASS |

Dueña: 046 (docstring: FR-046-112/113, T-046-143/148; `tasks.md` T-046-143 ✅ apunta a este fichero); apoyo 054.
