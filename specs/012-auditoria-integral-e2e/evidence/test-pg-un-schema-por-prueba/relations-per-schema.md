# Medición · relaciones por schema del arnés (HEAD 805074c, `ktest` en pgserver 55432)

Guion de medición de Claude (fuera del repositorio): `crear_motor_de_prueba` + `create_all` sobre un schema, conteo en
`pg_class`/`pg_constraint`/`pg_sequences`, `cerrar_sesion`.

```
RELKIND: {'i': 638, 'r': 203}  total pg_class: 841
CONSTRAINTS: {'f': 464, 'c': 87, 'u': 56, 'p': 203, 'x': 1}  SEQUENCES: 0  TABLAS metadata: 203
tiempos: CREATE SCHEMA 0.005s · create_all 0.938s
DROP SCHEMA CASCADE 0.184s · residuos: []
```

| Registro | Valor |
|---|---|
| `TABLES` | 203 |
| `INDEXES` | 638 |
| `SEQUENCES` | **0** |
| `CONSTRAINTS` | 811 (464 FK · 203 PK · 87 CHECK · 56 UNIQUE · 1 EXCLUSION) |
| `VIEWS` / `OTHER_RELATIONS` | 0 |
| `TOTAL_RELATIONS` (`pg_class`) | **841** (la referencia «1 129» de la hoja de ruta no se reproduce con este conteo; con restricciones son 1 652 objetos) |
| `RELATIONS_PER_SCHEMA_ACTUAL` | 841 relaciones + 811 restricciones |
| Coste DDL por schema | ≈ 0,94 s de `create_all` + 0,18 s de `DROP … CASCADE` ≈ **1,1 s por prueba** |
| Catálogo antes → después de UN schema (bytes) | `pg_class` 114 688 → 368 640 · `pg_attribute` 466 944 → 1 490 944 · `pg_depend` 106 496 → 548 864 · `pg_index` 32 768 → 188 416 · `pg_constraint` 24 576 → 303 104 |

Un solo schema multiplica por 3–12 el tamaño de las tablas de catálogo (espacio que luego reutiliza `autovacuum`:
`TEST-PG-CATALOGO-MARCA-DE-AGUA`, solo se mide).
