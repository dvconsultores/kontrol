# Causa raíz
ROOT_CAUSE = `CATCH_ALL_INTEGRITY_TRANSLATION` · ROOT_CAUSE_PROVEN = 1 · UNKNOWN = 0.

`_integrity(exc, code, message)` hace `del exc` y devuelve siempre `ConflictError(code)`; los cinco sitios capturan
`IntegrityError` sin clasificarlo. Por eso una clave foránea rota (D2) llega como duplicado y una violación única real
también (D1): las dos comparten la misma rama.

PREDICCIÓN: con la rama acotada a la violación única de **la** restricción del código, D2 pasa a 500 `INTERNAL_ERROR` y D1
sigue en 409.

CONTROL: adoptar el `es_violacion_unica` vigente (solo PostgreSQL) no basta. La firma SQLite del duplicado real no trae
`pgcode` (medido), así que el helper devolvería `False`. `test_concurrencia_de_codigo_resuelta_por_constraint`, que corre en
SQLite con una conexión por hilo, pasaría de `[200, 409]` a un 500. La decisión de la dueña exige el 409 en SQLite, de
modo que el reconocimiento SQLite es parte de la corrección (DERIVED; se verifica con la prueba de carrera tras aplicar).
