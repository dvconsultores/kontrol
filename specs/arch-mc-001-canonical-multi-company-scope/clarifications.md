# ACLARACIONES — ARCH-MC-001

Resueltas contra la autoridad existente. Solo se eleva lo que ninguna decidía.

## CL-MC-01 · ¿Cómo viaja el contexto de empresa?

**Cabecera explícita por petición.** Razonado en `research.md` §1: es el único de
los cuatro modelos que resuelve dos pestañas en empresas distintas sin tocar la
renovación de sesión ya remediada.

## CL-MC-02 · ¿Y si el usuario tiene una sola empresa?

Se resuelve automáticamente (`FR-MC-013`). Pedir elegir entre una opción es
fricción sin información. El backend sigue usando la empresa real: la comodidad
es de la interfaz, no del dato.

## CL-MC-03 · ¿Y si tiene varias y no manda cabecera?

La operación de empresa se **rechaza** con un error explícito.

Se consideró elegir «la primera» o «la última usada». Se descarta: una factura
emitida por la empresa equivocada porque el sistema adivinó es exactamente el
daño que esta remediación evita.

## CL-MC-04 · ¿De dónde sale el acceso del usuario a una empresa?

De `UserScope`, que ya existe con `company_id` anulable, y de `user_roles`, que
también lo tiene. **No se crea un sistema paralelo** (`FR-MC-031`).

Hoy ninguna de las dos se usa para esto. Adaptarlas es trabajo de esta
remediación; sustituirlas, no.

## CL-MC-05 · ¿Pertenecer al tenant da acceso a todas sus empresas?

**No** (`FR-MC-030`). Sería reproducir el defecto en la capa de permisos: un
usuario de nóminas de la empresa A no tiene por qué ver la tesorería de la B.

Para instalaciones existentes con una sola empresa, el backfill de accesos es
determinista: todos los usuarios del tenant acceden a la única empresa.

## CL-MC-06 · ¿Directa o derivada?

Directa si la entidad es cabecera o maestro. Derivada si existe FK **obligatoria**
a una autoridad de empresa.

Medido: las 36 derivadas lo hacen por FK no anulable. Ninguna depende de una
relación que pueda faltar, que es lo que el §11 exige.

## CL-MC-07 · ¿Qué se hace con una fila histórica ambigua?

Se **anota y se detiene**, nunca se adivina (`FR-MC-051`). Si es fiscal,
financiera o de inventario, **bloquea** la migración final (`FR-MC-053`).

Es la misma decisión que la Spec 046 tomó con el legado documental, y la Spec 011
con el backfill de unidades.

## CL-MC-08 · ¿Basta con que hoy el tenant tenga una empresa?

**No** (`FR-MC-052`). Hay que demostrar que tuvo una sola durante el **intervalo**
en que se creó la fila. Un tenant que creó su segunda empresa en marzo tiene
filas deterministas antes y ambiguas después.

Por eso hace falta reconstruir el histórico de creación de empresas y calcular,
por tenant, el instante en que dejó de ser monoempresa.

## CL-MC-09 · ¿La licencia limita el esquema?

**No** (`FR-MC-035`). El esquema es multiempresa siempre. La licencia limita
cuántas empresas se pueden **crear y operar**. Degradar el esquema por el plan
comercial reproduce el defecto en cuanto alguien cambie de plan.

## CL-MC-10 · ¿Qué pasa con el plan `MONO_COMPANY` actual?

Hoy no se impone: se creó una segunda empresa con ese plan. El backend pasa a ser
autoridad (`FR-MC-034`). No se inventan planes ni límites nuevos: se **aplica** el
que ya existe.

## CL-MC-11 · ¿La auditoría histórica se migra?

Se clasifica igual que las transacciones. Un evento cuya empresa no sea
reconstruible **se queda sin ella**, anotado. Inventar la empresa de un evento de
auditoría sería falsificar el registro que existe para no falsificar nada.

## CL-MC-12 · ¿Las 14 tablas del tenant cambian?

Siete renombran `company_id` a `tenant_id` con FK real: hoy su nombre miente.

Tres —`user_roles`, `user_scopes`, `audit_events`— son filas del tenant cuyo
`company_id` **sí** designa una empresa: esa columna pasa a FK real. No es
contradicción: la fila es del tenant, el alcance que expresa es de empresa.

