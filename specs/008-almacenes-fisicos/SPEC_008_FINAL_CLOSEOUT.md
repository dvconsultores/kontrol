# SPEC 008 — FINAL CLOSEOUT

**Almacenes físicos** · 2026-08-30 · rama `develop` · PostgreSQL **18.6**

---

## 1. Estado

**`SPEC 008 COMPLETE_100`**

Segunda Spec del proyecto en alcanzarlo, tras la 045.

## 2. Fases ejecutadas

| Fase | Contenido | Tareas | Estado |
|---|---|---:|---|
| F1 · Modelo e integridad | 8 tablas, restricciones, retirada del cascade, `0017` | 11 | DONE |
| F2 · Conversión de referencias | 2 columnas a FK real, `0018` con clasificación | 12 | DONE |
| F3 · Reglas de dominio | Cadena, régimen, orden, borrado, `allowed_actions` | 18 | DONE |
| F4 · API | 42 rutas | 9 | DONE |
| F5 · Pruebas de backend | 41 pruebas nuevas | 24 | DONE |
| F6 · Frontend | 3 pantallas | 12 | DONE |
| F7 · E2E y cierre | 15 E2E, cross-browser, axe, responsive | 10 | DONE |

**Orden real: F1→F2→F3→F4→F5→F6→F7.** El encargo (§4) manda respetar las
dependencias reales sobre los nombres de fase: aquí F7 es E2E y depende del
frontend. Lo que el orden protegía —**F2 antes que F4**, por P23— se cumple.

## 3. Modelo implementado

`Warehouse → Zone? → Aisle? → Rack? → Level? → WarehouseLocation`

8 entidades: 2 catálogos por empresa (`zone_types`, `location_types`), 4 tramos
intermedios y la hoja, más la extensión de `warehouses`. **Solo el almacén y la
ubicación son obligatorios.**

## 4. Warehouse

Extendido con `address`, `manager_id`, `description`, `location_managed`,
`structure_levels`, `structure_regime`, `code_policy`, `code_pattern` y
`version`. `UNIQUE (company_id, code)`. `branch_id` nulo = almacén central.
`allowed_actions` y `can_delete` los calcula el backend.

## 5. Locations

`WarehouseLocation` sustituye a `locations` **conservando los identificadores**:
ninguna clave foránea existente se rompió. Guarda la cadena completa, no solo el
padre inmediato. La etiqueta legible es **derivada**: renombrar una zona cambia
la etiqueta de sus ubicaciones sin tocar una sola fila de ubicación.

## 6. Structure levels

Declarados por almacén. `declared_levels` gobierna qué se puede crear, qué valida
la cadena y qué muestra la interfaz. Un tramo no declarado se rechaza con
`STRUCTURE_LEVEL_DISABLED`.

## 7. Integridad estructural

Régimen `INITIAL` → `OPERATIONAL`, **irreversible**. En operativo se rechazan
eliminar, reordenar, resemantizar o colapsar un tramo **utilizado**; un tramo
declarado sin nodos sí puede retirarse. El bloqueo lo produce el backend con
`code`, `reason`, `dependencies` y `allowed_actions`, y se verifica invocando la
API sin pasar por la interfaz.

## 8. Delete / deactivate

| Nodo | Borrado | Desactivación |
|---|---|---|
| Warehouse | Sin estructura, ubicaciones ni movimientos | Siempre |
| Zone/Aisle/Rack/Level | Sin descendientes y sin histórico **heredado** | Sin descendientes activos |
| Location | Sin movimientos, saldo ni reservas | Siempre |

Sin `cascade` destructivo y sin desactivación en cascada silenciosa. Verificado
además en la base: **todas** las claves foráneas hacia `warehouse_locations` son
`NO ACTION`, de modo que ni siquiera un error del ORM podría destruir historial.

## 9. Migración 0017

`SAFE_MIGRATION`. Crea catálogos y tramos, extiende `warehouses`, renombra
`locations` → `warehouse_locations` (con `ALTER INDEX` explícito en PostgreSQL,
que conserva los nombres al renombrar) y deriva `company_id` del almacén.
Aplica limpia sobre PostgreSQL 18.6. **PASS.**

## 10. Migración 0018

`BACKFILL_REQUIRED` + `MANUAL_REVIEW_REQUIRED` + `BLOCKING_ON_CRITICAL`.
Clasifica **antes de escribir**, evalúa el bloqueo, repara, anula, copia el texto
legado e impone las claves foráneas, en ese orden. **PASS.**

## 11. Huérfanos

| Clase | Acción | Verificado por |
|---|---|---|
| `VALID_REFERENCE` | Conservar | `test_caso_1` — 2/2 válidas, 0 filas modificadas |
| `RECONSTRUCTIBLE_ORPHAN` | Reparar con evidencia | `test_caso_2` — candidata única desde `inventory_movements` |
| `NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED` | `NULL` + legacy + incidencia | `test_caso_3` — `legacy_location_id` conserva el original |
| `CRITICAL_NON_RECONSTRUCTIBLE` | **BLOQUEA** | `test_caso_4` |

