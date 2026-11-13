# ATTEMPT_LOG · BUD-01 + BUD-02 (2026-11-13)

```text
DEEPSEEK_CALLS=23 (tope inicial 8; la dueña lo amplió: 18, +2, +1, +1 y +1 de integración con P2)  COST_USD≈0.157
GLOBAL_CAP_REACHED=1 (con cada ampliación autorizada explícitamente; nunca se superó sin autorización)
MAX_RETRIES_SINGLE_SUBPROBLEM=2 (migración: B1 -> R1 -> R2; pruebas PG: T1 -> R1 -> R2)
CLAUDE_SEMANTIC_CODE_WRITTEN=0  CLAUDE_SEMANTIC_TESTS_WRITTEN=0  CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0  CLAUDE_SEMANTIC_QA_WRITTEN=0
```

**Causa principal del sobrecoste.** DeepSeek devolvía un único fichero grande por respuesta. A partir de la llamada 5 se partió el trabajo por fichero y se lanzaron llamadas en paralelo.

| # | Encargo | Resultado |
|---|---|---|
| 1 | B1 capa de datos | Solo models.py: aplicado. Defecto: variable plpgsql ambigua en el trigger de partidas |
| 2 | B1 R1 | 12/14 aplicados. **Rechazados:** la migración (CHECK sin `IN (`) y la semilla N9 (dentro de otra función) |
| 3 | B2 servicio + API | **Rechazado:** solo el servicio, con level_id/orden confundidos, una consulta rota y la importación con doble validación |
| 4 | T1 pruebas PG | **Rechazado:** sin If-Match, `accion` en vez de `action`, años repetidos |
| 5 | B2a servicio (R1) | Aplicado. Defectos de mypy y de claves UUID/str, corregidos en C1-C3 |
| 6 | B2b esquemas + API + main | Aplicado con conversión de marcadores (solo formato). Deriva de longitudes, corregida en C1 |
| 7 | B1 R2 migración + semilla | Semilla aplicada (se añadió la ruta: solo formato). Migración con f-string multilínea (SyntaxError en 3.11), corregida en C1 |
| 8 | T1 R1 | Aplicada en provisional para diagnosticar. Defectos corregidos en T2 |
| 9 | F1a lista, detalle, ruta, menú | Aplicado (rutas entre ángulos: solo formato) |
| 10 | F1b componentes + prueba | Aplicado. 14 errores de tsc por firmas reales |
| 11 | C1 backend consolidado | 16/17 aplicados. **Rechazado:** el bloque 5 (`return None` inventado) |
| 12 | T2 pruebas (R2) | 14/15 aplicados. **Rechazado:** el bloque 15 (reintroducía un año repetido) |
| 13 | F1c frontend consolidado | Aplicado (bloque duplicado aplicado una vez) |
| 14 | F2 E2E + humo | Aplicado. Cabecera del CSV inventada (omisión del encargo), corregida en C3 |
| 15 | C2 servicio | **Rechazados los 4 bloques** (iteraba las claves del dict, `return` sustituido) |
| 16 | C3 servicio + Vitest + E2E | Aplicado |
| 17 | C4 fechas `date`, triggers en pytest.raises, Vitest, permisos de la E2E | Aplicado |
| 18 | C5 código completo en la tabla y selectores exactos | Aplicado |
| 19 | C6 colores del tema (Axe color-contrast 1,04) | Aplicado (bloques idénticos por fichero = todas las apariciones) |
| 20 | C7 contrato de consultas QC-02 | Aplicado |
| 21 | C8 import sin uso (tsc) | Aplicado |
| 22 | C9 constantes fijadas (cabeza, MFA, catálogo de permisos) | Aplicado |
| 23 | C10 integración con P2 (0107 tras 0106_open_supply_by_warehouse, catálogo 510) | Aplicado |

## Lo que hizo Claude (mecánico, declarado)

- Conversión de formato de marcadores y rutas, sin tocar el contenido: llamadas 6, 7 y 9.
- Aplicación en dos pasadas para desambiguar bloques: llamadas 11 y 12.
- `git mv` de la migración a 0107 y `git checkout --ours` en los 4 conflictos antes de C10.
- Regeneración de fixtures con `qa/fixtures_de_frontend.py`.
- Copias de diagnóstico temporales, borradas y nunca aplicadas: el payload de niveles en las pruebas PG y los nodos de Axe en la E2E.
- Worktree `wt-9dba4d8` para la atribución.
