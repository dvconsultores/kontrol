# RECEPCION-FUNCTIONAL-COMPLETION · registro de intentos

Ledger propio. Llamadas secuenciales, una a la vez. Sin commits en rojo.

| Subtarea | Intento | Coste | Resultado |
|---|---|---|---|
| RFC-B/F/H pruebas rojas backend | ATTEMPT | $0,001853 | AUDIT_REJECT: órdenes en DRAFT y `Query` sin resolver |
| RFC-B/F/H | RETRY_1 | $0,001982 | Aplicada; rojo medido. Ruff la rechazó |
| RFC-B/F/H | RETRY_2 | $0,000236 | AUDIT_PASS. Presupuesto agotado |
| RFC-G backend | ATTEMPT | $0,001167 | AUDIT_PASS |
| RFC-G | RETRY_1 | $0,000104 | AUDIT_PASS: el catálogo fijado sube a 327 |
| RFC-G | RETRY_2 | $0,000098 | AUDIT_PASS: `Sequence` en vez de `list`. El error era del encargo. Presupuesto agotado |
| RFC-D pruebas rojas pantalla | ATTEMPT | $0,002128 | AUDIT_REJECT: `name` resolvía a `window.name` |
| RFC-D | RETRY_1 | $0,000086 | AUDIT_PASS |
| RFC-E pantalla | ATTEMPT | $0,002028 | AUDIT_PASS; sus «decisiones» eran comprobaciones técnicas |
| RFC-K E2E y HTTP | ATTEMPT | $0,001181 | AUDIT_PASS; sin ejecutar |
| RFC-I pruebas por mutantes | ATTEMPT | $0,000544 | Aplicada; una prueba mal escrita |
| RFC-I | RETRY_1 | $0,000087 | AUDIT_PASS |

12 llamadas, 6 reintentos, $0,011494.

Claude hizo dos ajustes mecánicos, sin código semántico: regenerar `openapi-routes.json` con `qa/fixtures_de_frontend.py` y ordenar importaciones con `ruff --select I --fix` (OD-ORCH-01). Los documentos del catálogo de auditoría también son de Claude.

RFC-H (regla de almacén) quedó dentro de RFC-B/F/H y RFC-G; no fue una llamada aparte. RFC-A y RFC-J fueron de Claude: inventario y arnés temporal de mutaciones, fuera del repositorio.

## Mutaciones

42 en total: 41 muertas por aserción, 1 equivalente, 0 supervivientes requeridas. Frontend 26, backend 16.

M18 prefija el estado físico en el valor inicial. Es equivalente: el formulario solo se abre por `elegirRecepcion`, que vacía ese valor, así que el inicial no es alcanzable. Los mutantes de backend corrieron antes del cambio de anotación de RFC-G RETRY_2, que no altera la lógica.

## Fusión con la línea pública durante el ciclo

Upstream avanzó de `f544e59` a `fba4a31` mientras el ciclo estaba abierto. `PUBLIC_UPSTREAM_MOVED_DURING_CYCLE = YES`.

| COMMIT | TYPE | PRODUCT_LINE | FILES | IMPACT_ON_CURRENT_TARGET | IMPACT_ON_T052 | IMPACT_ON_RECEPTION | ACTION |
|---|---|---|---|---|---|---|---|
| `d1656a7` | feat | Government (ORG-04) | 69 | Solapa catálogo de auditoría y constantes de prueba | Segunda cabeza de Alembic junto a `0076_backup_rpo` | Ninguno funcional | Fusionado |
| `fba4a31` | docs | Government | 2 | Ninguno | Ninguno | Ninguno | Fusionado |

`NEW_TECHNICAL_BOUNDARY = 1`: dos cabezas sobre `0075_gov_ctl10_cierres`. Ninguna migración `0076` se modifica; `0077_fusion_backup_org04` las une sin cambiar el esquema, porque cada rama crea sus propias tablas.

| Subtarea | Intento | Coste | Resultado |
|---|---|---|---|
| RFC-M migración de fusión y constantes | ATTEMPT | $0,000313 | AUDIT_PASS |

Claude resolvió los marcadores de Git en el lado propio y recompuso `catalogo.md` como unión numerada: 330 filas. Ese documento no incluye los eventos de copias, que ya faltaban antes de esta fusión.

Total del ciclo con la fusión: 13 llamadas, 6 reintentos, $0,011807.

Certificación del árbol fusionado: SQLite con ClamAV 4875 recogidas, 3018 aprobadas, 0 fallidas, 0 errores, 1857 omitidas; Vitest 1536 de 1536 en 138 ficheros; TSC, ESLint y build RC 0; OpenAPI 707; mypy sin errores nuevos.
