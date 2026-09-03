# SPEC 020 — INCIDENCIAS DE RECEPCIÓN · INFORME DE IMPLEMENTACIÓN

| Campo | Valor |
|---|---|
| Ciclo | `SPEC 020 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-03) |
| Base | `409b945` |
| Migración | `0045_spec020_incidents` (revisa `0044_spec019_receipt`) |
| Estado de partida | cero: ninguna tabla, ruta, servicio ni pantalla |

## 1. Lo que decía el contrato y lo que no

La Spec 020 son tres etapas del proceso, no un módulo entero: **registrar** la diferencia (etapa 8),
**generar su evidencia** (9) y **escalarla a Compras** (10). Los cinco tipos son los cinco
subelementos literales de la etapa 8. Los cuatro tratamientos son los cuatro del §3.

Lo más útil de la auditoría fue descartar. El checkpoint sugería revisar trece candidatos a tipo de
incidencia; **ocho no lo son**:

| Candidato | Qué es en realidad |
|---|---|
| empaque, presentación, lote, serial, vencimiento | datos que la Spec 019 captura en la recepción |
| calidad | el veredicto `quality_status` de la etapa 7 |
| rechazo, cuarentena | **tratamientos**, no tipos |

Implementarlos como tipos habría sido inventarlos, y habría creado un segundo lugar donde vive lo
que ya vive en la línea de recepción.

## 2. Dónde vive cada cosa

El DOCX enumera los tratamientos dentro del §3, que es el proceso de la Spec 021, y la matriz de
procesos asigna «Tratamiento» a 021 y 025. Este ciclo separa las dos cosas de forma explícita:

- **020 registra la decisión.** Es donde se escala y donde se responde.
- **021 la ejecuta** contra el inventario, cuando la Spec 023 aprenda a escribir estados de
  mercancía no vendibles. Ese bloqueo no se toca ni se rodea.

Registrar no es ejecutar. Una prueba lo mide: resolver una incidencia no crea movimientos, no cambia
saldos y no escribe ningún estado de mercancía.

## 3. Lo que se construyó

| Área | Cambio |
|---|---|
| Modelo | `ReceiptIncident`: recepción, línea opcional, tipo, cantidad base afectada, descripción, ciclo de vida, escalamiento, tratamiento con motivo y solicitud de aprobación |
| Restricciones | seis en la base: tipo, estado y tratamiento del catálogo; cantidad positiva; **línea y cantidad según el tipo**; y resuelta obliga a tener tratamiento |
| Servicio | registrar, escalar, resolver, anular y el contrato de salida para la 021 |
| Aprobaciones | `RECEIPT_INCIDENT` como constante de integración; el ajuste autorizado abre solicitud y no se resuelve sin ella |
| Documentos | `ReceiptIncident` en el registro cerrado de la Spec 046; sin almacenamiento paralelo |
| API | 7 rutas: bandeja de empresa, listado y resultado por recepción, alta, detalle, escalar, resolver y anular |
| Frontend | pantalla propia con ruta y menú: registrar según el tipo, escalar, tratar con motivo y anular |
| Migración | `0045`, solo la tabla nueva; **cero incidencias retroactivas** |

## 4. Las tres decisiones de diseño que merecen explicación

**La línea y la cantidad dependen del tipo, y lo impone la base.** Una diferencia documental es del
documento: no lleva línea ni cantidad. Las otras cuatro son de mercancía y exigen ambas. Podría
haberse dejado como regla de servicio; está en una restricción porque una fila a medio camino no
tiene lectura posible, y las filas sobreviven al código que las escribió.

**El tope de cantidad no es el mismo para todos los tipos.** Un faltante habla de mercancía que
**no** llegó, así que su techo es lo que se pidió; los otros tres hablan de mercancía que sí llegó,
y su techo es lo recibido. Tratarlos igual habría impedido registrar un faltante grande —recibir 5
de 100 y faltar 95— o habría permitido dañar más de lo que bajó del camión.

**La acumulación se comprueba por línea y por tipo, con la línea bloqueada.** Dos incidencias de daño
sobre la misma línea no pueden sumar más de lo recibido; dos de tipos distintos sí, porque son
dimensiones independientes. Anular libera lo que comprometía.

## 5. Lo que deliberadamente no se hizo

- **No se añadió severidad, prioridad ni asignación.** No están en el contrato.
- **No se creó un segundo veredicto de conformidad.** `quality_status` sigue siendo el único.
- **No se copió el hecho físico.** La incidencia no tiene producto, unidad, presentación, factor,
  estado físico, lote ni vencimiento: apunta a la línea, que ya los tiene. Un guardia estructural
  falla si alguien añade alguno.
- **No se crearon motores locales** de aprobación, documentos ni inventario.
- **No se fabricó historia.** Había líneas con cantidad rechazada; convertirlas en incidencias
  habría inventado un tipo, un responsable y un tratamiento que nadie registró.

## 6. Dos defectos que solo la prueba de extremo a extremo podía encontrar

Ninguno de los dos aparecía en pytest ni en vitest, y los dos eran reales.

### 6.1 La tabla que crea la migración no admitía un solo insert

`receipt_incidents` se creó en `0045` con `created_at` y `updated_at` declarados `NOT NULL` **y sin
`server_default`**. `TimestampMixin` no pone valor desde Python: lo pone la base. La consecuencia es
que la tabla creada por la migración —es decir, la de cualquier instalación real— rechazaba todo
insert de la aplicación con `NotNullViolation`.

Por qué no lo vio nadie:

| Suite | Cómo construye la tabla | Qué escribe | Resultado |
|---|---|---|---|
| Funcional (24 casos) | `create_all` desde el ORM | por el ORM | el default sí existe → pasa |
| Migración (8 casos) | Alembic, la tabla real | SQL crudo con `now(), now()` | nunca ejerce el default → pasa |
| Frontend real → API real | Alembic, la tabla real | por el ORM | **falla** |

Las dos mitades del problema estaban cada una en una suite y no se tocaban. Se corrigió la
migración —las demás migraciones del repositorio ya lo hacían bien; esta era la excepción— y se
añadió el caso que faltaba: un insert del ORM contra la tabla que produce Alembic. Verificado por
los dos lados: con la migración sin default falla con `NotNullViolation` sobre `created_at`; con
ella, pasa.

### 6.2 Quince selectores anunciaban a los lectores de pantalla un nombre distinto del visible

`FormField` ya asocia su etiqueta con el campo mediante `htmlFor`. Los `<select>` llevaban además un
`aria-label` propio que **la pisa**. En once de los quince el texto no coincidía: la etiqueta visible
decía «Línea recibida» y el nombre accesible era «Línea de la recepción»; «Producto» frente a
«Producto de la línea»; «Almacén» frente a «Almacén de la reserva». Quien navega por voz dice lo que
lee, y lo que leía no existía. Es un incumplimiento de *Label in Name* (WCAG 2.5.3).

El defecto no era de esta Spec sola: estaba en cinco páginas —incidencias, recepciones, reservas,
pedidos de venta— sembrado por los tres ciclos de este bloque. Se quitó el `aria-label` redundante
de los quince; el nombre accesible pasa a ser el visible.

**Lo que esto dice de las pruebas:** una aserción de la propia e2e comprobaba que cierta etiqueta
*no* estaba presente, y pasaba porque esa etiqueta nunca existió con ese nombre. Pasaba por la razón
equivocada. Corregido el localizador, la aserción comprueba lo que decía comprobar.

## 7. Una consecuencia aceptada, en la frontera con la Spec 045

Si una incidencia queda en `PENDIENTE_AUTORIZACION` esperando el ajuste y luego se resuelve con otro
tratamiento —reclamo al proveedor, por ejemplo—, la solicitud de aprobación que se abrió queda
pendiente. El desenlace de la incidencia es correcto y queda auditado con el identificador de esa
solicitud, así que la traza no se pierde.

No se cierra desde aquí a propósito: el ciclo de vida de una solicitud es del motor de aprobaciones,
y cerrarla desde compras sería el mismo tipo de motor local que esta Spec evitó construir tres veces.
Queda anotado para quien tome la 045, no como deuda de la 020.
