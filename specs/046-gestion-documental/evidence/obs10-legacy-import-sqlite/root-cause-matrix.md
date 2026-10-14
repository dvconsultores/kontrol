# Matriz de causa raíz · `UNKNOWN = 0`
| TEST | REPRODUCED | CURRENT_SHARED_CONNECTION | CURRENT_FAILURE | CONTROL_B | CONTROL_C | POSTGRESQL | ROOT_CAUSE | PRODUCT_CHANGE | OWNER_DECISION | IMPLEMENTATION_ALLOWED |
|---|---|---|---|---|---|---|---|---|---|---|
| las siete importadoras (misma estructura y mismos ayudantes) | YES (3/3) | sí (C1) | F5 StaleDataError | F4 locked | PASS | PASS | **HARNESS_SHARED_CONNECTION_PLUS_LIFECYCLE**: la conexión compartida deja que el rollback de otra sesión descarte las escrituras sin confirmar de la prueba; con conexiones propias aflora que la prueba hace HTTP y abre sesiones auxiliares con su transacción de escritura abierta, sin que el contrato lo pida | NO | NO | **YES** |
Causa única para las siete, probada por la sonda (secuencia idéntica de ayudantes) y por los controles B/C sobre el módulo entero.
