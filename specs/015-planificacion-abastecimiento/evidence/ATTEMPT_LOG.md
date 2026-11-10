# SPEC015_ROTACION_PROYECCION_REORDER · registro de intentos

Llamadas secuenciales a `deepseek-v4-pro` con `stream=true`, cada una con su brief autocontenido.

**Presupuesto:**
- Encargo: 7 llamadas, objetivo 5.
- Decisiones de la dueña durante el ciclo:
  - en la llamada 3, una tarea por llamada con tope de 14;
  - en la llamada 10, tope de 22 con aviso en la 18;
  - en la llamada 22, 1 llamada extra;
  - al cierre, 2 más: la fusión con PROC-08 y un defecto de aislamiento de `b40bbdc`. **25 en total**.

**Reparto del trabajo:**
- DeepSeek propuso todo el código, las pruebas, la migración y la configuración funcional.
- Claude diseñó, auditó, aplicó y certificó.
- Las correcciones de medición se hicieron solo en copias temporales. Los ficheros temporales del repositorio se restauraron comprobándolos por md5.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | T015-A módulo, migración, API de configuración | 10543/18078 | $0,020314 | AUDIT_REJECT. SEARCH no único; importación inventada; `require_permission` con un argumento; FK a una tabla inexistente (error del contrato de Claude); mypy +26 |
| 2 | T015-A reintento 1 | 11990/11661 | $0,015361 | Parcial. Quedan el CHECK sin `op.f`, mypy y vigencias en texto descartadas en silencio |
| 3 | T015-A reintento 2 + T015-B motor (dos tareas) | 12116/8737 | $0,012872 | Ignoró A por completo. Motor con importación errónea, fechas sin zona en SQLite y sin las rutas de consulta. Con arreglos de medición: 11 de 14 vectores exactos en PostgreSQL |
| 4 | T015-A cierre | 6552/5730 | $0,007835 | AUDIT_REJECT parcial: 2 EDIT de migración con SEARCH no único. Aplicados 9 bloques (vigencias, enteros, pruebas) |
| 5 | T015-A reintento | 1750/1919 | $0,002431 | AUDIT_PASS tras normalizar el marco de un fragmento que el brief de Claude cortó a media línea. Claude ejecutó `ruff --fix F401`. Migración up/down/up correcta |
| 6 | T015-B cierre + API | 3132/4182 | $0,005001 | 11 de 12 bloques. Rechazado el escenario «o» (partía otro escenario, APIs inventadas). Defecto hallado en auditoría: EXISTS sobre COUNT, siempre verdadero |
| 7 | T015-B reintento 1 | 1200/1036 | $0,001423 | 3 de 4. Escenario «o» rechazado de nuevo |
| 8 | T015-B reintento 2 | 2282/692 | $0,001595 | AUDIT_PASS. 27/27 en PostgreSQL. La mutación EXISTS→COUNT la detecta «o» |
| 9 | T015-C requisición e instantánea | 7846/9809 | $0,011947 | Aplicada. Importaciones inventadas, `req.lines` inexistente, 400 en lugar de 422, decimales sin cuantizar, pruebas mal montadas |
| 10 | T015-C reintento 1 | 6516/6141 | $0,008177 | Aplicado. Queda la variable `lines` reasignada |
| 11 | T015-C reintento 2 | 555/152 | $0,000374 | AUDIT_PASS. 164/164 en PostgreSQL. La mutación de la versión de política la detecta «f» |
| — | Claude, mecánica | — | — | `ruff --fix --select I001,F401` sobre `app/modules/storage` (7 errores previos ocultos) |
| 12 | T015-D banda en el motor de almacenamiento | 4810/5304 | $0,006707 | Aplicada. Motor correcto; tres defectos de prueba |
| 13 | T015-D reintento 1 | 1859/1643 | $0,002238 | 6 de 8 bloques. 2 rechazados: SEARCH idéntico no único |
| 14 | T015-D reintento 2 | 517/601 | $0,000748 | AUDIT_PASS. 71/71 en PostgreSQL. La mutación «banda distinta coincide» la detecta la prueba lenta |
| 15 | T015-E1 Maestros → Planificación | 7309/9417 | $0,011372 | Aplicada. TS2322, avisos de lint, `h2` dentro de `Autorizado`, etiquetas exactas en pruebas: 4 de 7 en rojo |
| 16 | T015-E1 reintento 1 | 9524/8839 | $0,011833 | AUDIT_PASS. 7/7 |
| 17 | T015-E2 nueva requisición y detalle con panel | 6752/9974 | $0,011614 | Aplicada. 7 de 8 escenarios |
| 18 | T015-E2 reintento 1 | 630/80 | $0,000344 | AUDIT_PASS de la aserción. La suite completa destapó la puerta `gate-coverage`: alta sin `Autorizado` |
| 19 | T015-E2 reintento 2 | 398/186 | $0,000335 | AUDIT_PASS. Vitest 1891/1891 |
| 20 | T015-E3 banda en las reglas (UI) | 3891/4170 | $0,005320 | AUDIT_PASS a la primera. Vitest 1892/1892 |
| 21 | T015-F E2E | 3770/2552 | $0,003860 | Falla a 1280: carrera de sesión tras `goto("/")` (diagnosticada con una sonda), etiquetas que no existen y textos duplicados |
| 22 | T015-F reintento 1 | 3312/2728 | $0,003814 | E2E PASS a 1280, 390 y 320. Introdujo, sin pedírselo, una aserción vacía (`expect(bandasRes)`) |
| 23 | T015-F aserción (extra autorizada) | 259/57 | $0,000162 | AUDIT_PASS. E2E PASS a 1280, 390 y 320 |
| 25 | Aislamiento de `GET /storage/profiles` (deuda de `b40bbdc`, extra autorizada) | 1373/838 | $0,001326 | AUDIT_PASS. Barrido de aislamiento verde en PostgreSQL |
| 24 | Migración de fusión `0095_fusion_gov_planning` con PROC-08 de P1 y cabezas (extra autorizada) | 856/555 | $0,000855 | AUDIT_PASS. Alembic up/down/up en PostgreSQL con una sola cabeza |

**Total:** 25 llamadas, $0,147858. La 24 (fusión) y la 25 (aislamiento) las autorizó la dueña al cierre. La 25 se registra antes que la 24 porque se aplicó antes.

**Rechazos:**
- Completos: llamadas 1 y 3; esta última ignoró la tarea A.
- Parciales: llamadas 4, 6, 7 y 13.

**Errores de Claude:**
- En los contratos: FK, CHECK y nombres de constraint.
- En los briefs: un fragmento cortado a media línea y un fragmento sin la ruta.
- Medición: la primera corrida de la suite backend se lanzó sin el entorno del analizador.

**Implementado por Claude:** ninguna línea de producto, de pruebas ni de migración. Claude hizo dos operaciones mecánicas con herramienta:
- `ruff --fix` sobre imports sin uso y su orden;
- regeneración de las instantáneas del frontend con `qa/fixtures_de_frontend.py`.
- quitar líneas en blanco finales en 5 ficheros (`git diff --check`);
- resolución de los conflictos de la fusión con PROC-08 (contadores y cabezas tomados de P1, que DeepSeek apuntó después a `0095`).
