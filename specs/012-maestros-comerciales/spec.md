# SPEC 012 — MAESTROS COMERCIALES

> ## IMPLEMENTADA Y CONVERGIDA — 2026-09-02
>
> `SPEC 012 — COMPLETE / CONVERGED`
>
> Once entidades, catorce rutas y dos pantallas. Los catálogos nacen vacíos y
> `resolve_price` devuelve el precio **y la versión que lo produjo**, que es la
> deuda que esta Spec existía para cerrar.
>
> Evidencia: `spec012-final-checkpoint.md` · `implementation-report.md` ·
> `nested-resource-security-report.md` · `multi-company-evidence.md` ·
> `postgresql-integrity-report.md` · `pricing-resolution-report.md` ·
> `convergence.md`
>
> Autoridad: `docs/governance/gates/GATE-MULTICOMPANY-SCOPE.md` ·
> `specs/arch-mc-001-canonical-multi-company-scope/`

| Campo | Valor |
|---|---|
| Estado | **`COMPLETE / CONVERGED`** |
| Autoridad | `ADR-D0-005` (D0-05) · Constitución v1.1 · baseline arquitectónica |
| Propietaria de | Precio, descuento, condición de pago, zona, canal, crédito comercial |
| Depende de | 009 Terceros · 010 Catálogo · 011 Unidades · 045 Aprobaciones |
| Habilita | 029 Pedido · 030 Crédito · 034 Facturación · 036 Devoluciones · 037 CxC |

---

## 1. El problema, medido

No es una impresión: es lo que hay hoy en el código.

| Dato comercial | Dónde vive | Tipo real |
|---|---|---|
| Lista de precios del cliente | `customers.price_list` | `String(120)` **texto libre** |
| Condición de pago del cliente | `customers.payment_term` | `String(120)` **texto libre** |
| Zona comercial del cliente | `customers.zone` | `String(120)` **texto libre** |
| Vendedor asignado | `customers.salesperson` | `String(200)` **texto libre** |
| Condición de pago del proveedor | `suppliers.payment_term` | `String(120)` **texto libre** |
| Lista de precios de la cotización | `sales_quotes.price_list` | `String(120)` **texto libre** |
| Descuento | `sales_quote_lines.discount`, `sales_order_lines.discount` | `Numeric(18,2)` **tecleado, sin regla** |
| Precio unitario | `*_lines.unit_price` | `Numeric(18,2)` **tecleado, sin origen** |

Y lo que **no existe**, once entidades: `PriceList`, `PriceListVersion`,
`PriceListItem`, `PricePrecedence`, `PaymentTerm`, `CommercialZone`,
`SalesChannel`, `DiscountPolicy`, `CreditPolicy`, `CustomerCommercialTerms` y
`SalesCommissionPolicy` (reservada). Ninguna tabla. Ninguna FK. Ninguna vigencia.

> Esta lista decía nueve e incluía una `PriceRule` que ningún artefacto define,
> mientras `data-model.md` describía once. Lo que `PriceRule` iba a hacer lo hace
> `PricePrecedence`; se retira el nombre sobrante.

> Nota de auditoría: **no** existen `price_1`..`price_5` en el código. El
> problema no es un maestro mal modelado; es que no hay maestro.

### Lo que esto significa

Cada cotización emitida hoy lleva un precio cuyo origen **no puede
reconstruirse**: no se sabe de qué lista salió, con qué vigencia, ni quién
autorizó el descuento. Un descuento del 40 % y uno del 4 % son indistinguibles
para el sistema: los dos son un número que alguien escribió.

Es la misma clase de deuda que cerró la Spec 011 con las unidades, y se comporta
igual: **no se pierde el dato, es que nunca se captura** (`P23`). Ninguna
migración posterior puede repararlo.

---

## 2. Lo que esta Spec NO es

012 **no** es un CRUD de listas de precios. Si termina siendo eso, habrá
fallado.

| No es | Es |
|---|---|
| Un catálogo de precios | La **autoridad comercial transversal** del sistema |
| Una tabla de plazos | El maestro que hace que «30 días» signifique lo mismo en todas partes |
| Un motor de promociones | La configuración desde la que otras Specs calculan |
| El proceso de venta | Lo que el proceso de venta **consulta** |

**No implementa** cotización, pedido, crédito ni facturación. Prepara sus
contratos.

---

## 3. Principios que gobiernan

