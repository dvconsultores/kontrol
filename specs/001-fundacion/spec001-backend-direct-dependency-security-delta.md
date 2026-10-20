# SPEC 001 · Delta — BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES

| Campo | Valor |
|---|---|
| Deuda | BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES (seguridad, dependencias directas) |
| Spec dueña | 001 (ADR-014, `cve-review.md`, `dependency-matrix.md`); apoyo 052 (lock, OD-CERT-05) |
| Decisiones aplicadas | **OD-SEC-01** (adelantar) · **OD-SEC-02** (un aviso conocido y corregible en una dependencia directa de autenticación o criptografía bloquea la release) · OD-CERT-01..05 preservadas |
| HEAD de entrada | `eba1090` |
| Ruta | S (sin evidencia de OBS-09) |
| Evidencia | `evidence/backend-direct-dependency-security/` |

## 1. Specify
- **Objetivo:**
  - los pines directos de PyJWT y cryptography no tienen avisos conocidos y corregibles;
  - el manifiesto y el lock coinciden;
  - el piso de seguridad queda documentado y protegido por prueba;
  - se preservan los contratos JWT (lista de algoritmos explícita, sin `none`, firma, caducidad, 401 saneado) y de
    licencias (Ed25519/PEM, ancla de confianza).
- **Fuera de alcance:**
  - cambiar el producto;
  - la separación runtime/dev;
  - la base flotante;
  - los hashes del lock;
  - el defecto previo de `UnsupportedAlgorithm` (§2, deuda nueva).

## 2. Clarify — avisos, uso real y aplicabilidad
**Refresco de avisos** (`advisory-inventory.tsv`), con pip-audit 2.10.1 (PyPI y OSV), OSV, GHSA, changelogs upstream y
avisos de OpenSSL:

| Paquete | Avisos únicos | Aplicables | Sin parche |
|---|---|---|---|
| PyJWT 2.13.0 | 14 | 2 | 0 |
| cryptography 46.0.6 | 5 | 1 | 0 |

- Aplicables en PyJWT: PYSEC-2026-4142 y PYSEC-2026-4147. Aplicable en cryptography: GHSA-537c-gmf6-5ccf.
- Alias deduplicados: los 15 registros iniciales eran 14 avisos únicos de PyJWT.
- Todos los avisos son corregibles.

**PYSEC-2026-4146** (CVE-2026-103001 / GHSA-gvp8-978c-rx2q):

| Indicador | Valor | Evidencia |
|---|---|---|
| METADATA_CONFLICT | 1 | OSV `introduced 2.11.0, last_affected 2.13.0`; GHSA `>= 2.11.0, <= 2.13.0` con `first_patched_version = None`; pip-audit lo listaba «sin versión corregida» |
| FIXED_IN_CANDIDATE | 1 | sonda conductual: 2.13.0 muta `options`, 2.15.0 no |
| APPLICABLE_TO_KONTROL | 0 | 0 usos de `options` y `verify_signature` |

**Uso real de PyJWT:**
- `security.decode_token` llama a `jwt.decode(token, secret_key, algorithms=[settings.jwt_algorithm])` con HS256 por
  defecto.
- `Settings` exige un `secret_key` de ≥ 32 caracteres.
- `PyJWTError` se convierte en 401 (`AUTH_INVALID_TOKEN` / `SESSION_INVALID`).
- 0 usos de JWK, JWKS, `PyJWKClient`, `options`, `verify_signature`, `decode_complete` y `get_unverified_*`.

**Uso real de cryptography:**
- Ed25519 (`generate`, `sign`, `verify`), PEM (`load_pem_public_key`, `load_pem_private_key`, `public_bytes`,
  `private_bytes`/`NoEncryption`) e `InvalidSignature`.
- 0 usos de X.509, PKCS7, cifrados y hashes.
- Modelo OpenSSL: wheel `manylinux_2_34` con OpenSSL estático (trixie tiene glibc 2.41).

**Sonda de la cadena real** (`jwt-behavior-probe.txt`): con 2.13.0, que es lo desplegado hoy, y con 2.10.1 (V0):
- una firma con `!!!!` añadido **se acepta**;
- una cabecera profundamente anidada deja escapar `RecursionError`, que se convierte en **HTTP 500 sin autenticar**.

Con 2.15.0 los dos casos dan 401. Firma ajena, HS512, `alg=none`/`NONE`, token caducado, cabecera no objeto y token
malformado dan 401 en las tres versiones.

**Hallazgo previo e independiente de la actualización** (`key-loading-probe.txt`):
- Una PEM SM2 hace que `UnsupportedAlgorithm` escape de `trust_anchor.load_trust_anchor` y de
  `license_contract.load_public_key`, en lugar de `TrustAnchorError` o `ValueError`.
- Ocurre igual en 46.0.6 y en 50.0.2.
- Solo hay entrada de operador: configuración y CLI de la autoridad central. Falla cerrado.
- Se registra como **CRYPTO-KEY-LOADING-UNSUPPORTED-ALGORITHM-UNWRAPPED** y no se absorbe, porque exige cambiar el
  producto.
- PEM EC de curva explícita, Ed448, ML-DSA y RSA siguen dando `TrustAnchorError("invalid")` / `ValueError` igual en las
  dos versiones.

## 3. Selección de versiones
| Paquete | Actual | Candidata | Piso | Motivo |
|---|---|---|---|---|
| PyJWT | 2.13.0 | **2.15.0** | 2.15.0 | mínima con 0 avisos (2.14.0 deja 4141 y 4183). Incluye el envoltorio de la recursión. 2.15.1 solo relaja el parseo (acepta relleno `=` final, pensado para AWS ALB), que KONTROL no necesita |
| cryptography | 46.0.6 | **50.0.2** | 50.0.2 | 50.0.0 es la mínima sin avisos del paquete. 50.0.1 y 50.0.2 solo actualizan el OpenSSL embebido: 4.0.2 corrige CVE-2026-54874 y 4.0.3 corrige CVE-2026-84783 y CVE-2026-54875. 50.0.2 es la mínima sin vulnerabilidades conocidas en su OpenSSL. Rupturas de 47 a 50 revisadas: ninguna afecta a Ed25519 ni a PEM |

- Las dos versiones se publicaron antes del corte del lock (2026-09-28 y 2026-09-30):
  SECURITY_REQUIRES_LOCK_CUTOFF_ADVANCE = 0.
- cryptography 46 → 50 es un salto mayor. Este es el ciclo de seguridad explícito que pide ADR-014, con compatibilidad
  exhaustiva (§6).

## 4. Plan
| Tarea | Contenido | EXECUTOR | MODEL | FILES |
|---|---|---|---|---|
| T1 | Pines directos `PyJWT==2.15.0` y `cryptography==50.0.2` | DEEPSEEK | deepseek-v4-flash | `resources/backend/requirements.txt` |
| T1b | Regenerar el lock con el comando canónico (procedimiento mecánico) | CLAUDE (procedimiento) | n-a | `resources/backend/requirements.lock` |
| T2 | Prueba `test_seguridad_dependencias.py` (SDV). Piso de `SUELOS_CVE` en IDL-05 | DEEPSEEK | deepseek-v4-pro | `resources/backend/tests/test_seguridad_dependencias.py`, `resources/backend/tests/test_dependencias_lock.py` |
| T3 | Registro de seguridad (`cve-review.md`) y enlace cruzado en `dependency-matrix.md` | CLAUDE (decisión de seguridad documentada) | n-a | `docs/evidence/cve-review.md`, `specs/001-fundacion/dependency-matrix.md` |

`Dockerfile.backend`, el producto, compose, los workflows y QA no cambian.

## 5. Constitution gate y trazabilidad
- **P10/P16:** no se libera con vulnerabilidades conocidas corregibles.
- **ADR-014:** pines exactos y lock reproducible, con el mismo corte.
- **Sin cambio:** esquema, migraciones y producto.

