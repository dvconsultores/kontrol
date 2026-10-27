# SPEC 003 · Delta — SHARED-CORE-P0-HARDENING-02D · COMPANY READ-PERMISSION ENFORCEMENT

| Campo | Valor |
|---|---|
| Spec dueña | **003** (Usuarios / Roles / Alcance). Specs afectadas por el inventario: 002 (maestros), 003-inventario, 004, 005, 006, 007, 008-regulación, 009 (reportes), 011-homologación y 008 (estructura) |
| Deuda que cierra | **COMPANY-READS-WITHOUT-DECLARED-PERMISSION** (declarada en 02C, ADR-018; reclasificada HIGH / P0 por el encargo) |
| HEAD de entrada | `fb8ead1` (develop = origin/develop) |
| Evidencia | `evidence/read-permission-enforcement/` |
| Decisiones de la dueña | **OD-READ-01..06** (encargo 02D, ratificadas): toda lectura protegida exige la capacidad de vista declarada **y** alcance válido; autenticado o miembro de la empresa no basta; se usa la capacidad del módulo, sin un `business:read_all`; listas, detalle, búsqueda, selectores, agregados, conteos, tableros, vistas previas y descargas son lecturas; lo deliberadamente amplio se clasifica de forma explícita; ante la duda, **fail closed**. Se mantienen OD-DEL-10 (ADMIN técnico, FUNCIONAL_COMPLETO funcional), OD-DEL-12, ADR-017, ADR-018 y OD-UI-01 |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| DATABASE_CHANGE | NOT_APPLICABLE (§6) |
| NORMATIVE_RESEARCH | NOT_APPLICABLE (§4) |
| Estado | **IMPLEMENTED — CONVERGED — REQUIRED_SUITE_INVENTORY_COMPLETE = 1** (2026-10-27; autorizado por el encargo «SHARED-CORE-P0-HARDENING-02D»; convergencia en §19) |

## 1. Discover (medido en `fb8ead1`)

### 1.1 Cómo se autoriza hoy una lectura

| Pieza | Comportamiento medido |
|---|---|
| `require_permission(recurso, acción)` | Exige la capacidad en **alguna** empresa (`get_user_permissions`) y marca la ruta con `kontrol_permission` |
| `get_company_context` | Resuelve la empresa (404 si no hay acceso) y **solo** exige en ella las capacidades que la ruta declara (`_permisos_declarados`). Sin capacidad declarada, basta con acceder a la empresa |
| Ruta GET típica sin capacidad | `user: User = Depends(get_current_user), ctx = Depends(get_company_context)`: autenticado + acceso a la empresa |
| `catalogo_de_operaciones` (`/auth/operations`) | Publica, por operación, las capacidades declaradas y su alcance. Una lectura sin capacidad aparece con `capabilities: []` |

### 1.2 Inventario (READ_AUTHORIZATION_SURFACE_MATRIX)

Generado desde la aplicación real (recorrido de `app.routes` y de cada árbol de dependencias): **554 operaciones, 227 GET**.

| Situación de las 227 lecturas | Nº |
|---|---|
| COMPANY sin capacidad declarada | 113 (02C contó 112; la nueva es `/authority/company`) |
| COMPANY con capacidad declarada | 82 |
| GLOBAL con capacidad declarada | 16 |
| GLOBAL autenticadas sin capacidad | 11 |
| Públicas | 5 |

La matriz completa, ruta por ruta, está en `evidence/read-permission-enforcement/read-authorization-surface-matrix.md`:

| Resultado de la clasificación | Nº |
|---|---|
| Ganan capacidad (FIX_REQUIRED) | **111** (105 COMPANY y 6 GLOBAL) |
| Ya la declaraban | 98 |
| Sin capacidad, clasificadas y justificadas | 18 (5 PUBLIC_REFERENCE_DATA, 11 SELF_SCOPED_DATA, 1 AUTHENTICATED_GLOBAL_REFERENCE_DATA, 1 COMPANY_REFERENCE_DATA) |

**UNINVENTORIED_READ_SURFACES = 0**: el generador se detiene ante cualquier GET que no tenga clase.

Lecturas que no son GET: ninguna operación POST/PUT/DELETE sin capacidad devuelve datos de negocio. Son los flujos de la propia cuenta (`/auth/*`), las acciones de destinatario de notificaciones y tareas (CL-047-05) y `POST /inventory/balances/recompute`, una escritura que ya es la deuda INVENTORY-RECOMPUTE-UNGUARDED y no se absorbe. Sí leen datos de otros módulos la creación de exportaciones y la ejecución de trabajos de reporte (§17 «export preparation»): entran en AD-5.

### 1.3 Servicios y lecturas indirectas (§18, §19, §31, §32)

