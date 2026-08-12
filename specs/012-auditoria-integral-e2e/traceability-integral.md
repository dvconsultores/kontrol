# Trazabilidad Integral — Spec 012 (pasada 2)

> Consultable en ambos sentidos: REQUISITO → CÓDIGO y CÓDIGO → REQUISITO. Fuentes: specs 001-011, `requerimientos/`, código productivo, evidencia regenerada.

## Requisito → Código (por dominio)

| Dominio | Spec | Requisito representativo | Implementación (UI/API/Backend) | Evidencia |
|---|---|---|---|---|
| Fundación | 001 | Empresa/Sucursal/Almacén/Licencia/Auditoría | EmpresasPage, SucursalesPage, AlmacenesPage; `/organization/*`; `/license/*` | E2E 19/20 |
| Seguridad | 001 | Login, sesión, usuarios, roles, permisos | LoginPage, UsuariosPage, RolesPage, SesionesPage; `/auth/*`, `/users`, `/roles` | tests security 8/8 |
| Maestros | 002 | Terceros, productos, servicios, catálogo, perfiles fiscales | TercerosPage, ProductosPage, ServiciosPage, CatalogosPage, PerfilesFiscalesPage | smoke API |
| Inventario | 003 | Existencias, kardex, movimientos, transferencias, conteos, ajustes, lotes, valorización | 8 páginas `/inventario/*` | smoke 22/22 |
| Compras/CxP | 004 | Requisición, orden, recepción, factura, CxP, notas, devoluciones | 7 páginas `/compras/*` | E2E |
| Ventas/CxC | 005 | Cotización, orden, despacho, factura, CxC, notas, devoluciones | 7 páginas `/ventas/*` | E2E |
| Tesorería | 006 | Cajas, IE, transferencias, conciliación, IGTF, maestros | 6 páginas `/tesoreria/*` | parcial |
| Fiscal | 007 | Config, numeración, emisión, notas, retenciones, libros, períodos | 6 páginas `/fiscal/*` | parcial (requiere validación normativa) |
| Regulatorio | 008 | Organismos, vehículos, permisos, evaluación, aprobaciones | 5 páginas `/regulatorio/*` | parcial |
| Reportes/Auditoría | 009 | Centro, exportaciones, auditoría | 3 páginas `/reportes/*` | **GAP: exportación sin archivo (KAUD-002/003)** |
| Licenciamiento | 010 | Config central, entitlements, renovación, eventos | 4 páginas `/licenciamiento/*` | smoke 3/3 |
| Homologación | 011 | Actos, versiones, timeline | 3 páginas `/homologacion/*` | parcial |

## Código → Requisito (detección de huérfanos)

| Detección | Resultado | Acción |
|---|---|---|
| Página sin Spec | 0 (todas las rutas mapean a un módulo con spec) | — |
| API sin consumidor | 58 endpoints sin llamada frontend (`backend-orphan-endpoints.json`) | Clasificar (KAUD-007) |
| Tabla sin uso | No detectada en pasada 2 (144 tablas; las de negocio se usan en servicios) | Revalidar en PostgreSQL |
| Requisito sin implementación | **Exportación con archivo (KAUD-002)**, **auditoría de negocio (KAUD-001)**, jobs list (KAUD-003) | Plan de remediación |
| Prueba sin requisito | No relevante | — |
| Menú → ruta inexistente | **0** (66/66) | Gate G1 OK |
| Ruta → página inexistente | **0** (72/72) | Gate G2 OK |
| Página → endpoint inexistente | **0** (234/234) | Gate G3 OK |

## Puertas permanentes (evitan regresión tipo Sucursales)

`src/tests/audit-completeness.test.ts` (vitest, 177 casos) implementa:
- **G1**: todo menú apunta a una ruta declarada.
- **G2**: toda ruta resuelve a una página existente (import válido).
- **G3/G4**: cada página con `apiFetch` apunta a un endpoint del fixture OpenAPI (`tests/fixtures/openapi-routes.json`).

Resultado esta pasada: **193/193 vitest PASS**. Estas puertas garantizan que un futuro cambio que rompa menú→página→API falle el CI.
