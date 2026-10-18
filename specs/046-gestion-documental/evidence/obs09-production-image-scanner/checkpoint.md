# Checkpoint · OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER (2026-10-18 02:30)
| Registro | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `6779f96` / `6779f96` / `6779f96` |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_6779F96` | `develop` · limpio · 0 |
| `RUN_DATABASES` · `T_SCHEMAS` · `EPHEMERAL_STORAGE_ROOTS` · `QA_PORT_STATE` | 0 · 0 · 0 · libres (8000/8010/5173/3310) |
| PostgreSQL de QA | el reinicio del equipo vació `/tmp`: el clúster `kontrol-pgdata-045` no existía; reprovisionado con `qa/pg-provision.sh start` + `mkdb ktest` (acción canónica de QA; sin cambio en el repositorio) |
| Almacén legado `<tmp>/kontrol-test-storage` | **ya no existe**: lo eliminó la limpieza de `/tmp` del sistema al reiniciar, no este ciclo (OBS-06 lo había conservado) |
| Runtime de contenedores | **ninguno**: `docker`, `podman` y `nerdctl` no están instalados y no hay `sudo` sin contraseña → la construcción de la imagen y la composición no pueden ejecutarse en este equipo (`COMPOSE_RUNTIME_UNAVAILABLE`); ver `implementation-decision.md` |
| ClamAV de QA | prefijo `<qa-cache>` con `clamscan` 1.4.3 y firmas (main 63 · daily 28153 · bytecode 339); `clamav-daemon` 1.4.3 descargable de Debian sin root (`apt-get download`, SHA256 verificada) |
| Decisión | `[x] OBS-09`, opción **B** ratificada: `clamd` como servicio aparte, INSTREAM, sin rutas ni montaje del almacén, puerto interno, falso seguro sin alternativa implícita; cambio mínimo de producto autorizado (adaptador) |
| MASTER57 / SPEC057 / NEXT | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED |
