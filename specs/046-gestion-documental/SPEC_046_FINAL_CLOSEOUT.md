# SPEC 046 — FINAL CLOSEOUT

**Gestión documental** · 2026-08-30 · `develop` · PostgreSQL **18.6** · ClamAV **1.4.3**

---

## 1. Estado

**`SPEC 046 COMPLETE_100`** — cuarta Spec del proyecto en alcanzarlo, tras 045, 008 y 011.

Con dos salvedades declaradas, no ocultas: el adaptador compatible con S3 está
implementado pero **sin verificar contra un servicio real** en este entorno, y la
purga por retención existe como operación pero **sin planificador**, porque la
plataforma todavía no tiene trabajador común y crearlo aquí sería ampliar el
alcance. Ambas se detallan en §36.

## 2. Qué se construyó, y qué deliberadamente no

046 es una **capacidad transversal**, no un módulo de «subir archivos». La
diferencia se ve en que ningún dominio consumidor guarda archivos: consulta a 046.

| Se construyó | No se construyó, a propósito |
|---|---|
| Modelo documental de 8 entidades | Microservicio documental |
| Abstracción de almacenamiento con 2 proveedores | Binarios en PostgreSQL |
| Flujo de subida con 8 controles en orden | OCR, miniaturas, deduplicación |
| Versionado inmutable y congelación histórica | Retención legal con plazos inventados |
| Vinculación autorizada a 19 tipos de recurso | Procesos consumidores (son de sus Specs) |
| Componente de adjuntos reutilizable | Un componente por módulo |
| Anotación del legado | Documentos falsos a partir de texto suelto |

## 3. Fases ejecutadas

| Fase | Contenido | Tareas | Estado |
|---|---|---:|---|
| F1 · Modelo y catálogo | 8 entidades, catálogo vacío | 11 | DONE |
| F2 · Almacenamiento | Abstracción + 2 proveedores | 8 | DONE |
| F3 · Servicio | Flujo de subida y versionado | 12 | DONE |
| F4 · Vinculación y autorización | **Antes que la API** | 11 | DONE |
| F5 · Seguridad del archivo | Análisis, estados, retención | 8 | DONE |
| F6 · API | 14 rutas | 11 | DONE |
| F7 · Pruebas de backend | 5 archivos, suite de amenazas | 14 | DONE |
| F8 · Frontend | 3 pantallas + 1 componente | 12 | DONE |
| F9 · Legado, E2E y cierre | Anotación, importación, E2E | 16 | DONE |

**F4 fue antes que F6**, y no por gusto: una API de documentos sin autorización
sobre la entidad vinculada no es una funcionalidad incompleta, es una
vulnerabilidad. El orden es el control.

## 4. Modelo implementado

```
DocumentCategory ─┐
                  ├─ DocumentType ──┐
                  │   (política)     │
                  │                  ├─ Document ── DocumentVersion ── StoredFile
                  │                  │   (lógico)     (inmutable)      (binario)
                  │                  │                     │                │
                  │                  └─ DocumentLink ──────┘         FileSecurityScan
                  │                     (frozen_version_id)
                  └───────────────── LegacyDocumentReference (no es un documento)
```

Tres estados **separados**, que en la mayoría de los sistemas se confunden:

| Concepto | Estado | Valores |
|---|---|---|
| El documento lógico | `Document.status` | `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED`, `REVOKED` |
| El binario | `StoredFile.status` | `AVAILABLE`, `QUARANTINED`, `PURGED` |
| Su seguridad | `StoredFile.security_status` | `PENDING_SCAN`, `CLEAN`, `INFECTED`, `SCAN_FAILED`, `SKIPPED` |

`EXPIRED` **no está en ninguna de las tres listas**: es derivado de
`expiration_date`, no un estado persistido. Persistirlo obligaría a un proceso
que lo mantuviera al día, y un documento vencido cuyo estado nadie actualizó es
peor que no tener el estado.

## 5. El orden del flujo de subida

No es una secuencia cualquiera; cada paso existe porque el anterior no basta:

```
1. temporal      → nada se registra antes de pasar los controles
2. tamaño        → corte en flujo, sin consumir el archivo entero
3. MIME real     → por contenido; el declarado solo sirve para detectar mentiras
4. política      → lista blanca del tipo; vacía significa NINGUNO
5. análisis      → sin analizador NO hay CLEAN: falso seguro
6. hash          → lo calcula el servidor; el del cliente se ignora
7. almacenamiento→ clave opaca generada por el servidor
8. verificación  → «escribí» no es «está y es el que era»
9. confirmación  → solo ahora nace el StoredFile en AVAILABLE
```

Si el paso 8 falla, se borra el objeto y se responde 503. Si algo falla después,
la transacción revierte y queda un binario huérfano: **basura recuperable, no
evidencia perdida**. Se eligió ese lado del error a conciencia.

## 6. Almacenamiento

| Proveedor | Estado | Verificación |
|---|---|---|
| `FilesystemStorageProvider` | Producción | Suite de conformidad completa sobre disco real |
| `S3CompatibleStorageProvider` | Implementado | **Sin verificar**: no hay servicio real en este entorno |

El `endpoint_url` es obligatorio y configurable: eso es lo que lo hace compatible
con MinIO, Ceph o el propio S3 sin acoplarse a ninguno. Las credenciales llegan
por entorno y no viven en la base, ni en el frontend, ni en un registro.

Elegir proveedor es **configuración, no código**: `get_storage()` lo resuelve y
ningún servicio de negocio lo consulta.

## 7. ESC-046-01 — analizador real, RESUELTO

La escalación exigía un analizador **real** en QA, no un `TODO`, ni una interfaz
vacía, ni un proveedor que siempre dice «limpio».

| Elemento | Valor |
|---|---|
| Motor | ClamAV **1.4.3**, extraído del `.deb` de PGDG sin privilegios |
| Base de firmas | `freshclam`, **3.28 M** firmas |
| Fixture de malware | Cadena **EICAR** — fixture de prueba estándar, **no** malware real |
| Resultado con EICAR | `INFECTED` + firma reconocida → subida rechazada, nada almacenado |
| Resultado con PDF limpio | `CLEAN` → subida aceptada |
| Sin analizador disponible | `SCAN_FAILED` — **nunca** `CLEAN` |
| Análisis desactivado por configuración | `SKIPPED`, **declarado** al cliente en cada respuesta |

`SCAN_FAILED` nunca se entrega. `SKIPPED` viaja siempre en la respuesta para que
nadie lea «sin analizar» como «verificado».

**ESC-046-01: RESUELTO.**

## 8. Modelo de amenazas — `AMZ-01`..`AMZ-20`

Una prueba por amenaza, en `tests/test_documents_security.py`. Ninguna se excluyó.

| Id | Amenaza | Control verificado |
|---|---|---|
| AMZ-01 | Recorrido de rutas | 6 vectores (`../`, absoluta, Windows, codificada, doble) — el nombre del usuario nunca toca el disco |
| AMZ-02 | Suplantación de MIME | ELF con nombre y `Content-Type` de PDF → rechazado, sin versión |
| AMZ-03 | Ejecutable | Rechazado por lista blanca y por familia peligrosa |
| AMZ-04 | Contenido activo | SVG con guion → `attachment`, `nosniff`, `sandbox`, aunque el tipo lo declare en línea |
| AMZ-05 | XSS por nombre | Nombre con etiquetas → dato en JSON, cabecera con comillas balanceadas |
| AMZ-06 | Referencia insegura directa | 4 endpoints con identificador ajeno → **404**, nunca 403 |
| AMZ-07 | Fuga entre empresas | Las 5 operaciones aisladas: listar, crear, subir, vincular, ver tipos |
| AMZ-08 | URL pública | 4 respuestas sin `storage_key`, ruta ni URL |
| AMZ-09 | URL firmada de vida larga | No existe: el proveedor no expone ningún método de URL |
| AMZ-10 | Malware | EICAR rechazado; **el almacenamiento no cambió**; descarga 404 |
| AMZ-11 | Bomba de descompresión | Comprimidos rechazados por defecto |
| AMZ-12 | Adivinación de clave | Mismo archivo y nombre → claves distintas; sin nombre ni extensión |
| AMZ-13 | Sobrescritura | v1 sigue en disco con sus bytes tras cargar v2 |
| AMZ-14 | Hash como autorización | Conocer el `sha256` no abre ninguna vía |
| AMZ-15 | Asignación masiva | `storage_key`, `sha256`, `version_number` del cliente ignorados |
| AMZ-16 | Vinculación no autorizada | Permiso sobre el **destino**; recurso inexistente → 404 |
| AMZ-17 | Desvinculación no autorizada | Vínculo congelado → 409 `LINK_FROZEN`, también para el dueño |
| AMZ-18 | Archivo enorme | 413 con el límite en el detalle; **nada llegó al almacenamiento** |
| AMZ-19 | Inyección de cabeceras | Cabecera de una sola línea; nombre saneado sin CR/LF |
| AMZ-20 | Fuga por registros | Ni contenido, ni raíz, ni contraseña, ni `storage_key` en trazas ni en auditoría |