| Superficie | Hallazgo | Decisión |
|---|---|---|
| `reporting.dashboard` | Calcula totales de ventas, compras, banco, CxC, CxP, documentos fiscales, despachos bloqueados, partidas vencidas, períodos y permisos. Lo protege solo `get_current_user`. Y `dashboard:view` es **capacidad técnica de ADMIN** (OD-DEL-10): ADMIN sin negocio leería esas cifras en cuanto se exija solo `dashboard:view` | AD-4: cada indicador exige su capacidad de origen |
| `reporting.report(key)` | Vista previa de ventas, inventario, aging, libros fiscales y evaluaciones regulatorias. Lo reutilizan `create_export` (archivo real) y `run_job` | AD-5: capacidad del reporte en vista previa, exportación, trabajo y descarga |
| `GET /reporting/exports/{id}/download` | Devuelve el archivo real sin capacidad declarada | AD-5 |
| Documentos (Spec 046) | `_assert_can_read_file` exige la capacidad de vista de **alguna** entidad vinculada (`RESOURCE_KINDS`), y las descargas ya declaran `documentos:download` | NO-OP con prueba (las de Spec 046) |
| Notificaciones y tareas (Spec 047) | Fila de destinatario o candidato; los tipos de origen sin capacidad se excluyen (`catalogo.tipos_prohibidos`); `scope=all` exige `tareas:view`, con los permisos calculados en la empresa activa | NO-OP con prueba (CL-047-05) |
| Detalle por id | `_owned(...)` y comparaciones `company_id == ctx.company_id` (02B; `test_architecture_scope` lo vigila) | Se mantiene: 404 después de la capacidad |
| Selector de empresa `/organization/companies` | Solo las empresas a las que el usuario accede | SELF_SCOPED_DATA (regla 5 de 02C) |

### 1.4 Consumidores cruzados (§27, §37)

Lecturas de un módulo que consumen pantallas de otro (medido en el frontend):

| Lectura | Pantallas de otros módulos que la consumen |
|---|---|
| `/maestros/terceros` | Selector de cliente o proveedor en 14 pantallas de ventas, compras, tesorería, fiscal y regulatorio |
| `/treasury/currencies` | Listas de precio (comercial) |
| `/purchasing/receipts`, `/receipts/{id}/conciliacion`, `/receipts/{id}/confirmacion-inventario` | Confirmación de inventario |
| `/inventory/putaway/ubicaciones` | Preparación de pedidos (ventas) |
| `/regulatory/drivers`, `/regulatory/vehicles` | Despacho (ventas) |
| `/sales/collections`, `/purchasing/payments` | Ingresos y egresos (tesorería) |
| `/sales/invoices` | Emisión y notas (fiscal) |
| `/sales/shipments` | Evaluación (regulatorio) |

### 1.5 Causa raíz (§44, medida)

`get_company_context` hace cumplir **solo lo que la ruta declara**. Las 111 lecturas no declaran nada porque se escribieron con `get_current_user` como única dependencia de usuario. Es el supuesto implícito «quien está en la empresa puede leer». No hay un helper sin permiso compartido ni un repositorio genérico detrás: el defecto está en la declaración de cada ruta. Por eso la corrección es declarativa.

## 2. Reproducción (rojo, §43)

Se reproduce con pruebas en rojo escritas por DeepSeek (T01) antes de implementar: `evidence/read-permission-enforcement/rojo-backend.txt`.

## 3. Requisitos

