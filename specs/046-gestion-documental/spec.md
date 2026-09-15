# SPEC 046 — GESTIÓN DOCUMENTAL

| Campo | Valor |
|---|---|
| Estado | Ciclo documental · **no implementada** |
| Autoridad principal | `ADR-D0-008` — Gestión documental transversal |
| Tipo | **Capacidad transversal** (P22) |
| Specs bloqueadas por su ausencia | **8** — 018, 019, 020, 027, 035, 040, 044, 051 |
| Motor | PostgreSQL **18.x** (`ADR-D0-001` `CONFIRMED_BY_EXECUTION`) |

---

## 1. Propósito

Que una evidencia guardada hoy pueda abrirse, verificarse y atribuirse dentro de
diez años, y que ningún módulo vuelva a inventar su propia forma de guardar
archivos.

Ocho Specs necesitan adjuntar documentos. Si cada una lo resuelve por su cuenta,
KONTROL tendrá ocho sistemas de archivos incompatibles, ocho formas de autorizar
descargas y ocho maneras de perder un binario. Esta Spec construye **una sola**.

## 2. Punto de partida real — verificado, no supuesto

| Comprobación | Estado real |
|---|---|
| `file_metadata` | **Existe** con `sha256`, `storage_key`, `mime_type`, `size`, `company_id`, `expires_at` |
| Consumidores de `file_metadata` | **0** — solo aparece en `models.py` |
| Endpoints de subida | **0** (`UploadFile`: sin coincidencias) |
| Subida en el frontend | **0** — sin `type="file"`, sin `FormData` |
| Vínculo archivo ↔ entidad | **No existe** |
| Columnas con semántica documental | **13**, todas `String`, **0 con clave foránea** |
| Único mecanismo real de archivo | `reporting`: exportaciones que **genera el servidor** |
| `python-multipart` | **Ya en `requirements.txt`** |
| Volumen `kontrol-storage:/data/storage` | **Ya en `compose.yaml`** |

La infraestructura estaba preparada y nunca se usó. `file_metadata` es un maestro
*write-only*: el mismo patrón que 008 halló en `locations` y 011 en
`presentations`.

## 3. Alcance

### Incluido

1. Modelo `Document` → `DocumentVersion` → `StoredFile`, con `DocumentLink`.
2. `DocumentType` y `DocumentCategory` como catálogo por empresa.
3. Abstracción de almacenamiento con proveedor intercambiable.
4. Subida con validación de tipo real, tamaño y nombre seguro.
5. Descarga y previsualización **autorizadas por la entidad vinculada**.
6. Hash SHA-256 calculado en el servidor.
7. Versionado con versiones históricas inmutables.
8. Vinculación a entidades de cualquier dominio, con integridad.
9. Estados, archivado, borrado protegido y capacidad de retención.
10. Permisos, auditoría y contratos de evento.
11. Componente de adjuntos reutilizable y biblioteca documental.
12. Contratos declarados para las 16 Specs consumidoras.

### Fuera de alcance

Los procesos consumidores: importación (018), recepción e incidencias (019/020),
factura de proveedor (027), despacho (035), pagos (040), reglas regulatorias
(044), notificaciones (047) y reportes (050). 046 provee la capacidad; **la regla
de negocio pertenece al consumidor** (§142).

`FUTURE_CAPABILITY`: OCR, deduplicación física, *legal hold*, cuotas de
almacenamiento, miniaturas, subida multiparte, absorción de las exportaciones de
`reporting`.

## 4. Actores

| Actor | Interés |
|---|---|
| Usuario operativo | Adjuntar evidencia sin salir de su proceso |
| Comprador / almacenista | Cargar packing list, fotos de incidencia |
| Responsable regulatorio | Custodiar permisos con su vigencia |
| Auditor | Verificar que el archivo es el que se aprobó |
| Administrador | Definir tipos documentales y sus políticas |
| Atacante | **Es un actor**: el modelo de amenazas es requisito, no anexo |

## 5. Historias de usuario

| ID | Como… | Quiero… | Para… |
|---|---|---|---|
| HU-046-01 | operador | adjuntar un PDF a una recepción | dejar constancia sin salir del proceso |
| HU-046-02 | operador | sustituir un documento equivocado | corregir sin borrar lo anterior |
| HU-046-03 | auditor | ver qué versión se usó en una aprobación | verificar la decisión como se tomó |
| HU-046-04 | responsable regulatorio | registrar un permiso con su vencimiento | saber cuándo caduca |
| HU-046-05 | administrador | definir qué tipos admite cada proceso | sin pedir un cambio de código |
| HU-046-06 | usuario | descargar un documento al que tengo acceso | y **solo** a ese |
| HU-046-07 | responsable de seguridad | que un ejecutable disfrazado se rechace | que el repositorio no distribuya malware |
| HU-046-08 | administrador | archivar documentos obsoletos | sin destruir evidencia |
| HU-046-09 | desarrollador de otra Spec | adjuntar sin conocer el almacenamiento | no acoplarme a la infraestructura |
| HU-046-10 | operador | ver por qué falló mi carga | corregirlo sin adivinar |

## 6. Modelo conceptual

```
DocumentCategory ─ DocumentType ─┬─ DocumentMetadataSchema?
                                 │
Document ── DocumentVersion ── StoredFile ── FileSecurityScan?
   │
   └── DocumentLink (resource_type, resource_id, role)
```

> **R-046-1 · Documento lógico ≠ archivo físico.** «Permiso sanitario» es un
> documento; el PDF es un archivo. Un documento puede tener varias versiones, y
> una versión un solo archivo. Confundirlos es lo que hace imposible versionar.

> **R-046-2 · La base de datos es la autoridad del catálogo.** El almacenamiento
> guarda binarios. Está prohibido inferir qué documentos existen leyendo
> carpetas (§78).

> **R-046-3 · `storage_key` es opaca.** No se deriva de nombres de empresa,
> tercero ni archivo, y no se expone (R-D0-08-2, §55).

> **R-046-4 · Nada se sustituye en sitio.** Reemplazar un archivo crea una
> versión; la anterior se conserva con su hash (R-D0-08-5, P5).

> **R-046-5 · Un hash sin binario no es un documento.** Un `sha256` histórico
> cuyo archivo no existe **no** se convierte en documento: crearlo afirmaría que
> hay una evidencia que nadie puede abrir. Se conserva, se marca y se reporta.

## 7. Requisitos funcionales

### Documento, versión y archivo

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-001 | `Document` con empresa, tipo, título, número externo, emisor, estado y vigencia opcional | P0 |
| FR-046-002 | `DocumentVersion` con número correlativo, archivo, motivo del reemplazo, autor y momento | P0 |
| FR-046-003 | `StoredFile` con nombre original, `storage_key` opaca, MIME declarado y detectado, tamaño, SHA-256 y proveedor | P0 |
| FR-046-004 | El número de versión lo asigna el **servidor**; jamás el cliente (§101) | P0 |
| FR-046-005 | Una versión anterior **nunca** se sobrescribe (R-046-4) | P0 |
| FR-046-006 | El original se conserva **byte a byte**; toda miniatura o conversión es derivada (§54) | P0 |
| FR-046-007 | Distinguir «nueva versión del mismo documento» de «documento nuevo»; la política la fija el `DocumentType` (§24) | P0 |

### Tipos y categorías

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-010 | `DocumentCategory` y `DocumentType` como catálogo **por empresa**; nace vacío | P0 |
| FR-046-011 | `DocumentType` declara extensiones y MIME admitidos, tamaño máximo, política de versionado y de retención | P0 |
| FR-046-012 | Ningún tipo documental está codificado: todos son dato (P8) | P0 |
| FR-046-013 | `DocumentType` es distinto del MIME: `PACKING_LIST` no es `application/pdf` (§13) | P0 |
| FR-046-014 | Metadata extensible **validada por esquema** del tipo; nunca JSON libre para datos críticos (§34, §35) | P1 |

