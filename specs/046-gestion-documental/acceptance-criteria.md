# CRITERIOS DE ACEPTACIÓN — SPEC 046

Toda ejecución sobre **PostgreSQL 18.x** y un **proveedor de almacenamiento
real**, no simulado (NFR-046-07).

## AC-046-01 · Catálogos vacíos
**Dado** una instalación nueva
**Entonces** no existe ninguna categoría ni tipo documental: KONTROL no los entrega.

## AC-046-02 · Lista blanca vacía significa ninguno
**Dado** un tipo sin `allowed_mime_types`
**Cuando** intento subir cualquier archivo
**Entonces** se rechaza con `MIME_NOT_ALLOWED`; la lista vacía **no** significa «todos».

## AC-046-03 · Documento lógico sin archivo
**Cuando** creo un documento y no subo nada
**Entonces** existe en estado `DRAFT`, sin versiones, y la biblioteca lo muestra.

## AC-046-04 · Subida válida
**Cuando** subo un PDF admitido dentro del tamaño
**Entonces** se crea la versión 1
**Y** se calcula el SHA-256 **en el servidor**
**Y** `storage_key` no contiene el nombre original, ni el de la empresa, ni el del tercero.

## AC-046-05 · El nombre del usuario nunca es ruta
**Cuando** subo `../../../etc/passwd`, `..\\win.ini`, `/etc/shadow`, `CON.pdf` o un nombre con Unicode de control
**Entonces** todos se aceptan o rechazan **sin** escribir jamás fuera del directorio del proveedor
**Y** `original_filename` conserva el texto original
**Y** la `storage_key` es un identificador generado por el servidor.

## AC-046-06 · MIME por contenido, no por extensión
**Dado** un ejecutable renombrado `factura.pdf`
**Cuando** lo subo declarando `application/pdf`
**Entonces** 422 `MIME_MISMATCH`
**Y** el archivo **no** queda almacenado.

## AC-046-07 · Doble extensión
**Cuando** subo `factura.pdf.exe`
**Entonces** se rechaza; la extensión final no engaña a la validación.

## AC-046-08 · Tamaño máximo
**Cuando** subo un archivo mayor que el máximo del tipo
**Entonces** 413 `FILE_TOO_LARGE`
**Y** el rechazo ocurre **sin** haber persistido el archivo completo.

## AC-046-09 · Hash del servidor
**Entonces** el SHA-256 almacenado coincide con el del contenido recibido
**Y** un hash enviado por el cliente se **ignora**.

## AC-046-10 · Versionado sin sobrescritura
**Dado** un documento con versión 1
**Cuando** subo una versión nueva
**Entonces** se crea la 2, la 1 queda `SUPERSEDED` y su archivo **sigue existiendo**
**Y** el hash de la 1 no cambia.

## AC-046-11 · Número de versión del servidor
**Cuando** dos usuarios crean versión **simultáneamente**
**Entonces** no existen dos versiones con el mismo número
**Y** solo una queda `ACTIVE`.

## AC-046-12 · Versión superada inmutable
**Cuando** intento editar o borrar una versión `SUPERSEDED`
**Entonces** 409 `VERSION_IMMUTABLE`.

## AC-046-13 · Subida idempotente
**Cuando** repito la misma petición con la misma `Idempotency-Key`
**Entonces** obtengo **la misma versión**, no una nueva.

## AC-046-14 · Vinculación
**Cuando** vinculo un documento a una entidad admitida
**Entonces** se crea el vínculo
**Y** consultar los documentos de esa entidad lo devuelve.

## AC-046-15 · Un archivo, varias entidades
**Cuando** vinculo el mismo documento a dos entidades
**Entonces** ambas lo ven **sin** duplicar el binario: hay un solo `stored_file`.

## AC-046-16 · Tipo de recurso desconocido
**Cuando** vinculo con `resource_type = "Cualquiera"`
**Entonces** 422 `RESOURCE_TYPE_UNKNOWN`; no hay texto libre.

