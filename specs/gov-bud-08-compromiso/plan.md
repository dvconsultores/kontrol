# Plan · BUD-08

## Constitution gate

```text
GOV_BUD_012_CLEAR=1  BUD06_AUTHORITY_CLEAR=1  CERTIFICATE_CONSUMPTION_CLEAR=1  NO_DOUBLE_COUNT_FORMULA_CLEAR=1
COMMITMENT_IDENTITY_CLEAR=1  MULTILINE_DECISION_CLEAR=1  FUNCTIONAL_AUTHORITY_CLEAR=1  MONETARY_LIMIT_CLEAR=1
SUPPORT_AUTHORITY_CLEAR=1  ANNULMENT_RULE_CLEAR=1  CONCURRENCY_RULE_CLEAR=1  SOD_RULE_CLEAR=1
BENEFICIARY_MASTER_REQUIRED=0  BUD07_NOT_ABSORBED=1  BUD09_NOT_ABSORBED=1  BUD10_NOT_ABSORBED=1  BUD11_NOT_ABSORBED=1
MATERIAL_DECISION_REQUIRED=0  SHARED_CORE_CHANGE_REQUIRED=0  CONSTITUTION_GATE=PASS
```

## Decisiones de diseño (Claude)

| Id | Decisión |
|---|---|
| PDD-B08-01 | Cabecera más líneas. Una línea por CDP dentro de un compromiso (UNIQUE commitment_id + certificate_id). El total no se guarda como columna: se deriva de las líneas y queda en la instantánea hasheada. |
| PDD-B08-02 | `disponible_de_credito` y `_vigentes_por_credito` aplican la fórmula de tres términos. La tabla de disponibilidad de BUD-06 conserva «Certificado» (Σ CDP vigentes) y añade «Comprometido». Las certificaciones exponen consumido, remanente y situación. |
| PDD-B08-03 | Orden de bloqueo: ejercicio, luego CDP (ordenadas por id), luego créditos. Es el mismo orden que la anulación de la CDP, así que no hay interbloqueo. |
| PDD-B08-04 | La SoD es una guarda dura que reutiliza `usuarios_equivalentes` y `funcionarios_de_actor` de CTL-01. El intento bloqueado se audita con `record_audit_after_rollback`. |
| PDD-B08-05 | El soporte es un documento del ejercicio. Una vista de opciones lista CDP, autoridades y soportes, para que la pantalla no muestre UUID. |
| PDD-B08-06 | Expediente derivado de las CDP; el cuerpo no trae expediente. |
| PDD-B08-07 | Migración 0113 sobre 0112: crea las 2 tablas con triggers PG, siembra `commit` para FUNCIONAL_COMPLETO y amplía el CHECK de historia. |

## Ficheros

**Backend:**
- `models.py`;
- `alembic/versions/0113_gov_bud08_compromiso.py`;
- `setup/api.py`, `mfa_policy.py` y `audit_catalog_entries.py` (+3 entradas);
- `schemas_presupuesto_compromiso.py`, `api_presupuesto_compromiso.py`, `service_presupuesto_compromiso.py` y `main.py`;
- `service_presupuesto_certificacion.py`: fórmula, campos derivados y guarda de anulación;
- fijaciones: catálogo 536→539, cabeza 0113 en 3 ficheros, MFA 72→73, delegación 165→166;
- `tests/test_gov_bud08.py`.

**Frontend:**
- `api.ts`;
- `CompromisosEjercicio.tsx` (nuevo) y su prueba;
- `DisponibilidadEjercicio.tsx`: columnas nuevas;
- `EjercicioPresupuestarioPage.tsx`;
- E2E `gobierno-presupuesto-compromiso.spec.ts`.
