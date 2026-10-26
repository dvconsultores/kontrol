# SPEC 003 · Delta — SHARED-CORE-P0-HARDENING-02 · DELEGATION CEILING

| Campo | Valor |
|---|---|
| Spec dueña | **003** (Usuarios / Roles / Alcance). Sin carpeta propia (OBS-04, sigue abierta): se aloja en `specs/001-fundacion/` como los deltas de la Spec 002 |
| Gap | P0 n.º 2 de OD-GSR-2 |
| Decisiones | OD-DEL-01..09 (encargo) · **OD-DEL-10** y **OD-DEL-11** (dueña, 2026-10-26, §4) · OD-AUTHRESET-07/08 = DEFERRED |
| HEAD de entrada | `464c913` |
| Evidencia | `evidence/delegation-ceiling/` |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| Estado | **IMPLEMENTED — CONVERGED** (2026-10-26) · MATERIAL OQ = 0 · implementación autorizada por el encargo «SHARED-CORE-P0-HARDENING-02 DELEGATION CEILING» |

> El encargo llegó truncado en «82. PRODUCTION … No production» (límite del mensaje). Las secciones siguientes (Git, DoD, informe,
> Final Analyze, prompt siguiente) se aplican como en el ciclo anterior y en el borrador de prompt que redactó Claude en `464c913`; no se
> pide a la dueña que las reenvíe.

## 1. Discover

### 1.1 AUTHORITY_MUTATION_SURFACE_MATRIX (medida en `464c913`)

| SURFACE_ID | Ruta / orden | Acción | Permiso del actor | Objetivo | Capacidades afectadas | Alcance afectado | Control backend actual | Control UI actual | Auditoría | Riesgo | Spec |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AS-01 | `POST /users/{id}/roles` | asignar rol | `roles:edit` + reautenticación | usuario del tenant | todas las del rol | `company_id` del cuerpo (nulo = todas las empresas donde opere) | tenant del objetivo; empresa del tenant; **sin techo** | RolesPage ofrece todos los roles | `ROLE_ASSIGNED` | **CRITICAL** (R1–R3) | 003 |
| AS-02 | `DELETE /users/{id}/roles/{role_id}` | quitar rol | `roles:edit` + reautenticación | usuario del tenant | todas las del rol | — | tenant; **sin protección del último administrador** | botón por asignación | `ROLE_REMOVED` | **HIGH** (R11) | 003 |
| AS-03 | `POST /roles` | crear rol | `roles:create` + reautenticación | catálogo (instalación o empresa) | las del cuerpo | `company_id` del rol | catálogo existente; empresa del tenant; **sin techo** | **no hay UI** | `ROLE_CREATED` | **CRITICAL** (R4, R9) | 003 |
| AS-04 | `POST /users` | crear usuario | `users:create` + reautenticación | usuario nuevo | ninguna (el cuerpo no admite roles) | ninguno | política de contraseña | UsuariosPage | `USER_CREATED` | bajo | 003 |
| AS-05 | `POST /users/{id}/mfa/reset` | restablecer MFA | `users:mfa_reset` + MFA + reautenticación | usuario del tenant | — | — | **techo ya existente** (`target_perms − actor_perms`) y no a sí mismo | UsuariosPage | `MFA_RESET_BY_ADMIN` | cubierto (Spec 002) | 002 |
| AS-06 | `POST /setup/initialize` | arranque | instalación sin inicializar | primer administrador | ADMIN (85 permisos) | instalación | solo una vez | asistente de instalación | sí | **contradice OD-DEL-06** (ADMIN = técnico + funcional) | 001/003 |
| AS-07 | `user_scopes` | alcance de empresa o sucursal | — | — | — | empresas o sucursales | **no hay ruta ni orden de producto**: solo guiones de `qa/` | ninguna | — | sin superficie | 003 |
| AS-08 | edición o borrado de roles; activación o desactivación de usuarios | — | — | — | — | — | **no existen** en la API (los permisos `users:deactivate` y `roles:edit` existen en el catálogo) | — | — | sin superficie | 003 |
| AS-09 | políticas de aprobación (`aprobaciones:configure`) | define aprobadores por rol | `aprobaciones:configure` | política | autoridad de aprobación (negocio) | empresa | Spec 045 | sí | sí | SoD de proceso (fuera de este delta) | 045 |
| AS-10 | `mfa_breakglass`, `password_breakglass` (CLI local) | recuperación | acceso al servidor | usuario | — | — | confirmación y auditoría | — | sí | no concede capacidades | 002 |

