# SPEC 003 · Delta — SHARED-CORE-P0-HARDENING-02C · UI COMPANY-AWARE AUTHORIZATION

| Campo | Valor |
|---|---|
| Spec dueña | **003** (Usuarios / Roles / Alcance); afecta a todas las pantallas de negocio |
| Deuda que cierra | **UI-PERMISSIONS-NOT-COMPANY-AWARE** (declarada en ADR-017) |
| HEAD de entrada | `56f0f5e` (develop = origin/develop) |
| Evidencia | `evidence/ui-company-aware-authorization/` |
| Decisiones de la dueña | **OD-UI-01 = cobertura total con puerta central.** Toda acción que modifica, en las 93 pantallas, se condiciona por la misma operación del backend que invoca, sin capacidades fijadas en la UI (2026-10-27). Se mantienen las anteriores: OD-DEL-10 (ADMIN técnico, FUNCIONAL_COMPLETO funcional, ninguno implica todas las empresas), OD-DEL-12 y ADR-017 |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| Estado | **IMPLEMENTED — CONVERGED — REQUIRED_SUITE_INVENTORY_COMPLETE = 1** (2026-10-27; diseño autorizado por el encargo «SHARED-CORE-P0-HARDENING-02C»; convergencia: UIA-FR-01..12, AD-1..AD-8 y las 25 tareas de §10 sin hallazgos) |

## 1. Discover (medido en `56f0f5e`)

### 1.1 Cómo decide hoy la UI

| Pieza | Fuente | Hallazgo |
|---|---|---|
| `AuthContext.hasPermission` | `GET /auth/me` → `identity_service.get_user_permissions` | Suma los permisos de **todos** los roles del usuario, sin mirar la empresa de cada asignación. Se carga al entrar y al renovar la sesión; **no** cambia al cambiar de empresa |
| `Sidebar` | `hasPermission(section.permission)` en 21 puntos | Una sección se ve si el permiso está en cualquier empresa |
| Router (111 rutas *lazy*) | `RouteGuard`, que solo exige sesión | **Sin guarda de autoridad.** Una URL directa monta la pantalla y el backend la rechaza después |
| Botones de acción | Sin comprobación en 71 de 93 pantallas con acciones | `allowed_actions` de ventas, compras, inventario, tesorería y aprobaciones se calcula **solo por estado** (0 referencias a permisos en sus servicios). El botón se ve aunque el usuario no tenga la capacidad en ninguna empresa |
| 13 ficheros con `hasPermission` | Tareas, alertas, reglas, enlace de notificaciones, usuarios (MFA), licencia, diagnóstico, panel, banner | Usan la suma de todo el tenant también para superficies de empresa |
| Caché por empresa | `crearHashDeClave` (claves con la empresa activa), `AppShell` (descarta la caché y remonta al cambiar), `onCompanyRejected` (404 de empresa → suelta el contexto) | **Reutilizable:** una consulta de autoridad con raíz de empresa queda separada por empresa sin código nuevo |
| Cabecera de empresa | `esRutaDeEmpresa`: no la envía a `/auth/` | La autoridad de empresa no puede vivir bajo `/auth/` |

### 1.2 UI_AUTHORITY_SURFACE_MATRIX

`evidence/ui-company-aware-authorization/ui-authority-surface-matrix.md`, generada a partir del código y del inventario de rutas del backend:
- **A. 110 rutas de pantalla:** 85 COMPANY_SCOPED, 14 GLOBAL_TECHNICAL y 11 sin llamada propia (inicio, preferencias, MFA…).
- **B. 229 acciones que modifican:** 195 COMPANY_SCOPED, 10 TENANT_WIDE y 24 GLOBAL_TECHNICAL, en 93 pantallas.

Además están las 21 entradas del menú condicionadas y los 13 ficheros con `hasPermission`.

Tres llamadas GET no resuelven por concatenación de texto: el combobox genérico, la cola de put-away y la línea de auditoría. Se clasifican a mano: COMPANY_SCOPED, de solo lectura.

**UNINVENTORIED_UI_AUTHORITY_SURFACES = 0.**

### 1.3 Clasificación (§23)

