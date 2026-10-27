# UI con autoridad por empresa · Screen / Form Completeness Gate (2026-10-27)

Diseño de base: §6 del delta `spec003-ui-company-aware-authorization-delta.md` y ADR-018.

Evidencia:
- E2E-UI-SCOPE-01..09 (`e2e/ui-company-scope.spec.ts`) y E2E-SCOPE-10 reescrita, en Chromium, Firefox y WebKit.
- vitest de `src/app/autoridad`, `src/components` (Autorizado, RutaAutorizada), `src/layout` (Sidebar), `src/tests`
  (`authority-surfaces`, `gate-coverage`) y `src/pages/AuditoriaPage*`.

El ciclo no crea pantallas de negocio ni campos de formulario. Cambia **qué se ofrece** en cada pantalla: lo decide la autoridad que el
backend calcula en la empresa activa (ADR-018), no la suma del tenant.

AUTHORITY_UI_SURFACE_COUNT = 5 (inventario completo en `ui-authority-surface-matrix.md`: 110 rutas, 229 acciones; UNINVENTORIED = 0).

## 1. Gate por superficie

| | UIA-S01 Menú lateral | UIA-S02 Guarda de ruta (URL directa) | UIA-S03 Acciones de las pantallas | UIA-S04 Selector de empresa | UIA-S05 `/auditoria` |
|---|---|---|---|---|---|
| PROCESS | Navegar a lo que se puede usar en la empresa activa | Entrar a una pantalla por enlace o URL | Crear, editar, transicionar, aprobar, exportar | Cambiar la empresa de trabajo | Consultar la bitácora |
| FIELDS | Entradas por módulo; sin cambios de texto | Denegación: h1 + texto (§3) | Ningún campo nuevo. Los campos de datos de un detalle no editable siguen visibles en solo lectura (PoliticaDetalle) | Sin cambios | La descripción dice qué parte ve: todo el tenant o solo sus empresas (§3) |
| STATES | CARGANDO: solo lo que no exige nada; LISTA: lo autorizado | CARGANDO → `LoadingState`; DENEGADA → `DenegacionDeAutoridad` (role="alert"); PERMITIDA → la pantalla | Lo no autorizado **no se pinta** (AD-6); estado ∧ autoridad en las filas | Al cambiar, la autoridad de la otra empresa nunca se sirve: CARGANDO hasta la nueva | Sin cambios de carga, vacío ni error |
| PERMISSIONS | Registro único `pantallas.ts` (capacidad del módulo con alcance explícito ∧ operación principal) | El mismo registro | La operación exacta que dispara cada control (`<Autorizado>` / `puede`) | El selector no autoriza; la cabecera elige y el backend decide | `audit:view` (global para entrar; el contenido lo acota el backend, ADR-017 (f)) |
| VALIDATIONS | Deriva: rutas del router ↔ registro, capacidades ∈ catálogo del backend | Idem | gate-coverage: toda llamada mutante con capacidades tiene puerta o exención justificada | Empresa inaccesible → 404 `COMPANY_NOT_FOUND` → el contexto se suelta (CURRENT_COMPANY_NO_LONGER_AUTHORIZED) | — |
| AUDIT | Sin cambios | La UI no pide; si alguien llama por API, el backend audita `COMPANY_SCOPE_DENIED` (02B) | Idem | Sin cambios | Sin cambios |
| SECURITY | Orientación, no seguridad: el backend autoriza cada petición (E2E-UI-SCOPE-04 y SCOPE-10 por API) | Sin montar la pantalla ni pedir datos (SCOPE-10: 0 peticiones a la API); FUNCIONAL_COMPLETO de D1 no vale en D2 (UI-SCOPE-05) | ADMIN sin FUNCIONAL_COMPLETO no ve pantallas ni acciones de negocio (UI-SCOPE-06) | Frescura ≤ 60 s y ante cada 403 (AD-3) | Ningún texto nombra otras empresas |
| ACCESSIBILITY | Enlaces con nombre accesible; sin cambios | Denegación con h1 y `role="alert"`; axe WCAG 2.0/2.1/2.2 AA sin graves en `main` (SCOPE-10 y UI-SCOPE) | Ocultar no deja huecos en el orden de tabulación | Sin cambios | Texto plano en la cabecera |
| E2E | UI-SCOPE-01/02/06/08 y el crawler de rutas | UI-SCOPE-03/05/06, SCOPE-10 | UI-SCOPE-01 (alta en su empresa), UI-SCOPE-07 (catálogo de todo el tenant); por API, UI-SCOPE-04 | UI-SCOPE-02/09, SCOPE-10 | vitest ALC-01/02 |
| STATUS | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## 2. Preguntas funcionales

| Pregunta | Respuesta |
|---|---|
| ¿Qué intenta la persona? | Trabajar en la empresa elegida con la autoridad que tiene en ella |
| ¿Qué debe ver? | Solo lo que esa autoridad permite en esa empresa: menú, pantallas y acciones |
| ¿Qué no debe ver? | Acciones que el backend negaría en la empresa activa, autoridad de otra empresa ni datos de otras empresas |
| ¿Qué pasa si entra por URL directa sin autoridad? | Ve «Acceso prohibido», «Sin autoridad en esta empresa» (con la empresa activa) o «Requiere autoridad en todas las empresas», y la pantalla no pide nada |
| ¿Qué pasa si cambia de empresa? | Menú, guarda y acciones se recalculan con la autoridad de la nueva empresa; mientras llega no se ofrece nada de empresa |
| ¿Y si le quitan un rol mientras trabaja? | El primer 403 del backend invalida la autoridad y recarga `/auth/me`; sin interacción, como mucho 60 s |
| ¿Hay campos nuevos? | No |

## 3. Field contract (textos nuevos o cambiados)

| Superficie | Texto exacto |
|---|---|
| Denegación · `PERMISSION_DENIED` | «Acceso prohibido» / «No tiene permiso para esta pantalla. Si lo necesita, pídalo a su administrador.» |
| Denegación · `COMPANY_SCOPE_FORBIDDEN` (empresa) | «Sin autoridad en esta empresa» / «Su autoridad para esta pantalla no incluye la empresa activa ({nombre}). Cambie a una empresa en la que la tenga o pida acceso a su administrador.» |
| Denegación · `COMPANY_SCOPE_FORBIDDEN` (tenant) | «Requiere autoridad en todas las empresas» / «Esta configuración afecta a todas las empresas del tenant; solo puede gestionarla quien tiene esta autoridad en todas ellas.» |
| `/auditoria` · auditor de todo el tenant | «Eventos de acceso y operaciones de todas las empresas del tenant, incluidos los que no pertenecen a ninguna empresa (como los inicios de sesión).» |
| `/auditoria` · auditor de algunas empresas | «Eventos de las empresas en las que usted tiene autoridad de auditoría. Los eventos sin empresa (como los inicios de sesión) solo los ve quien audita todas las empresas del tenant.» |

Sustituye a la deuda declarada en el gate del ciclo anterior (CSA-S03 «PASS con deuda UI-PERMISSIONS-NOT-COMPANY-AWARE»): **cerrada**.
