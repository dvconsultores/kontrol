# FASE D0 — RESULTADO

| Campo | Valor |
|---|---|
| Fase | D0 — Decisiones fundacionales |
| Estado | **COMPLETADA** |
| Fecha | 2026-08-29 |
| Rama · HEAD | `develop` · `def2b52` |
| Decisiones | 13 de 13 resueltas o formalmente clasificadas |
| Artefactos | 12 documentos + 13 ADR + 6 políticas |
| Cambios en código | **0** |

---

## 1. Resumen ejecutivo

Las trece decisiones estructurales que condicionaban el roadmap quedan tomadas y documentadas.
**Once están cerradas para efectos de construcción.** Las dos restantes no impiden escribir Specs:
el licenciamiento tiene su arquitectura cerrada y, desde el 2026-10-07, la autoridad central implementada como servicio del propietario (Fase 1; la sincronización espera una decisión de autenticación); el gobierno fiscal
está cerrado y lo que falta es contenido tributario, que por definición no lo produce el software.

El resultado más importante no es el número de decisiones cerradas, sino un cambio de naturaleza:
**antes de D0 había cinco bloqueantes de proceso que aparentaban detener el desarrollo; después de
D0 no queda ninguno.** La mayoría no eran decisiones pendientes sino configuración pendiente, y la
confusión entre ambas cosas es lo que mantenía el proyecto en espera.

Cinco decisiones no requerían más que evidencia y criterio y se cerraron directamente: PostgreSQL
con paridad de producción, modelo genérico de almacén, snapshot de unidad y conversión, vínculo
pedido-factura y separación entre estado de documento y estado de mercancía. Cuatro quedaron con
arquitectura cerrada y valores del cliente pendientes: aprobaciones, reserva, reglas comerciales y
confirmación de pedido.

---

## 2. Por qué se ejecutó D0

El GAP Analysis determinó que faltan 31 de 56 Specs y que la deuda se concentra en la capa operativa
de almacén. Escribir esas Specs sobre decisiones implícitas habría reproducido el patrón que la
auditoría ya documentó: cuatro motores de aprobación divergentes, precios como texto libre,
ubicaciones desconectadas de las transacciones y una factura que no sabe a qué pedido pertenece.

Cada uno de esos casos nació igual — nadie decidió, cada módulo resolvió — y cada uno cuesta hoy una
migración.

---

## 3. Decisiones cerradas

| ID | Decisión | Qué queda decidido |
|---|---|---|
| **D0-01** | PostgreSQL | Motor obligatorio en desarrollo, CI, QA, staging y producción. SQLite solo con excepción declarada. Ninguna Spec alcanza `COMPLETE_100` sin evidencia sobre PG |
| **D0-04** | Almacenes | Jerarquía `Company→Branch→Warehouse→Zone→Location(aisle,rack,level,position)`. Sin zonas fijas. `location_managed` por almacén permite adopción gradual |
| **D0-08** | Documentos | Servicio transversal con vinculación polimórfica y versionado. Ningún módulo implementa adjuntos propios |
| **D0-09** | Unidad y presentación | Toda línea conserva unidad, presentación, factor congelado y cantidad base. El inventario va siempre en unidad base |
| **D0-10** | Estados de mercancía | 15 estados; el estado del documento y el de la mercancía son dimensiones independientes |
| **D0-11** | Pedido → factura | Vínculo obligatorio cuando la factura deriva de pedido; factura directa sigue existiendo con permiso y política |
| **D0-13** | Dimensiones | Matriz de 19 tipos de documento; `CostCenter` y `BusinessUnit` como maestros con FK real |

## 3b. Decisiones cerradas con configuración pendiente

| ID | Arquitectura cerrada | Falta del cliente |
|---|---|---|
| **D0-02** | Motor único de aprobaciones con política versionada, cuórum, segregación y delegación | Niveles, umbrales y resolutores |
| ~~**D0-03**~~ | ~~Disparador configurable, defecto `ORDER_RELEASED`~~ → **CLOSED 2026-09-02**: disparador fijo `ORDER_CONFIRMATION`, concurrencia garantizada en base de datos, prioridad por orden de compromiso | Solo `reservation_ttl_days` (CONFIG opcional) |
| **D0-05** | Nueve maestros comerciales, precedencia declarativa, snapshot obligatorio | Precedencia confirmada, límites de descuento, alcance de comisiones |
| **D0-12** | Confirmación como entidad y evento propios, segregación configurable con defecto restrictivo | Qué procesos exigen segregación |

---

## 4. Decisiones pendientes

Ninguna decisión de arquitectura queda pendiente. Lo pendiente es de otra naturaleza:

