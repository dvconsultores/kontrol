# A2-POC · prefijo de usuario temporal, sin privilegios (`a2-feasibility-poc-output.txt`)

| Registro | Valor |
|---|---|
| A2-POC-01 `POC_PACKAGE_SOURCE` | `apt-get download` (sin root) desde `deb.debian.org trixie/main`: `clamav`, `libclamav12`, `clamav-freshclam`, `clamav-base` `1.4.3+dfsg-1` amd64 (15 MB); **SHA256 de los cuatro `.deb` = la publicada en los metadatos firmados de apt** |
| A2-POC-02 | `dpkg-deb -x` a `<tmp>/a2-poc/prefix` (66 MB): `usr/bin/{clamscan,freshclam,sigtool,clambc,clamsubmit}`, `usr/lib/x86_64-linux-gnu/libclamav.so.12`, `libfreshclam.so.3` |
| A2-POC-03 `POC_DEPENDENCY_SET` | `ldd`: solo `libclamav.so.12` resuelve al prefijo; el resto (`libjson-c5`, `libcurl4t64`, `libssl3t64`, `zlib1g`, `libbz2`, `libmspack0t64`, `libpcre2-8-0`, `libxml2`) ya está en el sistema. Sin `LD_LIBRARY_PATH` el binario no arranca («error while loading shared libraries») → el provisionador escribe envoltorios `bin/clamscan` que la fijan y ejecutan el binario real |
| A2-POC-04 `POC_ENGINE_VERSION` | `ClamAV 1.4.3` (misma versión semántica que el closeout 046) |
| A2-POC-05 `POC_ROOT_REQUIRED` | **NO** (ni `apt-get download`, ni `dpkg-deb -x`, ni `freshclam --datadir` necesitan root) |
| A2-POC-06 `POC_DB_VERSION` · `POC_DB_DATE` | `freshclam --config-file --datadir` a un directorio de usuario, 172 s, 108 MB: `main.cvd` v63 (16 Dec 2025, 3 287 027 firmas) · `daily.cvd` v28153 (14 Oct 2026 06:24 UTC, 355 765) · `bytecode.cvd` v339 (11 Sep 2025, 80); cada base superada «Database test passed» |
| A2-POC-07 `POC_CLEAN_RESULT` | PDF sintético: `OK`, rc 0, 8,0 s |
| A2-POC-08 `POC_EICAR_RESULT` | `Eicar-Test-Signature FOUND`, rc 1, 6,7 s |
| A2-POC-09 | directorio de firmas vacío: `cli_loaddbdir: No supported database files found`, **rc 2** (nunca CLEAN) |
| A2-POC-10 | nada fuera de `<tmp>/a2-poc`; eliminado al terminar el ciclo |
| `POC_NETWORK_REQUIRED` | sí (paquetes 15 MB; firmas ≈ 113 MB vía `freshclam`) |
| `POC_RESULT` | **PASS** · compuerta material A2: REAL_ENGINE, USER_PREFIX, ROOT_REQUIRED=NO, DEPENDENCY_CLOSURE, SIGNATURE_DB, CLEAN, EICAR, FAIL_CLOSED, UNOFFICIAL_BINARY_SOURCE=NO, SYSTEM_MUTATION=0 → autorización etapa 2 |

Coste por análisis: `clamscan` carga la base en cada invocación (≈ 7–8 s): una suite con ~35 subidas añade ≈ 4–5 min.
