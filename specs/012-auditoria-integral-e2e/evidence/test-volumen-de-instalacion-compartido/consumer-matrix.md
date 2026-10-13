# Matriz de consumidores del volumen de instalación en `tests/` (HEAD 1f28c83)

Generada por un guion de análisis de Claude (búsqueda estática por patrones; conteos de coincidencias por fichero).
Columnas: WRITES_KEY = `initialize(` / `get_or_create_installation(` (escribe la clave en el volumen configurado) · READS_KEY(producto) = `sync_license(` / `_installation_private_key(` (carga la clave) · READS_KEY(ruta) = `_private_key_path(` / `installation_volume_path` / `installation_private_key.pem` · PATCHES_OWN_VOLUME = fija su propio volumen (`setenv`, `setattr(_private_key_path)`, entorno de subproceso) · CLEARS_CACHE · MODULE_SCOPE_WORLD · THREADS · SUBPROCESS · TESTCLIENT.

```
FILE | CLASSIFICATION | WRITES_KEY | READS_KEY | READS_KEY | PATCHES_OWN_VOLUME | CLEARS_CACHE | MODULE_SCOPE_WORLD | THREADS | SUBPROCESS | TESTCLIENT_LIFESPAN
central/test_central_authority_pg.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 0
central/test_central_challenge_rate_limit.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1
central/test_central_challenge_rate_limit_pg.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1
central/test_central_sync_auth.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1
central/test_central_sync_auth_pg.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1
concurrency.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
conftest.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0
sondas_pg/sonda_modulo.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_audit_total_count.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_documents_migration_0024.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 0
test_licensing_offline_sqlite.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_mc_preflight.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_migraciones_url_porcentaje.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 1 | 0
test_n10_convergence.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_n8_contract.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_pg_harness_lifecycle.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0
test_spec019_migration_0044.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0
test_spec020_migration_0045.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0
test_spec021_migration_0047.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0
test_spec022_migration_0048.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 1 | 0
test_spec023_migration_0046.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0
test_spec030_concurrency.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec030_migration_0043.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0
test_spec031_picking.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec032_picking_execution.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec033_confirmation.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec034_billing.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec035_dispatch.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec047_notifications.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0
test_spec047_scheduler.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0
test_spec047_schema.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0
test_spec052_migration_0033_legacy.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0
test_uom_architecture.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_uom_backfill.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0
test_warehouse_migration_0018.py | INDEPENDENT(settings/threads only) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0
central/test_central_authority.py | PATCHES_OWN_VOLUME | 2 | 1 | 0 | 2 | 4 | 0 | 0 | 0 | 1
test_backend_keepalive.py | PATCHES_OWN_VOLUME | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0
test_e2e_base_ciclo.py | PATCHES_OWN_VOLUME | 0 | 0 | 0 | 1 | 0 | 3 | 0 | 3 | 0
test_installation_key_reference.py | PATCHES_OWN_VOLUME | 3 | 1 | 4 | 1 | 1 | 0 | 0 | 0 | 1
test_migrations_offline.py | PATCHES_OWN_VOLUME | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 2 | 0
test_spec004_installation_race.py | PATCHES_OWN_VOLUME | 6 | 0 | 3 | 1 | 2 | 1 | 2 | 1 | 0
test_e2e_corrida.py | READS_SHARED_VOLUME_ONLY | 0 | 0 | 3 | 0 | 0 | 0 | 1 | 0 | 0
test_sync_auth_contract.py | READS_SHARED_VOLUME_ONLY | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0
audit_world.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 1
conftest_multicompany.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_approvals_api.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_audit_integration.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_audit_tenant_isolation.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_auth_session_rotation.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_company_list_envelope.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_company_search.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_documents.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_documents_legacy_import.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_documents_security.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_homologation.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0
test_idempotency_concurrency.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_license_access.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_license_import_access.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_license_import_race.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0
test_license_key_rotation.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 3 | 1 | 0 | 0 | 1
test_license_revision_client.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_license_revision_race.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 0 | 3 | 0 | 0
test_license_state_reverification.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 3 | 1 | 0 | 0 | 4
test_license_sync_rate_limit_client.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 2
test_openapi_security.py | USES_SHARED_VOLUME(writes key via initialize) | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0
test_password_reset.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_picklist_duplicada.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_process_flows.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_qa_fixes.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_roles_create.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_security_integration.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 1
test_services.py | USES_SHARED_VOLUME(writes key via initialize) | 7 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0
test_system_access.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_system_version.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 4 | 1 | 0 | 1 | 1
test_uom_conversion.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_warehouse_list_cost.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1
test_warehouse_structure.py | USES_SHARED_VOLUME(writes key via initialize) | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1
test_license_period_rollback.py | WRITES_AND_READS_SAME_SCOPE(shared path) | 1 | 0 | 2 | 0 | 2 | 1 | 0 | 0 | 1
test_license_sync_client.py | WRITES_AND_READS_SAME_SCOPE(shared path) | 1 | 8 | 2 | 0 | 2 | 1 | 0 | 0 | 2
test_license_trust_anchor.py | WRITES_AND_READS_SAME_SCOPE(shared path) | 1 | 0 | 4 | 0 | 4 | 1 | 0 | 0 | 1
test_licensing_central.py | WRITES_AND_READS_SAME_SCOPE(shared path) | 1 | 7 | 0 | 0 | 2 | 0 | 0 | 0 | 0

RESUMEN: {'USES_SHARED_VOLUME(writes key via initialize)': 34, 'INDEPENDENT(settings/threads only)': 35, 'PATCHES_OWN_VOLUME': 6, 'READS_SHARED_VOLUME_ONLY': 2, 'WRITES_AND_READS_SAME_SCOPE(shared path)': 4} ficheros: 81
```

Resumen: 81 ficheros con alguna coincidencia · USES_SHARED_VOLUME 34 · WRITES_AND_READS_SAME_SCOPE 4 (`test_license_period_rollback`, `test_license_sync_client`, `test_license_trust_anchor`, `test_licensing_central`) · PATCHES_OWN_VOLUME 6 · READS_SHARED_VOLUME_ONLY 2 (son coincidencias de cadena: `test_e2e_corrida` comprueba el entorno del runner; `test_sync_auth_contract` genera sus propias claves Ed25519 en memoria y no toca el volumen) · INDEPENDENT 35 · **ASSUMES_PREEXISTING_KEY 0** · **UNKNOWN 0**.

Ámbitos: `scope="module"` en los mundos; **ningún** `scope="class"` ni `scope="session"` en `tests/`. Hilos (`test_license_revision_race`, `test_license_import_race`, `test_spec004_installation_race`…) leen o crean la instalación de su propio ámbito; ningún hilo escribe la clave de otro mundo. Subprocesos de pruebas (migraciones, pg_harness, keepalive, E2E) o fijan su propio volumen o no escriben claves.
