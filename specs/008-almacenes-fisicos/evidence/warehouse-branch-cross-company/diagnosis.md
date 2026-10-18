# Diagnóstico (sonda desechable sobre el mundo canónico `tests/conftest_multicompany.py`, PostgreSQL; usuario `ua` = solo empresa A)
| Id | Escenario | HTTP | Persistido | Resultado |
|---|---|---|---|---|
| D0 | alta en A con sucursal de A (control) | 200 | sucursal A | correcto |
| **D1** | alta en A con sucursal de **B** (mismo tenant) | **200** | almacén de A, `branch_id` = sucursal de B (empresa B) | **DEFECTO** |
| **D2** | alta en A con sucursal de **C** (otro tenant) | **200** | almacén de A colgado de una sucursal de otro tenant | **DEFECTO** |
| **D3** | `PATCH` del almacén de A a la sucursal de B | **200** | `branch_id` cambiado a la sucursal de B | **DEFECTO** |
| D4 | `GET /warehouses?branch_id=<sucursal B>` desde A | 200 · total 2 | — | el listado de A se deja filtrar por una sucursal ajena y la expone en `branch_id` |
| D5 | sucursal inexistente (OBS-01) | 500 `INTERNAL_ERROR` | 0 filas | correcto hoy; con la corrección pasa a 404 sin llegar a la base |
| T1/T2 | ubicación/zona de A con tipo de catálogo de B | 200 / 200 | — | misma familia, **otra deuda** (no absorbida) |
PROVEN: D1, D2, D3 (y D4 como consecuencia). NOT_MEASURED: filas cruzadas ya existentes en instalaciones reales (fuera de
alcance: lectura de producción no autorizada). CONTRADICTED: ninguno.
