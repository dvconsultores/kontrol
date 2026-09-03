# DEUDA FUNCIONAL — PROCESOS PARCIALMENTE IMPLEMENTADOS

| ID | Proceso | Etapas exigidas | Etapas cubiertas | Rompe en | Spec |
|---|---|---:|---:|---|---|
| DF-01 | Importación | 12 | 0 | Primera etapa (detección de necesidad con rotación) | 018 |
| DF-02 | Recepción física | 12 | 11 | Clasificación y ubicación (etapa 12) | 019 (8) · 020 (3) · 022 (1) |
| DF-03 | Incidencias de recepción | *(3, dentro de DF-02)* | 3 de 3 | — **cerrado 2026-09-03** | 020 |
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

## Dos correcciones de conteo (2026-09-03)

Las cifras anteriores no cuadraban con su propia tabla y se corrigen aquí:

1. **DF-03 no era un proceso aparte.** Sus etapas son la 8, la 9 y la 10 de la recepción física
   —las que el DOCX §2 asigna a la Spec 020—, ya contadas dentro de las 12 de DF-02. Las nueve
   que la fila declaraba no salen de ninguna fuente: se contaban dos veces, y de más. DF-03 queda
   como puntero al tramo de DF-02 que gobierna la 020, sin conteo propio.
2. **Los totales en prosa estaban obsoletos.** Decían 137 exigidas y 30 cubiertas; la tabla sumaba
   139 y 38. Los de abajo se recalculan **desde la tabla**, no desde el párrafo anterior.

## Concentración de la deuda

De las **130 etapas** de proceso documentadas, **41 están cubiertas (32 %)**.

La deuda se concentra en dos tramos contiguos:

- **Entrada de mercancía** (DF-01, DF-02, DF-04, DF-05): 45 etapas exigidas, **13 cubiertas (29 %)**.
- **Salida de mercancía** (DF-07 a DF-11): 45 etapas exigidas, **10 cubiertas (22 %)**.

Lo que hoy funciona bien —maestros, órdenes, inventario contable, CxC/CxP, tesorería, fiscal— es
la capa **administrativa**. Lo que falta es la capa **operativa de almacén**: exactamente lo que
los dos documentos de proceso de agosto describen y ninguna Spec recogió.

## Implicación para el roadmap

No es un conjunto de huecos dispersos: es un bloque coherente. Con 011 (unidades en transacción),
019 (recepción física) y 020 (incidencias) cerradas, lo que queda del tramo de entrada es 021
(confirmación), 022 (put-away) y 008 (ubicaciones reales); el de salida sigue entero en 031/032/033
(cola→picking→confirmación). Ese conjunto cierra el grueso de la deuda con un modelo de datos común.

**La entrada de mercancía ya no rompe en la primera etapa.** Rompe en la etapa 12, la ubicación:
la mercancía se recibe, se inspecciona, se incidencia y se escala; lo que todavía no sabe hacer el
sistema es decir **dónde** quedó.