| Clase | Superficies | Regla de la UI |
|---|---|---|
| COMPANY_SCOPED | Negocio: organización (salvo empresas), maestros, inventario, compras, ventas, tesorería, fiscal operativo, regulatorio, aprobaciones, documentos, comercial, reportes, tareas, alertas, reglas | Capacidades **en la empresa activa** |
| TENANT_WIDE | Fuentes legales, versiones de reglas fiscales (alta y aprobación), escrituras de homologación, alta de empresa | Capacidades **en todas las empresas del tenant** (C4) |
| GLOBAL_TECHNICAL | Usuarios, roles, sesiones, MFA, licenciamiento, diagnóstico, bitácora `/audit/events` | Permisos de `require_permission` (`/auth/me`), sin empresa |
| MIXED | `/auditoria`: global para entrar (`audit:view` en alguna empresa) y acotada por empresa en el contenido (C3) | La UI dice que la lista es de las empresas donde se audita |

## 2. Reproducción

Se reproduce con E2E en rojo (TA-F1, E2E-UI-SCOPE-01..09) antes de implementar. Un actor con `maestros:view` y `maestros:create` en D1, con la empresa activa D2:
- ve la sección «Maestros»;
- ve el botón de alta;
- monta `/maestros/unidades` por URL directa.

El backend responde 403 `COMPANY_SCOPE_FORBIDDEN`. Evidencia en `rojo-e2e.txt`.

## 3. Causa raíz

La UI tiene **una sola fuente de autoridad, la suma de todo el tenant**. No existe proyección del backend por empresa, y tres consumidores la necesitan:
1. el menú (`Sidebar`);
2. la ruta, que no tiene guarda;
3. las acciones, que no tienen puerta.

El backend sí distingue tres alcances (C1 empresa, C4 tenant, `require_permission` global), pero no publica ninguno salvo el global. Las capacidades que gobiernan cada acción viven en el backend (permiso declarado por la ruta), y la UI no tenía forma de conocerlas sin copiarlas.

## 4. Investigación normativa

**NOT_APPLICABLE.** Es autorización genérica del núcleo compartido; ninguna norma venezolana fija la presentación de la autoridad en la interfaz. Los requisitos de Gobierno aplicables se reconcilian en §11.

## 5. Modelo de proceso, dominio y datos

- **Proceso:** el usuario entra, elige una empresa (o se resuelve la única) y opera.
- **Invariante:** `UI_ACTION_AVAILABLE(actor, operación, empresa) ⇔ el backend la autorizaría ahora`, con la misma fórmula de ADR-017.
- **Datos:** **DATABASE_CHANGE = NOT_APPLICABLE**, sin migración.

## 6. Diseño

### AD-1 · Proyección del backend (la única fuente)

| Endpoint | Clase | Contenido |
|---|---|---|
| `GET /api/v1/auth/me` (existe) | global | Añade `tenant_permissions`: capacidades que valen en **todas** las empresas del tenant (`authority.tenant_wide_capabilities` = ∩ `capabilities_in_company` sobre las empresas del tenant; vacío si no hay ninguna). `permissions` no cambia: es exactamente lo que usa `require_permission` |
| `GET /api/v1/authority/company` (nuevo) | de empresa, sin permiso declarado (gobierna el acceso) | `{company_id, permissions}` = `capabilities_in_company` en la empresa de la cabecera. Inaccesible, de otro tenant o inexistente → 404 `COMPANY_NOT_FOUND` (C1) |
| `GET /api/v1/auth/operations` (nuevo) | global | Catálogo `{operations: [{method, path, capabilities, scope}]}` de las rutas de la API, con los permisos declarados (el mismo recorrido de dependencias que C1) y `scope` ∈ COMPANY (depende de `get_company_context`) / TENANT (`require_tenant_permission`, marcado con `kontrol_scope = "TENANT"`) / GLOBAL. Se calcula una vez por proceso. No es dato de usuario |

Ninguno de los tres expone autoridad de otra empresa:
- `/authority/company` responde solo por la empresa de la cabecera, que el acceso valida;
- `/auth/operations` es metadato de la API, igual para todos.

### AD-2 · Autoridad en el frontend (proyección, no modelo propio)

`src/app/autoridad/`:
- `operaciones.ts` (puro): compila las plantillas del catálogo y resuelve `(método, ruta concreta)` a su operación.
- `AutoridadProvider` y `useAutoridad()`, dentro de `CompanyProvider`.

