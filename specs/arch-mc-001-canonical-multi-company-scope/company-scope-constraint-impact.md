# IMPACTO SOBRE RESTRICCIONES E ÍNDICES — ARCH-MC-001

## 1. Únicos que ya incluyen `company_id`

13 en el modelo. Al pasar de tenant a empresa, su alcance **se estrecha**: lo que
era único en el tenant pasa a serlo en la empresa.

| Tabla | Columnas | Efecto | Veredicto |
|---|---|---|---|
| `approval_policies` | company, process_type, version | Ya es empresa real (Spec 045) | Sin cambio |
| `approval_requests` | company, document_type, document_id, fingerprint | Ya es empresa real | Sin cambio |
| `document_categories` · `document_types` | company, code | Ya es empresa real (Spec 046) | Sin cambio |
| `documents` | company, tipo, número | Ya es empresa real | Sin cambio |
| `location_types` · `zone_types` · `warehouses` | company, code | Ya es empresa real (Spec 008) | Sin cambio |
| `supplier_invoices` | company, proveedor, número, control | Se estrecha | **Correcto**: dos empresas pueden recibir la misma factura del mismo proveedor |
| `inventory_lots` | company, producto, lote | Se estrecha | **Correcto**: el stock no se mezcla |
| `product_serials` | company, serial | Se estrecha | **Correcto** |
| `movement_types` | company, code | Se estrecha | **Correcto**: catálogo operativo de cada empresa |
| `units_of_measure` | company, code | Se estrecha | **Requiere decisión** — `OQ-MC-01` |

## 2. El caso que hay que decidir

`units_of_measure` es hoy único por tenant. Si pasa a empresa, cada empresa
necesita su propio «KG» y la conversión de la Spec 011 opera dentro de cada una.

Ambas lecturas son defendibles: el kilogramo es universal, pero una unidad de
venta propia («caja de 12») puede ser de una empresa. **No se decide aquí**
(`OQ-MC-01`); la ola correspondiente no se ejecuta sin respuesta.

## 3. Secuencias fiscales

Ningún único acota hoy el correlativo: la clave primaria de
`fiscal_number_series`, `control_numbers` y `control_number_batches` es solo `id`.

El alcance correcto —empresa, establecimiento, tipo de documento, serie— se lee
de la normativa y del modelo fiscal existente, **no se inventa** (`FR-MC-063`).
Es trabajo de la ola fiscal, con el especialista fiscal.

> Sin restricción de unicidad, hoy nada impide en la base que dos series de la
> misma empresa emitan el mismo número. Que no haya ocurrido no es una garantía.

## 4. Índices nuevos

Acotar por empresa cambia los planes. Criterio:

- **No** se crea un índice por `company_id` en cada tabla por reflejo.
- Se revisa con `EXPLAIN` sobre las tablas con volumen real.
- Se prefiere el **compuesto** encabezado por `company_id` cuando la consulta ya
  filtra por otra columna.
- Las derivadas no reciben índice de empresa: no tienen la columna.

## 5. Claves foráneas

| Regla | Resultado |
|---|---|
| Columna llamada `company_id` | FK real a `companies.id` |
| Columna llamada `tenant_id` | FK real a `tenants.id` |
| Integridad que PostgreSQL puede garantizar | La garantiza PostgreSQL, no el servicio |

Hoy: 17 de 107 columnas `company_id` tienen FK. Objetivo: **todas**.
