# MATRIZ DE TRAZABILIDAD — ARCH-MC-001

Derivada por script de `spec.md`, `tasks.md` y `acceptance-criteria.md`.

## 1. Cobertura

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 50 |
| Requisitos no funcionales | 8 |
| Criterios de aceptación | 66 |
| Tareas | 103 |
| **FR sin tarea ni criterio** | **0** |
| **NFR sin tarea ni criterio** | **0** |
| **Criterios sin tarea** | **0** |
| **Tareas sin requisito** | **0** |

## 2. Requisito funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| FR-MC-001 | `tenant_id` significa siempre `Tenant.id`; `company_id`, `Company.id`; `bran | T-MC-001 |
| FR-MC-002 | Ninguna columna puede nombrar una entidad y almacenar otra | T-MC-001 |
| FR-MC-003 | Toda entidad persistente declara su alcance: `GLOBAL`, `INSTALLATION`, `TENA | T-MC-002, T-MC-033 |
| FR-MC-004 | No existe `UNKNOWN_SCOPE`: las 166 tablas quedan clasificadas | T-MC-003 |
| FR-MC-005 | Una entidad `DERIVED` alcanza su empresa por una ruta **obligatoria, determi | T-MC-004, T-MC-034 |
| FR-MC-006 | El objetivo no es poner `company_id` en 82 tablas, sino que 133 entidades de | T-MC-004 |
| FR-MC-010 | Existe un `CompanyContext` por petición con tenant, empresa, usuario y alcan | T-MC-010 |
| FR-MC-011 | El frontend **propone** la empresa; el backend la **valida**: existe, es del | T-MC-011, T-MC-090 |
| FR-MC-012 | Manipular el almacenamiento del navegador no da acceso a otra empresa | T-MC-138 |
| FR-MC-013 | Con una sola empresa autorizada, se resuelve automáticamente y no se pide el | T-MC-012, T-MC-092 |
| FR-MC-014 | Con varias, hay selector inequívoco y la empresa activa está siempre visible | T-MC-091 |
| FR-MC-015 | Dos pestañas pueden operar en empresas distintas sin contaminarse | T-MC-094 |
| FR-MC-016 | El contexto no reintroduce la carrera de `/auth/refresh` cerrada en `REM-AUT | T-MC-020 |
| FR-MC-017 | El cierre de sesión limpia contexto, pista de empresa y cachés de empresa | T-MC-095 |
| FR-MC-018 | Perder el acceso a una empresa con la sesión viva invalida el contexto en la | T-MC-017 |
| FR-MC-019 | Los trabajos sin petición HTTP se ejecutan bajo un contexto explícito, nunca | T-MC-019 |
| FR-MC-020 | Toda consulta sobre entidad de empresa se acota en el **backend**, no por fi | T-MC-035, T-MC-060, T-MC-061 |
| FR-MC-021 | Un listado nunca devuelve filas de otra empresa esperando que el cliente fil | T-MC-060, T-MC-076 |
| FR-MC-022 | Leer un recurso de otra empresa responde **404**, sin confirmar existencia | T-MC-077 |
| FR-MC-023 | Escribir no acepta `company_id` del cliente distinto del contexto validado | T-MC-078, T-MC-096 |
| FR-MC-024 | En entidades de empresa, `company_id` no es asignable en masa | T-MC-079 |
| FR-MC-025 | Ningún servicio asigna `actor.tenant_id` a una propiedad llamada `company_id | T-MC-030 |
| FR-MC-030 | Pertenecer al tenant **no** concede acceso a todas sus empresas | T-MC-014 |
| FR-MC-031 | El acceso se expresa con la estructura existente de la Spec 003; no se crea  | T-MC-014, T-MC-021 |
| FR-MC-032 | El permiso y el alcance son cosas distintas: `ventas:view` en la empresa A n | T-MC-015 |
| FR-MC-033 | El alcance por sucursal sigue vigente y convive con el de empresa | T-MC-016 |
| FR-MC-034 | El límite de empresas lo impone el **backend** según los derechos de la lice | T-MC-022 |
| FR-MC-035 | El esquema es multiempresa aunque el plan sea de una sola: la licencia limit | T-MC-023 |
| FR-MC-040 | Toda operación de empresa permite reconstruir tenant, empresa, usuario, acci | T-MC-075 |
| FR-MC-041 | Un evento de empresa transporta la empresa real, no el tenant | T-MC-075 |
| FR-MC-050 | Patrón `EXPAND → BACKFILL → VERIFY → SWITCH → CONSTRAIN → CONTRACT`; nunca u | T-MC-043, T-MC-058, T-MC-107, T-MC-112 |
| FR-MC-051 | Cada fila heredada se clasifica `MC-A`..`MC-E`; **no se inventa empresa** | T-MC-042, T-MC-051, T-MC-052 |
| FR-MC-052 | El determinismo se demuestra sobre el **intervalo** relevante, no sobre el n | T-MC-050 |
| FR-MC-053 | Un crítico no reconstruible **detiene** la migración final; no hay valor por | T-MC-055 |
| FR-MC-054 | El valor heredado se conserva hasta verificar | T-MC-040 |
| FR-MC-055 | Existe un mecanismo auditable de resolución manual: quién, cuándo, con qué e | T-MC-056 |
| FR-MC-056 | La migración no altera importes, cantidades, bases imponibles ni números de  | T-MC-057 |
| FR-MC-057 | Ninguna columna doble sobrevive sin fase de retirada declarada | T-MC-110, T-MC-111 |
| FR-MC-058 | Un informe previo, **sin escribir**, muestra el recuento por clase antes de  | T-MC-054 |
| FR-MC-060 | Si la columna se llama `company_id`, hay FK real a `companies`; si `tenant_i | T-MC-031, T-MC-032, T-MC-041, T-MC-100 |
| FR-MC-061 | La integridad la garantiza PostgreSQL cuando puede, no solo el servicio | T-MC-101 |
| FR-MC-062 | Los índices únicos con alcance se revisan uno a uno: pasar de tenant a empre | T-MC-102 |
| FR-MC-063 | Las secuencias fiscales se acotan según la normativa, no por comodidad | T-MC-062, T-MC-103 |
| FR-MC-070 | La Spec 008 no se rompe: es la referencia positiva | T-MC-140 |
| FR-MC-071 | La Spec 045 mantiene su empresa real; no se degrada a tenant | T-MC-126 |
| FR-MC-072 | `ResourceKind` de la Spec 046 declara `scope_kind` y su resolutor **explícit | T-MC-120 |
| FR-MC-073 | Tras normalizar, los 19 tipos registrados se prueban y `STILL_BLOCKED_BY_046 | T-MC-122, T-MC-124 |
| FR-MC-074 | La Spec 011 conserva intacta su semántica de conversión | T-MC-140 |
| FR-MC-080 | Ninguna entidad nueva introduce `tenant_id`, `company_id` o `branch_id` sin  | T-MC-005 |
| FR-MC-081 | Toda Spec futura que cree datos de empresa incluye **dos empresas del mismo  | T-MC-006 |

## 3. Requisito no funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| NFR-MC-01 | Aceptación sobre **PostgreSQL 18.x** real; SQLite no es evidencia final | T-MC-142 |
| NFR-MC-02 | Acotar por empresa no degrada el plan de consulta: índices revisados con `EX | T-MC-104 |
| NFR-MC-03 | Toda caché de empresa lleva la empresa en su clave | T-MC-080 |
| NFR-MC-04 | Las claves de idempotencia no colisionan entre empresas | T-MC-081 |
| NFR-MC-05 | El selector cumple WCAG 2.2 AA y es operable con teclado | T-MC-097 |
| NFR-MC-06 | Sin desbordamiento horizontal entre 320 y 1440 | T-MC-097 |
| NFR-MC-07 | Cross-browser en Chromium, Firefox y WebKit | T-MC-139 |
| NFR-MC-08 | La migración se ejecuta por fases con recuperación entre ellas | T-MC-043 |

