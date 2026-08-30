# `/speckit.analyze` — SPEC 046 · GESTIÓN DOCUMENTAL

Fecha: **2026-08-30** · Rama `develop` · Análisis documental.
**No se escribió código. No se creó ninguna migración. No se ejecutó
`/speckit.implement`.** La cadena Alembic sigue en `0022`.

---

## 1. Cadena comparada

`Constitución v1.1` → `ADR vigentes` → `baseline` → `D0` → `G0` → `GAP` →
`roadmap` → `spec.md` → `clarifications.md` → `research.md` → `plan.md` →
`data-model.md` → `contracts/` → `wireframes/` → `checklist.md` → `tasks.md` →
`acceptance-criteria.md` → `test-plan.md` → `risk-register.md` →
`traceability-matrix.md` → `document-consumer-contract-matrix.md` →
`legacy-document-migration-matrix.md`.

## 2. Artefactos — 16/16

Los 15 exigidos por §173, más este informe.

## 3. Coherencia — verificada por comando

| Comprobación | Resultado |
|---|---|
| Requisitos funcionales sin tarea | **0** de 84 |
| Requisitos no funcionales sin tarea | **0** de 9 |
| Criterios de aceptación sin tarea | **0** de 50 |
| Tareas sin requisito ni criterio | **0** de 103 |
| Códigos de error: contrato ↔ criterios | **18 ↔ 18**, coincidentes |
| Documentos normativos citados que no existen | **0** |
| Tareas de dominios ajenos | **0** |
| Código o migración creados | **0** |

La matriz se **genera por script** desde los artefactos: no puede envejecer sin
que se note.

## 4. Estado actual encontrado — el hallazgo que define la Spec

Auditoría del código real, no de los nombres:

| Métrica | Valor |
|---|---:|
| Columnas con semántica de referencia revisadas | **69** |
| Con semántica **documental real** | **13** |
| Con clave foránea a un archivo | **0** |
| Consumidores de `file_metadata` | **0** — solo aparece en `models.py` |
| Endpoints de subida | **0** |
| Capacidad de subida en el frontend | **0** |
| Vínculo archivo ↔ entidad | **No existe** |

Y sin embargo `python-multipart` **ya está** en `requirements.txt` y el volumen
`kontrol-storage:/data/storage` **ya está** en `compose.yaml`.

> La infraestructura estaba preparada y nunca se conectó. `file_metadata` tiene
> los cuatro campos correctos —`sha256`, `storage_key`, `mime_type`, `size`— y
> cero consumidores: el mismo patrón que la Spec 008 halló en `locations` y la
> 011 en `presentations`. Lo que falta no es infraestructura, es **el vínculo
> entre un archivo y aquello de lo que es evidencia**.

## 5. Contradicciones detectadas y resueltas

### C-01 · Numeración de reglas con salto arbitrario — **RESUELTA**

Las reglas iban `R-046-1..4` y saltaban a `R-046-9`, definida en otro artefacto.
Es el mismo defecto que apareció en la Spec 011. Renumerada a `R-046-5` y
**definida formalmente en `spec.md`**, junto a las otras cuatro.

### C-02 · Identificadores de amenaza confundibles con tareas — **RESUELTA**

Las amenazas eran `T-01`..`T-20` y las tareas `T-046-001`..`T-046-155`. En un
registro de riesgos que cita ambas, `T-01` y `T-046-001` se leen igual de un
vistazo. Las amenazas pasan a `AMZ-01`..`AMZ-20`. Sin colisión.

### C-03 · Nomenclatura divergente del ADR — **RESUELTA, documentada**

`ADR-D0-008` llama `Attachment` y `AttachmentLink` a lo que esta Spec llama
`Document` y `DocumentLink`. **No es divergencia**: el ADR describe la capacidad
y esta Spec distingue documento lógico de archivo físico, distinción que la
palabra «adjunto» borra. Semántica, columnas y contrato **idénticos**, y la
equivalencia queda escrita (CL-046-16) para que nadie la lea como cambio de
decisión.

**Contradicciones sin resolver: 0.**

## 6. Conformidad constitucional

| Principio | Veredicto | Evidencia |
|---|---|---|
| P2 autorización expresa | ✅ | Ciclo documental; se detiene antes de implementar |
| P3 trazabilidad | ✅ | 0 huérfanos en las cuatro direcciones |
| P4 núcleo fiscal separado | ✅ | 046 guarda evidencia; no toca el motor fiscal |
| **P5 dato histórico protegido** | ✅ **eje** | Versiones inmutables, evidencia en uso no se borra, original byte a byte, hash sin binario no genera documento |
| **P6 backend es la autoridad** | ✅ **eje** | Nombre, MIME, tamaño, hash, permiso y número de versión los fija el servidor |
| P8 sin negocio en código | ✅ | Catálogos vacíos; lista blanca vacía = ninguno |
| P11 accesibilidad y responsive | ✅ | Carga operable solo con teclado; nombres largos probados |
| P13 integridad transaccional | ✅ | Escribir → verificar → confirmar; sin metadata huérfana |
| **P17 / P22 autoridad única** | ✅ **eje** | Un solo módulo documental; R-D0-08-1; matriz de consumidores |
| P18 sin modales complejos | ✅ | Biblioteca y detalle en página completa |
| P21 paridad del motor | ✅ | PostgreSQL 18.x **y almacenamiento real**, no simulado |
| P23 captura temprana | ✅ | El hash solo es verificable al recibir el archivo |