UNINVENTORIED_AUTHORITY_MUTATION_SURFACES = 0. No se encontraron escrituras directas del ORM sobre `user_roles`, `role_permissions` o
`user_scopes` fuera de `service.py` (asignar y quitar), `create_role` y `setup` (búsqueda de `UserRole(`, `RolePermission(`, `UserScope(`,
`delete(UserRole…)` en `app/` y `scripts/`).

### 1.2 Modelo de autoridad medido

- **Permisos efectivos:**
  - `get_user_permissions(user)` es la unión de los permisos de todos sus roles.
  - `require_permission` **no tiene en cuenta la empresa del rol**: un permiso concedido para la empresa A vale en todas. Es el hallazgo
    OD-DEL-11; queda como deuda aparte.
- **Acceso a empresas:**
  - lo decide `user_scopes` (`accessible_company_ids`);
  - sin filas, el usuario accede a todas las empresas del tenant.
- **Asignación:** `user_roles.company_id` nulo significa «el rol vale en cualquier empresa donde el usuario opere».
- **ADMIN:**
  - lo crea `setup` con **los 85 permisos** del catálogo, técnicos y funcionales;
  - es protegido y no se puede crear por API.
- **Catálogo de roles:** los roles personalizados con `company_id` nulo son de **toda la instalación**, no de un tenant (deuda
  ROLE-CATALOG-INSTALLATION-WIDE).
- **Frescura:** los permisos se leen de la BD en cada petición (`require_permission`), sin caché. Quitar un rol tiene efecto en la
  petición siguiente (AUTHORITY_REVOCATION_EFFECTIVE por diseño).

## 2. Reproducción (`evidence/delegation-ceiling/reproduccion.txt`)

**Actor:** rol `R_GESTOR_ROLES` = `roles:edit`, `roles:create`, `users:view`. Entra con MFA real.

| Caso | Resultado actual | Esperado |
|---|---|---|
| R1 autoasignarse ADMIN | **200** | 403 `SELF_ESCALATION_FORBIDDEN` |
| R2 autoasignarse `users:mfa_reset` | **200** | 403 `SELF_ESCALATION_FORBIDDEN` |
| R3 asignar a otro un rol con `users:mfa_reset` | **200** | 403 `AUTHORITY_CEILING_EXCEEDED` |
| R4 crear un rol con `users:mfa_reset` | **201** | 403 `AUTHORITY_CEILING_EXCEEDED` |
| R9 crear un rol «sombra» con los 85 permisos de ADMIN | **201** | 403 `AUTHORITY_CEILING_EXCEEDED` |
| R7 asignar con una empresa de otro tenant | 404 `COMPANY_NOT_FOUND` | ya bloqueado |
| R11 quitar ADMIN al administrador inicial | **200** | 409 `LAST_SECURITY_ADMIN_REQUIRED`, si deja al tenant sin administrador de seguridad |

**R5 (editar un rol), R8 (ampliar el alcance propio) y R10 (el administrador técnico fabrica autoridad):**
- no hay ruta de edición de roles ni de alcances;
- R10 es estructural: ADMIN ya tiene toda la autoridad funcional (AS-06).

**R6 (empresa A frente a B del mismo tenant) y R12 (carrera):** se cubren en las pruebas en rojo, con un mundo de dos empresas y con
hilos sobre PostgreSQL.

Gravedad: **CRITICAL**. Cualquier poseedor de `roles:edit` se convierte en ADMIN (R1).

## 3. Causa raíz (medida)

1. La autorización de las rutas que conceden autoridad es local y gruesa: solo `roles:edit` o `roles:create`. Ningún servicio compara lo
   que se concede con lo que posee el actor.
2. No existe una «autoridad efectiva» canónica (capacidad × alcance).
3. No hay invariante de último administrador.
4. ADMIN mezcla autoridad técnica y funcional.
5. La UI ofrece cualquier rol, aunque la UI no es la autoridad (P-05).