| Requisito | Tarea | Prueba |
|---|---|---|
| Pines ≥ piso, coherentes entre manifiesto y lock | T1/T1b | SDV-01 e IDL-01/05 |
| Piso documentado y coherente | T3 | SDV-02 |
| Avisos corregibles cubiertos y ninguno sin parche aplicable | T3 | SDV-03 |
| Sin exclusiones de pip-audit | — | SDV-04 |
| Contrato JWT por HTTP: firma, algoritmo, `none`, caducidad, malformado → 401, nunca 500 | — | SDV-05 |
| Lista de algoritmos explícita, de un elemento, sin `options`, `verify_signature` ni JWK | — | SDV-06 |
| Clave vacía o corta → fallo al arrancar | — | SDV-07 |

Trazabilidad: 7 de 7 requisitos con tarea y prueba.

## 6. Material gate (V4-CANDIDATE en el scratchpad, antes de tocar el repositorio)

**Avisos y aplicabilidad**

| Indicador | Valor |
|---|---|
| CURRENT_SECURITY_FINDINGS | 19 (14 + 5) |
| PYJWT_FIXABLE · CRYPTOGRAPHY_FIXABLE | 14 · 5 |
| PYJWT_CANDIDATE · CRYPTOGRAPHY_CANDIDATE | 2.15.0 · 50.0.2 |
| CANDIDATE_AUDIT_CLEAN (lock completo, PyPI y OSV) | 1 · 1 |
| UNPATCHED_FINDINGS · UNPATCHED_APPLICABLE_FINDINGS | 0 · 0 |
| PYSEC_2026_4146_METADATA_CONFLICT · APPLICABLE | 1 · 0 |

**Compatibilidad**

| Indicador | Valor |
|---|---|
| PYJWT_USAGE_COMPATIBLE · CRYPTOGRAPHY_USAGE_COMPATIBLE | 1 · 1 |
| JWT_ALGORITHM_CONTRACT_PRESERVABLE · LICENSE_CRYPTO_CONTRACT_PRESERVABLE | 1 · 1 |
| Lock candidato | determinista; solo cambian los dos pines directos (UNRELATED_VERSION_CHANGES = 0) |
| V4 | `pip check` PASS; freeze = lock; OpenSSL 4.0.3 |
| Módulos de auth, licencias y criptografía en V4 | 63 módulos: 928 passed, 0 failed |
| Flujos criptográficos reales con avisos como errores | PASS |

**Alcance y decisión**

| Indicador | Valor |
|---|---|
| PRODUCT · SCHEMA · MIGRATION change required | 0 · 0 · 0 |
| OWNER_RISK_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 7. Implementación
- **T1 — `requirements.txt`:** `PyJWT==2.15.0` y `cryptography==50.0.2`.
- **T1b — `requirements.lock`:** regenerado con el comando canónico de su cabecera, con el **mismo corte**
  (`--exclude-newer 2026-10-20T00:00:00Z`).
  - Idéntico al candidato de V4 e idempotente.
  - Cambian solo `pyjwt` y `cryptography`: UNRELATED_VERSION_CHANGES = 0 y SECURITY_REQUIRES_LOCK_CUTOFF_ADVANCE = 0.
- **T2 — `tests/test_seguridad_dependencias.py` (SDV-01..07):**
  - SDV-01: piso y coherencia entre manifiesto y lock.
  - SDV-02: piso documentado.
  - SDV-03: cada aviso revisado está corregido por el pin, o no tiene parche ni aplica (OWNER_RISK_DECISION_REQUIRED en
    caso contrario).
  - SDV-04: sin exclusiones de pip-audit.
  - SDV-05: el contrato JWT por HTTP da 401 y nunca 500.
  - SDV-06: lista de algoritmos de un elemento, sin `options`, `verify_signature` ni JWK (por AST).
  - SDV-07: una clave vacía o corta impide arrancar.
  - `SUELOS_CVE` (IDL-05) sube a PyJWT 2.15.0 y cryptography 50.0.2.
