# Cierre · BUD-02-CLASSIFIER-PARENT-LEVEL (2026-11-20)

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:** Gobierno › Presupuesto › Ejercicios presupuestarios › el ejercicio › «Clasificador registrado por el ente» (Nueva partida e Importar partidas (CSV)).
- **WHAT_CAN_USER_DO:**
  - Cargar el clasificador del ejercicio, a mano o por CSV, con la seguridad de que cada partida cuelga de una del nivel inmediatamente anterior.
  - Si el padre es de otro nivel o no está en ese clasificador, la pantalla dice cuál es el nivel encontrado y cuál el esperado, bajo «Código superior» o con «Fila N» en el CSV.
- **HOW_IS_PARENT_LEVEL_VALIDATED:**
  - La regla única `service_presupuesto.validar_padre_partida` exige que, para el nivel N, el padre tenga nivel N-1, el mismo tipo y esté en el mismo clasificador.
  - El mapa `(tipo, codigo) → nivel` sale del clasificador del ejercicio.
  - No se deduce nada del prefijo del código.
- **HOW_IS_ROOT_LEVEL_HANDLED:** `NIVEL_RAIZ_PARTIDA = 1`, por BUD12-06 y por el CHECK `nivel BETWEEN 1 AND 12`. La raíz no admite padre; los demás niveles lo exigen.
- **HOW_ARE_CLASSIFIER_VERSIONS_ISOLATED:**
  - Hay un clasificador por ejercicio (`year_id` UNIQUE) y por empresa, y el mapa de niveles solo carga ese clasificador.
  - Un padre de otro ejercicio, de una versión aprobada o de otra empresa no existe para la regla.
  - Las versiones aprobadas no se reescriben y siguen legibles (j04).
- **HOW_IS_CSV_VALIDATED:**
  - Cada fila pasa por la misma regla.
  - El padre puede estar en la base o en una fila anterior del mismo lote, que es el contrato vigente.
  - Una hija antes que su padre se rechaza.
- **HOW_IS_IMPORT_ATOMICITY_PRESERVED:** si una fila falla, se devuelve 422 con todas las filas en error y no se escribe ninguna. Lo prueba j07 y lo protege la mutación M8.
- **HOW_ARE_CONSUMERS_PROTECTED:**
  - Ningún consumidor cambia: BUD-03/04/05/06/08/09, CNT-01/03 y TRE-03/04/05/09 leen las partidas por id.
  - Su regresión pasa: PG dirigida 352/352 sobre el árbol fusionado y E2E del presupuesto en verde.
- **OWNER_UAT_READY:** YES (`OWNER_UAT_CARD.md`, partes A–F).
- **ACCESSIBLE:** YES. Axe a 1280, 390 y 320 sin violaciones serias, tras corregir la lista de errores del CSV (`<div role="alert"><ul>`).
- **PRODUCT_STATUS:** FUNCTIONAL_PRODUCT. Falta `OWNER_ACCEPTED`, que solo puede conceder la dueña.
- **MISSING_GATES:** la UAT de la dueña.

## Evidencia

| Puerta | Resultado |
|---|---|
| Defecto reproducido antes del cambio | Con `service_presupuesto.py` de b726c1da: alta de nivel 3 con padre de nivel 1 → 201; CSV con salto de nivel → 200. Suite del ciclo: 7 fallidas. Después: 9/9 |
| Mutaciones | 8 de 8 muertas (M1–M8), todas por la aserción del padre |
| PG dirigida (árbol del ciclo) | 304/304 |
| PG dirigida (árbol fusionado con TRE-05) | 352/352 |
| PG completa (árbol del ciclo) | 5905 pasadas, 18 omitidas y 5 fallidas, ninguna nueva (ver la tabla siguiente) |
| E2E (árbol del ciclo) | Jerarquía y presupuesto: 7/7 |
| E2E (árbol fusionado) | 10/10: jerarquía, BUD-01/02, aprobado, bitácora de procesos y retenciones; limpieza LIMPIA |
| Humo UAT | 1/1 (antes y después de la fusión) |
| Vitest | 2537/2537 en el árbol del ciclo y 2567/2567 en el fusionado |
| typecheck, lint y build | 0 |
| ruff | limpio |
| mypy | 157 de línea base y 0 en los ficheros tocados |
| OpenAPI | Idéntico a `origin/develop` (932 rutas): OPENAPI_UNEXPECTED_DIFF=0 |
| Migración | Ninguna. Cabeza única tras la fusión: 0129_gov_tre05_retencion (de P1) |

### Clasificación de la PG completa (reproducida)

| Prueba | Aislada en el árbol del ciclo | Aislada en HEAD b726c1da | Clase |
|---|---|---|---|
| `test_iso_barridos::test_barrido_cabecera_manipulada` | PASA | — | TIME_WINDOW_BASELINE |
| `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada` | FALLA | FALLA | BASELINE_FAILURE |
| `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo` | FALLA | FALLA | BASELINE_FAILURE |
| `test_spec019_receipt` ×2 | FALLA | FALLA | BASELINE_FAILURE |

NEW_FAILURE=0 · ENVIRONMENT_FAILURE=0.

## Integración con P1

- **P1_ADVANCED_SINCE_ENTRY:** YES, 10 commits:
  - TRE-05 (retenciones y comprobantes, migración 0129);
  - pin del MCP 2.4.0;
  - rebaseline empresarial de P3.
- **P1_MERGED:** YES, fusión ordinaria y sin conflictos.
- **P1_P2_FUNCTIONAL_OVERLAP:** NONE.
  - Solo comparten `OWNER_UAT_READY_CATALOG.md`, que se fusionó solo.
  - La rebaseline de P3 es empresarial y no registra defectos de Gobierno.

## DeepSeek

- 2 llamadas de un tope de 6: T03 y su reintento 1.
- 3963 tokens de entrada y 2370 de salida; coste $0,003565.
- El reintento se debió a un error del contrato de Claude.
- Claude implementó T01, T02, T04 y T05. El detalle está en `ATTEMPT_LOG.md`.

## Roadmap

- BUD-02: defecto de SÍ a NO; prioridad de P1 a NONE (KEEP sin defecto).
- Auditoría: P0=2, P1=27, P2=9 y NONE=6.
- CURRENT_PRODUCT_DEFECTS pasa de 1 a 0.
- Cero defectos conocidos en la auditoría de parametrización no es producto completo. Siguen pendientes:
  - los refactors P0 (BUD-01, BUD-05) y P1;
  - las brechas normativas;
  - las integraciones externas;
  - la aceptación de la dueña.

## Commits

- Código: 2a1b857c.
- Documentación: e8f87bbb.
- Entrada: b726c1da.
