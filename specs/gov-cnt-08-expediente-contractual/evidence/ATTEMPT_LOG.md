# CNT-08 · Registro de intentos de DeepSeek (2026-11-15)

- **Llamadas:** siempre `deepseek-v4-pro`, sin `session_id` ni `thinking`, con `max_tokens` explícito y sin mensaje de sistema.
- **Egreso:** antes de cada llamada se comprobó `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`.
- **Topes:** el tope inicial era 8 (`OWNER_EXCEPTION_INHERITED=0`). La dueña lo amplió cinco veces, siempre con el diagnóstico listo: hasta 12, 16, 18, 21 y 22.

| N.º | Encargo | Tokens (entrada/salida) | Coste (USD) | Resultado de la auditoría |
|---|---|---|---|---|
| 1 | T003: servicio de proyección | 16816/17832 | 0,022829 | **REJECT** (D1–D14): código muerto `if False`, contexto fabricado, `instante_actual` sin importar, `date.today()`, `vigente` inventada, `try/except pass`, `version` inexistente, actos sin documento, orden, actor con tenant None, etiquetas equivocadas y lista paginada en memoria |
| 2 | T002+T004: migración, modelos, catálogo, cabeceras, paquete, API y `main` | 16174/15498 | 0,020519 | Migración, modelos, catálogo y cabeceras **PASS**; paquete **REJECT** (E1–E12): `version.stored_file` inexistente, búsqueda heurística, UUID como versión, campos vacíos en CSV/JSON, `ScalarResult` sin `.first()`, `descargar` por clave inexistente |
| 3 | T003·R1 | 10248/15933 | 0,018320 | **PASS** parcial (12/12 bloques); residuo de tipos (E13–E16) |
| 4 | T004·R1, más el residuo de T003 | 8444/11315 | 0,013517 | 13/14 bloques aplicados; el bloque 3 se **RECHAZÓ** (SEARCH no exacto: el puente convirtió `﻿` en el carácter BOM); el bloque 14 no cambiaba nada |
| 5 | T004·R2 | 8940/7663 | 0,010556 | Bloque 4 aplicado con corrección de transporte (abajo); el bloque 5 venía malformado y se **RECHAZÓ** y revirtió; mypy de vuelta a la línea base |
| 6 | T005: pruebas PG | 10615/6262 | 0,010065 | **REJECT**, sonda 9/9: 8 defectos de la prueba (ninguno de producto) |
| 7 | T006: frontend y Vitest | 10728/27482 | 0,028576 | **REJECT**: 3 de producto (código muerto, tipo de `notify` y parámetros no literales que rechaza QC-02) y 5 de la prueba |
| 8 | T005·R1 | 2191/2320 | 0,002971 | Parcial: quedaron 3 defectos (imports, manifiesto y acciones de auditoría) |
| 9 | T006·R1 | 1469/1052 | 0,001554 | **PASS**: Vitest y guardas 25/25 |
| 10 | T005·R2 | 883/557 | 0,000869 | **PASS**: 9/9 PG |
| 11 | T005b: prueba del snapshot | 1486/1188 | 0,001680 | **PASS**: la mutación M4 (sin REPEATABLE READ), que antes vivía, muere |
| 12 | T007: E2E | 3212/3374 | 0,004333 | **REJECT** en la sonda: imports sin usar, usuario sin permisos de control fiscal y descarga de un documento sellado (404) |
| 13 | T003c: sello en el índice (D08-09) | 1779/1888 | 0,002416 | Producto **PASS**; la prueba nueva traía 3 defectos y una premisa falsa del brief (el paquete no incluye los sellados) |
| 14 | T006c: frontend del sello | 1990/1938 | 0,002552 | Producto **PASS**; la prueba nueva quedó anidada dentro de otra |
| 15 | T003c·R1 | 981/561 | 0,000915 | **PASS**: 10/10 PG, motivo SELLADO |
| 16 | T006c·R1 | 851/498 | 0,000803 | **PASS**: 12/12 |
| 17 | T007·R1 | 1177/790 | 0,001199 | **PASS**: E2E 1/1 |
| 18 | T003d: integración CNT-03 | 3081/2779 | 0,003758 | Producto **PASS** (sonda 11/11); prueba nueva **REJECT** (rutas, ayudantes y firmas inexistentes) |
| 19 | T006d: Ejecución en el frontend | 2194/4278 | 0,004676 | **REJECT**: interfaz partida (sintaxis) y 3 campos inexistentes |
| 20 | T003d·R1 | 1176/882 | 0,001279 | Parcial: `mundo.get` usado como cliente |
| 21 | T006d·R1 | 1150/896 | 0,001280 | **PASS**: 26/26 |
| 22 | T003d·R2 | 545/221 | 0,000429 | **PASS**: 11/11 PG |

```text
DEEPSEEK_CALLS=22 (tope inicial 8; 14 extra con 5 autorizaciones de la dueña)  OWNER_EXCEPTION_USED=5
DEEPSEEK_RETRIES=12 semánticos  MAX_RETRIES_SINGLE_SUBPROBLEM=2  TOKENS=106130/125207  COSTE_TOTAL=$0,155096
```

## Correcciones de aplicación y de herramienta (Claude, documentadas)

1. **Revisión de la migración.** Pasó de `0119_gov_cnt08_expediente_contractual` (37 caracteres) a `0119_gov_cnt08_expediente`, porque `alembic_version` admite 32. El nombre lo fijó Claude en el brief. Después se reencadenó a `0120_gov_cnt08_expediente` sobre la 0119 de CNT-03 (P1).
2. **Bloque 4 de T004·R2.** El SEARCH solo difería en dos líneas: el puente convirtió el escape `﻿` del brief en el carácter BOM. El REPLACE se aplicó sobre el tramo exacto al que apuntaba el ancla, sin alterar su contenido (mismo criterio que la llamada 8 de CNT-02).
3. **Orden de imports y un import sin usar.** Los resolvió `ruff --fix` (formato mecánico): I001 en dos ficheros tras T004·R2 y un F401 tras T005b.

**Implementado por Claude:** arqueología, fuentes, spec, plan, contrato de datos, gate y tareas; briefs, auditorías, sondas (retiradas y restauradas por huella) y mutaciones (restauradas); fixtures OpenAPI, evidencia, matrices y fusiones. **Ninguna línea de producto, prueba, E2E ni migración es de Claude**, salvo las tres correcciones de arriba.

## Mutaciones (sonda de Claude, restauradas por huella)

| Mutación | Prueba que la mata |
|---|---|
| M1: monto vigente = monto original | `test_expediente_completo` |
| M2: no excluir CONTRATO y GARANTIA de PROC-03 | `test_cronologia_orden_filtros_y_paginacion` |
| M3: integridad sin `storage.verify` | `test_integridad` |
| M4: sin REPEATABLE READ | `test_paquete_snapshot_consistente` |
| M5: sin control MANIFIESTO_ALTERADO | `test_paquete_generar_descargar_verificar` |
| M6: expediente también para un BORRADOR | `test_borrador_y_aislamiento` |
