# INVESTIGACIÓN — SPEC 046

## 1. Auditoría de la capacidad actual (§139)

| Capacidad | Existe hoy | Duplicada | Riesgo | Acción |
|---|:---:|:---:|---|---|
| Subida de archivos | **No** | — | Ocho Specs bloqueadas | **Construir** |
| Descarga | Parcial | No | Solo exportaciones de `reporting`, con nombre generado por el servidor | Construir la general; no tocar la de 050 |
| Almacenamiento | Parcial | No | Volumen `/data/storage` existe y solo lo usa `reporting` | **Abstraer** |
| Metadata de archivo | **Sí** (`file_metadata`) | No | **Cero consumidores**: maestro *write-only* | **Evolucionar** a `stored_files` |
| Versionado | **No** | — | Sustituir un archivo lo perdería | **Construir** |
| Vinculación a entidad | **No** | — | Un archivo no puede pertenecer a nada | **Construir** — es la carencia central |
| Validación de MIME | **No** | — | Un ejecutable disfrazado entraría | **Construir** |
| Hash | **Sí** en el modelo | No | Columna presente, nunca calculada | **Activar** |
| Autorización de descarga | Parcial | No | `reporting` filtra por empresa; no hay modelo general | **Construir** |
| Auditoría | **Sí**, transversal | No | Ninguno | **Consumir** |
| Retención | **No** | — | Sin política | **Construir la capacidad**, no los plazos |
| Análisis de malware | **No** | — | Superficie nueva | **Diseñar**, configurable |

### El dato que resume la Spec

`file_metadata` tiene `sha256`, `storage_key`, `mime_type` y `size` — los cuatro
campos correctos — y **cero consumidores**. `python-multipart` está instalado. El
volumen existe. Todo estaba preparado y nada se conectó. Lo que falta no es
infraestructura: es **el vínculo entre un archivo y aquello de lo que es
evidencia**.

---

## 2. Alternativas de modelo (§140)

### Modelo A · Adjunto simple por entidad

Una tabla de adjuntos por dominio: `purchase_order_attachments`, etc.

**Descartado.** Es exactamente lo que P17 y R-D0-08-1 prohíben, y produce ocho
sistemas incompatibles. Además impide que un mismo packing list sirva al embarque
y a la recepción sin duplicar el binario.

### Modelo B · `Document` + `File`

Dos tablas: el documento y su archivo.

**Descartado como final.** Resuelve la separación lógico/físico pero no el
versionado: reemplazar el archivo obliga a sobrescribir la fila o a duplicar el
documento. Viola R-D0-08-5.

### Modelo C · `Document` + `DocumentVersion` + `StoredFile` + `DocumentLink`

**Adoptado.** Es el modelo del ADR. Cada pieza existe por una razón distinta:

| Entidad | Existe porque… |
|---|---|
| `Document` | El documento lógico sobrevive a sus archivos |
| `DocumentVersion` | Reemplazar no puede destruir; la aprobación de ayer apunta a la versión de ayer |
| `StoredFile` | El binario tiene su propia identidad, hash y proveedor; **y puede ser compartido** |
| `DocumentLink` | Un archivo sirve a varias entidades sin duplicarse |

### Modelo D · Servicio documental desacoplado

Microservicio independiente.

**Descartado.** KONTROL es un monolito modular desplegado por cliente (§141).
Un microservicio añadiría un despliegue, una red y un modo de fallo por una
capacidad que no lo exige. **Almacenamiento externo no es microservicio**: el
binario puede vivir fuera sin que el código lo haga.

---

## 3. Subida: por el backend o directa al almacenamiento (§91)

| | Por el backend | Directa con URL pre-firmada |
|---|---|---|
| Validación de MIME real | **Posible**: el servidor ve los bytes | Imposible antes de escribir |
| Hash en el servidor | **Directo** | Requiere paso posterior |
| Análisis de malware | Natural en el flujo | Requiere disparador asíncrono |
| Independencia de proveedor | **Total** | Solo con proveedores que firmen URL |
| Sistema de archivos local | **Funciona** | **No aplica** |
| Archivos muy grandes | Consume memoria del proceso | Mejor |
| Trazabilidad | Completa | Parcial |

**Adoptado: por el backend en el MVP.** Es la única opción compatible con el
proveedor de sistema de archivos —el que KONTROL usará en la mayoría de las
instalaciones independientes— y la única que permite validar el contenido
**antes** de aceptarlo, que es requisito de seguridad, no comodidad.

La abstracción deja la puerta abierta: un proveedor que soporte URL pre-firmada
podrá ofrecerla sin cambiar el contrato. La subida multiparte se clasifica
`FUTURE_CAPABILITY` mientras ningún NFR exija archivos que no quepan en memoria
(§92).

---

## 4. Descarga (§93)

