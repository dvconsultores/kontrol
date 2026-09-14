# `/speckit.analyze` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> Análisis previo a implementación, 2026-09-14, sobre `88634a1`.

## 1. Cadena comparada

`spec.md` ↔ `clarifications.md` ↔ `plan.md` ↔ `checklist.md` ↔ `tasks.md` ↔
`traceability-matrix.md`, contra el código, las migraciones y las autoridades
citadas.

## 2. Detección exigida por el §92

| Detección | Resultado |
|---|---|
| Motor de notificaciones duplicado | No existe ninguno. Los avisos de interfaz no lo son (CL-047-12) |
| Motor de tareas duplicado | **Riesgo real** con la bandeja de la 045; cerrado por CL-047-02 y R-047-11 |
| Aprobación duplicada | No |
| Planificador duplicado | No existe ninguno; crearlo es OQ-047-01 |
| Proveedor duplicado | No; la 048 |
| Lógica de negocio dentro de la 047 | Excluida: FR-047-026 |
| Completar tarea altera el origen | Excluido: R-047-01, M047-05 |
| Idempotencia ausente | **Sin clave definida** hasta OQ-047-01 |
| Estado de lectura compartido | Excluido: R-047-02, M047-04 |
| Fuga de destinatario | Visibilidad revalidada en lectura (CL-047-03) |
| Empresa equivocada | `CompanyContext`; M047-03 |
| Tenant equivocado | M047-02 |
| IDOR | R-047-06/07, M047-07 |
| `datetime` ingenuo | CL-047-04, M047-10 |
| Historial por borrado | R-047-03/04, M047-09 |
| Fallo externo que borra la interna | R-047-05, M047-06 |
| Paginación de primera página | Página 3 con > 100 (T047-114) |
| Parámetros no soportados | Sin `limit`; prueba de parámetro no soportado |
| Deriva OpenAPI | T047-083 |
| Deriva ORM ↔ Alembic | T047-090 |
| Carrera de consultar y luego crear | T047-041, T047-111 |
| 500 aceptado como conflicto | M047-12 |
| Guardas de arquitectura posicionales | Solo `bloque_de_spec` |
| Material OQ | **2** |
| UNKNOWN | 0 |

## 3. Contradicciones

| ID | Contradicción | Estado |
|---|---|---|
| C-047-01 | `ADR-D0-003` da el planificador a la 047; `ADR-009` y el §29 impiden construirlo sin ADR | **Abierta** → OQ-047-01 |
| C-047-02 | FR-047-034 exige i18n; no existe, no tiene dueña y `R-D0-10-2` lo reserva a un cambio propio | **Abierta** → OQ-047-02 |

## 4. Hallazgos ajenos — registrados, no corregidos

| Hallazgo | Dueña | Clasificación |
|---|---|---|
| `GET /approvals/inbox` pagina con `limit` y `offset`, contra la invariante de selector paginado | 045 | `PREEXISTING` |
| `approvals_service.inbox` carga los pasos `IN_REVIEW` de **todas** las empresas, lee la solicitud de cada uno por separado y filtra por empresa en Python. El aislamiento se sostiene; el coste crece con el número de empresas | 045 | `PREEXISTING` |
| La fila 052 del máster espera un «planificador de retención»: el mismo mecanismo que OQ-047-01 | 052 | Dependencia a considerar en la decisión |

## 5. Recuento

| Puerta | Valor | Exigido |
|---|---:|---:|
| BLOCKER | **2** — OQ-047-01, OQ-047-02 | 0 |
| CRITICAL | 0 | 0 |
| CONTRADICTIONS | **2** — C-047-01, C-047-02 | 0 |
| ORPHAN REQUIREMENTS | 0 | 0 |
| ORPHAN TASKS | 0 | 0 |
| MATERIAL OQ | **2** | 0 |
| UNKNOWN | 0 | 0 |
| TRACEABILITY | 100 % documental (36/36) · 0 % implementada | 100 % |
| OWNER DEPENDENCIES | 3 — 048, 046, 003 (condicional) | — |
| OWNER GAPS | 1 — internacionalización | — |
| CONSTITUTION GATE | 16 PASS · 2 CONDICIONADAS · 2 PREVISTAS | — |

## 6. Veredicto

**`SPEC047 — BLOCKED BY MATERIAL DECISION`**

La autorización expresa del §4 del prompt exige las ocho puertas a cero. Tres no
lo están. **No se ejecuta `/speckit.implement`.**

## 7. Lo que no se hizo

Ni código, ni migraciones, ni permisos en el catálogo, ni pantallas, ni pruebas.
No se tocó la 045, ni la 046, ni la 048, ni la 049, ni `reportes:view`. No se
resolvieron MD-049-01 ni MD-049-02.
