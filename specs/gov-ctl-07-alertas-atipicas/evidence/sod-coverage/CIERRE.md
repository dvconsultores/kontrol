# GOV-SOD-COVERAGE-01 · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno · Control interno › «Alertas de operaciones atípicas»;
  - Gobierno · Control interno › «Reporte de control interno».
- **WHAT_CAN_USER_DO:**
  - ver como alerta «Segregación de funciones» todo intento bloqueado por SoD, venga de donde venga: CTL-01 (acciones incompatibles), PROC-11 (funciones incompatibles) y BUD-08 (quien certifica no compromete);
  - revisar esas alertas con la misma clave estable de siempre;
  - ver en REP-10 el total de los tres productores, agrupado por regla, proceso y tipo de conflicto, y exportarlo a CSV.
- **OWNER_UAT_READY:** YES. Los dos procesos ya lo eran. Este ciclo corrige el defecto P0 sin cambiar su clasificación.
- **PRODUCT_STATUS:** OWNER_UAT_READY · CURRENT_PRODUCT_DEFECT=NO en CTL-07 y en REP-10.
- **MISSING_GATES:** ninguno del ciclo. El refactor de hardcode sigue pendiente (REFACTOR_HARDCODED_POLICY, FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING).

## Cambio

- **Autoridad única nueva:** `app/modules/government/service_sod_eventos.py`.
  - Contiene el registro `PRODUCTORES` (acción → adaptador) y `ACCIONES_SOD`.
  - `consultar()` filtra por tenant, empresa y el intervalo `[inicio, fin)`.
  - `normalizar()` devuelve la proyección canónica.
  - Un productor nuevo solo necesita un registro.
- **Consumidores:**
  - `service_alertas` (CTL-07) y `service_reporte_control` (REP-10) consumen la autoridad;
  - ninguno de los dos nombra ya acciones SoD.
- **Pantalla REP-10:** `regla_codigo` puede ser `null`, y hay una columna nueva «Tipo de conflicto».
- **Lo que no cambia:**
  - CTL-07 conserva la clave `AUTOAPROBACION:<audit_event_id>` y el aviso;
  - no hay migración ni cambio de esquema;
  - no se tocaron los productores.
- **Clasificación:** EVENT_TAXONOMY=PLATFORM_INVARIANT · RULE_CONFIGURATION=DOMAIN/TENANT POLICY.

## Evidencia

| Prueba | Resultado |
|---|---|
| PG nuevas `test_gov_sod_cobertura.py` | 11/11; incluye los productores reales de BUD-08 y PROC-11 |
| Mutaciones M1–M6 | 6/6 muertas (ver `ATTEMPT_LOG.md`) |
| PG dirigida sobre el árbol fusionado con BUD-09 | 148/148 |
| Vitest completo, árbol fusionado | 2357/2357 (212 ficheros) |
| typecheck · lint · build | OK |
| ruff | limpio |
| mypy | 157 de línea base; 0 en ficheros tocados |
| OpenAPI | idéntico antes y después |
| E2E sobre el árbol fusionado: SoD cobertura, BUD-08, BUD-09, CNT-04 plazo, CTL-07, REP-10, PROC-11 y CTL-01 ×3 | 10/10, RC=0, limpieza LIMPIA |
| Axe 0 serious/critical | 1280, 390 y 320 en SoD cobertura y en CNT-04 (CNT04_AXE_1280 PASS) |

### PG completa sobre el código final (6b32b8d2)

5732 passed, 18 skipped, 5 failed.

- **BASELINE_FAILURE (4):**
  - `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada`;
  - `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo`;
  - `test_spec019_receipt` ×2.
- **ENVIRONMENT_RESIDUE (1):**
  - La prueba es `test_gobierno_integridad_runner::test_ejecutar_controles_sin_errores_contra_esquema_real`: el control OC20 dio −5.
  - La causa fue el esquema huérfano `t_c82c9467127a`, que dejó la corrida interrumpida sobre c2f77903.
  - Tras borrar el esquema: 3/3, RC=0, sobre el mismo código.
- **NEW_FAILURE:** 0.
- **Medianoche:** la corrida fue de 10:27 a 13:30 −04 y no cruzó la medianoche.

**SHAs:**

- FINAL_CODE_CERTIFIED_SHA=6b32b8d2.
- FINAL_DOCUMENTATION_SHA es el commit que añade este documento.
- CODE_DIFF_BETWEEN_THEM=0: el commit de documentación solo toca `specs/`.

## Integración con P1 (BUD-09)

- Fusión ordinaria en 6b32b8d2, con una sola cabeza: `0123_gov_bud09_causado`.
- BUD-09 no crea eventos SoD nuevos. Sus acciones entran en el `CATALOGO_SOD` de CTL-01, emiten `GOV_SOD_CONFLICT_BLOCKED` y ya están cubiertas.
- La fusión no tocó los ficheros SoD del ciclo. P1_P2_FUNCTIONAL_OVERLAP=0.

## DeepSeek

- `deepseek-v4-pro`: 8 llamadas (el tope), 4 reintentos, 4 rechazos y 4 aceptaciones, $0,041698.
- OWNER_EXCEPTION_USED=0.

Claude diseñó, auditó, aplicó y certificó. DeepSeek escribió todo el código semántico y todas las pruebas.

## Auditoría de parametrización

- CTL-07 y REP-10 pasan de CURRENT_PRODUCT_DEFECT YES a NO.
- La clasificación sigue en REFACTOR_HARDCODED_POLICY.
- CURRENT_REAL_DEFECTS_OPEN pasa de 10 a 8.

## Deudas heredadas (se conservan)

- OBS-E2E-CNT01-REAUTH-300S-01
- OBS-PG-MIDNIGHT-CROSSING-01
- OBS-PG-MFA-REPLAY-FLAKY-01
- OBS-UAT-HUMO-CLAMAV-MARGEN-01

## Observación

La aserción del «Resumen» en la E2E de cobertura (un total de «1») es débil. El total exacto de los tres productores lo prueba la PG.
