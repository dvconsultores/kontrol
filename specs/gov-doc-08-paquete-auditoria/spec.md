# Spec · GOV-DOC-08 Paquete de auditoría exportable (DOC-08, GOV-DOC-010)

## 1. Lo que podrá hacer Control Interno / control fiscal externo (vista del sponsor)

Cuando este ciclo termine, Control Interno podrá:
- abrir una muestra de auditoría ya registrada y pedir su paquete de auditoría;
- ver antes de generar qué entra: eventos, documentos que se incluirán, documentos que quedan fuera y por qué, hallazgos y tamaño estimado;
- generar el paquete con un propósito declarado y obtener un código, una fecha y una huella del paquete;
- descargarlo con su índice, su manifiesto, los metadatos seguros de cada evento, la copia de cada documento autorizado y los hallazgos originados en la muestra;
- consultar el historial de paquetes generados;
- verificar más tarde cualquier copia del paquete y saber si está íntegra, alterada, incompleta o en una versión no soportada.

El auditor externo podrá comprobar la integridad del paquete fuera del sistema, con herramientas corrientes.

## 2. Fuentes y decisiones

- **Requisito:** GOV-DOC-010, «Generar paquete de auditoría exportable con índice, hashes/metadatos y referencias cruzadas», P1. Fuentes N18, N21 y N22.
- **Normativa:**
  - N18 (LOCGR, control fiscal): auditabilidad del control interno y externo.
  - N21 (rendición de cuentas): integridad de soportes y evidencia reproducible.
  - N22 (Normas Generales de Auditoría de Estado): evidencia, trazabilidad y papeles de trabajo.
  - Ninguna fija formato, algoritmo ni estructura del paquete. KONTROL no declara cumplimiento de una forma legal concreta: el paquete es un **papel de trabajo exportable con integridad verificable**. LEGAL_VALIDATION_REQUIRED = 0, porque no se hace ninguna afirmación jurídica.
- **Hash ≠ firma electrónica.** El paquete no lleva firma; DOC-05 sigue separado. La UI y el manifiesto lo dicen expresamente.
- **Decisiones de la dueña (2026-11-04):**
  - **OD-DOC08-01:** el ZIP lleva la copia exacta de cada documento autorizado y limpio, en la versión que corresponda (§4.4), con su sha256.
  - **OD-DOC08-02:** el alcance es la muestra de CTL-04 (eventos, objeto, documentos) más los hallazgos de CTL-06 originados en ella, con recomendaciones, acciones, responsable y evidencia.
  - **OD-DOC08-03:** un documento sin permiso o no disponible no impide generar. El manifiesto lo declara EXCLUIDO con su motivo, sin título ni contenido, y la vista previa lo avisa.
  - **OD-DOC08-04:** nueva capacidad `gobierno_paquetes`:
    - `view`: listar, ver detalle, descargar y verificar;
    - `generate`: generar, SENSITIVE con MFA;
    - la concede FUNCIONAL_COMPLETO;
    - leer los documentos sigue exigiendo su propio permiso.

### Prueba de bloqueo material

| Pregunta | Respuesta |
|---|---|
| ¿Requiere el expediente de DOC-01? | No. La IR pide un paquete de auditoría en general (GOV-DOC-010), no el de un expediente (GOV-DOC-001) ni el expediente de cuenta (GOV-CTL-006). No se inventa ningún expediente. |
| ¿Puede producirse desde una muestra de CTL-04 con sus eventos, objetos y documentos? | Sí. Las muestras y los eventos son inmutables, y las versiones documentales tienen sha256 y análisis. |
| ¿Faltan tipos de evidencia? | No. Hay eventos, documentos vinculados y hallazgos con su evidencia. |
| ¿Requiere firma electrónica (DOC-05)? | No. Hash ≠ firma. |
| ¿Requiere un régimen de retención (DOC-06)? | No. El paquete y su registro son permanentes, sin borrado. |
| ¿Requiere identidad de control fiscal no modelada? | No. Actúa un usuario con la capacidad, y su nombre de usuario queda en el manifiesto. |

