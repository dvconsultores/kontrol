# Plan · CNT-01

## Constitution Gate

```text
GOV_CNT_001_CLEAR=1
AWARD_AUTHORITY_CLEAR=1          PROC-08: decisión VIGENTE + ADJUDICADA + offer_id
CONTRACTOR_AUTHORITY_CLEAR=1     PROC-06: oferta adjudicada (fotografía)
OBJECT_AUTHORITY_CLEAR=1         PROC-03: GovernmentProcurementFile.objeto
AMOUNT_AUTHORITY_CLEAR=1         PROC-06 OMA: total_con_tributos de la versión vigente
CURRENCY_AUTHORITY_CLEAR=1       PROC-06 OMA: moneda declarada (VES, USD o EUR)
TERM_AUTHORITY_CLEAR=1           instrumento contractual: fecha_inicio y fecha_fin
BUDGET_SOURCE_AUTHORITY_CLEAR=1  BUD-06: CDP VIGENTE
GUARANTEE_AUTHORITY_CLEAR=1      PROC-10: instrumentos REGISTRADA
DOCUMENT_AUTHORITY_CLEAR=1       DOC-08: documento vinculado al expediente, versión vigente y sha256
SIGNER_AUTHORITY_CLEAR=1         ORG-03/04/06/07: FIRMAR × CONTRATACIONES + límite (patrón AAL)
CNT01_REQUIRES_BUD08=0
CNT01_REQUIRES_PROC05=0
PARTIAL_AWARD_SUPPORTED=0
AUTO_DERIVE_INSTRUMENT_FROM_MODALITY=0
CNT02_NOT_ABSORBED=1 CNT03_NOT_ABSORBED=1 CNT04_NOT_ABSORBED=1 CNT08_NOT_ABSORBED=1
MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

### Fuentes que contradicen el encargo

- **LCP arts. 74 y 75.** Permiten firmar el contrato por el monto disponible y hacer contratos plurianuales. No contradicen el encargo, porque *permiten* y no *exigen*; el encargo es más estricto. Esa variante se documenta como OQ-CNT01-01 y no se construye.
- **VES frente a VED.** Se documenta como OQ-CNT01-02. Con igualdad estricta de códigos no hace falta ninguna decisión para construir.

En ninguno de los dos casos se detiene el ciclo.

## Decisiones de diseño (Claude)

| Id | Decisión |
|---|---|
| OD-CNT01-01 | Un módulo nuevo, `service_contratos.py`, con su API en `api_contratos.py` y prefijo `/gobierno/contratos`. Se reutilizan los ayudantes de PROC-03 (`_evento`, `_abierto`) y el patrón documental de PROC-10 |
| OD-CNT01-02 | El código del instrumento se asigna al formalizar, con prefijo según el tipo y secuencia por ente, prefijo y año, bajo `pg_advisory_xact_lock(7012001, hashtext(company_id))`. En SQLite no hay bloqueo |
| OD-CNT01-03 | Un contrato por decisión, con `UNIQUE (decision_id)`. Si la decisión deja de estar vigente, el borrador queda bloqueado y no se descarta. La nueva adjudicación genera otro contrato |
| OD-CNT01-04 | La cobertura y las garantías se sustituyen completas con PUT. No hay UPDATE de vínculos: se borran y se vuelven a insertar mientras el contrato está en BORRADOR |
| OD-CNT01-05 | El clasificador AAL se generaliza en `service_decision_limite.py` con dos funciones nuevas, `competencia_en_vigor(db, cargo, fecha, accion, materia)` y `clasificar_monto(tipo_limite, monto_limite, moneda_limite, monto, moneda)`. `evaluar_limite` de PROC-08 pasa a usarlas sin cambiar su resultado. CNT-01 las usa con FIRMAR × CONTRATACIONES |
| OD-CNT01-06 | La cronología del expediente tiene una clase nueva, `CONTRATO`: el CHECK se amplía en la migración, como hizo 0096 con `GARANTIA`. Se anota solo al formalizar |
| OD-CNT01-07 | La auditoría usa `entity_type = "GovernmentProcurementFile"` y el id del expediente, como PROC-10, para que CTL-01 detecte las acciones. Su detalle es `DETALLE_CONTRATO`, sin importes |
| OD-CNT01-08 | La fecha de formalización es `hoy_de_negocio()` (Caracas): con ella se evalúan la competencia y el límite del firmante, igual que en BUD-06 |
| OD-CNT01-09 | No hay constancia PDF interna (opcional en el encargo §34). La autoridad es el documento firmado, que se abre con el módulo de documentos |

## Modelo de datos (migración `0114_gov_cnt01_contratos`)

> Reencadenada en la integración: P1 publicó `0113_gov_bud08_compromiso` durante el ciclo. La migración se renombró a `0114_gov_cnt01_contratos` con `down_revision = 0113_gov_bud08_compromiso`, sin cambiar su contenido; ALEMBIC_HEAD_COUNT=1.

### `gov_contracts`

`GovernmentContract`: UUIDMixin, TimestampMixin, CreatedByMixin y VersionMixin, `__scope__ = COMPANY`.

| Columna | Tipo | Nulo | Nota |
|---|---|---|---|
| company_id | String(36) FK companies | no | index |
| file_id | String(36) FK gov_procurement_files | no | index |
| decision_id | String(36) FK gov_procurement_decisions | no | **UNIQUE** |
| offer_id | String(36) FK gov_procurement_offers | no | index |
| act_id | String(36) FK gov_acts | no | acto de la decisión |
| amount_id | String(36) FK gov_procurement_offer_amounts | no | versión del monto usada |
| estado | String(12) | no | default BORRADOR |
| tipo | String(16) | sí | CONTRATO, ORDEN_COMPRA u ORDEN_SERVICIO |
| codigo | String(20) | sí | al formalizar |
| numero | Integer | sí | ≥ 1 |
| anio | SmallInteger | sí | |
| expediente_numero | String(40) | no | fotografía |
| objeto | String(1000) | no | fotografía |
| descripcion_complementaria | String(2000) | sí | |
| decision_referencia | String(10) | no | DEC-NN |
| decision_fecha | Date | no | fecha de `decidida_en` en Caracas |
| acto_etiqueta | String(400) | no | «{tipo} {numero}» del acto |
| oferta_referencia | String(12) | no | R-NNNN |
| contratista_nombre | String(300) | no | |
| contratista_documento | String(40) | no | |
| contratista_representante | String(200) | sí | |
| monto | Numeric(18,2) | no | > 0 |
| moneda | String(3) | no | `length = 3` |
| fecha_inicio, fecha_fin | Date | sí | fin ≥ inicio |
| referencia_instrumento | String(120) | sí | |
| document_id | String(36) FK documents | sí | |
| document_version_id | String(36) FK document_versions | sí | |
| documento_version_numero | BigInteger | sí | |
| documento_sha256 | String(64) | sí | |
| documento_titulo | String(300) | sí | |
| firmante_cargo_id | String(36) FK gov_positions | sí | |
| firmante_cargo_nombre | String(200) | sí | |
| firmante_funcionario_nombre | String(200) | sí | |
| fecha_formalizacion | Date | sí | |
| formalizado_en | DateTime(tz) | sí | |
| formalizado_por | String(36) | sí | |
| snapshot | JSON | sí | |
| huella | String(64) | sí | |

**CHECK:**
- `estado IN (...)`;
- `tipo IS NULL OR tipo IN (...)`;
- `monto > 0`;
- `length(moneda) = 3`;
- `numero IS NULL OR numero >= 1`;
- `fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio`;
- completitud según el estado:
  - en BORRADOR son nulos `codigo`, `numero`, `anio`, `fecha_formalizacion`, `formalizado_en`, `formalizado_por`, `snapshot` y `huella`;
  - en FORMALIZADO no es nulo ninguno de `tipo`, `codigo`, `numero`, `anio`, `fecha_inicio`, `fecha_fin`, `referencia_instrumento`, `document_id`, `document_version_id`, `documento_sha256`, `firmante_cargo_id`, `fecha_formalizacion`, `formalizado_en`, `formalizado_por`, `snapshot` y `huella`.

**UNIQUE:** `(company_id, codigo)` y `decision_id`.

### `gov_contract_budget_allocations`

`GovernmentContractBudgetAllocation`: UUIDMixin, TimestampMixin y CreatedByMixin.

- **Columnas:**
  - `company_id`;
  - `contract_id` (FK, index);
  - `certificate_id` (FK `gov_budget_certificates`, index);
  - `year_id` (FK `gov_budget_years`);
  - `certificado_codigo` String(20);
  - `monto` Numeric(18,2), con CHECK > 0;
  - `moneda` String(3).
- **Restricción:** `UNIQUE (contract_id, certificate_id)`.

### `gov_contract_guarantees`

`GovernmentContractGuarantee`: UUIDMixin, TimestampMixin y CreatedByMixin.

- **Columnas:**
  - `company_id`;
  - `contract_id` (FK, index);
  - `instrument_id` (FK `gov_guarantee_instruments`, index);
  - `garantia_referencia` String(20).
- **Restricción:** `UNIQUE (contract_id, instrument_id)`.

### Disparadores (solo PostgreSQL)

- **`kontrol_gov_contract_guard()`** es BEFORE UPDATE OR DELETE en `gov_contracts`:
  - DELETE: excepción `GOV_CONTRACT_IMMUTABLE`;
  - `OLD.estado = 'FORMALIZADO'`: excepción;
  - cambio (`IS DISTINCT FROM`) en `company_id`, `file_id`, `decision_id`, `offer_id`, `act_id`, `amount_id`, `expediente_numero`, `objeto`, `decision_referencia`, `oferta_referencia`, `contratista_nombre`, `contratista_documento`, `monto` o `moneda`: excepción;
  - en otro caso, `RETURN NEW`.
  - Más un disparador BEFORE TRUNCATE.
- **`kontrol_gov_contract_link_guard()`** es BEFORE INSERT OR UPDATE OR DELETE en las dos tablas de vínculos:
  - UPDATE: excepción;
  - si el contrato (`COALESCE(NEW.contract_id, OLD.contract_id)`) está FORMALIZADO: excepción;
  - en otro caso, `RETURN COALESCE(NEW, OLD)`.
  - Más disparadores TRUNCATE.
- Mensaje: `ERRCODE 'P0001'`, `MESSAGE 'GOV_CONTRACT_IMMUTABLE'`.

### Otros cambios de la migración

- `CLASES_EVENTO_EXPEDIENTE` añade `CONTRATO`; el CHECK `ck_gov_procurement_file_events_ck_gov_procurement_file__de56` se borra y se vuelve a crear con la lista nueva.
- Permisos `gobierno_contratos` `view`, `manage` y `formalize`, concedidos a FUNCIONAL_COMPLETO con el patrón `_conceder_permisos` de 0112.
- `downgrade` simétrico.

## API (`/api/v1/gobierno/contratos`)

| Método | Ruta | Permiso | Cuerpo | Respuesta |
|---|---|---|---|---|
| GET | `` | view | `?estado=&tipo=` | `{items: [...]}` |
| POST | `` | manage | `{expediente_id}` | 201 ficha |
| GET | `/{contrato_id}` | view | — | ficha |
| PATCH | `/{contrato_id}` | manage | If-Match; `tipo?`, `fecha_inicio?`, `fecha_fin?`, `referencia_instrumento?`, `descripcion_complementaria?`, `documento_id?` | ficha |
| PUT | `/{contrato_id}/cobertura` | manage | If-Match; `{asignaciones: [{certificado_id, monto}]}` | ficha |
| PUT | `/{contrato_id}/garantias` | manage | If-Match; `{instrumento_ids: []}` | ficha |
| POST | `/{contrato_id}/formalizar` | formalize | If-Match; `{firmante_cargo_id}` | ficha |

**Ficha.**
- **Identificación y estado:** `id`, `version`, `estado`, `estado_etiqueta`, `tipo`, `tipo_etiqueta`, `codigo` e `identificacion` (el código, o «Borrador · {expediente} · {DEC-NN}»).
- **Origen:**
  - `expediente{id, numero}`;
  - `decision{id, referencia, fecha, acto, vigente}`;
  - `oferta{id, referencia}`;
  - `contratista{nombre, documento, representante}`.
- **Condiciones:**
  - `objeto`, `descripcion_complementaria`, `monto`, `moneda`;
  - `fecha_inicio`, `fecha_fin`, `referencia_instrumento`;
  - `documento{id, titulo, version, sha256}` o nulo.
- **Cobertura y garantías:**
  - `cobertura{asignaciones: [{certificado_id, codigo, monto, moneda, anio, partida, fuente, estado}], total_asignado, faltante, completa}`;
  - `garantias: [{instrumento_id, referencia, tipo_etiqueta, emisor, monto, moneda, vigente_hasta, estado}]`.
- **Formalización:** `firmante{cargo, funcionario}` o nulo, `fecha_formalizacion`, `formalizado_en` y `huella`.
- **Opciones** (solo en BORRADOR; vacío en FORMALIZADO):
  - `certificados_elegibles: [{id, codigo, monto, saldo_libre, moneda, anio, partida, fuente, concepto}]`;
  - `garantias_elegibles: [...]`;
  - `documentos_elegibles: [{id, titulo, version}]`;
  - `firmantes: [{cargo_id, cargo, limite, control{estado, estado_etiqueta, permite, mensaje}}]`.
- **Estado para formalizar:** `pendientes` (lista de mensajes de lo que falta) y `puede_formalizar`.

La ficha del expediente (PROC-08), en la decisión vigente, añade `contrato: {id, identificacion, estado}` o `null`.

## Orden de comprobación al formalizar

1. Contrato `FOR UPDATE`, con If-Match. Si no es BORRADOR, 409 `GOV_CONTRACT_ALREADY_FORMALIZED`.
2. Expediente `FOR UPDATE` y ABIERTO.
3. Decisión: vigente, ADJUDICADA y misma oferta; si no, 409 `GOV_CONTRACT_AWARD_NOT_CURRENT`. Monto vigente igual (`id`, total y moneda); si no, 409 `GOV_CONTRACT_SOURCE_CHANGED`.
4. Campos completos (tipo, fechas, referencia y documento); si falta alguno, 422 `GOV_CONTRACT_INCOMPLETE` con `field_errors`.
5. Documento: sigue vinculado, con la misma versión vigente y el mismo `sha256`; si no, 409 `GOV_CONTRACT_DOCUMENT_CHANGED`.
6. CDP `FOR UPDATE` ordenadas por id. Cada una debe estar VIGENTE (si no, 409 `GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE`), tener la misma moneda, el mismo ejercicio y un expediente compatible, y no quedar sobreasignada. La suma debe ser igual al monto (409 `GOV_CONTRACT_COVERAGE_INSUFFICIENT`).
7. Garantías vinculadas: todas siguen REGISTRADA; si no, 409 `GOV_CONTRACT_GUARANTEE_NOT_ACTIVE`.
8. Firmante:
   - el cargo debe ser del ente;
   - su estructura se bloquea con `FOR UPDATE`;
   - `_autoridad_valida(hoy, FIRMAR, CONTRATACIONES)`; si falla, 422 `GOV_CONTRACT_SIGNER_INVALID`;
   - `exigir_autoridad_funcional`;
   - límite: si bloquea, `record_audit_after_rollback(GOV_CONTRACT_SIGNER_BLOCKED)` y 409.
9. CTL-01: `evaluar_antes_de_actuar("PROC03_CONTRATO_FORMALIZAR")`.
10. Cierre:
    - código;
    - fotografía y huella (sha256 del JSON canónico con `sort_keys`);
    - estado FORMALIZADO y campos del firmante;
    - `version += 1` en el contrato y en el expediente;
    - `_evento(CONTRATO)`;
    - auditoría `GOV_CONTRACT_FORMALIZED`.

## Frontend

- **Menú:** la sección «Gobierno · Contratos» tiene la entrada «Contratos y órdenes», en `/gobierno/contratos`.
- **`ContratosPage`:** lista con filtros por estado y tipo.
- **`ContratoPage`** (`/gobierno/contratos/:contratoId`):
  - datos del origen en solo lectura;
  - formulario del borrador;
  - selector de CDP con monto asignado;
  - casillas de garantías;
  - selector de documento;
  - firmante con el panel de límite;
  - «Formalizar» con confirmación;
  - ficha FORMALIZADA.
- **`ExpedienteDecision`:** con la decisión vigente ADJUDICADA aparecen el botón «Crear contrato u orden» (permiso manage) y el enlace «Ver contrato» si ya existe.
- **Diseño:** sin UUID, en una columna en móvil y con `break-words`.

## Pruebas

- **Backend en PostgreSQL** (`tests/test_gov_cnt01_contratos.py`): los vectores A a I del encargo, inmutabilidad en base, permisos y MFA, catálogo, cronología y CTL-01.
- **Vitest:** de las páginas.
- **E2E:** `gobierno-contratos.spec.ts` con el recorrido del encargo §50 y sus negativas, a 1280, 390 y 320 px, más Axe.
- **Mutaciones:** sin `FOR UPDATE` de las CDP, `>=` en la cobertura, sin revalidar la decisión, y el límite del firmante.
