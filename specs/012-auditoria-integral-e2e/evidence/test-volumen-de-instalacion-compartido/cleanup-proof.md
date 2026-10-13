# Prueba de limpieza

| Comprobación | Evidencia | Resultado |
|---|---|---|
| `TEMP_DIRECTORY_EXISTS_DURING = true` | TV-02b / TV-05 (`os.path.isdir(volumen)` dentro del ámbito); sondas: `clave_dentro = true` | PASS |
| `TEMP_DIRECTORY_EXISTS_AFTER = false` (módulo) | TV-08 (salida normal y con excepción), TV-10 (la clave muere con el volumen) | PASS |
| `TEMP_DIRECTORY_EXISTS_AFTER = false` (sesión) | TV-03 y TV-09: tras el proceso, ni la clave, ni el volumen, ni la raíz existen | PASS |
| Limpieza cuando la prueba **falla** | TV-09: `sonda_falla.py` escribe su clave y revienta (`rc != 0`, «fallo deliberado de la sonda»); después, volumen y raíz ausentes | PASS |
| Limpieza cuando el **ámbito** revienta en proceso | TV-08b: excepción dentro del gestor → `rmtree` y restauración en el `finally` | PASS |
| Tras cada corrida de este ciclo (dirigidas SQLite, TV, dirigidas PostgreSQL, certificación paralela, mutaciones RESTORED) | `ls -d <tmp>/kontrol-test-license-*` → 0 | PASS |
| Interrupción abrupta (`SIGKILL`) | no se promete: `pytest_unconfigure` no corre; se documenta como límite | — |

Mecanismo: el hijo se elimina en el `finally` del gestor de contexto (el finalizador de la fixture corre pase o falle la
prueba); la raíz en `pytest_unconfigure`. Residuos observados durante el ciclo: 11 raíces **vacías** que dejaron los
mutantes M-05/M-08 (sin limpieza por diseño) y que se eliminaron a mano; el directorio fijo antiguo
`<tmp>/kontrol-test-license` desapareció durante la campaña porque el mutante M-01 lo usó como raíz y su propio
`pytest_unconfigure` lo eliminó al cerrar. Estado final del temporal: 0 directorios atribuibles al arnés.
