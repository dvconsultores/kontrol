# SPEC 003 · Delta — SHARED-CORE-P0-HARDENING-02B · COMPANY-SCOPE AUTHORIZATION ENFORCEMENT

| Campo | Valor |
|---|---|
| Spec dueña | **003** (Usuarios / Roles / Alcance); afecta a las rutas de empresa de todas las Specs de negocio (se descubren en §1) |
| Deuda que cierra | **ROLE-COMPANY-SCOPE-NOT-ENFORCED** (P0, reclasificada por la dueña: OD-DEL-11 corregida) |
| HEAD de entrada | `021c1c6` (develop = origin/develop) |
| Evidencia | `evidence/company-scope-authorization/` |
| Decisiones vigentes | OD-DEL-10 ratificada (ADMIN técnico / FUNCIONAL_COMPLETO de negocio; la migración 0060 se acepta como compatibilidad) · OD-DEL-12 ratificada con restricciones (solo el arranque explícito recibe alcance de tenant; auditado, con MFA, sin replicarse en silencio) · OD-DEL-11 **corregida**: no es una excepción aceptada, es P0 de este ciclo |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 (este ciclo es núcleo compartido) |
| Estado | **IMPLEMENTED — CONVERGED — REQUIRED_SUITE_INVENTORY_COMPLETE = 1** (2026-10-27; diseño autorizado por el encargo «SHARED-CORE-P0-HARDENING-02B») |

> El encargo llegó truncado en «96. NEXT PROGRAM ORDER» (límite del mensaje). El orden del programa siguiente se toma del ciclo anterior
> (4 America/Caracas, 5 catálogo de auditoría, 6 parámetros no declarados → 422, 7 copia y restauración, 8 aislamiento de ente de Gobierno).

## 1. Discover (medido en `021c1c6`)

### 1.1 Modelo de autorización actual

- **Acceso a empresas:** `company_context.resolve_company`. La cabecera `X-Kontrol-Company` **selecciona** y el servidor valida contra
  `user_scopes` (`accessible_company_ids`; sin filas, todas las del tenant). Una empresa inaccesible o ajena responde 404 sin enumerar.
- **Capacidades:** `require_permission(resource, action)` es la unión de los permisos de todos los roles del usuario y **ignora**
  `UserRole.company_id`.
- **Hueco:** quien tiene la capacidad X solo en D1 (rol asignado con `company_id = D1`) y acceso a D2 (sin `user_scopes`, o con D2
  declarada) ejerce X en D2.
- **Lo que no cambia:** el aislamiento del dato por empresa (ARCH-MC-001 / ADR-D0-014: cada consulta filtra por `ctx.company_id`) ya está
  probado por `test_mc_*`. El hueco es la **autoridad** por empresa, no el filtrado del dato.

### 1.2 COMPANY_SCOPE_ENFORCEMENT_MATRIX

Inventario mecánico de las 552 rutas (`evidence/.../rutas.json`, generado del árbol de dependencias de FastAPI).

| Grupo | Rutas | Control actual | Riesgo | Corrección |
|---|---|---|---|---|
| G1 · empresa + permiso declarado | 360 | contexto (acceso) + permiso de tenant | **P0**: la capacidad no se acota a la empresa | **C1** central: en el contexto de empresa, cada permiso declarado por la ruta se exige en `ctx.company_id` |
| G2 · empresa sin permiso declarado | 120 (lecturas de catálogo y listas de purchasing, inventory, sales, treasury, notifications, fiscal, regulatory, master_data, reporting y organization; y lo propio de notifications) | solo acceso (`user_scopes`) | no hay capacidad que acotar: la autoridad de lectura es el acceso a la empresa (ARCH-MC-001) | ninguna; se prueba que el acceso sigue mandando (DSC-R) |
| G3 · aprobaciones sin contexto | 3 (`/approvals/steps/{id}/approve\|reject\|return`) | permiso de tenant + elegibilidad congelada; `resolve_actors` (ROLE) toma a cualquiera con el rol, sin mirar la empresa de la asignación | **P0**: un aprobador con el rol solo en D1 aprueba en D2 | **C2**: elegibles por rol solo si la asignación cubre la empresa de la solicitud; al decidir, `aprobaciones:approve` en esa empresa |
| G4 · auditoría | 1 (`GET /audit/events`) | solo tenant | **ALTA**: quien audita D1 lee la bitácora de D2 (importes, ids, actores) | **C3**: filas de empresas en el alcance de `audit:view`; las filas sin empresa solo con alcance de tenant |
| G5 · catálogos de instalación o tenant que afectan a todas las empresas | 11 (`fiscal/legal-sources`, `fiscal/tax-rule-versions` [4]; `homologation/*` [6]; `POST /organization/companies` [1]) | permiso de tenant | **ALTA**: autoridad acotada a D1 cambia reglas de todas las empresas o crea empresas | **C4**: dependencia `require_tenant_permission`, que exige la capacidad con alcance de **todo** el tenant |
| G6 · identidad (usuarios, roles, MFA) | 7 | techo de delegación (ciclo anterior) | cubierto | sin cambios |
| G7 · licencia y sistema | 18 | permiso técnico de instalación | sin dato de empresa | sin cambios |
| G8 · `documentos/salud/almacenamiento`, `approvals/process-types` | 2 | lectura técnica o de metadatos, sin dato de empresa | bajo | sin cambios |

