# SPEC 052 · Delta — PRODUCTION-BASE-IMAGE-FLOATING-TAG

| Campo | Valor |
|---|---|
| Deuda | PRODUCTION-BASE-IMAGE-FLOATING-TAG (dueña 052, apoyo 001) |
| Decisiones | OD-CERT-06 (patch tag + digest inmutable) · OD-CERT-01..05 · OD-SEC-01/02 |
| HEAD de entrada | `6459fa0` |
| Ruta | B (sin evidencia de OBS-09) |
| Estado | **BLOCKED BY OWNER DECISION — MATERIAL_OQ = 1**: el gate material no admite ningún candidato sin decisión de la dueña |
| Evidencia | `evidence/production-base-image-pinned/` |

## 1. Specify
Objetivo: que el mismo commit dé la misma base OCI, la misma plataforma, el mismo Python, las mismas expectativas del
sistema, el mismo grafo Python y el mismo resultado certificado.
- Referencia preferida (OD-CERT-06): `python:<patch>-slim-<distro>@sha256:<digest completo>`.
- Fuera de alcance:
  - el lock y requirements;
  - libmagic;
  - la etapa runtime;
  - el producto;
  - las puertas Docker de ejecución.

## 2. Clarify — reproducción, consumidores y arquitectura
Detalle en `pre-fix-and-architecture.md` y `oci-discovery.json`.

- **Causa raíz probada:**
  - `FROM python:3.13-slim` no fija parche, distro ni digest;
  - hoy esa etiqueta resuelve a CPython **3.13.16** (índice `70729b46…`, creado el 2026-10-06);
  - la imagen **publicada** `kontrol-backend:latest` (2026-10-20) ejecuta **3.13.16**;
  - la certificación de despliegue (V4) usa **3.13.15**: ya hay deriva entre intérprete certificado y desplegado.
- **Consumidores:** IDL, IBE e IMB son compatibles con un `FROM tag@sha256`. Los literales `python:3.13-slim` de las
  pruebas son Dockerfiles sintéticos.
- **Arquitectura:**
  - CI en `ubuntu-latest` (x86_64), buildx sin `platforms`;
  - imagen publicada solo para `linux/amd64` (medido en el registro);
  - DEPLOYMENT_ARCHITECTURE_CONFIRMED = 1, TARGET_PLATFORM = linux/amd64; el host de producción queda NOT MEASURED;
  - con el digest de **índice**, buildx elige el hijo `linux/amd64`.

## 3. Descubrimiento OCI y coherencia
Contenido medido en el sistema de ficheros OCI (`base-security-and-coherence.md`):

| Candidato | Índice (multiarquitectura) | Manifiesto linux/amd64 | CPython | glibc | OpenSSL del sistema |
|---|---|---|---|---|---|
| A `python:3.13.15-slim-trixie` | `sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b` | `sha256:37134a49d21d2120…` | 3.13.15 | 2.41 | 3.5.7-1~deb13u2 |
| B `python:3.13.16-slim-trixie` | `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` | `sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024` | 3.13.16 | 2.41 | 3.5.7-1~deb13u3 |

- Los dos: PATCH_TAG_EXISTS = 1, 8 plataformas, distro trixie explícita y glibc ≥ 2.34 (el wheel de cryptography se
  instala como wheel).
- libmagic1t64 y libmagic-mgc 1:5.46-5 están disponibles en trixie.

## 4. Seguridad de la base
- **A congela el OpenSSL de Debian deb13u2** con **CVE-2026-35189**, aplicable: el backend es cliente TLS del servidor
  de licencias, un certificado manipulado puede causar denegación de servicio por memoria, y la severidad es baja. Está
  corregido en deb13u3. A sería además una **regresión de seguridad** frente a lo desplegado hoy (3.13.16 con deb13u3).
  BASE_IMAGE_SECURITY_BLOCKER_FOUND = 1.
- **B** no tiene bloqueantes conocidos.
  - Las correcciones de CPython 3.13.16 y los demás CVE de OpenSSL y pcre2 no aplican al uso real.
  - Hay dos actualizaciones de Debian posteriores a B: xz (no aplica) y ca-certificates (NOT MEASURED).
  - Las cubre la política de actualización.

