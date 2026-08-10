# Spec 012 — Cobertura de Requerimientos (requirements-coverage.md)

## Estado por dominio (pasada 1, sin validación normativa fiscal)
| Dominio | Req. cubiertos (UI+API) | Req. sin UI | Observación |
|---|---|---|---|
| Organización | Empresa, Sucursal, Almacén | **Establecimiento, Ubicación** | PARTIAL |
| Seguridad/Identity | Login, sesión, contraseña | **Usuarios, Roles** | BROKEN |
| Maestros | Terceros, Productos, Servicios, Catálogo | Perfiles fiscales | PARTIAL |
| Ventas | Cotización, Orden, Factura, CxC | — | PARTIAL (sin E2E) |
| Compras | Requisición, Orden, Recepción, Factura, CxP | — | PARTIAL |
| Inventario | Existencias, Kardex, Transferencias, Conteos, Ajustes | Movimientos/balances | PARTIAL |
| Tesorería | Cajas, IE, Transferencias, Conciliación, IGTF | — | PARTIAL |
| Fiscal | Config, Numeración, Emisión, Notas, Retenciones, Libros | Perfiles | PARTIAL |
| Regulatorio | Organismos, Vehículos, Permisos, Evaluación | — | PARTIAL |
| Reportes/Auditoría | Centro, Exportaciones, Auditoría | — | PARTIAL |
| Licenciamiento | Estado, Config central, Sync, Renovación, Eventos | — | COMPLETE |
| Homologación | Actos, Versiones, Timeline | — | PARTIAL |

## Conclusión
- **COMPLETE**: Licenciamiento + cadenas organizacionales básicas.
- **BROKEN**: Seguridad (Usuarios/Roles).
- **PARTIAL**: resto (falta UI de establecimiento/ubicación/perfiles o E2E de proceso).

Nota: la validación de cumplimiento normativo fiscal (IVA/ISLR/IGTF/retenciones/números de control) **no** se realizó en esta pasada y es requisito para GO.
