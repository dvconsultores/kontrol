# Certificación — LOCK-CERTIFI-PYSEC-2026-4320 (2026-10-21, tras la reconstrucción del entorno)

**Entornos:**
- V0 = `.venv` de control.
- **V5** = IMAGE_ROOTFS del digest fijado `70729b46…`: CPython 3.13.16, glibc 2.41, OpenSSL 3.5.7, libmagic y CA
  corregido, con el **lock nuevo** (certifi 2026.10.19).
- Telemetría de suspensión en `suspension-telemetry.txt`: **0 s en toda la cadena**, sin desvío de reloj.

| Corrida | Resultado | Duración | Anomalía |
|---|---|---|---|
| V0 SQLite 1 | 1928/0/1056 (rc 0) | 771,9 s | NORMAL |
| V0 SQLite 2 | 1928/0/1056 (rc 0) | 851,8 s | NORMAL |
| V0 PostgreSQL | 2958/0/26 (rc 0) | 1569,2 s | NORMAL |
| **V5 SQLite** | **1928/0/1056** (rc 0) | 626,9 s | NORMAL |
| **V5 PostgreSQL** | **2958/0/26** (rc 0) | 1404,5 s | NORMAL |
| V0 E2E | **284/0/0**, LIMPIA, protegidas intactas | — | — |
| **V5 E2E** | **284/0/0**, LIMPIA, protegidas intactas | — | — |

**Notas de la tabla:**
- El +1 respecto de la línea base (1927 / 2957) es SDV-08.
- El `backend.log` de ambas E2E da QueuePool 0, 500 0, Traceback 0 y MIME 0. El único Traceback de `suite.log` es la
  prueba negativa conocida de alcance de usuario.
- Anfitrión: memoria disponible mínima de 733 MB, swap máxima de 6,3 GB y carga máxima de 15,0.

## Dirigidas (`directed-tests.txt`)
- **Orden normal:** V0 104/104 y V5 104/104. Cubren SDV, IDL, IBB, IMB, IBE, keepalive, compose QA, reporting y
  documentos con ClamAV.
- **SDV + IDL solas:** 22/22 en V0 y V5. Las pruebas nuevas tienen FAIL 0 y SKIP 0.
- **Orden inverso:** 103 passed y **1 failed** en V0 y en V5, en `tests/test_documents.py::test_catalogos_nacen_vacios`.
  - **Atribución:** dependencia de orden **previa**, dentro del módulo. La prueba exige que el catálogo de tipos
    documentales empiece vacío y, en orden inverso, se ejecuta después de pruebas del mismo módulo que crean tipos.
  - Invirtiendo solo `test_documents.py` da el mismo resultado en `e0f0804` (`git archive`) y en el árbol actual
    (1 fallo, 24 pasan).
  - `test_documents.py` y `app/**` son idénticos a `e0f0804`. **No es regresión de este ciclo.**
  - Se registra como TEST-DOCUMENTS-CATALOG-ORDER-DEPENDENT y no se absorbe.

## Seguridad y humo de V5
- `pip check` PASS; freeze = lock (certifi 2026.10.19).
- **pip-audit 0 en PyPI y en OSV**, en V5 y sobre el lock.
- Humo en PASS:
  - app, `create_app`, lifespan, 85 módulos y alembic;
  - OpenAPI 544/533/11 y MIME PDF;
  - ReportLab, JWT HS256 (basura en la firma → DecodeError), Ed25519, licencias y ancla.
- Contexto TLS por defecto con 148 CA, sin las raíces de DSA-6572-1.
- certifi 2026.10.19 sin «emSign ECC Root CA - G3».
- 0 bibliotecas del anfitrión (`v5-smoke.txt`).
- Uso de certifi, httpx, requests o urllib3 en el producto: 0.

## OpenAPI
- V0↔V5: exactamente las 4 diferencias conocidas del framework.
- V5 con el lock nuevo da el mismo recuento (544/533/11). certifi no participa en el contrato.
- OPENAPI_CONTRACT_DRIFT = 0.

## Diferencia funcional entre V5 con el lock anterior y V5 con el nuevo
**0**: mismos recuentos en todas las suites (1927 → 1928 y 2957 → 2958, solo por SDV-08), E2E igual y OpenAPI igual.
