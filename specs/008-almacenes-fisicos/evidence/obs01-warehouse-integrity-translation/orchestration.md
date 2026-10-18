# Orquestación (regla permanente 1: Claude diseña y escribe el brief · DeepSeek escribe el código y las pruebas · Claude audita, aplica y certifica)
| Delegación | Modelo | Tokens | Coste | Auditoría | Hallazgos devueltos | Aplicado |
|---|---|---|---|---|---|---|
| T02 intento | `deepseek-v4-pro` | 11 167 / 8 424 | $0,0122 | producto **PASS** · prueba **REJECT** | prueba: F401 ×3, UP038; `GET …/zones` es lista y no había zona (02/05/07/09); `NodeIn.name` obligatorio (03/08); la 10 dependía de otras pruebas y llamaba a `make_engine()`; `__import__`; bucle muerto en la 14 | producto sí (tal cual) |
| T02 corrección 1 | `pro` | 12 895 / 5 253 | $0,0102 | **PASS** salvo un hallazgo menor | `restriccion_unica` importada dentro de la 11 (contra H6) | sí (tal cual) |
| T02 corrección 2 | `flash` | 1 823 / 674 | $0,0004 | **REJECT** | SEARCH sin coincidencia (0 apariciones): el puente truncó el fichero de contexto | no |
| T02b (reclasificación tras 2 reintentos; fragmentos literales en el brief) | `flash` | 886 / 432 | $0,0002 | **PASS** | — | sí (tal cual) |
TASKS 2 (T02, T02b) · CLAUDE_BRIEFS 4 · DEEPSEEK_CALLS 4 · RETRIES 2 (T02) · EGRESS_CHECKS 4/4 todo 0 · AUDIT_PASS 3 ·
AUDIT_FAIL 2 · CHANGES_APPLIED 3 · CHANGES_REJECTED 2 · COST **$0,0230**. Claude no escribió ni retocó ninguna línea de producto
ni de prueba; aplicó los bloques con un aplicador literal (SEARCH único o rechazo) desde la respuesta cruda de DeepSeek.
El puente abrevió el contexto en T02 (`warehouse_api.py`) y en las dos correcciones; los SEARCH se verificaron contra el
fichero real (deuda conocida `EJECUTOR-ABREVIA-EL-CONTEXTO`).
ROUTES_ALLOWED: `app/core/integrity.py`, `app/modules/organization/warehouse_api.py`, `tests/test_warehouse_integrity.py` ·
ROUTES_FORBIDDEN (respetadas): modelos, `structure.py`, `alembic/**`, `tests/conftest.py`, `test_warehouse_structure.py`,
`app/core/errors.py`, otros llamantes de `es_violacion_unica`, frontend, `qa/**`, `.env*`.