| Conjunto | Fuente | Clave de caché |
|---|---|---|
| global | `useAuth().permissions` (`/auth/me`) | `["auth", …]`: no depende de la empresa |
| tenant | `useAuth().tenantPermissions` (`/auth/me`) | idem |
| empresa | `GET /authority/company` | `["autoridad", "empresa", userId]`: raíz de empresa, así que la caché la separa por empresa sola |
| catálogo | `GET /auth/operations` | `["auth", "operaciones"]`, `staleTime: Infinity` |

API del hook:
- `estado`: `CARGANDO | LISTA | ERROR`.
- `puede(método, ruta)`: resuelve la operación y exige todas sus capacidades en el conjunto de su `scope`. Una operación sin capacidades se permite, porque la gobierna el acceso. Una ruta desconocida no se permite.
- `motivo(método, ruta)`: `null | PERMISSION_DENIED | COMPANY_SCOPE_FORBIDDEN`. Es COMPANY_SCOPE_FORBIDDEN si las capacidades están en el conjunto global pero no en el de su alcance; si tampoco, PERMISSION_DENIED.
- `tiene(capacidad, alcance)`: `alcance` ∈ `empresa | tenant | global`, explícito.

Sin empresa activa, el conjunto de empresa está vacío: ninguna superficie COMPANY_SCOPED se ofrece.

**Se retira `hasPermission` de `AuthContext`.** Sus 13 consumidores pasan a `useAutoridad`, con alcance explícito, para que nadie vuelva a usar la suma del tenant como autoridad de empresa.

### AD-3 · Frescura (FRONTEND_STALE_SCOPE_AUTHORITY = BLOCKED)

| Evento | Efecto |
|---|---|
| Cambio de empresa | La clave cambia de identidad y la autoridad de D1 nunca se sirve bajo D2. Sin `placeholderData`: mientras llega, el estado es `CARGANDO` y no se ofrece nada de empresa |
| Revocación (rol, alcance o permiso) | El cliente notifica todo 403 `PERMISSION_DENIED` o `COMPANY_SCOPE_FORBIDDEN` (`setAuthorityDenialHandler`). El proveedor invalida la autoridad de empresa y recarga `/auth/me`, una vez por ráfaga |
| Paso del tiempo | `refetchInterval` de 60 s y recarga al volver el foco: la autoridad caducada dura como mucho 60 s sin interacción |
| Renovación de sesión | Ya recarga `/auth/me` |
| Empresa activa ya no autorizada | `/authority/company` responde 404 `COMPANY_NOT_FOUND`, y el mecanismo existente `onCompanyRejected` suelta el contexto y muestra la selección (CURRENT_COMPANY_NO_LONGER_AUTHORIZED) |

El backend sigue autorizando cada petición.

### AD-4b · Requisito de pantalla (medido en la ejecución)

**Medido:** 63 de las 85 rutas de pantalla COMPANY_SCOPED tienen como lectura principal una ruta que no declara permiso. Son las lecturas G2 de 02B (`GET /sales/orders`, `/purchasing/orders`, `/inventory/balances`…), que gobierna solo el acceso. Una guarda que mirara solo la operación principal dejaría a ADMIN entrar en las pantallas de ventas.

**Diseño:** un registro único `src/app/autoridad/pantallas.ts`, que consumen el router y el menú. Por cada ruta declara uno de dos valores:
- `null` (la gobierna solo la sesión, como Inicio, preferencias o MFA), en una lista blanca explícita;
- `{capacidad, alcance, operacion?}`. La capacidad es la del módulo (la misma que la sección del menú), con alcance explícito; la operación es la lectura principal cuando declara capacidades (p. ej. `GET /approvals/inbox` → `aprobaciones:approve`).

La pantalla se permite si se cumplen las dos: `tiene(capacidad, alcance)` y `puede(operacion)`.

**Deriva:**
- un vitest exige que cada ruta del router tenga entrada;
- otro, que cada capacidad del registro exista en el catálogo del backend (instantánea).

**Deuda nueva: COMPANY-READS-WITHOUT-DECLARED-PERMISSION** (MEDIUM, preexistente). Las 112 lecturas GET de empresa sin permiso declarado (G2) del backend no exigen la capacidad de vista del módulo: ADMIN (sin negocio) puede leer, por ejemplo, órdenes de venta por API. La UI no lo ofrece, porque el registro exige la capacidad del módulo, pero el backend sí lo permite. Afecta a GOV-CTL-004 y a RNF-GOV-012 en lectura. No se absorbe en silencio en este ciclo de UI: exige decidir, ruta por ruta, el permiso de vista. Se propone para el ciclo de identidad o de catálogo de auditoría.

