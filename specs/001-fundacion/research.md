# RESEARCH — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Arquitecto de software / equipo multidisciplinario |
| Ruta | `specs/001-fundacion/research.md` |

## 1. Propósito

Documentar la investigación de decisiones técnicas y normativas de la fundación: problema, opciones, ventajas, desventajas, riesgos, decisión propuesta, fuente y estado. Ninguna decisión de versión se fija sin evidencia.

## 2. Decisiones investigadas

### 2.1 PostgreSQL (16 vs 18)

| Aspecto | Detalle |
|---|---|
| Problema | DOC-08 propone PostgreSQL 18.x; no hay otra versión fijada; DOC-03 no fija versión |
| Opciones | PostgreSQL 16 LTS-ish; PostgreSQL 18 (última) |
| Ventajas 18 | Últimas características, soporte oficial largo en la línea 18 |
| Desventajas 18 | Menor tiempo en mercado; validar compatibilidad de imágenes oficiales y drivers |
| Riesgos | Imagen no fijada; cambios de comportamiento |
| Decisión propuesta | **PostgreSQL 18.x** con imagen fijada por digest en producción; validar CVE y compatibilidad con SQLAlchemy 2 en CI; registrar en `dependency-matrix.md` |
| Fuente | DOC-08; docs.postgresql.org |
| Estado | PROPUESTA — requiere validación de soporte antes de fijar imagen (CL-11/CON-01) |

### 2.2 Vite (8.x) y React (19.x)

| Aspecto | Detalle |
|---|---|
| Problema | DOC-08 fija Vite 8.x, React 19.x, TypeScript 6.x |
| Opciones | Vite 8 + React 19; Vite 7 + React 19; plantillas oficiales |
| Decisión propuesta | **React 19.x + Vite 8.x** según DOC-08, sujeto a verificar la disponibilidad real de Vite 8 al momento de crear lockfiles; si Vite 8 no está estable, usar la línea estable más reciente y registrar ADR |
| Riesgos | Disponibilidad real; compatibilidad con plugins (Tailwind, React Router, TanStack) |
| Fuente | DOC-08; vite.dev; react.dev |
| Estado | PROPUESTA — verificar en fase de plan de implementación (CL-12/CON-02) |

### 2.3 Python (3.13.x) y FastAPI

| Aspecto | Detalle |
|---|---|
| Problema | DOC-08 fija Python 3.13.x |
| Decisión propuesta | **Python 3.13.x** con FastAPI, Pydantic 2, SQLAlchemy 2, Alembic 1; validar soporte de paquetes |
| Riesgos | Compatibilidad de dependencias nativas |
| Fuente | DOC-08; python.org |
| Estado | PROPUESTA — verificar (CL-13/CON-03) |

### 2.4 Estrategia JWT vs cookies HttpOnly

| Aspecto | Detalle |
|---|---|
| Problema | Almacenamiento de sesión seguro |
| Opciones | Access token en localStorage + refresh (frágil a XSS); cookies HttpOnly para refresh + access token en memoria |
| Decisión propuesta | **Cookies HttpOnly/Secure/SameSite para refresh + access token corto en memoria + CSRF + rotación y revocación de sesiones**. No localStorage para tokens de larga duración |
| Riesgos | CSRF (mitigado), complejidad de SPA multi-dominio |
| Fuente | DOC-08 (15.1); OWASP |
| Estado | ADR-004 propuesto |

### 2.5 Argon2id

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | **Argon2id** (passlib/argon2-cffi) con parámetros recomendados OWASP |
| Fuente | DOC-05; OWASP |
| Estado | Aprobado como mecanismo (ADR-004) |

### 2.6 Licenciamiento con firma asimétrica

| Aspecto | Detalle |
|---|---|
| Problema | Autoridad de licencia en el propietario; verificación local |
| Decisión propuesta | **Ed25519** (o equivalente aprobado). Clave privada solo en autoridad central; clave pública distribuida con `kid` versionado. Firma verificada en cada arranque y antes de aplicar licencia nueva. Instalación firma heartbeats con su par local |
| Riesgos | Rotación de claves, gestión de `kid`, clonación |
| Fuente | DOC-07 |
| Estado | ADR-005 propuesto |

### 2.7 Monolito modular

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | **Monolito modular** (sin microservicios prematuros). Separación en código, servicios, datos, contratos, permisos, eventos, pruebas y documentación |
| Riesgos | Acoplamiento si los límites no se respetan |
| Fuente | DOC-05, DOC-08 |
| Estado | ADR-001 propuesto |

### 2.8 Cola de trabajos (Redis/Celery)

| Aspecto | Detalle |
|---|---|
| Problema | Reportes pesados, correos, tareas programadas |
| Opciones | Celery+Redis; Dramatiq; RQ; ARQ; ninguno por ahora |
| Decisión propuesta | **No incluir en 001-fundacion.** Diferir hasta Spec con necesidad demostrada. El diseño deja outbox y tareas programadas acopladas al scheduler del sistema |
| Fuente | DOC-05 (opcional), DOC-08 (lo fija para fases posteriores) |
| Estado | ADR-009 propuesto (aplazar) |

### 2.9 Almacenamiento documental

| Aspecto | Detalle |
|---|---|
| Opciones | Volúmenes locales; MinIO; S3 |
| Decisión propuesta | **Volúmenes persistentes locales en 001**; metadatos/hash en DB; MinIO/S3 diferido (ADR-008) |
| Fuente | DOC-05, DOC-08 |
| Estado | ADR-008 propuesto |