| ID | Requisito | Origen |
|---|---|---|
| READ-FR-01 | **Lista**: sin la capacidad de vista del módulo, ninguna lista protegida devuelve datos: 403 `PERMISSION_DENIED` | OD-READ-01/04, §24 |
| READ-FR-02 | **Detalle por id**: exige la misma capacidad; conocer el id no da lectura (IDOR/BOLA); el objeto de otra empresa responde 404 | §25 |
| READ-FR-03 | **Búsqueda** (`/maestros/catalogos/items/search` y filtros): misma capacidad | §26 |
| READ-FR-04 | **Selectores**: la lectura de referencia exige la capacidad de su módulo dueño. No hay capacidad «de referencia» menor (AD-3) | §27, OD-READ-06 |
| READ-FR-05 | **Conteos y agregados** (aging, partidas abiertas, valorización, conciliación, triple match, contadores de libros): misma capacidad | §28 |
| READ-FR-06 | **Tablero**: `dashboard:view` da acceso al contenedor; cada indicador exige además la capacidad de su origen en la empresa activa. Sin ella, el indicador **no se calcula ni se devuelve** | §29, FR-009-021, GOV-CTL-004 |
| READ-FR-07 | **Vista previa de reporte**: `reportes:view` más la capacidad del reporte | §30 |
| READ-FR-08 | **Descarga**: la de una exportación exige `reportes:export` más la capacidad del reporte exportado. Los documentos mantienen la regla de Spec 046 | §32 |
| READ-FR-09 | **Preparación de exportación** (crear exportación, crear y ejecutar trabajo): la capacidad del reporte, además de `reportes:export` | §17 |
| READ-FR-10 | **Alcance de empresa**: la capacidad tiene que valer en la empresa activa. Solo en otra empresa → 403 `COMPANY_SCOPE_FORBIDDEN`. Empresa sin acceso, de otro tenant o inexistente → 404 `COMPANY_NOT_FOUND` | §22, 02B |
| READ-FR-11 | **Catálogos globales** (fuentes legales, versiones de reglas fiscales, homologación): la capacidad de vista del módulo, en alguna empresa del tenant (alcance GLOBAL, igual que la UI) | §21 |
| READ-FR-12 | **Clasificación**: toda lectura sin capacidad pertenece a una clase justificada de una lista cerrada | OD-READ-05 |
| READ-FR-13 | **Contrato de error y API directa**: (1) sin la capacidad en ninguna empresa → 403 `PERMISSION_DENIED`; (2) empresa sin acceso → 404; (3) capacidad solo en otra empresa → 403 `COMPANY_SCOPE_FORBIDDEN`; (4) objeto de otra empresa → 404. Nunca un 500. La denegación no devuelve datos | §23 |
| READ-FR-14 | **Paridad UI/API**: la UI pide la misma capacidad que el backend exige; no ofrece lecturas que el backend rechaza en su lectura principal | §37 |
| READ-FR-15 | **Completitud del catálogo**: una ruta GET nueva sin capacidad declarada y sin clase rompe la construcción | §46, §47 |

## 4. Investigación normativa

NORMATIVE_RESEARCH = **NOT_APPLICABLE**. Es control de acceso del núcleo compartido. Ninguna fuente legal venezolana fija qué capacidad de software autoriza leer un listado. No se inventan obligaciones.

## 5. Modelos de proceso, dominio y UX

- **Proceso.** No cambia ningún flujo de negocio. Cambia quién puede ver: el que tiene la capacidad de vista del módulo en la empresa activa.
- **Dominio.** Las capacidades ya existen todas en `CATALOGO_DE_PERMISOS`: `fiscal:view`, `inventario:view`, `maestros:view`, `organization:view`, `compras:view`, `regulatorio:view`, `ventas:view`, `tesoreria:view`, `homologacion:view`, `reportes:view`, `reportes:export`, `dashboard:view` y `audit:view`. **No se crea ninguna** (OD-READ-03).
- **UX.** Se mantiene 02C:
  - Una lectura denegada en la pantalla principal pinta la denegación sin pedir datos.
  - Un control no autorizado se oculta.
  - Un selector cuya lectura de referencia se deniega muestra el error de la API, sin datos (AD-3).

## 6. Datos y base de datos

**DATABASE_CHANGE = NOT_APPLICABLE.**
- No se crea ninguna tabla, columna, índice ni migración.
- Las capacidades ya están sembradas por `_bootstrap_roles` en toda instalación.
- Las consultas siguen filtrando por `ctx.company_id`.
- La decisión de capacidad se toma **antes** de consultar los datos, porque es una dependencia de la ruta: una denegación no ejecuta la consulta de negocio (§55).

## 7. Diseño

### AD-1 · Declaración explícita por ruta, con la primitiva existente

Cada lectura protegida declara su capacidad con `require_permission(recurso, "view")` en lugar de `get_current_user`. No se construye un marco nuevo (§45): la ruta dice su contrato y `get_company_context` lo hace cumplir en la empresa activa (02B).

| Orden de evaluación (FastAPI resuelve las dependencias por orden) | Resultado |
|---|---|
| 1. `require_permission`: la capacidad no está en ninguna empresa | 403 `PERMISSION_DENIED` (no revela si la empresa existe) |
| 2. `get_company_context`: empresa sin acceso, de otro tenant o inexistente | 404 `COMPANY_NOT_FOUND` |
| 3. `get_company_context`: la capacidad no vale en esta empresa | 403 `COMPANY_SCOPE_FORBIDDEN` (y evento `COMPANY_SCOPE_DENIED`, como en 02B) |
| 4. Cuerpo: objeto de otra empresa | 404 del recurso |

En las rutas GLOBAL (sin `get_company_context`) solo aplica el paso 1, igual que en sus escrituras.

### AD-2 · Capacidad del dueño funcional

Por defecto, la capacidad del módulo de la API. Excepción medida: `GET /purchasing/receipts/{id}/conciliacion` y `GET /purchasing/receipts/{id}/confirmacion-inventario` sirven a la confirmación de inventario (Spec 021; su escritura exige `inventario:confirm`). Por eso exigen `inventario:view`.

### AD-3 · Selectores entre módulos: fail closed