UNINVENTORIED_COMPANY_SCOPED_SURFACES = 0: toda ruta HTTP está en un grupo. Hay además superficies que no son rutas:
- **trabajos de fondo** (`company_context_for`): abren su contexto de forma explícita y los inicia una ruta que ya pasa C1;
- **guiones de QA**: solo QA.

### 1.3 Reproducción (`evidence/company-scope-authorization/reproduccion.txt`)

**Mundo:** tenant DEMO con D1 y D2. Rol `R_SOLO_D1` (`maestros:view|create|deactivate`, `reportes:export`) asignado con
`company_id = D1`; el actor no tiene `user_scopes`, así que alcanza D1 y D2. Entra con MFA real.

| Caso | Petición | Actual | Esperado |
|---|---|---|---|
| S01 | crear unidad en D1 | 200 | 200 |
| S02 | listar unidades de D2 (`maestros:view`) | **200** | 403 `COMPANY_SCOPE_FORBIDDEN` |
| S03 | crear unidad en D2 | **200** | 403 |
| S04 | desactivar una unidad de D2 | **200** | 403 |

## 2. Causa raíz

1. La autorización de capacidad (`require_permission`) y la de empresa (`get_company_context`) son dos dependencias **independientes**, y
   ninguna combina «qué» con «dónde».
2. Comentarios de código (`company_context.py`, `approvals.service.resolve_actors`) fijaron «UserRole dice qué; UserScope, dónde». Ningún
   ADR ratificado lo dice: ADR-D0-014 no habla de roles. La decisión de la dueña de este ciclo la sustituye.
3. Las rutas sin contexto que actúan sobre datos de empresa (G3) o que afectan a todo el tenant (G4, G5) heredan el permiso de tenant.

## 3. Modelo de dominio — EFFECTIVE_AUTHORITY

Una sola fórmula, la de `identity_access/authority.py`, extendida:

```
accesibles(u)                = empresas de user_scopes; sin filas, todas las del tenant          (acceso: dónde puede entrar)
alcance(u, c)                = ⋃ por cada asignación de un rol ACTIVO que contiene c:
                                 company_id NULL → accesibles(u) ; company_id = E → {E} ∩ accesibles(u)
PUEDE(u, c, empresa)         ⇔ u ACTIVE ∧ empresa ∈ alcance(u, c)                                 (capacidad × empresa)
PUEDE_TENANT(u, c)           ⇔ u ACTIVE ∧ alcance(u, c) ⊇ empresas del tenant                     (capacidad de todo el tenant)
```

**Contrato del comodín (§12; un solo significado):**
- `UserRole.company_id NULL` = «en todas las empresas a las que el usuario accede»;
- sin `user_scopes` = «accede a todas las del tenant»;
- **nunca** significa «ninguna».

**Precedencia (§13):** la intersección (asignación ∩ acceso) es el menor privilegio. La unión solo opera **entre asignaciones del mismo
usuario**, que es tener dos roles. El alcance de rama sigue igual: vacío = sin restricción.

**Funciones nuevas, que reutilizan las existentes:**

