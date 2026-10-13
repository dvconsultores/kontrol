# Medición 03 · Dos procesos de pytest sobre la ruta compartida (arnés actual, HEAD 1f28c83)

Sin `xdist`: dos procesos `pytest` independientes, subconjuntos disjuntos, SQLite, sin puertos.

## 03a · Concurrencia real (los dos a la vez)

- Proceso A: `pytest tests/test_license_sync_client.py` (sincroniza con la Autoridad Central en proceso:
  firma el sobre con la clave del volumen; la Autoridad conoce la clave pública registrada por A).
- Proceso B: `pytest tests/test_license_trust_anchor.py tests/test_license_period_rollback.py` (cada módulo
  vuelve a inicializar una instalación: reescribe la clave).

```
--- A ---
[TV-PROBE sessionstart]  pid=4116485 sha256_16=e3dff197181ad4ea mtime=06:42:24
[TV-PROBE sessionfinish] pid=4116485 sha256_16=c940a245f8ee80d1 mtime=06:43:02
E  AssertionError: {"code":"CENTRAL_SYNC_REJECTED", ... "details":{"central_code":"SYNC_AUTH_INVALID"}}
E   +  where 502 = <Response [502 Bad Gateway]>.status_code
FAILED test_csync_01 … FAILED test_csync_02 … 03 … 04 … 05 … 06 … 07 … 08 … 10 … 13   (10 de 13)
A rc=1
--- B ---
[TV-PROBE sessionstart]  pid=4116484 sha256_16=e3dff197181ad4ea mtime=06:42:24
[TV-PROBE sessionfinish] pid=4116484 sha256_16=74599cb11e8d293d mtime=06:43:06
B rc=0
```

| Registro | Valor |
|---|---|
| `PROCESS_A_PATH_ID` / `PROCESS_B_PATH_ID` | el mismo: `<tmp>/kontrol-test-license/installation_private_key.pem` |
| `SAME_DIRECTORY` | **YES** |
| `OVERWRITE` | **YES** (B reescribe la clave mientras A corre) |
| `CROSS_READ` | **YES** (A carga y firma con la clave de B) |
| `SIGNATURE_MISMATCH` | **YES**: la Autoridad rechaza con `SYNC_AUTH_INVALID`; el cliente responde 502 `CENTRAL_SYNC_REJECTED` |
| `OTHER_INTERFERENCE` | 10 de 13 pruebas de A fallan; B pasa (le tocó escribir la última) |

## 03b · Determinista (sin azar ni esperas)

Sonda `tv_interferencia`: en `pytest_runtest_call` de `test_csync_02`, con el mundo del módulo ya montado,
lanza y ESPERA un proceso B (`pytest tests/test_system_version.py -k "ver_03 and not 03b"`) que inicializa
otra instalación sobre la misma ruta; después sigue la prueba de A.

```
pytest tests/test_license_sync_client.py -k "csync_01 or csync_02" -p tv_probe -p tv_interferencia
[TV-PROBE sessionstart]     pid=4120353 sha256_16=f03c7c6b509b5d80 mtime=06:44:57
[TV-PROBE A antes de B]     pid=4120353 sha256_16=c0c1aee2a86631dd mtime=06:45:30
[TV-INTERFERENCIA] proceso B rc=0
[TV-PROBE A después de B]   pid=4120353 sha256_16=8377a54a6d3e0c22 mtime=06:45:35
E  AssertionError: {"code":"CENTRAL_SYNC_REJECTED", ... "details":{"central_code":"SYNC_AUTH_INVALID"}}
E  assert 502 == 200
FAILED tests/test_license_sync_client.py::test_csync_02_la_licencia_emitida_por_la_autoridad_llega_autenticada_y_pasa_por_la_importacion
```

Reproducible a voluntad: cada vez que un proceso ajeno inicializa una instalación entre el montaje del mundo
y la firma, la sincronización falla con `SYNC_AUTH_INVALID`.

Observación colateral (fuera de alcance, anotada en el delta): ejecutado `-k csync_02` a solas, la prueba
falla antes con 422 `CENTRAL_NOT_CONFIGURED`, porque depende de que `csync_01` haya configurado la Autoridad
en el mismo módulo. Es una dependencia de orden intramodular ajena al volumen; no se toca aquí.
