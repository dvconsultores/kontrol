# GATE DE ARQUITECTURA MULTIEMPRESA — AUDITORÍA Y DECISIÓN

Fecha: 2026-08-31 · Origen: hallazgo de `REM-046-001` · **Auditoría, sin cambios de código**

---

## 1. La pregunta

> ¿KONTROL pierde granularidad y separación entre empresas por usar `tenant_id`
> en campos denominados `company_id`?

**Sí.** Y no es una deuda de nomenclatura: es un **defecto funcional multiempresa**
con consecuencias fiscales. Sigue la evidencia.

---

## 2. Evidencia — no se asumió nada

### 2.1 El sistema permite dos empresas por tenant

El plan del tenant es `MONO_COMPANY` por defecto, pero `POST /organization/companies`
**no lo comprueba**. Creada la segunda empresa:

```
crear segunda empresa -> 200
  Empresa A = 8c779a9a-…
  Empresa B = 51d8d6c0-…
  empresas en el tenant: 2   (plan del tenant: MONO_COMPANY)
```

La restricción existe en la documentación del código, no en el código.

### 2.2 El dato de negocio no pertenece a ninguna de las dos

Creando un tercero por la API real:

```
parties.company_id guardado = e79382e2-…
  ¿= Empresa A?  False
  ¿= Empresa B?  False
  ¿= tenant_id?  True
```

### 2.3 Y no se puede ni filtrar por empresa

```
GET /maestros/terceros → el endpoint no admite `company_id`
```

El alcance es el tenant entero. Dos empresas del mismo tenant **comparten toda la
cartera de terceros**, y el sistema no ofrece forma de separarlas.

### 2.4 Lo que sí funciona

Las Specs cerradas con rigor usan FK real a `companies`:

```
almacén en A -> 200 | almacén en B -> 200
  almacenes visibles filtrando por A: 1
  almacenes visibles filtrando por B: 1
```

La Spec 008 separa correctamente. La diferencia no es de criterio: es de época.

### 2.5 El código lo sabía

`organization/service.py:35`:

> «Los módulos de negocio (ventas, compras, inventario) usan el `tenant_id` del
> usuario como alcance (`company_id`) […] **En el modelo MONO_COMPANY el tenant
> tiene una sola empresa**, por lo que este helper reconcilia ambos identificadores.»

Es una simplificación deliberada, documentada y **válida solo mientras nadie cree
una segunda empresa**. Nada impide crearla.

---

## 3. Alcance medido

| Métrica | Valor |
|---|---:|
| Tablas del modelo | 166 |
| Con columna `company_id` | 107 |
| **Con FK real a `companies`** | **17** |
| **Sin FK — contienen `tenant_id`** | **90** |
| De ellas, legítimamente del tenant | 8 |
| **De ellas, que deben ser de empresa** | **82** |

### 3.1 Las 17 correctas

`branches` · `approval_requests` · `approval_policies` · `approval_delegations` ·
`warehouses` · `warehouse_zones` · `warehouse_aisles` · `warehouse_racks` ·
`warehouse_levels` · `warehouse_locations` · `zone_types` · `location_types` ·
`documents` · `document_versions` · `document_links` · `document_types` ·
`document_categories`

Es decir: **Specs 008, 045 y 046**. Las tres cerradas con `COMPLETE_100`.

### 3.2 Las 82 incorrectas, por módulo

| Módulo | Tablas | Gravedad |
|---|---:|---|
| **fiscal** | **11** | **Crítica — ver §4** |
| purchasing | 14 | Alta |
| inventory | 11 | Alta |
| regulatory | 11 | Alta |
| treasury | 11 | Alta |
| master_data | 10 | Alta |
| sales | 8 | Alta |
| reporting | 2 | Media |
| identity_access | 2 | Media |
| approvals | 1 | Baja (`approval_events`) |
| documents | 1 | Baja (`stored_files`) |

### 3.3 Las 8 legítimamente del tenant

`currencies` · `exchange_rates` — tasas nacionales, no de una empresa ·
`idempotency_records` · `outbox_events` — infraestructura de petición ·
`report_definitions` — plantilla compartida · `roles` — global o de empresa,
anulable · `audit_events` — ya lleva `tenant_id` **y** `company_id` ·
`legacy_document_references` — anotación de migración.

Estas **no** requieren cambio. Deben quedar declaradas como `TENANT_SCOPED`.

---

## 4. Por qué esto es un defecto y no una deuda

El módulo **fiscal** asigna con `actor.tenant_id`:

```python
fiscal_service.create_number_series(db, company_id=actor.tenant_id, …)   # api.py:278
fiscal_service.create_control_batch(db, company_id=actor.tenant_id, …)   # api.py:298
fiscal_service.emit_document(db,       company_id=actor.tenant_id, …)   # api.py:353
fiscal_service.register_print(db,      company_id=actor.tenant_id, …)   # api.py:363
```

En Venezuela cada empresa tiene su **propio RIF** y, por ley, su propia serie de
numeración, sus propios números de control autorizados por el SENIAT, sus propios
períodos y libros, y sus propias declaraciones.

Con dos empresas en un tenant compartirían:

| Tabla | Qué se comparte | Consecuencia |
|---|---|---|
| `fiscal_number_series` | El correlativo de factura | Numeración entrelazada entre dos RIF |
| `control_number_batches` · `control_numbers` | Los números de control del SENIAT | Consumo cruzado de un rango autorizado a otra empresa |
| `fiscal_periods` | Los períodos y libros | Libro de ventas con facturas de dos contribuyentes |
| `fiscal_documents` | Las facturas emitidas | — |
| `tax_return_batches` | Las declaraciones | Declaración que mezcla bases imponibles |

