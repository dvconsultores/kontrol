# Recibido sin confirmar: registro de intentos

- **Modelo y modo:** todo con `deepseek-v4-pro`, `stream=true` y `max_tokens` explícito (de 3000 a 24000).
- **Topes:**
  - 8 llamadas por ciclo como máximo global;
  - 2 reintentos por subproblema como máximo.
- **Excepciones:** ninguna `OWNER_EXCEPTION`.

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A. Backend: `open_supply.py`, motor, necesidad y pruebas | 8621/9047 | $0,011621 | **Entrada defectuosa:** el puente recortó el brief (faltaban unas 160 líneas de contexto de pruebas) y añadió una línea inventada. Se audita lo recibido: 4 bloques con AUDIT_PASS (motor y necesidad). Rechazado `open_supply.py`, porque `en_camino` duplicaba las dos consultas en lugar de reutilizar los constructores. Rechazadas las pruebas: variables sin asignar en la prueba 1, firma de `_necesidades_activas`, clave `recommended` y falta de `currency` |
| 2 | A·R1 | 7336/7011 | $0,009291 | Rechazado `open_supply.py` por regresión grave: constante inventada `"PENDING"`, atribución por el destino de la línea en lugar del almacén de la recepción, sin filtro de estado ni de confirmación, unión que multiplica filas y sin `coalesce`. AUDIT_PASS del fichero de pruebas salvo la prueba 1, que seguía mal y se corrigió por EDIT en R2 |
| 3 | A·R2 (base obligatoria: el módulo del intento 1 y la estructura exacta de `en_camino`) | 4431/2716 | $0,004290 | AUDIT_PASS. Ruff limpio; 9/10 en PostgreSQL. El fallo restante tiene una causa nueva: el motivo obligatorio de RECIBIDO → RECHAZADO |
| 4 | A2. Motivo en la decisión de rechazo del helper de pruebas | 593/567 | $0,000751 | AUDIT_PASS. 10/10 nuevas y 9/9 de suministro abierto |
| 5 | B. Pantallas, Vitest y E2E | 9293/6308 | $0,009530 | 6 bloques con AUDIT_PASS. Rechazado el bloque de las filas de la necesidad (dos `=======` en un mismo bloque). Al medir: `postCrudo` sin uso (TS6133 y lint), y la E2E comprobaba la pantalla sin volver a cargar el detalle en los pasos 6 y 10 |
| 6 | B·R1 | 1131/941 | $0,001311 | AUDIT_PASS de 5 bloques. Typecheck y lint limpios, Vitest 1974/1974, E2E en verde a 1280, 390 y 320 |

```text
TOTAL_CALLS=6  TOTAL_RETRIES=3 (A·R1, A·R2, B·R1)  SPLIT_SUBTASKS=1 (A2)
MAX_RETRIES_SINGLE_SUBPROBLEM=2  GLOBAL_CAP_REACHED=0 (6/8)  OWNER_EXCEPTION=0
TOTAL_COST=$0,036794
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración. Claude hizo:
- la arqueología de las autoridades;
- el delta, el gate y los briefs;
- la auditoría y la aplicación literal de los bloques aprobados;
- las 3 mutaciones de control, restauradas byte a byte;
- la configuración de Playwright para las sondas, fuera del repositorio;
- los documentos.

**Lección del puente:** el brief de la llamada 1 se recortó al retranscribirse. Desde la llamada 2 se pide `BRIEF_INTEGRO` y la última línea esperada, y los briefs se hicieron más cortos (de 27 KB a 3 KB).
