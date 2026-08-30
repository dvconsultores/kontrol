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
