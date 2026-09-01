# ARCH-MC-001 — ALCANCE CANÓNICO MULTIEMPRESA

| Campo | Valor |
|---|---|
| Tipo | **Remediación arquitectónica transversal** — no consume número de Spec |
| Estado | `DRAFT` — ciclo documental |
| Origen | `GATE-MULTICOMPANY-SCOPE.md` · `REM-046-001.md` |
| Severidad | **P0 — defecto funcional multiempresa** |
| Bloquea | **Spec 012** · `REM-046-001` · convergencia de 046 |
| Decisión de producto | **KONTROL es multiempresa por tenant** (tomada, no se re-pregunta) |

---

## 1. El problema, medido

`INSTALLATION → TENANT → COMPANY → BRANCH → OPERACIÓN` es la cadena que la
baseline declara. El dato no la sostiene.

| Medición | Valor |
|---|---:|
| Tablas del modelo | **166** |
| Con columna `company_id` | 107 |
| Con FK real a `companies` | **17** |
| Con `company_id` que en realidad guarda `tenant_id` | **90** |
| Escrituras `company_id = actor.tenant_id` | **100** |
| Lecturas `company_id == user.tenant_id` | **75** |
| Operaciones de API con alcance de empresa | **276** de 404 |

Las 17 correctas son exactamente las de las Specs **008**, **045** y **046** —las
tres cerradas con `COMPLETE_100`— más `branches`. La diferencia no es de criterio:
es de época.

### Lo que está probado, no supuesto

```
crear segunda empresa          -> 200   (con el plan del tenant en MONO_COMPANY)
parties.company_id guardado    -> ni Empresa A, ni Empresa B: el tenant
GET /maestros/terceros         -> no admite filtrar por empresa
almacenes filtrando A / B      -> 1 y 1     ← Spec 008, con FK real
vincular documento a Party     -> 404 RESOURCE_NOT_FOUND
vincular documento a Warehouse -> 200
```

## 2. Por qué es defecto y no deuda

El módulo fiscal asigna con `actor.tenant_id` la serie de numeración, los lotes de
números de control del SENIAT, la emisión y el registro de impresión.

Cada empresa es un **RIF distinto**. Dos empresas del mismo tenant compartirían
correlativo de factura, rango autorizado a otra y libro de ventas. Eso no produce
un modelo feo: produce **libros inválidos**. Contradice el `P4`.

## 3. La ventana que se cierra

| Situación del tenant | ¿Se deduce la empresa de una fila? |
|---|---|
| Una empresa en todo su histórico | **Sí, con certeza** |
| Dos o más | **No.** La fila no lo dice |

Hoy el backfill es determinista. En cuanto una instalación tenga dos empresas y
opere con ambas, deja de serlo **para siempre**. No es que el dato se pierda: es
que nunca se captura (`P23`).

---

## 4. Requisitos funcionales

### 4.1 Semántica canónica

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-001 | `tenant_id` significa siempre `Tenant.id`; `company_id`, `Company.id`; `branch_id`, `Branch.id` | P0 |
| FR-MC-002 | Ninguna columna puede nombrar una entidad y almacenar otra | P0 |
| FR-MC-003 | Toda entidad persistente declara su alcance: `GLOBAL`, `INSTALLATION`, `TENANT`, `COMPANY`, `BRANCH` o `DERIVED` | P0 |
| FR-MC-004 | No existe `UNKNOWN_SCOPE`: las 166 tablas quedan clasificadas | P0 |
| FR-MC-005 | Una entidad `DERIVED` alcanza su empresa por una ruta **obligatoria, determinista y persistente**; una FK anulable no es ruta | P0 |
| FR-MC-006 | El objetivo no es poner `company_id` en 82 tablas, sino que 133 entidades determinen su empresa sin ambigüedad | P0 |

### 4.2 Contexto de empresa

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-010 | Existe un `CompanyContext` por petición con tenant, empresa, usuario y alcances | P0 |
| FR-MC-011 | El frontend **propone** la empresa; el backend la **valida**: existe, es del tenant, el usuario accede, la licencia lo permite, la empresa está activa | P0 |
| FR-MC-012 | Manipular el almacenamiento del navegador no da acceso a otra empresa | P0 |
| FR-MC-013 | Con una sola empresa autorizada, se resuelve automáticamente y no se pide elegir | P1 |
| FR-MC-014 | Con varias, hay selector inequívoco y la empresa activa está siempre visible | P0 |
| FR-MC-015 | Dos pestañas pueden operar en empresas distintas sin contaminarse | P0 |
| FR-MC-016 | El contexto no reintroduce la carrera de `/auth/refresh` cerrada en `REM-AUTH-ROUTE-CRAWL-001` | P0 |
| FR-MC-017 | El cierre de sesión limpia contexto, pista de empresa y cachés de empresa | P0 |
| FR-MC-018 | Perder el acceso a una empresa con la sesión viva invalida el contexto en la siguiente operación | P0 |
| FR-MC-019 | Los trabajos sin petición HTTP se ejecutan bajo un contexto explícito, nunca implícito | P1 |