### 2.10 Auditoría

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Tabla `AuditEvent` append-only con hash/encadenamiento opcional, partición por fecha/tenant, búsqueda indexada; considerar pgaudit para eventos de BD |
| Fuente | DOC-03, DOC-09 (SNAT/2024/000121) |
| Estado | ADR-012 propuesto |

### 2.11 Observabilidad

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Logs JSON + request ID + correlation ID; métricas mínimas; OpenTelemetry/Prometheus/Grafana/Sentry diferidos (ADR-010) |
| Fuente | DOC-05 |
| Estado | ADR-010 propuesto |

### 2.12 Backups

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | `pg_dump`/`pg_basebackup` o equivalente, cifrados, verificación de restauración periódica; RPO ≤15 min, RTO ≤4 h |
| Fuente | DOC-05, DOC-07 |
| Estado | Documentado en `backup-restore-plan.md` |

### 2.13 ReportLab

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | **ReportLab 4.x** en backend para documentos; plantillas versionadas, hash, metadatos; sin HTML impreso para documentos críticos |
| Fuente | DOC-08, DOC-01 |
| Estado | ADR-007 propuesto |

### 2.14 Nginx

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | **Nginx** como reverse proxy y servidor SPA; TLS, headers, compresión, límites |
| Fuente | DOC-08 |
| Estado | Aprobado en plan |

### 2.15 Estrategia de archivos

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Carga a servicio de documentos; referencias por ID; no base64 en JSON ordinario; hash, MIME, tamaño, permisos |
| Fuente | DOC-03, DOC-08 |
| Estado | ADR-008 propuesto |

### 2.16 Estrategia de multiempresa

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Tenant/Installation → Company → Branch → Establishment → Warehouse → Location; tenant/company explícito en cada agregado; filtros en repositorios; pruebas negativas |
| Fuente | DOC-03, DOC-05 |
| Estado | ADR-011 propuesto |

### 2.17 Estrategia de permisos

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | RBAC + alcance + condiciones; permisos por acción (ver, crear, editar, aprobar, rechazar, activar, desactivar, eliminar, anular, reversar, imprimir, reimprimir, exportar, cerrar, reabrir, configurar, auditar); deny by default; backend autoridad |
| Fuente | DOC-08, DOC-03 |
| Estado | En plan y data-model |

### 2.18 Estrategia de errores

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Contrato uniforme `{code, message, field_errors, request_id, details}`; manejo de 400/401/403/404/409/422/423/429/5xx; sin stack traces ni SQL |
| Fuente | DOC-03, DOC-08 |
| Estado | Contrato en `contracts/error-contract.md` |

### 2.19 Idempotencia

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | `Idempotency-Key` en POST críticos; tabla `IdempotencyRecord`; retries seguros |
| Fuente | DOC-03, DOC-05 |
| Estado | ADR-013 propuesto |

### 2.20 Concurrencia

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Versión/ETag en PATCH; 409 en conflicto; locks en operaciones transaccionales; correlativos asignados dentro de la transacción final |
| Fuente | DOC-03, DOC-08 |
| Estado | ADR-013 propuesto |

### 2.21 Estrategia de frontend

| Aspecto | Detalle |
|---|---|
| Decisión propuesta | Sistema de diseño primero; TanStack Query (keys por dominio/empresa); React Hook Form; Zod; rutas completas; sin modales para formularios complejos; sin scroll horizontal; WCAG 2.2 AA |
| Fuente | DOC-08 |
| Estado | `frontend-foundation.md` |

## 3. Decisiones normativas investigadas

| Tema | Hallazgo | Estado |
|---|---|---|
| Núcleo fiscal separado | Decisión central de producto (Volumen 1) | Vigente |
| Homologación | SNAT/2024/000121 exigía proveedor autorizado y sistema homologado; **derogada** por SNAT/2026/00084 (G.O. N.º 43.435, 12-08-2026): el requisito se retira; la auditoría inmutable se mantiene por principio propio | `DEROGADA (2026-08-12)` |
| Alícuotas IVA | General 16%, reducida 8% (art. 64), exportación 0%, consumo suntuario 15% (configurable) | `LEGAL_VALIDATION_REQUIRED` |
| IGTF | Decreto 4.972: 0% numerales 1-4; 3% numerales 5-6; ligado al pago, no a la moneda de la factura | `LEGAL_VALIDATION_REQUIRED` |
| Retención IVA | SNAT/2025/000054: 75% regla general, 100% supuestos | `LEGAL_VALIDATION_REQUIRED` |
| Retención ISLR | Decreto 1.808: catálogo art. 9, sustraendo, UT, pago o abono en cuenta | `LEGAL_VALIDATION_REQUIRED` |
| Resolución SICA | DM/N.º 025-12 vigente (G.O. 39.949); derogó DM/N.º 22-12 | `LEGAL_VALIDATION_REQUIRED` |
| Conservación | 10 años para facturación digital (SNAT/2024/000102) | `LEGAL_VALIDATION_REQUIRED` |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Decisiones técnicas investigadas | ✔ |
| Decisiones normativas | ✔ (todas marcadas para validación legal) |
| Versiones con evidencia | Parcial — verificar disponibilidad real al fijar lockfiles |
| Aprobación | Pendiente |
