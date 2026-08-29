# `/speckit.analyze` — SPEC 008 · ALMACENES FÍSICOS
## Reejecución tras el Gate pre-implementación (Controles 1, 2 y 3)

Fecha: **2026-08-30** · Rama `develop` · Análisis documental. **No se escribió
código productivo.** No se creó `0017` ni `0018`. No se ejecutó
`/speckit.implement`.

---

## 1. Cadena comparada

`Constitución v1.1` → `ADR vigentes` → `baseline arquitectónica` → `D0` → `G0` →
`spec.md` → `clarifications.md` → `research.md` → `plan.md` → `data-model.md` →
`contracts/` → `wireframes/` → `checklist.md` → `tasks.md` →
`acceptance-criteria.md` → `test-plan.md` → `risk-register.md` →
`traceability-matrix.md`, más los tres artefactos que el Gate incorpora:
`migration-0018-policy.md`, `structure-mutability-policy.md` y
`docs/governance/postgresql-version-validation.md`.

---

## 2. Artefactos — 15

| Artefacto | Estado | Cambio en el Gate |
|---|---|---|
| `spec.md` | Completo — 10 HU, **75 FR**, 8 NFR, **14 reglas no negociables** | +13 FR, +4 reglas |
| `clarifications.md` | Completo — 27 decisiones | +12 (CL-008-16..27) y la corrección de hecho |
| `research.md` | Completo | +3 comparativas: política de huérfanas, régimen de mutabilidad, dónde vive el bloqueo |
| `plan.md` | Completo | Estrategia `0018` endurecida; §10 de políticas normativas |
| `data-model.md` | Completo | `structure_regime`, `legacy_location_id`, reporte de migración, histórico heredado |
| `contracts/api-contracts.md` | Completo — **14 códigos de error** | +4 códigos estructurales, forma de la respuesta de bloqueo, régimen de `structure_levels` |
| `wireframes/wireframes.md` | Completo — 8 pantallas | +2: bloqueo estructural y borrar frente a desactivar |
| `checklist.md` | Completo | +3 bloques, uno por control |
| `tasks.md` | Completo — **96 tareas** | +26 |
| `acceptance-criteria.md` | Completo — **40 criterios** | +16; AC-008-18 **reescrito** |
| `test-plan.md` | Completo | §4 reescrita (6 casos), §10 nueva (8 casos), motor fijado en 18.x |
| `risk-register.md` | Completo — **18 riesgos** | +5; RSK-008-03 reescrito |
| `traceability-matrix.md` | **Regenerada por script** desde los artefactos | Item por item, sin rangos |
| **`migration-0018-policy.md`** | **Nuevo — normativo** | Control 1 |
| **`structure-mutability-policy.md`** | **Nuevo — normativo** | Control 2 |

---

## 3. Coherencia — verificada por comando, no afirmada

| Comprobación | Resultado |
|---|---|
| Requisitos funcionales sin tarea | **0** de 75 |
| Requisitos no funcionales sin tarea | **0** de 8 |
| Criterios de aceptación sin tarea que los cubra | **0** de 40 |
| Tareas sin requisito ni criterio | **0** de 96 |
| Colisiones de identificador de tarea | **0** |
| Documentos normativos citados que no existen | **0** |
| Códigos de error: contrato ↔ política | **14 ↔ 14**, coincidentes |

La matriz ya no usa rangos: cada uno de los 75 FR, los 8 NFR y los 40 AC aparece
con su lista concreta de tareas, generada desde `tasks.md`. Un rango como
«FR-008-050..056» ocultaba huérfanos; la comprobación item por item los expuso y
se cerraron **13 FR, 3 NFR y 25 AC** que no tenían tarea atribuida.

---

## 4. Contradicciones detectadas y resueltas

El Gate introdujo cambios sobre artefactos ya escritos. Se buscaron activamente
las contradicciones resultantes y se encontraron **cuatro**.

### C-01 · `AC-008-18` contradecía el Control 1 — **RESUELTA**

