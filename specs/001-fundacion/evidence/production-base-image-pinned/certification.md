# Certificación — base fijada y almacén de CA (2026-10-21)

**Entornos:**
- V0 = `.venv` de control (CPython 3.11.16).
- **V5** = IMAGE_ROOTFS: el CPython 3.13.16 de `python:3.13.16-slim-trixie@sha256:70729b46…`, con su cargador, glibc
  2.41 y OpenSSL 3.5.7; libmagic y `ca-certificates 20250419+deb13u1` aplicados al rootfs; dependencias con
  `pip install --no-deps -r requirements.lock`.

| Corrida | Resultado | Duración | Anomalía |
|---|---|---|---|
| V0 SQLite 1 | 1927/0/1056 (rc 0) | 687,1 s | NORMAL |
| V0 SQLite 2 | 1927/0/1056 (rc 0) | 683,7 s | NORMAL |
| V0 PostgreSQL, corrida 1 | 2956/**1**/26 (rc 1), **desvío de reloj 9398,9 s** | 1895,9 s monotónicos | ver atribución |
| **V0 PostgreSQL, corrida 2** (sin interrupción) | **2957/0/26** (rc 0), desvío 0,0 s | 1517,6 s | NORMAL |
| V5 SQLite | 1927/0/1056 (rc 0) | 652,9 s | NORMAL |
| V5 PostgreSQL | 2957/0/26 (rc 0) | 1461,5 s | NORMAL |
| V0 E2E | **284/0/0**, LIMPIA, protegidas intactas | — | — |
| V5 E2E | **284/0/0**, LIMPIA, protegidas intactas (backend sobre el CPython de la imagen) | — | — |

**Notas de la tabla:**
- El +6 respecto de la línea base (1921 / 2951) son las IBB nuevas.
- El `backend.log` de ambas E2E da QueuePool 0, 500 0, Traceback 0 y MIME 0. El único Traceback de `suite.log` es la
  prueba negativa conocida de alcance de usuario.
- Anfitrión durante las E2E: memoria disponible mínima de 607 MB, swap máxima de 9,6 GB y carga máxima de 13,9.
- En la E2E de V5, la migración de la autoridad central usa el `.venv` fijo: deuda conocida
  E2E-HARNESS-INTERPRETER-FIXED, no absorbida.

**Atribución de la corrida 1 de V0 PostgreSQL:**
- El equipo se **suspendió** entre las 02:16 y las 04:53: el log de PostgreSQL no registra actividad en ese intervalo y
  `suite_tiempos` mide un desvío entre reloj de pared y monotónico de 9398,9 s.
- El único fallo es `test_e2ecorrida_18`, en la aserción `observado["reloj"]["salto"] is False`. Esa prueba exige que
  la mini-corrida del arnés no vea salto de reloj, y el arnés **detectó correctamente** el salto de la suspensión.
- Es causa ambiental y no hay regresión. La corrida 2, misma orden, sin cambios y sin interrupción, da 2957/0/26.

**Dirigidas** (`directed-tests.txt`):
- V0 y V5: 62/62, en orden normal e inverso. Cubren IBB, IDL, IMB, IBE, SDV, keepalive y compose QA.
- IBB solas: 6/6 sin skips.

**OpenAPI:**
- V5 da 544/533/11.
- **V4↔V5: 0 diferencias.**
- V0↔V5: las 4 del framework ya clasificadas.
- OPENAPI_CONTRACT_DRIFT = 0.

**JWT y criptografía en V5:**
- 10 casos JWT idénticos a V4.
- Ed25519, licencias y ancla de confianza en PASS con `-W error`.
- Contexto TLS por defecto: 148 CA, ninguna de las raíces retiradas por DSA-6572-1.

**Seguridad V5 (pip-audit):** 1 hallazgo, PYSEC-2026-4320 en certifi 2026.10.18. Aplicabilidad 0 por contenido y por
uso; ver `ca-trust-store-dsa-6572.md`.

**V4↔V5:** 0 diferencias funcionales. Mismos recuentos en todas las suites, E2E igual, OpenAPI idéntico y JWT idéntico.
Solo cambian los metadatos del intérprete.

**Imagen:** NOT EXECUTED (sin Docker). EXACT_IMAGE_CA_RUNTIME_CERTIFIED = 0 y
BASE_IMAGE_RUNTIME_CONTENTS_CERTIFIED = 0.
