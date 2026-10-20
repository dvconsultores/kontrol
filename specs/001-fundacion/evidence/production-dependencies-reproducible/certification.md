# Certificación — REPRODUCIBLE DEPLOYMENT DEPENDENCIES (2026-10-20)

**Entornos:**
- V0 = `.venv` histórico de control (CPython 3.11.16, FastAPI 0.115.6).
- **V3** = CPython 3.13.15 + `pip install --no-cache-dir --no-deps -r requirements.lock && pip check`, exactamente el
  mecanismo de la imagen.

**Puertas previas en V3:**
- `pip check`: «No broken requirements found».
- **freeze = lock** (49/49; el único extra es el `pip` del venv, `v3-freeze.txt`).
- Humo en PASS: import, `create_app`, lifespan, 85 módulos (incluidas licencias), alembic, OpenAPI, MIME del PDF,
  exportación con ReportLab, PyYAML, JWT HS256 y Ed25519.

Backend con `qa/suite_tiempos.py --con-analizador` (ClamAV real) y E2E con `qa/e2e-run.py --con-analizador`:

| Corrida | Resultado | Duración | Anomalía |
|---|---|---|---|
| V0 SQLite 1 | 1907/0/1056 (rc 0) | 672,2 s | NORMAL |
| V0 SQLite 2 | 1907/0/1056 (rc 0) | 652,0 s | NORMAL |
| V0 PostgreSQL | 2937/0/26 (rc 0) | 1448,0 s | NORMAL |
| V3 SQLite | 1907/0/1056 (rc 0) | 591,0 s | NORMAL |
| V3 PostgreSQL | 2937/0/26 (rc 0) | 1323,7 s | NORMAL |
| V0 E2E | **284/0/0**, LIMPIA, `protegidas_sin_cambios` = true | 4,4 min | — |
| V3 E2E | **284/0/0**, LIMPIA, `protegidas_sin_cambios` = true | 4,4 min | — |

**Notas de la tabla:**
- El +7 respecto de la línea base (1900 / 2930) son las IDL nuevas.
- El `backend.log` de ambas E2E da QueuePool 0, 500 0, Traceback 0 y rechazos MIME 0.
- El único «Traceback» de `suite.log` es la salida esperada de la prueba negativa de `alcance-de-usuario.spec.ts`: el
  ayudante rehúsa y no escribe nada. Aparece igual en todas las corridas anteriores.
- Anfitrión durante las E2E: memoria disponible mínima de 745 MB, swap máxima de 6,4 GB y carga máxima de 12,0.

**Pruebas dirigidas** (`directed-tests.txt`):
- V0 y V3 dan 157 passed y 9 skipped. Los 9 skips son previos: marcas `solo_postgresql` de las pruebas documentales
  sobre SQLite.
- IDL solas: 7/7 sin skips.
- Estructurales en orden inverso: 22/22.

**OpenAPI:**
- V0 y V3 dan 544/533/11.
- V0 es idéntico al del ciclo anterior y V3 idéntico al de V1'.
- El diff semántico V0-V3 da 4 rutas, exactamente las 4 diferencias generadas por el framework ya clasificadas
  (`contentMediaType` y `format` del fichero de subida; `ctx` e `input` de `ValidationError`).
- **OPENAPI_CONTRACT_DRIFT = 0.**

**Imagen:**
- **NOT EXECUTED** (DOCKER_AVAILABLE = 0). IMAGE_FREEZE_EQUALS_LOCK = NOT MEASURED.
- La equivalencia está demostrada en V3 con el mismo mecanismo de instalación. La comprobación en la imagen queda como
  puerta externa: IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED.