## CL-MC-13 · ¿Y `units_of_measure`, que hoy es única por `(company_id, code)`?

Su índice único acota hoy por tenant. Tras normalizar, acotaría por empresa: cada
empresa necesitaría su propio «KG».

**Se eleva.** Es una decisión de producto sobre si el catálogo de unidades es del
tenant o de la empresa. La Spec 011 lo trató como catálogo; el modelo permite
ambas. Ver `OQ-MC-01`.

---

## Elevado

| Id | Pregunta | ¿Bloquea? |
|---|---|---|
| **OQ-MC-01** | ¿`units_of_measure`, `movement_types` y otros catálogos con único por `(company_id, code)` son del tenant o de la empresa? | **No** para especificar; **sí** para migrar esas tablas concretas |
| **OQ-MC-02** | Con acceso a varias empresas, ¿el selector recuerda la última por usuario y dispositivo, o arranca siempre sin elegir? | No |

`OQ-MC-01` afecta a un puñado de catálogos, no al diseño. La clasificación los
marca y la ola correspondiente no se ejecuta hasta responderla.

---

# N7 — ACLARACIONES DE INTEGRIDAD ESTRUCTURAL

Cada respuesta sale de medir el catálogo de PostgreSQL 18.6 en el head vigente,
los modelos, las migraciones y las Specs cerradas. Donde no había autoridad, se
registra como pregunta abierta en vez de inventarse.

## 1. ¿Qué entidades son de empresa directa?

**101 tablas.** Son las que llevan `company_id` propio: 88 con alcance declarado
`COMPANY` más 13 que no lo declaran pero lo son por construcción (§6).

## 2. ¿Qué entidades son de tenant?

**14**, según la matriz canónica y confirmado en los modelos: auditoría,
monedas, tasas de cambio, registros de idempotencia, referencias documentales
heredadas, definiciones de informe, outbox, usuarios y las de identidad.

## 3. ¿Qué entidades son globales?

**3**: `permissions`, `tax_rule_versions`, `unit_conversions`. No se les añade
tenant ni empresa. Una unidad de medida del sistema no pertenece a nadie.

## 4. ¿Qué entidades son de instalación?

**13**, todas del dominio de licenciamiento, homologación y ajustes del sistema.

## 5. ¿Cuáles derivan su empresa?

**35.** Todas declaran su autoridad con `__scope_authority__`.

## 6. ¿Siguen siendo 36 las rutas derivadas?

**No: son 35.** La matriz canónica registraba 36. Medido contra los modelos
vigentes son 35. La corrección se aplica al documento; el hecho relevante —que
ninguna deriva por una clave anulable— se confirma.

## 7. ¿Cuál es la autoridad de cada derivada, y está sana?

Las 35 tienen clave foránea **real** y **NOT NULL** hacia su autoridad. Ninguna
ruta está rota, ninguna es ambigua, ninguna es anulable.

Es el único bloque de N7 que ya estaba completo antes de empezar, y conviene
decirlo: las líneas de documento, los movimientos de sesión de caja y las líneas
de conteo nunca perdieron su padre.

## 8. ¿Qué clave intermedia debe ser NOT NULL?

Todas las de las 35 rutas derivadas ya lo son. En las directas, **11 tablas**
tienen `company_id` anulable: `service_templates`, `presentations`,
`product_presentation_versions`, `units_of_measure`, `stored_files`,
`movement_types`, `taxonomy_nodes`, `profile_versions`, `product_templates`,
`attribute_definitions`, `costing_profiles`.

Estas once necesitan decisión caso por caso y se tratan en §16.

## 9–11. Los UNIQUE: alcance, estado y acción

Hay **31** restricciones de unicidad además de las claves primarias. La
clasificación real:

| Alcance | Cuántas | Ejemplos |
|---|---:|---|
| Ya por empresa | 11 | `warehouses(company_id, code)`, `document_types(company_id, code)`, `units_of_measure(company_id, code)`, `supplier_invoices(company_id, supplier_id, invoice_number, control_number)` |
| Por padre de empresa | 10 | `warehouse_zones(warehouse_id, code)`, `document_versions(document_id, version_number)`, `presentations(product_id, code)` |
| Por identidad de tercero o artículo | 6 | `customers(party_id)`, `suppliers(party_id)`, `products(item_id)` |
| Global legítima | 4 | `feature_flags(key)`, `stored_files(storage_key)`, `unit_conversions(from_unit_id, to_unit_id)`, `legacy_document_references(...)` |

