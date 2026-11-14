# Confirmación completa: registro de intentos

- **Modelo:** todo con `deepseek-v4-pro`, sin `session_id` ni `thinking`, con `max_tokens` explícito (de 3000 a 24000).
- **Topes:**
  - 8 llamadas por ciclo como máximo global;
  - 2 reintentos por subproblema como máximo.
- **Excepciones:** ninguna `OWNER_EXCEPTION`.
- **Comprobaciones por llamada:** `EGRESS_CHECK_COMPLETE=1` antes de cada una. Cada brief termina con una línea de cierre y el puente confirma `BRIEF_INTEGRO=1`; las 6 llegaron íntegras.

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A. Servicio, conciliación y pruebas | 8800/8364 | $0,011105 | AUDIT_PASS de 5 bloques: import, `_base_aceptada`, conciliación y los dos de la prueba de la 015. También es correcto el bloque que invoca la validación, pero se aparta porque depende de la función rechazada. **Rechazados:** `validar_completitud_de_confirmacion` (variable `l`, ruff E741, y `list[dict[str, str]]` con `None`, error de mypy); y el fichero de pruebas, porque `_contar` emparejaba con `[[]]` y contaba solo una línea con el valor `"[]"`, y porque la prueba «no aceptada» usaba un helper que siempre acepta |
| 2 | B. Pantalla, tipos, Vitest y E2E | 11674/9407 | $0,013262 | AUDIT_PASS de 7 bloques: tipos, los 3 de la pantalla y los 3 de las E2E existentes, incluido el arreglo del arnés de `inventory-confirmation`. **Rechazados:** el Vitest, que usaba `screen.getByLabel` (no existe en Testing Library), y la E2E nueva, por una constante `RUN` sin uso (TS6133) |
| 3 | A·R1 | 6337/5555 | $0,007589 | AUDIT_PASS. Se aplicó junto con el bloque apartado de la llamada 1. 62/62 en PostgreSQL, mypy igual que HEAD (157). Quedaba ruff B905 (`zip` sin `strict=`) en dos líneas del fichero de pruebas |
| 4 | A·R2 | 378/180 | $0,000321 | AUDIT_PASS: `strict=True`. Ruff limpio |
| 5 | B·R1 | 5532/5026 | $0,006779 | AUDIT_PASS. El diff contra el intento anterior solo cambia `getByLabel` → `getByLabelText` y quita `RUN`. Vitest 5/5 y E2E en verde a 1280, 390 y 320 |
| 6 | B·R2 | 398/145 | $0,000299 | AUDIT_PASS. La regresión E2E a 1280 encontró dos specs más que rellenaban la etiqueta antigua, «Cantidad a confirmar» (`recibido-sin-confirmar` e `importaciones`). Se cambió el localizador y las dos pasan |

```text
TOTAL_CALLS=6  TOTAL_RETRIES=4 (A·R1, A·R2, B·R1, B·R2)  SPLIT_SUBTASKS=0
MAX_RETRIES_SINGLE_SUBPROBLEM=2  GLOBAL_CAP_REACHED=0 (6/8)  OWNER_EXCEPTION=0
TOTAL_COST=$0,039355
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E, fixture ni migración. Claude hizo:
- la reproducción con una sonda diagnóstica fuera del repositorio;
- la arqueología, el delta, el gate y los briefs;
- la auditoría y la aplicación literal de los bloques aprobados;
- las 3 mutaciones de control, restauradas byte a byte;
- las configuraciones de Playwright de las sondas, fuera del repositorio;
- los documentos y la tarjeta.

**Lección:** antes de redactar un brief que cambia la etiqueta de un campo, buscar en `e2e/` los usos de esa etiqueta por la pantalla, no solo las llamadas a la API. Esa búsqueda incompleta costó el reintento B·R2.
