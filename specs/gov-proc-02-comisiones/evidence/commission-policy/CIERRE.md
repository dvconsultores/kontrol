# PROC-07/PROC-08-COMMISSION-POLICY · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno · Contrataciones › «Políticas de comisión» (nueva);
  - Gobierno · Contrataciones › «Comisiones» (selector de política, «Regla aplicada», «Designar presidente»);
  - Gobierno · Contrataciones › Expediente › «Evaluación» y «Decisión» (regla de la política y modo sin comisión).
- **WHAT_CAN_USER_DO:**
  - crear, editar, activar y cerrar políticas de comisión con versiones, y abrir una nueva versión de una vigente;
  - fijar en la política la composición (mínimo y máximo de principales, impar, suplentes, secretario, presidente), los requisitos de integración (área, cargo, unidad, competencia o funcionario), el quórum, la mayoría de decisión y su base, el voto y el voto dirimente del presidente, el acto requerido y los documentos por etapa;
  - elegir la base LCP art. 14 como piso legal versionado, que se puede endurecer pero no rebajar (OD-CP-03);
  - crear una comisión desde una política vigente, que congela la regla al activarse; las comisiones anteriores conservan su regla histórica (OD-CP-04);
  - designar presidente y registrar inhibiciones por expediente: el inhibido no cuenta y actúa su suplente;
  - abrir ofertas, evaluar y recomendar con el quórum y la mayoría de la política, o sin comisión mediante los responsables del expediente (OD-CP-02);
  - ver la historia inmutable de cada política y la auditoría de cada acción.
- **OWNER_UAT_READY:** YES. La tarjeta está en `OWNER_UAT_CARD.md`.
- **PRODUCT_STATUS:** OWNER_UAT_READY · CURRENT_PRODUCT_DEFECT=NO en PROC-07 y en PROC-08 (antes YES, P0). OWNER_ACCEPTED=NO: solo la dueña lo concede.
- **MISSING_GATES:** ninguno del ciclo.

## Cambio

- **Migración:** `0124_gov_commission_policy`, sin backfill.
  - 4 tablas de política: políticas, requisitos, documentos e historia (con disparadores de inmutabilidad en PG).
  - 2 tablas de responsables: de la apertura y de la recomendación sin comisión.
  - Columnas nuevas en comisiones, miembros, inhibiciones, aperturas, recomendaciones, aportes y resultados.
  - Permiso `gobierno_comisiones:configure`.
- **Autoridad única:** `service_comision_regla.py` (COMMISSION_POLICY_AUTHORITIES=1).
  - PROC-02, PROC-07 y PROC-08 la consumen; ninguno tiene ya una lista privada de reglas.
  - El frontend ya no calcula el quórum: lo muestra desde la regla del backend.
- **SoD:** sin cambios. CTL-01 y PROC-11 siguen siendo la única autoridad.
- **Clasificación de reglas:** PLATFORM_INVARIANT, LEGAL_MANDATORY, INSTITUTIONAL_POLICY y OPERATIONAL_CONFIGURATION, en el delta (`spec002-commission-policy-delta.md`).
- **Auditoría de hardcode:** `HARDCODE_AUDIT.md`. ZERO_INSTITUTIONAL_HARDCODE=1, TENANT_CONFIGURABLE=1, NATIONAL_REUSABLE_PRODUCT=1, NAGUANAGUA_SPECIFIC_CODE=0, TENANT_SPECIFIC_CODE=0.

## Evidencia

| Prueba | Resultado |
|---|---|
| PG de políticas y autoridad (`test_gov_comision_politica.py`) | 14/14 |
| PG de integración con PROC-07 y PROC-08 (`test_gov_comision_politica_procesos.py`) | 9/9 |
| PG de PROC-02 más las dos anteriores, tras las mutaciones | 32/32 |
| PG dirigida | 387 pasadas, RC=0 |
| Mutaciones M1–M8 | 8/8 muertas (ver `ATTEMPT_LOG.md`) |
| Vitest completo | 2383/2383 (215 ficheros) |
| typecheck · lint · build | OK |
| ruff | limpio |
| mypy | 157 de línea base; 0 en ficheros tocados |
| OpenAPI | Solo cambios del alcance: rutas de políticas y esquemas de comisión, evaluación y decisión |
| Cabezas de Alembic | Una sola: `0124_gov_commission_policy`. Upgrade, downgrade y upgrade en una base nueva |
| E2E CP-E2E-01 (real, sin mocks) | 1/1; Axe 0 serious/critical en 1280, 390 y 320 |
| E2E de regresión: comisiones, evaluación, decisión, expedientes, garantías, monto de la oferta, contratos y SoD | 14/14 |

