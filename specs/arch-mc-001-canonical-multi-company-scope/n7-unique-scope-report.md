# UNICIDAD POR ALCANCE — N7

## 1. Son 31, no 13

El «13» que arrastraba la documentación era una estimación anterior a N3. El
número real medido en el catálogo es **31** restricciones de unicidad además de
las claves primarias, más la que N7 añade como destino compuesto: **32**.

## 2. Distribución

| Alcance | Cuántas | Ejemplos |
|---|---:|---|
| Por empresa | 11 | `warehouses(company_id, code)`, `document_types(company_id, code)`, `units_of_measure(company_id, code)`, `supplier_invoices(company_id, supplier_id, invoice_number, control_number)` |
| Por padre de empresa | 10 | `warehouse_zones(warehouse_id, code)`, `document_versions(document_id, version_number)` |
| Por identidad de tercero o artículo | 6 | `customers(party_id)`, `suppliers(party_id)`, `products(item_id)` |
| Global legítima | 4 | `feature_flags(key)`, `stored_files(storage_key)`, `unit_conversions(from_unit_id, to_unit_id)` |
| Añadida por N7 | 1 | `warehouses(company_id, id)`, destino de la clave compuesta |

## 3. Ninguna se cambió, y esa es la conclusión

Las once que debían ser de empresa **ya lo son**, porque N3 las creó así. Las de
padre heredan el alcance por la cadena, que es correcto y no redundante.

Cambiar una restricción correcta para que la fase parezca más grande sería
trabajo inventado. Lo que N7 aporta aquí no es una migración: es la prueba de
que se comportan como dicen.

## 4. Lo que se comprueba, sobre PostgreSQL

| Caso | Resultado |
|---|---|
| Mismo código de almacén en la empresa A y en la B | **aceptado** |
| Mismo código repetido dentro de la empresa A | **rechazado**, `23505` |

La primera importa tanto como la segunda: si la unicidad fuera global, la
segunda empresa no podría usar su propia codificación, y eso es una regla de
negocio rota tanto como la duplicación.

## 5. Colisiones

**0.** Ninguna clave existente entra en conflicto con el alcance declarado.
