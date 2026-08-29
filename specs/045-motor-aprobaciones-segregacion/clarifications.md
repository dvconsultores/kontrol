# CLARIFICACIONES — SPEC 045

| ID | Pregunta | Resolución | Fuente / decisor |
|---|---|---|---|
| CL-045-01 | ¿El motor orquesta flujos de trabajo generales (BPM)? | **No.** Resuelve aprobaciones: condición → niveles → decisión. Un motor BPM genérico es un producto distinto y no lo pide ningún documento maestro | Alcance §3 |
| CL-045-02 | ¿Los niveles son secuenciales o paralelos? | **Secuenciales entre niveles, paralelos dentro de un nivel.** El nivel 2 no abre hasta resolverse el 1; dentro de un nivel varios actores resuelven según cuórum | HU-045-09/10 |
| CL-045-03 | ¿Qué ocurre si un rechazo llega en el nivel 2? | Es **terminal para la solicitud**. No hay «rechazo parcial»: el documento vuelve a estado editable con el historial completo | R-D0-02-7 |
| CL-045-04 | ¿Cómo se expresa la condición sin caer en un motor de expresiones arbitrarias? | Condición **declarativa**: conjunto de predicados sobre dimensiones tipadas (campo, operador, valor), combinados con `AND`. Varias reglas cubren el `OR`. Descartado un DSL libre: sería difícil de auditar y de explicar a un contador | `ADR-D0-005` aplica el mismo criterio a precios |
| CL-045-05 | ¿Sobre qué se calcula la huella de obsolescencia? | **Solo sobre los campos que participan en la condición de las reglas aplicadas.** Sobre el documento completo, cualquier cambio cosmético invalidaría la solicitud y el control se volvería inutilizable | R-D0-02-9 |
| CL-045-06 | ¿El vencimiento de un paso aprueba o rechaza automáticamente? | **Ninguna de las dos.** Marca la solicitud como vencida y emite evento. Que el silencio equivalga a una decisión es incompatible con P5 y con la auditoría | FR-045-027 |
| CL-045-07 | ¿Puede un mismo usuario ocupar dos niveles distintos? | Sí, salvo que la política lo prohíba. Se añade `distinct_actors_across_levels` como opción de política, con **defecto `true`** para operaciones con segregación | HU-045-04 |
| CL-045-08 | ¿La delegación es por proceso o global? | **Por ámbito acotado**: tipo de proceso, empresa, sucursal o combinación. Una delegación global sin ámbito es posible pero debe declararse explícitamente | R-D0-02-8 |
| CL-045-09 | ¿Qué pasa con las decisiones tomadas bajo una delegación revocada? | **Permanecen válidas.** Revocar afecta al futuro, no reescribe la historia | P5 · FR-045-046 |
| CL-045-10 | Sin la Spec 046, ¿cómo se adjunta evidencia? | El modelo declara el contrato de vinculación desde el día uno. Mientras 046 no exista, la evidencia es `reason` y `observations` en texto. **La Spec 046 no exigirá cambios en el modelo de 045** | Alcance §3 |
| CL-045-11 | Sin la Spec 047, ¿cómo se avisa a un aprobador? | 045 **emite eventos de dominio** y expone la bandeja. El aviso activo (correo, notificación interna) es de 047. 045 no conoce a 047 | Alcance §3 |
| CL-045-12 | ¿Qué umbrales trae KONTROL de fábrica? | **Ninguno.** El producto entrega el motor y, opcionalmente, plantillas de política vacías. Los valores son de cada cliente | `OQ-02` · P8 |
| CL-045-13 | ¿Se migran las aprobaciones históricas con su política? | No: **se desconoce** qué política se aplicó porque no existía. Se migran cerradas con `LEGACY_UNVERSIONED`. Inventar una política retroactiva sería falsear la auditoría | FR-045-074 |
| CL-045-14 | ¿El motor puede bloquear una operación fiscal ya emitida? | **No.** Un documento fiscal emitido es inmutable (P4/P5). El motor aprueba operaciones *sobre* él —anulación, nota, reapertura de período— no el documento en sí | ADR-D0-007 |
| CL-045-15 | ¿Qué tipo de proceso identifica cada consumidor? | Un `process_type` de catálogo extensible por datos. Añadir un consumidor nuevo **no** requiere modificar el módulo de aprobaciones | FR-045-006 |

## Cuestiones que quedan como configuración, no como bloqueo

Conforme al §32 del encargo de D0 y a `POL-D0-001` §5, lo siguiente **no impide especificar ni
construir** el motor:

- Cuántos niveles tiene cada proceso en una empresa concreta.
- Qué umbral separa un nivel de otro.
- Qué rol o usuario resuelve cada nivel.
- Si una empresa exige o no segregación en un proceso dado.
- Vencimientos y delegaciones vigentes.

Todo ello es dato de implantación (`OQ-02`, `OQ-12`).
