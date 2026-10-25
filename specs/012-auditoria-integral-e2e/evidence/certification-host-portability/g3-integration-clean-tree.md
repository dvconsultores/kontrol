# G3 — prueba de integración en un árbol limpio sin `.venv` (2026-10-25, MEASURED)

Árbol exportado con `git archive` de un árbol temporal (índice y objetos en el scratchpad, sin escribir en el
repositorio), sin `resources/backend/.venv` ni `node_modules`. HOME de certificación propio en el scratchpad.

| Paso | Resultado |
|---|---|
| `aprovisionar_postgres_qa(ctx)` 1.ª vez | descarga de la rueda y del `.deb` por https, sha256 verificados; instalación `postgres-qa/d271eb859971e9c1`; `reutilizada = False`; `.venv` en la ruta: no |
| 2.ª vez | descargas reverificadas, instalación verificada contra RECORD y `btree_gist`; `reutilizada = True` |
| `POSTGRES_QA_SOURCE` | postgres 16.2 · rueda `d595789b…8813` · btree_gist `c9de1cc6…d699` · `verificada = 1` · `venv_preexistente_requerido = 0` |
| `KONTROL_PGBIN=<fijado> KONTROL_PG_SIN_COMPILAR=1 bash qa/pg-provision.sh start` (puerto 55498, datos en el scratchpad) | `server started`; `PostgreSQL 16.2 … compiled by gcc 10.2.1` (los binarios de la rueda) |
| `/proc/<postmaster>/exe` | `<home de certificación>/postgres-qa/d271eb859971e9c1/pgserver/pginstall/bin/postgres` |
| `CREATE EXTENSION btree_gist` | versión 1.7 |
| `pg-provision.sh stop` | `server stopped`; puerto 55498 libre |

Sin compilador en el anfitrión (`gcc` y `make` ausentes), sin PATH ni descarga flotante.