### 4.3 Autoridad de consulta y escritura

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-020 | Toda consulta sobre entidad de empresa se acota en el **backend**, no por filtro del cliente | P0 |
| FR-MC-021 | Un listado nunca devuelve filas de otra empresa esperando que el cliente filtre | P0 |
| FR-MC-022 | Leer un recurso de otra empresa responde **404**, sin confirmar existencia | P0 |
| FR-MC-023 | Escribir no acepta `company_id` del cliente distinto del contexto validado | P0 |
| FR-MC-024 | En entidades de empresa, `company_id` no es asignable en masa | P0 |
| FR-MC-025 | Ningún servicio asigna `actor.tenant_id` a una propiedad llamada `company_id` | P0 |

### 4.4 Acceso del usuario y licencia

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-030 | Pertenecer al tenant **no** concede acceso a todas sus empresas | P0 |
| FR-MC-031 | El acceso se expresa con la estructura existente de la Spec 003; no se crea un sistema paralelo | P0 |
| FR-MC-032 | El permiso y el alcance son cosas distintas: `ventas:view` en la empresa A no habilita B | P0 |
| FR-MC-033 | El alcance por sucursal sigue vigente y convive con el de empresa | P1 |
| FR-MC-034 | El límite de empresas lo impone el **backend** según los derechos de la licencia | P0 |
| FR-MC-035 | El esquema es multiempresa aunque el plan sea de una sola: la licencia limita el uso, no degrada la arquitectura | P0 |

### 4.5 Auditoría y eventos

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-040 | Toda operación de empresa permite reconstruir tenant, empresa, usuario, acción y entidad | P0 |
| FR-MC-041 | Un evento de empresa transporta la empresa real, no el tenant | P0 |

### 4.6 Migración e histórico

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-050 | Patrón `EXPAND → BACKFILL → VERIFY → SWITCH → CONSTRAIN → CONTRACT`; nunca una migración destructiva única | P0 |
| FR-MC-051 | Cada fila heredada se clasifica `MC-A`..`MC-E`; **no se inventa empresa** | P0 |
| FR-MC-052 | El determinismo se demuestra sobre el **intervalo** relevante, no sobre el número de empresas de hoy | P0 |
| FR-MC-053 | Un crítico no reconstruible **detiene** la migración final; no hay valor por defecto permisivo | P0 |
| FR-MC-054 | El valor heredado se conserva hasta verificar | P0 |
| FR-MC-055 | Existe un mecanismo auditable de resolución manual: quién, cuándo, con qué evidencia, valor anterior y nuevo | P0 |
| FR-MC-056 | La migración no altera importes, cantidades, bases imponibles ni números de documento | P0 |
| FR-MC-057 | Ninguna columna doble sobrevive sin fase de retirada declarada | P0 |
| FR-MC-058 | Un informe previo, **sin escribir**, muestra el recuento por clase antes de cualquier cambio | P0 |

### 4.7 Restricciones e índices

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-060 | Si la columna se llama `company_id`, hay FK real a `companies`; si `tenant_id`, a `tenants` | P0 |
| FR-MC-061 | La integridad la garantiza PostgreSQL cuando puede, no solo el servicio | P0 |
| FR-MC-062 | Los índices únicos con alcance se revisan uno a uno: pasar de tenant a empresa cambia su significado | P0 |
| FR-MC-063 | Las secuencias fiscales se acotan según la normativa, no por comodidad | P0 |

### 4.8 Contratos con lo ya cerrado

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-070 | La Spec 008 no se rompe: es la referencia positiva | P0 |
| FR-MC-071 | La Spec 045 mantiene su empresa real; no se degrada a tenant | P0 |
| FR-MC-072 | `ResourceKind` de la Spec 046 declara `scope_kind` y su resolutor **explícitos**, sin inferir del nombre de la columna | P0 |
| FR-MC-073 | Tras normalizar, los 19 tipos registrados se prueban y `STILL_BLOCKED_BY_046` queda en 0 | P0 |
| FR-MC-074 | La Spec 011 conserva intacta su semántica de conversión | P0 |

### 4.9 Regla para lo que venga

| Id | Requisito | Prioridad |
|---|---|---|
| FR-MC-080 | Ninguna entidad nueva introduce `tenant_id`, `company_id` o `branch_id` sin declarar alcance, autoridad y ruta | P0 |
| FR-MC-081 | Toda Spec futura que cree datos de empresa incluye **dos empresas del mismo tenant** en su matriz de aceptación | P0 |

---