**Bloqueos:** SECURITY, DATA_INTEGRITY, LEGAL, NORMATIVE, ARCHITECTURAL, TESTABILITY y DOMAIN_DEPENDENCY, todos en 0. **MATERIAL_BLOCKER = 0.**

## 3. Modelo del proceso

```
MUESTRA CTL-04 (inmutable)
  → VISTA PREVIA (alcance, incluidos, excluidos con motivo, límites)
  → GENERAR (propósito; síncrono y acotado)
  → PAQUETE REGISTRADO (código, huellas, manifiesto)
  → DESCARGAR (paquete o manifiesto)
  → VERIFICAR (cualquier copia: VÁLIDO / INVÁLIDO / INCOMPLETO / VERSIÓN NO SOPORTADA)
```

- El paquete no tiene estados. La generación es síncrona y acotada (§4.8): o se registra completo o no se registra. No hay cola ni trabajos (PDD-DOC08-03).
- Una muestra puede tener varios paquetes, uno por generación, numerados 1, 2, … Cada uno es una instantánea de su momento.
- **Idempotencia** con la cabecera opcional `Idempotency-Key`:
  - la misma clave en la misma empresa devuelve el mismo paquete;
  - la misma clave con otra muestra da 409 `GOV_PACKAGE_IDEMPOTENCY_CONFLICT`.

## 4. Contratos

### 4.1 Origen (PACKAGE_SOURCE)

- Una muestra de CTL-04 de la empresa activa produce un paquete.
- El paquete referencia la definición exacta de la muestra, sin recomputarla: código, título, criterio, justificación, método, semilla, filtros, población, tamaño, partidas en su orden, creada_por y creada_en.
- No se modifica la muestra ni sus partidas. Siguen protegidas por los disparadores de CTL-04.
- Una muestra de otra empresa o de otro tenant responde 404 `GOV_AUDIT_SAMPLE_NOT_FOUND`, igual que en CTL-04.

### 4.2 Contenido del ZIP (PACKAGE_FORMAT)

Las rutas son fijas y ASCII. No se usan nombres de usuario ni nombres originales en las rutas.

| Ruta | Contenido | Compresión |
|---|---|---|
| `manifest.json` | manifiesto (§4.3) | DEFLATED |
| `SHA256SUMS` | una línea `<sha256>  <ruta>` por fichero, incluido `manifest.json` y excluido el propio `SHA256SUMS`; formato de `sha256sum -c` | DEFLATED |
| `INDICE.csv` | índice legible: `ruta;tipo;referencia;descripcion;bytes;sha256`, en UTF-8 con BOM y separador `;` | DEFLATED |
| `LEEME.txt` | qué es el paquete; que el hash no es firma; cómo verificarlo en KONTROL y con `sha256sum -c SHA256SUMS` | DEFLATED |
| `muestra/muestra.json` | definición de la muestra (§4.1) | DEFLATED |
| `eventos/NNNN-<evento_id>.json` | por partida, con NNNN = orden en 4 cifras: resumen del evento y detalle **seguro** (`safe_details`, el mismo de CTL-04), objeto de negocio `{tipo, id}` e ids de documentos referenciados | DEFLATED |
| `documentos/<documento_id>-v<versión>[.<ext>]` | copia exacta de cada documento INCLUIDO; extensión por `safe_extension` | **STORED** (sin comprimir) |
| `hallazgos/<codigo>.json` | por hallazgo originado en la muestra: atributos, partidas, recomendaciones, acciones con su instantánea de cargo, avances con su documento e historia | DEFLATED |

- Sin contenido ejecutable: no hay HTML, scripts ni rutas absolutas, `..` o directorios fuera de la lista.
- Cada entrada lleva la fecha de generación y permisos 0644. El orden de las entradas es fijo (la tabla, y dentro de cada carpeta por nombre).
- El ZIP generado se guarda en el **almacenamiento canónico** de la Spec 046 (`get_storage().put`, clave `generate_storage_key(empresa)`). No hay un segundo subsistema de ficheros (AD-DOC08-02).

