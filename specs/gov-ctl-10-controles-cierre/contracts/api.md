# API: /api/v1/gobierno/cierres

Guardas: autenticación → permiso → empresa → módulo `gobierno`. Campos extra rechazados. Escrituras con If-Match sobre `version` de la política. El cliente no envía `company_id`.

| # | Método y ruta | Permiso | Estado | Respuesta |
|---|---|---|---|---|
| 1 | GET `/catalogo` | gobierno_cierre:view | — | `{acciones[{codigo, etiqueta}], tipos[{codigo, etiqueta, requiere_riesgo}]}` |
| 2 | GET `/politicas` (`accion_cierre?`, `estado?`, `pagina`, `tamano`) | view | — | `{items, total, resumen}` |
| 3 | POST `/politicas` | manage | — | 201 detalle |
| 4 | GET `/politicas/{id}` | view | — | detalle con `controles` e `historia` |
| 5 | PATCH `/politicas/{id}` (If-Match) | manage | BORRADOR | detalle |
| 6 | POST `/politicas/{id}/controles` | manage | BORRADOR | 201 detalle |
| 7 | DELETE `/politicas/{id}/controles/{control_id}` (If-Match) | manage | BORRADOR | detalle |
| 8 | POST `/politicas/{id}/activar` | activate | BORRADOR | detalle |
| 9 | POST `/politicas/{id}/retirar` | activate | BORRADOR o VIGENTE | detalle |
| 10 | GET `/bloqueos` (`accion_cierre?`, `desde?`, `hasta?`, `pagina`, `tamano`) | view | — | `{items, total}` leídos de auditoría |

**Entradas**: `PoliticaIn {nombre, accion_cierre, fundamento, vigente_desde, vigente_hasta?}`; `PoliticaCambios {nombre?, fundamento?, vigente_desde?, vigente_hasta?}`; `ControlIn {tipo, riesgo_minimo?, materialidad}`; `RetiroIn {motivo}`. Activar sin cuerpo.

**Detalle**: `id, codigo, nombre, accion_cierre, fundamento, estado, vigente_desde, vigente_hasta, efectiva_hoy, version, activada_por, activada_en, retirada_por, retirada_en, motivo_retiro, controles[id, tipo, riesgo_minimo, materialidad], historia[evento, detalle, usuario, instante]`.

**Errores**: 422 `GOV_CLOSURE_POLICY_INVALID`; 428 `GOV_CLOSURE_POLICY_IF_MATCH_REQUIRED`; 409 `GOV_CLOSURE_POLICY_STALE`, `_INVALID_STATE`, `_ACTIVE_EXISTS`; 404 `GOV_CLOSURE_POLICY_NOT_FOUND`; 409 `GOV_MATERIAL_CLOSE_BLOCKED`.

**409 GOV_MATERIAL_CLOSE_BLOCKED** (devuelto por los endpoints de cierre existentes de estructura y programa, sin cambio de ruta): `details {politica_codigo, politica_nombre, proceso, objeto_codigo, total, dueno: "Control Interno", controles[{tipo, etiqueta, materialidad, pendientes, muestra[≤5 {codigo|numero, titulo|asunto, ruta}], ruta_lista}]}`.

**Guarda** (interna): `service_cierres.evaluar_cierre(db, ctx, accion, objeto_tipo, objeto_id, objeto_codigo, ejercicio)`; sin política efectiva no hace nada.

**Auditoría** (`owner_spec` gov-ctl-10; entidad `GovernmentClosurePolicy`): GOV_CLOSURE_POLICY_CREATED, _UPDATED, _CONTROL_ADDED, _CONTROL_REMOVED, _ACTIVATED, _RETIRED, GOV_MATERIAL_CLOSE_BLOCKED (REJECTION; after: politica_codigo, politica_version, accion_cierre, objeto_tipo, objeto_id, objeto_codigo, ejercicio, controles[{tipo, pendientes}], total), GOV_MATERIAL_CLOSE_ALLOWED. Ocho acciones; catálogo 311 → 319.

**SoD**: proceso CTL-10: CTL10_REGISTRAR (crea), CTL10_ACTIVAR, CTL10_RETIRAR; guarda en activar y retirar; sin reglas por defecto. **CTL-04**: proceso CTL-10 con rastreo a `/gobierno/cierres/{id}`.

**Capacidad**: `gobierno_cierre` view, manage (STANDARD), activate (SENSITIVE). Recuentos de política MFA: SENSITIVE 52 → 53, STANDARD 51 → 53.