**Ninguna requiere estrecharse de tenant a empresa**: las once que debían ser de
empresa ya lo son, porque N3 las creó así. Las de padre heredan el alcance por
la cadena, que es correcto y no redundante.

El recuento de «13 uniques» que arrastraba la documentación anterior era una
estimación previa a N3. El número real medido es 31, con la distribución de
arriba.

## 12. ¿Cuáles son las reglas de borrado?

Se mantiene el comportamiento por omisión (`NO ACTION`): borrar una empresa con
datos debe fallar. Una empresa es una persona jurídica con histórico fiscal; que
su borrado arrastre en cascada asientos, documentos y libros sería exactamente
lo contrario de lo que la ley exige conservar.

Esto no es una decisión nueva: es P5 de la Constitución —histórico protegido—
aplicado a la capa estructural.

## 13. ¿Alguna clave debe ser diferible?

**No.** Ninguna carga de N7 inserta ciclos entre tablas dentro de una misma
transacción que requieran diferir la comprobación. Añadir `DEFERRABLE` sin
necesidad debilitaría la comprobación a cambio de nada.

## 14. ¿Qué tablas conservan `tenant_id` y `company_id` a la vez?

**Una**: `audit_events`. Es deliberado —el rastro debe poder responder «en qué
instalación» y «en qué empresa»— y desde N5 el tenant se deduce de la empresa al
registrarlo, así que no pueden contradecirse por construcción.

Los cinco casos de `company_id` + `warehouse_id` son los `warehouse_*`, y sí
pueden contradecirse hoy: nada impide que una zona diga pertenecer a la empresa
A y colgar de un almacén de la B.

## 15. ¿Qué redundancias retirará N8?

`legacy_scope_id` y `scope_backfill_class` en 80 tablas, añadidas por N3 como
red de seguridad para un backfill que resultó no ser necesario. N7 **no** las
toca.

## 16. ¿Cuáles se mantienen y protegen en N7?

Las once columnas `company_id` anulables. La decisión, por evidencia:

- **`units_of_measure`, `unit_conversions`** — Spec 011 y `OQ-MC-01` ya
  resolvieron que las unidades del sistema son globales y las de negocio son de
  empresa. Una columna anulable es exactamente la forma de expresar esa mezcla.
  **Se mantiene anulable**, con clave foránea.
- **`stored_files`** — un archivo puede existir antes de saber a qué documento
  pertenecerá. **Se mantiene anulable**, con clave foránea.
- **Las nueve restantes** (`service_templates`, `presentations`,
  `product_presentation_versions`, `movement_types`, `taxonomy_nodes`,
  `profile_versions`, `product_templates`, `attribute_definitions`,
  `costing_profiles`) — son configuraciones de empresa. Se revisó cada punto de
  creación y **todos fijan la empresa**, del contexto validado o del artículo
  padre. **Se endurecen a NOT NULL.**

En todas ellas la clave foránea se añade igualmente: una empresa nula es
distinta de una empresa inventada.

## 17. ¿Cuál es el alcance de cada numeración funcional?

Las claves primarias son UUID, así que no hay secuencias físicas. Los
correlativos existen y son lógicos:

| Numeración | Alcance | Autoridad |
|---|---|---|
| Serie fiscal (`next_number`) | Empresa | `fiscal_number_series.company_id` |
| Números de control | Empresa, por lote | `control_number_batches.company_id` |
| Códigos de orden de compra y venta | Empresa | `code` + `company_id` |
| Números de factura de proveedor | Empresa + proveedor | UNIQUE ya existente |
| Recepciones, pagos, cobros, conciliaciones | Empresa | `code` + `company_id` |

## 18. ¿Cuál es el alcance de las claves de idempotencia?

**Empresa**, en los tres sitios donde N5 encontró contaminación: facturas de
venta, facturas de proveedor y movimientos de inventario. La corrección de N5 lo
aplicó en la consulta; N7 evalúa si además procede una restricción de unicidad
por `(company_id, idempotency_key)`.

