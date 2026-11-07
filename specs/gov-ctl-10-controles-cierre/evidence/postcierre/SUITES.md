# CTL-10 POST-CLOSURE-01 · certificación del árbol final

Ejecutado el 2026-11-07, después del último cambio de producto y de pruebas.

| Suite | Resultado |
|---|---|
| Pruebas backend del delta | 10/10 (`test_gov_ctl10_lista_contexto.py`); RED previo: 7 fallidas, 3 salvaguardas previas |
| Regresión dirigida backend CTL-10 y CTL-06 | 138 pruebas, 0 fallos |
| E2E dirigida CTL-10, CTL-06 y DOC-02 | 42/42 en chromium, firefox y webkit, `--retries=0` |
| Mutaciones | 35 muertos, 0 equivalentes, 0 supervivientes |
| PostgreSQL | `r20261107t010747p192868n5241e9`: 4569/0/18 |
| SQLite | `r20261107t020909p803148n3af0b7`: 2792/0/1795 |
| vitest · tsc · eslint · build | 1304/1304 (rc 0, 0 errores no controlados); 0; 0; correcto |
| ruff · mypy | limpio; 154 = línea base, 0 nuevos |
| OpenAPI | 530 rutas, 0 nuevas, 0 retiradas, 0 esquemas; solo 2 operaciones con parámetros opcionales aditivos |
| Regresión de Gobierno | `r20261107t022644p940408n30b0aa`: 189/189 en tres navegadores; `rc_scan=0`, `rc_integridad=0` |
| Canónica | `r20261107t025151p1002758nd97ced`: 451/451, 0 reintentos |
| Integridad tras la E2E | 96 controles, 0 violaciones |

T042_REPRODUCED = 1. MIGRATION_ADDED = 0. CROSS_VERTICAL_SEMANTIC_CHANGE_REQUIRED = 0. UNRUN_REQUIRED_SUITES = 0.

T042, desde el menú: panel de bloqueo → «Ir a la lista» → lista con el contexto aplicado; «Quitar filtro» vuelve a la lista general. Probado en CIE-E2E-01 (hallazgos) y CIE-E2E-02 (actos).

T043: `test_lc10_mas_de_cinco_pendientes`, con seis pendientes: muestra de 5, `pendientes` real, `total` igual y lista enlazada con el mismo total. Mutantes T01 a T05 muertos.

## Pila de prueba de la dueña

Relevada a `6fa6d4f`, puertos 18100 / 15273 / 18110, corrida `r20261107t030704p1043956nbac55d`, sin conexiones vivas que respetar. HUMO-UAT-01: 1/1. `/login` → 200; API sin sesión → 401. UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, permisos 600. OWNER_UAT_ACCESSIBLE = YES. OWNER_ACCEPTED = pendiente.
