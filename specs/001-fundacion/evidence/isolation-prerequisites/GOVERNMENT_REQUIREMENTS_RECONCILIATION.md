# Reconciliación final con los requisitos de Gobierno (ciclo 07)

Fuente releída al cierre, el 2026-10-29: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, SHA-256 `8f86615f63ecfa0b…`, sin cambios desde el discovery. Se releyó en solo lectura y no se implementa nada de Gobierno (`GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0`). Biblioteca Normativa: solo se usan sus clases de fuente.

## Requisitos aplicables y qué deja el núcleo

| Requisito (texto de la fuente) | Qué deja certificado el núcleo | Qué sigue siendo de Gobierno |
|---|---|---|
| **RNF-GOV-001** (P0) «Cada tenant/ente debe tener aislamiento de datos, llaves, configuración y permisos; pruebas hostiles obligatorias.» | **Datos y permisos del tenant y la empresa:** 505 de 556 operaciones reciben una petición hostil medida y las 51 restantes son de instalación con motivo. Barridos IDS (228 rutas), LISTAS y CABECERA (482 rutas, no enumeración) sin hallazgos. ISOLATION-E2E en tres navegadores. Escáner de invariantes y guardas de modelos, rutas y frontend | Llaves y configuración por ente; la dimensión `entity` en el arnés y en el escáner (FUTURE_EXTENSION_CONTRACT §2) |
| **RNF-GOV-006** «Toda autorización crítica se valida en backend; no confiar en UI ni claims…» | La cabecera de empresa es una entrada: el servidor la resuelve y la valida (ISO-CAB-01). Ningún id del cliente concede autoridad (barridos de ids y de cuerpo). El frontend solo proyecta (guarda vitest) | — |
| **RNF-GOV-012** «Roles predefinidos no conceden autoridad transversal…» | Los roles van por tenant (OD-ISO-11); el homónimo de otro tenant no se revela (ISO-TEN-03) | El rol de plataforma (INSTALLATION-AUTHORITY-FROM-ANY-TENANT) |
| **GOV-ORG-001** «… sin compartir reglas entre tenants por defecto.» | OD-ISO-10: una petición de empresa ya no crea reglas globales (403 `GLOBAL_SCOPE_FORBIDDEN`); las globales existentes se miden | Perfil normativo por ente |
| **GOV-ORG-007** «… el frontend nunca decide company/ente scope.» | `FRONTEND_NEVER_DECIDES_SCOPE = 1` (guarda `alcance-frontend.test.ts`, mutante M07-32 muerto) | Alcance por ente, unidad y cargo |
| **GOV-CTL-004** «No permitir al administrador técnico fabricar autoridad funcional…» | Un tenant no ve, asigna ni duplica roles de otro (OD-ISO-11) | Separar la autoridad de plataforma de la funcional (`BLOCKING_FINAL_GOV = 1`) |
| **GOV-CTL-002/003/005** bitácora append-only, metadatos y consulta read-only del auditor | La bitácora del tenant y la empresa no se cruza (ciclo 04; mutante M07-29 muerto) | La autoridad, la unidad y la correlación institucional (F08) |
| **GOV-DOC-008** «búsqueda … con control de acceso» | La búsqueda y los recuentos no traen filas ajenas (BARRIDO-LISTAS con `q` = centinela ajeno, ISO-PAG-01, E2E de búsqueda en terceros) | La búsqueda por expediente y acto |
| **E2E-06** «… 100 % denegado y auditado.» | **Denegado:** el 100 % en tenant y empresa. **Auditado:** se audita el 403 de empresa (`COMPANY_SCOPE_DENIED`) | Auditar el 404 de no enumeración entre entes (SCOPE-DENIAL-AUDIT; OD de Gobierno) |
| Criterio de salida «sin bypass de SoD, cross-tenant o autorización backend.» | No hay bypass cross-tenant ni cross-company medido en API, almacén, reportes, exportaciones, documentos ni auditoría | SoD de Gobierno (E2E-07) y `AuthorityGrant` |

## Las once preguntas de cierre (§73)

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Todo modelo del núcleo tiene alcance? | Sí: 206, 0 sin clasificar | `SCOPE_MODEL_INVENTORY.md`, guarda g01, mutante M07-30 |
| ¿Toda ruta con estado tiene alcance? | Sí: 556, 0 sin clasificar, 505 con petición hostil | `SCOPE_ROUTE_INVENTORY.md`, guarda g03, mutante M07-31 |
| ¿Se valida todo id relacionado? | Sí: los 24 GAP corregidos; el resto por el triaje y el contrato de relaciones | T04–T10, T17; BARRIDO-IDS |
| ¿Puede el tenant B inferir A? | No: un id ajeno da la misma respuesta que uno inexistente; ISO-TEN-01..07 | ISO-CAB-01, ISO-TEN |
| ¿Puede A1 inferir A2? | No (mismo contrato) | ISO-CAB-01 con a1_op→A2 |
| ¿Pueden filtrarse recuentos o búsquedas? | No | BARRIDO-LISTAS, ISO-PAG-01, E2E de búsqueda |
| ¿Pueden filtrarse documentos o el almacén? | No: la clave es opaca y la descarga está acotada | `STORAGE_SCOPE_INVENTORY.md`, M07-27 |
| ¿Pueden filtrarse reportes o exportaciones? | No: la descarga y el fichero están acotados por empresa y la escritura es exclusiva | ISO-STO-01/02, M07-18/28 |
| ¿Puede filtrarse la auditoría? | No | ciclo 04; M07-29 |
| ¿Puede un campo de alcance del cliente conceder autoridad? | No: ni la cabecera, ni el cuerpo, ni un literal de rol en la UI | M07-24, M07-33, M07-32 |
| ¿Puede Gobierno extender el modelo sin rehacerlo? | Sí, añadiendo dimensiones (FUTURE_EXTENSION_CONTRACT) | — |

`ENGINEERING_REQUIREMENTS_DOCUMENT_REVIEWED = 1 · ENGINEERING_REQUIREMENTS_RECONCILED = 1 · APPLICABLE_REQUIREMENTS_COVERAGE = 100 % · UNEXPLAINED_REQUIREMENT_OMISSIONS = 0 · FUNCTIONALITY_ACCIDENTALLY_OMITTED = 0`.

**Veredicto:** `CORE_ISOLATION_PREREQUISITES = CERTIFIED` (fundamento técnico F05).
- Esto **no** hace a Gobierno `READY`.
- Siguen pendientes la línea separada de Gobierno (SPONSOR REVIEW y freeze), F06 (dimensión de ente), F08 (auditoría institucional) y las deudas citadas.
- Las métricas de producto de Gobierno no cambian: funcional 0/1 280 y lista para la dueña 0/122.
