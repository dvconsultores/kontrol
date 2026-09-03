# REGISTRO DE RIESGOS — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/risk-register.md` |

Formato: | ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-005-01 | Reserva/despacho sin el motor de 003 (sobreasignación) | Media | Crítico | Invoca 003 `reserve`/`ship`; sin duplicar saldos | Arquitecto | Activo |
| RSK-005-02 | Cobro duplicado por reintentos | Media | Alto | `Idempotency-Key` en cobro/aplicación | Backend | Activo |
| RSK-005-03 | Aplicación que excede el saldo de CxC | Media | Crítico | Motor atómico de 004; no excede origen/destino | Backend | Activo |
| RSK-005-04 | Despacho sin validación documental | Media | Alto | Bloqueo si falta/venció/no coincide (DOC-01 §5) | Logística | Activo |
| RSK-005-05 | Factura de venta editable tras emitir | Baja | Crítico | Inmutabilidad; nota/anulación vinculada (P5) | Backend | Activo |
| RSK-005-06 | Crédito mal controlado (exposición) | Media | Alto | Límites y reglas versionadas por empresa (P8) | Crédito | Activo |
| RSK-005-07 | Retención sufrida mal registrada | Media | Medio | Reglas versionadas; motor fiscal en 007 | Contador | Activo |
| RSK-005-08 | Aislamiento multiempresa débil | Baja | Crítico | company_id en cada agregado + pruebas negativas | Seguridad | Activo |
| RSK-005-09 | Acoplamiento con 003/004/006 | Media | Alto | Contratos de API v1 (reserve/pick/ship; cobros/aplicaciones) | Arquitecto | Activo |
| RSK-005-10 | Snapshot ausente altera histórico | Media | Alto | Snapshot por línea (producto/precio/impuesto/tasa) | Datos | Activo |
| RSK-005-11 | Implementación sin dependencias previas | Media | Alto | Requiere 001 certificada + 002/003/004 implementados + autorización | Producto | Activo |

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |

---

# RIESGOS — SPEC 030 (2026-09-02)

| ID | Riesgo | Probabilidad | Impacto | Mitigación aplicada | Estado |
|---|---|---|---|---|---|
| R-030-01 | Dos vendedores comprometen la misma unidad | Alta sin control | Venta que no se puede cumplir | Bloqueo de fila en PostgreSQL dentro de la transacción, orden determinista y prueba de carrera con dos conexiones | **Cerrado** |
| R-030-02 | Reservas huérfanas tras cancelar o rechazar | Alta (era el comportamiento anterior) | Disponible reducido para siempre | Liberación atómica en cancelar, rechazar, revertir y expirar; idempotente | **Cerrado** |
| R-030-03 | Reservar la cantidad tecleada en vez de la base | Alta con presentaciones | Reservar 1 caja en vez de 12 unidades | Reserva contra `base_quantity` con factor snapshot; prueba con caja ×12 y cambio posterior de factor | **Cerrado** |
| R-030-04 | Migrar reservas legadas inventándoles procedencia | Media | Evidencia histórica falsificada | Clasificación en cuatro clases; la línea solo se asocia si es determinista; las ambiguas se listan | **Cerrado** |
| R-030-05 | Pedidos en vuelo sin reserva al migrar | Cierta si hay `CREDIT_PENDING` | Pedido comprometido sin stock reservado | La migración no reserva por ellos: los lista para revisión manual | **Aceptado y documentado** |
| R-030-06 | Un pedido queda vivo sin reserva al expirar | Media | Contradice el invariante de la política | Expirar la reserva expira el pedido en la misma transacción; la liberación manual de reservas de pedido está prohibida | **Cerrado** |
| R-030-07 | Sobreventa por carrera confundida con sobreventa por política | Media | Se toleraría un defecto como si fuera una decisión | `oversell` se marca en la reserva y en la auditoría con el disponible previo; sin `allow_negative` la carrera no puede producirla | **Cerrado** |
| R-030-08 | El frontend muestra un estado que el backend no reconoce | Media | Acciones imposibles en pantalla | Las acciones salen de `allowed_actions`; `RESERVED` retirado de las tres pantallas y del contrato de tipos | **Cerrado** |
| R-030-09 | La expiración necesita un planificador que no existe | Media | Dependencia con una Spec no iniciada | TTL desactivado por defecto; endpoint idempotente; el planificador es de la Spec 047 y no bloquea | **Aceptado, no bloqueante** |
| R-030-10 | Restricciones solo en la migración y no en el ORM | Media (ocurrió en la Spec 012) | Las pruebas interrogarían un esquema más débil que producción | Declaradas en ambos y verificado el nombre en el catálogo de PostgreSQL | **Cerrado** |
