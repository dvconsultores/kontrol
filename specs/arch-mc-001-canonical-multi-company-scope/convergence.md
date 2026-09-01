# CONVERGENCIA — ARCH-MC-001

Convergencia **por fase**. No es la convergencia global de la Spec: N8, N9 y N10
siguen pendientes.

---

# N7 — INTEGRIDAD ESTRUCTURAL

## 1. Requisitos frente a implementación

| | |
|---|---:|
| Requisitos funcionales | 30 |
| Requisitos no funcionales | 6 |
| Criterios de aceptación | 10 |
| Implementados y probados | **46 / 46** |
| Sin tarea | 0 |
| Sin prueba | 0 |

## 2. Tareas frente a implementación

Diecinueve tareas, todas cerradas. Ninguna huérfana: cada una nace de un
requisito y termina en una prueba.

Dos tareas cerraron **sin producir código**, y conviene decir por qué en vez de
inventarles trabajo:

- **T-N7-009 (unicidad)**: las once restricciones que debían ser de empresa ya
  lo eran. Cambiar una correcta para que la fase pareciera mayor habría sido
  trabajo inventado. Lo que produjo la tarea fue la prueba de que se comportan
  como dicen.
- **T-N7-008 (índices)**: 102 de 107 columnas de empresa ya tenían uno, y las
  cinco restantes no se consultan por empresa. Medido con `EXPLAIN`.

## 3. Migraciones frente a modelos

Cinco migraciones (`0033`–`0037`) y 90 columnas del ORM actualizadas. La paridad
se comprueba con una prueba que compara columna a columna lo que el modelo
declara con lo que la base tiene.

Esa prueba existe por un error de esta fase: las claves se añadieron primero
solo en las migraciones, y como la base de pruebas nace de `create_all`, las
pruebas de corrupción corrían contra un esquema sin restricciones.

**Deriva: 0.**

## 4. Modelos frente al catálogo de PostgreSQL

| Comprobación | Resultado |
|---|---|
| Claves foráneas | 336, sin deriva |
| Obligatoriedad | sin deriva |
| Unicidad | sin deriva |
| Índices | sin deriva |
| Modelos sin alcance declarado | 0 |

## 5. Evidencia de pruebas

| Suite | Qué demuestra |
|---|---|
| `test_n7_corruption.py` (12) | Lo que PostgreSQL rechaza por sí solo, con `SQLSTATE` verificado |
| `test_n7_structure.py` (7) | Invariantes sobre el catálogo real, no sobre el ORM |
| `test_architecture_scope.py` (10) | Las tres rojas históricas ahora en verde |
| Instalación limpia | 37 migraciones, 336 claves |
| Fixture hostil | Aborta sin escrituras parciales |
| Suites de dominio | Sobre empresas reales, no sobre cadenas inventadas |

## 6. Artefactos

`spec.md`, `clarifications.md`, `plan.md` con su Constitution Gate,
`checklist.md`, `tasks.md`, `analysis-report.md`, `traceability-matrix.md` y
trece informes técnicos de N7. Ninguno sustituye a los artefactos del ciclo:
los complementan.

## 7. Deuda oculta

**Ninguna.** No quedan claves pendientes, rutas anulables, unicidades sin
revisar ni coherencias sin proteger.

Una limitación registrada, no una deuda: el planificador de N4 infiere del
modelo vigente y no del catálogo de la base destino. Se documenta como contrato
para la Spec 052 en lugar de resolverse a ciegas, porque no existe ningún
destino heredado que leer y adivinar su forma sería inventar el requisito.

## 8. Trabajo de otras fases colado

| Fase | Comprobación | Resultado |
|---|---|---|
| N8 | `legacy_scope_id`, `scope_backfill_class`, mecanismos transicionales | intactos |
| N8 | Cabecera en OpenAPI | sigue sin declarar, anotada |
| N9 | `REM-046-001`, tipos de recurso, reconvergencia de 046 | sin tocar |
| Spec 012 | — | sin implementar |
| Intercompany | — | sin implementar; las operaciones cruzadas siguen bloqueadas |

## 9. Veredicto

**`N7 CONVERGED`**

No es `ARCH-MC-001 COMPLETE_100`.

---

# N8 — CONTRATO Y RETIRADA DE LO TRANSITORIO

## 1. Requisitos frente a implementación

26 funcionales, 4 no funcionales, 10 criterios de aceptación. **40/40**
implementados y probados. Sin tarea: 0. Sin prueba: 0.

## 2. Tareas

Diecisiete, todas cerradas. Dos cerraron **sin producir código**, y el documento
lo dice en vez de inventarles trabajo:

- **T-N8-002 (lectura y escritura doble)**: no existían. Las columnas de
  respaldo se crearon y el backfill que las habría usado resultó innecesario, así
  que nunca hubo transición que desmontar. La ausencia no es un logro de N8: es
  la consecuencia de haber cerrado la ventana a tiempo.
- **T-N8-004 (cargas útiles heredadas)**: N5 cerró el último caso.

## 3. El hallazgo material

El clasificador de N4 había quedado ciego tras N7 y **dos skips lo ocultaban**.
Se corrigió antes de retirar nada, que es el orden que el plan imponía por una
razón concreta: borrar primero habría convertido un fallo detectable en uno
silencioso.

## 4. Migraciones frente a modelos

`0038` retira 160 columnas que ningún modelo declaraba. La prueba de paridad de
N7 sigue verde.

## 5. Contrato frente a runtime

