# SPEC — 001-FUNDACION

| Campo | Valor |
|---|---|
| Código | 001-fundacion |
| Nombre | Fundación de KONTROL |
| Versión | 1.0 (borrador para aprobación) |
| Estado | ESPECIFICADA (pendiente de `/speckit.analyze` y autorización expresa) |
| Responsable | Product Owner de KONTROL |
| Fecha | 2026-08-03 |
| Fuente | Volúmenes 0–6 de KONTROL; Estándar Maestro de Frontend v1.0; Especificación de Licenciamiento; Leyes Venezolanas; Expediente SICA/SIGESAI/Decreto 1.808; Compilación Providencias SENIAT |
| Dependencias | Ninguna (es la primera iniciativa) |
| Exclusiones | Ver apartado 12.4 |
| Ruta | `specs/001-fundacion/spec.md` |

---

## 1. Propósito y alcance

`001-fundacion` establece la base documental, arquitectónica, técnica, de seguridad, de licenciamiento y operativa sobre la cual se construirán todas las Specs posteriores. **No implementa procesos de negocio completos** (compras, ventas, facturación fiscal, inventario, tesorería, retenciones, libros, SICA/SIGESAI).

Su misión es comprobar una trayectoria fundacional completa:
instalación Docker → inicialización segura → identificación de instalación → activación de licencia → creación de empresa inicial → creación segura del administrador → cambio obligatorio de contraseña → inicio de sesión → App Shell → navegación por permisos → auditoría de acceso → modos de licencia (completo / solo consulta) → health checks → backup → restauración → diagnóstico.

## 2. Problema

- KONTROL inicia desde cero; no es continuación técnica de INNOVA.
- INNOVA dejó lecciones de retrabajo (frontend inconsistente, permisos limitados a CRUD, tablas con scroll, modales abusados, seguridad de tokens) que no deben repetirse.
- Se necesita una base arquitectónica, visual, operativa y de seguridad común y reproducible.
- Cada cliente tendrá una instalación Docker independiente; el propietario controla el licenciamiento; el administrador local gestiona su empresa.
- Los dominios fiscales deben permanecer separados, versionados e inalterables.
- Las referencias INNOVA son únicamente fuente de requerimientos, normativa y antecedente; no autoridad arquitectónica.

## 3. Objetivos

1. Fundación reproducible (Docker Compose, migraciones, seeds idempotentes).
2. Seguridad por defecto (backend como autoridad, secretos gestionados, Argon2id).
3. Multiempresa (Tenant/Installation → Company → Branch → Establishment → Warehouse → Location).
4. Auditoría integral e inmutable.
5. Licenciamiento local mínimo (verificar firma, aplicar modos, bloquear escritura).
6. Frontend uniforme con sistema de diseño y componentes compartidos.
7. Backend monolito modular con contratos explícitos.
8. Despliegue Docker con imágenes versionadas.
9. Pruebas automatizadas (unidad, componentes, integración, E2E, infraestructura).
10. Trazabilidad completa (requisito → Spec → plan → tarea → código → prueba → evidencia).

## 4. Fuera de alcance (exclusiones)

- Procesos completos de compras, ventas, facturación fiscal, inventario, tesorería, CxC, CxP, retenciones, libros, SICA, SIGESAI, reportes empresariales completos (Specs posteriores).
- Portal central de licencias completo (`010-licenciamiento-central`).
- Integración automática con organismos (SENIAT/SUNAGRO/INSAI/SACS).
- Homologación formal ante el SENIAT (fase posterior).
- Migración de datos de INNOVA.
- Emisión fiscal real (facturación) — solo se prepara la infraestructura del núcleo fiscal.
- Selección/implementación de cola de trabajos (Redis/Celery), almacenamiento de objetos (MinIO/S3) y observabilidad avanzada (Prometheus/Grafana/Sentry) — requieren ADR y necesidad demostrada.

## 5. Actores

| Actor | Descripción |
|---|---|
| Propietario de KONTROL | Organización titular; controla licencias, activación, renovación, derechos, revocación |
| Operador de licencias | Revisa comprobantes, prepara renovaciones |
| Auditor de licencias | Consulta contratos y eventos (solo lectura) |
| Administrador de empresa | Configura empresa, usuarios, roles, permisos dentro de la instalación |
| Administrador técnico del servidor | Instala Docker, DNS, TLS, respaldos |
| Usuario empresarial | Opera según rol y estado de licencia |
| Auditor | Consulta integral, evidencias, exportaciones controladas |
| Soporte técnico | L1/L2/L3 según matriz de soporte |
| Servicio programado | Tareas de salud, diagnóstico, respaldos |
| Integración | Clientes API futuros |

## 6. Historias de usuario

| ID | Historia |
|---|---|
| US-001 | Como técnico, quiero instalar KONTROL con Docker Compose de forma reproducible para levantar una instalación aislada por cliente. |
| US-002 | Como sistema, quiero generar una identidad de instalación persistente para que los contenedores puedan recrearse sin perderla. |
| US-003 | Como administrador local, quiero importar y activar una licencia firmada para habilitar la instalación. |
| US-004 | Como sistema, quiero crear la empresa inicial y el administrador mediante un asistente seguro para que no existan credenciales fijas. |
| US-005 | Como administrador local, quiero que se me exija cambiar la contraseña inicial para garantizar acceso seguro. |
| US-006 | Como usuario, quiero iniciar y cerrar sesión de forma segura para acceder según mi rol. |
| US-007 | Como usuario, quiero navegar el App Shell según mis permisos para ver solo lo que me corresponde. |
| US-008 | Como usuario, quiero recibir un acceso prohibido claro cuando intento una acción sin permiso. |
| US-009 | Como auditor, quiero consultar la auditoría de accesos para verificar quién accedió y cuándo. |
| US-010 | Como administrador local, quiero consultar el estado de mi licencia para conocer período, modo y límites. |
| US-011 | Como sistema, quiero pasar a modo solo consulta al vencer la licencia para conservar los datos y bloquear escritura. |
| US-012 | Como técnico, quiero ejecutar backup y restauración verificados para garantizar continuidad. |
| US-013 | Como técnico, quiero consultar el diagnóstico y los health checks para verificar el estado de los servicios. |
| US-014 | Como usuario, quiero recibir mensajes de error amigables y persistentes para comprender y corregir las operaciones. |
| US-015 | Como usuario, quiero recuperar mi contraseña de forma segura para restaurar el acceso. |
| US-016 | Como usuario, quiero que las sesiones revocadas se cierren en todas las pestañas para proteger la seguridad. |
| US-017 | Como administrador local, quiero completar la configuración inicial de la empresa para poder operar. |
| US-018 | Como sistema, quiero registrar un evento de auditoría en cada acción relevante para mantener trazabilidad. |

## 7. Requisitos funcionales

Convención de IDs: `FR-001-XXX`. Cada requisito tiene fuente (documento maestro), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 7.1 Instalación e identidad

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-001 | El repositorio permite desplegar una instalación con `compose.yaml` (frontend, backend, db, reverse-proxy) con imágenes versionadas, health checks, restart policy y red interna. | DOC-05, DOC-08, DOC-07 | P0 | Técnico |
| FR-001-002 | Al primer arranque, el backend genera `installation_uuid`, par de claves de instalación y solicitud de activación persistidos en volumen protegido. | DOC-07 | P0 | Sistema |
| FR-001-003 | La identidad de instalación persiste ante recreación de contenedores, reinicio de Docker o actualización de imagen. | DOC-07 | P0 | Sistema |
| FR-001-004 | El backend inicia aunque la licencia esté vencida, permitiendo consulta, renovación y diagnóstico. | DOC-07 | P0 | Sistema |
| FR-001-005 | Las variables obligatorias se validan al inicio y el servicio falla de forma segura si falta alguna. | DOC-08 | P0 | Sistema |

### 7.2 Inicialización y administrador

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-010 | Existe un asistente seguro de inicialización que crea la empresa inicial y el usuario administrador sin credenciales fijas. | DOC-07, DOC-01 | P0 | Administrador |
| FR-001-011 | El primer inicio de sesión del administrador exige cambio de contraseña obligatorio. | DOC-07 | P0 | Sistema |
| FR-001-012 | Las contraseñas se almacenan con Argon2id (o mecanismo aprobado) y cumplen una política de complejidad. | DOC-05, DOC-08 | P0 | Sistema |
| FR-001-013 | La recuperación de contraseña usa token de un solo uso con expiración y revocación. | DOC-05, DOC-08 | P1 | Usuario |

### 7.3 Autenticación y sesiones

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-020 | El backend autentica usuarios y emite access token de corta duración y refresh token seguro. | DOC-08 | P0 | Sistema |
| FR-001-021 | No se almacenan tokens de larga duración en localStorage; se usan cookies HttpOnly/Secure/SameSite para refresh (ADR-004). | DOC-08 | P0 | Sistema |
| FR-001-022 | Las sesiones son visibles, revocables y soportan cierre en todas las pestañas. | DOC-08 | P1 | Usuario |
| FR-001-023 | Existe rate limiting y protección contra fuerza bruta en login y recuperación. | DOC-05, DOC-08 | P0 | Sistema |
| FR-001-024 | MFA está preparado (habilitable) sin implementar la totalidad de flujos en esta Spec. | DOC-05, DOC-08 | P2 | Usuario |

### 7.4 Organización y multiempresa

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-030 | El modelo soporta Installation/Tenant, Company, Branch, Establishment, Warehouse y Location con aislamiento de datos. | DOC-03, DOC-07 | P0 | Sistema |
| FR-001-031 | El administrador local crea/configura sucursales, establecimientos y almacenes dentro de los límites de la licencia. | DOC-07 | P1 | Administrador |
| FR-001-032 | Toda operación pertenece a una empresa y respeta el alcance organizacional del usuario. | DOC-03, DOC-05 | P0 | Sistema |
| FR-001-033 | Las pruebas incluyen aislamiento negativo: un usuario de una empresa no accede a datos de otra. | DOC-01, DOC-05 | P0 | QA |

### 7.5 Roles, permisos y alcance

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-040 | El modelo de seguridad usa roles, permisos por acción (no solo CRUD) y alcance (empresa/sucursal/establecimiento/almacén). | DOC-03, DOC-08 | P0 | Sistema |
| FR-001-041 | El backend devuelve `allowed_actions` calculadas por registro; el frontend no deduce integridad referencial. | DOC-08 | P0 | Sistema |
| FR-001-042 | La navegación valida permisos antes de cargar datos sensibles; 403 se maneja siempre. | DOC-08 | P0 | Sistema |
| FR-001-043 | Existe segregación de funciones (SoD) básica y roles protegidos. | DOC-05, DOC-08 | P1 | Sistema |

### 7.6 Licencia local

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-050 | El backend verifica la firma de la licencia (Ed25519 o equivalente) y el `installation_id` en cada arranque y antes de aplicar una licencia nueva. | DOC-07 | P0 | Sistema |
| FR-001-051 | El sistema mantiene copia firmada de la licencia, período, derechos y última fecha confiable en almacenamiento persistente. | DOC-07 | P0 | Sistema |
| FR-001-052 | El sistema calcula el modo actual (FULL_ACCESS, RENEWAL_NOTICE, CRITICAL_RENEWAL_NOTICE, READ_ONLY, SECURITY_SUSPENSION) con fecha confiable en America/Caracas. | DOC-07 | P0 | Sistema |
| FR-001-053 | En modo READ_ONLY, el middleware de licencia bloquea escrituras (POST/PUT/PATCH/DELETE de negocio) antes de abrir transacción y antes de reservar correlativos. | DOC-07 | P0 | Sistema |
| FR-001-054 | El sistema permite cargar comprobante de renovación y consultar el estado en la pantalla Mi licencia (ruta completa). | DOC-07 | P0 | Administrador |
| FR-001-055 | La clave privada del propietario no reside en la instalación, en imágenes, en Git ni en variables distribuidas. | DOC-07 | P0 | Sistema |
| FR-001-056 | El reloj del navegador no decide el estado de la licencia; se usa fecha del servidor y última fecha confiable. | DOC-07 | P0 | Sistema |

### 7.7 Frontend base

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-060 | Existe App Shell con Sidebar, Topbar, PageLayout, PageHeader, Breadcrumbs y PageActions. | DOC-08 | P0 | Usuario |
| FR-001-061 | El router soporta rutas completas con estados loading, ready, empty, forbidden, not-found y error; cada alta/edición/detalle tiene URL propia. | DOC-08 | P0 | Sistema |
| FR-001-062 | Los formularios complejos se muestran en pantalla completa, no en modales; los modales solo para confirmaciones breves. | DOC-08 | P0 | Sistema |
| FR-001-063 | Toda acción asíncrona tiene loader dentro del botón, prevención de doble envío, mensaje de éxito/error persistente y request ID. | DOC-08 | P0 | Sistema |
| FR-001-064 | Los cambios sin guardar se detectan y confirman antes de abandonar la ruta. | DOC-08 | P0 | Sistema |
| FR-001-065 | DataTables sin scroll horizontal, búsqueda general, filtro de estado, paginación >10, acciones a la derecha. | DOC-08 | P0 | Sistema |
| FR-001-066 | La UI cumple WCAG 2.2 AA y responsive (móvil/tablet/laptop/desktop/zoom). | DOC-08 | P0 | Sistema |
| FR-001-067 | El contexto global de licencia muestra banner y bloquea escritura en READ_ONLY, con enlace a Mi licencia. | DOC-08 | P0 | Sistema |

