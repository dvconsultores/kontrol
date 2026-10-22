# Certificación en un árbol aislado sin `.venv` (V5, PostgreSQL de QA)

El `.venv` real del repositorio no se tocó. El árbol aislado vive en el scratchpad y se borra al terminar. En él,
`resources/backend/.venv` no existe (`SIN_VENV=1`).

| Momento | Árbol | Conjunto | Resultado |
|---|---|---|---|
| Antes (`d20da5b`) | `git archive d20da5b` | 15 ficheros de migración | **17 failed, 71 errors, 7 passed, 3 skipped**. Los 88 fallos son `FileNotFoundError: …/.venv/bin/alembic`, y las 3 omisiones son silenciosas (`test_migrations_offline.py`): **NO_VENV_PRE_RESULT = FAIL** |
| Después (T1+T2+T3) | ficheros versionados del árbol de trabajo y ficheros nuevos del ciclo | 15 ficheros de migración, `test_alembic_interprete_certificado.py` y `test_migraciones_url_porcentaje.py` | **140 passed, 0 failed, 0 errors, 0 skipped**: **NO_VENV_TREE_GREEN = 1** |

Procedencia medida con la sonda en el árbol aislado: los 73 subprocesos alembic corren con `v5/bin/python` CPython
**3.13.16**; el ejecutable real es el `ld-linux` del rootfs de la imagen, con alembic 1.14.0 y SQLAlchemy 2.0.36 de
`v5/lib/python3.13/site-packages`. Ninguno corre en el anfitrión ni en V0.

## Revalidación sobre el árbol final (2026-10-22, tras T4 y T5)

| Árbol | Conjunto | Resultado |
|---|---|---|
| Ficheros versionados y nuevos del árbol de trabajo (`git ls-files -co --exclude-standard`), copiados al scratchpad **sin** `resources/backend/.venv`; V5 3.13.16; PostgreSQL de QA | los mismos 15 ficheros de migración, `test_alembic_interprete_certificado.py` (ahora con AIC-08) y `test_migraciones_url_porcentaje.py` | **141 passed, 0 failed, 0 errors, 0 skipped**: **NO_VENV_TREE_GREEN = 1** |

Corrección de datos: en `fixed-path-inventory.json`, las rutas de `tests/` llevaban duplicado el prefijo `resources/backend/`. Se normalizaron; el contenido medido no cambia.
