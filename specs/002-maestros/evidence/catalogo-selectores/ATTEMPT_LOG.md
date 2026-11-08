# CATALOGO-SELECTORES-PRIMERA-PAGINA-01 · registro de intentos

Las llamadas fueron secuenciales, nunca en paralelo, y no hubo commits en rojo. Cada fila es una llamada a DeepSeek mediante `deepseek-executor`.
Un ajuste de pruebas dentro de la misma frontera cuenta como reintento de su subtarea. Solo se abrió una subtarea
nueva cuando había `NEW_ROOT_CAUSE` o `NEW_TECHNICAL_BOUNDARY` documentados.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| CAT-A prueba roja de pantallas | ATTEMPT | flash | NOT_RECOVERED | AUDIT_PASS; 43 en rojo, reproducido |
| CAT-C pruebas canónicas del componente | ATTEMPT | flash | $0,001550 | AUDIT_REJECT: `rerender` duplicaba el árbol, tipo de `alCambiar`, `_omitir` sin uso |
| CAT-C | RETRY_1 | flash | NOT_RECOVERED | AUDIT_PASS; CC-05 quedó con un error de la prueba |
| CAT-D componente | ATTEMPT | flash | $0,004774 | AUDIT_REJECT: etiqueta no atada al id y «Mostrando» siempre visible |
| CAT-D | RETRY_1 | flash | $0,001195 | AUDIT_PASS; las pruebas revelaron `isFirstPageError` |
| CAT-D | RETRY_2 | flash | $0,000345 | Sin bloques: presupuesto agotado |
| CAT-D | OWNER_EXCEPTION | flash | $0,000132 | Autorizada por la dueña («Una llamada extra»), acotada a `isFirstPageError`. AUDIT_PASS |
| CAT-D2 opción interactiva | ATTEMPT | flash | $0,000167 | NEW_ROOT_CAUSE previo al ciclo (`git show ea22171`): la opción no era interactiva. AUDIT_PASS |
| CAT-C | RETRY_2 | flash | $0,000210 | AUDIT_PASS; CC-05 espera antes de cada clic. Presupuesto cerrado |
| CAT-E inventario (7 pantallas) | ATTEMPT | flash | $0,001464 | AUDIT_PASS; 28 bloques |
| CAT-F compras (4 pantallas) | ATTEMPT | flash | $0,000897 | AUDIT_PASS; 16 bloques |
| CAT-G ventas (3 pantallas) | ATTEMPT | flash | $0,000740 | AUDIT_REJECT: tres bloques sin `=======` |
| CAT-G | RETRY_1 | flash | $0,000768 | AUDIT_PASS; 12 bloques |
| CAT-A | RETRY_1 | flash | $0,000245 | Mock de presentaciones con forma paginada en lugar de lista: error no controlado y Vitest con RC 1. AUDIT_PASS |
| CAT-H pruebas de supervivientes | ATTEMPT | pro | $0,003524 | NEW_TECHNICAL_BOUNDARY: fase de mutación, fichero nuevo. AUDIT_REJECT: sin `QueryClientProvider`, ruta inventada, `vi.resetModules` |
| CAT-H | RETRY_1 | pro | $0,005112 | AUDIT_PASS; S-04 en rojo con el código actual |
| CAT-H | RETRY_2 | flash | $0,000208 | AUDIT_PASS; S-04 pasa pero no mata M4. Presupuesto cerrado |
| CAT-A | RETRY_2 | flash | $0,000185 | Auditoría propia tardía: `setTimeout(50)` prohibido. AUDIT_PASS. Presupuesto cerrado |
| CAT-I E2E preparada | ATTEMPT | flash | $0,000924 | AUDIT_REJECT: verde falso (servicio no creado) y Spec equivocada |
| CAT-I | RETRY_1 | flash | $0,001272 | AUDIT_PASS; compila con TSC. Preparada, sin ejecutar: no hay PostgreSQL |

| CAT-C | OWNER_EXCEPTION | flash | $0,000257 | CC-18 era inestable: tabulaba sobre la lista sin filtrar, que se desmontaba. La dueña autorizó una llamada extra («Una llamada extra»). AUDIT_PASS; dos suites completas en verde |