| Principio | Consecuencia concreta en 012 |
|---|---|
| **P8** · nada hardcodeado | Ningún precio, plazo, límite de descuento, zona ni canal vive en el código. Los catálogos **nacen vacíos** |
| **P5** · histórico protegido | Editar una lista **nunca** cambia un documento aprobado |
| **P6** · el backend manda | El límite de descuento se valida en el servidor, no en la interfaz |
| **P17/P22** · autoridad única | Una sola fuente de precio; ningún módulo calcula el suyo |
| **P13** · integridad transaccional | El snapshot se escribe en la misma transacción que aprueba el documento |
| **P23** · captura temprana | El origen del precio se registra al emitir, no se deduce después |
| **P21** · paridad del motor | Aceptación sobre **PostgreSQL 18.x** real |

---

## 4. Requisitos funcionales

### 4.1 Listas de precios

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-001 | `PriceList` por empresa, con moneda tomada del maestro monetario existente y segmento opcional | P0 |
| FR-012-002 | `PriceListVersion` con `valid_from` / `valid_to`; **una lista nunca se edita en sitio** | P0 |
| FR-012-003 | `PriceListItem` por producto o categoría, con presentación y rango de volumen | P0 |
| FR-012-004 | El precio se expresa en la unidad y presentación de la Spec 011; el factor se congela como allí | P0 |
| FR-012-005 | Dos versiones de la misma lista **no** pueden solapar vigencia | P0 |
| FR-012-006 | Una versión referenciada por un documento aprobado **no se borra ni se altera** | P0 |
| FR-012-007 | Estados de versión: `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED` | P0 |
| FR-012-008 | La lista declara su **fuente**: quién la cargó y de dónde | P1 |

### 4.2 Resolución de precio

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-010 | La precedencia es **dato configurable por empresa**, no código (`R-D0-05-1`) | P0 |
| FR-012-011 | KONTROL entrega el orden por defecto documentado en `ADR-D0-005`, reordenable, **no impuesto** | P0 |
| FR-012-012 | Empate de precedencia: se resuelve por vigencia más reciente y, a igualdad, menor precio (`R-D0-05-2`) | P0 |
| FR-012-013 | Un empate **irresoluble** se reporta como error de configuración; **jamás** se resuelve al azar | P0 |
| FR-012-014 | `resolve_price(...)` es la **única** autoridad de precio del sistema | P0 |
| FR-012-015 | La resolución devuelve el precio **y** la versión que lo produjo | P0 |
| FR-012-016 | Sin lista aplicable, la resolución **no inventa** un precio: lo declara ausente | P0 |

### 4.3 Descuentos

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-020 | Descuento de **línea** y de **documento** son entidades distintas | P0 |
| FR-012-021 | `DiscountPolicy` define el máximo por rol, producto o categoría | P0 |
| FR-012-022 | **Ningún porcentaje viene de fábrica.** El catálogo nace vacío | P0 |
| FR-012-023 | Superar el límite **genera solicitud de aprobación** (Spec 045); no bloquea | P0 |
| FR-012-024 | La acumulación es configurable; las incompatibilidades se declaran | P1 |
| FR-012-025 | Todo descuento registra la política, su versión y el nivel de autorización | P0 |

### 4.4 Condiciones de pago

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-030 | `PaymentTerm` es maestro, **nunca** una cadena (`R-D0-05-3`) | P0 |
| FR-012-031 | Estructura: días, cuotas, porcentajes, desplazamiento del vencimiento, contado, anticipo | P0 |
| FR-012-032 | El catálogo **nace vacío**: «contado» y «30 días» son datos de cada empresa | P0 |
| FR-012-033 | Aplicable a cliente y a proveedor, sin duplicar el maestro | P1 |

### 4.5 Zona comercial y canal

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-040 | `CommercialZone` es **territorio de ventas**, entidad distinta de `WarehouseZone` (Spec 008) | P0 |
| FR-012-041 | Prohibido reutilizar la tabla de zona física por compartir el nombre «zona» | P0 |
| FR-012-042 | `SalesChannel` como maestro; nace vacío | P1 |
| FR-012-043 | La zona puede tener vendedor y ruta asignados | P1 |

### 4.6 Condiciones comerciales del cliente

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-050 | El cliente puede tener lista, condición, zona, canal y vendedor **por referencia**, no por texto | P0 |
| FR-012-051 | **No se duplica** `Party` ni `Customer`: se extiende con FK | P0 |
| FR-012-052 | `CreditPolicy` es distinta de la condición de pago (`R-D0-05-4`) | P0 |
| FR-012-053 | El bloqueo comercial conserva motivo, autor y fecha | P1 |

