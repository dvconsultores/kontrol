# RECEPCION-FUNCTIONAL-CLOSURE · registro de intentos

Una llamada a la vez. Sin commits en rojo.

| Subtarea | Intento | Coste | Resultado |
|---|---|---|---|
| RCL-J pruebas rojas de la máquina | ATTEMPT | $0,002142 | Rojo 39 de 39; ruff F811 |
| RCL-J | RETRY_1 | $0,000213 | AUDIT_PASS |
| RCL-F auditoría canónica | ATTEMPT | $0,000420 | AUDIT_PASS |
| RCL-B QUALITY_PENDING y consumidores | ATTEMPT | $0,000943 | AUDIT_PASS; cinco pruebas del ciclo anterior quedaban con el contrato viejo |
| RCL-B | RETRY_1 | $0,000328 | AUDIT_PASS |
| RCL-C aceptación parcial | ATTEMPT | $0,000404 | AUDIT_PASS |
| RCL-D cierre | ATTEMPT | $0,000567 | **AUDIT_REJECT erróneo de Claude**: las líneas en blanco sí estaban y el aviso de ruff era un artefacto de lintar en copia temporal |
| RCL-D | RETRY_1 | $0,000465 | Idéntica al intento; aplicada |
| RCL-E anulación | ATTEMPT | $0,000434 | AUDIT_PASS |
| RCL-I acciones en la API | ATTEMPT | $0,000333 | AUDIT_PASS |
| RCL-I pruebas rojas de pantalla | ATTEMPT | $0,001141 | AUDIT_REJECT: comprobaba el código del estado, no la etiqueta |
| RCL-I pruebas | RETRY_1 | $0,000128 | Aplicada; TSC rechazó `exact` en getByRole |
| RCL-I pruebas | RETRY_2 | $0,000074 | AUDIT_PASS. **El error era del encargo de Claude**. Presupuesto agotado |
| RCL-I pantalla | ATTEMPT | $0,000763 | AUDIT_PASS |
| RCL-L E2E y HTTP | ATTEMPT | $0,001374 | AUDIT_REJECT: `mundo.almacen_a` (el encargo no daba el nombre) y `/confirmacion` |
| RCL-L | RETRY_1 | $0,000082 | AUDIT_PASS |
| RCL-H escaneo histórico | ATTEMPT | $0,000585 | AUDIT_PASS |
| RCL-K pruebas por mutantes | ATTEMPT | $0,000240 | AUDIT_PASS |

19 llamadas, 6 reintentos, $0,010636. Dos reintentos los causó Claude. Agotados: RCL-I pruebas de pantalla. Se preservan los agotados del ciclo anterior (RFC-B/F/H, RFC-G).

Claude, sin código semántico: regenerar instantáneas con su generador, recomponer `catalogo.md` y el inventario de emisiones, y los arneses temporales de mutación.

## Mutaciones

31: 21 de backend y 10 de pantalla. 31 muertas por aserción, 0 equivalentes, 0 supervivientes requeridas. F9 y M10c sobrevivieron hasta RCL-K.