No se introduce semántica «cualquiera de» ni una capacidad de referencia nueva:
- Romperían la regla «todas las capacidades declaradas», que el resolvedor de la UI y el mutante R6 de 02C fijan.
- La dueña pidió no crear una capacidad amplia (OD-READ-03).

Un rol que vende y necesita elegir clientes incluye `maestros:view`. FUNCIONAL_COMPLETO ya las tiene todas.

La consecuencia queda registrada como deuda **CROSS-MODULE-SELECTOR-COMPOSITION** (LOW, §14): un rol parcial ve el error de la API en el selector. Una capacidad de consulta mínima exigiría una decisión de la dueña.

### AD-4 · Tablero por indicador

`GET /reporting/dashboard` exige `dashboard:view` (el contenedor). El servicio recibe las capacidades del usuario en la empresa activa: `capabilities_in_company`, una sola consulta. Calcula y devuelve solo los indicadores cuya capacidad de origen tiene:

| Clave | Capacidad de origen |
|---|---|
| `indicators.ventas`, `indicators.cxc` | `ventas:view` |
| `indicators.compras`, `indicators.cxp` | `compras:view` |
| `indicators.tesoreria_banco` | `tesoreria:view` |
| `indicators.documentos_fiscales`, `vencimientos.periodos_fiscales_abiertos` | `fiscal:view` |
| `indicators.despachos_bloqueados`, `vencimientos.permisos_activos` | `regulatorio:view` |
| `vencimientos.open_items_vencidos` | `ventas:view` **y** `compras:view` (mezcla cobrar y pagar; no se cambia su semántica) |

Con esta regla, ADMIN (técnico, con `dashboard:view`) recibe `indicators: {}` y `vencimientos: {}` (GOV-CTL-004).

### AD-5 · Reportes, exportaciones y descargas

`CAPACIDADES_DE_REPORTE` (en `reporting/service.py`) es la única tabla de clave de reporte → capacidades de origen:

| Clave | Capacidades de origen |
|---|---|
| `executive_ventas` | `ventas:view` |
| `operational_inventario` | `inventario:view` |
| `financial_aging` | `ventas:view`, `compras:view` |
| `fiscal_libros_*` | `fiscal:view` |
| `regulatory_evaluaciones` | `regulatorio:view` |

`capacidades_de_reporte(key)` devuelve las capacidades, o lanza 404 `REPORT_NOT_FOUND` si la clave no existe: las claves no son secretas.

Nuevo helper `authority.require_capability(db, *, user, capability, company_id)`, con el mismo orden que AD-1:
1. Si la capacidad no está en ninguna empresa: 403 `PERMISSION_DENIED`.
2. Si lo está, pero no en esta empresa: `require_capability_in_company`, que responde 403 `COMPANY_SCOPE_FORBIDDEN` y registra el evento.

Rutas:

| Ruta | Exige |
|---|---|
| `GET /reports/{key}` | `reportes:view` + las de la clave |
| `GET /exports`, `/jobs`, `/jobs/{id}` | `reportes:view` (solo metadatos) |
| `GET /exports/{id}/download` | `reportes:export` + las de `export.report_key` |
| `POST /exports`, `POST /jobs` | `reportes:export` + las de la clave del cuerpo |
| `POST /jobs/{id}/run` | `reportes:export` + las de `job.report_key` (se carga el trabajo de la empresa antes de ejecutarlo) |

### AD-6 · Auditoría y seguridad

- `GET /reporting/audit/timeline` exige `audit:view` (§34, en la empresa activa, como `/audit/events` en 02B).
- La pantalla `reportes/auditoria` pasa a exigir `audit:view`.
- Las denegaciones se auditan según la política vigente (§57): `COMPANY_SCOPE_DENIED` con capacidad y empresa, sin carga del registro. `PERMISSION_DENIED` sigue sin evento propio, como en 02B.

### AD-7 · Clasificación cerrada y puerta de completitud

`tests/test_read_catalog_completeness.py` guarda `LECTURAS_SIN_CAPACIDAD`: las 18 rutas, con su clase y motivo. La prueba falla si:
- un GET no declara capacidad y no está en la lista;
- una entrada de la lista ya no existe;
- una entrada de la lista declara capacidad.

Es la misma forma que `_SIN_CONTEXTO_JUSTIFICADO` (02B).

### AD-8 · UI (02C se mantiene; solo cambia lo que exige el nuevo contrato)

| Pantalla | Cambio |
|---|---|
| `DashboardPage` | Pide el tablero solo con `tiene("dashboard:view", "empresa")`; pinta solo los indicadores presentes. En los tipos, los indicadores pasan a ser opcionales |
| `CentroReportesPage` | Cada reporte declara sus capacidades (las de AD-5). Las categorías se filtran con `tiene(..., "empresa")`; solo se pide el reporte permitido; sin ninguno, estado vacío |
| `ExportacionesPage` | El botón de descarga se oculta sin `puede("GET", "/reporting/exports/_/download")` |
| `pantallas.ts` | `reportes/auditoria` → `audit:view` |
| Instantánea `operaciones.json` | Se regenera con `qa/fixtures_de_frontend.py` (generador, sin contenido de Claude) |

### AD-9 · Rendimiento

FastAPI resuelve `get_current_user` una vez por petición. Cada lectura añade lo mismo que ya pagaban sus escrituras:
- `get_user_permissions`;
- `effective_scope`, una sola vez por capacidad.

Se miden los presupuestos de consultas existentes en PostgreSQL; no se cambia ningún umbral (§56).

### AD-10 · OpenAPI

`require_permission` depende de `get_current_user`, así que la seguridad publicada no cambia. No se añaden parámetros ni esquemas. Deriva esperada: ninguna o solo descriptiva; se mide (§33).

## 8. Modelo de amenazas (§59)

| Amenaza | Control | Requisito | Prueba |
|---|---|---|---|
| Autenticado sin capacidad lee | AD-1 | READ-FR-01/02 | RPE-01..04 |
| Lectura cruzada de empresa | AD-1 paso 3 | READ-FR-10 | RPE-05 |
| Otro tenant / empresa inexistente | AD-1 paso 2 | READ-FR-10/13 | RPE-06 |
| IDOR/BOLA (id conocido) | AD-1 + `_owned` | READ-FR-02 | RPE-02 y RPE-07 |
| Fuga por lista, búsqueda, selector o conteo | AD-1 | READ-FR-01/03/04/05 | RPE-01, 03, 04 |
| Fuga por agregado o tablero | AD-4 | READ-FR-05/06 | RPE-08, RPE-09 |
| Fuga por vista previa de reporte | AD-5 | READ-FR-07 | RPE-10 |
| Fuga por descarga o preparación de exportación | AD-5 | READ-FR-08/09 | RPE-11 |
| Recurso anidado (adjuntos) | Spec 046 | READ-FR-08 | pruebas de Spec 046 (NO-OP) |
| ADMIN técnico lee negocio | AD-1 + AD-4 | GOV-CTL-004 | RPE-09, RPE-12, READ-E2E-05 |
| FUNCIONAL_COMPLETO en otra empresa | AD-1 paso 3 | RNF-GOV-012 | RPE-05, READ-E2E-06 |
| Cabecera de empresa manipulada | 02B (`resolve_company`) | READ-FR-10 | RPE-06 |
| Ruta nueva sin clasificar | AD-7 | READ-FR-15 | gate + mutante M-CAT |
| Salto por API directa | AD-1 (el backend decide) | RNF-GOV-006 | READ-E2E-03 |

## 9. Gate de la Constitución

| Principio | Resultado |
|---|---|
| P1/P2 (Spec y autorización) | PASS: delta en la Spec dueña, autorizado por el encargo que lo nombra |
| P6 (seguridad en backend) | PASS: el backend decide; la UI solo proyecta |
| P7 (multiempresa) | PASS: capacidad × empresa (02B) |
| P10 (pruebas antes) | PASS: T01 y T02 en rojo antes de implementar |
| P12 (ADR) | PASS: ADR-019 (T22) |
| P13 (trazabilidad) | PASS: §11 |
| P21 (sin respaldos silenciosos) | PASS: fail closed |
| P27 (evidencia) | PASS: `evidence/read-permission-enforcement/` |

Resultados del gate: BLOCKER, CRITICAL, CONTRADICTIONS y OWNER CONFLICT = 0; MATERIAL OQ = 0 (AD-3 es clasificación por módulo dueño, §14 del encargo); UNKNOWN = 0.

## 10. Tareas

Todas: EXECUTOR DEEPSEEK, SECURITY_SENSITIVE sí, EGRESS_SAFE sí y RETRY_MAX 2.

| Tarea | Modelo | Ficheros | Contenido | DONE_WHEN |
|---|---|---|---|---|
| T01 | pro | `tests/test_read_permission_enforcement.py` (nuevo) | Rojo RPE-01..12 | En rojo por la causa del ciclo antes de T03; en verde después |
| T02 | pro | `tests/test_read_catalog_completeness.py` (nuevo) | Puerta AD-7 | Roja con las 111; verde tras T03..T14 |
| T03..T11 | flash | `fiscal`, `inventory`, `master_data`, `organization`, `purchasing`, `regulatory`, `sales`, `treasury` y `homologation` (`api.py`) | AD-1/AD-2, un módulo por llamada | Sus rutas declaran la capacidad de la matriz |
| T12 | pro | `identity_access/authority.py` + prueba | `require_capability` | Prueba de orden de errores |
| T13 | pro | `reporting/service.py` | `CAPACIDADES_DE_REPORTE`, `capacidades_de_reporte`, tablero por indicador | RPE-08..10 |
| T14 | pro | `reporting/api.py` | AD-5 y AD-6 en las rutas | RPE-09..11 |
| T15..T18 | flash/pro | `DashboardPage.tsx`, `types.ts`, `CentroReportesPage.tsx`, `ExportacionesPage.tsx`, `pantallas.ts` | AD-8 | vitest + tsc |
| T19 | flash | pruebas vitest de T15..T18 | AD-8 | Verdes |
| T20 | flash/pro | Pruebas del backend afectadas | Dar al actor de la prueba la capacidad de vista que la lectura ahora exige, sin debilitar aserciones | Suites completas verdes |
| T21 | pro | `e2e/read-permission.spec.ts` (nuevo) | READ-E2E-01..08 | 3 navegadores |
| T22 | flash | `adr/ADR-019.md`, `contracts/api-contracts.md` | Documentación de producto | Revisada |

