# Patrones hermanos (instantes a nivel de módulo en pruebas)
| Fichero | Variable | Uso | Riesgo | En alcance |
|---|---|---|---|---|
| `test_licensing_central.py` | `SERVER_TIME = now + 5 min` | reloj del servidor falso y aserción de igualdad | **defecto** (frontera de operación = importación) | sí |
| `test_license_import_access.py`, `test_license_trust_anchor.py` | `AHORA = now.replace(microsecond=0)` | fechas de licencias sintéticas | referencia de **fecha civil** (validez por días), no frontera de operación | no (sin evidencia de fallo; registrado) |
| `test_license_*_race/rollback/revision/key_rotation/sync_client/state_reverification.py` | `HOY = now.astimezone(CARACAS)` | fechas de período | ídem | no |
Ningún hermano compara un instante de importación con uno persistido por una operación posterior con regla monótona.