## AC-046-17 · Vincular exige permiso sobre el destino
**Dado** un usuario sin permiso sobre la entidad de destino
**Cuando** intenta vincular
**Entonces** 403 `RESOURCE_ACCESS_DENIED`, aunque tenga permiso sobre el documento.

## AC-046-18 · Congelación — contrato con la Spec 045
**Dado** una solicitud de aprobación con un documento vinculado en versión 1
**Cuando** la solicitud se resuelve
**Entonces** el vínculo queda congelado en la **versión 1**
**Cuando** después se crea la versión 2
**Entonces** la aprobación **sigue apuntando a la versión 1**
**Y** el modelo de la Spec 045 **no cambió** para lograrlo.

## AC-046-19 · Vínculo congelado no se desvincula
**Cuando** intento desvincular un vínculo congelado
**Entonces** 409 `LINK_FROZEN`.

## AC-046-20 · Descarga autorizada por la entidad
**Dado** un usuario con permiso documental pero **sin** permiso sobre la entidad vinculada
**Cuando** intenta descargar
**Entonces** se deniega, aunque conozca el identificador.

## AC-046-21 · Conocer el identificador no da acceso
**Dado** un usuario de la empresa A que conoce el identificador de un documento de B
**Cuando** lo consulta o lo descarga
**Entonces** recibe **404**, no 403: no se confirma que exista.

## AC-046-22 · Aislamiento multiempresa
**Entonces** listar, consultar, descargar, vincular y versionar entre empresas es imposible
**Y** un documento de A no puede vincularse a una entidad de B.

## AC-046-23 · Sin URL pública permanente
**Cuando** examino la respuesta de descarga
**Entonces** no existe ninguna URL que funcione sin autorización
**Y** ninguna URL firmada se persiste ni aparece en los registros.

## AC-046-24 · Previsualización con la misma seguridad
**Cuando** un usuario sin permiso de descarga solicita la previsualización
**Entonces** se deniega igual: no es un permiso menor.

## AC-046-25 · Contenido activo nunca en línea
**Cuando** solicito la previsualización de un SVG o un HTML
**Entonces** se sirve como descarga, con `Content-Disposition: attachment`
**Y** nunca se muestra en el contexto autenticado.

## AC-046-26 · Ejecutables y comprimidos
**Cuando** un tipo no los declara admitidos
**Entonces** los ejecutables y los comprimidos se rechazan por defecto.

## AC-046-27 · Archivo no analizado no se entrega
**Dado** un archivo con `security_status = PENDING_SCAN`
**Cuando** intento descargarlo
**Entonces** 409 `FILE_NOT_SCANNED`
**Y** si el estado es `INFECTED`, 422 `FILE_INFECTED`.

## AC-046-28 · Sin analizador, se declara
**Dado** un despliegue sin analizador
**Entonces** `security_status` es `SKIPPED` y **viaja en la respuesta**
**Y** en ningún punto se afirma que el archivo fue analizado.

## AC-046-29 · Estado del documento y del archivo son distintos
**Entonces** un documento `ACTIVE` puede tener su archivo en `PENDING_SCAN`
**Y** archivarlo no cambia el estado de seguridad del archivo.

## AC-046-30 · `EXPIRED` es derivado
**Cuando** busco `EXPIRED` entre los estados persistidos
**Entonces** no existe: se calcula desde `expiration_date`.

## AC-046-31 · Borrado protegido
**Cuando** intento borrar un documento con vínculos o versiones
**Entonces** 409 `DOCUMENT_IN_USE`
**Y** `allowed_actions` ofrece `archive`, no `delete`
**Y** archivar es reversible y auditado.

## AC-046-32 · El binario sobrevive al archivado
**Cuando** archivo un documento
**Entonces** el binario **no** se destruye y sigue descargándose si hay permiso.

## AC-046-33 · Sin referencias colgantes
**Cuando** una versión está referenciada por un vínculo congelado
**Entonces** su archivo no puede purgarse por retención.

