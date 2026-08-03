# REGISTRO DE RIESGOS — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Especialista en gestión de riesgos |
| Ruta | `specs/001-fundacion/risk-register.md` |

Formato: | ID | Riesgo | Probabilidad | Impacto | Control | Responsable | Estado |

| ID | Riesgo | Prob. | Impacto | Control | Responsable | Estado |
|---|---|---|---|---|---|---|
| RSK-001 | Normativa fiscal desactualizada o mal interpretada | Alta | Crítico | `LEGAL_VALIDATION_REQUIRED`; revisión por abogado/contador antes de producción | Legal | Activo |
| RSK-002 | Versiones tecnológicas no verificadas (PostgreSQL/Vite/Python) | Media | Alto | Research + validación en CI antes de fijar lockfiles (CL-11/12/13) | Arquitecto | Activo |
| RSK-003 | Aislamiento multiempresa deficiente (acceso cruzado) | Media | Crítico | tenant/company en cada agregado; pruebas negativas | Datos/Seguridad | Activo |
| RSK-004 | Evasión de licencia por reloj o clonación | Media | Alto | Fecha confiable persistente; identidad persistente; heartbeats | Seguridad | Activo |
| RSK-005 | Retrabajo visual por inconsistencias | Alta | Medio | Sistema de diseño + componentes compartidos; ADR-006 | UI/UX | Activo |
| RSK-006 | Secreto en el repositorio | Media | Crítico | `.gitignore`, escaneo de secretos en CI | DevSecOps | Activo |
| RSK-007 | Reutilización de nombres/estructuras INNOVA | Media | Medio | Auditoría de marca en artefactos nuevos; KONTROL obligatorio | Producto | Activo |
| RSK-008 | No verificación de restauración de backups | Media | Alto | Restore probado periódicamente; RPO/RTO | Infraestructura | Activo |
| RSK-009 | Modalidad fiscal sin homologación | Alta | Crítico | Emisión fiscal fuera de alcance de 001; puertas G5 | Legal/QA | Activo |
| RSK-010 | Doble envío / duplicados por reintentos | Media | Alto | Idempotency-Key; ADR-013 | Backend | Activo |
| RSK-011 | Sobrescritura concurrente | Media | Alto | Versión/ETag + 409 | Backend | Activo |
| RSK-012 | Auditoría editable/borrable | Baja | Crítico | Append-only; ADR-012 | Backend | Activo |
| RSK-013 | Acceso no autorizado del soporte a datos del cliente | Media | Alto | Sin acceso remoto sin autorización expresa; sesión trazable | Operación | Activo |
| RSK-014 | Instalación no reproducible | Media | Alto | Imágenes fijadas, lockfiles, seeds idempotentes | DevSecOps | Activo |
| RSK-015 | Fallo de integración futura (SICA/SIGESAI/SENIAT) | Media | Alto | Contratos y outbox desde el inicio; no sustitución de organismos | Arquitecto | Activo |
| RSK-016 | Falta de revisión legal de la matriz normativa | Alta | Crítico | Bloqueante de producción; T-048 | Legal | Activo |

## Criterios

- Todo riesgo tiene control y responsable. ✔
- Riesgos críticos sin control → bloqueo de implementación.

## Estado

| Elemento | Estado |
|---|---|
| Registro de riesgos | ✔ |
| Controles asignados | ✔ |
| Aprobación | Pendiente |
