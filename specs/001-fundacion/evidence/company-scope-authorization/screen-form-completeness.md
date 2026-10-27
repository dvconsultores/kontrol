# Autoridad por empresa · Screen / Form Completeness Gate (2026-10-26)

Diseño de base: §6 del delta `spec003-company-scope-authorization-delta.md`.

Evidencia:
- E2E-SCOPE-01..10 (`e2e/company-scope.spec.ts`) en los 3 motores.
- Las pruebas de backend `test_company_scope_*.py`.

Este ciclo no crea pantallas ni campos. Cambia lo que el backend permite en la empresa activa: la misma pantalla puede responder distinto según la empresa.

AUTHORITY_UI_SURFACE_COUNT = 3:
- **Selector de empresa**: sin cambios.
- **Roles** (`/seguridad/roles`): sin cambios de UI; su promesa pasa a ser verdad.
- **Pantallas de negocio** con la empresa activa: cambia su comportamiento.

## 1. Gate por superficie

| | CSA-S01 Selector de empresa | CSA-S02 «Asignar rol» (campo Empresa) | CSA-S03 Pantallas de negocio en la empresa activa |
|---|---|---|---|
| PROCESS | Elegir en qué empresa se opera | Conceder un rol en una empresa o en todas | Operar (leer, crear, editar, transicionar, exportar) |
| FIELDS | Lista de `GET /organization/companies`: las **accesibles** (`user_scopes`; sin filas, todas las del tenant) | «Empresa»: «Todas las empresas en las que opera» o una. Ayuda: «El rol solo valdrá en la empresa elegida…». **Antes del ciclo era falso** (la capacidad valía en todas); ahora el backend lo cumple (C1, C5) | Las de cada pantalla, sin cambios |
| STATES | Sin cambios | Sin cambios | Nuevo caso de ERROR: 403 `COMPANY_SCOPE_FORBIDDEN` cuando la capacidad no vale en la empresa activa. La pantalla muestra su error genérico («No fue posible cargar las unidades.») o `ForbiddenState`, **no el motivo** (deuda UI-PERMISSIONS-NOT-COMPANY-AWARE) |
| PERMISSIONS | El selector **no autoriza**: la cabecera elige y el backend valida acceso y capacidad en cada petición | El backend aplica el techo (ADR-016) y ahora también el valor de la asignación por empresa (ADR-017) | La guarda de UI usa `/auth/me` (suma de todo el tenant): puede mostrar el menú de una pantalla que el backend rechaza en esa empresa. Es orientación, no autoridad |
| VALIDATIONS | Backend: empresa inaccesible, de otro tenant o inexistente → 404 `COMPANY_NOT_FOUND` (E2E-SCOPE-09) | — | Backend: tenant → acceso → capacidad declarada → capacidad en la empresa → dominio (ADR-017) |
| AUDIT | — | `ROLE_ASSIGNED` con `company_id` | `COMPANY_SCOPE_DENIED` (empresa y capacidad) en cada denegación (E2E-SCOPE-06; CSA-C01) |
| SECURITY | Selector ≠ autorización | Asignación a empresa sin acceso: no cuenta (CSD-07) | Sin efecto en la base al denegar (E2E-SCOPE-02; CSA-C02/C03) |
| ACCESSIBILITY | Sin cambios | Sin cambios | Pantalla rechazada: encabezado de nivel 1 y error visibles; axe WCAG 2.0/2.1/2.2 AA sin violaciones graves (E2E-SCOPE-10) |
| E2E | SCOPE-09, SCOPE-10 (cambio D2 ↔ D1) | SCOPE-01..08 (asignaciones por empresa vía API) | SCOPE-01..08, SCOPE-10 |
| STATUS | **PASS** | **PASS** | **PASS con deuda** UI-PERMISSIONS-NOT-COMPANY-AWARE (MEDIUM, UX, sin bypass) |

## 2. Preguntas funcionales

| Pregunta | Respuesta |
|---|---|
| ¿Qué intenta la persona? | Trabajar en la empresa elegida con la autoridad que tiene en ella |
| ¿Qué debe ver? | Solo lo que su autoridad permite en esa empresa. Hoy ve el menú de toda su autoridad del tenant y el backend rechaza lo demás (deuda) |
| ¿Qué no debe poder hacer? | Leer, crear, cambiar, aprobar o exportar en una empresa donde su rol no vale, por ninguna vía: UI, API directa, cabecera manipulada o servicio interno (C1–C5) |
| ¿Qué pasa si cambia de empresa? | La petición siguiente se autoriza con la nueva empresa; sin caché ni rotación de sesión (E2E-SCOPE-08, SCOPE-10) |
| ¿Hay campos nuevos? | No. Field contract sin cambios: la cabecera `X-Kontrol-Company` documenta el 403 nuevo (OpenAPI explicado) |