## 4. Decisiones aplicadas

| OD | Contenido |
|---|---|
| OD-DEL-01 | Subconjunto exacto de capacidades |
| OD-DEL-02 | Alcance igual o más estrecho; nunca entre tenants |
| OD-DEL-03 | Sin autoescalada; se puede renunciar respetando el último administrador |
| OD-DEL-04 | Crear o editar roles pasa por el mismo techo; no se edita un rol de autoridad superior |
| OD-DEL-05 | Asignar ADMIN exige ser ADMIN legítimo en el tenant con alcance de tenant, MFA, reautenticación y auditoría |
| OD-DEL-06 | El administrador técnico no fabrica autoridad funcional |
| OD-DEL-07 | Último administrador de seguridad por capacidades, no por nombre |
| OD-DEL-08 | Cadenas solo con autoridad poseída en el momento de la acción |
| OD-DEL-09 | Techo por capacidad y alcance exactos; la clase MFA no sirve para decidir |
| **OD-DEL-10** (dueña, 2026-10-26) | **Separar técnico y funcional.** ADMIN conserva solo las capacidades técnicas y de seguridad (§7.1). Se crea el rol protegido **FUNCIONAL_COMPLETO** con las capacidades de negocio. La migración lo asigna, auditado, a quienes hoy tienen ADMIN, para no romper instalaciones. Las instalaciones nuevas lo conceden de forma explícita en el arranque |
| **OD-DEL-11** (dueña, 2026-10-26) | El techo se aplica sobre el alcance **declarado** (empresa de la asignación ∩ `user_scopes`). Que la autorización de cada ruta acote por empresa es la deuda **ROLE-COMPANY-SCOPE-NOT-ENFORCED** (HIGH), con delta propio |
| **OD-DEL-12** (dueña, 2026-10-26) | **Administrador inicial con alcance de tenant.** Hallazgo medido: `setup` asigna ADMIN con la empresa inicial, no con nulo. Con el techo sobre el alcance declarado (OD-DEL-11), en un tenant con varias empresas nadie podría delegar para las demás (bloqueo). Decisión: `setup` asigna ADMIN y FUNCIONAL_COMPLETO con `company_id` nulo. La migración `0060` pasa a nulo la asignación ADMIN del administrador inicial (`users.created_by = 'setup'`), con auditoría. No amplía la autoridad efectiva de hoy: los permisos ya ignoran la empresa (OD-DEL-11) |
| OD-AUTHRESET-07/08 | DEFERRED: no se absorben |

## 5. Modelo de dominio — EFFECTIVE_AUTHORITY (módulo nuevo `identity_access/authority.py`)

