# SPEC 001 · Delta — TENANT / COMPANY ISOLATION PREREQUISITES (SHARED-CORE-P0-HARDENING-07)

| Campo | Valor |
|---|---|
| Spec dueña | **001**: FR-001-030 (aislamiento Installation/Tenant/Company), FR-001-032 (toda operación en su empresa y alcance), FR-001-033 (pruebas negativas de aislamiento), FR-001-040 (roles, permisos y alcance) |
| Fuente del modelo de alcance | **ARCH-MC-001** (`specs/arch-mc-001-canonical-multi-company-scope/`): `Scope`, `CompanyContext`, ADR-D0-014 y guardas N5/N10. Se reutiliza; no se duplica |
| Afectadas | 008 (almacenes), 003-inventario, 002-maestros/011-unidades, 004 (compras), 005 (ventas), 006 (tesorería), 046 (documentos), 009 (exportaciones), 047 (notificaciones) |
| Deudas en alcance | ROLE-CATALOG-INSTALLATION-WIDE · WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES · WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY (verificación) · WAREHOUSE-BRANCH-* · `branch_ids` · fila «001 Aislamiento tenant/ente» de `government-start-readiness.md` |
| Base | `0dbe632` (develop == origin/develop) |
| Evidencia | `evidence/isolation-prerequisites/` |
| Estado | **IMPLEMENTED — CERTIFIED — CONVERGED** (2026-10-29; reanudación controlada tras GOV-PRODUCT-COMPLETENESS-RETRO-01, base `1cbb79f`) |

## 0. Reconciliación previa

- **Gobierno.** El PDF `Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` se releyó (hash `8f86615f…`, sin cambio). Aplican:
  - RNF-GOV-001: aislamiento de datos, llaves, configuración y permisos por tenant/ente, con pruebas hostiles obligatorias;
  - RNF-GOV-006: toda autorización crítica en el backend;
  - RNF-GOV-012: permisos por capacidad y alcance;
  - RNF-GOV-005: auditabilidad;
  - RNF-GOV-020: QA con pruebas hostiles y mutación;
  - RNF-GOV-021: privacidad;
  - GOV-ORG-001: sin compartir reglas entre tenants por defecto;
  - GOV-ORG-007: el frontend nunca decide el alcance de company/ente;
  - E2E-06 (hostil multi-ente: «100 % denegado y auditado») y E2E-07 (hostil SoD).

  No se implementa nada de Gobierno: `GovernmentEntity`, `GovernmentUnit` y `AuthorityGrant` siguen sin existir.
- **Línea base de arquitectura de Gobierno** (`9a41503`): TENANT_SCOPE_CONTRACT, ORG_SCOPE_CONTRACT y AUTHORITY_SCOPE_CONTRACT. Este ciclo certifica el contrato actual (tenant = aislamiento, empresa = alcance) y define cómo se extiende (`FUTURE_EXTENSION_CONTRACT.md`), sin sustituir la línea base.
- **Hecho medido que condiciona la severidad.** El producto crea **un solo tenant**: `setup/initialize` corre una vez (`SETUP_ALREADY_DONE`) y ninguna ruta crea otro. Todo cruce entre tenants es **latente en producción y real en el modelo**: el mundo de pruebas, la certificación de restauración y Gobierno (varios entes por instalación) tienen varios. Se corrige igual (OD-ISO-01).

## 1. Discovery (medido en `0dbe632`)

| Universo | Medida |
|---|---|
| Modelos persistentes | 206: 171 COMPANY, 20 INSTALLATION, 11 TENANT, 4 GLOBAL. **0 sin `__scope__`** |
| Operaciones `/api/v1` | 556 (422 rutas): 482 con `CompanyContext` y 74 sin él (tenant, instalación, propias o públicas) |
| Campos `*_id` en cuerpos de escritura | 262, en 140 operaciones |
| Aristas FK | 301 COMPANY→COMPANY, 141 COMPANY→TENANT (`company_id → companies`), 12 TENANT→TENANT y el resto de instalación o global |

Herramientas de medición de Claude (scratchpad, fuera de Git):
- `inv_modelos.py`, `inv_rutas.py` e `inv_cuerpos.py`: introspección;
- `triaje_ids.py`: triaje estático de la validación de `*_id`;
- `ctx_sin_uso.py`: rutas con contexto que no lo usan.

Las 79 filas del triaje que no salieron validadas se revisaron a mano, en parte con dos agentes de lectura. **Claude verificó en el código** los hallazgos graves.

### 1.1 GAP (código leído; el rojo se mide en C07-T02)

| Id | Superficie | Defecto | Severidad |
|---|---|---|---|
| G-INV-03 | `POST /inventory/costing-profiles` | `global_scope=true` crea un perfil con empresa nula, visible y **efectivo en todas las empresas de todos los tenants**. Con `product_id` gana al perfil general propio (`_costing_method` ordena por producto). `product_id` sin validar | HIGH (dinero) |
| G-INV-04 | `POST /inventory/movement-types` | `global_scope=true` crea un tipo global, visible y resuelto por `_get_movement_type_by_code` en empresas que no tienen uno propio | HIGH |
| G-TES-01 | `POST /treasury/cash-sessions/{id}/movements` | `instrument_id` y `payment_id` sin validar. `_find_execution` busca el `payment_id` **sin empresa**: un movimiento con el pago de otra empresa hace que su `execute_payment`/`execute_collection` con clave idempotente responda `idempotent: true` sin ejecutar | HIGH |
| G-TES-02 | `POST /treasury/reconciliations/{id}/lines` | `bank_transaction_id` de cualquier empresa; `propose_matches` lee su importe y su referencia | HIGH (fuga) |
| G-ROL-01 | `GET/POST /roles`, `POST /users/{id}/roles` | Un rol personalizado con empresa nula es de toda la instalación: visible y asignable desde otro tenant; el 409 `ROLE_DUPLICATE` revela los códigos ajenos (ROLE-CATALOG-INSTALLATION-WIDE) | MEDIUM (latente) |
| G-COM-01 | `POST /purchasing/supplier-invoices/{id}/lines` | `product_id`, `order_line_id` y `receipt_line_id` sin validar; la propiedad de la factura se comprueba **después** de insertar; `match_invoice` lee la línea de orden ajena | HIGH |
| G-COM-02..04 | líneas de orden, solicitud y cotización de compra | `product_id` (y `unit_id` en solicitud) sin validar | MEDIUM |
| G-COM-05 | `POST /purchasing/receipts/{id}/confirmacion-inventario` | `decisions[].incident_id` sin comprobar que sea de la empresa ni de la recepción | MEDIUM |
| G-VEN-01 | `POST /sales/invoices/{id}/lines` | `product_id` sin validar | MEDIUM |
| G-VEN-02 | `POST /sales/confirmacion/{order_id}` | `product_id` de las líneas sobrantes sin validar | MEDIUM |
| G-VEN-03 | `POST /sales/devoluciones` | `lot_id`/`serial_id` (sin FK) sin validar | LOW |
| G-INV-01 | `POST /inventory/transfers` | `lines[].product_id/lot_id/serial_id` sin validar | MEDIUM |
| G-INV-02 | `POST /inventory/counts/{id}/lines` | `product_id`, `location_id` y `lot_id` sin validar (el producto se detecta al aprobar; la ubicación y el lote nunca) | MEDIUM |
| G-MD-01 | `POST /maestros/catalogos/items` | `category_id`, `base_unit_id`, `tax_profile_id`, `inventory_profile_id` y `billing_unit_id` sin validar | MEDIUM |
| G-MD-02 | `POST /maestros/catalogos/taxonomia` | `parent_id` sin validar | MEDIUM |
| G-MD-03 | presentaciones y sus versiones | `unit_id` y `factor_uom_id` sin validar (el inexistente da 409 engañoso) | MEDIUM |
| G-DOC-01 | `POST /documentos/tipos` | `category_id` sin validar; el inexistente da 409 `DOCUMENT_TYPE_CODE_DUPLICATE` | MEDIUM |
| G-NOT-01 | `POST /notifications/rules` | `escalation_role_id` solo se comprueba que exista: se acepta el rol de otra empresa u otro tenant | LOW |
| G-WH-01 | `validate_chain` (ubicaciones y nodos) | un nodo de otro tenant da 422 `HIERARCHY_CROSS_WAREHOUSE` y uno inexistente 404: oráculo de existencia | LOW |
| G-SES-01 | `DELETE /auth/sessions/{id}` | una sesión ajena (incluso de otro tenant) da 403 y una inexistente 404: oráculo | LOW |
| G-STO-01 | exportaciones de reportes | `write_bytes` en un directorio plano compartido por todos los tenants: una colisión de `file_ref` sobrescribiría el objeto ajeno sin fallar | LOW |
| G-HLP-01 | `_owned`/`_get_owned` (6 copias) | `getattr(obj, "company_id", tenant)` **falla abierto** con un modelo sin columna `company_id` (hoy sin llamadas así; latente) | MEDIUM (latente) |

**Campos ignorados** (se aceptan en el esquema y no se usan; no cruzan nada; se registran sin corregir):
- `create_item`: `traceability_profile_id` y `regulatory_profile_id`;
- `operation_ship`: `lot_ids`;
- `create_conversion`: `from_unit_id`;
- `apply_credit_note`: `source_id`.

### 1.2 Sin GAP (medido)

- **Contexto de empresa:**
  - la cabecera propone y el servidor resuelve, valida y autoriza;
  - 404 `COMPANY_NOT_FOUND` para una empresa ajena o inexistente;
  - 403 `COMPANY_SCOPE_FORBIDDEN` auditado (`COMPANY_SCOPE_DENIED`) para una capacidad en otra empresa.
- **Guardas AST vigentes:** las tres familias N5/N10, más modelos sin alcance = 0.
- **Idempotencia de dominio:** acotada por empresa en compras, inventario y tesorería (FX). `get_or_record` genérico no tiene llamadas.
- **Almacén documental:**
  - `storage_key` de 192 bits generada por el servidor, única en la base, nunca expuesta y nunca aceptada del cliente;
  - toda lectura pasa por `StoredFile` → documento → empresa.
- **Exportaciones:** la descarga pasa por la fila de la empresa y la capacidad de origen.
- **Auditoría:** `/audit/events` y `/audit/filters` acotados (ciclo 04).
- **Comercial:** valida todas sus referencias.
- **`branch_ids`:** `UserScope` no tiene escritor en el producto y `CompanyContext.branch_ids` no lo consume nadie. Es **latente**: no hay camino del producto que cree estado inválido.
- **`manager_id`:** etiqueta opaca que nunca se resuelve.
- **`system_settings`:** sin uso.
- **`renewal-request`:** regla ratificada en la Spec 004.
- **`list_sources`:** catálogo estático.

## 2. Inventarios (en `evidence/isolation-prerequisites/`)

| Inventario | Contenido |
|---|---|
| `SCOPE_MODEL_INVENTORY.md` | Los 206 modelos con alcance OD-ISO-06, columna, ruta de autoridad, FK, unicidades, clase de aplicación, pruebas y estado |
| `SCOPE_ROUTE_INVENTORY.md` | Las 556 operaciones con fuente de tenant y empresa, capacidad, dependencia, error y estado |
| `SERVICE_SCOPE_INVENTORY.md` | Ayudantes y servicios que cargan por id: quién aplica el alcance |
| `STORAGE_SCOPE_INVENTORY.md` | Operaciones de almacén documental y de exportaciones |
| `SCOPE_ERROR_MATRIX.md` | Semántica de error por clase de operación y caso hostil |
| `FUTURE_EXTENSION_CONTRACT.md` | Cómo encajarían ente, unidad y autoridad sin implementarlos |

Correspondencia de las clases OD-ISO-06 con `app/core/scope.Scope`:

| OD-ISO-06 | `Scope` |
|---|---|
| TENANT_SCOPED | `TENANT` |
| COMPANY_SCOPED | `COMPANY` (y `BRANCH`, sin uso) |
| INSTALLATION_SCOPED | `INSTALLATION` |
| GLOBAL_REFERENCE | `GLOBAL` |
| SECURITY_GLOBAL_WITHIN_INSTALLATION | `INSTALLATION` con motivo en la lista cerrada (catálogo de permisos y roles protegidos del sistema) |
| EXPLICITLY_UNSCOPED_BY_DESIGN | ninguno: no existe `UNKNOWN` |

## 3. Decisiones de la dueña aplicadas

| Decisión | Aplicación |
|---|---|
| OD-ISO-01 | El tenant es la frontera dura: lista, detalle, búsqueda, recuento, exportación, descarga, auditoría y relación |
| OD-ISO-02 | La empresa es alcance dentro del tenant: capacidad × empresa × tenant × estado vigente |
| OD-ISO-03 | `X-Kontrol-Company` selecciona; el servidor resuelve y valida (sin cambios) |
| OD-ISO-04 | Sin reescritura global de errores: `SCOPE_ERROR_MATRIX` preserva lo certificado; los GAP adoptan el 404 del objeto relacionado, idéntico a inexistente (ADR-D0-014) |
| OD-ISO-05 | El frontend proyecta; guarda de frontend |
| OD-ISO-06 | Clasificación explícita con lista cerrada para INSTALLATION y GLOBAL |
| OD-ISO-07 | Almacén: `CURRENT_ISOLATION_SUFFICIENT` (mapeo opaco validado); en exportaciones solo escritura exclusiva para las altas nuevas; sin migrar claves |
| OD-ISO-08 | `DATA_REPAIR_EXECUTED = 0`: se miden las filas cruzadas existentes con el escáner y se registra el plan |
| OD-ISO-09 | Primitivas reutilizables (metadatos, escáner y arnés) sin condicionales de Gobierno |
| **OD-ISO-10 = A** (2026-10-29; evidencia: respuesta de la dueña en el diálogo de preguntas a las 03:02:42Z, «Prohibirlo desde empresa (Recommended)») | `global_scope=true` en tipos de movimiento y perfiles de costeo desde una petición de empresa → **403 `GLOBAL_SCOPE_FORBIDDEN`**; la UI quita la casilla; las filas globales existentes se conservan y se miden |
| **OD-ISO-11 = A** (2026-10-29; misma respuesta, «tenant_id sin relleno (Recommended)») | Migración `0062`: `roles.tenant_id` anulable con FK a `tenants` (nulo = roles protegidos del sistema). Los roles nuevos llevan el tenant del actor; listar, asignar y detectar duplicados se filtran por tenant. **Sin relleno**: los roles personalizados heredados con tenant nulo se miden y queda un plan de reparación |

## 4. Arquitectura

### 4.1 Contrato de relaciones (§22–§24)

Una escritura de empresa que recibe un `*_id` **carga el objeto y comprueba su alcance antes de persistir nada**. Clases:

| Clase | Regla | Ejemplos |
|---|---|---|
| SAME_COMPANY_REQUIRED | `obj.company_id == ctx.company_id` (o por la ruta de autoridad) | producto, lote, serie, ubicación, línea, instrumento, pago, transacción, categoría documental, perfil, taxonomía |
| TENANT_WIDE_REFERENCE_ALLOWED | el objeto es del tenant del contexto | rol personalizado del tenant (OD-ISO-11) |
| GLOBAL_REFERENCE_ALLOWED | `company_id` nulo, sembrado por la plataforma | unidades globales (`_get_unit`), tipos de movimiento y perfiles globales existentes |
| EXPLICIT_CROSS_COMPANY_RELATION_ALLOWED | ninguno hoy | — |

- **Respuesta:** 404 con el código del objeto relacionado, **idéntico** para ajeno, de otro tenant e inexistente. Se reutilizan los ayudantes de cada módulo: `_require_product`, `_require_incident`, `_get_unit`/`_unidad_visible`, `_require_account`, etc.
- **Excepción preservada:** `NOTIFICATION_RULE_INVALID` (422, motivo `ROLE_NOT_FOUND`), que es el contrato vigente para un rol inexistente; el rol ajeno recibe la misma respuesta.
- **Ayudantes genéricos:** `_owned` y `_get_owned` fallan **cerrado** si el modelo no tiene `company_id` (G-HLP-01).

### 4.2 Base de datos (§23, §45)

- **FK compuestas.** Cubrir las 301 aristas COMPANY→COMPANY exigiría añadir `company_id` a 42 tablas derivadas y rellenarlo; es una migración masiva con reparación.
  - Decisión: **NO_ADOPTED** en este ciclo. La protección es la validación en el backend, más las pruebas hostiles, más el escáner de invariantes.
  - WAREHOUSE-BRANCH-FK-COMPUESTA sigue como decisión de la dueña.
- **Única migración:** `0062_spec001_roles_tenant` (OD-ISO-11). Añade la columna, el índice y la FK; no rellena ni toca los datos. Hay que probar el upgrade, el downgrade y la cabeza única.

### 4.3 Escáner de invariantes de alcance (`app/ops/scope_scan.py`)

- **Herramienta de operación de solo lectura:** `python -m app.ops.scope_scan`, con la URL de la base por variable de entorno. En PostgreSQL usa `SET TRANSACTION READ ONLY`.
- **Comprobaciones:**
  - por cada FK entre modelos con empresa resoluble (columna propia o cadena `__scope_authority__`), cuenta las filas cuya empresa difiere de la del padre; un padre con empresa nula es una referencia global admitida;
  - la arista TENANT de `roles` (OD-ISO-11);
  - las filas globales escritas por empresas (OD-ISO-10).
- **Salida:** JSON con aristas comprobadas, violaciones por arista (solo recuentos e ids, sin datos de negocio) y la clase CROSS_TENANT o CROSS_COMPANY. Código de salida: 0 limpio, 1 con violaciones, 2 de uso.
- **Usos:**
  - en las pruebas hostiles (ninguna fila cruzada nueva);
  - en la certificación de la base tras la E2E (`CROSS_SCOPE_ROWS_CREATED_BY_E2E = 0`);
  - para medir las filas cruzadas existentes en una instalación, a ejecutar por la operadora; ejecutarlo contra producción queda fuera de este ciclo.

### 4.4 Arnés hostil reutilizable (`tests/hostil_mundo.py`)

**Mundo** (PostgreSQL, por módulo):
- `TA` con empresas `A1` y `A2`;
- `TB` con empresas `B1` y `B2`;
- una sucursal y un almacén por empresa (creados por la API).

**Actores:**

| Actor | Rol | Alcance | Notas |
|---|---|---|---|
| `a1_op` | funcional no privilegiado | solo A1 | sin MFA |
| `a12_op` | ídem | A1 y A2 | |
| `a_admin` | ADMIN + FUNCIONAL_COMPLETO | todo el tenant TA | con MFA, vía `login_completo` |
| `b1_op` | funcional | solo B1 | |
| `b_admin` | ADMIN + FUNCIONAL_COMPLETO | todo TB | con MFA, vía `login_completo` |
| `a1_aud` | `audit:view` | solo A1 | |
| `a_aud_t` | `audit:view` | todo el tenant | |

No hay ninguna fixture que conceda «todo» por omisión.

**Siembra de centinelas.** Recetas por API que crean, en cada empresa, recursos representativos con un **centinela** único en código y nombre (`ZZ<dim><empresa><token>`). Hay al menos:
- un tercero (proveedor y cliente) y un producto;
- un almacén y una ubicación;
- un tipo y un documento con versión;
- una exportación;
- una orden de compra con línea;
- una cuenta, una caja y un pago;
- un tipo de movimiento propio.

**Contrato del caso** (`CasoHostil`):
- actor y empresa activa;
- método, ruta y cuerpo;
- tenant y empresa objetivo;
- estado y código esperados;
- tablas cuya huella no debe cambiar;
- acción de auditoría esperada o ninguna.

`ejecutar_caso` comprueba:
- el estado y el código;
- que ningún centinela de otra dimensión aparezca en el cuerpo de la respuesta;
- que la huella de las tablas declaradas no cambie (recuento y md5, en la base);
- el delta de auditoría.

**Extensión:** `DIMENSIONES = ("tenant", "company")`. El mundo expone `ids[dimension][clave]`; añadir `entity`, `unit` o `authority` es añadir una dimensión y sus recetas, sin tocar el contrato.

**Barridos genéricos:**
- **BARRIDO-IDS.** Para toda operación con contexto y parámetro de ruta `{…id}` (GET, PATCH, PUT, DELETE y acciones POST), con todos los ids de las filas de las empresas ajenas (B1, B2 y A2 para `a1_op`):
  - nunca 2xx;
  - nunca un centinela ajeno en la respuesta;
  - la huella de las empresas ajenas no cambia.

  Las rutas cuyo recurso es GLOBAL o de instalación quedan en una lista cerrada con motivo.
- **BARRIDO-LISTAS.** Para toda operación GET con contexto y sin parámetro de ruta, como `a1_op` en A1, sin filtros y con `q` igual a un centinela ajeno donde `q` exista: ningún centinela ajeno en la respuesta, y un `total` que no cambia al sembrar más filas en B.
- **Casos dirigidos.** Cada GAP de §1.1 tiene su caso rojo. Además hay casos representativos de documentos (metadatos, vista previa, descarga, adjuntos y borrado), reportes y exportaciones (generar, listar y descargar), auditoría (auditor de A1 frente a A2, tenant B y eventos de tenant) y paginación.
- **Concurrencia (§46, §73).** Quitar un `UserScope` con la sesión viva, o el rol, deja la siguiente petición en 404 o 403 (precedente AC-MC-16).

### 4.5 Guardas de arquitectura

| Guarda | Regla |
|---|---|
| SCOPE_MODEL | Todo modelo declara `__scope__` (vigente). Los INSTALLATION y GLOBAL están en `ALCANCE_DE_INSTALACION_JUSTIFICADO = {tabla: (motivo, spec)}`, una lista cerrada: uno nuevo sin motivo falla, y una entrada muerta falla |
| SCOPE_ROUTE | Toda operación `/api/v1` o usa `get_company_context`, o figura en `RUTAS_SIN_EMPRESA_CLASIFICADAS = {(método, ruta): (clase, motivo)}` con clase en PUBLIC, SELF, TENANT, INSTALLATION o ELIGIBILITY. Una operación nueva sin clasificar falla, y una entrada muerta falla |
| HELPER | Ningún `getattr(obj, "company_id", <valor>)` como comprobación de propiedad (G-HLP-01) |
| GLOBAL_WRITE | Ningún `company_id=None if body.global_scope` en las rutas de empresa (OD-ISO-10) |
| FRONTEND | En `src`: `X-Kontrol-Company` solo en `api/client.ts`; ningún `tenant_id`/`tenantId` en peticiones; ninguna comparación de código de rol (`=== "ADMIN"`); ningún `global_scope: true` |

### 4.6 Almacén (§27–§28)

- **Documentos:** `STORAGE_NAMESPACE_DECISION = CURRENT_ISOLATION_SUFFICIENT`.
  - La clave es opaca, de 192 bits, generada por el servidor, única en la base, nunca expuesta y nunca aceptada del cliente.
  - El acceso pasa siempre por una fila acotada.
  - Una colisión es criptográficamente despreciable.
  - Sin cambio y sin migración.
- **Exportaciones (G-STO-01):** el `file_ref` lleva 48 bits aleatorios y un segundo, en un directorio compartido. Las altas nuevas se escriben en **modo exclusivo** (`open(..., "xb")`): una colisión falla cerrado, con 500 saneado, y nunca sobrescribe. Sin migrar los ficheros existentes.

### 4.7 Copia y restauración (§29)

- `BACKUP_SCOPE_LEVEL = INSTALLATION`. Incluye todos los tenants, y el almacén documental y las exportaciones completos (ciclo 06).
- La columna nueva viaja con `pg_dump`. Hay que repetir la certificación real (C-00..C-13) con la cabeza 0062.
- La exportación por ente es de Gobierno y queda fuera.

### 4.8 Auditoría (§30)

Sin acciones nuevas en el catálogo:
- `COMPANY_SCOPE_DENIED` sigue auditando el 403 de alcance;
- el 404 de no enumeración y el 403 `GLOBAL_SCOPE_FORBIDDEN` no se auditan, igual que `PERMISSION_DENIED`;
- el «auditado» de E2E-06 queda como punto de extensión de Gobierno (`FUTURE_EXTENSION_CONTRACT.md` §4).

### 4.9 UI

- Se quita la casilla «global» de `TiposMovimientoPage` (OD-ISO-10).
- No hay pantallas nuevas.
- Se revisan las pantallas afectadas (tipos de movimiento, valorización, roles, documentos, almacenes) en la puerta de pantallas y formularios.

## 5. Seguridad

Superficies certificadas:
- IDOR/BOLA (barrido de ids);
- escape de tenant o empresa;
- asignación masiva (`company_id` y `tenant_id` del cuerpo, vigentes en N5);
- manipulación de cabecera o consulta (ciclo 05);
- escape del almacén;
- fuga por exportación, auditoría, recuento o búsqueda;
- enumeración por error (G-WH-01, G-SES-01).

EGRESS: los encargos no llevan contraseñas, tokens, claves, `.env`, datos personales ni rutas personales. El mundo genera las credenciales con `secrets` dentro de la prueba.

## 6. Tareas

Todas con RETRY_MAX = 2, EGRESS_SAFE = 1 y SECURITY_SENSITIVE = 1. DeepSeek redacta todo el código, las pruebas, los guiones y la migración; Claude diseña, audita, aplica y certifica.

| Tarea | Modelo | Ficheros | Prueba / DONE_WHEN |
|---|---|---|---|
| C07-T01 arnés y mundo | pro | `tests/hostil_mundo.py` | importa; el mundo se construye en PG; los actores entran; centinelas sembrados |
| C07-T02 rojo dirigido | pro | `tests/test_iso_relaciones.py` | **falla con el producto de `0dbe632`** en cada GAP de §1.1 (rojo atribuible registrado) |
| C07-T03 escáner | pro | `app/ops/scope_scan.py`, `tests/test_scope_scan.py` | violaciones sembradas detectadas y base limpia en 0, en los dos motores |
| C07-T04 inventario | pro | `inventory/api.py`, `inventory/service.py` | G-INV-01..04 y G-HLP-01 (inventario) en verde |
| C07-T05 maestros y documentos | flash | `master_data/api.py`, `master_data/uom_api.py`, `documents/api.py` | G-MD-01..03 y G-DOC-01 en verde |
| C07-T06 compras | pro | `purchasing/api.py`, `purchasing/service.py` | G-COM-01..05 y G-HLP-01 (compras) en verde |
| C07-T07 ventas | pro | `sales/api.py`, `sales/service.py` | G-VEN-01..03 y G-HLP-01 (ventas) en verde |
| C07-T08 tesorería | pro | `treasury/api.py`, `treasury/service.py` | G-TES-01/02 y G-HLP-01 (tesorería) en verde |
| C07-T09 roles y sesiones | pro | migración `0062`, `identity_access/models.py`, `identity_access/service.py`, `notifications/service.py` | G-ROL-01, G-SES-01 y G-NOT-01 en verde; upgrade y downgrade |
| C07-T10 almacenes y exportaciones | flash | `organization/structure.py`, `reporting/service.py`, ayudantes de `regulatory`/`fiscal` | G-WH-01, G-STO-01 y G-HLP-01 (resto) |
| C07-T11 guardas | pro | `tests/test_iso_guardas.py` | las cinco guardas de §4.5 |
| C07-T12 barridos | pro | `tests/test_iso_barridos.py` | BARRIDO-IDS y BARRIDO-LISTAS sin hallazgos |
| C07-T13 matrices hostiles | pro | `tests/test_iso_matrices.py` | documentos, exportaciones, auditoría, paginación y concurrencia |
| C07-T14 frontend | flash | `TiposMovimientoPage.tsx` y su prueba, guarda de frontend (vitest) | vitest, tsc, eslint |
| C07-T15 ISOLATION-E2E | pro | `e2e/isolation.spec.ts`, siembra con centinelas en `qa/n6_world.py` | Chromium, Firefox y WebKit |
| C07-T16 base tras la E2E | flash | envoltorio `--orden` con `scope_scan` | 0 filas cruzadas creadas |

Claude: inventarios, matriz de errores, contrato de extensión, mutaciones, certificación, convergencia e informe.

## 7. Puerta

| Condición | Valor |
|---|---|
| SCOPE_MODEL_INVENTORY_COMPLETE · SCOPE_ROUTE_INVENTORY_COMPLETE · STORAGE_SCOPE_INVENTORY_COMPLETE | 1 · 1 · 1 (generados desde la introspección; §2) |
| ERROR_MATRIX_DEFINED · HOSTILE_HARNESS_DESIGNED | 1 · 1 |
| GOVERNMENT_REQUIREMENTS_REVIEWED | 1 |
| DATA_REPAIR_EXECUTED | 0 |
| MATERIAL_OQ · UNKNOWN · CONTRADICTIONS · BLOCKER | 0 · 0 · 0 · 0 (OD-ISO-10/11 resueltas por la dueña) |

**GATE PASS.** El encargo autoriza `implement` para SHARED-CORE-P0-HARDENING-07, solo núcleo compartido.

## 8. Implementación (estado: IMPLEMENTED)

Todo el código, las pruebas, la migración `0062` y la QA los escribió DeepSeek; Claude redactó los encargos, auditó cada parche, lo aplicó literal y midió. Formato aplicado por herramienta: `ruff --fix` (I001/F401) en T01C y en `list_roles` (OD-ORCH-01).

| Tarea | Resultado | Intentos |
|---|---|---|
| T01 arnés `tests/hostil_mundo.py` | mundo TA{A1,A2} · TB{B1,B2}, 8 actores, centinelas `ZZ<emp><hex>`, `CasoHostil`/`ejecutar_caso` | c0 → r1 → r2 + T01C (lint) |
| T02a–d rojo dirigido | 53/25/21/3 rojas en `0dbe632`, con 19/10/12/3 controles verdes | T02a r2 (c0 truncado) · T02b r1 · T02c r2 + T02cC · T02d c0 |
| T03 escáner `app/ops/scope_scan.py` | solo lectura, reglas 1 y 2, filas globales y roles de instalación; SS-01..07 | c0 → r1 → r2 |
| T04–T10 correcciones | los 24 GAP de §1.1 en verde (inventario, maestros, documentos, compras, ventas, tesorería, roles, sesiones, notificaciones, almacenes, exportaciones, ayudantes) | T08 r1 · T09 r1 · T10B (contratos viejos fijados en pruebas) |
| T11 guardas | g01–g05: alcance declarado, lista cerrada de instalación (23), rutas sin empresa clasificadas (74), `__scope_authority__`, frontend | c0 |
| T12 barridos | BARRIDO-IDS (228 rutas, ~10 840 peticiones) y BARRIDO-LISTAS | c0 → r1 → r2 |
| T13 matrices | ISO-PAG-01, ISO-CON-01, ISO-CON-02 | c0 → r1 |
| T14 frontend | casilla global retirada; guarda vitest (regex corregida en T14C) | c0 + T14C |
| T15 ISOLATION-E2E | `e2e/isolation.spec.ts` y centinelas en `qa/n6_world.py` | c0 → r1 |
| T17 hallazgos del barrido | G-VEN-04 (`/cxc/clientes/{id}/saldo`, `estado-de-cuenta`, `creditos`) y G-TES-03 (`/accounts/{id}/balance`) | c0 |
| T18 mutante superviviente | ISO-TES-04 sobre `_find_execution` | c0 rechazado (sin línea de ruta, nombre) → r1 |

