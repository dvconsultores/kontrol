# RECEPCION-LINEA-ORDEN-INTEGRIDAD · registro de intentos

Ledger propio. Llamadas secuenciales, una a la vez. Sin commits en rojo.

| Subtarea | Intento | Coste | Resultado |
|---|---|---|---|
| RLI-B prueba roja backend | ATTEMPT | $0,001386 | AUDIT_REJECT: omitió `ProductSerial` (BT-09) |
| RLI-B | RETRY_1 | $0,001734 | AUDIT_PASS; aplicada. BT-11 cayó por el arnés |
| RLI-B | RETRY_2 | $0,000124 | AUDIT_PASS; `expire_all` en la fixture. Presupuesto agotado, sin más llamadas |
| RLI-D invariante backend | ATTEMPT | $0,000424 | AUDIT_PASS |
| RLI-A prueba roja interfaz | ATTEMPT | $0,002013 | AUDIT_REJECT: servidor falso con envoltorio y selectores por rol demasiado amplios |
| RLI-A | RETRY_1 | $0,002401 | AUDIT_PASS |
| RLI-E selector y producto derivado | ATTEMPT | $0,001427 | AUDIT_PASS; sus «dudas materiales» eran técnicas y se comprobaron con TSC |
| RLI-F pruebas por mutantes supervivientes | ATTEMPT | $0,000346 | AUDIT_PASS |
| RLI-H E2E preparada | ATTEMPT | $0,000672 | AUDIT_PASS; sin ejecutar |

9 llamadas, 3 reintentos, 2 parches rechazados, $0,010527. RLI-F es subtarea propia del plan: cubre requisitos que RLI-A no pedía, no corrige pruebas de RLI-A. RLI-C y RLI-G fueron de Claude: diseño y arnés temporal de mutaciones, fuera del repositorio.

## Mutaciones

32 en total: 31 muertas por aserción, 1 equivalente, 0 supervivientes requeridas.

M9b quita la guarda de presentación. Es equivalente: cada cambio de línea y de recepción ya vacía la presentación, así que la guarda no actúa en ningún flujo alcanzable. M9c, que quita ambas protecciones, muere.