## 19. ¿Qué consistencias se pueden expresar relacionalmente?

Las de par redundante: empresa/sucursal, empresa/almacén, empresa/cuenta. La
forma limpia es una clave foránea compuesta contra una clave única del padre que
incluya su empresa — sin añadir columnas nuevas, porque ambas ya existen.

## 20. ¿Qué debe seguir en los servicios?

Todo lo que no es una relación entre filas: que un pago no cancele la deuda de
otra empresa cuando ambos objetos son válidos por separado, que un permiso no
ampare un vehículo ajeno, que una transferencia entre empresas se bloquee. Son
reglas de negocio sobre combinaciones legítimas de datos legítimos, y una clave
foránea no las expresa.

Las guardas de N5 **no se retiran**. N7 añade una capa; no sustituye ninguna.

## Preguntas abiertas

**OQ-N7-01 — RESUELTA.** Se revisó cada punto de creación de las ocho:
`TaxonomyNode`, `AttributeDefinition`, `ProfileVersion`, `ProductPresentationVersion`,
`Presentation`, `MovementType`, `CostingProfile`, `ServiceTemplate` y
`ProductTemplate`. **Todos fijan la empresa**, tomándola del contexto validado o
del artículo padre. Ninguno crea filas sin empresa.

Por tanto se endurecen a NOT NULL, salvo `units_of_measure` y `stored_files`,
que tienen razón documentada para admitir nulo (§16).

Nota de método: la primera medición dio falsos positivos porque el `grep`
contaba constructores multilínea como si no fijaran la empresa. Se comprobó
leyendo cada sitio.

**OQ-N7-02 — Alcance declarado en 13 tablas.** No llevan `__scope__` aunque son
de empresa por construcción. Es una laguna de declaración, no de estructura: sus
claves foráneas ya son correctas. Se declara en N7 para que las pruebas de
arquitectura las cubran.

Ninguna de las dos exige una decisión de negocio o fiscal nueva.

---

# N8 — ACLARACIONES DE CONTRATO Y RETIRADA

Cada respuesta sale de medir el código, el catálogo y las migraciones.

## 1–3. ¿Qué columnas transitorias existen y en cuántas tablas?

`legacy_scope_id` y `scope_backfill_class`, añadidas por las migraciones
`0025`–`0031` a **80 tablas** de empresa.

## 4–7. ¿Alguien las lee, las escribe o depende de ellas?

**Nadie.** Cero referencias en `app/`, cero en `tests/`, cero en el ORM. Nunca
llegaron al modelo operativo: se añadieron como red de seguridad para un
backfill que resultó no ser necesario, porque no existe ninguna instalación
desplegada.

Retirarlas es un `DROP` limpio, no una desconexión.

## 8–10. ¿De qué depende el clasificador de N4?

De dos cosas distintas, y la diferencia es el trabajo de esta fase.

`preflight.py` consulta `information_schema` del **destino**: ya está
desacoplado y sigue funcionando contra cualquier esquema.

`planes()`, en `runner.py`, decide el conjunto de trabajo leyendo el **ORM
vigente** y excluyendo las tablas cuya `company_id` ya tiene clave foránea. Tras
N7 eso vale para todas, así que devuelve cero planes: el clasificador quedó
ciego.

**Debe desacoplarse `planes()`**, no `preflight`. El alcance declarado
—`__scope__`, `__scope_authority__`— sí puede seguir viniendo de los modelos:
describe la *semántica* del dominio, que no cambia entre versiones. Lo que tiene
que preguntarse al destino es «¿esta columna ya tiene dueño garantizado ahí?».

## 11. ¿Qué repliegues de empresa siguen vivos?

**Uno**: `warehouse_in_tenant_scope`, en organización. Su docstring lo describe
como diseño vigente:

> «Los módulos de negocio usan el `tenant_id` del usuario como alcance
> (`company_id`) […] En el modelo MONO_COMPANY el tenant tiene una sola empresa,
> por lo que este helper reconcilia ambos identificadores».

Sus cuatro llamantes pasan hoy `company_id`, así que la primera rama hace la
comprobación correcta y la segunda —la búsqueda por tenant— es código muerto.
Funciona por accidente y su nombre invita a reintroducir el defecto.