| Función | Qué hace |
|---|---|
| `has_capability_in_company(db, user, capability, company_id) -> bool` | Evalúa `PUEDE(u, c, empresa)` |
| `require_capability_in_company(db, user, capability, company_id)` | Lanza 403 `COMPANY_SCOPE_FORBIDDEN` y deja auditoría `COMPANY_SCOPE_DENIED` |
| `has_tenant_wide_capability(db, user, capability) -> bool` | Evalúa `PUEDE_TENANT(u, c)` |
| `companies_with_capability(db, user, capability) -> set[str]` | Alias de `effective_scope`, para filtrar consultas |

**Semántica de los roles (OD-DEL-10/12):**
- ADMIN no da capacidades de negocio.
- FUNCIONAL_COMPLETO da las de negocio, solo donde está asignado: FUNCIONAL_COMPLETO en D1 vale solo en D1.
- El alcance de tenant lo da `company_id NULL` con acceso a todas las empresas. Hoy solo lo recibe el administrador del arranque (OD-DEL-12).
  Cualquier otra asignación con NULL es una concesión explícita de quien tiene ese alcance, que pasa por el techo de delegación y queda
  auditada como `ROLE_ASSIGNED` con `company_id: null`.

## 4. Diseño

### C1 · Ejercicio de la capacidad en la empresa (central, G1)

**Mecanismo:**
- `get_company_context` (la única puerta de toda ruta de empresa) resuelve el contexto como hoy.
- Después lee los permisos que **declara la ruta**, que son los `kontrol_permission` de los comprobadores de `require_permission` en el
  árbol de dependencias de `request.scope["route"]`, cacheados por ruta.
- Exige cada uno con `require_capability_in_company(..., ctx.company_id)`.
- Ninguna ruta cambia su firma, y no hay implementaciones paralelas por ruta.

**Error:** 403 `COMPANY_SCOPE_FORBIDDEN`, «No tiene esa autoridad en esta empresa».
- La empresa es una a la que el actor ya accede, así que el 403 no revela su existencia.
- Las empresas inaccesibles siguen respondiendo 404 `COMPANY_NOT_FOUND`, antes que la capacidad.

**Auditoría:** `COMPANY_SCOPE_DENIED` con actor, `reason = "COMPANY_SCOPE_FORBIDDEN"`, `evidence = {capability, company_id}` y
`request_id`. No guarda datos del objetivo.

### C2 · Aprobaciones (G3)

- `resolve_actors` (ROLE) solo toma asignaciones con `company_id` NULL o igual a la empresa de la solicitud.
- `_assert_can_decide` exige `aprobaciones:approve` en `request.company_id`. Sin ella responde 403 `COMPANY_SCOPE_FORBIDDEN`, también al
  delegado.

### C3 · Bitácora (G4)

`GET /audit/events` filtra antes de contar y paginar, en la misma consulta:

```
company_id ∈ companies_with_capability(actor, "audit:view")
OR (company_id IS NULL AND has_tenant_wide_capability(actor, "audit:view"))
```

### C4 · Catálogos de todo el tenant (G5)

Se añade `require_tenant_permission(resource, action)` en `app/core/dependencies.py`:
- Es igual que `require_permission`, pero exige `PUEDE_TENANT`. Si no se cumple, responde 403 `COMPANY_SCOPE_FORBIDDEN`.
- Conserva `kontrol_permission`, para que las pruebas de arquitectura lo sigan viendo.
- Sustituye a `require_permission` en las 11 rutas de G5.

### C5 · Decisiones dentro del servicio (descubierto en la ejecución)

La suite completa no lo mostraba; lo encontró la auditoría de los helpers de `allowed_actions`. Cuatro helpers calculaban los
permisos del usuario sumados de todas sus asignaciones (`identity_service.get_user_permissions`), sin mirar la empresa, y
autorizaban con ellos dentro del servicio:

| Helper | Decide | Gravedad |
|---|---|---|
| `notifications/service._permisos` | Visibilidad de tareas (`scope=all`), completar/asignar, orígenes de notificaciones y alertas, contadores | **Bypass de lectura**: `tareas:view` en D1 listaba todas las tareas de D2 |
| `documents/api._permissions` | Acceso al recurso vinculado (`_assert_resource_access`, `_assert_can_read_file`) y `allowed_actions` | **Bypass de lectura**: documentos por recurso de D2 con el permiso del recurso solo en D1 |
| `master_data/uom_api._permissions` | `allowed_actions` de unidades y presentaciones | Paridad: ofrecía acciones que C1 rechaza |
| `organization/structure.user_permission_set` | `allowed_actions` de almacenes, nodos y ubicaciones | Paridad |

