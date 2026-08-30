# PLAN DE PRUEBAS — SPEC 046

**Motor obligatorio: PostgreSQL 18.x** y **un proveedor de almacenamiento real**
(§120, §158). La aceptación no puede basarse solo en simulaciones: un adaptador
simulado no reproduce permisos de escritura, rutas ni fallos del sistema de
archivos, que es donde vive el riesgo.

## 1. Unidad (§118)

| Grupo | Casos |
|---|---|
| Saneado de nombre | `../` · `..\` · ruta absoluta · nombre reservado · Unicode de control · CR/LF · nombre vacío · 255+ caracteres |
| Generación de `storage_key` | Opacidad · unicidad · sin rastro del nombre, empresa ni tercero |
| Validación de MIME | Declarado igual al detectado · distinto · fuera de lista · lista vacía · doble extensión |
| Tamaño | Bajo el límite · en el límite · por encima · sin límite de tipo → global |
| Hash | Determinista · igual contenido igual hash · el del cliente se ignora |
| Versionado | Primera versión · reemplazo · versión superada inmutable · número asignado por servidor |
| Estados | Transiciones válidas · `EXPIRED` derivado · estado de documento vs. de archivo |
| Autorización | Con permiso sobre la entidad · sin él · sin permiso documental · empresa ajena |
| Registro de recursos | Tipo admitido · tipo desconocido · tipo con empresa distinta |
| `allowed_actions` | Tres estados de permiso · documento archivado · vínculo congelado |
| Retención | Con política · sin política · protegido por vínculo congelado |

## 2. Integración sobre PostgreSQL + almacenamiento real (§119)

Los doce casos exigidos: subir, finalizar, versionar, descargar, vincular,
desvincular, archivar, borrado protegido, objeto ausente, fallo de
almacenamiento, acceso entre empresas y descarga no autorizada.

Añadidos por el alcance real:

- Documento **sin archivo** (lógico) de extremo a extremo.
- Documento de **referencia externa**: subida rechazada.
- Un archivo vinculado a **dos** entidades, con un solo binario.
- Subida repetida con la misma clave de idempotencia.

## 3. Matriz por adaptador de almacenamiento (§120)

| Caso | Sistema de archivos | Compatible con S3 |
|---|---|---|
| Escribir y leer | Obligatorio | Obligatorio |
| Ausencia del objeto | Obligatorio | Obligatorio |
| Fallo de escritura | Obligatorio (permisos, disco) | Simulado |
| Seguridad de rutas | **Obligatorio** — es donde importa | No aplica |
| Atomicidad | Obligatorio | Según proveedor |
| Borrado | Obligatorio | Obligatorio |

El proveedor de sistema de archivos es el que **más** debe probarse: es el que
usarán las instalaciones independientes y el único con riesgo de recorrido de
rutas.

## 4. Seguridad — suite propia, no un apartado (§126)

Un caso por cada amenaza `AMZ-01` a `AMZ-20` del registro de riesgos. Las que **deben
fallar** la operación:

| Prueba | Resultado exigido |
|---|---|
| Nombre con recorrido de rutas | Nada se escribe fuera del directorio del proveedor |
| Ejecutable renombrado a PDF | Rechazo; el archivo **no** queda almacenado |
| SVG solicitado en línea | Se sirve como descarga |
| Descarga con identificador ajeno | **404**, no 403 |
| Vinculación a entidad sin permiso | 403 |
| Desvinculación de vínculo congelado | 409 |
| `storage_key` enviada por el cliente | Ignorada |
| Descarga con análisis pendiente | 409 |
| Registros tras subida y descarga | Sin contenido, sin secretos, sin URL firmadas |

## 5. Concurrencia (§58)

| Caso | Resultado |
|---|---|
| Dos versiones simultáneas del mismo documento | Una sola `ACTIVE`; sin números duplicados |
| Archivar mientras otro descarga | Estado final coherente; sin descarga a medias |
| Dos vínculos simultáneos a la misma entidad | Un solo vínculo |
| Subida duplicada con la misma clave | Una sola versión |
| Congelación mientras se crea una versión | El vínculo congela una versión **existente**, nunca una a medio crear |

## 6. Recuperación ante fallo (§75, §76)

| Escenario | Resultado exigido |
|---|---|
| Almacenamiento cae durante la escritura | Sin confirmación; sin metadata huérfana; 503 |
| La confirmación falla tras escribir | Queda binario sin metadata: basura recuperable, **no** evidencia perdida |
| Objeto borrado fuera de la aplicación | La verificación lo detecta; la descarga responde `STORAGE_OBJECT_MISSING` |
| Fallo al borrar el binario | Reintento por el trabajador común; sin inconsistencia silenciosa |

## 7. Contrato (§121)

OpenAPI ↔ frontend ↔ consumidores: forma de la subida, versiones, errores,
`allowed_actions`, vinculación y **ausencia de `storage_key`** en toda respuesta.

## 8. Migración legada (§125)

| Caso | Comprobación |
|---|---|
| Referencia con texto y sin binario | Marcada `UNVERIFIED_LEGACY`; **0 documentos creados** |
| Hash sin binario | `LEGACY_HASH_WITHOUT_FILE`; **0 documentos** |
| Archivo declarado e inexistente | `MISSING_LEGACY_FILE` reportado |
| Nombre inseguro en el legado | No se importa; se reporta |
| `file_metadata` | Evoluciona conservando columnas; sin filas que migrar |

En los cinco casos: **el texto original permanece intacto**.

## 9. E2E (§122)

Los quince pasos exigidos, más:

- **§123 · Contrato con la Spec 045**: adjuntar a una solicitud → aprobar →
  crear V2 → comprobar que la aprobación conserva V1 **y que el modelo de 045 no
  cambió**.
- **§124 · Regulatorio**: permiso → documento → versión → vencimiento →
  consulta, **sin** implementar reglas de la Spec 044.
- Documento simple sin vínculos, que funciona igual.

## 10. Cross-browser

Chromium, Firefox y WebKit. **WebKit no se reporta como Safari.** La carga se
prueba en los tres: el control de archivo es donde más difieren.

## 11. Accesibilidad y responsive

axe WCAG 2.2 AA y 6 viewports sobre las pantallas que 046 crea. La carga debe ser
operable **solo con teclado**, sin arrastrar y soltar. Se prueba explícitamente
con **nombres de archivo largos**, que es lo que rompe la disposición.

Las 22 violaciones preexistentes de las Specs 005/054 **no** se corrigen aquí,
pero ninguna pantalla nueva puede añadir una.

## 12. Rendimiento

- Listar 5.000 documentos **sin abrir un solo binario**, paginado.
- Consulta de vencimientos resuelta por índice, verificada con `EXPLAIN`.
- Documentos de una entidad: por índice, sin recorrido completo.

## 13. Criterio de salida

- Suite completa verde sobre PostgreSQL 18.x **y almacenamiento real**.
- Los 50 criterios de aceptación cubiertos.
- Las 20 amenazas con prueba que las ejerce.
- La migración legada **sin crear un solo documento**.
- 0 tipos documentales ni extensiones codificados.
- 0 respuestas que expongan `storage_key`.
- Un solo mecanismo de archivos en todo el sistema.