## 12. ¿Hay cargas útiles con propiedad ambigua?

No. N5 cerró el último caso —el cuerpo que imponía la empresa en la Spec 045— y
la familia de pruebas de arquitectura de N5 lo vigila.

## 13–17. El contrato de la cabecera

| Situación | Comportamiento del runtime |
|---|---|
| Una sola empresa accesible, sin cabecera | Se resuelve sola |
| Varias, sin cabecera | `400 COMPANY_CONTEXT_REQUIRED` |
| Empresa no accesible | `404 COMPANY_NOT_FOUND` |
| Empresa de otro tenant | `404`, sin revelar que existe |
| Empresa inactiva | `409 COMPANY_INACTIVE` |
| Rutas de tenant, global o instalación | No aplica |

El contrato debe declarar la cabecera como **opcional**, con la descripción de
cuándo hace falta. Declararla obligatoria sería mentir: el runtime la resuelve
solo cuando puede, y esa auto-resolución es una decisión de diseño de N1, no un
descuido.

## 18–19. Nulos legítimos frente a nulos de transición

| Tabla | Campo | Qué significa el nulo | ¿Transitorio? |
|---|---|---|---|
| `units_of_measure` | `company_id` | Unidad del sistema (Spec 011, `OQ-MC-01`) | No |
| `stored_files` | `company_id` | Archivo anterior a su documento | No |
| `movement_types` | `company_id` | `global_scope`: tipo de toda la instalación | No |
| `costing_profiles` | `company_id` | Ídem | No |
| `roles`, `user_roles`, `user_scopes` | `company_id` | Vale en todas las empresas del tenant | No |
| `idempotency_records`, `legacy_document_references` | `company_id` | Sin acotar | No |
| `audit_events`, `outbox_events` | `company_id`, `tenant_id` | Acción anterior a conocerlos | No |

**Ninguno es transitorio.** Los once tienen semántica documentada, y N7 ya
corrigió el error de endurecer dos de ellos por inercia.

## 20–21. Los skips

| Categoría | Cuántos | Ejemplos |
|---|---:|---|
| Motor ausente en el entorno (PostgreSQL, alembic) | 6 | aislamiento multiempresa, estructura de N7 |
| Servicio externo (ClamAV, S3, libmagic) | 5 | análisis antivirus, almacenamiento real |
| Cadena documental no aplicable | 1 | `homologation_records.evidence_sha256` |
| **Fixture legado ausente** | **2** | preflight de N4 sobre base heredada |

Los dos últimos son **categoría F**: ocultaban un requisito de N8. Las pruebas
del fixture hostil se saltaban porque la base `kontrol_legacy` se sembró en una
sesión anterior y se perdió al borrarse el directorio temporal.

Un fixture hostil que no se puede reconstruir no es un fixture: es un recuerdo.
Se resuelve creando el sembrador como artefacto versionado.

## 22. ¿Hay alias heredados en el frontend?

No. N6 centralizó la cabecera en un único punto y una prueba de arquitectura
comprueba que no exista una segunda asignación.

## 23. ¿Quedó documentación vieja tras los cambios de alcance de N7?

Sí. `canonical-scope-matrix.md` clasifica `currencies`, `exchange_rates` y
`report_definitions` como de tenant, y N7 demostró que son de empresa: el código
las crea con la empresa activa, las lista por empresa y N5 ya había probado su
aislamiento.

## Preguntas abiertas

**Ninguna material.** El desacoplamiento de `planes()` no introduce ninguna
decisión de negocio: aplica al conjunto de trabajo la misma pregunta que
`preflight` ya le hace al destino.

---

# N9 — ACLARACIONES DE LA RECONVERGENCIA DE 046

## 1–6. Cardinalidad

Registrados hoy: **19**. Que `REM-046-001` exige añadir: **4**. Esperado al
cerrar: **23**. Sin extras, sin duplicados —comprobado por diccionario, cuyas
claves no pueden repetirse.

El «19/19» del encargo nombra otra cosa, también cierta: hay 19 registrados y
**uno** probado. No hay contradicción entre autoridades, hay dos preguntas
distintas, y N9 responde a las dos.

