# Certificación final — CERTIFICATION-ALEMBIC-INTERPRETER-PARITY (2026-10-22)

**Árbol:** HEAD `9a41503` (= `d20da5b` + documentación de la línea Gobierno) + T1..T5 del ciclo.

**Entorno tras el reinicio del equipo:**
- PostgreSQL de QA reaprovisionado: `pg-provision.sh start` y `mkdb ktest`;
- V5 reconstruido por digest (`v5-rebuild.json`);
- ClamAV 1.4.3 (main 63 · daily 28153 · bytecode 339).

## V5 (IMAGE_ROOTFS)

| Indicador | Valor |
|---|---|
| Índice / plataforma / config | `sha256:70729b46…` / `sha256:8fb4cfa1…` / `sha256:ce3ff952…`, verificados por sha256 junto con las 4 capas |
| V5_SYS_EXECUTABLE | `<scratch>/paridad/v5/bin/python` (lanzador con `--argv0`); `exe_real` = `ld-linux-x86-64.so.2` del rootfs |
| V5_PYTHON_VERSION | CPython 3.13.16; OpenSSL 3.5.7; glibc 2.41 |
| V5_RUNTIME_LIB_SOURCE | rootfs + wheels del lock. Con app, psycopg2, cryptography, libmagic, ReportLab, JWT, alembic y SQLAlchemy cargados: 76 bibliotecas, 51 del rootfs, 25 del venv y **0 del anfitrión** |
| CA | `ca-certificates 20250419+deb13u1` (sha256 `c10585ac…`); bundle de **148**, sin `Comodo_AAA_Services_root` ni `emSign_ECC_Root_CA_-_G3` |
| libmagic | `1:5.46-5`; PDF sintético → `application/pdf` |
| `pip check` · freeze = lock | PASS · 1 |
| pip-audit PyPI · OSV (lock, `--no-deps`) | 0 · 0 |

**Nota de reconstrucción:** `dpkg-deb -x` superpone el paquete pero no borra los dos certificados retirados que dejó el rootfs base. Se quitaron los ficheros que el `.deb` corregido ya no trae y se regeneró el bundle desde `ca-certificates.conf`, como haría dpkg.

## Backend (con analizador real, `qa/suite_tiempos.py`)

| Corrida | Intérprete | Resultado | Monotónico | Anomalía |
|---|---|---|---|---|
| `r20261022t023433` SQLite | V0 3.11.16 | **1956/0/1062** | 661,0 s | NORMAL |
| `r20261022t024548` SQLite | V5 3.13.16 | **1956/0/1062** | 626,4 s | NORMAL |
| `r20261022t031233` PostgreSQL | V5 3.13.16 | **2992/0/26** | 1436,5 s | NORMAL |

- Frente a la evidencia anterior (1955/0/1056 y 2985/0/26): +1 en SQLite (AIC-08) y +6 omitidas (e2ecorrida 19..24, que solo corren sobre PostgreSQL); +7 en PostgreSQL.
- **Corrida invalidada `r20261022t025629`** (PostgreSQL V5, 1214/38/26 con 1740 errores): `FATAL: database "ktest" does not exist` desde la primera conexión.
  - Tras el reinicio, `pg-provision.sh start` recrea el clúster pero no las bases, y faltó `mkdb ktest`. Es un defecto de la preparación del entorno (ENVIRONMENT_SETUP), no del código.
  - Se repitió una sola vez, con la base creada por el procedimiento oficial.

## E2E final (una corrida por intérprete, `qa/e2e-run.py --con-analizador`)

| | V0 `r20261022t033651` | V5 `r20261022t034152` |
|---|---|---|
| Resultado | **284/0/0** · LIMPIA · salida 0 | **284/0/0** · LIMPIA · salida 0 |
| Suite | 275,0 s | 278,0 s |
| `licencia-revision` | 17,5 s | 17,5 s |
| E2E_HARNESS_SYS_EXECUTABLE | `<repo>/resources/backend/.venv/bin/python` | `<tmp>/…/paridad/v5/bin/python` |
| E2E_HARNESS_PYTHON_VERSION | 3.11.16 | 3.13.16 |
| E2E_AUTHORITY_MIGRATION_COMMAND | `<ejecutable> -m alembic -c central_authority/alembic.ini upgrade head` | igual |
| E2E_AUTHORITY_MIGRATION_SYS_EXECUTABLE | igual que el arnés | igual que el arnés (`exe_real` = `ld-linux` del rootfs) |
| E2E_AUTHORITY_MIGRATION_PYTHON_VERSION | 3.11.16 | 3.13.16 |
| ALEMBIC · SQLALCHEMY (hijo) | 1.14.0 · 2.0.36 | 1.14.0 · 2.0.36, desde el `site-packages` de V5 |
| E2E_INTERPRETER_PARITY | **1** | **1** |
| Bases protegidas sin cambios · reloj · red | sí · desvío 0,0 · sin cambio | sí · desvío 0,0 · sin cambio |

- Procedencia medida por la sonda de T4, con el mismo ejecutable, `cwd` y entorno que la migración.
- En los dos modos, el backend, la migración del tenant y la siembra usan `sys.executable` del arnés.
- Los ayudantes que las specs lanzan con `execFileSync` siguen en V0 (`e2e-specs-fixed-python-inventory.md`, deuda nueva no absorbida).

Precondiciones medidas antes de cada E2E final:
- 0 bases de corrida;
- PostgreSQL HEALTHY (2,3–2,4 ms);
- puertos 8000/5173/8010 libres;
- NTP sincronizado;
- `boottime − monotonic` = 98,4 s, constante (sin suspensión);
- preflight del analizador PASS.

## OpenAPI

V0 y V5: 544 operaciones, 533 con `BearerAccessToken` y 11 públicas, con la misma huella de `paths` (`444c820edc7e`). OPENAPI_CONTRACT_DRIFT = 0.

## Lint y tipos

- ruff: backend completo y `qa/e2e_corrida.py` limpios.
- mypy: limpio en los cuatro ficheros tocados.
- `mypy app`: 154 errores, idénticos en `d20da5b`; `app` no se tocó (PREEXISTING).
