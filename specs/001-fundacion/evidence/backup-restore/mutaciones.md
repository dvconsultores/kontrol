# Campaña de mutaciones 06 — copia y restauración verificadas

Mutantes ejecutados con `mutar06.py` (herramienta de Claude, fuera del repositorio). Por cada mutante:
- se sustituye un fragmento único;
- se purga `__pycache__` con `PYTHONDONTWRITEBYTECODE=1`;
- se ejecuta la orden asesina;
- se restaura el fichero y se verifica por sha256.

Todos los mutantes quedaron restaurados.

Órdenes asesinas:
- **Producto:** `pytest -x` sobre `test_backup_crypto`, `test_backup_bundle`, `test_backup_cli`, `test_backup_create_pg` y `test_backup_restore_pg`, contra el PostgreSQL de QA con `KONTROL_PG_BIN_DIR`.
- **M06-21:** `test_license_state_reverification` y `test_license_reverification_rules`.
- **Guion `qa/backup_restore_cert.py`:** corrida real y después el validador externo del manifiesto. El validador exige:
  - veredicto PASS;
  - fases P1..P13 y LIMPIEZA en verde;
  - checks C-00..C-11 y S-01 en verde;
  - métricas de RPO y RTO presentes.

Resumen de las rondas:
- **Ronda 1:** 20 mutantes de producto, 10 muertos y 10 supervivientes.
- **Pruebas nuevas (C06-T09):** BB-18, BB-19, BCP-09, BCP-10 y BR-16..BR-21.
- **Ronda 2:** los 10 supervivientes y M06-21, todos muertos.
- **Guion:** 4 mutantes, 3 muertos y 1 equivalente.

| ID | Mutación (§73) | Ronda 1 | Final | Prueba que lo mata |
|---|---|---|---|---|
| M06-01 | omit document storage | KILLED | KILLED | BCP-01 |
| M06-02 | omit DB dump validation (rc de `pg_dump`) | SURVIVED | KILLED | BCP-09 |
| M06-03 | omit manifest verification (lectura) | SURVIVED | KILLED | BB-18 |
| M06-04 | omit DB hash | SURVIVED | KILLED | BB-19 |
| M06-05 | omit storage hash (objeto del paquete) | KILLED | KILLED | BB-09 |
| M06-06 | omit storage hash (rehash al restaurar) | SURVIVED | KILLED | BR-16 |
| M06-07 | skip encryption | KILLED | KILLED | BC-01 |
| M06-08 | embed key (en el manifiesto cifrado) | SURVIVED | KILLED | BCP-10 |
| M06-09 | skip installation identity check | KILLED | KILLED | BR-03 |
| M06-10 | allow non-empty target (base) | KILLED | KILLED | BR-04 |
| M06-11 | allow non-empty target (almacén) | KILLED | KILLED | BR-05 |
| M06-12 | skip Alembic check (revisión que no resuelve) | SURVIVED | KILLED | BR-17 |
| M06-13 | skip Alembic check (no es cabeza) | SURVIVED | KILLED | BR-18 |
| M06-14 | skip audit trigger validation | KILLED | KILLED | BR-10 |
| M06-15 | skip document hash validation (copia) | KILLED | KILLED | BCP-03 |
| M06-16 | skip external-key check (clave de instalación) | SURVIVED | KILLED | BR-19 |
| M06-17 | skip external-key check (anillo MFA) | KILLED | KILLED | BR-07 |
| M06-18 | ignore failed restore step (rc de `pg_restore`) | SURVIVED | KILLED | BR-20 |
| M06-19 | ignore failed restore step (sin limpieza) | KILLED | KILLED | BR-07 |
| M06-20 | report success before verification (huellas) | SURVIVED | KILLED | BR-21 |
| M06-21 | skip license reverification (arranque) | — | KILLED | REVST-01 |
| M06-22 | report success before functional smoke (`return 0` antes de P12) | — | KILLED | Validador del manifiesto (veredicto PENDING, checks ausentes) |
| M06-23 | omit RTO measurement | — | KILLED | M-01 del guion y validador |
| M06-24 | omit RPO measurement | — | KILLED | M-01 del guion y validador |
| M06-25 | skip point-in-time check (`c05 = True` en el guion) | — | INVALID | — (Principio 27: mismo resultado en el caso probado; sustituido por M06-26) |
| M06-26 | skip point-in-time (`pg_dump` sin `--snapshot`), sustituto de M06-25 | SURVIVED | KILLED | BR-22 (prueba nueva de convergencia, C06-T09B) |
| M06-27 | estado de licencia del manifiesto leído por `installations.id` (defecto F1 reintroducido) | — | KILLED | BCP-11 (rojo medido antes de corregir, C06-T050) |

**M06-25 no es válido (Principio 27).** El guion mutado da el mismo resultado en el caso probado: la escritura posterior se hace cuando `create` ya terminó, así que no puede entrar en el paquete con ningún producto. Se sustituyó por M06-26, que rompe la propiedad real en el producto: sin `--snapshot`, `pg_dump` vuelca otra instantánea, posterior a la del manifiesto. M06-26 sobrevivió a toda la batería, lo que destapó la falta de una prueba que combine una escritura concurrente con una restauración. BR-22 lo mata: la restauración detecta que las huellas no coinciden.

```
TOTAL_MUTANTS                   = 27
KILLED_MUTANTS                  = 26
EQUIVALENT_MUTANTS              = 0
BEHAVIORALLY_SURVIVING_MUTANTS  = 0
INVALID_MUTANTS                 = 1
```

Las campañas anteriores se informan por separado y no se suman:

| Campaña | Total | Muertos | Equivalentes | Supervivientes |
|---|---|---|---|---|
| 02D | 91 | 89 | 2 | 0 |
| 02E | 12 | 11 | 1 | 0 |
| 03 | 35 | 35 | 0 | 0 |
| 04 | 24 | 24 | 0 | 0 |
| 05 | 23 | 23 | 0 | 0 |
| 06 | 27 | 26 | 0 (1 inválido) | 0 |
