# Spec 012 — Matriz de Rutas (route-matrix.md)

Fuente: `evidence/route-audit.json` (57 rutas) y `evidence/menu-route-audit.json`.

## Resumen
| Verificación | Resultado |
|---|---|
| Rutas declaradas en router | 57 |
| Rutas con página/import existente | 57 (0 rotos) |
| Opciones de menú | 53 |
| Menú con ruta declarada | 51 |
| **Menú sin ruta (→ 404)** | **2** |

## Menú roto (PATRÓN SUCURSALES)
| Grupo | Etiqueta | Ruta | Estado |
|---|---|---|---|
| Seguridad | Usuarios | `/seguridad/usuarios` | **RUTA_NO_DECLARADA** → 404 |
| Seguridad | Roles | `/seguridad/roles` | **RUTA_NO_DECLARADA** → 404 |

## Rutas verificadas (muestra representativa)
| Ruta | Componente | Página existe |
|---|---|---|
| `/` | DashboardPage | ✔ |
| `/organizacion/empresas` | EmpresasPage | ✔ |
| `/organizacion/sucursales` | SucursalesPage | ✔ |
| `/organizacion/almacenes` | AlmacenesPage | ✔ |
| `/maestros/terceros` | TercerosPage | ✔ |
| `/ventas/facturas` | FacturasVentasPage | ✔ |
| `/fiscal/emision` | EmisionPage | ✔ |
| `/licenciamiento/configuracion` | ConfiguracionCentralPage | ✔ |
| `/homologacion/actos` | ActosPage | ✔ |
| ... (total 57; ver `evidence/route-audit.json`) | | |
