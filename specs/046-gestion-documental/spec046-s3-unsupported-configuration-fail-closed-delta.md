# SPEC 046 · Delta — S3-UNSUPPORTED-CONFIGURATION-FAIL-CLOSED

| Campo | Valor |
|---|---|
| Deudas | **PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED** (dueña 046) · **DEUDA-046-1** (adaptador S3 IMPLEMENTED_NOT_VERIFIED) |
| Decisiones | OD-GOV-START-01 (S3 = OPTION B: no soportado, fallo cerrado, sin `boto3`) · **OD-S3-01** (dueña, 2026-10-25): se **retira** el adaptador `S3CompatibleStorageProvider` · OD-CERT-30 (SPEC054 confirmada con la certificación oficial pendiente; se abre este ciclo) |
| HEAD de entrada | `c0216e8` |
| Evidencia | `evidence/s3-unsupported-configuration-fail-closed/` |
| Autorización de implement | Encargo de la dueña («opción 3») + OD-S3-01 (Constitución P2) |

## 1. Specify

**Objetivo.** S3 no forma parte de la línea base del producto. El almacenamiento documental es solo de sistema de
archivos, y una instalación configurada para S3 no arranca: no hay vuelta silenciosa al disco ni un 500 en el primer uso.
El producto deja de importar `boto3`.

**Requisitos.**
- **R1:** `S3CompatibleStorageProvider` desaparece del producto. `get_storage()` siempre devuelve el proveedor de sistema de archivos y no lee ninguna variable `KONTROL_S3_*`.
- **R2:** si existe cualquier variable cuyo nombre empiece por `KONTROL_S3_` (sin distinguir mayúsculas), `Settings` falla al validarse y, por tanto, el servicio no arranca (FR-001-005):
  - cubre el entorno del proceso y el fichero `.env` que lee `Settings`;
  - la configuración a medias también falla;
  - el mensaje nombra las variables y nunca sus valores.
- **R3:** sin variables S3, el comportamiento actual del sistema de archivos queda intacto: misma raíz, mismo contrato y la misma conformidad.
- **R4:** la frontera de dependencias ya no admite opcionales del producto: `boto3` sale de `OPCIONALES_DEL_PRODUCTO`, y cualquier import de terceros fuera del lock vuelve a ser un fallo.
- **R5:** documentación y trazabilidad:
  - FR-046-032 queda **NOT_SUPPORTED_BY_PRODUCT_BASELINE**;
  - DEUDA-046-1 se cierra por retirada;
  - PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED se cierra como NOT_SUPPORTED_BY_PRODUCT_BASELINE / CONFIGURATION_GUARDED.

**Fuera de alcance.**
- Implementar S3 o añadir `boto3`.
- Tocar la abstracción `DocumentStorageProvider` (FR-046-030 se mantiene).
- Cambiar el análisis o la ruta de almacenamiento.

## 2. Clarify (medido)

| Hecho | Medida |
|---|---|
| Selección actual | `get_storage()` lee `KONTROL_S3_BUCKET` y `KONTROL_S3_ENDPOINT` con `os.environ` y, si están las dos, crea `S3CompatibleStorageProvider`; si falta una, **vuelve en silencio** al sistema de archivos |
| Fallo actual | sin `boto3` (que no está en ningún lock), el primer uso lanza `StorageError STORAGE_MISCONFIGURED` 500 |
| Configuración | `Settings` (`env_prefix="KONTROL_"`, `env_file=".env"`, `extra="ignore"`, `hide_input_in_errors=True`) ignora hoy las `KONTROL_S3_*`; ya hay validadores que fallan al inicio (`secret_key`, ancla de licencia) |
| Pruebas S3 | `tests/test_documents_storage.py`: el parámetro `s3` de la conformidad (8 pruebas siempre omitidas), `test_el_adaptador_s3_no_se_acopla_a_un_fabricante` y `test_la_seleccion_de_proveedor_es_configuracion_no_codigo` |
| Frontera | `tests/test_dependencias_frontera.py`: `OPCIONALES_DEL_PRODUCTO = frozenset({"boto3"})`; IDF-08 exige que el conjunto sin distribución sea igual a ese |
| Otras referencias | `docs/governance/KONTROL_ARCHITECTURE_BASELINE.md` (MinIO/S3), `docs/roadmap/046-dependency-closeout.md` y `specs/046-gestion-documental/{SPEC_046_FINAL_CLOSEOUT.md,plan.md,data-model.md,tasks.md,traceability-matrix.md}`; ningún `.env.example`, compose ni README |
| Dependencia | `python-dotenv` 1.2.4 ya está en `requirements.lock` (lo trae pydantic-settings) |

## 3. Diseño

- **D1 — Retirada.** Se eliminan de `app/modules/documents/storage.py`:
  - la clase `S3CompatibleStorageProvider`;
  - las importaciones que solo usaba ella;
  - la rama S3 de `get_storage()`.

  Los docstrings del módulo y de `get_storage` dicen que el único proveedor de la línea base es el sistema de archivos y que S3 no está soportado (OD-S3-01).
