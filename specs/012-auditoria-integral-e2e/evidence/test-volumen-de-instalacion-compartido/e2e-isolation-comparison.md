# Comparación con el aislamiento del runner E2E (SPEC052, `qa/e2e_corrida.py`)

| Registro | Valor |
|---|---|
| `E2E_VOLUME_SCOPE` | por corrida (`run_id`) |
| `E2E_VOLUME_PATH_SOURCE` | `self.estado = Path(KONTROL_E2E_STATE_DIR o /tmp/kontrol-e2e) / run_id` → `entorno_de_procesos()` fija `KONTROL_INSTALLATION_VOLUME_PATH = estado/license`, `KONTROL_STORAGE_PATH = estado/storage`, `KONTROL_BACKUP_PATH = estado/backups` (líneas 191-206) |
| `E2E_CLEANUP` | `shutil.rmtree(self.estado)` al terminar (línea 612; el manifiesto anota `estado: eliminado`) |
| `SHARED_WITH_BACKEND_UNIT_TESTS` | **false**: el runner nunca usa `kontrol-test-license`; `test_e2e_corrida_13` ya exige que las cinco rutas de estado empiecen por `corrida.estado` |
| Conclusión | el patrón «un estado efímero por proceso, eliminado al terminar» ya está ratificado en el repositorio; el arnés de pytest es el único que sigue con una ruta fija compartida. El runner **no cambia** en este ciclo |
