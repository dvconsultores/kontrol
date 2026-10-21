# SPEC 052 · Delta — LOCK-CERTIFI-PYSEC-2026-4320 (+ cierre formal de PRODUCTION-BASE-IMAGE-FLOATING-TAG)

| Campo | Valor |
|---|---|
| Deuda | LOCK-CERTIFI-PYSEC-2026-4320 (dueña 052, apoyo 001) |
| Decisiones | **OD-LOCK-01** (corte mínimo) · **OD-LOCK-02** (UNRELATED_VERSION_CHANGES = 0 como puerta dura) · **OD-LOCK-03** (suelo de certifi protegido sin volverla directa) · OD-CERT-01..08 · OD-SEC-01/02 |
| HEAD de entrada | `e0f0804` |
| Ruta | L (sin evidencia de OBS-09) |
| Evidencia | `evidence/lock-certifi-cutoff/` |

## 1. Specify
- **Objetivo:** que pip-audit (PyPI y OSV) dé 0 en el grafo de despliegue, corrigiendo **una** transitiva (certifi)
  mediante un movimiento mínimo de `--exclude-newer`. Sin exclusiones, sin pin directo nuevo y sin otras versiones.
- **Además:** cerrar formalmente PRODUCTION-BASE-IMAGE-FLOATING-TAG, cuyo gate solo estaba bloqueado por «V5 pip-audit
  0».
- **Fuera de alcance:** la base, el pin de CA, libmagic, los pisos directos, el producto, el Dockerfile,
  `requirements.txt` y el resto de deudas.

## 2. Clarify
Detalle en `evidence/lock-certifi-cutoff/cutoff-selection.md`.
- Aviso revalidado: GHSA critical, rango `< 2026.10.19`. Suelo: 2026.10.19.
- Artefacto relevante: el wheel de 2026-10-20T02:24:15.072385Z.
- Frontera de uv: precisión de milisegundo y comparación estricta, así que el corte mínimo es
  **2026-10-20T02:24:15.073Z** (+8655,073 s).
- En la ventana solo se publicó certifi.
- Dos resoluciones idénticas.
- Diff: **solo certifi**.
- El lock nuevo audita a 0.

## 3. Plan
| Tarea | Contenido | EXECUTOR | MODEL | FILES |
|---|---|---|---|---|
| T1 | Regenerar el lock con el comando canónico y el corte nuevo | CLAUDE (procedimiento mecánico) | n-a | `resources/backend/requirements.lock` |
| T2 | IDL-04 acepta fracción de segundo en el corte; nueva SDV-08 (suelo de transitivas desde `cve-review`) | DEEPSEEK | deepseek-v4-pro | `tests/test_dependencias_lock.py`, `tests/test_seguridad_dependencias.py` |
| T3 | Registro de seguridad: tabla «Avisos de dependencias transitivas», con PYSEC-2026-4320 marcado como corregido | CLAUDE (registro de decisión) | n-a | `docs/evidence/cve-review.md` |

## 4. Constitution gate y trazabilidad
- ADR-014: actualización controlada, moviendo el corte de forma deliberada.
- P10/P16: sin avisos conocidos corregibles en el grafo.
- Sin cambios de producto, esquema, migraciones ni Dockerfile.

| Requisito | Tarea | Prueba |
|---|---|---|
| certifi en el lock y ≥ suelo | T1 | SDV-08 |
| certifi no directa | T1 | SDV-08 |
| Corte coherente con la publicación del suelo | T1 | SDV-08 |
| Comando canónico completo en la cabecera, con fracción | T1/T2 | IDL-04 |
| Lock completo y fijado; directas iguales en manifiesto y lock | T1 | IDL-01..03 |

Trazabilidad: 5 de 5 requisitos con tarea y prueba.