### 4.3 Manifiesto (MANIFEST)

JSON canónico (`sort_keys`, separadores `(",", ":")`, UTF-8 sin escape ASCII), con estas claves:

| Clave | Contenido |
|---|---|
| `formato` | `"kontrol-gobierno-paquete-auditoria"` |
| `version_manifiesto` | `1` |
| `paquete` | `codigo`, `numero_generacion`, `titulo`, `proposito`, `generado_en` (ISO 8601 UTC), `generado_por` (nombre de usuario), `algoritmo_hash` = `"SHA-256"`, `aviso` = `"La huella SHA-256 prueba integridad; no es una firma electrónica."` |
| `ente` | `empresa_id` y `denominacion` (ORG-01 si existe; si no, `null`) |
| `muestra` | §4.1, más `archivo` = `"muestra/muestra.json"` |
| `eventos[]` | `orden`, `id`, `fecha`, `proceso`, `accion`, `entidad`, `entidad_id`, `usuario`, `archivo`, `objeto` (`{tipo, id}` o `null`), `documentos` (ids) |
| `documentos[]` | ordenados por id. INCLUIDO: `id`, `estado` = `"INCLUIDO"`, `version_id`, `version`, `archivo`, `nombre_original` (saneado), `tipo_mime`, `bytes`, `sha256`, `referencias`. EXCLUIDO: solo `id`, `estado` = `"EXCLUIDO"`, `motivo` (`SIN_PERMISO` o `NO_DISPONIBLE`) y `referencias` |
| `hallazgos[]` | `id`, `codigo`, `titulo`, `riesgo`, `estado`, `archivo`, `partidas` (ids de evento), `acciones` (ids), `documentos` (ids) |
| `archivos[]` | todos los ficheros menos `manifest.json` y `SHA256SUMS`: `ruta`, `bytes`, `sha256`, ordenados por ruta |
| `totales` | `eventos`, `documentos_incluidos`, `documentos_excluidos`, `hallazgos`, `archivos`, `bytes` (suma de `archivos[]`) |

- Las referencias de un documento son `{"tipo": "evento" | "objeto" | "accion_correctiva" | "avance", "id": …}`.
- No contiene secretos, contraseñas, IP, `user_agent` ni valores fuera de `safe_details`.

### 4.4 Inclusión de documentos (DOCUMENT_INCLUSION)

**Candidatos, sin repetir:**
- los ids que el detalle seguro de cada evento referencia (la misma función de CTL-04);
- los documentos vinculados (`DocumentLink`) al objeto de negocio de cada evento, cuando `_objeto_desde_evento` lo resuelve en la empresa;
- los vinculados a las acciones correctivas de los hallazgos;
- el `document_id` de cada avance.

**Versión:**
- si el vínculo está congelado, `frozen_version_id`;
- si no, `current_version_id` en el momento de generar.

Un documento solo se INCLUYE si se cumplen **todas** estas condiciones:
1. es de la empresa activa;
2. el usuario que genera tiene `documentos:download` en la empresa;
3. el usuario puede leer el archivo según la regla de la Spec 046 (`_assert_can_read_file`: puede ver alguna entidad vinculada o el documento no tiene vínculos);
4. la versión es entregable (`assert_deliverable`): existe, su hash coincide y está limpia.

**Exclusión:**
- si falla la condición 1 o la 4, queda EXCLUIDO con motivo `NO_DISPONIBLE` (no se confirma su existencia);
- si falla la 2 o la 3, queda EXCLUIDO con motivo `SIN_PERMISO`;
- en ningún caso se incluye un documento solo porque un evento cite su id.

### 4.5 Referencias cruzadas (CROSS_REFERENCE)

