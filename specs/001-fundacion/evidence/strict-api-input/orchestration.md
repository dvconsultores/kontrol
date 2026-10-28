# STRICT API INPUT (05) — orquestación Claude + DeepSeek (2026-10-28)

## Reparto del trabajo

Claude:
- hizo la arqueología con sondas en el scratchpad, sin confirmar: inventario de rutas con `get_flat_dependant`, barrido de línea base, inventario de instantes y de consultas de la UI, y un worktree desacoplado de HEAD para atribuir los fallos E2E preexistentes;
- diseñó AD-1..AD-9, PDD-API-11 y PDD-API-12, y redactó los encargos;
- pasó el EGRESS antes de cada llamada;
- auditó, aplicó tal cual, midió rojo y verde y certificó;
- escribió el delta, la evidencia y la enmienda de ADR-020 (artefactos de diseño);
- regeneró las instantáneas del frontend con su generador (paso mecánico).

DeepSeek escribió todo el código de producto, todas las pruebas (pytest, vitest y Playwright), los cambios de los guiones QA y los contratos. **Implementado por Claude: 0.**

**Formato aplicado por Claude (OD-ORCH-01, informado):** `ruff --select I001 --fix`, que solo reordena imports, en `approvals/api.py`, `master_data/api.py`, `inventory/api.py` y cuatro ficheros de prueba nuevos.

## Tareas

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| C05-T01 | Rojo del contrato de consulta | pro ×2 | c0: `rol_operador.__wrapped__` (ambigüedad del encargo de Claude), sustitución de `{param}` rota y guarda de lectores demasiado amplia (`db.query`) → r1 PASS | 1 |
| C05-T02 | Mecanismo central `query_contract.py` y `main.py` | pro | PASS | 0 |
| C05-T03 | Rojo de instantes | pro ×2 | c0: prefijo `/api/v1` duplicado, `from __future__` frente a la app sintética e import y recorrido de la guarda erróneos → r1 PASS | 1 |
| C05-T04a | `InstanteDeEntrada` y manejador de `NAIVE_DATETIME` | pro | PASS | 0 |
| C05-T04b | Tipo aplicado a los 16 campos (21 bloques) | flash | PASS | 0 |
| C05-T05 | Búsqueda de Existencias (backend) | pro ×2 | Producto PASS. Pruebas c0: usuario creado y usuario con sesión distintos, `company_id` del rol y E-07 ambiguo (**encargo de Claude**) → r1 PASS | 1 |
| C05-T06 | Pantalla de Existencias | pro ×2 | Producto PASS. Pruebas c0: F-07 exigía igualdad y F-06 montaba dos veces → r1 PASS | 1 |
| C05-T07 | `company_id` obsoleto en 7 llamadas | flash | PASS | 0 |
| C05-T08 | Instantánea con `query` | flash | PASS | 0 |
| C05-T09 | Guarda de frontend | pro ×2 + T15 | c0: la ruta dinámica contaba como violación, ternario muerto y precedencia sin paréntesis → r1 PASS; después tsc (`JsxAttributeName`) → T15 | 2 |
| C05-T10 | Clientes E2E y QA | flash + T15 | PASS; después tsc (`c` sin uso) → T15 | 1 |
| C05-T11 | Búsqueda de taxonomía (Rubro), hallazgo de la guarda | pro ×2 | Producto PASS. Pruebas c0: función de prueba pasada como `reloj` (**encargo de Claude**: no nombraba `reloj_mfa`) e import y uso de `crear_usuario` → r1 PASS | 1 |
| C05-T12 | QUERY-422-E2E, EXISTENCIAS-E2E y RUBRO-E2E | pro ×2, flash | c0: promesa pasada a `expect` → r1 PASS. r1 falló en E2E: espera de red con `staleTime: 30 000` (**encargo de Claude**) → r2 PASS | 2 |
| C05-T13 | Contratos de error y de API | flash | PASS | 0 |
| C05-T14 | Pruebas del backend con el contrato antiguo | flash ×2 | c0: aplicado; EMP-Q-16 conservaba una línea que su fragmento omitió (**error de Claude**) → r1 PASS. Observación sin rechazo: `?&` inocuo | 1 |
| C05-T15 | Corrección de tsc (T09 r2 y T10 r1) | flash | PASS | — |

## Contadores

| Concepto | Valor |
|---|---|
| Llamadas facturadas | **25** (16 pro, 9 flash) |
| Tokens | **118 699 de entrada y 69 591 de salida** |
| Coste | **0,0957 USD** |
| Reintentos semánticos | 11 |
| Rechazos | 11 |
| Fallos de transporte | 0 |
| Reclasificaciones | 1 (T15 agrupa dos correcciones de tipos) |
| Atribuibles a Claude | **5** (T01 R1, T05 R3, T11 R1, T12 r2 y T14 r1) |

## EGRESS

EGRESS_OK antes de cada llamada.
- Ningún fichero con la contraseña sintética salió: se dieron firmas reales y extractos, nunca `mfa_mundo.py` entero.
- Las tres apariciones `process.env.KONTROL_E2E_*` del encargo T12 son nombres de variables, sin valores: falso positivo de la expresión regular, revisado.
- EICAR nunca salió.
