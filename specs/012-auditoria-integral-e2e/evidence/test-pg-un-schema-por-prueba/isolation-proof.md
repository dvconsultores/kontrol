# Prueba de aislamiento · gate material

| Criterio | Evidencia | Resultado |
|---|---|---|
| Filas de A no visibles en B (mismo módulo) | PGS-02/03 en proceso; sondas `sonda_sesion_a/b` (`instalaciones_al_empezar == []` en cada prueba) | PASS |
| `commit` de la prueba y del producto (`initialize` → `get_or_create_installation` → `db.commit()`) no escapan | PGS-04/05; M-02, M-03, M-05 muertos | PASS |
| `update` / `delete` no observables fuera del ámbito | PGS-02 (update + rollback dentro), PGS-03 (delete), PGS-05 | PASS |
| Segunda sesión del ámbito ve lo del ámbito y la prueba siguiente nada | PGS-06/06b | PASS |
| Hilos | no aplica a las 12 suites (0 hilos); las suites con hilos conservan su schema por prueba | n/a (documentado) |
| Secuencias / identidades | 0 en modelos y en el schema (PGS-08 en ambos motores) | PASS (contrato: no hay) |
| Un schema por módulo, nunca por sesión | PGS-09, PGS-07 (dos módulos → dos schemas, exactamente uno nuevo por módulo), PGS-28 estático; M-01, M-07 muertos | PASS |
| PGLIFE suelta el schema del módulo, también tras un fallo | PGS-10/11 (0 schemas con el pid del hijo), M-06 y M-09b muertos | PASS |
| Dos procesos a la vez | PGS-26 (schemas distintos, 0 residuos) | PASS |
| Orden inverso y prueba sola | PGS-23 | PASS |
| SQLite sin cambio semántico | PGS-09 rama SQLite (motor nuevo por prueba), M-08 muerto; suite completa SQLite sin regresión | PASS |
| Independencia por módulo entero / prueba individual (PGS-24/25) | PGS-23 (`::test_2` sola) y PGS-11 (módulo entero) | PASS |

`AISLAMIENTO_PRESERVADO = YES`. Límite documentado: el mecanismo no vale para fixtures con sesiones secundarias ligadas
al motor (`TestClient` + `dependency_overrides`) ni para hilos con commits reales; esas suites quedan fuera (schema por
prueba) y están listadas con su razón en `suite-inventory.md`.
