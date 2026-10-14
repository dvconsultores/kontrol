# Pruebas dirigidas de seguridad · SA-01…SA-20

| Id | Qué | SQLite | PostgreSQL |
|---|---|---|---|
| SA-01 | I1 controlada (dos lecturas antes de la primera escritura) → `[200, 401]`, un reemplazo | 10/10 | — (SA-02) |
| SA-02 | carrera controlada con `FOR UPDATE` → `[200, 401]`, un reemplazo | — | 5/5 |
| SA-03 | prueba objetivo natural ×20 | 20/20 | — |
| SA-04 | prueba objetivo natural ×20 | — | 20/20 |
| SA-05 | sesión ya revocada → 401 `SESSION_REVOKED` | PASS | PASS |
| SA-06 | replay del token usado → 401 `SESSION_REVOKED` | PASS | PASS |
| SA-07 | expirada → 401 `SESSION_EXPIRED`, sin sesión nueva | PASS | PASS |
| SA-08 | hash distinto → 401 `SESSION_INVALID`, sesión sigue viva (validación antes de la escritura) | PASS | PASS |
| SA-09 | usuario inactivo → 403 `AUTH_USER_INACTIVE`, sesión sigue viva | PASS | PASS |
| SA-10 | perdedor (rowcount 0) crea 0 sesiones | PASS (SA-01 y SA-06) | PASS |
| SA-11 | ganador crea exactamente 1 | PASS | PASS |
| SA-12 | nunca dos reemplazos vivos de una misma rotación (vivas = antes + 1 en la carrera) | PASS | PASS |
| SA-13 | instancia ORM cargada sincronizada; un flush posterior no deshace la revocación | PASS | PASS |
| SA-14 | `OperationalError` en la escritura sube tal cual, no es `SESSION_REVOKED`; la sesión no queda revocada | PASS | PASS |
| SA-15 | excepciones de hilo visibles (lista vacía exigida) | PASS | PASS |
| SA-16 | contrato estático: escritura condicional, orden, `with_for_update`, reloj canónico, prohibiciones, prueba objetivo intacta | PASS | PASS |
| SA-17 | ACS-01…08 (`test_motor_para_hilos.py`) | 8/8 | 8/8 |
| SA-18 | almacenes (`test_warehouse_structure.py`, carrera incluida) | PASS (1 skip preexistente: integridad referencial solo PG) | PASS |
| SA-19 | OpenAPI 544/533/11 `BearerAccessToken`, OAS-01…15 | PASS | PASS |
| SA-20 | migración 0 · esquema 0 (`git diff --stat -- alembic/` vacío; modelo sin cambio) | PASS | PASS |

Corridas: `tests/test_auth_rotacion_atomica.py` + `tests/test_auth_session_rotation.py` 17/17 en los dos motores; series en
`directed-series-after.txt` (65/65 corridas PASS). 0 directorios `kontrol-test-sqlite-*` tras cada serie.
