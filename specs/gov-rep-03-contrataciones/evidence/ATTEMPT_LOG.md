# ATTEMPT_LOG · REP-03 (2026-11-13)

```text
DEEPSEEK_CALLS=8 (tope 8 alcanzado sin excederlo; ninguna autorización extra)  COST_USD≈0.042
GLOBAL_CAP_REACHED=1 (la 8.ª llamada es la integración tras el merge ordinario con P2)
MAX_RETRIES_SINGLE_SUBPROBLEM=2 (backend: R1 -> C1 -> C2/B1; E2E: C2 -> C3)
PROVIDER_EMPTY_RESPONSES=1 (1.ª llamada: «Traceback», 2 tokens; se reenvió el mismo contenido, partido en dos mensajes)
CLAUDE_SEMANTIC_CODE_WRITTEN=0  CLAUDE_SEMANTIC_TESTS_WRITTEN=0  CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0  CLAUDE_SEMANTIC_QA_WRITTEN=0
```

| # | Encargo | in/out | USD | Resultado |
|---|---|---|---|---|
| 1 | R1 backend | 4980/2 | 0,0022 | Respuesta vacía del proveedor («Traceback»): nada que auditar |
| 2 | R1 (reenvío en 2 mensajes) | 5462/8461 | 0,0096 | 6/7 aplicados. **Catálogo rechazado** (SEARCH y REPLACE invertidos). Medidos: 12 errores de mypy, `record_audit(event_code=…)` inexistente, writer del CSV roto, fixture `ocupacion` duplicada y objeto desvinculado |
| 3 | C1 (reintento 1) | 9045/7955 | 0,0107 | 3/3 aplicados: PG 18/19 y catálogo 494 |
| 4 | R2 frontend (2 mensajes) | 10769/9203 | 0,0127 | 4/6 aplicados. **Router y Sidebar rechazados** (anclas inexistentes). Faltó la fila de PROC-11 en el humo |
| 5 | C2 (cableado + restos + E2E) | 6357/3485 | 0,0057 | 7/7 aplicados. E2E con selector ambiguo; B1 solo reformateó |
| 6 | C3 (reintento 1 de la E2E, 2 del tipo) | 874/525 | 0,0008 | 5/5 aplicados. Introdujo una colisión de nombre (causa nueva) |
| 7 | C4 (causa nueva) | 364/198 | 0,0003 | Aplicado: mypy en la línea base (157) |
| 8 | M1 integración tras merge con P2 (Spec 018 añadió otra entrada al catálogo: 495) | 387/115 | 0,0003 | Aplicado: catálogo 11/11 |

## Lo que hizo Claude (mecánico, declarado)

- **Regeneración:** instantáneas `qa/fixtures_de_frontend.py`.
- **Diagnóstico:** una copia temporal `e2e/zz-diag-rep03.spec.ts` con `exact: true`, borrada tras la corrida y nunca aplicada.
- **Atribución:** worktree `wt-279d6c8` para medir la línea base de mypy (157) y de las suites.
