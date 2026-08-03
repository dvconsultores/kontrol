# REGISTRO DE RIESGOS — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/002-maestros/risk-register.md` |

Formato: | ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-002-01 | EAV libre para datos críticos | Media | Crítico | Atributos gobernados; prohibición de EAV para inventario/impuestos/lotes/seriales/regulación | Arquitecto de datos | Activo |
| RSK-002-02 | Duplicidad de RIF mal controlada | Media | Alto | Unique por empresa/rol + validación de formato | Backend | Activo |
| RSK-002-03 | Catálogo multirrubro inflexible | Media | Alto | Taxonomía configurable + plantillas versionadas | Arquitecto | Activo |
| RSK-002-04 | Servicio tratado como inventario | Media | Medio | Especialización Product/Service; validación de dominio | Producto | Activo |
| RSK-002-05 | Rendimiento de catálogos grandes | Media | Alto | Búsqueda asíncrona backend, índices, paginación | Backend | Activo |
| RSK-002-06 | Aislamiento multiempresa débil | Baja | Crítico | company_id en cada agregado + pruebas negativas | Seguridad | Activo |
| RSK-002-07 | Perfiles con vigencias solapadas | Media | Medio | Constraints de vigencia + aprobación | Datos | Activo |
| RSK-002-08 | Retrabajo visual en maestros | Media | Medio | Componentes compartidos + patrones WF | UI/UX | Activo |
| RSK-002-09 | Implementación sin 001 certificada | Media | Alto | Requiere 001 certificada (CI/Docker/legal) antes de implementar | Producto | Activo |

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |
