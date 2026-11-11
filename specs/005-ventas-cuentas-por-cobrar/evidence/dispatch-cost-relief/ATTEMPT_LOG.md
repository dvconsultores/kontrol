# DISPATCH-COST-RELIEF · registro de intentos

Todo con `deepseek-v4-pro` y `stream=true`, con briefs autocontenidos de 55 KB como máximo. **Presupuesto:** objetivo 2 llamadas, máximo 4, y máximo 2 reintentos por subproblema. **Usados:** 3 llamadas (backend, pruebas backend y E2E) y 3 reintentos, en 6 envíos.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | Backend: motor con desglose, instantánea, migración 0098, alivio en el despacho, reposición en la devolución, guardias, pruebas | 11318/7789 | $0,011700 | AUDIT_REJECT completo. Editaba las migraciones publicadas 0096 y 0097 y no tocaba las guardias. La instantánea se creaba antes del movimiento, con `movement_id=""`. Faltaban: la nueva comprobación tras el bloqueo, el fallo cerrado de AVERAGE parcial y varios imports. Cambiaba el comportamiento por defecto de los helpers, un SEARCH no coincidía y las pruebas estaban rotas |
| 1·R1 | El mismo encargo con los 11 motivos de rechazo | 13922/9682 | $0,014479 | Código de producto, migración, guardias y helpers: AUDIT_PASS y aplicados. Fichero de pruebas: AUDIT_REJECT (usaba una fixture `db` inexistente, claves inventadas, una aserción vacía y una sesión compartida entre hilos) |
| 2 | Causa nueva medida: el catálogo de auditoría rechazaba la clave `cost`. Se corrigen D1 a D5 y se reescriben las pruebas | 11849/6879 | $0,011139 | D1 a D5: AUDIT_PASS. Pruebas: 6 fallos medidos en PostgreSQL, por defecto de la prueba (no pasaba `cantidad`) |
| 2·R1 | Correcciones de las pruebas sobre fragmentos | 5055/1438 | $0,003450 | 9 de 10 bloques aplicados. El de aislamiento se rechazó porque su SEARCH no coincidía. 10 de 11 PASS |
| 2·R2 | Expectativa de V2 (una fila por capa), E741 y aislamiento por empresa | 1690/846 | $0,001471 | AUDIT_PASS, 8 de 8 bloques |
| 3 | E2E: landed cost vigente → despacho → V1 = V0 − costo consumido | 3443/1684 | $0,002963 | AUDIT_PASS. E2E PASS en Chrome sobre PostgreSQL |

**Total:** 6 envíos, $0,045202.

**Implementado por Claude:** ninguna línea de producto, de prueba ni de migración. Claude hizo:
- el delta, con la fórmula, la escala, el contrato y los vectores fijados antes de delegar;
- la auditoría;
- las mediciones;
- la evidencia y la tarjeta.

**Bloques rechazados y no reparados a mano:** los de la llamada 1, las pruebas de 1·R1, y el bloque de aislamiento de 2·R1, que se volvió a pedir en 2·R2.

**Error de Claude:** en la primera redacción de los pasos 86 y 88 de la tarjeta afirmé que la pantalla Valorización filtra por artículo y que la pestaña Costos muestra la cantidad restante. Ninguna de las dos cosas estaba medida, así que lo corregí antes de publicar.
