# Plan · BUD-06

## Constitution gate

```text
GOV_BUD_009_CLEAR=1  GOV_BUD_010_CLEAR=1  CREDIT_AUTHORITY_CLEAR=1 (BUD-05)  AVAILABILITY_FORMULA_CLEAR=1  CERTIFICATE_EFFECT_CLEAR=1
SIGNER_AUTHORITY_CLEAR=1 (ORG-03 FIRMAR×PRESUPUESTO + ORG-06 exigir_autoridad_funcional, sin segundo sistema)
EXPEDIENT_AUTHORITY_CLEAR=1 (PROC-03 opcional + referencia textual; sin DOC-01 ni motor nuevo)
ANNULMENT_RULE_CLEAR=1  MONETARY_RULE_CLEAR=1 (contrato BUD-05)  CONCURRENCY_RULE_CLEAR=1 (FOR UPDATE ejercicio + crédito)
BUD07_NOT_ABSORBED=1  BUD08_NOT_ABSORBED=1  BUD11_NOT_ABSORBED=1  SECOND_BUDGET_LEDGER_CREATED=0
MATERIAL_DECISION_REQUIRED=0  SHARED_CORE_CHANGE_REQUIRED=0 (permiso nuevo en el catálogo de Gobierno existente)
CONSTITUTION_GATE=PASS
```

## Decisiones de diseño (Claude, no materiales)

| Id | Decisión |
|---|---|
| PDD-B06-01 | Se certifica en APROBADO y RECONDUCIDO (LOPPM 234-236); nunca en BORRADOR ni en CERRADO (LOPPM 248) |
| PDD-B06-02 | La fecha de emisión es hoy (Caracas) y debe caer dentro del año del ejercicio (LOPPM 250) |
| PDD-B06-03 | Capacidad nueva `gobierno_presupuesto:certify` (SENSITIVE) para emitir y anular. `view` consulta y descarga. `manage` no basta |
| PDD-B06-04 | `concepto` (10–500 caracteres) obligatorio: el objeto que se certifica |
| PDD-B06-05 | La huella es el sha256 del snapshot canónico de la certificación (el patrón del fundamento de BUD-01). El PDF tiene su propio sha256 en el almacenamiento |
| PDD-B06-06 | La emisión no exige If-Match del ejercicio (el ejercicio aprobado no cambia de versión): la integridad la dan los bloqueos de fila. La anulación bloquea la fila de la certificación y exige el estado VIGENTE |
| PDD-B06-07 | Los rechazos (422 y 409) no se auditan: igual que PDD-B05-06, no los pide ningún requisito |

## Modelo (migración `0112_gov_bud06_certificacion`, down `0111_gov_bud05_aprobado`)

Tabla `gov_budget_certificates` con estas columnas:
- comunes: id, timestamps, created_by, year_id, company_id;
- datos: credit_id FK, numero int, codigo String(20), estado String(10) CHECK, monto, saldo_antes y saldo_despues Numeric(18,2), moneda String(3), fecha Date, concepto, expediente_referencia String(120), procurement_file_id FK nullable;
- firmante: firmante_cargo_id FK gov_positions, firmante_cargo_codigo, firmante_cargo_nombre, firmante_unidad, firmante_funcionario_id nullable, firmante_funcionario_nombre nullable, emitida_por, emitida_en;
- integridad: snapshot JSON, huella String(64);
- documento: documento_storage_key, documento_sha256, documento_tamano, documento_nombre;
- anulación: anulada_por, anulada_en, motivo_anulacion;
- restricciones: UNIQUE(year_id, numero), UNIQUE(company_id, codigo), CHECK de los saldos y CHECK de la coherencia de la anulación.

Además:
- trigger de inmutabilidad: sin DELETE; UPDATE solo VIGENTE → ANULADA, sin tocar ningún otro campo;
- historia: CHECK con +2 tipos;
- permiso `gobierno_presupuesto:certify` sembrado y concedido a FUNCIONAL_COMPLETO, como en 0107.

## API (base `/gobierno/presupuesto/ejercicios/{id}`)

- GET `/disponibilidad`, con filtros categoria_id, unidad_id, partida_id y fuente_id.
- GET `/certificaciones` y GET `/certificaciones/{cid}` (view).
- POST `/certificaciones` (certify).
- POST `/certificaciones/{cid}/anular` (certify).
- GET `/certificaciones/{cid}/documento` (view; PDF).

## Encargos a DeepSeek (deepseek-v4-pro; objetivo 3–5, tope 8)

1. C1: datos y contrato.
2. C2: dominio, PDF y almacenamiento.
3. C3: pruebas PG.
4. C4: pantalla y Vitest.
5. C5: E2E.
