# SPEC 009 · Delta — SHARED-CORE-P0-HARDENING-02E · AUTHENTICATED REPORT / EXPORT DOWNLOAD

| Campo | Valor |
|---|---|
| Spec dueña | **009** (reportes y auditoría: FR-009-020 «exportación auditada», KAUD-002 descarga del archivo real). Spec afectada: **003** (autorización de lectura, 02D/ADR-019) |
| Deuda que cierra | **REPORT-EXPORT-DOWNLOAD-ANCHOR** (MEDIUM, registrada en 02D) |
| HEAD de entrada | `36f076c` (develop = origin/develop) |
| Evidencia | `evidence/report-export-download/` |
| Decisiones de la dueña | **OD-DOWNLOAD-01..05** (encargo 02E, ratificadas): la descarga sigue autenticada; sin token en URL, query, nombre ni Referer; transporte autenticado → Blob → URL de objeto temporal → descarga → revocación; se conservan autenticación, `reportes:export`, capacidad de origen, tenant y empresa; nombre de fichero de un contrato seguro; fallos distinguibles. Se mantienen OD-READ-01..06 (ADR-019) y OD-UI-01 (ADR-018) |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| DATABASE_CHANGE | NOT_APPLICABLE |
| NORMATIVE_RESEARCH | NOT_APPLICABLE (comportamiento técnico de descarga autenticada; ninguna norma venezolana lo condiciona) |
| Estado | **IMPLEMENTED — VERIFIED — CONVERGED** (autorizado por el encargo «SHARED-CORE-P0-HARDENING-02E»; §13–§19) |

## 1. Discover (medido en `36f076c`)

### 1.1 DOWNLOAD_SURFACE_MATRIX

Barrido de todo `src/` (`<a href>`, `window.open`, `location.href`, URLs `/api/v1/…` directas, `createObjectURL`, `responseType: "blob"`, `data:`, `window.print`, CSV, PDF):

| SURFACE_ID | Pantalla | Módulo | Ruta | Mét. | MIME | Nombre esperado | Auth | Capacidad | Origen | Empresa | Tenant | Mecanismo actual | Contrato backend | Resultado actual | Fix | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DL-01 | `reportes/exportaciones` · «Descargar» | 009 | `GET /reporting/exports/{id}/download` | GET | `text/csv; charset=utf-8` o `application/pdf` | `report-<clave>-<sello>.<csv\|pdf>` (`Content-Disposition`) | sí | `reportes:export` | la del reporte (AD-5 de 02D) | sí | sí | `<a href="/api/v1/…">` sin `download`: navegación del navegador **sin `Authorization`** | 200 binario; 401/403/404 JSON | **ROTO** (la petición sale sin credencial: 401) | SÍ | DOWNLOAD-E2E-01..08 |
| DL-02 | `reportes/centro` · «Exportar CSV (auditado)» | 009 | `POST /reporting/exports` (+ DL-01) | POST | — | — | sí | `reportes:export` | la del reporte | sí | sí | `apiFetch` crea la exportación y avisa «Archivo X · DONE»; **no entrega el archivo** | 200 JSON con `id` y `file_ref` | **PROCESO INCOMPLETO**: hay que ir a otra pantalla, que además está rota (DL-01) | SÍ | DOWNLOAD-E2E-09 |
| DL-03 | `documentos/:id` · versión | 046 | `GET /documentos/{id}/versiones/{v}/descargar` | GET | el del archivo | `original_name` | sí | `documentos:download` + entidad vinculada | — | sí | sí | `apiFetch(…, { responseType: "blob" })` → URL de objeto → revocación | 200 binario | OK | NO (Spec 046, NO-OP de 02D) | pruebas de 046 |
| DL-04 | Panel de adjuntos | 046 | `GET /documentos/{id}/descargar` | GET | el del archivo | `original_name` o título | sí | ídem | — | sí | sí | ídem | 200 binario | OK | NO | pruebas de 046 |
| DL-05 | Códigos de recuperación MFA | 002 | — (no hay API) | — | `text/plain` | `kontrol-codigos-recuperacion.txt` | — | — | — | — | — | `data:` URL con los códigos que la pantalla ya muestra; el `href` se vacía tras el clic | ninguno | OK; **no es una descarga protegida** | NO | pruebas de 002 |

No es descarga: `TasasPage` sube un CSV. Los trabajos de reporte (`/reporting/jobs`) guardan `result_ref`, pero no generan archivo ni tienen ruta de descarga (§9, deuda).

**DOWNLOAD_SURFACE_COUNT = 5 · UNINVENTORIED_DOWNLOAD_SURFACES = 0 · rotas: 1 (DL-01) · proceso incompleto: 1 (DL-02).**

### 1.2 Transporte autenticado existente

`src/api/client.ts` → `rawFetch` es la primitiva:
- pone `Authorization: Bearer` desde la memoria (ADR-004: nunca `localStorage`), `credentials: "include"` y la cabecera de empresa, fijada al construir la petición;
- con `responseType: "blob"`, solo un 2xx se devuelve como binario; un 4xx/5xx JSON se convierte en `ApiError` (`code`, `status`): **nunca se guarda un error como archivo**;
- `apiFetch` renueva la sesión una vez ante 401 y reautentica ante `REAUTH_REQUIRED`;
- un fallo de red llega como `TypeError` (no `ApiError`).

**Falta:** el acceso a `Content-Disposition` (la primitiva devuelve solo el `Blob`) y una función única que cree la URL de objeto, dispare la descarga y la revoque.

### 1.3 Contrato del backend (sin cambios)

`download_export`:
- **Autorización:** `require_permission("reportes", "export")`, después `get_company_context` (empresa + capacidad en la empresa), después la capacidad de origen de `export.report_key` (AD-5).
- **Respuesta:** el archivo, `StreamingResponse` en memoria con `media_type` CSV o PDF y `Content-Disposition: attachment; filename="<path.name>"`.
- **Nombre:** sale del servidor (`report-<clave>-<AAAAMMDDhhmmss>.<ext>`). La clave está validada contra `CAPACIDADES_DE_REPORTE`: no la escribe el usuario.
- **Errores:** 401 `AUTH_REQUIRED`, 403 `PERMISSION_DENIED`/`COMPANY_SCOPE_FORBIDDEN`, 404 `EXPORT_NOT_FOUND`/`EXPORT_FILE_MISSING`/`REPORT_NOT_FOUND`, todos en JSON.

### 1.4 Tamaño

Los archivos son reportes de una empresa. El servidor ya los lee enteros en memoria (`path.read_bytes()`) antes de servirlos, así que un `Blob` en el navegador no añade un límite nuevo. El encargo no fija exportaciones masivas en streaming. **Blob aceptable** (OD-DOWNLOAD-02; sin MATERIAL_OQ).

## 2. Reproducción

DOWNLOAD-E2E (T01) en rojo antes de implementar (`evidence/report-export-download/rojo-e2e.txt`):
- con un usuario autorizado, el clic en «Descargar» no produce ningún evento `download`;
- la API con el cliente autenticado responde 200: RPE-11 de 02D, y DOWNLOAD-E2E-02 lo vuelve a medir.

## 3. Causa raíz

`ExportacionesPage.downloadExport` crea un `<a href="/api/v1/reporting/exports/{id}/download">` y lo pulsa. Es una navegación del navegador y no lleva la cabecera `Authorization`, que solo pone `rawFetch`: el token vive en memoria, no en una cookie (ADR-004). El backend responde 401 con razón. El Centro de reportes nunca pidió el archivo tras crearlo.

## 4. Requisitos

| ID | Requisito |
|---|---|
| DL-FR-01 | Un usuario autorizado descarga, desde Exportaciones, el archivo real de una exportación de su empresa |
| DL-FR-02 | El archivo es el que el servidor entrega: bytes no vacíos (PDF), nombre seguro y MIME del servidor |
| DL-FR-03 | El token nunca aparece en URL, query, fragmento, nombre, DOM, consola, mensajes ni evidencia; la URL de la descarga es `blob:` |
| DL-FR-04 | La URL de objeto se revoca tras disparar la descarga |
| DL-FR-05 | Nombre seguro: de `Content-Disposition` (`filename*` RFC 5987 antes que `filename`); sin separadores de ruta, sin caracteres de control ni CR/LF, longitud acotada; si falta o queda vacío, un nombre de reserva determinista y saneado |
| DL-FR-06 | Errores distinguibles: `PERMISSION_DENIED`, `COMPANY_SCOPE_FORBIDDEN`, no encontrado (`*_NOT_FOUND`, `EXPORT_FILE_MISSING`), red y cualquier otro fallo; nunca se anuncia éxito sin `Blob` |
| DL-FR-07 | Mientras una descarga está en curso, su botón queda ocupado: sin doble petición accidental; descargas sucesivas funcionan |
| DL-FR-08 | El backend no cambia: sin autenticación → 401; sin `reportes:export` → 403; sin capacidad de origen → 403; otra empresa → 403/404; otro tenant → 404 |
| DL-FR-09 | El Centro de reportes completa el proceso «exportar»: crea la exportación auditada y entrega el archivo en la misma acción |
| DL-FR-10 | Una sola primitiva de descarga autenticada para los reportes, apoyada en `rawFetch` (sin leer el token en los componentes) |

