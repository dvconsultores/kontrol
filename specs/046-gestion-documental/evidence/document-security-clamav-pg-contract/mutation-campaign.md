# Mutaciones M-01…M-10 · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS (`mutation-run.txt`, `mutation-script.sh`)

Detector: `tests/test_documents_carreras_contrato.py` (DOCENV-05/12/13/14/15) en SQLite; SEARCH/REPLACE único, `__pycache__`
purgado, `PYTHONDONTWRITEBYTECODE=1`, restauración desde copias GOOD byte a byte. GOOD 7/7.

| Id | Mutación (`test_documents_security.py`) | MUTATED | Detector | RESTORED |
|---|---|---|---|---|
| M-01 | quitar el marcador a `test_tres_subidas…` | 2 failed | DOCENV-05 (conjunto exacto), DOCENV-12 (omisión en SQLite) | 7 passed |
| M-02 | quitar el marcador a la carrera parametrizada | 2 failed | DOCENV-05, DOCENV-12 | 7 passed |
| M-03 | marcar PostgreSQL-only `test_amz_10` (no es carrera) | 1 failed | DOCENV-05 | 7 passed |
| M-04 | razón «solo PostgreSQL» sin FR-046-115/P21 | 1.ª pasada **sobrevivió** (la autoridad se buscaba en todo el fichero, y el comentario la contenía) → se comprueba la razón del propio marcador → 1 failed | DOCENV-12 (autoridad) | 7 passed |
| M-05 | `PG = True` (el marcador nunca omite) | 2 failed | DOCENV-12 (`modulo.PG is pg`), DOCENV-12 (omisión) | 7 passed |
| M-06 | `skipif(True, …)` (omite también en PostgreSQL) | 1 failed | DOCENV-12 (autoridad/forma) | 7 passed |
| M-07 | mecanismo de carrera (`carrera`) en una prueba sin marcador | 1.ª pasada **sobrevivió** (`_ = carrera` no era una llamada) → nombres por AST (no prosa: «carrera» aparece en docstrings) → 1 failed | DOCENV-12 (primitivas) | 7 passed |
| M-08 | `scanning.set_scanner(scanning.DisabledScanner())` en el fixture | 1 failed | DOCENV-14 | 7 passed |
| M-09 | `status_code in (200, 422)` tras una subida | 1 failed | DOCENV-15 | 7 passed |
| M-10 | quitar el marcador a la séptima carrera (`test_subidas_a_documentos_distintos_no_se_esperan`) | 2 failed | DOCENV-05, DOCENV-12 | 7 passed |

**10/10 muertas** (M-04 y M-07 tras reforzar el contrato; documentado). Hallazgo de la campaña: al pasar de buscar texto a
analizar el AST apareció una **séptima** prueba con mecanismo de carrera dependiente de PostgreSQL
(`test_subidas_a_documentos_distintos_no_se_esperan`: una subida sin confirmar en `_FACTORY` y otra petición que **no debe
esperar**, imposible con el bloqueo de toda la base de SQLite); se marcó también. Equivalentes contadas: 0.