Total: 21 llamadas. Coste conocido de 19 de ellas: $0,023969; las otras 2 son `NOT_RECOVERED`. Reintentos: 10, más dos
excepciones de la dueña (CAT-D y CAT-C). Parches rechazados en auditoría: 5 (CAT-C, CAT-D, CAT-G, CAT-H y CAT-I en su primer intento); hubo
además una respuesta vacía (CAT-D RETRY_2). Presupuestos cerrados: CAT-A, CAT-C, CAT-D y CAT-H.

## Notas

- **Defecto del aplicador local, no del ejecutor.** Un REPLACE vacío dejaba una línea en blanco en las 7 pantallas de
  CAT-E. Claude quitó esas 7 líneas (ajuste mecánico) y corrigió el aplicador antes de CAT-F.
- **Error de auditoría de Claude.** El `setTimeout(50)` de CAT-A pasó la primera auditoría y se detectó al revisar las
  pruebas para la fase de mutación. Se pagó con el último reintento de CAT-A.
- **Error de brief de Claude.** El brief de CAT-H recortó con «...» las líneas de import del patrón, y eso explica en parte
  la ruta inventada del primer intento.
- **Superviviente aceptado: M4** (la clave de caché sin empresa). El mock resuelve la búsqueda nueva antes de la
  aserción, así que la caché antigua no llega a verse. S-04 pasa con el código y con el mutante, de modo que **no demuestra
  lo que dice su nombre**. CAT-H agotó su presupuesto y no se reabre con otro nombre.
- **Costes NOT_RECOVERED:** dos llamadas anteriores a la compactación del contexto no dejaron una línea `USAGE`
  recuperable.

## CATALOGO-SELECTORES-CONVERGENCIA-02 (2026-11-07)

La dueña corrigió la clasificación anterior porque el mutante requerido M4 seguía vivo y ProductoNuevoPage no tenía una
prueba directa. Los presupuestos de CAT-A, C, D y H siguen cerrados. Hay dos subtareas nuevas:

- **CAT-J1:** `NEW_ROOT_CAUSE = MUTATION_TEST_DOES_NOT_OBSERVE_CACHE_SCOPE_ISOLATION`.
- **CAT-J2:** `NEW_TECHNICAL_BOUNDARY = SHARED_COMPONENT_CONSUMER_REGRESSION_NOT_DIRECTLY_CERTIFIED`.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| CAT-J1 aislamiento de caché | ATTEMPT | pro | $0,005651 | AUDIT_REJECT: `children(value)` con tipo `ReactNode`, `vi.doMock`, espera de llamada trivial en CACHE-03 que dejaba vivir al mutante, MemoryRouter sobrante |
| CAT-J1 | RETRY_1 | pro | $0,006509 | AUDIT_PASS; 6 de 6. M4 lo matan CACHE-01, 02, 03 y 06; M4b lo mata CACHE-05. El puente recortó solo la sección «intento anterior» del brief (desviación registrada) |
| CAT-J2 ProductoNuevoPage | ATTEMPT | pro | $0,004676 | AUDIT_REJECT, 6 de 7 en rojo: `within` sin uso, etiqueta exacta «Código» (el brief de Claude no avisaba del « * (obligatorio)»), PN-02 tomaba la búsqueda q="" |
| CAT-J2 | RETRY_1 | pro | $0,006131 | 4 de 7 en rojo. PN-02 seguía siendo un error de la prueba. PN-04, 06 y 07 destaparon un **defecto preexistente**: doble POST y navegación bloqueada |
| CAT-J2 | RETRY_2 | pro | $0,003809 | AUDIT_REJECT: un SEARCH ambiguo (coincidía con PN-06 y PN-07) y `findPostCall` sin uso. STOP |
| CAT-J2 | OWNER_EXCEPTION | pro | $0,004620 | Autorizada durante el ciclo («Una llamada extra»). Fichero completo; AUDIT_PASS; 7 de 7 |

Total del microciclo: 6 llamadas, $0,031396; 3 reintentos y 1 excepción de la dueña.

- **Defecto preexistente enrutado:** no se arregla aquí y la prueba no lo oculta. Las pruebas PN certifican el contrato del Rubro; la navegación y el número de POST pertenecen a la prueba roja del defecto nuevo.
- **Residuo:** el nombre de PN-04 aún dice «y navega al listado», pero ya no lo comprueba. Se corrige en el ciclo del defecto.