## 5. Requisitos no funcionales

| Id | Requisito |
|---|---|
| NFR-MC-01 | Aceptación sobre **PostgreSQL 18.x** real; SQLite no es evidencia final |
| NFR-MC-02 | Acotar por empresa no degrada el plan de consulta: índices revisados con `EXPLAIN` en las tablas grandes |
| NFR-MC-03 | Toda caché de empresa lleva la empresa en su clave |
| NFR-MC-04 | Las claves de idempotencia no colisionan entre empresas |
| NFR-MC-05 | El selector cumple WCAG 2.2 AA y es operable con teclado |
| NFR-MC-06 | Sin desbordamiento horizontal entre 320 y 1440 |
| NFR-MC-07 | Cross-browser en Chromium, Firefox y WebKit |
| NFR-MC-08 | La migración se ejecuta por fases con recuperación entre ellas |

---

## 6. Fuera de alcance

ARCH-MC-001 corrige la propiedad de lo que **ya existe**. No implementa:

- La Spec 012 ni ningún maestro comercial.
- Flujos nuevos de compras, ventas o inventario.
- Reglas fiscales nuevas.
- Contabilidad, consolidación o transferencias **intercompany** — `FUTURE_CAPABILITY`.
- Fusiones o escisiones societarias.

> El modelo normalizado debe **poder distinguir** A de B para que lo intercompany
> se construya después. Simular intercompany mezclando datos es justamente el
> defecto que esta remediación cierra.

---

# 7. FASE N7 — INTEGRIDAD ESTRUCTURAL EN POSTGRESQL

## 7.1 Qué añade N7, y qué no

N5 hizo que el sistema **se comporte** bien con dos empresas. N6 hizo que el
frontend **opere** bien sobre ese comportamiento. Las dos protecciones viven en
código: si alguien escribe una consulta nueva, un trabajo de fondo, un script de
importación o un `INSERT` a mano, las esquiva enteras.

N7 convierte esas invariantes en **estructura**: lo que hoy garantiza el
servicio pasa a garantizarlo también PostgreSQL, que no se puede olvidar de
comprobarlo.

N7 **no sustituye** a N5 ni a N6. Es la cuarta capa de una defensa que ya tiene
tres, y ninguna de las anteriores se retira.

## 7.2 El estado medido, no supuesto

Contra el catálogo real de PostgreSQL 18.6 en el head `0032_mc_expand_tenant_scoped`:

| Hecho | Medida |
|---|---:|
| Tablas de alcance COMPANY con `company_id` propio | 88 |
| De ellas, **sin clave foránea real a `companies`** | **80** |
| De ellas, con `company_id` **anulable** | **11** |
| Tablas de alcance COMPANY que derivan su empresa | 35 |
| De ellas, con ruta válida (FK real y NOT NULL) | **35** |
| Tablas de alcance TENANT | 14 |
| De ellas, **sin clave foránea real a `tenants`** | **3** |
| Claves foráneas existentes en total | 242 |
| Restricciones UNIQUE (sin contar claves primarias) | 31 |

Dos correcciones documentales que salen de medir en vez de asumir:

**Las rutas derivadas son 35, no 36.** La matriz canónica registraba 36. Al
comprobarlo contra los modelos vigentes son 35, y las 35 tienen clave foránea
real y no anulable. La afirmación «ninguna deriva por una FK anulable» se
confirma; el recuento se corrige.

**`company_id` es texto sin clave foránea en 80 tablas.** N3 las expandió y N5
las llenó con la empresa correcta, pero la columna sigue siendo una cadena que
la base no contrasta con nada. Hoy nada impide escribir ahí el identificador de
un tenant, de una empresa de otro tenant, o de algo que no existe.

## 7.3 Requisitos funcionales

**FR-N7-001** — Toda tabla de alcance COMPANY con `company_id` propio tiene
clave foránea real a `companies.id`.

**FR-N7-002** — Toda tabla de alcance TENANT con `tenant_id` propio tiene clave
foránea real a `tenants.id`.

**FR-N7-003** — Toda columna que referencie una sucursal tiene clave foránea
real a `branches.id`.

**FR-N7-004** — Toda tabla de alcance COMPANY que derive su empresa declara su
autoridad y esa autoridad existe como columna.

**FR-N7-005** — La columna que determina la empresa por derivación es NOT NULL y
tiene clave foránea real. Una ruta que puede ser nula no es una ruta.

**FR-N7-006** — Ninguna columna `company_id` puede contener el identificador de
un tenant. La clave foránea lo impide estructuralmente.

**FR-N7-007** — Cada restricción UNIQUE expresa el alcance funcional de su
regla, no el que tuviera por conveniencia histórica.

**FR-N7-008** — Una clave de negocio de alcance empresa puede repetirse entre
dos empresas cuando la regla funcional lo permita.