## 5. Diseño

- **AD-1 · Primitiva.** `RequestOptions.responseType` admite `"archivo"`. Con 2xx, `rawFetch` devuelve `{ blob, contentDisposition }` (la cabecera, o `null`). Los errores siguen el contrato JSON → `ApiError`. Sin otra vía de autenticación.
- **AD-2 · Módulo `src/api/descargas.ts`.**
  - `nombreSeguro(contentDisposition: string | null, reserva: string): string`, pura (DL-FR-05).
  - `descargarArchivo(ruta: string, reserva: string): Promise<string>`: llama a `apiFetch(ruta, { responseType: "archivo" })`, crea la URL de objeto, pulsa un `<a download>` temporal, lo retira del DOM, revoca la URL en el mismo turno tras el clic (el patrón de Spec 046, probado) y devuelve el nombre usado.
  - `mensajeDeDescarga(error: unknown): string`, que asigna los textos de DL-FR-06.
- **AD-3 · Exportaciones.** «Descargar» llama a `descargarArchivo` con la reserva `exportacion-<id>`. Aviso de éxito «Archivo descargado» con el nombre. Ante un error, aviso de error con `mensajeDeDescarga`. Ocupado durante la descarga (DL-FR-07). Sin `reportes:export` el botón sigue oculto (AD-6 de 02C).
- **AD-4 · Centro.** «Exportar CSV (auditado)» crea la exportación y, con su `id`, llama a `descargarArchivo`. Éxito solo con archivo. Si la creación funcionó y la descarga no, avisa de que la exportación quedó creada y se puede descargar desde Exportaciones.
- **AD-5 · Sin cambios** en backend, OpenAPI, base de datos ni documentos (Spec 046).

### Textos (field contract de los mensajes)

| Caso | Texto |
|---|---|
| Éxito | «Archivo descargado» · descripción: el nombre |
| `PERMISSION_DENIED` | «No tiene permiso para descargar este archivo.» |
| `COMPANY_SCOPE_FORBIDDEN` | «No tiene esa autoridad en esta empresa.» |
| No encontrado | «El archivo ya no existe o no está disponible.» |
| Red (`TypeError`) | «No hay conexión con el servidor. Inténtelo de nuevo.» |
| Otro | «No fue posible descargar el archivo.» |
| Título del aviso de error | «No fue posible descargar» |
| Centro, exportación creada sin archivo | «La exportación quedó creada; puede descargarla desde Exportaciones.» |

## 6. Modelo de amenazas (§48)

| Amenaza | Control | Requisito | Prueba |
|---|---|---|---|
| Token en query, URL, historial o Referer | Cabecera `Authorization` solo en `rawFetch`; descarga desde `blob:` | DL-FR-03 | DOWNLOAD-E2E-02 (ninguna URL pedida lleva el token; la descarga es `blob:`) |
| Descarga sin autenticar | Backend sin cambios | DL-FR-08 | DOWNLOAD-E2E-05 |
| Otra empresa / IDOR | `get_company_context` + `_owned` | DL-FR-08 | DOWNLOAD-E2E-04 |
| Otro tenant | 404 | DL-FR-08 | DOWNLOAD-E2E-04 (identificador ajeno) |
| Sin capacidad de origen | AD-5 de 02D | DL-FR-08 | DOWNLOAD-E2E-06 |
| Inyección por nombre o `Content-Disposition` | `nombreSeguro` | DL-FR-05 | vitest DESC-* |
| XSS por nombre o mensaje | Texto plano en React (sin HTML) | DL-FR-05/06 | vitest |
| URL de objeto o `Blob` retenidos | Revocación inmediata; el ancla se retira | DL-FR-04 | vitest DESC (revoke llamado) |
| Doble clic | Botón ocupado | DL-FR-07 | DOWNLOAD-E2E-08 + vitest |
| Memoria con archivos grandes | El tamaño ya está acotado por el servidor (§1.4) | — | medición |
| Error guardado como archivo | `ApiError` en no-2xx | DL-FR-06 | DOWNLOAD-E2E-07, vitest |