## 11. Trazabilidad

| Requisito de ingeniería (Gobierno) | Requisito | Clase de dato | Capacidad | Alcance | Ruta / servicio | UI | Prueba |
|---|---|---|---|---|---|---|---|
| RNF-GOV-006 | READ-FR-01..05, 13 | COMPANY_PROTECTED_DATA | `<módulo>:view` | empresa | 105 rutas COMPANY (matriz) | registro de pantallas | RPE-01..07, READ-E2E-02/03 |
| RNF-GOV-012 | READ-FR-10, 11 | COMPANY / GLOBAL | idem | empresa / global | AD-1 | `tiene(…, alcance)` | RPE-05, READ-E2E-04/06 |
| GOV-CTL-004 | READ-FR-06 | COMPANY_PROTECTED_DATA | origen por indicador | empresa | `dashboard` | `DashboardPage` | RPE-09, READ-E2E-05 |
| GOV-CTL-005 | AD-6 | SECURITY_SENSITIVE_DATA | `audit:view` | empresa | `/reporting/audit/timeline` | `reportes/auditoria` | RPE-12 |
| RNF-GOV-009 | READ-FR-07..09 | COMPANY_PROTECTED_DATA | `reportes:*` + origen | empresa | `report`, exportaciones, trabajos | Centro, Exportaciones | RPE-10/11 |
| RNF-GOV-005 | AD-6 | evento de seguridad | — | empresa | `require_capability_in_company` | — | RPE-05 (evento) |
| E2E-06 (hostil multi-ente, futuro) | READ-FR-10 | — | — | empresa (el ente sigue siendo futuro) | AD-1 | — | READ-E2E-04/06 |
| — (OD-READ-05) | READ-FR-12, 15 | 18 clasificadas | — | — | `LECTURAS_SIN_CAPACIDAD` | — | T02 |
| — (§37) | READ-FR-14 | — | — | — | — | AD-8 | vitest, `authority-surfaces`, READ-E2E-08 |

## 12. Inventario de suites obligatorias (antes de implementar)

| RS | Suite | Orden |
|---|---|---|
| RS-01 | Dirigidas y negativas del ciclo (RPE, puerta) | `pytest tests/test_read_permission_enforcement.py tests/test_read_catalog_completeness.py` |
| RS-02 | Backend PostgreSQL completo con analizador | `qa/suite_tiempos.py --motor postgres --con-analizador` |
| RS-03 | Backend SQLite completo con analizador | `qa/suite_tiempos.py --motor sqlite --con-analizador` |
| RS-04 | vitest | `vitest run` |
| RS-05 | tsc | `tsc -b --noEmit` |
| RS-06 | eslint | `eslint --max-warnings 0 .` |
| RS-07 | build | `vite build` |
| RS-08 | E2E del ciclo en 3 navegadores | `qa/e2e-run.py --con-analizador -- read-permission.spec.ts --project=…` |
| RS-09 | Regresión E2E: alcance + delegación + UI-SCOPE (78) | `qa/e2e-run.py -- company-scope delegation-ceiling ui-company-scope` (3 navegadores) |
| RS-10 | E2E canónica (339 + las del ciclo) | `qa/e2e-run.py --con-analizador` |
| RS-11 | Mutaciones del ciclo y regresión de alcance, delegación y UI | herramientas de Claude, fuera del árbol |
| RS-12 | OpenAPI | comparación antes/después |
| RS-13 | ruff y mypy de los ficheros tocados | `ruff check`, `mypy` (sin errores nuevos) |
| RS-14 | Cabeza de Alembic, residuos y secretos | `alembic heads`, barrido |
| RS-15 | Base después de la E2E | bases efímeras eliminadas; denegaciones sin mutaciones |

## 13. Revisión de pantallas (Screen / Form)

`evidence/read-permission-enforcement/screen-form-completeness.md`.

## 14. Deuda