**Diseño:**
- Nueva función `authority.capabilities_in_company(db, user, company_id) -> set[str]`, con invariante `cap ∈ capabilities_in_company(c) ⇔ c ∈ effective_scope(cap)`.
- Los cuatro helpers reciben `company_id`, y las 37 llamadas (6 + 7 + 10 + 14) pasan `ctx.company_id`.
- `/auth/me` y `mfa_service` (techo del restablecimiento de MFA, G6) conservan la suma de todo el tenant. La primera alimenta la guarda de UI (deuda UI-PERMISSIONS-NOT-COMPANY-AWARE); la segunda es identidad y ya la gobierna el techo.

### Lo que no cambia

| Aspecto | Por qué sigue igual |
|---|---|
| Lecturas de G2 | Su autoridad es el acceso |
| Techo de delegación | Ya usa la misma fórmula |
| MFA, reautenticación y sesiones | Sin cambios |
| Frescura | La autoridad se lee de la base en cada petición, sin caché: retirar un rol o un alcance tiene efecto en la petición siguiente (COMPANY_SCOPE_REVOCATION_EFFECTIVE). No hace falta rotar sesiones |
| Concurrencia | La decisión se toma en la transacción de la petición. Una revocación concurrente surte efecto en la siguiente. No se añade candado: TOCTOU acotado a una petición, la misma que ya acepta el modelo de permisos |
| Selector de empresa | Muestra las empresas **accesibles**, que es el acceso. La UI no autoriza: el backend decide por petición |

**RLS:** no se introduce. La autorización del servicio es la canónica (ADR-D0-014). La RLS queda como opción de arquitectura no adoptada.

### Contrato de API y OpenAPI

| Código | Cuándo |
|---|---|
| `COMPANY_SCOPE_FORBIDDEN` (403) | Nuevo, en las rutas de G1 y G5 y en las decisiones de aprobación |
| `COMPANY_NOT_FOUND` (404) | Sin cambios |
| `COMPANY_CONTEXT_REQUIRED` (400) | Sin cambios |

La descripción común de la cabecera (`DESCRIPCION_CABECERA`) añade el 403. Ese cambio de OpenAPI está explicado: OPENAPI_UNEXPLAINED_DRIFT = 0.

## 5. Modelo de seguridad (amenaza → control → prueba)

| Amenaza | Control | Prueba |
|---|---|---|
| IDOR/BOLA entre empresas, `company_id` manipulado, sustitución anidada | ARCH-MC-001, ya existente: el dato se filtra por contexto | `test_mc_*` |
| Capacidad de D1 ejercida en D2 (lista, detalle, alta, edición, baja, transición, exportación) | C1 | CSA-* |
| Cabecera manipulada | `resolve_company` y C1 | CSA-H |
| Aprobación en otra empresa | C2 | CSA-P |
| Fuga en la bitácora | C3 | CSA-A |
| Catálogo de tenant con autoridad parcial | C4 | CSA-T |
| ADMIN usado como autoridad de negocio | OD-DEL-10 | CSA-S01 |
| FUNCIONAL_COMPLETO como «todas las empresas» | Fórmula | CSA-S02 |
| Arranque | OD-DEL-12 | CSA-S03 |
| Alcance obsoleto | Lectura por petición | CSA-R01 |
| Entre tenants | `resolve_company` | CSA-X |

## 6. Modelo UX/UI

- La interfaz no cambia de autoridad.
- **Corrección medida en la ejecución.** La UI **no** muestra el mensaje del backend. Cada pantalla pinta su error propio: «No fue posible cargar las unidades.», o `ForbiddenState` en seis pantallas. TC-6 no se implementa en este ciclo, por dos razones:
  - hacer la guarda de UI consciente de la empresa exige cambiar `AuthContext`, cada `PermissionGuard` y `/auth/me`, un cambio transversal de UI;
  - el backend es la autoridad.
  
  Queda la deuda **UI-PERMISSIONS-NOT-COMPANY-AWARE**. E2E-SCOPE-10 comprueba que la pantalla rechazada no se rompe (encabezado y error visibles, axe sin violaciones graves) y que vuelve al cambiar de empresa.
