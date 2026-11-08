# Matriz de completitud de Terceros (Spec 002)

| Requisito | Prior. | Antes | Producto requerido | Subtarea |
|---|---|---|---|---|
| FR-002-001 Party común | P0 | Modelo; alta API sin nationality ni residence | Alta y edición con todos los campos | TF-C |
| FR-002-002 RIF y duplicidad | P0 | Solo el primer rol y el primer registro | Regla multirol; formato | TF-C |
| FR-002-003 direcciones, contactos, cuentas | P1 | Modelo sin superficie | CRUD con validez, sin borrar historia | TF-E |
| FR-002-004 Customer | P1 | Modelo sin superficie; `blocked` decorativo | Extensión operable; bloqueo efectivo | TF-F |
| FR-002-005 Supplier | P0 | Modelo sin superficie | Extensión operable | TF-G |
| FR-002-006 Carrier y Driver | P2 | Modelos sin superficie | Datos maestros operables; la operación sigue en Spec 008 | TF-G |
| FR-002-007 campos como texto | P0 | Modelo correcto | Conservar ceros en API y UI | TF-E, TF-L |
| FR-002-042 listado | P0 | Sin filtro ni paginación | Búsqueda, estado, paginación, acciones | TF-B |
| FR-002-043 búsqueda asíncrona | P0 | Hecho (`SelectorDeTercero`) | Preservar | — |
| FR-002-044 activar, desactivar, eliminar | P0 | Solo desactivar sin comprobar | Activar, desactivar con bloqueo, eliminar sin relaciones | TF-D |
| FR-002-045 auditoría por entidad | P0 | Nada | Eventos y timeline con Request ID | TF-I |
| US-002-001 | — | Solo API | Alta multirol en UI | TF-C, TF-K |
| US-002-003 | — | — | Perfil de retenciones; sin pago sin aprobación | TF-G, TF-H |
| US-002-009 | — | — | Conservar historia | TF-D |
| US-002-010 | — | Hecho | Preservar | — |
| US-002-011 | — | Estado decorativo | Aprobación que gobierna pagos | TF-G, TF-H |
| US-002-012 | — | Nada | Timeline | TF-I |
| EDGE-002-01 | — | Parcial | 409 con mensaje claro | TF-C |
| EDGE-002-02 | — | No bloquea | **Bloquear** con documentos activos | TF-D |
| EDGE-002-09 | — | Sin versión | 409 con versión | TF-J |
| EDGE-002-11 | — | Paga sin aprobar | **Bloquear** | TF-H |
| EDGE-002-12 | — | `TaxProfile` versionado en Spec 007 | No se duplica; se muestra | TF-K |
| EDGE-002-13 | — | 404 en tercero | 404 también en hijos y extensiones | TF-L |
| CL-002-04 | — | Permitía dos Party con un RIF | Un Party por RIF y empresa | TF-C |
| CL-002-07 | — | Campo sin uso | `withholding_profile` referencia; el motor sigue en fiscal | TF-G |
| CL-002-08 | — | Sin efecto | Aprobación requerida | TF-G, TF-H |

## Estados de la Spec frente al modelo

`data-model.md` describe `Party` con DRAFT y PENDING_APPROVAL, y `Supplier` con DRAFT y ACTIVE adicionales. El modelo y todos los consumidores usan `Party.status` ACTIVE/INACTIVE y `Supplier.approval_status` por defecto PENDING_APPROVAL. Se conserva el vocabulario en uso: PENDING_APPROVAL, APPROVED y REJECTED. La actividad la lleva `Party.status`, sin un estado ACTIVE duplicado en `Supplier`. No hay flujo de aprobación de `Party` en ningún requisito funcional: solo el de proveedor (US-002-011).

## Carrier y Driver

`CARRIER_DRIVER_FUNCTIONAL_OWNER = SPEC008` para la operación (vehículos, `TransportDriver`, evaluación del despacho). `PARTY_MASTER_ROLE_OWNER = SPEC002` para el rol y la extensión de datos maestros de FR-002-006, que se hacen operables sin duplicar la operación.

## Eliminar

FR-002-044: eliminar solo sin relaciones. Se implementa con `can_delete` calculado sobre las claves foráneas reales del esquema; cualquier referencia documental la bloquea. Los registros de auditoría se conservan.

## Estado final (2026-11-08)

Todos los requisitos de la matriz tienen backend, frontend y prueba funcional en local. El caso concurrente real y la E2E quedan en `FINAL_ENTERPRISE_CERTIFICATION`. `EDGE-002-12` se limita a mostrar la referencia `withholding_profile`: `TaxProfile` versionado sigue en Spec 007.