## 5. Material gate
| Indicador | A (3.13.15) | B (3.13.16) |
|---|---|---|
| ROOT_CAUSE_PROVEN · DEPLOYMENT_ARCHITECTURE_CONFIRMED · PATCH_TAG_EXISTS | 1 · 1 · 1 | 1 · 1 · 1 |
| MULTIARCH_INDEX_DIGEST_CONFIRMED · PLATFORM_MANIFEST_DIGEST_CONFIRMED | 1 · 1 | 1 · 1 |
| REFERENCE_POLICY_CONFIRMED (patch tag + distro + digest de índice) | 1 | 1 |
| CERTIFICATION_CPYTHON_VERSION · BASE_CPYTHON_VERSION · **CPYTHON_MATCH** | 3.13.15 · 3.13.15 · **1** | 3.13.15 · 3.13.16 · **0** |
| GLIBC_SATISFIES_CRYPTOGRAPHY_WHEEL · LIBMAGIC_PACKAGE_AVAILABLE | 1 · 1 | 1 · 1 |
| **BASE_IMAGE_SECURITY_BLOCKER_FOUND** | **1** | 0 |
| PRODUCT · REQUIREMENTS · LOCK · SCHEMA · MIGRATION change required | 0 · 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 · 0 (el lock usa `--python-version 3.13`) |
| **MATERIAL_OQ** | 1 | 1 |

**No se implementa.** Ningún candidato cumple a la vez CPYTHON_MATCH = 1 y BASE_IMAGE_SECURITY_BLOCKER_FOUND = 0. Por §11
del encargo, recertificar contra otro intérprete no se ejecuta automáticamente. DEEPSEEK_CALLS = 0.

## 6. Decisión para la dueña (MATERIAL_DECISION_REQUIRED)

| Opción | Qué es | Seguridad | Coste |
|---|---|---|---|
| **B (recomendada)** | `FROM python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS base` y recertificación de despliegue con **CPython 3.13.16 (V5)** | sin bloqueante conocido; es el intérprete ya desplegado | ciclo de certificación completo; el lock no cambia |
| A | `FROM python:3.13.15-slim-trixie@sha256:7c61056e… AS base` | congela CVE-2026-35189, aplicable; baja el Python desplegado | ninguno |
| C | A con aceptación expresa del riesgo de CVE-2026-35189 | riesgo aceptado | ninguno |

**Detalles de B:**
- El intérprete de V5 debería salir **de la propia imagen**: el `/usr/local` de la capa CPython del manifiesto
  `linux/amd64`, verificado por digest y compilado para trixie con glibc 2.41, sobre el host Debian 13. Es
  MEASURED_OCI_FILESYSTEM, más fiel que una compilación aproximada. Alternativa: python-build-standalone 3.13.16
  (uv 0.12.17 no lo lista).
- V5 = ese intérprete + `pip install --no-deps -r requirements.lock && pip check` + pip-audit + suites completas.
- Elimina la deriva entre intérprete certificado y desplegado que ya existe.

**Recomendación técnica: B.** Es la única que cumple a la vez OD-CERT-06, OD-SEC-02 y «no degradar», y alinea la
certificación con lo que ya se ejecuta en producción.

## 7. Política de actualización (para el ciclo que implemente)
1. Elegir la etiqueta `python:<patch>-slim-trixie` candidata.
2. Resolver su digest de índice y los manifiestos por plataforma en el registro.
3. Comprobar `linux/amd64`.
4. Medir CPython, glibc y OpenSSL en el sistema de ficheros OCI.
5. Revisar la seguridad: changelog de CPython, trixie-security, OpenSSL y aplicabilidad.
6. Actualizar el `FROM` (patch tag + digest de índice completo).
7. Recertificar el despliegue con ese intérprete (pip check, pip-audit, SQLite, PostgreSQL, E2E y OpenAPI).
8. Solo entonces, commit.