- Pantallas afectadas por comportamiento: las de negocio con selector de empresa. La revisión está en
  `evidence/company-scope-authorization/screen-form-completeness.md`.

## 7. Requisitos

| ID | Requisito |
|---|---|
| CSA-FR-01 | Lectura con capacidad acotada a la empresa |
| CSA-FR-02 | Alta |
| CSA-FR-03 | Edición |
| CSA-FR-04 | Baja |
| CSA-FR-05 | Transición |
| CSA-FR-06 | Aprobación |
| CSA-FR-07 | Exportación e informe |
| CSA-FR-08 | Revocación efectiva |
| CSA-FR-09 | Entre empresas, 403; entre tenants, 404 |
| CSA-FR-10 | Arranque de tenant |
| CSA-FR-11 | Separación ADMIN / FUNCIONAL_COMPLETO |
| CSA-FR-12 | Auditoría de la denegación |
| CSA-FR-13 | Bitácora acotada |
| CSA-FR-14 | Catálogos de tenant |
| CSA-FR-15 | API directa (sin UI) |

## 8. Gobierno (releído: Ingeniería de Requerimientos KONTROL Gobierno v1.0)

| Requisito | Aplicación | Estado |
|---|---|---|
| RNF-GOV-006 (autoridad en backend) | C1–C4 en el servidor | COVERED |
| RNF-GOV-012 (mínimo privilegio) | Capacidad × empresa | COVERED |
| E2E-06 (aislamiento hostil) | E2E-SCOPE-* | COVERED en el núcleo; el ente de Gobierno es FUTURE_GOV_SPEC |
| GOV-CTL-004 (administrador técnico) | ADMIN sin negocio | COVERED |
| GOV-CTL-001 (SoD) | Aprobación por empresa (C2) | COVERED en lo compartido; la matriz SoD es FUTURE_GOV_SPEC |
| RNF-GOV-005 (auditoría) | `COMPANY_SCOPE_DENIED`; bitácora acotada | COVERED |
| GOV-ORG-001..003 (organismo / ente / unidad) | — | FUTURE_GOV_SPEC: el ente se apoyará en esta fórmula, pero no está resuelto |

Investigación normativa: **NOT_APPLICABLE**. Es seguridad genérica del núcleo y ninguna norma venezolana fija el modelo de autorización.

## 9. Tareas

Todas: SECURITY_SENSITIVE · EGRESS_SAFE · RETRY_MAX 2 · código de DeepSeek; diseño, auditoría y certificación de Claude.

| Tarea | Contenido |
|---|---|
| TC-A1 | Pruebas en rojo C1 (maestros, inventario, compras, ventas, exportación), revocación y semántica de roles |
| TC-A2 | Pruebas en rojo C2, C3 y C4 |
| TC-1 | `authority`: funciones nuevas |
| TC-2 | C1 en `get_company_context` |
| TC-3 | C2 (aprobaciones) |
| TC-4 | C3 (auditoría) |
| TC-5 | C4 (dependencia y 11 rutas) |
| TC-6 | Mensaje de UI |
| TC-7 | Pruebas existentes afectadas (medidas) |
| TC-8 | E2E-SCOPE-01..10 |
| TC-9 | Documentación (contrato y ADR-017) |
| TC-10 | Mutaciones (Claude) |
| TC-A3 | Pruebas en rojo C5 (tareas, documentos por recurso, `allowed_actions` de unidades y almacenes) — añadida en la ejecución |
| TC-A4 / TC-A5 | Pruebas que matan los supervivientes S15/S16 (acceso e inactividad en `capabilities_in_company`) y S13 (asignación a empresa sin acceso) |
| TC-11a..e | C5: `capabilities_in_company` y los cuatro helpers |
| TC-6 | **Reclasificada a deuda** UI-PERMISSIONS-NOT-COMPANY-AWARE (ver §6) |

## 10. Inventario de suites obligatorias (§82, regla permanente)

