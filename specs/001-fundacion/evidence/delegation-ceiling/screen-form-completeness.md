# Techo de delegación · Screen / Form Completeness Gate (2026-10-26)

Base del diseño: §10 del delta `spec003-delegation-ceiling-delta.md`.

Base de la evidencia:
- `RolesPage.test.tsx`: 7 pruebas.
- `e2e/delegation-ceiling.spec.ts`: E2E-DEL-01..07 en los 3 motores.
- Pruebas de backend: `test_delegation_*.py` y `test_spec003_migration_0060.py`.

AUTHORITY_UI_SURFACE_COUNT = 2:
- **Roles** (`/seguridad/roles`): cambia en este ciclo.
- **Usuarios** (`/seguridad/usuarios`): sin cambios funcionales. Ya muestra roles y MFA, y su reset de MFA tiene techo desde la Spec 002.

## 1. Gate por pantalla

| | DEL-S01 «Asignar rol a usuario» | DEL-S02 «Roles y permisos» (lista) | DEL-S03 «Asignaciones actuales» + diálogo «Quitar rol» |
|---|---|---|---|
| PROCESS | Asignar rol (§6) | Consultar el catálogo visible y su delegabilidad | Quitar rol o renunciar (§6) |
| ACTORS | `roles:edit` con MFA y reautenticación | `roles:view` | `roles:edit` con MFA y reautenticación |
| FIELDS | Usuario (obligatorio); Rol (obligatorio; los no delegables se muestran `disabled` con «— fuera de su autoridad»); Empresa (opcional: «Todas las empresas en las que opera» o una empresa, con ayuda) | Nombre, código, «Puede delegarlo» / «Fuera de su autoridad», «protegido», capacidades | Chip rol · empresa; botón «Quitar rol X a Y» |
| ACTIONS | «Asignar» (AsyncButton, sin doble envío) | — | Quitar → `ConfirmationDialog` (ADR-015: confirmación breve) con «Quitar» o «Cancelar» |
| STATES | NORMAL; LOADING; SUCCESS («Rol asignado»); ERROR con mensaje por código: AUTHORITY_CEILING_EXCEEDED, SELF_ESCALATION_FORBIDDEN, CROSS_SCOPE_DELEGATION_FORBIDDEN, ROLE_ALREADY_ASSIGNED, ROLE_INACTIVE, desconocido → mensaje del servidor | LOADING («Cargando…»); EMPTY («Sin roles.») | CONFIRMING; SUCCESS («Rol quitado»); ERROR: AUTHORITY_CEILING_EXCEEDED, TARGET_OUT_OF_SCOPE, LAST_SECURITY_ADMIN_REQUIRED (explica que hay que asignar antes el rol a otra persona) |
| PERMISSIONS | La UI no es la autoridad: deshabilitar es solo orientación, el backend decide (E2E-DEL-03 lo prueba sin interfaz) | Delegabilidad calculada en el servidor para el actor | El backend decide techo, alcance y último administrador |
| VALIDATIONS | UI: no vacíos. Backend: rol del tenant, activo, capacidades ⊆, protegido, alcance ⊆, `extra="forbid"` | — | Backend: techo, alcance, último administrador |
| DB/API | `POST /users/{id}/roles` (200/403/404/409/422) | `GET /roles` (`delegable`, `motivo`, solo del tenant) | `DELETE /users/{id}/roles/{role_id}` (200/403/409) |
| AUDIT | `ROLE_ASSIGNED` (con `company_id`) / `AUTHORITY_DELEGATION_DENIED` (código y capacidades excedidas) | — | `ROLE_REMOVED` / `AUTHORITY_DELEGATION_DENIED` / `LAST_ADMIN_OPERATION_DENIED` |
| SECURITY | Sin autoescalada ni rol sombra; ADMIN y FUNCIONAL_COMPLETO solo para quien los tiene | No lista roles de empresas de otro tenant | Nunca deja al tenant sin administrador de seguridad, tampoco en carrera (candado; DLA-L04/L05) |
| RESPONSIVE | 320 px sin scroll horizontal (E2E-DEL-07) | idem | idem |
| ACCESSIBILITY | Etiquetas asociadas (`htmlFor`/`id`), ayuda con `aria-describedby`; axe WCAG 2.0/2.1/2.2 AA sin violaciones serias (E2E-DEL-07) | idem | El diálogo tiene `role="dialog"`; los botones tienen nombre accesible |
| E2E | DEL-01, 02, 03 | DEL-01 | DEL-04, 05, 06 |
| STATUS | **PASS** (sujeto a la corrida E2E de cierre) | **PASS** | **PASS** |

La pantalla de alta y edición de roles no existe y no se crea (ROLE-CREATE-UI-MISSING, deuda LOW). La API ya aplica el techo.

## 2. Preguntas funcionales

| Pregunta | Respuesta |
|---|---|
| ¿Qué intenta la persona? | Dar o quitar autoridad a otra persona, o renunciar a la propia |
| ¿Qué debe ver? | Qué roles puede delegar, por qué no los demás y en qué empresas valdrá lo que concede |
| ¿Qué no debe poder hacer? | Darse más autoridad, dar autoridad que no tiene, dar ADMIN o FUNCIONAL_COMPLETO sin tenerlos, conceder fuera de sus empresas, gestionar roles superiores al suyo o dejar a la empresa sin administrador de seguridad |
| ¿Y si la interfaz se salta? | El backend rechaza igual (E2E-DEL-03, DC-*, DCR-*) y lo audita |
| ¿Qué pasa con lo ya delegado si el delegante pierde autoridad? | Se conserva (sin cascada); el delegante ya no puede delegarlo más (DC-H01) |
| ¿Cuándo surte efecto quitar un rol? | En la petición siguiente: los permisos se leen de la base en cada petición (E2E-DEL-06) |

## 3. Paridad DB / API / UI

- La UI no ofrece lo que el backend rechazaría: las opciones no delegables están deshabilitadas, con el motivo del servidor.
- La API no expone roles de otro tenant (DCR-G03).
- La BD no permite lo que la API supone imposible: el candado consultivo serializa las mutaciones de autoridad por tenant. La comprobación del último administrador va después del candado (DLA-L04/L05 en PostgreSQL).
- No hay acción de UI que el backend autorice de más.

DB_API_UI_CONTRACT_PARITY = PASS · SCREEN_FORM_COMPLETENESS_GATE = PASS · PROCESS_COMPLETENESS = PASS · FIELD_COMPLETENESS = PASS ·
UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0.
