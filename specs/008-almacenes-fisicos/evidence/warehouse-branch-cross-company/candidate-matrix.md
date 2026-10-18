# Matriz de candidatos (RUTA B; fuentes autoritativas leídas; prioridad conceptual: aislamiento > integridad > producción > …)
| Candidato | Fuente · dueña | Riesgo principal | Decisión de la dueña | Solapa OBS-09 | Alcance | Recomendación |
|---|---|---|---|---|---|---|
| **WAREHOUSE-BRANCH-CROSS-COMPANY** | observación de la delta OBS-01 · **008**; contrato ADR-D0-014 (ARCH-MC-001) y precedente `create_establishment` (404 `BRANCH_NOT_FOUND`, `test_n10`) | **multiempresa y multitenant**: almacén de A colgado de una sucursal de B o de otro tenant (medido, D1-D3) | **no**: contrato y respuesta ya escritos | no | 1 fichero de producto + pruebas | **SELECCIONADA** |
| WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY (nuevo, medido en este ciclo) | sonda T1/T2 · 008 | multiempresa: ubicación o zona de A con `location_type_id`/`zone_type_id` de B → 200 | probablemente no (mismo contrato) | no | mismo fichero | **no se absorbe**: candidata prioritaria del ciclo siguiente |
| ROLES-SIN-TECHO-DE-DELEGACION | roadmap · 003 | seguridad | **sí** (política de delegación no ratificada) | no | política | excluida |
| ADDITIONAL_UNBOUNDED_LISTING | `spec008-listados-sin-tope-delta.md` §13 · varias | rendimiento | **sí** (dueñas, consumidores, fiscal intocable) | no | 85 endpoints | excluida |
| ALMACENES-PAGINACION-LIMIT-OFFSET | roadmap · 008 | contrato | **sí** (rompe 12 pantallas y 10 suites) | no | transversal | excluida |
| OBS-04 SPEC-SEGURIDAD-SIN-CARPETA | inventario | documental | **sí** | no | documental | excluida |
| POLITICA-E2E-RED-RELOJ / E2E-PANTALLA-SIN-PINTAR | roadmap · 054 | QA | **sí** (política del arnés) | no | entorno | excluida |
| TEST-PG-CATALOGO-MARCA-DE-AGUA | roadmap · 054 | ninguno demostrado | no | no | diagnóstico | excluida (`NO_EFFECT` probable) |
| OBS-03 TESTCLIENT-RELANZA-EN-HILO | OBSERVACIONES · 054 | ninguno | no | no | guía | excluida (no accionable) |
SELECTED_ID WAREHOUSE-BRANCH-CROSS-COMPANY · dueña 008 · OWNER_DECISION_REQUIRED 0 · OBS09_INDEPENDENT 1 · SCOPE_BOUNDED 1 ·
ROOT_CAUSE_PROVABLE 1 (probada, D1-D3). WHY_NOW: única deuda medida de aislamiento multiempresa sin decisión pendiente.