### Vinculación

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-020 | `DocumentLink` vincula un documento a una entidad de cualquier dominio, con rol opcional | P0 |
| FR-046-021 | Un mismo documento puede servir a **varias** entidades sin duplicar el binario | P0 |
| FR-046-022 | `resource_type` pertenece a un **registro cerrado y validado**, no a texto libre (§10) | P0 |
| FR-046-023 | Vincular exige permiso sobre la **entidad de destino**, no solo sobre el documento | P0 |
| FR-046-024 | Un documento vinculado a una entidad inmutable no puede desvincularse (R-D0-08-8) | P0 |
| FR-046-025 | Consultar los documentos de una entidad es una operación de primera clase | P0 |

### Almacenamiento

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-030 | Abstracción `DocumentStorageProvider` con proveedor **intercambiable por configuración** | P0 |
| FR-046-031 | Proveedor de sistema de archivos como implementación por defecto, sobre el volumen ya existente | P0 |
| FR-046-032 | Proveedor compatible con S3 como segunda implementación, **sin acoplar a ningún fabricante** (§7) | P1 |
| FR-046-033 | Ningún binario en PostgreSQL (R-D0-08-3) | P0 |
| FR-046-034 | Aislamiento por instalación: sin depender de un depósito compartido entre clientes (§8) | P0 |
| FR-046-035 | Las credenciales del almacenamiento son secretos: nunca en base de datos, frontend ni registros (§80) | P0 |
| FR-046-036 | La escritura es **verificar y luego confirmar**: no puede quedar metadata sin binario (§75) | P0 |
| FR-046-037 | Verificación de integridad que detecte metadata sin binario o con hash distinto (§74) | P1 |

### Subida

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-040 | La `storage_key` la genera el servidor; el nombre del usuario **nunca** es ruta (§15) | P0 |
| FR-046-041 | `original_filename` se conserva y se sanea solo para mostrarlo | P0 |
| FR-046-042 | Recorrido de rutas imposible: `../`, rutas absolutas, Unicode y doble codificación rechazados (§16) | P0 |
| FR-046-043 | MIME **declarado** y MIME **detectado por contenido** se guardan por separado (§17) | P0 |
| FR-046-044 | Discrepancia entre ambos: política del tipo, rechazo por defecto (§18) | P0 |
| FR-046-045 | Tamaño máximo configurable por tipo, con máximo global; rechazo **antes** de consumir el flujo entero (§20) | P0 |
| FR-046-046 | SHA-256 calculado en el servidor sobre el contenido recibido (R-D0-08-4) | P0 |
| FR-046-047 | Subida **idempotente**: doble clic, reintento o repetición no crean dos versiones (§57) | P0 |
| FR-046-048 | Ejecutables rechazados; SVG y comprimidos con política explícita (§50, §51, §84) | P0 |
| FR-046-049 | Coincidencia de hash se **registra**, no se bloquea: dos documentos pueden ser legítimamente iguales (§56) | P1 |

### Descarga y previsualización

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-050 | La descarga se autoriza por permiso sobre la **entidad vinculada** (R-D0-08-6) | P0 |
| FR-046-051 | Conocer el identificador **no** da acceso; se responde como inexistente (§128) | P0 |
| FR-046-052 | Sin URL pública permanente (§81) | P0 |
| FR-046-053 | Si hay URL firmada: expiración corta, alcance mínimo, no persistida ni registrada (§129) | P0 |
| FR-046-054 | Previsualización con **la misma** autorización que la descarga (§107) | P0 |
| FR-046-055 | Formatos no seguros se fuerzan a descarga, no se muestran en línea (§47) | P0 |
| FR-046-056 | Sin ejecución de contenido activo; cabeceras de seguridad y aislamiento en la previsualización (§83) | P0 |
| FR-046-057 | Los documentos sensibles no quedan en cachés compartidas (§82) | P0 |