## AC-046-34 · Consistencia base ↔ almacenamiento
**Dado** que el almacenamiento falla al escribir
**Entonces** la transacción **no** confirma y no queda metadata sin binario
**Y** se responde 503 `STORAGE_FAILURE`.

## AC-046-35 · Metadata sin binario se detecta
**Dado** un archivo borrado del almacenamiento fuera de la aplicación
**Cuando** se ejecuta la verificación de integridad
**Entonces** se reporta
**Y** la descarga responde `STORAGE_OBJECT_MISSING`, nunca contenido incorrecto.

## AC-046-36 · Coincidencia de hash no bloquea
**Cuando** subo dos archivos con el mismo contenido
**Entonces** ambos se aceptan y la coincidencia se **registra**, no se bloquea.

## AC-046-37 · Metadata validada por esquema
**Cuando** envío metadata que no cumple el esquema del tipo
**Entonces** se rechaza
**Y** ningún dato crítico —empresa, estado, tipo, hash— vive en JSON.

## AC-046-38 · Referencia externa marcada
**Cuando** registro un documento como referencia externa
**Entonces** `is_managed` es `false`
**Y** subirle un archivo se rechaza con `EXTERNAL_DOCUMENT_NO_FILE`.

## AC-046-39 · Legado: nada se inventa
**Dado** columnas `file_ref` con texto y sin binario
**Cuando** se ejecuta la migración de marcado
**Entonces** se marcan como `UNVERIFIED_LEGACY`
**Y** **no** se crea ningún documento
**Y** el texto original se conserva intacto.

## AC-046-40 · Legado: hash sin archivo
**Dado** `homologation_records.evidence_sha256` con hash y sin binario
**Entonces** se marca `LEGACY_HASH_WITHOUT_FILE`
**Y** **no** se crea documento alguno.

## AC-046-41 · Legado: archivo faltante
**Dado** una referencia que afirma un archivo inexistente
**Entonces** se registra `MISSING_LEGACY_FILE`
**Y** la migración **no** declara éxito sobre esa fila.

## AC-046-42 · `file_metadata` evoluciona sin backfill
**Entonces** la tabla se extiende conservando sus columnas
**Y** no había filas que migrar, porque no tenía consumidores.

## AC-046-43 · Auditoría
**Entonces** quedan auditados: creación, subida, versión, actualización de metadata,
vinculación, desvinculación, archivado, intento de borrado, borrado permitido,
acceso denegado y resultado del análisis
**Y** la descarga se audita **según la política del tipo**, no siempre.

## AC-046-44 · `allowed_actions` en backend
**Cuando** un usuario sin permiso consulta un documento
**Entonces** `allowed_actions` es `[]`
**Y** invocar la operación directamente por API se rechaza igual.

## AC-046-45 · Concurrencia optimista
**Cuando** dos ediciones de metadata usan la misma versión
**Entonces** una prospera y la otra recibe 409 `VERSION_CONFLICT`.

## AC-046-46 · La lista no lee binarios
**Dado** 5.000 documentos
**Cuando** listo la biblioteca
**Entonces** no se abre ningún archivo del almacenamiento
**Y** el resultado viene paginado.

## AC-046-47 · Consulta de vencimientos
**Cuando** consulto los documentos que vencen antes de una fecha
**Entonces** se resuelve por índice, sin recorrer toda la tabla.

## AC-046-48 · Sin tipos codificados
**Cuando** busco tipos documentales o extensiones en el código
**Entonces** hay **0** coincidencias: todo procede de datos.

## AC-046-49 · Sin registrar secretos
**Cuando** reviso los registros tras una subida y una descarga
**Entonces** no aparece contenido, ni credenciales, ni URL firmadas
**Y** sí aparecen identificadores de documento, versión y archivo.

## AC-046-50 · Accesibilidad y responsive
**Entonces** las pantallas de 046 pasan axe WCAG 2.2 AA en Chromium, Firefox y WebKit,
la carga es operable **solo con teclado** sin arrastrar y soltar,
y no hay scroll horizontal entre 320 y 1920 px ni con nombres de archivo largos.
