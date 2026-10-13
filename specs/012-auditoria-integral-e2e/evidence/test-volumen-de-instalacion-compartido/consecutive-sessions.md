# Medición 02 · Dos sesiones de pytest consecutivas (arnés actual, HEAD 1f28c83)

Sonda de medición (`-p tv_probe`, fuera del repositorio): imprime en `pytest_sessionstart` y
`pytest_sessionfinish` la huella sha256 truncada, el tamaño, el modo y el mtime del fichero compartido.
Nunca el contenido. Las claves son sintéticas (las genera `get_or_create_installation` en cada mundo).

```
### ANTES
[TV-PROBE previo]        pid=4113912 sha256_16=d1c0ac32416b7356 size=119 mode=0o600 mtime=06:19:39
### SESIÓN A: pytest tests/test_system_version.py -k "ver_03 and not 03b"
[TV-PROBE sessionstart]  pid=4113913 sha256_16=d1c0ac32416b7356 size=119 mode=0o600 mtime=06:19:39
[TV-PROBE sessionfinish] pid=4113913 sha256_16=b48f3a0d791af572 size=119 mode=0o600 mtime=06:42:18
### SESIÓN B: pytest tests/test_license_access.py
[TV-PROBE sessionstart]  pid=4114075 sha256_16=b48f3a0d791af572 size=119 mode=0o600 mtime=06:42:18
[TV-PROBE sessionfinish] pid=4114075 sha256_16=e3dff197181ad4ea size=119 mode=0o600 mtime=06:42:24
```

| Registro | Valor |
|---|---|
| `CROSS_SESSION_VISIBILITY` | **YES**: B arranca viendo exactamente la clave que dejó A (`b48f3a0d791af572`) |
| Sobrescritura entre sesiones | **YES**: B la sustituye por la suya (`e3dff197181ad4ea`); A ya no podría firmar nada verificable |
| Limpieza al terminar | ninguna: el fichero y el directorio sobreviven a las dos sesiones |