| ID | Spec | Categoría | Severidad | Evidencia | Impacto | Bloquea | Siguiente acción |
|---|---|---|---|---|---|---|---|
| CROSS-MODULE-SELECTOR-COMPOSITION | 003 | RBAC / UX | LOW | §1.4, AD-3 | Un rol parcial sin la vista del módulo de referencia ve un error en el selector | No | Decidir con la dueña si se crea una capacidad de consulta mínima |
| REPORT-EXPORT-DOWNLOAD-ANCHOR | 009 | UI | MEDIUM (preexistente) | `ExportacionesPage.downloadExport` usa un `<a href>` que no envía el token de acceso | La descarga desde la UI no puede autenticarse (falla cerrada, 401) | No | Ciclo de reportes: descargar con `apiFetch` como blob |

Se mantienen, sin absorber:
- AUDIT-EVENTS-WITHOUT-COMPANY, ROLE-STATUS-NOT-IN-GLOBAL-PERMISSIONS, ROLE-CATALOG-INSTALLATION-WIDE y ROLE-CREATE-UI-MISSING;
- USER-LIFECYCLE-API-MISSING, ROLES-FORM-FIXED-WIDTHS, SHELL-SIDEBAR-NOT-RESPONSIVE y OBS-DEL-E2E-401-PARALELO;
- PASSWORD-RESET-OOB-CHANNEL-MISSING, ADMIN-PASSWORD-RESET-WEB-MISSING y GENERIC_LOGIN_RATE_LIMIT_DEBT;
- APPROVAL-CANCEL-WITHOUT-REQUESTER-CHECK, INVENTORY-RECOMPUTE-UNGUARDED, APPLY-SOURCE-STATUS-UNCHECKED, REGULATORY-DOCUMENT-SELF-VALID y ALEMBIC-CHECK-DRIFT-PREEXISTING;
- la observación OBS-TIME-01, que pasa al ciclo 03.

## 15. Tareas añadidas durante la ejecución

| Tarea | Motivo | Resultado |
|---|---|---|
| T12r1, T13r1/r2 (división), T15r1, T16b r1, T21b r1 | Rechazos de auditoría (ver `orchestration.md`) | PASS |
| T16a | Paridad UI/API: la instantánea `operaciones.json` incluye `report_capabilities` | PASS; CR-04 la verifica |
| T19a | NAV-07: con `audit:view` el menú tiene dos «Auditoría» (consecuencia de AD-6) | PASS |
| T19b | Falsos verdes de temporización en DSH-03 y READ-E2E-05 (mutante F02) | PASS; F02 muere |
| T20 | `test_reporting.py` al nuevo contrato obligatorio del tablero | PASS |
| T-M1 | RPE-16: los trabajos de reporte (mutantes B12/B13) | PASS; B12/B13 mueren |
| T21b, T21c | READ-E2E-09 (320 px, axe); excluye solo la deuda del `<main>` del shell | PASS |
| T16c | Contraste AA de la cabecera de la tabla del Centro (axe en READ-E2E-09) | PASS |
| T15b | Claves de lista en Inicio (aviso de React, crawler canónico) | PASS |

## 16. Resultados (árbol final)

| Suite | Resultado | Corrida |
|---|---|---|
| Dirigidas y negativas (RPE-01..16, puerta, RCA, reporting, instantáneas) | 43/43 PostgreSQL · 43/43 SQLite | — |
| Backend PostgreSQL completo con analizador | **3536/0** (18 omitidas; 3511 + 25 del ciclo); desvío de reloj 0,1 s, NORMAL | r20261027t190518p280385nee80fb |
| Backend SQLite completo con analizador | **2472/0** (1082 omitidas, solo PostgreSQL; 2447 + 25) | r20261027t194947p637077nb911ca |
| vitest | **625/625** (54 ficheros) | — |
| tsc · eslint · build | 0 · 0 · OK | — |
| E2E del ciclo READ-E2E-01..09, Chromium + Firefox + WebKit | **27/27** | r20261027t202638p858543nd407c7 |
| Regresión E2E: alcance + delegación + UI-SCOPE, 3 navegadores | **78/78** | r20261027t201036p783140nd438d9 |
| E2E canónica con analizador | **348/348** (339 + 9), sin omitidas | r20261027t202012p830414n1d7f9c |
| Mutaciones | 91 en total: 89 muertas, 2 equivalentes demostradas (F04, P1), **0 supervivientes de comportamiento** | `mutaciones.md` |
| OpenAPI | 420 → 420 rutas; 0 operaciones ni esquemas cambiados | `openapi.md` |
| ruff · mypy | Limpio · 154 errores en `app`, los mismos de la línea base (ninguno nuevo) | — |
| Alembic | Cabeza única `0060_spec003_admin_split`; DATABASE_CHANGE = NOT_APPLICABLE | — |
| Base después de la E2E | Bases efímeras eliminadas (0 huérfanas); las denegaciones son GET sin efectos; limpieza LIMPIA en las 6 corridas | — |
| Residuos y secretos | 37 ficheros del ciclo, 0 alertas; 0 `.mutbak`; puertos 8000/5173 libres | — |