### PG completa

Corrida de 21:57 a 00:55 −04 sobre 9a18d5a5 más los cambios del ciclo: 5746 passed, 18 skipped, 16 failed.

- **NEW_FAILURE (12), todos constantes declaradas a propósito que la migración, el catálogo y el permiso nuevos debían actualizar:**
  - cabeza de Alembic `0123` → `0124`: `test_installation_key_reference` (1), `test_migraciones_url_porcentaje` (8) y `test_spec018_migration_timestamps` (1);
  - catálogo de auditoría 593 → 599 (6 eventos nuevos): `test_audit_catalog_backup::test_catb_03_catalog_size`;
  - catálogo de permisos 177 → 178 (`gobierno_comisiones:configure`): `test_delegation_ceiling::test_dc_t01_catalogo_y_admin_inicial`.
  - Tras actualizar las constantes, los 12 pasan (corrida de 00:56).
- **BASELINE_FAILURE (4)**, los mismos que constan en el cierre de BUD-09 (`specs/gov-bud-09-causado/evidence/CIERRE.md`) y en el de SoD:
  - `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada` (`import_*.created_by`);
  - `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo`: el campo `abierta_en` de las aperturas de PROC-07, idéntico en HEAD (el ciclo no lo tocó);
  - `test_spec019_receipt` ×2 (RECEIPT_EMPTY, 409).
- **ENVIRONMENT_FAILURE:** 0. Antes de la corrida no había esquemas `t_*` huérfanos.
- **Medianoche:** la corrida la cruzó. Los 4 de línea base ya fallaban en corridas diurnas anteriores, y los 16 se repitieron después de medianoche con el mismo resultado. Ninguno se atribuye a la fecha.

## Integración con P1

`git fetch` a las 01:00 −04: `origin/develop` seguía en 9a18d5a5. No hubo nada que fusionar (P1_P2_FUNCTIONAL_OVERLAP=0).

## SHAs

- FINAL_CODE_CERTIFIED_SHA=dd1021ca.
- FINAL_DOCUMENTATION_SHA es el commit que añade este documento.
- CODE_DIFF_BETWEEN_THEM=0: el commit de documentación solo toca `specs/`.

## DeepSeek

- `deepseek-v4-pro`: 30 llamadas de un tope de 31, 18 reintentos y $0,264675.
- El tope era 18 (OD-CP-01); la dueña lo amplió a 26 y a 31 (OWNER_EXCEPTION ×2).
- El detalle de cada llamada y todo el trabajo de Claude, declarado, están en `ATTEMPT_LOG.md`.

## Auditoría de parametrización

- PROC-07 y PROC-08 pasan de CURRENT_PRODUCT_DEFECT YES a NO, y de P0 a P1.
- Recuento: P0=4, P1=28 y CURRENT_PRODUCT_DEFECTS=6.
- FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING.

## Deudas

**Nuevas:**

- OBS-PROC02-SELF-ACTIVATION-CTL01-01: el control «quien registró la comisión no puede activarla» sigue en el servicio y no pasa por CTL-01.
- OBS-CP-REGLA-VISIBLE-SOLO-EN-FORMULARIOS-01: en el expediente, la regla se ve solo dentro de los formularios de apertura y recomendación.

**Heredadas (se conservan):**

- OBS-E2E-CNT01-REAUTH-300S-01
- OBS-PG-MIDNIGHT-CROSSING-01
- OBS-PG-MFA-REPLAY-FLAKY-01
- OBS-UAT-HUMO-CLAMAV-MARGEN-01
