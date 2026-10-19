# Orquestación (regla permanente 1)
| Delegación | Modelo | Tokens | Coste | Auditoría | Hallazgos | Aplicado |
|---|---|---|---|---|---|---|
| K02 intento | `deepseek-v4-pro` | 9 244 / 10 540 | $0,0131 | producto y O01 aplicados; **REJECT** parcial | mypy `"Base" has no attribute "company_id"` (defecto del diseño de Claude: `db.get` con una unión de tipos); ruff I001 en el import de O01; F401 y F841 en la prueba nueva; C19 sin el alta en almacén ajeno; C28 sobrescribía el acumulador; C29 sin el orden de `_create` | llamadas y O01-07/08/09 sí; prueba no |
| K02 corrección 1 | `pro` | 9 983 / 8 192 | $0,0114 | **REJECT** | respuesta truncada en el tope de 8 192 tokens (`finish_reason: length`); faltaban K1 y K2 | no |
| K02a (reclasificación: ayudante + import) | `flash` | 1 434 / 1 143 | $0,0005 | **PASS** | — | sí, tal cual |
| K02b (reclasificación: prueba completa, tope 32 000) | `pro` | 9 357 / 8 604 | $0,0114 | **PASS** | — | sí, tal cual |
- **Totales.** TASKS 3 (K02, K02a, K02b) · CLAUDE_BRIEFS 4 · DEEPSEEK_CALLS 4 · RETRIES 1, tras el cual se reclasificó en dos
  subtareas · EGRESS_CHECKS 4/4 todo 0 · AUDIT_PASS 3 (incluye el producto parcial de K02) · AUDIT_FAIL 2 ·
  CHANGES_APPLIED 3 · CHANGES_REJECTED 2 · COST **$0,0364**.
- **Autoría.** Claude no escribió ni retocó código de producto ni de prueba.
- **Error de Claude.** Una nota explicativa de K02b perdió dos fragmentos entre comillas invertidas, porque bash los sustituyó
  en un heredoc sin comillas. No afectó a lo pedido: los hallazgos, los cambios y la referencia viajaron desde fichero.