## 7–16. Entidad, tabla, clave y alcance de cada tipo

Los 23 son de **empresa directa**: llevan `company_id` propio con clave foránea
real a `companies`. Ninguno es derivado, de tenant ni global.

`HomologationRecord` merece una nota: el registro declara `company_id` como su
columna de empresa y el modelo **no la tiene**, así que `resolve_resource`
devuelve `None` y el control se apoya solo en el permiso. Es deliberado —el acto
de homologación es de la instalación— y está escrito en el propio registro.

## 17–19. Permisos

Cada tipo declara el suyo, del módulo dueño de la entidad: `compras:view`,
`ventas:view`, `inventario:view`, `maestros:view`, `regulatorio:view`,
`aprobaciones:view`, `organization:view`, `homologacion:view`. Los cuatro nuevos
usan `tesoreria:view` y `compras:view` según su módulo.

## 20–24. Autorización del documento y del recurso

Son dos comprobaciones distintas y ambas ocurren: el documento se resuelve
contra la empresa activa —corregido en N5— y el recurso vinculado se comprueba
aparte con `_assert_resource_access`, que valida empresa **y** permiso.

Un documento sin vínculos se autoriza por su propia empresa. Descarga y
previsualización dependen del documento, y el vínculo añade la comprobación del
recurso cuando existe.

## 25. Los cuatro nuevos

**Empresa directa**, los cuatro. Verificado contra el modelo vigente, no contra
el informe histórico: `ap_payments`, `bank_transactions`, `cash_sessions` y
`reconciliations`, todas con `company_id` y clave foránea.

## 26–29. Congelado y Spec 045

`frozen_version_id` vive en `DocumentLink`. La cadena
`ApprovalRequest → DocumentLink → frozen_version_id` está implementada y
`CVG-045-04` figura **`RESOLVED_BY_SPEC_046`** en la convergencia de 045.

## 30–33. Almacenamiento y análisis

Sistema de ficheros: proveedor operativo, verificable en este entorno.

**S3 es `FR-046-032`, prioridad P1.** No es obligatorio para cerrar 046, así que
los 8 saltos son legítimos y no ocultan ningún requisito. Se clasifican como
`IMPLEMENTED_NOT_VERIFIED`.

ClamAV **1.4.3 real**, con sus tres bases de firmas. Sin simulación.

## 34–38. Máquina de estados del análisis

`PENDING_SCAN`, `CLEAN`, `INFECTED`, `SCAN_FAILED`. Solo `CLEAN` permite la
entrega; el propio módulo lo dice en su cabecera: *«un archivo que no está
`CLEAN`»* no se entrega, y no poder analizar **significa** `SCAN_FAILED`.

## 39–40. Retención

`FR-046-065` —política de retención configurable— es **P1**. La operación de
purga está implementada; el planificador que la ejecute periódicamente no es
requisito P0 de 046 y su dueño natural es la Spec de instalación y
actualización. Se documenta, no se esconde.

## 41–44. Consumidores y artefactos

La matriz histórica declaraba desbloqueadas cinco Specs por «tipo registrado y
probado», y el propio `REM-046-001` corrigió esa afirmación: *«registré dieciséis
tipos y probé uno»*. N9 la rehace contra el maestro de Specs, y ningún consumidor
se declara desbloqueado sin revisar sus otros impedimentos.

## El hallazgo que cambia el diseño de la remediación

`REM-046-001` proponía dos caminos y recomendaba el B —que el registro declarara
si la columna de cada consumidor contiene una empresa o un tenant— porque el A
—normalizar los cinco módulos— era «enorme y no cabe en una remediación
puntual».

**Se hizo el A.** No como remediación de 046, sino como ARCH-MC-001 entera. N5
corrigió los escritores y N7 puso las claves foráneas; medido hoy, las tablas de
los cinco módulos tienen `company_id` con referencia real.

El camino B queda **sin objeto**: añadir un campo que distinga empresa de tenant
describiría una ambigüedad que ya no existe, y sería deuda nueva el día que
alguien lo leyera y creyera que aún hace falta.

No es una decisión material nueva. Es una decisión anterior que dejó de ser
necesaria porque su causa se resolvió en otro sitio.

## Preguntas abiertas

**Ninguna material.**
