# CLARIFICACIONES — SPEC 046

Regla de trabajo (§143): **primero se resuelve con la autoridad existente.** De
las quince cuestiones que el encargo exige cerrar, doce las resuelve
`ADR-D0-008`, la Constitución o el código real. Tres se escalan **sin bloquear**.

---

## 1. Las quince cuestiones del §143

| # | Cuestión | Resolución | Autoridad |
|---|---|---|---|
| CL-046-01 | Modelo Document/File/Version | `Document` → `DocumentVersion` → `StoredFile`, más `DocumentLink`. Es el modelo conceptual del ADR, con `Attachment` renombrado a `Document` | `ADR-D0-008` §Modelo conceptual |
| CL-046-02 | Abstracción de almacenamiento | Interfaz con proveedor intercambiable; sistema de archivos por defecto sobre el volumen existente, S3-compatible como segunda implementación | `ADR-008` + §7 |
| CL-046-03 | Propiedad y vinculación | Tabla de vínculos separada, con `resource_type` de **registro cerrado y validado** | `ADR-D0-008` (`AttachmentLink`) + §10 |
| CL-046-04 | Versionado | Nunca en sitio: nueva versión, la anterior con su hash | R-D0-08-5, P5 |
| CL-046-05 | Borrado / archivado | Lo usado históricamente no se borra: se archiva. El binario no se destruye si hay histórico | R-D0-08-8, §39, §42 |
| CL-046-06 | Validación de MIME | Declarado **y** detectado, guardados por separado; discrepancia se rechaza salvo política del tipo | R-D0-08-9, §17, §18 |
| CL-046-07 | Mecanismo de subida | **Por el backend** en el MVP; ver §3 de `research.md` | §91 |
| CL-046-08 | Mecanismo de descarga | Flujo por el backend, con autorización sobre la entidad vinculada | R-D0-08-6, §93 |
| CL-046-09 | Análisis de malware | **Capacidad de despliegue configurable**, no obligatoria en el MVP; sin analizador el estado es `SKIPPED` y queda declarado | §48 |
| CL-046-10 | Retención | Capacidad configurable por tipo. **No se inventan plazos legales** | §40 |
| CL-046-11 | Metadata extensible | Esquema validado por `DocumentType`; JSON **nunca** para empresa, propietario, estado, tipo, hash ni relaciones | §34, §35 |
| CL-046-12 | URL externas | Admitidas y **marcadas como no administradas**; no se tratan como archivo de KONTROL | §112 |
| CL-046-13 | Migración legada | Cinco clases; nada se inventa. Detalle en `legacy-document-migration-matrix.md` | §110-115 |
| CL-046-14 | Auditoría de descargas | **Según política del tipo**, no siempre: auditar toda descarga generaría volumen sin propósito | §61 |
| CL-046-15 | Tipos globales o por empresa | **Por empresa**, y el catálogo nace vacío | P8 |

## 2. Decisiones tomadas

| ID | Decisión | Razón |
|---|---|---|
| CL-046-16 | `Attachment` del ADR se llama `Document` aquí | El ADR describe la capacidad; esta Spec distingue documento lógico de archivo físico, y «adjunto» confunde ambos. **Semántica y columnas idénticas**: se documenta la equivalencia para que no se lea como divergencia |
| CL-046-17 | `resource_type` con registro cerrado, no texto libre | Una clave foránea polimórfica sin control admite `resource_type = "cualquiercosa"` y hace imposible autorizar. El registro declara qué tipos existen y cómo se comprueba la propiedad |
| CL-046-18 | `DocumentCategory` **sí** existe, separada de `DocumentType` | La categoría agrupa para navegar y para permisos gruesos; el tipo lleva la política. Fundirlas obligaría a repetir la política en cada tipo |
| CL-046-19 | `file_metadata` evoluciona a `stored_files`, no se crea otra tabla | Tiene ya los campos correctos y está vacía de uso. Crear una tabla paralela dejaría dos |
| CL-046-20 | El estado del documento y el del archivo son columnas distintas | Un permiso vigente cuyo PDF está en cuarentena es un estado real; una sola columna no puede expresarlo (§49) |
| CL-046-21 | `EXPIRED` se deriva, no se persiste | Persistirlo exigiría un proceso que lo actualice y crearía inconsistencia entre la fecha y el estado (§38) |
| CL-046-22 | Sin deduplicación física en el MVP | Dos documentos pueden compartir contenido legítimamente. Deduplicar acopla su ciclo de vida: borrar uno afectaría al otro (§22) |
| CL-046-23 | Sin OCR, sin miniaturas, sin cuotas, sin *legal hold* en el MVP | `FUTURE_CAPABILITY` explícito. El modelo no los impide (§41, §52, §68, §138) |
| CL-046-24 | Las exportaciones de `reporting` **no** se absorben ahora | Ya funcionan y son de la Spec 050. Absorberlas sería scope creep sin desbloquear ninguna Spec (§5 de la matriz legada) |
| CL-046-25 | SVG: **solo descarga**, nunca en línea | Puede contener guion activo. Rechazarlo cerraría un caso legítimo; mostrarlo abriría ejecución en contexto autenticado (§84) |
| CL-046-26 | Comprimidos rechazados por defecto | Bombas de descompresión y contenido anidado sin inspección. Un tipo puede habilitarlos explícitamente (§51) |
| CL-046-27 | 046 emite contratos de evento, **no** notifica | 047 será consumidor. Acoplar aquí invertiría la dependencia (§65) |

## 3. Escalados — ninguno bloqueante

| ID | Cuestión | Por qué se escala | Qué se hace mientras |
|---|---|---|---|
| **ESC-046-01** | **¿El análisis de malware es obligatorio en producción?** La arquitectura lo soporta como capacidad configurable; exigirlo añade una dependencia de despliegue (un servicio analizador) a cada instalación de cliente | Es decisión de **producto y de riesgo**, con impacto en el despliegue de cada cliente. No es técnica | Se implementa configurable, **desactivado por defecto y declarado** como `SKIPPED` en la metadata del archivo, de modo que nunca se afirme que un archivo fue analizado si no lo fue |
| **ESC-046-02** | **Los registros de homologación con `evidence_sha256` sin binario: ¿son actos formales vigentes?** Si lo son, la ausencia del archivo es un hallazgo de cumplimiento, no una nota de migración | Es una cuestión **de negocio y posiblemente legal**, no de arquitectura | Se marca `LEGACY_HASH_WITHOUT_FILE` y se reporta. **No** se crea documento (R-046-5). La migración no se bloquea por ello salvo que se confirme que son actos vigentes |
| **ESC-046-03** | **Plazos de retención documental.** Qué debe conservarse y cuánto depende de la normativa venezolana aplicable a cada tipo | El encargo prohíbe expresamente **inventar plazos legales** (§40), y afirmarlos sin fuente sería peor que no fijarlos | Se implementa la **capacidad**: `retention_policy` por tipo, configurable y versionable. Sin valores por defecto. Ningún documento se elimina automáticamente mientras no se declare una política |

## 4. Lo que no se escala, y por qué

No se pregunta al usuario por: motor de persistencia (`ADR-D0-001`), aprobaciones
(Spec 045), auditoría (`ADR-012`), permisos (Spec 003), concurrencia
(`ADR-013`), estrategia de archivos (`ADR-008`) ni el modelo documental
(`ADR-D0-008`). Todo ello está cerrado y se **consume**.

Tampoco se escala si los binarios van en PostgreSQL: `ADR-D0-008` R-D0-08-3 ya lo
prohíbe.