### 4.7 Snapshot comercial

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-060 | Al aprobarse un documento se congela: precio, descuento, política y versión, condición, moneda, tasa **y la versión de lista/regla que produjo el precio** (`R-D0-05-5`) | P0 |
| FR-012-061 | Modificar un maestro **nunca** altera un documento aprobado (`R-D0-05-6`) | P0 |
| FR-012-062 | La reconstrucción histórica se hace **desde el snapshot**, jamás recalculando | P0 |
| FR-012-063 | `pricing_source` distingue precio resuelto, precio manual justificado y legado | P0 |

### 4.8 Contratos hacia las Specs consumidoras

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-070 | Contrato `resolve_price` para 029 / 034, sin implementar sus procesos | P0 |
| FR-012-071 | Contrato de validación de descuento para 029, que dispara 045 | P0 |
| FR-012-072 | Contrato de condición y crédito para 030 / 037 | P1 |
| FR-012-073 | 012 **no** emite eventos ni notifica | P0 |

### 4.9 Legado

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-080 | Las cadenas actuales se **anotan y conservan** en `legacy_value`; no se borran | P0 |
| FR-012-081 | Una cadena ambigua **no** se convierte automáticamente: se marca para revisión | P0 |
| FR-012-082 | Los documentos históricos **no reciben snapshot inventado**: `pricing_source = LEGACY_FREETEXT` | P0 |
| FR-012-083 | La migración informa cuántas cadenas hay de cada clase y **no crea ningún maestro por su cuenta** | P0 |

### 4.10 Comisiones

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-090 | `SalesCommissionPolicy` queda **reservado** en el modelo, sin implementar | P2 |
| FR-012-091 | 012 **no** calcula comisión ni toca nómina | P0 |

---

## 5. Requisitos no funcionales

| Id | Requisito |
|---|---|
| NFR-012-01 | Resolver un precio no debe requerir recorrer todas las versiones: índice por lista, vigencia y producto |
| NFR-012-02 | Aceptación sobre **PostgreSQL 18.x** real (`P21`) |
| NFR-012-03 | WCAG 2.2 AA sin violaciones serias; sin desbordamiento horizontal entre 320 y 1440 |
| NFR-012-04 | Pantallas completas, no modales para formularios complejos (`P18`, `ADR-015`) |
| NFR-012-05 | **0 valores comerciales codificados**: verificable por comando |
| NFR-012-06 | Todo importe en `Numeric`, jamás `float` (lección de la Spec 011) |

---

## 6. Fuera de alcance — explícito

- Motor de promociones y campañas.
- Cálculo y liquidación de comisiones.
- El proceso de cotización, pedido, facturación o cobranza.
- Crédito operativo (exposición en tiempo real) — es de 030.
- Precios de compra negociados con proveedor — es de 016.
- Cualquier porcentaje, plazo o límite concreto: son **datos del cliente**.

---

## 7. La pregunta abierta

`ADR-D0-005` cierra con `OQ-06 · BUSINESS_VALIDATION_REQUIRED`: confirmación del
orden de precedencia, límites de descuento por rol, alcance de comisiones y
política de crédito.

**No bloquea esta Spec.** Precisamente porque `P8` exige que todo eso sea
**dato configurable**, la Spec especifica la capacidad de configurarlo y los
catálogos nacen vacíos. Lo que OQ-06 debe confirmar son los **valores que cargará
el cliente**, no el diseño.

Si la respuesta de negocio fuese que la precedencia debe ser fija y codificada,
entonces sí habría que reabrir — y sería una violación de `P8` que esta Spec
rechazaría.

---

## 8. Requisitos multiempresa — posteriores a ARCH-MC-001

ARCH-MC-001 cerró como `COMPLETE / GLOBALLY CONVERGED` y dejó un contrato que
esta Spec debe cumplir desde el primer día. No es una capa que se añada después:
es la forma de las tablas y de las rutas.

### 8.1 Alcance

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-001 | Toda entidad de 012 declara `__scope__` explícito | P0 |
| FR-012-MC-002 | Toda entidad sin columna de ámbito declara `__scope_authority__` | P0 |
| FR-012-MC-003 | Alcance indeterminado: **0** | P0 |
| FR-012-MC-004 | Los maestros de empresa pertenecen a una empresa **real**, con FK a `companies` | P0 |
| FR-012-MC-013 | La unicidad de negocio incluye la empresa cuando el maestro es de empresa | P0 |
| FR-012-MC-014 | Una unicidad global no se convierte mecánicamente en unicidad por empresa | P0 |
| FR-012-MC-015 | La propiedad de `PriceList` queda explícita: **empresa**, columna propia | P0 |
| FR-012-MC-016 | La propiedad de `PriceListVersion` queda explícita: derivada de su lista | P0 |
| FR-012-MC-017 | `PriceListItem` deriva su alcance de su versión | P0 |
| FR-012-MC-018 | Las derivadas **no** llevan `company_id` redundante | P0 |
| FR-012-MC-019 | Toda ruta de derivación es obligatoria y no ambigua | P0 |

