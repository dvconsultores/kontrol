# Medición 01 · Estado previo del directorio compartido

Inspección segura ANTES de ejecutar ninguna suite de este ciclo (`stat`, `find -printf`; nunca se lee el
contenido de la clave). `<tmp>` = `tempfile.gettempdir()` del equipo.

| Registro | Valor |
|---|---|
| Directorio | `<tmp>/kontrol-test-license` |
| `DIRECTORY_EXISTS` | **sí** (modo 775, mtime del directorio 2026-10-13 05:51:38) |
| `FILE_COUNT` | 1 |
| `KEY_FILE_EXISTS` | **sí**: `installation_private_key.pem`, 119 bytes (PKCS8 Ed25519 sin cifrar) |
| `MODE` | 0600 |
| `AGE/MTIME` del fichero (saneado) | 06:19:39 del mismo día: lo dejó la corrida anterior a este ciclo |
| `OTHER_STATE_FILES` | 0 (el producto solo escribe la clave en el volumen: `service.py` `os.makedirs` + `os.open(..., 0o600)`) |
| Huella sintética inicial (sha256/16) | `d1c0ac32416b7356` (clave SINTÉTICA generada por una prueba; no es material real) |

Vecinos observados, **fuera del alcance de este ciclo** (no se tocan; se anotan en el delta):

| Directorio | Estado |
|---|---|
| `<tmp>/kontrol-test-storage` | existe, 63 entradas acumuladas (`exports/*.csv|pdf`, `documents/`) desde 2026-10-12 |
| `<tmp>/kontrol-test-backups` | ausente |
