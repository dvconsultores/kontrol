# CNT-07 · Registro de intentos de DeepSeek (2026-11-16)

- **Llamadas:** siempre `deepseek-v4-pro`, sin `session_id` ni `thinking`, con `max_tokens` explícito y sin mensaje de sistema.
- **Egreso:** antes de cada llamada se comprobó `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`. Solo salió código y datos sintéticos; los textos normativos se leyeron en local.
- **Topes:** el inicial era 8 (`OWNER_EXCEPTION_INHERITED=0`). La dueña lo amplió dos veces, con el diagnóstico listo: hasta 12 y hasta 15.

| N.º | Encargo | Tokens (entrada/salida) | Coste (USD) | Resultado de la auditoría |
|---|---|---|---|---|
| 1 | T002: migración 0122, modelo, permiso, catálogos de auditoría y SoD | 9766/6359 | 0,009781 | **PASS** (11/11): n10 sin diferencias en la tabla nueva y mypy en su línea base |
| 2 | T003: `situacion_contractual.py` y servicio | 16090/13259 | 0,018534 | **REJECT** parcial: 16 errores de mypy, E741, DOCUMENTO_ACUERDO en todas las figuras, APERTURA comparada con la eficacia, bloqueo auditado demasiado amplio, `version: int`, vista sin 409 |
| 3 | T004: API, guardas CNT-02/03/04, CNT-09, ficha y CNT-08 | 6774/5554 | 0,007779 | Guardas y API **PASS**; CNT-08 **REJECT**: nombre inexistente `situacion_contractual_terminacion_formalizada` |
| 4 | T005: pruebas PG | 7646/7234 | 0,009620 | **REJECT**, sonda 14/14: acto sin `emitido_en`, segundo borrador sobre el mismo contrato, módulo inexistente, `:cid` sin enlazar, CSV con base supuesta vacía |
| 5 | R1 (T003+T004+T005, 39 anclas) | 8837/6885 | 0,009834 | 38/39 aplicados; el bloque 38 con corrección de transporte (abajo). Producto **PASS** (mypy en línea base); 5 pruebas nuevas **REJECT** (sin `@ONLY_PG`, claves y métodos inexistentes) |
| 6 | R2 (pruebas, 9 anclas) | 3254/3776 | 0,004701 | 9/9; quedó un nombre inexistente (`GovernmentContractAct`) |
| 7 | T006 (frontend completo) | 0/0 | 0 | **Fallo de transporte**: timeout de la API de DeepSeek, sin respuesta ni coste |
| 8 | R3 (un nombre) | 199/64 | 0,000142 | **PASS**: PG 19/19 |
| 9 | T006a: página, tipos y Vitest | 8676/14461 | 0,016355 | **REJECT** parcial: props de componentes inexistentes, import sin usar, sin estado 404 y 2 defectos de la prueba |
| 10 | T006b: rutas, ficha, sección CNT-08 y documentos elegibles | 8697/2507 | 0,005964 | **PASS** (15/15); observación: fecha sin formatear |
| 11 | R4 (frontend, 6 anclas) | 1280/881 | 0,001323 | **PASS**: Vitest 60/60, tsc y ESLint |
| 12 | T007: E2E del sponsor y ajustes del ayudante | 4153/3018 | 0,004432 | 3/4 anclas aplicadas y H4 con corrección de transporte (abajo). Sonda: 5 localizadores ambiguos y 2 defectos de producto destapados |
| 13 | R5 (página: permiso `terminate` y envoltorios `relative`) | 639/350 | 0,000582 | **PASS** |
| 14 | R6 (E2E: localizadores) | 644/366 | 0,000599 | **PASS**: E2E 1/1 |

```text
DEEPSEEK_CALLS=14 (tope inicial 8; ampliado a 12 y a 15 por la dueña; 1 de reserva sin usar)  OWNER_EXCEPTION_USED=2
DEEPSEEK_RETRIES=6 semánticos (R1–R6)  TRANSPORT_FAILURES=1 (llamada 7)  MAX_RETRIES_SINGLE_SUBPROBLEM=2
TOKENS=76655/64714  COSTE_TOTAL=$0,089646
```

## Correcciones de aplicación (Claude, documentadas)

1. **Recuento SENSITIVE (77 → 78)** en `tests/test_mfa_policy.py`. La prueba no estaba entre los ficheros del brief de T002 (defecto del brief); es una consecuencia mecánica del permiso fijado en la Spec.
2. **R1, bloque 38:** el ancla al final del fichero incluía la línea vacía posterior al último salto, y el SEARCH la arrastró. Se aplicó sobre el tramo exacto, sin alterar el REPLACE.
3. **`ruff --fix`** (F401 e I001): imports sin usar en las pruebas y orden de imports en los servicios tocados por T004.
4. **T007, ancla H4:** el subagente envió el ancla corrupta (`firmanteSinLimite.id,`) y DeepSeek la reprodujo. Se restauró el ancla del brief y se aplicó la línea aportada (`emisorId: emisor.id,`) sin cambios.
5. **E2E:** se retiró un import de tipo sin usar (`APIRequestContext`), equivalente a un F401.
6. **Vitest de la página:** la capacidad simulada pasó de `formalize` a `terminate`. La prueba codificaba el mismo defecto que corrigió R5; la cadena la fija la Spec (C07-21).
7. **Recuento del catálogo (174 → 175)** en `tests/test_delegation_ceiling.py`. Lo destapó la PG completa. Es el mismo defecto del brief que el punto 1: el permiso nuevo sube el total, como ya ocurrió en CNT-03 y CNT-04.

**Implementado por Claude:** fuentes (lectura de N11, N12 y N25), spec, plan, contrato de datos, gate y tareas; briefs, auditorías, sondas (retiradas y restauradas por huella) y mutaciones (restauradas por huella); fixtures OpenAPI, evidencia, matrices y memoria. **Ninguna línea de producto, prueba, E2E ni migración es de Claude**, salvo las siete correcciones de arriba.

## Mutaciones (sonda de Claude, restauradas por huella; `sondas/cnt7/mutar7.py`)

| Mutación | Prueba que la mata |
|---|---|
| M1: permitir dos extinciones (sin el control ALREADY_EXISTS) | `test_rescision_no_imputable_formalizada` |
| M2: ignorar la causal | `test_causales_por_figura` |
| M3: aceptar cualquier acto como válido | `test_borrador_if_match_y_validaciones` (acto GENERAL) |
| M4: fecha de eficacia = día de registro | `test_eficacia_juridica_no_es_fecha_de_registro` |
| M5: hito posterior permitido en CNT-03 | `test_guardas_posteriores` |
| M6: ejecutar las garantías al formalizar | `test_garantes_y_garantia_no_se_ejecuta` |
| M7: anular los compromisos BUD-08 | `test_compromiso_presupuestario_no_se_anula` |
| M8: omitir CNT-07 de la cronología de CNT-08 | `test_expediente_cnt08_proyecta_la_terminacion` |
