# CTL05_RECONCILIATION_REPORT · 2026-11-11

```
OLD_BASE          = bb64b41
CURRENT_ORIGIN    = b73c171 (fix(inventory): dispatch consumes cost layers, P2)
MERGE_BASE        = bb64b41
ORIGIN_MOVED      = 1 commit (P2, Enterprise)
```

**Integración (sin rebase, sin reset destructivo y sin force):**
1. Respaldo `herramientas/ctl05/ctl05-candidato-2.patch` (3.243 líneas).
2. Stash `ctl05-pre-b73c171`.
3. `merge --ff-only origin/develop`.
4. `stash apply`.

**P1_CHANGED_FILES (candidato CTL-05):**
- **Ficheros nuevos:**
  - `alembic/versions/0098_gov_ctl05_rendicion.py`;
  - `government/{api,schemas,service}_rendicion.py`;
  - `tests/test_gov_ctl05_rendicion.py`;
  - `specs/gov-ctl-05-expediente-de-cuenta/*`.
- **Ficheros modificados:** `main.py`, `government/models.py`, `government/service_auditoria.py`, `identity_access/mfa_policy.py`, `setup/api.py`, `shared/audit_catalog_entries.py`, `tests/test_audit_catalog_backup.py` y `tests/test_mfa_policy.py`.
- **Pruebas de cabeza Alembic:** `tests/test_installation_key_reference.py`, `tests/test_migraciones_url_porcentaje.py` y `tests/test_spec018_migration_timestamps.py`.

**P2_CHANGED_FILES (`b73c171`):**
- **Producto:** `0098_dispatch_cost_relief.py`, `inventory/{models,service}.py` y `sales/service.py`.
- **Catálogo:** `audit_catalog_entries.py` (detalle de `SHIPMENT_CONFIRMED`).
- **Pruebas:** las 3 de cabeza Alembic y `test_spec035_*` / `test_spec036_returns.py`.
- **E2E:** `e2e/importaciones.spec.ts`.
- **Documentación:** documentos de Enterprise.

**OVERLAPPING_FILES:**
- **`audit_catalog_entries.py`:** se fusionó sola. Conserva el detalle `("cost", "order_id")` de P2 y las 11 entradas `GOV_RENDITION_*`.
- **Las 3 pruebas de cabeza Alembic:** había conflicto y se resolvió con el lado publicado (`0098_dispatch_cost_relief`). El valor final lo fijará DeepSeek junto con la revisión renumerada.

**Resultado de la reconciliación:**
```
SEMANTIC_CONFLICTS    = 0
ALEMBIC_CONFLICT      = 1. Dos revisiones 0098 con el mismo down_revision 0097 dan dos cabezas.
                        CTL-05 pasa a 0099_gov_ctl05_rendicion con down_revision 0098_dispatch_cost_relief
                        (la escribe DeepSeek).
SHARED_CORE_CONFLICT  = 0. P2 no tocó identity_access, setup, government ni audit_catalog fuera de la línea ventas.
ENTERPRISE_IMPACT     = 0. CTL-05 no toca inventory ni sales.
CATALOGO              = P2 no añadió entradas (462 + 11 = 473 sigue valiendo).
SAFE_TO_CONTINUE      = 1
```