Decía: *«la referencia queda nula, se reporta y la migración **termina**»*. Eso es
exactamente lo que el Control 1 prohíbe. Reescrito: la fila se clasifica y la clase
decide; lo crítico bloquea. El criterio anterior queda explícitamente sustituido.

### C-02 · `checklist.md` conservaba «sin abortar» — **RESUELTA**

La línea *«Saldos y conteos huérfanos detectados y reportados, sin abortar»*
sobrevivía del ciclo anterior. Sustituida por la regla de clasificación.

### C-03 · Colisión de identificadores entre reglas y riesgos — **RESUELTA**

Las reglas nuevas se numeraron `R-008-11..17` y el registro de riesgos ya usaba
`R-008-11`, `R-008-12` y `R-008-13` para riesgos distintos. Dos cosas diferentes
con el mismo nombre en la misma Spec. Resuelto renumerando: las reglas pasan a
`R-008-4..R-008-10`, continuando la serie existente `R-008-1..3`, y los riesgos a
`RSK-008-01..18`. Sin ambigüedad.

### C-04 · Columna inexistente arrastrada desde el ciclo anterior — **RESUELTA**

Ver §5. Es la más importante porque no era una contradicción entre documentos,
sino entre los documentos y la realidad.

---

## 5. Corrección de hecho — `AdjustmentLine` no existe

Los artefactos del ciclo anterior afirmaban que **tres** columnas pasan a FK:
`InventoryBalance.location_id`, `AdjustmentLine.location_id` y
`StockCountLine.location_id`.

Verificado contra el esquema real desplegado sobre PostgreSQL 18.6:

```sql
select table_name from information_schema.columns
 where table_schema='public' and column_name='location_id';
--  inventory_balances
--  inventory_movements
--  stock_count_lines
```

**No existe `adjustment_lines`, e `inventory_adjustments` no tiene `location_id`.**
Se convierten **dos** columnas, no tres. Corregido en los nueve artefactos que lo
repetían.

Es precisamente el tipo de defecto que la regla de este proyecto —no confiar en
nombres, verificar la cadena completa— existe para atrapar: la afirmación se había
propagado por nueve documentos sin que nadie consultara la base.

---

## 6. Conformidad constitucional

| Principio | Veredicto | Evidencia tras el Gate |
|---|---|---|
| P2 autorización expresa | ✅ | Gate documental; se detiene antes de implementar |
| P3 trazabilidad | ✅ | Matriz item por item, 0 huérfanos en las cuatro direcciones |
| P4 núcleo fiscal separado | ✅ N/A | 008 no lo toca |
| **P5 dato histórico protegido** | ✅ **reforzado** | R-008-4 y R-008-5: prohibida la anulación de conveniencia; lo crítico bloquea. R-008-8: sin `cascade` destructivo. Régimen `OPERATIONAL` |
| **P6 backend es la autoridad** | ✅ **reforzado** | FR-008-093 y AC-008-39: el bloqueo se prueba invocando la API sin pasar por la UI |
| P8 sin reglas de negocio en código | ✅ | R-008-3, NFR-008-08, AC-008-22 |
| P11 accesibilidad y responsive | ✅ | NFR-008-04/05, AC-008-24 |
| P13 integridad transaccional | ✅ | FK reales, clasificación transaccional, concurrencia probada |
| P18 sin modales para formularios complejos | ✅ | NFR-008-06 → T-008-078 |
| **P21 paridad del motor** | ✅ **cerrado con evidencia** | PostgreSQL 18.6 validado por ejecución; ya no hay divergencia ADR/QA |
| P22 autoridad única | ✅ | 008 sigue siendo la única autoridad sobre estructura física |
| **P23 captura temprana** | ✅ **reforzado** | F2 antes que F4 se mantiene; y `legacy_location_id` conserva lo que la FK expulsa |

**0 violaciones. 0 enmiendas constitucionales requeridas.** Los tres controles solo
aplican principios existentes con más rigor.

---

## 7. Scope creep — comprobado

