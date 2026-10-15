# Causa raíz
`ROOT_CAUSE_CLASS = TEST_TIME_ANCHOR_DEFECT` (subtipo: referencia de importación usada como frontera de operación).
`MODULE_IMPORT_TIME_USED_AS_OPERATION_BOUNDARY = YES` · `PRODUCT_DEFECT = NO` · `CLOCK_CONTRACT_DEFECT = NO` ·
`DB_PRECISION = NO` · `TIMEZONE = NO` · `ORDERING = NO` · `OBS-12 = amplificador, no causa`.
Mecanismo: `SERVER_TIME` nace al importar el módulo (+5 min). La prueba activa la licencia a `_now()` (instante real) y
sincroniza con un servidor cuyo reloj es la referencia; el producto adopta el reloj del servidor solo si es posterior al
confiable vigente. Cuando la prueba corre más de 5 minutos después de la importación (cualquier suite completa: SQLite
≈ 10 min, PostgreSQL ≈ 30 min, módulo ejecutado a ≈ 12,6 min en la firma `15:45:41` vs `15:38:04`), la activación es
posterior al servidor y el producto, correctamente, conserva la activación: la aserción `== SERVER_TIME` falla.
Hipótesis descartadas con evidencia: H2 producto (verdadero negativo PASS), H3 reloj canónico (procedencia), H4/H5
zona y precisión (análisis por motor, igualdad exacta con referencia válida), H6 orden/aislamiento (aislada 20/20 y
frontera 8/8 con edades envejecidas), H7 motor (matriz idéntica).
