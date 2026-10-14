# Implementación (etapa 2) · producto 0 · analizador 0 · migración/esquema 0
`tests/test_documents_legacy_import.py`: (1) fixture sobre `with motor_para_hilos("documents-legacy-import") as engine:`
(mismo cuerpo, sangrado, comentario con el porqué); (2) `_doc_type(db, company)` y `_reference(db, company, …)` reciben la
empresa en vez de llamar a la API; (3) en las siete pruebas, `company, actor = _company_id(), _actor()` **antes** de
`db = _FACTORY()` (comentario de tres líneas) y `actor=actor` en la llamada al servicio. Ninguna aserción cambia; el
`db.commit()` final de cada prueba sigue donde estaba (`DURABLE_BEFORE_HTTP` no aplica: el único HTTP posterior,
`GET /descargar`, ya ocurría tras `db.close()`). `tests/test_documents_legacy_import_contrato.py` (nuevo): motor por
sesión; en cada importadora la tupla `(_company_id(), _actor())` precede a `_FACTORY()` y dentro del `try` no aparecen
`_company_id`, `_actor`, `_headers` ni `_CLIENT` (por AST); los ayudantes reciben `company` y no llaman a la API; las
aserciones del legado presentes literalmente; ≥ 7 `db.commit()`; sin skip/xfail/sleep/retry/Lock ni manipulación del analizador.
