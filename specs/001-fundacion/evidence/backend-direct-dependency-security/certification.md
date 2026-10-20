# Certificación — BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES (2026-10-20)

**Entornos:**
- V0 = `.venv` de control (CPython 3.11.16, PyJWT 2.10.1, cryptography 44.0.0); solo detecta regresiones ajenas.
- **V4** = CPython 3.13.15 + `pip install --no-cache-dir --no-deps -r requirements.lock && pip check` con el lock nuevo:
  PyJWT 2.15.0, cryptography 50.0.2 y OpenSSL 4.0.3. `pip check` en PASS y freeze = lock.

| Corrida | Resultado | Duración | Anomalía |
|---|---|---|---|
| V0 SQLite 1 | 1921/0/1056 (rc 0) | 685,9 s | NORMAL |
| V0 SQLite 2 | 1921/0/1056 (rc 0) | 706,7 s | NORMAL |
| V0 PostgreSQL | 2951/0/26 (rc 0) | 1525,5 s | NORMAL |
| V4 SQLite | 1921/0/1056 (rc 0) | 621,2 s | NORMAL |
| V4 PostgreSQL | 2951/0/26 (rc 0) | 1349,6 s | NORMAL |
| V0 E2E | **284/0/0**, LIMPIA, protegidas intactas | 4,5 min | — |
| V4 E2E | **284/0/0**, LIMPIA, protegidas intactas | 4,5 min | — |

**Notas de la tabla:**
- El +14 respecto de la línea base (1907 / 2937) son las SDV: 6 pruebas más los 8 casos de SDV-05.
- El `backend.log` de ambas E2E da QueuePool 0, 500 0, Traceback 0 y rechazos MIME 0. El único Traceback de
  `suite.log` es la prueba negativa conocida de alcance de usuario.
- Anfitrión durante las E2E: memoria disponible mínima de 527 MB, swap máxima de 9,6 GB y carga máxima de 16,5. Pasaron
  sin fallos.

**Pruebas dirigidas** (`directed-tests.txt`):
- En V0 y en V4: 998 passed, 0 fail y 45 skip. Abarcan los 63 módulos de auth, licencias y criptografía, más SDV, IDL,
  la imagen (MIME y etapas), reporting y documentos con ClamAV. Los 45 skips son previos: `solo_postgresql` sobre SQLite.
- SDV + IDL solas y en orden inverso: 21/21 sin skips.

**Seguridad:**
- `final-security-audit.txt`: pip-audit con PyPI y OSV sobre el lock y sobre el entorno V4 da 0 vulnerabilidades.
- Sondas en V4: JWT da 401 en los 10 casos; los flujos criptográficos y la carga de claves se comportan igual que con
  46.0.6.

**OpenAPI:** V0 y V4 dan 544/533/11; el diff semántico son las 4 diferencias del framework. OPENAPI_CONTRACT_DRIFT = 0.

**Imagen:** NOT EXECUTED (DOCKER_AVAILABLE = 0). La puerta IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED sigue
separada. El Dockerfile ya instala el lock (IDL-06).
