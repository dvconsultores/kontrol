# PLAN — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de software / Arquitecto de datos |
| Ruta | `specs/002-maestros/plan.md` |

## 1. Validación contra la Constitución

| Principio | Cumplimiento |
|---|---|
| P1 Spec antes que código | ✔ Este plan no implementa |
| P2 Autorización expresa | ✔ Se detiene en `/speckit.analyze` |
| P3 Trazabilidad | ✔ `traceability-matrix.md` |
| P6 Seguridad en backend | ✔ permisos/alcance en backend |
| P7 Frontend uniforme | ✔ patrones WF y componentes compartidos |
| P8 No hardcodear reglas | ✔ rubros/atributos/perfiles versionados |
| P9 Instalación independiente | ✔ hereda 001 |
| P11 Accesibilidad/responsive | ✔ hereda 001 |
| P13 Integridad transaccional | ✔ constraints, idempotencia, versión/ETag |
| P15 Datos del cliente protegidos | ✔ hereda 001 |
| P17 No retrabajo visual | ✔ componentes compartidos |
| P18 Política de modales | ✔ formularios completos (ADR-015) |

**Resultado: compatible con la Constitución.**

## 2. Arquitectura

Módulos de backend (extienden la fundación de 001):

| Módulo | Responsabilidad en 002 |
|---|---|
| `master_data/parties` | Party + extensiones (Customer/Supplier/Carrier/Driver) + direcciones/contactos/cuentas |
| `master_data/catalog` | CatalogItem, Product, Service, taxonomía, plantillas, atributos, unidades, presentaciones |
| `master_data/profiles` | Perfiles versionados (inventario, trazabilidad, fiscal, regulatorio) |

Frontend: páginas/módulos por dominio (`maestros/terceros`, `maestros/productos`, `maestros/servicios`, `maestros/catalogos`), reutilizando `design-system` y componentes compartidos de 001.

## 3. Estructura de archivos esperada

```text
resources/backend/app/modules/master_data/
├── parties/         (models, service, api, tests)
├── catalog/         (models, service, api, tests)
├── profiles/        (models, service, api, tests)
resources/backend/alembic/versions/0002_maestros.py
resources/frontend/src/modules/maestros/
├── terceros/  productos/  servicios/  catalogos/
specs/002-maestros/... (este paquete)
```

## 4. Datos y migraciones

- Modelo en `data-model.md`; migración Alembic `0002_maestros` (upgrade/downgrade).
- Seeds idempotentes: unidades de medida base (UNIDAD, KG, LT, C/U, HORA...) y, opcionalmente, catálogo semilla de rubros (CL-002-11).
- Constraints: unique de RIF por empresa/rol, barcode por empresa/presentación, versión/ETag en maestros editables.

## 5. Contratos

- OpenAPI con endpoints REST para terceros, catálogo y perfiles.
- `allowed_actions` calculadas en backend.
- Búsqueda asíncrona con `q`, `status`, `page`, `page_size`.
- Contrato de errores heredado de 001.

## 6. Pruebas

Plan en `test-plan.md`: unitarias (validación RIF, duplicidad, conversiones, perfiles), integración (API/PostgreSQL, aislamiento multiempresa), E2E (asistente de producto, alta de tercero, búsqueda asíncrona), accesibilidad/responsive.

## 7. Fases de implementación (para `/speckit.implement`)

1. Modelos + migración `0002_maestros` + seeds.
2. Backend `parties` (CRUD + duplicidad + aprobación).
3. Backend `catalog` (taxonomía, atributos, items, productos, servicios).
4. Backend `profiles` (perfiles versionados).
5. Frontend: páginas de terceros, productos (asistente), servicios, taxonomía.
6. Búsqueda asíncrona (AsyncCombobox) y validaciones.
7. Tests (unit/integración/E2E) y CI.
8. Documentación y evidencia.

## 8. Entregables de esta fase documental

Este plan forma parte de la fase documental de `002-maestros`; **no autoriza implementación**. La implementación requiere `/speckit.analyze` consistente, **001 certificada** y autorización expresa.

## 9. Estado de aprobación

| Elemento | Estado |
|---|---|
| Arquitectura | ✔ |
| Datos | ✔ (data-model.md) |
| Pruebas | ✔ (test-plan.md) |
| Aprobación | Pendiente |
