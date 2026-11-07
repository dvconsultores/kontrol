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
