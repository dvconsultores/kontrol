# Orquestación (regla permanente 1)
| Delegación | Modelo | Tokens | Coste | Auditoría | Hallazgos | Aplicado |
|---|---|---|---|---|---|---|
| B02 intento | `deepseek-v4-pro` | 5 615 / 5 159 | $0,0068 | producto + O01-06 **PASS** · prueba **REJECT** | imports inventados (`app.shared.setup`, `app.shared.sql`, `PASSWORD` de conftest); `_bootstrap_roles` en módulo equivocado; I001, F401/F811, UP038 ×2; ruta relativa en B-15; imports dentro de funciones | producto y O01-06 sí (tal cual) |
| B02 corrección 1 | `pro` | 5 010 / 4 270 | $0,0058 | **PASS** | — (después, mutaciones M11 y M12 sobreviven) | sí (tal cual) |
| B02 corrección 2 | `pro` | 1 308 / 631 | $0,0010 | **REJECT** | B-16/B-17 usaban el dict de cabeceras como cliente (`'dict' object has no attribute 'post'`) y una ruta sin prefijo | no |
| B02b (reclasificación; contexto y REPLACE fijados en el brief) | `flash` | 1 390 / 1 014 | $0,0005 | **PASS** | — | sí (tal cual; solo añade líneas) |
TASKS 2 (B02, B02b) · CLAUDE_BRIEFS 4 · DEEPSEEK_CALLS 4 · RETRIES 2 · EGRESS_CHECKS 4/4 todo 0 · AUDIT_PASS 3 · AUDIT_FAIL 2 ·
CHANGES_APPLIED 3 · CHANGES_REJECTED 2 · COST **$0,0141**. Claude no escribió ni retocó código de producto ni de prueba. Los
fragmentos literales viajaron dentro del brief, y el puente no truncó nada esta vez.
ROUTES_ALLOWED: `warehouse_api.py`, `tests/test_warehouse_branch_scope.py`, `tests/test_warehouse_integrity.py` (solo O01-06).
ROUTES_FORBIDDEN respetadas.
