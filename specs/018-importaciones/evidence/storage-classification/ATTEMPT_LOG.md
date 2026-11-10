# SPEC018_CLASIFICACION_ZONA_ETIQUETADO · registro de intentos

Llamadas secuenciales a `deepseek-v4-pro` con `stream=true`. Presupuesto del encargo: 6 llamadas, objetivo 4. La dueña autorizó 5 extra, una a una y con el diagnóstico listo: **11 en total**. Todo el código, las pruebas y las migraciones los propuso DeepSeek; Claude diseñó, auditó, aplicó y certificó. Las correcciones de medición se hicieron solo en copias temporales, y el fichero se restauró después comprobándolo por md5. El ciclo se suspendió el 2026-11-10 por traslado de la dueña y se retomó el mismo día; al retomarlo, P1 había publicado PROC-07.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | T-SC-A motor completo | 12767/32620 | $0,033933 | Aplicada. Motor con 3 defectos (orden de reglas, razones de descarte, concurrencia: esta última, laguna del contrato de Claude). Pruebas con 7 defectos, uno de ellos un falso verde (skipif con una variable inventada) |
| 2 | T-SC-A reintento 1 | 4544/4118 | $0,005559 | Correcciones aplicadas tras normalizar solo los delimitadores (DeepSeek copió «/» del brief: error de formato de Claude). Faltó inicializar `discarded` |
| 3 | T-SC-A reintento 2 + T-SC-B (dos tareas, autorizado) | 10740/13099 | $0,016068 | Motor: 15 de 15. Expediente y etiqueta: importaciones que faltaban, atributo inexistente, candidatas como objetos ORM |
| 4 | T-SC-B reintento 1 + T-SC-C frontend (dos tareas, autorizado) | 11617/24405 | $0,026286 | Backend de B en verde. Frontend con defectos: ruta de autorización inventada, módulo de descargas inexistente, manejadores no asíncronos |
| 5 | T-SC-C reintento 1 | 7865/5669 | $0,008353 | Quedan un `</div>` huérfano, `SelectAlmacen` sin `id` y la política sin opción vacía |
| 6 | T-SC-C reintento 2 + T-SC-D E2E (dos tareas, autorizado) | 3639/2760 | $0,003984 | Se borró el `</div>` equivocado; `fila` redeclarada en la E2E |
| 7 | Correcciones finales (extra 1) | 1815/1744 | $0,002307 | JSX bien cerrado, volumen vacío como `null`, carrera de la política. E2E PASS a 1280, 390 y 320 |
| 8 | Migración de fusión con PROC-07 + 2 pruebas Vitest (extra 2, dos tareas) | 1218/776 | $0,001205 | AUDIT_PASS. `0093_fusion_gov_storage`; Vitest 461 de 461 |
| 9 | Autoridad única de almacenes (extra 3) | 2709/2237 | $0,003125 | AUDIT_REJECT: quitó importaciones en uso; el aplicador de Claude no detectó los bloques mal formados (ya endurecido) |
| 10 | Reintento 1 (extra 4) | 1189/765 | $0,001183 | AUDIT_REJECT: importación duplicada con una ruta inexistente y aviso dentro del FormField (rompía la etiqueta) |
| 11 | Reintento 2 (extra 5) | 779/573 | $0,000837 | AUDIT_PASS. Vitest 1868 de 1868; E2E PASS a 1280, 390 y 320 |

**Total:** 11 llamadas, $0,102840. Rechazos completos: 9 y 10. Las llamadas 3, 4, 6 y 8 llevaron dos tareas, con la autorización de la dueña. Implementado por Claude: ninguna línea de producto, de pruebas ni de migración. Claude hizo además la resolución mecánica de los conflictos de la fusión (contadores y cabezas tomadas de P1, que DeepSeek apuntó después a `0093`) y la negación en `.gitignore`.
