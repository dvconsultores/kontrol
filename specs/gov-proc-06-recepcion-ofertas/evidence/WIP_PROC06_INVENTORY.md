# WIP_PROC06_INVENTORY (entrada del ciclo, 2026-11-09)

`HEAD = origin/develop = d8a3a2f`; 0 adelante, 0 atrás. `PUBLIC_UPSTREAM_REQUIRED = 0`. 22 ficheros de trabajo, más el SNAT (protegido, no tocado). Copia antes de modificar: `wip-entrada.patch` y `wip-entrada-untracked.tgz` en la caché de QA; la copia anterior se conserva. El código local es `CANDIDATE_WORK`.

| WIP_FILE | INTENDED_CAPABILITY | STATUS | DEFECT | KEEP | REWRITE | OWNER | DEPENDENCY |
|---|---|---|---|---|---|---|---|
| documents/models.py | `DocumentSeal` | REUSABLE | — | sí | no | DeepSeek | migración |
| documents/service.py | Sello, integridad, reglas | REQUIRES_CORRECTION | `documents_for` no filtra sellados: por recurso y paquetes aún los ven. Comprobación antes del docstring de `purge_blockers`. Código muerto en `purge_version` | parte | parcial | DeepSeek | — |
| documents/api.py | 404 por id, listado | REUSABLE | Import usado | sí | no | DeepSeek | service |
| government/models.py | Oferta, documentos, triggers | REUSABLE | — | sí | no | DeepSeek | migración |
| government/service_ofertas.py | Recepción | REQUIRES_CORRECTION | `ctx` indefinido; integridad contra la versión vigente, no la fijada; usa booleano como clave; `_evento` con columnas inexistentes; sin `official_id`; sin SoD; sin rollback de duplicado | parte | total | DeepSeek | esquemas |
| government/api_ofertas.py | Rutas | REQUIRES_CORRECTION | **Sin ninguna comprobación de permiso** (seguridad); imports duplicados; `_version` propio | no | total | DeepSeek | servicio |
| government/schemas_ofertas.py | Contrato | REUSABLE | Revisar contra salida | sí | ajuste | DeepSeek | — |
| government/service_expedientes.py | Pendiente de apertura | REQUIRES_CORRECTION | `GovernmentProcurementOffer` sin importar; atributo `estado` inexistente; pasa el objeto en vez del id; condición errónea | no | parcial | DeepSeek | modelo |
| government/schemas_expedientes.py | Campos de oferta | REUSABLE | — | sí | no | DeepSeek | — |
| government/service_expedientes_acciones.py | Folio rechaza sellado | REUSABLE | — | sí | no | DeepSeek | service |
| government/service_sod.py | `PROC03_RECIBIR` | REQUIRES_CORRECTION | **Regresión: eliminó `PROC03_CERRAR`** | no | parcial | DeepSeek | — |
| main.py | Registro de rutas | REUSABLE | — | sí | no | DeepSeek | api |
| setup/api.py, mfa_policy.py | Capacidad | REUSABLE | — | sí | no | DeepSeek | — |
| audit_catalog_entries.py | Eventos | REQUIRES_CORRECTION | Entidad `GovernmentProcurementOffer` frente a registro con entidad de expediente | no | parcial | DeepSeek | servicio |
| alembic 0081 | Esquema | REQUIRES_CORRECTION | **Perdió las tablas**; permiso `write` en vez de `receive`; CHECK reducido a un solo valor; Revises erróneo | no | total | DeepSeek | modelos |
| tests/test_gov_proc06_ofertas.py | Pruebas | REQUIRES_CORRECTION | Sin fixture `gobierno`; `_crear` con argumento inexistente; duplica ayudantes | no | total | DeepSeek | todo |
| 5 contadores de pruebas | Cardinalidades | REUSABLE | Validar al final | sí | no | DeepSeek | — |

DISCARD_FROM_CANDIDATE: ninguno de los ficheros; se reescriben dentro del candidato. NOT_PROC06: el SNAT.
**PROCESS_VIOLATION_P1_03 = CLAUDE_WROTE_SEMANTIC_CODE_AND_TEST** (ciclo anterior). Rutas a bloques y bloque en `Sidebar.test.tsx`: no se repiten; un bloque sin ruta se rechaza.
