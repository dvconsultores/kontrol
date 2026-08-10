# Spec 012 — Matriz de Procesos (process-matrix.md)

## Procesos verificados E2E (local)
| Proceso | Actor | Pantallas | API | Resultado |
|---|---|---|---|---|
| Configuración inicial | Admin | Setup | POST `/setup/initialize` | ✔ 200 |
| Login | Usuario | Login | POST `/auth/login` | ✔ 200 |
| Activar empresa | Admin | Empresas | GET `/organization/companies` | ✔ 200 + feedback |
| Crear sucursal | Admin | Sucursales | GET/POST `/organization/branches` | ✔ 200 |
| Crear almacén | Admin | Almacenes | GET/POST `/organization/warehouses` | ✔ 200 |

## Procesos con cadena incompleta
| Proceso | Paso faltante | Clasificación |
|---|---|---|
| Org: Empresa→Sucursal→**Establecimiento**→Almacén | **Establecimiento sin UI** | `PROCESS_INCOMPLETE` (F-05) |
| Seguridad: gestión de **Usuarios** | Página/ruta ausente | `PROCESS_INCOMPLETE` (F-01) |
| Seguridad: gestión de **Roles** | Página/ruta y API ausentes | `PROCESS_INCOMPLETE` (F-02) |
| Inventario: movimientos/balances | API sin UI (balances/reverse) | `PROCESS_INCOMPLETE` (F-04) |

## Procesos presentes pero sin E2E integral (requieren T-10)
Ventas (cotización→orden→factura→CxC), Compras (requisición→orden→recepción→factura→CxP),
Inventario (conteo→ajuste→kardex), Tesorería (arqueo→conciliación), Fiscal (numeración→emisión→notas→retenciones→libros→cierre),
Regulatorio (permiso→evaluación→despacho), Homologación (acto→liberación).