332 operaciones declaran la cabecera, 72 no, y las dos direcciones se comprueban.
Se declara opcional porque el servidor la resuelve solo con una empresa
accesible: decirla obligatoria describiría un sistema distinto.

Además del contrato se prueba el comportamiento, que es lo que evita que las dos
descripciones se separen con el tiempo.

## 6. Skips

De 16 a 14. Los dos que desaparecieron ocultaban trabajo de N8.
`N8_REQUIREMENT_HIDDEN_BY_SKIP = 0`.

## 7. Deuda oculta

**Ninguna.** No queda repliegue activo, lectura ni escritura doble, columna
transitoria en el esquema operativo, ni contrato que mienta sobre el contexto.

La capacidad de migración se conserva y **mejora**: el clasificador ya no
depende del modelo de la versión que lo ejecuta.

## 8. Trabajo de otras fases colado

| Fase | Comprobación | Resultado |
|---|---|---|
| N9 | `REM-046-001`, tipos de recurso, reconvergencia de 046 | sin tocar |
| N10 | Convergencia global | sin ejecutar |
| Spec 012 | — | sin implementar |
| Specs 052 / 053 | Solo contrato documental | sin implementar |

## 9. Veredicto

**`N8 CONVERGED`**

No es `ARCH-MC-001 COMPLETE_100`.


---

# N8 — CONVERGENCIA DEL SELLO FINAL DE EVIDENCIA

## 1. Continuidad, no reapertura

`specify`, `clarify`, `plan` y el Constitution Gate siguen `PASS` y no se
rehicieron: el sello no cambia ninguna decisión de diseño. Se actualizaron
`checklist.md`, `tasks.md` y `traceability-matrix.md`, y se ejecutó un
`/speckit.analyze` **delta** antes de tocar código.

## 2. Qué faltaba

De las once evidencias exigidas, cuatro estaban completas —`MC-A`, `MC-B`,
`MC-C`, `MC-E`— y siete no:

- `MC-D` no tenía semilla.
- `INVALID_LEGACY_SCOPE` y `CROSS_TENANT` solo tenían comparaciones del valor
  del enum.
- Las cuatro estrategias de maestro se comprobaban llamando a la función con
  conjuntos sintéticos, sin pasar por la ruta del preflight.

## 3. Dos defectos, no dos lagunas

La distinción importa. `CROSS_TENANT` y `MASTER_DERIVE` estaban **definidos en el
contrato y no implementados**: el primero nunca se emitía y el segundo no podía
devolverse.

Corregirlos no introdujo semántica nueva — aplicó la que ya estaba escrita. Es
exactamente lo que separa «la rama existe» de «hay ejecución», y en estos dos
casos ni siquiera había rama.

## 4. Verificación

| Qué | Resultado |
|---|---|
| Clasificación explícita por caso | 8 clases, todas con filas reales |
| Estrategias de maestro | 4, todas alcanzadas en la corrida |
| Cero escrituras | conteos y `alembic_version` idénticos |
| Repetibilidad | comparada **por clase**, no por total |
| Severidad | `INVALID` y `CROSS_TENANT` no degradan a `MC-D` |
| Fixture versionado | sí, con aserciones de siembra |
| Independencia del ORM final | el fixture vive en `0032` y el código en `0038` |
| Trazabilidad | una fila por caso; 0 huérfanos |

## 5. Deuda de evidencia

**Ninguna.** No queda clase declarada sin ejecutar ni estrategia sin fixture.

## 6. Veredicto

**`N8 FINAL EVIDENCE CONVERGENCE: PASS`**

---

# N9 — CIERRE DE REM-046-001 Y RECONVERGENCIA DE LA SPEC 046

## 1. Requisitos frente a implementación

46 funcionales, 9 criterios de aceptación, 29 tareas. **Huérfanos: 0.**

## 2. Lo que la auditoría cambió antes de implementar

Dos hallazgos, ambos registrados en el análisis en lugar de resolverse en
silencio:

**La premisa de `REM-046-001` estaba resuelta.** Recomendaba el camino B —añadir
al registro un campo que distinguiera empresa de tenant— porque el A era
demasiado grande. Se hizo el A, como ARCH-MC-001 entera. El B no se implementó y
no por descartarlo: se quedó sin causa.

**La cardinalidad.** 19 registrados, 4 exigidos, 23 esperados. El «19/19» del
encargo nombra otra cosa igual de cierta —19 registrados y uno probado— y N9
satisface ambas cuentas.

## 3. La evidencia

De **1 tipo probado a 23**. Cada uno con entidad persistida en PostgreSQL,
vínculo en su empresa, y bloqueo comprobado contra otra empresa y contra otro
tenant. 48 pruebas, ninguna saltada, con el fallo nombrando el tipo.

Más la integridad probada rompiéndola: objeto alterado y objeto ausente
detectados en la entrega, en vez de servidos en silencio.

## 4. Deuda declarada

| Qué | Prioridad | Dueño |
|---|---|---|
| S3 con servicio real | P1 | Entorno |
| Planificador de retención | P1 | Spec de instalación |

Ninguna P0, ninguna disfrazada.

## 5. Trabajo de otras fases

N10 no se inicia. La Spec 012 no se toca y conserva su estado.

## 6. Veredicto

**`N9 CONVERGED`** · **`SPEC 046 RECONVERGED`** · **`REM-046-001 CLOSED`**

No es `ARCH-MC-001 COMPLETE_100`.
