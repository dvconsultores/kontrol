# SPEC 019 — CHECKPOINT FINAL

## Veredicto

`SPEC 019 — COMPLETE / CONVERGED`

## Lo primero fue corregir la cuenta

Cuatro artefactos repetían «Recepción física: 10 etapas» y la matriz de procesos listaba nueve. El
DOCX que todos citan tiene **doce**, y solo ocho son de esta Spec. La cifra se había copiado entre
documentos sin volver a la fuente. Corregida en los cinco.

## Baseline, mismo instrumento antes y después

| Métrica | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 177 · 177 | 177 · 177 |
| Migraciones | 43 | 44 |
| Rutas · operaciones | 318 · 437 | 321 · 440 |
| Operaciones con contrato de empresa | 375 | 378 |

Ninguna tabla nueva: la recepción ya existía y lo que le faltaba eran columnas y proceso.

## El defecto que no estaba donde parecía

El checkpoint operativo situó el riesgo en la línea de recepción, que no capturaba presentación. Al
implementar apareció la causa un nivel más abajo: `record_movement` guardaba bien la cantidad base
en el movimiento y acto seguido sumaba al saldo la cantidad tecleada. El movimiento decía 24 y el
saldo sumaba 2. No era un riesgo futuro: la API de movimientos ya admitía presentaciones.

## Siete defectos preexistentes cerrados

El saldo en cantidad tecleada; los seriales que viajaban como lista a una columna de texto mientras
la aceptación esperaba una cadena; la posibilidad de recibir contra la línea de otra orden; la de
añadir líneas a una recepción ya aceptada; una suma de aceptado más rechazado que podía superar lo
recibido; la acumulación en la orden sin bloqueo; y esa misma acumulación en cantidad tecleada.

## Una decisión de diseño

No se añadió un campo de conformidad. `quality_status` ya responde «¿la recepción es conforme?».
Lo que faltaba no era el veredicto sino la inspección que lo sostiene, y eso es lo que se construyó.

## Regresión

| Compuerta | Resultado |
|---|---|
| Backend (PostgreSQL 18.6 · ClamAV 1.4.3) | **871 pruebas · 863 pasadas · 8 saltadas · 0 fallos · 0 errores** |
| — nuevas de esta Spec | **37** |
| Frontend | 283/283 · `tsc` · ESLint · build |
| E2E | 6/6 en tres navegadores · axe 22/22 · recorrido de rutas 1/1 |
| Responsive | 194/216, los 22 casos idénticos a la auditoría anterior |
| Instalación limpia | subir, bajar la `0044`, volver a subir |

## Deuda propia

**Ninguna P0.**

## Lo que sigue

La cadena de entrada avanza. La Spec 020 queda como única `READY_FOR_IMPLEMENTATION`: tiene cero
bloqueos y ahora, además, una recepción capaz de describir lo que llegó. Detrás siguen la 021 —que
espera la capacidad de excepción de la 020 y que el motor de saldos sepa escribir estados no
vendibles— y la 022, y detrás de ellas la 031 y la 032.