**DeepSeek:** 39 llamadas registradas (23 `deepseek-v4-pro`: 83 516/76 534 tokens · 16 `deepseek-v4-flash`: 22 228/14 687), **0,106049 USD**, todas `finish_reason=stop`; una respuesta más (T02a c0) llegó truncada a 8192 tokens y se descartó sin registro de uso. Parches rechazados: 16 (incluido el truncado); aceptados: 24 (16 + 24 = 40 respuestas). Ninguna tarea superó `RETRY_MAX: 2`. Claude no escribió código de producto ni pruebas.

**Mutaciones (campaña 07, separada de las líneas base 02D…06):** 23 mutantes · **23 KILLED** · 0 SURVIVED. Dos corridas inválidas (M07-07 y M07-10: selector `-k` que no casaba nada) se repitieron con los ids reales (`rel1`, `rel7`) y murieron. M07-12 (quitar el filtro de empresa de la vía de caja de `_find_execution`) sobrevivió a la ronda 1 y lo mató ISO-TES-04 (T18).

**Contratos:** OpenAPI idéntico a `HEAD` (422 rutas, 556 operaciones, mismos esquemas): `OPENAPI_DRIFT = 0`; `global_scope` se conserva en el esquema y se rechaza con 403 `GLOBAL_SCOPE_FORBIDDEN` (OD-ISO-10). mypy: 154 = `HEAD`, misma lista de errores. ruff limpio.

**Inventarios de SALIDA:** 206 modelos (183 ENFORCED_TESTED: 171 COMPANY + 12 TENANT · 23 UNSCOPED_BY_DESIGN: 19 INSTALLATION + 4 GLOBAL) y 556 operaciones ENFORCED_TESTED; `GAP = 0`.

## 8b. Reanudación controlada (2026-10-29, base `1cbb79f`)

El trabajo sin confirmar no se descartó ni se dio por bueno: se reconcilió primero.
- **Procedencia:** cada línea del árbol frente a `HEAD` se buscó en las respuestas crudas de DeepSeek. Resultado: 44 ficheros semánticos, 0 de procedencia desconocida, 0 código semántico de Claude. Formato automático (OD-ORCH-01): un import quitado por `ruff --fix` F401 y dos I001 (`UNCOMMITTED_C07_RECONCILIATION_MATRIX.md`).
- **Decisiones:** OD-ISO-10/11 se conservan con su evidencia (§3); `INVENTED_OWNER_DECISIONS = 0`.

| Tarea | Resultado | Intentos |
|---|---|---|
| T19 cabeza `0062` declarada | MIG-09/10 y KR-18/19 | c0 |
| T20 → T20b barrido de cabecera ISO-CAB-01 | oráculo de no enumeración (ajena = inexistente) sobre 482 rutas y 5 casos; 0 hallazgos | T20 c0 → r1 → r2 (oráculo del encargo mal planteado), reformulado como T20b c0 → r1 |
| T21a rutas de tenant y propias (ISO-TEN-01..07) | 7 en verde | c0 → r1 |
| T21b `reject`/`return` ajenos | en verde | c0 |
| T22a/T22b puertos configurables (PDD-QA-PORTS-01) | 41/41 en el arnés sin omitidas con el 8000 ocupado por otro proyecto | T22a c0 → r1 · T22b c0 → r1 → r2 |
| T23/T23b E2E de Tipos de movimiento | E2E-TMOV-01..03; sin `test.skip` nuevo (contrato del arnés) | T23 c0 · T23b c0 → r1 |
| T24 defensas sin prueba (mutación) | ISO-HLP-02 (seis ayudantes) e ISO-STO-02 | c0 → r1 |
| T25, T26, T27, T28 oráculo y localizadores de la E2E | cuerpo leído tras navegar → interceptación con `page.route`; `exact: true` en dos localizadores | c0 cada una |

## 9. Pruebas y evidencia

Inventario de suites: `REQUIRED_SUITE_INVENTORY.md` (36). Todas se ejecutaron.