| ID | Suite |
|---|---|
| RS-01 | Backend PostgreSQL completo con analizador (`qa/suite_tiempos.py --motor postgres --con-analizador`) |
| RS-02 | Backend SQLite completo con analizador |
| RS-03 | Pruebas del ciclo en ambos motores |
| RS-04 | Mutaciones del ciclo (0 supervivientes) y regresión de las de delegación (21/21) |
| RS-05 | vitest completo |
| RS-06 | `tsc -b` |
| RS-07 | `eslint .` |
| RS-08 | `vite build` |
| RS-09 | E2E del ciclo en Chromium, Firefox y WebKit |
| RS-10 | E2E canónica completa (`qa/e2e-run.py --con-analizador`) |
| RS-11 | `ruff check` canónico |
| RS-12 | mypy de los ficheros tocados (sin errores nuevos) |
| RS-13 | Cabeza única de Alembic |
| RS-14 | Residuos: bases E2E, `.mutbak`, sondas |
| RS-15 | Barrido de secretos e historial |

**Al cierre:** UNRUN_REQUIRED_SUITES = 0 y UNKNOWN_REQUIRED_RED_TESTS = 0.

## 11. Gate

BLOCKER = 0 · CONTRADICTIONS = 0 (los comentarios «UserRole nunca dónde» se sustituyen por decisión de la dueña) · MATERIAL OQ = 0 ·
UNKNOWN = 0.

**Constitución:** P1, P2 (encargo), P6 (backend), P7, P10, P12 (ADR-017), P13, P21 (dos motores) y P27 (mutaciones): **PASS**.

## 12. Deudas

| DEBT_ID | Severidad | Situación |
|---|---|---|
| ROLE-COMPANY-SCOPE-NOT-ENFORCED | P0 | Este ciclo |
| UI-PERMISSIONS-NOT-COMPANY-AWARE | MEDIUM (UX; sin bypass) | **Nueva.** La guarda de UI usa `/auth/me` sumado de todo el tenant y puede ofrecer una pantalla que el backend rechaza en la empresa activa; las pantallas muestran su error genérico, no el motivo |
| AUDIT-EVENTS-WITHOUT-COMPANY | MEDIUM | **Nueva.** Algunos eventos se auditan sin `company_id` (p. ej. `uom_api._audit`). Con C3, solo los ve un auditor de todo el tenant: falla en seguro, pero un auditor de empresa no ve las altas de unidades de su empresa. Va al punto 5 del programa (catálogo de auditoría) |
| ROLE-CATALOG-INSTALLATION-WIDE | MEDIUM | Revisada: es visibilidad de metadatos. El techo y C1 impiden ejercer o conceder con esos roles fuera de alcance. Se conserva |
| ROLE-CREATE-UI-MISSING, USER-LIFECYCLE-API-MISSING, ROLES-FORM-FIXED-WIDTHS, OBS-DEL-E2E-401-PARALELO, SHELL-SIDEBAR-NOT-RESPONSIVE y demás de §87 | — | Sin cambios |

## 13. Cierre (2026-10-27)

### REQUIRED_SUITE_INVENTORY (§82)

| ID | Suite | Resultado |
|---|---|---|
| RS-01 | Backend PostgreSQL completo con analizador | **3502 / 0** (18 skip) · `qa/backend-runs/r20261027t003429…` |
| RS-02 | Backend SQLite completo con analizador | **2438 / 0** (1082 skip) · `qa/backend-runs/r20261027t013155…` |
| RS-03 | Pruebas del ciclo en ambos motores (CSA 12 · CSS 6 · CSD 9 · approvals · AUD-TENANT) | Incluidas en RS-01/02, verdes |
| RS-04 | Mutaciones | Alcance **23/23** en SQLite y en PostgreSQL · delegación **21/21** (D17 en PostgreSQL) · `evidence/…/mutaciones.md` |
| RS-05 | vitest completo | **563 / 563** |
| RS-06 | `tsc -b` | PASS |
| RS-07 | `eslint .` | PASS |
| RS-08 | `vite build` | PASS |
| RS-09 | E2E del ciclo + delegación en Chromium, Firefox y WebKit | **51 / 51** (SCOPE 30 + DEL 21) · REAL_SAFARI_NOT_MEASURED (WebKit ≠ Safari) |
| RS-10 | E2E canónica completa | **330 / 330** (320 de línea base + 10 SCOPE), limpieza LIMPIA |
| RS-11 | `ruff check` | PASS |
| RS-12 | mypy de los ficheros tocados | 0 errores nuevos (58 preexistentes, comparados con `HEAD` vía `git archive`) |
| RS-13 | Cabeza de Alembic | Única: `0060_spec003_admin_split`. Sin migraciones en el ciclo |
| RS-14 | Residuos | 0 bases E2E huérfanas · 0 `.mutbak` · sondas solo en el scratchpad |
| RS-15 | Barrido de secretos | Limpio. El valor histórico de `test_audit_tenant_isolation.py` es preexistente: no está en el diff y no viajó a DeepSeek |

