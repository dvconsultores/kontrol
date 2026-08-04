# REGISTRO DE RIESGOS — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/004-compras-cuentas-por-pagar/risk-register.md` |

Formato: | ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-004-01 | Factura del proveedor duplicada | Media | Alto | Clave de duplicidad + idempotencia + excepciones documentadas | Backend | Activo |
| RSK-004-02 | Aplicación que excede el saldo de CxP | Media | Crítico | Aplicaciones atómicas con bloqueo; no excede origen/destino | Backend | Activo |
| RSK-004-03 | Pago duplicado por reintentos | Media | Alto | `Idempotency-Key` en pago/aplicación | Backend | Activo |
| RSK-004-04 | Recepción sin actualizar inventario o duplicando lógica | Media | Alto | Invoca 003 `receive`; sin duplicar saldos/costos | Arquitecto | Activo |
| RSK-004-05 | Conciliación triple con diferencias no resueltas | Media | Alto | Diferencias explícitas + resolución auditada; POSTED condicionado | Contador | Activo |
| RSK-004-06 | Retención calculada mal (porcentajes hardcodeados) | Media | Alto | Reglas versionadas; motor fiscal en 007 (P8) | Contador | Activo |
| RSK-004-07 | Aprobaciones sin segregación | Baja | Crítico | Reglas de aprobación versionadas + segregación (DOC-02 §12) | Seguridad | Activo |
| RSK-004-08 | Aislamiento multiempresa débil | Baja | Crítico | company_id en cada agregado + pruebas negativas | Seguridad | Activo |
| RSK-004-09 | Acoplamiento con 003/006 | Media | Alto | Contratos de API v1 (receive; Payment/Application) | Arquitecto | Activo |
| RSK-004-10 | Snapshot ausente altera histórico | Media | Alto | Snapshot por línea (producto/precio/impuesto/tasa) | Datos | Activo |
| RSK-004-11 | Implementación sin dependencias previas | Media | Alto | Requiere 001 certificada + 002/003 implementados + autorización | Producto | Activo |

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |
