# GOVERNMENT_PRODUCT_INVENTORY

> Medición sobre `develop` `0dbe632` (2026-10-29). Fuentes: IR de Gobierno v1.0 (`8f86615f…`), Biblioteca Normativa v1.0 (`4a980bb9…`), `government-architecture-baseline.md`, `government-start-readiness.md`, OpenAPI generado de la app, metadato SQLAlchemy, `src/layout/Sidebar.tsx`, `src/app/router.tsx` y `alembic/versions/`. Se leyó el producto real, no solo las Specs.

## 1. Lo que hay de Gobierno en el producto

| Superficie | Gobierno | Total del producto | Cómo se midió |
|---|---|---|---|
| Rutas de API | **0** | 422 (556 operaciones) | `app.openapi()`; ninguna ruta `gov`, presupuesto, contratación, bien, expediente ni trámite |
| Modelos / tablas | **0** | 206 | `Base.registry.mappers`; ningún `gov_*` |
| Migraciones | **0** | 63 ficheros en `alembic/versions` | sin `gov` en ningún nombre |
| Entradas de menú | **0** | 98, en 18 grupos | `Sidebar.tsx`; las dos coincidencias de «gobierna» son comentarios |
| Rutas de frontend | **0** | 112 | `router.tsx` |
| Specs de Gobierno | **0** | — | sin `specs/gov-*`; `GOVERNMENT_SPEC_STARTED = 0` |

**Conclusión:** KONTROL Gobierno no tiene hoy ninguna funcionalidad construida. Lo que existe es su planificación (IR, Biblioteca, línea base de arquitectura, readiness) y el núcleo compartido que Gobierno reutilizará.

## 2. Módulos

Los quince módulos salen de la IR §6–§7, §11 y §12. Se añaden dos filas para no omitir lo que el encargo nombra.

| Id | Módulo | Familia de procesos | Spec dueña | Menú | Rutas | Backend | Frontend | Documentos | Reportes | Auditoría | E2E | Procesos | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORG | Government Core: ente, estructura y autoridad | GOV-ORG | ninguna (GOV-0) | — | — | — | — | — | — | — | — | 7 | NOT_STARTED / BLOCKED |
| BUD | Presupuesto público | GOV-BUD | ninguna (GOV-1) | — | — | — | — | — | — | — | — | 13 | NOT_STARTED / BLOCKED |
| REQ | Requisiciones públicas | GOV-REQ | ninguna (GOV-2) | — | — | — | — | — | — | — | — | 5 | NOT_STARTED / BLOCKED |
| PROC | Contrataciones públicas / Licitaciones | GOV-PROC | ninguna (GOV-2) | — | — | — | — | — | — | — | — | 12 | NOT_STARTED / BLOCKED |
| CNT | Contratos públicos | GOV-CNT | ninguna (GOV-2) | — | — | — | — | — | — | — | — | 9 | NOT_STARTED / BLOCKED |
| WH | Almacén de consumo público | GOV-WH | ninguna (GOV-3) | — | — | — | — | — | — | — | — | 5 | NOT_STARTED / BLOCKED |
| TRE | Tesorería pública | GOV-TRE | ninguna (GOV-3) | — | — | — | — | — | — | — | — | 10 | NOT_STARTED / BLOCKED |
| ACC | Contabilidad pública | GOV-ACC | ninguna (GOV-3) | — | — | — | — | — | — | — | — | 8 | NOT_STARTED / BLOCKED |
| AST | Bienes públicos / Activo fijo patrimonial | GOV-AST | ninguna (GOV-4) | — | — | — | — | — | — | — | — | 11 | NOT_STARTED / BLOCKED |
| DOC | Expedientes y actos administrativos | GOV-DOC | ninguna (GOV-5) | — | — | — | — | — | — | — | — | 8 | NOT_STARTED / BLOCKED |
| CTL | Control interno, auditoría y rendición | GOV-CTL | ninguna (GOV-5) | — | — | — | — | — | — | — | — | 10 | NOT_STARTED / BLOCKED |
| DIG | Gobierno Digital: trámites e interoperabilidad | GOV-DIG | ninguna (GOV-6) | — | — | — | — | — | — | — | — | 3 | BLOCKED |
| HR | Gasto de personal e interfaz Atenea | GOV-HR | ninguna (GOV-7) | — | — | — | — | — | — | — | — | 3 | NOT_STARTED / BLOCKED |
| INT | Integraciones institucionales | IR §11 | ninguna (GOV-7) | — | — | — | — | — | — | — | — | 7 | NOT_STARTED / BLOCKED |
| REP | Reportes y tableros institucionales | IR §12 | ninguna (con su dominio) | — | — | — | — | — | — | — | — | 11 | NOT_STARTED / BLOCKED |
| — | **Prefecturas** (lo nombra el encargo) | — | — | — | — | — | — | — | — | — | — | 0 | **NOT_IN_REQUIREMENTS**: ni la IR v1.0 ni el repositorio lo contienen. Si es alcance, hace falta una fuente (MOQ-RETRO-02) |
| — | Activos Fijos **privados** (Spec 057) | línea Empresarial | 057 | — | — | — | — | — | — | — | — | — | `PLANNED / NOT_STARTED` (MASTER57). Es otra línea; no equivale a bienes públicos (línea base, «Private Fixed Assets vs Public Assets») |

Total: **15 módulos y 122 procesos**. El desglose está en `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.md`.

«Compras», «Tesorería», «Reportes» y «Auditoría» existen en el producto, pero son de la **línea Empresarial**: compras comerciales, tesorería de empresa, reportes privados y bitácora del núcleo. La línea base los clasifica como PRIVATE_ONLY o SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION. Por eso aparecen como «equivalente privado (no cuenta)» y no como avance de Gobierno.

## 3. Inventario de frontend (§28)

Cada superficie se enlaza a su línea; ninguna a un proceso de Gobierno, porque no existe ninguna. `UNMAPPED_FRONTEND_SURFACES = 0`.

| Grupo del menú | Entradas | Clase (línea base) | Proceso de Gobierno |
|---|---|---|---|
| Principal (inicio, mi licencia) | 2 | SHARED_CORE | — |
| Notificaciones, tareas, alertas, reglas, preferencias | 5 | SHARED_CORE (047) | — (motor para CNT-09, DOC-04) |
| Organización | 5 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION (empresa ≠ ente/unidad) | — |
| Maestros | 7 | PRIVATE_ONLY / SHARED_CONTRACT (terceros) | — |
| Inventario | 13 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION (comercial ≠ consumo) | — |
| Compras | 9 | PRIVATE_ONLY (compras comerciales) | — |
| Ventas | 11 | PRIVATE_ONLY | — |
| Tesorería | 11 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION | — |
| Fiscal | 7 | PRIVATE_ONLY (SENIAT 039–043) | — |
| Regulatorio | 5 | PRIVATE_ONLY (SICA/SIGESAI) | — |
| Aprobaciones | 3 | SHARED_CORE (045) | — (motor para CTL-01) |
| Documentos | 2 | SHARED_CORE (046) | — (almacén para DOC-01) |
| Comercial | 2 | PRIVATE_ONLY | — |
| Reportes | 3 | SHARED_CORE (motor 050) | — |
| Licenciamiento | 4 | SHARED_CORE (004) | — |
| Homologación | 3 | SHARED_CORE (instalación) | — |
| Seguridad | 3 | SHARED_CORE | — |
| Sistema (MFA, auditoría, diagnóstico) | 3 | SHARED_CORE | — |
| **Total** | **98** | | **0** |

Rutas de frontend: 112, todas de las clases de arriba. Pantallas, formularios, modales, asistentes, tablas y tableros de Gobierno: **0**.

## 4. Inventario de backend (§29)