Ninguna de esas tablas tiene además restricción de unicidad que acote el
correlativo: la clave primaria es solo `id`.

Esto contradice el **Principio 4** (núcleo fiscal separado y versionado) y haría
inválidos los libros. No es «funciona por ahora»: es que **no funcionaría** en el
primer tenant con dos empresas.

---

## 5. Reconstruibilidad — y por qué hay prisa

| Situación del tenant | ¿Se puede deducir la empresa de una fila? |
|---|---|
| **1 empresa** | **Sí, con certeza**: `tenant_id → esa única empresa` |
| **2 o más empresas** | **No.** La fila no dice a cuál pertenece |

Hoy toda instalación nace con una empresa, así que el backfill es **determinista**.
Pero el sistema permite crear la segunda sin ninguna barrera, y desde el instante
en que una instalación tenga dos empresas y opere con ambas, **la información deja
de ser reconstruible para siempre**.

No es que el dato se pierda: es que **nunca se captura** (`P23`). Es exactamente la
forma de la deuda que cerró la Spec 011 con las unidades, y que el `ADR-D0-009`
describió como «la deuda que más rápido se encarece».

**La ventana de corrección determinista está abierta y se cierra sola.**

---

## 6. Lo que Opción A realmente exige

No es un renombrado con backfill. Falta una pieza de arquitectura:

> **El backend no sabe en qué empresa opera el usuario.**

- `UserScope.company_id` existe y **no se usa** para esto.
- El frontend mantiene `activeCompany` en `localStorage` y **nunca la envía**.
- No hay cabecera, ni claim en el token, ni resolución por alcance.

Por eso hoy se usa `tenant_id`: es el único identificador de ámbito que el
backend tiene a mano en cada petición.

Opción A requiere, en este orden:

1. Establecer el **contexto de empresa por petición** (claim, cabecera o alcance).
2. Resolverlo y validarlo contra los alcances del usuario.
3. Migrar las 82 tablas a `Company.id` con FK real, con backfill determinista
   mientras cada tenant tenga una empresa.
4. Cambiar los ~90 puntos de `actor.tenant_id` a la empresa del contexto.
5. Imponer el plan `MONO_COMPANY` o habilitar de verdad el multiempresa.

Es una Spec, no una remediación puntual.

---

## 7. Decisión

### Lo que está en juego si se sigue con 012 primero

La Spec 012 crea **nueve tablas** —listas de precios, versiones, ítems,
condiciones, zonas, canales, políticas de descuento y de crédito, condiciones del
cliente— y todas son inequívocamente **de empresa**: dos empresas del mismo grupo
tienen listas de precios distintas, plazos distintos y límites de crédito
distintos. Es su razón de ser.

Implementarla sobre el modelo actual añadiría **9 tablas más** al mismo defecto, y
lo haría en el dominio donde más se nota: el precio.

### Veredicto

> **`GATE MULTIEMPRESA — DEFECTO FUNCIONAL CONFIRMADO`**
>
> **Se recomienda ejecutar la normalización estructural (Opción A) ANTES de la Spec 012.**

Razones, en orden de peso:

1. **Integridad fiscal.** Correlativos y libros compartidos entre RIF distintos no
   son un defecto estético.
2. **La ventana se cierra sola.** El backfill es determinista hoy y deja de serlo
   en cuanto alguien cree la segunda empresa.
3. **012 agravaría el problema** en nueve tablas del dominio comercial.
4. **El producto ya promete multiempresa**: hay selector de empresa activa en la
   interfaz. Prometer separación que el dato no sostiene es peor que no ofrecerla.

### Lo que NO se recomienda

- **No** aceptar el apaño de que `ResourceKind` declare el ámbito de cada
  consumidor. Haría funcionar 046 sobre una arquitectura que sigue sin distinguir
  empresas. Es «funciona por ahora», que este Gate excluye.
- **No** normalizar las 8 tablas legítimamente del tenant.
- **No** implementar el multiempresa completo si el negocio decide que KONTROL es
  mono-empresa: en ese caso la corrección es **imponer** `MONO_COMPANY` y renombrar
  la columna a lo que de verdad significa. Eso también cierra el defecto, y es
  mucho más barato. **Requiere decisión de producto.**

---

## 8. La pregunta que debe responder negocio

> ¿KONTROL vende multiempresa por tenant, o una empresa por tenant?

| Respuesta | Corrección |
|---|---|
| **Multiempresa** | Opción A completa: contexto de empresa + 82 tablas + FK + backfill |
| **Una empresa por tenant** | Imponer el plan, renombrar la columna a `tenant_id`, y dejar `company_id` solo donde hay FK real |

Las dos son arquitectónicamente correctas. La actual —prometer lo primero y
sostener lo segundo— no lo es.

El roadmap y la interfaz apuntan a multiempresa; la baseline lo declara en su
cadena `Installation → Tenant → Company → Branch`. Pero es una decisión de
producto y **no la tomo yo**.

---

## 9. Estado de las Specs afectadas

| Spec | Efecto del hallazgo |
|---|---|
| **008** | Sin efecto. Usa FK real; separa correctamente |
| **045** | Sin efecto en su modelo. `approval_events` queda por revisar |
| **046** | `REM-046-001` sigue **BLOCKED**: su registro no puede repararse sin resolver esto antes |
| **011** | Sin efecto directo: las unidades no son de empresa |
| **012** | **No debe implementarse** antes que la normalización |