## 4. Criterio → tarea

| Criterio | Enunciado | Tareas |
|---|---|---|
| AC-MC-01 | Toda columna `company_id` tiene FK a `companies`; toda `tenant_id`, a `tenan | T-MC-031, T-MC-101 |
| AC-MC-02 | Los 166 modelos declaran alcance; `test_all_persistent_models_have_declared_ | T-MC-033 |
| AC-MC-03 | Ninguna entidad derivada depende de una FK anulable | T-MC-034 |
| AC-MC-04 | `grep` de `company_id=actor.tenant_id` en entidades de empresa devuelve **0* | T-MC-030 |
| AC-MC-10 | Con cabecera válida, el contexto se resuelve y la operación ocurre en esa em | T-MC-011 |
| AC-MC-11 | `UA` con una sola empresa y sin cabecera: se resuelve sola | T-MC-012 |
| AC-MC-12 | `UAB` sin cabecera: **400 `COMPANY_CONTEXT_REQUIRED`**. No se adivina | T-MC-013 |
| AC-MC-13 | `UA` pidiendo la empresa B: **404**, sin confirmar existencia | T-MC-013 |
| AC-MC-14 | `UC` pidiendo A: **404** | T-MC-013 |
| AC-MC-15 | Empresa desactivada: **409 `COMPANY_INACTIVE`** | T-MC-018 |
| AC-MC-16 | `UAB` pierde acceso a B con la sesión viva: la siguiente operación en B da * | T-MC-017 |
| AC-MC-17 | Manipular el valor guardado en el navegador **no** da acceso | T-MC-138 |
| AC-MC-18 | Dos pestañas en A y B operan sin contaminarse | T-MC-094 |
| AC-MC-19 | Cerrar sesión limpia contexto, pista y cachés | T-MC-095 |
| AC-MC-20 | Un trabajo sin contexto explícito **falla**; no toma uno por defecto | T-MC-019 |
| AC-MC-30 | Un listado con contexto A **no** contiene filas de B, y viceversa | T-MC-076, T-MC-132 |
| AC-MC-31 | Leer por id un recurso de B con contexto A: **404** | T-MC-077, T-MC-132 |
| AC-MC-32 | Modificar un recurso de B con contexto A: bloqueado | T-MC-132 |
| AC-MC-33 | Borrar un recurso de B con contexto A: bloqueado | T-MC-132 |
| AC-MC-34 | Enviar `company_id` de B en el cuerpo con contexto A: **409 `COMPANY_MISMATC | T-MC-078, T-MC-132 |
| AC-MC-35 | `UAB` cambia de A a B: ve solo B, sin restos de A | T-MC-093 |
| AC-MC-36 | Nunca se permite T1 → T2: el aislamiento previo se mantiene | T-MC-133 |
| AC-MC-40 | Con la licencia limitada a una empresa, crear la segunda: **409 `COMPANY_LIM | T-MC-022 |
| AC-MC-41 | Con derechos para varias, la segunda se crea y opera de forma independiente | T-MC-022 |
| AC-MC-42 | Pertenecer al tenant **no** concede acceso a todas sus empresas | T-MC-014 |
| AC-MC-43 | `ventas:view` en A no habilita ventas de B | T-MC-015 |
| AC-MC-44 | El alcance por sucursal sigue vigente dentro de la empresa | T-MC-016 |
| AC-MC-50 | A y B tienen series de numeración independientes; no colisionan | T-MC-062, T-MC-063, T-MC-137 |
| AC-MC-51 | Un rango de números de control de A **no** puede consumirse desde B | T-MC-063 |
| AC-MC-52 | El libro de ventas de A no contiene documentos de B | T-MC-064 |
| AC-MC-53 | El libro de compras de A no contiene documentos de B | T-MC-064 |
| AC-MC-54 | Una retención conserva la empresa agente; no se reconstruye por el contexto  | T-MC-065 |
| AC-MC-55 | Una factura reimpresa muestra su empresa emisora, no la activa | T-MC-071 |
| AC-MC-60 | Órdenes de compra de A y B separadas; ambas pueden llevar el número 100 | T-MC-066 |
| AC-MC-61 | Recepción cuya orden es de A y cuyo almacén es de B: **bloqueada** | T-MC-067 |
| AC-MC-62 | Facturas de proveedor y obligaciones separadas por empresa | T-MC-066 |
| AC-MC-63 | Un pago de A no se aplica a una factura de B: **409 `CROSS_COMPANY_OPERATION | T-MC-073 |
| AC-MC-64 | Mismo producto, almacenes de A y B: existencias **no** se mezclan | T-MC-068 |
| AC-MC-65 | Transferencia entre almacenes de A y B: bloqueada como intercompany | T-MC-069 |
| AC-MC-66 | Pedidos y facturas de venta separados | T-MC-070 |
| AC-MC-67 | Cuentas bancarias y movimientos separados | T-MC-072 |
| AC-MC-68 | Permisos y documentos regulatorios pertenecen a la empresa correcta | T-MC-074 |
| AC-MC-69 | Los costos no se mezclan entre empresas | T-MC-068 |
| AC-MC-70 | El informe previo se ejecuta **sin escribir** y detalla por tabla y clase | T-MC-054 |
| AC-MC-71 | MC-A se decide por el intervalo, no por el número de empresas de hoy | T-MC-050 |
| AC-MC-72 | Una fila MC-C no se rellena automáticamente | T-MC-053 |
| AC-MC-73 | Un MC-E **detiene** la migración final, sin escrituras destructivas parciale | T-MC-055, T-MC-135 |
| AC-MC-74 | El valor heredado se conserva hasta verificar | T-MC-040 |
| AC-MC-75 | La resolución manual registra quién, cuándo, evidencia, valor anterior y nue | T-MC-056 |
| AC-MC-76 | Tras migrar: importes, cantidades, bases imponibles y números **idénticos** | T-MC-057 |
| AC-MC-77 | Base vacía → `alembic upgrade head` sin error | T-MC-134 |
| AC-MC-78 | Fixture anterior a la normalización migra con su informe | T-MC-134 |
| AC-MC-79 | Ninguna columna de transición sobrevive a N8 | T-MC-110 |
| AC-MC-80 | `ResourceKind` declara alcance y resolutor **explícitos** | T-MC-120 |
| AC-MC-81 | Los **19** tipos registrados se prueban: entidad de la empresa activa → vínc | T-MC-122 |
| AC-MC-82 | Las 4 entradas de `REM-046-001` quedan registradas y probadas | T-MC-121 |
| AC-MC-83 | `STILL_BLOCKED_BY_046` = **0** para toda entidad existente | T-MC-123 |
| AC-MC-84 | La integración 045 → 046 con versión congelada sigue pasando | T-MC-125, T-MC-126 |
| AC-MC-90 | Toda la aceptación sobre **PostgreSQL 18.x** | T-MC-142 |
| AC-MC-91 | Regresión global con **0 fallos**; ningún escenario multiempresa omitido | T-MC-141 |
| AC-MC-92 | Selector sin violaciones serias de WCAG 2.2 AA, operable con teclado | T-MC-097 |
| AC-MC-93 | Sin desbordamiento horizontal entre 320 y 1440 | T-MC-097 |
| AC-MC-94 | Cross-browser en Chromium, Firefox y WebKit | T-MC-139 |
| AC-MC-95 | Acotar por empresa no degrada el plan: `EXPLAIN` en las tablas grandes | T-MC-104 |
| AC-MC-96 | Toda caché de empresa lleva la empresa en su clave | T-MC-080 |
| AC-MC-97 | Las claves de idempotencia no colisionan entre empresas | T-MC-081 |

## 5. Autoridad → requisito

| Autoridad | Requisitos |
|---|---|
| Gate multiempresa · defecto probado | FR-MC-001, FR-MC-002, FR-MC-020 |
| Constitución P4 · núcleo fiscal separado | FR-MC-063, AC-MC-50, AC-MC-51 |
| Constitución P5 · histórico protegido | FR-MC-054, FR-MC-056 |
| Constitución P6 · el backend es autoridad | FR-MC-011, FR-MC-020, FR-MC-034 |
| Constitución P8 · nada hardcodeado | FR-MC-035 |
| Constitución P17/P22 · autoridad única | FR-MC-010, FR-MC-031 |
| Constitución P21 · paridad del motor | NFR-MC-01 |
| Constitución P23 · captura temprana | FR-MC-052, R-MC-14 |
| `REM-AUTH-ROUTE-CRAWL-001` | FR-MC-016 |
| `REM-046-001` | FR-MC-072, FR-MC-073 |
| Spec 008 · referencia positiva | FR-MC-070 |
| Spec 045 · empresa real | FR-MC-071 |
| Spec 011 · conversión intacta | FR-MC-074 |
| Spec 003 · sin RBAC paralelo | FR-MC-031, FR-MC-032 |
| Spec 004 · derechos de licencia | FR-MC-034 |

## 6. Cadena: requisito → diseño → tarea → prueba

| Bloque | Diseño | Tareas | Prueba |
|---|---|---|---|
| Alcance canónico | `canonical-scope-matrix.md` | T-MC-001..006 | Pruebas de arquitectura |
| Contexto de empresa | `data-model.md` §3 | T-MC-010..023 | Unidad + seguridad |
| Cortar la hemorragia | `plan.md` N2 | T-MC-030..035 | Fallan en construcción |
| Migración | `legacy-company-reconstruction-matrix.md` | T-MC-040..058 | Seis bases |
| Dominios | `domain-company-normalization-matrix.md` | T-MC-060..081 | Integración A/B |
| Frontend | `wireframes/` | T-MC-090..097 | E2E, axe, responsive |
| Restricciones | `company-scope-constraint-impact.md` | T-MC-100..107 | FK en PostgreSQL |
| Spec 046 | `closed-spec-impact-matrix.md` | T-MC-120..126 | 19 tipos + ClamAV |
| API | `endpoint-scope-matrix.md` | T-MC-035, T-MC-076..079 | Contrato |

---

# N6 — FRONTEND MULTIEMPRESA

Cada requisito con su código, su prueba y su evidencia. Sin huérfanos.

| Requisito | Código | Prueba | Evidencia |
|---|---|---|---|
| Selector de empresa | `components/company/CompanySelector.tsx` | `n6-a11y-responsive.spec.ts` | `n6-accessibility-report.md` |
| Solo empresas autorizadas | `organization/api.py::list_companies` | `test_mc_company_isolation.py` | `n6-client-tampering-evidence.md` |
| Una sola empresa se resuelve sola | `CompanyContext.tsx::resolver` | `companyProvider.test.tsx` | `n6-company-context-ui-matrix.md` |
| Varias empresas piden selección | `CompanyContext.tsx::estado` | `companyProvider.test.tsx`, `n6-multicompany.spec.ts` | `n6-company-context-ui-matrix.md` |
| Cabecera centralizada | `api/client.ts::setCompanyResolver` | `companyContext.test.ts`, `architecture-company.test.ts` | `n6-request-context-evidence.md` |
| Empresa fijada al crear la petición | `api/client.ts::apiFetch` | `companyContext.test.ts` | `n6-request-context-evidence.md` |
| Sin repliegue al tenant | — (ausencia) | `architecture-company.test.ts` | `n6-request-context-evidence.md` |
| Contexto por pestaña | `CompanyContext.tsx::escrituraDePestana` | `n6-multicompany.spec.ts` | `n6-multitab-evidence.md` |
| Preferencia recordada y revalidada | `CompanyContext.tsx::clavePreferencia` | `companyProvider.test.tsx` | `n6-company-context-ui-matrix.md` |
| Preferencia caducada descartada | `CompanyContext.tsx::resolver` | `companyProvider.test.tsx` | `n6-company-context-ui-matrix.md` |
| Caché separada por empresa | `app/company/queryScope.ts`, `main.tsx` | `companyContext.test.ts` | `n6-cache-isolation-matrix.md` |
| Cambio de empresa descarta lo anterior | `app/AppShell.tsx` | `n6-multicompany.spec.ts` | `n6-cache-isolation-matrix.md` |
| Formularios protegidos | `app/company/useCompanyScope.ts` | `architecture-company.test.ts` | `n6-form-company-safety-matrix.md` |
| Relaciones dependientes reiniciadas | `app/AppShell.tsx` (remontado) | `n6-multicompany.spec.ts` | `n6-form-company-safety-matrix.md` |
| Errores de contexto sin bucle | `app/company/errores.ts` | `companyContext.test.ts` | `n6-final-checkpoint.md` |
| Acceso revocado sin cierre de sesión | `CompanyContext.tsx::onCompanyRejected` | `companyContext.test.ts` | `n6-company-context-ui-matrix.md` |
| Descargas con contexto | `api/client.ts` (`responseType: blob`) | `architecture-company.test.ts` | `n6-request-context-evidence.md` |
| Manipulación sin escalada | — (autoridad del servidor) | `n6-multicompany.spec.ts` | `n6-client-tampering-evidence.md` |
| Accesibilidad WCAG 2.2 AA | `CompanySelector.tsx` | `n6-a11y-responsive.spec.ts` | `n6-accessibility-report.md` |
| Adaptación 320–1440 | `CompanySelector.tsx` | `n6-a11y-responsive.spec.ts` | `n6-responsive-report.md` |
| Cross-browser | — | las tres suites × 3 motores | `n6-cross-browser-report.md` |

---

# N7 — INTEGRIDAD ESTRUCTURAL

| Requisito | Aclaración | Plan | Tarea | Código / migración | Prueba | Evidencia | Estado |
|---|---|---|---|---|---|---|---|
| FR-N7-001 FK de empresa | §1 | §4 | T-004 | `0033`, 80 modelos | `test_n7_structure::empresa_directa` | `n7-foreign-key-report.md` | ✅ |
| FR-N7-002 FK de tenant | §2 | §4 | T-005 | `0034` | `test_n7_structure::tenant` | ídem | ✅ |
| FR-N7-003 FK de sucursal | §1 | §4 | T-005 | ya existentes | `test_n7_structure` | ídem | ✅ |
| FR-N7-004 autoridad derivada | §5–7 | §3 | T-011 | `establishments` | `test_n7_structure::derivada` | `n7-derived-scope-report.md` | ✅ |
| FR-N7-005 autoridad obligatoria | §8 | §5 | T-011 | — (ya cumplido) | ídem | ídem | ✅ |
| FR-N7-006 empresa ≠ tenant | §1 | §4 | T-004, T-010 | `0033`, `0037` | `test_n7_corruption::tenant_como_empresa` | `n7-postgresql-catalog-evidence.md` | ✅ |
| FR-N7-007→010 unicidad | §9–11 | §6 | T-009 | — (sin cambios) | `test_n7_corruption::unicidad` | `n7-unique-scope-report.md` | ✅ |
| FR-N7-011 global e instalación | §3–4 | §11 | T-003 | 13 declaraciones | `test_architecture_scope` | `n7-derived-scope-report.md` | ✅ |
| FR-N7-012 tenant/empresa | §14 | §7 | T-010 | `record_audit` (N5) | `test_mc_events_audit_ab` | `n7-postgresql-catalog-evidence.md` | ✅ |
| FR-N7-013 empresa/sucursal | §19 | §7 | T-011 | ya coherente | `test_n7_structure` | ídem | ✅ |
| FR-N7-014 empresa/almacén | §19 | §7 | T-012 | `0036` | `test_n7_corruption::zona_ajena` | `n7-inventory-integrity-report.md` | ✅ |
| FR-N7-015 empresa/cuenta | §19 | §7 | T-013 | guarda de servicio (N5) | `test_mc_treasury_ab` | `n7-financial-integrity-report.md` | ✅ |
| FR-N7-016→022 fiscal | §17 | §9 | T-019, T-021 | `0033` | `test_n7_corruption::fiscal` | `n7-fiscal-integrity-report.md` | ✅ |
| FR-N7-023 paridad fiscal | — | §9 | T-013 | — | `test_fiscal.py` | ídem | ✅ |
| FR-N7-024 financiero | §19 | §9 | T-014, T-017 | `0033` | `test_n7_corruption::pago` | `n7-financial-integrity-report.md` | ✅ |
| FR-N7-025 inventario | §19 | §9 | T-016 | `0033`, `0036` | `test_n7_corruption::movimiento` | `n7-inventory-integrity-report.md` | ✅ |
| FR-N7-026 sin huérfanas | §12 | §4 | T-004 | `0033`, `0034`, `0037` | `test_n7_structure` | `n7-foreign-key-report.md` | ✅ |
| FR-N7-027 sin rutas rotas | §7 | §3 | T-011 | — | `test_n7_structure::derivada` | `n7-derived-scope-report.md` | ✅ |
| FR-N7-028 sin colisiones | §9–11 | §6 | T-009 | — | `test_n7_corruption::unicidad` | `n7-unique-scope-report.md` | ✅ |
| FR-N7-029 obligatoriedad | §8, §16 | §5 | T-006 | `0035` | `test_n7_structure::opcional` | `n7-not-null-report.md` | ✅ |
| FR-N7-030 rechazo de la base | — | §9 | T-010 | migraciones | `test_n7_corruption` (12) | `n7-postgresql-catalog-evidence.md` | ✅ |
| NFR-N7-001 migraciones pequeñas | — | §1 | T-004→008 | 5 migraciones | — | `n7-migration-report.md` | ✅ |
| NFR-N7-002 SQL sin conexión | — | §9 | T-015 | — | 105 sentencias | ídem | ✅ |
| NFR-N7-003 instalación limpia | — | §9 | T-014 | — | 37 migraciones, 336 FK | ídem | ✅ |
| NFR-N7-004 paridad | §19 | §9 | T-002 | 90 modelos | `test_n7_structure::orm_y_base` | `n7-postgresql-catalog-evidence.md` | ✅ |
| NFR-N7-005 rendimiento | §19 | §8 | T-008 | — (0 índices) | `EXPLAIN` × 5 | `n7-index-report.md` | ✅ |
| NFR-N7-006 sin romper lo válido | §20 | §9 | T-017, T-018 | correcciones | regresión completa | `n7-regression-report.md` | ✅ |

**Requisitos huérfanos: 0. Tareas huérfanas: 0. Cobertura: 100%.**

---

# N8 — CONTRATO Y RETIRADA DE LO TRANSITORIO

| Requisito | Aclaración | Plan | Tarea | Código / migración | Prueba | Evidencia | Estado |
|---|---|---|---|---|---|---|---|
| FR-N8-001 sin `legacy_scope_id` | §1–4 | §6 | T-010 | `0038` | `test_n8_contract::columnas` | `n8-legacy-removal-inventory.md` | ✅ |
| FR-N8-002 sin `scope_backfill_class` | ídem | §6 | T-010 | `0038` | ídem | ídem | ✅ |
| FR-N8-003 sin lectura doble | §11 | §1 | T-002 | — (no existía) | `test_n8_contract` | `n8-dual-read-write-report.md` | ✅ |
| FR-N8-004 sin escritura doble | ídem | §1 | T-002 | — | ídem | ídem | ✅ |
| FR-N8-005 sin repliegue | §11 | §4 | T-008 | `organization/service.py` +4 | `test_n8_contract::repliegue` | `n8-fallback-removal-report.md` | ✅ |
| FR-N8-006 sin ayudante ambiguo | ídem | §4 | T-008 | ídem | ídem | ídem | ✅ |
| FR-N8-007 alcance canónico | §11 | §4 | T-008 | ídem | `test_architecture_scope` | ídem | ✅ |
| FR-N8-008 cabecera declarada | §13–17 | §5 | T-009 | `company_context.py` | `test_n8_contract::declaran` | `n8-company-header-contract.md` | ✅ |
| FR-N8-009 refleja la auto-resolución | ídem | §5 | T-009 | ídem | `test_n8_contract::opcional` | ídem | ✅ |
| FR-N8-010 omisión con una empresa | ídem | §5 | T-009 | — | `test_n8_contract::omitirse` | ídem | ✅ |
| FR-N8-011 error con varias | ídem | §5 | T-009 | — | `test_n8_contract::ausencia` | ídem | ✅ |
| FR-N8-012 no concede acceso | ídem | §5 | T-009 | — | suite de N6 | ídem | ✅ |
| FR-N8-013 preflight ejecutable | §8–10 | §3 | T-007 | `mc/runner.py` | `test_mc_preflight` (23) | `n8-n4-compatibility-report.md` | ✅ |
| FR-N8-014 clasifica contra el destino | ídem | §3 | T-007 | ídem | ídem | ídem | ✅ |
| FR-N8-015 fixture hostil | §20–21 | §2 | T-006 | `qa/n4-legacy-hostile-seed.py` | ídem | `n8-hostile-fixture-report.md` | ✅ |
| FR-N8-016→018 clases preservadas | ídem | §2 | T-012 | — | ídem | ídem | ✅ |
| FR-N8-019→021 nulos globales | §18–19 | §7 | T-013 | — | `test_n8_contract::global` | `n8-legacy-removal-inventory.md` | ✅ |
| FR-N8-022 alineación | — | §7 | T-011 | — | `test_n7_structure::orm_y_base` | `n8-orm-schema-cleanup-report.md` | ✅ |
| FR-N8-023 documentación | §23 | §7 | T-015 | `canonical-scope-matrix.md` | — | `n8-runtime-contract-inventory.md` | ✅ |
| FR-N8-024 cargas útiles | §12 | §7 | T-004 | — | familia de N5 | ídem | ✅ |
| FR-N8-025 skips auditados | §20–21 | §7 | T-014 | — | — | `n8-skipped-tests-audit.md` | ✅ |
| FR-N8-026 N5/N6/N7 verdes | — | §7 | T-016 | — | suites completas | `n8-regression-report.md` | ✅ |
| NFR-N8-001 migraciones pequeñas | — | §6 | T-010 | `0038` | — | `n8-orm-schema-cleanup-report.md` | ✅ |
| NFR-N8-002 fixture reproducible | §20 | §2 | T-006 | `qa/…-seed.py` | `test_mc_preflight` | `n8-hostile-fixture-report.md` | ✅ |
| NFR-N8-003 solo lectura y repetible | — | §7 | T-012 | — | `test_el_preflight_no_escribe_nada` | `n8-n4-compatibility-report.md` | ✅ |
| NFR-N8-004 sin deriva | — | §7 | T-011 | — | `test_n7_structure` | `n8-openapi-contract-report.md` | ✅ |

**Requisitos huérfanos: 0. Tareas huérfanas: 0. Cobertura: 100%.**
