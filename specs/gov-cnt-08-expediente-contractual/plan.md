# Plan · CNT-08 Expediente contractual

## Arquitectura

| Fichero | Contenido |
|---|---|
| `alembic/versions/0119_gov_cnt08_expediente.py` | Tablas `gov_contract_dossier_packages` y `gov_contract_dossier_package_verifications`, con guardas de inmutabilidad en PG (patrón de 0071 y DOC-08) |
| `models.py` | `GovernmentContractDossierPackage` y `GovernmentContractDossierPackageVerification`, que reutilizan `RESULTADOS_VERIFICACION_PAQUETE` |
| `service_expediente_contractual.py` | Proyección: `listar`, `expediente`, `cronologia`, `auditoria` e `integridad`, más los ayudantes públicos `indice_documental`, `cronologia_completa` y `FUENTES_FUTURAS` |
| `service_expediente_paquetes.py` | `generar`, `listar`, `descargar` y `verificar`, con las primitivas de `service_paquetes` |
| `schemas_paquetes.PaqueteIn` (DOC-08, reutilizado) | `proposito` de 10 a 1000 caracteres; no hay esquema nuevo |
| `api_expediente_contractual.py` | Rutas de la tabla de abajo |
| `audit_catalog_entries.py` | +4 entradas `GOV_CONTRACT_DOSSIER_PACKAGE_*`, con entidad `GovernmentContractDossierPackage` y proceso `gov-cnt-08` |

## Rutas (prefijo `/api/v1`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| GET `/gobierno/expedientes-contractuales` | `gobierno_contratos:view` | Lista paginada |
| GET `/gobierno/contratos/{id}/expediente` | `gobierno_contratos:view` | Expediente |
| GET `/gobierno/contratos/{id}/expediente/cronologia` | `gobierno_contratos:view` | Cronología paginada |
| GET `/gobierno/contratos/{id}/expediente/auditoria` | `gobierno_contratos:view` + `gobierno_auditoria:view` | Eventos CTL-02 paginados |
| GET `/gobierno/contratos/{id}/expediente/integridad` | `gobierno_contratos:view` | Integridad por documento |
| POST `/gobierno/contratos/{id}/expediente/paquetes` | `gobierno_paquetes:generate` (MFA), escritura | 201 creado; 200 en repetición idempotente (`Idempotency-Key`) |
| GET `/gobierno/contratos/{id}/expediente/paquetes` | `gobierno_paquetes:view` | Paquetes del contrato |
| GET `/gobierno/expedientes-contractuales/paquetes/{paquete_id}/descargar` | `gobierno_paquetes:view` + control documental | ZIP |
| POST `/gobierno/expedientes-contractuales/paquetes/verificar` | `gobierno_paquetes:view`, escritura | Resultado de la verificación |

Las consultas GET no hacen commit; los POST sí. Un contrato de otra empresa da 404 `GOV_CONTRACT_NOT_FOUND`. Un BORRADOR da 409 `GOV_CONTRACT_DOSSIER_NOT_FORMALIZED`.

## Reglas

- **R1 · Vigencia (D08-06):**
  - `hoy < fecha_inicio` → POR_INICIAR («Por iniciar»);
  - `hoy > fecha_fin_vigente` → VENCIDO («Plazo vencido»);
  - en otro caso → EN_PLAZO («En plazo»).

  `fecha_fin_vigente` es `historia(...)["vigente"]["fecha_fin"]` de CNT-02.
- **R2 · Índice documental:**
  - **Entradas y su clave estable:**

    | Tipo | Origen | Clave |
    |---|---|---|
    | INSTRUMENTO | `gov_contracts.document_*` | `doc:{document_id}:{version_id}` |
    | MODIFICACION | `document_*` de las modificaciones FORMALIZADA | `doc:{document_id}:{version_id}` |
    | GARANTIA | `document_*` de los instrumentos vinculados | `doc:{document_id}:{version_id}` |
    | FOLIO | folios de documento del expediente PROC-03, versión `document_version_id` o la vigente | `doc:{document_id}:{version_id}` |
    | ACTO | `documento_acto_id` del acto de adjudicación y de los de designación, versión vigente | `doc:{document_id}:{version_id}` |
    | COMPROBANTE_CDP | `documento_storage_key` y `documento_sha256` de las CDP de la trazabilidad | `cdp:{id}` |
    | COMPROBANTE_COMPROMISO | ídem, de los compromisos del expediente | `cmp:{id}` |

  - **Duplicados:** una clave repetida se fusiona y acumula sus referencias.
  - **Huella registrada:** la de la autoridad (`documento_sha256` del contrato o de la modificación, `sha256` de la garantía). En folios y actos es `DocumentVersion.sha256`.
- **R3 · Integridad:**
  - **Documento del gestor:**
    - versión ausente → MISSING;
    - `huella_registrada ≠ DocumentVersion.sha256` → MISMATCH;
    - binario ausente (`storage.exists`) → MISSING;
    - `storage.verify(StoredFile.storage_key, huella)` falso → MISMATCH;
    - en otro caso → VERIFIED.
  - **Comprobante BUD:** la misma regla sobre `documento_storage_key` y `documento_sha256`.
  - **Sin huella:** NOT_APPLICABLE.
