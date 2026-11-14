# CTL-07 · Registro de intentos de DeepSeek

- **Modelo:** todo con `deepseek-v4-pro`, sin `session_id` ni `thinking`, con `max_tokens` explícito.
- **Comprobaciones:** antes de cada llamada, `EGRESS_CHECK_COMPLETE=1`. Cada brief termina con su línea de cierre; las 9 llegaron íntegras (`BRIEF_INTEGRO=1`).
- **Topes:** 8 llamadas por ciclo como máximo global y 2 reintentos por subproblema.

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A1 · backend (modelo, migración 0109, servicio, esquemas, API, registros y recuentos) | 9543/9489 | $0,012407 | **PASS parcial.** Aprobados el modelo, los esquemas, `setup`, MFA, el catálogo, el `include` de `main.py` y las 5 pruebas de recuento. **Rechazados:** `service_alertas.py` (4 errores de mypy, código muerto `... if False else ...` en `_salida` y orden contrario al contrato) y el orden de imports (ruff I001) en `api_alertas.py`, la migración y `main.py` |
| 2 | A1·R1 | 1727/1177 | $0,001775 | AUDIT_PASS. Ruff limpio y mypy en 157, igual que la línea base. Paridad n10 sin diferencias nuevas |
| 3 | B · pantalla, ruta, menú, requisito y Vitest | 4814/7984 | $0,009040 | Pantalla, ruta, menú y requisito aprobados (typecheck y eslint limpios). **Vitest rechazado:** 2 de 8 fallan por defectos de la prueba (`getByText` con dos coincidencias; doble render sin desmontar) |
| 4 | A2 · pruebas de backend | 5330/6535 | $0,008004 | **Rechazado:** cerca ```python dentro del bloque NEW. La sonda dio 10/12: el UUID se buscaba también en la clave, se usaba el id como nombre de usuario e I001 |
| 5 | B·R1 | 701/355 | $0,000614 | AUDIT_PASS. Vitest 8/8 |
| 6 | C · E2E | 4379/4363 | $0,005701 | **Rechazado:** cerca ```typescript; `detalle` tratado como objeto; autorrevisión con observación vacía (daba 422); ids tipados como número |
| 7 | A2·R1 | 7357/6519 | $0,008872 | AUDIT_PASS. 12/12 en PostgreSQL y ruff limpio. Mueren 2 mutaciones: sin autorrevisión (1 fallo) y sin filtro de empresa (1 fallo) |
| 8 | C·R1 | 5005/4385 | $0,005992 | **Rechazado:** variable sin usar (TS6133). La sonda encontró además un selector ambiguo (`getByLabel('Observación')` coincidía con «Sin observación») y una violación de Axe a 390 en la pantalla (`scrollable-region-focusable`) |
| 9 | X · OWNER_EXCEPTION | 614/248 | $0,000483 | **Llamada extra concedida por la dueña**, limitada a 3 cambios de una línea ya demostrados en una sonda: región accesible de la tabla, `exact: true` y quitar la variable. AUDIT_PASS. E2E en verde a 1280, 390 y 320 con Axe |
| 10 | Y · OWNER_EXCEPTION | 396/93 | $0,000253 | **Segunda llamada extra concedida por la dueña.** La suite PG final destapó `test_mfa_g00b_recuentos` (69→70 sensibles y 75→76 estándar, por los dos permisos nuevos). Se limitó a esos 2 literales. AUDIT_PASS. `test_mfa_policy.py` 95/95 |

```text
TOTAL_CALLS=10 (8 del tope + 2 OWNER_EXCEPTION)  TOTAL_RETRIES=4 (A1·R1, B·R1, A2·R1, C·R1)
MAX_RETRIES_SINGLE_SUBPROBLEM=1  GLOBAL_CAP_REACHED=1  OWNER_EXCEPTION=2
TOTAL_COST=$0,053141
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E, fixture ni migración. Claude hizo:
- la arqueología, la selección, la Spec, las decisiones, el plan, el gate y los briefs;
- la auditoría y la aplicación literal de los bloques aprobados;
- las sondas de diagnóstico, temporales y retiradas;
- las 2 mutaciones, restauradas byte a byte;
- la regeneración de fixtures (`qa/fixtures_de_frontend.py`);
- las matrices y los documentos.

**Lecciones:**
- DeepSeek envuelve en cercas de código los bloques NEW largos aunque el formato no lo pida. Hay que decirlo explícitamente en el primer brief: «sin cercas».
- En formularios con opciones de texto parecido, pedir en el brief de la E2E selectores `exact: true`.
- Cada permiso nuevo mueve también `test_mfa_g00b_recuentos`. Hay que incluirlo en el primer brief, junto con el catálogo y el techo de delegación.
