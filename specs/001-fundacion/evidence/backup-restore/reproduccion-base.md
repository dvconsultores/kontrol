# Rojo de línea base (f24e74e, 2026-10-28)

Herramientas tal como están, contra destinos del scratchpad de Claude. Sin datos reales.

| ID | Prueba | Resultado medido |
|---|---|---|
| BK-RED-01 | `scripts/backup.sh` con `KONTROL_DB_URL` de QA | **rc 127** (`docker: orden no encontrada`): la estación no tiene Docker y el guion depende de él. Aun así **deja un directorio fechado vacío**. Con Docker, su alcance sería solo `db.sql`: el almacén y el estado de licencia no se copian (lo dice el propio guion) y no hay manifiesto |
| BK-RED-01b | `kontrol.py backup` | **rc 0** con «Backup en …/kontrol-backup-<fecha>» y un **directorio vacío**: éxito engañoso |
| BK-RED-02 | `kontrol.py restore` y `scripts/restore.sh` | **rc 0** imprimiendo el runbook: no se restaura nada. `restore.sh` descifra en un temporal y lo borra al salir |
| BK-RED-03 | Almacén tras restaurar | No aplica: no existe restauración. El almacén documental no se copiaba nunca |
| BK-RED-04 | Licencia reverificada tras restaurar | No hay restauración. La reverificación al arrancar existe en el producto y la certificación la ejercita |
| BK-RED-05 | Copia corrupta | Sin manifiesto ni AEAD: `openssl -aes-256-cbc` no detecta la manipulación con garantía, y la clave viaja como `pass:<clave>` en la línea de órdenes, visible en `ps` |

DT-11 confirmado: **la copia y la restauración no se habían ejecutado nunca de verdad.**