### Estados, archivado y retención

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-060 | Estados del **documento**: `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED`, `REVOKED` | P0 |
| FR-046-061 | `EXPIRED` se **deriva** de `expiration_date`; no se persiste como estado (§38) | P0 |
| FR-046-062 | El estado del documento es distinto del estado de seguridad del archivo (§49) | P0 |
| FR-046-063 | Un documento en uso histórico **no se borra**: se archiva (§39) | P0 |
| FR-046-064 | Archivar es lógico: el binario **no** se destruye si hay histórico (§42) | P0 |
| FR-046-065 | Política de retención configurable por tipo; **sin plazos legales inventados** (§40) | P1 |
| FR-046-066 | El borrado físico, cuando proceda, se ejecuta por el trabajador común, no por un planificador propio (§137) | P1 |
| FR-046-067 | Sin referencias colgantes: una versión referenciada históricamente es estable (§43) | P0 |

### Seguridad del archivo

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-070 | Estado de seguridad del archivo: `PENDING_SCAN`, `CLEAN`, `INFECTED`, `SCAN_FAILED`, `SKIPPED` | P0 |
| FR-046-071 | Un archivo no `CLEAN` **no se descarga ni se previsualiza** | P0 |
| FR-046-072 | El análisis es una **capacidad de despliegue configurable**; sin analizador, el estado es `SKIPPED` y **se declara** (§48) | P0 |
| FR-046-073 | El resultado del análisis se audita | P0 |

### API, permisos y auditoría

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-080 | Contratos de documento, versión, vínculo, subida, descarga y previsualización | P0 |
| FR-046-081 | Contrato de vinculación que **no expone** el almacenamiento (§94) | P0 |
| FR-046-082 | `allowed_actions` calculado en backend según permiso, estado, referencias, retención, empresa y análisis (§63) | P0 |
| FR-046-083 | Permisos con la convención vigente de la Spec 003; sin RBAC nuevo | P0 |
| FR-046-084 | Auditoría por la capacidad transversal; sin tabla local (§60) | P0 |
| FR-046-085 | La descarga se audita **según política del tipo**, no siempre (§61) | P0 |
| FR-046-086 | `If-Match` con el mecanismo existente (§59) | P0 |
| FR-046-087 | Aislamiento multiempresa en listar, consultar, descargar, vincular y versionar (§9) | P0 |
| FR-046-088 | Contratos de evento `document.uploaded`, `version.created`, `document.expiring`, `document.scan_failed`; **046 no notifica** (§65) | P1 |

### Frontend

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-090 | Biblioteca documental con URL propia, filtros y paginación | P0 |
| FR-046-091 | Detalle con metadata, vínculos e historial de versiones | P0 |
| FR-046-092 | Componente de adjuntos **reutilizable** por cualquier dominio (§97) | P0 |
| FR-046-093 | Subida operable **sin arrastrar y soltar** (§161) | P0 |
| FR-046-094 | Estado de la carga claro; sin porcentaje fingido si no se conoce (§99) | P0 |
| FR-046-095 | Errores diferenciados por causa; nunca «error desconocido» (§100) | P0 |
| FR-046-096 | Previsualización adaptada en pantalla estrecha; alternativa usable (§106) | P1 |
| FR-046-097 | Nombres de archivo largos no rompen la disposición (§104) | P0 |

