# Benchmark ANTES (W07/W08) · suite completa PostgreSQL en HEAD 805074c

`KONTROL_TEST_DB_URL=postgresql+psycopg2://***@localhost:55432/ktest pytest tests -q -p no:cacheprovider -p pgs_contador` con
`PYTHONDONTWRITEBYTECODE=1`; el contador (guion de medición fuera del repositorio) imprime al cerrar la sesión lo que PGLIFE apuntó;
el catálogo se mide con `pg_relation_size` / `pg_total_relation_size` y `pg_database_size` antes y después, en el mismo proceso de medición.

```
[CATALOGO ANTES] pg_class=114688 pg_attribute=466944 pg_depend=106496 pg_index=32768 pg_constraint=24576 pg_attrdef=0 pg_type=122880 pg_total(pg_class+attribute+depend)=96092160 base_total=150524387 schemas_t_=0 pg_class_filas=413
[PGS-CONTADOR] schemas_creados=384 schemas_soltados=384 bases_soltadas=17 conexiones_cortadas=0 residuos=0 duracion_s=895.8
>       assert state.last_reliable_date.replace(tzinfo=UTC) == SERVER_TIME  # el reloj confiable viene del servidor autenticado
rc=1
[TIME] wall=929.849884489 s
[CATALOGO DESPUES] pg_class=114688 pg_attribute=466944 pg_depend=106496 pg_index=32768 pg_constraint=24576 pg_attrdef=0 pg_type=122880 pg_total(pg_class+attribute+depend)=96092160 base_total=150663651 schemas_t_=0 pg_class_filas=413
passed=2584 failed=38 skipped=28 (los mismos 38 de la base: 35 documentales, 2 n9_integrity, 1 intermitente temporal)
```

| Métrica | ANTES |
|---|---|
| `TOTAL_TESTS` | 2 650 (2 584 pasan · 38 fallan · 28 omitidas) |
| `SCHEMAS_CREATED` / `SCHEMAS_DROPPED` | **384 / 384** (214 de las 12 suites `db_session`, 43 de otras fixtures de función, ~35 mundos de módulo, sondas de PGLIFE…) |
| `CREATE_ALL_CALLS` | 384 (uno por schema) |
| `RELATIONS_CREATED_ESTIMATE` / `RELATIONS_DROPPED_ESTIMATE` | 384 × 841 = **322 944** relaciones (+ 384 × 811 = 311 424 restricciones) |
| `TOTAL_DURATION` | **929,8 s** de pared (895,8 s dentro de pytest) |
| `DDL_DURATION` (estimada) | 384 × ≈1,1 s ≈ **430 s** (≈ 46 % de la corrida) |
| `PEAK_SCHEMAS` / `RESIDUAL_SCHEMAS` | 1 vivo por ámbito (PGLIFE) / **0** |
| `CATALOG_SIZE_BEFORE` → `AFTER` | `pg_class` 114 688 → 114 688 · `pg_attribute` 466 944 → 466 944 · `pg_depend` 106 496 → 106 496 · `pg_total(pg_class+pg_attribute+pg_depend)` 96 092 160 → 96 092 160 · base 150 524 387 → 150 663 651 (+139 KB) |
| `CATALOG_DELTA` | 0 en las relaciones de catálogo: la «marca de agua» (≈ 96 MB con índices y TOAST) ya está alcanzada y el espacio se reutiliza; `TEST-PG-CATALOGO-MARCA-DE-AGUA` solo se mide (sigue OPEN) |
