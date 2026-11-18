# Plan · GOV-TRE-03 · Orden de pago

## Constitution gate

| Compuerta | Estado |
|---|---|
| Autorización expresa que nombra TRE-03 | PASS (encargo 2026-11-17) |
| MATERIAL OQ | 0. El encargo fija la autoridad, el beneficiario, la política, la SoD y las fronteras. Las decisiones de diseño de Claude están abajo (PDD) |
| Contradicciones | 0 |
| Migración | `0124_gov_tre03_orden_pago`, down `0123_gov_bud09_causado`. No se toca 0123 |
| Cero hardcode | Política, documentos, numeración y regla SoD son datos del ente |
| DeepSeek | `deepseek-v4-pro`, objetivo 4–6, tope 8. No se hereda ninguna excepción |

## Decisiones de diseño (PDD, de Claude)

- **PDD-TRE03-01:** la proyección neutral `app/modules/government/proyeccion_obligaciones.py` importa solo modelos. Ofrece `montos_ordenados(db, company_id, cause_ids)` y `montos_pagados(db, company_id, order_ids)`; esta última devuelve 0 hasta TRE-04, en un solo lugar. BUD-09 y TRE-03 la consumen y no hay ciclo de importaciones.
- **PDD-TRE03-02:** el beneficiario no se escribe en la orden: es el beneficiario común de sus causados, comparado tras `strip()` y de forma exacta. Ver FR-05.
- **PDD-TRE03-03:** la política no se elige por el tipo de gasto de un solo causado. El usuario elige la política vigente; si esta tiene `tipo_gasto`, cada causado debe venir de una política de causado del mismo tipo.
- **PDD-TRE03-04:** los documentos se referencian, no se copian. Valen los documentos vinculados al ejercicio (patrón BUD-09) y los ya congelados como evidencia `DOCUMENT` de un causado de la orden.
- **PDD-TRE03-05:** la anulación exige un cargo con la competencia de la política en vigor en la fecha de anulación, más la autoridad funcional, sin control de límite (anular no compromete monto).
- **PDD-TRE03-06:** la SoD se evalúa por causado, con el proceso TRE-03 sobre el objeto `GovernmentBudgetCause`. El actor de TRE03_CAUSAR sale de un resolvedor (`formalizado_por`); el de TRE03_ORDENAR, de las órdenes emitidas vigentes con ese causado. Si P2 publica GOV-SOD-COVERAGE-01 antes del cierre, TRE-03 usa su autoridad de eventos.

## 1. Modelo (migración 0124)

| Tabla | Claves |
|---|---|
| `gov_payment_order_settings` | 1 por empresa; `patron` (por defecto `{ANIO}-{NUMERO:5}`, configurable) |
| `gov_payment_order_policies` | `codigo` (único por empresa), `nombre`, `descripcion`, `tipo_gasto` NULL = todos, `requiere_expediente_completo`, `competencia_accion` = ORDENAR_PAGO, `competencia_materia` = TESORERIA, `vigente_desde/hasta`, `fundamento`, `act_id`, `tipo_regla` (INSTITUTIONAL_POLICY \| OPERATIONAL_CONFIGURATION \| LEGAL_MANDATORY), `estado`, activación y cierre, `version` |
| `gov_payment_order_policy_documents` | `document_type_id`, `obligatorio`, `etapa` = EMISION, `condicion` |
| `gov_payment_order_policy_history` | append-only |
| `gov_payment_orders` | `year_id`, `policy_id` + `policy_version`, `estado` BORRADOR/EMITIDA/ANULADA, `numero`, `codigo`, `fecha_orden`, `moneda`, `monto` (> 0, = Σ líneas), `beneficiario` (NULL solo en BORRADOR), `concepto`, autoridad en instantánea, `emitida_por/en`, `snapshot`, `huella`, anulación (`anulada_por/en`, `motivo_anulacion`, cargo), `version` |
| `gov_payment_order_lines` | `order_id`, `cause_id`, `monto > 0`, única (`order_id`, `cause_id`) |
| `gov_payment_order_documents` | `order_id`, `document_id`, `document_type_id`, `document_version_id`, `sha256`, `snapshot`, único (`order_id`, `document_id`) |
| `gov_payment_order_history` | append-only |