| Función | Contrato |
|---|---|
| `effective_capabilities(db, user) -> set[str]` | Unión de `recurso:accion` de los roles **ACTIVE** del usuario, si el usuario está ACTIVE (si no, vacío) |
| `effective_scope(db, user, capability) -> Alcance` | Empresas donde el usuario tiene la capacidad: para cada asignación de un rol que la contiene, si `company_id` es nulo, todas sus empresas accesibles (`accessible_company_ids`); si no, `{company_id}` ∩ accesibles. Sin la capacidad: vacío |
| `granted_scope(db, target, company_id) -> set[str]` | Empresas que concede una asignación: `{company_id}` si viene; si es nulo, las accesibles del objetivo |
| `check_can_assign(db, actor, target, role, company_id)` | En este orden: rol con empresa de otro tenant → 404 `ROLE_NOT_FOUND`; rol no ACTIVE → 409 `ROLE_INACTIVE`; alguna capacidad del rol fuera de las del actor → 403 `AUTHORITY_CEILING_EXCEEDED` (`SELF_ESCALATION_FORBIDDEN` si el objetivo es el actor); rol **protegido** (ADMIN, FUNCIONAL_COMPLETO) que el actor no tiene asignado con un alcance ⊇ `granted_scope` → 403 `AUTHORITY_CEILING_EXCEEDED` (OD-DEL-05); `granted_scope` ⊄ `effective_scope(actor, c)` para alguna capacidad `c` del rol → 403 `CROSS_SCOPE_DELEGATION_FORBIDDEN` (`SELF_ESCALATION_FORBIDDEN` si el objetivo es el actor) |
| `check_can_create_role(db, actor, permissions, company_id)` | Lanza `AUTHORITY_CEILING_EXCEEDED` si `permissions` ⊄ capacidades del actor, o `CROSS_SCOPE_DELEGATION_FORBIDDEN` si `company_id` está fuera de `effective_scope(actor, c)` para alguna `c`; un rol de toda la instalación exige que el actor tenga cada `c` con alcance de todo el tenant |
| `check_can_manage_assignment(db, actor, target, role, company_id)` (quitar; edición futura) | Capacidades del rol ⊆ las del actor, si no 403 `AUTHORITY_CEILING_EXCEEDED`. El alcance de la asignación ⊆ el del actor, si no 403 `TARGET_OUT_OF_SCOPE`. OD-DEL-04: no se gestiona desde abajo. La renuncia propia la cumple siempre |
| `is_security_admin(db, user) -> bool` | El usuario está ACTIVE y tiene `SECURITY_ADMIN_CAPABILITIES` = {`users:create`, `roles:edit`, `users:mfa_reset`} ⊆ `effective_capabilities`, con cualquier alcance. Es conservador a propósito: `setup` asigna ADMIN **con la empresa inicial** (no con nulo) y, por OD-DEL-11, hoy un permiso vale en todas las empresas; exigir alcance de tenant dejaría sin protección al administrador inicial de un tenant con varias empresas |
| `would_remove_last_security_admin(db, tenant_id, *, user_id, role_id) -> bool` | Verdadero si el usuario es administrador de seguridad **antes** y, sin esa asignación, el tenant se queda con **cero** administradores de seguridad |

**Reglas de uso:**
- Las rutas y servicios que conceden o quitan autoridad (`assign_role_to_user`, `remove_role_from_user`, `create_role`) llaman a estas
  funciones **dentro de la transacción y antes del commit**.
- En esos tres servicios, `actor` pasa a ser **obligatorio** (`str`, el id del usuario). Siempre se aplica el techo: no hay rama «sin actor»
  que lo salte. Los arranques del sistema (`setup`, migración) escriben por ORM y no usan esos servicios.
- La denegación se audita (§11) y se confirma antes de lanzar el error.
- No hay implementaciones paralelas en las rutas (INV-DEL-10).
- Quitar un rol exige `check_can_manage_role`: no se quita un rol de autoridad superior a la propia.
- La renuncia propia está permitida, sujeta a la protección del último administrador.

### 5.1 Invariantes INV-DEL-01..12

Los invariantes del encargo, con estos controles:
- **INV-DEL-12 (concurrencia):** en PostgreSQL, las mutaciones de autoridad de un tenant se serializan con `pg_advisory_xact_lock(7003041, hashtext(:tenant_id))`, tomado **antes de leer** el estado de autoridad. SQLite serializa las escrituras.
- **INV-DEL-08 (último administrador):** se evalúa tras tomar el bloqueo y antes del commit, así que dos administradores no pueden quitarse el uno al otro a la vez.

## 6. Modelo de proceso

| Proceso | Actor | Precondiciones | Validación (backend) | Resultado | Auditoría | Error |
|---|---|---|---|---|---|---|
| Asignar rol | `roles:edit` + MFA + reautenticación | objetivo del tenant; rol ACTIVE del catálogo visible para el tenant | `check_can_assign` | fila en `user_roles`; revocación de sesiones si cambia la clase MFA | `ROLE_ASSIGNED` / `AUTHORITY_DELEGATION_DENIED` | 403 / 404 / 409 |
| Quitar rol (incluida la renuncia) | `roles:edit` + MFA + reautenticación | asignación existente | `check_can_manage_role` + último administrador | fila borrada; idem | `ROLE_REMOVED` / `LAST_ADMIN_OPERATION_DENIED` / `AUTHORITY_DELEGATION_DENIED` | 403 / 409 |
| Crear rol | `roles:create` + MFA + reautenticación | permisos del catálogo | `check_can_create_role` | rol no protegido | `ROLE_CREATED` / `AUTHORITY_DELEGATION_DENIED` | 403 / 409 / 422 |
| Arranque de la instalación | instalación nueva | — | — | usuario inicial con **ADMIN + FUNCIONAL_COMPLETO** (concesión explícita y auditada) | `ROLE_ASSIGNED` ×2 | — |

