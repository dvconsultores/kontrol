# Mutaciones · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS (`mutation-run.txt`, `mutation-script.sh`)
Detectores: `tests/test_documents_legacy_import.py` + `tests/test_documents_legacy_import_contrato.py` (y ACS para la primitiva);
analizador real exportado; SEARCH/REPLACE único; `__pycache__` purgado; restauración byte a byte. GOOD 12/12.

| Id | Mutación | Detector | Resultado |
|---|---|---|---|
| M-01 | volver a `make_engine()` | contrato (motor por sesión) | muerta |
| M-02 | HTTP con la sesión de escritura abierta (caso 5) | contrato (orden `(_company_id(), _actor())` antes de `_FACTORY()`) | muerta |
| M-03 | omitir el `commit` antes del `GET /descargar` | la propia prueba (404) + contrato (≥ 7 commits) | muerta |
| M-04 | `:memory:` privado por conexión | las 7 importadoras + ACS-01…08 | muerta |
| M-05 | la API comparte una sola sesión con las pruebas | 1.ª pasada SEARCH mal formado; 2.ª **sobrevivió** (equivalente en comportamiento para este módulo: no hay cruce de sesiones) → contrato exige sesión por petición en `_override_get_db` → 3.ª muerta | muerta |
| M-06 / M-07 | debilitar el 409 / la clasificación esperada | contrato (aserciones literales) | muertas |
| M-08 / M-09 | ocultar excepción de hilo / vector incompleto | **no aplican** (el módulo no usa hilos): no se cuentan | — |
| M-10 | bucle de reintento | 1.ª pasada **sobrevivió** → contrato prohíbe `range(`/`while ` → muerta | muerta |
| M-11 | `sleep` | contrato | muerta |
| M-12 | `skipif` en una importadora | contrato | muerta |
| M-13 | apagar el analizador en el fixture | contrato (`set_scanner`/`DisabledScanner`) | muerta |
| M-14 | el ayudante vuelve a llamar a la API | contrato (ayudantes sin API) | muerta |
| M-15 | esquema/migración | `git diff -- alembic/` vacío (tripwire, no se cuenta) | — |

**12/12 muertas de las aplicables** (M-05 y M-10 tras reforzar el contrato; documentado); equivalentes contadas 0.
