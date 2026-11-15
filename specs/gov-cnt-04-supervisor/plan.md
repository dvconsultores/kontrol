# Plan · CNT-04 Supervisor / responsable del contrato

## Constitution Gate

```text
GOV_CNT_004_CLEAR=1  CNT01_PREREQUISITE_CLEAR=1  SUPERVISOR_IDENTITY_CLEAR=1  OCCUPATION_AUTHORITY_CLEAR=1
DESIGNATION_ACT_CLEAR=1  DESIGNATING_AUTHORITY_CLEAR=1 (OD-CNT04-02)  EFFECTIVE_DATE_RULE_CLEAR=1  REPLACEMENT_RULE_CLEAR=1
CONCURRENCY_RULE_CLEAR=1  SOD_RULE_CLEAR=1
NEW_DESIGNAR_CONTRACTS_COMPETENCY_INVENTED=0  CNT03_NOT_ABSORBED=1  P1_P2_OVERLAP=0
MATERIAL_DECISION_REQUIRED=0 (OD-CNT04-01 y 02 resueltas por la dueña el 2026-11-15)
BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0 UNKNOWN=0  -> PASS
```

Constitución:
- P2: autorización por encargo nominal CNT-04.
- Tenant: Scope.COMPANY y 404 para ajenos.
- Inmutabilidad: trigger PG.
- MFA: SENSITIVE.
- Auditoría: CTL-02.
- Sin migración destructiva: tabla nueva y un permiso nuevo; el downgrade retira ambos.

## Datos: `gov_contract_supervisors` (modelo `GovernmentContractSupervisorAssignment`, migración 0117)

| Columna | Tipo | Nota |
|---|---|---|
| id, created_at, updated_at, created_by, version | mixins | UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin |
| company_id | String(36) FK companies, index | |
| contract_id | String(36) FK gov_contracts, index | |
| numero | Integer | 1..n por contrato; referencia `SUP-NN` |
| estado | String(12) | CHECK IN ('VIGENTE','SUSTITUIDA') |
| official_id | FK gov_officials | |
| assignment_id | FK gov_assignments | ocupación ORG-04 elegida |
| position_id | FK gov_positions | |
| unit_id | FK gov_units | |
| act_id | FK gov_acts, index | acto de designación |
| funcionario_nombre | String(200) | instantánea |
| funcionario_documento | String(40) | instantánea enmascarada (`enmascarar_documento`) |
| figura | String(24) | figura de la ocupación (TITULAR, ENCARGADURIA, SUPLENCIA, COMISION_SERVICIO) |
| cargo_codigo / cargo_nombre | String(30) / String(200) | instantánea |
| unidad_nombre | String(250) | instantánea |
| acto_etiqueta | String(400) | instantánea: `{Tipo} N.º {numero} del {fecha}` |
| acto_emisor_cargo | String(200) | instantánea |
| desde | Date | |
| hasta | Date null | |
| motivo | String(500) null | obligatorio si `sustituye_id` no es nulo |
| sustituye_id / sustituida_por_id | String(36) FK self null | |
| registrado_en | DateTime(tz) | |
| registrado_por | String(36) | |

CHECK:
- `hasta IS NULL OR hasta >= desde`;
- `(estado = 'VIGENTE') = (hasta IS NULL AND sustituida_por_id IS NULL)`;
- `sustituye_id IS NULL OR motivo IS NOT NULL`;
- `numero >= 1`.

Índices:
- UNIQUE(contract_id, numero);
- índice único parcial `uq_gov_contract_supervisors_vigente` sobre (contract_id) WHERE estado = 'VIGENTE' (postgresql_where y sqlite_where).

Trigger PG `kontrol_gov_contract_supervisor_guard`:
- DELETE y TRUNCATE lanzan GOV_CONTRACT_SUPERVISOR_IMMUTABLE.
- La única UPDATE válida va de OLD.estado = 'VIGENTE' a NEW.estado = 'SUSTITUIDA', con `NEW.hasta` y `NEW.sustituida_por_id` no nulos, y todas las demás columnas iguales salvo version y updated_at. Cualquier otra UPDATE lanza el mismo error.

El guard va dos veces: como DDL en models.py (after_create, solo postgresql, como `GOV_CONTRACTS_GUARD_PG`) y en la migración.