### 7.8 Auditoría

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-070 | Se registran eventos de auditoría con tenant/company, usuario, acción, entidad, antes/después, request_id, sesión, fuente, motivo, evidencia y timestamp del servidor. | DOC-03, DOC-05 | P0 | Sistema |
| FR-001-071 | Los eventos de auditoría son inmutables (append-only). | DOC-09 (SNAT/2024/000121) | P0 | Sistema |
| FR-001-072 | Se registran: inicio exitoso/fallido, cierre, renovación, cambio de contraseña, recuperación, creación de usuario, cambio de rol/permiso/alcance, activación, cambio de licencia, intento bloqueado, error crítico y cambio de configuración. | DOC-01, DOC-07 | P0 | Sistema |

### 7.9 Operación

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-080 | Existen endpoints de health (liveness/readiness) para frontend, backend y DB. | DOC-05 | P0 | Técnico |
| FR-001-081 | Los logs son estructurados (JSON) con request ID, servicio, nivel y sin secretos. | DOC-05, DOC-08 | P0 | Sistema |
| FR-001-082 | Las migraciones (Alembic) son revisadas, reversibles cuando sea posible y con semilla idempotente separada de datos legales. | DOC-05, DOC-08 | P0 | Sistema |
| FR-001-083 | Existen scripts de backup y restauración verificados, con RPO ≤15 min y RTO ≤4 h como objetivo. | DOC-05, DOC-07 | P0 | Técnico |
| FR-001-084 | Existe diagnóstico de instalación que reporta estado de servicios, versión, identidad y licencia sin exponer secretos. | DOC-07 | P1 | Técnico |

### 7.10 Núcleo fiscal (preparación)

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-001-090 | Se prepara la estructura del núcleo fiscal (LegalSource, TaxRuleVersion, FiscalNumberSeries, ControlNumberBatch) versionada y separada de módulos administrativos, sin emisión real. | DOC-01, DOC-09, DOC-10 | P1 | Sistema |
| FR-001-091 | Toda regla fiscal/regulatoria se modela con fuente, vigencia y versión; nada hardcodeado. | DOC-09 | P0 | Sistema |

## 8. Requisitos no funcionales

| ID | Atributo | Objetivo |
|---|---|---|
| NFR-001-001 | Seguridad | Argon2id, cookies HttpOnly, CSRF, CORS restrictivo, TLS, headers (CSP, HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), rate limiting, secretos fuera del repo, usuario PostgreSQL restringido, SBOM |
| NFR-001-002 | Disponibilidad | 99,5% mensual objetivo inicial; ventanas planificadas documentadas |
| NFR-001-003 | Rendimiento | Listados <2 s p95; guardados transaccionales <3 s p95 (sin integraciones externas) |
| NFR-001-004 | Escalabilidad | Frontend/API horizontales; PostgreSQL optimizado; trabajos asíncronos diferidos |
| NFR-001-005 | Accesibilidad | WCAG 2.2 AA; teclado, foco, contraste, labels, errores asociados |
| NFR-001-006 | Responsive | 320/375/768/1024/1280/1440; zoom 125/150/200; sidebar expandido/colapsado |
| NFR-001-007 | Observabilidad | Logs JSON, request ID, correlation ID, métricas mínimas, alertas, retención y rotación |
| NFR-001-008 | Recuperación | Backups cifrados y verificados, restore probado, RPO ≤15 min, RTO ≤4 h, runbooks |
| NFR-001-009 | Mantenibilidad | Monolito modular, contratos explícitos, cobertura, migraciones, ADR |
| NFR-001-010 | Reproducibilidad | Imágenes versionadas, lockfiles, seeds idempotentes, configuración por ambiente |
| NFR-001-011 | Portabilidad | Contenedores, configuración por ambiente, almacenamiento desacoplado |
| NFR-001-012 | Compatibilidad | Navegadores modernos; sin dependencias `latest` en producción |
| NFR-001-013 | Privacidad | Minimización, permisos por campo, exportaciones auditadas, retención documental |
| NFR-001-014 | Auditoría | Registro automático e inmutable de eventos relevantes |
| NFR-001-015 | Soporte | Matriz L1/L2/L3/Fiscal/Infraestructura definida |

## 9. Casos límite

