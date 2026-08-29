# VALIDACIÓN DE MIGRACIONES — SPEC 045

Reproducible con `bash qa/pg-migration-validation.sh`.

## Caso A · base limpia

```
alembic upgrade head   → 0001 … 0016 sin error
alembic current        → 0016_approvals_backfill (head)
alembic heads          → 0016_approvals_backfill (head)   [head único, sin ramas]
tablas creadas         → 153
```

| Comprobación | Resultado |
|---|---|
| Todas las migraciones ejecutan | ✔ |
| `0015` (esquema) ejecuta | ✔ 8 tablas + renombrado de la legada |
| `0016` (datos) ejecuta | ✔ permisos + histórico |
| Head divergente | ✔ ninguno |
| FK inválidas | ✔ ninguna |
| Constraints incompatibles | ✔ ninguno |
| Esquema final ↔ ORM | ✔ sin drift de 045 |

## Caso B · base anterior a 045, con datos

Estado inicial: cadena hasta `0014` + instalación, tenant, empresa, rol ADMIN,
usuario y **4 solicitudes legadas** (3 con empresa válida, 1 con referencia colgante).

```
[0016] omitida solicitud legada leg-4: la empresa 'co-BORRADA' ya no existe.
[0016] 1 solicitud(es) omitida(s) por empresa inexistente. Permanecen en
       `regulatory_approval_requests`, sin pérdida de datos.
```

### Conteos

| Métrica | Antes | Después |
|---|---:|---:|
| Solicitudes legadas | 4 | **4** (renombradas, íntegras) |
| Solicitudes en el motor | 0 | **3** |
| Permisos `aprobaciones` | 0 | **6** |
| `role_permissions` de ADMIN | 0 | **6** |

**Pérdida de datos: 0.** Las 4 filas legadas conservan id, referencia, importe,
decisión y estado:

```
leg-1 | DESP-0001 | 1500.00 | APPROVED | APPROVED
leg-2 | DESP-0002 | 2500.00 | REJECTED | REJECTED
leg-3 | DESP-0003 |  900.00 | —        | PENDING
leg-4 | DESP-0004 |  100.00 | APPROVED | APPROVED
```

Migradas al motor, **sin inventar política** (AC-22):

```
leg-1 | APPROVED  | LEGACY_UNVERSIONED | 1500.00
leg-2 | REJECTED  | LEGACY_UNVERSIONED | 2500.00
leg-3 | CANCELLED | LEGACY_UNVERSIONED |  900.00
```

`leg-3` estaba `PENDING`: sin motor no puede resolverse, así que se cierra como
`CANCELLED` y su origen queda en el snapshot. `leg-4` no se migra porque su
empresa no existe y la tabla nueva sí tiene FK — se conserva íntegra en la legada.

## Colisión `regulatory.approval_requests` (FR-045-073)

| Comprobación | Resultado |
|---|---|
| Nombre nuevo correcto | ✔ `regulatory_approval_requests` |
| Datos conservados | ✔ 4 = 4 |
| PK conservada | ✔ renombrada a `pk_regulatory_approval_requests` |
| Índices correctos | ✔ `ix_regulatory_approval_requests_company_id` |
| ORM actualizado | ✔ clase `RegulatoryApprovalRequest` |
| Consultas y servicios actualizados | ✔ `regulatory/{models,service,api}.py` |
| Pruebas actualizadas | ✔ `test_regulatory.py` verde en ambos motores |
| Duplicidad accidental | ✔ ninguna |
| Shadow table | ✔ ninguna |

Índices tras la migración, sin colisión:

```
pk_approval_requests                       (motor)
pk_regulatory_approval_requests            (legada)
ix_approval_requests_{company_id,document_id,document_type,fingerprint,idempotency_key,process_type}
ix_regulatory_approval_requests_company_id
uq_approval_requests_open_document         (índice parcial de idempotencia)
```

## Idempotencia de `0016`

`test_approvals_data_migration_is_idempotent`: dos ejecuciones no duplican el
histórico ni los permisos, y la fila con referencia colgante **no se migra pero
tampoco se pierde**.