Permiso nuevo:
- `gobierno_contratos:assign_supervisor` (permissions y role_permissions de FUNCIONAL_COMPLETO, como `_conceder_permisos` de 0115). El downgrade lo retira de todos los roles.
- setup/api.py: `"gobierno_contratos": ["view", "manage", "formalize", "assign_supervisor"]`.
- mfa_policy: SENSITIVE.

## Servicio `service_contratos_supervision.py` (nuevo, sin tocar service_contratos.py)

`designar(db, ctx, user, contrato_id, cuerpo)` recibe `{funcionario_id, asignacion_id, acto_id, desde, motivo?, sustituye_id?}`:

1. Contrato del ente con FOR UPDATE; si no existe, 404 GOV_CONTRACT_NOT_FOUND. Si `estado ≠ FORMALIZADO`, 409 GOV_CONTRACT_SUPERVISOR_CONTRACT_NOT_FORMALIZED. El contrato nunca se escribe (el guard de CNT-01 lo prohíbe).
2. Designación vigente con FOR UPDATE. Si `sustituye_id ≠ vigente.id` (incluido el caso null frente a existente), 409 GOV_CONTRACT_SUPERVISOR_STALE con `details.vigente_id`.
3. Fecha efectiva (`desde`):
   - mínimo: `min(fecha_inicio, fecha_formalizacion)`, porque la supervisión controla la ejecución desde el inicio del plazo (LCP art. 137.1); con vigente, además `vigente.desde + 1 día`;
   - máximo: `fecha_fin`. Una fecha futura deja la designación programada (`situacion = PROGRAMADA`); la supervisión expone `programada` y `ultima_id` (la VIGENTE, que el cliente cita como `sustituye_id`). Cada `item` lleva `situacion` (EN_EJERCICIO, PROGRAMADA o CONCLUIDA). La FK `sustituida_por_id` es DEFERRABLE INITIALLY DEFERRED, porque la anterior se cierra antes de insertar la nueva;
   - fuera de rango: 422 GOV_CONTRACT_SUPERVISOR_DATE_INVALID en el campo `desde`.
   - Con vigente, el motivo no puede estar en blanco: 422 GOV_CONTRACT_SUPERVISOR_REASON_REQUIRED.
4. Funcionario del ente en estado ACTIVO; si no, 422 GOV_CONTRACT_SUPERVISOR_OFFICIAL_INVALID en `funcionario_id`.
5. La ocupación debe estar en `ocupaciones_de_funcionario(db, ctx, funcionario_id, desde)` y en la misma lista para hoy, con `situacion = VIGENTE` y figura cuyo grupo no sea DELEGACION. Si no, 422 GOV_CONTRACT_SUPERVISOR_OCCUPATION_INVALID en `asignacion_id`, con auditoría BLOCKED.
6. Acto:
   - del ente, `status = EFICAZ` y `fecha_eficacia ≤ desde`; si no, 422 GOV_CONTRACT_SUPERVISOR_ACT_INVALID en `acto_id` (con BLOCKED);
   - con vigente, si `acto_id = vigente.act_id`, 422 GOV_CONTRACT_SUPERVISOR_ACT_REUSED;
   - si `_autoridad_valida(db, company, acto.cargo_id, acto.fecha, "APROBAR", "CONTRATACIONES")` es falso, 422 GOV_CONTRACT_SUPERVISOR_ACT_AUTHORITY_INVALID (con BLOCKED);
   - después, `exigir_autoridad_funcional(db, ctx, acto.cargo_id, "APROBAR", "CONTRATACIONES")`.
7. SoD: `evaluar_antes_de_actuar(db, ctx, "PROC03_CONTRATO_SUPERVISOR_DESIGNAR" o "..._SUSTITUIR", "GovernmentProcurementFile", contrato.file_id)`.
8. Escritura:
   - `numero = max + 1`; el id se genera antes;
   - si hay vigente: `estado = SUSTITUIDA`, `hasta = desde − 1`, `sustituida_por_id = nuevo.id`, `version += 1`, y flush;
   - después se inserta la nueva fila VIGENTE y se hace flush;
   - una IntegrityError única (`es_violacion_unica`) responde 409 GOV_CONTRACT_SUPERVISOR_CONFLICT.