### AD-4 · Guarda de ruta (DIRECT_URL_DENIAL_UI)

- Cada ruta del router declara `handle: { operacion: [método, ruta] }`, su operación principal: la lectura con la que se monta.
- `RutaAutorizada`, en `AppShell` alrededor del `Outlet`, lee la coincidencia más profunda:

| Estado | Pinta |
|---|---|
| `CARGANDO` | `LoadingState` |
| denegada | `DenegacionDeAutoridad`, con el mensaje de su motivo |
| permitida | La pantalla |

- Las rutas sin operación (inicio, preferencias, MFA…) se listan explícitamente en una lista blanca. Una prueba de inventario exige que cada ruta tenga operación o esté en la lista.

### AD-5 · Menú

- **Sección:** conserva la capacidad de su módulo (`fiscal:view`, `ventas:view`…) como relevancia de navegación. Ahora se evalúa con alcance explícito: `empresa` en las secciones de negocio y `global` en Seguridad y Licenciamiento. Se mide en la empresa activa, no en la suma.
- **Entrada:** además declara su operación principal, y se ve solo si `puede(operación)`.

Medido: algunas lecturas no declaran permiso; por ejemplo, `GET /fiscal/legal-sources` es global y la gobierna el acceso. Si la capacidad de sección desapareciera, todo usuario vería módulos ajenos a su rol. Con la regla de arriba, el menú nunca ofrece más de lo que el backend permite, y tampoco ofrece módulos irrelevantes.

**Deriva:** un vitest exige que cada capacidad de sección exista en el catálogo.

### AD-6 · Acciones (OD-UI-01)

`<Autorizado operacion={[método, ruta]}>` envuelve el botón o el control que dispara esa llamada exacta. Si la operación no está autorizada en la empresa activa (o en su alcance), el control **no se pinta**.

Regla de UX (§43):
- Se **oculta** lo que la autoridad no permite. Mostrarlo deshabilitado añadiría ruido en tablas de 93 pantallas sin dar al usuario nada que pueda hacer.
- La explicación vive en la denegación de la ruta.
- Las acciones deshabilitadas por **estado** (`allowed_actions`, `can_*`) siguen como están. En una fila se combinan: estado ∧ autoridad.

### AD-7 · Mensajes (§17, §44)

`DenegacionDeAutoridad`. Ningún mensaje nombra otras empresas ni datos de ellas.

| Motivo | Título | Texto |
|---|---|---|
| `PERMISSION_DENIED` | «Acceso prohibido» | «No tiene permiso para esta pantalla. Si lo necesita, pídalo a su administrador.» |
| `COMPANY_SCOPE_FORBIDDEN` (empresa) | «Sin autoridad en esta empresa» | «Su autoridad para esta pantalla no incluye la empresa activa (*nombre*). Cambie a una empresa en la que la tenga o pida acceso a su administrador.» |
| `COMPANY_SCOPE_FORBIDDEN` (tenant) | «Requiere autoridad en todas las empresas» | «Esta configuración afecta a todas las empresas del tenant; solo puede gestionarla quien tiene esta autoridad en todas ellas.» |
| CURRENT_COMPANY_NO_LONGER_AUTHORIZED | (lo pinta `EstadoDeEmpresa` al soltarse el contexto) | — |

### AD-8 · Rendimiento

| Recurso | Coste |
|---|---|
| Catálogo de operaciones | 1 petición por sesión |
| Autoridad de empresa | 1 petición por empresa y minuto (o por denegación) |
| `/auth/me` | +1 conjunto: N consultas, una por empresa del tenant, solo al entrar o renovar |

`puede()` resuelve en memoria con un índice por método y número de segmentos. No hay peticiones por botón ni por entrada del menú. El backend no cambia ningún listado, así que el presupuesto de consultas de 02B se conserva.

## 7. Modelo de seguridad