El caso crítico se verifica **por inspección de la base tras el aborto**, no por
el código de salida: `alembic_version` sigue en `0016`, `warehouse_locations` no
existe, no hay claves foráneas creadas y la referencia crítica sigue intacta.
**Cero escrituras aplicadas.**

Añadido sobre lo exigido: con **dos** candidatas la fila no se repara — degrada a
crítica. No se elige «la más probable» (`test_reconstruccion_ambigua_no_adivina`).

`legacy_path` conserva el texto original, incluido el espacio de `"A "`, y
**ninguna** zona, pasillo, rack ni nivel se crea automáticamente.

## 12. PostgreSQL

| | |
|---|---|
| Versión | **18.6** (PGDG `18.6-1.pgdg12+2`), la que fija `ADR-D0-001` |
| Instancia | QA aislada, sin Docker ni root; sin datos productivos |
| Migración limpia | `0001 → 0018` **PASS** |
| Upgrade pre-008 con datos | **PASS** — recuentos intactos, `legacy_path` preservado |
| Paridad de esquema | `alembic check` = 18 líneas, **idénticas** a la base pre-008 |

**La Spec 008 no introduce ni una sola línea de drift.** Las 18 son la deuda ya
escalada de la Spec 010.

## 13. Backend

`structure.py` (motor de dominio) + `warehouse_api.py` (42 rutas). Ninguna regla
de negocio codificada: la estructura es dato.

## 14. API

Las **18 rutas del contrato** están en OpenAPI, sin faltantes. 14 códigos de
error estables. `If-Match` sobre los nodos editables. `depth` y paginación en
`/structure`. `/locations/ordered` con `physical_order` para la Spec 031.

## 15. Frontend

`AlmacenesPage` (lista, búsqueda, alta con declaración de tramos),
`AlmacenDetallePage` (pestañas **solo de los tramos declarados**),
`UbicacionesPage` (búsqueda y orden físico). Páginas con URL propia, sin modales
para formularios. `tsc` y `eslint` limpios; 218/218 unitarias.

## 16. Simple warehouse

**PASS.** Crear, ubicar, consultar, editar, desactivar y reactivar sin declarar
un solo tramo. La interfaz **no muestra** pestañas de zona, pasillo, rack ni
nivel, comprobado en los tres navegadores.

## 17. Complex warehouse

**PASS.** Cadena completa por interfaz, etiqueta derivada correcta, orden físico
estable entre llamadas.

## 18. Multiempresa

**PASS.** Listar, consultar, crear hijos, modificar, desactivar y borrar sobre
recursos ajenos devuelven **404** —no 403— para no confirmar su existencia. La
referencia a un tramo de otra empresa se rechaza con `HIERARCHY_CROSS_WAREHOUSE`.

## 19. Seguridad

IDOR cerrado en almacén, tramo y ubicación. Alcance por empresa en toda consulta
y escritura. Sin asignación masiva: los cuerpos son modelos Pydantic explícitos.
`allowed_actions` se recorta por permiso del usuario; sin permisos, lista vacía.
Concurrencia optimista con `If-Match`, y la unicidad de código la garantiza una
restricción de base de datos, no una comprobación previa.

## 20. Auditoría

13 acciones sobre la capacidad transversal, sin tabla local: `CREATE`, `UPDATE`,
`DELETE`, `ACTIVATE`, `DEACTIVATE`, `BLOCK`, `BULK_CREATE`, `HIERARCHY_CHANGED`,
`STRUCTURE_LEVELS_CHANGED` y los **cuatro intentos denegados**
(`DELETE_BLOCKED`, `DEACTIVATE_BLOCKED`, `RELOCATE_BLOCKED`,
`STRUCTURE_CHANGE_BLOCKED`).

## 21-23. Unit, integration y contract tests

41 pruebas nuevas: 34 de estructura y dominio, 7 de migración. Contrato
verificado contra OpenAPI: 18/18 rutas. **317/317** en la suite completa.

## 24. E2E

5 escenarios sobre frontend real → API real → backend real → PostgreSQL real.
Nada del núcleo mockeado.

## 25. Cross-browser

| Navegador | Resultado |
|---|---|
| Chromium | **5/5 PASS** |
| Firefox | **5/5 PASS** |
| WebKit | **5/5 PASS** |

**WebKit se reporta como WebKit**, no como Safari. Edge y Opera no están
disponibles en el entorno: no se declara validación sobre ellos.

## 26. Responsive

320, 375, 768, 1024, 1280 y 1440 px sobre las pantallas de 008: **sin scroll
horizontal general**.

## 27. Accesibilidad

axe WCAG 2.2 AA sobre las tres pantallas: **0 violaciones serias o críticas**.
Operable con teclado. Las 22 violaciones responsive preexistentes de las Specs
005/054 **no** se corrigen aquí: siguen escaladas.

