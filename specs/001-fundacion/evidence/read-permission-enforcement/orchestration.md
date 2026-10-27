# READ-PERMISSION ENFORCEMENT — orquestación Claude + DeepSeek (2026-10-27)

**Reparto del trabajo**

Claude:
- Descubrió y midió: inventario de las 554 operaciones, matriz de 227 lecturas, consumidores cruzados y servicios.
- Diseñó el delta (AD-1..AD-10, READ-FR-01..15).
- Generó los encargos; los de módulo, con las firmas literales extraídas por guion, con unicidad comprobada.
- Pasó el EGRESS de cada encargo antes de enviarlo.
- Auditó cada parche sobre copia: diff estricto, sintaxis, ruff/mypy, tsc/eslint y la comprobación «solo cambia la dependencia» en los 111 cambios de firma.
- Aplicó solo lo aprobado, tal cual, y verificó con suites, mutaciones y E2E.

DeepSeek escribió todo el código de producto, todas las pruebas (backend, vitest y E2E), el código de QA (`qa/fixtures_de_frontend.py`) y la documentación de producto (ADR-019 y contrato). **Implementadas por Claude: 0.** Claude solo ejecutó el formateador permitido (OD-ORCH-01: `ruff --select I --fix`, orden de imports de T01) y regeneró la instantánea `operaciones.json` con el generador (sin contenido propio).

El anfitrión se reinició a las 19:00 y el directorio temporal del scratchpad se perdió. Las herramientas de Claude se reescribieron (aplicador, extractor, EGRESS, costes) o se recuperaron de la traza de la sesión (mutaciones de 02B/02C, OpenAPI). PostgreSQL de QA se reprovisionó con su orden canónica.

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| T01 | Pruebas en rojo RPE-01..15 | pro | c0: ruff F841 (variable sin uso) → r1 PASS; r1 corrida: 10 pruebas fallaban en el alta MFA porque un usuario sin rol privilegiado entra sin MFA (**el encargo de Claude decía usar siempre `alta_por_desafio`**) → r2 con el helper `_entrar` PASS | 2 |
| T02 | Puerta de completitud del catálogo (AD-7) | pro | PASS | 0 |
| T03..T11 | 104 firmas de lectura en 9 módulos | flash | 9/9 PASS al primer intento; 111/111 líneas difieren solo en la dependencia | 0 |
| T12 | `authority.require_capability` + prueba RCA | pro | producto PASS; prueba c0 rechazada (condición siempre verdadera, `parametrize` de un valor, códigos fijos, sin docstring) → r1 PASS | 1 |
| T13 | Tabla de capacidades por reporte y tablero por indicador | pro | c0: orden de claves alterado y comentario incompleto; r1: orden aún alterado; r2: orden correcto, pero perdió la línea de comentario → **dividida tras agotar reintentos**: (a) bloque 1 de r1 y (b) bloque 2 de r2, ambos auditados y aplicados tal cual | 2 + división |
| T14 | Rutas de `/reporting` (AD-5, AD-6) | pro | PASS | 0 |
| T15 | Inicio: tablero por capacidad + pruebas DSH | pro | c0: condición de sección tautológica → r1 PASS | 1 |
| T16a | Instantánea con `report_capabilities` | flash | PASS | 0 |
| T16b | Centro de reportes por capacidad + CR-01..04 | pro | c0: 6 motivos (cabecera duplicada, `REPORTS` sin exportar, `require` en ESM, `aria-pressed` sobre el estado, clave posiblemente indefinida, aserción con 2 argumentos) → r1 PASS | 1 |
| T16c | Contraste AA de la cabecera de la tabla del Centro | flash | PASS | 0 |
| T17 | Descarga oculta sin `reportes:export` + registro de `reportes/auditoria` + EXP-01..03 | pro | PASS (un bloque SEARCH = REPLACE, sin efecto: desviación de formato) | 0 |
| T19a | NAV-07 con las dos entradas «Auditoría» | flash | PASS | 0 |
| T19b | DSH-03 y READ-E2E-05 sin falso verde de temporización | pro | PASS (F02 muere) | 0 |
| T20 | `test_reporting.py` al nuevo contrato del tablero | flash | PASS | 0 |
| T21 | E2E READ-E2E-01..08 | pro | PASS | 0 |
| T21b | READ-E2E-09 (320 px, axe) | pro | c0: firma de helper inventada (**el encargo de Claude no daba las firmas**) → r1 PASS | 1 |
| T21c | Excluir solo la deuda de `<main>` del shell en axe | flash | PASS | 0 |
| T22 | ADR-019 y contrato | flash | PASS | 0 |
| T-M1 | RPE-16 (trabajos de reporte; mata B12 y B13) | pro | PASS | 0 |

**Coste del ciclo:**
- 35 llamadas (16 pro, 19 flash);
- 99 891 tokens de entrada y 66 804 de salida;
- **0,0720 USD**;
- todas terminaron en `stop`.

El coste del puente (Sonnet) lo factura la sesión de Claude Code.

**Rechazos (AUDIT_REJECT): 8** (T01 2, T12 1 —solo su prueba; el producto se aceptó—, T13 2, T15 1, T16b 1, T21b 1). El reintento 2 de T13 se aceptó en parte y la tarea se dividió:
- Todos con motivo concreto y contexto completo en el reintento.
- **Atribuibles a Claude: 2**, ambos de encargos que no daban el contexto real: T01 r1 (helper de alta MFA) y T21b c0 (firmas de helpers).
- Ninguna tarea pasó de dos reintentos; T13 se dividió.

**Defectos de prueba que encontró la campaña de mutaciones, y su origen:**
- **F02**: falso verde de temporización en DSH-03. **Origen: encargo de Claude**, que pedía comprobar tras la llamada y no tras la respuesta. El mismo patrón estaba en READ-E2E-05.
- **B12/B13**: el encargo de T01 de Claude no cubría los trabajos de reporte.

Los dos los corrigió DeepSeek (T19b, T-M1).

**Lecciones para los encargos:**
- Dar SIEMPRE las firmas reales de los helpers que la prueba debe usar.
- La ausencia de algo en la UI se comprueba después de una señal de que la respuesta llegó, nunca justo tras la petición.
- Un usuario sin rol privilegiado no pasa por MFA: el helper de entrada lo distingue.
- Los encargos con texto entre comillas invertidas se escriben con heredoc entrecomillado o desde Python. Este error de Claude se detectó antes de enviar el encargo de T13.