Todas llevan `__scope__ = Scope.COMPANY`. Disparadores PG: una orden EMITIDA solo puede pasar a ANULADA; sus líneas y documentos no cambian fuera de BORRADOR; las historias son append-only (patrón 0123). El CHECK `ck_gov_sod_rules_proceso` suma `TRE-03`.

## 2. Parametrización

| Regla | Clase |
|---|---|
| FR-01, FR-02, FR-04, FR-10, FR-11, FR-12 y FR-17 | Invariante de plataforma (N03, N05) |
| Documentos exigidos, expediente completo, tipo de gasto y competencia | INSTITUTIONAL_POLICY (`tipo_regla` de la política) |
| Separación causar/ordenar | INSTITUTIONAL_POLICY en CTL-01 |
| Numeración | OPERATIONAL_CONFIGURATION |

## 3. API (`/api/v1/gobierno/tesoreria`)

| Método | Ruta | Permiso `gobierno_ordenes_pago` | MFA |
|---|---|---|---|
| GET/PUT | `/ordenes-pago/configuracion` | view / policy | — |
| GET/POST | `/politicas-orden-pago` | view / policy | — |
| GET/PUT | `/politicas-orden-pago/{id}` (If-Match, solo BORRADOR) | view / policy | — |
| POST | `/politicas-orden-pago/{id}/activar` · `/cerrar` | policy | sí |
| GET | `/ejercicios/{year_id}/ordenes-pago` (filtros) · `/reporte.csv` · `/opciones` | view | — |
| POST | `/ejercicios/{year_id}/ordenes-pago` | manage | — |
| GET/PUT | `/ordenes-pago/{id}` (PUT If-Match, solo BORRADOR) | view / manage | — |
| GET | `/ordenes-pago/{id}/controles` | view | — |
| POST | `/ordenes-pago/{id}/emitir` | issue | sí |
| POST | `/ordenes-pago/{id}/anular` | cancel | sí |

Permisos nuevos: `gobierno_ordenes_pago` con view, manage, issue, cancel y policy. Son SENSITIVE issue, cancel y policy. El catálogo pasa de 177 a 182 permisos y SENSITIVE de 80 a 83. La auditoría suma 9 eventos `GOV_PAYMENT_ORDER_*` (593 → 602).

## 4. Frontend (`src/modules/gobierno/tesoreria/ordenes-pago/`)

| Pantalla | Ruta |
|---|---|
| Lista: ejercicio, filtros, CSV y «Nueva orden» | `/gobierno/tesoreria/ordenes-pago` |
| Nueva / editar: obligaciones elegibles con causado, ordenado y pendiente; compatibilidad; montos; fecha; política; documentos; autoridad | `/gobierno/tesoreria/ordenes-pago/nueva`, `/:id/editar` |
| Detalle: controles, emitir y anular (MFA), causados con su nuevo pendiente, historia y «qué sigue» (TRE-04) | `/gobierno/tesoreria/ordenes-pago/:id` |
| Políticas: lista y ficha con documentos, activar y cerrar, numeración | `/gobierno/tesoreria/politicas-orden-pago`, `/:id` |

El menú vive en la sección «Gobierno · Tesorería» (superficie GOVERNMENT). Se registran `router.tsx`, `pantallas.ts` y `Sidebar.tsx`.

## 5. Motor de procesos

| Componente | En TRE-03 |
|---|---|
| ProcessDefinition / Version | Política versionada |
| Stages / Transitions | BORRADOR → EMITIDA → ANULADA |
| AuthorityBinding | Competencia de la política a la fecha de la orden, autoridad funcional y límite (TRE-09) |
| DOCUMENT_RULES / EVIDENCE_RULES | Documentos de EMISION y expediente completo |
| CONTROL_RULES | `/controles` |
| SOD_RULES | CTL-01, proceso TRE-03 |
| RESPONSIBILITY_BINDING | Autoridad en instantánea |
| NORMATIVE_BINDING | `fundamento` + `tipo_regla` |
| TENANT_POLICY | Política, configuración y regla SoD por empresa |

## 6. Pruebas

- **Backend:** encargo §39 y §40 (incluida la carrera real en PG).
- **Mutaciones:** encargo §41.
- **Vitest:** encargo §42.
- **E2E `gobierno-tesoreria-orden-pago`:** encargo §43, a 1280/390/320 px con Axe.
- **Humo UAT:** las dos pantallas nuevas.