9. Expediente con FOR UPDATE: `version += 1` y `_evento(…, "CONTRATO", desde, "Supervisor de {codigo}: {nombre}", detalle="{cargo} · {unidad} · {acto}")`.
10. Auditoría:
    - acción GOV_CONTRACT_SUPERVISOR_ASSIGNED o GOV_CONTRACT_SUPERVISOR_REPLACED, sobre GovernmentProcurementFile = `file_id`;
    - after con {contrato, designacion, supervisor, cargo, unidad, acto, desde, sustituye, motivo}, sin None.
11. Devuelve `supervision(...)`.

Lecturas:
- `supervision(db, ctx, contrato_id)` → {contrato: {id, codigo, estado, fecha_formalizacion, fecha_fin}, vigente: item | None (= `supervisor_en(hoy)`), historia: [item] por número descendente, puede_designar}.
- `item` → {id, referencia "SUP-NN", numero, estado, estado_etiqueta (Vigente / Sustituida), funcionario: {id, nombre, documento}, asignacion_id, figura, figura_etiqueta, cargo: {id, codigo, nombre}, unidad: {id, nombre}, acto: {id, etiqueta, emisor_cargo}, desde, hasta, motivo, sustituye (referencia o null), registrado_en}.
- `opciones(db, ctx, contrato_id, fecha)` → {fecha, vigente_id, funcionarios: [{id, nombre, documento, ocupaciones: [{asignacion_id, figura_etiqueta, cargo_id, cargo, unidad_id, unidad}]}] (solo los que tienen ocupación válida en la fecha y hoy), actos: [{id, etiqueta, emisor_cargo, fecha, fecha_eficacia}] (EFICAZ con eficacia ≤ fecha y emisor válido con APROBAR×CONTRATACIONES)}.
- `supervisor_en(db, ctx, contrato_id, fecha)` → item | None, por intervalo (desde ≤ fecha y hasta nulo o ≥ fecha).
- `supervisor_vigente(db, ctx, contrato_id)` = `supervisor_en(hoy)`.

## API `api_contratos_supervision.py` (nuevo router, prefijo `/gobierno/contratos/{contrato_id}/supervision`)

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `` | gobierno_contratos:view | supervision |
| GET | `/opciones?fecha=` | gobierno_contratos:assign_supervisor | opciones |
| GET | `/en?fecha=` | gobierno_contratos:view | {fecha, supervisor: item \| null} |
| POST | `/designaciones` | gobierno_contratos:assign_supervisor + require_write_allowed | 201 supervision |

## Frontend

- `contratos/SupervisionContrato.tsx` (nuevo) y su `.test.tsx`.
- ContratoPage lo pinta cuando `estado = FORMALIZADO`, después de «Instrumento formalizado».
- Sección `<section aria-labelledby>` con h2 «Supervisor / responsable del contrato». Muestra:
  - el vigente (dl), o un EmptyState «Sin supervisor designado»;
  - la región «Historial de supervisores» (tabla);
  - el formulario (solo con assign_supervisor): fecha efectiva, funcionario, ocupación (con cargo y unidad visibles), acto y motivo (si hay vigente). El botón «Formalizar designación» abre un ConfirmationDialog y el POST lleva `sustituye_id`.
- Los tipos van en `contratos/api.ts`.

## Pruebas

- **PG** (`test_gov_cnt04_supervisor.py`):
  - vectores A–H;
  - permisos y MFA;
  - aislamiento;
  - inmutabilidad (UPDATE, DELETE y TRUNCATE);
  - concurrencia real (`carrera`) de designación y de sustitución;
  - acto no eficaz;
  - acto de un cargo sin APROBAR;
  - delegación no es ocupación;
  - auditoría;
  - cronología;
  - `supervisor_en`.
- **Vitest:** la sección (vacía, vigente, historia, formulario y error).
- **E2E:** se extiende al final del recorrido de `gobierno-contratos.spec.ts`, porque el contrato formalizado ya existe.
- **Fijaciones:**
  - cabeza Alembic;
  - catálogo de auditoría +3;
  - MFA SENSITIVE +1;
  - techo de delegación +1;
  - OpenAPI.