- Cada partida enlaza `evento.id` → `objeto{tipo,id}` → `documentos[]`.
- Cada documento enlaza `referencias[]`.
- Cada hallazgo enlaza `partidas[]` (eventos de la muestra), `acciones[]` y `documentos[]`. Cada acción conserva su instantánea de cargo (código, denominación, unidad, ejercicio).
- Las identidades son ids y códigos estables, nunca URL de la interfaz.

### 4.6 Huellas (HASH)

- **Algoritmo:** SHA-256 sobre los bytes exactos, en hexadecimal minúsculas. Biblioteca estándar `hashlib`, sin dependencias nuevas.
- **Por fichero:** cada fichero de `archivos[]` lleva su sha256. El de un documento coincide con el `sha256` de su versión en la Spec 046; si no coincide, el documento queda NO_DISPONIBLE.
- **Manifiesto:** `huella_manifiesto` = sha256 de los bytes de `manifest.json`. Se registra en KONTROL.
- **Paquete:** `huella_paquete` = sha256 de los bytes del ZIP. Se registra, se muestra y viaja en la auditoría.
- **Ancla de confianza:** las huellas registradas en KONTROL. `SHA256SUMS` sirve para la comprobación local, pero no prueba nada por sí solo.

### 4.7 Verificación (VERIFY)

Se sube una copia del ZIP (`multipart`, campo `archivo`). El servidor la abre **de forma segura**; incumplir una sola condición responde 422 `GOV_PACKAGE_UPLOAD_INVALID` con su motivo:
- tamaño de subida ≤ 300 MiB;
- es un ZIP legible;
- ≤ 1 000 entradas;
- sin rutas absolutas, `..`, barras invertidas ni nombres duplicados;
- tamaño descomprimido declarado ≤ 300 MiB;
- cada entrada con una razón de compresión ≤ 200.

Después determina el resultado, con esta precedencia:

| Resultado | Cuándo |
|---|---|
| `VERSION_NO_SOPORTADA` | `manifest.json` existe y su `formato` o su `version_manifiesto` no son los de §4.3 |
| `INVALIDO` | cualquiera de: `manifest.json` ausente o ilegible; código del paquete no registrado en la empresa (`PAQUETE_NO_REGISTRADO`, sin revelar otras empresas); sha256 de `manifest.json` distinto del registrado (`MANIFIESTO_ALTERADO`); fichero listado con sha256, tamaño o CRC distinto (`ARCHIVO_ALTERADO`); fichero no listado distinto de `manifest.json` y `SHA256SUMS` (`ARCHIVO_INESPERADO`) |
| `INCOMPLETO` | falta algún fichero listado en `archivos[]` (`ARCHIVO_AUSENTE`) |
| `VALIDO` | ninguno de los anteriores |

- La respuesta incluye `resultado`, `motivos[]` (`{codigo, ruta?}`), `paquete` (código e id si está registrado), `huella_archivo` e `identico` (si la huella del ZIP subido coincide con la registrada).
- Cada verificación de un paquete registrado se guarda en su historia (inmutable) y se audita. Las de un paquete no registrado solo se auditan.

### 4.8 Límites

- Eventos ≤ 500 (el máximo de la muestra de CTL-04), documentos incluidos ≤ 200 y bytes de documentos incluidos ≤ 250 MiB.
- Si se supera alguno, la vista previa lo marca (`excede_limite` y `motivo_limite`) y la generación responde 422 `GOV_PACKAGE_TOO_LARGE`.

### 4.9 Descarga

- **Paquete** (`…/descargar`) y **manifiesto** (`…/manifiesto`, leído del ZIP almacenado). Exigen `gobierno_paquetes:view`, empresa, `documentos:download` y poder leer **cada** documento INCLUIDO en ese momento (regla de §4.4.3). Si falla alguno, 403 `GOV_PACKAGE_DOCUMENTS_FORBIDDEN`. El paquete no salta el control documental.
- Antes de entregar se comprueba `storage.verify(clave, huella_paquete)`. Si no coincide, 500 `STORAGE_HASH_MISMATCH`, el contrato de la Spec 046 para corrupción del almacenamiento.
- Cabeceras de la Spec 046: `attachment`, `no-store`, `nosniff` y CSP `sandbox`.
- Nombres de fichero: `paquete-<codigo>.zip` y `manifiesto-<codigo>.json`.