Además, tres fallos de almacenamiento que **no** se disfrazan de entrega:

| Situación | Respuesta |
|---|---|
| La escritura falla | 5xx y **cero versiones** creadas |
| El objeto ya no está | 500 `STORAGE_OBJECT_MISSING` |
| El objeto cambió bajo los pies | 500 `STORAGE_HASH_MISMATCH` |
| El archivo no superó el análisis | 409 `FILE_NOT_SCANNED` |

## 9. Autorización — por la entidad, no por el documento

Tres reglas que no son negociables:

1. **Vincular** exige permiso sobre la **entidad de destino**, no sobre el documento.
2. **Leer un archivo** exige poder ver alguna entidad vinculada. Un documento
   suelto, aún sin adjuntar, lo lee quien tenga permiso documental.
3. **Previsualizar** exige el **mismo** permiso que descargar, no uno menor.

Y una regla de forma: se responde **404, no 403**. Un 403 confirma que el
recurso existe, y eso ya es información.

## 10. Versionado y congelación — el contrato con la Spec 045

| Contrato publicado por 045 | Estado |
|---|---|
| Vincular evidencia a `ApprovalRequest` | **Satisfecho** |
| «No exige cambios en el modelo de 045» (CL-045-10) | **Satisfecho — 0 cambios en 045** |
| La evidencia interina en texto se conserva | **Satisfecho** |
| CVG-045-04 · dependencia diferida a 046 | **Cerrada** |

Cuando una aprobación se resuelve, `freeze_links` congela **la versión que se
usó**. Cargar después una v2 no reinterpreta la decisión: quien lea la
aprobación descarga los bytes que existían cuando se aprobó. Es la diferencia
entre un archivo adjunto y una evidencia.

## 11. Migraciones

| Migración | Qué hace | Resultado |
|---|---|---|
| `0023_document_model` | 7 tablas nuevas; `file_metadata` → `stored_files` con renombrado explícito de sus 3 índices | PASS sobre PostgreSQL 18.6 |
| `0024_document_legacy_marks` | Anota 12 columnas heredadas; concede 9 permisos | PASS |

`0024` **lee datos**, y por eso no es válida en modo `--sql`. Se dice en su
cabecera, no se descubre en producción.

## 12. Legado — anotar no es convertir

| Métrica de `0024` | Valor exigido | Valor obtenido |
|---|---:|---:|
| `documents_created` | **0** | **0** |
| `columns_modified` | **0** | **0** |

La migración comprueba su propia invariante y **aborta** si alguna anotación
creó un documento.

Las cinco formas del legado, cada una con su desenlace, verificadas con fixture:

| Forma | Clasificación | ¿Documento? |
|---|---|---|
| URL absoluta | `EXTERNAL_REFERENCE` | No: no es un archivo nuestro |
| Ruta relativa sin binario localizable | `MISSING_FILE` | No: **reportado, no inventado** |
| Ruta relativa con binario localizable y verificado | `VALID_MANAGED_FILE` | Sí, en `PENDING_SCAN` |
| Binario localizado con huella distinta | `MIGRATION_BLOCKER` | No: se detiene |
| Hash suelto | `LEGACY_HASH_WITHOUT_FILE` | No: un hash no es un archivo |

Lo importado nace en `PENDING_SCAN` y **no se entrega**: el legado no pasó por
el analizador de hoy, y decir lo contrario sería una mentira cómoda.

Ninguna fuente heredada se modifica ni se borra. `test_ninguna_importacion_borra_la_fuente`
lo comprueba explícitamente.

## 13. Frontend

