# KONTROL Enterprise · matriz de trabajo vigente

Ciclo `ENTERPRISE-REBASELINE-AND-NEXT-WORK-GATE-01`, 2026-11-06, `develop` `dbcf510`. Vista por línea de producto. La autoridad de
cada deuda sigue en `../technical-debt-matrix.md` y `../technical-debt-roadmap.md`.

`PRODUCT_LINE`: `ENTERPRISE_ONLY` (E), `SHARED_CORE` (S), `GOVERNMENT_ONLY` (G). «s/c» = sin severidad canónica.
Verificación: **M** medida en el árbol en este ciclo; **R** registrada en documentación, no reverificada.

## 1. Selección

**`SELECTED_CANDIDATE = T052-RPO-DESIGN-AND-OWNER-DECISION-GATE`** · SHARED_CORE · dueña 001/053 · HIGH.
Es un ciclo de diseño y decisión. `NEXT_CYCLE_IMPLEMENTATION_ALLOWED = 0`.

## 2. Matriz de candidatos

| CANDIDATE_ID | TITLE | LINE | OWNER_SPEC | STATUS | SEV | ROOT_CAUSE | REPRO | OWNER_DEC | EXT_DEP | SHARED / GOV | USER_IMPACT | DATA | SEC | RELEASE | SIZE | P1_OVERLAP | ELIGIBLE_NOW | RATIONALE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T052 BACKUP-SCHEDULE-RPO | RPO ≤15 min verificable | S | 001 / 053 | OPEN | HIGH | Proven: no hay planificación | Sí (estructural) | Sí | Base externa | Sí / bloquea release Gov | Pérdida de hasta todo lo no copiado | Alto | Medio | Alto | M | Bajo | Sí, como gate | Único HIGH de la franja backup/RPO; sin él, FR-001-083 no se cumple. **Seleccionado** |
| T053 BACKUP-PG-TOOLS-IN-OPS-IMAGE | Clientes PG en la imagen | S | 001 / 052 | OPEN | MEDIUM | Proven | Sí (estructural) | Versión de cliente | Docker para certificar | Sí / sí | `kontrol.py backup` falla | Alto | Bajo | Alto | S | Bajo | No | Prerrequisito probable de T052: se decide en el gate |
| SPEC054 cierre | Corrida oficial RC 0 | S | 054 | IMPLEMENTED — CERT PENDING | Bloqueo de release | n/a | n/a | No | Anfitrión dedicado | Sí / sí | Sin release certificada | Bajo | Medio | Alto | S | Alto | No | Sin anfitrión no es ejecutable |
| OBS-09 | Evidencia Docker del analizador | S | 046 | IMPLEMENTED — EXTERNAL_GATE | s/c | Proven | Requiere Docker | No | Docker | Sí / sí | Carga documental en imagen no probada | Bajo | Medio | Alto | S | Bajo | No | Prioridad 1 automática si llega la evidencia |
| ALMACENES-DESPLEGABLES-TRUNCADOS | Desplegables limitados a 50 almacenes | E | 008 | OPEN | s/c | Proven | Sí (> 50 almacenes) | No | No | No / No | No opera el almacén 51+ | Bajo | Nulo | Bajo | S | Bajo | **Sí** | Segundo: defecto funcional real, radio menor que la continuidad |
| SPEC057 | Activos fijos | E | 057 | PLANNED | Nueva funcionalidad | NOT_APPLICABLE | n/a | Sí, priorización | No | Bajo / Bajo | Alto, funcionalidad nueva | n/a | n/a | n/a | XL | Bajo | No | Ver baseline §7 |
| MOQ-RETRO-01 | Retrospectiva de completitud Enterprise | E | gobernanza | OPEN | MEDIUM | n/a | n/a | Sí | No | No / No | Sin métrica real de producto | Nulo | Nulo | Medio | L | Nulo | No | Debe decidirla la dueña |
| DT-13 | Cobertura de pruebas de página | S | 054 | OPEN (programa) | HIGH | Proven | Sí | Alcance | No | Sí / Sí | Regresiones de UI sin detectar | Bajo | Bajo | Medio | XL | Medio | No | Programa de ola, no ciclo acotado |
| DT-06 | Auditoría de organización y maestros | S | 006 / 051 | PARCIAL | HIGH | Proven | R | Contrato de eventos | No | Sí / Sí | Rastro incompleto en empresas, artículos y categorías | Medio | Medio | Medio | M | Medio | No | Catálogo de eventos sin fijar |
| DT-04 | `cost_center_id` sin tabla ni FK | E | 007 | OPEN | HIGH | Proven | R | Alcance de la 007 | No | Bajo / Bajo | Datos sucios | Medio | Nulo | Bajo | M | Bajo | No | Exige migración y backfill |
| KONTROL-PY-UPDATE-NO-OP | `update` declara éxito sin actuar | S | 052 | NUEVA | MEDIUM propuesta | Proven | Sí | No | No | Sí / Sí | Operadora cree actualizar | Medio | Bajo | Medio | S | Bajo | Sí | Por debajo de T052 |

## 3. Deuda abierta por severidad

Recuentos de lo registrado con severidad canónica; las filas nuevas de este ciclo no se cuentan.

| Severidad | Nº | Deudas |
|---|---|---|
| P0 / BLOCKER / CRITICAL | 0 | RUNTIME-LOCK-API-BOOT-FAILURE y RUNTIME-LOCK-OPERATIONS-CATALOG-EMPTY corregidas en local el 2026-11-07, sin publicar. DT-08 y DT-11 cerradas o sustituidas |
| HIGH | 4 | BACKUP-SCHEDULE-RPO (S, M, implementada en local; puertas externas) · DT-04 (E, R) · DT-06 (S, R, parcial) · DT-13 (S, R) |
| MEDIUM | 13 | BACKUP-PG-TOOLS-IN-OPS-IMAGE (M) · BACKUP-RTO-DATOS-REALES (R) · E2E-TOTP-PASO-COMPARTIDO (R) · DOCUMENT-UPLOAD-VALIDATION-REJECTION-NOT-AUDITED (R) · PRODUCT-COMPLETENESS-PRIVATE-LINE-UNVERIFIED (R) · INSTALLATION-AUTHORITY-FROM-ANY-TENANT (S, latente, R) · DT-10 (M) · DT-12 · DT-14 · DT-15 · DT-16 (M: `login_rate_limit_per_minute` sin consumidor) · DT-17 · DT-18 (R) |
| LOW | 19 | BACKUP-RESTORED-UI-SMOKE · E2E-PAGINACION-RELLENO-INEFICAZ · AUDIT-TIMELINE-TOTAL-LIMITADO · AUDIT-DYNAMIC-VALUES-NOT-STATIC · QA-REPRO-AUDIT-PROBES · REPORT-PERIOD-INPUT-ON-SNAPSHOT-REPORTS · AUDITORIA-PANTALLA-DUPLICADA · EXISTENCIAS-IDENTIFICADORES-CRUDOS · EXISTENCIAS-FILTROS-DEDICADOS-UI · NOTIFICATION-PREFERENCES-SQLITE-BOOL-OR · GUARD-Q02-CUERPO-LISTA · E2E-N6-PESTANAS-FF-WK · E2E-N6-ENTRAR-UAB-INTERMITENTE · E2E-MFA-08-FILA-BAJO-CARGA · ROLES-HEREDADOS-SIN-TENANT · CAMPOS-IGNORADOS-EN-ESQUEMA · SALES-CONFIRMATION-EXTRA-WITHOUT-PRODUCT-500 · TIPOS-MOVIMIENTO-SIN-INDICADOR-GLOBAL · DT-07 |
| s/c | 23 | ALMACENES-DESPLEGABLES-TRUNCADOS (M) · EMPRESAS-PLACEHOLDER-GENERICO · AUDITORIA-TIMELINE-FECHA-CRUDA · DATATABLE-CAPTION-EN-MODO-MANUAL · LISTADOS-SIN-RESPONSE-MODEL (incluye AUDIT-OPENAPI) · BUSQUEDA-Q-SIN-ESCAPE · AUDITORIA-OFFSET-EN-BITACORA-VIVA · DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD · DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500 · ADDITIONAL_UNBOUNDED_LISTING · ALMACENES-PAGINACION-LIMIT-OFFSET · MOVTYPE-GLOBAL-SIN-UNICIDAD · SEED-EMPRESA-CODIGO-NO-UNICO · OBS-04 · EMPRESAS-STATUS-SORT · EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR · POLITICA-E2E-RED-RELOJ-MEMORIA · E2E-PANTALLA-SIN-PINTAR · WAREHOUSE-BRANCH-FK-COMPUESTA · WAREHOUSE-CATALOG-TIPOS-INACTIVOS · WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES · WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO · E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY |

**Sin reconciliar, `UNKNOWN = 2`:** FECHAS-ZONA-DE-PRESENTACION y FECHAS-FORMATO-A-MANO. `b24b121` trató la zona horaria, pero
ninguna fuente declara su cierre. El siguiente ciclo que las toque debe verificarlas.

## 4. Bloqueos

| Tipo | Nº | Elementos |
|---|---|---|
| Decisión de la dueña | 26 | BACKUP-SCHEDULE-RPO · DT-04 · DT-06 · DT-07 · DT-12 · DT-16 · BUSQUEDA-Q-SIN-ESCAPE · AUDITORIA-OFFSET-EN-BITACORA-VIVA · DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD · DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500 · ADDITIONAL_UNBOUNDED_LISTING · ALMACENES-PAGINACION-LIMIT-OFFSET · MOVTYPE-GLOBAL-SIN-UNICIDAD · SEED-EMPRESA-CODIGO-NO-UNICO · OBS-04 · EMPRESAS-STATUS-SORT · EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR · POLITICA-E2E-RED-RELOJ-MEMORIA · E2E-PANTALLA-SIN-PINTAR · WAREHOUSE-BRANCH-FK-COMPUESTA · WAREHOUSE-CATALOG-TIPOS-INACTIVOS · WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES · WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO · AUDITORIA-PANTALLA-DUPLICADA · PRODUCT-COMPLETENESS-PRIVATE-LINE-UNVERIFIED · ROLES-HEREDADOS-SIN-TENANT |
| Entorno | 5 | CERTIFICATION-HOST-INFRASTRUCTURE (SPEC054) · OBS-09 · PRODUCTION-IMAGE-WITHOUT-LIBMAGIC (certificación de imagen) · IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED · BASE-IMAGE-RUNTIME-CONTENTS-NOT-CERTIFIED |
| Legal o externo | — | D0-07 (039–043, 056) · 044 · D0-06 (004) |

## 5. Frontera GOVERNMENT_ONLY

P2 no asume: GOV-ORG, BUD, PRO, CON, WHS, TRE, ACC, AST, DOC, CTL, DIG; AUDIT-ROLE-UNIT-CONTEXT; SCOPE-DENIAL-AUDIT;
AUDIT-RETENTION-POLICY en su parte legal de Gobierno. INSTALLATION-AUTHORITY-FROM-ANY-TENANT es latente en Enterprise: la parte de
rol de plataforma (GOV-CTL-004) es de Gobierno.

## 6. Matriz de candidatos tras T052 (2026-11-07)

`ENTERPRISE_NEXT_CANDIDATE_MATRIX`. T052 solo espera puertas externas.

| DEBT | PRIORITY | DEPENDENCIES | BLOCKERS | OVERLAP | ELIGIBLE | WHY |
|---|---|---|---|---|---|---|
| ALMACENES-DESPLEGABLES-TRUNCADOS | 1 | `listAllWarehouses` existente | Ninguno para producto; E2E espera PostgreSQL | Bajo | **Sí** | Defecto funcional Enterprise demostrado, sin decisión. **SELECTED_NEXT_ENTERPRISE_TARGET** |
| KONTROL-PY-UPDATE-NO-OP | 2 | Ninguna | Ninguno | Bajo con T052 | Sí | Falso éxito operativo, Shared Core; radio menor en producto |
| T052-A1-CLI-AUDIT-TEST | 3 | T052 | Política de reintentos | Sí, T052 | No | Exige frontera nueva demostrada |
| RESTORE-LEDGER-RESET | 3 | `backup_restore.py` | Ruta certificada | Sí, T052 | No | Toca la restauración certificada |
| DT-04, DT-06, MOQ-RETRO-01 | — | Decisión | Decisión de la dueña | — | No | Sin decisión |
| T054, T055, SPEC054, OBS-09 | — | Entorno | Excluidas | Sí | No | Fuera de alcance |

## 7. Matriz de candidatos tras los selectores de almacén (2026-11-07)

| DEBT | PRIORITY | OWNER_SPEC | DEPENDENCIES | ROOT_CAUSE_PROVEN | OWNER_DECISION_REQUIRED | EXTERNAL_GATE | OVERLAP | PRODUCT_IMPACT | ELIGIBLE | WHY |
|---|---|---|---|---|---|---|---|---|---|---|
| RECEPCION-ALMACEN-TEXTO-LIBRE | 1 | Compras | `useAlmacenesDeEmpresa` | Sí | No | Solo E2E | Bajo | Alto: recibir mercancía exige pegar un identificador | **Sí** | **SELECTED_NEXT_ENTERPRISE_TARGET** |
| KONTROL-PY-UPDATE-NO-OP | 2 | 052 | Ninguna | Sí | No | Docker para certificar | Bajo | Medio: falso éxito operativo | Sí | Por debajo: afecta a operación, no al flujo diario |
| ALMACENES-LISTADO-PRIMERA-PAGINA | 3 | 008 | ALMACENES-PAGINACION-LIMIT-OFFSET | Sí | Sí, estilo de contrato | No | Medio | Bajo: hay búsqueda | No | Decisión previa |
| T052-A1-CLI-AUDIT-TEST | 3 | 001 | T052 | Sí | No | No | Sí | Bajo | No | Política de reintentos |
| RESTORE-LEDGER-RESET | 3 | 001 | Restauración | Sí | No | PostgreSQL | Sí | Medio | No | Mismo bloqueo PostgreSQL |
| T061 y certificación T052 | — | 001 | PostgreSQL | No aplica | No | PostgreSQL | — | Alto | No | Sin entorno |

## 8. Matriz de candidatos tras el almacén de la recepción (2026-11-07)

| DEBT | PRIORITY | OWNER_SPEC | DEPENDENCIES | ROOT_CAUSE_PROVEN | OWNER_DECISION_REQUIRED | EXTERNAL_GATE | OVERLAP | PRODUCT_IMPACT | ELIGIBLE | WHY |
|---|---|---|---|---|---|---|---|---|---|---|
| RECEPCION-LINEA-ORDEN-TEXTO-LIBRE | 1 | 004/019 | `PurchaseOrderSummary.lines` | Por demostrar en rojo | No | Solo E2E | Bajo | Alto: bloquea recibir por interfaz | **Sí** | **SELECTED_NEXT_ENTERPRISE_TARGET** |
| IDENTIFICADORES-EN-TEXTO-LIBRE | 2 | Varias | Una por campo | Parcial | No | Solo E2E | Medio | Medio | No todavía | Hay que clasificar cada campo |
| KONTROL-PY-UPDATE-NO-OP | 3 | 052 | Ninguna | Sí | No | Docker para certificar | Bajo | Medio | Sí | No bloquea un proceso diario |
| ALMACENES-LISTADO-PRIMERA-PAGINA | 4 | 008 | Paginación | Sí | Sí | No | Medio | Bajo | No | Exige decisión de contrato |
| RECEPCION-ALMACEN-INACTIVO-ACEPTADO | 4 | 008/004 | Regla de negocio | Parcial | Sí | No | Bajo | Medio | No | Exige decisión |
| T052-A1-CLI-AUDIT-TEST | 5 | 001 | T052 | Sí | No | No | Sí | Bajo | No | Política de reintentos |
| RESTORE-LEDGER-RESET | 5 | 001 | Restauración | Sí | No | PostgreSQL | Sí | Medio | No | Mismo bloqueo |
| T061 y certificación T052 | — | 001 | PostgreSQL | — | No | PostgreSQL | — | Alto | No | Sin entorno |

