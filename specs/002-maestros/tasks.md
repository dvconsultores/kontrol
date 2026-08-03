# TASKS — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Ruta | `specs/002-maestros/tasks.md` |

Formato: | ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |

> Las tareas se ejecutan únicamente tras autorización expresa **002-maestros** y con **001 certificada**.

| ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |
|---|---|---|---|---|---|---|
| T-002-001 | FR-002-030 | Crear modelo de unidades y conversiones + migración | 001 (Alembic) | `master_data/catalog/models.py`, migración `0002` | Test de conversión | Datos |
| T-002-002 | FR-002-010 | Crear taxonomía (TaxonomyNode) y servicio de árbol | T-002-001 | `master_data/catalog/` | Test de árbol | Backend |
| T-002-003 | FR-002-011 | Crear atributos gobernados (Definition/Applicability/Value) | T-002-002 | `master_data/catalog/` | Test de atributos | Backend |
| T-002-004 | FR-002-020/021/022 | Crear CatalogItem + Product + Service | T-002-002 | `master_data/catalog/` | Test de especialización | Backend |
| T-002-005 | FR-002-031 | Crear perfiles versionados (inventario/trazabilidad/fiscal/regulatorio) | T-002-004 | `master_data/profiles/` | Test de versiones | Backend |
| T-002-006 | FR-002-001/002 | Crear Party + extensiones + duplicidad RIF | T-002-001 | `master_data/parties/` | Test de duplicidad | Backend |
| T-002-007 | FR-002-004/005 | Crear Customer y Supplier (aprobación) | T-002-006 | `master_data/parties/` | Test de aprobación | Backend |
| T-002-008 | FR-002-006 | Crear Carrier y Driver | T-002-006 | `master_data/parties/` | Test de extensión | Backend |
| T-002-009 | FR-002-003 | Crear direcciones, contactos y cuentas bancarias | T-002-006 | `master_data/parties/` | Test de validez | Backend |
| T-002-010 | FR-002-007 | Validaciones de texto (RIF, cédula, cuentas, códigos) | T-002-006 | `shared/validators.py` | Test de formatos | Backend |
| T-002-011 | FR-002-025/014 | Crear presentaciones, barcodes y variantes | T-002-004 | `master_data/catalog/` | Test de barcode unique | Backend |
| T-002-012 | FR-002-042/043 | Endpoints de listado y búsqueda asíncrona | T-002-004, T-002-006 | `contracts/api-contracts.md` | Contract test | Backend |
| T-002-013 | FR-002-044/045 | `allowed_actions` y auditoría por entidad | T-002-012 | servicios | Test de acciones/auditoría | Backend |
| T-002-014 | FR-002-040 | Asistente de producto (frontend, WF-002-A) | T-002-012 | `src/modules/maestros/productos/` | E2E | Frontend |
| T-002-015 | FR-002-041 | Detalle de producto | T-002-014 | `src/modules/maestros/productos/` | Component/E2E | Frontend |
| T-002-016 | FR-002-001/004/005 | Páginas de terceros (listado, formulario, detalle) | T-002-012 | `src/modules/maestros/terceros/` | E2E | Frontend |
| T-002-017 | FR-002-022 | Formulario de servicio (sin lote/serial/almacén) | T-002-014 | `src/modules/maestros/servicios/` | Component test | Frontend |
| T-002-018 | FR-002-010/011 | Páginas de taxonomía y atributos (matriz WF-05) | T-002-012 | `src/modules/maestros/catalogos/` | Component/E2E | Frontend |
| T-002-019 | FR-002-043 | AsyncCombobox (búsqueda asíncrona) | T-002-012 | `src/components/AsyncCombobox.tsx` | Vitest + E2E | Frontend |
| T-002-020 | FR-002-044 | Desactivar/activar/eliminar con confirmación | T-002-013 | componentes | Component test | Frontend |
| T-002-021 | NFR (multiempresa) | Pruebas de aislamiento negativo | T-002-012 | `tests/` | Pytest negativo | QA |
| T-002-022 | NFR (rendimiento) | Pruebas de búsqueda asíncrona y listados | T-002-019 | `tests/` | Prueba de rendimiento | QA |
| T-002-023 | NFR (accesibilidad) | axe + responsive en rutas de maestros | T-002-014..020 | Playwright | axe | QA |
| T-002-024 | CHK-002-DB-005 | CI: migración `0002` upgrade/downgrade | T-002-001 | `.github/workflows` | CI | DevSecOps |
| T-002-025 | CHK-002-OP-001 | Seeds idempotentes (unidades; rubros opcional CL-002-11) | T-002-001 | `scripts/seed.py` | Test de seed | Datos |

## Notas

- No existen tareas genéricas; todas son atómicas, con dependencias y pruebas.
- T-002-001 requiere la infraestructura de 001 (Alembic, Base, módulos) ya certificada.