Crear usuario, editar o borrar roles, desactivar usuarios y gestionar alcances: no existen como superficie (AS-04, AS-07, AS-08). El
techo y el último administrador se aplicarán a esas operaciones cuando existan, por las mismas funciones.

## 7. Modelo de datos — migración `0060_spec003_admin_split` (OD-DEL-10)

### 7.1 Capacidades

| Rol | Capacidades |
|---|---|
| **TÉCNICAS** (ADMIN) | `dashboard:view`, `organization:*` (7), `users:*` (6), `roles:*` (3), `audit:view`, `license:*` (4), `notificaciones:configure`, `tareas:configure`, `documentos:manage_types` |
| **FUNCIONALES** (FUNCIONAL_COMPLETO) | Todas las demás del catálogo, incluida `aprobaciones:configure`, que da forma a la autoridad de aprobación |

Las listas quedan como constantes en `authority.py` (`TECHNICAL_CAPABILITIES`), las usa `setup` y las prueba la migración.

### 7.2 Migración

| Paso | Upgrade | Downgrade |
|---|---|---|
| 0 | OD-DEL-12: las asignaciones ADMIN con empresa de los usuarios con `created_by = 'setup'` pasan a `company_id` nulo; un evento `USER_SCOPE_CHANGED` por fila (motivo `OD-DEL-12`, `before`/`after` con la empresa) | Se conserva (la empresa anterior queda en la auditoría; revertirla no es seguro sin saber si se concedió algo después) |
| 1 | Crear el rol `FUNCIONAL_COMPLETO` (protegido, `company_id` nulo, ACTIVE) si no existe | Devolver a ADMIN las capacidades funcionales |
| 2 | Moverle las capacidades funcionales que hoy tiene ADMIN (`role_permissions`) | Borrar las asignaciones de FUNCIONAL_COMPLETO y el rol |
| 3 | Asignar FUNCIONAL_COMPLETO, con la misma `company_id`, a cada usuario que tenga ADMIN | — |
| 4 | Un evento de auditoría por asignación (`ROLE_ASSIGNED`, motivo `OD-DEL-10`) | — |

Es idempotente y reversible, con una sola cabeza. Se prueba en instalación limpia, en actualización con datos y en downgrade, sobre
PostgreSQL.

`setup` crea los dos roles y asigna ambos al usuario inicial con `company_id` nulo (OD-DEL-12).

## 8. Modelo de seguridad

| Amenaza | Control | Prueba |
|---|---|---|
| Autoescalada (rol, capacidad o alcance) | `check_can_assign` con el objetivo igual al actor | DC-S01..S03 |
| Escalada por rol | Subconjunto exacto | DC-A01..A03 |
| Creación de un rol sombra | `check_can_create_role` | DC-C01..C03 |
| Edición de un rol (futura) | `check_can_manage_role` | DC-M01 (quitar un rol superior) |
| Rol ADMIN protegido | Exige ADMIN de tenant | DC-P01..P03 |
| Administrador técnico (OD-DEL-06) | División de ADMIN (OD-DEL-10): ADMIN sin FUNCIONAL_COMPLETO no tiene ni puede delegar autoridad funcional | DC-T01..T02, migración |
| Cadenas | Evaluación en el momento de la acción | DC-H01 (pierde la capacidad y ya no puede delegarla) |
| Alcance | `granted_scope` ⊆ `effective_scope` | DC-E01..E03 |
| Entre tenants (IDOR/BOLA) | Objetivo, rol y empresa del tenant | DC-X01..X02 |
| Último administrador | `would_remove_last_security_admin` | DC-L01..L03 |
| Carrera | Bloqueo consultivo por tenant | DC-R01 (PostgreSQL, hilos) |
| Asignación masiva o campos ocultos | Esquemas con `extra="forbid"` | DC-V01 |
| Bypass de la UI | Toda la decisión en el backend | DC-* por API |
| Omisión de auditoría | Denegación y operación auditadas | DC-AU01 |

