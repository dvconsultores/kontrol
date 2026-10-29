# STORAGE_SCOPE_INVENTORY — ciclo 07

Proveedores: `FilesystemStorageProvider` (documentos, `<storage_path>/documents`) y el directorio de exportaciones (`<storage_path>/exports`). S3 no está soportado (OD-S3-01: falla al arrancar).

| Operación | Proveedor | Dueño lógico | Tenant | Empresa | Generación de la clave | Lectura | Escritura | Borrado | Descarga | Separación del espacio | Riesgo de colisión | Prueba hostil |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Subir versión de documento | Filesystem | `StoredFile` → `Document` | derivado de la empresa | `documents.company_id` | servidor: `AAAA/MM/DD/` + `token_urlsafe(24)` (192 bits); nunca del cliente; nunca expuesta | — | temporal + `os.replace`, 0600 | — | — | mapeo opaco validado: la clave solo se alcanza por una fila acotada | despreciable (2⁻¹⁹²); `storage_key` única en la base | `test_iso_matrices` (documentos) |
| Descargar o previsualizar | Filesystem | idem | idem | documento de la empresa activa | — | por `StoredFile` del documento acotado | — | — | autenticada (ciclo 02) | idem | — | `test_iso_matrices`, BARRIDO-IDS |
| Borrar o purgar | Filesystem | idem | idem | idem | — | — | — | `delete(storage_key)` tras resolver la fila acotada | — | idem | — | BARRIDO-IDS (DELETE) |
| Importar legado | Filesystem | `LegacyDocumentReference` | instalación | anulable | servidor | ruta local de la operadora | `put` con verificación de hash | — | — | idem | idem | — (sin ruta HTTP) |
| Crear exportación | directorio de exportaciones | `ReportExport` | derivado | `report_exports.company_id` | `report-<clave>-<segundo>-<48 bits>.<fmt>` | — | **G-STO-01:** `write_bytes` sobrescribía → modo exclusivo `xb` | — | — | directorio plano compartido; acceso solo por la fila de la empresa | 2⁻⁴⁸ por colisión en el mismo segundo y la misma clave; antes **no fallaba cerrado** | `test_iso_relaciones` (colisión forzada) |
| Descargar exportación | idem | idem | idem | fila de la empresa + capacidad de origen | — | `get_export_file` acotado | — | — | `StreamingResponse` | idem | — | `test_iso_matrices` (exportaciones) |
| Copia y restauración (06) | ambos | instalación | todos | todas | — | lista blanca del manifiesto | staging + `os.replace` | — | — | por instalación | — | certificación C-00..C-13 |

**Decisión:**
- `STORAGE_NAMESPACE_DECISION = CURRENT_ISOLATION_SUFFICIENT` para los documentos, sin migración.
- Las exportaciones nuevas se escriben en modo exclusivo y las existentes no se tocan.
- `STORAGE_CROSS_TENANT_ACCESS = BLOCKED`, demostrado por las pruebas hostiles.