- **D2 — Guarda.** Nuevo `@model_validator(mode="after")` `_s3_no_soportado` en `Settings`:
  - nombres = las claves de `os.environ` y del `.env` de `model_config["env_file"]` (si existe, leído con `dotenv_values`) cuya versión en mayúsculas empieza por `KONTROL_S3_`;
  - si hay alguna: `ValueError("El almacenamiento compatible con S3 no está soportado en la línea base de KONTROL (OD-S3-01); el almacenamiento documental es solo de sistema de archivos. Quita: <nombres>")`;
  - solo nombres, ordenados.
- **D3 — Pruebas** (fichero nuevo `tests/test_documents_storage_s3_no_soportado.py`, S3N-01…):
  - guarda por variable, en minúsculas, en `.env` y con valores que nunca aparecen;
  - sin variables, arranque normal y FILESYSTEM;
  - checks estructurales: sin clase S3, sin `boto3` ni `KONTROL_S3` en `storage.py`.

  En `test_documents_storage.py` se retira el parámetro `s3` y las dos pruebas solo de S3, y la conformidad queda sobre el sistema de archivos. En `test_dependencias_frontera.py`, `OPCIONALES_DEL_PRODUCTO = frozenset()`.
- **D4 — Documentación** (Claude: especificaciones, roadmap y gobierno). FR-046-032 pasa a NOT_SUPPORTED_BY_PRODUCT_BASELINE; se actualizan el cierre de DEUDA-046-1, la matriz de deuda y la línea base de arquitectura.

## 4. Plan y tareas

| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| TS-A | Pruebas S3N (rojo) | DEEPSEEK | v4-pro | sí (fallo cerrado de configuración) | sí | 2 | `tests/test_documents_storage_s3_no_soportado.py` | rojo por las causas correctas | rojo atribuido |
| TS-1 | D1 retirada + D2 guarda | DEEPSEEK | v4-pro | sí | sí | 2 | `app/modules/documents/storage.py`, `app/core/config.py` | S3N | verde |
| TS-2 | Pruebas existentes (conformidad y frontera) | DEEPSEEK | v4-flash | no | sí | 2 | `tests/test_documents_storage.py`, `tests/test_dependencias_frontera.py` | conformidad, IDF | verde |
| TS-3 | Documentación y trazabilidad | CLAUDE | n-a | no | n-a | — | specs/docs | revisión | hecho |

## 5. Gate y trazabilidad

- Producto: sí, retirada más guarda de configuración.
- Esquema, migraciones y dependencias de producción: 0; se elimina una dependencia opcional no declarada.
- OpenAPI: sin cambios esperados; la deriva debe ser 0.
- Seguridad: la guarda falla cerrado y no expone valores.

| Requisito | Tareas | Pruebas |
|---|---|---|
| R1 | TS-1 | S3N estructurales y FILESYSTEM |
| R2 | TS-1 | S3N de guarda |
| R3 | TS-2 | conformidad del sistema de archivos |
| R4 | TS-2 | IDF-08 |
| R5 | TS-3 | revisión |

Trazabilidad 5/5. BLOCKER = CRITICAL = CONTRADICTIONS = 0; MATERIAL OQ = 0 (resuelta con OD-S3-01).

## 6. Estado (2026-10-25)
**IMPLEMENTED — CERTIFICATION PENDING** (técnicamente convergida). La certificación oficial queda pendiente del anfitrión dedicado
(OD-CERT-30): la misma corrida certificará SPEC054 y esta delta.

| Medida | Resultado |
|---|---|
| R1 retirada | `S3CompatibleStorageProvider`, `import io` y la rama S3 de `get_storage()` eliminados (−115 líneas); `storage.py` sin `boto3` ni `KONTROL_S3` |
| R2 guarda | `Settings._s3_no_soportado`: cualquier `KONTROL_S3_*` (entorno o `.env`, sin distinguir mayúsculas) hace fallar el arranque; solo nombres, nunca valores |
| R3 sistema de archivos | la conformidad sigue en verde (ahora solo con el proveedor real) |
| R4 frontera | `OPCIONALES_DEL_PRODUCTO = frozenset()`; IDF-08 en verde |
| Rojo previo | `evidence/…/red-s3n.txt`: 9 de 10 fallan por la guarda o la retirada ausentes |
| Pruebas dirigidas | 56 passed (S3N, conformidad, frontera, clamd); ruff global 0; mypy de los ficheros tocados 0 |
| Mutaciones | 7 de 7 eliminadas, restauración verificada (`mutations.json`) |
| SQLite (diagnóstico) | **2138 / 0 / 1062**; las 8 omisiones de conformidad S3 desaparecen |
| PostgreSQL (diagnóstico) | **3182 / 0 / 18**; ídem |
| OpenAPI | firma idéntica a la referencia (3.1.0, 411/544/533/11, huella `444c820e…`): deriva 0 |
| Seguridad | sin cambios de dependencias; se elimina una opcional no declarada |
| Orquestación | 6 llamadas, $0.0078 (`orchestration.md`) |

S3_PROVIDER_SUPPORTED = 0; S3_CONFIGURATION_GUARDED = 1. Siguiente: GOVERNMENT-START-READINESS.
