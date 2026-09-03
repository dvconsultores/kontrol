# SPEC 030 — CHECKPOINT FINAL

## Veredicto

`SPEC 030 — COMPLETE / CONVERGED`

## Qué se pidió y qué se hizo

Convertir el pedido en borrador que entrega la Spec 029 en un pedido comercial comprometido,
aplicando la decisión que D0-03 dejó cerrada: **la reserva nace al confirmar el pedido**. Se hizo
sin reabrir la decisión, sin crear una segunda Spec, sin duplicar el motor de inventario ni el de
aprobaciones y sin inventar un planificador.

## Baseline, medida con el mismo instrumento antes y después

| Métrica | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 177 · 177 | 177 · 177 |
| Claves foráneas | 371 | 373 |
| Migraciones | 42 | 43 |
| Rutas · operaciones | 311 · 429 | 318 · 437 |
| Operaciones con contrato de empresa | 367 | 375 |

Ninguna tabla nueva. Las dos claves foráneas son la identidad que le faltaba a la reserva: de qué
pedido y de qué línea viene.

## La decisión, hecha código

`DRAFT → SUBMITTED` reserva. Todo o nada, en unidad base, con el saldo bloqueado en PostgreSQL
mientras se decide. Sin política de crédito el pedido sigue hasta `RELEASED` en la misma
transacción; con ella espera en `SUBMITTED` y la Spec 045 resuelve. Rechazar, revertir, cancelar y
expirar liberan de forma atómica. Despachar consume. `RELEASED` es lo que la Spec 031 recibirá.

## La prueba que el documento pedía

Disponible 10, dos pedidos de 8, dos conexiones reales a PostgreSQL con barrera: uno reserva y el
otro recibe `409`. El reservado termina en 8. Nunca en 16. Con `allow_negative` los dos entran, uno
marcado como sobreventa, y los contadores siguen íntegros.

## Regresión

| Compuerta | Resultado |
|---|---|
| Backend completo (PostgreSQL 18.6 · ClamAV 1.4.3) | **831 pruebas · 823 pasadas · 8 saltadas · 0 fallos · 0 errores** |
| — de ellas, nuevas de la Spec 030 | **56** (11 estructurales, 26 funcionales multiempresa, 2 de carrera, 10 hostiles de integridad, 7 de migración) |
| Saltos | los 8 de `test_documents_storage.py`: S3 sin servicio real, dependencia externa P1 ya declarada |
| Frontend | 283/283 · `tsc` · ESLint · build |
| Extremo a extremo | 12/12 en Chromium, Firefox y WebKit · axe 22/22 · recorrido de rutas 1/1 |
| Instalación limpia | subir a cabeza, bajar la `0043`, volver a subir: sin errores |
| Contrato de rutas | 437 operaciones, fixture del frontend cuadrado al detalle |

## Deuda propia

**Ninguna P0.** Los catorce hechos que la auditoría de D0-03 había levantado están cerrados uno por
uno, cada uno con una prueba que falla si vuelve.

## Anotado para otras Specs

- La línea de pedido no modela todavía lote ni serial exigidos por el cliente. La reserva ya sabe
  transportarlos cuando la Spec 024 los añada.
- No hay outbox transversal; la auditoría es la fuente de los cuatro eventos de reserva. Si la
  Spec 047 lo introduce, ese es el punto de conexión.
- `test_mc_preflight.py` decide saltar comparando un mensaje de error traducible. En un entorno sin
  base legado y con PostgreSQL en español falla en vez de saltar. No se tocó: es del preflight
  multiempresa.

## Lo que sigue

La cadena de preparación. Las Specs 031 y 032 ya reciben pedidos en `RELEASED` con sus reservas
vinculadas por línea, pero siguen esperando a la 022 (put-away), que a su vez espera a la 021 y a la
020. Esa es la cadena que el próximo checkpoint maestro tendrá que ordenar.
