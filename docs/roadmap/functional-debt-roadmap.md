# DEUDA FUNCIONAL — PROCESOS PARCIALMENTE IMPLEMENTADOS

| ID | Proceso | Etapas exigidas | Etapas cubiertas | Rompe en | Spec |
|---|---|---:|---:|---|---|
| DF-01 | Importación | 12 | 0 | Primera etapa (detección de necesidad con rotación) | 018 |
| DF-02 | Recepción física | 12 (8 de 019) | 8 de 8 | — **cerrado 2026-09-03** | 019 |
| DF-03 | Incidencias de recepción | 9 | 0 | Registro de faltante/sobrante/daño | 020 |
| DF-04 | Confirmación de inventario recibido | 11 | 2 | Conteo detallado por SKU | 021 |
| DF-05 | Put-away | 10 | 0 | Determinación de zona | 022 |
| DF-06 | Toma del pedido | 7 | 4 | Condiciones comerciales desde maestro | 029 |
| DF-07 | Cola y ruta de picking | 10 | 0 | Recepción del pedido en almacén | 031 |
| DF-08 | Preparación física y consolidación | 12 | 2 | Llegada a la ubicación indicada | 032 |
| DF-09 | Confirmación de pedido | 8 | 0 | Recepción en área de confirmación | 033 |
| DF-10 | Liberación y facturación | 9 | 4 | Autorización de facturación | 034 |
| DF-11 | Despacho | 6 | 4 | Verificación preparado+confirmado+facturado | 035 |
| DF-12 | Devolución de venta | 6 | 4 | Inspección previa al reingreso | 036 |
| DF-13 | Retenciones | 7 | 4 | Conceptos ISLR cargados; enteramiento | 040 |
| DF-14 | Aprobaciones transversales | 8 | 3 | Bandeja única y delegación | 045 |
| DF-15 | Notificaciones y tareas | 6 | 0 | Toda la cadena | 047 |
| DF-16 | Planificación de abastecimiento | 6 | 3 | Revisión de rotación y demanda | 015 |

## Concentración de la deuda

De las 137 etapas de proceso documentadas, **30 están cubiertas (22 %)**.

La deuda se concentra en dos tramos contiguos:

- **Entrada de mercancía** (DF-01 a DF-05): 52 etapas exigidas, **5 cubiertas (10 %)**.
- **Salida de mercancía** (DF-07 a DF-11): 45 etapas exigidas, **10 cubiertas (22 %)**.

Lo que hoy funciona bien —maestros, órdenes, inventario contable, CxC/CxP, tesorería, fiscal— es
la capa **administrativa**. Lo que falta es la capa **operativa de almacén**: exactamente lo que
los dos documentos de proceso de agosto describen y ninguna Spec recogió.

## Implicación para el roadmap

No es un conjunto de huecos dispersos: es un bloque coherente. Construir 008 (ubicaciones reales),
011 (unidades en transacción), 020/021/022 (recepción→confirmación→put-away) y 031/032/033
(cola→picking→confirmación) cierra el 78 % de la deuda funcional con un modelo de datos común.
