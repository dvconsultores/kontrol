# ALMACENES-DESPLEGABLES-TRUNCADOS · registro de intentos

Coste total: $0,007751 en 7 llamadas, secuenciales. Ledger propio: defecto distinto.

| Subtarea | Intento | Coste | Resultado | Motivo |
|---|---|---|---|---|
| ALM-A prueba roja | 1 | $0,000806 | AUDIT_PASS con un defecto | `findByRole` con dos selectores; corregido en ALM-C |
| ALM-B parte 1 | 1 | $0,001178 | AUDIT_PASS | — |
| ALM-B parte 2 | 1 | $0,001069 | 19 de 20 bloques; 1 rechazado | Mi extracto llevaba 2 espacios de más |
| ALM-C | 1 | $0,003142 | Parcial | Faltaron ayudantes; 2 anclas con sangría errónea, también de mi extracto |
| ALM-C RETRY_1 | 2 | $0,000227 | AUDIT_PASS | — |
| ALM-C RETRY_2 | 3 | $0,000725 | AUDIT_PASS | Presupuesto agotado y cerrado |
| ALM-E E2E preparada | 1 | $0,000604 | AUDIT_PASS | Sin ejecutar |

Sin llamadas en paralelo y sin commits en rojo.