| ID | Caso límite | Comportamiento esperado |
|---|---|---|
| EDGE-01 | Licencia inválida (firma incorrecta) | SECURITY_SUSPENSION; no aplicar paquete; alerta |
| EDGE-02 | Licencia vencida (1 de mayo sin renovación) | READ_ONLY; consulta permitida; escritura bloqueada |
| EDGE-03 | Instalación duplicada / clonación | Detectar heartbeats simultáneos; marcar sospecha; requerir revisión |
| EDGE-04 | Reloj alterado / retroceso | Usar última fecha confiable; mantener la mayor; alertar |
| EDGE-05 | Base no disponible | Error amigable con request ID; no simular éxito |
| EDGE-06 | Migración fallida | Rollback documentado; no dejar esquema inconsistente |
| EDGE-07 | Seed reejecutado | Idempotente; no duplica ni sobrescribe |
| EDGE-08 | Token vencido | Refresh único; si falla, cierre seguro de sesión |
| EDGE-09 | Sesión revocada | Cierre en todas las pestañas |
| EDGE-10 | Usuario desactivado | Bloqueo en backend; sesión revocada |
| EDGE-11 | Empresa desactivada | Bloqueo de operaciones de esa empresa |
| EDGE-12 | Error de red | Estado offline/API unavailable; sin simular éxito |
| EDGE-13 | Restore en otro servidor | Reconciliar identidad/licencia; no retroceder período |
| EDGE-14 | Contenedor recreado | Identidad persistente conservada |
| EDGE-15 | Volumen ausente | Diagnóstico claro; fallo seguro |
| EDGE-16 | Variable obligatoria ausente | Falla segura al inicio |
| EDGE-17 | Contraseña insegura | Rechazo con política de contraseña |
| EDGE-18 | Acceso entre empresas | 403/aislamiento negativo |
| EDGE-19 | Doble envío / request duplicada | Idempotency-Key; sin duplicados |
| EDGE-20 | Conflicto concurrente | 409 + versión/ETag; no sobrescritura silenciosa |
| EDGE-21 | Backup antiguo restaurado | Reconciliar con volumen y autoridad; no retroceder período |
| EDGE-22 | Cambio de fecha en límite | Evaluación en login y en cada escritura |

## 10. Criterios de aceptación globales

- La instalación es reproducible desde `compose.yaml` + migraciones + seeds.
- No existen credenciales fijas ni secretos en el repositorio.
- La identidad de instalación persiste ante recreación de contenedores.
- La licencia se verifica por firma; solo el propietario la emite/renueva.
- El modo READ_ONLY bloquea toda escritura desde backend, jobs e integraciones, y conserva consulta/exportación/respaldo.
- El administrador local gestiona su empresa sin poder modificar la licencia.
- La navegación respeta permisos y alcance; el backend es autoridad.
- La auditoría registra los eventos obligatorios de forma inmutable.
- Los health checks y el diagnóstico reportan el estado real.
- Backup y restauración están verificados con evidencia.
- Los requisitos tienen identificador, fuente, dueño, criterio de aceptación y prueba.
- Se cumple el Estándar Maestro de Frontend (matriz FR-001..FR-040) y la Constitución.

---

## 11. Documentos fuente

| Ref | Documento |
|---|---|
| F1 | Documento Maestro de Requerimientos de INNOVA v1.1 (antecedente) |
| F2 | Manual Saint Enterprise Administrativo (referencia comparativa, no legal) |
| F3 | Compilación de Providencias Administrativas SENIAT |
| F4 | Expediente normativo SICA, SIGESAI y Decreto N.º 1.808 |
| F5 | Guías SENIAT, SICA y SIGESAI |
| F6 | Ley del IVA (G.O. 6.507 Ext.) |
| F7 | Ley de ISLR (G.O. 6.210 Ext.) |
| F8 | Ley de IGTF (G.O. 6.687 Ext.) |
| F9 | Código Orgánico Tributario (G.O. 6.507 Ext.) |
| F10 | Manuales oficiales SIGESAI (INSAI) |

## 12. Estado de la Spec

| Elemento | Estado |
|---|---|
| Identificación | ✔ |
| Problema y objetivos | ✔ |
| Fuera de alcance | ✔ |
| Actores | ✔ |
| Historias | ✔ |
| Requisitos funcionales | ✔ |
| Requisitos no funcionales | ✔ |
| Casos límite | ✔ |
| Criterios de aceptación | ✔ |
| Aprobación de la Spec | Pendiente — requiere `/speckit.analyze` y autorización expresa |
