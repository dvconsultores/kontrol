# V5 — procedencia del intérprete (IMAGE_ROOTFS, 2026-10-21)

**Rootfs:** `linux/amd64` de `python:3.13.16-slim-trixie@sha256:70729b46…`, a partir de las 4 capas del manifiesto
`8fb4cfa1…` verificadas por sha256, con whiteouts aplicados, en el scratchpad.

**Lo que el build añade en la capa apt, reproducido:**
- `libmagic1t64` y `libmagic-mgc` `1:5.46-5`, de trixie main: `InRelease` con firma correcta, `Packages.xz` verificado
  y `.deb` verificados por sha256.
- `ca-certificates` `20250419+deb13u1` (ver `ca-trust-store-dsa-6572.md`).
- `curl` no se reproduce: no forma parte del proceso Python (solo lo usa el HEALTHCHECK).
- Los paquetes se aplicaron con `dpkg-deb -x`, sin ejecutar el `postinst` de libmagic (solo dispara ldconfig). **No
  equivale a una instalación completa de dpkg.**

**Entorno:**
- `v5/bin/python` es un lanzador que ejecuta el CPython de la imagen así:
  `<rootfs>/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --inhibit-cache --library-path <rootfs>/usr/local/lib:<rootfs>/usr/lib/x86_64-linux-gnu:<rootfs>/lib/x86_64-linux-gnu --argv0 v5/bin/python <rootfs>/usr/local/bin/python3.13`.
- Exporta `SSL_CERT_FILE` (bundle del rootfs) y `MAGIC` (`magic.mgc` del rootfs).
- `pyvenv.cfg` con `home = <rootfs>/usr/local/bin`. Gracias a `--argv0`, `sys.executable` es el lanzador, y los
  subprocesos (pytest, uvicorn y QA) vuelven a pasar por el cargador del rootfs.
- Dependencias: `pip install --no-cache-dir --no-deps -r requirements.lock`.

**Resultados:**

| Indicador | Valor |
|---|---|
| `pip check` | «No broken requirements found» |
| V5_FREEZE_EQUALS_LOCK | 1 |
| cryptography | `cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64.whl` (wheel) |
| V5_CPYTHON_VERSION | 3.13.16 |
| `ssl.OPENSSL_VERSION` | OpenSSL 3.5.7 de la imagen |
| glibc | 2.41 de la imagen |
| `/proc/self/maps` con la app, psycopg2, cryptography, libmagic, ReportLab y JWT cargados | 83 bibliotecas: 50 del rootfs, 33 de los wheels del lock dentro de V5 y **0 del anfitrión** |
| V5_CPYTHON_SOURCE | **IMAGE_ROOTFS** |
| V5_RUNTIME_LIB_SOURCE | rootfs del candidato + wheels del lock |
| V5_CA_TRUST_SOURCE | bundle del rootfs reconstruido (148 CA, sin las raíces de DSA-6572-1) |

**Humo:**
- import, `create_app`, lifespan, 85 módulos, alembic, OpenAPI 544/533/11 y MIME PDF → `application/pdf`.
- ReportLab, JWT HS256 (10 casos idénticos a V4), Ed25519, licencias y ancla de confianza en PASS, con `-W error`.

**V5_SECURITY_AUDIT (pip-audit):** 1 hallazgo, PYSEC-2026-4320 en certifi, con aplicabilidad 0. Ver
`ca-trust-store-dsa-6572.md`.

**No es certificación exacta del runtime de imagen:**
- no hay contenedor;
- no hay `pip install` dentro de la imagen;
- `curl` no está;
- dpkg no se ejecutó.

EXACT_IMAGE_CA_RUNTIME_CERTIFIED = 0 y BASE_IMAGE_RUNTIME_CONTENTS_CERTIFIED = 0.