| Suite | Resultado | Evidencia |
|---|---|---|
| Rojo dirigido | T02a–d: 53/25/21/3 rojas en `0dbe632` | §8 |
| Hostiles de aislamiento | 440 pruebas en 31 ficheros hostiles; 0 fugas | trazador `c07/cobertura` |
| Barridos | IDS 228 rutas / 8 658 peticiones · LISTAS 0 fugas · CABECERA 482 rutas / 4 949 peticiones / 2 410 pares ajena-inexistente idénticos | `test_iso_barridos.py` |
| PostgreSQL completa | **4 055 / 0 / 18** | `qa/backend-runs/r20261029t160230p2508334nfedc15` |
| SQLite completa | **2 772 / 0 / 1 301** | `qa/backend-runs/r20261029t164734p2940024naa4018` |
| Arnés E2E | 41/41 (antes, 15 y 21 omitidas con el 8000 ajeno) | `test_e2e_corrida.py` |
| vitest · tsc · eslint · build | 705/705 · 0 · 0 · OK | — |
| ruff · mypy | limpio · 154 = `HEAD` (misma lista) | — |
| Alembic | cabeza única `0062`; upgrade/downgrade (T09) | MIG-09/10 |
| OpenAPI | idéntico a `HEAD` (422 rutas, 556 operaciones) | `OPENAPI_UNEXPLAINED_DRIFT = 0` |
| Mutaciones (campaña 07) | **34 mutantes: 33 KILLED · 1 EQUIVALENT · 0 SURVIVED · 2 corridas inválidas repetidas** | `c07/mutantes07*.json` |
| ISOLATION-E2E ×3 | todas las pruebas de aislamiento en verde en Chromium, Firefox y WebKit (corrida 3 y diagnóstica WebKit) | `qa/e2e-runs/r20261029t202947…`, `…t210113…` |
| E2E canónica | **388 / 388** | `qa/e2e-runs/r20261029t205309p3197850n9e7ccf` |
| Base tras la E2E | cabeza `0062`, 3 triggers de auditoría, 0 eventos fuera del catálogo, `CROSS_SCOPE_ROWS_CREATED_BY_E2E = 0` (tres corridas) | `post_e2e_inspect.py` |
| Copia y restauración | 29 PASS / 0 FAIL | `qa/backup-runs/20261029T210227Z-d7162e` |
| Residuos | 0 schemas, 0 bases de corrida, 0 conexiones; `test-results` del día retirado | `pg-test-residuos.py`, `e2e-bases.py` |

**Mutantes M07-24..34**, que cubren las clases de §59 que faltaban:
- KILLED:
  - cabecera como autoridad;
  - descarga sin empresa;
  - bitácora sin tenant;
  - guarda de modelos;
  - guarda de rutas;
  - literal de rol en el frontend;
  - empresa del rol de otro tenant;
  - puertos que ignoran el entorno.
- **M07-25 EQUIVALENT:** `accessible_company_ids` parte de las empresas del tenant, así que la comprobación de tenant de `resolve_company` es defensa en profundidad.
- **M07-26 y M07-28** sobrevivieron (no había prueba); T24 los mató (ronda 5).

**E2E, intermitencias.** En las corridas del conjunto de aislamiento con los tres navegadores a la vez, 2–4 pruebas fallan esperando `/auth/refresh` al entrar. Las pruebas que fallan son N6 y, una vez, el `beforeEach` de aislamiento en WebKit, y cambian de una corrida a otra. Es la deuda registrada E2E-N6-ENTRAR-UAB-INTERMITENTE (ciclo 09) y no una regresión:
- falla antes de cualquier aserción del producto;
- cambia de prueba y de navegador en cada corrida;
- en la canónica, 0 fallos.

Se hizo **una** corrida diagnóstica declarada (aislamiento en WebKit): 3/3.

## 10. Convergencia

Spec Kit convergido contra §1.1, §3, §4, §6 y los criterios de la reanudación. Los 24 GAP y los 2 del barrido están corregidos. 0 modelos sin clasificar y 0 rutas sin clasificar. Superficie de producto afectada revisada (`AFFECTED_PRODUCT_SURFACE_MATRIX.md`), con la ficha de pantalla de Tipos de movimiento en PASS. Contrato de extensión de Gobierno completo, sin implementación.

| Elemento | Valor |
|---|---|
| Datos | `DATA_REPAIR_EXECUTED = 0` |
| Gobierno | `GOVERNMENT_ENTITY/UNIT/AUTHORITY_IMPLEMENTED = 0` |
| Métricas de Gobierno | fundamentos 14/38 (36,8 %, F05 COMPLETE) · funcional 0/1 280 · UAT 0/122 · aceptado 0/122 |

## 11. Deudas

En `docs/roadmap/technical-debt-roadmap.md`, sección del ciclo 07:

| Deuda | Estado |
|---|---|
| ROLE-CATALOG-INSTALLATION-WIDE | CLOSED para roles nuevos |
| WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES | MEDIBLE, 0 en las bases medidas |
| WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO | LATENT |
| E2E-PUERTOS-FIJOS-ESTACION-MULTIPROYECTO | CLOSED (PDD-QA-PORTS-01) |
| INSTALLATION-AUTHORITY-FROM-ANY-TENANT | nueva, MEDIUM, `BLOCKING_FINAL_GOV` |
| ROLES-HEREDADOS-SIN-TENANT | nueva, LOW |
| SCOPE-DENIAL-AUDIT | nueva, MEDIUM, Gobierno |
| CAMPOS-IGNORADOS-EN-ESQUEMA | nueva, LOW |
| SALES-CONFIRMATION-EXTRA-WITHOUT-PRODUCT-500 | nueva, LOW |
| TIPOS-MOVIMIENTO-SIN-INDICADOR-GLOBAL | nueva, LOW |

Fuera de alcance y sin absorber: T052 RPO (HIGH, ciclo 08), E2E-TOTP-PASO-COMPARTIDO y E2E-N6-ENTRAR-UAB-INTERMITENTE (ciclo 09), T053–T055.