Flujo por el backend, coherente con la subida y con `reporting`. Autorización
sobre la entidad vinculada, no sobre el conocimiento del identificador. Si en el
futuro se activa un proveedor con URL firmada, la expiración será corta, el
alcance mínimo, y **la URL no se registrará ni se persistirá** (§129, §130).

---

## 5. Vinculación: cómo evitar una clave foránea polimórfica insegura (§11)

| Modelo | Integridad | Extensible | Autorizable | Veredicto |
|---|---|---|---|---|
| **A · Polimórfica libre** (`entity_type` texto, `entity_id` suelto) | Ninguna | Sí | **No**: no se sabe cómo comprobar la propiedad | **Descartado** |
| **B · Tabla de vínculos** con los mismos dos campos | Ninguna | Sí | Igual de mal | Insuficiente |
| **C · Registro de recursos validado** | **Media-alta** | Sí | **Sí** | **Adoptado** |
| **D · Tabla de relación por dominio** | Alta | **No**: una tabla por consumidor | Sí | Descartado: no escala a 16 Specs |

**C** en detalle: existe un **registro de tipos de recurso** que declara, para
cada `resource_type` admitido, la tabla, la columna de empresa y cómo se
comprueba el permiso. `resource_type` se valida contra ese registro y no admite
texto libre. Así:

- la integridad se comprueba en el servicio, con la tabla real;
- la autorización es posible, porque se sabe **sobre qué** autorizar;
- añadir un consumidor es una entrada en el registro, no una tabla nueva.

Es menos estricto que una clave foránea real y **se admite conscientemente**:
una clave foránea por dominio exigiría 16 tablas y haría imposible un componente
único. Se compensa con validación de existencia y con prueba de que un
`resource_type` desconocido se rechaza.

> No se prioriza «menos tablas» sobre integridad (§11): se elige la única opción
> que hace **autorizable** el vínculo, que es lo que la integridad protege aquí.

---

## 6. Metadata extensible (§34)

| Alternativa | Problema |
|---|---|
| Muchas columnas opcionales en `documents` | Cien columnas nulas; cada consumidor añade la suya |
| JSON libre | Sin validación; el encargo lo prohíbe para datos críticos |
| Tabla de extensión por dominio | No escala |
| **Esquema por `DocumentType` + JSON validado** | **Adoptado** |

Los datos críticos —empresa, propietario, estado, tipo, hash, marcas de tiempo,
relaciones— son **columnas tipadas**. La metadata específica del tipo (emisor,
número de permiso, organismo) va en JSON **validado contra el esquema declarado
por el tipo**, versionable. Un JSON sin esquema no se acepta.

---

## 7. Estados: por qué dos columnas y no una (§37, §49)

El documento y su archivo tienen ciclos distintos:

- Un permiso puede estar `ACTIVE` con su PDF `PENDING_SCAN`.
- Un documento `ARCHIVED` conserva un archivo `CLEAN`.
- Un archivo `INFECTED` no invalida el documento: lo hace **no entregable**.

Una sola columna obligaría a inventar estados combinados. Dos columnas expresan
la realidad y permiten la regla simple: **no `CLEAN` no se entrega**.

`EXPIRED` no es un estado sino una lectura de `expiration_date` (§38):
persistirlo exigiría un proceso que lo mantuviera y crearía el clásico desfase
entre la fecha y la etiqueta.

---

## 8. Consistencia entre base de datos y almacenamiento (§75, §76)

El fallo temido: la base confirma y el binario no está.

**Orden adoptado:** escribir el binario → **verificar** que está y que su hash
coincide → confirmar la transacción de metadata. Si la escritura falla, la
transacción no confirma y no queda metadata huérfana. Si la confirmación falla
tras escribir, queda un binario sin metadata: basura recuperable, no evidencia
perdida — el error benigno.

Para el borrado, el orden inverso: marcar en la base, y **después** borrar el
binario mediante el trabajador común, con reintento. Nunca al revés.

Se añade una **verificación de integridad** que detecta metadata sin binario o
con hash distinto (§74): sin ella, la inconsistencia solo se descubre el día que
alguien intenta descargar.

---

## 9. Modelo de amenazas — resumen

El detalle está en `risk-register.md`. Las cinco que condicionan el diseño:

1. **Recorrido de rutas** — la `storage_key` la genera el servidor; el nombre del
   usuario nunca toca el sistema de archivos.
2. **Suplantación de MIME** — se detecta por contenido, no por extensión.
3. **Contenido activo** (SVG, HTML) — solo descarga, nunca en línea.
4. **Referencia insegura directa** — la autorización es sobre la entidad
   vinculada; conocer el identificador no basta y se responde como inexistente.
5. **Fuga entre empresas** — filtro obligatorio en las cinco operaciones.