- **R4 · Cronología (D08-05):** la fecha va en `fecha`, ISO (date). Las fuentes son:

  | Proceso | Origen | `fecha` | Tipo |
  |---|---|---|---|
  | PROC-03 | Eventos del expediente, salvo las clases CONTRATO y GARANTIA | `evento.fecha` | La clase del evento |
  | BUD-06 | Cada CDP de la trazabilidad | `cert.fecha` | CDP_EMITIDA, y CDP_ANULADA con la fecha de `anulada_en` |
  | BUD-08 | Cada compromiso | `fecha` | COMPROMISO_REGISTRADO, y COMPROMISO_ANULADO |
  | PROC-10 | Instrumentos vinculados | `fecha_emision` (efectiva: `vigente_desde`) | GARANTIA_REGISTRADA |
  | PROC-10 | Eventos de esos instrumentos | `fecha` | GARANTIA_\<accion\> |
  | CNT-01 | Contrato | `fecha_formalizacion` (efectiva: `fecha_inicio`) | CONTRATO_FORMALIZADO |
  | CNT-02 | Cada modificación formalizada | `fecha_instrumento` (efectiva: `vigente_desde`) | MODIFICACION_FORMALIZADA |
  | CNT-04 | Cada designación | `desde` (documento: fecha del acto) | SUPERVISOR_DESIGNADO, o SUPERVISOR_SUSTITUIDO si `sustituye` |
  | CNT-08 | Paquetes generados | `created_at` | PAQUETE_GENERADO |

  Orden: `fecha`, después `fecha_registro` (los nulos al final) y después el orden de proceso (PROC-03, PROC-10, BUD-06, BUD-08, CNT-01, CNT-02, CNT-04, CNT-08). `orden` empieza en 1 sobre la lista completa; los filtros se aplican después de numerar.
- **R5 · Auditoría:** los ids del expediente son: el expediente PROC-03, el contrato, la decisión, las modificaciones, las designaciones, los instrumentos de garantía, las CDP, los compromisos y los paquetes CNT-08. La consulta es `AuditEvent` con el tenant y la empresa del contexto y `entity_id IN ids`, ordenada por `event_time` descendente y paginada; se resume con `service_auditoria._resumenes`.
- **R6 · Paquete:**
  - **Formato:** `kontrol-gobierno-expediente-contractual`, versión 1.
  - **Código:** `EC-{año}-{n:04d}` por empresa; `numero_generacion` por contrato.
  - **Documentos:** los del gestor se evalúan con `service_paquetes._evaluar` (incluye el permiso `documentos:download`); los folios reservados quedan EXCLUIDO por RESERVADO; los comprobantes BUD solo entran con `gobierno_presupuesto:view` y si `storage.verify` es verdadero (si no, EXCLUIDO por SIN_PERMISO o NO_DISPONIBLE).
  - **Límites:** los de DOC-08 (`MAX_DOCUMENTOS`, `MAX_BYTES`); si se superan, 422 `GOV_CONTRACT_DOSSIER_PACKAGE_TOO_LARGE`.
  - **Manifiesto:** `contract_id`, `contract_code`, `company_id`, `generated_at`, `generated_by`, `version_producto` (`app.__version__`), `corte`, `fuentes_incluidas`, `fuentes_excluidas` (FUENTES_FUTURAS), `documentos`, `archivos`, `totales` (`eventos`, `documentos_incluidos`, `documentos_excluidos`, `archivos` y `bytes`) y `algoritmo_hash`.
  - **ZIP:** fechas fijas, entradas ordenadas y los documentos sin compresión; `SHA256SUMS` cubre todos los ficheros, incluido el manifiesto.
  - **Registro:** el paquete y su verificación quedan registrados e inmutables; generar, descargar y verificar se auditan.
- **R7 · Snapshot (D08-03):** en `generar`, primero `db.commit()` (cierra la transacción de lectura de la autenticación) y después `db.connection(execution_options={"isolation_level": "REPEATABLE READ"})` si el dialecto es `postgresql`. La proyección, el ZIP y el registro ocurren en esa transacción.
- **R8 · Verificación:** sigue la semántica de `service_paquetes.verificar` (`_copiar_subida`, `_entradas_seguras` y `_huella_de_entrada`). El paquete se busca por `paquete.codigo` del manifiesto, dentro del tenant y la empresa. Motivos: MANIFIESTO_AUSENTE, MANIFIESTO_ILEGIBLE, PAQUETE_NO_REGISTRADO, MANIFIESTO_ALTERADO, ARCHIVO_AUSENTE, ARCHIVO_ALTERADO y ARCHIVO_INESPERADO.

## Forma de las respuestas

Ver `contracts/expediente.md`.

## Frontend

| Ruta | Pantalla | Permiso |
|---|---|---|
| `gobierno/expedientes-contractuales` | `ExpedientesContractualesPage`: filtros, tabla y paginación | `gobierno_contratos:view` |
| `gobierno/contratos/:contratoId/expediente` | `ExpedienteContractualPage`: 14 secciones con navegación interna | `gobierno_contratos:view` |

- Nueva entrada de menú «Expedientes contractuales» en «Gobierno · Contratos».
- En `ContratoPage`, un contrato formalizado muestra el enlace «Expediente contractual».
- No se muestran UUID como dato principal.
