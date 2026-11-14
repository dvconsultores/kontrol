# AAL · Registro de intentos de DeepSeek

- **Modelo:** todo con `deepseek-v4-pro`, sin `session_id` ni `thinking` y con `max_tokens` explícito.
- **Antes de cada llamada:** `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`. Los 5 briefs llegaron íntegros, con su línea de cierre.
- **Topes:** 8 llamadas por ciclo como máximo y 2 reintentos por subproblema. No se usó ninguna excepción de la dueña (`OWNER_EXCEPTION_USED=0`).

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | A · servicio del límite, ejecución, vista previa, catálogo y recuento (T002) | 4453/3474 | $0,004959 | **AUDIT_PASS** al primer intento: 7 bloques exactos, ruff limpio, mypy en 157 (igual que la base), PROC-08, OMA, REP-03 y PROC-10 en 46/46 en PostgreSQL |
| 2 | B · pruebas backend (T003) | 4848/4939 | $0,006406 | **AUDIT_REJECT**: `.count()` sobre un `Select` (no existe en SQLAlchemy 2), falta el import de `registrar_decision` y la desierta usa una versión obsoleta (409 STALE). Sonda: 11 de 12 |
| 3 | B·R1 · 4 ediciones sobre la propuesta | 5719/400 | $0,002836 | **AUDIT_PASS**: 12/12 en PostgreSQL y ruff limpio. Las 4 mutaciones mueren |
| 4 | C · panel de UI y Vitest (T004) | 2264/2325 | $0,003008 | **PASS parcial**: el componente y las 4 ediciones de `ExpedienteDecision.tsx` se aprueban. **Test rechazado:** TS2739, porque `base()` devolvía un `ControlMonto` incompleto (el Vitest pasaba 3/3) |
| 5 | D · E2E (ayudantes, recorrido y garantías) + C·R1 (T005) | 4449/3616 | $0,005081 | **AUDIT_PASS**: 12 bloques exactos; typecheck y lint limpios; Vitest 3/3; E2E de decisión, garantías, monto y REP-03 en 4/4, con 0 reintentos |

```text
DEEPSEEK_CALLS=5  GLOBAL_CALL_HARD_CAP=8  GLOBAL_CAP_REACHED=0  OWNER_EXCEPTION_USED=0
DEEPSEEK_RETRIES=2 (B·R1 y C·R1; C·R1 fue en la misma llamada que D)
MAX_RETRIES_SINGLE_SUBPROBLEM=1
TOTAL_COST=$0,022290
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración (no hubo migración). Claude hizo:
- la arqueología, el delta, el gate, el plan, las tareas y los briefs;
- la auditoría y la aplicación literal (aplicador nuevo `apply_file.py`: SEARCH exacto y único, y escritura atómica);
- las sondas temporales, retiradas;
- las 4 mutaciones, restauradas con la misma huella `7dec601c9a62`;
- la regeneración de fixtures (sin cambios);
- las matrices y los documentos.

**Mutaciones** (`service_decision_limite.py`):

| Mutación | Prueba que la mata |
|---|---|
| M1: `>` → `>=` | `test_misma_moneda_compara_el_total[50000.00]` |
| M2: sin control de moneda | `test_moneda_distinta_bloquea_sin_convertir` |
| M3: sin `FOR UPDATE` de la estructura | `test_carrera_con_cambio_de_limite` |
| M4: «sin monto» evaluado antes que «sin límite» | `test_oferta_sin_monto_con_limite_bloquea` |

**Lecciones:**
- La sonda temporal con las correcciones mínimas permite dar en un solo reintento todos los motivos.
- Un reintento de test se puede agrupar con la tarea siguiente sin mezclar fronteras.
- El arnés de mutación tiene que detectar las líneas `FAILED`: con `-q`, esta configuración no imprime «N failed».
