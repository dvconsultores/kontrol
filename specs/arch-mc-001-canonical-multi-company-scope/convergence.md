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