| Amenaza | Control | Prueba |
|---|---|---|
| La UI muestra una acción no autorizada | AD-6 por la operación exacta | vitest por pantalla y E2E-UI-SCOPE-01/02 |
| La guarda deja pasar una ruta inaccesible | AD-4 | E2E-UI-SCOPE-03, vitest de la guarda |
| El cambio de empresa conserva capacidades | Clave por empresa, sin *placeholder* | E2E-UI-SCOPE-08, vitest del proveedor |
| La caché de D1 se reutiliza en D2 | `crearHashDeClave` | vitest |
| FUNCIONAL_COMPLETO se interpreta como todas las empresas | La proyección viene del backend (`capabilities_in_company`) | E2E-UI-SCOPE-05 |
| ADMIN se interpreta como autoridad funcional | Ídem: ADMIN no trae negocio | E2E-UI-SCOPE-06 |
| Una ruta de tenant se trata como de empresa | `scope` TENANT del catálogo | E2E-UI-SCOPE-07, pytest del catálogo |
| URL directa | AD-4 | E2E-UI-SCOPE-03 |
| Deriva entre backend y frontend | El catálogo se genera del backend. Prueba de inventario: cada `apiFetch` del frontend resuelve en el catálogo (instantánea de pruebas regenerada desde el backend, cuya prueba compara la instantánea con las rutas vivas) | pytest y vitest de deriva |
| Manipulación del estado del frontend | No da autoridad: el backend decide (02B) | E2E-UI-SCOPE-04 |

## 8. UX/UI y Screen/Form (revisión previa)

**Cambian:**
- el menú;
- la guarda de ruta;
- las acciones de 93 pantallas;
- `TareasPage` (el ámbito «todas» por `tareas:view` en la empresa);
- `AlertasPage` y `ReglasPage` (la entrada por permiso en la empresa);
- el enlace de notificaciones (el destino por la autoridad de empresa);
- la página `/auditoria` (texto que acota la bitácora a las empresas auditadas).

No cambian campos ni formularios. Los formularios con selector de empresa (asignar rol) conservan el contrato de ADR-016/017.

La revisión completa por pantalla queda en `screen-form-completeness.md` al cierre: proceso, estados, permisos, alcance, errores, a11y, 320 px y E2E.

## 9. Requisitos

| ID | Requisito |
|---|---|
| UIA-FR-01 | El menú refleja la autoridad en la empresa activa |
| UIA-FR-02 | La guarda de ruta deniega con el motivo correcto |
| UIA-FR-03 | Las acciones se ofrecen solo si su operación está autorizada |
| UIA-FR-04 | Cambiar de empresa recalcula la autoridad sin restos |
| UIA-FR-05 | Una revocación se refleja tras la denegación siguiente o en ≤ 60 s |
| UIA-FR-06 | TENANT_WIDE exige todas las empresas |
| UIA-FR-07 | GLOBAL_TECHNICAL usa los permisos globales |
| UIA-FR-08 | ADMIN no recibe UI funcional |
| UIA-FR-09 | FUNCIONAL_COMPLETO en D1 no vale en D2 |
| UIA-FR-10 | Mensajes distintos para PERMISSION_DENIED y COMPANY_SCOPE_FORBIDDEN |
| UIA-FR-11 | La fuente es el backend; sin modelo de permisos propio en la UI |
| UIA-FR-12 | Deriva detectada por pruebas |

## 10. Tareas

Todas: EXECUTOR DeepSeek · SECURITY_SENSITIVE · EGRESS_SAFE · RETRY_MAX 2 · auditoría y certificación de Claude.

| Tarea | Contenido | Modelo |
|---|---|---|
| TA-B1 | Pruebas backend en rojo: `tenant_permissions`, `/authority/company` y `/auth/operations` | pro |
| TA-F1 | E2E en rojo E2E-UI-SCOPE-01..09 | pro |
| TB-1 | `authority.tenant_wide_capabilities`; catálogo de operaciones; marca `kontrol_scope` | pro |
| TB-2 | Endpoints (`identity_access`) | flash |
| TB-3 | Instantánea del catálogo para las pruebas del frontend, y su prueba de deriva | flash |
| TF-1 | Cliente: notificación de denegaciones | flash |
| TF-2 | `operaciones.ts` (resolución pura) y vitest | pro |
| TF-3 | `AuthContext` (`tenantPermissions`, `reloadMe`, sin `hasPermission`) y `AutoridadProvider`/`useAutoridad` con vitest | pro |
| TF-4 | `Autorizado`, `RutaAutorizada` y `DenegacionDeAutoridad` con vitest | pro |
| TF-5 | Router (`handle.operacion`), `AppShell` y prueba de inventario de rutas y llamadas | pro |
| TF-6 | `Sidebar` por operación y su prueba | flash |
| TF-7 | Los 13 consumidores de `hasPermission` y sus pruebas | flash |
| TF-8.* | Puerta de acciones, por módulo (aprobaciones, comercial, compras, documentos, fiscal, homologación, inventario, licenciamiento, maestros, notificaciones, organización, regulatorio, reportes, seguridad, tesorería, ventas, páginas) | pro |
| TF-9 | Texto de alcance de `/auditoria` | flash |

