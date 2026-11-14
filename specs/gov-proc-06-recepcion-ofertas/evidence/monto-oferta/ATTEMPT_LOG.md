# OMA · Registro de intentos de DeepSeek

- **Modelo:** todo con `deepseek-v4-pro`, sin `session_id` ni `thinking` y con `max_tokens` explícito.
- **Antes de cada llamada:** `EGRESS_CHECK_COMPLETE=1`. Los 8 briefs llegaron íntegros, con su línea de cierre.
- **Topes:** 8 llamadas por ciclo como máximo y 2 reintentos por subproblema. No se usó ninguna excepción de la dueña (`OWNER_EXCEPTION_USED=0`).

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A · backend núcleo (modelo, 0110, servicio, esquemas, API, registros y recuentos) | 12972/8895 | $0,013381 | **PASS parcial.** Modelo, migración, API, registros y recuentos aprobados; ORM igual a la migración (n10). **Rechazado:** I001 en 2 ficheros, import `date` sin usar y mypy (expediente posiblemente None) |
| 2 | B · consumidores PROC-10, REP-03 y PROC-08 | 5122/3732 | $0,005475 | 14 de 15 bloques aprobados. **Rechazado:** el bloque 6, porque su SEARCH tenía 8 espacios donde había 4 (el brief mostraba la línea sin sangría) |
| 3 | A·R1 + B·R1 | 1124/951 | $0,001316 | A·R1 AUDIT_PASS (ruff limpio, mypy igual a la línea base). **B·R1 rechazado:** el REPLACE del bloque 6 subía la sangría a 8 |
| 4 | C · pruebas (13) + B·R2 | 4919/9205 | $0,010148 | B·R2 AUDIT_PASS; las pruebas de PROC-10 pasan. **Pruebas rechazadas:** la sonda dio 12 de 13 en rojo (fixture llamado como función, campo inexistente, versión obsoleta, `db.text`, carrera sin sesión, nombres de modelo y de claves) |
| 5 | D · frontend (componente, ficha, decisión, reporte y Vitest) | 7934/9398 | $0,011628 | **PASS parcial.** Pantallas aprobadas. **Rechazado:** TS2345 (errores de campo como string), Vitest de la nota por nombre accesible y TS2322 en el fixture de REP-03 |
| 6 | C·R1 + D·R1 | 11742/10195 | $0,013977 | D·R1 AUDIT_PASS (typecheck, lint y Vitest 25/25). **C·R1 rechazado:** faltaban `pytest_plugins` e `import json`, sobraba una variable y había un I001. La sonda con esas 2 líneas dio 13/13 |
| 7 | E · E2E del monto + REP-03 | 9368/7969 | $0,011008 | AUDIT_PASS al primer intento. E2E en verde: las 2 pruebas a 1280, 390 y 320 con Axe |
| 8 | C·R2 | 9796/9374 | $0,012417 | AUDIT_PASS. 13/13 en PostgreSQL y ruff limpio. Las 3 mutaciones mueren |

```text
DEEPSEEK_CALLS=8  GLOBAL_CALL_HARD_CAP=8  GLOBAL_CAP_REACHED=1  OWNER_EXCEPTION_USED=0
DEEPSEEK_RETRIES=6 (A·R1, B·R1, B·R2, C·R1, C·R2 y D·R1, repartidos en 4 llamadas)
MAX_RETRIES_SINGLE_SUBPROBLEM=2 (B y C)
TOTAL_COST=$0,079350
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E, fixture semántico ni migración. Claude hizo:
- la arqueología, el delta, las decisiones, el gate, el plan, las tareas y los briefs;
- la auditoría y la aplicación literal de los bloques aprobados;
- las sondas de diagnóstico, temporales y retiradas;
- las 3 mutaciones, restauradas con la misma huella;
- la regeneración de fixtures (`qa/fixtures_de_frontend.py`);
- las matrices y los documentos.

**Lecciones:**
- Los fragmentos SEARCH de un brief deben mostrar su sangría literal. Una línea suelta sin indentar provocó 2 reintentos.
- En un brief de pruebas hay que dar la línea `pytest_plugins` literal y la firma de los callbacks de `carrera` (reciben la sesión).
- Agrupar varios reintentos de subproblemas distintos en una llamada ahorra presupuesto sin mezclar fronteras.