| Módulo | Operaciones | Modelos | Clase |
|---|---|---|---|
| sales | 89 | 18 | PRIVATE_ONLY |
| treasury | 63 | 22 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| organization | 59 | 13 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| purchasing | 55 | 23 | PRIVATE_ONLY |
| master_data | 39 | 24 | PRIVATE_ONLY / SHARED_CONTRACT |
| inventory | 37 | 13 | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| fiscal | 32 | 13 | PRIVATE_ONLY |
| regulatory | 26 | 11 | PRIVATE_ONLY |
| identity_access | 25 | 11 | SHARED_CORE |
| approvals | 22 | 8 | SHARED_CORE |
| commercial | 22 | 11 | PRIVATE_ONLY |
| documents | 20 | 8 | SHARED_CORE |
| notifications | 20 | 11 | SHARED_CORE |
| licensing | 19 | 7 | SHARED_CORE |
| reporting | 10 | 3 | SHARED_CORE (motor) |
| homologation | 10 | 3 | SHARED_CORE |
| system, setup, audit, main | 8 | 5 (+ scheduler 2) | SHARED_CORE |
| **Total** | **556** | **206** | **Gobierno: 0** |

Comandos, jobs, reportes, documentos e integraciones de Gobierno: **0**.

## 5. Backend oculto, UI muerta y paridad (§32, §33, §74, §75)

| Métrica | Gobierno | Motivo |
|---|---|---|
| Backend sin frontend (`BACKEND_WITHOUT_FRONTEND`) | 0 | no hay backend de Gobierno |
| Endpoints sin proceso de negocio | 0 | ídem |
| Código obsoleto contado como avance | 0 | ningún avance de Gobierno se ha contado sobre código |
| Controles muertos (`DEAD_CONTROLS`) / parciales / marcadores | 0 / 0 / 0 | no hay UI de Gobierno |
| Paridad BD-API-UI por proceso | FAIL en los 122 | no existe ninguna de las tres capas |
| Paridad de documentos y reportes | FAIL donde aplica (78 y 104 procesos) | ningún documento ni reporte de Gobierno implementado |

La línea Empresarial sí tiene backend, pantallas y controles. Medir allí sus controles muertos y su backend oculto con esta norma es la retrospectiva privada (MOQ-RETRO-01), que queda fuera de este encargo.

## 6. Menú (§73)

| Métrica | Valor |
|---|---|
| USER_FACING_PROCESSES | 122 (los 7 de integración tienen monitoreo y gestión de lotes de cara al usuario) |
| PROCESSES_WITH_MENU_ENTRY | 0 |
| PROCESSES_WITHOUT_MENU_ENTRY | 122 |
| ORPHAN_MENU_ENTRIES (Gobierno) | 0 |
| ORPHAN_FRONTEND_ROUTES (Gobierno) | 0 |

## 7. Integraciones (§61)

| Integración | Propósito (IR §11) | Prioridad | Estado | Fallo / reintento / conciliación / auditoría | Dependencia de UAT |
|---|---|---|---|---|---|
| Atenea Nómina | lote aprobado → compromiso/causado/asiento/orden de pago, idempotente por ente-período-tipo-versión | P0 | BLOCKED (D-GOV-07) | sin diseñar | E2E-04 |
| Bancos | archivos/APIs con contrato del banco; maker-checker y conciliación | P0 | NOT_STARTED | sin diseñar | TRE-04, TRE-06 |
| SNC/RNC | consulta y validación de contratistas con provenance | P1 | BLOCKED (D-GOV-03) | sin diseñar | PROC-05 |
| SUDEBIP | reportes, codificación y notificaciones por mecanismo oficial; sin inventar API | P1 | BLOCKED (D-GOV-05) | sin diseñar | AST-02 |
| ONAPRE/ONCOP | exportación/importación por formato oficial versionado | P1 | BLOCKED (D-GOV-02/04) | sin diseñar | BUD-13, ACC-08 |
| Interoperabilidad del Estado | contratos N28/N26 con fuente, finalidad, versión, respuesta y fallos | P0 | BLOCKED (D-GOV-08) | sin diseñar | DIG-03 |
| Firma electrónica | proveedor o certificado solo cuando sea jurídicamente admisible | P1 | BLOCKED (D-GOV-08) | sin diseñar | DOC-05 |

Ninguna integración simulada se presenta como lista.