**FR-N7-009** — Esa misma clave no puede duplicarse dentro de una empresa.

**FR-N7-010** — Las entidades de alcance tenant conservan unicidad por tenant.

**FR-N7-011** — Los catálogos globales y de instalación conservan su alcance. No
se les añade tenant ni empresa.

**FR-N7-012** — Cuando una tabla guarda a la vez `tenant_id` y `company_id`, no
puede persistirse una combinación en la que la empresa pertenezca a otro tenant.

**FR-N7-013** — Cuando una tabla guarda a la vez `company_id` y `branch_id`, la
sucursal debe pertenecer a esa empresa.

**FR-N7-014** — Cuando una tabla guarda a la vez `company_id` y `warehouse_id`
representando la misma propiedad, el almacén debe pertenecer a esa empresa.

**FR-N7-015** — Cuando una tabla guarda a la vez `company_id` y una cuenta
bancaria representando la misma propiedad, la cuenta debe pertenecer a esa
empresa.

**FR-N7-016** — La configuración fiscal pertenece inequívocamente a una empresa.

**FR-N7-017** — Las series de numeración fiscal pertenecen inequívocamente a una
empresa.

**FR-N7-018** — Los lotes de números de control pertenecen a la empresa
autorizada, y los números que cuelgan de ellos heredan esa empresa.

**FR-N7-019** — El documento fiscal pertenece a la empresa emisora.

**FR-N7-020** — Libros y cierres pertenecen a la empresa correcta.

**FR-N7-021** — Las retenciones conservan la empresa del agente que las practica.

**FR-N7-022** — La numeración fiscal no se mezcla entre empresas.

**FR-N7-023** — N7 no modifica ninguna fórmula ni ningún importe fiscal.

**FR-N7-024** — Las relaciones financieras mantienen propiedad consistente.

**FR-N7-025** — Las rutas derivadas de inventario mantienen empresa consistente.

**FR-N7-026** — No quedan claves foráneas huérfanas.

**FR-N7-027** — No quedan rutas derivadas rotas.

**FR-N7-028** — No quedan colisiones de unicidad.

**FR-N7-029** — Ninguna autoridad obligatoria queda anulable sin justificación
registrada.

**FR-N7-030** — PostgreSQL rechaza por sí solo las inserciones estructuralmente
inválidas, sin depender del código de aplicación.

## 7.4 Requisitos no funcionales

**NFR-N7-001** — Las migraciones son auditables y pequeñas, separadas por
naturaleza del cambio, no una sola migración masiva.

**NFR-N7-002** — `alembic upgrade --sql` produce SQL válido para las migraciones
de esquema.

**NFR-N7-003** — Una instalación limpia sobre PostgreSQL 18.6 vacío llega a head
y opera con dos empresas.

**NFR-N7-004** — El catálogo de PostgreSQL, el ORM y las migraciones coinciden.
Deriva nueva: cero.

**NFR-N7-005** — Las consultas representativas por empresa no se degradan. Los
índices que se añadan están justificados por un patrón de consulta real.

**NFR-N7-006** — Las restricciones no rompen ninguna operación funcionalmente
válida. Si algo se rompe, se busca la causa raíz antes de tocar la restricción.

## 7.5 Criterios de aceptación

**AC-N7-001** — Un `INSERT` directo con el identificador de un tenant en
`company_id` es rechazado por PostgreSQL con `foreign_key_violation`.

**AC-N7-002** — Un `INSERT` directo con una empresa inexistente es rechazado
igual.

**AC-N7-003** — Un `INSERT` directo con la autoridad derivada en NULL es
rechazado con `not_null_violation`.

**AC-N7-004** — La misma clave de negocio en dos empresas distintas se acepta.

**AC-N7-005** — La misma clave repetida dentro de una empresa es rechazada con
`unique_violation`.

**AC-N7-006** — Una sucursal de otra empresa en una fila que guarda ambas es
rechazada.

**AC-N7-007** — El fixture hostil de N4, que contiene filas inválidas a
propósito, **no** pasa las restricciones. Que falle es el resultado correcto.

**AC-N7-008** — Los cálculos fiscales antes y después son idénticos: mismas
bases, mismos importes, mismos totales.

**AC-N7-009** — Las once regresiones de N5 y las de N6 siguen verdes.

**AC-N7-010** — Fallos inesperados: cero.

## 7.6 Fuera del alcance de N7

No se retira `legacy_scope_id` ni `scope_backfill_class`; no se retira ningún
mecanismo transicional; no se declara `X-Kontrol-Company` en OpenAPI. Todo eso
es N8.

No se toca `REM-046-001`, ni los tipos de recurso pendientes, ni la
reconvergencia de 046. Eso es N9.

No se implementa la Spec 012. No se implementa ninguna capacidad intercompany.
