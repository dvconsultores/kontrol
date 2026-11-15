# Plan · CNT-02

## Constitution Gate

```text
GOV_CNT_002_CLEAR=1              IR §7.5 + LCP arts. 74, 130–135 (FUENTES.md)
CNT01_AUTHORITY_CLEAR=1          GovernmentContract FORMALIZADO (inmutable por la guarda PG)
OBS_CNT01_BUD08_01=CLOSED        decisión de la dueña: cobertura documental (delta H07–H10)
OBS_CNT01_TRE09_01=CLOSED        decisión de la dueña: canonical_currency + TRE-09 (delta H01–H06)
ORIGINAL_CONTRACT_IMMUTABLE=1    no se escribe en gov_contracts ni en sus vínculos
EFFECTIVE_STATE_DERIVABLE=1      proyección = última formalizada con vigente_desde ≤ D
AMENDMENT_TYPES_CLEAR=1          ADENDA, PRORROGA, MODIFICACION, VARIACION (sin efecto automático)
TERM_CHANGE_RULE_CLEAR=1         solo extensión: nueva_fecha_fin > fecha_fin base
AMOUNT_CHANGE_RULE_CLEAR=1       delta ≠ 0; nuevo = anterior + delta > 0 (CHECK)
BUDGET_COVERAGE_RULE_CLEAR=1     cobertura válida + adicional exacta = monto nuevo; saldo H07
BUD08_CONSISTENCY_RULE_CLEAR=1   reducción: compromisos del expediente ≤ monto nuevo
AUTHORITY_RULE_CLEAR=1           FIRMAR × CONTRATACIONES contra el monto efectivo nuevo; MFA
TRE09_RULE_CLEAR=1               verificar_limite a la fecha de formalización; GOV_OFFICIAL_RATE_REQUIRED
CONCURRENCY_RULE_CLEAR=1         un borrador por contrato; numero único; previous único; base_numero; versión
OBJECT_CHANGE_ALLOWED=0  CONTRACTOR_CHANGE_ALLOWED=0  CURRENCY_CHANGE_ALLOWED=0
CNT02_CREATES_BUD08_COMMITMENT=0  CNT03/04/06/07_IMPLEMENTED=0
P1_P2_OVERLAP=0                  P1 = CNT-04; las pantallas de CNT-02 son nuevas y ContratoPage solo recibe un enlace
BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0 MATERIAL_OQ=0 UNKNOWN=0
MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

Las OQ abiertas (OQ-CNT02-01..03, OBS-CNT02-LIBERACION-01) aplican la opción más restrictiva y no bloquean el ciclo.

## Decisiones de diseño (Claude)

| Id | Decisión |
|---|---|
| OD-CNT02-01 | Módulo nuevo `service_contratos_modificaciones.py` con `schemas_contratos_modificaciones.py` y `api_contratos_modificaciones.py`. Las rutas cuelgan de `/gobierno/contratos/{contrato_id}/modificaciones`. Los ayudantes compartidos con CNT-01 se publican en `service_contratos.py`: `control_firmante`, `saldo_libre`, `compromisos_del_expediente`, `documento_valido` y `reclamado_formalizado`. |
| OD-CNT02-02 | Se reutilizan los permisos `gobierno_contratos:view/manage/formalize`, porque formalizar un instrumento modificatorio es formalizar un instrumento contractual. Sin permisos nuevos no cambian los recuentos de permisos ni de MFA. |
| OD-CNT02-03 | La SoD añade `PROC03_MODIFICACION_PREPARAR` y `PROC03_MODIFICACION_FORMALIZAR` en `CATALOGO_SOD["PROC-03"]`, como hizo CNT-01. |
| OD-CNT02-04 | La cronología usa la clase `CONTRATO` existente. No se toca el CHECK de eventos, así que el downgrade no tiene trampas con eventos sembrados. |
| OD-CNT02-05 | Fecha de formalización = `hoy_de_negocio()`. Con ella se evalúan la competencia, el límite, la tasa y las reglas de C02-17. |
| OD-CNT02-06 | El borrador se puede descartar con DELETE físico de sus filas BORRADOR y de sus asignaciones. La guarda PG solo lo permite en estado BORRADOR. |
| OD-CNT02-07 | Las pantallas son dos y nuevas: `ContratoModificacionesPage` (historia y estado efectivo) y `ModificacionPage` (borrador y ficha formalizada). `ContratoPage` solo recibe el enlace, las condiciones vigentes y la conversión del firmante (H06), para no solaparse con CNT-04 de P1. |

## Modelo de datos (migración `0118_gov_cnt02_modificaciones`, `down_revision = 0116_gov_proc08_conversion`)

### `gov_contract_amendments` · `GovernmentContractAmendment`

Mixins: UUID, Timestamp, CreatedBy y VersionMixin. `__scope__ = COMPANY`.

| Columna | Tipo | Nulo | Nota |
|---|---|---|---|
| company_id | String(36) FK companies | no | index |
| contract_id | String(36) FK gov_contracts | no | index |
| file_id | String(36) FK gov_procurement_files | no | index; copia de `contrato.file_id` |
| estado | String(12) | no | default `BORRADOR` |
| tipo | String(14) | no | |
| numero | Integer | sí | se asigna al formalizar |
| codigo | String(40) | sí | |
| previous_amendment_id | String(36) FK gov_contract_amendments | sí | |
| base_numero | Integer | no | default 0 |
| motivo | String(2000) | sí | |
| fecha_instrumento | Date | sí | |
| vigente_desde | Date | sí | |
| nueva_fecha_fin | Date | sí | |
| delta_monto | Numeric(18,2) | sí | |
| condiciones | String(4000) | sí | |
| referencia_instrumento | String(120) | sí | |
| document_id / document_version_id | String(36) FK documents / document_versions | sí | |
| documento_version_numero | BigInteger | sí | |
| documento_sha256 | String(64) | sí | |
| documento_titulo | String(300) | sí | |
| moneda | String(3) | no | canónica del contrato |
| monto_anterior / monto_nuevo | Numeric(18,2) | sí | al formalizar |
| fecha_fin_anterior / fecha_fin_nueva | Date | sí | al formalizar |
| firmante_cargo_id | String(36) FK gov_positions | sí | |
| firmante_cargo_nombre | String(200) | sí | |
| firmante_funcionario_nombre | String(200) | sí | |
| fecha_formalizacion | Date | sí | |
| formalizado_en | DateTime(tz) | sí | |
| formalizado_por | String(36) | sí | |
| snapshot | JSON | sí | |
| huella | String(64) | sí | |

Restricciones:
- `uq_gov_contract_amendments_numero` (contract_id, numero).
- `uq_gov_contract_amendments_codigo` (company_id, codigo).
- `uq_gov_contract_amendments_previa` (previous_amendment_id).
- Índice único parcial `uq_gov_contract_amendments_borrador` (contract_id) `WHERE estado = 'BORRADOR'`, en PG y en SQLite.
- CHECK:
  - `estado IN ('BORRADOR','FORMALIZADA')`;
  - `tipo IN ('ADENDA','PRORROGA','MODIFICACION','VARIACION')`;
  - `numero IS NULL OR numero >= 1`;
  - `base_numero >= 0`;
  - `delta_monto IS NULL OR delta_monto <> 0`;
  - `length(moneda) = 3`;
  - `vigente_desde IS NULL OR fecha_instrumento IS NULL OR vigente_desde >= fecha_instrumento`;
  - **montos**: `monto_nuevo IS NULL OR (monto_nuevo > 0 AND monto_nuevo = monto_anterior + COALESCE(delta_monto, 0))`;
  - **plazo**: `fecha_fin_nueva IS NULL OR (nueva_fecha_fin IS NULL AND fecha_fin_nueva = fecha_fin_anterior) OR (nueva_fecha_fin IS NOT NULL AND nueva_fecha_fin > fecha_fin_anterior AND fecha_fin_nueva = nueva_fecha_fin)`;
  - **completitud**:
    - `(estado='BORRADOR' AND numero IS NULL AND codigo IS NULL AND monto_anterior IS NULL AND monto_nuevo IS NULL AND fecha_fin_anterior IS NULL AND fecha_fin_nueva IS NULL AND fecha_formalizacion IS NULL AND formalizado_en IS NULL AND formalizado_por IS NULL AND snapshot IS NULL AND huella IS NULL)`
    - `OR (estado='FORMALIZADA' AND numero IS NOT NULL AND codigo IS NOT NULL AND motivo IS NOT NULL AND fecha_instrumento IS NOT NULL AND vigente_desde IS NOT NULL AND referencia_instrumento IS NOT NULL AND document_id IS NOT NULL AND document_version_id IS NOT NULL AND documento_sha256 IS NOT NULL AND monto_anterior IS NOT NULL AND monto_nuevo IS NOT NULL AND fecha_fin_anterior IS NOT NULL AND fecha_fin_nueva IS NOT NULL AND firmante_cargo_id IS NOT NULL AND fecha_formalizacion IS NOT NULL AND formalizado_en IS NOT NULL AND formalizado_por IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL)`.

### `gov_contract_amendment_allocations` · `GovernmentContractAmendmentAllocation`

Columnas: `company_id` (FK companies, index), `amendment_id` (FK, index), `contract_id` (FK gov_contracts, index), `certificate_id` (FK gov_budget_certificates, index), `year_id` (FK gov_budget_years), `certificado_codigo` String(20), `monto` Numeric(18,2) y `moneda` String(3).

Restricciones: `uq_gov_contract_amendment_allocations_certificado` (amendment_id, certificate_id) y `CHECK monto > 0`.

### Disparadores (solo PostgreSQL, en el modelo y en la migración)

- `kontrol_gov_contract_amendment_guard()`, BEFORE UPDATE OR DELETE en `gov_contract_amendments`:
  - DELETE: error si `OLD.estado <> 'BORRADOR'`.
  - UPDATE: error si `OLD.estado = 'FORMALIZADA'`, o si cambia `company_id`, `contract_id`, `file_id`, `moneda` o `created_by`.
  - Se añade un trigger de TRUNCATE.
  - Mensaje: `GOV_CONTRACT_AMENDMENT_IMMUTABLE`.
- `kontrol_gov_contract_amendment_link_guard()`, BEFORE INSERT OR UPDATE OR DELETE en las asignaciones: error en UPDATE y en TRUNCATE, y si la modificación madre está FORMALIZADA.

## API (`/api/v1/gobierno/contratos/{contrato_id}/modificaciones`)

| Método y ruta | Permiso | Cuerpo y cabeceras | Respuesta |
|---|---|---|---|
| GET `` `?fecha=YYYY-MM-DD` | view | — | historia y estado efectivo (abajo) |
| POST `` | manage | `{tipo}` | ficha del borrador, 201 |
| GET `/{modificacion_id}` | view | — | ficha |
| PATCH `/{modificacion_id}` | manage | If-Match; campos del borrador | ficha |
| PUT `/{modificacion_id}/cobertura` | manage | If-Match; `{asignaciones:[{certificado_id, monto}]}` | ficha |
| DELETE `/{modificacion_id}` | manage | If-Match | 204 |
| POST `/{modificacion_id}/formalizar` | formalize (MFA) | If-Match; `{firmante_cargo_id}` | ficha |

**GET historia:**
- `contrato`: `{id, codigo, identificacion, tipo_etiqueta, estado, contratista_nombre, objeto, moneda}`.
- `original`: `{monto, moneda, fecha_inicio, fecha_fin, huella}`.
- `vigente`: `{fecha, monto, fecha_fin, modificacion_codigo|null, programadas:[codigo]}`.
- `ultima`: `{monto, fecha_fin, vigente_desde|null, modificacion_codigo|null}`.
- `historial`: `[{id, codigo, numero, tipo, tipo_etiqueta, fecha_instrumento, vigente_desde, motivo, plazo:{anterior, nuevo}|null, monto:{anterior, delta, nuevo}|null, condiciones, firmante:{cargo, funcionario}, documento:{titulo, version, sha256}, huella, formalizado_en, cobertura_adicional:[{codigo, monto}]}]`, ordenado por `numero`.
- `borrador`: `{id, tipo, tipo_etiqueta}` o null.
- `puede_crear` y `motivo_no_crear`.

**Ficha de la modificación:**
- Identidad: `id, version, estado, estado_etiqueta, tipo, tipo_etiqueta, codigo, identificacion` («Borrador · {codigo_contrato}» o el código).
- Contexto: `contrato {id, codigo}`, `moneda`.
- Campos: `fecha_instrumento, vigente_desde, motivo, nueva_fecha_fin, delta_monto, condiciones, referencia_instrumento`, `documento {id, titulo, version, sha256}|null`.
- `base {monto, fecha_fin, numero}`; `propuesta {monto_nuevo|null, fecha_fin_nueva}`.
- `cobertura {existente_valida, requerida_adicional, asignaciones:[{certificado_id, codigo, monto, moneda, anio, partida, fuente, estado}], total_asignado, completa}`.
- `compromisos {total, moneda, permite, mensaje}`.
- `firmante {cargo, funcionario, limite, conversion|null}|null`; `formalizado_en`, `huella`.
- `opciones {certificados_elegibles, documentos_elegibles, firmantes}`, solo en BORRADOR.
- `pendientes []` y `puede_formalizar`.

## Orden de comprobación al formalizar

1. Contrato de la empresa con FOR UPDATE (404); estado FORMALIZADO (409 `GOV_CONTRACT_NOT_FORMALIZED`).
2. Modificación de ese contrato con FOR UPDATE (404).
   - Sin If-Match: 428 `GOV_CONTRACT_AMENDMENT_IF_MATCH_REQUIRED`.
   - Versión distinta: 409 `GOV_CONTRACT_AMENDMENT_STALE`.
   - Estado distinto de BORRADOR: 409 `GOV_CONTRACT_AMENDMENT_ALREADY_FORMALIZED`.
   - `base_numero` distinto del número de formalizadas: 409 `GOV_CONTRACT_AMENDMENT_STALE`.
3. Expediente con FOR UPDATE.
4. Base = la última formalizada, o el contrato si no hay ninguna. Hoy mayor que `base.fecha_fin`: 409 `GOV_CONTRACT_AMENDMENT_CONTRACT_EXPIRED`.
5. Faltantes: `motivo`, `fecha_instrumento`, `vigente_desde`, `referencia_instrumento`, `documento_id`, y `nueva_fecha_fin` si es PRORROGA. Responde 422 `GOV_CONTRACT_AMENDMENT_INCOMPLETE` con `field_errors`. Si no hay ningún cambio (ni plazo, ni delta, ni condiciones): 422 `GOV_CONTRACT_AMENDMENT_NO_CHANGE`.
6. Fechas según C02-17: 422 `GOV_CONTRACT_AMENDMENT_DATE_INVALID`. Plazo (C02-06): 422 `GOV_CONTRACT_AMENDMENT_TERM_INVALID`. Monto nuevo ≤ 0: 422 `GOV_CONTRACT_AMENDMENT_AMOUNT_INVALID`.
7. Documento revalidado: 409 `GOV_CONTRACT_AMENDMENT_DOCUMENT_CHANGED`.
8. Cobertura (C02-08), con las CDP del borrador FOR UPDATE ordenadas por id:
   - CDP no válida: 409 `GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE`.
   - Saldo libre insuficiente: 409 `GOV_CONTRACT_CERTIFICATE_OVERALLOCATED`.
   - Suma distinta de lo requerido: 409 `GOV_CONTRACT_AMENDMENT_COVERAGE_INSUFFICIENT`, con `{cubierto, requerido, monto_nuevo, moneda}`.
9. Reducción frente a compromisos (C02-09).
10. Firmante: cargo de la empresa (422 `GOV_CONTRACT_SIGNER_INVALID`), estructura FOR UPDATE, `_autoridad_valida` y `exigir_autoridad_funcional`. Después `control_firmante(monto_nuevo)`:
    - SIN_TASA: 422;
    - EXCEDE: 409;
    - en ambos casos se registra `GOV_CONTRACT_AMENDMENT_SIGNER_BLOCKED` tras el rollback.
11. SoD: `PROC03_MODIFICACION_FORMALIZAR`.
12. Asignaciones: `numero = max + 1`, `codigo`, `previous_amendment_id`, fotografía y huella (sha256 del JSON canónico, como CNT-01). Después:
    - se sella el soporte (`resource_type = "GovernmentContractAmendment"`) y se congela el vínculo;
    - se incrementa `expediente.version`, se registra `_evento CONTRATO` y se audita `GOV_CONTRACT_AMENDMENT_FORMALIZED`.

## Frontend

- `api.ts` (contratos) recibe los tipos y las rutas `rutaModificaciones(id)` y `rutaModificacion(id, mid)`.
- Pantallas nuevas:
  - `ContratoModificacionesPage.tsx`: tarjetas «Condiciones originales» y «Condiciones vigentes al …» (con las programadas), historia en línea de tiempo y acción «Nueva modificación» (o «Continuar el borrador»).
  - `ModificacionPage.tsx`:
    - formulario del borrador, con vista previa del monto y del plazo anterior y nuevo;
    - cobertura adicional, compromisos y firmante con su control;
    - pendientes, «Formalizar» y «Descartar borrador»;
    - ficha formalizada de solo lectura, con documento, huella y conversión.
- `router.tsx` y `pantallas.ts` reciben dos rutas cada uno, con `gobierno_contratos:view` y alcance de empresa.
- `ContratoPage.tsx` recibe:
  - en un contrato formalizado, el enlace «Modificaciones (n)» y las condiciones vigentes;
  - en el firmante formalizado, la conversión.
- No se expone ningún UUID: las CDP, documentos y cargos se eligen por etiqueta.

## Pruebas

- PG, `tests/test_gov_cnt02_modificaciones.py`: C02-01..20 con vectores de concurrencia, inmutabilidad en base, aislamiento, MFA, SoD y auditoría.
- PG, `tests/test_gov_cnt01_moneda_cobertura.py`: H01–H09.
- Se ajusta `test_vector_g_moneda_distinta` de CNT-01, porque H05 sustituye CURRENCY_MISMATCH.
- Mutaciones M1–M6 sobre `service_contratos_modificaciones.py` y `service_contratos.py`.
- Vitest de las dos pantallas.
- E2E `e2e/gobierno-contratos-modificaciones.spec.ts`.
