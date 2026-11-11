# Plan · CTL-09

**Base:** develop `57ff082`, Alembic `0100_gov_ctl05_rendicion`. La migración nueva es `0101_gov_ctl09_actas`; antes de pedirla se hace `fetch` y se comprueban las cabezas.

**CONSTITUTION GATE:** PASS. N34 leída, 0 bloqueos materiales y 0 decisiones de la dueña. Se reutilizan ORG-03/04/06, TRE-01, PROC-03, DOC-02, CTL-05, CTL-02, storage, ReportLab y la infraestructura documental (Spec 046 y AdjuntosPanel).

**Presupuesto de DeepSeek:** como máximo 8 llamadas (C1a modelo/migración/cableado, C1b servicio/API/pruebas, C3 frontend, C5 E2E; el resto es reserva).

## Modelo

### `GovernmentHandoverAct` (`gov_handover_acts`)

Mixins UUID, Timestamp, CreatedBy y Version; `__scope__` COMPANY.

**Campos:**
- **Identificación y estado:** `company_id`, `codigo String(20)` (AE-AAAA-NNNN), `estado` (BORRADOR, SUSCRITA o VERIFICADA), `ambito` (ENTE o UNIDAD), `unit_id String(36)?`.
- **Saliente:** `assignment_id` (FK `gov_assignments`, **UNIQUE** con `company_id`) y la instantánea `saliente JSON` (funcionario, funcionario_codigo, cargo, cargo_codigo, unidad, unidad_codigo, figura, asignacion_codigo).
- **Receptor:** `receptor_official_id`, `receptor_assignment_id?` y la instantánea `receptor JSON` (funcionario y funcionario_codigo, y el cargo si existe).
- **Modalidad:** `modalidad` (ENTREGA o LEVANTADA_POR_RECEPTOR), `testigos JSON` (lista de {nombre, documento}) y `auditor_official_id?`.
- **Cabecera:** `motivo String(1000)`, `fundamento String(1000)`, `lugar String(200)`, `fecha_corte Date`.
- **Suscripción:** `fecha_suscripcion Date?`, `errores_deficiencias String(2000)?`, `suscrita_por?`, `suscrita_en?`, `snapshot JSON?`, `snapshot_sha256?`, `informe_storage_key?`, `informe_sha256?`, `informe_bytes?`.
- **Después de suscribir:** `remision_uai_fecha Date?` y `remision_uai_registrada_por?`.
- **Verificación:** `verificacion_numero String(50)?`, `verificacion_fecha Date?`, `verificacion_resultado` (CONFORME o CON_OBSERVACIONES), `verificacion_fundamento String(2000)?`, `verificada_por?` y `verificada_en?`.

**CHECK:**
- estado en el dominio;
- estado ≠ BORRADOR ⇒ hashes no nulos;
- estado = VERIFICADA ⇔ `verificacion_resultado` no nulo;
- modalidad LEVANTADA_POR_RECEPTOR ⇒ `auditor_official_id` no nulo.

### `GovernmentHandoverAnnex` (`gov_handover_annexes`)

**Campos:** `company_id`, `act_id` (FK), `codigo String(8)` (A11_1..A11_6, A17_1..A17_5), `titulo String(200)`, `obligatorio Bool`, `generable Bool`, `incluir_generado Bool`, `documento_ids JSON` (lista de ids de documentos vinculados al acta), `constancia String(1000)?`, `contenido JSON?` (congelado al suscribir), `documentos JSON?` (congelado: [{documento_id, version_id, sha256}]).

**Restricciones:**
- UNIQUE (`act_id`, `codigo`).
- CHECK: `incluir_generado` ⇒ `generable`.

### `GovernmentHandoverObservation` (`gov_handover_observations`)

**Campos:** `company_id`, `act_id` (FK), `fecha Date`, `texto String(2000)`, `registrada_por` y `registrada_en`.

### Disparadores PostgreSQL

Siguen el patrón de CTL-05, comparando `::text` en las columnas JSON:
- **Acta:** sin DELETE ni TRUNCATE. Si `snapshot_sha256` no es nulo, no cambian cabecera, instantáneas, snapshot ni informe.
- **Anexos:** sin UPDATE ni DELETE si el acta no está en BORRADOR.
- **Observaciones:** solo INSERT (sin UPDATE, DELETE ni TRUNCATE).

## Cableado

- **Migración y permisos:** `gobierno_actas` view, manage y verify (COMPANY), concedidos a FUNCIONAL_COMPLETO.
- **Registros de la aplicación:**
  - `setup/api.py`;
  - `mfa_policy.py`: manage y verify en SENSITIVE, view en STANDARD;
  - `audit_catalog_entries.py`: 9 acciones `GOV_HANDOVER_*` sobre `GovernmentHandoverAct`, con `owner_spec` `gov-ctl-09`: CREATED, UPDATED, ANNEX_RESOLVED, SUBSCRIBED, REMITTED, OBSERVED, VERIFIED, EXPORTED, INTEGRITY_CHECKED;
  - `service_auditoria.PROCESOS` añade ("CTL-09", "Actas de entrega", "gov-ctl-09");
  - `main.py`;
  - `documents/resources.py`: ResourceKind `GovernmentHandoverAct` (`gobierno_actas:view`, `("gov-ctl-09",)`).
- **Pruebas transversales:**
  - catálogo 475 → 484;
  - MFA SENSITIVE 65 → 67 y STANDARD 72 → 73;
  - techo de delegación 154 → 157;
  - CTL-04 GX02 añade "CTL-09";
  - ResourceKinds 33 → 34, con la semilla N9;
  - 3 pruebas de cabeza Alembic → 0101.