**Añadidas en la ejecución** (detalle, rechazos y costes en `evidence/ui-company-aware-authorization/orchestration.md`):

| Tarea | Contenido | Por qué |
|---|---|---|
| TF-8L.01..18 | Limpieza tras TF-8 (imports y variables sin uso, `disabled` redundantes) y AD-6 en dos botones que se deshabilitaban | tsc/eslint y una desviación de AD-6 aceptada en auditoría |
| TF-8T.01..05 | Mock de `useAutoridad` en cinco pruebas de pantalla | Montaban pantallas con puerta sin `AutoridadProvider` (23 fallos, una causa) |
| TF-8z | `src/tests/gate-coverage.test.ts`: ninguna llamada mutante con capacidades sin puerta | Impedir regresiones de OD-UI-01 |
| TF-E1 / TF-E2 | E2E-SCOPE-10 al comportamiento nuevo; el crawler espera el menú completo | La E2E canónica fijaba el comportamiento viejo / carrera nueva del menú |
| TF-M1 / TF-M2 | Pruebas que matan los mutantes R6, P3 y P6 | Supervivientes de la primera corrida de mutaciones |
| TB-R1..3 | Tres guardas del backend tocadas por el ciclo | Suite PostgreSQL completa: 3 fallos |
| TD-1 / TD-2 | ADR-018 y contrato de la API | Documentación de producto |

## 11. Gobierno (releído: Ingeniería de Requerimientos KONTROL Gobierno v1.0, 2026-10-27)

| Requisito | Texto (resumen) | Aplicación | Estado |
|---|---|---|---|
| P-05 | El backend decide el alcance; la UI no es autoridad | AD-1/AD-2: proyección del backend. Las puertas son UX | COVERED |
| RNF-GOV-006 | Autorización crítica en el backend, «no confiar en UI ni claims sin verificación contextual» | Sin cambios en el backend (02B). E2E-UI-SCOPE-04 lo prueba por API | COVERED |
| RNF-GOV-012 | Roles sin autoridad transversal; capacidades y alcance | La UI deja de sumar el tenant (AD-2) | COVERED |
| GOV-CTL-004 | El administrador técnico no fabrica autoridad funcional | ADMIN sin negocio también en la UI (E2E-UI-SCOPE-06) | COVERED |
| GOV-CTL-005 | Consulta *read-only* para el auditor | `/auditoria` acotada y rotulada (TF-9) | COVERED |
| RNF-GOV-005 | Auditabilidad | Sin cambios: la denegación del backend ya se audita (02B) | COVERED (sin cambio) |
| RNF-GOV-014 | UI usable con teclado, contraste y etiquetas | axe en las pantallas del ciclo (E2E) | COVERED |
| RNF-GOV-015 | Errores deterministas | Motivos y mensajes por código (AD-7) | COVERED |
| E2E-06 | Hostil multi-ente: 100 % denegado y auditado | Núcleo: E2E-UI-SCOPE-03/04 más los de 02B. El ente es FUTURE_GOV_SPEC | COVERED en el núcleo |

**Releído al cierre** (2026-10-27, `pdftotext` del PDF de Ingeniería de Requerimientos v1.0): los nueve requisitos dicen lo que esta tabla
recoge; RNF-GOV-015 (interoperabilidad: APIs versionadas, contrato de esquema y errores) queda cubierto además por la deriva de OpenAPI
explicada (`evidence/ui-company-aware-authorization/openapi.md`). La línea base de Gobierno `9a41503` no cambia (sin diferencias en
`requerimientos/gobierno/`). GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 · GOVERNMENT_SPEC_STARTED = 0 · GOV0_STARTED = 0.