| Pantalla | Ruta | Qué resuelve |
|---|---|---|
| Biblioteca | `/documentos` | Lista con 4 filtros y paginación; **no abre un solo binario** |
| Detalle | `/documentos/:id` | Metadata, historial de versiones, vínculos |
| Tipos documentales | `/documentos/tipos` | La política, declarada por el usuario, no por el código |
| `AdjuntosPanel` | componente | **Único** componente de adjuntos de la plataforma |

Decisiones que se ven al usarlo:

- La carga funciona **solo con teclado**: `<input type="file">` nativo, enfocable.
  Arrastrar y soltar sería un extra, nunca el único camino.
- El estado dice «Subiendo…» y «Verificando…», **sin porcentaje inventado**.
- Cada error tiene su mensaje y su salida. Nunca «error desconocido»: si el
  archivo excede el límite, se dice cuál es; si el formato no se admite, se dice
  cuáles sí.
- Los nombres largos se truncan **por el centro**, conservando la extensión, que
  es lo que identifica el archivo.

Un defecto encontrado por sus propias pruebas: `ApiError` descartaba `details`,
con lo que esos mensajes accionables nunca habrían podido leer el límite ni la
lista de formatos. Corregido en `src/api/client.ts`.

## 14. Pruebas

| Archivo | Qué cubre |
|---|---|
| `test_documents.py` | Flujo, versionado, metadata, retención, rendimiento |
| `test_documents_security.py` | `AMZ-01`..`AMZ-20`, fallos de almacenamiento, concurrencia, contrato |
| `test_documents_storage.py` | Conformidad parametrizada por proveedor |
| `test_documents_legacy_import.py` | Los 5 casos del fixture legado |
| `test_documents_migration_0024.py` | Anotación, invariantes y reversión de la migración |

Sobre **PostgreSQL 18.6 real**, **almacenamiento en disco real** y **ClamAV
real**. Ningún doble de prueba sustituye a ninguno de los tres en el camino
principal.

### Resultados ejecutados

| Suite | Resultado |
|---|---|
| Backend completo, PostgreSQL 18.6 | **431 pasan · 8 omitidas · 0 fallan** (439 recolectadas) |
| — de las cuales, de 046 | **88** repartidas en 5 archivos |
| Omitidas | Las 8 de conformidad S3, por no haber servicio real. **Se omiten diciéndolo** |
| Frontend (Vitest) | **236 pasan · 0 fallan** |
| E2E documental, 3 navegadores | **36 pasan · 0 fallan** (12 × Chromium, Firefox, WebKit) |
| E2E de toda la plataforma, Chromium | **65 pasan · 1 falla preexistente** (ver §16) |

Las pruebas E2E se ejecutaron contra el sistema levantado de verdad: uvicorn
sobre PostgreSQL 18.6, Vite sirviendo el frontend, almacenamiento en disco y
ClamAV analizando cada archivo. La prueba de malware tarda entre 10 y 17
segundos por navegador porque **el análisis ocurre de verdad**.

Seis de las pruebas E2E fallaron en su primera ejecución. Las seis eran
selectores ambiguos en el propio archivo de prueba —«Cargar» también prefija
«Descargar la versión 1»; el mensaje de error aparece dos veces por diseño,
junto al formulario y como notificación—. En los seis casos el sistema había
hecho exactamente lo correcto y lo mostraba en pantalla. Se corrigieron los
selectores, no las afirmaciones.

## 15. Convergencia y trazabilidad

| Comprobación | Resultado |
|---|---|
| OpenAPI global | **294 rutas**, 14 bajo `/documentos` |
| Deriva de Alembic | Idéntica a la línea base previa a 046: **0 atribuible a 046** |
| `storage_key` en respuestas | **0** |
| `storage_key` en frontend | **0** (solo un comentario y una aserción negativa) |
| Tipos documentales codificados | **0** — los catálogos nacen vacíos (NFR-046-08) |
| Tipos de recurso registrados | **19**, registro cerrado |
| Permisos `documentos:*` | 9, con la convención de la Spec 003 |

### `/speckit.converge 046`