## API (`/gobierno/actas-entrega`)

| Método | Ruta | Capacidad | Resultado |
|---|---|---|---|
| GET | `/opciones` | view | `{ocupaciones:[{asignacion_id, codigo, funcionario, cargo, unidad, figura, estado, desde, hasta, fin_efectivo, maxima_autoridad}], funcionarios:[{official_id, codigo, nombre}], anexos:[{codigo,titulo,obligatorio,generable}], nivel_territorial}` |
| GET | `/actas` | view | Filtros `estado, texto, ambito, desde, hasta, pagina, por_pagina≤50`. Devuelve `{items, total, pagina, por_pagina}` |
| POST | `/actas` | manage | `{assignment_id, receptor_official_id, receptor_assignment_id?, modalidad, testigos?, auditor_official_id?, motivo, fundamento, lugar, fecha_corte}`; 201, ficha |
| GET | `/actas/{id}` | view | Ficha |
| PUT | `/actas/{id}` | manage + If-Match | Cabecera |
| GET | `/actas/{id}/anexos/{codigo}/vista` | view | Contenido generado al corte (vista previa; congelado si la acta está suscrita) |
| PUT | `/actas/{id}/anexos/{codigo}` | manage | `{incluir_generado?, documento_ids?, constancia?}`; ficha |
| POST | `/actas/{id}/suscribir` | manage | `{fecha_suscripcion, errores_deficiencias?}`; ficha |
| POST | `/actas/{id}/remision` | manage | `{fecha}`; ficha |
| POST | `/actas/{id}/observaciones` | manage | `{fecha, texto}`; 201, ficha |
| POST | `/actas/{id}/verificacion` | verify | `{numero, fecha, resultado, fundamento}`; ficha |
| GET | `/actas/{id}/acta.pdf` | view | Bytes guardados (409 si está en BORRADOR) |
| GET | `/actas/{id}/integridad` | view | `{estado: VALIDO\|INCOMPLETO, snapshot_ok, informe_ok, documentos:[{codigo, documento_id, estado}]}` |
| GET | `/actas/{id}/historial` | view | `{items:[{fecha, accion, accion_etiqueta, usuario}]}` |

### Ficha

- **Identificación y cabecera:** `id, codigo, version, estado, ambito, unidad (nombre o null), saliente{…}, receptor{…}, modalidad, testigos, auditor{funcionario,codigo}|null, motivo, fundamento, lugar, fecha_corte`.
- **Anexos:** `anexos:[{codigo, titulo, obligatorio, generable, incluir_generado, documento_ids, constancia, resuelto, documentos_congelados|null}]`, `anexos_pendientes:[codigo]` y `documentos_del_acta:[{id, nombre}]` (los vinculados por AdjuntosPanel).
- **Suscripción:** `fecha_suscripcion, errores_deficiencias, suscrita_por, suscrita_en, snapshot_sha256, informe{sha256,bytes}|null`.
- **Después de suscribir:** `remision_uai_fecha`, `observaciones:[{fecha,texto,registrada_por,registrada_en}]` y `verificacion{numero,fecha,resultado,fundamento,verificada_por,verificada_en}|null`.

### Errores

| Código | Caso |
|---|---|
| 404 `GOV_HANDOVER_NOT_FOUND` | Acta inexistente o de otro ente |
| 422 `GOV_HANDOVER_ASSIGNMENT_INVALID` | Ocupación saliente no válida |
| 422 `GOV_HANDOVER_RECEIVER_INVALID` | Receptor no válido |
| 422 `GOV_HANDOVER_WITNESSES_REQUIRED` | Faltan testigos o auditor en la modalidad del art. 9 |
| 422 `GOV_HANDOVER_CUTOFF_INVALID` | Corte fuera de la vigencia de la ocupación |
| 422 `GOV_HANDOVER_ANNEX_INVALID` | Anexo inexistente, generado no generable o documento no vinculado al acta |
| 422 `GOV_HANDOVER_ANNEXES_PENDING` | Anexos obligatorios sin resolver al suscribir |
| 422 `GOV_HANDOVER_INVALID_PAGE` | Paginación fuera de rango |
| 409 `GOV_HANDOVER_DUPLICATE` | Ya existe un acta para esa ocupación |
| 409 `GOV_HANDOVER_STATE` | Transición o edición no permitida |
| 409 `GOV_HANDOVER_NOT_SUBSCRIBED` | PDF o integridad pedidos en BORRADOR |
| 409 `VERSION_CONFLICT` | If-Match no coincide |
| 403 `GOV_HANDOVER_SAME_ACTOR` | La verificación la registra quien suscribió, el saliente o el receptor |

## Frontend

Menú Gobierno › «Actas de entrega» (después de «Expedientes de cuenta»), con las pantallas listado, nueva y ficha (`src/modules/gobierno/actas/`).

## E2E

Recorrido completo del acta:
1. crear;
2. resolver los anexos (documento y constancia);
3. suscribir;
4. descargar el PDF;
5. comprobar el snapshot frente a un hecho posterior;
6. remisión y observación;
7. verificación por otro usuario.

Además:
- **Negativas:** otro ente da 404, suscribir con anexos pendientes da 422 y editar una acta suscrita da 409.
- **Calidad:** Axe y 390/320 px.
- **Humo:** pantalla y capacidad `gobierno_actas:view` añadidas al humo.