## 9. Contrato de API

| Ruta | Antes | Después |
|---|---|---|
| `POST /users/{id}/roles` `{role_id, company_id?}` | 200 / 404 / 409 | 200 o **403** `AUTHORITY_CEILING_EXCEEDED` / `SELF_ESCALATION_FORBIDDEN` / `CROSS_SCOPE_DELEGATION_FORBIDDEN`, 404 `ROLE_NOT_FOUND` / `COMPANY_NOT_FOUND`, 409 `ROLE_ALREADY_ASSIGNED` / `ROLE_INACTIVE`; `extra="forbid"` |
| `DELETE /users/{id}/roles/{role_id}` | 200 / 404 | 200 o **409** `LAST_SECURITY_ADMIN_REQUIRED`, **403** `AUTHORITY_CEILING_EXCEEDED` / `TARGET_OUT_OF_SCOPE`, 404 |
| `POST /roles` | 201 / 409 / 422 | 201 o **403** `AUTHORITY_CEILING_EXCEEDED` / `CROSS_SCOPE_DELEGATION_FORBIDDEN`, 409, 422 |
| `GET /roles` | `items` | Cada rol añade `delegable: bool` y `motivo: str \| null` (`AUTHORITY_CEILING_EXCEEDED`), calculados para el actor (tenant y empresa por defecto) |

Ninguna denegación de seguridad es 500. Las respuestas de error usan el envoltorio común `{code, message, request_id}`.

## 10. Modelo UX/UI

Detalle en `evidence/delegation-ceiling/screen-form-completeness.md`, al cierre.

| Pantalla | Cambios |
|---|---|
| **Roles** (`/seguridad/roles`) | Cada rol muestra sus capacidades (lista legible) y si el actor puede delegarlo. El selector de asignación solo ofrece roles delegables; los no delegables se muestran deshabilitados con el motivo. Selector de empresa opcional («Todas las empresas en las que opera» o una concreta). Mensajes para cada código de §9; la denegación del último administrador lo explica. Quitar un rol pide confirmación |
| **Usuarios** | Sin cambios funcionales: ya muestra los roles y el estado MFA |

La creación de roles por UI no existe y queda como FUTURE_SPEC (ROLE-CREATE-UI-MISSING). La API ya aplica el techo.

## 11. Auditoría

| Evento | Cuándo | Contenido |
|---|---|---|
| `ROLE_ASSIGNED`, `ROLE_REMOVED`, `ROLE_CREATED` | Existentes | Añaden `company_id` y el resumen de capacidades del rol |
| `AUTHORITY_DELEGATION_DENIED` | Denegación de asignar, quitar o crear | `reason` = código; `evidence` = {`role_code`, `capabilities_excedidas` (lista de `recurso:accion`), `company_id`} |
| `LAST_ADMIN_OPERATION_DENIED` | Protección del último administrador | — |

Nunca incluyen secretos.

## 12. Concurrencia

- Hay bloqueo consultivo por tenant en las tres operaciones.
- La unicidad de `(user_id, role_id)` ya existe por comprobación previa. Se añade la protección del bloqueo.
- Dos quitas cruzadas del último administrador: la segunda ve el estado tras la primera y recibe 409.

## 13. Gobierno (`requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, releído)

| Requisito | Aplicación | Estado |
|---|---|---|
| RNF-GOV-012 mínimo privilegio | Techo por capacidad y alcance | COVERED (la aplicación del alcance de empresa en cada ruta es OD-DEL-11, deuda) |
| P-05 / RNF-GOV-006 autoridad en backend | `authority.py` en el servicio | COVERED |
| GOV-CTL-004 el administrador técnico no fabrica autoridad | OD-DEL-10 | COVERED |
| GOV-ORG-005 separar la administración técnica | ADMIN técnico frente a FUNCIONAL_COMPLETO | COVERED en lo técnico; la SoD configurable de Gobierno es FUTURE_GOV_SPEC |
| GOV-CTL-001 matriz SoD / GOV-PROC-017 conflictos SoD de proceso | — | FUTURE_GOV_SPEC (SoD de proceso; DELEGATION_SOD_COMPLETE ≠ GLOBAL_SOD) |
| GOV-ORG-004 delegaciones versionadas con acto soporte y vigencia | — | FUTURE_GOV_SPEC (dominio de Gobierno) |
| RNF-GOV-005 / GOV-CTL-002 / GOV-CTL-003 auditoría | §11 | COVERED (append-only = FUTURE_GOV_SPEC) |
| E2E-06 hostil multi-ente | DC-X, E2E-DEL-05 | COVERED en el núcleo; Gobierno lo hereda |
| E2E-07 hostil SoD | DC-S/A/T, E2E-DEL-02/03/08 | COVERED para la SoD de delegación |
| RNF-GOV-019 migraciones | `0060` | COVERED |
| RNF-GOV-020 QA | §14 | COVERED |
| RNF-GOV-014 accesibilidad | §10 | COVERED |

