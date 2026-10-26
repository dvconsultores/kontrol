# DELEGATION CEILING — orquestación Claude + DeepSeek (2026-10-26)

**Reparto del trabajo:**
- **Claude** diseñó (el delta `spec003-delegation-ceiling-delta.md`), escribió cada encargo y comprobó su EGRESS con un guion antes de enviarlo. Después auditó, aplicó las propuestas tal cual, midió las causas raíz (con sondas temporales de diagnóstico fuera del árbol) y verificó.
- **DeepSeek** escribió todo el código de producto, todas las pruebas, la migración `0060`, el frontend, la E2E, el guion de QA `qa/rol_con_permisos.py` y la documentación de producto (contrato y ADR-016).

**Correcciones de formato de Claude** (OD-ORCH-01): `ruff --select I --fix` (orden de imports) en las pruebas nuevas `test_delegation_*.py` y en `conftest_multicompany.py`.

**Decisiones de la dueña en el ciclo:** OD-DEL-10 (separar técnico y funcional), OD-DEL-11 (deuda aparte para el alcance por ruta) y OD-DEL-12 (administrador inicial con alcance de tenant).

**Valor histórico:**
- No viajó a DeepSeek en ningún encargo.
- El patrón `rol_sin_permiso.py` se envió con el valor enmascarado (`<SEMILLA_HISTORICA>`).
- El guion nuevo no lo contiene (comprobado con un guion).

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| TD-A1a | Pruebas en rojo del techo al asignar y quitar (DC) | pro / flash | **c0:** contenido correcto, docstring de marcador → c1 PASS.<br>**c2:** P03 contradecía el orden de reglas (contrato de Claude) → PASS | 2 |
| TD-A1b | Pruebas en rojo del alta de roles y del listado (DCR) | pro | **c0:** pasaba el id en lugar del nombre a `alta_por_desafio` (brief ambiguo de Claude); permisos tratados como objetos → c1 PASS | 1 |
| TD-A1c | Pruebas en rojo del alcance de empresa (DSC) | pro | **c0:** el mismo error de `alta_por_desafio`; eventos comparados por identidad → c1 PASS | 1 |
| TD-A1d | Pruebas en rojo del último administrador (DLA) | pro | **c0:** `alta_por_desafio`, `UserRole(tenant_id)` inexistente, orden de L04.<br>**c1:** contenido correcto.<br>**c2:** la carrera cruzada no aislaba el invariante (diseño de Claude, medido en PostgreSQL) → L04/L05 → PASS | 2 |
| TD-A2 | Pruebas de la migración `0060` (PostgreSQL) | pro / flash | **c0:** R05 no ejecutaba el downgrade → c1 PASS.<br>**c2:** el catálogo de 0059 no tiene solo 7 permisos (contrato de Claude) → bloque 1 erróneo → se divide en TD-A2d → PASS | 2 |
| TD-1a | División de ADMIN en `setup` y constantes de `authority.py` | pro / flash | **c0:** PASS.<br>**c1** (seguridad: la búsqueda del rol protegido no filtraba `protected`): un SEARCH con una errata → **c2** PASS | 2 |
| TD-1b | Migración `0060` | pro / flash | **c0:** correcta salvo el filtro `protected = true` (riesgo de escalada) → c1 PASS | 1 |
| TD-2a | Funciones de autoridad efectiva | pro | **c0:** lógica correcta; faltaba `NoReturn` y había dos errores de mypy → c1 PASS | 1 |
| TD-2b | Integración en asignar, quitar y crear rol; candado; corrección del 500 al renunciar | pro | PASS | 0 |
| TD-3 | API: listado del tenant con `delegable`/`motivo`; `extra="forbid"` | flash | PASS | 0 |
| TD-4 | Pantalla Roles y 7 vitest | pro | **c0:** pantalla correcta; las pruebas pisaban el mock y los localizadores no estaban anclados; `in` sobre el prototipo → c1 PASS | 1 |
| TD-4b | Contraste WCAG AA (`text-text-400` → `text-text-500`), medido por axe en la E2E | flash | PASS | 0 |
| TD-5a..e | Pruebas existentes afectadas por la división de ADMIN (mundos «con todo», cabeza de Alembic, ROLE-16, migraciones 0024/0043/0047) | flash | PASS (5a con una observación de estilo) | 0 |
| TD-6a | Guion de QA `rol_con_permisos.py` (sin literal de contraseña) | flash | PASS | 0 |
| TD-6b | E2E-DEL-01..07 | pro | **c0:** variables sin usar.<br>**c1:** inventó un token en localStorage → rechazado.<br>**c2:** PASS (observación: `page.request`) | 2 |
| TD-6c | Subtarea dividida: localizador del encabezado; DEL-06 con 401 SESSION_REVOKED (contrato de Claude corregido) | pro | PASS | 0 |
| TD-6d | Subtarea dividida: menú plegado a 320 px (deuda del shell), token nuevo tras la interfaz, cuerpos en las aserciones | pro | PASS | 0 |
| TD-7 | Contrato de API y ADR-016 | flash | PASS | 0 |
| TD-6e1..e5 | Arnés QA para la E2E canónica. El mundo N6 recibe FUNCIONAL_COMPLETO. Se crea `admintenant`, administrador de QA de todo el tenant (el `admin` E2E tiene alcance declarado solo en D1 y el techo le impide, como debe, conceder autoridad sobre D2), con sus clones y su línea base. El recuento de usuarios del arnés pasa a 42 | flash | **e1:** un bloque no aplicable porque el fragmento de Claude acababa a mitad de línea → c1 PASS.<br>**e2:** constante sin usar → c1 PASS.<br>**e4:** la siembra exigía la clave sin fuente común → se usa `n6_world.PASS` | 1 en e1 y en e2 |
| TD-6f / 6g | Verificador «con todo» de la cadena de ventas y usuario de notificaciones: ADMIN + FUNCIONAL_COMPLETO | flash | PASS (6f se reenvió tras un `Request timed out` de red, que no cuenta como reintento) | 0 |
| TD-6h | Inventario de llamadas a `ejecutarPython`. Faltaba `password-reset.spec.ts`, del ciclo anterior: el vitest ya estaba en rojo en `464c913` y no se detectó al cerrar ese ciclo | flash | PASS | 0 |
| TD-A3 / A3b | Pruebas que matan D08, D13 y D17 (DSC-C01, DC-U01, DLA-L06 con intercalado forzado) | flash | **A3:** bloque 2 con `actor` como objeto → c1 PASS.<br>**A3b:** SEARCH de import no aplicable → c1 PASS | 1 cada una |

**Mutaciones:** 21 de 21 muertas (`mutaciones.md`).

**Rojo atribuido:** `rojo-td-a1a.txt` y `rojo-td-a1.txt`.

**Reproducción antes y después:** `reproduccion.txt`.

**Coste del ciclo:** 52 llamadas contadas por la herramienta · 86 700 tokens de entrada · 79 179 de salida · **0,0906 USD**.

**Coste acumulado de la sesión:** 279 llamadas · 1,0392 USD. El coste del puente (Sonnet) lo factura la sesión de Claude Code.

**Lecciones para los encargos:**
- Nombrar sin ambigüedad cada argumento de las APIs de prueba. Por ejemplo: «el tercer argumento de `alta_por_desafio` es el NOMBRE de usuario».
- Medir el catálogo real antes de fijar contratos sobre él.
- Una carrera entre dos operaciones rápidas solo se prueba forzando el intercalado.
- La renuncia que cambia la clase de MFA revoca la sesión: en la prueba es un 401, no un 403.
- El token de API previo a `entrarComoUsuario` no sobrevive a la renovación del navegador.
