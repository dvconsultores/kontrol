# Mapa del arnés PostgreSQL · `make_engine` → `pg_harness` → PGLIFE (HEAD 805074c)

```
prueba pide db_session
  → make_engine()                                  tests/conftest.py:make_engine
      → pg_harness.crear_motor_de_prueba(url)      exigir_base_de_prueba (URL declarada, «test» en el nombre, entorno de prueba, ≠ KONTROL_DB_URL)
          schema = f"t_{uuid4().hex[:12]}"         CREATE SCHEMA + COMMENT (marca «kontrol-test pid=… creado=…»)
          create_engine(url, connect_args={options: -csearch_path=<schema>, application_name: kontrol-test:<schema>})
          ambito_vigente().motores.append(...)     ámbito = prueba (fixture autouse _recursos_pg_de_la_prueba) o módulo (_recursos_pg_del_modulo)
          INFORME.schemas_creados += 1
  → init_models(); Base.metadata.create_all(engine)   en la fixture de cada suite (203 tablas, 638 índices, 811 restricciones)
  → sessionmaker(bind=engine)()                    sesión de la prueba
  → prueba
  → session.close()
  → cerrar_ambito(prueba)                          pg_harness._liberar → soltar_schema: dispose, corta conexiones abiertas, DROP SCHEMA CASCADE, comprueba, INFORME.schemas_soltados += 1
  → pytest_sessionfinish                           cerrar_sesion (red de seguridad) y exitstatus=1 si hay residuos
```

| Registro | Valor |
|---|---|
| `SCHEMA_NAME_SOURCE` | `t_` + 12 hex de `uuid4` por `crear_motor_de_prueba` |
| `ENGINE_SCOPE` | el de la fixture que llama: FUNCIÓN en las 12 suites (un motor + un schema por prueba) |
| `CREATE_ALL_SITE` / `CREATE_ALL_COUNT` | en cada fixture `db_session` · una vez por prueba (214 por corrida solo en las 12) |
| `DROP_SITE` / `DROP_OWNER` | `pg_harness.soltar_schema` · el ámbito PGLIFE que lo creó (prueba o módulo) |
| `PGLIFE_SCOPE` | prueba y módulo (fixtures autouse del conftest, se desmontan después que las del módulo) |
| `SCHEMA_TRACKING` | `Ambito.motores` + `INFORME` (creados/soltados/conexiones cortadas/residuos) |
| `FAILURE_CLEANUP` | el finalizador de la fixture autouse corre pase o falle; `cerrar_sesion` al final |
| `RESIDUAL_GUARD` | `pytest_sessionfinish` fuerza `exitstatus=1` si quedan residuos; `qa/pg-test-residuos.py` para corridas muertas |
| Módulo ya soportado | sí: un `make_engine()` dentro de una fixture de módulo se apunta al ámbito del módulo y se suelta con él (PGLIFE) |
| SQLite | `make_engine()` sin `KONTROL_TEST_DB_URL` → `sqlite+pysqlite:///:memory:` con `StaticPool` por prueba: coste de milisegundos; `SQLITE_SCHEMA_CONCEPT = base en memoria nueva por motor`; `SQLITE_RESET_MECHANISM = motor nuevo` |
