# SPEC 020 — INCIDENCIAS DE RECEPCIÓN · CICLO SPECKIT PREVIO AL CÓDIGO

| Campo | Valor |
|---|---|
| Autorización | `SPEC 020 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-03) |
| Base | `409b945` (`SPEC 019 — COMPLETE / CONVERGED`) |
| Baseline remedida | PostgreSQL 18.6 (UTC) · 177 modelos · 177 tablas · 44 migraciones (cabeza `0044_spec019_receipt`) · 373 FK · 321 rutas · 440 operaciones · 378 con contrato de empresa |
| Fuente autoritativa | `requerimientos/Procesos - Importacion - Recepcion de Importación y Distribucion en Almacen.docx` |
| Estado de partida del código | **cero**: ninguna tabla, ruta, servicio ni pantalla de incidencia |

---

## Las tres etapas, extraídas de la fuente

DOCX §2, párrafos 40 a 47, literales:

| # proceso | Etapa fuente | Owner | Implementación actual | Hueco |
|---:|---|---|---|---|
| 8 | «Si existen diferencias, **registrar**: faltantes; sobrantes; daños; referencias incorrectas; diferencias documentales» | **020** | ninguna | la entidad entera |
| 9 | «Generar **evidencia** de la incidencia» | **020** · 046 | ninguna | el enlace documental |
| 10 | «**Escalar** la novedad a Compras» | **020** · 047 | ninguna | la transición de escalamiento |

Las otras nueve del proceso ya tienen dueño: ocho son de la Spec 019 (cerradas) y una de la 022.

## Los cinco tipos, extraídos de la etapa 8

No se inventa ninguno: son los cinco subelementos literales de la etapa 8.

| Tipo | Fuente | ¿Afecta línea? | ¿Afecta cantidad? |
|---|---|---|---|
| `FALTANTE` | «faltantes» | sí | sí |
| `SOBRANTE` | «sobrantes» | sí | sí |
| `DANO` | «daños» | sí | sí |
| `REFERENCIA_INCORRECTA` | «referencias incorrectas» | sí | sí |
| `DIFERENCIA_DOCUMENTAL` | «diferencias documentales» | **no**: es del documento, no de la mercancía | no |

Se auditaron los trece candidatos que el checkpoint sugería revisar. Ocho de ellos —empaque,
presentación, lote, serial, vencimiento, calidad, rechazo y cuarentena— **no son tipos de
incidencia** en el contrato: empaque, presentación, lote, serial y vencimiento son datos que la
Spec 019 captura en la recepción; calidad es el veredicto `quality_status` de la etapa 7; y rechazo
y cuarentena son **tratamientos**, no tipos. Implementarlos como tipos habría sido inventarlos.

## Los cuatro tratamientos, extraídos del contrato

DOCX §3, párrafos 71 a 75, literales: «Determinar tratamiento: ajuste autorizado; reclamo al
proveedor; investigación interna; mercancía en cuarentena».

| Resolución | Fuente | ¿Aprobación? | Qué recibe la Spec 021 |
|---|---|---|---|
| `AJUSTE_AUTORIZADO` | «ajuste autorizado» | **sí** — control crítico 115: «Autorización de ajustes» | una cantidad a ajustar, ya autorizada |
| `RECLAMO_PROVEEDOR` | «reclamo al proveedor» | no | una cantidad reclamada; no entra al inventario |
| `INVESTIGACION_INTERNA` | «investigación interna» | no | una cantidad en investigación; no se confirma todavía |
| `CUARENTENA` | «mercancía en cuarentena» | no | una cantidad a separar; control crítico 116 |

**Dónde vive cada cosa, dicho sin ambigüedad.** El DOCX enumera los tratamientos dentro de §3, que
es el proceso de la Spec 021, y la matriz de procesos asigna «Tratamiento» a 021 y 025. Este ciclo
implementa que la **decisión** quede registrada en la incidencia —que es donde se escala y donde se
responde— y deja la **ejecución** contra el inventario a la Spec 021, cuyo bloqueo con la
capacidad de estados de la Spec 023 no se toca. Registrar no es ejecutar.

## El ciclo de vida, derivado de las etapas

El DOCX describe acciones, no estados. Los estados son la expresión mínima de esas acciones más el
control crítico de autorización; cada nombre corresponde a una palabra del documento.

| Estado | De dónde sale |
|---|---|
| `REGISTRADA` | etapa 8, «registrar» |
| `ESCALADA` | etapa 10, «escalar» |
| `PENDIENTE_AUTORIZACION` | control crítico 115, «autorización de ajustes» |
| `RESUELTA` | §3, «determinar tratamiento» |
| `ANULADA` | registrada por error; sin efecto |

| Desde | Acción | Precondición | Hasta | Efecto |
|---|---|---|---|---|
| `REGISTRADA` | escalar | — | `ESCALADA` | queda constancia de a quién y cuándo |
| `REGISTRADA` · `ESCALADA` | resolver sin autorización | tratamiento ≠ `AJUSTE_AUTORIZADO`, con motivo | `RESUELTA` | resultado estructurado para 021 |
| `REGISTRADA` · `ESCALADA` | resolver con `AJUSTE_AUTORIZADO` | solicita aprobación a 045 | `PENDIENTE_AUTORIZACION` | solicitud abierta |
| `PENDIENTE_AUTORIZACION` | resolver | 045 aprobó | `RESUELTA` | ídem |
| `REGISTRADA` · `ESCALADA` · `PENDIENTE_AUTORIZACION` | anular | con motivo | `ANULADA` | libera la cantidad afectada |
| `RESUELTA` · `ANULADA` | — | terminal | — | inmutable |

---

## `/speckit.specify`

**Alcance.** Registrar la incidencia contra la recepción y, cuando es de mercancía, contra su línea;
enlazar la evidencia por la Spec 046; escalar a Compras; resolver con uno de los cuatro tratamientos,
pidiendo autorización a la Spec 045 cuando el tratamiento es un ajuste; y entregar un resultado
estructurado que la Spec 021 pueda consumir sin interpretar texto libre.

**Fuera de alcance, con dueño.** La captura del hecho físico (019, cerrada). La confirmación y
conciliación del inventario y la escritura de estados no vendibles (021 + capacidad de 023). El
put-away (022). Picking, consolidación, facturación y despacho. La factura del proveedor (027).
Ningún motor paralelo de aprobaciones, documentos o inventario.

### Requisitos propios

| Id | Requisito | Etapa |
|---|---|---|
| FR-020-001 | Una incidencia pertenece a una recepción de la empresa del contexto | 8 |
| FR-020-002 | Los tipos de mercancía exigen línea y cantidad afectada; el documental no admite ninguna de las dos | 8 |
| FR-020-003 | La cantidad afectada se expresa en unidad base, tomada del snapshot de la línea; no se recalcula con maestros actuales | 8 |
| FR-020-004 | La cantidad afectada acumulada por línea y tipo no puede superar el tope físico de ese tipo | 8 |
| FR-020-005 | La incidencia referencia el hecho de la Spec 019; no lo copia ni lo reescribe | 8 |
| FR-020-006 | La evidencia se adjunta por la Spec 046, con la incidencia como recurso enlazable | 9 |
| FR-020-007 | Escalar deja constancia de cuándo y de quién | 10 |
| FR-020-008 | Resolver exige un tratamiento del catálogo y un motivo | §3 |
| FR-020-009 | `AJUSTE_AUTORIZADO` exige aprobación previa por la Spec 045 | control 115 |
| FR-020-010 | Resolver dos veces no ejecuta dos decisiones | — |
| FR-020-011 | Dos resoluciones concurrentes: solo una gana | — |
| FR-020-012 | Una recepción sin diferencias no crea ninguna incidencia | 16 del encargo |
| FR-020-013 | La incidencia no escribe inventario ni asigna ubicación | — |
| FR-020-014 | El resultado es estructurado y consultable por la Spec 021 | §3 |

Los IMP-020-001..048 del encargo se trazan uno a uno en `traceability-matrix.md`.

---

## `/speckit.clarify` — 36 respuestas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Las tres etapas | registrar (8), evidencia (9), escalar (10) |
| 2-4 | ¿Modelo, tabla, cabecera o línea? | **No existe nada.** Se crea `ReceiptIncident`, ligada siempre a la recepción y opcionalmente a la línea: los cuatro tipos de mercancía la exigen, el documental la prohíbe |
| 5 | Tipos | los cinco de la etapa 8 |
| 6 | Estados | los cinco derivados arriba |
| 7 | Resoluciones | los cuatro tratamientos del §3 |
| 8 | ¿Cuáles exigen aprobación? | solo `AJUSTE_AUTORIZADO` (control crítico 115) |
| 9 | ¿Cuál exige motivo? | todas |
| 10 | ¿Cuál exige documentación? | ninguna la exige como bloqueo; la etapa 9 la habilita |
| 11-12 | ¿Severidad, prioridad, asignación? | **no están en el contrato**: no se implementan |
| 13-15 | Permisos | crear y escalar: `compras:quality`; resolver: `compras:approve`; ambos ya existen |
| 16 | Datos de 019 a referenciar | la línea entera por clave foránea: producto, cantidades, unidad, presentación, factor, base, observación física, lote, serial y vencimiento |
| 17-18 | Cantidad afectada | en unidad base; la tecleada y su presentación se leen de la línea, no se repiten |
| 19 | Invariantes | `FALTANTE` ≤ lo pedido; los otros tres ≤ lo recibido en base; acumulado por línea y tipo |
| 20-26 | Qué ocurre con cada caso | sobrante, faltante, daño y referencia son tipos; documentación es tipo de cabecera; **calidad** es `quality_status` de 019, no un tipo; **lote, serial y vencimiento** son datos de 019, no tipos |
| 27-28 | Qué consume la 021 | tipo, línea, producto, cantidad base afectada y tratamiento resuelto. Estructurado, no texto |
| 29-30 | Rutas y pantalla | ninguna; se crean |
| 31-32 | Documentos | Spec 046, registrando `ReceiptIncident` en su catálogo cerrado |
| 33 | Aprobaciones | Spec 045, con un tipo de proceso nuevo en el catálogo de constantes de integración |
| 34-35 | Datos heredados | **ninguno**: no hay filas que migrar. No se fabrica historia |
| 36 | Riesgos de concurrencia | dos resoluciones a la vez, y dos incidencias que compiten por la cantidad de la misma línea |

**Ninguna decisión material nueva.** Las tres candidatas están cerradas: el estado del saldo es de
021 con capacidad de 023; ubicar es de 022; y el hecho físico ya lo capturó 019.

---

## `/speckit.plan` — 24 olas

Baseline y auditoría · extracción de etapas · tipos · tratamientos · ciclo de vida · modelo ·
semántica de cantidad · migración `0045` · paridad ORM · servicios · resolución · integración 045 ·
integración 046 · contrato para 021 · auditoría · permisos · API · frontend · multiempresa ·
idempotencia y concurrencia · pruebas hostiles · instalación limpia · regresión · convergencia.

---

## CONSTITUTION GATE

| Validación | Resultado |
|---|---|
| Constitución (P5, P8, P21, P23) | PASS: histórico inmutable; ninguna política de cliente codificada —la segregación la decide 045—; PostgreSQL autoridad; el hecho físico no se duplica |
| ARCH-MC-001 | PASS: contexto autoridad; cadena recepción → línea → incidencia; cuerpos estrictos |
| Spec 011 | PASS: la cantidad base sale del snapshot de la línea |
| Spec 019 | PASS: se referencia, no se reescribe |
| Frontera con 021 | PASS: se entrega resultado, no se ejecuta confirmación |
| Hueco de 023 | PASS: no se toca ni se rodea |
| Frontera con 022 | PASS: sin ubicación |
| Spec 045 | PASS: motor único; se añade una constante de integración, no un motor |
| Spec 046 | PASS: registro cerrado de recursos; sin almacenamiento paralelo |
| Sin incidencia de camino feliz | PASS |
| Sin segundo veredicto de conformidad | PASS: `quality_status` sigue siendo el único |
| Estándar de frontend | PASS |

**CONSTITUTION GATE: PASS**

## `/speckit.checklist` · `/speckit.tasks`

Los 31 ítems y las 60 tareas del encargo, ajustadas: la 015 (backfill) queda **no aplicable** —no
hay datos heredados— y la 028 (eventos/outbox) también, porque no existe outbox transversal y la
auditoría es la fuente, como ya se resolvió en la Spec 030.

## `/speckit.analyze`

| Detección | Resultado |
|---|---|
| Requisito sin tarea · tarea sin requisito | 0 · 0 |
| Etapa sin dueño | 0: las tres cubiertas |
| Tipo o resolución inventados | 0: cinco y cuatro, literales del DOCX |
| Texto libre como única autoridad | no: tipo, estado y tratamiento son enumerados |
| Incidencia de camino feliz | no |
| Cabecera o línea ambiguas | no: regla por tipo, con restricción en base de datos |
| Línea de otra recepción | prevenida |
| Cantidad por encima de lo permitido | prevenida, con tope por tipo y acumulado bajo bloqueo |
| Cantidad tecleada usada como base | no |
| Factor actual consultado | no |
| Hecho de 019 duplicado o sobrescrito | no |
| Segundo veredicto de conformidad | no |
| Motor de aprobaciones o de documentos local | no |
| Resolución antes de la aprobación | prevenida |
| Aprobación reutilizada tras cambio material | prevenida por `document_changed` |
| Resultado ambiguo para 021 | no: enumerado y consultable |
| Estados de saldo escritos por 020 | no |
| Efecto de put-away o ubicación | no |
| Empresa desde el cuerpo · usuario AB · cadena cruzada | prevenidos |
| Incidencia terminal mutable · resolución duplicada | prevenidas |
| Desajuste ORM contra migración | no |
| Pruebas verdes por causa equivocada | revisión caso a caso |

BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0.

**Autorización expresa satisfecha: se procede a `/speckit.implement`.**