## 7. Gate de la Constitución

| Principio | Resultado |
|---|---|
| P1/P2 (delta en la Spec dueña, autorizado por el encargo) | PASS |
| P6 (el backend decide) | PASS |
| P7 (multiempresa) | PASS |
| P10 (rojo primero) | PASS |
| P13 (trazabilidad) | PASS |
| P21 (sin respaldos silenciosos) | PASS |
| P27 (evidencia) | PASS |

P12: no hace falta ADR nuevo. Es la aplicación de ADR-004, ADR-018 y ADR-019; queda en el contrato.

Resultados del gate: BLOCKER, CRITICAL, CONTRADICTIONS y MATERIAL_OQ = 0.

## 8. Tareas

Todas: EXECUTOR DEEPSEEK y RETRY_MAX 2.

| Tarea | Modelo | Ficheros | DONE_WHEN |
|---|---|---|---|
| T01 | pro | `e2e/report-download.spec.ts` (nuevo): DOWNLOAD-E2E-01..09 | 01, 02, 08 y 09 en rojo por la causa; las de seguridad del backend, verdes |
| T02 | pro | `src/api/client.ts` (AD-1) + `src/api/descargas.ts` (nuevo, AD-2) + `src/api/descargas.test.ts` (nuevo) | vitest, tsc, eslint |
| T03 | pro | `ExportacionesPage.tsx` + su prueba (AD-3) | vitest |
| T04 | pro | `CentroReportesPage.tsx` + su prueba (AD-4) | vitest |
| T05 | flash | `specs/001-fundacion/contracts/api-contracts.md` (contrato de descarga) | revisado |

## 9. Deuda (al diseñar)

| ID | Spec | Categoría | Severidad | Evidencia | Impacto | Bloquea | Siguiente acción |
|---|---|---|---|---|---|---|---|
| EXPORT-CSV-EMPTY-WITHOUT-HEADER | 009 | Producto | LOW (preexistente) | `_to_csv([])` devuelve `""`: un reporte sin filas exporta un CSV de 0 bytes, sin cabecera | El archivo vacío no dice qué columnas tendría | No | Ciclo de reportes |
| REPORT-JOB-RESULT-NOT-DOWNLOADABLE | 009 | Producto | LOW (preexistente) | `run_job` guarda `result_ref`, pero no escribe archivo ni hay ruta de descarga | «Ejecutar job» no produce un resultado descargable | No | Ciclo de reportes (decidir si los trabajos generan archivo) |

## 10. Reconciliaciones previas a implementar

### 10.1 Tabla de capacidades por reporte (§31)

**Backend.** `CAPACIDADES_DE_REPORTE` define cinco claves:

| Clave | Capacidades de origen |
|---|---|
| `executive_ventas` | `ventas:view` |
| `operational_inventario` | `inventario:view` |
| `financial_aging` | `ventas:view`, `compras:view` |
| `regulatory_evaluaciones` | `regulatorio:view` |
| `fiscal_libros_*` (regla de prefijo) | `fiscal:view` |

**Dónde se exige.** En la vista previa, la creación de la exportación, la creación y ejecución de trabajos y la descarga, siempre además de `reportes:view` o `reportes:export`.

**Paridad.** La UI (`REPORTS` del Centro) recibe la misma tabla por la instantánea del backend, y CR-04 la verifica.

**Resultado.** Toda exportación descargable sale de una de esas claves, porque `create_export` la valida con `capacidades_de_reporte`. **REPORT_CAPABILITY_TABLE_COMPLETE = 1.**

### 10.2 CROSS-MODULE-SELECTOR-COMPOSITION (§33, solo reconciliación)

