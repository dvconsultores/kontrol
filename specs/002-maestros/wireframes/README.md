# Wireframes — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Ruta | `specs/002-maestros/wireframes/` |

## Patrones reutilizados de 001

| Patrón | Uso en 002 |
|---|---|
| WF-01 Listado | Terceros, productos, servicios, taxonomía, unidades |
| WF-02 Formulario | Maestro de tercero, edición de producto/servicio |
| WF-03 Detalle | Detalle de producto, detalle de tercero |
| WF-06 Asistente | Asistente de producto (pasos) |
| WF-05 Matriz | Asignación de atributos por rubro/plantilla |

## Referencias DOC-04

- Pantalla 02 (Listado de productos) → WF-01.
- Pantalla 03 (Asistente de producto) → WF-06.
- Pantalla 04 (Detalle de producto) → WF-03.
- Pantalla 05 (Formulario de servicio) → WF-02 (sin lote/serial/almacén).
- Pantalla 07 (Maestro de cliente) → WF-02 (crédito y perfil fiscal).
- Pantalla 08 (Maestro de proveedor) → WF-02 (aprobación bancaria/fiscal).

## WF-002-A — Asistente de producto (pasos)

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Título · Paso 2 de 4  [1][2][3][4]              │
├──────────────────────────────────────────────────────────────┤
│ Identificación → Datos fiscales → Inventario → Regulación      │
│ [Campo] [Búsqueda asíncrona de rubro] [Atributos del rubro]    │
├──────────────────────────────────────────────────────────────┤
│ [Anterior]                                    [Siguiente]      │
└──────────────────────────────────────────────────────────────┘
```

Reglas: campos activados por plantilla/perfiles; guardar borrador y reanudar; no usar condiciones rígidas por nombre de rubro; pantalla completa (no modal).

## WF-002-B — Maestro de tercero

```text
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumbs · Título / Estado          [Activar] [Editar]      │
├──────────────────────────────────────────────────────────────┤
│ Identificación · Direcciones · Contactos · Cuentas bancarias   │
│ Roles: Cliente / Proveedor / Transportista / Conductor          │
├──────────────────────────────────────────────────────────────┤
│ Perfil fiscal · Retenciones · Aprobación bancaria              │
├──────────────────────────────────────────────────────────────┤
│ Timeline / Auditoría                                          │
└──────────────────────────────────────────────────────────────┘
```

Reglas: extensiones por rol; RIF como texto; duplicidad controlada por empresa/rol; proveedor requiere aprobación antes de pagar.
