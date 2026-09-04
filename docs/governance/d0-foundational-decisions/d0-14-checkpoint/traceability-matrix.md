# D0-14 · TRAZABILIDAD

| Requisito | OQ | Evidencia | Decisión | Dueño | Prueba futura | Estado |
|---|---|---|---|---|---|---|
| FR-D011-001 · el compromiso es independiente de la ubicación | 01 | `POL-D0-002` §7 «Nunca ubicación» | **R-D0-14-1** | 030 | reserva sobrevive al put-away | ✔ |
| FR-D011-002 · el put-away no crea ni elimina reservas | 01 | `POL-D0-002` §8, tabla cerrada de eventos | **R-D0-14-2** | 022 | guardia estructural | ✔ |
| FR-D011-003 · no asigna una reserva concreta a una ubicación | 01 | `POL-D0-002` §11 «no asigna ubicación» | **R-D0-14-4** | 031 | guardia estructural | ✔ |
| FR-D011-004 · el disponible del almacén se conserva | 01 | caso canónico | **R-D0-14-2** | 023 | 100 → `L1`, disponible 70 antes y después | ✔ |
| FR-D011-005 · `qty_reserved` no queda atado a la ubicación | 01 | `POL-D0-002` §7 | **R-D0-14-3** | 023 | disponible agregado por almacén | ✔ |
| FR-D011-006 · sin segundo motor de reservas | 01 | escritores medidos: solo `inventory/service.py` | **R-D0-14-5** regla 3 | 030 | guardia estructural | ✔ |
| FR-D011-007 · semántica de capacidad inequívoca | 02 | `capacity_uom` es `String(16)` libre; cero consumidores | **R-D0-14-6** | 022 | ningún rechazo por capacidad en V1 | ✔ |
| FR-D011-008 · sin bloqueo sin unidad ni fórmula | 02 | no existe fórmula de ocupación | **R-D0-14-6** | 022 | ídem | ✔ |
| FR-D011-009 · aviso solo si la comparación es válida | 02 | la unidad no está tipada | **R-D0-14-7**: sin aviso calculado en V1 | 022 | — | ✔ |
| FR-D011-010 · modo de selección explícito | 03 | cinco de siete atributos ausentes | **R-D0-14-8** manual | 022 | e2e de selección | ✔ |
| FR-D011-011 · sin automatismo sobre atributos inexistentes | 03 | `CatalogItem` auditado | **R-D0-14-10** | 022 | guardia estructural | ✔ |
| FR-D011-012 · la selección manual se valida en el backend | 03 | — | **R-D0-14-9** | 022 | ubicación ajena rechazada | ✔ |
| FR-D011-013/014 · misma empresa y mismo almacén | 03 | ARCH-MC-001 · clave foránea compuesta de la 008 | **R-D0-14-9** | 022 | multiempresa | ✔ |
| FR-D011-015 · sin transferencia entre almacenes | — | Spec 025 es su dueña | frontera declarada | 025 | guardia estructural | ✔ |
| FR-D011-016/017 · la asignación al picking es de la 031 | 01 | `POL-D0-002` §11 | **R-D0-14-4** | 031 | guardia estructural | ✔ |
| FR-D011-018 · el movimiento reconstruye el traslado | — | una sola columna `location_id`, medido | **R-D0-14-11** | 023 | paridad por ubicación | ✔ |
| FR-D011-019/020/021 · físico, estado, lote y serial se conservan | — | `ADR-D0-010` v2 | **R-D0-14-13** | 023 | conservación | ✔ |
| FR-D011-022 · la 022 puede reanudarse sin decisión nueva | — | las tres OQ cerradas | — | — | — | ✔ |
| FR-D011-023 · la 031 sigue bloqueada | — | la 022 no está implementada | — | — | — | ✔ |
| FR-D011-024 · código de producto = 0 | — | guardia de diff | — | — | — | ✔ |
| FR-D011-025 · trazabilidad 100 % | — | esta tabla | — | — | — | ✔ |

**Cobertura: 100 % (25/25). Huérfanos: 0. OQ materiales: 0.**