## 5. Campos (FIELD_CONTRACT)

| ID | Etiqueta | Significado | Tipo / BD / API | Req. | Validación | Visibilidad | Auditoría | Efecto en export | Error | Ayuda |
|---|---|---|---|---|---|---|---|---|---|---|
| P01 | Código | identificador del paquete en el ente | str · String(20) · str | sistema | `PA-AAAA-NNNN`, único por empresa | view | sí | `paquete.codigo` | 409 GOV_PACKAGE_CONFLICT | — |
| P02 | Muestra | muestra de origen | uuid · FK gov_audit_samples · str | sí | de la empresa | view | sí | `muestra` | 404 | «Muestra de auditoría de origen» |
| P03 | Generación n.º | orden de generación para la muestra | int · Integer · int | sistema | ≥1, único (muestra, n.º) | view | sí | `paquete.numero_generacion` | 409 | — |
| P04 | Título | título del paquete | str · String(200) · str | sistema | «Paquete de auditoría · <título de la muestra>» (truncado a 200) | view | no | `paquete.titulo` | — | — |
| P05 | Propósito | para qué se exporta | str · Text · str | **sí** | 10–1000 caracteres, sin espacios a los extremos | view | sí | `paquete.proposito` | 422 VALIDATION_ERROR | «Indique para qué y para quién se genera el paquete» |
| P06 | Generado por / en | autor e instante | uuid + datetime | sistema | — | view | sí | `paquete.generado_*` | — | — |
| P07 | Huella del paquete | sha256 del ZIP | str · String(64) · str | sistema | hexadecimal de 64 | view | sí | — | — | «Compárela con la de cualquier copia» |
| P08 | Huella del manifiesto | sha256 de manifest.json | str · String(64) · str | sistema | hexadecimal de 64 | view | sí | — | — | — |
| P09 | Tamaño | bytes del ZIP | int · BigInteger · int | sistema | >0 | view | sí | — | — | — |
| P10 | Contenido | eventos / incluidos / excluidos / hallazgos / archivos | int ×5 | sistema | ≥0 | view | sí | `totales` | — | — |
| P11 | Manifiesto | copia del manifiesto (sin nombres en la API) | JSON · JSON · objeto | sistema | §4.3 | view | no | — | — | — |
| V01 | Archivo a verificar | copia del ZIP | fichero · — · multipart | sí | §4.7 | view | sí | — | 422 GOV_PACKAGE_UPLOAD_INVALID | «Suba el ZIP descargado» |
| V02 | Resultado | VALIDO / INVALIDO / INCOMPLETO / VERSION_NO_SOPORTADA | enum · String(20) · str | sistema | §4.7 | view | sí | — | — | — |
| V03 | Motivos | lista de códigos y rutas | JSON · JSON · lista | sistema | — | view | sí | — | — | — |
| V04 | Huella del archivo / idéntico | sha256 subido y si coincide byte a byte | str + bool | sistema | — | view | sí | — | — | — |

- **Campos de solo lectura de la vista previa:** muestra (código, título, método, semilla, población, tamaño); totales; lista de documentos con estado y motivo, sin títulos; hallazgos; bytes estimados y límites.
- MISSING_REQUIRED_FIELDS = 0.

## 6. Datos (migración `0071_gov_doc08_paquetes`)

