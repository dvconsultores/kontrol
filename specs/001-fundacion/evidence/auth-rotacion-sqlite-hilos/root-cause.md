# Causa raíz y clasificación · `ROOT_CAUSE = PROVEN` · `CLASSIFICATION = PRODUCT_DEFECT` (acotado a SQLite) · `FROZEN`

## Dos capas, las dos demostradas

**Capa 1 — arnés (`HARNESS_SHARED_CONNECTION`)**: `make_engine()` en SQLite entrega una sola conexión pysqlite a todos los
hilos (sonda: 1 conexión en 10/10). Produce las firmas de ruido: `cannot commit transaction - SQL statements in progress`,
`StaleDataError`, hilos muertos (`len == 1` o `0`). Con una conexión por hilo (`motor_para_hilos`) desaparecen por
completo (0 excepciones en 25 rondas; Experimento B 20/20). Es la misma causa que cerró `ALMACENES-CARRERA-SQLITE-HILOS`.

**Capa 2 — producto sobre SQLite (`PRODUCT_DEFECT`, acotado al motor)**: con sesiones independientes, conexiones DBAPI
independientes, el mismo datastore y la interleaving I1 (las dos leen antes de que ninguna escriba), **las dos
renovaciones confirman** (5/5 controladas; 18/20 naturales con barrera de arranque) y queda una sesión viva huérfana.
Secuencia SQL real por hilo: `SELECT sessions … WHERE id = :sid` (sin `FOR UPDATE`: SQLite lo ignora) → `UPDATE sessions
SET revoked_at` → `INSERT INTO sessions` → `UPDATE sessions SET refresh_token_hash` → `COMMIT`. La garantía «solo una
gana» del contrato se apoya **exclusivamente** en el bloqueo de fila `with_for_update()` (commit `bf0ba9e`), que PostgreSQL
honra (serie C 20/20) y SQLite no. La afirmación del cierre de REM-AUTH y del comentario del servicio —«`with_for_update`
es inocuo en SQLite, que serializa las escrituras por su cuenta»— es **falsa para esta carrera**: SQLite serializa las
escrituras, sí, pero no impide que la segunda transacción escriba sobre una lectura ya obsoleta, porque pysqlite (isolation
level legado `''`) ejecuta el `SELECT` sin transacción abierta y no retiene bloqueo alguno entre leer y escribir.

## Qué NO es

- No `HARNESS_STATE_LEAK`: falla sola en proceso nuevo (15/20) y el módulo solo falla en esa prueba.
- No `SQLITE_LOCKING_SEMANTICS` como causa del contrato roto: no aparece `database is locked` en ninguna serie; el bloqueo
  solo surge en la exploración (c) por un artefacto de la barrera.
- No solo `POSTGRESQL_ONLY_CONTRACT`: ese es uno de los caminos de decisión (opción D), no la causa; la causa es que el
  servicio no tiene ningún mecanismo independiente del motor que garantice un solo ganador.

## Compuerta

`PRODUCT_DEFECT_GATE`: con sesiones independientes + conexiones independientes + mismo datastore + concurrencia controlada
válida, **ambas rotaciones confirman** cuando el contrato exige un ganador → **PRODUCT_DEFECT = PROVEN candidate** →
**STOP antes de `/speckit.implement`**. Veredicto: `AUTH-ROTACION-SQLITE-HILOS — BLOCKED BY PRODUCT DECISION`.
El informe para la dueña, con opciones, está en `product-defect-report.md`.

Alcance de seguridad: **producción no está expuesta** (P21: PostgreSQL, donde `FOR UPDATE` cierra la ventana; serie C
20/20; certificación de REM-AUTH 28/28 ×3 sobre PostgreSQL 18.6). La exposición es de cualquier despliegue sobre SQLite
(no existe en producción) y, hoy, de la **evidencia**: la prueba de concurrencia en SQLite no demuestra la garantía y la
pasaría o fallaría según el reloj; adoptar `motor_para_hilos` sin más la volvería verde por sincronización (Experimento B),
no por contrato: confianza falsa, descartada.