| Comprobación | Resultado |
|---|---|
| Autoridad única documental (P22) | ✅ 0 accesos al almacenamiento fuera del módulo |
| Sistemas paralelos de adjuntos | ✅ 0 |
| RBAC paralelo | ✅ 0 — 20 rutas usan `require_permission("documentos", …)` |
| Auditoría paralela | ✅ 0 — se usa `record_audit` |
| Aprobaciones duplicadas | ✅ 0 |
| Otras Specs implementadas por 046 | ✅ 0 — solo 2 archivos ajenos tocados, y por evolución declarada |
| Deriva de migraciones | ✅ 0 atribuible a 046 |
| Tipos documentales codificados | ✅ 0 |

Los dos archivos ajenos tocados son `system/models.py` (de donde `FileMetadata`
se marchó al evolucionar a `StoredFile`) y `setup/api.py` (los 9 permisos
nuevos). Ninguno implementa lógica de otra Spec.

**PASS.**

## 16. Deuda declarada

| Id | Qué | Por qué no se cerró aquí |
|---|---|---|
| DEUDA-046-1 | Conformidad del adaptador S3 sin verificar | No hay servicio compatible con S3 en este entorno. Las pruebas existen y **se omiten diciéndolo**; un doble no demostraría nada |
| DEUDA-046-2 | Purga sin planificador | La plataforma no tiene trabajador común. Crear un planificador propio violaría FR-046-066. La operación queda lista para que ese trabajador la invoque |
| DEUDA-046-3 | E2E regulatorio por interfaz | La Spec 044 no tiene pantallas de permiso con carga. El contrato está verificado en backend |
| DEUDA-046-4 | `UnsavedChangesGuard` no aplicado | Los formularios de 046 son de una línea y la carga es inmediata; aplicarlo añadiría fricción sin proteger nada |

Ninguna de las cuatro afecta a una regla no negociable de la Spec.

## 17. Specs desbloqueadas

De las 8 que 046 bloqueaba:

| Situación | Specs |
|---|---|
| **Desbloqueadas** — su entidad ya está registrada | 019, 027, 035, 044, 051 — **5** |
| A la espera de **su propio** modelo de dominio | 018, 020, 040 — **3** |

Las tres pendientes no están bloqueadas *por 046*: lo que les falta es su
entidad, que es suya. Registrarla después será una línea en `resources.py` y no
tocará ningún servicio. El detalle está en §5 de
`document-consumer-contract-matrix.md`.

## 18. Próxima Spec

**`012`**, según el roadmap vigente. **No se ha iniciado**: requiere autorización
expresa, y esta implementación no la sustituye.


## 19. Deuda externa

| Deuda | Clasificación | Destino |
|---|---|---|
| 18 líneas de deriva de licenciamiento e inventario | `DEFERRED_EXTERNAL_DEPENDENCY` | Specs 010 / 054 |
| `route-crawl.spec.ts` acumula 401 de `/auth/refresh` | `DEFERRED_EXTERNAL_DEPENDENCY` | Spec 054 |
| `installations.key_reference` es `varchar(120)` | **Observación** | Una ruta de instalación algo larga rompe el arranque. No es de 046 |

Sobre la segunda: el token de acceso vive en memoria (ADR-004), de modo que un
`goto` que recarga la página lo pierde y la primera petición devuelve 401 antes
de que la renovación lo reponga. Las rutas que lo producen son
`/organizacion/almacenes` (Spec 008) y `/tesoreria/maestros` (Spec 006);
**ninguna ruta de 046 aparece**. Se comprobó instrumentando el recorrido, no
suponiéndolo.

## 20. Veredicto

**`SPEC 046 COMPLETE_100`**

0 BLOCKER · 0 CRITICAL · 0 contradicciones · 0 requisitos huérfanos ·
PostgreSQL 18.6 · ClamAV 1.4.3 real con 3,28 M de firmas · 2 migraciones PASS ·
**0 documentos creados por migración** · **0 columnas heredadas modificadas** ·
20/20 amenazas del modelo con prueba propia · 19 tipos de recurso registrados ·
0 `storage_key` en respuestas · 431/431 backend + 236/236 frontend + 36/36 E2E
en tres navegadores · WCAG 2.2 AA sin violaciones serias · 6 viewports sin
desbordamiento · convergencia PASS · ESC-046-01 **RESUELTO**.

Con 4 deudas declaradas (§16), ninguna sobre una regla no negociable.

**No se inicia la Spec 012.** Requiere autorización expresa.