### Contratos para Specs consumidoras

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-100 | Contrato de la Spec 045 satisfecho **sin cambiar el modelo de 045** (§27) | P0 |
| FR-046-101 | Contratos para 018, 019, 020, 027, 035, 040, 044 y 051 | P0 |
| FR-046-102 | Metadata regulatoria (emisor, número, emisión, vencimiento) disponible **sin** convertir 046 en motor regulatorio (§33) | P0 |
| FR-046-103 | El consumidor declara qué tipos exige y su cardinalidad; 046 **no** los codifica (§29) | P0 |
| FR-046-104 | Consulta eficiente de documentos próximos a vencer, para que 047 la consuma (§135) | P1 |
| FR-046-105 | Referencia externa admitida y **marcada como no administrada** (§112) | P1 |

### Migración legada

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-110 | `file_metadata` evoluciona sin backfill: está vacía de uso (ADR: `SAFE_MIGRATION`) | P0 |
| FR-046-111 | Las 9 columnas `UNVERIFIED_LEGACY` se conservan y se marcan; **no** se crean documentos por texto | P0 |
| FR-046-112 | Un binario localizable se importa calculando su hash y preservando el original (§113) | P1 |
| FR-046-113 | Si la base afirma archivo y no está, se registra `MISSING_LEGACY_FILE`; **no se inventa** (§114) | P0 |
| FR-046-114 | Un hash histórico **sin binario** no se convierte en documento (R-046-5) | P0 |

### Delta dirigido CONC-046 — dos subidas simultáneas de versión (2026-09-15)

Detalle: `conc-046-concurrent-version-delta.md`.

| ID | Requisito | Prioridad |
|---|---|---|
| FR-046-115 | Dos creaciones simultáneas de versión del mismo documento producen **exactamente una** versión nueva y una sola vigente; la que pierde recibe `409 VERSION_CONFLICT`, nunca un 500. Decide la restricción de PostgreSQL | P0 |
| FR-046-116 | La operación que pierde no deja versión, archivo registrado, análisis, auditoría ni binario en el almacenamiento | P0 |
| FR-046-117 | Con la misma `Idempotency-Key`, la que pierde la carrera recibe la versión ganadora como acierto idempotente | P0 |
| FR-046-118 | El acierto idempotente devuelve la versión que creó esa clave en ese documento, no la vigente de después ni la de otro documento | P0 |
| FR-046-119 | Subidas a documentos distintos, de la misma empresa, de otra o de otro tenant, no se bloquean entre sí; aislamiento y permisos intactos | P0 |

## 8. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-046-01 | Listar documentos **no** lee binarios (§132) |
| NFR-046-02 | Biblioteca paginada; sin carga completa (§133) |
| NFR-046-03 | Índices justificados por consulta real (§89) |
| NFR-046-04 | WCAG 2.2 AA en las pantallas de 046, incluida la subida |
| NFR-046-05 | Responsive de 320 a 1920 px sin scroll horizontal |
| NFR-046-06 | Páginas completas con URL propia; modal solo para confirmación breve |
| NFR-046-07 | **Toda la evidencia sobre PostgreSQL 18.x y un proveedor de almacenamiento real**, no solo simulado (§158) |
| NFR-046-08 | Sin tipos ni extensiones codificados: todo es dato (P8) |
| NFR-046-09 | Sin registrar contenido, secretos ni URL firmadas (§130) |

## 9. Reglas no negociables

1. Ningún módulo implementa su propio almacenamiento de archivos.
2. Documento lógico y archivo físico son cosas distintas.
3. La `storage_key` es opaca y la genera el servidor.
4. El nombre que envía el usuario **nunca** es una ruta.
5. Una versión histórica **no** se sobrescribe.
6. El original se conserva byte a byte; lo derivado es derivado.
7. Conocer el identificador de un archivo **no** da acceso a él.
8. Sin URL públicas permanentes.
9. La previsualización tiene la misma seguridad que la descarga.
10. Un archivo no analizado como limpio no se entrega.
11. La evidencia en uso histórico no se borra.
12. Un hash sin binario **no es un documento**.
13. La base de datos es la autoridad del catálogo; el almacenamiento solo guarda bytes.
14. 046 provee la capacidad; la regla de negocio es del consumidor.