- **T3:**
  - `docs/evidence/cve-review.md` gana las secciones «Piso de seguridad vigente» y «Avisos backend revisados», con los
    19 avisos, su aplicabilidad y el motivo de cada uno;
  - `dependency-matrix.md` gana el enlace cruzado.
- Producto, Dockerfile, compose, workflows, QA, esquema y migraciones: sin cambio.

## 8. Pruebas y mutaciones
**Rojo contra `eba1090`** (`red-against-head.txt`):
- **(a) Tal cual:** fallan SDV-01 (PyJWT 2.13.0 < 2.15.0; cryptography 46.0.6 < 50.0.2), SDV-02 y 03 (sin registro de
  seguridad) e IDL-05 (cryptography 46.0.6 < 50.0.2).
- **(b) Con los pines de HEAD y el registro nuevo:** fallan los mismos cuatro **solo por las versiones**
  (`pyjwt 2.13.0 no alcanza la corregida 2.14.0`, `versión fijada 2.15.0 ≠ 2.13.0`).
- SDV-04..07 pasan en HEAD: es el contrato que se preserva.

**Mutaciones: 17/17 KILLED**, todas restauradas idénticas (`mutations.json`):
- M01-M04: pines vulnerables o por debajo del piso.
- M05 y M06: desajuste entre manifiesto y lock.
- M07, M07b y M08: filas quitadas de `cve-review`.
- M09: `alg none` aceptado. M10: `algorithms=None`.
- M11: un token malformado da 500.
- M12: hallazgo corregible tratado como PASS.
- M13: `--ignore-vuln` en un workflow.
- M14: aviso aplicable sin parche tratado como cerrado.
- M15: validador de clave a 16. M16: HS512 por defecto.

**Auditoría final:** pip-audit con PyPI y OSV sobre el lock del repositorio y sobre el entorno V4 instalado da
**0 vulnerabilidades**.

**OpenAPI:** V0 y V4 dan 544/533/11; el diff semántico son las 4 diferencias del framework. Deriva de contrato 0.

## 9. Certificación
| Corrida | V0 (control) | V4 (despliegue seguro) |
|---|---|---|
| `pip check` · freeze = lock · auditoría | — | PASS · 1 · 0 vulnerabilidades (PyPI y OSV) |
| Dirigidas | 998 passed, 0 fail | 998 passed, 0 fail |
| SQLite | 1921/0/1056 ×2 | 1921/0/1056 |
| PostgreSQL | 2951/0/26 | 2951/0/26 |
| E2E con analizador | 284/0/0, limpia | 284/0/0, limpia |
| OpenAPI | 544/533/11 (sin cambio) | 544/533/11; deriva de contrato 0 |

## 10. Convergencia
| Indicador | Valor |
|---|---|
| PYJWT findings pre → post (corregibles · sin parche) | 14 → 0 (0 · 0) |
| CRYPTOGRAPHY findings pre → post (corregibles · sin parche) | 5 → 0 (0 · 0), más 3 CVE del OpenSSL embebido corregidos |
| UNPATCHED_APPLICABLE_FINDINGS · OWNER_RISK_DECISION_REQUIRED | 0 · 0 |
| JWT_ALGORITHM_ALLOWLIST_PASS · JWT_MALFORMED_TOKEN_PASS | 1 · 1 |
| CRYPTOGRAPHY_ACTUAL_API_COMPATIBILITY | PASS |
| LOCK_GRAPH_DETERMINISTIC · UNRELATED_VERSION_CHANGES | 1 · 0 |
| PRODUCT · SCHEMA · MIGRATION changed | 0 · 0 · 0 |
| OTHER_DEBT_ABSORBED | 0 |

**BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES = CLOSED / CONVERGED.**
- La comprobación en la imagen real sigue en la puerta separada IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED.
- Deuda nueva, sin absorber: **CRYPTO-KEY-LOADING-UNSUPPORTED-ALGORITHM-UNWRAPPED** (previa, de entrada de operador,
  falla cerrado).