**Pantallas afectadas** (02D §1.4):
- el selector de cliente o proveedor (`/maestros/terceros`) en 14 pantallas de ventas, compras, tesorería, fiscal y regulatorio;
- la moneda (`/treasury/currencies`) en Listas de precio;
- las ubicaciones de put-away en Preparación;
- conductores y vehículos en Despacho;
- recepciones en Confirmación de inventario.

**¿Impide completar un proceso por lo demás autorizado?** Solo para un rol a medida que tiene la capacidad de negocio pero no la vista del módulo de referencia. Por ejemplo, `ventas:create` sin `maestros:view` no puede elegir cliente, y por tanto no crea el pedido.
- Ese rol no está autorizado del todo para el proceso: elegir un cliente es leer datos maestros (OD-READ-03).
- Ningún rol que se entrega lo sufre: FUNCIONAL_COMPLETO lleva todas las vistas y ADMIN no tiene negocio.
- Hoy un rol a medida solo se crea por API: la UI de alta no existe (ROLE-CREATE-UI-MISSING).

**Clasificación.** No es un BLOCKING_PRODUCT_GAP. Es una regla de composición de roles, documentada en ADR-019 (d). **Se mantiene LOW** como «futuro delta separado». Crear una capacidad de consulta mínima (`lookup:*`) exige decisión de la dueña, y no se inventa.

**CROSS_MODULE_SELECTOR_COMPOSITION_STATUS = OPEN · LOW · NON_BLOCKING.**

### 10.3 TABLE-HEADER-CONTRAST-AA (§34)

El informe de 02D decía «el contraste de la cabecera se corrigió (T16c)» y, a la vez, listaba la deuda. Medido hoy en `36f076c`:
- El patrón `thead bg-surface-100 text-text-500` sigue en **3 ficheros**: `ProductoNuevoPage.tsx`, `LibrosPage.tsx` y `MfaAltaPage.tsx`.
- El Centro de reportes ya no lo tiene (T16c).

Es el caso **B**: se corrigió una tabla y queda la deuda más amplia. La entrada de deuda era correcta («corregido en el Centro»); la frase del informe era incompleta. **TABLE_HEADER_CONTRAST_DEBT_STATUS = PARTIAL**: corregido 1 de 4 y abierto en 3, con LOW sin cambios.

### 10.4 Contabilidad de mutaciones de 02D (§35)

La certificación de 02D es la campaña total.

| Medida | Valor |
|---|---|
| TOTAL | 91 |
| KILLED | 89 |
| EQUIVALENT | 2 |
| BEHAVIORAL_SURVIVORS | 0 |
| INVALID | 0 |

El «27 / 26 / 1» del prompt siguiente que escribió Claude era **SUBSET-02D-CICLO**. Su propósito eran los mutantes propios del ciclo: B01..B20 del backend y F01..F07 del frontend; 26 muertos y 1 equivalente (F04). Las otras 64 son las regresiones de 02B y 02C. Lo erróneo era presentar el subconjunto como «línea base». Se corrige en el prompt siguiente.

## 11. Screen / Form (análisis antes de implementar)

| Superficie | Proceso | Hueco medido | Diseño |
|---|---|---|---|
| Exportaciones (DL-01) | Ver exportaciones → descargar el archivo | La acción principal no funciona | AD-3 |
| Centro de reportes (DL-02) | Elegir reporte → período → vista previa → exportar → obtener el archivo | «Exportar» no entrega el archivo | AD-4 |
| Documentos (DL-03/04) | — | Ninguno (Spec 046) | Sin cambios |

**Field contract de la acción de descarga:**

| Campo | Valor |
|---|---|
| FIELD_ID | `descargar-exportacion` |
| LABEL | `Descargar <archivo>` (nombre accesible) |
| TYPE | botón |
| ROLE_VISIBILITY | `reportes:export` |
| Backend | `reportes:export` + capacidad de origen + empresa |
| API | `GET /reporting/exports/{id}/download` |
| ERROR | textos de §5 |
| Estado | ocupado durante la petición |

**Parámetro «Período»:**
- texto libre, opcional, por defecto «0»;
- sin validación en el cliente, y el backend lo trata como texto;
- sin cambios en este ciclo.

## 12. Inventario de suites obligatorias (antes de implementar)