**Cumplimiento: navegadores.** Chromium, Firefox y WebKit. **Safari real: NOT MEASURED** (WebKit no es Safari).

## 17. Relectura de cierre del documento de Gobierno

Releído `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` (SHA-256 `8f86615f…`, el mismo que al inicio). La línea base `9a41503` no tiene cambios en `requerimientos/gobierno/`.

| Pregunta del encargo (§88) | Respuesta |
|---|---|
| ¿Están cubiertos los requisitos de autorización de lectura aplicables? | Sí: RNF-GOV-006 (backend), RNF-GOV-012 (capacidad × alcance), GOV-CTL-004 (ADMIN sin cifras de negocio), GOV-CTL-005 (`audit:view`), RNF-GOV-009 (reportes con su capacidad de origen) y RNF-GOV-005 (COMPANY_SCOPE_DENIED auditado) |
| ¿Toda lectura protegida tiene capacidad y alcance? | Sí: 209 de 227 GET declaran capacidad; las 18 restantes están clasificadas y la puerta lo impone |
| ¿Algún requisito implica una superficie de lectura que falte? | No. GOV-CTL-007 (reportes de rendición) y E2E-06 entre entes son del módulo de Gobierno, futuro |
| ¿Queda dato accesible por API directa? | No: READ-E2E-03/07 y RPE-01..16 |
| ¿Se conservan los límites del administrador técnico? | Sí (RPE-09/15, READ-E2E-05) |
| ¿El aislamiento de entes de Gobierno sigue siendo futuro? | Sí. GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0, GOVERNMENT_SPEC_STARTED = 0, GOV0_STARTED = 0 |

**Métricas de la relectura:**
- ENGINEERING_REQUIREMENTS_REVIEWED = 1;
- RECONCILED = 1;
- APPLICABLE_REQUIREMENTS_COVERAGE = 100 %;
- UNEXPLAINED_REQUIREMENT_OMISSIONS = 0;
- FUNCTIONALITY_ACCIDENTALLY_OMITTED = 0.

## 18. Deuda nueva al cierre

| ID | Spec | Categoría | Severidad | Evidencia | Impacto | Bloquea | Siguiente acción |
|---|---|---|---|---|---|---|---|
| SHELL-MAIN-SCROLL-REGION-NOT-FOCUSABLE | 001 (shell) | Accesibilidad | MEDIUM (preexistente) | axe `scrollable-region-focusable` sobre el `<main>` de AppShell a 320 px (READ-E2E-09) | Teclado: el área con scroll no recibe foco | No | Ciclo del shell, junto a SHELL-SIDEBAR-NOT-RESPONSIVE |
| TABLE-HEADER-CONTRAST-AA | 001/varias | Accesibilidad | LOW (preexistente) | `thead bg-surface-100 text-text-500` con contraste 4,34:1 en ProductoNuevo, Libros y MfaAlta (corregido en el Centro, T16c) | WCAG 1.4.3 | No | Ciclo de accesibilidad |

Se mantienen las de §14: CROSS-MODULE-SELECTOR-COMPOSITION (LOW) y REPORT-EXPORT-DOWNLOAD-ANCHOR (MEDIUM).

**COMPANY-READS-WITHOUT-DECLARED-PERMISSION: CLOSED.**

## 19. Convergencia

El guion de prerrequisitos de Spec Kit resuelve la feature activa a `specs/012-auditoria-integral-e2e`, sin `spec.md` ni `plan.md`, así que el comando formal no puede converger este delta. Se hizo la convergencia equivalente (§90 del encargo), con el delta como fuente de intención.

| Ámbito | Elementos | Evidencia | Hallazgos |
|---|---|---|---|
| Requisitos | READ-FR-01..15 | Catálogo final: 209/227 GET con capacidad y 18 clasificadas; RPE-01..16, puerta, RCA y READ-E2E-01..09 en verde | 0 |
| Diseño | AD-1..AD-10 | Capacidades exactas de las rutas especiales (AD-2/5/6); tablero con `capacidades` obligatorio (AD-4); tabla y helper de reportes en sus 5 puntos (AD-5); 4 cambios de UI (AD-8); OpenAPI sin deriva (AD-10) | 0 |
| Tareas | §10 (22) y §15 (13) | Todas aplicadas, auditadas y probadas | 0 |
| Constitución | 8 principios de §9 | PASS | 0 |

Hallazgos por tipo:
- missing 0;
- partial 0;
- contradicts 0;
- unrequested 0.

T16c y T15b nacen de fallos medidos en pantallas afectadas (§77) y están registradas en §15.

**Resultado: CONVERGED.** `specs/001-fundacion/tasks.md` queda sin cambios.
