# Cierre · CNT-09 Alertas de vencimientos (GOV-CNT-010)

**Estado:** OWNER_UAT_READY. La aceptación (OWNER_ACCEPTED) queda pendiente de la dueña.

## Base y reconciliación

- Entrada: a017f8f.
- Durante el ciclo se integró con un merge ordinario el CNT-08 de P2 (1a8b8d7). Sin rebase ni force.
- Alembic: 0119 → 0120_gov_cnt08_expediente (P2) → 0121_gov_cnt09_alertas. Cabeza única: ALEMBIC_HEAD_COUNT=1.
- Ninguna migración publicada se modificó. La 0120 de CNT-09, que no estaba publicada, se renombró a 0121 y se reencadenó.
- Conflictos del merge resueltos de forma mecánica:
  - las fijaciones de cabeza;
  - el catálogo de auditoría (574 + 1 de CNT-09 + 4 de CNT-08 = 579);
  - el menú, con las dos entradas;
  - los imports de la ficha del contrato, con los dos;
  - las matrices, con la fila CNT-08 de P2 y la fila CNT-09 de P1.

## Alcance

- La alerta informa y no decide: ALERT ≠ DECISION. Ningún estado de negocio cambia.
- Se reutiliza el motor de la Spec 047 (`crear_alerta`, `resolver_alerta_de_sistema`, `/alerts`, registro del planificador). No se creó otro motor.
- Fuentes:
  - plazo efectivo del contrato (CNT-01 + CNT-02);
  - hitos y entregables de CNT-03 (manda la conformidad);
  - garantías de PROC-10 (`DIAS_POR_VENCER` importado).
- Ventanas: DUE_TODAY y OVERDUE por defecto. El preaviso solo se activa por política institucional. Calendario hábil: DEFERRED_BY_CALENDAR_AUTHORITY.
- Comportamiento:
  - deduplicación idempotente;
  - las alertas obsoletas se resuelven, nunca se borran;
  - una reaparición crea `:r<n>`;
  - seguro entre empresas.
- Fuera de alcance: decisiones, prórrogas, conformidades, pagos y calendario hábil.

## Verificación

| Comprobación | Resultado |
|---|---|
| PG completa, una sola vez, sobre el árbol final de P1 previo al merge (`qa/suite_tiempos.py --motor postgres --con-analizador`, run r20261116t013118p3258247nd4bf5a) | 5631 pasan / 6 fallan / 18 omitidas |
| Fallos nuevos frente a la línea base | **0** (ver nota) |
| PG dirigida tras el merge: CNT-08, CNT-09, CNT-01/02/03, PROC-10, Spec 047, catálogo, cabezas, integridad e ISO | 162 pasan / 0 fallan |
| Vitest (árbol fusionado) | 2135/2135 |
| tsc, eslint y build | 0 errores, build OK |
| ruff | limpio |
| mypy (ficheros CNT-09) | sin errores propios; el total sigue igual que la línea base |
| E2E gobierno-contratos (CNT-01 con el tramo CNT-09, 1280/390/320, Axe) y gobierno-contratos-modificaciones, árbol fusionado | 2/2, 0 reintentos |
| E2E gobierno-expediente-contractual (P2), árbol fusionado | 1/1 al repetirla sola (ver OBS) |

**Nota sobre la PG completa.** Cinco fallos ya estaban en la línea base:
- imb_07 pip check;
- n10 ORM↔base;
- guard_d01;
- 2 de spec019 receipt.

El sexto, `test_gobierno_integridad_runner` (control OC20, −5 violaciones), fue un residuo de entorno. Una regresión dirigida que el propio Claude interrumpió con `timeout` dejó en `ktest` el esquema huérfano `t_c64daf44def7`. Como OC20 cuenta los disparadores en `pg_trigger` sin filtrar por esquema, los vio duplicados. Se retiró el esquema tras comprobar que no tenía conexiones vivas, y la prueba pasó 3/3.

**OBS-CNT08-E2E-VALIDO-01 (para P2, baja).** En la corrida conjunta, `gobierno-expediente-contractual.spec.ts:254` falló una vez por modo estricto: `getByText("Válido")` alcanzó también la celda «Válido · —» de la tabla de exportaciones ya refrescada. La misma prueba pasó en origin/develop (1a8b8d7) y, repetida sola, en el árbol fusionado. Es un selector no exacto de la prueba de P2, ajeno a CNT-09. P1 no tocó el fichero.

## Métricas (recontadas sobre la matriz fusionada)

- Gates completos: 441 de 1268 aplicables. P1 aporta 10 y P2 (CNT-08) 11.
- OWNER_UAT_READY: 43 de 122 (35,25 %).
- OWNER_ACCEPTED: 0.

## DeepSeek

- 8 llamadas (deepseek-v4-pro), 38.460 tokens de entrada y 44.946 de salida, USD 0,0558. Dentro del tope de 8. OWNER_EXCEPTION_USED=0.
- Detalle en ATTEMPT_LOG.md.
- CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## UAT

- La pila de prueba de la dueña se levantó desde el SHA publicado 2d74eef, en el worktree `uat/wt-2d74eef`:
  - frontend: http://localhost:16873/;
  - backend: 19700;
  - autoridad central: 19710.
- Corrida r20261116t034909p1159781n5cd89f: «PILA UAT LISTA».
- Humo HUMO-UAT-01: 1/1 (el usuario de consulta abre las catorce pantallas por el menú y luego se le retira el rol). OWNER_UAT_READY + ACCESSIBLE.
- La pila de b98d4e6 (CNT-03) sigue en pie. La de P2 no se tocó.
- Remota del sponsor: REMOTE_SPONSOR_UAT_AVAILABLE=NO (BLOCKED_BY_INFRASTRUCTURE).
- Credenciales: no se registran.
