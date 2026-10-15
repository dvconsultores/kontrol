# Telemetría OBS-12 tras OBS-06
| Campo del manifiesto (`residuos`) | Semántica |
|---|---|
| `modo_almacen` | `PROCESS_ISOLATED` (`HARNESS_STORAGE_MODE`) |
| `efimeros` | raíces `kontrol-test-almacen-*`, `kontrol-test-sqlite-*`, `kontrol-test-license-*` presentes **tras** la corrida: residuo (debe ser `[]`; `ORPHAN_HARNESS_ROOTS`) |
| `almacen_por_proceso` | el subconjunto `kontrol-test-almacen-*` (`POST_RUN_STORAGE_RESIDUE` y `POST_RUN_BACKUP_RESIDUE`, que viven en la misma raíz) |
| `almacen_fijo_legado_presente` | `<tmp>/kontrol-test-storage` existe (estado legado anterior a OBS-06); informativo, nunca falla la corrida |
`CURRENT_RUN_STORAGE_PRESENT`/`BACKUP_PRESENT` durante la corrida: la raíz existe mientras pytest corre (O06-08) y
desaparece en `pytest_unconfigure`, antes de que `suite_tiempos` inventaríe. Rutas saneadas (`<tmp>`). Duración monotónica,
perfil, anfitrión, analizador y anomalía no bloqueante: sin cambio (O12-01…08, 11…20 intactas). OBS-12 sigue cerrada.
