# CNT-08 · Cierre (2026-11-15)

- **Entrada:** `14f1341`, cabeza `0118_gov_cnt02_modificaciones`.
- **Salida:** cabeza `0120_gov_cnt08_expediente` (una sola), reencadenada sobre `0119_gov_cnt03_ejecucion` de CNT-03, que publicó P1.
- **Paralelo:** P1 construyó CNT-03 y P2 construyó CNT-08. Sin solape funcional: CNT-08 solo lee CNT-03.

## Qué se entregó

- **Expediente contractual de solo lectura** (`/gobierno/contratos/:id/expediente`), solo para contratos formalizados:
  - 14 secciones;
  - proyección de PROC-03/06/08/10, BUD-06/08, CNT-01/02/03/04, DOC-02/08 y CTL-02, sin duplicar datos ni blobs.
- **Lista global** en Gobierno · Contratos › **Expedientes contractuales**: filtros, vigencia y paginación acotada.
- **Cronología única** con fecha jurídica, de registro, del documento y efectiva separadas. Incluye los hechos de ejecución de CNT-03.
- **Integridad por documento:** VERIFIED, MISSING, MISMATCH o NOT_APPLICABLE, comprobada contra los bytes almacenados.
- **Paquete exportable** (ZIP determinista con manifest.json, expediente.json, cronologia.csv, indice.csv, referencias.json, LEEME.txt, SHA256SUMS y los documentos autorizados):
  - inmutable y registrado;
  - verificable como VALIDO, INVALIDO o INCOMPLETO;
  - generado con un snapshot REPEATABLE READ;
  - responde 404 a otra empresa.
- **D08-09 (decisión de la dueña):** el sello documental se respeta. Un instrumento sellado no se descarga y queda EXCLUIDO con motivo SELLADO, aunque su huella sigue siendo verificable.

## Evidencia

| Puerta | Resultado |
|---|---|
| PG dirigida CNT-08 | 11/11 |
| Mutaciones | 6/6 muertas (M1–M6) |
| PG completa sobre el árbol final convergido (`eba13d5d`) | 5658 pruebas: 5636 pasan, 18 se saltan y 4 fallan. Las 4 son de la línea base: `n10` por `import_*.created_by`, `naive_datetime` y `spec019` ×2. **NEW_BACKEND_FAILURES=0** |
| Alembic (ida, vuelta a 0119 e ida) | OK; `heads` = `0120_gov_cnt08_expediente` |
| Vitest completo | 200 ficheros, 2124/2124 |
| typecheck, lint y build | OK |
| E2E final (expediente, contratos con CNT-03/04, modificaciones y catálogo de auditoría) | 8 pasan y 1 falla: AUDIT-E2E-05, preexistente (abajo). Recorrido del sponsor a 1280/390/320 y Axe sin «serious» nuevos |
| Catálogo de auditoría | 578 (+4: paquete GENERATED, DOWNLOADED, VERIFIED y VERIFICATION_FAILED) |

## Deudas no absorbidas

- **OBS-E2E-COLAPSAR-320-01** (nueva, OPEN_PREEXISTING):
  - desde `12d7980a` (2026-11-09, anterior a la entrada) el menú a 320 px es un cajón sin el botón «Colapsar menú»;
  - `audit-catalog`, `delegation-ceiling`, `strict-api-input` y `ui-company-scope` lo siguen buscando;
  - no lo causa CNT-08, que solo añade una entrada al menú.
- **OBS-DOC-SELLO-ENTREGA-01:** la autoridad documental confunde el sello de inmutabilidad (CNT-01/02) con el de confidencialidad (PROC-06).
- **OBS-CNT01-DOC-SELLADO-01:** «Ver documento» de la ficha de CNT-01 responde 404 en un instrumento sellado.
- **Heredadas:**
  - OQ-CNT02-01/02/03, OBS-CNT02-LIBERACION-01 y OBS-CNT01D-01/02;
  - OBS-VITEST-ASYNCBUTTON-FLAKY: no reapareció; Vitest completo en verde sin carga;
  - OBS_PROC08_PARCIAL_01 y OQ_OMA_02;
  - REQ01_BLOCKED_N37, CNT06_BLOCKED_N38, BUD09_BLOCKED_N36 y TRE04_BLOCKED_N37.

## DeepSeek

Ver `ATTEMPT_LOG.md`: 22 llamadas (`deepseek-v4-pro`), 12 reintentos semánticos y un coste de $0,155096. La dueña amplió el tope cinco veces (OWNER_EXCEPTION_USED=5). Claude no escribió producto, pruebas, E2E ni migración, salvo las tres correcciones documentadas.

## Estado

- **Producto:** OWNER_UAT_READY, conciliado con CNT-03.
- **Pendiente:** OWNER_ACCEPTED=NO. La UAT remota está BLOCKED_BY_INFRASTRUCTURE.