## 12. Inventario de suites obligatorias (§60)

| ID | Suite | Resultado (árbol final, 2026-10-27) |
|---|---|---|
| RS-01 | Backend PostgreSQL completo con analizador | **3511/0** (18 omitidas; 3502 + 9 del ciclo), desvío de reloj 0,0 s, NORMAL · `r20261027t141528…` |
| RS-02 | Backend SQLite completo con analizador | **2447/0** (1082 omitidas; 2438 + 9), NORMAL · `r20261027t145308…` |
| RS-03 | Pruebas backend del ciclo (ambos motores) | UIA-B01..07 y deriva de instantáneas, dentro de RS-01/02 |
| RS-04 | vitest completo | **611/611** (52 ficheros) |
| RS-05 | `tsc -b` | 0 errores |
| RS-06 | `eslint .` | 0 errores, 0 avisos |
| RS-07 | `vite build` | OK |
| RS-08 | E2E del ciclo (UI-SCOPE) + 02B (SCOPE) + delegación en Chromium, Firefox y WebKit | **78/78** · `r20261027t133453…` (UI-SCOPE 27/27 también por separado) |
| RS-09 | E2E canónica completa (con analizador) | **339/339** (330 + 9 UI-SCOPE), sin omitidas · `r20261027t151620…` |
| RS-10 | Mutaciones | Frontend **19/20 + 1 equivalente**; gate-coverage 2/2; backend 02B **23/23** y delegación **21/21** (`evidence/…/mutaciones.md`) |
| RS-11 | OpenAPI: deriva explicada | 2 rutas nuevas de solo lectura, 1 descripción; esquemas idénticos; OPENAPI_UNEXPLAINED_DRIFT = 0 |
| RS-12 | `ruff` y mypy de los ficheros tocados | ruff limpio; mypy: 0 errores en los ficheros del ciclo (los 154 de `app` ya estaban en `HEAD`, mismos 18 ficheros) |
| RS-13 | Cabeza de Alembic | Una cabeza, `0060_spec003_admin_split`; el ciclo no migra |
| RS-14 | Residuos y barrido de secretos | 152 ficheros: 0 secretos, 0 rutas personales (una saneada en la evidencia); el `.docx` de la dueña fuera |

**Al cierre:** UNRUN_REQUIRED_SUITES = 0 y UNKNOWN_REQUIRED_RED_TESTS = 0.

## 13. Gate

BLOCKER = 0 · CONTRADICTIONS = 0 · MATERIAL OQ = 0 (OD-UI-01 resuelta por la dueña) · UNKNOWN = 0.

**Constitución:** P1, P2 (encargo), P6 (backend autoridad; la UI proyecta), P7, P10, P12 (ADR-018), P13, P21 y P27: **PASS**.

## 14. Deudas y observaciones

| ID | Severidad | Situación |
|---|---|---|
| UI-PERMISSIONS-NOT-COMPANY-AWARE | MEDIUM | **CERRADA** en este ciclo (ADR-018) |
| COMPANY-READS-WITHOUT-DECLARED-PERMISSION | MEDIUM (preexistente) | **Nueva** (AD-4b): 112 lecturas GET de empresa no declaran la capacidad de vista del módulo; la UI no las ofrece sin ella, pero el backend las permite por API (afecta a GOV-CTL-004 y RNF-GOV-012 en lectura). Exige decidir el permiso ruta por ruta: ciclo de identidad o de catálogo |
| ROLE-STATUS-NOT-IN-GLOBAL-PERMISSIONS | LOW (latente) | **Nueva.** `get_user_permissions` (y por tanto `require_permission` y `/auth/me`) no filtra roles inactivos ni el estado del usuario; `authority.*` sí. Latente: no existe API para desactivar roles. La paridad UI/backend se mantiene porque ambos usan la misma función. Va al ciclo de identidad |
| OBS-TIME-01 | Observación | Desvío de reloj de ~1360 s en la corrida PostgreSQL de 02B, marcado NORMAL. Se investiga en el ciclo 03 (America/Caracas); no se toca aquí |
| AUDIT-EVENTS-WITHOUT-COMPANY, ROLE-CATALOG-INSTALLATION-WIDE, SHELL-SIDEBAR-NOT-RESPONSIVE y demás de §65 | — | Sin cambios |
