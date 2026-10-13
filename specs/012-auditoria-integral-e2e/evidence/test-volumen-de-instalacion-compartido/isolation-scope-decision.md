# Decisión del alcance del aislamiento

| Candidato | Compatibilidad con las fixtures reales | Veredicto |
|---|---|---|
| FUNCTION | 34 mundos son `autouse` de **módulo** y escriben la clave una vez por módulo; un volumen vacío por prueba dejaría cada prueba sin la clave que su mundo escribió antes (`INSTALLATION_KEY_UNAVAILABLE` en los `csync_*`), salvo reescribiendo 34 mundos | **incompatible sin refactor masivo (prohibido)** |
| CLASS | no existe ningún `scope="class"` en `tests/` | sin objeto |
| MODULE | se monta antes que el mundo del módulo (medido con `--setup-show`) y se desmonta después; todo lector de la clave está en el ámbito que la escribió (matriz: `ASSUMES_PREEXISTING_KEY 0`); los mundos por prueba (`test_licensing_central`, `test_services`) reescriben y leen dentro del mismo módulo, en secuencia | **compatible** |
| SESSION (único por proceso) | obligatorio entre procesos: dos `pytest` no pueden recibir el mismo volumen | **obligatorio** |

`SELECTED_SCOPE = HYBRID`:

1. **Raíz única por proceso** de pytest, creada en `pytest_configure` con `tempfile.mkdtemp(prefix="kontrol-test-license-")`
   (API de directorio temporal con nombre aleatorio y creación atómica, no el PID; nunca `/tmp/...` fijo ni el cwd),
   publicada en `config.stash`, fijada en `KONTROL_INSTALLATION_VOLUME_PATH` con `get_settings.cache_clear()`, y
   **eliminada en `pytest_unconfigure`** restaurando el valor previo de la variable. Nace en un hook porque el
   conftest se importa dos veces (`conftest` y `tests.conftest`).
2. **Un volumen hijo por módulo** (`mkdtemp(prefix="<módulo>-", dir=raíz)`) mediante una fixture `autouse` de
   módulo: empieza vacío, fija la variable, limpia la caché, y al desmontar elimina el directorio, restaura la
   variable (a la raíz) y limpia la caché otra vez. El cuerpo vive en un gestor de contexto reutilizable para
   que las pruebas del arnés lo ejerciten en proceso.

Propiedades exigidas: (1) raíz única por proceso ✔ · (2) directorio propio por ámbito ✔ · (3) empieza vacío ✔ ·
(4) se elimina al terminar (módulo y sesión; también cuando una prueba falla: el finalizador de fixture corre
igual) ✔ · (5) ningún proceso comparte clave ✔ · (6) `Settings` recibe la ruta correcta ✔ · (7) la caché no
conserva la ruta anterior ✔.

Pruebas dependientes de estado ajeno: **0** (ninguna corrección de prueba necesaria). `pytest_sessionfinish`
ya existe para PGLIFE y no se toca; la limpieza del volumen va en `pytest_unconfigure` (después).
`tmp_path_factory` se descarta como raíz porque pytest retiene los tres últimos `basetemp` (dejaría claves en
disco entre corridas).