**`gov_audit_packages`** (empresa; inmutable)
- **Columnas:** `id`, `tenant_id`, `company_id`, `codigo`, `sample_id`, `numero_generacion`, `titulo`, `proposito`, `version_manifiesto`, `huella_manifiesto`, `huella_paquete`, `bytes`, `clave_almacenamiento`, `nombre_archivo`, `eventos`, `documentos_incluidos`, `documentos_excluidos`, `hallazgos`, `archivos`, `manifiesto` (JSON), `idempotency_key` (nullable), `created_by`, `created_at`, `updated_at`.
- **Únicos:** (company_id, codigo), (sample_id, numero_generacion), (company_id, idempotency_key) y clave_almacenamiento.
- **CHECK:** las huellas tienen 64 caracteres; `bytes` > 0; los contadores ≥ 0; `version_manifiesto` = 1.
- **PostgreSQL:** disparadores que rechazan UPDATE, DELETE y TRUNCATE.

**`gov_audit_package_verifications`** (empresa; inmutable)
- **Columnas:** `id`, `company_id`, `package_id` (FK), `resultado`, `motivos` (JSON), `huella_archivo`, `bytes_archivo`, `identico`, `created_by`, `created_at`, `updated_at`.
- **CHECK:** `resultado` IN (VALIDO, INVALIDO, INCOMPLETO, VERSION_NO_SOPORTADA).
- **PostgreSQL:** disparadores que rechazan UPDATE, DELETE y TRUNCATE.

**Permisos** `gobierno_paquetes:view` y `gobierno_paquetes:generate`, concedidos a FUNCIONAL_COMPLETO, como en 0070.

No se duplica el contenido de los documentos en la base: el ZIP vive en el almacenamiento canónico.

## 7. API (`/api/v1/gobierno`; guardas: permiso → empresa → módulo `gobierno`)

| # | Método y ruta | Permiso | Respuesta | Errores |
|---|---|---|---|---|
| 1 | GET `/auditoria/muestras/{id}/paquete/vista-previa` | paquetes:view | VistaPrevia | 404 |
| 2 | POST `/auditoria/muestras/{id}/paquetes` (`{proposito}`, cabecera opcional `Idempotency-Key`) | paquetes:generate + escritura de licencia | 201 PaqueteDetalle (200 si es repetición idempotente) | 404, 409 GOV_PACKAGE_CONFLICT / GOV_PACKAGE_IDEMPOTENCY_CONFLICT, 422 VALIDATION_ERROR / GOV_PACKAGE_TOO_LARGE |
| 3 | GET `/paquetes` (`muestra_id?`, `pagina`, `por_pagina` de 10 a 100) | paquetes:view | PaquetesListado | 422 |
| 4 | GET `/paquetes/{id}` | paquetes:view | PaqueteDetalle (resumen del manifiesto sin nombres de documento + verificaciones) | 404 GOV_PACKAGE_NOT_FOUND |
| 5 | GET `/paquetes/{id}/descargar` | paquetes:view (+ §4.9) | application/zip | 403 GOV_PACKAGE_DOCUMENTS_FORBIDDEN, 404, 500 STORAGE_HASH_MISMATCH |
| 6 | GET `/paquetes/{id}/manifiesto` | paquetes:view (+ §4.9) | application/json | ídem |
| 7 | POST `/paquetes/verificar` (multipart `archivo`) | paquetes:view + escritura de licencia | ResultadoVerificacion | 422 GOV_PACKAGE_UPLOAD_INVALID |

- No hay parámetros no declarados.
- Ningún error de negocio esperado responde 500. La única excepción es la corrupción del almacenamiento (§4.9).

## 8. Roles, MFA y auditoría

- **Permisos:** `gobierno_paquetes:view` es STANDARD y `gobierno_paquetes:generate` es SENSITIVE (MFA). Generar no da permiso para ver un documento (§4.4, §4.9).
- **Catálogo** (`owner_spec` `gov-doc-08`, entidad `GovernmentAuditPackage`, alcance COMPANY, clase SECURITY):

| Acción | Campos seguros |
|---|---|
| `GOV_AUDIT_PACKAGE_GENERATED` | `codigo`, `muestra_codigo`, `huella_paquete`, `huella_manifiesto`, `tamano_bytes`, `eventos`, `documentos_incluidos`, `documentos_excluidos`, `hallazgos` |
| `GOV_AUDIT_PACKAGE_DOWNLOADED` | `codigo`, `archivo` (`paquete` o `manifiesto`) |
| `GOV_AUDIT_PACKAGE_VERIFIED` | `codigo`, `resultado`, `huella_archivo`, `identico` (resultado VALIDO) |
| `GOV_AUDIT_PACKAGE_VERIFICATION_FAILED` | `codigo` o `null`, `resultado`, `motivos`, `huella_archivo` (resto de resultados) |

- Nunca se audita el contenido del paquete.
- La auditoría institucional de CTL-04 incorpora el proceso «DOC-08 · Paquetes de auditoría» y el rastreo de `GovernmentAuditPackage` → `/gobierno/paquetes/{id}`, con `gobierno_paquetes:view`.

## 9. Menú, pantallas y estados

- **S1 · Generar paquete** (`/gobierno/auditoria/muestras/:muestraId/paquete`):
  - **Entrada:** botón «Generar paquete de auditoría» en la ficha de la muestra (CTL-04), visible con `generate`.
  - **Contenido:** datos de la muestra; tarjetas de eventos, documentos incluidos, documentos excluidos y hallazgos; tabla de documentos con estado y motivo; tamaño estimado y aviso de límite; campo Propósito; aviso «la huella prueba integridad; no es una firma electrónica».
  - **Acción:** «Generar paquete», que lleva a S3.
- **S2 · Paquetes de auditoría** (`/gobierno/paquetes`, menú Gobierno › Paquetes de auditoría, `view`):
  - **Listado:** código, muestra, generado por/en, tamaño, huella abreviada y contenido; paginación.
  - **Panel «Verificar un paquete»:** subir el ZIP y pulsar «Verificar». El resultado sale con su estado, sus motivos y un enlace al paquete.
  - En la ficha de la muestra hay además la sección «Paquetes de esta muestra».
- **S3 · Paquete** (`/gobierno/paquetes/:paqueteId`):
  - **Datos:** código, muestra (enlace), propósito, generado por/en, huellas completas, tamaño y totales.
  - **Contenido:** pestañas o secciones de eventos, documentos (estado y motivo, sin títulos) y hallazgos.
  - **Acciones:** «Descargar paquete» y «Descargar manifiesto».
  - **Historial de verificaciones.**
- **Estados:** cargando, sin acceso, módulo no habilitado, vacío, error con reintento, no encontrado, límite superado, descarga prohibida por documentos y archivo de verificación rechazado.
- **Accesibilidad:** encabezados por pantalla; tablas con caption; etiquetas «(obligatorio)»; resultados con `role=status` y `role=alert`; región con nombre; foco tras generar.
- **Responsive:** sin desbordamiento a 320 px; huellas con `break-all`.

## 10. Escenario de éxito para la prueba de la dueña

1. Inicia sesión y entra en Gobierno › Auditoría institucional. Abre una muestra con evidencia documental y un hallazgo originado en ella.
2. Pulsa «Generar paquete de auditoría». La vista previa muestra N eventos, documentos incluidos y excluidos con motivo, y 1 hallazgo.
3. Escribe el propósito y genera. Ve el código PA-AAAA-NNNN, la huella del paquete y el contenido.
4. Descarga el paquete y el manifiesto. Abre `INDICE.csv` y `LEEME.txt`.
5. En Gobierno › Paquetes de auditoría verifica la copia descargada: **VÁLIDO, idéntico**.
6. Verifica una copia alterada: **INVÁLIDO, archivo alterado**.
7. **Negativas:**
   - un usuario solo con `view` no ve «Generar»;
   - un usuario sin `documentos:download` ve los documentos EXCLUIDOS (SIN_PERMISO) y no puede descargar un paquete que los incluya;
   - otra empresa recibe «Paquete no encontrado».
8. Sistema › Auditoría registra la generación, la descarga y las verificaciones.

OWNER_UAT_SCENARIO_DEFINED = 1.
