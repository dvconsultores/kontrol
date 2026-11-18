# ORG-04-AUTHORITY-ASSIGNMENT-POLICY · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno › «Políticas de asignación» (nueva): lista, ficha, formulario, nueva versión, activar y cerrar;
  - Gobierno › «Ocupación de cargos» › Asignaciones › «Nueva asignación» (sección «Regla aplicada» y autorización condicional);
  - Gobierno › «Ocupación de cargos» › Asignación (ficha con «Regla aplicada», documentos y «Avocar» solo si se admite).
- **WHAT_CAN_USER_DO:**
  - crear, editar, activar y cerrar políticas por figura (delegación de atribuciones y de firma, suplencia, encargaduría, designación y comisión de servicio), con versiones e historia inmutable;
  - fijar en la política el máximo de días, el fin obligatorio, el medio de eficacia del acto, el emisor (cualquiera, un cargo o una competencia), la autorización especial (nombre, ámbito y umbral de días), las competencias permitidas, la prohibición de avocación y los documentos exigidos al activar o revocar;
  - ver los pisos legales del régimen del ente: LOAP y LEFP en todo nivel, LOPPM art. 87 solo si el ente es MUNICIPAL (OD-AP-02). La política solo endurece;
  - registrar asignaciones con la regla aplicada a la vista; la autorización especial solo se pide cuando la regla la exige (defecto P0 corregido);
  - activar la asignación, que congela la regla; las asignaciones anteriores conservan su regla histórica, sin backfill (OD-AP-03);
  - revocar, finalizar y avocar según la regla congelada, con la auditoría de cada acción.
- **OWNER_UAT_READY:** YES. La tarjeta está en `OWNER_UAT_CARD.md`.
- **PRODUCT_STATUS:** OWNER_UAT_READY · CURRENT_PRODUCT_DEFECT=NO en ORG-04 (antes YES, P0). OWNER_ACCEPTED=NO: solo la dueña lo concede.
- **MISSING_GATES:** ninguno del ciclo.

## Cambio

- **Migración:** `0126_gov_assignment_policy` (sobre `0125_gov_tre03_orden_pago` de P1), sin backfill.
  - 4 tablas: políticas, competencias permitidas, documentos por etapa e historia (inmutable en PG).
  - En `gov_assignments`: `autorizacion_concejo` pasa a `autorizacion_especial`, y se añaden `policy_id`, `policy_version` y `regla` (JSON), protegidas por el disparador fuera de BORRADOR.
  - Permiso `gobierno_ocupacion:configure`; `GovernmentAssignment` pasa a ser ResourceKind documental.
  - La migración se escribió como 0125 y se renumeró al fusionar P1, que había tomado la 0125 con TRE-03.
- **Autoridad única:** `service_asignacion_regla.py` (ASSIGNMENT_POLICY_AUTHORITIES=1). Crear, editar, activar, revocar, avocar, el detalle y la nueva ruta `GET /gobierno/ocupacion/regla` la consumen; el catálogo de figuras ya no lleva `base_legal` ni `exige_gaceta`.
- **Frontend:** la etiqueta de la autorización, los fundamentos y los límites salen de la regla del backend; no queda «Autorización del Concejo» en el código del frontend.
- **SoD:** sin cambios. CTL-01 sigue siendo la única autoridad.
- **Clasificación de reglas:** en el delta (`spec004-assignment-policy-delta.md`) y en `HARDCODE_AUDIT.md`. ZERO_INSTITUTIONAL_HARDCODE=1, TENANT_CONFIGURABLE=1, NATIONAL_REUSABLE_PRODUCT=1, NAGUANAGUA_SPECIFIC_CODE=0, TENANT_SPECIFIC_CODE=0.

## Evidencia

| Prueba | Resultado |
|---|---|
| PG de políticas y autoridad (`test_gov_org04_politica.py`) más procesos y P0 (`test_gov_org04_politica_procesos.py`) | 20/20 |
| PG de ORG-04 existentes | 62/62 |
| Mutaciones M1–M9 | 9/9 muertas (ver `ATTEMPT_LOG.md`) |
| P0 reproducido | La prueba Vitest del P0 falla contra `NuevaAsignacionPage.tsx` de a51816b3 y pasa con el nuevo |
| PG dirigida sobre el árbol fusionado (ORG-04, N9, TRE-03, n10, integridad y contrato de auditoría) | 209 pasadas; solo falla n10 (línea base) |
| Constantes sobre el árbol fusionado (cabeza, catálogo, permisos, MFA y ResourceKinds) | RC=0 |
| Cabezas de Alembic | Una sola: `0126_gov_assignment_policy`. Upgrade, downgrade a 0125 y upgrade en una base nueva, RC=0 |
| Vitest completo (árbol fusionado) | 2472/2472 (223 ficheros) |
| typecheck · lint · build (árbol fusionado) | OK |
| ruff | limpio |
| mypy | 157 de línea base; 0 en ficheros del ciclo |
| OpenAPI | Solo cambios del alcance: 8 rutas y 12 esquemas nuevos; cambian `AsignacionDetalle`, `AsignacionIn` y `FiguraOut`. Las fixtures regeneradas tras fusionar coinciden con la fusión |
| E2E OAP-E2E-01/02/03 (real, sin mocks) | Antes de fusionar: 3/3; Axe 0 serious/critical en 1280, 390 y 320 |
| E2E de regresión: los 7 specs que crean asignaciones | Antes de fusionar: 12/12 |
| E2E sobre el árbol fusionado: la nueva, las 7 de regresión y las 2 de órdenes de pago de TRE-03 | 16/17 con 4 workers; el único fallo es CNT-01 por REAUTH_REQUIRED (deuda heredada OBS-E2E-CNT01-REAUTH-300S-01), que pasa sola con 2 workers (1/1). Total 17/17 |

### PG completa

Corrida de 12:09 a 16:02 −04 sobre a51816b3 más los cambios del ciclo: 5763 pasadas, 18 omitidas, 8 fallidas y errores de arranque.

- **NEW_FAILURE:** 0.
- **BASELINE_FAILURE (4)**, los mismos del cierre de la política de comisión, ajenos al ciclo:
  - `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada` (`import_*.created_by`, 6 columnas; ninguna del ciclo);
  - `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo` (`abierta_en` de las aperturas de PROC-07);
  - `test_spec019_receipt` ×2.
  - Se repitieron por separado tras la corrida, con el mismo resultado.
- **ENVIRONMENT_FAILURE:** el resto.
  - Fallos: `test_gobierno_integridad_runner` (OC20 = −10), `test_pg_harness_lifecycle` (pglife_05), `test_spec047_notifications` y `test_spec047_scheduler`.
  - Errores de arranque: `UniqueViolation` en `pg_extension_name_index` (22 apariciones) y `could not find tuple for opclass` (2), entre otros en `test_audit_record_contract` y `test_documents_migration_0024`.
  - Causa: el catálogo de la base de QA `ktest` quedó dañado durante la corrida y dejó 2 esquemas `t_*` imposibles de soltar (`could not find tuple for opclass`). Esos esquemas son los que falsean OC20.
  - Reproducción: se recreó `ktest` con `qa/pg-provision.sh mkdb ktest`. Después, `test_gobierno_integridad_runner`, `test_pg_harness_lifecycle`, `test_spec047_*`, `test_audit_record_contract`, `test_documents_migration_0024`, `test_approvals` y `test_audit_integration` pasan.
  - Las cuentas de la línea de progreso incluyen la salida de los pytest anidados de `test_pg_harness_lifecycle`; por eso la lista FAILED aparece repetida.
- **Medianoche:** la corrida no la cruzó.

## Integración con P1

- `git fetch`: `origin/develop` avanzó de a51816b3 a 250227c9 con TRE-03 (órdenes de pago, migración 0125).
- Merge ordinario, sin rebase. Conflictos solo en 6 pruebas de constantes, resueltos sumando los dos ciclos:

  | Constante | P1 | Este ciclo | Fusionado |
  |---|---|---|---|
  | Catálogo de auditoría | 608 | 604 | 613 |
  | Permisos | 183 | 179 | 184 |
  | MFA sensibles / estándar | 83 / 83 | 80 / 82 | 83 / 84 |
  | Cabeza | 0125 | 0125 | 0126 |

- Fusión automática sin conflicto en `main.py`, `mfa_policy.py`, `setup/api.py`, `audit_catalog_entries.py`, `router.tsx`, `Sidebar.tsx`, `pantallas.ts` y las fixtures del frontend.
- Las pruebas afectadas se repitieron sobre el árbol fusionado (tabla de evidencia).
- P1_P2_FUNCTIONAL_OVERLAP=0: TRE-03 no toca la ocupación de cargos.

## SHAs

- Código del ciclo: 3c27ad6e. Fusión con P1: 298f7df6 = FINAL_CODE_CERTIFIED_SHA.
- FINAL_DOCUMENTATION_SHA es el commit que añade este documento.
- CODE_DIFF_BETWEEN_THEM=0: el commit de documentación solo toca `specs/` y `docs/roadmap/`.

## DeepSeek

- `deepseek-v4-pro`: 17 llamadas de un tope de 24 (OD-AP-04), 11 reintentos y $0,128947. OWNER_EXCEPTION_USED=0.
- El detalle de cada llamada, las reclasificaciones y todo el trabajo de Claude, declarado, están en `ATTEMPT_LOG.md`.

## Auditoría de parametrización

- ORG-04 pasa de CURRENT_PRODUCT_DEFECT YES a NO, y de P0 a P1.
- Recuento: P0=3 (BUD-01, BUD-05 y CTL-09), P1=29 y CURRENT_PRODUCT_DEFECTS=5.
- FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING.
- NEXT_CANDIDATE=CTL-09, el único P0 con defecto de producto vigente.

## Deudas

**Nuevas:**

- OBS-PG-KTEST-CATALOG-DAMAGE-01: durante la PG completa, el catálogo de `ktest` se dañó (`pg_extension_name_index`, `opclass`) y dejó esquemas `t_*` imposibles de soltar. Se arregla recreando `ktest`; falta averiguar la causa.
- OBS-AP-AUTORIZACION-REFERENCIA-UNICA-01: la autorización especial guarda una sola referencia de texto aunque la regla exija varias autorizaciones a la vez.

**Heredadas (se conservan):**

- OBS-PROC02-SELF-ACTIVATION-CTL01-01
- OBS-CP-REGLA-VISIBLE-SOLO-EN-FORMULARIOS-01
- OBS-E2E-CNT01-REAUTH-300S-01
- OBS-PG-MIDNIGHT-CROSSING-01
- OBS-PG-MFA-REPLAY-FLAKY-01
- OBS-UAT-HUMO-CLAMAV-MARGEN-01
