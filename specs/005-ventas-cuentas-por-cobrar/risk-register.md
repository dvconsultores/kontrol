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
