# NUMERACIONES Y ALCANCE DE IDEMPOTENCIA — N7

## 1. No hay secuencias físicas

Las claves primarias son UUID, así que PostgreSQL no gestiona ninguna secuencia.
Concluir de ahí que «no hay numeración» sería equivocarse: los correlativos
existen, son lógicos y viven en columnas.

## 2. Inventario

| Dominio | Numeración | Alcance | Autoridad | Aislamiento A/B |
|---|---|---|---|---|
| Fiscal | Correlativo de serie | Empresa | `fiscal_number_series.company_id` | probado en N5 |
| Fiscal | Números de control | Empresa, por lote | `control_number_batches.company_id` | probado en N5 |
| Compras | Código de orden | Empresa | `company_id` + `code` | probado |
| Compras | Número de factura de proveedor | Empresa + proveedor | UNIQUE de cuatro columnas | probado |
| Compras | Código de recepción | Empresa | `company_id` + `code` | probado |
| Ventas | Código de orden | Empresa | `company_id` + `code` | probado |
| Ventas | Número de factura | Empresa | `company_id` | probado |
| Tesorería | Códigos de pago, cobro y conciliación | Empresa | `company_id` + `code` | probado |
| Inventario | Códigos de conteo y transferencia | Empresa | `company_id` + `code` | probado |

**Conflictos entre empresas: 0.** Ninguna numeración puede solaparse, porque
cada correlativo cuelga de una fila que pertenece a una sola empresa por clave
foránea obligatoria.

## 3. Idempotencia

N5 encontró contaminación en tres sitios: facturas de venta, facturas de
proveedor y movimientos de inventario. La búsqueda por clave no acotaba empresa,
así que A pedía con una clave que B había usado y recibía el objeto de B.

Se corrigió acotando la consulta. **N7 no añade una restricción de unicidad
sobre `(company_id, idempotency_key)`**, y conviene decir por qué: la clave es
opcional, y una restricción de unicidad sobre columnas nulas no impide lo que
aquí importaba —que la *lectura* devolviera el objeto de otra empresa—. La
corrección correcta era la de la consulta, y ya está aplicada con sus pruebas.

Registrar una restricción que no aporta garantía sería añadir ruido estructural
para que la fase pareciera más completa.
