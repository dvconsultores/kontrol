# Orquestación (regla permanente 1: Claude brief → DeepSeek código → Claude audita, aplica y certifica)
| Delegación | Modelo | Tokens | Coste | Auditoría | Hallazgos devueltos | Aplicado |
|---|---|---|---|---|---|---|
| T07 intento | `deepseek-v4-pro` | 8 313 / 7 195 | $0,0098 | **REJECT** | H1 línea original eliminada (csync_06) · H2 aserción debilitada (csync_13 `"PRIVATE"` → `"PRIVATE KEY"`) · H3 csync_04 falla (la clave de idempotencia incluye la licencia vigente: error de diseño del brief, corregido con `_sincronizacion_previa`) · H4 faltaba el fichero de regresión | no |
| T07 corrección 1 | `pro` | 8 297 / 8 942 | $0,0113 | módulo **PASS** · regresión **REJECT** | ruff UP038 y F841; contrato estático comparaba `ast.unparse` con comillas dobles; `primera_llamada` más laxa que el contrato | módulo sí (tal cual) |
| T07 corrección 2 | `pro` | 3 533 / 2 829 | $0,0039 | **PASS** | — | sí (tal cual) |
| T07b (reclasificación tras agotar 2 reintentos; superviviente M-09) | `flash` | 985 / 695 | $0,0003 | **REJECT** | lista de ejecutadas vacía: `-q` + `-v` → verbosidad 0 (defecto del brief) | no |
| T07b corrección 1 | `flash` | 989 / 775 | $0,0004 | **PASS** | — | sí (tal cual) |
TASKS 2 (T07, T07b) · CLAUDE_BRIEFS 5 · DEEPSEEK_CALLS 5 · RETRIES 3 (2 en T07, 1 en T07b) · EGRESS_CHECKS 5/5 todo 0 · AUDIT_PASS 3 ·
AUDIT_FAIL 3 · CHANGES_APPLIED 3 · CHANGES_REJECTED 3 · COST **$0,0257**. Claude no escribió ni retocó ninguna línea de prueba.
ROUTES_ALLOWED: `tests/test_license_sync_client.py`, `tests/test_license_sync_client_aislamiento.py` · ROUTES_FORBIDDEN: `app/**`,
`central_authority/**`, `tests/conftest.py`, otras pruebas, `qa/**`, `.env*` (respetadas).