| ID | Estado | Naturaleza |
|---|---|---|
| **D0-06** | **CLOSED / IMPLEMENTED** (2026-10-07) | Frontera y hospedaje lógico resueltos: servicio del propietario, aislado, agnóstico de proveedor (`ADR-D0-006`, Fase 1). Sincronización autenticada implementada el mismo día (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`, convergida) |
| **D0-07** | LEGAL_VALIDATION_PENDING | Contenido tributario de 24 reglas |

---

## 5. Decisiones legales pendientes

Las **24 reglas** de `D0-fiscal-validation-matrix.md`, ninguna en estado `VALIDATED`:
IVA (4) · retención de IVA (3) · ISLR y Decreto 1.808 (4) · IGTF (2) · documentos y control (5) ·
libros y cierres (3) · regulatorio SICA/SIGESAI/SACS (3).

Requieren abogado tributario venezolano y contador público sobre el ejercicio vigente. **El equipo
de software no puede resolver ninguna**, y el mecanismo está diseñado para impedir que lo intente:
una regla no validada no puede emitir documento en producción.

---

## 6. Decisiones empresariales pendientes

| ID | Pregunta | Bloquea |
|---|---|---|
| OQ-07 | Hospedaje de la autoridad de licencias y custodia de la clave — **resuelta el 2026-10-07** (servicio del propietario, agnóstico de proveedor; custodia operativa = procedimiento del propietario) | Ya no bloquea; la sincronización autenticada quedó implementada el 2026-10-07 |
| OQ-02 | Niveles y umbrales de aprobación | Implantación |
| OQ-03 | Disparador de reserva y vigencia | Implantación |
| OQ-06 | Precedencia de precio, límites de descuento, comisiones | Implantación |
| OQ-09 | Modalidad de facturación y plazo de homologación | Spec 056 |
| OQ-05, OQ-12, OQ-13 | Mapa físico, segregación, dimensiones activas | Puesta en marcha |

---

## 7. ADR creados

Trece, todos en estado explícito y ninguno en `PROPUESTO`:

`ADR-D0-001` PostgreSQL · `002` Aprobaciones · `003` Reserva · `004` Almacenes · `005` Comercial ·
`006` Licenciamiento · `007` Fiscal · `008` Documentos · `009` UOM/presentación · `010` Estados ·
`011` Pedido-factura · `012` Confirmación · `013` Dimensiones.

Extienden `ADR-003`, `ADR-005` y `ADR-008` de `001-fundacion` sin duplicarlos.

---

## 8. Cambios futuros requeridos

| Ámbito | Cambio |
|---|---|
| Infraestructura | PostgreSQL en `compose.dev` y CI; roles separados; base de pruebas por ejecución |
| Modelo | 6 tablas de aprobaciones · 3 de almacén · 4 de documentos · 9 comerciales · 2 de confirmación · 2 de dimensiones |
| Líneas de documento | ~4 columnas nuevas en ~15 tablas (unidad, presentación, factor, cantidad base) |
| Ventas | 2 FK de factura a pedido; 2 estados nuevos; compuerta de facturación |
| Inventario | 7 estados nuevos; ubicación obligatoria según almacén; restricción de no sobre-reserva |
| Fiscal | Estado de validación en `TaxRuleVersion`; bloqueo de emisión con regla no validada |
| Auditoría | Instrumentar `organization` y `master_data` |

---

## 9. Migraciones futuras

| Clasificación | Casos |
|---|---|
| `NO_MIGRATION` | D0-01, D0-06 |
| `SAFE_MIGRATION` | D0-04 (esquema), D0-07, D0-08, D0-10, D0-12, D0-13 (esquema) |
| `BACKFILL_REQUIRED` | **D0-09**, D0-05 |
| `BACKFILL_REQUIRED` + `MANUAL_REVIEW_REQUIRED` | D0-02, D0-04 (datos), D0-13 (datos) |
| `BACKFILL_REQUIRED` + `DATA_LOSS_RISK` | **D0-11** — ya materializado |

Ninguna se ejecuta en esta fase.

---

## 10. Impacto sobre las 56 Specs

Ninguna Spec cambia de estado: D0 no implementa. Lo que cambia es el **criterio de aceptación** y
la **claridad del diseño**.

| Efecto | Alcance |
|---|---|
| Techo de `COMPLETE_100` condicionado a PostgreSQL | **56** |
| Modelo de línea afectado por unidad y presentación | 18 |
| Aprobación centralizada en lugar de propia | 13 |
| Dimensiones organizacionales normalizadas | 13 |
| Operación física habilitada | 10 |
| Evidencia documental habilitada | 10 |

---

## 11. Specs desbloqueadas

> **CORREGIDO EN GATE G0 (2026-08-29).** Esta sección afirmaba «las 13» y enumeraba 17. Ambas cifras
> eran incorrectas. La cifra verificada contra las dos matrices es **22**.
> Derivación auditable en `docs/governance/G0-correction-note.md`.

**Las 22 Specs que estaban bloqueadas por decisión implícita:**

007, 008, 011, 012, 015, 017, 018, 019, 020, 021, 022, 023, 025, 029, 030, 031, 032, 033, 034, 035, 045, 046.

Todas pueden especificarse a partir de ahora sobre una decisión escrita.

---

## 12. Specs todavía bloqueadas

**Para comenzar: ninguna.**

Para **cerrarse**:

| Spec | Bloqueo |
|---|---|
| Las 56 | BLK-D0-01 — PostgreSQL real (técnico, resoluble por el equipo) |
| 039, 040, 041, 042, 043, 014, 056 | BLK-D0-02 — validación tributaria (externo) |
| 004 | BLK-D0-07 — hospedaje de la autoridad: **resuelto** (2026-10-07, Fase 1); y sincronización autenticada implementada (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`, convergida el 2026-10-07) |

---

## 13. Nuevo orden recomendado

| Orden | Spec | Cambio | Motivo |
|---:|---|---|---|
| 1ª | **045** Motor de aprobaciones | = | Nodo de mayor grado; arquitectura ya cerrada en ADR-D0-002 |
| 2ª | **008** Almacenes físicos | = | Prerequisito de put-away, cola y ruta de picking |
| 3ª | **011** Unidades y presentaciones | **▲ desde 5.ª** | Riesgo histórico máximo (H-01): el dato no capturado no se recupera |
| 4ª | **046** Gestión documental | = | Habilita evidencia en importación, incidencias y despacho |
| 5ª | **012** Maestros comerciales | **▼ desde 3.ª** | Alto riesgo histórico, pero menor que H-01, y depende de 045 |

Único reordenamiento sustantivo: **011 y 012 intercambian posición**, por análisis de datos no
reconstruibles.

---

## 14. Próxima Spec

**`045 — Motor de aprobaciones y segregación`**

Razón: es el nodo de mayor grado de salida del grafo (bloquea 015, 017, 025, 030, 033 y 047), ya
existen cuatro implementaciones divergentes que crecerán con cada Spec nueva, y su arquitectura está
cerrada en `ADR-D0-002` y `POL-D0-001`. Los umbrales desconocidos no la bloquean: son configuración.

**No se crea en esta fase. Requiere autorización expresa.**

---

## 15. Riesgos

| # | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| R-01 | Cada día sin D0-09 y D0-11 amplía el histórico irrecuperable | **ALTA** | Adelantar la captura del dato a la Ola 0 (E-03) |
| R-02 | La validación tributaria puede tardar más que el desarrollo | **ALTA** | Iniciar la contratación ahora; la Ola 7 es paralelizable desde hoy |
| R-03 | Pérdida de la clave privada de licencias invalida todas las licencias | **ALTA** | Definir custodia y respaldo antes de emitir la primera |
| R-04 | Al ejecutar sobre PostgreSQL aparecerán fallos hoy ocultos | MEDIA | Es el objetivo del cambio; planificar tiempo de corrección |
| R-05 | La presión por entregar puede llevar a cargar valores fiscales «provisionales» | MEDIA | El bloqueo de emisión con regla no validada lo impide por diseño |
| R-06 | Los 15 ADR fundacionales siguen sin aprobar (OQ-14) | MEDIA | Someterlos a aprobación o sustituirlos |
| R-07 | Saltar a las Specs visibles (034, 035) antes que a las fundacionales | MEDIA | El grafo de dependencias y esta resolución lo documentan |

---

## 16. Conclusión

D0 cumple su objetivo: **ninguna de las próximas Specs de KONTROL comenzará sobre una decisión
estructural implícita.**

Trece decisiones documentadas con alternativas, descartes razonados, regla definitiva, modelo
conceptual, impacto en siete dimensiones y clasificación de migración. Once cerradas para
construcción, dos clasificadas correctamente como externas al software.

Y un resultado que no estaba previsto: cinco de los siete bloqueantes que el GAP Analysis presentaba
como frenos del desarrollo **no lo eran**. Eran configuración de cliente confundida con decisión de
producto. Separarlas es lo que permite que el trabajo pueda empezar.

**La fase se detiene aquí. Se solicita autorización expresa para comenzar la Spec 045.**
