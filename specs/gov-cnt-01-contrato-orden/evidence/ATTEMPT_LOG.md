# CNT-01 · Registro de intentos de DeepSeek

- **Modelo:** todo con `deepseek-v4-pro`, sin `session_id` ni `thinking` y con `max_tokens` explícito.
- **Antes de cada llamada:** `EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0`.
  - Las coincidencias de «Secret» en el brief E eran «Secretaria de la Comisión»: falsos positivos revisados.
- **Topes:** 8 llamadas por ciclo como máximo y 2 reintentos por subproblema.
  - La dueña autorizó **una llamada extra** el 2026-11-14 para dos guardas de Vitest y la regresión de PROC-08 (llamada 9).
  - El 2026-11-15 autorizó **otra** para el downgrade de la migración (llamada 10). `OWNER_EXCEPTION_USED=2`.

| Llamada | Subproblema | Tokens (entrada/salida) | Coste | Resultado |
|---|---|---|---|---|
| 1 | T002 · modelo, migración 0113, clasificador AAL generalizado, permisos, MFA, catálogo, CTL-01 y recuentos | 7742/11127 | $0,013048 | **AUDIT_PASS**: 18 bloques exactos; upgrade, downgrade y upgrade en PG; AAL 12/12 sin cambio. Faltaba un recuento (STANDARD 76 → 78), que era omisión del brief y se agregó a la llamada 2 |
| 2 | T003 · servicio, esquemas, API, router y enlace en la decisión | 10592/13910 | $0,016709 | **AUDIT_REJECT**: dos `NameError` (imports), un 500 seguro al formalizar (`getattr(c, "documento_id")`), oferta `None` sin tratar y 31 errores nuevos de mypy |
| 3 | B·R1 · 33 ediciones | 2892/3010 | $0,003877 | **PASS parcial**: queda `from typing import Any` (quitado en `api_contratos.py`) |
| 4 | B·R2 (import `Any`) + T004 pruebas backend | 6631/9133 | $0,010830 | B: **AUDIT_PASS** (ruff limpio, mypy en 157). T004: **REJECT**, 7/13; los 6 fallos son de la prueba. Uno se debe al brief: `cuenta_con_permisos` recibe tuplas |
| 5 | C·R1 · 12 ediciones | 2036/1655 | $0,002326 | **AUDIT_PASS**: 13/13 en PG, ruff limpio y 121 aserciones; las 5 mutaciones mueren |
| 6 | T005 frontend + Vitest | 6343/18315 | $0,018693 | **PASS parcial**: las pantallas funcionan. Imports sin usar, importación cruzada entre pruebas y 2 selectores ambiguos |
| 7 | D·R1 (6 ediciones) + T006 E2E (con 3 anexos de patrones) | 14662/14983 | $0,019413 | D: **AUDIT_PASS** (typecheck, lint y Vitest). T006: **REJECT** en la sonda; ver la tabla siguiente |
| 8 | E·R1 + D·R2 + T003b (año sin UUID) | 4495/4914 | $0,006231 | **AUDIT_PASS**: 40 bloques exactos; E2E en verde a la primera, con 0 reintentos; typecheck, lint y Vitest en verde |
| 9 | Excepción de la dueña: G1 `pantallas.ts` (2 rutas), G2 QC-02 (nombres literales) y G3 regresión E2E de PROC-08 (el párrafo retirado se sustituye por el encabezado del panel) | 1099/490 | $0,000904 | **AUDIT_PASS**: 3 bloques exactos; Vitest 2044/2044, typecheck, lint y build en verde; E2E de decisión y contratos 2/2 |
| 10 | 2.ª excepción de la dueña: H1, simetría del downgrade de permisos de la migración. Antes solo borraba la asignación a FUNCIONAL_COMPLETO; ahora borra todas, como 0112 y 0113. Lo destapó el downgrade de la UAT al reencadenar tras TRE-09 | 828/358 | $0,000672 | **AUDIT_PASS**: 1 bloque exacto; ruff limpio; up/down/up en PG con un rol extra |

**Sonda E2E de Claude (temporal y retirada).** Antes de la llamada 8, Claude ejecutó la E2E de DeepSeek y aplicó correcciones mínimas *temporales* para descubrir todos los fallos de una vez. Después restauró los ficheros exactos de DeepSeek, verificados por huella.

| Fallo encontrado | Causa | Parte |
|---|---|---|
| 422 `credito_id` requerido | La respuesta del crédito es el ejercicio con `creditos[]` | E2E |
| 404 al registrar garantía | Ruta sin `/expedientes/{id}`; la respuesta es el estado con `requisitos[]` | E2E |
| Timeout en el selector de documento | 7 opciones con la misma etiqueta | E2E |
| Firmante elegido por etiqueta parcial | Hay que elegir por valor | E2E |
| «Modificado por otro usuario» | Se guardaba sin esperar la respuesta anterior y los botones no se bloqueaban | E2E + **producto** |
| **UUID en la columna «Ejercicio»** | `anio = year_id` | **Producto (backend)** |
| Panel del expediente en «Borrador» tras formalizar | Caché sin invalidar | **Producto (frontend)** |
| Axe `scrollable-region-focusable` a 390 y 320 | Tablas desplazables no enfocables | **Producto (frontend)** |
| Selectores con varias coincidencias | Modo estricto de Playwright | E2E |

```text
DEEPSEEK_CALLS=10 (8 + 2 excepciones de la dueña)  GLOBAL_CALL_HARD_CAP=8  GLOBAL_CAP_REACHED=1  OWNER_EXCEPTION_USED=2
DEEPSEEK_RETRIES=6 (B·R1, B·R2, C·R1, D·R1, D·R2, E·R1)  MAX_RETRIES_SINGLE_SUBPROBLEM=2 (T003 y T005)
COSTE_TOTAL=$0,092703 (8 llamadas: $0,091127 + llamada 9: $0,000904 + llamada 10: $0,000672)
```

**Mutaciones** (`service_contratos.py`). La huella se restauró igual: `9202e61ccd0d`. Las pruebas son posteriores a K1, pero las anclas mutadas no cambian.

| Mutación | Prueba que la mata |
|---|---|
| M1: adjudicación siempre vigente | `test_vector_b_adjudicacion_no_vigente` |
| M2: sin control de moneda de la CDP | `test_vector_g_moneda_distinta` |
| M3: sin bloqueo por el límite del firmante | `test_vector_f_autoridad_insuficiente` |
| M4: sin exigir cobertura completa | `test_vector_d_cobertura_insuficiente` |
| M5: CDP anulada aceptada | `test_vector_e_cdp_anulada` |

**Implementado por Claude:**
- **Diseño:** arqueología, Spec, plan, gate y tareas.
- **Briefs y auditoría:** briefs, auditoría y aplicación literal de los parches.
- **Herramienta:** aplicador corregido para crear directorios nuevos.
- **Verificación:** sondas temporales (retiradas), mutaciones (restauradas) y fixtures OpenAPI regeneradas.
- **Evidencia:** documentos y matrices.

Ninguna línea de producto, prueba, E2E ni migración es de Claude.
