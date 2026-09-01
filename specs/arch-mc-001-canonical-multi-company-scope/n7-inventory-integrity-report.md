# INTEGRIDAD DE INVENTARIO — N7

## 1. Estructura

Almacenes, ubicaciones, movimientos, saldos, lotes, seriales, conteos,
transferencias, capas de costo y reservas: todos con la empresa referenciada.

La estructura interna del almacén —zonas, pasillos, estanterías, niveles y
ubicaciones— tiene además **clave compuesta**: el par (empresa, almacén) debe
existir tal cual en `warehouses`.

## 2. El par que podía contradecirse

Esas cinco tablas guardan `company_id` y `warehouse_id`. Cada columna tenía su
clave y las dos eran válidas por separado, así que nada impedía que una zona
dijera pertenecer a la empresa A y colgara de un almacén de la B. Ninguna
referencia estaba mal; la combinación sí.

Resuelto con una clave foránea compuesta contra `warehouses(company_id, id)`. No
añade columnas —ambas ya existían— y no usa disparadores, que serían lógica
escondida en la base para algo que el modelo relacional expresa por sí solo.

Comprobado: una zona de A sobre un almacén de B se rechaza con `23503`; la misma
zona sobre su propio almacén se acepta.

## 3. Un defecto que la fase destapó

`_get_movement_type_by_code_optional` buscaba **solo por código**, ignorando el
parámetro `company_id` que ya recibía. El tipo «ENTRADA» que creara una empresa
lo consumía la siguiente que moviera existencias, y el tipo «REVERSO» se
autocreaba sin empresa.

Corregido: cada empresa tiene su catálogo, con preferencia por el suyo y
respaldo en el global cuando existe.

Ese respaldo importa. El primer arreglo acotó estrictamente por empresa y rompió
ventas y compras, porque la API expone `global_scope`: un interruptor que crea
el tipo para toda la instalación. La primera lectura fue que los fixtures
estaban mal; leyendo el contrato resultó ser al revés.

## 4. Transferencias entre empresas

Siguen bloqueadas en el servicio, no en la estructura. Una transferencia con
origen en A y destino en B tiene dos referencias válidas: la regla es sobre la
combinación, y sigue siendo del dominio.

No se implementa ninguna capacidad intercompany.