No se permiten actualizaciones flotantes automáticas. BASE_IMAGE_UPDATE_MECHANISM_DOCUMENTED = 1.

## 8. Ciclo 2026-10-21 · OD-CERT-07 = B ratificada → revalidación y bloqueante nuevo
Detalle en `oci-revalidation.json` y `base-security-recheck-and-v5-feasibility.md`.

- **Revalidación OCI:** el índice, el manifiesto amd64 y la config del candidato B no cambiaron (`70729b46…`,
  `8fb4cfa1…`, CPython 3.13.16, 2026-10-06). CANDIDATE_TAG_REBUILT = 0.
- **Recheck de seguridad:** **DSA-6572-1** (`ca-certificates`, 2026-10-20 21:00 UTC). El almacén del candidato
  (`ca-certificates 20250419`) **contiene, medido en el sistema de ficheros OCI**, las dos raíces que Debian retira por
  compromiso de CA intermedias de eMudhra: «emSign ECC Root CA - G3» y «AAA Certificate Services» (Comodo).
  - **Aplicable:** el cliente TLS de licencias usa el almacén del sistema. Mitigado en parte por las firmas Ed25519 y el
    nonce.
  - No existe todavía ninguna imagen oficial de CPython 3.13.16 con `20250419+deb13u1`.
  - **NEW_BASE_SECURITY_BLOCKER = 1 → STOP (§5).** No se implementa. DEEPSEEK_CALLS = 0.
- **Viabilidad de V5:** demostrada la clase **IMAGE_ROOTFS**. El CPython 3.13.16 de la imagen ejecuta con el cargador,
  glibc 2.41 y OpenSSL 3.5.7 del rootfs: 25 bibliotecas, 0 del anfitrión. Salvedad: el bundle de CA debe redirigirse al
  rootfs (`SSL_CERT_FILE`).
- **Observación:** la capa apt de `base` instala `curl` y `libmagic1t64` sin versión: se resuelven el día del build.
  Queda registrada como PRODUCTION-IMAGE-APT-PACKAGES-UNPINNED, sin absorber.

### Decisión para la dueña — OD-CERT-08 (cómo fijar B sin heredar DSA-6572-1)

| Opción | Qué es | Seguridad | Inmutabilidad | Coste |
|---|---|---|---|---|
| **R1 (recomendada)** | Fijar B (`3.13.16-slim-trixie@sha256:70729b46…`) **y** autorizar un cambio mínimo en la capa apt de `base`: añadir `ca-certificates=20250419+deb13u1` (versión exacta) a la orden `apt-get install` existente | DSA-6572-1 corregida desde el primer build; sin aceptación de riesgo | base inmutable y almacén de CA fijado por versión | ruta extra en el Dockerfile; si Debian sustituye esa versión, el build falla cerrado y obliga a revisar |
| R2 | Fijar B tal cual con aceptación expresa y temporal de DSA-6572-1, y volver a fijar cuando se reconstruya la imagen oficial | riesgo aceptado temporalmente | sí | depende de la dueña |
| R3 | No fijar todavía. Esperar la reconstrucción oficial de `3.13.16-slim-trixie` con `20250419+deb13u1` y entonces fijar ese nuevo digest (solo `FROM`, tal como se ratificó) | mientras tanto la etiqueta flotante recoge el arreglo sola | ninguna hasta entonces | plazo de reconstrucción desconocido |

**Recomendación técnica: R1.** Es la única que da inmutabilidad y almacén de CA corregido **ya**, sin aceptar riesgo.

**Detalles de R1:**
- Cuando exista la imagen oficial reconstruida, la política de actualización la vuelve a fijar y puede retirar el pin
  explícito de `ca-certificates`.
- V5 = IMAGE_ROOTFS del candidato, con `ca-certificates 20250419+deb13u1` aplicado al rootfs: `apt-get download`
  (sin root) y `dpkg-deb -x`, más `SSL_CERT_FILE` al bundle del rootfs.
- Se instala con `pip install --no-deps -r requirements.lock && pip check` y se ejecutan las suites completas.
