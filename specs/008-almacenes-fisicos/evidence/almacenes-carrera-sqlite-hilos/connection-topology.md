# Topología hilo → sesión → conexión (sonda `acs_sonda`, 20 corridas de la prueba sola; ids sintéticos T/C)

Sonda fuera del repositorio (`-p acs_sonda`): `threading.excepthook` (lo que mata a un hilo), eventos de SQLAlchemy
`checkout` (qué conexión DBAPI recibe cada hilo), `before_cursor_execute` (INSERT en `warehouse_locations`), `commit`,
`rollback` y `handle_error`. Sin direcciones de memoria: C1, C2…; T1, T2…

| THREAD | SESSION | SQLA CONNECTION | DBAPI CONNECTION | TX EVENTS | RESULT |
|---|---|---|---|---|---|
| MAIN/T1 (fixture, login, `_new_warehouse`) | propia | del pool | **C1** | checkout/rollback | — |
| T3/T4 (peticiones previas del `TestClient`) | propia | del pool | **C1** | checkout/rollback | — |
| T5 (hilo de carrera 1) | `Session` propia (`get_db`) | del pool | **C1** | INSERT · COMMIT | 200 |
| T6 (hilo de carrera 2) | `Session` propia | del pool | **C1** | INSERT · (error) · ROLLBACK | 409 ó excepción |

`StaticPool` entrega **siempre la misma conexión DBAPI** (`check_same_thread=False` solo desactiva la comprobación de
pysqlite): dos sesiones de dos hilos ejecutan sentencias **sobre la misma conexión y la misma transacción**.
`CONNECTION_TOPOLOGY = PROVEN` (20/20 corridas: una única conexión vista; `conexiones DBAPI distintas vistas: 1`).

## Secuencias observadas

Corrida que PASA (p. ej. run 2): T5 INSERT → T5 COMMIT → T6 INSERT → `IntegrityError: UNIQUE constraint failed` → T6
ROLLBACK → `[200, 409]`, total 1. El `COMMIT` de T5 terminó antes de que T6 ejecutara.

Corridas que FALLAN (runs 1, 7, 13, 20 de 20):

```
## run 1
[SQL] hilo=T5 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[DBERR] hilo=T5 tipo=ResourceClosedError msg=This result object does not return rows. It has been closed automatically. stmt=INSERT INTO warehouse_locations (company
[ROLLBACK] hilo=T5 conexion=C1
## run 7
[SQL] hilo=T6 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[COMMIT] hilo=T6 conexion=C1
[COMMIT] hilo=T6 conexion=C1
[SQL] hilo=T5 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[DBERR] hilo=T5 tipo=DatabaseError msg=UNIQUE constraint failed: warehouse_locations.warehouse_id, warehouse_locations.code stmt=INSERT INTO warehouse_location
[ROLLBACK] hilo=T5 conexion=C1
[ROLLBACK] hilo=T6 conexion=C1
## run 13
[SQL] hilo=T5 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[COMMIT] hilo=T5 conexion=C1
[SQL] hilo=T6 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[DBERR] hilo=T6 tipo=ResourceClosedError msg=This result object does not return rows. It has been closed automatically. stmt=INSERT INTO warehouse_locations (company
[ROLLBACK] hilo=T6 conexion=C1
[COMMIT] hilo=T5 conexion=C1
[ROLLBACK] hilo=T5 conexion=C1
## run 20
[SQL] hilo=T6 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[SQL] hilo=T5 conexion=C1 INSERT INTO warehouse_locations (company_id, warehouse_id, zone_id, ai
[DBERR] hilo=T5 tipo=ResourceClosedError msg=This result object does not return rows. It has been closed automatically. stmt=INSERT INTO warehouse_locations (company
[COMMIT] hilo=T6 conexion=C1
[ROLLBACK] hilo=T5 conexion=C1
[COMMIT] hilo=T6 conexion=C1
[ROLLBACK] hilo=T6 conexion=C1
```

- run 1, 13, 20: T4/T5 ejecuta su INSERT y entra en `COMMIT`; el INSERT del otro hilo se ejecuta **sobre la misma conexión
  mientras el commit del primero cierra los cursores** → pysqlite devuelve `ResourceClosedError: This result object does not
  return rows. It has been closed automatically.` en el INSERT del segundo hilo → no es `IntegrityError` → el servicio no lo
  traduce → 500 → `TestClient` relanza en el hilo → el hilo muere sin añadir resultado → `results == [200]`.
- run 7: la misma colisión aflora como `sqlite3.DatabaseError: UNIQUE constraint failed` (la clase base, no
  `IntegrityError`, porque el error se recoge por otra ruta del cursor compartido) → tampoco se traduce → 500.

`FAILURE_SIGNATURE`: **F1 (500 inesperado)** que la prueba ve como **F9/F2** (`assert [200] == [200, 409]`: un solo resultado
porque el hilo murió). En ningún caso `database is locked` (F6): con una sola conexión no hay bloqueo entre conexiones.