## 28. Rendimiento

Conjunto de **50.000 ubicaciones**, 20 zonas y 200 pasillos:

| Medida | Resultado | Umbral |
|---|---:|---|
| Búsqueda por código, P95 | **0,3 ms** | 200 ms |
| Consulta ordenada, P95 | **41,6 ms** | — |
| `/structure` por defecto | 53 ms, **sin ubicaciones** | — |
| `/locations/ordered` (100) | 192 ms | — |

`EXPLAIN` confirma `Index Scan using ix_warehouse_locations_wh_status`: sin
escaneo completo.

## 29. Regresión

**317/317** sobre PostgreSQL 18.6, sin exclusiones. `inventory` —el módulo de
mayor riesgo, cuyas dos referencias pasaron a FK— en verde sin cambio de
comportamiento.

Tres expectativas se actualizaron, ninguna se suavizó: dos por el cambio de
contrato a respuesta paginada (documentado y aprobado) y una por un fallo de
diseño de mi propia prueba, que ordenaba por identificadores aleatorios.

## 30. Trazabilidad

75 FR · 8 NFR · 40 AC · 96 tareas. **0 requisitos sin implementación, 0 tareas
sin requisito, 0 criterios sin evidencia.**

## 31. `/speckit.converge 008`

| Comprobación | Resultado |
|---|---|
| Autoridad única sobre la jerarquía (P22) | ✅ solo `organization` la define |
| Sin motor de aprobaciones propio | ✅ 0 |
| Sin auditoría local | ✅ usa la transversal |
| Sin permisos paralelos | ✅ extiende `organization:` con `delete` y `manage_structure` |
| Sin cascade destructivo | ✅ retirado, y todas las FK son `NO ACTION` |
| Sin otras Specs implementadas | ✅ 0 módulos ajenos tocados |
| Genericidad | ✅ 0 literales de estructura de cliente |
| Placeholders | ✅ 0 |
| Drift | ✅ 0 atribuible a 008 |

## 32. Deuda externa

| Deuda | Clasificación | Destino |
|---|---|---|
| 18 líneas de drift de licenciamiento | `DEFERRED_EXTERNAL_DEPENDENCY` | Spec 010 |
| 22 violaciones responsive preexistentes | `DEFERRED_EXTERNAL_DEPENDENCY` | Specs 005/054 |
| `qa/pg-provision.sh` sin camino a PostgreSQL 18 | `DEFERRED_EXTERNAL_DEPENDENCY` | Spec 054 |
| `cascade delete-orphan` en `Company→Branch` y `Branch→Establishment` | **Observación** | Fuera de la jerarquía física; la base lo bloquea con `NO ACTION`. Se escala, no se corrige aquí |
| `tsc` no detectó un import de paquete inexistente (`react-router-dom`) | **Observación** | Lo detectó el E2E; conviene revisar la configuración de tipos en Spec 054 |

Ninguna rompe un requisito de 008, todas tienen contrato y Spec destino, y 008
funciona completa sin ellas.

## 33. Specs desbloqueadas — verificadas por contrato

| Spec | Contrato disponible | Verificado |
|---|---|---|
| **022 · Put-away** | Búsqueda de ubicaciones con estado, tipo, jerarquía, capacidad y restricciones | `GET /locations` con 7 filtros |
| **031 · Cola y ruta de picking** | `GET /locations/ordered` con `physical_order`, orden total y determinista | `test_orden_fisico_determinista_y_estable` + E2E |
| **032 · Picking y consolidación** | `location_id` como FK real, búsqueda eficiente | `EXPLAIN` con índice |
| **023 · Inventario/Kardex (parcial)** | `location_id` es dimensión con FK real en movimiento y saldo | `test_las_dos_referencias_son_fk_reales` |
| **025 · Transferencias y conteos** | `source/destination/count_location` referenciables; `stock_count_lines` con FK | ídem |
| **019 · Recepción** | `destination_location_id` referenciable | FK real disponible |

Se declaran desbloqueadas por **contrato verificado**, no por el roadmap previo.

## 34. Próxima Spec

El roadmap sitúa **011 — Unidades y presentaciones** después de 008. Sigue siendo
correcto: 011 no depende de nada que 008 deje pendiente, y sí desbloquea a 012 y
al núcleo de inventario. **No se ha creado.**

## 35. Veredicto

**`SPEC 008 COMPLETE_100`**

0 BLOCKER · 0 CRITICAL · 0 contradicciones · 0 requisitos sin implementación ·
0 tareas obligatorias abiertas · PostgreSQL 18.x alineado con el ADR vigente ·
`0017` y `0018` PASS · los huérfanos críticos bloquean la migración · sin `NULL`
silenciosos · drift 0 · 317/317 backend · 218/218 frontend · 15/15 E2E en tres
navegadores · convergencia PASS.