Investigación normativa: NOT_APPLICABLE. Es seguridad del núcleo compartido; no hay una norma venezolana que fije el modelo RBAC. Las
decisiones son OWNER_DECISION y PROJECT_REQUIREMENT.

## 14. Tareas

Todas: SECURITY_SENSITIVE = sí · EGRESS_SAFE = sí · RETRY_MAX = 2 · código y pruebas de DeepSeek; diseño y auditoría de Claude.

| Tarea | Contenido | MODEL | FILES |
|---|---|---|---|
| TD-A1 | Pruebas en rojo del techo (DC-*) | v4-pro | `tests/test_delegation_ceiling.py` |
| TD-A2 | Pruebas en rojo de la migración `0060` | v4-pro | `tests/test_spec003_migration_0060.py` |
| TD-1 | Migración `0060` y `setup` (división de ADMIN) | v4-pro | `alembic/versions/0060_…`, `setup/api.py` |
| TD-2 | `authority.py` e integración en los servicios (asignar, quitar, crear rol) con bloqueo y auditoría | v4-pro | `identity_access/authority.py`, `service.py` |
| TD-3 | API: errores, `extra="forbid"`, `delegable`/`motivo` en `GET /roles` | v4-flash | `identity_access/api.py` |
| TD-4 | Frontend Roles y vitest | v4-pro | `modules/seguridad/roles/*` |
| TD-5 | Pruebas existentes afectadas por la división de ADMIN | v4-flash | las que se midan |
| TD-6 | E2E-DEL-01..10 | v4-pro | `e2e/delegation-ceiling.spec.ts` |
| TD-7 | Documentación (contratos, ADR, matriz de roles) | v4-flash | `contracts/api-contracts.md`, ADR |
| TD-8 | Mutaciones (Claude, herramienta local) | — | — |

## 15. Gate de la Constitución

P1 · P2 (encargo) · P3 · P6 (backend) · P7 · P10 · P11 · P12 (OD-DEL-10/11 y ADR) · P13 (todo en una transacción) · P21 (los dos motores) ·
P24 y P26 (migración) · P25 (bloqueo en la BD) · P27 (mutaciones): **PASS**.

BLOCKER = 0 · CRITICAL = 0 de diseño (el defecto CRITICAL es lo que se corrige) · CONTRADICTIONS = 0 · MATERIAL OQ = 0 (OD-DEL-10/11
resueltas por la dueña el 2026-10-26) · UNKNOWN = 0.

## 16. Deudas registradas (no absorbidas)