| RS | Suite |
|---|---|
| RS-01 | vitest dirigidas (DESC-*, Exportaciones, Centro) |
| RS-02 | Backend dirigidas: RPE-11/16 (descarga) y `test_reporting.py` |
| RS-03 | PostgreSQL completo con analizador |
| RS-04 | SQLite completo con analizador |
| RS-05 | vitest completo |
| RS-06 | tsc |
| RS-07 | eslint |
| RS-08 | build |
| RS-09 | DOWNLOAD-E2E-01..09 en Chromium, Firefox y WebKit |
| RS-10 | READ-E2E (27) |
| RS-11 | Alcance + delegación + UI-SCOPE (78) |
| RS-12 | E2E canónica con analizador (348 + las del ciclo) |
| RS-13 | Mutaciones del ciclo |
| RS-14 | OpenAPI |
| RS-15 | Seguridad: barrido de token en la E2E y en la evidencia |
| RS-16 | Accesibilidad y responsive (axe a 320 px del Centro y Exportaciones) |
| RS-17 | ruff y mypy (sin cambios de backend) |
| RS-18 | Cabeza de Alembic |
| RS-19 | Secretos y residuos (descargas de prueba, trazas, puertos, bases) |

## 13. Hallazgo durante la implementación: EXPORT-FILE-NAME-COLLISION (HIGH, corregido)

**Evidencia.** La primera corrida roja (r20261027t205236) produjo nombres repetidos entre pruebas que corrían en paralelo.

**Causa.** `create_export` nombraba el archivo `report-<clave>-<AAAAMMDDhhmmss>.<ext>` dentro de un directorio común a todos los tenants y empresas. Dos exportaciones del mismo reporte en el mismo segundo compartían archivo, y la segunda sobrescribía la primera. Una de ellas podía venir de otra empresa. Al descargar la primera se servían los datos de la segunda: una fuga entre empresas, aunque la autorización de la fila fuera correcta.

**Corrección (D-T05).** `file_ref = report-<clave>-<sello>-<uuid4 hex[:12]>.<ext>`.

**Prueba.** `test_exportaciones_del_mismo_segundo_no_comparten_archivo`:
- congela el reloj y crea dos exportaciones en el mismo segundo;
- comprueba que cada una conserva su propio contenido;
- antes de aplicar el producto, dio rojo atribuible.

Su mutante, K01, muere.

**Enmienda de diseño AD-6.** El diseño decía que el backend no cambiaba (AD-5). Esta corrección es el único cambio de backend:
- no cambia esquema, migración, OpenAPI ni autorización;
- cambia el patrón del nombre: §1.3 queda ampliado con el sufijo aleatorio;
- el nombre sigue saliendo del servidor y el cliente lo sanea igual.

**RS-17** (ruff y mypy) pasa a cubrir un cambio de backend real. Resultados: ruff limpio; mypy en 154, la línea base, sin errores nuevos.

## 14. Tareas ejecutadas

§8 era el plan inicial. La ejecución real fue D-T01..D-T12; el detalle está en `evidence/report-export-download/orchestration.md`.

- D-T05 (nombre único), D-T06 (búsqueda paginada de la fila en E2E) y D-T07 (guardas de arquitectura) nacieron de hallazgos.
- D-T09 y D-T12 son reclasificaciones tras agotar los reintentos.
- D-T10 y D-T11 cubren mutantes supervivientes.
- **Corrección de §8:** T05 apuntaba a `specs/001-fundacion/contracts/api-contracts.md`. El contrato de la descarga pertenece a la Spec dueña, y quedó en `specs/009-reportes-auditoria/contracts/api-contracts.md` (D-T08).

| Tarea | EXECUTOR | Resultado |
|---|---|---|
| D-T01..D-T12 | DEEPSEEK (13 llamadas pro, 9 flash) | 12/12 aplicadas tras auditoría; 0 implementadas por Claude |

## 15. Resultados