## 9. Matriz de candidatos tras la línea de la orden (2026-11-07)

| DEBT | PRIORITY | OWNER_SPEC | DEPENDENCIES | ROOT_CAUSE_PROVEN | OWNER_DECISION_REQUIRED | EXTERNAL_GATE | OVERLAP | PRODUCT_IMPACT | ELIGIBLE | WHY |
|---|---|---|---|---|---|---|---|---|---|---|
| CATALOGO-SELECTORES-PRIMERA-PAGINA | 1 | 002 | Patrón `listAllWarehouses` | Por demostrar en rojo | No | Solo E2E | Medio | Alto: un artículo fuera de los 20 primeros no se puede comprar, vender ni mover desde esos selectores | **Sí** | **SELECTED_NEXT_ENTERPRISE_TARGET** |
| ORDENES-SELECTOR-RECEPCION-PRIMERA-PAGINA | 2 | 004 | Filtro por estado | Por demostrar en rojo | No | Solo E2E | Bajo | Alto: una orden antigua no se puede recibir | Sí | Corto, pero menor alcance que el catálogo |
| RECEPCION-OBSERVACION-FIJA | 3 | 004/019 | Decisión de captura | Parcial | Posible | Solo E2E | Bajo | Medio | No todavía | Hay que definir cómo se declara |
| TERCEROS-SELECTORES-PRIMERA-PAGINA | 3 | 002 | Patrón común | Sin medir | No | Solo E2E | Medio | Medio | No todavía | Depende de lo que salga del catálogo |
| IDENTIFICADORES-EN-TEXTO-LIBRE | 4 | Varias | Una por campo | Parcial | No | Solo E2E | Medio | Medio | No todavía | Hay que clasificar cada campo |
| KONTROL-PY-UPDATE-NO-OP | 4 | 052 | Ninguna | Sí | No | Docker para certificar | Bajo | Medio | Sí | No bloquea un proceso diario |
| RECEPCION-LINEA-PRODUCTO-HISTORICO | 5 | 004 | Datos reales | No | Sí | Autorización de la dueña | Bajo | Bajo a medir | No | No se puede medir sin datos |
| ALMACENES-LISTADO-PRIMERA-PAGINA | 5 | 008 | Paginación | Sí | Sí | No | Medio | Bajo | No | Exige decisión |
| RECEPCION-ALMACEN-INACTIVO-ACEPTADO | 5 | 008/004 | Regla de negocio | Parcial | Sí | No | Bajo | Medio | No | Exige decisión |
| T052-A1-CLI-AUDIT-TEST | 6 | 001 | T052 | Sí | No | No | Sí | Bajo | No | Política de reintentos |
| RESTORE-LEDGER-RESET | 6 | 001 | Restauración | Sí | No | PostgreSQL | Sí | Medio | No | Mismo bloqueo |
| T061 y certificación T052 | — | 001 | PostgreSQL | — | No | PostgreSQL | — | Alto | No | Sin entorno |
