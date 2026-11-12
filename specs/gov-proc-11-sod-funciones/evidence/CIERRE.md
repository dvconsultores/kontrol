# CIERRE · PROC-11 «Funciones incompatibles en contratación» (GOV-PROC-017)

```
PRODUCT_STATUS=OWNER_UAT_READY  OWNER_UAT_ACCESSIBLE=YES  OWNER_ACCEPTED=NO
MENÚ=Gobierno · Contrataciones › Funciones incompatibles (+ bloque en la ficha del expediente)
MIGRACIÓN=1 (0103_gov_proc11_sod_funciones; cabeza única)
CAPACIDAD=gobierno_sod:view / manage / activate (ya existente de CTL-01; sin capacidad nueva)
CATÁLOGO DE AUDITORÍA=487 -> 492 (5 acciones de PROC-11; versión 2026-11-12.1)
GOBIERNO=279/1275 compuertas · 27/122 OWNER_UAT_READY · 0 OWNER_ACCEPTED
```

## Selección

Se reconstruyó la matriz desde el CSV canónico antes de elegir: **269/1275 compuertas**, **26/122 `OWNER_UAT_READY`**,
0 aceptados. La matriz de candidatos se hizo con las columnas que pide el mandato y el resultado fue:

- **Ningún P0 quedaba elegible salvo PROC-11.** Todos los demás P0 dependen de una decisión material (D-GOV-02 en
  presupuesto, D-GOV-03 en oferentes), de una fuente legal de clase C (N37, N36, N10), de un monto que no existe
  (OBS-PROC08-MONTO-01) o de un dominio que no está construido (contratos, pagos, contabilidad, almacén, bienes).
- **PROC-11** era el único P0 con todos sus requisitos, su fuente y sus dominios disponibles. La objeción registrada en
  REP-10 («le faltan 3 de los 5 roles») se verificó: la cadena del requisito tiene cinco funciones y en Gobierno existen
  cuatro con registros reales que las prueban. La quinta —`PAGADOR`— no existe porque el pago es GOV-TRE-004 (TRE-04).
  **No se simula**: el catálogo la publica como no disponible con su requisito habilitante y la matriz no la acepta, de
  modo que la compuerta se declara cumplida para lo que el producto puede ejercer hoy y la limitación queda visible en la
  pantalla, en la tarjeta de UAT y en las matrices.
- Descartadas por regla: OBS-PROC08-TZ-01 (mantenimiento, §7), REP-09 (duplica CTL-05), CNT-01 (monto y fuente
  presupuestaria), PROC-09 (BLOCKED se mantiene), BUD (D-GOV-02).

## Requisitos, autoridad y decisiones

- Requisito **GOV-PROC-017** (P0, N20/N23), IR §7.4, y el criterio **E2E-07 Hostil SoD** (IR §13).
- N20 y N23 exigen segregar y prevenir el conflicto de interés; **no fijan pares**. La matriz es institucional y la
  declara Control Interno, con el mismo criterio ya fijado en CTL-01 (OD-CTL01-02/04).
- `MATERIAL_DECISION_REQUIRED=0`. Doce decisiones de diseño en `DECISIONES.md`.

## Constitution Gate

`CONSTITUTION_GATE=PASS` en las ocho compuertas (detalle en `plan.md`). Se reutilizan la capacidad y la política MFA de
CTL-01, la equivalencia de actor de ORG-06, la bitácora de CTL-02 y los registros del expediente; **no se duplica** ningún
motor existente.

## Producto

- **Matriz:** reglas `RF-000n` con dos funciones del procedimiento, riesgo, fundamento y vigencia. `BORRADOR → VIGENTE →
  CERRADA`; la vigente no se edita y la historia no se borra (triggers de PostgreSQL).
- **Detección:** por período y por expediente, con la evidencia de cada función (registro, fecha, cargo). Cuenta como
  mismo actor quien lo sea por ORG-06 (mismo funcionario, vínculos cerrados o revocados, delegaciones).
- **Bloqueo:** con la matriz en vigor, el backend impide que una persona asuma una función incompatible con otra que ya
  ejerce en el expediente; responde 409 `GOV_SOD_ROLE_CONFLICT` nombrando la regla, la función previa y su registro, y deja
  el intento en la bitácora como rechazo. Cubre solicitar, recibir, vincular la comisión, abrir, evaluar, recomendar y
  decidir.
- **Exportación:** CSV del período, auditado.
- **Pantalla:** «Funciones incompatibles» con la lista de funciones vigiladas (y la que no lo está), la matriz con sus
  acciones y el listado de conflictos; y un bloque con los conflictos del expediente en su ficha.

## Pruebas

| Comprobación | Resultado |
|---|---|
| Backend PROC-11 (PG): 12 pruebas | 12/12 |
| Guardas de reloj, catálogo de auditoría, fixtures y contratos de ruta | PASS |
| ruff | limpio |
| Vitest completo (Node 22) | 1953/1953 (175 ficheros; +11) |
| tsc, eslint, build | verde |
| Migración: fresh install → head, downgrade -1, upgrade | OK; `ALEMBIC_HEAD_COUNT=1` |
| E2E PROC-11 (`gobierno-sod-funciones`, pila canónica con ClamAV real) | 1/1 |
| E2E vecinas: CTL-01 (3), PROC-06 (1), PROC-07 (1), PROC-08 (1) | 6/6 |

## Baseline y fallos nuevos

Se comparó contra un worktree del HEAD de entrada (`bedcc63`) con el mismo comando, Node, base y entorno. El conjunto de
ficheros con rojas se ejecutó en los dos árboles y se restaron las listas:

| Concepto | Valor |
|---|---|
| `BASELINE_FAILURES` (mismo conjunto de ficheros, HEAD de entrada `bedcc63`) | 75 |
| `FINAL_FAILURES` (suite completa PG, árbol final) | 77 |
| `NEW_BACKEND_FAILURES` | **0** |
| `NEW_FRONTEND_FAILURES` | **0** (1953/1953) |
| `NEW_E2E_FAILURES` | **0** (7/7) |

Dos rojas **sí** eran mías y se corrigieron en el ciclo:

- `test_iso_guardas::test_iso_g03_toda_ruta_sin_empresa_esta_clasificada` y
  `test_n10_convergence::test_ninguna_operacion_de_la_api_queda_sin_alcance`: el catálogo `GET /gobierno/sod/funciones`
  no declaraba empresa. Ahora exige `CompanyContext` como el resto de las lecturas de Gobierno.
- `test_migraciones_url_porcentaje`, `test_spec018_migration_timestamps` y `test_installation_key_reference` fijaban la
  cabeza `0102_gov_ctl09_actas`; se actualizaron a la cabeza real, como se hizo en su día con cada migración publicada.

Rojas preexistentes que **no** son de este ciclo (idénticas en el árbol de entrada en este entorno): copia y restauración
(`pg_dump` no está en el PATH), documentos (`test_documents*`), `spec019_receipt`, `n9_integrity`, y la deriva ORM↔base de
las tablas `import_*` que arrastra Empresarial. Los errores de creación de base de datos eran del entorno de prueba (rol sin
`CREATEDB`) y desaparecieron al concederlo; los dos que quedaron como *error* en lugar de *fallo* en una migración pasan
aislados y son de orden, no de código.

## Observaciones abiertas

- **OBS-PROC11-PAGADOR-01 (MEDIUM):** la función `PAGADOR` del requisito no se puede vigilar hasta que exista TRE-04. La
  matriz es de datos: se incorporará sin rediseño.
- **OBS-PROC11-RECEPTOR-01 (LOW):** `RECEPTOR` se refiere a la recepción de ofertas (PROC-06). La recepción física de
  bienes es WH-01 y no está construida.
- **OBS-PROC11-HISTORICO-01 (LOW):** el bloqueo impide conflictos nuevos; los anteriores a la regla se listan con su
  evidencia y no se corrigen de oficio.
- Se mantienen: `PROC09_STATUS=BLOCKED`, `OBS-PROC08-MONTO-01`, `OBS-PROC08-PARCIAL-01`, `OBS-CTL09-PLAZOS-01`,
  `OBS-CTL09-A11Y-01`, `OBS-REP10-HALLAZGOS-01`. **OBS-PROC08-TZ-01 = CLOSED_TEST_INFRA** (ver
  `OBS_PROC08_TZ_01_PREFLIGHT.md`).
- **OBS-MATRIZ-UAT-01 (nueva, LOW):** el catálogo de UAT no listaba las tarjetas de PROC-06/07/08/10 aunque la matriz ya
  las cuenta; se dejó constancia en su cabecera. No afecta al producto.

## Suite completa

Una sola corrida de la suite completa de PostgreSQL sobre el árbol final, con el rol de prueba habilitado para crear
bases y sin procesos concurrentes: **77 rojas**. De ellas, **75 son exactamente las del árbol de entrada** en este
entorno; las dos restantes se comprobaron una a una en el worktree de `bedcc63`:

- `test_gobierno_integridad_runner::test_ejecutar_controles_sin_errores_contra_esquema_real`: falla igual en `bedcc63`,
  con el mismo mensaje (`assert -5 >= 0`).
- `test_backup_create_pg::test_bcp09_pg_dump_falla` y `test_spec052_migration_0033_legacy::test_una_instalacion_limpia_…`
  son de orden: la primera falla igual en `bedcc63` por la ausencia de `pg_dump`, la segunda pasa aislada y el árbol de
  entrada produjo un error de la misma familia en otra prueba de migración.

Las 75 se agrupan así, todas ambientales o preexistentes:

| Grupo | Nº | Causa |
|---|---|---|
| `test_backup_create_pg`, `test_backup_restore_pg` | 31 | `pg_dump`/`pg_restore` no están en el PATH de esta máquina |
| `test_documents`, `test_documents_security` | 35 | el flujo documental se ejecuta en `bedcc63` con las mismas 35 rojas: es el entorno de esa suite |
| `test_spec019_receipt`, `test_n9_integrity`, `test_pg_harness_lifecycle`, `test_naive_datetime_input`, `test_imagen_backend_mime`, `test_document_upload_connection_boundary` | 8 | línea base conocida del proyecto en este entorno |
| `test_n10_convergence` (deriva ORM↔base de `import_*`) | 1 | preexistente de Empresarial, idéntica en `bedcc63` |
| `test_gobierno_integridad_runner` | 1 | un control devuelve −5; idéntico en `bedcc63` |
| `test_spec052_migration_0033_legacy` | 1 | error de orden al crear bases en lote; pasa aislada |

- **OBS-MATRIZ-UAT-01 (nueva, LOW):** el catálogo de UAT no listaba las tarjetas de PROC-06/07/08/10 aunque la matriz ya
  las cuenta; se dejó constancia en su cabecera. No afecta al producto.

## Suite completa

Una sola corrida de la suite completa de PostgreSQL sobre el árbol final, con el rol de prueba habilitado para crear
bases y sin procesos concurrentes: **77 rojas**. De ellas, **75 son exactamente las del árbol de entrada** en este
entorno; las dos restantes se comprobaron una a una en el worktree de `bedcc63`:

- `test_gobierno_integridad_runner::test_ejecutar_controles_sin_errores_contra_esquema_real`: falla igual en `bedcc63`,
  con el mismo mensaje (`assert -5 >= 0`).
- `test_backup_create_pg::test_bcp09_pg_dump_falla` y `test_spec052_migration_0033_legacy::test_una_instalacion_limpia_…`
  son de orden: la primera falla igual en `bedcc63` por la ausencia de `pg_dump`, la segunda pasa aislada y el árbol de
  entrada produjo un error de la misma familia en otra prueba de migración.

Las 75 se agrupan así, todas ambientales o preexistentes:

| Grupo | Nº | Causa |
|---|---|---|
| `test_backup_create_pg`, `test_backup_restore_pg` | 30 | `pg_dump`/`pg_restore` no están en el PATH de esta máquina |
| `test_documents`, `test_documents_security` | 35 | el flujo documental se ejecuta en `bedcc63` con las mismas 35 rojas: es el entorno de esa suite, no el producto de este ciclo |
| `test_spec019_receipt`, `test_n9_integrity`, `test_pg_harness_lifecycle`, `test_naive_datetime_input`, `test_imagen_backend_mime`, `test_n10_convergence` (deriva ORM↔base de `import_*`), `test_document_upload_connection_boundary` | 9 | línea base conocida del proyecto en este entorno |
| `test_gobierno_integridad_runner` | 1 | un control devuelve −5; idéntico en `bedcc63` |
