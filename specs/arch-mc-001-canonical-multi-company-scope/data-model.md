# MODELO DE DATOS — ARCH-MC-001

## 1. La cadena canónica

```
Installation ─ Tenant ─┬─ Company A ─┬─ Branch ─ Establishment ─ Warehouse ─ …
                       │             └─ Branch
                       ├─ Company B ─── Branch
                       └─ Company C
```

`tenant_id` → `tenants.id`. `company_id` → `companies.id`. `branch_id` →
`branches.id`. Sin excepciones sin documentar (`FR-MC-001`).

## 2. Acceso usuario–empresa

**No se crea entidad nueva.** Se usa lo que existe:

| Estructura | Hoy | Objetivo |
|---|---|---|
| `user_scopes.company_id` | Existe, anulable, **sin uso** para esto | Autoridad de acceso; FK real |
| `user_roles.company_id` | Existe, anulable | Permiso acotado a empresa; FK real |

Semántica: `company_id` nulo significa **todas las empresas del tenant**; con
valor, solo esa. Es la convención que la columna ya insinúa.

## 3. `CompanyContext`

Resuelto por dependencia en cada petición de alcance de empresa:

| Campo | Origen |
|---|---|
| `tenant_id` | Token |
| `user_id` | Token |
| `company_id` | Cabecera `X-Kontrol-Company`, **validada** |
| `company` | Cargada, del tenant y activa |
| `branch_scope` | `user_scopes`, cuando lo hay |
| `permissions` | Servicio de identidad |

Validación, en orden: la empresa existe → es del tenant → el usuario accede → la
licencia lo permite → está activa. Si algo falla: **404**, sin confirmar
existencia (`FR-MC-022`).

Sin cabecera: si el usuario accede a una sola empresa, se resuelve sola; si a
varias, se rechaza.

## 4. Metadatos de alcance en el ORM

Cada modelo declara su alcance, y una prueba de arquitectura lo comprueba:

```python
class PurchaseOrder(Base, CompanyScoped):        # DIRECT
    __scope__ = Scope.COMPANY

class PurchaseOrderLine(Base):                   # DERIVED
    __scope__ = Scope.COMPANY
    __scope_authority__ = "order_id → purchase_orders"
```

No es decoración: `test_all_persistent_models_have_declared_scope` falla sin ella
(`FR-MC-003`, `FR-MC-004`).

## 5. Recuento del modelo objetivo

| Alcance | Tablas | Forma |
|---|---:|---|
| `COMPANY_SCOPE` | **133** | 97 directas · 36 derivadas |
| `TENANT_SCOPE` | 14 | — |
| `INSTALLATION_SCOPE` | 16 | — |
| `GLOBAL_SCOPE` | 3 | — |
| **Total** | **166** | |

Las 36 derivadas lo hacen por FK **obligatoria**. Ninguna por FK anulable.

## 6. Campos de transición

Durante N3–N8, las tablas que hoy guardan el tenant conservan el valor original:

| Campo | Vida |
|---|---|
| `company_id` (heredado, texto) | Se renombra a `legacy_scope_id` en N3 |
| `company_id` (nuevo, FK) | Nace anulable en N3; `NOT NULL` en N7 |
| `scope_backfill_class` | `MC-A`..`MC-E`; se retira en N8 |

Los tres desaparecen en N8. **No hay modo dual permanente** (`FR-MC-057`).

## 7. Restricciones que cambian de significado

13 índices únicos incluyen `company_id`. Al pasar de tenant a empresa, su alcance
se estrecha:

| Tabla | Único | Efecto |
|---|---|---|
| `supplier_invoices` | `(company, proveedor, número, control)` | **Correcto y más permisivo**: dos empresas pueden recibir la misma factura |
| `warehouses`, `document_types`, `movement_types`, `location_types`, `zone_types` | `(company, code)` | Correcto: el código es local a la empresa |
| `inventory_lots`, `product_serials` | `(company, …)` | Correcto: el stock no se mezcla |
| `units_of_measure` | `(company, code)` | **Requiere decisión** — `OQ-MC-01` |

## 8. Índices nuevos

Acotar por empresa cambia los planes. Se revisan con `EXPLAIN` sobre las tablas
grandes, y se crean **compuestos** encabezados por `company_id` solo donde la
consulta real lo justifique. No se indexa por reflejo (`NFR-MC-02`).
