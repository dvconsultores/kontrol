# SPEC 020 — CHECKPOINT FINAL

## Veredicto

`SPEC 020 — COMPLETE / CONVERGED`

## Qué se pidió y qué se hizo

Convertir en excepciones formales, trazables y resolubles los hechos físicos que la Spec 019 observa
en el muelle. Son tres etapas del proceso: registrar la diferencia, generar su evidencia y escalarla
a Compras. Las tres quedan cubiertas, más el registro del tratamiento decidido.

## Baseline, mismo instrumento antes y después

| Métrica | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 177 · 177 | 178 · 178 |
| Migraciones | 44 | 45 |
| Rutas · operaciones | 321 · 440 | 328 · 448 |
| Operaciones con contrato de empresa | 378 | 386 |

Una tabla nueva, `receipt_incidents`, con seis restricciones que impiden filas sin lectura posible.

## Lo que se descartó

Ocho de los trece candidatos a tipo de incidencia no lo eran: cinco son datos que ya captura la
Spec 019, uno es el veredicto de conformidad y dos son tratamientos. Descartarlos con motivo fue la
parte más útil de la auditoría.

## Las tres decisiones que merecen explicación

La línea y la cantidad dependen del tipo, y lo impone la base de datos: una diferencia documental no
lleva ninguna de las dos y las otras cuatro exigen ambas. El tope de cantidad tampoco es el mismo
para todos: un faltante se mide contra lo pedido y los demás contra lo recibido. Y la acumulación se
comprueba por línea y por tipo, con la línea bloqueada, porque dos incidencias de daño no pueden
sumar más de lo que bajó del camión.

## Regresión

| Compuerta | Resultado |
|---|---|
| Backend (PostgreSQL 18.6 · ClamAV 1.4.3) | **920 · 912 pasadas · 8 saltadas declaradas · 0 fallos · 0 errores** |
| — nuevas de esta Spec | **47** |
| Frontend | 285/285 · `tsc` · ESLint · build |
| E2E | **86 pasadas · 16 fallos ajenos** en 13 suites × 3 navegadores. Dos suites del arnés N6 no corren en esta pila. **Remedido y sellado el 2026-09-04** (`spec020-evidence-seal.md`): 297 ejecuciones, 232 pasadas, 65 fallos, **los 65 reproducidos** en `409b945` —que falla 77 en esas mismas suites—, 0 regresiones nuevas y las dos suites N6 en verde sobre su propia base |
| Instalación limpia | subir, bajar la `0045`, volver a subir |

## Deuda propia

**Ninguna P0.**

## Lo que sigue

La Spec 021 recibe de la 020 lo que le faltaba: un resultado estructurado por línea y tipo. Le queda
un bloqueo, y no es de esta cadena: el motor de saldos solo sabe escribir `DISPONIBLE`, y confirmar
inventario exige poder escribir estados no vendibles. Eso es capacidad de la Spec 023.