### 8.2 Autoridad de la petición

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-005 | `CompanyContext` del backend es la autoridad de cada petición | P0 |
| FR-012-MC-006 | El `company_id` del cuerpo **nunca** sustituye a `CompanyContext` | P0 |
| FR-012-MC-007 | El `parent_id` de la URL **nunca** sustituye a `CompanyContext` | P0 |
| FR-012-MC-008 | Toda escritura hija resuelve y valida su padre contra `CompanyContext` | P0 |
| FR-012-MC-009 | Toda lectura hija valida su padre contra `CompanyContext` | P0 |
| FR-012-MC-010 | El acceso a un padre de otra empresa se bloquea **sin revelar su existencia** | P0 |
| FR-012-MC-011 | El acceso entre tenants se bloquea | P0 |
| FR-012-MC-012 | El respaldo Tenant→Company está prohibido | P0 |
| FR-012-MC-048 | Toda operación hija valida la autoridad de su padre | P0 |
| FR-012-MC-049 | Ningún endpoint hijo opera solo porque el UUID del padre exista | P0 |

`FR-012-MC-049` no es una cautela teórica. N10 encontró nueve rutas que hacían
exactamente eso y las corrigió; la 012 es la Spec con más rutas hijas del
sistema.

### 8.3 Coherencia con los maestros vigentes

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-020 | El alcance de Producto que usa 012 coincide con el modelo final: **empresa** | P0 |
| FR-012-MC-021 | El alcance de Tercero que usa 012 coincide con el modelo final: **empresa** | P0 |
| FR-012-MC-029 | El alcance de Moneda coincide con la baseline final: **empresa** | P0 |
| FR-012-MC-030 | El alcance de Tasa de cambio coincide con la baseline final: **empresa** | P0 |
| FR-012-MC-022 | La unidad respeta la Spec 011, incluida la unidad de plataforma con empresa nula | P0 |
| FR-012-MC-023 | La presentación respeta la Spec 011 | P0 |
| FR-012-MC-024 | Conversión física y presentación comercial siguen separadas | P0 |
| FR-012-MC-025 | Una lista puede usar presentación comercial **sin** redefinir el factor físico | P0 |

### 8.4 Histórico

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-026 | Una versión emitida no se reinterpreta con maestros actuales | P0 |
| FR-012-MC-027 | Un borrador **sí** resuelve contra las reglas vigentes | P0 |
| FR-012-MC-028 | Un documento congelado conserva su snapshot comercial | P0 |

### 8.5 Lo que 012 no duplica

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-031 | No introduce lectura dual de pertenencia | P0 |
| FR-012-MC-032 | No introduce escritura dual de pertenencia | P0 |
| FR-012-MC-039 | Usa la Spec 045 cuando una regla comercial exige aprobación | P0 |
| FR-012-MC-040 | No crea un segundo motor de aprobación | P0 |
| FR-012-MC-041 | No crea un segundo maestro de monedas | P0 |
| FR-012-MC-042 | No crea un segundo motor de unidades | P0 |
| FR-012-MC-043 | No crea una segunda autoridad de empresa | P0 |
| FR-012-MC-050 | No revive ninguna semántica superada por ARCH-MC-001 | P0 |

### 8.6 Contrato de API y permisos

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-033 | Las operaciones de empresa publican `X-Kontrol-Company` en OpenAPI | P0 |
| FR-012-MC-034 | Con una sola empresa se conserva la resolución automática | P0 |
| FR-012-MC-035 | Con varias y sin contexto se devuelve el error contractual vigente | P0 |
| FR-012-MC-036 | Tener permiso no equivale a tener acceso a una empresa | P0 |
| FR-012-MC-037 | `UserRole` no permite cruzar empresas | P0 |
| FR-012-MC-038 | La auditoría registra tenant, empresa y actor correctos | P0 |
| FR-012-MC-044 | Ninguna respuesta expone datos comerciales de otra empresa | P0 |

### 8.7 Frontend

| Id | Requisito | Prioridad |
|---|---|---|
| FR-012-MC-045 | Las claves de consulta incluyen la identidad de empresa | P0 |
| FR-012-MC-046 | El formulario queda fijado a la empresa con la que se abrió | P0 |
| FR-012-MC-047 | Cambiar de empresa con el formulario sucio no redirige la mutación | P0 |
