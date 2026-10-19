# Diagnóstico previo a la corrección (sonda desechable sobre `tests/conftest_multicompany.py`, PostgreSQL; `ua` = solo A)
| Id | Operación | HTTP | Persistido | Resultado |
|---|---|---|---|---|
| C1/C2 | control: tipo propio en ubicación y zona | 200 | — | correcto |
| T1 | alta de ubicación de A con `location_type_id` de B | 200 | sí | **DEFECTO** |
| T2 | alta de zona de A con `zone_type_id` de B | 200 | sí | **DEFECTO** |
| T3 | `PATCH /locations/{id}` de A al tipo de B | 200 | sí | **DEFECTO** |
| T4 | `PATCH /zones/{id}` de A al tipo de B | 200 | sí | **DEFECTO** |
| T5 | `POST /locations/bulk` en A con tipo de B | 200 | sí | **DEFECTO** |
| T6a/b | tipos de otro tenant (C) en ubicación y zona | 200 | sí | **DEFECTO** |
| R1 | lectura de la ubicación T1 desde A | 200 | — | expone el código del tipo ajeno (`LTB`) |
| L1 | listado de A filtrado por el tipo de B | 200 · total 4 | — | consecuencia |
Medido dos veces: el 2026-10-19 a las 02:37 (preparación) y a las 02:52 (este ciclo, `PRE_FIX_DEFECT_REPRODUCED = 1`).
Sonda eliminada; `TEMP_PROBES = 0`.