## 5. Material gate
| Indicador | Valor |
|---|---|
| PYSEC_2026_4320_REVALIDATED · CERTIFI_SAFE_VERSION · CERTIFI_SECURITY_FLOOR | 1 · 2026.10.19 · 2026.10.19 |
| CERTIFI_RELEVANT_UPLOAD_TIME | 2026-10-20T02:24:15.072385Z |
| LOCK_CUTOFF_PREVIOUS → NEW · DELTA | 2026-10-20T00:00:00Z → 2026-10-20T02:24:15.073Z · 8655,073 s |
| LOCK_GRAPH_DETERMINISTIC | 1 |
| TARGET · DIRECT · TRANSITIVE_REQUIRED · UNRELATED changes | certifi · 0 · 0 · **0** |
| NEW_APPLICABLE_FINDINGS_OTHER_THAN_TARGET | 0 |
| PRODUCT · REQUIREMENTS · DOCKER · SCHEMA · MIGRATION change required | 0 · 0 · 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 6. Implementación
- **T1:** lock regenerado, igual al candidato e idempotente. Diff:
  - la línea 2 de la cabecera, que ahora lleva el corte nuevo;
  - `certifi==2026.10.18` → `certifi==2026.10.19`.
- **T2:** DeepSeek lo hizo a la primera, con AUDIT_PASS.
- **T3:** `cve-review.md` actualizado.

## 7. Pruebas y mutaciones
- **Rojo contra `e0f0804`** (`red-against-head.txt`): solo falla SDV-08, por
  `certifi: lock 2026.10.18 < suelo 2026.10.19`. IDL y el resto pasan.
- **Mutaciones:** **12/12 KILLED**, todas restauradas (`mutations.json`).
  - M01 certifi 2026.10.18; M02 2026.7.22; M03 sin certifi; M04 certifi directa.
  - M05 corte anterior; M06 sin `--upgrade`; M07 cabecera con otra plataforma.
  - M08 transitiva sin pin; M09 directa desigual.
  - M10 suelo documental 2026.10.18; M11 registro sin fila; M12 publicación posterior al corte.

## 8. Certificación
Detalle en `evidence/lock-certifi-cutoff/certification.md`. El equipo se **reinició** a mitad de la primera cadena, y
V5 y el PostgreSQL de QA se reconstruyeron con el método documentado (`environment-incident-and-v5-rebuild.md`). La
cadena completa se repitió sin suspensiones.

| Corrida | V0 | V5 (lock nuevo) |
|---|---|---|
| Dirigidas | 104/104 (inverso: 1 fallo previo, atribuido) | 104/104 (ídem) |
| SQLite | 1928/0/1056 ×2 | 1928/0/1056 |
| PostgreSQL | 2958/0/26 | 2958/0/26 |
| E2E | 284/0/0 | 284/0/0 |
| pip-audit (PyPI y OSV) | — | **0 · 0** |
| OpenAPI | 544/533/11 | 544/533/11; deriva de contrato 0 |

## 9. Convergencia
| Deuda | Estado |
|---|---|
| **LOCK-CERTIFI-PYSEC-2026-4320** | **CLOSED / CONVERGED**: aviso revalidado; corte mínimo (+8655,073 s) justificado con la frontera medida; determinista; solo cambia certifi; suelo protegido por SDV-08 sin volverla directa; pip-audit 0 en PyPI y OSV; V0 y V5 verdes |
| **PRODUCTION-BASE-IMAGE-FLOATING-TAG** | **CLOSED / CONVERGED**: su único criterio pendiente («V5 pip-audit 0») se cumple ahora. El resto del gate se conserva: base `70729b46…` sin cambios, IBB verdes, V5 IMAGE_ROOTFS verde y OpenAPI sin deriva |
| BASE-IMAGE-CA-STORE-DSA-6572 | CLOSED / CONVERGED (sin cambio) |
| TEST-DOCUMENTS-CATALOG-ORDER-DEPENDENT (nueva) | OPEN, menor, previa, de pruebas (dueña 046) |
| Observación | la etiqueta `python:3.13.16-slim-trixie` se reconstruyó (`cf50a4f6…`, con `ca-certificates` deb13u1). Oportunidad de volver a fijar la base y retirar el pin de CA en un ciclo propio |
| Puertas externas (Docker) | BASE-IMAGE-RUNTIME-CONTENTS-NOT-CERTIFIED · EXACT_IMAGE_CA_RUNTIME · IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED · runtime de libmagic y de runtime stage · OBS-09 |