| DEBT_ID | Severidad | Siguiente acción |
|---|---|---|
| ROLE-COMPANY-SCOPE-NOT-ENFORCED | **HIGH** | `require_permission` debe acotar por la empresa de la asignación (OD-DEL-11); delta propio de la Spec 003 |
| ROLE-CATALOG-INSTALLATION-WIDE | MEDIUM | Los roles personalizados con `company_id` nulo son de toda la instalación (visibles y asignables desde otros tenants; el techo impide escalar con ellos) |
| ROLE-CREATE-UI-MISSING | LOW | Pantalla de alta y edición de roles con el techo (la API existe) |
| USER-LIFECYCLE-API-MISSING | LOW | Desactivar o reactivar usuarios: cuando exista, pasará por `would_remove_last_security_admin` |
| SHELL-SIDEBAR-NOT-RESPONSIVE (ya registrada, Spec 001) | MEDIUM | Se vuelve a observar en Roles. Con el menú desplegado, la cabecera desborda a 320 px (354 px). Con el menú plegado no hay scroll horizontal, pero `main` queda en unos 100 px y el contenido se recorta. La E2E-DEL-07 mide con el menú plegado, igual que la E2E MFA-14 |
| ROLES-FORM-FIXED-WIDTHS | LOW | Los selectores de la pantalla Roles tienen ancho fijo (`w-56` y `w-64`). Se corrigen cuando el shell deje espacio a 320 px (depende de SHELL-SIDEBAR-NOT-RESPONSIVE) |
| OBS-DEL-E2E-401-PARALELO | LOW (observación) | Un 401 en Firefox bajo carga paralela en E2E-DEL-03, en una corrida intermedia. No se reprodujo aislado (8 de 8 con 403) ni en la corrida final (21 de 21). Las aserciones ya llevan el cuerpo de la respuesta, así que si vuelve se podrá atribuir |
| APPROVAL-CANCEL-WITHOUT-REQUESTER-CHECK y demás deudas de §18 del encargo | — | Sin cambios |

## 17. Ejecución y evidencia (2026-10-26)

**Reproducción** (`evidence/delegation-ceiling/reproduccion.txt`): R1, R2, R3, R4, R9 y R11, antes 200/201, responden ahora 403. R7 sigue en 404.

**Defecto adicional corregido:** renunciar a un rol propio daba 500 (`ObjectDeletedError`). Ahora se lee la fila antes de borrarla.

**Pruebas nuevas:**
- `test_delegation_ceiling.py` (DC): 19 pruebas.
- `test_delegation_ceiling_roles.py` (DCR): 10.
- `test_delegation_scope.py` (DSC): 9.
- `test_delegation_last_admin.py` (DLA): 6, tres de ellas de carrera en PostgreSQL.
- `test_spec003_migration_0060.py`: 5.
- `RolesPage.test.tsx`: 7.
- `e2e/delegation-ceiling.spec.ts`: 7 × 3 motores.

**Pruebas existentes ajustadas a la división de ADMIN:**
- Los mundos «con todo» reciben FUNCIONAL_COMPLETO.
- La cabeza de Alembic pasa a `0060`.
- En las migraciones 0024, 0043 y 0047, los permisos se buscan en ADMIN ∪ FUNCIONAL_COMPLETO.

**Mutaciones:** 21 de 21 muertas (`mutaciones.md`).

**Certificaciones backend con analizador:**
- PostgreSQL: 3475 pasan, 0 fallan, 18 omitidas.
- SQLite: 2411 pasan, 0 fallan, 1082 omitidas.
- Anomalía NORMAL en ambas.

**E2E del ciclo:** 21 de 21 (Chromium, Firefox y WebKit), limpieza LIMPIA.

**E2E canónica completa:** 320 de 320, limpieza LIMPIA. Para llegar a ella se ajustó el arnés de QA:
- Los mundos «con todo» reciben FUNCIONAL_COMPLETO.
- Se añadió `admintenant`, administrador de QA de todo el tenant.
- El `admin` E2E, con alcance declarado solo en D1, ya no puede conceder autoridad sobre D2: es el techo funcionando (OD-DEL-02/11).

**Frontend:** vitest 563 de 563, `tsc`, `eslint` y build en verde.

**Observación del ciclo anterior:** el inventario de `ejecutarPython` ya estaba en rojo en `464c913` (faltaba `password-reset.spec.ts`). Se corrige aquí.

**Gates:** `screen-form-completeness.md` PASS.

**Orquestación:** `orchestration.md`.

DELEGATION_SOD_COMPLETE = 1 · GLOBAL_SOD = FUTURE_GOV_SPEC · AUTHORITY_REVOCATION_EFFECTIVE = 1 (E2E-DEL-06) · LAST_ADMIN_RACE = BLOCKED ·
DELEGATION_RACE_ESCALATION = BLOCKED · TECH_ADMIN_FUNCTIONAL_AUTHORITY = BLOCKED · REAL_SAFARI_NOT_MEASURED · PRODUCTION_TOUCHED = 0.
