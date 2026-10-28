# AUDIT CATALOG (04) — orquestación Claude + DeepSeek (2026-10-28)

**Reparto del trabajo.**

Claude:
- hizo la arqueología: inventario AST de emisiones, perfil de ejecución de la suite y perfil de datos de la base sembrada;
- diseñó el catálogo de 231 entradas (`catalogo.md`), AD-1..AD-12 y los encargos;
- pasó el EGRESS antes de cada llamada, con extractos saneados (sin EICAR_TEST_FIXTURE ni la contraseña sintética);
- auditó, aplicó tal cual, midió rojo y verde y certificó;
- escribió el delta y la evidencia, que son artefactos de diseño;
- regeneró las fixtures de rutas del frontend con su generador (`qa/fixtures_de_frontend.py`), un paso mecánico.

DeepSeek escribió todo el código de producto, la migración 0061, todas las pruebas (pytest, vitest y Playwright), la transcripción del catálogo y la documentación de contratos. **Implementadas por Claude: 0.**

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| C04-T01 | Núcleo del catálogo | pro, flash | c0: código muerto, imports sin uso, `typing`, `isinstance` con tupla, `set` que podía lanzar → r1 PASS | 1 |
| C04-T02a/b | Transcripción de 231 entradas | pro ×2 | PASS: 0 diferencias por comparación automática | 0 |
| C04-T02c | Corrección del DISEÑO: la familia de `decide_return` es APPROVED/REJECTED (**error de Claude**, detectado por PostgreSQL) | flash | PASS | 0 |
| C04-T03 | `record_audit`, ContextVar, middleware y frontera de rechazo | pro, flash | Producto PASS; pruebas c0: REC-08 mal planteada, REC-04 laxa, import `conftest` → r1 PASS | 1 |
| C04-T04a/b/c | Contexto de empresa y tenant | pro ×4, flash | Primer envío: fallo de transporte (>100 000 caracteres). Producto PASS; pruebas c0: import inventado → r1: analizador como `lambda` y firma posicional → r2 PASS | 2 (+1 transporte) |
| C04-T05 | Pruebas sonda | flash | PASS | 0 |
| C04-T06 | Inmutabilidad, migración 0061 e índice | pro, flash | c0: IMM-07 con excepción amplia e INSERT sin commit → r1 PASS | 1 |
| C04-T07 | Versión del motor y rechazo persistente | pro ×2 | Producto PASS; pruebas c0: import equivocado, código de empresa en vez de id → r1 PASS | 1 |
| C04-T08 + T08c/T08d | API: filtros, proyección y `/filters` | pro ×2, flash ×3 | Producto PASS; pruebas c0: ayudante inventado y rol nulo → r1: `entity_id` con sufijo (**ambigüedad del encargo de Claude**) → r2 PASS. T08c: AUD-TENANT-01 frente al contrato nuevo de `company_id` (**interacción no prevista por Claude**). T08d: claves del item en COUNT-12 | 2 + 2 reclasificaciones |
| C04-T09 + T09c | Guarda AST | pro ×3, flash | c0: rutas, aserción vacía, `ast.Str` → r1: revisión «contiene» y valores por defecto solo-palabra-clave → r2: un bloque mal formado (rechazado) → T09c PASS | 2 + reclasificación |
| C04-T10 + T10b–e | Pantalla Auditoría | pro ×3, flash ×5 | c0: Entidad ligada a `entity_id`, `select` con `"|"`, Reintentar en el `footer`, foco → r1 (primera respuesta truncada: transporte) → r2: código muerto. T10b: el puente truncó la entrada (transporte). T10c: alerta duplicada. T10d: pruebas antiguas (`action_label` igual a `action`, **encargo de Claude**). T10e: respuesta fuera de contrato | 2 + 4 reclasificaciones (+2 transporte) |
| C04-T11 | Fecha de Reportes › Auditoría y mensajes del analizador | flash | PASS | 0 |
| C04-T12 + T12b/c/d | AUDIT-E2E y SCAN-E2E | pro ×2, flash ×4 | c0: ayudantes inventados, `reason` mal situado y selectores inventados → r1: identidad base y USER → r2 PASS. T12b: inventarios del arnés. T12c: `__dirname` (**encargo de Claude**). T12d: rótulos del detalle (**encargo de Claude**) | 2 + 3 reclasificaciones |
| C04-T13 | Contratos de 001 y 046 | flash | PASS; además corrige la ruta inexistente `/audit/events/{id}` | 0 |

**Coste del ciclo:**
- **42 llamadas facturadas** (21 pro, 21 flash);
- **366 504 tokens de entrada y 159 184 de salida**;
- **0,2392 USD**.

**Contadores:**
- reintentos semánticos: 14;
- rechazos: 15;
- fallos de transporte: 3 (uno sin facturar);
- reclasificaciones: 9.

Rechazos o reclasificaciones atribuibles a Claude, 6:
- T08 r1, ambigüedad del encargo;
- T08c, interacción de contrato no prevista;
- T10d, `action_label` igual a `action` en el encargo T10b;
- T12c, `__dirname`;
- T12d, rótulos sin condición;
- T02c, valores de una familia dinámica mal enumerados en el diseño.

**EGRESS.** EGRESS_OK antes de cada llamada. EICAR nunca salió: la E2E lo lee en ejecución de `qa/clamav_qa.EICAR`. La contraseña sintética del mundo de prueba se sustituyó o se importó, y nunca se envió.