**0 violaciones. 0 enmiendas requeridas.**

## 7. Scope creep

| Comprobación | Resultado |
|---|---|
| Tareas de 018, 019, 020, 027, 035, 040, 044, 047, 050 | **0** |
| Microservicio | **0** — módulo del monolito (§141) |
| Absorción de las exportaciones de `reporting` | **0** — la Spec 050 conserva su mecanismo |
| Sistemas propios de permisos, auditoría, aprobaciones o notificaciones | **0** |
| Plazos legales de retención inventados | **0** — se implementa la capacidad, no los plazos |
| OCR, miniaturas, deduplicación, cuotas, *legal hold* | **0** — `FUTURE_CAPABILITY` explícito |

## 8. Verificación de transversalidad

**16 Specs** evaluadas en `document-consumer-contract-matrix.md`. De ellas,
**8 no pueden completarse sin esta capacidad**: 018, 019, 020, 027, 035, 040,
044 y 051. Ninguna podría resolverlo por su cuenta sin violar P22 y R-D0-08-1.

El contrato que la Spec 045 publicó se verifica punto por punto: se satisface
**sin un solo cambio en el modelo de 045**, tal como CL-045-10 exigía.

## 9. Seguridad — tratada como requisito, no como anexo

Es la primera Spec del proyecto cuyo riesgo dominante es de seguridad: introduce
la primera **entrada de binarios** de KONTROL. El modelo de amenazas encabeza el
registro de riesgos con **20 amenazas**, cada una con mitigación de diseño y el
criterio de aceptación que la ejerce.

Las cinco que condicionan el modelo: recorrido de rutas, suplantación de MIME,
contenido activo, referencia insegura directa y fuga entre empresas. Ninguna se
clasificó como capacidad futura: §168 lo prohíbe expresamente para lo que es
requisito básico de subida y descarga.

## 10. Ambigüedades y escalados

**Bloqueantes: 0.** Doce de las quince cuestiones del §143 se resolvieron con
autoridad existente. Se escalan **tres**, sin bloquear:

| ID | Cuestión | Mientras tanto |
|---|---|---|
| **ESC-046-01** | ¿El análisis de malware es obligatorio en producción? | Configurable, desactivado por defecto y **declarado** como `SKIPPED`: nunca se afirma que un archivo fue analizado si no lo fue |
| **ESC-046-02** | ¿Los registros de homologación con hash sin binario son actos formales vigentes? | Se marcan y se reportan; **no** se crea documento. La migración no se bloquea salvo confirmación |
| **ESC-046-03** | Plazos legales de retención documental | Se implementa la **capacidad**, sin valores por defecto. Nada se elimina automáticamente mientras no se declare una política |

Los tres son decisiones de producto, de riesgo o legales, no de arquitectura. El
encargo prohíbe expresamente inventar plazos legales (§40), y afirmarlos sin
fuente sería peor que no fijarlos.

## 11. Duplicidad de autoridad

**0.** No se crea RBAC, auditoría, aprobación ni notificación propios.
`reporting` no se toca. El único mecanismo de archivos del sistema pasará a ser
este.

## 12. Riesgos

17 riesgos de proyecto más las 20 amenazas. El dominante es **RSK-046-08 —
inventar evidencia legada**: crear un documento por cada `file_ref` con texto
dejaría un repositorio lleno de documentos que nadie puede abrir, con apariencia
de completitud. Por eso la migración de esta Spec **no crea ni un solo
documento**: solo anota.

## 13. Veredicto

| Criterio (§170) | Resultado |
|---|---|
| Modelo Document/Version/File cerrado | ✅ |
| Propiedad y vinculación cerradas | ✅ registro cerrado de tipos de recurso |
| Abstracción y estrategia de proveedor cerradas | ✅ |
| Subida y descarga cerradas | ✅ por el backend, con justificación |
| Validación de MIME y hash cerrados | ✅ |
| Versionado cerrado | ✅ con inmutabilidad |
| Borrado, archivado y retención | ✅ capacidad sin plazos inventados |
| Multiempresa, permisos y auditoría | ✅ sin sistemas paralelos |
| Integración con la Spec 045 | ✅ verificada punto por punto |
| Contratos de consumidores | ✅ 16 Specs, 8 bloqueadas identificadas |
| Migración legada diseñada | ✅ cinco clases; nada se inventa |
| Modelo de amenazas completo | ✅ 20 amenazas con mitigación y criterio |
| PostgreSQL y almacenamiento de QA planificados | ✅ |
| API, frontend y pruebas definidos | ✅ |
| Contradicciones | ✅ **0** |
| Requisitos y tareas huérfanos | ✅ **0** |

**APTA PARA IMPLEMENTACIÓN.**

Condiciones cuando se autorice: orden **F1→F2→F3→F4→F5→F6→F7→F8→F9**, con **F4
—vinculación y autorización— antes que F6**: publicar una descarga antes de saber
quién puede descargar convertiría la Spec en una vulnerabilidad. Toda la
evidencia sobre PostgreSQL 18.x **y un proveedor de almacenamiento real**.