| Suite | Resultado | Evidencia |
|---|---|---|
| RS-01/05 vitest completo | **646/646** (56 ficheros) | corrida local |
| RS-02 backend dirigidas | verdes (incluidas en RS-03/04) | — |
| RS-03 PostgreSQL completo con analizador | **3537/0** · desvío 0,0 s · NORMAL | `qa/backend-runs/r20261027t211140p922372nba159c` |
| RS-04 SQLite completo con analizador | **2473/0** (1082 omitidas, solo PG) · 805,1 s · desvío 0,0 s · NORMAL | `qa/backend-runs/r20261027t214607p1286785n687115` |
| RS-06 tsc | 0 errores | — |
| RS-07 eslint `--max-warnings 0` | 0 | — |
| RS-08 build | correcto | — |
| RS-09 DOWNLOAD-E2E-01..09 · 3 navegadores | **27/27** | `qa/e2e-runs/r20261027t210755p905980n1a47e0` |
| RS-10/11 READ-E2E + alcance + delegación + UI-SCOPE · 3 navegadores | **105/105** (27 + 78) · limpieza LIMPIA | `qa/e2e-runs/r20261027t220003p1403833n04641c` |
| RS-12 E2E canónica con analizador | **357/357 · limpieza LIMPIA** | `qa/e2e-runs/r20261027t220209p1425549n26e022` |
| RS-13 mutaciones del ciclo | 12 · 11 muertas · 1 equivalente (U10) · **0 supervivientes** | `evidence/…/mutaciones.md` |
| RS-14 OpenAPI | deriva 0 (420 rutas) | `evidence/…/openapi.md` |
| RS-15 token en E2E y evidencia | 0 apariciones | §16 |
| RS-16 accesibilidad y responsive | axe en READ-E2E-09 (320 px); foco conservado (FOCO-01) | `evidence/…/screen-form-completeness.md` |
| RS-17 ruff / mypy | limpio / 154 (línea base) | — |
| RS-18 Alembic | cabeza `0060`, sin migración nueva | — |
| RS-19 secretos y residuos | 0 bases de corrida, 8000/5173 libres, 0 `.bak`/`.mutbak`, almacén efímero eliminado; owner material sin tocar | §16 |

**Rojo primero.** El rojo atribuible de la E2E (`evidence/…/rojo-e2e.txt`) muestra:
- Exportaciones, sin corregir: sin evento `download`;
- el Centro no entregaba el archivo.

El rojo de backend lo da la prueba de colisión de §13.

## 16. Seguridad y residuos

| Control | Resultado |
|---|---|
| JWT en ficheros del ciclo y en la evidencia de las tres corridas E2E | 0 |
| `Bearer <valor>` en ficheros del ciclo | 0 |
| `token=` en query (ficheros del ciclo y logs de la canónica) | 0 |
| Rutas personales, `KONTROL_SECRET_KEY`, contraseñas o claves privadas en la evidencia | 0 |
| Bases efímeras tras las corridas (`qa/e2e-bases.py listar`) | 0 |
| Puertos 8000/5173 | libres |
| `.bak`, `.mutbak`, `.orig`, `.rej` | 0 |
| Archivos descargados en el árbol | 0 (el almacén de exportaciones vive en el estado efímero de cada corrida, eliminado) |
| `requerimientos/KONTROL_SNAT_2026_00093.docx` | sin tocar, sin seguimiento |
| PRODUCTION_TOUCHED | 0 |

**TOKEN_IN_URL = 0 · SECRET_EXPOSURE = 0 · RESIDUE = CLEAN.**

## 17. Relectura de Gobierno (antes y después)

| Fuente | SHA-256 | Estado |
|---|---|---|
| `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` | `8f86615f…0b5378c83` | sin cambios (línea base 9a41503) |
| `requerimientos/gobierno/Biblioteca_Normativa_Oficial_KONTROL_Gobierno_v1.0.pdf` | `4a980bb9…d304ac047b` | sin cambios |

| Requisito de Gobierno | Relación con 02E |
|---|---|
| GOV-ACC-011 (exportaciones a sistemas rectores) | Sin relación directa. La primitiva de descarga autenticada es la base que reutilizará; no se implementa nada de Gobierno |
| GOV-DOC-010 (paquete de auditoría exportable) | Ídem: el contrato de nombre seguro y de error JSON queda disponible |
| GOV-CTL-007 (reportes de rendición trazables) | Sin cambio de cálculo; el archivo descargado es exactamente el auditado (`REPORT_EXPORTED`) |
| RNF-GOV-006 (autorización en backend) | Reforzado: el backend sigue siendo la autoridad; la UI solo oculta |
| RNF-GOV-012 (mínimo privilegio, alcance) | Reforzado: la capacidad de origen y la empresa se conservan; la colisión de §13 está cerrada |
| RNF-GOV-005 / RNF-GOV-009 (auditabilidad, trazabilidad) | Sin regresión: cada archivo corresponde a una sola exportación auditada |

GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 · GOVERNMENT_SPEC_STARTED = 0 · GOV0_STARTED = 0 · owner material (`KONTROL_SNAT_2026_00093.docx`) sin tocar, sin seguimiento.

## 18. Deuda (al cerrar)

| ID | Severidad | Estado |
|---|---|---|
| REPORT-EXPORT-DOWNLOAD-ANCHOR | MEDIUM | **CERRADA** (DL-01 y DL-02 corregidas; la guarda de arquitectura impide reintroducir un ancla `/api/v1/`) |
| EXPORT-FILE-NAME-COLLISION | HIGH | **CERRADA** en este ciclo (§13) |
| EXPORT-CSV-EMPTY-WITHOUT-HEADER | LOW | Abierta (§9) |
| REPORT-JOB-RESULT-NOT-DOWNLOADABLE | LOW | Abierta (§9) |
| CROSS-MODULE-SELECTOR-COMPOSITION | LOW | Abierta, no bloqueante (§10.2) |
| TABLE-HEADER-CONTRAST-AA | LOW | **PARCIAL**: corregida en el Centro; abierta en ProductoNuevoPage, LibrosPage y MfaAltaPage (§10.3) |
| OBS-TIME-01 | — | Sin investigar en 02E por orden del encargo; pasa al siguiente ciclo |
| EXPORT-CREATE-IDEMPOTENCY-CONTRACT-GAP | MEDIUM (preexistente) | **Abierta.** El contrato de Spec 009 (§3) declara `POST /reporting/exports` «Idempotente», pero la ruta no usa `Idempotency-Key` (ADR-013): cada petición crea una fila auditada nueva. 02E no cambia esa semántica: el sufijo de §13 solo impide que dos filas compartan archivo. Relacionada con RNF-GOV-007. Siguiente acción: ciclo de reportes; o se aplica ADR-013 a la creación, o se corrige el contrato, por decisión de la dueña |

## 19. Convergencia (equivalente explícito)

La skill formal resuelve la Spec por la rama (`develop`) y no por el delta: apuntaría a otra Spec. Aplico su procedimiento a este delta y tomo como intención DL-FR-01..10, AD-1..AD-6, §6, §8/§14 y la Constitución.

| Requisito | Evidencia | Hallazgo |
|---|---|---|
| DL-FR-01 | DOWNLOAD-E2E-01, EXP-04 | — |
| DL-FR-02 | DOWNLOAD-E2E-01 (nombre sugerido), DOWNLOAD-E2E-02 (bytes `%PDF`, `blob:`), ARCH-01 | — |
| DL-FR-03 | DOWNLOAD-E2E-02, ARCH-02, U05 muerto | — |
| DL-FR-04 | DESC-08, U01 muerto | — |
| DL-FR-05 | DESC-01..06, U02 muerto | — |
| DL-FR-06 | DOWNLOAD-E2E-06/07, DESC-07, DESC-09, EXP-05, CR-06/07, ARCH-03, U04/U07 muertos | — |
| DL-FR-07 | DOWNLOAD-E2E-08, EXP-06/07, FOCO-01, U09/U11 muertos, U10 equivalente | — |
| DL-FR-08 | DOWNLOAD-E2E-03/04/05/06, RPE-11/16, 105/105 de regresión | — |
| DL-FR-09 | DOWNLOAD-E2E-09, CR-05..07, U08 muerto | — |
| DL-FR-10 | Guarda de arquitectura (solo el cliente central escribe `/api/v1/`), U06 muerto | — |
| AD-6 | Prueba de colisión, K01 muerto | — |
| Constitución P6/P7/P10/P13/P21/P27 | §7, §13, §15 | — |

**Hallazgos: 0 · missing 0 · partial 0 · contradicts 0 · unrequested 0. ✅ Converged.**

En «unrequested» se revisaron dos tareas que no estaban en el plan inicial:
- **D-T05:** está justificada por §13, una corrección de seguridad dentro del alcance DL-FR-08.
- **D-T09:** está justificada por la accesibilidad del flujo, que el foco se pierda es un defecto de DL-FR-07.
