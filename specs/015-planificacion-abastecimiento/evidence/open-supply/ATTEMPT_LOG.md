# Suministro abierto por almacén · registro de intentos

- **Modelo y modo:** todo con `deepseek-v4-pro`, `stream=true` y `max_tokens` explícito (de 3000 a 32000).
- **Topes:**
  - 8 llamadas por ciclo como máximo global;
  - 2 reintentos por subproblema como máximo.
- **Excepciones:** ninguna `OWNER_EXCEPTION`.
- **Subtareas divididas:** A2 y C son causas raíz nuevas que se separaron como subtareas. No reinician el contador global.

| Llamada | Subproblema | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A. Backend: 0106, modelos, `open_supply.py`, Compras, motor, necesidad, catálogo, guardias y pruebas | 8390/12537 | $0,014557 | AUDIT_PASS de 28 bloques. Rechazados 4: un SEARCH no único (5 coincidencias); un SEARCH de `add_receipt_line` sin sus dos comentarios reales (0 coincidencias); el constructor de la necesidad sin `trigger_open_supply` ni `trigger_projected_available` (A7); las pruebas con `func` sin importar, `__import__`, una aserción sin sentido y `supplier_id=None` |
| 2 | A·R1 | 12544/7683 | $0,012141 | AUDIT_PASS de 7 bloques: el código queda aplicado, ruff limpio y 139 pruebas existentes pasan. Rechazadas las pruebas: falta `import pytest`, y la sesión de prueba mantiene el `FOR UPDATE` de la orden mientras llama a la API sobre la misma orden (bloqueo en PostgreSQL) |
| 3 | A·R2 | 10469/5980 | $0,009757 | AUDIT_PASS: 8 de 9 en PostgreSQL. El fallo restante es una causa nueva (prueba 404/409 dirigida a una línea ya bloqueada) |
| 4 | B. Pantallas, Vitest y E2E | 13225/11613 | $0,015856 | Bloques aplicados. Al medir: TS6133 y lint (parámetro y variable sin uso), 4 fallos de Vitest y un localizador E2E en modo estricto |
| 5 | A2. Objetivo de las comprobaciones HTTP 404/409 | 589/502 | $0,000693 | AUDIT_PASS. 9/9 en PostgreSQL |
| 6 | B·R1 | 1415/1420 | $0,001851 | AUDIT_REJECT de formato: 9 de 10 bloques sin `=== END ===`. Claude no repara el formato del parche |
| 7 | B·R2 | 2993/1456 | $0,002569 | AUDIT_PASS de 9 bloques. Rechazado 1: el SEARCH de `beforeEach` tenía una sangría que no existe |
| 8 | C. `beforeEach` (cleanup implícito de Vitest) y escala de `open_quantity` («0» frente a «0.000000», medido en la E2E) | 451/153 | $0,000329 | AUDIT_PASS. Vitest 1972/1972 y E2E en verde a 1280, 390 y 320 |

```text
TOTAL_CALLS=8  TOTAL_RETRIES=4 (A·R1, A·R2, B·R1, B·R2)  SPLIT_SUBTASKS=2 (A2, C)
MAX_RETRIES_SINGLE_SUBPROBLEM=2  GLOBAL_CAP_REACHED=1 (8/8, sin superarlo)  OWNER_EXCEPTION=0
TOTAL_COST=$0,057753
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración. Claude hizo:
- la arqueología, las preguntas a la dueña, el delta, el gate y los briefs;
- la auditoría y la aplicación literal de los bloques aprobados;
- las 3 mutaciones de control, restauradas byte a byte;
- la regeneración mecánica de las fixtures de OpenAPI (`qa/fixtures_de_frontend.py`);
- las sondas de diagnóstico, fuera del repositorio y borradas;
- los documentos.

**Confirmaciones operativas:**
- **ALLOW:**
  - detener la UAT para la E2E;
  - crear y borrar la base de prueba `ktz106`;
  - un worktree temporal de HEAD para medir la línea base de mypy (eliminado);
  - preguntar a la dueña las decisiones materiales.
- **SKIP:** tocar órdenes reales; inferir el almacén histórico; ampliar la cotización (QUOTE-REQUISITION-LINK).
