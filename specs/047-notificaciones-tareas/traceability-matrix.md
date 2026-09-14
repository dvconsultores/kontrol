# Matriz de trazabilidad — SPEC 047

> Trazabilidad **documental**: requisito → tarea → prueba prevista. Ningún
> requisito está implementado; la columna final dice qué lo impide.

| FR | Tareas | Prueba dirigida prevista | Hostil | Mutación | E2E | Implementable hoy |
|---|---|---|---|---|---|---|
| 001 | T047-010, 101 | flujo A | — | — | centro | No · OQ-047-01 |
| 002 | T047-011 | destinatario del servidor | ids del cliente | — | — | No · OQ-047-01 |
| 003 | T047-012, 101 | flujo B | — | M047-04 | estado de lectura | No · OQ-047-01 |
| 004 | T047-010, 013 | persistencia de crítica | — | — | — | No · OQ-047-01 |
| 005 | T047-020, 102 | flujo C | — | — | tarea | No · OQ-047-01 |
| 006 | T047-020, 023 | reasignación | carrera | M047-09 | asignación | No · OQ-047-01 |
| 007 | T047-020, 021 | flujo D | — | M047-05 | completado | No · OQ-047-01 |
| 008 | T047-020, 050 | flujo I | — | M047-10 | — | No · OQ-047-01 |
| 009 | T047-020 | prioridad configurable | — | — | filtro | No · OQ-047-01 |
| 010 | T047-030, 104 | flujo E | — | — | alertas | No · OQ-047-01 |
| 011 | T047-010, 082 | enlace mínimo | — | — | enlace | No · OQ-047-01 |
| 012 | T047-010, 110 | flujo H | empresa B | M047-03 | aislamiento | No · OQ-047-01 |
| 013 | T047-010, 110 | cruce de tenant | T2 | M047-02 | — | No · OQ-047-01 |
| 014 | T047-084, 110 | visibilidad revalidada | permiso retirado | — | — | No · OQ-047-01 |
| 015 | T047-041 | flujo F · diez reintentos | — | M047-01, M047-08 | reintento | No · OQ-047-01 |
| 016 | T047-040 | correlación registrada | — | — | — | No · OQ-047-01 |
| 017 | T047-085 | reconstrucción §84 | — | M047-09 | — | No · OQ-047-01 |
| 018 | T047-013, 061 | obligatoria no desactivable | — | — | — | No · OQ-047-01 |
| 019 | T047-060, 061 | canal interno base | — | — | — | No · OQ-047-01 · 048 |
| 020 | T047-060 | guarda: sin credenciales en la 047 | — | — | — | No · 048 |
| 021 | T047-060 | reintento en la frontera | — | — | — | No · 048 |
| 022 | T047-060 | flujo G | — | M047-06 | — | No · OQ-047-01 · 048 |
| 023 | T047-053 | guarda de planificador único | — | — | — | No · OQ-047-01 |
| 024 | T047-051 | recordatorio | — | — | — | No · OQ-047-01 |
| 025 | T047-052 | flujo I con escalado | — | — | — | No · OQ-047-01 |
| 026 | T047-040 | sin recálculo de condiciones | — | M047-05 | — | No · OQ-047-01 |
| 027 | T047-042 | hecho masivo | — | — | — | No · OQ-047-01 |
| 028 | T047-080 | página 3 con > 100 | — | — | paginación | No · OQ-047-01 |
| 029 | T047-080, 102 | filtros reales | parámetro no soportado | — | filtros | No · OQ-047-01 |
| 030 | T047-081, 100 | contador agregado | contador de otra empresa | M047-11 | campana | No · OQ-047-01 · OQ-047-02 |
| 031 | T047-082 | flujo J con permiso | — | — | enlace | No · OQ-047-01 |
| 032 | T047-082 | flujo J sin permiso | IDOR | M047-07 | prohibido | No · OQ-047-01 |
| 033 | T047-070 | variable ausente | código en plantilla | — | — | No · OQ-047-02 |
| 034 | T047-071 | sin cadenas fuera del sistema | — | — | — | No · OQ-047-02 |
| 035 | T047-087 | sin borrado físico | — | — | — | No · OQ-047-01 |
| 036 | T047-081 | flujo K | — | M047-11 | — | No · OQ-047-01 |

| | |
|---|---|
| Requisitos con tarea | **36 / 36** |
| Requisitos con prueba prevista | **36 / 36** |
| Tareas sin requisito | **0** de 49 |
| M047-12 | T047-111: una carrera que devuelva 500 debe fallar la prueba |
| Requisitos implementados | **0 / 36** |
