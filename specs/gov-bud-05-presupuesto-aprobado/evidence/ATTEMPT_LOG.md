# ATTEMPT_LOG · BUD-05

**Tope:** 8 llamadas, con un objetivo de 3–5. La dueña lo amplió durante el ciclo, solo para este ciclo:
- a 10: «Ampliar a 10»;
- a 11: «Llamada 11, reintento 3»;
- a 12: «Llamada 12»;
- a 13: «Llamada 13», para la integración con P2.

**Modelo:** deepseek-v4-pro, con stream y sin sesión.

**Uso:** 13 llamadas. Una fue un timeout del transporte, sin respuesta. Las otras 12 suman 49 393 tokens de entrada y 62 489 de salida, USD 0,0757.

| # | Encargo | Frontera | Entrada/salida | USD | Auditoría | Qué se halló al medir |
|---|---|---|---|---|---|---|
| 1 | C1 | Datos y contrato | — | — | sin respuesta | «Streaming API Error: Request timed out». La carga se redujo de 31 k a 26 k |
| 2 | C1 (reenvío) | Modelos, migración 0109, catálogo (+8), esquemas, router, main, fijaciones | 7847/8785 | 0,0111 | PASS con defectos | Bloques sin ruta (se asignaron por orden: formato). ruff I001 en main.py. El ORM y la migración diferían en el índice único de las existencias |
| 3 | C2 | Dominio y guardas, más la corrección de C1 | 8398/11781 | 0,0139 | PASS con defectos | `except Exception`, parámetros sin uso, tope de 17 dígitos y 19 errores de mypy |
| 4 | C3 | Pruebas PG | 3944/9157 | 0,0096 | PASS con defectos | KeyError, versión tomada de una respuesta 403, procedencias cortas y fechas de corte futuras |
| 5 | C4 | Pantalla y Vitest | 6083/9602 | 0,0110 | PASS con defectos | Edición por fila inerte. Fixture con campos inexistentes (tsc). Texto duplicado en Vitest |
| 6 | C6 | Corrección del backend y las pruebas (reintento 1) | 6163/5963 | 0,0079 | PARCIAL | Aplicación mecánica: 5 bloques idénticos con `--todas=6` y 3 con `--todas=23`. Quedaron credito_id y v_anterior sin definir y los años sin cambiar |
| 7 | C7 | Corrección del frontend y E2E | 5363/6815 | 0,0083 | Frontend PASS; **E2E REJECT** | Bloque de la E2E sin `=======` y con rutas y cuerpos de API inventados |
| 8 | C8 | Residuo de pruebas PG, B3 y Vitest (reintento 2) | 2866/2583 | 0,0035 | PASS | PG 80/80, mypy 157 y Vitest verde |
| 9 | C9 | E2E (reintento 1) | 4957/5115 | 0,0066 | PASS con defectos | Medido: PERMISSION_DENIED en enteActivo. Auditado: ids, formato de montos y regiones |
| 10 | C10 | E2E (reintento 2) | 1687/1348 | 0,0019 | PASS | Medido: getByLabel exacto, por el asterisco aria-hidden de FormField |
| 11 | C11 | Localizadores de la E2E (reintento 3, autorizado) | 702/580 | 0,0008 | PASS | Medido: GOV_BUDGET_YEAR_INCOMPLETE. La siembra del clasificador iba sin documento, **por error del encargo de Claude** (`documento_id: null`) |
| 12 | C12 | Siembra del clasificador (autorizado) | 582/422 | 0,0006 | PASS | E2E 1/1, y 6/6 con las tres E2E de presupuesto y `--repeat-each=2 --workers=4` |
| 13 | C13 | Integración con P2 (autorizado): migración reencadenada como 0111 tras 0110 y fijaciones (catálogo 534) | 801/338 | 0,0006 | PASS | Alembic con una cabeza; pruebas tras el merge verdes, salvo la línea base. Antes, Claude tomó con git el lado propio (`--ours`) de las 4 fijaciones en conflicto y movió el fichero con `git mv`, sin escribir contenido |

## Errores de diseño atribuibles a Claude

- La revisión «0109_gov_bud05_presupuesto_aprobado» tenía 35 caracteres y VARCHAR(32) no la admite. Se corrigió en C6 como «0109_gov_bud05_aprobado».
- Las fechas de corte de las pruebas caían en el futuro con los años 2091–2099. Se corrigió en C6 y C8.
- `documento_id: null` en la siembra de la E2E. Se corrigió en C12.

## Escritura de Claude

CLAUDE_SEMANTIC_CODE_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0, CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0, CLAUDE_SEMANTIC_QA_WRITTEN=0.

Claude escribió solo documentos y encargos.

Los fixtures OpenAPI del frontend se regeneraron con el generador del repositorio (`qa/fixtures_de_frontend.py`). No se editaron a mano.

## Reintentos por subproblema

| Subproblema | Reintentos |
|---|---|
| Backend | 1 (C6) |
| Pruebas PG | 2 (C6 y C8) |
| Frontend | 2 (C7 y C8) |
| E2E | 4: C9 y C10, más C11 y C12 autorizados expresamente por la dueña. C7 fue el primer intento, rechazado |
