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
