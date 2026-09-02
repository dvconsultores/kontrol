# N10 — REGRESIÓN DE DOMINIO A/B

Cada dominio con dos empresas reales del mismo tenant y una tercera de otro.
`A posee lo de A`, `B posee lo de B`, cruce entre empresas bloqueado, cruce
entre tenants bloqueado.

| Dominio | Estado | Qué encontró N10 |
|---|---|---|
| Tesorería | PASS | La conciliación estaba protegida; su **línea** no. `resolve_line` comprobaba el estado y no el dueño |
| Compras / CxP | PASS | Tres rutas de línea sin contexto: cotización, recepción y devolución |
| Ventas / CxC | PASS | Dos rutas de línea sin contexto: cotización y devolución |
| Inventario | PASS | Sin hallazgos nuevos; N7 ya había cerrado el par empresa/almacén con clave compuesta |
| Regulatory | PASS | Sin hallazgos nuevos |
| Fiscal P0 | PASS | Sin hallazgos nuevos. El núcleo separado no lleva empresa por diseño (P4) |
| Aprobaciones | PASS | Cancelación sin contexto, y la elegibilidad de aprobadores ignorando la empresa |
| Maestros | PASS | Dos rutas creaban la misma conversión de unidades y solo una comprobaba algo |
| Organización | PASS | Listar establecimientos filtraba por tenant; crearlos, también |
| Identidad | PASS | Tres rutas operaban sobre la instalación entera |
| Auditoría | PASS | Actor, tenant y empresa correctos. Un desbordamiento de `entity_id` corregido |

## Paridad de cálculo fiscal

Las fórmulas no se tocaron en N10. Ninguna de las doce correcciones entra en el
motor de cálculo: todas añaden una comprobación de pertenencia antes de escribir
o acotan una consulta. Los totales mantienen paridad.

## Eventos

`outbox_events` está migrada y **no tiene ningún productor**: `OutboxEvent(` no
aparece fuera de su propia definición. Cero eventos escritos, cero eventos con
empresa incorrecta. No se inventa una arquitectura de eventos para llenarla
(§43).
