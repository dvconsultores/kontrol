# ATTEMPT_LOG · BUD-06

**Tope:** 8 llamadas, con un objetivo de 3–5. La dueña lo amplió a 9 solo para este ciclo: «Llamada 9».

**Modelo:** deepseek-v4-pro.

**Uso:** 9 llamadas, 45 065 tokens de entrada y 45 980 de salida, USD 0,0595.

| # | Encargo | Frontera | Entrada/salida | USD | Auditoría | Qué se halló al medir |
|---|---|---|---|---|---|---|
| 1 | C1 | Datos y contrato | 8157/2474 | 0,0057 | PARCIAL | Solo devolvió models.py, que era correcto y se aplicó |
| 2 | C2 | Servicio de dominio | 5098/7629 | 0,0089 | PASS con defectos | Fichero sin envoltura (se envolvió como fichero nuevo: formato). Defectos: `isinstance(x, Any)`, `_monto_es` sobre str, tipos Any, ids UUID hacia esquemas str e imports sin uso |
| 3 | C1b | Resto de datos y contrato | 6924/6667 | 0,0088 | PASS con defectos | UNIQUE de la migración distintos del ORM, router sin model_dump() e imports sin uso |
| 4 | C3 | Pruebas PG | 2958/5853 | 0,0064 | PASS con defectos | Sin envoltura (formato). KeyError 'items', clave motivo y cascada de la siembra |
| 5 | C4 | Pantalla y Vitest | 5706/8473 | 0,0097 | PASS con defectos | TextInput guardaba el evento, `vista` posiblemente indefinida y textos duplicados en Vitest |
| 6 | C5 | E2E | 4887/4688 | 0,0062 | PASS | Medido: todo el flujo pasaba; Axe a 320 px (target-size) |
| 7 | C7 | Corrección consolidada (reintento 1) | 7447/6752 | 0,0091 | PASS (26 de 27 bloques) | Devuelto en JSON (convertido a bloques: formato). El bloque 8 se rechazó por SEARCH no literal, sin retoque |
| 8 | C8 | Residuo (reintento 2) | 2129/2085 | 0,0027 | PASS | PG 8/10: login MFA dentro de cada hilo. Axe a 320 px: el select del firmante |
| 9 | C9 | Residuo final (autorizado) | 1759/1359 | 0,0019 | PASS | PG 10/10, Vitest 28/28, E2E 1/1 y mypy 157 |

## Ajustes de formato (sin contenido)

- Rutas asignadas por orden cuando venían sin ella (C1, C8, C9).
- Envoltura de ficheros nuevos que llegaron sin SEARCH/REPLACE (C2, C3).
- Conversión del JSON de C7 a bloques.
- `ruff --fix` en api_presupuesto_certificacion.py: orden alfabético de dos nombres dentro de un import.
- Fixtures OpenAPI regenerados con `qa/fixtures_de_frontend.py`.

## Diagnóstico de Claude (causa raíz, sin producto)

Para identificar el nodo de Axe a 320 px, Claude usó una copia temporal de la E2E que imprimía los nodos `target-size`. Se borró tras la ejecución y no se confirma.

## Escritura de Claude

CLAUDE_SEMANTIC_CODE_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0, CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0, CLAUDE_SEMANTIC_QA_WRITTEN=0.

## Reintentos por subproblema

| Subproblema | Reintentos |
|---|---|
| Backend | 2 (C7, C8) más el residuo autorizado (C9) |
| Pruebas PG | 2 (C7, C8) más C9 |
| Pantalla | 2 (C7, C8) más C9 |
| E2E | 0: la E2E de C5 no cambió; Axe se corrigió en la pantalla |
