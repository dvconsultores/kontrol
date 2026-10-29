# Retrospectiva de completitud de producto — KONTROL Gobierno (GOV-PRODUCT-COMPLETENESS-RETRO-01)

Primera aplicación de la norma permanente `docs/governance/product-completeness-and-owner-uat-policy.md` (2026-10-29, `develop` `0dbe632`). Ciclo de auditoría: **no cambia código de producto**.

| Entregable | Fichero |
|---|---|
| 1 · Política permanente | `docs/governance/product-completeness-and-owner-uat-policy.md` |
| 2 · Matriz de completitud (procesos × compuertas, incluida la matriz E2E) | `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.md` · `.csv` |
| 3 · Informe de avance real (cuatro métricas, fórmulas, módulos, replanificación) | `KONTROL_GOVERNMENT_REAL_PROGRESS_REPORT.md` |
| 4 · Catálogo de procesos listos para la dueña | `OWNER_UAT_READY_CATALOG.md` (vacío, y se dice) |
| 5 · Backlog de brechas | `GOVERNMENT_PRODUCT_COMPLETENESS_BACKLOG.md` · `.csv` |
| 6 · Reconciliación de afirmaciones históricas | `GOVERNMENT_HISTORICAL_CLAIM_INVENTORY.md` · `.csv` |
| 7 · Plan de prueba de la dueña | dentro del catálogo (4): hoy no hay ninguna tarjeta |
| Inventario de producto, frontend, backend, menú e integraciones | `GOVERNMENT_PRODUCT_INVENTORY.md` |
| Requisitos de Ingeniería × producto (194 entradas) | `GOVERNMENT_REQUIREMENTS_PRODUCT_MATRIX.md` · `.csv` |
| Fundamentos técnicos (38) | `GOVERNMENT_TECHNICAL_FOUNDATION_MATRIX.md` · `.csv` |
| Catálogo de no listos (122) | `GOVERNMENT_NOT_READY_CATALOG.md` |

Los CSV son la fuente legible por máquina; los `.md` homónimos se generan a partir de ellos. Las herramientas de medición son de Claude y viven en su espacio temporal, sin versionarse. Para regenerar: introspección de OpenAPI y SQLAlchemy, lectura del menú y del router, y extracción de la IR con `pdftotext -layout`.
