# COMPANY-SCOPE AUTHORIZATION — orquestación Claude + DeepSeek (2026-10-26/27)

**Reparto del trabajo**
- **Claude:**
  - diseñó el delta `spec003-company-scope-authorization-delta.md` y el inventario de rutas;
  - escribió cada encargo y comprobó su EGRESS con un guion antes de enviarlo;
  - auditó, aplicó las propuestas tal cual, midió las causas raíz y verificó, con sondas y herramientas de mutación fuera del árbol.
- **DeepSeek:** escribió todo el código de producto, todas las pruebas (backend y E2E) y la documentación de producto (contrato y ADR-017).

**Correcciones de formato de Claude** (OD-ORCH-01):
- `ruff --select I --fix` (orden de imports) en `test_approvals.py`, `test_company_scope_derived.py` y las pruebas nuevas.
- Dos bloques de no-op se omitieron al aplicar (`--omitir 2` en TC-11c y TC-11d): eran SEARCH = REPLACE porque el generador de fragmentos de Claude había casado `get_user_permissions(db, user)` dentro del cuerpo del helper. Fallo del encargo, no del ejecutor.

**Valor histórico:**
- no viajó en ningún encargo;
- ningún encargo llevó `.env`, claves, tokens, rutas personales ni datos reales (EGRESS_OK en las 33 llamadas).

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| TC-A1 | Pruebas en rojo C1 (CSA-01..12) | pro / flash | **c0:** código muerto en C06/C07 → c1 PASS.<br>**c2:** variable sin usar → PASS | 2 |
| TC-A2 | Pruebas en rojo C2–C4 (CSS) | pro / flash | **c0:** `UserRole(tenant_id)` inexistente → c1.<br>**c2:** `page_size` 500 > 100 y paso sin `id` (contrato de Claude) → PASS | 2 |
| TC-1 | Funciones de `authority` | flash | **c0:** ruta del bloque sin directorio (encargo de Claude) → c1 PASS | 1 |
| TC-2 | C1 en `get_company_context` | pro | PASS | 0 |
| TC-3 | C2 (aprobaciones) | flash | **c0:** PASS.<br>**c1:** la capacidad se exigía antes que las reglas de dominio (orden de Claude, medido en la suite completa) → se mueve al final → PASS | 1 |
| TC-4 | C3 (bitácora) | flash | **c0:** PASS.<br>**c1:** error de mypy nuevo (`ColumnElement`) → PASS | 1 |
| TC-5 | C4 (11 rutas de catálogo) | flash | **c0:** import sin usar (encargo de Claude) → c1 PASS | 1 |
| TC-7a | Pruebas existentes: `_role_with` con `aprobaciones:approve`, AUD-TENANT-09 con el contrato nuevo | flash | **c0:** PASS.<br>**c1:** el suplente de dos pruebas no tenía la capacidad que ya exigía la ruta (contrato de Claude incompleto) → PASS | 1 |
| TC-A3 | Pruebas en rojo C5 (CSD-01..04) | pro / flash | **c0:** `alta_por_desafio` con usuarios sin permisos sensibles (contrato de Claude) e imports → c1 PASS | 1 |
| TC-11a..e | C5: `capabilities_in_company` y 4 helpers (37 llamadas) | flash | PASS (c y d con un bloque no-op omitido, fallo del encargo) | 0 |
| TC-11f | `capabilities_in_company` en una consulta (presupuesto de consultas, medido en PostgreSQL) | pro | PASS | 0 |
| TC-A4 / A5 / A6 | Pruebas que matan los supervivientes S15/S16, S13 y S16b/S16c | flash | **A5:** inventó `mundo["Session"]` → reintento 1 PASS.<br>**A4 y A6:** PASS | 1 (A5) |
| TC-8 | E2E-SCOPE-01..10 | pro | **c0:** 27/30. SCOPE-10 usaba `activarEmpresa`, que solo sirve con una empresa (contrato de Claude) → c1 con el patrón del selector → 30/30 | 1 |
| TC-9 | Contrato y ADR-017 | flash | **c0:** ADR y tabla PASS. La viñeta del contrato decía «toda petición», impreciso → c1 PASS | 1 |
| TC-6 | Mensaje de UI | — | Reclasificada a deuda UI-PERMISSIONS-NOT-COMPANY-AWARE (§6 del delta) | — |

**Coste del ciclo:** 33 llamadas · 34 631 tokens de entrada · 31 127 de salida · **0,0277 USD**.

**Acumulado de la sesión:** 312 llamadas · 1,0670 USD. El coste del puente (Sonnet) lo factura la sesión de Claude Code.

**Rechazos:** un AUDIT_REJECT (TC-A5 c0: API inventada). Ninguna tarea agotó los dos reintentos. **Implementadas por Claude: 0.**

**Lecciones para los encargos:**
- Un helper de E2E con una precondición implícita, como «una sola candidata», se cita con esa precondición o no se cita.
- Cuando un encargo dice «una sesión», debe dar la forma exacta de abrirla (`mundo.factory()`).
- Un usuario con permisos no sensibles entra sin MFA: el helper de alta debe aceptar las dos respuestas.
- Un cambio en un helper de autorización que se llama en listados tiene presupuesto de consultas. Se mide en PostgreSQL, donde corre la prueba que lo fija.
