# D8 · Orden de captura de la configuración
Con la inyección en `pytest_configure`, un módulo importa `app.main`, crea la aplicación y un `TestClient` (salud 200) y
después otro módulo hace el escenario.
| Registro | Valor |
|---|---|
| `get_settings().storage_path` tras `create_app` + `TestClient` = entorno inyectado | **YES** |
| Proveedor documental y exportaciones bajo la raíz inyectada | **YES** / **YES** |
| Misma raíz en los dos módulos del proceso | **YES** |
| Raíz no fija · sin rastro al terminar | **YES** · **YES** |
Conclusión: `pytest_configure` precede a toda construcción de `Settings` (la primera ocurre al importar `app.main` en la
colección) y al primer uso del proveedor documental; no hay `SETTINGS_CAPTURE_DEFECT` ni `PRODUCT_PATH_CONTRACT`: la
corrección es puramente del arnés.
