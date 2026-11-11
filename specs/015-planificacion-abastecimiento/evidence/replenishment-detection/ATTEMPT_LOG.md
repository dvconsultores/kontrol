# SPEC015_AUTOMATIC_REPLENISHMENT_DETECTION · registro de intentos

Llamadas a `deepseek-v4-pro` con `stream=true`, una cada vez y con su brief autocontenido.

**Presupuesto del encargo:** máximo 5 llamadas, objetivo 3, ninguna solo de pruebas. **Usadas: 5.**

- La 4 corrige una regresión que introdujo la 3 y los defectos que solo aparecieron al ejecutar la E2E en Chrome.
- La 5 corrige el contrato de orden del registro, que solo reveló la suite completa.
- Las dos son causas nuevas, demostradas por una ejecución real.
- Todo el código, las pruebas y la migración los propuso DeepSeek.
- Claude diseñó, auditó, aplicó y certificó.
- Las correcciones de medición se hicieron solo en copias temporales y en sondas fuera del repositorio.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | Backend: dominio, migración 0096, servicio, manejador del planificador, alerta (Spec 047), API, trazabilidad y pruebas | 13274/21549 | $0,024522 | Aplicada salvo 1 bloque, que importaba en `registry.py` con un ancla inventada. Se normalizó el marco de un bloque cuya ancla cortó el contexto del brief de Claude. Defectos medidos: rutas de la API (dependencia inventada, prefijo duplicado, imports), `created_by` en dos modelos que no lo tienen, falta el import local en `registry.py`, un campo erróneo en el detalle, y pruebas mal montadas |
| 2 | Correcciones del backend + frontend (necesidades, detalle, requisición precargada, enlace de alerta, interruptor en Maestros, cableado, Vitest) | 11989/17171 | $0,020154 | Aplicada entera. El primer envío del subagente no llegó a DeepSeek (parámetros mal formados) y no cuenta. Quedaron una validación sobrante en la ruta, una función inexistente en Maestros y cinco defectos de prueba |
| — | Hallazgo de auditoría | — | — | `alembic check` sobre PostgreSQL migrado: 0096 creaba `created_by` NOT NULL sin default y `version` en las dos tablas nuevas, que el modelo no tiene. En una base migrada no se habría podido guardar ninguna necesidad |
| 3 | E2E canónica + correcciones medidas + migración alineada con el modelo | 6528/4650 | $0,006885 | 15 de 16 bloques aplicados. Rechazado C1: reasignaba `status` a un objeto `Query` y rompía el filtro de estado. La E2E real demostró el flujo de producto completo; los fallos eran de la propia prueba |
| 4 | Correcciones demostradas por la ejecución (regresión C1 + E2E + Vitest) | 1061/810 | $0,001166 | AUDIT_PASS. E2E PASS a 1280, 390 y 320 |
| 5 | Orden del registro del planificador | 480/363 | $0,000525 | AUDIT_PASS. La suite completa reveló que `test_backup_job_retencion` exige que los tres manejadores de copias vayan al final del tick (el registro dice «el orden importa»); el manejador nuevo se movió antes de ellos |

| 6 | OWNER_EXCEPTION: fusión de cabezas con PROC-10 (`origin/develop` d1d0a0a trajo `0096_gov_proc10_garantias`) — `deepseek-v4-flash` | 971/565 | $0,000294 | F1 (migración vacía `0097_fusion_gov_replenishment`) AUDIT_PASS. F2–F5 AUDIT_REJECT: sin SEARCH/REPLACE y con los marcadores de conflicto dentro del texto nuevo |
| 6·R1 | Reintento 1 de F2–F5 (autorizado por la dueña) | 818/485 | $0,000250 | AUDIT_PASS. Se aplicó con coincidencia exacta de cada bloque de conflicto: las 3 guardas de cabeza pasan a 0097 y el catálogo a 462 |

**Total:** 5 llamadas del presupuesto ($0,053252) + 1 de excepción de la dueña con 1 reintento ($0,000544) = $0,053796. La 4 y la 5 traen causas nuevas, no repiten las anteriores.

**Errores de Claude:**
- un fragmento de contexto cortado a media línea en el brief 1;
- en la verificación de las mutaciones, la primera M1 alteró la clave de resolver en lugar de la de crear, y se repitió;
- la primera versión de la tarjeta de la dueña decía que la UAT tiene temporizador, y no lo tiene.

**Implementado por Claude:** ninguna línea de producto, de pruebas ni de migración. Solo operaciones mecánicas con herramienta: `ruff --fix` (orden de imports e imports sin uso) y regeneración de las instantáneas del frontend.
