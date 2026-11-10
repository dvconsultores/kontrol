# Matriz de cobertura del sponsor

Fuente: Volumen 2, menú y procesos, y DOCX de importación, contrastados con router, permisos, OpenAPI y E2E del repositorio. Datos completos en `SPONSOR_APPLICATION_COVERAGE_MATRIX.csv`.

## Cómo se asigna el estado

| Estado | Regla |
|---|---|
| NOT_STARTED | Sin pantalla ni API |
| BACKEND_ONLY | API sin pantalla |
| FRONTEND_SHELL | Pantalla sin llamadas directas a la API |
| PARTIAL_PROCESS | Pantalla y API, sin E2E de usuario o con tramos faltantes |
| FUNCTIONAL_SLICE_COMPLETE | Pantalla, API y una E2E del repositorio que la recorre. **Esa E2E no se ejecutó en este ciclo: es un indicio, no una verificación** |
| OWNER_UAT_READY | Ejecutado de punta a punta en navegador real en este ciclo, con tarjeta de prueba |

**Límite:** la matriz se generó por menú y por ruta, no probando cada pantalla. Un estado alto no garantiza que el proceso esté completo. Un `requisito` de esta matriz es una opción del menú del Volumen 2, no cada frase del sponsor.

## Resumen

- Capacidades: 92
- OWNER_UAT_READY: 2
- FUNCTIONAL_SLICE_COMPLETE: 42
- PARTIAL_PROCESS: 30
- FRONTEND_SHELL: 1
- BACKEND_ONLY: 0
- NOT_STARTED: 17
- SCREEN_SURFACE_COVERAGE: 75 de 92 (superficie, no requisitos)
- GLOBAL_SPONSOR_REQUIREMENTS_COVERAGE: NOT_MEASURED_REQUIREMENT_BY_REQUIREMENT
- Verificadas en navegador con evidencia vigente: 5 filas
- OWNER_UAT_READY_MILESTONES: Terceros núcleo; Importaciones base, gastos, landed cost, reporte formal de diferencias, validación física y reubicación por error, sobre PostgreSQL. Comparación completa: `specs/018-importaciones/IMPORT_FULL_SPONSOR_COMPLETENESS_MATRIX.md`
- Importaciones: los ciclos 1 a 3 se verificaron primero solo sobre SQLite (`BROWSER_VERIFIED_SQLITE_ONLY`). El 2026-11-09 se halló que no funcionaban sobre PostgreSQL migrado; reparados y revalidados como `POSTGRESQL_BROWSER_VERIFIED` en `specs/018-importaciones/evidence/pg-integrity/EVIDENCE.md`. No se vuelve a aceptar SQLite como prueba de funcionamiento

## Por módulo

| Módulo | Capacidades | UAT | Tramo | Parcial | Sin empezar |
|---|---|---|---|---|---|
| Inicio | 5 | 0 | 2 | 2 | 1 |
| Maestros/Organización | 7 | 0 | 5 | 0 | 2 |
| Maestros/Terceros | 4 | 2 | 0 | 0 | 2 |
| Maestros/Productos | 8 | 0 | 5 | 1 | 2 |
| Maestros/Comercial | 6 | 0 | 0 | 2 | 4 |
| Maestros/Financiero | 2 | 0 | 1 | 1 | 0 |
| Maestros/Fiscal | 4 | 0 | 1 | 2 | 1 |
| Maestros/Regulatorio | 2 | 0 | 0 | 2 | 0 |
| Compras | 8 | 0 | 5 | 2 | 1 |
| Importaciones | 4 | 0 | 0 | 4 | 0 |
| Ventas | 8 | 0 | 5 | 2 | 1 |
| Inventario | 9 | 0 | 5 | 4 | 0 |
| CxC | 2 | 0 | 1 | 1 | 0 |
| CxP | 2 | 0 | 0 | 2 | 0 |
| Tesorería | 4 | 0 | 4 | 0 | 0 |
| Fiscal | 5 | 0 | 1 | 3 | 1 |
| Regulación | 3 | 0 | 0 | 2 | 1 |
| Reportes | 2 | 0 | 1 | 1 | 0 |
| Aprobaciones | 1 | 0 | 1 | 0 | 0 |
| Seguridad | 2 | 0 | 2 | 0 | 0 |
| Auditoría | 2 | 0 | 1 | 0 | 1 |
| Documentos | 1 | 0 | 1 | 0 | 0 |
| Configuración | 1 | 0 | 1 | 0 | 0 |

## Sin pantalla ni API

- Inicio: Vencimientos
- Maestros/Organización: Centros de costo
- Maestros/Organización: Unidades de negocio
- Maestros/Terceros: Vendedores
- Maestros/Terceros: Beneficiarios
- Maestros/Productos: Plantillas
- Maestros/Productos: Marcas y modelos
- Maestros/Comercial: Crédito
- Maestros/Comercial: Zonas y rutas
- Maestros/Comercial: Comisiones
- Maestros/Comercial: Descuentos
- Maestros/Fiscal: Plantillas fiscales
- Compras: Comparación de ofertas
- Ventas: Crédito
- Fiscal: Contingencia
- Regulación: Vencimientos
- Auditoría: Incidentes
