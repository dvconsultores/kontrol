# REGISTRO DE RIESGOS — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/003-inventario-logistica/risk-register.md` |

Formato: | ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-003-01 | Sobreadjudicación por concurrencia en reservas/salidas | Media | Crítico | Transacciones atómicas con `FOR UPDATE`/advisory locks; pruebas de concurrencia (T-003-022) | Backend | Activo |
| RSK-003-02 | Edición/borrado indebido de movimientos | Baja | Crítico | Inmutabilidad (sin UPDATE/DELETE físico), reverso vinculado, auditoría | Backend | Activo |
| RSK-003-03 | Diferencias de conteo mal aprobadas | Media | Alto | Segregación (crea/revisa/aprueba) + evidencia obligatoria | Costos | Activo |
| RSK-003-04 | Vencidos vendidos por falta de FEFO | Media | Alto | FEFO según perfil + bloqueo de vencidos + alertas | Almacén | Activo |
| RSK-003-05 | Valoración de costos incorrecta | Media | Alto | Capas versionadas, método por perfil (promedio/FIFO), pruebas de valoración | Costos | Activo |
| RSK-003-06 | Duplicidad de seriales/IMEI | Media | Alto | Unicidad según política (tenant/producto o global) + historial completo | Datos | Activo |
| RSK-003-07 | Balance inconsistente con movimientos | Media | Alto | Movimiento como fuente; balance reconstruible + job incremental | Backend | Activo |
| RSK-003-08 | Aislamiento multiempresa débil | Baja | Crítico | company_id en cada agregado + pruebas negativas | Seguridad | Activo |
| RSK-003-09 | Acoplamiento con 004/005 (recepción/despacho) | Media | Alto | API de integración v1 versionada; contract tests; sin duplicar lógica | Arquitecto | Activo |
| RSK-003-10 | Almacenes/ubicaciones sin maestros previos | Media | Medio | Crear Warehouse/Location en 003 como prerequisito (CL-003-02) | Datos | Activo |
| RSK-003-11 | Implementación sin 001 certificada / 002 implementado | Media | Alto | Requiere 001 certificada, 002 implementado y autorización expresa | Producto | Activo |
| RSK-003-12 | Congelamiento de conteo bloquea operaciones | Media | Medio | Política de congelamiento configurable por plan (SU-003-03) | Almacén | Activo |

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |
