# ATTEMPT_LOG · BUD-03 + BUD-04

**Tope:** 8 llamadas. La dueña lo amplió a 11 solo para este ciclo («Raise cap to 11»).

**Modelo:** deepseek-v4-pro en todas las llamadas, con stream y sin sesión.

**Uso:** 10 llamadas, 62 424 tokens de entrada y 67 392 de salida, USD 0,0858. La llamada 11 no se usó.

| # | Encargo | Frontera semántica | Entrada/salida | USD | Resultado de la auditoría | Qué se halló al medir |
|---|---|---|---|---|---|---|
| 1 | C1 | Datos: modelos, migración 0108, catálogo (+13) y fijaciones | 6060/7865 | 0,0095 | PASS con defecto | La migración usaba `_en` antes de definirlo (NameError); lo corrigió C2R |
| 2 | C2 | Servicios, esquemas, API y fotografía | 8487/5654 | 0,0086 | PARCIAL | Devolvió un solo fichero: importaba `app.core.constants` (no existe) y filtraba por `tenant_id` (no existe). Lo reemplazó C2R |
| 3 | C3 | Pruebas PG | 3780/5848 | 0,0067 | REJECT | Usaba códigos en lugar de ids, SQL crudo y helpers inventados |
| 4 | C4 | Frontend y Vitest | 5494/12456 | 0,0132 | PASS con defectos | tsc: genérico de escribirBloque, `documento.summary` y fixtures. Vitest: caída con `estructura_organizativa` indefinida y nombres de campos obligatorios |
| 5 | C2R | Reintento 1 de servicios y API | 9004/10222 | 0,0128 | PASS con 3 defectos | El bloque 19 se omitió (fotografía errónea). Tras aplicar se corrigieron el If-Match como valor por defecto (K1) y `ejercicio.status` (K2) |
| 6 | C6 | Reintento 1 de las pruebas PG | 5842/6775 | 0,0084 | PASS | Quedaron 6 fallos, todos del lado de la prueba |
| 7 | C7 | Corrección del frontend y primera E2E | 7248/6088 | 0,0084 | PASS con defectos | La E2E redefinía RESPONSABLE_ESTRUCTURA, usaba la firma equivocada del helper y comparaba rutas sin el prefijo `/api/v1` |
| 8 | C8 | Corrección consolidada medida | 9851/7318 | 0,0107 | PASS (aplicación mecánica, ver abajo) | Tras aplicarla: PG 19/23 y la E2E falló por el año |
| 9 | C9 | Pruebas PG y E2E | 6047/4796 | 0,0068 | PASS (tras aplicarla: PG 23/23) | La E2E falló por un localizador ambiguo; además, C9 eliminó sin pedirlo el paso del documento del plan |
| 10 | C10 | Localizadores con exact y restauración del documento del plan | 611/370 | 0,0006 | PASS | E2E 1/1, y 4/4 con `--repeat-each=2 --workers=4` |

## Aplicación mecánica

ap4 aplica los bloques todo o nada y sin retoques. Lo mecánico de C8 fue esto:

- Los bloques 5 y 12, y los bloques 13 y 14, tenían SEARCH y REPLACE idénticos. Se aplicaron una vez a las dos apariciones (`--todas`) y se omitió el bloque gemelo.
- El bloque 22 se solapaba con el 18, que ya cubría el mismo cambio, y se omitió.

No hubo más retoques.

## Escritura de Claude

CLAUDE_SEMANTIC_BACKEND_WRITTEN=0, CLAUDE_SEMANTIC_FRONTEND_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0. Claude escribió solo documentos: Spec, plan, tareas, matrices y evidencia.

## Reintentos por subproblema (máximo 2)

| Subproblema | Reintentos |
|---|---|
| Servicios y API | 1 (C2R) |
| Pruebas PG | 2 (C6 y C8; C9 es residuo medido de C8) |
| Frontend | 1 (C7) |
| E2E | 2 (C9 y C10) |
