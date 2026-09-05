# PREGUNTAS ABIERTAS

Clasificación estricta: **CONFIG** = configuración de cliente (no bloquea) ·
**BUSINESS** = decisión empresarial · **LEGAL** = validación tributaria · **GOV** = gobierno interno.

| ID | Decisión | Pregunta | Clase | Quién responde | Bloquea |
|---|---|---|---|---|---|
| OQ-01 | D0-01 | Dimensionamiento de recursos y del pool por instalación | CONFIG | DevOps en implantación | No |
| OQ-02 | D0-02 | ¿Cuántos niveles, con qué umbrales y qué rol resuelve cada proceso? | BUSINESS | Producto · Compras · Finanzas | Implantación |
| OQ-03 | D0-03 | ~~¿Qué disparador de reserva usa el cliente? ¿Cuánto dura una reserva? ¿Cómo se prioriza entre pedidos?~~ **RESUELTA 2026-09-02** (`d0-03-checkpoint/`): disparador fijo `ORDER_CONFIRMATION`; prioridad = orden de compromiso; residuo CONFIG `reservation_ttl_days` (defecto desactivado) | ~~BUSINESS~~ CONFIG | Implantación (solo TTL) | No |
| OQ-04 | D0-03 | ¿Backorder y sustitución entran en el alcance de la Spec 030? — **No: OUT_OF_SCOPE explícito (FR-030-012), FUTURE** | BUSINESS | Producto | No |
| OQ-05 | D0-04 | Mapa físico real: zonas, pasillos, racks, niveles, posiciones y criterio de asignación | CONFIG | Almacén · Logística | Puesta en marcha |
| OQ-06 | D0-05 | ¿Se confirma el orden de precedencia propuesto? ¿Cuál es el límite de descuento por rol? ¿Entran comisiones en el alcance? ¿Qué parámetros de crédito? | BUSINESS | Producto · Ventas · Crédito | Implantación |
| OQ-07 | D0-06 | ¿Dónde se hospeda la autoridad de licencias y quién custodia la clave privada? | **BUSINESS** | Producto · Infraestructura | **Cierre de la Spec 004** |
| OQ-08 | D0-07 | Las 24 reglas de `D0-fiscal-validation-matrix.md` | **LEGAL** | Abogado tributario · Contador público | **Certificación fiscal** |
| OQ-09 | D0-07 | ¿Qué modalidad de facturación se solicita y en qué plazo se inicia la homologación? | BUSINESS + LEGAL | Producto · Homologación | Spec 056 |
| OQ-10 | D0-08 | ¿Política de retención documental por tipo y por empresa? | BUSINESS | Producto · Legal | No |
| OQ-11 | D0-09 | ¿Existe algún producto cuya conversión no sea exacta en unidad base? | CONFIG | Inventario | No (la regla exige declararlo) |
| OQ-12 | D0-12 | ¿Qué procesos exigen segregación entre preparación y confirmación en cada empresa? | CONFIG | Auditoría interna del cliente | Implantación |
| OQ-13 | D0-13 | ¿Qué dimensiones marcadas `C` activa cada empresa? | CONFIG | Contabilidad del cliente | Implantación |
| **OQ-14** | **Gobierno** | **Los 15 ADR de `001-fundacion` siguen en estado `PROPUESTO`. Ninguno fue aprobado nunca.** ¿Se aprueban, se revisan o se sustituyen? | **GOV** | Arquitectura · Producto · Seguridad | Cumplimiento del Principio 12 |
| OQ-15 | Gobierno | ¿Se adoptan las tres enmiendas constitucionales propuestas en `D0-constitution-diff.md`? | GOV | Producto · Arquitectura · Legal · QA | No |
| OQ-16 (`OQ-031-1`) | D0-15 | ¿Con qué marca temporal se ordena la cola de preparación, `submitted_at` (compromiso) o `released_at` (entrada en cola)? Es decir: ¿una retención de crédito le cuesta al pedido su puesto en la fila? | BUSINESS | Ventas · Almacén | **031, 032** |
| OQ-17 (`OQ-031-2`) | D0-15 | ¿Se planifica el picking con lo ubicado cuando es menor que lo reservado, o se espera a que el put-away lo complete? | BUSINESS | Operaciones de almacén | **031, 032** |
| OQ-18 (`OQ-031-3`) | D0-15 | ¿Puede cancelarse un plan de picking? ¿Se invalida cuando la existencia que tenía asignada se mueve o se reclasifica? ¿Qué libera la asignación por ubicación? | BUSINESS | Almacén · Ingeniería | **031, 032** |

## Recuento

| Clase | Cantidad |
|---|---:|
| CONFIG — no bloquean nada del desarrollo | 5 |
| BUSINESS — bloquean implantación, no construcción | 5 |
| BUSINESS crítica — bloquea cierre de Spec | 1 (OQ-07) |
| LEGAL — bloquea certificación | 2 (OQ-08, OQ-09) |
| GOV — gobierno interno | 2 (OQ-14, OQ-15) |
| **TOTAL** | **15** |

## Sobre OQ-14

Es un hallazgo de esta fase, no del GAP Analysis. Los 15 ADR fundacionales del proyecto están todos
en estado `PROPUESTO` con «Aprobación pendiente». La Constitución (P12) exige que toda decisión
arquitectónica relevante se formalice mediante ADR **con estado de aprobación**. Que ninguno se haya
aprobado significa que, formalmente, KONTROL se construyó sobre decisiones propuestas.

Los ADR-D0 nacen `APPROVED` precisamente para no repetir el patrón. Pero deja abierta la pregunta de
qué hacer con los quince anteriores, dos de los cuales (ADR-003 y ADR-005) esta fase ha extendido.