| Comprobación | Resultado |
|---|---|
| Tareas de recepción, put-away o picking | **0** |
| Endpoint o tarea de reestructuración | **0** — T-008-036h verifica que **no** exista |
| Requisitos del Gate que añaden funcionalidad | **0** — los 13 son restricciones |

Los controles **reducen** lo que la implementación puede hacer. FR-008-097 y
`structure-mutability-policy.md` §6 dejan la reestructuración explícitamente fuera,
con la arquitectura preparada para una Spec posterior.

---

## 8. Control 3 — resultado de la validación de PostgreSQL

| Comprobación | Resultado |
|---|---|
| Versión que fija `ADR-D0-001` | 18.x |
| Versión obtenida y validada | **PostgreSQL 18.6** (paquetes oficiales PGDG) |
| `alembic upgrade head` 0001→0016 | **Aplica completa, sin modificar ninguna migración** |
| Suite de backend | **276 passed** |
| `alembic check` frente a 16.2 | **18 líneas de drift en ambas, idénticas** |
| `UTF8` · `UTC` · `pgcrypto` · roles separados | Conformes |
| Esquema | 153 tablas · 362 `timestamptz` · **0** `timestamp` sin zona · 164 FK |

**Cero diferencias atribuibles a la versión del motor.** El ADR continúa vigente sin
modificación, en estado `CONFIRMED_BY_EXECUTION`. No procedía enmienda: la decisión
era correcta y lo que faltaba era la evidencia.

Se cerró además el conflicto documental **CON-01** (PostgreSQL 16 vs 18), abierto
desde el inventario de documentos.

---

## 9. Ambigüedades y duplicidad de autoridad

**Ambigüedades bloqueantes: 0.** Las doce cuestiones del Gate se resolvieron con
autoridad existente —Constitución P5, P6, P23 y `ADR-D0-001`— sin escalar.

**Duplicidad de autoridad: 0.** Los dos documentos normativos nuevos no compiten con
`spec.md`: lo restringen, y `plan.md` §10 declara esa relación explícitamente.

---

## 10. Riesgos

18 riesgos, todos con mitigación. Los cinco nuevos cubren lo que el Gate destapó:

| ID | Riesgo | Sev. |
|---|---|---|
| RSK-008-14 | Pérdida silenciosa de dato histórico en `0018` | **ALTA** |
| RSK-008-15 | Destrucción estructural por edición simple de `structure_levels` | **ALTA** |
| RSK-008-16 | La reconstrucción «adivina» entre varias candidatas | **ALTA** |
| RSK-008-17 | El bloqueo se implementa solo en la UI y la API queda abierta | MEDIA |
| RSK-008-18 | La regla de bloqueo paraliza despliegues legítimos | MEDIA |

RSK-008-18 merece nota: se mitigó **acotando** el bloqueo. Solo la clase D detiene la
migración, y exige saldo vivo o referencia crítica. El ruido —saldo cero, almacén sin
ubicaciones— es clase C y no detiene nada. Sin esa acotación, el Control 1 habría
cambiado un riesgo de pérdida de dato por un riesgo de parálisis operativa.

---

## 11. Veredicto

| Criterio | Resultado |
|---|---|
| Artefactos completos | ✅ 15/15 |
| Contradicciones detectadas | 4 |
| Contradicciones **sin resolver** | ✅ **0** |
| Blockers | ✅ **0** |
| Critical | ✅ **0** |
| Requisitos huérfanos | ✅ **0** |
| Tareas huérfanas | ✅ **0** |
| Criterios sin cobertura | ✅ **0** |
| Violaciones constitucionales | ✅ **0** |
| Scope creep | ✅ **0** |
| Divergencia PostgreSQL | ✅ **RESUELTA** |
| Afirmaciones sobre el código verificadas contra la base real | ✅ 7/7 |

**APTA PARA IMPLEMENTACIÓN.**

Condiciones cuando se autorice: orden **F1 → F2 → F3 → F4 → F7 → F5 → F6**, con F2
antes que la API por P23; toda verificación sobre **PostgreSQL 18.x**; `0018`
ejecutada y validada con los seis casos de datos preexistentes **antes** de exponer
ningún endpoint.