UNRUN_REQUIRED_SUITES = 0 · UNKNOWN_REQUIRED_RED_TESTS = 0.

**Rojos atribuidos durante el ciclo, ya resueltos:**
- **SQLite, 20 fallos.** Venían del orden de C2 (TC-3 c1) y de fixtures del contrato anterior (TC-7).
- **PostgreSQL, 1 fallo.** Presupuesto de consultas de los listados de notificaciones, cubierto con TC-11f (una consulta).
- **E2E canónica, 40 fallos y 4 sin correr.** Fixtures que preparaban catálogos fiscales de todo el tenant con el `admin` E2E (solo D1), y bitácora de logins sin empresa consultada por usuarios de una empresa. Se cubrieron con TC-12a/b: el `admintenant` de QA prepara y consulta. El comportamiento es el de C3/C4.

### Pruebas de efecto real
- **Reproducción antes y después** (`reproduccion.txt`): S02, S03 y S04 pasaron de 200 a 403 `COMPANY_SCOPE_FORBIDDEN`, sin efecto en la base.
- **Rojos previos a cada corrección:** `rojo.txt` (C1–C4) y `rojo-derivados.txt` (C5).
- **OpenAPI:** OPENAPI_UNEXPLAINED_DRIFT = 0 (`openapi.md`).
- **Certificación de la base tras la E2E:** cada corrida crea su base efímera y la elimina; `qa/e2e-bases.py listar` da 0 bases de corrida.

### Trazabilidad

| Requisito | Pruebas |
|---|---|
| CSA-FR-01..05 (leer, alta, edición, baja, transición) | CSA-C01..C05, CSD-01..04, E2E-SCOPE-01..03 |
| CSA-FR-06 (aprobación) | CSS-P01/P02, test_approvals (S10, S11, S21) |
| CSA-FR-07 (exportación) | CSA-C05, E2E-SCOPE-04 |
| CSA-FR-08 (revocación) | CSA-C09, E2E-SCOPE-08 |
| CSA-FR-09 (403 entre empresas, 404 entre tenants) | CSA-C10/C11, CSD-07/08, E2E-SCOPE-09 |
| CSA-FR-10/11 (arranque y división) | CSA-C06/C07/C12 |
| CSA-FR-12 (auditoría de la denegación) | CSA-C01, E2E-SCOPE-06 |
| CSA-FR-13 (bitácora acotada) | CSS-A01/A02, AUD-TENANT-09, E2E-SCOPE-06 |
| CSA-FR-14 (catálogos de tenant) | CSS-T01/T02, E2E-SCOPE-07 |
| CSA-FR-15 (API directa) | E2E-SCOPE-01..09 (sin UI) |

Huérfanos: 0.

### Gobierno
§8 sin cambios de estado. E2E-06 (aislamiento hostil) queda COVERED en el núcleo por E2E-SCOPE-01..10. GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0; base de Gobierno `9a41503` intacta.

### Revisión multidisciplinar

| Ángulo | Revisión |
|---|---|
| Seguridad | Sin fallback silencioso: cada denegación es 403 auditado o 404 sin revelar. Sin RLS; MFA intacto |
| Datos | Sin migración ni cambio de esquema |
| Rendimiento | Presupuesto de consultas de los listados preservado (TC-11f) |
| UX | Deuda UI-PERMISSIONS-NOT-COMPANY-AWARE declarada; la pantalla rechazada no se rompe y cumple axe |
| Auditoría | Deuda AUDIT-EVENTS-WITHOUT-COMPANY declarada; falla en seguro |
| Contrato | ADR-017 y `api-contracts.md` |
